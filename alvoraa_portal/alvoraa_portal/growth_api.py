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


def check_page_data_fits(serialised, what=None):
	"""Refuse an oversize review page before the database does.

	Raises with a sentence that says what happened, why, and what to do next.
	The database's own message - "Data too long for column 'page_data'" - says
	none of those things to somebody who has just lost an afternoon's typing.
	"""
	used = page_data_bytes(serialised)
	if used <= PAGE_DATA_BUDGET_BYTES:
		return used
	over = used - PAGE_DATA_BUDGET_BYTES
	frappe.throw(
		_("This review has got too long to save - it is about {0} characters over. "
		  "Shorten your longest answer and it will save again. "
		  "Nothing you have already saved has been lost.").format(
			max(1, over // 3)),
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
