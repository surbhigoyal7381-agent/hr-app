---
slice: 010-portal-security-fixes
artifact: 03d-implementation-notes-group-d
author: hrms-fullstack-engineer
date: 2026-09-15
status: phase 1 (commits 1-3) built and tested locally; phases 2-4 not started
inputs: [00e-group-d-approved-decisions.md (wins), 00d-impact-analysis-group-d.md, 01d-security-privacy-group-d.md, 00c-review-copies-decisions.md, 03-implementation-notes.md]
---

# 010 group D — Review copies and review access: implementation notes

Later phases add their own section below. Nothing here is pushed.

---

# Phase 1 — commits 1, 2 and 3

## The short answer

**Phase 1 is built, committed on `slice/010-portal-security-fixes`, and tested on the
local bench. Nothing is pushed.**

- **34 new pin tests, all passing** (`alvoraa_portal/tests/test_review_copies_010d.py`).
- **Full suites:** only the failures that were already there (`test_leave_year` 3 errors; `test_invoicing` 1 failure + 10 errors). `alvoraa_goals`: 18 tests, OK. The first full run found a real bug of mine in the HR guard; fixed in `502443c` (section 6).
- **Integrity check:** "OK - all consistent" before every commit.
- **Two things you should know first:**
  1. **The review screens still show the live records.** Copies are taken and counted,
     but `get_my_review` and `get_manager_review` return the live Objectives and KPIs
     until commit 4 (phase 2). That is the plan's order.
  2. **Some people lose access today, on purpose.** HR and System Manager can no longer
     open a stranger's review before HR Review, in the portal or the desk. A manager
     cannot open a review before the self-review is sent. HR's appraisal table still
     shows an "Open Review" button in early stages; it now shows the refusal message.
     The page change is commit 11.

## 1. Commits

On `slice/010-portal-security-fixes`, oldest first. Brought into local `dev` with
`merge --ff-only` for testing.

| Commit | What |
|---|---|
| `d099aa7` | Commit 1: review items table, Extension fields, three settings, KPI indexes and history |
| `a49cfcd` | Commit 2: copies taken on first open, facts counted by date, stamps and flags; also fixes two commit-1 test checks |
| `4983314` | Commit 3: review-record access (SEC-5, SEC-6, SEC-10, SEC-27, PRIV-1, PRIV-2, decisions 15, 16, 22), draft-save bug, scorecards, M3 report |
| `4046707` | Test fix: compare HR Settings history with the stored value, not a cached copy |
| `c9c08e6` | Test fix: ask for the Version row Frappe skips while tests run |
| `502443c` | **Bug fix found by the full suite:** the HR guard no longer exempts the HR "stand-in" manager; the stand-in acts only in the manager review |
| this file | Implementation notes |

## 2. What came in from others

- **`origin/dev`:** fetched at the start and again before every merge and at the end.
  **Nothing came in.** It stayed at `c27fb56`.
- **Main checkout:** other sessions' uncommitted files, not touched: `CLAUDE.md`,
  `.claude/agents/*`, `.claude/context/frappe-conventions.md`,
  `.claude/context/ux-learnings.md`, `backlog/KPI_AUTOMATION_BACKLOG.md`, deleted
  `OBJECTIVES_KPI_REQUIREMENTS.md`, `hrms/.../alvoraa_position.py`, and untracked files.
  None is a file phase 1 changes.
- **One blocker on the way, cleared by someone else.** The first `merge --ff-only`
  refused: an untracked copy of `00c-review-copies-decisions.md` sat in the main
  checkout (identical to the committed one). I did not remove it; my attempt to move it
  aside was refused, and I stopped. The work board then said it had been removed, and
  the merge went through.
- **Docker Desktop was not running** at the start, so the bench was down for everyone.
  I started it and said so on the work board. Nothing else about the bench changed.
- No merge conflicts.

## 3. What was built, file by file

