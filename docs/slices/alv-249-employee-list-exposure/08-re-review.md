# ALV-249 · Re-review after round 2 (request guard, sign-in sync, narrower rollback)

**Verdict: SHIP WITH FIXES.** The request guard is sound. I could not find a request path
that gets past it, and nothing shipped with Frappe, ERPNext or Frappe HR depends on the two
words it drops. There are two P2 items to settle before the production run. Neither one
blocks a push to dev:

1. **The new rollback cannot fully undo the change.** It removes only the rows `run_once`
   added. Rows that the sign-in hook and the save hooks add stay behind, even after the
   code is reverted.
2. **The rule still reaches people with unusual roles before anyone has read the "check
   by hand" list.** The new sign-in hook makes this wider: it now reaches every staff
   member the first time they sign in after the deploy.

Reviewed 31 Oct 2026 on `slice/alv-249-employee-list-exposure`: 6 commits on `origin/dev`
81be44a4, all by `surbhigoyal7381-agent`, with no merge commits. I fetched `origin/dev`
first and it had not moved. Since my last review (d3afcaa5), one commit from another session
came in from dev: **81be44a4 ALV-259**, which touches `attendance_correction.py` and adds
`test_team_scope_259.py`. It scopes the team attendance page for HR through Company and
Branch rows. It does not touch Employee own-record rows, so it does not interact with this
slice (Proven, I read the diff). I did not edit any source file. This is advice. **Surbhi
decides.**

## What I ran, and what I could not

| What | Result | Label |
|---|---|---|
| Container code is the same as the worktree (md5 of `request_guard.py`, `own_record_permission.py`, `hooks.py`) | Identical | Proven |
| `test_request_guard_alv249` on `test249` | 5 + 4 tests, OK. The CI scan alone takes **43 s** | Proven |
| `test_own_record_permission_alv249` on `test249` | 25 + 1 tests, OK. No rollback file left behind | Proven |
| My own scan of every whitelisted function and controller method in the six installed apps | Only 6 functions take an `ignore_*permission*` argument. **No whitelisted controller method takes one** | Proven |
| My probe, rolled back: `on_login` for a login linked by `set_value` | Row made in 0.18 s the first time, 0.005 s at the second sign-in. **The row's owner is `Guest`** | Proven |
| My probe, rolled back: the word nested inside JSON, as a staff login (`frappe.client.insert` with `flags` and a top-level `ignore_permissions`; `get_list` with the word inside `filters`) | Insert refused both times. `get_list` raised `DataError`, so no rows came back | Proven |
| A real HTTP request through `frappe.app.application` (cookies, API key, `/api/v2`) | Not run. That needs a staff login with a password on the site, which means writing data I did not want to leave behind. The order is proven by reading `frappe/app.py` instead | Not checked |
| Portal writes with the row in place, real roles at DTC and `aahr`, the full suites | Not run by me. They are still on the dev test list in 06 §6 | Not checked |

---

## Findings, worst first

There are no P0 and no P1 findings. Nothing leaks, and the guard fails safe.

### P2-A (new) · The rollback no longer undoes the change

- **State:** `rollback()` deletes only the row names saved in
  `sites/<tenant>/alv249_rows_added.json` (`own_record_permission.py:243-257`). Those are
  only the rows that `run_once` itself added (lines 203-211). The sign-in hook (line 119),
  the Employee hook and the User hook all add rows too, and none of those are saved. The
  test `test_rollback_removes_only_what_run_once_added` pins this behaviour: it checks
  that the hook-made row stays.
- **What happens:** the code is deployed. Staff sign in before `run_once` runs, and each
  of them gets a row from the sign-in hook. Later, anyone who is promoted and moved back,
  or who leaves and is rehired, gets a **new** row from a hook. Then something goes wrong
  (P2-B is the likely cause), so the team runs `rollback` and reverts the code. Every row
  made by a hook stays. Those people stay cut down to their own reporting tree with no
  code left to explain why. Nobody gets a list of who they are.
