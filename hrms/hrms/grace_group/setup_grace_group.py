"""
Grace Group FMCG Distribution - Frappe HR Demo Setup
Phases 1-7: Org Structure, Fleet, Geo-Fenced Attendance, Custom Doctype,
            Performance Management, Executive Dashboard, Agentic Automation

Run: bench execute hrms.grace_group.setup_grace_group.setup_all
"""

import json
import frappe
from frappe.utils import today, getdate, nowdate


COMPANY = "Grace Group"
COMPANY_ABBR = "GG"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

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
# Phase 1a: Company
# ─────────────────────────────────────────────────────────────────────────────

def setup_company():
    if not _exists("Company", COMPANY):
        frappe.get_doc({
            "doctype": "Company",
            "company_name": COMPANY,
            "abbr": COMPANY_ABBR,
            "default_currency": "INR",
            "country": "India",
        }).insert(ignore_permissions=True)
        print(f"  [+] Company: {COMPANY}")
    else:
        print(f"  [=] Company already exists: {COMPANY}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1b: Departments
# ─────────────────────────────────────────────────────────────────────────────

def setup_departments():
    for dept_name in ["Management", "Sales", "Supply Chain", "Logistics", "IT", "HR"]:
        if not _exists("Department", _dept(dept_name)):
            frappe.get_doc({
                "doctype": "Department",
                "department_name": dept_name,
                "company": COMPANY,
            }).insert(ignore_permissions=True)
            print(f"  [+] Department: {dept_name}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1c: Designations
# ─────────────────────────────────────────────────────────────────────────────

def setup_designations():
    designations = [
        "Promoter & Director - Strategy",
        "Promoter & Director - Finance",
        "Promoter & Director - Digital",
        "KAM - Dairy",
        "KAM - Snacks",
        "KAM - Processed Foods",
        "KAM - Hardware",
        "Cold Storage Supervisor",
        "Warehouse Supervisor",
        "Logistics Manager",
        "Delivery Executive",
    ]
    for desig in designations:
        if not _exists("Designation", desig):
            frappe.get_doc({"doctype": "Designation", "designation_name": desig}).insert(
                ignore_permissions=True
            )
            print(f"  [+] Designation: {desig}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1c-b: Branches
# ─────────────────────────────────────────────────────────────────────────────

def setup_branches():
    for branch in ["Chandigarh", "Panchkula", "Head Office"]:
        if not _exists("Branch", branch):
            frappe.get_doc({"doctype": "Branch", "branch": branch}).insert(ignore_permissions=True)
            print(f"  [+] Branch: {branch}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1d: Employees
# ─────────────────────────────────────────────────────────────────────────────

def _make_employee(first_name, last_name, designation, department, gender="Male", branch=None):
    existing = _get_employee(first_name, last_name)
    if existing:
        return existing
    fields = {
        "doctype": "Employee",
        "first_name": first_name,
        "last_name": last_name,
        "designation": designation,
        "department": _dept(department),
        "company": COMPANY,
        "date_of_joining": "2024-01-01",
        "date_of_birth": "1985-06-15",
        "status": "Active",
        "gender": gender,
    }
    if branch:
        fields["branch"] = branch
    doc = frappe.get_doc(fields)
    doc.insert(ignore_permissions=True)
    print(f"  [+] Employee: {first_name} {last_name} ({designation})")
    return doc.name


def _link_reports_to(employee_id, manager_id):
    if employee_id and manager_id:
        frappe.db.set_value("Employee", employee_id, "reports_to", manager_id)


def setup_employees():
    # C-Suite – no reports_to
    dk = _make_employee("D.K.", "Malhotra", "Promoter & Director - Strategy", "Management")
    mukesh = _make_employee("Mukesh", "Mittal", "Promoter & Director - Finance", "Management")
    chaitanya = _make_employee("Chaitanya", "Malhotra", "Promoter & Director - Digital", "Management")

    # KAMs – reports to respective director
    arjun = _make_employee("Arjun", "Sandhu", "KAM - Dairy", "Sales")
    neha = _make_employee("Neha", "Sharma", "KAM - Snacks", "Sales", gender="Female")
    rohit = _make_employee("Rohit", "Verma", "KAM - Processed Foods", "Sales")
    priya = _make_employee("Priya", "Singh", "KAM - Hardware", "Sales", gender="Female")

    # Warehouse Supervisors – reports to Mukesh Mittal
    vikramjeet = _make_employee("Vikramjeet", "Singh", "Cold Storage Supervisor", "Supply Chain", branch="Chandigarh")
    amit = _make_employee("Amit", "Patel", "Warehouse Supervisor", "Supply Chain", branch="Panchkula")
    sandeep = _make_employee("Sandeep", "Kaur", "Cold Storage Supervisor", "Supply Chain", gender="Female")

    # Logistics – Gurpreet is Manager, Harpreet & Rajinder are Drivers
    gurpreet = _make_employee("Gurpreet", "Singh", "Logistics Manager", "Logistics")
    harpreet = _make_employee("Harpreet", "Babbar", "Delivery Executive", "Logistics")
    rajinder = _make_employee("Rajinder", "Kumar", "Delivery Executive", "Logistics")

    # Wire hierarchy
    _link_reports_to(arjun, dk)
    _link_reports_to(neha, chaitanya)
    _link_reports_to(rohit, dk)
    _link_reports_to(priya, mukesh)
    _link_reports_to(vikramjeet, mukesh)
    _link_reports_to(amit, mukesh)
    _link_reports_to(sandeep, mukesh)
    _link_reports_to(gurpreet, chaitanya)
    _link_reports_to(harpreet, gurpreet)
    _link_reports_to(rajinder, gurpreet)

    frappe.db.commit()
    print("  [+] Employee hierarchy wired")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: Fleet Management
# ─────────────────────────────────────────────────────────────────────────────

def setup_fleet():
    vehicles = [
        {"license_plate": "PB-65-AA-0001", "driver": "Harpreet", "driver_last": "Babbar"},
        {"license_plate": "PB-65-AA-0002", "driver": "Rajinder", "driver_last": "Kumar"},
    ]

    for v in vehicles:
        plate = v["license_plate"]
        if not _exists("Vehicle", plate):
            frappe.get_doc({
                "doctype": "Vehicle",
                "license_plate": plate,
                "make": "Mahindra",
                "model": "Bolero Camper",
                "year": 2023,
                "fuel_type": "Diesel",
                "uom": "Kilometer",
                "last_odometer": 0,
                "company": COMPANY,
            }).insert(ignore_permissions=True)
            print(f"  [+] Vehicle: {plate}")

        # Link vehicle to driver via Vehicle Log
        emp_id = _get_employee(v["driver"], v["driver_last"])
        if emp_id:
            existing_log = frappe.db.exists("Vehicle Log", {"license_plate": plate, "employee": emp_id})
            if not existing_log:
                frappe.get_doc({
                    "doctype": "Vehicle Log",
                    "license_plate": plate,
                    "employee": emp_id,
                    "date": today(),
                    "activity_type": "Receipt",
                    "odometer": 0,
                    "company": COMPANY,
                }).insert(ignore_permissions=True)
                print(f"  [+] Vehicle Log: {plate} → {emp_id}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: Geo-Fenced Mobile Attendance
# ─────────────────────────────────────────────────────────────────────────────

def setup_locations():
    locations = [
        {
            "location_name": "Chandigarh Warehouse",
            "latitude": 30.7333,
            "longitude": 76.7794,
            "geofence_radius": 100,
        },
        {
            "location_name": "Panchkula Warehouse",
            "latitude": 30.6942,
            "longitude": 76.8606,
            "geofence_radius": 100,
        },
    ]
    for loc in locations:
        if not _exists("Location", loc["location_name"]):
            frappe.get_doc({"doctype": "Location", **loc}).insert(ignore_permissions=True)
            print(f"  [+] Location: {loc['location_name']}")


def setup_shift_types():
    shifts = [
        {
            "name": "Q-Comm Morning Shift",
            "start_time": "05:30:00",
            "end_time": "13:30:00",
            "enable_auto_attendance": 1,
            "allow_check_in_before_shift_start_time": 30,
            "process_attendance_after": "2026-01-01 00:00:00",
        },
        {
            "name": "GT Day Shift",
            "start_time": "08:00:00",
            "end_time": "17:00:00",
            "enable_auto_attendance": 1,
            "allow_check_in_before_shift_start_time": 30,
            "process_attendance_after": "2026-01-01 00:00:00",
        },
    ]
    for s in shifts:
        name = s["name"]
        if not _exists("Shift Type", name):
            frappe.get_doc({"doctype": "Shift Type", **s}).insert(ignore_permissions=True)
            print(f"  [+] Shift Type: {name}")


def enable_geolocation_tracking():
    settings = frappe.get_single("HR Settings")
    if not getattr(settings, "allow_geolocation_tracking", None):
        try:
            settings.allow_geolocation_tracking = 1
            settings.save(ignore_permissions=True)
            print("  [+] HR Settings: Geolocation tracking enabled")
        except Exception:
            print("  [!] HR Settings: allow_geolocation_tracking field not found — enable manually")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Custom Doctype – Daily Route Log
# ─────────────────────────────────────────────────────────────────────────────

def setup_daily_route_log_doctype():
    if _exists("DocType", "Daily Route Log"):
        print("  [=] DocType already exists: Daily Route Log")
        return

    import os
    fixture_path = os.path.join(
        os.path.dirname(__file__), "fixtures", "daily_route_log.json"
    )
    with open(fixture_path) as f:
        meta = json.load(f)

    doc = frappe.get_doc(meta)
    doc.insert(ignore_permissions=True)
    print("  [+] Custom DocType: Daily Route Log")

    # Create "Logistics Manager" Role if it doesn't exist
    if not _exists("Role", "Logistics Manager"):
        frappe.get_doc({"doctype": "Role", "role_name": "Logistics Manager"}).insert(
            ignore_permissions=True
        )
        print("  [+] Role: Logistics Manager")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5: Performance Management – Goals, KRAs, Appraisal Template
# ─────────────────────────────────────────────────────────────────────────────

def setup_kras():
    kras = [
        ("Attendance Reliability", "Measures on-time and present shift consistency"),
        ("Route Efficiency", "Measures completed drops vs RTO rate"),
        ("Q-Comm SLA Protection", "Zero delivery penalties on Q-Comm routes"),
        ("Zero Perishable Spoilage", "Reduce cold storage wastage by target %"),
        ("Q-Comm Snack Dominance", "Penalty rate below 2% on snack deliveries"),
        ("Accelerate Group Growth", "Achieve turnover target above 180 Cr"),
    ]
    created = {}
    for title, desc in kras:
        if not _exists("KRA", title):
            doc = frappe.get_doc({"doctype": "KRA", "title": title, "description": desc})
            doc.insert(ignore_permissions=True)
            print(f"  [+] KRA: {title}")
            created[title] = doc.name
        else:
            created[title] = title
    return created


def setup_appraisal_cycle():
    cycle_name = "Grace Group Jan–Jun 2026"
    if not _exists("Appraisal Cycle", cycle_name):
        doc = frappe.get_doc({
            "doctype": "Appraisal Cycle",
            "cycle_name": cycle_name,
            "company": COMPANY,
            "start_date": "2026-01-01",
            "end_date": "2026-06-30",
            "kra_evaluation_method": "Manual Rating",
        })
        doc.insert(ignore_permissions=True)
        print(f"  [+] Appraisal Cycle: {cycle_name}")
        return doc.name
    return cycle_name


def setup_goals(kras, cycle_name):
    goal_matrix = [
        ("D.K.", "Malhotra", "Accelerate Group Growth", "Achieve group turnover > 180 Cr in FY2026"),
        ("Neha", "Sharma", "Q-Comm Snack Dominance", "Maintain SLA penalty rate < 2% on Lay's & Kurkure routes"),
        ("Vikramjeet", "Singh", "Zero Perishable Spoilage", "Reduce cold storage wastage by 20% vs prior period"),
        ("Harpreet", "Babbar", "Q-Comm SLA Protection", "Zero delivery penalties on all Q-Comm routes"),
        ("Rajinder", "Kumar", "Route Efficiency", "Maintain RTO rate < 5% across all assigned routes"),
    ]
    for first, last, goal_name, description in goal_matrix:
        emp_id = _get_employee(first, last)
        if not emp_id:
            print(f"  [!] Employee not found: {first} {last} — skipping goal")
            continue
        existing = frappe.db.exists("Goal", {"goal_name": goal_name, "employee": emp_id})
        if not existing:
            frappe.get_doc({
                "doctype": "Goal",
                "goal_name": goal_name,
                "employee": emp_id,
                "company": COMPANY,
                "description": description,
                "start_date": "2026-01-01",
                "end_date": "2026-06-30",
                "status": "In Progress",
                "appraisal_cycle": cycle_name,
                "kra": kras.get(goal_name),
            }).insert(ignore_permissions=True)
            print(f"  [+] Goal: {goal_name} → {first} {last}")


def setup_appraisal_template(kras):
    template_name = "Delivery Executive Review"
    if not _exists("Appraisal Template", template_name):
        frappe.get_doc({
            "doctype": "Appraisal Template",
            "template_title": template_name,
            "goals": [
                {
                    "doctype": "Appraisal Template Goal",
                    "key_result_area": kras.get("Attendance Reliability", "Attendance Reliability"),
                    "per_weightage": 40,
                },
                {
                    "doctype": "Appraisal Template Goal",
                    "key_result_area": kras.get("Route Efficiency", "Route Efficiency"),
                    "per_weightage": 60,
                },
            ],
        }).insert(ignore_permissions=True)
        print(f"  [+] Appraisal Template: {template_name}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6: Executive Dashboard – Promoter Command Center
# ─────────────────────────────────────────────────────────────────────────────

def setup_promoter_role():
    if not _exists("Role", "Promoter"):
        frappe.get_doc({"doctype": "Role", "role_name": "Promoter"}).insert(
            ignore_permissions=True
        )
        print("  [+] Role: Promoter")


def setup_number_cards():
    cards = [
        {
            "name": "Fleet Readiness Today",
            "label": "Fleet Readiness Today",
            "document_type": "Attendance",
            "function": "Count",
            "filters_json": json.dumps([
                ["Attendance", "attendance_date", "=", "Today"],
                ["Attendance", "shift", "in", "Q-Comm Morning Shift,GT Day Shift"],
                ["Attendance", "status", "=", "Present"],
            ]),
            "is_public": 1,
        },
        {
            "name": "Q-Comm SLA Breaches This Month",
            "label": "Q-Comm SLA Breaches",
            "document_type": "Daily Route Log",
            "function": "Count",
            "filters_json": json.dumps([
                ["Daily Route Log", "penalty_logged", "=", 1],
                ["Daily Route Log", "route_category", "=", "Q-Comm"],
                ["Daily Route Log", "date", "Timespan", "this month"],
            ]),
            "is_public": 1,
        },
        {
            "name": "Open Appraisals",
            "label": "Open Appraisals",
            "document_type": "Appraisal",
            "function": "Count",
            "filters_json": json.dumps([
                ["Appraisal", "docstatus", "=", 0],
            ]),
            "is_public": 1,
        },
    ]
    for card in cards:
        if not _exists("Number Card", card["name"]):
            frappe.get_doc({"doctype": "Number Card", **card}).insert(ignore_permissions=True)
            print(f"  [+] Number Card: {card['name']}")


def setup_dashboard_charts():
    charts = [
        {
            "chart_name": "Efficiency vs RTO (Weekly)",
            "chart_type": "Group By",
            "document_type": "Daily Route Log",
            "based_on": "date",
            "group_by_based_on": "date",
            "group_by_type": "Count",
            "time_interval": "Weekly",
            "timeseries": 1,
            "filters_json": "[]",
            "type": "Line",
            "is_public": 1,
        },
        {
            "chart_name": "Performance Score Distribution",
            "chart_type": "Group By",
            "document_type": "Appraisal",
            "group_by_based_on": "final_score",
            "aggregate_function_based_on": "final_score",
            "aggregate_function": "Count",
            "type": "Bar",
            "filters_json": "[]",
            "is_public": 1,
        },
    ]
    for chart in charts:
        name = chart["chart_name"]
        if not _exists("Dashboard Chart", name):
            try:
                frappe.get_doc({"doctype": "Dashboard Chart", **chart}).insert(
                    ignore_permissions=True
                )
                print(f"  [+] Dashboard Chart: {name}")
            except Exception as e:
                print(f"  [!] Dashboard Chart skipped ({name}): {e}")


def setup_promoter_workspace():
    ws_name = "Promoter Command Center"
    if _exists("Workspace", ws_name):
        print(f"  [=] Workspace already exists: {ws_name}")
        return

    content = json.dumps([
        {"type": "header", "data": {"text": "Grace Group – Promoter Command Center", "level": 2}},
        {"type": "card", "data": {"card_name": "Fleet Readiness Today"}},
        {"type": "card", "data": {"card_name": "Q-Comm SLA Breaches This Month"}},
        {"type": "card", "data": {"card_name": "Open Appraisals"}},
        {"type": "chart", "data": {"chart_name": "Efficiency vs RTO (Weekly)"}},
        {"type": "chart", "data": {"chart_name": "Performance Score Distribution"}},
        {
            "type": "shortcut",
            "data": {
                "shortcut_name": "Daily Route Log",
                "link_to": "Daily Route Log",
                "type": "DocType",
            },
        },
    ])

    frappe.get_doc({
        "doctype": "Workspace",
        "name": ws_name,
        "label": ws_name,
        "title": ws_name,
        "module": "HR",
        "is_standard": 0,
        "public": 1,
        "roles": [{"role": "Promoter"}],
        "content": content,
    }).insert(ignore_permissions=True)
    print(f"  [+] Workspace: {ws_name}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7: Agentic Automation – Auto Email Report
# ─────────────────────────────────────────────────────────────────────────────

def setup_auto_email_report():
    report_name = "Daily Route Log SLA Breaches"

    # Create a simple query report for Daily Route Log first
    if not _exists("Report", report_name):
        try:
            frappe.get_doc({
                "doctype": "Report",
                "report_name": report_name,
                "report_type": "Query Report",
                "ref_doctype": "Daily Route Log",
                "is_standard": "No",
                "query": """
SELECT
    drl.name AS `Log ID`,
    drl.employee AS `Employee`,
    drl.date AS `Date`,
    drl.vehicle AS `Vehicle`,
    drl.route_category AS `Route`,
    drl.completed_drops AS `Drops`,
    drl.rto_count AS `RTO Count`,
    drl.penalty_logged AS `Penalty Logged`,
    drl.remarks AS `Remarks`
FROM
    `tabDaily Route Log` drl
WHERE
    drl.docstatus = 1
    AND (drl.penalty_logged = 1 OR drl.rto_count > 5)
ORDER BY
    drl.date DESC
""",
            }).insert(ignore_permissions=True)
            print(f"  [+] Report: {report_name}")
        except Exception as e:
            print(f"  [!] Report creation skipped: {e}")

    # Fetch recipient emails
    chaitanya = _get_employee("Chaitanya", "Malhotra")
    mukesh = _get_employee("Mukesh", "Mittal")
    emails = []
    for emp_id in [chaitanya, mukesh]:
        if emp_id:
            email = (
                frappe.db.get_value("Employee", emp_id, "company_email")
                or frappe.db.get_value("Employee", emp_id, "personal_email")
                or frappe.db.get_value("Employee", emp_id, "user_id")
            )
            if email:
                emails.append(email)

    email_to = ",".join(emails) if emails else "directors@gracegroup.in"

    auto_report_name = f"Auto: {report_name}"
    if not _exists("Auto Email Report", auto_report_name):
        try:
            frappe.get_doc({
                "doctype": "Auto Email Report",
                "name": auto_report_name,
                "report": report_name,
                "email_to": email_to,
                "frequency": "Daily",
                "send_at": "09:00:00",
                "enabled": 1,
                "format": "HTML",
                "filters": json.dumps([
                    ["Daily Route Log", "penalty_logged", "=", 1],
                ]),
            }).insert(ignore_permissions=True)
            print(f"  [+] Auto Email Report: {auto_report_name} → {email_to}")
        except Exception as e:
            print(f"  [!] Auto Email Report skipped: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Main Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def setup_all():
    frappe.set_user("Administrator")

    print("\n══ Phase 1: Core Organizational Data ══")
    setup_company()
    frappe.db.commit()
    setup_departments()
    frappe.db.commit()
    setup_branches()
    frappe.db.commit()
    setup_designations()
    frappe.db.commit()
    setup_employees()

    print("\n══ Phase 2: Fleet Management ══")
    setup_fleet()
    frappe.db.commit()

    print("\n══ Phase 3: Geo-Fenced Attendance ══")
    setup_locations()
    setup_shift_types()
    enable_geolocation_tracking()
    frappe.db.commit()

    print("\n══ Phase 4: Custom Doctype – Daily Route Log ══")
    setup_daily_route_log_doctype()
    frappe.db.commit()

    print("\n══ Phase 5: Performance Management ══")
    kras = setup_kras()
    frappe.db.commit()
    cycle_name = setup_appraisal_cycle()
    frappe.db.commit()
    setup_goals(kras, cycle_name)
    frappe.db.commit()
    setup_appraisal_template(kras)
    frappe.db.commit()

    print("\n══ Phase 6: Executive Dashboard ══")
    setup_promoter_role()
    setup_number_cards()
    setup_dashboard_charts()
    setup_promoter_workspace()
    frappe.db.commit()

    print("\n══ Phase 7: Agentic Automation ══")
    setup_auto_email_report()
    frappe.db.commit()

    print("\n✓ Grace Group Phases 1-7 setup complete!")
    print("  Next: bench execute hrms.grace_group.setup_onboarding_leaves.setup_all")
