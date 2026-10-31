# ALV-249 · Implementation notes: staff see only their own Employee record

Built 31 Oct 2026 on branch `slice/alv-249-employee-list-exposure` (worktree
`.claude/worktrees/alv-249`), on top of `origin/dev` d3afcaa5. Nothing new came in from
`origin/dev` when I fetched before starting. **Local only. Not pushed. Dev and production
untouched. No SSH.** Surbhi's decisions: D-1 the standard own-record row with a sync
function; D-2 managers keep the standard behaviour and see their whole reporting tree.

---

## Bad news first

0. **The row breaks an approved behaviour: a non-HR reviewer loses their queue.**
   `test_inbox_counts_034.test_a_reviewer_who_is_not_hr_keeps_their_whole_queue` (AC-52,
   W1D-14) fails with this change and passes without it.
   - **Who:** a login with a custom role, like "Shift Supervisor", that may submit
     Attendance Requests for other people but does not read Employee.
   - **What happens:** that role is not excluded, so the login gets the row, and the row
     limits its Attendance Request queue to its own reporting tree. The queue showed 0
     instead of 3.
   - **Why approvers are different:** leave and expense approvers keep working, because
     Frappe HR shares each document with its approver (tested). Attendance Request
     reviewers get no share.

   **This needs Surbhi's decision before anything goes to dev. I have not changed the
   rule or the other team's test.** The choices:

   | | What | Cost |
   |---|---|---|
   | **A (my recommendation)** | Configuration, per tenant: give each genuine reviewer role read on Employee in Role Permission Manager. The rule then excludes it by itself. The 034 test fixture would need the same one permission | No code. Those reviewers keep seeing every employee, as today. The dry run's "check by hand" list shows every such login before the run |
   | B | Code: also exclude any role with submit on Attendance Request, Leave Application or Expense Claim | ~5 lines. Wider exemption, harder to explain |
   | C | Code: give the row only to logins whose roles are all ordinary staff roles; everyone else is listed and left as today | Fails open for every unusual role |

   Before choosing, count at DTC (read-only): which roles have submit on Attendance
   Request, and how many enabled logins hold them.

1. **The module has two `ignore_permissions`, not zero.** Only System Manager may write a
   User Permission, and the hooks run when HR saves an Employee or a User. Without the
   bypass, an HR User saving an Employee would get an error. The two writes are one insert
   and one delete of this exact row shape. They are pinned at 2 in
   `test_portal_security_010.CEILINGS`. `manager_scope.py` does the same thing for the same
   reason.
2. **Portal writes are still not proven.** The local site has no leave allocations, so I
   could not file or approve leave, file or decide a claim through the portal, raise an
   attendance request for a team member, give upward feedback, mark grooming, or use the
   driver portal with the row in place. These are the dev test list in section 6.
3. **ERPNext adds a Company row for an HR person** when an HR Employee is saved with a new
   `user_id` and `create_user_permission` = 1 (all 430 at DTC). My hook removes ERPNext's
   **Employee** row for HR (the ALV-226 trap). It does not touch the **Company** row:
   that is ERPNext's own and harmless on DTC's single company. On a multi-company tenant it
   would limit that HR person to one company. Not changed here; noted for review.
4. **Separate leak, for its own ticket:** the *Employee Leave Balance* report shows an HR
   Manager limited to one company the leave balances of **every company** (190 rows across
   all companies on the test site). The report ignores Company permissions. It does not
   bite at DTC (one company).
5. **The hook takes effect on deploy, before the one-off run.** From the moment the code is
   live, every Employee or User save gives or removes the row for that one person. Until
   `run_once` is run, most staff still have no row. That is safe (it only narrows), but
   counts taken between deploy and run will not match the "before" numbers exactly.

---

## What was built

| File | What | Rung |
|---|---|---|
| NEW `alvoraa_portal/alvoraa_portal/own_record_permission.py` | `excluded_roles`, `sync`, the two hooks, `run_once` (dry run and real), `rollback` | 4: a hook keeps a standard row right. Rung 2 alone (the row) does not survive new joiners or role changes |
| `alvoraa_portal/alvoraa_portal/hooks.py` | One line appended to `Employee.on_update`, one to `User.on_update` | Hot file: two lines appended, no other block touched |
| NEW `alvoraa_portal/alvoraa_portal/tests/test_own_record_permission_alv249.py` | 22 tests, named for ALV-249 so a bad merge fails CI | — |
| `alvoraa_portal/alvoraa_portal/tests/test_portal_security_010.py` | One ceiling row: the new file, 2 | — |

**Not built, on purpose:**
- No DocType, no Custom Field, no patch, no `after_migrate`. A tenant is changed only by
  the hooks or by someone running `run_once` on purpose.
- No Custom Role fixtures for the two reports. The real build closes both: the test
  `test_birthday_and_leave_balance_reports_show_no_colleague` passes with the row alone.
- No translations: there are no new user-facing strings. The only messages are
  "Run as Administrator." for a console function.

