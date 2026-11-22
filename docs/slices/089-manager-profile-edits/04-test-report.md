---
slice: 089-manager-profile-edits (ALV-431, ALV-433)
artifact: 04-test-report
author: hrms-test-automation-engineer
date: 2026-11-22
risk tier: 1
code tested: branch slice/089-manager-profile-edits, HEAD 968bfe0e plus one test commit (see end). origin/dev has since moved to 039bab0a (not rebased)
site and schema: alv089-bench, site test_site, image dev-3830ed3, schema built from this branch (Custom Field on ToDo present)
---

# 089 · Test report

**VERDICT: FAIL.** One P1 defect (D-1) and one unsettled P2 (D-6), the first found only in a real browser: **at 360 px the report icon on the Scorecard is covered by the "Joined" badge and cannot be tapped** (details below). Every 089 test passes (39 + 10 Python, 27 DOM runs). The other failures in the full suite are older and are listed below with how each was checked. Nothing was pushed or deployed.

## 1. Defects

| ID | Severity | What | Proof |
|---|---|---|---|
| D-1 | **P1** | At 360 px wide, the report icon (`#sc-left-btn`) is drawn under the "Joined 1 Jan 2025" badge. The icon box is x 244-288, y 112-156. The badge is x 204-324, y 121-148. `document.elementFromPoint` at the icon's centre returns `DIV.sc-join-badge`, not the button. A real finger tap hits the badge. The icon is not visible in the screenshot either. The name column is squeezed to a few pixels and the name runs under the badge. This breaks AC-1, AC-2 and AC-62 for the main user (a store manager on a phone). A script `click()` on the button works, so the DOM tests pass. | Ran it: real portal in headless Chromium, 360 x 780, signed in as a manager, scorecard of a direct report with no open report. Screenshots `shots/sc_r3.png`, `shots/sc_r2.png` in the scratchpad. |
| D-2 | P3 | `test_register_fill_194.test_the_seat_reports_the_soonest_last_day` fails. It hard-codes the dates 2026-11-01 and 2026-12-31, and today is 22 Nov 2026, so the "sooner" date is in the past. Not this slice: `register.py` and that test file are unchanged against 4df25095. A date rot, the kind lesson 5 warns about. | Ran it twice: same failure, `'2026-12-31' != '2026-11-01'`. |
| D-2b | P3 | Build 3, first run: three errors in `test_leave_permissions` ("You can only act for employees of the companies you look after"). The fixture puts the HR person and the other employee in "whichever company Frappe lists first" (comment in `leave_fixtures.py`). On `q3_site` they landed in two different companies (S043 Wave Three Company and Flags Test Co), so HR was refused. On `q5_site` the whole quarter passed, and on a fresh site the module passes before and after both 089 test files. Not 089 code (`_hr_target_employee` unchanged). Old fixture weakness. | Ran it: fails alone on `q3_site`, passes alone on `test_site` and `q5_site`. |
| D-5 | P3 | Build 2: `test_inbox_parts_042...test_get_nav_counts_does_not_grow_with_the_correction_backlog` failed `(5, 42) != (3, 40)`: two attendance corrections were already pending for that user, left by another test in the same quarter. The test's own guard message says "nothing was proved". Passed alone: the whole module twice on `test_site`, and the single test on `br_site`. No 089 module is in build 2. | Ran it |
| D-6 | **P2, not settled** | Build 4: `test_security_log_alv391` (the last module of the quarter, after 1,183 passing tests) gave one failure (`the refusal wrote nothing: the file did not grow`) and one error (`IndexError`). The module passes alone on `q4_site` and `test_site` after the quarter, and 12 of 12 times when four copies run together, so it is not a clash between my runs. It needs the whole quarter's process state first. No 089 module is in build 4, and 089 does not touch `access.refuse` or the logger. I started build 4 again alone on `q4_site` and stopped it after about 300 tests because it would take about 100 minutes to reach that module. **Not run to the end. CI's quarter 4 is the arbiter.** This test is what makes SEC-5 ("the log is real") observable on a tenant, so do not push until it is green in CI or on a clean quarter-4 run. | Ran it, not isolated |
| D-3 | P4 | A Left manager opening a report's Scorecard gets a `ValidationError` ("No employee record found"), not a `PermissionError`, and no SEC-5 log line. Nothing leaks. It is the old line, untouched by 089. | New test `test_a_left_manager_is_refused...` accepts either type and asserts nothing is returned. |
| D-4 | P4 | `TestPins.test_the_endpoint_is_post_only_and_rate_limited` has an assertion that only runs `if hasattr(...)`. The eleventh-request test over HTTP covers the limit for real, so nothing is uncovered. | Read the code. |

