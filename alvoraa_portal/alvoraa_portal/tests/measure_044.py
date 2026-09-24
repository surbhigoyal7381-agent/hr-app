"""Slice 044: measure the portal's landing calls against a real headcount.

Run it, do not guess:

    bench --site test044  execute alvoraa_portal.tests.measure_044.run \
          --kwargs "{'shape':'large'}"
    bench --site test044s execute alvoraa_portal.tests.measure_044.run \
          --kwargs "{'shape':'small'}"

**Steady state only.** Wave 2's first measurement reported 14 queries against 17
and the method was wrong, not the code: it inserted rows between the two
measurements, and inserting clears caches, so it compared a warm call with a
cold one. Here nothing is written while measuring. Every call is preceded by
three warm-up calls of the same call as the same user, and the number reported
is taken from calls after those.

What is recorded per call: the number of SQL statements (every read in Frappe
goes through `frappe.db.sql`, including the query builder's `.run()`), the wall
time, and the size of the payload as JSON bytes - which is what actually
crosses the wire.
"""

import json
import time

import frappe

REPEATS = 20
WARM = 3


class _Spy:
	"""Every SQL statement run inside the block."""

	def __init__(self):
		self.statements = []

	def __enter__(self):
		self._real = frappe.db.sql

		def spy(query, *args, **kwargs):
			self.statements.append(str(query))
			return self._real(query, *args, **kwargs)

		frappe.db.sql = spy
		return self

	def __exit__(self, *exc):
		frappe.db.sql = self._real
		return False


def _calls():
	"""The calls a portal page actually makes, each as (name, thunk)."""
	from alvoraa_portal import (
		frame_api,
		home_api,
		hr_api,
		inbox_api,
		pay_api,
		staff_api,
		time_api,
	)

	return [
		("get_frame", lambda: frame_api.get_frame()),
		("get_nav_counts", lambda: inbox_api.get_nav_counts()),
		("get_home", lambda: home_api.get_home()),
		("get_inbox", lambda: inbox_api.get_inbox()),
		("get_staff_list", lambda: staff_api.get_staff_list()),
		("get_team_scorecard", lambda: hr_api.get_team_scorecard()),
		# Slice 043, Wave 3. Two more landing calls, measured on the same two
		# fixture sites and by the same method, because a budget written
		# without a real headcount behind it is a guess that reads as proof -
		# four of Wave 2's five were wrong the day they were written.
		#
		# Both are OWN-RECORD calls, so the interesting number is not the count
		# but whether the count MOVES between twenty people and 981. If it
		# does, something in them is reading the tenant rather than the caller.
		("get_time", lambda: time_api.get_time()),
		("get_pay", lambda: pay_api.get_pay()),
	]


def _percentile(values, pct):
	if not values:
		return None
	ordered = sorted(values)
	# Nearest-rank. With 20 samples p95 is the 19th, which is what we want: the
	# second worst, not an interpolation that hides it.
	k = max(0, min(len(ordered) - 1,
	               int(round(pct / 100.0 * len(ordered) + 0.5)) - 1))
	return ordered[k]


def measure_one(thunk, repeats=REPEATS, warm=WARM):
	"""One call, warmed then measured. Nothing is written in between."""
	err = None
	for _ in range(warm):
		try:
			thunk()
		except Exception as exc:
			err = "%s: %s" % (type(exc).__name__, exc)
			return {"error": err}
	times, queries, sizes = [], [], []
	for _ in range(repeats):
		start = time.perf_counter()
		with _Spy() as spy:
			payload = thunk()
		times.append((time.perf_counter() - start) * 1000.0)
		queries.append(len(spy.statements))
		try:
			sizes.append(len(json.dumps(payload, default=str).encode("utf-8")))
		except Exception:
			sizes.append(None)
	sizes = [s for s in sizes if s is not None]
	return {
		"queries_min": min(queries),
		"queries_max": max(queries),
		"ms_p50": round(_percentile(times, 50), 1),
		"ms_p95": round(_percentile(times, 95), 1),
		"ms_max": round(max(times), 1),
		"bytes": max(sizes) if sizes else None,
		"repeats": repeats,
	}


def run(shape="large", repeats=REPEATS, build_first=1, write=1):
	"""Build if needed, then measure every call for every persona."""
	from alvoraa_portal.tests import fixtures_scale_044 as fx

	build_report = None
	if int(build_first):
		build_report = fx.build(shape)

	people = fx.count_built(shape)
	print("\n%s: %d people on this site (site total %d Employees)\n"
	      % (shape, people, frappe.db.count("Employee")), flush=True)

	results = {"shape": shape, "people": people,
	           "site_employees": frappe.db.count("Employee"),
	           "build": build_report, "personas": {}}

	for persona, _roles in fx.PERSONAS:
		login = fx.login_of(shape, persona)
		frappe.set_user(login)
		frappe.local.request_ip = "127.0.0.1"
		row = {}
		for name, thunk in _calls():
			row[name] = measure_one(thunk, repeats=int(repeats))
			got = row[name]
			if "error" in got:
				print("%-12s %-20s ERROR %s" % (persona, name, got["error"]),
				      flush=True)
			else:
				print("%-12s %-20s q=%-4s p50=%-8s p95=%-8s bytes=%s"
				      % (persona, name,
				         ("%d" % got["queries_min"]) if got["queries_min"] == got["queries_max"]
				         else "%d-%d" % (got["queries_min"], got["queries_max"]),
				         got["ms_p50"], got["ms_p95"], got["bytes"]), flush=True)
		results["personas"][persona] = row
		frappe.set_user("Administrator")

	if int(write):
		path = frappe.get_site_path("private", "files",
		                            "measure_044_%s.json" % shape)
		with open(path, "w") as handle:
			json.dump(results, handle, indent=1, default=str)
		print("\nwritten: %s" % path, flush=True)
	print(json.dumps(results["personas"], indent=1, default=str), flush=True)
	return results


def profile(shape="large", persona="sysmgr", call="get_nav_counts", top=12):
	"""Where the time and the queries actually go, for one call, one persona.

	A number that fails a budget is only half the answer; the other half is
	which statement it was. This prints every statement with its own time,
	slowest first, with the tables it touched.
	"""
	from alvoraa_portal.tests import fixtures_scale_044 as fx

	thunk = dict(_calls())[call]
	frappe.set_user(fx.login_of(shape, persona))
	frappe.local.request_ip = "127.0.0.1"
	for _ in range(WARM):
		thunk()

	timed = []
	real = frappe.db.sql

	def spy(query, *args, **kwargs):
		start = time.perf_counter()
		out = real(query, *args, **kwargs)
		timed.append(((time.perf_counter() - start) * 1000.0, str(query)))
		return out

	frappe.db.sql = spy
	try:
		thunk()
	finally:
		frappe.db.sql = real
	frappe.set_user("Administrator")

	total = sum(ms for ms, _q in timed)
	print("\n%s / %s / %s: %d statements, %.1f ms in SQL"
	      % (shape, persona, call, len(timed), total), flush=True)
	for ms, query in sorted(timed, reverse=True)[:int(top)]:
		flat = " ".join(query.split())
		print("  %7.1f ms  %s" % (ms, flat[:260]), flush=True)
	return [(round(ms, 2), " ".join(q.split())[:400]) for ms, q in timed]
