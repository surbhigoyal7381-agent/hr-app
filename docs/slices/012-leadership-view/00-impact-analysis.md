---
slice: 012-leadership-view
artifact: 00-impact-analysis
scope: push 1 only (US-1 to US-10)
author: hrms-fullstack-engineer
date: 2026-09-15
status: proposal — waiting for your approval
inputs: [02-functional-spec.md (incl. User decisions 2026-09-15), 01c-security-privacy-requirements.md, 07-devops-inputs.md §1–§3 and Decisions, 01b-ux-design.md §8.4 and §8.10, prototype-v2/index.html (pageReview), 01-product-brief.md (Gate decision), change-process.md, frappe-conventions.md, parallel-work.md, nfr-budget.md, work board, slice 010 group D 00d/00e/01d/03d, code at local dev 8ad6ea3 and origin/dev c27fb56, Frappe 16.33.1 / ERPNext 16.34.2 / HRMS 17.0.0-dev source inside hrlocal-bench, read-only SQL on ppj.localhost]
---

# 012 · Leadership view — push 1 impact analysis and strategy

**I recommend. You decide.** No code was changed. No worktree was made. Nothing on the
bench was changed: I ran only `SELECT` / `SHOW` queries on `ppj.localhost` and read files
inside the container. No `docker cp`.

## The short answer

**Bad news first.**

1. **HR Analytics numbers will change the day push 1 ships, for every HR user.** Attendance
   goes up or down (doubtful days left out, Work From Home counted, a different period — on
   the demo tenant September jumps from 65.8% to 97.0%),
   store HR and single-company HR see less, and an HR login with no company link sees a
   "not linked" message instead of figures. There is no switch. Tenant HR must be told first.
2. **On the demo tenant (`ppj.localhost`) almost every Step 0 check fires at once.** 7, 8 and 9
   Sep are 100% absent in all six branches; only 3 leave requests exist against 8,045
   allocated days; nobody has a leaving date. After push 1, HR Analytics shows a doubtful-day
   warning and three "needs review" items. That is the right answer for that data, but it is
   close to the brief's kill criterion ("more than half the cards say Needs review").
3. **Frappe drops some of the new indexes on a later upgrade unless we also mark the field as
   indexed.** I read Frappe's schema code: when a standard doctype is next synced, a
   single-column index on a field that Frappe thinks is not indexed gets removed. So I propose
   a small change to DevOps' OPS-52 method (section 6.1). **I disagree with DevOps here, in
   writing; you decide.**
4. **Slice 010 group D is building right now in the same app.** Local `dev` already holds 14
   of its commits that are not on `origin/dev`. Push 1 must go to `dev` **after** group D, or
   pushing `dev` would carry group D's unfinished work (section 11).
5. **Seven small rulings are needed before I build** (section 13). None is large. Each has a
   recommended default.

**What push 1 is, in one line:** eight indexes; one shared calculation for attendance, leave
and people figures; two small new doctypes; a 06:30 morning check; an HR "Data to review"
page; and the three live leak fixes G1, G2, G3 with the org-roles guard (Q6) and the "not
linked" message (BA-Q5).

**Size: about 11 working days**, in 10 local commits, pushed to `dev` once, on your word.

---

## 0 · What I checked

