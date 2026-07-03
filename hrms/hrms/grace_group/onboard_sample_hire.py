"""
Grace Group - Instantiate a live Employee Onboarding for a sample hire.

Takes the "Grace Group Standard Onboarding" process (see
setup_onboarding_process.py) and runs it for a sample new hire so you can see
the generated Project, Tasks and role-based ToDo assignments.

It ensures the prerequisites an Employee Onboarding needs:
  - a Holiday List (task dates skip holidays),
  - one enabled demo User per activity role (so ToDos have a real assignee),
  - a Job Applicant + Job Offer for the hire.

Then it creates and submits the Employee Onboarding, which fans the 5 template
activities out into 5 Tasks, each assigned to the user holding that role.

Run: bench execute hrms.grace_group.onboard_sample_hire.run
"""

import frappe
from frappe.utils import today

COMPANY = "Grace Group"
TEMPLATE_NAME = "Grace Group Standard Onboarding"

CANDIDATE_NAME = "Manjit Singh"
CANDIDATE_EMAIL = "manjit.singh@demo.gracegrp.in"
CANDIDATE_DESIGNATION = "Delivery Executive"
JOINING_DATE = "2026-08-01"

HOLIDAY_LIST = "Grace Group 2026 Holidays"

# One demo user per role used by the onboarding process.
ROLE_USERS = [
    ("HR Manager", "hr.manager@demo.gracegrp.in", "Harleen", "Kaur"),
    ("System Manager", "it.admin@demo.gracegrp.in", "Rahul", "Nair"),
    ("Logistics Manager", "logistics.manager@demo.gracegrp.in", "Gurpreet", "Singh"),
    ("Warehouse Manager", "warehouse.manager@demo.gracegrp.in", "Amit", "Patel"),
    ("Sales Manager", "sales.manager@demo.gracegrp.in", "Neha", "Sharma"),
]


def _exists(doctype, name):
    return bool(frappe.db.exists(doctype, name))


def _template_docname():
    """The template is autonamed (HR-EMP-ONT-#####); resolve it by its title."""
    return frappe.db.get_value(
        "Employee Onboarding Template", {"title": TEMPLATE_NAME}, "name"
    )


def ensure_holiday_list():
    if _exists("Holiday List", HOLIDAY_LIST):
        return HOLIDAY_LIST
    frappe.get_doc({
        "doctype": "Holiday List",
        "holiday_list_name": HOLIDAY_LIST,
        "from_date": "2026-01-01",
        "to_date": "2026-12-31",
        "holidays": [
            {"holiday_date": "2026-01-26", "description": "Republic Day"},
            {"holiday_date": "2026-08-15", "description": "Independence Day"},
        ],
    }).insert(ignore_permissions=True)
    print(f"  [+] Holiday List: {HOLIDAY_LIST}")
    return HOLIDAY_LIST


def ensure_role_users():
    """Create one enabled System User per role so onboarding ToDos get assigned."""
    for role, email, first, last in ROLE_USERS:
        if not _exists("Role", role):
            frappe.get_doc(
                {"doctype": "Role", "role_name": role, "desk_access": 1}
            ).insert(ignore_permissions=True)
            print(f"  [+] Role: {role}")

        if not _exists("User", email):
            frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": first,
                "last_name": last,
                "send_welcome_email": 0,
                "user_type": "System User",
                "enabled": 1,
                "roles": [{"role": role}],
            }).insert(ignore_permissions=True)
            print(f"  [+] User: {email} ({role})")
        elif not frappe.db.exists("Has Role", {"parent": email, "role": role}):
            user = frappe.get_doc("User", email)
            user.append("roles", {"role": role})
            user.save(ignore_permissions=True)
            print(f"  [=] Added role {role} to existing user {email}")


