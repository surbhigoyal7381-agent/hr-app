---
slice: 013-mobile-app
artifact: 03-implementation-notes-server-step3
author: hrms-fullstack-engineer
date: 2026-09-19
scope: STEP 3 of the server work - the join. US-5, 8, 9, 10, 11, 14, 20, the leaver's codes (US-23 second half), the alerts those stories name (US-19 N1-N4), company scoping of the two new doctypes (C-11c), the withdrawal (C-3), the real waiting-codes count, the per-code and per-phone rate limits
branch: slice/013-mobile-app in .claude/worktrees/013-mobile-app, four commits on top of step 2's 5ef47cd
status: BUILT AND STATICALLY CHECKED. NOT run against a database - Docker was down for the whole build. NOT in local dev. NOT pushed. No server touched.
---

# 013 step 3 — what I built, and what is still owed

**Read this first.** Everything is on the branch (`6f282c7`, `26377d4`, `2d51717`,
`821d3df`). Docker Desktop was not running for the whole of this build, so **no
test ran against a database** - not the 50 new tests, not the fail-without-fix
proof for the lock order, not the full suites. Section 6 says exactly what did run.
The database runs happen when the bench is back and free; they are the gate, not
this document.

---

## 1 · What I built, file by file

| File | New or changed | Mechanism | Why that one |
|---|---|---|---|
| `.../doctype/alvoraa_app_invite/` (json + py) | **new** | build | The code record (§4.2). Random-hash name, `track_changes`, read+report only for the three HR roles - no create, write, delete, email, print, share, export or import for anyone. The controller refuses every hand-made insert, change and delete, including for Administrator and scripts |
| `.../doctype/alvoraa_notice_acknowledgement/` (json + py) | **new** | build | The reading record (§4.3). Insert-only: the controller refuses any save of an existing row and any delete without the server flag |
| `alvoraa_portal/field_app_join.py` | **new** | build | E1 `check_code`, E2 `refuse_code`, E3 `join_with_code`, E9 `acknowledge_notice`, the withdrawal `withdraw_agreement`, and E7 `make_code` (desk). The fixed lock order lives here |
| `alvoraa_portal/field_app_alerts.py` | **new** | build | N1-N4 as Frappe `Notification Log` rows, queued on the `short` queue after the commit; recipients are enabled HR Managers whom Frappe lets read the employee |
| `alvoraa_portal/www/enrol.html` + `enrol.py` | **new** | build | The page behind a scanned code (US-20). Standalone, nothing from another host, never reads the fragment, `noindex` by meta tag and by `X-Robots-Tag` |
| `alvoraa_portal/field_checkin.py` | changed, 3 places | extend | `_device_from_token` takes an `allowed` set (default unchanged: Active only); the leaver hook cancels waiting codes **before** blocking phones (the lock order); `register_device` writes an acknowledgement row (AC-95) |
| `alvoraa_portal/field_app_access.py` | changed | extend | The device scoping pair became one shared pair used by three doctypes; `invite_*` and `acknowledgement_*` hooks added |
| `alvoraa_portal/field_app_settings.py` | changed, 1 function | extend | `_waiting_codes()` is a real count: Waiting and not yet run out |
| `alvoraa_portal/hooks.py` | changed, append only | configure | Two lines at the end of `permission_query_conditions`, two at the end of `has_permission` |
| `alvoraa_portal/subscription.py` | changed, 2 lines | configure | Both doctypes appended to `TENANT_DOCTYPES` |
| `.../alvoraa_field_device/alvoraa_field_device.json` | changed | configure | The two fields step 1 deferred: `invite` (Link to the code) and `app_version`. `invite` was already in the controller's frozen list |
| `tests/test_field_app_step3_013.py` | **new** | build | 50 tests, section 6 |
| `tests/test_portal_security_010.py` | changed, 4 rows | extend | `CEILINGS` gains the four new files at their exact counts (7, 0, 1, 1) |

### The lock order, exactly

