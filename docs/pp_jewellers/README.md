# PP Jewellers — Demo Specification (index)

**Client:** PP Jewellers Pvt Ltd — 5 jewellery stores (Chandigarh, Ambala, Noida, Delhi Karol Bagh, Delhi South Extension) and one head office in Chandigarh. 400 employees.
**Purpose:** a complete, step-by-step specification that Cowork can follow to build the PP Jewellers demo on a **new demo tenant, `ppj.dev.alvoraa.co`**, on the Enterprise plan.
**Written:** 2026-09-07. **Status:** spec complete; seed suite written and verified end to end on a local bench (file 11); tenant not yet created (needs server access); six product builds and one hotfix awaiting approval (file 10). Fiscal year April to March. Completed quarter for the appraisal: Q1 FY27 (1 Apr to 30 Jun 2026). In-progress quarter: Q2 FY27 (1 Jul to 30 Sep 2026).

## How to read this folder

Read the files in order. Each file says what to configure, the exact doctype and field values, which persona sees it, and how to check it worked.

| # | File | What it covers |
|---|---|---|
| 00 | `00-demo-instance-and-plan.md` | Creating the `ppj.dev.alvoraa.co` tenant from the control plane, the Enterprise feature set, why no ERPNext or Indian Compliance, and the opt-in rule for the new builds |
| 01 | `01-client-context-and-storyline.md` | Who PP Jewellers is, their pain points, the three personas, the 25-minute demo script |
| 02 | `02-organisation-and-master-data.md` | Company, branches, departments, designations, grades, holiday lists, 400 employees, reporting tree |
| 03 | `03-attendance-policy-and-essl.md` | Shift, ESSL punch feed (simulated now, real later), the quarter-day late rule as a product feature, simulated punch data |
| 04 | `04-payroll.md` | Salary components (Basic, HRA, PF, ESI, incentives, late deduction), salary structures per grade, payroll runs |
| 05 | `05-sales-targets-and-incentives.md` | Article categories, quarterly store targets, per-role targets as KPIs, incentive components |
| 06 | `06-recruitment-end-to-end.md` | Senior Sales Executive hiring run: requisition, JD, screening questions, 3 interview rounds, selection parameters, offer |
| 07 | `07-onboarding-and-employee-documents.md` | Pre-onboarding (BGV, police verification), the Employee Documents feature, onboarding template, 3-day induction |
| 08 | `08-policy-library-feature-spec.md` | Central policy library as a core-module feature: doctypes, sharing rules, portal widget |
| 09 | `09-performance-management.md` | Core values, Goal Cascade per store, KPIs per role, attendance-weighted appraisal (feature update), potential and overall ratings, 9-box |
| 10 | `10-build-list-and-impact-analysis.md` | The five product builds the demo needs, each with the mandatory impact analysis from `CLAUDE.md` §2 |
| 11 | `11-cowork-execution-checklist.md` | The ordered checklist Cowork runs, with a verification step after each block |
| data | `data/*.csv` | Generated data: employees, designations, KPI library, policies, applicants, sales targets |

Generator scripts live in `demo/pp_jewellers/` (the `demo/` folder is git-isolated from `main`, see `demo/README.md`).

## Decisions already taken (from the 2026-09-07 review)

| Topic | Decision |
|---|---|
| Custom builds | Yes. The spec includes six product builds, each with its own impact analysis and approval gate (file 10). Each is registered as an opt-in feature and switched on for the ppj tenant from the console (file 00 §3). Nothing is coded until each build is approved. |
| Target site | A **new tenant `ppj.dev.alvoraa.co`**, created from the control-plane console, plan Enterprise (all 13 Alvoraa HR features), subscription status Internal. No ERPNext modules, no Indian Compliance. See file 00. Changed on 2026-09-07 from `dev.alvoraa.co`. |
| Quarter-day rule | Week starts Monday. Late arrival (more than 60 minutes) and early exit (more than 60 minutes) both count. First violation in a week is free. Deduction is taken from leave balance first, then loss of pay. |
| Store timings | 9:30 to 18:30 at all five stores and head office. Stores open 7 days a week, including festival days, with a rotating weekly off. Head office closed on Sunday. |
| ESSL | Simulate all punches for the demo. The real integration design is in file 03, based on the eSSL eBioServerNew Web API manual (v1.3, 27 March 2025). |
| Incentives | No calculation engine. Incentives are salary components entered per month. Targets and attainment are shown separately as KPIs. |
| Recruitment content | No client material supplied. JD, screening questions and selection parameters are written in this spec. Three rounds: HR screening, Store In-charge interview, Owner final round. |
| Core values | Linked to goals, plus one manager-rated "Living our values" KPI, so everything stays in one scoring path. |
| Appraisal weights | Attendance regularity 20, manager feedback 30, targets achieved 50. Same weights for head office, with non-sales KPIs. |
| Document collection | A document table on the Employee record itself. The responsible person attaches each document there (file 07). |
| Policy library | A core-module feature with department-level ownership and role-based read/write sharing, shown as a Policies widget on the portal home page (file 08). |
| Attendance in appraisal | Generalise the existing attendance hook into a product feature, configurable from the portal cycle wizard (file 09). |
| Performance stack | Alvoraa Goals (KPIs, potential, overall rating) bridged into HRMS Appraisal for the final score. The PMS module is not used in this demo (see file 09 §1 for why). |

## Assumptions I made where no answer was given

- Client name spelt "PP Jewellers". One legal company. Stores are Branches.
- Nobody sits between Store In-charges and the Owner.
- All 400 employees are seeded. Two months of punch data (July and August 2026) plus 1 to 6 September.
- Leave deduction order for the late rule: Casual Leave, then Earned Leave, then Loss of Pay.
- Statutory rates in file 04 are the commonly used ones. They are marked "verify" because they change and I cannot confirm the current values.
