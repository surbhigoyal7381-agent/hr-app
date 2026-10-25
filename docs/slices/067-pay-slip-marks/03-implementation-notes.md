---
slice: 067-pay-slip-marks
ticket: ALV-208
artifact: implementation notes
author: hrms-fullstack-engineer
date: 2026-10-23
status: BUILT LOCALLY. Not pushed. No server touched (read only on 22 Oct).
branch: slice/067-pay-slip-marks, worktree .claude/worktrees/067-pay-slip-marks, from origin/dev
---

# 067 · Implementation notes

## 1 · What was built, file by file

| File | What | Rung |
|---|---|---|
| `alvoraa_portal/payroll_slip.py` | `push_marks_to_additional_salary` rewritten and now called by the slip's save hook, before the pay calculation re-runs. Sets `currency`. Same amount: nothing written. Changed amount: old record cancelled, new one "amended from" it. Zero: old record cancelled. Only records tagged `ref_doctype = Alvoraa Payroll Rule Set` are touched. Dated on the slip's end date, or the relieving date if earlier. All under a savepoint: a failure undoes every write of the step, logs the slip name only, and leaves a note for HR. Slip rows that still point at a cancelled engine record are dropped, because Frappe keeps them otherwise (found by the tests). Year to date, month to date and component year to date are worked out again after the engine's net pay. `ENGINE_LINES` is the list slice 066 adds its grooming row to. | 4: code in an existing hook |
| `alvoraa_portal/hooks.py` | One line: `Salary Slip.on_update` posts the notes the validate hook kept. A new slip is not in the database during validate, so a comment on it was refused. This also fixes the held-days note, which has never reached a new slip. | 4 |
| `alvoraa_portal/pay_api.py` | The Why? endpoint answers `{"from_attendance": True}` for an engine-made line, not "entered by hand". | 4 |
| `public/js/ess/portal.js` (`renderWhy` only), `public/js/ess/next-pay.js` (Why? sheet only) | The sentence: "Worked out from your attendance this month. Ask HR for the day-by-day workings." | 4 |
| `tests/test_pay_slip_marks_067.py` | 20 tests on real draft slips (section 3). | - |
| `tests/test_payroll_reprocess.py` | One test picked "any other company" and assumed it had no rule set. 063's and 067's test companies do have one. It now picks a company with no rule set. | - |
| `scripts/rehearsal_067.py` | The 11 rehearsal checks M-1 to M-11 (R-5b), on synthetic data, through a real Payroll Entry. | - |

