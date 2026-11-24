---
slice: 086-manager-held-days
artifact: 04-test-report
author: hrms-test-automation-engineer
date: 2026-11-23
code under test: worktree .claude/worktrees/086-manager-held-days, branch slice/086-manager-held-days, a149041e (+ my test commits)
site: test_site on the throwaway stack alv086-bench / alv086-db / alv086-redis. Schema from this branch (apps are bind-mounted from the worktree).
status: tested LOCALLY. Nothing pushed, nothing deployed.
---

# 086 test report

## Verdict: **FAIL** (one P1)

**P1. A real database deadlock turns a send into an HTTP 500.** Three managers sending 50 rows at the same moment (HTTP, gunicorn 4 workers x 2 threads): in 4 runs, 2 of 3 sends returned 500 each time (`QueryDeadlockError 1213`, then `rollback to savepoint held_row` fails with 1305 "SAVEPOINT does not exist", `held_team.py:188`). InnoDB had already rolled the whole transaction back, so the savepoint is gone. AC-32 / OPS-56 say the loop stops, rows before stay filed, one Error Log entry. In a real deadlock none of that holds. The build's AC-32 test raises the error but keeps the savepoint, so it could not see this. Pin test, red today and failing with the same 1305: `test_held_team_086_proof.ProofCase.test_a_deadlock_gets_a_sentence_and_the_answer_never_names_a_request_that_is_not_there`. A single manager sending alone is fine. Owner: `hrms-fullstack-engineer`. I did not change feature code. Note: the answer must also never say "sent" for a row a full rollback removed. I did not find the lock pair that deadlocks (no PROCESS privilege on the throwaway DB).

## Defects

