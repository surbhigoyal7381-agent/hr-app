"""Which details about a person a screen may show, and which it may never show.

Slice 078. Two closed lists and one deny rule, in ONE place, because the whole
privacy position of that slice rests on them being closed:

  * `POSITIONS_PROFILE_FIELDS` - the ten work facts a Positions reader may be
    shown about a colleague, if the organisation ticks them.
  * `MY_PROFILE_WRITE_FIELDS` - the six details an employee may correct on
    their own record, if the organisation ticks them.
  * `NEVER` plus `is_denied()` - what no tick may ever reach, whatever a
    setting says and whatever permission level the reader holds.

**Why a constant and not a permission level.** `employee_field_rights.py`
deliberately locked WRITE on 35 Employee fields and left READ open, because
level 0 is "the employee's own details" and no screen was to lose a field. So a
permlevel cannot refuse a READ: ticking `bank_ac_no` or `date_of_birth` would
simply work, and HR Manager holds read at level 1 anyway. The allow-list is the
control. A permlevel is not.

**Both ends intersect.** The setter refuses an off-list name, AND the reader
intersects again - so a value written straight into `DefaultValue` by any other
route produces nothing. The second one is the only half that survives a future
UI, which is why it is not optional.

Here in `hrms` rather than in `alvoraa_portal` because the settings setter that
validates a tick (`settings.py`) is here, and `alvoraa_portal` already imports
from `hrms` unguarded. The other direction is guarded everywhere it exists, and
a guarded import that fails open is not a control.
"""

import frappe

# ── the ten work facts a Positions reader may see ────────────────────────────
#
# Work facts, and nothing else. Every one of them is already on the chart, in
# the staff directory, or in a team page - this list says which of them may
# appear on ONE more screen, not that anything new becomes visible.
#
# "Work phone" is deliberately absent: Employee has no such field (checked in
# erpnext's employee.json, and `staff_api.py:69-71` says so in its own comment
# from the last time somebody asked). `cell_number` is labelled "Mobile" and is
# personal, so it is not a substitute. Ten, not eleven.
POSITIONS_PROFILE_FIELDS = (
	"designation",
	"department",
	"branch",
	"company",
	"reports_to",
	"grade",
	"employment_type",
	"date_of_joining",
	"default_shift",
	"company_email",
)

# ── the six details an employee may correct about themselves ─────────────────
#
# All six are permlevel 0 - the employee's own details - and all six are things
# only the person themselves actually knows. Their job, their pay, their bank
# and their identity numbers are not here and never will be: a self-service
# screen must not become a way round field rights.
#
# Blood group and marital status stay off: health and family data, and no
# screen needs them.
MY_PROFILE_WRITE_FIELDS = (
	"cell_number",
	"personal_email",
	"current_address",
	"person_to_be_contacted",
	"relation",
	"emergency_phone_number",
)

# ── what no tick may ever reach ──────────────────────────────────────────────
#
# This is belt and braces: nothing here is on either list above, so the lists
# alone already refuse all of it. It is written down anyway, because the lists
# will be edited one day by somebody who has not read this file, and a named
# deny list is what a test can assert and a reviewer can read.
#
# `pan_number` and the other India fields are CUSTOM fields, created by
# `hrms/regional/india/setup.py` - they exist only on an India-regional tenant.
# So a test that asserts "pan_number is refused" proves nothing unless the field
# exists on that site. Named here regardless, because the deny list must not
# depend on which regional pack a tenant installed.
NEVER = (
	# pay
	"ctc", "salary_mode", "salary_currency", "payroll_cost_center",
	"employee_advance_account",
	# bank
	"bank_name", "bank_ac_no", "iban", "ifsc_code", "micr_code",
	# statutory identity
	"pan_number", "esi_number", "provident_fund_account",
	# person, not worker
	"date_of_birth", "marital_status", "blood_group",
	# home and next of kin are the employee's to give, never a reader's to browse.
	# (They ARE on MY_PROFILE_WRITE_FIELDS, which is the employee's own screen -
	# `is_denied` is asked about the Positions list, see `allowed`.)
	"current_address", "permanent_address", "personal_email", "cell_number",
	"person_to_be_contacted", "relation", "emergency_phone_number",
	# the reason somebody is leaving is never a profile row. The DATE may appear
	# in the one "left on" sentence, which is not a field read.
	"relieving_date",
	# health
	"health_details", "health_insurance_no", "health_insurance_provider",
)


