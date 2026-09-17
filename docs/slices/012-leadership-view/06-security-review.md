---
slice: 012-leadership-view
artifact: 06-security-review
scope: push 1 only (US-1 to US-10)
author: hrms-security-privacy-engineer
date: 2026-09-16
status: review complete
code reviewed: local `dev` 5aad1ae for everything except DEF-8; DEF-8 verified at local `dev` c78efcd
inputs: [01c-security-privacy-requirements.md, 02-functional-spec.md, 03-implementation-notes.md, 04-test-report.md, 00-impact-analysis.md, 07-devops-inputs.md §3-§4, the code]
---

# 012 · Leadership view — push 1 security and privacy review

**I recommend. You decide.** No code was changed. No bench, docker, deploy or server
command was run. This is a read of the code and of other people's test evidence.

## The short answer

**Verdict: Ship-with-fixes. No Blocker.**

The three gaps this slice set out to close — G1, G2, G3 — are **really closed**. I read
each one in the code and can write the scenario that used to work and now does not.
DEF-8, which landed while I was reviewing, closes the last door onto no-branch
colleagues.

**One Major and eight Minor findings.** The Major is not in the new code: it is a door
`01c` told us to shut and push 1 shut only half of. HR Manager can still widen who sees
the whole org chart, through a different endpoint, with no record of who did it.

| Severity | Count | What |
|---|---|---|
| Blocker | 0 | — |
| Major | 1 | F1 — `set_cover_setting` still lets HR Manager grant org-chart visibility, no record |
| Minor | 8 | F2–F9 (below) |
| Worry | 5 | Listed separately; each needs more than a code read |

**Which head I checked.** Everything except DEF-8 was read at local `dev` **5aad1ae**,
the same commit the test engineer re-tested. The DEF-8 fix arrived as **c78efcd**
("Store HR see their own stores in the organisation attendance list…") while I was
reading. I reviewed that commit as well and it is in this report, marked.

**What I could not verify, plainly.** I ran nothing. The bench is claimed on the work
board right now for the DEF-8 test run, so I did not take it, not even for a rolled-back
probe. Everything below is a code read plus the test engineer's evidence in `04`. Where I
am leaning on their run rather than my own reading, I say so in the row.

---

## 1 · Every SEC and PRIV requirement in push 1 scope

Push 1 is US-1 to US-10. From `02` §"stories", that pulls in SEC-7, 8, 10 (part), 12
(part), 13, 14, 15, 16, 17, 18, 19, 22 and PRIV-1 (HR half), 10, 13, 14. Everything else
in `01c` belongs to push 2 and is listed at the end of this section so nothing is quietly
dropped.

