"""FastAPI Router for Nexova Inventory operations under /inventory."""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from services.api.auth_dependencies import get_current_user
from services.api.auth_models import UserRecord
from services.api.database import get_db
from services.api.inventory_service import (
    create_asset,
    get_asset_read,
    list_assets,
    list_orders,
    register_inbound_order,
    register_outbound_order,
)
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


@router.get(
    "/products",
    response_model=List[AssetRead],
    status_code=status.HTTP_200_OK,
    summary="List all catalogued assets with calculated stock",
)
def get_products(session: Session = Depends(get_db)) -> List[AssetRead]:
    """Retrieve all assets along with their derived stock per office."""
    return list_assets(session)


@router.post(
    "/products",
    response_model=AssetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new asset in catalog",
)
def post_product(
    payload: AssetCreate,
    session: Session = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
) -> AssetRead:
    """Create a new asset with initial stock 0. Requires authentication."""
    return create_asset(session, payload)


@router.get(
    "/products/{id}",
    response_model=AssetRead,
    status_code=status.HTTP_200_OK,
    summary="Retrieve an asset by ID with current stock",
)
def get_product_by_id(id: int, session: Session = Depends(get_db)) -> AssetRead:
    """Retrieve asset details and derived current stock. 404 if not found."""
    return get_asset_read(session, id)


@router.post(
    "/orders/inbound",
    response_model=AssetEntryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register inbound asset movement (stock arrival)",
)
def post_inbound_order(
    payload: AssetEntryCreate,
    session: Session = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
) -> AssetEntryRead:
    """Register stock arrival from supplier. Requires authentication."""
    user_uuid = str(current_user.id)
    return register_inbound_order(session, payload, user_uuid=user_uuid)


@router.post(
    "/orders/outbound",
    response_model=AssetExitRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register outbound asset movement (allocation or consumption)",
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
    return register_outbound_order(session, payload, user_uuid=user_uuid)


@router.get(
    "/orders",
    response_model=List[OrderItemRead],
    status_code=status.HTTP_200_OK,
    summary="List all inbound and outbound inventory movements",
)
def get_orders(session: Session = Depends(get_db)) -> List[OrderItemRead]:
    """Retrieve all inventory movements with parent asset details without N+1 queries."""
    return list_orders(session)