Every path that writes a code row or a phone row takes its locks in this order and
no other:

    Employee (SELECT ... FOR UPDATE)  ->  the person's codes  ->  the person's phones

| Path | Lock 1 | Lock 2 | Lock 3 |
|---|---|---|---|
| E3 join | Employee | the one code, re-read by name | own live app phones + the phone holding the old secret, by name order |
| E7 make a code | Employee | every Waiting code of the person | - |
| E2 this is not me | Employee | the one code (through the document) | - |
| E9 read it again | Employee | - | the one phone |
| withdrawal | Employee | - | the one phone |
| leaver hook | Employee (the save itself) | Waiting codes, cancelled first | phones, blocked second |

The collision defence is in E3: the code is found by its hash **without** a lock,
the Employee row is locked, and then the code is **re-read with a lock**. The second
of two phones pressing Agree waits on the Employee row, then sees `Used` and is told
`QR_USED`. The test `test_013_ac65_two_joins_on_one_code_exactly_one_wins` runs two
E3 calls on two threads, each with its own `frappe.local` and so its own database
connection, with a 1.2-second pause put into `refuse_unless_eligible` - a function
both E3 and E7 reach only **after** the Employee lock. **The fail-without-fix proof
is to change `for_update=lock` / `for_update=True` in `_employee` and
`_invite_locked` to `False` and run that test**: both callers then proceed, two
phones appear, and the assertion "the other is 410 QR_USED" fails. Not yet run.

### The code's hash, and one thing the spec had wrong

§4.2 says the hash is **emptied** the moment the code stops waiting (OPS-52). Taken
literally, a used or cancelled code could never be found again, so `QR_USED
{used_at}` and `QR_CANCELLED` (AC-54, AC-51, AC-61), and the "used code scanned
again" alert (AC-118), would be unbuildable. I did what step 1 did for the phone:
`token_hash` is emptied and its value moves to a hidden, indexed
`retired_token_hash`. A leaked table still holds no live hash for a dead code, and a
dead code can still be told what it is. The clean-up job's self-check (AC-128, step
6) stays meaningful: `token_hash` on a non-Waiting row must be empty.

### The rate limits, exactly

Frappe's `rate_limit(key=...)` reads `form_dict[key]` and writes the value into the
Redis key in clear (step 1, C-11a). So a thin outer decorator `_limited` hashes the
argument into a form field of its own - `code_hash_key`, `phone_hash_key`,
`hr_user_key` - runs Frappe's limiter on that, and removes the field afterwards.
The field names contain `key`, so Frappe's own Error Log redaction masks them too.
`ip_based=False`: one phone behind a changing mobile IP is one phone. Limits per
§6: E1 20/h per code, E2 5/h, E3 5/h, E9 5/h per phone, withdrawal 5/h per phone,
E7 30/h per HR user. Frappe's limiter does not run when there is no request, which
is why the tests that count give it a fake POST request.

### "Not now", the re-ask and the withdrawal

- E3 takes `agreed` (default 1). With `agreed=0` the code is still used and the
  phone is linked in **Consent not given** - it holds its secret, cannot punch
  (`CONSENT_REQUIRED`), and no acknowledgement row is written. This is the user's
  17 Sep decision.
- E9 with the current version writes the reading and, if the phone was parked,
  makes it Active with `status_change_source = The employee`. No new code.
- `withdraw_agreement` moves an Active phone to Consent not given the same way.
  Nothing is erased: the row, its secret hash, its punches and its readings all
  stay. A second call is harmless. A blocked phone gets `DEVICE_BLOCKED` here as
  everywhere.
- **Nothing records a dismissal.** The re-ask being dismissible for the session
  (C-4) is the app's; the server has no endpoint that records "no", so a dismissed
  prompt leaves no trace and cannot be mistaken for a refusal.

### Company scoping (C-11c) for the two new doctypes

Same pair as the phone record, now shared: `_scoped_by_employee_company(doctype,
user)` and `_one_row_by_employee_company(doc, user)`. Wrapped as `invite_*` and
`acknowledgement_*` for `hooks.py`. Pinned by the two-company test in the step-3
module, which fails without the four hook lines.

