---
slice: 010-portal-security-fixes
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-09-14
status: draft
inputs: [docs/slices/009-ess-portal-redesign/00-assessment-and-plan.md (§1a S1-S10, §6 decisions of 2026-09-14), docs/slices/009-ess-portal-redesign/appendix-a-frame.md, appendix-b-home-inbox.md, appendix-c-time-pay.md, appendix-d-growth-team-people.md, .claude/context/security-compliance-baseline.md, .claude/context/compliance-feature-map.md, .claude/context/nfr-budget.md, .claude/context/parallel-work.md, code at slice/010-portal-security-fixes = origin/dev 4e3ba28, read-only checks on hrlocal-bench site ppj.localhost]
---

# Portal security and privacy fixes (Wave 0a): security and privacy requirements

## The short answer

**All ten issues are real at `4e3ba28`. Three are worse than the plan says.**

1. **S3 is not only a read leak. An employee can change their own review.** The
   `Alvoraa Appraisal Extension` doctype gives the Employee role read, write *and* create,
   with no row rule in code. On the local copy, Rahul holds write permission on his own
   *Completed* review (overall rating 4.5). His manager Sakshi holds write permission on
   her reports' reviews, drafts included. I checked this with `frappe.has_permission`
   only. Nothing was written.
2. **S2 has four public upload paths, not one.** And the server accepts any text as the
   evidence file link.
3. **S7 is wider than two functions.** Six approve paths and four rating paths let
   somebody decide or rate their own record.

**One part of an issue is smaller than written.** S5's deduction email to the manager
carries loss-of-pay **days**, not the amount. That is inside the user's decision. The
**amount** leak is real in the API reply, and on any tenant without PP Jewellers' custom
permission, also through the desk and the REST API (a web interface for reading records
directly).

**Most of these holes are already on `main`.** That branch is meant to be what production
runs. I could not check what production actually runs, and I did not try. So there is
a question for counsel about whether anything has to be reported (section 8).

**This artifact sets 17 `SEC` and 8 `PRIV` requirements.** Each one has a test that
refuses the bad case.

Inputs note: this slice has no `01-product-brief.md` or `01b-ux-design.md`. It is a
back-end fix slice with no new screens, and the 009 assessment plan stands in for the
brief. The baseline entries I rely on were verified on 24 Aug 2026 and 6 Sep 2026. That
is under 90 days, so they are not stale.

---

## 1 · Threat model in four lines

1. **Who wants this data, and what is the cheapest way in?** Colleagues, not outsiders.
   A logged-in employee with browser developer tools can call any whitelisted endpoint
   (a server function the browser is allowed to call) with any record name. That lets
   them change a colleague's goal progress (S1), approve their own evidence (S2), raise
   their own rating (S3), or list every employee (S6). A manager can read a draft
   self-review (S4) or a report's loss-of-pay amount (S5). An HR user can approve their
   own request (S7), or reach employees of a company they do not look after (S10).
2. **Blast radius of one mistake.** Mostly **one tenant, every employee in it**. S6 and
   S10 cross companies *inside* a tenant. Each tenant is a separate site, so nothing here
   crosses tenants. S8 is the largest: a script planted in a goal name runs with the
   rights of whoever opens it, usually a manager or HR.
3. **What this makes possible that was impossible before.** The fixes add no new
   collection. They *remove* visibility and writes. The risk is breaking a real use:
   the reviewer picker, the org-chart search, or HR acting on behalf of someone. Those
   are listed as open questions, not quietly decided.
4. **How would we find out?** **Today we would not.** Refusals are not logged in a way
   anyone reviews. None of these paths leaves a trace that separates normal use from
   misuse. The self-review write in S1 does not even create a change history. **Detection
   is a gap in its own right** (SEC-17).

---

## 2 · Data inventory

Classes come from the baseline (feature map A1): `public / internal / sensitive /
statutory-id`. **No code in the repo applies these classes today.** I searched for a
sensitivity mechanism and found none. The classes below are a declaration, not a
control. No retention or purge job exists for any of these doctypes; the only purge job
is for check-in photos.

| Field or object | Class | Purpose | Retention | Who may see it |
|---|---|---|---|---|
| KPI `self_rating`, `self_comment` | sensitive | Performance review | Decision record, legal hold [counsel, C3] | Subject, their manager line, HR |
| KPI `manager_rating`, `potential_rating`, `manager_comment` | sensitive (decision-bearing) | Performance review | Same | Manager line, HR. Subject only after release (Q4) |
| Individual Goal `goal_name`, `unit` | internal | Goal tracking | Life of goal | Subject, manager line, HR |
| Individual Goal `actual_progress`, `progress_pct` | sensitive (feeds rating) | Performance review | Decision record | Same. **Written only by an approved path** |
| Goal Evidence `value`, `raw_extracted_data`, `validation_notes` | sensitive (may hold customer or sales detail) | Evidence for progress | Decision record | Subject, approver, HR |
| Evidence and progress-log **files** (Goal Evidence, Goal Progress Update, KPI Progress Log) | sensitive | Evidence for progress | Decision record | Same. **Never a public link** |
| Appraisal Extension: `page_data`, `achievements_text`, `challenges_text`, `development_needs_text`, `support_needed`, `overall_comment`, `next_period_goals_text` | sensitive | Self-review | Decision record | Subject always. Manager line and HR **only after it is sent** |
| Appraisal Extension: `manager_internal_notes`, `potential_rating`, `avg_potential_rating`, `potential_category`, `calibration_notes` | sensitive (decision-bearing) | Manager review, calibration | Decision record | Manager line, HR. **Never the subject** (Q4 for potential) |
| Appraisal Extension: `overall_rating`, `manager_feedback` | sensitive (decision-bearing) | Review outcome | Decision record | Manager line, HR. Subject after release (Q4) |
| Appraisal Extension: `invited_reviewers` (names, comments, allowed pages) | sensitive | 360 input | Decision record | Manager line, HR. The reviewer sees their own entry only |
| Attendance Deduction `lwp_amount`; Additional Salary `amount` | sensitive (pay) | Payroll deduction | Payroll records [counsel, C3] | Subject, HR Manager, Payroll. **Never a manager** (decision Q-b) |
| Attendance Deduction `lwp_days`, `deduction_days`, `explanation`, violation times | sensitive | Late-coming rule | Payroll records | Subject, HR. Manager: **days only** |
| Employee `employee_name`, `designation`, `department`, `image` | internal | Directory | Life of employment | Hierarchy scope (PRIV-5) |
| Employee reporting chain (`reports_to`, positions) | internal (commercially sensitive, per `reach()` docstring) | Org chart | Life of employment | Reach window (SEC-8) |
| Employee `ctc` | sensitive | Payroll | Life of employment | HR Manager, Payroll (permlevel 1 in Frappe) |
| Employee `pan_number`, `bank_ac_no`, `iban` | statutory-id | Payroll, statutory | Statutory [counsel] | HR Manager, Payroll (permlevel 1) |
| Employee `health_details`, `blood_group`, `passport_number` | sensitive / statutory-id | HR record | Statutory [counsel] | HR only |
| Leave Application `description` (reason) | sensitive (may reveal health) | Leave administration | Operational HR record | Subject, named approver, HR |
| Attendance Request `reason`, `explanation` | sensitive | Attendance correction | Operational HR record | Subject, decider |

