"""
PP Jewellers demo - Block 6: onboarding of Ritika Malhotra and induction.

Roles for the onboarding owners, the onboarding template (12 activities),
the Employee Onboarding created from her Job Offer (tasks and to-dos are
created by Frappe HR on submit), task completion, Employee PPJ-0401 created
through the onboarding, her user, salary and shift, two more September
joiners for the induction batch, the Training Program with three events,
a Training Result and Training Feedback.

Employee Documents (build B4) are not here.
Idempotent.
"""
import os
import sys

sys.path.insert(0, os.environ.get("PPJ_SCRIPT_DIR", "/tmp/ppj"))
from ppj_common import *  # noqa: F401,F403
from frappe.utils import add_days

connect()
frappe.flags.mute_emails = True

NOIDA = "PPJ Noida Sector 18"
KAROL_BAGH = "PPJ Delhi Karol Bagh"
JOIN = "2026-09-01"

noida_admin = first_employee("Store HR & Admin Executive", NOIDA)
noida_sic = first_employee("Store In-charge", NOIDA)
noida_fm_diamond = first_employee("Floor Manager - Diamond", NOIDA)
noida_fm_gold = first_employee("Floor Manager - Gold", NOIDA)
kb_accountant = first_employee("Store Accountant", KAROL_BAGH)
payroll_exec = first_employee("Payroll & Compliance Executive")
trainer = first_employee("Training & Development Executive")
hr_exec = first_employee("HR Executive")
hr_head = first_employee("Head - Human Resources")
qc_officer = first_employee("Hallmarking & QC Officer")
it_support = first_employee("IT Support Executive")

# ── Roles for onboarding owners ─────────────────────────────────────────────
log("Onboarding roles")
for role, emp in [("Store Admin", noida_admin), ("Store Manager", noida_sic), ("Payroll User", payroll_exec),
                  ("Trainer", trainer), ("HR User", hr_exec)]:
    add_role_to_user(emp.user_id, role)
commit()

# ── Template ────────────────────────────────────────────────────────────────
log("Employee Onboarding Template")
# (activity, role, user, begin_on, duration, required_for_employee_creation, description)
ACTIVITIES = [
    ("Collect joining documents", "HR User", hr_exec.user_id, 0, 3, 1,
     "Collect and attach the documents in the Employee Documents checklist: Aadhaar, PAN, photographs, address proof, education certificate, relieving letter, bank proof, UAN."),
    ("Background verification", "HR Manager", hr_head.user_id, 0, 5, 1,
     "Verify the last two employers and dates by phone or email. Record the outcome on the BGV document row."),
    ("Police verification", "Store Admin", noida_admin.user_id, 0, 7, 1,
     "File the police verification form at the local police station. Attach the acknowledgement; attach the certificate when received. Joining can proceed on acknowledgement."),
    ("Reference check", "Store Manager", noida_sic.user_id, 1, 3, 1,
     "Speak to one reference from the previous store."),
    ("Bank, PF and ESI details", "Payroll User", payroll_exec.user_id, 2, 3, 0,
     "Collect bank proof, UAN, ESI number if applicable."),
    ("ESSL enrolment and ID card", "Store Admin", noida_admin.user_id, 5, 2, 0,
     "Set the attendance device ID, enrol face and fingerprint on the store machines, issue the ID card."),
    ("Uniform and grooming kit", "Store Admin", noida_admin.user_id, 5, 2, 0,
     "Two sets of store uniform and a name badge."),
    ("Portal login and policy acknowledgement", "HR User", hr_exec.user_id, 8, 1, 0,
     "Create the User, link to the Employee, ask the joiner to read and acknowledge the policies marked 'acknowledge on joining'."),
    ("Induction Day 1: Company, values, policies", "Trainer", trainer.user_id, 8, 1, 0,
     "Training Event 'PPJ Induction - Day 1'."),
    ("Induction Day 2: Product, hallmarking, certification", "Trainer", trainer.user_id, 9, 1, 0,
     "Training Event 'PPJ Induction - Day 2'."),
    ("Induction Day 3: Floor, vault, billing, security drill", "Store Manager", noida_sic.user_id, 10, 1, 0,
     "Training Event 'PPJ Induction - Day 3', at the store."),
    ("30-day check-in", "Store Manager", noida_sic.user_id, 30, 1, 0,
     "First Goal Check In on the joiner's KPIs."),
]
TEMPLATE = "PPJ Store Staff Onboarding"
tpl_name = frappe.db.get_value("Employee Onboarding Template", {"title": TEMPLATE}, "name")
if not tpl_name:
    tpl = frappe.get_doc({"doctype": "Employee Onboarding Template", "title": TEMPLATE, "company": COMPANY,
                          "department": dept("Sales"),
                          "activities": [{"activity_name": a, "role": r, "begin_on": b, "duration": d,
                                          "required_for_employee_creation": req, "description": desc,
                                          "task_weight": 1}
                                         for a, r, u, b, d, req, desc in ACTIVITIES]})
    tpl.insert(ignore_permissions=True)
    tpl_name = tpl.name
    log(f"  [created] template {tpl_name}")
