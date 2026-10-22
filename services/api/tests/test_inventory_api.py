"""Integration tests for Nexova /inventory API endpoints and TinyDB authentication."""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from pydantic import SecretStr

from services.api.auth_dependencies import get_current_user
from services.api.auth_models import UserRecord, UserRole
from services.api.database import get_db, set_engine
from services.api.main import app


# Mock authenticated users
MOCK_USER_VALENCIA = UserRecord(
    id=42,
    email="valencia.agent@nexova.com",
    role=UserRole.USER,
    is_active=True,
    created_at=datetime.now(timezone.utc),
    hashed_password=SecretStr("mock-hashed-password"),
)

MOCK_USER_MIAMI = UserRecord(
    id=84,
    email="miami.agent@nexova.com",
    role=UserRole.USER,
    is_active=True,
    created_at=datetime.now(timezone.utc),
    hashed_password=SecretStr("mock-hashed-password"),
)


from sqlalchemy.pool import StaticPool

@pytest.fixture
def client(monkeypatch):
    """Test client using an isolated in-memory SQLite database and test JWT settings."""
    monkeypatch.setenv("JWT_SECRET_KEY", "this-is-a-very-long-test-secret-key-with-over-32-bytes")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    set_engine(test_engine)

    def override_get_db():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    # Clear any previous auth override
    app.dependency_overrides.pop(get_current_user, None)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    set_engine(None)


def test_get_products_empty(client: TestClient):
    response = client.get("/inventory/products")
    assert response.status_code == 200
    assert response.json() == []


def test_create_product_requires_auth(client: TestClient):
    payload = {
        "name": "Portátil 14\" Business",
        "sku": "NXV-IT-001",
        "category": "hardware",
        "office": "Valencia",
    }
    response = client.post("/inventory/products", json=payload)
    assert response.status_code == 401


