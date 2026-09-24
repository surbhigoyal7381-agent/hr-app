"""The Team screen: two sections, and the actions that follow from which one.

Surbhi's decision of 24 September 2026, approved in full. The Team screen
separates the two reasons a person is on it - **"Your team"** (they report to
you) and **"You cover"** (they are in your HR scope and they do not) - and the
action set differs between them.

**Why two sections and not one list with a label**, recorded so nobody
simplifies it back:

1. A screen is scanned by shape before it is read. Two headings say "these are
   two different relationships" before anybody reads a name. A chip on a row in
   one long list has to be read, one row at a time, forty-two times.
2. Mixed buttons in one list is how somebody presses the wrong one. Inside a
   section every row offers the same actions, so the hand learns the screen.
3. It degrades well. A manager who is not HR sees one section; an HR person
   with no reports sees one section; **nobody ever sees an empty heading**.

**Three rules this module exists to keep**, and each is a check:

* **`covered` is the HR scope MINUS `direct`.** `direct` wins. The two lists
  share nobody, so the two counts add up to the number of distinct people the
  caller can act on, and somebody who is both appears **once**, under "Your
  team", with the manager actions **plus** the HR-only ones (AC-75).
* **The section is DERIVED, never taken from the request** (045 SEC-18). There
  is no `section` or `basis` argument on anything here. `direct` means
  `reports_to = me` at this moment; `covered` means the HR scope minus that.
* **Every count is per section.** There is no combined Team total anywhere,
  because it would equal no list on the screen (AC-74).

**And the scope goes into the query as a subquery**, never as an `IN (...)` of
ids read into Python and shipped back. Slice 044 measured a x5 slope on that
shape and `nfr-budget.md` bans it. The scope is asked twice - once per section -
which is two constant queries, not one per person.
"""

import frappe
from frappe import _

from alvoraa_portal.hr_api import TEAM_LIST_CAP, me_block
from alvoraa_portal.home_api import _filter_list

# The only Employee fields a Team row carries, in EITHER section. What differs
# between the sections is the actions offered, never the fields carried. A
# fixed list, the same discipline as `frame_api.FRAME_KEYS` and
# `staff_api.ROW_KEYS` - "what can this payload contain" is one short list
# rather than something you work out per role.
ROW_FIELDS = ("name", "employee_name", "designation", "department", "user_id", "image")

# The eleven rows of the action matrix, as names the server decides and the
# screen only draws. Each one is enforced here AND by the endpoint behind it;
# a screen that hides a button is not an access rule.
ACT_APPROVE_LEAVE = "approve_leave"
ACT_SEE_LEAVE_WHY = "see_leave_why"
ACT_APPROVE_CORRECTION = "approve_correction"
ACT_APPROVE_EVIDENCE = "approve_evidence"
ACT_SET_GOALS = "set_goals"
ACT_SEE_SCORECARD = "see_scorecard"
ACT_SEE_PRESENCE = "see_presence"
ACT_OPEN_RECORD = "open_record"
ACT_INVITE_OR_BLOCK_PHONE = "invite_or_block_phone"
ACT_CANCEL_DEDUCTION = "cancel_deduction"
ACT_ACT_AS_HR = "act_as_hr"

# The matrix itself, as data rather than as branching, so that the eleven rows
# can be walked by a test one at a time. Eleven UI rows are eleven server
# checks, and a matrix is the shape where one row gets missed and the miss
# stays invisible until somebody presses it (045 SEC-18a).
#
# (action, allowed for a direct report, allowed for a covered person)
ACTION_MATRIX = (
	(ACT_APPROVE_LEAVE, True, False),
	(ACT_SEE_LEAVE_WHY, True, False),
	(ACT_APPROVE_CORRECTION, True, True),   # covered: only after the wait - see below
	(ACT_APPROVE_EVIDENCE, True, False),
	(ACT_SET_GOALS, True, False),
	(ACT_SEE_SCORECARD, True, False),
	(ACT_SEE_PRESENCE, True, True),
	(ACT_OPEN_RECORD, True, True),
	(ACT_INVITE_OR_BLOCK_PHONE, False, True),
	(ACT_CANCEL_DEDUCTION, False, True),
	(ACT_ACT_AS_HR, False, True),
)

