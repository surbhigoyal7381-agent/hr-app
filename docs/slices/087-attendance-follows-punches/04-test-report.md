---
slice: 087-attendance-follows-punches
artifact: 04-test-report
code under test: branch slice/087-attendance-follows-punches at 2fab09a2 (code unchanged since c83510d6; the later commits are tests and docs only; 01c9f2e7 adds one more test)
bench: container alv358-bench, site test_site, mounted from worktree alv358-daily-workings, detached at 2fab09a2. Schema on the site: 087 custom fields present (setUpModule runs `punch_fix.after_migrate`).
verdict: ROUND 1 FAIL, ROUND 2 PASS WITH KNOWN DEFECTS (see section 0)
---

# 087 test report

Nothing here was run on devstack, production or ppj.dev. Fixtures are invented (example.com logins, "Hd..." names). The browser fixtures were committed to test_site and are still there.

## 0. Round 2 (re-test after fix round 1; code 694f0b91, branch HEAD eec1713c, on dev 13743380)

Bench: alv358-bench, test_site, worktree alv358-daily-workings detached at 694f0b91. Browser: same method as round 1 (bench serve + throwaway proxy, both removed). Screens: `/Users/mac/hrlocal-data/087-screens/round2/` (59 files, scripts in its `scripts/`). Fixtures are new synthetic ones (tag Hdd3f91), committed to test_site.

**Browser-only stand-ins (declared):** the server for the browser ran with two patches the tests also use, so the final-slip cards could be seen: `held_day.is_in_final_slip` and the list's slip read say "final" for two named employees; and the preview-page flag was on so the Inbox opens. No real Salary Slip was made.

### Round 1 findings, one by one

| # | Round 1 finding | Round 2 | How I know |
|---|---|---|---|
| 1 | P1 text cut off at 360 | **Fixed** | Ran it: 0 clipped text boxes on the employee sheet (held, night, leave, ordinary), the send bar and the HR cards, at 360 and desktop, light and dark; no horizontal scroll; send-bar text does not overlap the button. Screens `emp-leave-p360-light.png`, `emp-night-p360-dark.png` |
| 2 | P2 AC-27 missing | **Fixed** | Ran it: card says "Also says 17:50 is wrong."; set-aside-only card says "says the punch at 12:30 is wrong."; the time is struck through on both Now and If approved |
| 3 | P2 AC-35 queries | **Fixed** | Ran it: `test_ac35_...` 50 cards: 0.20 to 0.36 s per call (before 1.17 to 1.41), 222 queries (before 1,232) |
| 4 | P2 bars 8 px low | **Fixed** | Ran it: bar centre minus dot centre = 0 px in every state I read. (Two cards read 154 px: my script compared the first bar and dot of two different strips, the Now strip has no bar; I treat it as a script artefact) |
| 5 | P2 hollow test | **Fixed** | `test_still_odd_...` is gone; `test_ac48_...` stays (passes) |
| 7 | P3 prototype differences | **Fixed except gap rows** | Note label "Note for X (optional)"; "Why not? X will see this." when declining; "Shaded band: shift ... Dots: punches." caption on every card variant. Gap rows are still 44 px (AC-96 says 52): for Surbhi |

### New checks, round 2

| Check | Result |
|---|---|
| Night-shift day, 09:00, 12:00 and a 00:00 punch on the next date | Pass: the sheet lists 09:00, 12:00, 00:00 in that order and draws 00:00 at the far end after the evening. Server: `NightShift` tests in test_punch_fix_087 (79 of 79) |
| Note box: ordinary day's add sheet has "Note (optional). HR and your manager can read this."; Held day's has none | Pass (AC-89, PRIV-2) |
| Final slip, Held day | Pass: card keeps Approve; real approval click: toast "Approved. 12:40 was added. The day is now Present. The day is in a slip that is already final, so the slip was not changed. Add an Additional Salary to pay it." (with the stand-in above) |
| Final slip, day that was not Held | Pass: card shows only Decline and "Since this was sent, the day went onto a salary slip that is final..." (with the stand-in above). The server refusal of an Approve is covered by the unit tests, not clicked |
| Leaver | Pass: Decline only, "This person has left, so no punch can be added. Decline it and say why." |
| Decline with no reason | Pass: no call sent, label "Why not? X will see this.", focus in the box, "Write a reason so X knows what to do next." |
| Approve payload and toast on an ordinary Held card | Pass: `{name, approve:1, note:"", seen:<token>}`; "Approved. 12:40 was added. The day is now Present." |
| Own-day card | **Not seen.** The HR person's own request is filtered out of their own queue, so the lock line can never be reached from the queue. Server tests (own-day locks) pass. Not a defect; the line may be dead text |
| Empty queue | Seen: the "waiting for you" section is hidden, nothing is drawn. Same as before 087; the prototype's P12 empty message is not drawn on this page |
| Inbox Review (AC-65) | **Partial.** In the preview Inbox, punch-fix rows show "Review" with no Approve; ordinary requests still show Approve and Decline. But "Review" lands on `#time/fix`, which in the preview frame is a placeholder ("the screen itself arrives in a later wave"). The card cannot be reached from the Inbox there |

