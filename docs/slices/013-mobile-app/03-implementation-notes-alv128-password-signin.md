# ALV-128 · Sign in to the field app with email and password — implementation notes

Built locally on 25 Sep 2026, on branch `slice/alv-128-password-signin` (from
`origin/dev` 0d51cac), in its own worktree. **Nothing pushed. No pull request. No
server, no tenant, no `docker cp`.** Tested in a throwaway container `hrlocal-128`
on its own site `test128` with its own Redis (`hrlocal-128-redis`); `hrlocal-bench`
and `hrlocal-wa042` were not used.

The strategy was approved by the user on 25 Sep 2026 (brought forward from ALV-128).

> **Read the "Review fixes (26 Sep 2026)" section at the end first.** It changes
> several things described below: the route switches now stop new joins only;
> the per-address limit is 500; the per-email limit is now per account; and the
> gaps list is mostly closed.

---

## What it does, in one paragraph

An employee whose Employee record is linked to a login (`Employee.user_id`) opens
the app, types a company code once (`sargam`), their work email and password, and
is signed in. If two-factor sign-in is on for them, the app asks for the one-time
code. They read the notice, tick, and land on the existing Welcome and Attendance
screens. From then on the phone is an ordinary app phone: it holds a device secret
and uses the same `field_status` / `field_checkin` calls, photo, GPS and 50 m rule
as a phone that joined with a QR code. "I have a joining code" still leads to the
QR flow, unchanged.

---

## The user's decisions, and where each one lives

| Decision (25 Sep 2026) | Where | Test that pins it |
|---|---|---|
| Any active employee with a login may sign in; the designation list binds QR phones only | `field_checkin._refuse_unless_app_phone_is_eligible` | `test_128_the_designation_list_binds_code_phones_only` |
| Master switch and plan gate apply to both ways in | `field_app_settings.refuse_unless_password_signin_on`, `@requires_field_app_plan` | `test_128_the_master_switch_stops_both_ways`, `test_128_the_plan_gate_still_applies` |
| Sign-in leads; "I have a joining code" is second; company code typed once and remembered | `web/index.html` (`signin` screen), `signin.js`, `signin-core.js` | node `signin.test.js`; browser run below |
| Company code builds `https://<code>.alvoraa.co`; `.dev` only in pilot/debug; same allow-list as the QR | `host-check.js` `originForCompanyCode` + shared `hostIsAllowed` | node `signin.test.js` (hostile inputs) + existing `host-check.test.js` |
| Frappe's own password check, lockout and two-factor | `field_app_join._check_password` (`LoginManager.authenticate`), `_start_second_step` (`authenticate_for_2factor`), `confirm_sign_in_code` (`confirm_otp_token`) | `test_128_frappe_lockout_is_respected`, `test_128_two_factor_...` |
| The app never stores the password | `signin.js` empties the box as soon as the request is sent; nothing writes it | browser run: `storedValuesHavePassword: false`, `localStorageHasPassword: false` |
| New HR Settings switch, default ON, ON for existing sites | `alvoraa_app_password_signin` (Check, default 1), seeded by `after_migrate` | `test_128_the_installer_seeds_both_ways_on_and_never_turns_one_back_on` |
| Matching switch for the code way; never both off | `alvoraa_app_code_join` + `validate_hr_settings` | `test_128_hr_settings_refuses_both_ways_off` |
| A new phone replaces the old one, no HR approval | shared `_set_up_phone` (both ways) | `test_128_a_new_sign_in_replaces_the_old_phone`, `test_128_a_code_join_replaces_a_password_phone_too` |
| Blocking ends access; disabling the login stops the phone | User `on_update` hook `block_phones_for_disabled_login` + a check on every call | `test_128_disabling_the_user_blocks_the_password_phone`, `test_128_a_disable_that_skipped_the_hook_still_stops_the_phone` |

---

## What changed, file by file

### Server (`alvoraa_portal`)

