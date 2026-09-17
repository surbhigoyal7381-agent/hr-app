**Verdict: SHIP WITH FIXES.** The design is sound and the server rules hold, but five Majors should be fixed before the dev push. The worst two: a KPI can drop out of an employee's review without warning, and a rejected KPI reading now inflates the live KPI number for good.

`SHIP WITH FIXES` is advice. It is not permission to push. The user decides.

---
slice: 010-portal-security-fixes
artifact: 05-review-group-d
author: hrms-technofunctional-reviewer
date: 2026-09-17
status: review complete, not committed
inputs: [00c-review-copies-decisions.md, 00d-impact-analysis-group-d.md, 01d-security-privacy-group-d.md, 00e-group-d-approved-decisions.md (decisions 1-33), 03d-implementation-notes-group-d.md (phases 1-4), diff c27fb56..cbdc63e (group D commits only), tests test_review_copies_010d / test_review_screens_010d / test_review_outside_010d / test_review_page_010d, read-only queries on ppj.localhost, one test run on test_site]
---

# 010 group D: senior architect review (step 5)

## 0. What was reviewed, and what came in

- **Code:** the 37 group D commits on `slice/010-portal-security-fixes` from `e58ffa2` to `cbdc63e`. The 22 slice 012 commits mixed in between were skipped (`ed8732f`, `1d75c28`, `bdc50c0`, `b89cdfb`, `c692ea9`, `85f0073`, `e6bae5c`, `3c33d56`, `21a2518`, `0fa5952`, `bf79aad`, `96f3ef9`, `3e2f1e0`, `15a2dae`, `bda1290`, `05342a9`, `18e9f7a`, `4de5423`, `502bddf`, `0f1a3ea`, `3a8850a`, `a6e38db`). `1d75c28` and `21a2518` are 012's too, but they were missing from the skip list I was given.
- **Local `dev` has moved on.** It is now at `24eb10a`, not `2db1d71`. Two commits came in, and both are docs only: `18af278` (parallel-work rules, portal redesign plan) and `24eb10a` (slice 012 documents). Group D code on `dev` is the same as on `cbdc63e`. I checked with `git diff cbdc63e 24eb10a`: only 012 files differ.
- **Impact analysis:** present (`00d`), and approved with decisions (`00e`). The process was followed.
- **Prototype:** group D has no `01b` and no clickable prototype. The screens were checked against `00d` §11 and decisions 1-33, not against an approved design. **No browser trace has been run** (03d phase 4 §7). Every page check here comes from reading code.

## 1. Tests I ran

I checked that the bench was free first: the work board said "no" on both rows, and `pgrep -af run-tests` was empty. I marked the board while running and removed the mark when done. Another session started its own run straight after mine finished. Site `test_site`, code = local `dev` (group D code identical to `cbdc63e`).

| Module | Result |
|---|---|
| `alvoraa_portal.tests.test_review_page_010d` | Ran 26 tests in 0.6 s, **OK** |
| `alvoraa_portal.tests.test_review_copies_010d` | Ran 34 tests in 137 s, **OK** |
| `alvoraa_portal.tests.test_review_outside_010d` | Ran 28 tests in 203 s, **OK** |
| `alvoraa_portal.tests.test_review_screens_010d` | Ran 39 tests in 279 s, **OK**; then its separate static-scan class: Ran 1 test in 6 s, **OK** |

I did not run the whole suites. Slice 012's final check ran both whole suites on `2db1d71` (work board, 2026-09-17): only the 14 known local failures. I did not run the page's static checks (`check_portal_handlers.js`, `check_undefined_js.js`); 03d says they pass.

---

## 2. Blockers

None.

---

## 3. Majors

### M1. The KPI add/remove dialog drops KPIs it never showed, or refuses to save at all

`alvoraa_portal/alvoraa_portal/performance_api.py:4085-4094` (`set_review_selection`), with `hrms-employee.html:15532-15542`.

