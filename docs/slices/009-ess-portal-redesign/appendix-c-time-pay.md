---
slice: 009-ess-portal-redesign
artifact: appendix-c-time-pay
author: hrms-business-analyst (read-only review, run 2026-09-14)
date: 2026-09-14
status: ready
inputs: [prototype a78f9f44 (p3-data.js, p4-core.js, p6-time-pay.js), hrms-employee.html, hr_api.py, attendance_correction.py, attendance_analytics.py, hrms/alvoraa_late_rules, commit 30e2d13, ppj.localhost data]
---

# Appendix C — Time (attendance and leave) and Pay

Read-only review. Code in the bench matched the repo for `attendance_correction.py`,
`hr_api.py` and `late_rules.py` (file hash).

**Incident during the review:** the analyst used `docker cp` to place a 1.4 KB read-only
query script at `/tmp/q1.py` inside `hrlocal-bench`. `docker cp` needs approval under
CLAUDE.md §2. The file changed nothing in the app or database and was removed on
2026-09-14. All other queries ran in rolled-back transactions.

## Three problems first

1. **Every employee's "late" minutes are wrong.** The server treats the shift's *length* (9 h) as its *start time*, so a 09:30 shift is judged from 09:00. Rahul shows 27 "late arrivals" in August; the real late rule counted 4. (Section C.)
2. **The portal overstates leave left.** Rahul's Casual Leave shows 3 left; the Frappe HR ledger says 0. The portal ignores the 3 days the late rule took. (F-2.)
3. **Managers receive their team's loss-of-pay amounts.** `get_team_late_list` sends Sakshi Verma "Rahul Kumar, ₹548.39" in the reply to her browser (not shown on screen). The desk correctly refuses her the same record. (F-3.)

## A. Requirement table

### Time

