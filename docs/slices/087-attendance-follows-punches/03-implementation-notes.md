---
slice: 087-attendance-follows-punches
artifact: 03-implementation-notes
worktree: /Users/mac/hr-app/.claude/worktrees/087-attendance-follows-punches
branch: slice/087-attendance-follows-punches, built on 50ae6da8 (ALV-411/412) via a72bd6ce; last commit c83510d6 (notes may be one commit later)
status: PART 1 (server) built and tested locally; PART 2 (screens) built, not seen in a browser. Nothing pushed.
---

# 087 implementation notes

## 0. Bad news first

1. **The screens (Part 2) are built but never seen in a browser.** The JavaScript passes `node --check`, the kind rule passes a node table check (`scripts/087_kind_table_check.js`, 6 of 6), and the server data behind them is tested. Nobody has looked at them at 360 px, with a screen reader or in dark theme. AC-1, AC-96, AC-97 and AC-99 are therefore NOT met until that is done.
2. **Surbhi's build decisions of 21 Nov are built (commit c83510d6):** (1) a day that was Held keeps 085's arrear path: approval is allowed on a final slip, the slip is never touched, `slip_final` is returned and `released_after_final_slip` still shows; a day that was not Held on a final slip is refused (`punch_fix.py` `day_state`). (2) Release fields only on Held days (unchanged). (3) `send` refuses a note on a Held day (PRIV-2) and the sheet has no note box for one. `test_ac18` is back to 085's expectation.
3. **The four screen differences are built as drawn**, but still not seen in a browser: strip on the HR card, the note as a box on the card (not a browser prompt; Decline with no reason opens it and says "Write a reason so X knows what to do next."), the real-status toast ("Approved. 14:40 was added. The day is now Present."; "...The day stays Held."), and the time sentences in the browser.
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
| P9 HR card: Now beside If approved with strips, times line (added in bold with +, set-aside struck through), Approve, Decline, "Add a note for X", See their month, caption | Built as `acPfCard`; note box on the card; no known difference (not seen in a browser) |
| P10 own day / P11 final slip / left | Built (own day: lock line and no buttons; slip or left: Decline only) |
| P12 queue empty | Existing "Nothing waiting" behaviour |
| P13 strip (shift band, dots, worked bars, aria-hidden) | Built on the employee sheet only |
| P14 Hindi, dark theme, frames | Hindi: English only. Dark theme: uses the same tokens as the prototype, not looked at |
| P15 "Not about a punch?" link | Built; opens today's reason form |
| P16 Inbox Review | Built |
| N1 to N4 | Built, including the real-status toasts (N3) |

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