| Req | Verdict | The mechanism, with file:line | The test that proves it |
|---|---|---|---|
| **SEC-7** endpoint hygiene: POST-only, plan-gated, no Guest, `no-store` | **Met** | `data_review.py:549` and `:638` are `@frappe.whitelist(methods=["POST"])` + `@requires_feature("analytics")`; `_require_hr` (`data_review.py:487-497`) refuses Guest and non-HR and sets `Cache-Control: no-store` | `test_data_review_012.TestThePage.test_endpoint_hygiene`, `test_people_who_are_not_hr_are_refused`, persona refusals in `test_personas_012` (17 tests). Test engineer's run, not mine |
| **SEC-8** no new `ignore_permissions`; SQL parameterised | **Met** | Zero matches for `ignore_permissions` in `data_review.py`, `org_figures.py` and both new doctype folders (I grepped). Scope reaches SQL only as bound parameters — `org_figures.condition()` at `:83-104` builds `%(scope_company)s` / `%(scope_branch)s` and never interpolates a value; only the alias and column name, which are constants in that file, go into the f-string | `test_portal_security_010` CEILINGS (`hr_api.py` 77 → 75, five new files pinned at 0); `test_hr_analytics_scope_012.test_a_branch_name_with_a_quote_is_just_a_value` |
| **SEC-10** minimum: System Manager only, 3–10, reason each time, every path | **Met** | Rule lives in the controller, so desk, REST, `frappe.client.set_value` and import all hit it: `alvoraa_leader_view_settings.py:26-44` (role check, range, "reason required", "refuse a save that changes nothing"), `:46-50` clears the reason after the history row, `min_group_size()` at `:53-66` falls back to **10** when the stored value is broken. DocPerm is System Manager create/read/write, HR Manager read only. `ensure_default()` at `:68-85` writes a whole record so the **first real change keeps a Version row** — that was a real catch by the engineer | `test_leader_settings_012` (14 tests); `test_morning_checks_edges_012.test_the_job_uses_the_stored_minimum` |
| **SEC-12** the minimum is not a Frappe default | **Met** | Stored in the Single only; `ALLOWED_ORG_SETTINGS` (`hr_api.py:2260`) refuses every other key, so no leader key can be written through Defaults | `test_the_minimum_is_not_a_frappe_default`; the G2 allow-list tests |
| **SEC-13** review records follow Frappe permissions; confirmations scoped, kept, immutable | **Met, with one leak on a path nobody uses on screen — see F2** | Records carry `company` and `alvoraa_branch`, so User Permissions apply. Portal reads go through `frappe.get_list` plus an explicit branch filter (`data_review.py:43-54`). Confirm (`:640-717`) checks, per record: exists → in scope company → in scope branch (so never a company-wide record for store HR) → `frappe.has_permission(write)` → right kind for the action → still Open; all-or-nothing, `for_update` row lock, one identical refusal message whatever the reason. `confirmed_by` is forced to the session user and the controller re-checks it (`alvoraa_data_review_item.py:82-90`). Hand edits on any path are refused (`:55-90`) | `test_data_review_item_012` (10), `test_data_review_012` (24), `test_personas_012` cross-company and same-named-branch tests. Mutation M2 and M3 in `04` §3 show the guards are real |
| **SEC-14** refusals logged the existing way, rule id, no values | **Met, with one deviation — see F6** | `access.refuse()` → `access.log_refusal()` (`hrms/hrms/alvoraa_hr_core/access.py:24-49`) writes one JSON line: user, endpoint, doctype, name, rule. No figure, no branch name, no key, no value. `_refuse_org_setting` (`hr_api.py:2263-2267`) deliberately logs neither the key nor the value | AC-23, AC-47, AC-51 tests |
| **SEC-15** no figures, names or scope in logs or error messages | **Partial** | The job's failure log is `{"company", "stage", "error type"}` only (`data_review.py:234-244`) and the page re-check's is `{"stage", "error type"}` (`:566-570`). Neither writes a traceback. **But** an unexpected exception anywhere else in the two endpoints still produces an ordinary Frappe Error Log, and nobody has forced that to check what it contains | `test_morning_checks_012.test_a_failure_is_logged_without_figures_and_the_stamp_stays_old` covers the job. **No test on the endpoint path** — `01c` asked for one ("patch a query to raise") |
| **SEC-16** Step 0: scope HR Analytics (G1) | **Met** | See §2 below for the full read. `hr_api.py:407-411` resolves scope and fails closed; every count carries `emp_where`; the two name lists use `frappe.get_list` with `scope_filters` (`:475-484`, `:509-515`) | `test_hr_analytics_scope_012` (10), `test_personas_012`. Mutation M1 went red only after the test engineer tightened it — worth knowing that the first version of that test would have passed a widened scope |
| **SEC-17** Step 0: scope `person()` and `filter_options()` (G3) | **Met** | See §2. `person()` at `attendance_analytics.py:552-580`, `_in_organisation` at `:535-549`, `filter_options` at `:462-504`, `_linked_branches` at `:506-519`. 12-month cap at `:577-580`, cut rather than refused | `test_attendance_scope_012` (9 at 5aad1ae, +3 at c78efcd), `test_personas_012`. Mutation M3 red |
| **SEC-18** `get/set_org_setting` allow-list (G2) | **Partial — F1** | `ALLOWED_ORG_SETTINGS = {"kra_link_mandatory": ("0","1")}` (`hr_api.py:2260`); both endpoints refuse any other key and any value outside the pair (`:2270-2288`). That half is exactly right. **The second half of SEC-18 is not done:** it said visibility-granting keys, *if they stay editable anywhere*, must be System Manager only with a change record. `alvoraa_org_full_reach_roles` and `alvoraa_org_managers_see_all` are still HR-Manager-writable through `set_cover_setting` (`hrms/hrms/alvoraa_org_structure/settings.py:140-147`) with no record | `test_org_settings_allowlist_012` (10) proves the allow-list. **Nothing tests the other endpoint** |
| **SEC-19** org-roles shortcut blocked by structure | **Met** | `NEVER_ORG_ROLES` (`attendance_analytics.py:62-63`) drops Leadership, Employee, Employee Self Service, **and** All, Guest, Desk User — the engineer added the last three, which is right: `All` would have granted everyone. `_org_roles()` (`:66-78`) subtracts them whatever the stored setting says, and logs role names only | `TestOrgRolesGuard` (4) plus `test_leadership_and_employees_cannot_open_another_person_even_if_listed`, `test_filter_options_refused_for_leadership_and_employee` |
| **SEC-22** the doubtful-day job: counts only, groups ≥ the minimum | **Met for the rule it was written for; partial overall — F8** | D5 gates on `having expected >= minimum` inside `_doubtful_days` (`data_review.py:310-383`), reading the stored minimum. Records hold no employee field at all (doctype JSON has none). **D18-1 has no minimum gate** (`:294-303`): a branch of 4 gets a "1 person left with no leaving date" record | `test_morning_checks_012.TestSmallGroups`, `test_a_four_person_branch_is_never_checked`, `test_a_group_of_exactly_the_minimum_is_checked`, `test_data_review_item_012.test_no_employee_field_and_no_name` |
| **PRIV-1** (HR half) totals only, allowed fields only | **Met for the new screen; a miss on the old one — F3** | `data_review_items` returns counts, dates, company and branch names, and two percentages. No employee anywhere. `org_figures` never selects `leave_type` or `description` — I checked every SELECT in the file. **But** `get_hr_analytics` still asks for `gender` in `recent_employees` (`hr_api.py:512`) and the page never draws it (`hrms-employee.html:8700-8701` renders name, designation, department, joining date only) | `test_central_hr_sees_every_kind_with_counts_and_no_people` (AC-36). Nothing checks the HR Analytics payload for unused sensitive fields |
| **PRIV-10** doubtful days are not a side door | **Met** | Detection only for groups at or above the minimum (same gate as SEC-22); the "with doubtful days" figure is computed on the same scoped population (`org_figures.open_doubtful_counts` `:197-225`, `rate_with` `:227-233`) | Small-group and boundary tests in `test_morning_checks_012` |
| **PRIV-13** purpose limitation | **Met** | `org_figures.PURPOSE = "operational-oversight-only"` (`:34`) with the reason written above it; the appraisal attendance score keeps its own separate formula in `hrms/alvoraa_hr_core/attendance_score.py`, untouched | `test_org_figures_012.TestAppraisalScoresDoNotMove` (2) and the hrms `test_attendance_score` (11). The import check `01c` asked for (`alvoraa_goals` must not import the leader module) **does not exist yet** — for push 2 |
| **PRIV-14** retention, declared | **Met as written, and that is the point** | The doctype description says "Kept 13 months after the date it concerns plus one year (declared, not purged automatically)". That is honest. There is no retention engine (feature map A6) | **No test, and there cannot be one.** This is a declared retention, not an enforced one. Say that on a questionnaire, not "we purge after 13 months" |