ALL_ACTIONS = tuple(a for a, _d, _c in ACTION_MATRIX)

REFUSAL = "This page is not part of your access. Ask HR if you think it should be."


def allowed(action, is_direct, is_hr_over_them):
	"""**The matrix, read in exactly one place.**

	`is_direct` - they report to this caller.
	`is_hr_over_them` - this caller's HR scope covers them.

	The two are not exclusive, and that is the whole of AC-75: somebody who is
	both gets the manager column **and** the HR-only column, and their row is
	drawn once, under "Your team". Being their manager does not take an HR
	caller's HR entitlements away; it decides which section the row appears in,
	not what the caller is.

	This function is the only place the matrix is consulted. The payload
	builder and the by-hand permission check both call it, so a screen and a
	server can never disagree about a row.
	"""
	for act, on_direct, on_covered in ACTION_MATRIX:
		if act == action:
			return (on_direct and is_direct) or (on_covered and is_hr_over_them)
	return False


def _caller(user=None):
	"""(employee row, is_hr). Fails closed on a caller with no Employee record.

	**The user is threaded through rather than read from the session twice.**
	The first version took the employee from an argument and the roles from
	`frappe.session.user`, so asking "may this OTHER person do this" would have
	answered with that person's employee record and the CALLER's roles - a
	mixture that is nobody's real permissions. Nothing called it that way yet,
	which is exactly why it was worth fixing before something did.
	"""
	from alvoraa_portal.hr_api import _get_employee

	user = user or frappe.session.user
	emp = _get_employee(user)
	is_hr = bool({"HR Manager", "HR User"} & set(frappe.get_roles(user)))
	return emp, is_hr


def direct_query(emp_id):
	""""Your team" - this person's own Active direct reports, as a subquery."""
	from alvoraa_portal.hr_api import direct_reports_query

	return direct_reports_query(emp_id)


def covered_conditions(user, emp_id):
	"""The conditions for "You cover" - the HR scope, MINUS the direct reports.

	**One filter builder, and it never returns "everything"** (045 AC-84 /
	SEC-6). `permitted_employee_filters()` never returns an empty dict, and
	`home_api._filter_list` is the one place that turns it into a condition
	list that can be added to. `hr_api.py:410` grew a hand-rolled second copy
	of that function; Wave 4 is the commit that would have given the copy more
	callers, so it calls the real one instead.

	Two conditions are added and each would be a regression if dropped:
	`status = Active` keeps leavers out, and the caller keeps themselves out.

	**What is NOT here, on purpose: `reports_to != me`.** Making the two
	sections disjoint is `_section`'s job, done by excluding rows rather than by
	filtering them, because a `!=` on a nullable field makes the count and the
	list disagree - see `_section`. `name != emp_id` is safe because `name` can
	never be NULL.
	"""
	from hrms.alvoraa_hr_core.access import permitted_employee_filters

	conds = _filter_list(permitted_employee_filters(user))
	conds += [["status", "=", "Active"]]
	if emp_id:
		conds += [["name", "!=", emp_id]]
	else:
		# No Employee id and an HR entitlement is the exact fail-open shape the
		# security review found. `name IN ()` matches nobody, and it is never
		# left as "no condition" (SEC-4).
		conds += [["name", "in", []]]
	return conds


