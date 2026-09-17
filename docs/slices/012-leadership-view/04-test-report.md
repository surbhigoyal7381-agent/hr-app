---
slice: 012-leadership-view
artifact: 04-test-report
scope: push 1 only (US-1 to US-10)
author: hrms-test-automation-engineer
date: 2026-09-15; re-tested 2026-09-16 after fix round 1; final verification 2026-09-17 after rounds 2 and 3
code tested: first run - local dev 15a2dae plus test commits bda1290, 05342a9; re-test - local dev 5aad1ae; final verification - local dev 2db1d71
site: test_site on hrlocal-bench (local only; nothing pushed, nothing deployed)
---

# 012 · Leadership view — push 1 test report

## Final verdict (2026-09-17, after fix rounds 1, 2 and 3): **Pass with issues**

**Nothing in the code under test fails.** The whole `alvoraa_portal` suite (1,073 tests) and the
whole `alvoraa_goals` suite (18) show only the 14 failures that were there before slice 012, and every
fix from rounds 2 and 3 did what it claims when I checked it myself. **"With issues" is for what is
left on purpose, not for anything broken:**

- **Eight review findings are deferred, not fixed** — including **F1 (Major)**: an HR Manager can still
  widen org-chart visibility through `set_cover_setting`, with no record. I re-checked that F1 and F2
  are still open exactly as the reviewers described.
- **DEF-4** stays a spec defect for the analyst (AC-32 wording).
- **Still not run:** a browser pass (360 px, zoom, keyboard), 2,000 employees, separate synthetic sites,
  the index-migrate timing (AC-5), and a real two-connection race.

The full final run is the last section of this file ("Final verification after fix rounds 2 and 3").
Earlier sections are kept as they were written.

### Defect table — current

| # | What | Severity | Status |
|---|---|---|---|
| DEF-1 | Two new doctypes not classified in `subscription.py` | High for release | **Fixed** (round 1), passes again in the final run |
| DEF-2 | Doubtful day older than 35 days never clears | Medium | **Fixed** (round 1) |
| DEF-3 | Menu badge missing on page load | Low | **Fixed** (round 1) |
| DEF-4 | AC-32 contradicts the approved strategy | Low (spec) | **Open — spec defect, for the analyst** |
| DEF-5 | Page re-check re-opened a Cleared record | Low | **Fixed** (round 1) |
| DEF-6 | Store HR open no-branch colleagues through `person()` / `filter_options()` | Medium (privacy) | **Fixed** (round 1) |
| DEF-7 | Response budget broken at 1,000 employees | Medium (performance) | **Fixed** (round 1) |
| DEF-8 | Store HR see no-branch colleagues, with leave types, in the organisation list | Medium (privacy) | **Fixed** (round 2, c78efcd) — verified independently |
| F3 | `get_hr_analytics` fetched `gender` for named people | Minor | **Fixed** (round 3) — verified |
| F4 | `get_hr_analytics` allowed GET and set no `Cache-Control` | Minor | **Fixed** (round 3) — verified over real HTTP |
| M1 | `data_review_items` had no rate limit although it writes | Minor | **Fixed** (round 3) — verified at the real cap of 120 |
| F1 | HR Manager can widen org-chart visibility via `set_cover_setting`, no record (`06-security-review.md`) | **Major** | **Deferred, not fixed** — confirmed still open |
| F2 | Location HR can list company-wide review records through desk or REST (`06`) | Minor | **Deferred, not fixed** — confirmed still open |
| m1 | A company that never records attendance never gets a data review (`05-review.md`) | Minor | **Deferred, not fixed** |
| m2 | List and badge stop counting above 1,000 open items (`05`) | Minor | **Deferred, not fixed** |
| m3 | A morning run failing for one company is invisible to HR for up to 26 hours (`05`) | Minor | **Deferred, not fixed** |
| m8 | A "figure is right" confirmation's audit record has no "before" (`05`) | Minor | **Deferred, not fixed** |
| m9 | Four screen strings are unconfirmed draft copy (`05`) | Minor | **Deferred, not fixed** |
| m10 | Small differences from prototype-v2 (`05`) | Minor | **Deferred, not fixed** |

---

## Verdict after fix round 1 (2026-09-16): **Pass with issues**

Six of the seven defects below are fixed and checked independently. **DEF-8 is open** — the same
kind of privacy gap as DEF-6, reached through the organisation list — and DEF-4 is a spec fix for
the analyst. The full re-test is the last section of this file.

**Everything between here and that section is the original run of 2026-09-15, kept as written.**

---

## Verdict of the first run (2026-09-15): **Pass with issues**

The scoped calls do what the spec says for every persona I tested, and **no cross-company leak
was found**. But push 1 is **not ready to push as it stands**: it turns one existing test red, it
breaks the response budget at 1,000 employees, and store HR can still open no-branch staff's days.

**Bad news first.**

| # | Defect | Severity | Caused by |
|---|---|---|---|
| **DEF-1** | **`test_invoicing.test_every_billing_doctype_is_named_as_control_plane_only` fails.** The two new doctypes (`Alvoraa Data Review Item`, `Alvoraa Leader View Settings`) are in neither `CONTROL_PLANE_DOCTYPES` nor `TENANT_DOCTYPES` in `subscription.py`. CI would go red on push. | **High for release** (blocks a green CI), low for users | 012 |
| DEF-2 | **A doubtful day older than 35 days never clears.** `existing_items()` only loads D5 records inside the 35-day window. If HR fixes the attendance after that, the record stays Open for ever: on HR's list and in the "N figures need review" count. The only way to remove it is to "confirm the absence was real", which would be false. | Medium | 012 |
| DEF-3 | **AC-31: the menu badge is not there on page load.** It appears only after HR opens HR Analytics or Data to review in that visit. (Known gap 2 in `03`.) | Low | 012 |
| DEF-4 | **Spec contradiction in AC-32**, not a code bug. The AC says store HR see company-wide items "with no confirm action"; the approved strategy (6.6) says store HR do not see company-wide items at all. The code follows the strategy, and I tested the strategy. The BA should correct AC-32. | Low (spec) | spec |
| DEF-5 | **The page re-check can re-open a Cleared record**, although decision D-5 says the page re-check "clears, does not create". It never creates one, and never touches a Confirmed one. See the probe result in section 7. | Low | 012 |
| **DEF-6** | **Store HR can open, through `person()`, the daily attendance and leave types of employees in their company who have no branch.** Frappe's non-strict User Permissions let an empty branch through. HR Analytics hides the same people from store HR (D-8), so the rule is not applied the same way. Not cross-company; narrower than before 012. Needs your decision (section 7, P1) | **Medium (privacy)** | 012 scope rule, inherited from the organisation list (D-6) |
| **DEF-7** | **At 1,000 employees the response budget is broken.** Warm p95: `get_hr_analytics` up to 895 ms, `data_review_items` up to 554 ms (budget 500 ms). Two Attendance queries read the **whole table** on every call; Attendance has no `company` index. OPS-55's condition for adding one is now met (section 5) | **Medium (performance)** | 012 |

Plainly: **fix DEF-1 before any push**; decide DEF-6 and DEF-7 (index) before `main`; DEF-2 to DEF-5
can follow.

Also not run, said plainly:

