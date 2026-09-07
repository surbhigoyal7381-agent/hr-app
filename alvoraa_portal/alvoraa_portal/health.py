"""Knowing a tenant is broken before they ring.

Frappe writes errors to an Error Log on the site where they happened. So a
tenant's errors live on the tenant's site, and the control plane cannot see
them. Today, if a customer's payroll breaks at two in the morning, we find out
when somebody telephones.

This pulls two signals up to the control plane, once a day:

  How many errors, of how many different kinds, and what they are called. One
  error a thousand times is a bug; a thousand different errors is a site
  falling over. The two need different reactions, so the count alone is not
  enough.

  Whether background work is actually running. With the scheduler off, nothing
  happens by itself on that tenant - no payroll, no leave allocation, no
  reminders, no invoice run. It fails silently and looks completely normal from
  the front, which is exactly what makes it worth watching. A scheduler that is
  switched ON but has not run for two days is the same failure wearing a
  disguise, so the last run time is collected as well as the flag.

**What is deliberately NOT collected: the tracebacks.**

A Frappe traceback carries whatever was in memory when it broke - an employee's
name, a salary, an email address, the contents of the record being saved. That
is our customer's employees' personal data, and moving it onto a machine they
did not agree to is a real problem under the DPDP Act, not a theoretical one.
It would also make the control plane the single most sensitive database we own,
protected for the sake of a diagnostic convenience.

So we take titles and counts. "ZeroDivisionError" or "Salary Slip: could not
submit" tells you which tenant to look at and how urgently. Then you open that
tenant's own Error Log and read the detail there, where it already lives and
where the customer's own administrators can see you doing it.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime, nowdate, time_diff_in_hours

from alvoraa_portal.pricing import _control_plane_only
from alvoraa_portal.usage import _read_payload

SENTINEL = "ALVORAA_HEALTH_JSON "

# Enough to see the shape of a bad day without turning the health record into a
# second error log.
TOP_N = 8


# ── the tenant side ──────────────────────────────────────────────────────────

@frappe.whitelist()
def check_here():
	"""Report this site's health. Runs on a tenant; reads only, sends no detail."""
	payload = {
		"site": frappe.local.site,
		"checked_at": str(now_datetime()),
		"errors": _error_counts(),
		"scheduler": _scheduler_state(),
	}
	print(SENTINEL + json.dumps(payload, default=str))
	return payload


def _error_counts():
	day = add_days(nowdate(), -1)
	week = add_days(nowdate(), -7)

	recent = frappe.get_all(
		"Error Log", filters={"creation": (">", week)},
		fields=["method", "creation"], limit_page_length=0, ignore_permissions=True)

	by_title = {}
	for row in recent:
		# `method` is Frappe's own one-line title for the failure. The traceback
		# is in `error`, and it is not read here or anywhere else in this file.
		title = (row.method or "Unknown")[:140]
		seen = by_title.setdefault(title, {"count": 0, "last_seen": None})
		seen["count"] += 1
		if not seen["last_seen"] or str(row.creation) > seen["last_seen"]:
			seen["last_seen"] = str(row.creation)

	top = sorted(by_title.items(), key=lambda kv: -kv[1]["count"])[:TOP_N]
	return {
		"last_24h": len([r for r in recent if str(r.creation) > str(day)]),
		"last_7d": len(recent),
		"distinct": len(by_title),
		"top": [{"title": t, "count": v["count"], "last_seen": v["last_seen"]}
		        for t, v in top],
	}


def _scheduler_state():
	last = frappe.db.get_value("Scheduled Job Log", {}, "creation",
	                           order_by="creation desc")
	# Frappe's own answer, not our reading of one flag. A scheduler can be off
	# for several unrelated reasons - paused on the site, paused across the
	# bench, maintenance mode, developer mode - and checking one of them would
	# report a site as healthy while nothing ran on it.
	try:
		from frappe.utils.scheduler import is_scheduler_inactive

		enabled = not is_scheduler_inactive(verbose=False)
	except Exception:
		# A future Frappe may move this. Better to say "unknown" by way of the
		# last-run time than to have the whole health check fail on one signal.
		enabled = None

	return {"enabled": enabled, "last_job": str(last) if last else None}


# ── the control plane side ───────────────────────────────────────────────────

@frappe.whitelist()
def collect(sites=None, timeout=90):
	"""Check every tenant and write one health record each, for today."""
	_control_plane_only(_("Checking tenant health"))
	frappe.only_for("System Manager")
	if isinstance(sites, str):
		sites = frappe.parse_json(sites)

	from alvoraa_portal.tenant_api import list_tenants

	wanted = sites or [t["site_name"] for t in list_tenants()]
	out = []
	for site in wanted:
		try:
			out.append(check_tenant(site, timeout=timeout))
		except Exception:
			out.append(_write(site, None, frappe.get_traceback(with_context=False)[-300:]))
			frappe.log_error(title=f"health: could not check {site}")
	frappe.db.commit()
	return {"date": nowdate(), "checked": out}