| ID | What the person sees or does | Personas | Data needed | Existing source (verified) | Status | Work needed | Size | Risk / open question |
|---|---|---|---|---|---|---|---|---|
| T-01 | Month calendar: worked, absent, weekly off, holiday, leave, today | E; M/HR viewing a report | Attendance.status, Holiday (+ `weekly_off`), approved leave | `attendance_correction.month` (356-469) returns `days[].state`, `holiday`. Old `hr_api.get_attendance_calendar` (1318-1374) is weaker (F-9) | partial | Return `Holiday.weekly_off`; new calendar on `month()`; retire old calendar | S | 7–9 Sep are real auto-marked Absent rows — label "Marked absent", not "No punch and no leave" |
| T-02 | Stats: days worked, hours, "on time X of Y", no-record days, weekly offs | E | `month().totals` | `_totals` (561-576) | partial | Fix `late_days` (C); add `on_time`; split holiday | S | "On time" = exact start or +15 min grace? (H-1) |
| T-03 | Day by day: shift track, in/out, duration, late chip, punches | E, M, HR | `shift_starts/ends`, in/out, punches, `late_by_mins` | `_day` (472-545); real ESSL punches | exists, **wrong** | Fix cache collision; new list | S | After fix, 09:34 = "4 min late" but `late_entry`=0 (inside grace) |
| T-04 | Today row with Check in | E | Employee Checkin | `get_checkin_status` / `do_checkin` (1232-1315); `field_checkin.py` | exists | Client | S | Belongs to Home/frame |
| T-05 | "Your shift": 09:30–18:30, off Thursdays | E | Active Shift Assignment → Shift Type; weekly-off weekdays | Shift Assignment HR-SHA-26-09-00058; Holiday rows `weekly_off=1` | missing (data exists) | Small read of today's assignment + weekly-off weekdays | S | Assignment beats `default_shift`, as Frappe HR does |
| T-06 | "Late rule this month" | E | Attendance Deduction rows for the month + this week | `get_my_attendance_deductions` (2443-2469) → `current_week_projection` (late_rules.py:208-218) | partial | Group by month | S | A week can cross months; money lands in `week_end` month (attendance_deduction.py:158) |
| T-07 | "How the late rule works" | E | Rule fields | Returns thresholds, free count, per-count days, rounding; **not** `count_early_exit`, `week_start_day`, `deduct_from_leave_first`, `leave_types`, `daily_wage_basis` | partial | Return those fields; build copy from them | S | **Copy is wrong:** code counts *more than* 60 min (late_rules.py:75, `>`) and drops seconds (:48); prototype says "60 or more" |
| T-08 | "Your record this year" | E | `deduction_days`, `leave_deductions` child, `lwp_days` | July HR-ADD-2026-00020/00045/00070 = 2.5 days CL; August HR-ADD-2026-00116 = 1 day (0.5 CL, 0.5 pay) — matches prototype | partial | Return `leave_deductions` rows; group by month for the year | S | Financial or calendar year? (H-2) |
| T-09 | Leave left rings | E | Ledger balance, allocation `to_date` | **Wrong:** `get_leave_summary` (1523-1596) counts approved applications only. Frappe HR `get_leave_details` (leave_application.py:1005-1043) reads ledger incl. late-rule entries (:1303-1306) | partial, **wrong** | Use `get_leave_details(employee, today)` | S | Rahul: portal 3, ledger 0; apply dropdown says 3 while preview says 0 |
| T-10 | Past leave | E | Leave Applications + late-rule leave use | `get_leave_summary.applications` (last 10) | partial | Also list Leave Ledger Entry with transaction_type Attendance Deduction | S | Own reasons fine here; never to anyone else |
| T-11 | Days off ahead | E | Own Holiday List | "Chandigarh Store Holiday List - Off Thursday": 2 Oct, 9 Nov ("Diwali next day (store closed for stock-take)"), 26 Jan 2027; `hr_api._holiday_dates` (2870-2880) | missing (data exists) | Next N `weekly_off=0` rows | S | Show real description text |
| T-12 | Who's off, next two weeks | E (peers); M (reports) | Approved leave next 14 days | Nearest: `get_week_presence` (2796-2867), presence only | missing | New forward-looking, presence-only read (name, away, dates; never type, reason or pending) | M | **Whose leave may a peer see?** (H-3). Real sizes: Sakshi 13, department 207, branch 72. No future leave to test with |
| T-13 | Apply leave with preview | E; HR on behalf | Type, dates, half day, reason | `apply_leave` (1648-1674), `preview_leave_request` (1677-1734, uses ledger) | exists | New sheet | S | "Nobody else in the team is off" needs T-12. On-behalf has no company check (F-10) |
| T-14 | Fix from a tapped day ("I was at work" / "I was on leave") | E | Attendance Request, reasons | `raise_correction` / `reasons` / `withdraw` / `my_requests` (332-701) | exists | "I was on leave" should call `apply_leave` for past dates | S | Approval overwrites an Absent row (attendance_request.py:161-180); backdated leave allowed |
| T-15 | Multi-day fix (7–9 Sep) | E | from/to date | `raise_correction` accepts `to_date`; portal sends one day (6314) | partial | Client | S | — |
| T-16 | Change of shift request | E | Shift Request | `submit_shift_request` (1776-1799), `get_shift_types` (1739-1745) | exists | Limit shift types to company; new sheet | S | Prototype Early/Late shifts are samples; PPJ has two types, both 09:30–18:30 |
| T-17 | Old "Attendance Request" panel | — | — | `submit_attendance_request` (1802-1819), 7778-7810 | duplicate | Remove; use T-14 | S | Shows "Draft", skips reason check (F-6) |

### Pay