- **Setup:** an employee has a KPI that is linked to an Objective that is not in their review. This is the normal cascade case: the KPI hangs off their manager's Objective (`controllers/kpi.py` `_validate_linked_objective` allows it). It also happens when their own Objective sits in another cycle. The KPI is tagged to the cycle, so it is copied with `parent_item = ""`.
- **What happens:** `live_kpis` takes every KPI copy whose `parent_item` is not a live row, and that includes this one. The dialog lists only KPIs with no `individual_goal` (`get_available_for_review`, `:4031-4043`), so this KPI is never shown and never sent back as ticked. `set(live_kpis) - kpis` therefore puts it in `remove`.
  - The employee unticks nothing and only adds a KPI. The page sends `acknowledge_removal: 0`, and the server refuses: "Removing an item loses what was changed for it inside this review. Confirm the removal to go on." **The employee cannot add anything, and the message makes no sense to them.**
  - The employee unticks any one KPI. The page sends `acknowledge_removal: 1`, and the cascaded KPI is also removed, with no warning. With the default setting (discard), its copy is deleted. **Nobody can put it back from the page:** the dialog never lists it, and nobody adds items after Employee Review (decision 7).
- The same happens to KPI copies whose Objective was just removed from the review: they become standalone copies the dialog does not list.
- **Why it is wrong:** R12 and VIS-5 say removal happens only when the person unticks the item, after a warning. On ppj today, 10 KPIs are cascaded to another person's Objective and 3 link to the employee's own Objective in another cycle. Dev tenants were not checked.
- **Smallest fix:** in `set_review_selection`, only remove KPI copies whose live KPI is one the dialog lists: no `individual_goal`, or an `individual_goal` with no live copy in this review. Add a pin test with a cascaded KPI.

### M2. A rejected reading on a Cumulative KPI stays in the live number for good

`performance_api.py:394-398` (`log_kpi_progress`), and `:457-467` (`approve_kpi_update` does not change `actual_value`).

- **Setup:** a Cumulative KPI at 40 (every KPI on ppj is Cumulative: 3,510 of 3,510). The employee logs 50 by mistake. The manager rejects it. The employee logs the right amount, 5.
- **What happens:** logging adds before approval, so `actual_value` becomes 90, then 95. Rejecting changes nothing. The live number reads 95 when the approved total is 45. `validate_kpi` then works out attainment from 95, and after the period ends `_set_status` marks the KPI "Achieved" instead of "Missed".
- **Why it is wrong:** before group D, the next reading replaced the number, so a mistake fixed itself. Now every rejected or wrong reading stays in the number. Everything that reads the live KPI shows the wrong figure: the Objectives & KPIs tree, My KPIs, the team KPI card's average attainment, the KPI update box ("currently at …%"), and the linked-KPI attainment on the goal detail (`goals_api.get_goal_detail`). The review copy is not affected, because it counts approved readings only. That is why the tests pass. `test_decision1_a_cumulative_reading_adds_up_and_an_absolute_one_replaces` has no rejection case.
- **Smallest fix:** in `approve_kpi_update`, on "Rejected" for a Cumulative KPI, take the rejected value off `actual_value`, only if it was Pending before. Or work out the live Cumulative number as approved plus pending, leaving rejected out. Pin a reject-then-relog test.

### M3. A manager who also holds an HR role cannot rate items, change them or remove them in the page

`performance_api.py:4588` (`"viewer_role": "hr" if is_hr else "manager"`), `hrms-employee.html:15950` (`_pr.viewerRole = d.viewer_role`), and `:15599-15611` (`riCanEditDefinition`, `riCanRemove`, `riCanRateAsManager` need `"manager"`).

- **Setup:** Manager Review. The line manager holds HR Manager or HR User. PP Jewellers' Managing Director holds HR Manager (see the `_assert_hr_can_view` docstring). The HR "stand-in" manager of anyone with no manager always holds HR Manager.
- **What happens:** the server treats this person as the manager (`get_manager_review` gives `VIEWER_MANAGER`; `_review_actor` gives `role = "manager"`). But the page gets `viewer_role: "hr"`. So the item rating boxes are read-only, with no "Save rating" button. "Edit" and "Remove" are hidden, and so is "Fill empty ratings from attainment". Answering a rating question asks "Why is HR answering for this rating?"
- **Why it is wrong:** decisions 6, 11, 12 and 29 give these actions to "the manager during Manager Review". For these managers, and for every employee with no manager, they cannot be reached. The server allows them; only the page hides them.
- **Smallest fix:** send `viewer_role` from the same test the server uses: `"manager" if _is_line_manager(ap.employee, me) else "hr"`. Add one page pin.