- **No browser run.** `ppj.localhost` has no 012 tables and no `alvoraa_branch` column (it was never
  migrated), and the dev server only serves `ppj.localhost`. Migrating it needs your approval. The
  page was traced by reading the code (section 6). 360 px, 200% zoom and keyboard focus are **not verified**.
- **No timing on separate synthetic sites, and no index-migrate timing (AC-5).** I timed on
  `test_site` inside one rolled-back transaction instead (section 5). Creating sites and a
  rehearsal copy is still open.
- **No real two-connection race test for AC-24.** The lock is proven by a second confirm being
  refused and by the `for_update` in the code, not by two threads.

---

## 1 · What I ran — exact commands and real results

All on `hrlocal-bench`, site `test_site`, one run at a time, `pgrep -af "run-tests|bench migrate"`
checked empty before each. Bench marked on the work board while in use.

| # | Command (inside `/home/frappe/frappe-bench`) | Code | Result |
|---|---|---|---|
| 1 | `bench --site test_site run-tests --app alvoraa_portal` | dev 15a2dae | **991 tests, 45 min. 2 failures, 13 errors, 4 skipped.** Two batches: 503 tests (1 fail, 3 errors, 4 skipped) and 488 tests (1 fail, 10 errors). All 15 classified in section 2 |
| 2 | `bench --site test_site run-tests --app alvoraa_goals` | dev 15a2dae | **18 tests OK** (2 skipped) |
| 3 | `bench --site test_site run-tests --app hrms --module hrms.alvoraa_hr_core.tests.test_attendance_score` | dev 15a2dae | **Did not start**: the hrms test bootstrap fails with "Could not find Parent Item Group: All Item Groups" (test-site setup, not 012) |
| 4 | same as 3 with `--skip-before-tests` | dev 15a2dae | **11 tests OK** |
| 5 | `run-tests --app alvoraa_portal --module alvoraa_portal.tests.test_leader_indexes_012` | dev bda1290 | **6 OK** (one new test) |
| 6 | `... --module alvoraa_portal.tests.test_morning_checks_edges_012` (new) | dev bda1290 | **16 OK, 1 expected failure** (DEF-2) |
| 7 | `... --module alvoraa_portal.tests.test_personas_012` (new) | dev bda1290 | **17 OK** |
| 8 | Mutation check: `mutate_012.py` piped to the bench's Python (section 3) | dev bda1290 | 5 of 8 mutations turned the test red; the 3 that did not are explained |
| 9 | `... --module alvoraa_portal.tests.test_personas_012` after tightening one test | dev 05342a9 | **17 OK**; the tightened test now goes red under its mutation |
| 10 | Timing: `perf_012.py 400 1000` piped to the bench's Python, one transaction, rolled back | dev 05342a9 | Section 5 |
| 11 | Probe: `probe_nobranch.py`, rolled back | dev 05342a9 | Section 7 |

Scripts 8, 10 and 11 live in my scratchpad; they were piped over stdin (no `docker cp`), they turn
off commits, and they roll back. Nothing they created is left on `test_site`.

**UI flows traced by hand (code reading, no browser):** HR Analytics for a linked HR person, HR
Analytics "not linked", Data to review list, the three confirm dialogs, the empty state, the stale
line, the error state, and the menu entry rule. Section 6.

## 2 · Every failure in the whole suite, classified

| Test | Result | Class | Evidence |
|---|---|---|---|
| `test_invoicing.TestBillingNeverWidensTenantAccess.test_every_billing_doctype_is_named_as_control_plane_only` | FAIL | **Caused by 012** (DEF-1) | Message lists exactly the two 012 doctypes. Slice 010 saw the same at 926369e and did not touch it |
| `test_invoicing` — 10 errors (`test_the_invoice_is_left_as_a_draft`, `test_a_cancelled_invoice_may_be_raised_again`, `test_the_link_is_kept_on_the_count_that_produced_it`, `test_it_separates_raised_from_waiting`, `test_a_line_says_what_it_is_in_english`, `test_an_annual_fee_never_lands_on_a_monthly_invoice`, `test_each_charge_is_its_own_line`, `test_it_is_dated_at_the_end_of_the_month_it_covers`, `test_the_headcount_is_written_on_the_invoice`, `test_the_items_are_services_not_stock`) and 1 failure (`test_running_the_job_again_skips_a_month_already_invoiced`) | 10 ERROR + 1 FAIL | **Pre-existing** | These are the 11 known from 2026-09-14. Cause in the log: "There is more than one company on this site, so the invoice has no obvious sender". `test_site` has held 20+ companies since 2026-09-09 (ERPNext test companies). 012's fixtures add two more committed companies (`S012 Kavya Retail`, `S012 Other Co`), which does not change the cause, but will keep these red after someone fixes it by removing companies — worth knowing |
| `test_leave_year.TestLeaveYearStart` — 3 errors | ERROR | **Pre-existing** | The 3 known from 2026-09-14. "Year start date or end date is overlapping with Fiscal Year _Test Fiscal Year 2025" — test-site fiscal-year data, not 012 code |

**Nothing caused by slice 010, nothing flaky.** Every 012 test module (existing and new) passed
inside the whole run and again on its own.

## 3 · New tests I added, and why

Commit `bda1290` and `05342a9` on `slice/012-leadership-view`, fast-forwarded into local `dev`.
No feature code changed.

| File | Tests | Why they were missing |
|---|---|---|
| `tests/test_personas_012.py` (new, 17) | HR Analytics: System Manager, line manager, employee, Leadership, Guest refused; System Manager + HR sees every company; HR User of **another company** sees only that company — names **and counts**; store HR with a Branch permission but no Employee and no Company permission is "not linked". Data to review: the same refusals on both endpoints; other-company HR cannot list or confirm; **store HR cannot reach Other Co's branch of the same name**; System Manager + HR lists every company; central **HR User** (not Manager) confirms a company-wide record; **role revoked mid-session** loses all three calls at once. Org setting: HR User, store HR, line manager, employee, Leadership refused even for the allowed key. `person()`: Leadership and Employee refused even when the stored org roles list them (the AC-53 `person()` part had no test); line manager keeps their report only; store HR refused for Other Co's same-named branch; `filter_options` refused for Leadership and Employee | The first tests covered HR Manager, store HR and not-linked HR only. Most cross-company leaks show up with the third persona or with same-named branches |
| `tests/test_morning_checks_edges_012.py` (new, 16 + 1 expected failure) | D5 at **exactly** the minimum (5 checked, 4 not); the job **reads the stored minimum** (10 hides an 8-person branch, 8 shows it); people with **no branch** never make a doubtful day (D-12); leavers with no branch make one **company-wide D18-1** record that cannot be confirmed and store HR never sees (deviation 4); a D6 or D18-2 confirmation **lasts one leave year** (D-3); a **whole second run** of the job writes nothing for all four rules, zero Version rows (AC-18); **confirmations survive fixed data** through both the page re-check and the job (AC-24); after migrate: indexes → settings → queued check, install never queues, a queue failure is logged and migrate carries on (OPS-72); the slow-call line has no company, branch or name (OPS-56/57); both doctypes track changes, nobody can create or delete a review record (OPS-58); **DEF-2 as an expected failure** | None of these had a test. D-3, D-12, deviation 4 and OPS-72 order were only in the notes |
| `tests/test_leader_indexes_012.py` (+1) | `test_the_resync_really_drops_an_unmarked_index`: removes one Property Setter, re-syncs Employee, asserts the index is **gone**, then restores both | Proves the existing OPS-71 survival test really re-syncs. It does: without the marker, `updatedb` dropped `Employee.relieving_date`'s index. So the survival test is a real tripwire |

