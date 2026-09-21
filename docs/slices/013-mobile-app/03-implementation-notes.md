---
slice: 013-mobile-app
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-09-17
status: in progress — part 1 of many (app guard and skeleton). Local only. Nothing pushed.
branch: slice/013-mobile-app in .claude/worktrees/013-mobile-app, from origin/dev 9138251
---

# 013 — implementation notes (written as the work goes)

## 0. Read this first

1. **Only the work that needs neither slice 014 nor Android Studio is built.** Three commits,
   all on `slice/013-mobile-app`. Not in local `dev`, not pushed.
2. **Every server story waits for slice 014 to be in local `dev`** (checked 2026-09-17: the
   014 branch is at `40b8b55`, local `dev` and `origin/dev` are still `9138251`).
3. **Everything that builds an Android project waits for Android Studio** (not installed).
4. No Frappe tests were run, because no server code changed. The bench was not used.

## 1. Base, and what else moved

- Worktree made from `origin/dev` `9138251` (the 010 + 012 + F1 release, now pushed).
- Fetched again before committing: `origin/dev` unchanged. Nothing came in.
- **Another session's worktree `ci-fix-9138251`** (board: CI test fixes, "possibly ci.yml
  site config") has **no commits and no edits yet**. My `ci.yml` change is a **new job**
  placed between `lint` and `test-python`; it does not touch the test job. Low clash risk;
  if both land, keep both.
- **Slice 014** adds one step inside the `lint` job, before Semgrep. My change is outside
  that job, so the two do not overlap textually.

## 2. What was built, commit by commit

### d9b900c — key guard before any app key exists (US-31, OPS-37, OPS-71, SEC-23)

| File | Mechanism | Why |
|---|---|---|
| `.gitignore` | Configure: key and secret patterns, `*.apk`, `*.aab`, `android/app/release/`, `android/app/build/` | OPS-37 list plus OPS-71's build outputs |
| `scripts/check_tracked_keys.py` (new) | Build: reads `git ls-files`, fails on any key-like name or folder | `git add -f` walks past `.gitignore`; this checks what git really tracks. Run it by hand before every push |
| `.github/workflows/ci.yml` | Extend: **new job `key-guard`** (tracked-file check + gitleaks 8.30.1, checked against its published SHA-256 `551f6fc8…70eb`, scanning only the new commits) | **Deviation from DevOps §4 gate 2** ("one step at the end of the lint job"): the scan needs full history (`fetch-depth: 0`) and the lint checkout is shallow. A separate job also stays clear of 014's lint step. No path filter |

### c135020 — Build Image skips app-only pushes (OPS-72, C-13)

`build-image.yml` push trigger gets `paths-ignore: mobile/**, .github/workflows/mobile.yml`.
`ci.yml` has no filter. `deploy.yml` unchanged.

### 06d813d — app skeleton, host allow-list, no-SDK checks

| File | What |
|---|---|
| `mobile/field-app/package.json`, `package-lock.json`, `.nvmrc` | Capacitor 8.5.2 exact (`core`, `android`, `cli`), Node 24. Lock file made with `npm install --package-lock-only`; `npm ci --ignore-scripts` used after |
| `capacitor.config.json` | No `server` block; WebView debugging off; mixed content off; `CapacitorHttp` and `CapacitorCookies` switched off globally (OPS-79) |
| `web/index.html` | Placeholder page with the content policy (`connect-src https://*.alvoraa.co`, `object-src 'none'`, scripts only from the app) |
| `web/js/host-check.js` | `checkEnrolLink(text, buildType)`: https only, no user part, no port, path `/enrol`, no query, host `<tenant>.alvoraa.co` (or `<tenant>.dev.alvoraa.co` in pilot and debug, never release), no punycode, 43-character code in `#t=`. Otherwise `QR_NOT_ALVORAA`. Pure, no network |
| `scripts/check_app.mjs` | Fails on: `server` block or debugging in config; loose pins; tracking/crash/ads/Firebase libraries (whole lock tree); outside URLs, CDNs or local addresses in the bundle; HTML written from strings (unless a reviewed `// safe-html:` line); Android permissions outside the five, cleartext, backup on (manifest check says **SKIPPED** until `android/` exists) |
| `test/host-check.test.js` | 26 hostile links × 3 build types refused with a fetch spy showing 0 calls; tenant link passes; dev host only outside release (AC-172) |
| `test/check-app.test.js` | Each rule fails when broken, including `ACCESS_BACKGROUND_LOCATION` (AC-177), a Firebase library (AC-178), a CDN URL, `innerHTML` (AC-223) |
| `.github/workflows/mobile.yml` (new) | On `mobile/**` changes: `npm ci --ignore-scripts`, `npm test`, `npm run check` |
| `README.md` | What never goes in the folder; what waits for Android Studio |
| `.gitignore` | `.gradle/`, `android/build/`, plugin build output |

