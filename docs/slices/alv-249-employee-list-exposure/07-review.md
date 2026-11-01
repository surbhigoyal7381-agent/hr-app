# ALV-249 · Senior review: the own-record User Permission row

**Verdict: SHIP WITH FIXES.** The code does what it says, and I ran its tests. Three gaps
need a written yes or a small step before the production run. None of them is a code
defect, and none blocks pushing to dev.

Reviewed 31 Oct 2026, on branch `slice/alv-249-employee-list-exposure` (4 commits on
`origin/dev` d3afcaa5, all by `surbhigoyal7381-agent`, no merge commits). `origin/dev` had
not moved when I fetched. I did not edit any source file. This is advice. **Surbhi decides
whether it ships.**

## What I ran, and what I could not

| What | Result | Label |
|---|---|---|
| `test_own_record_permission_alv249`, on the engineer's own site `test249` (container `hrlocal-249`, mounted from this worktree; file hashes match) | 21 + 1 tests, OK | Proven |
| `test_inbox_counts_034` (the module with the fixture change), same site | 17 + 2, OK, including `test_a_reviewer_who_is_not_hr_keeps_their_whole_queue` | Proven |
| My own probe, rolled back: an HR Manager and a staff login, each linked with `create_user_permission = 1` (the DTC shape), saved twice as Administrator | HR: ERPNext's Employee row is removed by the hook, its Company row stays. Staff: one own row. A second save changes nothing | Proven |
| The other suites the engineer lists (access control, 010, 215, 042, manager scope, 076) | Not re-run by me | Not checked |
| Portal writes with the row in place (leave, claims, grooming, goals, driver portal) | Nobody has run them; on the dev test list | Not checked |
| DTC's real roles, Custom DocPerm and Salary Slip data | No access; I relied on the engineer's read-only DTC count | Not checked |
| The script DTC uses to create logins | Not in the repo. `demo/link_employee_users.py` is the same shape | Not checked |

There is no product brief, UX design or functional spec for this ticket. It came in as a
bug. The impact analysis (04), test results (05) and notes (06) stand in for them. So
the compliance axis has no spec table to check against. I judged it against 04 §3.3 and
the security baseline instead, and say so below.

---

## Findings, worst first

No P0 and no P1. Nothing leaks, nothing is lost, and every write can be undone.

### P2-1 · Logins linked by a script never get the row. The hole reopens for each new batch

- **State:** DTC's logins are linked with `frappe.db.set_value("Employee", ..., "user_id", ...)`.
  The module's own docstring says so (`own_record_permission.py:6-7`).
  `demo/link_employee_users.py:83` does the same.
- **What happens:** `set_value` runs no hooks. The new login gets no row, so it can list
  every employee and every expense claim, exactly as today. It stays open until HR next
  saves that person's Employee or User record, or someone runs `run_once` again.
- **Why it matters:** DTC is still taking on staff, including agency staff. The fix only
  holds for logins linked through the form. 06 calls this an "acceptable simplification",
  but for a privacy hole it is not acceptable without an operating rule.
- **Smallest fix (no product code):** write one rule into the runbook: *after any bulk
  login creation, run `run_once` with `dry_run=0` on that tenant.* Better still, have
  the account script call `own_record_permission.sync(email, employee)` after its
  `set_value`. That is one line.

### P2-2 · The rule goes live on deploy, before anyone reads the "check by hand" list

- **State:** the hooks act from the moment the code is deployed, on every tenant the
  deploy reaches (DTC, `aahr`, the demos). The dry run's list of logins with unusual
  roles (`run_once`, lines 165-168) is the only human check, and it runs later.
- **What happens:** say HR saves the Employee record of someone with a custom role that
  acts on other people's documents but does not read Employee (an accounts or supervisor
  role). That person gets the row on that save. They are cut down to their own reporting
  tree before anyone has looked. The same happens to every future login with such a
  role. Nobody is ever shown a list for them.
- **Why it matters:** this is the ALV-226 lesson in a new form. It fails closed, which is
  the right way round for privacy, and it can be undone. But it can surprise a real user
  on day one. DTC was counted only for Attendance Request reviewers (Location Manager,
  already excluded). Other roles, and the other tenants, were not counted.
- **Smallest fix:** before the deploy, run the same read-only query on each tenant:
  enabled linked logins with no excluded role, holding a role outside `EXPECTED`. Apply
  option A (give the role read on Employee) where needed. Then run `run_once` straight
  after the deploy.