**Mutation check (does each new test go red when the protection is broken?)** — patched in memory only:

| Mutation | Test | Result |
|---|---|---|
| M1 `hr_scope` widened to every company | other-company HR in HR Analytics | green at first → **I tightened the test** (names reach the page through permission-checked lists; counts come from plain SQL). After `05342a9`: **red** (97 people ≠ 51) |
| M2 same widening, for Data to review | other-company HR cannot confirm | green: Frappe's User Permissions and `has_permission(write)` still refuse. A second, independent guard — good for the product; the test stays as evidence of behaviour |
| M3 `_in_organisation` always true | store HR vs Other Co's same-named branch | **red** |
| M4 org-roles guard emptied | Leadership/Employee `person()` | green: the `get_list` read inside `_in_organisation` still refuses them. The existing `TestOrgRolesGuard` summary tests are the ones that catch M4 |
| M5 HR role check widened | non-HR refused on both endpoints | **red** |
| M6 job ignores stored minimum | the job uses the stored minimum | **red** |
| M7 job and re-check treat Confirmed as Open, controller lock off | confirmations survive fixed data | **red** |
| M8 check queued before indexes | after-migrate order | **red** |

DEF-2's expected failure was checked for the **right reason**: in a rolled-back probe the record was
Open while inside the window, and after the attendance was fixed 40 days later the run changed 0
records and the status was still Open.

## 4 · Traceability — every push 1 AC

Result = what happened in runs 1, 5–7 and 9. "pass" means the named test passed in those runs.

### US-1 · Fast enough

| AC | Test(s) | Result |
|---|---|---|
| AC-1 all 8 indexes | `test_leader_indexes_012.test_install_creates_all_eight_indexes`, `test_the_hook_marks_fields_during_migrate_too` | pass — **on test_site, not a fresh `install-app` site** (gap) |
| AC-2 second migrate changes nothing | `test_running_again_adds_and_changes_nothing` | pass |
| AC-3 timings at 400 / 2,000, EXPLAIN | timing run (section 5) | **fail at 1,000 (DEF-7)**: 400 meets the warm budget; 1,000 is over 500 ms; EXPLAIN shows full scans of Attendance. Measured in a rolled-back transaction on test_site; 2,000 not run; not separate synthetic sites |
| AC-4 fixed query count | `test_org_figures_012.TestQueryCountsDoNotGrow`, `test_hr_analytics_scope_012.TestQueryCount`, `test_morning_checks_012.TestJobQueryCount`, `test_data_review_012.TestPageQueryCount` | pass. **`data_review_confirm` has no query-count test** (gap; it reads one row per item, capped at 40) |
| AC-5 index migrate time | — | **not run** (needs DDL on a volume site or the rehearsal copy) |

### US-2 · One calculation

| AC | Test(s) | Result |
|---|---|---|
| AC-6 95.4% formula | `test_org_figures_012.test_present_wfh_and_half_days_over_everyone_expected` | pass (HR side; leader side is push 2) |
| AC-7 draft / cancelled / amended | `test_only_the_submitted_record_counts_once` | pass |
| AC-8 late and short days | `test_late_arrivals_and_short_days` | pass |
| AC-9 leave year, calendar fallback | `test_this_leave_years_leave_over_allocations_overlapping_it`, `test_each_company_uses_its_own_leave_year`; fallback in `test_leave_year` | pass (the `test_leave_year` module has 3 pre-existing errors, so the **calendar-year fallback test did not run cleanly** — gap) |
| AC-10 HR = calculation | `test_hr_analytics_scope_012.test_hr_analytics_and_the_calculation_agree` | pass (leader half is push 2) |
| AC-11 appraisal scores unchanged | `test_org_figures_012.TestAppraisalScoresDoNotMove` (2); hrms `test_attendance_score` (11) | pass |

### US-3 · Doubtful days

| AC | Test(s) | Result |
|---|---|---|
| AC-12 one record, counts only | `test_morning_checks_012.test_a_doubtful_day_becomes_one_open_record_with_counts_only`; `test_data_review_item_012.test_no_employee_field_and_no_name` | pass |
| AC-13 thresholds | `test_ninety_five_percent_absent_and_under_five_percent_checked_in` | pass (20-person version of the 100-person example) |
| AC-14 4-person kiosk never checked | `test_a_four_person_branch_is_never_checked`; new `test_a_group_of_exactly_the_minimum_is_checked` | pass |
| AC-15 no check-ins at all | `test_absent_alone_decides_when_the_company_has_no_check_ins` | pass |
| AC-16 left out for that branch only | `test_org_figures_012.test_open_doubtful_days_leave_out_that_branch_only`; `test_hr_analytics_scope_012.test_open_items_and_doubtful_days_of_other_stores_do_not_reach_store_hr` | pass |
| AC-17 warning and "N figures need review" line | server: `TestReviewItemsInScope`; page: `test_data_review_page_012.test_hr_analytics_draws_not_linked_and_the_review_lines` (static) | pass (copy traced, not seen in a browser) |
| AC-18 re-run changes nothing; fixed → Cleared | `test_a_second_run_changes_nothing_and_a_fixed_day_is_cleared`; new `test_every_rule_second_run`; new expected failure `test_fixing_a_day_older_than_the_window_still_clears_it` | pass inside 35 days; **fails after 35 days (DEF-2)** |

### US-4 · HR confirms

| AC | Test(s) | Result |
|---|---|---|
| AC-19 confirm absence: who, when, figures, Version | `test_data_review_012.test_hr_confirms_the_absence_was_real` | pass. **Weak spot:** the figure check is skipped when the fixture days cross a month (first 5 days of a month). The `ldr:` cache part is push 2 (deviation 9) |
| AC-20 "Keep them left out" sends nothing | — | **no server test** (true by construction: the button only closes the dialog; traced in code) |
| AC-21 leave figure right | `test_hr_confirms_leave_used_is_right`; new `test_hr_user_with_company_permission_confirms_leave_used` | pass |
| AC-22 leavers: no "it is right" for D18-1 | `test_left_with_no_leaving_date_cannot_be_confirmed`; new `test_one_company_wide_record_that_cannot_be_confirmed`; page link traced | pass (desk link not opened in a browser) |
| AC-23 store HR 403 other store / company-wide, one log line | `TestStoreHrConfirms` (4); new `test_store_hr_same_branch_name_in_another_company_is_refused` | pass |
| AC-24 Confirmed survives job; second confirm refused | `test_a_confirmed_day_stays_confirmed`, `test_a_second_confirmation_of_the_same_day_is_refused`, `test_rows_are_locked_while_they_are_checked` (source check); new `test_page_recheck_and_job_leave_confirmations_alone` | pass. **Real simultaneous race not tested** |
| AC-25 no change on any path | `test_data_review_item_012.test_a_confirmed_record_cannot_be_changed_on_any_path`, `test_open_counts_cannot_be_changed_in_the_desk` | pass |

### US-5 · "Needs review" rules