### The rule, as coded

- **The row exists when** the login is enabled, is the `user_id` of an Employee, and holds
  no excluded role.
- **Otherwise the row is removed.** Only that exact shape is touched: allow Employee,
  `for_value` = the login's own Employee, all document types. `manager_scope`'s narrow rows
  and any row on somebody else's record are never touched (tested).
- **Excluded roles:** every role that reads Employee at level 0 in the site's own
  permissions, minus Employee and Employee Self Service, **plus System Manager and
  Administrator by name**. The test site taught this: System Manager had no read row on
  Employee there, and a rule computed only from permissions cut it down to one record.
- **Leavers:** ERPNext disables the login of any employee who is not Active, and enables
  it again on a rehire (`erpnext/setup/doctype/employee/employee.py:296-307`). The row
  follows the login, so a leaver loses it and a rehire gets it back (tested).
  **Changed from 05:** the code does not check the Employee status. If somebody
  re-enables a leaver's login by hand, the row stays. An enabled login without the row
  would see everyone, so this fails closed.
- **Promotion:** adding HR User removes the row in the same save; removing it puts the row
  back (tested).
- **Login moved:** clearing or changing `user_id` removes the old login's row (tested).

### The one-off production run (not run on any tenant)

```text
bench --site <tenant> execute alvoraa_portal.own_record_permission.run_once --kwargs "{'dry_run': 1}"
bench --site <tenant> execute alvoraa_portal.own_record_permission.run_once --kwargs "{'dry_run': 0, 'samples': ['a@x', 'b@x', 'c@x']}"
bench --site <tenant> execute alvoraa_portal.own_record_permission.rollback
```

- **Dry run, writes nothing.** It prints:
  - the excluded roles;
  - N, the number of logins due a row;
  - every login due a row that also holds a role other than Employee, Employee Self
    Service, Leave Approver or Expense Approver, for a person to check by hand;
  - the "before" count of rows, and how many sit on excluded or disabled logins;
  - per sample login, and per enabled login that gets no row (HR, System Manager): how
    many Employee rows they can list, plain and with `reference_doctype=ToDo`, and how
    many expense claims.
- **The real run** prints the same, syncs every linked login, then prints PASS or FAIL for:
  - rows = N exactly;
  - 0 rows on excluded or disabled logins;
  - every due login has its row (names any that do not);
  - each sample login can list exactly 1 + the people below them in the tree (from
    `lft`/`rgt`), with or without `reference_doctype`, and exactly the claims of those
    people plus claims shared with them;
  - every login without a row has identical counts to before.

  It returns the number of FAILs. Each expected number is worked out separately from what
  it is checked against.
- **Rollback** deletes own-record rows of the exact shape on every linked login. At DTC
  none existed before (31 Oct count), so this removes exactly what was added.
- Both refuse anyone but Administrator (tested). A second real run changes nothing and
  still passes (tested).

---

## Acceptance list (from 05's table) and how each is proven

| Check | Test |
|---|---|
| New joiner gets the exact row | `test_new_joiner_gets_the_exact_row` |
| REST list: own record only | `test_rest_list_is_own_record_only` |
| Extra word: `reference_doctype` Employee, ToDo, Leave Application, Expense Claim, Attendance | `test_the_extra_word_reference_doctype_does_not_open_it` |
| `get_count` with ToDo = 1 | `test_count_with_reference_doctype` |
| Colleague record refused, own allowed, colleague DOB empty | `test_one_record_and_one_value` |
| Link search and `/hrms` app: own only | `test_link_search_and_the_hrms_app` |
| Birthday and leave balance reports: no colleague | `test_birthday_and_leave_balance_reports_show_no_colleague` |
| Expense Claim list: own only; no read or write on others' (ALV-261) | `test_list_shows_only_own_claims`, `test_no_write_on_someone_elses_claim` |
| Approver share still gives read and submit | `test_an_approver_still_reaches_a_claim_shared_with_them` |
| Manager: self + whole tree, not a peer; narrow rows left alone | `test_manager_lists_self_reports_and_their_reports` |
| HR Manager and System Manager: no row, counts = all | `test_hr_manager_and_system_manager_get_none_and_keep_their_counts` |
| System Manager excluded even without a read row | `test_system_manager_is_excluded_even_without_a_read_row` |
| Promotion to HR removes, back to staff restores | `test_promotion_to_hr_removes_the_row_and_back_restores_it` |
| Leaver loses it, rehire gets it back; re-enabled leaver keeps it | `test_leaver_loses_...`, `test_an_enabled_login_on_a_left_record_keeps_the_row` |
| Login moved off a record | `test_login_moved_to_another_record` |
| Safe to run twice; dry run writes nothing; run_once clean twice | `SafeToRunTwice` (3 tests) |
| Rollback removes only the exact shape | `test_rollback_removes_only_the_exact_shape` |
| Hooks are wired (pin) | `test_hooks_are_wired` |
| Bypass count = 2 | `test_portal_security_010` ceiling row |

---

