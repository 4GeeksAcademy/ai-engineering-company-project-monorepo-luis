import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import { randomUUID } from "node:crypto";

const service = readFileSync(new URL("../telemetry.js", import.meta.url), "utf8");
const contract = readFileSync(new URL("../telemetry-contract.js", import.meta.url), "utf8");
const schema = JSON.parse(readFileSync(new URL("../../../docs/telemetry/event-schemas.json", import.meta.url), "utf8"));
const microtasks = async () => { for (let n = 0; n < 8; n++) await Promise.resolve(); };

function harness(options = {}) {
  let now = 0;
  let sequence = 0;
  let authenticated = Boolean(options.authenticated);
  let user = options.user || null;
  const timers = new Map();
  const storage = options.storage || new Map();
  const requests = [];
  const beacons = [];
  const warnings = [];
  const listeners = new Map();
  const authListeners = [];
  const schedule = (callback, delay, interval = false) => {
    const id = ++sequence;
    timers.set(id, { callback, at: now + delay, interval: interval ? delay : 0 });
    return id;
  };
  const document = {
    visibilityState: "visible",
    addEventListener(name, callback) { listeners.set(name, callback); },
  };
  const context = {
    URL, Blob, AbortController,
    crypto: options.noCrypto ? undefined : { randomUUID },
    location: { href: "http://localhost:5502/inventory.html" },
    document,
    __TELEMETRY_ENDPOINT__: options.endpoint === undefined ? "http://127.0.0.1:8000/telemetry/events" : options.endpoint,
    console: { warn: (message) => warnings.push(message) },
    sessionStorage: {
      getItem: (key) => { if (options.noStorage) throw new Error("blocked"); return storage.get(key); },
      setItem: (key, value) => { if (options.noStorage) throw new Error("blocked"); storage.set(key, value); },
      removeItem: (key) => { if (options.noStorage) throw new Error("blocked"); storage.delete(key); },
    },
    inventoryApi: {
      isAuthenticated: () => authenticated,
      getUser: () => user,
      onAuthStateChanged: (callback) => authListeners.push(callback),
    },
    fetch: (url, init) => {
      requests.push({ url, init, time: now });
      return options.fetch ? options.fetch(url, init) : Promise.resolve({ ok: true });
    },
    navigator: options.noBeacon ? {} : {
      sendBeacon: (url, blob) => {
        beacons.push({ url, blob });
        if (options.beaconThrows) throw new Error("synthetic-private");
        return options.beaconAccepted !== false;
      },
    },
    addEventListener: (name, callback) => listeners.set(name, callback),
    setTimeout: (callback, delay) => schedule(callback, delay),
    clearTimeout: (id) => timers.delete(id),
    setInterval: (callback, delay) => schedule(callback, delay, true),
  };
  context.window = context;
  runInNewContext(contract, context);
  runInNewContext(service, context);
  return {
    context, requests, beacons, warnings, storage,
    track: (type = "auth_login_succeeded", properties = { auth_method: "password" }) => context.Telemetry.track(type, properties),
    async advance(ms) {
      const target = now + ms;
      await microtasks();
      while (true) {
        const next = [...timers.entries()].filter(([, timer]) => timer.at <= target)
          .sort((a, b) => a[1].at - b[1].at)[0];
        if (!next) break;
        const [id, timer] = next;
        now = timer.at;
        if (timer.interval) timer.at += timer.interval;
        else timers.delete(id);
        timer.callback();
        await microtasks();
      }
      now = target;
      await microtasks();
    },
    visibility(state) {
      document.visibilityState = state;
      listeners.get("visibilitychange")?.();
    },
    pagehide: () => listeners.get("pagehide")?.(),
    auth(nextUser) {
      authenticated = Boolean(nextUser);
      user = nextUser;
      authListeners.forEach((callback) => callback(nextUser));
    },
  };
}

function body(request) {
  return JSON.parse(request.init.body);
}

test("batches at exactly 20 events or 10 seconds, captures immutable envelopes at creation", async () => {
  const h = harness();
  const properties = { auth_method: "password" };
  const before = Date.now();
  assert.equal(h.track("auth_login_succeeded", properties), true);
  properties.auth_method = "sso";
  await h.advance(9999);
  assert.equal(h.requests.length, 0);
  const sentAfter = Date.now();
  await h.advance(1);
  assert.equal(h.requests.length, 1);
  const first = body(h.requests[0]).events[0];
  assert.deepEqual(Object.keys(first).sort(),
    ["eventId", "timestamp", "sessionId", "userId", "event_type", "schemaVersion", "requestId", "properties"].sort());
  assert.equal(first.properties.auth_method, "password");
  assert.equal(first.sessionId, null);
  assert.equal(first.userId, null);
  assert.equal(first.schemaVersion, "1.0");
  assert(Date.parse(first.timestamp) >= before && Date.parse(first.timestamp) <= sentAfter);
  assert.match(first.eventId, /^[0-9a-f-]{36}$/);
  assert.notEqual(first.eventId, first.requestId);
  for (let n = 0; n < 19; n++) h.track();
  assert.equal(h.requests.length, 1);
  h.track();
  assert.equal(h.requests.length, 2);
  assert.equal(body(h.requests[1]).events.length, 20);
  const { init } = h.requests[1];
  assert.equal(init.credentials, "omit");
  assert.equal(init.headers.Authorization, undefined);
  assert.deepEqual(Object.keys(init.headers), ["Content-Type"]);
});

