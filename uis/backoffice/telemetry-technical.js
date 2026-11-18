(function (global) {
  "use strict";

  if (!global.__TELEMETRY_ENDPOINT__ || !global.Telemetry) return;
  const { track } = global.Telemetry;
  const pages = new Map([
    ["resumen", "dashboard"],
    ["catalogo", "inventory"],
    ["movimientos", "inventory"],
    ["historial", "reports"],
  ]);
  const pageId = pages.get(global.document.querySelector("backoffice-rail")?.getAttribute("current")) || "other";
  const office = global.__TELEMETRY_OFFICE__;
  const language = global.document.documentElement.lang.toLowerCase().split("-")[0];
  const sectionKey = "nexova_telemetry_section";
  let lastSection = null;
  let storageAvailable = true;

  function recordSection() {
    if (pageId === "other") return;
    try {
      if (storageAvailable) lastSection = global.sessionStorage.getItem(sectionKey);
      if (lastSection === pageId) return;
      if (storageAvailable) global.sessionStorage.setItem(sectionKey, pageId);
    } catch {
      storageAvailable = false;
      global.console.warn("[telemetry] section_storage_unavailable");
      if (lastSection === pageId) return;
    }
    lastSection = pageId;
    track("backoffice_section_viewed", {
      office, section_id: pageId, interface_language: ["es", "en"].includes(language) ? language : null,
    });
  }

  if (office === "valencia" || office === "miami") {
    global.addEventListener("pageshow", recordSection);
    if (global.document.readyState === "complete") recordSection();
  } else {
    global.console.warn("[telemetry] navigation_office_unavailable");
  }

  function recordLoad() {
    const navigation = global.performance?.getEntriesByType?.("navigation")[0];
    if (!navigation || !Number.isFinite(navigation.loadEventEnd) || navigation.loadEventEnd <= 0) return;
    const navigationType = ["navigate", "reload", "back_forward"].includes(navigation.type)
      ? navigation.type : "other";
    track("page_load_recorded", {
      page_id: pageId, duration_ms: navigation.loadEventEnd, navigation_type: navigationType,
    });
  }

  if (global.document.readyState === "complete") {
    global.setTimeout(recordLoad, 0);
  } else {
    global.addEventListener("load", () => global.setTimeout(recordLoad, 0), { once: true });
  }

  const scripts = new Set([
    "auth.js", "shared-nav.js", "inventory-api.js", "inventory-view.js", "inventory-form.js",
    "order-history.js", "incidents.js", "suppliers.js", "auth-protect.js",
  ]);
  const bursts = new Map();
  const windowSeconds = 60;
  const maxBursts = 64;

  function errorSignature(event) {
    if (event.type === "unhandledrejection") return "unhandledrejection";
    if (event.target !== global) return null;
    const filename = typeof event.filename === "string" ? event.filename : "";
    if (filename) {
      try {
        const url = new URL(filename, global.location.href);
        const script = url.pathname.split("/").pop();
        if (url.origin === global.location.origin && scripts.has(script)
            && Number.isSafeInteger(event.lineno) && event.lineno > 0
            && Number.isSafeInteger(event.colno) && event.colno >= 0) {
          return `error:${script}:${event.lineno}:${event.colno}`;
        }
      } catch {
        return "error:unknown";
      }
    }
    return "error:unknown";
  }

  function trackBurst(fingerprint, count, requestId) {
    track("frontend_uncaught_error", {
      error_fingerprint: fingerprint, page_id: pageId, occurrence_count: count, window_seconds: windowSeconds,
    }, requestId);
  }

  function recordError(event) {
    const signature = errorSignature(event);
    if (!signature) return;
    const existing = bursts.get(signature);
    if (existing) {
      existing.count += 1;
      if (!existing.requestId) existing.requestId = global.crypto.randomUUID();
      return;
    }
    if (bursts.size >= maxBursts) return;
    const burst = { count: 0, requestId: null, fingerprint: null };
    bursts.set(signature, burst);
    global.setTimeout(() => {
      bursts.delete(signature);
      if (burst.fingerprint && burst.count) trackBurst(burst.fingerprint, burst.count, burst.requestId);
    }, windowSeconds * 1000);
    // Hash only the controlled signature; never inspect the message, stack or rejection reason.
    global.crypto.subtle.digest("SHA-256", new TextEncoder().encode(signature)).then((hash) => {
      burst.fingerprint = Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, "0")).join("");
      trackBurst(burst.fingerprint, 1);
    }).catch(() => global.console.warn("[telemetry] fingerprint_unavailable"));
  }

  if (global.crypto?.subtle && typeof global.crypto.randomUUID === "function") {
    global.addEventListener("error", recordError);
    global.addEventListener("unhandledrejection", recordError);
  } else {
    global.console.warn("[telemetry] fingerprint_unavailable");
  }
})(window);
