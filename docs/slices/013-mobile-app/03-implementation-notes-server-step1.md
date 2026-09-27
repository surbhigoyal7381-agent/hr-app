---
slice: 013-mobile-app
artifact: 03-implementation-notes-server-step1
author: hrms-fullstack-engineer
date: 2026-09-18
scope: STEP 1 of the server work only - US-1, US-2, US-4 (the part step 1 needs), US-23, and the file split
branch: slice/013-mobile-app in .claude/worktrees/013-mobile-app, rebased on local dev d1fd9c6
status: built locally on a branch. NOT in local dev. NOT pushed. Database-backed tests UNRUN.
update-2026-09-21: PUSHED. Now on origin/dev (confirmed at commit 146fa59). GitHub
Actions' "Python tests" job (a real MariaDB-backed test site) ran at that commit and
passed. See ALV-40 and ALV-32 on YouTrack for the check. The line above describes this
step's state at the time it was written, not its state today.
---

# 013 step 1 — what I built, and what I could not prove

**Read this first — and see the update note above the frontmatter's `status`
line.** At the time this was written, everything below was true: nothing was in
`dev`, nothing was pushed, no bench command had run, no site had changed. That
is no longer the case — this step's code is on `origin/dev`, and the
database-backed tests it describes as unrun have since run for real, in CI, and
passed. What follows is left as-written, as the historical record of what was
built and how it was checked before that push.

---

## 1 · What I built, file by file

| File | New or changed | Mechanism | Why that one |
|---|---|---|---|
| `alvoraa_portal/field_app_photos.py` | **new** (moved) | move | The photo rules, the retention setting and the daily purge are not about the punch or about which phone is calling |
| `alvoraa_portal/field_app_access.py` | **new** (moved) | move | Who may read a punch and its photo, and the record of who looked at a face |
| `alvoraa_portal/field_app_pwa.py` | **new** (moved) | move | The icon, the manifest and the service worker |
| `alvoraa_portal/field_app_errors.py` | **new** | build | The one codes table §7.1 demands, the refusal that carries a code, the app-version check, and our own plan gate |
| `alvoraa_portal/field_app_notice.py` | **new** | build | The notice's words as versioned data, so app, desk and web page stop each holding a copy |
| `alvoraa_portal/field_checkin.py` | changed | extend | Codes on every refusal, the phone's new states, the leaver fix, the notice store wired in |
| `.../doctype/alvoraa_field_device/alvoraa_field_device.json` | changed | configure | 3 new statuses, 7 new fields, `set_only_once` on `employee`, `create` and `delete` removed from every role |
| `.../doctype/alvoraa_field_device/alvoraa_field_device.py` | changed | extend | The controller rules, because `validate` is the one place all five doors meet |
| `alvoraa_portal/hooks.py` | changed, 4 lines | configure | Each hook path now names the file the code actually lives in |
| `alvoraa_portal/tests/test_field_app_step1_013.py` | **new** | build | The pin tests |
| `alvoraa_portal/tests/test_checkin_security_014.py` | changed, 4 places | extend | Slice 014's fixture says it stands in for the server; two status numbers move from 417 to 400 |

`field_checkin.py` went from **1,126 lines to 726** before the new behaviour went
in, and is **about 800** now.

### The split, and why nothing moved in the same commit as a change

Commit `92bf1cf` moves code and changes none of it. Every moved name is imported
straight back into `field_checkin`, because `hooks.py`, the web page and the
browser all call them at `alvoraa_portal.field_checkin.<name>`, and a path in a
hook or a browser URL is a promise. I checked in the installed source that Frappe
keys its whitelist on the **function object**, not on the path
(`frappe/__init__.py:423-466` at v16.33.1), so the three guest endpoints are
still whitelisted through their old address. I then proved it by importing the
modules in a throwaway container and asserting each function is in
`frappe.whitelisted` and `frappe.guest_methods`.

`scripts/check_app_integrity.py` reads the source with AST rather than importing
it, so a hook pointing at a re-export read to it as a hook pointing at nothing —
it failed with 4 problems. I fixed that by pointing those four hook paths at the
new modules. The re-exports stay for everyone else.

---

## 2 · The acceptance criteria, one by one

