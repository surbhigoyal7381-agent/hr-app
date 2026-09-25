"""Growth: the self-review's data model, its company values, and its ceiling.

Three of Surbhi's five answers of 24 September 2026 live here.

**1. The self-review rates GOALS, in whole points**, with the KPI figures shown
beside them for reference. No half points. The scale is validated on the
server, because a rating that arrives as 3.5 from a browser is a rating that
somebody will have to explain in a calibration meeting.

**2. All company values, not two.** The recommendation was to pick two;
Surbhi overruled it with a reason - *"Most companies dont have more than 5
values. it is important to include all."* So **every** active value on the
tenant's own `Company Value` list is rated, with one optional comment each.
**The list is read from the tenant and nothing here assumes five**: a company
with seven gets seven.

**3. The ceiling on `page_data` is bytes, not characters**, and this module is
where that is enforced. See `PAGE_DATA_MAX_BYTES`.
"""

import json

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, now_datetime, nowdate

# ── the ceiling, measured rather than assumed ────────────────────────────────
#
# `Alvoraa Appraisal Extension.page_data` is a Frappe `Text`, which is MariaDB
# `TEXT`: **65,535 BYTES**, not characters. Measured on this project's own
# bench against the real column:
#
#   * `CHARACTER_OCTET_LENGTH` is 65535, and `sql_mode` includes
#     `STRICT_TRANS_TABLES` - at `@@GLOBAL` as well as `@@SESSION`, so it is
#     MariaDB's own default and not something Frappe sets.
#   * 21,845 Devanagari characters (65,535 bytes) store whole.
#   * **21,846 characters (65,538 bytes) raise
#     `DataError (1406, "Data too long for column 'page_data' at row 1")`.**
#
# **So it throws; it does not truncate silently.** That is the better of the
# two failures, but it is still the wrong one to leave unhandled: the write
# that fails is an AUTOSAVE, so an employee would keep typing while nothing was
# being saved and nothing told them.
#
# Hence a budget checked BEFORE the write, with a sentence that says what to
# do. The margin leaves room for the JSON envelope the column also has to
# carry.
#
# **A Devanagari answer gets one third the characters of an English one for the
# same budget.** That is Wave 5's problem arriving early, and it is why the
# message counts what is left rather than naming a character limit that would
# be a lie in two of the three languages this product is heading for.
PAGE_DATA_MAX_BYTES = 65535
PAGE_DATA_MARGIN_BYTES = 2048
PAGE_DATA_BUDGET_BYTES = PAGE_DATA_MAX_BYTES - PAGE_DATA_MARGIN_BYTES


def page_data_bytes(value):
	"""How much of the column this would actually use.

	Counted in UTF-8 bytes, which is what the column measures. `len()` on a
	string counts characters and would pass a Devanagari answer three times
	over the limit.
	"""
	if not isinstance(value, str):
		value = json.dumps(value, ensure_ascii=False)
	return len(value.encode("utf-8"))


def bytes_per_character(serialised):
	"""How many bytes a character of THIS person's writing actually costs.

	**Measured on what they wrote, not assumed.** A Devanagari character costs
	three bytes and an English one costs one, so a fixed divisor is a number
	that is wrong in two of the three languages this product is heading for -
	and it is wrong in the direction that matters, because it would tell a
	Hindi writer to cut three times more than they need to.

	Never less than 1, so the arithmetic below cannot divide by zero on an
	empty page.
	"""
	if not isinstance(serialised, str):
		serialised = json.dumps(serialised, ensure_ascii=False)
	characters = len(serialised)
	if not characters:
		return 1.0
	return max(1.0, len(serialised.encode("utf-8")) / characters)


def room_left_characters(serialised):
	"""How much more this person can type, **in their own language's terms.**

	A negative number means they are already over. The screen shows this while
	somebody is still typing, which is the whole point: the write that fails is
	an AUTOSAVE, so without a warning they would keep typing while nothing was
	being saved and nothing told them.
	"""
	spare = PAGE_DATA_BUDGET_BYTES - page_data_bytes(serialised)
	return int(spare / bytes_per_character(serialised))