### M4. The reviewer picker finds at most 50 people, from the review first opened

`hrms-employee.html:16067-16070`, `:16123-16147`, with `performance_api.py:1755` (`limit=50`, was 100).

- **Setup:** the reviewed person's company has more than 50 active employees. ppj has about 400.
- **What happens:** the page calls `search_employees` once with `query: ""` and caches the answer in `_prEmpCache`. It then filters that cache in the browser. The server returns the first 50 names in alphabetical order, so a manager typing "Vinod" sees "No employees found."
- The cache is never cleared. A manager or HR person who opens a second review, for someone in another company, gets the first company's list. Picking from it is refused by `_check_invitees`, which refuses the whole invite.
- **Why it is wrong:** decision 2 and SEC-7/SEC-18 say the picker finds people in the reviewed person's company. As built, it finds only the first 50. This was already broken at 100; group D made it narrower.
- **Smallest fix:** send the typed `query` to the server (debounced), which already filters by name and ID, and clear `_prEmpCache` in `prOpenManagerReview`.

### M5. The group D release checklist names commands that do not exist, and its rollback loses ratings

`docs/slices/010-portal-security-fixes/03d-implementation-notes-group-d.md` §8 (lines 1306-1331).

- **What it says:** run `alvoraa_goals.review_backfill.dry_run(site)`, then roll back with `review_backfill.rollback(site)`, which "removes the copies the patch made … so reviews behave as they did before". It also says `custom_docperm_report` lists `Individual Goal`, and that `bench build` is needed.
- **What the code has:** `report()`, `run()`, `undo_backfill(dry_run=1)` and `copy_ratings_back_for_rollback(dry_run=1)`. Neither `dry_run` nor `rollback` exists (checked with grep). `undo_backfill` leaves alone any review changed since. Ratings given after go-live live only on copies. Only `copy_ratings_back_for_rollback`, run before the revert, puts them back where the old code reads them. The report covers Extension, Appraisal and KPI, not Individual Goal.
- **Failure:** at the ppj rehearsal or the dev deploy, the operator's first command fails with AttributeError. Worse, an operator who follows §8's rollback reverts without copying ratings back, and every manager and self rating given after go-live disappears from the old screens.
- **Smallest fix:** correct §8 to match phase 3 §8, which is right: `report` → migrate → (rollback) `copy_ratings_back_for_rollback` dry run, then real → revert and migrate → `undo_backfill` dry run, then real.

---

## 4. Minors

