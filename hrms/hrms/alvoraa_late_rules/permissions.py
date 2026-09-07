# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""Row-level scope for Attendance Deduction: HR sees everything, a manager sees
their reporting line, an employee sees their own."""

import frappe

HR_ROLES = {"HR Manager", "HR User", "System Manager", "Administrator"}


def _employee_of(user):
	return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")


def _reporting_line(employee):
	lft, rgt = frappe.db.get_value("Employee", employee, ["lft", "rgt"]) or (None, None)
	if not lft:
		return []
	return frappe.get_all("Employee", filters={"lft": [">", lft], "rgt": ["<", rgt]}, pluck="name")


def attendance_deduction_query(user=None):
	user = user or frappe.session.user
	if HR_ROLES & set(frappe.get_roles(user)):
		return ""
	me = _employee_of(user)
	if not me:
		return "1=0"
	names = [me] + _reporting_line(me)
	quoted = ", ".join(frappe.db.escape(n) for n in names)
	return f"`tabAttendance Deduction`.employee in ({quoted})"


def has_attendance_deduction_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if HR_ROLES & set(frappe.get_roles(user)):
		return True
	if ptype not in (None, "read", "print", "email", "report"):
		return False
	me = _employee_of(user)
	if not me:
		return False
	return doc.employee == me or doc.employee in _reporting_line(me)