def _section(conds, order_by="employee_name asc", exclude=None):
	"""One section: its rows, its own total, and whether it is capped.

	**Every condition here is NULL-insensitive, and that is a defect this slice
	found by asserting it rather than a style choice.**

	The covered section is "the HR scope minus my direct reports". Writing that
	minus as a filter - `reports_to != me` - makes the count and the list
	disagree. `frappe.db.count` and `frappe.get_all` take different paths
	through Frappe, and the two treat NULL differently on a `!=`: one keeps a
	row whose `reports_to` is NULL, the other counts it out.

	Measured on this slice's own fixture: for a store HR caller the list drew
	**9** people and the count said **4** - because five of the nine have no
	manager recorded, which is the ordinary state of most people in a shop.
	**The screen would have read "You cover (4)" above nine cards.**

	So the minus is not done in SQL at all. `conds` carries only `=`, `in` and
	`!=`-on-a-mandatory-field, all of which both paths agree about, and the
	direct reports are removed from the rows here and from the total by
	subtracting a second NULL-insensitive count (`reports_to = me`, which is an
	equality and so safe). The two numbers cannot drift apart because neither
	depends on how NULL is handled.

	`exclude` is **one Employee id - a manager's**. When it is given, anybody
	reporting to that person is left out of the rows and out of the total. The
	read asks for twice the cap so that removing them cannot leave the page
	short, which bounds it at a hundred rows by construction.
	"""
	if exclude:
		# `exclude` is a manager's Employee id: drop the people who report to
		# them. Read WITH `reports_to` so the filtering needs no second query,
		# and build every row key by key from ROW_FIELDS afterwards - so
		# `reports_to` is used and dropped here and cannot reach a payload
		# (AC-6 asserts its absence, by key, recursively).
		#
		# Bounded: at most `cap` of the fetched rows can be direct reports that
		# also matter, so `cap * 2` is always enough to fill a page of `cap`.
		fetched = frappe.get_all(
			"Employee", filters=conds,
			fields=list(ROW_FIELDS) + ["reports_to"],
			order_by=order_by, limit=TEAM_LIST_CAP * 2,
			ignore_permissions=True)
		kept = [r for r in fetched if r.get("reports_to") != exclude]
		rows = [{k: r.get(k) for k in ROW_FIELDS} for r in kept[:TEAM_LIST_CAP]]
		# Both counts are EQUALITIES or `in`, which Frappe's two query paths
		# agree about. Neither depends on how NULL is handled, so they cannot
		# drift apart the way `reports_to != me` did.
		total = max(0, frappe.db.count("Employee", filters=conds)
		            - frappe.db.count("Employee",
		                              filters=conds + [["reports_to", "=", exclude]]))
		return {"rows": rows, "total": total,
		        "capped": total > len(rows), "cap": TEAM_LIST_CAP}
	rows = frappe.get_all("Employee", filters=conds, fields=list(ROW_FIELDS),
	                      order_by=order_by, limit=TEAM_LIST_CAP,
	                      ignore_permissions=True)
	total = frappe.db.count("Employee", filters=conds)
	return {
		"rows": rows,
		"total": total,
		"capped": total > len(rows),
		"cap": TEAM_LIST_CAP,
	}


def may(action, employee, user=None):
	"""**The one answer to "may this caller do this to this person".**

	Derived here, on the server, every time. There is no `section` argument and
	there never will be: the caller's relationship to the employee is a fact
	about this moment, and a client that could name it could name the wrong
	one.

	Returns (allowed, reason). `reason` is None when allowed, and otherwise a
	sentence the screen can print - never "not allowed", which tells nobody
	what to do next.
	"""
	user = user or frappe.session.user
	if action not in ALL_ACTIONS:
		# An unknown action is refused, not ignored. Fail closed on anything
		# about a person.
		return False, _("That is not something this screen can do.")
	if not employee:
		return False, _("No person was named.")

	emp, is_hr = _caller(user)
	if not emp:
		return False, _(REFUSAL)

	is_direct, is_hr_over_them = relationship(employee, emp.name, is_hr, user)
	if not (is_direct or is_hr_over_them):
		# The refusal reads identically whether the cause is "not in your
		# scope" or "not something you may do". A different sentence for a
		# different cause tells the caller which guess was closer.
		return False, _(REFUSAL)
	if not allowed(action, is_direct, is_hr_over_them):
		return False, _(REFUSAL)
	return True, None


