---
slice: 013-mobile-app
artifact: 00-impact-analysis-app-client
author: hrms-fullstack-engineer
date: 2026-09-21
status: draft — impact analysis and strategy only (CLAUDE.md §2, steps 1-2). No code written. Waiting for approval before any build.
inputs: [01-product-brief.md, 01b-ux-design.md (incl. Design check decision 2026-09-17), 02-functional-spec.md, 03-implementation-notes.md (part 1, 2026-09-17), 09-install-the-test-app.md, mobile/field-app/** on origin/dev, alvoraa_portal/alvoraa_portal/field_checkin.py, field_app_join.py, field_app_device.py, field_app_errors.py, field_app_notice.py on origin/dev]
---

# 013 — mobile app, client build — impact analysis and strategy (ALV-37)

**Important caveat on how this was produced.** My assigned worktree
(`.claude/worktrees/agent-a4e078558e4079082`) turned out to be checked out at an old,
unrelated commit (`65878e8`, a `main`-lineage release commit, 196 files and 36,157 lines
different from `origin/dev`), not at `origin/dev`. It does not even contain
`docs/slices/013-mobile-app/`. I did not reset or touch that worktree's branch — I read
every source file directly from `origin/dev` with `git show origin/dev:<path>` (fetched
fresh at the start of this session) and I am writing this one new file into the worktree
by hand. **Whoever picks this up to write code must start from a worktree actually on
`origin/dev`** — either rebase the existing `slice/013-mobile-app` branch (see §6) onto
today's `origin/dev`, or cut a fresh worktree from it. I have not touched git state, run
any bench command, or written any code — this document is the only output.

---

## 0. What is actually true today, checked against the source (drift check)

The brief, `01b` and the `02` spec were written on 2026-09-17, before the five server
build steps existed. Reading `origin/dev` now (commits through `3ab09f1`, pushed today)
against those documents finds real drift in three places. None of it blocks starting the
client build, but all three change what the client team needs to plan for.

### 0.1 The server contract is real and matches the spec almost exactly

Every endpoint the spec calls E1–E11 (working names) exists on `origin/dev` under its
real name, with the same guest/session rules, rate limits and lock order the spec
describes:

| Spec name | Real function | File |
|---|---|---|
| E1 check the code | `check_code(code, token=None)` | `field_app_join.py` |
| E2 this is not me | `refuse_code(code)` | `field_app_join.py` |
| E3 agree and finish | `join_with_code(code, notice_version, device_label, platform, token, agreed=1)` | `field_app_join.py` |
| E4 app start | `field_status(token)` | `field_checkin.py` |
| E5 punch | `field_checkin(token, log_type, latitude, longitude, accuracy, photo, captured_at, mock_location=0)` | `field_checkin.py` |
| E6 remove this phone | `remove_my_phone(token)` | `field_app_device.py` |
| E9 notice changed, agree again | `acknowledge_notice(token, notice_version)` | `field_app_join.py` |
| E7/E10/E11 (desk only, not app-facing) | `make_code`, `cancel_code`, `block_phone` | `field_app_join.py`, `field_app_device.py` |
| Web-only, app must never call | `register_device(employee_id, ...)` | `field_checkin.py` |

Every one of these is a guest `POST`, wrapped in `_private_request`, answers
`Cache-Control: no-store`, ignores session cookies, and refuses on a frozen `code` from
`field_app_errors.CODES` — exactly the contract §7 of the spec describes. This is good
news for the client: the hard, security-sensitive server work is done, tested, and the
app can be built against it now, on the local bench, without waiting on anyone.

### 0.2 A drift the client must handle: a consent state and code the approved design never drew

The server has a **third phone state, `"Consent not given"`,** and an error code,
**`CONSENT_REQUIRED`** (403, carries `version`), that appear nowhere in `01b`'s screen
list or the `02` spec's error-code table (§7.1/§7.2) or its US-35–48 acceptance criteria.
Reading the code:

- `join_with_code` (E3) takes an `agreed` argument. `agreed=0` still creates and activates
  the phone record, but in state `"Consent not given"` instead of `"Active"` — it holds a
  secret, cannot punch, and is asked again next time (via E9, `acknowledge_notice`).
- A new endpoint, `withdraw_agreement(token)`, lets an already-active phone go back to
  `"Consent not given"` on purpose — described in the code as a separate 2026-09-17 user
  decision from "remove this phone" (E6).
- `field_status` (E4) and `field_checkin` (E5) both refuse a `"Consent not given"` phone
  with `CONSENT_REQUIRED` via the shared `_device_from_token()` state check.

**None of this is in `01b`'s flow diagram, screen list or §14 acceptance-criteria seed
list, and none of it is in the `02` spec's §7.1/§7.2 code tables or US-36/41/42/43
stories.** It was evidently decided during the server build (steps 3–5), after the UX
design and functional spec were locked, and the design/spec documents were never
updated to match.

**My reading of what this means for the client, and my recommendation:** `01b`'s
approved notice screen has no "decide later" affordance — the tick box is required
before "Agree and finish" does anything, and the button does the whole join. I recommend
the client **never sends `agreed=0`** in this increment: build the join flow exactly as
`01b`/`02` describe it (tick required, one button, one outcome), so nothing in the
approved, clicked-through prototype changes. But the client **must still handle
`CONSENT_REQUIRED` defensively** wherever E4/E5/E9 can return it — a support action, a
future path, or simply because the server can send it and OPS-8's rule is that a client
must not crash on a code it does not expect to receive. The cheapest correct answer:
treat it like `noticeAgain` (re-show the six-row notice, tick again, call E9), reusing
the same screen and code path `US-42`/`NOTICE_CHANGED` already needs — **not** a new
eighteenth screen. I flag this as something to confirm with Security/the business
analyst rather than deciding it alone, since it is a real gap between what was approved
and what ships.

**One wording constraint this interacts with:** `01c` PRIV-4 is explicit that no
app-facing or desk-facing text may use the word "consent" until the compliance owner
answers Q-C1 — only the code names (`CONSENT_REQUIRED`, `consent_version`, the doctype
field `consent_given_on`) may say it. The screen the client shows for this code must be
worded like the rest of §7.12 ("Please read the notice again before you check in."),
never "You have not given consent." I will add this as a one-line test the same way
`01c` already asks for one on the desk side.

### 0.3 A drift that is not the client's to fix: the notice text is still the old version

`field_app_notice.py`'s `CURRENT_VERSION` is still `"2026-09-13"`, and its `"What we
record"` row does **not** mention the phone's model name. `01b`'s D19 explicitly said:
*"Change it now, before any pilot user agrees to the old words"* and *"please do not
build against `CONSENT_VERSION = "2026-09-13"`."* That instruction was not carried out —
the server still serves the old version and the old words.

The client cannot fix this itself: `01b`'s design (and the server's own
`notice.facts()` mechanism) is correct that the app must **render the server's notice
rows, never hardcode them** — so the app doing its job properly means it will show the
under-disclosing notice exactly as the server sends it. This is a small, two-line,
already-built-mechanism fix on the server side (`field_app_notice.py`: add a
`"2026-09-2x"` entry with the phone-model-name line, bump `CURRENT_VERSION`), not a
client change, but the client's build order should not need to wait for it. **I recommend
raising this with the user as a companion server fix to land before the pilot (US-48,
AC-229), not before the client build starts** — the join screens can be built and tested
today against whatever notice text the bench currently serves, and will pick up the
corrected words automatically once that one server file changes, with no app-side code
change, because the row list is server-driven by design.

### 0.4 What already exists in `mobile/field-app/` — confirmed against the real files

Reading every file named in the task, not just the implementation notes' summary:

| File | State today | Reusable as-is for the real build? |
|---|---|---|
| `web/js/host-check.js` | `checkEnrolLink(text, buildType)` — the exact host/scheme/path/fragment/code check AC-172 asks for, pure, no network, already unit-tested against 26 hostile links (`test/host-check.test.js`) | **Yes, unchanged.** This is US-33's client-side half, done. |
| `web/js/photo.js` | `shrinkToJpeg` / `fitSize` / `isTooBig` — exactly AC-201's numbers (640×480, JPEG 0.6 then 0.45, ≤150 KB), pure functions, unit-tested | **Yes, unchanged.** Needs wiring into the real capture flow (US-39), not rewriting. |
| `scripts/check_app.mjs` | Encodes the permission allow-list (SEC-20), the denied-dependency regex (analytics/crash/ads/Firebase), the "no outside URL" and "no `innerHTML` from strings" checks (SEC-17). Its own header says the checks that need a **built** package (merged manifest, debuggable flag, package size) are **SKIPPED until `android/` exists** | **Yes, keep extending it** — every new screen or plugin must still pass it. |
| `capacitor.config.json` | No `server` block, mixed content off, WebView debugging off, `CapacitorHttp`/`CapacitorCookies` disabled globally | Good starting shape for SEC-16; nothing to redo. |
| `package.json` | Only `@capacitor/core`, `@capacitor/android`, `@capacitor/cli` 8.5.2 pinned. **No camera plugin, no geolocation plugin, no QR/barcode plugin, no secure-storage plugin, no lock-file version-bump CI check yet.** | Needs three or four new dependencies added deliberately, each one vetted against `check_app.mjs`'s own gates before it is trusted (see §5). |
| `web/index.html`, `web/js/app.js` | **A throwaway camera+GPS test page, not the app.** Its own doc (`09-install-the-test-app.md`) says outright: "This is a test build. It is not the attendance app yet... No QR scanning, no joining, no Check In, no Check Out... Nothing reaches your Alvoraa site." It makes **zero server calls.** | **No.** This gets replaced by the real screens (US-35 onward), not extended. Its only carry-over value is that it already proved the camera and GPS work inside a Capacitor WebView on a real phone (09-install), which is useful evidence, not code. |
| `android/` project | **Does not exist.** `03-implementation-notes.md` (2026-09-18) says Android Studio was not installed, so nothing that needs a real Android build (Gradle flavors, manifest, apkanalyzer-based CI checks, an actual signed APK) has been done yet. | **Needs to be generated** (`npx cap add android`) before any of US-32/33/34's build-level ACs (AC-165, AC-171, AC-173, AC-177, AC-179) can be proven, not just asserted in JS. |

**So the honest starting point for ALV-37 is: US-31 is essentially done (key guard,
already merged in `03-implementation-notes.md`'s first commit); parts of US-33 and
US-34's *static, source-level* checks exist; and US-32, and all of US-35 through US-48,
are unbuilt.** The 58 app points are not evenly ahead — the earliest, cheapest,
least-product-visible slice (the CI/guard rails) is the one that is furthest along.

---

## 1. Cross-module reach

| App | Touched by the client build? | How |
|---|---|---|
| `mobile/field-app/**` | **Yes — this is almost the entire slice** | New Capacitor Android project, real screens replacing the test page, three new/changed npm dependencies, Gradle build-type flavors, expanded CI (`mobile.yml`, and `ci.yml`'s `key-guard` job already there) |
| `alvoraa_portal` | **Read only, one flagged exception (§0.3)** | The client is a new *caller* of an already-built, already-tested contract. No server code needs to change for US-35–46 to be built. The one exception is the notice-content fix in §0.3, which I recommend as a small, separate, server-side follow-up, not part of this build |
| `hrms`, `erpnext`, `alvoraa_goals`, `alvox_compensation` | **No** | Nothing in the client touches these; all HRMS-domain effects (punches landing in `Employee Checkin`, the geofence, the leaver lock) are already live and unaffected by which client calls the same endpoints |
| `www/hrms-employee.html` | **Never** | Unrelated; this slice's Line B rule was about server-side desk/portal work, not the app |
| `.github/workflows/*` | **Yes** | `mobile.yml` (already exists, JS-only checks) needs a real Android build step once `android/` exists; `ci.yml`'s existing `key-guard` job is unaffected. **Hot file** per `parallel-work.md` — check for other sessions' in-flight edits to these two files before touching them |

**Grep of callers.** Every endpoint the app will call (E1–E6, E9) is also either
(a) called only by the app (E1, E2, E3, E9 are new in this slice — the app is their only
caller today) or (b) shared with the existing web page (`E4`/`field_status`,
`E5`/`field_checkin`, and `register_device`, which the app must **never** call — D18, no
employee-ID path in the app). The shared endpoints already distinguish the two callers
by the presence of `X-Alvoraa-App-Version` (no header = web page, always allowed;
header present = app, version-checked) and by `join_method` (`"App QR code"` vs `"Web
check-in page"`), which is exactly how `_refuse_unless_app_phone_is_eligible` and the
notice/eligibility checks already branch. **The client build cannot break the web page's
existing behaviour** as long as it always sends the version header and never touches
`register_device` — both are true by construction if the app is built only against the
E-series endpoints in §0.1.

**HRMS domain impact:** Attendance only, and only additively — punches the app makes
land in `Employee Checkin` exactly as machine and web-page punches do today (already
proven server-side in the five build steps). No leave, payroll, appraisal or org-structure
domain is touched.

**Persona impact**

| Persona | What the client build changes for them |
|---|---|
| **Field employee** | Everything in this slice is for them: the whole join → confirm → notice → check-in → settings journey in §7 of `01b`. Nothing changes until the real build replaces the test page — the web check-in page keeps working unchanged throughout. |
| **HR Manager** | **No change from the client build itself.** The desk screens (invite, block, device list, settings) were server-side work already done in the five build steps. The client build only makes the app real for the person HR already invites. |
| **CXO** | Nothing visible, same as the brief said. |

---

## 2. Non-functional dimensions — what a new client must get right

Since this is new client code calling an already-hardened server, most of these are
framed as "what the build must get right," not "before vs after."

**Performance** — *neutral, contingent on discipline.* The server side already meets its
own budget (p95 ≤ 500 ms, checked in the five steps). The client's job is not to
undo that: send the version header and a 30 s timeout on every call (AC-203), retry a
punch only on an explicit "Try again" tap (never automatically), and cap `field_status`
polling to at most once a minute on resume (AC-202). Package size is capped at 10 MB
(AC-179) — this is a real constraint once a QR-scanning library and a secure-storage
plugin are added, and needs to be watched from the first dependency added, not
discovered at the end.

**Security** — *this is the dimension the slice is mostly about, and it is where the
open decisions sit.* The host allow-list (§0.4) and the permission/dependency CI gates
(§0.4) already exist and must keep passing as the real screens are built. The two
decisions still open are exactly the two places a badly chosen third-party dependency
could quietly reopen what `check_app.mjs` and `01c` close: **how the app reads a QR
code**, and **where it stores the device secret**. Neither has working code yet (see
§5). Every server-sent value must render as text, never HTML (SEC-17) — the existing
`app.js` already uses `textContent` exclusively, and that convention must carry over
unchanged into the real screens; `scripts/check_app.mjs`'s `HTML_SINK` check already
enforces this in CI.

**Reliability** — *this is the largest single piece of new client logic.*
`field_app_errors.CODES` names 21 server codes, plus 6 more the app makes itself with no
server call at all (§7.2 of the spec). Each must land on exactly one of the ~30 named
screens in `01b` §7, driven by `code` alone, never by matching English text (that
matters doubly here because `01c` SEC-19/OPS-8 promise old app builds keep working for
90 days even after wording changes). I recommend one small, data-driven
"code → screen" table as the single place this mapping lives (mirroring how
`field_app_errors.py` itself is one table on the server), with a hard default
(`unknownCode`) for anything not in the table — this is what makes the client honour
OPS-8's "endpoints only ever add" rule instead of silently breaking on the next added
code. Photo-kept-across-retry (AC-205) means the captured photo blob must live in a
small piece of state above the screen router, not be re-captured on every retry.

**Scalability** — *mostly already discharged server-side.* The "busy depot" case (400
phones on one Wi-Fi) is handled by per-device rate limits already built and tested
(E4: 60/hour, E5: 30/hour, keyed on the secret's hash, not the shared IP). The client's
only obligation is not to work against that — no automatic background polling, no retry
storms, which is the same discipline point as the performance row above.

**Maintainability** — *neutral to positive if the existing pattern is kept.* `photo.js`
and `host-check.js` are both small, pure, Node-testable modules with zero DOM
dependency, which is exactly why they were easy to verify against their ACs by reading
them in isolation. I recommend the same shape for the new modules this build needs: a
pure error-code-to-screen table, a pure QR-link/photo pipeline (already there), and a
thin screen-rendering layer that reads server answers and calls into these — not one
large `app.js` accreting every screen's logic inline, which would make the ~30-screen,
~21-code contract hard to audit against `01b` §7/§8 by eye.

**Data integrity** — *the device secret is the one piece of client-held state that
matters.* It must be written to secure storage **synchronously, after the server
confirms** (AC-188's order: E3 succeeds → write the secret → show `welcome`), never
before, so an app kill between "server accepted the join" and "phone saved the secret"
cannot leave a client that thinks it is set up when the server does not agree (or, worse,
a client that has already shown `welcome` while holding nothing to authenticate future
calls with). Every other piece of join-flow state (the scanned code, the picked photo,
the six-row notice) is memory-only and must never survive a screen change if the user
backs out (AC-190, AC-218) — this is a direct carry-over of PRIV-7's existing rule that
`photo.js` already respects (it hands back a `dataUrl` in memory, never writes a file).

**Compliance / privacy** — *several concrete, testable rules, one flagged gap.*
PRIV-1/AC-220: the only phone facts ever sent are model name (trimmed to 80 chars),
platform and app version — no call to anything that reads IMEI, Android ID, serial,
advertising ID, phone number, SIM or contacts; this needs an explicit code-review line
item once the real `Device.getInfo()` call is written, and a test that greps the bundle
for the banned API names the way `01c`'s own test plan describes. PRIV-4: no app-facing
string may use the word "consent" (§0.2 above) — I recommend a small lint check, mirroring
`check_app.mjs`'s existing pattern, that greps the string table for the word. PRIV-8/SEC-20:
only "while using the app" location is ever requested — this is a property of *which
Capacitor geolocation call is used*, not something to check after the fact, so it belongs
in the plugin choice in §5, not as a later audit. The one already-flagged compliance gap
that is **not** the client's to close is §0.3 (notice under-discloses the phone-model
collection) — the client renders whatever the server sends, correctly, and that is a
server-side follow-up.

---

## 3. Parallel-work check

- **What I could confirm:** `03-implementation-notes.md` (2026-09-17) records that a
  sibling worktree, `ci-fix-9138251`, was touching `ci.yml` with no commits at the time,
  and that slice 013's own CI change (`key-guard`, a new job) was placed so it does not
  overlap that or slice 014's `lint` job change. That is five days old information from
  a worktree that has since been folded into what is now `origin/dev`'s history — I
  cannot re-confirm it is still true today.
- **What I could not confirm, and why:** my own worktree is not on `origin/dev` (see the
  caveat at the top), so I cannot run `.claude/work-in-progress.md` or `git fetch` from a
  worktree that actually tracks the shared repo state right now. **Whoever starts the
  build must do this check themselves, fresh, before writing code** — it is step one of
  `parallel-work.md` and I have not been able to complete it on the real checkout.
- **Files this build will touch:** everything under `mobile/field-app/**` (new files
  mostly — no existing screen files to collide with, since `app.js`/`index.html` are
  being replaced, not edited by someone else), plus `.github/workflows/mobile.yml` and
  possibly `ci.yml` — both **hot files** per `parallel-work.md`, so check for other
  sessions' pending edits there specifically before touching them.
- **Branch to resume:** `03-implementation-notes.md` names `slice/013-mobile-app` in
  worktree `.claude/worktrees/013-mobile-app`, cut from `origin/dev@9138251`. That base
  is now four release-worth of commits behind today's `origin/dev@3ab09f1` (which
  includes all five server steps this app depends on). **This branch must be rebased
  onto current `origin/dev` before any new commit is added to it**, and the existing
  three commits (`d9b900c`, `c135020`, `06d813d`) should be re-read after the rebase to
  confirm nothing in `ci.yml`/`mobile.yml` conflicts with what slice 014 or other work
  has since added to those same files.

---

## 4. What the spec still leaves for the engineer to decide (confirmed against source, not guessed)

- **HTTP statuses for the error codes** were the business analyst's proposal, to be
  confirmed at strategy (spec §7, "frozen when the first pilot build ships"). Reading
  `field_app_errors.py`, they are **already frozen and shipped** — the table in §0.1 of
  this document is the real, live contract, not a proposal any more. The client should
  build against `field_app_errors.CODES` as printed in §0.2/0.3 above, not against the
  spec's §7.1 table, wherever the two differ (they differ only in the `CONSENT_REQUIRED`
  addition and the absence of a separately-listed `LOCATION_MISSING` in the spec's
  values — both already reconciled above).
- **The engineer names the endpoints** (spec §6, "working names"). They are already
  named, and named sensibly (`check_code`, `join_with_code`, `field_status`,
  `field_checkin`, `remove_my_phone`, `acknowledge_notice`) — nothing to redo here.

---

## 5. Proposed strategy

**Do not build all five stages / eighteen stories in one pass.** The spec's own
build-order table already sequences the app stories against the server stages
(stage 0: US-31 alone; stage 1: US-32/33/34; stage 2: US-35–38 against the local bench;
stage 3: US-39–46; stage 4: US-47/48), and I agree with that sequencing for a concrete
reason beyond "the spec says so": **stage 2 forces the two irreversible-ish technical
decisions (how the app reads a QR code, where it stores the device secret) that every
later stage's code depends on**, and it does so while the product risk of getting them
slightly wrong is still cheap — nobody has checked in yet, nothing is pilot-facing, and
the existing test infrastructure (Node unit tests against pure functions, no emulator
needed) already proves out exactly this kind of decision, the same way it already proved
out `host-check.js` and `photo.js`.

**Recommended build order for this ticket (ALV-37):**

1. **Confirm the starting point, not rebuild it.** Rebase `slice/013-mobile-app` onto
   today's `origin/dev`, re-run the existing `npm test` and `npm run check` from
   `03-implementation-notes.md`'s three commits, and confirm US-31's key-guard CI job is
   still green against current `ci.yml`. This is verification, not new work, and it is
   the only safe way to know the "done" claims in `03-implementation-notes.md` still
   hold five days and one server-side merge later.

2. **Finish stage 1 (US-32, US-33, US-34) as CI/config work**, once Android Studio/SDK
   availability is confirmed (see the open question below — `03-implementation-notes.md`
   said this was missing as of 2026-09-18, and everything past pure-JS checks needs it):
   generate `android/`, wire the three build-type flavors (`.debug`, `.pilot`, store ID)
   and the version-bump/lock-file CI checks (AC-165–171), extend `check_app.mjs`'s
   already-written static rules with the real, built-package checks its own header says
   are still SKIPPED (merged manifest via `apkanalyzer`, debuggable flag, package size).
   This is foundation work with no field-worker-visible outcome, which is exactly why it
   should be finished, not partially built, before stage 2's product screens start
   landing on top of it.

3. **Build stage 2 (US-35–38) as the first shippable, demoable increment: the join
   flow only**, first launch through `welcome`, plus the dead-code and "this is not me"
   screens. Test it against the local bench in a debug build, exactly as the spec's
   build-order table says. This is the brief's WOW moment (§7 of the brief), it only
   needs endpoints that are already fully built and tested server-side (§0.1), and it is
   where the two open plugin decisions below get made and proven, cheaply, before
   anything depends on them.

4. **Build stage 3 (US-39–46) second**: the daily attendance loop, problem screens, and
   settings — reusing `photo.js` unchanged and the error-code table stage 2 will already
   have built out for the join-side codes.

5. **Build stage 4 (US-47, US-48) last**: iPhone proof and the pilot, once Android is
   demonstrably reliable — this also lets the brief's own stop rule ("if the Android
   test build cannot check in reliably on a low-end phone, stop the app") be evaluated
   on real check-in behaviour (stage 3), not just the camera/GPS timing the test page
   already measured (`09-install-the-test-app.md`).

**Two technical decisions I recommend making explicitly, in stage 2, rather than by
default:**

- **How the app reads a QR code.** No scanning library exists in `package.json` today.
  I recommend a **pure in-page decoder reading `getUserMedia` video frames** (a small,
  dependency-light library such as a bundled `jsQR`) over a native barcode-scanning
  plugin, for three concrete reasons: it keeps the permission surface at `CAMERA` only
  (no plugin-added permissions to re-audit against SEC-20's allow-list); it keeps the
  "reads codes only, no network call" property provable in the same kind of pure Node
  unit test that already proves `host-check.js`; and the pilot phone table (AC-231)
  explicitly tracks "Google Play services yes/no" per phone, which tells me at least one
  pilot phone may lack it — a native scanner plugin built on Google's ML Kit would not
  run there, while a pure in-page decoder would.
- **Where the device secret lives.** AC-217 explicitly rules out `localStorage`,
  Capacitor `Preferences`, and WebView storage — it must be Keystore-backed secure
  storage. No such plugin exists in `package.json` yet. This needs one small, actively
  maintained, minimal-permission plugin (or a small custom one wrapping
  `EncryptedSharedPreferences`/Android Keystore), and whichever is chosen must be the
  **first** new dependency proven clean against `check_app.mjs`'s dependency-tree and
  permission checks — it is the highest-value thing to get right first, since every
  later stage reads and writes through it.

I am not deciding these two for the user by default; I am naming them here because the
spec and `01b` do not name a library for either, and getting them right is most of what
"Security" and "Reliability" mean for this slice.

---

## 6. Open questions for the user, before code starts

1. **Is Android Studio / the Android SDK now available** in the build environment? This
   was the blocking gap as of `03-implementation-notes.md` (2026-09-18) — it gates stage
   1 in full and every device-level AC in US-32–34.
2. **Should the notice-content gap (§0.3) be filed as a small server-side follow-up now**,
   so the corrected words are live before the pilot (AC-229), or is that deliberately
   deferred? I recommend fixing it before the pilot, not before the client build starts.
3. **Do you want the client to defensively handle `CONSENT_REQUIRED` / "Consent not
   given" (§0.2) as a reuse of the `noticeAgain` screen**, as I've recommended, or should
   this go back to the UX designer as a real screen decision, given it never went through
   the design-check gate?
4. **Confirm the branch/worktree to resume**: rebase the existing
   `slice/013-mobile-app` branch onto current `origin/dev`, or start fresh? (I recommend
   rebasing — three commits of real, already-reviewed work would otherwise be redone.)
5. Not blocking, but worth naming now: the two build-signing key holders (OPS-38/SEC-23)
   need to be named before any real key is generated, which stage 1 gets close to.

---

## Summary of decisions needed

- **Approve the build order**: stage 1 (finish CI/build-type foundation) → stage 2
  (join flow, first shippable increment) → stage 3 (daily attendance loop) → stage 4
  (iPhone + pilot). Not all 18 stories at once.
- **Confirm Android Studio/SDK availability** — this gates stage 1.
- **Pick a lane on the two open technical decisions** in §5 (QR-reading approach,
  secure-storage plugin) — my recommendations are stated, not assumed.
- **Decide what to do about the two drifts in §0.2/§0.3** (the undesigned consent state,
  and the stale/under-disclosing notice text) before stage 2 and the pilot respectively.
- **Confirm which branch/worktree the real build resumes from** (§3, §6.4).