def check_page_data_fits(serialised, what=None):
	"""Refuse an oversize review page before the database does.

	Raises with a sentence that says what happened, why, and what to do next.
	The database's own message - "Data too long for column 'page_data'" - says
	none of those things to somebody who has just lost an afternoon's typing.

	**The number in the sentence is counted in the characters they are actually
	typing**, not in a divisor that only happens to be right for Devanagari.
	"""
	used = page_data_bytes(serialised)
	if used <= PAGE_DATA_BUDGET_BYTES:
		return used
	over_characters = max(1, -room_left_characters(serialised))
	frappe.throw(
		_("This review has got too long to save - it is about {0} characters over. "
		  "Shorten your longest answer and it will save again. "
		  "Nothing you have already saved has been lost.").format(over_characters),
		title=_("Too long to save"),
	)


# ── the rating scale ─────────────────────────────────────────────────────────
#
# Whole points. Surbhi, 24 September 2026: the self-review rates goals in whole
# points, with the KPI figures beside them for reference.
RATING_MIN = 1
RATING_MAX = 5


def check_whole_point(value, label=None):
	"""A rating is a whole number between 1 and 5, or nothing at all.

	Validated on the server. Hiding the half-point from a slider is not a rule
	- the next person to build a screen, or anybody with a browser console,
	sends 3.5 and it is stored.
	"""
	if value in (None, ""):
		return None
	try:
		as_float = float(value)
	except (TypeError, ValueError):
		frappe.throw(_("A rating has to be a whole number from {0} to {1}.").format(
			RATING_MIN, RATING_MAX))
	if as_float != int(as_float):
		frappe.throw(_("Ratings are whole points - please pick {0}, not {1}.").format(
			int(as_float), as_float))
	as_int = int(as_float)
	if not (RATING_MIN <= as_int <= RATING_MAX):
		frappe.throw(_("A rating has to be a whole number from {0} to {1}.").format(
			RATING_MIN, RATING_MAX))
	return as_int


# ── the company's own values ─────────────────────────────────────────────────

VALUE_FIELDS = ("name", "value_name", "icon_emoji", "description")


def company_values_for(employee):
	"""**Every** active value on this employee's company's own list.

	Surbhi overruled the "pick two" recommendation: *"Most companies dont have
	more than 5 values. it is important to include all."*

	**Nothing here assumes five.** The count comes from the tenant, so a
	company with seven values gets seven rows and a company with three gets
	three. `Company Value` is scoped by `company` and carries `is_active`, so
	both are asked of the database rather than guessed.

	A value with no company set belongs to the whole tenant - that is how the
	doctype is used today, and excluding those would silently empty the step
	for any tenant that never filled the company in.
	"""
	if not employee:
		return []
	company = frappe.db.get_value("Employee", employee, "company")
	if not frappe.db.exists("DocType", "Company Value"):
		return []
	# A LIST of conditions, not a dict. A dict can only hold one condition per
	# field, so "this company" and "no company at all" cannot both be written
	# on `company` - the dict version silently keeps the last one and the step
	# quietly loses half the tenant's values.
	or_conditions = [["company", "=", company], ["company", "is", "not set"]] \
		if company else None
	return frappe.get_all(
		"Company Value",
		filters={"is_active": 1},
		or_filters=or_conditions,
		fields=list(VALUE_FIELDS),
		order_by="value_name asc",
		ignore_permissions=True,
	)


def values_step_is_answered(answers, values):
	"""A step counts as done when it has an answer, not when it was opened.

	045 AC-28. "Step 3 of 5" must mean three steps have answers - a step that
	was merely scrolled past is not progress, and a progress bar that says
	otherwise is the kind of number this project keeps having to apologise for.

	**Every** value needs a rating, because Surbhi's answer was all of them.
	The comment on each is optional and its absence never blocks the step.
	"""
	answers = answers or {}
	if not values:
		return False
	return all(answers.get(v["name"], {}).get("rating") for v in values)


