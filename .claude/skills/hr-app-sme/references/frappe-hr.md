# Frappe HR — subject matter reference

Source of truth for this file: the Frappe HR documentation at
<https://docs.frappe.io/hr/introduction> and the `hrms` app source vendored in
this repo at `hrms/hrms/`. Where the two disagree, **the vendored source wins**
— this repo runs a fork, not stock Frappe HR (see `hr-app-product.md`).

Version in this repo: Frappe Framework and ERPNext `>=17.0.0-dev,<18.0.0`
(pinned in `hrms/pyproject.toml`).

---

## 1. How to use the documentation site

Page URLs on `docs.frappe.io/hr` follow one rule: **the doctype name in
lower-case kebab-case.**

| Doctype | Page |
|---|---|
| Leave Type | `https://docs.frappe.io/hr/leave-type` |
| Leave Policy Assignment | `https://docs.frappe.io/hr/leave-policy-assignment` |
| Salary Structure Assignment | `https://docs.frappe.io/hr/salary-structure-assignment` |
| Income Tax Slab | `https://docs.frappe.io/hr/income-tax-slab` |
| Shift Type | `https://docs.frappe.io/hr/shift-type` |
| Appraisal Cycle | `https://docs.frappe.io/hr/appraisal-cycle` |
| Job Requisition | `https://docs.frappe.io/hr/job-requisition` |

So for any doctype in §3 you can construct the doc URL directly. Guide pages
that are not doctypes use the same kebab-case rule on their title, e.g.
`payroll-setup`, `auto-attendance`, `using-auto-attendance`, `roster`,
`how-to-process-payroll-in-frappehr`, `income-tax-calculation-in-frappehr`,
`how-to-encash-unused-leaves-using-salary-slips`,
`integrating-frappe-hr-with-biometric-attendance-devices`,
`interview-management`, `employee-attendance-tool`, `appraisal-overview-report`,
`leave-allocation-after-compensatory-leave-request`.

Older ERPNext-era HR manual pages still exist under
`docs.frappe.io/erpnext/v13|v14/user/manual/en/human-resources/…`. Treat those
as historical — the v14+ behaviour lives in the `hrms` app.

> **Note when citing:** always name the doctype, not just the URL. The doctype
> name is stable; doc URLs occasionally move.

---

## 2. The 13 functional areas

| Area | Core doctypes | What it does |
|---|---|---|
| Employee lifecycle | Employee, Employee Onboarding, Employee Promotion, Employee Transfer, Employee Separation, Exit Interview, Full and Final Statement | Hire-to-exit record of a person |
| Org structure | Company, Department (tree), Designation, Branch, Employee Grade, Employment Type | Who reports where; drives permissions and defaults |
| Leave | Leave Type, Leave Policy, Leave Policy Assignment, Leave Period, Leave Allocation, Leave Application, Leave Ledger Entry, Leave Encashment, Compensatory Leave Request, Leave Block List, Leave Control Panel, Leave Adjustment | Entitlement, application, balance |
| Attendance | Attendance, Attendance Request, Employee Checkin, Employee Attendance Tool, Upload Attendance | Daily presence |
| Shift | Shift Type, Shift Assignment, Shift Request, Shift Schedule, Shift Assignment Tool, Shift Location | Rostering and auto-attendance |
| Payroll | Salary Component, Salary Structure, Salary Structure Assignment, Payroll Entry, Salary Slip, Payroll Period, Payroll Settings, Additional Salary, Retention Bonus, Employee Incentive, Salary Withholding, Arrear, Payroll Correction | Pay run |
| Tax & benefits | Income Tax Slab, Employee Tax Exemption Declaration, Employee Tax Exemption Proof Submission, Employee Other Income, Employee Benefit Application, Employee Benefit Claim, Gratuity, Gratuity Rule | Statutory and flexible pay |
| Expenses & advances | Expense Claim, Expense Claim Type, Expense Claim Detail, Expense Claim Advance, Expense Taxes and Charges, Employee Advance, Travel Request | Reimbursement, integrated with ERPNext accounting |
| Performance | Appraisal, Appraisal Cycle, Appraisal Template, KRA, Goal (tree), Employee Performance Feedback, Employee Feedback Criteria | Goals, KRAs, 360° feedback |
| Recruitment | Job Requisition, Staffing Plan, Job Opening, Job Applicant, Interview, Interview Feedback, Job Offer, Appointment Letter, Employee Referral | Requisition-to-offer |
| Training | Training Program, Training Event, Training Result, Training Feedback | Learning records |
| Fleet | Vehicle (ERPNext), Vehicle Log, Vehicle Service | Company vehicles |
| Overtime | Overtime Type, Overtime Slip, Overtime Details | Overtime capture and payment |

