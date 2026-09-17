---
slice: 010-portal-security-fixes
artifact: 03d-implementation-notes-group-d
author: hrms-fullstack-engineer
date: 2026-09-15
status: phases 1 (commits 1-3), 2 (commits 4-7) and 3 (commits 8-10, 12) built and tested locally; phase 4 not started
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

---

# Phase 2 — commits 4, 5, 6 and 7

## The short answer

**Phase 2 is built, committed on `slice/010-portal-security-fixes`, and tested on the
local bench. Nothing is pushed.**

- **30 new pin tests, all passing** (`alvoraa_portal/tests/test_review_screens_010d.py`).
  Phase 1's 34 still pass.
- **Full suites:** only the failures that were already there. `alvoraa_portal`: 490 tests, 3 errors (`test_leave_year`, known); then 355 tests, 1 failure + 10 errors (`test_invoicing`, known). `alvoraa_goals`: 18 tests, OK (2 skipped). Nothing new.
- **Integrity check:** "OK - all consistent" before every commit.
- **No migration was needed.** Phase 2 changes no DocType JSON. The new hooks were live
  on `test_site` without one (the lock tests prove it).
- **Three things you should know first:**
  1. **The portal page is not changed yet (commit 11, phase 4), so some review buttons
     now fail safely instead of working.** The review screens send copy row names now.
     The wizard's "Remove" still calls `delete_goal` / `delete_kpi`, which now find no
     such record and do nothing (before, they deleted the real goal). "Edit" opens the old
     goal form with a row name, which fails. "Add/remove" works but removing needs a
     confirmation the page does not send yet. Group D must ship as one batch.
  2. **Decision 19 is only half done.** On the Future Objectives page, "Remove" on a
     carried-forward goal from an earlier cycle calls `delete_goal` on that live goal.
     The server cannot tell that call from a normal delete, so it still deletes the goal
     unless an open review holds it. The fix is the page change in commit 11.
  3. **Writing a goal's target back often fails, by an older rule.** The Objective
     controller refuses any target change once progress exists
     (`controllers/goal.py`). Write-back does not override it: completion goes ahead and
     the copy records "Not written back" with that reason. KPIs are not affected.

## 1. Commits

On `slice/010-portal-security-fixes`, oldest first, after phase 1's `11bba93`. Brought
into local `dev` with `merge --ff-only` for testing.

| Commit | What |
|---|---|
| `f5525f8` | Commit 4: review screens show the review's copies, never the live records |
| `7445820` | Commit 5: ratings, removals and definition changes are made on the copies (also fixes one commit 4 test that froze too early) |
| `70366bb` | Commit 6: freeze at the stamped point, unfreeze on return, completion block, write-back once, completed copies never change, scoring from copies |
| `8ad6ea3` | Commit 7: definition lock, release, delete rule, refresh hook, `attach_ongoing_to_cycle` and `set_goal_progress` guards |
| `4c30722` | Test fix: the static lock test reads files with a byte-order mark |
| `4bb3d8d` | Test fix: the static lock test proves it found the two guarded writers |
| this file | Phase 2 notes |

One commit of mine was redone before anything saw it: my first commit 5 attempt
swept the new tests into a commit named as a test fix. I undid it in my worktree
(`reset --soft`, my branch only) and committed it again as `7445820` with an honest
message.

## 2. What came in from others

- **`origin/dev`:** fetched before starting, before every merge, and before the full
  suites. **Nothing came in.** It stayed at `c27fb56`.
- **Work board:** only this slice's row. I marked "Bench in use" before each run and
  cleared it after.
- **Main checkout:** the same other sessions' uncommitted files as in phase 1
  (`CLAUDE.md`, `.claude/agents/*`, `.claude/context/frappe-conventions.md`,
  `.claude/context/ux-learnings.md`, `backlog/KPI_AUTOMATION_BACKLOG.md`, deleted
  `OBJECTIVES_KPI_REQUIREMENTS.md`, `hrms/.../alvoraa_position.py`, untracked files).
  None is a file phase 2 changes. Not touched. Every `merge --ff-only` went through.
- No conflicts.

## 3. What was built, file by file

Mechanism key: **configure**, **extend** (hooks, existing functions), **build** (new code).

### Commit 4 — review screens read the copies

| File | Mechanism | What and why |
|---|---|---|
| `alvoraa_goals/review_items.py` | build | `review_payload(ext, viewer)`: the one place that decides which copy fields a viewer gets (table below). `late_facts(ext)`: R10. `definition_changes(row)`: what changed inside the review, for change markers. `copied_sources(ext)`. The fact queries were split out of `_recount` (`_load_facts`, `_row_window`, `_facts_in_window`) so the late-facts view counts exactly the same way |
| `alvoraa_portal/performance_api.py` | extend | `get_my_review`, `get_manager_review`, `get_reviewer_view` return copies by row name, in the keys the page reads today, plus `removed_items` and `numbers_frozen`. The per-goal KPI query (`_goal_kpis`) is gone; the future-objectives cycle labels are one query instead of one per goal |

**Who sees what (`review_payload`):**

| Field group | Subject | Manager line | HR | Invited reviewer |
|---|---|---|---|---|
| Definition, numbers, facts count | yes | yes | yes | yes (only with `past-objectives`) |
| Change markers | yes | yes | yes | no |
| Self rating and comment | yes | once sent | once sent | once sent |
| Manager rating and comment | from Employee Final Review (decision 11) | yes | yes | no |
| Potential | never | yes | yes | no |
| Stamps, flags, answerers | never | yes | yes | no |
| Removed items | own removals; all from Employee Final Review, with label, date and reason, not who (decision 10) | yes, with who and stage | yes | no |
| Facts dated by upload | no | no | yes (decision 5) | no |
| Late facts (R10) | no | no | HR Review and Completed | no |

- **VIS-3:** no response holds a live record's name. `past_incomplete_goals` (Future
  Objectives page) stays on live records, as VIS-15 says, but leaves out anything this
  review holds a copy of, so a copy is never shown beside its own live record.
- **SEC-7, decision 17:** an invited reviewer is refused unless the review is in Manager
  Review. `page_data` is cut to the invited pages (none means nothing). Copies come only
  with `past-objectives`.

### Commit 5 — changes on the copies

| File | Mechanism | What and why |
|---|---|---|
| `review_items.py` | build | `live_row`, `is_rated`, `rating_value`, `apply_self_review` (SEC-1), `set_item_rating`, `remove_item` (R12, decision 9), `add_items` (VIS-5), `change_definition` (R2), `answer_flag` (R7), `audit` (an Info entry on the review record) |
| `performance_api.py` | extend | `save_review_page`: past-objectives keys must be this review's copies, or the save is refused. `submit_employee_review`: self fields onto copies only, no progress write, no `except: pass`; future objectives are created with no cycle (decision 19) and a failed one stops the submission (VIS-15). `get_available_for_review` / `set_review_selection`: only the subject, only before sending; add and remove copies; no cycle writes; removal needs `acknowledge_removal=1` |
| `performance_api.py` | build | New endpoints, all on copy row names: `save_review_item_rating`, `remove_review_item`, `delete_review_item`, `save_review_item_definition`, `answer_rating_flag`. One guard, `_review_actor`, decides subject / manager line / HR (HR under `_assert_hr_can_view`) and the stage each may act in, before anything is read or written |
| `performance_api.py` | extend | Retired (refuse, rule `R13`): `save_kpi_self_review`, `save_kpi_manager_review`, `add_additional_reviewer`, `save_additional_reviewer_rating` |

**Who may do what, and when (as built):**

| Action | Subject | Manager line | HR |
|---|---|---|---|
| Rate an item | self rating, Not Started / Employee Review | manager rating and potential, Manager Review | no |
| Change title, target, weight, period (decision 6) | Employee Review | Manager Review | no |
| Add items (decision 7) | Employee Review, own live items meeting the period | no | no |
| Remove an item | Employee Review, confirmation | Manager Review, confirmation and reason | HR Review, confirmation and reason |
| Delete an item created in the review (R11) | same stages as removal; only if created after the copies were taken, unrated, with no progress or evidence |
| Answer a rating question (decision 12) | never (SEC-10) | the rater, any stage from Manager Review until Completed | only when the rater has left or no longer manages the employee, in HR Review, with a reason |

- **Decision 9:** a copy with any self, manager or potential rating is kept, marked
  Removed, whatever the setting. An unknown setting keeps it too.
- **Decision 12:** "left or changed role" is worked out on the server: the rater's
  Employee is not Active, their login is disabled, or they are no longer in the
  employee's manager line (or, for a rating HR gave, no longer HR for that company). A
  rating stamped before raters were recorded is answered by the manager line. The
  employee gets an email with no numbers when a released overall rating changes.
- **Audit:** removal, delete, definition change, flag answer, freeze and unfreeze each
  write an Info entry on the review record (row name, user, stage, and the reason where
  one is given). The record opens only for HR under the stage rule (SEC-27).

### Commit 6 — freeze, completion, write-back, scoring

| File | Mechanism | What and why |
|---|---|---|
| `review_items.py` | build | `apply_stage(ext)`: after any stage move, freeze at the stamped freeze point (last count first), unfreeze when the review goes back before it (decision 18). `write_back(ext)`: R15 / SEC-25 |
| `alvoraa_appraisal_extension.py` | extend | Once a review is Completed, its copies cannot change, even through the review code (VIS-10) |
| `performance_api.py` | extend | Every stage move (`submit_employee_review`, `submit_manager_review`, `acknowledge_final_review`, `return_to_manager`, `return_for_revision`, `advance_review_status`) calls `apply_stage` and saves through the one review-record save. HR Review → Completed: refresh, refuse while `open_blocking_flags` > 0, freeze, stamp `completed_on`, write back; returns `write_back_notes` |
| `performance_api.py` | extend | VIS-7: `_scored_items(ap)`, `_sync_potential_to_extension` and `suggest_ratings` read copies; a review with no copies is refused. Only a brand-new appraisal in `hr_generate_appraisals` is projected from live records |
| `tests/test_portal_security_010.py` | configure | SEC-16 ceilings: `performance_api.py` 88 → 68; `review_items.py` 1 → 2 with its reason (the write-back save) |

**Write-back, as built:** for each copy whose name, target, weight or period differs
from `definition_at_start`, and only once (`written_back_on`):

- a field is written only if the live record still holds the start value; otherwise it
  is left alone and listed in `write_back_note`;
- the save goes through the document with a flag the lock honours, so the live record's
  own rules and change history apply, and an Info entry on the live record says which
  review changed what;
- a refused save (for example weights over 100% on the live cycle) is rolled back to a
  savepoint, recorded on the copy, logged with document names only, and does not stop
  completion.

### Commit 7 — the lock on live records

| File | Mechanism | What and why |
|---|---|---|
| `review_items.py` | build | `holds(doctype, names)`: one query; release date per record. `enforce_definition_lock`, `refuse_delete_while_held`, `refresh_copies_of` |
| `alvoraa_goals/hooks.py` | extend | Individual Goal: `before_validate`, `before_update_after_submit`, `on_trash`, `on_update`. KPI: `before_validate`, `on_trash`, `on_update`. Added under the existing entries, with comments |
| `performance_api.py` | extend | `attach_ongoing_to_cycle`: HR only, permitted companies only, skips held items and lists them under `held_by_open_review` (SEC-20). `set_cycle_membership`: refuses a held item |
| `goals_api.py` | extend | `set_goal_progress` refused while a review holds the goal (decision 21) |

- **Locked fields:** KPI `kpi_name`, `target_value`, `weightage`, `period_start`,
  `period_end`, `appraisal_cycle`, `employee`, `progress_mode`, `direction`,
  `baseline_value`, `unit`, `individual_goal`. Objective `goal_name`, `target_value`,
  `weightage`, `start_date`, `end_date`, `appraisal_cycle`, `employee`, `progress_mode`,
  `unit`, `parent_goal` (Objectives have no direction or baseline). Values are compared
  by field type, so "50" sent over REST equals 50.0.
- **Held** = a live copy in a review that is not Completed, whose appraisal is not
  cancelled, and whose lock is not released. **Released** on the server's date at cycle
  end + the setting's days; 0 days or no cycle end means never.
- **Fail closed:** if the "is it held?" lookup itself fails, the change or delete is
  refused.
- **Refresh hook:** one query finds open, unfrozen reviews holding the record; for each
  it refreshes the copies inside a savepoint. A failure is logged with names only and
  never stops the live save; the review catches up when next opened.

## 4. Requirements and decisions → test → result

All in `alvoraa_portal.tests.test_review_screens_010d` unless named. Result is the last
run on `test_site`.

