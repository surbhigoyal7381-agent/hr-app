"""Dotted-line managers, and their part in an appraisal.

A Chandigarh accountant sits under the Store In-charge on the chart - that is who
they work beside every day. For professional matters they answer to the Finance
Controller in head office. Both are real. Only one of them is on the solid line.

Today the appraisal hears from the solid-line manager alone, which means the
person who actually judges half of somebody's work has no say in their rating.
This makes the dotted-line manager a required contributor.

**After the manager has prepared, not instead of.** The order matters. The
solid-line manager rates first, on their own view; the dotted-line manager is
then asked, seeing that the appraisal exists but writing their own feedback. Ask
them both at once and the second one anchors on the first. Ask only the second
and the line manager is undermined.

The appraisal cannot be submitted until every dotted-line manager has answered.
Not a reminder - a block. A reminder is what makes this optional in practice, and
an optional second opinion is one that never arrives in a busy quarter.
"""

import frappe
from frappe import _
from frappe.utils import nowdate

FEATURE = "org_structure"


def _enabled():
	try:
		from alvoraa_portal.subscription import has_feature

		return has_feature(FEATURE)
	except Exception:
		return False


def _still_running(rows, as_at):
	"""Not yet ended, rather than never ending.

	Cover ALWAYS has an end date, so filtering on an empty one dropped every
	temporary arrangement - an acting manager filled nothing and the seat they
	were covering read as completely vacant.
	"""
	return [r for r in rows if not r.to_date or str(r.to_date) >= str(as_at)]


def _current_positions(employee, as_at):
	rows = frappe.get_all(
		"Alvoraa Position Assignment",
		filters={"employee": employee, "assignment_type": "Permanent",
		         "from_date": ("<=", as_at)},
		fields=["position", "to_date"])
	return [r.position for r in _still_running(rows, as_at)]


def _holders(position, as_at):
	"""Who permanently sits in a position now.

	Permanent only, deliberately: somebody standing in for a fortnight should not
	be pulled into an appraisal about a quarter they did not watch.
	"""
	rows = frappe.get_all(
		"Alvoraa Position Assignment",
		filters={"position": position, "assignment_type": "Permanent",
		         "from_date": ("<=", as_at)},
		fields=["employee", "employee_name", "to_date"])
	return _still_running(rows, as_at)


def dotted_line_managers(employee, as_at=None):
	"""Who has a dotted line to this person, as employees.

	Walks: the person's current positions -> the reporting lines out of them ->
	the people sitting in the positions those lines point at.

	Cover is excluded deliberately. Somebody standing in for a fortnight should
	not be pulled into an appraisal about a whole quarter they did not watch.
	"""
	if not _enabled():
		return []
	as_at = as_at or nowdate()

	positions = _current_positions(employee, as_at)
	if not positions:
		return []

	targets = []
	for line in frappe.get_all("Alvoraa Reporting Line",
	                           filters={"from_position": ("in", positions)},
	                           fields=["to_position", "line_type", "from_date", "to_date"]):
		if line.from_date and str(as_at) < str(line.from_date):
			continue
		if line.to_date and str(as_at) > str(line.to_date):
			continue
		targets.append(line)

	out = []
	seen = set()
	for line in targets:
		for holder in _holders(line.to_position, as_at):
			# Somebody who is their own dotted-line manager helps nobody, and it
			# happens the moment a person holds two linked positions.
			if holder.employee == employee or holder.employee in seen:
				continue
			seen.add(holder.employee)
			out.append({"employee": holder.employee, "name": holder.employee_name,
			            "position": line.to_position, "line_type": line.line_type})
	return out


# ── the appraisal ────────────────────────────────────────────────────────────

def request_dotted_line_feedback(doc, method=None):
	"""When the manager has prepared, ask the dotted-line managers.

	Called on Appraisal update. "Prepared" means the manager has put a score on
	it - there is no separate state for it in Frappe HR, and inventing one would
	mean a migration for something the score already tells us.
	"""
	if not _enabled() or not doc.get("total_score"):
		return

	for boss in dotted_line_managers(doc.employee):
		if frappe.db.exists("Employee Performance Feedback",
		                    {"appraisal": doc.name, "reviewer": boss["employee"],
		                     "docstatus": ("<", 2)}):
			continue
		frappe.get_doc({
			"doctype": "Employee Performance Feedback",
			"employee": doc.employee,
			"appraisal": doc.name,
			"appraisal_cycle": doc.appraisal_cycle,
			"reviewer": boss["employee"],
			"user": frappe.db.get_value("Employee", boss["employee"], "user_id"),
			"added_on": nowdate(),
			"feedback": "",
		}).insert(ignore_permissions=True)


def require_dotted_line_feedback(doc, method=None):
	"""Refuse to submit an appraisal the dotted-line manager has not answered.

	A block, not a reminder. A reminder is what makes a second opinion optional
	in practice, and an optional second opinion never arrives in a busy quarter -
	which leaves somebody rated by a manager who saw half their work.
	"""
	if not _enabled():
		return

	missing = []
	for boss in dotted_line_managers(doc.employee):
		given = frappe.db.exists(
			"Employee Performance Feedback",
			{"appraisal": doc.name, "reviewer": boss["employee"], "docstatus": 1})
		if not given:
			missing.append(f"{boss['name']} ({boss['line_type'].lower()} line)")

	if missing:
		frappe.throw(
			_("This appraisal still needs feedback from {0}. They manage part of "
			  "this person's work on a dotted line, so their view is part of the "
			  "rating rather than an optional extra.").format(", ".join(missing)),
			title=_("Waiting on the dotted-line manager"))


@frappe.whitelist()
def pending_dotted_line_feedback(appraisal_cycle=None):
	"""Every appraisal waiting on a dotted-line manager, and who it waits on.

	The thing somebody looks at on the last Friday of a cycle to find out why
	forty appraisals will not close.
	"""
	frappe.only_for(["HR Manager", "HR User", "System Manager"])
	filters = {"docstatus": 0}
	if appraisal_cycle:
		filters["appraisal_cycle"] = appraisal_cycle

	out = []
	for app in frappe.get_all("Appraisal", filters=filters,
	                          fields=["name", "employee", "employee_name",
	                                  "appraisal_cycle", "total_score"]):
		waiting = []
		for boss in dotted_line_managers(app.employee):
			if not frappe.db.exists("Employee Performance Feedback",
			                        {"appraisal": app.name,
			                         "reviewer": boss["employee"], "docstatus": 1}):
				waiting.append(boss)
		if waiting:
			out.append({
				"appraisal": app.name, "employee": app.employee,
				"employee_name": app.employee_name, "cycle": app.appraisal_cycle,
				# So the list separates "the manager has not started" from "the
				# manager is done and the dotted line is holding it up".
				"manager_has_prepared": bool(app.total_score),
				"waiting_on": waiting,
			})
	return {"appraisals": out, "count": len(out)}
