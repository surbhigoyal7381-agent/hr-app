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
from frappe.utils import cint, flt, nowdate

from hrms.alvoraa_org_structure import settings

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
			# So the chart marks somebody who also appears elsewhere rather than
			# reading as a duplicate. Anything not yet ended, so a person on
			# temporary cover in another store is marked too.
			"also_elsewhere": bool(_running(
				"Alvoraa Position Assignment",
				{"employee": r.employee, "position": ("!=", position),
				 "from_date": ("<=", as_at)}, ["name"], as_at)),
		})
	return sorted(people, key=lambda p: (not p["is_primary"], p["name"] or ""))


def _running(doctype, filters, fields, on):
	"""Rows in force on a date: started, and not yet ended.

	Cover always carries an end date, so a filter that only accepts an EMPTY one
	silently drops every temporary arrangement.
	"""
	rows = frappe.get_all(doctype, filters=filters, fields=fields + ["to_date"])
	return [r for r in rows if not r.to_date or str(r.to_date) >= str(on)]


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
			                     "to_date": ("is", "not set")}):  # noqa: E501
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
	today = nowdate()
	for a in _running("Alvoraa Position Assignment",
	                  {"is_primary": 1, "from_date": ("<=", today)},
	                  ["employee", "employee_name", "position"], today):
		parent = frappe.db.get_value("Alvoraa Position", a.position, "reports_to_position")
		if not parent:
			continue
		# Who holds the parent seat?
		holders = [h.employee for h in _running(
			"Alvoraa Position Assignment",
			{"position": parent, "is_primary": 1, "from_date": ("<=", today)},
			["employee"], today)]
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


# ── the view an employee actually wants ──────────────────────────────────────

@frappe.whitelist()
def my_view(employee=None, as_at=None):
	"""The chart around one person: their chain up, themselves, their team.

	An employee and an HR manager want different products from the same data.
	HR wants the whole tree. An employee wants four things, and none of them is
	"the whole company": where am I, who is my manager, who else is on my team,
	and who do I talk to in Finance.

	Most org charts on a portal fail by giving the employee the HR view - four
	hundred boxes to pan around looking for themselves. So this returns three
	levels and a breadcrumb, and nothing else. Everything past that is a click.

	Works with or without positions. Without them it walks `reports_to`, which
	is what Frappe HR has always drawn.
	"""
	as_at = as_at or nowdate()
	employee = employee or frappe.db.get_value(
		"Employee", {"user_id": frappe.session.user}, "name")
	if not employee:
		return {"me": None, "reason": "no employee record for this login"}

	if _enabled() and frappe.db.count("Alvoraa Position", {"status": "Active"}):
		return _my_view_by_position(employee, as_at)
	return _my_view_by_person(employee)


def _card(employee):
	e = frappe.db.get_value(
		"Employee", employee,
		["name", "employee_name", "designation", "department", "branch", "image"],
		as_dict=True)
	if not e:
		return None
	return {"employee": e.name, "name": e.employee_name, "title": e.designation or "",
	        "department": e.department or "", "branch": e.branch or "", "image": e.image}


def _my_view_by_position(employee, as_at):
	mine = _running("Alvoraa Position Assignment",
	                {"employee": employee, "from_date": ("<=", as_at)},
	                ["position", "weight", "is_primary", "assignment_type"], as_at)
	if not mine:
		return _my_view_by_person(employee)

	primary = next((r for r in mine if r.is_primary), mine[0])
	seat = frappe.db.get_value("Alvoraa Position", primary.position,
	                           ["name", "position_title", "reports_to_position"],
	                           as_dict=True)

	me = _card(employee)
	me["seats"] = [{"position": r.position, "weight": flt(r.weight),
	                "is_primary": bool(r.is_primary),
	                "cover": (r.assignment_type or "Permanent") != "Permanent"}
	               for r in mine]

	# Up: the chain to the top, so the shape is legible without drawing it.
	chain, at, guard = [], seat.reports_to_position, 0
	while at and guard < 20:
		guard += 1
		node = frappe.db.get_value("Alvoraa Position", at,
		                           ["name", "position_title", "reports_to_position"],
		                           as_dict=True)
		if not node:
			break
		chain.append({"position": node.name, "title": node.position_title,
		              "people": [_card(h.employee) for h in _holders_of(node.name, as_at)]})
		at = node.reports_to_position
	chain.reverse()

	return {
		"mode": "position",
		"me": me,
		"my_position": {"position": seat.name, "title": seat.position_title},
		"breadcrumb": chain,
		"manager": chain[-1] if chain else None,
		"peers": [_card(h.employee) for h in _holders_of(seat.name, as_at)
		          if h.employee != employee],
		"team": _team_under(seat.name, as_at),
		"dotted": _dotted_for(seat.name, as_at),
	}