### P2-3 · Managers will read their whole tree's salary slips, bank account numbers included. Confirm this in writing

- **State:** decision D-2 keeps ERPNext's standard behaviour: the row covers everyone
  below a manager. 05 Q1 says it covers "every document of theirs that links to
  Employee". `Salary Slip` gives the Employee role plain read, with no "only if owner"
  limit (`hrms/payroll/doctype/salary_slip/salary_slip.json`). `bank_name`,
  `bank_account_no`, `gross_pay` and `net_pay` sit at level 0 there. No row rule on
  Salary Slip exists in our apps (`hrms/hooks.py` `permission_query_conditions`).
- **What happens:** a manager calls `/api/resource/Salary Slip` and gets the pay and bank
  account number of everyone below them. Leave reasons, expense claims and appraisals of
  the tree are open to them the same way.
- **Why it matters:** this is **narrower than today**. Today every staff login can read
  every slip. So it is not a new leak. But D-2 was put to Surbhi mainly as "managers see
  their team's Employee records". Pay and bank details were not named. I did not check
  whether DTC has any Salary Slips. Payroll there runs outside the portal (memory, 26 Oct),
  so it may be zero today. It will not stay zero.
- **Ask:** "Managers will be able to read their team's salary slips and bank account
  numbers through the API. Is that OK, or should slips get their own rule (a separate
  ticket)?" **Provisional rank: P2.** It ships with a written yes, or with a ticket.

### P3-1 · "Tick hide descendants later" is not a lasting setting

- 05 §3 says managers' tree view can be turned off later by ticking "hide descendants".
  `sync` never rewrites an existing row, so a ticked row survives a normal save. That is
  good. But a promotion and demotion, or a leave and rehire, removes the row and adds it
  back **without** the tick (`own_record_permission.py:81-83`, pinned by
  `test_new_joiner_gets_the_exact_row`). That person quietly goes back to seeing their
  whole tree.
- **Fix if she ever chooses it:** it is a code change (one flag on the insert), not
  configuration. Write that into D-2 so nobody treats it as a switch.

### P3-2 · Rollback is exact only when there were no rows before, and it does not stop the hooks