---

## 3 · Access intent, including who must NOT see what

"Manager line" means anyone above the person in `Employee.reports_to`, at any depth. This
is what `_subordinates` / `descendants` already mean. Where the code uses direct reports
only, that is noted. Choosing one rule is open question Q11 below (appendix D, B10), and it
is not decided here.

| Persona | May see and do | Must NOT see or do |
|---|---|---|
| **Employee** | Own goals, KPIs, evidence, self-review, deductions (days and amount), leave, payslip. Own draft self-review until sent. Released outcome of own review. Directory within their scope (PRIV-5) | Any colleague's goals, KPIs, evidence, deductions or review. Own `manager_internal_notes`, own potential rating or category, own overall rating before release. **Write** anything on own review after sending. Set own goal progress or approve own evidence. Edit any colleague's record. Anyone outside their search scope |
| **Manager** (any level) | Reports' goals, KPIs, evidence, and approve them (direct manager, per current code). Reports' self-review **once sent**. Write the manager review in Manager Review stage. Reports' late-rule counts and **loss-of-pay days** | A report's self-review **before it is sent**. A report's **loss-of-pay amount**, in any payload, screen, email, print, report or REST read. Their **own** requests in their approval queue. Their own review's manager fields. Anyone outside their hierarchy in people search |
| **Invited reviewer** | The pages the manager allowed, for that one review, while invited | Any other page of the self-review. Any other review. Being able to create records by asking |
| **HR Manager / HR User** | Employees of the companies they are permitted (Q2). Reviews in HR Review or Completed. Their own review as the subject. Their reports' reviews as a manager. On-behalf leave within their companies | **Their own requests, evidence, KPI updates or rating** in any decide or rate path. A stranger's review before HR Review. Employees of companies they are not permitted. `ctc`, PAN or bank details through a leave endpoint (HR User has no permlevel-1 read in Frappe). Loss-of-pay amounts, for HR User (Q7) |
| **System Manager / CXO** | Same as HR, across the companies they are permitted. There is no CXO role in code; CXO is a persona holding HR or System Manager roles | Deciding or rating their own records. No exemption from separation of duties |
| **User with no Employee record** (website, vendor or driver portal users) | Nothing in these endpoints | Org chart, search, reviews. **Today `_within_reach` lets them through** (F-8) |

---

## 4 · Obligations engaged

I am not a lawyer. These are engineering requirements taken from the baseline, not legal
rulings. Dates are when the baseline entry was last verified. None is older than 90 days.

| Obligation | What it asks of this slice | Baseline section, verified |
|---|---|---|
| DPDP Act 2023 + Rules 2025: reasonable security safeguards, including access control | SEC-1 to SEC-14: server-side, fail-closed access checks on every endpoint in scope | §2, 24 Aug 2026 |
| DPDP: purpose limitation and data minimisation | PRIV-3/4 (pay amount is not needed to manage lateness), PRIV-5 (directory scope), PRIV-6 (no full Employee record in a leave call) | §2, 24 Aug 2026 |
| DPDP: breach handling (immediate intimation to data principals and the Board; detailed report within 72 hours) | Only if any of these holes was **used**. We cannot tell today (threat line 4). Question C1 | §2, 24 Aug 2026 |
| CERT-In Directions 2022: report "unauthorised access" incidents within 6 hours of becoming aware | Same trigger as above. Question C1 | §3, 24 Aug 2026 |
| CERT-In: ICT logs 180 days in India | Refusal logging (SEC-17) produces logs. They are in France today, so still not compliant (known gap, not this slice) | §3a, 6 Sep 2026 |
| GDPR Art 22 and Art 32 (anticipatory until the founder confirms EU exposure) | A rating must be made by the accountable human, not edited by its subject (SEC-5, SEC-10); security of processing | §4, 24 Aug 2026 |
| ISO/IEC 27001:2022: access control, segregation of duties; feature map B7 and F1 | SEC-9, SEC-10: no self-approval and no self-rating path exists | §5, 24 Aug 2026 |
| OWASP ASVS 5.0 Level 2 (adopt now): access control, output encoding, file handling | SEC-4 (file uploads), SEC-11 (encoding), SEC-12 (no script push) | §5, 24 Aug 2026 |
| Feature map I1, I3, I4 (CI gates) | SEC-15 (pin tests in CI), SEC-16 (`ignore_permissions` count in touched files), PRIV-8 (no personal values in logs) | feature map, 24 Aug 2026 |

---

## 5 · Abuse cases, verified against the code

"Verified" means I read the lines at `4e3ba28`. Where I also checked data on `ppj.localhost`,
it says so. Every bench check was read-only: `frappe.has_permission`, `frappe.get_list`
as a user, counts, then a rollback. "On main" means the same code is on `origin/main`
(`42c165d`), checked with `git show`.