| AC | Test(s) | Result |
|---|---|---|
| AC-26 D6 | `TestLeaveNeedsReview`, `TestLeaveAtOnePercent` | pass (3 people, same percentages) |
| AC-27 D18-1 | `test_left_with_no_leaving_date_per_branch` | pass |
| AC-28 D18-2 | `test_no_leaving_date_in_twelve_months_is_a_company_record` | pass |
| AC-29 cleared on page open | `test_leaving_dates_clear_leavers_when_store_hr_opens_the_page` | pass |
| AC-30 new tenant: no figures, no records | `test_no_attendance_means_no_records`, `test_no_attendance_means_no_figure` | pass. "No figures yet" copy on the page: traced ("—"), leader half is push 2 |
| BA-Q1 / D-2 "figure is right" for leavers | `test_nobody_left_in_a_year_can_be_confirmed` | pass |
| D-3 lasts one leave year | new `test_leave_and_nobody_left_are_asked_again_next_leave_year` | pass |

### US-6 · Data to review page

| AC | Test(s) | Result |
|---|---|---|
| AC-31 cards, copy, footer, badge | `test_central_hr_sees_every_kind_with_counts_and_no_people`; page pins in `test_data_review_page_012` | server pass; **badge on page load fails (DEF-3)**; copy traced only |
| AC-32 store HR only own items; others 403 | `test_store_hr_sees_only_their_store`, `test_people_who_are_not_hr_are_refused`; new persona refusals | pass **against the approved strategy** (store HR do not see company-wide items). Spec text contradicts it (DEF-4) |
| AC-33 last checked / stale > 26 h | `test_last_checked_and_the_stale_line` | pass |
| AC-34 empty state | `test_a_store_with_no_open_records_gets_an_empty_list` | pass (draft copy, BA-Q12) |
| AC-35 line links to Data to review | page pin `test_hr_analytics_draws_not_linked_and_the_review_lines`; traced | pass (no "Needs you" strip exists yet) |
| AC-36 no names or IDs | `test_central_hr_sees_every_kind_with_counts_and_no_people` | pass |

### US-7 · Morning checks

| AC | Test(s) | Result |
|---|---|---|
| AC-37 cron → enqueue once | `test_the_cron_entry_only_queues_the_job_once` | pass (asserts the call arguments; the "fires twice, one job" part relies on Frappe's `deduplicate`, which I read in Frappe's source: it skips a queued or started job with the same id) |
| AC-38 crash between companies | `test_a_run_after_a_crash_ends_like_one_clean_run` | pass |
| AC-39 failure log: company, stage, type only | `test_a_failure_is_logged_without_figures_and_the_stamp_stays_old` | pass |
| AC-40 release plan in `07` §5 | — | **not a code test**; for the release check |
| AC-161 migrate changes no HR record | `test_a_good_run_stamps_last_checked_and_changes_no_hr_record`; new after-migrate tests | pass |
| AC-163 | — | push 2 (Leadership role) |
| OPS-72 check after migrate | new `TestAfterMigrate` (3) | pass. I checked Frappe's `enqueue`: during migrate it queues normally and only runs inline if Redis cannot be reached, as the code comment says |
| D-9 skip tenants without analytics | `test_a_plan_without_analytics_is_skipped` | pass |

### US-8 · HR Analytics scoped (G1)

| AC | Test(s) | Result |
|---|---|---|
| AC-41 store HR: one store | `test_store_hr_sees_only_their_store` | pass |
| AC-42 other company nothing, same-named branch | `test_a_company_hr_user_sees_nothing_of_another_company`; new `test_hr_user_of_another_company_gets_only_that_company` | pass |
| AC-43 central HR: all branches, not Other Co | `test_central_hr_sees_every_branch_of_their_company` | pass |
| AC-44 not linked | `test_hr_with_no_company_and_no_employee_gets_no_figures`; new store-HR-no-employee test | pass (draft copy, BA-Q5) |
| AC-45 no `ignore_permissions`, parameters, gates kept | `test_no_ignore_permissions_and_the_gates_stay`, `test_a_branch_name_with_a_quote_is_just_a_value`, `test_portal_security_010` CEILINGS | pass |

### US-9 · `person()` and `filter_options()` (G3)

| AC | Test(s) | Result |
|---|---|---|
| AC-46 review line counts store's items only | `test_open_items_and_doubtful_days_of_other_stores_do_not_reach_store_hr` | pass |
| AC-47 store HR 403 other store, 200 own | `test_store_hr_cannot_open_another_stores_employee`, `test_store_hr_opens_their_own_stores_employee`; new same-named-branch test | pass |
| AC-48 12-month cap | `test_a_long_range_is_cut_to_twelve_months` | pass |
| AC-49 filter options from own store | `test_store_hr_sees_only_their_stores_options` | pass |
| AC-50 line manager, System Manager | `test_a_line_manager_keeps_their_line_and_nothing_else`, `test_system_manager_is_unchanged`; new line-manager test | pass |

### US-10 · Settings call and org-roles guard (G2)

| AC | Test(s) | Result |
|---|---|---|
| AC-51 allow-list, 403, unchanged, one log line each | `test_kra_link_mandatory_still_saves`, `test_every_other_key_is_refused_unchanged_and_logged`, `test_a_value_outside_zero_and_one_is_refused`, `test_a_system_manager_is_held_to_the_same_list` | pass |
| AC-52 get limited | `test_reading_is_limited_to_the_same_keys` | pass |
| AC-53 Leadership/Employee refused on summary, person, filter_options; log line | `TestOrgRolesGuard` (4); new `test_leadership_and_employees_cannot_open_another_person_even_if_listed`, `test_filter_options_refused_for_leadership_and_employee` | pass (the `person()` part had no test before) |
| AC-54 Org settings screen still saves | `test_the_page_still_calls_only_the_allowed_key`, `test_portal_call_paths` | pass (not clicked in a browser) |

**ACs with no automated test:** AC-5, AC-20 (by construction), AC-40 (release doc). Partial: AC-1
(not a fresh site), AC-3 (no 2,000, no separate sites), AC-24 (no real race).

## 5 · Performance — measured numbers

**How:** `perf_012.py`, run in the bench's Python against `test_site`, inside **one
transaction that was rolled back** (commits turned off; "seeded employees left = 0" printed after
each size). Not separate synthetic sites. The seed per size: one company, 6 branches (one with 4
people), 300 calendar days of attendance (6-day weeks, about 6% absent, 2% on leave, 11% late),
check-ins for half of those present, one allocation and two approved leave requests per person,
and one doubtful day. Four HR scopes: company (HR Manager), one branch, two branches, and a set
holding the 4-person branch (store HR). Each endpoint 30 times **cold** (whole site cache cleared
before every call — harsher than a real first call, it reloads every DocType and permission) and
30 times **warm**. `EXPLAIN` on every SELECT sent by one call.

**Environment caveat:** the local bench runs `bench serve` (one process) and shares Docker with
three other Frappe stacks on a Windows PC. Numbers are for comparing against the budget, not a
production forecast.

| Size | Seeded | Morning job, one company |
|---|---|---|
| 400 | 400 people, 102,800 attendance, 47,091 check-ins | **962 ms** (budget ≤ 20 s) — pass |
| 1,000 | 1,000 people, 257,000 attendance, 117,846 check-ins | **5,082 ms** (budget ≤ 60 s at 2,000) — pass |

p95 in ms (p50 in brackets). Budget from `07` §3 H: `get_hr_analytics` ≤ 500 ms at 400 and
≤ 1 s at 2,000; `data_review_items` ≤ 500 ms at every size; `nfr-budget.md` §2: a whitelisted
call ≤ 500 ms p95.

