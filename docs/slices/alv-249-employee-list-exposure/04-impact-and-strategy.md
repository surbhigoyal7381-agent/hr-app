# ALV-249 · Staff can list every employee · impact analysis and strategy

Status: **proposal only. No code written, nothing pushed, no dev or production data touched.**
Written 31 Oct 2026 by the full-stack engineer, on `origin/dev` d3afcaa5, in worktree
`.claude/worktrees/alv-249` (branch `slice/alv-249-employee-list-exposure`).

> **Superseded in part, 31 Oct 2026.** `05-test-results-standard-row-vs-code-rule.md`
> tested the standard own-record row (A-prime) next to option B. The recommendation is now
> **A-prime plus a sync hook**, not B: it also closes the two reports and expense claims
> (ALV-261), and B as written here cut off the System Manager. Read 05 first.

---

## Bad news first

1. **Option A, as chosen, does not close the hole.** A User Permission that applies only to
   Employee is skipped when the caller adds one extra parameter, `reference_doctype`, to
   Frappe's list call. Any staff login can still get all 597 rows that way. I found this by
   reading Frappe's code (section 1.3). I have **not** run it yet; it is the first test in
   section 4. The only User Permission shape that cannot be skipped is the "all document
   types" shape, and that is the shape DTC deliberately does not use.
2. **It is worse than dates of birth.** The fields a plain staff login can read include
   mobile number, personal email, home address, emergency contact name and phone, blood
   group, marital status, passport number and health details. Only bank, PAN, PF, ESI and
   salary are hidden (level 1, HR Manager only). This is from the code; whether DTC has
   those fields filled in I could not check.
3. **Two standard reports leak the same data by a second door.** Frappe HR's
   *Employee Birthday* report (every active employee's date of birth, gender, branch for a
   company) and *Employee Leave Balance* (everyone's leave balance) both allow the Employee
   role and read the table with **no permission check at all**. No row rule on Employee
   touches them. They must be closed in the same change or the fix is cosmetic.
4. **A second, related hole stays open:** the Employee role can read and write every
   Expense Claim at DTC unless the login has a permission row for Expense Claim (076 C,
   Escalation 1). Not part of this ticket. It needs its own count and ticket.

**My recommendation is to switch from option A to a small code rule (option B, below),
plus one configuration change for the two reports.** It closes every door I found, needs
no change to any of the 427 logins, works for new joiners with nothing to remember, and
rolls back by reverting one commit. Surbhi decides.

---

## 1. Why the hole exists

### 1.1 Frappe gives the Employee role read on every Employee row

- ERPNext's Employee DocType grants the **Employee** role `read`, `report`, `print`,
  `email` with no "only if owner" limit (installed `erpnext/setup/doctype/employee/employee.json`,
  permissions block; ERPNext v16.34.2, Frappe v16.33.1).
- ERPNext expects each login to be narrowed by a User Permission on its own Employee
  record, created when "Create User Permission" is ticked on the Employee
  (`erpnext/setup/doctype/employee/employee.py:197-210`). That row is the **all document
  types** kind. DTC does not use it, on purpose (memory note `dtc-user-permission-pattern`):
  such a row restricts the person on every document type, which cut HR people off on 25 Oct.
- So at DTC ~420 staff logins have **no** Employee User Permission, and Frappe applies no
  row limit to them.

### 1.2 Nothing in our apps puts a row rule on Employee

- No `permission_query_conditions` or `has_permission` entry for Employee exists in any of
  our three apps on `origin/dev`:
  `hrms/hrms/hooks.py:155-185`, `alvoraa_portal/alvoraa_portal/hooks.py:405-429`,
  `alvoraa_goals/alvoraa_goals/hooks.py:57-80`. ERPNext's `hooks.py` has none either (only
  `has_upload_permission`, line 309).
- **Field rights (ALV-215) are a write lock, not a read lock.**
  `alvoraa_portal/employee_field_rights.py:9-14` says it: level 2 (job, identity, date of
  birth) is written by HR only, but "every role that reads Employee also reads these".
  Lines 73-79 add a level-2 **read** row for every role that reads level 0, Employee
  included. Personal contact fields stay at level 0. Only the 13 level-1 fields (bank, IDs,
  salary, `employee_field_rights.py:46-50`) are HR Manager only.
- **`permitted_employee_filters` / `employee_in_scope` are not wired to Frappe.**
  (`hrms/hrms/alvoraa_hr_core/access.py:252-299`.) They are helpers our own endpoints call.
  They return "nobody" for a plain employee, but only when our code asks. Frappe's own list
  API, REST API, report view and link search never call them.

