"""The position register, as a list somebody can actually work with.

The chart answers "what does this company look like". This answers "what seats
do we have, which are empty, and what do I need to change" - and that is a
table, not a tree. Eighty-nine seats across six stores sort and scan in a list;
in a tree you hunt.

It is also where seats are created and re-parented, because that is awkward on
a chart and obvious in a row.

WHO MAY OPEN IT, AND WHO MAY CHANGE IT, IS FRAPPE'S OWN PERMISSION on the
document type "Alvoraa Position" - set on Desk, Role Permissions Manager, like
every other module (Surbhi, 19 Oct 2026). Read opens the page; Write changes
seats and who sits in them. It ships as HR Manager and System Manager. At the
first customer the owners keep the structure themselves through a role of their
own; at the next it may be HR. Either way an administrator ticks the boxes, and
nothing here needs to know which.

Everybody else has the Organisation page. The org chart's `reach()` decides
that page and does not decide this one.

READING IS SCOPED THE SAME WAY AS EVERY OTHER HR READER (slice 030): the
companies somebody may act for, and their branches if they are tied to a store.
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate

from hrms.alvoraa_org_structure import settings

POSITION = "Alvoraa Position"

# The fixed first words of the reason the hire hook writes on an assignment
# (slice 064). Ids only follow it, never a name. The page reads it to say
# "hired for this seat".
PLACED = "Placed on joining from Job Opening"


def _scope():
	"""The companies and branches this reader may act for.

	Returns (companies, branches). `branches` is None for somebody who is not
	tied to a store, which means "every branch" rather than "no branch".

	Somebody given this page in Role Permissions Manager without an HR role -
	the owners at the first customer - gets the same answer HR would: the
	companies in their User Permissions, or else the company on their own
	employee record. `permitted_companies` gives a non-HR role nothing, which
	opened the page on an empty table and refused every save. Every caller of
	this function has already passed `may_view` or `may_edit`.
	"""
	from frappe.core.doctype.user_permission.user_permission import get_user_permissions

	from hrms.alvoraa_hr_core.access import permitted_branches, permitted_companies

	companies = permitted_companies()
	if not companies:
		companies = sorted({d.get("doc") for d in get_user_permissions().get("Company", [])
		                    if d.get("doc")})
	if not companies:
		own = frappe.db.get_value("Employee", {"user_id": frappe.session.user,
		                                       "status": "Active"}, "company")
		companies = [own] if own else []
	return companies, permitted_branches()


def may_view():
	"""Whether this person may open the Positions page at all: Frappe's Read on
	Alvoraa Position. One rule for every endpoint behind the page and the menu.
	"""
	return bool(frappe.has_permission(POSITION, "read"))


def may_edit():
	"""Whether this person may change the structure: Frappe's Write on Alvoraa
	Position.

	ONE CAPABILITY, SET IN ONE PLACE. It covers the seats AND who sits in them
	(Alvoraa Position Assignment), so an administrator ticks one row and not
	two. Asking each doctype separately would let somebody draw seats they could
	not fill - which is what the first customer's own permission rows would have
	done to its owners. Write rather than Create, because nearly every change
	here is to a seat that already exists.
	"""
	return bool(frappe.has_permission(POSITION, "write"))


AUDITED = (POSITION, "Alvoraa Position Assignment")


def record_permission_change(doc, method=None):
	"""A readable record of every change to who may use the Positions page,
	and the menu brought up to date at once. Hooked on Custom DocPerm, which
	is what Role Permissions Manager adds, ticks and removes.

	THE RECORD is a Version on the doctype, written in the same transaction as
	the change, like the org chart's access settings (SEC-18). Frappe's own
	Permission Log was not enough on its own: a ticked box does not name the
	role, and the first change to a doctype copies every shipped row, which it
	logs as rows "Added" - an auditor would read that as HR being given rights.
	Here a copy says it is a copy.

	Skipped on purpose during a migrate, install or patch: nobody chose those
	changes on the screen, and the code that makes them is reviewed in git.
	Frappe's Permission Log skips them for the same reason.

	THE MENU: the Positions item is cached per user for an hour. Clearing it
	for the holders of the changed role makes it follow within the time of a
	page load. The server's own refusal never depended on this cache.
	"""
	if doc.parent not in AUDITED:
		return
	if frappe.flags.in_migrate or frappe.flags.in_install or frappe.flags.in_patch:
		return

	removed = method == "on_trash"
	before = None if removed else doc.get_doc_before_save()
	rights = [(df.fieldname, df.label) for df in frappe.get_meta("Custom DocPerm").fields
	          if df.fieldtype == "Check"]
	who = doc.role if not doc.permlevel else "{0} (level {1})".format(doc.role, doc.permlevel)
	yes_no = lambda v: "Yes" if v else "No"  # noqa: E731

	others = frappe.get_all("Custom DocPerm",
	                        filters={"parent": doc.parent, "name": ("!=", doc.name)},
	                        fields=["role", "permlevel"] + [f for f, _l in rights])
	if not removed and not before and _is_shipped_copy(doc, others, rights):
		changed = [["Role row: " + who, "shipped table",
		            "copied as it was - nobody gained or lost a right"]]
		roles = set()
	elif removed:
		changed = [["Role row: " + who, "on the list", "removed"]]
		changed += [[who + ": " + label, "Yes", "No"] for f, label in rights if doc.get(f)]
		roles = {doc.role}
		if not others:
			# The last row of the doctype's own gone: Frappe goes back to the
			# shipped table, which gives its roles their rights back.
			shipped = frappe.get_all("DocPerm", filters={"parent": doc.parent}, pluck="role")
			changed.append(["Permission table", "this organisation's own rows",
			                "the shipped rows apply again: " + ", ".join(sorted(set(shipped)))])
			roles |= set(shipped)
	elif not before:
		changed = [["Role row: " + who, "not on the list", "added"]]
		changed += [[who + ": " + label, "No", "Yes"] for f, label in rights if doc.get(f)]
		roles = {doc.role}
	else:
		changed = [[who + ": " + label, yes_no(before.get(f)), yes_no(doc.get(f))]
		           for f, label in rights if bool(before.get(f)) != bool(doc.get(f))]
		roles = {doc.role}
		if not changed:
			return

	frappe.get_doc({
		"doctype": "Version", "ref_doctype": "DocType", "docname": doc.parent,
		"data": frappe.as_json({"changed": changed}, indent=None, separators=(",", ":")),
	}).insert(ignore_permissions=True)  # Version has no create permission for anyone; Frappe writes its own the same way

	if doc.parent == POSITION and roles:
		holders = frappe.get_all("Has Role", filters={"parenttype": "User", "role": ("in", list(roles))},
		                         pluck="parent", distinct=True)
		if holders:
			keys = ["portal_ctx_" + u for u in holders]
			# After the commit, or a page load in between could cache the old answer again.
			frappe.db.after_commit.add(lambda: frappe.cache.delete_value(keys))


def _is_shipped_copy(doc, others, rights):
	"""True when Frappe is copying the shipped table, which it does the first
	time anything on a doctype is changed. The row matches a shipped row
	exactly, and so does every row of the doctype's own so far - so the rights
	in force do not change."""
	fields = ["role", "permlevel"] + [f for f, _l in rights]
	shipped = [tuple(_box(r.get(f)) for f in fields) for r in frappe.get_all(
		"DocPerm", filters={"parent": doc.parent}, fields=fields)]
	key = lambda r: tuple(_box(r.get(f)) for f in fields)  # noqa: E731
	return key(doc) in shipped and all(key(o) in shipped for o in others)


def _box(value):
	"""0, None and "" all mean an unticked box; a role name stays a name."""
	return value if isinstance(value, str) and value else int(value or 0)


def _may_see_who_is_leaving():
	"""Whether this reader may be told that somebody is working their notice.

	A pending resignation is the person's own news and is often not announced.
	Reading the organisation's SHAPE and reading who is about to leave it are
	different permissions, and this screen had been treating them as one.

	HR and leadership by role - they cannot plan a replacement otherwise. Plus
	anybody the leaver reports to, which `_my_reporting_line` decides.
	"""
	roles = set(frappe.get_roles())
	allowed = {r.strip() for r in
	           str(settings.get("alvoraa_org_full_reach_roles") or "").split(",")
	           if r.strip()}
	return bool(roles & allowed) or bool(_my_reporting_line())


def _my_reporting_line(depth=6):
	"""Every employee below this caller, however far down, or None for "all".

	None means a full-reach role, which is the only thing that may see the
	whole company's leavers. An empty set means they manage nobody.

	Walked a level at a time with a cap, rather than recursively per employee:
	a six-level company is six queries whatever its size, and a reporting loop
	in bad data stops at the cap instead of running for ever.
	"""
	roles = set(frappe.get_roles())
	allowed = {r.strip() for r in
	           str(settings.get("alvoraa_org_full_reach_roles") or "").split(",")
	           if r.strip()}
	if roles & allowed:
		return None

	me = frappe.db.get_value("Employee", {"user_id": frappe.session.user,
	                                      "status": "Active"}, "name")
	if not me:
		return set()

	seen, edge = set(), [me]
	for _ in range(depth):
		if not edge:
			break
		nxt = frappe.get_all("Employee",
		                     filters={"reports_to": ("in", edge),
		                              "status": "Active"},
		                     pluck="name", limit_page_length=0)
		nxt = [n for n in nxt if n not in seen]
		seen.update(nxt)
		edge = nxt
	return seen


def _refuse_view(endpoint, name=None):
	from hrms.alvoraa_hr_core.access import refuse

	refuse(
		_("The Positions page is open only to the roles your organisation has "
		  "chosen. To see who works where, use the Organisation page. If you "
		  "need this page, ask your HR team."),
		"SEC-8", endpoint, "Alvoraa Position", name)


def _refuse(endpoint, name=None):
	from hrms.alvoraa_hr_core.access import refuse

	refuse(
		_("Changing the position list is not yours to do. "
		  "Ask whoever maintains the structure in your organisation."),
		"SEC-8", endpoint, "Alvoraa Position", name)


@frappe.whitelist()
def position_table(branch=None, department=None, as_at=None):
	"""Every seat this person may see, with how full it is.

	One query for the seats, one for the people in them. Not one per row: at
	eighty-nine seats that is eighty-nine round trips for a table that renders
	in a single screen.
	"""
	if not may_view():
		_refuse_view("register.position_table")
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
		return {"rows": [], "may_edit": may_edit(), "may_delete": may_delete(), "as_at": as_at}

	names = [s.name for s in seats]
	filled, people = {}, {}
	# Slice 070: each person's Reports To and status ride on this same read,
	# through Frappe's link-field join - no second statement. Kept aside in
	# `line`, never on the person, until the rule below decides what may go.
	line, seated_active = {}, set()
	for a in frappe.get_all(
			"Alvoraa Position Assignment",
			filters={"position": ("in", names), "from_date": ("<=", as_at)},
			fields=["name", "position", "employee", "employee_name", "weight",
			        "assignment_type", "to_date", "from_date", "reason",
			        "employee.reports_to as reports_to_emp", "employee.status as emp_status"],
			limit_page_length=0):
		if a.to_date and str(a.to_date) < str(as_at):
			continue
		line[a.name] = (a.reports_to_emp or "", a.emp_status == "Active")
		if a.emp_status == "Active":
			seated_active.add(a.employee)
		filled[a.position] = filled.get(a.position, 0.0) + flt(a.weight) / 100.0
		people.setdefault(a.position, []).append({
			# The assignment's own name, so the dialog can end this one rather
			# than guessing from the employee - somebody can legitimately hold
			# the same seat twice over two periods.
			"assignment": a.name,
			"employee": a.employee, "name": a.employee_name,
			"weight": flt(a.weight),
			"type": a.assignment_type or "Permanent",
			"covering": (a.assignment_type or "Permanent") != "Permanent",
			# Put in this seat by the hire hook (slice 064): the day they joined.
			# Read from the assignment's own fixed reason; nothing is stored for it.
			"hired_on": str(a.from_date) if (a.reason or "").startswith(PLACED) else None})

	# Who is working their notice. Nothing new is stored for this: somebody is
	# on notice when they are still Active and their last day is already known.
	# A seat whose only occupant leaves in three weeks is a different problem
	# from a seat that is full, and the chart could not tell them apart.
	#
	# BUT IT IS NOT SHOWN TO EVERYONE WHO CAN READ THIS SCREEN. Everything else
	# here is structure; this one field is a person's private news, often before
	# it has been announced. Who may open this screen is a setting a tenant may
	# open to its managers, and `permitted_branches` is None - meaning every
	# branch - for anybody not tied to a store. Without this check a peer
	# manager in another city would read every pending resignation in the
	# company, by name, the day it was entered.
	#
	# So: HR and leadership, who cannot plan without it, and the person's own
	# reporting line, who are the ones who have to cover the gap. Nobody else.
	#
	# Suppressed rather than blurred. "Somebody in this seat is leaving" on a
	# one-person seat names them exactly, so a count is not a weaker disclosure
	# than a date - it is the same one, worded vaguely.
	leaving = {}
	may_see_leaving = _may_see_who_is_leaving()
	if may_see_leaving:
		holders = {a["employee"] for rows_ in people.values() for a in rows_} 			if people else set()
		mine = _my_reporting_line()
		if holders:
			for e in frappe.get_all(
					"Employee",
					filters={"name": ("in", list(holders)), "status": "Active",
					         "relieving_date": (">=", as_at)},
					fields=["name", "relieving_date"], limit_page_length=0):
				if mine is None or e.name in mine:
					leaving[e.name] = str(e.relieving_date)
	for rows_ in people.values():
		for a in rows_:
			a["leaving"] = leaving.get(a["employee"])

	# Is this seat already being recruited for? Without it the screen offers
	# "Advertise it" on a seat that is already advertised, and somebody raises
	# a second opening for the same job without ever being told about the
	# first. One query for the lot.
	openings = {}
	if frappe.get_meta(JOB_OPENING).has_field(POSITION_LINK):
		for o in frappe.get_all(
				JOB_OPENING,
				filters={POSITION_LINK: ("in", names), "status": "Open"},
				fields=["name", POSITION_LINK], limit_page_length=0):
			openings[o.get(POSITION_LINK)] = o.name

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
			# The opening that is filling this seat, if one is. The screen shows
			# a way into it instead of offering to make another.
			"opening": openings.get(s.name),
			"leaving_on": min([p["leaving"] for p in people.get(s.name, [])
			                   if p.get("leaving")] or [None],
			                  key=lambda d: d or "9999-12-31"),
			"reports_to": s.reports_to_position or "",
			# The parent's title, so the table reads without a second lookup.
			# Blank when the parent sits outside what this reader may see.
			"reports_to_title": titles.get(s.reports_to_position, ""),
			"people": people.get(s.name, []),
		})
	# The chart is one representation of three different relationships, and the
	# reader chooses which. Reporting is on the rows already; branch is flat so
	# it needs nothing; department IS a tree in ERPNext, so its parent links
	# come along or the department view would be one flat layer pretending to
	# be a hierarchy.
	depts = sorted({s.department for s in seats if s.department})
	parents = {}
	if depts:
		for d in frappe.get_all("Department",
		                        filters={"name": ("in", depts)},
		                        fields=["name", "parent_department",
		                                "department_head"],
		                        limit_page_length=0):
			parents[d.name] = {"parent": d.parent_department or None,
			                   "head": d.department_head or None}
		# A department whose parent is outside the seats we hold still needs
		# its ancestors, or the tree would start halfway up.
		seen, edge = set(parents), [p["parent"] for p in parents.values()
		                            if p["parent"]]
		for _ in range(8):
			edge = [e for e in edge if e and e not in seen]
			if not edge:
				break
			for d in frappe.get_all("Department",
			                        filters={"name": ("in", edge)},
			                        fields=["name", "parent_department",
			                                "department_head"],
			                        limit_page_length=0):
				parents[d.name] = {"parent": d.parent_department or None,
				                   "head": d.department_head or None}
				seen.add(d.name)
			edge = [parents[e]["parent"] for e in edge if e in parents]

	out = {"rows": rows, "may_edit": may_edit(), "may_delete": may_delete(), "as_at": as_at,
	        "departments": parents,
	        # Whether the page may say "leaving" at all, so a reader who may not
	        # see leavers gets no tile - never a "Nobody leaving" that is untrue.
	        "may_see_leaving": bool(may_see_leaving),
	        # "Set manager" opens the Employee record; offered only to somebody
	        # who may change it (design X-6).
	        "may_edit_employee": bool(frappe.has_permission("Employee", "write"))}

	# The people who are on no chart at all: Active, in no seat. A list of
	# named people, so it goes ONLY to somebody who may see them as HR, and
	# the key is ABSENT otherwise - the page then shows no tile, never a "0"
	# that would be untrue (SEC-2). Not stored anywhere; worked out per load.
	from hrms.alvoraa_hr_core.access import NO_EMPLOYEES, permitted_employee_filters

	people = permitted_employee_filters()
	if people != NO_EMPLOYEES:
		out["unseated"], out["active_people"] = _unseated(people, as_at)
	_add_managers(rows, line, seated_active, out, as_at)
	return out


def _add_managers(rows, line, seated_active, out, as_at):
	"""Slice 070: who each seated person reports to, so the chart can draw them
	under their manager's seat. FAILS CLOSED (SEC-1): the key says only what
	this reply already holds.

	- The manager's employee id, only when the person is Active and the manager
	  is Active and already in this reply: seated in one of its seats, or - for
	  a reader who gets the "in no seat" list - in that list.
	- "" when an Active person has no Reports To, and only for that HR reader.
	- Absent in every other case: a Left manager, a manager outside this
	  reader's seats, an unseated manager for a reader without HR scope, and
	  any date but today, because Reports To keeps no history.
	"""
	if getdate(as_at) != getdate():
		return
	hr = "unseated" in out
	known = set(seated_active)
	if hr:
		known.update(u["employee"] for u in out["unseated"])
	for r in rows:
		for p in r["people"]:
			boss, active = line.get(p["assignment"], ("", False))
			if not active:
				continue
			if boss and boss in known:
				p["manager"] = boss
			elif not boss and hr:
				p["manager"] = ""


# The ONLY fields a person in the "in no seat" list carries (PRIV-1). Named one
# by one, never a whole row, so a field added to Employee later cannot leak.
UNSEATED_KEYS = ("employee", "name", "job_role", "branch", "joined", "no_manager")


def _unseated(people, as_at):
	"""Active employees within `people` (HR's own scope, as Frappe filters)
	who hold no seat on `as_at`, and how many Active people that scope holds.

	Two statements whatever the headcount. The scope and the "no seat" test
	stay inside the database - a NOT EXISTS against current assignments - so
	no list of seated ids is read into Python and sent back (nfr-budget §2).
	`no_manager` is a yes/no; the manager's name is never sent.
	"""
	from pypika.terms import ExistsCriterion

	emp = frappe.qb.DocType("Employee")
	seat = frappe.qb.DocType(ASSIGNMENT)
	held = (frappe.qb.from_(seat).select(seat.name)
	        .where(seat.employee == emp.name)
	        .where(seat.from_date <= as_at)
	        .where(seat.to_date.isnull() | (seat.to_date >= as_at)))
	q = (frappe.qb.from_(emp)
	     .select(emp.name, emp.employee_name, emp.designation, emp.branch,
	             emp.date_of_joining, emp.reports_to)
	     .where(emp.status == "Active")
	     .where(ExistsCriterion(held).negate())
	     .orderby(emp.branch).orderby(emp.employee_name))
	for field, (op, value) in people.items():
		# permitted_employee_filters returns exactly these two shapes. Anything
		# else is refused rather than guessed at: a filter dropped here would
		# widen the list (fails closed).
		if op == "in":
			q = q.where(emp[field].isin(list(value)))
		elif op == "!=":
			q = q.where(emp[field] != value)
		else:
			frappe.throw(_("The list of people in no seat could not be scoped."))
	rows = [{"employee": e.name, "name": e.employee_name, "job_role": e.designation or "",
	         "branch": e.branch or "", "joined": str(e.date_of_joining or ""),
	         "no_manager": not e.reports_to}
	        for e in q.run(as_dict=True)]
	active = frappe.db.count("Employee", {**people, "status": "Active"})
	return rows, active


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


def may_delete():
	"""Frappe's own Delete right on Alvoraa Position, ticked on the same
	screen as Read and Write. Separate from Write on purpose: deleting is the
	one change here that cannot be undone from the page."""
	return bool(frappe.has_permission(POSITION, "delete"))


@frappe.whitelist(methods=["POST"])
def delete_position(position):
	"""Remove a seat that was made by mistake and never used.

	ONLY A SEAT WITH NO PAST. Anybody ever assigned to it is part of the record
	of who did what job, which a chart is asked about a year later - so that
	seat is closed, not deleted. Each refusal says what to do instead.
	"""
	if not may_delete():
		_refuse("register.delete_position", position)
	doc = frappe.get_doc(POSITION, position)
	companies, branches = _scope()
	if doc.company not in companies or (
			branches is not None and (doc.branch or "") not in branches):
		_refuse("register.delete_position", position)

	title = frappe.bold(doc.position_title or doc.name)
	if doc._current_assignments():
		frappe.throw(_("{0} still has people in it. Take them out of the seat, then "
		               "set its status to Closed - a seat somebody held is kept, "
		               "not deleted.").format(title))
	if frappe.db.exists(POSITION, {"reports_to_position": doc.name}):
		frappe.throw(_("{0} has other seats reporting to it. Move those seats "
		               "under a different one first, then delete this one.").format(title))
	if frappe.db.exists(ASSIGNMENT, {"position": doc.name}):
		frappe.throw(_("{0} has had people in it, and that history is kept. Set its "
		               "status to Closed instead of deleting it.").format(title))
	try:
		frappe.delete_doc(POSITION, doc.name)
	except frappe.LinkExistsError:
		frappe.throw(_("{0} is named on another record, such as a job opening or a "
		               "dotted reporting line. Set its status to Closed instead of "
		               "deleting it.").format(title))
	return {"ok": True, "name": doc.name}


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


def _person_in_scope(employee, endpoint):
	"""The PERSON must be in this caller's companies and branches, exactly as
	the seat must (slice 071 security F1, F2). One neutral refusal whether the
	ID is outside the scope or does not exist, so it says nothing about anybody.
	"""
	companies, branches = _scope()
	got = isinstance(employee, str) and frappe.db.get_value(
		"Employee", employee, ["company", "branch"], as_dict=True)
	if not got or got.company not in companies or (
			branches is not None and (got.branch or "") not in branches):
		from hrms.alvoraa_hr_core.access import refuse

		refuse(_("You can only look up or place people in your own companies and branches."),
		       "SEC-8", endpoint, "Employee", None)


@frappe.whitelist()
def what_they_hold(employee, ignore_position=None):
	"""Every seat this person is permanently in today, and how full they are.

	Asked BEFORE anybody is put in a seat, so the screen can say "Kamal is
	already 100% in Floor Manager" while there is still a choice to make,
	rather than refusing the save afterwards and leaving somebody to work out
	what to undo.

	Permanent only. Cover is carried on top of a person's own job by design -
	it is extra duty, not a reallocation - so it never needs making room for.

	It had no guard at all, so any login could ask what seats anybody holds.
	"""
	if not may_view():
		_refuse_view("register.what_they_hold", employee)
	_person_in_scope(employee, "register.what_they_hold")

	rows = []
	for a in frappe.get_all(
			ASSIGNMENT,
			filters={"employee": employee, "assignment_type": "Permanent",
			         "from_date": ("<=", nowdate())},
			fields=["name", "position", "weight", "from_date", "to_date"],
			limit_page_length=0):
		if a.to_date and str(a.to_date) < str(nowdate()):
			continue
		if ignore_position and a.position == ignore_position:
			continue
		rows.append({
			"assignment": a.name,
			"position": a.position,
			"title": frappe.db.get_value("Alvoraa Position", a.position,
			                             "position_title") or a.position,
			"weight": flt(a.weight),
			"since": str(a.from_date),
		})
	held = sum(r["weight"] for r in rows)
	return {"rows": rows, "held": held, "free": max(0.0, 100.0 - held)}


def _make_room(employee, position, weight, how):
	"""Take the person out of what they already hold, or shrink it to fit.

	Surbhi, 16 Oct 2026: "if the user confirms the person should be removed
	from the previous position or adjusted (e.g. if the person is only holding
	the new position for 50% then the previous position should show 100-50 =50%
	occupency)."

	  "end"    - they leave the other seats entirely
	  "reduce" - the other seats shrink in proportion so everything sums to 100

	With one previous seat at 100 and 50 wanted here, "reduce" leaves it at 50,
	which is her example exactly. With several, each gives up the same share of
	itself rather than the first one giving up everything.

	A seat that would be left holding less than one per cent is ENDED instead.
	A weight of zero is not a smaller assignment, it is somebody who is not in
	the seat, and the doctype refuses it for that reason.
	"""
	held = what_they_hold(employee, ignore_position=position)
	if not held["rows"]:
		return []

	# Everything being changed must be something this editor could change on
	# its own. Quietly skipping another branch's seat would leave the person
	# over-committed with nothing saying so.
	for r in held["rows"]:
		_position_in_scope(r["position"], "register.assign_person")

	room = 100.0 - flt(weight)
	done = []
	for r in held["rows"]:
		if how == "end" or room <= 0:
			_let_go_of(r["assignment"])
			done.append({"title": r["title"], "to": 0.0})
			continue
		share = r["weight"] / held["held"] if held["held"] else 0
		now = round(room * share, 2)
		if now < 1:
			_let_go_of(r["assignment"])
			done.append({"title": r["title"], "to": 0.0})
		else:
			frappe.db.set_value(ASSIGNMENT, r["assignment"], "weight", now)
			done.append({"title": r["title"], "to": now})
	return done


def _let_go_of(assignment):
	"""End the assignment, or delete it if they were only put in it today.

	`end_assignment` records the day BEFORE they left as their last day, and
	refuses when that would fall before the day they started - a record that
	ends before it begins. For somebody clicking "Take out" that refusal is
	right, and it says to delete the assignment instead.

	Here it would be wrong to refuse. Putting somebody in the wrong seat and
	moving them the same hour is ordinary work, not an error to argue with, so
	this does what that message advises: there is no history worth keeping in
	a seat nobody ever sat in.
	"""
	started = frappe.db.get_value(ASSIGNMENT, assignment, "from_date")
	if started and str(started) >= str(nowdate()):
		frappe.delete_doc(ASSIGNMENT, assignment, force=True,
		                  ignore_permissions=True, delete_permanently=True)
		return
	end_assignment(assignment)


@frappe.whitelist()
def assign_person(position, employee, weight=100, assignment_type="Permanent",
                  from_date=None, to_date=None, delegate_authority=0,
                  covering_for=None, reason=None, resolve=None, add_place=0):
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
	_person_in_scope(employee, "register.assign_person")

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

	# MAKE ROOM FIRST, and only when asked. Without `resolve` this behaves
	# exactly as it always did - the doctype refuses anybody who would be at
	# more than one person, and that refusal is the right default, because
	# moving somebody out of a job is not a side effect of filling another one.
	moved = []
	if resolve:
		if resolve not in ("end", "reduce"):
			frappe.throw(_("{0} is not a way to make room.").format(resolve))
		if assignment_type != "Permanent":
			# Cover sits on top of the person's own job, so there is nothing to
			# clear - and clearing it would take away the job they go back to.
			frappe.throw(_("Cover is carried on top of somebody's own job, so "
			               "there is nothing to move them out of."))
		moved = _make_room(employee, doc.name, weight, resolve)

	# Slice 071, "Place anyway" on a full seat: one more place first, in this
	# same request, so the seat count and the person go in together or not at
	# all. Read fresh here, never trusted from the browser. A seat with no
	# limit (0) or one that has room by now gets nothing added.
	if frappe.utils.cint(add_place):
		seats = flt(doc.seats)
		if seats and doc.filled_weight() + weight / 100.0 > seats + 0.01:
			save_position(name=doc.name, seats=seats + 1)

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
	# The permission was checked above, by `_position_in_scope`: Write on
	# Alvoraa Position, the one capability that governs the structure and who
	# sits in it (see `may_edit`). Asking Frappe again about the Assignment
	# doctype would refuse an owner a tenant had given the structure to.
	a.insert(ignore_permissions=True)
	return {"name": a.name, "position": doc.name, "moved": moved}


@frappe.whitelist()
def end_assignment(name, on_date=None):
	"""Take somebody out of a seat, from a date.

	Ended rather than deleted. Deleting would erase that they ever held it,
	which is the thing a chart is asked about a year later - "who was running
	Ambala in October" has to stay answerable.

	`on_date` IS THE FIRST DAY THEY ARE OUT, and `to_date` is the LAST DAY THEY
	HELD IT - so what gets stored is the day before. The two are not the same
	day and the difference was a visible bug (Surbhi, 15 Oct 2026: "currently
	the take out is not doing anything... the seat should be shown empty").

	Everything that reads a seat keeps anybody whose `to_date` has not yet
	passed - `if a.to_date and str(a.to_date) < str(as_at): continue`, in three
	places. So storing today meant the person stayed in the seat for the rest
	of the day: the click worked, the record changed, and the screen did not
	move. Nothing distinguished that from a dead button.

	This does NOT say anything about whether they left the company. It ends one
	person's hold on one seat, and touches no Employee field. They may have
	moved to another seat in the same hour.
	"""
	a = frappe.get_doc(ASSIGNMENT, name)
	_position_in_scope(a.position, "register.end_assignment")

	out_from = getdate(on_date or nowdate())
	last_day = add_days(out_from, -1)

	# The doctype refuses an assignment that ends before it starts, but this
	# writes with `db_set` and so skips that check. Refuse it here, or the
	# record saves and then throws at whoever next opens the form.
	if a.from_date and str(last_day) < str(a.from_date):
		frappe.throw(
			_("{0} went into this seat on {1}. Taking them out from {2} would "
			  "mean they never held it at all. Delete the assignment instead - "
			  "there is no history worth keeping.")
			.format(frappe.bold(a.employee_name or a.employee),
			        a.from_date, out_from))

	a.db_set("to_date", last_day)

	# GIVE THE APPROVALS BACK. Cover borrows the leave and expense approvals of
	# the team being covered, and handing them back is half of ending it.
	#
	# `db_set` writes one column and runs no hooks, so `on_update` - which is
	# where `_apply_delegation` would notice the cover had ended and restore
	# them - never fires. A stand-in taken out of a seat therefore kept
	# approving leave and expenses for a team that was no longer theirs, with
	# nothing anywhere saying so. Asked for explicitly here rather than by
	# switching to `save()`, because a full save re-runs every rule on the
	# doctype and would start refusing old records on a path whose only job is
	# to write one date.
	#
	# Only once the cover is genuinely over: an end date still in the future
	# means they are covering until then, and the approvals are still theirs.
	restored = 0
	if str(last_day) < str(nowdate()) and a.get("delegated_approvals"):
		restored = len(a.delegated_approvals)
		a.restore_delegation()

	return {"name": a.name, "to_date": str(last_day), "out_from": str(out_from),
	        "approvals_handed_back": restored}


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
	if not may_view():
		_refuse_view("register.where_does_this_person_sit", employee)

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
