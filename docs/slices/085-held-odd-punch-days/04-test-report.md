---
slice: 085-held-odd-punch-days (ALV-392)
artifact: 04-test-report
author: hrms-test-automation-engineer
date: 2026-11-20
code tested: branch slice/085-held-odd-punch-days, HEAD e57033e5 (fix round 1 included)
status: LOCAL ONLY. Nothing pushed, nothing deployed.
---

# 085 Held days: test report, round 2 (against the fixed code)

## Verdict: FAIL, for one small reason. Everything else the last round found is fixed.

**Bad news first**

1. **The engineer's baseline claim is wrong by one test.** `test_punch_rights_alv332 ... test_alv332_the_refusal_is_real` passes on the base commit (17 of 17) and fails on the 085 code (1 of 17). Release 1's new "nobody changes their own punch" line in `field_app_access.checkin_has_permission` now stops the test's negative control. The product is not wrong. The test now proves less than it did. Severity P2 (a test the slice turned red). Owner: `hrms-fullstack-engineer`. Fix: patch the new line off inside that test too, or drop the `rohan_mail` write assertion.
2. **Twenty-four more tests fail only in the full run** (payslip gate, pay screen, feature gates, plan checks). Each passes alone on the base commit and alone on 085, and passes after all the 085 modules run before it. So 085's own tests do not leak into them. I did not find what does cause them, and I did not run the full suite on the base. Label: **not proven either way**. P2, owner `hrms-devops-engineer` / engineer.
3. **The engineer's `alv085-bench` container has a stale `scripts/` copy** (not bind-mounted). Five backfill tests fail there with `no attribute 'run'` and `no attribute 'undo_run'`. They pass on `alv085-bench2`, which mounts the right script. This is an environment fault, not a code fault. Use bench2.

What was fixed and is now proven: the P1 (a sync account with HR roles releases a held day) and the backfill P2s (AC-58, 62, 63).

## 1. What I ran (all numbers are from runs I did, 19-20 Nov 2026)

Site schema: `test_site` on each container; installed apps frappe, erpnext, hrms, alvoraa_portal. `alvoraa_goals` is **not** installed. Code: the worktree tree. `alv085-bench2` mounts `.claude/worktrees/085-fix-tmp` at 487867d0; `git diff e57033e5 487867d0` over the app folders is empty, so it is the same code as HEAD.

Command shape: `bench --site test_site run-tests --app alvoraa_portal --module alvoraa_portal.tests.<module>`, one at a time, never two at once on a site.

| Module | Result on alv085-bench2 | Note |
|---|---|---|
| test_held_day_085 | 35 OK | bench1 showed 5 failures: stale scripts folder (item 3) |
| test_held_gaps_085 | 6 OK | bench1 showed 1 failure: same cause |
| test_held_p1_machine_accounts_085 | 3 OK | also 3 OK on bench1 |
| test_held_slip_085 | 1 OK + 3 OK (two summaries; the class is inherited) | |
| test_attendance_doors_085 | 16 OK | |
| test_decline_scope | 11 OK | |
| test_withdraw_after_decline | 6 OK | |
| test_team_scope_259 | 12 OK | |
| test_picker_scope_349 | 5 OK | |
| hrms Monthly Attendance Sheet | 18 OK | needs the two `_Test Fiscal Year` rows by SQL first (known bootstrap clash, already on this site) |

Total: **116 OK, 0 failed** on the fixed code. The three-in-a-row run of all nine portal modules plus the gate modules in one process also gave 0 failures.

Also run: `portal_correction_test.js` 40 passed 0 failed; `check_undefined_js.js` none; `check_portal_handlers.js` all reachable; `check_app_integrity.py` 971 checks OK. None of these has a Held test beyond one mention, see section 4.

**The engineer's full run (I read its log, I did not repeat it):** `/tmp/full2.log` in bench2 shows three summaries: 71 OK; 3,101 tests with 16 failures and 228 errors; 1,311 tests with 16 failures and 14 errors. That is 274 failing rows. The numbers match what the engineer reported.

## 2. The baseline question

