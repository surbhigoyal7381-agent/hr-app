---
slice: 063-dtc-leave-credit-and-lwp
artifact: implementation notes (change process steps 4 and 6)
author: hrms-fullstack-engineer
date: 2026-10-21
branch: slice/063-dtc-leave in .claude/worktrees/063-dtc-leave (from origin/dev 76f15e1d). LOCAL ONLY - nothing pushed, nothing on any server.
approval: the strategy (04-impact-and-strategy.md) was approved by Surbhi, relayed by the coordinator on 21 Oct 2026, with every open question on its recommended default except where she answered (OD-7 yes, HR approves LWP yes).
---

# 063 · Implementation notes

## 1 · Bad news first

1. **Rehearsed on synthetic data only, as Surbhi chose (07a section 3).** 30 of 30 named checks
   pass. What synthetic data cannot prove is in section 9a. The DTC rule set must still not be
   switched on until she says so.
2. **The live portal has no Inbox page.** Approvals happen on the Team page ("Pending Leave
   Approvals") and the Home card. HR's Leave Without Pay rows are added there. The Inbox
   endpoint (`inbox_api`) carries them too, but only the discarded "next" frame draws it.
   The Team page row has no "1 other person in this team is away" line - that line belongs to
   the Inbox part and the live page never showed it. **Differs from the prototype (R-54).**
3. **OD-1 remedy (iv) needed two things the strategy only half-saw.** The shift trap was real
   and worse than "fails at approval": with no shift on the request, Frappe **silently made a
   second attendance row for the same day** (proved on the bench). The hook now copies the
   row's shift. And the Attendance page's form has no half-day tick, so the hook also makes
   the request a half-day one on such a day. Both are pinned by tests.
4. **"Who was told" can be smaller than the chain.** Frappe never notifies the person who did
   the action, so when the store manager approves, he is not sent his own notice and the line
   says "(1 person)" where the prototype's example says 2. The line counts the real rows.

## 2 · What was built, file by file

| File | What | Rung | Why |
|---|---|---|---|
| `payroll_rules.py` | `DayVerdict.half_leave`; `evaluate_day(half_day_leave, other_half_regularised)`; `_judge_other_half` (half shift, cap 2 quarters before doubling, no late/early/window, no greens, absent half doubled, regularised half worked) | 4 | 01d, OD-1 iv - config cannot express it |
| `payroll_rules_apply.py` | `judge` sets the two flags (Half Day + leave link; approved request link); `LEAVE_FIELDS`, `PAID_LEAVES` constants; `evaluate_attendance` reads the fields | 4 | the engine reads the attendance, never the Leave Application |
| `payroll_month.py` | halves; `days_for_gate` = worked + approved Paid Leaves (E6) | 4 | E6 |
| `payroll_slip.py` | reads the leave fields; counts approved Paid Leaves days (half 0.5) and passes them (E6 + U1) | 4 | one call for slip, report and card |
| `payroll_reprocess.py`, salary report | field list; Worked/On leave/Absent/Held columns are Float | 4 | halves |
| **`leave_rules.py` (new)** | every DTC rule: validate (month, limit 5), chain notice, N-5/N-6, lock, half-day correction hook, card, Apply list, preview facts, list facts | 4 | hooks need a home; `hr_api.py` is at its ceiling; 0 bypasses |
| `hooks.py` | Leave Application `validate`, `on_submit`; Leave Type `validate`, `before_rename`, `on_trash` (+lock); Attendance Request `before_insert` - all appended | 4 | every door |
| `hr_api.py` | `_can_action_leave` LWP branch; `action_leave` (withdrawn message, LWP message, decision facts); `apply_leave` + `preview_leave_request` via `_leave_subject` (SEC-7, branch); Paid Leaves approver set; `get_leave_summary` (card, types, list facts); new `cancel_leave` (+1 bypass, 70); `get_all_active_employees` branch scope + `no_login`; HR LWP rows on Team/Home; DTC facts on approver rows | 4 | existing endpoints, one new |
| `inbox_api.py` | HR's LWP OR-branch, DTC row facts | 4 | for the Inbox part (next frame) and reused by the Team page |
| `portal.js`, `panels.css`, three page parts | the lp- block: card, list, cancel dialogs, Apply mode, Team row lines, decision sentence; LWP in the Apply list for every tenant | 4 | prototype v3 |
| `scripts/rehearsal_063.py`, `07-rehearsal-runbook.md` | release steps, local copy first | - | US-22..24 |

No new DocType, field, setting, job, cache or app. No patch.

## 3 · Tests (what was run, and what it said)

| Run | Result |
|---|---|
| `test_leave_063_engine` (new, pure) | 23 OK |
| `test_leave_063_rules` (new, site) | 38 OK |
| `test_leave_063_card_cancel` (new, site) | 17 OK |
| `portal_leave_063_test.js` (new, jsdom, every prototype sentence) | 100 passed, 0 failed |
| all 11 DOM tests (`scripts/run_dom_tests.js`) | 11 run, 0 failed |
| neighbours: test_leave, test_leave_permissions, test_portal_security_010, test_inbox_parts_042, test_inbox_counts_034, test_salary_report, test_payroll_reprocess, test_payroll_month, test_payroll_rules, test_leave_ledger_035, test_numbers_match_035, test_leave_privacy_045, test_leave_endpoint_access_173, test_leave_year, test_no_repeat_queries_044, test_home_holidays_035, test_frame_endpoint_registry_034, test_review_fixround_010d | all OK after the fixes below |
| **full alvoraa_portal suite, once** | see section 9 |
| `scripts/check_app_integrity.py` | OK, 792 checks |
| `scripts/check_design_system.py` | OK (one emoji found and replaced with the existing icon) |
| `check_undefined_js.js`, `check_portal_handlers.js`, `check_tag_balance.py` | OK |

**Guards broken on purpose** (each test must go red): the limit of 5, the month rule, the HR
scope in `_can_action_leave`, the own-record check in `cancel_leave`, the shift copy in the
correction hook, the two-quarter cap, the lock's Administrator-only rule, the SEC-2 refusal,
the Paid Leaves count passed to the month. **All went red.** The HR-scope guard first stayed
green - Frappe's own Branch permission on the Leave Application already refused - so a test
was added where Frappe would let the HR user through (a Branch permission limited to
Employee records) and only our scope refuses; with the guard removed it goes red.

**Existing tests changed, and why:**
- `test_leave_permissions`: two tests pinned the old silent fallback for a non-HR
  `on_behalf_of`. SEC-7 (every tenant, her decision) refuses it; they now pin the refusal.
- `test_payroll_month`: the class A fixture moved to DTC's flat values (15/4/4, counting to
  15). Two expected figures changed: 24 worked + 6 leave now gives 4 credits, 2 unpaid;
  the complete month gives 4 credits, 3 encashed, 26.5 paid days (01e section 3 listed both).
