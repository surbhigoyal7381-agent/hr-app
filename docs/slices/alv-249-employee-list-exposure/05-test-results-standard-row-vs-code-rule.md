# ALV-249 · Test results: the standard own-record row (A-prime) next to the code rule (B)

Run 31 Oct 2026 on my own local site only: container `hrlocal-249`, site `test249`, a copy
of slice 076 C's test site, with apps mounted from this worktree (`origin/dev` d3afcaa5),
then migrated. **Nothing pushed. Dev and production not touched. No SSH.**

**This file replaces the recommendation in `04-impact-and-strategy.md`.** The test showed
the standard row does more than I expected, and showed one fault in my own option B.

---

## Bad news first

1. **The hole is real, and it is reproduced.** A staff login with only the Employee role
   and no own-record row lists every Employee on the site (191 of 191), with date of birth,
   mobile, personal email, home address and passport number, through every door tested.
2. **It is wider than Employee.** On the same login, *Employee Birthday* returns every
   birthday in the company, *Employee Leave Balance* returns **190 people's leave
   balances**, and the login can list **all 27 expense claims and has write right on other
   people's claims** (ALV-261).
3. **My option B, as I wrote it in 04, had a fault.** It worked out who was HR from the
   site's permission rows, and on this site System Manager has no read row on Employee. So B
   cut the System Manager down to their own record: the attendance review picker fell from
   185 to 1. Fixed in the prototype by exempting System Manager by name; a real build would
   need that line and a test for it.
4. **Option B does not close the two reports' birthday leak or the expense claims.**
   Measured: *Employee Birthday* still 9 rows, expense claims still 27 with write.
5. **The standard row lets a manager see their whole reporting tree.** Employee is a tree in
   Frappe, and an own-record row also covers everyone below that person, unless "hide
   descendants" is ticked. Manager M1 lists 5 records (self + 4 reports) with their
   personal fields. That is far narrower than today's 191, and it is how ERPNext is meant to
   work, but it is a choice for Surbhi (Q1 below).
6. **Some flows are not proven yet.** I could not test portal writes (apply leave, file a
   claim, upward feedback, grooming, driver portal) on this site: the fixture has no leave
   allocations. Those go on the dev test list before production.

---

## 1. The local site (DTC shape)

| Login | Roles | User Permission rows |
|---|---|---|
| s1, s2, s4, s5, s6 | Employee | none |
| s3 | Employee, Leave Approver | none |
| m1 | Employee; 4 people report to m1 | 16 narrow rows from `manager_scope` (4 people × Attendance, Employee Checkin, Attendance Request, Leave Application) |
| h1 | Employee, HR Manager | Company, all document types |
| sm | Employee, System Manager | none |