| Size | Scope | `get_hr_analytics` warm | cold | `data_review_items` warm | cold |
|---|---|---|---|---|---|
| 400 | company | 359 (187) | 944 (624) | 345 (181) | 714 (568) |
| 400 | one branch | 172 (129) | 963 (561) | 143 (110) | 858 (523) |
| 400 | two branches | 188 (163) | 794 (604) | 283 (152) | 752 (555) |
| 400 | set with 4-person branch | 289 (161) | 676 (565) | 163 (139) | 751 (526) |
| 1,000 | company | **761** (420) | **1,638** (902) | **536** (417) | **1,099** (828) |
| 1,000 | one branch | 447 (313) | **1,116** (725) | 456 (287) | **992** (746) |
| 1,000 | two branches | **544** (411) | **1,373** (840) | **554** (377) | **1,096** (781) |
| 1,000 | set with 4-person branch | **895** (674) | **1,618** (905) | 433 (339) | **1,234** (868) |

**Reading it plainly:**

- **At 400 people, warm calls meet the budget** (all ≤ 359 ms). Cold calls (full cache flush) are
  680–960 ms, over 500 ms.
- **At 1,000 people — your stated target size — the budget is broken (DEF-7).** Warm
  `get_hr_analytics` is 447–895 ms (over 500 ms in 3 of 4 scopes, under the 1 s ceiling set for
  2,000). Warm `data_review_items` is 433–554 ms (over 500 ms in 2 of 4). Cold calls reach 1.0–1.6 s.
- **2,000 was not run.** Given the growth from 400 to 1,000, it would likely go past 1 s.

**`EXPLAIN` — full scans of big tables (AC-3 says there must be none on Attendance or Employee Checkin):**

| Query | Where | Rows scanned (estimate, 1,000 size) |
|---|---|---|
| `select max(a.attendance_date) from tabAttendance a where a.docstatus = 1 and a.company in (…)` (`org_figures.data_up_to`) | `get_hr_analytics` and `data_review_items`, **every scope, including one branch** | **212,585 — whole table** |
| `select 1 from tabAttendance where company = %s and docstatus = 1 limit 1` (`company_findings`) | `data_review_items` re-check and the morning job | **212,585** (the `limit 1` stops early when the company has data; a company with no attendance reads the whole table) |
| Employee, Leave Allocation, Leave Application | several | ≤ 2,051 — small tables; the optimiser's choice, not a concern at this size |
| Employee Checkin | — | **no full scan** |

The Attendance table has **no index on `company`** (checked with `SHOW INDEX`: only `name`,
`alvoraa_branch`, (`alvoraa_branch`, `attendance_date`), `attendance_date`, `creation`, `employee`,
`status`). OPS-55 said a (`company`, `attendance_date`) index is not approved "unless `EXPLAIN` shows
a full scan". **It does.** That index needs your decision; it is the likely fix for most of DEF-7.

Query counts per call at 1,000 people: `get_hr_analytics` 45 SELECTs (company) / 34 (branch);
`data_review_items` 12 / 10; the job 9. These do not grow with people (the query-count tests
prove that separately).

## 6 · UI journeys traced against prototype v2 (code reading, no browser)

| Journey / state | What the code does | Matches prototype v2 "hr-review"? |
|---|---|---|
| Menu | "Data to review" beside HR Analytics, shown by the same rule (`roles.is_hr` and plan). `is_hr` includes HR User, HR Manager **and System Manager** | Yes. A System Manager with no HR role sees the entry and gets a refusal on open (known gap 8) |
| Badge | `sb-dr-badge` set only inside `drAnalyticsNotes` and `drRender` | **No — only after HR opens one of the two panels (DEF-3)** |
| HR Analytics top lines | "Data up to {date}"; amber "Some attendance days look wrong" with the dates; "N figures need review. Leaders see 'Needs review' until they are fixed." with an "Open Data to review" button | Yes |
| Not linked | Hides the KPI grid and cards; shows the draft BA-Q5 message | Yes (draft copy) |
| Intro line | Same sentence as the prototype | Yes |
| Doubtful-day card | Title "{n} attendance days look wrong", amber chip "Doubtful days", counts and branches, "Leaders see", "Open attendance for these days" (desk list filtered by company, branches, dates), "The absence was real" only when `can_confirm`, "Found … · Checked again every morning" | Yes. Wording differs slightly ("no more than 2% checked in" vs "fewer than 2%") |
| Leave card | "Needs review" chip, requests / people / days, "Open leave requests", "The figure is right, show it" only for whole-company HR | Yes. Found line lacks "(3 months into the leave year)" |
| Leavers card | D18-1: "Open these {n} people" (Employee list, status Left, no leaving date), no confirm, "Clears by itself…". D18-2: "Open employees who left" + "The figure is right, show it" | Yes, plus BA-Q1's D18-2 button |
| Confirm dialogs | `role="alertdialog"`, `aria-modal`, labelled and described; focus starts on the safe button; Escape closes; Tab stays inside; "Count them" disabled after one tap | Yes. Doubtful text says "for this month" where the prototype says "for September". Leave text omits "(3 requests, 15 days of 6,912)" |
| After confirm | Toast (draft copy), list reloads, HR Analytics marked for reload | Focus is **not returned** to a control after success (the card is redrawn); it falls to the page. Low a11y issue |
| Footer | "Every 'the figure is right' confirmation is kept with who made it and when." | Prototype also says "Store HR sees only items for their own branch." — omitted |
| Stale / never run / error | Amber "Checks have not run since {date time}", "Checks have not run yet…", error card with "Try again" | Yes |
| 360 px | CSS: action buttons full width under 640 px, chip un-floated, 44 px targets, focus outline | **Not seen at 360 px** |
| Colour only? | Chips carry words ("Doubtful days", "Needs review") | OK |

## 7 · Probes — findings that are not in the ACs

Run in one rolled-back transaction (`probe_nobranch.py`).

| # | Question | Result | Meaning |
|---|---|---|---|
| P1 | Can store HR (HR User, Branch permission on their store, Employee in that store) open, through `person()`, an employee **of the same company with no branch**? | **Yes — opened.** `apply_strict_user_permissions` is 0 on the site, so Frappe's User Permissions let a record with an empty branch through `get_list` | **DEF-6.** Store HR can see the daily attendance and leave types of no-branch staff (often head office) in their company. HR Analytics leaves those people out for store HR (decision D-8), so the two screens disagree. It is **not** cross-company and is far narrower than before 012 (then any org-role holder opened anyone). The organisation list (`_population`, decision D-6) has the same behaviour, so this is a product decision: an explicit branch filter for location HR in `_in_organisation` and `_population`, or strict user permissions |
| P2 | Does the page re-check re-open a Cleared record? | Leaver record Cleared by the job after a leaving date was added; the date was removed again; store HR opened Data to review; the record was **Open** again | **DEF-5.** Harmless for data (the finding is real again), but it is not "clears only" as D-5 says. Either accept and correct D-5's wording, or pass a flag so the re-check skips Cleared records |

## 8 · Security, privacy and DevOps items in scope for push 1