| File | Change | Mechanism and why |
|---|---|---|
| `field_app_join.py` | **Refactor:** the part of `join_with_code` that makes the phone, replaces the old one and handles "old secret belongs to someone else" moved, unchanged, into `_set_up_phone()`, plus three tiny helpers (`_record_agreement`, `_tell_hr_one_phone_two_people`, `_joined_answer`). `join_with_code` calls them. **New:** `sign_in_with_password` and `confirm_sign_in_code` (guest, POST) and their helpers. `_phones_locked` now settles *either* kind of app phone. | Extend. One code path for both ways in, as asked — no copy. Lock order unchanged: Employee → (codes, QR only) → phones. |
| `field_checkin.py` | `_private_request` now always strips `password`, `pwd`, `otp` from `form_dict`, whatever the endpoint names. `_refuse_unless_app_phone_is_eligible`: password phones answer to the master switch + password switch + "is the login still enabled"; QR phones as before. The notice gate, the "accuracy required" rule and "no workplace coordinates" now apply to both app ways (`APP_JOIN_METHODS`). | Extend. |
| `field_app_settings.py` | Two new HR Settings Check fields (`alvoraa_app_code_join`, `alvoraa_app_password_signin`), both default 1 and seeded ON by `after_migrate` where never stored. `settings()` returns `code_join` / `password_signin`. `refuse_unless_eligible` (the QR check) now also refuses `JOIN_CODE_OFF`. New `refuse_unless_password_signin_on`. `validate_hr_settings`: both off is refused on every save; turning either off needs a reason (like the master switch). History wording covers the two switches. Active-phone count covers both ways. | Configure (custom fields on HR Settings, per CLAUDE.md §4) + extend. |
| `field_app_errors.py` | Nine codes **added** (none renamed): `SIGN_IN_FAILED` 401, `ACCOUNT_LOCKED` 429 (`retry_after_s`), `PASSWORD_EXPIRED` 403, `SIGN_IN_NOT_ALLOWED` 403, `OTP_WRONG` 401, `OTP_EXPIRED` 410, `NO_EMPLOYEE_RECORD` 403, `PASSWORD_SIGNIN_OFF` 403, `JOIN_CODE_OFF` 403. | Extend the frozen table (add-only rule). |
| `field_app_limits.py` | `SIGNIN_KEY` / `OTP_KEY` (hashed email / hashed one-time id); `_limited` lower-cases an email before hashing; new `_limited_by_address(limit)` (per caller address, Frappe's limiter, answered as `TOO_MANY_TRIES`). | Extend. |
| `field_app_device.py` | `block_phones_for_disabled_login` — User `on_update`: a disabled login blocks its password phones (Blocked, reason "Login disabled", secret retired). QR phones untouched. | Hook (`doc_events`). |
| `field_app_desk.py` | "Stopped" is worked out per way in; a person off the designation list with a password phone shows as **Joined**, not "not a field worker". `BLOCK_REASONS` gains "Login disabled". | Extend. |
| `hooks.py` | One line added at the end of `User.on_update`. | Hot file: one entry, commented. |
| `Alvoraa Field Device` JSON + controller | `join_method` option `App password sign-in`; `block_reason` option `Login disabled`; constants `JOIN_WEB/JOIN_QR/JOIN_PASSWORD/APP_JOIN_METHODS`; the "switched on by the app, not from here" rule covers both app ways. | DocType JSON (one Select option each). |
| `public/js/employee_field_app.js` | The Employee form says "by signing in with their email and password" for such a phone. | Desk wording. |
| `public/js/hr_settings_field_app.js` | The form asks for a reason when either way in is turned off, and says "keep one way in" before the server does. | Desk wording; the server still enforces. |
| `tests/test_field_app_password_signin_128.py` | **New**, 35 tests. | |
| `tests/test_field_app_step2_013.py` | One assertion updated: the exact `settings()` dict now has the two new keys. | Expected change. |

### Client (`mobile/field-app`)

| File | Change |
|---|---|
| `web/index.html` | New first screen `signin` (company code, work email, password, labels above inputs, errors in `role="alert"`, "Code for HR: …"); `signinOtp`; `signingIn`; `signinNotice`. The QR `first` screen keeps its words and gains "Sign in with email and password instead". |
| `web/js/signin-core.js` | **New**, pure: `checkForm`, `checkOtp`, `messageFor` (plain sentence per code), remembering the company code (localStorage, never the email or password). |
| `web/js/signin.js` | **New**, DOM only: the flow above. Password box emptied as soon as the request is sent. Secret + origin saved exactly as `join.js` does, then notice → `acknowledge_notice` → Welcome. |
| `web/js/host-check.js` | Host rule moved into `hostIsAllowed()`, shared by the QR link and the new `originForCompanyCode()`. Behaviour for QR links unchanged (its 81-line test still passes). |
| `web/js/api.js` | `signInWithPassword`, `confirmSignInCode` (both send `agreed: 0`). |
| `web/js/join.js` | `AlvoraaJoin.start()` now opens sign-in; `startQr()` opens the QR screen. Nothing else changed. |
| `web/css/app.css` | Field styles: 52 px inputs, visible focus. |
| `web/js/app-version.js`, `android/app/build.gradle` | **0.2.0**, versionCode 20000 (a new feature → minor number). `MIN_APP_VERSION` stays **0.1.0**; `releases.json` untouched (no store release). |
| `test/signin.test.js` | **New**, 17 tests. `test/check-versions.test.js`: expected version 0.2.0. |

---

## Decisions I made where the brief left room (please check)

1. **The password is sent once; the notice comes after.** The app signs in with
   `agreed=0`; the phone is created in "Consent not given"; the app shows the notice
   from the sign-in answer and calls the existing `acknowledge_notice`, which makes
   it Active. This is the path a QR phone already takes after "Not now". The
   alternative — notice first, then sign in with `agreed=1` — would mean holding the
   password in memory while the person reads, and asking for a two-factor code
   twice. The server still accepts `agreed=1` + the current notice version.
2. **Two-factor step never re-checks or caches the password.** Frappe's website
   caches the password in Redis beside the one-time id for up to 5 minutes; we hand
   Frappe an empty string instead (tested). The second step proves the one-time id
   and the code, as Frappe's own second step does. The id works once (we delete it).
3. **Password phones that lose their switch are refused with
   `PASSWORD_SIGNIN_OFF`, not blocked.** Same as the master switch: the phone keeps
   its secret and works again when HR turns the switch back on. Code phones get
   `JOIN_CODE_OFF` the same way.
4. **Before the migrate.** The two switches are read straight from `Singles`, not
   with `get_single_value`, because that throws for a field that does not exist yet
   and the fail-closed rule would then switch the *whole app* off for the length of
   a deploy. With nothing stored, the code way reads ON (how it worked before) and
   the password way reads OFF (fail closed) until `after_migrate` seeds it ON.
5. **No `patches.txt` line.** The existing `after_migrate` seeding loop sets both
   switches ON where no value was ever stored — that is exactly the one-time patch
   the brief asked for, it also runs on `bench install-app`, and it never turns a
   switch back on after a tenant turned it off (tested).
6. **Which answers are the same.** Unknown email, wrong password and disabled login
   all get `SIGN_IN_FAILED` with the same words (tested byte for byte). A login that
   is right but has no employee record gets `NO_EMPLOYEE_RECORD`; an employee who has
   left gets `EMPLOYEE_NOT_ACTIVE` — these only happen after a correct password, so
   they tell nobody anything they could not already see on the website.
7. **Lockout words.** `ACCOUNT_LOCKED` carries `retry_after_s` from System Settings.
   Frappe's own lockout message also reveals the lock; this is the same.
8. **Rate limits.** 10 an hour per email (hashed), 100 an hour per caller address,
   5 an hour per one-time id — on top of Frappe's lockout. The per-address limit is
   the only per-IP limit on an app endpoint besides `register_device`; see the gap
   below about a depot signing everybody in on day one.
9. **The disabled-login check runs on every call** (one primary-key read of `User`)
   as well as through the hook, so a login disabled by a script or `db.set_value`
   still stops the phone. It answers `DEVICE_BLOCKED` — an existing app screen.
10. **Block reason "Login disabled"** was added to the phone record's list, and so
   also appears in HR's block dialog (the list and the field are pinned together by
   an existing test). Harmless, and accurate if HR chooses it.
