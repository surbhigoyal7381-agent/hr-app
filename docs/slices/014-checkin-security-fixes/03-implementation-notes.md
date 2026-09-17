# 014 — Check-in security fixes — implementation notes

Built 2026-09-17 by the full-stack engineer, on the local machine only, in worktree
`.claude/worktrees/014-checkin-security-fixes`, branch `slice/014-checkin-security-fixes`.
Strategy: `00-impact-analysis.md`, approved by Surbhi 2026-09-17 with the recommended
answers.

**Nothing is pushed. Nothing touched the dev server or production.** Local `dev` now
holds the slice (see Update 2), and the tests ran on the local bench.

---

## Update 2 — 2026-09-17 evening: rebase, wildcard certificate, driver fix, tests run

**This section replaces section 0's points 1 and 2 and section 8's "owed" list, where
they differ.** Sections below it are kept as written, with commit hashes updated.

### What came in, and the rebase

- `git fetch origin`: the "010 group D + 012 push 1 + F1" release had reached
  `origin/dev` at `9138251`. The only commit on top of this branch's old base was
  `9138251` itself: docs only (four slice 010 files). I read its file list; nothing
  touches 014's files.
- `origin/main` (`2fc623c`) holds `d6613ea` "nginx: use alvoraa-wildcard cert", which is
  **not** on `dev`. The live server file matches main (pre-push checks, `00`).
- The branch was rebased onto `origin/dev` with no conflicts. **`d6613ea` was
  cherry-picked in before the nginx commit**, so 014's `deploy/nginx.conf` keeps the
  `alvoraa-wildcard` certificate paths.

### Commits now (oldest first)

| Commit | What |
|---|---|
| `98e1682` | Field check-in: keep photos, positions and names out of error logs |
| `a2ed577` | Blank field check-in data already copied into Error Logs |
| `a6b83ce` | Field check-in setup: same answer for a real and a made-up employee ID |
| `d6a7a31` | nginx: use alvoraa-wildcard cert (cherry-pick of main's `d6613ea`, unchanged) |
| `abb1bca` | nginx: pass Frappe only the real client address |
| `40b8b55` | Implementation notes (first version) |
| `b6c0c7c` | nginx check script: makes test certificates for whatever folders the file names. Without this, `nginx -t` failed on the wildcard path, which does not exist in the throwaway container |
| `6224f91` | **Driver location: only the assigned driver may post it** (scope addition) |
| `5838ba8` | Registration test: compare message words, not their random ids |
| `87e61e9` | Driver location test: the same fix |
| `18e9ed5` | Driver location: drop the dead `partner or ""` fallback |
| (this update) | Notes |

The two test fixes came from the first real run. Every message Frappe queues carries a
random `id`, so comparing the whole message as JSON could never be equal. The product
code was right; the tests compared the wrong thing.

### nginx — final file, checked again

- **Diff against `git show origin/main:deploy/nginx.conf`** (`git diff --stat origin/main
  HEAD -- deploy/nginx.conf`): **60 lines added, 12 removed.** The 12 removed lines are
  exactly the 10 `X-Forwarded-For $proxy_add_x_forwarded_for` lines and the 2
  `location = /api/method/login` lines. The 60 added lines are their replacements (10
  lines, plus 2 × (3 comment lines + the regex location)) and the Cloudflare block (18
  comment lines, 22 `set_real_ip_from`, `real_ip_header`, one blank). The certificate
  lines are identical to main's. **Nothing else differs.**
  - A plain `diff` against `git show` output lists every line, but only because the
    Windows working copy uses CRLF line endings. Git stores LF, as the server has.
- `python scripts/check_nginx_conf.py` → **OK**. On main's file → **FAIL** (10 forged-header
  lines, no Cloudflare lines, v1/v2 login paths unlimited on both hosts).
- `bash scripts/check_nginx_forwarded.sh deploy/nginx.conf` in throwaway `nginx:alpine`
  containers → **21 PASS, ALL PASSED**:
  - `nginx -t` ok, realip present
  - no forged address reaches the backend on either host, or on `/files/`, `/socket.io/`
    or pages
  - 11 forged values → 1 bucket
  - a forged `CF-Connecting-IP` is ignored
  - all three login paths answer 429 on both hosts
