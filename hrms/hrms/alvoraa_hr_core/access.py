"""Two access rules that the portal, goals and org-chart code all need.

Kept in one place so they cannot drift apart:

  refuse_own_decision(employee)  nobody approves or declines their own request
  permitted_companies(user)      which companies an HR user acts for

It lives in hrms because every one of our apps can import hrms, and hrms must
not import them.

Refusals are written to the "security" log as one JSON line: who, which
endpoint, which document, which rule. Never a field value, a name or a reason.
"""

import json

import frappe
from frappe import _

HR_ROLES = frozenset({"HR Manager", "HR User"})


def log_refusal(rule, endpoint, doctype=None, name=None):
	"""One structured line per refusal, so misuse can be found later (SEC-17).

	Document names and user ids only. Logging must never stop the refusal itself.
	"""
	try:
		frappe.logger("security").warning(
			json.dumps(
				{
					"event": "refused",
					"at": str(frappe.utils.now_datetime()),
					"user": frappe.session.user,
					"endpoint": endpoint,
					"doctype": doctype,
					"name": name,
					"rule": rule,
				}
			)
		)
	except Exception:
		pass


def refuse(message, rule, endpoint, doctype=None, name=None):
	log_refusal(rule, endpoint, doctype, name)
	frappe.throw(message, frappe.PermissionError)


def is_own_record(employee, user=None):
	"""Is this employee record the caller's own login?"""
	if not employee:
		return False
	user = user or frappe.session.user
	return frappe.db.get_value("Employee", employee, "user_id") == user


def refuse_own_decision(employee, doctype=None, name=None, endpoint=None):
	"""Stop anyone deciding a request that is about themselves (SEC-9).

	No role is exempt. An HR Manager, owner or System Manager who raised a
	request must have someone else approve it.
	"""
	if is_own_record(employee):
		refuse(
			_("You cannot decide your own request. Someone else must approve it."),
			"SEC-9",
			endpoint,
			doctype,
			name,
		)


def refuse_own_submit(doc, method=None):
	"""doc_events before_submit: the desk, REST and imports get the same rule.

	Submitting a Leave Application or an Attendance Request is what approves it,
	so a submit by the person the document is about is a self-approval.
	"""
	refuse_own_decision(doc.get("employee"), doc.doctype, doc.name, endpoint=f"{doc.doctype} submit")


def permitted_companies(user=None):
	"""Companies this user may act for as HR. Fails closed.

	- System Manager (treated as CXO for now) and Administrator: every company.
	- HR Manager / HR User: the companies in their User Permissions on Company;
	  with none, the company on their own active Employee record; with neither,
	  nothing.
	- Anyone else: nothing.
	"""
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if user == "Administrator" or "System Manager" in roles:
		return frappe.get_all("Company", pluck="name", order_by="name asc")
	if not HR_ROLES & roles:
		return []

	from frappe.core.doctype.user_permission.user_permission import get_user_permissions

	companies = sorted({d.get("doc") for d in get_user_permissions(user).get("Company", []) if d.get("doc")})
	if companies:
		return companies
	own = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "company")
	return [own] if own else []
