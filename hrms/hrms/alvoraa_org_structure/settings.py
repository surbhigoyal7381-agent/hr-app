"""How this organisation handles temporary cover.

Every one of these is a POLICY, not a fact, so none of them is hard-coded. A
company covering a shop two streets away and one covering a plant three hours
away should not be forced into the same rule.

Stored as Frappe Global Defaults, which is where organisation-level config
already lives in this product and what the portal's Org Setup page already reads
and writes. A settings doctype would have been a second place to look.

The defaults below are what a company gets before anybody thinks about it, and
they are set to the cautious answer in each case: cover must end, it does not
hide a vacancy, and 130% is as far as somebody is stretched without a reason
being written down.
"""

import frappe
from frappe.utils import cint, flt

# key, default, what it means
DEFAULTS = {
	# Time-box it, always. Cover that never ends is not cover - it is a second
	# job nobody agreed to, and it is the commonest way this goes wrong.
	"alvoraa_cover_require_end_date": 1,

	# After this many days somebody should decide: make it permanent, or
	# re-advertise. The alert is the point - the failure is not over-allocation
	# on day one, it is nobody noticing on day two hundred.
	"alvoraa_cover_max_days": 90,

	# Pay for it. Off by default because it costs money and that is the
	# customer's decision, not ours.
	"alvoraa_cover_pay": 0,
	"alvoraa_cover_allowance_percent": 15,
	"alvoraa_cover_allowance_component": "",

	# A covered seat is still an empty seat as far as hiring is concerned.
	# Once somebody is covering, urgency drops and the requisition quietly
	# stalls - which is how a three-month gap becomes a year.
	"alvoraa_cover_vacancy_stays_open": 1,

	# The ceiling on one person's total load, cover included.
	"alvoraa_cover_max_load": 130,

	# How far an ordinary employee may see on the org chart. Two levels up and
	# two down is enough to answer the questions they actually have - where am
	# I, who is my manager, who is on my team - without handing everybody a map
	# of the whole company. Structure is commercially sensitive, and a full org
	# chart is the first thing that walks out of the door with a leaver.
	"alvoraa_org_reach_up": 2,
	"alvoraa_org_reach_down": 2,

	# Who may roam the whole thing. HR needs it to do their job; leadership
	# needs it to run the place.
	"alvoraa_org_full_reach_roles": "HR Manager,HR User,System Manager",

	# Anybody with people reporting to them. On by default because a manager
	# who cannot see past their own team cannot plan around the one next door.
	"alvoraa_org_managers_see_all": 1,

	# Span of control. Past about nine, a manager cannot give anybody real
	# attention - one-to-ones stop and appraisals become a form to fill in.
	# Usually the sign that a layer is missing rather than that anybody is lazy.
	"alvoraa_org_span_wide": 9,

	# One person managing one person is usually a title rather than a job.
	# Sometimes it is a deliberate deputy, so this is a low-severity note, not
	# an error. Set to 0 to stop flagging it at all.
	"alvoraa_org_span_narrow": 1,

	# Above the ceiling: refuse, or allow with a written reason. Allowing with a
	# reason is the default, because a flat refusal gets worked around by
	# recording the cover as permanent, which is worse than the thing it stops.
	"alvoraa_cover_allow_over_cap": 1,
}

# Kept apart from the numbers so the Org Setup page can render a label and an
# explanation without either being duplicated in the front end.
LABELS = {
	"alvoraa_cover_require_end_date": ("Cover must have an end date",
		"Cover that never ends is a second job nobody agreed to."),
	"alvoraa_cover_max_days": ("Warn when cover runs longer than (days)",
		"After this, somebody decides: make it permanent, or re-advertise."),
	"alvoraa_cover_pay": ("Pay an allowance for cover",
		"Adds a salary component while the cover runs, and stops when it ends."),
	"alvoraa_cover_allowance_percent": ("Allowance, per cent of the cover weight",
		"15% of a 30% cover is roughly 4.5% of pay. Commonly 10 to 20."),
	"alvoraa_cover_allowance_component": ("Salary component to use",
		"Which line the allowance appears on."),
	"alvoraa_cover_vacancy_stays_open": ("A covered seat still counts as vacant",
		"So recruitment does not quietly stall once somebody is standing in."),
	"alvoraa_cover_max_load": ("Most one person may carry (per cent)",
		"Their own role plus everything they are covering."),
	"alvoraa_cover_allow_over_cap": ("Allow going over, with a written reason",
		"Off means refused outright. On means allowed once somebody says why."),
	"alvoraa_org_reach_up": ("Levels an employee may see above them", "Two is usually enough."),
	"alvoraa_org_reach_down": ("Levels an employee may see below them", "Two is usually enough."),
	"alvoraa_org_full_reach_roles": ("Roles that may see the whole chart",
		"Comma separated. HR and system administrators by default."),
	"alvoraa_org_managers_see_all": ("Anybody with direct reports sees the whole chart",
		"Off means a manager is bounded like everybody else."),
	"alvoraa_org_span_wide": ("Flag a manager with this many reports or more",
		"Past about nine, one-to-ones stop happening. Usually a missing layer."),
	"alvoraa_org_span_narrow": ("Flag a manager with this many reports",
		"One person managing one person. Set to 0 to stop flagging it."),
}


