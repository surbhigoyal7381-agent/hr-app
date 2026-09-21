---
slice: 013-mobile-app
artifact: 03-implementation-notes-server-step4
author: hrms-fullstack-engineer
date: 2026-09-19
scope: STEP 4 of the server work - daily use. US-12 (E4 app start), US-13 (E5 the punch), US-15 (E6 remove my phone), the section-6 limits for E4/E5/E6, the minimum radius, the fake-location field
branch: slice/013-mobile-app in .claude/worktrees/013-mobile-app, three commits on top of step 3's 37d9b21
status: BUILT AND STATICALLY CHECKED. NOT run against a database - another agent held the bench for a release-blocking fix for the whole build. NOT in local dev. NOT pushed. No server touched.
---

# 013 step 4 — what I built, and what is still owed

**Read this first.** The code and the tests are on the branch. **Nothing has run
against a database.** The bench was held by another session for a
release-blocking fix, on the user's instruction, so this step stops before the
first `bench` command. Section 6 says exactly what did run, and section 7 what
is owed. As in step 3, the database runs are the gate, not this document.

---

## 1 · What I built, file by file

| File | New or changed | Mechanism | Why that one |
|---|---|---|---|
| `alvoraa_portal/field_app_limits.py` | **new** | build (moved) | The `_limited` decorator, `_seconds_left`, the three key names and `_hash`, moved out of `field_app_join`. The punch and the start screen in `field_checkin.py` need the limiter, and `field_app_join` imports `field_checkin`, so it could not stay there without an import cycle. Behaviour change, deliberate: an empty or malformed argument is hashed as `""` (one shared bucket) instead of being refused `INVALID_REQUEST` by the limiter, so a missing secret still answers `NOT_SET_UP` (AC-3) and a bad code still answers `QR_NOT_RECOGNISED` |
| `alvoraa_portal/field_checkin.py` | changed | extend | **E4 `field_status`** complete for app phones; **E5 `field_checkin`** complete for app phones; the two shared helpers `_todays_punches` and `_workplace`; `_refuse_unless_notice_is_current`; `_flag`; `refuse_small_radius` (the Shift Location hook); the `alvoraa_mock_location` custom field in `after_migrate`; `MAX_ACCURACY_METRES` 100 → **50**; `MIN_RADIUS_M = 100` replaces the two unused advisory constants; `_hash` now imported from the limits module under its old name |
| `alvoraa_portal/field_app_device.py` | **new** | build | **E6 `remove_my_phone`**. E11 (HR blocks a phone, step 5) will live beside it |
| `alvoraa_portal/field_app_join.py` | changed | extend | Imports the limiter, `_hash`, `_todays_punches` and `_workplace` instead of holding its own copies; `_app_version` reads through `errors.sent_app_version`. No endpoint changed shape |
| `alvoraa_portal/field_app_errors.py` | changed, one function | extend | `sent_app_version()` - the one reader of the `X-Alvoraa-App-Version` header, used by the join and now by the punch. **No new code was needed**: every code step 4 sends was already declared in step 1 (section 2 lists them) |
| `alvoraa_portal/hooks.py` | changed, append only | configure | `doc_events["Shift Location"]["validate"]` → `refuse_small_radius`, appended at the end of `doc_events` |
| `tests/test_field_app_step4_013.py` | **new** | build | 33 tests, section 6 |
| `tests/test_portal_security_010.py` | changed, `CEILINGS` | extend | `field_app_join.py` 7 → **6** (the punches read moved out); new rows `field_app_device.py` **1**, `field_app_limits.py` **0** |

### E4 - the start screen, exactly

For every phone: `employee`, `employee_name`, `first_name`, `designation`,
`company`, `checked_in`, `todays_checkins`, `server_time`, `workplace {name,
radius_m}`, `min_version`, `notice_version`, `joined_on` - the section-6 list.
For a **web** phone only, the old `work_location {name, radius, latitude,
longitude}` block is still built, byte for byte, because `field-checkin.html`
reads it at lines 873 and 919 (traced by hand, as the impact analysis asked)
and step 4 may not change that page (AC-35). An **app** phone never receives
coordinates (PRIV-6). Keys were only added, never removed (OPS-8).