| Requirement / decision | Test | Result |
|---|---|---|
| VIS-3 (subject, manager, reviewer) | `test_vis3_review_screens_return_copies_and_never_a_live_record_name` | pass |
| VIS-15 + VIS-3 (future objectives list) | `test_vis15_future_objectives_list_leaves_out_what_this_review_holds` | pass |
| PRIV-1, PRIV-13, decision 11 | `test_priv1_priv13_each_viewer_receives_only_what_the_stage_allows` | pass |
| SEC-7, decision 17 | `test_sec7_an_invited_reviewer_reads_only_their_pages_and_only_during_manager_review` | pass |
| R10, PRIV-11 | `test_r10_facts_approved_after_the_freeze_are_shown_to_hr_and_never_change_the_score` | pass |
| NFR: opening a review | `test_query_count_opening_a_review_does_not_grow_with_its_items` (3 vs 16 items) | pass |
| SEC-1 | `test_sec1_the_self_review_writes_only_this_reviews_copies_and_never_progress` | pass |
| VIS-15, decision 19 (no cycle) | `test_vis15_a_future_objective_that_cannot_be_created_stops_the_submission` | pass |
| VIS-6, R13, retired endpoints, VIS-3 writes | `test_vis6_r13_ratings_are_saved_on_copies_and_the_old_rating_endpoints_are_retired` | pass |
| R12, SEC-24, decisions 9 and 10, VIS-10 (remove after completion) | `test_r12_sec24_who_removes_when_and_a_rated_copy_is_always_kept` | pass |
| VIS-5, decision 7 | `test_vis5_the_dialog_adds_and_removes_copies_and_never_moves_a_live_record` | pass |
| R11 inside the review | `test_r11_only_an_item_created_inside_the_review_with_no_facts_can_be_deleted` | pass |
| R2 inside the review, decision 6, R7 (definition moves a stamp) | `test_r2_decision6_the_employee_then_the_manager_change_a_copys_definition` | pass |
| R7, decision 12, SEC-23 (who answers) | `test_r7_decision12_the_rater_answers_a_flag_and_nobody_else_does` | pass |
| Decision 12 (HR for a rater who left; email) | `test_r7_decision12_hr_answers_with_a_reason_when_the_manager_has_left` | pass |
| R6, decision 18 | `test_r6_decision18_numbers_freeze_at_the_stamped_point_and_a_return_unfreezes_them` | pass |
| R6 default (HR sent) | `test_r6_with_the_default_the_numbers_freeze_when_hr_completes_the_review` | pass |
| R7, SEC-23, decision 13 (completion block) | `test_r7_sec23_hr_cannot_complete_while_a_manager_or_overall_rating_waits_for_an_answer` | pass |
| R15, SEC-25, R13 (once; refused save recorded) | `test_r15_sec25_agreed_changes_go_back_once_and_nobody_elses_change_is_overwritten` | pass |
| SEC-25 (conflict kept) | `test_sec25_a_live_record_changed_after_the_review_started_keeps_its_value` | pass |
| VIS-10 | `test_vis10_a_completed_reviews_copies_cannot_change_by_any_path` | pass |
| VIS-7 | `test_vis7_scores_come_from_the_reviews_copies_never_the_live_records` | pass |
| R2, SEC-19, decisions 8 and 20 (desk, REST, portal, ignore_validate) | `test_r2_sec19_a_held_definition_cannot_change_by_any_path` | pass |
| R9, SEC-22 | `test_r9_sec22_the_lock_releases_n_days_after_the_cycle_ends_and_0_means_never` | pass |
| R11 outside the review | `test_r11_a_held_record_cannot_be_deleted_by_any_path` | pass |
| Decision 21 | `test_decision21_progress_cannot_be_set_by_hand_while_a_review_holds_the_goal` | pass |
| SEC-20 | `test_sec20_only_hr_pulls_work_into_a_cycle_for_their_companies_and_held_items_stay` | pass |
| R3 refresh hook | `test_r3_approving_a_fact_updates_the_open_reviews_copy_without_opening_it` | pass |
| NFR: refresh hook | `test_query_count_the_refresh_hook_costs_one_query_when_no_open_review_holds_the_record` | pass |
| SEC-19 static | `test_r2_static_no_code_writes_a_locked_field_around_the_lock` | pass |
| SEC-16 ceilings | `test_portal_security_010.TestSec16IgnorePermissionsCeiling` | pass (full suite) |
| Phase 1 pins still hold | `test_review_copies_010d` (34) | pass |

**Where the documents differed, and what I followed:**

- **VIS-9 (01d) vs decision 18 (00e):** 01d says a return never unfreezes. Decision 18
  says it does. Built as decision 18.
- **Manager and HR removal stages:** 01d SEC-24 allows Manager Review, Employee Final
  Review and HR Review; 00d §6.4 says the manager in Manager Review and HR in HR Review.
  I built 00d's narrower rule (nobody removes while the employee is reading the final
  review). Say if you want the wider one.
- **Who answers for a rater who left (decision 12 vs 01d Q-D11):** decision 12 says HR;
  built that way, in HR Review only, because HR's stage rule (decision 15) keeps HR out
  earlier.
- **`save_kpi_self_review` / `save_kpi_manager_review`:** 00d said "redirect to the
  copy"; 01d VIS-3 says a write must never accept a live record's name. I retired both
  and added `save_review_item_rating`, which takes a row name.
- **R11 "added inside the review":** an item picked in the dialog that existed before
  the review can be removed, not deleted. Only an item created after the copies were
  taken can be deleted (00d §4.4).
- **Email on an overall rating change:** only when the rating is already released
  (Employee Final Review onwards). Before that the employee has not seen a rating, so an
  email would announce a change they cannot see.

## 5. Non-functional dimensions, re-checked on the code written

| Dimension | Before → after | Verdict | Why |
|---|---|---|---|
| Performance | per-goal KPI query in two readers; no hook | **improves** on review screens, small cost on saves | Review readers lost the N+1 `_goal_kpis`; opening a review costs the same for 3 or 16 items (tested). Every KPI and Objective save gains one indexed query (tested). A save that changes a locked field gains one more. Completion adds one save per changed copy |
| Security | ratings and cycle moves reachable around the review | **improves** | SEC-1, SEC-7 pages, SEC-19, SEC-20, SEC-23, SEC-24, SEC-25, VIS-3, VIS-5, VIS-10 closed and pinned. Four rating writers on live KPIs retired. `attach_ongoing_to_cycle` no longer open to any employee. `ignore_permissions`: `performance_api.py` 88 → 68; `review_items.py` 1 → 2 (write-back, reason in the ceiling test) |
| Reliability | silent `except: pass`, deletes of real goals from the wizard | **improves**, with two declared risks | Self-review submit fails whole instead of half-writing. Write-back failures are recorded, not raised. Risks: the refresh hook adds work to every save (bounded, in a savepoint, never blocks); the page's review buttons fail until commit 11 |
| Scalability | — | **neutral** | Hook: 1 query per save when nothing holds the record; a held record refreshes at most the reviews that hold it (normally 1, 2 with overlapping cycles). `attach_ongoing_to_cycle` now narrows by permitted companies' employees |
| Maintainability | — | **degrades slightly** | `review_items.py` is now about 1,400 lines and holds copies, access-filtered payloads, writes, freeze, write-back and the lock. Still one module with one save path, one field filter and one lock, each with named tests. Worth splitting into two files after group D ships |
| Data integrity | live edits could change finished reviews | **improves** | Definitions cannot move under an open review; completed copies are immutable; write-back never overwrites a later live change; ratings never reach live records |
| Compliance / privacy | potential and stamps reached the subject's screens | **improves** | One field filter; potential, stamps and flags never reach the subject; reviewers see only invited pages; removal reasons reach the employee only from Employee Final Review. New logs carry document names only. Audit entries hold user ids and reasons, on HR-only records |

**Query counts:** measured on `test_site` with a probe that switched commits off and rolled everything back
(checked afterwards: 0 probe records left). Times are single runs on the local bench, not a load test.

| Call | 3 items | 20 items |
|---|---|---|
| `get_my_review`, first open (takes the copies; cold caches on the first probe) | 117 queries, 242 ms | 52 queries, 109 ms |
| `get_my_review`, later opens | **18 queries, 25 ms** | **18 queries, 43 ms** |
| Refresh hook, record held by one open review | 10 queries, 14 ms | 10 queries, 24 ms |
| Refresh hook, record not held (the usual save) | **1 query, 3 ms** | — |

The tests pin the shape: later opens cost the same for 3 and 16 items; the hook costs
exactly 1 query when nothing holds the record and at most 12 when one review does.

**Indexes added:** none in phase 2 (the lookups use phase 1's indexes on
`tabAlvoraa Review Item.source_name` and `tabKPI.employee` / `appraisal_cycle`).

**Sensitive fields touched:** self, manager and potential ratings and comments (now
only on copies, filtered per viewer); removal reasons; stamps and flag answers.

## 6. Commands run and real results

All on `hrlocal-bench`, site `test_site`, one run at a time (`pgrep` first; work board
marked).

| When | Command | Result |
|---|---|---|
| Before every commit | `python scripts/check_app_integrity.py` | "OK - all consistent" (524 checks) |
| After commit 4 | `--module …test_review_screens_010d` | 6 tests: 1 failure, a test fault (it froze the numbers before its own setup readings were approved). Fixed in commit 5 |
| After commit 5 | same module | 15 tests, OK |
| After commit 5 | `--module …test_review_copies_010d` | 34 tests, OK |
| After commit 6 | `--module …test_review_screens_010d` | 22 tests, OK |
| After commit 7 | same module | 29 tests OK; the static test class (run separately) 1 error: a byte-order mark in `performance_api.py`. Fixed in `4c30722` |
| After `4c30722` and `4bb3d8d` | `--test test_r2_static_no_code_writes_a_locked_field_around_the_lock` | 1 test, OK (twice) |
| End of phase (at `4bb3d8d`) | full `--app alvoraa_portal` | 490 tests: 3 errors (`test_leave_year`, known). 355 tests: 1 failure + 10 errors (`test_invoicing`, known). Failure list checked name by name: nothing else |
| End of phase | full `--app alvoraa_goals` | 18 tests, OK (2 skipped) |
| End of phase | query-count probe through `bench --site test_site console`, commits off, rolled back | figures in section 5; 0 records left |

**Migrations run:** none in phase 2. No DocType JSON changed. Hooks and code were picked
up by the test runner without one.

## 7. Tenant steps and deploy notes (not done by me)

- Nothing new beyond phase 1's `bench migrate`. Phase 2 adds no fields and no patch.
- **Do not deploy phase 2 without commit 11.** The review screens now speak row names,
  and the page does not yet.
- The retired endpoints (`save_kpi_self_review`, `save_kpi_manager_review`,
  `add_additional_reviewer`, `save_additional_reviewer_rating`) have no reachable page
  caller (00d §9.2). Any integration calling them now gets a refusal.
- `attach_ongoing_to_cycle` now needs an HR role. Its only caller in our code is
  `hr_generate_appraisals` (HR already).

## 8. Known gaps and shortcuts — honestly

1. **Page not updated** (commit 11): see the short answer. Until then: wizard "Remove"
   and "Delete" do nothing useful; "Edit" fails; removal from the dialog needs a
   confirmation the page does not send; the manager screen has no flag answer, removal
   or definition controls.
2. **Decision 19 needs the page** (short answer, point 2).
3. **Objective target write-back** is refused by the existing "no target change after
   progress" rule, and recorded (short answer, point 3).
4. **Outside screens still show live ratings and use live records**: `KPI_FIELDS`,
   `get_cycle_items`, `get_team_kpis`, HR cycle screens, CSV export, calibration overview
   (commit 8, phase 3). `get_cycle_items` and `get_team_appraisal` were in 01d's VIS-3
   test list; I left them for commit 8 with the other outside payloads.
5. **Invited reviewers still come from any company** (commit 9).
6. **No lock reminder job** (commit 10).
7. **Existing open reviews are not backfilled** (commit 12). **Commit 12 must bypass the
   new VIS-10 guard** to write copies onto Completed reviews: the Extension now refuses
   any change to a Completed review's copies, even through `save_review_record`.
8. **`save_calibration_note` still fails** on the missing `calibration_notes` column
   (phase 1 gap 5, unchanged).
9. **An HR person who is also the employee's line manager acts as the manager** in the
   item endpoints, so in HR Review they cannot remove items as HR. Rare; a second HR
   person can.
10. **`delete_review_item` in keep mode** keeps the deleted item's copy marked Removed
    (the setting decides, as for removal). The copy then names a live record that no
    longer exists. Harmless (plain text), but the review shows it as removed, not deleted.
11. **The removal audit entry holds the reason as text** on the review record's timeline.
    Only HR (stage rule) and System Manager (all Comments over REST) can read it.
12. **`create_checkin` still writes progress with `ignore_validate`** (not a locked field,
    and decision 21 names only `set_goal_progress`). It does not change a copy's number:
    copies count dated facts only.
13. **No browser trace** (no page change in this phase). **Response times not measured.**
14. **SEC-15 revert proof not done** (the bench runs `dev`).

## 9. Decisions needed

1. **Removal stages:** keep manager = Manager Review, HR = HR Review (as built), or allow
   removal during Employee Final Review too (01d SEC-24)?
2. **Objective target write-back** (gap 3): leave the older "no target change after
   progress" rule to refuse it and record it (as built), or let an agreed review change
   pass that rule?
3. **Email on overall rating change before release:** keep "only once released" (as
   built)?

## 10. What phase 3 must do next (commits 8, 9, 10, 12)

- **Commit 8:** `KPI_FIELDS` without ratings; KPI rating fields to permlevel 1 (SEC-2,
  PRIV-9); `get_cycle_items`, `get_team_kpis`, `get_team_appraisal` from copies or without
  ratings; HR cycle screens and CSV from copies with SEC-26 scope; badge (R5, PRIV-10);
  Employee loses read on HRMS Appraisal (decision 26); `get_employee_scorecard` scoped to
  permitted companies (decision 28).
- **Commit 9:** reviewer picker and invite endpoints limited to the subject's company.
- **Commit 10:** daily reminder job for items still locked 15 days after a cycle ends.
- **Commit 12:** backfill patch, dry-run report, rollback script. Needs its own way past
  the VIS-10 guard for Completed reviews (gap 7).
- Before starting: fetch `origin/dev`, read the work board, rebase.


---

# Phase 3 — commits 8, 9, 10 and 12, and decisions 26 and 28

## The short answer

**Phase 3 is built, committed on `slice/010-portal-security-fixes`, brought into local
`dev`, and tested on the local bench. Nothing is pushed.**

- **27 new pin tests, all passing** (`alvoraa_portal/tests/test_review_outside_010d.py`).
  Phase 1's 34 and phase 2's 29 still pass.
- **Full suites:** `alvoraa_portal`: 495 tests, 1 failure + 3 errors; then 441 tests, 1 failure + 10 errors.
  All known (`test_leave_year` 3 errors, `test_invoicing` 1 failure + 10 errors) **except one that is not
  mine:** `test_invoicing.test_every_billing_doctype_is_named_as_control_plane_only` fails because slice
  012's two new doctypes are not classified in `subscription.py`. I left a note for 012 on the work board.
  `alvoraa_goals`: 18 tests, OK (2 skipped).
- **Integrity check:** "OK - all consistent" before every commit.
- **`bench --site test_site migrate` was run once** (KPI and Appraisal permission changes, and
  the new patch). `ppj.localhost` was not touched.
- **The copy of existing reviews is fast:** 806 synthetic reviews in ppj's stage mix, 3,870
  copies, **15.1 seconds**. The dry run took 1.4 seconds.
- **Three things you should know first:**
  1. **The portal page is still not changed (commit 11, phase 4).** Screens outside the review now
     leave out ratings, so the page shows gaps: the appraisal detail's goal rows show "0.00" where a
     score used to be, and the team KPI card has no "rated" count. The tree's "in review" tag now
     appears only on items an open review holds. The reviewer picker still sends no review, so a
     manager searches their own company. Group D must still ship as one batch.
  2. **Employees lose every desk and REST read of HRMS Appraisal** (decision 26). The one portal
     call that saved through that permission, "Save Self-Assessment", broke in phase 1 when
     decision 22 removed write. I fixed it in commit 8: it now writes its one field after its own
     owner check.
  3. **One choice I made that you may want the other way:** with the lock release set to 0
     (never), the HR reminder repeats every 7 days for as long as those reviews stay open. The
     alternative is no reminder at all when the lock never releases. Question 1 in section 9.

