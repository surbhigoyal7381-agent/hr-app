# Alvoraa subscription plans and module access — strategy

**Status:** approved 2026-08-23. Wave 1 built — see `alvoraa_portal/subscription.py`.
**Scope:** the whole tenant — Frappe desk, Frappe HR, ERPNext, and the Alvoraa portal.

---

## 1. The product model

> **Everything Frappe HR does is an Alvoraa HR feature.**
> **Everything ERPNext does is available only on the Custom plan.**

Alvoraa HR is not a wrapper around Frappe HR — it *is* Frappe HR, plus the layer we have
built on top. Customers buy HR capability, not a distinction between which upstream project
supplies it.

ERPNext is a different proposition: accounting, stock, manufacturing, selling. A company
buying HR software does not want it, and showing it makes the product look unfocused. It
belongs behind a Custom plan for customers who ask.

---

## 2. What we actually have to sell

Verified on the running site — these are real, not aspirational.

### Alvoraa HR — from Frappe HR (9 feature areas)

| Feature area | Module | What it covers |
|---|---|---|
| **Leaves** | HR | applications, allocations, policies, encashment |
| **Shift & Attendance** | HR | shifts, check-ins, attendance requests, regularisation |
| **Expenses** | HR | expense claims, advances, travel |
| **Tenure** | HR | onboarding, transfers, promotions, separation |
| **Recruitment** | HR | job openings, applicants, interviews, offers |
| **Performance** | HR | appraisals, feedback |
| **HR Setup** | HR | company HR policy, holiday lists, settings |
| **Payroll** | Payroll | salary structures, slips, payment entries |
| **Tax & Benefits** | Payroll | tax slabs, exemptions, benefit claims |

### Alvoraa HR — built by us

| Feature | App / module | Surface |
|---|---|---|
| **Employee Portal** | `alvoraa_portal` | `/hrms-employee` — the branded self-service app |
| **Goals & KPIs** | `alvoraa_goals` | goals panel, cascade, evidence, `/goals-portal` |
| **Performance Management** | `hrms` (our fork) | 37-doctype PMS: cycles, calibration, scorecards |
| **Analytics** | `alvoraa_portal` | HR analytics panel |
| **Vendor & Driver Portal** | `alvoraa_portal` | `/vendor-portal`, `/driver-portal` |

### ERPNext — Custom plan only

**Sellable business modules (11):** Accounts, Assets, Buying, CRM, Maintenance,
Manufacturing, Projects, Quality Management, Selling, Stock, Support.

**Infrastructure (10):** Setup, Regional, Utilities, Communication, Portal, Bulk
Transaction, EDI, ERPNext Integrations, Subcontracting, Telephony. These are plumbing, not
features. They stay installed and stay hidden on every plan.

---

## 3. A constraint that shapes everything

**Frappe HR depends on ERPNext.** Measured by walking every link field on HR and Payroll
doctypes:

| ERPNext module | What Frappe HR links to |
|---|---|
| Accounts | Bank Account, Journal Entry — payroll posting, expense reimbursement |
| Assets | Asset Movement — employee asset issue |
| Buying | Supplier — expense claims |
| Projects | Project, Task, Timesheet — timesheet-driven payroll |
| Setup | Terms and Conditions, Vehicle — fleet, offer letters |
| Stock | Delivery Trip — driver assignment |

So **ERPNext can never be uninstalled**, on any plan. Removing it breaks payroll and
expenses.

This is why the gate is *visibility and permission*, not installation: the doctypes must
keep working underneath while the modules stay out of sight and out of reach.

---

## 4. Revised subscription plans

Built from the feature areas above, not from the current arbitrary module list.

| Feature | **Starter** | **Business** | **Enterprise** | **Custom** |
|---|:--:|:--:|:--:|:--:|
| Employee Portal | ✅ | ✅ | ✅ | ✅ |
| Leaves | ✅ | ✅ | ✅ | ✅ |
| Shift & Attendance | ✅ | ✅ | ✅ | ✅ |
| Expenses | ✅ | ✅ | ✅ | ✅ |
| HR Setup | ✅ | ✅ | ✅ | ✅ |
| Tenure — onboarding / exit | — | ✅ | ✅ | ✅ |
| Recruitment | — | ✅ | ✅ | ✅ |
| Payroll | — | ✅ | ✅ | ✅ |
| Tax & Benefits | — | ✅ | ✅ | ✅ |
| Performance & Appraisals | — | — | ✅ | ✅ |
| Goals & KPIs | — | — | ✅ | ✅ |
| Analytics | — | — | ✅ | ✅ |
| Vendor & Driver Portal | — | — | ✅ | ✅ |
| **ERPNext modules** (11, individually) | ➕ | ➕ | ➕ | ➕ |

➕ = tickable per tenant on any plan; ticking any makes the plan name *Custom*.

**The shape of the ladder:**

