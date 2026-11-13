# ALV-328 - Implementation notes

Written as the build goes, so nothing is lost if a run stops.

## Status log
- 12 Nov 2026, later: code written in all 9 files; two new test files; fresh-site
  bootstrap took three rounds (below). Not committed yet - waiting for green.
- 12 Nov 2026: strategy approved (D1 no, D2 no change, D3 accepted). Work-board row added.
  `origin/dev` fetched: nothing new since `75149184`.

## What was built, file by file

| File | Change | Rung / mechanism |
|---|---|---|
| `payroll_rules.py` | New `punch_minutes` (drop seconds, fold repeats) and `minutes_on_break` (the one break sum). `_worked_percent` now calls `minutes_on_break` | edit existing code |
| `payroll_rules_apply.py` | `_punches` calls `punch_minutes`. New `breaks_by_day(employee, company, days, times_by_date)` for the two screens: rule set, `prepare` and `_employee_flags` once, then a loop in memory | edit existing code |
| `day_marks.py` | `_break_over` calls `minutes_on_break` (AC-17: one copy of the sum) | one line |
| `attendance_correction.py` | `month()`: two more fields on the existing Attendance `get_list`; times grouped by calendar date in the existing Checkin loop; `breaks_by_day` merged into the days; month-level `break_allowance_minutes` only when a day has a break. `_day()`: `rules_why`, `evaluated_on` only when set | edit existing code |
| `attendance_analytics.py` | `person()`: one Checkin `get_list` for the range; `breaks_by_day`; `company` added to the existing Employee name read | edit existing code |
| `field_app_access.py` | `WHOLE_LINE_SETTING`, `whole_line_on()` (fail closed), `_line_sql()` (one SQL text: direct, or recursive whole Active line). `checkin_query_conditions` uses it; `checkin_has_permission` is read-only outside HR (ALV-332/333), own new punch may be created, machine create unchanged | permission layer, edit existing hooks |
| `field_app_settings.py` | The Check field added to the existing `after_migrate` list (already in `after_migrate` and `after_install`). `_refuse_whole_line_change` at the top of `validate_hr_settings`: System Manager only | Custom Field + existing validate hook |
| `public/js/ess/portal.js` | `acBreak`, `acShowBreak`; `acPaint` header; `acRow` phone item and desktop cell; `acDetail` colspan, Break and Allowed tiles, not-measured help, "Why this day" section; `aiPerson` Break column, table wrapped in `.tbl-wrap` | edit existing screens |
| `public/css/ess/panels.css` | `.ac-brk` nowrap, `.ac-why*` (pre-line text) | a few lines |
| `tests/test_break_and_reason_alv328.py` | new | pin test for ALV-328 |
| `tests/test_punch_rights_alv332.py` | new | pin test for ALV-332, ALV-333 and the switch |

Not touched: `hooks.py`, `patches.txt`, any DocType JSON, `apps/frappe`, `apps/hrms` upstream code.

## Test environment

Own throwaway containers only: `hrlocal-328` (image `ghcr.io/.../alvoraa-app:dev-d3afcaa`,
`alvoraa_portal`, `alvoraa_goals`, `hrms` mounted from this worktree), `hrlocal-328-db`
(mariadb:10.8), `hrlocal-328-redis`, network `hrlocal-328`, volume `hrlocal-328-sites`.
Fresh site `test328`, built like CI (`new-site`, then `install-app` erpnext, hrms,
alvoraa_portal, alvoraa_goals; `allow_tests`). No migrate was run: the field comes from
`after_install`. The shared bench `hrlocal-bench` was not touched, except read-only source
reads and one read-only SELECT during step 1.
## Commands and real output

1. `scripts/check_app_integrity.py`: "app integrity: 922 checks, OK - all consistent"
   (no bench, so the doctype-shadowing part skipped).
2. `ruff check` on the 7 changed Python files and 2 new tests: 1 finding, E741 `l` at
   `attendance_correction.py:579`. **Not mine** (an existing loop over leaves); left alone.
