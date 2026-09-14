---
slice: 010-portal-security-fixes
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-09-14
status: draft
inputs: [docs/slices/009-ess-portal-redesign/00-assessment-and-plan.md (§1a S1–S10, §6 decisions of 2026-09-14), docs/slices/009-ess-portal-redesign/appendix-a-frame.md, appendix-b-home-inbox.md, appendix-c-time-pay.md, appendix-d-growth-team-people.md, code at slice/010-portal-security-fixes = origin/dev 4e3ba28, read-only checks on ppj.localhost (Frappe v16.33.1)]
---

# 010 — Portal security fixes (Wave 0a): impact analysis and fix strategy

This is steps 1 and 2 of the change process. **No code has been changed.** It ends at a
human gate.

Two inputs the handoff contract expects do not exist yet:

- `01c-security-privacy-requirements.md` is being written in parallel. Section 13 maps
  S-items to its ids once it lands.
- There is no `02-functional-spec.md`. See open question OQ-13.

---

## The short answer

**All ten problems are real at `4e3ba28`.** Three are bigger than the plan said, and one
is smaller.

**Bigger than reported:**

1. **An employee can write their own review record through Frappe's standard API.**
   Rahul can change `review_status`, `overall_rating` or `manager_feedback` on his own
   Alvoraa Appraisal Extension with a plain REST call. Nobody reported this. It sits
   under S3, because the fix is the same.
2. **Four upload places make files public, not one** (S2): goal evidence (two screens),
   goal progress log and KPI progress log.
3. **The goal drawer has more unescaped text than the goal name** (S8). It also shows
   the employee's own free-text note, the validation notes, the unit, and a file link
   the browser sends in. A `javascript:` link could be stored there.
4. **On a new tenant, managers can read loss-of-pay amounts through the desk and REST
   API as well** (S5). PP Jewellers is only safe because of a tenant-level permission
   override.

**Smaller than reported:**

- **S9 does nothing today.** Frappe v16 has no listener for `eval_js`, so the pushed
  script never runs. It should still go.
- **The late-rule email does not carry the amount** (S5). It says "0.5 as loss of pay"
   in days, and names the leave type. That already fits your decision (days at most).

**One consequence you need to decide on before S2 is built:** today there is **no working
screen to approve goal evidence**. The portal approval list is broken (F1, Wave 0c). If
evidence stops approving itself, progress stops moving until someone approves it. Today
that can only happen in the desk. See OQ-6.

**Recommended size:** about 6.5 build days, in 10 small commits. Two of them (S2, S6)
wait for your answers.

---

## 1. Each problem, checked again

Line numbers are at `4e3ba28`. "Checked on ppj" means a read-only call on
`ppj.localhost`, rolled back.

### S1 — The self-review writes to records the employee does not own

**Still there.** `alvoraa_portal/performance_api.py:3572-3597`.

**Root cause.** `save_review_page` (:3521) stores whatever JSON the browser sends.
`submit_employee_review` (:3554) later reads KPI names and goal names out of that JSON and
writes them with `frappe.db.set_value`. It checks that the **appraisal** is the caller's.
It never checks that each **KPI or goal** belongs to that appraisal's employee. Errors are
swallowed (`except Exception: pass`). `db.set_value` skips validation and writes no
Version row, so nobody can see the change afterwards.

Two more things in the same function:

- It lets the self-review set `Individual Goal.actual_progress`. Progress already has its
  own approval paths (evidence, goal updates). Appendix D says to remove this.
- It creates future goals with status "Not Started", which is not valid (B7, Wave 0c).
  Not changed here.

**Callers (grep):**

```
submit_employee_review
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:15898:    pf("submit_employee_review", {appraisal: _pr.appraisal, overall_comment: comment})
```

**Fix (in `alvoraa_portal/performance_api.py`, because the bug is there).**

