"""Counting the two things every invoice multiplies by.

Stage three. The price list says what things cost and the subscription says who
is on what; neither knows how big anybody is. Nothing in the control plane has
ever needed to, so the number does not exist anywhere - and the bill is a
function of it.

Two counts, on different populations:

  Billable employees, for the platform fee and every per-employee add-on.
  Named users per pack, for the ERPNext packs, which are sold per person who
  can open them rather than per head.

This file has two halves that never run in the same place.

  measure_here()  runs ON a tenant site, invoked by the control plane through
                  `bench --site X execute`. It counts and prints. It writes
                  nothing and decides nothing.

  collect()       runs on the CONTROL PLANE. It calls the above for each
                  tenant, applies that tenant's exclusions, and writes one
                  Alvoraa Usage Record per site per month.

The split matters. Only the tenant's own database can count its employees, and
only the control plane knows what was sold. Keeping the judgement on the control
plane side means a tenant site cannot influence its own bill.

Month-end, not a daily average, and deliberately: it is the number a customer
disputing an invoice can check for themselves in one click.
"""

import json

import frappe
from frappe import _
from frappe.utils import now_datetime, nowdate

# bench execute prints whatever it likes around a return value, and the shape of
# that has changed between Frappe versions. A sentinel makes the parse immune to
# all of it, which matters more here than anywhere else in the system: this line
# becomes an invoice.
SENTINEL = "ALVORAA_USAGE_JSON "

# The only status that costs money. Everything else - Inactive, Suspended, Left -
# is a record HR keeps, not a person being served this month.
#
# Chosen for a commercial reason as much as a technical one: "Active employees"
# is one filter on the Employee list, so a customer who doubts the bill can
# check it themselves in about four seconds. A cleverer rule that nobody can
# verify costs more in support than it earns in revenue.
BILLABLE_STATUS = "Active"


# ── the tenant side ──────────────────────────────────────────────────────────

@frappe.whitelist()
def measure_here():
	"""Count this site. Runs on a tenant, writes nothing, decides nothing.

	Returns the raw counts and prints them behind a sentinel so the control
	plane can read them back out of bench's stdout.
	"""
	payload = {
		"site": frappe.local.site,
		"measured_at": str(now_datetime()),
		"employees": _employee_counts(),
		"users_by_module": _users_by_module(),
	}
	print(SENTINEL + json.dumps(payload, default=str))
	return payload


def _employee_counts():
	"""Employees by status, and Active broken down by employment type.

	Both, because the billable number is Active minus some employment types,
	and an invoice that cannot show its working is an invoice that gets argued
	about.
	"""
	by_status, by_type = {}, {}
	rows = frappe.get_all("Employee", fields=["status", "employment_type"],
	                      limit_page_length=0, ignore_permissions=True)
	for row in rows:
		status = row.status or "Unknown"
		by_status[status] = by_status.get(status, 0) + 1
		if status == BILLABLE_STATUS:
			kind = row.employment_type or "Unspecified"
			by_type[kind] = by_type.get(kind, 0) + 1
	return {"total": len(rows), "by_status": by_status,
	        "active_by_employment_type": by_type}


def _users_by_module():
	"""How many people could open each module on the day of the count.

	A user counts for a module when they are enabled, are a real desk user, and
	their profile does not block it. That is the same mechanism the desk itself
	uses, so this measures what a person would actually experience rather than
	what a role table implies.

	It is a check, not a charge. What gets billed is what the subscription says
	was agreed; this is here so a gap between the two is visible before a
	customer discovers it.
	"""
	users = frappe.get_all(
		"User", filters={"enabled": 1, "user_type": "System User"},
		fields=["name"], limit_page_length=0, ignore_permissions=True)
	if not users:
		return {}

	blocked = {}
	for row in frappe.get_all("Block Module", fields=["parent", "module"],
	                          limit_page_length=0, ignore_permissions=True):
		blocked.setdefault(row.parent, set()).add(row.module)

	names = {u.name for u in users} - {"Administrator", "Guest"}
	modules = frappe.get_all("Module Def", pluck="name", ignore_permissions=True)

	counts = {}
	for module in modules:
		n = sum(1 for user in names if module not in blocked.get(user, ()))
		if n:
			counts[module] = n
	return counts