### Modules, round 2 (one at a time, both batches read)

| Module | Ran | Result |
|---|---|---|
| test_punch_fix_087 | 79 | OK |
| test_punch_fix_087_proof | 11 | OK |
| test_midnight_punch_alv402 | 5 | OK |
| test_held_day_085 | 44 | 6 failed, the 6 known backfill names |
| test_held_slip_085 | 1 + 5 | OK |
| test_held_p1_machine_accounts_085 | 3 | OK |
| test_held_gaps_085 | 6 + 1 | 3 failed, the 3 known names |
| test_security_alv411_412 | 9 | OK |
| test_attendance_correction | 148 + 19 | 3 failed, the 3 known holiday / weekly-off names (on the re-run) |
| test_company_scope_085 | 20 | OK |
| test_attendance_doors_085 | 16 | OK |
| test_portal_security_010 | 45 + 5 | 13 errors, the known Individual Goal / KPI import errors |

**One flake to watch (P3).** In the first full run of test_attendance_correction at 694f0b91 there was a 4th failure: `test_blank_costs_no_holiday_or_employee_read_and_a_long_list_costs_no_more` (19 statements != 23, a query-count test). It passes alone at 694f0b91 and at dev 13743380, and the full module re-run at 694f0b91 gave only the 3 known failures; the dev baseline gives the same 3. That first run was during a slow window (test_punch_fix_087 took 2,478 s against 316 s the round before, with other containers busy), so I treat it as timing or cache state, not a 087 fault. Not proven; if it returns, look at holiday-list cache state.

### Still open (unchanged, release gates)

Dry run on ppj.dev or a DTC copy (AC-59, OPS-12, OPS-18, PRIV-4); ALV-291 guard not built (OPS-19); AC-25 owner rule an assumption; AC-99 usability test; two-connection race untested; gap rows 44 vs 52 px (Surbhi); the Inbox Review link is a stub in the preview frame (AC-65); AC-3, AC-8, AC-31 and the other "not tested" rows in section 6 are unchanged by this round.

### Round 2 verdict

**Pass with known defects.** All round 1 blockers and P2 findings I raised are fixed and re-seen. No new failure that is 087's. The open items above are release gates and decisions for Surbhi, not test failures. Sections 1 to 11 below are the round 1 report, kept as the record; where they disagree with this section, this section wins.


## 1. Bad news first (round 1)