---

## 2 · The acceptance criteria, one by one

| AC | How | Proven? |
|---|---|---|
| AC-38 | `make_code`: Waiting, employee, owner = maker, `lifetime_hours`, `expires_at` = now + hours, hash stored, `link` = `get_url("/enrol")#t=<code>`, 43 chars | test written, **unrun** |
| AC-39 | Never stored; test searches the row, Version, Comment, Notification Log, Error Log | written, unrun |
| AC-40 | `_lifetime`: one of the six, ≤ setting, else "Choose a time up to your organisation's setting of {0}." | written, unrun |
| AC-41 | Waiting codes locked and cancelled "Newer code made" before the insert | written, unrun |
| AC-42 | `NOT_FIELD_ROLE` / `APP_OFF_FOR_FIELD` / `FEATURE_OFF` / "Only active employees can be invited." | written, unrun |
| AC-43 | HR role required **and** `frappe.has_permission("Employee", "read", doc=...)` for that user | written, unrun |
| AC-44 | 30/h per HR user, keyed on the hash of the user | written, unrun |
| AC-45 | Permissions in the JSON; controller for Administrator/scripts; no Print Format | written, unrun |
| AC-53 | Exactly seven keys; the notice includes the tick-box words | written, unrun |
| AC-54 | `_refuse_if_dead` + the retired hash; no name in any dead answer | written, unrun |
| AC-55 | Eligibility refused after the code is found, before any name is built | written, unrun |
| AC-56 | `surname_initial` = first char of `last_name` or empty | written, unrun |
| AC-58 | Waiting past `expires_at` → `QR_EXPIRED` at E1 and E3, no write | written, unrun |
| AC-59, AC-63 | 20/h and 5/h per code | written, unrun |
| AC-60 | Left employee at E1 → cancelled "Employee left", committed, then `QR_CANCELLED` | written, unrun |
| AC-61, AC-62 | E2 cancels + N2; a dead code answers as E1 and changes nothing | written, unrun |
| AC-64 | One transaction; Active from the first write; `activated_by` = the maker | written, unrun |
| **AC-65** | The lock order; two threads, two connections | **written, unrun; fail-without-fix owed** |
| AC-66 | `record_acknowledgement` patched to raise → 500, nothing written, code still works | written, unrun |
| AC-67 | Stale version → `NOTICE_CHANGED` with rows, nothing written | written, unrun |
| AC-68 | App off / designation / expired / Left → each code, nothing written | written, unrun |
| AC-69 | Extra fields are dropped by the signature; canaries searched | written, unrun |
| AC-70 | E3 and E7 together: same first lock, so no cycle | written, unrun |
| AC-72 to AC-75 | The phones lock; own → Replaced with `replaced_by`; other's → Removed + N4; web phone untouched; own secret again → no alert | written, unrun |
| AC-94 | E9: new row, old unchanged, stale → 409; same version twice → no extra row | written, unrun |
| AC-95 | `register_device` writes a "Web check-in page" row | written, unrun |
| AC-97 | Step 1's pin on the exact words still stands; E1 sends them from the store | proven in step 1 |
| AC-98 | JSON permissions + insert-only controller | written, unrun |
| AC-116 to AC-119, AC-121, AC-122 | `field_app_alerts`; recipients by permission; no secret in the text; `_send` never raises | written, unrun |
| AC-123 to AC-125 | `enrol.html` / `enrol.py` | written, unrun (file checks) |
| AC-135 (codes) | Leaver hook cancels Waiting codes first | written, unrun |
| AC-149 (codes, readings) | The shared scoping pair | written, unrun |
| C-3 | `withdraw_agreement` | written, unrun |
| AC-17 (waiting count) | `_waiting_codes()` | written, unrun |

### Not in step 3, deliberately

- **E10 cancel (US-7), E11 block, E12, the Employee form section, the QR dialog,
  the printed sheet** - step 5. `make_code` exists so a code can be made from the
  console or a REST call; no screen calls it yet.
