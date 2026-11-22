---
slice: 086-manager-held-days
artifact: 02-functional-spec
author: hrms-business-analyst
date: 2026-11-21
status: draft for Surbhi. Recommendations only. Nothing is approved, built, pushed or deployed.
risk tier: 1 (files requests that release pay; who may act for whom; personal free text). **Written for case A (counsel, 21 Nov). Case B is kept only as a note (section 15).**
inputs: 01-product-brief.md (21 Nov update and gate), 01b-ux-design.md (v2, H-1..H-11, design gate), prototype-v2.html, 01c (SEC-1..8, PRIV-1..4, C1, C2), 07-devops-inputs.md §1-§3 and Surbhi's decisions, 087's code and spec, and **counsel's answer of 21 Nov 2026 (relayed by Surbhi): case A**
---

# 086 · Functional spec: a manager sends the missing times for held days to HR

## 0 · The short version

**Bad news first.**

1. **Six things the earlier documents said are not true in the code, or are not yet decided. They are in section 15 and change what gets built.** The two that matter most:
   - **The server has no check that a time "fits the punches" or "is not in the future".** On 087's branch the only time checks are: a repeat within 2 minutes of a punch (`punch_fix._check_not_a_repeat`, `punch_fix.py:355`) and a future *day* (`raise_for_report`). The kind of punch (In or Out) is worked out from where the time falls (`punch_fix.derive`, `punch_fix.py:224`) and **overwrites** what the caller sent. So the Change link (H-11) would be a label only: a manager could flip to "arrival", type a time after the punch, and the server would quietly file a leaving. **086 adds two small refusals in its own send call** (AC-25, AC-26). This is the one real new rule in the slice.
   - **The brief assumed a manager's pending request does not stop the employee filing their own time. That is false.** Stock Frappe HR refuses any second request for the same employee and day while one is not cancelled (`hrms/hr/doctype/attendance_request/attendance_request.py:109-132`, `docstatus < 2`). The employee's way out is "Not right" with a time (087 AC-110).
2. **ALV-425 (anyone with the approve right skips the direct-report check) is closed only for the new send call, not for `raise_for_report` itself.** The hole is the `if not _may_review():` guard inside `raise_for_report`. SEC-1 puts a per-row direct-report check in the new call, so the bulk door is shut. The old single door stays open. A one-line change inside `raise_for_report` would shut both, but it changes 087's code and the HR path. **Surbhi to choose (section 15, F1). My recommendation: shut both.**
3. **Counsel answered on 21 Nov (relayed by Surbhi): case A.** A manager adding a time in the employee's favour needs no Confirm. What counsel asks instead: HR's approval, a mandatory reason, and a notice of manager-added times on the monthly register or payslip (**ALV-426, new**). So: (a) the request is **not** marked for Confirm; (b) staff with **no login** get a time box like everyone else; (c) **ALV-426 blocks release of 086** and is **not** built here (section 15, F10). **086 only ever adds a missing time. It never cuts time and never sets a punch aside, so the condition that would bring Confirm back never arises** (AC-55). Case B is a note only (section 15, F11).
4. **Release order is fixed by Surbhi:** 087 on main and proved first, then 086. If counsel is late, the list ships without the send bar.

**Rung: 4, a small amount of new code, on the existing Whole team page.** No new DocType, field, setting, patch, queue or app (OPS-61). **Counts: 9 stories, 26 points. 67 acceptance criteria (case A). Ready verdict: ready to build, with conditions (section 17).**

## 1 · What I read, and on which checkout