# ── the control plane side ───────────────────────────────────────────────────

def _control_plane_only(what):
	from alvoraa_portal.pricing import _control_plane_only as guard

	guard(what)


@frappe.whitelist()
def collect(period=None, sites=None, timeout=120):
	"""Measure every subscribed tenant and write one record each.

	Safe to run again: a record for the same site and month is updated in place,
	never duplicated. So a month that failed halfway can simply be re-run.
	"""
	_control_plane_only(_("Collecting usage"))
	frappe.only_for("System Manager")
	period = period or nowdate()[:7]
	if isinstance(sites, str):
		sites = frappe.parse_json(sites)

	wanted = sites or frappe.get_all("Alvoraa Subscription", pluck="name")
	done, failed = [], []
	for site in wanted:
		try:
			done.append(measure_tenant(site, period, timeout=timeout))
		except Exception:
			failed.append({"site": site, "error": frappe.get_traceback(with_context=False)[-400:]})
			frappe.log_error(title=f"usage: could not measure {site}")
	frappe.db.commit()
	return {"period": period, "measured": done, "failed": failed}


def measure_tenant(site, period, timeout=120):
	"""Run the count on one tenant and write its record."""
	from alvoraa_portal.tenant_api import _bench_run

	result = _bench_run(f"--site {site} execute alvoraa_portal.usage.measure_here",
	                    timeout=timeout)
	payload, problem = _read_payload(result)
	return _write_record(site, period, payload, problem)


def _read_payload(result):
	"""Pull our JSON back out of bench's output, or say why we could not."""
	if result is None:
		return None, "bench returned nothing"
	blob = (getattr(result, "stdout", "") or "") + "\n" + (getattr(result, "stderr", "") or "")
	for line in blob.splitlines():
		if line.startswith(SENTINEL):
			try:
				return json.loads(line[len(SENTINEL):]), None
			except Exception as exc:
				return None, f"could not read the count: {exc}"
	if getattr(result, "returncode", 1) != 0:
		return None, (getattr(result, "stderr", "") or "bench failed")[-400:]
	return None, "the site produced no count - is the app installed there?"


def _write_record(site, period, payload, problem):
	name = f"{site} {period}"
	doc = (frappe.get_doc("Alvoraa Usage Record", name)
	       if frappe.db.exists("Alvoraa Usage Record", name)
	       else frappe.new_doc("Alvoraa Usage Record"))
	doc.site_name = site
	doc.period = period
	doc.counted_on = now_datetime()
	doc.source = "Measured"

	if problem or not payload:
		# A failed measurement is RECORDED, not swallowed. A month with no row
		# looks like a tenant nobody billed; a row saying the count failed looks
		# like something to go and fix.
		doc.ok = 0
		doc.error = problem or "no payload"
		doc.save(ignore_permissions=True)
		return {"site": site, "ok": False, "error": doc.error}

	employees = payload.get("employees") or {}
	excluded = _excluded_employment_types(site)
	active = (employees.get("active_by_employment_type") or {})
	billable = sum(n for kind, n in active.items() if kind not in excluded)

	doc.total_employees = employees.get("total") or 0
	doc.billable_employees = billable
	doc.breakdown = json.dumps({
		"by_status": employees.get("by_status") or {},
		"active_by_employment_type": active,
		"excluded_employment_types": sorted(excluded),
	}, indent=1)
	doc.set("packs", _pack_rows(site, payload.get("users_by_module") or {}))
	doc.ok = 1
	doc.error = None
	doc.save(ignore_permissions=True)
	return {"site": site, "ok": True, "billable_employees": billable,
	        "total_employees": doc.total_employees}


