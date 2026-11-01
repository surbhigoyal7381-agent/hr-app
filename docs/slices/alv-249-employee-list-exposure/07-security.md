# ALV-249 · Security and privacy review

Reviewed 31 Oct 2026 by the security and privacy engineer, on branch
`slice/alv-249-employee-list-exposure` (`git diff origin/dev...HEAD`), worktree
`.claude/worktrees/alv-249`. I did not write or specify any of this change.

**What I ran.** Read-only calls inside the engineer's container `hrlocal-249`, site
`test249`, as a real staff login (`plain@l063.test`: roles Employee, Desk User; it has the
new own-record row). Every probe ran in a transaction that was rolled back. I called the
same whitelisted Frappe functions an HTTP request reaches, with the same parameters. I
did **not** send an HTTP request, did not touch dev or production, and changed no source.

No `01c-security-privacy-requirements.md` exists for this ticket (it is a bug fix), so
there are no SEC/PRIV numbers to trace. I judged it against the ticket's own goal: *a
staff login sees only its own Employee record, and only its own claims (ALV-261).*

---

## Bad news first

### 1. P0, Blocker: one extra word still opens every record, for every staff login

**This is live on production today, and this branch does not close it.** It is in Frappe
itself, not in our code.

- **What.** Frappe's list endpoints (`frappe.desk.reportview.get`, `get_list`,
  `get_count`) throw away a few dangerous parameters a caller sends, such as
  `ignore_permissions`. They do **not** throw away `ignore_user_permissions`. When a caller
  sends `ignore_user_permissions=1`, Frappe skips **every User Permission row**, which is
  the very thing this fix relies on.
  - Code: installed Frappe 16.33.1, `frappe/desk/reportview.py:24` (`DISALLOWED_PARAMS`)
    and `frappe/model/qb_query.py:59, 206` (the parameter is accepted and used).
  - Frappe's current `develop` branch has the same list (checked 31 Oct 2026). No
    upgrade fixes it.
- **Scenario (verified by running it).** A staff login, with the new row in place, calls
  `reportview.get_list` for Employee with `ignore_user_permissions=1`:

  | Asked for | Without the word | With the word |
  |---|---|---|
  | Employee: name, date of birth, mobile, personal email | 1 (own) | **191 of 191** |
  | Expense Claim: employee, amount | own only | **10 of 10** |
  | Attendance | own only | **28 of 28** |
  | Leave Application | own only | **all** |
  | Salary Structure Assignment: employee, **base pay** | 0 | **27 of 27** |
  | Employee count | 1 | **191** |

- **What still holds.** The HR-only fields (bank account, PAN, CTC: level 1, field rights
  ALV-215/075) stay hidden on this door, and filtering on them is refused (verified).
- **Who is affected.** Every tenant. Every login with the Employee role. It also defeats
  `manager_scope.py`'s rows and DTC's narrow per-doctype rows, not only this fix.
- **Blast radius.** Every person in the tenant. Not cross-tenant (each tenant is its own
  site).

### 2. P0, Blocker: link search has the same hole, by a second path

- **What.** Frappe's link search (`frappe.desk.search.search_widget`, whitelisted) accepts
  `ignore_user_permissions=1` when the caller names a form that has an Employee link
  marked "Ignore User Permissions". It only checks that such a field exists on that form
  (`frappe/desk/search.py:96-105, 295-307`). It does not check that the caller can use
  that form. It also accepts `filter_fields`, so the caller chooses the columns.
- **Ten such fields exist on this site** (verified by query), including ERPNext's own
  `Employee.reports_to`, `Serial No.employee` and `Employee Grievance.reports_to`.
- **Scenario (verified by running it).** The same staff login calls `search_widget` for
  Employee with `reference_doctype="Serial No"` (a form staff cannot even open),
  `link_fieldname="employee"`, `ignore_user_permissions=1` and
  `filter_fields=["date_of_birth","cell_number","personal_email"]`. It gets **191 of 191
  employees, with date of birth, mobile and personal email.** The same call without the
  word returns 1.

**Doors 1 and 2 mean ALV-249 and ALV-261 are not closed.** The branch narrows the doors
the ticket used, and that is still worth having. But nobody should tell DTC "fixed" until
both doors are shut.

**My recommendation (Surbhi decides).** One `before_request` line in our app that removes
`ignore_user_permissions` from every incoming request, next to the two hooks already in
`alvoraa_portal/hooks.py:26`. About five lines and a test that repeats the six calls
above. Rung 4: no setting closes a framework parameter. HR and System Managers lose
nothing, because they hold no row to ignore. The only cost: a staff or manager login
picking an "Ignore User Permissions" link in Desk sees its own tree, not everyone; staff
are sent to the portal anyway. Separately, report it to Frappe's security team.

