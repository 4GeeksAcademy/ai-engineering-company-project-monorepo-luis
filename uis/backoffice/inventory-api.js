/**
 * Nexova Backoffice — Centralized Inventory & Auth API Client
 * 
 * Enforces architectural constraints:
 * - Centralizes authenticated HTTP communication with FastAPI
 * - Strict prohibition of raw fetch() calls in components/views
 * - Sanitized error parsing for FastAPI 4xx/5xx responses (especially 400 insufficient stock)
 * - Session token management via sessionStorage without leaking credentials to console/logs
 */
(function (global) {
  "use strict";

  const STORAGE_KEYS = {
    TOKEN: "nexova_auth_token",
    USER: "nexova_auth_user",
  };

  const movementEvents = {
    inbound: new Set(["inbound_order_created", "kit_cost_variance_detected"]),
    outbound: new Set(["outbound_order_created", "stock_threshold_triggered"]),
    rejection: new Set(["direct_stock_edit_rejected"]),
  };

  const bursts = new Map();
  const windowSeconds = 60;

  function telemetryEnabled() {
    return Boolean(global.__TELEMETRY_ENDPOINT__ && global.Telemetry && global.crypto?.randomUUID);
  }

  function recordBurst(type, properties, requestId) {
    const key = JSON.stringify([type, properties]);
    const burst = bursts.get(key);
    if (burst) {
      if (burst.count === 0) burst.requestId = requestId;
      burst.count++;
      return;
    }
    if (bursts.size >= 64) return;
    const emit = (count, id) => global.Telemetry.track(type, {
      ...properties, occurrence_count: count, window_seconds: windowSeconds,
    }, id);
    const pending = { count: 0, requestId: null };
    bursts.set(key, pending);
    global.setTimeout(() => {
      bursts.delete(key);
      if (pending.count) emit(pending.count, pending.requestId);
    }, windowSeconds * 1000);
    emit(1, requestId);
  }

  function routeGroup(endpoint, method) {
    const path = endpoint.split(/[?#]/, 1)[0];
    if (path.startsWith("/auth/")) return "auth";
    if (path === "/inventory/orders/inbound") return "inbound_order";
    if (path === "/inventory/orders/outbound") return "outbound_order";
    if (method === "GET" && (path === "/inventory/orders" || path === "/inventory/products"
        || /^\/inventory\/products\/\d+$/.test(path))) return "inventory_read";
    if (path.startsWith("/api/incidents")) return "reporting";
    return "other";
  }

  function recordRequest(endpoint, method, started, response, error) {
    if (started === null) return;
    try {
      const receivedId = response?.headers.get("X-Request-ID");
      const requestId = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(receivedId ?? "")
        ? receivedId : global.crypto.randomUUID();
      const status = response?.status;
      const properties = {
        route_group: routeGroup(endpoint, method),
        http_method: ["GET", "POST", "PUT", "PATCH", "DELETE"].includes(method) ? method : "OTHER",
        status_code: Number.isInteger(status) && status >= 100 && status <= 599 ? status : null,
      };
      const duration = Math.max(0, global.performance.now() - started);
      const failed = !response?.ok;
      const sampleRate = failed || duration >= 1000 ? 1 : 0.1;
      // Use the same sampling decision for the same opaque request ID.
      let hash = 2166136261;
      for (const char of requestId) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619);
      if (sampleRate === 1 || (hash >>> 0) % 10 === 0) {
        global.Telemetry.track("api_latency_recorded", {
          ...properties, duration_ms: duration, sample_rate: sampleRate,
        }, requestId);
      }
      if (failed) {
        const errorCode = !response ? (error?.name === "TimeoutError" ? "timeout" : "network_error")
          : status >= 500 ? "server_error" : status >= 400 ? "client_error" : "other";
        recordBurst("api_request_failed", { ...properties, error_code: errorCode }, requestId);
      }
    } catch {
      global.console.warn("[telemetry] api_signal_unavailable");
    }
  }

  function captureMovement(response, kind) {
    if (!global.Telemetry || response.status !== (kind === "rejection" ? 409 : 201)) return;
    try {
      const header = response.headers.get("X-Inventory-Telemetry");
      if (!header) return;
      const requestId = response.headers.get("X-Request-ID");
      const seen = new Set();
      for (const { event_type, properties } of JSON.parse(header)) {
        if (!movementEvents[kind].has(event_type) || seen.has(event_type)) continue;
        seen.add(event_type);
        global.Telemetry.track(event_type, properties, requestId);
      }
    } catch {
      global.console.warn("[telemetry] invalid_inventory_signals");
    }
  }

  /**
   * Custom structured error for API failures
   */
  class ApiError extends Error {
    constructor(status, detail, message) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.detail = detail;
      this.isInsufficientStock = status === 400 && typeof detail === "string" && /stock|insuficiente|insufficient/i.test(detail);
    }
  }

  function resolveApiBaseUrl() {
    if (typeof window !== "undefined" && window.__API_BASE_URL__) {
      return window.__API_BASE_URL__;
    }
    if (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")) {
      return "http://127.0.0.1:8000";
    }
    return "";
  }

  function formatErrorMessage(status, detail) {
    if (typeof detail === "string" && detail.trim().length > 0) {
      return detail;
    }

    if (Array.isArray(detail)) {
      // Formato típico de errores de validación de Pydantic/FastAPI
      const messages = detail.map((err) => {
        const field = Array.isArray(err.loc)
          ? err.loc.filter((part) => part !== "body").join(".")
          : "campo";
        return field ? `${field}: ${err.msg}` : err.msg;
      });
      return messages.join("; ");
    }

    if (detail && typeof detail === "object" && detail.message) {
      return String(detail.message);
    }

    switch (status) {
      case 400:
        return "Solicitud incorrecta. Revisa los datos ingresados.";
      case 401:
        return "Credenciales incorrectas o sesión expirada. Inicia sesión para continuar.";
      case 403:
        return "No tienes autorización para realizar esta acción.";
      case 404:
        return "El recurso solicitado no fue encontrado.";
      case 422:
        return "Los datos proporcionados no superaron la validación del sistema.";
      case 500:
      case 502:
      case 503:
        return "El servicio de inventario no está disponible temporalmente. Inténtalo más tarde.";
      default:
        return `Error en la solicitud (${status}). Por favor intenta nuevamente.`;
    }
  }

  class InventoryApiClient {
    constructor(options = {}) {
      this.baseUrl = options.baseUrl || resolveApiBaseUrl();
      this._subscribers = new Set();
    }

    // ==========================================
    // Session & Token Management
    // ==========================================

    getToken() {
      try {
        return sessionStorage.getItem(STORAGE_KEYS.TOKEN);
      } catch (_) {
        return null;
      }
    }

    setToken(token) {
      try {
        if (token) {
          sessionStorage.setItem(STORAGE_KEYS.TOKEN, token);
        } else {
          sessionStorage.removeItem(STORAGE_KEYS.TOKEN);
        }
      } catch (_) {}
    }

    getUser() {
      try {
        const raw = sessionStorage.getItem(STORAGE_KEYS.USER);
        return raw ? JSON.parse(raw) : null;
      } catch (_) {
        return null;
      }
    }

    setUser(user) {
      try {
        if (user) {
          sessionStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
        } else {
          sessionStorage.removeItem(STORAGE_KEYS.USER);
        }
      } catch (_) {}
    }

    clearSession() {
      try {
        sessionStorage.removeItem(STORAGE_KEYS.TOKEN);
        sessionStorage.removeItem(STORAGE_KEYS.USER);
      } catch (_) {}
      this._notifyAuthChanged(null);
    }

    isAuthenticated() {
      return Boolean(this.getToken());
    }

    onAuthStateChanged(callback) {
      if (typeof callback === "function") {
        this._subscribers.add(callback);
      }
      return () => this._subscribers.delete(callback);
    }

    _notifyAuthChanged(user) {
      this._subscribers.forEach((cb) => {
        try {
          cb(user);
        } catch (_) {}
      });
    }

    // ==========================================
    // HTTP Request Core
    // ==========================================

    async request(endpoint, options = {}) {
      const { responseType = "json", movementKind, ...requestOptions } = options;
      const url = `${this.baseUrl}${endpoint}`;
      const headers = {
        Accept: "application/json",
        ...(requestOptions.headers || {}),
      };

      if (requestOptions.body && !(requestOptions.body instanceof FormData) && typeof requestOptions.body === "object") {
        headers["Content-Type"] = "application/json";
        requestOptions.body = JSON.stringify(requestOptions.body);
      }

      // Inyectar Authorization Bearer si no se especificó y tenemos token en sesión
      const token = this.getToken();
      if (token && !headers["Authorization"]) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      let response;
      const started = telemetryEnabled() && global.performance ? global.performance.now() : null;
      try {
        response = await fetch(url, {
          ...requestOptions,
          headers,
        });
      } catch (error) {
        recordRequest(endpoint, requestOptions.method || "GET", started, null, error);
        throw new ApiError(
          0,
          null,
          `No se pudo conectar con el servidor backend (${this.baseUrl}). Verifica que la API esté activa.`
        );
      }

      recordRequest(endpoint, requestOptions.method || "GET", started, response);
      if (movementKind) captureMovement(response, movementKind);

      if (response.ok && responseType === "blob") {
        return response.blob();
      }

      let data = null;
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        try {
          data = await response.json();
        } catch (_) {
          data = null;
        }
      } else {
        try {
          const text = await response.text();
          data = text ? { detail: text } : null;
        } catch (_) {
          data = null;
        }
      }

      if (!response.ok) {
        const detail = data && data.detail ? data.detail : null;
        const message = formatErrorMessage(response.status, detail);

        // Si el token expiró o fue rechazado con 401 en llamada autenticada, limpiar sesión
        if (response.status === 401 && token) {
          this.clearSession();
        }

        throw new ApiError(response.status, detail, message);
      }

      return data;
    }

    // ==========================================
    // Auth Endpoints
    // ==========================================

    /**
     * Iniciar sesión con email y contraseña (POST /auth/login)
     * Obtiene el token y perfil del usuario en una sola secuencia segura.
     */
    async login(email, password) {
      if (!email || !password) {
        throw new ApiError(400, "Campos requeridos", "Email y contraseña son obligatorios.");
      }

      let loginData;
      try {
        loginData = await this.request("/auth/login", {
          method: "POST",
          body: { email: email.trim(), password },
        });
      } catch (error) {
        if (telemetryEnabled()) {
          const failureCode = error.status === 401 ? "invalid_credentials"
            : error.status === 0 || error.status >= 500 ? "provider_unavailable" : "other";
          recordBurst("auth_login_failed", { auth_method: "password", failure_code: failureCode },
            global.crypto.randomUUID());
        }
        throw error;
      }

      const token = loginData.access_token;
      this.setToken(token);

      // Obtener datos del usuario autenticado
      let user = null;
      try {
        const meData = await this.getCurrentUser();
        user = meData.user || meData;
        this.setUser(user);
      } catch (_) {
        // En caso de que /auth/me falle, preservar al menos el email
        user = { email: email.trim() };
        this.setUser(user);
      }

      this._notifyAuthChanged(user);
      if (token && this.isAuthenticated() && telemetryEnabled()) {
        global.Telemetry.track("auth_login_succeeded", { auth_method: "password" });
      }
      return { token, user };
    }

    /**
     * Obtener el perfil y datos del usuario actual (GET /auth/me)
     */
    async getCurrentUser() {
      return this.request("/auth/me", { method: "GET" });
    }

    /**
     * Cerrar sesión activa
     */
    logout() {
      this.clearSession();
    }

    // ==========================================
    // Inventory Endpoints (/inventory)
    // ==========================================

    /**
     * Listar todos los activos con su stock calculado (GET /inventory/products)
     * @returns {Promise<Array<{ id: number, name: string, sku: string, category: string, office: string, current_stock: number }>>}
     */
    async getProducts() {
      return this.request("/inventory/products", { method: "GET" });
    }

    /**
     * Obtener un activo específico por ID (GET /inventory/products/{id})
     * @param {number} id
     */
    async getProductById(id) {
      const assetId = Number(id);
      if (!Number.isInteger(assetId) || assetId <= 0) {
        throw new ApiError(400, "ID inválido", "El ID del activo debe ser un número entero positivo.");
      }
      return this.request(`/inventory/products/${assetId}`, { method: "GET" });
    }

    /**
     * Registrar entrada de activo (POST /inventory/orders/inbound)
     * Requiere autenticación.
     * @param {{ asset_id: number, quantity: number, supplier: string, office: string }} payload
     */
    async createInboundOrder(payload) {
      return this.request("/inventory/orders/inbound", {
        movementKind: "inbound",
        method: "POST",
        body: payload,
      });
    }

    /**
     * Registrar salida de activo (POST /inventory/orders/outbound)
     * Requiere autenticación.
     * @param {{ asset_id: number, quantity: number, exit_type: 'allocation'|'consumption', assigned_to?: string|null, office: string }} payload
     */
    async createOutboundOrder(payload) {
      return this.request("/inventory/orders/outbound", {
        movementKind: "outbound",
        method: "POST",
        body: payload,
      });
    }

    async rejectDirectStockEdit(assetId, payload) {
      if (!Number.isSafeInteger(assetId) || assetId <= 0) {
        throw new ApiError(400, "ID inválido", "El ID del activo debe ser un entero positivo.");
      }
      return this.request(`/inventory/products/${assetId}/stock`, {
        movementKind: "rejection",
        method: "PATCH",
        body: payload,
      });
    }

    /**
     * Consultar historial de movimientos (GET /inventory/orders)
     * @returns {Promise<Array<OrderItemRead>>}
     */
    async getOrders() {
      return this.request("/inventory/orders", { method: "GET" });
    }
  }

  // Instancia única (singleton) para el backoffice
  const inventoryApiInstance = new InventoryApiClient();

  // Exportar al objeto global (navegador) o a CommonJS/Node (para pruebas automáticas)
  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      InventoryApiClient,
      ApiError,
      inventoryApi: inventoryApiInstance,
    };
  }

  if (typeof global !== "undefined") {
    global.InventoryApiClient = InventoryApiClient;
    global.ApiError = ApiError;
    global.inventoryApi = inventoryApiInstance;
  }
})(typeof window !== "undefined" ? window : globalThis);