### 1.3 Why a narrow User Permission (option A) can be skipped

- When Frappe lists Employee it looks at each Employee User Permission. A row with
  `applicable_for = "Employee"` is counted only when the caller's `reference_doctype` is
  Employee or empty. If the caller names any other doctype, the row is skipped and no
  limit is applied: `frappe/database/query.py:1490-1505` (v16 engine; the older engine has
  the same lines at `frappe/model/db_query.py:1129-1143`).
- The caller chooses `reference_doctype`. `frappe.desk.reportview.get` and `get_count` pass
  every request parameter through; only `cmd, data, ignore_permissions, view, user,
  csrf_token, join` are removed (`frappe/desk/reportview.py:24`, `:105`;
  `frappe/model/qb_query.py:52, 209`).
- So: `POST /api/method/frappe.desk.reportview.get` with `doctype=Employee`,
  `fields=["name","date_of_birth","cell_number"]`, `reference_doctype=ToDo` returns every row
  for a login whose only Employee permission is the narrow Employee kind. **Inference from
  code, to be proven in test D2 below.**
- The plain REST list (`/api/resource/Employee`) does not pass `reference_doctype`
  (`frappe/api/v1.py:12-32`, `frappe/client.py:27-40`), so option A would stop that one
  door, which is the one the ticket used. That is why it would look fixed.

### 1.4 How managers get access today

- `alvoraa_portal/manager_scope.py` gives each manager one **narrow** User Permission per
  direct report, for four doctypes: Attendance, Employee Checkin, Attendance Request,
  Leave Application. Employee is left off on purpose (docstring: it "would additionally
  expose date of birth"). It is kept in step by the Employee `on_update` hook
  (`hooks.py:187-188`) and `after_migrate` (`hooks.py:529`).
- DTC's 7 users with 416 rows also have rows for Expense Claim and PMS doctypes. Those did
  not come from `manager_scope.py`; someone added them. I did not find their source.
- None of those rows apply to Employee. **So today managers also see all 597 rows**, like
  everyone else.
- The portal's team screens do **not** depend on that: they read the team with
  `frappe.get_all` after their own reporting-line check (for example
  `attendance_correction.py:368-380`).

### 1.5 What reads colleagues' Employee rows through the permission layer

I grepped every caller of `frappe.get_list("Employee"...)`, `has_permission("Employee"...)`,
and every portal JS call to a generic Frappe API.

| Caller | Who calls it | Effect of a staff-only row rule |
|---|---|---|
| Portal JS (`public/js/ess/*.js`, `www/*`) | everyone | **None.** No generic API call on Employee. Every screen goes through our endpoints |
| Org chart, directory (`staff_api`), birthdays (`home_people`), team, notices audience, leave calendar, mentions | everyone | **None.** All read with `frappe.get_all` or the query builder after their own scope check |
| `attendance_correction.whose_months_i_can_open` (`:360`) | only users who may submit Attendance Request (HR) | None (HR exempt) |
| `hr_api` HR analytics (`:898`, `:932`), salary workings report (`:108`) | HR | None (HR exempt) |
| `field_app_alerts.py:62`, `field_app_desk.py:100` | HR Managers / HR | None (HR exempt) |
| Frappe HR's own PWA `/hrms`, `hrms.api.get_all_employees` (`hrms/api/__init__.py:63`) | anyone who opens `/hrms` | Shows only their own record. Names of colleagues in that app would show as IDs. I do not know if DTC uses `/hrms`; our portal is `/hrms-employee` |
| Desk: Employee list, link pickers ("Employee" field on any form), report builder | staff and managers, if they open Desk | Only their own record. A manager raising an Attendance Request **in Desk** for a report could not pick them. The portal path is unaffected |
| *Employee Analytics*, *Employee Leave Balance Summary* reports | Employee role | Rows narrowed to own record (they use `get_list`) |
| *Employee Birthday*, *Employee Leave Balance* reports | Employee role | **Not touched by any row rule** (raw query builder, `hrms/hr/report/employee_birthday/employee_birthday.py:39-56`, `employee_leave_balance.py:139-157`) |

---

## 2. Options on the ladder

| | A · narrow User Permission per login (chosen) | A3 · "all document types" User Permission per login (ERPNext default) | **B · code rule on Employee (recommended)** | C · raise personal fields to an HR-only level |
|---|---|---|---|---|
| Rung | 2 data + 4 code (a hook for new joiners) | 2 data + 4 code | 4 (customisation via hooks) | 2 config |
| Closes REST list | Yes | Yes | Yes | Fields only |
| Closes `reportview.get` + `reference_doctype` | **No** | Yes | Yes | Fields only |
| Closes link search, `get_count`, `get_value`, single record | Partly (link search shows names) | Yes | Yes | Fields only |
| Closes the two raw reports | No | No | No | No (they bypass levels too) |
| Survives new joiners | Only with a new hook on Employee / User | Only with a hook (or the ERPNext tick) | **Yes, by itself** | Yes |
| Changes live data | ~420 rows written at DTC | ~420 rows | **None** | Property Setters |
| What it breaks | Nothing visible | **Every** doctype that links Employee is cut to own record: an approver who is not a manager loses claims and leave they approve; breaks DTC's deliberate pattern; memory note says never | Desk pickers for non-HR (own record only); `/hrms` PWA names | Employee loses read of their **own** personal fields through Frappe; colleague names, titles, departments, phone still listed |
| Rollback | Delete the rows (needs a reliable marker; User Permission has none) | Same | Revert one commit | Remove Property Setters |
| Cost | Script + hook + tests | Same | ~30 lines + tests | Small, but does not meet the requirement |

**Rejected, and why:**

- **Rung 1 (already there):** nothing in Frappe, ERPNext or Frappe HR limits Employee rows
  except User Permissions. Checked.
- **A:** leaves the `reference_doctype` door open, writes 420 rows to live data, and still
  needs code for new joiners. It costs more than B and does less.
- **A3:** closes the hole but restricts staff on every document type. That is exactly what
  the memory note forbids, and it changes approval behaviour we have not mapped.
- **C:** hides some fields but still hands out the whole staff list with phone numbers
  unless every contact field is raised too, and then employees cannot read their own.

### Recommendation: option B, plus one config change

**B1 · A row rule on Employee, same pattern as ALV-117's feedback rule**
(`hrms/hrms/alvoraa_hr_core/feedback_access.py`, hooked at `hrms/hrms/hooks.py:167, 182`).

- One new file `hrms/hrms/alvoraa_hr_core/employee_access.py` with two functions:
  - `employee_query_conditions(user)`: returns `""` (no extra limit, Frappe's own rules
    and User Permissions still apply) when the user is Administrator or holds **any role
    other than Employee / Employee Self Service that is granted read on Employee** in the
    site's permissions (read from `frappe.get_meta("Employee").permissions`, so HR User,
    HR Manager, System Manager, and any role a tenant grants on purpose in Role Permission
    Manager keep what they have today). For everyone else it returns
    `` `tabEmployee`.`user_id` = <escaped user> ``: their own record only.
  - `has_employee_permission(doc, ptype, user)`: the same test for one record. Returns
    `True` explicitly when allowed. **Frappe v16 treats `None` as a refusal**
    (`frappe/permissions.py:494-498`), so this must never fall through.