Last full runs, on c83510d6:
- `test_punch_fix_087`: 78 tests, all OK (whole file).
- `test_held_day_085`: 44 run, 6 failed: exactly the 6 baseline names (backfill tests, script path missing in the bench). `test_held_slip_085` 6 of 6 OK (test_ac18 at 085's expectation). `test_held_p1_machine_accounts_085` 3 of 3. `test_security_alv411_412` 9 of 9.
- Earlier run (dbc4f82a), not repeated: `test_attendance_correction` 148 run, 3 failures that also fail on a72bd6ce; `test_portal_security_010` 13 Individual Goal/KPI import errors (known).

Break tests (a change in the code, one test, watched fail, restored; worktree back at f4155b1c clean):
| Control undone | Test that failed | Failure |
|---|---|---|
| door check in `before_submit` | `test_desk_submit_is_refused_and_the_control_works_through_decide` | Desk submit not refused |
| marks guard (`guard_marks`) | `test_marks_cannot_be_written_outside_an_approval` | write not refused |
| `_punches` set-aside filter | `test_punches_skip_a_set_aside_punch_and_nothing_else` | 3 != 2 |
| limit flag (restore the `_has_time` early return) | `test_the_monthly_limit_counts_ordinary_day_fixes_and_not_held_day_ones` | 4th request not refused |
| HR-only (both checks) | `test_a_login_with_the_submit_right_but_no_hr_role_is_refused` | PermissionError not raised |
Added on c83510d6, same method: Held day on a final slip must be approved (control restored to block it: the test errored with the slip refusal); a day that was not Held on a final slip must be refused (slice-rule removed: not refused, test failed); no note on a Held day (check removed: not refused, test failed). Worktree back at c83510d6 clean.
Not break-tested: own-day locks, scope, exactly-once, the preview-equals-result test, the engine check, the ALV-410 test.

Dry run `scripts/087_dry_run.py` on test_site only, 60 days: 34 days read, 0 moved, 0 set-aside punches on the site. With nothing set aside the filter is the identity by construction, so this proves little; it must be run on ppj.dev or a DTC copy (Surbhi's word) before main.
Integrity check passes (1002 checks).

## 7. The two-push split (D1)

- **Push 1 = server side:** 6447828b, 904bda32, 081d1a26, 571c4481, 9ba2f0d3 (plus the docs commit d57c65f8). HR keeps approving with the old screen, which now sends the token. One part of the Inbox change (Review) is in push 1.
- **Push 2 = screens:** f4155b1c (day sheet, sheets, send bar, HR card, `day_sheet` endpoint, CSS) and dbc4f82a (a one-line fix). `day_sheet` and `card` extras live in `punch_fix.py`, which is also in push 1, so push 2 cannot be a clean cherry-pick of files; split by commit.

## 8. Not done / known gaps

Listed in section 0 (items 1, 3, 4, 5) and section 6 (not break-tested). Also: Hindi (English only); the report "Punch fixes this month" not opened in a browser; ALV-404 not fixed or touched (a lone OUT punch still gives Absent in `hold_odd_punch_day`).

## Merge note: ALV-402 (from the 085 session, 21 Nov 2026)

ALV-402 counts a punch after midnight on the right day. It is committed as 13743380 on fix/alv402-midnight-punch, not pushed, and waiting for Surbhi. It changes the same `_punches` in payroll_rules_apply.py as this slice:

- it reads this day and the next with `fields=["time","shift_start"]`, and keeps a row only when `getdate(r.shift_start or r.time) == date`;
- it then calls `punch_minutes(times, day=date)`, which in payroll_rules.py adds 1440 for each calendar day past `day`.

**Whichever lands second:** keep 087's `alvoraa_fix_aside_request is not set` filter, and take ALV-402's two-day time range and its shift_start check.

## 9. Fix round 1 (after 04-test-report, rebased on dev 13743380; code at the commit before this note)

1. **P1 cut-off text.** `.pfx{white-space:normal}`; the sheet no longer inherits `nowrap` from its table cell. Only checked by reading the CSS. **Not re-seen in a browser** (the test engineer's harness is not mine).
2. **AC-27.** The card says "X says: Back in after a break at 14:40. Also says 17:50 is wrong." (set-aside only: "X says the punch at 17:50 is wrong."). The If-approved side keeps the set-aside time, struck through, and the strip marks it as set aside. Server: `card` flags `ticked` and adds the ticked punches to `after.punches` with `aside`. Test: `test_the_card_carries_the_after_times_the_shift_and_the_machine_note`.
3. **AC-35.** Measured with the test engineer's own test: 50 cards, 1,232 queries and 1.2 s per call before; **222 queries and 0.14 s after**. Causes: each card read the same rows again (the request, the employee, the day, the punches twice, leave, slip, the day's logs twice) and `to_review` also built the old 085 preview per row. Now `card_context` reads all of it once for the whole list and `card` works from memory; the old preview is made only when the card cannot be. What is left per card is about 5 queries inside Frappe's `Shift Type.is_half_holiday` (holiday list per employee), which I did not touch. The old estimate of 8 per card was wrong.
4. **Class collision.** All 087 classes and ids renamed `pf-` to `pfx-` (the old planner owns `.pf-bar`, `.pf-card`, `.pf-sub`). Checked by grep: the planner's rules are untouched. Not re-seen in a browser.
5. **Hollow test** `test_still_odd_stays_held_and_hours_are_written` deleted; `test_ac48_...` in the proof file replaces it.
6. **Prototype parity (P3).** HR note label now "Note for X (optional)", and "Why not? X will see this." when a decline has no reason; the "Shaded band: shift 09:00-18:00. Dots: punches." caption is under every card variant. **For Surbhi:** gap rows are 44 px as the prototype draws them; AC-96 says 52. Not changed. Also not built: the card's "· N min late" in the Present line (the day has a late flag, not minutes).
7. **ALV-402 rule in 087's reads** (agreed with the 085 session). `held_day._day_logs` and `punch_fix.day_punches` now read the day and the next and keep a punch when `getdate(shift_start or time) == date`, keeping the `skip_auto_attendance = 0` and `offshift = 0` filters in `_day_logs`. `_check_aside` uses the same rule. `worked_out` keeps its night-shift +1 day nudge for an HR-supplied time; `worked_out` also takes an optional `logs` list. With the rule, a punch added after midnight on a night shift is read back from the real punches, so the old "weak proof for a night punch" special case in `apply` is gone. The card sends `m` (minutes from the start of the day, over 1440 after midnight) so the strip puts a 00:00 departure after the evening punches. Tests: `NightShift` in `test_punch_fix_087.py` (3 punches on day 1 with a 00:00 on the next date: the card lists 3, `worked_out` out time is 00:00 next day, preview equals result). **Break-tested:** the rule undone in `_day_logs` fails the test (2 != 3); undone in `day_punches` fails it (2 != 3).
8. The `_punches` merge: I read ALV-402's two-day range, `shift_start` check and `punch_minutes(day=)` together with the aside filter in `payroll_rules_apply.py`: the aside filter sits in the query filters and the date rule runs after it, so a set-aside punch is out before the day is chosen. Looks right; the 085/402 tests pass.

Tests this round (bench test_site, one at a time, code 694f0b91): `test_punch_fix_087` 79 of 79; `test_punch_fix_087_proof` 11 of 11; `test_midnight_punch_alv402` 5 of 5; `test_held_slip_085` 6 of 6; `test_held_p1_machine_accounts_085` 3 of 3; `test_security_alv411_412` 9 of 9; `test_company_scope_085` 20 of 20 (run one commit earlier); `test_held_day_085` 44 run, the 6 known backfill failures (run one commit earlier); `test_attendance_correction` 148 run, the 3 known holiday failures.

## 10. Counsel's two conditions (ALV-418, ALV-419), built, NOT RUN

Written without the bench (Surbhi was using it). **Nothing in this section has been run**: not the new tests, not the changed old ones, not the screens. Integrity check and `node --check` only. Commit follows the one in section 9.

**ALV-418, a reason on every request (reverses PRIV-2 and decision 3).**
- `punch_fix.send`: an empty or blank reason is refused on every day ("Say why, so HR can decide. A reason is needed on every request."); the old Held-day note refusal is gone.
- `attendance_correction.raise_correction` (held path, the 085 form) and `raise_for_report` (held and ordinary) refuse an empty reason; the auto-picked "Forgot to Punch In/Out" still holds no text. `raise_for_report` asks after its permission and window checks so those refusals still come first.
- Screens: one required reason box in the send bar (also on a Held day; label "Reason (required). HR and your manager can read this."), the add sheet no longer has a note box; the 085 held form (managers' route) has the box and `acHeldSubmit` sends it as `explanation`. Client check "Write a reason so HR can decide."
- 085 docs on this branch marked "reversed by counsel, 21 Nov 2026 (ALV-418)": 01b, 01c, 02 (AC-28, traceability row, parity table note), 06. 087 spec and 01b have a new counsel section (AC-101 to AC-107).
- **Open for Surbhi:** an employee's own ordinary request (no time) still takes the reason from the dropdown and an explanation only for "Other". I did not change it.

**ALV-419, Confirm.**
- Three new Custom Fields on Attendance Request (now 11 fields in `punch_fix.FIELDS`): `alvoraa_needs_confirm`, `alvoraa_confirmed_by`, `alvoraa_confirmed_on`.
- `punch_fix._own_the_confirm_fields` (inside `validate`): on a new request `alvoraa_needs_confirm = 1` unless the filer is the employee or Administrator; on every edit all three fields are put back to what is stored. **Administrator is the one exception** (it is not a person filing for somebody; needs Surbhi to accept). A client cannot write them.
- `punch_fix.refuse_unconfirmed` is in `before_submit` for EVERY request (so `decide`, Desk and REST all refuse), before `punch_fix.before_submit`. Decline stays open.
- `punch_fix.confirm(name, ok, reason)`: POST, employee only, own request only, once. Confirm stamps `alvoraa_confirmed_by` and `alvoraa_confirmed_on` (db_set after the ownership check; no `ignore_permissions`). Not right needs the employee's reason and declines it with the existing reviewed-by, on and note. Ids-only log line.
- `day_sheet` returns `needs_confirm` and `filed_by` ("HR" or "manager"); the sheet shows "HR sent this for you. Is it right?" with Confirm and Not right (reason box, required). The HR card shows "Waiting for X to confirm" with Decline only (`card.awaiting_confirm`). The Inbox does not show it (smallest thing that works).
- Parity: **new, needs Surbhi's yes**, not in prototype-v2: the Confirm block and the reason box in the send bar (prototype has the note inside the add sheet).
- **Known gaps / risks:** (1) an employee with no login can never confirm, so a request filed for them waits for ever (fails closed; HR can decline it); (2) requests already waiting from before the migrate have no flag and need no Confirm (no backfill); (3) **expect other test files to fail on the bench**: any test that files a request as a named user other than the employee (a manager, HR) and then approves it now needs a Confirm. I changed the helpers I own (`PunchFixCase.decide`, the 085 `_approve`s) and added an explanation to the `raise_for_report` calls in `test_attendance_correction.py` and `test_held_day_085.py`; I could not find the rest without running. Look first at `test_attendance_correction`, `test_attendance_doors_085`, `test_decline_scope`, `test_inbox_parts_042`, `test_company_scope_085`, `test_leave_063_rules`.

**Tests written (not run):** `ReasonOnEveryRequest` (3), `Confirm` (8) in `test_punch_fix_087.py`; changed: the send tests, the field count (11), the proof file's send payload. **Break tests planned for when the bench is free:** (a) remove `refuse_unconfirmed` from the hook list: `test_approval_is_refused_until_the_employee_confirms_then_works` and the Desk test must fail; (b) remove the reason check in `send`: `test_send_needs_a_reason_on_an_ordinary_day_and_on_a_held_day` must fail; (c) remove the held-path reason check in `raise_correction` and in `raise_for_report`: the two matching tests must fail; (d) let a client write the fields (drop `_own_the_confirm_fields`): `test_a_client_cannot_write_the_confirm_fields` must fail; (e) drop the ownership check in `confirm`: `test_only_the_employee_can_confirm...` must fail.

## 11. Counsel's two conditions: run (bench test_site, code b8c488c6)

- `test_punch_fix_087` 89 of 89 OK (incl. `ReasonOnEveryRequest` 3 and `Confirm` 8). `test_attendance_doors_085` 16 of 16. `test_punch_fix_087_proof` 11/11, `test_held_slip_085` 6/6, `test_held_p1` 3/3, `test_security_alv411_412` 9/9, `test_decline_scope` 11/11, `test_inbox_parts_042` 32/32, `test_company_scope_085` 20/20, `test_leave_063_rules` 43/43, `test_attendance_correction` 148/148 (all run at 2248745b; the fixes below came after).
- Broken by my change and fixed: 4 of my own new tests (they filed a second request on a day that already had one, or used a manager login the fixture cannot give an insert right to); `test_raiser_cannot_submit_but_a_colleague_can` in `test_attendance_doors_085` (HR-filed, so it now needs the worker's Confirm before the colleague approves: the test checks the refusal, confirms, then approves); `test_a_held_request_sent_from_the_portal_carries_only_the_time` in `test_held_day_085` (the explanation is now the reason plus the stamp; run singly after the change: see report). `test_held_day_085` otherwise: the 6 known backfill failures.
- **Break tests (all 6 watched fail, restored, worktree clean):** `refuse_unconfirmed` off; `send` reason check off; `raise_correction` held reason off; `raise_for_report` reason off; confirm fields not owned by the server ((0, hr login, time) != (1, None, None)); `confirm` ownership off.
- **Text running off the edge on the 085 sheet:** the cause is `.ac-tbl td{white-space:nowrap}`; the opened day is a cell of that table. 087's first fix (`.pfx{white-space:normal}`) covered only 087's block, NOT the 085 held box, the "Sent to HR" card or the ordinary form. Now `.ac-open td{white-space:normal}`, which covers the whole opened day. Checked by reading the CSS only, not in a browser.

## 12. Section 10's open questions: DECIDED (Surbhi, 21 Nov 2026, spec commit 659a1c2d, all five as recommended)

1. Administrator-filed requests need no Confirm (the break-glass account). **Decided.**
2. An employee with no login cannot confirm; the request waits until HR declines it; HR files only for staff with a login. **Decided.**
3. Requests already waiting before the migrate carry no Confirm flag; no backfill. **Decided.**
4. An ordinary request without a time keeps the dropdown reason, free text only for "Other". **Decided.**
5. The Confirm block and the reason box in the send bar are new screens; her yes is asked once they can be seen working. **Still waiting for her yes on the screens.** Prototype-v4 exists (file in this folder, parity rows P-1 to P-19 and V4-1 to V4-6 in 01b) and is waiting for her yes: **not built to, on the coordinator's word.**

## 13. Prototype-v4 built (21 Nov 2026; Surbhi approved v4; decisions in the spec, last section)

**Server** (`punch_fix.py`): `confirm(name, ok, reason, time)`: Not right with a time is a required time and a required reason; it declines the filed request and files the employee's OWN request for that time in the same transaction (savepoint; both or neither), linked by the new `alvoraa_replaces` field (12 fields now), which only the server can set (a process flag). The time gets the add sheet's checks (the replacement's own `validate`: day, repeat within 2 minutes, kind) plus "That is the time that was sent. If it is right, go back and press Confirm." A filed set-aside has no time and just declines. The replacement needs no Confirm and does not count against the monthly limit (`held_day.enforce_monthly_limit`, a one-line addition to 085's function, in both the early return and the count). `day_sheet` and `card` now carry the filer's name and kind, the filer's reason, the item, `confirmed_at`, `declined_by_you`, `replaces`. `home_rows` + `home_api._needs`: one Home "Needs you" row per request waiting for the employee.
**Screens** (`portal.js`, `next-home.js`, `panels.css`): the Confirm block with the item, the filer's reason, the truth line; Not right panel with the kind-based time label (Required), the changing consequence line, a required reason box; "You confirmed at ... · Waiting for HR" with no Withdraw; "You said this is not right ... Your reason"; "This replaces the 12:40 that HR sent. You said it was not right." with Withdraw; manager's name shown, HR's not; tags "Added by HR · waiting for you"; "Added by HR on 21 Nov. You confirmed it."; the HR card names the filer ("Anil Sample (HR) asked to add"), the clock line "Waiting for X to confirm" with Decline only, the tick line after Confirm, "Replaces the 12:40 that ... sent"; the send-bar reason with the v3 words ("Your reason", Required, the Q3 line, placeholder, one line growing to three, error with icon clearing on typing, help line left and Send right); the 085 held form has the same words; the Confirm block on the older non-punch request card (words only, no time field); a Home row with Check.
**Not built or different from v4:** the HR "Decided" list (P-18; no such list exists in the product); the older request card's block has no filer name or reason (the data is not on that card); Home's Check uses the same route as Fix and **did not move off Home in the preview build** (not investigated; Fix is the same code path); the time field on Not right is checked against the gap the sent time sat in, in the browser only.
**Found by looking at it:** the Confirm block's element ids were shared between the day sheet and "My requests" (two blocks on one page): now one id set per request. The time error stayed on screen after the time was corrected: now it clears on typing. Buttons had no outline in dark: added.

**Tests (bench test_site):** `test_punch_fix_087` 96 tests, run at e0fda343: 94 passed; the 2 failures (field count 12; a set-aside filed by HR, which the server never allows, so the test files it as Administrator) were fixed and the later full run is below. Also at e0fda343: `test_held_day_085` 6 known backfill failures only; `test_attendance_doors_085` 16/16; `test_security_alv411_412` 9/9; `test_attendance_correction` 148/148. **Break tests (all watched fail):** required time off (a different sentence came back, so the test failed on the words); same-time check off; no replacement filed (error); decline not rolled back; link not server-owned. The first try at the limit exemption passed with the exemption removed, because a replacement for a Held day is exempt anyway (HR and managers can only file a time for a Held day): the test now uses an ordinary day with the Confirm flag set by hand, and removing the exemption makes it error.

**Looked at in a browser** (Chromium through the relay on 18097, `bench serve` on 8097, test_site fixtures, 360 px and 1280 px, light and dark): `/Users/mac/hrlocal-data/087-screens/round3/` (about 100 screenshots, scripts and results JSON in the same folder). Measured: no horizontal scroll anywhere; smallest text 12 px; employee buttons 48 px, HR card buttons 44 px, Home buttons 44 px; no wrapping problem. Home was seen on `/hrms-employee-next`, which is behind `portal_preview` and System Manager; I set `portal_preview` for the run and gave the fixture employee that role by a direct row (the user save was refused: queue overloaded), then removed both. **Not seen:** a real phone, a screen reader, the keyboard open on the reason box, Check opening the day.

## 14. Rebased on dev bad23ce0 (21 Nov 2026)

Incoming: `10ff4518` (docs, 085 R2a/R2b/S-2/R1 accepted) and `bad23ce0` (ALV-402 screens and ALV-404: `shift_day()` in `payroll_rules_apply.py`, `hold_odd_punch_day` guards `in_time or out_time`, the month list, break, analytics and Home's punches grouped by shift day). Read first; they touch held_day (8 lines), payroll_rules_apply, attendance_correction, attendance_analytics, home_api and two test files.
**Conflicts (2 files, 4 hunks, all in the first of my commits that touched them):** `attendance_analytics.py` (my `punch_fix.counting_only` and import beside their `shift_day` import and two-day read: kept both) and `attendance_correction.py` month punch loop (their `shift_start` field and `shift_day()` grouping with my two fix-mark fields: kept both; the break times now group by `shift_day` inside my set-aside `else`, so a set-aside punch is still left out of the break). `payroll_rules_apply._punches` merged without a conflict: my aside filter sits in the query filters and their `shift_day(r) == str(date)` keeps the rows.
**One rule:** 087's own copies of the shift-day test (`held_day._day_logs`, `punch_fix.day_punches`, `_check_aside`, the card context) now call `shift_day()`. `_day_logs` keeps its `skip_auto_attendance = 0` and `offshift = 0` filters and my aside filter; `worked_out`'s night-shift +1 day nudge for an HR-supplied time is unchanged.

## 15. SEC-7 (from 086's review): a Confirm covers what the employee saw

**The gap (read in code, then proven by the break test below):** after the employee confirmed, the filer could still edit the request's time, set-aside, dates or words, because `_own_the_confirm_fields` only kept the confirm fields as stored. HR would then approve a changed request marked confirmed.
**Fix, chosen: clear, not refuse.** In `_own_the_confirm_fields`, once `alvoraa_confirmed_on` is set, a change to any of `from_date`, `to_date`, `alvoraa_missing_time`, `alvoraa_missing_log`, `alvoraa_set_aside`, `explanation`, `reason`, `half_day`, `half_day_date` (`CONFIRMED_CONTENT`) clears `alvoraa_confirmed_by` and `alvoraa_confirmed_on`, so the employee must confirm again and `refuse_unconfirmed` refuses the approval until they do. I did not refuse the edit outright because HR may need to correct a typo and nothing is lost by asking the employee once more. A save with no change keeps the Confirm. Note: the time field compares a stored time with a typed string, so a save that retypes the same time counts as a change and asks for a new Confirm (the safe side).
**Tests:** `test_a_confirm_is_cleared_when_the_filer_changes_what_the_request_says` (time, reason and set-aside, each: confirmed, filer edits, no longer confirmed, approval refused) and `test_saving_the_request_again_without_a_change_keeps_the_confirm`. **Break test:** remove the clearing lines and the first must fail, which is also the proof of the gap (see the report for the result).

## 16. Counsel, 21 Nov: manager additions need no Confirm

`punch_fix._own_the_confirm_fields`: `needs_confirm = 0` for the employee's own request, Administrator, and a manager (filer holds no HR role) whose request carries a time and no set-aside; 1 for HR and for everything else. A manager's ordinary (non-punch) request still needs Confirm (not an addition). Test `test_a_managers_addition_goes_straight_to_hr_and_an_hr_filing_still_waits` (manager add approved with no Confirm; HR filing flagged; manager set-aside refused). Spec: AC-113. Screens follow the flag, so nothing else changed. Existing waiting manager requests keep their flag. **Not run yet** at the time of writing; break test: make `manager_adds` always False and the test must fail.

## 17. Results of the rebase round (bench test_site, one chain, code f66abf4f; one test fixed after)

- `test_midnight_punch_alv402` 7/7 (includes the new ALV-402 screens test); `test_held_day_085` 45 run, the 6 known backfill failures only (includes `test_alv404_a_lone_out_punch_is_held_not_absent`); `test_held_slip_085` 6/6; `test_punch_fix_087_proof` 11/11; `test_attendance_doors_085` 16/16; `test_attendance_correction` 148/148 and 19/19; `test_punch_fix_087` 99 run, 98 passed (including the SEC-7 test), 1 error: my new manager-addition test (it filed on the wrong day and had the set-aside check in the wrong place), fixed in ac195902 and run singly: OK. The whole 087 file was NOT re-run after that fix. An earlier attempt at this chain ran twice at once (two launches) and produced lock errors; it was killed and the chain re-run alone.
- **Break tests (ac195902, all watched fail):** SEC-7 clearing off (the request stays confirmed after the filer changes it: this is also the proof of the gap); manager-additions rule off (needs_confirm stays 1); rule too wide (HR counted as a manager: needs_confirm 0 for HR).
- **Not done / pending:** the v5 build (approval never waits, disputes, before-payroll list, slip refusal, Workings flag, printed-reason hint) waits on the coordinator's spec; "Signed on the register" and its photo moved to slice 088 (a single seam function `record_register_signature` is the only thing 087 will keep). The Confirm gate and its screens are NOT touched further, as told, because Surbhi is changing the design.

## 18. V5 built (21 Nov 2026): approval never waits

**Rule now:** `alvoraa_needs_confirm` (HR-filed, or any cut; manager additions, Administrator and the employee's own request: 0) means "needs the employee's confirmation before pay is locked". It no longer gates approval: `refuse_unconfirmed` is gone, `card.awaiting_confirm` only drives the quiet line.
**Built (`punch_fix.py`):** `confirm` works pending or approved; Not right needs a reason, and a time when one was sent: pending = decline + the employee's own request (v4), approved = a NEW request (time) or a DISPUTE (no time, or a cut: `alvoraa_disputed_by/on/dispute_reason`, 3 new fields, 15 in all) and the day stays as approved. `withdraw_filed` (HR in scope, pending only, D-2). `unconfirmed_changes`, `before_payroll` (HR list, scoped), `refuse_slip_while_unconfirmed` (Salary Slip before_submit: names each change, the refusal wording of the prototype; withdrawn, declined, manager additions and own requests never hold it), `unconfirmed_text_by_employee` + one column "Unconfirmed change" in Salary Workings, Home rows for approved changes too. **The seam:** `record_register_signature(requests, notice)` declared, raises "not available yet". It matches 088's spec 8.5: same name and shape; `_own_the_confirm_fields` puts `alvoraa_signed_notice` back on every other save and the slip gate counts it as confirmed, both only when 088's field exists (`_signed_field()`); the day sheet reads confirm_state "signed" the same way. **OQ-5 answer: matched, nothing to change.** 088 must add the field as a read-only Link and `frappe.get_meta` must see it.
**Screens:** the Confirm block for pending or approved filed changes (HR-filed or cut: Confirm + Not right; manager addition: Not right only), confirmed and disputed states, the consequence line that says which of the three things happens, quiet line on the HR card (no gate), the before-payroll card (Not yet, Withdraw on pending only), the printed-reason hint on the send bar, Not right and the 085 held form (Hindi line in `translations/hi.csv`, machine-drafted; whether Frappe loads it for the portal page is not checked).
**Not built (moved to 088):** photo, register dialog, register fields. Not built: the "button tries the slip".
**Open for Surbhi:** HR cannot clear a dispute on an approved change from 087 (it cannot be withdrawn after approval, D-2), so it holds the slip until the employee confirms or 088 signs it.

**Tests (test_site, code 214ca513 / one fix after):** `test_punch_fix_087` 108 run: 107 passed; the 1 failure (the before-payroll test counted other committed fixtures) fixed, run singly OK. `_proof` 11/11; `test_held_day_085` 45 run, the 6 known backfill failures; `held_slip` 6/6; `doors` 16/16; `alv402` 7/7; `alv411_412` 9/9; `attendance_correction` 148/148. **Break tests (all fail):** slip refusal off; a withdrawn change also holding the slip; approval waits again; withdraw allowed on an approved change.
**Browser (360 px and 1280 px, light and dark, `/Users/mac/hrlocal-data/087-screens/round3/`, `v5_*_results.json`):** no horizontal scroll, text at least 12 px, buttons 44 to 48 px; employee blocks (pending HR, approved HR, approved manager, dispute, confirmed), Not right on an approved change (the line changes with the time), the hint, HR before-payroll card and the pending HR card with Approve always present. Found by looking: after approval a manager addition still said "HR decides this": fixed. Not seen: Home for approved rows (the row text was checked in code only this round), a real phone. The default Redis queue held 607 dead jobs on this local bench (no worker); I deleted that one list so fixtures could be made.
