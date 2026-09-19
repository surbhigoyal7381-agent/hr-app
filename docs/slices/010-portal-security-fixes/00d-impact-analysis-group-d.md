---
slice: 010-portal-security-fixes
artifact: 00d-impact-analysis-group-d
author: hrms-fullstack-engineer
date: 2026-09-15
status: draft
inputs: [00c-review-copies-decisions.md (R1-R16, binding), 00b-review-copies-analysis.md, 01c-security-privacy-requirements.md, 03-implementation-notes.md §10, 00-impact-analysis.md (groups A-C, decisions 1-12), hrms/hrms/alvoraa_hr_core/access.py, code at slice/010-portal-security-fixes e58ffa2 (= origin/dev c27fb56 + the 00c doc), read-only console checks on ppj.localhost (rolled back), Frappe v16.33.1 source in hrlocal-bench]
---

# 010 group D — Review copies and review security: impact analysis and strategy

This is steps 1 and 2 of the change process. **No code has been changed.** It ends at a
human gate.

Line numbers are at `e58ffa2`. `01d-security-privacy-group-d.md` is being written at the
same time; the last section maps everything to the existing SEC/PRIV/VIS ids and leaves a
column for the 01d ids.

---

## The short answer

**The copy model in 00c can be built as decided, in about 14 build days and 12 commits.**
It fits Frappe well: one new child table on the review record, two hooks on KPI and
Objective, three settings in HR Settings.

**But one decision cannot be built as written. Please read this first.**

1. **R4 would double-count every KPI reading entered in the portal.** The KPI "Log
   progress" dialog tells people: *"Enter the cumulative value reached so far"*
   (`hrms-employee.html:12037`). So a reading is a running total. R4 says a *Cumulative*
   KPI adds up all its readings. Readings of 30 and then 50 would count as 80, not 50.
   Every KPI on ppj is *Cumulative* (3,510 of 3,510).
   **My recommendation:** keep R4, and change the dialog to ask for "the amount since
   your last update" on a Cumulative KPI and "the current reading" on an Absolute KPI.
   The backfill dry run lists KPIs whose existing readings look like running totals, so
   HR can fix them before the review counts them. **Question OQ-D1.**

**Three more things you should know before approving:**

2. **No code reads `progress_mode` today, and no number is built from approved facts.**
   A KPI's number is simply the last value typed, approved or not. Approving a reading
   changes nothing (`performance_api.py:332`, `:392-402`). So once copies exist, **the
   review will show a different number from "Objectives & KPIs"** whenever a reading is
   still pending, rejected, or dated outside the period. That is what R3 and R4 ask for.
   People will notice. **OQ-D3.**