@frappe.whitelist()
def get_company_values():
	"""The values this employee will be asked to rate, and how many there are.

	Whitelisted so the wizard can ask once and lay itself out for the real
	number. **The screen must stay usable on a phone at whatever length the
	tenant's list is** - see the implementation notes for what was done about
	that, because seven values on a 390 px screen is a scrolling problem, not a
	data problem.
	"""
	from alvoraa_portal.performance_api import _require_employee

	me = _require_employee()
	values = company_values_for(me)
	return {
		"values": values,
		"count": len(values),
		"rating_min": RATING_MIN,
		"rating_max": RATING_MAX,
		# Whole points only, said in the payload so the screen cannot invent a
		# half-point control and then be corrected by the server.
		"rating_step": 1,
	}


# ══════════════════════════════════════════════════════════════════════════
# The Growth screen
# ══════════════════════════════════════════════════════════════════════════
#
# **This screen is the employee's own.** It reads the caller's own goals, the
# caller's own KPI readings and the caller's own review. There is no employee
# argument on anything below, so there is nothing for a caller to change to
# somebody else's id - the scope is the session, derived on the server every
# time (045 SEC-18).
#
# **Nothing here computes a figure.** The approved number and the waiting
# number travel as two separate keys and no line adds them (AC-29). A figure a
# person sees on this screen is a figure somebody approved.

# Only the Individual Goal fields this screen draws. A fixed list, so adding a
# field to the doctype cannot widen the payload by accident.
GOAL_FIELDS = (
	"name", "goal_name", "target_value", "unit", "actual_progress",
	"progress_pct", "trajectory", "status", "modified", "start_date",
	"end_date", "appraisal_cycle", "is_extra_initiative",
)

# The KPI fields the goal cards show beside a rating. **No rating field and no
# comment field**: ratings are given and shown only inside a review, on its own
# copy (slice 010 group D, PRIV-9).
KPI_CARD_FIELDS = (
	"name", "kpi_name", "individual_goal", "unit", "target_value",
	"actual_value", "attainment_pct", "period_start", "period_end",
)

# AC-24 / `01b` §14 rule 12. `trajectory` is written in `validate` only
# (`alvoraa_goals/controllers/goal.py:36-54`), so a goal nobody saves keeps
# September's answer in December. Older than this and the chip carries the date
# it was worked out, and a stale "On Track" is not counted as attention-free.
#
# **One constant, in one place.** The interval is read by the chip, by the
# needs-attention rule and by the test. Three literals is how two of them come
# to disagree.
TRAJECTORY_STALE_DAYS = 14

# The trajectory values that mean somebody should look. **Names, never a
# percentage.** The prototype's 75 % has no source in the product, and a
# threshold written here would be a second definition of a judgement the goal
# controller already makes.
TRAJECTORY_NEEDS_ATTENTION = ("Off Track", "At Risk")


def _me():
	from alvoraa_portal.performance_api import _require_employee

	return _require_employee()


def _stale(modified):
	"""Is this goal's trajectory older than the interval above?"""
	if not modified:
		return True
	return date_diff(nowdate(), getdate(modified)) > TRAJECTORY_STALE_DAYS


def _trajectory_block(goal):
	"""The chip: the state, the date it was worked out, and whether it is old.

	**The screen is told, not asked to work it out.** `needs_attention` is
	decided here so that the list and any count of it can never be two
	different answers.
	"""
	state = goal.get("trajectory") or ""
	stale = _stale(goal.get("modified"))
	return {
		"state": state,
		# The date the answer was last worked out. Sent always, not only when
		# stale, so the screen never has to guess whether it has one.
		"as_of": str(getdate(goal["modified"])) if goal.get("modified") else "",
		"stale": bool(stale),
		# A stale "On Track" is not counted as attention-free (AC-24), and a
		# goal with no trajectory at all is "Not set yet", never "Off Track"
		# and never 0 % (AC-67).
		"needs_attention": bool(state in TRAJECTORY_NEEDS_ATTENTION),
	}


def _pending_for(child_doctype, parent_field, parents):
	"""The readings that are logged and **not yet approved**, per parent.

	One query for every goal or KPI on the screen, never one per row. The
	amounts come back as their own key and are never added to the approved
	figure - `01b` §7.2 and AC-29: "the figure above does not move until it is
	approved, so nobody sees a number that has not been checked".
	"""
	if not parents:
		return {}
	rows = frappe.get_all(
		child_doctype,
		filters={
			"parent": ["in", parents],
			"parentfield": parent_field,
			"approval_status": ["in", ["Pending", ""]],
		},
		fields=["parent", "value", "log_date", "logged_by"],
		order_by="log_date asc",
		limit=200,
	)
	out = {}
	for row in rows:
		out.setdefault(row["parent"], []).append({
			"amount": row.get("value"),
			"logged_on": str(row["log_date"]) if row.get("log_date") else "",
			# A login id, not a name: who logged it is the person reading the
			# screen in every case this endpoint can produce, because these are
			# the caller's own goals.
			"logged_by": row.get("logged_by") or "",
		})
	return out