- **N5 (threshold alert), the daily clean-up, the counters** - step 6.
- **Erasure on withdrawal** - not built, as agreed.
- **`deploy/nginx.conf`, `subscription.requires_feature`, any hrms index,
  `www/hrms-employee.html`, the old consent fields, `patches.txt`** - not touched.
  No patch: two new doctypes and two new device fields all come from the JSON on
  migrate.
- **`register_device` still writes `consent_given_on` / `consent_version`.** The
  web page and slice 014's tests read them; stopping is the page's own change.
  Declared, not hidden.

---

## 3 · The seven dimensions, against the code I wrote

| Dimension | Before → after | Why |
|---|---|---|
| **Performance** | **neutral to slightly degrades, bounded** | E1 is three indexed reads (two hash lookups, one Employee) plus the settings' three reads. E3 is the same plus three locked reads, one to four writes, one acknowledgement insert, today's punches, the shift location. No loop does a query except the old-phones loop, bounded by how many live app phones one person has (normally one). Alert recipients: one permission check per HR Manager, a handful. Designed volume: 400 field workers, ≤ 3,000 codes a year |
| **Security** | **improves** | The code is never stored; per-code and per-phone limits on the hash; the check answer names the least; HR needs both the role and Frappe's read on that employee; the two new doctypes are scoped by company and writable by nobody; `ignore_permissions` counted at exact ceilings (7/0/1/1) |
| **Reliability** | **improves** | One fixed lock order across six writers; the join is one transaction the wrapper rolls back on any failure; alerts never raise into the save; the withdrawal and E9 are safe to call twice; the leaver hook's new work is inside its own try |
| **Scalability** | **neutral** | Locks are per person, held for milliseconds (plus 1.2 s only in the test). Two joins for different people never touch the same rows |
| **Maintainability** | **improves** | One eligibility function, one notice store, one codes table, one scoping pair for three doctypes, one `_limited` decorator for six endpoints. Against that: `field_app_join` imports five private names from `field_checkin` |
| **Data integrity** | **improves** | The code's hash retires in the same save as its status; the phone's hash likewise (step 1); the old phone is replaced in the same transaction as the new one; readings are insert-only; `invite` on the phone is frozen |
| **Compliance / privacy** | **improves** | The readings history (PRIV-3); the tick-box words as versioned data (PRIV-4, C-1); the least in E1 (PRIV-5); no coordinates in E3's workplace (PRIV-6); no name in a dead-code answer (SEC-3); the withdrawal path that erases nothing but stops recording (C-3); alerts carry no code, hash or secret and go only to HR who may read the person. **No visibility widened**: the two new doctypes are HR-only and company-scoped |

---

## 4 · Things I found that the spec has wrong or unsettled

1. **§4.2 "hash emptied when the status leaves Waiting" makes AC-54, AC-51 and
   AC-118 unbuildable.** Built with a retired hash, as the phone record does
   (section 1). The spec should say so.
2. **`Notification Log.type` is a Link in Frappe v16, not a Select.** The alerts
   use the built-in `Alert` type. If a site somehow lacks it, the insert fails and
   `_send` logs it; the join stands.
3. **The spec's E3 has no "Not now" variant**, but the user's 17 Sep decision does.
   Built as `agreed=0` on E3. Somebody should add it to §6.
4. **AC-64 says "empty punches" for the join answer.** The answer sends today's
   punches for the employee (a web punch earlier the same day would show), which is
   what the home screen needs. Spec wording, not behaviour.
5. **Step 1's `_device_from_token` refused "Consent not given" for everything.** E9
   and the withdrawal need to reach such a phone, so the function takes an
   `allowed` set. The default is unchanged; the step-1 and step-2 tests still hold.

---

## 5 · Three personas

