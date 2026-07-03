"""
Grace Group FMCG Distribution - Employee Onboarding Process

Creates a reusable "Employee Onboarding Template" (the onboarding process
definition) with 5 activities, each assigned to a DIFFERENT role in the
organisation. When the template is applied to a new hire (Employee
Onboarding), each activity raises a to-do for whoever holds that role.

Roles used (one per activity):
  1. HR Manager        – document & background verification
  2. System Manager    – IT provisioning (email / app / permissions)
  3. Logistics Manager – fleet & vehicle allocation
  4. Warehouse Manager – cold-chain & Q-Comm SLA safety briefing
  5. Sales Manager     – FMCG brand & key-account training

Run: bench execute hrms.grace_group.setup_onboarding_process.setup_all
"""

import frappe

COMPANY = "Grace Group"
COMPANY_ABBR = "GG"
TEMPLATE_NAME = "Grace Group Standard Onboarding"


def _exists(doctype, name):
    return bool(frappe.db.exists(doctype, name))


def _hr_department():
    """Resolve an HR department for this company if one exists, else None.

    Different Grace Group site builds name it differently ("HR - GG" from the
    custom org setup, "Human Resources - GG" from the default ERPNext tree), so
    probe both and fall back to no department (the field is optional).
    """
    for name in (f"HR - {COMPANY_ABBR}", f"Human Resources - {COMPANY_ABBR}"):
        if _exists("Department", name):
            return name
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Onboarding process: 5 activities, each owned by a distinct role
# (activity_name, role, begin_on_day, duration_days, weight, description)
# ─────────────────────────────────────────────────────────────────────────────

ONBOARDING_ACTIVITIES = [
    ("Document Verification & Background Check", "HR Manager", 0, 2, 0.20,
     "Collect and verify ID proof, commercial driving license, police "
     "verification and address proof for the new hire."),
    ("Provision Email, Frappe HR App & Role Permissions", "System Manager", 0, 1, 0.20,
     "Create corporate email, configure Frappe HR mobile-app access and "
     "assign role-based permissions."),
    ("Fleet & Vehicle Allocation", "Logistics Manager", 1, 1, 0.20,
     "Assign a vehicle from the fleet pool, create the Vehicle Log entry "
     "and brief the hire on the maintenance SOP."),
    ("Cold-Chain & Q-Comm SLA Safety Briefing", "Warehouse Manager", 2, 1, 0.20,
     "Conduct the mandatory cold-chain handling and Q-Commerce delivery-SLA "
     "safety briefing."),
    ("FMCG Brand & Key-Account Training", "Sales Manager", 3, 2, 0.20,
     "Complete brand-knowledge training (product range, pricing) and the "
     "key-account handling protocol."),
]


def ensure_roles():
    """Each activity links to a Role; create any that don't already exist."""
    for _name, role, *_rest in ONBOARDING_ACTIVITIES:
        if not _exists("Role", role):
            frappe.get_doc(
                {"doctype": "Role", "role_name": role, "desk_access": 1}
            ).insert(ignore_permissions=True)
            print(f"  [+] Role: {role}")
    frappe.db.commit()


def setup_onboarding_process():
    existing = frappe.db.get_value(
        "Employee Onboarding Template", {"title": TEMPLATE_NAME}, "name"
    )
    if existing:
        print(f"  [=] Onboarding process already exists: {TEMPLATE_NAME}")
        return

    activities = [
        {
            "activity_name": activity_name,
            "role": role,
            "begin_on": begin_on,
            "duration": duration,
            "task_weight": weight,
            "description": description,
            "required_for_employee_creation": 0,
        }
        for activity_name, role, begin_on, duration, weight, description in ONBOARDING_ACTIVITIES
    ]

    template = {
        "doctype": "Employee Onboarding Template",
        "title": TEMPLATE_NAME,
        "company": COMPANY,
        "activities": activities,
    }
    hr_dept = _hr_department()
    if hr_dept:
        template["department"] = hr_dept

    frappe.get_doc(template).insert(ignore_permissions=True)
    frappe.db.commit()

    print(f"  [+] Onboarding process: {TEMPLATE_NAME}")
    for activity_name, role, *_ in ONBOARDING_ACTIVITIES:
        print(f"      {role:<18} -> {activity_name}")


# ─────────────────────────────────────────────────────────────────────────────
# Main Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def setup_all():
    frappe.set_user("Administrator")

    print("\n══ Grace Group Employee Onboarding Process ══")
    ensure_roles()
    setup_onboarding_process()

    print("\n✓ Onboarding process setup complete!")
    print("  Apply it: HR > Employee Lifecycle > Employee Onboarding > New, "
          f"pick template '{TEMPLATE_NAME}' to raise the 5 role-assigned tasks.")
