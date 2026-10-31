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

from hrms.alvoraa_org_structure import people_fields

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

	# Who may open or change the Positions page is not here. It is Frappe's own
	# permission on Alvoraa Position, set in Role Permissions Manager
	# (`register.may_view` / `may_edit`, Surbhi, 19 Oct 2026).

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

	# ── slice 078: what people may see and change about each other ───────────
	#
	# All four ship EMPTY or UNSET, which is the safest value at every existing
	# tenant: nothing a tenant sees changes until a System Manager ticks
	# something. They are `DefaultValue` keys because a doctype per chosen field
	# buys a permission surface, a migration and a list view and does nothing a
	# key with a Version row does not.
	#
	# Which of the ten allow-listed work facts a Positions reader is shown.
	# Empty is safe: the mini profile still opens, with a name and a job role.
	"alvoraa_positions_profile_fields": "",

	# Which `Employee Document Type` names appear on a person's profile. Empty
	# means "nobody can open an employee's documents from the Positions page",
	# which is a statement of fact and not a gap to fill.
	#
	# NOT a Check on `Employee Document Type`: that doctype grants HR Manager
	# `write: 1`, so the tick would be editable in Desk by exactly the role this
	# setting excludes - and at DTC that role IS the Positions audience. The
	# reason is a permission row, not taste.
	"alvoraa_positions_document_types": "",

	# Which of the six permlevel-0 details an employee may correct about
	# themselves. The photograph is NOT in this list: it is always on, and the
	# employee is told who sees it before they add it.
	"alvoraa_my_profile_fields": "",

	# How many days a joiner's pre-onboarding submission is kept when they never
	# become an employee. **Unset or 0 means the feature is OFF**, never "keep
	# for ever": counsel's 18 September 2026 policy prohibits indefinite
	# retention in so many words, so `field_app_photos`' `0 = keep for ever`
	# semantics must not be copied here.
	#
	# **It ships UNSET on purpose, and it is the only key here that does.**
	# 078-PRIV-7's guard is that the form cannot be switched on at a tenant
	# until this number has been set DELIBERATELY - proved by a `Version` row,
	# which an untouched default cannot have. Counsel's figure is outstanding,
	# so inventing one here would be the product answering a legal question.
	"alvoraa_joiner_retention_days": "",

	# How many days an invite link works. **7 is the shipped default, and
	# unlike retention there is every reason to have one**: this is not a legal
	# question, and getting it wrong is an inconvenience rather than an
	# exposure. HR's real case for changing it is a joiner who starts next
	# month and needs longer than a week.
	#
	# It is written into Frappe's own `Web Form Request.expires_on` when a link
	# is issued. There is NO second expiry mechanism anywhere - the framework
	# already owns the expiry, the single-use burn and the row lock.
	#
	# Easy to confuse with the key above, which is why both labels say what
	# they mean in plain words rather than "retention" and "expiry".
	"alvoraa_joiner_link_days": 7,

	# Whether an employee's photograph is included in the company-wide birthday
	# and work anniversary emails. Counsel asked for this by name on 29 Oct
	# 2026: the employer must be able to stop photographs going out in mail
	# WITHOUT turning off the photograph feature, and without turning off the
	# reminders either.
	#
	# **OFF by default, and that is a deliberate change from what the product
	# does today.** `hrms` puts the photograph's URL straight into the mail body
	# (`controllers/employee_reminders.py`, rendered by
	# `templates/emails/{birthday,anniversary}_reminder.html`), and
	# `send_work_anniversary_reminders` is switched ON on dev. Mail is the one
	# surface the person in the photograph cannot see, cannot check and cannot
	# recall, so it is the one place the safe default is worth a changed
	# behaviour. Nothing visible changes on the day this ships, because no
	# employee at any tenant has a photograph yet - which is the whole premise
	# of slice 078.
	#
	# A tenant that wants faces in its birthday mail ticks it on.
	"alvoraa_photo_in_emails": 0,
}

