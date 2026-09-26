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
  appId: "co.alvoraa.app",
  webDir: "web",
  loggingBehavior: "none",
  android: { allowMixedContent: false, webContentsDebuggingEnabled: false },
  plugins: { CapacitorHttp: { enabled: true }, CapacitorCookies: { enabled: false } },
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

test("config: a server block, debugging, mixed content, cookies on or native HTTP off fail", async () => {
  const { checkCapacitorConfig } = await load();
  assert.deepEqual(checkCapacitorConfig(GOOD_CONFIG), []);
  const bad = [
    { ...GOOD_CONFIG, server: { url: "https://evil.example" } },
    { ...GOOD_CONFIG, server: { allowNavigation: ["*"] } },
    { ...GOOD_CONFIG, android: { webContentsDebuggingEnabled: true } },
    { ...GOOD_CONFIG, android: { allowMixedContent: true } },
    { ...GOOD_CONFIG, plugins: { CapacitorCookies: { enabled: false } } },
    { ...GOOD_CONFIG, plugins: { CapacitorHttp: { enabled: true }, CapacitorCookies: { enabled: true } } },
    // Native HTTP off again: the WebView would block every tenant call as cross-origin (slice 038).
    { ...GOOD_CONFIG, plugins: { CapacitorHttp: { enabled: false }, CapacitorCookies: { enabled: false } } },
    { ...GOOD_CONFIG, plugins: { CapacitorCookies: { enabled: false } } },
    // SEC-30 (ALV-128): the bridge's log would carry request bodies, a sign-in password among them.
    { ...GOOD_CONFIG, loggingBehavior: "debug" },
    { ...GOOD_CONFIG, loggingBehavior: undefined },
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

test("vendored files: content must match the pinned SHA-256 exactly", async () => {
  const { checkVendoredFiles, VENDORED_FILES } = await load();
  const fs = require("node:fs");
  const allRealContent = {};
  for (const relPath of Object.keys(VENDORED_FILES)) {
    allRealContent[relPath] = fs.readFileSync(path.join(__dirname, "..", relPath), "utf8");
  }
  const [oneRelPath] = Object.keys(VENDORED_FILES);

  // Every real, unmodified file matches its pin.
  assert.deepEqual(checkVendoredFiles(allRealContent), []);
  // One byte different in just one of them, and the pin catches only that one.
  const oneChanged = Object.assign({}, allRealContent, { [oneRelPath]: allRealContent[oneRelPath] + "x" });
  assert.equal(checkVendoredFiles(oneChanged).length, 1);
  // Missing entirely is also a failure, not a silent skip.
  assert.equal(checkVendoredFiles({}).length, Object.keys(VENDORED_FILES).length);
});

const GOOD_GRADLE = `
android {
    buildTypes {
        debug {
            applicationIdSuffix ".debug"
            versionNameSuffix "-debug"
        }
        pilot {
            applicationIdSuffix ".pilot"
            versionNameSuffix "-pilot"
        }
        release {
            minifyEnabled false
        }
    }
}
`;

test("build types: debug and pilot need their own applicationIdSuffix; release needs none", async () => {
  const { checkBuildTypes } = await load();
  assert.deepEqual(checkBuildTypes(GOOD_GRADLE), []);
  assert.equal(checkBuildTypes(GOOD_GRADLE.replace('applicationIdSuffix ".pilot"', "")).length, 1);
  assert.equal(checkBuildTypes(GOOD_GRADLE.replace(/pilot \{[\s\S]*?\}\n/, "")).length, 1);
  assert.equal(
    checkBuildTypes(GOOD_GRADLE.replace("release {\n            minifyEnabled false",
      'release {\n            applicationIdSuffix ".x"\n            minifyEnabled false')).length,
    1);
  assert.equal(
    checkBuildTypes(GOOD_GRADLE.replace('applicationIdSuffix ".pilot"',
      'applicationIdSuffix ".pilot"\n            debuggable true')).length,
    1);
});

test("build types: a Google Services / Firebase plugin reference fails", async () => {
  const { checkBuildTypes } = await load();
  assert.equal(checkBuildTypes(GOOD_GRADLE + "\napply plugin: 'com.google.gms.google-services'\n").length, 1);
  assert.equal(checkBuildTypes("classpath 'com.google.gms:google-services:4.4.4'\n" + GOOD_GRADLE).length, 1);
});

const GOOD_NETWORK_CONFIG = `<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="false">localhost</domain>
        <domain includeSubdomains="false">10.0.2.2</domain>
    </domain-config>
</network-security-config>`;

test("debug network config: only localhost and the emulator alias may use cleartext", async () => {
  const { checkDebugNetworkConfig } = await load();
  assert.deepEqual(checkDebugNetworkConfig(GOOD_NETWORK_CONFIG), []);
  assert.equal(
    checkDebugNetworkConfig(GOOD_NETWORK_CONFIG.replace(">localhost<", ">ppj.alvoraa.co<")).length,
    1);
  assert.equal(
    checkDebugNetworkConfig('<network-security-config><base-config cleartextTrafficPermitted="true"/></network-security-config>').length,
    1);
  assert.equal(
    checkDebugNetworkConfig("<network-security-config></network-security-config>").length,
    1);
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