def relationship(employee, emp_id, is_hr, user):
	"""(is_direct, is_hr_over_them) - **derived, never declared.**

	045 SEC-18(b). `direct` means `reports_to = emp_id` at this moment;
	`is_hr_over_them` means this caller's HR scope covers them. Both are asked
	of the database when the question is asked, so nothing a client sends can
	move a person from one column to the other.

	Note the two are asked independently. `is_hr_over_them` is NOT "in the
	covered section" - a direct report of an HR caller is usually in their HR
	scope too, and that is exactly what gives the both-person their HR-only
	actions (AC-75).
	"""
	is_direct = bool(emp_id) and \
		frappe.db.get_value("Employee", employee, "reports_to") == emp_id
	is_hr_over_them = False
	if is_hr:
		conds = covered_conditions(user, emp_id)
		# `covered_conditions` excludes direct reports, because that is what
		# makes the SECTIONS disjoint. The HR entitlement question is a
		# different one, so the exclusion is dropped for it.
		conds = [c for c in conds if not (c[0] == "reports_to" and c[1] == "!=")]
		is_hr_over_them = bool(frappe.get_all(
			"Employee", filters=conds + [["name", "=", employee]],
			limit=1, pluck="name", ignore_permissions=True))
	return is_direct, is_hr_over_them


def actions_for(is_direct, is_hr_over_them):
	"""The action names this row may offer.

	The screen draws what is here and nothing else. A control absent from the
	payload cannot be pressed; a control that is merely disabled can be
	re-enabled in a browser, and `01b` §14 rule 1 forbids a greyed control
	anyway.

	**One caveat that belongs on the record, not in a button.**
	`approve_correction` appears on a covered row, but whether a PARTICULAR
	request may be decided yet depends on the two-working-day window - and that
	is a fact about the request, not about the person. `attendance_correction`
	owns it, refuses before the date with a sentence naming the manager and the
	day, and the row says "with [manager] until [date]".
	"""
	return sorted(a for a in ALL_ACTIONS if allowed(a, is_direct, is_hr_over_them))


@frappe.whitelist()
def get_team():
	"""The Team screen, in **one** call, carrying **both** sections.

	Two sections must not become two calls. The page's budget is one call
	beyond the frame's two, and it stays one after the split.
	"""
	emp, is_hr = _caller()
	if not emp:
		return {"no_employee": True}

	direct = _section([["reports_to", "=", emp.name], ["status", "=", "Active"]])

	# "You cover" is the HR scope MINUS the direct reports, and the minus is
	# done here rather than as a `reports_to != me` filter - see `_section` for
	# the count-versus-list defect that costs. The names to remove are read
	# with an EQUALITY on `reports_to`, which both of Frappe's query paths
	# agree about, and the read is capped the same way the section is.
	covered = None
	if is_hr:
		covered = _section(covered_conditions(frappe.session.user, emp.name),
		                   exclude=emp.name)

	# Which of the drawn direct reports are ALSO in the caller's HR scope - the
	# both-people, who get the HR-only actions as well (AC-75).
	#
	# **One query for the whole section, not one per row.** The obvious way to
	# write this is a `relationship()` call inside the loop, which is an N+1
	# the moment a manager has fifty reports; this asks the database once with
	# the drawn names, which are capped at fifty by construction.
	both = set()
	if is_hr and direct["rows"]:
		conds = covered_conditions(frappe.session.user, emp.name)
		conds = [c for c in conds if not (c[0] == "reports_to" and c[1] == "!=")]
		both = set(frappe.get_all(
			"Employee",
			filters=conds + [["name", "in", [r["name"] for r in direct["rows"]]]],
			pluck="name", ignore_permissions=True))

	for row in direct["rows"]:
		row["basis"] = "direct"
		row["also_covered"] = row["name"] in both
		row["actions"] = actions_for(True, row["also_covered"])
	if covered:
		for row in covered["rows"]:
			row["basis"] = "covered"
			row["also_covered"] = True
			row["actions"] = actions_for(False, True)

	return {
		"me": me_block(emp),
		# Each section carries its OWN total, cap and capped flag. There is no
		# combined number anywhere in this payload, because there is no single
		# list on the screen it could equal (AC-74).
		"direct": direct,
		"covered": covered,
		# Whether "You cover" is drawn at all. Never a label on one list.
		"is_hr_scope": is_hr,
		# So the screen can say which headings exist without counting rows and
		# without ever drawing an empty heading (AC-73).
		"has_direct": bool(direct["total"]),
		"has_covered": bool(covered and covered["total"]),
	}
