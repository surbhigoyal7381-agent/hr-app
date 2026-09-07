# 03 — Attendance policy and ESSL integration

This file has four parts: the shift configuration (config only), the ESSL punch feed (simulated for the demo, real design for later), the **quarter-day late rule as a product feature** (build), and the simulated punch data.

## 1. Shift configuration (config only)

Two Shift Types. Both 9:30 to 18:30.

| Field | `PPJ Store Shift` | `PPJ Head Office Shift` |
|---|---|---|
| Start Time / End Time | 09:30 / 18:30 | 09:30 / 18:30 |
| Enable Auto Attendance | 1 | 1 |
| Determine Check-in and Check-out | Strictly based on Log Type in Employee Checkin | same |
| Working Hours Calculation Based On | First Check-in and Last Check-out | same |
| Begin check-in before shift start time (min) | 90 | 90 |
| Allow check-out after shift end time (min) | 240 | 240 |
| Working hours threshold for Half Day | 4.5 | 4.5 |
| Working hours threshold for Absent | 2.0 | 2.0 |
| Enable Late Entry Marking / grace (min) | 1 / 15 | 1 / 15 |
| Enable Early Exit Marking / grace (min) | 1 / 15 | 1 / 15 |
| Mark auto attendance on holidays | 1 (stores work festivals) | 0 |
| Process Attendance After | 2026-07-01 | 2026-07-01 |
| Last Sync of Checkin | set by the loader after punches are pushed | same |
| Auto-update last sync | 1 | 1 |

Two grace periods matter and they are different things:

- **15 minutes** is the Shift Type grace. Arriving after 09:45 sets the `late_entry` flag on Attendance. This feeds the punctuality KPI in file 09 and the Shift Attendance report. It does not deduct anything.
- **60 minutes** is the quarter-day rule threshold (section 3). Arriving after 10:30, or leaving before 17:30, is a *violation* that can cost a quarter day.

Shift Assignment: one per employee, `default_shift` on Employee is enough for auto attendance; also create Shift Assignments from 2026-07-01 with no end date so the roster page shows them.

Attendance Requests (Work From Home / On Duty) stay available for head-office staff. Store staff do not use Work From Home.

## 2. ESSL punch feed

### 2.1 What the eSSL eBioServerNew Web API offers (from the manual, v1.3, 27 March 2025)

The manual describes a **SOAP 1.1 web service** at `http://<eBioServerNew host>/Webservice.asmx`. Every call takes `UserName` and `Password` (created in the eBioServer application). Results come back as one string. The calls that matter for us:

| Operation | Inputs | Returns | Use for us |
|---|---|---|---|
| `GetDeviceLogs` | Location (blank = all), LogDate | Punch records for a date: log date-time, employee code, device name, device location name, direction. Fields comma-separated, records semicolon-separated. | Daily catch-up pull, backfill |
| `GetDeviceLogsByLogId` | Location, LogId, LogCount | Same record shape plus **device log id**, starting after the given id | **Live incremental pull** (the right call for "read logs live") |
| `GetEmployeePunchLogs` | EmployeeCode, AttendanceDate | First-in and last-out of one employee for one date, then all punches | Spot check one person |
| `GetDeviceList` | Location | Devices connected in the database | Store-to-device map |
| `GetDeviceLastPing` | DeviceSerialNumber | Last ping time | Device health on the HR dashboard |
| `UpdateEmployee` / `UpdateEmployeeEx` | EmployeeCode, Name, Location code(s), Role (Normal/Admin), VerificationType (1 to 31, e.g. 16 = Face), expiry dates, card number, photo | success / error | **Push a new joiner to the machines** at the store on onboarding |
| `DeleteEmployee` | EmployeeCode | success / error | Remove on separation |
| `UpdateLocation` | LocationCode, description | success / error | One location per store |