3. **A reading's date is always the day it was typed.** The server sets `log_date =
   today()` (`performance_api.py:324`, `goals_api.py:994`). Someone who logs September's
   sales on 2 October puts them outside the Q2 review for good. **OQ-D2** asks whether
   people may choose the reading date.
4. **Inside the wizard, "Remove" deletes the real Objective or KPI today**
   (`hrms-employee.html:15143-15155`, `delete_goal` / `delete_kpi`). R11 and R12 need
   it to remove the copy only. I fix this as part of the build.

**What I checked on ppj (read-only):**

| Question from 00c | Answer |
|---|---|
| Is `KPI Progress Log.log_date` always set? | **Yes.** Required in the DocType, set by the server. 381 rows, 0 empty |
| Is `Goal Evidence.extracted_date` always set? | **Not guaranteed.** The field is optional; the caller may send it. ppj has 996 rows, 0 empty (demo data). **Fallback:** `upload_date` (set by the server), then `creation` |
| `Goal Progress Update.log_date` | Required, set by the server. 0 rows on ppj |

**Size:** about **14 build days** (range 12.5–15.5), **12 commits**. The product manager
estimated 9.5–10.5 days for copies. Adding the group D security items from `00` (about
2.75 days) gives 12.25–13.25. My figure is a little higher because of the facts-by-date
engine, the rating stamps, the lock hooks, and fixing the wizard's delete buttons.

**Waiting for your approval**, and answers to the open questions at the end. OQ-D1 to OQ-D5
change what gets built. The rest can be answered during the build.

---

## 1. What exists today (the parts group D changes)

### 1.1 The live review flow

Read from the code and checked against the page. Several performance endpoints have
**no caller in the page** ("API only"). They still work for anyone who calls them.

| Step | Screen (page function) | Server call | Caller today |
|---|---|---|---|
| HR creates the cycle and the reviews | Cycle wizard (`:13820`, `:16942`) | `save_cycle_wizard` (`performance_api.py:1336`). Creates an Appraisal and an Extension per selected employee. **No items are attached here** | Live |
| Employee writes the self-review | Wizard (`prOpenReview` `:14322`) | `get_my_review` `:3263`, `save_review_page` `:3529`, `submit_employee_review` `:3562` | Live |
| Employee picks what is reviewed | Add/remove dialog (`:15045-15128`) | `get_available_for_review` `:3394`, `set_review_selection` `:3460` (moves `appraisal_cycle` on the originals) | Live |
| Manager reviews | `prOpenManagerReview` `:15197` | `get_manager_review` `:3657`, `save_manager_review` `:3762`, `submit_manager_review` `:3984`. **The manager gives an overall and a potential rating only.** No per-KPI manager rating is reachable from the page | Live |
| Invited reviewer | `mrOpenFeedbackModal` `:13288` | `get_reviewer_view` `:3890`, `submit_reviewer_comments` `:3946` | Live |
| Employee reads and acknowledges | `prRenderEmployeeFinalReview` `:15699` | `get_employee_final_review` `:4047`, `acknowledge_final_review` `:4031` | Live |
| HR completes | `prFinishHrReview` `:15683`, `pfFinishHrReview` `:13385` | `advance_review_status` `:2397` (HR Review → Completed) | Live |
| HR calibration and export | `calLoad` `:11568`, `pdLoad` `:11062`, `pfExportCycleCsv` `:17106` | `get_calibration_matrix` `:2973` (reads the Extension only), `export_cycle_kpis_csv` `:2704`, `save_calibration_note` `:2951` | Live |
| Per-KPI ratings and scoring | none | `save_kpi_self_review` `:445`, `save_kpi_manager_review` `:809`, `add_additional_reviewer` `:2600`, `save_additional_reviewer_rating` `:2623`, `suggest_ratings` `:834`, `sync_appraisal_from_kpis` `:857`, `submit_appraisal` `:1139`, `get_cycle_items` `:1009`, `get_team_appraisal` `:850`, `hr_generate_appraisals` `:2116`, `hr_start_appraisal_process` `:627`, `hr_list_kpis` `:2104`, `hr_cycle_summary` `:2211`, `get_calibration_overview` `:2884`, `set_cycle_membership` `:977`, `attach_ongoing_to_cycle` `:916` | **API only** |

### 1.2 How the numbers are made today

| Number | Written by | When | Uses a date? | Uses `progress_mode`? |
|---|---|---|---|---|
| KPI `actual_value` | `log_kpi_progress` `:332` sets it to the typed value | On logging, **before approval** | No | No |
| KPI `attainment_pct` | `controllers/kpi._calculate_attainment` `kpi.py:89` | Every save | No | No |
| Objective `actual_progress` | `controllers/goal.recalculate_progress` `goal.py:65`: **sum of approved evidence** | On evidence approval | No | No |
| Objective `actual_progress` | `goals_api.submit_goal_update` `:1004`: **the typed value** | On logging, before approval | No | No |
| Objective `actual_progress` / `progress_pct` | `goals_api.set_goal_progress` `:678`, `create_checkin` `:829`, `submit_employee_review` `:3602` | Directly, no fact row | No | No |

- Approving a KPI reading or a goal update changes no number (`:392-402`, `goals_api.py:1049-1075`).
- On ppj, KPI `actual_value` equals the **sum** of approved readings for 190 of 191 KPIs,
  and Objective `actual_progress` equals the sum of approved evidence for 422 of 422. That
  is demo data, written by the seeder. Real portal entries are running totals (see the
  short answer).

### 1.3 Data on ppj (read-only)

| What | Count |
|---|---|
| Review extensions | 806: 403 Completed (Q1), 269 Employee Review, 134 Manager Review (Q2) |
| Items per review | about 4.3 KPIs + 0.5 Objectives; maximum 6 KPIs |
| Q2 KPIs with a manager rating | 601 of 1,755 (demo data). Q1: all 1,755 rated |
| Extensions with an overall rating | 403 (all Completed). 0 open reviews have one |
| Drafts with past-objectives page data | 0 |
| Invited reviewers | 0 |
| `KPI Additional Reviewer` rows | 0 |
| Custom DocPerm on the Extension | none |
| Indexes on `tabKPI` | `name`, `creation`, `modified` only. Query by employee + cycle is a full scan |
| Indexes on child tables | `parent` on KPI Progress Log and Goal Evidence |
| `Goal Check In` table | **does not exist on ppj** (the DocType was never synced). Not touched here |

---

## 2. The copy model (R1)

### 2.1 Where copies live

A new child DocType, **`Alvoraa Review Item`** (`istable: 1`, app `alvoraa_goals`),
as table field **`review_items`** on `Alvoraa Appraisal Extension`. That is method M2 in
`00b` §5.

- Outside screens read `KPI` and `Individual Goal`. Copies are not in those tables, so
  **no outside screen can show a copy** (VIS-1). Nothing outside needs a filter.
- A child row is read through its parent's permission. After SEC-5 removes the Employee
  role from the Extension, nobody but HR can reach copies through the desk or
  `/api/resource` (VIS-2).
- Frappe does not allow a child table inside a child table. So additional reviewer
  ratings cannot sit under an item (see §6.9).

### 2.2 Fields on `Alvoraa Review Item`

| Group | Fields | Why |
|---|---|---|
| Identity | `item_type` Select (Objective / KPI), `source_doctype` Select (Individual Goal / KPI), `source_name` **Data** with `search_index`, `parent_item` Data (row name of the Objective copy a KPI sits under) | `source_name` is **Data, not a Link or Dynamic Link**, on purpose. Frappe's `delete_doc` refuses to delete any document linked from a non-cancelled row (`frappe/model/delete_doc.py:475-495`). A Link would make an original impossible to delete for ever once any review copied it, even after the review closed. Our own rule (R11) is narrower, so we enforce it ourselves (§4) |
| How it arrived | `added_in_review` Check, `added_by` Link User, `added_on` Datetime, `backfilled` Check | R11; marks copies made by the migration |
| Definition (the copy's own) | `title`, `description`, `unit`, `direction`, `category`, `progress_mode`, `baseline_value`, `target_value`, `weightage`, `period_start`, `period_end` | R2: definition changes are made on the copy |
| Definition audit | `definition_at_start` Code (JSON, hidden), `definition_changed_by` Link User, `definition_changed_on` Datetime | R15 writes back only what changed; also detects a conflict (§5.4) |
| Numbers | `actual_value` Float, `attainment_pct` Percent, `facts_count` Int, `facts_as_of` Datetime, `source_cancelled` Check | Derived from the original's facts by date (§3) |
| Self rating | `self_rating`, `self_comment`, `self_rated_on`, and the stamp `self_basis_actual`, `self_basis_target`, `self_basis_weightage`, `self_flag` Check | R7 |
| Manager rating | `manager_rating`, `manager_comment`, `manager_rated_by`, `manager_rated_on`, stamp `manager_basis_actual`, `manager_basis_target`, `manager_basis_weightage`, `manager_flag` Check | R7. Reachable through the API only today (§1.1) |
| Potential | `potential_rating`, `potential_comment` | Moved off the KPI (R13). Never returned to the subject (PRIV-1) |
| Removal | `removed` Check, `removed_by` Link User, `removed_on` Datetime, `removal_reason` Small Text, `removed_at_stage` Data | R12, "keep with a reason" setting |
| Completion | `written_back_on` Datetime, `write_back_note` Small Text | R15 outcome, including a refused write-back |

There is no per-item HR rating today, so none is added. HR's calibrated rating stays
the Extension's `overall_rating` (`save_calibration_note`).

All fields are `read_only` in the JSON, so the desk form shows them but does not offer
editing. The desk and REST can still send a changed row, so the Extension controller
(`alvoraa_appraisal_extension.py`, empty today) refuses any change to `review_items`
unless the save comes from our review code (a document flag). That closes the HR desk
path around the stage and stamp rules.

### 2.3 New fields on `Alvoraa Appraisal Extension`

| Field | Type | Why |
|---|---|---|
| `review_items` | Table → Alvoraa Review Item | R1 |
| `items_taken_on` | Datetime | When copies were first taken. Also decides "added inside the review" (R11) |
| `freeze_point` | Select | The tenant setting **stamped when copies are taken**, so changing the setting mid-cycle does not change a running review |
| `frozen`, `frozen_on` | Check, Datetime | R6. `frozen_on` is also the line for "arrived after this review closed" (R10) |
| `overall_rating_basis` | Long Text (JSON, hidden) | R7 for the overall rating: the numbers of every item when the rating was given |
| `overall_rating_flag`, `overall_rated_by`, `overall_rated_on` | Check, Link User, Datetime | R7 |
| `completed_on` | Datetime | Starts the "lock release" count as a record of when the review really ended |

The Employee DocPerm row is removed in the same JSON (SEC-5, §8).

`_get_or_create_extension` (`:2303`) never sets `employee` or `appraisal_cycle` on the
records it creates. ppj has none missing, but `hr_api` scorecards filter on
`employee`. The new "ensure" step fills both.

### 2.4 When copies are taken

**Today nothing is attached when a cycle is created.** The live wizard
(`save_cycle_wizard`) makes Appraisals and Extensions only. Goal setting may still be
going on, so taking copies at that moment would copy half-set goals and lock them early.

**Proposal (OQ-D4):** copies are taken the **first time the review is opened or
changed** by anyone who may open it. One function, `ensure_review_items(extension)`,
is called at the top of every review reader and writer. It runs once per review; a
second call does nothing (VIS-4).

What gets copied:

1. Every non-cancelled Objective and KPI of the employee whose `appraisal_cycle` is the
   review's cycle.
2. **R16:** every item that `attach_ongoing_to_cycle` would have moved into this cycle
   but cannot, because an earlier review still holds it (§4.3). Such an item is then in
   both reviews, and its facts are split by date (§3.3).

After copies exist, the review's membership **is** its copies. `appraisal_cycle` on the
original becomes a planning tag only: outside screens filter by it, and the weightage
check uses it.

Items tagged to the cycle later (for example, a KPI created from "Objectives & KPIs"
during Employee Review) are **not** added silently. The wizard shows "2 items in this
cycle are not in your review" with the Add button. That avoids a silent omission without
changing the review behind the employee's back.

### 2.5 The add/remove dialog (I3)

- `get_available_for_review` keeps listing originals by date (it has to, to choose).
  `selected` now means "has a live copy in this review".
- `set_review_selection` **stops changing `appraisal_cycle`**. Ticking adds a copy;
  unticking removes the copy under R12 (§6.4).
- Stage rule (new): the employee may use it in Not Started and Employee Review; the
  manager in Manager Review; HR in HR Review. Today there is no stage check.

---

## 3. Facts by date (R3, R4, R10, R16)

### 3.1 Which facts count

| Copy of | Mode | Actual = | Fact rows | Date used |
|---|---|---|---|---|
| KPI | Cumulative | **sum** of approved readings dated in the window | `KPI Progress Log`, `approval_status = Approved` | `log_date` (always set) |
| KPI | Absolute | **latest** approved reading dated in the window (ties: later `approved_on`, then `creation`) | same | `log_date` |
| Objective | Cumulative | **sum** of approved evidence dated in the window | `Goal Evidence`, `validation_status = Approved` | `extracted_date`, else `upload_date`, else `creation` |
| Objective | Absolute | **latest** approved goal update dated in the window; if none, latest approved evidence | `Goal Progress Update` (Approved), then `Goal Evidence` | `log_date` / as above |

This matches the only approval-based code today (`recalculate_progress` sums evidence)
and the meaning of the goal update dialog ("New Progress Value", a reading,
`hrms-employee.html:8930`). **OQ-D1** asks you to confirm the Objective rows, and the KPI
dialog wording.

**Not counted:** `set_goal_progress`, check-ins and the old self-review progress write.
They have no dated fact row, so a copy cannot tell which period they belong to.

**The window** is the overlap of the copy's own period (`period_start`–`period_end`,
which may be changed inside the review) and the review's period (the Appraisal's
`start_date`–`end_date`). If the copy has no period, the review's period is used.

Attainment uses **one shared function**. `_calculate_attainment` in
`controllers/kpi.py:89` is split into a pure `attainment(actual, target, direction)`,
used by the KPI controller and by copies. Objective progress uses the same formula as
`recalculate_progress` (`min(actual / target × 100, 100)`).

### 3.2 When a copy's numbers refresh: stored, and refreshed on change

| Option | Cost | Problem |
|---|---|---|
| Compute on every read | 1–2 queries per review screen | HR cycle screens and the export read up to 1,000 reviews × 8 items. They would recompute every time |
| Scheduled job | one job | Numbers are stale for up to an hour. A job that misses a run leaves a wrong number silently |
| **Store on the copy, refresh when a fact changes, and on open (recommended)** | one indexed lookup per KPI/Objective save; about 1.2 ms per review refresh | Needs a hook on two DocTypes |

How it works:

1. **Doc event `on_update`** on `KPI` and `Individual Goal` (in `alvoraa_goals/hooks.py`)
   calls `refresh_copies_of(doc)`. Every fact change saves its parent:
   `approve_kpi_update` (`:402`), `approve_evidence` → `recalculate_progress`
   (`goal.py:83`), `approve_goal_update` (`goals_api.py:1075`), desk edits. The hook:
   - finds copies of this record in reviews that are **not frozen** and whose Appraisal
     is not cancelled: one query on the indexed `source_name`;
   - does nothing more if there are none. That is the common case, one query;
   - otherwise recomputes those copies (one query on the child table by `parent`) and
     writes only the rows whose numbers changed;
   - raises rating flags where a stamped number no longer matches (§6.6).
2. **On open**, the three review readers refresh the review's copies if it is not frozen.
   This is the safety net for any path that changes facts without saving the parent.

**Measured on ppj (read-only, averaged):**

| Query | Time |
|---|---|
| Approved readings for one review's KPIs, in the window | **1.22 ms** |
| Approved readings for all 1,755 Q2 KPIs | 43 ms |
| Approved evidence for all 212 Q2 Objectives | 12 ms |
| KPIs by employee + cycle (full table scan, no index) | 2.95 ms at 3,510 rows. Grows with the table |

Budget: a review screen stays within 500 ms at 20 items. A KPI or Objective save gains
one indexed query.

### 3.3 Overlapping cycles (R16)

An annual Objective reviewed in Q1 and Q2 has two copies. Each counts only facts dated
inside its own window. No fact is counted twice, and no fact is lost between them.

**A consequence nobody asked about:** a quarterly review of an annual goal compares one
quarter's facts with the full-year target. The Q1 attainment will look low unless the
target is changed inside the review (R2 allows that). I do not pro-rate targets
automatically; that would be a new rule.

### 3.4 Facts that arrive after the freeze (R10)

After a review freezes, a fact that is **approved after `frozen_on`** but **dated inside
the window** does not change the copy. HR's review screen shows, per item: "3 updates
dated in this period arrived after this review closed. With them the number would be 58
(now 50)." It is computed when HR opens the review (one query), and never changes the
score. The CSV export gains a column with that count.

---

## 4. The definition lock (R2, R9, R11)

### 4.1 What is locked, and when

**An original is "held" when** a live copy of it (not removed) sits in a review that is
not Completed, whose Appraisal is not cancelled, and whose lock has not been released.

**Locked fields:**

| DocType | Fields |
|---|---|
| KPI | `kpi_name`, `target_value`, `weightage`, `period_start`, `period_end`, `appraisal_cycle`, `employee` |
| Individual Goal | `goal_name`, `target_value`, `weightage`, `start_date`, `end_date`, `appraisal_cycle`, `employee` |

`employee` is not in R2's words. Moving an item to another person changes the definition
too, so I included it. Status is **not** locked: cancelling stays possible (OQ-D15), and
`recalculate_progress` sets "Completed" from facts.

**Release (R9):** the lock ends `N` days after the cycle's end date. `N` comes from the
tenant setting (default 30; 0 means never), and ends at once when the review is
Completed. It is worked out when checked, so no job is needed. After release the copy
keeps its own definition; only the original becomes editable again.

### 4.2 How it is enforced on every entry path

| Path | Mechanism | Covers |
|---|---|---|
| Saves through the document | Doc event `validate` on KPI and Individual Goal → `review_items.enforce_definition_lock`. For a saved record, uses `doc.has_value_changed(field)` (`frappe/model/document.py:699`; the "before" copy is loaded by `check_if_latest` before `validate` runs, `:1097`) and one "held?" query. Refuses with `frappe.ValidationError`, and logs through `access.log_refusal` (rule `R2`) | Portal `save_kpi`, `hr_save_kpi`, `relink_kpi`, `goals_api.update_goal`, desk form, `/api/resource`, Data Import |
| Deletes | Doc event `on_trash` on both DocTypes (none exists today). `frappe.delete_doc` calls it (`delete_doc.py:175-176`) | `delete_kpi`, `goals_api.delete_goal`, desk delete, REST delete |
| Writes that skip validation (`frappe.db.set_value`) | Explicit check in each function | `attach_ongoing_to_cycle` (skips held items and reports them), `set_cycle_membership` (refuses), `set_review_selection` (no longer writes the field) |
| Our own write-back | A document flag the hook honours | R15 only |

Message wording, for example: "This KPI is in Rahul Kumar's Q2 review. Change its target
inside the review, or after 30 Oct 2026." Only people who may see the review get the
review name; others get "…is in an open review".

**Known bypass, declared:** code that sets `flags.ignore_validate` skips the lock.
`recalculate_progress` (`goal.py:83`) and `set_goal_progress` (`goals_api.py:687`) do
this, but they write facts only. A pin test scans our apps for `db.set_value` or
`ignore_validate` saves on the locked fields, so a new one fails CI.

### 4.3 `attach_ongoing_to_cycle` (D-7, D-9)

- It **skips held items** and returns them as `held_by_open_review`. For those,
  `ensure_review_items` in the new cycle adds a copy (R16, §2.4).
- It keeps claiming items from Completed cycles. Copies now protect finished reviews
  (VIS-11), so that is harmless.
- **It gets an HR role check.** Today any logged-in user can call it (`:916`, D-9).

### 4.4 Delete (R11)

| Item | Delete allowed? |
|---|---|
| Existed before the review, held by an open review | **No.** "Remove it from the review instead." |
| Added inside the review (`added_in_review = 1`, the original was created after `items_taken_on`) | **Yes**, through the review: removes the copy and deletes the original, **only if the original has no fact rows**. With facts it can only be removed (facts are evidence, R3) |
| Not held by any open review | Yes, as today |

---

## 5. Freeze, completion and write-back (R6, R13, R15)

### 5.1 Freeze point (R6)

| Setting value | Freezes in | Unfreezes if |
|---|---|---|
| **HR sent (default)** | `advance_review_status` HR Review → Completed | Never; Completed is final |
| Manager review sent | `submit_manager_review` | `return_to_manager` (`:2498`) sends it back to Manager Review |
| Self-review sent | `submit_employee_review` | `return_for_revision` (`:2462`) sends it back to Employee Review |

Freezing does one last refresh, then sets `frozen` and `frozen_on`. **OQ-D10** confirms
the "unfreeze on return" rule. On unfreeze, facts that arrived meanwhile flow in, and any
rating whose numbers changed is flagged (R7).

### 5.2 Completion

In `advance_review_status` HR Review → Completed, in one transaction:

1. **Refuse** while any rating flag is open (§6.6).
2. Freeze (if not already), set `completed_on`.
3. Write back definition changes (R15, below).
4. Nothing is written to the original's rating fields (R13).

### 5.3 Write-back (R15)

For each copy, compare its definition with `definition_at_start`. For each changed field:

- **The original still has the start value** → set the new value on the original and save
  through the document with the write-back flag. That runs `validate_kpi` (including the
  100% weightage check) and writes a Version row. **KPI has `track_changes: 0` today**, so
  I turn it on in `kpi.json`. That also gives SEC-1 its "Version row exists". Individual
  Goal already tracks changes. An `Info` comment on the original says "Changed in review
  HR-APR-2026-00461 (Q2 FY27)", which is the "why".
- **The original changed after the lock was released** → do not overwrite. Record "Not
  written back: the live record was changed on 3 Nov" in `write_back_note`.
- **The save is refused** (for example, the weightage would pass 100% on the original's
  cycle) → do not block completion. Record the reason in `write_back_note`, and list it on
  HR's completion message. One Error Log entry with document names only.

### 5.4 Scoring reads copies (VIS-7)

`_scored_items`, `_apply_kpis_to_appraisal`, `sync_appraisal_from_kpis`,
`submit_appraisal`, `suggest_ratings` and `_sync_potential_to_extension` read the
review's copies (removed ones excluded). None of these has a caller in the page; they are
changed so the API cannot score from originals. Completion does **not** rebuild
`Appraisal.goals` automatically: no live flow does that today, and HRMS refuses the save
unless weightages total exactly 100, which would block completion.

`hr_generate_appraisals` (API only) still reads originals for its first projection,
because the Appraisal must exist before the Extension that holds copies.

---

## 6. Screens, endpoints and security, one by one

### 6.1 Review readers

| Function | Change | Security folded in |
|---|---|---|
| `get_my_review` `:3263` | `goals` / `standalone_kpis` built from copies, same shape the page reads today (§1.1 key list), with row names instead of KPI/Objective names. Removes the N+1 `_goal_kpis` query per goal. Adds `not_in_review_count`, `removed_items` (keep-mode), `rating_flags` (own self-rating) | Subject or HR (existing). HR through `_assert_hr_can_view`. Potential fields never returned (PRIV-1). `past_incomplete_goals` (Future Objectives page) stays on originals: those are next-period items, not copies (VIS-15) |
| `get_manager_review` `:3657` | Items from copies, plus change markers ("target 100 → 80, changed in this review"), flags, removed rows | **SEC-6 order:** relationship (manager line or HR) → `_assert_hr_can_view` → stage → read. **No Extension is created** by an unauthorised call. **PRIV-2:** before the self-review is sent, `page_data`, `pages_completed`, narrative, `overall_comment` and the copies' self fields are blank, with `self_review_sent: 0`. **SEC-10:** the subject calling on their own review is refused. HR viewers also get late facts (R10) |
| `get_reviewer_view` `:3890` | Items only if `past-objectives` is allowed | **SEC-7:** invitation checked with `frappe.db.get_value` before any read; never creates an Extension; refused before the self-review is sent; `page_data` cut to `allowed_pages` (empty list → nothing) |
| `get_employee_final_review` `:4047` | No items (unchanged) | **PRIV-1:** stop returning `potential_rating` and `potential_category` |
| `get_appraisal_extension` `:2316` | — | **PRIV-1:** the subject never gets `avg_potential_rating` or `potential_category`; `overall_rating` from Employee Final Review (decision 3). **PRIV-2:** narrative blank to others before sent |
| `get_my_appraisals` `:3154` | — | **PRIV-1:** `overall_rating` only from Employee Final Review |
| `get_team_reviews` `:678` | — | `potential_rating` only to the manager line and HR (it is). HR's own row: no potential |
| `get_cycle_items` `:1009` (API only) | From copies | — |
| `hr_api.get_employee_scorecard` `:702`, `get_team_scorecard` `:887` | — | **PRIV-1:** overall rating only when released (today it shows at any stage, raw SQL `:836`, `:949`). The employee's own scorecard shows no potential |

One function decides which Extension and copy fields a viewer receives:
`_review_fields_for(viewer_relationship, review_status)`. Every reader above serialises
through it (the `01c` Handoff "review-field filter").

### 6.2 Review writers

| Function | Change | Security folded in |
|---|---|---|
| `save_review_page` `:3529` | Past-objectives keys must be copy row names **of this review**; anything else refuses the save | **SEC-1** early check |
| `submit_employee_review` `:3562` | Writes `self_rating`, `self_comment`, stamp and `self_rated_on` **onto the copies**. Never touches KPI or Objective. **No progress write** (decision 4). Freezes if the setting says so. Removes both `except: pass` blocks; one bad key fails the whole submit, status unchanged | **SEC-1** |
| `set_review_selection` `:3460` | Adds or removes copies (§2.5). No `appraisal_cycle` write | Stage rule. The employee only in Not Started / Employee Review |
| **new** `remove_review_item(appraisal, row, reason)` | R12 (§6.4) | Stage and role rules; reason required for manager and HR |
| **new** `delete_review_item(appraisal, row)` | R11 (§4.4) | Only `added_in_review` rows; same stage rules |
| **new** `save_review_item_definition(appraisal, row, title, target_value, weightage, period_start, period_end)` | R2: edits the copy, stamps `definition_changed_by/on`, refreshes the copy's numbers for the new period, flags ratings if numbers move | Stage rules in OQ-D5. Values validated (target not 0, start ≤ end, weightage 0–100, review total may not exceed 100) |
| **new** `answer_rating_flag(appraisal, target, keep, new_rating, comment)` | R7 (§6.6) | Only the rater (or HR for the overall rating, OQ-D6); **SEC-10**: never the subject |
| `save_manager_review` `:3762` | Stamps `overall_rating_basis` when the overall rating changes | SEC-6 order, SEC-10. **Also fixes a live bug:** the page always sends `overall_rating: 0` and `potential_rating: 0` on "Save draft" (`_pr._mgr_*` is never set, `hrms-employee.html:15436-15437`), so every draft save wipes the manager's ratings. The server will only change a rating when one is sent |
| `submit_manager_review` `:3984` | Stamp; freeze if the setting says so | SEC-6, SEC-10 |
| `save_overall_rating` `:2863`, `save_calibration_note` `:2951` | Stamp the basis; clear the overall flag | SEC-10 (HR who is the subject is refused) |
| `advance_review_status` `:2397` | HR Review → Completed: refuse while flags are open; freeze; write-back | SEC-6 order for the manager step. No Extension created before the check |
| `return_for_revision` `:2462`, `return_to_manager` `:2498` | Unfreeze when the return goes before the freeze point | SEC-6: no Extension created before the check (F-13) |
| `invite_reviewer` `:3782`, `invite_reviewers_batch` `:3834` | — | SEC-6 order; **SEC-7:** invitee must be an active employee of the subject's company, not the subject |
| `submit_reviewer_comments` `:3946` | — | SEC-7: invitation checked before any create (F-13) |
| `add_action_item` `:2533`, `update_action_item_status` `:2556` | — | SEC-6: no Extension created before the check (F-13) |
| `save_kpi_self_review` `:445` (API only) | Writes the copy in the employee's open review in Employee Review; refused otherwise ("Rate this KPI inside your review") | SEC-1 class |
| `save_kpi_manager_review` `:809` (API only) | Writes the copy in the report's open review in Manager Review; refused otherwise | SEC-6, SEC-10, R13 |
| `add_additional_reviewer` `:2600`, `save_additional_reviewer_rating` `:2623` (API only, 0 rows on ppj) | **Retired:** both refuse with "Ratings are given inside the review. Invite a reviewer from the review instead." | Removes a KPI rating path outside the review (R13, R14, SEC-10) |

### 6.3 The decision guard for SEC-10

`hrms/hrms/alvoraa_hr_core/access.py` gains `refuse_own_rating(employee, doctype, name,
endpoint)`. It is the same check as `refuse_own_decision` (`is_own_record`), logged as
rule `SEC-10`. No role is exempt. The existing
`test_a_manager_who_is_also_hr_can_still_do_a_manager_review` must keep passing: a manager
who holds HR still rates their reports, never themselves.

### 6.4 Removal (R12)

| Who | When | Reason | Warning (always, before the call) |
|---|---|---|---|
| Employee | Not Started, Employee Review | Optional | "Remove '{title}' from this review? Anything changed for it inside this review — its target, weight, period and your rating — will be lost. Its progress and evidence stay on the live record." |
| Manager (line) | Manager Review | Required | Same, with "your rating" replaced by "the ratings" |
| HR | HR Review (or earlier as the fallback manager / own line) | Required | Same |

- **Setting "Discard the copy" (default):** the row is deleted.
- **Setting "Keep the copy with a reason":** `removed = 1`, by, on, reason, stage. The row is
  left out of scores, weightage totals and HR screens. It is shown struck through, with
  "Removed by {name} on {date}: {reason}", to people who may open the review.
- Either way the original, its facts and its evidence are untouched.
- Removing an item from the review ends the lock on it at once (it is no longer held).

### 6.5 Badge on originals (R5) and no ratings outside (R14)

**Badge.** The page already draws `<span class="tv-incycle">in review</span>` in the tree
from `in_cycle` (`tvCycleTag`, `hrms-employee.html:12795-12798`, fed by
`get_performance_tree` `:1965`, `:1973`). Today it means "tagged to a cycle". It will mean
"held by an open review":

- One batched helper, `review_holds(doctype, names)`, runs one query for the whole list
  and returns, per name: cycle label, review period end, frozen or not.
- Shown in: the Objectives & KPIs tree rows (`tvGoalRow` `:12693`, `tvKpiRow` `:12742`), the
  goal drawer (`renderGoalDrawer` `:8726`), the goal detail panel (`gpOpenDetail` `:10171`),
  and the KPI "Log progress" dialog (`pf-log-context` `:12030`).
- Text: "In review · Q2 FY27. Updates dated after 30 Sep 2026 don't change the review."
  Frozen: "In review · Q2 FY27 · numbers closed." It is text, not colour only.
- It carries **no review name, no rating and no link** (R14). The badge tells the owner
  and line that a review exists. They already know that.

**No ratings outside (R14).** What is reachable today:

| Outside payload or screen | Rating it carries today | Change |
|---|---|---|
| `KPI_FIELDS` (`:243`), used by `get_performance_tree`, `get_my_kpis`, `get_team_kpis`, `hr_list_kpis`, `suggest_ratings` | `self_rating`, `self_comment`, `manager_rating`, `manager_comment`, **`potential_rating`**, `potential_comment`, sent to the employee and the whole line | **Remove all six.** This also closes a PRIV-1 leak today: the subject receives their own potential rating in the tree payload |
| `get_team_kpis` `rated_count` (`:798`) | counts manager ratings | Removed |
| Desk and `/api/resource` on KPI | the same six fields, to anyone who can read the KPI | **Permlevel 1** in `kpi.json`, read for HR Manager, HR User and System Manager only. Nobody gets write (SEC-2, §8). Old Q1 ratings stay in the database for HR; nothing is deleted |

**Appraisal-level ratings are a different question.** Scorecards (`renderScorecard`
`:8014-8044`), the team comparison, "My Reviews" and the HR appraisals table show an
**overall** rating. I read R14 as being about Objective and KPI ratings, and apply the
PRIV-1 release rule (decision 3) to the overall rating instead. **OQ-D8.**

### 6.6 Rating stamps and flags (R7)

**What is stamped:**
- a self or manager rating on a copy: that copy's `actual_value`, `target_value` and
  `weightage`;
- the overall rating (the live flow's main rating): every live copy's actual, target,
  weightage and removed state, as JSON in `overall_rating_basis`.

**When a flag is raised:** whenever a copy's numbers are written (fact refresh,
definition edit, removal, adding an item), stamps are compared. A difference raises
`self_flag`, `manager_flag` or `overall_rating_flag`. Comparing uses the rounded stored
values, so "50.0" and "50" do not raise a flag.

**What people see:** "You rated this 4 when the actual was 40 of 100. It is now 55 of 100.
Keep 4, or change it?"

**Who answers, and what blocks:**

| Flag | Blocks HR completion? | Who answers |
|---|---|---|
| Overall rating | **Yes** | The manager who gave it, from their Reviews list, at any stage before Completed. HR may answer with a reason if the manager has left (OQ-D6) |
| Manager rating on a copy (API only today) | **Yes** | The same |
| Self rating | **No**, shown as information to the manager and HR | Nobody. The employee cannot reopen the review after sending it (OQ-D7) |

"Keep" re-stamps the basis to today's numbers and adds an Info comment on the Extension
(who and when). "Change" saves the new rating and stamps it.

HR's completion is refused with: "2 ratings were given on numbers that changed since.
Sakshi Verma must keep or change them before this review can be completed."

### 6.7 HR cycle screens (R8)

| Screen | Today | Change |
|---|---|---|
| CSV export `export_cycle_kpis_csv` `:2704` (live) | originals | Copies of every review in the cycle: one query for Appraisals, one for Extensions, one for items. Columns keep their order; "KPI ID" becomes the copy row id, plus a "Live record" column with the source name for HR (question for `01d`: OQ-D12). New columns: "Removed", "Facts arrived after close" |
| `hr_list_kpis` `:2104` (API only) | originals | Copies |
| `hr_cycle_summary` `:2211` (API only) | originals | Copies (counts, weightage, rated, attainment) |
| `get_calibration_overview` `:2884` (API only) | KPI potential and manager ratings | Copies. Also removes the `frappe.get_doc` per appraisal N+1 (`:2909`) |
| `get_calibration_matrix` `:2973` (live) | Extension only | No change |
| Desk KPI list | originals | Stays on originals. New `kpi_list.js` with `listview.page.add_inner_message(__("Live records, not the review record"))` (API checked at `frappe/public/js/frappe/ui/page.js:703`) |

### 6.8 Reviewer picker (decision 2, SEC-7)

`search_employees` (`:1466`, callers `hrms-employee.html:15318`, `:15375`) today returns
up to 100 active employees from every company to any logged-in user.

- New optional argument `appraisal`. The page sends it from both call sites.
- Caller must be the subject's manager line or HR (after `_assert_hr_can_view`). A plain
  employee is refused.
- Results: active employees of **the subject's company**, not the subject, not limited to
  the line (decision 2). Fields unchanged. Limit 50.
- Without `appraisal`: managers get their own company, HR gets `permitted_companies()`,
  everyone else gets nothing.
- The query is bound (`like` parameters through the ORM, as today). The ID search stays.

### 6.9 Additional reviewer ratings

Not copied. The two endpoints are retired (§6.2): no page calls them, and ppj has 0 rows.
Invited reviewers (comments by page) stay the 360 input.

---

## 7. The three tenant settings (R6, R9, R12)

### 7.1 Where they live

| Option | For | Against |
|---|---|---|
| **HR Settings custom fields (recommended)** | Organisation-level, where `CLAUDE.md` §4 says settings belong. Typed (Select, Int), so no free text. **HR Settings has `track_changes: 1`**, so every change has a Version row: who changed the freeze point, and when. That matters for fairness. HR Manager already edits HR Settings in the desk | Needs an installer on migrate and install. Not on the portal's Org Settings screen yet |
| Frappe Default store (`frappe.db.get_default`), like `alvoraa_checkin_photo_retention_days` in `field_checkin.py:533` | Existing portal precedent; editable from the Org Settings screen with no schema change | Untyped. `set_org_setting` accepts any key and any value from HR (F-15). No record of who changed it |

**Recommendation:** HR Settings custom fields, section "Performance reviews", created by
an idempotent installer `alvoraa_goals.review_items.after_migrate`, listed in **both**
`after_migrate` and `after_install` in `alvoraa_goals/hooks.py` (a fresh CI site never
runs migrate; `alvoraa_portal/hooks.py:222-230` explains why).

| Field | Type | Options / default | Read by |
|---|---|---|---|
| `alvoraa_review_freeze_point` | Select | HR sent (default) / Manager review sent / Self-review sent | `ensure_review_items` (stamped on the Extension) |
| `alvoraa_review_lock_release_days` | Int | 30. 0 = never | lock check, reminder job |
| `alvoraa_review_removal` | Select | Discard the copy (default) / Keep the copy with a reason | `remove_review_item` |

One reader, `review_settings()`, falls back to the default on an empty or unusable value.
It never throws. A negative number of days is treated as the default.

Showing them on the portal's Org Settings screen is **not** included (+0.5 day if you want
it). OQ-D9.

### 7.2 The lock reminder (R9)

A daily scheduler job, `alvoraa_goals.review_items.remind_hr_of_held_items` (added at the
end of `scheduler_events["daily"]` in `alvoraa_goals/hooks.py`):

- For each cycle whose end date was 15 or more days ago, where open reviews still hold
  items and the lock has not been released: an email and a Notification Log to each
  enabled HR Manager whose `permitted_companies()` include those reviews' company.
- Sent on day 15, then every 7 days (day 22, 29…). The date decides it, so no state is
  stored.
- If the release days are 15 or fewer, there is no reminder: the lock is already gone.
- Text: "Q2 FY27: 38 reviews are still open 15 days after the cycle ended. The Objectives
  and KPIs in them stay locked until 30 Oct 2026." Counts and cycle name only, no people's
  names.
- A failed send is logged with the user id only. It never stops the loop.

---

## 8. Group D security items, and how each is met

| Item | Mechanism | Where |
|---|---|---|
| **SEC-1** self-review writes only the subject's records | Copies of this review only; row-name check at save and submit; no progress write; whole submit fails on a foreign key | `save_review_page`, `submit_employee_review` |
| **SEC-2** rating fields on a KPI | **Stricter than 01c:** the six rating fields move to permlevel 1 with read for HR roles and **no write for anyone**. `validate_kpi` refuses any change to them unless a repair flag is set (patch or System Manager script). No portal path writes them any more (R13) | `kpi.json`, `controllers/kpi.py`. **Differs from 01c**, where the manager line could still write. Question for `01d` (OQ-D13) |
| **SEC-5 / PRIV-1** no Employee DocPerm on the Extension | Remove the Employee row from the JSON. Every portal read and write already goes through `get_doc`, `get_all` or `save(ignore_permissions=True)` (checked in `00` §S3); the page never calls `/api/resource` or `frappe.client` for it | Extension JSON |
| **M3** tenants whose Custom DocPerm re-grants Employee | Read-only report in the dry run (§10.2). Nothing is changed automatically | `backfill_report` |
| **SEC-6 / PRIV-2** manager review order and no draft read | §6.1, §6.2. One helper `_authorise_review_action(appraisal, action)` does relationship → HR guard → stage, before any read or create; `_extension(appraisal, create=False)` replaces `_get_or_create_extension` in the readers | `performance_api.py` |
| **SEC-7** reviewer pages and company | §6.1, §6.2, §6.8 | `get_reviewer_view`, `submit_reviewer_comments`, invite endpoints |
| **SEC-10** nobody rates their own review | `access.refuse_own_rating` (§6.3) in every rating writer | `save_manager_review`, `submit_manager_review`, `save_overall_rating`, `save_calibration_note`, `answer_rating_flag`, copy rating writers |
| **Reviewer picker** (decision 2) | §6.8 | `search_employees` |
| **SEC-16** `ignore_permissions` ceiling | Aim: no growth in `performance_api.py` (88). New writes to the Extension use `save(ignore_permissions=True)`, replacing existing ones where possible. If a use must be added, the ceiling in the test is raised in the same commit with a written reason | `test_sec16` |
| **SEC-17** refusals logged | Every new refusal goes through `access.refuse` (rules `SEC-1`, `SEC-6`, `SEC-7`, `SEC-10`, `R2`, `R11`, `R12`) | — |

---

## 9. Every file that changes, with callers

### 9.1 Files

| App | File | What |
|---|---|---|
| `alvoraa_goals` | **new** `doctype/alvoraa_review_item/` (json, py, `__init__`) | §2.2 |
| `alvoraa_goals` | `doctype/alvoraa_appraisal_extension/*.json` | table and fields (§2.3); Employee DocPerm removed (SEC-5) |
| `alvoraa_goals` | `doctype/alvoraa_appraisal_extension/*.py` | guard against direct edits of `review_items` |
| `alvoraa_goals` | `doctype/kpi/kpi.json` | `track_changes: 1`; `search_index` on `employee` and `appraisal_cycle`; rating fields permlevel 1 |
| `alvoraa_goals` | **new** `doctype/kpi/kpi_list.js` | desk list label (R8) |
| `alvoraa_goals` | **new** `review_items.py` | copies, facts, lock, stamps, settings, reminder, backfill report, installer |
| `alvoraa_goals` | `controllers/kpi.py` | shared `attainment()`; rating-field guard |
| `alvoraa_goals` | `hooks.py` | KPI and Individual Goal `validate` (as lists), `on_update`, `on_trash`; `after_migrate`, `after_install`; one daily job |
| `alvoraa_goals` | `patches.txt` + **new** `patches/v1_0/take_review_copies.py` | backfill (§10) |
| `alvoraa_portal` | `performance_api.py` | §6.1, §6.2, §6.5 (`KPI_FIELDS`, tree badge), §6.7, §6.8, §4.3, §5.4 |
| `alvoraa_portal` | `goals_api.py` | `delete_goal`, `update_goal`: friendlier lock messages; `get_goal_detail` badge |
| `alvoraa_portal` | `hr_api.py` | scorecards (PRIV-1 release rule), `get_goal_detail` badge. No signature changes |
| `alvoraa_portal` | `www/hrms-employee.html` | §11 |
| `alvoraa_portal` | **new** `tests/test_review_copies_010.py`; extend `tests/test_portal_security_010.py` | §13 |
| `hrms` (our module only) | `alvoraa_hr_core/access.py` | `refuse_own_rating` |

No edit to `apps/frappe`, `apps/erpnext` or stock HRMS code. HR Settings gets custom
fields through Frappe's `create_custom_fields`, not a JSON edit.

### 9.2 Callers of every function that changes (grep)

Python callers (`grep -rn` over `alvoraa_portal`, `alvoraa_goals`, `hrms/hrms/alvoraa_*`):

```
_get_or_create_extension   performance_api.py:896 1622 1662 1675 2324 2367 2389 2409 2467 2507 2543 2563 2853 2872 2956 3281 3537 3570 3668 3769 3791 3841 3897 3954 3991 4037 4054
_scored_items              performance_api.py:1102
_apply_kpis_to_appraisal   performance_api.py:869 1146 2181
_goal_kpis                 performance_api.py:3309 3711
KPI_FIELDS                 performance_api.py:276 1928
_kpi_rows                  performance_api.py:299 770 837 2112
attach_ongoing_to_cycle    performance_api.py:2130
_sync_potential_to_extension performance_api.py:873
_is_manager_of             performance_api.py:3399 3465 3664 3767 3787 3839 3989
_assert_hr_can_view        performance_api.py:606 2322 3270; tests/test_appraisal_visibility.py:83 154
refuse_own_decision        attendance_correction.py:743; goals_api.py:1058; hr_api.py:586; performance_api.py:384; controllers/evidence.py:86; tests/test_portal_security_010.py:401
validate_kpi               alvoraa_goals/hooks.py:21
delete_goal                tests/test_portal_call_paths.py:127,132 (pins the page's call path)
update_goal_status         tests/test_endpoint_entitlement.py:178
```

Page callers (`hrms-employee.html`) of the endpoints that change:

```
get_my_review 14322, 15130        save_review_page 14476        submit_employee_review 15895
get_manager_review 15197          save_manager_review 15432     submit_manager_review 15611
get_reviewer_view 13288           submit_reviewer_comments 13319
get_employee_final_review 15699   get_team_reviews 12893        get_appraisal_extension 14143, 14196
get_my_appraisals 13095           get_available_for_review 15050, 15062
set_review_selection 15118        advance_review_status 13385, 15683 (14271 unreachable)
return_for_revision 15938 (unreachable)                          invite_reviewers_batch 15521
search_employees 15318, 15375     export_cycle_kpis_csv 17106   save_calibration_note 17092
save_kpi_self_review 12236 (opener unreachable)                  save_kpi_manager_review 13017 (unreachable)
add_additional_reviewer 17039 (opener unreachable)               delete_kpi 14063, 15152
delete_goal 9928, 15145           update_goal 10139             save_kpi 14100
get_performance_tree 12469        log_kpi_progress 12070        hr_api.get_employee_scorecard 7914
hr_api.get_team_scorecard 8099    goals_api.get_goal_detail 10179   hr_api.get_goal_detail 8662
Never called by the page: hr_list_kpis, hr_cycle_summary, get_calibration_overview, save_overall_rating,
invite_reviewer, hr_save_kpi, hr_cancel_kpi, save_additional_reviewer_rating, attach_ongoing_to_cycle,
set_cycle_membership (12811 unreachable), sync_appraisal_from_kpis (10534 unreachable),
submit_appraisal (10544, 13043 unreachable), hr_generate_appraisals (14109 unreachable),
hr_start_appraisal_process (10567, opener unreachable), get_cycle_items (10482 unreachable)
```

**Existing tests that call the review endpoints:** almost none. Only
`test_appraisal_visibility.py` (`_assert_hr_can_view`) and `test_portal_security_010.py`
(`approve_kpi_update`, `log_kpi_progress`, `_send_notification`). **The review flow has
no automated safety net today**, so the pin tests in §13 are the first.

---

## 10. Backfill

### 10.1 What the patch does

`alvoraa_goals.patches.v1_0.take_review_copies`, appended to `alvoraa_goals/patches.txt`.
It runs after the DocType sync, because patches run after `sync_all`.

| Extensions | What happens |
|---|---|
| **Completed** (history) | Copies from the originals tagged to that cycle and employee. **Numbers are copied as stored** on the original (`actual_value`, `attainment_pct`, `progress_pct`), not recomputed from facts: Q1 on ppj has no fact rows, so a recount would show 0. Ratings and comments copied. `frozen = 1`, `backfilled = 1`, `completed_on` = the Extension's `modified`. Nothing is written back |
| **Employee Review, Manager Review, Employee Final Review, HR Review** | Copies as above, numbers as stored, ratings copied with stamps equal to those numbers (so no flag at migration). `freeze_point` stamped from the setting. Frozen only if the stage is past the freeze point. Past-objectives `page_data` keys translated from KPI/Objective names to row names |
| **Not Started** | Nothing. Copies are taken on first open |
| **Appraisal cancelled** | Nothing |

- The **first refresh after go-live** recomputes open reviews from facts by date. Where
  that changes a stamped number, R7 flags the rating. That is correct behaviour, and the
  dry run counts it in advance. On ppj: 0 open reviews have an overall rating, so 0
  overall flags. Q2 self-ratings: 0.
- **Safe to run twice:** an Extension that already has rows is skipped.
- **Commit** every 50 Extensions. Per-Extension `try` with a savepoint; a failure logs the
  Extension name only and carries on.
- **Output:** counts only. Extensions done, rows made, Extensions with 0 items (names
  listed: these are reviews whose originals were moved elsewhere and cannot be rebuilt).
- **Time [ASSUMPTION]:** about 5 inserts per Extension through `ext.save`, so about 1–2
  minutes for ppj's 806. I did not measure, because that needs writes.

### 10.2 Dry run (read-only), before any deploy

A function, `alvoraa_goals.review_items.backfill_report`, run after the code is on a site
but before its migrate. Or the same queries by hand, on your word, on each dev tenant
(I cannot reach them):

```sql
-- 1. Reviews by status (what gets copies)
SELECT review_status, COUNT(*) FROM `tabAlvoraa Appraisal Extension` GROUP BY 1;
-- 2. Completed reviews with nothing left tagged to their cycle (history that cannot be rebuilt)
SELECT COUNT(*) FROM `tabAlvoraa Appraisal Extension` x
 WHERE x.review_status='Completed'
   AND NOT EXISTS (SELECT 1 FROM tabKPI k WHERE k.employee=x.employee AND k.appraisal_cycle=x.appraisal_cycle)
   AND NOT EXISTS (SELECT 1 FROM `tabIndividual Goal` g WHERE g.employee=x.employee AND g.appraisal_cycle=x.appraisal_cycle);
-- 3. Cumulative KPIs whose readings look like running totals (OQ-D1)
SELECT COUNT(*) FROM tabKPI k
 WHERE k.progress_mode='Cumulative'
   AND (SELECT COUNT(*) FROM `tabKPI Progress Log` l WHERE l.parent=k.name AND l.approval_status='Approved') > 1
   AND ABS(k.actual_value - (SELECT SUM(l.value) FROM `tabKPI Progress Log` l WHERE l.parent=k.name AND l.approval_status='Approved')) > 0.001;
-- 4. Extensions with no employee or cycle set
SELECT COUNT(*) FROM `tabAlvoraa Appraisal Extension` WHERE IFNULL(employee,'')='' OR IFNULL(appraisal_cycle,'')='';
-- 5. M3: tenant permission rows that re-grant Employee on the Extension, or on KPI rating fields
SELECT parent, role, permlevel, `read`, `write` FROM `tabCustom DocPerm`
 WHERE parent IN ('Alvoraa Appraisal Extension','KPI') AND role='Employee';
-- 6. Drafts whose page data will be re-keyed
SELECT COUNT(*) FROM `tabAlvoraa Appraisal Extension`
 WHERE review_status IN ('Not Started','Employee Review') AND page_data LIKE '%"kpis"%';
```

The report function adds one more count that SQL cannot do simply: open reviews whose
facts-by-date number differs from the stored number, which is the number of R7 flags to
expect.

ppj results today: (1) 403 / 269 / 134; (3) not run as a running-total check, but 190 of
191 KPIs equal the sum, so about 0; (4) 0; (5) none; (6) 0.

### 10.3 Rollback

- **Code:** `git revert` of the group D commits, then deploy and migrate. The
  `Alvoraa Review Item` table and the HR Settings fields stay; they are harmless.
- **Data:** the patch never changes an original, so nothing needs restoring **from the
  patch**.
- **Ratings given after go-live live only on copies.** A rollback would hide them. I write
  `alvoraa_goals.review_items.copy_ratings_back_for_rollback(dry_run=1)` before deploy
  and prove it on `test_site`. It copies the latest self, manager and potential ratings
  from open reviews' copies to the KPIs, using the repair flag. It runs only on your word.
- **KPI rating fields at permlevel 1:** a revert of `kpi.json` plus migrate restores them.

---

## 11. The portal page (`hrms-employee.html`)

Hot file (22 commits in 7 days). All edits sit inside existing review functions, plus one
new block with its own prefix `ri…` for the new dialogs. No renames, no moves, no
re-indent.

| Area | Functions | Change |
|---|---|---|
| Wizard, past-objectives | `prRenderGoalsPage` `:14583`, `renderGoalNode`, `prReviewKpiRow`, `prRenderListGoals`, `prCollectPageData` `:14497` | Keys = row names. "Remove" calls `remove_review_item` with the §6.4 warning and a reason box when required. "Delete" only on `added_in_review` rows. "Edit" opens the new `riOpenEditItem` dialog (title, target, weight, period) instead of `gpOpenEditGoal` or the broken blank KPI form (`:15000`). Shows "N items in this cycle are not in your review" |
| Wizard, future objectives | `prCarryItem` `:14916` | "Remove" stops deleting an earlier-cycle Objective. It unticks "carry forward" instead (OQ-D11) |
| Selector | `_prShowSelectorModal` `:15069` | Escape labels and names with `gpEsc` (unescaped today at `:15099`, `:15101`) |
| Manager and HR review | `prOpenManagerReview` and its pages | Change markers, removed rows, flags with Keep/Change (`riAnswerFlag`), late facts for HR, the blocked-completion message. Save draft sends the ratings the manager actually set (bug fix) |
| Reviews list | `pfTeamReviewCard` `:12970` | "Rating needs your answer" when a flag is open |
| Final review, Overview card | `prRenderEmployeeFinalReview` `:15730`, `pfLoadMyReviewStatus` `:14234` | No potential rating or category (PRIV-1) |
| Badges | `tvCycleTag`, `renderGoalDrawer`, `gpOpenDetail`, `pfOpenLogModal` context `:12030` | §6.5 |
| KPI log dialog hint | `:12035-12037` | Wording by mode (OQ-D1) |
| Reviewer picker | `:15318`, `:15375` | send `appraisal` |

Every new input has a label. Flags and removed rows use text plus an icon, never colour
alone. New strings are wrapped for translation where the page already does so.

The static checks `scripts/check_portal_handlers.js` and `check_undefined_js.js` run on
the changed page. The existing pin `test_the_three_that_were_broken_stay_fixed` keeps
passing: `goals_api.delete_goal` is still called from `gpDeleteGoal` (`:9928`).

---

## 12. Impact

### 12.1 Cross-module reach

| App | Touched? | What |
|---|---|---|
| `alvoraa_goals` | Yes | New child DocType; Extension and KPI JSON; KPI and Objective hooks; `review_items.py`; installer; daily job; patch |
| `alvoraa_portal` | Yes | Review endpoints, outside payloads (`KPI_FIELDS`, badge), HR cycle screens, picker, scorecards, the page |
| `hrms` (our fork) | One function | `alvoraa_hr_core/access.py` `refuse_own_rating`. HR Settings gets custom fields at runtime; no HRMS file edited |
| `erpnext` | No | — |
| `frappe` | No edit | Uses `has_value_changed`, `on_trash`, `create_custom_fields`, child-table permissions, `add_inner_message` |
| `alvox_compensation` | Not present | The folder does not exist in this repo |
| Slice 012 (leadership view, design stage, docs only in the main checkout) | Overlap in plan | Its `07-devops-inputs.md` OPS-5 recommends the same KPI indexes. Leadership roll-ups keep reading originals (R3), which stay current because facts still reach them |

**Desk consequences:** employees and managers lose desk and REST access to the Extension
(SEC-5). Everyone except HR loses sight of KPI rating fields in the desk. HR sees copies in
the Extension form as read-only rows. KPI and Objective definitions refuse changes while
held, in the desk too.

### 12.2 Personas

| Persona | Gains | Loses or must change (on purpose) |
|---|---|---|
| **CXO** (System Manager today) | HR cycle screens and export show the review record, not live data. Setting changes have a history | Cannot complete a review while ratings are flagged. Cannot rate their own review |
| **HR Manager / HR User** | Settings (freeze point, lock release, removal). Late facts per item. A reminder about locked items. Write-back results listed at completion | Cannot fix a held item's target from the desk; must do it inside the review or after release. Cannot edit copies in the desk. Completion blocked by open flags. Cannot read a stranger's draft (unchanged rule, now also on every write) |
| **Manager** | Sees what changed inside the review. Removes items with a reason. Rating flags tell them when numbers moved | No draft self-review. No desk access to Extensions. No KPI ratings outside the review. Picker limited to the subject's company. Must answer flags before HR can finish |
| **Employee** | The review shows the numbers from approved, dated facts. Remove no longer deletes their real goal. Badge explains why a target cannot change | Cannot change a held item's definition outside the review. Cannot delete it. Late-typed readings count by the date they carry (OQ-D2). Never sees potential. The self-review no longer changes goal progress |
| **Invited reviewer** | — | Sees allowed pages only, after the self-review is sent. Only from the subject's company |

### 12.3 HRMS domain

| Domain | Impact |
|---|---|
| Appraisals | The review record becomes self-contained and replayable. Freeze, stamps, write-back. `Appraisal.goals` is not rebuilt automatically (§5.4) |
| Goals and KPIs | Definition lock while held; badge; facts unchanged in how they are entered; approval now matters for the review number |
| Org structure | Picker scope only |
| Leave, attendance, payroll | None. `attendance_score` on the Appraisal is untouched |

### 12.4 Non-functional verdicts (against this proposal)

| Dimension | Verdict | Reason |
|---|---|---|
| Performance | **improves** | Review screens drop the per-goal KPI query (N+1 in `_goal_kpis`) and the calibration overview drops a `get_doc` per appraisal. New indexes on KPI `employee` and `appraisal_cycle` end a full scan used by almost every KPI query. Cost: one indexed lookup per KPI/Objective save; about 1.2 ms per review refresh (measured) |
| Security | **improves** | SEC-1, 5, 6, 7, 10 and PRIV-1, 2 closed; ratings leave the tree payload and the desk; a whitelisted cycle mover gets a role check; copies unreachable outside the review. `ignore_permissions` held at its ceiling |
| Reliability | **improves**, with two risks | Silent `except: pass` removed from the self-review; wizard stops deleting real records; draft save stops wiping ratings. Risks: a write-back can be refused at completion (handled, recorded); the refresh hook adds work to every KPI/Objective save (bounded, tested for query count) |
| Scalability | **neutral** | Rows grow by about 8 × employees × cycles (1,000 × 8 × 4 = 32,000 a year). Child rows are read by indexed `parent`; lookups by indexed `source_name`. HR screens read copies with 3 bounded queries per cycle |
| Maintainability | **degrades slightly** | A second place holds item data, and a new module holds the rules. Contained: one module, one field filter, one attainment function, pin tests for each rule |
| Data integrity | **improves** | A finished review can no longer be changed by moving or editing originals. Ratings carry the numbers they were given on. Definition changes go back once, audited, with conflicts recorded. Risk: numbers inside and outside the review differ by design (OQ-D3) |
| Compliance / privacy | **improves** | The rating is a decision record with a named rater, the numbers, and its history. Potential never reaches the subject. Settings changes are versioned. No personal values in logs or reminders |

---

## 13. Test plan

**Files:** new `alvoraa_portal/alvoraa_portal/tests/test_review_copies_010.py` (R and VIS
items), and group D SEC/PRIV tests added to `test_portal_security_010.py`. Both use the
`_Base` pattern: `module_access.release_permissions()` in `setUpClass`, because
`test_module_access` and `test_subscription_access` leave plan restrictions behind. Every
test builds its own users, employees, cycle, Objective and KPIs with unique names, and
cleans up what committing endpoints wrote.

Runs on `test_site`, one run at a time (`pgrep -af run-tests` first, work board marked).

| Test | Proves |
|---|---|
| `test_r1_copies_taken_once_on_first_open` | VIS-4: second open adds no rows; count equals originals |
| `test_r1_outside_payloads_hold_no_copy` | VIS-1: tree, goals, scorecards and desk lists return originals only; no row name of a copy appears |
| `test_r1_child_rows_unreachable_through_rest` | VIS-2: employee and manager `frappe.client.get` / `get_list` on the Extension and on `Alvoraa Review Item` → PermissionError (also proves child permission follows the parent in v16) |
| `test_r1_inside_payload_holds_no_original_name` | VIS-3: JSON string search on `get_my_review`, `get_manager_review`, `get_reviewer_view` |
| `test_r3_facts_dated_in_period_reach_copy_until_freeze` | R3 with approve after log |
| `test_r3_facts_dated_after_period_stay_on_original` | R3 |
| `test_r4_cumulative_sums_absolute_takes_latest` | R4 for KPI and Objective; pending and rejected ignored |
| `test_r4_evidence_date_falls_back_to_upload_date` | 00c date question |
| `test_r16_overlapping_reviews_split_facts_by_date` | R16 |
| `test_r10_late_fact_shown_to_hr_and_score_unchanged` | R10 |
| `test_r2_definition_lock_in_portal_desk_rest_and_import` | R2: `save_kpi`, `doc.save`, `frappe.client.set_value`, `update_goal` refused while held; allowed after removal |
| `test_r2_cycle_move_refused_and_attach_skips_held` | R2 via `set_cycle_membership`, `attach_ongoing_to_cycle`, `set_review_selection` |
| `test_r2_static_no_unguarded_writes_to_locked_fields` | Static scan for `db.set_value` / `ignore_validate` on locked fields |
| `test_r9_lock_released_after_n_days_and_zero_means_never` | R9 with a fixed cycle end date |
| `test_r9_reminder_on_day_15_and_22_without_names` | R9 job, mocked `sendmail` |
| `test_r11_existing_item_cannot_be_deleted_added_item_can` | R11, and "with facts → remove only" |
| `test_r12_discard_and_keep_settings_and_stage_rules` | R12, both settings, employee after send refused, manager without reason refused |
| `test_r6_freeze_point_setting_each_value_and_unfreeze_on_return` | R6, OQ-D10 |
| `test_r6_setting_change_mid_cycle_does_not_touch_running_review` | stamped `freeze_point` |
| `test_r7_changed_number_flags_rating_and_blocks_hr_completion` | R7, overall and item flags; keep re-stamps |
| `test_r13_no_rating_written_to_original` | VIS-6 |
| `test_r14_outside_payloads_carry_no_rating_fields` | Recursive key scan of tree / KPI payloads for the six fields |
| `test_r15_writeback_once_with_version_and_conflict_note` | R15, VIS-11 |
| `test_r8_hr_screens_and_export_read_copies` | R8 |
| `test_r5_badge_holds_no_review_name_or_rating` | R5, R14 |
| `test_vis7_scoring_reads_copies` | VIS-7 |
| `test_sec1_self_review_writes_only_this_reviews_copies` | SEC-1 |
| `test_sec2_nobody_writes_kpi_rating_fields` | SEC-2 (stricter form) |
| `test_sec5_employee_has_no_docperm_on_extension` | SEC-5, plus shipped JSON check |
| `test_sec6_manager_review_order_and_no_create_before_check` | SEC-6, Extension count unchanged |
| `test_priv1_subject_never_receives_potential_any_endpoint_any_status` | PRIV-1, parameterised |
| `test_priv2_no_self_review_before_sent_and_after_return` | PRIV-2 |
| `test_sec7_reviewer_pages_and_company` | SEC-7 |
| `test_sec10_nobody_rates_their_own_review` | SEC-10, and the manager-who-is-HR test still passes |
| `test_picker_subject_company_only_and_plain_employee_refused` | decision 2 |
| `test_manager_draft_save_keeps_ratings` | the `_pr._mgr_*` bug |
| `test_backfill_patch_safe_twice_and_rekeys_page_data` | §10 |
| `test_rollback_script_dry_run_changes_nothing` | §10.3 |
| `test_query_count_review_open_bounded_by_constant` | 20 items vs 2 items: same number of queries |
| `test_query_count_kpi_save_not_held_one_extra_query` | refresh hook cost |
| `test_scale_hr_export_1000_reviews_8_items_under_3s` | NFR budget; seeded with `frappe.db.bulk_insert` |

**Whole suites** (`--app alvoraa_portal`, `--app alvoraa_goals`) before hand-off. Known
failures today: 11 in `test_invoicing`, 3 in `test_leave_year`.

**By hand in a browser on the local bench:** wizard (open, rate, remove, edit, add, send),
manager review (flags, keep/change, removed rows), HR completion (blocked, then done),
reviewer view, badge in the tree and the goal drawer, KPI log dialog wording, picker. At
200% zoom and a 360 px screen.

---

## 14. Parallel-work check

**Start-of-work steps (2026-09-15):**

- `git fetch origin`; `git log HEAD..origin/dev`: **nothing incoming.** The branch is
  `origin/dev` (`c27fb56`) plus one commit, the 00c decisions (`e58ffa2`).
- `git worktree list`: main checkout (`dev`, `c27fb56`) and this worktree only.
- Work board: one row, this slice. It already lists the group D files expected.
- Main checkout, another session's uncommitted work, **not mine, not touched:**
  `CLAUDE.md`, `.claude/agents/*`, `.claude/context/frappe-conventions.md`,
  `backlog/KPI_AUTOMATION_BACKLOG.md`, deleted `OBJECTIVES_KPI_REQUIREMENTS.md`,
  `hrms/.../alvoraa_position.py`, and untracked files including
  `docs/slices/012-leadership-view/`. None is a file group D changes.

**Files I will change:**

| File | Hot? | Commits 7 / 30 days on `origin/dev` | Overlap and plan |
|---|---|---|---|
| `alvoraa_portal/www/hrms-employee.html` | **Hot** | 22 / 40 | Edits inside review functions plus a new `ri…` block (§11). **Ask:** has Wave 1's split into includes started? If yes, *sequence*: rebase onto it and move my edits into the new includes |
| `alvoraa_portal/performance_api.py` | Busy | 6 / 9 (mostly this slice) | Many functions; no signature removed. New optional argument on `search_employees` only |
| `alvoraa_portal/hr_api.py` | **Hot** (signature rule) | 9 / 22 | Two scorecard bodies and the goal detail badge. No signature change |
| `alvoraa_portal/goals_api.py` | No | 2 / 5 | Messages and a badge |
| `alvoraa_goals/hooks.py` | Hooks rule | 0 / 2 | Entries added at the end of each list, with comments. `"validate"` for KPI and Individual Goal becomes a list that keeps the existing handler first |
| `alvoraa_goals/patches.txt` | **Hot** | — | One line at the end |
| Alvoraa Appraisal Extension JSON | **Hot (DocType JSON)** | 0 / 1 | Already claimed on the board for group D |
| KPI JSON | **Hot (DocType JSON)** | 0 / 1 | **Slice 012 plans KPI indexes (OPS-5).** *Sequence:* I claim KPI JSON on the board and add both indexes here; 012 then has nothing to add for KPI. Tell 012's session |
| New `Alvoraa Review Item` DocType, `review_items.py`, `kpi_list.js`, patch | New | — | — |
| `alvoraa_goals/controllers/kpi.py` | No | 0 / 1 | Split out `attainment()`; add rating guard |
| `hrms/hrms/alvoraa_hr_core/access.py` | New in this slice | — | One function added at the end |
| Tests | Shared fixture rule | — | Own records, unique names, no fixture changes |

**Other developers:** I cannot see other machines. **Question for you: is anyone else
working in the review screens, `performance_api.py` or `hrms-employee.html`?** (OQ-D14)

**Pins:** every R, VIS, SEC and PRIV item in §13 has a named test, so a bad merge that
drops one fails CI. Both files are in `alvoraa_portal`, which CI runs.

---

## 15. Rollout

**Needs `bench migrate` on every tenant**, which is your decision each time:

1. Deploy code (dev tenants first, on your word).
2. Before migrate: the dry-run queries in §10.2 on each tenant. Look at (2), (3) and (5).
3. `bench migrate`: syncs the new DocType, the Extension and KPI JSON, runs the HR
   Settings installer, runs the backfill patch, and the scheduler picks up the daily job.
   Adding indexes to `tabKPI` locks that table briefly (3,510 rows on ppj: seconds).
4. No `bench build` (the page is a www template). No `clear-cache` (migrate clears meta).

**Tenant configuration:** none needed; the defaults apply. HR may change the three
settings in HR Settings. Tenants with a Custom DocPerm from (5) need a manual decision; I
change nothing automatically (M3).

**Tell users, in plain words:**

- Employees: "Your review shows the numbers from approved updates dated in the review
  period." "While your review is open, an Objective's or KPI's target, weight, period and
  name are changed inside the review." "Remove takes an item out of your review. It no
  longer deletes it." "Log each reading with the amount since your last update" (if OQ-D1
  goes that way).
- Managers: "You'll see a self-review once it's sent." "If the numbers change after you
  rate, you'll be asked to keep or change your rating." "People search for reviewers
  shows your company."
- HR: the three settings; "a review can't be completed while a rating waits for an
  answer"; the reminder email; "the desk KPI list shows live records, not the review
  record".

**Order of deploy:** one batch for all of group D. The copy model, SEC-5 and the page
depend on each other.

---

## 16. Commits

Each commit carries its own pin tests. Estimates are build days, tests included.

| # | Commit | Items | Depends on | Days |
|---|---|---|---|---|
| 1 | Review items: a place on the review record for its own copy of each Objective and KPI, and the three settings | R1 structure, §2.2–2.3, §7.1, KPI indexes and `track_changes` | OQ-D9 | 0.75 |
| 2 | Copies are taken once, and count approved facts dated in the review period | §2.4, §3, R3, R4, R16, stamps and flags logic | 1, OQ-D1, OQ-D4 | 1.5 |
| 3 | Review records open only through the portal's rules; the manager sees a self-review once it is sent; nobody rates their own review | SEC-5, PRIV-1, PRIV-2, SEC-6, SEC-10, draft-save bug, scorecards, M3 report | 1 | 1.5 |
| 4 | Review screens show the review's copies, never the live records | §6.1, VIS-3, SEC-7 pages, R10 view | 2, 3 | 0.75 |
| 5 | Ratings, removals and definition changes are made on the copies | §6.2, SEC-1, R2 inside, R7 answers, R11, R12, retired endpoints | 4, OQ-D5, OQ-D6, OQ-D7 | 1.5 |
| 6 | A review freezes where the organisation says, and hands back agreed changes once | R6, R15, VIS-7, completion block | 5, OQ-D10 | 1.0 |
| 7 | An Objective or KPI in an open review keeps its definition until the review ends or the lock is released | R2 outside, R9 release, R11 delete, refresh hook, `attach_ongoing` role check | 2 | 1.0 |
| 8 | Outside screens show no ratings and a plain "in review" badge; HR cycle screens read the review record | R5, R14, R8, SEC-2 | 2, 7, OQ-D8, OQ-D12, OQ-D13 | 1.0 |
| 9 | Reviewers are found and invited from the reviewed person's company | picker, SEC-7 invitees | 3 | 0.5 |
| 10 | Remind HR when Objectives and KPIs stay locked after a cycle ends | R9 reminder | 7 | 0.25 |
| 11 | Portal page: the review screens work on copies | §11 | 4–9, OQ-D1, OQ-D11 | 2.0 |
| 12 | Copy existing reviews, with a dry-run report and a rollback script | §10 | 1–6 | 1.0 |
| — | Whole suites, scale test, browser trace, implementation notes | §13 | all | 1.0 |

**Total: about 13.75 days, 12 commits** (range 12.5–15.5, depending mostly on OQ-D1,
OQ-D5 and the page). Portal Org Settings screen for the settings: +0.5 day if wanted.

---

## 17. Risks, trade-offs and consequences nobody asked about yet

1. **R4 and the portal's wording disagree** (short answer 1). Built as decided without
   changing the dialog, every Cumulative KPI entered as running totals is over-counted
   in reviews. **Highest risk.**
2. **Two numbers for one KPI.** Outside shows the last typed value; the review shows
   approved, dated facts. Expect questions from employees. The long-term fix is one
   progress model for originals too (F-14, Q22), which is outside this slice.
3. **Late logging falls out of the period** (short answer 3).
4. **The lock will surprise HR.** A typo in a held target can only be fixed inside the
   review, or after release. The error message says how.
5. **Write-back can be refused at completion** (weightage over 100% on the original's
   cycle). Completion still happens; the note says what was not written.
6. **First refresh after go-live may flag ratings** on tenants whose stored numbers differ
   from facts. The dry run counts them; on ppj it is 0.
7. **History that cannot be rebuilt.** On tenants where originals were moved out of
   completed cycles, those reviews get no copies. The report names them.
8. **Setting changes mid-cycle.** Freeze point is stamped per review, so a change applies
   to reviews opened after it. Release days and removal behaviour apply at once.
9. **Rollback hides ratings given after go-live** unless the rollback script runs.
10. **The review flow has almost no existing tests** (§9.2). Regressions outside the
    paths I pin could go unseen; the browser trace matters.
11. **Retiring the per-KPI additional reviewer endpoints** removes an API-only feature
    with no data on ppj. Other tenants may have used it through the API; the dry run can
    count `tabKPI Additional Reviewer` rows.
12. **`hrms-employee.html` is the most-changed file.** A Wave 1 split during this build
    means moving my edits into includes.
13. **Found while reading, not fixed here:** `hr_api.approve_kpi_progress` /
    `reject_kpi_progress` import functions that do not exist; `Goal Check In` is not
    synced on ppj; future Objectives from the wizard are created with an invalid status
    and no dates, and the error is swallowed (B7); `hr_generate_appraisals` runs
    synchronously for every employee (API only today, so not moved to a background job
    here).

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| **OQ-D1** | R4 sums readings for a Cumulative KPI, but the portal asks for "the cumulative value reached so far". Change the dialog to "amount since your last update" for Cumulative and "current reading" for Absolute (recommended)? And confirm the Objective rows in §3.1 (evidence summed; goal updates as readings) | **User** | Commits 2, 11 |
| **OQ-D2** | A reading's date is the day it is typed. May people choose the date a reading is for (not in the future, not before the item's period)? Recommended yes, +0.5 day | **User** | Commits 2, 11 |
| **OQ-D3** | Accept that the review number and the live number differ (approved, dated facts vs last typed value)? | **User** | Everything; no build change if yes |
| **OQ-D4** | Copies are taken on first open of the review, not when HR creates the cycle (recommended, because goal setting may still be going on) | **User** | Commit 2 |
| **OQ-D5** | Who may change a definition inside the review: employee in Employee Review, manager in Manager Review, HR in HR Review — and the manager's submit counts as "agreed" (R15)? | **User** | Commits 5, 6 |
| **OQ-D6** | A rating flag raised after the manager has submitted: the manager answers from the Reviews list at any stage before Completed; HR may answer with a reason if the manager has left; if the overall rating changes after it was released, the employee gets an email. Agree? | **User** | Commit 5 |
| **OQ-D7** | Self-rating flags are information only and do not block HR (the employee cannot reopen a sent review). Agree? | **User** | Commit 5 |
| **OQ-D8** | R14 covers Objective and KPI ratings. The overall rating in scorecards and review lists follows the release rule (from Employee Final Review) instead. Agree? | **User**, with security (`01d`) | Commit 8 |
| **OQ-D9** | Settings in HR Settings custom fields (recommended), or the Default store used by field check-in? Also on the portal Org Settings screen now (+0.5 day)? | **User** | Commit 1 |
| **OQ-D10** | A return to a stage before the freeze point unfreezes the numbers (recommended). Agree? | **User** | Commit 6 |
| **OQ-D11** | On the Future Objectives page, "Remove" on a carried-forward goal stops deleting that earlier goal and only unticks it. Agree? | **User** | Commit 11 |
| **OQ-D12** | HR's CSV keeps the live record's id next to the copy (for reconciling). Allowed under VIS-3? | hrms-security-privacy-engineer (`01d`) | Commit 8 |
| **OQ-D13** | SEC-2 built stricter: nobody writes KPI rating fields any more (legacy, HR read-only). Adopt? | hrms-security-privacy-engineer | Commit 8 |
| **OQ-D14** | Is anyone else working in the review screens, `performance_api.py` or `hrms-employee.html`? Has Wave 1's include split started? | Surbhi | Build start |
| **OQ-D15** | Cancelling an original that an open review holds stays allowed; the copy stays and shows "cancelled after the review started". Agree? | **User** | Commit 7 |

## Assumptions

- [ASSUMPTION] Frappe v16.33.1 reads child rows only through the parent's permission, so
  removing the Employee DocPerm closes `Alvoraa Review Item` too. `db_query.py:612-628`
  passes `parent_doctype`; a REST test proves it (§13).
- [ASSUMPTION] `on_update` runs after saves made with `flags.ignore_validate`
  (`recalculate_progress`). A test proves it; if not, the refresh-on-open safety net still
  applies.
- [ASSUMPTION] "Review period" in R3 means the Appraisal's start and end dates,
  narrowed by the copy's own period.
- [ASSUMPTION] R12's "manager or HR later" means Manager Review for the manager and HR
  Review for HR.
- [ASSUMPTION] ppj counts (2026-09-15) are demo data and not typical. Dev tenants were not
  checked; I cannot reach them.
- [ASSUMPTION] Backfill time (1–2 minutes for 806 reviews) is an estimate, not a
  measurement.
- [ASSUMPTION] Sizes are one engineer on the local bench, with OQ-D1 to OQ-D5 answered
  before commit 2 starts.
- [ASSUMPTION] Group D ships as one batch to dev, on your word.

## Mapping to security, privacy and visibility requirements

| Requirement | Mechanism (section) | Commit | Pin test | 01d id (to fill) |
|---|---|---|---|---|
| SEC-1 | Copies of this review only; key check; no progress write (§6.2) | 5 | `test_sec1_…` | |
| SEC-2 | Rating fields permlevel 1, no writer, controller guard (§8) — stricter, OQ-D13 | 8 | `test_sec2_…` | |
| SEC-5 | Employee DocPerm removed (§8) | 3 | `test_sec5_…` | |
| M3 | Read-only report (§10.2 query 5) | 3 | `test_backfill_…` (report part) | |
| SEC-6 | `_authorise_review_action`, no create before check (§6.1–6.2) | 3 | `test_sec6_…` | |
| SEC-7 | Reviewer pages, no create, subject's company (§6.1, §6.8) | 4, 9 | `test_sec7_…`, `test_picker_…` | |
| SEC-10 | `access.refuse_own_rating` (§6.3) | 3, 5 | `test_sec10_…` | |
| PRIV-1 | `_review_fields_for`; potential removed from final review, tree payload, Overview card, scorecards (§6.1, §6.5) | 3, 8, 11 | `test_priv1_…`, `test_r14_…` | |
| PRIV-2 | Blank self-review before sent and after return (§6.1) | 3 | `test_priv2_…` | |
| PRIV-5 (picker, decision 2) | Subject's company, managers and HR only (§6.8) | 9 | `test_picker_…` | |
| SEC-16 | Ceiling held (§8) | all | `test_sec16_…` | |
| SEC-17 | `access.refuse` on every new refusal | all | `test_sec17_…` extended | |
| VIS-1 | M2 child table (§2.1) | 1, 2 | `test_r1_outside_payloads_…` | |
| VIS-2 | Parent permission + SEC-5 | 1, 3 | `test_r1_child_rows_unreachable_…` | |
| VIS-3 | Readers built from copies, row names only (§6.1) | 4 | `test_r1_inside_payload_…` | |
| VIS-4 | `ensure_review_items` once (§2.4) — moment changed by OQ-D4 | 2 | `test_r1_copies_taken_once_…` | |
| VIS-5 | Dialog adds/removes copies, no cycle write — removal now by R12, stages per §2.5 | 5 | `test_r12_…` | |
| VIS-6 | Ratings on copies (§6.2) | 5 | `test_r13_…` | |
| VIS-7 | Scoring reads copies (§5.4) | 6 | `test_vis7_…` | |
| VIS-8 | **Changed by R3, R6, R11:** facts reach the copy by date until the freeze point (default HR sent); deletes refused while held; cancel allowed (OQ-D15) | 2, 6, 7 | `test_r3_…`, `test_r11_…` | |
| VIS-9 | **Changed by R6:** unfreeze on return before the freeze point, facts flow again (OQ-D10) | 6 | `test_r6_…` | |
| VIS-10 | Completed copies read-only for everyone | 6 | `test_r15_…` | |
| VIS-11 | Copies independent of originals after completion | 6, 7 | `test_r15_…` | |
| VIS-12 | Desk KPI list stays on originals, labelled (R8) | 8 | `test_r8_…` | |
| VIS-13 | **Decided by R8:** HR cycle screens read copies | 8 | `test_r8_…` | |
| VIS-14 | Unselected originals have no copy | 2 | `test_r1_copies_taken_once_…` | |
| VIS-15 | Future Objectives stay originals, not copies | 4 | `test_r1_…` | |
| R1–R16 | §2–§7 | 1–12 | one named test each (§13) | |

## Handoff note

To the user first, then the DevOps engineer (07 §4) and the security engineer (`01d`):

**Do not approve R4 as written without OQ-D1.** The KPI dialog asks for running totals,
and R4 adds readings up. Everything else in 00c can be built as decided.

DevOps, please look at three things:
1. The backfill patch runs inside `bench migrate`, on every tenant, with no automatic undo
   for ratings given after go-live (§10.3).
2. The KPI index change locks `tabKPI` briefly during migrate.
3. The daily reminder job and the refresh hook on every KPI and Objective save.

Security, please check three places where I differ from `01c`:
1. SEC-2 is stricter: nobody writes KPI rating fields.
2. R14 is read as Objective and KPI ratings only (OQ-D8).
3. HR's export would keep the live record id (OQ-D12).

`hrms-employee.html` is hot. If Wave 1 has started, I rebase onto it before commit 11.

**Waiting for approval of this strategy.**
