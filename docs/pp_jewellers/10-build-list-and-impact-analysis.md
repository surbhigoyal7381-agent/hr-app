# 10 — Build list and impact analysis

Six product builds make this demo possible. Each one follows the mandatory process in `CLAUDE.md` §2: impact analysis first, then a strategy, then **explicit approval before any code**. This file is the impact analysis and strategy for all six. Nothing here is implemented yet.

Order of building: B2 (small, unblocks payroll) → B1 (attendance rule, the client's headline pain) → B6 (attendance in appraisal) → B4 (employee documents) → B3 (screening form) → B5 (policy library). B3, B4 and B5 are independent of each other and can run in parallel.

**Feature registry (new rule from 2026-09-07).** Every build except B2 registers its own key in `FEATURES` in `alvoraa_portal/subscription.py` with `opt_in: True` and a `requires` list, so it stays off on every existing tenant until the console ticks it for a named tenant. Keys and dependencies are in file 00 §3. The subscription tests (`test_opt_in_features.py`) must be extended for each key. This is part of each build's scope, not a follow-up.

Module home for all six: a new module **`alvoraa_hr_core`** in the `hrms` fork (like `performance_management`), plus portal work in `alvoraa_portal`. Nothing goes into `grace_group`. All doctypes are created as JSON in the module; all fields on ERPNext or stock Frappe HR doctypes are **Custom Fields** created in a `after_install`/patch, so upstream JSON is untouched. Tests with `bench run-tests --app hrms` for each module.

---

## B1 — Quarter-day late rule (Attendance Deduction Rule, Attendance Deduction)

Spec: file 03 §3.

**Functional impact**

- Cross-module: creates Leave Ledger Entry (hrms leaves) and Additional Salary (hrms payroll). Reads Attendance, Shift Type, Employee, Salary Structure Assignment. No change to any existing controller. Callers of the functions used (`get_leave_balance_on`, Additional Salary insert) are unchanged.
- Personas: Employee sees deductions on the portal; Store In-charge sees the team late list; HR runs and amends; CXO sees a per-store tile.
- HRMS domains: leaves (balance decreases), attendance (read only), payroll (a deduction line). Appraisals read the deductions in B6.
- Portal: two new APIs in `hr_api.py`, one card, one sub-tab, one tile.

**Non-functional**

| Dimension | Effect | Note |
|---|---|---|
| Performance | Neutral | One weekly job: 400 employees × 7 Attendance rows, batched by `frappe.get_all` with `in` filters; no per-row queries inside loops. Portal reads are indexed on employee + week_start (add index). |
| Security | Neutral | Rule: HR Manager write. Deduction: HR Manager create/cancel; Employee read own (`permission_query_conditions` on employee = own, and manager chain via `reports_to`). No `ignore_permissions` in reads. Scheduler writes with `flags.ignore_permissions` scoped to the job only. |
| Reliability | Improves the process | Idempotent per employee-week (unique key employee + week_start + rule). Re-running updates a Draft, never duplicates a Submitted. Cancel reverses ledger and salary. Half-processed weeks (shift changed mid-week) use the Attendance row's own shift. |
| Scalability | Neutral | Linear in employees. Multi-company: rule is per company; the job iterates enabled rules. Concurrent runs guarded by a Redis lock per rule and week. |
| Maintainability | Improves | Replaces an Excel process with a documented rule. Logic in one controller with unit tests for the free-violation, rounding and leave-order cases using `expected_deductions.csv` as fixtures. |
| Data integrity | Watch | Two writers to leave balance (Leave Application and this). Both go through Leave Ledger Entry, which is the single source of truth, so balances stay consistent. Additional Salary `payroll_date` = week_end keeps the deduction in the right month. A week that spans two months lands in the later month; state this in the policy. |
| Compliance / privacy | Neutral | Punch times are already stored. Deduction explanation is visible to the employee, which is the transparency the client wants. |

**Risks and trade-offs**

- Leave Application does not support 0.25 days, which is why the balance is consumed by ledger entry, not by a Leave Application. Leave reports that read Leave Ledger Entry will show it; reports that only read Leave Application will not. Acceptable; call it out to the client.
- Daily wage basis: `base / days in month` is simple and explainable. Gross-based is available as an option.

**Status: approved and implemented 2026-09-07.** Module `hrms/hrms/alvoraa_late_rules` ("Alvoraa Late Rules"): doctypes Attendance Deduction Rule (with child tables for leave types and exempt grades) and Attendance Deduction (submittable, with violation and leave rows); `late_rules.py` runs one week for one rule (Monday 02:00 scheduler for the previous week, plus an HR catch-up `run_for_range`), guarded by a file lock per rule and week; report **Late Coming Deductions**; permission query so an employee sees only their own deductions and a manager their team's; portal APIs `get_my_attendance_deductions` and `get_team_late_list` with a card on the attendance panel and one on the team panel; opt-in feature key `late_rules` in the subscription registry. Tests: `hrms/hrms/alvoraa_late_rules/tests/test_late_rules.py` (5 tests: week start, three violations from leave, four violations rounding up and spilling into pay with cancel reversing both, portal projection, exempt grade).

Two things changed against the proposal above:

1. **One core change in Frappe HR** (`hrms/hr/doctype/leave_application/leave_application.py`, `get_leaves_for_period`). The balance helper only counted Leave Application ledger entries, so a deduction posted by this rule did not lower the balance: PPJ-0058 was given a full day from Casual Leave when only half a day was left, and could still have applied for the leave. The helper now also counts ledger entries of type Attendance Deduction. It is one extra branch; Leave Application, the leave balance report and leave encashment all read balances through this helper, so they now agree. The existing leave application tests give the same result before and after the change (5 errors either way, all "No Holiday List was found" in the test fixtures, nothing to do with balances).
2. **The demo rule takes Casual Leave only**, not Casual then Earned. Earned Leave is the encashable one and the story for PPJ-0058 (half a day of leave, half a day of pay) needs it left alone. The rule still accepts more than one leave type in priority order.

Verified on the local demo site: 215 deductions for the punch data loaded there; PPJ-0054 week 17 Aug = 0.5 from Casual Leave; PPJ-0058 week 3 Aug = 0.5 from Casual Leave + 0.5 loss of pay, Additional Salary 548.39 (34,000 / 31 × 0.5) dated 2026-08-09. The punch generator was corrected at the same time (head office closed on Raksha Bandhan; the part-week before 1 July is not processed), so `expected_deductions.csv` now has 212 rows and the demo site is reloaded at the final verification (file 11).

---

## B0 — Hotfix found while testing: regional override wrapper breaks income-tax payslips

**Not a demo feature. A product bug that blocks payroll for any employee who owes income tax.**

`hrms/hrms/hr/utils.py` defines its own `allow_regional` decorator (added by commit d0469c8, 24 Aug 2026, "Stop our hrms fork replacing ERPNext's core doctypes"). It does `frappe.get_attr(overrides[fn_path])`, but `frappe.get_hooks("regional_overrides")` merges hook values into **lists**, so the call receives a list and fails with `'list' object has no attribute 'split'`. ERPNext's own decorator takes `overrides[function_path][-1]` for exactly this reason. The wrapper guards `calculate_tax_with_marginal_relief`, `calculate_annual_eligible_hra_exemption` and `calculate_hra_exemption_for_period`, all called from Salary Slip for Indian companies, so every payslip whose taxable income crosses the first slab crashes with "Salary Slip creation failed". Seen on the local bench with PPJ-0054 (annual taxable 4.29 lakh).

**Fix (three lines):** in the wrapper, if `overrides[fn_path]` is a list or tuple, use its last element before `frappe.get_attr`. Add a unit test that registers a regional override and calls a decorated function with the India country set.

**Impact:** payroll only; no data change; restores behaviour that ERPNext has. Performance, security, scalability neutral. Reliability: fixes a hard failure.

**Status: approved and implemented 2026-09-07.** Fix in `hrms/hrms/hr/utils.py`; regression test `hrms/hrms/tests/test_regional_override.py` (4 tests, list, last-wins, string, fallback).

## B2 — ESI components and fields

Spec: file 04 §3.

**Functional**: two Salary Components (ESI, Employer ESI), option `ESI` on `Salary Component.component_type`, custom fields `esi_number` (Employee), `esi_applicable` and `pf_applicable` (Salary Structure Assignment), report **ESI Deductions**. Formula and condition only; no controller code except the report. Personas: HR/payroll. Cross-module: payroll only.

**Non-functional**: Performance neutral (one more component per slip). Security neutral (report permission = Provident Fund Deductions report). Reliability: the `esi_applicable` switch avoids someone dropping out of ESI mid-period because of an incentive month, which is the classic bug in formula-only ESI. Scalability neutral. Maintainability: rates are in the component formula, editable by HR without code. Data integrity neutral. Compliance: ESI number is PII, shown only on the slip and the report, both already restricted.

**Risk**: statutory rates and ceilings come from memory, not a primary source. Decision 2026-09-07: applied as they stand for the demo; confirm before any real payroll.

**Status: approved and implemented 2026-09-07.** The India regional setup (`hrms/regional/india/setup.py`) now adds `esi_number` on Employee, a Statutory Deductions section with `pf_applicable` and `esi_applicable` on Salary Structure Assignment (both editable after submit), and the `ESI` / `Employer ESI` options on `component_type`. A before-insert hook (`hrms/regional/india/utils.py`, `set_esi_applicable`) switches ESI on for a new assignment whose base is at or below the ceiling constant `ESI_WAGE_CEILING` (21,000, applied for the demo by decision) and never clears a tick HR has set. New report **ESI Deductions** under Payroll. Patch `hrms.patches.v16_0.add_esi_fields_for_india` re-runs the regional setup on sites with Indian companies. Tests in `hrms/hrms/tests/test_esi.py`. The seeds now set the switches and the ESI numbers.

---

## B3 — Screening questions on the application form

Spec: file 06 §4 and §5.

**Functional**: nine custom fields `ppj_*` on Job Applicant (grouped in a "Screening" section, shown as read-only summary on the list view), one Web Form `ppj-senior-sales-application`. To make this reusable for the product rather than PP-specific, name the fields generically (`screening_q1_experience`, …) and put the question text in a small **Screening Question Set** doctype per Job Opening that the web form renders. For the demo, the simple custom-field version is enough; note the generic version as the product follow-up.

**Non-functional**: Performance neutral. Security: web form is public and unauthenticated by design (like the stock job-application form); add rate limiting via the existing Frappe web form throttling and keep the fields to the questions only, no free-text beyond availability and cover letter. Reliability neutral. Scalability neutral. Maintainability: custom fields carry a `module` so they export with the app. Data integrity neutral. Compliance: applicant PII already exists on Job Applicant; no new categories.

**Status: approved and implemented 2026-09-07**, in the generic form rather than the `ppj_*` one. Module `hrms/hrms/alvoraa_screening` ("Alvoraa Screening", its own Module Def):

- Custom fields (`setup.py`, patch `add_screening_fields`): a "Screening" section on Job Applicant with nine generic answer fields plus read-only `screening_result` (in the list view and filters) and `screening_notes`; a "Screening Rules" section on Job Opening (retail experience required, minimum years, product knowledge required, roster and festival availability required, maximum expected monthly CTC).
- `screening.py`: `evaluate` and a Job Applicant validate hook `screen` that applies the opening's rules when the applicant answered anything; a failed rule sets Screened Out, the reasons, and status Rejected on a new applicant. No rules on the opening means no verdict. Behind the `screening_forms` feature gate.
- Web Form `screening-application` ships with the app (neutral wording, `job_title` filled from the link's `?job_title=`); a client's own wording is a copy with different labels, which is what the seed does for PP Jewellers.
- Tests: `hrms/hrms/alvoraa_screening/tests/test_screening.py` (5 tests: rules read from the opening, evaluation, screened on insert, no rules or no answers, the shipped form).
- Seeds: rules on the PPJ opening, answers on the eight applicants (three screened out as the story says), the client-worded web form.

Not done: rate limiting beyond what Frappe applies to web forms; a per-opening question editor (the questions are fixed fields, the wording is per form).

---

## B4 — Employee Documents

Spec: file 07 §3.

**Functional**: two new doctypes (`Employee Document Type`, child `Employee Document`), one custom Table field on Employee, an `after_insert` hook on Employee (fill the checklist), a daily expiry job, portal card and HR compliance view. Personas: Employee uploads, HR/Store Admin verifies, managers read. Cross-module: onboarding (checklist shown on Employee Onboarding), Employee master (ERPNext doctype; the table is a custom field, so ERPNext upgrades are safe).

**Non-functional**

| Dimension | Effect |
|---|---|
| Performance | Neutral. One child table on Employee; the compliance view is one grouped query. |
| Security | Improves. Private files; verifier roles enforced in `validate`; the portal upload endpoint checks the row's `collect_from` and the user's own employee. |
| Reliability | Neutral. Hook is guarded so an Employee created outside onboarding still gets a checklist. |
| Scalability | Neutral. |
| Maintainability | Improves: replaces ad-hoc attachments with a typed checklist. |
| Data integrity | Neutral. Status transitions validated (cannot go to Verified without an attachment). |
| Compliance / privacy | Improves. Document numbers stored as last-4 only; expiry tracking for police certificates; read access follows Employee. |

**Risk**: existing employees have no rows. Provide a one-off "Create checklists for all employees" action on Employee Document Type.

**Also in scope (found while testing)**: `employee_boarding_controller.on_submit` sets the onboarding Project's expected start date to the joining date, so any pre-joining task is refused by ERPNext's Task date check. Use `boarding_begins_on` instead. One line, covered by a test that submits an onboarding with tasks before joining.

**Status: approved and implemented 2026-09-07.** Module `hrms/hrms/alvoraa_employee_documents` ("Alvoraa Employee Documents", its own Module Def so the console tick gates it cleanly):

- Doctypes: `Employee Document Type` (category, collected by, mandatory, expiry with reminder days, applies-to grades **and designations**, verifier roles, HR Manager writes, HR User and Employee read) with three small child tables, and the child `Employee Document` (type, status Pending / Received / Verified / Rejected / Expired, attachment, document number, dates, received and verified by, remarks).
- Custom fields (`setup.py`, patch `add_employee_document_fields`, fresh installs): a "Documents" tab on Employee with the table and a one-line summary; a read-only "Document Checklist" summary on Employee Onboarding.
- `employee_documents.py`: `fill_checklist` (Employee after_insert: one Pending row per type that applies to the grade or designation), `validate_documents` (attachment moves Pending to Received with who and when; Verified needs one of the type's verifier roles and stamps who and when; a passed expiry date sets Expired; the summary is rebuilt), `sync_onboarding_summary` (Employee on_update), `expire_documents` (daily 03:00: expiry and reminders by email to the employee and HR Managers), `attach_document` and `employees_missing_mandatory` for the portal. All of it is behind the feature gate `feature_enabled("employee_documents")` (`alvoraa_hr_core/features.py`, which reads the subscription registry and says yes on a bench without the portal app). The same gate now sits in front of the B6 hooks.
- Onboarding fix: `employee_boarding_controller.on_submit` starts the Project on `boarding_begins_on`, so pre-joining tasks no longer fail.
- Portal: `get_my_documents`, `attach_my_document` (private upload through Frappe's `upload_file`, then the row is set to Received; only rows collected from the employee) and `hr_document_compliance` (HR: active employees with a mandatory document not yet Verified, by branch). Page: a "My Documents" card on the home panel with Upload buttons, and a "Document Compliance" card with a branch filter on the Organisation Settings panel. Both hide unless the plan flag `plan_employee_documents` is on.
- Tests: `hrms/hrms/alvoraa_employee_documents/tests/test_employee_documents.py` (7 tests: scope by grade and designation, checklist on creation, attachment marks Received, verifier role enforced, expiry on save and by the job, portal attach and compliance, summary text).
- Seeds: 18 document types (block 1); every existing employee's rows are marked Verified as of joining, with PPJ-0200's police certificate Expired (block 2); Ritika's rows per file 07 §3.5 (block 6).

Not done: the "Employee Onboarding view" shows the counts, not the table itself (open the Employee record for the rows). Added 2026-09-07 (follow-up): expiry and reminder also raise a bell notification (Notification Log) for the employee and the HR Managers, next to the email.

---

## B5 — Policy Library

Spec: file 08.

**Functional**: three new doctypes, hooks only on them, a `permission_query_conditions` and `has_permission` pair, seven portal APIs, one home-page widget, one page. Personas: all. Cross-module: onboarding (activity auto-complete), Department (uses Department Head). No existing doctype changed.

**Non-functional**

| Dimension | Effect |
|---|---|
| Performance | Watch. The read rule expansion runs on every list query. Cache the viewer's "access profile" (roles, department, is-manager, is-leadership) per request; the SQL is a handful of `OR` clauses on an indexed child table. Home widget limited to 6 rows. |
| Security | Improves. Row-level scoping in the query, re-checked on open and on file download. Write is explicit. |
| Reliability | Neutral. Publishing is one transaction (bump version + snapshot + acknowledgement requests). |
| Scalability | Neutral. Multi-company via optional `company`. |
| Maintainability | Improves. One place for policies, versioned. |
| Data integrity | Improves. Readers see snapshots, so an edit-in-progress never leaks. |
| Compliance / privacy | Improves. Acknowledgement records give an audit trail (POSH, code of conduct). |

**Risk**: "Reporting Managers" is computed from `reports_to`; when a manager's last report leaves, they lose access. Acceptable and correct.

**Status: approved and implemented 2026-09-07.** Module `hrms/hrms/alvoraa_policy_library` ("Alvoraa Policy Library", its own Module Def):

- Doctypes: `Policy Document` (title, owner department, category, status Draft / Published / Archived, current version, dates, pinned, acknowledge flags, summary, attachment, content, read and write rule tables, version history; `POL-#####`), child `Policy Access Rule` (All Employees / Reporting Managers / HR Only / Department Only / Top Leadership / Role / User / Designation / Branch), child `Policy Document Version` (snapshot of summary, attachment and content with who, when and what changed), `Policy Acknowledgement` (policy, version, employee; one per version per employee; employees create their own, HR reads all).
- Custom field `department_head` on Department (`setup.py`, patch `add_policy_library_fields`): department heads are the "top leadership" of the rules and can write their own department's policies.
- `access.py`: one access profile per user per request (roles, employee, department, designation, branch, is-manager, department headships), the rules in Python (`can_read`, `can_write`, `has_permission`) and the same rules as SQL for the list (`permission_query_conditions`), so the list and the form never disagree. No `ignore_permissions` in the read path; the portal reads through `frappe.get_list`.
- Controller: `publish(change_note)` bumps the version and snapshots; validate flags unpublished changes on a published policy; readers get `published_view()`, the last snapshot. Publishing from the desk without a snapshot creates version 1.
- Onboarding link: an acknowledgement closes the onboarding task whose activity name contains "policy" once every joining policy is acknowledged.
- Portal (`hr_api.py`): `get_my_policies`, `list_policies` (search across title, summary and content; department and category filters), `get_policy`, `acknowledge_policy`, `save_policy` (with the "who can read" presets), `publish_policy`, `get_policy_compliance` (HR: pending by branch and by policy, review dates due). Page: a Policies widget on the home panel (pinned first, six cards, "Acknowledge" where pending), a Policies panel with search, filters, the reading view with version history, a Manage tab for writers (edit the working copy, choose who can read, publish with a change note, acknowledgement counts) and an HR compliance card.
- Tests: `hrms/hrms/alvoraa_policy_library/tests/test_policy_library.py` (7 tests: profiles, who sees what in the list, department-only follows the owner department, the form agrees with the list, who may write, publish snapshots while readers keep the old text, acknowledgement once per version).
- Seeds: block 7 `seed_policies.py`: department heads, 16 policies published with real text for the five demo ones, acknowledgements for everyone who joined before August, the Old Gold policy with unpublished changes.

Not done: rate limiting of the search (Frappe's own request limits apply). Added 2026-09-07 (follow-up): publishing a new version of a policy that must be acknowledged again sends every reader a bell notification and an email from a background job (`notify_new_version`, readers worked out with the same rules as the list).

---

## B6 — Attendance score in the appraisal, configurable from the portal

Spec: file 09 §8.

**Functional**

- Custom fields on Appraisal Cycle (weights and attendance parameters) and Appraisal (read-only score fields).
- Hook on `Appraisal.before_save` / `before_submit` in `alvoraa_hr_core`. Frappe HR's `calculate_final_score` is untouched; it already evaluates any formula against Appraisal fields.
- `performance_api.hr_create_cycle` and `save_cycle_wizard` change: they stop writing `final_score_formula = "goal_score"` and call the cycle's formula builder. Callers: the portal wizard only (grep confirms). `demo/setup_performance.py` writes its own formula and is unaffected.
- `grace_group/hooks/appraisal_metrics.py` keeps its route-log part; its attendance part delegates to the new function. Its hook registration stays.
- Personas: HR sets weights; managers and employees see the breakdown; CXO sees averages by store.
- Domains: appraisals read attendance, leave ledger and B1 deductions.

**Non-functional**

| Dimension | Effect |
|---|---|
| Performance | Watch. `before_save` on Appraisal runs three aggregate queries. Fine for one save; for `hr_generate_appraisals` on 400 employees, compute in one batched pass (one query per doctype for all employees in the cycle) and pass the results in, so generation stays at three queries, not 1,200. |
| Security | Neutral. Score fields are read-only; the hook runs in the saving user's context; reads are of records the appraisal's manager may already see. |
| Reliability | Improves. Exempt grades and employees with no attendance in the window get a defined result (5.0 with a note, or "no data" and weight redistributed, per a cycle setting). |
| Scalability | Neutral. |
| Maintainability | Improves. Removes the "Delivery Executive" hard-coding and the KRA-title matching. Unit tests for the formula with fixed attendance fixtures. |
| Data integrity | Watch. The score is snapshotted on the Appraisal at save/submit; attendance corrections after submit do not change a submitted appraisal (correct; that is what submit means). Before submit, re-saving recomputes. |
| Compliance / privacy | Neutral. |

**Also in scope (found while testing)**: `alvoraa_goals/controllers/cascade.py` `run_alignment_check` sums every goal on the cascade, so a multi-level cascade always reads Misaligned. Filter to goals with no `parent_goal`. Two lines plus a test with a two-level tree. **Done 2026-09-07** (`test_cascade_alignment_counts_only_top_level_goals`).

**Risk**: the formula is a `Code` field evaluated by `frappe.safe_eval`. The builder writes it; HR can still edit it by hand in desk. Validate on cycle save that the formula parses and references only known names.

**Status: approved and implemented 2026-09-07.** Module `hrms/hrms/alvoraa_hr_core` ("Alvoraa HR Core"):

- `setup.py` adds the custom fields: on Appraisal Cycle a section "Attendance in the Score" (include switch, the three weights, reliability and punctuality shares, penalty per deducted day, count paid leave as absent, what to do when there is no data, exempt grades as a Table MultiSelect of the new child `Appraisal Cycle Exempt Grade`); on Appraisal a collapsible "Attendance" section with the read-only score, reliability, punctuality, days deducted and a plain-words summary. Installed by patch `add_attendance_score_fields` and on fresh installs.
- `attendance_score.py`: `apply_cycle_settings` (Appraisal Cycle validate: the three weights must total 100; writes `final_score_formula` from them), `build_formula`, `numbers_for_many` (one query each on Employee, Attendance, Attendance Deduction and Leave Type for any number of employees, holidays cached per holiday list), `score_for`, `compute` (Appraisal before_save and before_submit: snapshot the numbers, then redo `calculate_final_score` so the formula sees them), `precompute` (fills a per-request cache so generating 400 appraisals costs four queries, not 1,200) and `cycle_scoring` for the portal.
- The Grace Group hook keeps its route-log logic and now gets its attendance figures from `attendance_numbers`. Its registration is unchanged; the new hook runs after it.
- Portal (`performance_api.py`): `hr_create_cycle` and `save_cycle_wizard` no longer hard-code `goal_score`; they call the builder. `save_cycle_wizard` takes a `scoring` argument, applied only when the tenant has `attendance_scoring`. `get_cycle_config` and the appraisal payload return the scoring settings and the attendance fields; `hr_cycle_summary` adds the attendance score per row and an average per branch; `get_wizard_filter_options` returns the grades. Page: a "How the Score Is Built" step in the Appraisal Setup panel (shown when the plan flag is on) with three sliders, a live total and formula preview, and an advanced fold; a "Score breakdown" card on the appraisal page for employees and managers; an Attendance column and a by-branch card on the HR cycle board.
- Tests: `hrms/hrms/alvoraa_hr_core/tests/test_attendance_score.py` (10 tests: formula from weights, weights must total 100, formula without attendance, the numbers, paid leave switch, score and penalty, snapshot on the appraisal and the final score using it, exempt grade, no-data rule, precompute cache). Stock `test_appraisal` and `test_appraisal_cycle` still pass with the hooks in place.

Added 2026-09-07 (follow-up): a hand-edited formula is tried once with sample numbers when the cycle is saved, so a typo is caught there and not on the first appraisal (`check_formula`, test `test_a_broken_hand_edited_formula_is_caught_on_save`).

---

## Approval

Reply "approve B1" (or any subset) to start implementation of that build. Each will come back with tests run, the architect review, and the before/after NFR check before any deploy step.
