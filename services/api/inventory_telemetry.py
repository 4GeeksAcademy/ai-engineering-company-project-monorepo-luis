"""Authoritative, allowlisted signals attached to inventory confirmations."""

import json
import os
from decimal import Decimal
from threading import RLock
from typing import Literal
from uuid import uuid4

from fastapi import Response
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError
from sqlmodel import Session, col, select

from services.api.models import AssetEntry, AssetEntryCost
from services.api.schemas import OfficeType

SIGNALS_HEADER = "X-Inventory-Telemetry"
REQUEST_ID_HEADER = "X-Request-ID"
movement_lock = RLock()


class InventoryFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(gt=0, strict=True)
    office: OfficeType
    programme_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    product_category: Literal["training_kit", "certification", "onboarding_equipment"]
    minimum_stock: int | None = Field(default=None, ge=0, strict=True)
    variance_threshold_percent: Decimal | None = Field(default=None, ge=0, le=100_000)

    def properties(self, quantity: int) -> dict[str, str | int]:
        return {
            "office": self.office.lower(),
            "currency": "EUR" if self.office == "Valencia" else "USD",
            "product_id": str(self.asset_id),
            "product_category": self.product_category,
            "programme_id": self.programme_id,
            "quantity": quantity,
        }


def load_inventory_facts() -> dict[tuple[int, str], InventoryFacts]:
    try:
        catalog = TypeAdapter(list[InventoryFacts]).validate_json(
            os.getenv("INVENTORY_TELEMETRY_CATALOG", "[]")
        )
    except ValidationError:
        raise RuntimeError("Invalid INVENTORY_TELEMETRY_CATALOG") from None
    result = {(item.asset_id, item.office): item for item in catalog}
    if len(result) != len(catalog):
        raise RuntimeError("Duplicate asset/office in INVENTORY_TELEMETRY_CATALOG")
    return result


def previous_unit_cost(session: Session, asset_id: int, office: str, supplier_id: int) -> int | None:
    return session.exec(
        select(AssetEntryCost.unit_cost_cents)
        .join(AssetEntry, col(AssetEntry.id) == col(AssetEntryCost.entry_id))
        .where(AssetEntry.asset_id == asset_id, AssetEntry.office == office,
               AssetEntryCost.supplier_id == supplier_id)
        .order_by(col(AssetEntry.id).desc())
        .limit(1)
    ).first()


def signal(event_type: str, properties: dict[str, str | int | float]) -> dict:
    return {"event_type": event_type, "properties": properties}


def attach_signals(response: Response, signals: list[dict]) -> None:
    response.headers[REQUEST_ID_HEADER] = str(uuid4())
    if signals:
        response.headers[SIGNALS_HEADER] = json.dumps(signals, separators=(",", ":"))