| # | Level | Finding | Evidence |
|---|---|---|---|
| 1 | **P1 blocks release** | **Sentences are cut off on a 360 px phone.** The new sheet sits in a table cell that says `white-space: nowrap`, and the `.pf-` text inherits it. Cut off: "It is covered by approved leave, so punches do not cha...", "Something missing? Tap a gap. Something wrong? Tap...", "One punch per request. If another is missing, send this...", and the send bar's "Nothing changes until HR approv..." runs under the Send button. The blocked-day sentence is the whole point of AC-20 to AC-23. Likely one CSS line (`.pf{white-space:normal}`), for the engineer. | Ran it. Computed style read in the browser: `P.pf-hint nowrap`, `DIV.pf nowrap`, `TD nowrap`. Screens: `emp-locked-leave-p360-light.png`, `emp-send-bar-p360-dark.png` |
| 2 | P2 | **AC-27 not built.** The card for a request that adds one punch and sets another aside has no "Also says 17:50 is wrong." line, and the If-approved side drops the set-aside time instead of showing it struck through. | `hr-decline-no-reason-p360-dark.png`; the string "Also says" is not in portal.js (grep count 0) |
| 3 | P2 | **AC-35: 50 cards cost about 1,232 database queries (about 25 per card).** The engineer's note estimated about 8. Time is inside the budget but close: 1.17 to 1.41 s per call against 1.5 s, on a Mac Docker bind mount (slower than a server). Predicted to be N+1: it grows with cards. | Ran it: `test_ac35_...`, 5 calls: 1.41, 1.17, 1.22, 1.22, 1.21 s; 1,325, 1,232, 1,232, 1,232, 1,232 queries |
| 4 | P2 | **Strip bars are drawn 8 px below their dots.** The old payroll planner already owns `.pf-bar` (margin 8px 0 6px). The new strip reuses the name, so its margin leaks in. Same collision on `.pf-card` and `.pf-sub`. Rename the new classes. | Ran it: computed margin `8px 0px 6px` on the new bar; bar centre 8 px under dot centre on the employee sheet and on both HR cards |
| 5 | P2 | **A test that could not fail.** `test_still_odd_stays_held_and_hours_are_written` asserts a status equals itself when hours are 4 or more. AC-48 had no proof. I added `test_ac48_...` and break-tested it. The old test should be deleted. | Read the code; break-test of the new one: 'Half Day' != 'Held' with the odd-count rule off |
| 6 | P2 | **Not done by the engineer and still open (release gates, not code I can write):** dry run on ppj.dev or a DTC copy (AC-59, OPS-12, OPS-18; PRIV-4); the ALV-291 guard (OPS-19, "D6 ticket"; the guard is not built); AC-25's Administrator-owner rule is still an assumption; AC-99 usability test. | engineer's notes section 0 and 6 |
| 7 | P3 | **Differences from prototype-v2** (not from the spec), listed in section 5: note label on the HR card; "Shaded band" caption missing; gap rows 44 px where AC-96 says 52. | measured |
| 8 | P3 | A Present day with 0 hours on the Attendance row reads "Present · 0h 00m" on the sheet. That is real data at DTC (ALV-355), so people will see it. My fixture rows also have no hours, so every Present day in my screens shows it. | Ran it |
| 9 | P4 | Existing page already shows the day's punches as chips above the new timeline, so the punches appear twice. | screens |

Known and not 087's (unchanged from the brief, names checked): 6 backfill failures in test_held_day_085, 3 in test_held_gaps_085, 3 holiday/weekly-off failures in test_attendance_correction, 13 Individual Goal/KPI "Module import failed" errors in test_portal_security_010. I did not find a new failure hiding behind them (I read the failing names in each module).

## 2. Commands run and numbers

All: `bench --site test_site run-tests --module alvoraa_portal.tests.<module>` in alv358-bench, one module at a time, nothing else running. Both batch summaries read for each.

| Module | Ran | Result |
|---|---|---|
| test_punch_fix_087 | 78 | OK |
| test_punch_fix_087_proof (mine, new) | 10 in the full run, 11 now | 10 OK in the module run; the 11th (AC-48) run alone: OK |
| test_held_day_085 | 44 | 6 failed, the 6 known backfill names |
| test_held_slip_085 | 1 + 5 (two batches) | OK |
| test_held_p1_machine_accounts_085 | 3 | OK |
| test_held_gaps_085 | 6 | 3 failed, the 3 known names |
| test_security_alv411_412 | 9 | OK |
| test_attendance_correction | 148 + 19 (two batches) | 3 failed: the known holiday / weekly-off names |
| test_portal_security_010 | 45 + 5 (two batches) | 13 errors, all "Module import failed" (Individual Goal 12, KPI 1) |
| test_company_scope_085 | 20 | OK |
| test_attendance_doors_085 | 16 | OK |
| `node scripts/087_kind_table_check.js` | 6 | 6 of 6 ok |

Integrity check: 1002 checks, OK. Full suite not run (usage rule: once, before release candidate).

## 3. Break-tests (the control switched off in the running process; no repo file edited)

Method: a script piped into the bench container; it re-defines one line (or replaces one function) in memory, then runs the named tests. Saved with the screens in `/Users/mac/hrlocal-data/087-screens/scripts/` (brk.py, runbreaks.sh). Control run (nothing broken): pass.

