# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""Grooming review pending (slice 066, Y4).

Everyone in the reader's HR scope whose "Grooming review pending" flag is up in
the chosen month, oldest first. One definition: `grooming.pending_reviews`, the
same one the Inbox counts. No rupee column - amounts live in the pay report.
To record a review, HR opens the person's Attendance month.
"""

import frappe
from frappe import _
from frappe.utils import get_first_day, getdate, nowdate

import alvoraa_portal.grooming as grooming


def execute(filters=None):
	filters = frappe._dict(filters or {})
	month = getdate(get_first_day(getdate(filters.get("month") or nowdate())))
	columns = [
		{"fieldname": "employee", "label": _("Employee"), "fieldtype": "Link",
		 "options": "Employee", "width": 120},
		{"fieldname": "employee_name", "label": _("Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "why", "label": _("Why it was raised"), "fieldtype": "Data", "width": 170},
		{"fieldname": "raised_on", "label": _("Raised on"), "fieldtype": "Date", "width": 110},
		{"fieldname": "live", "label": _("Grooming reds this month"), "fieldtype": "Int",
		 "width": 170},
	]
	rows = [{"employee": r.employee, "employee_name": r.employee_name, "why": _why(r),
	         "raised_on": getdate(r.raised_on), "live": r.live}
	        for r in grooming.pending_reviews(frappe.session.user, month)]
	message = None if rows else _("No grooming review is pending.")
	return columns, rows, message


def _why(r):
	"""Why the flag is up, in the words HR acts on (architect review m-1)."""
	if r.why == "raised":
		return _("Raised again by {0}").format(r.raised_by)
	if r.why == "max":
		return _("3 grooming reds, the most allowed")
	return _("Legal limit reached")