**Out of push 1 scope, on purpose:** SEC-1 to SEC-6, SEC-9, SEC-11, SEC-20, SEC-21, and
PRIV-2 to PRIV-9, PRIV-11, PRIV-12, PRIV-15, PRIV-16. All of them are push 2 (the leader
screens, the cache, the settings page, the employee "who can see" line). None has been
built early and none has been quietly dropped — I checked the spec's story table.

**Score:** 12 met, 3 partial, 1 not met (the second half of SEC-18, counted inside the
SEC-18 "partial" row as F1).

---

## 2 · Are the three original gaps really closed? I read the code.

### G1 · `get_hr_analytics` scoping — **closed**

`hr_api.py:390-555`. The old function had no company or branch condition anywhere.
Now:

- `scope = of.hr_scope()` at `:407`. `hr_scope` (`org_figures.py:60-79`) takes companies
  from `permitted_companies()` and narrows them by the caller's **Branch** User
  Permissions, counting only permissions that apply to Employee
  (`applicable_for in (None, "", "Employee")`). That last clause matters: a Branch
  permission scoped to Salary Slip grants nothing here.
- **Fail closed (BA-Q5).** `if scope.not_linked: return {"not_linked": True}` at
  `:408-411`. Not a partial answer, not a zeroed one — the response carries **no
  figures, no headcount and no names at all**. The page then shows the "how to get
  linked" message. I checked `not_linked` itself: it is `not self.companies`
  (`org_figures.py:52-54`), so an empty company tuple is the only way in, and
  `permitted_companies` returns `[]` for anyone who is not HR. This is the right shape.
- Every raw count carries `emp_where` from `employee_condition(scope)` (`:419`), used at
  `:427`, `:434`, `:441`, `:451`, `:497`, `:505`.
- The two lists that carry **names** use `frappe.get_list` with `scope_filters`
  (`:475-484` confirmations due, `:509-515` recent employees) — so the caller's own User
  Permissions apply *on top of* the scope. Both `ignore_permissions=True` calls are gone.
- Attendance and leave come from `org_figures`, whose `condition()` always pairs company
  **and** branch (`:83-104`), so the same branch name in two companies cannot bleed.
- LV2 is fixed too: leave use divides by this leave year's allocations, per company
  (`leave_figures`, `org_figures.py:278-338`).

**Scenario that used to work and now does not.** Store HR (HR User, Branch permission
"Lakeside Mall") calls `get_hr_analytics`. Before: every branch's totals plus names,
departments, joining dates and the gender of the 10 newest joiners **anywhere**. Now:
Lakeside only, and if they are not linked to a company at all, nothing.

### G2 · `set_org_setting` allow-list and the org-roles block — **closed for the endpoint, half-open elsewhere**

`hr_api.py:2255-2296`. The allow-list is one key with two allowed values, checked on both
read and write, with the type checked first (`isinstance(key, str)`) so a dict or list
cannot slip past. A refusal logs the rule id and **not** the key or the value — that is
the right call, because the key name is itself a hint about what exists.

`alvoraa_attendance_org_roles`, `alvoraa_checkin_photo_retention_days`,
`alvoraa_attendance_short_tolerance_mins`, `currency` and every other Frappe default are
now unreachable from this endpoint. I grepped the whole app tree for other
`frappe.db.set_default(` callers: there are exactly two, this one and
`settings.py:146`.

**Q6 / SEC-19 is a real structural block, not a note.** `NEVER_ORG_ROLES`
(`attendance_analytics.py:62-63`) is subtracted inside `_org_roles()` itself, so every
caller of `_may_see_organisation()` gets the narrowed set. Someone who types
`"HR User,Leadership"` into the setting achieves nothing, and a line lands in the
security log naming the ignored roles (role names only — no user, no figures). Adding
`All`, `Guest` and `Desk User` was the engineer's own idea and it is the more important
half: `All` is held by every user on the site.

**What is still open** is `set_cover_setting` — finding F1.

### G3 · `person()` and `filter_options()` — **closed**, and DEF-6/DEF-8 close the last door

- `person()` (`attendance_analytics.py:552-580`). The old test was
  `_may_see_organisation()` alone — any org-role holder could open anybody. Now it is
  `employee == me.name` **or** in the caller's reporting line **or**
  (`_may_see_organisation()` **and** `_in_organisation(employee, me)`).
  `_in_organisation` (`:535-549`) does one indexed lookup with the caller's own company
  and, for location HR, an explicit `branch in (their branches)`. The date range is cut
  to 12 months (`:577-580`) rather than refused — correct choice, a long range is a
  typo, not an attack. A non-string or empty `employee` is refused at `:556-557`.