Order of refusals: secret (`NOT_SET_UP` / `DEVICE_PENDING` / final states /
`CONSENT_REQUIRED`) → employee not Active (`EMPLOYEE_NOT_ACTIVE`, AC-83, new at
E4) → the switch and the designation list (`APP_OFF_FOR_FIELD` /
`NOT_FIELD_ROLE`, app phones only) → the notice (`NOTICE_CHANGED` with
`version, rows, retention_days, what_changed`, app phones only, AC-80). It
writes nothing (AC-77).

### E5 - the punch, exactly

Same refusal order as E4 first (AC-91), then `log_type`, then the position:

- no latitude or longitude → `LOCATION_MISSING`; **an app phone without an
  accuracy → `LOCATION_MISSING` too** (the decision "accuracy stored on every
  reading"); a web phone may still punch without one (AC-35);
- accuracy worse than **50 m** → `GPS_NOT_EXACT {accuracy_m, limit_m: 50}`.
  This applies to web phones as well - the physics is the same and the sentence
  the page matches on is unchanged; only the number moved. **Declared as a
  web-page behaviour change** (section 8);
- a second punch of the same kind inside **60 s** → `ALREADY_RECORDED {time}`.
  The query filters on `employee` (indexed), then `log_type` and `time`;
  `time` is not indexed in Frappe HR and no index was added (Finding D, C-9);
- Frappe HR's own radius rule → `OUTSIDE_WORKPLACE {distance_m, site,
  radius_m}` - unchanged from before; still never the depot's coordinates.

One `Employee Checkin` row per accepted punch with `latitude`, `longitude`,
`alvoraa_gps_accuracy`, `alvoraa_field_device`, `alvoraa_mock_location`
(section 4.6, new custom field, `in_standard_filter` so HR can filter the list
on it - AC-85), `alvoraa_captured_at` / `alvoraa_checkin_offline` as before,
and the private photo. The fake-location flag is **recorded, never refused**
(Q-15). After the save the phone's `last_seen`, `checkin_count` and - only on
a saved punch, never on an open - `app_version` from the header are written
with `db_set(update_modified=False)`. The answer adds `todays_checkins` so the
app redraws home with no extra E4 (AC-199).

**Photo.** The app sends 960×720 at quality 0.7 (the decision), roughly 80 to
150 KB. The server ceiling is unchanged at **400 KB** and JPEG magic bytes,
checked on the string before decoding (`field_app_photos`). A photo that fails
loses the photo, not the punch (AC-87, existing rule).

### E6 - remove my phone, exactly

Guest POST, secret only. Allowed states: **Active** and **Consent not given**
(the 17 Sep decision: a parked phone is removed like any other). Locks in the
fixed order - Employee, then the phone - and **reads the phone again under the
lock**, so a block HR made a moment earlier wins and is answered with its own
code instead of a controller crash (section 11: "never both"). Then status
Removed, `status_change_source = The employee`, `status_changed_by` empty; the
controller retires the hash in the same save. Nothing erased: the row, its
punches and its acknowledgement rows stay (SEC-22, D10). A second call finds the
retired hash and is told `DEVICE_REMOVED {removed_at}`. Not gated on the
switch or the designation list - a person may always take the company off
their phone. Gated on the plan like every device endpoint (section 7.1).

### The limits, exactly

| Endpoint | Was | Now |
|---|---|---|
| E4 `field_status` | 120/h **per IP** | **60/h per phone**, keyed on the hash |
| E5 `field_checkin` | 60/h **per IP** | **30/h per phone**, keyed on the hash |
| E6 `remove_my_phone` | - | **5/h per phone** |
| `register_device` (web page) | 10/h per IP | unchanged - not in this step |

The per-IP limits would have refused a depot where 400 phones share one Wi-Fi
(AC-140), so this is a correctness change, not only a spec one. Same
`_limited` pattern as step 3: `ip_based=False`, the hash in a form field whose
name contains `key`, removed afterwards, `TOO_MANY_TRIES {retry_after_s}` from
the key's TTL.

### The minimum radius, exactly

The radius is configured in **one place**: `Shift Location.checkin_radius`, a
Frappe HR field on a standard doctype (checked: no Org Settings screen or
`hr_api` path writes it; the two advisory constants in `field_checkin.py` were
never read by anything). So the refusal is a `validate` hook on Shift Location
from our app - every door, form, import and REST - and not an edit to hrms:
`0 < radius < 100` is refused with a sentence that says why and what to use.
**0 keeps Frappe HR's meaning, "no radius"**, and is allowed (the existing
`test_checkin_location` fixture uses 0). Rows already saved with a smaller
radius keep working until HR next edits them; the punch never refuses on the
setting itself. The hook fires for every tenant, plan or not, because a fence a
phone cannot check is wrong for every tenant - reversible by the user if they
disagree (section 8).

---

## 2 · The acceptance criteria, one by one

| AC | How | Proven? |
|---|---|---|
| AC-76 | The E4 key set; `workplace` name + radius only; body ≤ 4 KB; no `latitude`/`longitude` anywhere in an app phone's answer | test written, **unrun** |
| AC-77 | E4 reads only; five calls leave `last_seen`, `checkin_count`, `modified`, `app_version` unchanged | written, unrun |
| AC-78 | Switch off → `APP_OFF_FOR_FIELD`; designation off the list → `NOT_FIELD_ROLE {designation}`; restored → 200 with no new code; Version count of the phone unchanged | written, unrun |
| AC-79 | Web phone unaffected by the switch | step 2's test still stands |
| AC-80 | Latest acknowledgement older than current → 409 `NOTICE_CHANGED` with the four values; E9 then E4 → 200 | written, unrun |
| AC-81 | `FEATURE_OFF` for both kinds of phone | step 1's test still stands (`requires_field_app_plan` unchanged) |
| AC-82 | 61st E4 in an hour → 429; Redis holds the hash, never the secret | written, unrun |
| AC-83 | Employee Left, phone not yet blocked → 403 `EMPLOYEE_NOT_ACTIVE` at E4 and E5 | written, unrun |
| AC-84 | One row with every field; private File; phone's `last_seen`, `checkin_count`, `app_version` moved; answer has `log_type`, `time`, `todays_checkins` | written, unrun |
| AC-85 | `mock_location` 1 / "true" → row 1; the field is `in_standard_filter` | written, unrun (the filter is the field's own property) |
| AC-86 | `LOCATION_MISSING`; `GPS_NOT_EXACT {60, 50}`; `OUTSIDE_WORKPLACE` end to end with a real Shift Type, Shift Location (100 m) and submitted Shift Assignment, ~380 m away; `ALREADY_RECORDED {time}`; no row in each case | written, unrun; **the geofence fixture is the one most likely to need a correction on the first run** (section 7) |
| AC-86 "no distance available" | `_geofence_message` still answers `OUTSIDE_WORKPLACE` with empty values when the site cannot be read | unchanged from step 1 |
| AC-87 | Photo over 400 KB / not JPEG → punch without photo, nothing in the logs | slice 014's tests still stand |
| AC-88 | 31st E5 in an hour → 429 `TOO_MANY_TRIES` | written, unrun |
| AC-89, AC-90 | Photo view logging and the checkin hooks | unchanged; not re-tested here |
| AC-91 | E5 gives the same code as E4 in every state (switch, list, notice, leaver, consent) | written, unrun |
| AC-96 | Web phone never asked about the notice | written, unrun |
| AC-99 | E6: Removed, `The employee`, `status_changed_on`, hash moved; readings and punches untouched; E4/E5/E6 afterwards → `DEVICE_REMOVED {removed_at}` | written, unrun |
| AC-100 | Blocked → `DEVICE_BLOCKED` with no values and no reason word; Replaced → `DEVICE_REPLACED {replaced_at}`; nothing changes | written, unrun |
| AC-101 | 6th E6 in an hour → 429 | written, unrun |
| AC-140 (the part a unit test can show) | Two phones are two buckets; the per-IP limit is gone from E4/E5 | written, unrun |
| Min radius (decision) | 1, 50, 99 refused; 100, 0, 2000 allowed; editing an old row down to 30 refused | written, unrun |
| Fail-without-fix (duplicate guard) | Remove the `time` filter from `_refuse_duplicate` → `test_013_ac86_a_second_punch_inside_the_window_is_refused` fails on "second answer is ok" | **owed on the bench** |

### Not in step 4, deliberately

- **E10, E11, E12, the Employee form section, the QR dialog** - step 5.
- **N5, the daily clean-up, the counters** - step 6.
- **A new notice version** (AC-92, the six rows of `01b` §7.7 and a version
  that is not `2026-09-13`) - US-14, not assigned to step 4. `CONSENT_VERSION`
  is unchanged; the pin from step 1 still holds.
- **Erasure on withdrawal** - not built, as agreed.
- **`deploy/nginx.conf`, `subscription.requires_feature`, any hrms index,
  `www/hrms-employee.html`, the old consent fields, `patches.txt`** - not
  touched. No patch: the one new custom field comes from `after_migrate`.
- **Refusing on the fake-location flag** - flag only (Q-15).
- **`register_device`'s per-IP limit** - the web page's own; not in scope.

---

## 3 · The seven dimensions, against the code I wrote

| Dimension | Before → after | Why |
|---|---|---|
| **Performance** | **neutral** | E4: secret (1-2 indexed reads) + `get_doc` + Employee + settings (3 reads, app phones) + latest acknowledgement (1 indexed read by `device`, app phones) + today's punches (`employee` index) + shift location (2). E5: the same plus the duplicate read, the insert, the File write, one `db_set`, and today's punches for the answer. No loop does a query. E6: 2 secret reads twice + 2 locks + 1 save. Designed for 400 field workers × 2 punches × 26 days |
| **Security** | **improves** | Per-phone limits replace per-IP ones on E4/E5 (a shared IP is no longer one caller; one phone cannot hide behind changing IPs); E6 can only ever act on the phone whose secret was presented; the fake-location flag is recorded; a leaver is refused at E4 as well as E5; `ignore_permissions` counted at exact ceilings (6/1/0) |
| **Reliability** | **improves** | E6 re-reads under the lock so HR's block and the person's remove cannot both "win"; E6 is safe to call twice; the duplicate window is unchanged and now has a fail-without-fix test; a refused radius at save time means no punch is ever refused by a fence a phone could not check |
| **Scalability** | **improves** | AC-140's depot case no longer trips a per-IP limit. Locks are per person, milliseconds |
| **Maintainability** | **improves** | One limiter module for nine endpoints; one `_todays_punches`, one `_workplace`, one header reader, one notice check. Against that: `field_app_device` imports two lock helpers from `field_app_join` |
| **Data integrity** | **improves** | Every app reading carries its accuracy or is refused; `app_version` moves only on a saved punch; the phone record is never written by an open; E6 goes through the controller so the hash retires in the same save |
| **Compliance / privacy** | **improves** | No coordinates to an app phone (PRIV-6); no write on open, so no "last opened" exists (PRIV-9); the block reason never reaches E6 (PRIV-13); E6 erases nothing and is not a withdrawal (17 Sep); the notice gate holds at E4 and E5 (D19). **No visibility widened**: `alvoraa_mock_location` is a Check on Employee Checkin under the existing checkin permission hooks; it is a filter, not a new reader |

---

## 4 · Things I found that the spec has wrong or unsettled

1. **Section 6 says E5 is "30/hour per phone" while the code had 60/hour per
   IP.** Per IP would have refused the AC-140 depot. Fixed as per phone; the
   spec's number stands.
2. **AC-86 says "accuracy 140 m (limit 100)".** The decision made after the
   spec is 50 m. The test uses 60 m against a limit of 50. **The spec row should
   say 50.**
3. **The spec never says whether the 50 m limit applies to the web page.**
   Built as one limit for every phone (section 8 declares the change). If the
   user wants the page kept at 100 m, it is a one-line condition on
   `join_method`.
4. **Section 12's "index on `Employee Checkin.employee`, `time` exists
   [UNVERIFIED]"** - `time` is not indexed (Finding D). The duplicate check and
   today's punches use the `employee` index. No index added. The row should be
   corrected.
5. **US-13 does not say what to do with an app punch that has no accuracy.**
   Built as `LOCATION_MISSING` for app phones, because the decision is that
   every stored app reading carries one. Somebody should add it to AC-86.
6. **The radius is configured on `Shift Location` only.** The spec's "check
   where the radius is configured" is answered: nowhere else. The advisory
   constants in `field_checkin.py` (`FRAPPE_MIN_RADIUS_M`, `ADVISED_MIN_RADIUS_M`)
   were read by nothing and are gone.
7. **Step 3's `_limited` refused an empty argument with `INVALID_REQUEST`.**
   That contradicted AC-3 ("a missing secret → 401 `NOT_SET_UP`") for the
   endpoints step 4 wraps. Changed to one shared bucket for empty values; the
   endpoint answers. No step-3 test pinned the old behaviour.

---

## 5 · Three personas

| Persona | What changes | What must not change - and did not |
|---|---|---|
| **CXO / System Manager** | Can filter Employee Checkin on "Phone reported a fake location"; cannot save a Shift Location with a radius under 100 m | Cannot unblock or remove a phone from the desk (E6 is the phone's own) |
| **HR Manager / HR User** | Same filter; same radius rule on the Shift Location form, import and REST; sees "Removed by <the employee>" on the record (the desk section is step 5) | Sees no "last opened" - E4 writes nothing |
| **Employee (field worker)** | Opens the app and sees today; punches with photo, place and accuracy; is refused with a plain code for a vague fix, no fix, too far, twice, too often, a changed notice, a switched-off app, or a phone that has not agreed; can remove the phone | Never sees the depot's coordinates; never learns a block reason; nothing is erased when the phone is removed |
| **Employee (web check-in page)** | A fix worse than 50 m is now refused (was 100) - same sentence | Every key the page reads is still sent; the answer only grew |
| **Employee (office colleague), line manager** | Nothing | - |

---

## 6 · What I ran, and what I did not

**No bench, no container command, no site, no database.** Another agent held
the bench for a release-blocking fix. Static checks only:

| Check | Result |
|---|---|
| `ast.parse` on every changed and new `.py` (8 files) | all parse |
| `ruff check --config hrms/pyproject.toml` on the 8 files | **every file I wrote or changed is clean.** 7 findings, all in `tests/test_portal_security_010.py`, all present at `HEAD` before my 9-line edit (checked by running ruff on `git show HEAD:...`) |
| `scripts/check_app_integrity.py` | **614 checks, OK** (613 at step 3; the new hook path adds one) |
| `node --check` | nothing to check - no JavaScript changed |
| `ignore_permissions` counts | `field_app_join.py` 6, `field_app_device.py` 1, `field_app_limits.py` 0, `field_checkin.py` 4 (not in `CEILINGS`; was 3, +1 for the moved punches read) |
| Frappe v16.33.1 source, read from the running container (read only, no bench command) | `rate_limit` builds `identity = user_key` when `ip_based=False` and a key is given, so a hash of `""` is a valid identity; `get_request_header` reads `request.headers.get`; `Document.db_set(dict, update_modified=False)`; `frappe.guest_methods` exists (the contract test uses it) |
| Frappe HR source in the checkout | `Employee Checkin.validate` order (`fetch_shift` before `validate_distance_from_shift_location`); the geofence filters Shift Assignment by `shift_type = self.shift`; `checkin_radius <= 0` means no fence; `Shift Location` has no validate of its own beyond geolocation; no fixture anywhere in the repo saves a radius under 100 (demo uses 150; `test_checkin_location` uses 0) |

**The 33 tests, by class:** TheStartScreen 8, ThePunch 7, TheGeofence 3,
TheMinimumRadius 3, RemoveMyPhone 5, TheLimitsArePerPhone 4, TheContract 3.

---

## 7 · Owed to the bench, in order

1. `bench --site test_site migrate` from a throwaway container mounting this
   worktree - **needed**: one new custom field on Employee Checkin
   (`alvoraa_mock_location`). Without it the punch still saves (Frappe drops an
   unknown field on insert) but AC-84/85 fail on the stored flag.
2. `run-tests --module alvoraa_portal.tests.test_field_app_step4_013` (33
   tests). Expect the first run to correct the test module in these places, if
   anywhere: (a) the geofence fixture - a Shift Type spanning 00:00-23:59 must
   be found by `fetch_shift` at the moment the test runs; (b) the private File
   insert as Guest - if Frappe's File refuses it, that is a **product** finding
   (production punches as Guest too) and not a test to soften; (c) the
   `frappe.guest_methods` membership check.
3. **The fail-without-fix proof:** delete the line
   `"time": [">", add_to_date(now(), seconds=-DUPLICATE_WINDOW_SECONDS)],` from
   `_refuse_duplicate`, run `test_013_ac86_a_second_punch_inside_the_window_is_refused`,
   watch it fail, restore with `git checkout --`, re-run green.
4. The step-1, step-2, step-3 and 014 modules (the limiter moved and E4/E5's
   answers grew; step 3's rate-limit tests must still see their keys under
   `rl:alvoraa_portal.field_app_join`).
5. Full `alvoraa_portal` and `alvoraa_goals` once. Baseline 1,354 / 18; expect
   **1,387 / 18** (33 new).
6. Custom DocPerm count before and after (228 rows / 45 doctypes at step 3).

---

## 8 · Known gaps and shortcuts, declared

1. **Nothing has run against a database.** The whole of section 7 is open.
2. **The 50 m accuracy limit now applies to the web check-in page too.** The
   page's screens and sentences are unchanged, but a 70 m fix that punched
   yesterday is refused today. The decision named 50 m without saying app-only;
   I read it as the physics and applied it once. One condition reverses it.
3. **The minimum-radius hook fires for every tenant**, plan or not, on Shift
   Location. Reasoned in section 1. A tenant with an existing 30 m fence keeps
   it until they next save that record, and then must choose 100 or 0.
4. **The end-to-end geofence test depends on the clock**: it needs the shift to
   be found at test time, so the Shift Type spans the whole day. At 23:59:xx it
   could miss. Accepted for now.
5. **`app_version` is written only when the header differs from what the row
   holds** - one fewer write per punch, at the cost that a phone whose build
   never changes writes it once.
6. **E6 does not check the employee's status.** A leaver whose phone the hook
   has not blocked yet can still remove it. That is harmless (the row goes to
   Removed either way) and I preferred the simpler rule.
7. **No test for AC-87 (oversized photo) or AC-89/90 in this module** - slice
   014 and the existing hooks cover them and are unchanged.

---

## 9 · Step 4 proven (2026-09-19, later the same day)

The bench was released by session 030 and was idle (`docker ps` showed no
`hrlocal-0xx` container; `pgrep` in `hrlocal-bench` found no run). Claimed on the
work board, then everything below ran from a throwaway container `hrlocal-013`
mounting **this worktree's** three apps against the shared `hrlocal-sites`
volume, on the `hrlocal` network, as user `frappe`, one run at a time. No
`docker cp`, no dev tenant, no server, nothing pushed, nothing in local `dev`.

### 9.1 · What ran, and the real numbers

| Step | Command / check | Result |
|---|---|---|
| Baseline | Custom DocPerm on test_site | **228 rows / 45 doctypes** |
| Migrate | `bench --site test_site migrate` | **125 s, 0 failed.** `alvoraa_mock_location` present as a Custom Field (`in_standard_filter` 1) and as a column |
| First run, step-4 module | `run-tests --module ...test_field_app_step4_013` | 30 ran, **1 error**: the geofence class's Shift Type (00:00-23:59) was refused by Frappe HR - "reduce Allow check-out after shift end time to avoid shift time overlapping with itself" (the default 60-minute margins). Fixture fix: both margins 0. **No product change** |
| Second run | same | **33 OK** (21.5 s) |
| Fail-without-fix, first attempt | the `time` filter removed from `_refuse_duplicate` | **Still passed** - and rightly: without the filter the guard refuses on ANY earlier punch of the same kind, which is stricter. My recipe was wrong |
| **Fail-without-fix, the real one** | the `_refuse_duplicate(device, log_type)` call deleted; `test_013_ac86_a_second_punch_inside_the_window_is_refused` | **FAILED**: both punches saved (`EMP-CKIN-09-2026-000054` and `...000055`, two seconds apart; "`{'status': 'ok', ...} is not None`"). Restored with `git checkout --`, tree clean, re-run: **OK**. The broken state was never committed; the recipe in the test's docstring now says the right thing (commit `5a72525`) |
| Step 1 module | `...test_field_app_step1_013` | **15 + 13 = 28 OK** |
| Step 2 module, first time | `...test_field_app_step2_013` | **2 failures**: `NOTICE_CHANGED` instead of the switch's refusal. The step-2 fixture builds an Active app phone straight into the table with no reading, and since step 4 an app phone whose latest reading is not the current version is refused at E4/E5 (AC-80). In production every Active app phone has a reading (E3 writes it), so the fixture is the artefact. Fix: the fixture writes a reading; the shared base fixture deletes readings before phones (commit `ed6ee94`). **No product change** |
| Step 2 module, second time | same | **27 + 7 = 34 OK** |
| Step 3 module | `...test_field_app_step3_013` | **41 + 9 = 50 OK** (the moved limiter and its keys under `rl:alvoraa_portal.field_app_join` still hold) |
| Slice 014 module | `...test_checkin_security_014` | **14 + 2 = 16 OK** (the wrapper-order pin and the field tuples unchanged) |
| Step 4 module, after the fixture fixes | | **33 OK** |
| **Full `alvoraa_portal`** | `run-tests --app alvoraa_portal` | **613 + 774 = 1,387 tests, OK**, 0 failures, 0 errors, 4 skipped; 11.6 min + 32 min. Baseline was 1,354; the 33 new tests account for the difference exactly. No deadlock; nothing else was running |
| **Full `alvoraa_goals`** | `run-tests --app alvoraa_goals` | **18 OK**, 2 skipped |
| Custom DocPerm afterwards | | **228 rows / 45 doctypes** - unchanged |
| `test_review_copies_010d` alone | `run-tests --module ...test_review_copies_010d` | **34 OK** (111 s) |

### 9.2 · For the other sessions: `test_sec28_bad_values_are_refused_and_only_hr_manager_may_change_them`

**Passes on this branch - in the full run (tick shown in the runner's output)
and again when its module ran alone (34 OK).** It errors on any branch WITHOUT
slice 013 because `test_site` carries the HR Settings child-table field
`alvoraa_field_worker_designations` (child doctype `Alvoraa Field Worker
Designation`) from step 2's migrate, and code without 013 has no controller for
that child doctype. That is the site's schema being ahead of the branch under
test, **not a product fault** - it disappears when 013 is on the branch, and it
would disappear on any branch if `test_site` were rebuilt from that branch.

### 9.3 · What the runs found in the product

**Nothing.** Every correction was to a test fixture or a test's own recipe
(`5a72525`, `ed6ee94`). E4, E5, E6, the limits, the radius hook and the new field
are as built in `7fed73f`.

### 9.4 · State left behind

- `slice/013-mobile-app` at `ed6ee94`: five step-4 commits on step 3's `37d9b21`
  (`8aec710`, `7fed73f`, `0fe713b`, `5a72525`, `ed6ee94`). Not in local `dev`,
  not pushed.
- `test_site` carries the step-4 schema too (`alvoraa_mock_location` on
  Employee Checkin). Nothing on `dev` reads it, so nothing there breaks.
- Container `hrlocal-013` removed; bench claim cleared on the work board.
