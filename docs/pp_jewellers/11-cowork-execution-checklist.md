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
- [ ] Copy `data/punches.csv` to `/tmp/punches.csv` in the container; console: `demo/pp_jewellers/seed_attendance.py`. Takes a few minutes for 45,232 rows.
- [ ] Check: Employee Checkin ≈ 45,232; Attendance ≈ 22,616 submitted; Monthly Attendance Sheet for August, Chandigarh, shows L flags; PPJ-0054 has late entries on 18 and 20 Aug and early exit on 22 Aug.
- [ ] **(build B1)** Console → ppj tenant → Edit modules → tick `late_rules`. Then create Attendance Deduction Rule "PPJ Late Coming Rule" with the defaults; click "Run for range" 2026-07-01 to 2026-09-06.
- [ ] Check: Attendance Deduction list matches `data/expected_deductions.csv` (231 rows). PPJ-0054 week 17 Aug = 0.5 from Casual Leave. PPJ-0058 week 3 Aug = 0.5 leave + 0.5 LWP with an Additional Salary dated 2026-08-09.

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
- [ ] **(build B3)** tick `screening_forms` for the ppj tenant in the console; custom fields and web form; set `job_application_route`. Without B3, put the screening answers in the applicant `notes` field and say so.
- [ ] 8 Job Applicants from `data/applicants.csv` with statuses; Employee Referral for Shalini.
- [ ] 3 Interview Types with expected skills, pass marks and interviewers. Interviews and Interview Feedback per file 06 §7 (11 interviews, 11 feedback records with skill assessments). Submit the feedback.
- [ ] Job Offer for Ritika Malhotra, Accepted 2026-08-20. Appointment Letter. Job Requisition → Filled.
- [ ] Check: Recruitment Analytics: 8 applicants, 1 offer, 1 accepted. Ritika's record shows 3 interviews with averages 4.3 / 4.4 / 4.7.

## Block 6 — Onboarding and induction (file 07)

- [ ] Roles Store Admin, Store Manager, Payroll User, Trainer; assign to the right users (Noida Store HR & Admin, Noida Store In-charge, Payroll & Compliance Executive, Training & Development Executive).
- [ ] Employee Onboarding Template "PPJ Store Staff Onboarding" with 12 activities.
- [ ] **(build B4)** tick `employee_documents` for the ppj tenant in the console; 18 Employee Document Types.
- [ ] Employee Onboarding for Ritika from her Job Offer, boarding begins 2026-08-21, joining 2026-09-01. Submit. Close tasks 1 and 4; leave 2 and 3 open for the demo moment, or close all and screenshot the block message beforehand.
- [ ] Create Employee PPJ-0401 from the onboarding (after closing 2 and 3). Set device id 0401, shift, holiday list Noida - Off Wednesday, grade G3, salary structure assignment.
- [ ] **(build B4)** fill her Employee Documents rows per file 07 §3.5; seed PPJ-0200 with an expired police certificate.
- [ ] Training Program "PPJ Store Induction", 3 Training Events (1 to 3 Sep) with Ritika and two other joiners, Training Result, Training Feedback.
- [ ] Check: onboarding Completed; Employee exists; 3 training events.

## Block 7 — Policy library (file 08) **(build B5)**

- [ ] Tick `policy_library` for the ppj tenant in the console.

- [ ] Create the 16 policies from `data/policies.csv`, with content for the five that will be opened. Publish all. Set Department Heads on departments first.
- [ ] Log in as PPJ-0054: widget shows 9 policies. Store In-charge: 12. Owner: 16.
- [ ] Ritika acknowledges the 9 "acknowledge on joining" policies; onboarding activity 8 auto-completes.
- Without B5: create a File Manager folder "Policies" with the 16 PDFs and show it; say plainly that the widget and access rules are the product feature in the spec.

## Block 8 — Performance (file 09)

