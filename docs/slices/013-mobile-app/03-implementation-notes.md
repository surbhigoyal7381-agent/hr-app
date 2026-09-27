---
slice: 013-mobile-app
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-09-17, continued 2026-09-22 (twice)
status: in progress — part 3 added (US-35-38, the real join screens). Local only. Nothing pushed.
branch: slice/013-mobile-app in .claude/worktrees/013-mobile-app (2026-09-17 entries) and
  .claude/worktrees/agent-a4e078558e4079082 (2026-09-22 entries), rebased onto origin/dev
  3ab09f1 (today's fetch - all five server steps are on dev now)
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

---

## 7. Stage 1 (US-31–34) and the stage-2 spike (2026-09-22)

Written after `00-impact-analysis-app-client.md` was approved. All five server steps
(013's own) are on `origin/dev` now, and slice 014 is long since merged - the blocker
this file's part 1 recorded above no longer applies to anything server-side. This
session's sandbox has **no Android SDK at all** (no `ANDROID_HOME`, no SDK directory,
only a bare `gradle` binary) - every claim below says plainly whether it was actually
run, or only reviewed by reading source.

### 7.1 Correction to my own earlier analysis

The impact analysis (and this file's part 1) said `android/` was not generated yet,
going by the 2026-09-17/18 dates on the notes. That was wrong: `android/` was already
generated and committed, with a manifest already holding exactly the five allowed
permissions. I found this by actually looking at the checked-out tree before building,
not by trusting the older notes - which is the whole reason to check rather than
assume. `README.md` said the same wrong thing and is fixed in this commit.

### 7.2 Stage 1: US-31 verified, US-32/33/34 built

| Story | What | Mechanism | Proven how |
|---|---|---|---|
| US-31 | Key guard | Verified, unchanged | `python3 scripts/check_tracked_keys.py` → clean; `ci.yml`'s `key-guard` job read, intact |
| US-32 | Three build types, version rule | **Build**: added a `pilot` build type (`.pilot` suffix) beside the existing `debug`/`release`; **Build**: `scripts/check_versions.mjs`, pure and tested, enforcing OPS-40's formula and that versionCode always rises | `node --test` (new tests pass); ran the script by hand against `origin/dev`'s real `build.gradle` - failed before I bumped the version, passed after |
| US-33 | Debug-only cleartext allow-list | **Build**: `android/app/src/debug/res/xml/network_security_config.xml` + a debug-only manifest fragment, permitting HTTP only to `localhost`/`10.0.2.2` (via `adb reverse` or the emulator), never a tenant. Android's own source-set rules keep both files out of pilot/release | `check_app.mjs` extended to read and check this file's actual content; `npm run check` clean |
| US-34 | No hidden powers | **Configure**: removed the Capacitor template's dormant Google-Services/Firebase Gradle hook (both `build.gradle` files) - dead code today, but a `google-services.json` copied in from elsewhere would have silently switched it on | `check_app.mjs` now fails if either file reappears; confirmed by re-running `npm run check` |

Also added Gradle wrapper validation to `mobile.yml` (checks the wrapper jar against
Gradle's own published checksum - no SDK needed for this one).

**What was not, and could not be, run here:** any real `./gradlew` build, an installed
APK, or the new CI steps on an actual GitHub Actions runner. The manifest-merger
behaviour of the debug-only files in particular still needs proving on a machine with
the real SDK.

### 7.3 Stage-2 spike 1: QR reading — chose jsQR 1.4.0

Compared against `zxing-wasm` 3.1.4 (the other option DevOps named in `07` §5, "after
the spike"). Checked with `npm view` before installing either:

| | jsQR 1.4.0 | zxing-wasm 3.1.4 |
|---|---|---|
| Unpacked size | 280 KB (mostly `.d.ts` files; the real bundle is one 257 KB file) | 3.68 MB |
| Form | Plain JS (webpack UMD bundle) | WebAssembly binary + JS glue |
| Auditable by our own CI | Yes - `check_app.mjs`'s text scanners can read every line | No - a compiled `.wasm` file is opaque to a text scan |
| Needs Google Play services | No | No (not a differentiator here) |

Chose **jsQR 1.4.0** for the size, the plain-JS auditability (matches how
`scripts/check_app.mjs` already works - it scans source text, not binaries), and
because reading pixels needs nothing beyond the `CAMERA` permission the app already
holds for the punch photo, where a native ML-Kit-backed scanner plugin would have
brought its own permission surface to re-audit and would not run on a pilot phone
with no Google Play services (the pilot phone table, AC-231, tracks this per phone).

**Vendored, not resolved at build time** (there is no bundler step; `web/*.js` files
are loaded as plain `<script>` tags, same as `host-check.js` and `photo.js` already
are): `node_modules/jsqr/dist/jsQR.js` copied byte-for-byte to
`web/js/vendor/jsqr.js`, its licence alongside, its SHA-256 pinned in
`scripts/check_app.mjs` (`VENDORED_FILES`) the same way `ci.yml` already pins
gitleaks's checksum. `checkWebFile`'s line-by-line scan (built for our own code) is
skipped for anything under `vendor/` and replaced by the hash pin, because that scan
otherwise flags a real, harmless URL in jsQR's own comments (an algorithm reference,
not a network call) as if it were ours.

Wrote `web/js/qr-decode.js` - a thin, pure wrapper (`decode(imageData, jsQRFn)`) around
the vendored decoder, taking the decoder function as an argument the same way
`photo.js` takes `makeCanvas` as one, so it needs no browser and no DOM to test.

**Proven, for real, in `test/qr-decode.test.js`:** a genuine 33×33 QR module matrix
(computed once with the `qrcode` npm package - never added to this project, since a QR
*reader* has no business depending on a QR *writer* - for the exact link shape
`host-check.js` expects: `https://ppj.alvoraa.co/enrol#t=<43-char code>`) is rendered
into a raw RGBA buffer with a quiet zone, the way a real camera frame would look, and
decoded back with the real vendored `jsqr.js`. It reads back byte-for-byte the same
link that went in, and that decoded text then passes `host-check.js`'s own rule
end-to-end. Also proven: a blank frame finds nothing (no false positive); a malformed
frame returns `null` rather than throwing; a missing decoder throws rather than
silently reporting "no code here" (fail closed). Six tests, all passing -
`node --test test/qr-decode.test.js`.

**What this does NOT prove:** that the camera-frame loop itself - grabbing frames fast
enough, at a size jsQR can actually read, from a real phone's camera - works well
enough in practice. That is a device question for when the scan screen (US-35) is
built, not a decoding-logic question, and the pilot's own timing measures (AC-191,
AC-232) are where it gets settled.

### 7.4 Stage-2 spike 2: device secret storage — chose `capacitor-secure-storage-plugin` 0.13.0

Compared two candidates found on npm:

| | `capacitor-secure-storage-plugin` 0.13.0 | `@aparajita/capacitor-secure-storage` 8.0.0 |
|---|---|---|
| Capacitor 8 support | `peerDependencies: "@capacitor/core": ">=8.0.0"` | ships its OWN copies of `@capacitor/core`, `/android`, `/ios`, `/app`, `/keyboard` as regular dependencies |
| Extra native surface | None beyond the storage itself | Pulls in the `App` and `Keyboard` plugins too, unasked |
| Extra Android permissions | None (`AndroidManifest.xml` is empty) | Not checked - ruled out before going further |
| Licence | MIT | MIT |
| Last published | 2026-01-10 (recent) | 2026-02-10 |

Ruled the second one out without installing it: pulling in three unrelated native
plugins (`App`, `Keyboard`, and a second copy of `core`/`android`/`ios`) to get one
storage call is exactly the "abstraction beyond what the task requires" `CLAUDE.md` §4
warns against, and each of those is its own permission and dependency surface to
re-justify for no reason this app has.

**Installed and reviewed `capacitor-secure-storage-plugin@0.13.0`** (`npm install
--save-exact`, then `npx cap sync android`):

- **Installs cleanly** against `@capacitor/core` 8.5.2 - no peer-dependency conflicts.
- **`cap sync` wires it in correctly with no manual edits**: `android/capacitor.settings.gradle`
  gained an `include` and a `projectDir` line, `android/app/capacitor.build.gradle`
  gained one `implementation project(...)` line. Both diffs are small and reviewed.
- **No extra Android permission**: its own `AndroidManifest.xml` is empty.
- **Its `android/build.gradle` matches our project's SDK levels exactly** (compileSdk,
  targetSdk 36, minSdk 24, AGP 8.13.0), and reads them from `rootProject.ext.*` the same
  way our own module does, rather than forcing its own - it will not drag the project
  onto a different SDK level.
- **Read its Java source** (`PasswordStorageHelper.java`): it genuinely uses
  `android.security.keystore.KeyGenParameterSpec` and the `AndroidKeyStore` provider
  with a `Cipher`, storing only the encrypted bytes in `SharedPreferences` - not the
  plugin's `Preferences`, and not plaintext. This is a structural read of the imports
  and class shape, not a full line-by-line security audit; I recommend the security
  engineer or test-automation engineer give it a closer read before the join flow ships
  against it.
- **Its API is exactly what US-44 needs and no more**: `get`/`set`/`remove` (plus
  `clear`, `keys`, `getPlatform`, unused for now) - one key, one string value.
- **Found and flagged a real risk to design around, not a defect in the plugin**: its
  *web* fallback (`SecureStoragePluginWeb`, used only if the app somehow ran in a plain
  browser instead of the native Android runtime) is plain `localStorage` plus base64 -
  no encryption at all. This path should never execute in the shipped app, but the
  stage-2 build should check `getPlatform()` (or `Capacitor.isNativePlatform()`) before
  trusting a read or write, and fail closed rather than silently accept the web
  fallback's answer. Noted here so it is not forgotten when the wrapper is actually
  written.

**What this does NOT prove, and cannot prove in this sandbox:** whether the Keystore
round-trip actually works at runtime - encrypt, store, restart the app, decrypt - on a
real device, and specifically on a **32-bit low-end phone**, which is exactly the
question DevOps's `07 §5` asked the spike to answer before pinning the version for
real. AndroidKeyStore's hardware-backed behaviour varies by chipset and OEM, and this
is a JS-bridge-driven native plugin: it cannot be exercised by a Node test the way
`jsqr` could, because there is no Capacitor runtime bridge outside a real (or emulated)
Android WebView. No wrapper module was written for it this time (unlike
`qr-decode.js`), on purpose - a wrapper around code nobody has run once yet would be
untested code pretending otherwise, and stage 2 proper is where it gets written and
actually exercised on the bench.

### 7.5 What is still open before stage 2 writes real screens

1. **Run the secure-storage spike's actual round-trip on the local bench**, ideally on
   one 32-bit or otherwise low-end pilot phone, before any join-flow code stores a real
   secret through it.
2. **Decide the runtime safeguard** for the web-fallback risk above (check
   `getPlatform()`/`isNativePlatform()`, fail closed) as part of writing the storage
   wrapper in stage 2, not left implicit.
3. Everything server-side is now on `dev` and unblocked - the only remaining
   dependency for stage 2 (US-35–38) is Android Studio/SDK access for anything past
   what plain Node can check, which is confirmed available on the bench (not in this
   sandbox).

---

## 8. The real join screens: US-35, US-36, US-37, US-38 (2026-09-22, same day)

Written straight after the spike, on the user's decision to skip a separate throwaway
storage-test screen and go straight to the real join flow - the join flow writing a
real secret through the chosen plugin **is** the on-device proof, once someone can run
it. Same sandbox, same limits as §7: no Android SDK, no emulator, no device.

### 8.1 What was built, file by file

| File | Mechanism | Why |
|---|---|---|
| `web/js/app-version.js` (new) | **Build**: one constant, `APP_VERSION`, sent as `X-Alvoraa-App-Version` on every call (AC-203) | The version header the server's `check_app_version()` reads has to come from somewhere; one small file, pinned against `build.gradle` (below), beats a string duplicated wherever a call is made |
| `web/js/api.js` (new) | **Build**: `checkCode`/`refuseCode`/`joinWithCode` over `fetch`, reading `code`/`values` at the top level of the body per `field_app_errors.py`'s real, shipped contract - never Frappe's `message` envelope for a refusal, never the English sentence (MA-30) | This is the one place the wire format is parsed; every screen downstream trusts it once, instead of re-deriving it |
| `web/js/join-screens.js` (new) | **Build**: a pure `screenFor(code, values, opts)` table, one entry per code in scope, returning heading/body/steps/buttons/footer exactly as 01b §7.12 writes them | Mirrors `field_app_errors.py`'s own shape (one table, one place) - and is the one part of this whole build that could be proven the same way `host-check.js` already was |
| `web/js/device-secret.js` (new) | **Build**: `save`/`load`/`clear` wrapping `capacitor-secure-storage-plugin`, refusing to read or write through anything but a real native platform (the spike's own flagged risk, now enforced in code, not just written down) | AC-217: the secret may never sit in `localStorage`, `Preferences`, or WebView storage - including the plugin's OWN web fallback, which is exactly that |
| `web/js/build-type.js` (new) + two per-build-type overrides under `android/app/src/{debug,pilot}/assets/public/js/` | **Build**: `host-check.js`'s `checkEnrolLink(text, buildType)` needs to know its own build type at runtime; nothing wired this before. Uses Android's own source-set asset merging - the same mechanism `network_security_config.xml` (stage 1) already relies on - so `cap sync`/`cap copy` never touch the debug/pilot copies | The alternative (a runtime guess, or trusting a value from the server) would have been exactly the kind of thing OPS-7/SEC-14 exist to prevent |
| `web/js/vendor/capacitor-core.js`, `web/js/vendor/secure-storage-plugin.js` (new, vendored + hash-pinned, same pattern as `jsqr.js`) | **Configure**: Capacitor's public JS API (`registerPlugin`, `Capacitor.Plugins`, `isNativePlatform`) is not auto-injected by the native side the way the low-level bridge is - it has to be loaded from web assets, same as any other script here | See §8.3 - this is the least proven part of the whole build |
| `web/index.html`, `web/js/join.js`, `web/css/app.css` (rewritten / new) | **Build**: the real screens - `first`, `camExplain`, `scan`, `checking`, `confirm`, `notMe`/`notMeDone`, `notice`, `joining`, `welcome`, and one generic `problem` screen driven by `join-screens.js` | Replaces the throwaway camera/GPS test page entirely - it served its purpose (§6) and is gone, not extended |

Every value the server sends is rendered with `textContent`, never `innerHTML`
(SEC-17, US-45) - `scripts/check_app.mjs`'s own lint rule stayed green through the whole
build, which is the cheapest proof available that this held.

### 8.2 What is genuinely proven (real test output, not claimed)

`npm test`: **63 passing**, `0` failing, including 25 new tests across `api.test.js`,
`join-screens.test.js`, `device-secret.test.js` and `build-type.test.js`. `npm run check`
(now `check_app.mjs` **and** `check_versions.mjs`): clean.
`python3 scripts/check_tracked_keys.py`: clean, 2,630 tracked files.

What that actually proves: the network layer reads a refusal's `code`/`values` correctly
and never trusts Frappe's `message` key for one; every in-scope server code (and every
client-made one) lands on a real screen with real words, including the two date-shaped
sentences (`QR_EXPIRED`'s always-dated form, `QR_USED`'s today/on-date branch);
`device-secret.js` never writes or reads through anything but a real native platform,
proven with a fake plugin that WOULD have quietly worked if the safety check were
missing; and the vendored files have not drifted from what was actually installed.

### 8.3 What is NOT proven, and cannot be proven in this sandbox

This is the boundary the user asked to be explicit about, restated plainly:

1. **The Capacitor JS bridge wiring itself.** `capacitor-core.js` must load before
   `secure-storage-plugin.js` (the second expects a global, `capacitorExports`, that the
   first defines) - this is read from the packages' own structure and Capacitor's
   documented "no bundler" pattern, not proven against a running app. **If this is wrong,
   the visible symptom on a real device would be a console error like
   `capacitorExports is not defined`, and every screen after `welcome` would fail to save
   the secret.** This is the single most important thing to check first on a real build.
2. **The actual Keystore round trip** - encrypt, store, restart the app, decrypt - on a
   real phone, still unproven exactly as the spike (§7.4/§7.5) already said, and now the
   real code path (`agreeAndFinish` → `device-secret.js.save()`) depends on it working.
3. **The camera scan loop and the file-picker decode path**, both written against
   standard web APIs (`getUserMedia`, `<input type=file>`) with no Capacitor plugin, the
   same way the retired test page already proved the camera itself works in this
   WebView (§6) - but reading a live, moving QR code fast enough is a different question
   from opening the camera, and only a real phone answers it.
4. **Permission-prompt timing** (`camExplain` before the OS prompt, `AC-182`): this build
   always shows `camExplain` on first launch rather than detecting an already-granted
   permission, because the Permissions API's camera support is inconsistent across
   WebViews and untestable here - a small, deliberate simplification, not a forgotten
   requirement.
5. **`CAMERA_DENIED`'s "Open phone settings" button** does not actually open Android's
   per-app settings page - no vetted plugin does that yet (that would be a third native
   plugin decision, not made in this increment). It re-attempts the camera prompt instead,
   which some WebViews do re-show unless the person chose "don't ask again"; "Choose a
   picture instead" is the button that reliably works today.
6. **The phone's model name** (`device_label`, AC-220) is sent as an empty string, not the
   real model - reading it needs `Capacitor.Device` or a `navigator.userAgent` guess,
   neither of which was part of the two building blocks this stage-2 spike was scoped to.
   Small, declared, and worth a quick decision before this ships past a debug build.
7. **`CONSENT_REQUIRED` / "Consent not given"** (the drift the impact analysis flagged,
   and the user already approved reusing `noticeAgain` for): it cannot actually occur
   anywhere in this build. `join_with_code` is always called with `agreed=1` (`api.js`),
   so the server never has a reason to create a phone in that state from this flow, and
   none of E1/E2/E3 (the only endpoints this build calls) return that code at all - only
   E4/E5/E9 do, none of which are called before a phone is joined. `join-screens.js`
   still falls back safely (the generic `unknownCode` screen, never a blank one) if that
   ever changes, but no dedicated handling was needed or built.
8. **`NOTICE_CHANGED` during `join_with_code`** is handled minimally: the same `notice`
   screen is re-shown with the server's new rows in place, not the full `noticeAgain`
   screen `01b` describes for US-42 (not built this increment). One known gap: that
   refusal's `values` do not carry the tick-box's own wording, so the fallback English
   text is used - correct today (there is only one notice version), would need a small
   server-side addition if a future version ever changed those exact words.

### 8.4 What I did not build, on purpose

- No `Check In` screen (US-39) - `welcome`'s **Check In** button shows a plain
  "not built yet" line rather than pretending to work or failing silently.
- No settings screen, no "what this app records", no remove-phone flow (US-43).
- No Hindi strings, no language switch on `first` - `01b`'s design shows one, but with
  Hindi text still machine-drafted and unchecked (D15), and no build-type-aware way yet
  to hide it in pilot/release (AC-224), leaving it out entirely is more honest than a
  toggle that does nothing.

### 8.5 What the user's own real-device build (running in parallel) will actually settle

In order of how much this build depends on each answer: (1) does the app even load
without a console error from the Capacitor bridge wiring; (2) does a join actually save
a secret through the Keystore plugin and survive an app restart; (3) does the camera
scan loop read a real, moving QR code fast enough to feel like "one scan"; (4) everything
in §7's own still-open list (the 32-bit round trip, the network/build-type changes).
