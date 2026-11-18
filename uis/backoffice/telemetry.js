(function (global) {
  "use strict";

  const MAX_EVENTS = 500;
  const MAX_EVENT_BYTES = 8192;
  const BATCH_SIZE = 20;
  const KEEPALIVE_BYTES = 60 * 1024;
  const SESSION_KEY = "nexova_telemetry_session_id";
  const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const warned = new Set();
  const queue = [];
  let active = null;
  let flushDue = false;
  let hidden = global.document.visibilityState === "hidden";
  let hiddenBytes = 0;
  let sessionId = null;

  function warn(code) {
    if (!warned.has(code)) {
      warned.add(code);
      global.console.warn(`[telemetry] ${code}`);
    }
  }

  function endpointUrl() {
    const configured = global.__TELEMETRY_ENDPOINT__;
    if (!configured) {
      warn("endpoint_not_configured");
      return null;
    }
    try {
      const url = new URL(configured, global.location.href);
      if (!["http:", "https:"].includes(url.protocol) || url.username || url.password
          || url.search || url.hash) {
        warn("invalid_endpoint");
        return null;
      }
      return url.href;
    } catch {
      warn("invalid_endpoint");
      return null;
    }
  }

  const endpoint = endpointUrl();
  const definitions = new Map(
    (global.__NEXOVA_TELEMETRY_REGISTRY__ || []).map((event) => [event.event_type, event.properties])
  );
  if (!definitions.size) warn("contract_unavailable");

  function uuid() {
    if (!global.crypto || typeof global.crypto.randomUUID !== "function") {
      warn("uuid_unavailable");
      return null;
    }
    return global.crypto.randomUUID();
  }

  function authenticated() {
    return Boolean(global.inventoryApi && global.inventoryApi.isAuthenticated());
  }

  function updateSession(rotate = false) {
    try {
      if (!authenticated()) {
        sessionId = null;
        global.sessionStorage.removeItem(SESSION_KEY);
      } else {
        const stored = rotate ? null : global.sessionStorage.getItem(SESSION_KEY);
        sessionId = stored && uuidPattern.test(stored) ? stored : (rotate ? uuid() : sessionId || uuid());
        if (sessionId) global.sessionStorage.setItem(SESSION_KEY, sessionId);
      }
    } catch {
      warn("session_storage_unavailable");
      if (!authenticated()) sessionId = null;
      else if (rotate || !sessionId) sessionId = uuid();
    }
  }

  function validValue(value, rule) {
    const kinds = Array.isArray(rule.type) ? rule.type : [rule.type];
    const matches = (value === null && kinds.includes("null"))
      || (typeof value === "string" && kinds.includes("string"))
      || (typeof value === "number" && Number.isFinite(value)
        && (kinds.includes("number") || (kinds.includes("integer") && Number.isInteger(value))))
      || (Array.isArray(value) && kinds.includes("array"));
    if (!matches || (rule.enum && !rule.enum.includes(value))) return false;
    if (value === null) return true;
    if (typeof value === "string") {
      if (rule.minLength !== undefined && [...value].length < rule.minLength) return false;
      if (rule.format === "uuid" && !uuidPattern.test(value)) return false;
    }
    if (typeof value === "number") {
      if (rule.minimum !== undefined && value < rule.minimum) return false;
      if (rule.maximum !== undefined && value > rule.maximum) return false;
    }
    return !Array.isArray(value) || !rule.items || Array.from(value).every((item) => validValue(item, rule.items));
  }

  function validProperties(type, properties) {
    const rules = definitions.get(type);
    if (!rules || !properties || typeof properties !== "object" || Array.isArray(properties)) return false;
    if (Object.keys(properties).some((key) => !Object.hasOwn(rules, key))) return false;
    for (const [name, rule] of Object.entries(rules)) {
      if (!Object.hasOwn(properties, name)) {
        if (rule.required) return false;
      } else if (!validValue(properties[name], rule)) return false;
    }
    const expected = { valencia: "EUR", miami: "USD" }[properties.office];
    return !expected || properties.currency === undefined || properties.currency === expected;
  }

  function bytes(text) {
    return new Blob([text]).size;
  }

  function makeBatch() {
    const events = [];
    while (queue.length && events.length < BATCH_SIZE) {
      if (bytes(`{"events":[${[...events, queue[0]].join(",")}]}`) > KEEPALIVE_BYTES) break;
      events.push(queue.shift());
    }
    return { events, body: `{"events":[${events.join(",")}]}`, retries: 0, sending: false, timer: null };
  }

  function finish(job) {
    if (active !== job) return;
    active = null;
    if (queue.length >= BATCH_SIZE || flushDue || hidden) pump();
  }

  function send(job) {
    job.sending = true;
    const controller = new AbortController();
    let timeout;
    const deadline = new Promise((_, reject) => {
      timeout = global.setTimeout(() => {
        controller.abort();
        reject(new Error("Telemetry timeout"));
      }, 5000);
    });
    let request;
    try {
      request = global.fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "omit",
        mode: "cors",
        keepalive: hidden,
        signal: controller.signal,
        body: job.body,
      });
    } catch {
      request = Promise.reject(new Error("Telemetry transport unavailable"));
    }
    Promise.race([request, deadline]).then((response) => {
      if (!response.ok) throw new Error("Telemetry response rejected");
      global.clearTimeout(timeout);
      job.sending = false;
      finish(job);
    }).catch(() => {
      global.clearTimeout(timeout);
      job.sending = false;
      warn("delivery_failed");
      if (job.retries === 3) {
        warn("batch_discarded");
        finish(job);
        return;
      }
      const delay = 1000 * (2 ** job.retries++);
      job.timer = global.setTimeout(() => {
        job.timer = null;
        deliver(job);
      }, delay);
    });
  }

  function deliver(job) {
    if (hidden) {
      const size = bytes(job.body);
      if (hiddenBytes + size > KEEPALIVE_BYTES) {
        warn("hidden_transport_budget_reached");
        return;
      }
      hiddenBytes += size;
      let accepted = false;
      if (global.navigator && typeof global.navigator.sendBeacon === "function") {
        try {
          accepted = global.navigator.sendBeacon(endpoint, new Blob([job.body], { type: "application/json" }));
        } catch {
          warn("beacon_unavailable");
        }
      }
      if (accepted) {
        finish(job);
        return;
      }
    }
    send(job);
  }

  function pump() {
    if (active) return;
    if (!queue.length) {
      flushDue = false;
      return;
    }
    flushDue = false;
    active = makeBatch();
    deliver(active);
  }

  function track(eventType, properties, correlationId) {
    if (!endpoint || !definitions.size) return false;
    if (!validProperties(eventType, properties)) {
      warn("invalid_event");
      return false;
    }
    if (queue.length + (active ? active.events.length : 0) >= MAX_EVENTS) {
      warn("queue_full");
      return false;
    }
    const eventId = uuid();
    const requestId = typeof correlationId === "string" && uuidPattern.test(correlationId)
      ? correlationId : uuid();
    if (!eventId || !requestId) return false;
    updateSession();
    const anonymous = eventType === "auth_login_failed";
    const user = !anonymous && authenticated() ? global.inventoryApi.getUser() : null;
    const internalId = user && user.profile && user.profile.user_id;
    const event = {
      eventId,
      timestamp: new Date().toISOString(),
      sessionId: anonymous ? null : sessionId,
      userId: Number.isSafeInteger(internalId) && internalId > 0 ? String(internalId) : null,
      event_type: eventType,
      schemaVersion: "1.0",
      requestId,
      properties: Object.fromEntries(Object.entries(properties).map(([name, value]) => [
        name, Array.isArray(value) ? Array.from(value) : value,
      ])),
    };
    const serialized = JSON.stringify(event);
    if (bytes(serialized) > MAX_EVENT_BYTES) {
      warn("event_too_large");
      return false;
    }
    queue.push(serialized);
    if (queue.length >= BATCH_SIZE || hidden) pump();
    return true;
  }

  if (endpoint && definitions.size) {
    updateSession();
    if (global.inventoryApi) {
      global.inventoryApi.onAuthStateChanged((user) => updateSession(Boolean(user)));
    }
    global.setInterval(() => {
      flushDue = true;
      pump();
    }, 10000);
    global.document.addEventListener("visibilitychange", () => {
      hidden = global.document.visibilityState === "hidden";
      if (!hidden) hiddenBytes = 0;
      if (active && !active.sending) {
        global.clearTimeout(active.timer);
        active.timer = null;
        deliver(active);
      } else if (!active && hidden) {
        pump();
      }
    });
    global.addEventListener("pagehide", () => {
      hidden = true;
      if (active && !active.sending) {
        global.clearTimeout(active.timer);
        active.timer = null;
        deliver(active);
      } else if (!active) {
        pump();
      }
    });
  }

  global.Telemetry = Object.freeze({ track });
})(typeof window !== "undefined" ? window : globalThis);