1. **The Future Objectives page says new objectives are not tagged to the cycle, but they are.** `hrms-employee.html:15393` says "they are not tagged to this cycle". `prOpenGoalDialogForReview` (`:15439-15441`) puts the current cycle into the new goal's form. Result: a goal tagged to this cycle that is not in the review, and that `past_incomplete_goals` hides. It stays stuck in this cycle until the cycle is Completed. This breaks VIS-15 and decision 19 on this path. 03d phase 4 gap 4 names the problem but not the false sentence. Fix: stop stamping the cycle, or say what really happens.
2. **R10 and decision 5 are sent by the server but never shown.** `review_payload` gives HR `late_facts` and `facts_dated_by_upload` (`review_items.py:972-975`), but the page shows neither (grep: no match). HR sees late facts only as a count in the CSV, and never sees "dated by upload". R10 says "shown to HR as 'arrived after this review closed'".
3. **"N items in this cycle are not in your review" was not built.** 00d §2.4 put it in the approved strategy so items tagged after the copies were taken are not left out silently. No `not_in_review_count` exists, and 03d does not record it as a deviation.
4. **The reading date defaults to the UTC day.** `hrms-employee.html:12432-12433` uses `new Date().toISOString().slice(0,10)` for both the value and `max`. Between 00:00 and 05:30 IST this gives yesterday, and the date field's upper limit blocks picking today. A reading logged at 01:00 on 1 October is dated 30 September and counts in the Q2 review instead of Q3. Use the local date.
5. **"Rating needs your answer" shows only for the overall rating.** `performance_api.py:869-871` reads `overall_rating_flag` only. A flagged item manager rating, which also blocks HR (`open_blocking_flags`), does not show on the manager's Reviews list. HR's message says "Open the earlier pages of this review to see which", but HR cannot answer while the rater is still in place.
6. **Review screens write while they are being read.** `get_my_review` (`:3909`), `get_manager_review` (`:4515`) and `_review_actor` (`:4267`) refresh and save the review record. If the employee and the manager open the same review in the same second, after a fact changed, the second save can fail with "document has been modified", and that screen shows an error. It is rare, and a reload fixes it.
7. **Submitted Objectives miss the refresh hook and part of the lock.** On a submitted `Individual Goal`, Frappe runs `on_update_after_submit`, not `on_update` (`hooks.py:21`). A save with `flags.ignore_validate` also skips `before_update_after_submit` (Frappe `document.py:1407-1419`). So a fact approved on a submitted goal reaches the copy only when the review is next opened, and HR screens and the CSV show the old number until then. The static lock test only looks for `set_value`. ppj has 0 submitted goals today, so this is latent.
8. **The Remove dialog can reopen with the reason box hidden.** `riSwitchToDelete` hides the reason field (`:15686`), and it is shown again only after a successful call (`:15704`). If the person cancels, then opens Remove on another item, the box is still hidden. Today only the subject reaches delete, and their reason is optional, so the harm is small.
9. **`save_overall_rating` (API only) accepts 0 and stamps it.** `performance_api.py:3494-3499`. The page's own path treats 0 as "not sent". Make them agree.

<details><summary>Nits</summary>

- `alvoraa_goals/review_items.py` is about 1,780 lines: settings, copies, payloads, writes, freeze, write-back, lock and reminder. 03d already proposes splitting it after release. Agreed, but not now.
- The audit text in `remove_review_item` and `answer_rating_flag` puts the free-text reason into an Info comment. It is declared (03d phase 2 gap 11), and the record opens to HR only.
- `save_calibration_note` still fails on the missing `calibration_notes` column (known F-D8). The HR page calls it.
</details>

---

## 5. Decisions and rules: verification