| Item | How it was checked | Result |
|---|---|---|
| SEC-7 new endpoints: POST, plan-gated, HR only, no-store | `test_endpoint_hygiene`; persona refusals (System Manager, line manager, employee, Leadership, Guest, revoked role) | pass |
| SEC-8 no `ignore_permissions`, parameters only | CEILINGS in `test_portal_security_010` (50 pass in the whole run); quote-in-branch test | pass |
| SEC-10 settings: System Manager only, 3–10, reason, history | `test_leader_settings_012` (14); new `test_the_job_uses_the_stored_minimum` | pass |
| SEC-12 minimum not a Frappe default; allow-list | `test_the_minimum_is_not_a_frappe_default`; G2 tests | pass |
| SEC-13 record scope, confirm checks, locks | `test_data_review_item_012` (10), `test_data_review_012` (23), new persona tests | pass |
| SEC-14 one refusal line, rule id, no scope values | AC-23, AC-47, AC-51 tests | pass |
| SEC-15 failure log has no figures or names | `test_a_failure_is_logged_without_figures…` | pass |
| SEC-16 HR Analytics scope | `test_hr_analytics_scope_012` (10), new persona tests; M1 mutation red | pass |
| SEC-17 `person()` / `filter_options()` scope | `test_attendance_scope_012` (8), new tests; M3 mutation red | pass — **see probe P1** |
| SEC-18 allow-list | `test_org_settings_allowlist_012` (10), new persona test | pass |
| SEC-19 org-roles guard | `TestOrgRolesGuard` (4), new `person()` test | pass |
| SEC-22 / PRIV-10 counts only, groups ≥ minimum | small-group and boundary tests | pass |
| PRIV-1 (HR response) no names | AC-36 test | pass |
| PRIV-13 appraisal numbers unchanged | `TestAppraisalScoresDoNotMove`, hrms `test_attendance_score` (11) | pass |
| PRIV-14 declared retention | **Manual check**: the doctype description says "Kept 13 months after the date it concerns plus one year (declared, not purged automatically)". No purge exists | declared only — an untested control by design (Q10) |
| OPS-1, OPS-6 one grouped calculation | figures and agreement tests | pass |
| OPS-5, 20, 52, 70 indexes | `test_leader_indexes_012` | pass |
| OPS-71 indexes survive re-sync | survival test + new tripwire proving the re-sync drops an unmarked index | pass — the test is real |
| OPS-7, OPS-63 fixed query counts | four query-count tests | pass (no test for `data_review_confirm`) |
| OPS-9, OPS-48 cron → long queue, dedupe, write only on change | cron test, re-run tests | pass |
| OPS-21, OPS-22 | D5 tests | pass |
| OPS-40 30 confirms/hour per user | `test_thirty_confirmations_an_hour_per_user` | pass |
| OPS-49 page re-check | AC-29 test, `test_the_page_never_creates_a_record` | pass — **see DEF-5** |
| OPS-50 stamp, stale line, fixed title | stamp and stale tests | pass |
| OPS-53, OPS-64 timings | section 5 | **partial run; budget broken at 1,000 (DEF-7)** |
| OPS-56, OPS-57 slow-call line | new `TestTheSlowCallLine` | pass |
| OPS-58 track changes | settings Version tests; new `test_both_doctypes_track_changes` | pass |
| OPS-72 check after migrate | new `TestAfterMigrate` | pass |
| OPS-73 deploy window, OPS-77 `bench version`, OPS-79/80/81 | release items | **not testable here** — for `07` §5 |
| OPS-74 AC-11 pin in CI | `TestAppraisalScoresDoNotMove` is in `alvoraa_portal` (CI runs it) | pass |
| OPS-75 counter covers new files | CEILINGS table | pass |
| OPS-76 enqueue path resolves | `frappe.get_attr` assertion | pass |
| OPS-82 page size | `03` says ~19.5 KB; I did not re-measure | not re-checked |

## 9 · Parallel work during this run

- `origin/dev` brought in nothing all session (`git log dev..origin/dev` empty at start and end).
- Slice 010 worked in its own worktree (`e0c3c67` there); it did not merge into `dev` or use the
  bench while I did.
- Uncommitted work in the main checkout that is not mine and was not touched:
  `hrms/.../alvoraa_position.py`, `.claude/*`, `CLAUDE.md`, `backlog/…`, deleted
  `OBJECTIVES_KPI_REQUIREMENTS.md`. `alvoraa_position.py` is served to the bench, but none of the
  suites I ran touches it.
- My commits: `bda1290`, `05342a9` (tests only), on `slice/012-leadership-view`, fast-forwarded into
  local `dev`. Not pushed.

## 10 · Not automated — the human checklist

| Check | Why not automated | When |
|---|---|---|
| Browser: HR Manager opens Data to review, confirms one item, sees it clear; store HR sees only their store; not-linked HR sees the message | `ppj.localhost` is not migrated for 012; the dev server serves only that site. Needs your approval to migrate a local site, or do it on dev | Before the dev push is accepted |
| 360 px, 200% zoom, keyboard through the confirm dialog, screen reader reads the alert dialog | Needs a browser on a migrated site | Same |
| Desk links from the cards ("Open these 14 people", "Open attendance for these days") land on the right filtered list | Needs a browser | Same |
| Timing on separate 400 / 1,000 / 2,000-person sites, 30 cold and warm calls, EXPLAIN, index migrate timed (AC-3, AC-5, OPS-53, OPS-64) | Needs your word to create sites; I used a rolled-back transaction instead | Before `main` |
| Concurrency on a rehearsal stack (OPS-65) | Needs gunicorn and your word | Before `main` |
| Two HR people confirming the same item at the same second | Needs two real connections with committed data | Once, by hand on dev |
| First 06:30 run on dev succeeds; no "Leader data checks failed" row (AC-40, OPS-80) | Happens after the push | Morning after the dev push |
| Retention (PRIV-14) | Declared, no purge exists | When Q10 is decided |

---

# Re-test after fix round 1 (2026-09-16)

**Code tested:** local `dev` **5aad1ae** (= `slice/012-leadership-view`), which holds slice 012 fix
round 1 **and** slice 010 group D phase 4. `origin/dev` is still c27fb56 — nothing was pushed.

## R1 · New verdict: **Pass with issues**

Six of the seven defects are fixed, and I checked each one myself instead of trusting the
engineer's tests. **One privacy gap is left, and it is the same gap as DEF-6 through a different
door.**

| # | Defect | Status now | How I checked |
|---|---|---|---|
| DEF-1 invoicing classification | **Fixed** | `test_every_billing_doctype_is_named_as_control_plane_only` passes in the whole-suite run (log line 278) |
| DEF-2 old doubtful day never clears | **Fixed** | My own probe: a day 40 days old, found while inside the window, went to **Cleared** once the attendance was corrected. The expected-failure marker is gone and the test passes as a normal test |
| DEF-3 badge missing on page load | **Fixed** | My own probe: `get_portal_context` returns `review_open_count` = 2 with 2 Open records on the **first** load, drops to 1 straight after a confirmation (so it sits outside the one-hour cache), and an employee gets no such field at all |
| DEF-4 AC-32 contradiction | **Open — for the analyst** | Not a code defect. The code and the tests follow the approved strategy |
| DEF-5 page re-check re-opened a Cleared record | **Fixed** | My own probe: record Cleared by the job, data made bad again, HR opened Data to review — the record stayed **Cleared** |
| **DEF-6 store HR reaching no-branch colleagues** | **Half fixed — see DEF-8** | `person()` refuses (probe), `filter_options()` no longer lists a no-branch manager (probe), HR Analytics still hides them (probe). **But the organisation list still shows them** |
| DEF-7 speed at 1,000 people | **Fixed** | My own re-measurement, section R4 |

