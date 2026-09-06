"""Turning an estimate into an ERPNext Sales Invoice.

Stage five, and the last one. Everything before this produced numbers; this
produces a document with legal weight.

Three decisions shape the whole file.

**Drafts, never submitted.** Submitting a Sales Invoice posts it to the ledger,
and on the control plane - where india_compliance is installed - it can also
transmit an e-invoice to the government and pull an IRN back. That is not
something a scheduled job should do at two in the morning on its own judgement.
A draft is reviewed by a person who then submits it. The cost of that is a few
minutes a month; the cost of the alternative is a wrong invoice that has already
been filed.

**One invoice per site per month, and the record proves it.** The link is stored
on the usage record, which already exists once per site per month. So a second
run finds the invoice and skips, and nobody can be billed twice for August by
running the job again. No custom fields on Sales Invoice, no parallel ledger of
what we have billed - the row that produced the number holds the link to it.

**Nothing incomplete is invoiced.** If the estimate could not be finished, no
invoice is raised and the reason is reported. An invoice built on a missing
count is worse than a late one.

ERPNext does the rest: numbering, tax, the customer's GSTIN and place of supply,
the accounting entries. We supply lines and a customer.
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, get_last_day, nowdate

from alvoraa_portal.estimate import ANNUAL, estimate
from alvoraa_portal.pricing import _control_plane_only

# The service items every subscription line is billed against. Four, not one per
# module: a customer reading their invoice wants to see "Payroll" in the
# description, not to hunt through a list of forty item codes.
ITEMS = {
	"platform": ("Alvoraa Platform Fee", "Subscription platform fee"),
	"employees": ("Alvoraa Additional Employees", "Employees above the plan's included count"),
	"module": ("Alvoraa Module", "Add-on module subscription"),
	"packs": ("Alvoraa Operations Packs", "ERPNext operations packs, per named user"),
	"setup": ("Alvoraa Implementation", "One-time implementation and onboarding"),
}
ITEM_GROUP = "Services"


@frappe.whitelist()
def raise_invoices(period=None, dry_run=True, sites=None):
	"""Draft an invoice for every tenant that is ready for one.

	Safe to run again: a month already invoiced is skipped, not billed twice.
	"""
	_control_plane_only(_("Invoicing"))
	frappe.only_for("System Manager")
	period = period or _last_month()
	dry_run = frappe.parse_json(dry_run) if isinstance(dry_run, str) else bool(dry_run)
	if isinstance(sites, str):
		sites = frappe.parse_json(sites)

	wanted = sites or frappe.get_all("Alvoraa Subscription", pluck="name")
	drafted, skipped, failed = [], [], []

	for site in wanted:
		verdict = _should_invoice(site, period)
		if verdict["skip"]:
			skipped.append({"site": site, "why": verdict["why"]})
			continue
		if dry_run:
			drafted.append({"site": site, "customer": verdict["estimate"]["customer"],
			                "amount": verdict["estimate"]["totals"]["due_this_period"],
			                "lines": len(verdict["estimate"]["lines"]), "draft": None})
			continue
		try:
			drafted.append(_draft(site, period, verdict["estimate"]))
		except Exception:
			failed.append({"site": site,
			               "error": frappe.get_traceback(with_context=False)[-400:]})
			frappe.log_error(title=f"invoicing: could not draft for {site}")

	if not dry_run:
		frappe.db.commit()
	return {"period": period, "dry_run": dry_run, "drafted": drafted,
	        "skipped": skipped, "failed": failed,
	        "total": sum(flt(d.get("amount")) for d in drafted)}


def _should_invoice(site, period):
	"""Everything that stops an invoice, checked before anything is created."""
	sub = frappe.db.get_value("Alvoraa Subscription", site,
	                          ["status", "customer"], as_dict=True)
	if not sub:
		return {"skip": True, "why": "no subscription"}
	if sub.status == "Internal":
		return {"skip": True, "why": "ours - priced but never invoiced"}
	if sub.status == "Cancelled":
		return {"skip": True, "why": "cancelled"}
	if not sub.customer:
		return {"skip": True, "why": "no customer to invoice"}

	existing = _existing_invoice(site, period)
	if existing:
		return {"skip": True, "why": f"already invoiced as {existing}"}

	out = estimate(site, period)
	if not out["complete"]:
		# Better a late invoice than one built on a number nobody measured.
		return {"skip": True, "why": "; ".join(out["why_not"])}
	if flt(out["totals"]["due_this_period"]) <= 0:
		return {"skip": True, "why": "nothing to charge this month"}
	return {"skip": False, "estimate": out}


def _existing_invoice(site, period):
	"""The invoice already raised for this month, if it still stands.

	A CANCELLED invoice does not count. Somebody cancelled it deliberately, and
	the whole reason to cancel one is to raise it again.
	"""
	name = frappe.db.get_value("Alvoraa Usage Record", f"{site} {period}",
	                           "sales_invoice")
	if not name or not frappe.db.exists("Sales Invoice", name):
		return None
	return None if frappe.db.get_value("Sales Invoice", name, "docstatus") == 2 else name


def _draft(site, period, out):
	company = _company()
	posting = get_last_day(f"{period}-01")
	terms = frappe.db.get_single_value("Alvoraa Pricing Settings",
	                                   "payment_terms_days") or 15

	doc = frappe.new_doc("Sales Invoice")
	doc.customer = out["customer"]
	doc.company = company
	doc.posting_date = posting
	doc.set_posting_time = 1
	doc.due_date = add_days(posting, int(terms))
	doc.remarks = _remarks(site, period, out)

	for line in out["lines"]:
		if line["recurs"] == ANNUAL:
			# Belongs to the invoice for the year it covers, not to this month.
			continue
		doc.append("items", {
			"item_code": _item_for(line),
			"item_name": line["what"][:140],
			"description": f"{line['what']} - {line['detail']}",
			"qty": line["qty"] or 1,
			"rate": line["rate"],
			"uom": "Nos",
		})

	if not doc.items:
		frappe.throw(_("Nothing to invoice for {0} in {1}.").format(site, period))

	doc.selling_price_list = _price_list()
	# Let ERPNext fill in what ERPNext owns: currency, conversion rates, income
	# accounts, cost centres, tax templates. Hand-building those is how a
	# subscription invoice ends up posting somewhere nobody expected.
	doc.set_missing_values()

	doc.insert(ignore_permissions=True)     # DRAFT. A person submits it.

	frappe.db.set_value("Alvoraa Usage Record", f"{site} {period}",
	                    "sales_invoice", doc.name, update_modified=False)
	return {"site": site, "customer": doc.customer, "draft": doc.name,
	        "amount": flt(doc.grand_total) or flt(out["totals"]["due_this_period"]),
	        "lines": len(doc.items)}


def _remarks(site, period, out):
	"""The working, written onto the invoice itself.

	A customer querying a bill should find the answer on the document rather
	than by ringing us. The headcount is the number they will ask about, so it
	goes on first.
	"""
	lines = [f"Alvoraa subscription for {period}.", f"Tenant: {site}."]
	if out.get("billable_employees") is not None:
		lines.append(f"Billable employees counted at month end: "
		             f"{out['billable_employees']}.")
	for line in out["lines"]:
		if line["recurs"] != ANNUAL:
			lines.append(f"  {line['what']}: {line['detail']}")
	return "\n".join(lines)


def _item_for(line):
	what = line["what"]
	if what.endswith("platform fee"):
		key = "platform"
	elif what.startswith("Additional employees"):
		key = "employees"
	elif what.startswith("Operations packs"):
		key = "packs"
	elif what.startswith("Implementation"):
		key = "setup"
	else:
		key = "module"
	return ensure_item(key)


def ensure_item(key):
	"""Create the service item once, then reuse it.

	Non-stock and a service: an invoice line for a subscription must never look
	to ERPNext like something that moves in and out of a warehouse.
	"""
	code, description = ITEMS[key]
	if frappe.db.exists("Item", code):
		return code

	item = frappe.get_doc({
		"doctype": "Item", "item_code": code, "item_name": code,
		"item_group": _item_group(), "stock_uom": "Nos",
		"is_stock_item": 0, "is_sales_item": 1, "is_purchase_item": 0,
		"description": description,
		"gst_hsn_code": frappe.db.get_single_value("Alvoraa Pricing Settings",
		                                           "sac_code") or "997331",
	})
	# gst_hsn_code only exists where india_compliance is installed. It is on the
	# control plane and not on a plain bench, and an item that cannot be created
	# is worse than one missing a tax code somebody can add later.
	if not item.meta.has_field("gst_hsn_code"):
		item.gst_hsn_code = None
	item.insert(ignore_permissions=True)
	return code


def _price_list():
	"""The selling price list to bill against, found rather than assumed.

	ERPNext takes this from Selling Settings, and a site where the setup wizard
	never ran has none - which surfaces as a mandatory-field error on the
	invoice rather than as anything about price lists.

	We do not use it for prices; every rate comes from the subscription. It is
	here because ERPNext requires one, and because it carries the currency.
	"""
	chosen = frappe.db.get_single_value("Selling Settings", "selling_price_list")
	if chosen and frappe.db.exists("Price List", chosen):
		return chosen
	existing = frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Price List", "price_list_name": "Standard Selling",
		"selling": 1, "enabled": 1,
		"currency": frappe.db.get_default("currency") or "INR",
	}).insert(ignore_permissions=True)
	return doc.name


def _item_group():
	"""Where our service items live, found rather than assumed.

	`All Item Groups` is ERPNext's root on a site where its setup wizard ran.
	It is NOT there on every site - a bench built for something else may have a
	single flat group and no tree at all - and assuming it made every invoice
	fail with "Could not find Parent Item Group".

	So: use ours if it exists, create it under whatever the real root turns out
	to be, and if there is no tree at all, reuse a group that is already there.
	Building a root on a site that has none would fight whoever set it up that
	way, and organising the item tree was never our job.
	"""
	if frappe.db.exists("Item Group", ITEM_GROUP):
		return ITEM_GROUP

	root = frappe.db.get_value("Item Group", {"is_group": 1,
	                                          "parent_item_group": ("in", ["", None])},
	                           "name")
	if root:
		frappe.get_doc({"doctype": "Item Group", "item_group_name": ITEM_GROUP,
		                "parent_item_group": root, "is_group": 0}
		               ).insert(ignore_permissions=True)
		return ITEM_GROUP

	existing = frappe.db.get_value("Item Group", {}, "name")
	if existing:
		return existing
	frappe.throw(_("This site has no item groups, so a service item cannot be "
	               "created. Run the ERPNext setup wizard first."))


def _company():
	chosen = frappe.db.get_single_value("Alvoraa Pricing Settings", "invoice_company")
	if chosen:
		return chosen
	default = frappe.defaults.get_user_default("Company") or frappe.db.get_default("Company")
	if default:
		return default
	companies = frappe.get_all("Company", pluck="name", limit=2)
	if len(companies) == 1:
		return companies[0]
	frappe.throw(
		_("There is more than one company on this site, so the invoice has no "
		  "obvious sender. Set 'Invoice From' in Alvoraa Pricing Settings."),
		title=_("Which company is billing?"))


def _last_month():
	from frappe.utils import add_months

	return add_months(nowdate(), -1)[:7]


# ── reading ──────────────────────────────────────────────────────────────────

@frappe.whitelist()
def invoice_run_summary(period=None):
	"""What a month's billing looks like: raised, waiting, and blocked."""
	_control_plane_only(_("Invoicing"))
	frappe.only_for("System Manager")
	period = period or _last_month()

	raised, waiting = [], []
	for site in frappe.get_all("Alvoraa Subscription", pluck="name"):
		invoice = _existing_invoice(site, period)
		if invoice:
			doc = frappe.db.get_value(
				"Sales Invoice", invoice,
				["grand_total", "docstatus", "customer", "outstanding_amount"],
				as_dict=True)
			raised.append({
				"site": site, "invoice": invoice, "customer": doc.customer,
				"amount": flt(doc.grand_total),
				# Drafted, submitted or cancelled - in the customer's words,
				# because "docstatus 1" means nothing to anybody.
				"state": {0: "draft", 1: "sent", 2: "cancelled"}.get(doc.docstatus),
				"outstanding": flt(doc.outstanding_amount),
			})
		else:
			verdict = _should_invoice(site, period)
			waiting.append({"site": site, "why": verdict["why"] if verdict["skip"]
			                else "ready to raise",
			                "ready": not verdict["skip"]})

	return {
		"period": period,
		"raised": raised,
		"waiting": waiting,
		"drafted_value": sum(r["amount"] for r in raised if r["state"] == "draft"),
		"sent_value": sum(r["amount"] for r in raised if r["state"] == "sent"),
		"ready_to_raise": len([w for w in waiting if w["ready"]]),
	}
