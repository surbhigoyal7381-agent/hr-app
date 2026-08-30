# ERPNext — subject matter reference (from an HR product's point of view)

Source of truth: <https://docs.frappe.io/erpnext/introduction> and the ERPNext
source at the version pinned in `hrms/pyproject.toml`
(`erpnext>=17.0.0-dev,<18.0.0`).

Frappe HR **installs on top of ERPNext**. Half of what looks like "HR" is
actually ERPNext. Getting that boundary wrong is the single most common cause
of duplicated doctypes in this codebase.

---

## 1. Module map

ERPNext ships 21 modules (`erpnext/modules.txt`):

Accounts · CRM · Buying · Projects · Selling · Setup · Manufacturing · Stock ·
Support · Utilities · Assets · Portal · Maintenance · Regional ·
ERPNext Integrations · Quality Management · Communication · Telephony ·
Bulk Transaction · Subcontracting · EDI

Rough sizes: Accounts ~191 doctypes, Stock ~80, Manufacturing ~49, Setup ~40,
Assets ~26, Selling ~20, Buying ~19, Projects ~15, Subcontracting ~13.

Documentation URLs follow `https://docs.frappe.io/erpnext/<page-slug>`; the
older versioned manual lives at
`https://docs.frappe.io/erpnext/v14/user/manual/en/<module>/<page>`.

---

## 2. 🔴 The boundary: what ERPNext owns, not Frappe HR

**In upstream Frappe HR these doctypes do not exist. They are ERPNext Setup
doctypes:**

`Employee` · `Department` (tree) · `Designation` · `Branch` · `Company` ·
`Holiday List` · `Holiday` · `Employee Education` ·
`Employee External Work History` · `Employee Internal Work History` ·
`Employee Group` · `Vehicle` · `Driver` · `Global Defaults`

Frappe HR extends `Employee` with custom fields and `doc_events`; it does not
redefine it.

> ### ⚠️ This repo currently violates that boundary
>
> The vendored fork defines its **own** copy of all nine of these under
> `hrms/hrms/hr/doctype/` (module `HR`): `employee`, `department`,
> `designation`, `branch`, `company`, `holiday`, `holiday_list`,
> `employee_education`, `employee_external_work_history`,
> `employee_internal_work_history`. The fork's `Employee` declares **90
> fields**; ERPNext's declares **109**. That gap is the drift, and it is not
> documented anywhere else.
>
> Two apps declaring the same doctype name means **the last one migrated wins**
> and the loser's fields quietly disappear from the schema. Any proposal that
> touches Employee, Department, Designation, Branch, Company or Holiday List
> must say explicitly which definition it is editing and what happens on the
> next `bench migrate`. Flag it as a risk every time — do not silently pick one.

Also note upstream Frappe HR has **re-grouped its modules** into
HR Setup / Tenure / Recruitment / Shift and Attendance / Leaves / Expenses /
Performance / Payroll / Tax and Benefits / HR, while the fork still uses the
older three: HR / Payroll / Performance Management. Any future upstream merge
will collide on module assignment.

---

## 3. Where HR touches ERPNext accounting

| HR document | ERPNext effect | Doctypes involved |
|---|---|---|
| Salary Slip (submit) | Salary accrual booked | Journal Entry, GL Entry, Account, Cost Center |
| Payroll Entry (submit) | Accrual + bank entry for the run | Journal Entry, Mode of Payment, Bank Account |
| Expense Claim (submit) | Payable to employee + expense booking | GL Entry, Account, Payment Entry |
| Employee Advance | Advance ledger, offset against claims | Journal Entry, Payment Entry |
| Leave Encashment | Creates Additional Salary → next slip | Salary Component |
| Gratuity (submit) | Payable booking | Journal Entry |
| Timesheet → Salary Slip | Hours priced into pay | Timesheet, Activity Type, Activity Cost |
| Employee as party | Payments to employees | Party Type "Employee", Party Link |
| Vehicle Log | Fleet running cost | Vehicle, Expense Claim |
| Employee Referral bonus | Additional Salary | Salary Component |

Accounting dimensions (`Cost Center`, `Project`, `Accounting Dimension`) flow
through payroll: `Employee Cost Center` — a child table on **Salary Structure
Assignment**, not on Employee — splits one employee's cost across cost centres
for a given assignment period. Any payroll change that adds a component must state which account and
cost centre it posts to.

---

## 4. ERPNext concepts an HR feature spec keeps needing

**Company** — multi-company is the default assumption. Every HR doctype that
holds money or org structure carries `company`. Chart of Accounts, Fiscal Year,
Cost Centers and Holiday Lists are per company.

**Fiscal Year vs Payroll Period** — different things. Fiscal Year drives
accounting; Payroll Period drives income-tax computation. In India they both
run Apr–Mar, which hides bugs until someone configures them differently.

**Naming Series** — document numbering. India Compliance imposes hard rules on
naming for anything reported to GSTN (see `india-compliance.md` §7).

**Party Type / Party Link** — an Employee can be paid as a party. This is how
Expense Claim and Employee Advance settle through Payment Entry.

**Accounts Settings** — carries the Audit Trail switch (once on, cannot be
turned off) and the "delete accounting/stock ledger entries" options that
Audit Trail disables permanently.

**Tax Withholding Category** — TDS/TCS engine. Used for vendor payments, and
relevant when an HR flow pays a non-employee (contractor, consultant).

**Projects & Timesheet** — Timesheet links employee hours to Project/Task and
can be billed into a Sales Invoice or priced into a Salary Slip.

**Assets** — asset issue and recovery at exit is Asset Movement, referenced by
`Full and Final Asset` in the Full and Final Statement.

---

## 5. Rules of engagement

1. Before creating any doctype or custom field, search ERPNext **and** Frappe HR
   for an existing one. In this codebase the failure mode is not "missing
   feature", it is "third parallel implementation".
2. Use the ORM: `frappe.get_doc`, `frappe.get_all`, `doc.insert`, `doc.submit`,
   `frappe.db.set_value`. Raw SQL only where the ORM genuinely cannot express
   the query, and then say why in the proposal.
3. Anything that writes GL entries must be reversible on cancel. Submittable +
   `on_cancel` that unwinds, not a delete.
4. Multi-company and row-level permission scoping are non-negotiable for every
   new list view, report and whitelisted API.
