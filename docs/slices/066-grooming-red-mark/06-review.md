---
slice: 066-grooming-red-mark
artifact: 06-review (the senior architect review, change-process step 5; plays the part of 05-review in the handoff contract)
author: hrms-technofunctional-reviewer
date: 2026-10-25
reviewed: branch slice/066-grooming, commits d70c26b0, 64474bd9, f9752cdb, 2a4e43e0, b23ed7a1, 4758a774 (base origin/dev 6aaf9ffd)
runs alongside: 06b-security-verification.md (security). Its findings are referenced, not repeated.
---

# 066 · Review: the grooming red mark

## 1 · Verdict

**BLOCK (on the committed code, 4758a774).** A manager can read a mark they are not allowed to
read, and a file (a photo) can be attached to a mark. Both are fixed in uncommitted work that is
in the worktree now, but not yet committed or tested as a whole. Once that lands with its tests,
I expect **SHIP WITH FIXES**, with the P2 items below accepted in writing or fixed.

This verdict is advice. Surbhi decides whether the slice ships. "Ship" would only mean "ready to
show for deploy approval".

**Read these first:**

1. **The code changed while I reviewed it.** Six files in the worktree have uncommitted edits
   (`grooming.py`, `grooming_mark.py`, `hooks.py`, `payroll_slip.py`, both test files), made by
   another session in answer to the security verification (B1, B2, B3, M1, M2). The container
   mounts the worktree, so **my probes ran against that uncommitted code**, not against
   4758a774. Where that matters I say so. I did not review the uncommitted diff as finished work.
2. **What I ran (proven):** `check_app_integrity.py` OK (819 checks); design system, tag balance,
   brand spelling, API paths, tracked keys: all OK; node `check_attendance_strip`,
   `check_portal_handlers`, `check_undefined_js` OK; tray check static half OK (browser half needs
   playwright - not run); `check_day_widget` crashed with `ERR_INVALID_ARG_TYPE` (not this slice's
   script; not looked into). On site `test066g` (own container `hrlocal-066g`, a test site):
   `test_grooming_066` **54 + 1 OK**, `test_grooming_cap_066` **25 OK**,
   `test_portal_security_010` **45 + 5 OK**. These ran on the working copy, so they include the
   uncommitted edits. I did not run the full suite.
3. **What I could not run:** a real browser pass (the engineer reports 28 renders, 0 problems -
   not re-run); anything on DTC (no access), so the GRV component settings, `dtc_grade`
   permission level and the four Rs 0 people are **not checked**.
4. **No `07-devops-inputs.md` exists.** There are no `OPS` items to trace. The slice is
   unreviewable on that axis; DevOps owes it.
5. **Prototype v3 does not exist.** The "Other" box, the "Raise it with HR" button and sheet,
   and the 3-mark wording were built anyway. The spec (bad news 1) said they must wait for
   Surbhi's yes or v3. Known to the lead; it still blocks shipping those screens.

## 2 · Blockers (P1)

Both were found first by the security verification (`06b` B1, B2). I traced them myself and
agree. I do not repeat the detail.