def _holders_of(position, as_at):
	return _running("Alvoraa Position Assignment",
	                {"position": position, "from_date": ("<=", as_at)},
	                ["employee", "weight", "assignment_type"], as_at)


def _team_under(position, as_at):
	"""One level down, with empty seats shown as empty.

	A person looking at their own team should see the vacancy they are covering
	for - that is not a restructuring signal, it is why they are busy.
	"""
	out = []
	for child in frappe.get_all("Alvoraa Position",
	                            filters={"reports_to_position": position,
	                                     "status": ("!=", "Closed")},
	                            fields=["name", "position_title", "seats"],
	                            order_by="position_title asc"):
		people = _holders_of(child.name, as_at)
		out.append({
			"position": child.name, "title": child.position_title,
			"people": [{**_card(p.employee), "weight": flt(p.weight),
			            "cover": (p.assignment_type or "Permanent") != "Permanent"}
			           for p in people],
			"open": max(0.0, flt(child.seats)
			            - sum(flt(p.weight) for p in people) / 100.0),
		})
	return out


def _dotted_for(position, as_at):
	"""Shown as a line on the card - "also works with" - not as a crossing line.
	Five crossing lines turn a chart into spaghetti."""
	out = []
	for line in get_reporting_lines(as_at):
		if line["from_position"] != position:
			continue
		for h in _holders_of(line["to_position"], as_at):
			card = _card(h.employee)
			if card:
				out.append({**card, "line_type": line["line_type"]})
	return out


def _my_view_by_person(employee):
	"""The fallback, for the great majority of tenants who keep no positions."""
	me = _card(employee)
	chain, at, guard = [], frappe.db.get_value("Employee", employee, "reports_to"), 0
	while at and guard < 20:
		guard += 1
		chain.append({"position": None, "title": None, "people": [_card(at)]})
		at = frappe.db.get_value("Employee", at, "reports_to")
	chain.reverse()

	boss = frappe.db.get_value("Employee", employee, "reports_to")
	return {
		"mode": "person",
		"me": me,
		"my_position": None,
		"breadcrumb": chain,
		"manager": chain[-1] if chain else None,
		"peers": [_card(e) for e in frappe.get_all(
			"Employee", filters={"reports_to": boss, "status": "Active",
			                     "name": ("!=", employee)}, pluck="name")] if boss else [],
		"team": [{"position": None, "title": None, "open": 0,
		          "people": [_card(e)]} for e in frappe.get_all(
			"Employee", filters={"reports_to": employee, "status": "Active"},
			pluck="name")],
		"dotted": [],
	}


@frappe.whitelist()
def search_people(q, limit=12):
	"""Type a name, land on their card. That is how an org chart is actually
	used - somebody is looking for one person, not browsing a company."""
	q = (q or "").strip()
	if len(q) < 2:
		return []
	return frappe.get_all(
		"Employee",
		filters={"status": "Active", "employee_name": ("like", f"%{q}%")},
		fields=["name as employee", "employee_name as name", "designation as title",
		        "department", "image"],
		order_by="employee_name asc", limit=int(limit))


# ── the expandable tree ──────────────────────────────────────────────────────

# Two levels at a time. One at a time makes somebody click through a company
# node by node; three fills the screen with people they were not looking for and
# pushes what they wanted off the bottom.
DEFAULT_DEPTH = 2