## 1. Commits

On `slice/010-portal-security-fixes`, oldest first, after phase 2. Brought into local `dev`
with `merge --ff-only`.

| Commit | What |
|---|---|
| `f22a45e` | Commit 8, part 1: rating fields on the live KPI move to level 1 and nobody writes them (SEC-2, PRIV-9); Employee loses read on HRMS Appraisal (decision 26); desk list labels (R8); self-assessment save fixed |
| `ccf043f` | Commit 8, part 2: outside screens show no Objective or KPI rating; appraisal totals follow the release rule; `get_cycle_items` from copies; the "in review" badge (R14, PRIV-9, VIS-3, R5, PRIV-10) |
| `94d6eca` | Commit 8, part 3: HR cycle screens read the copies, scoped by company and stage (R8, SEC-26, SEC-30) |
| `0d30808` | Commit 8, part 4: `get_employee_scorecard` and `get_employee_detail_for_manager` scoped to HR's companies (decision 28) |
| `13f228f` | Commit 9: reviewer picker and invitees from the reviewed person's company (SEC-7, decisions 2 and 17) |
| `285858a` | Commit 10: daily reminder to HR about items still locked (R9) |
| `926369e` | Commit 12: copy existing reviews — patch, dry run, rollback helpers |
| `5100f83` | Test: `performance_api.py` ceiling 68 → 64; `review_backfill.py` pinned at 0 |
| `9c6d97b` | The M3 permission report also lists a tenant's read grant on Appraisal (decision 26) |
| this file | Phase 3 notes |

Commit 10 was amended once in my worktree, before it reached `dev`: my first commit carried a
test with a broken settings helper, because a check in my own edit script stopped the fix from
being applied. Nothing else was rewritten.

## 2. What came in from others

- **`origin/dev`:** fetched at the start, before every merge and at the end. **Nothing came in.**
  It stayed at `c27fb56`.
- **Local `dev` moved three times, all slice 012** (its own worktree, its own files). I read every
  diff and rebased onto it each time. None touches a file phase 3 changes:
  - `ed8732f`, `1d75c28`, `bdc50c0`: indexes (`data_review.py`), the Org Settings allow-list in
    `hr_api.get_org_setting` / `set_org_setting`, attendance analytics scope.
  - `b89cdfb`, `c692ea9`, `85f0073`, `e6bae5c`, `3c33d56`: two new doctypes (Data Review Item,
    Leader View Settings), `org_figures.py`, their tests and fixtures, one `after_migrate` addition.
  - **Worth knowing:** 012's allow-list means `set_org_setting` now accepts only
    `kra_link_mandatory`. Decision 23's portal Org Settings for the three review settings (phase 4)
    must write HR Settings, not Global Defaults — which is what 00d planned anyway.
- **Work board:** 012 held the bench twice while I built; I waited, then marked "Bench in use"
  for each of my runs and cleared it after.
- **Main checkout:** the same other sessions' uncommitted files as in phases 1 and 2 (`CLAUDE.md`,
  `.claude/agents/*`, `.claude/context/*`, `backlog/KPI_AUTOMATION_BACKLOG.md`, deleted
  `OBJECTIVES_KPI_REQUIREMENTS.md`, `hrms/.../alvoraa_position.py`, untracked files). None is a
  file phase 3 changes. Not touched. Every `merge --ff-only` went through.
- No conflicts.

## 3. What was built, file by file

Mechanism key: **configure** (JSON, settings), **extend** (hooks, existing functions),
**build** (new code).

### Commit 8 — outside screens, HR cycle screens, decisions 26 and 28

| File | Mechanism | What and why |
|---|---|---|
| `alvoraa_goals/.../doctype/kpi/kpi.json` | configure | `self_rating`, `self_comment`, `manager_rating`, `manager_comment`, `potential_rating`, `potential_comment` and the `additional_reviewers` table at permission level 1. Level-1 rows: read for HR Manager, HR User, System Manager; **no write for anyone**. Old values stay for HR (PRIV-9, PRIV-14) |
| `alvoraa_goals/controllers/kpi.py` | build | `refuse_rating_changes` (before_validate): any change to those fields, or to an additional reviewer's rating or comment, is refused, Administrator included, with `ignore_validate` too. A new KPI may not arrive rated. Only a document flag set by the rollback script passes (`RATING_REPAIR_FLAG`) (SEC-2) |
| `alvoraa_goals/hooks.py` | extend | KPI `before_validate` becomes a list: the lock first, then the rating guard |
| `alvoraa_goals/.../kpi/kpi_list.js`, `.../individual_goal/individual_goal_list.js` (new) | build | Desk lists say "Live records, not the review record" (R8, VIS-12). API checked: `page.add_inner_message` in Frappe `ui/page.js:703`; `<doctype>_list.js` is loaded by `desk/form/meta.py:100` |
| `hrms/hrms/hr/doctype/appraisal/appraisal.json` (our fork) | configure | Employee row removed: no read either (decision 26) |
| `alvoraa_portal/goals_api.py` | extend | `save_self_assessment` writes `reflections` with `db.set_value` after its owner and draft checks (it saved through the Employee's permission, which is gone). `get_appraisal_data`: no item scores; totals from Employee Final Review. `get_goal_detail`: `review_badge` |
| `alvoraa_portal/hr_api.py` | extend | `get_goal_detail`: `review_badge`. `get_employee_scorecard`, `get_employee_detail_for_manager`: HR outside its own line goes through `_hr_target_employee` (permitted companies, SEC-13 message); the manager-line rule is unchanged (decision 28). No signature change |
| `alvoraa_goals/review_items.py` | build | `review_badges(doctype, names)`: `{"in_review": 1, "updates_after": <period end>}` and nothing else, one query; shares `_holding_reviews` with the lock so the two agree. `rating_fields_for(viewer, stage)` and `overall_rating_visible`: the one field rule, now also used by `review_payload`. `VIEWER_NONE` for HR rows before HR Review. `late_fact_counts(reviews, rows)`: R10 for many reviews in three queries |
| `alvoraa_portal/performance_api.py` | extend | Table below |
| `demo/pp_jewellers/seed_performance.py` | extend | Seeded history sets the repair flag, or the guard would refuse the seeder's rated KPIs. `demo/` never reaches `main` |

`performance_api.py`, function by function:

| Function | Change |
|---|---|
| `KPI_FIELDS` | The six rating fields removed (feeds the tree, My KPIs, team KPIs) |
| `_decorate_kpis` | Adds `review_badge`, one query for all rows |
| `get_team_kpis` | `rated_count` removed |
| `get_performance_tree` | `review_badge` on goals and KPIs; `in_cycle` set only when an open review holds the item (R5) |
| `_appraisal_payload` | Goal rows lose `score` and `score_earned`; totals (`total_score`, `self_score`, `avg_feedback_score`, `final_score`) are `None` for the subject before Employee Final Review |
| `get_my_appraisal`, `get_appraisal` | Subject rule above; `get_appraisal` gives HRMS self-ratings to others only once the self-review is sent |
| `get_team_appraisal` | HR outside the caller's direct reports: `_assert_hr_can_view`, or the company check when there is no appraisal |
| `list_appraisals` | Scores per row: own from Employee Final Review; line always; HR outside the line from HR Review. One extra query |
| `get_cycle_items` | From the review's copies by row name once the caller may open the review at its stage (`source: "review"`); otherwise live records (`source: "live"`); never a rating. HR limited to permitted companies |
| new `_hr_cycle_reviews`, `_copies_of`, `_visible_ratings`, `_copy_numbers` | The scoped review list for HR screens, with a viewer per row: subject / manager (own line) / hr (HR Review on) / none |
| `hr_list_kpis` | KPI copies of the cycle's scoped reviews; ratings per viewer. **Needs a cycle now** (it returned every KPI in the tenant) |
| `hr_cycle_summary` | From copies; `rated` and `final_score` only where visible; branch average of final score only over visible rows |
| `hr_list_appraisals` | Scoped; overall rating per viewer; responsible emails in two queries instead of three per row |
| `send_review_reminder`, `archive_review`, `unarchive_review` | `_require_hr_for`: permitted companies or own line; no review record created |
| `export_cycle_kpis_csv` | From copies (Objectives and KPIs), scoped, ratings per viewer; "KPI ID" is the row id; removed copies only for manager/HR viewers; new columns at the end: Item Type, Review, Review Stage, Removed, Facts Approved After Close (HR viewers only); text cells starting `= + - @` written as text; one security log line with counts |
| `get_calibration_overview` | From copies, scoped; keys a viewer may not see are left out; no per-review `get_doc` |
| `get_calibration_matrix` | Scoped; own row has no `potential_rating`; employees and managers read in two queries instead of per row |
| `get_calibration_signoff` | HR only (SEC-30) |

### Commit 9 — reviewers from the reviewed person's company

| Function | Change |
|---|---|
| `search_employees(query="", appraisal=None)` | With `appraisal`: the review's manager line, or HR under `_assert_hr_can_view`; never the subject (SEC-10); results are active employees of the subject's company, not the subject, at most 50. Without: a manager (direct reports) gets their own company, HR its permitted companies, anyone else `[]`. One query (name or ID) |
| new `_check_invitees` | Invitees must be active employees of the subject's company and not the subject; one bad invitee refuses the whole call before anything is saved or emailed (SEC-7) |
| `invite_reviewer`, `invite_reviewers_batch` | Call it; the batch also refuses a malformed list |

Decision 17 (reviewers lose access after Manager Review) was already built in phase 2; phase 3
adds a pin for both the read and the comment submit.

### Commit 10 — the lock reminder

| File | Mechanism | What and why |
|---|---|---|
| `review_items.py` | build | `remind_hr_of_held_items()`: one query finds open reviews still holding items whose cycle ended 15 or more days ago; due on day 15, 22, 29… while the lock lasts; none if the lock releases on or before day 15; with 0 (never) it repeats until the reviews are completed. Each enabled HR Manager gets one Notification Log for their permitted companies: cycle name, count, date. No names (PRIV-15). A Notification Log also emails when the person's notification settings allow, so no second email is sent. A failure is logged with the user id only |
| `alvoraa_goals/hooks.py` | extend | Added at the end of `scheduler_events["daily"]`, with a comment |

### Commit 12 — copy existing reviews

| File | Mechanism | What and why |
|---|---|---|
| `alvoraa_goals/review_backfill.py` (new) | build | `report(names=None)` read-only dry run; `run(names=None)` the copy; `undo_backfill(dry_run=1)`; `copy_ratings_back_for_rollback(dry_run=1)`. One planning function feeds both the report and the copy, so they agree |
| `alvoraa_goals/patches/v1_0/take_review_copies.py` (new) | build | Syncs Alvoraa Review Item, the Extension and KPI first (a plain `patches.txt` line runs **before** the DocType sync — checked in Frappe `modules/patch_handler.py`), then `run()` |
| `alvoraa_goals/patches.txt` | configure | One line at the end |

**What the copy does, as built:**

| Review | Result |
|---|---|
| Completed | Copies of the non-cancelled, non-future Objectives and KPIs tagged to that cycle and employee. Numbers as stored (`actual_value`/`attainment_pct`, `actual_progress`/`progress_pct`). KPI ratings and comments copied and stamped on those numbers. `frozen = 1`, `completed_on` = the record's last change, `backfilled = 1` on every copy. Overall rating stamped |
| Employee Review, Manager Review, Employee Final Review, HR Review | The same, plus the freeze point and removal setting in force, frozen only if already past the freeze point, and the draft's `past-objectives` keys re-keyed from live names to row names (names not in the review are dropped and counted) |
| Not Started | Nothing |
| Appraisal missing or cancelled, no cycle, unknown stage | Nothing; counted in the report |
| Nothing tagged to the cycle and employee | Nothing; listed by review name in the report |

- **VIS-10 is not weakened.** Rows go straight into the table with `db_insert`, once, only for a
  review with no copies. The Extension's guard is not touched; a test proves a backfilled
  Completed review still refuses a change through the review record.
- **Safe to run twice:** a review with any copy, or with `items_taken_on`, is skipped.
- **Commits every 50 reviews; a savepoint per review;** a failure is logged by review name.
- **Not done by the copy (declared):** R16 (an item held by another open review is not added to a
  second review), additional reviewer ratings (0 rows on ppj), and a recount of open reviews —
  that happens on their first open, by design.

## 4. Requirements and decisions → test → result

All in `alvoraa_portal.tests.test_review_outside_010d`. Result is the last run on `test_site`
(27 tests, OK).

| Requirement / decision | Test | Result |
|---|---|---|
| SEC-2 (JSON) | `test_sec2_rating_fields_sit_at_level_1_and_nobody_is_given_write_there` | pass |
| SEC-2 (every path: desk/REST as creator, manager, HR Manager, System Manager; code with and without `ignore_validate`; Administrator; new rated KPI; additional reviewer row; a fact still saves) | `test_sec2_nobody_writes_a_rating_on_a_live_kpi_by_any_path` | pass |
| SEC-2 static | `test_sec2_static_no_code_writes_kpi_ratings_around_the_document` | pass |
| PRIV-9 (desk/REST read) | `test_priv9_only_hr_reads_the_old_ratings_on_a_live_kpi` | pass |
| Decision 26, self-assessment save | `test_decision26_employee_reads_appraisals_only_through_the_portal` | pass |
| R8, VIS-12 desk labels | `test_r8_vis12_desk_lists_say_they_are_live_records` | pass |
| R14, PRIV-9 (11 outside payloads, 3 viewers) | `test_r14_priv9_outside_payloads_carry_no_objective_or_kpi_rating` | pass |
| PRIV-9, decision 3 (totals) | `test_priv9_the_appraisal_summary_has_no_item_score_and_totals_follow_the_release_rule` | pass |
| VIS-3 for `get_cycle_items`, PRIV-2, company scope | `test_vis3_get_cycle_items_uses_the_copies_once_the_caller_may_open_the_review` | pass |
| R5, PRIV-10 | `test_r5_priv10_the_badge_says_in_review_and_the_period_end_and_nothing_else` | pass |
| SEC-26 (company and stage on 5 HR screens) | `test_sec26_hr_cycle_screens_list_only_permitted_companies_and_follow_the_stage` | pass |
| R8, SEC-26, R10, VIS-3 (CSV; log line with counts, no values) | `test_r8_sec26_the_csv_export_holds_copies_only_what_the_stage_allows_and_logs_counts` | pass |
| PRIV-1, SEC-26 (own row) | `test_priv1_sec26_your_own_row_on_hr_screens_never_carries_potential` | pass |
| SEC-26, SEC-6, SEC-30 (reminder, archive, sign-off) | `test_sec26_sec30_reminders_archive_and_sign_off_stay_inside_hrs_companies` | pass |
| NFR: HR screens do not grow with reviews | `test_query_count_hr_cycle_screens_do_not_grow_with_the_number_of_reviews` | pass |
| Decision 28 | `test_decision28_hr_opens_an_employee_scorecard_only_in_its_companies_and_managers_keep_their_line` | pass |
| SEC-7, decision 2 (picker) | `test_sec7_decision2_the_picker_finds_the_reviewed_persons_company_not_only_the_managers_line` | pass |
| SEC-7 (invitees) | `test_sec7_invitees_must_belong_to_the_reviewed_persons_company` | pass |
| Decision 17 | `test_decision17_an_invited_reviewer_loses_access_once_manager_review_ends` | pass |
| R9, SEC-22, PRIV-15 (day 15, not 16, day 22; own companies; no names) | `test_r9_hr_is_reminded_on_day_15_then_weekly_without_names_and_only_for_its_companies` | pass |
| R9 (released lock, 0 = never) | `test_r9_no_reminder_once_the_lock_is_released_and_0_means_keep_reminding` | pass |
| R9 scheduler line | `test_r9_the_reminder_runs_daily_from_the_goals_app` | pass |
| Backfill dry run changes nothing and counts right | `test_backfill_dry_run_counts_and_changes_nothing` | pass |
| Backfill: history as stored, open reviews, draft re-key, twice = once, VIS-10 kept, first open recounts and flags | `test_backfill_copies_history_as_stored_and_open_reviews_once_and_keeps_completed_copies_locked` | pass |
| Rollback helpers | `test_backfill_undo_leaves_changed_reviews_and_ratings_go_back_before_a_rollback` | pass |
| Patch line last; tables synced first | `test_backfill_patch_is_listed_last_and_syncs_its_tables_first` | pass |
| Decision 22 pin kept (now no Employee row at all) | `test_review_copies_010d.test_decision22_employee_cannot_write_or_create_an_hrms_appraisal` (updated) | pass |
| SEC-16 ceilings (`performance_api.py` 64, `review_backfill.py` 0) | `test_portal_security_010.TestSec16IgnorePermissionsCeiling` | pass |
| Decision 26, M3 report lists a tenant read grant on Appraisal | `test_decision26_m3_report_lists_a_tenant_read_grant_on_appraisal_and_changes_nothing` | pass |

**Where the documents differed, and what I followed:**

- **PRIV-10 vs 00d §6.5 badge text:** 00d's badge showed the cycle label and "numbers closed";
  PRIV-10 forbids the freeze state. I built PRIV-10's narrower payload (in review + the period
  end). The tree's existing `in_cycle` tag still carries the cycle name the item is tagged to,
  which anyone who sees the live record could already see.
