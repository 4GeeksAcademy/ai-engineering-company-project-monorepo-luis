/**
 * Nexova Backoffice — Centralized Inventory & Auth API Client
 * 
 * Enforces architectural constraints:
 * - Centralizes all HTTP communication with FastAPI (/inventory and /auth)
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
      const url = `${this.baseUrl}${endpoint}`;
      const headers = {
        Accept: "application/json",
        ...(options.headers || {}),
      };

      if (options.body && !(options.body instanceof FormData) && typeof options.body === "object") {
        headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(options.body);
      }

      // Inyectar Authorization Bearer si no se especificó y tenemos token en sesión
      const token = this.getToken();
      if (token && !headers["Authorization"]) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      let response;
      try {
        response = await fetch(url, {
          ...options,
          headers,
        });
      } catch (_) {
        throw new ApiError(
          0,
          null,
          `No se pudo conectar con el servidor backend (${this.baseUrl}). Verifica que la API esté activa.`
        );
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

      const loginData = await this.request("/auth/login", {
        method: "POST",
        body: { email: email.trim(), password },
      });

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
        method: "POST",
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
