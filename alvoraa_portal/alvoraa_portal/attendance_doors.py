"""Doors that nobody may open on their own attendance (slice 085, ALV-392).

Attendance decides pay. A person who looks after attendance must not be able to
confirm, cancel, amend, delete or hand-make their OWN day, and must not decide a
correction they raised themselves. The rule is the one `refuse_own_decision`
already draws for requests (SEC-9): no role is exempt.

Each function below is one door, wired in hooks.py as a `doc_events` entry, so
the Desk, the REST API and an import all meet the same refusal. One function
per door; no shared framework.
"""

import frappe
from frappe import _

from hrms.alvoraa_hr_core.access import refuse, refuse_own_decision


def refuse_own_attendance_change(doc, method=None):
	"""before_update_after_submit, before_cancel and on_trash on Attendance."""
	refuse_own_decision(doc.get("employee"), doc.doctype, doc.name,
	                    endpoint=f"Attendance {method or 'change'}")


def refuse_own_attendance_new(doc, method=None):
	"""validate on Attendance: only a new row, so a later save by the system is untouched."""
	if doc.is_new():
		refuse_own_decision(doc.get("employee"), doc.doctype, doc.name,
		                    endpoint="Attendance insert")


def refuse_raiser_submit(doc, method=None):
	"""before_submit on Attendance Request: whoever raised it does not decide it (SEC-3).

	Submitting IS approving. The raiser is the document's owner, the same test
	`attendance_correction.not_yours_yet` uses to draw the sentence on the
	screen. Administrator is exempt: it holds no Employee record, so it cannot
	be anybody's colleague, and `refuse_own_decision` already cannot bite it.
	A named System Manager who raised the request is refused.
	"""
	user = frappe.session.user
	if user != "Administrator" and doc.get("owner") == user:
		refuse(_("You raised this request, so someone else decides it."), "SEC-3",
		       "Attendance Request submit", doc.doctype, doc.name)


def refuse_outside_company(doc, method=None):
	"""before_submit on Attendance and Attendance Request (R5). Submitting is
	approving, and the Desk, REST and imports reach it without the portal's own
	scope check, so an HR login approves only for the companies it may act for.
	The employee's company is read from the Employee record, never from a field
	on the document. A manager's submit is governed by their User Permissions as
	before (they hold no HR role); Administrator and the scheduler are exempt.
	A System Manager is every company, through `permitted_companies`."""
	from hrms.alvoraa_hr_core.access import permitted_companies

	user = frappe.session.user
	if user == "Administrator" or not doc.get("employee"):
		return
	if not {"HR Manager", "HR User", "System Manager"} & set(frappe.get_roles(user)):
		return
	company = frappe.get_cached_value("Employee", doc.employee, "company")
	if company not in permitted_companies(user):
		refuse(_("This person works for a company you do not look after, so you cannot approve "
		         "this. Ask the HR Manager of that company."), "R5",
		       f"{doc.doctype} submit", doc.doctype, doc.name)