commit()

# ── Employee Onboarding for Ritika ──────────────────────────────────────────
log("Employee Onboarding")
ritika_app = frappe.db.get_value("Job Applicant", {"email_id": "ritika.malhotra@ppjewellers.demo"}, "name")
ritika_offer = frappe.db.get_value("Job Offer", {"job_applicant": ritika_app, "docstatus": 1}, "name")
if not (ritika_app and ritika_offer):
    raise SystemExit("Run seed_recruitment.py first")
onb_name = frappe.db.get_value("Employee Onboarding", {"job_applicant": ritika_app, "docstatus": ["!=", 2]}, "name")
if not onb_name:
    # The onboarding Project starts on boarding_begins_on (build B4 fix in
    # employee_boarding_controller), so pre-joining tasks are fine with the real joining date.
    onb = frappe.get_doc({"doctype": "Employee Onboarding", "job_applicant": ritika_app, "job_offer": ritika_offer,
                          "employee_name": "Ritika Malhotra", "date_of_joining": JOIN,
                          "boarding_begins_on": "2026-08-21", "company": COMPANY, "department": dept("Sales"),
                          "designation": "Senior Sales Executive", "employee_grade": "G3 Senior Executive",
                          "holiday_list": "Noida Store Holiday List - Off Wednesday", "notify_users_by_email": 0,
                          "employee_onboarding_template": tpl_name,
                          "activities": [{"activity_name": a, "role": r, "user": u, "begin_on": b, "duration": d,
                                          "required_for_employee_creation": req, "description": desc, "task_weight": 1}
                                         for a, r, u, b, d, req, desc in ACTIVITIES]})
    onb.flags.ignore_permissions = True
    onb.insert()
    onb.submit()          # creates the Project, one Task per activity, and a ToDo per assignee
    frappe.db.set_value("Project", onb.project, "expected_end_date", "2026-10-05")
    onb_name = onb.name
    log(f"  [created] Employee Onboarding {onb_name} with {len(onb.activities)} tasks")
commit()

# Close every task except the 30-day check-in (due in October), so the Employee can be created
onb = frappe.get_doc("Employee Onboarding", onb_name)
closed = 0
for act in onb.activities:
    if not act.task:
        continue
    if act.activity_name.startswith("30-day"):
        continue
    task = frappe.get_doc("Task", act.task)
    if task.status != "Completed":
        task.status = "Completed"
        task.completed_on = add_days("2026-08-21", int(act.begin_on) + int(act.duration))
        task.completed_by = act.user
        task.flags.ignore_permissions = True
        task.save()
        closed += 1
commit()
onb.reload()
log(f"  {closed} tasks closed, boarding_status = {onb.boarding_status}")

