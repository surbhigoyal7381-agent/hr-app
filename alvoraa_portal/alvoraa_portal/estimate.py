"""What a tenant owes for a month, and the working behind it.

Stage four. The price list says what things cost, the subscription says who is
on what, the usage record says how big they are. This multiplies them.

Nothing here writes an invoice. It produces a set of lines that a person can
read, argue with, and check - which is the whole point. An estimate a customer
cannot follow is an estimate that turns into a phone call, and by then the
number is already on their desk.

Two rules the whole file follows.

  It never guesses. A month with no count produces no figure at all, and says
  so. Treating a missing count as zero employees is a free month nobody would
  notice - and would look exactly like a correct invoice.

  It prices internal tenants in full. They are ours and never invoiced, but
  allabouthr exists to show what a change costs before a customer sees it, and
  a bench that does not compute is not a bench.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate

from alvoraa_portal.pricing import _control_plane_only

# How often a line is charged. Kept apart rather than summed together, because
# a yearly platform fee and a monthly add-on land on different invoices and
# adding them into one number is how a customer gets billed twelve times for
# something they pay for once.
MONTHLY = "monthly"
ANNUAL = "annual"
ONE_TIME = "one-time"


@frappe.whitelist()
def estimate(site, period=None):
	"""One tenant's charges for one month, line by line."""
	_control_plane_only(_("Estimates"))
	frappe.only_for("System Manager")
	period = period or nowdate()[:7]

	if not frappe.db.exists("Alvoraa Subscription", site):
		return {"site": site, "period": period, "complete": False,
		        "why_not": ["no subscription"], "lines": [], "totals": _empty_totals()}

	sub = frappe.get_doc("Alvoraa Subscription", site)
	usage = _usage(site, period)

	lines, missing = [], []
	if usage is None:
		missing.append(f"no usage count for {period}, so nothing per-employee can "
		               f"be worked out")
	elif not usage.ok:
		missing.append(f"the count for {period} failed: {usage.error or 'unknown'}")

	heads = cint(usage.billable_employees) if (usage and usage.ok) else None

	lines += _plan_lines(sub, heads, missing)
	lines += _addon_lines(sub, heads, missing)
	lines += _pack_lines(sub)
	lines += _one_time_lines(sub, period)

	return {
		"site": site,
		"period": period,
		"status": sub.status,
		"customer": sub.customer,
		"plan": sub.plan,
		"billing_frequency": sub.billing_frequency,
		"billable_employees": heads,
		# Priced either way; invoiced only if it is not ours.
		"will_be_invoiced": bool(sub.is_billable),
		"complete": not missing,
		"why_not": missing,
		"lines": lines,
		"totals": _totals(lines),
	}


# ── the platform fee ─────────────────────────────────────────────────────────

def _plan_lines(sub, heads, missing):
	if not sub.plan:
		missing.append("no plan, so there is no platform fee to charge")
		return []

	plan = frappe.get_doc("Alvoraa Plan", sub.plan)
	if plan.is_quote_only:
		missing.append(f"{plan.name} is quote only - the fee was negotiated and "
		               f"has to be entered by hand")
		return []

	annual = sub.billing_frequency == "Annual"
	fee = flt(plan.annual_fee) if annual else flt(plan.platform_fee)
	lines = [_line(
		what=f"{plan.name} platform fee",
		detail=(f"{plan.band_from} to {plan.band_to or 'any'} employees, "
		        f"{plan.included_employees} included"),
		qty=1, rate=fee, recurs=ANNUAL if annual else MONTHLY)]

	# Above the included headcount, every extra person is charged. Below it,
	# nothing - the fee already covers them.
	if heads is None:
		return lines
	over = heads - cint(plan.included_employees)
	if over > 0 and flt(plan.additional_pepm):
		lines.append(_line(
			what="Additional employees",
			detail=(f"{heads} counted, {plan.included_employees} included in the fee, "
			        f"so {over} extra"),
			qty=over, rate=flt(plan.additional_pepm), recurs=MONTHLY))
	return lines


# ── add-ons ──────────────────────────────────────────────────────────────────

def _addon_lines(sub, heads, missing):
	lines = []
	for row in sub.addons:
		rate = flt(row.agreed_rate)
		label = row.module_label or row.feature_key
		basis = row.basis or "PEPM"

		if basis == "PEPM":
			if heads is None:
				continue      # already explained once, in `missing`
			lines.append(_line(what=label, detail=f"{heads} employees at {rate}",
			                   qty=heads, rate=rate, recurs=MONTHLY))
		elif basis == "Per organisation":
			lines.append(_line(what=label, detail="per organisation",
			                   qty=1, rate=rate, recurs=MONTHLY))
		elif basis == "One-time":
			# Charged when it is delivered, not every month for ever. Stage five
			# decides which invoice it lands on.
			continue
		else:
			# Per named user, per device and usage all need a quantity nothing
			# measures yet. Named rather than silently priced at zero, because a
			# line quietly missing from an invoice is worse than one flagged.
			missing.append(f"{label} is charged {basis.lower()}, and nothing counts "
			               f"that yet - add it by hand")
	return lines


