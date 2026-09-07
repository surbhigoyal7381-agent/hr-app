# 11 — Cowork execution checklist

Run the blocks in order on `ppj.dev.alvoraa.co`. Each block ends with a check. Do not start the next block until the check passes. Blocks marked **(build)** depend on a product build from file 10 being approved and deployed first; the demo can be built up to that point without them.

Conventions: "desk" = the Frappe UI; "console" = `bench --site ppj.dev.alvoraa.co console` inside the backend container, with scripts copied to `/tmp` first (see `demo/README.md`); "portal" = `/hrms-employee`.

Data files are in `docs/pp_jewellers/data/`. Generator scripts in `demo/pp_jewellers/` are already run; re-run them only if you change the inputs.

## Block 0 — Create the tenant (file 00)

- [ ] Confirm the dev stack runs the `dev` image built from today's commits (feature registry with opt-in, subscription records). `BASE_DOMAIN` in `deploy/envs/dev.env` on the server must be `dev.alvoraa.co`.
- [ ] Control-plane console `/alvoraa-admin` → New tenant: subdomain `ppj`, tenant name "PP Jewellers (demo)", company PP Jewellers Pvt Ltd / PPJ / India / INR / Asia/Kolkata / FY start 1 April. Tick all 13 Alvoraa HR features (the Enterprise bundle, vendor included). No ERPNext modules. No Indian Compliance.
- [ ] Wait for the provisioning job; save the Administrator password from the status screen.
- [ ] Server: `deploy/add_tenant_cert.sh ppj.dev.alvoraa.co --dry-run`, then without `--dry-run`. Check `https://ppj.dev.alvoraa.co/alvoraa-login` loads with a valid certificate.
- [ ] Control plane desk: Alvoraa Subscription for `ppj.dev.alvoraa.co`, status Internal, plan Enterprise, started today. Run one health check and one usage collection from the tenant page.
- [ ] On the tenant: `bench --site ppj.dev.alvoraa.co list-apps` shows alvoraa_goals and not india_compliance. Desk shows the HR workspaces and no Accounts / Selling / Stock.
- [ ] Take a first backup of the empty tenant (`bench --site ppj.dev.alvoraa.co backup`) as the "clean" restore point.
- [ ] HR Settings on the tenant: Employee naming by Employee Number; leave approver mandatory; interview reminders on.
- [ ] Register the demo merge driver locally: `git config merge.ours.driver true`.

Every step below runs on the **ppj tenant**, never on `dev.alvoraa.co`.

## Block 1 — Company and masters (file 02)

- [ ] Company, two Fiscal Years, 6 Branches, 6 Shift Locations, 17 Departments with Department Heads for head office (Department Head = the "Head - …" employee, set after Block 2).
- [ ] 48 Designations from `data/designations.csv`; 6 Employee Grades with the CTC bands.
- [ ] 21 Holiday Lists (5 per store city × 4 cities + head office). Use "Add Weekly Holidays" for the off day.
- [ ] 5 Leave Types, Leave Policy "PPJ Standard Leave Policy".
- Check: Branch list = 6, Designation list = 48, Holiday List = 21.

## Block 2 — Employees (file 02 §7)

- [ ] Data Import: Employee from `data/employees.csv`, first pass without `reports_to` (map the columns; leave `esi_number` unmapped until B2).
- [ ] Second pass: update `reports_to` from the same file.
- [ ] Console: `demo/rebuild_nsm.py`, then `demo/fix_hierarchy.py` to prove the tree is clean.
- [ ] Console: `demo/link_employee_users.py` to create Users for all 400 (or at least the 5 personas), then assign roles per file 02 §10 and User Permissions on Branch for store managers.
- [ ] Leave Policy Assignment for all 400 for 2026-04-01 to 2027-03-31; run allocation.
- [ ] Leave Application for PPJ-0058: Casual Leave, 2026-05-11 to 2026-05-15 (5 days, "sister's wedding"), Approved and submitted. This sets up the loss-of-pay story.
- Check: Employee count 400 Active; each persona can log in to the portal and sees their name and store.

## Block 3 — Shifts, punches, attendance (file 03)

- [ ] Two Shift Types with the values in file 03 §1. Shift Assignments from 2026-07-01.
- [ ] Copy `data/punches.csv` to `/tmp/punches.csv` in the container; console: `demo/pp_jewellers/seed_attendance.py`. Takes a few minutes for 45,140 rows.
- [ ] Check: Employee Checkin ≈ 45,140; Attendance ≈ 22,570 submitted; Monthly Attendance Sheet for August, Chandigarh, shows L flags; PPJ-0054 has late entries on 18 and 20 Aug and early exit on 22 Aug.
- [ ] **(build B1)** Console → ppj tenant → Edit modules → tick `late_rules`. Then create Attendance Deduction Rule "PPJ Late Coming Rule" with the defaults; click "Run for range" 2026-07-01 to 2026-09-06.
- [ ] Check: Attendance Deduction list matches `data/expected_deductions.csv` (212 rows). PPJ-0054 week 17 Aug = 0.5 from Casual Leave. PPJ-0058 week 3 Aug = 0.5 leave + 0.5 LWP with an Additional Salary dated 2026-08-09.