- **Why it matters:** the change is no longer fully reversible (rung 5). At DTC this is a
  step backwards. DTC had **0** own-record rows before the change (the engineer's count),
  so the old "delete every own-shape row" rollback was exact there. The new rule fixed
  security finding 5 for `aahr` and the demo tenants, but it broke the undo for DTC.
- **Smallest fix:**
  - Before the deploy, save each tenant's existing own-shape rows. This is one read-only
    query. It cannot be `run_once`'s dry run, because that code is not on the tenant
    until the deploy.
  - Change `rollback` so it deletes every own-shape row on a linked login **except** the
    rows in that saved list.
  - Or, simpler: keep the deploy time, and have rollback delete the own-shape rows
    created after it.
  - Both are a few lines.

### P2-B (carried from P2-2, now wider) · The rule reaches people before the "check by hand" list is read

- **State:** the dry-run list of logins with unusual roles (`run_once`, lines 179-182) is
  still the only human check. The sign-in hook now applies the rule to **every** staff
  login the first time they sign in after the deploy. Before, it applied only when HR
  saved that person's record.
- **What happens:** at a tenant, some role acts on other people's documents but does not
  read Employee. One example is a supervisor role that reviews attendance corrections.
  Every holder of that role gets the row at their first sign-in, and their queue shrinks
  to their own tree. Option A (give the role read on Employee) is the agreed fix, but
  nobody has looked at that tenant's roles yet.
- **Why it matters:** it fails closed, which is the right way round. But a real user can
  meet it in their first week, and a rollback does not reach them (P2-A).
- **Smallest fix (no code):** before the deploy, run a read-only query on each tenant:
  enabled, linked logins with no excluded role that hold a role outside `EXPECTED`.
  Apply option A where it is needed. Or Surbhi accepts the risk in writing.

### P3-1 · A failure in the sign-in sync stops that person signing in

- **State:** Frappe's `run_trigger` (`frappe/auth.py:330-332`) has no `try` around the
  hooks, and `own_record_permission.on_login` (line 115) has none either. An error in it
  fails the login request, and the database is rolled back.
- **What I found:** no realistic trigger. I read User Permission's checks. The duplicate
  check needs an exact match. The "default" overlap check needs `is_default`, which this
  row never sets. Two first sign-ins at the same moment from two devices make two identical
  rows, not an error. That is harmless, because `sync` handles a list.
- **Why it is still listed:** every staff sign-in on every tenant now depends on this
  code. The project's own request-path hook, `lock_until_password_chosen`, fails open by
  design for exactly this reason. Your brief says the sync "must never block a login",
  and today nothing in the code makes that true.
- **Fix if wanted (three lines):** catch the error, write a `frappe.log_error` with the
  login id only, and let the sign-in go on. That person has no row until the next save or
  `run_once`, which is today's state. **Surbhi decides** between keeping people able to
  sign in and closing the gap at once.

### P3-2 · Nested arguments: no door today, but the CI test cannot see the one place a door could appear

- **Proven:** `drop_permission_skips` cleans `frappe.local.form_dict`. Every route reads
  that dictionary: "/" with `cmd`, `/api/method`, `/api/resource`, `/api/v2` and its
  document routes, `run_method`, website page POSTs, and JSON bodies. The order is
  `make_form_dict`, then the session (login runs here), then the `before_request` hooks,
  then `validate_auth`, then routing (`frappe/app.py:139-158, 214-245`). The API-key and
  OAuth paths call `set_user`, which empties `form_dict`, but then they put back **the
  same object**, already cleaned (`frappe/auth.py` validate_api_key_secret and
  validate_oauth). With a JSON body, query-string arguments are left out of `form_dict`,
  and no route reads them.
- **Two channels splat a nested JSON value into a whitelisted controller method:**
  `frappe.handler.run_doc_method(args=...)` and `/api/v2/method/run_doc_method
  (kwargs=...)`. The guard does not look inside them. Today nothing is reachable through
  them: my scan found no whitelisted controller method that takes either word.
- **The gap:** the CI test promises that "an upgrade that adds such an argument fails
  until someone looks". Suppose an upgrade adds a whitelisted **controller method** that
  takes `ignore_permissions`. That name is already in `DROP`, so the test passes. But the
  argument would arrive nested inside `args`, where `DROP` never reaches.
- **Smallest fix:** in the CI test, report any whitelisted method defined inside a class
  that takes such an argument, whatever `DROP` holds. That is about two lines.

### P3-3 · The guard's docstring says HR "hold no User Permissions". At DTC they do

- `request_guard.py:18-21` and 06 say that HR and System Managers see the same Desk link
  pickers as before. But ERPNext gives each HR person linked with "Create User
  Permission" a **Company** row, and the hook leaves it alone (my last review, P4 /
  follow-up ticket 1).
- **Effect at DTC:** none, because DTC has one company.
- **Effect on a multi-company tenant:** an HR person with that Company row loses the
  option to pick another company in Desk pickers on fields marked "Ignore User
  Permissions". Examples are `represents_company` and `Allowed To Transact With`.
  Announcements are not affected, because the portal posts them through its own method.
- **Fix:** correct the sentence, and add it to follow-up ticket 1.

### P3-4 · Rows made at sign-in are owned by "Guest"

- The hook runs before Frappe creates the session, so the session user is still `Guest`.
  My probe shows `owner = Guest` on the new row.
- In a grievance, a User Permission list showing "created by Guest" reads like an
  anonymous change.
