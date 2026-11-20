---
slice: 084-employee-regularisation-window
artifact: 04-test-report
author: hrms-test-automation-engineer
date: 2026-11-19
tier: 1
code under test: worktree /Users/mac/hr-app/.claude/worktrees/084-employee-window, branch slice/084-employee-window, HEAD c162374b (cut from fd658eff)
---

# 084 Test report

## Verdict: PASS WITH KNOWN GAPS. No P0 or P1 finding.

Bad news first:

1. **The full `alvoraa_portal` suite did NOT finish.** I started `bench run-tests --app alvoraa_portal` (4,433 test methods in 218 files). After about 70 minutes it had passed about 1,006 tests and was only at `test_attendance_correction`, with roughly 3,400 still to go. I stopped it. **No full-suite result is claimed.** I then ran the changed modules and their direct neighbours one by one (section 3). CI must run the full suite.
2. **Five modules errored in `setUpModule`/`setUpClass` in that partial run** (`test_leave_credit_rows_063`, `test_notices_076`, `test_late_minutes_017`, `test_grooming_066`, `test_daily_workings_alv358`). I re-ran one (063): it fails with a Fiscal Year overlap in `setUpModule` ("Year start date or end date is overlapping with Fiscal Year 2026"). That is site state from `hrms.tests.test_utils.before_tests` (which creates a calendar-year fiscal year) and nothing in this slice. **The other four were not diagnosed.** [ASSUMPTION: same cause.]
3. **Pre-existing fixture that differs from the real tenant (loud).** `CorrectionCase.person()` in `test_attendance_correction.py` gives every test employee a Shift Assignment, with the comment "Real employees have one". DTC employees do not. The engineer's 30 new tests sit on it. Because of this I wrote my own fixtures with **no Shift Assignment**; the same behaviours pass there (section 2). Not caused by this slice. P2 test debt, owner: whoever owns that file.
4. **No browser, phone, screen reader or 200%-text check was run.** The page journeys were traced through the jsdom test and the code only.

## 1. Where this ran

- **My own stack, built by me, nothing shared:** containers `t084-bench`, `t084-db`, `t084-redis`, network `t084net`, volume `t084-sites`. Image `ghcr.io/surbhigoyal7381-agent/hr-app:dev-3830ed3`. The slice's `alvoraa_portal`, `hrms`, `alvoraa_goals` folders from the worktree are mounted in. I did not use `hrlocal-bench` or the engineer's `alv084-*` stack.
- **Site `test_site`, built fresh**: `bench new-site`, then erpnext, hrms, alvoraa_portal, alvoraa_goals (the way `ci.yml` does). Schema came from the slice branch code. `developer_mode` off (production-like hook cache).
- **Hand steps I had to do on the fresh site:** `hrms.tests.test_utils.before_tests` creates `_Test Company` then stops with a ValidationError (the "Alvoraa Joiner" role guard on `add_all_roles_to`); and I created two Genders (`Male`, `Female`). Same two hand steps the engineer named (ALV-335). Not slice-related.
- **`alvoraa_goals` WAS installed on my site**, so `test_portal_security_010` ran cleanly, unlike the engineer's.
- Nothing pushed, nothing committed, no deploy command, no `clear-cache`/`migrate`/`build` on any shared thing. The new test file below is **untracked** in the worktree.

## 2. What I wrote

`/Users/mac/hr-app/.claude/worktrees/084-employee-window/alvoraa_portal/alvoraa_portal/tests/test_employee_window_084_independent.py`, untracked. 18 tests. Own fixtures: a holiday list with no weekly offs (so a window of N is exactly N calendar days on any weekday), no Shift Assignment, unique users per test. It drives **four ways in**: `raise_correction` (a), `submit_attendance_request` (b), `frappe.get_doc(...).insert()` as the employee (c), and `frappe.client.insert` (d, what `/api/resource` POST calls). Keep it or delete it; it overlaps the engineer's class on purpose, because the brief asked for independent proof.

