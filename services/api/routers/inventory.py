"""FastAPI Router for Nexova Inventory operations under /inventory."""

from collections.abc import Hashable
from typing import List
from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from services.api.auth_dependencies import get_current_user
from services.api.auth_models import UserRecord
from services.api.database import get_db
from services.api.response_models import DetailErrorResponse
from services.api.inventory_service import (
    create_asset,
    get_asset_read,
    list_assets,
    list_orders,
    register_inbound_order,
    register_outbound_order,
)
from services.api.response_cache import response_cache
from services.api.schemas import (
    AssetCreate,
    AssetEntryCreate,
    AssetEntryRead,
    AssetExitCreate,
    AssetExitRead,
    AssetRead,
    OrderItemRead,
)

router = APIRouter(prefix="/inventory", tags=["Inventory"])
PRODUCTS_CACHE_TTL_SECONDS = 15


def _products_cache_key(session: Session) -> tuple[str, Hashable]:
    return ("inventory:products", session.get_bind())


@router.get(
    "/products",
    response_model=List[AssetRead],
    status_code=status.HTTP_200_OK,
    summary="List all catalogued assets with calculated stock",
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
    responses={404: {"model": DetailErrorResponse, "description": "Asset not found."}},
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
    },
)
def post_inbound_order(
    payload: AssetEntryCreate,
    session: Session = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
) -> AssetEntryRead:
    """Register stock arrival from supplier. Requires authentication."""
    user_uuid = str(current_user.id)
    created = register_inbound_order(session, payload, user_uuid=user_uuid)
    response_cache.invalidate(_products_cache_key(session))
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
    },
)
def post_outbound_order(
    payload: AssetExitCreate,
    session: Session = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
) -> AssetExitRead:
    """Register stock exit (allocation or consumption).
    
    Verifies available stock for asset and office.
    Rejects with 400 and exact error message if stock is insufficient.
    Requires authentication.
    """
    user_uuid = str(current_user.id)
    created = register_outbound_order(session, payload, user_uuid=user_uuid)
    response_cache.invalidate(_products_cache_key(session))
    return created


@router.get(
    "/orders",
    response_model=List[OrderItemRead],
    status_code=status.HTTP_200_OK,
    summary="List all inbound and outbound inventory movements",
)
def get_orders(session: Session = Depends(get_db)) -> List[OrderItemRead]:
    """Retrieve all inventory movements with parent asset details without N+1 queries."""
    return list_orders(session)
