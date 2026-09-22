"""
Shared helpers for the Sargam Metals demo seed scripts.

Every seed script does:
    import sys, os; sys.path.insert(0, os.environ.get("SARGAM_SCRIPT_DIR", "/tmp/sargam")); from sargam_common import *

Scripts can be run two ways:
  1. bench --site <site> console < seed_x.py        (frappe already connected)
  2. env/bin/python seed_x.py --site <site>         (connect() below does init + connect)

Mirrors demo/pp_jewellers/ppj_common.py - same idiom, same reasons. Read that
file's comments (naming-series bug, the password gate) before changing this one.
"""
import os
import sys

import frappe

COMPANY_IN = "Sargam Metals Pvt Ltd"
ABBR_IN = "SML"
COMPANY_SG = "Cuproban Systems Singapore Pte Ltd"
ABBR_SG = "CSS"

FY_START, FY_END = "2026-04-01", "2027-03-31"


def demo_password():
    """The seeded users' password, or stop before writing anything.

    No built-in default - a shared password in public code is a shared
    password anyone can try on the tenant.
    """
    value = os.environ.get("SARGAM_DEMO_PASSWORD", "").strip()
    if not value:
        sys.exit(
            "SARGAM_DEMO_PASSWORD is not set. Choose a password for the seeded "
            "users and export it before running a script that creates users:\n"
            "  export SARGAM_DEMO_PASSWORD='<a new, strong password>'\n"
            "No user was created."
        )
    return value


def connect():
    """Connect when run as a plain python script (not inside bench console)."""
    if getattr(frappe.local, "site", None) and getattr(frappe.local, "db", None):
        return
    site = None
    if "--site" in sys.argv:
        site = sys.argv[sys.argv.index("--site") + 1]
    site = site or os.environ.get("SARGAM_SITE")
    if not site:
        raise SystemExit("Pass --site <site> or set SARGAM_SITE")
    frappe.init(site=site)
    frappe.connect()
    frappe.set_user("Administrator")


def log(msg):
    print(msg, flush=True)


def ensure(doctype, filters, values=None, submit=False, quiet=False):
    """Return the name of a doc matching `filters`; create it with `values` if missing.

    Same contract as ppj_common.ensure() - `filters` is used both for the
    existence check and as fields on the new doc; `values` are extra fields
    for creation only.
    """
    name = frappe.db.get_value(doctype, filters, "name") if isinstance(filters, dict) else (
        filters if frappe.db.exists(doctype, filters) else None)
    if name:
        return name
    doc = frappe.new_doc(doctype)
    fields = dict(filters) if isinstance(filters, dict) else {}
    fields.update(values or {})
    if isinstance(filters, str):
        doc.name = filters
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


def counts(*doctypes):
    for dt in doctypes:
        log(f"  {dt}: {frappe.db.count(dt)}")
