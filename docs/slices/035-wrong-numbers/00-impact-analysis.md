---
slice: 035-wrong-numbers
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-09-22
status: waiting for approval — no code written
inputs: [docs/slices/009-ess-portal-redesign/00-assessment-and-plan.md (Wave 0b, W2–W5, W7), appendix-b-home-inbox.md (E1–E4), appendix-c-time-pay.md (F-2, F-4, P-08), appendix-d-growth-team-people.md (B16, B17, B19), docs/slices/017-late-minutes/, decisions Q-e (14 Sep) and 00f (22 Sep, uncommitted in slice 034's worktree)]
---

# Slice 035 — the remaining wrong numbers (Wave 0b). Impact analysis and strategy

Wave 0b of slice 009, minus late minutes (W1, fixed in slice 017) and the org-chart
manager (W6, a data fix for HR). Branch `slice/035-wrong-numbers`, worktree
`.claude/worktrees/035-wrong-numbers`, cut from `origin/dev` at `1c4e84c`.

**Nothing here is built.** Every number below was measured read-only on `ppj.localhost`
on 22 Sep 2026 (SELECTs and read-only Python through stdin, each ending in a rollback).
Nothing was written to any site. No test run, no migrate, no `docker cp`.

There is no `02-functional-spec.md` for this slice. Slice 017 went the same way: the
assessment, its appendices and the decisions stand in for the brief. If you want a spec
first, say so and the business analyst writes one from this document.

---

## 0. The short answer

| # | Figure | What is wrong | Money or a decision wrong? | Rows that change on PPJ |
|---|---|---|---|---|
| W2 | **Leave left** | Ignores the days the late-coming rule took. Home also drops "of 8" and hides a fully used type | **Display only.** Pay and the leave gate use Frappe HR's ledger, which is right. But the employee plans leave on the wrong number, and the same form contradicts itself | **97 of 403 employees**, all Casual Leave, **76 days** overstated. Rahul: 3 → 0 |
| W3 | **Holidays** | Home lists every holiday in every list on the site, not the employee's own. Also stops at 31 December | **Display, but it drives a decision.** A store employee is told Diwali (8 Nov), Dussehra, Guru Nanak Jayanti and Christmas are holidays. They are Head Office holidays only. Someone who stays home is marked absent, and absence cuts pay | **363 of 403** see 4 holidays that are not theirs. **All 403** miss 26 Jan and 23 Mar until January |
| W3b | **Holidays, the source** (new) | The portal reads `Employee.holiday_list`. Frappe HR v16 pay and leave read **Holiday List Assignment**. Nothing keeps them in step | Not wrong on PPJ today. **Likely wrong on a fresh tenant** and on PPJ from 1 April 2027 | 0 today on PPJ (403 of 403 agree). `dtc` and `aahr`: **not checked** — I have no access, and should not have |
| W4 | **"Team this week"** | Wrong people, everyone judged by the viewer's weekly off, and nobody ever "in" today | **Display only.** Nothing reads it. It does show peers the presence of people in other cities | **359 non-managers** see a department list (Rahul: 40 people, **34 in other cities**). **282 of 402** reports have a different weekly off from their manager |
| W5 | **Goal percentages** | Averages mix Q1 and Q2. Manager team list counts 83 Q1 goals still marked Active. Team reviews with no cycle pick the oldest | **Display only.** The appraisal's own goal score is per cycle and weighted — correct. But managers rate in October with the wrong comparison chart in front of them | **210 of 213** employees with goals. Inflated by **13 points on average, up to 50** |
| W7 | **Payslip** | The PDF uses Frappe's generic layout. PPJ's own format exists but is not the default, and exists **only in PPJ's database** — the real clients have nothing | **The amounts are right. The document is not.** 555 of 800 slips print a rounded "Net Pay" and words that differ from the bank transfer by up to 50 paise. The generic PDF shows internal fields and "Professional Tax ₹0.00" | **All 800** PDFs change layout. **555** differ between printed net and paid net |

**No wrong number reaches money.** Every pay and leave calculation reads Frappe HR's own
data (the leave ledger, holiday assignments, per-cycle goals). What is wrong is what
people are **told** — and on holidays and payslips, what they are told can lead them
to act, or can be held up as a statutory document.

---

## 1. W2 — Leave left

### What the screen shows, and what it should

| Screen | Endpoint | Shows today | Should show |
|---|---|---|---|
| Home, "Leave" card | `hr_api.get_employee_dashboard` | Rahul CL **3**, no "of 8" | **0 of 8** |
| Leave page, rings | `hr_api.get_leave_summary` | CL 3 left, "5 / 8 used" | 0 left, "8 / 8 used" |
| Apply-leave drop-down | `get_leave_summary` (page line 7229) | "Casual Leave (3 days left)" | "(0 days left)" |
| Apply-leave preview | `hr_api.preview_leave_request` | **0** — already uses Frappe HR's ledger | unchanged |
| Manager: report's scorecard | `hr_api.get_employee_scorecard` | taken 5 / allocated 8 | 8 / 8 |
| Manager: report's detail | `hr_api.get_employee_detail_for_manager` | 3 of 8 | 0 of 8 |
| HR: leave on someone's behalf | `get_leave_summary(employee_id)` | 3 | 0 |
| Leadership: leave used % | `org_figures.py` :303 | 5 of 8,045 days used | 81 of 8,045 (see §1.5) |

So the same apply-leave form tells Rahul "3 days left" in the drop-down and "0" in
the preview. That contradiction is what an employee sees first.

### Cause

Four endpoints each work out the balance themselves: *allocated minus approved Leave
Applications since the start of the financial year*. That misses every other kind of
entry in Frappe HR's **leave ledger** (the running record of every leave added or used):
late-rule deductions, encashments, expiries and carry-forwards. On PPJ the ledger holds:

| Ledger entry type | Rows | Days |
|---|---|---|
| Leave Allocation | 1,209 | +8,045 |
| Attendance Deduction (the late rule) | 212 | **−76** |
| Leave Application | 3 | −5 |

Frappe HR already has the right answer: `get_leave_balance_on` and
`get_leave_details` (`hrms/hr/doctype/leave_application/leave_application.py`
:1005, :1046). The late rule itself uses `get_leave_balance_on` before taking leave
(`attendance_deduction.py` :83). The preview uses it too. Only the four screens don't.

**Home has a second, separate bug (E2, confirmed):** the page reads `b.total_leaves`
(`hrms-employee.html` :6566, :6572), the server sends `total`. So "of 8" never
appears, and the filter "hide a type with nothing allocated" hides any type whose
balance is 0. **Fixing the balance without this line makes Home worse:** Rahul's Casual
Leave would vanish from Home instead of showing 0.

### Measured on PPJ

I ran both calculations for every active employee and leave type (1,209 rows):

- **97 rows differ. All 97 overstate. All are Casual Leave.** 97 employees.
- **76 days overstated in total** — exactly the 76 days of late-rule deductions.
- Rahul Kumar (PPJ-0058): portal 3, ledger 0. The only employee at 0.
- Nobody is understated.

### Money or decision?

**Money: no.** The leave gate (`LeaveApplication.validate_balance_leaves`), the late
rule and leave encashment all read the ledger. Casual Leave does not allow a negative
balance on PPJ, so an employee cannot actually take leave they don't have.

**Decisions: yes, small.** An employee plans leave on "3 left" and is refused. A manager
sees "3 of 8" on a scorecard. And next week's late deduction will go to **loss of pay**
because the ledger is at 0, while the screen still says 3 — the employee sees money
taken "although I had leave".

Decision **Q-e (14 Sep)** already settles the rule: *leave left comes from Frappe HR's
ledger, including late-rule days.* Assessment correction **D5** says the same: "Casual
Leave 8 of 8 used (not 5 of 8)".

### Fix

1. One new private helper in `hr_api.py`, `_ledger_leave_balances(employee, date)`,
   returning per leave type: `total`, `taken`, `pending`, `balance` — computed by
   Frappe HR's own functions (`get_leave_allocation_records`, `get_leaves_for_period`,
   `get_leaves_pending_approval_for_period`, `get_remaining_leaves` and the two expiry
   helpers), in the same way `get_leave_details` combines them.
2. The four endpoints call it instead of their own sums. Their output keys stay the
   same, so the page needs no change except the next line.
3. Home: `loadHomeLeave` reads `b.total` (two lines in the page).

**Why not call `get_leave_details` directly?** It starts with `validate_leave_access`,
which refuses anyone who is not the employee, their named leave approver, or holder of
desk read on Employee. A manager who is the `reports_to` but not the named
`leave_approver`, or a store HR person with branch-scoped permissions, would get a
permission error on a screen that works today. The portal already checks who may see
whom before it reaches this code (`get_effective_manager`, `_hr_target_employee`). So
the helper calls the lower Frappe HR functions, which do no permission check of their
own. That copies about 12 lines of `get_leave_balance_on`'s shape — **intentional
trade-off**, pinned by a test that compares the helper with `get_leave_balance_on` for
the same employee, so an upstream change breaks CI rather than the screen.

### 1.5 Leadership's "leave used %" (not in this slice — slice 012's file)

`org_figures.py` :303 has the same blind spot: it counts only Leave Applications. On
PPJ it says 5 of 8,045 days used; the ledger says 81. It is an aggregate, not a
person's balance, and the file is slice 012's. **I recommend a follow-up in 012's lane**,
after you confirm late-rule days count as "used" for leadership too (Q-e reads that
way). I will not touch it here.

---

## 2. W3 — Holidays

### What the screen shows, and what it should

**Home, "Upcoming holidays" card** (`get_employee_dashboard` :250–269). Rahul, on the
Chandigarh store list (Thursday off), is shown:

| Date | Holiday | On Rahul's list? |
|---|---|---|
| 2 Oct | Gandhi Jayanti | yes |
| **20 Oct** | **Dussehra** | **no — Head Office only** |
| **8 Nov** | **Diwali** | **no — Head Office only** |
| 9 Nov | Diwali next day (store closed for stock-take) | yes |
| **24 Nov** | **Guru Nanak Jayanti** | **no — Head Office only** |
| **25 Dec** | **Christmas** | **no — Head Office only** |
| 26 Jan, 23 Mar | Republic Day, Holi | yes — **but hidden until January** |

For a jewellery store, Diwali is the busiest day of the year. Telling store staff it is
a holiday is the most damaging wrong number in this slice.

### Cause

The query reads the `Holiday` table with **no `parent` filter** — every list on the
site, every company — then removes duplicate dates. It also stops at 31 December,
while PPJ's lists run April to March. The Time calendar (`get_attendance_calendar`),
the correction screen (`attendance_correction` :423) and "team this week"
(`_holiday_dates`) do filter by the employee's list. Only Home doesn't.

On a tenant with several companies, Home would also show **other companies'**
holidays. That is not personal data, but it is another company's data.

### 2b. A second cause nobody listed: two holiday sources that drift apart

This Frappe HR (v16.33 / hrms 17-dev) works out an employee's holidays from **Holiday
List Assignment** records (`hrms/utils/holiday_list.py` :96,
`get_holiday_list_for_employee`). Payroll working days, leave day counts and
auto-attendance all use it. **The portal reads the older `Employee.holiday_list`
field instead**, in four places. Nothing copies one to the other: saving an assignment
does not set the field, and setting the field on the Employee form (still editable)
does not create an assignment.

| Where | PPJ today | When it breaks |
|---|---|---|
| PPJ | 403 of 403 agree — a v16 patch created the assignments from the field | **1 April 2027**: HR creates the new year's lists and assignments; the field still points at this year's list. The portal shows no holidays and no weekly offs from then on |
| A fresh tenant (`dtc`, `aahr`) | **Not checked** | If HR sets only the Employee field, payroll refuses to run ("No Holiday List was found"). If HR sets only assignments, the portal shows no holidays at all |

**Money:** the portal's holidays feed nothing. **Decision:** an employee who trusts the
portal's calendar over the one payroll uses can be marked absent.

### Measured on PPJ

- **363 of 403** employees (every store list) see 4 holidays that are not theirs.
  The 40 Head Office staff see the right set.
- **All 403** miss 26 Jan and 23 Mar until the calendar turns.
- 21 holiday lists, 5 named holidays each for stores, 10 for Head Office.

### Fix

- **B1 (Home card):** the employee's own list only, resolved the Frappe HR way, named
  holidays only (no weekly offs), from the start of this month to the end of that
  list's period. Frappe HR ships the shape: `hrms.hr.utils.get_holidays_for_employee`
  (`only_non_weekly=True`). The window depends on **Q16** (financial or calendar
  year) — see the questions.
- **B2 (all portal holiday reads):** one helper that resolves an employee's holidays
  for a date range through Holiday List Assignment, falling back to the company's
  assignment, then to `Employee.holiday_list`. For one person, Frappe HR's
  `get_holiday_dates_between_range`; for a team, the batch helper
  `get_assigned_holiday_lists_to_employee_and_company`, which Frappe HR's own Monthly
  Attendance Sheet uses — one query for everyone, not one per person. Callers:
  `get_employee_dashboard`, `get_attendance_calendar`, `_holiday_dates` /
  `get_week_presence`, `attendance_correction` :423.

**The fallback to the Employee field is deliberate**, not a shim: a tenant set up by
hand may have only the field. It keeps today's behaviour where assignments are missing.

---

## 3. W4 — "Team this week"

### What the screen shows, and what it should

`hr_api.get_week_presence` (:3117), drawn on Home by `loadHomeWeek` (page :6583).

| Problem | Today | Should |
|---|---|---|
| **Who** — someone with no reports | The first 40 people in their **department**, alphabetically, across all stores. Rahul: 40 people, **34 in other cities** (13 Ambala, 8 Noida, 8 South Extension, 5 Karol Bagh, 6 his own store) | The people they work with — **Q7 is open**: same manager, or same department **and** branch |
| **Weekly offs** | Everyone judged by the **viewer's** holiday list. Rahul's Thursday is marked "off" for all 40; 38 of them are off on a different day | Each person's own list |
| **What an "off" day looks like** | A colleague's real weekly off in the past shows as **"away"** — which reads as absent | "off" |
| **Today** | Built only from Attendance. PPJ marks attendance automatically **after the shift ends**, so during the day nobody is ever "in" | "in" once they have checked in today |
| **Week start** | Sunday (System Settings `first_day_of_week` is blank) | Monday is usual for Indian retail — your call, one setting, not code |

### Measured on PPJ

- **359** of 403 employees have no reports, so they get the department view.
  Sales alone is 207 people across 5 branches.
- **44** managers. **282 of 402** reports have a different holiday list from their
  manager, so a manager sees their weekly offs wrong.
- Demo check-ins stop on 11 Sep, so "never in today" cannot be seen in data. It
  follows from the code and from `enable_auto_attendance` on both shift types.

### Money or decision?

**Display only.** Nothing else reads it. But the department view shows a peer the
daily presence of up to 39 colleagues in other cities, with false "away" days. Fixing
it **narrows** what peers see. Decision 3 (22 Sep) — "presence only" — is already how
it works, and stays.

### Fix

Server: pick the group by Q7; batch each person's holidays (B2's helper); read today's
first check-in in one query (`Employee Checkin`, `log_type = "IN"`, time today, for the
listed people). Page: one line — the title reads "Your team this week" or "Your
department this week"; a same-manager group needs its own honest words ("People you
work with this week"). **Needs Q7.**

