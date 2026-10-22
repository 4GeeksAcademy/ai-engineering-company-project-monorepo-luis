"""Unit tests for Nexova inventory SQLModel models and Pydantic schemas."""

import pytest
from pydantic import ValidationError
from sqlmodel import Session, SQLModel, create_engine, select

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


# ==========================================
# Schema Tests
# ==========================================

def test_asset_create_valid():
    payload = {
        "name": "Portátil 14\" Business",
        "sku": "NXV-IT-001",
        "category": "hardware",
        "office": "Valencia",
    }
    asset = AssetCreate(**payload)
    assert asset.name == "Portátil 14\" Business"
    assert asset.category == "hardware"
    assert asset.office == "Valencia"


def test_asset_create_invalid_category():
    with pytest.raises(ValidationError):
        AssetCreate(
            name="Test",
            sku="SKU-1",
            category="furniture",  # Not in allowed categories
            office="Valencia",
        )


def test_asset_create_invalid_office():
    with pytest.raises(ValidationError):
        AssetCreate(
            name="Test",
            sku="SKU-1",
            category="hardware",
            office="Madrid",  # Not Valencia or Miami
        )


def test_asset_create_forbids_extra_fields():
    with pytest.raises(ValidationError):
        AssetCreate(
            name="Test",
            sku="SKU-1",
            category="hardware",
            office="Valencia",
            current_stock=10,  # Forbidden
        )
    with pytest.raises(ValidationError):
        AssetCreate(
            name="Test",
            sku="SKU-1",
            category="hardware",
            office="Valencia",
            id=1,  # Forbidden
        )


def test_asset_read_serialization():
    data = {
        "id": 1,
        "name": "Ratón ergonómico",
        "sku": "NXV-PER-001",
        "category": "peripherals",
        "office": "Valencia",
        "current_stock": 15,
    }
    asset_read = AssetRead(**data)
    assert asset_read.id == 1
    assert asset_read.current_stock == 15


def test_asset_entry_create_valid():
    entry = AssetEntryCreate(
        asset_id=1,
        quantity=10,
        supplier="TechDistrib Valencia S.L.",
        office="Valencia",
    )
    assert entry.quantity == 10
    assert entry.supplier == "TechDistrib Valencia S.L."


def test_asset_entry_create_non_positive_quantity():
    with pytest.raises(ValidationError):
        AssetEntryCreate(
            asset_id=1,
            quantity=0,
            supplier="Supplier",
            office="Valencia",
        )
    with pytest.raises(ValidationError):
        AssetEntryCreate(
            asset_id=1,
            quantity=-5,
            supplier="Supplier",
            office="Valencia",
        )


def test_asset_exit_create_allocation_valid():
    exit_item = AssetExitCreate(
        asset_id=1,
        quantity=2,
        exit_type="allocation",
        assigned_to="Dev Team Lead",
        office="Valencia",
    )
    assert exit_item.exit_type == "allocation"
    assert exit_item.assigned_to == "Dev Team Lead"


def test_asset_exit_create_allocation_requires_assigned_to():
    with pytest.raises(ValidationError, match="assigned_to.*required"):
        AssetExitCreate(
            asset_id=1,
            quantity=2,
            exit_type="allocation",
            assigned_to=None,
            office="Valencia",
        )
    with pytest.raises(ValidationError, match="assigned_to.*required"):
        AssetExitCreate(
            asset_id=1,
            quantity=2,
            exit_type="allocation",
            assigned_to="   ",
            office="Valencia",
        )


def test_asset_exit_create_consumption_valid():
    exit_item = AssetExitCreate(
        asset_id=1,
        quantity=1,
        exit_type="consumption",
        assigned_to=None,
        office="Miami",
    )
    assert exit_item.exit_type == "consumption"
    assert exit_item.assigned_to is None


def test_asset_exit_create_consumption_must_not_have_assigned_to():
    with pytest.raises(ValidationError, match="assigned_to.*must be null"):
        AssetExitCreate(
            asset_id=1,
            quantity=1,
            exit_type="consumption",
            assigned_to="Someone",
            office="Miami",
        )


def test_asset_exit_create_non_positive_quantity():
    with pytest.raises(ValidationError):
        AssetExitCreate(
            asset_id=1,
            quantity=0,
            exit_type="consumption",
            office="Valencia",
        )


# ==========================================
# SQLModel ORM Model Tests
# ==========================================

@pytest.fixture
def in_memory_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_sqlmodel_asset_persistence(in_memory_session: Session):
    asset = Asset(
        name="Hub USB-C",
        sku="NXV-PER-002",
        category="peripherals",
        office="Miami",
    )
    in_memory_session.add(asset)
    in_memory_session.commit()
    in_memory_session.refresh(asset)

    assert asset.id is not None
    assert asset.id > 0
    assert asset.sku == "NXV-PER-002"

    retrieved = in_memory_session.exec(select(Asset).where(Asset.sku == "NXV-PER-002")).first()
    assert retrieved is not None
    assert retrieved.name == "Hub USB-C"


def test_sqlmodel_entries_and_exits_relationships(in_memory_session: Session):
    asset = Asset(
        name="Portátil 14\" Business",
        sku="NXV-IT-001",
        category="hardware",
        office="Valencia",
    )
    in_memory_session.add(asset)
    in_memory_session.commit()
    in_memory_session.refresh(asset)

    entry = AssetEntry(
        asset_id=asset.id,
        quantity=10,
        supplier="TechDistrib Valencia S.L.",
        office="Valencia",
        user_uuid="1",
    )
    exit_item = AssetExit(
        asset_id=asset.id,
        quantity=2,
        exit_type="allocation",
        assigned_to="Carlos Dev",
        office="Valencia",
        user_uuid="1",
    )
    in_memory_session.add(entry)
    in_memory_session.add(exit_item)
    in_memory_session.commit()

    in_memory_session.refresh(asset)
    assert len(asset.entries) == 1
    assert asset.entries[0].quantity == 10
    assert asset.entries[0].supplier == "TechDistrib Valencia S.L."

    assert len(asset.exits) == 1
    assert asset.exits[0].quantity == 2
    assert asset.exits[0].exit_type == "allocation"
    assert asset.exits[0].assigned_to == "Carlos Dev"
