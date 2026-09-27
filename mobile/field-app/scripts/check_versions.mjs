// AC-168 (slice 013, OPS-40): versionName must be MAJOR.MINOR.PATCH, versionCode
// must equal MAJOR x 1,000,000 + MINOR x 10,000 + PATCH x 100 + build number
// (build number 0-99), and versionCode must rise from one build to the next -
// never repeat, never fall, so two builds can never be confused with each
// other on a phone or in the Play Console.
//
// Run from mobile/field-app:
//
//     node scripts/check_versions.mjs                    format only
//     node scripts/check_versions.mjs old-build.gradle    format + must-rise
//
// The second form is how CI calls this: it writes the base branch's copy of
// android/app/build.gradle to a temp file with `git show`, then passes it here
// (see .github/workflows/mobile.yml). Nothing here needs git or the network
// itself - both entry points are given plain text.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const APP_DIR = fileURLToPath(new URL("..", import.meta.url));

// ── pure logic ───────────────────────────────────────────────────────────────

export function extractVersion(gradleText) {
  const name = /versionName\s+["']([^"']+)["']/.exec(gradleText);
  const code = /versionCode\s+(\d+)/.exec(gradleText);
  if (!name || !code) return null;
  return { versionName: name[1], versionCode: Number(code[1]) };
}

export function parseVersionName(name) {
  // The base name only - "0.1.0", never "0.1.0-debug": the debug/pilot
  // suffixes are added by Gradle's versionNameSuffix, not written here.
  const match = /^(\d+)\.(\d+)\.(\d+)$/.exec(name || "");
  if (!match) return null;
  return { major: Number(match[1]), minor: Number(match[2]), patch: Number(match[3]) };
}

export function checkVersionFormat({ versionName, versionCode }) {
  const problems = [];
  const parsed = parseVersionName(versionName);
  if (!parsed) {
    problems.push(`versionName "${versionName}" is not MAJOR.MINOR.PATCH (OPS-40, AC-168).`);
    return problems;
  }
  if (!Number.isInteger(versionCode) || versionCode < 0) {
    problems.push(`versionCode "${versionCode}" is not a whole number (AC-168).`);
    return problems;
  }
  const base = parsed.major * 1_000_000 + parsed.minor * 10_000 + parsed.patch * 100;
  const buildNumber = versionCode - base;
  if (buildNumber < 0 || buildNumber > 99) {
    problems.push(
      `versionCode ${versionCode} does not match versionName "${versionName}" under the formula ` +
      `MAJOR x 1,000,000 + MINOR x 10,000 + PATCH x 100 + build number (0-99); expected ${base}-${base + 99} (AC-168).`);
  }
  return problems;
}

export function checkVersionBump(oldCode, newCode) {
  const problems = [];
  if (!(newCode > oldCode)) {
    problems.push(`versionCode did not rise: was ${oldCode}, is now ${newCode}. Every build needs a strictly higher versionCode (AC-168).`);
  }
  return problems;
}

// AC-203: every server call carries X-Alvoraa-App-Version, read from
// web/js/app-version.js's one constant. If that constant ever drifted from
// build.gradle's versionName, the app would send a number the server never
// actually shipped with - APP_TOO_OLD/APP_VERSION checks on the server side
// would then be comparing against a fiction. Extracted the same crude way as
// build.gradle's own fields - this file is JS, not Groovy, but a small
// hand-written app has exactly one of these constants to find.
export function extractAppVersionConstant(jsText) {
  const match = /APP_VERSION\s*=\s*["']([^"']+)["']/.exec(jsText);
  return match ? match[1] : null;
}

export function checkAppVersionMatchesGradle(jsVersion, gradleVersionName) {
  const problems = [];
  if (!jsVersion) {
    problems.push("Could not find APP_VERSION in web/js/app-version.js.");
    return problems;
  }
  if (jsVersion !== gradleVersionName) {
    problems.push(
      `web/js/app-version.js's APP_VERSION ("${jsVersion}") does not match ` +
      `android/app/build.gradle's versionName ("${gradleVersionName}"). The app would send a ` +
      `version number on every call (AC-203) that the build it ships in does not actually have.`);
  }
  return problems;
}

// ── CLI ──────────────────────────────────────────────────────────────────────

function readVersion(path) {
  const text = readFileSync(path, "utf8");
  const version = extractVersion(text);
  if (!version) {
    console.log(`FAIL: could not find both versionName and versionCode in ${path}.`);
    process.exit(1);
  }
  return version;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const gradlePath = join(APP_DIR, "android", "app", "build.gradle");
  const current = readVersion(gradlePath);
  const problems = checkVersionFormat(current);

  const versionJsPath = join(APP_DIR, "web", "js", "app-version.js");
  const jsVersion = extractAppVersionConstant(readFileSync(versionJsPath, "utf8"));
  problems.push(...checkAppVersionMatchesGradle(jsVersion, current.versionName));

  const oldPath = process.argv[2];
  if (oldPath) {
    // Only a build.gradle that actually changed represents a new build. A
    // commit that leaves it untouched (a script or test fix elsewhere under
    // mobile/**) has nothing new to compare, so it must not be forced to
    // bump the version just to pass this check.
    const gradleChanged = readFileSync(oldPath, "utf8") !== readFileSync(gradlePath, "utf8");
    if (gradleChanged) {
      const old = readVersion(oldPath);
      problems.push(...checkVersionBump(old.versionCode, current.versionCode));
    }
  } else {
    console.log("NOT YET: comparing against the previous build's versionCode - pass the base branch's build.gradle as an argument (CI does this).");
  }

  if (problems.length) {
    console.log(`FAIL: ${problems.length} problem(s).`);
    for (const p of problems) console.log(`  - ${p}`);
    process.exit(1);
  }
  console.log(`OK: versionName "${current.versionName}", versionCode ${current.versionCode}.`);
}
