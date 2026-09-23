---
slice: 043-redesign-wave3
artifact: 02-functional-spec
author: hrms-business-analyst
date: 2026-09-24
revision: 2
status: draft, revised 2026-09-24 after this slice's `01c` and `07` landed. **Revision 2 corrects two things revision 1 got wrong** — see "What changed in revision 2" below
inputs: [../009-ess-portal-redesign/00-assessment-and-plan.md §4 Wave 3 and Appendix C, ../009-ess-portal-redesign/appendix-c-time-pay.md, ../009-ess-portal-redesign/01b-ux-design.md, ../009-ess-portal-redesign/00f-decisions-2026-09-22.md, ../034-redesign-wave1/00g-decision-register.md (W1D-01 to W1D-21), ../034-redesign-wave1/02-functional-spec.md revision 4, ../034-redesign-wave1/01c-security-privacy-requirements.md revision 4, ../034-redesign-wave1/03-implementation-notes.md §4, ../035-wrong-numbers/03-implementation-notes.md, prototype-v2.html, 01c-security-privacy-requirements.md (043, revision 1), 07-devops-inputs.md (043), ../034-redesign-wave1/03-implementation-notes.md stretch 4 (OPS-31, measured 2026-09-23)]
brief: there is no `01` for this slice. The approved brief is `../009-ess-portal-redesign/00-assessment-and-plan.md` (Wave 3), the design is `../009-ess-portal-redesign/01b-ux-design.md`, and the decisions are in `00f-decisions-2026-09-22.md` and `../034-redesign-wave1/00g-decision-register.md`
---

# Wave 3 — Time and Pay: functional spec

## What changed in revision 2

**Two things in revision 1 were wrong, and both would have shipped.** They are corrected
in place; this list is so nobody works from a printout of revision 1.

| # | Revision 1 said | The truth, verified in code | Where it is fixed | Ticket |
|---|---|---|---|---|
| **1** | The Why? sheet should end with *"If a day here is wrong, fix the day first — the rule follows the attendance record."* | **False.** `hrms/hrms/alvoraa_late_rules/late_rules.py:208-215` skips any Attendance Deduction that is already submitted, in the weekly run **and** in HR's catch-up `run_for_range:251`. Correcting 4 August in September leaves the deduction, and the lost pay, exactly where they are. The only remedy is a person cancelling the deduction by hand, and that only helps while the Salary Slip is unsubmitted | §18.4, AC-58, AC-59 | **ALV-115** |
| **2** | The manager's deduction email carries the **rupee amount** | **False.** `attendance_deduction.build_explanation:37-59` uses `lwp_days` and never `lwp_amount` — there is no currency figure in it. What it does carry is the **leave type**: "Taken: 0.5 from Sick Leave, 0.5 as loss of pay", sent as one identical body to the employee and the manager (`notify:182-205`). So a manager learns their report used **Sick Leave**, which this product hides on every screen | Bad news 1, §11 F-3b, AC-17 | **ALV-113** |

