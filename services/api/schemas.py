"""Pydantic request and response schemas for Nexova inventory API.

Ensures strict separation between database ORM entities and API contracts.
Enforces Nexova domain validation rules:
- Valid categories: hardware, peripherals, office_supplies, training_materials
- Valid offices: Valencia, Miami
- Valid exit_types: allocation, consumption
- Conditional assigned_to: required when exit_type=allocation, must be null when consumption
- Positive quantities (gt=0)
- Client prohibited from supplying id, created_at, user_uuid, or current_stock in create payloads
"""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

CategoryType = Literal["hardware", "peripherals", "office_supplies", "training_materials"]
OfficeType = Literal["Valencia", "Miami"]
ExitType = Literal["allocation", "consumption"]
MovementType = Literal["inbound", "outbound"]


# ==========================================
# Asset Schemas
# ==========================================

class AssetBase(BaseModel):
    name: str = Field(..., min_length=1, description="Asset display name")
    sku: str = Field(..., min_length=1, description="Unique asset SKU code")
    category: CategoryType = Field(..., description="Predefined asset category")
    office: OfficeType = Field(..., description="Office location (Valencia or Miami)")


class AssetCreate(AssetBase):
    """Payload for creating a new asset.
    
    extra='forbid' prevents sending id, created_at, user_uuid, or current_stock.
    """
    model_config = ConfigDict(extra="forbid")


class AssetRead(AssetBase):
    """Public representation of an asset including calculated stock."""
    id: int
    current_stock: int = Field(default=0, description="Derived net stock (entries - exits)")

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Asset Entry (Inbound) Schemas
# ==========================================

class AssetEntryCreate(BaseModel):
    """Payload for registering an inbound stock delivery."""
    asset_id: int = Field(..., gt=0, description="Target asset ID")
    quantity: int = Field(..., gt=0, description="Units received, must be positive")
    supplier: str = Field(..., min_length=1, description="Supplier name")
    office: OfficeType = Field(..., description="Receiving office (Valencia or Miami)")

    model_config = ConfigDict(extra="forbid")


class AssetEntryRead(BaseModel):
    """Public representation of an inbound asset entry."""
    id: int
    asset_id: int
    quantity: int
    supplier: str
    office: OfficeType
    created_at: datetime
    user_uuid: str

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Asset Exit (Outbound) Schemas
# ==========================================

class AssetExitCreate(BaseModel):
    """Payload for registering an outbound asset exit (allocation or consumption)."""
    asset_id: int = Field(..., gt=0, description="Target asset ID")
    quantity: int = Field(..., gt=0, description="Units allocated/consumed, must be positive")
    exit_type: ExitType = Field(..., description="Type of exit: allocation or consumption")
    assigned_to: Optional[str] = Field(default=None, description="Mandatory for allocation, null for consumption")
    office: OfficeType = Field(..., description="Office where exit occurs (Valencia or Miami)")

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_assigned_to(self) -> "AssetExitCreate":
        if self.exit_type == "allocation":
            if not self.assigned_to or not self.assigned_to.strip():
                raise ValueError("Field 'assigned_to' is required when exit_type is 'allocation'.")
        elif self.exit_type == "consumption":
            if self.assigned_to is not None:
                raise ValueError("Field 'assigned_to' must be null when exit_type is 'consumption'.")
        return self


class AssetExitRead(BaseModel):
    """Public representation of an outbound asset exit."""
    id: int
    asset_id: int
    quantity: int
    exit_type: ExitType
    assigned_to: Optional[str] = None
    office: OfficeType
    created_at: datetime
    user_uuid: str

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Unified Orders / Movement List Schemas
# ==========================================

class OrderItemRead(BaseModel):
    """Consolidated representation of an inbound or outbound inventory order."""
    id: int
    movement_type: MovementType = Field(..., description="'inbound' for entry, 'outbound' for exit")
    asset_id: int
    asset_name: str
    asset_sku: str
    quantity: int
    office: OfficeType
    supplier: Optional[str] = None
    exit_type: Optional[ExitType] = None
    assigned_to: Optional[str] = None
    created_at: datetime
    user_uuid: str

    model_config = ConfigDict(from_attributes=True)

