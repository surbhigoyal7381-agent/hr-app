# ALV-178 step A (hot-fix): implementation notes

Branch `fix/alv-178-payment-entry` (worktree `.claude/worktrees/alv-178`), from `origin/dev`
24ffbf4. Nothing came in from `origin/dev` during the work (fetched at start and before
each commit). **Local only: not pushed, not merged into `dev`, no server touched.**
Surbhi's decisions of 29 Sep 2026 are D1–D9 in `ALV-178-impact-and-strategy.md` §9.

## What was built, file by file

| File | Change | Mechanism |
|---|---|---|
| `hrms/hr/doctype/expense_claim/expense_claim.py`, `employee_advance.py`, `leave_encashment.py`, `payroll/doctype/gratuity/gratuity.py` | Back to exactly their content before 48f5439 (no later commit touched them). Ledger posting, the paid amount, the payable-account check, unlinking payments on cancel, accounting-dimension defaults, exchange gain/loss, the advance Return button. | restore (taken from slice 050's 85cd29b, D1) |
| `hrms/overrides/employee_payment_entry.py` | Upstream Frappe HR v16.20.0 copy, **not** the July copy: it adds read-permission checks on the three whitelisted functions, a write check and POST-only on `set_exchange_rate_in_advance`, and a clear "Bank/Cash Account Required" message. | extend (override class) |
| `hrms/overrides/employee_project.py` | Upstream v16 copy. | extend |
| `hrms/overrides/company.py` | Adds v16's `set_expense_claim_type_accounts` + `get_or_create_expense_claim_account` (D4). | hook |
| `hrms/hooks.py` | `doctype_js` Payment Entry, Journal Entry; `override_doctype_class` Payment Entry, Project; `doc_events` Payment Entry, Unreconcile Payment, Journal Entry (full v16 set), Company.on_update +1; `advance_payment_payable_doctypes`, `invoice_doctypes`, `repost_allowed_doctypes`, `audit_trail_doctypes` (D9). | configure |
| `alvoraa_portal/hr_api.py` | `apply_expense_claim` fills `payable_account` and `cost_center` (header and row) from the company; new `_expense_claim_accounts` refuses with a plain message when HR has not set the payable account, the cost centre, or the expense type's account (D3). | build (small) |
| `alvoraa_portal/tests/test_erpnext_integration_178.py` | New pin tests (see below). | test |
| `alvoraa_portal/tests/test_expense_and_scoping.py` | Fixture now gives the test company a payable account and the claim type an account; two new tests. | test |
| `.github/workflows/ci.yml` | `check_api_paths.py --max 0`; new step running the hrms Expense Claim, Employee Advance, Leave Encashment, Gratuity, Full and Final Statement and Salary Withholding tests on their own site (D6). | CI |

**Coupled into step A, beyond the list:** the **Project** override. The hrms Expense Claim
test `test_total_expense_claim_for_project` fails without it, because a submitted claim
updates its project's costing and only this class counts claims. It is upstream v16's
62-line class and only affects Project costing. Also `advance_payment_payable_doctypes` and
`invoice_doctypes`: without them an Employee Advance never becomes Paid and a Payment Entry
cannot allocate against a claim.

## What now works end to end (proved on the throwaway bench)

Own containers `alv178`, `alv178-db`, `alv178-redis`, network `alv178`, volume
`alv178-sites`; image `alvoraa-app:helpdesk-lms-test2` (Frappe 16.35.0, ERPNext 16.36.0 —
the pinned versions). Two fresh sites: `test_site` (erpnext, hrms, alvoraa_portal,
alvoraa_goals, as CI) and `hrms_test` (erpnext, hrms only).

- Expense Claim: submit → GL entries posted → `get_payment_entry_for_employee` (what
  "Create Payment" calls) returns a Payment Entry → submit → claim **Paid**, reimbursed =
  total → cancel the payment → **Unpaid**, reimbursed 0.
- Expense Claim paid by **Journal Entry** → Paid; cancel → Unpaid. A Journal Entry that
  pays more than the claim is refused.
- Employee Advance: submit → Create Payment → Paid, paid amount set → cancel → Unpaid.
- Leave Encashment: Frappe HR's own `test_status_of_leave_encashment_after_payment_via_payment_entry_and_fnf`
  calls `get_payment_entry_for_employee`, submits the payment and checks the status — passes.
  Gratuity, Full and Final Statement and Salary Withholding: their own hrms suites pass,
  including the Journal Entry and payment-entry paths (results below).
- Portal: a claim filed from the portal carries the company's payable account and cost
  centre; with no payable account set, the employee sees "…Please ask HR to set the
  Default Expense Claim Payable Account on the company…" and nothing is saved.

Not done: clicking the button in a browser. The throwaway bench has no built front-end
files, so the proof is the server call the button makes. Surbhi's dev test covers the click.

## Tests run (real output)

All run in the throwaway containers, never on a shared bench.

| Run | Result |
|---|---|
| `alvoraa_portal.tests.test_erpnext_integration_178` (test_site) | 15 tests, OK |
| `alvoraa_portal.tests.test_expense_and_scoping` (test_site) | 8 tests, OK |
| hrms Expense Claim (hrms_test) | 28 tests, OK (first run: 1 failure, `test_total_expense_claim_for_project`, fixed by restoring the Project override; later a `test_rejected_expense_claim` error in a run disturbed by a parallel run, clean on rerun) |
| hrms Employee Advance | 15 tests, OK |
| hrms Leave Encashment | 11 tests, OK |
| hrms Gratuity | 5 tests, OK |
| hrms Full and Final Statement | 4 tests, OK |
| hrms Salary Withholding | 4 tests, OK |
| full `alvoraa_portal` suite (test_site) | cut short at hand-off: two batches finished OK (16 and 870 tests, 16 skipped); the run was still going with 2,236 passes and 0 failures logged when the containers were stopped. Needs one full rerun. |
| full `alvoraa_goals` suite (test_site) | not reached (queued after the portal suite). Needs a run. |
| `check_api_paths.py --max 0` | OK, 0 unresolved |
| `check_app_integrity.py` | OK, 674 checks |
| `check_brand_spelling.py` | OK |
| `ruff check` / `ruff format` (0.6.9) on new and changed code | clean |

**Gratuity and Leave Encashment first failed** with "wkhtmltopdf … HostNotFoundError". Not
our code: submitting a salary slip emails it as a PDF, and wkhtmltopdf fetches styles from
the site's own URL. With a host name and a web server (as upstream Frappe HR's CI does)
they pass. The CI step does the same.