test("preserves auth session across documents, rotates at login, clears at logout; never uses PII as ID", async () => {
  const account = { email: "synthetic-private@example.invalid", name: "Synthetic Private", profile: { user_id: 42 } };
  const h = harness();
  h.auth(account);
  h.track();
  await h.advance(10000);
  const first = body(h.requests[0]).events[0];
  assert.equal(first.userId, "42");
  assert.match(first.sessionId, /^[0-9a-f-]{36}$/);
  const next = harness({ storage: h.storage, authenticated: true, user: account });
  next.track();
  await next.advance(10000);
  assert.equal(body(next.requests[0]).events[0].sessionId, first.sessionId);
  h.auth(null);
  h.track();
  h.auth(account);
  h.track();
  await h.advance(10000);
  const [anonymous, relogin] = body(h.requests[1]).events;
  assert.equal(anonymous.sessionId, null);
  assert.equal(anonymous.userId, null);
  assert.notEqual(relogin.sessionId, first.sessionId);
  assert(!h.requests.some((request) => request.init.body.includes("synthetic-private")));
});

test("retries network/HTTP failures at 1/2/4 seconds, preserves IDs/body, drops exhausted batch", async () => {
  let attempts = 0;
  const h = harness({ fetch: () => ++attempts % 2 ? Promise.reject(new Error("synthetic-private")) : Promise.resolve({ ok: false }) });
  for (let n = 0; n < 20; n++) h.track();
  await h.advance(999);
  assert.equal(h.requests.length, 1);
  await h.advance(1);
  assert.equal(h.requests.length, 2);
  await h.advance(1999);
  assert.equal(h.requests.length, 2);
  await h.advance(1);
  assert.equal(h.requests.length, 3);
  await h.advance(4000);
  assert.deepEqual(h.requests.map((request) => request.time), [0, 1000, 3000, 7000]);
  assert.equal(new Set(h.requests.map((request) => request.init.body)).size, 1);
  await h.advance(30000);
  assert.equal(h.requests.length, 4);
  assert(h.warnings.includes("[telemetry] batch_discarded"));
  assert(!h.warnings.join("").includes("synthetic-private"));
  assert.equal(h.track(), true);
});

test("queue includes in-flight events, caps at 500, and recovers after timeout/exhaustion", async () => {
  const h = harness({ fetch: () => new Promise(() => {}) });
  for (let n = 0; n < 500; n++) assert.equal(h.track(), true);
  assert.equal(h.track(), false);
  assert.equal(h.requests.length, 1);
  await h.advance(27000);
  assert.equal(h.requests.length, 5);
  assert.equal(h.requests[0].init.signal.aborted, true);
  assert.equal(h.track(), true);
  assert(h.warnings.includes("[telemetry] queue_full"));
});

test("hidden/pagehide flushes with Beacon, without double sending accepted events", async () => {
  const h = harness();
  for (let n = 0; n < 4; n++) h.track();
  h.visibility("hidden");
  h.pagehide();
  await h.advance(10000);
  assert.equal(h.beacons.length, 1);
  const payload = JSON.parse(await h.beacons[0].blob.text());
  assert.equal(payload.events.length, 4);
  assert.equal(h.beacons[0].blob.type, "application/json");
  assert.equal(h.requests.length, 0);
});

test("Beacon fallback uses bounded keepalive with no credentials for absence/rejection/exception", async () => {
  for (const options of [{ noBeacon: true }, { beaconAccepted: false }, { beaconThrows: true }]) {
    const h = harness(options);
    h.track();
    h.visibility("hidden");
    await h.advance(0);
    assert.equal(h.requests.length, 1);
    assert.equal(h.requests[0].init.keepalive, true);
    assert.equal(h.requests[0].init.credentials, "omit");
    h.pagehide();
    await h.advance(0);
    assert.equal(h.requests.length, 1);
    assert(!h.warnings.join("").includes("synthetic-private"));
  }
});

test("does not resend an in-flight batch when hidden; flushes its pending successor", async () => {
  let resolve;
  const h = harness({ fetch: () => new Promise((done) => { resolve = done; }) });
  for (let n = 0; n < 23; n++) h.track();
  h.visibility("hidden");
  assert.equal(h.beacons.length, 0);
  resolve({ ok: true });
  await h.advance(0);
  assert.equal(h.beacons.length, 1);
  const events = JSON.parse(await h.beacons[0].blob.text()).events;
  assert.equal(events.length, 3);
  assert.equal(new Set([...body(h.requests[0]).events, ...events].map((event) => event.eventId)).size, 23);
});

