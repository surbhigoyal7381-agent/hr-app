---
slice: 010-portal-security-fixes
artifact: 00b-review-copies-analysis
author: hrms-business-analyst
date: 2026-09-14
status: draft
inputs: [user requirement of 2026-09-14 (quoted below), 00-impact-analysis.md, 01c-security-privacy-requirements.md, code at slice/010-portal-security-fixes = origin/dev 4e3ba28 (line numbers are at 4e3ba28), read-only console checks on ppj.localhost, rolled back]
---

# 010 — Review copies of Objectives and KPIs: who sees what

The requirement, in the user's words (2026-09-14):

> "since we create a copy of Objective and KPIs while they are under an ongoing review,
> those copies shouldn't be visible outside the review process. and within the review
> the original version shouldn't be visible."

This is analysis only. No code or data was changed. It ends with decisions for the user.

---

## The short answer

**The portal does not make copies today.** No code path copies an Objective
(`Individual Goal`) or a `KPI` when a review starts. A review reads and writes **the live
records themselves**. The only link between a record and a review is the record's
`appraisal_cycle` field, and a record can sit in one cycle at a time.

So, measured against the rule as written:

| Half of the rule | Today |
|---|---|
| "Copies must not be visible outside the review" | **Nothing to leak.** There are no copies. |
| "Inside the review, originals must not be visible" | **Broken everywhere.** Every review screen and every rating and scoring path (§2.2, rows I1–I9) shows and changes the originals. So do 4 HR cycle screens (H1–H4). |

**Three things in the code probably explain why it feels like copies exist:**

1. **Same-name records in each quarter.** Rahul (PPJ-0058) has "Own sales value vs target"
   twice: `KPI-2026-00205` in Q1 and `KPI-2026-01960` in Q2. They are two separate records.
   The demo seeder created both. Nothing links them. Several outside screens show both
   side by side, because they do not filter by cycle.
2. **A half-built copy design in a different module.** `hrms/pms/draft_isolation.py` and
   the `PMS Business Goal` DocType have `is_review_draft` and `carried_over_from` fields
   for "draft clones created during review". **No code ever creates a clone.** The PMS
   tables hold 0 rows on ppj. The Alvoraa portal does not use this module.
3. **The HRMS Appraisal keeps a thin frozen copy.** When a Q1 appraisal is submitted, its
   `goals` table holds each KPI's label, weight and score (for example
   `('Own sales value vs target', 50.0, 5.0)` on `HR-APR-2026-00058`). That table is a real
   copy, but it has no targets, actuals or comments.

**Also bad, and it is what copies would fix:** `attach_ongoing_to_cycle`
(`performance_api.py:910`) **moves** a live record out of a Completed cycle into the new
one. When that happens, the finished review loses the record and the new review gains it,
with the old ratings still on it. Right now, on ppj, 381 progress readings, 400 evidence
rows and 601 manager ratings sit on Q2 records while 403 Q2 reviews are open. All of them
change the numbers under a review that is in progress.

**My recommendation:** if you confirm you want copies (decision D-1), make the copy a
**snapshot stored on the review record**: a new child table on
`Alvoraa Appraisal Extension`. Do not put copy rows into the `KPI` and `Individual Goal`
tables. Outside screens then cannot show copies at all, because the copies are not in the
tables those screens read. Only the review endpoints change.

**Size:** about **8 days** for the snapshot approach (§11). If you only meant "stop showing
Q1 and Q2 side by side" (D-1 option B), it is about **1.5 days**.

**Nothing should be built until D-1 to D-6 are answered.** They change what gets built.

---

## 1. How reviews use Objectives and KPIs today

### 1.1 Is there a field that marks a copy?

**No.** Fields checked in the DocType JSON and on the ppj database (no Custom Fields exist
on either DocType):

| Field | DocType | What it does | Used as a copy marker? |
|---|---|---|---|
| `appraisal_cycle` (Link → Appraisal Cycle) | KPI, Individual Goal | Tags the **live** record to one cycle. Rewritten by the paths in §1.2 | No. A tag on the original |
| `carry_over_from` (Link → Individual Goal) | Individual Goal | Exists in the JSON | No. No code writes it. 0 rows set on ppj |
| `is_future_plan` (Check) | Individual Goal | Exists in the JSON | No. No code writes it. 0 rows set |
| `parent_goal` (Link → Individual Goal) | Individual Goal | The cascade: Rahul's `GD-IG-2026-0230` → Sakshi's `GD-IG-2026-0228` | No. Parent and child, not source and copy |
| `is_review_draft`, `carried_over_from` | **PMS Business Goal** (`hrms/performance_management`) | Designed for review clones | Only in the unused PMS module. Nothing creates a clone. 0 rows |

`git log --all -S` for `review_copy`, `snapshot_of`, `source_kpi`, `source_goal`,
`copy_of` and `review_snapshot` finds nothing on any branch. `review_draft` appears only in
the PMS commit `48f5439` (31 Jul 2026).

### 1.2 Every path that brings work into a review, or changes it during one

