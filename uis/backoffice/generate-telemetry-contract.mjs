import { readFileSync, writeFileSync } from "node:fs";
import assert from "node:assert/strict";

const source = new URL("../../docs/telemetry/event-schemas.json", import.meta.url);
const target = new URL("./telemetry-contract.js", import.meta.url);
const registry = JSON.parse(readFileSync(source, "utf8"));
const events = registry.events.map(({ event_type, properties }) => ({ event_type, properties }));
const output = "// Generated from docs/telemetry/event-schemas.json; do not edit manually.\n"
  + `globalThis.__NEXOVA_TELEMETRY_REGISTRY__ = ${JSON.stringify(events)};\n`;

if (process.argv.includes("--check")) {
  assert.equal(readFileSync(target, "utf8").replace(/\r\n/g, "\n"), output, "Regenerate the static telemetry contract");
} else {
  writeFileSync(target, output);
}
