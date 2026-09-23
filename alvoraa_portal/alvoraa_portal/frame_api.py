"""Slice 034, Wave 1: everything the portal frame needs, in one call.

The frame is the rail, the top bar, the bottom bar and the profile sheet. Today
the page builds them from three separate calls - `get_portal_context`,
`get_available_features` and `get_switch_target` - which arrive in any order, so
the menu is drawn twice and items appear late or go missing (FR-03). `get_frame`
asks those same three functions, on the server, and answers once.

Three rules govern this module, and each one has a test that fails if it is
broken:

**A fixed list of keys (SEC-12, AC-46).** `get_portal_context` returns the whole
Employee record - date of birth, gender, phone number, joining date, manager,
branch - and the whole role list. None of that is needed to draw a menu, and all
of it would then be in every page's memory, in every screenshot and in every
browser error report. This call returns SIX fields about the caller and FOUR
role booleans, and the key list is a constant so that adding a field is a
deliberate act somebody reviews.

**No `ignore_permissions`, anywhere in this file (SEC-6, AC-71).** Everything
here is either the caller's own record or a count the caller is entitled to.

**No module-level state that changes at run time (SEC-15, AC-70).** One worker
serves several sites. Every constant below is a tuple, and a filter dict is
built fresh per call. Caching belongs to `frappe.cache()`, which is per site.

The preview page does not protect any of this. Every function here is live on
production from the release that carries it, whatever page calls it (SEC-2), so
each ships with its Guest, wrong-persona and scope tests in the same commit.
"""

import frappe
from frappe import _

# ── The payload's shape ───────────────────────────────────────────────────────
#
# Tuples, not lists or sets: nothing in this module may be appended to at run
# time (SEC-15). `test_frame_endpoint_registry_034` proves the file holds no
# mutable module-level state at all.

# The only Employee fields that leave this module. SEC-12 names the six, and
# names what must never join them: date_of_birth, gender, cell_number,
# date_of_joining, reports_to, branch.
ME_FIELDS = ("employee", "employee_name", "designation", "department", "image", "company")

# Every top-level key `get_frame` returns, for every persona. The set does not
# change between callers - only the values do - so "what can this payload
# contain" is one short list rather than a thing you work out per role.
FRAME_KEYS = (
	"user",                # the caller's own login id
	"user_full_name",      # the caller's own display name, for the rail and the profile sheet
	"has_employee",        # false for a platform operator and for a leaver (persona rule 6)
	"me",                  # ME_FIELDS, or None when has_employee is false
	"is_hr",
	"is_manager",
	"is_system_manager",
	"is_control_plane",
	"has_reports",         # somebody is recorded as reporting to this person
	"may_save_settings",   # AC-67: the Org settings panel reads this
	"review_open_count",   # AC-9c: HR's "Data to review" badge; None for everybody else
	"features",            # get_available_features(), unchanged
	"switch_target",       # get_switch_target(), unchanged - {"label", "url"} or None
	"persona_rule",        # which row of the spec's section 2 matched, 1 to 6
	"show_team",           # is there a Team group for this person
	"allowed_pages",       # the pages the menu may draw, in a fixed order
	"bottom_bar",          # up to four page keys, More is the browser's job
)

# Every page the frame can route to, in the order the fallback walks them.
# Section 2's B4 rule: Home, Inbox, Time, Goals, Pay, Team, Company.
PAGE_ORDER = ("home", "inbox", "time", "growth", "pay", "team", "company")

# Section 2's six persona rows, first match wins. Rules 1 to 5 are tried only
# for somebody who has an ACTIVE Employee record; anybody else falls to rule 6.
# Without that, a platform operator is a System Manager, so `is_hr` is true and
# `has_reports` is false - she would match rule 2 and be given a Time button
# that she has nothing behind (AC-10 and AC-63 used to contradict each other).
RULE_BARS = (
	("home", "inbox", "company", "team"),    # 1: HR with reports
	("home", "inbox", "company", "team"),    # 2: HR without reports (W1D-20)
	("home", "team", "inbox", "time"),       # 3: a manager who is not HR
	("home", "time", "pay", "growth"),       # 4: employee, tenant has payroll
	("home", "time", "inbox", "growth"),     # 5: employee, no payroll
	("home", "inbox", "company"),            # 6: no Active Employee record
)

