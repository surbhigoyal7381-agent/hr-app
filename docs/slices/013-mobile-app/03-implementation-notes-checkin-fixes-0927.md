# Field app check-in fixes (0.2.1) — implementation notes

Built locally on 27 Sep 2026, on branch `slice/013-checkin-fixes` (from `origin/dev`
6411f73), in its own worktree. **Nothing pushed. No pull request. No server, no
tenant, no `docker cp`.** Found by Surbhi on a real phone on 26 Sep 2026 (PPJ-0010 on
ppj.dev.alvoraa.co) and approved on 27 Sep 2026.

## What was wrong, and what changed

| # | What she saw | Cause | Fix |
|---|---|---|---|
| 1 | "Photo taken", but the camera never opened | `capturePunchPhoto()` opened the front camera on a hidden `<video>` and kept the first frame | A camera screen: live preview, **Take photo**, then a still with **Use photo** / **Retake**; **Cancel** goes home and sends nothing |
| 2 | Result said "At PPJ Head Office Chandigarh" while she was ~13 km away | The card printed the workplace name whenever one existed | `field_checkin` answers with `location` (workplace, radius, distance, `within`, accuracy); the card says "At …" only when `within` is true |
| 3 | Welcome said "Check in within 0 m" | Radius 0 (Frappe HR's "no limit") printed as a number | "Check in from anywhere" for 0 or none, on welcome, home and settings |
| 4 | Captured time 5 h 30 min early | App sent UTC with no mark; server read it as site time | App sends local time with its offset; server converts to the site's time zone |

## File by file

| File | Mechanism | What and why |
|---|---|---|
| `mobile/field-app/web/js/camera.js` (new) | build | The camera steps (open, take, retake, use, cancel, pause). Everything from the browser is passed in, so Node tests drive it with a fake camera. Stops the stream on use, cancel, failure, and when the app goes to the background. |
| `web/js/checkin.js` | extend | Camera screen wiring; `doPunch` opens the camera unless a photo is already kept (AC-205 Try again); `sendPunch` does location + save; result line from the server's `location`; rule line on home and settings; `captured_at` with offset; a fresh Check In press always takes a fresh photo. |
| `web/js/checkin-screens.js` | extend | Pure helpers: `formatDistance`, `ruleLine`, `whereLine`, `localTimeWithOffset`; OUTSIDE_WORKPLACE shows km above 1 km. |
| `web/js/join.js`, `web/js/signin.js` | extend | Welcome card rule line uses `ruleLine` (both screens draw the same card). |
| `web/index.html`, `web/css/app.css` | extend | The camera section and one script tag; three CSS lines (frame height, `[hidden]` for buttons, disabled look). Plain on purpose — the Material 3 redesign restyles it. |
| `alvoraa_portal/alvoraa_portal/field_checkin.py` | extend | `_where_it_was()` adds `location` to the success answer; `_validated_captured_at()` converts an offset-marked time with Frappe's `convert_utc_to_system_timezone`. |
| `android/app/build.gradle`, `web/js/app-version.js` | configure | 0.2.1 / versionCode 20100. `releases.json` unchanged (debug build, never in a store). `MIN_APP_VERSION` unchanged. |

## Decisions and assumptions

- **[ASSUMPTION] A denied or missing camera still allows the punch without a photo.**
  The old code did this silently (AC-200). The new screen says so plainly and offers
  **Try the camera again** and **Check in without a photo**. Dropping the second button
  would change AC-200; I did not.
- **The photo time is the moment of "Take photo"**, not the moment of sending. That is
  what `captured_at` is documented to mean, and Try again resends the same time with
  the same photo.
- **`within` is computed from the raw distance**, exactly as Frappe HR's
  `validate_distance_from_shift_location` compares it (not reduced by the GPS accuracy).
- **The photo shrink is unchanged.** photo.js is 640x480 at quality 0.6 (0.45 if over
  120 KB). The brief said "960x720, q0.7"; that is the size the camera is *asked* for,
  not the shrink. Nothing about it was changed.
- **The join flow was checked**: the QR scanner shows its preview on screen
  (`#scan-video`) and never captures a photo. Nothing to fix; a test pins it.
- No reverse geocoding, no map service.

## Server answer (new key on `field_checkin` only)

```json
"location": {"workplace": "PPJ Head Office Chandigarh", "radius_m": 0,
             "distance_m": 13216, "within": null, "accuracy_m": 14}
```

`within` is null when there is no workplace, a radius of 0, or no coordinates on the
workplace. The workplace coordinates are never sent (PRIV-6). `field_status` is
unchanged: its `workplace` block already carries the name and `radius_m` the rule line
needs.

## Tests and checks — what I actually ran

Own throwaway containers: `hrlocal-013c` (bench, mounts this worktree),
`hrlocal-013c-db` (its own MariaDB) and `hrlocal-013c-redis`; site `test013c`,
bootstrapped with hrms's `before_tests`. `hrlocal-bench`, `hrlocal-wa042`,
`hrlocal-128`, `hrlocal-oas` not used. One module at a time.

| Module (`bench --site test013c run-tests --module alvoraa_portal.tests.…`) | Result |
|---|---|
| `test_field_checkin_fixes_013` (new) | 13 tests, OK |
| `test_field_app_password_signin_128` | 59 tests, OK |
| `test_field_app_step1_013` | 15 + 13, OK |
| `test_field_app_step2_013` | 27 + 7, OK |
| `test_field_app_step3_013` | 41 + 9, OK |
| `test_field_app_step4_013` | 33, OK |
| `test_field_app_step5_013` | 28 + 3, OK |
| `test_field_app_step6_013` | 1 + 27, OK |
| `test_field_app_permissions_013` | 9, OK |
| `test_checkin_location` | 9, OK |
| `test_checkin_security_014` | 14 + 2, OK |
| **Total** | **310 tests, 0 failures**, all after the last server change |

| Check | Result |
|---|---|
| `npm test` (on an LF copy — see the CRLF note) | 174 tests, 174 pass |
| `npm run check` (LF copy) | OK: app config, dependencies and bundled files; OK: 0.2.1 / 20100 |
| `python scripts/check_app_integrity.py` | 654 checks, OK |
| `python scripts/check_min_app_version.py` | OK (floor 0.1.0) |
| `ruff check` (0.6.9, hrms config) on the two changed .py files | All checks passed |
| Debug APK (`npm ci --ignore-scripts`, `npx cap sync android`, `gradlew.bat assembleDebug`) | BUILD SUCCESSFUL; `C:\Users\Dell\Downloads\alvoraa\alvoraa-app-0.2.1-debug.apk`, versionName 0.2.1-debug, versionCode 20100. The two capacitor*.gradle files restored after sync. |

**CRLF note:** in this Windows worktree the three vendored files are CRLF, so the
two vendored-hash tests fail there (172/174) — the known trap. On an LF export of the
commit (`git -c core.autocrlf=false archive`) everything passes.

**Gradle note:** Android Studio's JBR on this machine is Java 25, which Gradle 8.14.3
cannot run ("Unsupported class file major version 69"). The APK was built with
`C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot` instead.

## Non-functional check, against the code written

| Dimension | Verdict | Why |
|---|---|---|
| Performance | neutral | Two small reads added to a successful punch (the Shift Assignment and Shift Location lookup the refusal path already used). No loops. |
| Security | neutral | No new endpoint or permission. The answer adds a distance about the caller's own punch; no workplace coordinates. All new text set with `textContent`. |
| Reliability | improves | The camera is stopped on every way out, including cancel while the phone is still asking and the app going to the background. An aware `captured_at` no longer risks a naive-vs-aware compare. |
| Scalability | neutral | Per-punch cost is constant. |
| Maintainability | improves | Camera steps in one testable module; wording in pure helpers with tests. |
| Data integrity | improves | `alvoraa_captured_at` stored in site time for 0.2.1 phones. |
| Compliance / privacy | improves | The person now sees and chooses the photo that is sent. Photo still memory-only and private (PRIV-7). No personal data in logs. |

## Known gaps — honest list

- **Old phones (0.2.0 and earlier) still store the photo time 5 h 30 min early** until
  they update. They send UTC with no mark and the server cannot tell it apart from
  site time. *Temporary debt* — removed as phones move to 0.2.1. (If wanted: the
  server could treat an unmarked time from an app older than 0.2.1 as UTC, using the
  version header. Not built — it was not in the approved fix.)
- **The rule line trusts the radius even when HR Settings' "allow geolocation
  tracking" is off.** Then Frappe HR does not enforce the radius, but home still says
  "Check in within 200 m of X". The result card is honest in that case ("About 380 m
  from X"). *Question for the user*: should the rule line say "from anywhere" when
  tracking is off?
- **Frappe HR filters the Shift Assignment by the punch's shift; our lookup
  (`_shift_location_for`) does not.** Same as before this fix; an employee with two
  assignments on different locations could see a different workplace named. *Acceptable
  simplification*, unchanged.
- **The camera screen is not tested in a real browser here.** There is no headless
  browser harness in `mobile/field-app/test`. camera.js is driven by Node tests with a
  fake `getUserMedia`, `<video>` and shrink (preview, take, use, retake, cancel,
  cancel-while-opening, denied, no camera, pause). The DOM wiring in checkin.js needs
  the phone. *Intentional trade-off*; the APK is ready for that check.
- **"Open phone settings" for a denied camera is still a retry**, as before (no
  plugin to open Android's per-app settings page).
- Work board row not added: the main checkout was being refreshed by another session
  and the brief said not to touch it.

## What else moved while I worked

Branch started from `origin/dev` 6411f73. No other commits were brought in.
