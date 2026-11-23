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
