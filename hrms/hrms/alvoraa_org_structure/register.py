"""The position register, as a list somebody can actually work with.

The chart answers "what does this company look like". This answers "what seats
do we have, which are empty, and what do I need to change" - and that is a
table, not a tree. Eighty-nine seats across six stores sort and scan in a list;
in a tree you hunt.

It is also where seats are created and re-parented, because that is awkward on
a chart and obvious in a row.

WHO MAY CHANGE IT IS A SETTING, not a hard-coded role. At the first customer the
owners maintain the structure themselves and HR does not; at the next it will be
the other way round. `alvoraa_org_position_editor_roles` decides, and like the
other keys that hand out privilege it can only be changed by a System Manager,
and leaves a record when it is.

READING IS SCOPED THE SAME WAY AS EVERY OTHER HR READER (slice 030): the
companies somebody may act for, and their branches if they are tied to a store.
A branch head reads their own store and changes nothing unless the setting says
they may.
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from hrms.alvoraa_org_structure import settings

EDITOR_ROLES_KEY = "alvoraa_org_position_editor_roles"


def _scope():
	"""The companies and branches this reader may act for.

	Returns (companies, branches). `branches` is None for somebody who is not
	tied to a store, which means "every branch" rather than "no branch".
	"""
	from hrms.alvoraa_hr_core.access import permitted_branches, permitted_companies

	return permitted_companies(), permitted_branches()


def _may_read():
	"""Anybody who may see the whole chart, and any manager, may read the list.

	Deliberately wider than who may change it. A branch head planning next
	month's cover needs to see the empty seats in their store; letting them
	change the company's structure is a different decision.
	"""
	from hrms.alvoraa_org_structure.api import reach

	return bool(reach().get("unlimited"))


def may_edit():
	"""Whether this person may create or change a seat.

	Read from a setting rather than fixed in code, because who owns the shape of
	the organisation differs by customer. At DTC it is the owners; elsewhere it
	will be HR.
	"""
	allowed = {r.strip() for r in str(settings.get(EDITOR_ROLES_KEY)).split(",") if r.strip()}
	return bool(allowed & set(frappe.get_roles()))


def _refuse(endpoint, name=None):
	from hrms.alvoraa_hr_core.access import refuse

	refuse(
		_("You can look at the position list, but changing it is not yours to do. "
		  "Ask whoever maintains the structure in your organisation."),
		"SEC-8", endpoint, "Alvoraa Position", name)


@frappe.whitelist()
def position_table(branch=None, department=None, as_at=None):
	"""Every seat this person may see, with how full it is.

	One query for the seats, one for the people in them. Not one per row: at
	eighty-nine seats that is eighty-nine round trips for a table that renders
	in a single screen.
	"""
	if not _may_read():
		_refuse("register.position_table")
	as_at = as_at or nowdate()
	companies, branches = _scope()

	filters = {"status": ("!=", "Closed"), "company": ("in", companies)}
	if branches is not None:
		# A seat with no branch is outside every store (DEF-6), the same rule
		# every other reader follows.
		filters["branch"] = ("in", branches)
	if branch:
		asked = branch if isinstance(branch, list) else [branch]
		if branches is not None:
			asked = [b for b in asked if b in branches]
		filters["branch"] = ("in", asked)
	if department:
		filters["department"] = department

	seats = frappe.get_all(
		"Alvoraa Position", filters=filters,
		fields=["name", "position_title", "status", "is_key_position", "seats",
		        "reports_to_position", "branch", "department", "designation",
		        "grade", "company", "effective_from", "effective_to"],
		order_by="branch asc, department asc, position_title asc",
		limit_page_length=0)
	if not seats:
		return {"rows": [], "may_edit": may_edit(), "as_at": as_at}

	names = [s.name for s in seats]
	filled, people = {}, {}
	for a in frappe.get_all(
			"Alvoraa Position Assignment",
			filters={"position": ("in", names), "from_date": ("<=", as_at)},
			fields=["name", "position", "employee", "employee_name", "weight",
			        "assignment_type", "to_date"],
			limit_page_length=0):
		if a.to_date and str(a.to_date) < str(as_at):
			continue
		filled[a.position] = filled.get(a.position, 0.0) + flt(a.weight) / 100.0
		people.setdefault(a.position, []).append({
			# The assignment's own name, so the dialog can end this one rather
			# than guessing from the employee - somebody can legitimately hold
			# the same seat twice over two periods.
			"assignment": a.name,
			"employee": a.employee, "name": a.employee_name,
			"weight": flt(a.weight),
			"type": a.assignment_type or "Permanent",
			"covering": (a.assignment_type or "Permanent") != "Permanent"})

	# Who is working their notice. Nothing new is stored for this: somebody is
	# on notice when they are still Active and their last day is already known.
	# A seat whose only occupant leaves in three weeks is a different problem
	# from a seat that is full, and the chart could not tell them apart.
	#
	# One query for everybody in these seats, not one per person.
	leaving = {}
	holders = {a["employee"] for rows_ in people.values() for a in rows_} 		if people else set()
	if holders:
		for e in frappe.get_all(
				"Employee",
				filters={"name": ("in", list(holders)), "status": "Active",
				         "relieving_date": (">=", as_at)},
				fields=["name", "relieving_date"], limit_page_length=0):
			leaving[e.name] = str(e.relieving_date)
	for rows_ in people.values():
		for a in rows_:
			a["leaving"] = leaving.get(a["employee"])

	titles = {s.name: s.position_title for s in seats}
	rows = []
	for s in seats:
		got = filled.get(s.name, 0.0)
		rows.append({
			"id": s.name,
			"title": s.position_title,
			"branch": s.branch or "",
			"department": s.department or "",
			"designation": s.designation or "",
			"grade": s.grade or "",
			"company": s.company,
			"status": s.status,
			"key": bool(s.is_key_position),
			"seats": flt(s.seats),
			"filled": got,
			# What the table is for. Half-seats are real: two people at 50% of a
			# one-seat role leave nothing open, one of them leaves half.
			"open": max(0.0, flt(s.seats) - got),
			# The soonest last day among the people in it, or None. A seat
			# losing somebody is not the same as an empty one, and it is the
			# earlier warning of the two.
			"leaving_on": min([p["leaving"] for p in people.get(s.name, [])
			                   if p.get("leaving")] or [None],
			                  key=lambda d: d or "9999-12-31"),
			"reports_to": s.reports_to_position or "",
			# The parent's title, so the table reads without a second lookup.
			# Blank when the parent sits outside what this reader may see.
			"reports_to_title": titles.get(s.reports_to_position, ""),
			"people": people.get(s.name, []),
		})
	return {"rows": rows, "may_edit": may_edit(), "as_at": as_at}


@frappe.whitelist()
def save_position(name=None, position_title=None, reports_to_position=None,
                  branch=None, department=None, designation=None, grade=None,
                  seats=None, is_key_position=None, status=None, company=None):
	"""Create a seat, or change one. The hierarchy is `reports_to_position`.

	An empty seat is not a special kind of record - it is a seat with nobody
	assigned to it, which is what makes "we are recruiting for this" visible on
	the chart instead of living in a spreadsheet.
	"""
	if not may_edit():
		_refuse("register.save_position", name)

	companies, branches = _scope()
	doc = frappe.get_doc("Alvoraa Position", name) if name \
		else frappe.new_doc("Alvoraa Position")

	if name:
		# Changing a seat outside your own companies or stores is refused for
		# the same reason reading one is.
		if doc.company not in companies:
			_refuse("register.save_position", name)
		if branches is not None and (doc.branch or "") not in branches:
			_refuse("register.save_position", name)

	fields = {
		"position_title": position_title, "reports_to_position": reports_to_position,
		"branch": branch, "department": department, "designation": designation,
		"grade": grade, "seats": seats, "is_key_position": is_key_position,
		"status": status, "company": company,
	}
	for key, value in fields.items():
		if value is not None:
			doc.set(key, value)

	if not doc.company:
		doc.company = companies[0] if companies else None
	if doc.company not in companies:
		_refuse("register.save_position", name)
	if branches is not None and (doc.branch or "") not in branches:
		# Creating a seat in somebody else's store is the same mistake as
		# editing one, and is refused in the same breath.
		_refuse("register.save_position", name)
	if doc.reports_to_position and doc.reports_to_position == doc.name:
		frappe.throw(_("A position cannot report to itself."))

	doc.flags.ignore_permissions = True
	doc.save() if name else doc.insert()
	return {"ok": True, "name": doc.name, "title": doc.position_title}


# ── who is in a seat ─────────────────────────────────────────────────────────
#
# Creating a seat and filling it are two different acts with two different
# risks, which is why they were built apart. A seat is a shape on a chart; an
# assignment can rewrite whose approval an employee needs. So the second one
# carries the extra guard below, and `delegate_authority` is never implied.

ASSIGNMENT = "Alvoraa Position Assignment"

# What a person can be in a seat. Anything but Permanent reads as "covering"
# on the chart, and is what GRN-style cover flags are counted from.
COVER_TYPES = ("Acting", "Interim", "Additional Charge")


def _position_in_scope(position, endpoint):
	"""The seat, if this editor may touch it. Refuses otherwise.

	Same rule as changing the seat itself: a store's editor works on their own
	store. Checked here rather than trusted from the request, because this is
	a whitelisted endpoint and the position comes in as an argument.
	"""
	if not may_edit():
		_refuse(endpoint, position)
	doc = frappe.get_doc("Alvoraa Position", position)
	companies, branches = _scope()
	if doc.company not in companies:
		_refuse(endpoint, position)
	if branches is not None and (doc.branch or "") not in branches:
		_refuse(endpoint, position)
	return doc


@frappe.whitelist()
def assign_person(position, employee, weight=100, assignment_type="Permanent",
                  from_date=None, to_date=None, delegate_authority=0,
                  covering_for=None, reason=None):
	"""Put somebody in a seat, for a share of it.

	`weight` is what makes part time expressible: two people at 50 each fill a
	one-seat position between them, and one at 50 leaves half of it open. It is
	a percentage of ONE seat, not of the person's working week - the same
	number the chart already shows and the load flags already count.

	DELEGATE AUTHORITY IS OFF UNLESS ASKED FOR, and it is the reason this
	endpoint is not a convenience wrapper. Switching it on rewrites who
	approves that employee's leave and expenses - a change to their working
	life, made from a screen about org structure, which nobody would look for
	there afterwards. So it is passed explicitly, defaulted off, and recorded.
	"""
	doc = _position_in_scope(position, "register.assign_person")

	weight = flt(weight)
	if weight <= 0 or weight > 100:
		frappe.throw(_("A share of a seat is between 1 and 100 per cent."))
	if assignment_type not in ("Permanent",) + COVER_TYPES:
		frappe.throw(_("{0} is not a kind of assignment.").format(assignment_type))
	if assignment_type in COVER_TYPES and not to_date:
		# Cover with no end date is how "acting" quietly becomes permanent,
		# which the chart already flags. Better refused at the source.
		frappe.throw(_("Cover needs a last day. An acting role with no end date "
		               "becomes permanent by neglect, which is what the chart "
		               "flags months later."))

	a = frappe.new_doc(ASSIGNMENT)
	a.update({
		"position": doc.name,
		"employee": employee,
		"weight": weight,
		"assignment_type": assignment_type,
		"from_date": from_date or nowdate(),
		"to_date": to_date or None,
		"covering_for": covering_for or None,
		"delegate_authority": 1 if frappe.utils.cint(delegate_authority) else 0,
		"reason": reason or None,
	})
	# No ignore_permissions. The editor role holds create on this doctype, so
	# this is a real check and not a formality - and if a tenant has not given
	# it, the refusal is the correct answer rather than something to work past.
	a.insert()
	return {"name": a.name, "position": doc.name}


@frappe.whitelist()
def end_assignment(name, on_date=None):
	"""Take somebody out of a seat, from a date.

	Ended rather than deleted. Deleting would erase that they ever held it,
	which is the thing a chart is asked about a year later - "who was running
	Ambala in October" has to stay answerable.
	"""
	a = frappe.get_doc(ASSIGNMENT, name)
	_position_in_scope(a.position, "register.end_assignment")

	on_date = on_date or nowdate()
	if str(on_date) < str(a.from_date):
		frappe.throw(_("Somebody cannot leave a seat before they were in it."))
	a.db_set("to_date", on_date)
	return {"name": a.name, "to_date": str(on_date)}


# ── advertising a seat ───────────────────────────────────────────────────────

JOB_OPENING = "Job Opening"
POSITION_LINK = "alvoraa_position"


@frappe.whitelist()
def post_job(position, vacancies=1, publish=0, closes_on=None, description=None):
	"""Advertise a seat through Frappe HR's own recruitment.

	NO RECRUITMENT IS BUILT HERE. Job Opening already carries applications, the
	careers page and the rest of it; this fills one in from the seat so nobody
	retypes what the position already knows.

	THIS IS THE EXTERNAL ROUTE ONLY. Internal means something different here
	and it is not an unpublished advert: Surbhi, 15 Oct 2026, "internal job
	posting means the selection of an employee suitable for that role within
	the company" - which is `candidates_for` plus `assign_person`, not this.

	`publish` therefore means exactly what Frappe means by it: on puts the
	opening on the careers page, off leaves it with HR until they are ready.
	Both are external; the difference is only whether the world can see it yet.
	"""
	doc = _position_in_scope(position, "register.post_job")
	if not doc.designation:
		frappe.throw(_("This seat has no job role on it, and a job opening needs "
		               "one. Set the role on the seat first."))

	# Job Opening builds its own route as jobs/<company>/<title> and the column
	# is UNIQUE, so two seats with the same title in one company collide on a
	# database integrity error - "Sales Executive" exists in five branches at
	# the first tenant, so the second branch to advertise would simply fail.
	# The branch goes in the route, and a counter after that, because two seats
	# can share a title in one branch too.
	route = "jobs/{0}/{1}".format(
		frappe.scrub(doc.company),
		frappe.scrub(doc.position_title).replace("_", "-"))
	if doc.branch:
		route += "-" + frappe.scrub(doc.branch).replace("_", "-")
	base, n = route, 1
	while frappe.db.exists(JOB_OPENING, {"route": route}):
		n += 1
		route = "{0}-{1}".format(base, n)

	opening = frappe.new_doc(JOB_OPENING)
	opening.update({
		"route": route,
		"job_title": doc.position_title,
		"company": doc.company,
		"designation": doc.designation,
		"department": doc.department or None,
		"location": doc.branch or None,
		"vacancies": frappe.utils.cint(vacancies) or 1,
		"status": "Open",
		"publish": 1 if frappe.utils.cint(publish) else 0,
		"closes_on": closes_on or None,
		"description": description or None,
	})
	if opening.meta.has_field(POSITION_LINK):
		opening.set(POSITION_LINK, doc.name)
	opening.insert()
	return {"name": opening.name, "published": bool(opening.publish)}


@frappe.whitelist()
def where_does_this_person_sit(employee):
	"""The seat somebody holds, and the branch it is in.

	For the "pick the reporting manager" way of adding a seat: name the person
	this new seat reports to, and their own position and branch answer the next
	two questions. A person in more than one seat answers with their primary,
	or failing that the one they hold most of - guessing silently would put a
	new seat under the wrong parent, so the caller is told which was used.
	"""
	if not _may_read():
		_refuse("register.where_does_this_person_sit", employee)

	as_at = nowdate()
	rows = frappe.get_all(
		ASSIGNMENT,
		filters={"employee": employee, "from_date": ("<=", as_at)},
		fields=["name", "position", "weight", "is_primary", "to_date"],
		limit_page_length=0)
	rows = [r for r in rows if not r.to_date or str(r.to_date) >= str(as_at)]
	if not rows:
		return {"position": None, "branch": None, "why": _("This person holds no seat.")}

	# The BIGGEST share of their time wins, and `is_primary` only breaks a tie.
	#
	# That is the opposite way round from what it looks like it should be, and
	# the reason is a defect in the flag rather than a view about it:
	# `is_primary` defaults to 1 on Alvoraa Position Assignment, so every new
	# assignment claims it and demotes the one before. In practice it means
	# "most recently added", not "their main job" - which is not what its own
	# description says it means. Trusting it here would put a new seat under
	# whichever job somebody happened to be given last, including a 30% side
	# role. Raised separately; this function does not try to fix it.
	rows.sort(key=lambda r: (-flt(r.weight), 0 if r.is_primary else 1))
	best = rows[0]
	pos = frappe.db.get_value("Alvoraa Position", best.position,
	                          ["name", "position_title", "branch", "department",
	                           "company"], as_dict=True)
	companies, branches = _scope()
	if not pos or pos.company not in companies or (
			branches is not None and (pos.branch or "") not in branches):
		# Their seat is outside what this reader may see. Saying so beats
		# handing back a blank that reads as "they have no manager".
		return {"position": None, "branch": None,
		        "why": _("This person's own seat is outside what you can see.")}

	return {
		"position": pos.name, "position_title": pos.position_title,
		"branch": pos.branch or None, "department": pos.department or None,
		"why": (_("They hold more than one seat; this is their main one.")
		        if len(rows) > 1 else None),
	}


@frappe.whitelist()
def candidates_for(position, q=None, limit=20):
	"""Who already works here and could take this seat.

	THIS IS WHAT "INTERNAL" MEANS (Surbhi, 15 Oct 2026): not an unpublished
	advert, but picking somebody already in the company who suits the role.
	External is the job opening and the careers page; internal is this.

	NO SUITABILITY IS SCORED. It offers people who already hold the same job
	role, and says how much of their time is already committed, because that
	is the fact somebody needs and cannot see anywhere else. Ranking humans by
	fitness for a job from the fields on an Employee record would be a
	judgement this has no business making, and an automated decision about a
	person the moment it did.

	POST, like `search_people`, for the same reason: a search term is somebody's
	name, and a name does not belong in a URL or a proxy log.
	"""
	doc = _position_in_scope(position, "register.candidates_for")
	companies, branches = _scope()

	filters = {"status": "Active", "company": ("in", companies)}
	if branches is not None:
		filters["branch"] = ("in", branches)
	q = (q or "").strip()
	if q:
		filters["employee_name"] = ("like", "%" + q.replace("%", "") + "%")
	elif doc.designation:
		# No search term: offer the people already doing this job elsewhere.
		# A blank box that lists the whole company is not an offer, it is a
		# directory.
		filters["designation"] = doc.designation

	rows = frappe.get_all(
		"Employee", filters=filters,
		fields=["name as employee", "employee_name as name", "designation",
		        "branch", "department"],
		order_by="employee_name asc",
		limit_page_length=min(frappe.utils.cint(limit) or 20, 50))
	if not rows:
		return {"rows": [], "role": doc.designation or ""}

	# How much of each person is already committed, counted the same way the
	# chart counts it, so the two cannot disagree about who is full.
	as_at = nowdate()
	load = {}
	for a in frappe.get_all(
			ASSIGNMENT,
			filters={"employee": ("in", [r.employee for r in rows]),
			         "from_date": ("<=", as_at)},
			fields=["employee", "weight", "to_date"], limit_page_length=0):
		if a.to_date and str(a.to_date) < str(as_at):
			continue
		load[a.employee] = load.get(a.employee, 0.0) + flt(a.weight)

	for r in rows:
		r["allocated"] = flt(load.get(r.employee, 0.0))
		r["free"] = max(0.0, 100.0 - r["allocated"])
	return {"rows": rows, "role": doc.designation or ""}