- **Fix:** add one line to the module docstring, and to the runbook, saying that rows made
  at sign-in show Guest as owner. A code change is not worth it.

### P3-5 · Carried and still open

- **Old P3-4:** Location Managers, and any role given read on Employee under option A,
  keep reading every employee's date of birth, address and passport number. I could not
  find this residual written on the ticket with an owner.
- **Old P3-5:** a manager used as a sample in `run_once` can print a false FAIL if they
  hold hand-made Expense Claim rows. 06 does not mention it. Use plain staff logins as
  `samples`.
- **Already open sessions:** the sign-in hook does not reach a session opened before the
  deploy, and that session can last up to 170 hours on `test249`. API-key access is not
  reached either. `run_once` straight after the deploy covers both. Keep that order in the
  runbook.

### P4 (backlog)

- `test_server_code_passing_the_word_is_untouched` cannot fail. It only checks that
  Administrator's `get_list` returns something.
- The CI scan adds about 43 s to every full run. An app whose package folder is not
  `apps/<app>/<app>` is skipped silently, so the test would pass without checking it.
- The `SafeToRunTwice` tear-down deletes `alv249_rows_added.json`. If someone ran this
  test on a live tenant by mistake, it would delete that tenant's rollback list. The
  rollback test would also delete real rows in that case.
- `Employee.user_id` has no database index. Each sign-in and each User save scans
  Employee. That is fine at 430 people, and a few milliseconds at 10,000.
- 06 cites commit `53a3e9f5` for the guard. After the rebase, that commit is `5b552ca2`.
- There is still no test for the ALV-226 path (an HR login linked with
  `create_user_permission = 1`).

---

## Your questions, answered

| Question | Answer | Label |
|---|---|---|
| Desk link pickers | A field marked "Ignore User Permissions" now shows a login that holds rows only its permitted records. Staff and managers see their own tree. HR at DTC sees no change (one company). See P3-3 for multi-company tenants. Saving still works, because Frappe reads that flag from the field definition on the server, not from the request | Proven (read `link.js:437`, `search.py:97-105`) |
| `validate_link_and_fetch` | Does not send either word | Proven (grep of Frappe JS) |
| `search_link` used on purpose by HR or System Manager | They hold no Employee rows, so dropping the word changes nothing for Employee. Company rows: see P3-3. Frappe v16 also checks the word against the field definition before honouring it (`validate_ignore_user_permissions`) | Proven |
| Apps that send the word from the browser | Only three places in all six apps: the link control, the table multi-select (the same flag), and bulk "clear assignment". `remove_multiple(doctype, names)` does not take the word, so it was already ignored | Proven (`assign_to.py:191`) |
| ERPNext `make_*` and the other 5 methods | No browser code sends `ignore_permissions` to them, so nothing breaks. The door is shut | Proven |
| API key and token calls | Guarded. The auth step puts back the same cleaned `form_dict` | Proven (read) |
| Website POST to "/" with `cmd` | Guarded. The same `form_dict` is cleaned before `frappe.handler.handle` | Proven (read) |
| Guest methods | None takes either word. Dropping them changes nothing | Proven (scan) |
| Is `form_dict` where everything lives? | Yes for every route that passes arguments. JSON body: parsed into `form_dict`. A JSON list body: put under `data`. v1 create and update re-read the raw body, but there `flags` is a reserved key, and a plain `ignore_permissions` key is never read by `insert()` or `save()` | Proven (read and probe) |
| The word nested in a JSON parameter | `get_list`: becomes a filter, which raises `DataError`. `client.insert` and `save`: refused. `run_doc_method` `args` and v2 `kwargs`: not cleaned, but there is no target today (P3-2) | Proven (probe and scan) |
| Runs before `/api/resource` and `/api/v2`? | Yes. Hooks run in `init_request`, before any routing | Proven (read) |
| Hook order with the auth lock | Frappe's recorder, monitor and rate limiter run first, then the guard, then the lock. The guard cannot raise, because `form_dict` is always a dict | Proven |
| `on_login` speed | 0.18 s at the first sign-in (warm-up plus one insert), 0.005 s after that | Proven (probe) |
| `on_login` failure | It would block that sign-in (P3-1) | Proven (read) |
| HR and System Manager sign-ins | The same few queries. It removes any own-record row ERPNext made for them, which is the intended ALV-226 behaviour | Proven (read) |
| API-key logins | Never reach `on_login`. Covered only by `run_once` and the save hooks | Proven (read) |
| Rollback file: multi-site and multi-worker | One file per site path, so sites do not clash. Only `run_once` and `rollback` touch it. Two operators running at once could lose names (read, merge, write), which is an edge case. A half-written file makes rollback refuse, so it fails safe. Names that were never committed are filtered out at rollback | Proven (read) |
| A second sign-in | Does nothing. `sync` finds the row and returns | Proven (probe) |
| CI test false failures on other apps | No false failures today: India Compliance and our apps have no such argument. A future harmless argument with that name would fail CI on purpose. The bigger risks are false passes: P3-2, and app folders that are skipped (P4) | Proven (scan) |