| Checked | How | Result |
|---|---|---|
| Framework versions on the bench | `frappe/__init__.py`, ERPNext and HRMS `__version__` | **Frappe 16.33.1**, ERPNext 16.34.2, HRMS 17.0.0-dev, MariaDB 10.8.8. Security read Frappe 16.22 elsewhere; I re-read the parts I rely on here |
| `frappe.db.add_index` | `database/mariadb/database.py:419` | Checks by **index name**, commits, runs `ADD INDEX IF NOT EXISTS`. Adds a Property Setter only outside migrate and install |
| When migrate drops an index | `database/schema.py:311`, `database/mariadb/schema.py:129-161` | A single-column non-unique index is dropped when the doctype syncs and the field's meta has no `search_index` |
| Custom DocPerm behaviour (BA assumption) | `model/meta.py:640-652` | **Confirmed.** Once any Custom DocPerm row exists for a doctype, Frappe ignores all its standard DocPerms |
| V6 — does Branch belong to a company? | `SHOW COLUMNS FROM tabBranch` | **No company field.** `branch` is unique across the whole tenant. Two companies share one Branch record |
| V7 — who can create User Permissions | `tabDocPerm`, `tabCustom DocPerm` on ppj | System Manager only; no Custom DocPerm |
| Version permissions | `tabDocPerm` | System Manager read (no delete); Administrator delete |
| Scheduled job queues | `scheduled_job_type.py:187` | A `cron` entry runs on `default`; only "Long" frequencies use `long`. So the cron entry must enqueue onto `long` |
| `frappe.enqueue` | `utils/background_jobs.py:76` | Has `queue`, `timeout`, `job_id`, `deduplicate`. `job_id` is namespaced by site (`:649`) |
| `@rate_limit` | `rate_limiter.py:104-160` | Identity is the IP, or a value **the client sends** in the form. Not usable per user |
| `frappe.get_doc(..., for_update=True)` | `__init__.py:81` | Exists (row lock for the confirm race) |
| Standard fields used | JSON in bench | Attendance `status` = Present / Absent / On Leave / Half Day / Work From Home; Attendance, Leave Application and Leave Allocation all have `company`; Employee Checkin has **no** company; Employee `company`, `branch`, `department`, `date_of_joining`, `relieving_date` have no `search_index`; Checkin `time` has none |
| Indexes today on ppj | `information_schema.STATISTICS` | Employee: status, designation, device id, lft/rgt. Attendance: employee, status, attendance_date. Checkin: employee, shift. **`alvoraa_branch` is not on ppj yet** (slice 011's migrate has not run there) |
| Demo data on ppj | `SELECT` counts | 403 active, 0 left, 1 company, 6 branches, no employee without a branch. Attendance: 22,570 Present, 1,689 Absent, 5 On Leave, **0 Half Day, 0 WFH**. Fiscal Year 1 Apr–31 Mar |
| Incoming work | `git fetch`; `dev..origin/dev` | **Nothing new on `origin/dev`.** Local `dev` is 14 commits ahead (slice 010 group D, not pushed) |
| Other sessions' uncommitted edits in the main checkout | `git status` | `.claude/*`, `CLAUDE.md`, `backlog/…`, `alvoraa_position.py`, deleted `OBJECTIVES_KPI_REQUIREMENTS.md`, untracked docs. **None is a file push 1 touches.** I leave them alone |

---

## 1 · Cross-module reach

| App | Touched in push 1? | How |
|---|---|---|
| `alvoraa_portal` | **Yes — all the code** | `hr_api.py` (`get_hr_analytics`, `get_org_setting`, `set_org_setting`); `attendance_analytics.py` (`_org_roles`, `person`, `filter_options`); **new** `org_figures.py` (shared calculation and HR scope); **new** `data_review.py` (morning checks, page endpoints); **new** doctypes `Alvoraa Data Review Item` and `Alvoraa Leader View Settings`; `hooks.py` (one cron entry, one `after_migrate` and one `after_install` line); `www/hrms-employee.html` (HR Analytics additions, new Data to review panel); new tests |
| `hrms` — our code in `hrms/hrms/alvoraa_hr_core` | **Read and reused, not changed** | `access.permitted_companies`, `access.refuse`, `access.log_refusal`, `features.feature_enabled`. `attendance_score.py` is **not** touched (AC-11) |
| `hrms` — Frappe HR upstream | Read only | Attendance, Employee Checkin, Leave Application, Leave Allocation, Shift Type |
| `erpnext` | Read only | Employee, Branch, Company, Fiscal Year (`get_fiscal_year` through `_leave_year_start`) |
| `frappe` | Configure only | Property Setter (`search_index`), `add_index`, scheduler cron, `track_changes`, logger |
| `alvoraa_goals` | **Not touched** | It imports nothing from the new modules. `hr_api.py` already imports `alvoraa_goals.permissions`; no change there |
| `alvox_compensation` | Not touched | — |

**HRMS domains:** attendance (figures, doubtful days), leaves (leave used this leave year,
pending requests), org structure (company and branch scope), people records (headcount,
joiners, leavers). **Payroll, appraisals, goals and compensation are not touched.** Appraisal
attendance scores keep their own formula on purpose.

---

## 2 · Every caller of every function I will change

Grep over `alvoraa_portal`, `alvoraa_goals`, `hrms/hrms`, `alvox_compensation` (Python, HTML,
JS, JSON). Line numbers at local `dev` 8ad6ea3.

| Function I change | Callers found | Effect on each caller |
|---|---|---|
| `hr_api.get_hr_analytics` | `hrms-employee.html:8500` (`loadAnalyticsPanel`); `tests/test_endpoint_entitlement.py:100, 107, 114` | Page: same keys kept, new keys added (`scope`, `not_linked`, `data_up_to`, `review`). Tests: they check the plan gate and the decorator; both stay. Test 107 calls it as an enterprise user — it must still not be refused by the plan (it may now return `not_linked`) |
| `hr_api.get_org_setting` | `hrms-employee.html:15988` (`orgLoad`, key `kra_link_mandatory`); `tests/test_portal_call_paths.py:127-131` (checks the call path exists) | Key stays allowed. No page change |
| `hr_api.set_org_setting` | `hrms-employee.html:16002` (`orgSaveKraMandatory`, key `kra_link_mandatory`, values "1"/"0"); `test_portal_call_paths.py:127-131` | Key and values stay allowed. No page change. **The only key any screen writes** |
| `hr_api._require_hr` | `hr_api.py:2213, 2219, 2718, 2910` | **Not changed.** The allow-list sits inside the two setting functions |
| `attendance_analytics._org_roles` | `_may_see_organisation` (`:60`) → `views` (`:98`), `_population` (`:141`), `filter_options` (`:435`), `person` (`:475`) | All four get the guard at once. HR Manager, HR User, System Manager unaffected |
| `attendance_analytics.person` | `hrms-employee.html:5921` (`aiApi("person", …)` from a clicked name); `tests/test_attendance_analytics.py:207, 215` | Page: store HR can no longer open a name outside their scope (they could not see that name in the list anyway). Tests: a manager outside the line is still refused; self still opens |
| `attendance_analytics.filter_options` | `hrms-employee.html:5678` (`AI.opts = await aiApi("filter_options")`, has a catch) | Store HR gets only their store's departments, branches, designations, managers |
| `attendance_analytics._population` | `summary` (`:300`); `tests/test_branch_scope.py:154, 158, 162, 175` | **Not changed** (see decision D-6). `person()` reuses its organisation rule |
| `attendance_analytics._analyse` | `summary` (`:306`) only | **Not changed.** Attendance Insights keeps its own formula (BA-Q4) |
| `hr_api._leave_year_start` | `hr_api.py:164, 387, 792, 1065, 1581`; `tests/test_leave_year.py` | **Not changed.** Called by the new calculation with an explicit company |
| `access.permitted_companies` | 20+ callers across portal, goals, org structure | **Not changed.** Only called |
| Defaults keys read with `get_default` | `alvoraa_attendance_org_roles` (`attendance_analytics.py:56`), `alvoraa_attendance_short_tolerance_mins` (`:99, :304, :482`, `attendance_correction.py:444`), `kra_link_mandatory` (`kra_api.py:33`), `alvoraa_checkin_photo_retention_days` (`field_checkin.py:548`), org chart keys through `alvoraa_org_structure/settings.py:113,146` (its own guarded setter), `currency` (`invoicing.py:252`) | Reads unchanged. Only the portal setter narrows |

**New functions** (no callers yet): `org_figures.hr_scope`, `org_figures.attendance_figures`,
`org_figures.leave_figures`, `org_figures.people_figures`, `org_figures.data_up_to`,
`data_review.enqueue_morning_checks`, `data_review.run_morning_checks`,
`data_review.data_review_items`, `data_review.data_review_confirm`, `data_review.after_migrate`.

---

## 3 · Persona impact

| Persona | What changes in push 1 |
|---|---|
| **CXO / System Manager** (no HR role) | HR Analytics: unchanged — it still refuses a System Manager without an HR role (existing behaviour; the nav item shows for them because `is_hr` includes System Manager — an old mismatch, not fixed here). Attendance Insights: unchanged (slice 010 CXO decision). **Can no longer change `alvoraa_attendance_org_roles` through the portal setter** (can still use the desk console). Can read Data Review Items in the desk |
| **HR Manager, central, with a Company permission** | HR Analytics limited to permitted companies (same as today on a one-company tenant). New warning line and "N figures need review" link. New **Data to review** page with confirm actions. Attendance % changes (see section 5). `set_org_setting` refuses any key except `kra_link_mandatory` |
| **HR Manager / HR User with no Company permission and no Employee** | **Loses HR Analytics figures** and sees "Your account is not linked to a company…" (BA-Q5, fail closed). Data to review shows the same message. Attendance Insights unchanged (decision D-6) |
| **HR User, location HR** (Branch permission) | **Sees less:** HR Analytics for their branch only — counts, distributions, confirmations due and recent joiners. Data to review lists only their branch's items; they may confirm branch items only. `person()` refuses employees outside their store; `filter_options` lists only their store |
| **Line manager** | `person()` for their reporting line: unchanged. No new screen |
| **Employee** | Nothing visible. Protected: nobody can add Employee, Employee Self Service or Leadership to the org-roles setting through the portal, and even a value set from the console is ignored |
| **Leadership** | Role does not exist until push 2. The guard already refuses it if someone lists it |

---

## 4 · HRMS domain impact

| Domain | Impact |
|---|---|
| Attendance | New definition for HR Analytics (section 5). Doubtful days found per branch per day and left out of HR's figures while Open. **No Attendance record is changed.** |
| Leaves | "Leave used" divides this leave year's approved leave by allocations that overlap this leave year, per company (fixes LV2). D6 check. Pending approvals scoped |
| Org structure | Scope by company, then branch. Branch is never trusted alone, because one Branch record can be used by two companies (V6) |
| People | Headcount, joiners, confirmations due, recent joiners scoped. D18 checks on leaving dates |
| Payroll, appraisals, goals, compensation | Not touched. A pin test proves `attendance_score` returns the same numbers (AC-11) |

---

## 5 · What HR Analytics numbers change to

| Figure | Today | After push 1 |
|---|---|---|
| Scope | Whole tenant, every company | `permitted_companies()`, narrowed to the caller's Branch permissions when they have any. Empty → "not linked" message, no figures |
| Attendance rate | (Present + ½ Half Day) ÷ (that + Absent), month to date | (Present + WFH + ½ Half Day) ÷ (Present + WFH + Half Day + Absent). On Leave is in neither part. Submitted rows only. **Open doubtful days of that branch left out.** Period = the month of "data up to" (the last day with attendance in scope), day 1 to that day |
| Present / absent this month | Raw counts | Same counts, doubtful days left out |
| Leave utilisation | This year's leave ÷ **every allocation ever** | Per company: approved, submitted leave with `from_date` in that company's leave year ÷ allocations overlapping that leave year; then added up |
| Headcount, joiners, distributions | Tenant-wide | Scoped. Headcount = Active and joined on or before today |
| Pending approvals | Tenant-wide | Scoped |
| Confirmations due, recent joiners | `get_all(ignore_permissions=True)`, tenant-wide, names and gender | `frappe.get_list` (User Permissions apply) plus the scope filter. **Gender of the 10 newest joiners stays** in the scoped list — it is HR data, and removing it is not in the spec |
| New on the page | — | "Data up to 13 Sep"; amber "Some attendance days look wrong" naming the dates (AC-17); "**N figures need review.** Leaders see 'Needs review' until they are fixed. Open Data to review" |

**On ppj today (measured with read-only SQL):** September attendance moves from **65.8%**
(2,025 present, 1,053 absent) to **97.0%** (2,025 present, 63 absent) with 7–9 Sep left out.
The last day with attendance is 9 Sep, itself a doubtful day. Leave used stays 0.06% but raises
a Leave item; a Leavers item is raised because nobody has a leaving date.

**How HR is told:** a short note to each tenant's HR before push 1 reaches that tenant
(OPS-68). Who sends it is still open (BA-Q14). I will draft the note text in `03`.

---

## 6 · Proposed strategy

### 6.1 Indexes (US-1, OPS-5, OPS-20, OPS-52 to OPS-54)

Eight indexes, added from `data_review.after_migrate`, listed in both `after_migrate` and
`after_install` (a CI site never migrates):

| Table | Index |
|---|---|
| `tabEmployee` | `company` · `branch` · `department` · `date_of_joining` · `relieving_date` |
| `tabEmployee Checkin` | `(alvoraa_branch, time)` · `(time)` |
| `tabAttendance` | `(alvoraa_branch, attendance_date)` |

**Method, and where I disagree with DevOps.** OPS-52 says `frappe.db.add_index` alone. I read
Frappe 16.33's schema sync: when Employee or Employee Checkin is next synced (for example after
an ERPNext or HRMS update changes their JSON), Frappe **drops** any single-column index on a
field whose meta has no `search_index` (`database/schema.py:311`). The six single-column
indexes above would vanish, and the next `after_migrate` would rebuild them — a table lock on
Employee Checkin during a deploy, every upgrade. `add_index` protects against this with a
Property Setter, but **only outside migrate and install** (`database.py:434`), which is exactly
where we call it.