---

## 4. W5 — Goal percentages

### What the screen shows, and what it should

| Screen | Endpoint | Today | Should |
|---|---|---|---|
| Manager, team comparison chart ("goals" bar) | `hr_api.get_team_scorecard` :992 | Average of **every** goal ever, all cycles, drafts included | Average for the **current cycle** |
| Employee, Goals page "Avg Progress" | `goals_api._dashboard_stats` :79 | Same — all cycles | Current cycle |
| Manager, team goals list | `goals_api.get_team_goals` :810 | Goals with status Active, **any cycle** — 83 Q1 goals are still "Active" although Q1 is Completed | Current cycle |
| Manager, report's scorecard goal list | `hr_api.get_employee_scorecard` | Latest 15 goals, any cycle | Current cycle first |
| Manager, "My team's reviews" | `performance_api.get_team_reviews` :942 | With no cycle chosen, one appraisal per person picked by dictionary order — **the oldest wins** | The newest cycle |

### Cause

The goal queries filter by employee but not by `appraisal_cycle`. PPJ has Q1
(Completed) and Q2 (In Progress). Each employee has at most two goals, one per cycle,
so the average blends a finished quarter (Q1 goals average 97%) with the live one
(Q2 average 71%).

For `get_team_reviews`: the page always sends the active cycle, except when **no**
cycle is In Progress or open — the page's picker is then blank. **Q2 ends on 30 Sep.**
If HR marks it Completed before creating Q3, managers hit this in the first week of
October — go-live week.