3. `node --check portal.js`: OK.
4. Fresh-site trouble, three rounds (recorded so the next person does not lose an hour):
   - Round 1: built while I was still editing. Rebuilt.
   - Round 2: the first test run failed in `setUpModule`: "Could not find Warehouse Type:
     Transit" and "Could not find Gender: Male". A bare `new-site` + `install-app` has no
     setup-wizard data, and `bench run-tests --app alvoraa_portal` runs only
     alvoraa_portal's `before_tests` hooks (it has none), not hrms's.
   - Round 2b: running the setup wizard (or hrms `before_tests`) **after** alvoraa_portal is
     installed fails: "'Alvoraa Joiner' cannot be given to an account here" - the wizard
     gives Administrator every role, and the joiner guard refuses it. **Pre-existing, not
     this slice**; worth a ticket if a new tenant is ever set up through the wizard after
     install.
   - Round 3: `new-site`, install erpnext and hrms, run `setup_complete`, then install
     alvoraa_portal and alvoraa_goals.
   - Tests now create a Gender when none exists (the pattern `test_alv291_attendance_fix`
     already uses).
5. New modules on the bootstrapped fresh site `test328`:
   - `test_punch_rights_alv332`: **Ran 17, OK** (after one fix: Frappe writes no Version
     row while tests run unless `save(ignore_version=False)`, the same way
     `home_people` does it).
   - `test_break_and_reason_alv328`: two batches, **Ran 2, OK** and **Ran 16, OK** (after
     one fix: `frappe.client.get_value` returns `{}` for a colleague's row, not an error;
     the test now asserts "nothing", not "refused").
   - Total 35 new tests, all green.

## AC coverage

| AC | Test | Status |
|---|---|---|
| AC-1, 3, 7, 11, 12, 14, 15 | `test_alv328_the_days_the_spec_names` | green |
| AC-2, 6, 18, 19, 21, 22 (screen) | traced by hand in `portal.js`; no browser run | **not run in a browser** |
| AC-4 (leave), night shift | `test_alv328_leave_and_night_shifts_get_no_break` | green |
| AC-5 | `test_alv328_no_break_without_a_break_rule` | green |
| AC-8, 9, 10 | not tested separately (over-hour words are JS; category override uses `_employee_flags`, tested by ALV-326) | gap, small |
| AC-13 | `test_alv328_the_break_shown_is_the_break_the_pay_rules_counted` (engine runs on submit, figures compared) | green |
| AC-16 | `test_alv328_seconds_are_dropped_before_counting` | green |
| AC-17 | review: one `minutes_on_break`, called by engine, banner, screens; `collapse_duplicate_punches` defined once | done |
| AC-17a | `test_alv328_a_punch_after_midnight_counts_on_its_own_date` | green |
| AC-19, 20 | `test_alv328_the_reason_and_when_it_was_worked_out` | green (server side) |
| AC-23 | design S8; no special code | nothing to test |
| AC-24 | `test_alv328_the_direct_manager_sees_what_the_person_sees` | green |
| AC-25, 26 | `test_alv328_a_skip_level_manager_gets_no_break_by_default` | green |
| AC-27 | `test_alv328_off_a_manager_sees_direct_reports_only` | green |
| AC-28 | `test_alv328_the_field_is_there_and_off_on_a_fresh_site` (field came from `after_install`) | green |
| AC-29 | `test_alv328_a_system_manager_may_flip_it_and_it_is_recorded` | green |
| AC-30, 34 | `test_alv328_with_the_switch_on_the_skip_level_manager_sees_it`, `..._off_again_on_the_very_next_request` | green |
| AC-31, 32, SEC-8 | `test_alv328_on_the_whole_active_line_and_still_read_only` | green |
| SEC-6 | `test_alv328_the_list_and_the_single_record_agree` (4 users, switch off and on, record by record) | green |
| AC-33, PRIV-4 | `test_alv328_an_unreadable_switch_counts_as_off` | green |
| AC-35, SEC-11 | `log_photo_view` unchanged; no new test | gap (unchanged code) |
| AC-36, SEC-9 | `test_alv328_hr_manager_is_refused_on_every_door` (Desk save, `client.save`, `client.set_value`) + `..._may_still_save_other_settings` | green |
| AC-37, 38 | `test_alv328_hr_sees_the_same_break_on_insights_and_no_reason` | green |
| AC-40, PRIV-1 | `test_alv328_no_break_on_any_group_view` | green |
| AC-41 | `test_alv328_a_colleague_is_refused_and_gets_nothing` | green |
| AC-42, SEC-4 | `test_alv328_frappe_doors_keep_a_colleague_out_of_the_reason` with negative control | green |
| AC-43 | no new `ignore_permissions`; ceiling test in the full run | see full run |
| AC-44, PRIV-2 | review: one Custom Field, no write of break values | done |
| AC-45, PRIV-3 | review: no new log or throw carries a break or a reason | done |
| AC-46, 47 | `QueryCounts` (same count; exactly one Checkin read) | green |
| AC-48 | `test_alv328_no_key_is_sent_empty` | green |
| ALV-332 | `test_alv332_*` (manager read-only, REST-equivalent doors refuse, negative control, no punch for a report, HR keeps all, colleague nothing) | green |
| ALV-333 | `test_alv333_*` (own punch read-only, own new punch still allowed) | green |

