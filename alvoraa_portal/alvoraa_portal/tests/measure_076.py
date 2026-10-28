"""Slice 076, Part A: what does Home cost before and after?

Run it on the OLD code and on the NEW code, on both fixture sites of slice 044
(20 people and 1,000), and compare:

    bench --site test076s execute alvoraa_portal.tests.measure_076.run --kwargs "{'shape':'small','which':'before'}"
    bench --site test076l execute alvoraa_portal.tests.measure_076.run --kwargs "{'shape':'large','which':'before'}"
    ... and the same with 'after' on the new code.

The calls are the ones Home makes. BEFORE: the check-in status, Activity, the
dashboard, documents, policies, the goals cards, the bell's goal count and the
bell's grooming notices. AFTER: the same minus Activity, the bell's goal count
and `my_notices`, plus `get_inbox` and `notices_feed` (which the bell shares).

The method is slice 044's (measure_044): every call warmed three times, then 20
runs; every SQL statement counted through `frappe.db.sql`; the payload measured
as JSON bytes. Nothing is written while measuring. Wall time varies more than
the effect on this machine, so a query count is the figure that proves flatness
and a time is a record, not a pass.
"""

import json

import frappe

from alvoraa_portal.tests.measure_044 import REPEATS, measure_one

HOME = {
	"before": (
		("get_checkin_status", "alvoraa_portal.hr_api", "get_checkin_status"),
		("get_portal_activity", "alvoraa_portal.hr_api", "get_portal_activity"),
		("get_employee_dashboard", "alvoraa_portal.hr_api", "get_employee_dashboard"),
		("get_my_documents", "alvoraa_portal.hr_api", "get_my_documents"),
		("get_my_policies", "alvoraa_portal.hr_api", "get_my_policies"),
		("get_goals_portal_data", "alvoraa_portal.hr_api", "get_goals_portal_data"),
		("get_team_goals", "alvoraa_portal.hr_api", "get_team_goals"),
		("bell: get_pending_approvals_count", "alvoraa_portal.goals_api", "get_pending_approvals_count"),
		("bell: grooming my_notices", "alvoraa_portal.grooming", "my_notices"),
	),
	"after": (
		("get_checkin_status", "alvoraa_portal.hr_api", "get_checkin_status"),
		("get_employee_dashboard", "alvoraa_portal.hr_api", "get_employee_dashboard"),
		("get_my_documents", "alvoraa_portal.hr_api", "get_my_documents"),
		("get_my_policies", "alvoraa_portal.hr_api", "get_my_policies"),
		("get_goals_portal_data", "alvoraa_portal.hr_api", "get_goals_portal_data"),
		("get_team_goals", "alvoraa_portal.hr_api", "get_team_goals"),
		("get_inbox (Pending)", "alvoraa_portal.inbox_api", "get_inbox"),
		("notices_feed (card and bell)", "alvoraa_portal.notices", "notices_feed"),
	),
}


def _thunk(module, name):
	mod = frappe.get_module(module)
	fn = getattr(mod, name, None)
	if fn is None:
		return None
	return lambda: fn()


def run(shape="small", which="after", repeats=REPEATS):
	from alvoraa_portal.tests import fixtures_scale_044 as fx

	people = fx.count_built(shape)
	print("\n%s %s: %d people on this site\n" % (which, shape, people), flush=True)
	out = {"shape": shape, "which": which, "people": people, "personas": {}}
	for persona, _roles in fx.PERSONAS:
		frappe.set_user(fx.login_of(shape, persona))
		frappe.local.request_ip = "127.0.0.1"
		row, total_q, total_bytes = {}, 0, 0
		for label, module, name in HOME[which]:
			thunk = _thunk(module, name)
			if thunk is None:
				row[label] = {"error": "no such function"}
				continue
			got = measure_one(thunk, repeats=int(repeats))
			row[label] = got
			if "error" not in got:
				total_q += got["queries_max"]
				total_bytes += got["bytes"] or 0
		row["TOTAL"] = {"queries": total_q, "bytes": total_bytes}
		out["personas"][persona] = row
		frappe.set_user("Administrator")
		print("%-10s total queries %-4s payload %6s bytes" % (persona, total_q, total_bytes), flush=True)
		for label, got in row.items():
			if label == "TOTAL":
				continue
			if "error" in got:
				print("    %-34s %s" % (label, got["error"]), flush=True)
			else:
				print("    %-34s q=%-3s p50=%-7s p95=%-7s bytes=%s" % (
					label, got["queries_max"], got["ms_p50"], got["ms_p95"], got["bytes"]), flush=True)
	path = frappe.get_site_path("private", "files", "measure_076_%s_%s.json" % (which, shape))
	with open(path, "w") as handle:
		json.dump(out, handle, indent=1, default=str)
	print("\nwritten: %s" % path, flush=True)
	return out


def where_queries_go(shape="large", persona="companyhr", call="get_inbox", top=8):
	"""The statements one call sends, grouped by their text with the values taken
	out, most repeated first. A count that moves with headcount shows up here as a
	statement sent once per row."""
	import re
	from collections import Counter

	from alvoraa_portal.tests import fixtures_scale_044 as fx
	from alvoraa_portal.tests.measure_044 import _Spy

	module = {"get_inbox": "alvoraa_portal.inbox_api", "notices_feed": "alvoraa_portal.notices"}[call]
	fn = getattr(frappe.get_module(module), call)
	frappe.set_user(fx.login_of(shape, persona))
	frappe.local.request_ip = "127.0.0.1"
	fn()
	with _Spy() as spy:
		fn()
	frappe.set_user("Administrator")
	shape_of = Counter(re.sub(r"\s+", " ", re.sub(r"'[^']*'|\b\d+\b", "?", q))[:150] for q in spy.statements)
	print("\n%s %s %s: %d statements" % (shape, persona, call, len(spy.statements)), flush=True)
	for text, n in shape_of.most_common(int(top)):
		print("  %3d x  %s" % (n, text), flush=True)


def compare_goal_approvals(shape="large"):
	"""Does the Team panel's 'Pending Progress Approvals' list show what Pending
	counts? Pending counts Goal Progress Updates and KPI Progress Log rows (the
	inbox); the Team panel lists goal evidence (hr_api.get_pending_approvals)."""
	from alvoraa_portal import hr_api, inbox_api
	from alvoraa_portal.tests import fixtures_scale_044 as fx

	for persona, _roles in fx.PERSONAS:
		frappe.set_user(fx.login_of(shape, persona))
		inbox = {p["key"]: p["count"] for p in inbox_api.get_inbox()["parts"]}["goal_updates"]
		team = hr_api.get_pending_approvals()
		print("%-10s inbox goal_updates=%-4s team panel: goals=%s kpis=%s" % (
			persona, inbox, len(team.get("goals", [])), len(team.get("kpis", []))), flush=True)
	frappe.set_user("Administrator")