Base commit 101fd29b (merge-base of the slice) in a detached worktree and a throwaway container `alv085-base` (same image, same site volume as bench2, code bind-mounted from the base worktree; I checked `held_day.py` is absent there). I ran **25 modules** from the failing list on the base, each alone, and compared failing test names to the full run.

| Group | Tests failing in full run | On base alone | Reading |
|---|---|---|---|
| 15 goals / KPI / appraisal / review modules (appraisal_visibility, calibration_note_010d, calibration_signoff, count_matches_list_045, goal_company_scope_045, goal_cycle_035, joiner_to_employee_082, leave_year, no_repeat_queries_044, numbers_match_035, portal_security_010, replacement_plan_065, review_outside_010d, review_render_027, store_hr_scoping_030) | 106 | the **same 106** fail, same names | **Proven** not caused by 085 |
| frame_api_034 | 6 | 1 of the 6 fails alone (also 1 on 085 alone) | 1 proven same; other 5 are in the next row |
| entitlement/gate family (endpoint_entitlement, frame_api_034 x5, home_api_042, pay_screen_043, payslips_gate_043, portal_module_gate_016, staff_list_034, subscription, waves_5_6) | 24 | 0 fail alone on base; 0 fail alone on 085 | Order effect in the full run. Cause **not found**. Not shown to be 085 |
| punch_rights_alv332 | 1 | 0 fail on base alone | **Caused by 085** (defect 1 above) |
| Not sampled: review_screens_010d, review_fixround_010d, review_copies_010d, review_fixround2_010d, growth/self-review `setUpClass` errors, others | about 142 | not run on base | **Inference only.** Same kind (goals app missing) as the matching 010d module I did run |

portal_security_010 on base alone: 45 ran, 13 errors; the 13 are the same ones, all `No module named ... individual_goal / kpi`. The other 32 of its tests pass, so its ceilings for AC-57 are only partly proven.

## 3. Break tests (did the test ever fail for the right reason?)

Done in-process with a script on standard input, no repo file edited. Each run first showed the unbroken module passing.

| Fix switched off | Module | Result with fix on | Result with fix off | Label |
|---|---|---|---|---|
| P1: `files_as_machine` replaced by the old `is_machine_account` | held_p1_machine_accounts_085 | 3 OK | 2 fail (`Held` stays; wanted `Present`, `Machine punch`) | **Proven** |
| AC-16: slip refresh made a no-op | held_slip_085 | 3 OK | AC-16 fails (`0.0 != 1`), AC-18 also fails | **Proven** |
| AC-18: `is_in_final_slip` forced False | held_slip_085 | 3 OK | AC-18 fails (`False is not true`) | **Proven** |
| AC-62: same switch, on held_gaps_085 | held_gaps_085 | 6 OK | still 6 OK | **Not proven.** The test patches that function to True itself, so my switch does not reach it. I could not break the script's filter without editing it |
| Engineer's earlier six break tests (hold, machine test, slip hook, company guard, limit, ninth colour) | | | | Engineer reports them. **I did not repeat them** |

## 4. Traceability

Status key: **Pass** = a test named here passes on the fixed code. **Partial** = part of the criterion has a test. **None** = no automated test (a gap, not a pass).

