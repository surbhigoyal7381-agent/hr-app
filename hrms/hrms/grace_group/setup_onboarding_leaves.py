"""
Grace Group FMCG Distribution - Frappe HR Demo Setup
Phases 8-9: Employee Onboarding & Leave Management

Depends on setup_grace_group.setup_all() having been run first.
Run: bench execute hrms.grace_group.setup_onboarding_leaves.setup_all
"""

import frappe
from frappe.utils import today, getdate


COMPANY = "Grace Group"
COMPANY_ABBR = "GG"
LEAVE_PERIOD = "2026 Operations Year"


def _exists(doctype, name):
    return bool(frappe.db.exists(doctype, name))


def _dept(name):
    return f"{name} - {COMPANY_ABBR}"


def _get_employee(first_name, last_name):
    return frappe.db.get_value(
        "Employee",
        {"first_name": first_name, "last_name": last_name, "company": COMPANY},
        "name",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Phase 8a: Standard Onboarding Tasks
# ─────────────────────────────────────────────────────────────────────────────

_ONBOARDING_TASKS = [
    {
        "title": "Verify Commercial Driving License & Background Check",
        "department": "HR",
        "description": "Collect and verify CDL, police verification, and address proof for new hire.",
    },
    {
        "title": "Allocate Vehicle in Fleet Management",
        "department": "Logistics",
        "description": "Assign vehicle from fleet pool, log in Vehicle Log, and brief on maintenance SOP.",
    },
    {
        "title": "Q-Comm SLA & Cold Storage Safety Briefing",
        "department": "Supply Chain",
        "description": "Conduct mandatory briefing on Q-Commerce delivery SLAs and cold chain handling protocols.",
    },
    {
        "title": "Create Corporate Email & Frappe ERP Access",
        "department": "IT",
        "description": "Provision G-Suite email, configure Frappe HR mobile app access, and set role permissions.",
    },
    {
        "title": "FMCG Brand Training (Amul / Lays / McCain)",
        "department": "Sales",
        "description": "Complete brand knowledge training covering product range, pricing, and key account protocols.",
    },
]


def setup_onboarding_tasks():
    task_names = {}
    for t in _ONBOARDING_TASKS:
        existing = frappe.db.get_value("Task", {"subject": t["title"]}, "name")
        if existing:
            task_names[t["title"]] = existing
            continue
        doc = frappe.get_doc({
            "doctype": "Task",
            "subject": t["title"],
            "description": t["description"],
            "department": _dept(t["department"]),
            "status": "Open",
            "priority": "Medium",
            "company": COMPANY,
        })
        doc.insert(ignore_permissions=True)
        task_names[t["title"]] = doc.name
        print(f"  [+] Task: {t['title']}")
    return task_names


# ─────────────────────────────────────────────────────────────────────────────
# Phase 8b: Employee Onboarding Templates
# ─────────────────────────────────────────────────────────────────────────────

def setup_onboarding_templates(task_names):
    templates = [
        {
            "template_name": "Delivery Executive Onboarding",
            "designation": "Delivery Executive",
            "tasks": [
                "Verify Commercial Driving License & Background Check",
                "Allocate Vehicle in Fleet Management",
                "Q-Comm SLA & Cold Storage Safety Briefing",
            ],
        },
        {
            "template_name": "Key Account Manager (KAM) Onboarding",
            "designation": "KAM - Dairy",
            "tasks": [
                "Create Corporate Email & Frappe ERP Access",
                "FMCG Brand Training (Amul / Lays / McCain)",
            ],
        },
    ]

    for tmpl in templates:
        name = tmpl["template_name"]
        existing = frappe.db.get_value("Employee Onboarding Template", {"title": name}, "name")
        if existing:
            print(f"  [=] Template already exists: {name}")
            continue

        activities = []
        for task_title in tmpl["tasks"]:
            task_id = task_names.get(task_title)
            if task_id:
                task_meta = next((t for t in _ONBOARDING_TASKS if t["title"] == task_title), None)
                dept = _dept(task_meta["department"]) if task_meta else None
                activities.append({
                    "doctype": "Employee Onboarding Activity",
                    "activity_name": task_title,
                    "department": dept,
                    "task": task_id,
                    "required_for_employee_creation": 0,
                })

        frappe.get_doc({
            "doctype": "Employee Onboarding Template",
            "title": name,
            "designation": tmpl["designation"],
            "department": _dept("HR"),
            "company": COMPANY,
            "activities": activities,
        }).insert(ignore_permissions=True)
        print(f"  [+] Onboarding Template: {name}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 9a: Leave Period & Leave Types
# ─────────────────────────────────────────────────────────────────────────────

def setup_leave_period():
    existing = frappe.db.exists(
        "Leave Period", {"company": COMPANY, "from_date": "2026-01-01", "to_date": "2026-12-31"}
    )
    if not existing:
        frappe.get_doc({
            "doctype": "Leave Period",
            "leave_period_name": LEAVE_PERIOD,
            "company": COMPANY,
            "from_date": "2026-01-01",
            "to_date": "2026-12-31",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        print(f"  [+] Leave Period: {LEAVE_PERIOD}")
    else:
        print(f"  [=] Leave Period already exists: {existing}")


def setup_leave_types():
    leave_types = [
        {
            "leave_type_name": "Casual Leave",
            "is_carry_forward": 0,
            "is_earned_leave": 0,
            "allow_negative": 0,
        },
        {
            "leave_type_name": "Sick Leave",
            "is_carry_forward": 0,
            "is_earned_leave": 0,
            "allow_negative": 0,
        },
        {
            "leave_type_name": "Privilege Leave",
            "is_carry_forward": 1,
            "is_earned_leave": 1,
            "earned_leave_frequency": "Monthly",
            "allow_negative": 0,
        },
        {
            "leave_type_name": "Compensatory Off",
            "is_carry_forward": 0,
            "is_compensatory": 1,
            "is_earned_leave": 0,
            "allow_negative": 0,
        },
    ]
    for lt in leave_types:
        name = lt["leave_type_name"]
        if not _exists("Leave Type", name):
            frappe.get_doc({"doctype": "Leave Type", **lt}).insert(ignore_permissions=True)
            print(f"  [+] Leave Type: {name}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 9b: Leave Policies
# ─────────────────────────────────────────────────────────────────────────────

def setup_leave_policies():
    policies = [
        {
            "leave_policy_name": "Field & Logistics Leave Policy",
            "leave_policy_details": [
                {"leave_type": "Casual Leave", "annual_allocation": 10},
                {"leave_type": "Sick Leave", "annual_allocation": 10},
                {"leave_type": "Privilege Leave", "annual_allocation": 12},
                {"leave_type": "Compensatory Off", "annual_allocation": 0},
            ],
        },
        {
            "leave_policy_name": "Corporate & KAM Leave Policy",
            "leave_policy_details": [
                {"leave_type": "Casual Leave", "annual_allocation": 12},
                {"leave_type": "Sick Leave", "annual_allocation": 12},
                {"leave_type": "Privilege Leave", "annual_allocation": 15},
            ],
        },
    ]
    for policy in policies:
        name = policy["leave_policy_name"]
        existing = frappe.db.get_value("Leave Policy", {"title": name}, "name")
        if not existing:
            doc = frappe.get_doc({
                "doctype": "Leave Policy",
                "title": name,
                "leave_policy_details": [
                    {"doctype": "Leave Policy Detail", **row}
                    for row in policy["leave_policy_details"]
                ],
            })
            doc.insert(ignore_permissions=True)
            print(f"  [+] Leave Policy: {name}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 9c: Leave Policy Assignments
# ─────────────────────────────────────────────────────────────────────────────

def setup_leave_policy_assignments():
    # Resolve IDs from titles/filters
    field_policy_id = frappe.db.get_value("Leave Policy", {"title": "Field & Logistics Leave Policy"}, "name")
    corp_policy_id = frappe.db.get_value("Leave Policy", {"title": "Corporate & KAM Leave Policy"}, "name")
    leave_period_id = frappe.db.get_value(
        "Leave Period", {"company": COMPANY, "from_date": "2026-01-01"}, "name"
    ) or LEAVE_PERIOD

    assignments = [
        # Field policy → Drivers & Warehouse staff
        {"first": "Harpreet", "last": "Babbar",   "policy": field_policy_id},
        {"first": "Rajinder", "last": "Kumar",     "policy": field_policy_id},
        {"first": "Vikramjeet", "last": "Singh",   "policy": field_policy_id},
        {"first": "Amit",     "last": "Patel",     "policy": field_policy_id},
        # Corporate policy → KAMs & C-Suite
        {"first": "Arjun",    "last": "Sandhu",    "policy": corp_policy_id},
        {"first": "Neha",     "last": "Sharma",    "policy": corp_policy_id},
        {"first": "D.K.",     "last": "Malhotra",  "policy": corp_policy_id},
        {"first": "Mukesh",   "last": "Mittal",    "policy": corp_policy_id},
        {"first": "Chaitanya","last": "Malhotra",  "policy": corp_policy_id},
    ]

    for a in assignments:
        if not a["policy"]:
            print(f"  [!] Leave Policy not found — skipping {a['first']} {a['last']}")
            continue
        emp_id = _get_employee(a["first"], a["last"])
        if not emp_id:
            print(f"  [!] Employee not found: {a['first']} {a['last']} — skipping assignment")
            continue

        existing = frappe.db.exists(
            "Leave Policy Assignment",
            {"employee": emp_id, "leave_policy": a["policy"]},
        )
        if not existing:
            frappe.get_doc({
                "doctype": "Leave Policy Assignment",
                "employee": emp_id,
                "leave_policy": a["policy"],
                "leave_period": leave_period_id,
                "effective_from": "2026-01-01",
                "effective_to": "2026-12-31",
                "carry_forward": 0,
            }).insert(ignore_permissions=True)
            print(f"  [+] Leave Policy Assignment: {a['first']} {a['last']} → {a['policy']}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 9d: Leave Approver Hierarchy
# ─────────────────────────────────────────────────────────────────────────────

def setup_leave_approvers():
    gurpreet = _get_employee("Gurpreet", "Singh")     # Logistics Manager
    mukesh = _get_employee("Mukesh", "Mittal")         # Finance Director
    chaitanya = _get_employee("Chaitanya", "Malhotra") # Digital Director

    approver_map = [
        # Drivers → Logistics Manager
        (("Harpreet", "Babbar"),    gurpreet),
        (("Rajinder", "Kumar"),     gurpreet),
        # KAMs → Respective Directors
        (("Arjun", "Sandhu"),       mukesh),
        (("Neha", "Sharma"),        chaitanya),
        (("Rohit", "Verma"),        mukesh),
        (("Priya", "Singh"),        mukesh),
    ]

    for (first, last), approver_id in approver_map:
        emp_id = _get_employee(first, last)
        if emp_id and approver_id:
            approver_email = frappe.db.get_value("Employee", approver_id, "company_email") or \
                             frappe.db.get_value("User", {"full_name": frappe.db.get_value("Employee", approver_id, "employee_name")}, "name")
            if approver_email:
                frappe.db.set_value("Employee", emp_id, "leave_approver", approver_email)
                print(f"  [+] Leave Approver: {first} {last} → {approver_email}")
            else:
                print(f"  [!] No email found for approver {approver_id} — set leave_approver manually")


# ─────────────────────────────────────────────────────────────────────────────
# Main Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def setup_all():
    frappe.set_user("Administrator")

    print("\n══ Phase 8: Employee Onboarding ══")
    task_names = setup_onboarding_tasks()
    frappe.db.commit()
    setup_onboarding_templates(task_names)
    frappe.db.commit()

    print("\n══ Phase 9: Leave Management ══")
    setup_leave_period()
    frappe.db.commit()
    setup_leave_types()
    frappe.db.commit()
    setup_leave_policies()
    frappe.db.commit()
    setup_leave_policy_assignments()
    frappe.db.commit()
    setup_leave_approvers()
    frappe.db.commit()

    print("\n✓ Grace Group Phases 8-9 setup complete!")
    print("  Fleet Reallocation hook is active via hooks.py doc_events.")
