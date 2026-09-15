"""Fixtures for slice 012 (leadership view, push 1).

A synthetic tenant shaped like the spec's Kavya Retail: two companies that share
a branch NAME (ERPNext's Branch has no company), store HR, central HR and
employees. Invented names only.

Figure tests need many attendance rows, so rows are written straight to the
table with `db_insert` - the calculation reads the table, and building 100
submitted records through Frappe HR's validation would be the slowest part of
the suite for no extra proof. Anything a rule or permission reads is saved
through the document instead.

Frappe 16 rolls a test class back at its end, not after each test, so every
helper here makes names unique rather than assuming a clean table.
"""

import frappe
from frappe.utils import now_datetime

from alvoraa_goals.tests.utils import _ensure_erpnext_company_prerequisites, ensure_company, ensure_gender
from alvoraa_portal import branch_scope, data_review
from alvoraa_portal.tests.leave_fixtures import ensure_user

TAG = "S012"
KAVYA = "S012 Kavya Retail"
OTHER = "S012 Other Co"
SHIFT = "S012 Shift 9-18"
DRI = "Alvoraa Data Review Item"

_counter = {"n": 0}


def setup_module_fixtures():
	"""Once per module: the branch column, the indexes, two companies and a shift."""
	branch_scope.after_migrate()
	data_review.add_indexes()
	for company, abbr in ((KAVYA, "S12KR"), (OTHER, "S12OC")):
		if not frappe.db.exists("Company", company):
			ensure_company()
			_ensure_erpnext_company_prerequisites()
			frappe.get_doc({"doctype": "Company", "company_name": company, "abbr": abbr,
			                "default_currency": "INR", "country": "India"}).insert(ignore_permissions=True)
	if not frappe.db.exists("Shift Type", SHIFT):
		frappe.get_doc({"doctype": "Shift Type", "name": SHIFT,
		                "start_time": "09:00:00", "end_time": "18:00:00"}).insert(ignore_permissions=True)
	frappe.db.commit()


def unique(prefix):
	_counter["n"] += 1
	return f"{TAG} {prefix} {frappe.generate_hash(length=6)}{_counter['n']}"


def branch(prefix="Branch"):
	name = unique(prefix)
	frappe.get_doc({"doctype": "Branch", "branch": name}).insert(ignore_permissions=True)
	return name


def user(local, roles):
	email = f"s012.{local.lower()}@example.com"
	ensure_user(email, roles=roles)
	# The site's plan profile would block Alvoraa modules for a new user; these
	# tests are about the slice's own rules, not the plan.
	frappe.db.set_value("User", email, "module_profile", None, update_modified=False)
	frappe.db.delete("Block Module", {"parent": email, "parenttype": "User"})
	frappe.clear_cache(user=email)
	return email


def employee(first, company, branch=None, user_id=None, status="Active", joined="2015-01-01",
             relieving=None, department=None, reports_to=None, shift=SHIFT, gender=None):
	if user_id and (existing := frappe.db.get_value("Employee", {"user_id": user_id}, "name")):
		return existing
	doc = frappe.get_doc({
		"doctype": "Employee", "first_name": first, "last_name": TAG, "company": company,
		"branch": branch, "department": department, "reports_to": reports_to,
		"gender": gender or ensure_gender(), "date_of_birth": "1990-01-01",
		"date_of_joining": joined, "status": "Active", "user_id": user_id,
		"default_shift": shift, "create_user_permission": 0,
	})
	doc.insert(ignore_permissions=True)
	if status != "Active" or relieving:
		frappe.db.set_value("Employee", doc.name, {"status": status, "relieving_date": relieving},
		                    update_modified=False)
	return doc.name


def permission(user_id, allow, value, applicable_for=None):
	if frappe.db.exists("User Permission", {"user": user_id, "allow": allow, "for_value": value}):
		return
	frappe.get_doc({"doctype": "User Permission", "user": user_id, "allow": allow, "for_value": value,
	                "apply_to_all_doctypes": 0 if applicable_for else 1,
	                "applicable_for": applicable_for}).insert(ignore_permissions=True)
	frappe.clear_cache(user=user_id)


def attendance(emp, company, branch, date, status="Present", hours=9.0, shift=SHIFT, late=0,
               docstatus=1):
	doc = frappe.get_doc({
		"doctype": "Attendance", "name": frappe.generate_hash(length=12), "employee": emp,
		"company": company, "attendance_date": date, "status": status,
		"working_hours": hours, "shift": shift, "late_entry": late, "docstatus": docstatus,
		branch_scope.FIELD: branch,
	})
	doc.db_insert()
	return doc.name


def checkin(emp, branch, when):
	frappe.get_doc({
		"doctype": "Employee Checkin", "name": frappe.generate_hash(length=12), "employee": emp,
		"time": when, "log_type": "IN", branch_scope.FIELD: branch,
	}).db_insert()


def allocation(emp, company, branch, from_date, to_date, days, docstatus=1):
	leave_type = frappe.db.get_value("Leave Type", {}, "name")
	frappe.get_doc({
		"doctype": "Leave Allocation", "name": frappe.generate_hash(length=12), "employee": emp,
		"company": company, "leave_type": leave_type, "from_date": from_date, "to_date": to_date,
		"new_leaves_allocated": days, "total_leaves_allocated": days, "docstatus": docstatus,
		branch_scope.FIELD: branch,
	}).db_insert()


def application(emp, company, branch, from_date, days, status="Approved", docstatus=1):
	leave_type = frappe.db.get_value("Leave Type", {}, "name")
	frappe.get_doc({
		"doctype": "Leave Application", "name": frappe.generate_hash(length=12), "employee": emp,
		"company": company, "leave_type": leave_type, "from_date": from_date, "to_date": from_date,
		"total_leave_days": days, "status": status, "docstatus": docstatus,
		"posting_date": from_date, branch_scope.FIELD: branch,
	}).db_insert()


def review_item(company, branch=None, rule="D5", item_type="Doubtful day", check_date=None,
                status="Open", **counts):
	doc = frappe.get_doc({
		"doctype": DRI, "item_type": item_type, "rule": rule, "company": company,
		"alvoraa_branch": branch, "check_date": check_date, "status": "Open",
		"first_found_on": now_datetime(), **counts,
	})
	doc.flags.via_rule_check = True
	doc.insert()
	if status == "Cleared":
		doc.status = "Cleared"
		doc.save()
	elif status == "Confirmed":
		frappe.db.set_value(DRI, doc.name, {"status": "Confirmed", "confirmation": "Absence was real",
		                                    "confirmed_by": "Administrator",
		                                    "confirmed_on": now_datetime()}, update_modified=False)
	return doc.name


class QueryCounter:
	"""Counts every SQL statement the code under test sends."""

	def __init__(self):
		self.count = 0

	def __enter__(self):
		from unittest.mock import patch

		real = frappe.db.sql

		def counting(*args, **kwargs):
			self.count += 1
			return real(*args, **kwargs)

		self._patch = patch.object(frappe.db, "sql", side_effect=counting)
		self._patch.start()
		return self

	def __exit__(self, *exc):
		self._patch.stop()
		return False