11. **`activated_by` on a password phone is the login itself** — the record of who
   allowed the phone ("the person, by their own password"), and how the User hook
   finds it.

---

## Tests and checks — what I actually ran

All on `test128` in `hrlocal-128`, one module at a time. `bench run-tests` prints two
"Ran" lines for some modules (two test classes groups); both are counted.

| Command | Result |
|---|---|
| `run-tests --module alvoraa_portal.tests.test_field_app_password_signin_128` | **35 tests, OK** |
| `…test_field_app_step1_013` | 15 + 13 tests, OK |
| `…test_field_app_step2_013` | 27 + 7 tests, OK (the first run failed on the exact `settings()` dict; the assertion was updated for the two new keys) |
| `…test_field_app_step3_013` | 41 + 9 tests, OK |
| `…test_field_app_step4_013` | 33 tests, OK |
| `…test_field_app_step5_013` | 28 + 3 tests, OK |
| `…test_field_app_step6_013` | 1 + 27 tests, OK (includes the 400-phones and privacy-scan tests) |
| `…test_field_app_permissions_013`, `test_checkin_location` | 9 and 9 tests, OK |
| `…test_checkin_security_014` | 14 + 2 tests, OK |
| `…test_portal_module_gate_016` | 17 tests, OK |
| **Total** | **290 tests, 0 failures** — the final run, all after the last code change |
| `python scripts/check_app_integrity.py` | 638 checks, OK |
| `python scripts/check_min_app_version.py` (+ `--self-test`) | OK, floor 0.1.0; self-test OK |
| `python scripts/check_api_paths.py --max 2` | OK (2 known, within tolerance) |
| `node scripts/check_undefined_js.js`, `check_no_demo_passwords.py`, `check_tracked_keys.py` | OK |
| `ruff check <changed .py files> --config hrms/pyproject.toml` (0.6.9, as CI) | All checks passed |
| `node --test "test/*.test.js"` (mobile/field-app) | 132 tests: 130 pass, 2 fail — **both are the Windows CRLF trap** on the three vendored files (hashes match the pins exactly once CR is stripped). On an LF copy, `check_app.mjs` says "OK: app config, dependencies and bundled files pass". |
| `node scripts/check_versions.mjs` | OK: 0.2.0 / 20000 |