**My proposal:** for the six single-column indexes, first write a Property Setter
`search_index = 1` on the field (`make_property_setter`, the same call `add_index` uses), then
call `add_index`. Frappe then treats the index as its own and never drops it. Both steps are
safe to run twice. The two-column indexes start with `alvoraa_branch`, which already has
`search_index` from slice 011, so they are not at risk and use `add_index` only.

- Side effect: the six fields show "Index" ticked in Customize Form. Nothing else.
- The Property Setters travel only through our installer, not fixtures, so a site without
  `alvoraa_portal` is untouched.
- **Timing (OPS-53, OPS-54):** measured on the synthetic sites and a rehearsal copy, recorded in
  `03`. The migrate runs inside the runbook's backup-and-maintenance hold. I will not run a
  migrate on the bench without your word.

### 6.2 The two new doctypes — BA-Q10: I agree with the analyst

**`Alvoraa Data Review Item`** (module Alvoraa Portal). As spec §3c, with four changes I found
while checking it against the acceptance criteria:

| Change | Why |
|---|---|
| **Name = a hash of the rule key** (`rule`, `company`, `alvoraa_branch`, `check_date`), set in `autoname` | A unique index on (type, company, branch, date) does **not** stop duplicates in MariaDB when branch or date is empty (empty values never clash). A primary key does. A second insert fails cleanly, so the job is safe to run twice or in parallel |
| **`rule` is part of the key** | D18 rule 1 (per branch) and rule 2 (per company) are both "Leavers" |
| **D6 and D18-2 keys carry the leave year** (`check_date` = leave-year start) | Otherwise "the figure is right", confirmed once, would hide a real gap in every later year. Decision D-3 |
| **Drop `last_checked_on`** from the item | Writing it every morning changes every row and adds a Version row each day, which breaks AC-18 ("zero rows change"). The page shows "Last checked 06:32" from the settings stamp instead. Decision D-4 |

Permissions: HR Manager and HR User read and write; System Manager read; nobody create or
delete in the desk. The **controller** refuses every change made by a person, on every path
(desk, REST, `set_value`, import), unless the server set one of two flags that a client cannot
set: `via_rule_check` (the job or the page re-check may change counts and Open ↔ Cleared) or
`via_confirm` (the confirm endpoint may move Open → Confirmed once, with `confirmed_by`,
`confirmed_on`, `figure_without`, `figure_with`). `track_changes` on. Counts only — no employee
field, no name, no leave type.

**`Alvoraa Leader View Settings`** (Single, `track_changes`). **I recommend creating it in push
1, not push 2** (decision D-1), because push 1 already needs two things from it:

- the **minimum group size** for the doubtful-day check (D5 runs only for groups of at least the
  minimum — OPS-22, PRIV-10);
- the **"last successful run"** stamp (OPS-50), written with `frappe.db.set_single_value`, which
  updates the row without a document save, so no Version row.

Push 1 builds the doctype with its full SEC-10 controller rules (System Manager write, 3–10,
reason required when the value changes, reason cleared after the Version row is written, no
save without a change). The value is created as 5. **The portal settings screen and the history
endpoint stay in push 2.**

**Why not HR Settings (BA-Q10), with evidence:**
1. HR Manager has write on HR Settings (standard DocPerm, read on ppj). Making one field System
   Manager only needs a permlevel and a Custom DocPerm row. I confirmed in `model/meta.py:640-652`
   that **one Custom DocPerm row replaces all of HR Settings' standard permissions** for that
   tenant. That is a risky change to a doctype every HRMS screen reads.
2. **Slice 010 group D is adding three custom fields and a `validate` hook to HR Settings right
   now.** Two slices changing HR Settings at once is the clash `parallel-work.md` warns about.
3. `CLAUDE.md` §4 prefers HR Settings for organisation config, and I respect that. The minimum
   group is a privacy control with a different owner (System Manager), so a small doctype we own
   is the cleaner Frappe-first home.

### 6.3 One shared calculation — `org_figures.py` (US-2, OPS-1, OPS-6)

Designed so push 2 reuses it unchanged.

```
Scope(companies: tuple, branches: tuple | None)    # branches None = every branch of those companies
hr_scope(user) -> Scope                            # push 1. Push 2 adds leader_scope(user) in its own module
attendance_figures(scope, start, end, group_by=None, include_open_doubtful=False)
leave_figures(scope, as_of, group_by=None)
people_figures(scope, as_of, group_by=None)
data_up_to(scope)
```

- **Returns raw counts, never percentages alone and never names.** Each group carries its
  distinct-people count, so push 2 can apply the small-group rule (PRIV-2) on top. HR screens
  do not suppress.
- `group_by` is an enum checked in code (`None`, `"branch"`, `"department"`, `"month"`). A client
  string never picks a column.
- **Grouped SQL, fixed query count.** Written with `frappe.qb` where it reads cleanly (parameters
  by construction) and parameterised `frappe.db.sql` where joins make `qb` unreadable. Scope values
  are always parameters. No query inside a loop over people or branches.
- **Branch scope always adds the company condition too**, because a Branch record is not tied to
  a company (V6).
- Short days are counted in SQL: join Shift Type on `COALESCE(a.shift, e.default_shift)`, shift
  length from start and end times (+24 h for a night shift), compare with `working_hours × 60`
  and the tolerance key. Same rule as `attendance_analytics.py:249-259`. No shift → never short.
- Doubtful days are left out with an anti-join on Open `Alvoraa Data Review Item` rows for the
  same branch and date — one join, no extra query.
- Leave year: one query per company in scope, because companies can have different fiscal years.
  Query count grows with **companies** (usually 1–2), never with employees or branches. I will state
  this in the query-count test.
- `hr_scope`: `permitted_companies(user)`; if the user has Branch User Permissions that apply to
  Employee (all doctypes, or `applicable_for` Employee), those branches. **Employees with no branch
  are left out for store HR** (decision D-8). Empty companies → the "not linked" answer.
- A purpose constant says these figures are for oversight and must not feed ratings (PRIV-13).

### 6.4 HR Analytics rewrite — G1 (US-8, SEC-16)

`get_hr_analytics` keeps its name, `@frappe.whitelist()`, `@requires_feature("analytics")` and
its role check. Every count goes through `org_figures` or gets the scope conditions. The two
name lists use `frappe.get_list` without `ignore_permissions`, plus the scope filter. The
response keeps every existing key (so the page keeps working) and adds `not_linked`,
`data_up_to`, `review` (`open_count`, `doubtful_dates`). Not cached (07 §3 C).

### 6.5 Doubtful days, "Needs review" and the morning check (US-3, US-5, US-7)

**Job.** `hooks.py`: `scheduler_events["cron"]["30 6 * * *"] = ["alvoraa_portal.data_review.enqueue_morning_checks"]`.
That function only calls
`frappe.enqueue("alvoraa_portal.data_review.run_morning_checks", queue="long", timeout=900, job_id="leader-data-checks", deduplicate=True)`.

`run_morning_checks`, per company:

1. **D5 doubtful days, last 35 days**, per named branch per day, in two grouped queries: Attendance
   (rows not On Leave, Absent count) and Employee Checkin (distinct people with a check-in, through
   `(alvoraa_branch, time)`), plus one "any check-ins in 35 days" count for the company. Only groups
   with expected ≥ the minimum. ≥ 95% absent and < 5% checked in; with no check-ins at all, 95%
   absent alone.
2. **D6** (≥ 3 months into the leave year and leave used < 1%) per company.
3. **D18-1** (Left with no relieving date) per branch; **D18-2** (no relieving date in the last 12
   months) per company.
4. One read of this company's existing items in the window; compare; write **only differences**:
   insert new Open items, update changed counts on Open items, Open → Cleared when a rule stops
   firing. **Never touch a Confirmed item. Never delete.**
5. `frappe.db.commit()` after each company, so a crash keeps finished companies (AC-38).
6. At the end, stamp `last_checks_run_on`.

**Failure (OPS-50, OPS-57):** `frappe.log_error(title="Leader data checks failed", message=…)` with
company, stage and error **type** only — never `frappe.get_traceback()`, which can hold local
values. The stamp stays old. The job skips a tenant whose plan does not include `analytics`
(decision D-9). Employees with no branch get no doubtful-day check (decision D-12).

**Cost, estimate:** at 1,000 people about 35,000 attendance rows and 70,000 check-ins read through
indexes; a few seconds per site. Measured in `03`.

### 6.6 Data to review page endpoints (US-4, US-6)

Both in `data_review.py`: `@frappe.whitelist(methods=["POST"])`, `@requires_feature("analytics")`,
HR Manager or HR User only, Guest refused, `Cache-Control: no-store`.

**`data_review_items()`**
- Scope from `hr_scope`. Empty → `not_linked`.
- **Re-check on open (OPS-49):** re-runs D6 and D18 for the caller's scope and writes only
  changes. **It clears items but does not create new ones** — creating would need
  `ignore_permissions`, which SEC-8 forbids; new items appear at 06:30 (decision D-5). Store HR
  re-checks only their branches' D18-1 items.
- Lists Open items with `frappe.get_list` plus an explicit branch filter for store HR (Frappe's
  non-strict User Permissions would otherwise show company-wide items with an empty branch).
- Groups doubtful days into one card per set of dates; computes "attendance with those days" for
  the confirm dialog from `org_figures` (2 queries).
