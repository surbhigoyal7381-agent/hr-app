# 04 — Payroll

Frappe HR payroll handles all of this by configuration, except two additions: an ESI component pair (Frappe HR India ships PF and Professional Tax but no ESI) and one custom field for the ESI number. PF and ESI filing stays with the client's third party for now; the demo shows the amounts on the slip and the statutory reports, so the client can see that moving it in-house is a switch, not a project.

Statutory figures below are the commonly used ones. **They are marked "verify" because I cannot confirm today's values.** Check them on the EPFO and ESIC sites before the demo.

## 1. Payroll Settings

| Setting | Value | Why |
|---|---|---|
| Calculate Payroll Working Days Based On | Attendance | This is the whole point: punches drive pay |
| Consider Unmarked Attendance As | Absent | Forces the attendance process to be complete before payroll |
| Include holidays in Total no. of Working Days | 1 | Stores work holidays; keeps the month at 30/31 days |
| Consider marked attendance on holidays | 1 | Festival-day work counts as present |
| Daily Wages Fraction For Half Day | 0.5 | |
| Email Salary Slip to Employee | 0 for the demo | |
| Encrypt Salary Slips in Emails | on, password = date of birth | Show as a talking point |

## 2. Salary Components

Type E = Earning, D = Deduction, EC = Employer Contribution. Abbreviations are what formulas use.

| Component | Abbr | Type | Formula / rule | Depends on payment days | Statistical |
|---|---|---|---|---|---|
| Basic | B | E | `base * 0.50` | yes | no |
| House Rent Allowance | HRA | E | `B * 0.40` | yes | no |
| Conveyance Allowance | CA | E | `1600` | yes | no |
| Special Allowance | SA | E | `base - B - HRA - CA` (balancing figure) | yes | no |
| Gold Incentive | INC_G | E | Additional Salary only (file 05) | no | no |
| Diamond Incentive | INC_D | E | Additional Salary only | no | no |
| Silver & Fashion Incentive | INC_S | E | Additional Salary only | no | no |
| Platinum & Gemstone Incentive | INC_P | E | Additional Salary only | no | no |
| Store Performance Incentive | INC_ST | E | Additional Salary only (non-selling front staff) | no | no |
| Festival Working Allowance | FWA | E | Additional Salary, entered by HR for holiday work | no | no |
| Provident Fund | PF | D | `min(B, 15000) * 0.12` — condition `pf_applicable` (see §3) | no | no. `component_type` = Provident Fund |
| Employee State Insurance | ESI | D | `gross_pay * 0.0075` — condition `esi_applicable` | no | no. **New**, `component_type` = ESI (new option) |
| Professional Tax | PT | D | `0` for Delhi, Haryana, UP and Chandigarh; not levied in these states (verify). Keep the component so the slip shows the line as 0. | no | no. `component_type` = Professional Tax |
| Late Coming Deduction | LCD | D | Additional Salary created by the Attendance Deduction (file 03) | no | no |
| Income Tax | IT | D | `variable_based_on_taxable_salary` = 1, uses the Income Tax Slab | no | no |
| Employer PF Contribution | EPF_ER | EC | `min(B, 15000) * 0.12` (8.33% EPS + 3.67% EPF; show as one line) | no | no |
| Employer ESI Contribution | ESI_ER | EC | `gross_pay * 0.0325` — condition `esi_applicable` | no | no |

Rates to verify: PF 12% + 12% on basic capped at 15,000; ESI 0.75% employee, 3.25% employer, wage ceiling 21,000 gross per month.

## 3. The two custom fields (build B2 in file 10)

| Field | On | Type | Purpose |
|---|---|---|---|
| `esi_number` | Employee (custom field, India regional group) | Data | ESI insurance number, shown on the slip |
| `esi_applicable` | Salary Structure Assignment | Check, default from base ≤ 21,000 at assignment | Condition for the two ESI components. ESIC rules keep a person covered until the contribution period ends even if wages rise, so it must be a switch, not a live formula. |
| `pf_applicable` | Salary Structure Assignment | Check, default 1 | Lets HR exclude an employee (e.g. above ceiling and opted out) |