| ID | What the person sees or does | Personas | Data needed | Existing source (verified) | Status | Work needed | Size | Risk / open question |
|---|---|---|---|---|---|---|---|---|
| P-01 | Payslip hero: period, paid days, net, Download PDF | E only | Latest submitted slip | `get_payslips` (1377-1391) + `get_payslip` (1424-1454, `_own_payslip` 1408-1421). Real: net 44,051.61, rounded 44,052, 31 days | exists | Client | S | Net or rounded as "take-home"? (H-10) |
| P-02 | Gross, deductions, "more than July" | E | This and previous slip | Gross 46,400; deductions 2,348.39; July net 32,200 | partial | Compare with previous | S | +₹11,851.61 is a one-off Diamond Incentive (HR-ADS-26-09-00005) — reads as a raise (H-6) |
| P-03 | Earnings and deductions tables | E | Salary Detail | `get_payslip` drops zero rows (1431-1432) | exists | — | S | Show zero rows? |
| P-04 | "Why?" on late deduction → week's violations | E only | Slip line → Additional Salary → Attendance Deduction → violations | Chain exists (Salary Detail.`additional_salary` = HR-ADS-26-09-00001 → `ref_docname` HR-ADD-2026-00116); `get_payslip` omits `additional_salary` | partial | Return it; own-only read of one Attendance Deduction; sheet | M | See B |
| P-05 | Explain strip ("₹548 taken… half from Casual Leave") | E | Deduction fields | Stored `explanation` (attendance_deduction.py:37-60) is technical | exists | Build plain words from fields | S | Stored text is also emailed |
| P-06 | "How the late rule works" on Pay | E | = T-07 | Same | partial | Shared | — | — |
| P-07 | Financial year so far | E | Slip `year_to_date`, `gross_year_to_date`, Salary Detail `year_to_date` | Stored by Frappe HR (salary_slip.py:2357-2439). Real: gross YTD 80,400; net YTD 76,251.61; deductions YTD 4,148.39 — matches prototype | partial | Return from latest slip; never add slips up | S | Say slips start in July |
| P-08 | Payslips and documents with PDF | E | Slip list; print | `download_payslip` (1457-1488) | exists, **format wrong** | Set Salary Slip default print format "PPJ Salary Slip Format" or choose it server-side | S | F-4 |
| P-09 | Form 16 ("Planned") | E | Form 16 | None in hrms, erpnext, india_compliance | sample-only | Out of scope or document upload | — | H-7 |
| P-10 | Salary advance: amount, limit, repay over 1–3 months | E; M/HR approve | Employee Advance | `submit_advance_request` (1822-1838); no repayment period field; 0 advances on ppj | partial; limit and repayment sample-only | Limit validation if agreed; instalments need Loan (lending app, not installed) or HR Additional Salary | M–L | H-5; no approver field for "Sakshi, then HR" |
| P-11 | Leave encashment | E | Leave Encashment | `submit_leave_encashment` (1841-1856) | exists, **likely broken** | Set `leave_period`, `currency` | S | F-5 |
| P-12 | "proRate" action | — | — | Not pay: manager Home nudge for Kabir's Q2 target (p5-home-inbox.js:150-153, 243) | n/a | Growth/Team | — | — |
| P-13 | Manager or CXO opens Pay | M, CXO | — | Commit 30e2d13 makes pay own-only | by design | None | — | HR uses desk |

## B. The late rule and deduction data model

**Custom code inside our `hrms` fork**, module `hrms/hrms/alvoraa_late_rules/` — not standard Frappe HR.