## Block 4 — Payroll (file 04)

- [ ] Payroll Settings per file 04 §1. Payroll Period FY 2026-27. Income Tax Slab (verify slabs).
- [ ] 17 Salary Components. **(build B2)** for ESI components and the two custom fields (no console tick needed; B2 lives inside payroll); without B2, skip the ESI lines and note it.
- [ ] 5 Salary Structures, submitted. Bulk Salary Structure Assignment by grade with `base` = `monthly_ctc`.
- [ ] Employee Incentives from `data/sales_actuals_july.csv` (150 rows with `incentive_inr` > 0), payroll date 2026-08-31, plus Floor Manager, Store In-charge and Store Performance incentives per file 05 §5. Do this by a console loop, not by hand.
- [ ] Payroll Entry July 2026: create, get employees, create slips, submit. Same for August.
- [ ] Check: 800 submitted slips. PPJ-0054 August slip has Gold Incentive 9,200. PPJ-0058 August slip has Late Coming Deduction > 0. Salary Register totals per branch.

## Block 5 — Recruitment (file 06)

- [ ] Job Applicant Sources (5), Skills (9), Offer Terms (6), Job Offer Term Template, Appointment Letter Template, Staffing Plan.
- [ ] Job Requisition (Noida), approve as Owner. Job Opening with the JD, published.
- [ ] **(build B3)** tick `screening_forms` for the ppj tenant in the console. Block 5 of the seed sets the screen-out rules on the opening, creates the client-worded web form `ppj-senior-sales-application` and screens the eight applicants (Rohit, Preeti and Sunil come out Screened Out).
- [ ] 8 Job Applicants from `data/applicants.csv` with statuses; Employee Referral for Shalini.
- [ ] 3 Interview Types with expected skills, pass marks and interviewers. Interviews and Interview Feedback per file 06 §7 (11 interviews, 11 feedback records with skill assessments). Submit the feedback.
- [ ] Job Offer for Ritika Malhotra, Accepted 2026-08-20. Appointment Letter. Job Requisition → Filled.
- [ ] Check: Recruitment Analytics: 8 applicants, 1 offer, 1 accepted. Ritika's record shows 3 interviews with averages 4.3 / 4.4 / 4.7.

## Block 6 — Onboarding and induction (file 07)

- [ ] Roles Store Admin, Store Manager, Payroll User, Trainer; assign to the right users (Noida Store HR & Admin, Noida Store In-charge, Payroll & Compliance Executive, Training & Development Executive).
- [ ] Employee Onboarding Template "PPJ Store Staff Onboarding" with 12 activities.
- [ ] **(build B4)** tick `employee_documents` for the ppj tenant in the console; block 1 of the seed creates the 18 Employee Document Types and block 2 marks existing staff's rows Verified (PPJ-0200's police certificate Expired).
- [ ] Employee Onboarding for Ritika from her Job Offer, boarding begins 2026-08-21, joining 2026-09-01. Submit. Close tasks 1 and 4; leave 2 and 3 open for the demo moment, or close all and screenshot the block message beforehand.
- [ ] Create Employee PPJ-0401 from the onboarding (after closing 2 and 3). Set device id 0401, shift, holiday list Noida - Off Wednesday, grade G3, salary structure assignment.
- [ ] **(build B4)** block 6 fills her Employee Documents rows per file 07 §3.5 (14 Verified, police certificate Received, salary slips Pending).
- [ ] Training Program "PPJ Store Induction", 3 Training Events (1 to 3 Sep) with Ritika and two other joiners, Training Result, Training Feedback.
- [ ] Check: onboarding Completed; Employee exists; 3 training events.

## Block 7 — Policy library (file 08) **(build B5)**

- [ ] Tick `policy_library` for the ppj tenant in the console.

- [ ] Run block 7 of the seed (`seed_policies.py`): Department Heads on the departments, the 16 policies from `data/policies.csv` published (real text for the five that are opened), acknowledgements for everyone who joined before August, the Old Gold policy with unpublished changes.
- [ ] Log in as PPJ-0054: widget shows 9 policies. Store In-charge: 12. Owner: 16 (department heads and HR Managers read everything).
- [ ] Ritika acknowledges the 8 "acknowledge on joining" policies from the portal (Grievance Redressal is read-only); the onboarding task whose name contains "policy" completes by itself.
- [ ] Head - Purchase & Sourcing opens Policies → Manage, edits "Old Gold Exchange and Valuation Policy" (it already carries draft changes), publishes with a change note; Gold Valuers see "To acknowledge".