| AC | How it is satisfied | Proven? |
|---|---|---|
| AC-1 Pending phone and unknown secret are identical | Both go through `_refuse_as_pending()` → `DEVICE_PENDING`, 401. The response body is `{http_status_code, exc_type, code, values}` and is identical for both; the sentence is one string, shared | test written, **unrun** |
| AC-2 Blocked / Replaced / Removed each get their own code, no reason leaks | `_REFUSAL_FOR_STATUS`. `DEVICE_BLOCKED` declares **no values at all**, so `refuse()` drops a `reason` even if someone passes one | value-dropping proven; the rest unrun |
| AC-3 missing or short secret → `NOT_SET_UP` | `_device_from_token`, unchanged rule, new code | unrun |
| AC-4 no status without a named refusal | A test reads the Select options off the doctype and fails if one has no entry in `_REFUSAL_FOR_STATUS` | **proven** (read off the shipped JSON) |
| AC-5 stopping a phone retires its secret in the same save | `before_save` → `_retire_the_secret`, for every path including a person blocking from the desk. `_device_from_token` then looks up `retired_token_hash` too, so the old secret gets its own code instead of "not set up" | unrun |
| AC-6 an Active phone still punches | Control case | unrun |
| AC-7 a stopped phone is never switched back on | `_status_moves_are_legal`: `old in FINAL` refuses for everybody, server flag included | unrun |
| AC-8 HR cannot create or delete | `create` and `delete` removed from all three roles, **plus** a controller insert guard and `on_trash` for Administrator and scripts | permissions **proven** from the JSON; controller unrun |
| AC-9 / AC-13 frozen fields | `FROZEN_AFTER_INSERT` and `FROZEN_UNLESS_SERVER`, compared as text | unrun |
| AC-10 HR switches on a waiting web phone | Allowed pair, sets `activated_by` and the three `status_changed_*` fields | unrun |
| AC-11 a block says why | `_a_block_says_why` | unrun |
| AC-12 nobody sets Replaced, Removed or goes back to Pending | `SERVER_ONLY` and `ALLOWED_BY_A_PERSON` | unrun |
| AC-26 every code keeps its status and values | A second copy of the table in the test is the pin | **proven** |
| AC-28 `Cache-Control: no-store` | `_never_cache()` on every device call. Frappe already defaults to no-store, so this changes nothing today — which is why it is written down | not separately proven |
| AC-29 the version header | `parse_version` + `check_app_version`. 1.10.0 is newer than 1.9.0; a 25-character string, "abc" and "1.2" are all refused; no header is the web page and is allowed | **proven** |
| AC-30 over-long secret, bad `log_type` → `INVALID_REQUEST` with no field name | `MAX_TOKEN_CHARS` and the log-type check. The sentence names no field | partly unrun |
| AC-35 the web page behaves exactly as before | The page matches on the sentence and on "not 2xx" only (`field-checkin.html:648-667`, hand-checked). No sentence changed. Two status numbers moved, which the page never reads | **hand-traced, not run** |
| AC-135 a leaver's phones stop, secrets retired | `block_devices_for_leaver` rewritten to go through the document | **test written, unrun — this is the one I most want to run** |
| AC-136 a rehire does not re-arm the old phone | Blocked is final; the hook returns early on Active | unrun |

### Not in step 1, deliberately

- **`invite` (Link to Alvoraa App Invite) and `app_version` on the phone record.**
  `Alvoraa App Invite` does not exist until step 3, and a Link field pointing at
  a doctype that is not there breaks a migrate. `invite` is already in the
  controller's frozen list, so it is protected the day it appears.
- **Cancelling a leaver's waiting codes** (the other half of AC-135). Same
  reason: no invite doctype yet.
- **`APP_OFF_FOR_FIELD` and `NOT_FIELD_ROLE`** are in the codes table but nothing
  raises them yet — the settings they depend on are step 2. They are in the table
  now on purpose, because an app built against step 1 must already know every
  screen it will ever be shown (the §6 "only ever add" rule).
- **The withdrawal action.** The decision was that step 1 only needs the "not
  agreed" state to exist and to refuse punches. It does: `Consent not given` is a
  status, and `_device_from_token` refuses it with `CONSENT_REQUIRED`. The
  employee-facing action is step 3.
- **Erasure on withdrawal.** Not built, as agreed. Waiting for counsel.
- **Any index on a standard hrms doctype.** None added.
- **`www/field-checkin.html`, `www/field_checkin.py`, `subscription.py`,
  `patches.txt`, `deploy/nginx.conf`, `hrms-employee.html`.** Untouched.

---

## 3 · The seven dimensions, re-assessed against the code I actually wrote