Mechanism key: **configure** (JSON, settings), **extend** (hooks, existing functions),
**build** (new code).

### Commit 1 — structure and settings

| File | Mechanism | What and why |
|---|---|---|
| `alvoraa_goals/.../doctype/alvoraa_review_item/` (new: json, py, `__init__`) | build | Child DocType, fields as 00d §2.2, plus `facts_dated_by_upload` (decision 5) and `manager_flag_answered_by/_on` (decision 12). `source_name` is **Data with an index, not a Link**, so a live record can still be deleted later. All fields read-only |
| `.../alvoraa_appraisal_extension.json` | configure | Table `review_items`; `items_taken_on`, `review_window_start/end`, `freeze_point`, `removal_mode` (the stamps SEC-21 asks for), `frozen`, `frozen_on`, `completed_on`, `overall_rating_basis` (hidden), `overall_rating_flag`, `overall_rated_by/on`, `overall_flag_answered_by/on` |
| `.../alvoraa_appraisal_extension.py` | extend | `before_validate` refuses any change to `review_items` unless the review code set a document flag. Runs even with `ignore_validate`. No role exempt. Logged as rule `R1` |
| `.../doctype/kpi/kpi.json` | configure | Index on `employee` and `appraisal_cycle` (slice 012 planned the same; 010 adds them), `track_changes: 1` |
| `alvoraa_goals/review_items.py` (new) | build | `review_settings()` (never throws; bad value → default; days below 0 → 0 = never), `validate_hr_settings`, `after_migrate()` installer (Tab "Performance Reviews" on HR Settings; seeds the three values only when none is stored) |
| `alvoraa_goals/hooks.py` | extend | `doc_events["HR Settings"].validate`; `after_migrate` and `after_install` (a CI site never migrates) |

### Commit 2 — copies, facts by date, stamps

| File | Mechanism | What and why |
|---|---|---|
| `alvoraa_goals/controllers/kpi.py` | extend | `attainment(actual, target, direction)` split out and shared by KPI and copies |
| `alvoraa_goals/review_items.py` | build | `open_review`, `ensure_review_items` (once per review; skips Completed and cancelled appraisals; copies cycle items that are not cancelled and not future plans, plus items another open review of the same employee holds whose period overlaps, R16; stamps period, freeze point, removal setting; sets `frozen` if the review is already past its freeze point), `refresh_review_items` (writes only when a number or flag changed), `_recount` (R3, R4, decision 1, decision 5), `is_past_freeze_point` (unknown → frozen), `stamp_rating`, `stamp_overall_rating`, `raise_rating_flags` (a rating with no stamp counts as flagged, SEC-23), `open_blocking_flags` (manager and overall only, decision 13), `save_review_record` (the one save with the flag) |
| `alvoraa_portal/performance_api.py` | extend | `get_my_review` and `get_manager_review` call `open_review` after their checks, so the first open takes the copies (decision 4) |

**How a copy counts (as built):**

| Copy of | Mode | Actual | Facts | Date |
|---|---|---|---|---|
| KPI | Cumulative | sum of approved readings in the window | KPI Progress Log | `log_date` |
| KPI | Absolute | latest approved reading (date, then approved on, then created) | same | `log_date` |
| Objective | Cumulative | sum of approved evidence | Goal Evidence | `extracted_date`, else upload date, else created (marked "dated by upload") |
| Objective | Absolute | latest approved goal update; with none, latest approved evidence | Goal Progress Update, Goal Evidence | `log_date` / as above |

The window is the review period narrowed by the copy's own period. No review period →
nothing counted (fail closed). A cancelled live record keeps its copy and counts its
facts; the copy is marked `source_cancelled` (decision 20).

### Commit 3 — review-record access

