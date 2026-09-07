"""The price list: seeding it once, keeping it honest, and reading it back.

Three jobs.

`seed()` fills an empty price list with the model we agreed - seven tiers, five
operations packs, and a rate for every module we sell or plan to. It runs once
per site and records that it did, on the same principle as `baseline.py`: a seed
that runs twice overwrites whatever a person has since changed, and the second
run is always the one nobody remembers approving.

`sync_registry()` adds a price row for any feature the product has gained since
the last run. A module built on Tuesday should appear in the price list on
Tuesday, with no rate, visibly unpriced - rather than being quietly unsellable
because nobody remembered to add it. It never deletes: a rate that was once
charged has to stay readable, because an invoice points at it.

`get_price_catalogue()` is what the admin console reads.

All three refuse to run anywhere but the control plane. The doctypes ship with
the app, so they exist on every tenant site too; leaving them empty there is
what stops a tenant administrator reading our price list out of their own desk.
"""

import frappe
from frappe import _
from frappe.utils import flt

from alvoraa_portal.subscription import FEATURES, feature_spec

# Bumped when the seed content changes in a way an existing site should pick up.
# A site stamped with an older release is left alone: prices may have been edited
# since, and a seed is not allowed to overwrite a decision.
SEED_RELEASE = "2026-09-06"

# ── the model, as approved ───────────────────────────────────────────────────
# These are starting values. Once seeded they are rows, and the console is the
# only place they should ever change again.

PLANS = [
	# name, band_from, band_to, fee, included, extra PEPM
	("Starter",           1,    25,  1999,   25, 75),
	("Growth",            26,   50,  2999,   50, 65),
	("Business",          51,  100,  4999,  100, 60),
	("Professional",     101,  250,  8999,  250, 55),
	("Enterprise",       251,  500, 14999,  500, 50),
	("Enterprise Plus",  501, 1000, 24999, 1000, 45),
	("Enterprise Custom", 1001,  0,     0,     0, 40),   # quote only
]

# Every plan carries the same HR platform. The ladder is headcount, not
# features - the add-ons below are what a tenant buys on top, at any tier.
#
# Listed by hand rather than read from the registry's `required` flag, because
# the two answer different questions. `required` means a tenant cannot switch it
# off; this list means the platform fee already pays for it. Expenses is in both.
# Onboarding & Exit and Tax & Benefits are in this list and not `required` - they
# are included in the fee, and a tenant may still turn them off.
#
# Payroll is the one that decides the shape of the price list, and it is
# deliberately absent: it is charged per employee on top, at every tier.
PLATFORM_FEATURES = [
	"portal", "leaves", "attendance", "expenses", "hr_setup",
	"tenure", "tax_benefits",
]

PACKS = [
	# name, rate per named user, requires, ERPNext feature keys
	("Finance",           300, None,      ["erp_accounts", "erp_assets", "india_compliance"]),
	("Trade",             250, "Finance", ["erp_selling", "erp_buying", "erp_stock"]),
	("Manufacturing",     250, "Trade",   ["erp_manufacturing", "erp_quality_management"]),
	("Projects & Service", 200, "Finance", ["erp_projects", "erp_support", "erp_maintenance"]),
	("CRM",               200, None,      ["erp_crm"]),
]

PACK_CAP_PER_USER = 799

MODULE_PRICES = [
	# feature key, label, rate, basis, status
	("payroll",       "Payroll & Statutory",        25, "PEPM", "Built"),
	("recruitment",   "Recruitment / ATS",          35, "PEPM", "Built"),
	("performance",   "Performance Management",     25, "PEPM", "Built"),
	("goals",         "OKR & Goal Management",      20, "PEPM", "Built"),
	("analytics",     "Advanced Analytics",         20, "PEPM", "Built"),
	# Not in the registry, and deliberately so - nothing can switch these on
	# because they do not exist yet. Listed with the price we intend to charge.
	("feedback_360",  "360 Degree Feedback",        15, "PEPM", "Coming Soon"),
	("timesheet",     "Timesheet / Project Tracking", 25, "PEPM", "Coming Soon"),
	("engagement",    "Employee Engagement",        15, "PEPM", "Coming Soon"),
	("lms",           "Learning / LMS",             25, "PEPM", "Coming Soon"),
	("ai_assistant",  "AI HR Assistant",            30, "PEPM", "Coming Soon"),
	("ai_agents",     "Advanced AI Agents",          0, "Usage", "Coming Soon"),
	("api_access",    "API Access",               1500, "Per organisation", "Coming Soon"),
	("sso",           "Single Sign-On",           2000, "Per organisation", "Coming Soon"),
	("biometric",     "Biometric Integration",    1000, "Per device", "Coming Soon"),
	("whatsapp_bot",  "WhatsApp HR Bot",          1500, "Per organisation", "Coming Soon"),
	# Delivered by a person, not by a switch.
	("custom_workflow", "Custom Workflow",        2500, "One-time", "Service"),
	("custom_report",   "Custom Report",          2500, "One-time", "Service"),
]