| Dimension | Before → after | Why |
|---|---|---|
| **Performance** | **neutral** | `_device_from_token` can now do a **second** indexed lookup — on `retired_token_hash`, and only when the first misses. `retired_token_hash` carries `search_index: 1`, so it is one index hit, not a scan. No loop does a query. The leaver hook now loads and saves a document per phone instead of one `set_value`: a handful of rows on a rare event, on a path a human is already waiting on. `_refuse_duplicate` now asks for the `time` column it already read a row for — same query, one more column |
| **Security** | **improves** | Four holes that are open today close: HR can no longer re-point a phone at another employee, switch a blocked one back on, delete the record, or insert one by hand. `retired_token_hash` is hidden, `no_copy`, and never in any answer. The `values` in a refusal body are **filtered to the names its code declared**, so a stray `reason=` cannot reach the phone even if someone passes it. `ignore_permissions` gained no new use: the one insert that has it (`register_device`) had it before. `subscription.requires_feature` was not touched, and a test asserts so. **One thing I did not do:** `email`, `print` and `share` are still on the phone record for HR Manager and System Manager. That was question C-7 and it was not answered, so I left it and am flagging it again — a shared phone record says who carries which phone |
| **Reliability** | **improves slightly** | The leaver hook now fails safe: each phone is saved in its own `try`, so one bad row cannot stop the others and cannot stop HR saving the employee. `_device_from_token` fails closed on a status nobody taught it about, and on the impossible case of a retired hash on a live phone. `check_app_version` and `_never_cache` both swallow "there is no request at all", so a console or a background job is not broken by them. The one thing that got harder: the controller now refuses a save it cannot check (`get_doc_before_save()` returning None), which is a refusal where there used to be a silent write |
| **Scalability** | **neutral** | Nothing here grows with headcount. The leaver hook is per-employee and bounded by how many phones one person has |
| **Maintainability** | **improves** | 1,126 lines became five files. The codes live in one table instead of being scattered as sentences. The notice's words are data with one owner instead of a copy per screen. Against that: `field_checkin` now carries a block of re-export imports, which is a real cost and is there to keep a promise |
| **Data integrity** | **improves** | `employee` is `set_only_once` **and** checked in the controller. Statuses are one-way. The secret's hash is preserved rather than lost, so "why did this phone stop" stays answerable. `status_changed_on` exists because `modified` moves on every save and cannot answer it. No cache was added, so there is no invalidation to get wrong |
| **Compliance / privacy** | **improves** | The block reason never reaches the phone — structurally, because `DEVICE_BLOCKED` declares no values. A blocked phone gets no time either, because a time invites a guess at the reason. No new personal data is stored. No visibility widened: the three new status fields are read-only on a doctype no Employee-role user can read at all. `values` never carries a name, an employee ID, a secret, a photo or a coordinate, and the geofence values carry the **distance** but never the workplace's coordinates |

---

## 4 · Things I found that the spec has wrong or unsettled

1. **The spec's `_private_request` ordering note is right and load-bearing.**
   Confirmed: the wrapper must stay above the plan gate, and slice 014's own test
   asserts it. My plan gate sets `__alvoraa_feature__` so that test keeps working.

2. **C-11's first question is answered: Frappe's rate limiter *does* take a
   custom key.** `frappe.rate_limiter.rate_limit(key=..., limit=..., seconds=...,
   methods=..., ip_based=...)` at v16.33.1. So §6's "keyed on the SHA-256 hash"
   is buildable without hand-rolling anything. **But** — and this is why it is not
   used in step 1 — the existing comment in `field_checkin` says Frappe writes the
   key into the Redis key in clear, which would put a device secret's hash in
   Redis. A hash is not the secret, so this is probably fine, but it is a decision
   for step 3 and not a detail.

3. **AC-26 asks for the English sentence in `_server_messages` *and* `code` and
   `values` in the body.** Both happen. `frappe.throw(msg, exc=<an instance>)` is
   supported (`frappe/utils/messages.py:52-54`), so the sentence is queued exactly
   as before and the code travels on the exception.

4. **AC-7 says "the row and its Version count are unchanged".** In a Frappe test
   run `ignore_version` defaults to true, so the Version count is zero either way
   and that assertion would pass vacuously. My test compares the row's `status`,
   `modified` and `token_hash` instead, which actually proves something.

5. **AC-1's "byte-identical bodies" cannot be taken literally for the message.**
   Each queued message carries a random `__frappe_exc_id`. The **response body**
   is byte-identical; the sentence is identical as text. My test asserts both, the
   second as words — the same compromise slice 014 made for the same reason.