| File | Mechanism | What and why |
|---|---|---|
| `hrms/hrms/alvoraa_hr_core/access.py` | extend | `refuse_own_rating(employee, …)`, logged as rule `SEC-10`. No role exempt |
| `.../alvoraa_appraisal_extension.json` | configure | Employee DocPerm removed (SEC-5) |
| `hrms/hrms/hr/doctype/appraisal/appraisal.json` (our fork) | configure | Employee keeps read, loses write and create (decision 22) |
| `alvoraa_goals/permissions.py`, `hooks.py` | extend | `has_appraisal_extension_permission` and `appraisal_extension_query` (SEC-27). HR roles read a review in HR Review or Completed for a permitted company, or in their own line once the self-review is sent; **never their own**; no desk write below Administrator; anyone without an HR role is denied even if a tenant's Custom DocPerm re-grants them. Child rows follow |
| `alvoraa_portal/performance_api.py` | extend | See the table below |
| `alvoraa_portal/hr_api.py` | extend | Both scorecards show an overall rating and score only from Employee Final Review; the team scorecard takes the latest *released* review. No signature change |
| `alvoraa_goals/review_items.py` | build | `custom_docperm_report()` — read-only M3 report: non-HR Custom DocPerm rows on the Extension (any right), Appraisal (write/create/delete) and KPI (level 1+). Changes nothing |

`performance_api.py`, function by function:

| Function | Change |
|---|---|
| `_assert_hr_can_view` | System Manager no longer exempt (decision 15). HR acting for others: company must be in `permitted_companies()` (decision 16). No record yet = not in HR Review. Refusals logged |
| new `_is_line_manager` | Manager line, or, for an employee with no manager, the HR Manager the portal treats as their manager (`get_effective_manager`). Used only by the manager-review actions, advance from Manager Review, and return while in Manager Review, so that existing path keeps working without opening the review anywhere else |
| `_get_or_create_extension` | Fills `employee` and `appraisal_cycle` |
| new `_extension`, `_review_status` | Read without creating (SEC-6) |
| new `_manager_review_record` | Order: own review refused (SEC-10) → manager line or HR → HR stage/company rule → record exists and is in Manager Review → copies refreshed |
| new `_sent_rating`, `_set_manager_ratings` | A rating changes only when one is sent (0 or blank = leave it). Overall rating stamped when it changes |
| `get_appraisal_extension` | Subject: no potential keys at all; overall rating from Employee Final Review. Others: narrative blank before the self-review is sent. Only the subject's visit creates the record |
| `get_my_appraisals` | Overall rating only from Employee Final Review |
| `get_my_review` | Anyone but the subject refused before the self-review is sent (PRIV-2), including an HR person who is also the manager |
| `get_manager_review` | SEC-10, then relationship, then HR rule, then refused before the self-review is sent. Never creates the record |
| `save_manager_review`, `submit_manager_review` | Through `_manager_review_record`; **draft-save bug fixed** |
| `save_overall_rating` | Through `_manager_review_record` (direct manager, as before); Manager Review only; stamped |
| `save_calibration_note` | Own review refused; HR rule; HR Review only; never creates; stamped |
| `advance_review_status` | Stage read without creating; Manager Review and HR Review steps refuse the subject and apply the HR rule |
| `return_for_revision` | Subject refused; relationship and HR rule before the stage |
| `return_to_manager`, `acknowledge_final_review`, `get_employee_final_review` | Never create; final review no longer returns potential |
| `add_action_item`, `update_action_item_status` | HR rule; never create |
| `invite_reviewer`, `invite_reviewers_batch` | Through `_manager_review_record` |
| `get_reviewer_view`, `submit_reviewer_comments` | No record = no invitation; invitation checked before the stage |
| `get_team_reviews` | HR: active employees of permitted companies plus own reports. Own row: no potential, overall only when released. Others outside the line: ratings only from HR Review |
| `list_appraisals` | HR: permitted companies plus own line |
| `save_kpi_manager_review`, `suggest_ratings`, `sync_appraisal_from_kpis`, `submit_appraisal` | Own review refused (SEC-10) |