- [ ] 5 Company Values, Alvoraa Rating Scale "PPJ 5-Point" (default), 3 Leadership Principles, 7 Employee Feedback Criteria, Appraisal Template "PPJ Standard".
- [ ] HR portal → cycle wizard: create "Q1 FY27 Performance Cycle" (Apr–Jun) and "Q2 FY27 Performance Cycle" (Jul–Sep), all 400 employees. **(build B6)** tick `attendance_scoring` for the ppj tenant in the console, then set weights 50 / 30 / 20 in the wizard; without B6, set `final_score_formula` on the cycle by hand to `goal_score * 0.5 + average_feedback_score * 0.3 + self_appraisal_score * 0.2` and say attendance is coming.
- [ ] Goal Cascades for Q1 and Q2 with the store → floor → individual tree from `data/sales_targets.csv` (console script; 5 + 15 + 190 goals per quarter).
- [ ] KPIs for all 400 for both quarters from `data/kpi_library.csv` (console script; generic 3-KPI set for roles not in the library). Q1: actuals and manager ratings filled; Q2: July and August progress logs from `data/sales_actuals_july.csv`.
- [ ] Goal Evidence for July and August on every "Own sales" goal; run `recalculate_progress`; run the alignment check.
- [ ] Q1: Employee Performance Feedback per employee (submitted), potential ratings on KPIs, overall ratings on the extensions, generate and submit all 400 appraisals, calibration adjustments for 6 employees, calibration sign-off, cycle status Completed.
- [ ] Q2: generate 400 Draft appraisals; manager ratings on ~150 KPIs; leave PPJ-0054 unrated for the live demo.
- [ ] Upward Feedback from ~60 store staff for Q1.
- [ ] Check: file 09 §11.

## Block 9 — Dress rehearsal

- [ ] Walk the 25-minute script in file 01 §4 as each persona. Fix anything that does not load.
- [ ] Take screenshots of every demo moment as a fallback.
- [ ] Re-run `bench --site ppj.dev.alvoraa.co backup` and keep this backup as the "demo-ready" restore point.

## Scripts (written, in `demo/pp_jewellers/`)

One script per block, all idempotent, all reading the CSVs in `docs/pp_jewellers/data/`. `run_all.sh` runs them in checklist order on one site; `verify_ppj.py` prints the check numbers listed above.

| Script | Block | Creates |
|---|---|---|
| `provision_ppj.sh` | 0 | Runs on the server: create_tenant on the control plane, waits for the job, adds the TLS name, records the Alvoraa Subscription. Not tested from the development container; read it before running. |
| `seed_masters.py` | 1 | Company (if missing), fiscal years, branches, shift locations, departments, designations, grades, 21 holiday lists, leave types, leave policy and period, shift types, HR Settings |
| `seed_employees.py` | 2 | 400 employees in two passes, tree rebuild, users with the demo password, roles by designation, user permissions, approvers, leave policy assignments, PPJ-0058's May leave |
| `seed_attendance.py` | 3 | Shift assignments, 45,232 check-ins through the punch API, auto attendance for both shifts |
| `seed_payroll.py` | 4 | Payroll settings, period, tax slab, accounts, 17 components (ESI included as formula components), 5 structures, 400 assignments, incentives from July sales, July and August payroll with slips submitted |
| `seed_recruitment.py` | 5 | Sources, skills, offer terms, letter template, staffing plan, requisition, opening with the JD, 8 applicants, referral, 3 interview types, 11 interviews with 22 feedback records, offer, appointment letter |
| `seed_onboarding.py` | 6 | Roles, onboarding template, Ritika's onboarding with tasks closed, Employee PPJ-0401 created through it, two more joiners, users and salary for the three, training program, 3 events, result, feedback, skill map |
| `seed_performance.py` | 8 | Values, scale, principles, criteria, template, two cycles with configs, two cascades with the store/floor/individual tree, evidence and progress, ~4,000 KPIs, Q1 feedback and submitted appraisals with extensions, calibration, Q2 draft appraisals, upward feedback |
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