6. **The old consent fields are still written** by `register_device`. Finding B
   said to stop, but the acknowledgement doctype it would write instead does not
   exist until step 3. Kept as-is, deliberately.

7. **`join_method` is empty on every phone that exists today**, and I did not add
   a patch to backfill it. Every phone that exists came from the web page, which
   is the only thing that could have made one, and the controller treats an empty
   `join_method` as a web phone. If a patch is ever wanted it can be added later
   without changing behaviour.

---

## 5 · What I ran, and what I did not

**The shared bench `hrlocal-bench` was not used.** Another session is deploying
and owns it. I used `docker run --rm` throwaway containers from the same image
with **no mounts on the sites volume, no network, no database and no site** — one
to read Frappe v16.33.1's own source, one to import my modules, one to run the
checks that need no database. All were removed by `--rm`.

| Check | Result |
|---|---|
| `python -c "import ast; ast.parse(...)"` on every changed file | parses |
| Import every module in a throwaway container | imports; every old `field_checkin.<name>` path resolves |
| `frappe.whitelisted` / `frappe.guest_methods` after the split | all six endpoints still there |
| The six hook paths in `hooks.py`, resolved by import | all six resolve |
| `scripts/check_app_integrity.py` | **592 checks, OK** (it failed with 4 problems before I fixed the hook paths; `dev` is clean, so this is now level with `dev`) |
| `scripts/check_api_paths.py` | 2 unresolved — **both pre-existing on `dev`**, both in `hrms/overrides/employee_payment_entry.py`, neither mine |
| `ruff check` (0.6.9, hrms config) on my files | **All checks passed.** The app as a whole has 295 pre-existing findings and the CI step is `continue-on-error` |
| 12 no-database assertions from the new test module | 11 pass. The twelfth, "every hook path resolves", fails only because `frappe.get_attr` needs a full `frappe.init` that a site-less container does not have; the same six paths were then resolved by `importlib` and all six resolve |

**What did NOT run: every test that needs a database.** That is the whole of
US-1's behaviour, US-2's five doors, and — the one that matters most — **the US-23
leaver test**. They need `bench migrate` on the shared `test_site` to create the
new doctype fields, and both the bench and that site belong to another session
right now. **Nobody should treat step 1 as done until they have run
`bench --site <site> run-tests --module
alvoraa_portal.tests.test_field_app_step1_013` and
`...test_checkin_security_014`.**

The fail-without-fix proof for US-23 is also owed: the leaver test should be run
once against the old `frappe.db.set_value` line to show it fails.

---

## 6 · What else moved while I worked

Nothing. `git fetch origin dev` brought in no commits — `origin/dev` is still
`baa9f68`, which is behind local `dev` `d1fd9c6` (that commit is local and not
pushed). No file I touched was touched by anyone else. No conflict, nothing to
reconcile.

Files I hold, and who else is near them:

| File | Who else | What I did about it |
|---|---|---|
| `hooks.py` | slice 010 claims `doc_events` for Attendance Request and Leave Application | I changed four lines, none of them in 010's keys, and added nothing |
| `test_checkin_security_014.py` | slice 014 | Four small edits, each with a comment saying why. No assertion's *purpose* changed |
| `subscription.py` | slice 016 | **Not touched.** A test asserts `requires_feature` still reads as it did |
| `www/field-checkin.html`, `www/hrms-employee.html`, `patches.txt`, `deploy/nginx.conf` | 009, 010, 014, 015 | Not touched |

---

## 7 · Known gaps and shortcuts, declared

1. **The database-backed tests are unrun.** Declared above, twice, because it is
   the most important thing on this page.
2. **No fail-without-fix proof** for the leaver fix, for the same reason.
3. **`email`, `print` and `share` are still on the phone record.** Question C-7
   was never answered. I did not decide it on the user's behalf.
4. **`APP_OFF_FOR_FIELD` and `NOT_FIELD_ROLE` are declared but unraised.** They
   belong to step 2's settings. Declaring them now is deliberate; leaving them
   unraised is a gap only in the sense that the table is ahead of the code.
5. **`MIN_APP_VERSION` is `1.0.0` and nothing guards it yet.** AC-37's CI check —
   which stops somebody raising it above a version whose replacement has been out
   under 90 days — is step 6. Before the first store release the rule is written
   down in the file and enforced by nobody.