## Non-functional review, against the code written

| Dimension | Before → after | Why |
|---|---|---|
| Performance | Neutral | A hook costs 3-4 small queries per Employee or User save. Lists get one more `IN` condition from Frappe. `run_once` loops once over linked logins; at about 430 it is seconds |
| Security | **Improves** | Every door in 05 closed for staff, including `reference_doctype`; expense claims closed too |
| Reliability | Neutral | A hook error would fail the Employee or User save. Both writes use Frappe's own `get_doc().insert()` and `delete_doc()` |
| Scalability | Neutral | Per-person rows, one per login. Frappe caches them per user |
| Maintainability | Neutral | One file, ~220 lines (about half is the one-off run and its checks), same shape as `manager_scope.py` |
| Data integrity | Improves | The row follows the login on every save. Drift from direct database writes is caught by `run_once`'s counts |
| Compliance / privacy | **Improves** | A colleague's date of birth, phone, address, passport number, leave balance and claims are no longer open to every staff login. Fails closed: an unknown extra role still gets the row; only roles that read Employee are excluded. No personal data is logged; `run_once` prints login ids and employee ids only, to the operator's console |

## Personas

- **CXO / System Manager:** no change.
- **HR Manager / HR User:** no change. Never get the row.
- **Manager:** sees self + everyone below them, in Employee and every document linking
  to Employee. Today: everyone.
- **Employee:** sees self only. Today: everyone.

---

## Tests and checks run (own container `hrlocal-249`, site `test249`, one module at a time)

| Module | Result |
|---|---|
| `test_own_record_permission_alv249` | 22 tests, OK (first run: 1 failure, the leaver test; ERPNext disables a leaver's login, test and docstring corrected) |
| `test_access_control` | 34, OK |
| `test_portal_security_010` | 45 + 5, OK (includes the new ceiling row) |
| `test_employee_field_rights_alv215` | 20, OK |
| `test_home_076` | 6 + 18, OK |
| `test_expense_birthdays_076` | 35, **1 error, already there before this change**: `test_the_claimant_cannot_choose_their_approver_but_hr_can` fails the same way with my hooks switched off (an HR Manager may not delete the old approver's DocShare). Not mine; it needs its own ticket |
| `test_inbox_counts_034` | 17 + 2, **1 failure caused by this change**: `test_a_reviewer_who_is_not_hr_keeps_their_whole_queue` (bad news 1). With my hooks switched off it passes |
| `test_inbox_parts_042` | 31, OK |
| `test_manager_scope` | 12, OK |

How "with my hooks switched off" was checked: the two hook lines were taken out of
`hooks.py` in this worktree only, the cache cleared on `test249`, the one test re-run, then
the file put back byte for byte and the cache cleared again. A first attempt with `sed`
left `hooks.py` unparsable for a few seconds while `test_inbox_counts_034` was mid-run in
the background. The failure above was then reproduced cleanly with the hooks on, and the
pass with them off, so the result stands. I did not re-run `test_inbox_parts_042`, which
started after the file was restored.

- `python scripts/check_app_integrity.py`: 864 checks, OK.
- `python scripts/check_scope_traps.py`: OK.
- Full suites not run. One run at the end before a push, per the agent cost rule.

## What else moved

Nothing. `origin/dev` was still at d3afcaa5 when I fetched before building.

---

## 6. For the dev test, before production

Portal writes with the row in place, as a staff login and a manager:

1. Apply leave as staff; the manager approves.
2. File an expense claim as staff and see it in the list; the approver decides it.
3. A manager raises an attendance request for a report.
4. Upward feedback (`Upward Feedback.about_employee` names the manager, which is outside a
   staff member's tree).
5. Grooming mark by a supervisor.
6. Notice acknowledgement; policy acknowledgement.
7. Field check-in and the field app join flow.
8. Driver portal and delivery doctypes (`Delivery Partner.reporting_manager`,
   `Delivery Assignment.driver`), if any DTC login uses them.
9. Team goals, KPIs and appraisal screens for a manager.
10. Then `run_once` with `dry_run=1` on the dev tenant, Surbhi reads the "check by hand"
    list, then the real run, then the full suites once.

## Shortcuts, labelled

| Item | Label |
|---|---|
| Two `ignore_permissions` for the User Permission writes | Intentional trade-off (only System Manager may write that doctype) |
| ERPNext's Company row on HR people left alone | Acceptable simplification at DTC; a note for multi-company tenants |
| Leave Balance report ignores Company scope for HR | Dangerous debt on multi-company tenants: its own ticket |
| Portal writes untested locally | Temporary debt: removed by the dev test list above |
| Rows made by a direct database write to `user_id` or roles are not caught until the next save or `run_once` | Acceptable simplification, same as `manager_scope` |

## Subtract pass

Removed while building:
- a third `ignore_permissions` in `rollback`, which now reuses the delete;
- a status check, deliberately (see Leavers);
- the Custom Role fixtures, because the row closes both reports.

Nothing else can go without losing a test.
