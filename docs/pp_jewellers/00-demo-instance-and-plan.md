# 00 — Demo instance and subscription plan

Decision from the 2026-09-07 review: the use case is built on a **new demo tenant, `ppj.dev.alvoraa.co`**, not on `dev.alvoraa.co`. This file says how that tenant is created and which packages it must have. It is written against the `dev` branch as of 2026-09-07, which carries today's subscription changes (feature registry with opt-in, plan derived from features, Alvoraa Subscription records, usage and health pages).

## 1. How the tenant is created

The control plane creates tenants; nobody runs `bench new-site` by hand.

| Step | Where | Value |
|---|---|---|
| 1. Create the tenant | Admin console `/alvoraa-admin` on the control-plane site → "New tenant" (calls `tenant_api.create_tenant`) | Subdomain `ppj`. The site name becomes `ppj.` + `BASE_DOMAIN`, so the dev stack's `BASE_DOMAIN` must be `dev.alvoraa.co` (check `deploy/envs/dev.env` on the server; the committed example still says `dev.kinexus.in`). Tenant name "PP Jewellers (demo)". Company "PP Jewellers Pvt Ltd", abbr PPJ, India, INR, Asia/Kolkata, fiscal year start 1 April. Primary colour `#7a1f2b` (deep maroon), support email as for other demo tenants. |
| 2. Tick the features | Same screen, feature grid | The list in §2. Do not send a plan name; the console derives it from the ticks. |
| 3. Wait for the job | Provision status on the console | The worker runs `deploy/provision_tenant.sh`, installs erpnext → hrms → alvoraa_portal → alvoraa_goals (because Goals is ticked), writes `features` and `subscription_plan` into `site_config.json`, enables the scheduler. Save the Administrator password it returns. |
| 4. TLS | On the server: `deploy/add_tenant_cert.sh ppj.dev.alvoraa.co` | `deploy/nginx.conf` already serves `*.dev.alvoraa.co` and routes it to the dev stack, but the comment there says the certificate does not cover `*.dev.alvoraa.co`. So the site answers on HTTP and fails on HTTPS until the hostname is added to the certificate. HTTP-01 works because nginx serves the ACME challenge for that hostname. Mind the Let's Encrypt limit of 5 duplicate issuances a week; use `--dry-run` first. |
| 5. Subscription record | Desk on the control plane: **Alvoraa Subscription** | `site_name` = ppj.dev.alvoraa.co, `status` = **Internal** (the console then shows the real price and says plainly it is never invoiced), `plan` = the Enterprise Alvoraa Plan, `started_on` = today, `billing_frequency` Monthly, no packs, no add-ons. Without this record the tenant does not appear in usage collection or the health page. |
| 6. Health and usage | Console → tenant page | Run one health check and one usage collection so the tenant page shows numbers, not "never checked". |
| 7. Log in | `https://ppj.dev.alvoraa.co/alvoraa-login` | Administrator, then create the persona users in file 02. |

The control plane logs every reach into a tenant (Tenant Access Log). That is expected and is itself a talking point if the client asks about auditability.

## 2. Packages this use case needs

Plans on `dev` today, from `alvoraa_portal/subscription.py`:

| Plan | Features |
|---|---|
| Starter | portal, leaves, attendance, expenses, hr_setup (these five are `required` and cannot be switched off on any plan) |
| Business | Starter + tenure, recruitment, payroll, tax_benefits |
| Enterprise | Business + performance, goals, analytics, vendor |
| Custom | Enterprise + individually chosen ERPNext modules (and Indian Compliance, which needs ERPNext Accounts) |

What the demo uses, feature by feature:

| Feature key | Label in console | Used by | Needed |
|---|---|---|---|
| portal | Employee Portal | every persona screen | yes (required) |
| leaves | Leaves | leave policy, balances, the late rule's leave deduction | yes (required) |
| attendance | Shift & Attendance | shifts, ESSL check-ins, auto attendance, late rule | yes (required) |
| expenses | Expenses | not in the demo script; stays on because it is required | yes (required) |
| hr_setup | HR Setup | holiday lists, HR Settings | yes (required) |
| tenure | Onboarding & Exit | Employee Onboarding, templates, Employee Documents (build B4) | **yes** |
| recruitment | Recruitment | the Senior Sales Executive hiring run, Interviewer role | **yes** |
| payroll | Payroll | structures, slips, payroll entries, incentives, late deduction line | **yes** |
| tax_benefits | Tax & Benefits | income tax slab, PF, ESI components and reports | **yes** |
| performance | Performance & Appraisals | Appraisal Cycle, Appraisal, Employee Performance Feedback, attendance score (B6). Also switches on the PMS module's workspace; the demo does not open it. | **yes** |
| goals | Goals & KPIs | Goal Cascade, KPIs, potential rating, 9-box, company values | **yes** (installs the `alvoraa_goals` app; it cannot be added by a plan edit later without an app install, so tick it at creation) |
| analytics | Analytics | Owner and HR dashboards, store comparison | **yes** |
| vendor | Vendor & Driver Portal | not used | tick it anyway, see below |
| ERPNext modules (erp_*) | Accounts, Selling, Stock, … | not used. Sales figures are entered as KPI evidence and incentives, not from Sales Invoices (decision in file 05). Payroll's own Journal Entry needs still work because Frappe HR's ERPNext links are never blocked. | no |
| india_compliance | Indian Compliance | not used. PF, ESI and Professional Tax come from Frappe HR's India regional setup, not from this app. It needs ERPNext Accounts and adds GST screens that would confuse a jewellery HR demo. | no |

**Tick exactly the Enterprise bundle** (all thirteen Alvoraa HR features including vendor). The plan label is derived from the set of ticks, so leaving vendor unticked would make the console call this tenant "Custom", which is the wrong story for a sales demo. The vendor portal is a separate URL and never appears on the employee portal home page, so ticking it costs nothing in the demo.

## 3. New builds are opt-in features

Today's commit "Features: a new one is off everywhere until somebody switches it on" changed the rule for anything new: a feature marked `opt_in` in the registry is off on every tenant, including Enterprise, until the console ticks it for a named tenant. The six builds in file 10 must follow this:

| Build | Feature key to register (`opt_in: True`) | Depends on (`requires`) | What it gates |
|---|---|---|---|
| B1 quarter-day late rule | `late_rules` | attendance, leaves, payroll | Attendance Deduction Rule and Attendance Deduction doctypes, their report, the portal cards |
| B2 ESI | none, part of `payroll` and `tax_benefits` | | it is configuration plus one report |
| B3 screening form | `screening_forms` | recruitment | the screening fields and web form |
| B4 Employee Documents | `employee_documents` | tenure | Employee Document Type, the Employee table, the portal cards |
| B5 Policy Library | `policy_library` | portal | the three doctypes, widget and page |
| B6 attendance in appraisal | `attendance_scoring` | performance, attendance | the cycle fields, hook and wizard step |

So the checklist has one extra step after each build is deployed: open the ppj tenant in the console → Edit modules → tick the new feature. That is the path that re-syncs access on the tenant. The registry gates by module def and workspace today; if it cannot scope a single doctype set inside the shared `alvoraa_hr_core` module, give each build its own Module Def so the tick can gate it cleanly. Confirm that against `subscription.py` when B1 is implemented.

## 4. Verification

- Console tenant list shows `ppj.dev.alvoraa.co`, plan **Enterprise**, status Internal.
- `https://ppj.dev.alvoraa.co` loads over HTTPS with a valid certificate.
- Desk sidebar on the tenant shows the Leaves, Shift & Attendance, Expenses, HR Setup, Tenure, Recruitment, Payroll, Tax & Benefits, Performance, Alvoraa Goals workspaces and no ERPNext business workspaces (Accounts, Selling, Stock are hidden).
- `bench --site ppj.dev.alvoraa.co list-apps` shows frappe, erpnext, hrms, alvoraa_portal, alvoraa_goals and not india_compliance.