6. **The rate limits are still Frappe's per-caller ones**, not §6's per-code and
   per-phone ones. That is step 3's work; §6's numbers are unbuilt and I have not
   pretended otherwise.
7. **`_never_cache()` is belt and braces.** Frappe already sends `no-store` on API
   answers, so this line changes nothing today. It is there because a framework
   default can move and a cached punch refusal would tell somebody they are
   checked in when they are not.
8. **A migrate is needed** before any of this works on a site: the doctype gained
   fields and Select options. Nobody has run it.

---

## 8 · Step 1 proven (2026-09-19)

Run on the shared `test_site` from a throwaway container `hrlocal-013` mounting
the 013 worktree (the shared bench mounts the main checkout). One run at a time,
the bench claimed on the work board and cleared afterwards, container removed.
No `docker cp`, no dev tenant, no server, nothing pushed, nothing in local `dev`.

### 8.1 · What ran, and the real numbers

| Step | Command / check | Result |
|---|---|---|
| Migrate | `bench --site test_site migrate` from the container | **2 min 33 s, 0 failed.** Device table now 30 columns (the 7 new ones present), 6 statuses, `employee` set-only-once, create/delete gone from all three roles. `email`/`print`/`share` still there (C-7, unanswered, left alone) |
| First run | `run-tests --module ...test_field_app_step1_013` | 15 + 13 tests, **1 error** (`test_013_ac11`: its own rollback deleted the phone it had just made - a missing `frappe.db.commit()`) |
| First run | `run-tests --module ...test_checkin_security_014` | 14 + 2 tests, **3 failures** - see 8.2, a real product bug |
| After the fix (commit `3a45261`) | both modules | **013: 15 + 13 = 28 OK. 014: 14 + 2 = 16 OK** |
| Fail-without-fix (US-23) | old `frappe.db.set_value(..., update_modified=False)` body put back in `block_devices_for_leaver`, module re-run | **`test_013_ac135_leaving_stops_every_phone_and_retires_its_secret` FAILS** (`AssertionError: '' != 'Left the company'`); the other 27 pass. Fix restored with `git checkout --`, module re-run: **28 OK**. The broken state was never committed |
| Full `alvoraa_portal` | `run-tests --app alvoraa_portal` | **597 + 673 = 1,270 tests, OK**, 4 skipped, 0 failures, 0 errors (35 min). The "known 14" no longer fail on this head - slices 020/022 fixed them |
| Full `alvoraa_goals` | `run-tests --app alvoraa_goals` | **18 OK**, 2 skipped |
| test_site afterwards | Custom DocPerm | **228 rows / 45 doctypes before and after** - unchanged. HR Settings value restored, probe rows and probe users gone |

### 8.2 · What the tests found, and the fix

