"""FastAPI Router for Nexova Inventory operations under /inventory."""

from collections.abc import Hashable
from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session

from services.api.auth_dependencies import get_current_user
from services.api.auth_models import UserRecord
from services.api.database import get_db
from services.api.response_models import DetailErrorResponse
from services.api.inventory_service import (
    calculate_asset_stock,
    create_asset,
    get_asset_by_id,
    get_asset_read,
    list_assets,
    list_orders,
    register_inbound_order,
    register_outbound_order,
)
from services.api.inventory_telemetry import (
    InventoryFacts,
    attach_signals,
    movement_lock,
    previous_unit_cost,
    signal,
)
from services.api.response_cache import response_cache
from services.api.routers.suppliers import get_supplier
from services.api.schemas import (
    AssetCreate,
    AssetEntryCreate,
    AssetEntryRead,
    AssetExitCreate,
    AssetExitRead,
    AssetRead,
    OrderItemRead,
    OfficeType,
)

router = APIRouter(prefix="/inventory", tags=["Inventory"])
DEFAULT_ERROR_RESPONSES = {500: {"model": DetailErrorResponse, "description": "Internal server error"}}
PRODUCTS_CACHE_TTL_SECONDS = 15


def _facts(request: Request, asset_id: int, office: str) -> InventoryFacts | None:
    return (getattr(request.app.state, "inventory_facts", None) or {}).get((asset_id, office))


def _products_cache_key(session: Session) -> tuple[str, Hashable]:
    return ("inventory:products", session.get_bind())


@router.get(
    "/products",
    response_model=List[AssetRead],
    status_code=status.HTTP_200_OK,
    summary="List all catalogued assets with calculated stock",
    responses=DEFAULT_ERROR_RESPONSES,
)
def get_products(session: Session = Depends(get_db)) -> List[AssetRead]:
    """Retrieve all assets along with their derived stock per office."""
    return response_cache.get_or_set(
        _products_cache_key(session),
        PRODUCTS_CACHE_TTL_SECONDS,
        lambda: list_assets(session),
    )


@router.post(
    "/products",
    response_model=AssetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new asset in catalog",
    responses={
        400: {"model": DetailErrorResponse, "description": "SKU already exists."},
        401: {"model": DetailErrorResponse, "description": "Authentication required or invalid bearer token."},
        **DEFAULT_ERROR_RESPONSES,
    },
)
def post_product(
    payload: AssetCreate,
    session: Session = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
) -> AssetRead:
    """Create a new asset with initial stock 0. Requires authentication."""
    created = create_asset(session, payload)
    response_cache.invalidate(_products_cache_key(session))
    return created


@router.get(
    "/products/{id}",
    response_model=AssetRead,
    status_code=status.HTTP_200_OK,
    summary="Retrieve an asset by ID with current stock",
    responses={404: {"model": DetailErrorResponse, "description": "Asset not found."}, **DEFAULT_ERROR_RESPONSES},
)
def get_product_by_id(id: int, session: Session = Depends(get_db)) -> AssetRead:
    """Retrieve asset details and derived current stock. 404 if not found."""
    return get_asset_read(session, id)


