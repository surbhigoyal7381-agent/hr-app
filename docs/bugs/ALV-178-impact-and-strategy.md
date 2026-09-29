# ALV-178 — "Create Payment" fails on Expense Claim: impact analysis and fix strategy

Status: **analysis and strategy only. No product code changed.** Waiting for Surbhi's
approval (CLAUDE.md §2 step 3).
Worktree: `.claude/worktrees/alv-178`, branch `fix/alv-178-payment-entry`, from `origin/dev` 24ffbf4.
Written 29 Sep 2026.

---

## 0. The answer first

**The bug is much bigger than one button.** Commit **48f5439** (31 Jul 2026, titled
"Performance module UI…") tried to make our Frappe HR copy run *without ERPNext*. It did
that by switching off every place Frappe HR talks to accounting. ERPNext is installed on
every tenant, so none of that was needed, and all of it is still switched off on `dev`
and on `main` today.

What is broken right now, on every tenant, dev and production:

| # | What people see | Why |
|---|---|---|
| 1 | "Create Payment" fails on Expense Claim, Employee Advance, Leave Encashment and Gratuity | `get_payment_entry_for_employee` was deleted |
| 2 | A Payment Entry cannot point at an Expense Claim or Employee Advance at all, even made by hand | the Payment Entry override was removed, so ERPNext only allows "Journal Entry" as a reference for an employee |
| 3 | **Expense claims, leave encashments and gratuities post nothing to the accounts** | `make_gl_entries` / `create_gl_entries` were replaced with `pass` |
| 4 | An expense claim never becomes "Paid", even when it is paid by Journal Entry | the Payment Entry / Journal Entry hooks were removed, **and** the "how much was paid" function was changed to always return 0 |
| 5 | Full & Final Statements never become "Paid"; salary withholding never shows "released" | the Journal Entry hooks were removed |
| 6 | Cancelling a payroll Journal Entry leaves salary slips pointing at the cancelled entry | the Journal Entry `on_cancel` hook was removed |
| 7 | Payroll entries and expense claims lose accounting dimensions (e.g. branch, department) | the dimension lookup was replaced with an empty list, and the hook that adds dimension fields was removed |
| 8 | "Return" on an Employee Advance crashes | the bank/cash account lookup was replaced with `None` |
| 9 | **Four HR reports and the Shift Assignment Tool ignore User Permissions** | `build_qb_match_conditions` was replaced with an empty filter (a security gap — see §3.4) |

**Good news:** production has no live paying customer yet (dtc goes live in the first week
of October), so the amount of wrong data should be small. But dtc goes live on this code
unless we fix it first.

**Second finding you need before approving: this fix is already half-built.** Slice
`050-erpnext-restore` (branch `slice/050-erpnext-restore`, commit 85cd29b, 26 Sep, local
only, not pushed) restores the four payment/ledger controllers and the three override
files. It does **not** restore the Payment Entry / Journal Entry hooks, so after 050 alone
the button works but the claim still never becomes "Paid". It also has a known bug (the
Employee override, see §6.3) that another session flagged on 27 Sep, and a staged,
uncommitted fix for it sits in that worktree. **I recommend ALV-178 takes over and finishes
050, rather than doing the same work twice.** That needs your word, because 050 belongs to
another session.

---

## 1. Everything 48f5439 changed under `hrms/`

The commit touched 226 files. Under `hrms/` it did four kinds of thing:

- added the PMS module (`performance_management/`, `pms/`, `www/pms-*`) — **kept, deliberate**;
- added 14 stub copies of ERPNext doctypes (Company, Employee, Account, …) and pointed
  imports at them — **already undone** by d0469c8 (24 Aug);
- stubbed out ERPNext calls in controllers, overrides, reports and patches — **mostly still
  there**, this bug;
- removed hooks from `hooks.py` — **still missing**, this bug.

Classes: **(a)** accidental loss, must be restored · **(b)** deliberately replaced by our own
code, found the replacement · **(c)** obsolete or no effect · **(done)** already restored by a
later commit.

### 1.1 `hooks.py`

