"""
PP Jewellers demo - Block 2: 400 employees, users, roles, leave policy.

Reads data/employees.csv. Two passes (reports_to needs the manager to exist),
then rebuilds the Employee tree, creates a User per employee with the demo
password, gives roles by designation, adds Branch user permissions for store
managers, assigns the leave policy to everyone, and seeds PPJ-0058's Casual
Leave in May so the loss-of-pay story in file 03 holds.

Idempotent: safe to re-run.
"""
import os
import sys

sys.path.insert(0, os.environ.get("PPJ_SCRIPT_DIR", "/tmp/ppj"))
from ppj_common import *  # noqa: F401,F403
from frappe.utils.nestedset import rebuild_tree

connect()

rows = read_csv("employees.csv")
log(f"Employees: {len(rows)} rows in CSV")

for g in ("Male", "Female", "Other"):
    ensure("Gender", g, {"gender": g}, quiet=True)
ensure("Employment Type", "Full-time", {"employee_type_name": "Full-time"}, quiet=True)

# ── Pass 1: employees without reports_to ────────────────────────────────────
created = 0
for r in rows:
    if frappe.db.exists("Employee", r["employee_id"]):
        continue
    emp = frappe.get_doc({
        "doctype": "Employee",
        "employee_number": r["employee_id"],
        "first_name": r["first_name"], "last_name": r["last_name"],
        "gender": r["gender"], "date_of_birth": r["date_of_birth"],
        "date_of_joining": r["date_of_joining"], "company": COMPANY,
        "branch": r["branch"], "department": dept(r["department"]),
        "designation": r["designation"], "grade": r["employee_grade"],
        "employment_type": r["employment_type"], "status": "Active",
        "holiday_list": r["holiday_list"], "default_shift": r["default_shift"],
        "attendance_device_id": r["attendance_device_id"],
        "company_email": r["user_id"], "prefered_contact_email": "Company Email",
        "ctc": flt(r["monthly_ctc"]) * 12, "salary_currency": "INR",
    })
    if emp.meta.has_field("provident_fund_account"):
        emp.provident_fund_account = r["pf_uan"]
    if emp.meta.has_field("esi_number") and r["esi_number"]:     # build B2
        emp.esi_number = r["esi_number"]
    emp.flags.ignore_mandatory = True
    # ERPNext's Employee autoname always uses the naming series (the HR Settings
    # "Employee Number" option is not wired to it in this fork). Import mode keeps a
    # preset name, which is exactly what Data Import relies on.
    emp.name = r["employee_id"]
    frappe.flags.in_import = True
    try:
        emp.insert(ignore_permissions=True)
    finally:
        frappe.flags.in_import = False
    if emp.name != r["employee_id"]:
        frappe.rename_doc("Employee", emp.name, r["employee_id"], force=True)
    created += 1
    if created % 50 == 0:
        commit()
        log(f"  {created} created")
commit()
log(f"  pass 1: {created} new employees")

# ── Pass 2: reports_to ──────────────────────────────────────────────────────
updated = 0
for r in rows:
    if r["reports_to"] and frappe.db.get_value("Employee", r["employee_id"], "reports_to") != r["reports_to"]:
        frappe.db.set_value("Employee", r["employee_id"], "reports_to", r["reports_to"], update_modified=False)
        updated += 1
commit()
rebuild_tree("Employee")
commit()
log(f"  pass 2: {updated} reports_to set, tree rebuilt")

# ── Users and roles ─────────────────────────────────────────────────────────
STORE_MANAGER_DESIG = {"Store In-charge", "Assistant Store Manager", "Floor Manager - Gold",
                       "Floor Manager - Diamond", "Floor Manager - Silver & Fashion"}
ROLES_BY_DESIG = {
    "Owner & Managing Director": ["HR Manager", "HR User", "Leave Approver", "Expense Approver", "Interviewer"],
    "Head - Human Resources": ["HR Manager", "HR User", "Leave Approver", "Expense Approver", "Interviewer"],
    "HR Executive": ["HR User", "Interviewer"],
    "Recruitment Executive": ["HR User", "Interviewer"],
    "Payroll & Compliance Executive": ["HR User", "Payroll Manager", "Payroll User"],
    "Training & Development Executive": ["HR User"],
    "Store HR & Admin Executive": ["HR User", "Leave Approver"],
    "Store In-charge": ["Leave Approver", "Expense Approver", "Interviewer"],
    "Assistant Store Manager": ["Leave Approver", "Expense Approver", "Interviewer"],
    "Floor Manager - Gold": ["Leave Approver", "Interviewer"],
    "Floor Manager - Diamond": ["Leave Approver", "Interviewer"],
    "Floor Manager - Silver & Fashion": ["Leave Approver", "Interviewer"],
    "Store Accountant": ["Leave Approver"],
}
HEAD_PREFIX_ROLES = ["Leave Approver", "Expense Approver", "Interviewer"]   # "Head - ..." and managers at HO

