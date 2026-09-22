// Slice 013, US-36/AC-217: the device secret is written only through a real
// native plugin, never through the plugin's own (unencrypted) web fallback.
// This proves the SAFETY LOGIC with a fake plugin - it cannot prove the real
// Keystore round trip, which needs an actual Android device (see
// docs/slices/013-mobile-app/03-implementation-notes.md §7.4/§7.5).
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const { save, load, clear, KEY } = require(path.join(__dirname, "..", "web", "js", "device-secret.js"));

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