- Returns counts, dates, rule, found date, "Last checked" and a stale flag (> 26 h). No names or
  employee IDs (AC-36).

**`data_review_confirm(items, action)`**
- `items`: list of item names, capped at 40. `action`: one of `absence_real`, `figure_right`.
- For each: `frappe.get_doc(..., for_update=True)` (a row lock, so two HR users cannot both
  confirm — AC-24), `frappe.has_permission(doc, "write")`, and a scope check: branch in the
  caller's scope; a company-wide item only when the caller's scope covers the whole company.
  Status must be Open; action must match the item type. **Any failure refuses the whole request**
  through `access.refuse(…, "SEC-13", …)` — one security log line, no scope values — and nothing
  is written.
- Saves with the server flag; one Version row per item.
- **Per-user limit, 30 an hour (OPS-40, approved):** a small helper keyed by the session user in
  Frappe's cache, because Frappe's `@rate_limit` counts by IP or by a value the client sends. Push 2
  reuses it for leader reads and the settings save (its second and third uses).
- **Leavers:** "The figure is right" for **rule D18-2 only**; rule D18-1 (Left with no date) keeps no
  button, because a missing date is always a gap (decision D-2).

### 6.7 `person()` and `filter_options()` — G3 (US-9, SEC-17)

- `person(employee)` opens only: self; the caller's reporting line (unchanged); or, for org-role
  holders, an employee **inside the same organisation rule `summary()` uses** — company = caller's
  own Employee company, `frappe.get_list` for non-System Managers (User Permissions apply), System
  Manager unchanged. One `get_list(..., filters={"name": employee}, limit=1)` — not the whole list.
  Left employees inside that rule may still be opened (decision D-7). Refusal: `access.refuse`,
  rule `SEC-17`, the employee id as document name only.
- Date range: cut to at most 12 months ending on `date_to` (AC-48), not refused.
- `filter_options()`: `frappe.get_list` for non-System Managers, for all four lists including
  manager names.

### 6.8 `set_org_setting` allow-list — G2 (US-10, SEC-18) and the org-roles guard (Q6, SEC-19)

- `ALLOWED_ORG_SETTINGS = {"kra_link_mandatory": ("0", "1")}` — the only key any screen reads or
  writes. `get_org_setting` and `set_org_setting` refuse every other key with `access.refuse`, rule
  `SEC-18`, no value logged. A value outside `"0"`/`"1"` is refused too.
- Not on the list: `alvoraa_attendance_org_roles`, `alvoraa_attendance_short_tolerance_mins`,
  `alvoraa_checkin_photo_retention_days`, org chart keys, `currency` and everything else. No screen
  edits them today (decision D-10).
- `_org_roles()` removes `Leadership`, `Employee`, `Employee Self Service` — and I propose also
  Frappe's automatic roles `All`, `Guest`, `Desk User`, which every user or visitor holds
  (decision D-11). When it removes one, it writes one `security` log line with the role names only.

### 6.9 The "not linked" message (BA-Q5)

When `hr_scope` has no company, HR Analytics and Data to review return `not_linked: true` and no
figures. Draft copy for the UX designer to confirm: "**Your account is not linked to a company, so
there are no figures to show.** Ask your System Manager to give you permission for your company, or
to link your employee record to your login."

### 6.10 The portal page (`hrms-employee.html`, hot file)

- **HR Analytics panel:** inside `renderAnalyticsData` only — the "not linked" state, "Data up to",
  the amber doubtful-day warning and the "N figures need review" line (copy from 01b §8.4, §8.10).
- **Data to review:** a new, self-contained panel `#panel-data-review` with its own `dr…` function
  and CSS prefix; one nav item beside Analytics with a count badge; one line in `switchPanel()`; one
  line in `applyPlanNav()` (same rule as Analytics: HR and plan). Confirm dialogs as accessible alert
  dialogs, 44 px targets, every string in `__()`.
- **Not touched:** `orgLoad`, `orgSaveKraMandatory` and the Org Settings screen, which slice 010 is
  changing. There is no "Company ›" menu or "Needs you" strip yet (slice 009), so nothing goes there.

### 6.11 Cache invalidation

**Push 1 adds no cache.** HR Analytics and Data to review are computed on every request (07 §3 C).
Nothing to clear on deploy.

For push 2, push 1 already provides what the leader cache key needs: `r` = the newest `modified` of
the company's review items (a confirmation or a clear changes it, so a leader key changes at once),
and `min` from the settings doctype. Push 2 adds the explicit `ldr:` deletes on confirm and on
settings save (OPS-43 a and b) when there are keys to delete. I am not writing code for keys that do
not exist yet.

### 6.12 Observability

- One `frappe.logger("leader_view")` line when `get_hr_analytics`, `data_review_items` or
  `data_review_confirm` takes over 1 s: endpoint, scope type, number of branches, query count,
  duration (OPS-56). No figures, names or branch names.
- Refusals through `access.log_refusal` (SEC-14). Job failures in Error Log with a fixed title
  (OPS-50); `health.collect_scheduled` already carries the count to the control plane.

### 6.13 Rollback

No switch (OPS-68). `git revert` of the push, deploy on your word. The two new tables, the Property
Setters and the indexes stay and are harmless. The cron entry disappears on migrate.

---

## 7 · The seven non-functional dimensions

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **Improves** | Eight indexes on the columns every figure filters on. HR Analytics moves to a fixed number of grouped queries (about 15, plus one per company for the leave year). `person()` range capped. The morning job adds a few seconds of reading once a day, on the `long` queue. One-off cost: index builds during migrate (seconds at 1,000 people; measured before release) |
| **Security** | **Improves** | Closes G1, G2, G3. Org-roles shortcut blocked in code. No new `ignore_permissions` (the counter must not rise). All SQL parameterised. New endpoints POST-only, plan-gated, HR-only, rate-limited, with refusals logged |
| **Reliability** | **Improves**, with one new moving part | Every write in the job is safe to run twice, committed per company, never overwrites a confirmation. Failure is visible (Error Log + stale line after 26 h). The new moving part is the job's dependency on `worker-long` (OPS-69 release check) |
| **Scalability** | **Improves** | Query counts do not grow with employees or branches (tested at 10/100 employees and 2/8 branches). Designed for 1,000 employees, timed at 400 and 1,000, and at 2,000 if cheap |
| **Maintainability** | **Neutral** | Removes one of three attendance formulas (HR Analytics now shares the leader formula). Adds two small doctypes, two modules and a job. Attendance Insights keeps its own formula (BA-Q4), so a third formula remains |
| **Data integrity** | **Improves** | Figures stop counting device-failure days as absence and stop dividing by every allocation ever. Confirmations are locked, recorded and race-safe. Risk: a doubtful day is only found at 06:30, so a bad day shows in HR's figure until the next morning |
| **Compliance / privacy** | **Improves** | Store HR and single-company HR stop seeing other stores' and companies' names, gender and joining dates. New records hold counts and HR user ids only. Settings changes and confirmations keep who, when, before and after |