def reach():
	"""How far this person may see, and whether they may roam.

	An ordinary employee gets a window around their own seat - two levels up and
	two down by default. That answers the questions they actually have without
	handing everybody a map of the whole company: structure is commercially
	sensitive, and a full org chart is the first thing that walks out of the door
	with a leaver.

	HR and leadership roam freely because they cannot do their jobs otherwise,
	and so does anybody with people reporting to them - a manager who cannot see
	past their own team cannot plan around the one next door.

	Enforced HERE rather than in the page. A limit that lives in JavaScript is a
	suggestion: the endpoint is whitelisted, and anybody who can open the portal
	can call it with any root they like.
	"""
	roles = set(frappe.get_roles())
	allowed = {r.strip() for r in
	           str(settings.get("alvoraa_org_full_reach_roles") or "").split(",")
	           if r.strip()}
	if roles & allowed:
		return {"unlimited": True, "why": "role"}

	if settings.get("alvoraa_org_managers_see_all") and _has_people_under_them():
		return {"unlimited": True, "why": "manager"}

	return {"unlimited": False,
	        "up": int(settings.get("alvoraa_org_reach_up")),
	        "down": int(settings.get("alvoraa_org_reach_down"))}


def _has_people_under_them():
	"""Does this person manage anybody?

	Asked once per box while the tree renders, and the answer cannot change
	inside one request - so it is worked out once. Without this a thirty-box
	chart was thirty round trips for the same answer.

	Kept apart from reach() itself, which still reads its settings live: caching
	the whole verdict would mean a setting changed mid-request stopped taking
	effect, and a test that changes one and re-asks would pass against a stale
	answer.
	"""
	cache = getattr(frappe.local, "_alvoraa_leads", None)
	if cache is None:
		cache = frappe.local._alvoraa_leads = {}
	user = frappe.session.user
	if user not in cache:
		me = _me()
		cache[user] = bool(me and (
			frappe.db.count("Employee", {"reports_to": me, "status": "Active"})
			or _leads_a_position(me)))
	return cache[user]


def _leads_a_position(employee):
	"""A manager by structure rather than by `reports_to` - somebody whose seat
	has seats under it, even when nobody has been pointed at them yet."""
	seat = _my_position_of(employee, nowdate())
	if not seat:
		return False
	return bool(frappe.db.count("Alvoraa Position", {"reports_to_position": seat}))


def _my_position_of(employee, as_at):
	mine = _running("Alvoraa Position Assignment",
	                {"employee": employee, "from_date": ("<=", as_at)},
	                ["position", "is_primary"], as_at)
	if not mine:
		return None
	return next((r.position for r in mine if r.is_primary), mine[0].position)


def _within_reach(root, as_at):
	"""Is this node inside the window the viewer is allowed to see?

	Walks up from the requested node looking for the viewer's own seat within
	`up` steps, and up from the viewer looking for the node within `down`. One
	of the two has to hold, or they are asking about a part of the company that
	is not theirs.
	"""
	r = reach()
	if r["unlimited"]:
		return True

	positions = _enabled() and frappe.db.count("Alvoraa Position", {"status": "Active"})
	mine = _my_position_of(_me(), as_at) if positions else _me()
	if not mine or not root:
		return True                        # nothing to compare; the default view
	if root == mine:
		return True

	def up_from(node, steps):
		# Not `for _ in` - that would shadow frappe's translation function `_`
		# inside this scope, and the next person to add a message in here would
		# get a baffling TypeError instead of a translated string.
		seen, at = [], node
		for _step in range(steps):
			at = (frappe.db.get_value("Alvoraa Position", at, "reports_to_position")
			      if positions
			      else frappe.db.get_value("Employee", at, "reports_to"))
			if not at:
				break
			seen.append(at)
		return seen

	# Above me, up to `up` steps: my manager, my manager's manager.
	if root in up_from(mine, r["up"]):
		return True
	# Below me, up to `down` steps: walking up from the node should reach me.
	if mine in up_from(root, r["down"]):
		return True
	return False