- Two lines in `hrms/hrms/hooks.py`: one in `permission_query_conditions`, one in
  `has_permission`.
- No query added: roles and meta are already cached for the request. The condition is one
  equality on a 600-row table.
- Both Frappe query engines call the hook (`frappe/database/query.py:1593, 1619-1643`), and
  it is applied whatever `reference_doctype` says.
- New joiners: nothing to do. The rule reads `user_id` at query time.

**B2 · Close the two raw reports by configuration** (rung 2).

- A **Custom Role** record for *Employee Birthday* and one for *Employee Leave Balance*,
  listing HR User and HR Manager only. Frappe uses Custom Role instead of the report's own
  roles when one exists (`frappe/core/doctype/report/report.py:140-154`).
- Shipped as a fixture in `hrms/hrms/hooks.py` (next to the existing Workflow fixture,
  line 150) so new tenants and every migrate get it.

**Open question for Surbhi (Q1): should a manager also see their direct reports' Employee
records through Frappe?**

- Why it matters: only for Desk. In Desk, a manager picking a report on an Attendance
  Request form would see only themselves. The portal is unaffected either way.
- It changes one line in `employee_query_conditions`: add `or name in (the manager's
  existing Employee User Permissions)`.
- **My default: no.** Own record only. That matches `manager_scope.py`'s own reasoning
  (team DOB is not needed), and it fails closed. If a manager complains about a Desk
  picker, we add the line.

**Question Q2: who else reads Employee at DTC today?** The rule exempts any role with read
on Employee other than Employee itself. The production before-count (section 4.3) lists
those roles so Surbhi sees exactly who keeps full access before anything changes.

---

## 3. Impact