`ignore_permissions` in `performance_api.py`: still 88 (the ceiling). New file
`review_items.py`: 1, added to the ceiling test with its reason.

## 4. Requirements covered in phase 1 → test → result

All tests in `alvoraa_portal.tests.test_review_copies_010d`. Result is the last run on
`test_site` (34 tests, OK).

| Requirement | Test | Result |
|---|---|---|
| R1 structure | `test_r1_copies_live_in_a_child_table_on_the_extension` | pass |
| R1 no desk/REST edits of copies | `test_r1_a_desk_or_rest_change_to_review_items_is_refused` | pass |
| SEC-28 settings in one audited place, validated | `test_sec28_settings_are_installed_on_hr_settings_with_their_defaults`, `test_sec28_reader_falls_back_on_unusable_values_and_never_throws`, `test_sec28_bad_values_are_refused_and_only_hr_manager_may_change_them` | pass |
| KPI indexes, track changes | `test_kpi_is_indexed_by_employee_and_cycle_and_keeps_change_history` | pass |
| VIS-4, decision 4 (first open, once) | `test_vis4_copies_are_taken_once_when_the_review_is_first_opened` | pass |
| VIS-14, VIS-15 | `test_vis14_vis15_other_cycle_cancelled_and_future_items_get_no_copy` | pass |
| History not rebuilt | `test_no_copies_for_a_completed_review` | pass |
| SEC-21 stamps at open | `test_sec21_period_freeze_point_and_removal_setting_are_stamped_when_copies_are_taken` | pass |
| R6 freeze steps, fail closed | `test_r6_freeze_point_steps_and_unknown_values_fail_closed` | pass |
| R4 KPI modes | `test_r4_kpi_cumulative_sums_and_absolute_takes_the_latest_approved_reading` | pass |
| R3 window | `test_r3_facts_dated_outside_the_period_do_not_count` | pass |
| R3 until freeze | `test_r3_new_facts_reach_the_copy_until_it_freezes` | pass |
| R4 + decision 1 Objectives | `test_r4_objective_evidence_is_summed_and_goal_updates_count_as_readings` | pass |
| Decision 5 | `test_decision5_evidence_without_its_own_date_is_dated_by_upload_and_marked` | pass |
| R16 | `test_r16_overlapping_reviews_split_facts_by_date` | pass |
| R7 flags, decision 13 | `test_r7_a_changed_number_flags_every_rating_given_on_the_old_numbers` | pass |
| SEC-23 no stamp = flagged | `test_sec23_a_rating_with_no_stamp_counts_as_flagged` | pass |
| NFR: refresh cost does not grow | `test_query_count_refreshing_a_review_does_not_grow_with_its_items` | pass |
| SEC-5, VIS-2 (child rows) | `test_sec5_employee_and_manager_cannot_reach_the_review_record_through_the_desk_or_rest` | pass |
| M3 | `test_m3_report_lists_a_tenant_grant_to_employee_and_changes_nothing` | pass |
| Decision 22 | `test_decision22_employee_cannot_write_or_create_an_hrms_appraisal` | pass |
| SEC-27, decision 15 (desk) | `test_sec27_hr_desk_reads_follow_the_stage_and_company_rule_and_nobody_writes` | pass |
| PRIV-1, decision 3 | `test_priv1_subject_never_receives_potential_and_sees_the_overall_rating_from_final_review`, `test_priv1_team_reviews_hide_your_own_potential_and_strangers_ratings_before_hr_review` | pass |
| PRIV-2 (incl. after return) | `test_priv2_nobody_else_opens_a_self_review_before_it_is_sent_or_after_it_is_returned` | pass |
| SEC-6 (no record created) | `test_sec6_calls_from_people_who_may_not_act_create_no_review_record` (15 endpoints, stranger and HR) | pass |
| Draft-save bug | `test_manager_draft_save_keeps_the_ratings_already_given` | pass |
| SEC-10 | `test_sec10_an_hr_manager_cannot_rate_calibrate_or_close_their_own_review` (13 calls; another HR Manager then completes it) | pass |
| Decision 15 (portal) | `test_decision15_system_manager_follows_the_stage_rule` | pass |
| Decision 16 | `test_decision16_hr_acts_only_for_the_companies_they_look_after` | pass |
| HR stand-in manager: acts in Manager Review, not exempt from the HR guard | `test_the_hr_stand_in_for_a_manager_less_employee_reviews_in_manager_review_but_is_not_exempt_elsewhere` | pass |
| Scorecards (PRIV-1 release rule) | `test_scorecards_show_an_overall_rating_only_once_it_is_released` | pass |
| SEC-16 ceiling | `test_portal_security_010.TestSec16IgnorePermissionsCeiling` (review_items.py added at 1) | pass (full suite) |
| Existing guard tests still hold | `test_appraisal_visibility` (all 7, incl. the manager who is also HR) | pass (after `502443c`) |