| # | Actor, state, path, result | Evidence | Status |
|---|---|---|---|
| **S1** | Rahul, own review in Employee Review. He calls `save_review_page(appraisal=own, page_key="past-objectives", page_data_json={"kpis":{"<Neha's KPI>":{"self_rating":1}},"objectives":{"<Neha's goal>":{"actual_progress":0}}})`, then `submit_employee_review(own)`. Neha's KPI self-rating and goal progress are overwritten. No Version row (change history) is written, and errors are swallowed | `performance_api.py:3559` checks only that the *appraisal* is his; `:3575-3587` KPI loop with `frappe.db.set_value` at `:3585`; `:3589-3597` goal loop at `:3594`; `except: pass` at `:3586`, `:3596`. `save_review_page` `:3521-3550` stores any JSON | **Exists. On main.** Also lets him set **his own** goal progress without approval |
| **S2** | Rahul opens his goal and submits evidence "value 500000". It is saved as Approved and progress moves at once. The file goes to `/files/…`, a public link anyone on the internet can open without logging in | `alvoraa_goals/api/goal_api.py:71` hard-codes `"Approved"`; `:83-84` recalculates; upload `hrms-employee.html:9084` `is_private=0`. Bench: 996 evidence rows, all Approved, no files | **Exists, worse (F-5). On main** |
| **S3** | Rahul, desk or REST: `GET` and `PUT /api/resource/Alvoraa Appraisal Extension/HR-APR-2026-00058` (his Completed review, overall 4.5). He can read `manager_internal_notes` and `potential_rating`, and **write** `overall_rating` or `review_status`. Separately, `get_my_appraisals` returns `overall_rating` at any stage | Doctype JSON: Employee role read/write/create, all fields permlevel 0, no `permission_query_conditions` for this doctype in `alvoraa_goals/hooks.py:29-36`. `performance_api.py:3195`. `get_appraisal_extension:2334-2335` returns potential rating and category to the subject. Bench: `has_permission` read **and write** True for Rahul on both his extensions; `get_list` returns 2 rows | **Exists, worse (F-1). On main.** Cross-colleague read is blocked on ppj only because the tenant has User Permissions on Employee. That is tenant setup, not code |
| **S4a** | Sakshi, while Rahul's review is still in Employee Review, calls `get_manager_review(Rahul's appraisal)`. She receives his whole draft `page_data`. `get_appraisal_extension` gives her his draft narrative | `:3649-3736` has no stage check; `:3656` any-depth `_is_manager_of`; `:2314` any-depth `_subordinates`, `:2336-2339` narrative with no stage check. Bench: Sakshi has read and write on Rahul's in-progress extension | **Exists. On main** |
| **S4b** | An HR User in another store, not in Rahul's line, calls `get_manager_review` on Rahul's draft. It succeeds. The HR guard `_assert_hr_can_view` is never called there, nor in `save_manager_review` or `submit_manager_review`, so that HR User can also **write** Rahul's manager review during Manager Review | `:3655-3658`, `:3759`, `:3981`; guard defined at `:48` | **Exists. On main** |
| **S4c** | Any employee calls `get_reviewer_view(<any appraisal name>)`. An extension record is **created and committed** before the invitation check. An invited reviewer receives **all** of `page_data`, not just the allowed pages | `:3889` (`_get_or_create_extension` commits at `:2305`) before the check at `:3893`; `:3927` returns full `page_data` | **Exists. On main** |
| **S5** | Sakshi's browser calls `get_team_late_list`. The reply includes `recent[].lwp_amount = 548.39` and `explanation` for Rahul. The screen shows days only. On a tenant without PP Jewellers' Custom DocPerm, Sakshi can also `GET /api/resource/Attendance Deduction/HR-ADD-2026-00116`, which gives the Employee role read, and a row rule that lets her whole line through, and read `lwp_amount` | `hr_api.py:2473-2497`, fields at `:2424`, `recent` at `:2494`. Doctype JSON: Employee read. `hrms/alvoraa_late_rules/permissions.py:36-44`. `lwp_amount` permlevel 0. Bench: ppj's Custom DocPerm leaves only System Manager, so desk reads fail there | **Payload leak exists (dev only, not on main). Email: carries days, not amount** (`attendance_deduction.py:37-60`, `:197-205`), which is inside decision Q-b |
| **S6a** | Rahul calls `hrms.alvoraa_org_structure.api.search_people(q="an")` or `performance_api.search_employees(query="")`. He gets up to 12, or 80 plus 20, active employees from every company, with designation, department and photo | `api.py:546-558`, `performance_api.py:1459-1487`. Both use `frappe.get_all`, which skips permission checks | **Exists.** `search_people` dev only; `search_employees` **on main** |
| **S6b** | Rahul calls `my_view(employee=<any employee>)` and gets that person's manager chain to the top, their peers and their team. `chain_to_top(node=<any>)` returns the chain above any node, trimmed to 3 steps but never checked for reach | `api.py:392-415` (no `_within_reach`); `:888-930` (trims at `:926-929`, no reach check) | **Exists. Dev only** |
| **S7** | Kamal (HR Manager) raised attendance correction HR-ARQ-26-09-00001 for himself. He calls `attendance_correction.decide(name, approve=1)`, and it is submitted. As HR he can also call `approve_kpi_update` on his own KPI update | `attendance_correction.py:722-755` (no subject check); `_may_review` `:237-245` is role-based. `performance_api.py:382` (`_is_hr()` passes for the owner). Bench: that request exists, `owner` = Kamal | **Exists.** `decide` dev only; `approve_kpi_update` **on main**. Wider: F-2, F-3 |
| **S8** | An employee names a future goal `<img src=x onerror=…>` in the self-review wizard (`submit_employee_review:3625`), or through any path that skips Frappe's save-time cleaner. Their manager opens it from Team goals (`openTeamGoalDrawer` → `get_goal_detail` → `renderGoalDrawer`), and the script runs with the manager's session | `hrms-employee.html:8742` (`g.goal_name`), `:8745` (`g.employee_name`), caller `:8674`. Frappe's cleaner (`base_document._sanitize_content`) strips most attributes on a normal insert but is skipped by `frappe.db.set_value`, and skips Attach fields. I did not plant a payload, because that would be a write | **Sink exists. On main.** More sinks: F-6 |
| **S9** | Every review notification calls `publish_realtime("eval_js", {"script": …}, user=…)`. Frappe's desk runs whatever script arrives on that channel. Today the script is harmless. But the channel is the defect: anyone who can influence that dict, or who copies the helper, has remote script execution in a colleague's browser | `performance_api.py:3113-3127`, `:3121-3125`. The only `eval_js` in our apps (grep) | **Exists. On main** |
| **S10** | An HR User whose job covers Company A calls `apply_leave(…, on_behalf_of=<employee of Company B>)` and creates Company B leave. Or they call `get_leave_summary(employee_id=<B>)` and receive B's **whole Employee record**. `get_all_active_employees` lists every company | `hr_api.py:1653-1654` then `insert(ignore_permissions=True)` `:1672`; `:1527-1528`, full doc returned `:1595`; `:1508-1520`; `preview_leave_request:1701-1702` | **Exists. On main.** Worse: F-10 |

---

## 6 · Requirements

Rules for every item:

- **Enforcement is always on the server.** A hidden button or a filtered screen does not
  count.
- **Fail closed:** any doubt (no Employee record, unknown status, missing company
  permission, unparseable input) means **refuse** with `frappe.PermissionError`. Write
  nothing, and log the refusal (SEC-17).
- **One mechanism per rule**, called from every path it covers. That means one scope
  helper, one decision guard, and one review-field filter. Ten separate `if`s would
  drift apart.
- Tests run on `test_site`, with synthetic users made for the test. Never real people's
  data.

### Security

**SEC-1 · The self-review writes only the subject's own records. (S1)**
- *Rule:* `submit_employee_review` updates a KPI only if `KPI.employee == Appraisal.employee`
  and the KPI is in the appraisal's cycle. It never writes `Individual Goal.actual_progress`.
  It writes through the document API (`doc.save`), so a Version row exists.
- *Enforcement:* `submit_employee_review`, and also `save_review_page`, which rejects
  foreign names at save time so the error shows early.
- *Fail closed:* one foreign or unknown name refuses the **whole** submission. The status
  stays Employee Review. No exception is swallowed.
- *Test:* Employee A saves page data naming colleague B's KPI and goal, then submits →
  `PermissionError`. B's `self_rating` and `actual_progress` are unchanged. A's status is
  still "Employee Review". **Negative:** A names **own** goal `actual_progress` → refused or
  ignored, and the value is unchanged. **Positive:** A rates own KPI → value saved, and a
  `Version` row exists for that KPI.

**SEC-2 · Rating fields on a KPI are written only by the manager line or HR, whatever the
path. (S1 class, F-18, recommended)**
- *Rule:* `manager_rating`, `potential_rating` and `manager_comment` may change only when the
  caller is in the subject's manager line or is HR, **and** is not the subject.
- *Enforcement:* `alvoraa_goals.controllers.kpi.validate_kpi`, which covers the portal, desk,
  REST and import.
- *Fail closed:* no Employee record for the caller → refuse.
- *Test:* An employee who created their own KPI calls `frappe.client.set_value("KPI", own,
  "manager_rating", 5)` → `ValidationError`/`PermissionError`, value unchanged. Manager does
  the same → succeeds. An HR user who is the KPI's subject → refused.

**SEC-3 · Evidence starts as Pending and only an approver can approve it. (S2)**
- *Rule:* every new Goal Evidence row is saved as `Pending`, whoever submits it. Progress is
  recalculated only from `Approved` rows. Only the goal owner's manager or HR, **never the
  goal owner**, can approve or reject. Approval addresses the row by **row name**, not by
  list position.
- *Enforcement:* `goal_api.submit_goal_evidence`, `controllers/evidence.approve_evidence` and
  `reject_evidence`, and the `hr_api` proxies.
- *Fail closed:* an unknown row, or a goal owner without a manager and no HR caller →
  refuse.
- *Test:* Employee submits → response and database say `Pending`; `actual_progress` is
  unchanged. Owner calls `approve_goal_evidence` on own row → `PermissionError`. An HR user
  approving **their own** goal's evidence → `PermissionError`. The manager approves by row
  name → `Approved`, progress recalculated, audit log row written. Reordered rows → the
  right row is approved.

**SEC-4 · Evidence and progress files are private, owned by the submitter, and attached
to the record. (S2, F-5)**
- *Rule:* the server accepts `evidence_file` / `evidence_url` only if it names a `File`
  record with `is_private = 1` whose `owner` is the caller. After saving, the File is
  attached to the goal or KPI, so reading the file follows reading the record. All four
  portal upload calls send `is_private=1`.
- *Enforcement:* `goal_api.submit_goal_evidence`, `goals_api.submit_goal_update`,
  `performance_api.log_kpi_progress`, plus the page at `:8975`, `:9084`, `:10359`, `:12062`.
- *Fail closed:* a public URL, an external URL, a `javascript:` value, or a file owned by
  someone else → refuse, and write nothing.
- *Test:* Submit with a `/files/x.pdf` public file → refused. With `https://evil/x` →
  refused. With another user's private file → refused. With own private file → accepted,
  and `File.attached_to_name` equals the goal. A colleague outside the goal's line requests
  the `/private/files/…` URL → HTTP 403. A static test asserts no `is_private", "0"` remains
  in the portal page.