def _control_plane_only(what):
	"""Refuse anywhere but the control plane.

	The pricing doctypes install on every site because they ship with the app.
	They stay empty on a tenant, which is the only reason a tenant administrator
	- who is System Manager on their own site - cannot read our price list.
	"""
	if frappe.conf.get("alvoraa_control_plane") is None:
		frappe.throw(
			_("{0} runs on the control plane only. This site is a tenant, and its "
			  "price list is meant to stay empty.").format(what),
			title=_("Not the control plane"))


# ── seeding ──────────────────────────────────────────────────────────────────

def seed(force=False):
	"""Fill an empty price list with the agreed model. Runs once per site."""
	_control_plane_only(_("Seeding the price list"))

	settings = frappe.get_single("Alvoraa Pricing Settings")
	if settings.seeded and not force:
		return {"seeded": False,
		        "reason": f"already seeded ({settings.seeded}) - prices may have "
		                  f"been edited since, and a seed does not overwrite a decision"}

	made = {"plans": 0, "packs": 0, "modules": 0}

	for name, low, high, fee, included, pepm in PLANS:
		if frappe.db.exists("Alvoraa Plan", name):
			continue
		quote_only = not fee
		doc = frappe.get_doc({
			"doctype": "Alvoraa Plan",
			"plan_name": name,
			"sequence": len(frappe.get_all("Alvoraa Plan")) + 1,
			"band_from": low,
			"band_to": high,
			"platform_fee": fee,
			# Ten months' money for twelve months' service.
			"annual_fee": fee * 10,
			"included_employees": included,
			"additional_pepm": pepm,
			"is_quote_only": 1 if quote_only else 0,
			"features": [{"feature_key": k} for k in PLATFORM_FEATURES],
		})
		doc.insert(ignore_permissions=True)
		made["plans"] += 1

	# Module prices before packs: a pack stamps its `pack` field onto rows that
	# already exist, so creating them the other way round leaves the link unset.
	for key, label, rate, basis, status in MODULE_PRICES:
		if frappe.db.exists("Alvoraa Module Price", key):
			continue
		frappe.get_doc({
			"doctype": "Alvoraa Module Price",
			"feature_key": key,
			"module_label": label,
			"rate": rate,
			"basis": basis,
			"status": status,
		}).insert(ignore_permissions=True)
		made["modules"] += 1

	made["modules"] += _sync_registry_rows()

	# Packs in listed order so a pack's prerequisite exists before it is named.
	for name, rate, requires, features in PACKS:
		if frappe.db.exists("Alvoraa Operations Pack", name):
			continue
		frappe.get_doc({
			"doctype": "Alvoraa Operations Pack",
			"pack_name": name,
			"rate_per_user": rate,
			"requires_pack": requires,
			"features": [{"feature_key": k} for k in features],
		}).insert(ignore_permissions=True)
		made["packs"] += 1

	settings.pack_cap_per_user = settings.pack_cap_per_user or PACK_CAP_PER_USER
	settings.seeded = SEED_RELEASE
	settings.save(ignore_permissions=True)
	frappe.db.commit()
	return {"seeded": True, "created": made}


# ── keeping up with the product ──────────────────────────────────────────────