### Measured on PPJ

- **210 of 213** employees with goals get a different average.
- Inflated by **13 points on average, 50 at most**.
- 83 stale "Active" Q1 goals in managers' team goal lists.
- Weightage is 0 on every PPJ goal, so weighting changes nothing on PPJ today.

### Money or decision?

**The rating itself is right.** The appraisal's goal score reads goals **for that
cycle, by weight** (`performance_api` :1480–1490). The wrong figure sits on the
manager's comparison chart — in front of them while they rate in October. That is a
decision risk, not a money error.

### Fix

One helper: the current cycle for a company, with the rule `get_performance_context`
already uses (In Progress, else the newest not Completed) — but **per company**, which
today's rule is not. Four aggregates filter by it. `get_team_reviews` orders by
`start_date` so the newest wins when no cycle is given. Simple average stays as it is
(weighting is a question, not a fix — see Q-G2).

---

## 5. W7 — The payslip

### What is wrong, exactly

**There are two payslips: the portal view and the PDF.** They are different code.

| # | What | PDF | Portal view | Evidence |
|---|---|---|---|---|
| P1 | **Layout.** Frappe's generic automatic layout, not a payslip. `Salary Slip` has no default print format, so `download_payslip` gets "Standard" | **wrong** | — | `get_meta("Salary Slip").default_print_format` is `None` on PPJ |
| P2 | **Internal fields printed:** Journal Entry, Payroll Entry, Salary Structure, CTC, Status, "Company Currency" duplicates, tax-projection fields | **wrong** | fine | Rendered labels, 22 Sep |
| P3 | **Zero lines printed:** "Professional Tax ₹0.00" on all 800 slips (PT is 0 on every PPJ slip), "Income Tax ₹0.00" on 741 | **wrong** | fine (hides zeros) | `tabSalary Detail` |
| P4 | **Missing statutory identifiers:** no UAN, no PAN, no employee number, no date of joining, no establishment address | **missing** | missing | Standard layout |
| P5 | **Net pay printed ≠ net pay paid.** Both views show `rounded_total` (and the words say the rounded figure). The bank entry (`payroll_entry.make_bank_entry`) pays the unrounded sum of lines. Earnings − deductions ≠ the figure shown, and no "rounding" line explains it | **wrong** | **wrong** | **555 of 800** slips differ, by up to **₹0.50**; 269 rounded up, 286 down |
| P6 | **Why paid days < working days is not shown.** 442 slips have absent days that reduced pay | shown (Standard) | **missing** — only "Unpaid leave" is shown, and it is 0 on all 800 | `absent_days` |
| P7 | **Fractional paid days truncated** — PPJ's own format uses `payment_days | int`. With half-day LWP at 0.5, a 29.5-day month prints 29 | n/a today | fine | PPJ format; no fractional slip on PPJ yet |
| P8 | **Statistical / not-in-total components** would be listed and would not add up to the total | fine (PPJ format filters) | **wrong** (lists every non-zero line) | `hr_api.get_payslip` `lines()`; none on PPJ today |
| P9 | **The only good format exists only on PPJ.** "PPJ Salary Slip Format" (Jinja, made on 8 Sep) is in PPJ's database, not in the repo, and says PP Jewellers' colours | — | — | `tabPrint Format`; `grep` of the repo |

