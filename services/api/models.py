"""SQLModel ORM models for Nexova inventory management.

Entities strictly follow the Nexova briefing specifications:
- Asset: Catalogued inventory assets.
- AssetEntry: Inbound inventory movements.
- AssetExit: Outbound inventory movements (allocation or consumption).
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


def utc_now() -> datetime:
    """Return timezone-aware or ISO UTC datetime."""
    return datetime.now(timezone.utc)


class Asset(SQLModel, table=True):
    """Catalogued inventory asset entity.
    
    Current stock is strictly calculated dynamically from movements
    and is NEVER persisted as a table column.
    """

    __tablename__ = "asset"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, index=True)
    sku: str = Field(nullable=False, unique=True, index=True)
    category: str = Field(nullable=False, index=True)
    office: str = Field(nullable=False, index=True)

    # Relationships to inbound/outbound movements
    entries: List["AssetEntry"] = Relationship(back_populates="asset")
    exits: List["AssetExit"] = Relationship(back_populates="asset")


class AssetEntry(SQLModel, table=True):
    """Inbound asset movement representing stock arrival from a supplier."""

    __tablename__ = "asset_entry"

    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id", nullable=False, index=True)
    quantity: int = Field(nullable=False)
    supplier: str = Field(nullable=False)
    office: str = Field(nullable=False, index=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    user_uuid: str = Field(nullable=False, index=True)

    # Relationship to the parent asset
    asset: Optional[Asset] = Relationship(back_populates="entries")


class AssetExit(SQLModel, table=True):
    """Outbound asset movement representing allocation or consumption."""

    __tablename__ = "asset_exit"

    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id", nullable=False, index=True)
    quantity: int = Field(nullable=False)
    exit_type: str = Field(nullable=False, index=True)
    assigned_to: Optional[str] = Field(default=None, nullable=True)
    office: str = Field(nullable=False, index=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    user_uuid: str = Field(nullable=False, index=True)

    # Relationship to the parent asset
    asset: Optional[Asset] = Relationship(back_populates="exits")
