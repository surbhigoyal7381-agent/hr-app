"""The organisation chart: seats where they exist, people where they do not.

Frappe HR already draws a chart from `Employee.reports_to`. It is person-based,
so a vacancy is an absence - nothing renders, and the one thing an executive
opens an org chart to find is the thing it cannot show.

This adds positions on top WITHOUT making them compulsory. A mid-market customer
will not maintain a position register just to see a chart, and a feature that
demands discipline nobody has is a feature that gets switched off. So:

    positions exist  ->  draw seats, with the people in them and the holes
    no positions     ->  draw people, exactly as Frappe HR does today

The fallback is the point. It means this can be switched on for a tenant that has
never heard of a position and nothing changes until they want it to.

Two things are deliberately withheld from the employee portal: vacancy detail and
cost. Where the holes are is a restructuring signal and belongs to HR.
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

FEATURE = "org_structure"


def _enabled():
	"""Whether this tenant bought the position layer.

	Read from the site's own feature list, which a tenant cannot edit. Without
	it the chart still works - it simply draws people.
	"""
	try:
		from alvoraa_portal.subscription import has_feature

		return has_feature(FEATURE)
	except Exception:
		# alvoraa_portal is not installed on this bench. Positions are ours, so
		# treat that as "not bought" rather than failing the whole chart.
		return False


def _may_see_vacancies():
	roles = set(frappe.get_roles())
	return bool({"HR Manager", "HR User", "System Manager"} & roles)


# ── the chart ────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_children(parent=None, company=None, as_at=None):
	"""One level of the chart. Positions if this tenant keeps them, else people.

	`as_at` renders the structure as it stood on a date - which is what makes a
	restructure viewable before it happens and last April viewable after it.
	"""
	as_at = as_at or nowdate()
	if _enabled() and frappe.db.count("Alvoraa Position", {"status": "Active"}):
		return _position_children(parent, company, as_at)
	return _people_children(parent, company)


def _position_children(parent, company, as_at):
	filters = {"status": ("!=", "Closed")}
	if company and company != "All Companies":
		filters["company"] = company
	filters["reports_to_position"] = parent if (parent and parent != company) else ("in", ["", None])

	out = []
	for pos in frappe.get_all("Alvoraa Position", filters=filters,
	                          fields=["name", "position_title", "designation",
	                                  "department", "seats", "status", "lft", "rgt",
	                                  "is_key_position", "effective_from", "effective_to"],
	                          order_by="position_title asc"):
		if not _in_effect(pos, as_at):
			continue
		people = _people_in(pos.name, as_at)
		filled = sum(flt(p["weight"]) for p in people) / 100.0
		node = {
			"id": pos.name,
			"name": pos.position_title,
			"title": pos.designation or pos.department or "",
			"kind": "position",
			"people": people,
			"seats": flt(pos.seats),
			"filled": round(filled, 2),
			"is_key_position": bool(pos.is_key_position),
			"connections": _descendant_count(pos.lft, pos.rgt, company),
		}
		node["expandable"] = bool(node["connections"])
		if _may_see_vacancies():
			# Never stored. A stored count drifts the first time somebody resigns
			# on a Friday, and a chart that calls a filled seat empty is worse
			# than no chart.
			node["vacancy"] = round(max(0.0, flt(pos.seats) - filled), 2)
			node["frozen"] = pos.status == "Frozen"
		out.append(node)
	return out


def _in_effect(pos, as_at):
	if pos.effective_from and str(as_at) < str(pos.effective_from):
		return False
	if pos.effective_to and str(as_at) > str(pos.effective_to):
		return False
	return True


def _people_in(position, as_at):
	"""Who is in this seat on that date, and how much of them.

	The weight is shown, always. It explains why somebody appears twice, and
	hiding it makes the chart look broken rather than discreet.
	"""
	rows = frappe.get_all(
		"Alvoraa Position Assignment",
		filters={"position": position, "from_date": ("<=", as_at)},
		fields=["employee", "employee_name", "weight", "is_primary", "to_date"])
	people = []
	for r in rows:
		if r.to_date and str(r.to_date) < str(as_at):
			continue
		people.append({
			"employee": r.employee,
			"name": r.employee_name,
			"weight": flt(r.weight),
			"is_primary": bool(r.is_primary),
			"image": frappe.db.get_value("Employee", r.employee, "image"),
			# So the chart can mark somebody who also appears elsewhere rather
			# than looking like a duplicate.
			"also_elsewhere": frappe.db.count(
				"Alvoraa Position Assignment",
				{"employee": r.employee, "position": ("!=", position),
				 "to_date": ("is", "not set")}) > 0,
		})
	return sorted(people, key=lambda p: (not p["is_primary"], p["name"] or ""))


def _descendant_count(lft, rgt, company):
	filters = {"lft": (">", lft), "rgt": ("<", rgt), "status": ("!=", "Closed")}
	if company and company != "All Companies":
		filters["company"] = company
	return frappe.db.count("Alvoraa Position", filters)


def _people_children(parent, company):
	"""The person-based fallback: the same shape Frappe HR's own chart returns."""
	filters = [["status", "=", "Active"]]
	if company and company != "All Companies":
		filters.append(["company", "=", company])
	filters.append(["reports_to", "=", parent if (parent and parent != company) else ""])

	out = []
	for emp in frappe.get_all("Employee", filters=filters,
	                          fields=["name as id", "employee_name as name", "lft", "rgt",
	                                  "image", "designation as title"],
	                          order_by="employee_name asc"):
		emp["kind"] = "person"
		emp["connections"] = frappe.db.count(
			"Employee", {"lft": (">", emp.lft), "rgt": ("<", emp.rgt), "status": "Active"})
		emp["expandable"] = bool(emp["connections"])
		out.append(emp)
	return out