**P9 changes the task.** The assessment said "set PPJ's format as the default". PPJ is
the demo. `dtc` and `aahr` would get the generic layout (P1–P4) on day one. The fix
has to be **a payslip format the product ships**, for every tenant.

**The amounts are right.** Every line, gross, deduction and net comes from the
submitted Salary Slip, and the portal only reads it.

### Things I noticed in the pay data, outside this slice

Not checked properly, not proposed, **for a payroll person to look at**: ESI is deducted
on some slips with gross above ₹21,000 (up to ₹37,100) — the contribution-period rule
may explain it; 7 slips at or under ₹21,000 have no ESI; the Provident Fund component
is set not to follow payment days. None of these is a display bug.

### Fix

- **E1 — a shipped payslip format.** A standard Print Format "Alvoraa Salary Slip" in
  `alvoraa_portal`, based on PPJ's layout (which already fixes P1–P4), in neutral
  colours, reading the company's own name. `download_payslip` uses the tenant's own
  default if one is set, else this one — so a client with its own format keeps it.
  Fix P7 (show days to two decimals, hiding ".00"). Frappe syncs a print format from an
  app folder on `bench migrate` (`frappe/model/sync.py` `IMPORTABLE_DOCTYPES`) — the
  deploy already migrates. **The content needs your decisions — §9, Q-P1 to Q-P7.**