| Rule | Status | Evidence |
|---|---|---|
| R1 copies on the Extension | met | `alvoraa_review_item.json`; Extension `before_validate` guard; `test_r1_*` |
| R2 definition lock (inside and outside) | met, one gap | `enforce_definition_lock` on `before_validate` / `before_update_after_submit`; `set_cycle_membership`, `attach_ongoing_to_cycle` ask `holds()`; `test_r2_sec19_*`, static scan. Gap: Minor 7 (submitted goal + `ignore_validate`) |
| R3 facts by date until freeze | met | `_recount`, `refresh_copies_of`; `test_r3_*` |
| R4 Cumulative sums, Absolute latest | met on copies | `_numbers_for`; `test_r4_*`. **The live number is wrong after a rejection (M2)** |
| R5 badge | met | `review_badges`, `riReviewBadge`; `test_r5_*` (server and page) |
| R6 freeze point | met | `apply_stage`, `is_past_freeze_point`; `test_r6_*` |
| R7 stamps and flags, completion blocked | met on the server; partial in the page | `raise_rating_flags`, `_refuse_open_rating_questions`; `test_r7_*`. M3 and Minor 5 |
| R8 HR screens read copies | met | `_hr_cycle_reviews`, `_copies_of`; `test_r8_*`, `test_sec26_*` |
| R9 lock release, reminder | met | `_holding_reviews`, `remind_hr_of_held_items`; `test_r9_*` |
| R10 late facts shown to HR | **partial** | Server yes (`late_facts`, CSV column); page no (Minor 2) |
| R11 delete rule | met | `refuse_delete_while_held`, `delete_review_item`; `test_r11_*` |
| R12 remove with warning | **partial** | `remove_review_item` correct; `set_review_selection` removes items nobody unticked (M1) |
| R13 no rating written back | met | Retired endpoints; `refuse_rating_changes`; `test_vis6_r13_*`, `test_sec2_*` |
| R14 no ratings outside | met | `KPI_FIELDS`, `_appraisal_payload`, page deletions; `test_r14_*` |
| R15 write-back once, audited | met | `write_back`, `WRITE_BACK_FLAG`, Info comment, Version; `test_r15_*`, `test_sec25_*` |
| R16 overlapping reviews | met (not in backfill, declared) | `_held_by_other_open_reviews`; `test_r16_*` |
| D1 "amount since last update" | met, with M2 | Label, hint, server add; tests |
| D2 reading date | met, with Minor 4 | `_reading_date`; 4 server tests + page pin |
| D3 numbers can differ | met | Badge text |
| D4 copies on first open | met | `open_review`; `test_vis4_*` |
| D5 upload date, shown to HR | **partial** | Counted; not shown (Minor 2) |
| D6 who changes a definition | met on the server; **page gap for manager-with-HR (M3)** | `_review_actor`, `_ITEM_STAGES` |
| D7 no adds after Employee Review | met | `_selection_record` |
| D8 extra locked fields | met | `LOCKED_FIELDS` |
| D9 rated copy never discarded | met | `remove_item` `is_rated`; `test_r12_sec24_*` |
| D10 employee sees removal label, date, reason | met | `review_payload` removed list; `riRemovedHtml` |
| D11 item manager ratings from EFR | met | `rating_fields_for` |
| D12 rater answers; HR for a rater who left | met on the server; page M3 | `answer_rating_flag`, `_rater_still_acts` |
| D13 self flags information only | met | `open_blocking_flags` |
| D14 R14 scope | met | as R14 |
| D15 System Manager same stage rule | met | `_assert_hr_can_view`, `has_appraisal_extension_permission` |
| D16 `permitted_companies()` | met | review endpoints, HR screens |
| D17 reviewer access ends after MR | met | `get_reviewer_view`, `submit_reviewer_comments`; `test_decision17_*` |
| D18 return unfreezes | met | `apply_stage`; `test_r6_decision18_*` |
| D19 Future Objectives: no cycle, Remove does not delete | **partial** | Submit creates goals with no cycle, and Remove is gone; the page's "Add Objective" still stamps the cycle (Minor 1) |
| D20 cancel allowed | met | status not locked; `source_cancelled` |
| D21 `set_goal_progress` blocked while held | met | `goals_api.py`; `test_decision21_*` |
| D22, D26 Employee loses Appraisal write and read | met | `appraisal.json`; `test_decision22_*`, `test_decision26_*` |
| D23 settings in HR Settings and Org Settings | met | `get/save_review_settings`, `riLoadSettings`; tests |
| D24 Custom DocPerm check on dev tenants | done per work board (2026-09-17), not checked by me | — |
| D27 HR cannot open own review in desk | met | `has_appraisal_extension_permission` |
| D28, D33 HR scorecard and goal detail scoped | met | `_hr_target_employee`; `test_decision28_*`, `test_review_outside` get_goal_detail test |
| D29 removal stages | met | `_ITEM_STAGES` |
| D30 agreed Objective target written back | met | `controllers/goal.py`; `test_decision30_*` (both) |
| D31 email only once released | met | `answer_rating_flag` |
| D32 no reminder when 0 | met | `remind_hr_of_held_items`; test |

---

## 6. NFR verification

### 6.1 Budgets (`nfr-budget.md`)

| Budget | Measured or reasoned | Result |
|---|---|---|
| Queries per request bounded, none in a loop | Pinned: review open does not grow with items (3 vs 16); HR screens same count at 2 and 7 reviews; hook = 1 query when not held. Read: `write_back` is one get_doc and save per changed copy, only at completion | pass |
| Recalculation writes only on change | `refresh_review_items` saves only when `_recount` or flags changed | pass |
| Whitelisted API p95 ≤ 500 ms | 03d probe: later review opens 25-43 ms; first open 109-242 ms (single runs, not p95) | pass on single runs; **p95 not measured** |
| Core HR view ≤ 1.5 s at Typical volume | Not timed. HR screens are fixed-query | not measured |
| Anything > 2 s runs in the background | Backfill is 15 s for 806 reviews, but it runs inside `bench migrate`, not a request | pass |
| Cycle close for 1,000 employees | Completion runs one review at a time; write-back per changed copy | reasoned pass |

