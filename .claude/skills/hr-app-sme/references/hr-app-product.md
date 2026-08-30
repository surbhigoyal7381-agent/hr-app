# hr-app (Alvoraa) — product and codebase reference

What the SME must know about *this* product before applying generic Frappe HR
or ERPNext knowledge.

---

## 1. What the product is

A multi-tenant HR, performance-management and vendor/logistics platform built on
the Frappe Framework. It is not a standalone web app — it is a set of Frappe
apps installed into a Frappe bench, one site per tenant.

Live domains: `alvoraa.co` (production), `dev.alvoraa.co`, `minda.alvoraa.co`.
The product was renamed from Grace to Alvoraa; older names survive in code
(`grace_group`, `GRACE_USER_MANUAL.md`).

## 2. Apps in the monorepo

| App | Contains | Size |
|---|---|---|
| `hrms/` | Frappe HR fork — `hr`, `payroll`, `performance_management`, `grace_group`, plus the Vue 3 employee PWA (`frontend/`) and Roster SPA (`roster/`) | 211 doctypes |
| `alvoraa_goals/` | Cascaded goals and KPIs with evidence-based progress, appraisal extensions | 21 doctypes |
| `alvoraa_portal/` | Vendor portal, delivery/driver management, tenant provisioning, appraisal/KPI APIs, branded tenant portals | 22 doctypes |

`alvoraa_goals` doctypes: Alvoraa Appraisal Extension · Alvoraa Cycle Config ·
Alvoraa Rating Scale · Alvoraa Rating Scale Item · Appraisal Action Item ·
Cascade Alignment Report · Company Value · Evidence Duplicate Check ·
Evidence Validator · Goal Cascade · Goal Cascade Version · Goal Check In ·
Goal Evidence · Goal Progress Audit Log · Goal Progress Update ·
Individual Goal · KPI · KPI Additional Reviewer · KPI Progress Log ·
Leadership Principle · Upward Feedback.

`alvoraa_portal` doctypes: Delivery Assignment · Delivery Feedback ·
Delivery Hub · Delivery Hub Service Area · Delivery Order · Delivery Order Item ·
Delivery Partner · Delivery Performance Scorecard · Delivery Status History ·
Delivery Tracking · Driver Rating Summary · Order Rating ·
Partner Performance Rating · Partner Vehicle History · Vehicle Compliance
History · Vehicle Maintenance Compliance · Vehicle Tracking · Vendor ·
Vendor Address · Vendor Order · Vendor Order Item · Vendor User.

Key documents in the repo root: `ARCHITECTURE.md` (deployment and runtime
model), `DEPLOYMENT_RUNBOOK.md`, `KPI_AUTOMATION_STRATEGY.md`,
`OBJECTIVES_KPI_REQUIREMENTS.md`, `KNOWN_ISSUES.md`, `Design_Theme_Guide.md`,
`GRACE_USER_MANUAL.md`, `New_req.md`, `order_tracking.md`.

## 3. The three personas — every spec covers all three

| Persona | Sees | Typical needs |
|---|---|---|
| **CXO** | All companies | Cross-company rollups, calibration, talent flags, org-wide KPI health |
| **HR Manager** | One or several companies | Cycle administration, policy config, exceptions, approvals |
| **Employee** | Own company, own record | Self-service: leave, attendance, claims, goals, check-ins, PWA |

A feature that only works for one persona is not finished. State explicitly what
each persona sees, and how row-level scoping enforces it.

## 4. Overlaps to watch (four ways to do the same thing)

Goals and performance exist in **four** places in this codebase:

1. Frappe HR stock — `Goal` (tree), `Appraisal`, `Appraisal Cycle`, `KRA`,
   `Employee Performance Feedback`.
2. Fork-only PMS — 37 `PMS *` doctypes (cycles, calibration, check-ins,
   upward feedback, talent flags).
3. `alvoraa_goals` — `Individual Goal`, `KPI`, `Goal Cascade`, `Goal Evidence`.
4. ERPNext `Project`/`Task` for delivery work.

**Before proposing anything goal-, KPI- or appraisal-shaped, say which of these
four it belongs in and why the other three are wrong.** This is the highest-risk
duplication area in the product.

Same discipline for: leave (stock only — never a parallel doctype), expenses
(extend `Expense Claim Type` / `Expense Claim Detail`), attendance (Employee
Checkin → Shift Type → Attendance), org structure (see the duplicate-doctype
warning in `erpnext.md` §2).

## 5. Runtime facts that change designs

- **Frappe process model**: web (gunicorn), socketio, scheduler, workers
  (`short`/`default`/`long`), nginx. All share the `sites/` directory.
- **🔴 The scheduler is a cluster-wide singleton.** Two schedulers double-fire
  every job — duplicate emails to real employees and vendors, double-counted KPI
  progress, duplicate scorecards. Never propose a design whose correctness
  depends on a job running exactly once without saying how that is enforced.
- Existing scheduled jobs: `update_delivery_tracking` (~4 min),
  `recalculate_all_progress` and `calculate_driver_ratings` (hourly),
  `send_progress_reminders`, `send_arrival_notifications`,
  `check_compliance_alerts`, `check_cascade_alignment` (daily),
  `generate_monthly_scorecards` (monthly), plus stock Frappe/ERPNext/HRMS jobs.
- `recalculate_all_progress` iterates every goal across every tenant. Its cost
  grows linearly with tenants — budget one `long` worker per ~20 tenants. Any
  new hourly full-scan job needs a cost estimate at 50 tenants.
- **One site = one tenant = one database.** Cross-tenant queries are not a
  thing. Multi-company scoping happens *within* a tenant.
- Redis queue instance must be `noeviction` with AOF; losing queued jobs loses
  notifications, provisioning and scorecards.
- `site_config.json` holds the per-site `encryption_key`. A DB restore without
  it cannot decrypt stored secrets.
- PII lives in `private/files/` — payslips, contracts, IDs.

## 6. Non-negotiable working rules (from `CLAUDE.md`)

These override anything in this skill:

1. **Branch discipline** — work on `dev` unless told otherwise. `main` is
   production releases only.
2. **Impact analysis before any code**, covering functional (cross-module,
   persona, HRMS domain) *and* every NFR dimension: performance, security,
   reliability, scalability, maintainability, data integrity, compliance and
   privacy. State improve / degrade / neutral for each.
3. **Propose strategy, then wait for explicit approval.** "Go ahead with all
   changes" approves implementation, not skipping review and deploy gates.
4. After implementation: run tests, senior architect review, present findings,
   **wait for deploy approval**. Committing is part of deployment.
5. **Frappe-first, no over-engineering.** Reuse Frappe HR and ERPNext doctypes.
   No backwards-compatibility shims, no feature flags, no abstractions beyond
   the task.
6. **Never touch production** (`/var/www/html/hr-app`, `https://alvoraa.co/`).
7. Deploy commands needing explicit approval: `docker cp`, `bench clear-cache`,
   `bench migrate`, `bench build`, `nginx -s reload`, any `git push`, any `scp`.
8. **Write in plain English.** Short sentences. Lead with the answer. Bad news
   first, in bold. Explain a technical word the first time it appears.
9. `demo/` uses a `merge=ours` driver and must never land in `main`.

## 7. Testing

- Python: `bench run-tests --app <app>` for any changed module.
- JS/HTML: manually trace every affected UI flow — desk, PWA (`hrms/frontend`),
  Roster (`hrms/roster`), and the server-rendered portals in
  `alvoraa_portal/…/www/`.
- `hrms/frappe-ui` is a **git submodule**. Clones need `--recurse-submodules` or
  the PWA build fails.
