---
slice: 010-portal-security-fixes
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-09-14
status: groups A, B and C built and tested locally; group D on hold
inputs: [00-impact-analysis.md (approved 2026-09-14 with decisions 1-12), 01c-security-privacy-requirements.md]
---

# 010 — Portal security fixes (Wave 0a): implementation notes, groups A–C

## The short answer

**Groups A, B and C are built, committed on `slice/010-portal-security-fixes`, and
tested on the local bench. Nothing is pushed.** Group D (review visibility: S1, S3, S4,
the reviewer picker and the invited-reviewer company rule) is not touched.

- **50 new pin tests**, all passing, in `alvoraa_portal/tests/test_portal_security_010.py`.
- **Full suites after every group:** the only failures are the ones that were already
  there — 11 in `test_invoicing`, 3 in `test_leave_year`. `alvoraa_goals` passes.
- **Four things need you** (section 9): tenant steps for PP Jewellers, `bench migrate` on
  deploy, two findings I fixed that were not on the list, and 011's commits now sitting
  under mine in local `dev`.

---

## 1. Commits

On `slice/010-portal-security-fixes`, oldest first. Hashes are after the last rebase.

| Group | Commit | What |
|---|---|---|
| — | `21614fa` | The two approved input documents (00, 01c) |
| A | `1234fc7` | Nobody can approve their own request, in the portal or the desk (S7) |
| A | `01d72e2` | HR acts only for employees of the companies they look after (S10 + leave summary leak) |
| A | `d2b1e91` | Managers see a report's loss-of-pay days, never the amount (S5) |
| A | `48889e2` | Stop pushing a script to the browser after review emails (S9) |
| A | `19f3c2f` | Tests: prove our refusal, not a side effect |
| A | `7a69653` | Tests: a second company must not become everyone's company |
| B | `76255ba` | People search finds only your own line; org views obey the reach rule (S6) |
| — | `881e37f`, `fa9b358` | **Not mine.** Slice 011, brought in by rebasing on local `dev` |
| C | `e9a327a` | Goal evidence waits for approval, and evidence files are private (S2 + approval list) |
| C | `09f3530` | Escape what people typed in the goal drawer; stop logging evidence values (S8, extras) |
| C | `5868c47` | Evidence-file patch: move a link shared by several tables once, fix every row (bug found by its own test) |
| — | this file | Implementation notes |

---

## 2. What was built, file by file

Mechanism key: **configure** (settings, JSON), **extend** (hooks, existing functions),
**build** (new code).

### Shared

| File | Mechanism | What and why |
|---|---|---|
| `hrms/hrms/alvoraa_hr_core/access.py` (new) | build | `refuse_own_decision`, `refuse_own_submit`, `is_own_record`, `permitted_companies`, `refuse`, `log_refusal`. One rule each, used from every app. In `hrms` because every app can import `hrms` and not the other way round. Every refusal writes one JSON line to `frappe.logger("security")`: time, user, endpoint, doctype, name, rule id — no field values |

### Group A

