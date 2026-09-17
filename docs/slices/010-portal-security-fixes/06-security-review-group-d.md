---
slice: 010-portal-security-fixes
artifact: 06-security-review-group-d
author: hrms-security-privacy-engineer
date: 2026-09-17
status: draft, for the user's decision
inputs: [01d-security-privacy-group-d.md (VIS-1..15, SEC-1/2/5/6/7/10, PRIV-1/2, SEC-18..30, PRIV-9..15), 00e-group-d-approved-decisions.md (decisions 1-33, binding), 00d-impact-analysis-group-d.md, 03d-implementation-notes-group-d.md, code at slice/010-portal-security-fixes cbdc63e (group D commits after c27fb56), tests test_review_copies_010d.py, test_review_screens_010d.py, test_review_outside_010d.py, test_review_page_010d.py, test_portal_security_010.py, hrms/hrms/alvoraa_hr_core/access.py, Frappe v16.33.1 source on hrlocal-bench, read-only probes on test_site (rolled back, SQL generated with run=0, no rows written), security-compliance-baseline.md (entries of 24 Aug and 6 Sep 2026)]
---

# 010 group D: security and privacy review

## Verdict: Block (1 Blocker, 5 Major, 8 Minor)

**The copy design is built well and most of it is proven by tests. But one side door
undoes two of your decisions: any System Manager can read every review's change
history and audit notes through the REST API, at any stage, including their own
potential rating.** This is the Blocker. The fix is small.

What that means in plain words:

- **Blocker B1.** Frappe keeps a change history ("Version" rows) for the review record,
  and group D writes its audit notes as "Comment" rows. Neither has a row rule. A System
  Manager can list them for every review. They hold ratings, potential ratings, self-review
  drafts and removal reasons. Decisions 15 and 27 said this must not happen.
- **Major M1.** Three older scoring calls (`sync_appraisal_from_kpis`, `submit_appraisal`,
  `suggest_ratings`) still let any HR person act on any company's review at any stage. One
  of them submits the appraisal.
- **Major M2.** A KPI's creator can **rename** it. A rename skips the definition lock, so
  the lock no longer applies to that KPI, and the review's copy loses its facts.
- **Major M3.** A manager who also holds an HR role can rate a report, calibrate the
  overall rating and complete the review alone. Nobody else is involved.
- **Major M4.** HR still reads HRMS `Appraisal` scores in the desk at any stage, and for
  every company when HR has no Company user permission.
- **Major M5.** The release checklist in `03d` §8 names two backfill functions that do not
  exist, and leaves out the rating copy-back step. Someone running it would be stuck, or
  would roll back in the wrong order.

