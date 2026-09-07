"""Subscriptions: adopting the tenants that already exist, and reading them back.

Stage two of the billing build. The price list says what things cost; this says
who is on what.

`adopt_existing_tenants()` is the migration. Every site already on disk gets a
subscription built from the module list its site_config.json actually records,
rather than from what anybody remembers agreeing. It leaves the plan blank and
says so in the notes, because the plan is a headcount band and nothing counts
employees until stage three - guessing that number is how a migration becomes a
billing dispute.

Every tenant today is ours, so every one comes out Internal: demo is the sales
demo, test_site is the bench the tests run on, dev is the development instance,
and allabouthr is where we run our own business. Internal means priced exactly
like a customer and never invoiced - allabouthr in particular is meant to carry
a real plan, so a change and its cost can be tried before a customer sees either.

Like everything else in billing, this refuses to run anywhere but the control
plane.
"""

import frappe
from frappe import _
from frappe.utils import flt, today

from alvoraa_portal.pricing import _control_plane_only, plan_for_headcount

# Ours, whatever their site_config says. Named here rather than guessed from the
# domain: a customer could perfectly well be called demo-something, and a rule
# that quietly stops billing a real customer is worse than one that misses.
OUR_OWN_SITES = {
	"demo.alvoraa.co": "the sales demo",
	"dev.alvoraa.co": "the development instance",
	"test_site": "the bench the tests run on",
	"allabouthr.dev.alvoraa.co": "where we run our own business, and the pricing bench",
}


@frappe.whitelist()
def adopt_existing_tenants(dry_run=True, headcounts=None):
	"""Create a subscription for every site that does not have one yet.

	`headcounts` is an optional {site: number} supplied by a person. Nothing
	counts employees until stage three, and a plan cannot be chosen without
	that number - see _proposed() for why guessing it is worse than leaving it
	blank.

	Runs safely more than once: an existing subscription is never touched, so
	anything corrected by hand stays corrected.
	"""
	_control_plane_only(_("Adopting tenants"))
	frappe.only_for("System Manager")
	dry_run = frappe.parse_json(dry_run) if isinstance(dry_run, str) else bool(dry_run)
	headcounts = frappe.parse_json(headcounts) if isinstance(headcounts, str) else (headcounts or {})

	from alvoraa_portal.tenant_api import list_tenants

	planned, skipped = [], []
	for tenant in list_tenants():
		site = tenant.get("site_name")
		if not site:
			continue
		if frappe.db.exists("Alvoraa Subscription", site):
			skipped.append({"site": site, "why": "already has a subscription"})
			continue
		planned.append(_proposed(site, tenant, headcounts.get(site)))

	created = []
	if not dry_run:
		for row in planned:
			created.append(_create(row))
		frappe.db.commit()

	return {"dry_run": dry_run, "created": created,
	        "planned": planned, "skipped": skipped}


def _proposed(site, tenant, headcount=None):
	"""What this site's subscription should look like, read from its own config.

	Two things this deliberately does NOT do.

	It does not map the old plan name onto a new plan. site_config records
	`subscription_plan` as starter, business, enterprise or custom - and those
	were FEATURE bundles. The new plans are HEADCOUNT bands that all carry the
	same features. A tenant on the old "enterprise" with twenty staff belongs in
	the new Starter band with add-ons, so carrying the name across would put
	them on a fee seven times too big. The old name goes in the notes, where a
	person can see it.

	And it does not guess a headcount. Nothing counts employees until stage
	three. A subscription with no plan is visibly unfinished; a subscription
	with a plan picked from a number nobody measured looks finished and bills
	the wrong amount.
	"""
	features = set(tenant.get("modules") or [])
	proposal = {
		"site": site,
		"status": "Internal" if site in OUR_OWN_SITES else "Trial",
		"why": OUR_OWN_SITES.get(site, "not a site we recognise as ours"),
		"old_plan_name": tenant.get("plan"),
		"headcount": headcount,
		"plan": plan_for_headcount(headcount) if headcount else None,
		"addons": [],
		"needs_a_human": [],
	}

	if not headcount:
		proposal["needs_a_human"].append(
			"no headcount, so no plan band can be matched - set one and re-run, "
			"or fill the plan in by hand")
	if not features:
		proposal["needs_a_human"].append(
			"records no module list, so it is currently getting whatever the code "
			"defaults to - which is not a product anybody sells")

	included = set()
	if proposal["plan"]:
		included = set(frappe.get_all("Alvoraa Plan Feature",
		                              filters={"parent": proposal["plan"]},
		                              pluck="feature_key"))

	for key in sorted(features - included):
		price = frappe.db.get_value("Alvoraa Module Price", key,
		                            ["rate", "is_sellable", "status"], as_dict=True)
		if not price:
			proposal["needs_a_human"].append(
				f"holds {key}, which is not in the price list")
		elif not price.is_sellable:
			proposal["needs_a_human"].append(
				f"holds {key}, which is marked {price.status} and cannot be sold")
		else:
			proposal["addons"].append({"feature_key": key,
			                           "agreed_rate": flt(price.rate)})

	return proposal