- **086 worktree** `slice/086-manager-held-days` at `6a82d930` (docs only).
- **087 worktree** `slice/087-attendance-follows-punches` at `ae249815`. **Newer than the `c05704bc` that 01c read.** Read this session: `punch_fix.py` 110-402 (`is_punch_fix`, `day_state`, `derive`, `outcome`, `validate`, `_own_the_confirm_fields`, `send`); `attendance_correction.py` `raise_for_report` (line 2386 to the end), `team_days` (2155-2330), `_held_request_fields` (1252), the review-status reader (about 1090-1110), `_flag` (2092), `_reports_to` in `attendance_analytics.py` (106); `held_day.py` `validate_missing_time` (242), `extra_when` (301); stock `attendance_request.py` 109-132; 087's `02-functional-spec.md` section 18 and the end (counsel's conditions, decisions of 21 Nov).
- **Not run:** no test, no bench, no site, no browser. Every statement about "the server does X" is code reading.
- **Not read:** `acHeldForm` and `portal.js` (so the one-punch inference rule is **[UNVERIFIED, engineer to confirm]**); `confirm()` and `refuse_unconfirmed` bodies (read by 01c only); the stock role rows on Attendance Request (quoted from 01c, not re-read); anything about delete protection on a filed request.
- **Cross-module reach.** `alvoraa_portal` (the page, the new send call, `attendance_correction`, `punch_fix`, `held_day`); `hrms` (stock Attendance Request overlap check, Employee `reports_to` and `user_id`); `frappe` (permissions, rate limit, CSRF). **Not touched:** `alvoraa_goals`, `alvox_compensation`, `erpnext`. HRMS domains: attendance (Held status, requests), payroll (a Held day is held pay; approval releases it; 087's slip refresh), org structure (`reports_to`). Not leaves, appraisals, goals, compensation, learning.
- **Personas:** Line manager (the user), HR User/Manager (decides each request), Employee (is told, may say Not right), CXO (sees nothing new; counts as HR for scope only if they hold an HR role), plus the frontline supervisor on a phone.

## 2 · Questioning the ask

- **Symptom or cause?** The brief traces the problem to a real cause: the manager is the person who knows what happened, and today the daily send to HR is outside the product (brief, 21 Nov). Not a reminder problem. Accepted.
- **What decision does this drive, and who makes it?** HR decides each request, as today. The manager only vouches. The system decides nothing. Good.
- **Automating chaos?** The risk is the one the brief names: a manager invents times. The design answers it with no blanket time, the real punches beside the box, a reason per row, the employee told on their day sheet and able to say Not right, HR's look at each request, and ALV-426's notice on the register or payslip. It is reduced, not removed (01c R1).

## 3 · Gap analysis (comes first)

"Looked" names the file I opened. Verdicts: Configure / Extend / Build new / Drop.

| # | Requirement | What exists today (read) | Verdict | Cost |
|---|---|---|---|---|
| G1 | Manager lists held days of direct reports with no request | `team_days` (`attendance_correction.py:2155`) reads **every** Attendance row for the period, reads punches, builds flags in Python, then pages. Its `only` filter is a *flag* (`no_clock_out` is punch-count based, `_flag` line 2092), not the Held status. `_reports_to(me, deep=False)` gives direct reports (`attendance_analytics.py:106`, Active only) | **Extend.** Add the Held status to the Attendance query **before** the punch read and exclude days with an open request. Engineer's choice: a `held` option on `team_days`, or a small sibling function. **Recommendation: the sibling**, because `team_days` counts and pages by flag and OPS-53 needs a fixed query count. Same scope helpers either way | M |
| G2 | The "Held" chip, day control, rows, bar, confirm, banner | The Whole team page: `trChips` etc. in `portal.js` (about line 16331, seen by grep only). No Held concept on it today (01b WT2) | **Extend** (screen code in the existing file) | M |
| G3 | File one held-day time for one report | `raise_for_report` (`attendance_correction.py:2386`): POST only, no `ignore_permissions`, reason required (087 AC-102), held fields via `_held_request_fields` (1252), stamp "Raised by X on behalf of the employee" | **Configure/reuse as is** | 0 |
| G4 | Send many in one call, one result per day | Nothing. A browser loop on the single call would hit nginx `/api/` 120 a minute (07 OPS-41) | **Build new, small:** a loop around `raise_for_report`, one savepoint per row. Cheaper rung rejected: browser loop (rate limit, half-done state the manager cannot see) | M |
| G5 | Direct-report check on every caller | `raise_for_report` checks direct reports only `if not _may_review()`. Anyone who may review skips it (ALV-425) | **Extend:** per-row check in the new call (SEC-1). Optional: fix at source (F1) | S |
| G6 | One open request per person per day | Stock overlap check, `docstatus < 2`, read-then-throw (`attendance_request.py:109-132`). Not safe against two calls at the same instant | **Extend:** lock the day's Attendance row (`for_update`, as `punch_fix.day_row` already supports at line 135) inside each row's savepoint | S |
| G7 | Reason on every request | 087 AC-102 in `raise_for_report` (read) | **Reuse** | 0 |
| G8 | **Case A: a manager's held-day time fix needs no Confirm** | 087 `_own_the_confirm_fields` (`punch_fix.py:314`) marks every request filed by anyone but the employee (read). It runs after `alvoraa_for_held_day` is set in `validate` (read, lines 271-312), so it can see "this is a held-day time fix". Approval is refused until confirmed (`refuse_unconfirmed`: **seen in 01c, not re-read**) | **Extend, one condition in one place:** do not mark when the request is a held-day time add with no set-aside, filed by the employee's direct manager. HR-filed and every other request stay marked. No setting | S |
| G9 | Staff with no login | Under case A nothing is needed: the request needs no Confirm, so a person with no login is filed for like anyone else. The no-login refusal drawn in prototype-v2 (case B) is **dropped** | **Drop** | 0 |
| G10 | Refuse a future time; refuse an In/Out that disagrees with the time | **Nothing on the server** (see section 0). `derive` overwrites the caller's In/Out | **Build new, tiny**, in the send call, by *calling* `punch_fix.derive` (no copy of the rule) and comparing | S |
| G11 | Stamp with manager id and "one of n" (SEC-8) | `raise_for_report` stamp has the name only | **Extend:** one line in the stamp. Touches 087's code and any 087 test that asserts the old stamp text | S |
| G12 | Rate limit, 30 sends an hour | `field_app_limits._limited(field, source, limit, window)` exists (read signature, line 59). 01c cites `SELF_KEY` and `expense_evidence.py:620-635` as the existing use; **not read by me** | **Reuse** | S |
| G13 | Employee sees what was said in their name; HR sees it | 087's day sheet and HR card. The Confirm block does **not** show for an unmarked request, so case A needs a **notice with Not right** on the day sheet (drawn in prototype-v2, Case A). Whether `confirm`'s Not right works on an unmarked request: **[UNVERIFIED, engineer to confirm]** | **Extend** (small) | S |
| G16 | Manager-added times shown on the monthly register or payslip (counsel's third condition, **ALV-426**) | Not read by me: the register and payslip print code | **Out of 086's build** (section 15, F10) | not sized |
| G14 | Held chip vs "No clock-out" chip (UX-1) | Both would show. `held_day._switch_on(company)` says whether the hold is on | **Extend:** where the hold is on, show Held and hide "No clock-out". **Needs Surbhi's explicit yes** (not decided in writing) | S |
| G15 | Answer-lost recheck | 085 AC-30 guard, cited by 01b and 07; **not read by me** | **Extend:** one read-only call (OPS-58) | S |

### Recommend dropping (not in this slice)

Each of these was proposed somewhere and would be scope nobody asked for.

| Dropped | Reason |
|---|---|
| Bulk approval by HR; one time or one reason for many; a "same reason as above" link | Pay at stake; refused in 085 and by counsel's condition |
| "Take back" for the manager (UX-5) | Wrong time is caught by the confirm list, the employee's Not right and HR. Add only if HR's decline count shows it |
| Far-from-shift refusal ("more than 4 hours after the shift") | Only an assumption in 01b. G10's two refusals cover the impossible cases |
| Hiding the old "Ask HR to fix" button on Held rows (01b item 13, Q5) | Q5 is unanswered and the Held view has its own boxes. Leave the Everything view unchanged. Engineer reports what the old button does on a Held day (section 15) |
| A background job and progress bar; a daily cap per manager (OPS-R-1); an nginx change; a cache; a new field or setting for case A/B; the no-login refusal (case B only); a per-manager count, ranking or reminder | OPS-55, OPS-R-1 (Surbhi: no cap), brief section 7, 01c |
| A "has a login" detail beyond yes/no; a new batch-id field | PRIV-3; stamp text carries "one of n" |

**Single source of truth.** Whether a day is Held: `Attendance.status = "Held"` (085). Whether it has a request: Attendance Request rows with `docstatus < 2` for that employee and day. Who is a direct report: `Employee.reports_to` with `status = "Active"`. The page never keeps its own copy.

## 4 · Process flow (the manager's day, with the unhappy paths)

1. Manager opens Attendance, Whole team. The page loads the Held view for the latest day that has rows. *(Decision: no rows at all → "Nothing is held" state, flow ends.)*
2. For each row she knows, she reads the real punches, types the time (and the gap for 3 or more punches) and her reason. *(One-punch row: she may press Change if the inferred end is wrong.)* A row with both time and reason shows Ready.
3. A person with no login shows the same boxes as everyone else. *(Case A.)*
4. The bar says "N days ready". She presses Send N to HR. **One** confirm lists person, day, time and the reason typed. She presses Send.
5. One call carries up to 50 rows. The server, for each row in its own savepoint: checks the caller, the row's scope, the login, the time, locks the day, files through `raise_for_report`.
6. The answer has one entry per row. Sent rows leave the list. Refused rows stay with their time, reason and a sentence. The banner says "N of M sent".
7. **Unhappy:** offline before sending (nothing sent, typed values stay); answer lost (the page asks the server what went, never re-sends); a day released while the page was open (that row refused: "no longer held"); more than 50 (first 50 go); lock wait (loop stops, the rest "not sent").
8. Each employee sees a notice on their day sheet and may say Not right. HR decides each one (087). The notice on the monthly register or payslip is ALV-426, not built here.

## 5 · Epic and user stories

**Epic 086: A line manager files the missing times for their direct reports' held days in one send, with a reason on each, and HR still decides each one.** Personas from `product-context.md`. Sizes 1/2/3/5/8; none is an 8. Order: US-1 and US-3 first (server), then the screens.

| ID | Story | Pts | INVEST note | Prototype | SEC / PRIV / OPS | ACs |
|---|---|---|---|---|---|---|
| US-1 | *As a* line manager *I want* the Whole team page to show only the held days of my direct reports that nobody has asked HR about yet, one day at a time *so that* I see exactly what needs my word | 5 | Valuable alone (a list with no send is still the founder's "filter the held days"). Small enough: one read, one chip, one day control | H-1, H-2, H-7, H-10 | SEC-1 (list), PRIV-3, OPS-39, 49, 53, 54 | AC-1..10 |
| US-2 | *As a* line manager *I want* a time box and a reason box on each held row, with the day's real punches beside them and a way to correct the end the page guessed *so that* I say what I know and nothing is filled in for me | 3 | Depends on US-1. Testable by what it sends | H-3, H-4, H-5, H-10, H-11 | PRIV-1, PRIV-2 (warning line), PRIV-4 | AC-11..17 |
| US-3 | *As a* line manager *I want* one call that files my rows to HR and tells me, per day, what went *so that* I do not open ten month pages | 5 | Independent of the screens (testable by calling it). The riskiest story: Tier 1 | H-6 | SEC-1..5, SEC-8, PRIV-1, PRIV-2, OPS-40, 41, 44, 48, 55..61 | AC-18..42 |
| US-4 | *As a* line manager *I want* one send bar, one confirm that lists what I am saying, and a result I can trust, even when the network drops *so that* nothing goes to HR that I did not mean and nothing is lost silently | 5 | Depends on US-3. Words and counts that must add up | H-5, H-6, H-9, H-10 | SEC-4, SEC-5, PRIV-4, OPS-58, 59 | AC-43..53 |
| US-5 | *As a* line manager *I want* my missing time for a held day to go to HR without waiting for the employee to confirm, *and as an* employee *I want* to be told and to be able to say Not right *so that* staff who never open the app are still paid, and nobody has a time filed in their name unseen | 2 | Case A (counsel, 21 Nov). One condition in `punch_fix._own_the_confirm_fields` plus a notice. Valuable: without it a no-login report can never be helped | H-8 (Case A variant) | SEC-6, PRIV-3 | AC-54..56 |
| US-6 | *As an* employee *I must not* have my filed request changed or deleted by the manager who filed it, *so that* what HR decides is what the manager filed and what I was told | 2 | A must-not story. May be built in 087 or here (engineer says where) | | SEC-7, A7, A8 | AC-57, 58 |
| US-7 | *As an* HR manager *I want* to read who vouched for each time, as whose manager, with the reason and the real punches, and to approve without waiting for a Confirm, *so that* I decide on evidence and a year later the record can be rebuilt | 2 | Mostly 087's HR card. 086 adds the stamp and the tests | (087 v4 HR card) | SEC-8, PRIV-3 | AC-36, 37, 59..62 |
| US-8 | *As a* line manager's **colleague, a guest or a stranger** *I must not* read or send anything here, *and no log, error or message may hold a reason* *so that* HR-grade data stays in its lane | 1 | Must-not story; tests only, no new code | | SEC-1, SEC-4, PRIV-2, PRIV-3, OPS-50, 60 | AC-18, 22..24, 63 |
| US-9 | *As a* frontline supervisor on a shared phone *I want* the page to work at 360 px and keep nothing on the handset *so that* the next person on it sees nothing | 1 | Part of US-2 and US-4's build; split out so the check is not forgotten | H-10 | PRIV-4, OPS-46 | AC-52, 64..67 |

**Points: 5+3+5+5+2+2+2+1+1 = 26.**

### YouTrack-ready table (do not create issues; Surbhi's call)

| Summary | Description | Persona | Pts | ACs | Requirements |
|---|---|---|---|---|---|
| 086-1 Held list for my direct reports | Held chip, one day at a time, only days with no open request, direct reports only, server filter before punch read | Line manager | 5 | AC-1..10 | SEC-1, PRIV-3, OPS-39, 49, 53, 54 |
| 086-2 Time and reason on each held row | Time box, Change link, 087 timeline for 3+ punches, required reason, Ready | Line manager | 3 | AC-11..17 | PRIV-1, 2, 4 |
| 086-3 Send call | One POST, max 50, per-row savepoint and result, scope and time refusals, stamp, rate limit, recheck call | Line manager | 5 | AC-18..42 | SEC-1..5, 8; OPS-40, 41, 44, 48, 55..61 |
| 086-4 Send bar, confirm, banner | One confirm with reasons, results, answer lost | Line manager | 5 | AC-43..53 | SEC-4, 5; PRIV-4; OPS-58, 59 |
| 086-5 Case A: no Confirm, notice to the employee | One condition in `_own_the_confirm_fields`; never cuts or sets aside; notice with Not right | Line manager, Employee | 2 | AC-54..56 | SEC-6 |
| 086-6 Filed request cannot be changed or deleted by the filer | Refuse the filer's edit and delete after filing | Employee | 2 | AC-57, 58 | SEC-7 |
| 086-7 HR sees who vouched | Stamp with id and batch; HR card; approve without Confirm | HR | 2 | AC-36, 37, 59..62 | SEC-8, PRIV-3 |
| 086-8 Nothing leaks, nobody strays | Logs, errors, guest, strangers | All | 1 | AC-18, 22..24, 63 | PRIV-2, SEC-1, 4 |
| 086-9 Phone, accessibility, nothing stored | 360 px, 44 px targets, no storage | Frontline supervisor | 1 | AC-52, 64..67 | PRIV-4, OPS-46 |

## 6 · Data model

**Nothing new.** No DocType, no Custom Field, no patch, no fixture (OPS-61). Every item reuses a field that exists; why no new field is enough:

| Need | Existing field | Why no new field |
|---|---|---|
| The missing time, In/Out | Attendance Request `alvoraa_missing_time`, `alvoraa_missing_log` (set by `_held_request_fields`, 1252; `alvoraa_missing_log` then overwritten by `derive` in `punch_fix.validate`) | already built (085, 087) |
| The manager's reason | `explanation` (087 AC-101/102 stores it there) | already the home of the reason |
| Who filed, as whose manager, one of n | `owner`, `creation`, and the stamp text appended to `explanation` | SEC-8: text, not a field. A batch-id field was removed (01c subtract) |
| Confirm state | `alvoraa_needs_confirm` (set to 0 by the case A condition), `alvoraa_confirmed_by/_on` stay empty (087) | 087's |

**The list response (read-only, new function) carries per row:** employee id, employee name, the day, the day's punches (time and source), the shift window, and what the screen needs to draw the strip. **It carries no** GPS, photo, `user_id`, email, login yes/no, or another person's punches (PRIV-3, OPS-54).

**The send request, per row, five keys only:** `employee`, `date`, `time`, `in_or_out`, `reason`. Any other key is ignored (SEC-3).

**The send answer:** per row `{employee, date, ok, request (name) or the plain sentence}`, plus `sent` and `not_sent` counts that must equal the entries. **Never the reason, the typed time, punches or slip figures** (OPS-48, PRIV-2).

*(Function names are proposals, not read from source: [UNVERIFIED, engineer to name].)*

## 7 · States and transitions

No new workflow and no new state. A request created by the new call is the 087 request, **not marked for Confirm (case A)**: Waiting → HR approves or declines (the employee may also say Not right, AC-56). Terminal: approved (day released), declined, withdrawn (employee only). Reversible: nothing, except the employee's own withdraw. **The manager's page has no state of its own**: a row is either listed (Held, no open request) or it is not.

| Request state (existing) | Listed on 086's page? | Who acts next |
|---|---|---|
| none | **Yes** | manager |
| Waiting for HR (case A: no Confirm step) | No | HR (the employee may say Not right) |
| Approved | No (the day is no longer Held) | none |
| Declined or withdrawn **as a draft** (`docstatus 0`, label Declined/Withdrawn; see the status reader near line 1090) | **No**, because the stock overlap check still sees it (`docstatus < 2`) and would refuse a new request | HR or the employee. **[UNVERIFIED, engineer to confirm at runtime; section 15 F5]** |
| Cancelled (`docstatus 2`) | Yes again | manager |

## 8 · Permission and visibility matrix

Level on the two new calls. "Direct reports" = `Employee.reports_to` = the caller, `status` Active. Stock role rows on Attendance Request are quoted from 01c (not re-read by me).

| Actor | List held days | Send call | Recheck call | Notes (the negative cases) |
|---|---|---|---|---|
| Line manager (Active Employee, has direct reports, tenant manager switch on) | **Own direct reports only** | **Own direct reports only**, ≤ 50 rows, 30 sends an hour | own sends only | **Must not:** skip-level, another manager's report, another company's person, a leaver, themselves, an id the page never offered |
| Manager whose own Employee is Left (login still on) | empty | nothing filed | nothing | `_employee_for` finds no Active record |
| Manager when the tenant switch `manager_on_behalf_on()` is "0" | empty | nothing filed | nothing | existing switch, `raise_for_report` refuses |
| Login with the submit right, no HR role (Shift Supervisor) | own direct reports only | own direct reports only (**closes ALV-425 for this door**) | own | today `raise_for_report` alone would let it file for anyone |
| HR User / HR Manager | own direct reports only (acting stops at direct for HR too: comment in `team_days`, read) | own direct reports only | own | HR decides requests elsewhere; this door is not HR's tool. Approval of a manager's held-day request needs no Confirm (case A); HR-filed requests still do (087 AC-105) |
| CXO | as their role: HR role → as HR; no Employee record → nothing | nothing (no Active Employee) | nothing | no company figure, no count, nothing new |
| Employee with no reports | "Nobody reports to you, so there is nothing to review here." (existing sentence) | nothing | nothing | |
| Employee whose day it is | cannot list | cannot send for others | | sees a notice with the time and reason on their day sheet and may say Not right; **must not** be filed for without being able to see it (no-login staff are told through ALV-426) |
| A colleague | nothing | nothing | nothing | another person's request and reason are unreadable |
| Guest | refused | refused | refused | not `allow_guest` |
| Administrator | nothing useful | refused: **no Active Employee record** | | 087 treats Administrator as break-glass for Confirm only |

**Row-level rules:** own direct reports; own company only through the reports link (a direct report in another company is allowed by the link; the hold switch is per company, so a company with the hold off has no Held days to list).

**After filing:** the filer cannot change or delete a request (US-6). Only `confirm` (employee) and `decide` (HR) change its state.

## 9 · Acceptance criteria

Oracle in every one. Written for case A (counsel, 21 Nov). **Test names are not written yet** (the test engineer names them at stage 04); the traceability table in section 14 says so.

### US-1 · The list

- **AC-1** Given manager M with a direct report R1 (Held day, no request) and a skip-level report S (Held day), when M opens Whole team and picks Held, then the list response holds R1's row and no row for S, and no row for M. *Oracle: set of employee ids in the response ⊆ M's direct reports.*
- **AC-2** Given R1's Held day has an Attendance Request with `docstatus < 2` (waiting for HR), when M opens the list, then that day is absent. Given the request is cancelled (`docstatus 2`), the day is back. *Oracle: row present or absent.*
- **AC-3** Given 11 qualifying rows, then the chip reads "Held 11", the line reads "11 held days need a time from you" (singular text for 1, from the prototype), and the chip number equals the number of rows under it across all pages at the current Show setting. With 0 rows the chip is not drawn.
- **AC-4** Show lists the days that have rows, latest first, default the latest day, plus "All days in this period" (period: the existing 92-day limit). A day with no rows left drops out of the list. *Oracle: option list equals the days with rows.*
- **AC-5** Given no row for the chosen day, then the page says "Nothing is held on {day}." with a button to the next day that has rows, or "See everything" if none.
- **AC-6** The list makes the same number of queries (at most about 8) at 5 rows and at 50 rows, filters on Held **before** the punch read, and on a copy with a 60-person team and a 442-person HR view its p95 is ≤ 500 ms. *Oracle: query count equal at 5 and 50; timing recorded in the test report.* (OPS-39, 52, 53)
- **AC-7** The list response for a row holds none of `latitude`, `longitude`, a photo field, `user_id`, an email, another person's punches, or a reason for absence, and no login yes/no. (PRIV-3, OPS-54)
- **AC-8** Given M's Employee is Left, or the tenant manager switch is "0", or M has no direct reports, then the list is empty and no box is offered (the existing sentence for no reports). *Oracle: three runs.*
- **AC-9** *(Needs Surbhi's yes, UX-1.)* Given a manager whose people's company has the hold on, then the Held chip shows and "No clock-out" is hidden; where the hold is off, "No clock-out" shows as today and no Held chip. *Oracle: chips drawn in both tenants.*
- **AC-10** The list call is read-only and cached nowhere: no `frappe.cache` key is created for a manager's team or held list, and the network response header for the call is written down in the test report (not assumed). (OPS-49)

### US-2 · The row

- **AC-11** A row for a direct report, **with or without a login**, shows the name, the day, a Held chip with the word, the strip, the real punches, a time box and a reason box. **Neither box has a pre-filled value.** *Oracle: both inputs empty on load.*
- **AC-12** On a one-punch row the question names the person and the inferred end ("What time did Ravi leave?" or "...arrive?"), with the help "Type the time you know it was. Nothing is filled in for you." **[UNVERIFIED: the engineer confirms the rule is `acHeldForm`'s; I did not read it.]**
- **AC-13** *(H-11, Surbhi's change.)* Given a one-punch row with a time typed, when the manager presses **Change**, then: the question switches between arrival and leaving; the time box is emptied; the dashed ring on the strip moves (shift start for arrival, shift end for leaving); focus returns to the time box; the link's spoken name is "Change to arrival" or "Change to leaving"; "Start again" resets it; nothing is stored. *Oracle: label, input value, ring position, focused element.*
- **AC-14** On a row with 3 or more punches the box is a button that opens 087's timeline; tapping a gap opens 087's add sheet with the kind worked out ("Back in after a break"); the row then shows "+14:40 · Back in after a break" and a Change that reopens the sheet. One punch per row.
- **AC-15** Ready shows only when the time (or gap) **and** a non-blank reason are both there. A time with no reason shows the line "Add a reason to include this day": no red, no error before she tries to send.
- **AC-16** Typing in a box never redraws the page (focus and cursor stay); pressing Enter in a box does not send. *Oracle: element identity and `document.activeElement` unchanged after typing.*
- **AC-17** The reason box is labelled "Your reason · Required" with the line "HR and {name} can read this. No health or family details." and has no way to copy a reason to another row. The browser box limits to 500 characters. *(Counter not drawn: [ASSUMPTION]; the server limit is AC-27.)*

### US-3 · The send call

- **AC-18** The call accepts POST only. A GET is refused. A guest is refused. A POST from a signed-in browser session **without** the CSRF header is refused, **proved over HTTP**, not by calling the function, and the refusal is shown to come from CSRF (break-and-restore: remove the header check in the test client and see the failure). (SEC-4)
- **AC-19** More than 50 rows: the whole send is refused, nothing filed, with "50 at most in one send." Exactly 50 are accepted. An empty list is refused with a sentence. The server never takes "the first 50". (SEC-3, OPS-55)
- **AC-20** Each row reads only the five keys. A row that also carries `ignore_permissions`, `alvoraa_needs_confirm: 0` or `to_date` is processed as if the extra keys were absent (the request is still filed as the server decides, still one day). (SEC-2, SEC-3)
- **AC-21** The same person and day twice in one send: the first is filed, the second refused ("Already waiting with HR"). (SEC-3)
- **AC-22** *(The seven-case scope test, SEC-1.)* Given a manager with two direct reports, one send carries: a direct report, a skip-level report, another manager's report, a person in a second company, a leaver, a made-up id, and the manager's own id. Then only the direct report is filed; each of the other six gets the **same** sentence "Not sent. This person is not one of your direct reports." with **no name**; `security.log` gets six lines (through `access.refuse`: caller, employee id, a rule code, **no reason text**). *Fails first:* remove the per-row check and watch a stranger get filed.
- **AC-23** The AC-22 send repeated as a login that holds the submit right but no HR role, and as an HR User: the same result (only direct reports filed). (SEC-1, ALV-425 for this door)
- **AC-24** A manager whose Employee is Left, and a tenant whose manager switch is "0": nothing is filed. (SEC-1)
- **AC-25** A row with no time is refused. A row for a day later than today is refused. **A row for today with a time later than the server's clock now is refused**: "It is only {hh:mm} now, so {time} has not happened yet. Enter the time the person really left." (New rule, G10; words from 01b v1 5.5.)
- **AC-26** Given a row whose `in_or_out` disagrees with what `punch_fix.derive` works out for that time against the counted punches, then the row is refused in words, nothing is filed: "{time} comes after the punch at {hh:mm}, so it is a leaving, not an arrival. Press Change if the missing punch is the leaving." (and the mirror for a time before the first punch). *Oracle: one-punch day with a 09:00 punch; row `in_or_out = IN`, time 18:30: refused; row `OUT`, 18:30: filed.* (New rule, G10; **new words, not drawn in prototype-v2: needs Surbhi's yes**, section 13.)
- **AC-27** A blank or empty reason is refused with 087's sentence "Say why, so HR can decide. A reason is needed on every request." A reason over 500 characters is refused ("Keep the reason to 500 characters."). A reason `<img src=x onerror=alert(1)>` is filed, and then **each of three screens** (the manager's confirm, HR's card, the employee's day sheet and Confirm block) is opened in a browser test: shown as text, nothing runs. (SEC-2, SEC-3, A10)
- **AC-28** Given five rows where row 3 has a blank reason and row 4 is on a day that is no longer Held: rows 1, 2 and 5 are filed; rows 3 and 4 are refused with the server's sentence and leave **no document**; the counts are 3 sent, 2 not sent and equal the entries. *Fails first:* blank the reason check in `raise_for_report` and watch row 3 get filed. (SEC-2, OPS-55)
- **AC-29** Every request filed by the send call has `alvoraa_needs_confirm = 0` (case A), whatever the client sent; a client-sent value is put back. (SEC-6)
- **AC-30** Given the day was Held when the page loaded and is not Held now (a machine punch or HR fixed it), then that row is refused: "This day is no longer held. A machine punch or HR may have fixed it. Reload the page to see where it stands." and nothing is filed for it.
- **AC-31** Sending the same list twice back to back files one request per employee-day, and the second answer says "Already waiting with HR" for each. Two sends at the same moment from two threads also file one request per day. **The test fails first** with the lock removed (the check runs after locking the day's Attendance row, `for_update`, inside the row's savepoint). (SEC-5, OPS-57, OPS-44)
- **AC-32** Given a lock wait or deadlock on row 2 of 5 (forced in the test), then the loop stops, row 2 is rolled back, rows 3 to 5 are answered "not sent", row 1 stays filed, and **one** Error Log entry is written holding ids and counts only. No retry inside the loop. (OPS-56)
- **AC-33** Given an unexpected error on a row, then that row's sentence is "Could not send this one. Nothing was filed for it. Try again.", with no traceback and no raw server text, and the Error Log entry (one) holds request count, manager employee id, sent/refused counts and the first refusal class, and **no** reason, typed time or name. (OPS-60, PRIV-2)
- **AC-34** The answer holds per row `{employee, date, ok, request or sentence}` and the counts; the counts equal the entries; it never holds the reason, the typed time, punches or slip figures. (OPS-48, PRIV-2)
- **AC-35** The 31st send by one login in an hour is refused "Too many sends. Please wait a while." (the existing per-login limiter, 30 an hour). A 429 from nginx reads to the manager as "wait a minute, then reload and look before sending again". (SEC-4, OPS-59)
- **AC-36** A filed request's `explanation` reads: the reason, a blank line, then "Raised by {manager name} ({manager employee id}), their reporting manager, on behalf of the employee." and, when the send carried more than one day, "One of {n} days sent together." *Oracle: the text. If an existing 087 test asserts the old stamp, it is updated in the same change.* (SEC-8)
- **AC-37** From the request alone, with no log, a tester answers: who filed and when (`owner`, `creation`); as whose manager and in a batch (the stamp); what was said (`alvoraa_missing_time`, `alvoraa_missing_log`, `explanation`); whether the employee agreed (`alvoraa_confirmed_by`/`_on`, or the Declined state and `alvoraa_replaces`); who decided and what they told the employee (`alvoraa_reviewed_by`, `alvoraa_reviewed_on`, `alvoraa_review_note`). Run for file, confirm, approve, and again for Not right. (SEC-8)
- **AC-38** *(The recheck.)* The recheck call is read-only, takes the employee ids and the day, returns for each whether a request by this manager now exists and its state, never files, and is tried at most three times with a pause. Given the answer is killed after the server filed 3 of 5, then the page shows 3 sent and 2 still ready. Same query-count rule as AC-6. (OPS-58, SEC-5)
- **AC-39** The send creates no email, no Notification Log row and no Inbox row of its own. *Oracle: Email Queue and Notification Log counts unchanged around a send.* (OPS-43)
- **AC-40** A 50-row send on a copy with DTC-size data is timed and written in the test report; **over 10 s is a stop-and-rethink** (OPS-55, brief kill criterion 1), not a silent pass.
- **AC-41** The existing `NoQuietBypass` test covers the new module: no `ignore_permissions`, no flag set around `raise_for_report`, no copy of a rule that lives there. (SEC-2)
- **AC-42** The change adds no Custom Field, patch, fixture or `patches.txt` line. *Oracle: diff.* (OPS-61)

### US-4 · The send bar, confirm and result

- **AC-43** The bar appears only when at least one row is Ready; it reads "{N} days ready" (counted across the page's rows, not only the visible ones) and "Each person is told on their day sheet. HR decides.", with the button **Send {N} to HR**. Never greyed.
- **AC-44** Over 50 Ready: the bar adds "50 at most in one send. The first 50 go now; {k} stay here for the next send." and the page sends exactly 50.
- **AC-45** Exactly **one** confirm opens: title "Send {N} days to HR?"; the sentence "Your name goes on each request. Each person is told on their day sheet and can say it is not right. HR decides each one. Until HR does, the day stays held."; one line per day with person, day, time and **the reason typed for that day**; no shared note box; buttons **Send {N} to HR** and "Go back". It is a dialog with a focus trap; Escape and Go back close it; focus returns to the Send button; on a phone it is a bottom sheet. *Oracle: keyboard-only test.*
- **AC-46** *(Test what it sends.)* Pressing the real Send posts **one** call carrying one list, with exactly the five keys per row, each row with **its own** reason. It never posts one call per row. (PRIV-1, OPS-41)
- **AC-47** While sending, the button is disabled and reads "Sending {N}... please keep this page open". A double tap files once (AC-31 is the guarantee; the disabled button is the comfort).
- **AC-48** Given all rows sent, then the sent rows leave the list and the banner reads "{n} of {n} sent to HR. {Names}: HR will decide each one. Each person has been told on their day sheet." in a status region that announces itself. The names come only from this send's answer.
- **AC-49** Given some rows refused, then the banner reads "Sent {a} of {b} to HR. {c} not sent. The reason is on each one below. The {a} that went are waiting for HR." with a button "Go to the first one"; each refused row stays with its time and reason and a red box "Not sent. {the server's sentence} Change the time and send again." (`role="alert"`); the box goes when she edits the time; the row is not Ready until she does. *Oracle: a + c = b, and the banner equals the answer's counts.*
- **AC-50** Given none sent: "Nothing sent. {c} not sent. The reason is on each one below." Given the browser is offline: "Nothing was sent. You are offline. The times you typed are still here. Connect, then press Send again." and the typed values stay.
- **AC-51** Given no answer arrives, then the banner reads "We did not get an answer from the office. Some days may have gone through. Checking now, please do not send again." and the page calls the recheck (AC-38) and then shows the real counts. After three tries without an answer: "We could not check. Reload the page to see which days are still listed before sending again." **(New words: 07 OPS-58 pointed at a "Waiting for HR" list that v2 no longer has. Needs Surbhi's yes, section 13.)**
- **AC-52** Nothing typed is written to `localStorage` or `sessionStorage`; after logout, Back shows no row content. *Oracle: both stores inspected after typing two rows; Back-after-logout browser test.* (PRIV-4)
- **AC-53** Reloading the page loses unsent typed values (said by the bar's first line while any exist: "N days ready" is the visible reminder). No draft is saved anywhere. [ASSUMPTION: no extra warning is drawn; none in the prototype.]

### US-5 · Case A: no Confirm, only ever an added time, the employee is told

- **AC-54** Given a held-day time add (no set-aside) filed through the send call by the employee's direct manager, then `alvoraa_needs_confirm = 0`, and HR's approval is **not** refused for want of a Confirm. The condition is one place in `punch_fix._own_the_confirm_fields`, with no setting. *Oracle: the field, and approval succeeding.*
- **AC-55** *(Counsel: a manager who could cut time or set a punch aside would need Confirm. 086 cannot.)* Every request that does **not** meet AC-54's condition is still marked for Confirm (087 AC-104): a request filed by HR, a request on a day that was not Held, a request with a punch set aside, a request filed by a manager who is not the employee's direct manager. A `set_aside` key in a send row has no effect and the request has none (the send call reads five keys only; `punch_fix.validate` already refuses a manager's set-aside, `punch_fix.py:271-312`, read). *Oracle: five requests, five values of the field.*
- **AC-56** A report with no `user_id`, or a disabled User, gets the same boxes and the same filing as everyone else. No refusal, no special row. *Oracle: the row is filed and the request exists.*

### US-6 · The filer cannot change or delete

- **AC-57** After a request is filed through the send call, the manager who filed it cannot change its employee, day, time, In/Out or `explanation`: a REST `set_value` by that manager is refused. HR in scope may still correct a typo. *Oracle: the manager's `set_value` refused; HR's allowed.* **Under case A there is no Confirm to clear, so 087's "clear the Confirm on edit" (`punch_fix._own_the_confirm_fields`, `CONFIRMED_CONTENT`, read at `ae249815`) protects nothing here. 01c SEC-7 asks for the refusal; this is a small new guard (in 087's `validate` or here; engineer says where). Section 15, F2.**
- **AC-58** The manager who filed it cannot delete the request: REST delete is refused. **[UNVERIFIED: I found no delete guard; 01c says the Employee role holds `delete`. If none exists, this AC fails until the guard is built.]**

### US-7 · What the employee and HR see

- **AC-59** Given a request filed by the send call, then the employee's day sheet shows a notice with the manager's name, the time and the manager's reason: "Your manager {name} sent {time} for you. HR will decide." with **Not right** (their reason required). *Oracle: the day-sheet text. Parity note: the notice is drawn in prototype-v2 only as the bar, confirm and banner lines; the day-sheet notice is the 087 Confirm block's sibling and needs Surbhi's yes (section 13, P-7).*
- **AC-60** HR's approval of that request works with no Confirm (AC-54). The HR card names the filer, shows the reason and the real punches, and does **not** say it is waiting for the employee.
- **AC-61** Not right on the notice declines the manager's request. Not right with a time files the employee's own request in its place in the same transaction, linked by `alvoraa_replaces` (087 AC-108..110). **[UNVERIFIED: whether `confirm()` accepts a request that is not marked for Confirm; if not, a small change in 087's `confirm`.]** *Oracle: both documents.*
- **AC-62** No endpoint, screen or report in this slice returns a count of days per manager, a ranking, a "who forgets most" view or a reminder. *Oracle: grep of the new function and screen code; the list and send answers hold no such field.* (brief section 10)

### US-8 · Nothing leaks

- **AC-63** File a row whose reason holds a marker string. Then search `logs/*.log`, `tabError Log`, `tabEmail Queue`, `tabNotification Log` and the send's answer: **no marker anywhere** except the request's own `explanation` and the screens named in AC-27. Force an error on one row: its Error Log entry has no marker. (PRIV-2, OPS-50, OPS-60)

### US-9 · Phone and accessibility

- **AC-64** At 390 px and 360 px and 200% text: nothing is wider than the screen; time and reason fields are 16 px text and at least 44 px tall; targets at least 44 px on a phone and 24 px on a laptop; explanatory text is at least 12 px; the bar is fixed above the portal's bottom bar; the confirm is a bottom sheet whose Send button stays in view. *Oracle: scripted measurement, as the designer did for the prototype.*
- **AC-65** Every field has a visible label; Held, Ready and Not sent each carry words, never colour alone; the banner is a polite status region and a refused row is an alert; the whole flow works by keyboard.
- **AC-66** Every string is translatable (`__()` on the page, `_()` on the server). The Hindi words in 01b 5.8 and the prototype are used; **Hindi ships only after a native reader** (not a build blocker).
- **AC-67** Dates and times are drawn with the site's formats (not hard-coded) and times use the 24-hour form shown in the prototype. [ASSUMPTION: the site's time format is read as for 087's screens.]

### Case B (not built; a note only)

If counsel's answer is ever reversed: the condition in AC-54 is removed (so 087 AC-104 marks the request), the no-login row of prototype-v2 is drawn, the server refuses a report with no `user_id` or a disabled User, the bar/confirm/banner lines go back to "Each person confirms in the app first", and the employee uses 087's Confirm block. One condition in one place, no setting, no second build. Not specified further.

## 10 · Edge cases that can happen here

| Case | What must happen | AC |
|---|---|---|
| **A report has no login** | same boxes, same filing; the notice reaches them through ALV-426 | AC-56 |
| **A day is released while the page is open** (a machine punch arrives, or HR fixes it) | that row refused with "no longer held"; the others still go | AC-30, 28 |
| **Partial failure** (3 of 10 refused) | sent rows leave, refused rows stay with their words; banner counts add up | AC-28, 49 |
| **More than 50 ready** | page sends 50, the rest stay; server refuses 51 | AC-19, 44 |
| **The answer is lost** (timeout, dropped network) | page asks the server what went; never re-sends | AC-38, 51 |
| **The Change link** | label flips, box emptied, server still refuses a time that disagrees | AC-13, 26 |
| **A double tap or a repeat send** | one request per employee-day | AC-31, 47 |
| **Two managers or HR file the same day at once** | the later one is refused ("Already waiting with HR"); the lock is on the day's Attendance row | AC-31 |
| **The employee files their own time meanwhile** | refused by the stock overlap check; the employee's way out is Not right with a time. *(Brief assumed otherwise; it was wrong.)* | AC-61 |
| **Manager leaves or is moved to Left mid-flow** | next send refused for the whole call; no Active record | AC-24 |
| **A report leaves or changes manager mid-flow** | that row refused ("not one of your direct reports") | AC-22 |
| **Manager with no direct reports, or no manager set on the employee** | existing "Nobody reports to you" sentence; an employee with no `reports_to` is on nobody's list (HR's own route stays) | AC-8 |
| **Circular reporting line** | not reachable: the list uses direct reports only, no walk up or down | AC-1 |
| **Skip-level person** | not listed, not filed | AC-1, 22 |
| **Declined or withdrawn request left at draft** | per the stock overlap check the day is not re-offered. **[UNVERIFIED]**, may mean a declined day can only be re-raised by the employee or HR | AC-2 (cancelled only) and F5 |
| **Night shift, a time after midnight** | `derive` uses the shift-day rule (`extra_when`, `held_day.py:301`); the page sends the time and the day, the server decides the kind | AC-26 |
| **Today's day, time later than now** | refused | AC-25 |
| **Back-dated day** | a Held day is never outside the filing window (`raise_for_report`: the window check runs `if not held`, read) | AC-28 |
| **Multi-company manager** | direct reports in any company, if the link says so; the hold switch is per company so only companies with the hold on have Held days | AC-1 |
| **Re-hired employee, duplicate employee records** | the Active record is the one used; a Left old record is refused | AC-22 |
| **Half-days, leave, holiday on a Held day** | 087's `day_state` refuses leave, slip-final (not for Held days: 085's arrear path), hand-marked, no-shift in words; the row shows the server's sentence | AC-28 |
| **Reason holds a script** | shown as text on three screens | AC-27 |
| **Shared handset** | nothing stored | AC-52 |
| **The tenant manager switch is "0"** | empty list, nothing filed | AC-8, 24 |
| **ALV-404** (a lone OUT punch on a log-type shift marks Absent) | such a day may not be Held and so is not listed; not this slice's to fix | none: **gap by design, noted** |
| **Bulk import, cancelled or amended documents** | not applicable (no import; a cancelled request frees the day) | AC-2 |

## 11 · Non-functional requirements for this slice

| Item | Number | Source | AC |
|---|---|---|---|
| List call | ≤ about 8 queries at 5 and at 50 rows; p95 ≤ 500 ms on a 60-person and a 442-person copy; Held filter before the punch read | nfr-budget, OPS-39, 53 | AC-6 |
| List payload | ≤ 50 rows a page, about 4-6 KB gzipped (estimate), next page on request | OPS-47, 54 | AC-7 |
| Send call | synchronous, ≤ 50 rows; 50-100 ms an insert (estimate) so 3-10 s; measured, stop if over 10 s; no background job unless measured over | OPS-40, 55 | AC-40 |
| Rate | 30 sends an hour per login (Surbhi's yes); nginx unchanged (`/api/` 120 a minute, burst 30, read, OPS-41) | 01c SEC-4, OPS-59 | AC-35 |
| Volume | a few hundred requests a month at DTC (355 held days in 1-16 Nov); retention follows the request | OPS §1 | none (no new store) |
| Page weight | no new file; the view is added to `portal.js` (1.3 MB, existing). Cold-load on 3G is the existing cost, not ours | OPS-46 | **gap: P3 FYI, measure once on dev before the usability test, no test** |
| Personal data | missing time, reason (sensitive free text), punches: protected as in 01c §3; nothing new stored, cached, logged | PRIV-2, OPS-49, 50 | AC-10, 63 |
| Queue | none new. 087's slip refresh runs on `short` at HR's approval; a worker on `short` is checked by `rq:workers` and `docker top` at release | OPS-62 | release check |

## 12 · Migration, notifications, localisation, audit

- **Migration / backfill: nothing.** No field, patch or fixture (AC-42). Rollback: redeploy the previous tag with migrations off; the tag must exist in the `alvoraa-app` package (OPS-62). The `portal.js` change needs `assets.json` in the sites volume moved or nobody sees it (OPS-61).
- **Notifications: none new** (AC-39). 087's Confirm block and Inbox behaviour are 087's and do not apply to these requests (case A). The notice of manager-added times on the register or payslip is **ALV-426, not built here**. Nothing in any message may carry a reason to anyone but the employee and HR (PRIV-2).
- **Messages and toasts:** every sentence in AC-3..AC-55 is the designer's (01b v1 5.5, v2) except those marked "new words" (AC-25, 26, 51 and the SEC-1 sentence), which need Surbhi's yes.
- **Localisation and accessibility:** AC-64..67. Hindi is machine-drafted; native review before it ships. Frontline phone: card layout, 44 px, bar above the bottom bar.
- **Audit:** AC-36, 37. The request is the durable record. `security.log` keeps about 2 MB (01c R5) and is not an archive. Nothing here writes a new audit row.

## 13 · Prototype parity table

Build every feature in `prototype-v2.html` as drawn (rule of 21 Oct). **Any difference needs Surbhi's yes.** Rows H-1 to H-11 are the designer's (01b v2.3, v2.7). The prototype's review bar (Case A/B switch, Load, Start again) is **not part of the product**.

| # | Prototype-v2 draws | Built as | AC | Difference? |
|---|---|---|---|---|
| H-1 | Day control (+ "All days in this period"), Held chip, "N held days need a time from you" | as drawn | AC-3, 4 | none |
| H-2 | Only held days with no request, direct reports | as drawn | AC-1, 2 | none |
| H-3 | Strip, real punches, and 087's timeline for 3+ punches | as drawn | AC-11, 14 | none |
| H-4 | Gap tap opens 087's add sheet, kind shown | as drawn | AC-14 | none |
| H-5 | Required reason per row, listed in the confirm; no shared note | as drawn | AC-15, 17, 45 | none |
| H-6 | Sent rows leave; banner names who | as drawn | AC-48 | none |
| H-7 | No "Everyone below me" | as drawn | AC-1 | none |
| H-8 | No-login line (B); Case A shows boxes | **Case A as drawn** (boxes for everyone); the no-login line is **not built** (case B note only) | AC-56 | none (counsel chose the drawn Case A variant) |
| H-9 | Bar line "Each person confirms in the app first. Then HR decides." (B); "Each person is told on their day sheet. HR decides." (Case A) | **Case A line**; confirm sentence and banner line also the Case A ones drawn | AC-43, 45, 48 | none |
| H-10 | Kept: Held chip, real punches, no pre-fill, Ready, bar, cap of 50, confirm, banner and refusal words, answer-lost, phone, Hindi, no storage | as drawn | AC-11, 43..52, 64..66 | none |
| H-11 | Change link beside the question; box emptied; ring moves; focus returns | as drawn | AC-13 | none |
| P-1 | Chip: Everything and Held (no "No clock-out") | hide "No clock-out" where the hold is on, **UX-1, not decided in writing** | AC-9 | **needs her yes** |
| P-2 | Scope refusal for a stranger: the server's own sentence naming the person (01b v1) | one fixed sentence, no name (01c SEC-1) | AC-22 | **differs, needs her yes** (unreachable from the page) |
| P-3 | Refusal when In/Out and time disagree: "the server still checks ... refused in words" (v2.7), **no words drawn** | AC-26 words | AC-26 | **new words, needs her yes** |
| P-4 | Future-time refusal in v1 5.5 words | AC-25, same words as v1 | AC-25 | none (v1's words), but a **server rule that did not exist** |
| P-5 | "We could not check..." (OPS-58 words refer to a list v2 lacks) | AC-51 words | AC-51 | **new words, needs her yes** |
| P-6 | 500-char reason and a 30-sends-an-hour limit: **not drawn** (no counter, no rate-limit sentence) | sentences in AC-27, AC-35 | AC-27, 35 | **new words, needs her yes** (Surbhi chose the numbers) |
| P-7 | Case A day-sheet notice "Your manager sent 18:30 for you. HR will decide." with Not right | prototype-v2 draws only the Case A bar, confirm and banner lines; **the day-sheet notice itself is not drawn** (087 v4 draws the Confirm block, not this). Built from 087's styles | AC-59, 61 | **new screen, needs her yes**; and whether Not right is still wanted after counsel's answer (F12) |

## 14 · Traceability

**What "status" means here.** Spec stage: every ACs below is *written*. **No test exists yet**, so none of these rows claims one. The test engineer names each test at stage 04. A gap means no AC at all.

### 14.1 Brief (`01-product-brief.md`)

| Brief line | Story | AC | Status |
|---|---|---|---|
| Bottom line 1: a real Held filter, a time box on each row, one Send bar, no new page or DocType | US-1..4 | AC-1, 11, 43, 42 | covered |
| Bottom line 2: the Whole team page cannot fix a held day today | US-2, 3 | AC-11, 28 | covered |
| Bottom line 3: reuse `raise_for_report`; the new code is a wrapper | US-3 | AC-28, 41 | covered |
| Decision 1 (20 Nov): manager files only for direct reports | US-1, 3, 8 | AC-1, 22, 23 | covered (the whole-line display half is dropped by the 21 Nov gate) |
| Decision 2: one time per person per day, no blanket time | US-2, 3 | AC-11, 21, 46 | covered |
| Decision 3: cap 50 per send | US-3, 4 | AC-19, 44 | covered |
| Decision 4: manager only files the request; HR decides; reason box (now required, per row) | US-3, 7 | AC-27, 60 | covered |
| 21 Nov: only held days with no request | US-1 | AC-2 | covered |
| 21 Nov: direct reports only, shown and filed | US-1 | AC-1 | covered |
| 21 Nov: one day at a time, latest day, period filter to catch up | US-1 | AC-4 | covered |
| 21 Nov: required reason on each row, never shared | US-2, 3 | AC-15, 17, 27, 46 | covered |
| 21 Nov: after sending the row leaves; banner "N of M sent" | US-4 | AC-48, 49 | covered |
| 21 Nov: Case B default, no-login row | US-5 | AC-56 | **superseded by counsel's answer (case A); no-login row not built; case B kept as a note** |
| 21 Nov: Case A is one condition; counsel answered A (21 Nov) | US-5 | AC-54, 55 | covered |
| Gate 1: ask counsel, build for B meanwhile | US-5 | AC-54 | covered: counsel answered A |
| Gate 5: if B and under half have a login, drop the send bar | US-4 | none | **moot under case A (counsel, 21 Nov); no criterion needed** |
| Thin slice: confirm once in words; lost-answer guard; refuse a future time; duplicate refused | US-3, 4 | AC-45, 38, 51, 25, 31 | covered |
| Counsel 21 Nov: register or payslip notice of manager-added times (ALV-426) | | none | **gap, deliberate: not 086's build; blocks release (F10)** |
| Out of scope: bulk approval, shared time, auto-approval, reminders, new page/setting, CXO figure, per-manager count | | AC-62 | covered (negative) |
| Section 9 / 21 Nov success measures | | none | **gap, deliberate: measured from existing rows; no new code, no per-manager display** |
| Kill criteria 1 (500 ms; 10 s) | US-1, 3 | AC-6, 40 | covered |
| Kill criteria 2 (a manager files for a non-report) | US-3 | AC-22, 23 | covered |
| Kill criteria 7 (approved with no reason, or for a non-report) | US-3, 7 | AC-27, 60, 22 | covered |
| Kill criteria 3, 4, 5, 6 (HR declines most; few managers use it; few have a login) | | none | **gap, deliberate: post-release measures, not acceptance tests** |
| Risk: chip vs status disagree (UX-1) | US-1 | AC-9 | covered, needs her yes |

### 14.2 Prototype and 01b

| Item | Story | AC | Status |
|---|---|---|---|
| H-1 .. H-11 | | see section 13 | covered (each row in 13 names its AC) |
| Empty state "Nothing is held on {day}." | US-1 | AC-5 | covered |
| Loading and failed-load states (existing) | US-1 | none | **gap: the page's existing loading and error lines are reused unchanged; no new criterion. The designer wanted "Try again" after a timeout: not tested** |
| Phone 390/360, 200% text | US-9 | AC-64 | covered |
| Hindi words | US-9 | AC-66 | covered (native review outside) |
| Accessibility list (01b section 6) | US-9 | AC-16, 45, 65 | covered |
| Dark theme (drawn) | | none | **gap: reuse of the portal's theme tokens; no criterion** |
| Usability test (01b section 10) | | none | **gap: planned, run before release, not an AC** |
| 01b items 13 (hide "Ask HR to fix"), 14 (day-sheet line) | | none | **13: dropped (F4). 14: case A notice in AC-59** |
| UX-1 / UX-2 / UX-4 / UX-5 | | AC-9 / n/a (no skip-level rows) / chip count inside chip, AC-3 / dropped | UX-4 follows the page's own pattern, AC-3 |

### 14.3 Security (`01c`)

| Item | AC | Status |
|---|---|---|
| SEC-1 scope for every row and caller | AC-22, 23, 24 | covered |
| SEC-2 every row through `raise_for_report`, savepoints | AC-20, 28, 41 | covered |
| SEC-3 fixed payload, cap 50, 500 chars, escaped | AC-19, 20, 21, 27 | covered |
| SEC-4 POST, CSRF, 30 an hour | AC-18, 35 | covered |
| SEC-5 replay and double send, lock, recheck | AC-31, 38 | covered |
| SEC-6 case B default; case A one condition | AC-29, 54, 55, 56 | covered, **for case A** (counsel, 21 Nov) |
| SEC-7 filer cannot change or delete | AC-57, 58 | covered as a refusal (01c's form). **Under case A 087's "clear the Confirm" protects nothing, so the guard is needed: F2** |
| SEC-8 rebuild a year later; stamp with id and batch | AC-36, 37 | covered |
| A1 (false later time) | | **accepted residual R1 (Surbhi to put her name and date), not preventable; AC-11, 59 are the mitigations (punches beside the box, HR card)** |
| A2 (false earlier time) | AC-59, 61 | covered (employee can say Not right) |
| A3..A13 | AC-22, 23, 19, 31, 57, 58, 55, 27, 18, 24, 52 | covered |
| ⚠ C1, ⚠ C2 | AC-54..56 | **C1 answered (case A). C2 answered by the notice on the register or payslip, which is ALV-426: blocks release** |
| R1..R6 | | residual, owners named in 01c §10. R3 is closed by 087's ae249815 only in the "clear" form (F2) |

### 14.4 Privacy (`01c`)

| Item | AC | Status |
|---|---|---|
| PRIV-1 time, In/Out, one reason per row, nothing else | AC-20, 46 | covered |
| PRIV-2 reason goes nowhere new | AC-17, 34, 63 | covered |
| PRIV-3 what the employee, HR and the list see | AC-7, 56, 59, 60, 62 | covered |
| PRIV-4 nothing on a shared phone | AC-52 | covered |

### 14.5 DevOps (`07` §1-§3)

| Item | AC | Status |
|---|---|---|
| OPS-39 Held filter before the punch read | AC-6 | covered |
| OPS-40 one call, cap, savepoint, result | AC-19, 28, 40 | covered |
| OPS-41 no browser loop | AC-46 | covered |
| OPS-42 slip cost at approval (no bulk approve) | AC-62 | covered by "not built"; no test of slip time (087's) |
| OPS-43 no notification per request | AC-39 | covered |
| OPS-44 double click files once | AC-31, 47 | covered |
| OPS-45 and OPS-R-1 no daily cap (Surbhi: none) | | **not adopted as a feature; Surbhi's decision (21 Nov): no daily cap. No AC** |
| OPS-46 page weight | | **gap: measure once, P3 FYI, no test** |
| OPS-47, 54 payload and page of 50 | AC-6, 7 | covered |
| OPS-48 send call shape | AC-34 | covered |
| OPS-49 no caching of per-person answers | AC-10 | covered |
| OPS-50 nothing personal in logs or job args | AC-33, 63 | covered |
| OPS-51 the shared note | | **superseded (per-row reason); no AC** |
| OPS-52 timing on a copy | AC-6, 40 | covered |
| OPS-53 constant query count | AC-6 | covered |
| OPS-55 synchronous, per-row savepoint, server cap | AC-19, 28, 40 | covered |
| OPS-56 partial failure; lock wait stops the loop | AC-28, 32, 33 | covered |
| OPS-57 idempotent per employee and day | AC-31 | covered |
| OPS-58 answer-lost recheck | AC-38, 51 | covered |
| OPS-59 no nginx change; 429 wording | AC-35 | covered |
| OPS-60 logs: ids and counts only | AC-33, 63 | covered |
| OPS-61 no migration; assets.json | AC-42 | covered (assets.json is a release step) |
| OPS-R-2 release order; list may ship without the bar | | **release gate, not an AC.** Surbhi decided 21 Nov: 087 proved on main first, then 086; list alone if counsel is late |
| OPS-62 what to prove on dev | AC-6, 28, 31, 38, 19, 22, 40 | covered (the worker check and rollback timing are release checks) |

### 14.6 087 conditions this slice leans on

| Item | AC | Status |
|---|---|---|
| ALV-418 reason on every request | AC-27, 28 | covered (the check lives in 087; tested here) |
| ALV-419 Confirm by the employee | AC-29, 54, 55 | covered: **ALV-419 does not apply to a manager's added time** (counsel, 21 Nov); it still applies to everything else (AC-55) |
| ALV-425 approve-right skips direct-report check | AC-23 | **closed for the new door only; F1** |

## 15 · Open questions, risks and decisions (owner, and what each blocks)

| # | Item | Owner | Blocks |
|---|---|---|---|
| ✔ C1 | **Answered 21 Nov (counsel, relayed by Surbhi): case A.** A manager adding a time in the employee's favour needs no Confirm; HR's approval, a mandatory reason and a register or payslip notice are enough. **A manager who could cut time or set a punch aside would need Confirm; 086 cannot (AC-55).** I am not a lawyer; I have not seen counsel's own text | Surbhi | closed |
| ✔ C2 | Staff with no login: answered by the notice on the monthly register or payslip (**ALV-426**), not by the day sheet | Surbhi | **Release, until ALV-426 ships** |
| F1 | Shut the `_may_review()` hole inside `raise_for_report` itself too (one line) or only in the new call (ALV-425)? **Recommendation: both**, because HR's own `can_raise` already says acting stops at direct reports "for everybody, HR included" (`team_days` comment) and the endpoint does not enforce it | Surbhi, then the engineer on 087 | Whether ALV-425 closes fully |
| F2 | 01c SEC-7 asks for refusing the filer's edit and delete. 087 (`ae249815`) only clears the Confirm on an edit. **Under case A there is no Confirm, so that guard does nothing for these requests.** AC-57 and 58 need a new small guard. Build it in 087 or in 086? | Engineer, security engineer, Surbhi | Release of 086 |
| F3 | The brief's assumption "a manager's pending request does not stop the employee filing" is false (stock overlap check). Confirm the employee's route (Not right with a time) is acceptable | Surbhi | none; told for the record |
| F4 | What does the old "Ask HR to fix" request (no time) do to a Held day (brief Q5)? Not changed here | Engineer to report | nothing in 086 |
| F5 | A declined or withdrawn request that stays at `docstatus 0` blocks a new request via the stock overlap check; so the day is not re-offered. Is that what we want, or should the list offer it again and the send replace? | Surbhi, engineer to confirm what really happens | the edge case row only |
| F6 | UX-1: hide "No clock-out" where the hold is on? | Surbhi | AC-9 |
| F7 | New words (SEC-1 sentence, AC-25, 26, 51, 35, 27) | Surbhi | those sentences |
| F8 | How the one-punch inference works (`acHeldForm`) and whether the page can tell the hold is on for the tenant (brief Q6, 01b Q8) | Engineer | AC-9, AC-12 |
| F9 | R1 (manager and employee agree a false later time) needs her name and date | Surbhi | none |
| F10 | **ALV-426 (new): show manager-added times on the monthly register or payslip.** Counsel's third condition; it is also how staff with no login are told. **My judgement: out of 086's build, and it blocks 086's release.** Why: it is a different surface (the register or payslip print) that I have **not read**; it must cover every manager-added time, including ones filed outside 086; and 086's own code is unchanged by it (the data it needs, `owner` and the stamp in `explanation`, AC-36, already exists). **If the engineer finds it is one line in an existing print format, folding it in becomes the smaller path: Surbhi to decide after the engineer reads the code.** | Surbhi; engineer to size | Release of 086 |
| F11 | Case B is a note only (section 9, "Case B"). If counsel reverses, it is one condition removed and the no-login row drawn | Surbhi | nothing |
| F12 | Counsel's answer asks for HR's approval, a reason, and the register notice. It does not mention the employee's Not right on a day sheet, which prototype-v2's Case A bar and confirm lines promise ("can say it is not right"). Keep the notice with Not right (AC-59, 61), or drop it to the smallest thing (register notice only)? **Recommendation: keep it: it is what Surbhi approved at the design gate, and it is the only way an employee with a login can correct a wrong time before pay.** It adds a small screen and possibly a change to 087's `confirm` | Surbhi | AC-59, 61, G13 |
| N5 | How many DTC held-day staff have a login | Surbhi | **Moot under case A** (it only decided whether to drop the send bar under case B) |

**Risks.** (1) A manager invents times: reduced by design, not removed (R1). (2) The one new rule (AC-26) is a comparison against `derive`: if `derive` changes in 087, this check follows it because it *calls* it. (3) 086 depends on 087 landing first; a 086 without 087 files requests with no reason (OPS-R-2). (4) 20 rows means 20 typed reasons: counsel's condition, not our choice. (5) **A manager's false earlier time could pay a person less than they worked** (01c A2): counsel's "in the employee's favour" holds because a Held day is unpaid until fixed, but a time that yields a short day is not a favour. The protections are HR's look at the real punches, the employee's Not right, and the register notice (ALV-426). Not a legal ruling; Surbhi to confirm with counsel if wanted.

**Assumptions.** `[ASSUMPTION]` the page's "Held" view ships inside the existing Whole team page's file; `[ASSUMPTION]` AC-17 and AC-53 draw no counter and no extra warning; `[ASSUMPTION]` the site time format (AC-67); `[ASSUMPTION]` 50-100 ms per insert (estimate carried from OPS-40, unmeasured).

## 16 · Compliance-impact sub-analysis (I am not a lawyer. Nothing here is a legal ruling.)

**1 · Data touched**

| Field / object | Class | Purpose | Lawful basis (as recorded) | New collection? |
|---|---|---|---|---|
| Missing time and In/Out | sensitive (decides pay) | release the held day | employer's wage-record duty; as 085/087 | No (existing fields) |
| Manager's reason (free text, may hold health or family detail) | sensitive | counsel's ALV-418; context for HR | as 087 | **No new field, new per row** (one reason on each request) |
| Who filed and the stamp | internal | audit, grievance | as above | No (stamp text extended) |
| Confirm state | internal | ALV-419 (not applicable to a manager's added time, case A) | as 087 | No |
| (login yes/no) | internal | not collected or shown: case A needs no login test | | Nothing |
| The day's punches beside the box | sensitive | evidence next to the typed time | | No (manager already sees them) |

Nothing new is collected that is not already in 085/087's requests. The outcome is impossible without a time and a reason.

**2 · Obligations engaged** (sources: `security-compliance-baseline.md`; `compliance-feature-map.md` checked)

| Obligation | What this slice does | Feature |
|---|---|---|
| Counsel's ALV-418 (reason on every request) and ALV-419 (Confirm by the employee), relayed by Surbhi, 21 Nov | reason per row; no Confirm on a manager's added time (counsel's case A), Confirm kept on every other request | 087's, tested here (AC-27, 29, 54, 55) |
| **ALV-426 (new):** manager-added times shown on the monthly register or payslip (counsel's third condition, relayed 21 Nov) | the employee, including one with no login, can see which times a manager added | **not 086's build; blocks 086's release (F10)** |
| DPDP accuracy and correction; reasonable safeguards | employee sees and contests what is said in their name; scope checked per row; nothing in logs | AC-22, 59, 61, 63 |
| Wage records (the attendance register), secondary sources only | the record shows who vouched for each time, and for whom | AC-36, 37 |

The baseline's DPDP entry goes stale on 22 Nov 2026 (01c R6). Not re-verified by me.

**3 · Visibility delta.** Managers see no punch they could not already see. The employee sees **more** (the manager's name, time and reason, as a notice on their day sheet). HR sees the filer's name, reason and punches (087). **Negative cases:** a skip-level manager, another manager, a colleague, a guest see nothing new; no list of managers or counts exists. A reason never reaches a log, an email, a notification or the send's answer.

**4 · Decision automation.** None. The manager vouches; the employee is told and may say Not right (case A, no Confirm); **HR decides each request**; no ranking, no automatic approval. Accountable human: HR. The employee is told on their day sheet and contests with Not right.

**5 · Retention and deletion.** Nothing changes: a request keeps what a request keeps today. 086 adds no deletion path and no new clock. The wage-record retention question is open from 087 (01c §3).

**6 · ⚠ Open compliance questions**

| Question | Who decides | Blocks |
|---|---|---|
| C1 and C2 | answered 21 Nov (case A) | closed; ALV-426 (F10) blocks release |
| Does 087's "clear the Confirm" meet SEC-7 (F2)? | Security engineer, Surbhi | Release of both slices |
| Wage-record retention period | Surbhi to counsel (087 01c §3) | nothing new |

**7 · AI features.** None. Nothing prohibited is required: no AI-set rating, no inference, no monitoring, no individual surveillance, no manager league table.

## 17 · Subtract pass and Definition of Ready

**Subtract pass.** I removed, from the documents I was given: the far-from-shift refusal; hiding the old "Ask HR to fix" button; "Take back"; a counter on the reason box; a draft warning on reload; the "Waiting for HR" list the OPS-58 wording pointed to. I did **not** add a setting, field, DocType, queue, job or cache. **What I added:** two small refusals in the send call (a future time, and an In/Out that disagrees with the time) because without them the approved Change link does nothing, and a lock on the day's row because the stock duplicate check is not safe against two calls at once. Everything else is reuse.

**Definition of Ready** (`definition-of-ready-done.md`):

- [x] Brief approved ("build it, every recommendation taken", 21 Nov) and design agreed (prototype-v2 with the Change link, 21 Nov).
- [x] A clickable prototype exists and was reviewed (`prototype-v2.html`).
- [ ] **Design feedback logged in `ux-learnings.md`: not checked by me.** The orchestrator confirms.
- [x] Every state designed (empty, loading by reuse, error, no permission, first-time, answer-lost, offline). Loading and failed-load are the page's existing ones (a gap noted in 14.2).
- [x] 01c (8 SEC, 4 PRIV) and 07 §1-§3 (OPS-39..62, R-1, R-2) written, with Surbhi's decisions.
- [x] Gap analysis done, each row against code I read (section 3).
- [x] Epic and 9 stories plus 1 conditional, sized, INVEST noted, must-not stories included (US-6, US-8).
- [x] Every story has Given/When/Then criteria with an observable oracle: 67 criteria (case A).
- [x] Traceability: every brief line, H-1..H-11, SEC, PRIV, OPS and R item maps to an AC or is listed as a gap or a decision (section 14). **Gaps: 4 (Gate 5, success measures, kill criteria 3-6, usability test), 3 smaller (loading/error states, dark theme, page weight).**
- [x] Permission matrix with negatives (section 8). Edge cases (10), NFRs (11), migration (nothing, 12), compliance sub-analysis (16).
- [x] Every ⚠ COMPLIANCE question names an owner and what it blocks.
- [x] Nothing prohibited is required.
- [ ] **Usability test (5 people, 360 px) not run.** Needed before release, not before build.

**Verdict: Ready to build, with conditions.** (1) 087 must be built first; 086 builds on its `ae249815`. (2) Surbhi's yes on the "needs her yes" rows in section 13 (P-1 to P-3, P-5 to P-7) before the screens are finished. (3) The engineer answers F8 and F5 at the start. (4) **Release is blocked by ALV-426 (F10) and F2.** Counsel's answer (C1, C2) is in; Surbhi's count of DTC staff with a login (N5) is now moot. None of these blocks the first day of work.

## Surbhi's decisions on the spec, 21 Nov 2026

All as recommended:
1. Accept the parity items P-1 to P-6, including hiding "No clock-out" on the manager page.
2. P-7: the employee sees a notice on their day sheet when their manager filed for them, with "Not right" (their own time and a required reason). This follows 087's Confirm redesign: the employee can modify, and approval never waits.
3. ALV-426 (the monthly register or payslip notice) is its own small piece of work. It must land before 086 is released.
4. A manager's pending request blocks the employee from filing the same day; this is stock Frappe HR. The employee sees "Your manager already sent this day to HR" and can use "Not right" on it.