### 3. P1, Major: new joiners made by the account script never get the row

- **What.** `demo/link_employee_users.py:66-85` inserts the User first, then links it with
  `frappe.db.set_value("Employee", ..., "user_id", ...)`. The User hook fires before the
  link exists, so it finds no Employee. `db.set_value` fires no hook. Result: no row.
- **Scenario (inference from code; not run).** After `run_once`, DTC adds 20 staff with
  this script. Those 20 logins have no row and list every colleague through every plain
  door, exactly as before the fix. Nothing alerts anyone.
- **Fails open.** The fix decays with the first new batch.
- **Fix options:** the script calls `own_record_permission.sync(email, emp.name)` after
  the link (one line), or `run_once` is re-run after every batch. Either way, the "logins
  due a row but without one" count from `run_once` is the only detector.

### 4. P2, Major: changing role permissions does not re-run the rule

- **What.** A login's row is decided only when its Employee or User is saved
  (`own_record_permission.py:91-104`). Roles that read Employee are exempt, worked out at
  that moment (`:45-49`).
- **Scenario (inference from code).** Someone removes Employee read from "Location
  Manager" in Role Permission Manager. The five Location Managers at DTC still have no
  row, now hold only the Employee role's read, and list every employee until someone
  saves their User or runs `run_once`. Fails open, silently.
- **The other direction fails closed** (a role gains Employee read; its holders keep a
  row and are limited). That is safe.
- **Fix:** re-run `run_once` after any Employee permission change; say so in the tenant
  setup rule in 06.

### 5. P2, Major: `rollback()` is only safe where no such rows existed before

- **What.** `rollback()` (`:213-221`) deletes every own-record row on every linked login.
  It cannot tell the rows `run_once` added from rows ERPNext made earlier (ERPNext makes
  the same shape when "Create User Permission" is ticked).
- **Scenario (verified the data shape).** On `test249`, 41 such rows existed before this
  branch. Running `rollback()` there removes all 41 and opens those 41 logins to every
  record. At DTC the count before was 0 (06), so it is safe there only.
- **Fix:** run it only where the dry run's "BEFORE own-record rows" was 0, and write that
  in the runbook. Or keep the list of names `run_once` added and delete only those.

---

## What the fix does close (with doors 1 and 2 still open)

All verified by running, as the staff login above, except where marked.