- **E2 — the portal view.** Filter lines the same way as the PDF (P8); show absent
  days (P6); show net pay by your answer to Q17 (P5).

---

## 6. Personas

| Persona | Before | After |
|---|---|---|
| **Employee** | Leave left too high (97 people); Diwali shown as a holiday to store staff; a team view of strangers in other cities; goal average blended with last quarter; a PDF that looks like a database dump | Leave matches the ledger and the preview; own holidays only; own team, own weekly offs, "in" today; this quarter's average; a real payslip |
| **Manager** | Report's balance too high; wrong weekly offs for 282 of 402 reports; comparison chart 13 points high; team reviews pick the oldest cycle between cycles | Consistent with what Frappe HR will allow and with the review screen |
| **HR** | Acting on someone's behalf, sees the wrong balance; holiday source can drift from payroll's without anyone seeing it | Same balance the leave gate uses; one holiday source |
| **Owner / CXO** | Leadership leave-used % low (slice 012's file, §1.5); org figures otherwise untouched | Unchanged in this slice. Follow-up offered in 012's lane |

**No one sees more than before.** W4 narrows what peers see. No new field goes into a
list, export, notification or API response, except: `taken` now includes late-rule
days (already shown on the deduction card to the same people), and, if you say yes to
Q-L1, a "3 of these for late arrivals" line to the employee only.

---

## 7. Cross-module impact

| Module | Effect |
|---|---|
| **Leave** | Read-only. The four screens start reading the ledger. No write, no change to Leave Application, Allocation or the ledger |
| **Attendance** | Read-only. Holiday and weekly-off resolution for the portal; today's check-ins for presence. The late rule, auto-attendance and slice 017's figures are untouched |
| **Payroll** | One new print format; the download chooses it. No Salary Slip, structure or component changes. Payroll Settings untouched |
| **Appraisals** | `get_team_reviews` ordering only. Review records, ratings and the goal-score projection untouched |
| **Goals (`alvoraa_goals`)** | Read-only filters on Individual Goal. No doctype change, no controller change |
| **Late rules (`hrms/alvoraa_late_rules`)** | Not changed. **One upgrade risk found:** the ledger counts late-rule days only because of a 4-line local edit inside Frappe HR's `get_leaves_for_period` (`leave_application.py` :1303). A Frappe HR update that drops it would make *every* balance — Frappe's and ours — ignore late-rule days again, silently. W2's pin test will catch that |
| **Org structure (`hrms/alvoraa_org_structure`)** | Not touched |
| **Mobile field app** | Calls none of these endpoints (grepped `mobile/`) |

### Every caller of what I would change

| Function | Callers (outside tests) | Change to its contract |
|---|---|---|
| `hr_api.get_employee_dashboard` | page :6675 only | same keys; values corrected |
| `hr_api.get_leave_summary` | page :7201, :7267, :7329 | same keys |
| `hr_api.get_employee_scorecard` | page :8073 | same keys |
| `hr_api.get_employee_detail_for_manager` | page :8037 | same keys |
| `hr_api.get_team_scorecard` | page :8258 | same keys |
| `hr_api.get_week_presence` | page :6584 | same keys; `basis` may gain one value (Q7) |
| `hr_api._holiday_dates` | `get_week_presence` only | replaced by the shared helper |
| `hr_api.get_attendance_calendar` | page :7121 (Time calendar) | holiday source only |
| `attendance_correction` holiday block :423 | inside `_month` | holiday source only |
| `hr_api.get_payslip` | page :7634 | same keys, fewer lines when statistical |
| `hr_api.download_payslip` | page :7677 (a link) | print format choice only |
| `goals_api._dashboard_stats` | `goals_api.get_portal_context` :140 → page :10101 | same keys |
| `goals_api.get_team_goals` | page :11226 | same keys |
| `performance_api.get_team_reviews` | page :13539; 5 test files | order only |
| `hrms/pms` `get_employee_dashboard` | a different function in `hrms.pms.api` — not affected | — |

Greps run: `Leave Allocation`, `total_leaves_allocated`, `get_leave_balance_on`,
`get_leave_details`, `Leave Ledger Entry`, `"Holiday"`, `holiday_list`,
`get_holiday_list_for_employee`, `progress_pct`, `appraisal_cycle`,
`get_team_reviews`, `default_print_format`, `download_payslip`, `get_payslip`, and each
endpoint name, across `alvoraa_portal`, `alvoraa_goals`, `hrms/hrms/alvoraa_*`, `mobile/`,
`scripts/`, `demo/`.

---

## 8. Non-functional verdict (proposal)

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **degrades slightly, within budget** | The ledger balance costs about **30–37 queries and ~35 ms warm** per person (measured: PPJ-0047 29 q / 33 ms, PPJ-0001 34 q / 43 ms; first call 395 ms cold) against today's 2. Frappe HR does one holiday-count query per Leave Application inside the period — bounded by the person's own applications. Budget: 500 ms per call. Holidays and week presence **improve**: Home stops reading up to 200 rows from every list; presence batches holidays in one query instead of applying one person's to all. Goal filters shrink result sets |
| **Security** | **neutral to improves** | No new endpoint, no new permission. The ledger helper deliberately skips Frappe's `validate_leave_access` — every caller has already checked who may see whom (named per caller in the tests). `ignore_permissions` count in `hr_api.py` **goes down** (the allocation/application reads go). Payslip ownership check (`_own_payslip`) untouched |
| **Reliability** | **improves** | One source of truth per figure. Missing holiday list → empty, never a crash (`raise_exception=False`). No cycle → newest, not arbitrary. Payslip falls back to the shipped format, never to the generic dump |
| **Scalability** | **neutral** | All reads are per person or per team (≤ 40), bounded, no loops of queries over headcount. Week presence becomes one batch holiday query for the team |
| **Maintainability** | **improves** | Four copies of the leave sum become one helper; three holiday lookups become one; three goal averages share one cycle rule. The ~12 copied lines of Frappe HR's balance are pinned by a comparison test |
| **Data integrity** | **improves** | Nothing stored changes — every figure is computed per request, so nothing to backfill. No cache added, so no invalidation to define. The screens stop disagreeing with the ledger, the assignments and the appraisal |
| **Compliance / privacy** | **improves** | Peers stop seeing strangers' presence. A statutory document stops printing internal fields and starts carrying the identifiers — **subject to your wording decisions** (PAN and bank number are sensitive; §9). No personal data logged |

---

## 9. Questions for you

**Leave**
- **Q-L1.** Should the employee see *"8 of 8 used — 3 of these for late arrivals"*, or
  just *"8 of 8 used"*? I recommend the split line for the employee only, never the
  manager (in line with Q-b: managers learn days at most).

**Holidays**
- **Q16 (open since 14 Sep).** Home's holiday card: this **financial** year (April–March,
  matching the lists) or the **calendar** year? I recommend: from this month to the end
  of the employee's current holiday list, which is the financial year on PPJ.