for role in {r for rs in ROLES_BY_DESIG.values() for r in rs} | set(HEAD_PREFIX_ROLES):
    ensure("Role", role, {"role_name": role}, quiet=True)

emps = emp_map()
made_users = 0
frappe.flags.in_import = True      # User creation is throttled to 60 per hour outside import mode
for r in rows:
    email = r["user_id"].strip().lower()
    desig = r["designation"]
    roles = list(ROLES_BY_DESIG.get(desig, []))
    if desig.startswith("Head - ") or desig in ("IT Manager", "Admin Manager", "Central Vault & Inventory Manager", "Legal & Compliance Officer"):
        roles = sorted(set(roles) | set(HEAD_PREFIX_ROLES))
    roles = ["Employee"] + [x for x in roles if x != "Employee"]
    if not frappe.db.exists("User", email):
        user = frappe.get_doc({
            "doctype": "User", "email": email, "first_name": r["first_name"], "last_name": r["last_name"],
            "send_welcome_email": 0, "user_type": "System User", "new_password": DEMO_PASSWORD,
            "roles": [{"role": x} for x in roles],
        })
        user.flags.no_welcome_mail = True
        user.insert(ignore_permissions=True)
        made_users += 1
    else:
        user = frappe.get_doc("User", email)
        have = {x.role for x in user.roles}
        missing = [x for x in roles if x not in have]
        if missing:
            for x in missing:
                user.append("roles", {"role": x})
            user.save(ignore_permissions=True)
    e = emps[r["employee_id"]]
    if e.user_id != email:
        # create_user_permission=1 restricts the user to their own Employee record; managers
        # must see their team, so they get a Branch permission instead.
        frappe.db.set_value("Employee", e.name, {
            "user_id": email,
            "create_user_permission": 0 if (desig in STORE_MANAGER_DESIG or roles != ["Employee"]) else 1,
        }, update_modified=False)
    if made_users and made_users % 50 == 0:
        commit()
commit()
frappe.flags.in_import = False
log(f"  users: {made_users} created, all {len(rows)} linked")

# Employee user permission (own record) for plain employees; Branch permission for store managers
log("User Permissions")
perm_count = 0
for r in rows:
    email = r["user_id"].strip().lower()
    desig = r["designation"]
    if desig in STORE_MANAGER_DESIG:
        if not frappe.db.exists("User Permission", {"user": email, "allow": "Branch", "for_value": r["branch"]}):
            frappe.get_doc({"doctype": "User Permission", "user": email, "allow": "Branch",
                            "for_value": r["branch"], "apply_to_all_doctypes": 1}).insert(ignore_permissions=True)
            perm_count += 1
    elif ROLES_BY_DESIG.get(desig) is None and not desig.startswith("Head - "):
        if not frappe.db.exists("User Permission", {"user": email, "allow": "Employee", "for_value": r["employee_id"]}):
            frappe.get_doc({"doctype": "User Permission", "user": email, "allow": "Employee",
                            "for_value": r["employee_id"], "apply_to_all_doctypes": 1}).insert(ignore_permissions=True)
            perm_count += 1
commit()
log(f"  {perm_count} user permissions created")

# Leave approver = reports_to's user
log("Leave and expense approvers")
for r in rows:
    if r["reports_to"]:
        approver = emps[r["reports_to"]].user_id or frappe.db.get_value("Employee", r["reports_to"], "user_id")
        if approver:
            frappe.db.set_value("Employee", r["employee_id"],
                                {"leave_approver": approver, "expense_approver": approver}, update_modified=False)
commit()

# ── Holiday List Assignments (company fallback + one per employee) ─────────
log("Holiday List Assignments")
assign_holiday_list(COMPANY, "Head Office Holiday List", FY_START, applicable_for="Company")
n = 0
for r in rows:
    assign_holiday_list(r["employee_id"], r["holiday_list"], FY_START)
    n += 1
    if n % 100 == 0:
        commit()