**SEC-5 · No direct Employee-role access to the Appraisal Extension doctype. (S3, S4,
F-1)**
- *Rule:* the Employee role has no read, write or create DocPerm on `Alvoraa Appraisal
  Extension`. All employee and manager access goes through whitelisted endpoints that apply
  PRIV-1 and PRIV-2. HR keeps its doctype permissions.
- *Enforcement:* doctype JSON, plus a check that no tenant Custom DocPerm re-grants it
  (report any found; do not silently overwrite them).
- *Fail closed:* yes, by removal.
- *Test:* As an Employee-role user, `frappe.client.get`, `get_list` and `set_value` on their
  **own** extension → `PermissionError`. As a manager, `set_value(report's extension,
  "overall_rating", 5)` → `PermissionError`. As HR Manager, `get` → succeeds. Every
  portal review flow still works (run the existing `test_appraisal_visibility.py`).

**SEC-6 · Manager-review endpoints check stage, relationship and the HR guard, in that
order, before touching any record. (S4)**
- *Rule:* `get_manager_review`, `save_manager_review`, `submit_manager_review`,
  `save_overall_rating`, `invite_reviewer`, `invite_reviewers_batch`, `add_action_item`,
  `return_for_revision` and `advance_review_status` first confirm the caller is in the
  subject's manager line or is HR. For HR acting outside their own line, they apply
  `_assert_hr_can_view`. Only then may they read or create the extension.
- *Enforcement:* those endpoints. One shared helper, not a copy in each one.
- *Fail closed:* no extension yet, and the caller is not authorised → refuse **without
  creating one**.
- *Test:* HR User outside the line, subject in Manager Review → `get_manager_review` and
  `submit_manager_review` refused. Extension row count is unchanged after an unauthorised
  call on an appraisal with no extension. The existing
  `test_a_manager_who_is_also_hr_can_still_do_a_manager_review` still passes.

**SEC-7 · An invited reviewer sees only the allowed pages of one review, and can be
invited only from the subject's company. (S4, F-12, F-13)**
- *Rule:* `get_reviewer_view` and `submit_reviewer_comments` check the invitation **before**
  any read or write, and never create an extension. `page_data` is cut to
  `allowed_pages`. Only active employees of the subject's company, other than the subject,
  can be invited (Q9).
- *Enforcement:* those four endpoints.
- *Fail closed:* an empty `allowed_pages` means no pages.
- *Test:* A non-invited employee calls `get_reviewer_view(<appraisal with no extension>)` →
  `PermissionError`, and the extension count is unchanged. Invited with
  `allowed_pages=["past-dev"]` → response `page_data` keys are exactly `{"past-dev"}`.
  Manager invites an employee of another company → refused.

**SEC-8 · Every org-chart endpoint checks reach for the node it is asked about, and a
caller with no Employee record gets nothing. (S6, F-8)**
- *Rule:* `my_view(employee)`, `chain_to_top(node)`, `subtree(root)` and `get_children(parent)`
  call `_within_reach` for any node that is not the caller's own. `_within_reach` returns
  **False** when the caller has no Employee record.