def _sync_registry_rows():
	"""One unpriced row for every registry feature that has none yet."""
	made = 0
	existing = set(frappe.get_all("Alvoraa Module Price", pluck="name"))
	for key in _sellable_registry_keys():
		if key in existing:
			continue
		spec = feature_spec(key)
		frappe.get_doc({
			"doctype": "Alvoraa Module Price",
			"feature_key": key,
			"module_label": spec.get("label") or key,
			"basis": "Per named user" if spec.get("erpnext") else "PEPM",
			"status": "Built",
			# No rate. It shows in the console as built and unpriced, which is
			# the state that gets noticed - unlike simply being absent.
		}).insert(ignore_permissions=True)
		made += 1
	return made


def _sellable_registry_keys():
	"""Features a tenant can be charged for: everything the platform fee omits.

	Measured against PLATFORM_FEATURES rather than the registry's `required`
	flag. Onboarding & Exit is optional but included in the fee, so it needs no
	price of its own - and giving it one would list it as unpriced for ever.
	"""
	from alvoraa_portal.subscription import ERPNEXT_FEATURES
	keys = [k for k in FEATURES if k not in PLATFORM_FEATURES]
	keys += list(ERPNEXT_FEATURES.keys())
	return keys


@frappe.whitelist()
def sync_registry():
	"""Add a price row for anything the product gained since the last run."""
	_control_plane_only(_("Syncing the price list"))
	frappe.only_for("System Manager")
	made = _sync_registry_rows()
	if made:
		frappe.db.commit()
	return {"added": made}


# ── reading ──────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_price_catalogue(include_private=False):
	"""Everything the pricing screens render, in one call."""
	_control_plane_only(_("The price list"))
	frappe.only_for("System Manager")

	plan_filters = {"is_active": 1}
	if not frappe.parse_json(include_private or "false"):
		plan_filters["is_private"] = 0

	plans = frappe.get_all(
		"Alvoraa Plan", filters=plan_filters, order_by="sequence asc, band_from asc",
		fields=["name", "plan_name", "band_from", "band_to", "platform_fee",
		        "annual_fee", "included_employees", "additional_pepm",
		        "is_quote_only", "is_private", "built_for", "notes"])
	for plan in plans:
		plan["features"] = frappe.get_all(
			"Alvoraa Plan Feature", filters={"parent": plan["name"]},
			fields=["feature_key", "feature_label"], order_by="idx asc")

	packs = frappe.get_all(
		"Alvoraa Operations Pack", filters={"is_active": 1}, order_by="rate_per_user desc",
		fields=["name", "pack_name", "rate_per_user", "requires_pack"])
	for pack in packs:
		pack["features"] = frappe.get_all(
			"Alvoraa Pack Feature", filters={"parent": pack["name"]},
			fields=["feature_key", "feature_label"], order_by="idx asc")

	modules = frappe.get_all(
		"Alvoraa Module Price", order_by="status asc, module_label asc",
		fields=["name", "feature_key", "module_label", "rate", "basis", "status",
		        "pack", "is_sellable", "in_registry", "notes"])

	settings = frappe.get_single("Alvoraa Pricing Settings")
	return {
		"plans": plans,
		"packs": packs,
		"modules": modules,
		"pack_cap_per_user": flt(settings.pack_cap_per_user),
		"currency": settings.currency or "INR",
		"unpriced": [m["feature_key"] for m in modules
		             if m["status"] == "Built" and not m["rate"]],
	}


def plan_for_headcount(count):
	"""The public plan whose band contains `count`, or None.

	Private plans are never matched - they are chosen by name for one client.
	"""
	for plan in frappe.get_all(
			"Alvoraa Plan", filters={"is_active": 1, "is_private": 0},
			order_by="band_from asc",
			fields=["name", "band_from", "band_to"]):
		if count >= plan.band_from and (not plan.band_to or count <= plan.band_to):
			return plan.name
	return None


def pack_total_per_user(pack_names):
	"""What one named user costs across the packs they hold, cap applied."""
	if not pack_names:
		return 0.0
	rates = frappe.get_all("Alvoraa Operations Pack",
	                       filters={"name": ("in", list(pack_names))},
	                       pluck="rate_per_user")
	total = sum(flt(r) for r in rates)
	cap = flt(frappe.db.get_single_value("Alvoraa Pricing Settings", "pack_cap_per_user"))
	return min(total, cap) if cap else total
