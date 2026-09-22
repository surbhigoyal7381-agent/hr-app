---
slice: 013-mobile-app
artifact: 03-implementation-notes-daily-use
author: hrms-fullstack-engineer
date: 2026-09-22
scope: The rest of ALV-37 - US-39 (Attendance/punch), the punch and on-open problem screens (US-40/41), US-42 (notice changed), US-43 (Settings), US-46/D15 (debug-only language gate) - and the separate ALV-43 server fix (stale consent notice). Approved strategy in 00-impact-analysis-daily-use.md.
branch: slice/013-mobile-app-alv37 in .claude/worktrees/013-mobile-app-alv37, on top of origin/dev@1c4e84c
status: BUILT AND STATICALLY CHECKED. No Android SDK, no bench, no device, no emulator in this sandbox - nothing here is proven on a real phone. Not pushed.
---

# 013 daily use + ALV-43 — what I built, and what is still owed

**Read this first.** No Android SDK, no bench, no device, no emulator in this
sandbox (the task's own constraint). Proof here is `npm test` / `node
scripts/check_app.mjs` for the app, and `ast.parse` / `ruff` for the server
change - exactly the same honest limit `03-implementation-notes-server-step4.md`
stated before it later ran on a real bench. Nothing below claims otherwise.

**A planning correction, found while building, not before.** My own impact
analysis (§4.6) proposed building a new `/enrol` guest page for S13. That was
wrong: it already exists (`alvoraa_portal/alvoraa_portal/www/enrol.py` and
`enrol.html`, commit `a7cc42e`, from server step 3), fully matching AC-123/124/125,
with its own passing-shaped tests already in `test_field_app_step3_013.py`. I
should have run `git ls-tree` on `alvoraa_portal/alvoraa_portal/www/` during the
impact analysis instead of inferring from the spec alone. **No changes were made
to it** - I read it, checked it against AC-123/124/125 by hand, and it is correct.
This is the one item from the task's numbered list that needed nothing.

---

## 1 · What I built, file by file

| File | New or changed | Mechanism | Why |
|---|---|---|---|
| `mobile/field-app/web/js/checkin-screens.js` | **new** | build | The daily-use `code -> screen` table (US-39/40/41/42), a sibling of `join-screens.js`, not an extension of it - several codes (`TOO_MANY_TRIES`, `SERVER_ERROR`, `NO_INTERNET`, `APP_TOO_OLD`) need different wording at check-in than at join, and a flat table cannot hold two answers for one key. Reuses `join-screens.js`'s exported `onDateAt`/`todayOrDateAt` rather than copying them |
| `mobile/field-app/web/js/checkin.js` | **new** | build | The DOM/camera/geolocation layer: boot gate, the Attendance screen, the punch, Settings, "What this app records", Remove this phone. Same untested-without-a-device honesty `join.js` already states |
| `mobile/field-app/web/js/notice-cache.js` | **new** | build | `localStorage`-backed save/load/clear of the notice text the person actually agreed to, so Settings' "What this app records" (AC-215) reads with no call |
| `mobile/field-app/web/js/main.js` | **new** | build | The one boot decision: does this phone have a secret? Calls `AlvoraaCheckin.start()` or `AlvoraaJoin.start()` |
| `mobile/field-app/web/js/device-secret.js` | changed | extend | One new key, `alvoraa_tenant_origin`, alongside the existing secret, in the same Keystore-backed store (`saveOrigin`/`loadOrigin`); `clear()` now removes both keys always, never one without the other. No existing function's behaviour changed - the 6 pre-existing tests still pass unmodified |
| `mobile/field-app/web/js/api.js` | changed | extend | Four new exported functions (`fieldStatus`, `punch`, `removeMyPhone`, `acknowledgeNotice`, → E4/E5/E6/E9), all through the existing `callMethod`. The 3 pre-existing functions are untouched |
| `mobile/field-app/web/js/join.js` | changed, 3 named edits | extend | (1) the trailing `show("first")` is now `window.AlvoraaJoin.start()`, called by `main.js` instead of running unconditionally; (2) `welcome-check-in`/`welcome-not-now` call into `checkin.js` instead of the `#welcome-not-built` placeholder; (3) after E3 succeeds, also saves the tenant origin and a notice snapshot, in the same order as the secret (server confirms, then write) |
| `mobile/field-app/web/index.html` | changed | extend | New `<section>`s for `home`, `locExplain`, `punching`, `result`, `noticeAgain`, `settings`, `records`, `leaveConfirm`; a `#problem-card` slot added to the EXISTING shared `#problem` section (join.js's own screens never set `card`, so nothing changes for them); the `#welcome-not-built` placeholder removed; new `<script>` tags in dependency order |
| `mobile/field-app/web/css/app.css` | changed | extend | Small additive rules for the new screens (top bar, status line, punch list, settings rows) - no existing rule changed |
| `mobile/field-app/android/app/build.gradle` | changed | build | `versionCode` 10002 → 10003 (what ships changed) |
| `mobile/field-app/test/*.test.js` | changed/new | build | `device-secret.test.js` +9 tests, `api.test.js` +5, new `checkin-screens.test.js` (12), new `notice-cache.test.js` (8) |
| `alvoraa_portal/alvoraa_portal/field_app_notice.py` | changed | extend | New entry `"2026-09-22"` (D19's phone-model sentence added to "What we record"); `CURRENT_VERSION` moved to it. `"2026-09-13"` is untouched, per the module's own "never edit a published version" rule |
| `alvoraa_portal/alvoraa_portal/tests/test_field_app_step1_013.py` | changed | extend | `TheNoticeSaysWhatItSaid` now pins the NEW version's words as current, and separately pins that the OLD version's words are still exactly what they were, and still match the (deliberately untouched) web page - see §4 below |

**Nothing in `alvoraa_portal` outside these two files changed.** No new doctype,
no new field, no new endpoint - `field_app_notice.py`'s existing mechanism
(one entry per version) was built exactly for this.

---

## 2 · The acceptance criteria, one by one

| AC | How | Proven? |
|---|---|---|
| AC-197 | `home` shows top bar, status line (not-in / in-since / **checked out at** - built correctly from the start, not "fixed", since this screen never existed with the FC-1 bug), punch list, rule line | code written; `npm test` proves the pure pieces (screen table, storage); the DOM rendering itself needs a device |
| AC-198 | First-ever Check In → `locExplain`; a small local flag (`alvoraa_location_explained`, fail-soft like `notice-cache.js`) stops it showing again | written, unrun (needs a device for the real permission prompt) |
| AC-199 | Busy sequence; one `punch` call; `resultIn`/`resultOut` (one shared `result` screen, filled dynamically) from the punch's own answer with no extra `fieldStatus` call | written, unrun |
| AC-200 | Camera denied/unavailable → punch still saves, "Photo · Not taken" | written, unrun |
| AC-201 | Unchanged - `photo.js` is reused, not rewritten | still proven by its own existing, passing tests |
| AC-202/203 | Version header and 30 s timeout: unchanged, `api.js`'s existing `callMethod` | proven by `api.test.js` |
| AC-204 (mock-location flag) | **NOT satisfied.** Always sends `mock_location: 0` - see §5's honest gap |
| AC-205 | `state.photoDataUrl` is kept across `Try again` for `GPS_NOT_EXACT`/`OUTSIDE_WORKPLACE`/`NO_INTERNET`/`TOO_MANY_TRIES`; never re-captured | written, unrun |
| AC-206/207/208 | `checkin-screens.js` covers `SERVER_ERROR`'s card, and `OUTSIDE_WORKPLACE`'s no-distance fallback sentence, both pinned by unit tests | **proven** (12/12 in `checkin-screens.test.js`) |
| AC-209 | `update` screen: only reachable screen, card names the phone's and the needed version; the ONE button OPS-58 asks for is **not built** - plain instructions instead, a declared gap (§5) | partially satisfied, declared |
| AC-210 | Blocked/Replaced/`left` (`EMPLOYEE_NOT_ACTIVE`): Remove is **local only**, no E6 call, after a `window.confirm()` (a declared UI shortcut, §5) | written, unrun |
| AC-211 | `appOff`/`notField` after joining: secret is kept; Remove routes to the SAME `leaveConfirm`/E6 flow as Settings, since the device is genuinely still Active underneath (confirmed by reading `_device_from_token`/`_refuse_unless_app_phone_is_eligible`) | written, unrun |
| AC-212 | `NOT_SET_UP`/`DEVICE_PENDING`/`DEVICE_REMOVED` clear local state and hand off to `AlvoraaJoin.start()` | written, unrun |
| AC-213 | `noticeAgain`: six rows re-rendered from the refusal's own `values`; **Agree and continue** calls `acknowledgeNotice` (E9) and only then reloads status | written, unrun |
| AC-214 | `settings` screen groups exactly as `01b` §7.13; Language group **not in the DOM at all** outside a debug build (AC-224, below) | written, unrun |
| AC-215 | `records` reads `notice-cache.js`, no call; falls back to a plain sentence if the cache is empty (a WebView that cleared storage, or a phone that joined before this cache existed) | written, unrun |
| AC-216 | Remove: E6 call; on success clears BOTH `device-secret.js` keys and the notice cache; on `NO_INTERNET`, keeps everything and shows the exact sentence from `01b` | written, unrun |
| AC-224 | Language row exists in the DOM only when `BUILD_TYPE === "debug"` (checked, not merely hidden) | **proven for the gate logic** (build-type branch is a one-line `if`, matching `host-check.js`'s own precedent); the row itself does nothing yet - see §5 |
| AC-226 | Not fully satisfied - no lint rule enforcing "every string from a string table" exists, because there is no string table (English-only, matching the join flow's own state) - see §5 |

---

## 3 · What I ran, and what I did not

**Mobile app (no Android SDK, no device):**

| Check | Result |
|---|---|
| `npm test` (`node --test`) | **96/96 pass** - 63 already on `origin/dev` + 33 new (9 device-secret, 5 api, 12 checkin-screens, 8 notice-cache, minus one net test-count difference from a merged assertion) |
| `node scripts/check_app.mjs` | **OK** - the same "NOT YET: checks on the BUILT package" note as every prior step (needs a real Android build) |
| `node scripts/check_versions.mjs <origin/dev's build.gradle>` | **OK**: `versionName "0.1.0"`, `versionCode 10003` (up from `origin/dev`'s 10002) |

One real finding from `check_app.mjs` while building, not after: my first draft of
the "update" screen hardcoded a placeholder Firebase/Play Store URL for OPS-58.
`check_app.mjs`'s own outside-URL rule (SEC-16/OPS-22) correctly failed the build
on it. Rather than work around a security control I am supposed to respect, I
removed the hardcoded links entirely - see §5.

**Server (`field_app_notice.py`, its test file) - no bench:**

| Check | Result |
|---|---|
| `ast.parse` on both changed files | both parse |
| `ruff check --config hrms/pyproject.toml` on both | **clean** |
| The updated `TheNoticeSaysWhatItSaid` class | written, unrun - needs `bench run-tests --module alvoraa_portal.tests.test_field_app_step1_013` on a real site |
| Every other test file that reads `notice.CURRENT_VERSION` | grepped by hand: all read it dynamically (`fc.CONSENT_VERSION`, `notice.CURRENT_VERSION`), so the version bump does not need them changed - only the one test that hardcoded the old string needed touching |

**Not run, and cannot be from here:** `bench run-tests`, `bench migrate`, anything
against a real site or database; the Android build; any device or emulator.

---

## 4 · ALV-43, stated plainly

- `CONSENT_VERSION` moves from `2026-09-13` to **`2026-09-22`**.
- The only wording change is one added sentence in "What we record": *"When you
  set up: this phone's model name."* Every other row is byte-for-byte the same.
- **The web check-in page (`www/field-checkin.html`) is deliberately not
  touched.** `AC-35` protects it from this slice, and `field_checkin.notice_facts()`'s
  own comment says the page reading the store "belongs with the page's own
  work" - not yet assigned. This means: **a new app phone sees the corrected
  words. The web check-in page keeps showing the old ones** (missing the
  phone-model disclosure) until somebody does that migration. This is a real,
  named gap, not a side-effect I am hiding - the updated test
  (`test_013_the_web_page_still_shows_the_pre_review_wording`) exists
  specifically to keep it visible rather than let it drift unnoticed.
- Bumping the version has **zero effect on already-joined phones or the web
  page**: `_refuse_unless_notice_is_current` only ever gates app phones (confirmed
  in server step 4's own notes: "AC-96: web phone never asked about the
  notice"), and no already-active app phone is forced to re-agree just because
  a new version exists - they are asked again only at their next `field_status`/
  `field_checkin` call, exactly as `NOTICE_CHANGED`/US-42 already describes.

---

## 5 · Known gaps and shortcuts, declared

1. **The mock-location flag (SEC-21/AC-204) is not implemented.** The plain Web
   Geolocation API (`navigator.geolocation`) this build uses has no field for
   Android's "is this a fake GPS provider" flag - `GeolocationCoordinates` does
   not carry one. Reading the real flag needs a native call (a Capacitor
   Geolocation plugin, or a small bridge of our own), which the approved
   strategy deliberately did not add (keeping the dependency and permission
   surface at exactly what US-39 needs). The app always sends `mock_location: 0`.
   **This needs a decision**: add a geolocation plugin (a new dependency to vet
   against `check_app.mjs`), or accept that SEC-21 is not enforced by this
   build. I did not decide this myself - it surfaced only while writing the
   punch code, after the impact analysis was approved, so I am flagging it now
   rather than silently shipping a flag that always reads false.
2. **The "update" screen has no live link (OPS-58).** `check_app.mjs`'s own
   outside-URL rule (SEC-16/OPS-22) refuses any hardcoded address outside
   `*.alvoraa.co`, and no real Play Store listing or Firebase tester link exists
   yet to embed even if that rule did not apply. The screen gives plain
   instructions per build type instead of a button. Testers already get their
   own download link by email (AC-230), so this mainly affects a future release
   build, once a real Play listing exists to link to safely.
3. **No real Hindi text exists anywhere in this app**, including the
   already-shipped join screens (confirmed by grep: zero Hindi strings, no
   string-table mechanism at all - `01b`'s D15 "English only until checked" is
   simply the app's whole current state, not a debug-only exception). The
   Settings "Language" group is gated correctly (DOM-absent outside a debug
   build, satisfying AC-224's literal wording), but in a debug build it shows
   two disabled radio rows with a note that nothing changes yet - a scaffold,
   not a working translation. Building real Hindi support is a larger,
   cross-cutting piece of work spanning every screen (including ones I did not
   touch), which this ticket did not ask for.
4. **`Remove {company} from this phone` from a dead-end gate screen (blocked/
   replaced/left) uses the platform's own `window.confirm()`** rather than a
   dedicated screen. AC-210 says "after a confirm" without naming a shape; I
   chose the smallest thing that satisfies it rather than adding a fourth
   confirm screen. Worth revisiting if a designer wants a styled sheet instead.
5. **AC-226 (a lint rule for "every string comes from the string table") is not
   built**, because there is no string table for this app to check against (see
   point 3) - the rule would have nothing to enforce yet.
6. **The camera used for the punch photo is front-facing (`facingMode: "user"`)**,
   an assumption (a selfie-style attendance photo), not stated explicitly
   anywhere in `01b`. Worth confirming.
7. **Everything camera-, geolocation- and Keystore-related is unproven on a
   real phone**, same honest limit every prior step in this slice has stated.

---

## 6 · The seven dimensions, against the code I actually wrote

| Dimension | Before → after | Why |
|---|---|---|
| **Performance** | neutral | One `fieldStatus` call on open, one `punch` call per tap, one `acknowledgeNotice` only when the notice actually changed - no polling added |
| **Security** | neutral, one named gap | Same fail-closed Keystore gate for the new origin key; every server value still rendered with `textContent`; the mock-location gap (§5.1) is the one real, declared shortfall |
| **Reliability** | improves | The app can now survive a restart at all (the tenant-origin gap this build closes); every one of the 21 server codes plus the client-made ones lands on a named screen or the honest `unknownCode` fallback, pinned by 12 unit tests |
| **Scalability** | neutral | No new automatic polling; per-phone server-side limits are unchanged |
| **Maintainability** | neutral to positive | One new pure, tested table (`checkin-screens.js`) rather than a bigger edit to a file under active review; some duplication of shape (not text) with `join-screens.js`, a declared trade-off |
| **Data integrity** | improves | The secret and the tenant origin are now written and cleared together, always, by construction (`device-secret.js`'s own `clear()`) |
| **Compliance / privacy** | improves, one declared gap | ALV-43 closes the phone-model disclosure gap for new joins; the web page's own gap is named, not hidden; nothing widens what is shown beyond what `01c`'s inventory already allows |

---

## 7 · What else moved while I worked

`git fetch origin dev` before starting and again before this document: `origin/dev`
unchanged at `1c4e84c` throughout. The parallel review worktree
(`review-013-alv39`) had no new commits either - the coordinator's own
`join-screens.js` fix (the `TOO_MANY_TRIES`/`FEATURE_OFF` wording bugs the review
found) had not landed by the time this was written. I did not touch
`join-screens.js` at all, and `checkin-screens.js` only reads its two exported
date-formatting helpers, which that fix does not change - confirmed with the
coordinator before starting.

---

## 8 · Three personas

| Persona | What changes | What must not change - and did not |
|---|---|---|
| **Field employee** | Gets a real Attendance screen, a real punch, real Settings, for the first time | The web check-in page is untouched; nothing here changes it |
| **HR Manager** | No change - the desk side shipped in server steps 4-5 | Sees no new field, no new visibility |
| **CXO** | Nothing visible | — |

---

## Worktree / commits

- `.claude/worktrees/013-mobile-app-alv37`, branch `slice/013-mobile-app-alv37`,
  on top of `origin/dev@1c4e84c`.
- `60892bd` - impact analysis (no code).
- `927b20e` - the daily-use client build (14 files).
- This document's own commit follows.

Not pushed. Not merged into local `dev`. No server, no bench, no device touched.