- *Enforcement:* `hrms/alvoraa_org_structure/api.py`.
- *Fail closed:* yes (a change from today's `return True` at `:657-658`).
- *Test:* An ordinary employee with default reach (2 up, 2 down) calls
  `my_view(employee=<3+ levels away>)` → `PermissionError`, and the same for `chain_to_top`
  and `get_children`. A logged-in user with no Employee record calls `subtree(root=X)` →
  `PermissionError`. HR (full-reach role) → allowed. **Must run in CI** (SEC-15; today
  `test_reach.py` does not).

**SEC-9 · Nobody decides their own request. (S7, F-3)**
- *Rule:* one guard, `caller's Employee != subject Employee`, on every decide path. That
  covers approve **and** decline, because declining your own request is withdrawing it.
- *Enforcement, one guard called from each:*
  - `attendance_correction.decide`, plus a `before_submit` doc event on Attendance Request
    so desk submits are covered too
  - `performance_api.approve_kpi_update`
  - `goals_api.approve_goal_update`
  - `evidence.approve_evidence` and `reject_evidence`
  - `hr_api.action_leave`, which refuses self-approval even when HR Settings
    `prevent_self_leave_approval` is 0 (it is 0 on ppj; Q8)
  - `to_review` and any approvals list, which leave out the caller's own items
- *Fail closed:* the caller has no Employee record but holds an HR role → allowed only if the
  subject is not linked to the caller's user (compare `user_id` too).
- *Test:* for each path, an HR Manager who is the subject → `PermissionError`, and the
  document is unchanged (docstatus, approval status). A second HR Manager → succeeds. Desk:
  `frappe.get_doc("Attendance Request", own).submit()` as the subject → refused.
  `to_review` as the subject → own request not listed.

**SEC-10 · Nobody rates their own review. (S7 class, F-2)**
- *Rule:* the subject of an appraisal cannot call `save_manager_review`,
  `submit_manager_review`, `save_overall_rating`, `save_calibration_note` or
  `save_additional_reviewer_rating` on their own record. Holding HR or System Manager does not
  change that.
- *Enforcement:* the same guard as SEC-9.
- *Fail closed:* yes.
- *Test:* An HR Manager with their own appraisal in Manager Review calls each endpoint on it →
  `PermissionError`, and `overall_rating` is unchanged. Their manager → succeeds.

**SEC-11 · User-entered text in the goal drawer and evidence list is escaped, and links are
checked. (S8, F-6)**
- *Rule:* in `renderGoalDrawer` and the evidence list, each of `goal_name`, `employee_name`,
  `unit`, `trajectory` label, `evidence_type`, `validation_notes` and `raw_extracted_data` goes
  through `esc()`. `evidence_file` is rendered only if it starts with `/private/files/`, and is
  escaped as an attribute. The same applies to the second drawer's `g.unit` at `:10230`.
- *Enforcement:* client escaping as the output rule, **and** SEC-4 on the server, so a bad
  link cannot be stored.
- *Fail closed:* an unrecognised link → no link is drawn.
- *Test:* A static check (in the style of `scripts/check_portal_handlers.js`) fails if any of
  those fields is concatenated into HTML without `esc(`. A server test: a goal named
  `<img src=x onerror=alert(1)>` stored via `frappe.db.set_value`, fetched through
  `get_goal_detail`, returns the raw text. The client check proves it is escaped. If a DOM
  test harness exists, render it and assert no element has an `onerror` attribute.

**SEC-12 · The server never pushes script to a browser. (S9)**
- *Rule:* no `publish_realtime("eval_js", …)` anywhere in `alvoraa_portal`, `alvoraa_goals` or
  our `hrms/hrms/alvoraa_*` modules. `_send_notification` stops swallowing every error
  silently. It logs the failure with the recipient's user id and subject only.
- *Enforcement:* remove the call. A static test is the guard.
- *Test:* A test greps those folders for `eval_js` and fails on any hit. A unit test mocks
  `frappe.publish_realtime` and `frappe.sendmail`, calls `_send_notification`, and asserts no
  realtime call with event `eval_js`.

**SEC-13 · HR acts only for employees of the companies they are permitted. (S10, F-11)**
- *Rule:* `apply_leave(on_behalf_of)`, `preview_leave_request(on_behalf_of)`,
  `get_leave_summary(employee_id)` and `get_all_active_employees` accept a target only if the
  caller may read that Employee under Frappe's own rules (`frappe.has_permission("Employee",
  "read", doc)`, which applies User Permission on Company). `get_all_active_employees` uses
  `frappe.get_list`. The leave insert stops using `ignore_permissions`, or checks first.
- *Enforcement:* those four endpoints, through the shared scope helper (Handoff note).
- *Fail closed:* on a tenant with more than one company, an HR user with no Company User
  Permission → only their own Employee's company (Q2).
- *Test:* On `test_site` with two companies, an HR User permitted Company A calls
  `apply_leave(on_behalf_of=<B employee>)` → `PermissionError`, and no Leave Application is
  created. `get_leave_summary(<B>)` → refused. `get_all_active_employees` → only A.
  `preview_leave_request(on_behalf_of=<B>)` → refused. A System Manager with no restriction →
  both.

**SEC-14 · `get_employee_goals` checks the target person, not a doctype-wide right.
(F-4, recommended)**
- *Rule:* reading another employee's goals requires the caller to be in their manager line or
  HR. A doctype-level `has_permission("Individual Goal","write")` is not enough, because every
  Employee holds it.
- *Enforcement:* `alvoraa_goals/api/goal_api.py:24`.
- *Test:* Rahul-like employee calls `get_employee_goals(employee_id=<stranger>)` →
  `PermissionError`. Own → returns. Manager for a report → returns.

**SEC-15 · Every fix has a named test that runs in CI. (all)**
- *Rule:* one test module, `alvoraa_portal/alvoraa_portal/tests/test_portal_security_010.py`,
  with at least one test per requirement, named after it, e.g.
  `test_sec1_self_review_cannot_write_a_colleagues_kpi`. It lives in `alvoraa_portal`
  because **CI runs only `--app alvoraa_goals` and `--app alvoraa_portal`**
  (`.github/workflows/ci.yml:281-282`). Tests placed in `hrms` would not run (Q10).
- *Test:* the test engineer's report lists each `SEC`/`PRIV` ID against a passing test. A
  deliberate revert of any one fix on a scratch branch makes its test fail. Proven once, and
  recorded in `04-test-report.md`.

**SEC-16 · `ignore_permissions` does not grow in the files this slice touches.**
- *Rule:* the counts at `4e3ba28` are a ceiling: `performance_api.py` 88, `hr_api.py` 77,
  `goals_api.py` 15, `attendance_correction.py` 2, `goal_api.py` 0, `evidence.py` 0,
  `alvoraa_org_structure/api.py` 2. There is no repo-wide counter in CI (feature map I3 is
  missing). Across our three apps' folders I count 539.
- *Test:* a test reads each file, counts `ignore_permissions`, and fails if any count is above
  its ceiling. The ceilings are lowered in the same commit whenever a use is removed.

**SEC-17 · Refusals on these endpoints leave a trace someone can query. (threat line 4)**
- *Rule:* every `PermissionError` raised by the guards in this slice writes one structured log
  line with: time, user, endpoint, target doctype and name, and rule ID. **No field values.**
  Use `frappe.logger("security")`, not Error Log, so it does not flood the desk.
- *Test:* trigger a SEC-1 refusal and assert one log record with those keys. Assert the
  record does not contain the submitted rating or comment text.

### Privacy

**PRIV-1 · The subject never receives manager-only review fields. (S3)**
- *Rule:* one function decides which extension fields a viewer may receive, from their
  relationship (subject / manager line / HR / invited) and `review_status`. For the subject:
  `manager_internal_notes`, `calibration_notes`, `potential_rating`, `avg_potential_rating`,
  `potential_category` are **never** returned. `overall_rating` and `manager_feedback` only
  from the release stage (Q4). Every endpoint that returns extension data goes through it:
  `get_my_appraisals`, `get_appraisal_extension`, `get_employee_final_review`, `get_my_review`,
  `get_manager_review` (HR subject), `get_team_reviews` (HR's own row).
- *Fail closed:* an unknown status → the subject gets the narrowest field set.
- *Test:* a parameterised test over every review status × each endpoint. As the subject,
  assert those keys are **absent** (not just empty) from the JSON. As the manager, present. An
  HR Manager who is the subject calls `get_manager_review` on own → refused or filtered.

**PRIV-2 · Managers and HR do not see a self-review before it is sent. (S4, decision Q-d)**
- *Rule:* while `review_status` is `Not Started` or `Employee Review`, nobody but the subject
  receives `page_data`, `pages_completed`, the narrative fields or `overall_comment`. After
  `return_for_revision` sends it back, it is hidden again until re-sent [ASSUMPTION].
- *Enforcement:* the PRIV-1 function, used by `get_manager_review`, `get_appraisal_extension`
  and `get_reviewer_view`.
- *Test:* Manager calls `get_manager_review` for a report in Employee Review → refused.
  `get_appraisal_extension` → no narrative keys. Employee submits → manager now receives them.
  Manager returns it → hidden again.

**PRIV-3 · A manager never receives a report's loss-of-pay amount. Days at most. (S5,
decision Q-b)**
- *Rule:* no reply, screen, email or notification sent to anyone other than the subject,
  HR Manager or Payroll contains `lwp_amount`, the Additional Salary amount, or any money
  figure derived from pay. `lwp_days` is allowed.
- *Enforcement:* `get_team_late_list` asks for an explicit field list without `lwp_amount`
  (`_deduction_rows` takes a `fields` argument). The deduction email keeps building its text
  from days only.
- *Test:* seed a submitted deduction with `lwp_amount = 548.39` for a report. The manager calls
  `get_team_late_list` → a recursive key scan of the JSON finds no `lwp_amount`, and a value
  scan finds no `548`; `lwp_days` is present. Submit a deduction with `notify_manager = 1` → the
  Email Queue message has no currency figure. The employee's own `get_my_attendance_deductions`
  still includes the amount.

**PRIV-4 · The loss-of-pay amount is restricted on the doctype itself. (S5, F-9)**
- *Rule:* `Attendance Deduction.lwp_amount` moves to permlevel 1, readable by HR Manager,
  Payroll User and System Manager (HR User: Q7). That closes the desk form, REST, print and
  report on every tenant, not just the ones with PP Jewellers' custom permission.
- *Enforcement:* doctype JSON in our `hrms` fork.
- *Test:* on `test_site` with the shipped permissions (no Custom DocPerm), a manager calls
  `frappe.client.get("Attendance Deduction", report's)` → `lwp_amount` absent or null.
  Payroll User → present.

**PRIV-5 · People search finds only the searcher's own hierarchy downwards. (S6,
decision Q-c)**
- *Rule:* `search_people` and `search_employees` return only active employees in the caller's
  subtree (`alvoraa_goals.permissions.descendants`). A person with no reports finds themselves
  only [proposed, Q1]. HR, System Manager and CXO find employees of their permitted companies
  [proposed, Q2]. Fields: employee id, name, designation, department, image. No contact
  details.