### 6.2 The seven dimensions: 00d's claim against what the code does

| Dimension | 00d claim | Before → after (code) | Finding |
|---|---|---|---|
| Performance | improves | Per-goal KPI query and calibration `get_doc` loop gone; new KPI indexes. Cost: 1 query per KPI/Objective save, 1 per badge list, first-open writes | **Agrees** |
| Security | improves | SEC-1/2/5/6/7/10/19-30, PRIV-1/2/9-15 closed on the server and pinned. The page hides allowed actions from some managers (M3), which blocks work but opens nothing | **Agrees** |
| Reliability | improves, two risks | `except: pass` gone; wizard no longer deletes live records. **New:** the dialog can refuse, or drop items unasked (M1); read endpoints now write (Minor 6) | **Partly degrades**, not declared |
| Scalability | neutral | ~8 rows per review; indexed `parent` and `source_name`; daily reminder bounded by open reviews | **Agrees** |
| Maintainability | degrades slightly | One module of ~1,780 lines; one field rule; one save path; ~126 pin tests | **Agrees** |
| Data integrity | improves | Review records are now replayable, frozen and written back once. **But the live Cumulative number no longer corrects itself (M2)**, and old running-total readings are summed by the copies (declared, 03d phase 4 gap 3) | **Degrades on live KPI numbers.** 00d marked it "improves" and did not foresee M2 |
| Compliance / privacy | improves | Potential never reaches the subject; ratings leave outside payloads; refusal logs carry names only; the reminder has no names | **Agrees** |

---

## 7. Compliance verification (01d obligations)