def ensure_applicant_and_offer():
    applicant = frappe.db.get_value("Job Applicant", {"email_id": CANDIDATE_EMAIL}, "name")
    if not applicant:
        doc = frappe.get_doc({
            "doctype": "Job Applicant",
            "applicant_name": CANDIDATE_NAME,
            "email_id": CANDIDATE_EMAIL,
            "designation": CANDIDATE_DESIGNATION,
            "status": "Accepted",
        }).insert(ignore_permissions=True)
        applicant = doc.name
        print(f"  [+] Job Applicant: {applicant} — {CANDIDATE_NAME}")

    offer = frappe.db.get_value("Job Offer", {"job_applicant": applicant}, "name")
    if not offer:
        doc = frappe.get_doc({
            "doctype": "Job Offer",
            "job_applicant": applicant,
            "applicant_name": CANDIDATE_NAME,
            "designation": CANDIDATE_DESIGNATION,
            "company": COMPANY,
            "offer_date": today(),
            "status": "Accepted",
        }).insert(ignore_permissions=True)
        offer = doc.name
        print(f"  [+] Job Offer: {offer} → {CANDIDATE_NAME}")

    return applicant, offer


def create_onboarding(applicant, offer, holiday_list):
    existing = frappe.db.get_value("Employee Onboarding", {"job_applicant": applicant}, "name")
    if existing:
        print(f"  [=] Employee Onboarding already exists: {existing}")
        return existing

    template_docname = _template_docname()
    template = frappe.get_doc("Employee Onboarding Template", template_docname)
    activities = [
        {
            "activity_name": a.activity_name,
            "user": a.user,
            "role": a.role,
            "task_weight": a.task_weight,
            "required_for_employee_creation": a.required_for_employee_creation,
            "description": a.description,
            "duration": a.duration,
            "begin_on": a.begin_on,
        }
        for a in template.activities
    ]

    doc = frappe.get_doc({
        "doctype": "Employee Onboarding",
        "job_applicant": applicant,
        "job_offer": offer,
        "employee_name": CANDIDATE_NAME,
        "company": COMPANY,
        "designation": CANDIDATE_DESIGNATION,
        "date_of_joining": JOINING_DATE,
        "boarding_begins_on": JOINING_DATE,
        "holiday_list": holiday_list,
        "employee_onboarding_template": template_docname,
        "notify_users_by_email": 0,
        "activities": activities,
    })
    doc.insert(ignore_permissions=True)
    doc.submit()
    frappe.db.commit()
    print(f"  [+] Employee Onboarding: {doc.name} (submitted) — project {doc.project}")
    return doc.name


def report(onboarding_name):
    doc = frappe.get_doc("Employee Onboarding", onboarding_name)
    print(f"\n  Generated tasks for project '{doc.project}':")
    tasks = frappe.get_all(
        "Task",
        filters={"project": doc.project},
        fields=["name", "subject", "exp_start_date", "exp_end_date"],
        order_by="exp_start_date",
    )
    for t in tasks:
        assignees = frappe.get_all(
            "ToDo",
            filters={"reference_type": "Task", "reference_name": t.name, "status": "Open"},
            pluck="allocated_to",
        )
        who = ", ".join(assignees) if assignees else "(unassigned)"
        print(f"    - {t.subject}")
        print(f"        {t.exp_start_date} → {t.exp_end_date}  assigned to: {who}")


def run():
    frappe.set_user("Administrator")

    if not _template_docname():
        frappe.throw(
            f"Onboarding process '{TEMPLATE_NAME}' not found. "
            "Run hrms.grace_group.setup_onboarding_process.setup_all first."
        )

    print("\n══ Instantiate onboarding for sample hire ══")
    holiday_list = ensure_holiday_list()
    ensure_role_users()
    frappe.db.commit()
    applicant, offer = ensure_applicant_and_offer()
    frappe.db.commit()
    onboarding = create_onboarding(applicant, offer, holiday_list)
    report(onboarding)

    print("\n✓ Sample onboarding instantiated.")