@frappe.whitelist()
def subtree(root=None, depth=None, as_at=None, kind=None):
	"""A node and the levels beneath it, ready to render.

	Expansion rather than re-centring. Clicking a box opens what is under it in
	place, so the reader keeps the context they built - re-centring throws away
	the path they took to get there, which is the thing they were using to
	understand the shape.

	`root` is an employee when the tenant keeps no positions, and a position
	when it does. `kind` says which, and is returned so the caller does not have
	to guess on the way back in.
	"""
	as_at = as_at or nowdate()
	depth = int(depth or DEFAULT_DEPTH)

	# Refused rather than quietly returned empty. An employee who asks about a
	# part of the company that is not theirs should be told so, not left staring
	# at a blank box wondering whether it is broken.
	if root and not _within_reach(root, as_at):
		frappe.throw(
			_("That part of the organisation is outside what you can see. You can "
			  "look two levels above and below your own role."),
			frappe.PermissionError)

	r = reach()
	if not r["unlimited"]:
		depth = min(depth, r["down"] + 1)

	positions = _enabled() and frappe.db.count("Alvoraa Position", {"status": "Active"})

	if positions:
		root = root or _my_position(as_at)
		if not root:
			return _person_subtree(_me(), depth, as_at)
		return _position_subtree(root, depth, as_at)
	return _person_subtree(root or _me(), depth, as_at)


def _me():
	return frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")


def _my_position(as_at):
	mine = _running("Alvoraa Position Assignment",
	                {"employee": _me(), "from_date": ("<=", as_at)},
	                ["position", "is_primary"], as_at)
	if not mine:
		return None
	return next((r.position for r in mine if r.is_primary), mine[0].position)


def _position_subtree(position, depth, as_at):
	pos = frappe.db.get_value(
		"Alvoraa Position", position,
		["name", "position_title", "designation", "department", "seats", "status",
		 "is_key_position"],
		as_dict=True)
	if not pos:
		return None

	people = _holders_of(pos.name, as_at)
	filled = sum(flt(p.weight) for p in people) / 100.0
	kids = frappe.get_all("Alvoraa Position",
	                      filters={"reports_to_position": pos.name,
	                               "status": ("!=", "Closed")},
	                      pluck="name", order_by="position_title asc")

	node = {
		"kind": "position",
		"id": pos.name,
		"title": pos.position_title,
		"subtitle": pos.designation or pos.department or "",
		# What is wrong with this box, if anything. Worked out here so the chart
		# and the health dashboard cannot drift apart and disagree about which
		# seats are in trouble.
		"flags": _node_flags(pos, people, filled, len(kids)),
		"people": [{**_card(p.employee), "weight": flt(p.weight),
		            "cover": (p.assignment_type or "Permanent") != "Permanent"}
		           for p in people],
		"seats": flt(pos.seats),
		"open": max(0.0, flt(pos.seats) - filled),
		"frozen": pos.status == "Frozen",
		# How many are underneath, so a collapsed box can say what it is hiding
		# rather than just offering a chevron.
		"child_count": len(kids),
		"children": [],
		# The caller needs to know whether there is more, even when it stopped
		# fetching. Without this the last row looks like the bottom of the tree.
		"has_more": bool(kids) and depth <= 1,
	}
	if kids and depth > 1:
		node["children"] = [c for c in
		                    (_position_subtree(k, depth - 1, as_at) for k in kids) if c]
	return node


SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}


