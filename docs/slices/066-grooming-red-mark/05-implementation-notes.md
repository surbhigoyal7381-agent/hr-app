---
slice: 066-grooming-red-mark
artifact: 05-implementation-notes (change-process steps 4 and 6; the engineer's 03-implementation-notes for this slice)
author: hrms-fullstack-engineer
date: 2026-10-24
branch: slice/066-grooming in .claude/worktrees/066-grooming-build, cut from origin/dev eb33129b, rebased onto af0b7cdf (25 Oct 2026)
status: built and tested LOCALLY only. Nothing pushed. No server, no docker cp, no migrate outside hrlocal-066g.
---

# 066 · Implementation notes: the grooming red mark

## 0 · Final state (25 Oct 2026) - read this first; the sections below are the history

**What is built.** A store manager marks a direct report "Grooming red" for today; HR marks any
open day this month for people in scope. One of four clothing reasons, or "Other" with up to 100
typed characters. At most 3 marks a person a month, for everyone, with the 3%-of-Basic legal
check behind it (at marking and on the slip). The person is told the same day (desk bell and
the live portal's bell, fixed words, a link to the day) and sees who, why and what it costs; they
may ask HR once; HR keeps or removes (a cancel, never a delete). At the limit a review flag rises;
the manager sees a warning and may "Raise it with HR" once a month; HR records the conversation
in a private review note that only HR in scope and the direct manager read - the person sees only
"Action agreed on {date}". The month's total is one "Grooming Red Value" slip line; a slip is not
submitted while marks changed since the save or while the person's "Ask HR" is unanswered. HR has
three saved desk views and a "Grooming Review Pending" report. Screens follow prototype v3.

**Accepted in writing.** Surbhi accepted in writing on 25 Oct 2026 that a word list cannot catch
every sensitive remark; mitigations: the box hint, an audit log of every Other text, HR treats it
as sensitive, notices never repeat it, counsel to review. She also accepted "Saved. Kiran has been
told, with your name." (no "and the reason") and a phone-only live bell for now.

**Z-list (prototype v3) answers.** Z1-Z5, Z7-Z12, Z16: built as drawn (section 14). Z6: the word
list stays as built (leak accepted, above). Z13, Z14, Z15, Z17: as built / samples only. D-3
(v1's 5-mark "legal limit" employee state) cannot occur under the 3-mark rule.

**Limits and follow-ups.**
- *Follow-up ticket idea:* a bell on the **desktop** portal. The live portal's notice panel is in
  the phone header only, so desktop users see grooming notices through the desk bell and the month.
- The "Other" free text on a fine record: counsel to review the word list and the text itself.
- "Marks per marker per month" groups by owner only (Report Builder groups by one column).
- About 12 tests skip on days 1-4 of a month (they need earlier days in the month).
- The 00:10 IST time-zone case (AC-46) is covered by using the site's `nowdate()`, not by a clock test.

**Tests and checks** (on test066g, my own container; branch rebased onto af0b7cdf): see section 15.

## Bad news first

1. **Steps 8-11 (the cap, the slip line, the flag, the review note and the new "Raise it
   with HR") are in their own commit, marked provisional.** Surbhi changed the cap three
   times today (3% stop -> 3 marks a month for everyone -> plus "Raise it with HR", option A).
   The code follows her latest words (see 3). If anything moves again, only that commit changes.
2. **Two places differ from prototype v2 on the lead's later instruction, and need Surbhi's
   yes:**
   - **SETTLED 25 Oct: the direct manager DOES read the review note** (Surbhi, following v2;
     commit b23ed7a1). The paragraph below records what was first built.
   - **The direct manager does NOT read the review note.** v2 (Y2) drew "Only HR and Rahul's
     manager can read it". The lead's final brief said the employee *and the manager* see only
     "Action agreed on {date}". I built the stricter one. The two notes on screen say "Only HR
     can read this. Rahul and Rahul's manager see only "Action agreed on Sat 24 Oct"". Widening
     it later is one condition in `_review_payload`.
   - **Free text is back on the mark** ("Other" + 100 characters), at Surbhi's request. That
     reverses 01c SEC-8 ("no free text on the mark"). **Security must re-check it at 06.** What
     holds it in: it is stored on the mark only, never in a notice, the Inbox, a report or a
     saved view; words about health, family, religion, religious dress and the body are
     refused (a floor, not a filter that makes text safe); it cannot be changed after the mark.
3. **The "Raise it with HR" route was built from the brief's words, not from a drawing.** No
   prototype v3 exists. Words used are the brief's ("Decisions 24 Oct 2026 (3)") where it gives
   them; the raise sheet's heading and info line are mine (listed in section 6).
4. **Frappe's assign-to created a ToDo for someone who cannot read the mark** (found on the
   bench). DocPerm alone did not stop it. The side-record guard now covers Comment, ToDo and
   DocShare (SEC-8, as 01c asked). One name comparison for every other row.
5. **SETTLED 25 Oct: checked in a real browser** (section 10). Original note:
   **Not checked in a real browser.** The 390/1440 px, light/dark renders (AC-71) were not run:
   no portal is served from my container. The DOM, handler, design-system, tag-balance,
   brand-spelling and strip checks were run (section 7). This needs a browser pass before dev.
6. **The Inbox lives only on the preview page.** `inbox_api` (where HR's asks and pending
   reviews now appear) is read by `/hrms-employee-next`, which does not exist on production.
   The live portal's bell reads goals approvals only. HR's real signals on the live portal are
   the desk bell (Notification Log), the month's review line and the "Grooming Review Pending"
   report. Worth a decision: should the live bell panel list these?

## 1 · Commits (slice/066-grooming, not pushed)

| Commit | What |
|---|---|
| d70c26b0 | The record, may_mark, the read gate, removal, ask/keep, notices, endpoints, "Other", the side-record guard, three saved views, HR's asks in the Inbox, ceilings |
| 64474bd9 | The screens: Today card, the day box, the sheets (incl. "Other") |
| f9752cdb (provisional, see 1) | 3-mark stop + 3% backstop, flag at the limit mark, the private review record, "Raise it with HR", the slip line, the submit check (stale line, open "Ask HR"), the workings report columns, the pending-review report |
| 2a4e43e0 | The sheets use the portal's own dialog shell (.gp-backdrop/.gp-modal) - the tray check found my own backdrop |

## 2 · What I built, file by file (rung of the ladder)

| File | Rung | Why that rung |
|---|---|---|
| `doctype/grooming_mark/` (new) | 5 new DocType | Approved: nothing standard records a daily fine; Attendance is rebuilt at DTC |
| `doctype/grooming_review/` (new, provisional) | 5 new DocType | Approved (D5): the only private place; a manager note is readable by the subject in the desk |
| `grooming.py` (new) | 4 code | The one definition of every rule (may_mark, may_read, flag_for, may_raise), the endpoints, the notices |
| `hooks.py` | 4 | +5 doc_event/permission entries, appended |
| `attendance_correction.py` | 4 | `month()` gets one call; no other line changed |
| `payroll_month.py`, `payroll_slip.py` (provisional) | 4 | One ENGINE_LINES row, one count, the cap, one submit check |
| `inbox_api.py`, `next-frame.js` | 4 | One new Inbox part, HR only |
| 3 saved Report Builder views | 2 configuration | Report Builder, shipped as standard records |
| `report/grooming_review_pending/` (provisional) | 4 small script report | Y4: the flag is worked out, so Report Builder cannot filter on it |
| `portal.js`, `panels.css`, `policies.html` | 4 | Own `gm*` block; four one-line calls into the month and Whole team |
| `scripts/check_attendance_strip.js` | - | Loads the six `gm*` helpers the month now calls |

## 3 · The cap, as built (Surbhi, 24 Oct 2026, final words via the lead)

- **At most 3 live marks per person per calendar month, for every marker (HR too).**
- **The 3% check stays as a backstop.** At marking: (live + 1) × rate must not pass 3% of the
  full monthly Basic. At pricing: the month's line is capped at 3% of the earned Basic, and the
  Why says so. A Senior on Basic under ₹20,000 is stopped at 2.
- **The flag rises at the mark that reaches either limit,** whichever comes first. The 3rd mark's
  bell ends "This is your 3rd grooming red this month, the most allowed. HR will talk to you
  about it."; a 3%-stop mark's bell ends with the legal-limit sentence (Y5).
- **The manager's warning** (brief words): "Rahul has had 3 grooming reds this month, the most
  allowed. HR has been told and will talk to Rahul. If it carries on, you can raise it with HR."
  and the **Raise it with HR** button. No Mark button. HR's variant has no raise.
- **Raise it with HR** (option A, her five defaults): the subject's current manager, once a
  month, on the mark that reached the limit, one fixed reason (no "Other"). Three fields on that
  mark (`raised_on`, `raised_by`, `raised_reason` - the brief said two; the reason needs the
  third). The flag goes back to pending; HR in scope get a bell; the employee is told "Ravi
  Kumar, your manager, has asked HR to talk to you about grooming. This adds no fine." HR clears
  it with the same "Record the review" sheet (at most two reviews a month). HR can never add a
  4th mark. A raise drops off when the person leaves or the manager changes.
- **An open "Ask HR" holds the person's slip** at submit: "Rahul asked HR to look at the
  grooming red on 21 Oct. Keep or remove it first." An unanswered raise holds nothing.
- To let a manager raise on a limit mark HR made on another day (which they may not read), the
  mark's permission hook lets the current direct manager **write** (never read or cancel) a
  report's mark; the controller refuses every change from them except the raise. Tested.

## 4 · Acceptance criteria

All ACs of US-1 to US-9, US-12, US-13 and US-16 are covered by `tests/test_grooming_066.py`;
US-10, US-11, US-14, US-15 and the raise by `tests/test_grooming_cap_066.py`, re-pointed from
"4th mark" to the 3-mark rule. Not satisfied or not proven:

| AC | State |
|---|---|
| AC-34 (tapping the bell opens the day) | Not built: the portal has no Notification Log list; the desk bell opens the mark |
| AC-46 time-zone case (00:10 IST, Berlin clock) | Not tested as a clock simulation; "today" is `nowdate()`, the site time zone (Asia/Kolkata on test066g) |
| AC-55 | Changed by decision: 3rd mark, not 4th |
| AC-62 | Changed by D5: the note is its own record, not a manager note |
| AC-66 | Report Builder groups by one column: "Marks per marker per month" groups by owner only (not owner + marked as) |
| AC-71 | Not run in a browser (bad news 5) |
| B-4 (Payroll Entry with one stale slip) | Not run; Frappe HR catches a ValidationError per slip (read in code by the strategy) |

## 5 · Seven non-functional dimensions, against the code written

| Dimension | Before -> after | Verdict |
|---|---|---|
| Performance | Today card flat in queries (test: same count for N and N+5 reports). Month view +5 to +9 for a permitted viewer, +1 (the gate) for others. Slip save +1 (distinct mark dates), submit +2 (asks, re-price). A raise-state row on the Today card costs ~6 queries, only for rows at the limit | degrades slightly |
| Security | New records gated by their own hooks (fail closed: `1=0`, never empty). Zero new `ignore_permissions` (ceilings: grooming.py 0, both controllers 0, payroll_month 0, report 0, payroll_slip held at 2). New: free text on the mark ("Other"), and the manager-write rule for the raise | degrades, guarded - needs 06 |
| Reliability | Notices never block a mark (tested with a forced failure). Payroll Entry submits slips one by one; a held slip says what to do | neutral |
| Scalability | Every list query is one sub-query, never IN (445 names). Pending reviews: one query each for scope, marks, reviews, people, managers, Basic | neutral |
| Maintainability | Two doctypes, one module (~1,250 lines), one screen block (~600 lines) | degrades |
| Data integrity | Flag and "live" worked out on read; pay counts distinct dates; a stale slip cannot be submitted; removal is a cancel | neutral |
| Compliance / privacy | Fixed-word notices; review note readable by HR only; "Other" text stored on the mark only; 3% backstop | degrades by design (a fine about a person) |

## 6 · Words that are mine (not in a prototype or the brief) - for Surbhi's eye

- Raise sheet: "Raise Rahul Sharma's grooming with HR?" / "Choose the one reason that fits. You
  cannot add your own words." / "HR will be told and will talk to Rahul. Rahul will be told you
  raised it. This adds no fine and no grooming red."
- After a raise, Today row: "Raised with HR on 26 Oct. HR recorded a review on 27 Oct." (brief)
- HR review line after a raise: "Ravi Kumar raised it again on 26 Oct: Not in uniform." (brief)
- Manager review line after a raise: "You raised it with HR on 26 Oct. HR will talk to Rahul.
  You do not need to do anything."
- HR bell on a raise: "Grooming review pending for Rahul Sharma: Ravi Kumar raised it again on 26 Oct."
- Manager flag line for the 3-mark case: "Rahul has had 3 grooming reds in October, the most
  allowed, so HR will talk to Rahul about it. You do not need to do anything."
- "Other" refusals: "Write your reason in a few words." / "Keep your reason to 100 characters." /
  "Keep the reason to clothing or grooming. Nothing about health, family, religion or the
  person's body."
- Brand: the prototype's "no reporting manager in Alvoraa" is written "Alvora" (ALV-149 check).
- N2 uses the marker's first name for "he" (spec assumption).

## 7 · Commands run and what they said

All on my own container `hrlocal-066g`, site `test066g` (a copy of test067), never the shared bench.

| Run | Result |
|---|---|
| `test_grooming_066` (steps 1-7, "Other", guards) | **54 OK** (53 integration + 1 unit) |
| `test_grooming_cap_066` (3-mark stop, 3% backstop, flag, review note, raise, slip) | **25 OK** |
| Guards broken on purpose (read gate, R13 tick, comment/ToDo guard, purpose fence, submit check, 3-mark stop, one raise a month, open-ask hold) | every one failed its tests (12, then 5 named failures); restored |
| Affected modules after the rebase: attendance_correction, pay_slip_marks_067, payroll_month, salary_report, inbox_counts_034, inbox_parts_042, portal_security_010, leave_063_card_cancel, leave_063_engine, portal_full_width_213 | all OK except **2 errors in test_attendance_correction** (`test_a_holiday_in_the_range_pushes_the_reach_further_back`, `test_a_weekly_off_counts_the_same_way`): the same 2 fail on untouched origin/dev 6aaf9ffd today - the manager filing window, date-dependent, not this slice |
| **Full suite, once, at the end** (`run-tests --app alvoraa_portal`, branch at 2a4e43e0) | 16 OK; **963: 1 failure, 6 errors, 20 skipped**; **2,246: 2 errors, 40 skipped**. All 9 are outside this slice: 7 are the site-copy faults slice 067 recorded (3 `test_leave_year` overlapping fiscal year, 3 `test_provision_guards` root-owned file, 1 `test_shift_types_043` leftover shift) and 2 are the date-dependent filing-window tests that fail the same way on untouched origin/dev. Every grooming test passed in it |
| `scripts/check_app_integrity.py` | OK |
| design system, tag balance, API paths, brand spelling, portal handlers, undefined JS, attendance strip | OK (brand caught "Alvoraa" from the prototype - fixed; strip check needed the gm helpers listed) |
| tray check (static half) | OK, 26 fixed elements, all in inventory (after moving to .gp-backdrop). Browser half needs PROBE_USR - not run |
| DOM tests (NODE_PATH to an existing jsdom) | 12 run, 0 failed; `portal_correction_test` is flaky on origin/dev too (a 1.5 s bell timer races its "nothing sent" check) |

## 8 · What else moved while I worked

One commit came in: **6aaf9ffd ALV-213 "the employee portal uses the whole screen"** (portal.js
leave cards and phone account menu, panels.css phone rules, frame.html, attendance.html,
hrms_employee.py, a new test). Different regions from mine. Rebase was clean; both sides' code
is present (`toggleAcctMenu`, `leave-apps-cards`, `.lv-card` beside the `gm*` block) and its
pin test `test_portal_full_width_213` passes (5). My worktree and branch
are new. Other sessions' uncommitted files in the main checkout were not touched.

## 9 · Known gaps and shortcuts

| Item | Kind |
|---|---|
| Steps 8-11 provisional commit | intentional trade-off (removed by Surbhi confirming the cap words) |
| No browser render check (AC-71) | temporary debt (removed by a browser pass on a served copy) |
| Inbox only on the preview page | temporary debt (a decision on the live bell) |
| "Other" free text on a fine record | **dangerous debt - escalate now** to the security engineer and counsel: a judgement about appearance in a person's own words, read by the subject, manager and HR |
| Raise-state on the Today card is a few queries per row at the limit | acceptable simplification (only rows at the limit) |
| HR's `_hr_users_for` reads every HR login on the site for a bell | acceptable simplification at DTC (7 HR users) |
| "Marks per marker per month" groups by owner only | acceptable simplification (Report Builder limit) |
| DOM and tray checks need jsdom/playwright, absent on this PC | environment; run with NODE_PATH pointing at an existing install |

## Subtract pass

Removed: the "RAISE WITH HR" placeholder comment (the route is built); a test that only
checked a dataclass; `add_months` from the steps 1-7 module; a per-row half-day query on the
Today card (one batched read instead). Kept the manager-write rule (the raise cannot work on an
HR-made limit mark without it, and there is no bypass).


## 10 · Follow-up, 25 Oct 2026 (coordinator's decisions)

| Item | What was done | Commit |
|---|---|---|
| Manager reads the review note | Employee role gets read on Grooming Review, narrowed by its own gate to the reader's direct reports (never themselves); the month shows the note to the manager with v2's words; tests changed (manager reads it through REST and the screen; subject, owner, colleague, skip-level, other HR still do not) | b23ed7a1 |
| Raise wording in one place | `GM_RAISE_WORDS` in portal.js; the server's copies (warning, bells) in grooming.py | b23ed7a1 |
| AC-34, a bell opens the day | Every grooming bell has `link` = `/hrms-employee?grooming=<day>` (`&who=<person>` for HR); the portal opens that month at that day. The server's month() still decides who may open it. Test pins both links. Works from the desk bell and the bell e-mail; the live portal has no list of notices (see below) | b23ed7a1 |
| Browser check | Chromium, 7 screens (Today card with limit + raise button, raise sheet, mark sheet with no-login tick and "Other", HR month with review pending, review sheet, manager month, employee month) x 390/1440 x light/dark = **28 renders, 0 problems** after two fixes: the sheet heading was near-black in dark mode (contrast 1.08), and the grooming tag/tile label were 11 px. Measures: sideways scroll, text < 12 px, contrast 4.5:1 (3:1 large), phone targets 44/48 px, script errors. The contrast check was broken on purpose and caught the heading (6 fails). Script and screenshots: scratchpad `browser_066.js`, `shots/` | 4758a774 |
| Payroll Entry end to end (test066g) | 5 slips made through Frappe HR's Payroll Entry with real shift, attendance and punches: GRV line Rahul Rs 200 (Senior, 1 mark), Kiran Rs 300 (3 marks; net = gross - 300), none for the unmarked. Submit: 3 submitted; **Kiran held** (open Ask HR); **Pooja held** (a mark added on a new day after her slip was made); the entry itself submitted. Earlier run with no attendance: earned Basic 0, so the back-stop priced every line at Rs 0 and the Why said "capped at Rs 0 by the legal limit" | - |

Test-site setup the payroll run needed (not code): the payroll payable account typed "Payable",
salary components given an account, a shift on the employees.

**Live-portal notices - options (not built):**

| Option | What | Effort |
|---|---|---|
| A (recommended) | Add grooming items to the live portal's existing bell panel (`loadNotifPanel` / `loadNotifBadge`, today goals approvals only): HR sees open asks and pending reviews; the person sees "a grooming red was marked/removed/kept" from their own Notification Log rows. One small endpoint in grooming.py, ~30 lines of JS in the existing panel. No new page | about half a day with tests |
| B | Show every Notification Log row of the user in the live bell panel (all modules, not only grooming) | about a day; it changes what every user sees, so it is a product decision |
| C | Ship the preview Inbox to production | not recommended: it belongs to the discarded redesign |

Final test numbers after the follow-up: test_grooming_066 55 OK, test_grooming_cap_066 25 OK.


## 11 · Security verification (06b) and architect review (06), 25 Oct 2026

| Finding | Fix | Test (failed when the fix was taken out) | Commit |
|---|---|---|---|
| B1 empty save read a mark and stamped modified_by | Manager write only through `raise_with_hr` (in-memory flag no REST call can set); an after-submit save that changes nothing is refused | `test_b1_an_empty_save_neither_reads_nor_stamps_a_mark`, `test_b1_a_raise_sent_straight_through_rest_is_refused` | 6c899251 |
| B2 files and tags on a mark | File and Tag Link join the side-record guard | `test_b2_no_file_and_no_tag_on_a_mark` | 6c899251 |
| B3 / M-4 word check | One list, now sensitive-information words only (below); clothing and grooming words allowed | `test_m4_one_list_refuses_sensitive_information_and_allows_grooming_words` | 6c899251, bcf4d48f |
| M1 / m-5 race to a 4th mark | Row lock on the person's Employee at marking; the slip charges at most 3 days | `test_m1_the_slip_never_charges_more_than_three_days` | 6c899251 |
| M2 leaver reads own marks | Marker's own read needs an Active employee | `test_m2_a_marker_who_has_left_reads_nothing` | 6c899251 |
| M-1 slip held for ever when GRV is scaled or rounded | Submit check compares the engine's Additional Salary with the marks and checks the slip carries its row, not the slip row's amount | `test_m1_a_scaled_grooming_line_does_not_hold_the_slip_for_ever` (depends_on_payment_days on) | 59c87eda |
| M-2 second raise after a removal | Raises on removed marks count | `test_m2_one_raise_a_month_even_after_the_mark_it_was_on_is_removed` | bcf4d48f |
| m-1 report label | "Raised again by [manager]"; "3 grooming reds, the most allowed" | `test_m1_pending_report_says_why_in_the_right_words` | bcf4d48f |
| m-2 raise sheet error | "Choose a reason first." | `test_m2_the_raise_sheet_asks_for_a_reason_not_why_it_is_removed` (reads the screen code) | bcf4d48f |
| m-6 Today card queries per row at the limit | `_raise_states` reads all rows at the limit in two queries | `test_m6_the_today_card_is_flat_with_people_at_the_limit` | bcf4d48f |

Tests: test_grooming_066 60 OK, test_grooming_cap_066 31 OK; pay_slip_marks_067, salary_report,
payroll_month OK. Held as told: the Inbox part (not deleted), prototype v3 words.

**The "Other" word list, for counsel** (`grooming.NOT_ABOUT_CLOTHES`; "*" = any word starting so):
religion and its items - religio*, hindu*, muslim*, islam*, sikh*, christian*, jain*, buddhis*,
parsi*, jew, jews, jewish, god, gods, puja, namaz, prayer*, temple*, mosque*, church*, gurdwara*,
fasting, roza, ramzan*, ramadan*, navratri*, turban*, pagdi*, pagri*, patka*, hijab*, burqa*,
burka*, niqab*, tilak*, bindi*, sindoor*, kara, kada, mangalsutra*, rudraksh*, janeu*; caste and
race - caste*, dalit*, brahmin*, race, racial*, ethnic*, tribe*, tribal*; health - health*, sick*,
illness*, disease*, medical*, medicine*, doctor*, hospital*, injur*, disab*, handicap*, blind*,
deaf*, pregnan*, period, periods, menstru*, mental*, depress*, diabet*, allerg*; family - family,
families, husband*, wife, wives, child*, kids, mother*, father*, marri*, divorc*, widow*; gender -
gender*, sex, sexual*, transgender*, gay, lesbian*. Allowed on purpose: dirty, head, hair, beard,
jewellery. Questions for counsel: religious dress items are refused although "head" and "beard"
are allowed - is that the right line?


## 12 · Security M1, second look (25 Oct 2026)

The row lock alone did not stop a 4th mark: the second transaction's snapshot was fixed before
the lock was granted (MariaDB REPEATABLE READ). Saving a mark now counts the marks with a locking
read (`frappe.db.get_values(..., for_update=True)` in `_facts`, `may_mark(locking=True)` from the
controller). Proof: `TestTwoMarkersAtOnce` runs a real second bench process
(`tests/grooming_race_066.py`). With the fix: refused, 3 marks. Without the locking read: "RESULT
saved", a 4th. The slip still charges at most 3 days as a second line of defence. Tests:
test_grooming_066 60 OK, test_grooming_cap_066 32 OK. The B3 word list was not touched.


## 13 · Live portal bell, and the "Other" text (Surbhi, 24-25 Oct 2026)

**Surbhi accepted in writing on 25 Oct 2026 that a word list cannot catch every sensitive remark;
mitigations: the box hint, an audit log of every Other text, HR treats it as sensitive, notices
never repeat it, counsel to review.** The word list (section 11) is unchanged.

- **Audit log of every Other text:** on submit, `grooming.audit_other_text` writes one line to the
  security log: event `grooming_other_text`, who, when, the mark, the employee id and the text's
  length - never the words (PRIV-7). The words stay on the mark only, which nobody can edit or
  delete after it is made. Test: `test_every_other_text_is_audit_logged_by_id_never_by_its_words`.
- **Live portal bell:** `grooming.my_notices` / `my_notices_seen` feed a "Grooming red" section at
  the top of the existing bell panel, and the badge counts unread ones. The caller's own
  Notification Log rows only, fixed sentences only (marked, undone, removed, kept, limit reached,
  raised, asked, review pending, action agreed), each linking to its day; a row shows only while
  its reader may still read what it is about (the mark's own gate; for a review the subject, the
  current manager or HR in scope). New: an "Action agreed on {date}" notice to the person and their
  manager when HR records a review - the date only, never the note. Tests: `TestLivePortalBell`,
  `TestActionAgreedNotice`.
- **The preview-only Inbox part is removed** (`inbox_api.py` and `next-frame.js` back to origin/dev).
- Prototype v3 wording: not changed; waiting for approval.


## 14 · Prototype v3 alignment (approved 25 Oct 2026, Z1-Z17)

Commit fa9dc7c9 (the bell: 20147018; Inbox removal: 0d722fa9). Every screen word is in one table,
`GM_WORDS` in portal.js, the shape of v3's `V3`. Built to v3: Z1-Z5 ("Other" label, counter,
blank error on screen and server, sheet help, info line, bell N1-O), Z7-Z12 (raise sheet no-login
line, row after a raise shows the stop alone and the "Raised with HR on..." line which takes the
focus, "raised it with HR on" for HR's line and bell, neutral limit row, raise network failure),
Z16 (HR's line after a review: "More grooming reds in October will not raise it again. Kiran's
manager can still raise it with HR once this month." before a raise; the old sentence after the
raise's review). Z6, Z13, Z14, Z15, Z17: as built. The "Other" word list is unchanged.

**One small difference not drawn in v3, for Surbhi's eye:** HR's "Saved." line after marking
with "Other" says "Saved. Kiran has been told, with your name." (without "and the reason"),
because the notice does not carry the reason (Z4/Z5's own logic). Every other v3 word is as drawn.

**The live bell is phone-only.** The portal's existing notice panel is in the phone header; the
desktop page has no bell, so desktop users see grooming notices only through the desk bell and
the month. Not changed (it is the existing panel).

Checks: test_grooming_066 65 OK, test_grooming_cap_066 35 OK; browser 34 renders (7 screens x
390/1440 x light/dark, plus the live bell and the after-raise row; the bell on phones only),
0 problems after the bell times were made 12 px; DOM 12 run 0 failed; handlers, undefined JS,
trays, design system, tag balance, brand spelling, integrity all OK.

## 15 · Final run after the rebase onto af0b7cdf (25 Oct 2026)

**Rebase.** slice/066-grooming now sits on origin/dev af0b7cdf. No conflicts. What came in:
12 commits of slice 069 (wall chart printing) in portal.js, panels.css, positions.html, their
tests and check scripts, and run_dom_tests.js (13 files expected). Both sides' code is present.
Tip: a9af0501. Nothing pushed.

**One commit touches another slice's test - a9af0501.** `alvoraa_portal/tests/portal_correction_test.js`
belongs to the attendance correction screen, not to 066. Its "nothing was sent" check counted every
server call in a time window. 066 adds a second bell timer (the grooming notices, beside the goals
badge), so a bell call sometimes landed inside that window and the test failed at random. The fix
counts only calls that name a server method (`calls.filter(c => c.fn)`), which is what the check
means. The correction screen's own code is unchanged.

**Python tests on test066g (after migrate), all OK:**

| Module | Tests |
|---|---|
| test_grooming_066 | 64 + 1 (race, second process) |
| test_grooming_cap_066 | 35 |
| test_pay_slip_marks_067 | 18 + 2 |
| test_payroll_month | 29 |
| test_payroll_rules | 76 |
| test_payroll_flags | 9 |
| test_payroll_reprocess | 12 |
| test_salary_report | 12 + 4 |
| test_leave_063_engine | 23 |
| **Total** | **285, 0 failed** |

**Browser check** (390 and 1440 px, light and dark; live bell on phones only): 34 renders,
0 problems - no sideways scroll, no text under 12 px, no low contrast, no small phone targets,
no script errors, every expected word present.

**Other checks:** DOM tests 13 files run, 0 failed; handlers OK; undefined JS OK; attendance strip
OK; trays 26/26; wall chart 183 checks OK; design system, tag balance, brand spelling OK;
`scripts/check_app_integrity.py` OK.