| Function (file:line at 4e3ba28) | Who | What it really does | Copy? |
|---|---|---|---|
| `hr_start_appraisal_process` (`performance_api.py:621`) | HR | Creates the cycle, then calls `hr_generate_appraisals` | No |
| `hr_generate_appraisals` (`:2110`) | HR | Calls `attach_ongoing_to_cycle`, then creates one `Appraisal` per employee. `_apply_kpis_to_appraisal` (`:1086`) writes label, weight and score rows into `Appraisal.goals` | No for KPI and goal. Yes, thin, for `Appraisal.goals` |
| `attach_ongoing_to_cycle` (`:910`) | HR (whitelisted, **no role check inside**; it relies on its caller) | `db.set_value(appraisal_cycle = cycle)` on every live record whose dates overlap. **Takes records back from Completed cycles** (`claimable`, `:931`) | No. **Moves** the original |
| `set_cycle_membership` (`:971`) | Owner, manager, HR | Sets or clears `appraisal_cycle` on one record | No. Moves |
| `get_available_for_review` (`:3386`) / `set_review_selection` (`:3452`) | Employee, manager, HR, during the self-review | The "Add/remove Objectives" and "Add/remove KPIs" dialog (`hrms-employee.html:15048-15129`). Sets or clears `appraisal_cycle` on originals. **No stage check**: it still works after the review is sent | No. Moves |
| `save_review_page` (`:3521`) | Employee | Stores the typed self-ratings, comments and progress as JSON in `Extension.page_data`. This is the only "draft" layer, and it holds only what the employee typed | Partly: a draft of typed values, not of the records |
| `submit_employee_review` (`:3554`) | Employee | Writes those typed values **onto the originals** (`KPI.self_rating`, `self_comment`, `Individual Goal.actual_progress`). Creates new goals for next period (`:3622`) | No. Writes originals (S1 / SEC-1) |
| `save_kpi_self_review` (`:439`) | Employee | Self-rating dialog outside the wizard (`pfOpenSelfRating`, `hrms-employee.html:12224`) | No. Writes original |
| `save_kpi_manager_review` (`:803`) | Manager, HR | Manager rating dialog (`pfSaveRating`, `hrms-employee.html:13011`) | No. Writes original |
| `add_additional_reviewer` / `save_additional_reviewer_rating` (`:2594`, `:2617`) | Manager, reviewer | Child rows on the original KPI | No |
| `suggest_ratings`, `sync_appraisal_from_kpis`, `submit_appraisal` (`:828`, `:851`, `:1133`) | Manager, HR | Read `KPI.manager_rating` and goal progress **live**, then rebuild `Appraisal.goals` | No. Reads originals |
| `relink_kpi`, `save_kpi`, `delete_kpi`, `hr_save_kpi`, `hr_cancel_kpi` (`:1748`, `:2031`, `:2062`, `:2073`, `:2089`) | Author, HR | Change or **delete** the original, with no stage check | No. A KPI under review can be deleted mid-review |
| `log_kpi_progress` (`:311`), `goals_api.submit_goal_update` (`goals_api.py:977`), `hr_api.submit_goal_evidence_portal` (`hr_api.py:2008`) | Employee | Change `actual_value` or `actual_progress` on the original | No |

### 1.3 What happens at the end

| Event | What happens to Objectives and KPIs |
|---|---|
| Self-review sent ("Manager Review") | Typed values are written onto the originals. Nothing is frozen |
| Returned for revision (`return_for_revision`, `:2456`) | Only the status changes. Records are untouched |
| Completed | Nothing. The ratings stay on the live KPI. `Appraisal.goals` (label, weight, score) is the only frozen record |
| Appraisal cancelled | Nothing. The records keep `appraisal_cycle` |
| Next cycle generated | Overlapping live records are **moved** into it, including ones from a Completed cycle |

### 1.4 Real example: Rahul Kumar (PPJ-0058) on ppj

| Record | Name | Cycle | Linked to | Status |
|---|---|---|---|---|
| Objective | `GD-IG-2026-0018` "Own sales Q1" | Q1 (Completed) | parent `GD-IG-2026-0016` (Sakshi) | Completed |
| Objective | `GD-IG-2026-0230` "Own sales Q2" | Q2 (In Progress) | parent `GD-IG-2026-0228` (Sakshi) | Active |
| 6 KPIs | `KPI-2026-00205` … `00210` | Q1 | `00205` → `GD-IG-2026-0018` | rated (self and manager) |
| 6 KPIs | `KPI-2026-01960` … `01965` | Q2 | `01960` → `GD-IG-2026-0230` | not rated yet |
| Appraisal | `HR-APR-2026-00058` | Q1 | submitted; `goals` = 6 rows (label, weight, score) | review Completed |
| Appraisal | `HR-APR-2026-00461` | Q2 | draft; `goals` = 1 placeholder row "Targets achieved (KPIs)" | review in Employee Review |

**0 copies, 2 originals per quarter, no link between Q1 and Q2.** Across ppj this pattern
repeats: 1,755 KPI names exist in both Q1 and Q2 (3,510 KPIs), and 212 + 212 objectives.
Review extensions: 403 Completed, 269 Employee Review, 134 Manager Review.

---

## 2. Every place Objectives and KPIs are shown or returned

Key: **Outside** = not part of a review. **Inside** = part of a review. **Mixed** = HR cycle
screens that read review data but are not a person's review (see D-4).

"Shows" says what the screen returns today. Because no copies exist, every row says
"originals". The last column says what must change **if copies are built**.

### 2.1 Outside the review