| Persona | What changes | What must not change - and did not |
|---|---|---|
| **CXO / System Manager** | Can read every code and reading; cannot make, change or delete one by hand; can call `make_code` | Cannot see a code after it was made; cannot unblock a phone |
| **HR Manager / HR User** | Can call `make_code` for employees they may read; get the four alerts for employees they may read; read codes and readings for their companies only | An HR user limited to company A cannot invite, read or be told about company B |
| **Employee (field worker)** | Joins with a code in one step; may say "not now" and agree later; may withdraw; is asked again when the notice changes | Never sees a block reason; never learns who else has a code; nothing erased on withdrawal |
| **Employee (office colleague), line manager** | Nothing. No role on either new doctype | - |

---

## 6 · What I ran, and what I did not

**No bench, no container, no site, no database.** Docker Desktop was down for the
entire build. Static checks only:

| Check | Result |
|---|---|
| `ast.parse` on every changed `.py`; `json.load` on the three doctype JSONs | all parse |
| `ruff check --config hrms/pyproject.toml` on every file I wrote or changed | **All checks passed** (after one import-order fix and three findings in the test module) |
| `scripts/check_app_integrity.py` | **613 checks, OK** (602 at step 2; the two doctypes, hooks and the page add eleven) |
| `ignore_permissions` count in the four new files | 7 / 0 / 1 / 1, written into `CEILINGS` at exactly those numbers |
| `enrol.html` scanned for `http://` / `https://` and for `src=`/`href=` on script, link and img | none |
| Frappe v16.33.1 source read (before Docker stopped) | `rate_limit` signature and the no-request bypass; `get_value(for_update=)`; pypika `.for_update()`; `enqueue(now=, enqueue_after_commit=)` and `frappe.in_test`; `make_notification_logs`, `_get_user_ids` (enabled users, by email); `Notification Type` built-ins; `frappe.local.response_headers` applied in `app.py`; `sanitized_dict`'s masked names |

**Owed, and not started:**

1. `bench --site test_site migrate` from a throwaway container mounting this
   worktree (two new doctypes, two new device fields). test_site carries the step-2
   schema; step 3 adds to it.
2. `run-tests --module alvoraa_portal.tests.test_field_app_step3_013` (50 tests).
3. **The fail-without-fix proof:** `for_update` off in `_employee` and
   `_invite_locked`, run `test_013_ac65_...`, watch it fail, restore with
   `git checkout --`, re-run green.
4. The step-1, step-2 and 014 modules, then the full `alvoraa_portal` and
   `alvoraa_goals` suites once. Baseline 1,304 OK / 18 OK.
5. **Two names in the tests I could not verify against the source after Docker
   stopped:** `frappe.allowed_http_methods_for_whitelisted_func` and
   `frappe.cache.get_keys` / `delete_keys`. Both are names I know from the
   framework, and step 1 read the whitelist region; if either is wrong the first
   run says so and the test, not the product code, changes.
6. Three things in the thread test that only a run can settle: that
   `frappe.init` + `connect` in a thread gets its own connection (it should - `local`
   is thread-scoped), that MariaDB's lock wait behaves as expected under the 1.2 s
   pause, and that `frappe.enqueue(now=True)` in the thread inserts the alert rows
   without a `frappe.flags.in_test` on that thread.

---

## 7 · What else moved while I worked

`git fetch origin dev` **failed** with `fatal: bad object refs/heads/slice/025-brand-logo`
- a broken branch ref in the shared `.git`, belonging to slice 025's session. Not
mine; not touched; reported. The local `origin/dev` ref is still `baa9f68`.

Local `dev` is at `3f5ce3d`, three commits my base `d1fd9c6` does not have
(`4f35960` runbook, `99a17a4` and `3f5ce3d` slice 024). Of my files they touch only
`hooks.py`, at the **top** (`get_website_user_home_page`); every line of mine is at
the end of a block. A rebase will be clean. Not rebased: the instruction was to
commit on the branch only.

---

## 8 · Known gaps and shortcuts, declared

1. **Nothing has run against a database.** Said three times because it is the
   whole story of this document.
2. **The lock-order proof is owed.** The collision test and its fail-without-fix
   run are the point of step 3 and neither has happened.