### 3.1 Personas

| Persona | Before | After (B) |
|---|---|---|
| CXO / System Manager | All employees | Unchanged |
| HR Manager / HR User | Their companies (Company permission) or all | Unchanged |
| Manager (the 7) | **All 597, including DOB and contacts** | Own record through Frappe. Portal team screens unchanged |
| Employee | **All 597** | Own record only. Directory, birthdays card, org chart unchanged (our endpoints, fixed fields) |

### 3.2 Modules

- `alvoraa_goals`, `alvoraa_portal`, `erpnext`: no code change. Their Employee reads are
  `get_all` or HR-only `get_list`.
- `hrms`: two hook lines, one new file, one fixture. Leave, attendance, payroll,
  appraisals, org structure: no change to how their documents are permitted; the rule is
  on the Employee doctype only, not on documents that link to it.

### 3.3 Non-functional dimensions

| Dimension | Verdict | Why |
|---|---|---|
| Performance | Neutral | No added query. One equality condition |
| Security | **Improves** | Closes REST list, report view (with or without `reference_doctype`), count, link search, single-record read, and the two raw reports |
| Reliability | Neutral, one risk | The risk is a screen that silently relied on reading colleagues through Frappe. My grep found none in the portal; the full test suites and the walk-through in section 4 are the check |
| Scalability | Neutral | Same cost at 600 or 6,000 employees |
| Maintainability | Neutral | Same shape as `feedback_access.py`; no list of roles to keep up to date |
| Data integrity | Neutral | Reads only. No data written. No cache |
| Compliance / privacy | **Improves** | DPDP purpose limitation: a colleague's DOB, phone, address, emergency contact, blood group and passport number are no longer handed to every login. Fails closed: an unknown role is restricted |

### 3.4 Parallel-work check

| File | Others in it | Plan |
|---|---|---|
| `hrms/hrms/hooks.py` (hot file) | Last changed by slice 065 (`cf5d1702`). Work board: `alv-178` holds unpushed edits to other blocks of it | Append one line at the end of each of the two dicts and one fixture line. Rebase on `origin/dev` before commit |
| NEW `hrms/hrms/alvoraa_hr_core/employee_access.py` | Nobody | New file, on purpose: the main checkout has someone's uncommitted edits in `access.py` |
| NEW fixture `hrms/hrms/fixtures/custom_role.json` | Nobody | New file |
| NEW test `hrms/hrms/alvoraa_hr_core/tests/test_employee_access_alv249.py` | Nobody | New file. It names ALV-249, so a bad merge that drops the hook fails CI |

---

## 4. Test plan

### 4.1 Local first (own container, own site, never `hrlocal-bench`)

Fixture logins on a DTC-shaped site:

| Login | Roles | User Permissions |
|---|---|---|
| S1, S2 | Employee only | none (the DTC staff shape) |
| S3 | Employee + Leave Approver | none |
| M1 | Employee (manager of 3) | `manager_scope` rows, 4 doctypes |
| H1 | HR Manager + Employee | Company, all doctypes |
| H2 | HR User + Employee | Branch, applicable to Employee |
| SM | System Manager | none |
| X | Employee, no Employee record | none |

API calls, each run as each login (expected counts after the fix; "N" = the site's total):

| # | Call | S1/S2/S3/M1 | X | H1 | H2 | SM |
|---|---|---|---|---|---|---|
| D1 | `GET /api/resource/Employee?fields=["name","date_of_birth","cell_number"]&limit_page_length=0` | 1 (own) | 0 | company total | branch total | N |
| D2 | `POST frappe.desk.reportview.get` doctype Employee, same fields, `reference_doctype=ToDo` | **1** | 0 | as D1 | as D1 | N |
| D3 | `frappe.desk.reportview.get_count` doctype Employee | 1 | 0 | as D1 | as D1 | N |
| D4 | `GET /api/resource/Employee/<colleague>` | 403 | 403 | 200 | 200 if in branch | 200 |
| D5 | `GET /api/resource/Employee/<own>` | 200 | n/a | 200 | 200 | 200 |
| D6 | `frappe.desk.search.search_link` doctype Employee, `txt=""`, `reference_doctype=Leave Application` | own only | none | many | branch | many |
| D7 | `frappe.client.get_value` Employee, colleague, `date_of_birth` | refused | refused | value | value | value |
| D8 | `frappe.desk.query_report.run` *Employee Birthday* | refused | refused | rows | rows | rows |
| D9 | same for *Employee Leave Balance* | refused | refused | rows | rows | rows |
| D10 | `hrms.api.get_all_employees` | 1 | 0 | as D1 | as D1 | N |

**D2 is run twice:** once with option A's row and no code (expected: all rows, proving
section 1.3), then with B (expected: 1). If D2 under A returns 1, my reading in 1.3 is
wrong and I will say so before building.