| # | Screen | Function (file:line) | Filter today | Shows | If copies are built (M2) |
|---|---|---|---|---|---|
| O1 | Objectives & KPIs tree | `get_performance_tree` (`performance_api.py:1878`) | Goals: employee only, **no cycle filter even when `cycle` is passed**. KPIs: employee (+ cycle if passed) | Originals, all cycles. Checked as Rahul: 5 Q1 + 5 Q2 standalone KPIs side by side | No change needed for copies. Cycle-filter bug is separate (D-1 B) |
| O2 | My KPIs | `get_my_kpis` (`:283`) via `_kpi_rows` (`:267`, uses `get_list`, so desk rules apply) | employee (+ cycle) | Originals. As Rahul, no cycle: all 12 | None |
| O3 | Team KPIs | `get_team_kpis` (`:754`) | direct reports (+ cycle) | Originals. As Sakshi, no cycle: Rahul's 12 | None, unless it is the rating screen (D-4) |
| O4 | My goals | `goals_api.get_my_goals` (`goals_api.py:140`), `hr_api.get_goals_portal_data` (`hr_api.py:1923`) | employee, not cancelled | Originals, both quarters (checked) | None |
| O5 | Goal drawer / detail | `goals_api.get_goal_detail` (`:577`), `hr_api.get_goal_detail` (`:2091`) | by name | Original | None. Copy names never reach these (they are not goal names) |
| O6 | Team goals | `goals_api.get_team_goals` (`:785`), `hr_api.get_team_goals` (`:2148`), `get_employee_goals_for_manager` (`:2376`) | reports | Originals | None |
| O7 | Home goal card / stats | `goals_api._dashboard_stats` (`:73`) | employee | Originals | None |
| O8 | Scorecards | `hr_api.get_employee_scorecard` (`:691`), `get_team_scorecard` (`:876`) | employee(s), all cycles | Originals | None |
| O9 | Check-ins | `goals_api.create_checkin` / `get_checkins` (`:829`, `:872`) | goal | Original | None |
| O10 | Progress logging and approvals | `log_kpi_progress` (`:311`), `approve_kpi_update` (`:372`), `get_kpi_update_log` (`:402`), `goals_api.submit_goal_update` / `approve_goal_update` / `get_goal_update_log` (`:977`, `:1046`, `:1077`), `goals_api.get_pending_approvals` (`:1124`) | record | Original | None. Progress keeps going to the original (D-3) |
| O11 | Evidence | `hr_api.submit_goal_evidence_portal` (`:2008`), `alvoraa_goals/api/goal_api.submit_goal_evidence` (`:45`), `controllers/evidence.approve_evidence` / `reject_evidence` (`:145`, `:162`) | goal | Original | None |
| O12 | Linkable objectives, create or edit goal and KPI | `goals_api.get_linkable_objectives` (`:546`), `create_goal` (`:366`), `update_goal` (`:463`), `delete_goal` (`:513`), `save_kpi` (`:2031`), `relink_kpi` (`:1748`), `delete_kpi` (`:2062`) | record | Original | Add a stage rule: see VIS-8 (D-5) |
| O13 | Desk and REST: KPI and Individual Goal lists, forms, search, Link fields, `/api/resource` | `alvoraa_goals.permissions.kpi_query` / `individual_goal_query` / `has_employee_permission` (`alvoraa_goals/permissions.py:168-173`, hooks `:28-36`) | self + subtree; HR all | Originals | None under M2. Under M1 every one of these must hide copies |
| O14 | Background jobs | `alvoraa_goals.scheduled_jobs.recalculate_all_progress` (hourly), `check_cascade_alignment`, `send_progress_reminders` (daily); cascade roll-up `controllers/goal._aggregate_cascade` (`controllers/goal.py:91`); weightage budget `controllers/kpi._validate_weightage_budget` | all | Originals | None under M2. **Under M1 copies would double-count** cascade roll-up and weightage (100% budget) |

### 2.2 Inside the review

| # | Screen | Function (file:line) | Reads | Shows today | Verdict |
|---|---|---|---|---|---|
| I1 | Self-review wizard, "Past Objectives & KPIs" | `get_my_review` (`:3255`), `_goal_kpis` (`:3370`) | `Individual Goal` + `KPI` where `employee` and `appraisal_cycle` | **Originals.** As Rahul, Q2: `GD-IG-2026-0230` with `KPI-2026-01960`, and 5 standalone KPIs | Breaks "originals must not be visible" |
| I2 | Wizard "Future Objectives": unfinished goals from earlier cycles | `get_my_review` (`:3304`) | goals in **other** cycles, not completed | Originals from other cycles | Needs D-6 |
| I3 | Add/remove dialog | `get_available_for_review` (`:3386`), `set_review_selection` (`:3452`) | originals by date | Originals, and **moves** them | This is the "pick what to copy" step. It has to read originals (VIS-5) |
| I4 | Manager review | `get_manager_review` (`:3649`) | same as I1 | Originals. As Sakshi on `HR-APR-2026-00461`: same records | Breaks |
| I5 | Invited reviewer | `get_reviewer_view` (`:3882`) | goals in cycle | Originals | Breaks |
| I6 | Appraisal screen, cycle items | `get_cycle_items` (`:1003`) | cycle-tagged | Originals. As Rahul Q2: 1 goal, 6 KPIs | Breaks |
| I7 | Manager's appraisal payload | `get_team_appraisal` → `_appraisal_payload` (`:844`, `:467`) | cycle KPIs | Originals | Breaks |
| I8 | Rating and scoring | `save_kpi_self_review` (`:439`), `save_kpi_manager_review` (`:803`), `add_additional_reviewer` (`:2594`), `save_additional_reviewer_rating` (`:2617`), `suggest_ratings` (`:828`), `sync_appraisal_from_kpis` (`:851`) + `_scored_items` (`:1053`), `submit_appraisal` (`:1133`), `_sync_potential_to_extension` (`:878`) | originals | Originals, written and read | Breaks. Ratings must move to the copy |
| I9 | Self-review submit | `submit_employee_review` (`:3554`) | writes originals | Originals | Breaks. Also S1 / SEC-1 |
| I10 | Employee final review | `get_employee_final_review` (`:4039`) | extension only | No goals or KPIs | No change |

