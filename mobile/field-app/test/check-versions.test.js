// Slice 013, AC-168: versionName is MAJOR.MINOR.PATCH; versionCode is
// MAJOR x 1,000,000 + MINOR x 10,000 + PATCH x 100 + build number, and must
// rise on every build.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

const load = () => import(pathToFileURL(path.join(__dirname, "..", "scripts", "check_versions.mjs")).href);

test("the committed build.gradle has a well-formed version", async () => {
  const { extractVersion, checkVersionFormat } = await load();
  const fs = require("node:fs");
  const text = fs.readFileSync(path.join(__dirname, "..", "android", "app", "build.gradle"), "utf8");
  const version = extractVersion(text);
  assert.ok(version, "versionName/versionCode not found in build.gradle");
  assert.deepEqual(checkVersionFormat(version), []);
});

test("parseVersionName accepts only MAJOR.MINOR.PATCH", async () => {
  const { parseVersionName } = await load();
  assert.deepEqual(parseVersionName("1.2.3"), { major: 1, minor: 2, patch: 3 });
  for (const bad of ["1.2", "1.2.3.4", "1.2.3-debug", "v1.2.3", "", null, undefined]) {
    assert.equal(parseVersionName(bad), null, String(bad));
  }
});

test("checkVersionFormat: versionCode must match the formula, build number 0-99", async () => {
  const { checkVersionFormat } = await load();
  assert.deepEqual(checkVersionFormat({ versionName: "1.2.3", versionCode: 1_020_300 }), []);
  assert.deepEqual(checkVersionFormat({ versionName: "1.2.3", versionCode: 1_020_399 }), []);
  assert.equal(checkVersionFormat({ versionName: "1.2.3", versionCode: 1_020_400 }).length, 1); // build 100
  assert.equal(checkVersionFormat({ versionName: "1.2.3", versionCode: 1_020_299 }).length, 1); // build -1
  assert.equal(checkVersionFormat({ versionName: "1.2.3", versionCode: 9_999_999 }).length, 1);
  assert.equal(checkVersionFormat({ versionName: "1.2", versionCode: 1_020_300 }).length, 1);
});

test("checkVersionBump: versionCode must strictly rise", async () => {
  const { checkVersionBump } = await load();
  assert.deepEqual(checkVersionBump(10000, 10001), []);
  assert.equal(checkVersionBump(10000, 10000).length, 1);
  assert.equal(checkVersionBump(10001, 10000).length, 1);
});

test("the committed app-version.js matches the committed build.gradle", async () => {
  const { extractVersion, extractAppVersionConstant, checkAppVersionMatchesGradle } = await load();
  const fs = require("node:fs");
  const gradleText = fs.readFileSync(path.join(__dirname, "..", "android", "app", "build.gradle"), "utf8");
  const jsText = fs.readFileSync(path.join(__dirname, "..", "web", "js", "app-version.js"), "utf8");
  const gradleVersion = extractVersion(gradleText);
  const jsVersion = extractAppVersionConstant(jsText);
  assert.equal(jsVersion, "0.3.0"); // 27 Sep 2026: the Material 3 redesign (ALV-133)
  assert.deepEqual(checkAppVersionMatchesGradle(jsVersion, gradleVersion.versionName), []);
});

test("extractAppVersionConstant reads APP_VERSION out of plain JS text", async () => {
  const { extractAppVersionConstant } = await load();
  assert.equal(extractAppVersionConstant('var APP_VERSION = "1.2.3";'), "1.2.3");
  assert.equal(extractAppVersionConstant("nothing here"), null);
});

test("checkAppVersionMatchesGradle: a mismatch fails, a match and a missing constant are handled", async () => {
  const { checkAppVersionMatchesGradle } = await load();
  assert.deepEqual(checkAppVersionMatchesGradle("0.1.0", "0.1.0"), []);
  assert.equal(checkAppVersionMatchesGradle("0.1.0", "0.2.0").length, 1);
  assert.equal(checkAppVersionMatchesGradle(null, "0.1.0").length, 1);
});

test("extractVersion reads both fields out of a Gradle file's text", async () => {
  const { extractVersion } = await load();
  const text = 'versionCode 10000\n        versionName "0.1.0"\n';
  assert.deepEqual(extractVersion(text), { versionName: "0.1.0", versionCode: 10000 });
  assert.equal(extractVersion("versionCode 10000\n"), null);
});
