// Slice 013: the app checks must actually fail on what they promise to catch.
// AC-173 (config), AC-174/AC-179 (outside URLs), AC-177 (permissions),
// AC-178 (tracking libraries), AC-223 (HTML from strings), OPS-41 (exact pins).
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

const load = () => import(pathToFileURL(path.join(__dirname, "..", "scripts", "check_app.mjs")).href);

const GOOD_CONFIG = {
  appId: "co.alvoraa.fieldattendance",
  webDir: "web",
  android: { allowMixedContent: false, webContentsDebuggingEnabled: false },
  plugins: { CapacitorHttp: { enabled: false }, CapacitorCookies: { enabled: false } },
};

const GOOD_MANIFEST = `<manifest xmlns:android="http://schemas.android.com/apk/res/android">
  <application android:allowBackup="false" android:label="x"></application>
  <uses-permission android:name="android.permission.INTERNET" />
  <uses-permission android:name="android.permission.CAMERA" />
  <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
</manifest>`;

test("the committed app passes its own checks", async () => {
  const { runAll } = await load();
  const { problems } = runAll();
  assert.deepEqual(problems, []);
});

test("config: a server block, debugging, mixed content or global native HTTP fail", async () => {
  const { checkCapacitorConfig } = await load();
  assert.deepEqual(checkCapacitorConfig(GOOD_CONFIG), []);
  const bad = [
    { ...GOOD_CONFIG, server: { url: "https://evil.example" } },
    { ...GOOD_CONFIG, server: { allowNavigation: ["*"] } },
    { ...GOOD_CONFIG, android: { webContentsDebuggingEnabled: true } },
    { ...GOOD_CONFIG, android: { allowMixedContent: true } },
    { ...GOOD_CONFIG, plugins: { CapacitorCookies: { enabled: false } } },
    { ...GOOD_CONFIG, plugins: { CapacitorHttp: { enabled: false }, CapacitorCookies: { enabled: true } } },
  ];
  for (const config of bad) {
    assert.ok(checkCapacitorConfig(config).length > 0, JSON.stringify(config));
  }
});

test("permissions: background location, storage or phone state fail; the five pass", async () => {
  const { checkManifest } = await load();
  assert.deepEqual(checkManifest(GOOD_MANIFEST), []);
  for (const extra of [
    "android.permission.ACCESS_BACKGROUND_LOCATION",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.READ_PHONE_STATE",
    "android.permission.RECORD_AUDIO",
  ]) {
    const xml = GOOD_MANIFEST.replace("</manifest>", `<uses-permission android:name="${extra}"/></manifest>`);
    assert.equal(checkManifest(xml).length, 1, extra);
  }
  const sdk23 = GOOD_MANIFEST.replace("</manifest>",
    '<uses-permission-sdk-23 android:name="android.permission.ACCESS_BACKGROUND_LOCATION"/></manifest>');
  assert.equal(checkManifest(sdk23).length, 1);
});

test("manifest: plain HTTP or backup allowed fail", async () => {
  const { checkManifest } = await load();
  assert.equal(checkManifest(GOOD_MANIFEST.replace('android:label="x"', 'android:usesCleartextTraffic="true"')).length, 1);
  assert.equal(checkManifest(GOOD_MANIFEST.replace('android:allowBackup="false"', 'android:allowBackup="true"')).length, 1);
});

test("dependencies: tracking libraries and loose versions fail", async () => {
  const { checkDependencies } = await load();
  const pkg = { dependencies: { "@capacitor/core": "8.5.2" }, devDependencies: { "@capacitor/cli": "8.5.2" } };
  assert.deepEqual(checkDependencies(pkg, { packages: {} }), []);
  assert.equal(checkDependencies({ dependencies: { "@capacitor/core": "^8.5.2" } }, {}).length, 1);
  assert.equal(checkDependencies({ dependencies: { "@capacitor-firebase/analytics": "7.0.0" } }, {}).length, 1);
  assert.equal(checkDependencies(pkg, { packages: { "node_modules/@sentry/capacitor": {} } }).length, 1);
});

test("bundled files: outside URLs, CDNs, local addresses and HTML sinks fail", async () => {
  const { checkWebFile } = await load();
  assert.deepEqual(checkWebFile("a.html",
    '<meta http-equiv="Content-Security-Policy" content="connect-src https://*.alvoraa.co">'), []);
  assert.equal(checkWebFile("a.html", '<script src="https://cdn.example.com/x.js"></script>').length, 1);
  assert.ok(checkWebFile("a.js", 'locateFile: () => "cdn.jsdelivr.net/npm/zxing-wasm"').length >= 1);
  assert.ok(checkWebFile("a.js", 'var BASE = "http://localhost:8010";').length >= 1);
  assert.equal(checkWebFile("a.js", "el.innerHTML = serverText;").length, 1);
  assert.equal(checkWebFile("a.js", "el.insertAdjacentHTML('beforeend', x);").length, 1);
  assert.deepEqual(checkWebFile("a.js", 'el.innerHTML = ""; // safe-html: clearing a node, no data'), []);
  assert.deepEqual(checkWebFile("a.js", "el.textContent = serverText;"), []);
});