## Block 8 — Performance (file 09)

- [ ] 5 Company Values, Alvoraa Rating Scale "PPJ 5-Point" (default), 3 Leadership Principles, 7 Employee Feedback Criteria, Appraisal Template "PPJ Standard".
- [ ] HR portal → cycle wizard: create "Q1 FY27 Performance Cycle" (Apr–Jun) and "Q2 FY27 Performance Cycle" (Jul–Sep), all 400 employees. **(build B6)** tick `attendance_scoring` for the ppj tenant in the console, then in the wizard step "How the Score Is Built" switch attendance on and set 50 / 30 / 20 (the seed does the same through the cycle fields; the cycle writes the formula itself).
- [ ] Goal Cascades for Q1 and Q2 with the store → floor → individual tree from `data/sales_targets.csv` (console script; 5 + 15 + 190 goals per quarter).
- [ ] KPIs for all 400 for both quarters from `data/kpi_library.csv` (console script; generic 3-KPI set for roles not in the library). Q1: actuals and manager ratings filled; Q2: July and August progress logs from `data/sales_actuals_july.csv`.
- [ ] Goal Evidence for July and August on every "Own sales" goal; run `recalculate_progress`. Run the alignment check on both cascades: Aligned (fixed in file 10).
- [ ] Q1: Employee Performance Feedback per employee (submitted), potential ratings on KPIs, overall ratings on the extensions, generate and submit all 400 appraisals, calibration adjustments for 6 employees, calibration sign-off, cycle status Completed.
- [ ] Q2: generate 400 Draft appraisals; manager ratings on ~150 KPIs; leave PPJ-0054 unrated for the live demo.
- [ ] Upward Feedback from ~60 store staff for Q1.
- [ ] Check: file 09 §11.

## Block 9 — Dress rehearsal

- [ ] Walk the 25-minute script in file 01 §4 as each persona. Fix anything that does not load.
- [ ] Take screenshots of every demo moment as a fallback.
- [ ] Re-run `bench --site ppj.dev.alvoraa.co backup` and keep this backup as the "demo-ready" restore point.

## Verified on a local bench, 2026-09-07