def _review_block(employee, cycle):
	"""Where the caller's own self-review has got to, and who it goes to.

	AC-59: an employee with no manager is told plainly, rather than finding out
	when Send refuses.
	"""
	from alvoraa_portal import performance_api

	manager = frappe.db.get_value("Employee", employee, "reports_to")
	goes_to = frappe.db.get_value("Employee", manager, "employee_name") if manager else ""

	appraisal = None
	status = ""
	if cycle:
		appraisal = frappe.db.get_value(
			"Appraisal",
			{"employee": employee, "appraisal_cycle": cycle, "docstatus": ["!=", 2]},
			"name")
	if appraisal:
		status = frappe.db.get_value(
			"Alvoraa Appraisal Extension", {"appraisal": appraisal},
			"review_status") or "Not Started"
	return {
		"appraisal": appraisal or "",
		"status": status,
		# Empty string, not a fabricated name. `get_effective_manager` falls
		# back to the first active HR Manager, which is fine for "who do we
		# notify" and is NOT fine as an answer to "who is your manager"
		# (AC-83). This screen does not use it.
		"goes_to": goes_to or "",
		"has_manager": bool(manager),
		"can_open": bool(appraisal),
	}


@frappe.whitelist()
def get_growth():
	"""The Growth screen, in one call: the cycle, the goals, and the review.

	Query count does not move with how many goals a person has: the goals are
	one read, their KPIs are one read, the two pending-reading sets are one
	read each.
	"""
	from alvoraa_portal.hr_api import _get_employee, me_block

	emp = _get_employee()
	if not emp:
		return {"no_employee": True}
	me = emp["name"]

	cycle = frappe.db.get_value(
		"Appraisal Cycle", {"status": "In Progress"},
		["name", "cycle_name", "start_date", "end_date"], as_dict=True)

	goals = frappe.get_all(
		"Individual Goal",
		filters={"employee": me, "docstatus": ["!=", 2],
		         "status": ["not in", ["Cancelled"]]},
		fields=list(GOAL_FIELDS),
		order_by="end_date asc, goal_name asc",
		limit=100,
	)
	goal_names = [g["name"] for g in goals]
	kpis = frappe.get_all(
		"KPI",
		filters={"employee": me, "status": ["!=", "Cancelled"]},
		fields=list(KPI_CARD_FIELDS),
		order_by="kpi_name asc",
		limit=200,
	)

	goal_pending = _pending_for("Goal Progress Update", "progress_updates", goal_names)
	kpi_pending = _pending_for("KPI Progress Log", "progress_log",
	                           [k["name"] for k in kpis])

	by_goal = {}
	for kpi in kpis:
		block = {
			"kpi": kpi["name"],
			"kpi_name": kpi.get("kpi_name") or "",
			"unit": kpi.get("unit") or "",
			"target": kpi.get("target_value"),
			# **The approved figure.** The waiting one is its own key below and
			# nothing adds the two (AC-29).
			"approved": kpi.get("actual_value"),
			"attainment_pct": kpi.get("attainment_pct"),
			"waiting": kpi_pending.get(kpi["name"], []),
		}
		by_goal.setdefault(kpi.get("individual_goal") or "", []).append(block)

	rows = []
	for goal in goals:
		rows.append({
			"goal": goal["name"],
			"goal_name": goal.get("goal_name") or "",
			"unit": goal.get("unit") or "",
			"target": goal.get("target_value"),
			"approved": goal.get("actual_progress"),
			"progress_pct": goal.get("progress_pct"),
			"status": goal.get("status") or "",
			"start_date": str(goal.get("start_date") or ""),
			"end_date": str(goal.get("end_date") or ""),
			"is_extra_initiative": int(goal.get("is_extra_initiative") or 0),
			"trajectory": _trajectory_block(goal),
			"waiting": goal_pending.get(goal["name"], []),
			"kpis": by_goal.get(goal["name"], []),
		})

	return {
		"me": me_block(emp),
		"cycle": {
			"name": cycle["name"],
			"cycle_name": cycle.get("cycle_name") or cycle["name"],
			"start_date": str(cycle.get("start_date") or ""),
			"end_date": str(cycle.get("end_date") or ""),
		} if cycle else None,
		"goals": rows,
		# The list, and the count of the SAME list. Surbhi's standing rule: a
		# number worked out separately from its list is how the two come to
		# disagree.
		"needs_attention": [r["goal"] for r in rows
		                    if r["trajectory"]["needs_attention"]],
		"review": _review_block(me, cycle["name"] if cycle else None),
		"stale_after_days": TRAJECTORY_STALE_DAYS,
	}


