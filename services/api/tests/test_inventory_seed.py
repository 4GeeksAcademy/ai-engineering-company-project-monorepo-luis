"""Unit tests for Nexova inventory seed data and idempotency."""

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from services.api.database import set_engine
from services.api.inventory_seed import seed_inventory
from services.api.inventory_service import calculate_asset_stock
from services.api.models import Asset, AssetEntry, AssetExit


@pytest.fixture
def session():
    """Isolated in-memory SQLite session with StaticPool."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    set_engine(test_engine)

    with Session(test_engine) as s:
        yield s

    set_engine(None)


def test_seed_inventory_minimum_requirements_and_net_stocks(session: Session):
    assets_c, entries_c, exits_c = seed_inventory(session)

    # 1. Minimum counts check
    assert assets_c == 6
    assert entries_c >= 4  # briefing requires at least 4 entries
    assert exits_c >= 3    # briefing requires at least 3 exits

    # 2. Verify all 6 assets exist
    assets = session.exec(select(Asset)).all()
    assert len(assets) == 6
    sku_map = {a.sku: a for a in assets}

    expected_skus = [
        "NXV-IT-001",
        "NXV-IT-002",
        "NXV-PER-001",
        "NXV-PER-002",
        "NXV-OFF-001",
        "NXV-TRN-001",
    ]
    for sku in expected_skus:
        assert sku in sku_map

    # 3. Verify net derived stocks
    # NXV-IT-001 in Valencia: (10 + 5) - 3 = 12
    stock_it_val = calculate_asset_stock(session, sku_map["NXV-IT-001"].id, "Valencia")
    assert stock_it_val == 12

    # NXV-IT-002 in Miami: 8 - 0 = 8
    stock_it_mia = calculate_asset_stock(session, sku_map["NXV-IT-002"].id, "Miami")
    assert stock_it_mia == 8

    # NXV-PER-001 in Valencia: 15 - 2 = 13
    stock_per_val = calculate_asset_stock(session, sku_map["NXV-PER-001"].id, "Valencia")
    assert stock_per_val == 13

    # NXV-PER-002 in Miami: 12 - 0 = 12
    stock_per_mia = calculate_asset_stock(session, sku_map["NXV-PER-002"].id, "Miami")
    assert stock_per_mia == 12

    # NXV-OFF-001 in Valencia: 20 - 5 = 15
    stock_off_val = calculate_asset_stock(session, sku_map["NXV-OFF-001"].id, "Valencia")
    assert stock_off_val == 15

    # 4. Verify exit types (at least one allocation with assigned_to, and one consumption with None)
    exits = session.exec(select(AssetExit)).all()
    allocations = [e for e in exits if e.exit_type == "allocation"]
    consumptions = [e for e in exits if e.exit_type == "consumption"]

    assert len(allocations) >= 1
    assert any(a.assigned_to for a in allocations)

    assert len(consumptions) >= 1
    assert any(c.assigned_to is None for c in consumptions)


def test_seed_inventory_idempotency(session: Session):
    # First execution
    a1, e1, x1 = seed_inventory(session)
    assert a1 == 6
    assert e1 == 6
    assert x1 == 3

    # Second execution on the same database
    a2, e2, x2 = seed_inventory(session)
    assert a2 == 0
    assert e2 == 0
    assert x2 == 0

    # Total counts remain identical
    assert len(session.exec(select(Asset)).all()) == 6
    assert len(session.exec(select(AssetEntry)).all()) == 6
    assert len(session.exec(select(AssetExit)).all()) == 3