- `test_portal_security_010`: `hr_api.py` 69 -> 70 (named `cancel_leave`), `leave_rules.py` 0.
- `test_frame_endpoint_registry_034`: three configuration reads declared in `inbox_api.py`.
- `scripts/run_dom_tests.js`: the new DOM test registered; expected count 10 -> 11.

## 4 · Acceptance criteria

All 118 are built except where the table says otherwise. The rows that differ or wait:

| AC | Status |
|---|---|
| AC-7, AC-104, AC-108 | **Wait for the rehearsal / go-live** (need DTC data) |
| AC-15 | skeleton built; 3G timing not measured (needs a device profile) |
| AC-18 | the card is built from named keys only and never carries money; the "31000" scan was dropped because the fixture has no salary, so it would prove nothing (honest gap) |
| AC-23 | equal query count at 5 more employees, pinned; **24 queries** for the card with no attendance, 52 ms on the local site. A full month adds about 3 per attendance day (month_summary) - measure on the copy |
| AC-47, AC-53, AC-54, AC-55 | built on the Team page and Home card (no Inbox page) - see section 6 |
| AC-62 | built in code, no Notification record |
| AC-74, AC-75 | built |
| AC-82 | wording built; RC-11 (no non-HR role reads DTC reasons on the desk) is a release check |
| AC-103..AC-108 | runbook and script written; not run on DTC data |

