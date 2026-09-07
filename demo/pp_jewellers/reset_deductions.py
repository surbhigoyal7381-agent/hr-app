"""Undo every Attendance Deduction the late-coming rule created, so the rule
can be run again from scratch. Cancelling puts the leave and the pay back.

Usage: bench --site <site> execute demo.pp_jewellers.reset_deductions.run
   or: cd sites && ../env/bin/python <repo>/demo/pp_jewellers/reset_deductions.py <site>
"""

import sys

import frappe


def run():
    names = frappe.get_all("Attendance Deduction", filters={"docstatus": ["!=", 2]}, pluck="name")
    for name in names:
        doc = frappe.get_doc("Attendance Deduction", name)
        doc.flags.ignore_permissions = True
        if doc.docstatus == 1:
            doc.cancel()
    for name in frappe.get_all("Attendance Deduction", pluck="name"):
        frappe.delete_doc("Attendance Deduction", name, ignore_permissions=True, force=True)
    for name in frappe.get_all("Additional Salary", filters={"docstatus": 2, "ref_doctype": "Attendance Deduction"}, pluck="name"):
        frappe.delete_doc("Additional Salary", name, ignore_permissions=True, force=True)
    frappe.db.set_value("Attendance Deduction Rule", {"name": ["like", "%"]}, "last_processed_week", None, update_modified=False)
    frappe.db.commit()
    print(f"removed {len(names)} attendance deductions")


if __name__ == "__main__":
    frappe.init(site=sys.argv[1])
    frappe.connect()
    run()