The checker caught real problems on its first run: example links in comments inside the
bundle. They were moved out of the bundle into the tests.

## 3. Commands run and what they said

| Command | Result |
|---|---|
| `python scripts/check_tracked_keys.py` (clean tree) | OK, 2426 tracked files |
| Same, after `git add -f test.jks google-services.json …/android/app/build/x.txt` (unstaged and deleted straight after, never committed) | **FAIL**, listed all three, exit 1 |
| `python -c "yaml.safe_load(...)"` on `ci.yml`, `build-image.yml`, `mobile.yml` | All parse; `build-image.yml` push has `paths-ignore` |
| `npm view @capacitor/{core,cli,android}@8.5.2` | exist; cli needs Node ≥ 22 |
| `npm ci --ignore-scripts` | 98 packages |
| `npm test` | **11 tests, 11 pass** |
| `npm run check` | OK (manifest check SKIPPED: no `android/`) |
| `python scripts/check_tracked_keys.py` after the last commit | OK, 2438 tracked files |
| Secret grep over `mobile/` (excluding `node_modules`) | nothing but the words in tests and the host check; lock file resolves only from `registry.npmjs.org` |

**Not run:** the GitHub workflows themselves (nothing is pushed), gitleaks (CI only; not
downloaded here), any Frappe test, any Android build.

## 4. Waiting, and why

| Work | Waits for |
|---|---|
| Step 0 web pin tests, US-4, US-1, US-2 (+ one revoke function), and every other server story | **Slice 014 in local `dev`** (it changes `field_checkin.py`, which these pin and change) and a free bench |
| `npx cap add android`, Android manifest check on a real project, Gradle wrapper validation, debug builds, `adb reverse` route (OPS-84) | **Android Studio 2025.2.1+ with its SDK** on this PC |
| Built-package checks (apkanalyzer, debuggable, network rules, ≤ 10 MB) | Android Studio, before the first pilot build |
| Spike: secure-storage plugin, jsQR vs zxing-wasm (OPS-78), mock-location plugin, native HTTP with the global switch off and redirects refused | Android Studio and a USB pilot phone |
| Server codes table vs app table check; copied capture-code drift check (OPS-80) | The server codes file (after 014) and the app's copy of the capture code |
| Signing keys, pilot workflow, Firebase | Much later, on Surbhi's word. **No key made** |

## 5. Decisions and gaps — declared

- **App ID `co.alvoraa.app`** (Surbhi, 2026-09-18; replaced the placeholder `co.alvoraa.fieldattendance`). An Android app ID cannot change after the first store release.
- **Key guard is its own CI job**, not a lint step (reason in §2).
- The key guard and `mobile.yml` have never run on GitHub. The first push will be their
  first real run.
- NFR dimensions, against the code written so far: security **improves** (keys cannot be
  tracked, bundle and permission rules are enforced); maintainability **neutral** (new
  folder, self-tested checks); performance, reliability, scalability, data integrity,
  privacy **neutral** (no server change yet).

---

## 6. The Android project and the first debug build (2026-09-18)

