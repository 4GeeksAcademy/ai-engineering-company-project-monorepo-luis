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
    assert client.get("/inventory/orders").json() == []
    spec = client.get("/openapi.json").json()
    routes = {
        ("/inventory/products", "get"): ("200", "AssetRead", True),
        ("/inventory/products", "post"): ("201", "AssetRead", False),
        ("/inventory/products/{id}", "get"): ("200", "AssetRead", False),
        ("/inventory/orders/inbound", "post"): ("201", "AssetEntryRead", False),
        ("/inventory/orders/outbound", "post"): ("201", "AssetExitRead", False),
        ("/inventory/orders", "get"): ("200", "OrderItemRead", True),
    }
    for (path, method), (code, model, is_list) in routes.items():
        operation = spec["paths"][path][method]
        schema = operation["responses"][code]["content"]["application/json"]["schema"]
        if is_list:
            assert schema["type"] == "array"
            schema = schema["items"]
        assert schema["$ref"].endswith(f"/{model}")
        assert bool(operation.get("security")) == (method == "post")
        for error_code in ("500",) + (("401",) if method == "post" else ()):
            error = operation["responses"][error_code]["content"]["application/json"]["schema"]
            assert error["$ref"].endswith("/DetailErrorResponse")
        if "{id}" in path or "/orders/" in path:
            assert "404" in operation["responses"]
        if method == "post" and path in ("/inventory/products", "/inventory/orders/outbound"):
            assert "400" in operation["responses"]
        if method == "post" or "{id}" in path:
            assert "422" in operation["responses"]
    for model in ("AssetCreate", "AssetEntryCreate", "AssetExitCreate"):
        schema = spec["components"]["schemas"][model]
        assert schema["additionalProperties"] is False
        assert not {"id", "created_at", "user_uuid", "current_stock"} & schema["properties"].keys()


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
    assert set(data) == {"id", "name", "sku", "category", "office", "current_stock"}
    assert {key: data[key] for key in payload} == payload
    app.dependency_overrides.pop(get_current_user)
    assert client.get("/inventory/products").json() == [data]
    assert client.get(f"/inventory/products/{data['id']}").json() == data


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
    assert get_res.json() == create_res.json()

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
    assert set(inbound_data) == set(inbound_payload) | {"id", "created_at", "user_uuid"}
    assert {key: inbound_data[key] for key in inbound_payload} == inbound_payload
    datetime.fromisoformat(inbound_data["created_at"])
    for field, value in (("id", 99), ("created_at", "2030-01-02T03:04:05"), ("user_uuid", "84"), ("current_stock", 99)):
        rejected = client.post("/inventory/orders/inbound", json={**inbound_payload, field: value})
        assert rejected.status_code == 422
    assert client.post("/inventory/orders/inbound", json={**inbound_payload, "asset_id": 99999}).status_code == 404

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
    outbound_data = success_res.json()
    assert set(outbound_data) == set(valid_payload) | {"id", "created_at", "user_uuid"}
    assert {key: outbound_data[key] for key in valid_payload} == valid_payload
    datetime.fromisoformat(outbound_data["created_at"])
    for field, value in (("id", 99), ("created_at", "2030-01-02T03:04:05"), ("user_uuid", "84"), ("current_stock", 99)):
        assert client.post("/inventory/orders/outbound", json={**valid_payload, field: value}).status_code == 422
    assert client.post("/inventory/orders/outbound", json={**valid_payload, "asset_id": 99999}).status_code == 404
    app.dependency_overrides.pop(get_current_user)
    assert client.post("/inventory/orders/outbound", json=valid_payload).status_code == 401

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
    app.dependency_overrides.pop(get_current_user)
    orders_res = client.get("/inventory/orders")
    assert orders_res.status_code == 200
    orders = orders_res.json()
    assert len(orders) == 2

    # Verify eager loaded asset fields and user_uuid
    movement_types = {o["movement_type"] for o in orders}
    assert movement_types == {"inbound", "outbound"}
    for order in orders:
        assert set(order) == {
            "id", "movement_type", "asset_id", "asset_name", "asset_sku", "quantity",
            "office", "supplier", "exit_type", "assigned_to", "created_at", "user_uuid",
        }
        assert order["asset_id"] == asset_id
        assert order["asset_name"] == "Hub USB-C"
        assert order["asset_sku"] == "NXV-PER-002"
        assert order["user_uuid"] == "42"
        datetime.fromisoformat(order["created_at"])
        if order["movement_type"] == "inbound":
            assert order["supplier"] == "Office Depot Miami"
            assert order["quantity"] == 15
            assert order["exit_type"] is None
        else:
            assert order["supplier"] is None
            assert order["exit_type"] == "consumption"
            assert order["quantity"] == 4
        assert order["assigned_to"] is None
    assert orders == sorted(orders, key=lambda order: (order["created_at"], order["id"]), reverse=True)
    assert client.get(f"/inventory/products/{asset_id}").json()["current_stock"] == 11
