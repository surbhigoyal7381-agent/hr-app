"""Capture a real `get_performance_tree` payload as a tracked test fixture.

045 AC-63. Two jsdom tests - `portal_tree_test.js` and `portal_redesign_test.js`
- have never run, because they take a `get_performance_tree` payload as their
third argument and no such file was in the repository. They were skipped, and
`run_dom_tests.js` called them Wave 3's; they are the Growth screens, so they
are Wave 4's.

**This is a real call, not a hand-written shape.** A fixture somebody typed out
drifts from the endpoint the moment a key is renamed, and then the test passes
against a payload the product never sends - which is the failure the skip was
already producing, only quieter.

**Every name in it is replaced.** The payload carries employee names and goal
names from whatever site it was captured on. They are scrubbed here, on the way
out, so nothing about a real person can reach a tracked file.

Run it in your OWN container, against a fixture site:

    bench --site test044s execute \\
      alvoraa_portal.scripts.capture_performance_tree_fixture.main

or, from this repository, through the path the bench sees. The file lands at
`alvoraa_portal/tests/fixtures/performance_tree.json`, which is bind-mounted, so
no `docker cp` is involved.
"""

import json
import os
import re

import frappe

# This file lives INSIDE the app, not in `scripts/`, for one practical reason:
# the bench container mounts the apps and not the repository root, so a tool in
# `scripts/` cannot be reached from `bench execute` at all without copying it -
# and copying files into a container is exactly what this slice may not do.
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "fixtures", "performance_tree.json")

# Names that go INTO the file, in place of whatever was on the site. Short,
# obviously fake, and stable - so a re-capture produces the same file and a diff
# shows a real shape change rather than a reshuffle of somebody's colleagues.
FIXTURE_PEOPLE = ["Asha Fixture", "Bala Fixture", "Chandra Fixture", "Deepa Fixture"]
# **The names must not share a prefix.** `portal_redesign_test.js` searches for
# the first six characters of the first objective's name and asserts the tree
# gets SHORTER. With every row called "Fixture ..." the search matched
# everything and the assertion failed - a fixture defect that looked exactly
# like a product defect, which is the strongest argument for distinct names.
FIXTURE_GOALS = ["Alpha Objective", "Bravo Objective", "Charlie Objective",
                 "Delta Objective", "Echo Objective"]
FIXTURE_KPIS = ["Foxtrot KPI", "Golf KPI", "Hotel KPI", "India KPI"]

# Every key whose VALUE is somebody's words rather than the product's structure.
# Scrubbed by key, recursively, so a key added later still gets caught by the
# check at the bottom rather than travelling out unnoticed.
NAME_KEYS = {"employee_name", "owner_name", "logged_by_name", "approved_by_name"}
GOAL_KEYS = {"goal_name", "objective", "parent_goal_name"}
KPI_KEYS = {"kpi_name"}
DROP_KEYS = {"description", "note", "comment", "self_comment", "manager_comment",
             "evidence_file", "owner", "modified_by", "logged_by", "approved_by"}


def _pick(pool, seen, value):
	if value not in seen:
		seen[value] = pool[len(seen) % len(pool)] + (
			"" if len(seen) < len(pool) else " %d" % len(seen))
	return seen[value]


def scrub(node, seen):
	if isinstance(node, list):
		return [scrub(n, seen) for n in node]
	if not isinstance(node, dict):
		return node
	out = {}
	for key, value in node.items():
		if key in DROP_KEYS:
			# Free text and login ids are dropped outright rather than
			# replaced. Nothing in these two tests reads them, and a fixture
			# does not need to carry a field to prove a shape.
			out[key] = "" if isinstance(value, str) else None
		elif key in NAME_KEYS and isinstance(value, str) and value:
			out[key] = _pick(FIXTURE_PEOPLE, seen, value)
		elif key in GOAL_KEYS and isinstance(value, str) and value:
			out[key] = _pick(FIXTURE_GOALS, seen, value)
		elif key in KPI_KEYS and isinstance(value, str) and value:
			out[key] = _pick(FIXTURE_KPIS, seen, value)
		else:
			out[key] = scrub(value, seen)
	return out


# Anything that still looks like an email address or a phone number after the
# scrub. Belt and braces: the key list above is a list somebody maintains, and
# this is the check that fails when they forget one.
# Three shapes, and deliberately NOT "any run of digits": the payload is full
# of dates and document ids, and a check that fires on `2027-05-22` is a check
# somebody switches off.
LEAKY = re.compile(
	r"[\w.+-]+@[\w-]+\.[\w.]+"      # an email address
	r"|\+\d[\d ()-]{8,}"             # an international phone number
	r"|(?<!\d)\d{10}(?!\d)"          # a bare ten-digit Indian mobile
)


def main(user="Administrator", scope="organisation"):
	"""Capture as `user`, over `scope`.

	**Both matter, and the first capture proved it.** Run as Administrator over
	the default scope, the payload came back with twelve objectives and **no
	KPIs at all** - and `portal_tree_test.js` exists to click KPI rows, so that
	fixture would have made the test run and assert nothing. The capture is
	aimed at a population that really has both, and `check_the_fixture_is_worth
	_having` below fails if it ever comes back empty again.
	"""
	from alvoraa_portal import performance_api

	frappe.set_user(user)
	payload = performance_api.get_performance_tree(scope=scope)
	clean = scrub(json.loads(json.dumps(payload, default=str)), {})

	blob = json.dumps(clean, indent=2, sort_keys=True, ensure_ascii=False)
	found = LEAKY.findall(blob)
	if found:
		raise SystemExit(
			"the scrubbed payload still contains something that looks like a "
			"contact detail, so it is NOT safe to track: %r" % (found[:3],))

	# **A fixture with nothing in it makes a test that proves nothing.** The
	# two jsdom tests click objective rows AND KPI rows, so both have to be
	# there or the file is worse than no file - it would turn a skip that
	# everybody could see into a pass that nobody could question.
	if not clean.get("roots"):
		raise SystemExit("no objectives came back - capture from a site that has some")
	if not clean["counts"].get("kpis"):
		raise SystemExit(
			"no KPIs came back, so portal_tree_test.js would run and assert "
			"nothing. Capture as a user and scope that really has KPIs.")

	os.makedirs(os.path.dirname(OUT), exist_ok=True)
	with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
		fh.write(blob + "\n")
	print("wrote %s (%d roots, %d flat goals)"
	      % (OUT, len(clean.get("roots") or []), len(clean.get("flat_goals") or [])))
