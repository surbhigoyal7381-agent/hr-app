"""
Shared helpers for the PP Jewellers seed scripts.

Every seed script does:
    import sys, os; sys.path.insert(0, os.environ.get("PPJ_SCRIPT_DIR", "/tmp/ppj")); from ppj_common import *

Scripts can be run two ways:
  1. bench --site <site> console < seed_x.py        (frappe already connected)
  2. env/bin/python seed_x.py --site <site>         (connect() below does init + connect)
Data CSVs are read from PPJ_DATA_DIR (default /tmp/ppj/data).
"""
import csv
import os
import sys

import frappe
from frappe.utils import cint, flt, getdate

COMPANY = "PP Jewellers Pvt Ltd"
ABBR = "PPJ"
DATA_DIR = os.environ.get("PPJ_DATA_DIR", "/tmp/ppj/data")
DEMO_PASSWORD = os.environ.get("PPJ_DEMO_PASSWORD", "Ppj@2026")

HEAD_OFFICE = "PPJ Head Office Chandigarh"
STORES = ["PPJ Chandigarh Sector 17", "PPJ Ambala City", "PPJ Noida Sector 18",
          "PPJ Delhi Karol Bagh", "PPJ Delhi South Extension"]
STORE_SHIFT = "PPJ Store Shift"
HO_SHIFT = "PPJ Head Office Shift"

Q1_START, Q1_END = "2026-04-01", "2026-06-30"
Q2_START, Q2_END = "2026-07-01", "2026-09-30"
FY_START, FY_END = "2026-04-01", "2027-03-31"


def connect():
    """Connect when run as a plain python script (not inside bench console)."""
    if getattr(frappe.local, "site", None) and getattr(frappe.local, "db", None):
        return
    site = None
    if "--site" in sys.argv:
        site = sys.argv[sys.argv.index("--site") + 1]
    site = site or os.environ.get("PPJ_SITE")
    if not site:
        raise SystemExit("Pass --site <site> or set PPJ_SITE")
    frappe.init(site=site)
    frappe.connect()
    frappe.set_user("Administrator")


def log(msg):
    print(msg, flush=True)


def read_csv(name):
    path = os.path.join(DATA_DIR, name)
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def exists(doctype, name_or_filters):
    return frappe.db.exists(doctype, name_or_filters)


def ensure(doctype, filters, values=None, submit=False, quiet=False):
    """Return the name of a doc matching `filters`; create it with `values` if missing.

    `filters` is a dict used both for the existence check and as fields on the
    new doc. `values` are extra fields for creation only.
    """
    name = frappe.db.get_value(doctype, filters, "name") if isinstance(filters, dict) else (
        filters if frappe.db.exists(doctype, filters) else None)
    if name:
        return name
    doc = frappe.new_doc(doctype)
    fields = dict(filters) if isinstance(filters, dict) else {}
    fields.update(values or {})
    if isinstance(filters, str):
        doc.name = filters          # honoured by Prompt-named doctypes; field-named ones set it from the field
        doc.set("__newname", filters)
    for k, v in fields.items():
        if isinstance(v, list):
            for row in v:
                doc.append(k, row)
        else:
            doc.set(k, v)
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    if submit:
        doc.submit()
    if not quiet:
        log(f"  [created] {doctype}: {doc.name}")
    return doc.name


def submit_if_draft(doctype, name):
    doc = frappe.get_doc(doctype, name)
    if doc.docstatus == 0:
        doc.flags.ignore_permissions = True
        doc.submit()
    return doc


def commit():
    frappe.db.commit()


def dept(name):
    """Department docnames carry the company abbreviation."""
    return f"{name} - {ABBR}"


def employees(**filters):
    filters.setdefault("company", COMPANY)
    return frappe.get_all("Employee", filters=filters,
                          fields=["name", "employee_name", "designation", "department", "branch",
                                  "reports_to", "grade as employee_grade", "user_id", "holiday_list",
                                  "default_shift", "date_of_joining", "gender"],
                          order_by="name asc")


def emp_map():
    return {e.name: e for e in employees()}


def month_range(year, month):
    from calendar import monthrange
    from datetime import date
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def counts(*doctypes):
    for dt in doctypes:
        log(f"  {dt}: {frappe.db.count(dt)}")


def make_user(email, first_name, last_name, roles):
    """Create (or update) a System User with the demo password and the given roles."""
    email = email.strip().lower()
    roles = ["Employee"] + [r for r in roles if r != "Employee"]
    for r in roles:
        if not frappe.db.exists("Role", r):
            frappe.get_doc({"doctype": "Role", "role_name": r}).insert(ignore_permissions=True)
    if frappe.db.exists("User", email):
        user = frappe.get_doc("User", email)
        have = {r.role for r in user.roles}
        for r in roles:
            if r not in have:
                user.append("roles", {"role": r})
        user.save(ignore_permissions=True)
    else:
        user = frappe.get_doc({"doctype": "User", "email": email, "first_name": first_name, "last_name": last_name,
                               "send_welcome_email": 0, "user_type": "System User", "new_password": DEMO_PASSWORD,
                               "roles": [{"role": r} for r in roles]})
        user.flags.no_welcome_mail = True
        frappe.flags.in_import = True       # bypass the 60-per-hour user creation throttle
        try:
            user.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_import = False
    return email


def add_role_to_user(email, role):
    if not frappe.db.exists("Role", role):
        frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)
    user = frappe.get_doc("User", email)
    if role not in {r.role for r in user.roles}:
        user.append("roles", {"role": role})
        user.save(ignore_permissions=True)


def first_employee(designation, branch=None):
    filters = {"designation": designation, "status": "Active", "company": COMPANY}
    if branch:
        filters["branch"] = branch
    rows = frappe.get_all("Employee", filters=filters, fields=["name", "user_id", "employee_name", "branch"],
                          order_by="name asc", limit=1)
    return rows[0] if rows else None


def assign_holiday_list(assigned_to, holiday_list, from_date, applicable_for="Employee"):
    """This Frappe HR version resolves holidays through Holiday List Assignment, not Employee.holiday_list."""
    if not frappe.db.exists("DocType", "Holiday List Assignment"):
        return
    if frappe.db.exists("Holiday List Assignment", {"assigned_to": assigned_to, "from_date": from_date, "docstatus": 1}):
        return
    hla = frappe.get_doc({"doctype": "Holiday List Assignment", "applicable_for": applicable_for,
                          "assigned_to": assigned_to, "holiday_list": holiday_list, "from_date": from_date})
    hla.flags.ignore_permissions = True
    hla.insert()
    hla.submit()