| Obligation | Mechanism in the diff | Test that proves it | Status |
|---|---|---|---|
| SEC-1 self-review writes only this review's copies | `apply_self_review` key check; no progress write | `test_sec1_*` | discharged |
| SEC-2 nobody writes KPI ratings | permlevel 1, no write; `refuse_rating_changes` (before_validate, Administrator too) | `test_sec2_*` (JSON, every path, static) | discharged |
| SEC-5 / M3 no Employee DocPerm; tenants reported | Extension JSON; `custom_docperm_report` | `test_sec5_*`, `test_m3_*`, `test_decision26_m3_*` | discharged |
| SEC-6 order, no create before check | `_manager_review_record`, `_extension()` | `test_sec6_*` (15 endpoints) | discharged |
| SEC-7 / SEC-18 reviewer pages and company | `get_reviewer_view`, `_check_invitees`, `search_employees(appraisal)` | `test_sec7_*` | discharged on the server; **the picker only half works in the page (M4)** |
| SEC-10 nobody rates own review | `refuse_own_rating` in every rating writer | `test_sec10_*` | discharged |
| SEC-19 lock on every path | before_validate / before_update_after_submit; `holds()` in set_value writers | `test_r2_sec19_*`, static scan | partial (Minor 7, latent) |
| SEC-20 only HR re-tags, held items skipped | `attach_ongoing_to_cycle` | `test_sec20_*` | discharged |
| SEC-21 window, freeze point, removal mode stamped | `ensure_review_items` | `test_sec21_*` | discharged |
| SEC-22 release on server date; 0 = never | `_holding_reviews` | `test_r9_sec22_*` | discharged |
| SEC-23 server stamps; HR blocked on open flags | `stamp_*`, `_refuse_open_rating_questions` | `test_r7_sec23_*`, `test_sec23_*` | discharged |
| SEC-24 removal named, reasoned, audited; rated copy kept | `remove_review_item`, `remove_item`, `audit` | `test_r12_sec24_*` | **partial**: removals through `set_review_selection` include items nobody chose (M1) |
| SEC-25 write-back once, no overwrite, audited | `write_back`, Info comment, Version (KPI `track_changes: 1`) | `test_r15_sec25_*`, `test_sec25_*` | discharged |
| SEC-26 HR screens: company and stage | `_hr_cycle_reviews`, `rating_fields_for` | `test_sec26_*`, CSV test | discharged |
| SEC-27 desk follows the stage rule | `has_appraisal_extension_permission`, `appraisal_extension_query` | `test_sec27_*` | discharged |
| SEC-28 settings in one audited place | HR Settings custom fields; `validate_hr_settings`; save through the document | `test_sec28_*`, `test_decision23_*` | discharged |
| SEC-29 reviewer rating only on own entry | per-KPI reviewer endpoints retired | `test_vis6_r13_*` | discharged |
| SEC-30 calibration sign-off HR only | `_require_hr()` | `test_sec26_sec30_*` | discharged |
| PRIV-1 subject never gets potential | `rating_fields_for`, `get_employee_final_review`, `get_appraisal_extension` | `test_priv1_*` | discharged |
| PRIV-2 no self-review before sent | `get_my_review`, `get_manager_review` refusals | `test_priv2_*` | discharged |
| PRIV-9 no rating outside a review | `KPI_FIELDS`, `_appraisal_payload`, `list_appraisals`, scorecards | `test_r14_priv9_*`, `test_priv9_*` | discharged |
| PRIV-10 badge reveals nothing else | `review_badges` returns 2 keys | `test_r5_priv10_*` | discharged |
| PRIV-11 late facts HR only, score unchanged | `late_facts` only for `VIEWER_HR` | `test_r10_*` | discharged for privacy; **R10's "shown to HR" not met (Minor 2)** |
| PRIV-12 removed items seen by the right people | `review_payload` removed list | `test_r12_*` | discharged |
| PRIV-13 stamps follow rating visibility | `_STAMP_FIELDS` for deciders only | `test_priv1_priv13_*` | discharged |
| PRIV-14 no delete path for copies | no role deletes the Extension (permission hook); discard only for unrated copies (decision 9); `undo_backfill` is an operator script (declared) | `test_vis10_*`, `test_sec27_*` | discharged, with the declared operator exception |
| PRIV-15 names only in logs | `frappe.log_error` messages carry document names; reminder has counts | read in code | discharged |
| VIS-15 future objectives never tagged to the current review | `submit_employee_review` creates with no cycle | `test_vis15_*` | **partial** (Minor 1: page create path stamps the cycle) |
| C-D1..C-D4 counsel questions | none | none | open, for counsel (not blocking per 00e) |

---

## 8. Upgrade and migration safety on real tenants

What I checked:

- **The patch runs before the DocType sync**, so it reloads the three doctypes it writes to first (`take_review_copies.py`). `review_settings()` does not fail when the HR Settings fields do not exist yet: `get_single_value` reads `tabSingles` and returns nothing, so the defaults apply (checked in Frappe v16 `database.py:878`).
- **It is safe to run twice:** a review with `items_taken_on` or any copy row is skipped. Each review gets its own savepoint, with a commit every 50.
- **Open reviews with old manager ratings on their KPIs** (ppj Q2: 601 of 1,755) are stamped on the stored numbers. Their first open recounts from approved, dated facts, and every item whose number moves gets flagged. **Each flag blocks HR completion until the manager answers it.** `report()` counts these in advance (`rating_questions_expected_on_first_open`). On dev.alvoraa.co (363 open) and ppj.dev (403 open) the counts are unknown until the report runs.
- **Old running-total readings** on Cumulative KPIs are summed by the copies (03d phase 4 gap 3). `report()` counts them (`cumulative_kpis_whose_readings_look_like_running_totals`). There is no tool to fix them: HR must correct readings by hand in the desk.
- **Default freeze point "HR sent"** means numbers keep moving through Employee Final Review and HR Review. Every late approval re-flags the overall rating and blocks completion again. This follows R6 and R7 as decided, but HR will feel it in the first cycle.
- **Employees lose desk and REST read on Appraisal** (decision 26). Any HRMS screen or integration an employee used on Appraisal stops working. That is by design.

**Must be checked by hand after deploy, per tenant:**

