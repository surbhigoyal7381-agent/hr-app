# 075 - implementation notes

## Built
- `alvoraa_portal/alvoraa_portal/payroll_month.py`: `late_window_quarters` and `late_window_deduction` on the month summary. Configure/extend: reuses the roll-up the slip uses.
- `.../report/salary_components_and_workings/salary_components_and_workings.py`: two new columns, grooming column relabelled, message explains Net.
- `alvoraa_portal/alvoraa_portal/tests/test_salary_report.py`: class `TestTheTwoDeductionColumns` (6 tests).

## Requirements
1. Columns: done. Rupees = quarters / 4 x daily rate. Grooming read from the existing roll-up figure (grade rate x distinct marked days, minus leave/absent days, capped at 3% of Basic earned).
2. Net: 11 AM already inside Basic, Net not changed for it (test proves ticking moves Basic and Net by the same amount). Grooming was already subtracted by slice 066; nothing new needed. Off = 0.
3. 11 AM only for ticked staff: engine unchanged; tests show field named + unticked = 0, + ticked = charge, column agrees. The tests use the stock Employee tick box `unsubscribed` as the stand-in.
4. Default ticked: **not possible from code.** The Custom Field exists only on the DTC site. Options: (a) Surbhi sets Default = 1 in Customize Form on the DTC site (existing employees are not changed, tick them herself); (b) add the Custom Field to `payroll_fields.py` with default 1 - this would create it on every tenant, which is a new mechanism, so not done.

## Tests (site test075, own container)
test_salary_report 18 OK (2 skipped, as before); test_payroll_flags 9 OK; test_payroll_month 29 OK; test_grooming_066 64 OK; test_grooming_cap_066 42 OK; test_grooming_erase_066 25 OK; test_pay_slip_marks_067 18 OK. `check_app_integrity.py`: 837 checks OK.

## Subtract pass
Removed: a planned rupee-value property (put the figure on the summary directly) and a planned engine test file (report tests cover the engine path).

## Gaps
- Acceptable simplification: an absent day carrying a late-window quarter shows its quarter in the column although the engine only charges quarters above four on absent days. Cannot happen in practice (a punch inside the window means the person was in).
- Not verified: Excel export on the DTC site itself; no production data touched.