| Removed or changed | Class | Evidence / note |
|---|---|---|
| `required_apps = ["frappe/erpnext"]` | (a) | Removed only to allow the no-ERPNext experiment. ERPNext is on every site (Dockerfile, provision_tenant.sh). Upstream v16 has it. |
| `doctype_js` for Employee, Company, Department, Timesheet, Payment Entry, Journal Entry, Delivery Trip, Bank Transaction | (a) | The eight JS files still exist in `hrms/public/js/erpnext/` but are never loaded. Replaced in the dict by the two PMS entries, which we keep. |
| `setup_wizard_complete = hrms.subscription_utils.update_erpnext_access` | (c) | Only acts on `*.frappehr.com` sites; does nothing for us. Restore anyway to match upstream (no effect). |
| `override_doctype_class` (Employee, Timesheet, Payment Entry, Project) | (a) | No replacement anywhere (grepped `alvoraa_portal`, `alvoraa_goals`). `alvoraa_portal/hooks.py` has its own `override_doctype_class` for "CRM Invitation" only; Frappe merges the two. |
| `doc_events["Timesheet"]` validate_active_employee | (a) | |
| `doc_events["Payment Entry"]` on_submit/on_cancel/on_update_after_submit → `update_payment_for_expense_claim` | (a) | **Core of the "never Paid" bug.** |
| `doc_events["Unreconcile Payment"]` on_submit | (a) | |
| `doc_events["Journal Entry"]` validate (claim over-payment check), on_submit (claim paid, F&F paid, withholding released), on_update_after_submit, on_cancel (+ salary slip unlink) | (a) | |
| `doc_events["Loan"]` validate | (a) | Lending app is not installed, so no effect today. Restore for parity. |
| `advance_payment_payable_doctypes` (Leave Encashment, Gratuity, Employee Advance) | (a) | ERPNext reads this (`accounts/utils.py`) to write Advance Payment Ledger rows, which is how an Employee Advance learns it was paid. |
| `invoice_doctypes` (Expense Claim) | (a) | ERPNext Payment Entry reads it (`payment_entry.py:708`) to treat a claim like an invoice. |
| `period_closing_doctypes` (Payroll Entry) | (a) | ERPNext Accounting Period reads it (`accounting_period.py:89`) — a closed period no longer blocks a Payroll Entry. |
| `accounting_dimension_doctypes` (5 HR doctypes) | (a) | ERPNext reads it (`accounting_dimension.py:270`) when a new dimension is created. |
| `bank_reconciliation_doctypes` (Expense Claim) | (a) | Bank reconciliation cannot match a bank line to an expense claim. |
| `repost_allowed_doctypes` (Expense Claim) | (a) | Needed by ERPNext's Repost Accounting Ledger — and by our data repair (§4.3). |
| `override_doctype_dashboards` Timesheet, Bank Account | (a) | The "Salary Slip" / "Employee" links on those forms. |
| `ignore_translatable_strings_from` lost "erpnext" | (a) | Cosmetic, translation build only. |
| `has_upload_permission`, `doc_events["User"].validate` pointed at our stub Employee | (done) | d0469c8 pointed them back at ERPNext. |
| Added: PMS `doctype_js`, route rules, fixtures, `permission_query_conditions`, `has_permission`, PMS doc_events and scheduler jobs | keep | Deliberate PMS work. |

### 1.2 Overrides (`hrms/hrms/overrides/`)

| File | Now | Class |
|---|---|---|
| `employee_payment_entry.py` (332 lines → 5-line stub) | stub | (a) — no replacement. Called by `expense_claim.js:362`, `employee_advance.js:106`, `leave_encashment.js:117`, `gratuity.js:38`, `public/js/erpnext/payment_entry.js:79`. |
| `employee_project.py` (→ stub) | stub | (a) — project costing no longer counts expense claims. |
| `employee_timesheet.py` (→ stub) | stub | (a) — Timesheet status "Payslip" / "Completed" no longer set. |
| `employee_master.py` — base class `Employee` → `Document` | changed | (a) but **dangerous to restore half-way** — see §6.3. The rest of the file (158 lines, the doc_event functions) is unchanged and in use. |
| `company.py` — import pointed at stub Account | (done) | d0469c8. |

### 1.3 Controllers, reports, patches