- `filter_options()` (`:462-504`) swapped `frappe.get_all` for `_org_read()`
  (`get_list` for everyone except System Manager, `:521-527`) and added the same branch
  filter. The manager list now drops a manager whose name the caller may not read,
  rather than showing a bare employee id — a nice detail: an id is still a disclosure.
- **DEF-8, at c78efcd.** `_population(view="organisation")` (`:160-201`) had no branch
  filter, so store HR still got head-office colleagues **with names, days and
  `leave_by_type`** — more than `person()` ever showed. The fix at `:172-184` uses the
  same `_linked_branches()` helper: a branch the caller does not hold is **refused with
  one security line** (SEC-17), not silently trimmed, and an absent branch filter becomes
  `branch in (their branches)`, which excludes the empty-branch records that Frappe's
  non-strict User Permissions were letting through. `_linked_branches()` returns `None`
  for anyone with no Branch permission, so central HR and System Manager are untouched
  and slice 011's pinned tests still describe users this code does not reach.

**I have not seen DEF-8 run.** The commit adds three tests
(`test_attendance_scope_012.py:171-200`), and the work board says the bench is in use
for exactly that run right now. My verdict on DEF-8 is a code read. Ask for the run
result before you push.

**Route-by-route answer to "can store HR still reach a no-branch person?"** — I checked
every route named in the task and then looked for others:

| Route | File:line | Store HR reaches no-branch people? |
|---|---|---|
| `attendance_analytics._population` (organisation list) | `:172-184` | **No**, since c78efcd. Was **yes** at 5aad1ae (DEF-8) |
| `attendance_analytics.person` | `:535-549`, `:558-575` | No |
| `attendance_analytics.filter_options` | `:462-470` | No |
| `hr_api.get_hr_analytics` | `:419-422`, `:475-484`, `:509-515` | No |
| `data_review.data_review_items` | `:43-54`, `:574-578` | No — explicit branch filter on top of User Permissions |
| `data_review.data_review_confirm` | `:678-687` | No — and a company-wide record is refused outright |
| Portal context badge | `hr_api.py:156-167`, `data_review.py:56-74` | No — same `item_filters`, and it returns a number, never a record |
| Desk / REST `/api/resource/Alvoraa Data Review Item` | doctype JSON perms | **Company-wide records: yes.** See F2. No employee data, counts only |
| Desk / REST `/api/resource/Employee` | pre-existing | Yes, and always has — Frappe's non-strict User Permissions. Not this slice's; recorded as R-pre below |
| `attendance_analytics.summary(view="team"/"mine")` | `:141-158` | Only their own reporting line — unchanged |

---

## 3 · The abuse cases from `01c` that apply to push 1

| ID | Result now | Evidence |
|---|---|---|
| **AB-13** parameters: another branch, another company, `min_group=1`, free dates | **Held.** The two new endpoints take only `items` (list of ≤ 40 strings) and `action` (one of two literals) — `data_review.py:658-663`. No scope parameter exists to abuse. `person()` takes an employee id but checks it (`:558-575`); `summary()` takes a branch and now **refuses** one outside the caller's set (`:180-184`). The minimum is never a parameter — it is read from the Single | Code read + `test_personas_012` |
| **AB-18** store HR confirms another store's doubtful day by record name | **Held.** `data_review_confirm` `:676-687`: company check, branch check, `has_permission(write)`, kind check, status check — all-or-nothing, identical refusal message so the answer never reveals that a record exists elsewhere | `TestStoreHrConfirms` (4), `test_store_hr_same_branch_name_in_another_company_is_refused` |
| **AB-21** "Leadership" added to the org roles "until the view ships" | **Held by structure.** `NEVER_ORG_ROLES` | `TestOrgRolesGuard` |
| **AB-24** two companies share a branch name | **Held on every figure path** — `org_figures.condition()` always pairs company and branch. **One narrow hole left** on the Attendance Insights path: see F7 |
| **AB-26** Guest or plain employee calls a leader endpoint | **Held.** `_require_hr` refuses Guest by name and everyone without HR Manager / HR User. The badge (`_with_review_count`) returns the context untouched for anyone who is not HR, so a non-HR user's portal load runs **no** review query at all | `test_people_who_are_not_hr_are_refused`, badge probe in `04` R3 |
| **AB-19 / AB-20** HR Manager writes the minimum, or reads all `Version` rows, through REST | **AB-19 held** — the rule is in the controller, and the DocPerm gives HR Manager read only. **AB-20 is push 2** (SEC-11 endpoint). I checked: nothing in this slice grants HR Manager read on `Version` | `test_leader_settings_012` |
| AB-1 to AB-12, AB-14 to AB-17, AB-22, AB-23, AB-25 | **Push 2.** They are all about leader screens, suppression, the cache or the employee line, none of which exists yet | — |

**Do the "Data to review" items leak names or figures to the wrong scope?** No, on the
screen. The record type has **no employee field at all** — I read the JSON field list,
and the counts are `expected_count`, `absent_count`, `checked_in_count`,
`affected_count`, `people_count`, `days_allocated`. The only figures that leave are two
attendance percentages, computed over the caller's own scope
(`_figures_for_confirming`, `data_review.py:534-547`). A store HR person never sees a
company-wide card on the page (`item_filters`, `:43-54`). The one exception is the REST
path, F2.

**Do the "needs review" reasons reveal anything about an individual?** Mostly no, and
where they could, only to people who could already see it:

- A doubtful day says "96–99% marked absent, 2% checked in" for a branch on a date —
  about a branch, not a person, and only for branches at or above the minimum.
- **D18-1 is the one to watch.** "1 person in Hilltop Kiosk is marked Left with no
  leaving date" in a 4-person branch is, to that branch's HR person, effectively one
  named individual. Today only HR sees it, and HR can open the same Employee list
  anyway, so nothing is disclosed that was not already reachable. **It becomes a real
  problem in push 2**, when leaders see a "Needs review" label on a group. Finding F8.

**Do the slow-call log, the error logs or the job's logs carry names, figures or
identifiers?**

| Log | What it holds | Verdict |
|---|---|---|
| Slow call (`org_figures.log_if_slow`, `:343-366`) | event, endpoint, scope **kind**, number of branches, duration, and only `int/float/bool` extras — the filter at `:363` drops anything else | Clean. No company, no branch name, no figure |
| Job failure (`data_review._log_failure`, `:234-244`) | company name, stage, exception **type**. No traceback, deliberately | Clean of personal data. A company name is not personal data |
| Page re-check failure (`:566-570`) | stage and exception type | Clean |
| Security refusals (`access.log_refusal`) | user, endpoint, doctype, document name, rule | **Carries an Employee id** on the `person()` path. Finding F6 |
| Minimum-broken error (`min_group_size`, `:62-64`) | a fixed sentence, no value | Clean |

**Can confirmations be forged or replayed by a lower-privileged user?** No, on four
independent counts, which is the right number for a record that changes a figure:

1. POST only, HR role only, plan-gated (`:638-641`, `_require_hr`).
2. `confirmed_by` is set server-side to `frappe.session.user` (`:709`) and the
   **controller re-checks it** (`alvoraa_data_review_item.py:86`) — so even a hand-built
   save cannot attribute a confirmation to somebody else.
3. Replay: a second confirm of the same record finds `status != "Open"` and throws
   (`:692-694`). A Confirmed record can never be reopened by the job or the page
   (`apply_findings` `:441-442`, controller `_check_rule_update` `:76-81`).
4. Rows are taken `for_update` in a sorted, deterministic order (`:675`), so two HR
   people racing cannot both win and cannot deadlock. **Proven by the lock in the code
   and by a second confirm being refused, not by two real connections** — the test
   engineer says so plainly in `04` and I agree that is a gap worth one manual check.

---

## 4 · New attack surface

### The two new doctypes

| | `Alvoraa Data Review Item` | `Alvoraa Leader View Settings` |
|---|---|---|
| Read | HR Manager, HR User, System Manager | System Manager, HR Manager |
| Write | HR Manager, HR User | System Manager |
| Create | **nobody** (server inserts run as the job's user) | System Manager only (a Single's first save is an insert) |
| Delete | **nobody** | n/a (Single) |
| Report / export | HR Manager, HR User | no |
| Row scoping | `company` + `alvoraa_branch` fields → User Permissions apply | Single, no scoping needed |
| Change history | `track_changes` on | `track_changes` on |

**Write without create or delete is the right shape** — a record can be confirmed but
never conjured or destroyed. And the write that the DocPerm allows is then almost
entirely taken away again by the controller: every field is `read_only`, the name is a
hash of the finding's key so it cannot be re-pointed, and `validate`
(`alvoraa_data_review_item.py:55-90`) refuses any save that does not carry one of two
server-set flags. I traced the paths: desk save, `/api/resource` PUT,
`frappe.client.set_value` and data import all go through `validate`. `frappe.db.set_value`
does not — but it is not whitelisted, so it is not reachable from a browser.

**The one real gap is listing, not writing** — F2.

### The scheduler job

`hooks.py` adds a `cron` key, `"30 6 * * *"` → `data_review.enqueue_morning_checks`
(`data_review.py:193-195`), which enqueues on the `long` queue with
`job_id="leader-data-checks"` and `deduplicate=True`, so a double fire is one job.
`run_morning_checks` (`:198-231`) returns immediately for a tenant without the analytics
feature, commits per company, and only stamps "last checked" when every company
finished. It writes counts. It reads Attendance, Employee Checkin and Employee with
grouped SQL and never loads a person. It runs as the scheduler user, which is the normal
and correct posture for a system job — there is no user input anywhere in its path, so
there is nothing to inject.

