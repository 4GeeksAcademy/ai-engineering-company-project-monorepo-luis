"""Domain service and business logic for Nexova Inventory operations.

Implements all core business requirements:
- Derived stock: current_stock = SUM(AssetEntry) - SUM(AssetExit) per (asset_id, office).
- Zero initial stock on asset creation.
- Insufficient stock validation returning exact required error message.
- Atomic operations with zero partial state on rejection.
- N+1 query avoidance for order listings and asset stock aggregations.
"""

from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from services.api.models import Asset, AssetEntry, AssetExit
from services.api.schemas import (
    AssetCreate,
    AssetEntryCreate,
    AssetEntryRead,
    AssetExitCreate,
    AssetExitRead,
    AssetRead,
    OrderItemRead,
)


class InsufficientStockError(HTTPException):
    """Raised when an outbound movement exceeds available stock for the asset and office."""

    def __init__(self, asset_name: str, available: int, requested: int):
        detail = f"Insufficient stock for asset '{asset_name}'. Available: {available}, requested: {requested}."
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class AssetNotFoundError(HTTPException):
    """Raised when an asset does not exist."""

    def __init__(self, asset_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with id {asset_id} not found.",
        )


class DuplicateSkuError(HTTPException):
    """Raised when creating an asset with an existing SKU."""

    def __init__(self, sku: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset with SKU '{sku}' already exists.",
        )


def calculate_asset_stock(session: Session, asset_id: int, office: str) -> int:
    """Calculate derived net stock for a specific asset and office.
    
    current_stock = SUM(AssetEntry.quantity) - SUM(AssetExit.quantity)
    Filtered strictly by asset_id and office to avoid cross-office leakage.
    """
    total_entries_query = select(
        func.coalesce(func.sum(AssetEntry.quantity), 0)
    ).where(
        AssetEntry.asset_id == asset_id,
        AssetEntry.office == office,
    )
    total_entries = session.exec(total_entries_query).one()

    total_exits_query = select(
        func.coalesce(func.sum(AssetExit.quantity), 0)
    ).where(
        AssetExit.asset_id == asset_id,
        AssetExit.office == office,
    )
    total_exits = session.exec(total_exits_query).one()

    return int(total_entries) - int(total_exits)


def get_asset_by_id(session: Session, asset_id: int) -> Asset:
    """Retrieve an Asset ORM instance by ID or raise AssetNotFoundError."""
    asset = session.get(Asset, asset_id)
    if not asset:
        raise AssetNotFoundError(asset_id)
    return asset


def create_asset(session: Session, payload: AssetCreate) -> AssetRead:
    """Create a new Asset in catalog.
    
    Enforces SKU uniqueness and ensures initial stock is strictly zero.
    """
    existing = session.exec(select(Asset).where(Asset.sku == payload.sku)).first()
    if existing:
        raise DuplicateSkuError(payload.sku)

    asset = Asset(
        name=payload.name,
        sku=payload.sku,
        category=payload.category,
        office=payload.office,
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)

    return AssetRead(
        id=asset.id,
        name=asset.name,
        sku=asset.sku,
        category=asset.category,
        office=asset.office,
        current_stock=0,
    )


def get_asset_read(session: Session, asset_id: int) -> AssetRead:
    """Retrieve an asset with its calculated current stock."""
    asset = get_asset_by_id(session, asset_id)
    stock = calculate_asset_stock(session, asset.id, asset.office)
    return AssetRead(
        id=asset.id,
        name=asset.name,
        sku=asset.sku,
        category=asset.category,
        office=asset.office,
        current_stock=stock,
    )


