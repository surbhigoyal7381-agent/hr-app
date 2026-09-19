# Permission templates — who sees whose records

**Written:** 14 Sep 2026 · **Direction from Surbhi:** permissions are each
organisation's choice, not something we decide from one tenant. We ship
**templates** built on best practice and common customer choices, a system admin
applies and adjusts them per tenant, and later a **tenant permission
configuration page** does this after a tenant is created, based on the features
they bought.

**Status:** templates defined here. First applied by hand to PP Jewellers on
14 Sep 2026. The configuration page is not built.

---

## 1. The principles the templates rest on

| Principle | What it means here |
|---|---|
| **Least privilege** | Start from nothing and grant what a job needs, not the reverse |
| **Need to know, not rank** | Seniority is not a reason to see a record. A job is |
| **Scope by reporting line for people data** | Leave, attendance, balances, claims and personal details follow who manages whom |
| **Scope by location for location HR** | A store's HR person handles that store |
| **Pay is narrower than people** | Seeing someone's attendance is not a reason to see their salary |
| **Presence, never the reason** | Colleagues may see *that* someone is away, never *why* |
| **Data limits, not denied screens** | Prefer a report that shows your own scope over a report nobody can open |
| **Defence in depth** | Bulk routes (export, spreadsheet view) get their own lock, in case a data limit is ever missing |

## 2. The templates

Each template is a combination of **Frappe roles** and **User Permissions**.

> **The Frappe fact the whole model depends on:** Employee is a **tree** built on
> `reports_to`. A User Permission on a person's own Employee record automatically
> covers **everyone below them** in the reporting line, and updates itself when
> reporting lines change. One permission per manager, not one per team member.

| Template | Roles | User Permission | Sees |
|---|---|---|---|
| **T1 · Employee** | Employee, Employee Self Service | Own Employee record | **Themselves** |
| **T2 · Line manager** | T1 + Leave Approver, Expense Approver as needed | Own Employee record — which covers their reporting line | **Themselves + everyone below them** |
| **T3 · Location HR** | HR User | **Their branch** — *not* their own record | **Their location's people and payroll** |
| **T4 · Central HR** | HR User or HR Manager | None | **Everyone** |
| **T5 · Payroll** | **Payroll User** — the payroll record types and the locked salary fields. *HR User no longer carries payroll* | None for central payroll; **branch** when payroll is run per location | Pay data for their scope |
| **T8 · Recruitment** | **Recruitment User** — recruitment records only, plus *select* on Employee, Department, Designation, Branch, Company | **Own record, limited to people data** (attendance, leave, claims, goals…) — **not** recruitment records | **Every** opening, applicant, requisition, referral and interview; **only themselves** for everything else |
| **T6 · Leadership** | ⚠ No template yet | — | Should be **aggregates**, not every payslip. There is no leadership view today, so owners borrow HR Manager — see §5 |
| **T7 · System admin** | System Manager | None | Configuration. **Not** a reason to read people data |

### The locks that go with every template