Two things I would watch rather than block: it is a new dependency on `worker-long`, and
`after_migrate` queues it (`hooks.py`), so the first run happens at deploy time — which
is deliberate (DevOps §4 point 3: otherwise HR's figure jumps the next morning).

### The portal context badge

`hr_api._with_review_count` (`:156-167`) → `data_review.open_count_for_hr` (`:56-74`).
It returns **an integer and nothing else**, only for `is_hr`, only when the plan has
analytics, using the same scoped `get_list`. It is added **outside** the one-hour
context cache, so it cannot be served to the wrong user by a stale cache; the cache key
is per user (`hr_api.py:101`) in any case. It swallows every exception and returns 0 — a
badge is not worth breaking a page for, and 0 is the fail-closed answer. No extra HTTP
call. This is a small, well-shaped addition.

### New whitelisted endpoints

Exactly two. I diffed the whole slice range to be sure nothing else was added.

| Endpoint | Methods | Permission checks, in order | Rate limit |
|---|---|---|---|
| `alvoraa_portal.data_review.data_review_items` | POST only | `requires_feature("analytics")` → `_require_hr` (Guest out, HR Manager/HR User/Administrator only) → `hr_scope()` fails closed → every read scoped by company + branch | **None** — F5 |
| `alvoraa_portal.data_review.data_review_confirm` | POST only | same, then per record: exists, company, branch, `has_permission(write)`, kind, status Open; ≤ 40 items per call | **30 per hour per user**, counted in Redis by user id, not IP (`:501-516`, `CONFIRMS_PER_HOUR` at `:476`). Cache trouble never blocks HR — correct, availability over a soft limit |

`get_hr_analytics`, `get_org_setting`, `set_org_setting`, `person` and `filter_options`
already existed; push 1 narrowed all five. None gained a parameter.

---

## 5 · Privacy

**Data minimisation of what the screens return.** Good, with one miss.

- `data_review_items` returns counts, dates, company and branch names, two percentages,
  and record ids. No person, anywhere, by construction — the doctype has no employee
  field, so there is nothing to leak. That is the right shape: the safe thing is the
  only thing available.
- `org_figures` never selects `leave_type` or `description`. I read every SELECT in the
  file to check that, rather than trusting the module docstring.
- **The miss:** `get_hr_analytics` still asks the database for `gender` in
  `recent_employees` (`hr_api.py:512`) and the page never shows it
  (`hrms-employee.html:8700-8701`). Sensitive attribute, in the response body, in the
  browser, for no purpose. One word to delete. F3.

**Retention.** Declared, not enforced, and the documents say so honestly.

| Object | Declared | Enforced? |
|---|---|---|
| `Alvoraa Data Review Item` (incl. confirmations, which live on the same record) | 13 months after the date it concerns, plus one year | **No.** No purge exists anywhere in the product (feature map A6) |
| Settings history (`Version` rows) | Life of the tenant, at least one year | No purge; `Version` is outside Frappe's log clean-up, which DevOps confirmed in the Frappe source |
| Security refusal log | At least one year (DPDP Rules Rule 6(1)(e)) | File-based; rotation not verified by me |

Two things follow. First, on a questionnaire the answer is "we declare a retention
period; automatic purge is on the roadmap", never "we delete after 13 months". Second,
confirmations are **decision-bearing** — they are the record that defends a changed
attendance figure — so when the retention engine is built, these records need a legal
hold, not a blanket delete. Worth writing into the retention backlog item now, while
somebody remembers why.

**DPDP notice implications.** Nothing in push 1 collects new personal data, and nothing
makes an automated decision about a person, so on my reading no new notice obligation is
triggered and no DPIA gate opens. What *does* change is who sees what: HR Analytics
narrows (fewer people see less), and nothing widens. A narrowing needs no notice. The
employee-facing "who can see" line (PRIV-12) is push 2, and that is where the notice
conversation properly belongs. **I am not a lawyer** — CQ1 and CQ4 in `01c` are still
open with the compliance owner, who is still not named (F-open).

**Do the reasons reveal anything about individuals?** Covered in §3 above. Short answer:
not today; D18-1 on a tiny branch will in push 2.

---

## 6 · Findings

Each one names the actor, the state, the path and what they see. If I cannot write that
sentence, it is in the worries list instead.

### F1 · Major — HR Manager can still widen org-chart visibility, with no record

`hrms/hrms/alvoraa_org_structure/settings.py:140-147`.

**Scenario.** An HR Manager (or anyone holding that login) posts to
`hrms.alvoraa_org_structure.settings.set_cover_setting` with
`key="alvoraa_org_full_reach_roles"`, `value="HR Manager,HR User,System Manager,Employee"`.
`set_cover_setting` calls `frappe.only_for(["HR Manager","System Manager"])`, finds the
key in `DEFAULTS` (`:53`), and writes it. From the next request **every employee can roam
the whole org chart** — names, designations and the reporting line of the entire company.
`alvoraa_org_managers_see_all` (`:58`) is the same story for managers. **Nothing records
who did it**: `frappe.db.set_default` writes a Defaults row and commits, with no Version
and no security log line.

**Why this is a finding against push 1 and not just old code.** SEC-18 named these two
keys explicitly and said that if they stay editable anywhere, that path must be System
Manager only and must leave a change record. Push 1 shut the door SEC-18 was written
about and left the one SEC-18 also named. The result is that P2 ("only a System Manager
changes sensitive settings") is still untrue, which is exactly the state `01c` asked us
to leave behind.

**Recommended fix (small).** Split `DEFAULTS` into ordinary keys and access-granting
keys. For the access-granting ones: `frappe.only_for(["System Manager"])`, and one
`log_refusal`-style line recording who changed what, or move them onto the new settings
doctype where `track_changes` does it for free. Roughly the same size as the G2 fix.

### F2 · Minor — location HR can list company-wide review items through desk or REST

Doctype JSON permissions (HR User: read, write, report) + `data_review.py:43-54`.

**Scenario.** Store HR (HR User, Branch permission "Lakeside Mall") opens
`/api/resource/Alvoraa Data Review Item?fields=["*"]`, or the desk list view. Frappe's
User Permissions filter by Branch — but the site does not run strict user permissions
(the test engineer proved this in probe P1), so records with an **empty**
`alvoraa_branch` pass. Those are the company-wide records: D6 ("leave used", carrying the
company's requests, people with allocations and days allocated) and D18-2. The explicit
branch filter that keeps them off the portal page lives only in `item_filters()`, which
the REST path does not go through.

**What leaks:** company-wide counts, to someone scoped to one store. No names, no
employee ids, no leave types. **Confirming those records is still refused** — that check
is in the endpoint and works (`:680-683`).

**Fix.** A `permission_query_conditions` entry for the doctype (there is none —
`hooks.py:167-169` registers one only for Employee Checkin), or drop `report` from the
HR User DocPerm and rely on the portal path. The query condition is the better
mechanism: it is one rule that covers every list, report and export, including the ones
nobody has written yet.

### F3 · Minor — `gender` is fetched and never shown

`hr_api.py:512`. `recent_employees` selects `gender` for the 10 newest joiners; the page
renders name, designation, department and joining date only
(`hrms-employee.html:8700-8701`). A sensitive attribute travelling for no purpose, into
a response that (see F4) has no `no-store` header. Delete the word.

### F4 · Minor — `get_hr_analytics` allows GET and sets no `Cache-Control`

`hr_api.py:388` is a bare `@frappe.whitelist()`, so the endpoint answers GET as well as
POST, and unlike the two new endpoints it never sets `Cache-Control: no-store`. The
response carries employee names, designations, departments and joining dates. A GET
response with no cache header can be stored by a browser or an intermediary proxy — on a
shared store PC that is a real, if unglamorous, exposure. The new endpoints in
`data_review.py` do this correctly (`:496`), so the pattern is already in the codebase.

*I did not verify what header Frappe sets by default on `/api/method` responses on our
build — that needs a running bench. The fix is a one-liner either way.*

### F5 · Minor — `data_review_items` has no rate limit, and it writes

`data_review.py:549-583`. Every call runs `recheck()`, which re-runs the leave and
leavers rules for the caller's whole scope and **saves what changed** (`apply_findings`,
`allow_create=False`). A logged-in HR user looping this endpoint drives repeated writes
and ~12 queries a time against Attendance, Employee and the two leave tables. OPS-40 set
a per-user limit for confirms; the read endpoint, which is the expensive one, has none.
Suggest the same `_within_hourly_limit` helper with a read budget (say 60 a minute), or
skip the re-check when the last one was under a minute ago.

### F6 · Minor — the refusal log records the employee id that was asked for

`attendance_analytics.py:573-574` calls `refuse(..., "Employee", employee)`, and
`access.log_refusal` writes `name` into the security log line. So a refused `person()`
call leaves `{"doctype":"Employee","name":"HR-EMP-00042"}` in a log kept for a year.

That is an identifier of a data subject in an operational log. It is defensible — it is
the single most useful field when investigating whether someone was probing employee
ids — and it is the shared slice-010 mechanism, documented as "document names and user
ids only". But it **contradicts SEC-14 as `01c` wrote it** ("never … the requested
scope's values"). I am not asking for it to be removed; I am asking for it to be a
decision with a name and a date, and for SEC-14's wording to be corrected to match, so
the next reviewer does not re-open this.

### F7 · Minor — AB-24 is still open for an HR user with no Employee record

`attendance_analytics.py:539-548` (`_in_organisation`) and `:167-168` (`_population`)
apply the company filter only `if me and me.company`. An HR user with **no Employee
record**, no Company permission and one Branch permission therefore gets a branch filter
with no company filter. If two companies on the site use a branch of the same name, that
caller reaches the other company's people in that branch — names, days and leave types.

Narrow (it needs all three conditions plus a shared branch name), and D-6 already
records "HR with no Employee record sees all companies" as an accepted decision. But
`org_figures.hr_scope` solves exactly this by falling back to `permitted_companies()`,
and using the same helper here would close it in two lines.

### F8 · Minor — the minimum-group gate covers D5 only

`data_review.py:294-303`. D18-1 creates a per-branch record however small the branch is,
so a 4-person branch can get "1 person marked Left with no leaving date". Harmless in
push 1 (only HR sees it, and HR can already open that Employee list). **It stops being
harmless in push 2**, when a leader sees a "Needs review" label attached to a group.
Either gate D18-1 on the minimum like D5, or make sure the push-2 leader-facing label
carries no count. Please carry this into the push 2 requirements rather than the
backlog.

### F9 · Minor — SEC-15 has no test on the endpoint path

`01c` asked for a test that patches a query to raise inside a leader endpoint and asserts
that neither the Error Log nor the response carries a figure, a name or a branch name.
The job's failure path has that test; the two endpoints do not. Small test, and it is the
kind that catches a future contributor adding `str(scope)` to an error message.

---

## 7 · Worries — not findings, because I cannot write the full scenario

1. **No browser run at all.** 360 px, 200% zoom, keyboard through the confirm dialog and
   the desk links are unverified by eye, by anyone. A confirm dialog that can be
   triggered by a stray Enter is a security-shaped problem, not only a usability one.
2. **The DEF-8 fix has no run evidence yet.** Code read only, by me. The test run was in
   flight on the bench as I wrote this.
3. **`01c` §10's OPS-32 conditions C1, C2, C5 and the HSTS check are still unrun** (V3,
   V4). They need a bench. Nothing in push 1 changes that verdict, but the conditions
   were attached to an approval and none has been discharged.
4. **`apply_strict_user_permissions` is 0 on this site.** That single setting is why
   DEF-6, DEF-8 and F2 all exist — three symptoms, one cause. Turning it on is a
   tenant-wide behaviour change well outside this slice, but somebody should own the
   question, because we are now fixing the same class of bug one endpoint at a time.
5. **No two-connection race test** on a confirmation, and no concurrency rehearsal. The
   lock reads correctly; I have not seen it under two real connections.

---

## 8 · Compliance verification

| Obligation | Source, last verified | Push 1 position |
|---|---|---|
| DPDP — purpose limitation | Baseline §2, 24 Aug 2026 | **Met.** `org_figures.PURPOSE`; appraisal formula untouched and pinned by a test |
| DPDP — data minimisation | Baseline §2, 24 Aug 2026 | **Met for the new screens; one miss (F3)** |
| DPDP — notice | Baseline §2, 24 Aug 2026 | **Not engaged.** No new collection, no new visibility. The employee line is push 2. CQ4 still open |
| DPDP s.7(i) legitimate use | Act text, 15 Sep 2026 | Unchanged; ⚠ counsel (CQ1) |
| DPDP Rules 2025 Rule 6(1)(c)/(e) — access visible in logs, kept a year | Rules text, 15 Sep 2026 | **Partial.** Refusals are logged with a rule id. Allowed HR reads are not logged one by one. ⚠ CQ3 |
| CERT-In — 180-day India-resident logs | Baseline §3, §3a, 6 Sep 2026 | **Still open, and not this slice's.** Push 1 adds two new log streams (`leader_view`, the job's Error Logs), both in France like everything else |
| DPDP — breach clocks | Baseline §2, §3 | No workbench exists (feature map A5). Unchanged by this slice |
| EU AI Act Art 5 / GDPR Art 22 | Baseline §4, 24 Aug 2026 | **Not engaged.** No automated decision about a person anywhere in push 1 |
| GDPR Art 5, Art 88 | Baseline §4, 24 Aug 2026 | Anticipatory until the founder answers F2/EU exposure |
| OWASP ASVS 5.0 L2 — access control, logging | Baseline §5, 24 Aug 2026 | **Improved.** Server-side scope, deny by default, refusals logged, no new `ignore_permissions` |
| ISO 27001 — access control | Baseline §5, 24 Aug 2026 | Improved. Access recertification evidence starts in push 2 |