**Arrear (Q5 of the coordinator's list):** configuration, not code. DTC's Arrear component has
"Depends on Payment Days" ticked, so a typed Arrear would be scaled by paid days. Test
`test_an_arrear_stays_whole_only_when_it_does_not_depend_on_payment_days` proves both sides.
The desk step is in the release checklist (section 6).

## 2 · Acceptance (from 04 section 6)

| # | How it is met |
|---|---|
| T1 | `test_a_juniors_reds_after_the_free_two_reach_the_slip_and_match_the_report`, `test_red_and_green_lines_and_one_record_each` |
| T2 | `test_a_senior_pays_two_hundred_a_red` |
| T3 | `test_two_reds_are_free_so_no_line_and_no_record` |
| T4 | `test_contract_staff_carry_no_marks_whatever_their_attendance` |
| T5 | `test_saving_twice_writes_nothing_new` |
| T6 | `test_a_changed_figure_cancels_the_old_record_and_amends_it` |
| T7 | `test_falling_to_nothing_cancels_the_record_and_the_line_goes` |
| T8 | `test_a_line_hr_typed_by_hand_is_untouched` |
| T9 | `test_nothing_is_written_while_the_rule_set_is_off` |
| T10 | `test_a_failure_half_way_leaves_no_half_written_lines` |
| T11 | inside T1: paid days and Basic equal the report; no Leave Encashment line |
| T12 | `test_year_to_date_follows_the_engines_net_pay` |
| T13 | `test_a_paid_slip_and_its_lines_are_never_changed` |
| T14 | `test_a_leavers_line_is_dated_on_the_relieving_date` |
| T15 | `test_the_why_sheet_never_calls_an_engine_line_hand_entered` |
| extra | `test_a_slip_made_again_reuses_the_record` (Payroll Entry re-run), `test_the_held_days_note_reaches_a_brand_new_slip`, Arrear, two wiring pins |

## 3 · Tests run

All on my own throwaway site `test067` in my own containers (`hrlocal-067`, `hrlocal-067-redis`),
never on the shared bench.

| Run | Result |
|---|---|
| `scripts/check_app_integrity.py` | OK, 797 checks, before each commit |
| `test_pay_slip_marks_067` (new) | 18 + 2 tests, OK |
| `test_why_sheet_043` (incl. "pay_api.py has no write call") | 36 + 4, OK |
| `test_salary_report` | 12 + 4, OK |
| `test_payroll_month`, `test_leave_063_engine`, `test_payslips_payload_043` | 29, 23, 13, OK |
| `test_payroll_reprocess` | first run 1 failure: `test_a_company_with_no_rule_set_is_left_alone` picked my new company, which has a rule set. Test fixed to pick a company with no rule set; 12 OK |
| `test_leave_063_card_cancel` | 1 error in the module run (`test_the_employee_withdraws_a_waiting_request`); passes alone. Leave code, not touched by this slice |
| **Full suite, once, at the end** (`run-tests --app alvoraa_portal`, branch on 653521de) | **957 integration: 1 failure, 6 errors, 20 skipped. 16 unit: OK.** None in payroll or pay code: 3 in `test_leave_year` (a Fiscal Year on this copied site overlaps "_Test Fiscal Year 2025"), 3 in `test_provision_guards` (a root-owned `kinexus_provision_jobs.json` in the copied sites volume: Permission denied), 1 in `test_shift_types_043` (a leftover "CI Test Shift" record on the copied site). All three come from the site copy, not the code. |
| After the rebase onto 30ac5192 | pay_slip_marks_067 (20), why_sheet_043 (40), payroll_reprocess (12), salary_report (16), leave_063_rules (38), payslips_payload_043 (13): **all OK** |
| `scripts/rehearsal_067.py`, BULK=40 (46 people) | **52 of 52 checks pass.** 46 slips in 16 to 31 s with or without the lines (noise is larger than the difference). Rollback 10 to 11 s. |


## 4 · Non-functional, against the code as written

| Dimension | Before → after | Verdict |
|---|---|---|
| Performance | Unchanged slip: +1 query per line (2 now). Changed line: a cancel plus an insert and submit. Measured in the rehearsal (M-10). | degrades slightly |
| Security | No new endpoint. Writes use `ignore_permissions` only inside a slip save Frappe has already checked. The Why? endpoint still checks ownership first; the new branch answers only about the caller's own line. `pay_api.py` still contains no write call (its pin test passes). | neutral |
| Reliability | A dead, broken function is now tested on real slips. Savepoint: no half-written lines. Notes now reach new slips. | improves |
| Scalability | Linear in staff, inside Frappe's own background job for more than 30 slips. | neutral |
| Maintainability | One place decides pay lines; grooming is one row. | improves |
| Data integrity | Lines are written in the slip's transaction; replace, never add; paid slips untouched; stale rows dropped. | improves |
| Compliance / privacy | Error Log titles carry the slip name only (tested). Every change to a pay line leaves a cancelled record and an amended one. | neutral |

## 5 · What else moved while I worked

origin/dev moved from 747a4293 to 42317fbe before I branched: `c625ce6a` (panels.css,
trays open against the window) and `42317fbe` (`scripts/check_portal_trays.js` and a CI step).
Neither touches my files. Then, before committing and again before finishing: `653521de` (ALV-210/211: attendance_correction.py, hooks.py 2 lines, portal.js, demo seed) and `21cdeff7`, `ec550e1b`, `520fc8ac`, `30ac5192` (leave test fixtures, Positions back to the old chart: portal.js, panels.css, positions.html, scripts). Both rebases were clean. I checked that each line 653521de added to hooks.py and portal.js is still there, and that my `renderWhy` lines sit beside the Positions change. The modules above were re-run after the second rebase.

## 6 · Release checklist for DTC (each step on Surbhi's word)

1. Deploy 063 + 067 to dev, then production, **rule set still off**. Production's
   `payroll_slip.py` is older than dev today.
2. Run `scripts/rehearsal_067.py` (and 063's seed) on a throwaway synthetic site; Surbhi sees M-10 and M-11.
3. 063 runbook R-9 to R-11.
4. **Data, not code (Surbhi, with DTC):** 94 active staff have no Salary Structure Assignment, so
   they get no slip. 3 active Permanent staff have no `dtc_grade`, so their reds cost Rs 0.
5. **Desk:** untick "Depends on Payment Days" on the **Arrear** component before any arrear is typed.
6. **Tell DTC HR:** never type Red Value or Green Value by hand. The engine owns those lines and
   drops any other row for them from a draft slip.
7. Switch the rule set on (R-12). First Payroll Entry; slips stay draft; HR compares five named
   slips with the desk report; then submit.
8. **Rollback:** untick the rule set; in Additional Salary filter `Reference Document Type = Alvoraa
   Payroll Rule Set`, payroll date in the month, submitted; cancel them; cancel and re-run the
   Payroll Entry.
9. When slice 066 ships: HR stops typing Grooming Red Value by hand that month.

## 7 · Known gaps and shortcuts

- **Acceptable simplification:** a failed marks step still saves the slip (Surbhi's choice, Q3 of
  the strategy). Frappe also shows the user the error message from the failed step, which is a
  useful warning, not a refusal.
- **Intentional trade-off:** after a late attendance fix, a draft slip is only updated when it is
  saved again (or the Payroll Entry is re-run). Same as paid days today.
- **Temporary debt:** the Why? sheet does not show the day-by-day reds; it points to HR. A
  separate slice if wanted.
- **Acceptable simplification:** `Red Value` and `Green Value` stay named constants; one tenant uses them.

## 8 · Subtract pass

Removed on the subtract pass: a separate "refresh draft slips" step after a reprocess (not
asked for); a code change for Arrear (it is a desk setting, proven by a test instead); a
per-slip lookup to tell engine rows from hand rows (the live record names returned by the
write step are enough); keeping the old `employee, company, from_date, to_date` signature of
`push_marks_to_additional_salary` (no caller). Left alone, though noticed: an unused
`add_days` import in `payroll_slip.py` that was there before.
