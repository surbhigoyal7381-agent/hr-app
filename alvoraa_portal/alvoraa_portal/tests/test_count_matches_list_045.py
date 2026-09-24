"""045 — a heading number must agree with the list beneath it.

`frappe.db.count` and `frappe.get_all` do not generate the same SQL for a
negation. Given the identical filter `{"status": ["!=", "Cancelled"]}`:

    frappe.get_all / get_list   ... WHERE IFNULL(`status`,'') <> 'Cancelled'
    frappe.db.count             ... WHERE `status` <> 'Cancelled'

In SQL `NULL <> 'Cancelled'` is NULL, not true. So the count drops every row
whose column is NULL and the list keeps it, and a user sees a number smaller
than the rows underneath it. Both columns pinned here are nullable.

Two live pairings were found. One of them - the Home team goal card - was
deleted outright by the 042 review's F3 before this branch landed, so one live
pairing is covered here: the KPI chip on a goal card. **The test writes one row
with a NULL status**, which is what makes the two engines disagree, and then
asserts the shipped number matches the list. It also asserts that
`frappe.db.count` still gives the WRONG answer on the same data — otherwise a
site where the trap did not reproduce would let it pass over nothing. The
static pin at the bottom still covers both functions.

`inbox_api._count_rows` is the pattern being copied: it counts by plucking
through `frappe.get_list`, so the inbox badge and the inbox list share one
query path and cannot diverge. **Anyone who "optimises" it to
`frappe.db.count` turns it into a live bug**, because
`attendance_correction.review_queue_filters` negates a nullable
`alvoraa_review_status`.
"""

import frappe
from frappe.utils import add_days, nowdate

from alvoraa_portal import goals_api, home_api
from alvoraa_portal.tests.fixtures_045 import Wave4Base

TAGGED = "S045 null-status probe"


class _Goals(Wave4Base):
	"""A goal (and a KPI) whose status is NULL, which no form can make.

	`status` has a default of `Active`, so the NULL is written after the insert
	with `db.set_value`. That is how a NULL gets there in real data too: a
	migration or an import, never a screen. `None` and not `""` — an empty
	string passes `<> 'Cancelled'` quite happily, and only a real NULL makes
	the two engines disagree.
	"""

	def _goal(self, employee, status="Active"):
		doc = frappe.get_doc({
			"doctype": "Individual Goal",
			"employee": employee,
			"goal_name": TAGGED,
			"target_value": 10,
			"start_date": add_days(nowdate(), -30),
			"end_date": add_days(nowdate(), 30),
		})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		frappe.db.set_value("Individual Goal", doc.name, "status", status,
		                    update_modified=False)
		self.addCleanup(self._drop, "Individual Goal", doc.name)
		frappe.db.commit()
		return doc.name

	def _kpi(self, employee, goal, status="Active"):
		doc = frappe.get_doc({
			"doctype": "KPI",
			"kpi_name": TAGGED,
			"employee": employee,
			"individual_goal": goal,
			"target_value": 10,
		})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		frappe.db.set_value("KPI", doc.name, "status", status,
		                    update_modified=False)
		self.addCleanup(self._drop, "KPI", doc.name)
		frappe.db.commit()
		return doc.name

	def _drop(self, doctype, name):
		frappe.set_user("Administrator")
		frappe.db.delete(doctype, {"name": name})
		frappe.db.commit()


# `TestTheHomeTeamGoalCard` lived here. It covered the second of the two
# pairings: the "N goals" on the Home team card, counted with `frappe.db.count`
# over a list the Goals screen showed in full.
#
# **That card no longer exists.** Wave 3's rebase brought in the 042 review's
# F3, which deleted the whole team goal summary from `home_api._goals` - the
# number was wrong for a different reason as well (it counted the goals of the
# first fifty people and reported the headcount of all of them), it read every
# permitted employee id into Python, and no screen drew it. There is nothing
# left to count there, so the test is deleted rather than rewritten against a
# function that is gone.
#
# The defect it found is NOT gone from the codebase, and is still pinned twice:
# the KPI chip below is the live call site, and the static pin at the bottom
# still reads `home_api._goals`, so the `mine` query - which also negates a
# nullable `status` - cannot be "optimised" back to `frappe.db.count` either.

class TestTheGoalCardKpiChip(_Goals):
	"""`goals_api.get_my_goals` — the KPI chip against the contributor list."""

	def test_the_chip_counts_the_kpis_the_detail_screen_lists(self):
		goal = self._goal(self.rahul, status="Active")
		self._kpi(self.rahul, goal, status="Active")
		self._kpi(self.rahul, goal, status=None)

		filters = {"individual_goal": goal, "status": ["!=", "Cancelled"]}
		wrong = frappe.db.count("KPI", filters)
		# The same filter the contributor list on the detail screen uses.
		listed = len(frappe.get_all("KPI", filters=filters, pluck="name",
		                            limit_page_length=0, ignore_permissions=True))
		self.assertEqual(2, listed)
		self.assertEqual(1, wrong,
		                 "db.count and get_all agreed - the trap did not reproduce")

		self.as_user(self.rahul_user)
		rows = [g for g in goals_api.get_my_goals() if g["name"] == goal]
		frappe.set_user("Administrator")
		self.assertTrue(rows, "the probe goal did not come back from get_my_goals")
		self.assertEqual(
			listed, rows[0]["linked_kpi_count"],
			"the goal card's KPI chip dropped the KPI whose status is NULL")


class TestTheCountedPathIsNotQuietlySwappedBack(Wave4Base):
	def test_no_db_count_carries_a_negated_filter(self):
		"""A static pin, because the fix is one edit away from being undone.

		Somebody "optimising" a `len(get_all(...))` back to `frappe.db.count`
		would put this bug straight back, and the data it needs to show up (a
		NULL status) is not on most sites. So the SHAPE of the call is pinned
		as well as its result.

		Only NEGATED filters are pinned. `frappe.db.count` on an equality —
		`{"parent": name}` — is fine and stays, because both engines agree
		about `=`.
		"""
		import inspect
		import re

		# `frappe.db.count(` ... up to its closing bracket, allowing one level
		# of nesting for the filter dict, containing a negation.
		negated = re.compile(r'frappe\.db\.count\((?:[^()]|\([^()]*\))*'
		                     r'(?:"!="|\'!=\'|"not in"|\'not in\')')
		for fn in (home_api._goals, goals_api.get_my_goals):
			src = inspect.getsource(fn)
			src = "\n".join(l for l in src.split("\n")
			                if not l.strip().startswith("#"))
			src = re.sub(r'"""(.|\n)*?"""', "", src)
			self.assertIsNone(
				negated.search(src),
				f"{fn.__name__} counts a negated filter with db.count again - "
				"see this module's docstring for why that disagrees with the list")