**What gets worse for someone (not a dimension "degrades", but you should know):**
- An HR login with no Company permission and no Employee record loses HR Analytics figures (intended, BA-Q5).
- HR numbers change without a switch.
- Store HR can no longer open another store's employee in Attendance Insights (intended, G3).
- HR can no longer change the tolerance, photo retention or org-roles keys from the portal API (none of them has a screen).

---

## 8 · How each in-scope SEC, PRIV and OPS item is met

### Security

| Item | How it is met in push 1 | Test |
|---|---|---|
| SEC-7 (new endpoints) | `whitelist(methods=["POST"])`, `requires_feature("analytics")`, HR role check, Guest refused, `no-store` header | GET refused, Guest refused, header asserted |
| SEC-8 | No `ignore_permissions` in new or rewritten code; `qb` / `%s` parameters only | Counter does not rise; a branch name with a quote is refused normally |
| SEC-10 (settings doctype, if D-1 approved) | Controller `validate` on every path: System Manager only, 3–10, reason with change, reason cleared after the Version row, no unchanged save; a broken stored value is read as 10 | HR Manager refused through desk save, REST and `set_value`; 2 and 11 refused; DB value 1 read as 10 |
| SEC-12 | Minimum lives in the doctype; `set_org_setting` refuses any other key | `tabDefaultValue` has no minimum key; setter refuses |
| SEC-13 | Items carry `company` and `alvoraa_branch`; `get_list` + explicit branch filter; confirm checks `has_permission` and scope; controller locks confirmed fields | AC-19 to AC-25, AC-32 |
| SEC-14 | `access.log_refusal` / `access.refuse` | One JSON line with rule id, nothing else |
| SEC-15 | Fixed Error Log title, error type only; generic page messages | Forced exception scanned for names, figures, branch names |
| SEC-16 | Section 6.4 | AC-41 to AC-45 |
| SEC-17 | Section 6.7 | AC-47 to AC-50 |
| SEC-18 | Section 6.8 | AC-51, AC-52, AC-54 |
| SEC-19 | Section 6.8 | AC-53 |
| SEC-22 | Job writes counts only, only for groups ≥ minimum | AC-12, AC-14 |
| SEC-1 to SEC-6, SEC-9, SEC-11, SEC-20, SEC-21 | Push 2 (leader view) | — |

### Privacy