---

## 3. Doctype inventory (as vendored in this repo)

Flags: `child` = child table, `submittable` = has draft/submitted/cancelled
lifecycle, `single` = one record only, `tree` = nested set.

### `hrms/hr` — 127 doctypes

Appointment Letter; Appointment Letter content [child]; Appointment Letter Template; Appraisal [submittable]; Appraisal Cycle; Appraisal Goal [child]; Appraisal KRA [child]; Appraisal Template; Appraisal Template Goal [child]; Appraisee [child]; Attendance [submittable]; Attendance Request [submittable]; Branch; Company; Compensatory Leave Request [submittable]; Daily Work Summary; Daily Work Summary Group; Daily Work Summary Group User [child]; Department [tree]; Department Approver [child]; Designation; Designation Skill [child]; Earned Leave Schedule [child]; Employee; Employee Advance [submittable]; Employee Attendance Tool [single]; Employee Boarding Activity [child]; Employee Checkin; Employee Education [child]; Employee External Work History [child]; Employee Feedback Criteria; Employee Feedback Rating [child]; Employee Grade; Employee Grievance [submittable]; Employee Health Insurance; Employee Internal Work History [child]; Employee Onboarding [submittable]; Employee Onboarding Template; Employee Performance Feedback [submittable]; Employee Promotion [submittable]; Employee Property History [child]; Employee Referral [submittable]; Employee Separation [submittable]; Employee Separation Template; Employee Skill [child]; Employee Skill Map; Employee Training [child]; Employee Transfer [submittable]; Employment Type; Exit Interview [submittable]; Expected Skill Set [child]; Expense Claim [submittable]; Expense Claim Account [child]; Expense Claim Advance [child]; Expense Claim Detail [child]; Expense Claim Type; Expense Taxes and Charges [child]; Full and Final Asset [child]; Full and Final Outstanding Statement [child]; Full and Final Statement [submittable]; Goal [tree]; Grievance Type; Holiday [child]; Holiday List; Holiday List Assignment [submittable]; HR Settings [single]; Identification Document Type; Interest; Interview [submittable]; Interview Detail [child]; Interview Feedback [submittable]; Interview Type; Interviewer [child]; Job Applicant; Job Applicant Source; Job Offer [submittable]; Job Offer Term [child]; Job Offer Term Template; Job Opening; Job Opening Template; Job Requisition; KRA; Leave Adjustment [submittable]; Leave Allocation [submittable]; Leave Application [submittable]; Leave Block List; Leave Block List Allow [child]; Leave Block List Date [child]; Leave Control Panel [single]; Leave Encashment [submittable]; Leave Ledger Entry [submittable]; Leave Period; Leave Policy [submittable]; Leave Policy Assignment [submittable]; Leave Policy Detail [child]; Leave Type; Offer Term; Overtime Details [child]; Overtime Salary Component [child]; Overtime Slip [submittable]; Overtime Type; Purpose of Travel; PWA Notification; Shift Assignment [submittable]; Shift Assignment Tool [single]; Shift Location; Shift Request [submittable]; Shift Schedule [submittable]; Shift Schedule Assignment; Shift Type; Skill; Skill Assessment [child]; Staffing Plan [submittable]; Staffing Plan Detail [child]; Training Event [submittable]; Training Event Employee [child]; Training Feedback [submittable]; Training Program; Training Result [submittable]; Training Result Employee [child]; Travel Itinerary [child]; Travel Request [submittable]; Travel Request Costing [child]; Upload Attendance [single]; Vehicle Log [submittable]; Vehicle Service [child]; Vehicle Service Item