| Door | Result |
|---|---|
| `/api/resource/Employee` list, `reportview` with `reference_doctype` Employee, ToDo, Leave Application, Expense Claim, Attendance, `get_count` | Own record only (the engineer's tests; I re-ran the plain list: 1) |
| Link search without the extra word | 1 |
| `frappe.desk.form.load.getdoc` on a colleague | Refused |
| Print view of a colleague | Refused |
| `get_value` / `get_employee_field_property` on a colleague | Refused (`hrms/hr/utils.py:200` checks permission) |
| `get_leave_details` for a colleague | Refused |
| Global search for Employee | 0 (Frappe checks each hit, `global_search.py:534`) |
| Employee child tables (education, work history) | 0 outside own record (no data on the site; inconclusive) |
| Every doctype the Employee role reads that has data (Attendance, Checkin, Expense Claim, Leave Application, Leave Ledger, Salary Structure Assignment, Promotion, Transfer, Goals, KPI): rows about someone else | **0** in all of them |
| Reports the Employee role can open: Employee Birthday, Leave Balance (engineer's test), Leave Balance Summary, Shift Attendance | Own rows only |
| Salary, tax, appraisal, advance and ledger reports | Refused (no report right on the source doctype) |
| Export from Report view | Not run. Goes through the same list code, so closed without the extra word and **open with it** (inference) |
| Field rights (075): bank, PAN, CTC | Hidden on every door, including doors 1 and 2 |

**Real data shape.** These checks only mean something where data exists. On `test249`
there are no Salary Slips, no Employee child-table rows and no grooming marks, so "0"
there proves nothing. At DTC I could not check which of these hold data.

---

## What the fix does not close, rated

| # | What | Rating | Label |
|---|---|---|---|
| 6 | **Managers see their whole reporting tree** (D-2, accepted by Surbhi 31 Oct 2026). This is wider than "personal fields": it is every Employee field at levels 0 and 2 (date of birth, phone, address, passport, emergency contact), **and** every claim, leave, attendance record and Salary Structure Assignment **with base pay** of everyone below them, at any depth. The last one is inference: the Employee role reads Salary Structure Assignment on this site (verified); a tree row then covers it | P2, decision | Intentional trade-off, **if** Surbhi confirms D-2 covers pay and claims |
| 7 | HR roles unchanged by design. An HR User or HR Manager still sees every employee they did before | P4 | Intentional |
| 8 | *Employee Leave Balance* ignores Company permissions: an HR Manager limited to one company sees every company's balances (from 05; I did not re-run it) | P2 | Dangerous debt on multi-company tenants; harmless at DTC (one company). Own ticket |
| 9 | ERPNext's Company row. When a System Manager saves an Employee with "Create User Permission" ticked (all 430 at DTC), ERPNext also adds a Company row, all document types. It restricts, it never widens. On a multi-company tenant it would cut an HR person to one company | P3 | Acceptable simplification at DTC |
| 10 | Employee Self Service has **write** on Employee level 0 on this site (Custom DocPerm, verified). A manager holding ESS can change the phone, address or passport number of anyone in their tree by saving the record. Before this fix: of anyone at all. Inference from the permission rows; not run. I do not know whether any DTC login holds ESS | P2 | Needs a count at DTC |
| 11 | Frappe HR's org chart method (`hrms/hr/page/organizational_chart/organizational_chart.py:6`, whitelisted, uses `get_all`) gives any login the name, designation, photo and manager of every active employee (131 on this site, verified). The User list gives any Desk User the login email of every user (151) | P3 | Same data as the directory (slice 045 D-10). Note for questionnaires |
| 12 | Rows made by a direct database write (as in finding 3) are not caught until the next save or `run_once` | P1 via finding 3 | See finding 3 |

---

## New attack surface added by this branch

| Question | Answer | How I know |
|---|---|---|
| Can a user make the sync add or remove a row for someone else? | No in practice. The sync runs only when an Employee or User is saved. It applies the same rule whoever triggers it, and only for that record's own login. A staff login cannot save another Employee (no write) or another User (no write) | Verified in code, `own_record_permission.py:71-104`; permissions read on `test249` |
| Can a staff login widen its own tree by changing `reports_to`, `user_id`, `status` or `company`? | No. All four are level 2: only HR may write them (field rights). Roles on User are level 1: System Manager only. No portal endpoint writes `reports_to` or `user_id` (grep of `alvoraa_portal`, `alvoraa_hr_core`, `alvoraa_goals`) | Verified: field levels read from meta; grep |
| Can a staff login change a colleague's `reports_to`? | No, same reason. An HR User can, by design, and that save is kept in the Employee's version history | Verified (meta; Employee track_changes = 1) |
| Can the two `ignore_permissions` writes be reached by a non-Administrator? | Only through the two save hooks, and only to write or remove the exact row the rule demands. Pinned at 2 by `test_portal_security_010` | Verified in code |
| `run_once` / `rollback` | Not whitelisted, so not callable over HTTP. Both refuse anyone but Administrator. `bench execute` runs as Administrator | Verified in code `:155, :215`; engineer's test |
| SQL or injection | None. ORM calls with dict filters only | Verified in code |
| Error text | Only "Run as Administrator." No personal data | Verified in code |
| Audit trail | An added row carries who triggered it and when (`owner`, `creation`); Frappe keeps no version on insert (0 versions for User Permission on `test249`). A removed row is copied to Deleted Document with who and when (285 there). The save that caused it is in the Employee or User history. **The reason is not recorded** | Verified by query |
| Console output | `run_once` prints login emails and employee IDs. Keep that output out of tickets, chat and git | Verified in code |

---

## The DPDP angle (advice, not a legal opinion)

I am not a lawyer. This section prepares the questions; counsel answers them.

**The facts, as far as I know them:**

- From the day staff logins were created at DTC until this fix runs, any staff login
  could read every colleague's date of birth, phone, personal email, address, emergency
  contact, passport number and leave balance, and every expense claim. (04, 05.)
- **Doors 1 and 2 keep that true after the fix**, for anyone who knows the extra word, on
  every tenant, until they are closed. It also covers base pay where Salary Structure
  Assignments exist.
- **Nobody can show who looked.** Frappe does not log list reads. Its Access Log covers
  exports and prints only. nginx logs show the address of GET requests (so a GET with
  `ignore_user_permissions` in it would show), but not the body of POST requests. I do not
  know how long the server keeps nginx logs.
- Obligations engaged (baseline, verified 24 Aug 2026, 68 days old, so still current):
  DPDP's reasonable security safeguards and breach intimation (immediate notice to the
  people and the Board, detailed report within 72 hours); CERT-In's 6-hour report for
  unauthorised access, counted from awareness. The baseline says DPDP's duties phase in
  fully around May 2027; the exact phase dates are still a counsel question.

**What I advise telling DTC's owner or DPO, in writing, once counsel agrees the wording:**
what data was open, to whom (all staff logins), since when, that no record can show
whether anyone used it, what has been fixed and on what date, and what remains open
(doors 1 and 2) until a named date.

**Do now, whatever counsel says:** copy and keep the production nginx access logs before
they rotate. They are the only evidence of who used these doors.

**Questions for counsel:**

| # | Question | What it blocks |
|---|---|---|
| C1 | Does access that was *possible* but not shown to have happened count as a personal data breach under DPDP, and does it need intimation? | Whether DTC must notify staff and the Board |
| C2 | Did the DPDP or CERT-In clock start, and when: at ALV-249's discovery, or today (31 Oct 2026) for doors 1 and 2? | Whether a report is already late |
| C3 | Who notifies: DTC as the employer, us as the processor, or both? What must we send DTC, and by when? | The letter to DTC |
| C4 | Is a manager reading the whole tree's personal data and pay (finding 6) consistent with purpose limitation for DTC's staff? | Whether D-2 stands as accepted |

---

## What Surbhi must decide or accept

1. **Doors 1 and 2 (P0).** Approve a fix before ALV-249 goes anywhere. My recommendation:
   the `before_request` line described above, built and tested with this branch, so
   ALV-249, ALV-261 and the two doors ship together. Production is exposed now, so this
   is urgent. Also decide whether we report it to Frappe.
2. **Do not call ALV-249 or ALV-261 closed**, to DTC or in YouTrack, until doors 1 and 2
   are shut on production.
3. **New joiners (P1).** Choose: add one `sync` line to the account script, or re-run
   `run_once` after every batch. Without one of them the fix wears off.
4. **D-2 scope (P2).** Confirm that "managers see their tree" includes the tree's claims,
   leave, attendance and base pay, not only their personal fields. If not, tick "hide
   descendants" (untested for goals and KPIs, per 05).
5. **Rollback (P2).** Accept that `rollback()` is safe only where the dry run showed 0
   rows before, or ask for it to remove only what `run_once` added.
6. **Role permission changes (P2).** Accept that `run_once` must be re-run after any change
   to who reads Employee, and add that to the tenant setup rule.
7. **Read-only counts at DTC (needs your approval to run on production):** logins holding
   Employee Self Service; Salary Structure Assignments; roles that read Employee.
8. **DPDP (C1-C4).** Send the four questions to counsel, keep the nginx logs, and decide
   what DTC is told and when.
9. **Accept in writing, with your name and a date,** each item left open: 6, 8, 9, 10, 11.

---

## Residual risk

| Risk | Rating | Owner | Accepted |
|---|---|---|---|
| Doors 1 and 2: every record open with one extra word | P0 | Surbhi (decision), full-stack engineer (fix) | **Not accepted. Must not be.** |
| New joiners without the row (finding 3) | P1 | Surbhi | Open |
| Managers read the whole tree, including pay and claims | P2 | Surbhi | D-2 accepted 31 Oct 2026 for personal fields; pay and claims not yet confirmed |
| Role permission drift; rollback scope | P2 | Surbhi | Open |
| Leave Balance report and multi-company HR | P2 | Surbhi | Open; own ticket |
| ESS write on the tree | P2 | Surbhi | Open until the DTC count |
| Org chart names and login emails visible to all | P3 | Surbhi | By design (D-10); confirm |
| No record of past reads | Fact, not fixable | Counsel | For C1-C3 |

## What I could not check

- Production's Frappe version, and whether DTC holds Salary Structure Assignments, ESS
  holders or private Employee files. Needs a read-only count on production, with your
  approval.
- The doors over real HTTP. I called the same whitelisted functions with the same
  parameters; a browser-based request was not sent.
- Portal writes with the row in place (06 lists them for dev).
- How long production keeps nginx logs.

## Subtract pass

Removed from my draft: a full STRIDE table (the four questions are answered inside the
findings), a list of every Employee field by sensitivity class (04 already has it), and a
second fix option for doors 1 and 2 (a per-endpoint override). One request-level line does
the same job in fewer places.
