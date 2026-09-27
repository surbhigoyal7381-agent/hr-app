"""Keep late rules and attendance scoring on for the tenants that already had them.

Until 26 Sep 2026 both were opt-in features in the tenant registry, given to a
tenant by naming `late_rules` or `attendance_scoring` in its site config
`features` list. They are now two Organisation Settings switches, off by
default. Without this patch the one tenant using them (PP Jewellers) would stop
deducting and scoring the day the change deploys.

What it does: for each switch whose old feature key this site's config names,
set the switch to "1" - but only if HR has not already set it either way.

- A plan bundle never granted either key: `plan_features()` has always stripped
  opt-in keys, so only an explicit `features` list could name them. The check
  still asks `plan_features()` too, in case that ever changes.
- The old keys stay in site config untouched; nothing reads them any more.
- Safe to run twice: a switch that already has a value is left alone.
- A new site has no old config, and Frappe marks its patches done without
  running them, so every new tenant starts with both switches off.

Rollback: set the switch back with `hr_api.set_org_setting(key, "0")`, or clear
it with `frappe.db.set_default(key, "")`.
"""

import frappe

import hrms.alvoraa_hr_core.features as org_features

OLD_KEY_TO_SWITCH = {
	"late_rules": org_features.LATE_RULES_SWITCH,
	"attendance_scoring": org_features.ATTENDANCE_SCORING_SWITCH,
}


def named_features(conf):
	"""The feature keys this site's config names, directly or through its plan."""
	from alvoraa_portal.subscription import plan_features

	named = set(conf.get("features") or [])
	if conf.get("features") is None and conf.get("subscription_plan"):
		named |= set(plan_features(conf.get("subscription_plan")))
	return named


def switches_to_turn_on(conf):
	named = named_features(conf)
	return [switch for old, switch in OLD_KEY_TO_SWITCH.items() if old in named]


def execute(conf=None):
	conf = conf if conf is not None else frappe.conf
	for switch in switches_to_turn_on(conf):
		if frappe.db.get_default(switch) in (None, ""):
			frappe.db.set_default(switch, "1")