## Earlier findings: where they stand

| Earlier | Now |
|---|---|
| P2-1 script-linked logins | **Mostly closed.** The sign-in hook and `sync_user` are tested. Still open: DTC's own account script is not in the repo, so its one line is not added, and the two demo-script lines have not been made |
| P2-2 rule live before the list is read | **Open, wider.** See P2-B |
| P2-3 managers read their tree's pay and bank details | **Closed with a recorded yes.** 06 records Surbhi's acceptance on 31 Oct (Inferred: I saw the record, not her words) |
| P3-1 hide descendants | Closed. Written into D-2 |
| P3-2 rollback scope | Changed, and it opened P2-A |
| P3-3 role permission changes | Closed by the sign-in hook plus a runbook line |
| P3-4, P3-5 | Open (see P3-5 above) |

## Seven dimensions: what 06 claimed, and what the code does

| Dimension | 06 claim | My finding |
|---|---|---|
| Performance | Neutral | Agree. About 3 queries per sign-in and 43 s more of CI time |
| Security | Improves | Agree. Doors 1 and 2 are shut on every route. Nested channel: no target today (P3-2) |
| Reliability | Neutral | **Slightly worse.** Every sign-in now depends on the sync (P3-1), and the rollback is partial (P2-A) |
| Scalability | Neutral | Agree. `Employee.user_id` has no index (P4) |
| Maintainability | Neutral | Agree. The guard is 10 lines of code. One docstring sentence is wrong (P3-3) |
| Data integrity | Improves | Agree. Rows drift less now that sign-in catches up |
| Compliance / privacy | Improves | Agree. Purpose limitation now holds even against a crafted request |

## Compliance (judged against 04 §3.3 and the baseline, as before)

| Obligation | Mechanism | Test | Status |
|---|---|---|---|
| Staff see only their own record, even with a crafted request | Own-record row, plus `request_guard` | `test_request_guard_alv249` door tests | Discharged |
| New joiners covered | Sign-in hook and `sync_user` | `LinkedByDatabaseWrite` | Discharged for password sign-in. Partial for API keys and already-open sessions (covered by `run_once`) |
| Undo is possible | `rollback` | `test_rollback_removes_only_what_run_once_added` | **Partial** (P2-A) |
| No personal data in logs | No new logging | read | Discharged |

## What to delete

Nothing. The guard is minimal. `on_login` and `sync_user` close a real gap. The rollback
file is the right idea, but its scope is wrong (P2-A). The only candidate is the one test
that cannot fail (P4). Fix it or delete it.

## What was done well

- **The guard is in the right place.** It runs once, in one hook, before Frappe routes
  anything. It covers every entry point without listing any of them.
- **The door tests can fail.** Each one first shows a colleague's record coming back
  without the guard, then shows it gone with the guard.
- **A second word was found by testing, not by reading the review.** The engineer found
  `ignore_permissions` on `make_salary_slip` and shut it in the same change.
- **The CI scan is a test, not new infrastructure.** An upgrade that adds a new skip
  argument now fails CI.

## Confidence

- **High:** where request arguments live and the order of the hooks (read and probe), the
  list of skip arguments (scan), and the test results for the two modules I ran.
- **Medium:** the impact on real tenants' roles (P2-B). I could not see DTC's or `aahr`'s
  roles.
- **Not checked:** a real HTTP request through the WSGI app, portal writes with the row in
  place, and the full suites. To check them I would need a staff login with a password on
  `test249`, and the dev test list in 06 §6.

## Questions

| Priority | Question | Holds the verdict? |
|---|---|---|
| Must know | P2-A: will rollback delete every own-shape row except a list saved before the deploy (or every row created after the deploy time)? | Yes, before the production run |
| Must know | P2-B: will the read-only role check run on each tenant before the deploy, or does Surbhi accept the risk in writing? | Yes, before the production run |
| Should know | P3-1: should a failed sync let the person sign in (and log the error), or block the sign-in? | No |

## Subtract pass on this review

I removed three things:

- A finding about `/api/v1` create and update re-reading the raw body. My probe showed
  it is not a door, so it is now one line in the table.
- A worry about duplicate rows from two sign-ins at once. The result is harmless, so it
  is folded into P3-1.
- A note about `auth.on_login` reading `frappe.session.user` while it is still Guest.
  That is older code, not part of this slice, and I did not trace it.