- *Enforcement:* one scope helper, used by both endpoints and by SEC-13.
- *Fail closed:* no Employee record and no HR role → empty list.
- *Test:* Manager M with subtree {A, B, C} searches a name matching A and a stranger S → only A.
  An employee with no reports searches a colleague's name → empty or self only. HR permitted
  Company A searches a Company B name → no B rows. No-employee user → `[]`.

**PRIV-6 · Leave lookups return only the fields the leave screen uses. (S10, F-10)**
- *Rule:* `get_leave_summary` returns `employee` as {id, name, company, department}. It never
  returns a full `Employee` document.
- *Test:* as an HR User, `get_leave_summary(employee_id=<permitted employee with ctc set>)` →
  the response has no `ctc`, `pan_number`, `bank_ac_no`, `health_details`, `passport_number`,
  `date_of_birth` keys. As the employee for themselves, the same.

**PRIV-7 · Evidence files that are already public are made private. (S2)**
- *Rule:* a patch finds every `File` referenced from Goal Evidence `evidence_file`, Goal
  Progress Update `evidence_file` and KPI Progress Log `evidence_file` with `is_private = 0`.
  It makes each private (moving it under `/private/files/`), updates the referring row, and
  prints counts only.
- *Fail closed:* a file that cannot be moved is listed by File name for HR. It is not left
  silently public.
- *Test:* seed one public file on each of the three child tables → run the patch → each
  `is_private = 1`, the row points at the new URL, and an anonymous request to the old
  `/files/…` URL returns 404. Running it twice changes nothing.

**PRIV-8 · No personal or performance values in logs. (F-7)**
- *Rule:* remove the `[DEBUG]` `frappe.log_error` and `msgprint` blocks in
  `controllers/evidence.py:11-26` and `:64-77`. They write goal name, value and file link
  to Error Log. Logs written by this slice carry document names only.
- *Test:* insert a Goal Evidence row → no new Error Log whose title starts `[DEBUG]`. The
  PII-in-logs scan (feature map I4, not yet built): until it exists, a test asserts the string
  `[DEBUG]` does not appear in `evidence.py`.

---

## 7 · Found while verifying

Same class, same files. Each has evidence. "Include" means I recommend it goes in this slice
under the requirement named. The user decides.