### `hrms/payroll` — 47 doctypes

Account; Additional Salary [submittable]; Arrear [submittable]; Bulk Salary Structure Assignment [single]; Cost Center; Employee Benefit Application [submittable]; Employee Benefit Application Detail [child]; Employee Benefit Claim [submittable]; Employee Benefit Detail [child]; Employee Benefit Ledger; Employee Cost Center [child]; Employee Incentive [submittable]; Employee Other Income [submittable]; Employee Tax Exemption Category; Employee Tax Exemption Declaration [submittable]; Employee Tax Exemption Declaration Category [child]; Employee Tax Exemption Proof Submission [submittable]; Employee Tax Exemption Proof Submission Detail [child]; Employee Tax Exemption Sub Category; Fiscal Year; Gratuity [submittable]; Gratuity Applicable Component [child]; Gratuity Rule; Gratuity Rule Slab [child]; Income Tax Slab [submittable]; Income Tax Slab Other Charges [child]; Mode of Payment; Payroll Correction [submittable]; Payroll Correction Child [child]; Payroll Employee Detail [child]; Payroll Entry [submittable]; Payroll Period; Payroll Period Date [child]; Payroll Settings [single]; Retention Bonus [submittable]; Salary Component; Salary Component Account [child]; Salary Detail [child]; Salary Slip [submittable]; Salary Slip Leave [child]; Salary Slip Loan [child]; Salary Slip Timesheet [child]; Salary Structure [submittable]; Salary Structure Assignment [submittable]; Salary Withholding [submittable]; Salary Withholding Cycle [child]; Taxable Salary Slab [child]

### `hrms/performance_management` — 37 doctypes (fork-only, see §8)

PMS Action Item; PMS Additional Manager [child]; PMS Business Goal; PMS Calibration Adjustment [child]; PMS Calibration Scope [child]; PMS Calibration Session; PMS Check In; PMS Check In Agenda [child]; PMS Company Value; PMS Cycle; PMS Cycle Applicability [child]; PMS Cycle Stage Deadline [child]; PMS Dev Goal Link [child]; PMS Dev Review [child]; PMS Development Goal; PMS Dialogue Action [child]; PMS Goal Progress Update [child]; PMS Goal Rating [child]; PMS Goal Value Tag [child]; PMS KPI [child]; PMS KPI Rating [child]; PMS Leadership Principle [child]; PMS LP Rating [child]; PMS Manager Assessment; PMS Objective Link; PMS Rating Level [child]; PMS Rating Scale; PMS Review Record; PMS Review Template; PMS Self Evidence [child]; PMS Self Review; PMS Self Review Achievement [child]; PMS Support Plan Action [child]; PMS Talent Flag; PMS Template Section [child]; PMS Upward Feedback; PMS Values Rating [child]

---

## 4. Mechanisms you must not get wrong

### 4.1 Leave balance is a ledger, not a field

There is **no stored balance field**. Balance is derived by summing
**Leave Ledger Entry** rows. Leave Ledger Entry is submittable, and its fields
are: `employee`, `leave_type`, `transaction_type`, `transaction_name`,
`leaves` (positive = credit, negative = debit), `from_date`, `to_date`,
`is_carry_forward`, `is_expired`, `is_lwp`, `holiday_list`, `company`.

Anything that changes a balance writes ledger entries:

| Source | Ledger effect |
|---|---|
| Leave Allocation (submit) | + new leaves, + carry-forward row (separate, flagged `is_carry_forward`) |
| Leave Application (submit) | − leaves |
| Leave Encashment (submit) | − encashed leaves, and creates an Additional Salary |
| Compensatory Leave Request (submit) | + comp-off, via a Leave Allocation |
| Expiry (scheduled job) | − expired carry-forward, flagged `is_expired` |
| Cancel of any of the above | reversing entries |

**Rule for any feature touching leave:** never compute or cache a balance
without defining how the cache is invalidated on ledger writes. Use
`hrms.hr.doctype.leave_application.leave_application.get_leave_balance_on()`
rather than re-deriving the maths.

### 4.2 Earned leave accrues on a schedule

`Leave Type.is_earned_leave` allots pro-rata by `earned_leave_frequency`
(Monthly / Quarterly / Half-Yearly / Yearly) through a scheduled job that
updates Leave Allocation. Rounding is controlled by `rounding` on Leave Type.
A feature that assumes "allocation is fixed at assignment time" is wrong for
earned leave types.

### 4.3 Payroll chain

```
Salary Component ──► Salary Structure (earnings + deductions, formulas)
                        │
Income Tax Slab ────────┼──► Salary Structure Assignment (employee, from_date,
                        │        base, variable, income_tax_slab)
                        ▼
                   Payroll Entry (period, company, filters)
                        │  Get Employees → Create Salary Slips (draft)
                        ▼
                   Salary Slip (submit) ──► Journal Entry / Bank Entry (ERPNext)
```

Key rules:

- Salary Structure Assignment is **dated**. Multiple assignments per employee
  over time are normal; always pick the one effective on the slip's start date.
- Salary Component with `variable_based_on_taxable_salary` triggers the
  automatic income-tax engine — it reads Payroll Period, Income Tax Slab,
  Employee Tax Exemption Declaration, Employee Other Income, and previously
  submitted slips in the same Payroll Period.
- Income Tax Slab rows may carry **conditions** written against fields of
  Employee, Salary Structure, Salary Structure Assignment and Salary Slip.
- `Salary Withholding` holds pay for a cycle without deleting the slip.
- Payroll Period ≠ Fiscal Year. Tax is computed over the Payroll Period.

### 4.4 Auto attendance

`Employee Checkin` rows + `Shift Type` auto-attendance settings → `Attendance`.
Attendance is only marked for check-ins created **after** the shift is set up
and assigned. Relevant Shift Type fields: `enable_auto_attendance`,
`determine_check_in_and_check_out`, `working_hours_calculation_based_on`,
`begin_check_in_before_shift_start_time`,
`allow_check_out_after_shift_end_time`, `working_hours_threshold_for_half_day`,
`working_hours_threshold_for_absent`, `process_attendance_after`,
`last_sync_of_checkin`. `last_sync_of_checkin` is the watermark — moving it
backwards re-processes, moving it forwards silently skips days.

### 4.5 Expense Claim posts to accounts

Expense Claim is an accounting document. On submit it writes GL entries against
the payable account and the expense accounts on `Expense Claim Detail`, offsets
linked `Employee Advance` rows, and can be paid through a Payment Entry. Never
add an expense-like flow with a parallel doctype — extend Expense Claim Type
and Expense Claim Detail.

### 4.6 HR Settings is the config surface

`HR Settings` (single) carries the org-level switches. Current fields include:
`retirement_age`, `emp_created_by`, `expense_approver_mandatory_in_expense_claim`,
`leave_approver_mandatory_in_leave_application`,
`show_leaves_of_all_department_members_in_calendar`, `auto_leave_encashment`,
`role_allowed_to_create_backdated_leave_application`,
`restrict_backdated_leave_application`, `send_leave_notification`,
`leave_approval_notification_template`, `leave_status_notification_template`,
`standard_working_hours`, `send_holiday_reminders`,
`send_work_anniversary_reminders`, `send_birthday_reminders`,
`send_interview_reminder`, `send_interview_feedback_reminder`,
`check_vacancies`, `exit_questionnaire_web_form`,
`allow_multiple_shift_assignments`, `allow_employee_checkin_from_mobile_app`,
`allow_geolocation_tracking`,
`unlink_payment_on_cancellation_of_employee_advance`,
`prevent_self_leave_approval`, `prevent_self_expense_approval`.