| AC | Test (file::test) | Status |
|---|---|---|
| 1 | held_day::test_held_is_a_status_and_the_fields_exist | Pass (bench site; a site built by migrate alone not rebuilt by me) |
| 2 | operator read-back per tenant | None (untested control) |
| 3, 4 | held_slip::test_two_held_days_cost_two_days_under_both_unmarked_settings (real draft slips) | Pass; engineer break-tested, I did not re-break |
| 5 | held_day::test_held_days_are_taken_off_the_payment_days; the reader table in notes 03 | Partial (read, not all 31 readers tested) |
| 6 | held_slip (`held_dates` in payload) | Partial |
| 7 | held_day::test_the_monthly_attendance_sheet_opens_with_a_held_row; hrms sheet 18 | Pass |
| 8 | held_day::test_the_hooks_are_wired (list JS registered) | Partial; chip never seen in a browser |
| 9 | held_gaps::test_ac9 (real auto-attendance job); held_day::test_one_punch_is_held..., test_three_punches... | Pass |
| 10 | held_gaps::test_ac10; held_day::test_switch_off_marks_as_before | Pass |
| 11 | held_gaps::test_ac11 (three more ticks) | Pass |
| 12 | none (half-day leave plus one punch) | None |
| 13 | held_day::test_three_punches_are_held_and_two_are_not | Pass |
| 14 | held_day::test_hr_approval_releases_by_the_shifts_own_thresholds, test_a_held_day_with_no_shift... | Pass |
| 15 | same test (release how, by, on) | Pass |
| 16 | held_slip::test_ac16 (real draft slip, +1 day) | Pass, **proven** |
| 17 | held_day::test_a_fault_in_the_release_never_fails_the_punch | Partial (machine path; a failing slip re-save writing Error Log is not tested) |
| 18 | held_slip::test_ac18 (slip submitted by `set_value` docstatus=1, not a real submit) | Pass, **proven**; fixture shortcut noted P4 |
| 19 | decline path unchanged; decline_scope 11 OK | Partial |
| 20 | held_day::test_a_late_machine_punch_releases_the_day; p1 module (3) | Pass, **proven** for the P1 |
| 21 | held_day::test_a_punch_by_anyone_but_the_machine_account_leaves_the_day_held, test_a_human_hr_user_without_the_sync_role..., test_a_repeat_scan... | Partial (portal `do_checkin` and a staff REST insert with a device id are not separate tests) |
| 22, 23 | none | None |
| 24 | day sheet wording (JS) | None |
| 25, 26, 27 | held_day::test_the_month_names_the_held_day_and_sends_no_reason (server side only) | Partial; screens not exercised |
| 28 | held_day::test_a_held_request_sent_from_the_portal_carries_only_the_time | Pass |
| 29, 30, 31 | none | None |
| 32 | held_day (`raise_for_report` with the time) | Partial |
| 33 | team_scope_259 12 OK, picker_scope_349 5 OK | Pass (existing refusals) |
| 34, 35 | held_day::test_the_hr_card_previews_what_approval_will_do | Pass for the computed line; button wording None |
| 36 | nothing built | n/a |
| 37 | held_day::test_the_count_is_an_integer_and_refused_outside_the_callers_companies | Partial (button text None) |
| 38, 39 | none | None |
| 40, 41, 43 | held_day::test_the_fourth_ordinary_request_is_refused_and_a_held_one_is_not, test_an_exempt_role_and_limit_zero_are_never_refused | Pass |
| 42 | same exempt-role test | Partial (Sales Executive's odd day still Held is not asserted) |
| 44 | held_day::test_ac44_the_limit_counts_the_way_graces_script_did | Partial; the live read-back and disabling the Server Script are operator steps |
| 45, 46, 47 | attendance_doors 16 OK | Pass |
| 48 | held_gaps (job runs as Administrator, leaves Held alone) | Pass |
| 49 | attendance_doors::test_raiser_cannot_submit_but_a_colleague_can, test_a_named_system_manager... | Pass (`decide` path not separately named) |
| 50, 51 | attendance_doors::test_hr_login_with_no_company_and_no_branch_sees_nobody, held_day count/settings test | Pass |
| 52 | read-back of the Company permission row | None (operator step, Q1) |
| 53 | held_day::test_only_an_hr_manager_of_the_company_may_change_the_settings | Pass |
| 54 | none (stock `track_changes`) | None |
| 55 | team_scope_259 | Partial |
| 56 | none | None |
| 57 | no test; the 010 ceilings: 32 of 45 run, 13 cannot (goals app missing) | None / partial (untested control) |
| 58, 59, 60, 61, 63 | held_day::test_backfill_end_to_end_dry_run_then_apply_then_undo, test_hold_then_rerun_finds_nothing_then_undo_restores, test_the_test_hook_still_refuses_every_other_site, BackfillScript (2); held_gaps::Backfill (3) | Pass. The kill-criterion figures (86 and 80) need Grace data and were **not run** |
| 62 | held_gaps::test_ac62 | Pass, but with a stand-in for the slip and **not break-proven** |
| 64, 65, 66, 67 | runbook `08-release-runbook.md`; AC-66 cache header | None (human read-through) |
| 68, 69 | none | None |

| Control | Test | Status |
|---|---|---|
| SEC-1 pay, release, final slip | AC-3, 4, 16, 18 | Pass |
| SEC-2 own-day doors | attendance_doors (16) | Pass |
| SEC-3 raiser | attendance_doors | Pass |
| SEC-4 scope fails closed | attendance_doors, held_day | Pass |
| SEC-5 machine punch only | p1 module (3), held_day | Pass, **proven** |
| SEC-6 settings rights, limit | AC-40, 53 | Pass |
| SEC-7 backfill | AC-58 to 63 | Pass (see AC-62, 63 caveats) |
| PRIV-1 no new reader | AC-55 to 57 | Partial |
| PRIV-2 time only, nothing in logs | AC-28 payload test only | Partial: no assertion on a captured log body |
| PRIV-3 person sees state and release source | AC-15, 20 fields | Partial |
| OPS-1 dry run, chunks | dry-run tested; chunk size not | Partial |
| OPS-2 written once | AC-11 | Pass |
| OPS-11 auto-attendance leaves Held | held_gaps | Pass |
| OPS-15 script refuses other sites | held_day (site refusal) | Pass |
| OPS-16 undo list read back | held_day (undo tests) | Pass |
| OPS-3, 4, 6, 9, 10, 14 | partly through AC-1, 2, 16 | Partial |
| OPS-5, 7, 8, 12, 13, 17 to 23 | runbook items: deploy order, window, rollback, assets.json, disk and queue | None (human) |

## 5. Journeys

**Not checked by hand.** The alv085 stack publishes no port and runs no web server, so I could not open the day sheet, the HR card, the settings card or the Attendance list chip, and so I did not compare them with `prototype-v1.html`. What exists instead: the 40-test DOM file (one mention of Held) and the server-side tests above. The screen ACs 8, 24 to 27, 29 to 31, 34 (buttons), 37 (button text) and 38 have **no proof at all**.

## 6. Defects and debt

| # | Severity | What | Owner |
|---|---|---|---|
| 1 | P2 | `test_punch_rights_alv332::test_alv332_the_refusal_is_real` fails on 085 only. Reproduce: run that module on bench2 (1 failure), then on the base (OK). The negative control no longer shows what it says | engineer |
| 2 | P2 | 24 gate tests fail in the full run but not alone. Cause unknown, not shown to be 085 | devops / engineer |
| 3 | P2 | No test for the screen criteria (see section 5), AC-12, 22, 23, 38, 39, 56, 68, 69 | engineer, or accept in writing |
| 4 | P3 | AC-62's test patches the function it should prove; no break test possible | engineer |
| 5 | P3 | `alv085-bench` scripts folder is stale; fix the mount or the copy | devops |
| 6 | P4 | AC-18 marks the slip final with `set_value`, not a real submit | engineer |
| - | not a defect | `portal_security_010` 13 errors and the goals/KPI/review errors: alvoraa_goals is not installed on this site; same on base | |

Fixture note: the held-slip tests build real draft slips through Salary Slip insert, which is the real shape. No fixture adds something real employees do not have. No real personal data anywhere.

## 7. What a human still has to check

1. Open the day sheet, HR card, settings card and the Attendance list chip on a running site and compare with the prototype (360 px width, 200% text, 44 px targets).
2. Run the backfill dry run on a copy of Grace's data and confirm 86 and 80.
3. Read-backs per tenant: AC-2 (Held in status options), AC-52 (Grace HR's Company permission), AC-44 (Grace script disabled, one refusal).
4. Read the runbook once (AC-64 to 67), including the 00:30 to 05:30 IST window.
5. Run the full suite on the base commit once, to settle defect 2.

## 8. Left behind

Containers `alv085-bench`, `alv085-bench2`, `alv085-db`, `alv085-redis` untouched. I added `alv085-base` (stopped when I finish) and the detached worktree `.claude/worktrees/085-base-check` at 101fd29b; both can be removed. I changed no repo file except this report. Nothing pushed.

**Defect 1 fixed:** the negative control in `test_alv332_the_refusal_is_real` now writes a manager's report punch, not the acting person's own, so D-2 no longer blocks it before the ALV-332 refusal. Product code and D-2 are unchanged.