def get(key):
	"""One setting, with its default when nobody has chosen."""
	if key not in DEFAULTS:
		frappe.throw(f"Unknown cover setting: {key}")
	raw = frappe.db.get_default(key)
	fallback = DEFAULTS[key]
	if raw in (None, ""):
		return fallback
	if isinstance(fallback, int) and not isinstance(fallback, bool):
		return cint(raw) if float(raw) == int(float(raw)) else flt(raw)
	return raw


def all_settings():
	return {k: get(k) for k in DEFAULTS}


@frappe.whitelist()
def get_cover_settings():
	"""What the Org Setup page renders: value, label and why it exists."""
	frappe.only_for(["HR Manager", "System Manager"])
	return [{
		"key": k,
		"value": get(k),
		"default": DEFAULTS[k],
		"label": LABELS[k][0],
		"help": LABELS[k][1],
	} for k in DEFAULTS]


@frappe.whitelist()
def set_cover_setting(key, value):
	"""Change one. Refuses a key it does not know, so a typo in the front end
	cannot quietly create a setting nothing ever reads."""
	frappe.only_for(["HR Manager", "System Manager"])
	if key not in DEFAULTS:
		frappe.throw(f"Unknown cover setting: {key}")
	frappe.db.set_default(key, value)
	frappe.db.commit()
	return {"ok": True, "key": key, "value": get(key)}


# ── cover that has quietly become permanent ──────────────────────────────────

@frappe.whitelist()
def long_running_cover():
	"""Cover that has outlasted what this organisation considers temporary.

	This is the one that matters. The failure is not somebody at 130% on day
	one - that was a decision. It is nobody noticing on day two hundred, by
	which point a person has been doing two jobs for most of a year and nobody
	ever revisited it.

	So the useful number is not the load, it is HOW LONG it has been true.
	"""
	frappe.only_for(["HR Manager", "HR User", "System Manager"])
	limit = cint(get("alvoraa_cover_max_days"))
	today = frappe.utils.nowdate()

	out = []
	for row in frappe.get_all(
			"Alvoraa Position Assignment",
			filters={"assignment_type": ("!=", "Permanent"),
			         "from_date": ("<=", today)},
			fields=["name", "employee", "employee_name", "position", "weight",
			        "assignment_type", "from_date", "to_date", "covering_for"]):
		if row.to_date and str(row.to_date) < today:
			continue
		days = frappe.utils.date_diff(today, row.from_date)
		if days < limit:
			continue
		out.append({
			**row,
			"days": days,
			"over_by": days - limit,
			# What somebody actually decides between.
			"ends_on": row.to_date or "open-ended",
		})

	out.sort(key=lambda r: -r["days"])
	return {"limit_days": limit, "cover": out, "count": len(out)}


def alert_on_long_cover():
	"""Daily. Writes nothing and blocks nothing - it puts the list where HR
	will see it, which is the whole intervention."""
	found = long_running_cover.__wrapped__() if hasattr(long_running_cover, "__wrapped__") \
		else long_running_cover()
	if not found["count"]:
		return
	frappe.log_error(
		title=f"Cover running longer than {found['limit_days']} days",
		message="\n".join(
			f"{c['employee_name']} covering {c['position']} for {c['days']} days "
			f"({c['assignment_type']}, ends {c['ends_on']})" for c in found["cover"]))
	return found
