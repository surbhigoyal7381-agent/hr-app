// Slice 013, US-43/AC-215: "What this app records" reads from saved data,
// with no server call. This proves the pure save/load/clear logic against a
// fake storage object; it does not prove real Android WebView localStorage
// behaviour, which needs a device.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const { save, load, clear, KEY } = require(
  path.join(__dirname, "..", "web", "js", "notice-cache.js"));

function fakeStorage(initial) {
  const store = Object.assign({}, initial);
  return {
    _store: store,
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: (k) => { delete store[k]; },
  };
}

const ENTRY = {
  version: "2026-09-22",
  rows: [{ heading: "What we record", body: "A photo of you..." }],
  agree: "I have read this and I understand.",
  retentionDays: 90,
  agreedAt: "2026-09-22 09:01:00",
};

test("save() then load() round-trips the whole entry", () => {
  const storage = fakeStorage();
  assert.equal(save(ENTRY, storage), true);
  assert.deepEqual(load(storage), ENTRY);
});

test("load() on a fresh phone (nothing saved) returns null, not a throw", () => {
  assert.equal(load(fakeStorage()), null);
});

test("load() returns null for corrupt JSON rather than throwing", () => {
  const storage = fakeStorage({ [KEY]: "{not json" });
  assert.equal(load(storage), null);
});

test("clear() removes the saved entry", () => {
  const storage = fakeStorage();
  save(ENTRY, storage);
  clear(storage);
  assert.equal(load(storage), null);
});

test("save() fills in safe defaults for a partial entry, never throws on a missing field", () => {
  const storage = fakeStorage();
  assert.equal(save({ version: "2026-09-22" }, storage), true);
  const loaded = load(storage);
  assert.equal(loaded.version, "2026-09-22");
  assert.deepEqual(loaded.rows, []);
});

test("save() degrades to false, load() to null, when there is no storage at all", () => {
  assert.equal(save(ENTRY, null), false);
  assert.equal(load(null), null);
  assert.doesNotThrow(() => clear(null));
});

test("a storage whose setItem/getItem throw (quota, a locked-down WebView) fails soft", () => {
  const angry = {
    getItem: () => { throw new Error("blocked"); },
    setItem: () => { throw new Error("quota"); },
    removeItem: () => { throw new Error("blocked"); },
  };
  assert.equal(save(ENTRY, angry), false);
  assert.equal(load(angry), null);
  assert.doesNotThrow(() => clear(angry));
});

test("save() refuses a non-object entry without throwing", () => {
  const storage = fakeStorage();
  assert.equal(save(null, storage), false);
  assert.equal(save("a string", storage), false);
  assert.equal(save(undefined, storage), false);
});