**Where the documents differed, and what I followed:**

- **SEC-27 "or it is their own":** 01d lets HR open their own review in the desk. That
  record holds their potential rating, which PRIV-1 says they never see. I denied it
  (fail closed). Say if you want it the other way.
- **PRIV-2 in `get_manager_review`:** 00d proposed returning blank fields before the
  self-review is sent; 01d's test says refuse. I refused — nothing leaks either way, and
  the page only offers the button from Manager Review on.
- **Settings Version row:** 01d says HR Settings keeps a history. True, but Frappe skips
  Version rows while tests run; the test asks for one explicitly. Checked outside test
  mode on `test_site`: a settings save writes one.

## 5. Non-functional dimensions, re-checked on the code written

| Dimension | Before → after | Verdict | Why |
|---|---|---|---|
| Performance | — | **neutral** now, improves later | New: KPI indexes on `employee` and `appraisal_cycle` (every KPI query by person or cycle). Added: opening a review costs about 5 extra reads (refresh), or about 13 reads plus one insert per item on the first open. Readers still run their old queries until commit 4 removes the per-goal KPI query |
| Security | — | **improves** | SEC-5, SEC-6, SEC-10, SEC-27, PRIV-1, PRIV-2 closed on 25 endpoints and the desk/REST; System Manager and cross-company HR brought under the stage and company rule; HRMS Appraisal no longer writable by Employee; desk edits of copies refused. `ignore_permissions` unchanged in touched files; +1 in a new file |
| Reliability | — | **improves** | Draft save no longer wipes ratings. Unauthorised calls no longer leave empty review records. Copy refresh writes nothing when nothing changed. Risk: the first open of a review now does writes inside a read endpoint (it commits, like the existing record creation) |
| Scalability | — | **neutral** | Refresh is 5 queries whatever the item count (tested: 3 and 11 items, same count). Copies grow about 8 rows per review. HR's team list is now bounded by permitted companies |
| Maintainability | — | **degrades slightly** | A new module and a second place that holds item data. Contained: one module, one save path, one attainment formula, one manager-review check, 33 named tests |
| Data integrity | — | **improves** | Ratings now carry the numbers they were given on; copies cannot be edited around the review code; a review's settings are fixed when it opens |
| Compliance / privacy | — | **improves** | Potential never reaches the subject in the endpoints touched; drafts stay with the author; every refusal logged with document names only. No personal values in any new log line |

**Query counts (read from the code; the refresh count is also tested):**

- `refresh_review_items`: at most 5 reads — readings, evidence, goal updates, cancelled
  KPIs, cancelled Objectives. Same count for 3 and 11 items. One save only when changed.
- `ensure_review_items` (first open): Appraisal 1, cycle 0–1, settings 3 (cached per
  request), Objectives 1, KPIs 1, other open reviews 1, overlapping held items 0–2, then
  the 5 above, then one save (Extension update, one insert per copy, one Version row).