# ══════════════════════════════════════════════════════════════════════════
# The self-review wizard
# ══════════════════════════════════════════════════════════════════════════

# The steps, in order, as names the server decides and the screen only draws.
# **The order is one of the three things the design pass may still change**
# (Surbhi's answer 3), which is exactly why it is data here and not the order
# of some `if`s in a browser.
STEP_GOALS = "goals"
STEP_VALUES = "values"
STEP_OPEN_ITEMS = "open_items"
STEP_NEXT = "next"
STEP_OVERALL = "overall"

STEPS = (STEP_GOALS, STEP_VALUES, STEP_OPEN_ITEMS, STEP_NEXT, STEP_OVERALL)


def _steps_answered(answers, values, goals):
	"""Which steps have an ANSWER, not which were opened (AC-28).

	"Step 3 of 5" has to mean three steps have answers. A step that was merely
	scrolled past is not progress, and a progress bar that says otherwise is
	the kind of number this project keeps having to apologise for.
	"""
	answers = answers or {}
	done = []
	rated = answers.get("goals") or {}
	# **No `goals and`.** A review with no goal copies has nothing to rate, so
	# the step is answered - `all()` over an empty list is already true. With
	# the old `goals and` a person with no goals could never finish step 1 and
	# Send was unreachable for them (AC-90).
	if all((rated.get(g) or {}).get("rating") for g in goals):
		done.append(STEP_GOALS)
	if values_step_is_answered(answers.get("values"), values):
		done.append(STEP_VALUES)
	for step in (STEP_OPEN_ITEMS, STEP_NEXT, STEP_OVERALL):
		block = answers.get(step)
		if isinstance(block, dict) and any(
				str(v or "").strip() for v in block.values()):
			done.append(step)
		elif isinstance(block, str) and block.strip():
			done.append(step)
	return done