**The screens in a real browser.** No Android SDK here, so no APK. Instead the real
`web/` files were served locally and driven in headless Chrome with the native
storage and the network stubbed (scratch harness, not committed). What it proved:
the app opens on sign-in; a bad company code is refused with no network call; a
wrong password shows the plain sentence and "Code for HR: SIGN_IN_FAILED" and
empties the password box; the call goes to
`https://sargam.alvoraa.co/api/method/alvoraa_portal.field_app_join.sign_in_with_password`
with the password only in the POST body; two-factor shows the code step, a wrong
code stays there, the right one moves on and sends no password; the secret and the
company are stored, the password is not (checked in both stores); the notice
refuses to finish without the tick; agreeing calls `acknowledge_notice` and shows
"Welcome, Ravi. This phone is set up."; "I have a joining code" opens the QR screen
and its new link comes back; the company code is remembered.

---

## Non-functional check, against the code as written

| Dimension | Verdict | Why |
|---|---|---|
| Performance | neutral | Sign-in: Frappe's own password check plus ~6 indexed reads and the same writes a QR join makes. Every existing call on a password phone adds one primary-key read of `User`; QR and web phones add nothing. The settings read went from 2 to 3 queries (one `Singles` read for both new switches). |
| Security | improves (with one trade-off) | Password checked only by Frappe (lockout, disabled logins, IP and hour limits, two-factor); one answer for unknown email and wrong password; password stripped from every request log and never cached; three rate limits; no web session. Trade-off: a login is now also a way in to the app, so a leaked website password can set up a phone — the same password already opens the website. |
| Reliability | neutral | Same locked, all-or-nothing save as the QR join. Crash path logs a place, no values (tested). A deploy's migrate window can no longer switch the whole app off. |
| Scalability | neutral, one watch item | 100 sign-ins an hour per address; see the gap below for a depot's first day. |
| Maintainability | improves | One `_set_up_phone` for both ways in; `APP_JOIN_METHODS` replaces five scattered `== "App QR code"` checks. |
| Data integrity | neutral | One live app phone per person across both ways (tested both directions). Disabled logins stop their phones through the same final Blocked state with the secret retired. |
| Compliance / privacy | neutral | Same notice, same acknowledgement record. The rate-limit keys hold a hash of the email, never the address (tested). The app stores the company code (not personal) in plain storage and the device secret in the Keystore, as before. |

---

## Not done, and known gaps

- **No APK built** — there is no Android SDK/Gradle toolchain in this session. The
  `web/` bundle is proven in a browser as above; a debug build on a real phone is
  still needed before pilot. *(temporary debt — removed by the first device build)*
- **The 2 CRLF node failures** are the working copy, not the code (committed blobs
  are LF). *(acceptable — known trap)*
- **App closed on the notice screen.** The phone already holds its secret in
  "Consent not given"; on the next open the Attendance flow asks for the notice
  with its "The notice has changed" heading, which is slightly wrong wording for a
  first agreement. *(acceptable simplification)*
- **A depot signing 100+ people in within one hour from one Wi-Fi** hits the
  per-address limit; the rest wait up to an hour. Frappe's own per-address lockout
  counts only wrong passwords. If a first-day roll-out is planned, raise the number
  in `sign_in_with_password` or roll out in batches. *(intentional trade-off — ask
  the user)*