**What is good.** The lock sits in the document layer. Ratings on live KPIs are closed
for every role. The review readers all go through one field filter. The HR cycle screens
follow company and stage. The child copy table cannot be listed around the review
record (I checked Frappe v16's SQL). Everything the page draws is escaped.
`ignore_permissions` went down (278 → 255 across our apps; `performance_api.py` 88 → 64).
Logs carry names and counts only.

No live customers yet (memory, 14 Sep 2026), so none of this starts a reporting clock.
**You decide what happens next.** I am not a lawyer; where an answer turns on the law,
it is listed as a question for counsel.

---

## 1 · Threat model, re-checked against the code

| Question | What `01d` said | What the code does now |
|---|---|---|
| **1. Who wants it, cheapest way in** | Insiders with a session: employee editing what feeds the score, manager hiding a bad item, HR-role subject closing their own review, curious colleague or reviewer reading ratings | Mostly closed. **Still open:** a System Manager lists Version and Comment rows (B1); any HR person calls three scoring endpoints for any company (M1); a KPI creator renames the KPI to escape the lock (M2); a manager with an HR role does every step alone (M3) |
| **2. Blast radius** | One review for most paths; whole tenant for `attach_ongoing_to_cycle`, settings, write-back | `attach_ongoing_to_cycle` is HR-only, company-scoped and skips held items. Write-back never overwrites a later change. **B1 is whole tenant** (every review's history). **M1 is whole tenant** for HR. Nothing crosses tenants (one database each) |
| **3. What is newly possible** | A second, frozen store of decision records; freeze, removal, stamp answers, write-back | Built as designed. New store is written only through `save_review_record` (`review_items.py:431-443`), refused otherwise by `alvoraa_appraisal_extension.py:31-61`. **New and unplanned:** the store's full history also lands in Version rows, readable outside the rule (B1) |
| **4. How would we find out** | Today we would not; group D must audit freeze, removal, answers, write-back | Audit entries exist for removal, delete, definition change, flag answer, freeze and unfreeze (`review_items.audit`), and write-back leaves an Info entry on the live record. Refusals and CSV exports are logged with names and counts. **Not detected:** reads of Version/Comment rows, reads through the three scoring endpoints, and a KPI rename. Security logs are still in France (CERT-In gap, baseline §3a) |

---

## 2 · Requirement verification

"Test" names are in `alvoraa_portal/alvoraa_portal/tests/`. I did **not** run them (see
§5). Results are from `03d` (phases 1–4, all passing) and from slice 012's final full run
on local `dev` `2db1d71`, which contains every group D commit.

### 2.1 Visibility rules

| ID | Status | Mechanism in the diff | Test that proves it |
|---|---|---|---|
| VIS-1 | **Met** | Copies live only on the Extension child table; `KPI_FIELDS` has no rating (`performance_api.py:263-269`) | `test_review_outside_010d.test_r14_priv9_outside_payloads_carry_no_objective_or_kpi_rating` (11 payloads, 3 viewers) |
| VIS-2 | **Met** | `has_appraisal_extension_permission` + `appraisal_extension_query` (`alvoraa_goals/permissions.py:197-256`), hooked at `alvoraa_goals/hooks.py:52,59`. **Checked on test_site:** Frappe v16 joins the parent and applies its condition when HR lists `Alvoraa Review Item` directly. But see B1 for Version/Comment | `test_review_copies_010d.test_sec5_…`, `test_sec27_…` |
| VIS-3 | **Met** | `review_payload` addresses copies by row name; `_review_row` refuses anything else (`performance_api.py:4271-4276`) | `test_review_screens_010d.test_vis3_…`, `test_review_outside_010d.test_vis3_get_cycle_items_…` |
| VIS-4 | **Met** | `ensure_review_items` once per review (decision 4: first open) | `test_review_copies_010d.test_vis4_…` |
| VIS-5 | **Met** | `_selection_record` (subject, ER only), `add_items`, `remove_item`; no cycle write (`performance_api.py:3980-4105`) | `test_review_screens_010d.test_vis5_…` |
| VIS-6 | **Met** | `set_item_rating` on copies; old KPI rating endpoints retired | `test_vis6_r13_…` |
| VIS-7 | **Met** | `_scored_items` reads copies; refuses with no copies (`performance_api.py:1265-1290`) | `test_vis7_…`. Note: a brand-new appraisal is still projected from live records, which can carry legacy ratings (`03d` phase 3 gap 3) |
| VIS-8 | **Partial** | Facts routed by date; lock on `before_validate` / `on_trash`. **Rename skips it (M2)** | `test_r3_…`, `test_r2_sec19_…`, `test_r11_a_held_record_…` |
| VIS-9 | **Met, as changed by decision 18** | `apply_stage` unfreezes on return (`review_items.py:1365-1391`) | `test_r6_decision18_…` |
| VIS-10 | **Met** | Extension guard refuses any change to a Completed review's copies, flag or not (`alvoraa_appraisal_extension.py:38-54`) | `test_vis10_…`; backfill keeps it (`test_backfill_copies_history_…`) |
| VIS-11 | **Met** | Completed copies immutable; `attach_ongoing_to_cycle` skips held items (`performance_api.py:1094-1111`) | `test_sec20_…`, `test_vis10_…` |
| VIS-12 | **Met** | `kpi_list.js`, `individual_goal_list.js` label | `test_r8_vis12_…` |
| VIS-13 | **Met** | `_hr_cycle_reviews`, `_copies_of`, `_visible_ratings` (`performance_api.py:2459-2540`) | `test_sec26_hr_cycle_screens_…`, `test_r8_sec26_the_csv_export_…` |
| VIS-14 | **Met** | Copy helper skips unselected, cancelled, future items | `test_vis14_vis15_…` |
| VIS-15 | **Met** | `submit_employee_review` creates future objectives with no cycle; a failure stops the submission (`performance_api.py:4197-4216`) | `test_vis15_a_future_objective_…`, `test_vis15_future_objectives_list_…` |

### 2.2 Items re-stated from `01c`

| ID | Status | Mechanism | Test |
|---|---|---|---|
| SEC-1 | **Met** | `apply_self_review` checks every key is this review's live copy; no progress write (`review_items.py:1109-1141`) | `test_sec1_…` |
| SEC-2 | **Met** | `refuse_rating_changes` on KPI `before_validate`, no role exempt (`controllers/kpi.py:141-164`); rating fields at level 1, no write for anyone. Only the rollback helper passes, with a document flag | `test_sec2_rating_fields_sit_at_level_1…`, `test_sec2_nobody_writes_a_rating…`, `test_sec2_static_…` |
| SEC-5 | **Met** | Employee DocPerm removed; hooks deny non-HR even with a Custom DocPerm; M3 report (`review_items.py:734-776`). Dev tenants checked read-only 2026-09-17, clean (work board; not by me) | `test_sec5_…`, `test_m3_…`, `test_decision26_m3_…` |
| SEC-6 | **Met** | `_manager_review_record`, `_review_actor`, `_extension` never creates | `test_sec6_calls_from_people_who_may_not_act_create_no_review_record` (15 endpoints) |
| SEC-7 | **Met** | Invitation checked first; MR only; pages cut; copies only with `past-objectives` (`performance_api.py:4739-4807`); `_check_invitees` (`:1759-1772`) | `test_sec7_an_invited_reviewer_…`, `test_sec7_invitees_…`, `test_decision17_…` |
| SEC-10 | **Met for own review** | `refuse_own_rating` in `access.py:76-90`, called from every decision path | `test_sec10_an_hr_manager_cannot_rate_calibrate_or_close_their_own_review`. **Related gap: M3** (same person as manager and HR) |
| PRIV-1 | **Partial** | `rating_fields_for` / `review_payload`; `get_employee_final_review` drops potential (`performance_api.py:4951-4961`). **A System Manager subject reads their own potential rating in Version rows (B1)** | `test_priv1_…` (3 tests) |
| PRIV-2 | **Partial** | Review readers refuse before sending. **Gaps:** `suggest_ratings` has no stage check, so a direct manager lists the draft's chosen items in ER (M1); HR screens treat an HR-role line manager as "manager" in ER and list copy titles (m7) | `test_priv2_…` |

### 2.3 New security requirements

| ID | Status | Mechanism | Test |
|---|---|---|---|
| SEC-18 | **Met** | `search_employees(appraisal)`: line or HR under stage rule; subject's company; never the subject; 50 max (`performance_api.py:1699-1756`) | `test_sec7_decision2_the_picker_…` |
| SEC-19 | **Partial** | `enforce_definition_lock` on `before_validate` and `before_update_after_submit`; `refuse_delete_while_held` on `on_trash`; fails closed on lookup error (`review_items.py:1568-1626`). **KPI rename bypasses it (M2).** Static test checks `set_value` only, not `db_set` or SQL (m6) | `test_r2_sec19_…`, `test_r11_a_held_record_…`, `test_r2_static_…` |
| SEC-20 | **Met** | `_require_hr`, permitted companies, held items skipped (`performance_api.py:1058-1115`); `set_cycle_membership` refuses held | `test_sec20_…` |
| SEC-21 | **Met** | Window, freeze point, removal mode stamped at first open; freeze and unfreeze audited | `test_sec21_…`, `test_r16_…`, `test_r6_…` |
| SEC-22 | **Partial** | Release on server date, 0 = never, reminder without names. **Lock release days are read live from HR Settings, not stamped per review** (`review_items.py:1527`) (m1) | `test_r9_sec22_…`, `test_r9_hr_is_reminded_…`, `test_r9_decision32_…` |
| SEC-23 | **Met** | `raise_rating_flags`, unstamped = flagged, completion refused while open (`performance_api.py:3032-3043`), rater or HR-for-former-rater with reason (`:4414-4483`) | `test_r7_sec23_…`, `test_r7_decision12_…` (2), `test_sec23_a_rating_with_no_stamp_…` |
| SEC-24 | **Met, as narrowed by decision 29** | `_review_actor` stages; reason and acknowledgement required; rated copy always kept; audit in both modes (`performance_api.py:4301-4327`, `review_items.py:1161-1183`) | `test_r12_sec24_…` |
| SEC-25 | **Met** | `write_back` compares with `definition_at_start`, writes once, savepoint, Info entry on the live record (`review_items.py:1403-1463`). The entry names the review but not who agreed (that sits on the copy) | `test_r15_sec25_…`, `test_sec25_a_live_record_changed_…`, `test_decision30_…` (2) |
| SEC-26 | **Met for the five screens** | `_hr_cycle_reviews` viewer per row; CSV formula-safe, one log line with counts (`performance_api.py:3294-3366`) | `test_sec26_…`, `test_r8_sec26_…`, `test_priv1_sec26_…`, `test_query_count_hr_cycle_screens_…`. **Same data reachable outside it: M1, M4** |
| SEC-27 | **Partial** | Extension read by stage and company, never own, no desk write (`permissions.py:197-256`). **Version and Comment rows are not covered (B1)** | `test_sec27_…`, `test_decision15_…` |
| SEC-28 | **Met** | HR Settings fields, `validate_hr_settings`, `save_review_settings` HR Manager only, POST only, document save with caller's permission, Version row plus security log line (`performance_api.py:5087-5117`) | `test_sec28_…` (5), `test_decision23_…` (2) |
| SEC-29 | **Met by retirement** | `add_additional_reviewer`, `save_additional_reviewer_rating` refuse (R13) | `test_vis6_r13_…` |
| SEC-30 | **Met** | `_require_hr` on `get_calibration_signoff` (`performance_api.py:5046`) | `test_sec26_sec30_…` |

### 2.4 New privacy requirements

| ID | Status | Mechanism | Test |
|---|---|---|---|
| PRIV-9 | **Met** | No rating in outside payloads; KPI rating fields level 1 (HR read); Employee row removed from HRMS Appraisal (decision 26); `get_appraisal_data` totals follow release | `test_priv9_…` (2), `test_r14_priv9_…`, `test_decision26_…` |
| PRIV-10 | **Met** | `review_badges` returns `{in_review, updates_after}` only (`review_items.py:1539-1554`); page escapes it | `test_r5_priv10_…`, page pins |
| PRIV-11 | **Met** | `late_facts` only for HR viewer in HRR/C | `test_r10_…` |
| PRIV-12 | **Met (decision 10)** | Subject sees label, date and reason from EFR; never "who"; reviewers never (`review_items.py:1001-1017`) | `test_r12_sec24_…`, page `test_decision10_…` |
| PRIV-13 | **Met** | Stamps and flags only for manager and HR viewers | `test_priv1_priv13_…` |
| PRIV-14 | **Partial** | Extension delete refused below Administrator by `has_permission`; rated copies kept. **No `on_trash` guard, no test**, and `undo_backfill` deletes rows directly (operator only) (m4) | none |
| PRIV-15 | **Partial** | Log lines carry names and counts (`access.py:24-44`, `review_items.py:1455,1662,1775`, `review_backfill.py:338,506`); reminder has no names. **No marker test across removal, flag answer and write-back;** write-back note on the live record holds old and new values (m3) | `test_r9_hr_is_reminded_…` (reminder only) |

**Count:** 43 items (15 VIS, 8 re-stated, 13 new SEC, 7 new PRIV). **Met 35**, including
VIS-9, SEC-24 and PRIV-12 as changed by a decision, and SEC-10 and SEC-26, which are met
but have a related gap elsewhere (M3, M1, M4). **Partial 8:** VIS-8, PRIV-1, PRIV-2,
SEC-19, SEC-22, SEC-27, PRIV-14, PRIV-15. **Not met 0.**

---

## 3 · Findings

### Blocker

**B1 · A System Manager reads every review's change history and audit notes, at any stage, including their own potential rating.**

- **Where:** `alvoraa_goals/alvoraa_goals/alvoraa_goals/doctype/alvoraa_appraisal_extension/alvoraa_appraisal_extension.json:93` (`track_changes: 1`);
  `alvoraa_goals/alvoraa_goals/review_items.py:431-443` (every copy change is a document save, so Frappe writes a Version row outside tests);
  `review_items.py:1671-1677` (audit notes are Comment rows);
  `alvoraa_portal/alvoraa_portal/performance_api.py:4320-4324` and `:4466-4470` (removal reasons and "answering for" reasons go into those Comments);
  `alvoraa_goals/alvoraa_goals/hooks.py:52,59` (row rules exist for the Extension only).
- **Checked in Frappe v16.33.1 on the bench:** `Version` read is System Manager; `Comment`
  read is System Manager and Website Manager. Neither has a `has_permission` or
  `permission_query_conditions` hook. A `get_list` on either produces plain SQL with no
  row condition (probe on test_site, SQL only, nothing written). A Version row's `data`
  holds whole added rows and every changed field, old and new.
- **Scenario 1 (decision 15).** Priya holds System Manager and is not in Rahul's line.
  Rahul's review is in Manager Review. Priya calls
  `GET /api/resource/Version?filters=[["ref_doctype","=","Alvoraa Appraisal Extension"]]&fields=["docname","data"]`.
  She reads the manager's item ratings, potential ratings and Rahul's self-ratings as they
  were typed. The desk and portal both refuse her the same review.
- **Scenario 2 (decision 27, "potential never").** Arjun holds System Manager and has his
  own open review. He filters the same call on his own review's name and reads the
  `potential_rating` his manager gave him. Decision 27 refused exactly this in the desk.
- **Scenario 3.** Any System Manager or Website Manager lists
  `Comment` rows for the Extension and reads every removal reason ("Reason: …") and every
  HR "answering for a former rater" reason, for every company.
- **Why it is a Blocker:** personal performance data, including potential, reaches an
  audit table that a person the decisions call non-entitled can read.
- **Fix (one mechanism):** add `has_permission` and `permission_query_conditions` for
  `Version` and `Comment` that, when `ref_doctype` / `reference_doctype` is
  `Alvoraa Appraisal Extension`, apply the same rule as
  `has_appraisal_extension_permission` (other doctypes unchanged). Add a test: System
  Manager, stranger's review in MR and own review in HRR → no Version or Comment rows
  returned; HR in HRR → returned. The alternative, turning off `track_changes` on the
  Extension, loses history that grievances need, so I do not recommend it.

### Major

**M1 · Three scoring endpoints let any HR person act on any company's review at any stage, and one of them submits the appraisal.**

- **Where:** `performance_api.py:150-158` (`_require_can_review` returns at once for any
  HR role, System Manager included); callers `suggest_ratings` `:946-965`,
  `sync_appraisal_from_kpis` `:990-1015`, `submit_appraisal` `:1371-1394`. None calls
  `_assert_hr_can_view` or checks the stage. Reachable from the page:
  `hrms-employee.html:10928`, `:10938`, `:15732`.
- **Scenario A (read).** Meena is HR User for Company A only. Sunil works for Company B;
  his review is in Manager Review and his manager has rated four items. Meena calls
  `sync_appraisal_from_kpis(<Sunil's appraisal>)`. It writes Sunil's in-progress scores to
  the HRMS Appraisal and returns `total_score` and `final_score`. Decision 16 and SEC-26
  say she gets nothing for Company B, and no ratings before HR Review.
- **Scenario B (write).** Same Meena calls `submit_appraisal(<Sunil's appraisal>)` while the
  manager is still reviewing. If every item has a rating, the HRMS Appraisal is submitted
  (docstatus 1). The manager's later syncs fail with "already submitted".
- **Scenario C (PRIV-2).** Sunil's manager calls `suggest_ratings(Sunil, cycle)` while Sunil
  is still in Employee Review. The reply lists the items Sunil has chosen for his draft.
- **Tests:** only the own-review refusal is pinned (`test_review_copies_010d.py:969-971`).
- **Fix:** in all three, after `refuse_own_rating`: if the caller is not in the line, call
  `_assert_hr_can_view`; refuse before Manager Review for everyone. Pin HR-other-company
  and manager-in-ER cases.

**M2 · Renaming a KPI takes it out of the definition lock.**

- **Where:** `alvoraa_goals/alvoraa_goals/alvoraa_goals/doctype/kpi/kpi.json:3`
  (`allow_rename: 1`, unchanged from c27fb56); Employee has write at level 0 and
  `has_employee_permission` gives write to the creator (`alvoraa_goals/permissions.py:154-159`);
  Frappe's `update_document_title` checks only write (`frappe/model/rename_doc.py:59`) and
  a rename runs no `before_validate`; group D adds no `before_rename` hook
  (`alvoraa_goals/hooks.py`); `holds()` matches on `source_name`, a Data field that a
  rename does not update (`review_items.py:1500-1523`).
- **Scenario.** Rahul created KPI `KPI-00412`. His open review holds it. He calls
  `POST /api/method/frappe.model.rename_doc.update_document_title` with
  `doctype=KPI, docname=KPI-00412, name=KPI-00412-b`. Frappe allows it. Now `holds()` finds
  nothing, so he lowers `target_value` through `PUT /api/resource/KPI/KPI-00412-b`, which
  the lock would have refused. Next time the review is opened while still unfrozen, the
  copy finds no facts under the old name and recounts to 0, raising rating questions.
  At completion, write-back says "the live record no longer exists". HR can do the same
  to anyone's KPI.
- **Not run:** a rename is a database write, which this review may not do. This is from the
  code and the Frappe source.
- **Fix:** a `before_rename` doc event on KPI (and Individual Goal, for safety) that refuses
  while `holds()` finds the record, logged as rule R2; or set `allow_rename` to 0 on KPI.
  Add a test.

**M3 · A manager who holds an HR role can rate, calibrate and complete a report's review alone.**

- **Where:** `performance_api.py:83-84` (`_assert_hr_can_view` returns for anyone below
  the caller); `save_calibration_note` `:3558-3590` and the HR Review step of
  `advance_review_status` `:3010-3014` rely on it; `refuse_own_rating` blocks only the
  subject.
- **Scenario.** Gurpreet manages Vinod and holds HR Manager. In Manager Review he rates
  Vinod's items and overall rating. Vinod acknowledges. In HR Review Gurpreet calls
  `save_calibration_note(<Vinod's appraisal>, "…", calibrated_rating=2)`, then
  `advance_review_status` to Completed. Every call passes. No second person saw it. On
  ppj the managing director holds HR Manager and sits at the top of the tree, so this
  covers every review in the company.
- **Rule it breaks:** `01d` §3 defines HR as acting "for a subject … who is not in their
  own line", and the baseline's ISO/IEC 27001 segregation of duties. It is older
  behaviour, not new in group D, but group D made calibration and completion decision
  points (stamps, write-back).
- **Needs your decision:** either refuse the HR steps (calibrate, HR removal, HR flag
  answer, HR Review → Completed) to anyone in the subject's line, or accept it in writing
  for small organisations. I recommend refusing, with a clear message naming who else can
  do it.

**M4 · HR reads HRMS Appraisal scores in the desk at any stage, and for every company when it has no Company user permission.**

- **Where:** `hrms/hrms/hr/doctype/appraisal/appraisal.json` permissions (HR User and HR
  Manager read and report; System Manager read); no permission hook for Appraisal in
  `hrms/hrms/hooks.py`; scores are written from the copies' manager ratings by
  `_apply_kpis_to_appraisal` (`performance_api.py:1321`, via `_scored_items` `:1284`).
- **Scenario.** Farah is HR User with no Company user permission; `permitted_companies()`
  gives her only her own company. In the desk she opens Report Builder on Appraisal with
  `total_score` and the `goals` table. She sees in-progress scores for every company's
  reviews that are still in Manager Review, which decisions 15 and 16 closed on the review
  record.
- **Fix:** a `has_permission` / `permission_query_conditions` pair on Appraisal that applies
  the same stage and company rule as the Extension for HR roles (the subject already has
  no role). Or accept it, with a name and date, as HR-trusted.

**M5 · The release checklist would fail or roll back in the wrong order.**

- **Where:** `03d-implementation-notes-group-d.md:1308` names
  `alvoraa_goals.review_backfill.dry_run(site)` and `:1327` names
  `alvoraa_goals.review_backfill.rollback(site)`. Neither exists. The real functions are
  `report()`, `undo_backfill(dry_run=1)` and `copy_ratings_back_for_rollback(dry_run=1)`
  (`review_backfill.py:224,384,449`). `:1319` says the permission report covers
  `Individual Goal`; it does not (`review_items.py:751-753`). The phase 4 rollback text
  also drops the step that puts ratings back on live KPIs before a code revert, which the
  phase 3 section (`03d:1004-1009`) has.
- **Scenario.** On release night the operator runs the §8 checklist. Step 2 errors, so there
  is no dry run. If a rollback is needed, "rollback(site)" errors; if they improvise with
  `undo_backfill` first and revert, ratings given in the portal after go-live stay only on
  copies that the old code never reads.
- **Why Major:** a rollback runbook that has never been exercised and names the wrong
  commands is not a capability. **Fix:** correct §8 from phase 3 §8, and rehearse it on
  ppj.localhost (gate 2 on the release train).

### Minor

| # | Finding | Where | Scenario |
|---|---|---|---|
| m1 | **Lock release days are not stamped per review** (SEC-22 said stamped) | `review_items.py:1527` reads `review_settings()` live | An HR Manager sets days from 30 to 1 on 20 Jul. Every open review whose cycle ended before 19 Jul releases its lock at once; employees edit live targets while their reviews are still open. Copies are safe and write-back will not overwrite, and HR Settings history records who. Stamp `lock_release_days` with the other three at first open |
| m2 | **Approvers cannot see when a back-dated reading was typed** | `goals_api.py:1190-1203` and `performance_api.py:491-505` return `log_date`, not creation time; `_reading_date` allows any day back to the period start (`performance_api.py:336-357`) | On 20 Jul Rahul logs a large reading dated 28 Jun, which lands in his still-open Q1 review. His manager sees "28 Jun" and approves. Return and show "logged on" beside "for" |
| m3 | **Write-back note on the live record holds old and new values**, readable by everyone who can read the KPI (the whole manager line and all HR) | `review_items.py:1447-1450` | PRIV-15 allowed values only in HR-only audit bodies. The values are definitions already visible on the live record, so the harm is low. Put the values on the review record and leave only "changed by review X" on the live record |
| m4 | **PRIV-14 has no test and no `on_trash`**; Administrator and code with `ignore_permissions` can delete a review record with copies; `undo_backfill` deletes rows directly | `alvoraa_appraisal_extension.py` (no `on_trash`); `review_backfill.py:443` | A future cleanup script using `frappe.delete_doc(..., ignore_permissions=True)` deletes decision records silently. Add `on_trash` refusing when copies exist, and a test |
| m5 | **No PRIV-15 marker test** across removal, flag answer, write-back and freeze | tests | Only the reminder has a marker test. Add one test that puts a marker in a label, reason and comment and asserts it is absent from Error Log, Email Queue and Notification Log |
| m6 | **The static lock test sees `set_value` only** | `test_review_screens_010d.py:1064-1066` | A later `doc.db_set("target_value", …)` or `frappe.db.sql("update tabKPI set weightage …")` would pass CI. None exists today (grep). Widen to `db_set` and SQL `update` |
| m7 | **HR screens show an HR-role line manager the draft's item list in Employee Review** | `performance_api.py:2505` sets viewer "manager" regardless of stage; `hr_list_kpis` / CSV then list copy titles and numbers | PRIV-2 says nobody but the subject sees which items were chosen before sending. Low sensitivity (titles and numbers the manager sees on live records anyway). Skip rows in ER for non-subjects |
| m8 | **`approve_kpi_update` lets any HR person approve any company's reading** (group A code, but approved readings now feed review copies) | `performance_api.py:451-455` | HR User of Company A approves a back-dated reading of a Company B employee, which then flows into that employee's open review. Raise separately under decision 16's rule |

### Worries (not findings: I cannot write a full actor-and-path sentence)

- **Dotted-line managers.** `request_dotted_line_feedback` runs on every Appraisal update once
  `total_score` is set (`hrms/hrms/hooks.py:224-237`). Sync now writes copy-based scores.
  I did not check what the stock Employee Performance Feedback form shows them.
- **HR stand-in manager.** For an employee with no manager, the first HR Manager is treated
  as manager (`permissions.py:47-71`). Which HR Manager that is depends on row order, not on
  anyone's choice.
- **Departed employees** with an enabled login: `_employee_id` does not check status. Unchanged
  from `01d`.
- **`delete_review_item`** lets a manager or HR delete a live record the employee created
  inside the review (if unrated and without facts). The page offers it only to the subject.
- **`save_calibration_note` still fails** on the missing `calibration_notes` column
  (F-D8). Its positive path, including the stamp, is untested.

---

## 4 · Compliance verification

I am not a lawyer. These are engineering readings of the baseline (entries verified
24 Aug 2026 and 6 Sep 2026: 24 and 11 days old, not stale; I did not re-verify them
against primary sources because they are within 90 days).

| Obligation | Mechanism in the diff | Test | Discharged? |
|---|---|---|---|
| DPDP 2023 + Rules 2025: reasonable security safeguards, access control | Server-side stage and company rules on review record, copies, HR screens; fail-closed guards; refusals logged | 010d suites | **Partial:** B1, M1, M4 leave side doors |
| DPDP: purpose limitation and minimisation (potential kept from subject; no ratings on outside screens) | `rating_fields_for`, `KPI_FIELDS`, level-1 KPI ratings, Appraisal Employee row removed | `test_priv1_…`, `test_r14_priv9_…` | **Partial:** B1 (own potential via Version) |
| DPDP erasure vs defensible rating | No delete path for copies below Administrator; rated copies always kept | none (m4) | **Partial:** C-D1 with counsel is open; no test |
| GDPR Art 22 (anticipatory): a named human decides, the person can contest | Stamps record rater and answerer; removal reason shown to the employee; nobody rates their own review | `test_r7_…`, `test_sec10_…`, `test_decision10_…` | **Partial:** M3 lets one person decide every step |
| ISO/IEC 27001:2022: segregation of duties, logging | `refuse_own_rating`; audit entries; security log lines | `test_sec10_…`, `test_r8_sec26_the_csv_…` | **Partial:** M3; no detection of Version/Comment reads |
| CERT-In: logs kept 180 days in India | Log lines exist | none | **Not discharged:** hosting in France (baseline §3a), not this slice |
| Feature map E6 (locked definitions, change audit) | `enforce_definition_lock`, `write_back` audit | `test_r2_sec19_…`, `test_r15_sec25_…` | **Partial:** M2 (rename) |
| Feature map D6 (period freeze), E1 (replayable rating) | Stamped window and freeze point; rating stamps with basis numbers | `test_sec21_…`, `test_r7_…` | **Discharged** (m1 is about the lock, not the freeze) |
| Feature map A6 (retention with legal hold) | None built; deletion blocked instead | none | **Not discharged** (out of scope, as `01d` said) |
| Feature map I1 (permission tests in CI) | ~100 group D tests in `alvoraa_portal/tests`; ceilings lowered | `TestSec16IgnorePermissionsCeiling` | **Discharged**; note the counter does not see `db.set_value` (group D added one in `goals_api.save_self_assessment`, behind an owner check) |

---

## 5 · What I could not verify

| What | Why | What it would take |
|---|---|---|
| **Test results** | Running tests needs the work board marked, which is a second file; my brief allows one. I relied on `03d` §6 and slice 012's final run on `2db1d71` | The user or the test engineer runs the three 010d modules and the page pins on test_site |
| **B1 and M2 by execution** | Both need rows written (a Version row, a rename). This review may not write to any database | A rolled-back probe on test_site with the user's word, or the fixes' own tests |
| **Real data** | ppj.localhost is not migrated to group D; test_site has no reviews | The release-train rehearsal (migrate + dry run + browser trace on ppj) |
| **Who holds System Manager or Website Manager on each tenant** | No tenant access in this review | A read-only role count per dev tenant, on the user's word |
| **HRMS Appraisal delete when a review record links to it** (PRIV-14) | Not traced | A rolled-back delete attempt on test_site |
| **What dotted-line managers see** in Employee Performance Feedback | Stock HRMS form not traced | Open the form as a dotted-line manager on a migrated local site |
| **Browser behaviour** of the new page | No browser trace run (`03d` §7) | Run `trace_review_copies_010d.py` after the ppj migrate |
| **Legal points** C-D1 (retention and erasure of copies), C-D3 (withholding potential on an access request), C-D4 (telling employees about removals) | Questions for counsel, still open | Counsel's answers |

---

## 6 · Residual risk

Nothing here is accepted yet. Each row needs your name and a date. "Before push" rows
should be fixed rather than accepted, in my view; you decide.

| # | Risk | Why it remains | Recommend | Accepted by | Date |
|---|---|---|---|---|---|
| R1 | System Manager and Website Manager read review history and audit notes (B1) | No row rule on Version and Comment | Fix before push to dev | — | — |
| R2 | HR acts on any company's review through three scoring endpoints (M1) | Old `_require_can_review` guard | Fix before push to dev | — | — |
| R3 | A KPI creator or HR renames a held KPI and escapes the lock (M2) | `allow_rename` with no `before_rename` | Fix before push to dev | — | — |
| R4 | One person who is both manager and HR decides every step (M3) | Product rule, older than group D | **Fixed by decision 34** (see `03d`, "Decision 34 (M3)") | — | — |
| R5 | HR reads HRMS Appraisal scores at any stage and, without Company user permissions, for every company (M4) | Stock HRMS permissions, no hook | Fix, or accept as HR-trusted | — | — |
| R6 | Rollback runbook names wrong functions (M5) | Documentation | Fix and rehearse before push | — | — |
| R7 | Legacy ratings on live KPIs stay readable to HR in the desk | Decision records, not deleted (PRIV-14) | Accept | — | — |
| R8 | A tenant's Custom DocPerm can re-open KPI level 1, Appraisal or the review record | Custom DocPerm replaces our JSON; the M3 report only lists. Dev tenants clean on 2026-09-17 | Accept; re-run the report before each deploy | — | — |
| R9 | After a code rollback, `copy_ratings_back_for_rollback` puts potential ratings back on live KPIs, where the old code shows them to employees | That is how the old code works | Accept only with the rollback; tell HR | — | — |
| R10 | No retention engine or legal hold for copies (feature map A6) | Out of scope; deletion is blocked instead | Accept until counsel answers C-D1 | — | — |
| R11 | Security and audit logs are in France, not India (CERT-In) | Infrastructure (baseline §3a) | Accept at slice level; tracked in the baseline | — | — |
| R12 | Cumulative KPI numbers change meaning for old readings (decision 1) | No way to tell old intentions apart (`03d` phase 4 gap 3) | Accept; tell HR | — | — |
| R13 | Lock release days follow the current setting, not the one in force when the review opened (m1) | Not stamped | Fix soon, or accept with HR Settings history as the record | — | — |

---

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| Q1 | B1: add row rules on Version and Comment for the review record (recommended), or turn off change history on it? | User | Push to dev |
| Q2 | M3: may someone in the subject's line do the HR steps (calibrate, HR removal, HR flag answer, complete)? | User | Release decision on R4 |
| Q3 | M4: should HR's desk reads of HRMS Appraisal follow the review's stage and company rule? | User | R5 |
| C-D1, C-D3, C-D4 | As in `01d` §7 | Counsel | Retention, potential on access requests, removal notices |

## Assumptions

- [ASSUMPTION] Frappe writes Version rows for the review record in production. I read
  `frappe/model/document.py:576` (skipped only in tests) and did not observe a row.
- [ASSUMPTION] Local `dev` `2db1d71`, where slice 012 ran both full suites, contains every
  group D commit up to `cbdc63e` unchanged. The work board says so; I did not diff it.
- [ASSUMPTION] Slice 012 commits on this branch do not weaken a 010 control. I skimmed their
  file list and the `ignore_permissions` ceilings; I did not review them line by line.

## Handoff note

To the fullstack engineer: fix B1, M1 and M2 first, each with a refusing test; they are
small and local. M5 is a documentation fix plus the ppj rehearsal. M3 and M4 need the
user's decision before code. To the test engineer: add PRIV-14 and PRIV-15 tests (m4, m5)
and widen the static lock scan (m6). To the user: nothing here is pushed or deployed;
the residual-risk table needs names and dates for anything you choose to accept.
