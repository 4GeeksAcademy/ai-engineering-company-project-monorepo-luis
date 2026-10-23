import test from "node:test";
import assert from "node:assert/strict";

// Mock sessionStorage for Node test environment
class MockSessionStorage {
  constructor() {
    this.store = new Map();
  }
  getItem(key) {
    return this.store.get(key) || null;
  }
  setItem(key, value) {
    this.store.set(key, String(value));
  }
  removeItem(key) {
    this.store.delete(key);
  }
  clear() {
    this.store.clear();
  }
}

globalThis.sessionStorage = new MockSessionStorage();

// Load inventory-api.js
await import("../inventory-api.js");
const { InventoryApiClient, ApiError, inventoryApi } = globalThis;

test("InventoryApiClient: token and session storage", () => {
  const client = new InventoryApiClient({ baseUrl: "http://test-server" });
  assert.equal(client.isAuthenticated(), false);
  assert.equal(client.getToken(), null);
  assert.equal(client.getUser(), null);

  client.setToken("fake-jwt-token");
  client.setUser({ id: 1, email: "admin@nexova.com", role: "admin" });

  assert.equal(client.isAuthenticated(), true);
  assert.equal(client.getToken(), "fake-jwt-token");
  assert.deepEqual(client.getUser(), { id: 1, email: "admin@nexova.com", role: "admin" });

  let notifyCount = 0;
  const unsubscribe = client.onAuthStateChanged((user) => {
    assert.equal(user, null);
    notifyCount++;
  });

  client.logout();
  assert.equal(client.isAuthenticated(), false);
  assert.equal(client.getToken(), null);
  assert.equal(client.getUser(), null);
  assert.equal(notifyCount, 1);

  unsubscribe();
});

test("InventoryApiClient: error formatting & ApiError classification", async () => {
  // Test 400 with insufficient stock
  const stockErr = new ApiError(400, "Insufficient stock for asset in Valencia: requested 10, available 3", "Stock insuficiente");
  assert.equal(stockErr.status, 400);
  assert.equal(stockErr.isInsufficientStock, true);

  // Test 422 validation detail array
  const client = new InventoryApiClient({ baseUrl: "http://test-server" });
  
  // Custom fetch mock for 422
  globalThis.fetch = async () => ({
    ok: false,
    status: 422,
    headers: { get: () => "application/json" },
    json: async () => ({
      detail: [
        { loc: ["body", "quantity"], msg: "Input should be greater than 0" },
        { loc: ["body", "office"], msg: "Input should be 'Valencia' or 'Miami'" },
      ],
    }),
  });

  await assert.rejects(
    async () => client.createInboundOrder({ quantity: -1 }),
    (err) => {
      assert(err instanceof ApiError);
      assert.equal(err.status, 422);
      assert(err.message.includes("quantity: Input should be greater than 0"));
      assert(err.message.includes("office: Input should be 'Valencia' or 'Miami'"));
      return true;
    }
  );
});

test("InventoryApiClient: sends Bearer token in authenticated calls", async () => {
  const client = new InventoryApiClient({ baseUrl: "http://test-server" });
  client.setToken("valid-token-123");

  let recordedHeaders = null;
  globalThis.fetch = async (url, options) => {
    recordedHeaders = options.headers;
    return {
      ok: true,
      status: 201,
      headers: { get: () => "application/json" },
      json: async () => ({ id: 99, asset_id: 1, quantity: 5, supplier: "Nexova Tech", office: "Valencia" }),
    };
  };

  const result = await client.createInboundOrder({
    asset_id: 1,
    quantity: 5,
    supplier: "Nexova Tech",
    office: "Valencia",
  });

  assert.equal(result.id, 99);
  assert.equal(recordedHeaders["Authorization"], "Bearer valid-token-123");
  assert.equal(recordedHeaders["Content-Type"], "application/json");
});

test("InventoryApiClient: handles network failure gracefully", async () => {
  const client = new InventoryApiClient({ baseUrl: "http://unreachable-backend" });
  globalThis.fetch = async () => {
    throw new TypeError("Failed to fetch");
  };

  await assert.rejects(
    async () => client.getProducts(),
    (err) => {
      assert(err instanceof ApiError);
      assert.equal(err.status, 0);
      assert(err.message.includes("No se pudo conectar con el servidor backend"));
      return true;
    }
  );
});

test("InventoryApiClient: clears session on 401 response", async () => {
  const client = new InventoryApiClient({ baseUrl: "http://test-server" });
  client.setToken("expired-token");
  client.setUser({ email: "user@example.com" });

  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    headers: { get: () => "application/json" },
    json: async () => ({ detail: "Could not validate credentials" }),
  });

  await assert.rejects(
    async () => client.createOutboundOrder({ asset_id: 1, quantity: 1, exit_type: "consumption", office: "Valencia" }),
    (err) => {
      assert.equal(err.status, 401);
      return true;
    }
  );

  // Token should be wiped
  assert.equal(client.getToken(), null);
  assert.equal(client.getUser(), null);
  assert.equal(client.isAuthenticated(), false);
});

test("InventoryApiClient: inventory CRUD calls match API contract", async () => {
  const client = new InventoryApiClient({ baseUrl: "http://test-server" });
  const calls = [];

  globalThis.fetch = async (url, options) => {
    calls.push({ url, method: options.method, body: options.body });
    return {
      ok: true,
      status: 200,
      headers: { get: () => "application/json" },
      json: async () => [{ id: 1, name: "Dell Latitude 5540", sku: "NEX-HW-001", current_stock: 12 }],
    };
  };

  const products = await client.getProducts();
  assert.equal(products.length, 1);
  assert.equal(calls[0].url, "http://test-server/inventory/products");
  assert.equal(calls[0].method, "GET");

  await client.getProductById(1);
  assert.equal(calls[1].url, "http://test-server/inventory/products/1");

  await client.getOrders();
  assert.equal(calls[2].url, "http://test-server/inventory/orders");
});

test("InventoryApiClient: login sets token and user profile", async () => {
  const client = new InventoryApiClient({ baseUrl: "http://test-server" });

  globalThis.fetch = async (url) => {
    if (url.endsWith("/auth/login")) {
      return {
        ok: true,
        status: 200,
        headers: { get: () => "application/json" },
        json: async () => ({ access_token: "jwt-token-xyz", token_type: "bearer" }),
      };
    }
    if (url.endsWith("/auth/me")) {
      return {
        ok: true,
        status: 200,
        headers: { get: () => "application/json" },
        json: async () => ({
          user: { id: 7, email: "operaciones@nexova.com", role: "admin" },
          profile: { name: "Operaciones Nexova" },
        }),
      };
    }
    throw new Error("Unexpected url: " + url);
  };

  const { token, user } = await client.login("operaciones@nexova.com", "SecretPass123!");
  assert.equal(token, "jwt-token-xyz");
  assert.equal(user.email, "operaciones@nexova.com");
  assert.equal(client.isAuthenticated(), true);
  assert.equal(client.getToken(), "jwt-token-xyz");
});