1. `bench --site <site> execute alvoraa_goals.review_backfill.report` **before** migrate (not `dry_run`: see M5). Stop if `cannot_copy_nothing_tagged.open` is not empty or `custom_docperm_rows_to_look_at` lists anything.
2. After migrate: the patch line "Review copies: N reviews, N copies, 0 failed", and the Error Log has no "Review copy backfill failed".
3. As an employee: open a review, see items, log a KPI reading. Check the label and the date.
4. As a manager **who holds no HR role and as one who does**: open Manager Review, rate an item, change a target, remove an item with a reason (M3).
5. Open the reviewer picker and search for a name that sorts late (M4).
6. As HR: Org Settings shows the three settings; HR Review shows the blocked-completion message when a flag is open.
7. On one Cumulative KPI: log, reject, log again, and check the live number (M2).
8. Pick an employee with a cascaded KPI: open "Add/remove KPIs" and add one (M1).

**Rollback, in order:** `copy_ratings_back_for_rollback(dry_run=1)` then `0` → revert + migrate → `undo_backfill(dry_run=1)` then `0`. Not what 03d §8 says (M5).

---

## 9. What to delete

- **`pfOpenReviewerModal`, `pfSubmitAdditionalReviewer` and the `pf-reviewer-modal` markup** (`hrms-employee.html:4285-4310`, `:17854-17876`). They have no caller, and they call the retired `add_additional_reviewer`, which now always refuses.
- **The Future Objectives "new KPIs" filter on `standalone_kpis` by `appraisal_cycle`**: always empty, because copies carry no cycle (03d phase 4 gap 7). Delete it, or decide what it is for.
- **`_scored_live_items`' use of the legacy `manager_rating`** (`performance_api.py:1292-1303`). It is API only. After R13 that field never changes, so a new appraisal's first projection scores from last cycle's frozen ratings. Score 0 there, or drop the projection.
- **The `hasattr(ext, "calibration_notes")` branch in `save_calibration_note`** (`:3580-3584`). It writes a column that does not exist (F-D8). Remove the branch, or add the field in a separate change.
- The unused `onRemove` argument of `prReviewKpiRow` can stay until the page is split. The engineer's reason (a hot file) is fair.

Nothing large should go. The one module, the one save path and the one field rule are the right size for what the decisions ask.

---

## 10. What was done well

- **One field rule for every screen.** `rating_fields_for` / `overall_rating_visible` serve the review screens, the HR cycle screens and the CSV, so privacy cannot drift between them.
- **Guards on `before_validate`, not `validate`.** The lock and the rating guard catch `flags.ignore_validate` saves, which is how most of this codebase writes goals. The engineer checked this in Frappe's source.
- **Copies point to live records by `Data`, not `Link`.** A live record never becomes impossible to delete because a closed review once copied it. It is a small choice that avoids a long tail of support tickets.
- **Each review stamps its own freeze point, removal mode and period.** A settings change cannot rewrite a review that is already running.
- **The backfill writes rows directly**, instead of weakening the VIS-10 "Completed never changes" guard to let the migration through.
- **Write-back failures do not stop completion**, and every failure is recorded on the copy and in the Error Log with document names only.
- **The CSV export guards against formula injection** and writes one security log line with counts.
- **The live draft-save bug** (every "Save draft" wiped the manager's ratings) was found while reading and fixed with a pin.

---

## 11. Confidence, and what I could not check

- **High confidence** in the server rules. I read `review_items.py`, `review_backfill.py`, the permission hooks and every changed review endpoint in full, and traced them against Frappe v16 source where it mattered.
- **M1-M4 were traced in code, not run.** I did not write probes against `test_site`, to stay read-only. A 10-minute browser check (§8 items 4, 5, 7, 8) would confirm or clear each one.
- **No browser trace.** I could not check layout, 360 px, 200% zoom, labels in a real browser, or whether a manager can reopen a review from the Reviews list after sending it (which Minor 5 depends on).
- **No timing at Typical or Large volume.** Only the engineer's query counts and single-run probes exist.
- **Dev tenant data is unknown to me:** cascaded KPIs, running-total readings, old manager ratings on open reviews, and custom permission rows. Only `report()` on each tenant answers these.
- **Security review (06) and release readiness (07 §5) are running separately.** I did not repeat their threat model or deploy plan.