All baseline entries I leaned on were verified 24 Aug or 6 Sep 2026, and the two DPDP
points on 15 Sep 2026. The oldest is 23 days old, so **nothing here is stale** under the
90-day rule. **I am not a lawyer**; every ⚠ above is a question for counsel or the
compliance owner, and the compliance owner is still not a named person.

---

## 9 · Residual risk

Carried forward from `01c` §13, plus what push 1 adds. **None of these has been accepted
yet — each needs a name and a date, and an unnamed accepted risk is just an accident
waiting for an owner.** I propose Surbhi as owner for all of them.

| # | Risk | Size | Owner | Accepted on |
|---|---|---|---|---|
| **N1** | **F1** — HR Manager can widen org-chart visibility with no record, through `set_cover_setting` | **Major** | — | — |
| N2 | **F2** — location HR can list company-wide review item counts through desk or REST | Minor | — | — |
| N3 | **F7** — AB-24 remains open for an HR user with no Employee record and a shared branch name | Minor | — | — |
| N4 | **F8** — D18-1 creates a record for a branch under the minimum; becomes leader-visible in push 2 | Minor now, Major in push 2 | — | — |
| N5 | **F6** — the refusal log carries the employee id that was asked for | Minor | — | — |
| N6 | Retention is **declared, not enforced** (PRIV-14). Nothing purges. Confirmations are decision-bearing and will need a legal hold | Medium | — | — |
| N7 | DEF-8's fix is verified by code read only, at c78efcd | Low, and closes with one test run | — | — |
| N8 | No browser run: dialogs, 360 px, keyboard, desk links | Medium (a11y and mis-click) | — | — |
| N9 | `apply_strict_user_permissions` is off site-wide — the root cause behind DEF-6, DEF-8 and F2 | Medium | — | — |
| N10 | No real two-connection race test on a confirmation | Low | — | — |
| R9 (carried) | System Manager reads everything in the desk as CXO | Known, wide | Recorded in slice 010 | 2026-09-14 |
| R-pre (carried) | Frappe's non-strict User Permissions let empty-link records through on `Employee` in the desk | Pre-existing, not widened here | — | — |

