---
slice: 087-attendance-follows-punches
artifact: 03-implementation-notes
worktree: /Users/mac/hr-app/.claude/worktrees/087-attendance-follows-punches
branch: slice/087-attendance-follows-punches, built on 50ae6da8 (ALV-411/412) via a72bd6ce; last commit dbc4f82a
status: PART 1 (server) built and tested locally; PART 2 (screens) built, not seen in a browser. Nothing pushed.
---

# 087 implementation notes

## 0. Bad news first

1. **The screens (Part 2) are built but never seen in a browser.** The JavaScript passes `node --check`, the kind rule passes a node table check (`scripts/087_kind_table_check.js`, 6 of 6), and the server data behind them is tested. Nobody has looked at them at 360 px, with a screen reader or in dark theme. AC-1, AC-96, AC-97 and AC-99 are therefore NOT met until that is done.
2. **Waiting for Surbhi (unchanged, not touched since the first report):**
   - (4) 085 released a Held day that sat on a final slip and told HR; 087 (SEC-5, AC-33) refuses it. I followed 087; `test_ac18` expects the refusal. `slip_final` in `decide` and `released_after_final_slip` on the day sheet cannot fire for a punch fix now.
   - (5a) Release fields (`alvoraa_release_how/by/on`) are written only for a day that was Held, not for every fixed day (AC-45), so the old "Held, now X" box never shows on an ordinary day.
   - (5b) The new `send` accepts a note on a Held day; 085's PRIV-2 says no reason box for a held day. The 085 session should confirm.