Also add option `ESI` to the existing `component_type` Select on Salary Component so a future ESI report can key off it, and add report **ESI Deductions** (copy of Provident Fund Deductions filtered on `component_type = ESI`, columns: employee, ESI number, gross, employee ESI, employer ESI).

## 4. Salary Structures (one per grade)

All five structures have the same components. Only `base` differs, and it comes from the Salary Structure Assignment. Incentive and deduction components are present with amount 0 so the slip shows the line when an Additional Salary lands.

| Structure | Grade | Payroll frequency | Notes |
|---|---|---|---|
| PPJ-G1 | G1 Support | Monthly | ESI applies to all; PF applies |
| PPJ-G2 | G2 Executive | Monthly | ESI applies below 21,000 |
| PPJ-G3 | G3 Senior Executive | Monthly | |
| PPJ-G4 | G4 Manager | Monthly | |
| PPJ-G5 | G5 Head and G6 | Monthly | no incentive components except Store Performance Incentive for Store In-charges |

Salary Structure Assignment for all 400: `from_date` = 2026-04-01, `base` = `monthly_ctc` from the CSV, `income_tax_slab` = "India New Regime FY 2026-27" (create with the slabs of the new regime; verify slabs), `esi_applicable` = 1 when base ≤ 21,000. Use **Bulk Salary Structure Assignment** grouped by grade.

## 5. Payroll Period and Income Tax Slab

- Payroll Period `FY 2026-27`: 2026-04-01 to 2027-03-31.
- Income Tax Slab `India New Regime FY 2026-27`: enter the current new-regime slabs and standard deduction. **Verify with a CA**; I am not certain of the FY27 figures.

## 6. Payroll runs for the demo

| Payroll Entry | Period | Employees | State | What it demonstrates |
|---|---|---|---|---|
| PPJ July 2026 | 2026-07-01 to 2026-07-31 | all 400, branch-wise selection allowed | Submitted, slips submitted | First attendance-based run. PPJ-0058's July slip shows no LCD (all from leave) |
| PPJ August 2026 | 2026-08-01 to 2026-08-31 | all 400 | Submitted | PPJ-0058's slip shows LCD for 0.5 day. Incentives for July sales land here (file 05). PPJ-0054's slip shows Gold Incentive. |
| PPJ September 2026 | 2026-09-01 to 2026-09-30 | all 400 | Draft, not created until the demo | Live: HR clicks "Get Employees", validation lists employees with unmarked attendance (September is only processed to the 6th), showing the guard rail |

On Payroll Entry set `validate_attendance` = 1.

## 7. Payslip for the persona

PPJ-0054 Suresh Sethi, August 2026, base 37,500 (check the CSV for the exact figure):

| Line | Amount (illustrative) |
|---|---|
| Basic | 18,750 × payment days / 31 |
| HRA | 7,500 × ratio |
| Conveyance | 1,600 × ratio |
| Special Allowance | balancing |
| Gold Incentive | 9,200 (July sales 106% of target, file 05) |
| PF | 1,800 |
| ESI | 0 (above ceiling) |
| Professional Tax | 0 |
| Late Coming Deduction | 0 (0.5 day came from Casual Leave) |
| Net pay | computed |

PPJ-0058 August: same structure, plus `Late Coming Deduction` = base / 31 × 0.5, with the slip line linking to the Attendance Deduction record.

## 8. Reports for the demo

Salary Register (August, by branch), Provident Fund Deductions, ESI Deductions (new), Employee CTC Break Up, Bank Remittance. Number cards: Total Payroll Cost this month, Employees on ESI.

## 9. Known blocker

Payslips with income tax fail on the current `dev` code because of the regional override wrapper bug described in file 10, B0. Apply that hotfix before running Block 4 on the tenant.

## 10. Verification after this block

- 400 Salary Structure Assignments, 400 slips for July and August, all submitted, no "Leave Without Pay does not match" errors.
- PPJ-0058 August slip: `leave_without_pay` = 0 (the LCD is a deduction line, not LWP days), `Late Coming Deduction` > 0.
- Provident Fund Deductions report totals = sum of PF lines. ESI Deductions report lists exactly the 146 ESI-eligible employees.