- `_assert_hr_can_view`: roles (cached), own Employee 1, owner 1, subtree walk, effective
  manager 1–2, company 1, permitted companies 1–2, status 1.
- Response times were not measured.

**Indexes added:** `tabKPI.employee`, `tabKPI.appraisal_cycle`,
`tabAlvoraa Review Item.source_name`.

**Sensitive fields touched:** potential rating and category (now withheld from the
subject), overall rating (release rule), self-review narrative (withheld before sent).

## 6. Commands run and real results

All on `hrlocal-bench`, site `test_site`, one run at a time (`pgrep` first; work board
marked).

| When | Command | Result |
|---|---|---|
| Before every commit | `python scripts/check_app_integrity.py` | "OK - all consistent" (519 checks) |
| After commit 1 | `bench --site test_site migrate` | Done; new DocType, fields, indexes, HR Settings fields (after_migrate) |
| After commit 1 | `--module …test_review_copies_010d` | 6 tests: 2 failures, both test faults (index name; Version check). Fixed in commit 2 |
| After commit 2 | same module | 20 tests: 1 error (a test shadowed `frappe` with a local import). Fixed in commit 3 |
| After commit 3 | `bench --site test_site migrate` | Done; permission changes on Extension and Appraisal |
| After commit 3 | same module | 33 tests: 1 failure (Version row, see section 4). Two test-only commits followed |
| Probe | fresh-connection script on `test_site`, rolled back | HR Settings save as Administrator and as the HR Manager test user: Version count 0 → 1 |
| After test fixes | same module | 33 tests, OK |
| Full suite, run 1 (at `c9c08e6`) | full `--app alvoraa_portal` | 489 tests: 3 errors (`test_leave_year`, known). 325 tests: 3 failures + 10 errors — `test_invoicing` 1 failure + 10 errors (known) and **2 new failures in `test_appraisal_visibility`** (`test_hr_still_cannot_read_a_stranger_mid_review`, `test_the_refusal_says_what_has_to_happen_first`). Cause: my stand-in exemption in the HR guard. Fixed in `502443c` |
| After the fix | `--module …test_appraisal_visibility`; `--module …test_review_copies_010d` | 7 tests, OK; 34 tests, OK |
| Full suite, run 2 (at `502443c`) | full `--app alvoraa_portal` | 489 tests: 3 errors (`test_leave_year`, known). 326 tests: 1 failure + 10 errors (`test_invoicing`, known). Nothing new |
| Final | full `--app alvoraa_goals` | 18 tests, OK (2 skipped) |

**Migrations run:** `bench --site test_site migrate`, twice (after commits 1 and 3).
Nothing else was migrated. `ppj.localhost` was not touched.

## 7. Tenant steps and deploy notes (not done by me)

- **Every tenant needs `bench migrate`:** new DocType, Extension and KPI JSON, HRMS
  Appraisal permission, HR Settings fields (installer). Adding the two KPI indexes locks
  `tabKPI` briefly.
- **Before any push to dev (decision 24):** run the read-only M3 report on each dev
  tenant, on your word:
  `bench --site <site> execute alvoraa_goals.review_items.custom_docperm_report`.
  Any row it lists keeps its grant, because a tenant's Custom DocPerm replaces our JSON.
  On `ppj.localhost` and `test_site` 01d found none.
- **Tenants with their own Appraisal Custom DocPerm** (ppj has one) are not affected by
  decision 22's JSON change; the report lists them if they grant Employee write.
- **Do not deploy phase 1 alone.** Group D ships as one batch (00d §15). On its own,
  phase 1 changes who may open reviews but the screens still show live records.

## 8. Known gaps and shortcuts — honestly

1. **Review readers still return live records** (commit 4). Copies exist and are counted
   but are not shown yet.
2. **Copies refresh only when a review is opened.** The hook on KPI and Objective saves is
   commit 7.