3. **`make_code` has no screen.** It is callable from the desk console and REST;
   the dialog is step 5.
4. **N5 and the daily job are not built** (step 6), so a code that runs out is
   marked so only when next checked, never by itself, and its hash stays live until
   then. Bounded by the lifetime (≤ 7 days).
5. **`register_device` writes both the old fields and the new row.** Declared in
   section 2.
6. **The thread test's 1.2-second pause** makes two tests slow by design. If the
   suite's time matters, it can drop to 0.5 s once the bench shows how fast the
   second connection reaches the lock.
7. **`hr_managers_who_can_read` loops `has_permission` per HR Manager.** Fine at
   the designed volume; a tenant with hundreds of HR Managers would want the
   company-list shortcut instead.

---

## 9 · Step 3 proven (2026-09-19, later the same day)

Docker came back and the bench was idle (`pgrep run-tests|migrate|bench build` empty;
slice 025's container `hrlocal-025` was found `Exited (255)` from the restart and left
in place). Everything below ran from a throwaway container `hrlocal-013` mounting
**this worktree's** three apps against the shared `hrlocal-sites` volume, on the
`hrlocal` network, as user `frappe`, one run at a time, with the bench claimed on the
work board from the first command to the last. No `docker cp`, no dev tenant, no
server, nothing pushed, nothing in local `dev`.

### 9.1 · What ran, and the real numbers