- **OQ-D12 (live record id in HR's CSV):** 01d VIS-3 says `source_name` never leaves the server.
  Not added; HR cannot match a CSV row to a live KPI by id.
- **00d §6.7 "removed rows left out of HR screens" vs "Removed column":** removed copies are left out
  of every HR screen except the CSV, where manager and HR viewers see them marked Removed.
- **R9 with 0 days:** 00d does not say. Built as "keep reminding weekly" (question 1).
- **SEC-26 counts:** 01d allows status and counts before HR Review. I also left out the "rated"
  counts there, because a count of manager-rated items shows how far a manager has got (fail closed).

## 5. Non-functional dimensions, re-checked on the code written

| Dimension | Before → after | Verdict | Why |
|---|---|---|---|
| Performance | per-row queries on HR screens | **improves** | HR screens run a fixed number of queries whatever the cycle size (tested: 2 and 7 reviews give the same counts). The calibration overview no longer loads each review record; the appraisals table no longer runs 3 queries per row; the matrix no longer reads each employee. Cost: one extra query on the tree, My KPIs, team KPIs and goal detail (the badge), one on `list_appraisals` |
| Security | ratings writable and readable on live KPIs; HR screens unscoped; picker open to all | **improves** | SEC-2, SEC-7, SEC-26, SEC-30, PRIV-9, decisions 26 and 28 closed and pinned. `ignore_permissions`: `performance_api.py` 68 → 64 (ceiling lowered); no new use elsewhere |
| Reliability | self-assessment save broken since phase 1 | **improves**, one risk | Save fixed. The backfill is safe to run twice and isolates failures. Risk: the reminder job runs daily for every open review (one query, bounded by open reviews) |
| Scalability | HR screens N+1 | **improves** | Measured at 806 reviews: backfill 15.1 s, dry run 1.4 s. HR screens: constant query count; child rows read by indexed `parent` |
| Maintainability | — | **neutral** | One field rule (`rating_fields_for`) now serves both review and HR screens, replacing duplicated logic. A new module for the backfill. `review_items.py` is now about 1,750 lines (still worth splitting after group D ships) |
| Data integrity | live ratings could change | **improves** | Live ratings frozen as legacy; existing reviews get a replayable record; undo refuses to touch reviews changed since |
| Compliance / privacy | potential and ratings on outside screens and exports | **improves** | Potential and ratings leave every outside payload; HR exports follow stage and company; export and refusals are logged with counts and names only; reminder has no names |

**Query counts (measured on `test_site`, second call, caches warm):**

| HR screen | 2 reviews | 7 reviews |
|---|---|---|
| `hr_list_appraisals` | 7 | 7 |
| `hr_list_kpis` | 6 | 6 |
| `hr_cycle_summary` | 6 | 6 |
| `get_calibration_overview` | 7 | 7 |
| `get_calibration_matrix` | 9 | 9 |
| `export_cycle_kpis_csv` | 7 | 7 |

Response times of the HR screens at a large cycle were not measured; only query counts.

**Backfill timing (measured on `test_site`, commits off, rolled back, 0 records left):**

| Step | Result |
|---|---|
| Synthetic data | 806 reviews (403 Completed, 269 Employee Review, 134 Manager Review), 3,467 KPIs, 403 Objectives, one approved reading per KPI |
| `report()` | **1.43 s** |
| `run()` | **15.10 s**: 806 reviews, 3,870 copies, 0 failed (about 19 ms per review) |
| second `run()` | 0.52 s, 0 copied |
| **Projection for ppj (806 reviews, 3,510 KPIs, 212 + Q1 Objectives)** | about 15–20 seconds inside `bench migrate`, plus the commits every 50 reviews (a few seconds). ppj's real counts are close to the synthetic set |

**Indexes added:** none (reads use `tabAlvoraa Review Item.parent` and `source_name`, and the KPI
indexes from phase 1).

**Sensitive fields touched:** KPI self, manager and potential ratings and comments (now level 1,
HR-read only); appraisal totals (release rule); HR screens' ratings (per viewer); invitee list.

## 6. Commands run and real results

All on `hrlocal-bench`, site `test_site`, one run at a time (`pgrep` first; work board marked).

| When | Command | Result |
|---|---|---|
| Before every commit | `python scripts/check_app_integrity.py` | "OK - all consistent" (542 checks) |
| Before migrate | `bench --site test_site execute alvoraa_goals.review_backfill.report` | Output in section 7: `test_site` has no review records |
| After commits 8–12 | `bench --site test_site migrate` | Done. Patch ran: "Review copies: 0 reviews, 0 copies, 0 failed" (0.9 s). KPI level-1 fields and Appraisal permissions checked in the database afterwards |
| Then | `--module alvoraa_portal.tests.test_review_outside_010d` | 26 tests, OK (first run) |
| Then | `--module …test_review_copies_010d`; `--module …test_review_screens_010d` | 34 tests, OK; 29 tests, OK (plus its separate 1-test class, OK) |
| Then | timing probe through the bench's Python, commits off, rolled back | section 5 |
| End of phase (at `926369e`) | full `--app alvoraa_portal` | 495 tests: 1 failure + 3 errors. 441 tests: 1 failure + 10 errors. Checked name by name: `test_leave_year` 3 and `test_invoicing` 11 known; the other failure is slice 012's (see short answer) |
| End of phase | full `--app alvoraa_goals` | 18 tests, OK (2 skipped) |
| After `5100f83`, `9c6d97b` (brought into `dev`) | the ceiling test; the two M3 report tests | 1, 1, 1 tests, OK |

**Migrations and patches run:** `bench --site test_site migrate`, once. It ran
`alvoraa_goals.patches.v1_0.take_review_copies` on `test_site` (0 reviews there). Nothing else was
migrated. `ppj.localhost` was not touched.

## 7. The dry-run report output

On `test_site` before its migrate (it has no review records):

```
{"reviews": 0, "by_cycle_and_stage": {}, "will_copy": {"reviews": 0, "items": 0, "completed": 0, "open": 0,
 "open_already_frozen": 0}, "items_per_review": {"average": 0, "most": 0}, "skipped": {},
 "cannot_copy_nothing_tagged": {"completed": [], "open": []}, "reviews_with_no_period": 0,
 "rated_items_copied": 0, "approved_facts_dated_outside_the_review_period": {},
 "open_items_whose_number_changes_on_first_open": 0, "rating_questions_expected_on_first_open": 0,
 "draft_keys_dropped": 0, "cumulative_kpis_whose_readings_look_like_running_totals": 0,
 "extensions_missing_employee_or_cycle": 0, "kpi_additional_reviewer_rows": 0,
 "custom_docperm_rows_to_look_at": []}
```

On the 806-review synthetic set (timing probe, rolled back):

```
reviews 806; will_copy {reviews 806, items 3870, completed 403, open 403, open_already_frozen 0};
items_per_review {average 4.8, most 6}; skipped {}; open_items_whose_number_changes_on_first_open 201;
rating_questions_expected_on_first_open 0
```

(The 201 are the synthetic open reviews' Objectives: stored progress 5, no approved evidence, so
their first open counts 0. On a real tenant the report shows the true number before migrate.)

## 8. Tenant steps and deploy notes (not done by me)

- **Every tenant needs `bench migrate`:** KPI JSON (level-1 rating fields), HRMS Appraisal JSON
  (no Employee row), the patch, the scheduler entry.
- **Before each tenant's migrate, on your word (read-only):**
  `bench --site <site> execute alvoraa_goals.review_backfill.report`. Look at
  `cannot_copy_nothing_tagged` (history that cannot be rebuilt), `rating_questions_expected_on_first_open`,
  `cumulative_kpis_whose_readings_look_like_running_totals` and `custom_docperm_rows_to_look_at`.
  Decision 24's M3 check is included in it.
- **Tenants with a Custom DocPerm on KPI or Appraisal** keep their own permissions: a Custom
  DocPerm replaces our JSON. The report lists any grant to a role that is not HR on Appraisal
  (read included, since `9c6d97b`) and on KPI level 1. ppj has its own Appraisal Custom DocPerm
  (System Manager only), which is already stricter.
- **The patch prints one line** ("Review copies: N reviews, N copies, N failed") and takes about
  15–20 seconds on ppj's volume.
- **Rollback, in order, on your word:**
  1. `bench --site <site> execute alvoraa_goals.review_backfill.copy_ratings_back_for_rollback --kwargs "{'dry_run': 1}"`,
     then with `0` — only if ratings were given in the portal after go-live.
  2. `git revert` of group D, deploy, `bench migrate` (KPI fields go back to level 0; the Appraisal
     Employee row comes back).
  3. Optionally `undo_backfill` (dry run first). The copy table itself is harmless if left.
- **Do not deploy phase 3 without phase 4.** The page still reads rating keys that are now gone.

## 9. Known gaps and shortcuts — honestly

1. **The page is not updated** (commit 11, phase 4): see the short answer. Also: the CSV has new
   columns at the end; `hr_list_kpis` needs a cycle (no page caller); calibration rows now leave
   out keys instead of blanking them, and the page must not assume they exist.
2. **`hr_api.get_goal_detail` still lets any HR role open any company's goal.** Same hole as
   decision 28, in a function decision 28 did not name. Not changed. Question 2.
3. **The new-appraisal projection** (`hr_generate_appraisals`, API only) still reads the legacy
   `manager_rating` on live KPIs for its first score. No page calls it.
4. **A skip-level manager with no direct reports** finds nobody in the reviewer picker until the
   page sends the review (phase 4).
5. **A desk user who edits a KPI rating sees no error**: Frappe silently resets a level-1 field
   they may not write. The value does not change. Only code and Administrator get the refusal.
6. **The reminder relies on the Notification Log's own email**, which follows each person's
   notification settings; someone who turned those emails off sees the reminder only in the bell.
7. **Backfill limits:** no R16 second copy; history's "facts approved after close" (R10) counts
   facts approved after the copy was made, against numbers that were stored rather than counted;
   `undo_backfill` deletes copy rows directly (an operator script, not a user path — the one
   delete PRIV-14 did not foresee).
8. **Found and fixed in this phase:** the M3 report checked Appraisal for write only; a tenant
   read grant would have kept appraisal scores open unseen. Fixed in `9c6d97b`, pinned.
9. **`save_calibration_note` still fails** on the missing `calibration_notes` column (phase 1 gap 5).
10. **No browser trace** (no page change in this phase). **HR screen response times at scale were
    not measured**; only query counts and the backfill.
11. **SEC-15 revert proof not done** (the bench runs `dev`).

## 10. Decisions needed

1. **Reminder with lock release 0 (never):** keep reminding HR every 7 days while those reviews
   stay open (as built), or send no reminder when the lock never releases?
2. **`hr_api.get_goal_detail` HR company scope** (gap 2): fix inside 010, or separately?
3. Still open from phase 2, unchanged in phase 3: removal stages; whether an agreed Objective
   target change should pass the "no target change after progress" rule on write-back; emailing
   the employee about an overall rating change only once released.

## 11. What phase 4 must do next (commit 11 and the page items)

- **Commit 11, the review screens:** keys are row names; Remove / Delete / Edit on copies with the
  §6.4 warning and a reason box; the manager screen's flags (Keep/Change), removed rows, change
  markers and late facts for HR; the blocked-completion message; Save draft sends only ratings set.
- **Outside screens:** render `review_badge` ("In review · updates dated after <date> do not change
  it") in the tree, goal drawer, goal detail panel and KPI log dialog; stop drawing goal-row scores
  and the team "rated" count; handle `None` totals as "not released yet".
- **Reviewer picker:** send `appraisal` from both call sites.
- **HR screens:** handle absent rating keys in calibration rows; the CSV's new columns.
- **Future Objectives page:** "Remove" unticks instead of deleting (decision 19).
- **Decision 1** KPI dialog wording, **decision 2** reading date, **decision 23** portal Org
  Settings for the three settings (HR Settings, not `set_org_setting`, which slice 012 limited).
- Static page checks (`check_portal_handlers.js`, `check_undefined_js.js`), whole suites, a browser
  trace at 200% zoom and 360 px, and the notes.
- Before starting: fetch `origin/dev`, read the work board, rebase.

---

# Phase 4 — commit 11, the page items, and the last of the decisions

## The short answer

The page now speaks the review's own copies, and group D is complete on the local
instance. Five commits: the KPI reading date and the review-settings endpoints
(decisions 1, 2, 23), the page itself, its pin tests, a test-fixture fix and the
manager's "fill empty ratings" button.

Three things are worth calling out.

1. **Buttons that used to destroy data are gone.** "Remove" in a review deleted the
   Objective or the KPI itself — on the Future Objectives page it could delete an
   objective from an earlier cycle, taking its history with it. It now takes the
   item out of the review and leaves the record alone (decision 19, R12). Rating a
   KPI outside a review is gone with its dialog (R14).
2. **The manager can now do their job inside the review.** Item ratings, a rating
   question to keep or change, a definition change, a removal with a reason. None of
   it was reachable from the page before this commit; the endpoints existed from
   phase 2 with nothing to call them.
3. **Nothing of slice 012's was lost.** Six more 012 commits landed in local `dev`
   while this phase was building, one of them in `hrms-employee.html`. The rebase was
   clean and both changes are in the file; §2 names them and shows the proof.

## 1. Commits

| Commit | What it does |
|---|---|
| `bc29257` | A KPI reading can name the day it is for; HR reads and saves the three review settings (decisions 1, 2, 23) |
| `d2e7949` | The portal's review screens work on the review's own copies — commit 11 |
| `0a070b6` | 26 pin checks on the page, so a merge cannot drop any of it |
| `6269cf4` | Test fixture fix: the reading-date tests use a KPI whose period is around today |
| `7ec35e0` | The manager's "fill empty ratings from attainment" button, reading the copies |

All five are on `slice/010-portal-security-fixes` and in local `dev` by
`git merge --ff-only`. **Nothing is pushed.**

## 2. What came in from others

Slice 012 pushed six commits into local `dev` between phase 3 and the end of this
phase. The slice branch was rebased onto them before testing.

| Commit | Files | Overlap with 010 |
|---|---|---|
| `18e9f7a` | `subscription.py` | none. This is the `test_invoicing` failure phase 3 reported to slice 012; it is now fixed by them |
| `4de5423` | `data_review.py`, `test_morning_checks_edges_012.py` | none |
| `502bddf` | `attendance_analytics.py`, `test_attendance_scope_012.py` | none |
| `0f1a3ea` | `test_leader_indexes_012.py` | none |
| `3a8850a` | `hr_api.py`, `hrms-employee.html`, two 012 tests | **the page.** One line added inside `loadPortalContext` |
| `a6e38db` | `test_attendance_scope_012.py` | none |

**The page was the only shared file, and the rebase applied with no conflict.** The
two changes are in different functions, hundreds of lines apart. Proof that both
survived, run on the rebased tree:

    grep -c "drSetBadge(ctx.review_open_count" hrms-employee.html   -> 1   (012's line)
    grep -c "riOpenRemove" hrms-employee.html                       -> 5   (010's block)
    grep -c "riLoadSettings()" hrms-employee.html                   -> 1   (010's Org Settings)

and the page's two static checks pass on the rebased file.

Earlier phases' incoming work is in the phase 1, 2 and 3 sections.

## 3. What was built, file by file

| File | Mechanism | What changed |
|---|---|---|
| `alvoraa_portal/performance_api.py` | extend | `_reading_date` and `log_kpi_progress(..., log_date=None)`: a reading may name its day. Blank means today; the day must be real, not in the future, and not before the KPI's period — or, with no period, not more than a year back. A cumulative reading now **adds** to the live number instead of replacing it, because the box asks for the amount since the last update (decision 1). This matches what the review has always counted: `_numbers_for` sums cumulative readings. New `get_review_settings` / `save_review_settings`: HR reads, an HR Manager saves, through the `HR Settings` document so the change keeps its history (SEC-28). `get_team_reviews` also returns `rating_needs_answer`, and never on the person's own row |
| `alvoraa_portal/www/hrms-employee.html` | extend | The page. One new block with its own `ri…` prefix and two new dialogs; every other change sits inside an existing function. No renames, no moves, no re-indent. Details below |
| `alvoraa_portal/tests/test_review_screens_010d.py` | extend | Eight new checks: the reading date (four) and the review settings (four), including the refusals |
| `alvoraa_portal/tests/test_review_page_010d.py` | build | 26 checks that read the page and fail if one of this slice's fixes goes missing |

### The page, area by area

| Area | Change |
|---|---|
| New `ri…` block | `riIndex` (the copies on screen, by row name), `riOpenEditItem` / `riSaveEditItem` (R2, decision 6), `riOpenRemove` / `riSwitchToDelete` / `riConfirmRemove` (R12, decisions 9, 10, 29), `riSaveItemRating`, `riSuggestRatings`, `riAnswerFlag` (R7, decisions 12, 13), `riReviewBadge` (R5), `riRemovedHtml`, `riReviewNotesHtml`, `riLoadSettings` / `riSaveSettings` (decision 23), and four small helpers that decide what to offer at each stage |
| Wizard, past objectives | Keys were already row names; what was missing were the controls. Edit and Remove now appear by stage and part, not by whether the self-assessment boxes are open. The manager gets a rating, a comment, a potential box and the flag answer per item. Removed items are listed struck through, with who, when and why. The "Update actual progress" box is gone: the number comes from approved facts and the page says so |
| Wizard, future objectives | "Edit" and "Remove" removed. Unticking the box is the whole of "do not carry this on" (decision 19). The old Remove deleted the Objective, including one from an earlier cycle |
| Add/remove dialog | Names, statuses, units and periods escaped (SEC-11, they were raw). Unticking now warns before it removes, and sends the acknowledgement the server asks for |
| Manager and HR | "Rate & Submit" carries the overall rating question. HR's "Finish Review" says how many ratings are waiting and is switched off until they are answered, instead of failing on the click |
| Reviews list | "Rating needs your answer" on the rows that need one |
| Reviewer picker | Both call sites send `appraisal`, so a skip-level manager searches the reviewed person's company (SEC-7) |
| Badges outside the review | `tvCycleTag` takes the `review_badge` the server sends. Drawn in the tree, the goal drawer, the goal detail panel and the KPI update box. Text: "In review · updates dated after 30 Sep 2026 don't change it". No review name, no rating, no link (R5) |
| No ratings outside | `pfOpenSelfRating`, `pfSubmitSelfRating`, `pfSaveRating`, `pfSuggest` and the self-rating dialog deleted — their endpoints refuse now. The appraisal screen's KPI table keeps the items and their weights and points to the review for the ratings; a score that has not been released says "Not shared yet" instead of a dash that reads like zero (decision 3) |
| KPI update box | "Amount since your last update" for a cumulative KPI, "The reading now" for an absolute one (decision 1), plus a date field that cannot be set past today (decision 2) |
| Org Settings | A "Performance reviews" card with the three settings, each with its own label. An HR User sees them read-only; only an HR Manager gets the save button |
| One bug found on the way | `prOpenReview` never cleared `_pr.viewerRole`. A manager who had opened someone else's review earlier in the same session was still treated as a manager on their own review screen. Fixed |

## 4. Requirements and decisions → test → result

| Rule | Test | Result |
|---|---|---|
| Decision 1, R4 | `test_decision1_a_cumulative_reading_adds_up_and_an_absolute_one_replaces` | pass |
| Decision 1 wording | `test_decision1_the_box_asks_for_the_amount_since_the_last_update` | pass |
| Decision 2 | `test_decision2_a_blank_date_means_today_and_a_chosen_day_is_kept` | pass |
| Decision 2, refusals | `test_decision2_a_future_day_or_a_day_before_the_period_is_refused` | pass |
| Decision 2, no period | `test_decision2_a_kpi_with_no_period_accepts_a_year_back_and_no_more` | pass |
| Decision 2, page | `test_decision2_the_box_offers_the_day_the_reading_is_for` | pass |
| Decision 23, SEC-28 | `test_decision23_an_hr_manager_reads_and_saves_the_three_settings` | pass |
| Decision 23, bad values | `test_decision23_a_value_outside_the_list_is_refused` | pass |
| SEC-28, employee | `test_sec28_an_employee_cannot_read_or_change_the_review_settings` | pass |
| SEC-28, HR User | `test_sec28_an_hr_user_reads_the_settings_but_only_an_hr_manager_saves_them` | pass |
| Decision 23, page | `test_decision23_the_three_settings_have_a_labelled_field_each`, `test_decision23_the_card_loads_with_the_screen_and_saves_through_hr_settings`, `test_sec28_an_hr_user_who_cannot_save_is_not_offered_the_button` | pass |
| R14 | `test_r14_the_page_has_no_way_to_rate_a_kpi_outside_a_review`, `test_r14_the_appraisal_screen_shows_no_item_rating_and_no_zero_score` | pass |
| Decision 3 | `test_decision3_a_score_that_is_not_shared_yet_says_so` | pass |
| R5 | `test_r5_the_badge_says_what_it_means_and_carries_nothing_else`, `test_r5_the_tree_the_drawer_the_detail_and_the_log_box_all_draw_it` | pass |
| R11, R12 | `test_r11_r12_remove_no_longer_deletes_the_objective_or_the_kpi`, `test_r12_the_warning_says_what_is_lost_and_what_is_kept` | pass |
| Decision 10 | `test_decision10_a_reason_is_required_of_everyone_but_the_subject`, `test_decision10_removed_items_are_shown_with_who_when_and_why` | pass |
| R2, decision 6 | `test_r2_decision6_edit_changes_the_copy_not_the_live_record` | pass |
| Decisions 6, 29 | `test_decision6_decision29_the_page_offers_each_action_only_at_its_stage` | pass |
| R7, decision 12 | `test_decision12_the_manager_can_keep_or_change_a_flagged_rating`, `test_r7_the_reviews_list_says_a_rating_needs_an_answer` | pass |
| Decision 13 | `test_decision13_a_self_rating_question_is_information_only` | pass |
| SEC-23 | `test_sec23_hr_cannot_finish_while_a_rating_waits_for_an_answer` | pass |
| VIS-3 | `test_vis3_review_screens_key_everything_by_the_copys_row_name` | pass |
| R3 | `test_r3_progress_is_never_typed_into_a_review` | pass |
| PRIV-1 (own review) | `test_a_manager_opening_their_own_review_is_not_treated_as_a_manager` | pass |
| Decision 19 | `test_decision19_carrying_forward_has_no_delete_button_at_all` | pass |
| SEC-11 | `test_sec11_the_add_remove_dialog_escapes_every_name_it_draws`, `test_sec11_removal_reasons_and_flag_text_are_escaped` | pass |

Phases 1 to 3 keep their own tables above; all of those tests still pass.

## 5. Non-functional dimensions, re-checked on the code written

| Dimension | Before phase 4 | Verdict | Why |
|---|---|---|---|
| Performance | The page reloaded the whole review after every small change | **neutral to improves** | `riReload` makes one call, the same one the screen already makes. No new endpoint runs in a loop. `get_team_reviews` gained one field on a query it already ran, so no extra query. `get_review_settings` is three single-value reads on a Single doctype |
| Security | Endpoints were closed in phases 1 to 3; the page still offered buttons that led to refusals, and some that destroyed data | **improves** | Rating outside a review is unreachable, not merely refused. Every ri* control is hidden unless the server would allow it, and the server still decides. The settings write goes through the `HR Settings` document with the caller's own permission, so it is refused for an HR User and recorded for an HR Manager |
| Reliability | "Remove" deleted a live Objective, including one from an earlier cycle | **improves** | Nothing on a review screen deletes a live record except the explicit delete of something created inside the review, which the server already guards. HR's "Finish" is switched off rather than failing on the click. A reading dated wrongly is refused with a sentence that says what to do |
| Scalability | — | **neutral** | No new query grows with headcount or with the number of items |
| Maintainability | Review controls were scattered through the wizard | **improves** | One `ri…` block holds every change to a copy, with four small functions that answer "may this person do this now". The old dead handlers are deleted rather than left to rot. 26 page checks pin it |
| Data integrity | The live KPI number replaced itself with each reading, while the review summed them | **improves** | The two now agree: a cumulative reading adds, an absolute one replaces unless it is back-dated behind a reading already logged. A reading cannot be dated in the future or before the KPI's period |
| Compliance / privacy | A manager's own review could be drawn with manager controls; names and reasons from copies went into the add/remove dialog raw | **improves** | `_pr.viewerRole` is cleared when a person opens their own review. Everything drawn from a copy or a removal is escaped. The badge outside a review still carries no rating, no review name and no link |

## 6. Commands run and real results

Every command below was really run, and its real result is reported. The bench runs
the main checkout on `dev`, so the slice branch was rebased on local `dev` and brought
in with `git merge --ff-only` before each run. This slice's row on the work board was
marked "bench in use" for the whole of it, and released afterwards. One run at a time.
**No migrate was needed:** phase 4 adds no field and no doctype, and `test_site` was
already migrated in phase 3.

**The static page checks** (on the rebased page, after the last page commit):

    node scripts/check_portal_handlers.js .../hrms-employee.html
      -> ok   hrms-employee.html
         portal handlers: all reachable and callable

    node scripts/check_undefined_js.js .../hrms-employee.html
      -> ok   hrms-employee.html
         undefined identifiers: none

    python scripts/check_app_integrity.py
      -> app integrity: 558 checks
         OK - all consistent

`check_app_integrity.py` was run before every commit and said "OK - all consistent"
every time.

**The new page pin tests:**

    bench --site test_site run-tests --module alvoraa_portal.tests.test_review_page_010d
      -> Ran 26 tests in 0.923s
         OK

**The review-screen suite, phases 2 to 4 together:**

    bench --site test_site run-tests --module alvoraa_portal.tests.test_review_screens_010d
      -> Ran 39 tests in 326.720s
         OK
      -> Ran 1 test in 5.673s          (the static lock scan, run as its own category)
         OK

The first run of that suite had 2 errors, both in the new reading-date tests and both
my fixture's fault: the KPI was built inside a far-future cycle, and a KPI with no
period of its own takes its cycle's, so every reading dated today was before the KPI's
period and refused. Commit `6269cf4` fixes the fixture. **No production code changed
because of it.**

**The whole `alvoraa_portal` suite**, run sequentially after it:

    bench --site test_site run-tests --app alvoraa_portal
      -> Ran 538 tests in 925.368s     FAILED (errors=3, skipped=4)
      -> Ran 527 tests in 1382.220s    FAILED (failures=1, errors=10)

Fifteen tests did not pass. **All fifteen are the known local-only failures, compared
by name:**

| Where | What | Ours? |
|---|---|---|
| `test_leave_year` | 3 errors: `test_uses_the_fiscal_year_when_one_exists`, `test_a_date_before_the_fiscal_year_start_belongs_to_the_previous_one`, `test_falls_back_to_the_calendar_year_when_no_year_covers_the_date` | No. Fiscal-year set-up on this bench, older than slice 010 |
| `test_invoicing` | 1 failure and 10 errors, all named after invoices, charge lines, annual fees and headcounts | No. Older than slice 010 |

Slice 012's `test_every_billing_doctype_is_named_as_control_plane_only`, which phase 3
reported as a new failure not on the list, **now passes**: slice 012 fixed it in
`18e9f7a`, which came in during this phase.

**The whole `alvoraa_goals` suite**, run after it:

    bench --site test_site run-tests --app alvoraa_goals
      -> Ran 18 tests in 3.388s
         OK (skipped=2)

**The `ignore_permissions` ceilings held**, unchanged by this phase:
`performance_api.py` 64 (ceiling 64), `review_items.py` 2 (ceiling 2).

## 7. The browser trace — written, not run

`C:/Surbhi-Git/hrlocal-data/mobile-audit/trace_review_copies_010d.py`.

It signs in as three real people on the local ppj copy — Vinod Gupta, an accountant;
Gurpreet Dhillon, the head of finance he reports to; and Arjun Bhatia, the head of HR
— and walks the whole review: the employee on an iPhone 13, the manager and HR on a
desktop window. It takes a screenshot per step, checks each screen for inputs without
a label and for sideways overflow, checks the review screens for a live record name
(the failure this whole slice is about), and checks the screens outside a review for
any rating. It repeats the self-review screen at 200% zoom.

**It is not run, because it writes to `ppj.localhost`.** To run it, two things need
the user's word:

    docker exec hrlocal-bench bash -lc \
      "cd /home/frappe/frappe-bench && bench --site ppj.localhost migrate"
    python C:/Surbhi-Git/hrlocal-data/mobile-audit/trace_review_copies_010d.py \
      C:/Surbhi-Git/hrlocal-data/mobile-audit/2026-09-16-review-copies

The migrate adds group D's fields and runs `alvoraa_goals`' `review_backfill` patch,
which takes a copy of the items of every review already open on that site. The trace
then sends a review and changes items. Neither touches dev or production. The logins
were read from `ppj.localhost` read-only; nothing was written there.

## 8. Release checklist for group D

*Corrected in the fix round (security review M5, code review M5). The first version
named two functions that do not exist (`dry_run`, `rollback`), said the permission
report covers Individual Goal, and left the rating copy-back out of the rollback.*

Group D ships as **one batch**, with its fix round. Phases 2 and 3 changed what the
review endpoints return; the page only caught up in phase 4. Shipping any part without
the rest leaves screens reading keys that are no longer there.

**Order, per environment:**

1. **Back up first.** A database dump of the tenant, kept until the release is
   accepted.
2. **Dry run, per tenant, read-only, before migrate.**
   `bench --site <site> execute alvoraa_goals.review_backfill.report`
   It changes nothing. Read: `will_copy`, `cannot_copy_nothing_tagged`,
   `reviews_with_no_period`, `open_items_counted_from_facts_differ_from_live`,
   `ratings_stamped_on_counted_numbers`,
   `cumulative_kpis_whose_readings_look_like_running_totals` and
   `custom_docperm_rows_to_look_at`. **Stop** if `cannot_copy_nothing_tagged.open` is not
   empty or `custom_docperm_rows_to_look_at` lists anything.
3. **Migrate.** `bench --site <site> migrate`. It adds the `Alvoraa Review Item` child
   table, the new review-record fields (including `lock_release_days` and, from
   decision 35, `calibration_notes` — without it portal calibration fails), the three HR
   Settings fields, the KPI rating permission level and indexes, and the
   "Cumulative KPI Readings Check" report. It runs two patches, in this order:
   `take_review_copies` (the backfill) then `stamp_lock_release_days`. Check the output
   line "Review copies: N reviews, N copies, 0 failed", and that the Error Log has no
   "Review copy backfill failed".
4. **Clear the cache** so the page, the desk list scripts and the report are served:
   `bench --site <site> clear-cache`. (Assets come with the deploy image.)
5. **The permission report, on every tenant (decision 24).**
   `bench --site <site> execute alvoraa_goals.review_items.custom_docperm_report`
   Read-only. It lists Custom DocPerm rows on `Alvoraa Appraisal Extension`,
   `Appraisal` and `KPI` (level 1 and above) that give a role other than HR a right.
   It does not look at `Individual Goal`. The Version, Comment and Appraisal row rules
   (fix round B1, M4) are code hooks, which a Custom DocPerm cannot switch off.
6. **HR runs "Cumulative KPI Readings Check"** in the desk for each company, and
   corrects readings that were typed as running totals, before relying on reviews.
7. **Check by hand on the deployed tenant** (05 section 8):
   an employee opens a review and sees items, and logs a KPI reading (label and date);
   a manager with no HR role and one who holds an HR role open Manager Review, rate an
   item, change a target, remove an item with a reason; the reviewer picker finds a
   name that sorts late; HR sees the three settings in Org Settings and the blocked
   completion message when a rating question is open; on one Cumulative KPI, log,
   reject, log again, and check the live number; for an employee with a cascaded KPI,
   open "Add/remove KPIs" and add one.

**Rollback, in this order, on the user's word.** Steps 1 and 2 need the group D code,
so they run **before** the image is rolled back.

1. **Put ratings back where the old code reads them** (only if ratings were given in the
   portal after go-live):
   `bench --site <site> execute alvoraa_goals.review_backfill.copy_ratings_back_for_rollback --kwargs "{'dry_run': 1}"`,
   read it, then the same with `{'dry_run': 0}`. Tell HR: the old code shows potential
   ratings on live KPIs to employees again (residual risk R9).
2. **Optional: remove the backfilled copies** from reviews nobody changed since:
   `bench --site <site> execute alvoraa_goals.review_backfill.undo_backfill --kwargs "{'dry_run': 1}"`,
   then `{'dry_run': 0}`. Reviews changed since are listed and kept. The copy table is
   harmless if left.
3. **Roll the code back:** redeploy the previous image (`dev-c27fb56` on dev), then
   `bench --site <site> migrate` (KPI rating fields go back to level 0; the Appraisal
   Employee row comes back). If that fails, restore the backup from step 1 of the
   release. **Roll the page and the server back together**, for the same reason they
   ship together.

**What to tell users**, before the release:

- A review now keeps its own copy of each objective and KPI, so the numbers it was
  decided on do not move afterwards.
- Ratings are given inside the review. The rating boxes on the Objectives screens have
  gone.
- "Remove" in a review takes the item out of the review. It no longer deletes the
  objective or the KPI.
- The KPI update box asks for the amount added since the last update, and lets you say
  which day it is for.

## 9. Commits on this branch that are NOT slice 010's

`slice/010-portal-security-fixes` is 57 commits ahead of `origin/dev`. **Twenty of them
belong to slice 012** and came in through local `dev`. A push of 010 must not carry
them unless slice 012 has said so.

`ed8732f`, `bdc50c0`, `b89cdfb`, `c692ea9`, `85f0073`, `e6bae5c`, `3c33d56`, `0fa5952`,
`bf79aad`, `96f3ef9`, `3e2f1e0`, `15a2dae`, `bda1290`, `05342a9`, `18e9f7a`, `4de5423`,
`502bddf`, `0f1a3ea`, `3a8850a`, `a6e38db`

The other 37 are 010's, from `e58ffa2` (the review-copies decisions) to `7ec35e0`.
Because the two slices are interleaved in local `dev`, **010 cannot be pushed on its own
by cherry-picking around 012.** Either both go together, with slice 012's agreement, or
012 pushes first and 010 rebases onto the pushed `dev`. This is the user's call.

## 10. Known gaps and shortcuts — honestly

1. **No browser trace was run.** Everything above was proved by the suites and by the
   page checks, which read the page as text. A real browser has not opened these
   screens. The script is written and ready; running it needs §7's approvals. This is
   the biggest gap in the phase.
2. **Response times were not measured.** No screen was timed against the NFR budget.
   The query counts are bounded and pinned by
   `test_query_count_opening_a_review_does_not_grow_with_its_items`, but a bounded
   query count is not a measured page.
3. **The cumulative KPI number changes meaning for data already there.** From now on a
   cumulative reading adds to the live number. Readings logged before this release were
   typed as "the total so far" by people reading the old label, although the review
   always summed them. The live number and the review's number may therefore disagree
   on old KPIs until someone logs a new reading. Nothing is lost — every reading is
   still there — but HR should know. This follows from decision 1; there is no
   migration that can tell the two intentions apart.
4. **The Future Objectives page still creates live records straight away** when someone
   adds a new objective from it, although the review's own submit creates next-period
   objectives with no cycle (decision 19). I corrected the sentence on the page so it
   no longer promises a cycle tag, and left the behaviour alone: it is outside commit
   11 and changing it is a product decision. **Worth a slice of its own.**
5. **`riSwitchToDelete` offers the outright delete only to the person whose review it
   is**, although the server allows a manager and HR to delete an item created inside
   the review. Narrower than the rule, never wider. Easy to widen later.
6. **The manager's per-item rating boxes save one at a time**, each with its own "Save
   rating" button. A manager with twenty items presses twenty buttons. One save for the
   whole page would be better and needs a server call that does not exist yet.
7. **One dead payload key remains:** the Future Objectives page filters
   `standalone_kpis` by `appraisal_cycle`, which copies no longer carry, so that "new
   KPIs" list is always empty. It renders nothing and breaks nothing. Removing it
   properly means deciding what that section is for.
8. **`prReviewKpiRow` still takes an `onRemove` argument it no longer uses.** Left in
   place on purpose: `hrms-employee.html` is the hottest file in the repo and changing
   a signature makes other people's merges harder for no gain.

## 11. Decisions needed

None about the design. Every open question from phases 1 to 3 is answered in `00e`.
What the user must decide is a release question:

1. **Run the browser trace?** It needs `bench --site ppj.localhost migrate` plus the
   backfill patch, and it writes to that site (§7).
2. **How to push?** 010 and 012 are interleaved in local `dev` (§9). Both together, or
   012 first and 010 rebased onto the pushed `dev`.


---

# Fix round — code review (05) and security review (06)

## The short answer

**Every finding in both reviews is fixed and tested on the local instance, except
security M3, which waits for the user's decision. Nothing is pushed.**

- **28 commits**, this notes commit included, on `slice/010-portal-security-fixes`, brought into local `dev`
  with `merge --ff-only` (local `dev` at the notes commit).
- **39 new pin tests** in `alvoraa_portal/tests/test_review_fixround_010d.py`, all
  passing. Five existing tests were changed on purpose, where a fix changed the
  behaviour they pinned (listed below).
- **Full suites:** see "Commands run". Only the known local failures.
- **Three things you should know first:**
  1. **HR now sees less in the desk.** HRMS Appraisal records follow the review's
     stage and company rule (security M4). HR's desk list of Appraisals shows nothing
     for a review still before HR Review, unless it is in their own line. The portal
     screens are unchanged.
  2. **The live KPI number moves only when a reading is approved** (code review M2).
     Logging a reading no longer changes "currently at …%" until the manager approves
     it. Tell employees.
  3. **Open reviews are counted from dated facts at copy time** (release risk). The
     upgrade no longer raises a rating question on every open review with old
     ratings; the ratings are stamped on the counted numbers instead. That is the
     trade-off you asked for: nobody is asked about the change from the old live
     number to the counted number.

Commit hashes in some commit messages (`ecdb303`, `9351fec`) are from before the last
rebase; their commits are now `780021d` and `d782a98`.

## 1. What came in from others

At the start, the slice branch was rebased onto local `dev`. Nine commits came in, none
touching group D code: slice 012's last code and document commits up to `2db1d71`,
`18af278` (parallel-work rules, portal redesign plan), `24eb10a` (slice 012 documents)
and `6d0273f` (slice 012 F1: `hrms/alvoraa_org_structure/settings.py`, its test, and one
new row at the end of the `CEILINGS` table in `test_portal_security_010.py`). Before
testing, a second rebase brought in `c507030` (012 F1 notes, docs only). No conflicts.

F1 writes Version rows about `DefaultValue` (`settings.py:197`). The new Version row
rule (B1) touches only rows about `Alvoraa Appraisal Extension`, `Alvoraa Review Item`
and `Appraisal`, so those rows are untouched, and `test_org_access_settings_012f1` ran in
the full suite. The `CEILINGS` table was not edited in this round, so F1's row stays.

The main checkout holds another session's uncommitted edits
(`.claude/context/ux-learnings.md`, `backlog/KPI_AUTOMATION_BACKLOG.md`,
`hrms/.../alvoraa_position.py`, a deleted `OBJECTIVES_KPI_REQUIREMENTS.md`). None is in a
file this round changes; none was touched.

## 2. Each finding → what changed → test → result

"Test" names are in `test_review_fixround_010d.py` unless another file is named.

### Security review

| Finding | What changed | Pin test | Result |
|---|---|---|---|
| **B1** Version and Comment rows readable at any stage | `alvoraa_goals/permissions.py`: `version_query`, `comment_query`, `has_review_history_permission`, registered in `alvoraa_goals/hooks.py`. A Version or Comment row about a review record, one of its copies, or an HRMS Appraisal is readable only by someone who may read that record (same stage, company and "never your own" rule). Audit notes on the review record cannot be created, edited or deleted by hand below Administrator. Rows about any other doctype are untouched. **Chosen: row rules, not moving audit notes off Comment.** Frappe v16.33.1 applies app hooks for core doctypes in both list paths (`model/db_query.py:1159`, `database/query.py:1619`, AND-ed with Frappe's own) and in `has_controller_permissions` (`permissions.py:491`); the desk timeline loads comments only after the record's own read check. So the hook scopes them safely and change history for grievances stays. | `TestB1ReviewHistoryAndNotes` (4 tests: System Manager, Website Manager and HR at Manager Review; System Manager at HR Review; a System Manager's own review; ToDo history and notes still listed and read; hooks registered) | pass |
| **M1** three scoring calls open to any HR at any stage | `performance_api._require_scoring_access`, used by `suggest_ratings`, `sync_appraisal_from_kpis`, `submit_appraisal`: never the subject; the direct manager or HR; HR outside the line needs HR Review or Completed and a company it looks after; nobody before the self-review is sent | `TestM1ScoringCallsFollowTheStageAndCompanyRule` (3) | pass |
| **M2** a rename steps round the lock | `review_items.refuse_rename_while_held` (`before_rename`) and `follow_rename` (`after_rename`) on KPI and Individual Goal. A held record keeps its name; a later rename moves every copy's pointer (one query). Copies being robust matters because the lock can be released while a review is still open. | `TestM2RenameWhileHeld` (3) | pass |
| **M3** manager with an HR role does every step | **Not changed. On hold for the user's decision.** Code review M3 was fixed so that in HR Review an HR role holder still gets HR's controls exactly as before. | — | open |
| **M4** HR reads Appraisal scores in the desk | `permissions.appraisal_query` and `has_appraisal_permission` (hooked on `Appraisal`): read and write follow the review's stage and company rule and never your own; create needs a company the caller looks after; a submitted appraisal with no review record is history and readable. `permitted_companies()` gives HR with no Company user permission its own company only. | `TestM4HrmsAppraisalInTheDesk` (3) | pass |
| **M5** release checklist | §8 above rewritten from phase 3 §8, with real functions and the copy-back in the rollback, both before the image rollback | — (documentation) | done; **not rehearsed** |
| m1 lock release days live | New `lock_release_days` field on the review record, stamped with the others at first open and by the backfill; the lock and the HR reminder read each review's own value; patch `stamp_lock_release_days` after the backfill | `TestM1LockReleaseDaysStamped` (2); changed: `test_r9_sec22_…` (screens), `TestR9LockReminder._release_days` (outside), `test_backfill_patch_is_listed_last…` | pass |
| m2 approvers cannot see when a reading was typed | `logged_on` in `get_kpi_update_log`, `goals_api.get_goal_update_log` and `get_pending_approvals`; the update log shows "typed <date>" when it differs | `test_m2_approvers_see_when_a_reading_was_typed`, `test_m2_the_update_log_shows_when_a_reading_was_typed` | pass |
| m3 write-back note shows values to every reader | Live-record note names the review and fields only; values go to an audit note on the review record | `test_m3_the_live_records_note_names_fields…` | pass |
| m4 PRIV-14: no `on_trash`, no test | `AlvoraaAppraisalExtension.on_trash` refuses when copies exist, for everyone including Administrator and `ignore_permissions` | `test_m4_priv14_no_path_deletes…` | pass |
| m5 no PRIV-15 marker test | Marker in a title changed in the review, a removal reason, a comment and HR's answer reason; review run to completion with write-back; not in Error Log, Email Queue, Notification Log or the live record's notes | `test_m5_priv15_a_marker…` | pass |
| m6 static lock test sees `set_value` only | Also flags `db_set`, `frappe.db.sql` updates on `tabKPI`/`tabIndividual Goal` and `frappe.qb.update` on those doctypes, unless the function asks `holds()`; checks it really saw `db_set` and `sql` calls | `test_r2_static_no_code_writes_a_locked_field_around_the_lock` (screens) | pass |
| m7 HR-role line manager sees a draft's items | `_draft_hidden`: `hr_list_kpis` and the CSV skip a review in Employee Review for everyone but the subject | `TestM7HrScreensHideDraftItems` | pass |
| m8 HR approves any company's reading | `approve_kpi_update` and `approve_goal_update`: HR who is not the direct manager only for `permitted_companies()`; `get_pending_approvals` lists only those companies plus own direct reports | `test_m8_hr_approves_readings_only…` | pass |

### Code review

| Finding | What changed | Pin test | Result |
|---|---|---|---|
| **M1** dialog removes KPIs it never showed | `_selectable_items` lists every KPI that does not come with an Objective already in the review (cascaded ones included); `set_review_selection` removes only what that list holds | `TestCrM1SelectionRemovesOnlyWhatWasListed` | pass |
| **M2** rejected reading stays in the live number | `log_kpi_progress` no longer changes `actual_value`; `approve_kpi_update` moves it through `_move_live_number` (Cumulative adds on approval, takes off when an approval is reversed; Absolute takes the latest approved by date); attainment and Achieved/Missed follow on save | `TestCrM2LiveNumberMovesOnApproval` (approve, reject, reverse, same decision twice); changed: `test_decision1_a_cumulative_reading_adds_up…` (screens) | pass |
| **M3** manager with an HR role gets HR's view | `get_manager_review` sends `viewer_role: "manager"` to the manager for this review; `"hr"` for HR outside the line, and for an HR role holder in HR Review (unchanged, security M3) | `TestCrM3ManagerWithHrRole` | pass |
| **M4** reviewer picker: 50 names, never cleared | Page searches on the server as the person types (2 letters, 300 ms pause), drops stale answers, clears on opening a review; server returns nobody for fewer than 2 letters, after its permission checks, limit 50 | `TestCrM4ReviewerPickerSearchesTheServer` (2) | pass |
| **M5** | as security M5 | — | done |
| minor 1 Add Objective tags the cycle | No cycle stamped; KPI dialog from a review starts with no cycle; page text says what happens | `test_cr_minor1_…` | pass |
| minor 2 late facts and "dated by upload" not shown | `riFactsNote` for HR on each item | `test_cr_minor2_…` | pass |
| minor 3 "items not in your review" not built | `review_items.not_in_review_count`, `get_my_review.not_in_review_count` (subject, before sending), note in `riReviewNotesHtml` | `TestCrMinor3NotInReviewCount`, `test_cr_minor3_…` | pass |
| minor 4 UTC reading date | Local date for value and `max` | `test_cr_minor4_…` | pass |
| minor 5 item flags not on the Reviews list | `get_team_reviews` adds one query for flagged item ratings | `TestCrMinor5ItemFlagsOnTheReviewsList` | pass |
| minor 6 read screens save and conflict | `open_review` runs under a savepoint; on "document has been modified" it takes its attempt back, reloads and carries on (all review screens and writes use it) | `TestCrMinor6OpeningTogether` | pass |
| minor 7 submitted Objectives | `on_update_after_submit` refresh hook; locked fields on a submitted goal are closed by Frappe's own after-submit rule on every path (no locked field allows on submit), pinned | `test_m2_minor7_rename_and_after_submit_hooks_are_registered` | pass |
| minor 8 reason box hidden after cancel | `riOpenRemove` shows it every time | `test_cr_minor8_…` | pass |
| minor 9 `save_overall_rating` accepts 0 | Refuses 0 | `TestCrMinor9OverallRatingOfZero` | pass |

### Release risks (05 §8)

| Risk | What changed | Pin test | Result |
|---|---|---|---|
| Every open review raises rating questions on first open | Backfill counts open, unfrozen reviews from approved dated facts at copy time (facts loaded once for all reviews) and stamps ratings and the overall rating on those numbers; first open stamps an overall rating that has no stamp yet. `report()` keys renamed to `open_items_counted_from_facts_differ_from_live` and `ratings_stamped_on_counted_numbers` | `TestReleaseRiskOverallRatingStampedOnFirstOpen`; changed: two backfill tests (outside) — first open now asks nothing, a later fact still does | pass |
| Running-total readings | Script Report "Cumulative KPI Readings Check" (HR Manager, HR User; own companies; no ratings; read-only) | `TestReleaseRiskRunningTotalsReport` | pass |

## 3. Non-functional dimensions, re-checked on the code written

| Dimension | Before → after | Verdict |
|---|---|---|
| Performance | Version/Comment lists by a System Manager carry two to three subqueries; Appraisal read checks add 2–4 small queries per document; `get_team_reviews` +1 query; `get_my_review` +2 for the subject in draft; `open_review` +1 SAVEPOINT; picker now one small query per search instead of one 50-row load; backfill loads facts once | neutral |
| Security | B1, M1, M2, M4, m7, m8 close side doors; audit notes no longer editable by hand; picker returns nobody for short searches | improves |
| Reliability | Selection dialog no longer refuses or drops items; read screens no longer fail on a save race; live KPI number self-corrects on rejection | improves |
| Scalability | Everything bounded; backfill facts chunked by 500 | neutral |
| Maintainability | Two more hook pairs in `alvoraa_goals/permissions.py`; one new report; `review_items.py` a little longer | neutral |
| Data integrity | Live number counts approved readings only; each review keeps its lock days; copies follow renames; review records with copies cannot be deleted | improves |
| Compliance / privacy | History and notes follow the review rule; potential no longer readable by the subject through Version rows; live-record notes carry no values; PRIV-14 and PRIV-15 now tested | improves |

`ignore_permissions` counts unchanged: `performance_api.py` 64, `review_items.py` 2,
`goals_api.py` 15; the new code adds none.

## 4. Commands run and real results

Every command below was really run. One test run at a time, with this slice's row on the
work board marked "bench in use", after slice 012's F1 runs had finished.

    python scripts/check_app_integrity.py            -> OK - all consistent (before every commit)
    node scripts/check_portal_handlers.js            -> portal handlers: all reachable and callable
    node scripts/check_undefined_js.js               -> undefined identifiers: none
    bench --site test_site migrate                   -> completed (new field, patch, report)

    bench --site test_site run-tests --module alvoraa_portal.tests.test_review_fixround_010d
      first run  -> Ran 33 tests FAILED (failures=3, errors=3); Ran 6 tests FAILED (failures=2)
      second run -> Ran 33 tests in 249.688s OK; Ran 6 tests in 0.207s OK

The first run's eight problems were all in the new tests or a code comment, none in a
fix (commit `6326307`): HR roles hold no role on Version or Comment, so the B1 test
wrongly expected HR to list them; a removed copy was looked up with a helper that
raises; the "rater who left" was a made-up user in a Link field; `modified` compared as
a date against text; the picker test cut the page at the wrong place; the m2 page test
quoted the wrong half of a string; and a comment contained the word the reading-date
test looks for.

    bench --site test_site run-tests --app alvoraa_portal
      -> Ran 546 tests in 916.542s   FAILED (errors=3, skipped=4)
      -> Ran 572 tests in 1516.409s  FAILED (failures=1, errors=10)

Fourteen did not pass, **all the known local-only failures, compared by name**:
`test_leave_year` 3 errors (fiscal-year set-up on this bench) and `test_invoicing`
1 failure + 10 errors (invoices, charge lines, annual fees, headcounts). Every group D
suite (`test_review_copies_010d`, `test_review_screens_010d`, `test_review_outside_010d`,
`test_review_page_010d`, `test_review_fixround_010d`) and slice 012's
`test_org_access_settings_012f1` passed.

    bench --site test_site run-tests --app alvoraa_goals
      -> Ran 18 tests in 2.880s  OK (skipped=2)

**Not run:** a browser trace, and the release checklist rehearsal on ppj.localhost.

## 5. What is still open

1. **Security M3 is on hold** (a manager who also holds an HR role doing HR steps on
   their own report's review: calibrate, HR removal, HR flag answer, complete). No code
   changed; the user decides. Residual risk R4.
2. **Residual-risk rows need a name and a date** from the user before anything is
   accepted: R4 (M3), R7 (legacy ratings on live KPIs), R8 (tenant Custom DocPerm), R9
   (potential back on KPIs after a code rollback), R10 (no retention engine), R11 (logs
   in France), R12 (cumulative readings change meaning — now helped by the new report).
   R1, R2, R3, R5, R6 and R13 are fixed by this round and no longer need acceptance;
   R6's rehearsal is still to do.
3. **The release checklist has not been rehearsed** on ppj.localhost (release train gate
   2), and **no browser trace was run** for the page changes in this round. Both need the
   user's word.
4. **The HRMS desk Appraisal list now hides in-progress appraisals from HR** (M4). If HR
   used that list to watch progress, they should use the portal's HR screens.
5. **Counsel questions** C-D1, C-D3, C-D4 are unchanged.
6. **Not changed, from the reviews' "worries" and "what to delete"** (not asked for in
   this round): dotted-line managers' feedback form, the HR stand-in chosen by row order,
   departed employees with an enabled login, `save_calibration_note`'s missing column
   (F-D8), and the dead reviewer modal and `_scored_live_items` legacy rating.

# Decision 34 (M3) — the subject's line does not do HR's steps

## The short answer

**Security M3 is fixed, as the user decided on 2026-09-17: nobody in the
subject's reporting line does the HR steps on that review, even with an HR
role. A different HR person does them. Tested on the local instance. Nothing is
pushed.**

- **Two commits** plus this notes commit: `9cdc9d2` (the rule and the page),
  `d1252e8` (pin tests).
- **Things to know first:**
  1. **On ppj.localhost this touches 402 of the 403 open reviews**, because the
     managing director holds HR Manager and sits at the top of the tree. Every one
     of them still has **at least 8** other HR people who can do the steps. No
     open review is left with nobody (read-only count, below).
  2. **The HR stand-in counts as the manager.** For someone with no manager, the
     system already makes the first HR Manager their manager
     (`get_effective_manager`). That person does the manager steps, so they are
     refused the HR steps too. This goes one small step past "manager or above";
     say if you want it taken out.
  3. **Portal calibration is still broken for everyone** — the missing
     `calibration_notes` column (F-D8, raised before, not in this fix). The
     fail-without-fix run hit it.

## 1. What came in from others

Nothing. At the start the slice branch, local `dev` and the worktree were all at
`07b261d`, and `origin/dev` was still at `c27fb56`. Fetched again before the
commits: no change. The main checkout still holds another session's uncommitted
edits in files this fix does not touch; none was touched.

## 2. The rule, and where it is checked

**One shared check** in `hrms/hrms/alvoraa_hr_core/access.py`, next to
`refuse_own_rating`:

- `subjects_in_my_line(employees, user, stand_in)` walks `reports_to` upward from
  each subject, for all of them at once: one query per level, at most 50 levels,
  a loop ends that person's walk, and a line still going at 50 counts as "in the
  line" (fails closed). Every Employee record linked to the login counts as the
  caller. `stand_in` is a function, called at most once and only when a subject
  has no manager.
- `refuse_hr_step_in_line(employee, …)` refuses with *"You are in this person's
  reporting line, so you cannot do the HR steps on their review. Ask another HR
  person in <company> to do this step."* It names the company, never a person,
  and logs through `access.refuse` as rule **`D34`** (user, endpoint, doctype,
  document name — no values).

**Where it is used** (`performance_api.py`, all through `_refuse_hr_step_in_line`):

| HR step | Where | Note |
|---|---|---|
| Calibration and calibrated rating | `save_calibration_note` | after the own-review check |
| Complete (HR Review → Completed) | `advance_review_status`, HR Review branch | |
| Send back from HR Review | `return_for_revision`, when the stage is HR Review | not asked for by name; it is an HR-only decision in HR Review, so it is included. The manager's own send-back in Manager Review is unchanged |
| HR removal and deletion of items | `_review_actor`, for `remove_review_item` and `delete_review_item` | someone in the line was already refused here by accident (they count as "manager", and managers act only in Manager Review); now they get the D34 message and log line |
| HR's answer to a rating question | `answer_rating_flag`, the "rater has left" path | the rater answering for their own rating stays a manager step and is allowed |
| Desk: change the HRMS Appraisal | `alvoraa_goals.permissions.has_appraisal_permission` | from HR Review on, any non-read permission is refused to the line. Not logged: Frappe asks this hook for display as well as for a save. The review record itself was already closed to desk writes below Administrator |

**Not HR steps, so not changed:** `suggest_ratings`, `sync_appraisal_from_kpis`
and `submit_appraisal` (the line manager's scoring; security M1 already scoped
HR's use), `add_action_item` (manager or HR, not a decision), and the cycle-level
`save_calibration_signoff` (no single subject). The older `hrms/pms` review module
(PMS Calibration Session) is a separate system that group D does not use; not
touched.

**Reading is unchanged.** The line keeps the manager's view in every stage.

## 3. The page

The server sends `hr_steps_elsewhere` (1 when the caller holds an HR role, the
review is in HR Review and the caller is in the line) on `get_manager_review`,
`hr_list_appraisals`, `get_calibration_overview` and `get_team_reviews`. Each list
does one walk for all its HR Review rows, and none for a caller without an HR
role. In `get_manager_review`, such a caller now gets `viewer_role: "manager"` in
HR Review (it was `"hr"`, pinned by code review M3's test, changed on purpose).

In `hrms-employee.html`, a new `pfHrStepsElsewhereNote()` shows *"Another HR
person needs to do the HR steps for this review, because they report to you."*
(words and an icon, not colour alone) in place of:

- **Finish Review** in the team reviews table and the HR appraisal table (a
  **View** button stays);
- the calibration table's **Note** button;
- the **Finish Review** button on the Finalize page of the review screen, which
  now shows the manager's assessment read-only for the line.

With `viewer_role: "manager"` in HR Review, the item **Remove** buttons and the
HR reason prompt for rating answers no longer show for the line either.

## 4. Tests

New file `alvoraa_portal/tests/test_review_line_hr_010d.py` (10 tests), starting
from shipped permissions like the other 010 tests:

| Test | Proves |
|---|---|
| `test_d34_a_manager_with_hr_manager_is_refused_each_hr_step_and_each_refusal_is_logged` | calibration, removal, deletion, both flag answers, send-back and completion are refused to the manager with HR Manager; each logs exactly one `D34` line with the endpoint and review; nothing changed; message names the company and not the person |
| `test_d34_a_skip_level_manager_with_an_hr_role_is_refused` | the same for an HR Manager two levels up |
| `test_d34_the_hr_stand_in_for_someone_with_no_manager_is_refused` | the stand-in is refused completion |
| `test_d34_a_different_hr_person_removes_answers_and_completes` | another HR person removes, answers both questions and completes |
| `test_d34_a_different_hr_person_calibrates_and_sends_back` | another HR person passes every permission check on calibration (the save itself then hits F-D8) and sends back |
| `test_d34_the_manager_with_an_hr_role_still_rates_in_manager_review` | item and overall ratings by the manager still work |
| `test_d34_the_manager_still_reads_the_review_in_hr_review` | reading unchanged |
| `test_d34_screens_tell_the_page_who_must_not_see_hr_buttons` | the four screens flag the line, and not another HR person |
| `test_d34_the_desk_refuses_the_line_a_change_to_the_hrms_appraisal_from_hr_review` | desk write refused to the line in HR Review, allowed to other HR, and to the manager in Manager Review; read unchanged |
| `test_d34_the_page_shows_a_note_instead_of_hr_buttons_for_the_line` | the page shows the note, not the buttons, in all four places |

Changed on purpose: `TestCrM3ManagerWithHrRole` in `test_review_fixround_010d.py`
now expects `"manager"` for the manager with an HR role in HR Review.

## 5. Non-functional dimensions, re-checked on the code written

| Dimension | Before → after | Verdict |
|---|---|---|
| Performance | HR step calls: +1 query for the caller's Employee rows and +1 per reporting level (usually under 6); +2 only when the subject has no manager (stand-in). Lists: one batched walk for their HR Review rows only; nothing for non-HR callers. Desk: only on non-read permission checks from HR Review on | neutral |
| Security | Segregation of duties between manager and HR steps on one review; fails closed at the depth cap; server side on every path, page only hides | improves |
| Reliability | Loops in the tree end cleanly; refusals are clear and say what to do | neutral |
| Scalability | Walk is bounded (50 levels) and batched for lists | neutral |
| Maintainability | One shared check used by six paths and one hook; no new abstraction beyond it | neutral |
| Data integrity | No writes added; a refused step changes nothing (tested) | neutral |
| Compliance / privacy | ISO/IEC 27001 segregation of duties and the anticipatory GDPR Art 22 "a second person decides" gap from `06` §5 closed for this case; log lines carry no values; message names no person | improves |

`ignore_permissions` counts unchanged (`performance_api.py` 64, `access.py` 0,
`permissions.py` not in the table and gains none).

## 6. Commands run and real results

    python scripts/check_app_integrity.py   -> app integrity: 579 checks, OK - all consistent (before each commit)
    node scripts/check_portal_handlers.js    -> portal handlers: all reachable and callable
    node scripts/check_undefined_js.js       -> undefined identifiers: none
    git -C C:/Surbhi-Git/hr-app merge --ff-only slice/010-portal-security-fixes   -> fast-forward

No migrate: no schema change. One test run at a time, work board marked.

    bench --site test_site run-tests --module alvoraa_portal.tests.test_review_line_hr_010d
      -> Ran 9 tests OK; Ran 1 test OK

**Fail without the fix.** The bench runs the shared main checkout, which may not
be edited, so the check was switched off inside the test process only: a Python
run in the bench container patched `access.subjects_in_my_line` and
`performance_api.subjects_in_my_line` to find nobody, and pointed the page test at
the page from `07b261d` (piped to `/tmp` in the container and deleted after). No
repository file changed.

      -> Ran 9 tests FAILED (failures=3, errors=2); Ran 1 test FAILED (errors=1)
         failed: the manager refusal test and the skip-level test (errors: the
         call was not refused and ran into save_calibration_note's missing
         column, F-D8), the stand-in test, the screens flag test, the desk test,
         and the page test (the note is not in the old page)
         passed either way, by design: the four "still allowed" tests (another HR
         person, the manager still rates, the manager still reads)

    bench --site test_site run-tests --module alvoraa_portal.tests.test_review_fixround_010d
      -> Ran 33 tests OK; Ran 6 tests OK
    bench --site test_site run-tests --module alvoraa_portal.tests.test_review_screens_010d
      -> Ran 39 tests OK; Ran 1 test OK
    bench --site test_site run-tests --module alvoraa_portal.tests.test_review_copies_010d
      -> Ran 34 tests OK
    bench --site test_site run-tests --module alvoraa_portal.tests.test_portal_security_010
      -> Ran 45 tests OK; Ran 5 tests OK
    bench --site test_site run-tests --module alvoraa_portal.tests.test_review_page_010d
      -> Ran 26 tests OK

**Not run:** the full `alvoraa_portal` and `alvoraa_goals` suites (a separate
verification run follows), `test_review_outside_010d`, and a browser trace.

**Read-only count on ppj.localhost** (a Python run with `frappe.get_all` reads
only, rolled back, counts printed, no names): 403 open appraisals (not submitted,
review not Completed), one company, 14 enabled HR Manager / HR User logins (11
with an active Employee record). Open appraisals with **no** eligible HR person —
every HR login for that company is the subject or in the subject's line:
**0**, in every variant counted (any HR login or only those with an Employee
record; with or without the stand-in; with or without System Manager). 402
reviews lose at least one HR person to the rule; the fewest left on any review is
8.

## 7. What is still open

1. **The stand-in rule** (point 2 at the top) is my reading of "the manager
   recorded on the review"; there is no manager field on the review or the
   Appraisal. Say if the stand-in should be allowed.
2. **The desk hook does not log** its refusals (see §2). The portal paths do.
3. **F-D8** (`calibration_notes` column missing) still breaks portal calibration
   for everyone. Not in this fix.
4. **A browser trace** of the four page places was not run.
5. The other residual-risk rows in `06` still need a name and a date; only R4 is
   marked, as fixed.

# Decision 35 (F-D8 calibration notes)

## The short answer

**Saving a calibration note works again. Tested on the local instance. Nothing is
pushed.** The user approved the fix on 2026-09-17 (decision 35) and kept the HR
stand-in refused (decision 36).

- **What was wrong:** `save_calibration_note` wrote `calibration_notes` on
  `Alvoraa Appraisal Extension`, but that field never existed. `git log -S
  calibration_notes` shows it was never in the DocType JSON in any commit; only the
  endpoint and the docs named it. So every portal save failed on an unknown column.
- **What changed:**
  - `alvoraa_appraisal_extension.json`: new field `calibration_notes` (Text, label
    "Calibration notes", read-only in the desk), after `manager_internal_notes`.
    No permission level: no field on this record uses one, and employees and
    managers have no role on the record at all (SEC-5).
  - `performance_api.save_calibration_note`: the `hasattr` / `frappe.db.set_value`
    branch is gone; it sets the field. A note that is not text is refused. Every
    earlier check (own review, decision 34 line rule, company, HR Review only) is
    unchanged.
  - `test_review_line_hr_010d`: the calibration test no longer swallows the old
    failure; it checks the note was stored.
  - New `tests/test_calibration_note_010d.py` (9 tests).

## Who can read the note, and why

01c classes it as decision-bearing: "Manager line, HR. Never the subject". Nothing
new was opened.

| Who | Portal screens | Desk / REST / Version rows |
|---|---|---|
| Subject (with or without an HR role) | Never — no endpoint returns it | Never (the "never your own" rule) |
| Manager without an HR role | Never | Never (no role on the record) |
| HR for the subject's company, not in the line | Not shown on any screen (the calibration box opens empty) | From HR Review on, like the rest of the record |
| Someone in the line who holds an HR role | Never | From Manager Review on, under the existing record rule (01c allows the line) |
| System Manager | — | Version rows under the same record rule (B1) |

`track_changes` is on, so each note change leaves a Version row with the text. Those
rows already follow the review record's rule (fix round B1); the new test proves it
for a real note Version row.

## Tests and the fail-without-fix proof

| Run | Result |
|---|---|
| `bench --site test_site migrate` | done, no errors |
| `test_calibration_note_010d` | 9 tests OK (first run: 1 test fault — the Version row test reused the same note text, so no change and no Version; fixed in the second commit) |
| `test_review_line_hr_010d` | 9 OK |
| `test_review_fixround_010d` | 33 OK |
| `test_review_screens_010d` | 39 OK |
| `test_review_copies_010d` | 34 OK |
| `test_portal_security_010` | 45 OK |
| `test_review_page_010d` | 26 OK |

**Switch-off proof.** A throwaway script was piped into the bench on stdin (no file
copied, no repo file changed). In its own memory it left `calibration_notes` out of
every write of the review record, then ran the two save tests:
`test_d35_an_eligible_hr_person_saves_a_note_and_a_calibrated_rating_and_both_persist`
failed (`None != 'S010D calibration note …'`) and
`test_d34_a_different_hr_person_calibrates_and_sends_back` failed
(`None != 'calibrated'`). A control run with nothing switched off: both passed.

Full suites were not run (not asked).

## Non-functional dimensions

| Dimension | Verdict | Why |
|---|---|---|
| Performance | neutral | One more column in the same save; no extra query |
| Security | neutral | Same checks; no new reader; desk writes still refused below Administrator |
| Reliability | improves | The HR calibration step no longer fails every time |
| Scalability | neutral | One text column |
| Maintainability | improves | Dead fallback branch removed |
| Data integrity | improves | The calibrated rating and its note are now saved together in one save |
| Compliance / privacy | neutral | The note follows the record's rule; subject never reads it; nothing logged |

## Release and rollback

- Release: the field comes with `bench --site <site> migrate` (checklist §8 step 3
  now says so). Without the migrate, portal calibration keeps failing.
- Rollback: an older image leaves the column in place; that is harmless. The old
  code would fail on calibration again.

## What is still open

1. HR cannot see a saved note in the portal: the calibration box opens empty, and no
   screen lists notes. Showing it to HR would be a new visibility decision, so it was
   not added.
2. There is still no separate calibration change log beyond Version rows (feature map
   E5).
3. No browser trace of the calibration box was run.