- **Q-H1.** May I (or you) run a **read-only** count on `dtc` and `aahr`: how many
  employees have a Holiday List Assignment, and how many only the Employee field? It
  decides whether B2 must go in the second release. I have not touched them.

**Team this week**
- **Q7 (open since 14 Sep).** For someone with no reports: **same manager** (their
  colleagues under one person — 5 of 402 are in another branch), or **same department
  and branch**? I recommend same manager.
- **Q-T1.** Week starting Sunday or Monday? It is one System Setting, per tenant.

**Goals**
- **Q-G1.** "Current cycle" = In Progress, else the newest not Completed, **per
  company**. Agree?
- **Q-G2.** When goals carry weights, should the average be weighted? PPJ has none
  today. I recommend weighted when the weights add up to more than 0, otherwise simple.

**Payslip — please do not let me guess any of these. It is a statutory document.**
- **Q-P0.** Will `dtc` and `aahr` run payroll in Alvoraa in October? If not, the
  payslip can wait for the third release.
- **Q17 / Q-P1 (open since 14 Sep).** Which net pay is printed: the **exact** net that is
  paid (e.g. ₹32,400.60), or the **rounded** ₹32,401 with a "Rounding" line? Today the
  slip says the rounded figure while the bank entry pays the exact one. Alternatively
  HR switches rounding off in Payroll Settings, and both become the exact figure.