## Non-functional re-check (against the code written)

| Dimension | Before | After | Verdict |
|---|---|---|---|
| Performance | `month()` 1 Checkin read; `person()` none | `month()` same 1 Checkin read + a constant handful for the rule set (only when there are punches); `person()` 1 Checkin read + the same handful. Test proves the count does not grow with punches or months | neutral |
| Security | Any manager or person could edit or delete punches through the API | Outside HR read-only; own new punch only; machine create unchanged; no new endpoint, no new `ignore_permissions`. One parameterised `frappe.db.sql` in `checkin_has_permission` (the rule itself, reading Employee names) | improves |
| Reliability | - | No rule set, no shift, unreadable switch: no break, no error | neutral |
| Scalability | Direct reports read into Python as an ID list | The line stays in SQL (one statement), as nfr-budget §2 asks | improves |
| Maintainability | Three copies of the break sum | One `minutes_on_break`; one SQL text for both punch hooks | improves |
| Data integrity | Punches changeable by many | Only HR changes or deletes a punch; nothing new stored, no cache | improves |
| Compliance / privacy | Reason not on any screen | Person sees their own break and reason; no break on group views; switch off by default, System Manager only, Version history | improves |
## Non-functional re-check (against the code written)
## What else moved while I worked
## Known gaps and shortcuts

- **No browser run of the two screens** (AC-2, 6, 21 on screen, 360 px). The JS was traced
  by hand and `node --check` passed. *Temporary debt*: removed by one browser pass on my
  own stack before the dev push.
- **Hindi not shipped** (Q-C, agreed difference): the new words go through `drT`; no
  translation rows added.
- **Photo-log gap with the switch on** (SEC-11, R3): unchanged code, accepted by Surbhi.
  *Intentional trade-off*.
- **Count E on DTC: 0** (D1 condition, run 12 Nov 2026, recorded in 05-impact-and-strategy):
  nobody outside HR added punches for others in the last 120 days.
- **Before main: count punch shares on DTC** (security review R5). A share with write lets
  someone outside HR edit a punch. Read-only script `step32-punch-shares-readonly.py`.
- **Browser pass, 13 Nov 2026** on hrlocal-328 with made-up people: both screens drawn, every
  break figure as the spec, "Why this day" and "Worked out on" shown, no script errors. Phone
  widths (360 / 390 px) not checked.
- **Pre-existing, not touched:** ruff E741 at `attendance_correction.py:579`; the setup
  wizard cannot run after alvoraa_portal is installed (joiner guard). Worth a ticket.
- Desk still shows a Save button to a manager on a report's punch; the server refuses.
  *Acceptable simplification* (K5).
## Subtract pass

Read the diff once more for what can go:
- Removed a separate pure "day state" helper; the state rules live once in `breaks_by_day`.
- Kept `punch_minutes`: without it the "drop seconds" rule would be written twice.
- Kept the `if not any(times_by_date.values())` early return: it is what keeps a skip-level
  manager's call from reading the rule set at all.
- No `hooks.py` change, no new section break on HR Settings, no new endpoint.
Nothing further removed on this pass.