3. **Rating writers on copies, flag answers, the completion block, freezing on stage
   moves, write-back** are commits 5 and 6. `open_blocking_flags` exists but nothing uses it.
4. **Existing open reviews take copies from facts on their first open**, not as stored.
   The backfill (commit 12) stamps them first. An open review that already has an overall
   rating is flagged on first open (no stamp). ppj has 0 such reviews (00d §1.3).
5. **`save_calibration_note` still fails** on the missing `calibration_notes` column
   (01d F-D8, "raise separately"). I added its guards; its positive path cannot be tested.
6. **HR cycle screens are still unscoped:** `hr_list_appraisals`, calibration overview and
   matrix, CSV export, `send_review_reminder`, archive (SEC-26, commit 8).
   `send_review_reminder` and archive can still create a record for any company.
7. **Employee keeps read on HRMS Appraisal.** Decision 22 said "remove write; reads go
   through our endpoints". I removed write and create only. Removing read too would stop
   REST reads of appraisal scores (PRIV-9, commit 8). **Question below.**
8. **`hr_api.get_employee_scorecard` lets any HR role open any company's employee**
   (attendance, leave, contact details, appraisal history). Found while reading; not a
   review endpoint, not changed. Worth its own fix.
9. **The desk line rule uses the org tree's nested set** (includes people who left); the
   portal uses active reports. A manager-who-is-HR may see a departed report's released
   review in the desk. Small.
10. **The HR stand-in manager** (the first HR Manager, whom the portal treats as manager
    of anyone with no manager) can still open and act on those people's manager review in
    Manager Review, as before. Nowhere else. Which HR Manager is "first" is not chosen by
    anyone; that is an existing product rule, not new.
11. **A manager cannot set a rating back to 0** through save/submit: 0 means "not sent".
    0 is not a rating on any configured scale.
12. **No browser trace.** Phase 1 changes no page code. Visible effects: early-stage
    "Open Review" from HR's table and "View Review" in Employee Final Review for HR
    outside the line now show the refusal message (commit 11 should hide those buttons).
13. **SEC-15 revert proof not done** (same reason as groups A–C: the bench runs `dev`).

## 9. Decisions needed

1. **Decision 22, reads:** remove Employee **read** on HRMS Appraisal too, so appraisal
   scores cannot be read through REST? Recommended yes, in commit 8 with PRIV-9. The
   portal does not rely on that read.
2. **SEC-27, own review in the desk:** I deny it (PRIV-1). Keep?
3. **`get_employee_scorecard` HR company scope** (gap 8): fix inside 010 or separately?

## 10. What phase 2 must do next (commits 4–7)

- **Commit 4:** build `goals` / `standalone_kpis` in `get_my_review`, `get_manager_review`,
  `get_reviewer_view` from copies, by row name; one field filter per viewer and stage;
  SEC-7 page cut for invited reviewers; R10 late facts for HR; VIS-3 test.
- **Commit 5:** rating writers on copies (`submit_employee_review` without progress
  writes, `save_kpi_self_review`, `save_kpi_manager_review`), `stamp_rating` on each;
  `remove_review_item` (decision 9: a rated copy is always kept), `delete_review_item`,
  `save_review_item_definition` (decisions 6, 7, 8), `answer_rating_flag` (decision 12;
  record the answerer; email on overall change); retire the additional-reviewer endpoints.
- **Commit 6:** freeze on stage moves (`is_past_freeze_point` is ready), unfreeze on
  return (decision 18), completion refused while `open_blocking_flags` > 0, write-back,
  scoring from copies (VIS-7).
- **Commit 7:** definition lock hooks (`before_validate`, `on_trash`) on KPI and
  Individual Goal, refresh hook (`on_update`), lock release, `attach_ongoing_to_cycle`
  role check and skip, `set_goal_progress` blocked while held (decision 21).
- Before starting: fetch `origin/dev`, read the work board, rebase.