# Slice 012 F1 (SEC-18): the keys that hand out privilege on the org chart.
# Changing any of them can show people parts of the company they could not see
# before, or let them rewrite its structure, so only a System Manager changes
# them, and every change leaves a record.
# The reach levels are here too: raising them to 99 gives every employee close to
# the whole chart, just as adding "Employee" to the roles does.
# The cover and span keys stay with HR - they change alerts and pay rules, not
# who can see or change anybody.
ACCESS_GRANTING = frozenset({
	"alvoraa_org_full_reach_roles",
	"alvoraa_org_managers_see_all",
	"alvoraa_org_reach_up",
	"alvoraa_org_reach_down",
	# Slice 078 (078-SEC-5): the four lists decide what one person may see and
	# change about another, which is the same kind of decision as the reach
	# levels above - so it gets the same treatment, for free: System Manager
	# only, anybody else refused and logged, and a Version row in the same
	# transaction naming the key, the old value and the new one.
	"alvoraa_positions_profile_fields",
	"alvoraa_positions_document_types",
	"alvoraa_my_profile_fields",
	"alvoraa_joiner_retention_days",
	"alvoraa_joiner_link_days",
	# It decides whether a face goes out to every colleague by email, which is
	# exactly the kind of decision this set exists for.
	"alvoraa_photo_in_emails",
})

# Which rule id a refusal and a change are logged under. Slice 012's four keys
# are SEC-18; slice 078's four are 078-SEC-5. One grep must not conflate them -
# plain `SEC-17` and `SEC-18` already mean field rights and org-chart access in
# this codebase, so the new ids are slice-qualified.
RULE_FOR_KEY = {
	"alvoraa_positions_profile_fields": "078-SEC-5",
	"alvoraa_positions_document_types": "078-SEC-5",
	"alvoraa_my_profile_fields": "078-SEC-5",
	"alvoraa_joiner_retention_days": "078-SEC-5",
	"alvoraa_joiner_link_days": "078-SEC-5",
	"alvoraa_photo_in_emails": "078-PRIV-1",
}
DEFAULT_RULE = "SEC-18"

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
	# Slice 078. The card draws its own words from the design; these are the
	# fallback label and explanation, used wherever a key is rendered generically.
	"alvoraa_positions_profile_fields": ("Details a Positions reader may see",
		"Work facts only. Pay, bank details, identity numbers, date of birth and personal contact details can never be chosen."),
	"alvoraa_positions_document_types": ("Document types shown on a person's profile",
		"Whoever can open the Positions page can open the file itself, for everyone in their own companies and branches."),
	"alvoraa_my_profile_fields": ("Details an employee may correct about themselves",
		"A photo is always on. These are the other details they may change."),
	# PLAIN WORDS, not "retention" and "expiry". The two are easy to read as
	# the same thing - and were read that way once already - so each label says
	# what it actually decides.
	"alvoraa_joiner_retention_days": ("How long we keep a submission from someone who never joins",
		"In days. Set it deliberately: until it is set, the joiner form cannot be switched on. Unset or 0 keeps the form off - it does not mean keep for ever."),
	"alvoraa_photo_in_emails": ("Include photographs in birthday and anniversary emails",
		"Off by default. Email is the one place a person cannot see, check or recall who received their picture."),
	"alvoraa_joiner_link_days": ("How long an invite link works",
		"In days, counted from when HR sends it. Seven by default. Longer suits a joiner who starts next month."),
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
	if isinstance(key, str) and key in ACCESS_GRANTING:
		return _set_access_setting(key, value)
	frappe.only_for(["HR Manager", "System Manager"])
	if key not in DEFAULTS:
		frappe.throw(f"Unknown cover setting: {key}")
	frappe.db.set_default(key, value)
	frappe.db.commit()
	return {"ok": True, "key": key, "value": get(key)}