| Step | Command / check | Result |
|---|---|---|
| The two unverified names | `env/bin/python -c` in the container | `frappe.allowed_http_methods_for_whitelisted_func`: **exists**. `RedisWrapper.get_keys` / `delete_keys`: **both exist** |
| Baseline | Custom DocPerm on test_site | **228 rows / 45 doctypes** |
| Migrate | `bench --site test_site migrate` | **2 min 42 s, 0 failed.** Both new tables present; `invite` and `app_version` on the device table |
| First run, step-3 module | `run-tests --module ...test_field_app_step3_013` | 41 + 9 tests, **47 errors**: one cause - `frappe.has_permission` does not take `print_logs` (only `frappe.permissions.has_permission` does). Fixed |
| Second run | same | **19 errors, 2 failures**: the test helpers passed the filter dict positionally to `get_all` (lands in `fields`); the fake request had no `host` for `get_url`; **a product bug** - E2 on a used code sent the "scanned again" alert (N3) to every HR Manager on the site, which AC-62 forbids; and N2's rows vanished. Fixed the first three |
| N2 investigation | `_send` logged only a sentence; reproduced the mechanism directly (probe row inserted fine); the Error Log showed no new failure on reruns | The rows were written, then **rolled back by the next refusal in the same test** - in a test run the alert is written at once inside the open transaction. In production the request handler commits at the end of a successful call. The test helper now commits after a successful call, as the handler does. `_send` now logs the value-free code places on failure, like the punch |
| Third run | same | **2 failures**: `retry_after_s` empty on a 429 (Frappe's decorator says how many, not how long - the value `code_and_values` reads is the global limiter's) - **fixed**: `_limited` answers `TOO_MANY_TRIES` with the window's remaining seconds from the key's TTL; and the maker could not read an acknowledgement row - **C-11c working as pinned** (an HR Manager with no company and no employee record sees nothing); the test now gives the maker a company for that check |
| Fourth run | same | 1 error: AC-44 still expected Frappe's raw `RateLimitExceededError`; it is now a `TOO_MANY_TRIES` refusal with a wait. Test fixed |
| **Fifth run** | same | **41 + 9 = 50 OK** |
| **Fail-without-fix (the lock order)** | `for_update=lock` → `False` in `_employee`, `for_update=True` → `False` in `_invite_locked`; `test_013_ac65_two_joins_on_one_code_exactly_one_wins` | **FAILED**: `AssertionError: Tuples differ: (404, 'INVALID_REQUEST') != (410, 'QR_USED')` - with no lock both joins ran into each other and the loser's writes collided. Restored with `git checkout --`, tree clean, re-run: **OK**. The broken state was never committed |
| Step 1 module | `...test_field_app_step1_013` | **15 + 13 = 28 OK** |
| Step 2 module | `...test_field_app_step2_013` | **27 + 7 = 34 OK** |
| Slice 014 module | `...test_checkin_security_014` | **14 + 2 = 16 OK** |
| Full `alvoraa_goals` | `run-tests --app alvoraa_goals` | **18 OK**, 2 skipped |
| Full `alvoraa_portal`, first time | `run-tests --app alvoraa_portal` | **613 + 741 = 1,354 tests, 1 failure** (skipped=4), 15 min + 70 min. The failure was `test_data_review_012.TestThePage.test_endpoint_hygiene` - **mine, by pollution**: my `/enrol` test replaced `frappe.local.response_headers` with a plain dict and left it there; 012's endpoint sets its `no-store` header with `.set` inside a try/except and its test rebuilds the object with `__class__()`, so 900 tests later there was no header. Test fixed to build one of the same class and restore the original; proven by running my module and then 012's module in that order: **50 OK, then 25 + 1 OK** |
| Custom DocPerm after all of the above | | **228 rows / 45 doctypes** - unchanged |
| Full `alvoraa_portal`, second time (after the test fix) | `run-tests --app alvoraa_portal` | **613 + 741 = 1,354 tests, 3 errors + 3 failures - none from the branch, all from an unclaimed run alongside mine.** MariaDB's `LATEST DETECTED DEADLOCK` (read as root) names both parties: my container (172.30.0.7) and **`hrlocal-bench` itself (172.30.0.6)**, running a second `alvoraa_portal` suite with slice-012 fixture users, not claimed on the work board. (a) The 3 errors: `test_access_control` tearDowns deadlocked against it. (b) The 3 failures: `test_field_app_step2_013` AC-17/18/19 - "ValidationError not raised" and the reason not emptied, i.e. the HR Settings hooks did not fire. `hrlocal-bench` mounts the **main checkout** (`dev` code, which has no step-2 hooks) and shares the same Redis, so its run rebuilt the site's `app_hooks` cache without them while mine was between those tests. Both modules **pass alone** straight afterwards: step 2 **27 + 7 OK**, `test_access_control` **34 OK**. Recorded on the board for whoever ran it |
| **Full `alvoraa_portal`, third time** (nothing foreign live) | `run-tests --app alvoraa_portal`, then `alvoraa_goals` | **613 + 741 = 1,354 tests, OK**, 0 failures, 0 errors, 4 skipped, 13 min + 39 min; no deadlock. `alvoraa_goals` **18 OK**, 2 skipped. Custom DocPerm afterwards **228 rows / 45 doctypes** - unchanged. (Baseline was 1,304; the 50 new tests account for the difference exactly) |

### 9.2 · What the runs found in the product, and the fixes (commits)

| Commit | What |
|---|---|
| `f960e58` | `frappe.permissions.has_permission` in `make_code` and the alert recipients; N3 only from E1 (AC-62); `TOO_MANY_TRIES` carries `retry_after_s` from the key's TTL; failed alerts log code places |
| `07f148a` | The test module as the runs corrected it |
| `37d9b21` | The enrol test restores the headers object (the full-run pollution) |

Nothing else in the product changed. The lock order, the doctypes, the endpoints'
shapes and the answer keys are as built.

### 9.3 · State left behind

- `slice/013-mobile-app` at `37d9b21` (seven step-3 commits on step 2's `5ef47cd`). Not
  in local `dev`, not pushed.
- `test_site` carries the step-3 schema (two new tables, two new device columns).
  Nothing on `dev` reads them, so nothing there breaks; anyone rebuilding test_site
  from `dev` must migrate from this branch before running these modules.
- Container `hrlocal-013` removed; bench claim cleared on the work board;
  `hrlocal-025` left as found (Exited).
- Both new names are verified; the earlier list of unverified names is closed.
