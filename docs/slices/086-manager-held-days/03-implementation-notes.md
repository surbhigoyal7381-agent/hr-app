---
slice: 086-manager-held-days
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-11-23
status: built and tested LOCALLY. Nothing pushed, nothing deployed.
built on: worktree /Users/mac/hr-app/.claude/worktrees/086-manager-held-days, branch slice/086-manager-held-days, base origin/dev 412d5361
---

# 086 - Implementation notes

## What was built (rung 4, a little new code, no DocType, field, setting, job or patch)

| File | Mechanism | Why |
|---|---|---|
| `alvoraa_portal/held_team.py` (new) | Build: two calls, `held_days` (read) and `send_held` (POST, 30 an hour, 50 rows) | The list and the batch did not exist. Every rule is delegated to `attendance_correction.raise_for_report`; this file adds only the per-row scope check, the future-time and In/Out refusals, and the locks |
| `attendance_correction.py` | Extend: the direct-report check now runs for every caller (D-1, ALV-425); the stamp names the manager's id (SEC-8) | Closes F1 |
| `punch_fix.py` | Extend: `_refuse_edit_by_others` in `validate`, `refuse_delete_by_others` for `on_trash` (D-2) | Under case A there is no Confirm, so this is the guard |
| `hooks.py` | One `on_trash` line on Attendance Request | Frappe-first hook |
| `public/js/ess/portal.js`, `public/css/ess/panels.css` | Extend: Held chip and view on the Whole team page (`hdl*`), send bar on `<body>`, timeline on 3+ punch rows | Prototype-v2, P-1 to P-6 |
| `scripts/check_portal_trays.js` | Inventory gets the new fixed bar | The static check counts every `position:fixed` |
| `tests/test_held_team_086.py`, `tests/portal_held_team_086_test.js`, `scripts/run_dom_tests.js` | Tests; the DOM runner now expects 29 | Pin tests |
| `tests/test_held_day_085.py`, `tests/test_punch_fix_087.py` | Old tests follow D-1 (HR is made the worker's manager first; the stamp has the id) | Surbhi's decision D-1 |

## Commits (all local)
a03ed628 and 8cea5fc3 (earlier engineer), e80a0491 (DOM test and runner), plus the notes commit that follows this file.

## Acceptance criteria
Covered by `test_held_team_086.py` (31 tests: list, send, scope, filer guard, lock, HR and employee side, 088 notice) and the DOM test (20 checks). I did not re-walk all 67 ACs one by one in this step; the reviewer and test stage should trace the AC table against the test names. **Not checked:** the 360 px screen and the timings (left to the test stage by instruction).

## Gaps against the prototype
None found by reading prototype-v2 against `hdlRow`/`hdlBar`/`hdlAsk`. Two approved words differ from v2 by decision: D-4 (reason box says it is printed on the monthly notice) and P-3/P-5/P-6. **Not checked in a browser.**

## Seven non-functional dimensions (against the code written)
| Dimension | Verdict | Line |
|---|---|---|
| Performance | neutral | `held_days`: four queries however many rows (a test counts them); 50-row page; a send is one savepoint per row |
| Security | improves | F1 closed (HR no longer files for people who do not report to them); filer edit/delete guard; every row scope-checked; POST only; a locking read stops a double send; no `ignore_permissions` (a test greps for it) |
| Reliability | improves | a refused row leaves no document, the others go; a lock wait stops the loop and keeps what went; a lost answer is re-read, never re-sent |
| Scalability | neutral | bounded by 50 rows and 92 days; locks taken in sorted order so two overlapping sends do not deadlock |
| Maintainability | neutral | one new file; rules stay in the existing door; no copy of the reason rule |
| Data integrity | improves | stamp joined with a blank line so 088 prints only the manager's words; duplicate check is a locking read (see below) |
| Compliance / privacy | improves | rows carry five keys, no GPS, photo, login or email; error log holds counts and the manager id only; nothing typed is stored in the browser |

## Test results (alv086-bench, site test_site)
test_held_team_086 31 OK (30 in the first batch run; 31 on the final re-run after the break tests, I did not find which test is the extra one); test_held_day_085 45 OK; test_punch_fix_087 132 OK; test_punch_fix_087_proof 11 OK; test_register_notice_088 79 OK; test_attendance_correction 148 OK (second batch 19 OK); test_security_alv411_412 9 OK; test_attendance_doors_085 16 OK; test_confirm_switch_alv430 13 OK. DOM runner: 29 run, 0 failed. Static checks (design system, trays, brand spelling, app integrity, scope traps): exit 0 each.

**The 21 errors seen in the first 085 run were not 086 code.** All were Frappe's own "Throttled" (more than 60 new Users in an hour, `throttle_user_limit`) after the 086 module created many users. I set `throttle_user_limit` to 100000 in the throwaway site's config on this stack only, and 085 then passed (45 OK). Anyone running the whole list back to back will hit the same wall.

## Break tests (fix undone, own test watched failing, fix restored)
| Fix | Test | Result |
|---|---|---|
| Future-time refusal | test_a_time_that_has_not_happened_is_refused | fails (the row was filed, no refusal) |
| In/Out refusal | test_an_in_or_out_that_disagrees_with_the_time_is_refused | fails (filed) |
| Duplicate lock (locking read) | TheLock two-connection test | fails: second send missed the first's request and filed |
| Day lock | TheLock | **still passes without it**: see gaps |
| D-1 | test_hr_and_a_submit_right_login_are_held_to_direct_reports_too | fails (no refusal) |
| D-2 edit guard | test_neither_the_manager_nor_the_employee_may_change_what_it_says | fails |
| D-2 on_trash | test_neither_may_delete_it_but_hr_may | fails |
| D-3 blank line | test_the_notice_for_the_register_carries_only_the_managers_words | fails: printed "...18:30 One of 2 days sent together." |
| DOM: reason required | portal_held_team_086_test.js | 2 checks fail |

## Known gaps
- **Day lock has no test of its own (temporary debt).** The duplicate lock alone already serialises the two sends. The day-row lock is kept because it also guards against a punch or an HR fix landing in between, but no test proves that. Removing it is the alternative; the reviewer should choose.
- Throttle setting above is a local-stack setting, not in the repo.
- Subtract pass: I removed nothing from the earlier engineer's code; I read each function and found none unused.


## Fix round 1 (23 Nov 2026, after the test report: Fail, one P1)

**P1, the deadlock. Design chosen: commit after each filed row** (`held_team.send_held`). Why: a deadlock makes InnoDB roll back the whole transaction and forget its savepoints, so `rollback to savepoint` itself failed (1305) and the manager got a 500. With a commit after every row, what is filed is durable, so AC-32 is true as written (rows before the fault stay filed) and the answer can say "sent" only for a row that really is committed. Locks are also held for one row instead of 50. A small `_undo_row()` tries the savepoint and falls back to a plain rollback; because earlier rows are already committed, only the failing row is lost. No retry, no new setting. The lock-wait branch still stops the loop, rows after it are answered "not sent", one Error Log row with counts, manager id and fault name. Rejected: catching the deadlock without committing (every earlier row would be gone, so the answer would have to say "nothing sent", which breaks AC-32). Trade-off: a send is no longer all-or-nothing at the database level. It never was at the answer level (AC-28), so nothing the manager sees changes.
Tests: `test_held_team_086_proof` 11 OK (the deadlock test is green); `test_held_team_086` 31 OK. **Break test:** with the plain-rollback fallback removed, the deadlock test fails with the same `1305 SAVEPOINT held_row does not exist`; restored.

**P2.** Chip: `.tr-chip` is now `inline-flex` with `min-height:24px`, and 44 px under 768 px (existing `max-width:768px` breakpoint, existing values only). This also sizes the other chips on that page the same way, so the row stays even. Prototype parity: (a) on the Held view the From/To/Person/Group by block gives way to the one Show box (`trBar` brings it back when you leave), then chips, line and list; (b) the explanation paragraph is drawn; (c) the warning triangle (prototype-v2's path) is on the chip.

**P3.** "1 day ready" / "N days ready"; "Go to the first one" button in the banner when a refusal is showing (scrolls to and focuses the first refused row); refusal line now ends "Change what is needed and send again."; the red "No clock-out" badge is hidden on every row while the hold is on (same condition as the chip). AC-35: `_limited` got an optional `message` argument (default is the old sentence, so no other caller's words change; count of other callers passing it: 0). `send_held` passes "Too many sends. Please wait a while."

**Not changed / for the next stage:** the old Held-view code for a leaver or empty list still shows the full filter block when there are no held days (the Show box has nothing to offer). Not browser-checked at 360 px in this round: re-measure chip and first-row position.


## Fix round 2 (23 Nov 2026, after the review and the security review: SHIP WITH FIXES)

Worktree `/Users/mac/hr-app/.claude/worktrees/086-manager-held-days`, branch `slice/086-manager-held-days`. Rebased on `origin/dev` 0a181d05 before any edit (was base 412d5361). Surbhi approved every recommendation. Local only: nothing pushed, nothing deployed. Risk tier 1 (who may file a time for whom, a lock on shared data, text printed on a notice).

**What came in with the rebase (clean, no conflict).** Three ALV-436 commits by the same account: `bcb8a6f8` "a reason is refused rather than quietly emptied", `f6d91de4` "put back the four assertions my edit split off", `0a181d05` "the test that found this fault now states the fix". Files: `punch_fix.py` (+40, new `refuse_if_the_words_would_be_lost`, called first in the Attendance Request `validate`), `register_notice.py` (+6), `tests/test_punch_fix_087.py`, `tests/test_register_notice_088.py`. I read the diff. **Effect on 086:** a manager's reason shaped like a tag (`<urgent>`) is now refused with a sentence. Two things followed. (1) `test_reason_rules` filed `<img ... onerror>` and expected a request; it now expects the refusal. (2) `_refusal_of` used `strip_html_tags`, which ate the "< and >" out of that sentence ("without  around a word"). It now removes only real tags (`<b>`, `</b>`). Both are pinned.

**M-1 (P2), the deadlock.** `held_team.py`: the duplicate check is a plain read (no `for_update`); `frappe.db.commit()` at the top of each row, before the day-row lock, so the read after the lock starts a fresh snapshot. Day-row lock kept. No index. Proof (all proven, run here):
- `TheLock` and `TheDayLock` pass (the 11-test proof module is OK; `test_held_team_086` is in the table below).
- Break test: with the commit removed, `TheLock` fails (the second send files a duplicate). Restored.
- Three managers x 50 rows, real HTTP (gunicorn 4 workers x 2 threads, 120 s), 4 runs: 12 of 12 sends answered 200, **150 of 150 rows sent in every run, 0 not sent, 0 deadlocks, 0 new Error Log rows, 0 500s**; for every send the rows answered "sent" matched the Attendance Requests in the database, both ways (0 missing, 0 extra). Each send took 2.9 to 3.7 s.
- Break run on a fresh day with the old code (locking read, no commit): the deadlock came back at once. Manager 1 sent 0 of 50, manager 3 sent 1 of 50 (49 "not sent"), 2 Error Log rows. So the loser of a race got "all not sent" under the old code and does not now.

**F1.** Blank lines in the manager's reason are collapsed to one line break before filing (`_file_one`). Pin: `test_a_blank_line_in_the_reason_does_not_cut_what_088_prints` (088's `_reason_of` now returns both lines). Break test: without the collapse it returned only "Left at 20:30". Fails, restored.

**F2.** A `rows` string that is not JSON gives "The days could not be read. Reload the page and try again."; a `day` that is not a date gives "That day was not understood. ..." (both plain sentences). Pin: `test_a_broken_payload_or_day_gets_a_sentence_not_a_traceback`. Break test: the `rows` part fails with the raw JSON error without the guard. **The bad `day` line was not broken separately** (not checked on its own).

**P4 (reviewer).** The deadlock proof test now asserts the row before the fault is `ok` and filed, and the faulted row is not. Break test: forcing `ok` to False with a sentence (which the old test accepted) fails the new assert. Restored.

**Subtract.** Deleted the "50 at most in one send, the first 50 go now" line and the `Math.min(n, 50)` in `hdlBar` (a page holds at most 50 rows, so over 50 ready can never happen). No test pinned it. **AC-44 is moot.** Added: `from` and `to` in the `held_days` answer (two dates, for the "All days" option); CSS for the empty block and day headings (three small rules, existing values).

**Empty Held view (reviewer P3, prototype-v2 `listHtml`).** The Show box is now drawn from every answer, so it can never keep the old day counts. The empty block reads "Nothing is held on {day}." + "No held day without a request is waiting for you. When somebody forgets to punch, the day shows up here." + primary "Show {other day}" (when another day has rows) + "See everything". The Held chip stays while the view is open, with a count of 0. No count line or send bar when nothing is held. Pin: new checks in `portal_held_team_086_test.js`; break test (Show box only when there are rows) fails the box check. Restored.

**The six wording and icon differences (reviewer m-2), each now as in prototype-v2:**
1. "Change to leaving / Change to arrival" as text -> visible "Change", the full words in its `aria-label`.
2. Three punches: "What time was the missing punch?" -> "Where is the missing punch?"; "Choose where the missing punch goes" -> "Show the punches and tap the gap".
3. "Punches on this day: ..." -> "Punches: ... · Shift 09:00-18:00" (shift only when the day has one).
4. The Held label on each row now has the warning triangle (the chip's own icon).
5. "All days" mode now has a day heading above each day's rows.
6. "All days in this period" now carries the dates, "(21 Aug to 21 Nov)" in the browser's own short-date order. v2's sample reads "1 to 20 Nov"; the month is not merged, so the text can read slightly longer. Not left as a difference Surbhi should decide: it is the same information.
Not touched: D-4 and P-1 to P-6 differences Surbhi already approved.

**Seven dimensions, against the code as it now is.**
| Dimension | Round 1 | Now | Why |
|---|---|---|---|
| Performance | degrades (send scanned the whole request table per row) | **improves** | no table scan, no lock on it; 50 rows took 2.9-3.7 s with three managers at once (unmeasured alone this round) |
| Security | improves | neutral to round 1 | F1 closes the paragraph-forging gap; F2 gives sentences, no traceback; day-row lock and scope check unchanged |
| Reliability | degrades under concurrency | **improves** | 0 deadlocks in 12 concurrent sends; answer matched the database both ways |
| Scalability | degrades (claim "sorted order, no deadlock" was false) | **improves** | one row locks one person-day only; the sorted-order comment is now true |
| Maintainability | neutral | neutral | one regex line, one try, one fewer branch in `hdlBar`; the `_refusal_of` change is the only reach beyond the slice |
| Data integrity | improves | improves | reason printed by 088 is the whole reason the manager typed |
| Compliance / privacy | improves | neutral to round 1 | answer and logs unchanged (no reason in the Error Log); the two new sentences hold no personal data |

**Test results this round (stack alv086-bench, site test_site):** see the table at the end of this section.

**Known gaps.** The bad-`day` branch of F2 has no break test of its own (temporary debt; one more assertion removes it). Browser check of the empty view is in the table. Day-row lock is now tested (`TheDayLock`) - the round 1 "temporary debt" is closed. Throwaway data removed: 150 test employees, their days and requests, the three test managers, Error Log rows; the temporary `default_site` is put back.

**Test table, fix round 2 (all run here on alv086-bench, one module at a time, final code 62bd524e + d7937ad8; the line shows every "Ran" summary the module printed):**
| Module | Result |
|---|---|
| test_held_team_086 | 33 tests OK (31 before + 2 new pins) |
| test_held_team_086_proof | 11 OK |
| test_held_day_085 | 45 OK |
| test_punch_fix_087 | 134 OK |
| test_punch_fix_087_proof | 11 OK |
| test_register_notice_088 | 80 OK |
| test_attendance_correction | 148 OK + 19 OK (second batch) |
| test_employee_documents_078 | 20 OK |
| test_field_app_password_signin_128 | 59 OK |
| test_leaver_report_089 | 47 OK |
| test_portal_security_010 | 45 OK + 5 OK (second batch) |
| DOM runner | 29 run, 0 not run, **1 failed: `portal_leave_063_test.js` "R-88: should not show <15>"**. Not mine: the same failure on a clean checkout of origin/dev 0a181d05, and I did not touch that file or the leave screen (inferred: it looks for the text "15" on a page that shows a date or time; not investigated). The 086 DOM test: 27 passed, 0 failed |
| check_design_system, check_brand_spelling, check_app_integrity (1,031 checks), check_portal_trays.js --static (33 fixed elements, 0 problems) | all OK |
| check_scope_traps.py | OK in the container (its Python is 3.14, not 3.12; it cannot parse on the host's 3.9). Ran against the app and the bench's hrms folder, not the repo's own `hrms/` copy |

**Browser, headless Chrome at 360 px, the real portal on this stack, a manager with two held days (screenshots read: `.../scratchpad/shots086b/360_*.png`):** the Held view opened on the latest day with the Show box and the (2) count; wording and the shift on the Punches line as listed above; after sending the last rows of a day, the Show box redrew with new counts, the Held chip showed 0, and the empty block read "Nothing is held on 21 Nov 2026." with "Show 20 Nov 2026" and "See everything"; the next day opened with the 3-punch row asking "Where is the missing punch?" and "Show the punches and tap the gap"; "All days" showed the period. No sideways scroll, no script errors. Not browser-checked: the day headings in "All days" mode with more than one day (the DOM test does not cover them either; read from code only), 1280 px, and the Hindi words.

**Cleanup:** gunicorn, `bench serve` and the port forward `alv086-fwd` stopped; the stack's assets folder and common config put back; test employees, days, requests, users and Error Log rows removed (employees back to 53, requests 0). The alv086 containers were already running when I started and are left running.