@router.post(
    "/orders/inbound",
    response_model=AssetEntryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register inbound asset movement (stock arrival)",
    responses={
        401: {"model": DetailErrorResponse, "description": "Authentication required or invalid bearer token."},
        404: {"model": DetailErrorResponse, "description": "Asset not found."},
        **DEFAULT_ERROR_RESPONSES,
    },
)
def post_inbound_order(
    payload: AssetEntryCreate,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
) -> AssetEntryRead:
    """Register stock arrival from supplier. Requires authentication."""
    facts = _facts(request, payload.asset_id, payload.office)
    supplier_id, cents = payload.supplier_id, payload.unit_cost_cents
    signals = []
    with movement_lock:
        if supplier_id is not None and cents is not None:
            supplier = get_supplier(supplier_id)
            payload = payload.model_copy(update={"supplier": supplier.name})
            threshold = facts.variance_threshold_percent if facts else None
            baseline = previous_unit_cost(session, payload.asset_id, payload.office, supplier_id) if threshold is not None else None
            if facts:
                properties = {
                    **facts.properties(payload.quantity),
                    "unit_cost": cents / 100,
                    "supplier_ref": str(supplier_id),
                }
                signals.append(signal("inbound_order_created", properties))
                if threshold is not None and baseline is not None and baseline > 0:
                    variance = Decimal(cents - baseline) * 100 / baseline
                    if variance > threshold:
                        signals.append(signal("kit_cost_variance_detected", {
                            **properties, "baseline_unit_cost": baseline / 100,
                            "variance_percent": float(variance), "threshold_percent": float(threshold),
                        }))
        created = register_inbound_order(session, payload, user_uuid=str(current_user.id))
    response_cache.invalidate(_products_cache_key(session))
    attach_signals(response, signals)
    return created


@router.post(
    "/orders/outbound",
    response_model=AssetExitRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register outbound asset movement (allocation or consumption)",
    responses={
        400: {"model": DetailErrorResponse, "description": "Insufficient stock for this asset and office."},
        401: {"model": DetailErrorResponse, "description": "Authentication required or invalid bearer token."},
        404: {"model": DetailErrorResponse, "description": "Asset not found."},
        **DEFAULT_ERROR_RESPONSES,
    },
)
def post_outbound_order(
    payload: AssetExitCreate,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
) -> AssetExitRead:
    """Register stock exit (allocation or consumption).
    
    Verifies available stock for asset and office.
    Rejects with 400 and exact error message if stock is insufficient.
    Requires authentication.
    """
    facts = _facts(request, payload.asset_id, payload.office)
    minimum = facts.minimum_stock if facts else None
    signals = []
    with movement_lock:
        before = calculate_asset_stock(session, payload.asset_id, payload.office) if minimum is not None else None
        created = register_outbound_order(session, payload, user_uuid=str(current_user.id))
    if facts and payload.recipient_type is not None:
        signals.append(signal("outbound_order_created", {
            **facts.properties(created.quantity), "recipient_type": payload.recipient_type,
        }))
    if facts and minimum is not None and before is not None and before >= minimum > before - created.quantity:
        signals.append(signal("stock_threshold_triggered", {
            **facts.properties(before - created.quantity), "threshold_quantity": minimum,
        }))
    response_cache.invalidate(_products_cache_key(session))
    attach_signals(response, signals)
    return created


class DirectStockEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    office: OfficeType
    quantity: int = Field(strict=True, ge=-2_147_483_647, le=2_147_483_647)


@router.patch(
    "/products/{id}/stock",
    status_code=status.HTTP_409_CONFLICT,
    response_model=DetailErrorResponse,
    summary="Reject a direct stock change; an inventory order is required",
    dependencies=[Depends(get_current_user)],
)
def reject_direct_stock_edit(
    id: int, payload: DirectStockEdit, request: Request, session: Session = Depends(get_db),
) -> JSONResponse:
    get_asset_by_id(session, id)
    facts = _facts(request, id, payload.office)
    response = JSONResponse(status_code=409, content={"detail": "Registra una orden de entrada o salida para modificar existencias."})
    signals = [signal("direct_stock_edit_rejected", {
        **facts.properties(payload.quantity), "rejection_code": "order_required",
    })] if facts else []
    attach_signals(response, signals)
    return response


@router.get(
    "/orders",
    response_model=List[OrderItemRead],
    status_code=status.HTTP_200_OK,
    summary="List all inbound and outbound inventory movements",
    responses=DEFAULT_ERROR_RESPONSES,
)
def get_orders(session: Session = Depends(get_db)) -> List[OrderItemRead]:
    """Retrieve all inventory movements with parent asset details without N+1 queries."""
    return list_orders(session)