### New defect found in the re-test

| # | Defect | Severity |
|---|---|---|
| **DEF-8** | **Store HR still see no-branch colleagues in Attendance Insights' organisation list.** `attendance_analytics._population` (view "organisation") reads Employee with `get_list` and no branch filter, and Frappe's User Permissions are not strict here, so a record with an empty branch passes a Branch permission. Logged in as store HR, my probe got 5 rows **including the head-office employee**. Each row carries that person's **name, days present and absent, late and short days, and `leave_by_type` — the leave types**. That is more than `person()` ever showed, and `person()` now refuses the same people. This is the D-6 gap recorded in `00` (slice 011 behaviour), but after fix round 1 two screens apply two different rules. **The fix looks small:** the same `_linked_branches()` helper the engineer added, used in `_population`. It returns None for a user with no Branch permissions, so slice 011's pinned tests (`test_central_hr_sees_every_store_in_the_portal_view`, `test_system_manager_alone_still_sees_every_store_in_the_portal_view`) are about users it would not touch. **Your decision: fix it in push 1, or record it as accepted.** | **Medium (privacy)** |

## R2 · Runs — commands and real results

Bench claimed on the work board; `pgrep -af "run-tests|bench migrate"` empty before each run; one
run at a time.

| # | Command | Result |
|---|---|---|
| R-1 | `bench --site test_site run-tests --app alvoraa_portal` | **1,065 tests (538 + 527), 38 min. 1 failure, 13 errors, 4 skipped** |
| R-2 | `bench --site test_site run-tests --app alvoraa_goals` | **18 tests OK** (2 skipped) |
| R-3 | `run-tests --module alvoraa_portal.tests.test_leader_indexes_012` | **6 OK** |
| R-4 | `run-tests --module alvoraa_portal.tests.test_morning_checks_edges_012` | **16 OK, no expected failures** (the marker is gone) |
| R-5 | `run-tests --module alvoraa_portal.tests.test_personas_012` | **17 OK** |
| R-6 | `probe_r2.py` piped to the bench's Python, rolled back | DEF-6, DEF-2, DEF-5 and the query-change checks — section R3 |
| R-7 | `probe_badge.py`, rolled back | DEF-3 — three checks, all pass |
| R-8 | `perf_012.py 1000`, rolled back | section R4 |

**Every failure in R-1, classified:**

| Test | Result | Class | Evidence |
|---|---|---|---|
| `test_leave_year.TestLeaveYearStart` × 3 | ERROR | **Pre-existing** | The same "Fiscal Year _Test Fiscal Year 2025 overlapping" as on 2026-09-14 and in my first run |
| `test_invoicing` × 11 (10 errors + 1 failure) | ERROR / FAIL | **Pre-existing** | The same "more than one company on this site" as before; `test_site` has held 20+ companies since 2026-09-09 |
| — | — | — | **Nothing caused by 012, nothing caused by 010 group D phase 4, nothing flaky.** The first run had these same 14 plus DEF-1; DEF-1 is gone. The suite also grew: 991 tests then, 1,065 now (010 D phase 4's tests and mine) |

## R3 · Independent checks of the fixes (rolled-back probes)

| Check | Result |
|---|---|
| Store HR opens a no-branch colleague through `person()` | **refused** (was: opened) |
| Store HR opens a colleague in their own branch | still works |
| `filter_options()` lists a no-branch manager to store HR | **no** |
| `person()` with an explicit date range for a no-branch colleague | **refused** |
| HR Analytics shows no-branch people to store HR | **no** |
| **Organisation list (`summary(view="organisation")`) shows a no-branch colleague to store HR** | **YES — DEF-8** |
| Doubtful day 40 days old, found inside the window, data then fixed | **Cleared** |
| The same day made bad again after it was Cleared | stays Cleared until it falls inside the 35-day window again. Sensible, but worth knowing |
| Leavers record Cleared by the job, data made bad again, HR opens the page | stays **Cleared** |
| Badge on the first portal load / straight after a confirmation / for an employee | 2 / 1 / field absent |

## R4 · Performance, measured again by me

Same script and method as the first run: one rolled-back transaction on `test_site`, 1,000 people,
257,000 attendance rows, 117,846 check-ins, 30 warm and 30 cold calls per scope. "Cold" clears the
whole site cache, which is harsher than any real first call.

| Scope | `get_hr_analytics` warm p95 | before | `data_review_items` warm p95 | before |
|---|---|---|---|---|
| Company | **283 ms** | 761 ms | **243 ms** | 536 ms |
| One branch | **66 ms** | 447 ms | **36 ms** | 456 ms |
| Two branches | **100 ms** | 544 ms | **60 ms** | 554 ms |
| Set with the 4-person branch | **68 ms** | 895 ms | **40 ms** | 433 ms |
| Morning job, one company | **675 ms** | 5,082 ms | — | — |

**Every warm call is now inside the 500 ms budget at 1,000 people** — the worst is 283 ms, against
895 ms before. My numbers are a little better than the engineer's (they reported 359 ms and 409 ms
for company scope). Same ballpark, both under budget, so their claim stands.

Cold (whole-cache-flush) calls are 564–672 ms, down from 1,116–1,638 ms. Still over 500 ms, but that
path only happens after a cache flush or a restart, and most of it is Frappe reloading its own
metadata rather than this slice's queries.

**`EXPLAIN` after the fix: no full scan of Attendance or Employee Checkin anywhere** — not in
`get_hr_analytics`, `data_review_items` or the morning job, at company or at branch scope. AC-3's
`EXPLAIN` condition is met for those two tables. What still reads whole tables is small: Employee
(1,077 rows), Leave Allocation (1,015) and Leave Application (2,051). **Watch item, not a defect:**
the two leave tables grow with headcount and have no (`company`, `from_date`) index, so they are the
next thing to bite well above this size.

## R5 · The query change lost nothing (point 4)

| Question | Answer |
|---|---|
| Does HR Analytics show late arrivals, short days or "people inside the figure"? | **No.** The screen's own labels are: Active Employees, New Joiners, Attendance Rate, Pending Approvals, Confirmations Due, Leave Utilisation, Days Present, Days Absent, and the four distributions. None of them comes from the three dropped columns |
| Do the cheap and the full query agree on what is shown? | **Yes** — probe: present, work from home, half day, absent, on leave and the rate are identical |
| Do "Days Present" and "Days Absent" still come from the same counts? | Yes: `present + wfh + half/2` and `absent`, both still selected |
| Does the full calculation still exist for push 2? | **Yes.** `attendance_figures` keeps `detail=True` as its default, and the probe confirms it still returns late, short and the distinct people count (the small-group rule needs that count). `test_org_figures_012.test_late_arrivals_and_short_days` calls it with the default and asserts late = 1 and short = 1; it passed in the whole-suite run |
| Any other caller affected? | No. Only two callers pass `detail=False`: `get_hr_analytics` and `data_review._figures_for_confirming` (which shows a percentage only). Attendance Insights keeps its own separate formula (BA-Q4), untouched |
| Risk taken | Until push 2 there is no caller using `detail=True`, so only tests keep that branch alive. Those tests exist, so rot would fail CI |
| Does the "data up to" change cost anything? | It now runs one small indexed read **per company in scope** instead of one MAX over all of them. For a tenant (1–2 companies) that is 1–2 queries. For a System Manager over our test site's 20+ companies it is 20+ tiny queries — still fixed with respect to people and branches, so AC-4 holds, but worth remembering if a tenant ever has many companies |

