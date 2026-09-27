// App checks that need no Android SDK. Slice 013: SEC-16, SEC-17, SEC-20, OPS-22,
// OPS-38, OPS-41, OPS-55, OPS-74, OPS-79, PRIV-8.
//
// Each check turns a promise ("no background location", "no outside content",
// "no analytics", "debug, pilot and release can never collide") into a build
// failure. Run from mobile/field-app:
//
//     node scripts/check_app.mjs            exit 0 = pass
//
// What this does NOT cover yet, and why: the checks on the BUILT package
// (merged manifest read with apkanalyzer, debuggable flag, actual network
// rules once merged, size <= 10 MB) need a real Android SDK build, which this
// sandbox does not have. They arrive before the first pilot build (DevOps §4
// gate 5). Until android/ exists at all, the source-level checks below say
// SKIPPED instead of passing silently.

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, extname } from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";

const APP_DIR = fileURLToPath(new URL("..", import.meta.url));

// ── the rules ───────────────────────────────────────────────────────────────

// The only Android permissions the app may hold (SEC-20). Anything else - above
// all ACCESS_BACKGROUND_LOCATION - needs a reviewed change to this list.
export const ALLOWED_PERMISSIONS = new Set([
  "android.permission.INTERNET",
  "android.permission.ACCESS_NETWORK_STATE",
  "android.permission.CAMERA",
  "android.permission.ACCESS_FINE_LOCATION",
  "android.permission.ACCESS_COARSE_LOCATION",
]);

// Libraries that phone home or track people (SEC-20, PRIV-8, gate decision 6).
export const DENIED_DEPENDENCY = /analytics|crashlytics|firebase|sentry|bugsnag|datadog|amplitude|mixpanel|segment|appsflyer|adjust-sdk|admob|google-mobile-ads|onesignal|posthog|newrelic|instabug|appcenter|clevertap|branch-sdk|facebook/i;