def check_tenant(site, timeout=90):
	from alvoraa_portal.tenant_api import _bench_run

	result = _bench_run(f"--site {site} execute alvoraa_portal.health.check_here",
	                    timeout=timeout)
	# One parser, tested once, shared with the usage collector - bench has
	# changed the shape of its output between Frappe versions and neither caller
	# should have to learn that twice.
	payload, problem = _read_payload(result, sentinel=SENTINEL)
	return _write(site, payload, problem)


def _write(site, payload, problem):
	name = f"{site} {nowdate()}"
	doc = (frappe.get_doc("Alvoraa Tenant Health", name)
	       if frappe.db.exists("Alvoraa Tenant Health", name)
	       else frappe.new_doc("Alvoraa Tenant Health"))
	doc.site_name = site
	doc.on_date = nowdate()
	doc.checked_at = now_datetime()

	if problem or not payload:
		# A site that cannot be reached is the loudest signal this file
		# collects, so it is recorded as a row rather than dropped.
		doc.ok = 0
		doc.error = problem or "no answer"
		doc.save(ignore_permissions=True)
		return {"site": site, "ok": False, "error": doc.error}

	errors = payload.get("errors") or {}
	sched = payload.get("scheduler") or {}
	doc.ok = 1
	doc.error = None
	doc.errors_24h = errors.get("last_24h") or 0
	doc.errors_7d = errors.get("last_7d") or 0
	doc.distinct_kinds = errors.get("distinct") or 0
	doc.set("top_errors", [
		{"title": e.get("title"), "count": e.get("count"), "last_seen": e.get("last_seen")}
		for e in (errors.get("top") or [])])
	doc.scheduler_enabled = 1 if sched.get("enabled") else 0
	doc.last_job = sched.get("last_job")
	doc.hours_since_job = (
		int(time_diff_in_hours(now_datetime(), sched["last_job"]))
		if sched.get("last_job") else 0)
	doc.save(ignore_permissions=True)
	return {"site": site, "ok": True, "errors_24h": doc.errors_24h,
	        "scheduler_enabled": bool(doc.scheduler_enabled)}


def collect_scheduled():
	"""The daily job. Silent on a tenant - only the control plane has anything
	to check, and a job that threw on every site every day would fill the error
	log with the same non-problem until nobody read the error log."""
	if frappe.conf.get("alvoraa_control_plane") is None:
		return
	frappe.set_user("Administrator")
	return collect()


# ── reading ──────────────────────────────────────────────────────────────────

# Above this, a tenant is having a bad day rather than a normal one. Round and
# arbitrary on purpose: the point is to sort the list, not to be a diagnosis.
NOISY = 25

# A scheduler that has not run in this long is stalled, whatever its flag says.
STALLED_HOURS = 6


@frappe.whitelist()
def health_summary(on_date=None):
	"""Every tenant's health for a day, worst first."""
	_control_plane_only(_("Tenant health"))
	frappe.only_for("System Manager")
	on_date = on_date or nowdate()

	rows = frappe.get_all(
		"Alvoraa Tenant Health", filters={"on_date": on_date},
		fields=["name", "site_name", "ok", "error", "errors_24h", "errors_7d",
		        "distinct_kinds", "scheduler_enabled", "hours_since_job",
		        "last_job", "checked_at"])

	for row in rows:
		row["stalled"] = bool(row["ok"] and row["scheduler_enabled"]
		                      and row["hours_since_job"] > STALLED_HOURS)
		row["noisy"] = bool(row["ok"] and row["errors_24h"] > NOISY)
		row["needs_attention"] = bool(
			not row["ok"] or row["stalled"] or row["noisy"]
			or (row["ok"] and not row["scheduler_enabled"]))
		row["top_errors"] = frappe.get_all(
			"Alvoraa Tenant Error", filters={"parent": row["name"]},
			fields=["title", "count", "last_seen"], order_by="count desc")

	# Worst first. A list sorted by name makes the one broken tenant as easy to
	# miss as if it were not there.
	rows.sort(key=lambda r: (not r["needs_attention"], -(r["errors_24h"] or 0)))

	from alvoraa_portal.tenant_api import list_tenants

	seen = {r["site_name"] for r in rows}
	return {
		"on_date": on_date,
		"tenants": rows,
		"needs_attention": [r["site_name"] for r in rows if r["needs_attention"]],
		# Never checked today. A tenant missing from a health report looks
		# exactly like a healthy one.
		"not_checked": sorted(t["site_name"] for t in list_tenants()
		                      if t["site_name"] not in seen),
	}