## 2. What I ran

All on the engineer's stack (`alv089-bench`, `test_site`), one run at a time, `pgrep run-tests` checked before each.

| Command | Result |
|---|---|
| `bench --site test_site run-tests --app alvoraa_portal --module alvoraa_portal.tests.test_leaver_report_089_qa` (my new file) | **Ran 10 tests, OK** |
| The full suite (see the next sentence) | **The full suite, run the way CI runs it:** `CI=true bench --site <site> run-parallel-tests --app alvoraa_portal --build-number N --total-builds 4`, one build per site on four sites (`test_site`, `br_site`, `q3_site`, `q4_site`), at the same time. A single `run-tests` over 4,941 tests needed about 6 hours, so I stopped it at 1,107 tests (0 failures, not counted below) and used CI's own split. This runner prints one `Tests:` line per build, not two batches. Build 1: **1182 tests, 0 failing, 0 errors.** Build 2: **1273 tests, 1 failing** (D-5). Build 3: **1287 tests, 3 errors** (D-2b), then re-run on a second fresh site `q5_site`: **1287 tests, 0 failing, 0 errors.** Build 4: **1199 tests, 1 failing, 1 error** (D-6). Total 4,941 tests. |
| `hrms.alvoraa_org_structure.tests` modules `test_cover_policy` 25, `test_reach` 13, `test_register_194` 38, `test_company_scope_194` 8, `test_metrics` 24, `test_org_structure` 33 | all OK |
| `test_register_fill_194` | Ran 62, **FAILED (failures=1, skipped=2)**: D-2, a date that is now in the past. Not this slice |
| Break-test runs, single tests on `test_site` | 8 tests broken and run, each shown failing, then restored (section 3) |
| `node scripts/run_dom_tests.js` | 27 run, 0 not run, 0 failed |
| `python3 scripts/check_app_integrity.py` (exit code read directly) | exit 0, 1015 checks, OK |

## 3. Break tests (each new test, failed for its own reason, then restored)

Commit first, patch, run only that test, `git checkout` the file. Run from `scratchpad/brk.sh`.