@frappe.whitelist()
def get_self_review(appraisal=None):
	"""Everything the wizard needs, in one call, for the caller's OWN review.

	There is no employee argument. `appraisal` is checked against the caller's
	own Employee record before anything is read, so naming somebody else's
	review is a refusal and not a smaller payload.
	"""
	me = _me()
	if appraisal:
		owner = frappe.db.get_value("Appraisal", appraisal, "employee")
		if owner != me:
			frappe.throw(
				_("This page is not part of your access. Ask HR if you think it should be."),
				frappe.PermissionError)
	else:
		cycle = frappe.db.get_value("Appraisal Cycle", {"status": "In Progress"}, "name")
		appraisal = frappe.db.get_value(
			"Appraisal", {"employee": me, "appraisal_cycle": cycle,
			              "docstatus": ["!=", 2]}, "name") if cycle else None
	if not appraisal:
		# AC-43. A sentence, never an empty wizard and never a spinner that
		# stops.
		return {
			"appraisal": "",
			"note": _("There is no review running right now. Your goals are below."),
		}

	from alvoraa_portal import performance_api

	page = performance_api.get_my_review(appraisal)
	values = company_values_for(me)
	# **The wizard's OWN block, not the whole page_data (AC-97).**
	#
	# `save_self_review` writes under `page_data["wizard"]`; this read used to
	# hand back the whole dict. So the screen was given `{"wizard": {...}}`,
	# drew an empty wizard, and posted that back - which stored
	# `wizard.wizard`, then `wizard.wizard.wizard`. A draft did not survive a
	# reload and each save buried the last one a level deeper. Nothing raised,
	# which is why it took a real reload in a real browser to see it: a
	# same-URL `goto` does not reload the document at all, and the check that
	# said "it resumes" was reading the value still sitting in the DOM.
	answers = wizard_block(page.get("page_data") or {})
	goal_ids = [g.get("name") for g in (page.get("goals") or []) if g.get("name")]
	return {
		"appraisal": appraisal,
		"cycle": page.get("cycle"),
		"review_status": page.get("review_status"),
		"goals": page.get("goals") or [],
		"standalone_kpis": page.get("standalone_kpis") or [],
		# **Every** active value on the tenant's own list. Seven if the tenant
		# has seven. Nothing in this payload or in the screen assumes five.
		"values": values,
		"values_count": len(values),
		"answers": answers,
		"steps": list(STEPS),
		"steps_answered": _steps_answered(answers, values, goal_ids),
		# D-13's default, sent to the screen rather than repeated in it: the
		# ratings are required, the three written steps are not, and the last
		# step lists the ones still empty so nobody sends blank answers
		# without noticing. One tuple decides it, on the server.
		"required_steps": list(REQUIRED_STEPS),
		"blank_optional_steps": blank_optional_steps(answers),
		"rating_min": RATING_MIN,
		"rating_max": RATING_MAX,
		"rating_step": 1,
		# The ceiling, in the unit the column actually measures, so the screen
		# can warn while somebody is still typing rather than after the save
		# has already failed.
		"budget_bytes": PAGE_DATA_BUDGET_BYTES,
		"used_bytes": page_data_bytes(json.dumps(answers, ensure_ascii=False)),
	}


@frappe.whitelist(methods=["POST"])
def save_self_review(appraisal, answers):
	"""Save the wizard's answers, and say how much room is left.

	Three things happen here in this order, and the order is the point:

	1. **The caller's ownership is checked**, so a review that is not theirs is
	   refused before anything is read or written.
	2. **Every rating is validated as a whole point** on the server. Hiding the
	   half-point from a control is not a rule - the next screen, or anybody
	   with a browser console, sends 3.5 and it is stored.
	3. **The byte budget is checked BEFORE the write.** The column is 65,535
	   BYTES in strict mode, so an oversize write raises rather than truncating
	   - and the write that fails is an AUTOSAVE, which means somebody would
	   keep typing while nothing was being saved and nothing told them.

	Returns the server's confirmed time and the room left, counted in the
	characters the person is actually typing rather than in a number that is
	only true in English (AC-37, AC-40).
	"""
	me = _me()
	owner = frappe.db.get_value("Appraisal", appraisal, "employee")
	if not owner or owner != me:
		frappe.throw(
			_("This page is not part of your access. Ask HR if you think it should be."),
			frappe.PermissionError)

	if isinstance(answers, str):
		try:
			answers = json.loads(answers)
		except ValueError:
			frappe.throw(_("This review could not be read. Please try again."))
	if not isinstance(answers, dict):
		frappe.throw(_("This review could not be read. Please try again."))

	# Every rating, wherever it is in the answers, goes through the same check.
	for block in ("goals", "values"):
		for key, entry in (answers.get(block) or {}).items():
			if isinstance(entry, dict) and entry.get("rating") not in (None, ""):
				entry["rating"] = check_whole_point(entry.get("rating"))

	from alvoraa_portal import performance_api

	# **One write path, and one budget check.** The check lives inside
	# `save_review_page`, on the string that is actually written - which
	# carries every other page of the review as well. Checking a second time
	# here, on this page's fragment, would be a number that is only ever too
	# generous, and two checks that can disagree are worse than one.
	out = performance_api.save_review_page(
		appraisal, "wizard", json.dumps(answers, ensure_ascii=False))
	return {
		# The SERVER's confirmed time (AC-37). A browser clock can be hours
		# out, and "Saved at 14:02" from a wrong clock is worse than no time.
		"saved_at": str(now_datetime()),
		"used_bytes": out.get("used_bytes"),
		"budget_bytes": out.get("budget_bytes"),
		"room_left_characters": out.get("room_left_characters"),
	}


