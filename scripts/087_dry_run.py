"""Slice 087 (AC-59, OPS-R8): does the new punch reader move any day?

With the set-aside field set on no punch, the reader `_punches` must count exactly
what the old reader counted. This reads every submitted Attendance row in a window,
counts its punches the old way (no set-aside filter) and the new way (`_punches`),
and prints COUNTS AND ATTENDANCE NAMES ONLY: no employee name, no time. Read only.

Run on a site (a copy, never production):
    bench --site <site> execute alvoraa_portal.scripts_087_dry_run.run   (or paste into a console)
or:  ../env/bin/python scripts/087_dry_run.py <site> [days=60]   from the sites folder
"""
import sys

import frappe
from frappe.utils import add_days, nowdate


def run(days=60):
	from alvoraa_portal.payroll_rules import punch_minutes
	from alvoraa_portal.payroll_rules_apply import _punches

	marked = frappe.db.count("Employee Checkin", {"alvoraa_fix_aside_request": ("is", "set")})
	rows = frappe.get_all("Attendance", filters={"docstatus": 1, "attendance_date": (">=", add_days(nowdate(), -int(days)))},
	                      fields=["name", "employee", "attendance_date"], limit_page_length=0)
	moved = []
	for r in rows:
		old = frappe.get_all("Employee Checkin", filters={"employee": r.employee, "time": (
			"between", [f"{r.attendance_date} 00:00:00", f"{r.attendance_date} 23:59:59"])},
			pluck="time", order_by="time asc")
		old_count = len(punch_minutes(map(frappe.utils.get_datetime, old))) if old else 0
		if old_count != _punches(r.employee, r.attendance_date)[2]:
			moved.append(r.name)
	print(f"set-aside punches on the site: {marked}")
	print(f"days read: {len(rows)}   days whose punch count moved: {len(moved)}")
	for name in moved[:50]:
		print("  moved:", name)
	return {"read": len(rows), "moved": len(moved), "set_aside": marked}


if __name__ == "__main__":
	frappe.init(site=sys.argv[1], sites_path=".")
	frappe.connect()
	run(sys.argv[2] if len(sys.argv) > 2 else 60)