**Running the hrms tests needs their own site.** ERPNext's test bootstrap creates
calendar-year "_Test Fiscal Year"s, which overlap the April–March years our portal tests
create, and test discovery then fails. CI uses a separate `hrms_test_site`.

## Pin tests (fail if a merge drops the fix)

`test_erpnext_integration_178.py`: every restored doc_event handler; the Payment Entry and
Project overrides; the four ERPNext hook lists; the two form scripts; the payment functions
exist and are whitelisted; a Payment Entry for an Employee accepts Expense Claim, Employee
Advance, Leave Encashment and Gratuity; the three ledger controllers are
`AccountsController`s; no "(no erpnext)" stub left in the five files; plus the three
end-to-end tests above. It runs in CI with the `alvoraa_portal` suite.

## Seven dimensions, against the code written

| Dimension | Before → after | Note |
|---|---|---|
| Performance | neutral | Upstream's own queries; one extra hook call per Payment/Journal Entry submit; portal claim filing adds 2 small reads. |
| Security | **improves** | v16 permission checks on `get_payment_entry_for_employee`, `get_payment_reference_details`, `get_reference_details_for_employee`, `set_exchange_rate_in_advance`. `expense_type` from the portal is only a parameterised filter value. |
| Reliability | **improves** | Buttons work; set-up gaps give a plain message instead of a raw error. |
| Scalability | neutral | |
| Maintainability | **improves** | Fork back towards upstream; pin tests + hrms tests in CI. |
| Data integrity | **improves** for new records | Ledger, paid amounts and statuses right from now on. Old records need step C. |
| Compliance / privacy | **improves** | `audit_trail_doctypes` adopted; telemetry not adopted; messages and logs carry no personal data. |

## Before this reaches a tenant — set-up each company needs

Checked on the fresh site; the same will be true on tenants:

1. **Default Expense Claim Payable Account** on each Company (D3; the accountant chooses).
   Without it the portal refuses new claims with the plain message, and desk submit says
   "Payable Account is mandatory".
2. **Expense account on each Expense Claim Type** — filled automatically by
   `set_expense_claim_type_accounts` the next time each Company is saved (it creates an
   "Expense Claims" account). For existing companies, save each Company once, or set by hand.
3. **"Employee Advances" account type = Receivable.** The standard chart leaves it untyped
   and Frappe HR refuses an Employee Advance payment otherwise. Add to the dry-run:
   `SELECT c.name, a.name, a.account_type FROM tabCompany c JOIN tabAccount a ON a.name = c.default_employee_advance_account WHERE IFNULL(a.account_type,'') <> 'Receivable';`
4. A **fiscal year** covering the posting date and a **default cash/bank account** (needed
   by Create Payment; the v16 message now says so).
5. After deploy: restart and clear cache, so the new hooks are read (deploy step, needs
   approval).

## Left for step B (and why)

- `override_doctype_class` **Employee** — must go in with `EmployeeMaster(Employee)` in the
  same commit (050's bug). **D5: before dtc loads its 302 employees.** What changes: since
  31 Jul every new employee is named by naming series (`HR-EMP-…`) whatever HR Settings
  says. After step B, naming follows HR Settings → "Employee Naming By": Naming Series
  (same as now), Employee Number (the ID becomes the number HR types, e.g. dtc's own
  codes), or Full Name. If that setting is empty, creating an employee **fails** with
  "Please setup Employee Naming System". Existing employees are never renamed. So before
  dtc's load: set dtc's HR Settings to the naming they want and include `employee_number`
  in the load file if they choose Employee Number.
- **Timesheet** override and hook, Loan hook.
- `accounting_dimension_doctypes`, `period_closing_doctypes`, `bank_reconciliation_doctypes`,
  `required_apps`, `setup_wizard_complete`, remaining `doctype_js`, Timesheet/Bank Account
  dashboards, `ignore_translatable_strings_from`.
- Payroll Entry accounting dimensions, Salary Slip base class, attendance status check,
  vehicle-expenses chart, the two patch bodies, one patch for missing dimension fields.
- The User Permission fixes in three reports and the Shift Assignment Tool (ALV-180).

## Known gaps and shortcuts

- **Acceptable simplification:** the portal refuses a claim when set-up is missing, rather
  than saving a draft HR could fix later. Surbhi's instruction; the message says what HR
  must set.
- **Temporary debt:** proof ran on Frappe 16.35.0 / ERPNext 16.36.0 in a local image, not
  the dev image; dev testing removes it.
- **Intentional trade-off:** the big controllers were restored from our July copy, not v16,
  because v16's versions need doctype fields our develop-based fork does not have.
- `ruff`: my new and changed code is clean under the pinned 0.6.9. `hooks.py` and
  `hr_api.py` carry older formatting and lint findings (non-blocking in CI), left alone.