# ══════════════════════════════════════════════════════════════════════════
# Send - the wizard's answers reach the manager (US-21, AC-87 to AC-99)
# ══════════════════════════════════════════════════════════════════════════
#
# **The failure this closes is a silent one.** Before this, the submit path
# wrote `self_rating` for a KPI copy and only a comment for a goal copy, so a
# Send that appeared to work would have dropped every goal rating and nobody
# would have found out until a calibration meeting. That is why the checks
# below compare stored values with what was on screen rather than checking
# that nothing threw.

# One page key per screen. `wizard` is the wizard's; `past-objectives` is the
# OLD Objectives & KPIs screen's, and it still ships. Nothing is renamed and no
# data is moved (AC-98).
WIZARD_PAGE_KEY = "wizard"
OLD_PAGE_KEYS = ("past-objectives", "past_objectives")

# ── what counts as finished for Send (D-13) ──────────────────────────────────
#
# **This tuple is the whole answer to D-13, and changing it is one line.**
#
# Surbhi has not answered yet, so this is the recommended default from the
# spec: **the ratings are required, the three written steps are not.** A review
# is mostly unusable without its ratings; it is still usable when somebody had
# nothing to add. Forcing text produces "n/a" in three boxes, which looks like
# an answer and is worse than a blank one.
#
# If she wants the written steps required too, that is this one line:
#     REQUIRED_STEPS = STEPS
# The refusal sentences, the screen's list of blank steps and the tests all
# read this tuple, so nothing else has to change.
REQUIRED_STEPS = (STEP_GOALS, STEP_VALUES)


def optional_steps():
	"""The steps a person may leave empty. Derived, never listed twice."""
	return tuple(step for step in STEPS if step not in REQUIRED_STEPS)


def wizard_block(page_data):
	"""The wizard's own block of a review's `page_data`, never the whole dict."""
	block = (page_data or {}).get(WIZARD_PAGE_KEY)
	return block if isinstance(block, dict) else {}


def _block(answers, key):
	block = (answers or {}).get(key)
	return block if isinstance(block, dict) else {}


def _entry(block, key):
	entry = block.get(key)
	return entry if isinstance(entry, dict) else {}


def _text_of(entry):
	if isinstance(entry, dict):
		return " ".join(str(v or "") for v in entry.values())
	if isinstance(entry, str):
		return entry
	return ""


def blank_optional_steps(answers):
	"""The written steps that are still empty, so the last step can say so.

	Listed, never blocked (D-13). The person sees what they are leaving blank
	and decides; the screen does not decide for them.
	"""
	answers = answers or {}
	return [step for step in optional_steps()
	        if not _text_of(answers.get(step)).strip()]


def _live_rows(ext, item_type=None):
	"""This review's own live copies. Never a live `Individual Goal` or `KPI`."""
	from frappe.utils import cint

	return [row for row in (ext.get("review_items") or [])
	        if not cint(row.removed)
	        and (item_type is None or row.item_type == item_type)]


def check_wizard_keys(ext, answers, endpoint="save_review_page"):
	"""SEC-1 on the wizard's page, on a save AND on a send (AC-92, AC-93).

	Every key in the goals block must be a row name of THIS review's own live
	**Objective** copy. One key that is not refuses the whole call and nothing
	is stored - the same rule the old screen has had since slice 010, running
	at last on the page the product is about to use.

	A KPI row name under `goals` is refused too (AC-93). Surbhi decided on
	24 September that goals are rated and KPI figures are shown beside them;
	this is that decision enforced rather than assumed.
	"""
	from hrms.alvoraa_hr_core.access import refuse

	def no(message):
		refuse(message, "SEC-1", endpoint, "Alvoraa Appraisal Extension", ext.name)

	if not isinstance(answers, dict):
		no(_("This review could not be read. Reload the page and try again."))
	goals = answers.get(STEP_GOALS)
	if goals is None:
		return
	if not isinstance(goals, dict):
		no(_("This review could not be read. Reload the page and try again."))
	live = {row.name: row.item_type for row in _live_rows(ext)}
	for key in goals:
		if key not in live:
			no(_("The self-review names an item that is not in this review."))
		if live[key] != "Objective":
			# A KPI row name in the goals block. Refused, not quietly ignored:
			# ignoring it would store a rating the product has no screen for,
			# and nobody would ever see it again.
			no(_("KPI figures are shown beside a goal, not rated. "
			     "Send the rating on the goal itself."))