commit()
log(f"  assignments: {frappe.db.count('Holiday List Assignment', {'docstatus': 1})}")

# ── Leave policy assignment (creates allocations) ───────────────────────────
log("Leave Policy Assignments")
from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import create_assignment_for_multiple_employees
policy = frappe.db.get_value("Leave Policy", {"title": "PPJ Standard Leave Policy"}, "name")
period = frappe.db.get_value("Leave Period", {"company": COMPANY, "from_date": FY_START}, "name")
todo = [r["employee_id"] for r in rows
        if not frappe.db.exists("Leave Policy Assignment", {"employee": r["employee_id"], "leave_policy": policy,
                                                            "effective_from": FY_START, "docstatus": 1})]
if todo:
    frappe.flags.ignore_permissions = True
    for i in range(0, len(todo), 50):
        create_assignment_for_multiple_employees(todo[i:i + 50], {
            "leave_policy": policy, "assignment_based_on": "Leave Period", "leave_period": period,
            "effective_from": FY_START, "effective_to": FY_END, "carry_forward": 0,
        })
        commit()
        log(f"  assigned {min(i + 50, len(todo))}/{len(todo)}")
log(f"  Leave Allocations: {frappe.db.count('Leave Allocation', {'docstatus': 1})}")

# ── PPJ-0058: 5 days Casual Leave before July (story in file 03) ────────────
log("PPJ-0058 Casual Leave in May/June")
approver = frappe.db.get_value("Employee", "PPJ-0058", "leave_approver")
for frm, to, reason in [("2026-05-11", "2026-05-12", "Sister's wedding - travel"),
                        ("2026-05-15", "2026-05-16", "Sister's wedding"),
                        ("2026-06-01", "2026-06-01", "Family function")]:
    if not frappe.db.exists("Leave Application", {"employee": "PPJ-0058", "from_date": frm, "docstatus": 1}):
        la = frappe.get_doc({"doctype": "Leave Application", "employee": "PPJ-0058", "leave_type": "Casual Leave",
                             "from_date": frm, "to_date": to, "description": reason, "leave_approver": approver,
                             "status": "Approved", "posting_date": frm, "company": COMPANY})
        la.flags.ignore_permissions = True
        la.insert()
        la.submit()
        log(f"  [created] Leave Application {la.name}: {la.total_leave_days} day(s)")
commit()

log("Block 2 done")
counts("Employee", "User", "User Permission", "Leave Policy Assignment", "Leave Allocation", "Leave Application")


# ── Employee documents (build B4) ───────────────────────────────────────────
# Every new Employee gets a Pending checklist from the hook. Existing staff
# joined years ago, so their papers are on record: mark them Verified as of the
# joining date. PPJ-0200 keeps an expired police verification certificate for the
# Document Compliance view.
if frappe.db.exists("DocType", "Employee Document"):
    log("Employee documents: existing staff verified (build B4)")
    from hrms.alvoraa_employee_documents.employee_documents import backfill_checklists, refresh_summary
    filled = backfill_checklists()        # employees created before the feature was switched on
    log(f"  checklists backfilled for {filled} employees")
    ED = frappe.qb.DocType("Employee Document")
    pending = frappe.get_all("Employee Document", filters={"parenttype": "Employee", "status": "Pending"},
                             fields=["name", "parent"])
    joined = {e.name: e.date_of_joining for e in frappe.get_all("Employee", filters={"company": COMPANY},
                                                                 fields=["name", "date_of_joining"])}
    by_parent = {}
    for r in pending:
        by_parent.setdefault(r.parent, []).append(r.name)
    for parent, names in by_parent.items():
        on = joined.get(parent) or "2026-01-01"
        (frappe.qb.update(ED).set(ED.status, "Verified").set(ED.received_on, on).set(ED.verified_on, on)
         .set(ED.received_by, "Administrator").set(ED.verified_by, "Administrator")
         .where(ED.name.isin(names))).run()
    cert = frappe.db.get_value("Employee Document", {"parent": "PPJ-0200", "parenttype": "Employee",
                                                     "document_type": "Police verification certificate"}, "name")
    if cert:
        frappe.db.set_value("Employee Document", cert, {"status": "Expired", "issue_date": "2020-04-01",
                                                        "expiry_date": "2023-03-31",
                                                        "remarks": "Renewal not yet applied for"})
    for parent in by_parent:
        refresh_summary(parent)
    commit()
    log(f"  {len(pending)} rows verified for {len(by_parent)} employees; PPJ-0200 police certificate expired")