def _excluded_employment_types(site):
	"""Employment types this tenant does not pay for, one per line on their
	subscription. Empty means everybody Active counts."""
	raw = frappe.db.get_value("Alvoraa Subscription", site,
	                          "excluded_employment_types") or ""
	return {line.strip() for line in raw.splitlines() if line.strip()}


def _pack_rows(site, users_by_module):
	"""Agreed against measured, for each pack this tenant holds."""
	if not frappe.db.exists("Alvoraa Subscription", site):
		return []
	rows = []
	for held in frappe.get_all("Alvoraa Subscription Pack",
	                           filters={"parent": site},
	                           fields=["pack", "named_users"]):
		measured = _pack_user_count(held.pack, users_by_module)
		agreed = held.named_users or 0
		rows.append({"pack": held.pack, "agreed_users": agreed,
		             "measured_users": measured,
		             "over_by": max(0, measured - agreed)})
	return rows


def _pack_user_count(pack, users_by_module):
	"""The most people who can open ANY module in the pack.

	The most, not the total: one person with access to Accounts and Assets is
	one named user of Finance, not two. Taking the largest single module is the
	closest honest answer without pulling every user list back across the wire.
	"""
	from alvoraa_portal.subscription import feature_spec

	best = 0
	for key in frappe.get_all("Alvoraa Pack Feature", filters={"parent": pack},
	                          pluck="feature_key"):
		for module in feature_spec(key).get("module_defs") or []:
			best = max(best, users_by_module.get(module, 0))
	return best


def collect_scheduled():
	"""The monthly job. Counts the month that has just ended, not this one.

	Returns without a sound on a tenant site. The scheduler runs on every site
	we own, and a job that threw on each of them every month would fill the
	error log with the same non-problem until nobody read the error log.

	The month just ended, because a count taken on the 1st of a month is a count
	of nothing. Frappe runs monthly jobs at the start of the month, so the
	period being closed is the previous one.
	"""
	if frappe.conf.get("alvoraa_control_plane") is None:
		return
	from frappe.utils import add_months

	period = add_months(nowdate(), -1)[:7]
	frappe.set_user("Administrator")
	return collect(period=period)


# ── reading ──────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_usage(site, period=None):
	_control_plane_only(_("Usage"))
	frappe.only_for("System Manager")
	period = period or nowdate()[:7]
	name = f"{site} {period}"
	if not frappe.db.exists("Alvoraa Usage Record", name):
		return None
	doc = frappe.get_doc("Alvoraa Usage Record", name)
	return {
		"site_name": doc.site_name, "period": doc.period,
		"billable_employees": doc.billable_employees,
		"total_employees": doc.total_employees,
		"counted_on": str(doc.counted_on), "ok": bool(doc.ok), "error": doc.error,
		"source": doc.source,
		"breakdown": json.loads(doc.breakdown) if doc.breakdown else {},
		"packs": [{"pack": r.pack, "agreed_users": r.agreed_users,
		           "measured_users": r.measured_users, "over_by": r.over_by}
		          for r in doc.packs],
	}


@frappe.whitelist()
def usage_summary(period=None):
	"""Every tenant's count for a month, and everything the month is missing."""
	_control_plane_only(_("Usage"))
	frappe.only_for("System Manager")
	period = period or nowdate()[:7]

	records = frappe.get_all(
		"Alvoraa Usage Record", filters={"period": period}, order_by="site_name asc",
		fields=["site_name", "billable_employees", "total_employees", "ok",
		        "error", "source", "counted_on"])
	have = {r["site_name"] for r in records}
	subscribed = frappe.get_all("Alvoraa Subscription",
	                            fields=["name", "status"])
	return {
		"period": period,
		"records": records,
		# A subscription with no count cannot be invoiced. Named rather than
		# implied, because a missing row is exactly what nobody notices.
		"not_counted": sorted(s["name"] for s in subscribed if s["name"] not in have),
		"failed": [r["site_name"] for r in records if not r["ok"]],
		"billable_total": sum(r["billable_employees"] or 0 for r in records if r["ok"]),
	}