### 2.3 Mixed: HR cycle screens

| # | Screen | Function | Shows today | Decision |
|---|---|---|---|---|
| H1 | HR KPI list | `hr_list_kpis` (`:2098`) | Originals | D-4 |
| H2 | Cycle summary | `hr_cycle_summary` (`:2205`) | Originals, cycle-tagged | D-4 |
| H3 | CSV export | `export_cycle_kpis_csv` (`:2698`) | Originals, cycle-tagged, with ratings | D-4 |
| H4 | Calibration overview / matrix | `get_calibration_overview` (`:2878`), `get_calibration_matrix` (`:2967`) | Originals: KPI potential and manager ratings | D-4 |
| H5 | Team review list | `get_team_reviews` (`:672`) | Extension only | No change |

**Count:** 9 review screens (I1–I9), plus 4 HR cycle screens (H1–H4) that read review
ratings, show originals where the rule wants the review's copy. 0 screens leak copies,
because none exist.

---

## 3. What the requirement could mean: the first decision

| Option | What it means | Fits the words? | Size |
|---|---|---|---|
| **A. Build review copies** *(recommended if the goal is a stable, auditable review)* | When a review starts, copy each selected objective and KPI. The review shows and rates only the copy. Live work carries on against the original. A finished review keeps its copy forever, so later moves or edits cannot rewrite it | Yes, both halves | ~8 days (§11) |
| **B. No copies. Tidy the per-cycle records** | Treat Q1 and Q2 records as the "versions". Outside screens default to the current cycle. Review screens stay as they are | Only if "copy" meant "last quarter's record with the same name" | ~1.5 days |
| **C. Revive the PMS draft-clone module** | Use `PMS Business Goal.is_review_draft` | No. That module has different DocTypes, 0 data, pages the portal does not use, and no clone step | Not recommended |

The rest of this document assumes **A**, and marks what B would need.

---

## 4. Proposed visibility rules (option A)

Words used below:

- **Review copy**: a snapshot row for one objective or KPI, belonging to one review
  (one `Alvoraa Appraisal Extension`, which is one Appraisal).
- **Original**: the live `Individual Goal` or `KPI` record.
- **Inside the review**: the endpoints in §2.2 (I1–I9), plus the HR screens in §2.3 if D-4
  says so.
- **Outside the review**: everything in §2.1 (O1–O14).

| ID | Rule (testable) |
|---|---|
| **VIS-1** | No outside endpoint (O1–O12) and no desk or REST read of `KPI` or `Individual Goal` (O13) returns a review copy, for any persona. |
| **VIS-2** | Review copies live only on the review record. The only way to read them is through the inside endpoints, which apply the existing review access rules (SEC-5, SEC-6, SEC-7, PRIV-1/2). No Employee-role user can read a copy through `/api/resource` or `frappe.client`. |
| **VIS-3** | Every inside endpoint (I1, I4–I9) returns **only** review copies for goals and KPIs. The response has no field holding an original's name, value, rating or comment. It may keep `source_name` for audit only if D-2 allows it; otherwise the source link stays on the server. |
| **VIS-4** | A review copy is created for each objective and KPI in the review **at one defined moment** (D-2 default: when the Appraisal is generated, or on first open if missing). Creating it twice does nothing the second time: one copy per original per review. |
| **VIS-5** | While the review is "Not Started" or "Employee Review", the add/remove dialog (I3) may list originals, because choosing what to copy needs them. Adding creates a copy. Removing deletes that copy. The original's `appraisal_cycle` is **not** changed. From "Manager Review" onward the dialog refuses. |
| **VIS-6** | Every rating and comment made inside a review (self rating, self comment, manager rating and comment, potential, additional reviewer rating) is saved on the review copy. The original's rating fields are not changed. |
| **VIS-7** | Appraisal scoring (`_scored_items`, `sync_appraisal_from_kpis`, `submit_appraisal`, `suggest_ratings`) reads review copies only. A change to an original after its copy is frozen does not change the score. |
| **VIS-8** | Progress readings, evidence, check-ins and edits during a review go to the **original** (D-3). The copy's numbers refresh from the original until the self-review is sent, then freeze (D-2). An original that has a copy in an open review cannot be deleted. It can still be cancelled, and the copy is marked "Cancelled after review started" (D-5). |
| **VIS-9** | When a review is returned for revision, the copies unfreeze for the employee's edits. Their numbers are **not** refreshed from the originals unless the employee presses "Refresh numbers" (D-2). |
| **VIS-10** | When a review is Completed, its copies become read-only for everyone, including HR. They are shown only on the completed review screens, to the same people who may open that review (D-6). |
| **VIS-11** | Moving or editing an original after a review is Completed (for example `attach_ongoing_to_cycle` claiming it for the next cycle) does not change that review's copies or its score. |
| **VIS-12** | HR desk lists of `KPI` and `Individual Goal` show originals only. HR reads copies through the review screens, or through the Extension form in the desk (D-4). |
| **VIS-13** | If HR cycle screens (H1–H4) count as inside the review (D-4), they report ratings from copies. Otherwise they report live originals and are labelled "Live, not the review record". |
| **VIS-14** | An original not selected for a review has no copy and appears only outside. |
| **VIS-15** | New objectives created from the wizard's "Future Objectives" page are **originals** for the next period. They appear outside, and not as copies in the current review. |

**If you choose option B instead,** replace VIS-1 to VIS-15 with:

- **VIS-B1:** O1, O2, O3, O4, O6 and O8 default to the current open cycle. They show other
  cycles only when the user picks one.
- **VIS-B2:** `get_performance_tree` applies the `cycle` filter to goals as well as KPIs.
- **VIS-B3:** `attach_ongoing_to_cycle` stops taking records back from Completed cycles.
  This is needed because B has no copy to protect history.

---

## 5. How to enforce it: options

### M1 — Copy rows inside the `KPI` and `Individual Goal` tables

Add `review_of` (Link to the same DocType) and `review_appraisal` (Link to Appraisal). Copy
with `frappe.copy_doc`.

| For | Against |
|---|---|
| Review screens can keep their current queries (add a filter) and the KPI controller (rating limits, attainment maths) | **Every one of the ~45 readers in §2.1 must add `review_of is not set`**, plus the desk hooks, the hourly and daily jobs, cascade roll-up and the 100% weightage check. Miss one and copies leak or double-count |
| Child tables (progress log, reviewers) copy with the record | Each new endpoint must remember the filter forever. This is the S-class bug pattern this slice is closing |
| | KPI naming series and row counts double. `evidence`, `progress_updates` and `Goal Progress Audit Log` hooks fire on copies |

### M2 — A snapshot child table on the review record *(recommended)*

New child DocType **`Alvoraa Review Item`** (`istable: 1`), table field `review_items` on
`Alvoraa Appraisal Extension`.