- **Q-P2.** **PAN and bank account number on the slip:** in full (PPJ's format), last
  four digits only, or not at all? I recommend PAN in full (it is the employee's own
  and needed for tax), account number masked to the last four.
- **Q-P3.** **What must a wage slip carry** under the Code on Wages and the state Shops
  and Establishments rules for Punjab, Haryana, Delhi and Uttar Pradesh (where PPJ has
  stores)? I do not know the exact list and will not guess. PPJ's format has: company
  name, pay period, employee name, number, designation, department, location, date of
  joining, UAN, PAN, working/paid/LWP/absent days, every non-zero earning and deduction,
  gross, total deductions, net, amount in words, bank and mode. **Missing: the
  establishment's address, the employer's registration numbers (PF, ESI), the
  father's/spouse's name, the rate of wages.** Someone qualified should confirm.
- **Q-P4.** Show the **employer's** PF and ESI contributions (for information), and
  **year-to-date** totals? Both are common in India, neither is in PPJ's format.
- **Q-P5.** Show **leave balances** on the slip? PPJ's Payroll Settings say yes
  (`show_leave_balances_in_salary_slip = 1`), but PPJ's format ignores it. If yes, it
  shows the ledger balance — which after W2 matches the portal.
- **Q-P6.** The footer says *"This is a computer generated salary slip and does not
  require a signature."* Keep that wording?
- **Q-P7.** The company's **logo** from the tenant's brand (slices 025/029), or
  name only? Logo costs a little work for multi-company tenants.

---

## 10. Strategy: commits in shipping order

Each commit is one change a reviewer can hold in their head, with its own tests and a
test that names it (so a merge cannot silently drop it).

| # | Commit | Files | Needs | Size | Release |
|---|---|---|---|---|---|
| **1** | **Leave left from Frappe HR's ledger** — `_ledger_leave_balances`, used by the four endpoints; Home reads `total`. Tests: Attendance Deduction reduces every screen's balance; helper equals `get_leave_balance_on`; manager-not-approver and store HR still get the figure; Home keeps a fully used type; query count asserted | `hr_api.py` (4 functions + 1 helper), page `loadHomeLeave` (2 lines), new test file | Q-e (decided). Q-L1 only for the optional split line | 0.75 day | **2nd** |
| **2** | **Home holidays: the employee's own list** — own list, named holidays, this month to the end of the list. Tests: another list's dates never appear; another company's never appear; January–March shown | `hr_api.get_employee_dashboard` holiday block, test | Q16 (default: to the end of the list) | 0.25 day | **2nd** |
| **3** | **Goal % for the current cycle** — per-company cycle helper; `get_team_scorecard`, `_dashboard_stats`, `goals_api.get_team_goals`, scorecard list; `get_team_reviews` newest-first. Tests: Q1 goal never in a Q2 average; no active cycle picks the newest | `hr_api.py`, `goals_api.py`, `performance_api.py` (1 line), test | Q-G1 (default as written). Q-G2 can follow | 0.75 day | **2nd** — reviews happen in go-live week |
| **4** | **One holiday source for the portal** — assignment first, then company, then the Employee field; used by the calendar, the correction screen and presence | `hr_api.py`, `attendance_correction.py` (holiday block only), test | Q-H1 decides urgency | 0.5 day | **3rd**, or **2nd** if `dtc`/`aahr` use assignments only |
| **5** | **"Team this week"** — group by Q7, each person's own weekly offs (batch), "in" from today's check-ins, honest title | `hr_api.get_week_presence`, page `loadHomeWeek` (1 line), test | **Q7** | 0.75 day | **3rd** |
| **6** | **Shipped payslip format** — "Alvoraa Salary Slip", default for the download unless the tenant set its own | new `alvoraa_portal/alvoraa_portal/print_format/alvoraa_salary_slip/`, `hr_api.download_payslip` (1 line), test renders it | **Q-P0 to Q-P7** | 1 day | **2nd only if** the clients run payroll in October **and** you answer Q-P1–P3 this week; else **3rd** |
| **7** | **Portal payslip view** — same line filter as the PDF, absent days, net pay per Q17 | `hr_api.get_payslip`, page `renderPayslip`, test | Q17 | 0.5 day | with 6 |

**Total: about 4.5 days** of build and tests, plus review (the reviewer, the security
review and release readiness run together in `/slice-build`, as for 017).

### What goes in the second release, and what waits

**Second release (recommended): commits 1, 2 and 3 — about 1.75 days.**
- They fix the three numbers people will act on in go-live week: leave (97 people),
  Diwali (363 people), and the goal chart managers rate beside (210 people).
- All three are read-only changes to figures, with decisions already made or a safe
  default. No migrate, no doctype, no data change on any tenant.
- Only two page lines change (Home leave), which keeps the collision with slice 034
  small.

**Second release, only on your word:** commit 4 if Q-H1 shows the new tenants use
assignments; commits 6–7 if the clients run payroll in October and the payslip
wording is decided.

**Third release:** commit 5 ("team this week") — needs Q7, and Home's week card is
redesigned in Wave 2 anyway. Commit 4 at the latest before **1 April 2027**.

---

## 11. Parallel-work check

**What came in.** My branch is `origin/dev` at `1c4e84c`. Local `dev` in the main
checkout is at `3ab09f1`, 9 commits behind `origin/dev`: the mobile app client
(slice 013 stages 1–2 and ALV-37 fix), worker health (026), and the new private image
package (033). None touches leave, holidays, presence, goals or payslips. The files I
would change are identical in local `dev` and `origin/dev`, so the bench (which runs
the main checkout) ran the same code I read.

**Another session's uncommitted work in the main checkout** — not mine, not touched:
Android build files under `mobile/field-app/` (staged and unstaged) and untracked
`mobile/field-app/` folders.

**Files I would change, and who else is in them.**

| File | Hot? | Who else | Plan |
|---|---|---|---|
| `alvoraa_portal/alvoraa_portal/hr_api.py` | **hot** | Board rows 010 (leave on behalf, `get_leave_summary`) and 012 (`get_hr_analytics`, org settings) — **both already in `origin/dev`**, nothing outstanding on their branches. 017 claims `get_team_late_list`, not mine | **Split.** I change only the functions named in §7. New helpers are added, no signature changes |
| `alvoraa_portal/alvoraa_portal/goals_api.py` | shared | 010's `approve_goal_update`, `submit_goal_update` — landed | **Split.** `_dashboard_stats`, `get_team_goals` only |
| `alvoraa_portal/alvoraa_portal/performance_api.py` | shared | 010 round 2 claimed `get_team_reviews` — landed (0 commits outstanding) | One ordering line. **Ask** whether 010's owner minds |
| `alvoraa_portal/alvoraa_portal/attendance_correction.py` | shared | 017 (`_shift_start`), 010 (`decide`) | **Split.** Holiday block :423 only, commit 4 |
| `alvoraa_portal/alvoraa_portal/www/hrms-employee.html` | **the hottest file** | **Slice 034 is planning to split this page right now** | See below |
| new `print_format/alvoraa_salary_slip/` and new test files | new | nobody | — |

**Slice 034 (the redesign frame) — where we could collide.** Its plan is not written
yet, so I cannot see its claims. My page changes are tiny and in the figures' own
render functions: `loadHomeLeave` (commit 1, two lines), `loadHomeWeek` (commit 5, one
line), `renderPayslip` (commit 7). **Proposed sequence:** 035's commits 1–3 land in
`dev` first (they touch two page lines); 034 rebases onto them. If 034's split lands
first, I rebase and make the same two-line change wherever `loadHomeLeave` moved to.
Everything else in 035 is server-side, in 034's lane only as a caller. **I will not
move, rename or re-indent anything in the page.**

**Tests that pin what I touch.** `test_portal_security_010.py` (the
`ignore_permissions` ceiling for `hr_api.py`, today 75 — mine lowers the count, so the
ceiling can drop); `test_review_*_010d.py` (5 files call `get_team_reviews`, all with a
cycle except two, which I will run); `test_review_copies_010d.py` /
`test_review_outside_010d.py` (scorecard and detail access); `test_endpoint_entitlement.py`
(`get_team_goals` gating). **Nothing tests `get_employee_dashboard`,
`get_week_presence`, `get_payslip` or `download_payslip` today** — each commit adds the
test that names its fix.

**Bench.** No test run in this analysis. When approved: tests in a throwaway container
against its own site (as 017b and 024 did), claimed on the board first.

---

## 12. What I did not check

- `dtc.alvoraa.co` and `aahr.alvoraa.co` — no access, and not asked for. Holiday source
  (Q-H1) and payroll use (Q-P0) are unknown for them.
- Real phones and browsers — nothing was rendered in a browser for this analysis.
- The legal content of an Indian wage slip (Q-P3).
- Whether PPJ's payroll figures (ESI, PF, TDS) are right — noted in §5, out of scope.
