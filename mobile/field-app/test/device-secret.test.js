// Slice 013, US-36/AC-217: the device secret is written only through a real
// native plugin, never through the plugin's own (unencrypted) web fallback.
// This proves the SAFETY LOGIC with a fake plugin - it cannot prove the real
// Keystore round trip, which needs an actual Android device (see
// docs/slices/013-mobile-app/03-implementation-notes.md §7.4/§7.5).
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const { save, load, clear, KEY, ORIGIN_KEY, saveOrigin, loadOrigin } =
  require(path.join(__dirname, "..", "web", "js", "device-secret.js"));

const REAL_SECRET = "s".repeat(43); // secrets.token_urlsafe(32) shape

function fakeNativeCapacitor(store) {
  return {
    isNativePlatform: () => true,
    Plugins: {
      SecureStoragePlugin: {
        set: ({ key, value }) => { store[key] = value; return Promise.resolve({ value: true }); },
        get: ({ key }) => (key in store)
          ? Promise.resolve({ value: store[key] })
          : Promise.reject("Item with given key does not exist"),
        remove: ({ key }) => {
          const had = key in store;
          delete store[key];
          return Promise.resolve({ value: had });
        },
      },
    },
  };
}

function fakeWebCapacitor(store) {
  // The plugin's own web fallback shape: still callable, just not native.
  return Object.assign(fakeNativeCapacitor(store), { isNativePlatform: () => false });
}

test("save() then load() round-trips through the fake native plugin", async () => {
  const store = {};
  const cap = fakeNativeCapacitor(store);
  const saved = await save(REAL_SECRET, cap);
  assert.equal(saved, true);
  assert.equal(store[KEY], REAL_SECRET);
  const loaded = await load(cap);
  assert.equal(loaded, REAL_SECRET);
});

test("load() on a fresh phone (nothing stored) resolves null, not a rejection", async () => {
  const cap = fakeNativeCapacitor({});
  assert.equal(await load(cap), null);
});

test("clear() removes the secret and says whether one was there", async () => {
  const store = { [KEY]: REAL_SECRET };
  const cap = fakeNativeCapacitor(store);
  assert.equal(await clear(cap), true);
  assert.equal(KEY in store, false);
  assert.equal(await clear(cap), false); // nothing left to clear the second time
});

test("save() refuses when there is no real native platform - never falls back to the web store", async () => {
  const store = {};
  const cap = fakeWebCapacitor(store);
  await assert.rejects(() => save(REAL_SECRET, cap), /not available/);
  assert.deepEqual(store, {}); // nothing was written anywhere
});

test("load() and clear() fail closed (empty/false), not through the web fallback, when not native", async () => {
  const store = { [KEY]: "leftover-from-somewhere" };
  const cap = fakeWebCapacitor(store);
  assert.equal(await load(cap), null);
  assert.equal(await clear(cap), false);
  assert.equal(store[KEY], "leftover-from-somewhere"); // untouched - never read or cleared via the web path
});

test("save() refuses a missing or too-short secret before it ever calls the plugin", async () => {
  const store = {};
  const cap = fakeNativeCapacitor(store);
  await assert.rejects(() => save("", cap));
  await assert.rejects(() => save("short", cap));
  await assert.rejects(() => save(undefined, cap));
  assert.deepEqual(store, {});
});

test("with no Capacitor global at all (a plain browser preview), every call fails closed", async () => {
  assert.equal(await load(null), null);
  assert.equal(await clear(null), false);
  await assert.rejects(() => save(REAL_SECRET, null));
});

// ── the tenant-origin key (US-39/43: the app must remember which tenant it
//    talks to across a restart, not just its secret) ─────────────────────────

const REAL_ORIGIN = "https://kaveri.alvoraa.co";

test("saveOrigin() then loadOrigin() round-trips through the fake native plugin", async () => {
  const store = {};
  const cap = fakeNativeCapacitor(store);
  const saved = await saveOrigin(REAL_ORIGIN, cap);
  assert.equal(saved, true);
  assert.equal(store[ORIGIN_KEY], REAL_ORIGIN);
  assert.equal(await loadOrigin(cap), REAL_ORIGIN);
});

test("loadOrigin() on a fresh phone (nothing stored) resolves null, not a rejection", async () => {
  assert.equal(await loadOrigin(fakeNativeCapacitor({})), null);
});

test("saveOrigin() refuses when there is no real native platform - never falls back to the web store", async () => {
  const store = {};
  const cap = fakeWebCapacitor(store);
  await assert.rejects(() => saveOrigin(REAL_ORIGIN, cap), /not available/);
  assert.deepEqual(store, {});
});

test("saveOrigin() refuses anything that is not a plain https origin", async () => {
  const cap = fakeNativeCapacitor({});
  for (const bad of ["", "http://kaveri.alvoraa.co", "https://kaveri.alvoraa.co/enrol",
                      "https://kaveri.alvoraa.co#t=x", "javascript:alert(1)", null, undefined, 42]) {
    await assert.rejects(() => saveOrigin(bad, cap));
  }
});

test("loadOrigin() fails closed (null), not through the web fallback, when not native", async () => {
  const store = { [ORIGIN_KEY]: "leftover-from-somewhere" };
  assert.equal(await loadOrigin(fakeWebCapacitor(store)), null);
  assert.equal(store[ORIGIN_KEY], "leftover-from-somewhere"); // untouched
});

test("clear() removes the secret AND the origin together, never one without the other", async () => {
  const store = { [KEY]: REAL_SECRET, [ORIGIN_KEY]: REAL_ORIGIN };
  const cap = fakeNativeCapacitor(store);
  assert.equal(await clear(cap), true); // return value still answers for the secret only
  assert.equal(KEY in store, false);
  assert.equal(ORIGIN_KEY in store, false);
});

test("clear() still reports the secret's own presence when only the origin was left behind", async () => {
  // A hypothetical half-cleared phone from before this key existed - clear()
  // must not crash or misreport just because the origin key is missing.
  const store = { [KEY]: REAL_SECRET };
  assert.equal(await clear(fakeNativeCapacitor(store)), true);
  assert.equal(KEY in store, false);
});

test("with no Capacitor global at all, loadOrigin() and saveOrigin() fail closed too", async () => {
  assert.equal(await loadOrigin(null), null);
  await assert.rejects(() => saveOrigin(REAL_ORIGIN, null));
});