# ── Employee created through the onboarding ─────────────────────────────────
log("Employee PPJ-0401 from onboarding")
from hrms.hr.doctype.employee_onboarding.employee_onboarding import make_employee
if not frappe.db.exists("Employee", "PPJ-0401"):
    emp = make_employee(onb_name)      # refuses unless the four required tasks are complete
    emp.update({
        "employee_number": "PPJ-0401", "first_name": "Ritika", "last_name": "Malhotra", "gender": "Female",
        "date_of_birth": "1995-03-14", "date_of_joining": JOIN, "branch": NOIDA, "department": dept("Sales"),
        "designation": "Senior Sales Executive", "grade": "G3 Senior Executive",
        "reports_to": noida_fm_diamond.name, "employment_type": "Full-time", "status": "Active",
        "holiday_list": "Noida Store Holiday List - Off Wednesday", "default_shift": STORE_SHIFT,
        "attendance_device_id": "0401", "company_email": "ritika.malhotra@ppjewellers.demo",
        "prefered_contact_email": "Company Email", "ctc": 42000 * 12, "salary_currency": "INR",
        "job_applicant": ritika_app,
    })
    emp.flags.ignore_permissions = True
    emp.flags.ignore_mandatory = True
    emp.name = "PPJ-0401"
    frappe.flags.in_import = True
    try:
        emp.insert()
    finally:
        frappe.flags.in_import = False
    if emp.name != "PPJ-0401":
        frappe.rename_doc("Employee", emp.name, "PPJ-0401", force=True)
    log("  [created] Employee PPJ-0401 Ritika Malhotra")
commit()

# Her document checklist (build B4): the hook created one Pending row per type
# that applies to her grade and designation; the joining paperwork is in.
if frappe.db.exists("DocType", "Employee Document") and frappe.db.exists("Employee", "PPJ-0401"):
    from hrms.alvoraa_employee_documents.employee_documents import backfill_checklists, refresh_summary
    backfill_checklists(["PPJ-0401"])     # no-op when the hook already filled it
    rows = frappe.get_all("Employee Document", filters={"parent": "PPJ-0401", "parenttype": "Employee"},
                          fields=["name", "document_type", "status"])
    hr_user = frappe.db.get_value("Employee", hr_exec.name, "user_id") or "Administrator"
    for r in rows:
        if r.document_type == "Police verification certificate":
            values = {"status": "Received", "received_on": "2026-08-28", "received_by": hr_user or "Administrator",
                      "remarks": "Police acknowledgement received; certificate pending"}
        elif r.document_type == "Last 3 months' salary slips":
            values = {"status": "Pending"}
        else:
            values = {"status": "Verified", "received_on": "2026-08-26", "received_by": hr_user or "Administrator",
                      "verified_on": "2026-08-29", "verified_by": hr_user or "Administrator"}
        frappe.db.set_value("Employee Document", r.name, values)
    log(f"  documents: {refresh_summary('PPJ-0401')}")
    commit()

# Two more September joiners so the induction has a batch
log("Other September joiners")
JOINERS = [
    ("PPJ-0402", "Kabir", "Anand", "Male", "1998-11-02", NOIDA, "Sales", "Sales Executive", "G2 Executive",
     noida_fm_gold.name, "Noida Store Holiday List - Off Monday", "0402", 22000),
    ("PPJ-0403", "Nandini", "Bajaj", "Female", "1999-06-21", KAROL_BAGH, "Cashiering & Accounts", "Cashier",
     "G2 Executive", kb_accountant.name, "Delhi Store Holiday List - Off Tuesday", "0403", 20000),
]
for eid, fn, ln, gender, dob, branch, department, desig, grade, rep, hol, dev, ctc in JOINERS:
    if frappe.db.exists("Employee", eid):
        continue
    e = frappe.get_doc({"doctype": "Employee", "employee_number": eid, "first_name": fn, "last_name": ln,
                        "gender": gender, "date_of_birth": dob, "date_of_joining": JOIN, "company": COMPANY,
                        "branch": branch, "department": dept(department), "designation": desig,
                        "grade": grade, "reports_to": rep, "employment_type": "Full-time",
                        "status": "Active", "holiday_list": hol, "default_shift": STORE_SHIFT,
                        "attendance_device_id": dev, "company_email": f"{fn.lower()}.{ln.lower()}@ppjewellers.demo",
                        "prefered_contact_email": "Company Email", "ctc": ctc * 12, "salary_currency": "INR"})
    e.flags.ignore_mandatory = True
    e.name = eid
    frappe.flags.in_import = True
    try:
        e.insert(ignore_permissions=True)
    finally:
        frappe.flags.in_import = False
    if e.name != eid:
        frappe.rename_doc("Employee", e.name, eid, force=True)
    log(f"  [created] Employee {eid} {fn} {ln}")