---

## 10 · Verdict and what I recommend

**Ship-with-fixes.** Push 1 makes the product meaningfully safer than `dev` is today: it
closes three live gaps, adds two doctypes with a careful permission shape, and adds no
`ignore_permissions`. I found no Blocker and nothing that would make me hold the slice.

Before the push to `dev`, in this order:

1. **F3 and F4** — delete `gender` from `recent_employees`, add `no-store` to
   `get_hr_analytics`. Two lines, no behaviour change, no test to rewrite.
2. **Get the DEF-8 test run result** (N7). It is already running.

Before the push to `main`:

3. **F1** — the `set_cover_setting` split. This is the one I would not let drift: it is
   the other half of a requirement we already agreed, and it will be forgotten the
   moment push 2 starts.
4. **F2** — a `permission_query_conditions` entry for the review doctype.
5. **F9** — the SEC-15 endpoint test.

For the push 2 requirements, not for the backlog:

6. **F8** — gate D18-1 on the minimum, or keep the count off the leader-facing label.
7. **F7** — reuse `permitted_companies()` in `_in_organisation` and `_population`.
8. **F6** — decide and record the employee-id-in-refusal-log question, and correct
   SEC-14's wording to match the decision.

And one thing for you to name rather than fix: **N9**, who owns the
`apply_strict_user_permissions` question. We have now fixed the same class of bug three
times in one slice.