test("pending retry uses Beacon on hiding, preserving original envelope", async () => {
  const h = harness({ fetch: () => Promise.reject(new Error("offline")) });
  for (let n = 0; n < 20; n++) h.track();
  await h.advance(0);
  h.visibility("hidden");
  assert.equal(await h.beacons[0].blob.text(), h.requests[0].init.body);
  await h.advance(20000);
  assert.equal(h.requests.length, 1);
});

test("disabled/invalid endpoint and unavailable UUID do not send or throw", async () => {
  for (const endpoint of ["", "ftp://localhost/events", "https://user:pass@localhost/events",
    "https://localhost/events?secret=synthetic-private", "http://["]) {
    const h = harness({ endpoint });
    assert.equal(h.track(), false);
    await h.advance(30000);
    assert.equal(h.requests.length, 0);
    assert.equal(h.beacons.length, 0);
    assert(!h.warnings.join("").includes("synthetic-private"));
  }
  const h = harness({ noCrypto: true });
  assert.equal(h.track(), false);
  assert(h.warnings.includes("[telemetry] uuid_unavailable"));
});

test("blocked storage keeps a memory-only session and missing user ID stays null", async () => {
  const h = harness({ noStorage: true, authenticated: true, user: { email: "synthetic-private" } });
  h.track();
  h.track();
  await h.advance(10000);
  const events = body(h.requests[0]).events;
  assert.equal(events[0].sessionId, events[1].sessionId);
  assert.equal(events[0].userId, null);
  assert(h.warnings.includes("[telemetry] session_storage_unavailable"));
});

test("validates all 19 contracts, rejects unknown keys/types, respects nulls/arrays/bounds", async () => {
  const h = harness();
  for (const definition of schema.events) {
    const properties = {};
    for (const [name, rule] of Object.entries(definition.properties)) {
      const kinds = Array.isArray(rule.type) ? rule.type : [rule.type];
      properties[name] = rule.enum ? rule.enum.find((value) => value !== null)
        : rule.format === "uuid" ? randomUUID()
          : kinds.includes("string") ? "synthetic-reference"
            : kinds.includes("number") || kinds.includes("integer") ? rule.minimum ?? 1 : [];
    }
    assert.equal(h.track(definition.event_type, properties), true, definition.event_type);
    assert.equal(h.track(definition.event_type, { ...properties, email: "synthetic-private" }), false);
    for (const name of Object.keys(properties)) {
      assert.equal(h.track(definition.event_type, { ...properties, [name]: {} }), false);
    }
  }
  const latency = { route_group: "auth", http_method: "GET", status_code: null, duration_ms: 10, sample_rate: 1 };
  assert.equal(h.track("api_latency_recorded", latency), true);
  for (const change of [{ status_code: 99 }, { status_code: 600 }, { duration_ms: NaN },
    { duration_ms: Infinity }, { duration_ms: -1 }, { sample_rate: 0 }, { sample_rate: 1.1 },
    { status_code: true }]) {
    assert.equal(h.track("api_latency_recorded", { ...latency, ...change }), false);
  }
  const search = { office: "miami", currency: "USD", result_count: 0, programme_id: null, filters_used: ["availability"] };
  assert.equal(h.track("inventory_search_performed", search), true);
  assert.equal(h.track("inventory_search_performed", { ...search, currency: "EUR" }), false);
  assert.equal(h.track("inventory_search_performed", { ...search, filters_used: ["private-search"] }), false);
  assert.equal(h.track("inventory_search_performed", { ...search, filters_used: new Array(1) }), false);
  const inheritedSerializer = Object.assign(Object.create({
    toJSON() { return { email: "synthetic-private" }; },
  }), { auth_method: "password" });
  assert.equal(h.track("auth_login_succeeded", inheritedSerializer), true);
  assert.equal(h.track("unknown", {}), false);
  assert.equal(h.track("auth_login_succeeded", {}), false);
  assert.equal(h.track("auth_login_succeeded", null), false);
  assert.equal(h.track("auth_login_succeeded", { auth_method: "password", toJSON() { return {}; } }), false);
  await h.advance(10000);
  assert(!h.requests.some((request) => request.init.body.includes("synthetic-private")));
});

test("bounds event bytes and total hidden send budget, resumes parked batches when visible", async () => {
  let resolve;
  const h = harness({ fetch: () => new Promise((done) => { resolve = done; }) });
  const properties = {
    error_fingerprint: "x".repeat(7000), page_id: "inventory", occurrence_count: 1, window_seconds: 60,
  };
  assert.equal(h.track("frontend_uncaught_error", { ...properties, error_fingerprint: "x".repeat(9000) }), false);
  for (let n = 0; n < 20; n++) assert.equal(h.track("frontend_uncaught_error", properties), true);
  h.visibility("hidden");
  resolve({ ok: true });
  await h.advance(0);
  assert(h.beacons.length > 0);
  assert(h.beacons.reduce((total, beacon) => total + beacon.blob.size, 0) <= 60 * 1024);
  const before = h.requests.length;
  h.visibility("visible");
  assert.equal(h.requests.length, before + 1);
});