Site totals: 191 Employee records (19 in h1's company), 27 expense claims, none belonging to
the fixture people. Every fixture employee has a date of birth, mobile, personal email,
address and passport number filled in. `apply_strict_user_permissions` = 0, as Frappe ships.

The probe calls the real Frappe functions as each user (`frappe.set_user`):
`frappe.client.get_list` (what `/api/resource` calls), `frappe.desk.reportview.execute` (what
`reportview.get` calls) with five different `reference_doctype` values, `reportview.get_count`,
`frappe.has_permission` on one record, `frappe.client.get_value`, `frappe.desk.search.search_link`,
`frappe.desk.query_report.run`, `hrms.api.get_all_employees`, and the portal endpoints that
read colleagues. Everything ran inside a transaction that was rolled back. The scripts are
in the scratchpad, not in the repo.

---

## 2. Results

Numbers are rows returned. "refused" means Frappe raised a permission error.

| Check | Today: s1 / s3 / m1 / h1 / sm | **A-prime** (standard row): s1 / s3 / m1 / h1 / sm | **B** (code rule, SM fixed): s1 / s3 / m1 / h1 / sm |
|---|---|---|---|
| `/api/resource/Employee` list | 191 / 191 / 191 / 19 / 191 | **1 / 1 / 5** / 19 / 191 | **1 / 1 / 1** / 19 / 191 |
| reportview, ref = Employee | 191 / 191 / 191 / 19 / 191 | 1 / 1 / 5 / 19 / 191 | 1 / 1 / 1 / 19 / 191 |
| reportview, ref = **ToDo** (the extra-word test) | 191 / 191 / 191 / 19 / 191 | **1 / 1 / 5** / 19 / 191 | **1 / 1 / 1** / 19 / 191 |
| reportview, ref = Leave Application | 191 / 191 / 4 / 19 / 191 | 1 / 1 / 5 / 19 / 191 | 1 / 1 / 0 / 19 / 191 |
| reportview, ref = Expense Claim | 191 / 191 / 191 / 19 / 191 | 1 / 1 / 5 / 19 / 191 | 1 / 1 / 1 / 19 / 191 |
| reportview, ref = Attendance | 191 / 191 / 4 / 19 / 191 | 1 / 1 / 5 / 19 / 191 | 1 / 1 / 0 / 19 / 191 |
| `get_count`, ref = ToDo | 191 / 191 / 191 / 19 / 191 | 1 / 1 / 5 / 19 / 191 | 1 / 1 / 1 / 19 / 191 |
| Read a colleague's record | yes for all | **no / no / no** / yes / yes | **no / no / no** / yes / yes |
| Read own record | yes for all | yes for all | yes for all |
| `get_value` colleague's DOB | value for all | **empty / empty / empty** / value / value | **empty / empty / empty** / value / value |
| Link search, ref = Leave Application | 191 / 191 / 4 / 19 / 191 | 1 / 1 / 5 / 19 / 191 | 1 / 1 / 0 / 19 / 191 |
| Link search, ref = Attendance Request | 191 / 191 / 4 / 19 / 191 | 1 / 1 / 5 / 19 / 191 | 1 / 1 / 0 / 19 / 191 |
| Report *Employee Birthday* (Oct, h1's company) | 9 / 9 / 9 / 9 / 9 | **1 / 1 / 5** / 9 / 9 | **9 / 9 / 9** / 9 / 9 (still open) |
| Report *Employee Leave Balance* | 190 / 190 / 190 / 190 / 190 | **refused ×3** / 190 / 190 | **refused ×3** / 190 / refused before the SM fix, not re-checked after |
| Report *Employee Analytics* | 17 for all | 1 / 1 / 5 / 17 / 17 | 1 / 1 / 1 / 17 / 17 |
| `hrms.api.get_all_employees` (`/hrms` app) | 191 / 191 / 191 / 19 / 191 | 1 / 1 / 5 / 19 / 191 | 1 / 1 / 1 / 19 / 191 |
| **Expense Claim list** (ALV-261) | 27 / 27 / 27 / 0 / 27 | **0 / 0 / 0** / 0 / 27 | **27 / 27 / 27** / 0 / 27 (still open) |
| **Write right on someone else's claim** | yes / yes / yes / no / yes | **no / no / no** / no / yes | **yes / yes / yes** / no / yes (still open) |
| Claim shared to me as approver: read, submit | yes, yes for all | yes, yes for all | yes, yes for all |
| Portal: org chart `my_view` | works | works, same | works, same |
| Portal: org search "A249" | 1 / 1 / 5 / 9 / 9 | same | same |
| Portal: team dashboard | team 0 / 0 / 4 / 17 / 0 | same | same |
| Portal: review picker | 0 / 0 / 4 / 18 / 185 | same | same (185 → 1 before the SM fix) |
| Portal: inbox, pending approvals, attendance calendar | works | same | same |
| Portal: birthdays | switch off on this site | same | same |
| Portal: directory, notice people | refused for everyone on this site (plan gate) | same | same |

### What the numbers mean

- **A-prime closes every door I tested for staff**, including the extra-word test. A row of
  the "all document types" kind is never skipped, whatever `reference_doctype` says.
- **A-prime also closes the birthday report, the leave balance report and expense claims**,
  because Frappe applies the same row to those reports' rows and to every document that
  links to Employee. B does not.
- **An approver still sees what is shared with them.** Frappe HR shares a claim or leave with
  its approver, and that share still gives read and submit with the row in place.
- **The manager (m1) keeps their team** in the Leave Application and Attendance pickers (5 =
  self + 4). Under B the same manager gets **0** in those pickers, not even themselves,
  because B's "own record only" and the manager's narrow rows cancel each other out.
- **No portal screen I could call changed** under either option.
- HR (h1) and System Manager (sm) are unchanged under A-prime, because they get no row.

### Side finding, not this ticket

*Employee Leave Balance* shows h1, an HR Manager limited to one company, **190 rows across
all companies**. The report ignores the Company permission. That is a multi-company HR leak
for a separate ticket; DTC has one company, so it does not bite there today.

---

## 3. Recommendation (changed from 04)

**Use the standard own-record row (A-prime), kept correct by one small sync function.**
It closes ALV-249 and ALV-261 together, with the mechanism ERPNext already uses, and the
test shows nothing in the portal lost.

| | A-prime + sync | B + Custom Role for the reports |
|---|---|---|
| Employee list, all doors | Closed | Closed |
| Birthday report | Closed | Needs the Custom Role too |
| Leave balance report | Closed | Closed |
| Expense claims (ALV-261) | **Closed** | **Open**, needs its own fix |
| Manager pickers | Self + team | Broken (0) |
| Data change at DTC | ~420 rows | None |
| Code | One sync function, two hook lines | One rule, two hook lines, a fixture |
| Fails how | A missed login stays open (the counts below catch it) | A missed role is cut off (the SM fault) |

**Ladder.** Rung 2 (a standard User Permission row, ERPNext's own design) plus rung 4 (a
hook so it stays right). Rung 1 was rejected because ERPNext only creates the row when the
Employee is saved through its controller, and our account script uses `frappe.db.set_value`.
It would also create the row for HR people, which is the ALV-226 trap.

### Q1 for Surbhi: should a manager see their whole reporting tree?

- **Default (Frappe's standard, "hide descendants" off):** a manager reads the Employee
  records of everyone below them, personal fields included, and every document of theirs
  that links to Employee. Goals, KPIs and appraisals of the team keep working.
- **"Hide descendants" on:** a manager reads only their own Employee record. Their team
  stays reachable on the four `manager_scope` doctypes, plus Expense Claim and PMS where DTC
  added rows. **Not tested:** team goals and KPIs may go missing for managers.
- **My recommendation: the default.** It is what ERPNext intends and narrows 597 to the
  manager's own tree. Tick "hide descendants" later if Surbhi wants managers not to see
  their team's dates of birth.

---

## 4. Who gets the row, and who never does

### The exclusion list, and how it is computed

```text
readers  = roles with read on Employee at level 0
           (Custom DocPerm if Employee has any, else DocPerm)
excluded = (readers - {"Employee", "Employee Self Service"}) + {"System Manager", "Administrator"}
```

On this site that gives **Administrator, HR Manager, HR User, System Manager**. System
Manager is added by name because, as the B test showed, it may have no read row of its own.
**A login holding any excluded role gets no row**, and any row it has is removed. This is
exactly the ALV-226 lesson: no HR or admin login ever carries this row.

**Before running at DTC, Surbhi reads two lists:**

- the excluded roles, as computed on DTC;
- every login that **will** get the row but holds a role other than Employee, Employee Self
  Service, Leave Approver or Expense Approver. An accountant or a payroll clerk would show
  up here and can be decided one by one.

### New joiners, role changes, leavers

One function, `sync_own_record_permission(user)`, in a new small file in `alvoraa_portal`:

- **The row should exist** when the login is enabled, is linked to an Active Employee, and
  holds no excluded role.
- **Otherwise it should not exist.** That includes removing the row ERPNext's own controller
  adds for an HR person, because `create_user_permission` is 1 on all 430 DTC employees.
- It is called from the Employee `on_update` hook (`user_id` or status changed) and from the
  User `on_update` hook (roles changed: a staff member promoted to HR loses the row on the
  same save). `module_access` already hangs off User this way.
- It is safe to run twice. It touches only rows of this exact shape: allow Employee,
  `for_value` = that person's own Employee, all document types.

**Not chosen: fixing the account script.** It covers new accounts only, not role changes.
The script can keep using `set_value`, because the hook catches the save that links the
login. If the script never triggers a save, the after-count below shows the gap.

---

## 5. The production step (separate, needs Surbhi's word)

Order: code reaches dev → tested there → main → production deploy → this data step, run
once by calling the same sync function for every login.

### Before (read-only), every number written down

| # | Count | Expected at DTC |
|---|---|---|
| B1 | Logins that will get the row: enabled, Active Employee, no excluded role | about 420; record the exact number as **N** |
| B2 | Own-record "all document types" rows that exist now | 0 (31 Oct fact) |
| B3 | Such rows on any excluded login | 0 |
| B4 | As 3 named staff logins: Employee `get_list` count, Expense Claim `get_list` count | 597 each; all claims |
| B5 | As each HR and System Manager login: Employee count, Expense Claim count | record each |
| B6 | For each of the 3 staff: 1 + people below them in the tree (from `lft`/`rgt`), and claims whose employee is in that set | record; these are the after targets |

### After, each line prints PASS or FAIL against a number worked out separately

| # | Check | Pass only if |
|---|---|---|
| A1 | Own-record rows | **= N exactly** (not "about") |
| A2 | Rows on excluded logins | **= 0** |
| A3 | Each of the 3 staff: Employee count, normal and with `reference_doctype=ToDo` | = their B6 number |
| A4 | Each of the 3 staff: Expense Claim count | = their B6 claim number |
| A5 | Each HR / SM login: Employee and claim counts | **= their B5 numbers exactly**; any change is a stop and a rollback |
| A6 | Logins in B1 still without a row | = 0, listed by name if not |

A1, A3, A4 and A6 can each fail on their own, so a dropped login cannot hide behind the
total. This is the lesson from 26 Oct.

### Rollback

Delete the User Permission rows with allow Employee, all document types, `for_value` = the
user's own Employee, for the B1 logins. B2 showed there were none before, so this removes
exactly what was added. Then revert the code commit. Re-run A5 to confirm HR is as before.

---

## 6. Still to prove on dev, before production

- Portal writes as staff and manager: apply leave and approve; file a claim and decide it;
  attendance request for a team member; upward feedback (it links `about_employee`); grooming
  marks; notices acknowledgement; field check-in.
- The driver portal and delivery doctypes (`Delivery Partner.reporting_manager`,
  `Delivery Assignment.driver`) if any DTC login uses them.
- Team goals, KPIs and appraisal screens for a manager, under both Q1 answers.
- A staff login filing their **own** expense claim still sees it. Logic says yes; this
  fixture had no own claims.
- Full suites once at the end: `alvoraa_portal`, `hrms`, `alvoraa_goals`.

## What I ran

- Created my own container `hrlocal-249`, its redis `hrlocal-249-redis` and volume
  `hrlocal-249-sites`. Created site `test249` from a database dump of `test076c` (read-only
  dump) and migrated it. No other container or site was written to.
- One fixture script, committed on `test249` only: 9 users and employees, one Company row
  for h1. `manager_scope` made m1's 16 rows by itself when the reports were saved.
- The A-prime rows were added for 7 logins, probed, then removed again (7 removed); cache
  cleared on `test249` only.
- B was tested by adding the two hook entries in the probe process only. No product file
  was changed.
- The container is left running for re-runs. Stop it with `docker stop hrlocal-249 hrlocal-249-redis`.