// URLs a bundled file may contain: only the tenant pattern (in the content policy).
const ALLOWED_URL = /^https:\/\/\*\.alvoraa\.co$/;
const URL_IN_TEXT = /\b(?:https?|wss?|ftp):\/\/[^\s"'`<>)]+/gi;
// Hosts that serve code or fonts from outside, even when written without a scheme.
const OUTSIDE_HOST = /jsdelivr|unpkg\.com|cdnjs|googleapis|gstatic|cloudflare|localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\./i;

// Writing HTML from strings is how server text could run as code (SEC-17).
// A line may opt out only with a reason: // safe-html: <why>
const HTML_SINK = /\.(?:innerHTML|outerHTML)\s*[+]?=|insertAdjacentHTML\s*\(|document\.write(?:ln)?\s*\(/;

const WEB_EXTENSIONS = new Set([".html", ".js", ".mjs", ".css", ".json", ".svg"]);

// web/js/vendor/*: third-party code copied byte-for-byte from an npm
// package's published dist output (see web/js/vendor/README.md), never
// hand-edited. It is pinned by hash here instead of being scanned line by
// line like our own code - a vendored bundle legitimately mentions an outside
// URL in a comment (jsQR's does, an algorithm reference, not a network call),
// and the hash pin is the stronger check anyway: it catches ANY change, not
// only the ones our own line-based rules know to look for.
export const VENDORED_FILES = {
  "web/js/vendor/jsqr.js":
    "bc40c8a15196236b2314db0856f72ca0b49980cd5413b8c852a7349f5fee0859", // jsqr 1.4.0, dist/jsQR.js
  "web/js/vendor/capacitor-core.js":
    "3333389c8cccd266c26399aaf7fc2a695c110684dd6340aea47935416be86a0c", // @capacitor/core 8.5.2, dist/capacitor.js
  "web/js/vendor/secure-storage-plugin.js":
    "aca8dcc86ceed62b299b566d3f9f796bc409f7a3909cf9e6510c866db95d8d6b", // capacitor-secure-storage-plugin 0.13.0, dist/plugin.js
  // D-M3-3: built, not copied - @material/material-color-utilities 0.3.0 joined
  // into one file by esbuild 0.28.2 (scripts/vendor/build_mcu.mjs).
  "web/js/vendor/material-color-utilities.js":
    "6e70be868a4ff28b30cccf78552c23d9faf69c851c61bc2570c50c893ad732c2",
};

// ── the checks, each returning a list of problems ───────────────────────────

export function checkCapacitorConfig(config) {
  const problems = [];
  if (config.server !== undefined) {
    problems.push("capacitor.config.json has a \"server\" block (server.url, cleartext or allowNavigation). The app must load only its bundled page (SEC-16).");
  }
  if (config.android?.webContentsDebuggingEnabled === true) {
    problems.push("WebView debugging is on in capacitor.config.json (SEC-16).");
  }
  if (config.android?.allowMixedContent === true) {
    problems.push("allowMixedContent is on in capacitor.config.json (SEC-16).");
  }
  // Native HTTP must be ON: the bundled page's POSTs to https://<tenant>.alvoraa.co
  // are cross-origin from the WebView, the server sends no CORS headers on purpose
  // (OPS-1, OPS-47), and only Capacitor's native layer is outside CORS (OPS-2).
  // Decided 2026-09-23 (slice 038), which reverses OPS-79's "global switch off".
  // Off again would mean the phone itself blocks the app's first call.
  if (config.plugins?.CapacitorHttp?.enabled !== true) {
    problems.push("CapacitorHttp must be on (plugins.CapacitorHttp.enabled = true), or the WebView blocks every call to the tenant as cross-origin (OPS-2, slice 038).");
  }
  // SEC-30 (ALV-128): Capacitor's bridge logs every native call - with native
  // HTTP on, that is every request body, sign-in password included - to the
  // Android log, which other tools on a phone can read. "none" turns it off.
  if (config.loggingBehavior !== "none") {
    problems.push('loggingBehavior must be "none" in capacitor.config.json, or request bodies (a sign-in password among them) reach the Android log (SEC-30).');
  }
  if (config.plugins?.CapacitorCookies?.enabled !== false) {
    problems.push("CapacitorCookies must be off (plugins.CapacitorCookies.enabled = false) (OPS-79).");
  }
  return problems;
}

export function checkDependencies(pkg, lock) {
  const problems = [];
  for (const section of ["dependencies", "devDependencies"]) {
    for (const [name, version] of Object.entries(pkg[section] || {})) {
      if (!/^\d+\.\d+\.\d+$/.test(version)) {
        problems.push(`${name} is "${version}". Pin an exact version, no ^, ~ or ranges (OPS-41, OPS-77).`);
      }
    }
  }
  const names = new Set(Object.keys({ ...pkg.dependencies, ...pkg.devDependencies }));
  for (const path of Object.keys(lock?.packages || {})) {
    const idx = path.lastIndexOf("node_modules/");
    if (idx !== -1) names.add(path.slice(idx + "node_modules/".length));
  }
  for (const name of names) {
    if (DENIED_DEPENDENCY.test(name)) {
      problems.push(`Dependency "${name}" looks like analytics, crash reporting, ads or Firebase. Not allowed in this app (SEC-20).`);
    }
  }
  return problems;
}

export function checkWebFile(path, text) {
  const problems = [];
  for (const match of text.matchAll(URL_IN_TEXT)) {
    const url = match[0].replace(/[;,.]+$/, "");
    if (!ALLOWED_URL.test(url)) {
      problems.push(`${path}: outside URL "${url}". The bundle may load nothing from the internet (OPS-22).`);
    }
  }
  const lines = text.split(/\r?\n/);
  lines.forEach((line, i) => {
    if (OUTSIDE_HOST.test(line)) {
      problems.push(`${path}:${i + 1}: names an outside or local host (CDN, fonts or a development address) (OPS-22, OPS-84).`);
    }
    if (HTML_SINK.test(line) && !/\/\/\s*safe-html:\s*\S/.test(line)) {
      problems.push(`${path}:${i + 1}: writes HTML from a string. Use textContent, or mark the line "// safe-html: <reason>" after review (SEC-17).`);
    }
  });
  return problems;
}

// A vendored file's actual content must match the SHA-256 pinned above -
// exactly, every byte. `files` is { "web/js/vendor/x.js": "<bytes>", ... },
// so this stays pure and testable without touching a real filesystem.
export function checkVendoredFiles(files) {
  const problems = [];
  for (const [path, expected] of Object.entries(VENDORED_FILES)) {
    const content = files[path];
    if (content === undefined) {
      problems.push(`${path} is missing but is listed as a vendored file in VENDORED_FILES.`);
      continue;
    }
    const actual = createHash("sha256").update(content).digest("hex");
    if (actual !== expected) {
      problems.push(`${path} does not match its pinned SHA-256 (expected ${expected}, got ${actual}). A vendored file must never be hand-edited - update the pin deliberately if the version really changed (web/js/vendor/README.md).`);
    }
  }
  return problems;
}

export function checkManifest(xml) {
  const problems = [];
  const permission = /<uses-permission(?:-sdk-23)?\b[^>]*android:name\s*=\s*"([^"]+)"/g;
  for (const match of xml.matchAll(permission)) {
    if (!ALLOWED_PERMISSIONS.has(match[1])) {
      problems.push(`AndroidManifest.xml asks for ${match[1]}. Only ${[...ALLOWED_PERMISSIONS].join(", ")} are allowed (SEC-20).`);
    }
  }
  if (/android:usesCleartextTraffic\s*=\s*"true"/.test(xml)) {
    problems.push("AndroidManifest.xml allows plain HTTP (usesCleartextTraffic=\"true\") (SEC-16).");
  }
  if (/<application\b/.test(xml) && !/android:allowBackup\s*=\s*"false"/.test(xml)) {
    problems.push("AndroidManifest.xml must set android:allowBackup=\"false\" (SEC-16, AC-221).");
  }
  return problems;
}

// Finds a top-level `name { ... }` block by matching braces, starting at the
// first "name {" in the text. Good enough for our own small, hand-written
// build.gradle - not a real Groovy parser, the same trade-off checkManifest
// already makes with regex instead of a real XML parser.
function namedBlock(text, name) {
  const start = text.indexOf(`${name} {`);
  if (start === -1) return null;
  let depth = 0;
  for (let i = text.indexOf("{", start); i < text.length; i++) {
    if (text[i] === "{") depth++;
    else if (text[i] === "}") {
      depth--;
      if (depth === 0) return text.slice(start, i + 1);
    }
  }
  return null;
}

// OPS-38, AC-165: debug, pilot and release must each end up with a different
// app ID, so all three install side by side and a test build can never
// replace the real one. Also SEC-20/gate decision 6: no Firebase plugin, since
// this app has no push notifications and no crash-reporting tool.
export function checkBuildTypes(gradleText) {
  const problems = [];
  const SUFFIXED = { debug: ".debug", pilot: ".pilot" };

  for (const [type, suffix] of Object.entries(SUFFIXED)) {
    const block = namedBlock(gradleText, type);
    if (!block) {
      problems.push(`android/app/build.gradle has no "${type}" build type (OPS-38, AC-165).`);
      continue;
    }
    const wanted = new RegExp(`applicationIdSuffix\\s*["']${suffix.replace(".", "\\.")}["']`);
    if (!wanted.test(block)) {
      problems.push(`The "${type}" build type must set applicationIdSuffix "${suffix}" (OPS-38, AC-165), so it never collides with the other two on one phone.`);
    }
    if (/\bdebuggable\s+true\b/.test(block) && type !== "debug") {
      problems.push(`The "${type}" build type must not set debuggable true (AC-173).`);
    }
  }

  const release = namedBlock(gradleText, "release");
  if (release && /applicationIdSuffix/.test(release)) {
    problems.push('The "release" build type must have no applicationIdSuffix - it is the store app ID (AC-165).');
  }
  if (release && /\bdebuggable\s+true\b/.test(release)) {
    problems.push('The "release" build type must not set debuggable true (AC-173).');
  }

  if (/classpath\s+['"]com\.google\.gms:google-services/.test(gradleText)
      || /apply\s+plugin:\s*['"]com\.google\.gms\.google-services['"]/.test(gradleText)) {
    problems.push("A Google Services / Firebase Gradle plugin reference was found. This app has no Firebase feature in scope (push, crash reporting) - remove it (SEC-20, gate decision 6).");
  }

  return problems;
}

// AC-166: a debug build may reach plain HTTP only at the developer's own
// machine (localhost, or 10.0.2.2 for an emulator) - never a tenant, and never
// through a config that applies cleartext to every domain.
export function checkDebugNetworkConfig(xml) {
  const problems = [];
  const baseConfigOpen = /<base-config[^>]*cleartextTrafficPermitted\s*=\s*"true"/.test(xml);
  if (baseConfigOpen) {
    problems.push("network_security_config.xml allows cleartext at the base-config level, which reaches every domain including a tenant (AC-166, SEC-16). Scope it to a named domain-config instead.");
  }
  const domainConfig = /<domain-config[^>]*cleartextTrafficPermitted\s*=\s*"true"[\s\S]*?<\/domain-config>/g;
  const allowed = new Set(["localhost", "10.0.2.2"]);
  let sawAny = false;
  for (const match of xml.matchAll(domainConfig)) {
    sawAny = true;
    for (const d of match[0].matchAll(/<domain[^>]*>([^<]+)<\/domain>/g)) {
      if (!allowed.has(d[1].trim())) {
        problems.push(`network_security_config.xml allows cleartext to "${d[1].trim()}". Only localhost and 10.0.2.2 may - never a tenant host (AC-166, OPS-7).`);
      }
    }
  }
  // Only worth saying when nothing at all grants cleartext yet - if the
  // base-config already grants it too broadly, that is the problem to fix,
  // not a missing domain-config as well.
  if (!sawAny && !baseConfigOpen) {
    problems.push("network_security_config.xml has no cleartext domain-config at all - the debug build cannot reach the local bench over plain HTTP (AC-166).");
  }
  return problems;
}

// ── running them ────────────────────────────────────────────────────────────

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) out.push(...walk(full));
    else out.push(full);
  }
  return out;
}