## 3. Commands and numbers (all run by me, today, on the site above)

| Command (inside `t084-bench`, `cd /home/frappe/frappe-bench`) | Result |
|---|---|
| `CI=true bench --site test_site run-tests --app alvoraa_portal --module alvoraa_portal.tests.test_attendance_correction` | batch 1 **Ran 148, OK** (393 s); batch 2 **Ran 19, OK**. Contains the engineer's `TheEmployeesFilingWindow` (30) beside the manager's 25 |
| `... --module alvoraa_portal.tests.test_employee_window_084_independent` | **Ran 18, OK** (60 s) |
| `... --module alvoraa_portal.tests.test_org_setting_scope_030` | **Ran 6, OK** (one batch printed) |
| `... --module alvoraa_portal.tests.test_org_settings_allowlist_012` | **Ran 10, OK** (one batch printed) |
| `... --module alvoraa_portal.tests.test_portal_security_010` | batch 1 **Ran 45, OK**; batch 2 **Ran 5, OK**. Holds the `ignore_permissions` ceiling test. This is the file the engineer could not run |
| `... --module alvoraa_portal.tests.test_leave_credit_rows_063` | **Ran 0, errors=1** in both batches: Fiscal Year overlap in `setUpModule`. Site state, not this slice (item 2 above) |
| `... run-tests --app alvoraa_portal` (everything) | **Did not finish; stopped by me.** About 1,006 passed marks, 8 setUp errors, reached `test_attendance_correction` |
| `NODE_PATH=/Users/mac/hr-app/node_modules node alvoraa_portal/tests/portal_correction_test.js` | **57 passed, 0 failed** |
| `node --check .../public/js/ess/portal.js` | OK |
| `python3 scripts/check_app_integrity.py` | 952 checks OK (no bench, so the shadowing check is skipped) |

I read the "Ran" lines of both batches in each log. Not run: `test_scale_flatness_044`, the other ~210 files, any browser.

## 4. The four things you asked me to prove

Method: break the code **in process** (a script piped on standard input; no repo file edited), run the named tests, watch them fail, then run a control with no break. Control run (no break) of five of the tests: 5 run, 0 failures.

| # | Break (in process) | Tests run | Result |
|---|---|---|---|
| 1. AC-12 | Hook moved from `validate` to `before_insert` (doc-hook table patched) | my two edit-path tests, my three-ways test, engineer's `test_moving_a_draft_back_...`, engineer's `test_the_hook_is_registered_on_validate` | **3 fail, 2 pass.** Fail: my `test_AC12_editing_a_draft_back_to_an_old_day_is_refused` (via `doc.save()` and `frappe.client.set_value`), my `test_AC12_moving_to_date_back_alone_...`, engineer's `test_moving_a_draft_back_...`. The three insert tests still pass, as they should (before_insert still catches creation). The registration pin test passes under this break only because I patched the doc-hook table and not `get_hooks`; **moving the line in `hooks.py` would trip it (inference, not run by me)** |
| 2. Blank trap | `set_org_setting` condition narrowed to `key == MANAGER_FILING_WINDOW_KEY` only | my AC-7, my zero-save test, engineer's `test_hr_can_set_a_number_and_can_clear_it_again` | **3 of 3 fail** with `PermissionError: This setting cannot be read or changed here.` on saving `""`, the right reason |
| 3a. Joining day | Exception removed (joining date treated as blank) | my AC-15..17 test, engineer's joining test | **2 of 2 fail**: the joining day alone is refused |
| 3b. Joining day | A range from the joining day is treated as allowed | same two | **2 of 2 fail**: the range is let through |
| 4a. Blank costs nothing | Hook reads `Employee` before checking the setting | my AC-21 test, engineer's `test_blank_costs_no_holiday_or_employee_read_...` | **2 of 2 fail** (a `tabEmployee` read appears) |
| 4b. Guard does nothing | Hook replaced by a no-op | my three-ways test, my HR-own-day test, my zero-means-today test | **3 of 3 fail** |
| extra | Blank read as zero | my AC-60, AC-7, engineer's `..._keep_blank_and_zero_apart` | **3 fail** (2 failures, 1 error) |
| extra | Hook binds every record, not only the caller's own | my AC-26, engineer's `test_hr_is_bound_on_their_own_day_and_free_for_everybody_elses` | **2 of 2 error**: HR's old day for someone else is wrongly refused |