## 5 · The seven dimensions, against the code written

| Dimension | Before -> after | Verdict |
|---|---|---|
| Performance | Leave page at DTC: + one `month_summary` for one person (24 queries measured empty; ~3 per attendance day), same at any headcount; Team page for HR: 62 queries measured with no rows; DTC rows on the Team page cost a chain walk and a month's LWP each (bounded by the list, not by headcount) | degrades slightly, inside budget |
| Security | new refusals on every door; scope in the database; one named bypass (70); self-approval refused everywhere | improves |
| Reliability | chain notice and card can never block an approval or the page; every refusal says what to do | improves |
| Scalability | nothing per head; no job, no cache | neutral |
| Maintainability | DTC rules in one module with 0 bypasses; `hr_api.py` +243 lines, `portal.js` +580 (own lp- block) | neutral to slightly degrades |
| Data integrity | one source per number; OD-1 hook writes one true fact before validation, rolled back with the request | improves |
| Compliance / privacy | card days only, named keys; notice four facts; no reason in any log or notice (pinned) | improves |

## 6 · Prototype parity, row by row (spec 6.4)

**Built** = as drawn, pinned by `portal_leave_063_test.js` or a server test.
**Differs** = built, but not exactly as drawn - raised here, not resolved.

| Rows | Status |
|---|---|
| R-1 .. R-12 | Built (R-9 with the "(up to {date})" bracket, X-3 agreed) |
| R-13 | **Differs (small):** the skeleton shows from the second load on; the very first visit shows the page's existing "Loading..." until the server says this is a DTC company |
| R-14 .. R-21 | Built |
| R-22 | Built; **differs in the example only:** the count is the real rows, and the approver is not sent his own notice (bad news 4) |
| R-23 .. R-27 | Built (R-27: X-1 resolved by OD-1 iv; the button opens the Attendance page at that day) |
| R-28 | Built; **differs (small):** the Half day box sits below the preview, where the existing form has it, not above it |
| R-29 | **Differs:** a search box, as today, not a select - DTC has 445 people. It says "Who is this leave for?", "Myself ({name})", marks "· no login", and shows the help sentence |
| R-30 .. R-48 | Built (R-30/R-36 on behalf: no Paid Leaves figure, X-2 kept) |
| R-49, R-50, R-52, R-53 | Built (R-50 says "has been told" only when the notice went to someone) |
| R-51 | **Differs:** "tell **them** yourself", not "tell him yourself" - the manager may be a woman |
| R-54 | **Differs:** on the Team page and the Home card, not an Inbox; no "other person away" line; the row's buttons keep today's "Approve" / "Reject" |
| R-55 .. R-57 | Built (Team page rows) |
| R-58, R-59 | Built (X-4 interim, now permanent: "{first} has no email on record, so please tell them"); **differs:** the badge after deciding keeps today's "Approved" / "Rejected" and a toast appears too |
| R-60 | **Differs:** "{first} cancelled this request." arrives as the refusal message (a toast), and nothing is written |
| R-61 | Built (Team page) |
| R-62 | Built (column removed for every tenant - it was always empty) |
| R-63 | Existing |
| R-64, R-65 | Built (email depends on each manager's notification settings; production email is muted until go-live) |
| R-66 .. R-73 | Built (server rules) |
| R-74 | **Blocked as agreed (X-5):** every string goes through `drT` / `_()`; no Hindi file is installed, because installing one switches Hindi on for Hindi users. The draft is in the spec, section 16 |
| R-75 | Built (roles, labels, Escape, 44px, 16px fields in the DTC form) |

## 7 · What else moved while I worked

`origin/dev` did not move between 76f15e1d and the last fetch before each commit. No conflicts.
Another engineer works on slice 064 (Positions) in another worktree; I touched only the leave
block of `portal.js`, an appended block of `panels.css`, and the team month table/rows.

## 8 · Decisions I made that Surbhi should know

1. OD-1 (iv) as built: raising a correction on a past half-day leave day with a punch missing
   marks the other half **Absent** on the attendance record, copies the row's shift onto the
   request, and makes it a half-day request. HR's approval then counts the half as worked.
   Any approved correction counts (OD-1a). If HR **cancels** an approved one later, Frappe
   cancels the whole attendance row - the runbook asks the rehearsal to record what happens.
2. The card always carries the 15-day number (for the rule box, AC-3) and, under 15, the
   "up to" date (X-3). Both are additions to SEC-1's key list; security should confirm.
3. SEC-7 applies to every tenant, and so does the branch scope on HR filing for someone and
   on the picker.
4. The employee cancel endpoint works only where the pay rule set is on.
5. LWP rows for HR appear on the Team page and the Home card, because that is where the live
   portal approves leave.
6. The Team page's month table lost its (always empty) Leave Type column for every tenant.

## 9 · Full suite (run once, own container hrlocal-063, own site test063)

3,052 tests in two batches (952 + 2,084, plus 16). **On the first pass 51 did not pass; none is
caused by this slice:**

| What | Cause | Proof |
|---|---|---|
| 46 errors in test_module_access, test_tenant_setup, test_subscription_access, test_org_attendance_switches | my new site had no `locks` folder | folder made; all four modules rerun: 52, 10, 56, 33 + 14 OK |
| 1 fail test_email_logo_175, 2 errors test_attendance_correction (manager filing window), 2 errors test_scale_flatness_044 (get_pay) | already failing on this site | the same three modules run on **unchanged origin/dev code** against the same site: the same 5 fail |

So: every test this slice could reach passes; 5 tests fail the same with and without it (they look
date- and site-dependent: the run crossed midnight into 22 Oct, and the test site's brand and
payslip data). Worth a ticket each, outside this slice.

## 9a · The synthetic rehearsal (07a section 3, Surbhi's choice)

`scripts/seed_rehearsal_063.py` on the local test site, August 2026 (31 days):
**30 of 30 checks pass** - Test-901 (14 days, gate not met), 902 (exactly 15), 903 (full month,
35 paid days), 904 (half day with punches: 19.5 worked, attended 20, used 0.5, paid out 3.5), 905
(missed punch, HR approves the half-day correction: the half counts as worked) and 905d (declined:
the half is absent, 2 quarters), 906 (half-day LWP pays the same as 904), 907/908 (E6 approved vs
Open), 909/910 (special day not doubled / doubled), 911 (automatic Half Day unchanged), 912 (Absent
changed by a half-day leave), and the same month twice. Month close for 40 bulk staff: 5.7 s,
about 63 s for 445. `rehearsal_063.py cost` on the synthetic company: **+54 paid days for 60
people** against the accrual values; the rupee figure cannot be shown (no salaries in synthetic
data).

**What it cannot prove** (07a 3.4): DTC's real device quirks and shift mix, its real data
mistakes, the rupee size of the extra cost, and AC-104 (card equals the desk report for two real
staff), which can only be done on DTC after switch-on.

## 10 · Known gaps

| Gap | Label |
|---|---|
| No rehearsal on DTC data; no extra-cost figure yet | **temporary debt** - removed by the rehearsal (runbook R-1..R-7) |
| R-29, R-54, R-58..R-60 wording/placement differences above | **intentional trade-off**, raised for Surbhi |
| AC-15 3G timing and AC-23 full-month query count not measured | temporary debt - measure on the copy |
| `my_requests` in the Inbox part still says "Waiting for your approver" for LWP | acceptable simplification (the next frame is not drawn) |
| Hindi not installed | intentional (X-5) |
| A request withdrawn while HR has the Team page open gives a toast, not a row sentence | acceptable simplification |

## Subtract pass

Removed while building: a separate Inbox part for HR (one OR branch), a Hindi file (would
switch Hindi on), a `told` field (Notification Log rows are the record), the AC-18 "31000"
scan (proved nothing without a salary), a change to `attendance_correction.py` (the
doctype hook keeps 060 untouched), a background job for the notice. Kept: the lock (D1,
OD-8), the per-row DTC facts on the Team page (the prototype draws them).