# ── operations packs ─────────────────────────────────────────────────────────

def _pack_lines(sub):
	"""Packs, with the per-user cap applied the way a person would apply it.

	The cap is per USER across every pack they hold, and counts alone cannot say
	which people overlap. So we assume the most overlap: the users of a smaller
	pack are the same people who hold the bigger one. That is the reading most
	favourable to the customer and the easiest to say out loud - the same staff
	use the packs, and nobody pays more than the cap.

	Worked on a real shape. Finance 5 users at 300, Trade 3 at 250,
	Manufacturing 2 at 250, cap 799:

	    users 1 and 2   hold all three   800 -> capped to 799
	    user 3          Finance + Trade  550
	    users 4 and 5   Finance only     300 each

	2,748 rather than 2,750. The cap rarely bites, and that is fine: it exists
	so nobody can be quoted an absurd number, not to be a discount.
	"""
	held = [(r.pack, cint(r.named_users), flt(r.agreed_rate)) for r in sub.packs
	        if cint(r.named_users) > 0]
	if not held:
		return []

	cap = flt(frappe.db.get_single_value("Alvoraa Pricing Settings",
	                                     "pack_cap_per_user"))
	most = max(n for _, n, _ in held)

	total, capped_users = 0.0, 0
	for seat in range(1, most + 1):
		# This seat holds every pack that has at least this many users.
		per_user = sum(rate for _, n, rate in held if n >= seat)
		if cap and per_user > cap:
			per_user = cap
			capped_users += 1
		total += per_user

	detail = ", ".join(f"{pack} {n} at {rate:g}" for pack, n, rate in held)
	if capped_users:
		detail += f" - {capped_users} user(s) capped at {cap:g}"
	return [_line(what="Operations packs", detail=detail,
	              qty=most, rate=total / most if most else 0,
	              recurs=MONTHLY, amount=total)]


# ── one-time ─────────────────────────────────────────────────────────────────

def _one_time_lines(sub, period):
	"""The implementation fee, on the first month only.

	`started_on` is what decides it, not a flag somebody has to remember to
	clear - a flag gets missed and the customer is charged setup twice.
	"""
	fee = flt(sub.implementation_fee)
	if not fee or not sub.started_on:
		return []
	if str(sub.started_on)[:7] != period:
		return []
	return [_line(what="Implementation", detail=f"one time, started {sub.started_on}",
	              qty=1, rate=fee, recurs=ONE_TIME)]


# ── shaping ──────────────────────────────────────────────────────────────────

def _line(what, detail, qty, rate, recurs, amount=None):
	return {"what": what, "detail": detail, "qty": qty, "rate": flt(rate),
	        "recurs": recurs,
	        "amount": flt(amount if amount is not None else flt(qty) * flt(rate))}


def _empty_totals():
	return {MONTHLY: 0.0, ANNUAL: 0.0, ONE_TIME: 0.0, "due_this_period": 0.0}


def _totals(lines):
	out = _empty_totals()
	for line in lines:
		out[line["recurs"]] += line["amount"]
	# What actually goes on this month's invoice: everything monthly, plus
	# anything one-off that falls in it. An annual fee is deliberately NOT added
	# in - it belongs to the invoice for the year it covers, and adding it here
	# would show a customer a monthly figure twelve times too big.
	out["due_this_period"] = out[MONTHLY] + out[ONE_TIME]
	return out


def _usage(site, period):
	name = f"{site} {period}"
	if not frappe.db.exists("Alvoraa Usage Record", name):
		return None
	return frappe.get_doc("Alvoraa Usage Record", name)


# ── everybody at once ────────────────────────────────────────────────────────

@frappe.whitelist()
def estimate_all(period=None):
	"""Every tenant's charges for a month, and everything stopping a bill."""
	_control_plane_only(_("Estimates"))
	frappe.only_for("System Manager")
	period = period or nowdate()[:7]

	rows, blocked = [], []
	revenue = 0.0
	for site in frappe.get_all("Alvoraa Subscription", pluck="name"):
		one = estimate(site, period)
		rows.append({"site": site, "status": one["status"], "plan": one["plan"],
		             "billable_employees": one["billable_employees"],
		             "due": one["totals"]["due_this_period"],
		             "will_be_invoiced": one["will_be_invoiced"],
		             "complete": one["complete"]})
		if not one["complete"]:
			blocked.append({"site": site, "why": one["why_not"]})
		if one["will_be_invoiced"] and one["complete"]:
			revenue += one["totals"]["due_this_period"]

	return {
		"period": period,
		"tenants": rows,
		# Only what will really be invoiced. Internal tenants are priced in the
		# rows above so the bench works, and left out of the total so the figure
		# is one we could actually bank.
		"invoiceable_total": revenue,
		"blocked": blocked,
		"ready": len([r for r in rows if r["complete"] and r["will_be_invoiced"]]),
	}