| # | Finding | Evidence | Recommend |
|---|---|---|---|
| F-1 | **Employee role can read, write and create any Appraisal Extension, limited only by tenant User Permissions.** Rahul has write on his own Completed review; Sakshi has write on her reports' drafts | Doctype JSON perms; no row rule in `alvoraa_goals/hooks.py:29-36`; bench `has_permission` results. On main | **Include** (SEC-5). This is the "standing item" in `nfr-budget.md` §4, now verified |
| F-2 | **HR can rate their own review.** `save_manager_review:3759`, `submit_manager_review:3981`, `save_overall_rating:2861`, `save_calibration_note:2947` pass on `_is_hr()` with no subject check. `get_manager_review:3655` gives an HR subject their own internal notes | Code | **Include** (SEC-10, PRIV-1) |
| F-3 | **More self-approval paths:** `goals_api.approve_goal_update:1055`, `evidence.approve_evidence:145` and `reject_evidence:162` (HR role passes), `hr_api.action_leave:580`. The last relies on `prevent_self_leave_approval`, which is 0 on ppj | Code; bench HR Settings | **Include** (SEC-9) |
| F-4 | **Any employee can read any employee's submitted goals and approved evidence values.** `goal_api.get_employee_goals:24` checks a doctype-wide write right that every Employee holds | Bench: `has_permission("Individual Goal","write")` True for Rahul. On main | **Include** (SEC-14) |
| F-5 | **Four public upload paths**, not one: `:8975` goal update, `:9084` and `:10359` goal evidence, `:12062` KPI progress. The server accepts any string as the file link (`goal_api:45`, `goals_api:977`, `performance_api:311`) | Code. On main | **Include** (SEC-4, PRIV-7) |
| F-6 | **More unescaped sinks in the same drawer:** `evidence_file` into `href`/`src` `:8761-8762` (Attach fields skip Frappe's cleaner, so `javascript:` or a quote break-out would survive); `validation_notes` `:8765`; `raw_extracted_data` `:8767`; `evidence_type` `:8770`; `g.unit` `:8783`, `:10230`. **Dormant today:** the evidence query asks for columns that no longer exist (`hr_api.py:1953`, `:2126`) and the error is swallowed, so evidence never renders. **They go live the day someone fixes that query** | Code; Goal Evidence field list | **Include** (SEC-11) |
| F-7 | **Debug logging of evidence values** to Error Log and on-screen popups, `evidence.py:11-26`, `:64-77` | Code. On main | **Include** (PRIV-8) |
| F-8 | **Org chart fails open.** `get_children` (`api.py:55-65`) is whitelisted with no reach check. `_within_reach` returns True when the caller has no Employee record (`:657-658`) | Code. Dev only | **Include** (SEC-8) |
| F-9 | **Loss-of-pay amount readable through the desk and REST on any tenant with shipped permissions:** Employee role read, a row rule for the whole line, `lwp_amount` at permlevel 0 | JSON; `permissions.py:36-44`. ppj is protected only by its Custom DocPerm (which also blocks HR Manager, a functional problem for HR) | **Include** (PRIV-4) |
| F-10 | **`get_leave_summary` returns the whole Employee record to any HR User**, including `ctc`, `pan_number` and `bank_ac_no`. Frappe hides these from HR User (permlevel 1), but `frappe.get_doc` output is not filtered. Rahul's `ctc` is populated | `hr_api.py:1528`, `:1595`; bench meta permlevels. On main. I read the code; I did not call the endpoint | **Include** (PRIV-6) |
| F-11 | `preview_leave_request(on_behalf_of)` has the same company gap as S10 | `hr_api.py:1701-1702` | **Include** (SEC-13) |
| F-12 | **A manager can invite anyone from any company as a reviewer**, and today that person receives the whole self-review | `invite_reviewer:3790`, `invite_reviewers_batch:3847` | **Include** (SEC-7) |
| F-13 | **Records created before the permission check:** `submit_reviewer_comments:3946`, `advance_review_status:2403`, `return_for_revision:2461`, `update_action_item_status:2557` | Code | **Include** (SEC-6, SEC-7) |
| F-14 | **Progress moves before approval** in two more places: `log_kpi_progress:329` sets `actual_value` on logging; `submit_goal_update:1001` sets `actual_progress` | Code (appendix D B24) | **Not in 010.** It needs product decision Q22 ("progress only after approval?"). Record it; do not guess |
| F-15 | `set_org_setting` (`hr_api.py:2074`) lets an HR Manager write **any** Global Default key, including keys the platform depends on. The portal shows an "auto approve evidence" toggle (`:15991-16014`) that no server code reads, so the toggle does nothing | Code | **Not in 010** (different class). Raise as its own item. The toggle matters to SEC-3: Q6 |
| F-16 | **CI does not run tests in our `hrms` modules** (`ci.yml:281-282`). `test_reach.py`, `test_late_rules.py` and `test_org_structure.py` never run in CI | Workflow file | **Include as a condition** of SEC-15. Changing CI is outside a feature slice (parallel-work §6), so Q10 |
| F-17 | No `ignore_permissions` counter in CI (feature map I3). 539 uses across `alvoraa_portal`, `alvoraa_goals` and `hrms/hrms/alvoraa_*` | grep | **Include file-scoped** (SEC-16). The repo-wide gate is a separate item |
| F-18 | An employee who **created** their own KPI can set `manager_rating` on it through REST. The Employee role has doctype write on KPI, and `has_employee_permission` allows write when `owner == user`. On ppj no KPI was created by its own subject, so this is not seen in data | `alvoraa_goals/permissions.py` `has_employee_permission`; `kpi.json` perms | **Include** (SEC-2). Small, and it is the structural half of S1 |

**Worries, not findings** (I cannot write a full actor-and-path sentence for these):
- `alvoraa_portal/del_script.py` deletes every appraisal, cycle and extension when it is
  *imported* (module-level `run()`). It is not whitelisted and sits outside the Python
  package, so no web path reaches it. Anyone who runs it by hand wipes the review history.
  Worth deleting in a housekeeping change.
- Frappe's save-time HTML cleaner probably neutralises a script in `goal_name` on the normal
  insert path. I did not test a payload, because that would be a write. The sink is still
  the defect.

---

## 8 · Questions for counsel or the compliance owner

I am not a lawyer. Each question names the decision it blocks.

| # | Question | Owner | Blocks |
|---|---|---|---|
| C1 | S1, S2 (public files), S3 (self-edit of own rating), S4, S8, S9, S10, F-1, F-4 and F-10 are on `main`. If a production tenant runs `main`, and we **cannot show from logs** that nobody used these paths, is that a "personal data breach" under DPDP, or an "unauthorised access" incident under CERT-In? The 6-hour and 72-hour clocks start from awareness, so this has to be answered quickly. Also: as a likely data processor for the employer, what must we tell the customer, and when? | Counsel + founder | Whether to open an incident record today; whether to review production access logs before or after the fix ships |
| C2 | Managers learning a report's loss-of-pay **days** (decision Q-b). Is that covered by the employer's existing employment purpose and notice, or does the notice need to say it? | Counsel | Wording of any employee notice. **Does not block the build** |
| C3 | Retention for evidence files, deduction records and review extensions, and how legal hold applies to a disputed rating | Counsel | The retention column in section 2; a later purge engine. Does not block this slice |
| C4 | The potential rating and `manager_internal_notes` are about the employee. If the employee makes a data-access request, may the employer withhold them? PRIV-1 hides them **in the product**; an access request is a separate route | Counsel | Whether PRIV-1's "never the subject" is final, or "not in the portal, but disclosable on request" |
| C5 | Should an HR User (not HR Manager, not Payroll) see loss-of-pay amounts? | Compliance owner / founder | PRIV-4 role list (same as Q7) |

---

## Open questions

| # | Question | Owner | Decision it blocks |
|---|---|---|---|
| Q1 | What does a person with **no reports** find in people search? Proposed: themselves only | Product owner | PRIV-5 |
| Q2 | What do **HR, System Manager and CXO** find? Proposed: employees of their permitted companies, taken from Frappe User Permission on Company. If none is set on a multi-company tenant, their own company only (fail closed), not everything | Product owner | PRIV-5, SEC-13 |
| Q3 | Does decision Q-c ("own hierarchy, downwards") also apply to the **org chart** (`my_view` shows peers and two levels up; managers see the whole org via `alvoraa_org_managers_see_all`) and to the **reviewer picker**, which uses `search_employees` today (`hrms-employee.html:15321`, `:15378`)? If yes, managers can no longer invite a peer from another team | Product owner | PRIV-5, SEC-7, SEC-8 |
| Q4 | When is a review "**released**" to the employee: Employee Final Review (what `get_employee_final_review` shows today) or Completed (what the comment at `performance_api.py:2340` says)? And is the potential rating or category ever shown to the employee? | Product owner (+ C4) | PRIV-1 |
| Q5 | After a manager **returns** a self-review for revision, should it be hidden from them again until the employee re-sends it? Proposed: yes (recorded as an assumption until confirmed) | Product owner | PRIV-2 |
| Q6 | **Evidence auto-approval:** remove the unused "auto approve evidence" toggle, or make the server honour it (off by default)? Should Invoice or Sales Order evidence that passes validators still auto-approve? | Product owner | SEC-3 |
| Q7 | Loss-of-pay amount: HR Manager + Payroll + System Manager only, or HR User too? | Founder / compliance owner | PRIV-4 |
| Q8 | Turn on HR Settings `prevent_self_leave_approval` on every tenant as well as the portal guard? | Product owner | SEC-9 (leave part) |
| Q9 | Invited reviewers: same company only, or also other companies in the tenant? | Product owner | SEC-7 |
| Q10 | Should CI run tests in our `hrms` modules (DevOps change), or should all pin tests for this slice live in `alvoraa_portal`? | User + hrms-devops-engineer | SEC-15, and whether S5/S6 tests are pinned |
| Q11 | Direct reports or the whole line for manager review access? The code mixes both (`_reports_of` vs `_is_manager_of`, appendix D B10) | Product owner | SEC-6 detail. Until decided, keep each endpoint's current rule and only add the stage and HR checks |

## Assumptions

- [ASSUMPTION] Line numbers are at `4e3ba28`, and `origin/dev` had not moved when I fetched.
- [ASSUMPTION] `origin/main` (`42c165d`) is what production runs. I did not check production
  and must not.
- [ASSUMPTION] Bench permission results (`has_permission`, `get_list` as a user) reflect what
  the REST API would allow. I did not send any write to confirm.
- [ASSUMPTION] After `return_for_revision`, the self-review is hidden from the manager again
  until it is re-sent (PRIV-2).
- [ASSUMPTION] Evidence child-row hooks in `evidence.py` do not run when rows are appended
  through the parent's save (appendix D B2, inferred, not proven). SEC-3 therefore enforces
  Pending in `submit_goal_evidence` itself, not only in the hook.
- [ASSUMPTION] Removing the Employee DocPerm from `Alvoraa Appraisal Extension` breaks no
  portal flow, because every portal read and write goes through endpoints that use
  `ignore_permissions` or raw SQL (grep found no client-side `frappe.client` use of it). The
  engineer must confirm this in `00`.
- [ASSUMPTION] No sensitivity-class mechanism (feature map A1) and no retention engine (A6)
  exist, so the classes and retention in section 2 are declarations only.

## Handoff note

To the hrms-fullstack-engineer:

**Build three shared helpers, not twenty-five patches.**
1. A **scope helper**: "which employees may this user act on or find". It serves PRIV-5,
   SEC-13, SEC-7 invitee check and SEC-8. It reuses `descendants` and
   `frappe.has_permission("Employee", …)`.
2. A **decision guard**: "the caller is not the subject". It serves SEC-9 and SEC-10, and is
   also hung on Attendance Request `before_submit` so the desk is covered.
3. A **review-field filter**: relationship × status → allowed fields. It serves PRIV-1 and
   PRIV-2. Every review endpoint serialises through it.

**Order.** Do SEC-5 (doctype permission) and SEC-1 first. They close the two write holes
that let an employee change ratings and progress. Keep one commit per S-item, each with its
pin test (SEC-15), so a bad merge cannot drop one silently.

**Watch for these.**
- **SEC-5, PRIV-4 and PRIV-7 change doctype JSON or add a patch.** They take effect only
  after `bench migrate`, which is a deploy command that needs the user's approval. Tenants
  may hold Custom DocPerm rows that re-grant Employee access: report them, do not overwrite
  them.
- **`hrms-employee.html` is a hot file.** SEC-4 and SEC-11 touch it. Follow the hot-file
  rules in `parallel-work.md` §6.
- **Do not "fix" the dormant evidence query** (`hr_api.py:1953`, `:2126`) without SEC-11 in
  the same commit. Fixing the query alone switches on six unescaped sinks.
- **PRIV-5 may break two working features:** the org-chart search jump (`my_view(employee)`
  after `search_people`) and the reviewer picker. Stop and raise Q3 before changing their
  behaviour. Do not pick a winner.
- **The existing test `test_a_manager_who_is_also_hr_can_still_do_a_manager_review`** must keep
  passing next to SEC-6 and SEC-10. A manager who holds HR still reviews their reports, but
  never themselves.
- **S5's email is already within the decision.** Pin it (PRIV-3) rather than rewrite it.

**I disagree with one line of the plan.** Section 1a calls S3 a read leak. Treat it as a
**write** hole that lets an employee change their own finished rating. If the slice has to be
cut, cut from the "recommended" F-items, never SEC-5 or SEC-1.
