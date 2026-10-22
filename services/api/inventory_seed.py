"""Idempotent seed script for Nexova Inventory development data.

Seeds the minimum required entities specified in the Nexova briefing:
- 6 catalogued assets across Valencia and Miami offices
- At least 4 inbound asset entries
- At least 3 outbound asset exits (allocation with assigned_to and consumption with null)
- Idempotent execution: will not duplicate assets or movement records
"""

import sys
from pathlib import Path
from typing import Tuple

from sqlmodel import Session, select

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.api.database import get_engine, init_db
from services.api.models import Asset, AssetEntry, AssetExit

SEED_ASSETS = [
    {
        "name": "Portátil 14\" Business",
        "sku": "NXV-IT-001",
        "category": "hardware",
        "office": "Valencia",
    },
    {
        "name": "Portátil 14\" Business",
        "sku": "NXV-IT-002",
        "category": "hardware",
        "office": "Miami",
    },
    {
        "name": "Ratón ergonómico",
        "sku": "NXV-PER-001",
        "category": "peripherals",
        "office": "Valencia",
    },
    {
        "name": "Hub USB-C",
        "sku": "NXV-PER-002",
        "category": "peripherals",
        "office": "Miami",
    },
    {
        "name": "Resma de papel A4",
        "sku": "NXV-OFF-001",
        "category": "office_supplies",
        "office": "Valencia",
    },
    {
        "name": "Cuaderno de formación en liderazgo",
        "sku": "NXV-TRN-001",
        "category": "training_materials",
        "office": "Valencia",
    },
]

# Move definitions by asset SKU
SEED_ENTRIES = [
    {
        "sku": "NXV-IT-001",
        "quantity": 10,
        "supplier": "TechDistrib Valencia S.L.",
        "office": "Valencia",
        "user_uuid": "1",
    },
    {
        "sku": "NXV-IT-001",
        "quantity": 5,
        "supplier": "TechDistrib Valencia S.L.",
        "office": "Valencia",
        "user_uuid": "1",
    },
    {
        "sku": "NXV-PER-001",
        "quantity": 15,
        "supplier": "TechDistrib Valencia S.L.",
        "office": "Valencia",
        "user_uuid": "1",
    },
    {
        "sku": "NXV-PER-002",
        "quantity": 12,
        "supplier": "Office Depot Miami",
        "office": "Miami",
        "user_uuid": "1",
    },
    {
        "sku": "NXV-OFF-001",
        "quantity": 20,
        "supplier": "Papelería Valencia S.L.",
        "office": "Valencia",
        "user_uuid": "1",
    },
    {
        "sku": "NXV-IT-002",
        "quantity": 8,
        "supplier": "Office Depot Miami",
        "office": "Miami",
        "user_uuid": "1",
    },
]

SEED_EXITS = [
    {
        "sku": "NXV-IT-001",
        "quantity": 3,
        "exit_type": "allocation",
        "assigned_to": "Carlos Gómez",
        "office": "Valencia",
        "user_uuid": "1",
    },
    {
        "sku": "NXV-OFF-001",
        "quantity": 5,
        "exit_type": "consumption",
        "assigned_to": None,
        "office": "Valencia",
        "user_uuid": "1",
    },
    {
        "sku": "NXV-PER-001",
        "quantity": 2,
        "exit_type": "allocation",
        "assigned_to": "Ana Martínez",
        "office": "Valencia",
        "user_uuid": "1",
    },
]


def seed_inventory(session: Session | None = None) -> Tuple[int, int, int]:
    """Idempotently populate Nexova inventory seed data.
    
    Returns (assets_created, entries_created, exits_created).
    """
    engine = get_engine()
    init_db(target_engine=engine)

    def _execute_seed(s: Session) -> Tuple[int, int, int]:
        assets_created = 0
        entries_created = 0
        exits_created = 0

        # 1. Upsert / Seed Assets by SKU
        sku_to_asset: dict[str, Asset] = {}
        for item in SEED_ASSETS:
            existing = s.exec(select(Asset).where(Asset.sku == item["sku"])).first()
            if not existing:
                asset = Asset(
                    name=item["name"],
                    sku=item["sku"],
                    category=item["category"],
                    office=item["office"],
                )
                s.add(asset)
                s.commit()
                s.refresh(asset)
                sku_to_asset[item["sku"]] = asset
                assets_created += 1
            else:
                sku_to_asset[item["sku"]] = existing

        # 2. Seed Entries (Idempotent: check if entries already exist for these assets)
        existing_entries_count = s.exec(select(AssetEntry)).all()
        if not existing_entries_count:
            for entry_data in SEED_ENTRIES:
                asset = sku_to_asset[entry_data["sku"]]
                entry = AssetEntry(
                    asset_id=asset.id,
                    quantity=entry_data["quantity"],
                    supplier=entry_data["supplier"],
                    office=entry_data["office"],
                    user_uuid=entry_data["user_uuid"],
                )
                s.add(entry)
                entries_created += 1
            s.commit()

        # 3. Seed Exits (Idempotent: check if exits already exist)
        existing_exits_count = s.exec(select(AssetExit)).all()
        if not existing_exits_count:
            for exit_data in SEED_EXITS:
                asset = sku_to_asset[exit_data["sku"]]
                exit_item = AssetExit(
                    asset_id=asset.id,
                    quantity=exit_data["quantity"],
                    exit_type=exit_data["exit_type"],
                    assigned_to=exit_data["assigned_to"],
                    office=exit_data["office"],
                    user_uuid=exit_data["user_uuid"],
                )
                s.add(exit_item)
                exits_created += 1
            s.commit()

        return assets_created, entries_created, exits_created

    if session:
        return _execute_seed(session)
    else:
        with Session(engine) as s:
            return _execute_seed(s)


def main() -> int:
    try:
        assets, entries, exits = seed_inventory()
        print(
            "Nexova inventory seed complete: "
            f"{assets} assets created, {entries} entries recorded, {exits} exits recorded."
        )
        return 0
    except Exception as exc:
        print(f"Error seeding inventory: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