BAR_SIZE = 4


def _me(user):
	"""The caller's own Active Employee record, cut down to ME_FIELDS.

	One "who am I" helper for the whole frame, reading the ACTIVE record the way
	`hr_api._get_employee` does, so that a person with two Employee rows cannot
	be described two different ways by two parts of the same page.

	Returns None when there is no Active record - a platform operator who was
	never an employee, and a leaver whose login is still enabled. Both get
	persona rule 6.
	"""
	row = frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": "Active"},
		# "name" is the Employee id; it is renamed to "employee" below so the
		# payload never carries two things called name.
		["name", "employee_name", "designation", "department", "image", "company"],
		as_dict=True,
	)
	if not row:
		return None
	return {
		"employee": row.get("name"),
		"employee_name": row.get("employee_name"),
		"designation": row.get("designation"),
		"department": row.get("department"),
		"image": row.get("image"),
		"company": row.get("company"),
	}


def _has_reports(employee):
	"""Is anybody recorded as reporting to this person?

	Deliberately NOT today's `is_manager`, which is also true for any HR user
	when somebody in the tenant has no manager at all (the stand-in rule,
	hr_api.get_portal_context). That rule decides who covers an unassigned
	person's approvals; it was never meant to decide whether to draw a Team
	button, and using it for both is why an HR user with nobody reporting to
	them was shown a manager's bar (W1D-02).
	"""
	if not employee:
		return False
	return frappe.db.count("Employee", {"reports_to": employee, "status": "Active"}) > 0


def _may_save_settings(roles):
	"""AC-67 / W1D-03: may this caller SAVE an organisation-wide setting?

	This must say exactly what `hr_api.set_org_setting` does, or the panel
	offers a Save button that then refuses. The two guards it mirrors are
	`hr_api._require_hr` (HR Manager or System Manager) and
	`hr_api._refuse_store_hr` (a store's HR person holds a Branch User
	Permission and may read but not save; System Manager is not limited).

	It is computed here rather than by calling those guards, because
	`_refuse_store_hr` writes a refusal to the security log, and a store HR
	person simply opening the portal is not a refusal worth recording.
	`test_frame_api_034` calls the real endpoint for every persona and asserts
	it throws exactly when this flag is false, so the two cannot drift apart.
	"""
	if "System Manager" in roles:
		return True
	if "HR Manager" not in roles:
		return False
	from hrms.alvoraa_hr_core.access import permitted_branches

	return permitted_branches() is None


def _allowed_pages(has_employee, is_hr, has_reports, features):
	"""Which pages this person may open. An entry the person cannot use is not
	drawn at all - there are no greyed-out items in this frame.

	A missing plan key means "not answered yet", so the item shows (`is not
	False`), with one exception: `plan_payroll`, where absent hides the salary
	parts, so that nobody is shown payslips their tenant did not buy.
	"""
	allowed = {
		"home": True,
		"inbox": True,
		# Time, Pay and Growth are about the caller's own working life, so they
		# need a working life to be about. Expenses is a required feature on
		# every plan, so the Pay group always has something in it.
		"time": has_employee,
		"pay": has_employee,
		"growth": has_employee and bool(features.get("goals")),
		"team": has_employee and (is_hr or has_reports),
	}
	# Company is a group: it is offered when at least one thing inside it is.
	# For HR that is always true - Org settings is theirs on every tenant, and
	# HR analytics and Reviews (HR) join it where the plan allows - so `is_hr`
	# settles it on its own. For everybody else the group exists only when the
	# tenant bought something in it.
	allowed["company"] = bool(
		is_hr                                    # Org settings, and HR analytics / Reviews where sold
		or features.get("plan_policy_library")   # Policies
		or features.get("plan_org_structure")    # People, the org chart
	)
	# `plan_staff_list` is deliberately NOT in that list (W1D-21, SEC-16).
	#
	# The staff list is an HR screen - `staff_api.get_staff_list` refuses a
	# caller who is entitled to nobody - so the tenant having the feature is not
	# a reason to open the Company group for somebody who is not HR. It would
	# open a group whose only new entry then refuses them.
	#
	# For an HR caller `is_hr` already opens the group above, so the staff list
	# needs nothing here. What decides whether the ENTRY is drawn is
	# `is_hr and features.plan_staff_list`, and both of those are already in
	# this payload - the entry list itself is the page's job, not the frame's.
	# Absent must behave as hidden, because the key is opt-in: a tenant that was
	# never given it, and an entitlement read that failed, must look the same
	# (AC-45).
	return allowed