**Why the second one matters beyond the fix:** AC-17 as revision 1 wrote it ("carries the
days and not the rupee amount") would have **passed on the day it was written**, because
the amount was never there. A green test, and the leak still going out by email. That is
the shape of mistake this spec exists to prevent, and I made it.

Everything else in revision 2 is the five spec changes the security review requires, the
five Wave 3 `01c` verdict items, and two DevOps corrections. Nothing else was touched.

---

## Bad news first

**Four things, and the first one is a live privacy leak that Wave 3 will make worse if it
is not fixed in the same slice.**

1. **A manager's deduction email tells him which leave type his report used.**
   *Corrected in revision 2 — the leak is real, but it is not the one revision 1 named.*
   `attendance_deduction.notify:182-205` puts the employee's and the manager's `user_id`
   in one `recipients` list and sends both the identical stored `explanation`. That text
   carries **days, not rupees** (`build_explanation:37-59` uses `lwp_days`; there is no
   currency figure anywhere in it) — so Q-b of 14 Sep is met on the amount. It is
   breached on something plainer: **"a colleague's leave type"**, which §5 forbids on
   every screen. A manager whose report had half a day taken from Sick Leave reads
   "Taken: 0.5 from Sick Leave, 0.5 as loss of pay" in his inbox. **Severity Major,
   P2** (043 `01c`). Fixed here: AC-17, §20 D-1, ticket **ALV-113**.
2. **The payslip list endpoint is not behind the payroll feature.**
   `hr_api.get_payslips:1515` carries `@frappe.whitelist()` and nothing else, while
   `get_payslip:1563` and `download_payslip:1596` both carry
   `@requires_feature("payroll")` — **confirmed fact**, read at lines 1514, 1561 and 1594.
   W1D-01 hides the salary parts of the menu on a tenant without payroll; the list behind
   them is still callable by hand. **This is a Wave 3 fix with an acceptance check**,
   not a decision.
3. **Loss of pay is worked out as base ÷ calendar days.** That is a payroll and legal
   question and **this spec does not rule on it** (Q18). Wave 3 explains the figure in
   plain words on screen, which makes the method visible to 400 people. §20 D-3.
4. **The prototype's "Who is away · next two weeks" card contradicts a decision already
   taken.** 009 design decision 3 closed Q15 as "presence only — approved leave is the
   reason". A forward-looking list of who is booked away **is** approved leave. The card
   is dropped, and §21 records it.

**Good news, and it matters:** the two worst wrong numbers are already fixed on `dev`.
Slice 017 gave lateness a real shift start and a configurable grace
(`attendance_analytics._shift_row:233`, `_shift_grace:259`, `org_late_grace:254`), and
slice 035 gave leave and holidays one true source (`hr_api._ledger_leave_balances:88`,
`_own_upcoming_holidays:312`). **Verified at `origin/dev` `8718f27`.** Wave 3 builds on
true numbers, which is exactly what the plan asked for.

---

## 0. How to read the numbers in this file

**Story and check numbers are per slice.** This slice runs `US-1` to `US-13` and `AC-1`
to `AC-61` (revision 2 added AC-57 to AC-61). Cite them as "043 AC-12" so they are not confused with Wave 1's or Wave 2's.

Claims carry a label: **Confirmed fact** (read in the source, file and line),
**Stakeholder statement**, `[ASSUMPTION]`, **Recommendation**, **Risk**,
**Open question**.

---

## 1. Cross-module reach — named before anything is specified

| App | Touched how |
|---|---|
| `alvoraa_portal` | New `time_api.py` and `pay_api.py`; edits to `hr_api.py` (payslips, shift types, encashment, retiring two endpoints) and `attendance_correction.py` (the month payload); the Time and Pay markup inside Wave 1's include files |
| `hrms` (our fork) | `alvoraa_late_rules` — **read** the rule's remaining fields for the explanation, and **change one thing**: the manager's notification email (D-1). `alvoraa_hr_core/access.py` reused unchanged |
| `erpnext` | Read only — Salary Slip, Salary Detail, Additional Salary, Holiday List, Shift Type, Shift Assignment |
| `frappe` | Read only, plus the print pipeline for the payslip PDF |
| `alvoraa_goals` | **Not touched** |
| `alvox_compensation` | **Not touched.** Not installed on either client tenant |

**HRMS domains involved:** attendance (calendar, day detail, corrections, shifts),
leaves (balances, apply, past leave, encashment), payroll (payslip, deductions, year to
date, PDF), org structure (who may open whose month).

**Personas** are Wave 1's (034 §2, W1D-02 and W1D-20): **Rahul**, **Sandeep**, **Kamal**,
**Priya**, **Asha**. Pay is **own-record only for everybody** — commit `30e2d13` made it
so and this slice keeps it (appendix C, P-13).

---

## 2. Questioning the ask before specifying it

**The brief's problem is the right one, and it is named with evidence.** Appendix C did
not say "people distrust the portal"; it measured a 09:25 arrival on a 09:30 shift being
called 25 minutes late, and 27 late days in a month where the real rule counted 4. That
cause is fixed. What is left is the second half of the same problem: **a correct number
that nobody can check is still not trusted.** So Wave 3's job is explanation, not more
numbers.

**What happens after each thing we put on the screen:**

| Thing | Decision it drives | Who decides | Could the system act instead? |
|---|---|---|---|
| The month calendar | "that day is wrong — fix it" | the employee | No. The correction is the employee's account of their day |
| "Late by 12 min (within grace)" | usually nothing — it stops an argument | — | It already acts: the weekly job decides what counts. The screen only shows why |
| "Why was ₹548 deducted?" | raise it with HR, or accept it | the employee | No |
| Days off ahead | plan leave | the employee | No |
| Payslip PDF | keep it, show it to a bank | the employee | No |
| "Your record this year" (late-rule days) | change behaviour, or challenge the record | the employee | **No, and this is the one to watch.** A running per-person lateness tally is one design step from a ranking. §18.4 says why we will not take that step |

---

## 3. Gap analysis — what already exists, checked in the source

Line numbers from `origin/dev` at `8718f27`, read in
`.claude/worktrees/043-redesign-wave3` on 2026-09-24.

### Time

| Requirement | What exists today (file : line) | Verdict | Cost |
|---|---|---|---|
| Month calendar with day states | `attendance_correction.month:360` returns `days[].state`, `holiday`, `totals`, `late_grace_mins`, `can_review`, `can_request` | **Reuse**, plus return `Holiday.weekly_off` so a weekly off and a public holiday are told apart | S |
| Day detail: shift track, in/out, punches, late chip | `attendance_correction._day:476`, now correct — `_shift_start:74` and `_shift_minutes` read one cached row through `_shift_row:233` (slice 017) | **Reuse, unchanged** | — |
| True minutes with grace, "Late by 12 min (within grace)" | `_day` sets `late_by_mins`, `grace_mins` and `is_late` separately (lines 533–539) | **Reuse** — the design's wording is already possible without a code change | S |
| "Arrived within grace" statistic | `_totals:573` counts late days past the grace (line 586) | **Reuse**, relabel | S |
| The old calendar | `hr_api.get_attendance_calendar:1456` — assumes Sat/Sun off, marks any record-less weekday Absent, uses UTC today. **Only caller is `hrms-employee.html:7128`** | **Drop** — retire the endpoint and the panel in one commit | S |
| The old Attendance Request panel | `hr_api.submit_attendance_request:1943` — `ignore_permissions=True`, no reason check, shows "Draft". **Only caller is `hrms-employee.html:7965`** | **Drop** — retire both; the correction flow replaces it | S |
| "Your shift" card | nothing reads Shift Assignment for the portal | **Build** — today's assignment beats `Employee.default_shift`, as Frappe HR does | S |
| Days off ahead | `hr_api._own_upcoming_holidays:312` (slice 035) | **Reuse, unchanged** | — |
| Weekly off weekdays | Holiday rows with `weekly_off = 1` on the employee's own list | **Extend** — derive the weekday names from the list, never hard-code | S |
| Leave left, past leave | `hr_api._ledger_leave_balances:88`, `get_leave_summary:1685` | **Reuse**; **extend** past leave to list Leave Ledger Entry rows whose `transaction_type` is "Attendance Deduction", so the late rule's days are visible | S |
| Apply leave with preview | `hr_api.apply_leave:1789`, `preview_leave_request:1818` (already reads the ledger) | **Reuse** | S |
| Fix from a tapped day | `attendance_correction.raise_correction:659`, `reasons:336`, `withdraw:700`, `my_requests:650` | **Reuse**; `raise_correction` already takes `to_date`, so multi-day works with a client change | S |
| "I was on leave" for a past day | — | **Extend** — route it to `apply_leave` rather than to a correction | S |
| Change of shift | `hr_api.submit_shift_request:1917`; `get_shift_types:1880` returns **every** shift type with `ignore_permissions=True`, no feature gate and no caller check (confirmed, lines 1879-1885) | **Extend** — require an Active Employee record, drop `ignore_permissions`, and scope the list. **Correction from 043 `01c` SEC-7: Shift Type has no `company` field** (verified in `hrms/hrms/hr/doctype/shift_type/shift_type.json`), so "the caller's company's" cannot be built as revision 1 wrote it. The scope must be by something that exists — §20 D-6 | S |
| Late rule explained | `hr_api.get_my_attendance_deductions:2777` returns thresholds, free count, per-violation days and rounding, but **not** `count_early_exit` as a flag, `week_start_day`, `deduct_from_leave_first`, `leave_types` or `daily_wage_basis` (confirmed, lines 2795–2801) | **Extend** — return those fields and build the words from them. **No hard-coded number and no hard-coded day of the week** | M |
| "Who is away next two weeks" | `get_week_presence:3151` is presence only and backward-looking | **Drop** — 009 design decision 3. §21 row (c) | — |

### Pay

| Requirement | What exists today | Verdict | Cost |
|---|---|---|---|
| Payslip list | `hr_api.get_payslips:1515` — **no `@requires_feature("payroll")`**, reads with `ignore_permissions=True` (`:1526`), and returns `{"payslips": ..., "employee": emp}` where `emp` is `_get_employee()`'s whole row — `date_of_birth`, `gender`, `cell_number`, `branch`, `reports_to` and the rest (`hr_api.py:152-160`, confirmed) | **Extend** — add the gate **and** cut the payload to the six-key `me` block. Wave 1's biggest finding, live today, on the screen people attach to a support ticket (043 `01c` SEC-3). AC-30, AC-6 | S |
| One payslip | `get_payslip:1563` — gated, own-only through `_own_payslip:1545`; drops zero rows; **does not return `additional_salary` on a line** | **Extend** — return the link so "Why?" can follow it | S |
| Payslip PDF | `download_payslip:1596` — own-only, uses `frappe.get_meta("Salary Slip").default_print_format`, which is unset on PP Jewellers | **Configure** — set the tenant's own print format. No code change; a per-tenant action (release gate 3) | S |
| "Why was this deducted?" | The chain exists in data: Salary Detail `additional_salary` → Additional Salary `ref_docname` → Attendance Deduction → its Violation child rows | **Build** an own-only read of one Attendance Deduction, ownership checked the way `_own_payslip` does | M |
| The explanation in plain words | `Attendance Deduction.explanation` is stored and technical, and the same text is emailed | **Build** the words from the fields; never show the stored text | S |
| Year to date | Salary Slip stores `year_to_date`, `gross_year_to_date`; Salary Detail stores its own `year_to_date` | **Reuse** — read from the latest slip. **Never add slips up** | S |
| "More than July" comparison | previous slip | **Build**, with the caveat in §11 D-2 | S |
| Leave encashment | `submit_leave_encashment:1982` never sets `leave_period` or `currency`, which the desk's own script sets (`leave_encashment.js:101-109`) — **likely fails every time** | **Extend** — set both server-side | S |
| Salary advance | `submit_advance_request:1963` — no repayment period field, no approver | **Drop** from Wave 3 (§12); the button keeps today's behaviour behind its existing flag | — |
| Form 16 | nothing in `hrms`, `erpnext` or `india_compliance` | **Drop** (§12) | — |

**No new DocType, no custom field, no patch, no migration.** Two endpoints are **removed**
and their panels with them.

**Where two models describe the same thing.** Lateness is described by
`attendance_analytics`/`attendance_correction` (what the screen shows) and by
`alvoraa_late_rules` (what actually costs money). **The single source of truth for "did
this day count" is `alvoraa_late_rules`**, and the screen must say so: the calendar's chip
describes the day, the late-rule card describes the money, and where they could disagree
the screen shows the rule's answer. AC-12 pins it.

---

## 4. Process flow — what actually happens

### 4a. Rahul checks a day (the common path)

1. He opens Time. The Days tab shows the month calendar and his statistics.
2. **Decision point — is anything wrong?** No → he leaves. Yes → he taps the day.
3. The day sheet shows: the shift track, his punches, the true minutes, the grace row
   naming the setting ("15 minutes, set by PP Jewellers"), and what the day counted as.
4. **Decision point — what was actually true?**
   - "I was at work" → a correction, pre-filled with that day, reason required.
   - "I was on leave" → the apply-leave sheet for that date, with the ledger preview.
   - "That is right" → he closes it.
5. He sends. The row becomes "Waiting for <decider>". Wave 2's Inbox count moves.

**Unhappy paths:** no holiday list assigned (slice 035's sentence); no shift assignment
(the shift card says so rather than showing blank times); a day before his joining date
(not drawn as anything); the month is in the future (empty, with a plain line); he is
looking at somebody else's month and may not (`_subject:251` refuses, with its own
wording).

### 4b. Rahul asks why ₹548 came off his pay

1. Pay shows the latest payslip: period, paid days, take-home, Download PDF.
2. The deduction line "Late Coming Deduction ₹548.39" carries a **Why?** control.
3. He taps it. The sheet walks the real week: 3 Aug 70 min (free — first this week),
   4 Aug 65 min (counted), 5 Aug left 80 min early (counted), 7 Aug 90 min (counted);
   3 counted × ¼ = ¾ day, rounded up to 1 day; half from Casual Leave, half from pay.
4. **Decision point — does he accept it?** Yes → he closes it. No → "How the rule works"
   takes him to the Time tab's rule explanation, which names the settings, so his
   conversation with HR is about a setting and not about the product.

**Unhappy paths:** the deduction was typed by hand (no Attendance Deduction behind it) →
the sheet says so plainly rather than showing an empty week; the slip has no late
deduction → there is no Why? control at all; the tenant has no payroll → there is no Pay
salary tab (W1D-01) and the endpoints refuse.

---

## 5. Permission and visibility matrix

| | Rahul | Sandeep (manager) | Priya (store HR) | Kamal (HR + reports) | Asha (no Employee record) |
|---|---|---|---|---|---|
| Time: own month, day detail, punches | ✓ | ✓ | ✓ | ✓ | — (Time is not in her menu, 034 §3) |
| Time: **another person's** month | — | ✓ own reporting line, deep (`_subject:251`) | ✓ whoever `_may_review()` allows | ✓ | — |
| Time: own shift, own holidays, own weekly offs | ✓ | ✓ | ✓ | ✓ | — |
| Time: own leave balances and past leave, with reasons | ✓ | ✓ | ✓ | ✓ | — |
| Time: **another person's** leave reason | — | — | — | — | — |
| Time: late rule settings for the rule that covers them | ✓ | ✓ | ✓ | ✓ | — |
| Time: own late-rule record (days and amounts) | ✓ | ✓ | ✓ | ✓ | — |
| Time: a report's late **days** | — | ✓ (`get_team_late_list:2806`) | ✓ | ✓ | — |
| Time: a report's late **amount** or explanation text | **— never** | **— never** | **— never** | **— never** | — |
| Pay: own payslip, PDF, year to date | ✓ where `plan_payroll` | ✓ own only | ✓ own only | ✓ own only | — |
| Pay: **anyone else's** payslip | **— never, for anyone, including HR** (HR uses the desk) | — | — | — | — |
| Pay: own "why" deduction detail | ✓ | ✓ | ✓ | ✓ | — |
| Pay: Expenses | ✓ always (required feature) | ✓ | ✓ | ✓ | — |
| Pay: Leave encashment | ✓ where `leave_encashment` | ✓ | ✓ | ✓ | — |
| Pay: Request advance | ✓ where `advance_request` | ✓ | ✓ | ✓ | — |

### The negative cases, stated on purpose

**The Time screen must NOT show:**

| Must not | Why |
|---|---|
| Any colleague's leave type or reason | `01b` §9, slice 002's one-way rule |
| A forward-looking list of who is booked away | 009 design decision 3 — approved leave **is** the reason |
| A report's loss-of-pay **amount**, or the stored `explanation` text | Q-b. `_deduction_rows:2752` carries `lwp_amount` and `explanation` for the **employee's own** view; the team path must keep using `get_team_late_list`'s fixed field list |
| A ranking of people by lateness | §18.4 |
| Another person's punch times to anyone outside `_subject`'s rule | `attendance_correction._subject:251` is the whole control and stays it |
| The caller's `date_of_birth`, `gender`, `cell_number` | the Wave 1 lesson — a fixed payload key list (AC-6) |
| A hard-coded grace figure or a hard-coded week-start day | `01b` §14 item 7. Every number in the explanation comes from the rule record |

**The Pay screen must NOT show:**

| Must not | Why |
|---|---|
| Anybody else's payslip, in any state, to anybody | `_own_payslip:1545`. The refusal is identical whether the slip belongs to somebody else, is a draft, or does not exist — so a slip name cannot be used to probe |
| A payslip on a tenant without payroll | W1D-01, plus the missing gate on `get_payslips` (AC-30) |
| A take-home figure in any notification, email or toast | appendix B §C |
| The stored `explanation` text | it is technical and it is the same string that goes in the email |
| A comparison that implies a raise when it was a one-off | §11 D-2's caveat, AC-24 |
| Form 16, or an advance limit, as if they existed | both are Sample in the prototype and neither has a data source (§12) |

---

## 6. Numbers must equal the lists they link to

Surbhi's standing rule applies here too, and Time is full of totals.

| Number on screen | The list it must equal | How |
|---|---|---|
| "Days worked · 42h 10m" | the `present` rows in the day list | one `_totals:573` pass over the same `days` array the list renders |
| "Arrived within grace · 5 of 5" | the day rows whose chip is not "Late by …" | the same `is_late` flag, computed once in `_day:476` |
| "Days marked absent · 3" | the rows the calendar draws red **and** the days the Fix sheet pre-fills | **one helper**, shared with Wave 2's Home gap count (042 §11) |
| "Weekly offs so far · 4" | the rows whose state is a weekly off | requires `Holiday.weekly_off` in the month payload |
| "Nothing counted in September" | the late-rule card's violations for the month | `current_week_projection` plus the month's submitted Attendance Deduction rows — **never** re-derived from the calendar |
| "Your record this year · 3.5 days" | the month rows in the year table | one query, grouped in Python from the same rows |
| Year to date on Pay | the slips listed below it | **read from the latest slip's stored fields; never added up.** AC-25 fails if the code sums slips |

**Rule:** where a total and a list could be computed two ways, they are computed **once**
and the list is rendered from the same array the total was taken from. AC-11 enumerates
every total on both screens and asserts it against its list.

---

## 7. Stories

| # | Story | Screen | Points | Carries |
|---|---|---|---|---|
| **US-1** | As **Rahul**, I want a month at a glance with every day's state, so that I can see what is wrong without reading a table. | Time · Days | 5 | AC-1, AC-2, AC-3 |
| **US-2** | As **Rahul**, I want a day to tell me the true minutes and whether they counted, so that I stop arguing about 09:25. | Time · day sheet | 5 | AC-4, AC-5 |
| **US-3** | As **Rahul**, I want to fix a day where I stand, so that an unpaid day does not survive because the form was hard to find. | Time · day sheet | 5 | AC-7, AC-8, AC-9 |
| **US-4** | As **Rahul**, I want to know my shift and my days off ahead, so that I can plan. | Time · Days | 3 | AC-10 |
| **US-5** | As **Rahul**, I want the late rule explained from my organisation's own settings, so that no number in it is invented. | Time · Late rule | 5 | AC-12, AC-13 |
| **US-6** | As **Rahul**, I want my leave balance and my past leave, including days the late rule took, so that the balance and the history agree. | Time · Leave | 3 | AC-14, AC-15 |
| **US-7** | As **Rahul**, I want my payslip in my organisation's own format, so that it is the document a bank will accept. | Pay | 3 | AC-22, AC-23 |
| **US-8** | As **Rahul**, I want to follow a deduction back to the days that caused it, so that I can check it myself. | Pay · Why? | 8 — **split**: (a) return the link, (b) the own-only read, (c) the plain-words sheet | AC-26 to AC-29 |
| **US-9** | As **Rahul**, I want the year so far taken from what was actually paid, so that the figure matches my slips. | Pay | 3 | AC-25 |
| **US-10** | As **Sandeep**, I must never learn how much a report lost in pay — on a screen or in an email — so that a manager stays a manager. | Time · team; the notification | 5 | AC-16, AC-17, D-1 |
| **US-11** | As **Rahul**, my payslip must be unreachable by anyone else, and unreachable at all on a tenant without payroll. | Pay | 3 | AC-30, AC-31 |
| **US-12** | As **Rahul**, I want every state on both screens named, so that an empty month never reads as "you did not work". | Time, Pay | 3 | AC-32 to AC-38 |
| **US-13** | As the next engineer, I want the two old duplicate screens gone, so that two paths cannot disagree about the same day. | — | 3 | AC-18, AC-19 |

### YouTrack-ready table

| Summary | Description | Persona | Points | ACs |
|---|---|---|---|---|
| Month calendar on true states | Six day states, weekly off told apart from a holiday, tap to open | Rahul | 5 | AC-1 to AC-3 |
| Day detail with true minutes and grace | "Late by 12 min (within grace)"; grace row names the setting | Rahul | 5 | AC-4, AC-5 |
| Fix a day where you stand | Correction or leave from the tapped day; multi-day supported | Rahul | 5 | AC-7 to AC-9 |
| Your shift and days off ahead | Assignment beats default shift; own holiday list; weekly offs derived | Rahul | 3 | AC-10 |
| Late rule explained from the rule record | Every figure and the week-start day read from the rule; nothing hard-coded | Rahul | 5 | AC-12, AC-13 |
| Leave balance and past leave agree | Ledger balance; past leave includes the late rule's ledger entries | Rahul | 3 | AC-14, AC-15 |
| Payslip in the tenant's own format | Print format set per tenant; own-only download | Rahul | 3 | AC-22, AC-23 |
| Why was this deducted | Slip line → Additional Salary → Attendance Deduction → violations, in plain words | Rahul | 8 (split 3/3/2) | AC-26 to AC-29 |
| Year to date from stored fields | Read from the latest slip; never summed | Rahul | 3 | AC-25 |
| A manager never learns a report's loss of pay | Payload and **email** both days-only | Sandeep | 5 | AC-16, AC-17 |
| Payslips are own-only and payroll-gated | `requires_feature` on the list endpoint too | Rahul | 3 | AC-30, AC-31 |
| Every state named on Time and Pay | Loading, empty, no data, error, no permission | Rahul | 3 | AC-32 to AC-38 |
| Retire the old calendar and the old request panel | Two endpoints and two panels removed in one commit | engineer | 3 | AC-18, AC-19 |

---

## 8. Data model

**No new DocType, no new field, no patch, no migration.** Two whitelisted functions are
**deleted**.

| Shown | Doctype · field | Why an existing field carries it |
|---|---|---|
| Day state | Attendance · `status`; Holiday · `weekly_off`; Leave Application; Attendance Request | `month:360` already assembles these; it needs `weekly_off` added to the payload |
| True minutes, grace, is_late | computed in `_day:476` from Shift Type `start_time` and `late_entry_grace_period`, and the org default `alvoraa_attendance_late_grace_mins` | slice 017. **Never** a literal in the portal |
| Shift card | Shift Assignment · `shift_type`, else Employee · `default_shift` | Frappe HR's own precedence |
| Weekly off weekdays | Holiday rows with `weekly_off = 1` | Derived per employee; **no hard-coded Sat/Sun** (the old calendar's bug, `get_attendance_calendar:1456`) |
| Leave balance | Leave Ledger Entry through `_ledger_leave_balances:88` | slice 035 |
| Past leave, including the rule's days | Leave Application, plus Leave Ledger Entry · `transaction_type = "Attendance Deduction"` | the ledger is the reason the balance is what it is |
| Late-rule settings | Attendance Deduction Rule · thresholds, `count_early_exit`, `free_violations_per_week`, `deduction_per_violation_days`, `round_up_from_days`, `round_up_to_days`, `week_start_day`, `deduct_from_leave_first`, `leave_types`, `daily_wage_basis` | All exist; six are already returned (`:2795`), the rest are the extension |
| The record this year | Attendance Deduction · `week_start`, `deduction_days`, `lwp_days`, and its `leave_deductions` child | Money lands in the `week_end` month (a week can cross months — AC-13) |
| Payslip summary | Salary Slip · `start_date`, `end_date`, `payment_days`, `gross_pay`, `total_deduction`, `net_pay`, `rounded_total` | already returned by `get_payslip:1563` |
| The "why" link | Salary Detail · `additional_salary` → Additional Salary · `ref_doctype`, `ref_docname` | **The one addition to `get_payslip`'s payload** |
| Year to date | Salary Slip · `year_to_date`, `gross_year_to_date` | stored by Frappe HR; read, never summed |

**`get_time`'s and `get_pay`'s payload keys are fixed lists**, the same discipline as
Wave 1's `frame_api.FRAME_KEYS:49` and `ME_FIELDS:43`. AC-6 asserts them per persona.
The `me` block is the same six fields and never more.

---

## 9. Every state, on both screens, per persona

### Time

| Persona | Loading | Empty | No data | Error on one card | No permission | Page error |
|---|---|---|---|---|---|---|
| Rahul | skeleton ≤ 300 ms (AC-32) | a month with no records: the calendar renders with every day in its true state and the day list says "No attendance was recorded this month." — **never a blank grid** (AC-33) | no shift assignment → the shift card says "No shift is set for you. Ask HR." (AC-34); no holiday list → slice 035's sentence; no late rule covers this person → the Late rule tab says "No late-coming rule applies to you." and the tab is still there (AC-35) | the card says what failed + Try again; the calendar still works (AC-36) | a month before the joining date, or a future month → a plain line, not an error (AC-37) | Wave 1's page-error sentence (AC-38) |
| Sandeep | AC-32 | AC-33 | AC-34, AC-35 | AC-36 | opening a month outside his line → `_subject:251`'s refusal, shown as a sentence (AC-37) | AC-38 |
| Priya / Kamal | AC-32 | AC-33 | AC-34, AC-35 | AC-36 | AC-37 | AC-38 |
| Asha | Time is not in her menu (034 §3). Typing `#time` shows Wave 1's no-permission sentence | — | — | — | AC-37 | AC-38 |

### Pay

| Persona | Loading | Empty | No data | Error | No permission | Page error |
|---|---|---|---|---|---|---|
| Rahul, payroll on | AC-32 | no slips yet → "No payslips have been issued to you yet." with Expenses still reachable (AC-39) | a deduction with no Attendance Deduction behind it → the Why? sheet says "This was entered by hand, so there are no days behind it." and does **not** show an empty week (AC-29) | AC-36 | — | AC-38 |
| Rahul, **payroll off** | — | — | — | — | no My pay entry, no salary tab, no payslip search result; `#pay` shows Wave 1's no-permission sentence and Pay opens `#pay/expenses` (034 AC-44); the endpoints **refuse** (AC-30) | AC-38 |
| Sandeep / Priya / Kamal | as Rahul — **own record only** | | | | opening somebody else's slip → the identical refusal `_own_payslip:1545` gives (AC-31) | AC-38 |
| Asha | Pay is not in her menu | — | — | — | AC-37 | AC-38 |

**Wording** (translatable, `__()`; taken from `01b` where the designer wrote it):

| Where | Exact words |
|---|---|
| A day within grace | "Late by 12 min (within grace)" *(009 design decision 7 — take it as written)* |
| A day past grace | "Late by 75 min" |
| On time | "On time" |
| An auto-marked absent day | "Marked absent" *(design correction D5 — **not** "No punch and no leave")* |
| The grace row on the day sheet | "15 minutes of grace, set by PP Jewellers" — the number and the name from the record |
| What counts | "Arriving **more than** 60 minutes after your shift starts…" *(D5 and Q20: the code uses `>` at `late_rules.py:75`; the words change, not the code)* |
| No attendance this month | "No attendance was recorded this month." |
| No shift | "No shift is set for you. Ask HR." |
| No rule | "No late-coming rule applies to you." |
| No payslips | "No payslips have been issued to you yet." |
| Hand-entered deduction | "This was entered by hand, so there are no days behind it." |
| Payslip refused | "That payslip is not available." *(`_own_payslip:1545`'s existing wording, reused)* |
| No holiday list | "No holiday list is assigned to you yet. Ask HR to set one up." *(slice 035's wording)* |

---

## 10. Acceptance criteria

### US-1 · the month

- **AC-1** *Given* a month containing a worked day, an auto-marked Absent day, a weekly
  off, a public holiday, an approved leave day, today and a future day, *when* Time
  loads, *then* the calendar draws six distinct states, each labelled in words in its
  accessible name, and a weekly off is **not** drawn as a public holiday.
- **AC-2** *Given* 7, 8 and 9 Sep are real auto-marked Absent rows, *then* each reads
  **"Marked absent"**, not "No punch and no leave" (design correction D5).
- **AC-3** *Given* any day with a record or an absence, *when* it is tapped, *then* the
  day sheet opens; a future day and a day before the joining date are not tappable and
  are not drawn as absent.

### US-2 · the day

- **AC-4** Four arrivals against a 09:30 shift with 15 minutes of grace:

  | Punch | Chip | `late_by_mins` | `is_late` |
  |---|---|---|---|
  | 09:25 | "On time" | 0 | false |
  | 09:30 | "On time" | 0 | false |
  | 09:42 | "Late by 12 min (within grace)" | 12 | **false** |
  | 10:45 | "Late by 75 min" | 75 | true |

  The minutes shown are always the true minutes (009 design decision 7). A 09:25 punch
  must **not** produce 25 — the bug slice 017 fixed; this is the regression guard.
- **AC-5** *Given* the day sheet, *then* it shows a Grace row naming the source: the Shift
  Type's own `late_entry_grace_period` where set, otherwise the organisation default
  `alvoraa_attendance_late_grace_mins`, otherwise "no grace". A static check finds **no
  numeric grace literal** in the Time include files.
- **AC-6** `get_time`'s, `get_pay`'s **and `get_payslips`'s** payload keys are exactly
  §8's lists per persona, and the `me` block is exactly `employee`, `employee_name`,
  `designation`, `department`, `image`, `company` — never `date_of_birth`, `gender`,
  `cell_number`, `date_of_joining`, `reports_to` or `branch`. **`get_payslips` is the
  third one on purpose** (043 `01c` SEC-3): it returns the whole Employee row today. A
  static check also fails if any Wave 3 module passes a `_get_employee()` result straight
  into a payload.

### US-3 · fixing a day

- **AC-7** *Given* Rahul taps Fix on 7 Sep with 8 and 9 Sep also absent, *then* the sheet
  offers the range 7–9 Sep, one Attendance Request is created for the range, and the
  reason is **required** (`raise_correction:659` enforces it; the retired endpoint did
  not).
- **AC-8** *Given* he chooses "I was on leave" on a past day, *then* the apply-leave sheet
  opens for that date with the ledger preview, and **no** Attendance Request is created.
- **AC-9** *Given* a day already covered by an open correction, *then* Fix is not offered
  for it a second time, and the day shows "Request sent · waiting for <decider>".

### US-4 · shift and days off

- **AC-10** *Given* Rahul, *then* the shift card reads "09:30 – 18:30 · off on Thursdays",
  where the times come from today's Shift Assignment (falling back to
  `Employee.default_shift`) and the weekday comes from **his own** holiday list's
  `weekly_off` rows — **not** from a hard-coded Sat/Sun. Days off ahead lists his own
  list's named holidays with their real descriptions.

### US-5 · the late rule

- **AC-11 (the totals rule)** For every total on Time and Pay listed in §6, the number
  equals the list it links to, for each persona fixture. The test enumerates the totals
  from one place, so a new total with no matching list fails it.
- **AC-12** *Given* a tenant whose rule has `late_threshold_minutes` 45,
  `count_early_exit` off, `free_violations_per_week` 2, `week_start_day` Sunday and
  `deduct_from_leave_first` off, *then* the explanation says 45, says nothing about
  leaving early, says two free, says weeks run Sunday to Saturday, and says the day comes
  out of pay. **Every figure changes when the record changes**, proved by a second fixture
  with different values. A static check finds no `60`, no `Monday` and no "Casual Leave"
  literal in the rule copy.
- **AC-13** *Given* a week that crosses a month boundary (29 Sep – 5 Oct), *then* its
  deduction appears in the **October** row of "Your record this year", because the money
  lands in the `week_end` month — and the row's total equals the sum of the weeks listed
  under it.

### US-6 · leave

- **AC-14** *Given* Rahul whose Casual Leave ledger shows 0 of 8 after the late rule took
  3 days, *then* the ring reads **0 left of 8**, the apply-leave dropdown offers the same
  figure, and the preview agrees. A fixture where the three disagreed is the regression
  guard (the defect appendix C recorded at T-09).
- **AC-15** *Given* the same employee, *then* Past leave lists both his Leave Applications
  **and** the Leave Ledger Entry rows whose `transaction_type` is "Attendance Deduction",
  labelled "Taken by the late-coming rule" — so the balance and the history agree.

### US-10 · a manager never learns the amount

- **AC-16** *Given* Sandeep opens the team late list, *then* the payload carries
  `deduction_days` and `lwp_days` and **not** `lwp_amount` and **not** `explanation`
  (today's behaviour, pinned so Wave 3 cannot regress it).
- **AC-17 (D-1) — rewritten in revision 2; the version in revision 1 would have passed
  while the leak survived.** The fixture is a week where `deduct_from_leave_first` is on
  and the days came from **Sick Leave**. *Given* a tenant with `notify_manager` on,
  *when* an Attendance Deduction is submitted, *then* all four of these hold, asserted on
  the **rendered body per recipient**:

  | # | Rule | Oracle |
  |---|---|---|
  | 1 | **Separate bodies.** The employee's body is byte-identical to today's; the manager's is composed for a manager | two rendered strings, compared |
  | 2 | **Days only in the manager's body** — no `lwp_amount`, no currency symbol, no stored `explanation` text, no minute figure, no per-day violation list | the manager's body contains no `₹`, no digit followed by "min", and none of the `explanation` string |
  | 3 | **No leave type in the manager's body** — the real leak. "Sick Leave" (and every other Leave Type name on the fixture) appears nowhere in it | substring assertion against the tenant's Leave Type list |
  | 4 | **Separate `sendmail` calls**, one recipient each, so a later change to one body cannot reach the other person | the mail-capture shows two sends, each with one recipient |

  The subject line carries the employee's name and the week and nothing else. Ticket
  **ALV-113**; 043 `01c` SEC-8.

### US-13 · retiring the duplicates

- **AC-18** `hr_api.get_attendance_calendar` and `hr_api.submit_attendance_request` are
  **deleted**, their panels are deleted, and no tracked file names them. **Confirmed
  fact:** the only callers today are `hrms-employee.html:7128` and `:7965`, so nothing
  outside the portal breaks.
- **AC-19** After the removal, a day corrected through the portal always went through
  `raise_correction:659`, so the reason check and the review status apply to every
  correction — proved by a test that no Attendance Request can be created from the portal
  without a reason.

### US-7, US-8, US-9 · Pay

- **AC-22** *Given* a tenant with its own print format set on Salary Slip, *then*
  Download gives a PDF in that format; *given* none is set, *then* it gives Frappe's
  standard format and the page does not pretend otherwise.
- **AC-23** *Given* Rahul, *then* Download works for his own slip and the browser session
  survives it (`download_payslip:1596` deliberately does not use `set_user`; the test
  asserts the session is intact afterwards).
- **AC-24** *Given* August's net is ₹11,851.61 above July's **because of a one-off
  incentive**, *then* the comparison line names it as a one-off or is not shown — it must
  not read as a raise (§11 D-2).
- **AC-25** *Given* two slips, *then* "This financial year so far" reads the latest
  slip's `year_to_date` and `gross_year_to_date`. A test **fails** if the code adds slips
  up, and a second test proves the figure survives a mid-year joiner whose first slip is
  not April's.
- **AC-26** *Given* a slip line with an `additional_salary` link, *then* `get_payslip`'s
  payload carries that link for that line and for no other.
- **AC-27** *Given* Rahul's ₹548.39 line, *when* Why? is pressed, *then* the sheet lists
  the four violations of the week of 3 Aug with their true minutes, marks the first as
  free, shows 3 × ¼ = ¾ rounded up to 1 day, and shows the split — half from Casual Leave,
  half from pay — **with every figure read from the Attendance Deduction record**, not
  recomputed.
- **AC-28** *Given* somebody else's Attendance Deduction name, *when* the "why" endpoint
  is called by hand, *then* it refuses with the same message it gives for a slip that does
  not exist, so a name cannot be used to probe.
- **AC-29** *Given* a deduction line with no Attendance Deduction behind it, *then* the
  sheet says so in the §9 wording and shows no week.

### US-8 · the Why? sheet tells the truth about an automatic decision

**New in revision 2.** These five carry 043 `01c` PRIV-6 to PRIV-10, and AC-58 is the
correction to my own §18.4. They are numbered from 57 so nothing already written moves.

- **AC-57 (PRIV-6) · it says it was automatic, when, and under which rule.** *Given* the
  Why? sheet for Rahul's ₹548.39 line, *then* it carries **all seven** of these, and a
  content test asserts each one against **two different rule fixtures** so none of them
  can be a hard-coded sentence:
  1. that the figure was worked out **automatically by a rule, with nobody looking at his
     week by hand**;
  2. **when** the rule ran, and **which** rule (the `rule_name` from the record);
  3. the inputs — the violation days, the true minutes, which ones were free;
  4. the arithmetic (per §20 D-3, which may hold the last line back);
  5. where the days came from — leave, pay, or both;
  6. **what to do if it is wrong, truthfully** (AC-58);
  7. **who to contact**, with a working route (AC-60).
- **AC-58 (PRIV-8, ticket ALV-115) · the remedy on the screen is the remedy that exists.**
  **Confirmed fact:** `late_rules.py:208-215` skips any Attendance Deduction with
  `docstatus == 1`, in the weekly run and in `run_for_range:251`. The test is driven from
  a fixture where a correction for 4 August is **approved in September, after** the
  deduction was submitted. *Then*:
  (a) the deduction's `docstatus` is still **1** and the Leave Ledger Entry and the
      Additional Salary are **unchanged** — asserted on the documents, not on the screen;
  (b) the sheet's remedy text **agrees with that**, and
  (c) a **static check finds the sentence "the rule follows the attendance record"
      nowhere in the built page** — it was in revision 1 of this spec and it is false.
  **Wave 3 does not add automatic recomputation.** That would let one approval move money
  with nobody involved at all, which is more automation applied to a decision that already
  has too little.
- **AC-59 · the exact words**, translatable, one message each (no sentence built from
  fragments):

  | Block | Exact words |
  |---|---|
  | How it was decided | "This was worked out automatically by the <rule name> rule on <date>. Nobody looked at your week by hand." |
  | If a day is wrong | "If a day in this week is wrong, get it corrected. That puts your attendance record right and it counts for the weeks after it." |
  | What a correction does not do | "**It does not undo this deduction.** Once the rule has worked a week out, it does not work it out again." |
  | Getting it put back | "Only <accountable contact> can cancel a deduction, and only before that month's payslip is finalised. After that it has to be put right in a later payroll run." |
  | Who to go to | "If you think this is wrong, contact <accountable contact>." |

- **AC-60 (PRIV-7) · a person, not a function.** *Given* a rule with a named accountable
  owner, *then* the Late rule tab and the Why? sheet both show that person. *Given* a rule
  with none, *then* they show the fail-closed fallback from §20 D-7 — **never a blank, and
  never a sentence that implies a person reviewed the case.** A static check fails on any
  wording in the sheet that asserts human review of the individual week.
- **AC-61 (PRIV-10) · showing the decision creates no new record about the person.** No
  Wave 3 endpoint writes on a read path; nothing records that the sheet was opened, read
  or closed; no "acknowledged" flag is inferred from a close. Asserted as a static check
  plus a write-count assertion around a full Why? call.

### US-11 · Pay is own-only and gated

- **AC-30 (extended in revision 2)** *Given* a tenant whose `features` list **genuinely
  lacks** `payroll` — not a patched gate — *then* `get_payslips`, `get_payslip` and
  `download_payslip` all refuse when called by hand. Three parts, and the second and third
  are the ones 043 `01c` SEC-2 added:
  (a) the refusal comes from the real `subscription.has_feature`;
  (b) **a static check fails the build if any test in this slice patches `has_feature`,
  `requires_feature` or `enabled_features`** — a patched gate makes every entitlement test
  green while proving nothing, and it has happened in this repository before;
  (c) a **decorator-order** check: `@requires_feature("payroll")` sits **above**
  `@frappe.whitelist()` on all three, matching `get_payslip:1561` and
  `download_payslip:1594`.
- **AC-31 (extended in revision 2)** **Four causes, one message, asserted together in one
  test** so that changing one of them fails: a slip that belongs to somebody else, a slip
  that does not exist, a slip that is still a draft, and **a tenant that did not buy
  payroll**. All four return the byte-identical "That payslip is not available." and the
  same status code, from all three payslip endpoints **and from the Why? endpoint**. A
  refusal that varies tells the caller what the tenant has, or what exists (043 `01c`
  SEC-4).

### US-12 · states

- **AC-32** Skeletons for Time and Pay are in the server-rendered HTML and paint within
  **300 ms**, median of 5, on the W1D-09 rig.
- **AC-33** An empty month renders the calendar with every day in its true state and the
  §9 sentence in the day list — never a blank grid and never a spinner that stops.
- **AC-34** No shift assignment → the §9 sentence, not blank times.
- **AC-35** No late rule covers this person → the tab exists and says so; the statistics
  do not silently show zeros as if the rule were satisfied.
- **AC-36** One card failing leaves the rest of the screen working, with Try again.
- **AC-37** A month outside the caller's rights, a month before joining, a future month
  and `#pay` on a tenant without payroll each show a plain sentence — four separate
  wordings, none of them a raw error.
- **AC-38** `get_time` or `get_pay` failing shows Wave 1's page-error sentence with a code
  that holds no personal data.
- **AC-39** No payslips yet → the §9 sentence, and Expenses is still reachable (W1D-01).

### Cross-cutting

- **AC-40** Every string added is inside `__()`; no sentence is assembled from fragments;
  the rule explanation is one message per rule clause with placeholders, so Hindi and
  Punjabi word order works.
- **AC-41** At 390 px, light and dark, for all personas: no text under 12 px, no target
  under 44 px, no sideways scroll; the month calendar is usable with a thumb; the day
  list scrolls vertically only. The same passes with the Hindi fixture (W1D-12).
- **AC-42** Every whitelisted function in `time_api.py` and `pay_api.py` is in the
  registry test with Guest-refused, wrong-persona and scope cases (Wave 1 SEC-2).
- **AC-43** `time_api.py` and `pay_api.py` contain no `ignore_permissions`, no `global`
  and no module-level mutable state (Wave 1 SEC-6, SEC-15). Where the existing code uses
  `ignore_permissions` after an ownership check — `_own_payslip:1545`, `_deduction_rows`
  — the check is **before** the flag and a test proves the order.
- **AC-44 — rewritten in revision 2; OPS-31 has landed and the old rule is stale.**
  **Confirmed fact**, read in Wave 1's worktree today: OPS-31 shipped as commit `a2439e3`
  on `slice/034-redesign-wave1`, the portal's style and script are now static files under
  `public/css/ess/` and `public/js/ess/`, and markup is pasted in by `ess_part()` — a
  Jinja **global function** registered through Frappe's own `jinja` hook
  (`hooks.py:59`), which reads a file holding no Jinja and **takes no template cache
  slot**. Measured: 12 markup parts render *faster* than one include file (0.1541 s
  against 0.1600 s, 034 notes stretch 4). So **Time and Pay each get their own file in
  `templates/includes/ess/parts/`, and they cost nothing.** What the check must now
  assert:
  (a) Wave 3 adds **no new Jinja include template** — the pinned set stays at the three
  in `test_only_the_pieces_that_need_jinja_are_templates` (`frame.html`,
  `growth-modals.html`, `next/frame.html`), and a fourth fails the test;
  (b) every new part file contains **no `{{` and no `{%`**, or `ess_part()` refuses it at
  run time;
  (c) Wave 3's style and script go into new static files under `public/`, each loaded
  with a `?v=` stamp, which cost no template slot at all.

### The edge cases that bite

- **AC-45** *Mid-month joiner.* Days before `date_of_joining` are not drawn as absent and
  are not counted in any total.
- **AC-46** *Leaver.* A person set to Left mid-month sees their own month up to the day
  their login stops; they appear in nobody's team late list.
- **AC-47** *Half day and hourly leave.* A half-day leave day shows as half leave and half
  worked, and is not an absent day.
- **AC-48** *Back-dated leave.* Leave approved for a day already marked Absent updates
  that day's state on the next load, and the "days marked absent" total moves with it.
- **AC-49** *Night shift across midnight.* A shift ending after midnight does not produce
  an invented 1,080-minute early exit, and an arrival after midnight is not hidden
  (slice 017's two midnight fixes — pinned here because Wave 3 renders them).
- **AC-50** *Regional holiday lists.* Two employees in different stores see their own
  lists; neither sees the other's.
- **AC-51** *Time zone and DST.* "Today" is the site's date. A test with the browser in a
  different time zone still highlights the site's today.
- **AC-52 — rewritten in revision 2, because the version in revision 1 could not be
  built.** **Confirmed fact:** `Shift Type` has **no `company` field**
  (`hrms/hrms/hr/doctype/shift_type/shift_type.json`), so "the caller's company's only"
  has nothing to filter on. An engineer meeting that sentence at 11pm would invent a
  custom field or quietly drop the check. Three things hold whatever §20 D-6 chooses:
  (a) the caller must have an **Active** Employee record, or the call is refused;
  (b) the read carries **no `ignore_permissions`**;
  (c) the list is **not** every Shift Type in the tenant, and a test proves a shift type
  outside the chosen scope is absent.
  **My recommendation for the scope (D-6):** the Shift Types in use in the caller's own
  company through Shift Assignment, plus the caller's own `Employee.default_shift`. A
  fixture with two companies proves company B's night shift does not appear for company
  A's employee. 043 `01c` SEC-7.
- **AC-53** *Cancelled and amended.* A cancelled Salary Slip (`docstatus = 2`) is not
  listed and cannot be downloaded; an amended one is listed once, under its current name.
- **AC-54** *A deduction dated in an already-paid month.* The Why? sheet shows the
  deduction and says which payslip it reached, or says it has not reached one yet —
  never a silent mismatch. `[UNVERIFIED — no demo data exists for this; confirm on the
  bench before the Pay commit]`
- **AC-55** *Leave encashment.* `submit_leave_encashment:1982` sets `leave_period` and
  `currency` server-side and a claim actually saves. A test proves it fails without the
  fix. `[UNVERIFIED — never proven end to end; appendix C F-5]`
- **AC-56** *Concurrent correction.* Two people deciding the same correction: one
  succeeds, the other gets "This one has already been decided.", one
  `alvoraa_reviewed_by` on the document.

---

## 11. Known defects Wave 3 meets, and what it does about each

| # | Defect (appendix C) | State on `dev` at `8718f27` | What Wave 3 does |
|---|---|---|---|
| F-1 | Late minutes from the wrong shift start | **Fixed** (slice 017, `_shift_row:233`) | Renders it, and AC-4 guards the regression |
| F-2 | Leave balance ignores the late rule | **Fixed** (slice 035, `_ledger_leave_balances:88`) | Renders it; AC-14 guards it |
| F-3 | Loss-of-pay amount sent to managers (payload) | **Fixed** (`get_team_late_list:2806`, days only) | AC-16 pins it |
| F-3b | **Corrected in revision 2.** Not the amount — the **leave type**. `build_explanation:37-59` carries days, never `lwp_amount`; `notify:182-205` sends one identical body to the employee and the manager, and that body names the Leave Type the days came from | **NOT fixed** | **D-1** — Wave 3 fixes it, as four rules in AC-17, not as "remove the number". Ticket **ALV-113** |
| F-4 | Payslip PDF uses the generic layout | Unchanged — `default_print_format` unset | Configuration per tenant; release gate 3 |
| F-5 | Leave encashment likely always fails | Unchanged — `leave_period` and `currency` never set (`:1982`) | Fixed; AC-55 |
| F-6 | Old Attendance Request panel still live | Unchanged (`:1943`) | Retired; AC-18, AC-19 |
| F-7 | Rule copy "60 or more" vs code "more than 60" | Code unchanged (`>` at `late_rules.py:75`) | **The words change, not the code** (design correction D5, Q20). AC-12 |
| F-8 | Shift types from every company | Unchanged (`:1880`, `ignore_permissions=True`) | Scoped; AC-52 |
| F-9 | Old calendar assumes Sat/Sun, UTC today | Unchanged (`:1456`) | Retired; AC-18 |
| F-11 | Portal and the weekly job find a rule differently | `_late_rule_for:2710` now checks `covers()` | No change; noted so nobody "fixes" it twice |
| F-12 | Advance status colour map repeats "Paid" | Trivial | Fixed while the panel is touched |
| **New** | `get_payslips:1515` has no `@requires_feature("payroll")` | Live today | Fixed; AC-30 |
| **New** | `get_shift_types:1880` has no company scope **and** no feature gate | Live today | Fixed; AC-52 |
| D-2 caveat | "+₹11,851.61 more than July" is a one-off Diamond Incentive | — | AC-24: name it or drop the line |

---

## 12. Out of scope for Wave 3, and where it goes instead

| Thing | Where it goes |
|---|---|
| Home and Inbox | **Wave 2 (042)** |
| Growth, self-review, goal evidence, Team's look, the staff directory, the person sheet | **Wave 4** |
| Peer feedback | **Wave 4, own go/no-go** (009 design decision 4) |
| "Who is away next two weeks" | **Dropped.** 009 design decision 3 closed Q15 as presence only; a forward-looking leave list is the reason for an absence |
| Salary advance: limit, instalments, approver | **Dropped from Wave 3** (Q19). Instalments need the lending app, which is not installed, or HR-made Additional Salary rows. The existing button keeps today's behaviour behind its existing flag. Revisit with a brief |
| Form 16 | **Dropped.** No source in `hrms`, `erpnext` or `india_compliance`. Could become a document upload later — that is a different feature |
| Expense-claim approvals in the portal | **Dropped** (same as Wave 2). The missing `expense_approver` defect is filed separately |
| Is base ÷ calendar days the right daily wage? | **Not ruled on here** — D-3. Wave 3 shows the method; it does not change it |
| HR's own attendance and payroll screens | Stay in their current look inside the new frame until they are designed (plan §4, "Later") |
| Hindi and Punjabi for users | **Wave 5**; Wave 3 wraps strings and measures in Hindi fixtures only |
| Compression (slice 036) | Its own slice |
| Cached script files (OPS-31) | **Done** — landed in Wave 1 (`a2439e3`). Not a Wave 3 concern any more; AC-44 says what replaces the old rule |

---

## 13. Non-functional requirements for this slice

Measured on "Slow 4G" with a 4× CPU slow-down, cache off (W1D-09).

| What | Number |
|---|---|
| Calls on Time | **1** (`get_time`) beyond the frame's two. Today the page makes about 35–40 queries across several calls (appendix C §E) |
| `get_time` | ≤ **40** queries for a full month, ≤ 700 ms p95 over 20 warm calls. `attendance_correction.month` alone measured 15 queries / 702 ms — that is the number to beat, and the target is **not slower than today** |
| Calls on Pay | **1** (`get_pay`), plus the PDF on demand |
| `get_pay` | ≤ **15** queries, ≤ 500 ms p95 |
| The "why" sheet | ≤ **4** queries, ≤ 400 ms p95 |
| Payslip PDF | wkhtmltopdf costs roughly 1–3 s of CPU in the web worker. **It stays on demand.** No pre-generation and no "download all" — a 400-person tenant would take the worker down. **Measured before the production release** (OPS-W3-6), because production answers **8 requests at a time** (gunicorn, 4 workers × 2 threads, one replica) and payday is the same hour for everyone |
| **Payload size** *(new in revision 2, from OPS-W3-12 — `nfr-budget.md` carries no payload number)* | `get_time` ≤ **40 KB**, `get_pay` ≤ **20 KB**, the Why? sheet ≤ **8 KB**, asserted **in bytes** in the same test as the query count. A 2.5 s phone budget is mostly bytes, and a query count stays honest while a payload quietly grows |
| Query counts asserted, not only times | At **1,000 employees**, for the month calendar, the year table and the payslip lines (OPS-W3-11). 31 days × 5 doctypes is 155 queries if a loop creeps in |
| Skeleton painted | ≤ 300 ms, median of 5 |
| Time usable | ≤ 2.5 s p95 of 20 loads, with slice 036's compression live |
| Every list | capped, with the true total shown; the year table is bounded by the financial year |
| Background work | **None.** If the PDF ever exceeds 3 s at p95 it moves to a background job with a notification — stated now so it is not invented later |
| Record volume assumed | 1,000 employees; 12 slips per person per year; ~212 Attendance Deduction rows per tenant per quarter (the real PP Jewellers figure) |
| Retention | **Nothing new is stored.** Counsel's rule that performance records are kept for employment + 6 months is not engaged; attendance and payroll records keep their existing statutory periods, which this slice does not change |
| Personal or sensitive data | Punch times, absence facts, salary figures — **the most sensitive data in the product**. Own-record only, except a manager's day-level view of their own line through `_subject:251`, and days-only lateness |
| Accessibility | WCAG 2.2 AA; 390 px; 200 % zoom; 12 px floor; 44 px targets |

---

## 14. Data migration and backfill

**Nothing, with one decision that could change it.** No data change, no patch, no
backfill.

**The one thing that could:** §20 D-7. If Surbhi chooses to name the accountable human on
the rule itself, that is **one new field** on `Attendance Deduction Rule` — our own
doctype in the hrms fork, so a JSON field and one `bench migrate`, with **no data
backfill** (existing rules get an empty owner and the fallback wording applies until a
tenant fills it in). If she chooses the tenant-configuration route instead, this section
stays "nothing". Either way, 043 `01c` PRIV-11's check — that Wave 3 stores no new
**personal** record — still holds: a rule owner is a configuration value, not a record
about the employee.

**Two things that are not migrations and must still happen:**

1. **Set each tenant's Salary Slip print format** (F-4). A configuration action per
   tenant, on Surbhi's word on the day, like W1D-21's staff-list tick. Release gate 3.
2. **Seed the demo copy** before testing: more than one deduction that reached pay
   (today 1 of 212 did), some future leave, and attendance after 9 Sep. Without it every
   Pay test passes for the wrong reason (appendix C F-14).

**Rollback:** reverting the Wave 3 commits restores today's Time and Pay panels — **with
one exception worth naming.** AC-18 deletes two endpoints. A revert brings them back, so
rollback is clean, but the deletion commit must be its own commit so the revert is one
step. About ten minutes, like Wave 1's (W1D-10).

---

## 15. Notifications and messages

Wave 3 sends no new notification. It **changes one existing one**.

| Message | Trigger | Recipient | Change | Must never carry |
|---|---|---|---|---|
| Attendance Deduction notification | the weekly job submits a deduction | the employee | none | — (the employee may see their own amount) |
| Attendance Deduction notification | the same | **the manager**, when `notify_manager` is on | **D-1, corrected in revision 2: its own body, its own send.** Today one `sendmail` puts the employee and the manager in one `recipients` list with one body. The manager's body is rebuilt: **days only** | **the leave type** — the real leak, and the one revision 1 missed. Also: no rupee amount, no stored `explanation` text, no punch times, no per-day list. Ticket **ALV-113**; AC-17 |
| "Your payslip is ready" (Wave 2's Inbox row) | a slip is submitted | the employee only | none | **the take-home figure must not appear in any email or push preview** |
| Correction decided | `attendance_correction.decide:743` | the requester | none | another person's reason |

All on-screen messages are in §9's table.

---

## 16. Localisation and accessibility

- Every string in `__()`; the rule explanation is built from whole sentences with
  placeholders, never by joining fragments, because the figures move in word order
  between English, Hindi and Punjabi (AC-40).
- Dates, times and currency through the existing formatter. **Currency comes from the
  slip's own `currency` field**, never assumed.
- Measured at 390 px in light and dark with the Hindi fixture (AC-41).
- **Rahul is a shop-floor worker with no laptop, checking a deduction on his own phone.**
  On a phone: the calendar is thumb-sized; the day sheet is one scroll; the Why? sheet
  leads with the sentence and puts the table below it (the usability test in `01b` §12
  says to change it if people cannot explain the rule in their own words); the PDF opens
  in the phone's own viewer.
- Colour is never the only signal — every chip says its state in words, which is exactly
  why "Late by 12 min (within grace)" is neutral grey **and** says "(within grace)".

---

## 17. Audit and traceability

| What must be reconstructable a year later | How |
|---|---|
| Why a day was corrected, by whom, and when | Attendance Request's `alvoraa_review_status`, `alvoraa_reviewed_by`, `alvoraa_reviewed_on`, `alvoraa_review_note`, plus the submit that wrote the Attendance row. Wave 3 writes through `raise_correction` and `decide` and never sets a status itself |
| Why a deduction happened | Attendance Deduction, its Violation child rows, its Leave Ledger Entry and its Additional Salary — an unusually clean chain, and the reason "Why?" is buildable at all |
| What an employee was shown when they accepted a deduction | **Not recorded, and we are not adding it.** The record is the deduction; the screen is a rendering of it |
| Who read whose month | **Not recorded today.** Wave 1's residual risk R3 owns read-logging; Wave 3 adds no signal and does not pretend to |
| The retired endpoints | The deletion commit is the record; AC-18's test keeps them gone |

---

## 18. Compliance-impact sub-analysis

*The analyst is not a lawyer. Nothing below is a legal ruling, and D-3 explicitly is not.*

### 18.1 Data touched

| Field / object | Sensitivity | Purpose it was collected for | Lawful basis (as recorded) | New collection? |
|---|---|---|---|---|
| Own punch times, per day | **sensitive** — a pattern of arrivals can imply caring duties, health or religious observance | attendance and payroll | employment / statutory | No |
| Own attendance status per day | sensitive | attendance and payroll | employment / statutory | No |
| Own leave balances and past leave **with types** | sensitive — a leave type can imply a medical or family circumstance | leave administration | employment / statutory | No |
| Own salary components, gross, deductions, net | **sensitive** | pay | statutory | No |
| Own loss-of-pay amount and the days behind it | **sensitive** | payroll | statutory | No |
| A report's late **days** | internal | a manager's duty of care | legitimate operational need | No |
| A report's late **amount** | **sensitive** | — | — | **Never shown, and D-1 removes the last place it leaks** |

**Nothing new is collected.** Wave 3 shows data that already exists, to the person it is
about.

### 18.2 Obligations engaged

| Obligation | Source | What this slice must do | Feature that does it |
|---|---|---|---|
| DPDP minimisation | baseline §5 | Fixed payload key lists; days-only for managers | AC-6, AC-16, AC-17 |
| DPDP access rights — a person may see their own record | baseline §4 | Time and Pay are the access path for 400 people who have no desk login | US-1 to US-9 |
| Purpose limitation on absence and pay data | baseline §5 | Own-only for pay; day-level only inside the reporting line | AC-28, AC-30, AC-31 |
| Payroll record accuracy | statutory (⚠ counsel to confirm the Indian requirement) | The figure shown equals the figure paid, read from stored fields | AC-25, §6 |
| Logging duties — no personal content | baseline §5, CERT-In | Refusals logged without names or slip ids | AC-43, Wave 1 PRIV-5 |
| OWASP ASVS 5.0 L2 access control | baseline §4 | Ownership checked **before** any `ignore_permissions` | AC-43 |

**Checked `compliance-feature-map.md` first:** `_own_payslip`'s uniform refusal and
`access.log_refusal` already exist and are reused, not respecified.

### 18.3 Visibility delta

| Who | Can now see | Could they before? |
|---|---|---|
| Rahul | his own true late minutes and the grace that applied | Yes, but wrong — 09:25 read as 25 minutes late |
| Rahul | the days behind a deduction on his payslip | **New on screen**, but it is his own data and the chain already existed |
| Rahul | the late rule's settings in plain words | **New.** It is his employer's policy applied to him — the opposite of a privacy loss |
| Rahul | which of his past leave days the rule took | **New.** Explains a balance he can already see |
| Sandeep | a report's late **amount** | **No — and after D-1 not by email either. Narrower than today** |
| Anyone | a colleague's punch times outside `_subject:251`'s rule | **No** |
| Anyone | a colleague's payslip | **No** — including HR, who uses the desk |
| Anyone | who is booked away in the next two weeks | **No.** The prototype's card is dropped |

**One row gets narrower (the manager's email). Nothing gets wider.**

### 18.4 Decision automation

**A decision about a person is already automated in this product, and Wave 3 is where the
employee finally sees it.** The weekly late-coming job decides that a person loses a
quarter of a day, then half a day of pay. That decision is made by code, on a schedule,
without a human in the loop.

**Revision 2 corrects this section.** Revision 1 recommended telling the employee *"If a
day here is wrong, fix the day first — the rule follows the attendance record."*
**That sentence is false and it is struck.** Verified in
`hrms/hrms/alvoraa_late_rules/late_rules.py:208-215`: a submitted Attendance Deduction is
skipped by every later run, including HR's catch-up `run_for_range:251`. Correcting the
day in September leaves the deduction, and the lost pay, exactly where they are. I would
have had 400 people read a promise the product does not keep. Ticket **ALV-115**; the
replacement wording is AC-59 and the proof is AC-58.

| Question | Answer |
|---|---|
| Accountable human | **Not settled, and "HR" is not an answer.** A function cannot be contacted, held to an answer, or named in a grievance file. **Confirmed fact:** `Attendance Deduction Rule` has no owner field — its fields are `rule_name`, `company`, `shift_type`, `enabled`, the week and violation settings, `deduct_from_leave_first`, `leave_types`, `lwp_salary_component`, `daily_wage_basis`, `exempt_grades`, `notify_employee`, `notify_manager`. §20 D-7 decides where the name lives; AC-60 tests both the named case and the fallback |
| Where they intervene — **before** | Real and genuine: the rule's thresholds, free allowance, exempt grades, leave types and `process_from`. But that is control over **the rule**, not over **this decision about this person** |
| Where they intervene — **during** | **Nowhere.** There is no step between the calculation and the submitted Additional Salary (`_process_week:201-238`, `attendance_deduction.on_submit:63-73`). Whether to add one is Surbhi's call, not mine; §20 D-8. What its absence costs: every contest is after the fact and every remedy is a reversal |
| Where they intervene — **after** | A person can cancel the Attendance Deduction, which cancels the linked Additional Salary (`attendance_deduction.py:175-180`) — **but only while the Salary Slip is unsubmitted.** After the slip is submitted the product has no route back, and it must say so (AC-59) |
| What the employee is told | **This is what Wave 3 adds, and it is the best thing in the slice.** The days, the minutes, which were free, the arithmetic, where the days came from, the settings — **plus** the three things revision 1 left out: that it was automatic, when and under which rule, and who is accountable (AC-57) |
| How they contest it | Correcting a wrong day, **which fixes the record and future weeks and does not undo this deduction**; and a named contact who can cancel it while the slip is open (AC-58, AC-59, AC-60). **There is no recorded, clocked grievance route in the product** — counsel's note of 18 Sep 2026 records it as "not built, handled by hand". Wave 3 must not draw a "contest this" control that leads nowhere |
| Is the system deciding alone? | **Yes, and it was before this slice.** Wave 3 does not make it worse; it makes it visible and, within the limits above, contestable. **It deliberately adds no automation:** no automatic recomputation, no automatic reversal (AC-58) |
| Is it lawful with no human in the loop? | **I do not know, and I am not a lawyer.** Counsel's question 13 of 18 September asked this about the driver scorecard, which is not live. It applies word for word to this rule, which **is** live on a client tenant. §18.6 and 043 `01c` Q5 |

**No AI in this slice.** No rating, no inference, no emotion, voice or facial analysis,
no passive behavioural monitoring, no individual-level surveillance. §18.7 is empty by
construction.

**One prohibition genuinely approached, and refused here in writing:** a per-person
running lateness tally is one design step from a league table. **Wave 3 shows the
employee their own record and shows a manager only days for their own line. No ranking,
no comparison to colleagues, no "most improved", anywhere.** If that is ever asked for,
it needs the baseline read first, not a spec.

### 18.5 Retention and deletion

**Nothing changes, and one gap is now named rather than inherited.** No new record.
Attendance, Attendance Deduction, Leave Ledger Entry and Salary Slip keep the retention
they have — they are statutory payroll records and are decision-bearing, so they survive
an erasure request. That is the existing position, not a new one.

**The gap, stated because revision 1 let it pass silently** (043 `01c` PRIV-11):
counsel's note of 18 Sep 2026 sets periods for performance records and driver location.
**Attendance Deduction is in neither table.** It is decision-bearing about a person's pay,
so it must survive an erasure request under legal hold — and "kept for ever" is what Wave
1 already learned is not a lawful long-term answer. Wave 3 changes nothing here and adds
no second copy of the data. The question goes to counsel with a date (§18.6). **I am not
a lawyer.**

**And nothing records that the employee saw the explanation** (AC-61). "They were shown
it" is a tempting thing to store and it would be a new personal record with no purpose
tag and no retention period.

### 18.6 Open compliance questions

| Question | Who must decide | What it blocks |
|---|---|---|
| Is base pay ÷ calendar days the right daily wage for loss of pay (Q18, D-3)? | Surbhi, with a payroll or legal advisor | Not the build — Wave 3 shows the method either way. It blocks **how confidently the sentence is worded**, and a wrong method shown to 400 people is worse than one shown to nobody |
| Does showing a per-person lateness record to the employee create a record we must retain or disclose differently? | Surbhi, with the security engineer | Nothing; the record already exists, and AC-61 keeps Wave 3 from creating a second one |
| Must a deduction from pay have a human confirmation before it reaches a payslip? | Surbhi, with an advisor | Nothing in Wave 3's build; it would be its own slice. §20 D-8 |
| **What must a worker be told, and able to do, before an automatic deduction reaches their pay under Indian law?** Counsel's question 13 of 18 Sep was asked about the driver scorecard, which is not live. **This rule is live on a client tenant today.** | **Counsel, commissioned by Surbhi** (043 `01c` Q5) | Nothing in the build. It blocks any claim that this feature is compliant, and it is why AC-59's wording is written to be truthful rather than reassuring |
| **What retention period applies to an Attendance Deduction record?** It is in neither of counsel's two tables (§18.5) | **Counsel, commissioned by Surbhi** | Nothing here. It is recorded debt, not a silent assumption |

### 18.7 AI features

**None.** Nothing in this slice is AI-shaped.

---

## 19. Traceability

| Source | ID or line | Story | Acceptance criteria | Status |
|---|---|---|---|---|
| Plan §4 Wave 3 | "calendar and day-by-day list on the fixed late minutes" | US-1, US-2 | AC-1 to AC-5 | covered |
| Plan §4 Wave 3 | "your shift" | US-4 | AC-10, AC-34 | covered |
| Plan §4 Wave 3 | "days off ahead" | US-4 | AC-10 | covered (reuses slice 035) |
| Plan §4 Wave 3 | "who's off (presence only)" | — | — | **dropped** — 009 design decision 3; §21 row (c) |
| Plan §4 Wave 3 | "late rule explained from the real rule fields" | US-5 | AC-12, AC-13 | covered |
| Plan §4 Wave 3 | "corrections and leave from a tapped day" | US-3 | AC-7, AC-8, AC-9 | covered |
| Plan §4 Wave 3 | "retire the old calendar and the old Attendance Request screen" | US-13 | AC-18, AC-19 | covered |
| Plan §4 Wave 3 | "payslip summary" | US-7 | AC-22, AC-23, AC-39 | covered |
| Plan §4 Wave 3 | "why was this deducted, following the real chain" | US-8 | AC-26 to AC-29 | covered |
| Plan §4 Wave 3 | "year to date from stored slip fields" | US-9 | AC-25 | covered |
| Plan §4 Wave 3 | "PDF in the tenant's format" | US-7 | AC-22; release gate 3 | covered |
| Plan §4 Wave 3 | "Wave 0b must be done" | — | §11 | **done** — slices 017 and 035 are on `origin/dev` at `8718f27` |
| Appendix C | T-01 to T-17 | US-1 to US-6, US-13 | AC-1 to AC-19, AC-52 | covered; T-12 dropped |
| Appendix C | P-01 to P-13 | US-7 to US-11 | AC-22 to AC-31 | covered; P-09 (Form 16) and P-10 (advance) dropped |
| Appendix C | F-1 to F-14 | — | §11 | every one placed: fixed, fixed here, or dropped with a reason |
| Design `01b` §7.3 | grace per organisation, true minutes always | US-2, US-5 | AC-4, AC-5, AC-12 | covered |
| Design `01b` §14 item 7 | no hard-coded grace anywhere | US-5 | AC-5, AC-12 | covered |
| Design `01b` §14 item 9 | no screen shows an absence reason | — | §5 negatives, §21 row (c) | covered |
| Design `01b` §14 item 11 | a figure that cannot be trusted says "Needs review" | — | AC-35 (no rule → say so, not zeros) | covered |
| Design `01b` §14 item 12 | every total carries the date its data runs to | US-1 | AC-11 — each total names its month or year | covered |
| Design correction D5 | "Marked absent"; "more than 60 minutes"; CL 8 of 8 | US-1, US-5, US-6 | AC-2, AC-12, AC-14 | covered |
| 009 design decision 3 | who's off: presence only | — | §21 row (c) | covered by dropping the card |
| 009 design decision 7 | "Late by 12 min (within grace)" | US-2 | AC-4 | covered |
| Q-b (14 Sep) | managers learn days, never the amount | US-10 | AC-16, **AC-17** | **AC-17 is new work — the email was never fixed** |
| Q16 | financial or calendar year | US-9 | AC-25 | **closed by the data** — the stored `year_to_date` fields are the payroll year; the late-rule year table uses the same definition |
| Q20 | "60 or more" vs "more than 60" | US-5 | AC-12 | **closed** — the words change, not the code (D5) |
| Q17 | take-home: net or rounded | US-7 | **D-2** | **open** |
| Q18 | base ÷ calendar days | — | **D-3** | **open — payroll/legal, not ruled on here** |
| Q19 | advance limit, instalments, approver | — | §12 | **dropped from Wave 3** |
| W1D-01 | Pay without payroll | US-11 | AC-30, AC-39 | covered |
| W1D-09 | the measurement rig | — | AC-32, §13 | covered |
| Wave 1 SEC-2, SEC-6, SEC-15 | endpoints safe on their own | — | AC-42, AC-43 | covered |
| Wave 1 SEC-12 | fixed payload key list | US-12 | AC-6 | covered |
| DevOps OPS-31 | cached script files | — | AC-44 | **closed** — landed in Wave 1 (`a2439e3`); AC-44 rewritten to the `ess_part()` rule |
| 043 `01c` SEC-2 | the real feature gate, no patched gate, decorator order | US-11 | AC-30 | covered |
| 043 `01c` SEC-3 | fixed key list extended to `get_payslips` | US-12 | AC-6 | covered |
| 043 `01c` SEC-4 | four refusal causes, one message, incl. the Why? endpoint | US-11 | AC-31 | covered |
| 043 `01c` SEC-7 | `get_shift_types`: Active Employee, no `ignore_permissions`, real scope | — | AC-52, **D-6** | covered; the scope half needs D-6 |
| 043 `01c` SEC-8 | the email: separate bodies, separate sends, days only, no leave type | US-10 | AC-17 | covered — **ALV-113** |
| 043 `01c` SEC-5 | `_deduction_rows` stops taking a raw filters dict | US-8 | AC-43 (ordering), and the handoff note | covered |
| 043 `01c` SEC-11 | the two retired endpoints leave the whitelist, with a call-by-hand test | US-13 | AC-18, AC-19 | covered |
| 043 `01c` PRIV-6 | the sheet says it was automatic, when, which rule, who | US-8 | AC-57 | covered |
| 043 `01c` PRIV-7 | a named human, with a fail-closed fallback | US-8 | AC-60, **D-7** | covered; the source of the name needs D-7 |
| 043 `01c` PRIV-8 | the remedy on screen is the remedy that exists | US-8 | AC-58, AC-59 | covered — **ALV-115** |
| 043 `01c` PRIV-9 | a contest has a route and a recipient, or no control claims one | US-8 | AC-59, AC-60 | covered |
| 043 `01c` PRIV-10 | showing the decision creates no new record | US-8 | AC-61 | covered |
| 043 `01c` PRIV-11 | Attendance Deduction retention is a named gap, not an inherited answer | — | §18.5, §18.6 | **recorded, open with counsel** |
| DevOps OPS-W3-6 | the payslip PDF is measured before production | — | §13, release gates | **open — a release gate, not an AC** |
| Prototype | Days, Leave, Late rule tabs; Pay hero, explain strip, YTD, payslip list | US-1 to US-9 | as above | covered, with §21's differences |

**Gaps, listed rather than hidden:** the take-home figure (D-2); the daily-wage method
(D-3); the shift-type scope (D-6); where the accountable human's name lives (D-7);
AC-54 and AC-55 are `[UNVERIFIED]` and need one bench run; counsel's two questions
(§18.6) are open and neither blocks the build.

---

## 20. Needs a decision

**Eight, and only two of them stop a commit.** The Blocks column says which. Everything
not marked "blocks" can be answered while the build runs, because each has a fail-closed
default written into an acceptance check.

| # | Question | My recommendation | Blocks? |
|---|---|---|---|
| **D-1** | **The manager's deduction email.** Corrected in revision 2: it leaks the **leave type**, not the amount (§11 F-3b). Fix it in Wave 3 — and is `notify_manager` left on, on the two client tenants, until the fix ships? | **Fix it in Wave 3, in its own commit, before the panels**, as AC-17's four rules. It is one function and independent of every screen. **And turn `notify_manager` off on both client tenants in the meantime** — a one-tick mitigation available today, for a leak that cannot be un-sent. Ticket **ALV-113** | No — it is a defect fix. The interim tick is a same-day action |
| **D-2** | **"Take-home" — net pay (₹44,051.61) or the rounded amount paid (₹44,052)?** (Q17) | **The rounded amount**, with the exact net in the breakdown below. It is the figure the employee can check against their bank. Wave 2's "your payslip is ready" row must use the same choice, or the two screens disagree by a rupee | While building |
| **D-3** | **Is base pay ÷ calendar days the right daily wage?** (Q18) **No agent on this team is qualified to answer it.** | **Get a payroll or legal view before the Pay screen ships.** If the answer is slow, ship the Why? sheet **without** the arithmetic line and with the outcome only, then add the line when the method is confirmed. AC-57 element 4 is written so the sheet is complete without it | Blocks **one line** of the Why? sheet, not the sheet |
| **D-4** | **"More than July · +₹11,851.61"** reads as a raise; it was a one-off Diamond Incentive | **Drop the comparison for v1.** There is no field that says what is one-off, and a wrong "you earned more" line on a payslip is what people screenshot | While building |
| **D-5** | ~~OPS-31 before Wave 3~~ | **Closed by Wave 1.** OPS-31 landed as `a2439e3`; markup parts cost no template slot, so Time and Pay each get their own file for free. See AC-44. **What replaces it is not a decision but a condition:** Wave 3's panels sit on Wave 1 reaching `dev`, and OPS-31 must not reach **production** until ALV-112's asset refresh is on `main` (OPS-W3-2) | Closed |
| **D-6** | **How is `get_shift_types` scoped, given Shift Type has no `company` field?** (043 `01c` Q3) | **The Shift Types in use in the caller's own company through Shift Assignment, plus the caller's own `default_shift`.** Until it is answered, build the two parts that need no ruling — require an Active Employee record and drop `ignore_permissions` — which removes the worst of it | Blocks the **scope half** of AC-52, not the endpoint fix |
| **D-7** | **Where does the accountable human's name live?** **Confirmed fact:** `Attendance Deduction Rule` has no owner field. "HR" is a function and cannot be contacted or held to an answer (043 `01c` PRIV-7) | **One new field on the rule** — `Attendance Deduction Rule` is our own doctype, so it is a JSON field and one `bench migrate`, no backfill (§14). The alternative, a tenant-wide setting, is cheaper but names one person for every rule in the tenant. **Until answered: AC-60's fallback** — say plainly that it was automatic and give the tenant's HR contact, never a blank and never a hint that someone reviewed the case. `[UNVERIFIED — I found no per-site "HR contact" setting; the engineer must confirm what the fallback reads]` | Blocks the **last block** of the Why? sheet |
| **D-8** | **Should a deduction need a person's confirmation before it reaches a payslip?** Today there is no step at all between the calculation and the submitted Additional Salary | **Not in Wave 3.** It is a product and payroll change with a real cost, and the transparency this slice ships is worth having either way. **I recommend it as its own slice**, and I would rank it above a new feature. Related: should a correction approved *after* a submitted deduction raise a flag for a person to look at (option B in 043 `01c` Q1)? My recommendation is **yes, in Wave 4** — it closes the loop without letting an approval move money by itself | No |

**Not decisions, stated so they are not mistaken for one:** `get_payslips:1515`'s missing
feature gate (**P1** — it makes W1D-01's entitlement claim false), its full-Employee-row
payload, `get_shift_types:1880`'s `ignore_permissions` and missing caller check (**P3**),
and the manager's email body (**P2**) are **defects**. They are fixed in this slice by
AC-30, AC-6, AC-52 and AC-17 and need no ruling. **The order 043 `01c` ranks them in:**
the payroll gate first, the email second, the shift types third.

---

## 21. Differences from the approved prototype

The prototype is a review artifact and **is not changed**; this is the record.

| # | Prototype | Built | Why |
|---|---|---|---|
| a | Pay and Time say "drawn for Rahul in this prototype" for managers and the owner | Every person gets their own Time and Pay | A prototype limitation, not a design |
| b | "Take-home ₹44,052" (rounded) on the hero, "net" elsewhere | Per D-2 | Q17 was never answered |
| c | Time · Leave shows "Who is away · next two weeks" with a Sample tag | **Not built** | 009 design decision 3: presence only. A forward-looking list of who is booked away is approved leave, which **is** the reason for the absence |
| d | "+₹11,851.61 More than July" as a plain green figure | Per D-4 — recommended: dropped | It was a one-off incentive (appendix C P-02) |
| e | "Form 16 · FY 2026–27" with a Sample "Planned" tag | **Not built, and not shown as planned** | No data source anywhere. A "Planned" row on a payslip page is a promise |
| f | Salary advance with a limit and 1–3 month repayment, tagged Sample | **Not built** | No repayment field; instalments need the lending app (§12) |
| g | Late rule card says "more than 60 minutes" | Kept — and the **60 comes from the record**, not the copy | D5 and Q20 chose the words over the code; AC-12 proves the number moves with the rule |
| h | The day list's grace uses a 15-minute figure | Kept as a **fixture value**; the built screen reads the Shift Type or the org default | `01b` assumption: 15 is illustrative |
| i | "Why ₹548 was deducted" sheet shows "₹34,000 base ÷ 31 days ÷ 2" | Per D-3 | The method is not confirmed |
| j | Month calendar starts Monday | Kept, and the **week-start day comes from the rule record** where the late rule is concerned (`week_start_day`) | The calendar's first column and the rule's week are two different things, and the prototype uses one number for both |

---

## 22. Ready check

| Box | State |
|---|---|
| Brief approved | ✓ — the 009 plan (Wave 3) and the decisions stand in for `01` |
| Clickable prototype reviewed | ✓ 22 Sep, with §21's ten differences recorded |
| `01c` security and privacy written | ✓ — revision 1, 2026-09-24. Its five spec changes and two check extensions are applied in this revision |
| `07` DevOps inputs written | ✓ — 2026-09-24, `OPS-W3-1` to `OPS-W3-19`. Its Jinja-cliff item is now moot (OPS-31 landed); the PDF measurement (OPS-W3-6) is a release gate |
| Every state designed and specified per persona | ✓ §9 |
| Gap analysis verified in source | ✓ §3, with file and line |
| Stories: personas, sized, "must not" stories | ✓ §7 — US-10, US-11 and US-12 are the "must not" stories |
| Every story has checks with observable oracles | ✓ §10 |
| Traceability complete | ✓ §19, with the gaps listed |
| Permission matrix with negatives | ✓ §5 |
| Edge cases | ✓ AC-45 to AC-56 |
| NFR numbers | ✓ §13 |
| Migration stated | ✓ none (§14), with two configuration actions named |
| Compliance sub-analysis | ✓ §18 — including the one place this product already automates a decision about a person |
| No prohibited capability | ✓ nothing AI-shaped; the one prohibition approached (a lateness ranking) is refused in writing in §18.4 |
| Open questions owned, none blocks day 1 | **Partly** — nothing blocks the **first** commit any more. D-6 blocks half of one endpoint's check and D-7 blocks the last block of the Why? sheet; both have fail-closed defaults so the build starts without them |
| Frappe details verified in source | **Partly** — AC-54 and AC-55 are `[UNVERIFIED]` and need one bench run before the Pay commit; AC-60's fallback source is `[UNVERIFIED]` |
| The remedy told to the employee is true | ✓ — **fixed in revision 2.** AC-58 pins it to the code's behaviour; the false sentence is struck and a static check keeps it out (ALV-115) |

**Verdict, plainly: ready to start, not ready to finish.** Revision 2 closes the two
blockers revision 1 had. What is left is real but small: **D-6** and **D-7** each have a
fail-closed default, so the engineer can build past them; **D-3** holds one line of the
Why? sheet; and two questions belong to counsel and block no code.

**The order I would build in:** the payroll gate on `get_payslips` (P1, one line), then
the email fix (ALV-113, one function, its own commit), then the server side, then the
panels once Wave 1 is on `dev`.

---

## Open questions

| # | Question | Owner | Blocks | Can the build start without it? |
|---|---|---|---|---|
| 1 | D-1 — ship the email fix (ALV-113), and turn `notify_manager` off meanwhile | Surbhi | A live leak; one function | Yes — it is its own commit |
| 2 | D-5/Q1 — the remedy wording (ALV-115). My recommendation is written into AC-59 | Surbhi | The last section of the Why? sheet | Yes — AC-59 is the fail-closed default |
| 3 | D-6 — how `get_shift_types` is scoped | Surbhi, with the engineer | The scope half of AC-52 | Yes |
| 4 | D-7 — where the accountable human's name lives | Surbhi | The last block of the Why? sheet | Yes — AC-60's fallback |
| 5 | D-3 — base ÷ calendar days | Surbhi, **with a payroll or legal advisor** | One line of the Why? sheet | Yes |
| 6 | D-2 — take-home: net or rounded | Surbhi | One number on Pay, and Wave 2's row must match | Yes |
| 7 | D-4 — the "more than July" comparison | Surbhi | One card | Yes |
| 8 | D-8 — a human step before a deduction reaches pay | Surbhi, with an advisor | Nothing here; its own slice | Yes |
| 9 | Counsel's two: lawfulness of an automatic wage deduction, and Attendance Deduction retention | **Counsel, commissioned by Surbhi** | No code. It blocks any compliance claim | Yes |

## Assumptions

- `[ASSUMPTION]` `attendance_correction.month:360` can carry `Holiday.weekly_off` without
  a second query — the holiday rows are already read. Confirm before the calendar commit.
- `[ASSUMPTION]` Salary Detail's `additional_salary` link is populated on every deduction
  line that came from an Additional Salary. Confirmed for Rahul's one real case
  (HR-ADS-26-09-00001); **one real case is not a rule** — confirm on the bench.
- `[ASSUMPTION]` Frappe HR's `year_to_date` on Salary Slip is the payroll/fiscal year, so
  Q16 is settled by the data rather than by a choice. Confirm on the bench.
- `[ASSUMPTION]` `frappe.get_meta("Salary Slip").default_print_format` is per site, so
  each tenant sets its own. Confirm before release gate 3.
- `[ASSUMPTION]` Deleting `get_attendance_calendar` and `submit_attendance_request`
  breaks no external caller. **Checked:** the only references in the repository are
  `hrms-employee.html:7128` and `:7965`. Re-check on the day, because the mobile app
  (slice 013) is on a separate work line.
- `[ASSUMPTION — replaces revision 1's stale one]` **The Jinja template cliff no longer
  constrains this slice.** OPS-31 landed in Wave 1 (`a2439e3`), markup moved to
  `ess_part()` files that take no template slot, and 12 parts measured faster than one
  include file. So Time and Pay each get their own markup, style and script file for
  free, and revision 1's "no new include file before OPS-31" is withdrawn (AC-44).
  **What remains true and is a condition, not an assumption:** Wave 1 must reach `dev`
  first — `a2439e3` is on `slice/034-redesign-wave1`, **not** on `origin/dev` — and
  OPS-31 must not reach production before ALV-112's asset refresh is on `main`
  (OPS-W3-2).
- `[ASSUMPTION]` The fallback contact in AC-60 can be read from existing tenant
  configuration. **I could not verify this** — I found no per-site "HR contact" setting.
  `[UNVERIFIED — engineer to confirm]`, and D-7 may make it moot.
- **Confirmed fact, not an assumption:** slices 017 and 035 are on `origin/dev` at
  `8718f27` — `attendance_analytics._shift_row` and `hr_api._ledger_leave_balances` both
  present. Wave 3's numbers depend on it.

## Release gates (not acceptance checks)

1. Compression (slice 036) live before Time and Pay reach a tenant — they are the two
   heaviest screens in the portal.
2. The deletion of the two old endpoints (AC-18) ships in **its own commit**, so a
   rollback is one step.
3. **Each tenant's Salary Slip print format is set** before the Pay screen is shown to
   that tenant's people (F-4). A tenant configuration change, on Surbhi's word on the day.
4. **D-1's email change and the release note go together.** A manager who has been
   receiving one body stops receiving it; that is a narrowing and HR should be told, not
   surprised. **Two DevOps points belong with it:** prove the fix on dev with one
   deliberate send, because production email is muted until go-live (OPS-W3-10); and say
   on release day that **an image rollback restores the old email** — check the template
   after any rollback (OPS-W3-9).
6. **Measure the payslip PDF before the production release** (OPS-W3-6): 20 warm calls
   for p95, and 10 concurrent downloads. Production's web tier answers **8 requests at a
   time**, and payday is the same hour for a whole tenant. If p95 is over 3 s, or an
   ordinary request misses its 500 ms budget under that load, the PDF moves to the
   `short` queue with a notification. **No pre-generation and no "download all"**, now or
   later (OPS-W3-7).
7. **Wave 3's panels wait for Wave 1 to reach `dev`**, and OPS-31 must not reach
   **production** until ALV-112's asset refresh is on `main` and one deploy has proved it
   (OPS-W3-2). Otherwise production runs the new HTML against August's script and nothing
   on screen says so.
5. Demo data seeded on the local copy before the test run (§14), or every Pay test passes
   for the wrong reason.

## Handoff note

**To the security and privacy engineer:** this slice needs its own `01c`, and three
things deserve your eye first. **D-1** — the manager's email is a decided rule that is
still open in the one place nobody looked. **AC-43's ordering rule** — `_own_payslip` and
`_deduction_rows` both use `ignore_permissions` **after** an ownership check, and the test
must prove the order, not the presence. **§18.4** — the late-coming rule is an automated
decision about a person, and Wave 3 is the first time the employee sees how it was made;
please read that section as a requirement, not as background.

**To the DevOps engineer:** your `07` landed and is applied. D-5 is closed by OPS-31. The
payslip PDF is the live one — 1–3 s of wkhtmltopdf in the web worker against 8 request
slots, measured before the production release (OPS-W3-6), on demand only, no
pre-generation, no bulk download. The other two that reach you: proving the deployed
assets are the ones just built, and that a rollback restores the old deduction email.

**To the fullstack engineer:** the two most likely things to be quietly lost are the two
`01b` called out: **no hard-coded grace anywhere** (AC-5 and AC-12 both have static
checks, because this is easy to build the old way) and **the year-to-date figure must
never be a sum of slips** (AC-25 fails if it is). Build the "one total, one list" rule in
§6 before any card, not after.

**To the test engineer — four tests here are easy to write so that they prove nothing,
and one of them already was.** `AC-17` must assert on the **rendered body per
recipient**, with a Sick Leave fixture: the revision 1 version tested for a rupee amount
that was never there, so it would have gone green while the leak carried on. `AC-30`'s
gate test must call the real `has_feature` and must not patch it. `AC-31` must compare
**all four** refusal causes in one assertion. And `AC-58` must be driven from a
correction approved **after** the deduction was submitted, asserting on the deduction's
`docstatus` — written the other way round it passes and proves the opposite.

**To the test engineer:** AC-4's four punches are the regression guard for slice 017's
fix and are the single most valuable test in this slice — a 09:25 punch on a 09:30 shift
must read **0**. AC-12 needs **two** rule fixtures with different values, or it proves
nothing. AC-25 must fail when the code sums slips, so write the failing version first.