- On main's file (the live production file): **16 FAIL.**
- No test containers or networks left behind.
- The server's nginx is 1.31.5 with realip (K12, pre-push checks). This PC's image is
  1.31.2.

### Driver location fix (scope addition)

- **Where:** `alvoraa_portal/portal_api.py`, `update_driver_location`, plus a new
  `_driver_partner_for(user)` helper.
- **What was wrong:** any logged-in user could insert a Vehicle Tracking row (position,
  speed, heading, speeding alert) for any Delivery Order. The insert ignored permissions
  and nothing checked the caller.
- **Rule now:** the caller must be the Delivery Partner whose `primary_email` is the user.
  This is the same rule `get_portal_context` uses to recognise a driver, so the driver the
  portal serves is exactly the one allowed to post. The caller must also be the order's
  `assigned_to_partner`.
- **Everything else gets the same `PermissionError`** ("You can only share your location
  for a delivery assigned to you."), and nothing is written. That covers: another driver,
  a user who is not a driver, Administrator, Guest, an order with nobody assigned, and an
  order that does not exist. Because every refusal is identical, the answer does not
  reveal which orders exist.
- **Callers:** one, `www/driver-portal.html` `postLocation()`. It is called from real GPS
  (line 2113) and from the "Simulate GPS (Demo)" button (line 2196). The page is
  unchanged.
  - For the real driver, both still post.
  - **For an admin using the demo simulator on another driver's order, the post is now
    refused.** The page ignores errors on this call on purpose (`error:` is silent), so
    the admin sees the simulated marker move as before. No Vehicle Tracking row is saved.
    This is what the scope asked for.
- **Persona impact:** Driver (Delivery Partner user) — no change. Vendor — the location
  they read can no longer be faked by another user. HR Manager / System Manager — cannot
  write a driver's trail through this endpoint (the desk form is unchanged). Employee — no
  change.
- **NFR:** 2 extra single-row lookups per post (partner by email; the order's partner was
  already read). Security improves. No data exposure change. No `ignore_permissions`
  added.
- **Pin test:** `tests/test_driver_location_014.py`, 5 tests, all named
  `test_014_driver_location_*`. Delivery Order's `before_save` geocodes over the internet
  (Nominatim), so the fixture turns that off with `mock.patch` and the tests make no
  outside calls.
- **Found while doing it, not fixed (not in scope, needs a decision):** the rest of
  `portal_api.py` has the same gap. `get_vendor_orders(vendor_id)`,
  `get_driver_deliveries(partner_id)`, `driver_advance_status`, `submit_order_rating`,
  `get_all_vendors`, `get_all_partners`, `get_delivery_route` and
  `get_drivers_performance` take an ID from the caller and read or write with
  permissions ignored, with no ownership check. So does
  `controllers/delivery_assignment.update_gps_location` (any logged-in user can append a
  GPS point and trigger an "arriving soon" email). Suggest one follow-up slice for the
  driver and vendor portal APIs.

### Tests on the bench (`test_site`)

The bench was claimed on the board after `pgrep` showed it free.

| Run | Result |
|---|---|
| `bench --site test_site migrate` | rc 0. The patch `redact_field_checkin_error_logs` ran |
| `run-tests --module alvoraa_portal.tests.test_checkin_security_014` | First run: 13 tests, 1 failure (the random-id comparison, fixed in `5838ba8`). **Re-run: 13 tests, OK** |
| `run-tests --module alvoraa_portal.tests.test_driver_location_014` | First run: 5 tests, 1 failure (the same comparison, fixed in `87e61e9`). **Re-run: 5 tests, OK** |
| Full `alvoraa_portal` | 1,170 tests in two halves (557 + 613), 38 min. **Only the known 14 failures**: 3 errors in `test_leave_year`, 11 in `test_invoicing` (10 errors + 1 failure). Both 014 modules ran inside it and passed |
| Full `alvoraa_goals` | 18 tests, OK (2 skipped) |

One more commit came after the runs: `18e9ed5`, which drops a dead `partner or ""`
fallback in the same function (the check above it already refuses an order with nobody
assigned, and Vehicle Tracking needs the field). Python had already imported the module
when the suite started, so the running tests were unaffected; the 5 driver tests passed
again on the module run before it.

**Local `dev`** was fast-forwarded (`merge --ff-only`) to the branch after each fix.
**It now holds 014, which is not pushed. A push of local `dev` would carry 014, including
`deploy/nginx.conf`.**

### Still owed

1. **Pushing is Surbhi's decision**, at a quiet moment. First she clears the in-place edit
   in `/var/www/html/hr-app/deploy/nginx.conf` on the server (production wall — user
   only), so the deploy's checkout is clean. Just before the push, re-run
   `check_nginx_forwarded.sh` on the file being pushed.
2. A hand trace of `/checkin` and of the driver portal on `ppj.localhost`. It needs a
   migrate there, so ask first.
3. The open checks K3–K8 and K11 (section 8).
4. The follow-up for the rest of `portal_api.py` (above).
5. **Parallel work:** the `ci-fix-9138251` session may also edit `.github/workflows/ci.yml`
   (site config, test job). 014 adds one step to the lint job. If the two meet, keep both.

---

## 0. Read this first

1. **The Python tests have not run yet.** The bench only runs local `dev`, and two things
   keep this slice out of local `dev`: the release rule (no new commits on `dev` until
   "010 group D + 012 push 1" is on `origin/dev`), and slice 010's full test run, which
   had the bench all session. The test file is written and compiles. The wrapper's logic
   was checked with a stand-in for Frappe (section 6). **The real run is owed** (section 8).
2. **The nginx fix is proven on this PC.** In throwaway containers, the old file fails
   16 of 21 checks: forged addresses reach Frappe, 11 forged values give 11 rate-limit
   buckets, and the v1/v2 login paths have no limit. The new file passes all 21.
3. **New finding: nginx cannot fully limit logins.** Frappe logs in on **any** path when
   the request carries `cmd=login` (`frappe/auth.py`, `LoginManager.__init__`, installed
   v16.33.1). A path-based nginx limit cannot see that. The real brake is Frappe's own
   login lock (per user and per IP), which **this slice makes trustworthy**, because the
   IP can no longer be forged. It only works if System Settings "Allow Consecutive Login
   Attempts" is set on each tenant — a check for the user (K11).
4. **Deviations from the approved plan:** the nginx pin test is a CI script plus **one new
   step in `.github/workflows/ci.yml`**, not a Frappe test (section 2). The slice is based
   on local `dev`, not `origin/dev` (section 1). An unknown device secret now gets the
   "waiting for HR" answer (section 3, commit 3). Each is explained below.

---

## 1. Base and what else moved

- **Fetch at start and at the end:** `origin/dev` stayed at `c27fb56`. **Nothing came
  in.**
- **Base: local `dev` at `8a53522`, not `origin/dev`.** Why: the next `origin/dev` *is*
  local `dev` (the release train pushes it as one piece). Basing on it means the bench,
  which runs local `dev`, will run exactly this code on top of that release, and bringing
  the slice in later is a plain fast-forward. None of my files differ between `origin/dev`
  and local `dev` (`git diff --stat origin/dev dev` on all of them is empty), so nothing of
  010's or 012's is mixed into these commits. **Effect:** this branch cannot go to
  `origin/dev` before the release does. That was already the rule.
- **Other sessions' uncommitted files** in the main checkout (listed in `00` §1): none
  touched.
- **Conflicts:** none. No rebase was needed.
- **Work board:** row added for 014, with the files claimed. It now also names the one
  `ci.yml` step.
- **`00-impact-analysis.md` is not in these commits.** It sits untracked in the main
  checkout, where it was written and approved. Copying it into the worktree would break
  the "never copy files to sync" rule, and a tracked copy on this branch would block the
  later `merge --ff-only` (the same thing that once blocked slice 010). Commit it from the
  main checkout, by path, when the slice lands.

---

## 2. What was built, commit by commit

| # | Commit | Files | Mechanism | Why this one |
|---|---|---|---|---|
| 1 | `98e1682` (was 88c6dcf) Field check-in: keep photos, positions and names out of error logs | `alvoraa_portal/field_checkin.py` (new `_private_request`, `_log_server_error`, `_code_places`; decorator on `register_device`, `field_checkin`, `field_status`); new `tests/test_checkin_security_014.py` | **Extend**: a decorator in our own app | Frappe's field masking is hard-coded, and changing it means editing upstream code. A decorator that removes the fields and never lets an exception reach Frappe's handler is the only in-app way to keep the local variables out |
| 2 | `a2ed577` (was bc3c2b2) Blank field check-in data already copied into Error Logs | new `patches/v1_0/redact_field_checkin_error_logs.py`; one line at the end of `alvoraa_portal/patches.txt`; tests | **Build**: a one-time patch | Runs on every tenant at migrate, so nobody has to touch a server. It blanks the values and keeps the rows (user's decision 4) |
| 3 | `a6b83ce` (was ec1e479) Field check-in setup: same answer for a real and a made-up employee ID | `field_checkin.py` (`register_device`, `_device_from_token`, new `_refuse_as_pending`); tests | **Extend** | User's decision 7 |
| 4 | `abb1bca` (was ff32b69) nginx: pass Frappe only the real client address | `deploy/nginx.conf`; new `scripts/check_nginx_forwarded.sh`; new `scripts/check_nginx_conf.py`; `.github/workflows/ci.yml` (one step) | **Configure** | User's decisions 1, 2, 8 and 9 |
| 5 | (this file) | `docs/slices/014-checkin-security-fixes/03-implementation-notes.md` | — | — |

### Commit 1 — the log wrapper

`_private_request(*fields)` sits directly under `@frappe.whitelist(...)`, above the plan
gate and the rate limit.

- **On entry:** removes the named fields from `frappe.form_dict`. Frappe has already passed
  them to the function as arguments. After that, only logging reads `form_dict`: Error Log
  `metadata` and the `Form Dict:` line in `frappe.log`.
  - `field_checkin`: `photo, latitude, longitude, accuracy, captured_at`
  - `register_device`: `employee_id, device_label, platform`
  - `field_status`: none. It carries only `token`, which Frappe already hides. It still
    gets the wrapper, to keep names out of crash logs.
- **A refusal** (any exception with `http_status_code` below 500): rolls back, then sets
  the same status code and `exc_type` that Frappe's `report_error` would. It returns
  nothing. The sentence `frappe.throw` queued still goes out as `_server_messages`, so
  `www/field-checkin.html` behaves the same. This matters on dev, which runs developer
  mode and logs every refusal with local variables.
- **Anything else:** rolls back and writes one Error Log row:
  - title: `Field check-in: unexpected error in <endpoint>`
  - body: the class name and `file:line in function` for each frame, **no values, and not
    `str(exc)`**, because a database error can quote a value
  - then it clears queued messages and answers 500 with "Something went wrong on our side.
    Please try again in a minute."
  - if the Error Log insert itself fails, the same text goes to
    `frappe.logger("alvoraa_portal.field_checkin")`, which adds no request fields.
- **Why not catch and re-raise:** Frappe's own `frappe.call` frame holds the request
  arguments as `kwargs`. Any exception that climbs through it gets them printed
  (`frappe/__init__.py` `call`; `frappe/app.py:448` `log_error_snapshot`). Checked in the
  installed source, v16.33.1.
- **Side effect, fixed for free:** the three `frappe.log_error` calls in `_attach_photo`
  (rejected photo) no longer carry the photo or GPS in `metadata`.

### Commit 2 — redacting old copies

`execute()` finds Error Log rows where any of these match, 500 at a time:
- `metadata` like `%alvoraa_portal.field_checkin%`
- `error` like `%alvoraa_portal/field_checkin.py%`
- `method` like `Field check-in%`

For each row it:
- **`metadata`:** sets the values of `photo, latitude, longitude, accuracy, captured_at,
  employee_id, device_label, platform` in `form_dict` to `********`. If the metadata is
  not readable JSON, the whole field becomes `********`.
- **`error`:** replaces every variable line from `traceback_with_variables` with
  `name = ********`, and every deeper continuation line with `********`. Variable lines
  are indented six spaces; code lines are indented four. I checked that format against
  the installed library by running it on a made-up function in the bench container. That
  run did not touch any site.
- **Keeps** `method`, the `File "...", line N` lines, and the final exception line.
- Rewrites only what changed. A second run changes nothing. It logs a count only.

**Known limit:** the last line of a traceback (`SomeError: message`) is kept. If a
database error ever quoted a personal value there, it stays. The patch cannot know which
messages do.

### Commit 3 — `register_device` gives no ID away

- **Before:** only a real, active employee ID got a `token` in the reply. So the reply
  said which IDs exist.
- **Now:** every caller gets a secret. A made-up ID's secret is never stored.
- **The next call would have leaked it instead.** `field_status` answered an unknown secret
  "not set up" and a pending phone "waiting for HR". So `_device_from_token` now gives a
  well-formed but unknown secret **the same answer as a pending phone**.
- A missing or too-short secret still gets "not set up". That says nothing about any ID.
- **Behaviour change (deviation, tell the user):** a phone whose registration HR
  **deleted** now shows "Waiting for HR to approve this phone" instead of "This phone is
  not set up". That screen already has a "set up again" button, and HR knows what they
  deleted. A **blocked** phone still shows "blocked".
- **Left open:** timing. A real ID does one insert and a commit; a made-up one does not.
  The difference is a few milliseconds, and after commit 4 it can only be measured from one
  real address at 10 an hour. Accepted, not fixed.

### Commit 4 — nginx

- All 10 `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;` lines are now
  `$remote_addr`, in both server blocks. `X-Real-IP` was already `$remote_addr`.
- At the top of the file: 22 `set_real_ip_from` lines, one for each of Cloudflare's
  published ranges (15 IPv4 + 7 IPv6, from `cloudflare.com/ips-v4` and `/ips-v6`, read
  2026-09-17), and `real_ip_header CF-Connecting-IP;`.
  - They do nothing while DNS is grey (DNS only).
  - If the list goes stale, limits get stricter, not looser.
  - Check the list once a year; the comment in the file says so.
- `location = /api/method/login` is now `location ~ ^/api/(v1/|v2/)?method/login/?$` in
  both server blocks.
  - Frappe mounts the same routes under `/api/`, `/api/v1/` and `/api/v2/`
    (`frappe/api/__init__.py:94–96`), so the approval's "add v2" also needed v1.
  - A regex location wins over the plain `location /api/` prefix, so the login limit
    applies.
- **Deviation — how the pin test runs:** `deploy/` is not inside the app. The bench mounts
  only `hrms/`, `alvoraa_portal/` and `alvoraa_goals/`, and CI copies only those into the
  bench. A Frappe test could not find `nginx.conf` in either place. So:
  - the pin test is `scripts/check_nginx_conf.py`, a text check with no nginx needed;
  - **one step was added to CI's lint job**: "nginx never trusts a caller's address". This
    is the only change under `.github/`. The user can drop that step; then the pin runs
    only by hand.
- `scripts/check_nginx_forwarded.sh` is the behaviour test (section 6). It is run by hand
  before any push that changes `nginx.conf`.

---

## 3. Acceptance — each approved decision

| # | Decision (00, "Strategy approval") | How it is met | Status |
|---|---|---|---|
| 1 | Strategy as written | Commits 1, 2, 4 | Built. Python tests owed |
| 2 | One nginx commit for both server blocks | Commit 4 changes both | Done, checked in containers |
| 3 | Throwaway nginx containers on this PC | `scripts/check_nginx_forwarded.sh`; every container and the network are removed on exit (checked: none left) | Done |
| 4 | Blank the data, keep the rows | Commit 2 | Built. Test owed |
| 5 | Short runbook for server log files | Section 7 | Written |
| 6 | Dev keeps developer mode on | The wrapper answers refusals without raising, so developer mode has nothing to log (`test_014_refusal_in_developer_mode_leaks_nothing`) | Built. Test owed |
| 7 | Same answer for real and fake IDs | Commit 3 | Built. Test owed |
| 8 | `/api/v2/method/login` under the login limit | Commit 4, plus `/api/v1/…`. Proven: 429 on all three paths, both hosts | Done. **But see finding F7** |
| 9 | Cloudflare grey until the fix is live | Nothing to build. Reminder for the user | — |
| 10 | Nobody else editing these files | Board and fetch checked at start and end: no claims, nothing incoming | Done |

008 SEC-8 ("no personal data reaches any log, including Frappe's own") is met **for
field check-in**, once the owed tests pass. It is not met for logged-in endpoints — see
`00` §3.7, follow-up slice 015.

---

## 4. The seven dimensions, against the code actually written

| Dimension | Before → after | Verdict | Why |
|---|---|---|---|
| Performance | success path: 0 extra queries; refusal: 1 rollback (Frappe did the same); crash: rollback + 1 Error Log insert (Frappe did the same, plus a deferred insert). `register_device` with a made-up ID: one `token_urlsafe` call, no query. nginx: one CIDR match per request | **neutral** | Nothing on the hot path grows |
| Security | forged IP → fresh bucket (proven) → one bucket per real address (proven); Restrict-IP and login IP lock now see the real address; employee-ID check through `register_device` closed; v1/v2 login paths limited | **improves** | See F7: nginx still cannot limit `cmd=login` on other paths |
| Reliability | an unexpected error in a punch used to reach Frappe's handler; now it is rolled back and answered with a clear 500. **Risk:** a typing mistake in `nginx.conf` would take every site down — the container check ran green on the exact file | **improves**, with the nginx push risk stated | Rollback in section 9 |
| Scalability | Cloudflare-ready without collapsing all visitors into shared addresses | **improves** | — |
| Maintainability | ~90 lines of commented wrapper in one file, used 3 times; patch ~130 lines; two small scripts; one CI step; the Cloudflare list needs a yearly look | **neutral** | Everything is pinned by a named test or script |
| Data integrity | transaction handling matches Frappe's (rollback on failure; the endpoints' own mid-way commits unchanged); the patch edits log rows only, never business records, and a second run changes nothing | **neutral** | — |
| Compliance / privacy | photo, GPS, employee ID and name no longer reach Error Log or `frappe.log` from field check-in; old Error Log copies blanked; IPs in session and login records are true (CERT-In) | **improves** | Left over: log files (runbook), database backups, logged-in endpoints (slice 015) |

**Observability trade-off:** a crash log now says where, never with what. To debug one,
open the device or check-in named in the logs and reproduce it. That is the budget's rule
("log the document name").

**No visibility widened.** No new field in any list, report, export or API answer. The
`register_device` reply keeps the same keys it gave for a real ID before.

---

## 5. NFR notes

- **Queries:** see section 4. The patch reads 500 rows per page, plus one read and at most
  one write per matching row. The number of rows is bounded by Error Log retention, 14
  days by default.
- **Indexes added:** none.
- **Background jobs:** none added.
- **Where permissions are enforced:** unchanged. The three endpoints stay guest endpoints,
  proved by the device secret. No new `ignore_permissions`, so the CEILINGS table in
  `test_portal_security_010.py` is untouched.
- **Sensitive fields touched:** `photo`, `latitude`, `longitude`, `accuracy`,
  `captured_at`, `employee_id`, `employee_name` (via locals). All are now removed from
  logs; none newly exposed.
- **Fallbacks:** if the Error Log write fails, the same value-free text goes to the app
  logger.

---

## 6. Commands run and what they said

| Command | Result |
|---|---|
| `git fetch origin` (start and end) | `origin/dev` = `c27fb56` both times. Nothing incoming |
| `docker exec hrlocal-bench … git describe --tags` in `apps/frappe`; read `set_request_ip`, `handle_exception`, `get_error_metadata`, `sanitized_dict`, `LoginManager.__init__`, `frappe/api/__init__.py`, `api/v1.py`, `api/v2.py`, `utils/messages.py`, `utils/response.py` | **v16.33.1** (`988e54f`, 2026-09-08). Same code as the GitHub `version-16` reads in `00`. Read-only; no site used |
| `docker exec hrlocal-bench env/bin/python -` running `traceback_with_variables` on a made-up function | Confirmed the 6-space variable lines and 4-space code lines the patch relies on. No site used |
| `python -m py_compile` on every changed Python file | OK |
| `python scratchpad/wrapcheck.py` — the real `_private_request` source run against a stand-in for Frappe | PASS: success passes through and removes the fields; a refusal gives 417 + `ValidationError` + its sentence, with a rollback; a crash gives 500 + the generic sentence, and the log holds neither the name nor the photo. **Not a substitute for the Frappe tests** |
| Redaction helpers run against a stand-in | Sample row: values blanked, `File` line and exception line kept; second run changed nothing |
| `ruff check` (local ruff 0.15.4, `hrms/pyproject.toml`) on changed files | New code clean. 5 findings, all in lines that were already there (the file had 6 before) |
| `python scripts/check_app_integrity.py` | `app integrity: 580 checks — OK - all consistent`. The new patch exposes `execute()` |
| `python scripts/check_nginx_conf.py` | New file: **OK**. Old file: **FAIL**, 17 problems (10 forged-header lines, missing Cloudflare lines, v1/v2 login paths unlimited on both hosts) |
| `bash scripts/check_nginx_forwarded.sh <old file>` | `nginx -t` passes; **16 FAIL**: forged address reaches the backend 11/11 on both hosts and on `/files/`, `/socket.io/`, pages; 11 forged values give **11 buckets**; v1/v2 login paths answer 200 ×7 |
| `bash scripts/check_nginx_forwarded.sh deploy/nginx.conf` | **21 PASS, ALL PASSED**: `nginx -t` ok, no warnings; realip module present; no forged address reaches the backend; always one address; 11 forged values give **1 bucket**; a forged `CF-Connecting-IP` from a non-Cloudflare caller is ignored; `/api/method/login`, `/api/v1/method/login` and `/api/v2/method/login` all answer 429 on both hosts |
| `docker ps -a`, `docker network ls` after the runs | No `nginxcheck*` container or network left |
| `docker exec hrlocal-bench pgrep -af run-tests` (several times) | Slice 010's full `alvoraa_portal` run the whole time. **Bench not used by 014** |

The image used was the local `nginx:alpine`, **nginx 1.31.2**. The production container's
nginx version was not checked (K12).

**Not run:** `bench run-tests` for this slice (section 8). No hand trace of the field
check-in page. No migrate.

---

## 7. Runbook for the user — cleaning copies from server log files

**Do this only after commit 1 is deployed**, or new copies appear behind you. Agents do
not run these; production is your choice (CLAUDE.md §3). Nothing here prints a log line,
only file names and counts.

The copies are in each site's `logs/frappe.log*`, inside the `sites` volume, so they
survive deploys. The bench-level `logs/` inside the container is replaced on every deploy,
so it needs nothing.

```bash
# DEV (container devstack-backend-1). 1) which files, and how many matching lines
docker exec devstack-backend-1 bash -c \
  'cd /home/frappe/frappe-bench/sites && grep -c "alvoraa_portal.field_checkin" */logs/frappe.log* 2>/dev/null | grep -v ":0$"'

# 2) empty exactly those files. This also removes the other error lines in them.
#    Frappe rotates these at 100 KB x 20 files, so they hold only recent history anyway.
docker exec devstack-backend-1 bash -c \
  'cd /home/frappe/frappe-bench/sites && for f in $(grep -l "alvoraa_portal.field_checkin" */logs/frappe.log* 2>/dev/null); do : > "$f"; echo "emptied $f"; done'

# 3) check: step 1 again prints nothing.

# PRODUCTION - the same three steps with compose-backend-1, only if you decide to.
```

If you would rather keep the other lines, leave the files alone. With commit 1 live, no
new copies are written, and rotation pushes the old ones out.

**Cannot be cleaned:** Error Log rows inside database backups taken before the patch ran.
They age out as backups are rotated.

---

## 8. Owed, and checks still to run

**Owed before anyone asks to push (engineer or test engineer):**

1. After "010 group D + 012 push 1" is on `origin/dev`: fetch, read what came in, rebase
   this branch, `git -C C:/Surbhi-Git/hr-app merge --ff-only slice/014-checkin-security-fixes`.
2. When the board and `pgrep` show the bench free: claim it on the board, then
   `bench --site test_site migrate` (runs the new patch on `test_site`), then
   `bench --site test_site run-tests --module alvoraa_portal.tests.test_checkin_security_014`
   (13 tests), then the whole `alvoraa_portal` suite (expect only the known 14 failures)
   and `alvoraa_goals`. Clear the board after.
3. A hand trace of `/checkin` on `ppj.localhost`: register a real ID and a made-up ID
   (same screen), HR activates the real one, punch, a refused punch (same message as
   before), a forced crash (the "Something went wrong" screen). `ppj.localhost` needs its
   own migrate for the patch, so ask the user first.
4. Before the push that carries commit 4: run `bash scripts/check_nginx_forwarded.sh`
   again on the exact file being pushed, at a quiet moment, on the user's word.

**Checks from `00` §10, updated:**

| # | Check | State |
|---|---|---|
| K1 | Bench Frappe version and the functions read | **Done**: v16.33.1, identical |
| K2 | Live server `nginx.conf` equals git | Open — user |
| K3 | `developer_mode` on each dev and production site | Open. Less urgent now: the wrapper covers field check-in either way |
| K4 | Error Log retention per tenant | Open |
| K5 | Count of field check-in Error Log rows per tenant | Open. The patch cleans them whatever the count |
| K6 | Any user with Restrict IP set | Open |
| K7 | Sentry or telemetry set on dev or production | Open — user |
| K8 | Any Cloudflare record proxied (orange) today | Open — user. **Keep grey until commit 4 is live** |
| K9 | realip module in `nginx:alpine` | **Done** locally (nginx 1.31.2). See K12 |
| K10 | Does `/api/v2/method/login` log in? | **Answered by reading**: the path alone does not log in. `LoginManager` logs in when `path == "/api/method/login"` **or** `form_dict.cmd == "login"` on any path. Hence F7 |
| K11 (new) | System Settings "Allow Consecutive Login Attempts" set on each tenant | Open — this is the login brute-force brake that works on every path |
| K12 (new) | `docker exec compose-nginx-1 nginx -V` on the server shows `--with-http_realip_module` | Open — user, **before** the push. If it is missing, nginx will refuse the file and every site goes down. Every official `nginx:alpine` build has it, but the server's image was not checked |

---

## 9. Rollout and rollback reminders (not done; the user decides)

- Commits 1–3 are normal app code. They go out with a normal dev deploy and migrate. The
  patch runs at migrate on every dev tenant.
- **Commit 4 changes the nginx that also serves production, the moment it reaches `dev`.**
  - Push at a quiet moment, on the user's word, after K12.
  - After the deploy: dev answers; production answers `200` (the user checks);
    `docker logs --tail 20 compose-nginx-1` shows no `emerg`.
  - Live proof on dev, on the user's word: 11 `register_device` calls with 11 forged
    `X-Forwarded-For` values and consent `0` (nothing is created). The 11th answers 429.
- **Rollback:**
  - `git revert abb1bca`, then push on the user's word.
  - If nginx will not start: only the user can act, in `/var/www/html/hr-app`. Restore
    the previous `deploy/nginx.conf` from git, run `docker restart compose-nginx-1`, then
    check `docker logs`.
  - Commits 1–3 revert on their own. The redaction patch cannot be undone, and does not
    need to be.

---

## 10. Findings and gaps — declared

| # | What | Suggest |
|---|---|---|
| F7 (new) | Frappe logs in on any path when the request has `cmd=login`, so no nginx path limit can cover every login | Make sure K11 is set on every tenant. Optionally an nginx `map` on `$arg_cmd` covers the query-string form, but not a form body. Not done: not approved, and it only half-helps |
| Gap | Python tests not run (section 8) | Owed |
| Gap | The traceback's last line is kept by the patch | Accepted; stated in commit 2 |
| Gap | Timing difference between a real and a made-up ID in `register_device` | Accepted; stated in commit 3 |
| Gap | Logged-in endpoints (`do_checkin`, leave reason, attendance explanations, `upload_base64_file`) have the same Frappe logging exposure; dev's developer mode makes every refusal on them logged | Slice 015. The wrapper can move to a shared module when a second file needs it |
| Gap | Frappe's argument-type check (added by `@frappe.whitelist`) sits outside the wrapper. It could log in developer mode if these functions ever get type hints | They have none today. Adding hints later should move the wrapper or skip hints on these three |
| Note for slice 013 | The mobile app's new join endpoints should use `_private_request` and name their token field with `token` in it (013 OPS-20). `_device_from_token` now answers unknown secrets as "waiting"; 013's new statuses (OPS-28) must keep "only Active passes" | For 013's spec |