def test_create_product_success(client: TestClient):
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER_VALENCIA

    payload = {
        "name": "Portátil 14\" Business",
        "sku": "NXV-IT-001",
        "category": "hardware",
        "office": "Valencia",
    }
    response = client.post("/inventory/products", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "Portátil 14\" Business"
    assert data["sku"] == "NXV-IT-001"
    assert data["current_stock"] == 0


def test_create_product_duplicate_sku_fails(client: TestClient):
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER_VALENCIA

    payload = {
        "name": "Portátil 14\" Business",
        "sku": "NXV-IT-001",
        "category": "hardware",
        "office": "Valencia",
    }
    res1 = client.post("/inventory/products", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/inventory/products", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_create_product_forbids_client_managed_fields(client: TestClient):
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER_VALENCIA

    payload = {
        "name": "Portátil 14\" Business",
        "sku": "NXV-IT-001",
        "category": "hardware",
        "office": "Valencia",
        "current_stock": 50,  # forbidden
    }
    response = client.post("/inventory/products", json=payload)
    assert response.status_code == 422


def test_get_product_by_id(client: TestClient):
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER_VALENCIA

    create_res = client.post(
        "/inventory/products",
        json={
            "name": "Ratón ergonómico",
            "sku": "NXV-PER-001",
            "category": "peripherals",
            "office": "Valencia",
        },
    )
    asset_id = create_res.json()["id"]

    get_res = client.get(f"/inventory/products/{asset_id}")
    assert get_res.status_code == 200
    assert get_res.json()["sku"] == "NXV-PER-001"
    assert get_res.json()["current_stock"] == 0

    not_found = client.get("/inventory/products/99999")
    assert not_found.status_code == 404


def test_inbound_order_lifecycle(client: TestClient):
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER_VALENCIA

    create_res = client.post(
        "/inventory/products",
        json={
            "name": "Ratón ergonómico",
            "sku": "NXV-PER-001",
            "category": "peripherals",
            "office": "Valencia",
        },
    )
    asset_id = create_res.json()["id"]

    # Inbound requires auth
    app.dependency_overrides.pop(get_current_user)
    inbound_payload = {
        "asset_id": asset_id,
        "quantity": 10,
        "supplier": "TechDistrib Valencia S.L.",
        "office": "Valencia",
    }
    unauth_res = client.post("/inventory/orders/inbound", json=inbound_payload)
    assert unauth_res.status_code == 401

    # Inbound with auth
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER_VALENCIA
    inbound_res = client.post("/inventory/orders/inbound", json=inbound_payload)
    assert inbound_res.status_code == 201
    inbound_data = inbound_res.json()
    assert inbound_data["quantity"] == 10
    assert inbound_data["user_uuid"] == "42"  # String representation of user ID

    # Stock should now be 10
    stock_res = client.get(f"/inventory/products/{asset_id}")
    assert stock_res.json()["current_stock"] == 10


def test_outbound_order_validation_and_insufficient_stock(client: TestClient):
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER_VALENCIA

    # 1. Create asset
    asset_res = client.post(
        "/inventory/products",
        json={
            "name": "Portátil 14\" Business",
            "sku": "NXV-IT-001",
            "category": "hardware",
            "office": "Valencia",
        },
    )
    asset_id = asset_res.json()["id"]

    # 2. Add 5 units inbound
    client.post(
        "/inventory/orders/inbound",
        json={
            "asset_id": asset_id,
            "quantity": 5,
            "supplier": "TechDistrib Valencia S.L.",
            "office": "Valencia",
        },
    )

    # 3. Outbound schema validation: allocation without assigned_to
    invalid_allocation = {
        "asset_id": asset_id,
        "quantity": 2,
        "exit_type": "allocation",
        "assigned_to": None,
        "office": "Valencia",
    }
    assert client.post("/inventory/orders/outbound", json=invalid_allocation).status_code == 422

    # 4. Outbound schema validation: consumption with assigned_to
    invalid_consumption = {
        "asset_id": asset_id,
        "quantity": 1,
        "exit_type": "consumption",
        "assigned_to": "Someone",
        "office": "Valencia",
    }
    assert client.post("/inventory/orders/outbound", json=invalid_consumption).status_code == 422

    # 5. Outbound exceeding available stock (requested 6 > available 5)
    over_limit_payload = {
        "asset_id": asset_id,
        "quantity": 6,
        "exit_type": "allocation",
        "assigned_to": "Employee A",
        "office": "Valencia",
    }
    fail_res = client.post("/inventory/orders/outbound", json=over_limit_payload)
    assert fail_res.status_code == 400
    expected_error = "Insufficient stock for asset 'Portátil 14\" Business'. Available: 5, requested: 6."
    assert fail_res.json()["detail"] == expected_error

    # Verify stock remained 5
    assert client.get(f"/inventory/products/{asset_id}").json()["current_stock"] == 5

    # 6. Valid outbound within stock (quantity 3 <= 5)
    valid_payload = {
        "asset_id": asset_id,
        "quantity": 3,
        "exit_type": "allocation",
        "assigned_to": "Employee A",
        "office": "Valencia",
    }
    success_res = client.post("/inventory/orders/outbound", json=valid_payload)
    assert success_res.status_code == 201
    assert success_res.json()["user_uuid"] == "42"

    # Stock should now be 2 (5 - 3)
    assert client.get(f"/inventory/products/{asset_id}").json()["current_stock"] == 2


def test_office_isolation_via_api(client: TestClient):
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER_VALENCIA

    # Create asset in Valencia
    asset_res = client.post(
        "/inventory/products",
        json={
            "name": "Portátil 14\" Business",
            "sku": "NXV-IT-001",
            "category": "hardware",
            "office": "Valencia",
        },
    )
    asset_id = asset_res.json()["id"]

    # Inbound 10 to Valencia
    client.post(
        "/inventory/orders/inbound",
        json={
            "asset_id": asset_id,
            "quantity": 10,
            "supplier": "TechDistrib Valencia S.L.",
            "office": "Valencia",
        },
    )

    # Attempt to exit 2 from Miami (no stock in Miami)
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER_MIAMI
    miami_exit = {
        "asset_id": asset_id,
        "quantity": 2,
        "exit_type": "consumption",
        "assigned_to": None,
        "office": "Miami",
    }
    res = client.post("/inventory/orders/outbound", json=miami_exit)
    assert res.status_code == 400
    expected_msg = "Insufficient stock for asset 'Portátil 14\" Business'. Available: 0, requested: 2."
    assert res.json()["detail"] == expected_msg


def test_get_orders_list(client: TestClient):
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER_VALENCIA

    # Asset
    asset_res = client.post(
        "/inventory/products",
        json={
            "name": "Hub USB-C",
            "sku": "NXV-PER-002",
            "category": "peripherals",
            "office": "Miami",
        },
    )
    asset_id = asset_res.json()["id"]

    # Inbound
    client.post(
        "/inventory/orders/inbound",
        json={
            "asset_id": asset_id,
            "quantity": 15,
            "supplier": "Office Depot Miami",
            "office": "Miami",
        },
    )

    # Outbound
    client.post(
        "/inventory/orders/outbound",
        json={
            "asset_id": asset_id,
            "quantity": 4,
            "exit_type": "consumption",
            "assigned_to": None,
            "office": "Miami",
        },
    )

    # List orders
    orders_res = client.get("/inventory/orders")
    assert orders_res.status_code == 200
    orders = orders_res.json()
    assert len(orders) == 2

    # Verify eager loaded asset fields and user_uuid
    movement_types = {o["movement_type"] for o in orders}
    assert movement_types == {"inbound", "outbound"}
    for order in orders:
        assert order["asset_name"] == "Hub USB-C"
        assert order["asset_sku"] == "NXV-PER-002"
        assert order["user_uuid"] == "42"