**A real bug: no refusal carried its sentence.** `refuse()` in `field_app_errors.py`
raised `FieldAppRefusal` directly. Its docstring, and section 4 item 3 above, said the
sentence went through `frappe.throw` into `_server_messages` - it did not. Every
refusal came back with an empty message log. The web check-in page matches on that
sentence (`field-checkin.html:648-667`), so AC-35 ("the web page behaves exactly as
before") was broken. Slice 014's three sentence-pinning tests caught it. The 013
module's own AC-1 "same sentence" check passed because two empty strings are equal.

Fix, commit `3a45261` on `slice/013-mobile-app`:
- `refuse()` now raises through `frappe.throw(message, FieldAppRefusal(...))`. Frappe
  v16.33.1 accepts an exception *instance* as `exc` (`utils/messages.py`,
  `_raise_exception`: sets `exc.args` and `__frappe_exc_id` on it), so the code and
  values still travel on the exception the wrapper catches.
- The AC-1 pin now also asserts `"waiting for HR"` is in the sentence, so it can never
  pass on nothing again.
- `test_013_ac11` commits its phone before its rollback, like its neighbours.

Nothing else changed. No scope was widened.

### 8.3 · C-11 answered on the live site

**a. Does `rate_limit` accept a custom key? Yes - exercised, not just read.** A function
decorated `@rate_limit(key="probe_key", limit=2, seconds=30, methods=["POST"],
ip_based=False)` was called with a fake POST request against the real Redis: calls 1
and 2 returned, call 3 raised `RateLimitExceededError`, and a different key value got
its own fresh counter. Two things step 3 must know:
- `key` is the **name of a form field**; the decorator reads `frappe.form_dict[key]`
  and writes the value into the Redis key **in clear**: the keys seen were
  `rl:c11.probe:hashA:30` and `rl:c11.probe:hashB:30`. So the field the decorator
  reads must already hold the SHA-256 hash, never the secret. A thin outer decorator
  that sets `form_dict["token_hash"] = _hash(token)` before `rate_limit(key="token_hash")`
  runs does it. Section 4 item 2's worry is confirmed and has a clean answer.
- With `ip_based=True` and a key, the identity is `ip:value`, so one phone behind a
  changing mobile IP gets a new bucket per IP. For per-phone limits use
  `ip_based=False`.

**b. Are HR Settings values cached across worker processes? Two different answers,
depending on the read, and neither needs a restart.**
- `frappe.db.get_single_value("HR Settings", field)` is cached only in the connection's
  `value_cache`, which lives for one transaction. Proven with two processes: A read 1,
  B saved 0 and committed, A on the same open transaction still read 1, A after
  `commit()` read 0, A after a fresh `init/connect` (what every request does) read 0.
  **Live on the next request.** This is the read step 2 should use for its HR Settings
  fields.
- `frappe.get_cached_value(...)` stayed stale for the rest of the same request and was
  fresh on the next one.
- `frappe.db.get_default(key)` - what `field_app_photos._setting` uses for the photo
  retention days - goes through Frappe v16's `ClientCache` (`utils/redis_wrapper.py:448`):
  a per-process copy in front of Redis, invalidated by Redis client tracking, with a
  **hard-coded 10-minute local TTL and 1,024-key cap**; the source itself says "do not
  expect sub-second invalidation guarantees across processes". Measured across two
  processes: a changed value was seen at the first read 3 s after the change, and again
  at +17 s, +37 s and +62 s; a brand-new key was seen 3 s after it was set. One earlier
  un-seeded run read stale for about 5 s and did not reproduce. **Practical answer: a
  Global Default change is normally live in seconds, worst case 10 minutes, no restart.**
  If step 2 puts a setting in HR Settings and reads it with `get_single_value`, the
  60-second requirement is met with margin.

**c. Does an HR user's Company User Permission reach `Alvoraa Field Device`? No. This
is a visibility hole, and it is pre-existing, not step 1's.** Set up inside one
rolled-back transaction on test_site (nothing left behind): a user with `HR User`, and
another with `HR Manager`, each with a User Permission `Company = S010 Second Company`,
plus one Active phone for an employee of that company and one for an employee of
`Alvoraa Test Company`. For **both** roles:
- `frappe.get_list("Employee")` showed only `S010 Second Company` - the restriction works
  where a Company link exists.
- `frappe.get_list("Alvoraa Field Device")` returned **both phones**, including the other
  company's.
- `frappe.has_permission("Alvoraa Field Device", "read", doc=<other company's phone>)`
  returned **True**, and `get_doc(...).check_permission("read")` did not raise.
The doctype's link fields are `employee`, `activated_by`, `status_changed_by` and
`replaced_by` - no Company - and it has no `permission_query_conditions` or
`has_permission` hook (only `Employee Checkin` has them). Frappe's user permissions
only follow link fields present on the doctype, so a company restriction never reaches
it. **What it exposes today:** the other company's phone rows - employee name, device
label, platform, status, last seen, check-in count. The device doctype has existed with
these perms since slice 008, so dev has this hole now. **Recommended fix (needs the
user's word - it changes the impact analysis's "no change to
permission_query_conditions" line):** a `permission_query_conditions` + `has_permission`
pair for `Alvoraa Field Device` that scopes through the Employee's company, shaped like
`field_app_access.checkin_query_conditions`, plus a test pinned to this exact
two-company arrangement. The same will be needed for the step-3 doctypes
(`Alvoraa App Invite`, `Alvoraa App Consent`), which also link only Employee.

### 8.4 · State left behind

- `slice/013-mobile-app` at `3a45261` (five step-1 commits on local dev `d1fd9c6`).
  Not in local `dev`, not pushed.
- `test_site` carries the step-1 schema (migrated at `66a1b61`; `3a45261` adds no
  schema). Anyone running the main checkout's tests against test_site will see the new
  device columns; nothing on `dev` reads them, so nothing breaks.
- Container `hrlocal-013` removed. Bench claim cleared on the work board.
- One deadlock during the run was **mine**: a probe cleanup ran while the full suite
  was going and was chosen as the victim. The suite log has no deadlock. Lesson kept:
  no database probes while a suite runs, even tiny ones.