| Item | How | Test |
|---|---|---|
| PRIV-10 | Doubtful-day detection only when expected ≥ minimum; no banner for smaller groups | AC-14 |
| PRIV-13 | `attendance_score.py` untouched; purpose constant in `org_figures.py`; nothing in `alvoraa_goals` imports it | AC-11 pin test; import check |
| PRIV-14 | Declared retention in the doctype description and `03`; no purge (no retention engine) | `Version` not in log clean-up list |
| PRIV-1 (for HR's Data to review response) | Counts and dates only | AC-36 response scan |
| PRIV-2 to PRIV-9, PRIV-11, PRIV-12, PRIV-15, PRIV-16 | Push 2. The calculation already returns distinct-people counts per group so push 2 can apply them | — |

### DevOps (push 1 part)

| OPS | How |
|---|---|
| OPS-1 | HR Analytics built on one scope, never on the old unscoped queries |
| OPS-5, OPS-20, OPS-52 | Eight indexes, Property Setter + `add_index` (section 6.1, **differs from OPS-52's method**) |
| OPS-6 | Grouped SQL; `_analyse` and `_mark_actionable` not reused |
| OPS-7, OPS-63 | Query-count tests for `get_hr_analytics`, `data_review_items`, `data_review_confirm`, the job — same count at 10 and 100 employees, 2 and 8 branches |
| OPS-9, OPS-48 | Cron → enqueue on `long`, 900 s, `job_id`, dedupe; writes only on change; commit per company |
| OPS-21, OPS-22 | Stored doubtful days per branch per day; minimum-size rule; no-check-in tenants |
| OPS-40 | Per-user limit on confirm (30/hour) |
| OPS-43 (b) | Covered by the `r` key part for push 2; explicit delete added in push 2 |
| OPS-49 | Re-check on page open (clears, does not create — D-5) |
| OPS-50 | Stamp, stale line, fixed Error Log title |
| OPS-51 | No nightly summary |
| OPS-53, OPS-64 | Synthetic 400 and 1,000-person sites (2,000 if cheap), 30 cold/warm calls, `EXPLAIN`, index migrate timed — approved 15 Sep |
| OPS-54 | Release plan: migrate inside the backup-and-maintenance hold |
| OPS-56, OPS-57 | Slow-call log line; no personal data in any log |
| OPS-58 | `track_changes` on both doctypes; no Version access for HR |
| OPS-60 | Records in the site DB; covered by `bench backup` |
| OPS-67, OPS-68, OPS-69 | Push 1 alone; tenant HR note; release checks in `07` §5 |
| OPS-42, 44, 45, 46, 62 | Push 2 (no cache in push 1) |

---

## 9 · Existing tests that pin behaviour I touch

| Test | What it pins | After push 1 |
|---|---|---|
| `test_endpoint_entitlement.py` (97–114) | `get_hr_analytics` plan gate and decorator | Must still pass unchanged |
| `test_portal_call_paths.py::test_the_three_that_were_broken_stay_fixed` | The page calls `hr_api.get_org_setting` / `set_org_setting` | Unchanged |
| `test_attendance_analytics.py` (`TestTheBoundary`, arithmetic tests) | Org view refused to employees; manager line; self; short-day rule | Unchanged |
| `test_branch_scope.py` (142–185) | Store HR sees their store in desk and org view; central HR with no Employee sees every store; System Manager sees every store | Unchanged (decision D-6 keeps `_population` as it is) |
| `test_leave_year.py` | `_leave_year_start` per company | Unchanged |
| `hrms/alvoraa_hr_core/tests/test_attendance_score.py` | Appraisal attendance scores | Unchanged; plus a new AC-11 pin |
| `test_portal_security_010.py` | `permitted_companies` rules | Unchanged |

I run **the whole `alvoraa_portal` suite** and `hrms` `alvoraa_hr_core` tests, one run at a time on
`test_site`, after checking the bench is free.

## 10 · Tests I will add (each names the feature it keeps alive)

| File | Covers |
|---|---|
| `test_leader_indexes_012.py` | AC-1, AC-2 (second migrate adds nothing), the Property Setters exist |
| `test_org_figures_012.py` | AC-6 to AC-10 (95.4%, amended rows, late and short, 18.3% leave used, calendar-year fallback, HR vs calculation zero difference); AC-16 (doubtful rows out for that branch only); AC-30 (no figures yet); query counts |
| `test_data_review_012.py` | AC-12 to AC-15, AC-18, AC-26 to AC-29, AC-37 to AC-39, AC-161 (job, idempotence, crash mid-run, Confirmed untouched); AC-19 to AC-25 (confirm, cancel, race, desk/REST lock, 403 for another store and company-wide); AC-31 to AC-36 (listing, badge count, stale line, no names); rate limit |
| `test_leader_settings_012.py` | SEC-10 on every path (if D-1 approved) |
| `test_hr_analytics_scope_012.py` | AC-41 to AC-46, including the same-branch-name-in-two-companies case and "not linked" |
| `test_attendance_scope_012.py` | AC-47 to AC-50 (`person`, `filter_options`, 12-month cap), AC-53 (org-roles guard with the role names logged) |
| `test_org_settings_allowlist_012.py` | AC-51, AC-52, AC-54 |
| `test_attendance_score.py` (add one case) | AC-11 |
| Page | Traced by hand in the browser: HR Manager, store HR, HR with no link, employee (no menu); 360 px and 200% zoom; keyboard through the confirm dialogs |

Synthetic data only, names unique to these tests. Frappe skips Version rows during tests unless
asked (slice 010 learned this); the tests ask for them.

---

## 11 · Parallel-work check

**What came in:** nothing new on `origin/dev` since c27fb56. Local `dev` holds 14 commits of slice
010 group D (e58ffa2 … 8ad6ea3) that are **not pushed**; its worktree
`.claude/worktrees/010-portal-security-fixes` has no uncommitted changes and is at 8ad6ea3. Group D
phases 2–4 are still to come. Group D's files so far: `performance_api.py`, `goals_api.py`,
`hr_api.py` (two scorecard functions), `alvoraa_goals` hooks/permissions/review_items/KPI,
`hrms` `access.py` (`refuse_own_rating`), Appraisal JSON, new review doctypes and tests.

**Other developers:** the work board only covers this machine. `git log origin/dev --since="7 days ago"`
on my files shows only `surbhigoyal7381-agent` commits. **Please tell me if anyone else is working in
`hr_api.py`, `attendance_analytics.py`, `alvoraa_portal/hooks.py` or `hrms-employee.html`.**

| File I will change | Hot? | Who else is in it | Plan |
|---|---|---|---|
| `alvoraa_portal/hr_api.py` | **Hot** (signature rule) | 010 D changed `get_employee_scorecard` / `get_team_scorecard` (~lines 700–990); phase 3 scopes `get_employee_scorecard` (decision 28) | **Split.** I change only `get_hr_analytics` (374–520) and the two setting functions (2211–2222). No signature changes. Rebase before each bench test |
| `alvoraa_portal/attendance_analytics.py` | No (but pinned by 011 tests) | Nobody on the board | Build |
| `alvoraa_portal/hooks.py` | **Hot** (list rule) | The board lists "hooks.py (doc_events, scheduler line at end)" for 010 D. Its notes say that is **`alvoraa_goals/hooks.py`**. Groups A–C already changed `alvoraa_portal/hooks.py` (on dev) | **Split.** I add a new `"cron"` key at the end of `scheduler_events` and one line at the end of `after_migrate` and `after_install`, each with a comment. **Ask:** please confirm 010 D does not plan edits to `alvoraa_portal/hooks.py` |
| `patches.txt` (any app) | Hot | 010 D adds a line to `alvoraa_goals/patches.txt` | **No overlap.** Push 1 needs no patch: doctypes come from sync, indexes from `after_migrate` |
| `www/hrms-employee.html` | **Hot** | 010 D: review screens, KPI log dialog, badges, **Org Settings** (adds the HR Settings review fields to `orgLoad`) | **Split, then sequence.** I stay out of Org Settings entirely. My edits: `renderAnalyticsData`, a new `dr…` panel block, one nav item, one `switchPanel` line, one `applyPlanNav` line. I rebase onto group D before building the page (commit 9) |
| HR Settings | — | 010 D adds three custom fields and a `validate` hook | **No overlap** — push 1 does not use HR Settings (section 6.2) |
| New files (`org_figures.py`, `data_review.py`, two doctypes, `*_012.py` tests) | No | Nobody | Build |
| `hrms/alvoraa_hr_core/access.py` | Shared | 010 D added `refuse_own_rating` | **Read only** for me |
| KPI indexes | — | Done by 010 D | Not repeated |

**Order across the two slices (sequence):**
1. I branch `slice/012-leadership-view` from `origin/dev` in `.claude/worktrees/012-leadership-view`, as the rules say.
2. To test on the bench I rebase onto **local `dev`** (which holds group D) and `merge --ff-only`. That means my bench tests include group D's code — fine, and it proves we work together.
3. **Push 1 goes to `origin/dev` only after group D is pushed**, because pushing `dev` pushes everything in it. If you want push 1 first, I would need group D's commits kept out of the push — that needs your call and the 010 session's.
4. One test run at a time; I check `pgrep -af run-tests` and the board first.

After approval I add a row to the work board with these files.

---

## 12 · Size and order of commits

| # | Commit (local, in the worktree) | Days |
|---|---|---|
| 1 | Eight indexes: Property Setters + `add_index` in `after_migrate` / `after_install`; test | 0.5 |
| 2 | G2: org-setting allow-list, and the org-roles guard; tests | 0.5 |
| 3 | G3: `person()` scope and 12-month cap, `filter_options()` through `get_list`; tests | 0.75 |
| 4 | The two doctypes with controllers (key-hash names, locks, SEC-10); tests | 1 |
| 5 | `org_figures.py`: scope, attendance, leave, people, data up to; numbers and query-count tests | 2 |
| 6 | G1: `get_hr_analytics` on the shared calculation, "not linked"; tests | 1 |
| 7 | Morning checks: cron, enqueue, D5, D6, D18, stamp, failure log; tests | 1.5 |
| 8 | Data to review endpoints: list with re-check, confirm with lock and per-user limit; tests | 1.5 |
| 9 | Portal page: HR Analytics additions, Data to review panel; traced by hand | 1.5 |
| 10 | Synthetic 400 / 1,000 sites, timings, `EXPLAIN`, index migrate timing; `03` notes | 1 |
| | **Total** | **about 11 days** |

The leak fixes (2, 3) come early and do not depend on the calculation. G1 (6) needs the
calculation (5). All ten go to `dev` in **one push**, on your word.

---

## 13 · Decisions I need from you

| # | Question | My recommendation | Blocks |
|---|---|---|---|
| **D-1** | Create `Alvoraa Leader View Settings` in push 1 (minimum for the doubtful-day check, last-run stamp, SEC-10 rules), without its screen? Or keep it in push 2 and use a fixed 5 in push 1? | **Push 1**, and a new Single doctype, not HR Settings (BA-Q10) | Commits 4, 7 |
| **D-2** | "The figure is right" for leavers: only rule D18-2 (nobody left in 12 months), or also D18-1 (Left with no date)? | **D18-2 only.** A missing date is always a gap | Commit 8 |
| **D-3** | Should a D6 or D18-2 confirmation last only for that leave year, so it is asked again next year? | **Yes** | Commit 4 |
| **D-4** | Drop the per-item "last checked" field (it breaks AC-18) and show one "Last checked 06:32" for the page? | **Yes** | Commit 4 |
| **D-5** | The page re-check clears items but does not create new ones (creating needs `ignore_permissions`); new items appear at 06:30 | **Yes** | Commit 8 |
| **D-6** | Found while reading, **not fixed here:** in Attendance Insights, an HR login with **no Employee record** gets the organisation view with no company filter (all companies, limited only by User Permissions). Fixing it breaks slice 011's pinned test `test_central_hr_sees_every_store_in_the_portal_view`. Fix now with `permitted_companies()`, or leave for a separate change? | **Leave it**, record it as a known gap, and decide separately (it changes 011's decision) | Nothing in push 1 |
| **D-7** | `person()` for a **Left** employee inside HR's company: still allowed? | **Yes** — narrower than today, and HR sees leavers in the desk anyway | Commit 3 |
| **D-8** | Store HR and employees with **no branch**: leave them out of store HR's HR Analytics? | **Yes** (fail closed) | Commit 5 |
| **D-9** | The morning job skips tenants whose plan has no `analytics` | **Yes** | Commit 7 |
| **D-10** | Tolerance, photo-retention and org-chart keys are **not** on the setter allow-list (no screen uses them) | **Yes** | Commit 2 |
| **D-11** | Also ignore Frappe's automatic roles `All`, `Guest`, `Desk User` in the org-roles setting (the spec names three roles) | **Yes** | Commit 2 |
| **D-12** | Doubtful-day check skips employees with no branch in push 1 (the "No branch" group, BA-Q2, is a leader-view rule) | **Yes**, recorded as a gap | Commit 7 |
| **D-13** | HR Analytics period becomes "the month of the last day with attendance", to match the leader view (AC-10) | **Yes** | Commit 6 |
| **D-14** | Index method: Property Setter + `add_index` (mine) or `add_index` only (DevOps OPS-52)? | **Mine** (section 6.1) | Commit 1 |
| **D-15** | Push 1 waits until slice 010 group D is on `dev` | **Yes** | Push |
| Open from the spec | Who sends the Step 0 note to tenant HR (BA-Q14); final "not linked" copy (BA-Q5, UX) and Data to review empty-state and confirm-toast copy (BA-Q12, UX) | You name the sender; I use the drafts until UX replies | Release, commit 9 |

---

## 14 · Risks

| Risk | Size | What I do about it |
|---|---|---|
| HR sees numbers change with no warning | Medium | Tenant HR note before release (OPS-68); "Data up to" and the review line explain the change on screen |
| Demo tenant shows mostly "needs review" (kill criterion) | Medium | It reflects the data. Tell you now; the product manager may want the data fixed on ppj/dev before a demo |
| Index migrate holds Employee Checkin during a device sync | Low at 1,000 people | Timed first; run inside the maintenance hold (OPS-54) |
| Frappe drops single-column indexes on upgrade | Medium if ignored | Property Setters (D-14) |
| `worker-long` missing in a stack → checks never run | Medium | Stale line after 26 h; release check OPS-69 |
| Merge clash with slice 010 group D in `hrms-employee.html` / `hr_api.py` | Medium | Split by function; rebase often; whole-suite run after each rebase; stay out of Org Settings |
| Doubtful day only found next morning | Low | Stated on the page ("Checked again every morning") |
| A tenant with two companies on different fiscal years | Low | Leave year per company; tested |
| Slice 011's `alvoraa_branch` not yet on a tenant when push 1 migrates | Low | The same migrate runs 011's field installer and fill patch first (they are on `origin/dev`); the calculation checks the column exists |
| Attendance Insights still disagrees with HR Analytics (BA-Q4) | Low | Out of scope; recorded |

## Assumptions

- `[ASSUMPTION]` `dev` already has slice 011's `alvoraa_branch` field and fill patch (they are on `origin/dev`; I could not check the dev database).
- `[ASSUMPTION]` Timings in section 6.5 and 7 are estimates until commit 10 measures them.
- `[ASSUMPTION]` `frappe.qb` covers the grouped queries readably; where it does not I use parameterised `frappe.db.sql`.
- `[ASSUMPTION]` Nobody outside this machine is working in the files in section 11 (please confirm).

## Handoff note

To you: approve, adjust or redirect the strategy, and rule on D-1 to D-15. Nothing is built until you do.
To DevOps (07 §4): please comment on D-14 (index method), the per-company leave-year query, and the
decision to create the settings doctype in push 1. To the 010 session: I stay out of Org Settings and
the scorecard functions; please confirm `alvoraa_portal/hooks.py` is not in your plan. To the UX
designer: three pieces of copy (BA-Q5 "not linked", BA-Q12 empty state and confirm toast) are used as
drafts until you reply.

---

## Strategy approval (2026-09-15)

**Approved by the user** for building on the local instance only (not deploying). Includes:

- The approach in this file, with decisions **D-1 to D-15 as recommended** (D-6 left as a recorded known gap, decided separately).
- **D-14** resolved: Property Setter (`search_index`) + `add_index` for the six single-column indexes; `add_index` alone for the two two-column ones. DevOps §4 agrees (OPS-70), with a test that the indexes survive a re-sync (OPS-71).
- **OPS-72:** run the morning check once at the end of migrate, so HR does not see the old number for a day.
- **OPS-81:** fix forward is the default; rolling back reopens G1–G3.
- **OPS-75:** extend the `ignore_permissions` counter to cover the new files. (OPS-74, HRMS fork tests in CI, is a separate CI change.)
- **BA-Q14 (who tells tenant HR):** no note now — there are no live customers (production has none as of 2026-09-15). Revisit if a customer goes live before push 1 reaches `main`. Standing rule: any future change to a figure's formula ships with a short release note to tenant HR.
- **OPS-59 alert owner:** the user said "company leader" receives the three alerts (failed morning job, slow page, doubtful days found). To confirm with the user whether that means Alvoraa's own leader or each tenant's company head; not blocking the build.
- **D-15:** push 1 goes to `dev` only after slice 010 group D is on `dev`, and only on the user's word.