# ── dotted lines ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_reporting_lines(as_at=None):
	"""Matrix lines, drawn over the tree. Empty when the layer is not bought."""
	if not _enabled():
		return []
	as_at = as_at or nowdate()
	rows = frappe.get_all("Alvoraa Reporting Line",
	                      fields=["from_position", "to_position", "line_type",
	                              "from_date", "to_date"])
	return [r for r in rows
	        if not (r.from_date and str(as_at) < str(r.from_date))
	        and not (r.to_date and str(as_at) > str(r.to_date))]


# ── the register nobody wants to type ────────────────────────────────────────

@frappe.whitelist()
def propose_positions(company=None):
	"""Draft a position register from the people already there.

	Every employee has a designation, a department and a manager. That is a
	position in all but name. This proposes one position per distinct
	designation-and-department, parented by following the managers' own
	designations, seats set to how many people currently hold it.

	It PROPOSES. Nothing is written. It will be wrong in places - two people with
	the same title in the same department who genuinely do different jobs collapse
	into one seat, and somebody has to split them. But it turns a week of typing
	into an afternoon of correcting, which is the difference between a feature
	that is bought and a feature that is used.
	"""
	frappe.only_for(["HR Manager", "System Manager"])
	filters = {"status": "Active"}
	if company:
		filters["company"] = company

	staff = frappe.get_all("Employee", filters=filters,
	                       fields=["name", "employee_name", "designation", "department",
	                               "company", "grade", "branch", "reports_to"],
	                       limit_page_length=0)

	def key(e):
		return (e.designation or "Unspecified", e.department or "")

	groups = {}
	for e in staff:
		groups.setdefault(key(e), []).append(e)

	by_employee = {e.name: key(e) for e in staff}
	title = lambda k: f"{k[0]} - {k[1]}" if k[1] else k[0]  # noqa: E731

	proposed = []
	for k, members in sorted(groups.items()):
		# The parent is whatever the managers of this group belong to. Where they
		# disagree, the commonest wins and the rest is noted rather than guessed.
		parents = [by_employee.get(m.reports_to) for m in members if m.reports_to]
		parents = [p for p in parents if p and p != k]
		parent = max(set(parents), key=parents.count) if parents else None
		note = ""
		if len(set(parents)) > 1:
			note = (f"managers of these {len(members)} people sit in "
			        f"{len(set(parents))} different positions - check the parent")
		proposed.append({
			"position_title": title(k),
			"reports_to_position": title(parent) if parent else None,
			"designation": k[0] if k[0] != "Unspecified" else None,
			"department": k[1] or None,
			"company": members[0].company,
			"grade": members[0].grade,
			"branch": members[0].branch,
			"seats": len(members),
			"people": [{"employee": m.name, "name": m.employee_name} for m in members],
			"note": note,
		})
	return {"positions": proposed, "employees": len(staff),
	        "roots": len([p for p in proposed if not p["reports_to_position"]])}