| Control off | Test(s) | Result |
|---|---|---|
| link line in `apply` (AC-81) | `test_ac81_approval_then_frappes_attendance_job`, `test_ac81_frappes_attendance_job_then_approval` | both fail: link None, skip flag 1 on the added punch |
| own-day: `refuse_own_decision` | `test_hr_cannot_approve_their_own_day_...` | fails, but only on the sentence: the third lock still stops it |
| own-day: checkin insert rule | `test_the_punch_insert_is_a_lock_of_its_own_...` and the first test | both fail |
| own-day: both of the above | same two | HR can approve their own day: both fail |
| scope: `employee_in_scope` alone | scope tests | **pass** (second line of defence: `_refuse_outside_scope` still refuses) |
| scope: `_refuse_outside_scope` alone | `test_an_hr_person_and_a_manager_outside_scope_...` | fails: another company's HR can **decline** (decline has no other scope check) |
| scope: both | same + `test_hr_of_another_company_is_refused` | fails |
| exactly once: "already decided" check in `decide` | `test_decide_twice_adds_one_punch` | fails on the sentence only: the stale-token check catches it first |
| exactly once: repeat check in `apply` | `test_exactly_once_a_stale_second_approval_...` | **passes** (the stock repeat-scan hook is a third layer) |
| preview equals result (read-back line) | `test_the_approval_refuses_when_the_day_does_not_come_out_as_the_card_showed` | fails |
| engine check line | `test_the_approval_refuses_when_the_pay_engine_would_still_hold_the_day` | fails |
| ALV-410: engine blind to the real punch | `test_alv410_an_approved_fix_is_no_longer_held_by_the_engine` | errors: the approval is refused ("pay engine would still hold this day"), fails closed |
| AC-43: window check | `test_ac43_...` | fails (a different refusal comes first) |
| AC-48: odd-count rule | `test_ac48_...` | fails |

Not provable in one connection: two people pressing Approve at the same instant (`for_update` row locks). **Untested control**: needs two database connections. Layers that do get tested: the "already decided" check, the stale token, the apply-step repeat check.

## 4. What the screens send (ran it, real browser, real server)

Browser: Playwright (installed in a scratch venv) driving Chromium against `bench serve` inside alv358-bench, reached through a throwaway proxy container (removed after). The bench's `sites/assets/alvoraa_portal` is an 18 Nov copy with no `ess` files, so the browser served the slice's own css and js from the worktree; nothing on the bench was changed.

| Action | Captured POST body | Verdict |
|---|---|---|
| Send to HR | `alvoraa_portal.punch_fix.send` `{"date":"2026-11-16","time":"12:40","set_aside":"[]","note":""}` | exactly 4 keys: pass (AC-4 keys; PRIV-1). The server takes this exact shape: `test_send_takes_exactly_what_the_screen_sends` |
| Withdraw | `{"name":"HR-ARQ-..."}` | pass |
| Approve | `attendance_correction.decide` `{"name":...,"approve":1,"note":"","seen":"<40-char token>"}` | pass (AC-63) |
| Decline with no reason | no call made | pass (AC-30) |
| Decline with a reason | `{"name":...,"approve":0,"note":"Please ask the guard...","seen":""}` | pass (AC-66) |

Toasts seen: "Sent to HR." (not captured in a screenshot, code path ran), "Approved. 12:40 was added. The day is now Present." and "Declined. The employee will see your reason." Both match the prototype wording. Real-status toast works (N3).

## 5. Prototype parity, per screen

Screens in `/Users/mac/hrlocal-data/087-screens/` (65 files): `proto-*` are prototype-v2; `emp-*` and `hr-*` are the built screens, each at p360 and desktop, light and dark. Looked at in full: emp-held-sheet, emp-add-sheet, emp-send-bar, emp-locked-leave, hr-card-held, hr-decline-no-reason at 360 (light and dark). The desktop and the other combinations were measured by script (no horizontal scroll, row and button heights, font sizes, colours load) and spot-looked at, not each read by eye.