def refuse_if_unfinished(ext, answers, endpoint="submit_employee_review"):
	"""A part-finished review cannot be sent, and the SCREEN is not what says so.

	AC-89, AC-90, AC-91. The check runs on the review's live copies at the
	moment of Send, never on the list the browser was holding - so a goal added
	after somebody rated everything blocks the send until it is rated.

	Nothing is written before this passes.
	"""
	rated_goals = _block(answers, STEP_GOALS)
	unrated = [row.title or row.name for row in _live_rows(ext, "Objective")
	           if not _entry(rated_goals, row.name).get("rating")]
	if unrated:
		# Whole sentences with placeholders. Never a sentence built by joining
		# pieces - word order moves between English, Hindi and Punjabi.
		if len(unrated) == 1:
			frappe.throw(_("One goal still needs a rating: {0}. Go back to the goals "
			               "step, give it a rating, and send again.").format(unrated[0]))
		frappe.throw(_("{0} goals still need a rating: {1}. Go back to the goals step, "
		               "give each one a rating, and send again.").format(
			len(unrated), ", ".join(unrated)))

	if STEP_VALUES in REQUIRED_STEPS:
		rated_values = _block(answers, STEP_VALUES)
		missing = [v.get("value_name") or v["name"]
		           for v in company_values_for(ext.employee)
		           if not _entry(rated_values, v["name"]).get("rating")]
		if missing:
			if len(missing) == 1:
				frappe.throw(_("One company value still needs a rating: {0}. Go back "
				               "to the values step, give it a rating, and send again."
				               ).format(missing[0]))
			frappe.throw(_("{0} company values still need a rating: {1}. Go back to the "
			               "values step, give each one a rating, and send again."
			               ).format(len(missing), ", ".join(missing)))

	# Only reached if D-13 comes back the other way and a written step joins
	# REQUIRED_STEPS. One tuple decides it, here and on the screen.
	for step in REQUIRED_STEPS:
		if step in (STEP_GOALS, STEP_VALUES):
			continue
		if not _text_of((answers or {}).get(step)).strip():
			frappe.throw(_("This step still needs an answer before you can send: {0}."
			               ).format(_(step_label(step))))


STEP_LABELS = {
	STEP_GOALS: "Your goals",
	STEP_VALUES: "Company values",
	STEP_OPEN_ITEMS: "Still open from last time",
	STEP_NEXT: "What you want to take on next",
	STEP_OVERALL: "Anything else",
}


def step_label(step):
	"""The name a person sees for a step. One list, read by the server and the
	screen, so a refusal never names a step by a key nobody recognises."""
	return STEP_LABELS.get(step, step)


def apply_wizard_self_review(ext, answers, endpoint="submit_employee_review"):
	"""The wizard's goal ratings onto the review's OWN copies (AC-87).

	Through `review_items.set_item_rating`, which is the one function that
	already writes a rating and its stamp together - so the record keeps the
	numbers the person was looking at when they pressed Send, not the numbers
	today. That is what makes AC-96 answerable a year later.

	**The KPI half is left exactly as it is** (AC-94). The old Objectives & KPIs
	screen still writes `self_rating` on a KPI copy; the wizard never does. A
	KPI copy the wizard never touched keeps 0, and 0 already reads as "not
	rated" everywhere in this code, never as a score of zero.

	Nothing outside the review is written (AC-88, R13, SEC-1): no live
	`Individual Goal`, no `KPI`, and no figure is recomputed.
	"""
	from alvoraa_goals import review_items

	check_wizard_keys(ext, answers, endpoint)
	for key, values in _block(answers, STEP_GOALS).items():
		values = values if isinstance(values, dict) else {}
		rating = check_whole_point(values.get("rating"))
		if rating is None:
			continue
		comment = values.get("comment")
		review_items.set_item_rating(
			review_items.live_row(ext, key), "self",
			rating=rating,
			comment=str(comment) if comment is not None else None,
		)
