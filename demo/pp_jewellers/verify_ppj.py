"""
PP Jewellers demo - print the verification numbers from file 11 of the spec.
Run:  env/bin/python /tmp/ppj/verify_ppj.py --site <site>
"""
import os
import sys

sys.path.insert(0, os.environ.get("PPJ_SCRIPT_DIR", "/tmp/ppj"))
from ppj_common import *  # noqa: F401,F403

connect()


def c(dt, f=None):
    return frappe.db.count(dt, f or {})


log("Block 1-2 masters and employees")
for dt in ("Branch", "Department", "Designation", "Holiday List", "Leave Type", "Shift Type"):
    log(f"  {dt}: {c(dt)}")
log(f"  Employees active: {c('Employee', {'status': 'Active'})}; per branch: " +
    ", ".join(f"{b}={c('Employee', {'branch': b, 'status': 'Active'})}" for b in STORES + [HEAD_OFFICE]))
log(f"  Employees without reports_to: {c('Employee', {'reports_to': ['in', ['', None]], 'status': 'Active'})} (expect 1)")
linked = frappe.db.sql("select count(*) from tabEmployee where ifnull(user_id,'') != ''")[0][0]
log(f"  Users linked: {linked}")
log(f"  Leave Allocations: {c('Leave Allocation', {'docstatus': 1})}")

log("Block 3 attendance")
log(f"  Employee Checkin: {c('Employee Checkin')}  Attendance: {c('Attendance', {'docstatus': 1})}")
for s in ("Present", "Absent", "Half Day"):
    log(f"    {s}: {c('Attendance', {'status': s, 'docstatus': 1})}")
for emp, d in [("PPJ-0054", "2026-08-18"), ("PPJ-0054", "2026-08-22"), ("PPJ-0058", "2026-08-03")]:
    log(f"  {emp} {d}: {frappe.db.get_value('Attendance', {'employee': emp, 'attendance_date': d}, ['status', 'in_time', 'out_time', 'late_entry', 'early_exit'])}")
if frappe.db.exists("DocType", "Attendance Deduction"):
    log(f"  Attendance Deductions (build B1): {c('Attendance Deduction', {'docstatus': 1})} (expect 212 = data/expected_deductions.csv), "
        f"with loss of pay {c('Attendance Deduction', {'docstatus': 1, 'lwp_days': ['>', 0]})}")
    for emp, week in (("PPJ-0054", "2026-08-17"), ("PPJ-0058", "2026-08-03")):
        log(f"    {emp} week {week}: {frappe.db.get_value('Attendance Deduction', {'employee': emp, 'week_start': week, 'docstatus': 1}, ['deduction_days', 'lwp_days', 'lwp_amount', 'additional_salary'])}")

log("Block 4 payroll")
log(f"  Salary Structure Assignments: {c('Salary Structure Assignment', {'docstatus': 1})}  Slips: {c('Salary Slip', {'docstatus': 1})}  Incentives: {c('Employee Incentive', {'docstatus': 1})}")
for emp in ("PPJ-0054", "PPJ-0058"):
    s = frappe.db.get_value("Salary Slip", {"employee": emp, "start_date": "2026-08-01", "docstatus": 1}, ["name", "payment_days", "gross_pay", "net_pay"], as_dict=True)
    log(f"  {emp} Aug slip: {s}")
    if s:
        rows = frappe.get_all("Salary Detail", filters={"parent": s.name, "amount": [">", 0]}, fields=["salary_component", "amount"])
        log("    " + ", ".join(f"{r.salary_component}={r.amount}" for r in rows))

if frappe.get_meta("Employee").has_field("employee_documents"):
    log("Build B4 employee documents")
    log(f"  Document types {c('Employee Document Type')}, rows {c('Employee Document', {'parenttype': 'Employee'})}, "
        f"expired {c('Employee Document', {'parenttype': 'Employee', 'status': 'Expired'})}")
    log(f"  PPJ-0200: {frappe.db.get_value('Employee', 'PPJ-0200', 'documents_summary')}; PPJ-0401: {frappe.db.get_value('Employee', 'PPJ-0401', 'documents_summary')}")

log("Block 5 recruitment")
log(f"  Requisitions {c('Job Requisition')}, Openings {c('Job Opening')}, Applicants {c('Job Applicant')}, Interviews {c('Interview')}, Feedback {c('Interview Feedback', {'docstatus': 1})}, Offers {c('Job Offer', {'docstatus': 1})}, Appointment Letters {c('Appointment Letter')}")
for n in frappe.get_all("Interview", filters={"job_applicant": frappe.db.get_value("Job Applicant", {"email_id": "ritika.malhotra@ppjewellers.demo"}, "name")}, fields=["interview_type", "status", "average_rating"]):
    log(f"    Ritika {n.interview_type}: {n.status} avg {round((n.average_rating or 0) * 5, 2)}")