| Rank | What | Where |
|---|---|---|
| P1 | Deadlock gives 500, see above | `held_team.py` except branch for QueryDeadlockError |
| P2 | New **Held chip is 22 px tall at 360 and 390 px, 21 px at 1280**. AC-64 says 44 px on a phone and 24 px on a laptop. Prototype-v2 chips are about 44 px. The name button (`.tr-open`) is 23 px, but that is the existing page's | `panels.css` `.tr-chip` |
| P2 | Parity with prototype-v2 (needs Surbhi's yes per her rule): (a) the Held view opens under the whole filter block (From, To, Person, Group by, Show), so at 360 px the first held row is below the fold; v2 shows Show, chips and the list straight away. (b) v2's explanation paragraph "Held days have a punch missing, so pay for the day is on hold until HR fixes it. Give the missing time and a reason, and HR decides." is not drawn. (c) v2 chip has a warning icon; real one has none | `hdlRender`, `trChips` |
| P3 | AC-35 words: the 31st send gives 429 "Too many tries. Please wait a while and try again.", not "Too many sends. Please wait a while." (the shared limiter's sentence) | `field_app_limits._limited` |
| P3 | Bar says "1 days ready" (v2 has "1 day ready") | `hdlBar` |
| P3 | AC-49 says the banner has a "Go to the first one" button; none is drawn | `hdlDone` |
| P3 | Everything view still shows a red "No clock-out" badge on a Held row, next to "Held" (only the chip is hidden, per P-1) | `trRows` |
| P3 | Refusal line appends "Change the time and send again." to every refusal, including "Already waiting with HR" and "no longer held", where the time is not the fix. v2 says "Change what is needed and send again." | `hdlRow` |
| P4 | Test debt, mine: rate-limit keys left by the 31st-send test (cleanup pattern misses the Redis prefix). Unique names, harmless | proof file |
| P4 | Day lock now has its own test (see below). The engineer's "temporary debt" is closed | |

## Commands I ran (all on alv086-bench, test_site, one at a time)
`bench --site test_site run-tests --app alvoraa_portal --module alvoraa_portal.tests.<m>`; baseline of `test_held_team_086` before any change: 31 tests OK in 233 s. Final run numbers are in the section "Final runs". DOM: `NODE_PATH=/Users/mac/hr-app/node_modules node scripts/run_dom_tests.js`: **29 run, 0 not run, 0 failed**.

## Coverage of the 67 ACs
Test names: B = `test_held_team_086`, P = my `test_held_team_086_proof`, D = DOM test `portal_held_team_086_test.js`, J = my 360/390/1280 px browser journey, H = HTTP run, M = measured.

| AC | Proof | Result |
|---|---|---|
| 1, 2, 7 | B only_direct_reports...; P cancelled_request_brings_the_day_back | pass |
| 3, 4, 5 | B day_control_and_paging; J (chip "Held 5", line "5 held days need a time from you.", Show list "20 Nov 2026 (5)" + "All days") | pass. 5 (empty day text) only by reading code: **not run** |
| 6 | B query_count (2 vs 8 rows); M-1 6 queries at 5 and 50 rows | pass |
| 8 | B nobody_reports; P colleague_stranger_guest; P left_manager_sees_no_list | pass |
| 9 | P hold_switch_shows_in_the_answer; J (chip shown). "No clock-out" chip hidden: J. Row badge still shown | pass with P3 |
| 10 | P list_writes_nothing_to_the_cache; H header `Cache-Control: no-store,no-cache,must-revalidate,max-age=0` | pass |
| 11, 12, 13 | J: rows with strip and real punches, question names the person, Change flips the label, empties the box and puts focus in it | pass |
| 14 | J: 3-punch row shows a button, the timeline, a gap sheet that infers "Leaving", row then reads "+18:00 · Leaving Change" | pass |
| 15 | J: time only shows "Add a reason to include this day"; both shows "Ready" | pass |
| 16 | D; J used scripted input, not real keystrokes: **real-typing identity check not done** | D pass, J partial |
| 17 | J: label "Your reason Required", line "HR and X can read this. No health or family details.", D4 line "This reason is printed on the employee's monthly notice.", maxlength 500 | pass |
| 18 | H over real HTTP: GET 403; Guest POST 403; signed-in POST without CSRF header **400 CSRFTokenError, 0 requests filed**; B post_only | pass |
| 19 | B shape_and_size (51); P fifty_rows... (exactly 50 answered; 51 with a real first row files nothing) | pass |
| 20, 21, 27 | B shape_and_size, reason_rules | pass |
| 22, 23, 24 | B seven_case_scope, hr_and_a_submit_right..., left_or_switch_off; P colleague_stranger_guest (a colleague with no team, a login with no Employee, Guest) | pass |
| 25, 26 | B future-time, in_or_out tests; J (Esha 07:00 refused in words) | pass |
| 28, 30 | B partial_send; J (3 of 4 sent, 1 refused, no document for it) | pass |
| 29, 36, 54 | B row_is_filed_as_086_request | pass |
| 31 | B second_send; B TheLock (two real connections) | pass |
| 32 | B lock_wait_stops_the_loop | **passes only for a lock wait that leaves the savepoint. A real deadlock fails: P1** |
| 33, 34, 39 | B unexpected_error, answer_holds_no_reason, no_email | pass |
| 35 | P thirty_first_send (31st refused); H 31 posts: 30 x 200, 31st 429 | pass; words P3 |
| 37 | P request_alone_says_who_filed... | pass |
| 38 | Superseded by D-5 (no recheck endpoint). Page re-reads the list: D and code only | see "not covered" |
| 40 | M-3 | pass |
| 41 | B this_module_never_ignores_permissions | pass |
| 42 | diff against origin/dev: no patches.txt, fixture, custom field or json file | pass (diff) |
| 43, 44, 45 | J: bar "4 days ready ...", fixed on body, above the 68 px bottom menu at 360/390 and at bottom 0 at 1280; confirm lists name, day, time, reason | pass. 44 (over 50 ready) not run in a browser |
| 46, 47 | D (one call, five keys per row) | pass |
| 48, 49, 50 | J: banner "Sent 3 of 4 ... The 3 that went are waiting for HR.", role=status, refusal role=alert on its row, typed time and reason kept. 48 and 50 (offline) by D only | pass with P3 |
| 51 | D covers the lost-answer path. Browser: **not run** | partial |
| 52 | J: localStorage 0, sessionStorage 0 after typing. Back-after-logout: **not run** | partial |
| 53 | not run (assumption, no behaviour to test) | gap |
| 55, 60, 61 | B TheEmployeeAndHR (needs no Confirm, HR approves, Not right with a time replaces) | pass |
| 56 | P report_with_no_login_or_a_disabled_login | pass |
| 57, 58 | B TheFilerGuard | pass |
| 59 | B notice_for_the_register... (088's data); the day-sheet notice screen itself: **not run in a browser** | partial |
| 62 | read: the two functions return rows only; no per-manager count anywhere. Not automated | inspection |
| 63 | P marker_in_the_reason_appears_only_in_the_request (Error Log, Email Queue, Notification Log, Comment, Activity Log, every `.log` file in site and bench logs, the answer) | pass |
| 64 | J geometry: no sideways scroll at 360, 390, 1280; time box, reason box, Change, select, Send, confirm buttons on top, >= 44 px / 24 px. **Held chip fails (P2)** | fail on the chip |
| 65 | J: roles status and alert present; labels present. Keyboard flow, 200% text: **not run** | partial |
| 66, 67 | not tested (Hindi needs a native reader; time format read from code only) | gap |

## SEC, PRIV, OPS
| Item | Proof |
|---|---|
| SEC-1 | B seven_case, hr_and_submit_right; P colleague... (one fixed sentence, no name, security line per refusal) |
| SEC-2 | B never_ignores_permissions, partial_send |
| SEC-3 | B shape_and_size, reason_rules (script text loses `onerror`); P fifty rows |
| SEC-4 | H (GET, Guest, no CSRF, 31st). B pins the 30 per hour |
| SEC-5 | B TheLock; the savepoint P1 is the exception |
| SEC-6 | Case A only: B case_a_holds_only_for_the_managers_plain_addition |
| SEC-7 | B TheFilerGuard |
| SEC-8 | P request_alone...; B stamp test |
| PRIV-1 | D (five keys) |
| PRIV-2 | P marker test; B unexpected_error log test |
| PRIV-3 | B first test (no user_id, email, GPS, photo in rows) |
| PRIV-4 | J storage empty. Shared-handset Back test not run |
| OPS-39, 53 | M-1 |
| OPS-40, 55 | M-3 |
| OPS-41, 59 | HTTP 31st gives 429; nginx not run (not on this stack): **untested** |
| OPS-56 | **P1** |
| OPS-57 | B TheLock |
| OPS-58 | superseded by D-5 |
| OPS-60, 61, 62 | P marker (logs); diff for 61; OPS-62 release checks are the release's job |
| D-3 printed reason through 088 | B notice_for_the_register_carries_only_the_managers_words |
| OPS-62 worker alive for `short` queue | **not checked** (no worker in this stack) |

## Break tests (fix undone in-process by script on stdin; my test watched failing, then restored)
| New test | Guard switched off | Result |
|---|---|---|
| colleague_stranger_guest | `_team` returns everyone | fails (row filed, "+ Not sent...") |
| fifty_rows... | MAX_ROWS 500 | fails (51 accepted) |
| thirty_first_send | limiter unwrapped | fails ("ValidationError not raised") |
| cancelled_request_brings_the_day_back | cancelled request keeps hiding the day | fails |
| left_manager_hold_switch | `_switch_on` always true | fails |
| list_writes_nothing_to_the_cache | list writes a cache key | fails. **First version passed with the break (hollow); I rewrote it to spy on cache writes and re-proved it** |
| no_login_or_disabled_login | refuse no-login rows | fails |
| request_alone_says... | stamp without the manager id | fails |
| marker_in_the_reason | log carries the reason | fails |
| day lock (TheDayLock) | `day_row(for_update=False)` | fails ("second connection was not made to wait"); passes as built |
| deadlock test | none needed | red as built, 1305, the production error |
The first break of the 31st-send test was also hollow (I unwrapped one layer, not all); redone with `inspect.unwrap`.

## Measurements (throwaway data: 442 Employees tagged T86, one manager with 60 reports and 25 held days each = 1,500 held days, 1,729 Held in all; synthetic)
Gunicorn 4 workers x 2 threads, 120 s timeout, as production's compose. Date: 23 Nov 2026. MariaDB `innodb_lock_wait_timeout` 50 s, REPEATABLE-READ.

| M | Pass mark | Measured | Result |
|---|---|---|---|
| M-1 | equal counts, about 8 or fewer | 6 queries at 5 rows, 6 at 50, 6 for "all days" (1,500 held) | pass |
| M-2 | p95 <= 500 ms | 60 calls over HTTP: p95 46 ms (one day), 43 ms (all days); p50 39 and 37 ms. Reply 11.5 KB raw | pass |
| M-3 | 20 rows <= 3 s, 50 <= 10 s, queries per row steady | HTTP flat: 1 row 0.06 s, 20 rows 0.76 s, 50 rows 1.97 s. In-process 33 queries for row 2 and 33 for row 50 (ratio 1.0; first row 242-442 is cold cache) | pass |
| M-4 | deep <= 1.5 x flat | 50 rows: deep 2.00 s vs flat 1.97 s (1.02 x); queries per row 36 vs 33 | pass |
| M-5 | ordinary call p95 <= 500 ms, no 502/504; (and, in my reading, no failures) | ordinary call p95 50-76 ms, status 200 throughout. **But 2 of 3 simultaneous sends returned 500 (deadlock), 4 runs out of 4. The third took 1.9-2.5 s** | **fail (P1)** |
| M-6 | waits no longer than the send, no lock-wait error | second connection writing a day the send had filed waited 1.12 s; send took 1.76 s; no error | pass |
| M-7 | gzip growth <= about 8 KB | portal.js gzip -9: 371,189 to 376,832 = +5,643 bytes; panels.css +299 bytes; total about +5.9 KB. (Server's gzip level may differ) | pass |
First M-6 attempt wrote a day the send had not reached yet and so proved nothing; redone on the send's first row.

## Browser journeys (headless Chromium, the real portal served by this bench)
Walked at 360x780, 390x844 and 1280x900 as manager "Brw" with five reports (one punch In, one punch Out only, three punches, a very long name, a time the server refuses). Screenshots read: list, filled rows, timeline, gap sheet, bar, confirm, result. Held chip and day control; rows with strip and real punches; Change on one-punch rows; timeline on 3+ rows; required reason with the printed-notice line; fixed send bar above the bottom menu; confirm; banner and per-row refusal. No sideways scroll at any width. No console errors. The long name wrapped, no overflow.
Setup notes: on this stack I made `sites/assets/alvoraa_portal` a link to the app's public folder (it held only a stale copy without `css/ess` or `js/ess`), set `default_site` in the stack's common config, cleared `ess_part:` keys, set `last_password_reset_date` on my synthetic users (otherwise every call is refused by the first-use password wall, a real feature), and served with `bench serve` for the browser (gunicorn does not serve `/assets`). Passwords were generated at run time, never written in a test or the repo.

## Fixture honesty
The 085/087 fixtures create employees with no Shift Assignment, as DTC's staff have. My Held rows are built with real Employee Checkin and Attendance submits, as the app does. The timings used ORM inserts, not a bulk SQL write.

## Not automated, for a human
- Hindi wording (native reader). 200% text zoom, screen reader and full keyboard pass.
- Real phone on a real network: lost answer, offline banner, Back after logout on a shared handset.
- Employee's day-sheet notice and HR's card, drawn in a browser (only 088's data is pinned).
- nginx 429 wording on dev (not on this stack). Worker on the `short` queue (OPS-62).
- Counsel's gate and release order (OPS-R-2) are not code.
- Surbhi's yes on the P2 parity items.

## Not covered (named)
AC-5 text, AC-44 in a browser, AC-51/52/53 in a browser, AC-62 by automation, AC-66, AC-67.

## Subtract pass
Removed from my own first draft: nothing needed beyond rewrites (cache test rewritten, one test renamed). I kept one new class (TheDayLock) because the day lock had no proof at all.

## Final runs
See the section appended below after the last module finishes.

Run on 23 Nov 2026, alv086-bench, test_site, one module at a time, nothing else running:

| Module | Ran | Result |
|---|---|---|
| test_held_team_086_proof (mine) | 11 | 10 OK, **1 error: the deadlock test (P1), red on purpose** |
| test_held_team_086 | 31 | OK |
| test_held_day_085 | 45 | OK |
| test_punch_fix_087 | 132 | OK |
| test_attendance_correction | 148 + 19 (two batch summaries, both read) | OK, OK |
| DOM runner | 29 | 0 failed |
I did not run the full suite (instructed). The stack's `throttle_user_limit` is 100000 (local only; CI will meet Frappe's throttle on the 086 and 085 modules run back to back).

## Clean-up
Removed my T86 Employees, Users, requests, checkins, attendance, the "Held days send" Error Log rows the tests left, the rate-limit keys; put the assets folder and common config back; removed the proxy container. Left in place: the stack's own test fixtures (Hd* rows from the build suite are rolled back by the tests).

---

## Re-test after fix round 1 (23 Nov 2026, HEAD 58ed719a + one test commit)

**Verdict: PASS WITH KNOWN DEFECTS** (no P0, no P1). Site test_site, schema from this branch, stack alv086-*, one module at a time. The P1 is closed. One new P2 was found and fixed in the test code (below). Not done: nginx, real phone, Hindi, screen reader (see the human list above).

### P1: three managers at once (real HTTP)
Command: gunicorn 4 workers x 2 threads, 120 s timeout, port 8090; three signed-in managers, 50 rows each, sent at the same moment (a barrier); 4 runs on four different days; synthetic people (3 managers, 150 reports, 4 held days each).
- **500s: 0 of 12 sends.** All 12 answered 200 in 0.1 to 2.9 s. The deadlock still happens (`QueryDeadlockError` named in the Error Log in each run, 2 or 3 sends a run), but the answer is now a sentence ("Not sent. The office was busy ... send again.").
- **"Sent" is true:** for every send I compared the rows answered `ok` with `Attendance Request` rows in the database. Said sent but not in the database: **0**. In the database but not said sent: **0**. (Runs: 50/0/2, 50/0/0, 50/0/0, 50/0/0 sent for the managers that were not stopped; stopped sends had their later rows answered "not sent".)
- **Rows before the fault stay filed:** run 1, one manager got 2 rows filed, then stopped, and those 2 are in the database (AC-32).
- **One Error Log row per faulted send**, text only: manager id, 50 rows, N sent, first fault name. No name, time or reason.
- `test_held_team_086_proof`: 11 OK (including the deadlock pin).
- **Break test (in-process, nothing on disk changed):** with the plain-rollback fallback in `_undo_row` switched off, the same deadlock test fails with `1305 SAVEPOINT held_row does not exist`; as built it passes. Proven.
- Note for the next reader: managers who lose the race often get all 50 "not sent" (the deadlock hits their first row). The answer is correct and tells them to send again. That is the design (OPS-56), not a fault, but a busy Monday may feel like "nothing went". Not blocking.

### P2: Held chip, headless Chrome 360 / 390 / 1280, manager with 50 held days
| Check | 360 | 390 | 1280 |
|---|---|---|---|
| Held chip height (target 44 phone, 24+ laptop) | 44 | 44 | 26 |
| "Everything" chip height (same row) | 44 | 44 | 26 |
| Warning triangle on the chip | yes | yes | yes |
| First held row top (px from top of the window) | 547 of 780 | 523 of 844 | 457 of 900 |
| Sideways scroll / script errors | none / none | none / none | none / none |
Screenshots read (rt-360-team, rt-360-held, rt-360-refused, rt-1280-held, in the scratchpad). Against prototype-v2: the path of the triangle is the same string; the explanation paragraph ("Held days have a punch missing, so pay for the day is on hold ...") is the same words and is shown; on the Held view only the Show box is above the chips, the From/To/Person/Group by block is gone, and it comes back on Everything. The other chip on that page sits level with Held, same height. **Not checked:** the other flag chips (Late, Short hours and so on) were not on screen because the synthetic data had none; they share the same CSS rule only.

### P3 wording, in the browser at 360 px and by HTTP
- "1 day ready" after one row typed, "2 days ready" after two: seen.
- Send with one good row and one refused row: banner "Sent 1 of 2 to HR. 1 not sent. ... Go to the first one"; the button is there (44 px high), pressing it moves focus into the refused row's time box; refusal line ends "Change what is needed and send again.": seen.
- "No clock-out" chip: not on screen with the hold on (only Everything and Held). Inference: the data had no such flag, so this is the DOM test's proof (portal_held_team_086_test.js, 0 failed), not a browser one.
- 31st send: HTTP 429 `FieldAppRefusal: Too many sends. Please wait a while.` (manager had 4 earlier sends, the 27th more call was refused = the 31st in the hour). Other `_limited` callers keep their own words: the default argument is the old sentence, and `test_leaver_report_089`, which asserts "Too many tries", passes.

### Modules (each once, full output read, both batch summaries read)
| Module | Result |
|---|---|
| test_held_team_086 | 31 OK |
| test_held_team_086_proof | 11 OK |
| test_held_day_085 | 45 OK |
| test_punch_fix_087 | 132 OK (after the clean-up below) |
| test_punch_fix_087_proof | 11 OK |
| test_register_notice_088 | 79 OK |
| test_attendance_correction | 148 OK and 19 OK (two summaries) |
| test_employee_documents_078, test_field_app_password_signin_128, test_leaver_report_089, test_portal_security_010 (the modules that use `_limited` / field_app_limits) | 20, 59, 47, 45 + 5 OK |
| test_event_form_082 | **0 ran, 12 skipped** (I did not look into why; the skip is not new code) |
Static: DOM runner 29 run, 0 failed, exit 0. check_design_system.py exit 0. check_portal_trays.js --static exit 0 (33 fixed elements, 0 problems). check_brand_spelling.py exit 0. check_app_integrity.py exit 0 (1,031 checks). check_scope_traps.py inside the container exit 0, its self-test exit 0.

### New defect found and fixed in test code: P2, "a test must put back what it takes"
The first full pass had 3 failures in other modules: `test_punch_fix_087 ... test_to_review_gives_the_card_and_no_photo_or_location_key`, `test_punch_fix_087_proof ... test_ac35_fifty_pending_punch_fixes ...` (2.0 to 2.6 s against 1.5 s) and `test_attendance_correction ... test_hr_sees_what_is_waiting`. Cause: since fix round 1, `send_held` commits each row, and a commit makes every fixture of the test permanent. Running only the two 086 modules left **33 waiting requests, 53 Held days and 234 people** on the site (measured). The review queue reads the oldest 50 (and 200), so those three tests stopped seeing their own request. The site also still held 202 requests from my own earlier HTTP runs (also removed).
Fix: `HeldTeamCase._wipe` in `test_held_team_086.py` (commit 4113d192) deletes the case's people, days, punches, requests and logins at the end. **Proven:** before it, two 086 modules left 33 requests and 287 employees; after it, 0 requests and 53 employees (the baseline) after the same two modules. The three failing tests then passed alone, and 087, 087 proof and attendance_correction passed in full (above). Leftover on the site after those: 0 requests, 53 employees. For the product code this is fine (a request is real once filed). For the build team: any new test that calls `send_held` must use this case.
Known limit: `_wipe` deletes by the case's name tag. A test that makes a person with another name would leak.

### Still open (P3/P4, no one blocks)
- P3: the fix agent's own notes say the Held view with no held days still shows the full filter block; I did not look.
- P3: `test_event_form_082` skipped (12). Owner: whoever owns slice 082.
- P4: the 31st-send test names the old words; fine.

### Clean-up done
Removed my synthetic managers, reports, days, requests, Error Log rows; removed the earlier run's 202 requests and 442 T86 people; stopped gunicorn, bench serve and the temporary port forward (alv086-fwd); put the stack's assets folder back as it was; deleted the Chrome profile folders. Nothing pushed, nothing deployed.
