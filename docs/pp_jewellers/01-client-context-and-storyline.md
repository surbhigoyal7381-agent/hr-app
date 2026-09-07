# 01 — Client context and demo storyline

## 1. Who PP Jewellers is (as modelled in the demo)

PP Jewellers Pvt Ltd is a family-owned jewellery retailer in North India. The Owner and Managing Director runs the business from the Chandigarh head office. Five stores sell gold, diamond, silver, platinum and gemstone jewellery. Each store is run by a Store In-charge who reports directly to the Owner.

| Location | Branch name in the system | Headcount |
|---|---|---|
| Chandigarh, Sector 17 | PPJ Chandigarh Sector 17 | 72 |
| Ambala City | PPJ Ambala City | 72 |
| Noida, Sector 18 | PPJ Noida Sector 18 | 72 |
| Delhi, Karol Bagh | PPJ Delhi Karol Bagh | 72 |
| Delhi, South Extension | PPJ Delhi South Extension | 72 |
| Chandigarh head office (backend) | PPJ Head Office Chandigarh | 40 |
| **Total** | | **400** |

## 2. Their pain points, and what the demo must prove

| Pain point they told us | What the demo must show |
|---|---|
| Attendance is not transparent. Late-coming is argued about every month. | Punches from the ESSL machines land in the system. The quarter-day rule runs by itself every Monday. Each employee sees their own late list and deductions. The Store In-charge sees the store. HR sees everything. |
| Payroll is manual and disconnected from attendance. PF and ESI are with a third party. | Attendance days flow into the salary slip. Late deductions and category incentives appear as lines on the slip. PF and ESI are computed on the slip, so the third party is optional. |
| Hiring is frequent and they already know their process, but it lives in WhatsApp and Excel. | One full hiring run for Senior Sales Executive: requisition, published opening, screening questions, three rated rounds, offer, appointment letter. Every step visible to the right person. |
| New joiners start without documents or verification being complete. | Pre-onboarding tasks (BGV, police verification, reference check) block employee creation until done. Documents sit on the employee's own record. Induction runs as training events. |
| Policies are in a folder nobody can find. | A Policies widget on every employee's portal home page, filtered by their role and department. Department heads own their policies. |
| No performance appraisal process exists. On paper they want attendance regularity, manager feedback and targets achieved to count. | A completed Q1 appraisal cycle with those three weights (20 / 30 / 50), a live Q2 cycle, KPIs per role cascaded from store targets, core values, potential rating, overall rating, 9-box. |

## 3. Personas and the users to log in as

| Persona | Employee | User (demo login) | What they must see |
|---|---|---|---|
| Owner / CXO | PPJ-0001 Sahil Bhatia, Owner & Managing Director | sahil.bhatia1@ppjewellers.demo | All stores. Store-level attendance, payroll cost, hiring pipeline, Q1 results, Q2 target progress, 9-box. |
| HR Manager | PPJ-0010 Arjun Bhatia, Head - Human Resources | arjun.bhatia10@ppjewellers.demo | Everything HR: attendance exceptions, deduction runs, payroll entry, requisitions, onboarding, policy library admin, cycle setup. |
| Store In-charge | PPJ-0041 Jaspreet Chopra, Store In-charge, Chandigarh Sector 17 | jaspreet.chopra41@ppjewellers.demo | Own store only. Team attendance today, late list, team KPIs, interview feedback for their store's openings, manager ratings. |
| Employee | PPJ-0054 Suresh Sethi, Senior Sales Executive, Chandigarh Sector 17 | suresh.sethi54@ppjewellers.demo | Own attendance calendar, own late list and deduction, own payslip, own KPIs and evidence, own appraisal, policies. |
| New joiner (end of hiring run) | Created during the demo: Ritika Malhotra, Senior Sales Executive, Noida | ritika.malhotra@ppjewellers.demo | Pre-onboarding tasks, document checklist, induction calendar. |

Roles to assign: Owner = `Alvoraa CXO` (or the equivalent all-company role on the site, verify name on dev) + HR Manager read; HR Manager = `HR Manager`, `HR User`, `Interviewer`; Store In-charge = `Employee`, `Leave Approver`, `Expense Approver`, `Interviewer`; Employee = `Employee`.

## 4. The 25-minute demo script

Run it in this order. Each step names the screen and the persona.

| Min | Persona | Screen | What to say and show |
|---|---|---|---|
| 0–2 | Owner | Portal home | "Five stores, 400 people, one screen." Headcount by store, today's attendance by store, pending approvals. |
| 2–6 | Store In-charge | Team → Team Attendance | Today's punches for Chandigarh. Open the late list for last week. Show one Sales Executive with 3 violations and the 0.5-day deduction that ran on Monday. Open the employee's attendance calendar. |
| 6–8 | Employee | Attendance | Same employee's own view: punches, late flags, the deduction record with the rule explained in plain words, leave balance after deduction. |
| 8–11 | HR | Payroll Entry (August 2026) → one Salary Slip | Payment days came from attendance. Lines: Basic, HRA, Gold Incentive, Diamond Incentive, Late Coming Deduction, PF, ESI. "The third party is optional now." |
| 11–15 | HR → Store In-charge → Owner | Recruitment | Job Requisition (Noida, Senior Sales Executive) → Job Opening with screening questions → 8 applicants, 3 screened out by answers → Round 1 HR ratings → Round 2 Store In-charge ratings → Round 3 Owner → Job Offer accepted. Recruitment Analytics report. |
| 15–18 | HR → New joiner | Employee Onboarding | Pre-onboarding tasks: BGV, police verification, reference check, each assigned to a role, with due dates. Employee Documents table on the new joiner's record with statuses. Induction as three Training Events. Try to create the Employee before BGV is complete: the system blocks it. |
| 18–20 | Employee → HR | Portal home → Policies widget | Employee sees 6 policies for their role. HR opens the Policy Library, shows a department head's draft policy, publishes it to "Reporting Managers", it appears for the Store In-charge and not for the Sales Executive. |
| 20–24 | Owner → Store In-charge → Employee | Performance | Q2 Goal Cascade: company target → 5 store targets → floor → individual. Store In-charge rates a Senior Sales Executive's KPIs and "Living our values". Employee's Q1 appraisal: attendance 20, manager feedback 30, targets 50, final score, potential rating, overall rating. Owner opens the 9-box for all stores. |
| 24–25 | HR | Cycle wizard | Show the attendance weight and rule being set in the cycle wizard. "You change the policy here, the score follows." |