| File | Mechanism | What and why |
|---|---|---|
| `alvoraa_portal/hooks.py` | extend | `before_submit` on **Attendance Request** (added inside the existing entry) and **Leave Application** (new entry at the end) → `refuse_own_submit`. Covers desk, REST and import |
| `alvoraa_portal/attendance_correction.py` | extend | `decide` refuses your own request (approve and decline). `to_review` leaves your own requests out |
| `alvoraa_portal/performance_api.py` | extend | `approve_kpi_update` refuses your own KPI. `_send_notification` no longer publishes the script event, and logs a failure with the plain traceback only |
| `alvoraa_portal/goals_api.py` | extend | `approve_goal_update` refuses your own goal. `get_goal_update_log.can_action` is false on your own goal. `get_pending_approvals` leaves you out |
| `alvoraa_goals/controllers/evidence.py` | extend | `_assert_can_validate` and `can_validate_evidence` refuse your own goal |
| `alvoraa_portal/hr_api.py` | extend | `action_leave` refuses your own leave first (even as named approver, whatever HR Settings say); `_can_action_leave` agrees. `_hr_target_employee` scopes `apply_leave`, `preview_leave_request` and `get_leave_summary` to `permitted_companies()`, with one message for "elsewhere" and "does not exist". `get_all_active_employees` lists only permitted companies. `get_leave_summary` returns `{name, employee_name, company, department}` instead of the whole Employee. `get_team_late_list` reads a fixed field list with no amount or explanation. Also adds the missing `from frappe import _` (its absence turned `action_leave`'s refusal into a NameError) |
| `hrms/.../attendance_deduction.json` | configure | `lwp_amount` and `additional_salary` at permlevel 1; permlevel-1 read rows for HR Manager, HR User, System Manager. `modified` bumped so migrate picks it up |

### Group B

| File | Mechanism | What and why |
|---|---|---|
| `hrms/hrms/alvoraa_org_structure/api.py` | extend | `search_people` scoped by `_search_scope()` (decision 1): no reports → self; manager → own nested-set subtree in one query; HR and System Manager → `permitted_companies()`; no Employee → nobody. Limit capped at 50. `my_view(employee)`, `chain_to_top(node)` and `get_children(parent)` apply `_within_reach`; `get_children` with no parent needs full reach. `_within_reach` returns False for a login with no Employee record, and for an employee with no seat on a positions tenant. All refusals go through `_refuse_outside_reach` (same message as before, now logged) |
| `alvoraa_portal/www/hrms-employee.html` | extend | Search empty text: "Nobody by that name among the people you can see" |

### Group C

| File | Mechanism | What and why |
|---|---|---|
| `alvoraa_goals/api/goal_api.py` | extend | `submit_goal_evidence` saves **Pending**, no progress change, returns `evidence_row`, runs the file through `claim_evidence_file`. `get_employee_goals` requires HR or someone above the employee (`_may_see_goals_of`) |
| `alvoraa_goals/controllers/evidence.py` | extend + build | Debug `log_error`/`msgprint` blocks removed. `validate_evidence` keeps Invoice/Sales Order rules as a note, always Pending. `can_validate_evidence` asks for **read** on the goal (see 9.3). `approve_evidence` / `reject_evidence` take `evidence_row` (row name), refuse unknown or already-decided rows, write the row with `db.set_value`. New `claim_evidence_file(file_url, doctype, name, endpoint)` |
| `alvoraa_goals/controllers/goal.py` | extend | `recalculate_progress` saves with `flags.ignore_permissions` (see 9.3) |
| `alvoraa_goals/patches/v1_0/make_evidence_files_private.py` + `patches.txt` (one line at the end) | build | PRIV-7 patch. Groups rows from all three tables by link first (Frappe re-uses one file on disk for identical uploads, so tables can share a link), moves each file once, repoints every row, commits per link, safe to run twice |
| `alvoraa_goals/.../individual_goal.js` | extend | Desk message: "Evidence sent for approval." |
| `alvoraa_portal/goals_api.py`, `performance_api.py` | extend | `submit_goal_update`, `log_kpi_progress` run the file through `claim_evidence_file` |
| `alvoraa_portal/hr_api.py` | extend + build | `get_pending_approvals` rebuilt (it imported a function that does not exist): pending evidence this user may decide, 3 bounded queries. `approve_goal_evidence` / `reject_goal_evidence` take `evidence_row`. New read-only `get_self_approved_evidence` for HR (M2) |
| `alvoraa_portal/www/hrms-employee.html` | extend | All four evidence uploads `is_private=1`. Both toasts: "Evidence sent to your manager for approval". Progress approvals card decides by row name. The "auto-approve evidence" switch, its load and its save removed. Goal drawer: `esc()` on goal name, employee name, trajectory label, unit, cascade name, evidence type, status, validation notes, the employee's note, comments; new `_safeFileUrl` draws only `/private/files/` links, with `rel="noopener"`. Team goal card, the second goal panel's unit, and the manager scorecard's goal name also escaped |
| `alvoraa_portal/tests/test_portal_security_010.py` (new) | build | All pin tests (section 3) |

---

## 3. Requirements covered by this run → test → result

All tests are in `alvoraa_portal.tests.test_portal_security_010`. Result is the last run
on `test_site` (section 6).

| Req | What | Test(s) | Result |
|---|---|---|---|
| SEC-9 | Nobody decides their own request | `TestSec9NobodyDecidesTheirOwnRequest`: `test_sec9_decide_refuses_own_attendance_correction`, `test_sec9_to_review_leaves_out_own_requests`, `test_sec9_desk_submit_of_own_attendance_request_is_refused`, `test_sec9_desk_submit_of_own_leave_is_refused_even_when_hr_settings_allow_it`, `test_sec9_action_leave_refuses_own_even_as_named_approver`, `test_sec9_approve_kpi_update_refuses_own`, `test_sec9_approve_goal_update_refuses_own_and_the_flag_agrees`, `test_sec9_evidence_approve_and_reject_refuse_own` | pass |
| SEC-17 | Refusals logged without values | `test_sec17_a_refusal_is_logged_without_field_values` | pass |
| SEC-13 | HR acts only for permitted companies | `TestSec13HrActsOnlyForTheirCompanies` (7 tests) | pass |
| PRIV-6 | Leave summary returns only screen fields | `test_priv6_leave_summary_returns_only_the_fields_the_screen_uses` | pass |
| PRIV-3 | Manager never receives the amount | `test_priv3_manager_late_list_has_days_but_no_amount_or_explanation`, `test_priv3_employee_still_sees_their_own_amount`, `test_priv3_deduction_email_names_leave_type_and_days_but_no_amount` (decision 9) | pass |
| PRIV-4 | Amount restricted on the doctype | `test_priv4_amount_fields_are_hr_only_in_the_shipped_doctype`, `test_priv4_manager_desk_read_does_not_return_the_amount` | pass (the second needs a migrated site; it skips otherwise) |
| SEC-12 | No script push | `test_sec12_no_script_push_event_in_our_apps`, `test_sec12_notification_sends_email_only_and_logs_failure_without_names` | pass |
| SEC-16 | `ignore_permissions` does not grow | `test_sec16_ignore_permissions_does_not_grow` | pass |
| PRIV-5 | Search scope | `TestPriv5PeopleSearchScope` (5 tests) | pass |
| SEC-8 | Org chart obeys reach | `TestSec8OrgChartObeysReach` (5 tests) | pass |
| SEC-3 | Evidence Pending; approve by row name | `test_sec3_new_evidence_is_pending_and_progress_does_not_move`, `test_sec3_manager_approves_by_row_name_and_only_then_progress_moves`, `test_sec3_a_colleague_outside_the_line_cannot_decide` | pass |
| Decision 5 | Approval list; HR read-only list | `test_decision5_approval_list_shows_what_this_user_may_decide`, `test_decision5_hr_can_list_old_self_approved_evidence_read_only` | pass |
| SEC-4 | Private, own, attached files | `TestSec4EvidenceFilesArePrivate` (4 tests, incl. static page check) | pass |
| PRIV-7 | Patch makes old files private | `test_priv7_patch_moves_public_evidence_files_and_is_safe_to_run_twice` | pass |
| SEC-11 | Drawer escaping, safe links | `TestSec11GoalDrawerEscapesWhatPeopleTyped` (3 static tests) | pass |
| PRIV-8 | No debug logging of evidence | `test_priv8_no_debug_logging_of_evidence_values`, plus the Error Log count in the first SEC-3 test | pass |
| SEC-14 | `get_employee_goals` checks the person | `test_sec14_get_employee_goals_checks_the_person_not_the_doctype` | pass |
| SEC-15 | Named tests in CI | This module lives in `alvoraa_portal`, which CI runs | in place; revert proof not done (9.6) |

**Where 01c and 00 differed, and what I followed:**

- **SEC-4:** 00 proposed making a public upload private on the server. 01c says refuse
  anything that is not already a private file of the caller. I followed 01c.
- **SEC-11:** 00 allowed `/files/` and `/private/files/` links. 01c allows only
  `/private/files/`. I followed 01c.
- **SEC-12:** 01c asked to log the recipient and subject on a failed email. Your brief
  said "without names", and a subject can hold a name. I log the traceback only.
- **SEC-13:** 01c suggested `frappe.has_permission("Employee")`. 00 and decision 7 chose
  `permitted_companies()` (own company when there is no Company permission). I followed
  the decision.
- **SEC-3:** 01c says every new row is Pending. The Invoice and Sales Order validators
  used to auto-approve; they now only add a note.
- **PRIV-4:** 01c lists Payroll User. Payroll User has no read on Attendance Deduction at
  all, so a level-1 row would grant nothing. Not added.

---

## 4. Non-functional dimensions, re-checked against the code written

| Dimension | Before → after | Verdict | Why |
|---|---|---|---|
| Performance | — | **improves** (slightly) | Manager late list: one query instead of 1 + up to 50. Search: one bounded nested-set or company query, limit ≤ 50. Approval list: 3 queries whatever the headcount (was an ImportError). Added costs: one `Employee.user_id` lookup per decision; one File lookup per evidence upload |
| Security | — | **improves** | Self-approval closed on 6 paths plus desk submit; cross-company HR actions closed; amount out of manager payload and desk; directory scoped; reach enforced on 3 more endpoints; files private and owner-checked; drawer XSS sinks escaped; script push removed; `get_employee_goals` scoped. `ignore_permissions`: unchanged in every file except `controllers/goal.py` (+1, section 9.3) |
| Reliability | — | **improves** | Email failures now logged, not swallowed. Evidence approval works for managers (was broken). `get_pending_approvals` works (was an ImportError). The patch commits one file at a time and logs failures by name. Risk: a `before_submit` hook is skipped if code sets `flags.ignore_validate` on submit (Frappe behaviour) |
| Scalability | — | **improves** | Search and pickers bounded by line or company. Approval list reads at most 500 pending rows tenant-wide before filtering (9.4) |
| Maintainability | — | **improves** | Two shared rules in one module replace scattered checks. One refusal helper per org-chart endpoint. Evidence decisions by row name. Cost: `hrms.alvoraa_hr_core.access` is now imported from three apps |
| Data integrity | — | **improves** | Progress moves only on approval. Files attached to their record. Row-name approval cannot hit the wrong row. The patch rewrites every row sharing a link in the same commit |
| Compliance / privacy | — | **improves** | Pay amounts stay with the employee and HR; full Employee record no longer returned; evidence values out of the Error Log; refusals logged with names of documents only |

**Query counts on the heaviest calls (read from the code, not measured):**

- `get_team_late_list`: 1 team query + 1 rule lookup + 1 projection per report (unchanged) + **1** deduction query (was 1 + one per row, up to 50).
- `search_people`: roles (cached) + 1 Employee `lft/rgt` read (or 1–2 for HR) + **1** search query.
- `hr_api.get_pending_approvals`: roles + 1 own Employee + (HR: 1–2 company reads) + **3** queries.
- Response times were not measured.

**Indexes:** none added. `Employee.lft/rgt` are indexed by `NestedSet`. `File.file_url` is indexed by Frappe.

**Sensitive fields touched:** `lwp_amount`, `additional_salary` (restricted); `Employee` record fields (no longer returned by the leave summary); evidence files (made private).

---

## 5. What came in from others while I worked

- **Start of work:** `git fetch origin` — nothing incoming; worktree and `dev` at `4e3ba28`.
- **During group B→C:** slice 011 fast-forwarded local `dev` to `fa9b358` with two
  commits: `881e37f` (branch field on HR records, `hooks.py` `after_migrate` and
  `after_install` lines, `patches.txt` in `alvoraa_portal`, `attendance_analytics.py`,
  `branch_scope.py`, a patch and a test) and `fa9b358` (System Manager keeps the
  organisation attendance view, citing this slice's decision 1). I read both diffs.
  No file overlaps group C. `hooks.py` is shared but different blocks (their
  `after_migrate` / `after_install` lines, my `doc_events` lines, which were already in
  `dev`). Rebase of group C was clean.
- **Their commits are now under mine in local `dev` and on my branch.** 011's board row
  says they are not approved for push. They must not go out with 010 unless you say so.
- **Other sessions' uncommitted files in the main checkout**, not touched: `CLAUDE.md`,
  `.claude/agents/*`, `.claude/context/frappe-conventions.md`,
  `backlog/KPI_AUTOMATION_BACKLOG.md`, deleted `OBJECTIVES_KPI_REQUIREMENTS.md`,
  `hrms/hrms/alvoraa_org_structure/doctype/alvoraa_position/alvoraa_position.py` (same
  module as my `api.py`, different file — the bench tested with it present), and several
  untracked files.
- **In my worktree**, `docs/slices/010-portal-security-fixes/00b-review-copies-analysis.md`
  appeared, written by another session (the group D analysis). Not touched, not committed.
- No merge conflicts.

---

## 6. Commands run and real results

All on `hrlocal-bench`, site `test_site`, one run at a time (checked with `pgrep` before
each; the work board marked while running).

| When | Command | Result |
|---|---|---|
| Before any change | `run-tests --app alvoraa_portal` at `4e3ba28` | Output kept only as a tail: second category 236 tests, 11 failures (all `test_invoicing`). The first category's summary was cut off |
| Before any change | `run-tests --app alvoraa_goals` | 18 tests, OK (2 skipped) |
| Group A, run 1 | `--module ...test_portal_security_010` | 24 tests: 3 failures, 1 error — all test-setup faults (auto User Permissions, docstring hit, company ordering). Fixed in `19f3c2f`, `7a69653` |
| Group A | `bench --site test_site migrate` | Done. **Needed** so the permlevel change reaches `test_site`'s DocField table for the PRIV-4 desk test. Also ran other pending migrations on `test_site` |
| Group A, final | `--module ...test_portal_security_010` | 24 tests, OK |
| Group A | full `--app alvoraa_portal` | 485 tests: 3 errors (`test_leave_year`, known); 260 tests: 1 failure + 10 errors (`test_invoicing`, known) |
| Group A | full `--app alvoraa_goals` | 18 tests, OK (2 skipped) |
| Group B | `--module ...test_portal_security_010` | 34 tests, OK |
| Group B | `--app hrms --module hrms.alvoraa_org_structure.tests.test_reach` | 13 tests, OK |
| Group B | `--app hrms --module hrms.alvoraa_org_structure.tests.test_org_structure` | 33 tests, OK |
| Group B | full `--app alvoraa_portal` | 485: 3 errors (`test_leave_year`); 270: 1 failure + 10 errors (`test_invoicing`). Same as known |
| Group B | full `--app alvoraa_goals` | 18 tests, OK (2 skipped) |
| Group C | read-only dry-run count on `test_site` (query in section 7) | 0 / 0 / 0 |
| Group C | `bench --site test_site migrate` | Ran `alvoraa_goals.patches.v1_0.make_evidence_files_private`: "0 links made private, 0 failed, 0 rows with no File record". **It also ran slice 011's pending patch `fill_branch_on_hr_records` on `test_site`**, because 011's commits were already in local `dev` |
| Group C, run 1 | `--module ...test_portal_security_010` | 50 tests: 1 failure, 2 errors. The failure was **a real bug in the patch** (rows sharing a link across tables were left public); fixed in `5868c47`. The 2 errors were the Goals plan gate, which `test_site` does not have; the tests now switch it on |
| Group C, final | `--module ...test_portal_security_010` | 50 tests, OK |
| Group C | full `--app alvoraa_portal` (re-run 2026-09-15 after the build agent was cut off, dev at `5868c47`) | 489 tests: 3 errors (`test_leave_year`, known); 292 tests: 1 failure + 10 errors (`test_invoicing`, known). Nothing new |
| Group C | full `--app alvoraa_goals` | 18 tests, OK (2 skipped) |

**Pushed to dev on the user's word (2026-09-15) as 010 alone.** The two slice-011 commits
were left out. The 010 commits were cherry-picked onto `origin/dev` (`4e3ba28`) in a
separate worktree, so their hashes on `dev` differ from the ones in section 1. The pushed
tree differs from the tested tree only by 011's six files; nothing in 010 references them.
Dry run of the evidence-file patch on the dev tenants before the push: dev.alvoraa.co 2 /
0 / 0; ppj.dev, allabouthr.dev and test_site 0 / 0 / 0.
| Any | `node scripts/check_portal_handlers.js` and `check_undefined_js.js` on the changed page | "all reachable and callable", "undefined identifiers: none" — same as on `4e3ba28` |

**Dry run for the evidence-file patch on `test_site`** (read-only, before migrate):
Goal Evidence 0, Goal Progress Update 0, KPI Progress Log 0. Nothing to move on `test_site`; the patch test builds its own public files.

---

## 7. Tenant steps for you (not done by me)

**PP Jewellers (`ppj.localhost`), decision 8 — HR sees loss-of-pay amounts in the desk.**
ppj has a Custom DocPerm on Attendance Deduction that leaves only System Manager, so the
shipped JSON rules do not apply there. After deploying and migrating, on your word:

1. Desk → **Role Permissions Manager** → Document Type **Attendance Deduction**.
2. If HR should open these records at all: add **HR Manager, Level 0**, tick *Read*
   (and *Report*, *Print* if wanted). Same for **HR User** if wanted.
3. Add **HR Manager, Level 1**, tick *Read*. Same for **HR User, Level 1**.
4. Do **not** add any Level 1 row for Employee.
5. Check as a manager (for example Sakshi): the amount must not show in the form, list,
   print or `/api/resource/Attendance Deduction/<name>`.

**Every tenant on deploy:** `bench migrate` is needed for the Attendance Deduction
permission levels and the evidence-file patch. Run the dry-run query in
`make_evidence_files_private.py` on each tenant first. ppj's count was 0/0/0 on
2026-09-14 (from 00).

---

## 8. Known gaps and shortcuts — honestly

1. **An employee cannot submit evidence on a goal HR created.** `submit_goal_evidence`
   saves the goal as the employee, and only the creator has write
   (`alvoraa_goals.permissions`). This was already so; I did not change it. Tests use a
   goal the employee created.
2. **`submit_goal_update` still moves progress before approval** (F-14). Out of scope by decision 10.
3. **The desk "Submit Evidence" dialog** uses Frappe's Attach field. If the user uploads
   a public file there, the server now refuses it with "Attach a file you uploaded
   yourself, as a private file." Not traced in a browser.
4. **HR approval scope differs slightly between list and action.** The approval list
   shows HR only their permitted companies. `approve_evidence` itself still lets any HR
   Manager or HR User decide any company's evidence (the existing rule). Not widened, not narrowed.
5. **Approval list reads up to 500 pending evidence rows** tenant-wide before filtering.
   On a tenant with more pending rows, the oldest 500 are considered.
6. **SEC-15 revert proof not done.** The bench runs the main checkout, so proving each
   test fails against the unfixed code would mean moving `dev` backwards. Several tests
   did fail on the first run for real reasons. The test engineer should do the revert
   check in `04-test-report.md`.
7. **The manager late list still shows this week's violation times** (`team[].detail`).
   The screen uses it; your decision was about the amount. Say if you want days only there too.
8. **Security log is a file on each bench** (`logs/security.log` via `frappe.logger`), not
   central. Same known gap as CERT-In log location.
9. **The existing test `test_write_permission_is_still_required_on_top`** in
   `test_evidence_and_updates.py` still passes (it looks for `has_permission`), but its
   name now says "write" while the rule asks for read. Left for the test engineer.
10. **UI flows were not traced in a browser.** Checked by reading the code and by the two
    portal JS scripts. Needs a hand trace: evidence upload (drawer, panel, progress log,
    KPI log), the Team panel's approvals card, the org chart search, the Org Settings page
    without the switch.
11. **`get_goal_detail`'s evidence query still asks for columns that no longer exist**, so
    the drawer shows no evidence. Not fixed (not asked). The drawer is now escaped, so
    fixing it later is safe.
12. **`before_submit` hooks are skipped when code sets `flags.ignore_validate`** on submit.
    No code in our apps does that for these doctypes today.

---

## 9. Needs your decision or attention

1. **Pushing:** local `dev` holds 011's `881e37f` and `fa9b358` under my commits. A push of
   `dev` would send them too.
2. **Tenant steps** in section 7, and `bench migrate` on deploy.
3. **Two changes beyond the letter of the list, both needed for decision 5 to work:**
   - `can_validate_evidence` now asks for **read** on the goal, not write. With write,
     no manager who had not created the goal could approve anything.
   - `recalculate_progress` saves with `ignore_permissions`, for the same reason. This is
     the one place `ignore_permissions` grew (`controllers/goal.py` 2 → 3, pinned by SEC-16).
4. **Extras fixed in the same class:** the manager scorecard's goal name was unescaped
   (`renderScorecard`); `hr_api.py` was missing `from frappe import _`. Both small.
5. **Approval limit** (8.5) and **late-list times** (8.7) — say if either matters.

---

## 10. Left for group D (on hold)

- **S1 / SEC-1** — self-review writes only the subject's own KPIs, through `doc.save`; stops writing goal progress (decision 4).
- **SEC-2** — KPI manager-rating fields writable only by the manager line or HR, in `validate_kpi`.
- **S3 / SEC-5, PRIV-1** — remove the Employee DocPerm from Alvoraa Appraisal Extension; overall rating visible from "Employee Final Review" (decision 3); potential rating never.
- **S4 / SEC-6, PRIV-2** — no self-review before it is sent; HR guard on manager-review reads and writes; no extension created before the check.
- **SEC-7** — invited reviewer sees only allowed pages; invitees from the subject's company only.
- **SEC-10** — nobody rates their own review (the SEC-9 helper is ready to reuse).
- **Reviewer picker** (`performance_api.search_employees`) — own company, not limited to line (decision 2).
- **M3** — report tenants with a Custom DocPerm re-granting Employee on the extension.
- Plus whatever the "review copies" analysis (`00b`) changes.
