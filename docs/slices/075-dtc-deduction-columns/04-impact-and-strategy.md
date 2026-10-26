# 075 - 11 AM and grooming columns: impact and strategy

Rung: **new code, a few lines** in the existing report and the existing month roll-up. Configuration was rejected because the 11 AM figure is not kept anywhere the report can read (the verdict has it, the roll-up dropped it). No new DocType, field, hook or setting.

## What was found
- **11 AM**: the extra quarters are inside `total_quarters`. Paid days, then Basic earned, already carry them. The column only splits them out. Net must not change for it.
- **Grooming**: the report's Net already takes it off. Slice 066 put `grooming_deduction` into `summarise_month` and into `net`. It is the same figure the slip's "Grooming Red Value" line gets. It is 0 when `grooming.is_on()` is false.
- **Employee field**: `dtc_11am_quarter_deduction` is not defined in the repo. It exists only as a Custom Field on the DTC site.

## Plan
1. `payroll_month.py`: sum `extra_quarters` (not on held days) and price it as quarters / 4 x daily rate, the same conversion `day_credit` uses.
2. The report: two new columns (11 AM quarters, 11 AM deduction), relabel the grooming column "Grooming red deduction", and say in the message what Net does with each.
3. Engine behaviour (`late_window_employee_field`) is not touched.

## NFR, one line each
- Performance: neutral. One integer add per day already looped over.
- Security: neutral. No new endpoint or read. Same roles on the report.
- Reliability: neutral. Read-only report; held days charge no 11 AM.
- Scalability: neutral. No new queries.
- Maintainability: improves. One conversion, shared constant `QUARTERS_PER_DAY`.
- Data integrity: neutral. Net formula unchanged, so report and slip cannot drift.
- Compliance / privacy: neutral. Salary figures stay on a role-gated report; field rights (ALV-215) untouched.
