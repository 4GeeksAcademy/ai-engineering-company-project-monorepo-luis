"""Unit tests for Nexova inventory service domain logic."""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from services.api.models import Asset, AssetEntry, AssetExit
from services.api.schemas import AssetCreate, AssetEntryCreate, AssetExitCreate
from services.api.inventory_service import (
    AssetNotFoundError,
    DuplicateSkuError,
    InsufficientStockError,
    calculate_asset_stock,
    create_asset,
    get_asset_by_id,
    get_asset_read,
    list_assets,
    list_orders,
    register_inbound_order,
    register_outbound_order,
)


@pytest.fixture
def session():
    """Create an isolated in-memory SQLite database session for service testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_create_asset_initial_stock_zero(session: Session):
    payload = AssetCreate(
        name="Portátil 14\" Business",
        sku="NXV-IT-001",
        category="hardware",
        office="Valencia",
    )
    asset_read = create_asset(session, payload)
    assert asset_read.id is not None
    assert asset_read.current_stock == 0

    stock = calculate_asset_stock(session, asset_read.id, "Valencia")
    assert stock == 0


def test_create_asset_duplicate_sku_fails(session: Session):
    payload = AssetCreate(
        name="Portátil 14\" Business",
        sku="NXV-IT-001",
        category="hardware",
        office="Valencia",
    )
    create_asset(session, payload)
    with pytest.raises(DuplicateSkuError) as exc_info:
        create_asset(session, payload)
    assert exc_info.value.status_code == 400
    assert "already exists" in exc_info.value.detail


def test_get_asset_not_found(session: Session):
    with pytest.raises(AssetNotFoundError) as exc_info:
        get_asset_by_id(session, 9999)
    assert exc_info.value.status_code == 404


def test_stock_calculation_and_office_isolation(session: Session):
    # Create two assets: one in Valencia, one in Miami
    asset_val = create_asset(
        session,
        AssetCreate(
            name="Portátil 14\" Business",
            sku="NXV-IT-001",
            category="hardware",
            office="Valencia",
        ),
    )
    asset_mia = create_asset(
        session,
        AssetCreate(
            name="Portátil 14\" Business",
            sku="NXV-IT-002",
            category="hardware",
            office="Miami",
        ),
    )

    # Inbound 10 to Valencia
    register_inbound_order(
        session,
        AssetEntryCreate(
            asset_id=asset_val.id,
            quantity=10,
            supplier="TechDistrib Valencia S.L.",
            office="Valencia",
        ),
        user_uuid="101",
    )

    # Inbound 5 more to Valencia
    register_inbound_order(
        session,
        AssetEntryCreate(
            asset_id=asset_val.id,
            quantity=5,
            supplier="TechDistrib Valencia S.L.",
            office="Valencia",
        ),
        user_uuid="101",
    )

    # Verify Valencia stock is 15
    assert calculate_asset_stock(session, asset_val.id, "Valencia") == 15
    # Verify Miami stock for this asset is 0
    assert calculate_asset_stock(session, asset_val.id, "Miami") == 0
    # Verify Miami asset has 0 stock
    assert calculate_asset_stock(session, asset_mia.id, "Miami") == 0

    # Inbound 8 to Miami asset in Miami
    register_inbound_order(
        session,
        AssetEntryCreate(
            asset_id=asset_mia.id,
            quantity=8,
            supplier="Office Depot Miami",
            office="Miami",
        ),
        user_uuid="102",
    )
    assert calculate_asset_stock(session, asset_mia.id, "Miami") == 8
    # Valencia stock remains 15
    assert calculate_asset_stock(session, asset_val.id, "Valencia") == 15


def test_register_outbound_insufficient_stock_exact_error_message(session: Session):
    asset = create_asset(
        session,
        AssetCreate(
            name="Ratón ergonómico",
            sku="NXV-PER-001",
            category="peripherals",
            office="Valencia",
        ),
    )

    # Add 5 units
    register_inbound_order(
        session,
        AssetEntryCreate(
            asset_id=asset.id,
            quantity=5,
            supplier="TechDistrib Valencia S.L.",
            office="Valencia",
        ),
        user_uuid="1",
    )

    # Attempt to exit 6 units (exceeds available 5)
    with pytest.raises(InsufficientStockError) as exc_info:
        register_outbound_order(
            session,
            AssetExitCreate(
                asset_id=asset.id,
                quantity=6,
                exit_type="allocation",
                assigned_to="Developer X",
                office="Valencia",
            ),
            user_uuid="1",
        )

    # Check status code and exact message required by Nexova
    assert exc_info.value.status_code == 400
    expected_msg = "Insufficient stock for asset 'Ratón ergonómico'. Available: 5, requested: 6."
    assert exc_info.value.detail == expected_msg

    # Verify no exit record was persisted and stock is still 5
    exits = session.exec(select(AssetExit).where(AssetExit.asset_id == asset.id)).all()
    assert len(exits) == 0
    assert calculate_asset_stock(session, asset.id, "Valencia") == 5


def test_register_outbound_success(session: Session):
    asset = create_asset(
        session,
        AssetCreate(
            name="Resma de papel A4",
            sku="NXV-OFF-001",
            category="office_supplies",
            office="Valencia",
        ),
    )

    # Inbound 20 units
    register_inbound_order(
        session,
        AssetEntryCreate(
            asset_id=asset.id,
            quantity=20,
            supplier="Papelería Valencia",
            office="Valencia",
        ),
        user_uuid="2",
    )

    # Outbound allocation of 5 units
    exit_item = register_outbound_order(
        session,
        AssetExitCreate(
            asset_id=asset.id,
            quantity=5,
            exit_type="allocation",
            assigned_to="Admin Office",
            office="Valencia",
        ),
        user_uuid="2",
    )
    assert exit_item.id is not None
    assert exit_item.quantity == 5
    assert exit_item.assigned_to == "Admin Office"

    # Outbound consumption of 3 units
    exit_item2 = register_outbound_order(
        session,
        AssetExitCreate(
            asset_id=asset.id,
            quantity=3,
            exit_type="consumption",
            assigned_to=None,
            office="Valencia",
        ),
        user_uuid="2",
    )
    assert exit_item2.exit_type == "consumption"
    assert exit_item2.assigned_to is None

    # Remaining stock: 20 - 5 - 3 = 12
    read_asset = get_asset_read(session, asset.id)
    assert read_asset.current_stock == 12


def test_list_assets_and_list_orders(session: Session):
    asset1 = create_asset(
        session,
        AssetCreate(
            name="Portátil 14\" Business",
            sku="NXV-IT-001",
            category="hardware",
            office="Valencia",
        ),
    )
    asset2 = create_asset(
        session,
        AssetCreate(
            name="Hub USB-C",
            sku="NXV-PER-002",
            category="peripherals",
            office="Miami",
        ),
    )

    # Movements
    register_inbound_order(
        session,
        AssetEntryCreate(
            asset_id=asset1.id,
            quantity=10,
            supplier="TechDistrib Valencia S.L.",
            office="Valencia",
        ),
        user_uuid="10",
    )
    register_inbound_order(
        session,
        AssetEntryCreate(
            asset_id=asset2.id,
            quantity=7,
            supplier="Office Depot Miami",
            office="Miami",
        ),
        user_uuid="11",
    )
    register_outbound_order(
        session,
        AssetExitCreate(
            asset_id=asset1.id,
            quantity=2,
            exit_type="allocation",
            assigned_to="Lead",
            office="Valencia",
        ),
        user_uuid="10",
    )

    # list_assets
    assets = list_assets(session)
    assert len(assets) == 2
    stock_map = {a.sku: a.current_stock for a in assets}
    assert stock_map["NXV-IT-001"] == 8
    assert stock_map["NXV-PER-002"] == 7

    # list_orders
    orders = list_orders(session)
    assert len(orders) == 3
    # Check that eager loaded asset fields are populated
    for order in orders:
        assert order.asset_name in ["Portátil 14\" Business", "Hub USB-C"]
        assert order.asset_sku in ["NXV-IT-001", "NXV-PER-002"]
        assert order.user_uuid in ["10", "11"]