def _create(row):
	"""Record what is already true, even when it would not pass as a new sale."""
	doc = frappe.get_doc({
		"doctype": "Alvoraa Subscription",
		"site_name": row["site"],
		"status": row["status"],
		"plan": row["plan"],
		"billing_frequency": "Monthly",
		"started_on": today(),
		"addons": row["addons"],
		"notes": _notes(row),
	})
	try:
		doc.insert(ignore_permissions=True)
	except frappe.ValidationError as exc:
		# A live tenant may hold a combination the rules would refuse today -
		# a half dependency, a module since taken off sale. Refusing to RECORD
		# what is already running helps nobody and leaves the site unbilled and
		# invisible. So the subscription is created without the rows that failed,
		# and the reason is written where a person will read it.
		doc = frappe.get_doc({
			"doctype": "Alvoraa Subscription",
			"site_name": row["site"],
			"status": row["status"],
			"plan": row["plan"],
			"billing_frequency": "Monthly",
			"started_on": today(),
			"notes": _notes(row) + f"\n\nAdd-ons NOT carried over: {exc}",
		})
		doc.insert(ignore_permissions=True)
	return {"site": doc.site_name, "status": doc.status, "plan": doc.plan,
	        "addons": len(doc.addons)}


def _notes(row):
	lines = [f"Adopted {today()} from site_config.",
	         f"Plan name it recorded: {row['old_plan_name'] or 'none'} "
	         f"(a feature bundle under the old model, not a headcount band).",
	         f"Marked {row['status']} - {row['why']}."]
	if row["needs_a_human"]:
		lines += ["", "Needs a decision:"] + [f"  - {w}" for w in row["needs_a_human"]]
	return "\n".join(lines)


# ── reading ──────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_subscription(site):
	"""One tenant's subscription, with its rows resolved."""
	_control_plane_only(_("Subscriptions"))
	frappe.only_for("System Manager")
	if not frappe.db.exists("Alvoraa Subscription", site):
		return None
	doc = frappe.get_doc("Alvoraa Subscription", site)
	return {
		"site_name": doc.site_name,
		"status": doc.status,
		"customer": doc.customer,
		"plan": doc.plan,
		"billing_frequency": doc.billing_frequency,
		"implementation_fee": flt(doc.implementation_fee),
		"is_billable": doc.is_billable,
		"addons": [{"feature_key": r.feature_key, "module_label": r.module_label,
		            "basis": r.basis, "agreed_rate": flt(r.agreed_rate)}
		           for r in doc.addons],
		"packs": [{"pack": r.pack, "named_users": r.named_users,
		           "agreed_rate": flt(r.agreed_rate)} for r in doc.packs],
		"features": sorted(doc.selected_features()),
		"notes": doc.notes,
	}


@frappe.whitelist()
def list_subscriptions():
	"""Every subscription, with the internal ones plainly marked as ours."""
	_control_plane_only(_("Subscriptions"))
	frappe.only_for("System Manager")
	rows = frappe.get_all(
		"Alvoraa Subscription", order_by="status asc, site_name asc",
		fields=["name", "site_name", "status", "customer", "plan",
		        "billing_frequency", "implementation_fee"])
	for row in rows:
		row["is_ours"] = row["status"] == "Internal"
		row["addons"] = frappe.db.count("Alvoraa Subscription Addon",
		                                {"parent": row["name"]})
		row["packs"] = frappe.db.count("Alvoraa Subscription Pack",
		                               {"parent": row["name"]})
	return {
		"subscriptions": rows,
		"billable": len([r for r in rows if not r["is_ours"]]),
		"internal": len([r for r in rows if r["is_ours"]]),
		# Sites on disk with nothing recorded against them. A tenant that is
		# running and not on a subscription is either a missed bill or a
		# migration somebody did not finish.
		"unadopted": _sites_without_a_subscription(),
	}


def _sites_without_a_subscription():
	from alvoraa_portal.tenant_api import list_tenants

	have = set(frappe.get_all("Alvoraa Subscription", pluck="site_name"))
	out = []
	for tenant in list_tenants():
		site = tenant.get("site_name")
		if site and site not in have:
			out.append(site)
	return out