- **The desk has no special words for `JOIN_CODE_OFF`** when HR presses "Invite" with
  the code way off: the refusal code comes back and the form shows its generic
  message. *(temporary debt — small copy change in `employee_field_app.js`)*
- **Unlinking the login from the Employee record** (changing `user_id`) does not stop
  a password phone; disabling the login does. *(intentional — the phone belongs to
  the employee; ask if HR expects otherwise)*
- **"Remove this phone" still says "To use the app again, you need a new code from
  HR."** That is the approved wording (01b), but a person with a login can now just
  sign in again. Suggested: "To use the app again, sign in again, or ask HR for a new
  code." Not changed without your word. *(question for the user)*
- **My HR tab: not in scope.** The same device secret and phone record can later
  unlock it — a new token endpoint checks `_device_from_token` as `field_status`
  does; nothing here needs to change for that.

## What else moved while I worked

`origin/dev` did not move past 0d51cac during the build (checked before commit).
The main checkout holds another session's uncommitted files under
`mobile/field-app/android/` (gradle files, new `.kts` files, `.idea/`) — not
touched; this branch changes `android/app/build.gradle` only (versionName and
versionCode), which that session has not modified.

---

## Review fixes (26 Sep 2026)

The code review blocked on one P1; the security review passed with conditions.
The user approved all the fixes below on 26 Sep 2026. They are new commits on the
same branch; the three earlier commits were not rewritten. `origin/dev` had not
moved (still 0d51cac), so nothing came in.

### P1 — the two-factor step could cross tenants (fixed)

Frappe writes its two-factor keys (`<tmp_id>_usr`, `_otp_secret`, …) into Redis
with **no site prefix**, and one Redis serves every tenant on the bench. Because
the second step no longer re-checks the password, an id made on tenant A could
be confirmed on tenant B. Now:

- `_start_second_step` also writes `alvoraa_app_2fa:<tmp_id>` → user through
  `frappe.cache.set_value`, which puts **this site's database name** in front
  (5 minutes).
- `confirm_sign_in_code` takes the user **only** from that key; missing →
  `OTP_EXPIRED`. The key is deleted on success.
- This also means an id made by the website's own login is never accepted here.

Tests: an id whose `_usr` and secret exist but that this site never marked →
`OTP_EXPIRED`; a marker written under another site's prefix → `OTP_EXPIRED`; the
real marker is prefixed with this site's name and is gone after use.

### Security requirements added (SEC-26 to SEC-31)

| Item | What was built | Test |
|---|---|---|
| **SEC-26** a password change blocks the login's password phones | Two doors, because Frappe has two: (1) a new password set on the User form (HR or the person) — the existing User `on_update` hook reads Frappe's private `_User__new_password`; (2) the website's "forgot password" and change-password page (`frappe.core.doctype.user.user.update_password`), which writes the password **without saving the User** — wrapped through `override_whitelisted_methods` in `hooks.py`. Frappe's function does all the work; ours finds the user first (reset key or signed-in user) and blocks only after Frappe succeeded. Reason "Password changed". | User-form change → next punch `DEVICE_BLOCKED`; forgot-password reset with a real key → blocked; a wrong key (410) → nothing blocked |
| **SEC-27** a sign-in that replaces the same person's phone emails them | `frappe.sendmail` (Email Queue, `delayed=True`) to the login: "A new phone signed in to the Alvoraa attendance app as you… If this was not you, tell HR and change your password." Plus an Info comment on the new phone's timeline. Not sent for a first-ever phone. Password sign-in only. | Email Queue row with the right recipient and words; none for the first phone; the timeline comment |
| **SEC-28** Employee.user_id ≠ the phone's login → refused; unlinking blocks | Every call on a password phone checks it (`LOGIN_UNLINKED`, 403 — new code). An Employee `on_update` hook blocks, reason "Login unlinked", when `user_id` changes. This answers the user's question 3. | Change the link → blocked; unlink with the hook skipped → `LOGIN_UNLINKED`; a save that does not change the link blocks nothing |
| **SEC-29** per-account limit on the account Frappe finds | The pre-lookup per-typed-text limit is gone. `_count_account_try` asks Frappe's `User.find_by_credentials` (no password check) which login the typed text finds, and counts 10 an hour on a hash of that login's name; text that finds nobody is counted on itself. | Capitals, spaces, an "ä" and a "ŵ" all find the same login and share one count of 10; the key holds a hash |
| **SEC-30** `loggingBehavior: "none"` | Set in `capacitor.config.json`; `check_app.mjs` now fails a config without it. | `check-app.test.js`: missing or "debug" fails |
| **SEC-31** Activity Log per sign-in | `add_authentication_log("Phone app sign-in (<model>, <phone record>)", user, operation="Login")`. Activity Log fills in the caller's address itself. No session is made. | One row, with the address and the model; session user still Guest |