def is_denied(fieldname):
	"""Is this field one no Positions tick may ever reach?

	Includes every field a payroll rule set names, read live: a tenant that
	points a pay rule at a field has told us that field decides money.
	"""
	if not isinstance(fieldname, str) or not fieldname.strip():
		return True
	name = fieldname.strip()
	if name in NEVER:
		return True
	try:
		from alvoraa_portal.employee_field_rights import rule_set_fields

		return name in rule_set_fields()
	except Exception:
		# alvoraa_portal absent, or no rule set table yet. The static deny list
		# above has already been applied, and the allow-lists are the control.
		return False


# ── reading and writing a ticked list ────────────────────────────────────────

# key -> the allow-list a value stored under it is intersected with.
LIST_KEYS = {
	"alvoraa_positions_profile_fields": POSITIONS_PROFILE_FIELDS,
	"alvoraa_my_profile_fields": MY_PROFILE_WRITE_FIELDS,
	# Slice 079. All three are the SAME SIX as My Profile, by identity rather
	# than by copy (079 AC-104), so a third candidate list cannot appear and
	# drift away from the one the code actually allows.
	#
	# **HR-only fields are excluded, and the reason is `01c` §6's, not the old
	# one.** A joiner holds no write right on `Employee` at any level, so the
	# intersection `candidate ∩ has_permlevel_access_to(write)` is the empty set
	# for them, and admitting one would be a hard-coded exception for the
	# least-trusted principal in the system. The sentence this used to be
	# justified by - "there is no permission level on a path opened without a
	# login" - is FALSE now that the joiner has a login, and must not be quoted
	# again.
	"alvoraa_joiner_fields": MY_PROFILE_WRITE_FIELDS,
	"alvoraa_joiner_required_fields": MY_PROFILE_WRITE_FIELDS,
	"alvoraa_my_profile_required_fields": MY_PROFILE_WRITE_FIELDS,
}


def allowed(key, raw):
	"""The ticked field names a stored setting really grants, in list order.

	Called by the SETTER (so an off-list name is refused outright) and again by
	every READER (so a name written straight into `DefaultValue` by any other
	route produces nothing). The second call is the one that matters.

	Order comes from the allow-list, not from what was stored, so the screen
	reads the same whatever order somebody ticked things in.
	"""
	whitelist = LIST_KEYS[key]
	asked = {v.strip() for v in str(raw or "").split(",") if v.strip()}
	return tuple(f for f in whitelist if f in asked)


def off_list(key, raw):
	"""The names in a posted value that this key may not carry. Empty is good."""
	whitelist = set(LIST_KEYS[key])
	return tuple(sorted({v.strip() for v in str(raw or "").split(",") if v.strip()}
	                    - whitelist))


def asked_and_required(asked_key, required_key):
	"""Slice 079: what is asked, and which of it is compulsory.

	Two intersections, in order, and the second one is the point: a name on the
	required list that is **not** being asked for is dropped, so a required mark
	can never widen what may be asked or written (078-SEC-18, 079 AC-40). The
	setter refuses it too, but a value written straight into `DefaultValue` by
	any other route has to produce nothing - that is the half that survives a
	future UI.

	Returns (asked, required), both in allow-list order.
	"""
	asked = allowed(asked_key, frappe.db.get_default(asked_key))
	wanted = set(allowed(required_key, frappe.db.get_default(required_key)))
	return asked, tuple(f for f in asked if f in wanted)


# ── the 48 px copy ───────────────────────────────────────────────────────────

# The derived thumbnail is a private File row on the Employee, found by its own
# `attached_to_field`. No column on the HR master and no migration: the chart
# and the table are the only two things that read it, and both read it in ONE
# batched query whatever the headcount.
THUMB_FIELD = "alvoraa_photo_48"


def thumbnails_for(employees):
	"""{employee: 48 px url} for a list of employees, in ONE query.

	One statement for 20 people and one for 400 - which is OPS-6's requirement
	and also the privacy gate, because a per-person read is how a payload
	quietly grows. A missing row is not an error: the renderer falls back to the
	full photograph and then to the person's initials.
	"""
	names = [e for e in dict.fromkeys(employees or []) if e]
	if not names:
		return {}
	rows = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Employee",
		         "attached_to_field": THUMB_FIELD,
		         "attached_to_name": ("in", names)},
		fields=["attached_to_name", "file_url"],
		limit_page_length=0, ignore_permissions=True)
	return {r.attached_to_name: r.file_url for r in rows if r.file_url}