def _node_flags(pos, people, filled, child_count):
	"""Why this box is tinted.

	Two audiences with different rights. Anybody may see that a seat next to
	them is open or being covered - that is not a secret, it is why everybody
	there is busy. The rest is register hygiene and headcount planning, and it
	is HR's business, so it is only attached for somebody who may already see
	the whole chart.

	Each flag carries its own words. A coloured box with no explanation gets
	ignored by the second week.
	"""
	flags = []
	open_seats = flt(pos.seats) - filled

	if pos.status == "Frozen":
		flags.append({"code": "frozen", "severity": "low", "label": "Frozen",
		              "why": "No hiring into this seat at the moment."})
	elif open_seats >= 0.5:
		key = bool(pos.get("is_key_position"))
		flags.append({
			"code": "key_vacant" if key else "vacant",
			"severity": "high" if key else "medium",
			"label": "Key seat empty" if key else "Vacant",
			"why": ("A seat somebody marked critical has nobody permanently in it."
			        if key else "Budgeted and nobody permanently in it.")})

	if any((p.assignment_type or "Permanent") != "Permanent" for p in people):
		flags.append({"code": "covered", "severity": "low", "label": "Covered",
		              "why": "Somebody is standing in temporarily."})

	if not _can_see_health():
		return flags

	if flt(pos.seats) and filled > flt(pos.seats) + 0.01:
		flags.append({"code": "over_filled", "severity": "high",
		              "label": "More people than seats",
		              "why": "Headcount and cost from this seat down are wrong."})

	wide = cint(settings.get("alvoraa_org_span_wide"))
	narrow = cint(settings.get("alvoraa_org_span_narrow"))
	if wide and child_count >= wide:
		flags.append({"code": "span_wide", "severity": "medium",
		              "label": f"{child_count} direct reports",
		              "why": "Too many to manage properly. Usually a missing layer."})
	elif narrow and child_count == narrow:
		flags.append({"code": "span_narrow", "severity": "low",
		              "label": "A layer of one",
		              "why": "One person managing one person. Often a title, not a job."})

	return flags


def _can_see_health():
	"""Register-hygiene flags are for the people who can act on them."""
	try:
		return bool(reach().get("unlimited"))
	except Exception:
		return False


def _person_flags(child_count):
	"""Without positions there are no seats to be empty, so span of control is
	the only thing left worth colouring."""
	if not _can_see_health():
		return []
	wide = cint(settings.get("alvoraa_org_span_wide"))
	narrow = cint(settings.get("alvoraa_org_span_narrow"))
	if wide and child_count >= wide:
		return [{"code": "span_wide", "severity": "medium",
		         "label": f"{child_count} direct reports",
		         "why": "Too many to manage properly. Usually a missing layer."}]
	if narrow and child_count == narrow:
		return [{"code": "span_narrow", "severity": "low", "label": "A layer of one",
		         "why": "One person managing one person. Often a title, not a job."}]
	return []


def _person_subtree(employee, depth, as_at):
	card = _card(employee)
	if not card:
		return None
	kids = frappe.get_all("Employee",
	                      filters={"reports_to": employee, "status": "Active"},
	                      pluck="name", order_by="employee_name asc")
	node = {
		"kind": "person",
		"id": employee,
		"title": card["name"],
		"subtitle": card["title"],
		"people": [card],
		"seats": 1, "open": 0, "frozen": False,
		"flags": _person_flags(len(kids)),
		"child_count": len(kids),
		"children": [],
		"has_more": bool(kids) and depth <= 1,
	}
	if kids and depth > 1:
		node["children"] = [c for c in
		                    (_person_subtree(k, depth - 1, as_at) for k in kids) if c]
	return node


@frappe.whitelist()
def chain_to_top(node=None, as_at=None):
	"""The breadcrumb: every step from the top down to this node.

	Separate from the subtree because it changes only when the reader moves, and
	fetching it again on every expansion would be a query per click for something
	that did not change.
	"""
	as_at = as_at or nowdate()
	positions = _enabled() and frappe.db.count("Alvoraa Position", {"status": "Active"})
	chain, guard = [], 0

	if positions:
		at = node or _my_position(as_at)
		while at and guard < 30:
			guard += 1
			p = frappe.db.get_value("Alvoraa Position", at,
			                        ["name", "position_title", "reports_to_position"],
			                        as_dict=True)
			if not p:
				break
			holders = _holders_of(p.name, as_at)
			chain.append({"id": p.name, "title": p.position_title,
			              "who": (_card(holders[0].employee) or {}).get("name")
			              if holders else None})
			at = p.reports_to_position
	else:
		at = node or _me()
		while at and guard < 30:
			guard += 1
			c = _card(at)
			if not c:
				break
			chain.append({"id": at, "title": c["name"], "who": c["name"]})
			at = frappe.db.get_value("Employee", at, "reports_to")

	chain.reverse()
	r = reach()
	if not r["unlimited"] and len(chain) > r["up"] + 1:
		# Only as far up as they may see. A breadcrumb that names the chief
		# executive to everybody is the org chart leaking one row at a time.
		chain = chain[-(r["up"] + 1):]
	return chain