**Before proposing a new setting, check this list.** Org-level config belongs
here or in Frappe Global Defaults — never hardcoded.

---

## 5. Permissions model

- **Employee ↔ User** link drives self-service. `Employee.user_id`.
- `Employee.reports_to` builds the reporting chain.
- **`leave_approver` and `expense_approver` are Custom Fields, not native
  Employee fields.** Frappe HR adds them in `hrms/hrms/setup.py` via
  `create_custom_fields`, alongside `leave_approvers` and `expense_approvers`
  child tables on Department (child doctype `Department Approver`). Verified:
  neither ERPNext's Employee (109 fields) nor this fork's Employee (90 fields)
  declares them in its JSON. So they exist only after the app's `setup` has run
  — do not assume them in a fresh-site test or a raw doctype read.
- Standard roles: Employee, Employee Self Service, HR User, HR Manager,
  Leave Approver, Expense Approver, Interviewer.
- Row-level scoping uses **User Permission** on Company / Department /
  Employee. Multi-company scoping for a CXO persona is a User Permission
  problem, not a query-filter problem.
- `ignore_permissions=True` in a whitelisted method removes **all** row-level
  scoping. Every use needs an explicit justification and an explicit
  replacement check.

---

## 6. Extension points

| Need | Frappe-native way |
|---|---|
| Extra field on a stock doctype | Custom Field via fixtures or `create_custom_fields` |
| Extra behaviour on save/submit | `doc_events` hook in `hooks.py` |
| Replace a controller method | `override_doctype_class` |
| Extra API for the portal/PWA | `@frappe.whitelist()` in the custom app |
| Recurring job | `scheduler_events` in `hooks.py` |
| Country-specific behaviour | `regional/<country>/` + `regional_overrides` |
| Report | Query Report or Script Report in the owning module |

Do **not**: write raw SQL where the ORM works, create a parallel doctype that
duplicates a stock one, or add a feature flag / compatibility shim.

---

## 7. India-specific behaviour already in Frappe HR

`hrms/hrms/regional/india/` adds, on install for an Indian company:

- **Salary Component** custom field `component_type`:
  Provident Fund / Additional Provident Fund / Provident Fund Loan /
  Professional Tax.
- **Employee** custom fields: `ifsc_code`, `pan_number`, plus PF/ESI/UAN
  identifiers used by statutory reports.
- **Gratuity Rule** for India created automatically
  (Payment of Gratuity Act slabs).
- `regional/india/utils.py`: HRA exemption
  (`calculate_annual_eligible_hra_exemption`, `calculate_hra_exemption`,
  `validate_house_rent_dates`) and
  `calculate_tax_with_marginal_relief` for the new tax regime.
- Default Indian salary components seeded from
  `regional/india/data/salary_components.json`.

This is **payroll-side India compliance**. GST-side compliance is a different
app — see `india-compliance.md`.

---

## 8. This repo is a fork — know the drift

`hrms/` is committed into this monorepo, not pulled with `bench get-app`.
`performance_management` (37 PMS doctypes), `grace_group` setup scripts, PMS
portal routes and the Alvoraa branding are **local additions that do not exist
upstream**. Consequences:

- Upstream documentation will not describe PMS doctypes. Read the source.
- Anything that regenerates the app from upstream silently deletes them.
- When quoting stock behaviour, verify against `hrms/hrms/…` in this repo
  before asserting it.