The whole suite was run end to end on a bench built like the production image (Frappe 16.33 on Python 3.14, ERPNext 16.34, this repository's `hrms`, `alvoraa_goals` and `alvoraa_portal`), on a site whose company setup was completed the way the provisioner does it. Blocks 1 to 6 and 8 ran clean on that first run; block 7 (the policy library) was added with build B5 and the whole suite is re-run in the final verification below. Numbers from `verify_ppj.py`:

| Check | Result |
|---|---|
| Employees | 403 active (400 seeded + Ritika and two September joiners); 72 / 72 / 74 / 73 / 72 per store, 40 head office; one employee without a manager (the Owner) |
| Users, leave | 403 users linked; 1,209 leave allocations; 401 holiday list assignments |
| Attendance | 45,232 check-ins → 23,275 attendance records (22,577 Present, 693 Absent); PPJ-0054 flagged late on 18 and 20 Aug and early-exit on 22 Aug, exactly as scripted. The punch file was regenerated later the same day (45,140 rows, head office closed on Raksha Bandhan); the final verification run refreshes these numbers |
| Payroll | 403 salary structure assignments, 198 incentives, 800 submitted slips, 2 accrual journal entries. August: PF on 400 employees, ESI on 146 (the CSV's ESI-eligible count), income tax on 31. PPJ-0054 August gross 44,200 with Gold Incentive 9,200 |
| Recruitment | 1 requisition, 1 opening, 8 applicants, 11 interviews, 22 feedback records, 1 offer, 1 appointment letter; Ritika's rounds average 4.25 / 4.25 / 4.6 |
| Onboarding | Onboarding In Process (11 of 12 tasks closed, the 30-day check-in open), Employee PPJ-0401 created through it, 3 training events, 1 result, 3 feedback records |
| Performance | Q1 Completed with 403 submitted appraisals and 1,755 rated KPIs; Q2 In Progress with 403 drafts and 596 of 1,755 KPIs rated; 424 goals; cascade progress Q1 105%, Q2 71% to date; PPJ-0054 Q1 final score 4.56 (goal 4.6, feedback 4.36, self 4.76), High Potential; 62 upward feedback records |

Two product bugs surfaced and are written up in file 10: the regional override wrapper (B0, blocks payroll for taxpayers; the local run used the three-line fix) and the cascade alignment report (read Misaligned on any multi-level cascade; fixed with build B6). Three quirks are handled inside the seeds and noted in files 02, 03 and 07.

Run time on a 4-core box: Block 3 about 30 minutes (auto attendance), Block 4 about 8 minutes, Block 8 about 5 minutes, the rest under a minute each. The site needs a running background worker; without one, Frappe refuses new jobs after a few hundred queue up.

**Running it on a fresh local site.** Two things the provisioner does on a tenant have to be done by hand locally, before block 1: complete ERPNext's setup wizard the provisioner's way (`bench --site <site> execute alvoraa_portal.tenant_setup.complete_company_setup --kwargs '{"company_name": "PP Jewellers Pvt Ltd", "company_abbr": "PPJ", "country": "India", "currency": "INR", "timezone": "Asia/Kolkata", "fy_start_date": "2026-04-01"}'`; without it the Company cannot be created because the warehouse types do not exist), and declare the features in the site config (`bench --site <site> set-config -p features '[...]'` with the Enterprise list plus the five opt-in keys), which is what the console tick writes on a tenant. The six builds' hooks ask that list before acting on a stock doctype.

**Known local-bench limitation.** Test modules that render an email template (`test_employee_onboarding`, ERPNext's `test_employee.test_create_user_automatically`, two salary slip tests) error with `bundled_asset ... 'NoneType' object has no attribute 'get'` because the bench has no built assets (`bench build` needs Node 24, which the container lacks). They fail the same way with and without the builds; the production image builds assets.

## Scripts (written, in `demo/pp_jewellers/`)

One script per block, all idempotent, all reading the CSVs in `docs/pp_jewellers/data/`. `run_all.sh` runs them in checklist order on one site; `verify_ppj.py` prints the check numbers listed above.

| Script | Block | Creates |
|---|---|---|
| `provision_ppj.sh` | 0 | Runs on the server: create_tenant on the control plane, waits for the job, adds the TLS name, records the Alvoraa Subscription. Not tested from the development container; read it before running. |
| `seed_masters.py` | 1 | Company (if missing), fiscal years, branches, shift locations, departments, designations, grades, 21 holiday lists, leave types, leave policy and period, shift types, HR Settings |
| `seed_employees.py` | 2 | 400 employees in two passes, tree rebuild, users with the demo password, roles by designation, user permissions, approvers, leave policy assignments, PPJ-0058's May leave |
| `seed_attendance.py` | 3 | Shift assignments, 45,140 check-ins through the punch API, auto attendance for both shifts, the late-coming rule (its run happens in block 4, once salary assignments exist, so the loss-of-pay lines land before the slips) |
| `seed_payroll.py` | 4 | Payroll settings, period, tax slab, accounts, 17 components (ESI included as formula components), 5 structures, 400 assignments, incentives from July sales, July and August payroll with slips submitted |
| `seed_recruitment.py` | 5 | Sources, skills, offer terms, letter template, staffing plan, requisition, opening with the JD, 8 applicants, referral, 3 interview types, 11 interviews with 22 feedback records, offer, appointment letter |
| `seed_onboarding.py` | 6 | Roles, onboarding template, Ritika's onboarding with tasks closed, Employee PPJ-0401 created through it, two more joiners, users and salary for the three, training program, 3 events, result, feedback, skill map |
| `seed_performance.py` | 8 | Values, scale, principles, criteria, template, two cycles with configs, two cascades with the store/floor/individual tree, evidence and progress, ~4,000 KPIs, Q1 feedback and submitted appraisals with extensions, calibration, Q2 draft appraisals, upward feedback |
| `reset_deductions.py`, `reset_payroll.py`, `reset_performance.py` | 3, 4, 8 | Dev-only wipes so a block can be re-seeded from clean. Never on a tenant with real data. |
| `run_all.sh` | 1-8 | `run_all.sh --site ppj.dev.alvoraa.co --bench /home/frappe/frappe-bench [--from n | --only n]` |
| `verify_ppj.py` | all | prints the verification numbers |

On the server, after Block 0:

```
docker cp demo/pp_jewellers compose-backend-1:/tmp/ppj
docker cp docs/pp_jewellers/data compose-backend-1:/tmp/ppj/data
docker exec compose-backend-1 bash /tmp/ppj/run_all.sh --site ppj.dev.alvoraa.co
docker exec compose-backend-1 bash -lc 'cd /home/frappe/frappe-bench/sites && PPJ_SCRIPT_DIR=/tmp/ppj ../env/bin/python /tmp/ppj/verify_ppj.py --site ppj.dev.alvoraa.co'
```

Demo password for every seeded user: `Ppj@2026` (override with `PPJ_DEMO_PASSWORD`). Change it on the tenant after the demo.

The `demo/` folder is git-isolated; add empty stubs on `main` per `demo/README.md` before the next merge.