- **Starter** — employee self-service. Leave, attendance, expenses. The things every
  company needs on day one.
- **Business** — running an HR department. Adds hiring, the employee lifecycle, and
  payroll.
- **Enterprise** — managing performance. Adds appraisals, goals, analytics, and the
  vendor/driver portals.
- **Custom** — anything else.

**Plans are presets, not cages.** The control-plane admin sees ONE catalogue — the 13
Alvoraa HR features and the 11 ERPNext modules — and ticks whatever a tenant should have.
Picking a plan ticks a standard set; the admin is then free to add or remove anything.

The plan *name* is derived from what ends up ticked: matches a preset, and it is that plan;
anything else is **Custom**. So a Starter tenant that also needs Accounts is simply
Starter + Accounts, recorded as Custom. Nobody is pushed up a tier to buy one module.

---

## 5. How each plan is enforced

Four mechanisms, verified present. Only two of them actually deny anything.

| Mechanism | Effect | Enforces? |
|---|---|---|
| `user_type` = Website User | no desk at all | ✅ |
| **Roles / permissions** | server-side doctype access | ✅ |
| **Module Profile** → `block_modules` | hides modules from the desk UI | ❌ UI only |
| App not installed | doctypes do not exist | ✅ (only for our apps) |

**Module blocking hides; roles deny.** Blocking Payroll removes it from the sidebar but
does not stop `/api/resource/Salary Slip` if the role permits it. Both are needed: the
profile for a clean product, the roles for the boundary.

Per plan, provisioning would:

1. Set `modules_enabled` from the plan — one recorded source of truth
2. Build a **Module Profile** blocking every feature area not in the plan, plus all 21
   ERPNext modules unless Custom
3. Grant only the **roles** the plan includes; withhold the rest
4. Install `alvoraa_goals` / `alvoraa_portal` only when those features are sold
5. Create employees as **Website Users** — the portal is their interface; the desk is for
   HR and admins

Recruitment needs care: it has **no module of its own** (Job Opening, Job Applicant and
Interview all sit in the `HR` module), so it can only be gated by roles and permissions,
never by module blocking.

---

## 6. Delivery

| Wave | What | Risk |
|---|---|---|
| **1** | Feature registry + plan definitions, one source of truth, tests | none |
| **2** | Module Profile per plan; hide all ERPNext modules on non-Custom | low — UI only |
| **3** | Employees provisioned as Website Users | medium — prove on one user first |
| **4** | Role grants and withholding per plan | **highest** — this denies access |
| **5** | Conditional app install for goals / vendor | low |
| **6** | Portal API + route + UI gating | low |

Wave 2 alone makes the product look like an HR product instead of an ERP.

---

## 7. Decisions — settled 2026-08-23

| Question | Decision |
|---|---|
| Plan ladder in §4 | **Approved as written.** Recruitment stays in Business |
| Custom plan | ERPNext modules **pickable individually**, not bundled |
| Downgrade | **Hide and keep the data.** Never uninstall — `bench uninstall-app` drops tables |
| PMS vs Frappe HR Performance | **One sellable feature.** Both ship under "Performance & Appraisals" |
| Live sites staying Enterprise | **Intended.** They are demos, or empty core sites used to provision tenants |

Recorded in code as `PLANS` and `FEATURES` in `alvoraa_portal/subscription.py`, with tests
that assert the ladder rather than trusting it.

## 8. Housekeeping found on the way

`alvoraa_portal` and `alvoraa_goals` each still register **two** Module Defs — the live one
and an `Alvox` leftover from the rebrand:

```
alvoraa_portal   Alvoraa Portal, Alvox Portal
alvoraa_goals    Alvoraa Goals, Alvox Goals
```

Harmless, but they will appear in any module list we build a Module Profile from. Worth
deleting before this work, not during.

---

## 9. What I need from you

Approval of the plan ladder in §4 and answers to §7. Then wave 1 — the feature registry and
plan definitions — which is small, testable, and the thing every later wave reads from.

---

## 10. Open: Frappe's own 11 modules

Wave 2 hides ERPNext's 21 and any unsold Alvoraa HR module. Measured on a Starter
site afterwards: **24 hidden, 13 still visible** — and 11 of those 13 are Frappe
*framework* modules, which this strategy never considered:

```
Automation  Contacts  Core  Custom  Desk  Email
Geo  Integrations  Printing  Website  Workflow
```

So a Starter tenant's desk still offers Website, Integrations and Automation.

They split into two kinds:

| | Modules | View |
|---|---|---|
| **Noise for an HR tenant** | Website, Integrations, Automation, Geo, Printing, Contacts, Email, Workflow, Custom | hide by default |
| **The desk itself** | Core, Desk | must stay — hiding these risks breaking navigation |

This is a product decision, not a technical one, so it is recorded here rather
than assumed. My recommendation is to hide the first row for every tenant and
keep them available on the control plane, where they are genuinely used.