def _set_access_setting(key, value):
	"""A key that decides who sees whom (SEC-18).

	System Manager only, and anyone else is refused and logged - an HR Manager
	included. A real change writes a Version record in the same transaction as
	the change itself: who (owner), when (creation), which key, the old value and
	the new one. So there is never a change without its record. Version rows are
	not cleared by Log Settings, and only a System Manager can read them.
	"""
	from frappe import _
	from frappe.utils import cstr

	from hrms.alvoraa_hr_core.access import refuse

	endpoint = "alvoraa_org_structure.settings.set_cover_setting"
	rule = RULE_FOR_KEY.get(key, DEFAULT_RULE)
	if "System Manager" not in frappe.get_roles():
		refuse(
			_("Only a System Manager can change who may see the org chart. "
			  "Ask your System Manager to make this change."),
			rule,
			endpoint,
			"DefaultValue",
			key,
		)

	# Slice 078 (078-SEC-1, 078-SEC-7): a list key may only ever name fields
	# from its own closed allow-list. REFUSED, not quietly dropped - "a setting
	# that silently does nothing is how a tenant comes to believe a field is
	# editable". The reader intersects again regardless, so a value written
	# straight into `DefaultValue` by some other route still produces nothing.
	if key in people_fields.LIST_KEYS:
		stray = people_fields.off_list(key, value)
		if stray:
			refuse(
				_("These details cannot be chosen: {0}. Pay, bank details, "
				  "identity numbers, date of birth and personal contact "
				  "details are never shown or opened here.").format(", ".join(stray)),
				rule,
				endpoint,
				"DefaultValue",
				key,
			)

	# The retention period is a number of days, set deliberately. There is no
	# "keep for ever" value to save (078-PRIV-6, AC-131d).
	if key == "alvoraa_joiner_retention_days" and cstr(value).strip():
		raw = cstr(value).strip()
		if not raw.isdigit() or not (1 <= int(raw) <= 3650):
			refuse(
				_("Give the number of days a joiner's details are kept, "
				  "between 1 and 3650."),
				rule,
				endpoint,
				"DefaultValue",
				key,
			)

	# A switch, so 0 or 1 and nothing else. A typo must not read as "on".
	if key == "alvoraa_photo_in_emails" and cstr(value).strip() not in ("0", "1"):
		refuse(
			_("Give 0 or 1 for whether photographs go into birthday and "
			  "anniversary emails."),
			rule,
			endpoint,
			"DefaultValue",
			key,
		)

	# How long an invite link works. A blank is refused rather than treated as
	# "for ever": a link with no expiry is the thing the whole token design is
	# there to avoid. 90 days is the ceiling - past that it is not an invite.
	if key == "alvoraa_joiner_link_days":
		raw = cstr(value).strip()
		if not raw.isdigit() or not (1 <= int(raw) <= 90):
			refuse(
				_("Give the number of days an invite link works, between 1 "
				  "and 90."),
				rule,
				endpoint,
				"DefaultValue",
				key,
			)

	old = cstr(frappe.db.get_default(key))
	new = cstr(value)
	if old != new:
		frappe.get_doc({
			"doctype": "Version",
			"ref_doctype": "DefaultValue",
			"docname": key,
			"data": frappe.as_json({"changed": [[key, old, new]]}, indent=None, separators=(",", ":")),
		}).insert(ignore_permissions=True)  # Version has no create permission for anyone; Frappe writes its own the same way
		frappe.db.set_default(key, new)
		_log_access_change(endpoint, key, rule)
	frappe.db.commit()
	return {"ok": True, "key": key, "value": get(key)}


def _log_access_change(endpoint, key, rule=DEFAULT_RULE):
	"""The same JSON line shape as a refusal, so one grep finds both. The key
	only - the old and new values are in the Version record."""
	import json

	try:
		frappe.logger("security").warning(json.dumps({
			"event": "changed",
			"at": str(frappe.utils.now_datetime()),
			"user": frappe.session.user,
			"endpoint": endpoint,
			"doctype": "DefaultValue",
			"name": key,
			"rule": rule,
		}))
	except Exception:
		pass


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