| Prototype screen | Built | Parity |
|---|---|---|
| P1 day sheet (status line, shift line, strip, timeline, hint) | all present at 360 and desktop, dark colours load | **differs: text cut off (finding 1); strip bars 8 px low (finding 4); punches shown twice (finding 9)** |
| P2 add sheet (empty time, "It will be added as", focus, Escape, note) | role=dialog, aria-modal, focus on time, 16 px field, 48 px buttons, Escape closes, kind sentence "Back in after a break." | matches. No note box on a Held day (Surbhi's decision). The note box on an ordinary day's add sheet **not looked at** |
| P3 "This punch is wrong" / "Keep this punch" | "This punch is wrong ... crossed out, and stops counting once HR approves." then "Set 09:05 aside" | matches. "Keep this punch" not clicked |
| P4 send bar | "+12:40 In" / "Nothing changes until HR approves." / Send to HR | **differs at 360: text runs under the button (finding 1)**. Dark theme: the black button on a dark bar is weak (portal's own button style, not 087's) |
| P5 Waiting | "Sent to HR at 08:25 · Waiting", asked-for dashed punch, Withdraw | text cut at 360 (finding 1) |
| P6 Approved | "Fixed by HR · 8h 20m · Paid", "Added by HR on 21 Nov 2026, from your request." | matches |
| P7 Declined | "HR did not add this", "Reason from HR: ..." | matches (reason line may be cut at 360; not read) |
| P8 locked day | "This day cannot be fixed here" + sentence + no gap rows | **sentence cut at 360 (finding 1)** |
| P9 HR card | Now / If approved with strips, times line, Approve, Decline, note link, See their month, caption | **differs: no "Shaded band: shift ... Dots: punches." caption; AC-27 "Also says ..." missing; note label "Note for X. X will see it." where the prototype says "Why not? X will see this." on decline and "(optional)" on add** |
| P10 own day / P11 final slip / left | server tests only; **not looked at in a browser** | not tested in browser |
| P12 empty queue | not looked at | not tested |
| P13 strip | present, aria-hidden | offset (finding 4) |
| P14 Hindi | English only by decision | not built |
| P15 "Not about a punch?" link | present | matches |
| P16 Inbox Review | **not looked at** | not tested in browser |
| N1 to N4 | N3 real-status toast and decline-no-reason: looked at and matched. N1, N2, N4 | N1, N2, N4 not individually checked |

The prototype's primary colour is purple. The portal's is green (and black buttons). That is the portal's design system, not a 087 defect; I do not count it.

## 6. Coverage: every AC, one line each

`T` = test file `test_punch_fix_087` unless marked `P` (`test_punch_fix_087_proof`), `B` = browser run above. "Pass" means I ran it and it passed. "Break" means I watched it fail with the control off (section 3), or it was break-tested by the engineer (note 6 of 03), which I did not repeat.

| AC | Result | Proof |
|---|---|---|
| 1 | **Fail** | B: parts present; hint and sentences cut off at 360 |
| 2 | Pass | `Kind` six rows (T) + node table 6 of 6 |
| 3 | Not tested | client sentences for a time out of its gap: not typed in any run |
| 4 | Pass | B payload keys; `test_the_server_derives_it_and_ignores_the_one_sent` |
| 5 | Pass | B: gap rows gone, one-punch line shown (cut at 360) |
| 6 | Pass | `test_send_creates_one_waiting_request_for_the_callers_own_record` |
| 7 | Pass with finding 1 | B bar text |
| 8 | Not tested | server sentence beside the button: no refusal driven in the browser |
| 9 | Pass in part | B: empty time field not asserted, 16 px and focus yes; one-press-one-call not tested |
| 10 | Pass | B aside sheet words |
| 11 | Pass | `test_a_set_aside_that_leaves_no_punch_is_refused`; `P test_send_takes_exactly_what_the_screen_sends` (set-aside only) |
| 12 | Pass | `test_case_a_sets_the_wrong_punch_aside_and_it_stays_on_record` |
| 13 | Pass | `test_set_aside_names_must_be_this_employees_on_this_day_and_still_counting` |
| 14 | Pass with finding 1 | B waiting |
| 15 | Pass | B approved (a real approval through the card); `test_an_approved_fix_shows_added_and_set_aside_marks_to_the_employee` |
| 16, 17, 18 | Pass | `test_one_waiting_request_per_day_but_declined_and_approved_fixes_do_not_block`, `test_an_ordinary_declined_request_still_blocks_an_ordinary_one` |
| 19 | Pass | `test_case_a_...` |
| 20 | **Fail** | B shows the sentence, cut off at 360 |
| 21, 22 | Pass | `test_a_final_slip_blocks_a_fix_on_a_day_that_was_not_held_and_creates_nothing`, `test_a_day_with_no_attendance_row_is_not_fixable`, `test_send_for_a_blocked_day_creates_no_request` |
| 23 | Pass | `test_the_sheet_says_why_a_day_cannot_be_fixed_and_shows_the_request_state` |
| 24 | Not confirmed | half-day leave: `test_approved_leave_blocks_without_naming_the_leave_type` uses a plain leave; I did not read for a half-day case [inference only] |
| 25 | Pass, rule still an assumption | `test_a_hand_marked_day_is_not_fixable_and_an_auto_marked_one_is` on test_site; the scheduler's owner is not proven on ppj.dev |
| 26 | Pass | B card title and "says" line |
| 27 | **Fail** | finding 2 |
| 28 | Pass | B: "Still held · 1 punches · not paid" (note "1 punches"); `P test_ac48_...` (Break) |
| 29 | Pass | `test_the_preview_and_the_approval_come_from_one_function`; `P ...does_not_come_out_as_the_card_showed` (Break) |
| 30 | Pass | B; `test_a_declined_fix_changes_nothing_and_needs_a_reason_and_no_token` |
| 31 | Not tested | approve with a note; aria-describedby present in code only |
| 32 | Not tested in browser | server: `test_hr_cannot_approve_their_own_day_...` (Break) |
| 33 | Not tested in browser | server: `test_a_final_slip_blocks_the_approval_of_a_day_that_was_not_held_and_changes_nothing` and the Held-on-final-slip test, per Surbhi's amendment |
| 34 | Server only | `test_a_leaver_cannot_be_approved` |
| 35 | Pass on time, **finding 3 on queries** | `P test_ac35_...` |
| 36 | Pass | B caption under the buttons |
| 37, 38, 39 | Pass | `test_case_b_adds_one_punch_...`, `test_a_set_aside_leaves_a_version_row_naming_the_approver`, `test_only_the_ticked_punches_change` |
| 40 | Pass | `test_a_punch_within_two_minutes_of_a_counted_one_is_refused_both_ways` |
| 41 | Not tested | night shift; the engineer declares the read-back is weak there |
| 42 | Pass | `test_an_added_punch_never_triggers_the_machine_release_or_a_second_release` |
| 43 | Pass | `P test_ac43_...` (Break) |
| 44 | Pass | `test_no_ignore_permissions_and_no_cache_in_the_new_module` (a grep of the module) |
| 45 | Pass (as amended) | `test_case_b_...` (release fields on a Held day) |
| 46, 47 | Pass | `test_case_a_...`, `test_case_b_...` |
| 48 | Pass | `P test_ac48_...` (Break). The first file's test is hollow (finding 5) |
| 49 | Pass | `test_a_result_below_the_absent_threshold_is_absent` |
| 50 | Pass | `test_alv410_an_approved_fix_is_no_longer_held_by_the_engine` (Break, fails closed) |
| 51 | Pass | `test_alv410_the_typed_time_is_not_counted_twice` |
| 52 | Pass | `test_case_b_...` before and after |
| 53 | Pass | `test_the_draft_slip_is_refreshed_and_a_failure_does_not_undo_the_approval` |
| 54 | Pass | `P ...pay_engine_would_still_hold_the_day` (Break) |
| 56 | Pass | `test_a_failure_after_the_insert_leaves_nothing_behind` |
| 57 | Pass | `test_punches_skip_a_set_aside_punch_and_nothing_else` (Break by engineer) |
| 58 | Not tested | a list of readers in the notes, not code |
| 59 | **Not tested** | the dry run was a belt check on test_site (34 days, 0 moved); not run on ppj.dev or a DTC copy. Release gate |
| 60, 61, 62 | Pass | `test_decide_without_the_token_or_with_a_stale_one_is_refused`, `test_desk_submit_is_refused_and_the_control_works_through_decide`, `test_an_edit_of_the_draft_after_the_card_was_opened_makes_the_token_stale` (Break by engineer on the door) |
| 63 | Pass | B and `test_decide_twice_adds_one_punch` |
| 64 | Pass in part | `test_send_is_post_only`; `test_security_alv411_412` 9 of 9 for decide and the older calls. `day_sheet` is a GET and read-only |
| 65 | Not tested in browser | Inbox Review row |
| 66 | Pass | B decline payload |
| 67 | Pass | `test_hr_cannot_approve_their_own_day_...`, `test_the_punch_insert_is_a_lock_of_its_own_...` (Break) |
| 68 | Pass | `test_the_raiser_cannot_decide` |
| 69 | Pass | `test_a_login_with_the_submit_right_but_no_hr_role_is_refused` (Break by engineer) |
| 70 | Pass | `test_hr_of_another_company_is_refused`, `test_an_hr_login_with_no_company_and_no_branch_decides_nothing`, `P test_an_hr_person_and_a_manager_outside_scope_...` (Break) |
| 71 | Pass | `test_the_added_punch_belongs_to_the_approver_not_administrator` |
| 72 | Pass | `test_a_manager_can_send_for_a_held_day_but_not_an_ordinary_day_or_a_set_aside` |
| 73 | Pass | `test_the_monthly_limit_counts_ordinary_day_fixes_and_not_held_day_ones` (Break by engineer) |
| 74 | Not tested | filing window for a punch fix: no test name found |
| 75 | n/a | the daily cap was dropped (devops table, Surbhi) |
| 76 | Pass in part | repeat check and neighbours; "one per request" server refusal in `test_send_creates_one_waiting_request_...` |
| 77 | Pass | `test_a_leaver_cannot_be_approved` |
| 78 | Pass | `test_marks_cannot_be_written_outside_an_approval`, `test_a_marked_punch_cannot_be_edited_cleared_or_deleted_even_by_a_system_manager` (Break by engineer) |
| 79 | Pass | `test_cancelling_an_approved_fix_is_refused` |
| 80 | Pass in part | decide twice, stale `apply` (P). **Two-connection race not tested** (section 3) |
| 81 | Pass | `P test_ac81_...` both orders (Break) |
| 82 | Not tested | peer's request / punch by name |
| 83 | Not tested | manager's team view for "Added by HR" |
| 84 | Pass | `test_to_review_gives_the_card_and_no_photo_or_location_key`, `test_the_sheet_gives_punches_with_marks_and_the_shift_and_no_photo_or_location` |
| 85 | Pass in part | `test_a_note_is_in_no_refusal_and_no_log_line` (forced approval error only; send and decline paths not driven) |
| 86 | Pass in part | no leave type in the sentence (test name above); "no other person" not asserted |
| 87 | Pass in part | grep test for `allow_guest` and cache; a real guest call was not made |
| 88 | Not tested | the per-file `ignore_permissions` ceilings sit in test_portal_security_010, which has 13 known import errors; `git diff origin/dev...HEAD -- deploy/` is empty (0 lines) |
| 89 | Not tested | note label on an ordinary day's add sheet not opened |
| 90 | Pass on test_site only | `test_the_eight_fields_exist`; no fresh CI site |
| 91 | Not tested | operator step |
| 92 | Pass | `test_the_patch_marks_old_held_requests_and_runs_twice` |
| 93 | Pass | `test_rollback_is_a_new_request_that_sets_the_added_punch_aside` |
| 94 | n/a | release plan, not code |
| 95 | Pass [inference] | `test_held_p1_machine_accounts_085` 3 of 3; the diff of `held_day.py` shows `release_on_machine_punch` only in context lines |
| 96 | **Fail in part** | 360: no horizontal scroll, punch rows 56 px, buttons 48 px (HR card 44), input 16 px, smallest font 12 px: pass. Gap rows 44 px where AC says 52 (prototype says 44; spec and prototype disagree). Desktop smallest font 11 px is in existing stat labels, not 087 |
| 97 | Pass in part | B: dialog, aria-modal, focus, Escape, label. Screen reader not used |
| 98 | Not built | English only by decision |
| 99 | Not tested | usability test is a human gate |

## 7. SEC, PRIV, OPS

| Item | Result | Proof |
|---|---|---|
| SEC-1 one door and token | Pass | AC-60 to 63 tests |
| SEC-2 POST only | Pass in part | send and decide; `day_sheet` is a read |
| SEC-3 HR in scope, not own day | Pass | AC-67 to 70 (Break) |
| SEC-4 own day, gates count it | Pass | AC-13, 72, 73 |
| SEC-5 unfixable days refused | Pass (AC-25 assumption open) | AC-20 to 25 |
| SEC-6 marks only by approval | Pass | AC-78, 79 |
| SEC-7 exactly once | Pass in part | AC-80, 81; two-connection race untested |
| SEC-8 pay reads one list | Pass in part | `_punches` (engine) tested; month view, analytics, team days, grooming readers: not individually tested by me |
| PRIV-1 minimal payload | Pass | B payload |
| PRIV-2 note goes nowhere new | Pass | `test_a_note_is_taken_on_an_ordinary_day_and_refused_on_a_held_day`, AC-85 |
| PRIV-3 person sees every change | Pass | AC-15 and the marks test |
| PRIV-4 dry run copies no data | Not tested | dry run not run on a copy |
| OPS-3 one writer, link, lock | Pass in part | AC-81 (row lock itself untested) |
| OPS-5 measure | Pass in part | 50 cards measured; one slip save not measured |
| OPS-6 no backfill | Not tested | not read |
| OPS-7 hand-marked rule | Assumption open | AC-25 |
| OPS-8 inline work | Pass [inference] | no job or queue in `punch_fix.py` (read) |
| OPS-9 link and skip flag | Pass | AC-81 and AC-38 |
| OPS-10 audit on the punch | Pass | AC-71, AC-38 |
| OPS-11 no cache, no guest | Pass in part | grep test |
| OPS-12, OPS-18 dry run on a copy | **Not done** | release gate |
| OPS-13 assets landed | Not tested | note: this bench's assets folder is 18 Nov and has no `ess` files |
| OPS-14 patch creates fields | Pass in part | patch test; not on a pre-087 copy |
| OPS-15 `_punches` guard cost | Not measured | |
| OPS-16 pin test | Pass on test_site | `test_the_subclass_is_the_only_override_of_attendance_request`; not run on a site with all 12 apps |
| OPS-17 no deploy diff | Pass | `git diff origin/dev...HEAD -- deploy/`: 0 lines |
| OPS-19 ALV-291 guard first | **Not built** | open, P1 before ALV-291 runs at DTC |
| OPS-20 count HR who can approve | Not tested | per-tenant operator check |
| OPS-R6 race test | Pass | AC-81 |
| OPS-R7 no second release | Pass | AC-42 |
| OPS-R10 monitoring | Not tested | no automated check found |
| OPS-R11 rollback | Pass | AC-93 |
| other OPS-R (queues, rate limits, routes, logs, migration, assets) | Not tested | plan items, not code |

## 8. Extra cases I added beyond the ACs

- The Frappe job hazard shown directly (`test_ac81_the_link_is_what_keeps_the_job_off_the_added_punch`): with the link line out, the job marks the added punch skipped. This is what makes the two AC-81 tests believable.
- Stale second `apply` (two approvers holding one draft).
- Another company's HR can neither see, decline nor approve; a manager with no HR role cannot open the queue (a gap the 085 suite left: decline scope had no test).
- The exact payload the screen sends goes into `send`.

Fixture note: the first file's `day_of` leaves the day's original punches with no Attendance link. Real days have the link, because Frappe's job sets it. My AC-81 tests link them first. The older tests still use the unlinked shape.

## 9. Not automated (human checklist)

- Screen-reader pass, and the 360 px look on a real phone: someone once, before dev.
- AC-99 usability test (5 people).
- Hindi: not shipped; native reader first.
- Dry run on a DTC copy; the ALV-291 guard; counting HR approvers per tenant (OPS-20): before main.
- Two people pressing Approve at one instant: needs a two-connection harness, not built (not worth a framework; the three layers above are tested).
- A restore or rollback drill (OPS-R11): the code path is tested; the drill is a person's.

## 10. Subtract pass

Removed nothing from the engineer's file (I do not edit it). Recommend deleting `test_still_odd_stays_held_and_hours_are_written` (it cannot fail). In my own file I kept one test per control and did not add a fixture factory.

## 11. Verdict

**Fail.** Finding 1 (cut-off sentences on a phone) breaks AC-1 and AC-20, and nobody could read the reason a day is locked. AC-27 is also missing. The server side is solid: every control I switched off made a test fail, or showed me which other layer was holding. Fix findings 1, 2 and 4, then re-look at the screens (360 light and dark). Finding 3 (queries per card) and the release gates in finding 6 are for Surbhi to accept or schedule.