## R6 · Still not run (unchanged from the first report)

- **No browser run.** `ppj.localhost` is still not migrated for 012, and the dev server serves only
  that site. 360 px, 200% zoom, keyboard focus and the desk links are still unverified by eye.
- **2,000 employees, separate synthetic sites, and the index-migrate timing (AC-5).** The new ninth
  index (Attendance, company + date) makes that timing more relevant, not less: it is built on a
  table with 200,000+ rows on a real tenant.
- **A real two-connection race on one confirmation.**

## R7 · Board and bench state left

The bench is idle and my claim on `.claude/work-in-progress.md` is cleared. Local `dev` and
`slice/012-leadership-view` are both at 5aad1ae; I added no commits this round (the probes are
scratchpad scripts, and nothing they created survived the rollback). Nothing pushed, nothing
deployed.

---

# Final verification after fix rounds 2 and 3 (2026-09-17)

**Code tested:** local `dev` **2db1d71** = `slice/012-leadership-view` (worktree clean). It holds 012 fix
rounds 1–3 and all of slice 010 group D. `origin/dev` is still c27fb56 — nothing pushed. New since the
round-1 re-test: c78efcd (DEF-8), acbcaa5 (M1 read limit), 0fd66bd and 2db1d71 (F3, F4).

**A note on the run itself.** A first attempt on 2026-09-16 at 18:45 was cut off when the PC and Docker
Desktop stopped; its first batch had finished (540 tests, the 3 known errors) but the run never
completed, so **I do not count it**. Everything below comes from the complete run started 2026-09-17
at 20:20, after the containers were back and MariaDB answered a query. I wrote a progress line on the
work board after each suite finished.

## V1 · Whole suites

| Run | Result |
|---|---|
| `bench --site test_site run-tests --app alvoraa_portal` | **1,073 tests** (540 + 533), about 34 min. **1 failure, 13 errors, 4 skipped** |
| `bench --site test_site run-tests --app alvoraa_goals` | **18 OK** (2 skipped) |

**Against the baseline:** 1,065 tests at the round-1 re-test, 1,073 now — **8 more**, which is the tests
rounds 2 and 3 added. The failures are **exactly the known 14, and nothing else**:

| Test | Result | Class | Evidence |
|---|---|---|---|
| `test_leave_year.TestLeaveYearStart` × 3 | ERROR | **Pre-existing** | "Year start date or end date is overlapping with Fiscal Year _Test Fiscal Year 2025" — test-site fiscal-year data, same as 2026-09-14 and both earlier runs |
| `test_invoicing` × 11 (10 errors + `test_running_the_job_again_skips_a_month_already_invoiced` failure) | ERROR / FAIL | **Pre-existing** | "There is more than one company on this site, so the invoice has no obvious sender" — `test_site` has 25 companies |
| — | — | **Nothing caused by 012, nothing by 010, nothing flaky** | The same 14 appeared in all three complete runs. DEF-1's test (`test_every_billing_doctype_is_named_as_control_plane_only`) passes (log line 280) |

## V2 · Rounds 2 and 3, checked independently

All in scripts run in the bench's Python against `test_site`, commits turned off, rolled back at the end
(`probe_r3.py`, `probe_cap120.py`). Plus two HTTP calls to the local dev server (below).

**DEF-8 — store HR and no-branch colleagues (c78efcd)**

| Route | Result |
|---|---|
| Organisation list, no filter | **no-branch colleague absent**, other branch absent, own branch present (3 rows) |
| Organisation list asking for another branch (`branch=` another store) | **refused**, one security line with rule `SEC-17` |
| Organisation list asking for their own branch | works |
| Organisation list naming a no-branch person (`people=[…]`) | **refused** |
| Organisation list naming another branch's person | **refused** |
| `person()` for a no-branch colleague | **refused** |
| `filter_options()` | lists only their own branch |
| HR Analytics | no-branch and other-branch people absent |

I found no remaining route in the portal's attendance and analytics calls.

**Slice 011's pinned tests still mean what they meant.** `test_branch_scope.py` has **not been edited by
any 012 commit** (its last commits are 011's own, 411536c and e8f70c9). Its three portal tests use
employees who **have** a branch, and its central HR and System Manager users hold **no Branch
permission** — the one case where `_linked_branches()` returns None and nothing changes. All three pass
in the final run (log lines 1407–1411). My probe repeated their subjects with new users:

| Subject | Result |
|---|---|
| Central HR (Company permission, no Branch permission) | still sees every store **and** no-branch staff |
| System Manager alone | still sees every store |
| Store HR | sees their store; now also never sees no-branch staff — stricter, same assertions still true |

**M1 — the read limit (acbcaa5)**

| Check | Result |
|---|---|
| At the **real** cap of 120 an hour, one store HR user | calls 1–120 succeed, **call 121 refused** with "too many requests" |
| With the cap set to 3, then a second HR user in the same process (same machine, same IP) | first user refused on call 4; **the second user is not blocked** — the count is per user |
| Confirmations | their own separate cap, 30 an hour, unchanged |

**F3, F4 — HR Analytics (0fd66bd, 2db1d71)**

| Check | Result |
|---|---|
| Allowed HTTP methods | `["POST"]` |
| **Real HTTP GET, logged in** (local dev server, Administrator) | **403**, refused in Frappe's `handler.is_valid_http_method` — before the function runs. A control GET to `frappe.auth.get_logged_user` in the same session returned 200. I did not POST there, because `ppj.localhost` is not migrated for 012 |
| `Cache-Control` after a call | `no-store` |
| `gender` on any named person (recent joiners, confirmations due) | **absent** on all 6 returned |
| Gender ratio card | still has its counts |
| Does the page still work with POST only? | Yes by reading: HR Analytics loads through `api()` → `frappe.call`, which posts |

**Deferred findings, checked so the record is honest**

| Finding | Still open? |
|---|---|
| F1 `set_cover_setting` | **Yes** — still allows HR Manager, still writes no record |
| F2 location HR reading company-wide review records through `get_list` / REST | **Yes** — store HR can still read one |

## V3 · Not run

- **Browser pass**: 360 px, 200% zoom, keyboard through the confirm dialog, the desk links from the cards.
  `ppj.localhost` is still not migrated for 012 and the dev server serves only that site.
- **2,000 employees, separate synthetic sites, and the index-migrate timing (AC-5)** — the ninth index
  (Attendance, company + date) is built on a table of 200,000+ rows on a real tenant.
- **A real two-connection race** on one confirmation.
- I did not re-run the 1,000-person timing after rounds 2 and 3. Round 2 adds one branch filter to the
  organisation list and round 3 adds one cache counter and one header; neither touches the queries I
  timed, so the round-1 re-test numbers (all warm p95 ≤ 283 ms) still stand. That is a judgement, not a
  measurement.

## V4 · Board and bench left

My claim on `.claude/work-in-progress.md` is cleared and the bench is idle (`pgrep` empty). I added no
commits in this run; the probes are scratchpad scripts and everything they created was rolled back. I
logged in and out of the local dev server once, for the GET check. Nothing pushed, nothing deployed, no
`docker cp`.