commit()

# Users, salary, shift, leave policy for the three joiners
log("Users, salary, shift, leave for joiners")
policy = frappe.db.get_value("Leave Policy", {"title": "PPJ Standard Leave Policy"}, "name")
period = frappe.db.get_value("Leave Period", {"company": COMPANY, "from_date": FY_START}, "name")
slab = frappe.db.get_value("Income Tax Slab", {"company": COMPANY, "docstatus": 1}, "name")
STRUCT = {"G2 Executive": "PPJ-G2", "G3 Senior Executive": "PPJ-G3"}
for eid, base in [("PPJ-0401", 42000), ("PPJ-0402", 22000), ("PPJ-0403", 20000)]:
    e = frappe.get_doc("Employee", eid)
    assign_holiday_list(eid, e.holiday_list, JOIN)
    email = e.company_email
    make_user(email, e.first_name, e.last_name, [])
    if e.user_id != email:
        frappe.db.set_value("Employee", eid, {"user_id": email, "create_user_permission": 1}, update_modified=False)
    if not frappe.db.exists("User Permission", {"user": email, "allow": "Employee", "for_value": eid}):
        frappe.get_doc({"doctype": "User Permission", "user": email, "allow": "Employee", "for_value": eid,
                        "apply_to_all_doctypes": 1}).insert(ignore_permissions=True)
    approver = frappe.db.get_value("Employee", e.reports_to, "user_id")
    frappe.db.set_value("Employee", eid, {"leave_approver": approver, "expense_approver": approver}, update_modified=False)
    if frappe.db.exists("Salary Structure", STRUCT[e.grade]) and \
            not frappe.db.exists("Salary Structure Assignment", {"employee": eid, "docstatus": 1}):
        ssa = frappe.get_doc({"doctype": "Salary Structure Assignment", "employee": eid,
                              "salary_structure": STRUCT[e.grade], "company": COMPANY, "currency": "INR",
                              "from_date": JOIN, "base": base, "income_tax_slab": slab})
        ssa.flags.ignore_permissions = True
        ssa.insert()
        ssa.submit()
    if not frappe.db.exists("Shift Assignment", {"employee": eid, "docstatus": 1}):
        sa = frappe.get_doc({"doctype": "Shift Assignment", "employee": eid, "shift_type": STORE_SHIFT,
                             "company": COMPANY, "start_date": JOIN, "status": "Active"})
        sa.flags.ignore_permissions = True
        sa.insert()
        sa.submit()
    if policy and not frappe.db.exists("Leave Policy Assignment", {"employee": eid, "docstatus": 1}):
        from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import create_assignment_for_multiple_employees
        create_assignment_for_multiple_employees([eid], {"leave_policy": policy, "assignment_based_on": "Joining Date",
                                                         "leave_period": period, "effective_from": JOIN,
                                                         "effective_to": FY_END, "carry_forward": 0})
commit()

# ── Induction: Training Program and three events ────────────────────────────
log("Training Program and Events")
PROGRAM = "PPJ Store Induction"
ensure("Training Program", PROGRAM, {"training_program": PROGRAM, "status": "Scheduled", "company": COMPANY,
                                     "trainer_name": trainer.employee_name, "trainer_email": trainer.user_id,
                                     "description": "Three-day induction for every store joiner: company and values, product and certification, floor and vault procedures."})