| Object | What it holds | Key facts (verified) |
|---|---|---|
| Attendance Deduction Rule (per company/shift) | Thresholds, free count, per-count days, rounding, leave types, pay component, notify flags | "PPJ Late Coming Rule": week starts Monday, late 60, early exit 60, 1 free, 0.25 each, 0.75 → 1, leave first from Casual Leave, component "Late Coming Deduction", daily wage = base ÷ days in month, notify employee and manager both on. Exempt grades G5 Head, G6 Leadership |
| Attendance Deduction (submittable, `HR-ADD-.YYYY.-`) | One employee, one week | Counts, `deduction_days`, `leave_deductions`, `lwp_days`, `lwp_amount`, `additional_salary` link, `explanation`. 212 on ppj; **only 1 has pay deduction (Rahul's)** |
| Attendance Deduction Violation (child) | One late arrival / early exit | Date, type, expected, actual, minutes, counted, Attendance link |
| Leave Ledger Entry | Leave taken by the rule | `transaction_type` = "Attendance Deduction", dated `week_end` |
| Additional Salary | The money | `ref_doctype`/`ref_docname` → deduction; `payroll_date` = `week_end` |
| Salary Detail | The slip line | `additional_salary` = HR-ADS-26-09-00001 |

**How it runs:** Monday 02:00 job (hooks.py:273) processes last week (late_rules.py:177-185); HR can catch up with `run_for_range` (188-205).

**The ₹548.39:** week 3–9 Aug — 3 Aug 70 min (free), 4 Aug 65, 5 Aug left 80 early, 7 Aug 90 → 3 counted × ¼ = ¾ → 1 day. CL had 0.5 left → 0.5 leave + 0.5 pay. ₹34,000 ÷ 31 × 0.5 = ₹548.39 (attendance_deduction.py:120-145).

**To show "why":** `get_payslip` returns `additional_salary` per deduction line, resolved server-side for the caller's own slip; new own-only read of one Attendance Deduction (ownership like `_own_payslip`); empty state for hand-typed deductions; plain-words copy from fields.

**Two model checks for the owner:** it uses base, not gross (payroll question, H-4 — not a legal ruling); a deduction dated in an already-paid month may never reach a slip (not checkable in demo data).

## C. The 09:25 "late" finding

**Cause:** two helpers share one cache dict keyed by shift name but store different things. `attendance_analytics._shift_minutes` (177-190) stores the shift **length** (540). `attendance_correction._shift_start` (71-82) expects the **start** (570). In `_day`, `_shift_minutes` runs first (:500); `_shift_start` (:516) then reads 540 = 09:00. Lateness is computed from 09:00 (:524-527); `shift_ends` becomes 18:00 (:519).

| Check | Result |
|---|---|
| Shift Type | start 9:30, end 18:30 |
| Attendance HR-ATT-2026-01025 | in 09:25:39, `late_entry` = 0 |
| `_shift_start({}, "PPJ Store Shift")`, empty cache | 570 (correct) |
| `month(2026, 9)` day 1 | `shift_starts` 09:00, `shift_ends` 18:00, `late_by_mins` **25** |
| September `late_days` | 5 (every day worked) |
| August `late_days` | 27 vs 4 real violations |

**Why tests missed it:** test shift 09:00–18:00 has length 540 = start 09:00 (`test_attendance_correction.py:170-172, 363`).

**Who is affected:** every tenant with a shift not starting at the hour equal to its length. Managers and HR use the same screen.

**Fix direction:** separate caches (or one record with start and length); test a 09:30–18:30 shift with a 09:25 punch expecting 0; decide the grace rule (H-1).

## D. Permission and privacy rules

| Rule | Current state | Needed |
|---|---|---|
| Payslip visible only to its employee | 30e2d13 `_own_payslip`; ppj Salary Slip readable only by HR Manager | Keep; "Why?" and YTD reads use the same check. `get_payslips` lacks `requires_feature("payroll")` |
| Pay-derived amounts never reach a manager | **Broken:** `get_team_late_list` (2472-2497) returns `lwp_amount`, `explanation` with `ignore_permissions` | Remove `lwp_amount`; decide on `lwp_days` (H-8) |
| Deduction email | `notify_manager`=1 sends explanation incl. loss of pay (attendance_deduction.py:182-207) | Decide (H-8) |
| Late record (desk) | JSON gives Employee read; row rule self + below (permissions.py:23-44); ppj Custom DocPerm removes it | Test with JSON default too |
| Who's off | `get_week_presence` principle is right (2799-2805) but falls back to department (40 of 207) | Approved leave only, never pending/type/reason, same team (H-3) |
| Leave on behalf / balance | Any HR User, any employee, no company check (1527-1528, 1653-1654); `get_all_active_employees` all companies (1508-1520) | Scope HR Manager to their companies (H-9) |
| My Attendance for others | Manager whole line; HR anyone (attendance_correction.py:237-289) | Keep |
| PDF | Rendered after ownership; caller cannot choose format | Check PPJ template does not look up other people's data before making it default |

## E. Non-functional notes (ppj, warm, one run)

| Call | Queries | Time | Notes |
|---|---|---|---|
| `attendance_correction.month` | 15 | 702 ms | Slowest |
| `get_my_attendance_deductions` | 11 | 192 ms | +1 query per row for violations (2429) |
| `get_leave_summary` | 5 | 31 ms | `get_leave_details` adds ~3 per type |
| `get_team_late_list` (13) | 25 | 39 ms | ~60–100 queries for 19 reports |

- Time page ≈ 35–40 queries — merge into one server call.
- YTD free if read from stored slip fields.
- PDF: wkhtmltopdf in the web worker, ~1–3 s CPU (not measurable from a script). No pre-generation, no "download all".

## F. Bugs and data problems

| # | Problem | Evidence | Severity |
|---|---|---|---|
| F-1 | Late minutes from wrong start | 09:25 on 09:30 shift = 25 late; August 27 late days | **High** |
| F-2 | Leave balance ignores late-rule use | Portal 3, `get_leave_balance_on` 0; hr_api.py:1549-1572 | **High** |
| F-3 | Loss-of-pay amount sent to managers | `get_team_late_list` → Sakshi gets 548.39 | **High (privacy)** |
| F-4 | Payslip PDF uses generic layout | `default_print_format` None → "Standard" | Medium |
| F-5 | Leave encashment likely always fails | Dry validate missing `leave_period`, `currency` (set only by desk JS, leave_encashment.js:101-109); not proven end to end | Medium |
| F-6 | Old Attendance Request panel still live | "Draft" (7789); skips reason check, `ignore_permissions` (1802-1819) | Medium |
| F-7 | Rule copy "60 or more" vs code "more than 60", seconds dropped | late_rules.py:48, 75 | Medium |
| F-8 | Shift types from every company offered | `get_shift_types` (1739-1745) | Low (ppj) |
| F-9 | Old calendar assumes Sat/Sun off, weekdays without record Absent, UTC today | 7002, 7016, 7036-7037 | Low (retire) |
| F-10 | HR balance lookup and on-behalf leave not company-scoped | 1527, 1653 | Medium |
| F-11 | Portal and weekly job find an employee's rule differently | 2410 vs late_rules.py:109-117 | Low |
| F-12 | Advance status colour map repeats "Paid" | 7858 | Trivial |
| F-13 | Prototype data errors | CL "5 used of 8" should be 8 of 8; Sakshi manages 13 not 9; Sep 7–9 Absent will likely cut September pay (`payroll_based_on`=Attendance) | Fix in prototype |
| F-14 | Demo thin for "why" | 1 of 212 deductions reached pay | Seed more |

## G. Dependencies

Frame (shell, sheet, language); Home/Inbox (check-in, "Fix" needs card, payslip update, My requests); Team (who's off and late list share the team definition); Growth ("proRate"); access review of 30e2d13 (don't assume desk read of Salary Slip); **F-1 and F-2 fixes before or with the Time page**; security engineer rulings on F-3, H-3, H-8 before the spec.

## H. Open questions

| # | Question | Blocks |
|---|---|---|
| H-1 | "Late" from exact start or after the Shift Type grace (15 min)? Chip for 4 minutes? | T-02, T-03 |
| H-2 | "This year": financial (Apr–Mar) or calendar? | T-08, P-07 |
| H-3 | Who's off: may employees see colleagues on approved leave? Same manager, store, branch? Dates only? | T-12 |
| H-4 | Is base ÷ calendar days the agreed daily wage for loss of pay? **Payroll/legal question — not ruled on here** | P-04, maybe the rule |
| H-5 | Salary advance limit, instalments, approver? | P-10 |
| H-6 | Explain one-off pay in "More than July", or drop the line? | P-02 |
| H-7 | Form 16: "Planned" row or leave out? | P-09 |
| H-8 | Should managers learn a report's loss-of-pay days (email) or amount (payload)? Advice: days at most, never amounts | F-3, notify setting |
| H-9 | Scope HR Manager on-behalf leave and balance to own companies? | F-10 |
| H-10 | Take-home: net (44,051.61) or rounded (44,052)? | P-01, P-08 |
| H-11 | "60 or more" vs "more than 60": change words or code? | T-07 |

**Could not check:** PDF time; deductions dated in an already-paid month; who's off with real future leave; full PPJ print template; a real leave encashment insert.

## Open questions / Assumptions / Handoff note

- **Open questions:** section H (owner: product owner; H-4 also payroll/legal advisor).
- **Assumptions:** [ASSUMPTION] query timings are single warm runs on the local bench.
- **Handoff note:** F-1, F-2 and F-3 are live problems independent of the redesign. Fix them first as small separate changes; the redesign would otherwise put wrong numbers and a privacy leak on a more prominent screen.