Commits `696ab7b` (app ID `co.alvoraa.app`, Surbhi's decision) and `8b9b966`.

### What was done

| Step | Result |
|---|---|
| `npx cap add android` with the pinned Capacitor 8.5.2 | Project generated: AGP 8.13.0, Gradle 8.14.3, compileSdk and targetSdk 36, minSdk 24 |
| Manifest hardened | The five allowed permissions only; `allowBackup="false"`; cloud-backup and device-transfer rules exclude everything |
| Build types | Debug gets `co.alvoraa.app.debug` and `-debug` in the version name (OPS-38). Signed with Android's own debug key. **No key of ours was made** |
| Versions | `versionName 0.1.0`, `versionCode 10000` (OPS-40 formula) |
| Page | Honest option (a): the bundled page says it talks to no server, and tests the phone's camera (with the real 640x480 / JPEG 0.6 shrink) and its position against the server's 100 m rule. `web/js/photo.js` holds the size rules, with tests |
| `./gradlew assembleDebug` | **BUILD SUCCESSFUL in 4m 47s.** APK 4.0 MB |
| APK checked with `aapt2 dump` and `apksigner verify` | ID `co.alvoraa.app.debug`, version `0.1.0-debug`, target 36, signer "CN=Android Debug" |
| Instructions for Surbhi | `docs/slices/013-mobile-app/09-install-the-test-app.md`; a copy of the APK at `C:\Surbhi-Git\hrlocal-data\mobile-builds\alvoraa-attendance-0.1.0-debug.apk` (outside git) |

**Permissions in the built APK:** `INTERNET`, `ACCESS_NETWORK_STATE`, `CAMERA`,
`ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`, plus AndroidX's own
`co.alvoraa.app.debug.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION`, which is a
permission the app defines for itself, not one it asks of the phone. **The
built-file check (gate 5) must allow that one by name** or it will fail on a
library-added permission that is harmless.

### Why not the web check-in page in a debug build

The other option was to point the shell at the web check-in page on a dev tenant
in debug builds. I did not: the app would then load a **remote page inside the
native shell**, which the approved brief (section 5, point 2) and OPS-3 rule out
for this increment, and it would need a `server` block that this slice's own CI
check refuses. The camera and GPS are tested on the phone anyway, in our own page.

### Bad news: the JDK pin is wrong

DevOps OPS-77 says "JDK 21: Android Studio's bundled copy". **The installed
Android Studio bundles Java 25**, and Gradle 8.14.3 refuses it ("Unsupported
class file major version 69"). I downloaded Temurin **JDK 21.0.12.1+1**
(checksum checked against Adoptium's published SHA-256) and unpacked it to
`C:\Users\Dell\tools\jdk-21.0.12.1+1`. Nothing was installed system-wide and no
machine-wide environment variable was changed; the build sets `JAVA_HOME` for
that one command. **To build:**

```
set JAVA_HOME=C:\Users\Dell\tools\jdk-21.0.12.1+1
cd mobile\field-app\android
gradlew assembleDebug
```

`android/local.properties` (git-ignored) holds
`sdk.dir=C:/Users/Dell/AppData/Local/Android/Sdk`. Forward slashes matter: with
backslashes, Java reads the path as escape characters and the build fails with
"The filename, directory name, or volume label syntax is incorrect".

**For DevOps:** OPS-77 should say "JDK 21, from Studio only while Studio still
bundles 21; otherwise a pinned Temurin 21", and CI should use Temurin 21.

### Checks run

| Check | Result |
|---|---|
| `npm test` | **17 tests, 17 pass** (host allow-list, the check rules, the photo size rules) |
| `npm run check` | OK. The Android permission check now runs on the real manifest instead of saying SKIPPED |
| `python scripts/check_tracked_keys.py` after staging | OK, 2497 tracked files |
| `git status` | `android/build`, `.gradle`, `local.properties` and the generated `assets/public` copy are all ignored |

**Not done:** installing on a phone (none attached to this PC), so "it installs"
is unproven - Surbhi's test will show that. No push, no deploy, no bench use.

---

## Phone test results, and two decisions they forced (2026-09-18)

Surbhi installed the debug APK on a **OnePlus** phone and ran the first screen.

| Measured | Result |
|---|---|
| Photo | 480 x 640, quality 0.6, **10 KB** |
| GPS accuracy, outdoors | **12-14 m** |

Both decided by Surbhi on 2026-09-18, on the recommendation below.

### Photo: raise to 960 x 720 at quality 0.7

10 KB is smaller than it needs to be. At 200 staff checking in 22 days a month,
the whole estate costs 44 MB a month now and about 198 MB at the higher setting -
on a server with 43 GB free.

The reason to spend it: a 10 KB photo is fine for a glance, and not good enough to
settle "that wasn't me". The photo is evidence that cannot be recreated later, so
it should be worth having.

### Geofence: 100 m minimum, store the accuracy, refuse above 50 m

12-14 m outdoors is ordinary, not good, and it is the **best** case - indoors, in a
shop or a warehouse, expect 30-50 m.

Three consequences for the design:

1. **Minimum radius 100 m.** A 25 m fence around a store would tell someone standing
   at the counter that they are not there.
2. **Every check-in stores its accuracy**, not just the position. A reading at 14 m
   and one at 200 m are different facts; without the accuracy column they are
   indistinguishable forever after.
3. **Refuse readings worse than 50 m** and ask the person to step outside and try
   again, rather than silently accepting a position that means nothing.

### Still unproven

Everything that touches the server: consent gate, enrolment, field-worker
designations, photo check-in, device register. It waits for slice 014 to land, because
it edits the same check-in files.