if frappe.get_meta("Job Applicant").has_field("screening_result"):
    log(f"  Screening (build B3): passed {c('Job Applicant', {'screening_result': 'Passed'})}, screened out {c('Job Applicant', {'screening_result': 'Screened Out'})}; "
        f"web form ppj-senior-sales-application: {bool(frappe.db.exists('Web Form', 'ppj-senior-sales-application'))}")

log("Block 6 onboarding")
onb = frappe.db.get_value("Employee Onboarding", {"employee_name": "Ritika Malhotra"}, ["name", "boarding_status", "employee"], as_dict=True)
log(f"  Onboarding: {onb}; tasks completed {c('Task', {'status': 'Completed'})}, open {c('Task', {'status': ['in', ['Open', 'Working']]})}")
log(f"  Training Events {c('Training Event', {'docstatus': 1})}, Results {c('Training Result', {'docstatus': 1})}, Feedback {c('Training Feedback', {'docstatus': 1})}")

if frappe.db.exists("DocType", "Policy Document"):
    log("Block 7 policies (build B5)")
    log(f"  Policies published {c('Policy Document', {'status': 'Published'})}, with unpublished changes {c('Policy Document', {'has_unpublished_changes': 1})}, "
        f"acknowledgements {c('Policy Acknowledgement')}, department heads {c('Department', {'department_head': ['is', 'set']})}")
    for emp in ("PPJ-0054", "PPJ-0041", "PPJ-0001", "PPJ-0401"):
        user = frappe.db.get_value("Employee", emp, "user_id")
        frappe.local.policy_profiles = {}
        seen = len(frappe.get_list("Policy Document", filters={"status": "Published"}, pluck="name", user=user, limit=0))
        log(f"    {emp} sees {seen} policies")

log("Block 8 performance")
for cycle in ("Q1 FY27 Performance Cycle", "Q2 FY27 Performance Cycle"):
    log(f"  {cycle}: status {frappe.db.get_value('Appraisal Cycle', cycle, 'status')}, appraisals submitted {c('Appraisal', {'appraisal_cycle': cycle, 'docstatus': 1})}, draft {c('Appraisal', {'appraisal_cycle': cycle, 'docstatus': 0})}, KPIs {c('KPI', {'appraisal_cycle': cycle})}, rated KPIs {c('KPI', {'appraisal_cycle': cycle, 'manager_rating': ['>', 0]})}")
for cname in ("Q1 FY27 Company Sales", "Q2 FY27 Company Sales"):
    log(f"  {cname}: {frappe.db.get_value('Goal Cascade', {'cascade_name': cname}, ['company_target', 'aggregate_progress_pct', 'status'])}; alignment {frappe.db.get_value('Cascade Alignment Report', {'goal_cascade': frappe.db.get_value('Goal Cascade', {'cascade_name': cname}, 'name')}, ['variance_pct', 'status'])}")
ap = frappe.db.get_value("Appraisal", {"employee": "PPJ-0054", "appraisal_cycle": "Q1 FY27 Performance Cycle", "docstatus": 1}, ["total_score", "avg_feedback_score", "self_score", "final_score"], as_dict=True)
log(f"  PPJ-0054 Q1: {ap}")
if frappe.get_meta("Appraisal").has_field("attendance_score"):
    for emp in ("PPJ-0054", "PPJ-0058", "PPJ-0001"):
        log(f"  {emp} Q2 attendance (build B6): {frappe.db.get_value('Appraisal', {'employee': emp, 'appraisal_cycle': 'Q2 FY27 Performance Cycle', 'docstatus': 0}, ['attendance_score', 'attendance_reliability_pct', 'attendance_punctuality_pct', 'attendance_deduction_days', 'final_score'])}")
    log(f"  Q1 formula: {frappe.db.get_value('Appraisal Cycle', 'Q1 FY27 Performance Cycle', 'final_score_formula')}")
cats = frappe.db.sql("select potential_category, count(*) from `tabAlvoraa Appraisal Extension` where appraisal_cycle=%s group by potential_category", "Q1 FY27 Performance Cycle")
log(f"  Potential categories Q1: {cats}")
log(f"  Upward Feedback: {c('Upward Feedback')}")