Portal walk-through (each persona, 200% zoom, narrow phone width): Home (birthdays card on
and off), My profile (own DOB and contact still shown and editable where allowed), Team
and attendance review (M1, H1), leave apply and approve (S1 → M1), expense file and decide,
notice send (Notice Sender), org chart, directory, field check-in.

Suites: `bench run-tests --app hrms` (the alvoraa_hr_core modules), `--app alvoraa_portal`,
`--app alvoraa_goals`, full, once at the end. Both batch summaries read.

### 4.2 Dev (only after Surbhi says "push to dev")

- Deploy carries the code and the fixture; `migrate` loads the fixture.
- Repeat D1–D10 on the dev tenant with three real-shaped staff logins, one manager, one
  HR Manager. Same expected numbers.
- She tries the portal as a staff login and a manager.

### 4.3 Production (a separate step, needs her word for main and for the server)

There is **no production data change** with option B. The change is the release itself.

- **Before (read-only, bench console, `frappe.set_user` per login, no writes):**
  1. As 3 sample staff logins: `len(frappe.get_list("Employee", limit_page_length=0))`.
     Expect 597 each (matches the ticket).
  2. As one of the 7 managers: same. Expect 597.
  3. As each HR login: same. Record the numbers.
  4. The roles that keep full access:
     `frappe.get_all("Custom DocPerm", filters={"parent": "Employee", "read": 1, "permlevel": 0}, pluck="role")`.
     Surbhi reads this list before the release (Q2).
- **After:** the same four reads. Expect staff 1, managers 1 (or team if Q1 = yes), HR
  numbers **unchanged**. Plus D2 as one staff login: expect 1. Any HR number that changes
  is a stop.
- **Rollback:** revert the commit and redeploy; delete the two Custom Role records. Nothing
  else was written, so nothing else needs undoing.

### 4.4 If Surbhi keeps option A

For the record, it would be: one User Permission per staff login
(`allow=Employee, for_value=<own>, apply_to_all_doctypes=0, applicable_for=Employee`),
written by a reviewed script, plus an Employee `on_update` hook for new joiners and
`user_id` changes. Before/after count as in 4.3. Rollback by deleting rows matching that
exact shape for `for_value = own employee`. **D2 would still return 597 rows.** I would not
call the ticket closed.

---

## 5. What stays unfixed

| Item | Label | What removes it |
|---|---|---|
| Expense Claim: Employee role reads and writes every claim at DTC without a row for it (076 C, Escalation 1) | **Dangerous debt** | Its own ticket; count first (076 Q-A, second half) |
| Employee names, titles and departments stay visible to colleagues through our directory and org chart | Intentional (decision D-10, slice 045) | Nothing; it is by design |
| Desk pickers for non-HR show only themselves | Acceptable simplification | Q1 = yes adds the team |
| `/hrms` PWA shows colleague IDs, not names | Acceptable simplification, if DTC uses it at all | Not using `/hrms`; our portal is the product |
| *Employee Analytics* chart counts (people per department etc.) still come from a raw query | Acceptable simplification | Counts only, no personal data |
| The exposure since staff logins were created cannot be undone; whether anyone used it is not known | Needs Surbhi's call | Frappe does not log list reads by default; nginx access logs may show `reportview` / `resource/Employee` calls by staff. Say so if a breach assessment is needed |
| Custom Link fields on DTC's Employee pointing to Employee without "ignore user permissions" | Unknown | Checked in the production before-count if option A is kept; irrelevant to B |

---

## Commands run for this analysis

All read-only. No DB query on any site.

- `git fetch origin dev`; `git grep` on `origin/dev` for hooks, callers and helpers.
- `docker exec hrlocal-bench` **file reads only** (`grep`, `sed`, `python3 -c` on JSON) of
  installed Frappe v16.33.1, ERPNext v16.34.2, Frappe HR. No `bench` command, no site touched.
- `git worktree add .claude/worktrees/alv-249` from `origin/dev` d3afcaa5.

## Subtract pass

Removed from my first draft: a role list in code (replaced by reading the site's own
permissions), a "manager sees team" branch (made a question, default off), a patch for
existing sites (not needed: a hook and a fixture need no data backfill), and an
after-migrate function for the reports (a fixture does the same with no code).