Two things the manual does **not** give, so we must not assume them: the exact date-time format of the log records (get a sample export from the client's server before coding the parser), and whether the string "direction" is `in`/`out` or numeric. Both are one-line parser settings.

### 2.2 How it maps onto the product

Frappe HR already has the receiving side. The whitelisted function `add_log_based_on_employee_field` (in `hrms/hr/doctype/employee_checkin/employee_checkin.py`) takes an employee code, a timestamp, a device id and a log type, finds the employee by `Employee.attendance_device_id`, and creates an **Employee Checkin**. Auto attendance on the Shift Type then turns check-ins into Attendance every hour.

So the integration is: ESSL employee code = `Employee.attendance_device_id` (the CSV already sets this to the 4-digit part of the employee number); ESSL Location code = Branch; ESSL Device name = `Employee Checkin.device_id`.

### 2.3 Real integration design (build later, not for the demo)

Recommended shape: a small **on-site bridge** rather than a cloud-to-LAN connection. eBioServerNew usually sits on the client's LAN, and the cloud site cannot reach it without a static IP or VPN. A bridge script on the same LAN polls eBioServer and pushes to Alvoraa over HTTPS with an API key. No inbound firewall change at the client.

Product-side pieces:

| Piece | Type | Detail |
|---|---|---|
| `Biometric Sync Settings` | Single doctype, HR module | `enabled`, `provider` (eSSL eBioServerNew), `server_url`, `username`, `password` (Password field), `poll_interval_minutes` (5), `log_type_mapping` (in→IN, out→OUT), `datetime_format`, child table `Biometric Location Map` (essl_location_code, branch, shift_location, last_log_id, last_synced_at) |
| `Biometric Sync Log` | doctype | one row per poll: location, from_log_id, to_log_id, records_received, checkins_created, skipped_unknown_employee, errors. Keep 90 days. |
| Scheduler job | `cron: */5 * * * *` | for each mapped location: `GetDeviceLogsByLogId(location, last_log_id, 500)` → parse → `add_log_based_on_employee_field(...)` per record → advance `last_log_id`. If the server is on the LAN, the same job runs inside the bridge and calls the REST endpoint instead. |
| Onboarding hook | `Employee.after_insert` | if settings enabled and `attendance_device_id` set: `UpdateEmployee(code, name, branch location code, Normal, verification type from settings)`. Log the result on the Employee timeline. |
| Separation hook | `Employee.on_update` when status → Left | `DeleteEmployee(code)` |
| Dashboard | number card | "Devices not pinged in 30 min" from `GetDeviceLastPing` |

Duplicates are safe: Employee Checkin already rejects a second log for the same employee, time and log type. Unknown employee codes are counted in the sync log and skipped, not raised.

One rule found while testing: when a Shift Assignment carries a geofenced Shift Location, every check-in must carry coordinates, or Frappe HR refuses it. So the bridge sends the store's own coordinates with each punch (the `Biometric Location Map` row holds them). The demo loader does the same.

Use `requests` with a hand-built SOAP envelope and `xml.etree` to read the reply. No new Python dependency.

### 2.4 For the demo: simulated punches

`demo/pp_jewellers/generate_punches.py` writes `docs/pp_jewellers/data/punches.csv` (45,140 rows) and `data/expected_deductions.csv` (212 employee-weeks the rule must produce, with the violations listed, for verifying the build): `attendance_device_id, timestamp, log_type, device_id`. `demo/pp_jewellers/seed_attendance.py` reads it inside `bench console` and calls `add_log_based_on_employee_field` for each row, then sets `last_sync_of_checkin` on both Shift Types and runs `process_auto_attendance_for_all_shifts`. See file 11 for the run order.

The data has deliberate patterns so the demo has a story:

| Pattern | Who | Effect |
|---|---|---|
| Normal | 80% of staff | in 09:05 to 09:40, out 18:32 to 19:20 |
| Occasionally late | 15% of staff | in after 10:30 on about 8% of days |
| Chronically late | 5% of staff | in after 10:30 on about 25% of days; these people trip the full-day rule |
| Early exit | everyone | out before 17:30 on 3% of days |
| Absent, no punch | everyone | 3% of days |
| Persona case | PPJ-0054 Suresh Sethi | Week 17 to 23 Aug 2026: late Tue 10:47, late Thu 10:52, early exit Sat 17:05 → 3 violations → 0.5 day from Casual Leave. Otherwise a normal employee. |
| Full-day case | PPJ-0058 (Senior Sales Executive, Chandigarh, weekly off Thursday) | A chronic late-comer with a story: 5 days Casual Leave taken in May (seeded Leave Application, file 11). July weeks: 4, 4 and 3 violations → 1.0 + 1.0 + 0.5 = 2.5 days from Casual Leave. Balance left: 0.5. Week 3 to 9 Aug 2026: 4 violations → 1.0 day: 0.5 from Casual Leave, 0.5 loss of pay on the August payslip. |

Dates covered: 1 July to 6 September 2026. Weekly-off days and 15 August (head office only) have no punches.

## 3. Feature: quarter-day late rule (build)

**Status: built and verified 2026-09-07 (build B1, file 10).** Doctypes, weekly job, HR catch-up button, report, portal cards and tests are in the repo. One core change came with it: the leave balance helper in Frappe HR only counted Leave Applications, so it ignored the days this rule takes; it now counts Attendance Deduction ledger entries too (file 10, B1 status).

### 3.1 The policy in plain words (confirmed with the client)

- The week runs Monday to Sunday.
- A **violation** is arriving more than 60 minutes after shift start (after 10:30) or leaving more than 60 minutes before shift end (before 17:30). A day can carry two violations.
- The **first violation in a week is free**.
- Each further violation costs **a quarter day (0.25)**.
- Once **three quarters** are reached in a week, the deduction becomes **one full day**.
- So: 1 violation = 0, 2 = 0.25, 3 = 0.5, 4 or more = 1.0.
- The deduction comes **first from Casual Leave balance**, then as **loss of pay**. Earned Leave is left alone: it is the encashable leave, and the policy should not drain it.
- Days that are already Absent, On Leave or Half Day by the normal shift rules are not counted again.

Worked example, one week:

| Day | In | Out | Violation? | Running quarters | Deduction so far |
|---|---|---|---|---|---|
| Mon | 09:35 | 18:40 | no | 0 | 0 |
| Tue | 10:47 | 18:35 | late, free | 0 | 0 |
| Wed | 09:20 | 18:31 | no | 0 | 0 |
| Thu | 10:52 | 18:45 | late | 1 | 0.25 |
| Sat | 09:28 | 17:05 | early exit | 2 | 0.50 |
| Sun | 09:30 | 18:30 | no | 2 | 0.50 |

Result for the week: 0.5 day. Casual Leave balance 3 → 2.5. Nothing on the payslip. If it had been a third counted violation, the total would be 0.75 and would round up to 1.0.

### 3.2 Where it lives

New module **Alvoraa Late Rules** (`hrms/hrms/alvoraa_late_rules`) inside the `hrms` fork (same pattern as `performance_management`). Switched on per tenant by the opt-in feature key `late_rules` (file 00). Not in `grace_group`, which is client-specific. Not in `alvoraa_goals`, which has no attendance code.

### 3.3 Doctypes

**`Attendance Deduction Rule`** (setup, per company, optional per shift)

| Field | Type | Default |
|---|---|---|
| rule_name | Data | PPJ Late Coming Rule |
| company | Link Company | |
| shift_type | Link Shift Type | blank = all shifts |
| enabled | Check | 1 |
| late_threshold_minutes | Int | 60 |
| count_early_exit | Check | 1 |
| early_exit_threshold_minutes | Int | 60 |
| free_violations_per_week | Int | 1 |
| deduction_per_violation_days | Float | 0.25 |
| round_up_from_days | Float | 0.75 → becomes `round_up_to_days` |
| round_up_to_days | Float | 1.0 |
| week_start_day | Select Mon..Sun | Monday |
| deduct_from_leave_first | Check | 1 |
| leave_types | Table `Attendance Deduction Leave Type` (leave_type, priority) | Casual Leave 1 (a second type such as Earned Leave can be added if the client wants it) |
| lwp_salary_component | Link Salary Component | Late Coming Deduction |
| daily_wage_basis | Select: Base from Salary Structure Assignment / Gross Pay | Base |
| exempt_grades | Table MultiSelect Employee Grade | G5 Head, G6 Leadership |
| notify_employee, notify_manager | Check | 1, 1 |

**`Attendance Deduction`** (submittable, one per employee per week)

| Field | Type |
|---|---|
| employee, employee_name, branch, department, designation | fetched |
| rule | Link Attendance Deduction Rule |
| week_start, week_end | Date |
| violations | Table `Attendance Deduction Violation`: attendance_date, attendance (Link), violation_type (Late Arrival / Early Exit), expected_time, actual_time, minutes, counted (Check) |
| total_violations, counted_violations | Int |
| computed_days | Float (counted × 0.25) |
| deduction_days | Float (after round-up) |
| leave_deductions | Table `Attendance Deduction Leave`: leave_type, days, leave_ledger_entry |
| lwp_days | Float |
| additional_salary | Link Additional Salary (set on submit) |
| explanation | Small Text, auto-written in plain words ("3 violations this week. First is free. 2 counted × 0.25 = 0.5 day. 0.5 taken from Casual Leave.") |
| status | Draft / Submitted / Cancelled (docstatus) |
| hr_remarks | Small Text |

### 3.4 Logic

`process_week(rule, week_start)` — runs for every active employee on the rule's company (and shift, if set), skipping exempt grades:

1. Read submitted Attendance for the week with `status = Present` (Half Day, Absent, On Leave, WFH are skipped).
2. Compare `in_time` against shift start + threshold, and `out_time` against shift end − threshold, using the Attendance's own `shift` so shift changes are respected.
3. Order violations by date and time. Mark the first N (free) as `counted = 0`, the rest `counted = 1`.
4. `computed_days = counted × deduction_per_violation_days`. If `computed_days ≥ round_up_from_days` then `deduction_days = round_up_to_days`, else `deduction_days = computed_days`.
5. If `deduction_days = 0`, do not create a document (keep the list clean).
6. Otherwise create (or update if Draft exists) the Attendance Deduction and **submit it** (the scheduler submits; HR can cancel and amend).

`on_submit`:

- Walk `leave_types` in priority. For each, take `min(remaining, balance as of week_end)` using `get_leave_balance_on`. Create a **Leave Ledger Entry** with `leaves = -days`, `transaction_type = Attendance Deduction`, `transaction_name = this doc`, `from_date = to_date = week_end`. This is exactly how Leave Application and Leave Encashment consume balance, so balances and the portal's Leave Balance card stay correct.
- Remainder becomes `lwp_days`. If > 0, create and submit an **Additional Salary**: component from the rule, `payroll_date = week_end`, `amount = daily wage × lwp_days`, where daily wage = SSA `base` / days in that month (or gross from the last slip, if the rule says so). `ref_doctype`/`ref_docname` point back here, so the payslip line links to the explanation.

`on_cancel`: delete the ledger entries created by this doc, cancel the Additional Salary.

Scheduler: `cron "0 2 * * 1"` → `process_previous_week` for every enabled rule. Also whitelisted `run_for_range(rule, from_date, to_date)` with an HR-only button on the rule, used in the demo to process July and August after the punches are loaded.

Leave Application already refuses to overlap a date that has a submitted Attendance, so there is no double-counting between a leave and a deduction on the same day.

### 3.5 What each persona sees

| Persona | Where | What |
|---|---|---|
| Employee | Portal → Attendance tab, new card "Late & Deductions (this month)" | list of weeks, violations with times, deduction days, where it was taken from, the plain-words explanation |
| Store In-charge | Portal → Team → Team Attendance, new sub-tab "Late List" | this week's violations per team member, counted vs free, projected deduction; last 4 weeks' deductions |
| HR | Desk: Attendance Deduction list, report "Late Coming Deductions" (group by branch, week) | run/cancel/amend; totals per store |
| Owner | Portal home → new tile "Late deductions this month" per store | count and days |

Portal APIs in `alvoraa_portal/hr_api.py`: `get_my_attendance_deductions(month)`, `get_team_late_list(week_start)`, and a branch breakdown inside `get_hr_analytics`.

Notifications: on submit, an email/portal notification to the employee ("0.5 day deducted for week 17–23 Aug: 2 counted violations. See details.") and a weekly digest to the manager.

### 3.6 Impact analysis

See file 10, build B1. Summary: no change to Attendance, Salary Slip or Leave Application code. Everything is additive through documents Frappe HR already understands (Leave Ledger Entry, Additional Salary). The only shared surface is `Salary Component` (one new deduction component).

## 4. Attendance reports for the demo

| Report / screen | Filter | What it shows |
|---|---|---|
| Monthly Attendance Sheet | August 2026, Branch = Chandigarh | grid with P / A / HD / L, late and early-exit counts |
| Shift Attendance | July to August, consider grace | late entry hours, early exit hours per employee |
| Late Coming Deductions (new) | August 2026 | per store: employees affected, days from leave, days loss of pay, amount |
| Number cards | this month | Late Entry, Early Exit, Total Present, Total Absent |
| Portal Team Attendance | today | who is in, who is late, who has not punched |

## 5. Verification after this block

- Employee Checkin count ≈ 45,000. Attendance count ≈ 22,500 (one per employee per working day), all submitted.
- PPJ-0054 has an Attendance Deduction for week 2026-08-17 with 3 violations, 2 counted, 0.5 day, Casual Leave ledger −0.5, no Additional Salary.
- PPJ-0058 has Attendance Deductions for weeks 2026-07-06 (1.0), 2026-07-13 (1.0), 2026-07-20 (0.5) all from Casual Leave, and 2026-08-03 with deduction_days 1.0, 0.5 from Casual Leave, 0.5 LWP, and one Additional Salary "Late Coming Deduction" dated 2026-08-09.
- The Attendance Deduction list matches `data/expected_deductions.csv` row for row (212 rows). Any difference is a bug in the build, not in the data. The head office is closed on 15 Aug and 28 Aug (Raksha Bandhan), and the part-week before 1 July is never processed because the rule's `process_from` is 1 July; the CSV allows for both.
- Casual Leave balance for PPJ-0054 = allocation − 0.5 (minus any leave applications).