**Point 1, the three ways in, with no break:** on my fixtures every old day (8 days back, window 3) is refused by all four routes with our own sentence (it names Mon boundary date, "older than your organisation lets you raise yourself", "tell HR which day it was and why") and **leaves no row**. The boundary day is accepted and the day before refused on all four. The edit path (create today, then move `from_date` back) is refused through `save()` and `frappe.client.set_value`, and the stored date does not move. Moving both dates (from old, to today) is refused. Route (b) uses `ignore_permissions=True` and is still refused.

**Point 4, blank means zero cost, with no break:** with the setting blank the hook makes **0 statements** (spy on `frappe.db.sql`, one warm-up read first); with a limit set and only the explanation edited it also makes **0**; with blank, a 365-day-old day goes through on all four routes for an employee and for an HR Manager's own day. Stored `0` is "today only", not blank (yesterday refused on all four, today accepted).

## 5. Coverage: acceptance criteria

"Mine" = `test_employee_window_084_independent.py`. "Eng" = engineer's class `TheEmployeesFilingWindow` (Eng tests ran green inside the 148). All listed tests passed.

| AC | Proof | Note |
|---|---|---|
| 1, 2 | Mine `test_AC2_bad_values...`; Eng `test_hr_can_set_a_number_and_can_clear_it_again` | Mine checks all six bad values and 0, 30 |
| 3 | **Read by me** (label, input `min=0 max=30`, placeholder, `aria-describedby`, row sits before `org-on-behalf-on` and outside `org-filing-window-field`) | **No automated test** of the exact words. Hint carries Surbhi's approved reword ("does not limit what HR does for other people") |
| 4 | Read: `orgApply` never touches the new box | not run in a browser |
| 5 | Mine `test_the_zero_save_returns_the_server_date...` (0 returns `{"ok": True, "today": ...}`, others `{"ok": True}`) | save line for 1 or more names no date: approved departure; wording not test-checked |
| 6 | read only | not run |
| 7, 8 | Mine AC-7, `test_a_zero_is_not_blank_today_only`; Eng | break-tested (section 4) |
| 9, 10, 11 | Mine `test_AC9_to_11...` (four routes); Eng | |
| 12 | Mine two edit-path tests; Eng | **break-tested**: fails on `before_insert` |
| 13, 14 | Mine boundary test; Eng range test | |
| 15, 16, 17 | Mine `test_AC15_to_17...` (alone, whole range, day after, day before); Eng | break-tested both ways |
| 18 | Mine `test_AC18...`; Eng | |
| 19 | Eng `test_whatever_the_caller_sends_the_joining_date_comes_from_the_employee` | |
| 20 | Eng `test_a_leaver_is_refused_before_the_window_is_asked` | |
| 21 | Mine two zero-statement tests; Eng | break-tested |
| 22, 23, 24 | Eng zero / holiday push-back / no-holiday-list / future-end tests | my fixtures use no weekly offs, so holiday push-back is the engineer's alone |
| 25 | Eng `test_editing_only_the_explanation_of_an_old_draft_still_works`; mine AC-21 second test | |
| 26 | Mine `test_AC26...`; Eng | break-tested ("binds everyone") |
| 27 | Eng `test_the_screens_and_the_refusal_name_the_same_day` | |
| 28, 29 | Mine `test_PRIV2_PRIV4_PRIV6...` (no `log_refusal`, no `log_error`; no employee id, name, email, list name or company in any of the four sentences); Eng | The "no digit before day or hour" part is **not a test** (read by eye) |
| 30, 31 | Eng month-payload tests | |
| 32, 33, 34, 36 | jsdom test (57 pass) | |
| 35 | **Gap.** Sheet's own refusal box: built, **no DOM test** | P3 |
| 37, 38, 39, 40, 41, 42 | Eng `test_the_request_page_is_told...`; jsdom test | |
| 43 | accepted behaviour, no test | |
| 44, 69 | `scripts` counts I ran: `@frappe.whitelist` 10 and 69, `ignore_permissions` 4 and 71, **identical to `fd658eff`**; `test_portal_security_010` ceiling test OK | |
| **45, 46, 47** | **NOT BUILT, BY DECISION** (SEC-12 log line, ALV-391, awaits Surbhi) | not reported as defects |
| 48, 49 | `git show --stat b1d57b0a` lists `org-settings.html`, `attendance_correction.py`, `portal.js`, `hr_api.py`; the 12-row `02a` | |
| 50 | I re-ran the grep over `alvoraa_portal` and `hrms/hrms`: no remaining sentence says an employee's own day is unlimited. Matches left are unrelated sentences or true ones. DTC manual and Desk help **not searched** | floor, not total |
| 51 | read | |
| 52, 53, 54 | Eng; mine AC-26 (HR free for others) | |
| 55 | Mine `test_PRIV3_...` (a real manager reading a report's month gets no `joined_on`, no `own_window`) | |
| 56 | `test_org_setting_scope_030` 6 OK (includes the new store-HR test) | |
| 57, 58 | `test_org_settings_allowlist_012` 10 OK; Eng plain-employee test | |
| 59 | deleted by Surbhi | |
| 60 | Mine `test_AC60...` (blank changes nothing for anyone on any route) | not checked on a live tenant |
| 61, 62, 63, 66, 67 | release steps and human gates, **not run** | |
| 64 | `git diff --stat fd658eff`: no deploy, Dockerfile, workflow, requirements, patch or DocType file | |
| 65 | integrity script 952 OK | |
| 68 | Eng test (same statements with 300 more holiday rows). Mine, measured: month **17 statements blank, 19 with a limit**; history **5 vs 7** | not 500 rows (Frappe refuses a holiday date twice) |
| 70 | Eng `test_the_boundary_is_not_in_the_portal_context` | |
| 71 | section 4 | |
| 72, 73 | Read: `<label>`, `aria-describedby`, `role="status"`, `role="alert"` present; strings go through `drT` with the date as an argument. **No automated check of glued dates.** **Sheet is not a `role="dialog"`**: parity gap below | |

## 6. SEC / PRIV / OPS

| Item | Test | |
|---|---|---|
| SEC-1, 3 | three-ways + edit path, break-tested | proven |
| SEC-2 | Eng same-date test; no day/hour numbers in strings (by eye) | partly automated |
| SEC-4, 5, 6, 10 | Eng + mine | proven |
| SEC-7 | HR free for others, bound on own; two windows never read each other (Eng) | proven |
| SEC-8 | `test_org_setting_scope_030`, Eng plain-employee test | proven |
| SEC-9 | mine AC-2, AC-7 | proven |
| SEC-11 | counts equal; ceiling test OK | proven |
| **SEC-12** | **not built by decision (ALV-391)**. Untested control | |
| SEC-13 | Eng calendar-day fallback test | |
| PRIV-1 | diff has no new field/DocType | |
| PRIV-2, 4, 5, 6 | mine PRIV test | proven for the four routes |
| PRIV-3 | mine + Eng | proven for a direct manager. A skip-level reader was not separately run by me |
| PRIV-7 | statement, no test | |
| OPS-1, 2, 6, 7 | statement counts above | assertion is the property (flat with holiday rows), plus my numbers |
| OPS-5 | blank vs 0 | proven |
| OPS-9, 10 | Eng + mine | proven |
| OPS-12, 15, 16, 17, 18, 19, 20, 22, 24, 25, 26, 27, 28, 30 | release or human steps | **untested controls**; none are mine to run |
| OPS-21 (hook cache) | developer_mode **off** on my site; my 18 tests and the 148 ran on it | partly: I did not test a rollback |

## 7. NFR numbers (measured by me, one fresh site, tiny volume)

Median of 5 warm runs, same process. The 500 ms budget is met by a wide margin, **at three-row volume only; not a scale claim.**

| Path | Blank | Limit 3 |
|---|---|---|
| `month()` own month | 16.8 ms, 17 statements | 16.7 ms, 19 statements |
| `get_requests_history()` | 2.8 ms, 5 statements | 4.5 ms, 7 statements |
| a refused request (insert, limit 3) | not applicable | 10.5 ms |
| hook with blank / unchanged dates | 0 statements | 0 statements |

## 8. Extra cases beyond the ACs

- Edit path by `frappe.client.set_value`, not just `save()`.
- Route (d): `frappe.client.insert` (what a REST POST calls). `insert_many` also refuses an old day.
- A missing `from_date` is still an error, not a pass. A garbage date string gives a clean `ValidationError` ("is not a valid date string"), not a crash.
- A day **before** the joining day gets no exception.
- A peer filing for someone else's old day: **refused with `PermissionError`** on my fresh site with no User Permissions. One probe, not a test. This does not prove ALV-387 is closed on a real tenant.
- HR Manager with an Employee record: bound on own day on routes c and d, free for another employee's year-old day.

## 9. Defects and risks

| # | Sev | What |
|---|---|---|
| 1 | P2 | Full `alvoraa_portal` suite not run to the end by me. CI (the split `run-parallel-tests`) is the proof that nothing else broke |
| 2 | P2 | Fixture with a Shift Assignment (item 3 at the top) |
| 3 | P3 | AC-35 (sheet-side refusal box) has no DOM test |
| 4 | P3 | AC-3 / AC-5 exact words and AC-72/73 (no glued dates) have no automated test; AC-29(iii) digit rule is by eye |
| 5 | P4 | `arWindowNote()` decides "today only" by comparing the server date to the **browser's** date (`localToday()`). A phone clock a day off would show the "days from ... onwards" wording for limit 0. Wording only; the server still refuses correctly |
| 6 | P3 | Five modules error at setup on a freshly built site (item 2 at the top): the fresh-site baseline is not clean. Not from this slice |

No cross-tenant, permission or privacy finding.

## 10. Parity gaps (for Surbhi, not bugs)

- Day detail is an **inline row, not the prototype's modal `role="dialog"`**: no focus move or Escape-to-close. Awaiting her yes (AC-72).
- Refusal box on the Attendance Request page sits above the buttons (prototype: beside). Low.
- HR save line for 1 or more drops the example date (approved).
- No `hi.csv`: Hindi strings are not translated. Blocks the first number on a Hindi-reading tenant.

## 11. Not automated: human checklist

Browser pass on dev of the HR row, save lines, day sheet, `#att-req` note and refusal; 390 px, 200% text, 44 px taps, keyboard only, screen reader (AC-66); Hindi review; `next-time.js` press-Submit (OPS-27); landing proof and `security.log` (AC-61); one filing read in nginx's log (AC-67); release note wording (AC-63); counsel before the first non-blank number; DTC manual search; previous production tag proved to exist (OPS-28); Grace's 3-a-month script read before a number is set there.

## 12. Subtract pass

I deleted nothing from the engineer's tests. My file keeps one test per point plus the named persona and privacy checks; it deliberately repeats some of the engineer's cases on different fixtures. I removed one assertion from my own test (the joining date as a string inside a month blob) because it matched an ordinary day's `date` and could never be right.

## 13. Cleanup

I stop and remove `t084-bench`, `t084-db`, `t084-redis`, network `t084net` and volume `t084-sites`. The engineer's `alv084-*` stack is untouched and still running.