export function runAll(appDir = APP_DIR) {
  const problems = [];
  const notes = [];

  const config = JSON.parse(readFileSync(join(appDir, "capacitor.config.json"), "utf8"));
  problems.push(...checkCapacitorConfig(config));

  const pkg = JSON.parse(readFileSync(join(appDir, "package.json"), "utf8"));
  const lockPath = join(appDir, "package-lock.json");
  if (!existsSync(lockPath)) problems.push("package-lock.json is missing. Commit it and install with npm ci (OPS-41).");
  const lock = existsSync(lockPath) ? JSON.parse(readFileSync(lockPath, "utf8")) : {};
  problems.push(...checkDependencies(pkg, lock));

  const webDir = join(appDir, config.webDir || "web");
  const vendoredContent = {};
  for (const file of walk(webDir)) {
    if (!WEB_EXTENSIONS.has(extname(file).toLowerCase())) continue;
    const relPath = relative(appDir, file).replace(/\\/g, "/");
    if (relPath in VENDORED_FILES) {
      // Pinned by hash instead of scanned line by line - see VENDORED_FILES.
      vendoredContent[relPath] = readFileSync(file, "utf8");
      continue;
    }
    problems.push(...checkWebFile(relPath, readFileSync(file, "utf8")));
  }
  problems.push(...checkVendoredFiles(vendoredContent));

  const manifest = join(appDir, "android", "app", "src", "main", "AndroidManifest.xml");
  const gradlePath = join(appDir, "android", "app", "build.gradle");
  const rootGradlePath = join(appDir, "android", "build.gradle");
  const debugNetConfigPath = join(appDir, "android", "app", "src", "debug", "res", "xml", "network_security_config.xml");
  if (existsSync(manifest)) {
    problems.push(...checkManifest(readFileSync(manifest, "utf8")));

    if (existsSync(gradlePath)) {
      // The Firebase/Google-Services classpath this scans for is declared in
      // the ROOT build.gradle, not this one - scanning only this file let a
      // restored classpath line in the root file sail through unnoticed.
      let gradleText = readFileSync(gradlePath, "utf8");
      if (existsSync(rootGradlePath)) {
        gradleText += "\n" + readFileSync(rootGradlePath, "utf8");
      }
      problems.push(...checkBuildTypes(gradleText));
    } else {
      problems.push("android/app/build.gradle is missing.");
    }

    if (existsSync(debugNetConfigPath)) {
      problems.push(...checkDebugNetworkConfig(readFileSync(debugNetConfigPath, "utf8")));
    } else {
      problems.push("android/app/src/debug/res/xml/network_security_config.xml is missing (AC-166).");
    }
  } else if (existsSync(join(appDir, "android"))) {
    problems.push("android/ exists but android/app/src/main/AndroidManifest.xml does not.");
  } else {
    notes.push("SKIPPED: Android manifest, build-type and network-config checks - android/ is not generated yet (needs Android Studio and the SDK).");
  }
  notes.push("NOT YET: checks on the BUILT package (merged manifest via apkanalyzer, debuggable flag, package size <= 10 MB) - these need a real Android SDK build, which this run does not have. Before the first pilot build (DevOps 07 §4 gate 5).");

  return { problems, notes };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const { problems, notes } = runAll();
  for (const note of notes) console.log(note);
  if (problems.length) {
    console.log(`FAIL: ${problems.length} problem(s).`);
    for (const p of problems) console.log(`  - ${p}`);
    process.exit(1);
  }
  console.log("OK: app config, dependencies and bundled files pass.");
}