@frappe.whitelist()
def create_proposed_positions(positions):
	"""Write a reviewed proposal, and put the people in the seats."""
	frappe.only_for(["HR Manager", "System Manager"])
	positions = frappe.parse_json(positions) if isinstance(positions, str) else positions

	# Parents before children, or the tree link points at nothing yet.
	ordered = sorted(positions, key=lambda p: bool(p.get("reports_to_position")))
	made, assigned = 0, 0
	for row in ordered:
		if frappe.db.exists("Alvoraa Position", row["position_title"]):
			continue
		frappe.get_doc({
			"doctype": "Alvoraa Position",
			"position_title": row["position_title"],
			"reports_to_position": row.get("reports_to_position"),
			"designation": row.get("designation"), "department": row.get("department"),
			"company": row["company"], "grade": row.get("grade"),
			"branch": row.get("branch"), "seats": row.get("seats") or 1,
			"status": "Active",
		}).insert(ignore_permissions=True)
		made += 1

	for row in ordered:
		for person in row.get("people") or []:
			if frappe.db.exists("Alvoraa Position Assignment",
			                    {"employee": person["employee"],
			                     "position": row["position_title"],
			                     "to_date": ("is", "not set")}):
				continue
			frappe.get_doc({
				"doctype": "Alvoraa Position Assignment",
				"employee": person["employee"], "position": row["position_title"],
				"weight": 100, "is_primary": 1, "from_date": nowdate(),
				"reason": "Generated from the existing reporting structure",
			}).insert(ignore_permissions=True)
			assigned += 1

	frappe.db.commit()
	return {"positions_created": made, "people_assigned": assigned}


# ── the report that keeps the two models honest ──────────────────────────────

@frappe.whitelist()
def reporting_mismatches():
	"""Where the position hierarchy and `reports_to` disagree.

	Never reconciled automatically. `reports_to` routes performance reviews, so
	rewriting it from the chart would reassign live appraisals as a side effect of
	somebody tidying up - and nobody would connect the two. A disagreement is
	usually a real problem, and the answer is a person deciding which one is
	wrong.
	"""
	frappe.only_for(["HR Manager", "System Manager"])
	out = []
	for a in frappe.get_all("Alvoraa Position Assignment",
	                        filters={"is_primary": 1, "to_date": ("is", "not set")},
	                        fields=["employee", "employee_name", "position"]):
		parent = frappe.db.get_value("Alvoraa Position", a.position, "reports_to_position")
		if not parent:
			continue
		# Who holds the parent seat?
		holders = frappe.get_all("Alvoraa Position Assignment",
		                         filters={"position": parent, "is_primary": 1,
		                                  "to_date": ("is", "not set")},
		                         pluck="employee")
		says = frappe.db.get_value("Employee", a.employee, "reports_to")
		if holders and says and says not in holders:
			out.append({
				"employee": a.employee, "employee_name": a.employee_name,
				"position": a.position, "parent_position": parent,
				"chart_says": holders[0],
				"chart_says_name": frappe.db.get_value("Employee", holders[0], "employee_name"),
				"reports_to_says": says,
				"reports_to_says_name": frappe.db.get_value("Employee", says, "employee_name"),
			})
	return {"mismatches": out, "count": len(out)}