| File | What 48f5439 did | Class |
|---|---|---|
| `hr/doctype/expense_claim/expense_claim.py` | Base class `AccountsController` → `Document`; `make_gl_entries` → `pass`; payable-account check on submit removed; `on_update_after_submit` repost → `pass`; unlink payments on cancel → `pass`; default accounting dimensions → `return`; exchange gain/loss journal → `pass`; `get_total_reimbursed_amount` → **always 0**; bank account for "is paid" claims → `None`; missing expense account silently swallowed | (a) — all |
| `hr/doctype/employee_advance/employee_advance.py` | Unlink payment on cancel → `pass`; same-currency bank/cash account → `None` (**Return button crashes**); mode-of-payment account → `pass`; company currency/cost centre inlined | (a); the inlined currency/cost-centre lines are (c) — same result |
| `hr/doctype/leave_encashment/leave_encashment.py` | `AccountsController` → `Document`; `create_gl_entries` → `pass` | (a) |
| `payroll/doctype/gratuity/gratuity.py` | same as leave encashment | (a) |
| `payroll/doctype/payroll_entry/payroll_entry.py` | accounting dimensions → `[]` (two places); currency inlined; `get_fiscal_year` import | dimensions (a); fiscal year (done, d0469c8); currency (c) |
| `payroll/doctype/salary_slip/salary_slip.py` | `TransactionBase` → `Document`; currency inlined | (a), low risk — SalarySlip defines its own `set_status`; nothing it calls came from TransactionBase, but restore for parity |
| `hr/utils.py` | own `allow_regional`, `get_company_currency`, `InactiveEmployeeStatusError` | (b) — `allow_regional` was rewritten and then fixed by 8965ef5 (7 Sep) with a test. Keep for now; one gap: it reads the country from System Settings, ERPNext reads the company's country. Our local `InactiveEmployeeStatusError` is a *different class* from ERPNext's, so `except` on one does not catch the other — (a), low. |
| `hr/doctype/attendance/attendance.py` | status check removed | (a), low — Frappe checks Select options anyway |
| `hr/doctype/hr_settings/hr_settings.py` | wrong naming function | (done) — e8689d4 (19 Aug) |
| `hr/doctype/leave_application/leave_application.py` | own `daterange` copy | (c) — identical behaviour |
| `hr/doctype/leave_control_panel/leave_control_panel.py` | `get_default_company` inlined | (c), tiny difference (ignores a user's own default company); restore for parity |
| `hr/doctype/shift_assignment_tool/shift_assignment_tool.py` | User Permission filter → empty (2 places) | (a) **security** |
| `hr/report/employee_analytics`, `employee_birthday`, `shift_attendance` | User Permission filter → empty | (a) **security** |
| `hr/report/vehicle_expenses` | chart periods → `[]` | (a), chart is empty |
| `payroll/doctype/income_tax_slab` | currency inlined; `@allow_regional` dropped from `apply_surcharge_with_marginal_relief` | (c) — no app registers an override for it (checked upstream hrms v16.20 and India Compliance v16.10.0 hooks) |
| `payroll/report/*` (4 reports) | region/currency inlined | (c) — same result |
| `utils/custom_method_for_charts.py`, `api/*`, `controllers/*`, other imports | pointed at stubs | (done) — d0469c8 |
| `patches/v15_0/create_accounting_dimensions_in_leave_encashment.py` | body removed, **no `execute()` left** | (a) — restore; it is already marked as run on every site, so restoring changes no data |
| `patches/v16_0/set_reference_fields_in_expense_claim_advance.py` | body → `pass` | (a) — same |
| 14 stub doctypes (Company, Employee, Account, …) | added | (done) — removed by d0469c8 |
| `docker/init.sh`, `docker/provision_tenant.sh` | local-dev script edits | (c) — superseded by `deploy/provision_tenant.sh`; out of scope |

**Every ERPNext function the fix needs was checked in ERPNext v16.36.0 source** (the tag we
pin): `remove_ref_doc_link_from_pe`, `update_accounting_ledgers_after_reference_removal`,
`create_gain_loss_journal`, `unlink_ref_doc_from_payment_entries`, `build_qb_match_conditions`,
`get_default_bank_cash_account`, `get_bank_cash_account`, `validate_docs_for_voucher_types`,
`make_gl_entries`, `get_checks_for_pl_and_bs_accounts`, `get_accounting_dimensions`,
`create_accounting_dimensions_for_doctype`, `get_period_list`, `set_by_naming_series`,
`daterange`, `validate_status`, `InactiveEmployeeStatusError`, `Employee`,
`AccountsController`, `TransactionBase`, `get_account_currency`, and `erpnext.get_region /
allow_regional / get_default_cost_center / get_company_currency / get_default_company`.
All present.

---

## 2. Comparison with official Frappe HR v16

Compared against upstream `frappe/hrms` branch `version-16` at v16.20.0 (23 Sep 2026), the
release line that matches our Frappe v16.35 / ERPNext v16.36.

**Important background:** our fork was taken from upstream's `develop` branch on 3 Jul
(`__version__ = "17.0.0-dev"`), not from `version-16`. So even our July copy differs from
v16 in many files, for reasons that have nothing to do with 48f5439.

### 2.1 Where to take upstream v16, and where to take our July copy

| Area | Recommend | Why |
|---|---|---|
| `hooks.py` lost entries | **v16** | Our July entries equal v16's exactly, except where noted in §2.2. |
| `employee_payment_entry.py` | **v16** | v16 adds **permission checks** our July copy lacks: `frappe.has_permission(... "read" ...)` in `get_payment_entry_for_employee`, `get_payment_reference_details`, `get_reference_details_for_employee`, a write check in `set_exchange_rate_in_advance` (now POST-only), a clear "Bank/Cash Account Required" message instead of a crash, and an exchange-rate fix for advances. Slice 050 restored the July copy — **it should be replaced with v16's.** All v16 callers match ours. |
| `employee_project.py` | **v16** | v16 counts per-line project on expense claims. Our `Expense Claim Detail` already has the `project` field. |
| `employee_timesheet.py` | either | identical |
| `employee_master.py` | July copy (= v16 except one query rewritten from raw SQL to the query builder, plus a `docstatus = 1` filter) | Take v16's version of that query — it is safer and it fixes a bug (draft attendance was counted in the heatmap). |
| `dashboard_overrides.py` | July copy for now | v16 adds "Holiday List Assignment" and "Contract" links; Holiday List Assignment is a v16 doctype our fork does not have. |
| `company.py` | our copy + v16's `set_expense_claim_type_accounts` | See decision D4. |
| The big controllers (`expense_claim.py`, `payroll_entry.py`, `salary_slip.py`, `hr/utils.py`, `leave_application.py`) | **July copy — revert only the 48f5439 lines** | v16 differs from our July copy by 100–400 lines each, because of `develop`-vs-`version-16` drift. Some v16 changes need doctype fields and settings our fork does not have (e.g. `HR Settings.enable_multi_currency_expense_claim`, a "Partially Paid" claim status). Taking v16's controller without its JSON would break things. Re-basing the whole fork on v16 is a separate, larger job (it fits slice 054/056 "upgrade safety"). |
| `leave_encashment.py`, `gratuity.py`, `employee_advance.py`, reports, patches | July copy, 48f5439 lines only | small, same reason |

### 2.2 Every place our `hooks.py` now differs from upstream v16

**Ours only — deliberate, keep:**
- `doctype_js`: PMS Review Record, PMS Calibration Session.
- `website_route_rules`: four `/pms-*` routes.
- `fixtures`: Workflow `PMS%`.
- `permission_query_conditions` / `has_permission`: Attendance Deduction, Policy Document,
  Policy Acknowledgement, six PMS doctypes, Employee Performance Feedback (ALV-117).
- `doc_events`: Employee (documents validate / sync / checklist), Leave Application (fleet
  reallocation), Salary Structure Assignment (ESI), Appraisal (metrics, attendance score,
  dotted-line feedback), Appraisal Cycle, Job Applicant (screening), five PMS doctypes.
- `scheduler_events`: two cron jobs (late rule, document expiry), PMS hourly and daily jobs.

**Upstream v16 only — lost by 48f5439 (restore):** everything marked (a) in §1.1.

**Upstream v16 only — added upstream since July (decide each):**

| v16 entry | Recommend |
|---|---|
| `Company.on_update` → `set_expense_claim_type_accounts` | **Adopt** (D4). It creates an "Expense Claims" account per company and fills it into every Expense Claim Type — exactly the set-up gap that makes restored claims fail to submit. |
| `audit_trail_doctypes` (Expense Claim, Payroll Entry, Salary Slip, Leave Encashment, Gratuity) | **Adopt**. Low risk, good for audit. I could not confirm in the time available which screen reads it — I will verify before building. |
| `setup_wizard_requires` / `setup_wizard_stages` (`hrms.setup_wizard`) | **Do not adopt.** The module does not exist in our fork; our provisioning drives set-up. |
| `extend_bootinfo` (`hrms.utils.extend_bootinfo`) | **Do not adopt.** Not in our fork; only for Frappe's own hosted HR. |
| `hrms.telemetry.*` doc_events and daily job | **Do not adopt.** It sends usage events to Frappe's analytics service and needs a new doctype. A privacy decision, not a bug fix. |

---

## 3. Business impact, by persona

### 3.1 Accounts team (the people hit hardest)

- **Buttons that fail:** "Create → Payment" on Expense Claim, Employee Advance, Leave
  Encashment and Gratuity ("has no attribute get_payment_entry_for_employee"). "Return" on
  Employee Advance. Making a Payment Entry by hand for an employee and adding the claim as a
  reference ("Reference Doctype must be one of Journal Entry").
- **Books are wrong:** a submitted expense claim, leave encashment (paid by payment entry)
  or gratuity (not via salary slip) books **nothing**. The employee is never shown as owed
  money. Expense accounts are understated. "Is Paid" claims never credit the bank.
- **Payroll accounting:** payroll Journal Entries carry no accounting dimensions. Cancelling
  a payroll Journal Entry leaves salary slips linked to a cancelled entry. A closed
  Accounting Period no longer blocks a Payroll Entry.
- **Bank reconciliation:** an expense claim cannot be matched to a bank line.
- **Accounting dimensions:** a dimension created since 31 July was never added to Expense
  Claim, Expense Claim Detail, Expense Taxes and Charges, Payroll Entry or Leave Encashment.
- **Over-payment guard gone:** a Journal Entry can pay more than a claim is worth.

### 3.2 HR Manager / CXO

- **Statuses wrong:** Expense Claim stays "Unpaid" forever. Employee Advance stays "Unpaid"
  even after it is paid. Full & Final Statement stays "Unpaid" after its Journal Entry.
  Salary Withholding never shows the salary as released. Timesheet never shows "Payslip".
- **Reports:** Employee Analytics, Employee Birthday, Shift Attendance and the Shift
  Assignment Tool show every employee, ignoring User Permissions (see 3.4).
- **Project costing** ignores expense claims.
- Employee form: the payroll cost centre picker is not filtered by company; retirement date
  is not filled in from date of birth. Company form: HR default-account pickers not
  filtered. Delivery Trip: no "Create Expense Claim". Timesheet: no "Create Salary Slip".

### 3.3 Employee

- They can still file a claim in the portal. But the claim they were paid for **still shows
  "Unpaid"** in the portal and in the app, forever. This generates "why was I not paid?"
  questions to HR.
- Advances they have received show as unpaid, which can block claiming against them.

### 3.4 Security note (for the security reviewer)

`build_qb_match_conditions` is how those reports respect User Permissions. With it replaced
by an empty filter, an HR user restricted by User Permission to one company, branch or
department can pick another in the report filter and see those employees' names, birthdays,
and attendance. **This is inside one tenant, not across tenants** (each tenant is its own
site and database). It matters for multi-company tenants (the HR Manager persona "sees
their companies only"). Restoring the four calls closes it.

---

## 4. Data impact since 31 July, and how to find and repair it

### 4.1 Which sites

48f5439 went straight onto `main` on 31 July. Every image built since then carries it, so
**every tenant on dev and production** is affected, for every record created since that
tenant ran a post-31-July image. Tenants created after 31 July are affected for their whole
life. I did not run anything on any server.

### 4.2 Read-only dry-run queries (run per site, by Surbhi, later)

They read only. They print document names, companies and amounts — **no employee names**,
so the output can be pasted into a ticket. Run with `bench --site <site> mariadb` (or any
read-only DB client), dev first, then production.

```sql
-- Q1. Submitted expense claims with no ledger entries (every one is wrong).
--     no_payable = 1 means it cannot be reposted until a payable account is set.
SELECT ec.name, ec.company, ec.posting_date, ec.status, ec.is_paid,
       ec.total_sanctioned_amount, ec.grand_total, ec.total_amount_reimbursed,
       (IFNULL(ec.payable_account,'') = '') AS no_payable
FROM `tabExpense Claim` ec
WHERE ec.docstatus = 1
  AND NOT EXISTS (SELECT 1 FROM `tabGL Entry` g
                  WHERE g.voucher_type = 'Expense Claim' AND g.voucher_no = ec.name
                    AND g.is_cancelled = 0)
ORDER BY ec.posting_date;

-- Q2. Expense claims whose "reimbursed" figure disagrees with real payments.
SELECT ec.name, ec.company, ec.status, ec.grand_total, ec.total_amount_reimbursed,
       IFNULL(pe.amt,0) + IFNULL(je.amt,0) AS paid_per_payments
FROM `tabExpense Claim` ec
LEFT JOIN (SELECT reference_name, SUM(allocated_amount) amt
           FROM `tabPayment Entry Reference`
           WHERE reference_doctype = 'Expense Claim' AND docstatus = 1
             AND IFNULL(advance_voucher_type,'') = ''
           GROUP BY reference_name) pe ON pe.reference_name = ec.name
LEFT JOIN (SELECT reference_name,
                  SUM(debit_in_account_currency - credit_in_account_currency) amt
           FROM `tabJournal Entry Account`
           WHERE reference_type = 'Expense Claim' AND docstatus = 1
           GROUP BY reference_name) je ON je.reference_name = ec.name
WHERE ec.docstatus = 1 AND ec.is_paid = 0
  AND ABS(ec.total_amount_reimbursed - (IFNULL(pe.amt,0) + IFNULL(je.amt,0))) > 0.005;

-- Q3. Employee advances paid by Journal Entry but never marked paid
--     (no Advance Payment Ledger rows were written without the hook).
SELECT ea.name, ea.company, ea.status, ea.advance_amount, ea.paid_amount,
       (SELECT IFNULL(SUM(jea.debit_in_account_currency),0)
          FROM `tabJournal Entry Account` jea
         WHERE jea.reference_type = 'Employee Advance' AND jea.reference_name = ea.name
           AND jea.docstatus = 1) AS paid_by_je,
       (SELECT COUNT(*) FROM `tabAdvance Payment Ledger Entry` a
         WHERE a.against_voucher_type = 'Employee Advance' AND a.against_voucher_no = ea.name
           AND a.delinked = 0) AS ledger_rows
FROM `tabEmployee Advance` ea
WHERE ea.docstatus = 1
HAVING paid_by_je <> ea.paid_amount OR (paid_by_je > 0 AND ledger_rows = 0);

-- Q4. Cancelled employee advances still linked from a live payment entry.
SELECT per.parent AS payment_entry, per.reference_name AS employee_advance
FROM `tabPayment Entry Reference` per
JOIN `tabEmployee Advance` ea ON ea.name = per.reference_name
WHERE per.reference_doctype = 'Employee Advance' AND per.docstatus = 1 AND ea.docstatus = 2;

-- Q5. Leave encashments and gratuities that should have posted and did not.
SELECT 'Leave Encashment' AS doctype, le.name, le.company, le.encashment_date AS dt, le.status
FROM `tabLeave Encashment` le
WHERE le.docstatus = 1 AND le.pay_via_payment_entry = 1
  AND NOT EXISTS (SELECT 1 FROM `tabGL Entry` g WHERE g.voucher_type = 'Leave Encashment'
                  AND g.voucher_no = le.name AND g.is_cancelled = 0)
UNION ALL
SELECT 'Gratuity', gr.name, gr.company, gr.posting_date, gr.status
FROM `tabGratuity` gr
WHERE gr.docstatus = 1 AND gr.pay_via_salary_slip = 0
  AND NOT EXISTS (SELECT 1 FROM `tabGL Entry` g WHERE g.voucher_type = 'Gratuity'
                  AND g.voucher_no = gr.name AND g.is_cancelled = 0);

-- Q6. Full & Final statements paid by a Journal Entry but still "Unpaid".
SELECT DISTINCT f.name, f.company, f.status, jea.parent AS journal_entry
FROM `tabFull and Final Statement` f
JOIN `tabJournal Entry Account` jea
  ON jea.reference_type = 'Full and Final Statement' AND jea.reference_name = f.name
 AND jea.docstatus = 1
WHERE f.docstatus = 1 AND f.status <> 'Paid';

-- Q7. Salary withholding cycles whose release Journal Entry is submitted but not recorded.
SELECT swc.parent AS salary_withholding, swc.name AS cycle, swc.journal_entry
FROM `tabSalary Withholding Cycle` swc
JOIN `tabJournal Entry` je ON je.name = swc.journal_entry AND je.docstatus = 1
WHERE swc.docstatus = 1 AND swc.is_salary_released = 0;

-- Q8. Salary slips still linked to a cancelled payroll Journal Entry.
SELECT ss.name, ss.company, ss.journal_entry
FROM `tabSalary Slip` ss
JOIN `tabJournal Entry` je ON je.name = ss.journal_entry
WHERE ss.docstatus < 2 AND je.docstatus = 2;

-- Q9. Accounting dimensions missing on HR doctypes (0 rows = nothing to do).
SELECT ad.name AS dimension, d.dt
FROM `tabAccounting Dimension` ad
CROSS JOIN (SELECT 'Expense Claim' dt UNION ALL SELECT 'Expense Claim Detail'
            UNION ALL SELECT 'Expense Taxes and Charges' UNION ALL SELECT 'Payroll Entry'
            UNION ALL SELECT 'Leave Encashment') d
WHERE NOT EXISTS (SELECT 1 FROM `tabCustom Field` cf
                  WHERE cf.dt = d.dt AND cf.fieldname = ad.fieldname);

-- Q10. Payments made to employees since 31 Jul that are linked to nothing
--      (a likely workaround while the button was broken). For the accountant to review.
SELECT pe.name, pe.company, pe.posting_date, pe.paid_amount, pe.unallocated_amount
FROM `tabPayment Entry` pe
WHERE pe.docstatus = 1 AND pe.party_type = 'Employee' AND pe.posting_date >= '2026-07-31'
  AND pe.unallocated_amount > 0;

-- Q11. Set-up check: companies with no expense-claim payable account
--      (after the fix, claims in these companies cannot be submitted).
SELECT name FROM `tabCompany` WHERE IFNULL(default_expense_claim_payable_account,'') = '';

-- Q12. Set-up check: employee naming method (the Employee override throws if empty).
SELECT value FROM `tabSingles` WHERE doctype = 'HR Settings' AND field = 'emp_created_by';
```

### 4.3 Repair — a separate step, dry-run first, only after the code fix is live on that site

Each repair is safe to run twice, runs per site, prints what it *would* change first, and
logs document names only.

| Finding | Repair | Mechanism |
|---|---|---|
| Q1 claims with no ledger | Set `payable_account` where empty (from the company default — needs Q11 fixed first), then rebuild the ledger | ERPNext **Repost Accounting Ledger** with the claims as vouchers (Frappe-first, audited). Needs `repost_allowed_doctypes` restored and "Expense Claim" in Accounts Settings → Repost Allowed Types. Fallback: a script calling `doc.make_gl_entries()` only when Q1 still shows no ledger for that claim. **Postings are dated on the claim's own date** — your accountant must agree, especially if any period is closed. |
| Q2 wrong status | Re-run `update_reimbursed_amount(claim)` for each claim | the restored hrms function |
| Q3 / Q4 advances | Q4: `remove_ref_doc_link_from_pe` + `update_accounting_ledgers_after_reference_removal`. Q3: rebuild the Advance Payment Ledger rows for the JEs found. | ERPNext's own patch `erpnext.patches.v15_0.create_advance_payment_ledger_records` is the likely tool, **but I have not verified it only touches missing rows. I will read it before proposing it.** |
| Q5 encashment / gratuity | `create_gl_entries()` on each, only when still no ledger | restored controllers |
| Q6 F&F | Re-run `update_full_and_final_statement_status(je)` for each JE found | restored hrms function |
| Q7 withholding | Re-run `update_salary_withholding_payment_status(je, "on_submit")` | restored hrms function |
| Q8 slips | Clear `journal_entry` on those slips | `unlink_ref_doc_from_salary_slip(je)` |
| Q9 dimensions | New patch calling `create_accounting_dimensions_for_doctype` for the five doctypes | ERPNext function; skips fields that already exist |
| Q10 | No automatic repair. The accountant reconciles each by hand (allocate via Payment Reconciliation). | |

Delivered as one `bench --site X execute hrms.…alv178_repair.run --kwargs "{'dry_run': 1}"`
module with a dry-run default, written in the fix branch, **run by you**, dev first, then
production, each on your word.

---

## 5. Why no test caught it

1. **A guard did catch it — and was waved through.** `scripts/check_api_paths.py` was added
   on 18 Aug and found both dead paths (`get_payment_entry_for_employee`,
   `get_payment_reference_details`). CI was set to `--max 2` and the comment calls them
   "known debt: two pre-existing upstream hrms paths". They were not upstream debt; they
   were this bug. I re-ran it today: still exactly those two.
2. **hrms tests never run in CI.** `.github/workflows/ci.yml` runs `run-tests` for
   `alvoraa_goals` and `alvoraa_portal` only. `test_expense_claim.py`,
   `test_employee_advance.py` and `test_leave_encashment.py` exist and call
   `get_payment_entry_for_employee` and check ledger entries — they would have failed.
3. **`check_app_integrity.py` checks that each hook points at something real — but a hook
   that is deleted points at nothing, so there is nothing to check.**

Proposal (small, in the same fix):
- `check_api_paths.py --max 0` in CI.
- A **hook-contract test** in `alvoraa_portal/tests/` (so it runs in CI today) that fails if:
  Payment Entry / Journal Entry / Unreconcile Payment lose `update_payment_for_expense_claim`;
  Journal Entry loses the F&F, withholding and salary-slip hooks; `override_doctype_class`
  loses the four entries or `EmployeeMaster` stops inheriting ERPNext's `Employee`;
  `accounting_dimension_doctypes`, `advance_payment_payable_doctypes`, `invoice_doctypes`,
  `bank_reconciliation_doctypes`, `repost_allowed_doctypes`, `period_closing_doctypes` lose
  their HR doctypes; `ExpenseClaim`, `LeaveEncashment`, `Gratuity` stop inheriting
  `AccountsController`; any hrms source file contains "(no erpnext)".
- A behaviour test: submit a claim, see two GL entries, create a Payment Entry with
  `get_payment_entry_for_employee`, submit it, see the claim become "Paid".
- Add the hrms `expense_claim`, `employee_advance`, `leave_encashment`, `gratuity`,
  `full_and_final_statement` and `payroll_entry` doctype tests to CI with `--doctype`.
  These may need the known hrms test bootstrap fix (fiscal year); cost is some CI minutes.
  **Decision D6.**

---

## 6. Fix plan, size and risks

### 6.1 Recommended order

**Step A — hot-fix (small, ships first).** On `fix/alv-178-payment-entry`, off `origin/dev`:
1. `employee_payment_entry.py` ← upstream v16 (with its permission checks).
2. `hooks.py`: `override_doctype_class` for **Payment Entry only**, plus `doc_events` for
   Payment Entry, Unreconcile Payment and Journal Entry, plus `invoice_doctypes`,
   `advance_payment_payable_doctypes`, `repost_allowed_doctypes`, `doctype_js` for Payment
   Entry and Journal Entry.
3. `expense_claim.py`, `employee_advance.py`, `leave_encashment.py`, `gratuity.py`: revert
   the 48f5439 lines (restores ledger posting, the paid-amount count, the Return button).
4. `check_api_paths.py --max 0`; the hook-contract test; the behaviour test.
5. The set-up check Q11 per tenant and a way to set the payable account (D3).

This fixes Surbhi's button, puts claims and advances back in the books, and makes claims
turn "Paid". About 8 files, ~600 lines, almost all restored code. No doctype JSON, no new
fields, no migrate-time data change.

**Step B — full restore (follows, same release or the next one).** Everything else marked
(a): Employee/Timesheet/Project overrides, remaining hooks (Timesheet, Loan, dimensions,
bank reconciliation, period closing, dashboards, `required_apps`, `setup_wizard_complete`,
remaining `doctype_js`), payroll entry dimensions, salary slip base class, the four
User-Permission report fixes, vehicle expenses chart, attendance status check, the two
patches' bodies, one new patch for missing dimension fields, v16's `set_expense_claim_type_accounts`
and `audit_trail_doctypes` if approved.

**Step C — data repair (§4.3).** Separate tool, dry-run first, on your word per site.

**Why split A and B:** A touches only money paths and is easy to test by hand. B contains
the one risky change (the Employee override, below) and security changes that deserve their
own review.

### 6.2 How this relates to slice 050

Slice 050 (commit 85cd29b) has done most of step A's item 3 and the three stub overrides,
from the July copy. Options — **decision D1**:
- **(recommended)** ALV-178 takes 050 over: cherry-pick 85cd29b onto this branch, replace
  the Payment Entry override with v16's, add the hooks 050 left out, drop 050's "Employee"
  line from `override_doctype_class` until step B. 050's session is told and its worktree
  and bench (`hrlocal-050`) are left alone until it hands over.
- or 050 finishes and ALV-178 only adds what 050 lacks — two branches in the same files,
  more merge risk.

### 6.3 Risks

| Risk | What could happen | How we handle it |
|---|---|---|
| **Claims stop submitting** | Restoring the "Payable Account is mandatory" check. 050's notes say **no tenant company has `default_expense_claim_payable_account` set.** The portal's `apply_expense_claim` does not set it either. HR would hit an error on every claim. | D3: set the company default on every tenant before the fix goes live (with v16's account-creation hook, or by hand), and have `apply_expense_claim` fill `payable_account` from the company default. The error message will say where to set it. |
| **Employee override** | Registering `EmployeeMaster` while it still inherits `Document` replaces ERPNext's whole Employee controller — every Employee validation stops. (050's commit has exactly this bug.) Even done right, it changes naming: since 31 July every new employee was named by naming series; afterwards naming follows HR Settings, and **throws** if HR Settings has no naming method. dtc is about to load 302 employees. | Step B only, with the base class restored in the same commit, Q12 run on each tenant first, and after dtc's load or with dtc's naming confirmed (D5). |
| Ledger now required | Expense accounts per Expense Claim Type become necessary again (the silent "skip" is removed). | Same as D3/D4; the message says what to set. |
| Reports narrow | After the User Permission fix, restricted HR users see fewer rows in four reports. That is the intended behaviour, but someone may notice. | Mention in release notes. |
| Hook cache | New `doc_events` / overrides only take effect after a restart and cache clear. | Part of the deploy step, which needs your approval. |
| Other sessions in the same files | `hooks.py` is a hot file. 050 is in `hooks.py` and four controllers. | §7. |
| Migration | None needed for step A. Step B adds one idempotent patch (dimension fields). | |

### 6.4 NFR verdicts (for step A + B as proposed)

| Dimension | Verdict | Why |
|---|---|---|
| Performance | neutral | Restores upstream's own queries; one extra hook call per Payment/Journal Entry. |
| Security | **improves** | v16 permission checks on the payment endpoints; User Permissions back on four reports. |
| Reliability | **improves** | Buttons stop crashing; errors say what to set instead of silently skipping. |
| Scalability | neutral | |
| Maintainability | **improves** | Our fork moves back towards upstream; tests pin the hooks. |
| Data integrity | **improves** | Ledger, paid amounts and statuses become right again. |
| Compliance / privacy | **improves** | Accounting audit trail restored; repair output has no personal data; telemetry deliberately not adopted. |

---

## 7. Parallel-work check

| File | Others in it | Plan |
|---|---|---|
| `hrms/hrms/hooks.py` | slice 050 (override block); hot file | take over 050 (D1); edit only the lost blocks; rebase on `origin/dev` before each commit |
| `overrides/employee_payment_entry.py`, `employee_project.py`, `employee_timesheet.py`, `expense_claim.py`, `employee_advance.py`, `leave_encashment.py`, `gratuity.py` | slice 050 | same |
| `overrides/employee_master.py` | slice 050 has a **staged, uncommitted** change in its worktree | not touched until 050's session hands over |
| `payroll_entry.py`, `salary_slip.py`, four reports, `shift_assignment_tool.py` | none found on the work board | step B |
| `alvoraa_portal/hr_api.py` (`apply_expense_claim` only) | 010 / 012 / 016 have touched other functions in this file | one function only |
| `.github/workflows/ci.yml` (one flag) | shared | one line |

Bench: `hrlocal-050` is marked in use by slice 050. I will not use it or any other
`hrlocal-*` container. Testing needs its own throwaway container, on your word.

---

## 8. Release path (Surbhi's instruction, 29 Sep)

This fix must reach **production (`main`)**, because aahr is where Surbhi hit it. `main` is
being released right now (b4b0eff, email branding plus Helpdesk/LMS); `origin/main`
currently contains all of `origin/dev`.

1. **Local.** Build step A on `fix/alv-178-payment-entry` (from `origin/dev`), test on a
   throwaway local container, review. Stop and report.
2. **dev — on your word.** Rebase on `origin/dev`, fast-forward into `dev`, push. You test on
   dev: Create Payment on a claim, claim turns Paid, cancel reverses it, advance return.
3. **Dry-run on dev — on your word.** Run the §4.2 queries and the repair tool with
   `dry_run=1` on the dev tenants. Look at the output together.
4. **main — on your word, after dev testing.** Because b4b0eff is being released now, the
   hot-fix goes to `main` **after that release has landed**, as **its own small release**:
   `main` fast-forwards or merges from `dev` once dev holds only the release plus ALV-178
   step A. If other work lands on `dev` in between that is not ready for production, the
   alternative is to cherry-pick the ALV-178 commits onto a release branch off `main` —
   your choice at that point (D7).
5. **Production data dry-run — on your word, before any repair.** Run §4.2's queries and the
   repair tool with `dry_run=1` on each production tenant (aahr, dtc, and the demo tenants).
   **Nothing is repaired until you have seen the dry-run output for that tenant.**
6. **Production repair — on your word, per tenant.** Then re-run Q1–Q9 to prove they return
   no rows.
7. Step B follows the same path, as its own release, before dtc loads employees (or after,
   per D5).

I will not push, deploy, `docker cp`, clear caches or touch any server myself.

---

## 9. Decisions for Surbhi

| # | Decision | My recommendation |
|---|---|---|
| D1 | Take over slice 050's work into ALV-178, or let 050 finish? | Take over, with 050's session told. |
| D2 | Hot-fix first (step A), full restore (step B) after? | Yes. |
| D3 | Which account is each company's "expense claim payable" account, and do we set it on every tenant before the fix goes live? Also have the portal fill it on new claims? | Yes to both; the accountant names the account (commonly a "Payroll Payable" / "Expense Claims Payable" liability account). |
| D4 | Adopt upstream v16's `set_expense_claim_type_accounts` (auto-creates an "Expense Claims" account per company and fills Expense Claim Types)? | Yes. |
| D5 | When to restore the Employee override (naming follows HR Settings again) — before or after dtc loads 302 employees? | Before, with HR Settings checked on dtc, so dtc's IDs are right from day one — but only in step B, tested on its own. |
| D6 | Run the hrms payment/payroll doctype tests in CI (more CI minutes)? | Yes, the six doctypes named in §5. |
| D7 | Hot-fix to production as its own small release after b4b0eff lands, from `dev`, or by cherry-pick onto `main`? | From `dev` if dev holds nothing else unready; otherwise cherry-pick. |
| D8 | Repair past records via ERPNext's Repost Accounting Ledger (dated on each claim's own date), and who signs off the backdated postings? | Yes; the tenant's accountant signs off. |
| D9 | Adopt v16's `audit_trail_doctypes`? Skip v16 telemetry, setup-wizard stages and bootinfo? | Adopt audit trail; skip the other three. |