| New test | I broke | It failed with |
|---|---|---|
| `test_another_teams_manager_is_refused...` | the manager check in `get_employee_scorecard` (`and False`) | `PermissionError not raised` |
| `test_a_left_person_gives_no_fields_on_either_call` | dropped `status == "Active"` in `is_direct_active_report` | `'9876543210' unexpectedly found` in the scorecard JSON |
| `test_no_leaving_date_reaches_positions...` | `send_leaver_report` also wrote `relieving_date` | `datetime.date(2026, 12, 1) is not None` |
| `test_the_candidate_list_is_exactly_the_closed_list...` | added `personal_email` to `MANAGER_SEES_FIELDS` | `Items in the first set but not the second` |
| `test_a_value_written_around_the_setter_still_gives_nothing_off_list` | read the stored value without `people_fields.allowed` | `Items in the first set but not the second` |
| `test_eleven_holders_are_refused_and_ten_are_accepted` | `CONFIRMER_CAP = 100` | `PermissionError not raised` |
| `test_the_outcome_bell_is_read_only_by_its_reporter` | `_tell` also wrote a bell for the colleague | `Lists differ: [{'name': ...}] != []` |
| `test_nobody_outside_the_circle_reads_the_notice` | on `test_site`, inserted Custom DocPerm rows (copies of ToDo's two standard rows plus `Employee` read), run, then deleted them | `'Last working day' unexpectedly found` (my first try failed for the WRONG reason, `The report could not be sent`, because a bare extra row replaced the standard rows; I rebuilt it with the copies). Custom DocPerm rows on ToDo after: 0, as before. |

Not broken, and why: `test_a_left_manager_is_refused...` and `TestWhoIsRefusedPersonalDetails.test_personal_email_gender_company_email_never_appear...` assert absence. The engineer's break 1 (dropping the `reports_to` check) and my first break cover the same code. I did not prove the second one on its own: **a pass here rests on reading, not on a failing run** `[inference]`.

## 4. Coverage

AC numbers are the spec's. "E" is the engineer's file `test_leaver_report_089.py` (39 tests, read, not re-run alone; it is inside the full suite). "Q" is my file.

| AC | Proof | State |
|---|---|---|
| 1 icon rules | E `test_can_report_is_true_only_for...`; DOM | pass in code. **Fails on a real phone: D-1** |
| 2 sheet, 3 send, 5 double tap | E `test_a_direct_manager_reports...`, DOM; browser: sheet opens, focus on date, field 16 px, 44 px high, buttons 48 px, send then "Sent for confirmation", Done | pass. Sheet reached by script click because of D-1 |
| 4 no signal | DOM | pass (not re-run in a browser) |
| 6, 7 refusals | E `test_refusals_write_nothing_and_are_logged` | pass |
| 8 dates | E `test_the_date_window` | pass |
| 9 duplicate | E `test_a_second_report_is_refused...` | pass |
| 10-13 ToDo, one transaction | E first test, `test_a_failed_insert_leaves_no_todo_for_anyone` | pass |
| 14-18 outcome | E `TestEmployeeSave`, `test_a_confirmer_closes_it...`; Q bell test | pass |
| 19 | E `test_left_is_refused_while_active_people_report_to_them...` | pass |
| 20, 21 | E `TestGuard` | pass. The `assign_to.remove` door is not called: with no reference on the ToDo it finds nothing (read, plus the engineer's break 4) |
| 22-24 employee line | E `test_the_person_sees_one_line...`; browser: line shown, 15 px, no sideways scroll | pass |
| 25 who can read the ToDo | Q `test_nobody_outside_the_circle_reads_the_notice` (colleague, another team's manager, skip-level, other company's HR, guest; `get_list` and `client.get_list` on ToDo and Notification Log, `getdoc` on Employee) with the allowed readers (confirmer, reporter) beside it | pass, break-tested. Gap closed |
| 26, 27 | E | pass |
| 28 card only for System Manager | E `test_the_card_payload_is_system_manager_only...`; browser as Administrator | pass |
| 29-30, 32-35 settings | E `TestSettings`; Q list and cap tests | pass |
| 31, 43-48 | deferred by Surbhi | not built |
| 36-38 | E, Q `TestWhoIsRefusedPersonalDetails` (other team's manager, Left manager, Left person on both calls, the closed list on both calls) | pass. Gap closed |
| 39 | E | pass |
| 40, 41 | E; browser (card shows "Not set" for an empty value) | pass |
| 42 | E pin | pass |
| 49, 50 | E; browser: grey line on Team, note on Scorecard | pass |
| 51 not a leaving fact | Q `test_no_leaving_date_reaches_positions...` (Positions profile as HR Manager, skip-level's Team call, `relieving_date` empty, `status` Active) | pass, break-tested. Gap closed |
| 52 | E `test_the_open_state_is_one_query...` (1 and 51 people) | pass |
| 53-55 CSRF, POST only, rate limit | E `TestARealRequest` over real HTTP | pass |
| 56-60 | release steps | not code, not done here |
| 61 translation | engineer: every string wrapped, no Hindi added | human-checked |
| 62 360 px, 44 px, 16 px, no sideways scroll | browser, section 5 | **Fail on D-1; the rest pass** |
| 63 | E | pass |
| 64 no route, nginx, DocType, queue, scheduler change | `git diff 4df25095..HEAD --name-only`: no `deploy/`, no hooks for queues or scheduler, no DocType file | pass (read, not a test) |
| 65 | E `test_nobody_to_confirm_writes_nothing` | pass |

## 5. Browser journeys at 360 x 780 (real portal, headless Chromium, `br_site`, my own second site on the same stack)

Setup: second site `br_site` built the way CI builds one, synthetic S089 people, an Administrator and three users with a known password. Browser fixtures were made by the same helpers the tests use. The portal's own `sites/assets/alvoraa_portal` folder was a stale copy (only one file), so portal.js returned 404 until I linked it to the bind-mounted app folder. On this stack only; I did not check dev or production. It is a reason to compare the served portal.js with the image at release (OPS-8). ESS part keys for `br_site` cleared in Redis before the run.

| Screen | Targets 44 px+ | Field text 16 px+ | Sideways scroll | Result |
|---|---|---|---|---|
| Team card (2 cards) | card 137 x 215, whole card taps | n/a (no field) | none | pass. Grey line is 12 px text, not a target |
| Scorecard, report icon | box is 44 x 44 | n/a | none | **FAIL: covered by the Joined badge (D-1)** |
| Report sheet | date input 44 high, buttons 48 high, Done 48 | date input 16 px | none | pass. Focus lands on the date. Sheet bottom at 780 (touches the screen edge) |
| Scorecard note | text only | 15 px | none | pass |
| Personal details card | text only (labels 12 px, values 15 px) | n/a | none | pass on layout. Values are 15 px, the portal's own body size |
| Employee line (My profile, as the reported person) | text only | 15 px | none | pass |
| Administrator card: "Change what managers see" button 207 x 44, role select 290 x 44 at 16 px; the dialog's three ticks sit in rows 57 to 75 high | pass | select 16 px | none | pass |

200% text: I set the page font size to 200%. Most of the portal is in pixels, so this is a weak test. No sideways scroll on the scorecard, the sheet, My profile or the Administrator dialog. **A real phone with the system font at 200% is a human check.**

## 6. SEC, PRIV and OPS items

| Item | Proof |
|---|---|
| SEC-1, SEC-2 | E `test_nothing_personal_is_sent_by_default`, `test_who_gets_the_fields`; Q four tests in `TestWhoIsRefusedPersonalDetails`. Both lists non-empty in the allowed cases |
| SEC-3 | E `test_an_hr_manager_is_refused...`, `test_the_list_is_closed`; Q closed-list tests |
| SEC-4 | deferred with the change half. Pin `MANAGER_EDITABLE == ()` stands |
| SEC-5 | E reads the line from the log handler; Q asserts none of five personal values is in any line |
| SEC-6, SEC-7, SEC-8 | E; Q cap test with 11 real users (the engineer patched the number) |
| SEC-9 | E `TestGuard` (three of the four doors; see AC-20) |
| SEC-10 | Q `test_nobody_outside_the_circle_reads_the_notice`, `test_the_outcome_bell_...`. **Not checked: Custom DocPerm rows on ToDo at DTC, Grace, PPJ.** One read-only query per tenant before main (release step) |
| SEC-11 | E `test_the_name_is_escaped...` |
| SEC-12 | E `TestARealRequest` |
| PRIV-1 | E `test_fresh_defaults`; Q closed list |
| PRIV-2 | E `test_the_person_sees_one_line...` (no confirmer id in the JSON); browser |
| PRIV-3 | Q `test_no_leaving_date_reaches_positions...`. The served ESS parts hold no template tags (Frappe refuses them in `_read`) and no fixture value (grep of `parts/*.html`: none) |
| **PRIV-4 retention** | **Untested control.** No rule from counsel yet. Blocks main |
| OPS-1, OPS-16, OPS-17, OPS-18, OPS-22 | release steps on a copy, not run |
| OPS-2, OPS-7, OPS-11, OPS-13, OPS-19, OPS-21 | E: ToDo only, one POST, cap (Q, real people), no Email Queue row, no index |
| OPS-3, OPS-20 | E, Q: unknown, empty and no-writer roles refused; "Nobody can confirm this yet" |
| OPS-5 | E: one ToDo query for 1 and 51 people |
| OPS-6, OPS-15 | static: parts hold no text from a person. Redis part cache on dev (OPS-8) is a release read |
| OPS-9, OPS-14 | Q, E |
| OPS-10 | 3G timing: **not measured** |
| OPS-12 | E over real HTTP |
| OPS-23 | integrity script exit 0 |
| OPS-24 | `leaver_report.py: 1` in `test_portal_security_010` (inside the full run) |
| OPS-25 | E pin test; DOM test registered (27 run) |
| OPS-26 | E four break tests plus my eight (section 3) |

## 7. What I did not automate (human checks)

- A manager tapping the icon on a real phone, after D-1 is fixed. Re-measure with `elementFromPoint`.
- System font at 200% on a real phone. Focus ring colour. Screen reader reading the sheet.
- 3G timing of the Team part against 2.5 s (OPS-10).
- Hindi (none added).
- The set-Left dry run on a copy of real data (OPS-16), migrate timing and queue, Custom DocPerm rows on ToDo per tenant, and PRIV-4 with counsel.

## 8. Subtract pass

Removed from my own plan: a test for `assign_to.remove` (a no-op by construction), a Notification Log test of a non-existent comment door, and a wall-clock test. Nothing in my file restates an engineer test: each one is a case the engineer's notes named as not run.

## 9. Commits

`67fbca7f` (my test file). This report is in the next commit. Not pushed.