EVENTS = [
    ("PPJ Induction - Day 1: Company, values, policies", "Seminar", "2026-09-01", trainer, "PPJ Head Office Chandigarh (video link to store)",
     "History of PP Jewellers, the five core values, leave and attendance policy, incentive policy, POSH, code of conduct, grievance channel."),
    ("PPJ Induction - Day 2: Product, hallmarking, certification", "Workshop", "2026-09-02", qc_officer, "PPJ Head Office Chandigarh (video link to store)",
     "Gold purity and BIS hallmarking, diamond 4Cs, IGI and GIA certificates, platinum, gemstones, exchange and buy-back."),
    ("PPJ Induction - Day 3: Floor, vault, billing, security", "Workshop", "2026-09-03", noida_sic, "PPJ Noida Sector 18",
     "Opening and closing checklist, vault issue and return, billing and KYC rules for high-value sales, CCTV and security drill, grooming."),
]
joiners = ["PPJ-0401", "PPJ-0402", "PPJ-0403"]
for name, etype, date, host, location, intro in EVENTS:
    if frappe.db.exists("Training Event", name):
        continue
    ev = frappe.get_doc({"doctype": "Training Event", "event_name": name, "training_program": PROGRAM,
                         "event_status": "Completed", "type": etype, "level": "Beginner", "company": COMPANY,
                         "trainer_name": host.employee_name, "trainer_email": host.user_id, "course": "Induction",
                         "location": location, "start_time": f"{date} 10:00:00", "end_time": f"{date} 17:00:00",
                         "introduction": intro, "has_certificate": 0,
                         "employees": [{"employee": j, "status": "Completed", "attendance": "Present", "is_mandatory": 1}
                                       for j in joiners]})
    ev.flags.ignore_permissions = True
    ev.insert()
    ev.submit()
    log(f"  [created] Training Event: {name}")
commit()

day2 = EVENTS[1][0]
if not frappe.db.exists("Training Result", {"training_event": day2, "docstatus": 1}):
    tr = frappe.get_doc({"doctype": "Training Result", "training_event": day2,
                         "employees": [{"employee": "PPJ-0401", "hours": 7, "grade": "88%", "comments": "Strong on certification; knows IGI vs GIA."},
                                       {"employee": "PPJ-0402", "hours": 7, "grade": "74%", "comments": "Needs a second session on hallmark reading."},
                                       {"employee": "PPJ-0403", "hours": 7, "grade": "81%", "comments": "Good on KYC thresholds."}]})
    tr.flags.ignore_permissions = True
    tr.insert()
    tr.submit()
    log("  [created] Training Result for Day 2")
for name, _t, _d, host, _l, _i in EVENTS:
    if not frappe.db.exists("Training Feedback", {"training_event": name, "employee": "PPJ-0401", "docstatus": 1}):
        tf = frappe.get_doc({"doctype": "Training Feedback", "employee": "PPJ-0401", "training_event": name,
                             "feedback": "Clear and practical. The vault walk-through and the certificate reading exercise were the most useful parts."})
        tf.flags.ignore_permissions = True
        tf.insert()
        tf.submit()
commit()

# Skill map from the interview ratings
if not frappe.db.exists("Employee Skill Map", "PPJ-0401"):
    frappe.get_doc({"doctype": "Employee Skill Map", "employee": "PPJ-0401",
                    "employee_skills": [{"skill": s, "proficiency": r / 5.0, "evaluation_date": "2026-08-12"} for s, r in [
                        ("Communication & Grooming", 4.5), ("Diamond & Certification Knowledge", 4.5),
                        ("Selling & Closing", 4.5), ("Customer Handling", 4.5), ("Team Coaching", 4.0)]]
                    }).insert(ignore_permissions=True)
commit()

log("Block 6 done")
counts("Employee Onboarding", "Task", "ToDo", "Training Event", "Training Result", "Training Feedback")
log(f"  Employees now: {frappe.db.count('Employee', {'status': 'Active'})}")
