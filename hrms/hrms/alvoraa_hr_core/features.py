"""Is a feature switched on for this site?

Two different questions live here, and they are answered in different places.

`feature_enabled(key)` asks the subscription registry: did the tenant BUY it?
The Alvoraa features that live on stock doctypes (custom fields on Employee,
Appraisal Cycle, Appraisal) cannot be hidden by the module gate alone, so
their hooks ask before doing anything. On a bench without the portal app the
answer is yes: there is nothing to gate against.

`org_switch(key)` asks the organisation: has HR switched this RULE on? Some
things are not a product a tenant buys but a rule each company sets for
itself - whether lateness costs leave or pay, whether attendance counts in an
appraisal. Surbhi's decision of 26 Sep 2026: those are switches in the
portal's Organisation Settings, off until HR turns them on. They are stored in
Frappe's Default store, the same place `hr_api.set_org_setting` writes, and
that endpoint is the only way they change.
"""

import frappe

# The two organisation switches. Unset means off: a company that never opened
# Organisation Settings has neither rule.
LATE_RULES_SWITCH = "late_rules_enabled"
ATTENDANCE_SCORING_SWITCH = "attendance_scoring_enabled"
ORG_SWITCHES = (LATE_RULES_SWITCH, ATTENDANCE_SCORING_SWITCH)


def feature_enabled(key):
	try:
		from alvoraa_portal.subscription import has_feature
	except ImportError:
		return True
	try:
		return bool(has_feature(key))
	except Exception:
		return True


def org_switch(key):
	"""True only when HR has switched this organisation rule on.

	Fails closed: an unknown key, an unset value or anything but "1" is off.
	A rule that deducts pay must never start because a value could not be read.
	"""
	if key not in ORG_SWITCHES:
		return False
	return str(frappe.db.get_default(key) or "") == "1"


def late_rules_on():
	"""Has HR switched late coming and early exit rules on for this company?"""
	return org_switch(LATE_RULES_SWITCH)


def attendance_scoring_on():
	"""Has HR switched attendance in the appraisal score on for this company?"""
	return org_switch(ATTENDANCE_SCORING_SWITCH)