| Field | Type | Why an existing field cannot carry it |
|---|---|---|
| `item_kind` | Select: Objective / KPI | One table for both, like `get_cycle_items` |
| `source_doctype`, `source_name` | Data, Dynamic Link | Audit link to the original. **Server-side only** (VIS-3) |
| `parent_item` | Data (row name of the objective's copy) | Keeps the objective → KPI tree inside the review |
| `label`, `description`, `unit`, `direction`, `category` | Data / Small Text / Select | Frozen wording |
| `period_start`, `period_end` | Date | Frozen period |
| `target_value`, `baseline_value`, `actual_value`, `attainment_pct` (or `progress_pct`), `weightage` | Float / Percent | Frozen numbers. The original's keep moving |
| `self_rating`, `self_comment`, `manager_rating`, `manager_comment`, `potential_rating`, `potential_comment` | Float / Small Text | Ratings belong to the review, not the live record (VIS-6) |
| `snapshot_taken_on`, `frozen` (Check), `source_status_at_close` | Datetime / Check / Data | Proves when the numbers were fixed (audit) |

Additional reviewer ratings: either a second child table, or keep them keyed by
`review_item` row name inside the existing `invited_reviewers` data. `[UNVERIFIED — engineer
to confirm the least-change option]`

| For | Against |
|---|---|
| **Outside screens cannot leak copies.** The copies are not in the tables those screens read. O1–O14 need no change | Review screens and the rating dialogs must read and write the new rows. JS changes are in the wizard, manager review and rating dialogs |
| Desk and REST access follows the Extension. After SEC-5 removes the Employee DocPerm, employees and managers cannot reach copies outside the portal | Ratings no longer land on `KPI.manager_rating`. Any outside screen that shows a rating (O2, O3, O8) shows blank for new cycles unless D-6 says to write final ratings back |
| Deleting or moving an original cannot damage a finished review (VIS-11) | One more DocType to migrate (`bench migrate`) |
| Matches the pattern HRMS already uses (`Appraisal.goals` is a copy), with enough fields to be useful | |

**Frappe-first check:** HRMS `Appraisal Goal` (the `Appraisal.goals` rows) already copies
label, weight and score. Adding custom fields there for target, actual and comments would
extend a stock HRMS table that `_apply_kpis_to_appraisal` rebuilds on every sync. That is
fragile, so it is not recommended. `Appraisal.goals` stays the HRMS summary, rebuilt **from
the review items**.

### One helper, not scattered checks

New module `alvoraa_goals/review_items.py` (the DocType owner):

| Function | Used by |
|---|---|
| `take_snapshot(appraisal, names=None)` | `hr_generate_appraisals`, `set_review_selection`, first open of `get_my_review` if no rows (VIS-4) |
| `refresh_snapshot(appraisal)` | wizard open while not frozen, "Refresh numbers" (VIS-8, VIS-9) |
| `freeze(appraisal)` | `submit_employee_review` (VIS-8) |
| `review_payload(appraisal)` | Returns the **same shape** the wizard gets today (`goals[]` with `kpis[]`, `standalone_kpis[]`), built from copies. The JS change stays small |
| `save_item_rating(appraisal, row, fields, as_role)` | Every rating path in I8. One place for the stage, relationship and range checks (SEC-1, SEC-2, SEC-10) |
| `has_open_review_copy(doctype, name)` | `delete_kpi`, `delete_goal`, `hr_cancel_kpi` (VIS-8) |

**Endpoints that must change (M2):**

| File | Functions |
|---|---|
| `alvoraa_portal/performance_api.py` | `get_my_review`, `_goal_kpis`, `get_manager_review`, `get_reviewer_view`, `get_cycle_items`, `_appraisal_payload`, `get_available_for_review`, `set_review_selection`, `save_review_page`, `submit_employee_review`, `save_kpi_self_review`, `save_kpi_manager_review`, `add_additional_reviewer`, `save_additional_reviewer_rating`, `suggest_ratings`, `sync_appraisal_from_kpis`, `_scored_items`, `_apply_kpis_to_appraisal`, `submit_appraisal`, `_sync_potential_to_extension`, `hr_generate_appraisals`, `delete_kpi`, `hr_cancel_kpi`; and, per D-4, `hr_cycle_summary`, `export_cycle_kpis_csv`, `get_calibration_overview`, `get_calibration_matrix` |
| `alvoraa_portal/goals_api.py` | `delete_goal` (VIS-8) |
| `alvoraa_goals` | new child DocType; `review_items` table on the Extension JSON; `review_items.py`; one patch |
| `alvoraa_portal/www/hrms-employee.html` | wizard goals page (`prRenderGoalsPage` and helpers, `:14583`), selector (`:15048-15129`), self-rating dialog (`:12224`), manager rating dialog (`:13011`): send `review_item` row names instead of KPI names |

**Not changed under M2:** everything in §2.1, the desk permission hooks, the scheduler.

### Enforcement for desk and REST

- M2 needs **no** `permission_query_conditions` change for KPI or Individual Goal.
- Copies are child rows of the Extension. Frappe reads child tables only through the
  parent's permission. So SEC-5 (remove the Employee DocPerm from the Extension) is what
  closes REST for employees and managers. **VIS-2 depends on SEC-5 shipping.**
- HR Manager, HR User and System Manager keep desk access to the Extension, so they can see
  copies in the desk form at any stage. That matches their access to `page_data` today.
  See D-4.

---

## 6. Overlap with the approved fixes ("Group D")

| Approved item | Overlap | Build advice |
|---|---|---|
| **S1 / SEC-1** `submit_employee_review` writes only the subject's records | Under M2 the self-review writes **review item rows of this appraisal**, never KPIs or goals. "Owned by the employee" becomes "row belongs to this appraisal". Stopping `actual_progress` writes is automatic | If D-1 = A is decided this week, build S1 **once**, against review items. Otherwise ship S1 as approved. The M2 change then replaces those lines |
| **SEC-2** rating fields on a KPI written only by the manager line | Under M2 new ratings are written to review items. Keep the `validate_kpi` guard for old data and the desk, and apply the same rule in `save_item_rating` | Test both |
| **S3 / SEC-5** no Employee DocPerm on the Extension | **VIS-2 depends on it** | Ship first |
| **S3** `overall_rating` release rule | No overlap with copies | — |
| **S4 / SEC-6** manager cannot read a draft self-review | `review_payload` must blank the copies' **self** fields (`self_rating`, `self_comment`) until the review is sent, exactly as `page_data` is blanked | Put the stage check inside `review_payload`, so all three review readers inherit it |
| **S4 / SEC-7** reviewer sees only allowed pages | Copies are returned only if `past-objectives` is allowed | Same helper |

**Suggested order:** S3 → S4 → (decide D-1) → S1 written against review items → VIS.
Everything sits in `performance_api.py`, so one engineer should do all of it to avoid
merge conflicts.

---

## 7. Edge cases

| Case | Today | Proposed (M2) | Decision |
|---|---|---|---|
| Progress or evidence logged during a review | Goes to the original, and the review sees it at once | Goes to the original. The copy refreshes until sent, then freezes | D-3, D-2 |
| Evidence approved after the self-review is sent | Changes the original's progress, and so the score | Does not change the copy or the score | D-2 |
| Goal created during a review (outside the wizard) | Gets tagged into the cycle by `attach_ongoing` or by the dialog | It is an original. It enters the review only if added in the dialog before sending | — |
| Goals created in "Future Objectives" | Created as originals in the **current** cycle, with an invalid status (B7) | Originals, tagged to the **next** cycle or none (VIS-15) | D-6 |
| Returned for revision | Status only | Copies unfreeze. No automatic refresh | D-2 |
| Completed | Ratings stay on the live KPI | Copies read-only. History through the review screen | D-6 |
| Appraisal cancelled | Nothing | Copies kept with the cancelled record for audit. Not shown anywhere except HR desk | D-6 |
| Two cycles in a row | Original **moved** from Q1 to Q2 if dates overlap | Original may have a frozen copy in Q1 and a live copy in Q2. Moving it does not touch Q1 | — |
| KPI not selected | Not in the review | No copy (VIS-14) | — |
| HR bulk generation | Synchronous, 806 appraisals on ppj | Snapshot inside the same per-employee savepoint. Over 100 employees → background job on the `long` queue, with per-employee results (NFR: anything over 2 s) | — |
| Original deleted mid-review | Allowed. The review loses it silently | Refused while an open review has a copy. Cancel instead (VIS-8) | D-5 |
| Original edited mid-review (target changed) | The review shows the new target | Copy keeps the old target once frozen. The wizard may show "Target changed since review started" as text, without the new value | D-2 |
| HR browsing all KPIs in desk | Sees originals | Same (VIS-12) | D-4 |
| Employee with no manager | HR fallback manager rates the original | HR fallback rates the copy (same helper as S4 step 5) | — |
| Re-running generation | "Existing appraisals left alone" | Existing snapshot left alone. Runs safely twice (VIS-4) | — |

---

## 8. Pin tests

File: `alvoraa_portal/alvoraa_portal/tests/test_review_copies.py`. Each test builds its own
employee, manager, HR user, cycle, objective and 2 KPIs with unique names (style of
`test_appraisal_visibility.py`). No shared fixtures.

| Test | Persona | Action | Expected |
|---|---|---|---|
| VIS-1a | Employee | Snapshot taken. Call `get_performance_tree`, `get_my_kpis`, `goals_api.get_my_goals`, `hr_api.get_goals_portal_data`, `_dashboard_stats`, `get_employee_scorecard` | No returned row name is a review item row name. Counts equal the number of originals |
| VIS-1b | Manager | Same with `get_team_kpis`, `goals_api.get_team_goals`, `hr_api.get_team_goals`, `get_team_scorecard` | Same |
| VIS-1c | HR Manager | `frappe.get_list("KPI")`, `frappe.get_list("Individual Goal")` | Only originals (row count unchanged by the snapshot) |
| VIS-1d | static | Scan `goals_api.py`, `hr_api.py`, `portal_api.py`, `alvoraa_goals/api/*.py`, `hrms/hrms/alvoraa_org_structure/api.py` | The text `Alvoraa Review Item` / `review_items` does not appear outside the allowed list of review functions |
| VIS-2 | Employee, then Manager | `frappe.client.get("Alvoraa Appraisal Extension", own)`, `get_list("Alvoraa Review Item")` | `PermissionError` for both |
| VIS-3a | Employee | `get_my_review` | Every goal and KPI in the payload has a review item row name. No KPI or Individual Goal name appears anywhere in the JSON (string search) |
| VIS-3b | Manager (after send) | `get_manager_review` | Same |
| VIS-3c | Invited reviewer with `past-objectives` | `get_reviewer_view` | Same. Without that page: no items |
| VIS-3d | Manager | `get_cycle_items`, `get_team_appraisal` | Same |
| VIS-4 | HR | `hr_generate_appraisals` twice | One item per selected original. Count unchanged after the second run |
| VIS-5a | Employee, Employee Review | Add a KPI in the dialog | A new item exists. Original's `appraisal_cycle` unchanged |
| VIS-5b | Employee, Manager Review | `set_review_selection` | Refused. Items unchanged |
| VIS-6 | Employee then Manager | Self-rate 4, manager-rate 3 through the portal | Item has 4 and 3. Original `KPI.self_rating` and `manager_rating` unchanged (still 0) |
| VIS-7 | Manager | Rate items, then set the original's `actual_value` and `manager_rating` directly, then `sync_appraisal_from_kpis` | `Appraisal.goals` scores match the items, not the originals |
| VIS-8a | Employee, Employee Review | `log_kpi_progress` on the original, reopen wizard | Original `actual_value` changed. Item's `actual_value` refreshed |
| VIS-8b | Employee, after send | `log_kpi_progress`, approve it, reopen `get_manager_review` | Original changed. Item unchanged |
| VIS-8c | Author | `delete_kpi` on an original with an open-review copy | Refused. Both still exist |
| VIS-9 | Manager | `return_for_revision`, then employee opens the wizard | Items editable. Numbers equal the frozen values (no refresh) |
| VIS-10 | HR | After Completed, `save_item_rating` | Refused. Values unchanged |
| VIS-11 | HR | After Completed, `attach_ongoing_to_cycle(next)` moves the original | Completed review's items and `Appraisal.goals` unchanged |
| VIS-12 | HR Manager | Desk KPI list count before and after 5 snapshots | Equal |
| VIS-14 | Employee | Original not selected | No item for it. Visible in `get_my_kpis` |
| VIS-15 | Employee | Submit with one "Future Objective" | New `Individual Goal` exists and is outside. No item for it in the current review |
| S4 link | Manager, Employee Review | `get_manager_review` | Items returned with `self_rating` and `self_comment` blank |
| Scale | HR | `hr_generate_appraisals` for 500 seeded employees × 8 items | Runs as a background job. Per-employee result list. No timeout |

---

## 9. Performance notes

| Item | Note |
|---|---|
| Rows | 8 median, 20 ceiling per employee per cycle (NFR budget). ppj: ~9 per review × 806 reviews ≈ 7,300 child rows if backfilled. Small |
| Review screen reads | Today `get_my_review` runs 1 goals query + **1 KPI query per goal** (`_goal_kpis`, N+1) + 1 standalone query. M2: one child-table load with the Extension. **Improves** |
| Outside screens | No extra filter under M2. **Neutral.** Under M1 every reader gains a filter, and the columns need indexes |
| Indexes | Child rows are fetched by `parent`, which Frappe indexes. Add an index on `source_name` for `has_open_review_copy` (delete and cancel checks). **Existing gap, not caused by this:** `tabKPI` has **no index** on `employee` or `appraisal_cycle` (only `name`, `creation`, `modified`, checked on ppj). Almost every KPI query filters on both. Recommend `search_index` on both in the same migrate |
| Bulk generation | Adds up to 20 inserts per employee. Over 100 employees → `frappe.enqueue(queue="long")`, per the "over 2 s is a background job" rule |
| Payload | Same shape as today, slightly smaller (no `owner` or creator lookups per KPI) |

---

## 10. Data migration

| Existing reviews on ppj | Proposed backfill | Risk |
|---|---|---|
| 269 Employee Review, 134 Manager Review | Patch: `take_snapshot` from the originals tagged to the cycle. Copy existing self and manager ratings from the KPI into the item. Freeze those in Manager Review. Mark `snapshot_taken_on` = patch time | Numbers are "as at migration", not "as at send". Say so in the item (`source_status_at_close = "Backfilled"`) |
| 403 Completed (Q1) | Snapshot from Q1 originals, frozen, marked Backfilled. On ppj, Q1 originals are still tagged to Q1 and still hold their ratings | On other tenants, `attach_ongoing_to_cycle` may already have moved records out of completed cycles. Those reviews cannot be fully rebuilt. The patch logs the appraisal names with 0 items (names only, no personal data) |
| Other tenants (dev, `alvoraa.co`, `minda`) | Unknown. Run the patch in dry-run mode first, printing counts per cycle | Could not check |
| Rollback | Revert the code, and delete `Alvoraa Review Item` rows. Originals are never changed by the patch, so nothing else needs restoring | Ratings made **after** go-live live only on items. A rollback loses them unless a write-back script copies them to the KPI first. Write that script before deploy |

Runs safely twice: the patch skips any Extension that already has items.

---

## 11. Size

| Work | Days |
|---|---|
| Child DocType, Extension table field, `review_items.py` helper | 1.0 |
| Review readers (I1, I4–I7) using `review_payload`, with the S4 blanking | 1.0 |
| Rating and scoring paths (I8, I9), selection (I3), delete and cancel guards | 1.5 |
| HR cycle screens (H1–H4), depending on D-4 | 0.5 |
| JS: wizard goals page, selector, self and manager rating dialogs | 1.25 |
| Background job for bulk generation | 0.5 |
| Patch, dry run, write-back script for rollback | 0.75 |
| Pin tests (§8) and the 500-employee scale test | 1.5 |
| **Total, option A with M2** | **≈ 8 days** |
| Option A with M1, for comparison | ≈ 7 days to build, plus a standing leak risk in ~45 readers, the scheduler and roll-ups |
| Option B (VIS-B1 to B3) | ≈ 1.5 days |

This is on top of the ≈ 6.5 days in `00-impact-analysis.md`. S1 shrinks by about 0.25 day
if it is written straight against review items.

---

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| **D-1** | Did "copy" mean (A) build a review snapshot, or (B) the per-quarter records with the same name? Copies do not exist today | **User** | Everything in §4–§11 |
| **D-2** | When is the copy taken, and when does it freeze? Proposal: taken at appraisal generation (or first open); numbers refresh until the self-review is sent; frozen after; no automatic refresh on return for revision | **User** | VIS-4, VIS-8, VIS-9 |
| **D-3** | During a review, do progress readings and evidence go to the original (proposal) or to the copy? | **User** | VIS-8 |
| **D-4** | Are HR's cycle screens (KPI list, cycle summary, CSV export, calibration) "inside the review" and so built from copies? Should HR see copies in the desk Extension form before HR Review, as it sees `page_data` today? | **User**, with Security (`01c` owner) | VIS-12, VIS-13, H1–H4 |
| **D-5** | May an original with an open-review copy be deleted? Proposal: no, cancel only | **User** | VIS-8 |
| **D-6** | After Completed, is the review's copy the history? Should final ratings also be written back to the original KPI, so My KPIs and scorecards still show a rating? Proposal: copy is the history; no write-back. Where do "Future Objectives" go: next cycle or no cycle? Which earlier-cycle goals does the Future Objectives page list (I2)? | **User** | VIS-10, VIS-15, O2/O3/O8 rating display |
| D-7 | Should `attach_ongoing_to_cycle` keep taking records back from Completed cycles once copies protect history? | **User** | VIS-11, VIS-B3 |
| D-8 | Security to adopt VIS-1, VIS-2, VIS-3 as `PRIV-n` items in `01c`, so they are tracked like SEC items | hrms-security-privacy-engineer | Traceability |
| D-9 | Is `attach_ongoing_to_cycle` meant to be callable by any logged-in user? It is whitelisted with no role check of its own | Engineer (S-class check) | Security, separate from VIS |

## Assumptions

- [ASSUMPTION] "Objectives" means `Individual Goal` and "KPIs" means `KPI` in `alvoraa_goals`, as used by the portal. Not the PMS DocTypes, and not `Goal Cascade`.
- [ASSUMPTION] "The review process" means the Alvoraa review flow on `Alvoraa Appraisal Extension` (statuses Not Started → Employee Review → Manager Review → Employee Final Review → HR Review → Completed).
- [ASSUMPTION] The screen names for `pfOpenSelfRating` (`hrms-employee.html:12224`) and `pfSaveRating` (`:13011`) are the self-rating and manager KPI rating dialogs. I read the function names, not the rendered screens.
- [ASSUMPTION] SEC-5 (remove the Employee DocPerm from the Extension) ships before or with VIS. VIS-2 is not true without it.
- [ASSUMPTION] Frappe v16.33.1 applies the parent's permission to child-table rows, so the Extension's permissions cover `Alvoraa Review Item`. `[UNVERIFIED — engineer to confirm with a REST test, VIS-2]`
- [ASSUMPTION] Counts are from ppj.localhost on 2026-09-14. Other tenants were not checked.
- I am not a lawyer. Keeping a frozen review copy is proposed for audit and fairness (a person is rated on the numbers they were shown). Whether any rule requires it, and how long copies are kept, is for the compliance owner.

## Handoff note

To the engineer (and to the user first): **do not build VIS rules until D-1 is answered.**
The requirement assumes copies exist, and they do not. The cheapest mistake would be
adding a "hide copies" filter to 45 endpoints to protect records nobody creates.

If D-1 = A, use M2 (snapshot on the Extension), not copy rows in `KPI` and
`Individual Goal`. Copy rows would force a filter into every reader, the hourly progress
job, cascade roll-up and the 100% weightage check, and one miss either leaks or
double-counts. Build S3/SEC-5 first, because VIS-2 depends on it. Put the S4 stage
blanking inside `review_payload`, so the three review readers cannot drift apart. Write S1
against review items if the decision lands before S1 is started.

Watch `set_review_selection`: today it moves originals between cycles and has no stage
check. Under M2 it must stop touching `appraisal_cycle`. `hrms-employee.html` is hot
(Wave 1 split planned), so keep the JS edits inside the four functions named in §5.
Line numbers here are at `4e3ba28`. The worktree has uncommitted edits in the same files,
so find functions by name.