def _persona_rule(has_employee, is_hr, has_reports, features):
	"""Section 2's table, first match wins. Returns 1 to 6."""
	if not has_employee:
		return 6
	if is_hr and has_reports:
		return 1
	if is_hr:
		return 2
	if has_reports:
		return 3
	if features.get("plan_payroll"):
		return 4
	return 5


def _bottom_bar(rule, allowed):
	"""The persona's four buttons, with anything they may not open replaced.

	B4's fallback order is PAGE_ORDER, skipping what is already in the bar. When
	fewer than four pages are allowed the bar is simply shorter - it never pads
	itself with a button that opens a refusal.
	"""
	bar = [page for page in RULE_BARS[rule - 1] if allowed.get(page)]
	for page in PAGE_ORDER:
		if len(bar) >= BAR_SIZE:
			break
		if allowed.get(page) and page not in bar:
			bar.append(page)
	return bar[:BAR_SIZE]


@frappe.whitelist()
def get_frame():
	"""One start-up call for the whole frame (US-2, AC-7, AC-8).

	Guest is refused by `frappe.whitelist()` without `allow_guest`, which is the
	point: `get_portal_context` DOES allow guests, and this call must not
	inherit that. `test_frame_api_034` pins it.
	"""
	user = frappe.session.user
	if user == "Guest":
		# Belt as well as braces. If somebody ever adds allow_guest to the
		# decorator, this line is what still refuses.
		frappe.throw(_("Please sign in."), frappe.PermissionError)

	from alvoraa_portal.hr_api import get_available_features, get_portal_context
	from alvoraa_portal.module_access import get_switch_target

	# The same three calls the page makes today, so the answers cannot disagree
	# with the old ones (AC-8). Roles come from the context's own booleans; the
	# full role list stays on the server (SEC-12).
	context = get_portal_context() or {}
	features = get_available_features() or {}
	roles = set(frappe.get_roles(user))

	me = _me(user)
	has_employee = me is not None
	is_hr = bool(context.get("is_hr"))
	has_reports = _has_reports(me["employee"] if me else None)
	rule = _persona_rule(has_employee, is_hr, has_reports, features)
	allowed = _allowed_pages(has_employee, is_hr, has_reports, features)

	frame = {
		"user": user,
		"user_full_name": frappe.db.get_value("User", user, "full_name"),
		"has_employee": has_employee,
		"me": me,
		"is_hr": is_hr,
		"is_manager": bool(context.get("is_manager")),
		"is_system_manager": bool(context.get("is_system_manager")),
		"is_control_plane": bool(context.get("is_control_plane")),
		"has_reports": has_reports,
		"may_save_settings": _may_save_settings(roles),
		"review_open_count": context.get("review_open_count") if is_hr else None,
		"features": features,
		"switch_target": get_switch_target(),
		"persona_rule": rule,
		"show_team": allowed["team"],
		"allowed_pages": [page for page in PAGE_ORDER if allowed.get(page)],
		"bottom_bar": _bottom_bar(rule, allowed),
	}
	# The guarantee, enforced rather than described: whatever the code above
	# does, the payload leaves with exactly FRAME_KEYS and nothing else. A new
	# field cannot reach a browser by accident (SEC-12).
	return {key: frame[key] for key in FRAME_KEYS}