3. **Parity differences I made that Surbhi has not seen** (see section 4): Approve and Decline still use the old prompt box for the note, not the inline note drawn in P9; the server cannot know which gap was tapped, so the "not before / after / between" sentences exist only in the browser.
4. **Not done:** AC-81 (race with Frappe's `process_auto_attendance` in both orders), AC-35 (50 cards timed), AC-25 on ppj.dev, AC-43 test, AC-98 Hindi (English only by decision), AC-99 usability test, the D6 ticket.
5. **The dry run is a belt check only** (see section 6): 34 days read on test_site, 0 moved, no punch set aside anywhere. It has not been run on ppj.dev or a copy of DTC data.
6. **Resolved: AC-38 (Version row).** Frappe skips Version rows while `frappe.in_test` is true (`frappe/model/document.py` `_save`: `ignore_version = frappe.in_test`). With that switched off for the approval, a test shows one Version row owned by the approver. The earlier "no Version row" was the test run, not the code.

## 1. Rung of the ladder

Rung 4 (new code), one new module `punch_fix.py`, one small subclass, eight Custom Fields, one patch, one Script Report. No new DocType, app, job, queue, cache or index. The subclass is needed because stock blocks three things before any hook runs (spec 2.3).

## 2. What was built, per story (server side)

| Story | Built | Where |
|---|---|---|
| US-1/2 raise, kind, set aside | `send` (POST, own record), `derive` (kind from position and parity, the server's value is the one stored), repeat check within 2 minutes both ways, set-aside names checked (owner, day, still counting), lone set-aside leaving nothing refused. The server cannot know which gap the client tapped, so "is not before/after/between" sentences are not server side (client job, Part 2) | `punch_fix.py` `derive`, `validate`, `send` |
| US-3 states | Request keeps its states. Day-sheet words are Part 2 | not built |
| US-4 blocked days | `day_state` (left, unmarked, slip, leave incl. half-day, hand-marked, no shift) at raise and at approval, sentences from the spec, no leave type in any sentence | `punch_fix.py` `day_state`, `blocked_sentence` |
| US-5 card | `card()` returns now, if-approved, kind, token, blocked code, own-day flag, from the same `outcome()` the approval runs; `to_review` adds it per punch-fix row. The visual card is Part 2 | `punch_fix.py` `card`; `attendance_correction.py` `to_review` |
| US-6/7 approval, ALV-410 | `apply` (on_submit): set aside first, insert one punch as the approver, link it after insert (D7), re-read, assert read-back equals preview, write the day, before/after, engine must agree, refresh draft slip. One transaction | `punch_fix.py` `apply` |
| US-8 engine | `_punches` skips `alvoraa_fix_aside_request` only, guarded on the column. Month view (shown, marked, no break), analytics, team days, grooming also skip it | `payroll_rules_apply.py`, `punch_fix.counting_only` |
| US-9 one door | `decide(seen=)` token = sha1(request `modified`, day's punch ids); Desk submit refused in `before_submit` unless `decide` set a flag clients cannot send; Inbox row draws Review | `attendance_correction.py`, `punch_fix.before_submit`, `inbox_api.py`, `next-inbox.js` |
| US-10 who | HR role (HR User, HR Manager, System Manager) and `employee_in_scope`; D4: not_yours_yet gives managers "Only HR decides a punch fix." and HR no wait | `punch_fix.before_submit`, `not_yours_yet` |
| US-11 gates | `alvoraa_for_held_day` set by the server; limit and window read it | `punch_fix.validate`, `held_day.enforce_monthly_limit`, `refuse_own_day_outside_window` |
| US-12 marks | `guard_marks` on Employee Checkin validate and on_trash; cancel of an approved fix refused | `punch_fix.guard_marks`, `refuse_cancel` |
| US-13 once | `decide` reads the request `for_update`; day row locked in `apply` | see tests; the Frappe `process_auto_attendance` race test (AC-81) is **not written**, only "job after approval makes no second row" |
| US-15 | 8 fields from `after_migrate` and `after_install`; patch for old held requests; dry-run script `scripts/087_dry_run.py` **written, not run** | |
| US-17 | Subclass for the 3 stock blocks | `overrides/attendance_request.py` |
| AC-100 | Script Report "Punch fixes this month" | `report/punch_fixes_this_month/` |

## 3. The 085 session's eight conditions

1. Release fields still written: `punch_fix.py` `apply` calls `held_day._write_release` (`held_day.py` `_write_release`) for a day that was Held. **Deviation:** for a day that was not Held they are NOT written (AC-45 says always), because the old day-sheet box would print "Held, now Present" for a day that was never held. Needs Surbhi's yes or the Part 2 screen to word it.
2. Draft slip refreshed: `apply` calls `held_day.refresh_draft_slip`. A submitted slip is never touched: refused earlier (see 0.4).
3. Status from the shift thresholds through `worked_out`; `aside` argument added (`held_day.py` `worked_out`, `_day_logs`, shared `extra_when`).
4. `note_held_day` keeps: no longer held (for a request raised for a held day), multi-day (F3), no shift (also in `day_state`), no time (ordinary request on a held day). A time is allowed on other days.
5. No `release_on_machine_punch` for an approver (test `test_an_added_punch_never_triggers_...`); F1/R4 checks untouched; no `ignore_permissions` in `punch_fix.py` (a test greps for it).
6. `alvoraa_for_held_day` set by the server on insert from an existing Held row, never from the client; reset on edit; patch backfills old rows with `alvoraa_missing_log`; `_filed_by_hr` exemption unchanged.
7. PRIV-2 for held days: the old `raise_correction` held route is untouched (no note). **Conflict:** the new `send` accepts a note on a Held day too (AC-6 of the approved spec). The 085 session should confirm.
8. `test_held_day_085`, `test_held_slip_085` updated, none deleted. `test_held_p1_machine_accounts_085` passes unchanged (3 of 3). One 085 test replaced by two new ones (a time on an ordinary day is now a punch fix; a released held day is refused).

ALV-404 (lone OUT gives Absent in `hold_odd_punch_day`): **not fixed, not touched.**
ALV-410: fixed by inserting the real punch; `release_by_hr` deleted. Test goes red if the real punch is not there (fails closed), but I did not undo the fix to see it.

## 4. Prototype parity table

Built in `portal.js` (new block before `acHeldBox`), `panels.css` (appended, `.pf-` classes) and `punch_fix.py` (`day_sheet`, `card`). Not opened in a browser.

| ID | Status |
|---|---|
| P1 day sheet: one status line, muted shift line, strip, timeline with 44 px gap rows and 56 px punch rows, hint | Built. Row heights are in CSS, not measured |
| P2 add sheet: empty time field, "It will be added as: ...", note, "Add to request" | Built as a role=dialog bottom sheet, focus on the time, Escape closes. P2a: the note label says HR and the manager read it (Surbhi's Q3) |
| P3 "This punch is wrong" / "Keep this punch" | Built |
| P4 sticky send bar "+10:30 In · 11:15 set aside", "Nothing changes until HR approves.", Send to HR | Built. Sent keys are exactly date, time, set_aside, note. The server's sentence shows beside the button and stays; a network failure says "It may have gone through. Checking with the office." and reloads |
| P5 Waiting (dashed asked-for punch, Withdraw) / P6 Approved (added and set-aside lines, time still shown struck through) / P7 Declined with HR's reason | Built from `day_sheet`. The name of the HR person is never shown |
| P8 locked days (slip, leave, hand-marked) plus "not marked yet" | Built: sentence from the server, punches read-only, no gap rows |
| P9 HR card: Now beside If approved, strip-less times line (added in bold with +, set-aside struck through), Approve, Decline, See their month, caption | Built as `acPfCard`. **Differences:** no strip drawn on the card; Approve and Decline ask for the note in the old browser prompt, not an inline note box; "Add a note for X" link not built |
| P10 own day / P11 final slip / left | Built (own day: lock line and no buttons; slip or left: Decline only) |
| P12 queue empty | Existing "Nothing waiting" behaviour |
| P13 strip (shift band, dots, worked bars, aria-hidden) | Built on the employee sheet only |
| P14 Hindi, dark theme, frames | Hindi: English only. Dark theme: uses the same tokens as the prototype, not looked at |
| P15 "Not about a punch?" link | Built; opens today's reason form |
| P16 Inbox Review | Built |
| N1 to N4 | Sentences in place; the HR toasts still say "Approved — the day has been corrected." (the real-status toast N3 is NOT built) |

## 5. Seven dimensions, against the code written

| Dimension | Verdict |
|---|---|
| Performance | neutral. `_punches` gains one predicate and one cached `has_column`. Approval about 40 to 60 queries estimated, **not measured**. `to_review` does about 8 queries per punch-fix card (get_doc, punches, shift): **50 cards not measured**, AC-35 open |
| Security | improves: one door, HR only, scope, own-day (3 locks, 2 tested), marks guarded. New surface: `send` (POST, own record). Several tests not yet break-tested |
| Reliability | improves: one transaction, fail closed on preview or engine mismatch. Trap handled: pre-migrate column guards. Night-shift punch after midnight: read-back uses the preview for that case only (weak proof, declared) |
| Scalability | neutral, inline |
| Maintainability | degrades slightly: one module, one subclass, hot-file edits to `hooks.py`, `portal.js`, `held_day.py` |
| Data integrity | improves: day, punches, pay agree; before/after on the request. Risk D6 (ALV-291 clears `skip_auto_attendance` on set-aside punches): ticket, no code |
| Compliance/privacy | improves: ids and times only in the audit fields and logs; no photo or GPS key in any new payload (tested); no cache; release to main waits for counsel |

## 6. Tests (bench alv358-bench, site test_site, one module at a time)

Last full runs, on d57c65f8 / f4155b1c / dbc4f82a:
- `test_punch_fix_087`: 75 tests; 73 passed on f4155b1c, the other 2 (day-sheet tests that read the Time field) fixed in dbc4f82a and re-run singly: both OK. The whole file was not re-run after that fix.
- `test_held_day_085`: 44 run, 6 failed: exactly the 6 baseline names recorded before I touched held code (the backfill tests: script path missing in the bench). `test_held_slip_085` 6 of 6 OK. `test_held_p1_machine_accounts_085` 3 of 3 OK.
- `test_security_alv411_412` 9 of 9 OK.
- `test_attendance_correction`: 148 run, 3 failed (`test_a_holiday_in_the_range_pushes_the_reach_further_back`, `test_a_weekly_off_counts_the_same_way`, `test_a_holiday_pushes_the_boundary_further_back`). The same 3 fail on a72bd6ce, before any 087 code (run singly). Not mine.
- `test_portal_security_010`: 45 run, 13 errors, all "Module import failed" for Individual Goal / KPI (known site state).
- Not run: `test_held_gaps_085`; the browser.

Break tests (a change in the code, one test, watched fail, restored; worktree back at f4155b1c clean):
| Control undone | Test that failed | Failure |
|---|---|---|
| door check in `before_submit` | `test_desk_submit_is_refused_and_the_control_works_through_decide` | Desk submit not refused |
| marks guard (`guard_marks`) | `test_marks_cannot_be_written_outside_an_approval` | write not refused |
| `_punches` set-aside filter | `test_punches_skip_a_set_aside_punch_and_nothing_else` | 3 != 2 |
| limit flag (restore the `_has_time` early return) | `test_the_monthly_limit_counts_ordinary_day_fixes_and_not_held_day_ones` | 4th request not refused |
| HR-only (both checks) | `test_a_login_with_the_submit_right_but_no_hr_role_is_refused` | PermissionError not raised |
Not break-tested: own-day locks, scope, exactly-once, the preview-equals-result test, the engine check, the ALV-410 test.

Dry run `scripts/087_dry_run.py` on test_site only, 60 days: 34 days read, 0 moved, 0 set-aside punches on the site. With nothing set aside the filter is the identity by construction, so this proves little; it must be run on ppj.dev or a DTC copy (Surbhi's word) before main.
Integrity check passes (1002 checks).

## 7. The two-push split (D1)

- **Push 1 = server side:** 6447828b, 904bda32, 081d1a26, 571c4481, 9ba2f0d3 (plus the docs commit d57c65f8). HR keeps approving with the old screen, which now sends the token. One part of the Inbox change (Review) is in push 1.
- **Push 2 = screens:** f4155b1c (day sheet, sheets, send bar, HR card, `day_sheet` endpoint, CSS) and dbc4f82a (a one-line fix). `day_sheet` and `card` extras live in `punch_fix.py`, which is also in push 1, so push 2 cannot be a clean cherry-pick of files; split by commit.

## 8. Not done / known gaps

Listed in section 0 (items 1, 3, 4, 5) and section 6 (not break-tested). Also: Hindi (English only); the report "Punch fixes this month" not opened in a browser; ALV-404 not fixed or touched (a lone OUT punch still gives Absent in `hold_odd_punch_day`).