| # | What | Evidence | State |
|---|---|---|---|
| **B1** | A manager reads any of their report's marks - HR's reason, the "Other" text, whether the person asked HR - by saving it with no changes (`frappe.client.set_value` or `PUT /api/resource`). | **Inferred from code at 4758a774:** `grooming.py:470-472` gives the direct manager `write` on every mark of a report; `grooming_mark.py:57-59` returns early when nothing changed; Frappe 16.33 `client.set_value` returns `doc.as_dict()` and `api/v1.update_doc` returns the doc (read in the container). `raise_with_hr` (`grooming.py:738`) hands the manager the name of the limit mark, often an HR mark. **Proven fixed in the uncommitted code:** my probe on `test066g` - both doors now refused. | Fix uncommitted |
| **B2** | HR (and, through B1's write rule, the manager) can attach a file - a photo - or a tag to a mark. The brief's "no photo" had no mechanism behind it. | **Proven:** probe - Frappe's upload gate `check_write_permission` passes for HR on a mark; committed `hooks.py` guards Comment, ToDo and DocShare only. | Fix uncommitted (File and Tag Link added) |

Smallest fix for both: what the uncommitted diff does. It needs its own test for the empty save
and for a File insert, then a commit.

## 3 · Majors (P2)

**M-1 · The slip may refuse to submit, for ever, if DTC's GRV component is paid by payment days
or rounded.** *Inferred from Frappe HR's code; DTC's settings not checked.*
- *State:* `Grooming Red Value` has `depends_on_payment_days` = 1 (Frappe's default for a new
  component) or `round_to_the_nearest_integer` = 1, and the person was not paid every day, or the
  3% back-stop gives a figure with paise.
- *What happens:* the engine writes an Additional Salary of, say, Rs 300 (`overwrite` = 1).
  Frappe HR then scales that row by paid days, or rounds it
  (`hrms/.../salary_slip.py` `get_amount_based_on_payment_days`, lines 2126-2172: an overwriting
  row with `default_amount` 0 is scaled; the rounding flag is applied after). The slip shows, say,
  Rs 280. `check_grooming_before_submit` (`payroll_slip.py`, new, ~line 561) compares the slip row
  with the engine's Rs 300 and refuses: "Grooming marks changed since this slip was saved. Save it
  again." Saving again gives Rs 280 again. The slip can never be submitted.
- *Why it is wrong:* it fails closed (no wrong money), but it stops a real payslip with a message
  that sends HR round in a loop, in DTC's first payroll.
- *Why the tests could not show it:* the fixture makes GRV with `depends_on_payment_days` = 0
  (`test_grooming_066.py:113-117, 141`), and the Payroll Entry run in `05` §10 used that fixture.
- *Smallest fix:* a switch-on check: GRV at DTC has `depends_on_payment_days` = 0 and
  `round_to_the_nearest_integer` = 0. Red Value and Green Value need the same check - for them a
  scaled row is silent wrong money, which is slice 067's to own.

**M-2 · A manager can raise the same person twice in a month.** *Proven (probe).* AC-83 not met.
- *State:* Kiran has 3 marks; Ravi raises (written on mark 3). HR removes mark 3 as a mistake. A
  new mark brings Kiran back to 3.
- *What happens:* `may_raise` (`grooming.py:709-715`) looks for `raised_on` on **live** marks only,
  so the raise on the removed mark is not seen. `may_raise` returned `ok`. A second raise means a
  third review in the month.
- *Why it is wrong:* AC-83 and the brief ("one raise per person per month", "at most two reviews a
  month") count raises on removed marks too.
- *Smallest fix:* drop `docstatus: 1` from that one query (count `docstatus < 2` or any state).
- *Rank:* an unmet AC is P1 by the table. I rank it P2 because it adds no fine and needs an HR
  removal first. Surbhi may raise it.

**M-3 · Employees with a login never see the "same day" notice on the portal they use.**
*Proven by reading.* The bell is a desk Notification Log. The live portal's bell panel reads only
goals approvals (`portal.js` `loadNotifPanel` -> `goals_api.get_pending_approvals`). The brief's
fairness promise ("told the same day") and its WOW moment reach a person only if they open the
desk, or happen to open the day in their Attendance month. At DTC this affects the 7-10 people
with logins; everyone else is covered by the "told in person" tick. The engineer flagged it (`05`
bad news 6, options A-C). **Decision needed (Surbhi):** accept for now in writing, or option A
(about half a day).

**M-4 · The "Other" word check is scope nobody approved, and the stronger list now refuses
clothing words.** *Proven by reading.*
- The spec removed a word filter on purpose (subtract pass) and recommended **no** filter (Q-12);
  Surbhi has not decided. The build added one; security (`06b` B3) now asks for a longer one; the
  uncommitted list has about 130 entries.
- Some entries refuse plain clothing reasons: "dirty" ("dirty apron"), "head" ("cap not on head"),
  "ring" ("key ring badge"), "cross" ("cross belt"), "bath*" ("bathroom slippers"), "nail*". The
  marker gets "Keep the reason to clothing or grooming" for a reason that is about clothing.
- **Conflict, rung 2 (legal and privacy) against rung 3 (the business asked for free text):**
  security's floor protects people from religious or body comments; the false refusals push
  managers back to the fixed list. **Decision needed:** Surbhi with counsel (Q-C4). My
  recommendation: keep the floor (security's B3 is right about what it must catch), drop the
  entries that are also clothing words, and record her yes in the slice folder.

## 4 · Minors (P3)

| # | Finding (state -> what happens -> why wrong) | Evidence |
|---|---|---|
| m-1 | HR's "Grooming review pending" report: a person raised again by the manager -> the "Why it was raised" column says **"Legal limit reached"** -> HR is told the wrong reason (AC-67a wants "Raised again by [Manager]"). Also "3 grooming reds" lacks ", the most allowed". | Proven (probe). `grooming_review_pending.py:132` maps every non-"max" row to "Legal limit reached" |
| m-2 | Raise sheet, no reason chosen, press the button -> "Choose why you are removing it." -> wrong sentence; should be "Choose a reason first." | Proven by reading, `portal.js` gm block `gmConfirm` (`s.kind === "mark" ? ... : "Choose why you are removing it."`) |
| m-3 | Mark sheet with "Other" -> help line still says "You cannot add your own words." directly above a text box. Spec C-2 proposed new words | Proven by reading |
| m-4 | A marker who is not the direct manager, and the subject, get `raise_by` / `raise_on` in the month JSON, and the screen shows "[Manager] raised it with HR on..." to the non-manager marker. Spec 7.6: they see no raise line | Proven by reading, `grooming.py:1223-1226`, `managerLine` in `portal.js` |
| m-5 | Race on the 3rd/4th mark at 4758a774: two markers at the same moment can make 4 live marks, all 4 priced. Spec accepted the risk; Surbhi's rule is a hard 3 | Inferred. `06b` M1; the uncommitted diff adds a row lock and caps pricing at 3 |
| m-6 | Queries are higher than the impact analysis said, and the Today card has a query loop: Today card **27** with nobody at the limit, **+8 per report at the limit** (`_raise_state` per row); month view **33** for HR, **17** for the manager, **19** for the subject, **5** for a skip-level viewer (`04` §1.5 said ~7 flat and +3 to +5). The budget's rule is "flat in headcount"; rows at the limit break it | Proven (query counts on `test066g`, uncommitted code) |
| m-7 | HR's desk views: "Marks per marker per month" groups by owner only (AC-66: owner + marked as) and both group views sort by `modified`, not "count, highest first" as v2 draws; "People with grooming reds" groups by name, so two people with one name merge (`06b` m3) | Proven by reading the report JSON |
| m-8 | Tests that cannot fail on some days: about 12 skip on days 1-4 of a month - the payroll window (`06b` m4); `test_ac54_...` asserts only `if row:` (hollow when no row); no test for the empty-save door (B1), the report label (m-1), the second raise (M-2) or the 00:10 IST time-zone case (AC-46) | Proven by reading the tests |
| m-9 | The Inbox part is built for a page that is not live (see section 6) | Proven by reading |

**Nits (P4), collapsed:** HR cannot cancel a mark in the desk (`removal_reason` is read-only
there, so the desk Cancel always fails - the portal works). A draft left by REST can never be
deleted and blocks that day. The open-ask slip message says "21 Oct", not "Wed 21 Oct". The tile
rounds to whole rupees while a capped line has paise. The review sheet's "Action agreed on" date
uses the phone's clock. `_rupees` re-implements Frappe's money format. `test_portal_security_010.py`
will conflict with `slice/065-plan-a-replacement` (ceiling table, trivial); when 065 lands, its own
Comment/ToDo/DocShare/File/Tag guard duplicates this one (01c SEC-8 asked for one list).

## 5 · Acceptance criteria

| AC | State | Evidence |
|---|---|---|
| AC-1 to AC-7, AC-2a, AC-18, AC-19 (Today card) | Met | `grooming.today`, `gmPaintToday`; tests `TestTodayCard` |
| AC-8 to AC-17, AC-10a, AC-10b (manager marks) | Met | `TestManagerMarksToday`; AC-13 REST door tested |
| AC-9a to AC-9e (Other) | Partial | Built, but label "Your reason" not "What was wrong", hint above not under, errors worded differently; D-6 not drawn. AC-9d no text in notices: met (test) |
| AC-20, AC-21, AC-22a | Met | `TestRemoval` |
| AC-22 | Partial | The "undo closed at midnight" line shows only after a failed Undo, not on refresh (after refresh the row is a new day) |
| AC-12a, AC-23 to AC-27 (HR marks) | Met | `TestMonth`, `test_d3_...` |
| AC-28, AC-29 | Met | `test_ac28_...` (0 Deleted Document rows) |
| AC-30 to AC-32, AC-40 | Met | `TestMonth` |
| AC-33, AC-33a | Met | `TestNotices` |
| AC-34 | Partial | Desk bell link opens the day (test); the live portal has no notice list (M-3) |
| AC-35 to AC-38 | Met | `TestAskAndKeep` |
| AC-38a | Met (wording differs: "21 Oct") | `TestAskedHoldsTheSlip`; Payroll Entry run in `05` §10 (not re-run by me) |
| AC-38b | Met | same test |
| AC-39, AC-41 to AC-45 | Met | `TestManagerMarksToday` refusal tests |
| AC-46 | Partial | All refusals tested except the 00:10 IST / Berlin clock case. Code uses `nowdate()` (site time zone) everywhere on the server |
| AC-47 to AC-49 | Met (words D-7/D-8 not drawn) | `TestLegalLimit` |
| AC-50 to AC-53 | Met in code and tests | But see M-1: GRV component settings at DTC not checked |
| AC-54 | Partial | Columns proven; the value assertion is guarded by `if row:` |
| AC-55, AC-55a, AC-56, AC-58, AC-60 | Met | `TestReviewFlag` |
| AC-57 | Partial | Skip-level tested; org chart, directory, appraisals rely on the purpose-fence test (AC-73) |
| AC-59 (carry into next month) | Met in code (`month_lines`), not tested | |
| AC-61 to AC-65 | Met | `TestReviewNote`; manager reads the note (b23ed7a1) |
| AC-66, AC-66a | Partial | m-7 |
| AC-67 | Met | `test_ac66_ac67_...` |
| AC-67a | Partial | m-1 |
| AC-68 to AC-70, AC-72 | Met at the list and GET doors; **not met at the save door at 4758a774** (B1) | `TestReadGate`; probe |
| AC-73, AC-74 | Met | purpose fence test; SEC-16 ceilings pass |
| AC-75 | Met | `test_priv7_...` |
| AC-76, AC-77, AC-79 | Met for comment, share, assign; **files and tags not covered at 4758a774** (B2) | `TestNoFreeText`; probe |
| AC-78 | Met for the fixed list | |
| AC-71 | Met per the engineer (28 renders) | Not re-run by me |
| AC-80 | Partial | Sheet built; empty-reason error wrong (m-2); words not drawn (D-7) |
| AC-81, AC-82 | Partial | Fields, bells and "no new mark" met (tests); row line lacks "HR will talk to Kiran."; HR bell says "raised it again" (brief's words, not the spec's) |
| AC-83 | **Not met** | M-2 |
| AC-84, AC-85 | Met | `TestRaiseWithHR` |
| AC-86 | Partial | One review clears both parts (met); HR's line shows only the raise reason, not both |
| AC-87 | Partial | (a)-(d) met in code; (e) the no-login row text is not built |

**Surbhi's decisions, checked one by one:**

| Decision | State | Where |
|---|---|---|
| Max 3 marks per person per calendar month, for everyone (HR and owner marks count) | Met (race aside, m-5) | `_decide` counts every live mark, any owner, before the 3% check |
| 3% wage check as backstop | Met | stop at marking on full Basic; back-stop at pricing on earned Basic (`payroll_month.py`) |
| Flag at whichever limit comes first | Met | `_raise_point` |
| Never returns that month after clearing | Met | `flag_for`: any review -> "cleared"; `raised_by` sends no bell once a review exists |
| Cleared by the private review note | Met | `Grooming Review`, insert-only, `track_changes` 0 |
| Direct manager reads the note | Met | `review_has_permission`, `_review_payload` |
| Employee sees only "Action agreed on {date}" | Met | test `test_ac61_ac62_...` |
| Option A raise-it-with-HR | Met, with M-2 and m-1 | |
| An open Ask-HR blocks that person's slip | Met | `check_grooming_before_submit` |
| Marks cancelled, never deleted | Met | no role has delete; removal is cancel |
| Contract staff not marked | Met | R4 and `earns_marks` at pricing |
| Rs 200 Senior / Rs 100 Junior by `dtc_grade` | Met in code (read through the rule set's `grade_field`); DTC's field not checked | |
| Four Rs 0 staff refused until HR sets a grade | Met | R5 |
| Calendar pay month | Met | HR window and limit by calendar month |
| No Hindi | Met | 0 Devanagari characters in the diff |
| `ignore_permissions` ceiling: `payroll_slip.py` 2, no other new bypass | Met | `test_sec16_...` passes; no bypass in the new files |

## 6 · Non-functional check

| Budget (`nfr-budget.md`) | Measured or reasoned | Result |
|---|---|---|
| Queries flat in headcount | Today card flat except rows at the limit (+8 each); month view flat in days (facts read once) | **Fail for rows at the limit** (m-6), pass otherwise |
| Scope stays in the database | Read gates are sub-queries. `_facts` and `pending_reviews` send a team or month list as `IN (...)` (at most a team, or the people marked that month) | Pass at DTC size; note |
| Whitelisted call p95 ≤ 500 ms | Not timed | Not checked |
| Employee screen p95 ≤ 2.5 s on 3G | Not timed | Not checked |
| Workings report +1 query per employee (+445 at DTC) | `04` said it would be measured; `05` does not report it | Not checked |

**The seven dimensions, the impact analysis (`04` §1.6) against the code:**

| Dimension | `04` said | What the code does | Agree? |
|---|---|---|---|
| Performance | degrades slightly: Today ~7 flat, month +3 to +5 | 27 on the Today card plus 8 per row at the limit; month 17-33 | **No - worse than claimed** |
| Security | degrades slightly, then guarded; zero new bypass | Zero bypass is true. But the manager-write rule added after `04` opened B1, and B2 was open | **No at 4758a774**; yes once the uncommitted fix lands |
| Reliability | neutral | Fails closed at submit, but M-1 can make that a permanent refusal | Mostly; M-1 is the gap |
| Scalability | neutral | Flat apart from m-6 | Yes |
| Maintainability | degrades: ~400-line module, ~300 lines of screen | 1,237-line module, ~620 lines of screen, two doctypes, a script report, three views, an Inbox part | **No - about three times the size claimed** |
| Data integrity | neutral | Distinct dates, fail-closed submit, cancel not delete. Race on the 4th mark at 4758a774 (m-5) | Yes, with m-5 |
| Compliance / privacy | degrades by design | As claimed, plus free text on the mark (Surbhi's decision) and the B1/B2 gaps | Yes, with B1/B2 |

## 6b · Compliance verification

| Obligation | Mechanism in the diff | Test | State |
|---|---|---|---|
| SEC-1 one rule, every door | `may_mark` from the controller on validate and submit | `test_ac46_...`, REST tests | Discharged |
| SEC-2 one a day; pay counts days | R10; distinct dates in `month_summary` | `test_ac10a_...`, `test_ac53_...` | Discharged |
| SEC-3 day rules, site time zone | `nowdate()` throughout | refusals tested; time-zone case not | Partial (AC-46) |
| SEC-4 read gate fails closed | own hooks, `1=0`-style conditions | `TestReadGate` | **Partial at 4758a774** (B1) |
| SEC-5 removal | `before_cancel` | `TestRemoval` | Discharged |
| SEC-6 rule set off = nothing | `rule_set_for` first | `test_sec6_...` | Discharged |
| SEC-7 Rs 0 refused; grade HR-only | R5 | `test_ac39_ac41_...`; 063 SEC-17 at DTC not checked | Partial (switch-on item) |
| SEC-8 nothing attached | Comment/ToDo/DocShare guard | `TestNoFreeText` | **Partial at 4758a774** (B2) |
| SEC-9 slip and marks agree | engine line + submit check | `TestSlip` | Discharged in test; M-1 at DTC not checked |
| SEC-10 3% | stop + back-stop | `TestLegalLimit`, `test_ac50_...` | Discharged (interim, counsel) |
| SEC-11 fixed list in code | `REASONS`, controller check | `test_sec11_...` | Discharged for the fixed list; "Other" is Surbhi's change (M-4) |
| SEC-12 no bypass, purpose fence | ceilings; occurrence test | `test_sec16_...`, `test_ac73_...` | Discharged |
| PRIV-1 least fields | field list | `test_ac79_...` | Discharged with the recorded deltas |
| PRIV-2 told the same day | bell + told tick | `TestNotices`, R13 tests | Partial (M-3: not visible on the live portal) |
| PRIV-3 cancel never delete | no delete perm | `test_ac28_...` | Discharged |
| PRIV-4 no purge code | none in the diff | review check | Discharged |
| PRIV-5 one purpose | purpose fence | `test_ac73_...` | Partial: `inbox_api.py` now reads marks but is not on the fence's list; the test passes only because it names the doctype as `grooming.MARK`, not as a string. The fence checks a string, so any reader that imports the constant slips past it (section 8 deletes this reader) |
| PRIV-6 HR views incl. HR's own | three views | `test_ac66_ac67_...` | Partial (m-7) |
| PRIV-7 no personal text in logs | ids-only `refuse()`, notice failure logs the name | `test_priv7_...` | Discharged |
| OPS | - | - | **Unreviewable: no `07-devops-inputs.md`** |

## 7 · Prototype parity (v1 and v2) - every difference I found

Known and not drawn (prototype v3 pending): the "Other" box and its words (D-6); "Raise it with
HR" button, sheet, row lines, HR line and bells (D-7); every 3-mark sentence (D-8). Beyond those:

1. **Mark sheet help line** says "You cannot add your own words." next to the Other box (m-3).
2. **Raise sheet** empty-reason error is the remove sheet's sentence (m-2).
3. **Today card at the legal limit (v2 P53):** v2 draws only "...so this one cannot be marked."
   The build adds "HR has been told... you can raise it with HR." and the button (D-7, known).
4. **Keep sheet:** v2 says "still comes off **his** October pay"; build says "Rahul's" (pronoun
   removed - spec assumption, not her yes).
5. **N2 bell:** v2 "removed the grooming red **he** marked"; build uses the first name (spec
   assumption).
6. **HR desk views (v2 P39, P59, P60):** grouping and sort differ (m-7); the pending list's "Why"
   values differ (m-1).
7. **HR's 3-mark refusal** says "so no more can be marked"; spec W2 says "so this one cannot be
   marked" (D-8 area).
8. **Flag lines** say "the most allowed in a month" where the spec's words say "the most allowed"
   (D-8 area).
9. **Raised row** lacks "HR will talk to [Name]." and the no-login variant (AC-87e) (D-7 area).
10. **"Other" text box:** label "Your reason", hint above the box (spec: "What was wrong", hint
    under it) (D-6 area).

Everything else I compared against v2's string table (Today card heading, help, loading, counts,
not-clocked-in line, sheet info lines, undo lines, remove sheet, ask sheet, keep words, day box,
tile, capped day box, review lines and the manager's note view) matches word for word.

## 8 · What to delete

- **The Inbox part** (`inbox_api._part_grooming`, the `PARTS` and `APPROVAL_PARTS` rows, the
  `next-frame.js` label, about 60 lines). It serves `/hrms-employee-next`, a preview page that is
  not on production and belongs to the discarded redesign. The spec's reach (§1) does not list
  `inbox_api.py`. It changes HR's Inbox total in a shared hot file. What breaks if deleted: one
  test (`test_y4_the_inbox_lists_an_ask...`) and nothing a user sees. Delete it, and decide the
  live bell under M-3.
- **The "Other" word list, unless Surbhi says yes** (M-4). It was removed by the spec's subtract
  pass.
- **`hr_only()`** (`grooming.py:1062`): a one-caller helper for `v.get("capacity") == "HR"`. Nit.

## 9 · What was done well

- **One rule, every door.** `may_mark` is called by the controller on validate and submit, and
  every screen uses the same function for its buttons. The screen and the guard cannot disagree,
  and the test `test_sec1n_the_screens_flag_equals_may_mark_for_every_row` proves it.
- **The flag is worked out, never stored.** No field, no job, nothing to drift from the marks.
- **Fails closed at payroll.** The submit check re-prices with the same `month_summary`, so there
  is one definition of the price, and a stale or disputed slip cannot go out.
- **Review note as its own insert-only record with `track_changes` 0**, so no Version row ever
  holds the text. That is the right fix for the manager-note leak (ALV-216) without touching it.
- **Tests run as logins with no User Permission rows** - DTC's real shape - and the guards were
  broken on purpose to see the tests fail.
- **Zero new `ignore_permissions`**, and `payroll_slip.py` was put under a ceiling it never had.

## 10 · Open questions

| Kind | Question | Who | Ranked meanwhile |
|---|---|---|---|
| Must know | Will the uncommitted fixes for B1/B2 (and M1, M2) be committed with tests? | engineer | BLOCK until then |
| Must know | GRV, Red Value, Green Value at DTC: `depends_on_payment_days` and `round_to_the_nearest_integer` both 0? (M-1) | DevOps / HR at switch-on | P2, switch-on blocker |
| Must know | Yes to D-6, D-7, D-8 words, or prototype v3? | Surbhi | Those screens do not ship until answered |
| Should know | Live portal notices: accept or option A? (M-3) | Surbhi | P2 |
| Should know | "Other" word floor: which words? (M-4) | Surbhi with counsel | P2 |
| Nice to know | Delete the Inbox part? | Surbhi / PM | P3 |

## 11 · Confidence

- **Proven:** the tests and checks listed in section 1; B2's upload gate, M-2, m-1 and the query
  counts by probe on `test066g` (inside a transaction that was rolled back; no files written);
  everything else in sections 3-7 marked "proven by reading" from the files at 4758a774.
- **Inferred:** B1 at 4758a774 (code trace through Frappe 16.33's own source; the probe ran on
  the fixed code); M-1 (Frappe HR's slip code read in the container; DTC's settings unseen); m-5.
- **Not checked:** anything on DTC or dev; latency; the browser renders; the full test suite;
  the uncommitted diff as a whole; whether the local Frappe version matches production (bell
  e-mail behaviour for "Alert" notices depends on it - on 16.33 they send no e-mail).
- **Unreviewable:** OPS (no `07`); counsel's answers (Q-C1, Q-C4, Q-C5).

## Subtract pass

I removed from this review: a finding that the bell would also e-mail (checked Frappe 16.33:
"Alert" notices never e-mail); a finding on a duplicate `Comment` key in `hooks.py` (checked: no
duplicate); repeating the security verification's B3, M1, M2, m3, m4, m5 in full (referenced
instead); a finding on string-built SQL in the permission hooks (it uses `frappe.db.escape`, the
standard pattern for those hooks).

---

## Second look · 25 Oct 2026 (fix commits 6c899251, 59c87eda, bcf4d48f)

**Verdict: SHIP WITH FIXES.** Both blockers (B1, B2) are fixed and I could not break them. One
fix does not do what its comment says: **two marks at the same moment can still make a 4th live
mark** (proven by a real race). The pay slip still charges at most 3 days, so no wrong money.
That, the word list, and the decisions still open from the first look need a fix or Surbhi's
written yes before release.

This is advice. Surbhi decides. "Ship" means ready to show for deploy approval, nothing more.

**What I ran (proven).** Branch `slice/066-grooming` at bcf4d48f, worktree clean. Container
`hrlocal-066g`, site `test066g`, same `grooming.py` checksum as the branch. No merge commits and no
one else's commits came in: the three new commits are the engineer's, and they touch only the
eight 066 files.
- Repo checks: `check_app_integrity` OK (821), design system, tag balance, brand spelling, API
  paths, tracked keys, demo passwords, `check_attendance_strip`, `check_portal_handlers`,
  `check_undefined_js`: all OK.
- Tests on `test066g` (25 Oct, so no day-of-month skips): `test_grooming_066` 59 + 1 OK,
  `test_grooming_cap_066` 31 OK, `test_pay_slip_marks_067` 18 + 2 OK, `test_payroll_month` 29 OK,
  `test_payroll_rules` 76 OK, `test_payroll_flags` 9 OK, `test_payroll_reprocess` 12 OK,
  `test_portal_security_010` 45 + 5 OK. **287 run, 0 failed.**
- The old probe, rebuilt and extended (`probe066b.py` in the session scratchpad), in one
  transaction, rolled back. A real two-process race, committed, then deleted (0 marks left).
- Not run: a browser pass; the full suite; anything on DTC or dev.

### Each finding, tried

| Finding | State | How I tried to break it |
|---|---|---|
| **B1** empty save by a manager | **Fixed (proven)** | As Ravi on HR's old mark: `client.get`, `set_value {}`, `set_value asked_on ""`, an empty PUT-style save, `client.save` and `savedocs` **with `flags: {grooming_raise_with_hr: true}` sent in the body**: all PermissionError. `modified_by` unchanged; `raised_on` still empty. Frappe drops `flags` from any body (`RESERVED_KEYWORDS`, base_document.py:1597-1605; `api/v1.py:54`), so the raise flag cannot be sent from outside. HR's own empty save is refused too ("Nothing on this grooming red can be changed that way."). The real `raise_with_hr` still works and returns only the name. |
| **B2** file or tag on a mark | **Fixed (proven)** | `add_tag` and bulk `add_tags` as HR and as the manager; a public `File` insert as HR; a private file inserted bare and **attached afterwards**; a "Like": all refused. 0 File rows, 0 Tag Link rows. |
| **B3** "Other" misses the 01c words | **Reversed on purpose - decision needed** | See S-2 below. 6c899251 added beard, hair, tattoo, jewellery; bcf4d48f removed them again under my M-4. |
| **M1** race on the 4th mark | **Not fixed at marking (proven); money held** | See S-1 below. |
| **M2** leaver reads own marks | **Fixed (proven)** | Ravi set to Left: list empty, `client.get` on the mark he raised refused. Test `test_m2_a_marker_who_has_left_reads_nothing`. |
| **M-1** slip held for ever | **Fixed (proven)** | GRV with **both** `depends_on_payment_days` and `round_to_the_nearest_integer` on, 15 paid days, marks worth Rs 348.39: slip row Rs 169, submit check passes. Marks changed to Rs 400: refused, as it should be. Settings restored (0, 0) after rollback. The engineer's test covers payment days only, not rounding. |
| **M-2** second raise in a month | **Fixed (proven)** | Raise, HR removes that mark, new mark back to 3: `may_raise` says RAISE2. Test exists. |
| **m-1** report reason | **Fixed (proven)** | Report says "Raised again by Ravi G066"; "3 grooming reds, the most allowed". |
| **m-2** raise sheet error | **Fixed (read)** | `portal.js` gmConfirm: only the remove sheet says "Choose why you are removing it." Its test is a string match on the source, so it proves the line exists, not the behaviour. |
| **m-6** Today card query loop | **Fixed (proven by test)** | `_raise_states` reads all rows at the limit in 2 queries; `test_m6_...` counts SQL with 1 and with 3 people at the limit and gets the same number. |
| **M-4** word list | **Changed - decision still needed** | See S-2. |
| Review note | **Holds (proven)** | Manager (Ravi) reads the note through the month view; subject (Rahul) `client.get` refused, list empty, payload is `{"state": "cleared", ..., "on": "Sun 25 Oct"}` with no note; skip-level (Sunil) refused. |
| `ignore_permissions` ceilings | **Unchanged (proven)** | `payroll_slip.py` still 2 (same two lines); no new bypass in `grooming.py`, the controller or the report; `test_portal_security_010.py` not touched; its ceiling test passes. |

### Still open

**S-1 · Major, P2. The row lock does not stop the 4th mark.** *Proven by a real race.*
- *State:* Kiran has 2 marks this month, committed. HR marks 23 Oct and holds the transaction for
  8 s. The manager marks today at the same moment.
- *What happens:* the manager's request **waits 9.6 s on the lock, then saves anyway.** Kiran ends
  with **4 live marks**.
- *Why:* the database runs REPEATABLE-READ (checked: `@@tx_isolation`). The second request read
  other rows before it reached the lock in `validate` (`grooming_mark.py:38`), so its view of the
  marks is fixed from before the first mark was committed. The count in `_decide` is an ordinary
  read, so it still sees 2. The lock makes the second request wait; it does not make it see more.
- *Harm:* the slip cap (`payroll_slip.py:142`, `min(..., MONTH_MAX)`) keeps the money at 3 days.
  But the person, the manager and HR see 4 grooming reds, against Surbhi's "3, for everyone", and
  two bells go out for a month that should have stopped.
- *The comment at `grooming_mark.py:34-37` says the second request "counts 3". It does not.*
- *Smallest fix:* after the lock, count the person's live marks for the month with a locking read
  (`... FOR UPDATE`, which always sees the newest committed rows) and refuse at 3. Plus a test that
  needs two connections, or a written note that only the slip cap is tested.
- *Rung:* 3 (correctness of the business rule). No money at stake, so P2, not P1.

**S-2 · Major, P2. The "Other" floor is now weaker than the code first reviewed, and B3 was
undone.** *Proven by running the list.*
- *State:* the list in bcf4d48f dropped `skin`, `weight`, `fat`, `body` (all in 4758a774) and does not
  add the 01c SEC-11 words security asked for in B3.
- *What happens now:* allowed - "Too fat for uniform", "Skin rash", "Limping, wrong shoes", "Smells
  bad", "Beard not trimmed", "Hair too long", "Moustache untidy", "Tattoo showing", "Burkha on"
  (spelling the list does not know). Refused - "Turban untidy", "Sikh beard", "Muslim cap", "Pregnancy
  belt", and also "Childish behaviour" (false refusal from `child*`).
- *Why it is wrong:* my M-4 said keep security's floor and drop only words that are **also
  clothing words** (dirty, head, ring, cross). Body weight, skin and limp are not clothing words;
  they are about the person's body or health, which the hint itself rules out. Beard and hair are
  the hard case: for a Sikh or Muslim employee a beard is religious. Allowing them is a choice, and
  it was made by the builder, not by Surbhi or counsel. The test was changed to match
  ("Too much weight" was removed from the refused examples).
- *Conflict:* rung 2 (privacy) against rung 3 (free text the business asked for). **Decision
  needed: Surbhi with counsel (Q-C4).** My recommendation: put back body, skin, weight, fat, limp,
  smell; add `burkha`; let Surbhi decide beard and hair in writing. The free text itself stays a
  switch-on blocker in `06b` §5.

**S-3 · Minor, P3. The slip can now show less than the person's screen.** *Proven.* With payment
days on, the slip line was Rs 169 while the marks' price (on the person's tile and day box) was
Rs 348.39. The slip now submits, which was the point. But the person sees two figures. Release
check: GRV at DTC has `depends_on_payment_days` = 0 and `round_to_the_nearest_integer` = 0 (same
as before; not checked at DTC).

**Carried from the first look, not touched by these commits:**
- Prototype v3 / Surbhi's yes to D-6, D-7, D-8 words. **Those screens still do not ship until she
  answers.** (Her rule: every difference from the approved prototype needs her yes.)
- M-3 live portal bell: accept in writing or option A.
- No `07-devops-inputs.md`: the OPS axis is still unreviewable.
- The Inbox part (`inbox_api._part_grooming`) is still there; my recommendation to delete it stands.
- m-3, m-4, m-7, AC-46 time-zone test, AC-54 `if row:` test: unchanged.
- Switch-on blockers in `06b` §5 (ALV-215 grade field, counsel, retention): unchanged.

### What was done well in the fixes
- **The raise flag lives on the document in memory.** Frappe drops `flags` from every body, so the
  manager's write right now exists only inside `raise_with_hr`. That closes B1 with no new role
  and no new field.
- **The slip check moved to the right comparison.** The engine's record against the marks, plus
  "the slip carries that record", fails closed on a real change and lets Frappe's own scaling pass.
- **One verdict function for the raise** (`_raise_verdict`) used by both `may_raise` and the
  batched Today card, so the two cannot disagree.

### Subtract pass
Removed from this section: a worry that the empty-save refusal would break `ask` and `keep` (they
change a field, so they pass - tests green); a note on the `1=0` start of the list gate (correct);
a re-check of the m-6 count by hand (the test counts SQL calls and is sound).

### Confidence
- **Proven:** everything marked proven above, on `test066g` at bcf4d48f.
- **Inferred:** that a real browser request reads rows before `validate` the same way my race
  script did. Frappe reads the user and permissions first, so I expect it, but I did not race two
  HTTP requests.
- **Not checked:** DTC's GRV settings; a browser pass; the full test suite; dev.