- `rollback()` (lines 213-221) deletes **every** own-shape row on a linked login, not only
  the ones `run_once` added. At DTC that was 0 before (the engineer's 31 Oct count). On
  `aahr` or a demo tenant, ERPNext may already have made some through the form. Rollback
  would delete those too.
- While the code is deployed, the hooks add the rows back on the next save. So rollback
  without a code revert is a short pause, not an undo.
- A real run that prints FAIL does not undo itself, and `bench execute` commits. The
  operator must run `rollback` by hand.
- **Fix:** add one line to the runbook. Record the dry run's "BEFORE own-record rows"
  number. If it is not 0, save the row names before the real run. Roll back only with the
  code revert.

### P3-3 · Changing a role's permissions does not re-sync anyone

- Option A says "give the reviewer role read on Employee, and the rule excludes it by
  itself". That holds only for the next save of each holder. Their existing rows stay
  until then. The reverse is also true: a role that loses read on Employee leaves its
  holders without a row, and so open.
- **Fix:** a runbook line. After any change to Employee permissions in Role Permission
  Manager, re-run `run_once`.

### P3-4 · Residual exposure, decided but worth recording

- DTC's 5 Location Managers, and any role given read under option A, keep reading every
  employee's date of birth, address and passport number. That is the agreed trade-off
  (option A). It should be written on the ticket as a known residual, with an owner.

### P3-5 · The sample check can FAIL falsely for DTC's 7 hand-made managers

- `_expected` (lines 132-140) counts claims for the tree plus shared claims. 04 §1.4 says
  DTC's 7 managers also have hand-made Expense Claim rows whose source is unknown. If a
  sample manager has rows for people outside their tree, `got` will be bigger than
  `want`, and the check prints FAIL. **Inferred** from Frappe merging narrow rows with the
  all-doctypes row. It fails safe, but it could start a rollback for no reason.
- **Fix:** pick plain staff as the three samples (pass `samples=`), or read a FAIL on a
  manager sample as "check by hand" first.

### P4 (backlog)

- The ALV-226 path is not covered by a test: HR linked with `create_user_permission = 1`.
  Every test fixture uses 0, but DTC uses 1 on all 430. My probe above proves the
  behaviour is right. A test would keep it right.
- The `add_permission` call in the 034 fixture would copy all of Employee's standard rows
  into Custom DocPerm if none existed, and the teardown deletes only the role's own row.
  In practice it never fires: ALV-215 already writes Custom DocPerm rows on Employee.
- If a rehired person gets a new Employee record but keeps the same login, both records
  get a row. ERPNext allows this because its duplicate check looks at Active records only.
  The person sees their own two records. That is harmless.

---

## Your specific questions, answered

| Question | Answer | Label |
|---|---|---|
| Exclusion: Custom DocPerm vs DocPerm, permlevel 0, cache | `frappe.get_meta("Employee").permissions` returns Custom DocPerm when any exists (`frappe/model/meta.py:640-653`), else DocPerm. Level 0 only, "if owner" rows ignored. Meta is cleared when permissions change. System Manager and Administrator are added by name | Proven (read) |
| Hook order and re-entry | The controller's `on_update` runs before `doc_events`, so the hook always has the last word over ERPNext's own row. ERPNext's `update_user` and `update_user_status` each save the User, so one Employee save runs `sync` up to three times. Each run is safe to repeat. Inserting or deleting a User Permission saves neither User nor Employee, so there is no loop | Proven (read + probe) |
| Performance on every save | About 3 small queries per `sync`, so about 10 per Employee save, on top of ERPNext's `frappe.clear_cache()` that runs on every Employee save anyway. The User hook runs on every User save (passwords, themes) with no early exit, unlike `module_access`. It still costs well under 10 ms | Inferred |
| The two `ignore_permissions` | Lines 68 and 83. One delete and one insert of exactly this row shape. Needed because only System Manager may write User Permission. Pinned at 2 in `test_portal_security_010`. Justified | Proven |
| Leaver / rehire | ERPNext disables the login when status is not Active, and enables it on return (`employee.py update_user_status`). The row follows the login. Tested both ways | Proven (test run) |
| Promotion / role removed | Adding HR User removes the row on the same save. Removing it adds the row back (User `on_update`; Frappe clears the role cache first, `user.py:325`). Tested | Proven |
| A role's **permission** removed (not the role from the login) | Not re-synced. See P3-3 | Proven (read) |
| Multi-company / Company row | The hook never adds or removes Company rows. ERPNext's Company row on an HR person stays (probe). Harmless on one company. On a multi-company tenant it pins HR to one company. That is ERPNext's behaviour, not this change. Follow-up ticket 1 in 06 | Proven (probe) |
| `run_once` safety | The dry run only reads. The real run touches only own-shape rows, through `sync`. It refuses anyone but Administrator, it is not whitelisted (so it cannot be called over HTTP), and running it twice changes nothing (tested). The checks compare against numbers worked out separately. Gaps: P3-2, P3-5 | Proven (read + test run) |
| Manager tree | Self plus everyone below, not peers. `manager_scope`'s narrow rows are left alone (tested). Pay included, see P2-3 | Proven |
| Who could be cut off | HR User, HR Manager, System Manager, Administrator and Location Manager: never (excluded). Approvers outside the tree keep claims, leave and shift requests through Frappe HR's approver share (`hrms/hr/utils.py:800`; claims tested). Custom roles that act on others without reading Employee: yes, see P2-2. Portal endpoints mostly use `get_all` or `ignore_permissions`. Grooming and attendance-for-a-report inserts check permission but stay inside the direct-report tree | Proven for the listed paths; portal writes not checked |
| Tests can fail | Yes. They assert exact lists (`[self.me]`), exact counts against `frappe.db.count`, and before/after rows. The birthday report test reads `row[0]`, the employee id in that report's tuples, so it is not empty by accident. One weak spot: the leave-balance check counts a refusal as a pass. That is the right outcome, but the test would also pass if the report crashed with a permission error for another reason | Proven (read + run) |
| 034 fixture change | Only fixture lines were added. The assertion is untouched. It now gives the test reviewer role read on Employee, which is option A, the agreed tenant setup. So the test no longer covers "a reviewer role without Employee read". That case is now a setup rule, not code. Acceptable, with P2-2 covering it | Proven (diff + run) |

---

## Acceptance list (from 06) against code and tests

| Check | Status | Evidence |
|---|---|---|
| New joiner gets the exact row | Met, for form saves only | test passes; P2-1 for scripts |
| REST list, `reference_doctype`, count, single record, link search, `/hrms` | Met | tests pass (run by me) |
| Birthday and leave balance reports | Met | test passes |
| Expense Claim: own only, no write on others (ALV-261) | Met | tests pass |
| Approver share still works | Met for claims | test; leave and shift share by the same function (read) |
| Manager: self + tree, not a peer | Met | test |
| HR / SM: no row, full counts | Met | test, plus my probe for `create_user_permission = 1` |
| Promotion, leaver, rehire, login moved | Met | tests |
| Safe to run twice, dry run writes nothing, rollback shape | Met | tests; P3-2 on rollback scope |
| Portal writes with the row | **Not proven** | dev test list in 06 §6 |

## Non-functional check: what 04/06 claimed vs what the code does

| Dimension | 06 claim | My finding |
|---|---|---|
| Performance | Neutral | Agree. A few queries per save; Frappe caches the rows per user |
| Security | Improves | Agree, proven by tests. Residual: P2-2 (who is cut off), P3-4 (who keeps everything) |
| Reliability | Neutral | Agree. If a hook fails, the save fails, so there is no half-write |
| Scalability | Neutral | Agree. One row per login. `run_once` is one pass over about 430 logins |
| Maintainability | Neutral | Agree. Same shape as `manager_scope.py`; plain, commented |
| Data integrity | Improves | **Partly.** Drift from `set_value` and from permission edits is not caught (P2-1, P3-3) |
| Compliance / privacy | Improves | Agree, and strongly. Manager scope includes pay (P2-3) |

## Compliance (no spec table exists; judged against 04 §3.3 and the baseline)

| Obligation | Mechanism | Test | Status |
|---|---|---|---|
| Purpose limitation: staff see only their own personal data | Own-record row, kept by the hooks | alv249 suite | Discharged for form-linked logins; **partial** until P2-1 is closed |
| Role-based scoping, HR keeps access | Exclusion computed from permissions plus names | HR/SM test, my probe | Discharged |
| No personal data in logs | `run_once` prints login ids, employee ids and counts only, to the operator's console | read | Discharged |
| Managers' access to team pay and bank data | Decision D-2 (ERPNext default) | manager test | **Partial**: needs an explicit yes (P2-3) |

## What to delete

Nothing. `EXPECTED` and the dry-run listing earn their place (P2-2 depends on them). The
`run_once` checks are about half the file. They are the safety net for the live run, so
they stay. Nothing in the diff is beyond the ticket: no DocType, no field, no patch, no
`after_migrate`, no settings.

## What was done well

- **The approach changed after a real test, not an argument.** 05 measured option B next
  to the standard row and found B cut off the System Manager and left claims open. The
  team switched to ERPNext's own mechanism. That one step closed ALV-249 and ALV-261
  together, with less code.
- **The exclusion list is worked out from the site's own permissions,** with System
  Manager added by name after the test site showed it may have no read row. No hard-coded
  role list to go stale.
- **It only ever touches one exact row shape.** `manager_scope`'s rows and anybody else's
  rows are safe, and a test proves it.
- **The production run checks against numbers worked out separately,** so one missing
  login cannot hide inside a total (the 26 Oct lesson).
- **A test that the change broke was reported, not edited quietly.** The 034 failure was
  raised as bad news and decided by Surbhi before the fixture moved.

## Confidence

- **High** on the code paths I read and ran: the exclusion rule, hook order, the ALV-226
  path, and the test results.
- **Medium** on who could be cut off at real tenants. That depends on roles at DTC and
  `aahr` that I could not see (P2-2).
- **Not checked:** portal writes with the row in place, whether DTC holds Salary Slips,
  where DTC's account script lives, and the full suites. Needed: the dev test list in 06
  §6, a read-only role and slip count on each tenant, and one full-suite run before the
  push.

## Questions

| Priority | Question | Holds the verdict? |
|---|---|---|
| Must know | P2-3: is it OK that managers read their tree's salary slips and bank account numbers through the API? | Yes. Ship with a written yes, or a ticket |
| Must know | P2-1: who runs `run_once` after each batch of new logins, or does the account script call `sync`? | Yes, before the production run |
| Should know | P2-2: will the read-only role count be run on every tenant before the deploy? | No, but it is the cheap way to avoid a day-one surprise |

## Subtract pass on this review

Removed: a finding about the User hook running on every User save (it is cheap, so it
became a line in the table), a concurrency duplicate-row worry (I could not write a real
scenario for it), and a note about Employee deletion leaving rows (not checked, no
scenario).