### The user's answers, and what changed

1. **Per-address limit 500 an hour** (was 100), on both sign-in endpoints. Pinned
   by a test.
2. **The route switches stop NEW joins only.** Phones that already joined keep
   working; HR blocks one phone with the existing block action, or stops everyone
   with the master switch. `PASSWORD_SIGNIN_OFF` is asked only by the sign-in
   endpoints; `JOIN_CODE_OFF` only by `check_code`, `join_with_code` and
   `make_code`. The punch and start screen ask only the master switch (plus the
   designation list for code phones). Field help texts and the reason help text
   now say so. The desk's "Stopped" label follows the same rule. Decision 3 in the
   list above is replaced by this.
3. **Unlinking a login stops the phone** — SEC-28.
4. **Invite pressed while codes are off** → "Joining codes are switched off in HR
   Settings." (server sentence and the Employee form's own wording).
5. **First-time notice.** A phone closed on the first notice now reopens on
   "Before you start / Please read this and agree before your first check-in",
   with no "What is new" line. The sign is an empty notice cache (it is written
   only once the person agrees). One side effect: a phone whose app storage was
   cleared also sees the first-time heading for a real notice change — harmless.
6. **"Remove this phone"** now says "To use the app again, sign in again, or ask
   HR for a new code."
7. **Per-network lock words.** When Frappe's lock is on the caller's address, not
   the account, the answer is the new code `NETWORK_LOCKED` with "Too many sign-in
   attempts from this network. Try again later." — it never says "your account".
   Tested both ways (account lock from four networks; network lock from failures
   on other emails).

New block reasons on the phone record: "Password changed", "Login unlinked" (they
also appear in HR's block list, which is pinned to the field). Two new error codes,
added only: `NETWORK_LOCKED` (429), `LOGIN_UNLINKED` (403). The app shows
`LOGIN_UNLINKED` as "Please sign in again" with the Remove button.

### Proof, after the fixes

All in `hrlocal-128` / `test128`, one module at a time. (Docker Desktop was not
running when this session started; I started it, which brought the shared
`hrlocal-*` containers back up as they were. `test128`'s database user was tied
to the container's old address, so I let that one user connect from any address
on the private Docker network. No other site's user was touched.)

| Run | Result |
|---|---|
| `test_field_app_password_signin_128` | **48 tests, OK** (was 35) |
| Neighbours: steps 1–6, permissions, check-in location, check-in security 014, module gate 016 | **255 tests, OK** |
| **Total** | **303 tests, 0 failures** |

- The first neighbour run failed once: `test_016_no_bare_email_address_is_hardcoded`
  found an example address I had written in a comment. Reworded; module 016 and
  the new suite were run again after it and pass.
- `check_app_integrity.py` OK; `check_api_paths.py --max 2` OK; `check_min_app_version.py`
  OK; `check_no_demo_passwords.py` and `check_tracked_keys.py` OK; ruff 0.6.9 with
  the CI config: all checks passed on the changed files.
- App: 134 node tests. In the worktree 132 pass; the 2 failures are the known
  Windows line-ending trap on the vendored files. On a copy with LF line endings
  those pass and `check_app.mjs` says OK (that copy lacks the two build-type
  override files, so its 3 build-type tests cannot run there — they pass in the
  worktree). `check_versions.mjs` OK.
- **Browser, headless Chrome, stubbed storage and network:** the whole sign-in
  path from before still behaves the same (same 11 steps). New: a phone that holds
  a secret but never agreed reopens on "Before you start", with no "What is new";
  after one agreement, a changed notice still says "The notice has changed"; a
  network lock shows the neutral sentence and "Code for HR: NETWORK_LOCKED"; the
  Remove screen shows the new wording.

### Still not done

- **No APK** — no Android SDK here. A debug build on a real phone is still needed.
- **SEC-26 blocks on a password *change*, not on a reset *request*.** Pressing
  "Forgot password" only emails a link; the phone stops when the new password is
  actually set. A password changed by a script with `frappe.utils.password.update_password`
  (not through the User form or the website) does not fire either door.
- The desk section has no special state for "codes are switched off"; the Invite
  dialog says so when pressed.