| Lock | Setting | Why |
|---|---|---|
| **L1** | Employee and Employee Self Service roles: **no Report and no Export on Attendance** | Nobody but HR pulls a spreadsheet of attendance, even if a User Permission is ever missing |
| **L2** | Employee Birthday report: **HR roles only** | It shows birth year and gender. Frappe HR's birthday email already covers team culture without them |
| **L3** | **Salary and bank fields on the Employee record locked** (permlevel 1): CTC, salary currency and mode, PAN, PF, ESI, bank name, account, IFSC, MICR, IBAN, employee advance account, payroll cost centre. Readable by **HR Manager, Payroll User, System Manager** only | Otherwise anyone who can open an Employee record reads their pay. Measured at PP Jewellers: a floor manager read 18 colleagues' CTC, and recruitment, training and HR executives read all 402 |
| **L4** | **The Employee and Employee Self Service roles do not read pay records in the desk**: Salary Slip, Salary Structure Assignment, Employee Incentive, Retention Bonus, Employee Other Income, Employee Benefit Ledger, Payroll Correction, Salary Withholding. Payroll Period and Salary Component stay readable — reference lists that reveal nobody's pay. Employees see **their own** payslip in the portal, which checks ownership on the server | The Employee role's read relies on a User Permission to narrow it to the person. Wherever that permission is wider (a manager's reporting line) or missing (central staff), everyone else's pay showed. Measured: a store in-charge opened 71 payslips, HR executives 400. **Requires the portal payslip view to be deployed first**, or employees lose access to their own payslip |

## 3. Choices only the organisation can make

These are what the configuration page will ask. **Never infer them from roles.**

| Choice | Example | Why a role cannot answer it |
|---|---|---|
| **Is each HR person central or location HR?** | A store HR executive vs a head-office payroll executive | Both hold HR User; their scope is opposite |
| **Is payroll run centrally or per location?** | Decides T5's scope | Same |
| **Does a manager see their whole tree, or direct reports only?** | A store in-charge usually needs the whole store; some organisations want direct reports only | Frappe covers the whole tree by default. "Direct only" needs `hide_descendants` and a permission per report |
| **Can managers use the desk, or only the portal?** | Many retail managers never open the desk | Changes whether desk reports matter at all |
| **Who is the leadership persona, and what do they see?** | Owner, MD, board | Today the only option is HR Manager |

## 3a. How HR User was reshaped, and why not replaced

HR User is checked **by name in 25 places** in the portal — HR screens, the
organisation attendance view, report access lists. A new role copied from it
would silently lose all of those. So payroll was **taken out of** HR User and put
into **Payroll User**, which is the split Frappe HR itself ships. Anyone who needs
both holds both.

## 4. Known limits in Frappe, stated

- **A branch permission only filters records that have a branch field.**
  Employee and Salary Slip do; **Attendance does not**. So T3 location HR is
  scoped for people and pay, but **still sees every location's attendance**.
  Closing that needs a branch field on Attendance — a customisation, not a
  setting, and a product decision.
- **User Permissions are not inherited across doctypes.** A branch limit does not
  pass through an employee to their expense claims.
- **A second login is invisible to all of this.** A user with no linked Employee
  record gets no reporting-line scope at all.
- **The Employee role is the back door.** Its read on any record type assumes a
  User Permission narrows it to the person. Anyone holding the Employee role with a
  wider permission, or none, inherits company-wide read through it. Every new
  record type the Employee role can read needs the same question asked.
- **Training** cannot use a Training User role on a tenant that has not bought the
  training feature: the plan module removes non-admin permissions from those
  records at every sync.
- **After a plan change**, the plan module restores the permission snapshot taken
  before a feature was switched off. Roles added since then lose their access and
  must be re-applied.

## 5. Gaps these templates expose

| Gap | Size |
|---|---|
| **No leadership view.** Owners hold HR Manager to see the business, and get every salary with it | Product — a totals view |
| **HR User is one bucket.** Recruitment and training staff get payroll reports because payroll sits behind the same role | Role design |
| **Attendance has no branch field** | Customisation — see §4 |
| **The configuration page does not exist** | Build — see §6 |

## 6. The tenant permission configuration page — outline

After a tenant is created, a system admin opens one page:

1. **Pick a starting template set** — "Retail, multi-location", "Office, single site", "Central HR".
2. **Answer the §3 choices.**
3. **Map people**, where roles cannot: which HR people are central and which are location HR.
4. **Only features the tenant bought appear.** No payroll choices without payroll.
5. **Preview before applying** — for chosen people, "can see N people in Attendance, N in Salary Register" — the same measurement used to review PP Jewellers.
6. **Check approvers.** Refuse to apply if any leave or expense approver would lose sight of the people they approve.
7. Apply, and record who applied what and when.

Until it exists, a system admin applies templates by hand, per client.
