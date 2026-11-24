# Slice 090 · Test report (step 4, final run)

**Code tested:** branch `slice/090-leadership-hr-analytics`, **d41c1bed** (fix round 3). Full suite on **cb3677e3** (before rounds 2 and 3). Then a targeted re-run at d41c1bed. Site `test_site` on stack alv090-bench; schema from this branch. Not the shared bench. No push, no deploy.

## 0 · Read this first

| | |
|---|---|
| **Verdict** | **Pass with known defects** (all the defects are outside 090: groups A and B below, ticket ALV-442 for B) |
| 090-caused defects found | 3, all fixed in round 2 and re-run green at d41c1bed: the trays INVENTORY gate, `test_portal_split_034`, `test_browser_call_args_045` |
| Not run | A second full suite at d41c1bed (the coordinator agreed a targeted re-run is enough). DTC-size timing (OPS-23). Browser at 360 px, 200 percent text, a screen reader. |
| Stale-code warning | The full-suite numbers are for cb3677e3. Round 2 and round 3 changed `people_trends.py`. The 090 modules, the DOM runner and the gates were re-run at d41c1bed (section 3). The other ~2,900 tests were not. **Inference only** that they behave as they did. |

## 1 · Commands run

| Command | Where | Result |
|---|---|---|
| `bench --site test_site run-tests --app alvoraa_portal` (full) | alv090-bench, cb3677e3, about 4 h 20 | Two batches printed. Batch 1 (integration): **71 OK**. Batch 2: **3,629 ran, 15 failures, 228 errors, 51 skipped**. Batch 3 (old frappe test class): **1,374 ran, 18 failures, 11 errors, 20 skipped**. 262 distinct failing tests, **none in a 090 test file**. |
| Same command, 35 failing modules only | alv090-base, a copy of the stack with 640cd1f5 (090's base) mounted, same site | 235 of the 262 fail the same way. 0 fail only there. |
| `--module` runs at **d41c1bed**: `test_people_trends_090` (63 + 2), `_http_090` (1 + 5), `_property_090` (2), `_final_090` (3), `test_portal_split_034` (12), `test_browser_call_args_045` (6), `test_grooming_066` (65 + 1) | alv090-bench | **all OK, 0 failures** |
| `node scripts/run_dom_tests.js` at d41c1bed | host | **31 run, 0 not run, 0 failed** (at cb3677e3: 31 run, 1 failed, the date-based leave R-88, now fixed on dev and in this branch by the rebase) |
| The 25 gate steps of `ci.yml` (list in `scratchpad/final/gates2.log`) | host, d41c1bed | 23 pass, 2 fail for the Mac only: `check_scope_traps.py` (Mac Python 3.9 cannot parse an hrms file; **passes on the bench's Python 3.14**, "OK: no use of permitted_employee_filters lets a caller's id replace the scope") and `check_event_refusals.sh --self-test` (macOS `date -d`; same on 640cd1f5). `check_portal_trays.js --static` **now passes**. |

## 2 · Failures in the full run, by root cause (cb3677e3)

| Group | Count | Cause | Proof |
|---|---|---|---|
| **A** | 235 | `alvoraa_goals` is not installed on `test_site` (list-apps: frappe, erpnext, hrms, alvoraa_portal). About 170 say "No module named frappe.core.doctype.individual_goal / kpi / alvoraa_appraisal_extension / company_value". The rest are 010d review, 035/045 goals, 030 store HR, calibration, 2 wkhtmltopdf errors, 1 duplicate key (joiner_079), a few string checks. | **Proven not 090.** Same 235 tests fail on 640cd1f5 on the same site. |
| **B** | 25 | `test_goal_cycle_035.setUp` starts `patch(has_feature, True)` and then fails on the missing Individual Goal doctype. `tearDown` never runs, so the patch is never stopped, and every later "tenant without the feature" test sees the gate open. Hits entitlement, subscription, waves_5_6, portal_module_gate_016, frame_api_034, home_api_042, pay_screen_043, payslips_gate_043, staff_list_034. | **Proven not 090.** Reproduced on 640cd1f5: goal_cycle_035 then home_api_042, entitlement, payslips_gate_043, pay_screen_043 in one process gives the same failures. The same modules pass alone on both codes. **ALV-442.** Disappears once alvoraa_goals is installed. |
| **C** | 2 | 090: `test_portal_split_034` (asset list lacked `js/ess/people-trends.js`); `test_browser_call_args_045` (scanner did not see the `fetch` call). | Fixed in round 2. **Re-run at d41c1bed: 12 OK and 6 OK.** |
| **D** | 1 gate | 090: `check_portal_trays.js --static`, 2 problems (`#pt-sheet-scrim`, `#pt-sheet` not in INVENTORY). | Fixed in round 2. Re-run at d41c1bed: **passes**. |

Fixture warning for the owners of B: a fixture whose `setUp` starts a patch and then touches a thing that may not exist is a defect. Put the `start` after the risky call, or use `addCleanup`.

`test_grooming_066` ('Your reason' in portal.js) failed at cb3677e3 and fails on 640cd1f5 too. It passes at d41c1bed (65 + 1 OK), because the branch now carries dev's fix.

## 3 · Proof the new tests can fail

I switched the fix off in-process (the 703fee29 parent version of `people_trends.py` loaded in place of the real module), with no repo file edited:

| Test | With the fix | With the round-3 fix removed |
|---|---|---|
| `test_a_thin_bucket_sends_no_points_for_the_whole_view` | pass (63 OK) | **fails**: "'series' unexpectedly found" |
| `test_no_hidden_day_can_be_got_back_from_two_views_together` | pass | **fails**: "'series' unexpectedly found" |
| `test_by_company_sends_no_absent_percent_when_one_company_is_thin` | pass | **fails**: "0.0 is not None" |
| `test_leave_days_carry_a_comparison_with_the_window_before` (AC-84, mine) | pass | **fails** with `leave["before"]` renamed: KeyError 'before' |

**Not break-tested by me:** `test_a_half_day_row_adds_nothing_to_leave_days` (AC-123) and `test_the_same_request_gives_the_same_answer` (AC-60). They pin existing behaviour. They have passed, but I did not watch them fail. Label: **passes, not proven to fail**. The engineer's round-1 and round-2 break tests are quoted in 03 and not repeated.

## 4 · Fixture check

People are inserted straight into `tabEmployee` with `db_insert` (as the engineer's `person()` does) and attendance with `leader_fixtures_012.attendance`. That is not the shape a screen writes, but it is the shape every 012 and 090 test uses, and the figures are read by SQL over those same tables. **Inference only** that nothing depends on a hook that the screens fire. No shift assignment or other fixture differs from the real tenant in a way I found.

## 4 · Acceptance criteria (123) mapped to tests

Test files: **A** = `test_people_trends_090.py` (66 tests now), **H** = `test_people_trends_http_090.py` (6), **P** = `test_people_trends_property_090.py` (2), **F** = `test_people_trends_final_090.py` (3, added at this run), **D1** = `people_trends_090_dom_test.js`, **D2** = `people_trends_090_gaps_dom_test.js`. "Named" means the test's own comment names the AC; I read each test name, not every line. Results are in section 3. Table written against the cb3677e3 test list and checked again at d41c1bed (new tests: 7 in A, 3 in F).

| AC | Test that proves it | Status |
|---|---|---|
| 1 to 6 | A `test_scope_table` | covered |
| 4 | A `test_not_set_up_runs_no_figure_query` | covered |
| 7 | A `test_who_is_refused` | **not met as written**: HR + Leadership is refused in v1 (BQ-2, decision 2). Test asserts the refusal. |
| 8, 121 | A `test_role_has_no_permissions_and_hook_is_repeatable`, `test_the_role_adds_no_rows_anywhere` | covered |
| 9 | A `test_leadership_is_still_refused_the_organisation_attendance_view` | covered |
| 10 | A `test_a_leader_whose_own_record_is_left_is_refused` | covered |
| 11, 12 | H `test_get_and_guest_are_refused` | covered (real HTTP) |
| 13, 14 | H `test_a_post_without_the_token_is_refused_and_with_it_is_served` | covered (real HTTP) |
| 15 | H `test_a_plan_without_analytics_is_refused` | covered |
| 16, 65 | H `test_a_refusal_writes_exactly_one_line`, A `test_who_is_refused` | covered |
| 17 | A `test_extra_parameters_have_no_effect` | covered |
| 18 | A `test_period_is_checked_not_defaulted` | covered |
| 19 | H `test_the_log_line_is_in_the_file_and_holds_no_figure` | covered |
| 20 | H `test_forced_exception_gives_the_generic_message` | covered |
| 21 | A `test_a_branch_name_with_a_quote_is_just_refused`, `test_no_reason_or_pay_columns_in_the_sql` | covered |
| 22, 117 | A `test_no_reason_or_pay_columns_in_the_sql` (source scan for `frappe.cache`, `scheduler_events`, `ignore_permissions`) | covered by a source scan, not by watching a cache write |
| 23 | no test names it | **gap** (notes claim a source check; no test in the suite) (P3) |
| 24 | A `test_goals_and_appraisals_do_not_import_it` | covered |
| 25 | D2 (each tap sends its own request, focus stays) | covered |
| 26, 27, 28 | A `test_window_and_comparison_dates`, `test_clipped_window` | covered for dates; the exact AC-27 sentence is not asserted (P4) |
| 29, 30 | A `test_save_and_reopen`, `test_a_bad_period_is_refused_on_save`; D2 (three quick taps give one save, 2 s) | covered |
| 31 | D2 (a late answer to an older tap does not replace the last one) | covered |
| 32, 33 | A `test_company_figures_and_identity`, `test_identity_holds_for_every_chip_and_cut` | covered |
| 34, 35 | A `test_edges` | covered |
| 36 | A `test_company_figures_and_identity` (the formula only) | **partial**: attrition with an average of 0 ("–", no throw) is not tested (P4) |
| 37 | A `test_future_relieving_date_is_still_on_the_roll` | covered |
| 38, 39 | none | **gap**: wording and "no success/danger class" are not asserted (P4; the notes call 38 inferred from the CSS) |
| 40, 42, 44 | A `test_shown_cells`, `test_whole_company_only` | covered |
| 41 | none | **gap**: the exact cohort edge (X versus X + 1 days) is not tested (P3) |
| 43 | none | **gap** (P4) |
| 45, 46, 47 | (round 2 added A `test_the_guard_leaves_the_caller_out`) | A `test_callers_own_record_is_left_out_of_the_pass_test`, `test_minimum_is_read_every_call`, `test_empty_cut_is_no_match` | covered |
| 48, 49, 50, 51, 54, 55, 57 | A `test_branches_part_b_and_c`, `test_hidden_means_not_sent`, `test_the_chart_is_whole_or_absent`, `test_leaving_unshared_leaves_nothing_derived`, `test_employment_type_and_department_siblings` | covered |
| 52 | none by name | **gap**: "the same state everywhere on the page" is only partly shown by D1 and the hidden-means-not-sent test (P3) |
| 53 | A `test_four_stretches_hide_small_cohorts`, `test_shown_cells` | covered |
| 56, 58 | P (300 generated tenants) covers the rule; no example test names 56 or 58 | covered by the property test only |
| 59, 93 | A `test_a_small_company_hides_the_next_smallest_too` | covered |
| 60 | F `test_the_same_request_gives_the_same_answer` | covered (added at this run) |
| 61 | A `test_query_count_is_fixed` | covered |
| 62 | P `test_the_real_rule_holds_at_every_minimum`, `test_the_property_catches_part_c_removed` | covered; break-tested by the engineer (not re-done by me) |
| 63 to 68 | A `test_refused_filters`, `test_all_companies_has_no_sub_company_figures`, `test_branch_head_has_no_company_total_beyond_the_set`, `test_lists_hold_only_the_scope` | covered |
| 69, 70, 71 | D1 covers the refused-filter page ("403 says so without saying whether it exists") | **partial**: exact scope-line text, "(Not shared)" list entry and the PT-SCOPE wording are not each asserted (P4) |
| 72 | A `test_bins_sum_to_the_window` | covered |
| 73, 74 | D2 (no text under 12 px in the panel CSS) | covered for 74; 73 not named |
| 75 | none | **gap**: legend words (P4) |
| 76, 77, 83 | A `test_absent_percent_and_leave_days_match_the_shared_figures` | covered |
| 78 | none | **gap**: "Data up to" and the days-left-out line text (the count itself is asserted in the AC-76 test) (P4) |
| 79 | A `test_no_attendance_says_so` | covered |
| 80 | none by name | **partial**: department cut for attendance (A `test_employment_type_and_department_siblings` covers people only) (P3) |
| 81, 90 | A `test_a_failing_bucket_sends_no_series_at_all` (B1/F2), and from round 3 `test_a_thin_bucket_sends_no_points_for_the_whole_view`, `test_no_hidden_day_can_be_got_back_from_two_views_together` | covered |
| 82 | A `test_leave_across_the_window_edge_counts_only_days_inside` | covered |
| 84 | F `test_leave_days_carry_a_comparison_with_the_window_before` | covered (added at this run) |
| 85, 86, 87, 122 | A `test_types_are_named_only_at_the_top`, `test_leave_types_fold_small_ones_into_other`, `test_named_leave_types_are_the_same_on_every_chip` (F3), `test_the_headline_names_a_leave_type_only_if_it_beats_other` (AC-87) | covered |
| 88 | A `test_pending_requests_are_a_count_only` | covered |
| 89, 111, 112, 113 | A `test_totals_only`, `test_no_reason_or_pay_columns_in_the_sql` | covered |
| 91, 92 | A `test_the_headline_never_names_a_hidden_figure` | covered for the fixture; the "clause left out when withheld" is D1 only |
| 94 | A `test_by_company_sends_no_absent_percent_when_one_company_is_thin` and `test_all_companies_has_no_sub_company_figures` cover the card's content; AC-94's "no block for one company" is not named | **gap** (P4) |
| 95 | D2 (skeleton words on screen straight after the call) | covered; the 300 ms delay itself is not timed |
| 96, 97 | D2 (offline first load gives PT-LOAD; a dropped connection keeps old figures and says so, Try again) | covered |
| 98, 99, 100 | D1 (not set up, not shared, refusal pages) | **partial**: "No people records", "No one matches" and the "not set up" body wording are not each asserted (P4) |
| 101, 119, 120 | none | **not built**: US-19 (HR) deferred by decision; HR is refused (AC-118 tested) |
| 102, 103 | A `test_data_quality_line_only_at_the_top_and_only_five_or_more` | covered |
| 104 | A `test_the_page_carries_the_panel_the_nav_and_the_script`; diff has no `nginx.conf` change | covered by pin plus diff; no standalone assertion on `deploy/nginx.conf` |
| 105 | A `test_the_nav_item_is_hidden_from_a_login_the_page_refuses` (a source pin on `ptShow`) | **partial**: not run in a browser; the cache-after-role-change question is open |
| 106 | D2 (no text under 12 px) only | **not automated** (360 px, 200 percent text, target size): human, section 8 |
| 107 | D2 (chips are buttons, labels on selects, live region, sheet focus, Escape returns focus) | partial: **screen reader not run**, human |
| 108 | D1 (`localStorage` and `sessionStorage` empty after use) | covered for both; **cookies not checked** |
| 109 | D1 (sheet words) | partial (live minimum in the words not asserted) |
| 110 | none new | `hr_api.py` is untouched in the diff (checked: `git diff 640cd1f5 HEAD --name-only` lists no `hr_api.py`); the old HR Analytics tests ran inside the full suite |
| 114 | A `test_response_size_follows_branches_not_people` | covered |
| 115 | none | **not run**: DTC-size timing (OPS-23); human/devops |
| 116 | none | **gap**: the slow-call warning line is coded, not tested (P3) |
| 117 | A `test_no_reason_or_pay_columns_in_the_sql` | covered |
| 118 | A `test_who_is_refused` | covered |
| 123 | F `test_a_half_day_row_adds_nothing_to_leave_days` | covered (added at this run) |

AC totals: see section 3 for pass or fail. By name: ACs with at least one test naming them, excluding "not built" and "not automated" rows, are listed above; the gap rows are the answer to "which ACs have no test".


## 5 · Security, privacy and operations items

Tests are named by AC, not by SEC or PRIV id. This is the mapping I could make (`SEC` and `PRIV` text in `01c`).

| Item | Test | Status |
|---|---|---|
| SEC-1 one scope resolver, fail closed | A `test_scope_table`, `test_who_is_refused`, `test_not_set_up_runs_no_figure_query` | covered |
| SEC-2 filters refused, never trimmed | A `test_refused_filters`, `test_extra_parameters_have_no_effect`, H real calls | covered |
| SEC-3 filter lists from inside the scope | A `test_lists_hold_only_the_scope` | covered |
| SEC-4 endpoint hygiene | H `test_get_and_guest_are_refused`, CSRF test | covered over real HTTP |
| SEC-5 Leadership has no document permissions | A `test_role_has_no_permissions_and_hook_is_repeatable`, `test_the_role_adds_no_rows_anywhere`, `test_leadership_is_still_refused_the_organisation_attendance_view` | covered |
| SEC-6 access ends on the next request | A `test_a_leader_whose_own_record_is_left_is_refused` | covered for a Left record. **Untested:** a role removed mid-session through the UI |
| SEC-7 SQL parameterised, no `ignore_permissions` | A `test_a_branch_name_with_a_quote_is_just_refused`, `test_no_reason_or_pay_columns_in_the_sql` | covered (source scan) |
| SEC-8 narrowed Branch permission | A `test_scope_table` rows | covered |
| SEC-9 one log line, no figures | H `test_the_log_line_is_in_the_file_and_holds_no_figure`, `test_a_refusal_writes_exactly_one_line` | covered |
| SEC-10 no cache | A `test_no_reason_or_pay_columns_in_the_sql` (scan) | covered |
| PRIV-1 totals only | A `test_totals_only` | covered |
| PRIV-2 caller not counted | A `test_callers_own_record_is_left_out_of_the_pass_test`, `test_the_guard_leaves_the_caller_out` | covered |
| PRIV-3 hidden means not sent | A `test_hidden_means_not_sent`, `test_a_failing_bucket_sends_no_series_at_all`, round-3 tests | covered |
| PRIV-4 time rule | P property test | covered |
| PRIV-5 one filter at a time | A `test_refused_filters` | covered |
| PRIV-6 sibling rule | A `test_branches_part_b_and_c`, three F1 subtraction tests, P | covered |
| PRIV-7 shown figures do not rebuild a hidden one | A `test_leaving_unshared_leaves_nothing_derived`, round-3 `test_no_hidden_day_can_be_got_back_from_two_views_together` | covered for the cases written. **Not generated**: the F1 and M2 subtraction cases are examples, not a property test (P3) |
| PRIV-8 leave types folded | A `test_types_are_named_only_at_the_top`, `test_leave_types_fold_small_ones_into_other` | covered |
| PRIV-9, 10 | A `test_data_quality_line_only_at_the_top_and_only_five_or_more` | covered |
| PRIV-11 no export, ranking, names | A `test_totals_only`, `test_goals_and_appraisals_do_not_import_it` | covered |
| PRIV-12 purpose limitation | not a test: a design rule | **Untested control** |
| PRIV-13 property test | P | covered, break-tested by the engineer |
| OPS-12, 18, 19 endpoint, CSRF | H, D1 | covered |
| OPS-13, 14, 24 query count and size | A `test_query_count_is_fixed`, `test_response_size_follows_branches_not_people` | covered at fixture size |
| OPS-21, 22 refusals logged, timing line | H (refusal line); the slow-call warning (AC-116) | refusal line covered; **slow-call warning untested** |
| OPS-23, 28, 40, 41 DTC-size timing | none | **Not run**; owed before main (devops) |
| OPS-29 assets gate | `check_portal_assets_gate.py` | passes |
| OPS-30, 31, 37 role desk_access after migrate | none | **Not automated**: read-only checks on each site after release |
| OPS-33 gates | section 1 | 23 of 25 pass; 2 Mac-only (explained) |
| OPS-34 radii | `check_design_system.py` | passes |
| OPS-38, 39, 42, 43 release steps | none | **Not automated**: release checklist |

## 6 · Journeys against `prototype-v1.html`

I did not walk the prototype in a browser. **Not checked.** What I could trace is the DOM runner: the 090 DOM tests exercise the chips, the not-set-up, refused and failed pages, the why-not-shared sheet with Escape and focus return, the offline line, the stale-answer and single-save timing, and the 12 px floor. They do not compare the screen to the prototype's pixels or exact words. Prototype parity for the text of AC-69, 71, 75, 78, 98 to 100 is a **human** check.

## 7 · Extra tests I added

`test_people_trends_final_090.py`: AC-123 (half day adds nothing to leave days but still counts in the absence rate), AC-84 (leave comparison), AC-60 (same request, same answer after other calls). Reason: no earlier test named them. Committed earlier by the engineer (e0fe98ad, imports fixed 7d4790d4). A throwaway ordering file `test_zz_order_tmp.py` was used for the group B proof and deleted; it was never committed.

**Subtract pass:** I removed nothing from the existing suite. I did not add helpers. Candidates a later pass could drop: `test_people_trends_090.py::test_the_hook_is_registered` and `test_the_page_carries_the_panel_the_nav_and_the_script` are source pins (cheap, and they exist so a bad merge cannot drop things).

## 8 · What a human must still check

| Check | Why not automated |
|---|---|
| 360 px phone, 200 percent text, target size (AC-106) | no browser run |
| Screen reader reads the chart label, live region and sheet (AC-107) | needs a reader |
| Timing on a DTC-size dev copy, 3G profile, cold and warm, five periods (OPS-23, OPS-40; AC-115). Local numbers: 6.3 to 7.2 s for 1 year on this stack, about 8 times slower than production by the engineer's measure (**inference**) | needs a dev copy at about 600 staff and a year of attendance |
| The nav shows after a role change without an hour's wait (AC-105) | needs a browser and a login |
| Prototype parity of all on-screen wording | needs eyes |
| `desk_access` of Leadership on every site after migrate (OPS-30, 31, 37) | per-site read |
| Rollback tag exists (OPS-42) | token lacks `read:packages` |
| Cookies unchanged after use (AC-108) | not checked |

## 9 · Known defects and debt

| # | What | Level | Label |
|---|---|---|---|
| 1 | Group B: leaked `has_feature` patch in `test_goal_cycle_035` fails 25 tests in the full run (ALV-442) | P2, outside 090 | dangerous debt for the suite until alvoraa_goals is on the test site or the fixture is fixed |
| 2 | Group A: 235 tests cannot pass on this stack because alvoraa_goals is missing | P3 outside 090 | temporary debt; a CI site that has the app is green (**assumption**) |
| 3 | AC gaps with no test: 23, 36 (average 0), 38, 39, 41, 43, 52, 75, 78, 94, 116 | P3 to P4 | temporary debt |
| 4 | The F1/M2/round-3 subtraction guards are examples, not generated | P3 | temporary debt |
| 5 | AC-7 is not met as written (HR + Leadership refused in v1, BQ-2). AC-101, 119, 120 not built (US-19) | decision | intentional trade-off |
| 6 | Full suite not re-run at d41c1bed | P2 | labelled in section 0 |