def list_assets(session: Session) -> List[AssetRead]:
    """List all assets with aggregated stock calculations, preventing N+1 queries."""
    assets = list(session.exec(select(Asset).order_by(Asset.id)).all())
    if not assets:
        return []

    # Aggregate inbound entries by (asset_id, office)
    inbound_agg = session.exec(
        select(
            AssetEntry.asset_id,
            AssetEntry.office,
            func.coalesce(func.sum(AssetEntry.quantity), 0),
        ).group_by(AssetEntry.asset_id, AssetEntry.office)
    ).all()
    inbound_map = {(row[0], row[1]): int(row[2]) for row in inbound_agg}

    # Aggregate outbound exits by (asset_id, office)
    outbound_agg = session.exec(
        select(
            AssetExit.asset_id,
            AssetExit.office,
            func.coalesce(func.sum(AssetExit.quantity), 0),
        ).group_by(AssetExit.asset_id, AssetExit.office)
    ).all()
    outbound_map = {(row[0], row[1]): int(row[2]) for row in outbound_agg}

    result = []
    for asset in assets:
        key = (asset.id, asset.office)
        stock = inbound_map.get(key, 0) - outbound_map.get(key, 0)
        result.append(
            AssetRead(
                id=asset.id,
                name=asset.name,
                sku=asset.sku,
                category=asset.category,
                office=asset.office,
                current_stock=stock,
            )
        )
    return result


def register_inbound_order(
    session: Session, payload: AssetEntryCreate, user_uuid: str
) -> AssetEntryRead:
    """Record an inbound asset entry and attribute the authenticated user."""
    # Verify asset exists
    asset = get_asset_by_id(session, payload.asset_id)

    entry = AssetEntry(
        asset_id=asset.id,
        quantity=payload.quantity,
        supplier=payload.supplier,
        office=payload.office,
        user_uuid=user_uuid,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)

    return AssetEntryRead.model_validate(entry)


def register_outbound_order(
    session: Session, payload: AssetExitCreate, user_uuid: str
) -> AssetExitRead:
    """Record an outbound asset exit after verifying available stock.
    
    If requested quantity > available stock:
    Raises InsufficientStockError with exact text and commits no changes.
    """
    asset = get_asset_by_id(session, payload.asset_id)

    available = calculate_asset_stock(session, asset.id, payload.office)
    if payload.quantity > available:
        raise InsufficientStockError(
            asset_name=asset.name,
            available=available,
            requested=payload.quantity,
        )

    outbound = AssetExit(
        asset_id=asset.id,
        quantity=payload.quantity,
        exit_type=payload.exit_type,
        assigned_to=payload.assigned_to,
        office=payload.office,
        user_uuid=user_uuid,
    )
    session.add(outbound)
    session.commit()
    session.refresh(outbound)

    return AssetExitRead.model_validate(outbound)


def list_orders(session: Session) -> List[OrderItemRead]:
    """Retrieve all inbound and outbound movements with eager loaded asset info.
    
    Prevents N+1 queries by pre-fetching parent assets in joins/selectinload.
    """
    # Query entries with eager-loaded asset
    entries_query = (
        select(AssetEntry)
        .options(selectinload(AssetEntry.asset))
        .order_by(AssetEntry.created_at.desc(), AssetEntry.id.desc())
    )
    entries = list(session.exec(entries_query).all())

    # Query exits with eager-loaded asset
    exits_query = (
        select(AssetExit)
        .options(selectinload(AssetExit.asset))
        .order_by(AssetExit.created_at.desc(), AssetExit.id.desc())
    )
    exits = list(session.exec(exits_query).all())

    orders: List[OrderItemRead] = []

    for entry in entries:
        orders.append(
            OrderItemRead(
                id=entry.id,
                movement_type="inbound",
                asset_id=entry.asset_id,
                asset_name=entry.asset.name if entry.asset else "Unknown",
                asset_sku=entry.asset.sku if entry.asset else "Unknown",
                quantity=entry.quantity,
                office=entry.office,
                supplier=entry.supplier,
                exit_type=None,
                assigned_to=None,
                created_at=entry.created_at,
                user_uuid=entry.user_uuid,
            )
        )

    for exit_item in exits:
        orders.append(
            OrderItemRead(
                id=exit_item.id,
                movement_type="outbound",
                asset_id=exit_item.asset_id,
                asset_name=exit_item.asset.name if exit_item.asset else "Unknown",
                asset_sku=exit_item.asset.sku if exit_item.asset else "Unknown",
                quantity=exit_item.quantity,
                office=exit_item.office,
                supplier=None,
                exit_type=exit_item.exit_type,
                assigned_to=exit_item.assigned_to,
                created_at=exit_item.created_at,
                user_uuid=exit_item.user_uuid,
            )
        )

    # Sort combined movements by created_at descending
    orders.sort(key=lambda o: (o.created_at, o.id), reverse=True)
    return orders
