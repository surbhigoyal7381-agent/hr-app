# 07 — Onboarding and employee documents

Three parts: pre-onboarding (verification tasks that block employee creation), the **Employee Documents** feature (build B4 in file 10, decided in the review: documents live on the employee's own record), and induction as training events.

## 1. The joining journey for Ritika Malhotra

| Phase | When | What happens | Object |
|---|---|---|---|
| Offer accepted | 20 Aug | HR creates Employee Onboarding from the Job Offer | Employee Onboarding, status Pending |
| Pre-onboarding | 21 to 31 Aug | Background verification, police verification, reference check, document collection, ESSL enrolment prep, uniform and ID card | Tasks from the template, assigned by role |
| Employee created | 1 Sep | Only possible once the tasks marked "required for employee creation" are complete | Employee PPJ-0401 |
| Soft onboarding | 1 to 3 Sep | Documents verified on the Employee record, portal login, policies acknowledged | Employee Documents table, Policy Library |
| Induction | 1 to 3 Sep | Three Training Events | Training Program "PPJ Store Induction" |
| Confirmation | 1 Mar 2027 | Probation review | Appraisal in the Q3/Q4 cycle |

## 2. Employee Onboarding Template: "PPJ Store Staff Onboarding"

Company PP Jewellers Pvt Ltd, Department Sales, Designation blank (works for all store roles). Activities:

| # | Activity | Role | Begin on (day) | Duration (days) | Required for employee creation | Description |
|---|---|---|---|---|---|---|
| 1 | Collect joining documents | HR User | 0 | 3 | yes | Collect and attach the documents in the Employee Documents checklist (section 3). |
| 2 | Background verification | HR Manager | 0 | 5 | yes | Verify last two employers and dates by phone or email. Record the outcome on the BGV document row. |
| 3 | Police verification | Store HR & Admin (role `Store Admin`) | 0 | 7 | yes | File the police verification form at the local police station. Attach the acknowledgement; attach the certificate when received. Joining can proceed on acknowledgement, not on certificate. |
| 4 | Reference check | Store In-charge (role `Store Manager`) | 1 | 3 | yes | Speak to one reference from the previous store. |
| 5 | Bank, PF and ESI details | Payroll & Compliance (role `Payroll User`) | 2 | 3 | no | Collect bank proof, UAN, ESI number if applicable. |
| 6 | ESSL enrolment and ID card | Store HR & Admin | 5 | 2 | no | Set `attendance_device_id`, enrol face and fingerprint on the store machines, issue ID card. (With the real ESSL integration, the push to the device happens by itself when the Employee is created.) |
| 7 | Uniform and grooming kit | Store HR & Admin | 5 | 2 | no | Two sets of store uniform, name badge. |
| 8 | Portal login and policy acknowledgement | HR User | 8 | 1 | no | Create User, link to Employee, ask the joiner to read and acknowledge the policies marked "acknowledge on joining". |
| 9 | Induction Day 1: Company, values, policies | Training & Development (role `Trainer`) | 8 | 1 | no | Training Event "PPJ Induction – Day 1". |
| 10 | Induction Day 2: Product, hallmarking, certification | Trainer | 9 | 1 | no | Training Event Day 2. |
| 11 | Induction Day 3: Floor, vault, billing, security drill | Store In-charge | 10 | 1 | no | Training Event Day 3, at the store. |
| 12 | 30-day check-in | Store In-charge | 30 | 1 | no | First Goal Check In on the joiner's KPIs. |

Create the roles `Store Admin`, `Store Manager`, `Payroll User`, `Trainer` if they do not exist, and give them to the right head-office and Noida employees' users, so the tasks land with real people in the demo. `notify_users_by_email` = 1.

The template is the stock Frappe HR mechanism: on submit, each activity becomes a Task in a Project "Employee Onboarding : ritika.malhotra@…", assigned as a ToDo to the user or everyone with the role, and the boarding status moves Pending → In Process → Completed as tasks close. Creating the Employee is refused until activities 1 to 4 are complete ("required for employee creation").

**Quirk found while testing:** on submit, Frappe HR creates the onboarding Project with the joining date as its expected start, and ERPNext refuses a Task that starts before its Project. So pre-joining tasks (boarding begins 21 Aug, joining 1 Sep) fail unless the joining date on the onboarding equals the boarding start at submit time. The seed submits with 21 Aug and writes 1 Sep back afterwards. The product fix is one line in `employee_boarding_controller.on_submit`: use `boarding_begins_on` for the Project's expected start date. Add it to build B4.

**Demo moment:** with tasks 1 and 4 done and 2 and 3 still open, click "Create Employee". The system refuses and names the open tasks. Close them, click again, the Employee is created.

## 3. Feature: Employee Documents (build B4)

### 3.1 What the client asked for

"Document collection should be a field associated with each employee. The responsible person should attach all the documents to the employee's profile field itself."

### 3.2 Design

A child table **`Employee Document`** on the **Employee** doctype, added as a Custom Field (Employee belongs to ERPNext, so we do not edit its JSON; the custom field and the child doctype live in the `hrms` fork under the new `alvoraa_attendance`-style module, call it `alvoraa_hr_core`).

`Employee Document` (child table)

| Field | Type | Notes |
|---|---|---|
| document_type | Link `Employee Document Type` | master, section 3.3 |
| status | Select: Pending / Received / Verified / Rejected / Expired | default Pending |
| attachment | Attach | the file. Stored as a private File on the Employee. |
| document_number | Data | e.g. Aadhaar last 4, PAN, UAN |
| issue_date, expiry_date | Date | expiry drives the "Expired" status and a 30-day reminder |
| received_on, received_by | Date, Link User | set when a file is attached |
| verified_on, verified_by | Date, Link User | set when status → Verified; only roles named on the document type may verify |
| remarks | Small Text | e.g. "Police acknowledgement received; certificate pending" |

`Employee Document Type` (master)

| Field | Type |
|---|---|
| document_type_name | Data |
| category | Select: Identity / Address / Education / Employment / Statutory / Verification / Company Issued |
| mandatory_for_joining | Check |
| applies_to_grades | Table MultiSelect Employee Grade (blank = all) |
| verifier_roles | Table MultiSelect Role |
| has_expiry | Check |
| reminder_days_before_expiry | Int (30) |
| collect_from | Select: Employee / HR / Store Admin / Manager |

### 3.3 Standard document types for PP Jewellers

| Document type | Category | Mandatory | Collected by | Verified by |
|---|---|---|---|---|
| Aadhaar card | Identity | yes | Employee | HR User |
| PAN card | Identity | yes | Employee | HR User |
| Passport-size photographs | Identity | yes | Employee | HR User |
| Address proof (current) | Address | yes | Employee | HR User |
| Highest education certificate | Education | yes | Employee | HR User |
| Previous employer relieving letter | Employment | yes | Employee | HR Manager |
| Last 3 months' salary slips | Employment | no | Employee | HR User |
| Bank account proof | Statutory | yes | Employee | Payroll User |
| UAN / PF details | Statutory | no | Employee | Payroll User |
| ESI number (if applicable) | Statutory | no | Employee | Payroll User |
| Background verification report | Verification | yes | HR Manager | HR Manager |
| Police verification acknowledgement | Verification | yes | Store Admin | HR Manager |
| Police verification certificate | Verification | no, has expiry (3 years) | Store Admin | HR Manager |
| Reference check note | Verification | yes | Store Manager | HR Manager |
| Signed offer and appointment letter | Employment | yes | HR User | HR Manager |
| Signed policy acknowledgement | Company Issued | yes | HR User | HR User |
| Vault access authorisation (vault roles only) | Company Issued | for Vault & Inventory Custodian | Store Manager | HR Manager |
| Security agency licence (guards only) | Statutory | for Security Guard | Store Admin | HR Manager |

### 3.4 How it behaves

- **Onboarding hook:** when an Employee is created from an Employee Onboarding, the checklist is filled with every document type that is mandatory or applies to the grade, status Pending. Files already attached to the Job Applicant (resume) are not copied; the joiner's documents are collected fresh.
- **Employee Onboarding view:** a read-only "Documents" section shows the same table with counts (Pending / Received / Verified). Activity 1 in the template says "collect the documents in the checklist".
- **Verification:** only users with a verifier role for that type can set Verified. Others can set Received and attach.
- **Expiry:** a daily job moves rows past `expiry_date` to Expired and notifies HR and the employee 30 days before.
- **Portal (employee):** Profile tab gets a "My Documents" card: the checklist with status, and an upload button for rows where `collect_from = Employee`. Upload sets status Received.
- **Portal (HR):** HR Setup tab gets "Document Compliance": employees with any mandatory document not Verified, by store.
- **Privacy:** attachments are private files. Read access follows Employee read access (self, manager chain, HR). Number fields like Aadhaar hold only the last four digits.

### 3.5 Verification for the demo

- Ritika's Employee record shows 16 rows: 14 Verified, "Police verification certificate" Received with remark "certificate pending", "Last 3 months' salary slips" Pending, "Vault access authorisation" not present (not her grade).
- Document Compliance for Noida shows 1 employee with a pending mandatory document (an existing employee seeded with an expired police certificate, PPJ-0200).

## 4. Induction: Training Program "PPJ Store Induction"

| Training Event | Date | Type | Trainer | Content | Employees |
|---|---|---|---|---|---|
| PPJ Induction – Day 1: Company, values, policies | 2026-09-01 | Seminar | Training & Development Executive (PPJ-0015) | History of PP Jewellers, the five core values (file 09), leave and attendance policy, incentive policy, POSH, code of conduct, grievance channel | Ritika + 2 other September joiners |
| PPJ Induction – Day 2: Product, hallmarking, certification | 2026-09-02 | Workshop | Hallmarking & QC Officer + Head - Design & Quality | Gold purity and BIS hallmarking, diamond 4Cs, IGI/GIA certificates, platinum, gemstones, exchange and buy-back | same |
| PPJ Induction – Day 3: Floor, vault, billing, security | 2026-09-03 | Workshop, at Noida store | Store In-charge Noida | Opening/closing checklist, vault issue and return, billing and KYC rules for high-value sales, CCTV and security drill, grooming | same |

Training Result after Day 2 with a product-knowledge quiz score (Ritika 88%); Training Feedback from each joiner. Employee Skill Map for Ritika updated with the interview skills at their rated proficiency.

## 5. Verification after this block

- Employee Onboarding for Ritika: status Completed, 12 tasks closed, Project 100%.
- Employee PPJ-0401 exists, branch Noida, reports to the Diamond Floor Manager, joined 2026-09-01, `attendance_device_id` 0401, default shift PPJ Store Shift, holiday list Noida - Off Wednesday.
- Three Training Events with Ritika as attendee, one Training Result, three Training Feedback records.