1. Collect the KPI names and goal names from the JSON.
2. Keep only the ones the appraisal's employee owns. Use one batched
   `frappe.get_all("KPI", filters={"name": ["in", names], "employee": ap.employee, "docstatus": ["!=", 2]}, pluck="name")`,
   and the same for `Individual Goal`. Ignore the rest, and log the appraisal name (never
   a person's name) with `frappe.log_error` so a tampering attempt leaves a trace.
3. Check each rating is between 0 and `MAX_RATING`, the same rule
   `save_kpi_self_review` (:439) uses.
4. Write each owned KPI with `frappe.get_doc` and `doc.save(ignore_permissions=True)`,
   like `save_kpi_self_review` does. This runs `validate_kpi` and writes a Version row.
   There are at most 20 KPIs per person per cycle (NFR budget), so the loop is bounded.
5. **Stop writing `actual_progress` from the self-review** (OQ-5).
6. Remove the silent `except: pass`. If one write fails, the whole request fails and
   Frappe rolls it back. The status only moves to "Manager Review" when every write
   worked.

**Size:** 0.5 day.

---

### S2 — Goal evidence approves itself, and evidence files are public

**Still there, and wider than reported.**

- `alvoraa_goals/api/goal_api.py:71` sets `"validation_status": "Approved"` on every new
  row and recalculates progress at once (:84).
- The portal toast says "Evidence submitted — progress updated"
  (`hrms-employee.html:9067`, `:10346`).
- The desk dialog says "Evidence approved! New progress…"
  (`individual_goal.js:110`).
- **Four** uploads send `is_private=0`:

| Line | Screen | Saved into |
|---|---|---|
| `hrms-employee.html:8975` | Goal drawer → Log update | `Goal Progress Update.evidence_file` via `goals_api.submit_goal_update` |
| `hrms-employee.html:9084` | Goal drawer → Submit evidence | `Goal Evidence.evidence_file` |
| `hrms-employee.html:10359` | Goal detail panel → Submit evidence | `Goal Evidence.evidence_file` |
| `hrms-employee.html:12062` | KPI → Log progress | `KPI Progress Log.evidence_file` via `performance_api.log_kpi_progress` |

- The server takes the file URL from the browser and never checks it. It could be
  someone else's file, or a `javascript:` link.

**Checked on ppj:** 996 evidence rows, all "Approved". 40 have `approved_by` equal to
`uploaded_by`. None has a file. There are no files on Goal Progress Update or KPI
Progress Log either. So on ppj there is nothing to move. **Other tenants (dev tenants,
`alvoraa.co`, `minda`) are unknown.**

**Also found:**

- **No working approval path in the portal.** The approvals renderer (:8466) depends on
  `hr_api.get_pending_approvals`, which fails with an ImportError (F1). The bell uses
  `goals_api.get_pending_approvals`, which does not list evidence at all. The desk
  Individual Goal form shows approved evidence only. HR can still change the child row's
  status by hand in the desk.
- **The HR "auto-approve evidence" switch does nothing.** It is saved by
  `set_org_setting` (`hrms-employee.html:16014`), but no server code reads
  `auto_approve_evidence`. On ppj it is unset.
- `controllers/evidence.py:11-26, 64-77` still has debug `frappe.log_error` and
  `msgprint` blocks that write the evidence value and file into the Error Log (B23). The
  `before_insert` hook probably does not run when evidence is saved through the parent
  goal (appendix D, inferred, not proven). Not changed here; see §11.

**Callers (grep):**

```
submit_goal_evidence
./alvoraa_goals/alvoraa_goals/alvoraa_goals/doctype/individual_goal/individual_goal.js:97:  method: 'alvoraa_goals.api.goal_api.submit_goal_evidence'
./alvoraa_portal/alvoraa_portal/hr_api.py:2024-2025:  from alvoraa_goals.api.goal_api import submit_goal_evidence / return submit_goal_evidence(
submit_goal_evidence_portal
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:9059:    api("submit_goal_evidence_portal", {
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:10340:      api("submit_goal_evidence_portal", {
submit_goal_update
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:8982:    await window.gpFetch("alvoraa_portal.goals_api.submit_goal_update", {...evidence_url: evidenceUrl})
log_kpi_progress
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:12073:      await pf("log_kpi_progress", {kpi: kpi, ..., evidence_url: evidenceUrl})
```

**How Frappe handles private files (checked in v16.33.1 source):**

- `frappe/handler.py:129 upload_file` checks **write** permission on `doctype`/`docname`
  if they are sent (:174-175, `check_write_permission` :221).
- `frappe/core/doctype/file/file.py:989 has_permission`:
  - a public file is readable by anyone;
  - the owner can always read their file;
  - if the file is attached to a document, read follows the attached document's read
    permission.
- `File.handle_is_private_changed` (:318) moves the file on disk and changes its URL.
  It only updates a field on the attached parent document, not a child row.

**Fix.**

1. **Browser:** all four uploads send `is_private=1`, without `doctype`/`docname`. An
   employee often cannot *write* a goal HR created (`alvoraa_goals.permissions.has_employee_permission`
   allows write only for the creator), so attaching at upload time would fail for them.
2. **Server:** a new helper `claim_evidence_file(file_url, doctype, name)` in
   `alvoraa_goals/controllers/evidence.py` (next to the evidence rules it serves). It is
   used by `goal_api.submit_goal_evidence`, `goals_api.submit_goal_update` and
   `performance_api.log_kpi_progress`. That is three real uses. It:
   - finds the File by `file_url`, and refuses unless `owner == frappe.session.user`,
     so a stranger's file or a `javascript:` string is refused;
   - sets `is_private = 1` if needed (Frappe moves it) and sets `attached_to_doctype` /
     `attached_to_name` to the goal or KPI, then saves;
   - returns the file's final URL, which is stored on the row.

   After that, the goal's manager and HR can open the file, because they can read the
   goal or KPI. Colleagues cannot. The desk dialog passes through the same helper, so the
   desk is covered too.
3. **Evidence starts as "Pending".** `goal_api.submit_goal_evidence` stops setting
   "Approved" and stops recalculating progress. It returns `status: "Pending"`. Progress
   moves only when `approve_evidence` runs (it already recalculates, :156).
4. **Wording:**
   - both portal toasts say "Evidence sent to your manager for approval";
   - the desk message says "Evidence sent for approval".
5. **The unused auto-approve switch:** decide with OQ-6. My recommendation: take the
   switch out of the portal in this commit, so HR is not shown a control that does
   nothing.
6. **Existing files:** a patch makes existing public evidence files private (§8, M1).

**Where:** `alvoraa_goals` (`api/goal_api.py`, `controllers/evidence.py`,
`individual_goal.js`, a patch), `alvoraa_portal` (`goals_api.py`, `performance_api.py`,
`hrms-employee.html`).

**Size:** 1.25 days. Add 1–1.5 days if you want a working evidence approval list in the
portal now (OQ-6).

---

### S3 — Employees can read manager-only fields on their own review (and write them)

**Still there, and worse.**

- `get_my_appraisals` (:3195) returns `overall_rating` for every own appraisal, at every
  stage.
- `get_appraisal_extension` (:2330-2343) hides `overall_rating` from the employee until
  "Completed". It still returns `avg_potential_rating` and `potential_category` at every
  stage (:2334-2335).
- `get_employee_final_review` (:4085-4087) returns `overall_rating`, `potential_rating`
  and `potential_category` from "Employee Final Review" onward. The final-review screen
  shows the potential rating (`hrms-employee.html:15730`). So the product has **two
  different release points** today.
- **The DocType itself** (`alvoraa_goals/.../alvoraa_appraisal_extension.json`) gives the
  **Employee** role `read`, `write` and `create` on every row. It has no row-level hook
  (`alvoraa_goals/hooks.py:28-36` covers only Individual Goal and KPI). No field has a
  permlevel.

**Checked on ppj, as Rahul (PPJ-0058):**

| Check | Result |
|---|---|
| `frappe.get_list` with `manager_internal_notes`, `potential_rating`, `overall_rating` | Returned for his 2 rows (completed row: overall 4.5, potential 3.0) |
| Other people's rows | Hidden, **only because** Rahul has a User Permission (Employee = PPJ-0058, apply to all doctypes). That is tenant setup, not code |
| `frappe.has_permission(..., "write", own extension)` | **True.** He can change his own `review_status` or `overall_rating` through `/api/resource` |
| Active users with no Employee User Permission | 11. For them, every colleague's extension is readable and writable |
| Custom DocPerm on this DocType | None, so the JSON permissions apply |

**Callers (grep):**

```
get_my_appraisals
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:13098:    pf("get_my_appraisals", {})
get_appraisal_extension
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:14146:    pf("get_appraisal_extension", {appraisal: appraisalId})
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:14199:      return pf("get_appraisal_extension", {appraisal: ap.name})
get_employee_final_review
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:15702:    pf("get_employee_final_review", {appraisal: _pr.appraisal})
```

Every portal read and write of this DocType goes through `frappe.get_doc`, `get_all` or
`save(ignore_permissions=True)`:

- inserts at :1422 and :2304;
- about 20 saves, all with `ignore_permissions=True`;
- raw SQL reads in `hr_api.py:829` and `:940`.

The portal page never calls `/api/resource` or `frappe.client` (grep found none).
`frappe.get_all` skips permission checks in v16 (`frappe/__init__.py:1383` docstring). So
**changing the DocType permissions does not change the portal.**

**Options:**

| Option | What it does | Consequence |
|---|---|---|
| **A (recommended)** | Remove the Employee role's DocPerm row from the extension JSON. Keep HR Manager, HR User and System Manager | Closes REST/list reads and writes for employees and managers in one line. No per-field rules to keep in step. Managers (plain Employee role) also lose desk and REST access; they use the portal, which is unchanged |
| B | Keep Employee read. Move manager-only fields to permlevel 1, readable by HR roles only. Take away Employee write | More moving parts. Managers still cannot see those fields in the desk. Rows are still scoped only by User Permissions |
| C | Add `has_permission` and `permission_query_conditions` hooks, like `Employee Checkin` in `alvoraa_portal/hooks.py:158-164` | Most code, for a desk use nobody has asked for |

**Fix (option A plus endpoint rules), in `alvoraa_goals` (owns the DocType) and
`alvoraa_portal/performance_api.py` (owns the endpoints):**

1. Extension JSON: remove the `Employee` permission row. This needs `bench migrate` on
   deploy.
2. One constant in `performance_api.py`: `RATING_RELEASED = ("Employee Final Review", "HR Review", "Completed")`.
   The stage is OQ-3.
3. `get_my_appraisals`: return `overall_rating` only when `review_status` is released,
   otherwise `None`.
4. `get_appraisal_extension`: for the employee's own record, use the same release rule
   for `overall_rating`. **Never** return `avg_potential_rating` or `potential_category`
   to the employee.
5. `get_employee_final_review`: keep `overall_rating`. Potential fields depend on OQ-4.
6. `manager_internal_notes` is already never returned to the employee by any endpoint
   (checked). After step 1 the list API cannot return it either.

**Size:** 0.75 day.

---

### S4 — Managers read a draft self-review; HR guard skipped; reviewers see every page

**Still there.**

| Endpoint | Problem |
|---|---|
| `get_manager_review` (:3649) | No stage check. It returns `page_data`, `overall_comment` and goals while the review is still "Employee Review". It also skips `_assert_hr_can_view`, so HR can read any draft |
| `get_appraisal_extension` (:2310) | A manager (any level above) gets `achievements_text`, `challenges_text`, `development_needs_text`, `support_needed`. `save_self_review_narrative` (:2351) writes these **during** "Employee Review". Draft text leaks |
| `save_manager_review` (:3754), `submit_manager_review` (:3976) | Stage is checked ("Manager Review"). `_assert_hr_can_view` is not. Any HR user can write a manager review for anyone |
| `get_reviewer_view` (:3882) | Calls `_get_or_create_extension` (:3889) **before** checking the caller is invited, so any logged-in employee can create an extension row for any appraisal name. It then returns the whole `page_data` (:3895, :3927), not just `allowed_pages`. No stage check |

**Callers (grep):**

```
get_manager_review
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:15200:    pf("get_manager_review", {appraisal: appraisalName})
save_manager_review
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:15435:    pf("save_manager_review", {
submit_manager_review
./alvoraa_portal/alvoraa_portal/performance_api.py:2396:  (docstring only)
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:15614:    pf("submit_manager_review", {
get_reviewer_view
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:13291:    pf("get_reviewer_view", {appraisal: appraisalId})
_assert_hr_can_view
./alvoraa_portal/alvoraa_portal/performance_api.py:600, :2316, :3262
./alvoraa_portal/alvoraa_portal/tests/test_appraisal_visibility.py:83, :154
```

**Fix (in `alvoraa_portal/performance_api.py`):**

1. One constant: `SELF_REVIEW_SENT = ("Manager Review", "Employee Final Review", "HR Review", "Completed")`.
   This is your decision Q-d.
2. `get_manager_review`:
   - call `_assert_hr_can_view(appraisal)` after the manager/HR check;
   - if the status is not in `SELF_REVIEW_SENT`, return the **same shape** with
     `page_data = {}`, `pages_completed = []`, `overall_comment = ""` and a new flag
     `self_review_sent: 0`.

   The same shape means the existing screen does not break. One small JS change in the
   `mr-review` block shows "Not sent yet — you can read it once {name} sends it."
3. `get_appraisal_extension`: when the caller is not the employee, blank the four
   narrative fields unless the status is in `SELF_REVIEW_SENT`.
4. `save_manager_review`, `submit_manager_review`: call `_assert_hr_can_view(appraisal)`.
5. **Extend the `_assert_hr_can_view` exemption.** Add "HR is this employee's effective
   manager" (`alvoraa_goals.permissions.get_effective_manager(owner) == me`).
   `get_effective_manager` falls back to the HR Manager when `reports_to` is empty (1
   active employee on ppj). Without this, step 4 would stop HR acting as the fallback
   manager.
6. `get_reviewer_view`:
   - check the invitation first, using `frappe.db.get_value` on the extension. Never
     create a row here;
   - refuse unless the status is in `SELF_REVIEW_SENT`;
   - return only `page_data[k]` for `k in allowed_pages`;
   - return goals only if `past-objectives` is allowed.

**A consequence to accept:** after `return_for_revision` the status goes back to
"Employee Review". The manager then cannot see the self-review again until the employee
re-sends it. That is what "not before it is sent" means.

**Size:** 1 day, including the small JS message.

---

### S5 — Managers' browsers receive a report's loss-of-pay amount

**Still there.**

- `hr_api._deduction_rows` (:2419-2443) selects `lwp_amount` and `explanation`.
- `get_team_late_list` (:2494) uses it for the manager's team.

**Checked on ppj as Sakshi (PPJ-0048):** the reply rows carry `lwp_amount`, `explanation`,
`violations`, `leave_days`. None of her team had a loss-of-pay amount in the last 4 weeks
on the bench date. Rahul's ₹548.39 (HR-ADD-2026-00116) is from the week of 3 Aug, outside
the 4-week window. The keys are what matters.

**The email:**

- `attendance_deduction.py:182-207` sends `self.explanation` to the employee and manager
  together.
- HR-ADD-2026-00116's text is "…Taken: 0.5 from Casual Leave, 0.5 as loss of pay."
- `build_explanation` (:37-60) never includes an amount.

**So the email already fits "days at most".** No change is proposed. It does name the
leave type to the manager; see OQ-11.

**Also found — desk and REST:**

- `attendance_deduction.json` gives the **Employee** role `read` and `print`. The row rule
  (`alvoraa_late_rules/permissions.py:23-44`) allows self **and the whole reporting line
  below**. `lwp_amount` is permlevel 0.
- So on a tenant that uses the JSON defaults, a manager can read the amount with
  `/api/resource/Attendance Deduction?fields=["lwp_amount"]` or in the print view.
- ppj is protected only by a Custom DocPerm that leaves **System Manager as the only
  role** able to read Attendance Deduction. Checked: Sakshi gets PermissionError. As a
  side effect, HR Manager cannot open these records in the desk on ppj either.

The Script Report `late_coming_deductions` shows the amount. It is limited to HR Manager
and HR User. That is fine.

**Callers (grep):**

```
get_team_late_list
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:6944:  api("get_team_late_list", {weeks: 4}, ...)
_deduction_rows
./alvoraa_portal/alvoraa_portal/hr_api.py:2454:    rows = _deduction_rows({"employee": emp.name, ...})        (employee's own - keeps amount)
./alvoraa_portal/alvoraa_portal/hr_api.py:2494:    recent = _deduction_rows({"employee": ["in", team], ...})  (manager - must not)
```

The manager screen (`hrms-employee.html:6955`) uses only `employee_name`, `week_start`,
`deduction_days` and `lwp_days`.

**Fix:**

1. `alvoraa_portal/hr_api.py`: `get_team_late_list` gets its own small, fixed field list:
   `name, employee, employee_name, week_start, week_end, deduction_days, lwp_days`.
   - No `lwp_amount`, no `explanation`, no per-row violations query.
   - `_deduction_rows` stays as it is for the employee's own view.
   - This also removes up to 50 queries (one per row) from the manager call.
2. `hrms/hrms/alvoraa_late_rules/doctype/attendance_deduction/attendance_deduction.json`:
   - set `lwp_amount` and `additional_salary` to **permlevel 1**;
   - add permlevel-1 read rows for HR Manager, HR User and System Manager.

   Frappe then removes those fields from list, REST, form and print for everyone else
   (verified: `database/query.py:1386`, `model/document.py:957`). The employee still sees
   their own amount in the portal, because `get_my_attendance_deductions` uses
   `frappe.get_all`. Needs `bench migrate`.

**Size:** 0.5 day.

---

### S6 — People search shows everyone; `my_view` / `chain_to_top` skip the reach limit

**Still there.**

- `hrms/hrms/alvoraa_org_structure/api.py:547 search_people` uses `frappe.get_all` over
  all active employees. As Rahul, "ra" returned 100 people, including other stores.
- `alvoraa_portal/performance_api.py:1460 search_employees` returns the first 80 active
  employees to **any** logged-in user. As Rahul: 80.
- `my_view(employee=...)` (:392) takes any employee. As Rahul, `my_view(employee="PPJ-0191")`
  returned Sandeep Sodhi's full view: 3 levels of breadcrumb and a team of 4.
- `chain_to_top(node=...)` (:889) takes any node. As Rahul, it returned the Noida store's
  chain.
- `subtree` for the same node **is** refused ("outside what you can see"), because it
  calls `_within_reach` (:704).

**Callers (grep):**

```
search_people
./alvoraa_portal/alvoraa_portal/tests/test_portal_call_paths.py:153, :169   (checks the path exists)
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:5241:  gpFetch("hrms.alvoraa_org_structure.api.search_people", { q: q })
search_employees
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:15321, :15378:  pf("search_employees", {query: ""})   (manager's "invite a reviewer" picker)
my_view
./alvoraa_portal/alvoraa_portal/tests/test_portal_call_paths.py:152, :169
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:5266:  gpFetch("...api.my_view", { employee: employee })   (ocJump after a search hit)
chain_to_top
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:5106:  gpFetch("...api.chain_to_top", id ? { node: id } : {})
./hrms/hrms/alvoraa_org_structure/tests/test_reach.py:101:  api.chain_to_top()   (no node - unaffected)
_within_reach
./hrms/hrms/alvoraa_org_structure/api.py:704; tests/test_reach.py:81, 86, 109, 114, 127
```

**Proposed behaviour for `search_people` (your decision Q-c, with my proposals marked).**
Always active employees only, and only `employee, name, title, department, image`.

| Who is searching | Finds | Why |
|---|---|---|
| Employee with nobody reporting to them | **Only themselves** *(proposal)* | "Own hierarchy downwards" is just them. Returning colleagues would break the decision |
| Manager | Themselves and **everyone below them**, at any depth, in `reports_to` | Your decision |
| HR Manager / HR User | Everyone in **their companies** *(proposal)*: companies from their User Permissions on Company; if none, the company on their own Employee record; if neither, nobody | Fail closed. Matches S10 |
| System Manager | Everyone, all companies *(proposal)* | Administers the tenant |
| CXO | Everyone, all companies *(proposal)* — **but no "Alvoraa CXO" role exists on ppj**. It is only named in `alvoraa_policy_library/access.py:50`. Until a CXO role exists, a CXO is whoever holds System Manager or HR roles | OQ-1 |

- "Below them" uses **Employee's nested set**. ERPNext's `Employee` is a `NestedSet` with
  `nsm_parent_field = "reports_to"` (`erpnext/setup/doctype/employee/employee.py:25, 114`).
  So it is one query: `lft > mine.lft and rgt < mine.rgt`.
- Checked on ppj: the nested set matches the `reports_to` walk exactly for Sakshi (13),
  Sandeep Gupta (18) and Kamal (402).
- **Why explicit filters with `get_all`, not `frappe.get_list`:** employees carry a User
  Permission "Employee = self, apply to all doctypes". `get_list` would therefore show a
  manager only themselves. The scope is computed on purpose and tested.

**`search_employees` (reviewer picker) is a different tool** (OQ-2). Managers invite
peers and dotted-line managers who are often *outside* their own line. My proposal:

- only callers who manage someone, or HR, may use it;
- results are limited to the caller's companies;
- same fields as today.

Applying the "downwards only" rule here would stop managers inviting anyone useful.

**`my_view(employee)` and `chain_to_top(node)`:** apply the **existing** reach rule,
exactly as `subtree` does:

- `chain_to_top`: refuse with the same PermissionError message when
  `node and not _within_reach(node, as_at)`.
- `my_view`: when an `employee` other than the caller is passed, refuse unless their seat
  is within reach. Seat means their primary position on a positions tenant
  (`_my_position_of`), or the employee id otherwise.

This does **not** change what the org chart shows. It only closes the two doors that went
around it. Managers keep full reach (`alvoraa_org_managers_see_all`, default 1). The org
chart's own reach policy is not part of Q-c, and I do not propose changing it.

**Where:**

- a new small module `hrms/hrms/alvoraa_hr_core/access.py` with
  `permitted_companies(user=None)`. `hrms` is the one app all three custom apps can
  import. `alvoraa_goals` requires `hrms`, and `hrms` must not hard-import
  `alvoraa_goals`;
- `hrms/hrms/alvoraa_org_structure/api.py` (`search_people`, `my_view`, `chain_to_top`);
- `alvoraa_portal/performance_api.py` (`search_employees`);
- one copy line in the portal: when a search finds nothing, say "Nobody in your team by
  that name" (`hrms-employee.html:5243`).

**Size:** 1 day.

---

### S7 — People can approve their own requests

**Still there, in six places.** None checks "the request is mine".

| Path | File:line | Who can self-approve today |
|---|---|---|
| Attendance correction `decide` | `alvoraa_portal/attendance_correction.py:723` | Anyone who can submit Attendance Request (HR). Kamal's own correction is waiting on ppj |
| KPI progress `approve_kpi_update` | `alvoraa_portal/performance_api.py:372` | HR (`_is_hr()`). Kamal's own KPI update is waiting on ppj |
| Goal progress `approve_goal_update` | `alvoraa_portal/goals_api.py:1046` | HR |
| Evidence `approve_evidence` / `reject_evidence` | `alvoraa_goals/controllers/evidence.py:145, 162` (portal proxies `hr_api.py:2043, 2050`) | HR (`can_validate_evidence` :99) |
| Leave `action_leave` | `alvoraa_portal/hr_api.py:572` | Anyone named as their **own** leave approver |
| Desk: submit Attendance Request / Leave Application | Frappe HR controllers (no self check — grep of `leave_application.py`, `attendance_request.py` found none) | HR in the desk |

Dead paths, **not** changed here: `hr_api.approve_kpi_progress` / `reject_kpi_progress`
(:2056, :2062) import functions that do not exist (F1, Wave 0c).

**Callers (grep):**

```
decide
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:6400:    await acApi("decide", {name, approve, note})
./alvoraa_portal/alvoraa_portal/tests/test_attendance_correction.py:471, 487, 501, 537, 552, 560, 562  (all as Administrator)
approve_kpi_update
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:12162
approve_goal_update
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:12167
./alvoraa_portal/alvoraa_portal/tests/test_evidence_and_updates.py:72 (inspect.getsource)
approve_evidence / reject_evidence
./alvoraa_portal/alvoraa_portal/hr_api.py:2044-2045, 2051-2052
./alvoraa_portal/alvoraa_portal/tests/test_evidence_and_updates.py:26, 36 (inspect.getsource)
approve_goal_evidence / reject_goal_evidence
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:8466
action_leave
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:8101 (passes leave_name - wrong argument name, separate bug), 8270, 8298, 8483
./alvoraa_portal/alvoraa_portal/tests/test_leave_permissions.py:120, 128, 156 (inspect.getsource)
```

**Fix:**

1. One helper in `hrms/hrms/alvoraa_hr_core/access.py`: `refuse_own_decision(employee)`.
   - It throws `frappe.PermissionError` with "You cannot decide your own request. Someone
     else must approve it." when `Employee.user_id == frappe.session.user`.
   - Administrator and users with no Employee record pass.
   - There are six real uses, so a shared helper is justified.
2. Call it at the top of the five function paths, before any write.
3. **Desk and API as well** (OQ-8, recommended): a `before_submit` doc_event in
   `alvoraa_portal/hooks.py` for **Attendance Request** (added to the existing entry at
   :69) and **Leave Application** (new entry, added at the end of the block). Each calls
   the same helper. This covers all four entry points: portal, desk, REST and import.
   - The scheduler and bench run as Administrator, so they are not affected.
   - Leave Application `before_submit` also runs when **HR submits leave on someone
     else's behalf**. That is not the employee's own user, so it passes.
4. KPI, goal and evidence approvals are child-row changes with no submit event, so the
   function checks are the whole control there.

**Consequence:** an owner or HR person who is the only approver for their own requests
can no longer approve them anywhere. Someone else must: another HR user, or a System
Manager. On ppj that affects Kamal's two waiting items.

**Size:** 0.75 day.

---

### S8 — Unescaped goal and employee names in the goal drawer

**Still there, and more than names.** Values put into `innerHTML` without `esc()` in
`renderGoalDrawer` (`hrms-employee.html:8730`):

| Value | Line | Who can type it |
|---|---|---|
| `g.goal_name` | 8742 | Employee (creates or edits goals) |
| `g.employee_name` | 8745 | HR |
| `ev.evidence_type`, `parts` | 8765 | Server list |
| `ev.raw_extracted_data` | 8762 | **Employee free text** ("Note") |
| `ev.validation_notes` | 8760 | Approver's text plus user emails |
| `ev.evidence_file` in `href` and `src` | 8754-8755 | **Sent by the browser**. It could be `javascript:…` |
| `g.unit` | 8777, 8820, 8826 | Goal creator |
| `casc.cascade_name` | 8825 | HR |

Also `hrms-employee.html:9127` puts `g.goal_name` into a team goal card unescaped.

The drawer is opened by a manager for a report's goal (`openTeamGoalDrawer`, :8664). So a
script planted by an employee runs **in the manager's session**.

Goal **comments** (:8864) are not escaped either. Frappe's `Comment.validate` already
sanitises them (`frappe/core/doctype/comment/comment.py:71`). Lower risk; escaped anyway
in the same commit, because it is the same function.

**Callers (grep):**

```
renderGoalDrawer
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:8674:    renderGoalDrawer(d.goal, d.cascade || {}, d.is_owner, d.can_edit);
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:8721:  renderGoalDrawer(goal, casc);
```

**Fix (in `hrms-employee.html`, inside `renderGoalDrawer` and the card at :9127 only):**

- wrap each value above in the page's existing `esc()` (:4905), which is what `gpEsc`
  calls;
- for file links, add a local `_safeFileUrl(u)` that allows only `/files/` and
  `/private/files/` and otherwise returns an empty string.

No shared helper changes and no reformatting. The S2 server check stops new bad URLs from
being stored. This stops old ones from running.

**Size:** 0.25 day.

---

### S9 — A notification helper pushes a script to the browser

**Still there, but inert.** `performance_api.py:3121-3125` publishes
`eval_js` / `console.log('notification sent')`. A search of Frappe v16.33.1 (`apps/frappe/frappe`,
all files) finds **no `eval_js` handler**, so nothing runs it. It is still a pattern that
would run code if a listener were ever added. The same `try` also hides every email
failure (`except Exception: pass`).

**Callers (grep):**

```
_send_notification
./alvoraa_portal/alvoraa_portal/performance_api.py:2438, 2446   (advance_review_status)
./alvoraa_portal/alvoraa_portal/performance_api.py:2481         (return_for_revision)
./alvoraa_portal/alvoraa_portal/performance_api.py:2516         (return_to_manager)
```

**Fix (in `performance_api.py`):**

- delete the `publish_realtime` call;
- replace `pass` with `frappe.log_error(title="Review notification failed")`. The
  message holds the traceback only: no recipient, no subject, no names.

The email itself is unchanged.

**Size:** 0.1 day.

---

### S10 — HR leave-on-behalf and balance lookups are not limited to HR's companies

**Still there.** Any HR Manager, HR User or System Manager can act for any employee:

- `get_leave_summary(employee_id)` (:1524-1527);
- `apply_leave(on_behalf_of)` (:1648-1654);
- `preview_leave_request(on_behalf_of)` (:1700-1702);
- the picker `get_all_active_employees` (:1508) lists every company.

ppj has one company, so nothing leaks there today. The risk is on multi-company tenants.

**Callers (grep):**

```
get_leave_summary
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:7056, 7122 (own), 7184 (employee_id: id - HR)
(hrms/hr/report/monthly_attendance_sheet.py:518 is a different function of the same name)
apply_leave
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:7309
./alvoraa_portal/alvoraa_portal/tests/test_leave.py:74, 87, 106, 120, 143, 154
./alvoraa_portal/alvoraa_portal/tests/test_leave_permissions.py:54, 69
preview_leave_request
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:7225
./alvoraa_portal/alvoraa_portal/tests/test_leave.py:51, 59, 67, 99, 115, 130
./alvoraa_portal/alvoraa_portal/tests/test_leave_permissions.py:83, 92
get_all_active_employees
./alvoraa_portal/alvoraa_portal/www/hrms-employee.html:7142
```

**Fix (in `alvoraa_portal/hr_api.py`, using `permitted_companies()` from S6):**

- one private helper, `_hr_target_employee(employee_id)`. It loads the Employee and
  throws PermissionError unless the employee's `company` is in `permitted_companies()`.
  The message stays the same whether the employee is in another company or does not
  exist;
- the three on-behalf endpoints call it;
- `get_all_active_employees` filters `company in permitted_companies()`.

`permitted_companies()` is built on Frappe's own
`frappe.core.doctype.user_permission.user_permission.get_permitted_documents("Company")`
(verified at :187). It returns:

- System Manager: all;
- HR with User Permissions on Company: those companies;
- HR without: the company on their own Employee record;
- otherwise: an empty list.

The last two rows are the fail-closed choice (OQ-9). Frappe's plain default would be
"all companies".

**Size:** 0.5 day.

---

## 2. Cross-module reach

| App | Touched? | What |
|---|---|---|
| `alvoraa_portal` | Yes | `performance_api.py` (S1, S3, S4, S6 picker, S7, S9), `hr_api.py` (S5, S7 leave, S10), `goals_api.py` (S2 file claim, S7), `attendance_correction.py` (S7), `hooks.py` (S7 doc_events), `www/hrms-employee.html` (S2 uploads and wording, S4 message, S6 wording, S8), tests |
| `alvoraa_goals` | Yes | `api/goal_api.py` (S2), `controllers/evidence.py` (S2 file claim, S7), `individual_goal.js` (S2 wording), Alvoraa Appraisal Extension JSON (S3), one patch (S2) |
| `hrms` (our fork, our own modules only) | Yes | New `alvoraa_hr_core/access.py` (S6, S7, S10); `alvoraa_org_structure/api.py` (S6); `alvoraa_late_rules/.../attendance_deduction.json` (S5). **No edit to stock Frappe HR code** |
| `erpnext` | No edit | Reads Employee's nested set (`lft`/`rgt`) and Company |
| `frappe` | No edit | Uses `get_permitted_documents`, File permissions, permlevel handling, doc_events |
| `alvox_compensation` | Not present | The folder does not exist in this repo (the handoff contract still names it). Nothing in S1–S10 touches compensation |

**The desk is affected. Each consequence:**

- **S3:** employees and plain-Employee managers can no longer open Alvoraa Appraisal
  Extension in the desk, list it, or call it through `/api/resource`. HR roles keep full
  access. The portal is unchanged.
- **S5:** anyone without an HR role or System Manager no longer sees `lwp_amount` or the
  Additional Salary link on Attendance Deduction, in the desk form, list, print or REST.
  On ppj, a Custom DocPerm replaces the JSON rules and has no permlevel-1 row. So on ppj
  **even HR Manager** will not see the amount in the desk until the tenant's DocPerms get
  a permlevel-1 row. HR Manager cannot open these records in the ppj desk today anyway.
  See OQ-10.
- **S7:** nobody can submit their own Attendance Request or Leave Application in the desk
  (if OQ-8 is yes).
- **S2:** the desk "add evidence" dialog now says "sent for approval", and the file
  becomes private.

---

## 3. Persona impact

| Persona | Can still do | Loses (on purpose) |
|---|---|---|
| **CXO** (no separate role today; System Manager or HR roles in practice) | Everything they do today, across all companies. Search finds everyone (if System Manager) | Approving their own requests. If they hold only an HR role: acting for employees outside their permitted companies |
| **HR Manager / HR User** | Leave on behalf and balance lookups for employees in their companies. Read any review once it reaches HR Review or Completed. Act as manager for their own reports and for employees with no manager (fallback). Approve other people's evidence, KPI and goal updates, and attendance corrections. Full desk access to appraisal extensions and late-rule amounts (JSON default) | Approving their own requests. Reading or writing a manager review for someone else's report before HR Review. Searching or acting for employees outside their companies |
| **Manager** | Everything on their team's reviews **once the self-review is sent**. The late list on screen is unchanged. Search their whole line. Org chart as today. Invite reviewers from their company. Open evidence files of their reports | Reading a draft self-review. The loss-of-pay amount (payload and desk). Desk/REST access to appraisal extensions. Search results outside their line |
| **Employee** | Write and send the self-review. Rate their own KPIs. See their own loss-of-pay amount in the portal. Submit evidence (now waits for approval). See their overall rating once released | Changing colleagues' KPIs or goals through the review. Changing their own goal progress through the review (if OQ-5 yes). Evidence counting before approval. Public file links. Potential rating before or ever (OQ-4). Writing their own review record through REST. Search beyond themselves. Other people's org view through `my_view` / `chain_to_top` |
| **Invited reviewer** | Read the pages they were invited to, after the review is sent, and comment | Pages they were not invited to. Creating review records by calling the endpoint |

---

## 4. HRMS domain impact

| Domain | Impact |
|---|---|
| **Appraisals** | Stage rules become strict: sent / released. Self-review no longer changes goal progress. KPI self-ratings get Version history. The HR fallback manager still works. One visible change for employees: when the overall rating appears (OQ-3), and whether potential appears (OQ-4) |
| **Goals** | Evidence starts Pending, so **progress moves only on approval**. Until the Inbox or a fixed approvals list exists, approval happens in the desk (OQ-6). Evidence files become private and attached to the goal |
| **KPIs** | Progress-log files become private and attached to the KPI. Self-approval of KPI updates is refused |
| **Attendance deductions** | Manager payload drops amount and explanation. DocType amount fields move to permlevel 1. Weekly job, leave ledger, Additional Salary and payroll are untouched |
| **Attendance** | Nobody decides their own correction, in the portal or the desk |
| **Leave** | Nobody approves their own leave. HR on-behalf is limited to their companies. Balances and preview maths are unchanged |
| **Payroll** | No change. Additional Salary creation is untouched. Only who can *read* the link changes |
| **Org structure** | Search scope narrows. Two endpoints obey the existing reach rule. The chart itself is unchanged |

---

## 5. Non-functional verdicts

Checked against the proposal. They are re-checked against the real code in
`03-implementation-notes.md`.

| Dimension | Verdict | Reason |
|---|---|---|
| Performance | **improves** (slightly) | The manager late list loses a query per deduction row (up to 50). Search becomes one bounded nested-set query instead of an unbounded name scan. Small costs: `submit_employee_review` does one `get_doc` + `save` per owned KPI (≤ 20), and each decision adds one lookup |
| Security | **improves** | Closes cross-record writes (S1), self-approval (S2, S7), REST read and write of review records (S3), draft reads (S4), a payload and REST amount leak (S5), a directory leak (S6), stored XSS (S8) and a script push (S9). No new `ignore_permissions` except one scoped `save` on the File record the caller owns |
| Reliability | **improves**, with one flow risk | Silent `except: pass` removed from S1 and S9. Partial self-review writes can no longer happen. Risk: pending evidence has no portal approval screen yet (OQ-6). A file move in the patch can fail per file; it is handled per row |
| Scalability | **improves** | Search and pickers are bounded by line or company. HR on-behalf is bounded by company. Every added query has fixed cost whatever the headcount |
| Maintainability | **improves** | Two shared rules in one place (`refuse_own_decision`, `permitted_companies`) and two stage constants replace scattered checks. A small risk: portal code must now remember the stage constants when new review endpoints are added. Pin tests cover it |
| Data integrity | **improves** | KPI writes go through the controller with Version rows. Evidence only moves progress on approval. Private files are attached to their record. Risk: the private-file patch changes file URLs, and every child row must be updated in the same run (§8) |
| Compliance / privacy | **improves** | Pay amounts stay with the employee and HR. Drafts stay with the author. The directory is role-scoped. Evidence files are need-to-know. No new personal data in logs: only document names are logged |

---

## 6. Parallel-work check

**Start-of-work steps done on 2026-09-14:**

- `git fetch origin`, then `git log HEAD..origin/dev`: **nothing incoming.** The worktree
  equals `origin/dev` at `4e3ba28`. Checked twice.
- `git worktree list`: the main checkout (`dev`) and this slice's worktree only.
- Work board: one row, this slice.
- Main checkout `git status`: another session's uncommitted work, **not mine, not
  touched**:
  - `CLAUDE.md`, `.claude/agents/*`, `.claude/context/frappe-conventions.md`,
    `backlog/KPI_AUTOMATION_BACKLOG.md`;
  - deleted `OBJECTIVES_KPI_REQUIREMENTS.md`;
  - **`hrms/hrms/alvoraa_org_structure/doctype/alvoraa_position/alvoraa_position.py`**;
  - several untracked files.
- The bench runs the main checkout. That checkout has uncommitted changes in the org
  structure module, next to `api.py`. Before I test S6 on the bench, I must check that
  file is committed or unchanged, or ask.

**Files I will change:**

| File | Hot? | Commits in last 7 / 30 days | Overlap and plan |
|---|---|---|---|
| `alvoraa_portal/www/hrms-employee.html` | **Hot** | 19 / 37 | Wave 1 (frame) plans to **split this file into includes**. My edits are small and local: 4 upload lines, 3 toasts, `renderGoalDrawer`, one card, one `mr-review` message, one search empty state. **Sequence:** land 010 before Wave 1 step 2 (the split), or rebase onto it and move my lines into the new include. **Ask:** has Wave 1 started in another session? |
| `alvoraa_portal/hr_api.py` | **Hot** (signature rule) | 5 / 18 | No signature changes. One new private helper. Edits in `_deduction_rows` area, `apply_leave`, `get_leave_summary`, `preview_leave_request`, `get_all_active_employees`, `action_leave` |
| `alvoraa_portal/hooks.py` | **Hot** | — | Two `before_submit` entries: one added inside the existing Attendance Request dict, one Leave Application entry at the end of `doc_events`, each with a comment |
| `alvoraa_portal/performance_api.py` | No | 2 / 5 | Many functions, no signature changes |
| `alvoraa_portal/goals_api.py` | No | 0 / 3 | `submit_goal_update`, `approve_goal_update` |
| `alvoraa_portal/attendance_correction.py` | No | 2 / 2 | `decide` only |
| `alvoraa_goals/api/goal_api.py`, `controllers/evidence.py`, `individual_goal.js` | No | 0 / 2–3 | — |
| `alvoraa_goals/.../alvoraa_appraisal_extension.json` | **Hot (DocType JSON)** | 0 / 1 | Claim on the board once approved |
| `alvoraa_goals/patches.txt` + new patch file | **Hot** | 0 / 1 | Append one line at the end |
| `hrms/hrms/alvoraa_late_rules/.../attendance_deduction.json` | **Hot (DocType JSON)** | 0 / 1 | Claim on the board |
| `hrms/hrms/alvoraa_org_structure/api.py` | No, but busy | 6 / 6 | Three functions. **Another session has uncommitted edits in the same module** (`alvoraa_position.py`). **Ask** whether that session also plans `api.py` changes |
| `hrms/hrms/alvoraa_hr_core/access.py` | New | — | — |
| New/extended tests in `alvoraa_portal/tests/` | Shared fixtures rule | — | Own records with unique names. No shared fixture changes |

**Other developers:** I cannot see other machines. `git log origin/dev --since="7 days ago"`
for these files shows only this repository's sessions. **Question for you: is anyone
else working in these files?** (OQ-12)

**Pin tests:** each S-item ships with a named test (§7), so a bad merge fails CI.
**Important:** CI runs only `alvoraa_goals` and `alvoraa_portal` tests
(`.github/workflows/ci.yml:281-282`), **not `hrms`**. So pin tests for the `hrms` fork
changes (S5 JSON, S6 org API, the access helper) go into `alvoraa_portal/tests/`, or they
would never run in CI.

---

## 7. Test plan

Rules:

- Tests run on `test_site` only, one run at a time, after checking
  `pgrep -af run-tests`.
- Commands: `bench --site test_site run-tests --app alvoraa_portal` and
  `--app alvoraa_goals`.
- Every test sets its user with `frappe.set_user` and rolls back in `tearDown`.

| S | Test module | Persona → action → expected |
|---|---|---|
| S1 | **new** `test_self_review_ownership.py` | Employee A saves page JSON naming colleague B's KPI and goal, then submits → B's `self_rating`, `self_comment` and goal `actual_progress` unchanged. A's own KPI rating saved **with a Version row**. Rating 9 → refused, status stays "Employee Review". Goal progress in JSON → ignored (if OQ-5 yes) |
| S2 | extend `test_evidence_and_updates.py` | Employee submits evidence → row "Pending", goal progress unchanged, response `status == "Pending"`. Evidence file owned by another user → PermissionError. `javascript:alert(1)` → refused. Accepted file is `is_private = 1` and attached to the goal. Manager `File.has_permission(read)` → True; unrelated colleague → False. Manager approves → progress moves. Same for `log_kpi_progress` and `submit_goal_update`. **Static pin:** `hrms-employee.html` contains no `append("is_private", "0")` |
| S3 | extend `test_appraisal_visibility.py` | Employee: `frappe.has_permission("Alvoraa Appraisal Extension", "read"/"write", own)` → False; `frappe.get_list` → PermissionError. HR Manager → True. `get_my_appraisals` before release → `overall_rating is None`; after release → value. `get_appraisal_extension` as the employee → no `avg_potential_rating` / `potential_category` keys. Manager `get_manager_review` still returns ratings |
| S4 | extend `test_appraisal_visibility.py` | Manager `get_manager_review` at "Employee Review" → `self_review_sent == 0`, empty `page_data`. After `submit_employee_review` → content present. Manager `get_appraisal_extension` at "Employee Review" → narrative fields empty. HR (not in line) `save_manager_review` / `submit_manager_review` / `get_manager_review` at "Manager Review" → PermissionError. HR as fallback manager (employee with no `reports_to`) → allowed. Invited reviewer → only allowed pages' keys. Not invited → PermissionError **and the extension count does not change**. Reviewer at "Employee Review" → refused. **Existing tests to keep green:** `test_a_manager_who_is_also_hr_can_still_do_a_manager_review`, `test_hr_still_cannot_read_a_stranger_mid_review` |
| S5 | **new** `test_late_list_privacy.py` (in `alvoraa_portal`, because CI does not run `hrms`) | Manager `get_team_late_list` → no row has `lwp_amount` or `explanation`. Employee `get_my_attendance_deductions` → own `lwp_amount` present. `frappe.get_meta("Attendance Deduction").get_field("lwp_amount").permlevel >= 1`. As a manager with the JSON default perms, `frappe.get_list("Attendance Deduction", fields=["lwp_amount"])` returns no `lwp_amount` values. Query-count assertion on the manager call (fixed, whatever the number of rows) |
| S6 | **new** `test_people_search_scope.py` (in `alvoraa_portal`) | Employee with no reports → `search_people` returns only self. Manager → self and whole line, nobody else. HR with Company User Permission for company A → nobody from company B. HR with none → own company only. System Manager → both. `my_view(employee=outside reach)` → PermissionError. `chain_to_top(node=outside reach)` → PermissionError. `search_employees` as a plain employee → PermissionError; as a manager → own company only. Needs a **second Company** created in `setUpClass`, with a unique name |
| S7 | **new** `test_separation_of_duties.py` | HR raises and then `decide`s own attendance correction → PermissionError. HR `approve_kpi_update` on own KPI log → refused. `approve_goal_update` own → refused. `approve_evidence` own → refused. `action_leave` where the approver is self → refused. Desk: HR `frappe.get_doc("Attendance Request", own).submit()` → refused; same for own Leave Application (if OQ-8 yes). HR submits **someone else's** leave → allowed. **Existing:** `test_attendance_correction.py` decides as Administrator, so no change |
| S8 | **new** static test `test_portal_escaping.py` | Extract `renderGoalDrawer` from the page and assert no `+ g.goal_name +`, `+ g.employee_name +`, `+ ev.raw_extracted_data +`, `+ ev.validation_notes +` without `esc(`. `_safeFileUrl` exists and is used for `href`/`src`. Plus a hand trace of the drawer with a goal named `<img src=x onerror=alert(1)>` on the local bench |
| S9 | extend `test_portal_call_paths.py` (static) | No `"eval_js"` string anywhere under `alvoraa_portal/alvoraa_portal/*.py` |
| S10 | extend `test_leave_permissions.py` | HR in company A: `apply_leave(on_behalf_of=B-employee)`, `get_leave_summary(employee_id=B-employee)`, `preview_leave_request(on_behalf_of=B-employee)` → PermissionError. `get_all_active_employees` → only company A. **Existing** `test_hr_can_apply_on_behalf_of_another_employee` and `test_hr_preview_reads_the_named_employee` should still pass: the HR user has an Employee in the same test company as `other_emp`. I will confirm in the fixture before relying on it |

**Existing tests that may need changing:**

- Source-inspection tests in `test_evidence_and_updates.py` (:26, :36, :72) and
  `test_leave_permissions.py` (:120, :128, :156) grep function bodies. They should keep
  passing, because I add lines and remove none they look for. I will run them.
- `alvoraa_goals/tests/test_evidence.py::test_evidence_pending_on_manual_entry` is
  skipped today. No change.

**Whole suites** (`alvoraa_portal` and `alvoraa_goals`) run once before hand-off, not
only the modules above.

---

## 8. Data and migration

| # | What | Proposal | Needs |
|---|---|---|---|
| M1 | Existing **public** evidence files (Goal Evidence, Goal Progress Update, KPI Progress Log) | Patch `alvoraa_goals.patches.v1_0.make_evidence_files_private`. For each distinct `evidence_file` starting with `/files/`: find the File, set `is_private = 1`, set `attached_to_doctype`/`attached_to_name` to the parent goal or KPI, save (Frappe moves the file), then update **every child row** that holds the old URL. One try/except per file; on failure, log only the File name and carry on. **Safe to run twice** (skips private files). **Rollback:** none automatic. Flipping `is_private` back moves the files back. Say so honestly | `bench migrate` on deploy. **Dry run first on each tenant:** a count query (below) |
| M2 | Existing **self-approved** evidence | **Proposal, not a decision (OQ-7).** Do not change old rows automatically. Changing them would drop progress already shown to employees, and possibly used in closed appraisals. Instead, give HR a read-only list: rows with `validation_status = "Approved"` and (`approved_by` empty **or** `approved_by = uploaded_by`). On ppj: 40 rows, all seed data. Alternatives for you: (a) leave and list — recommended; (b) reset open-cycle rows to Pending; (c) add a note to `validation_notes` on those rows | Your choice |
| M3 | Alvoraa Appraisal Extension permissions | JSON change only, applied by `bench migrate`. **A tenant with its own Custom DocPerm on this DocType keeps it**, because Custom DocPerm replaces JSON. ppj has none. Proposal: the same deploy runs a read-only check that lists tenants with a Custom DocPerm granting Employee on this DocType. It removes nothing on its own | `bench migrate` |
| M4 | Attendance Deduction `lwp_amount` / `additional_salary` permlevel | JSON change by `bench migrate`. On tenants with Custom DocPerms (ppj), add a permlevel-1 read row for HR Manager and HR User **only if you agree** (OQ-10), because it changes that tenant's config | `bench migrate`; tenant config is a dev-stage action on your word |
| M5 | Stale `auto_approve_evidence` default | Leave the stored value. Remove the switch from the page (OQ-6) | — |

Dry-run count for M1 (read-only, per tenant):

```sql
SELECT 'Goal Evidence', COUNT(*) FROM `tabGoal Evidence` WHERE evidence_file LIKE '/files/%'
UNION ALL SELECT 'Goal Progress Update', COUNT(*) FROM `tabGoal Progress Update` WHERE evidence_file LIKE '/files/%'
UNION ALL SELECT 'KPI Progress Log', COUNT(*) FROM `tabKPI Progress Log` WHERE evidence_file LIKE '/files/%';
```

ppj: 0 / 0 / 0.

---

## 9. Rollout notes

**Order of commits:** see §10.

**Commands on deploy, each needing your explicit approval, and none run by me:**

- `bench migrate` on each tenant: DocType JSON (S3, S5), the M1 patch, and `hooks.py`
  doc_events (these load on restart; migrate is not strictly needed for hooks, but the
  deploy restarts anyway).
- No `bench build`: `hrms-employee.html` is a www template, not a built asset.
- `bench clear-cache` is **not** needed: migrate clears DocType meta. The portal context
  cache is not affected.

**Changes to tell users about, in plain words:**

- Employees:
  - "Evidence and progress files are now visible only to you, your manager and HR."
  - "Evidence counts towards your goal once your manager approves it."
  - "Your overall rating appears when your manager's review is released." (per OQ-3)
- Managers:
  - "You will see a self-review once your team member sends it."
  - "People search now finds people in your own team."
- HR:
  - "You cannot approve your own requests; another HR user or the owner must."
  - "Leave on behalf is limited to your companies."
  - "The 'auto-approve evidence' switch is removed."
- Dev tenants first, then main, each on your word (`CLAUDE.md` §1).

**Rollback:** `git revert` of the relevant commit, then deploy. The M1 file move is the
only part that is not undone by a revert.

---

## 10. Proposed commits

Each commit carries its own pin test. Estimates are build days, including tests.

| # | Commit | Items | Depends on | Estimate |
|---|---|---|---|---|
| 1 | Stop pushing a script to the browser from review emails, and log send failures | S9 | — | 0.1 |
| 2 | The self-review only rates the employee's own KPIs, through the KPI's own save | S1 | OQ-5 | 0.5 |
| 3 | Access helpers: who may decide what, and which companies HR covers | new `alvoraa_hr_core/access.py` | — | 0.25 |
| 4 | Nobody approves their own request, in the portal or the desk | S7 | 3, OQ-8 | 0.6 |
| 5 | Managers get loss-of-pay days, never the amount (payload and DocType) | S5 | OQ-10 | 0.5 |
| 6 | HR leave on behalf is limited to HR's own companies | S10 | 3, OQ-9 | 0.4 |
| 7 | Review records are read and written through the portal's own rules only; ratings shown on release | S3 | OQ-3, OQ-4 | 0.75 |
| 8 | A manager sees a self-review only once it is sent; HR guard on manager-review writes; reviewers see their pages only | S4 | 7 | 1.0 |
| 9 | Escape goal, evidence and names in the goal drawer | S8 | — | 0.25 |
| 10 | People search finds your own line; org views obey the reach rule | S6 | 3, OQ-1, OQ-2 | 1.0 |
| 11 | Evidence waits for approval, and evidence files are private | S2 + M1 | OQ-6, OQ-7 | 1.25 (+1–1.5 if the approval list is included) |

**Total: about 6.6 days** (7.6–8.1 if OQ-6 brings the approval list forward). This is
within the plan's 5–7 day range before that option.

---

## 11. Risks, trade-offs and consequences nobody asked about yet

1. **Evidence approvals have nowhere to happen** (S2). Without a decision, employees will
   see progress freeze. Either accept desk approval for a few weeks, or bring the evidence
   part of F1 into this slice.
2. **Wave 1 will split `hrms-employee.html` into includes.** If it lands first, my small
   edits must move into the new files. If mine land first, the split must carry them. The
   pin tests (S2 static, S8 static) must follow the includes, as Wave 1 already plans for
   other checks.
3. **CI does not run `hrms` tests.** Any protection that lives only in
   `hrms/.../tests` can be lost in a merge without CI noticing. Adding `hrms` modules to
   CI is a `.github/` change, outside a feature slice. I recommend a separate small task.
4. **Tenant Custom DocPerms override our JSON** (S3, S5). A tenant that customised these
   DocTypes will not get the fix from `bench migrate` alone. M3 and M4 give a way to find
   them.
5. **Removing Employee DocPerm from the extension** also removes desk access for
   managers. I found no use of it. If a tenant uses the desk list for team reviews, they
   will notice.
6. **Separation of duties in the desk** (S7) also blocks an owner who is the only
   approver. Small companies may need a second approver named before deploy.
7. **HR company scope fails closed.** On a multi-company tenant where HR staff have no
   Company User Permission, they will be limited to their own company. That is safer, but
   may surprise a group HR team. They will need User Permissions set first.
8. **The self-review stops changing goal progress** (if OQ-5 yes). Employees who used the
   review to "top up" progress must use evidence or goal updates instead. Both wait for
   approval.
9. **`goals_api.submit_goal_update` still moves progress before approval** (B24). This
   slice makes its files private but does not change that rule. It is the same kind of
   problem as S2 and belongs with the "one progress model" decision (G-06, Q22).
10. **Other gaps seen while reading, not fixed here:**
    - `get_team_reviews` shows HR every employee in every company (:678);
    - `hrms-employee.html:8101` calls `action_leave` with the wrong argument name;
    - `controllers/evidence.py` writes debug text with the evidence value into the Error
      Log (B23);
    - `get_my_appraisals` makes 3 queries per invited review;
    - manager-facing employee names in `title` attributes (:8136) are unescaped (HR
      controls those names);
    - ppj's Custom DocPerm hides Attendance Deduction from HR Manager in the desk.

    Each is listed so it is a decision, not a surprise.
11. **Private files are slower to serve.** Frappe checks permission on each download.
    Evidence images in the drawer are few per goal, so the cost is small.
12. **A public URL that was already shared stays copied** wherever it went (emails,
    screenshots). M1 closes the link, not the copies.

---

## 12. Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| OQ-1 | People search: (a) someone with no reports finds **only themselves** — agree? (b) HR finds everyone **in their companies** (User Permission on Company, else own company) — agree? (c) System Manager finds everyone — agree? (d) There is no CXO role on ppj. Should we treat System Manager as CXO for now, or create an "Alvoraa CXO" role? | Product owner (Surbhi) | Commit 10 |
| OQ-2 | Reviewer picker (`search_employees`): managers and HR, **own company**, not limited to their line — agree? (Limiting it to their line would stop inviting peers.) | Product owner | Commit 10 |
| OQ-3 | When does the employee see their **overall rating**: from "Employee Final Review" (recommended; the final-review screen already shows it), or only at "Completed"? | Product owner | Commit 7 |
| OQ-4 | Should the employee **ever** see their **potential rating** and category? Today the final-review screen shows it. Recommendation: never (it is a manager/HR talent judgment). | Product owner, with the security engineer | Commit 7 |
| OQ-5 | The self-review should **stop changing goal progress** — agree? | Product owner | Commit 2 |
| OQ-6 | Evidence starts Pending, but no portal screen can approve it today. (a) Accept desk approval until the Inbox (Wave 2); (b) add the evidence approval list to this slice (+1–1.5 days); (c) something else. Also: remove the unused "auto-approve evidence" switch, or make it work? | Product owner | Commit 11 |
| OQ-7 | Existing auto-approved evidence: leave it and give HR a list (recommended), reset open-cycle rows to Pending, or add a note? | Product owner | Commit 11 |
| OQ-8 | Block self-approval in the **desk and API** too (doc hook on Attendance Request and Leave Application)? Recommended: yes. | Product owner | Commit 4 |
| OQ-9 | HR with no Company User Permission is limited to **their own company** (fail closed), rather than Frappe's default of all companies — agree? | Product owner | Commits 6, 10 |
| OQ-10 | On ppj (Custom DocPerm on Attendance Deduction), add a permlevel-1 read row for HR Manager and HR User, so HR can see amounts in the desk? This changes that tenant's config. | Product owner | Commit 5 (tenant step only) |
| OQ-11 | The late-rule email names the leave type ("0.5 from Casual Leave") to the manager as well. Keep it? (No amount is sent.) | Product owner, with the security engineer | Nothing in this slice unless you want a change |
| OQ-12 | Is anyone else — another session or developer — working in `hrms-employee.html`, `hr_api.py`, `hooks.py` or `hrms/.../alvoraa_org_structure/`? Has Wave 1's include split started? | Surbhi | Build start |
| OQ-13 | This slice has no `02-functional-spec.md`. Do `01c` plus this document act as the spec for a back-end fix slice, or should the analyst write `02` first? | Surbhi | Build start |

## Assumptions

- [ASSUMPTION] `4e3ba28` on the bench equals the worktree. The bench runs the main
  checkout, which has no uncommitted changes in the files read, except
  `alvoraa_position.py`, which S1–S10 do not read.
- [ASSUMPTION] ppj results (one company, User Permissions on most employees, a Custom
  DocPerm on Attendance Deduction) are not typical of every tenant. Multi-company
  behaviour will be proven on `test_site` with a second company.
- [ASSUMPTION] No tenant uses the desk list of Alvoraa Appraisal Extension for managers or
  employees. I found no code or documentation that does.
- [ASSUMPTION] Evidence's `before_insert` hook does not run when evidence is saved through
  the parent goal (from appendix D, not proven). The S2 fix does not depend on it.
- [ASSUMPTION] Sizes are one engineer on the local bench, with answers to OQ-1 to OQ-13
  before the dependent commit starts.
- [ASSUMPTION] "CXO" today means whoever holds System Manager (or HR roles); no CXO role
  exists on ppj.

## Mapping to security and privacy requirements

To be filled when `01c-security-privacy-requirements.md` lands. Every row must map to an
SEC/PRIV id, or be marked "not adopted" with your decision.

| S | Commit | Mechanism | Pin test | SEC/PRIV (to be filled from 01c) |
|---|---|---|---|---|
| S1 | 2 | Ownership filter + `doc.save` with Version | `test_self_review_ownership` | |
| S2 | 11 | Pending status; `claim_evidence_file` (owner check, private, attached); patch M1 | `test_evidence_and_updates` (+ static) | |
| S3 | 7 | Employee DocPerm removed; release rule in endpoints | `test_appraisal_visibility` | |
| S3b (REST write) | 7 | Same DocPerm change | `test_appraisal_visibility` | |
| S4 | 8 | `SELF_REVIEW_SENT` stage rule; `_assert_hr_can_view` on writes; reviewer page filter; no create-before-check | `test_appraisal_visibility` | |
| S5 | 5 | Manager field list; permlevel 1 on `lwp_amount`, `additional_salary` | `test_late_list_privacy` | |
| S6 | 10 | Nested-set line scope; `permitted_companies`; `_within_reach` on `my_view` / `chain_to_top` | `test_people_search_scope` | |
| S7 | 4 | `refuse_own_decision` in 5 functions + `before_submit` hooks | `test_separation_of_duties` | |
| S8 | 9 | `esc()` + `_safeFileUrl` in the drawer | `test_portal_escaping` + hand trace | |
| S9 | 1 | `eval_js` removed; failures logged without personal data | `test_portal_call_paths` (static) | |
| S10 | 6 | `_hr_target_employee` with `permitted_companies` | `test_leave_permissions` | |

## Handoff note

To the DevOps engineer (07 §4) and the security engineer (01c):

- **Three things deserve your eye.**
  1. Two DocType JSON permission changes need `bench migrate`, and tenant Custom DocPerms
     can silently cancel them (M3, M4).
  2. The M1 patch moves files on disk and has no automatic rollback. Please dry-run the
     count on each dev tenant before deploy.
  3. CI does not run `hrms` tests, so I put every pin test in `alvoraa_portal`.
- **Where I may differ from the plan:**
  - S5's email needs no change: it has days, not the amount.
  - S9 is inert on v16.
  - S3 is worse than listed: employees can **write** their own review record through REST.
- If `01c` asks for something this strategy does not cover, say so and I will revise
  before any code.

**Waiting for approval of this strategy.**
