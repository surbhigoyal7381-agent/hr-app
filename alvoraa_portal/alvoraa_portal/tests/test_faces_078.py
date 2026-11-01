"""078 step 2 - faces on the chart and the table, and the cost of them.

Two tests here are the ones worth keeping, and both are about a NUMBER rather
than a feature:

  * **AC-37a / OPS-6 / 078-PRIV-4.** The same number of statements for 20
    people as for 400. It is a performance gate and a privacy gate at once: a
    per-person read is how a payload quietly grows, and the Organisation page
    was one `get_value` per person per box per expansion before this slice.
  * **OPS-20.** The Organisation page's card used to list every person in a
    seat - one expansion from the root was measured at 94 boxes and 185 people.
    Nobody chose that; it was what happened when nothing capped it.

The third is the one that carries the whole design: the 48 px copy is what the
chart and the table draw, and the stored 512 px picture is only for the
drawer's enlargement. If that ever inverts, a 16-face first paint goes from
about 10 KB to about 720 KB and nothing fails.
"""

import frappe
import hrms.alvoraa_org_structure.api as org_api
import hrms.alvoraa_org_structure.people_fields as people_fields

from alvoraa_portal.tests import fixtures_078 as fx
from alvoraa_portal.tests.fixtures_045 import Wave4Base


class _Spy:
	"""Counts statements by standing in front of `frappe.db.sql`. Copied from
	`test_notices_076`, which is where this project settled on one way to do it."""

	def __enter__(self):
		self.n = 0
		self._real = frappe.db.sql

		def spy(query, *a, **k):
			self.n += 1
			return self._real(query, *a, **k)

		frappe.db.sql = spy
		return self

	def __exit__(self, *exc):
		frappe.db.sql = self._real
		return False


class TestTheChartsCost(Wave4Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.p = fx.people()
		fx.give_photo(cls.p["with_photo"])
		fx.strip_photo(cls.p["no_photo"])

	def setUp(self):
		super().setUp()
		# The card cache is per REQUEST. A test that shares one across cases
		# would measure the cache instead of the code.
		if hasattr(frappe.local, "_alvoraa_org_cards"):
			del frappe.local._alvoraa_org_cards

	def test_the_thumbnail_read_is_one_statement_whatever_the_headcount(self):
		"""**The gate.** 20 ids and 400 ids cost the same.

		Measured by DevOps at 13.4 ms for 403 ids on the composite index
		`tabFile` already carries, which is what settled the spec's open
		question: a `File` row does NOT defeat the batching, so there is no
		column on the HR master and no migration.
		"""
		twenty = ["X%03d" % i for i in range(20)]
		four_hundred = ["X%03d" % i for i in range(400)]
		small = self._count(lambda: people_fields.thumbnails_for(twenty))
		large = self._count(lambda: people_fields.thumbnails_for(four_hundred))
		self.assertEqual(small, large, f"{small} statements for 20, {large} for 400")
		self.assertEqual(small, 1)

	def test_the_cards_of_a_whole_subtree_cost_two_statements_not_one_each(self):
		"""OPS-6. `_card` used to be one `get_value` per person per box, and a
		person drawn in two boxes was read twice."""
		people = [self.p["with_photo"], self.p["no_photo"], self.p["gps"],
		          self.p["other_branch"]]
		used = self._count(lambda: org_api._cards_for(people))
		# One for the Employee rows, one for the 48 px copies.
		self.assertEqual(used, 2, f"{used} statements for {len(people)} people")

	def test_a_second_ask_for_the_same_person_costs_nothing(self):
		"""E9: one request per person, not per box. Slice 072 draws the same
		person in several boxes on purpose."""
		org_api._cards_for([self.p["with_photo"]])
		again = self._count(lambda: org_api._card(self.p["with_photo"]))
		self.assertEqual(again, 0)

	def test_the_card_carries_the_48px_copy_and_the_stored_picture_separately(self):
		"""The chart and the table draw `thumb`; only the drawer's enlargement
		uses `image`. If those two ever swap, a 16-face first paint goes from
		about 10 KB to about 720 KB and nothing fails."""
		card = org_api._card(self.p["with_photo"])
		self.assertTrue(card["image"], "the stored 512 px picture")
		self.assertTrue(card["thumb"], "the derived 48 px copy")
		self.assertNotEqual(card["image"], card["thumb"])

	def test_a_person_with_no_photograph_carries_neither(self):
		"""So the renderer falls back to their initials, with nothing to fetch
		and no broken image anywhere (AC-12, AC-26)."""
		card = org_api._card(self.p["no_photo"])
		self.assertFalse(card["image"])
		self.assertFalse(card["thumb"])

	def test_a_missing_employee_is_cached_as_missing(self):
		"""A bad link costs one statement for the whole request, not one per
		box - and `_card` answers None rather than raising."""
		self.assertIsNone(org_api._card("S078-NOT-A-PERSON"))
		again = self._count(lambda: org_api._card("S078-NOT-A-PERSON"))
		self.assertEqual(again, 0)

	def test_the_three_name_cap_is_three_and_matches_the_front_end(self):
		"""OPS-20. It has to match `POS_NAMES_SHOWN` in `portal.js`, which the
		DOM suite pins literally at 3."""
		self.assertEqual(org_api.NAMES_SHOWN, 3)

	def test_a_seat_of_six_sends_three_people_and_says_how_many_more(self):
		"""OPS-20, on the data rather than on the drawing: the bytes are what
		matter on a 3G phone, so the cap is server-side."""
		holders = [frappe._dict({"employee": e, "weight": 100,
		                         "assignment_type": "Permanent"})
		           for e in [self.p["with_photo"], self.p["no_photo"], self.p["gps"],
		                     self.p["other_branch"], self.p["hr_wide"], self.p["hr_store"]]]
		cards = org_api._capped_cards(holders)
		self.assertEqual(len(cards), 3)
		self.assertEqual(max(0, len(holders) - org_api.NAMES_SHOWN), 3)

	def _count(self, fn):
		"""How many SQL statements a call makes. The shape slice 076 already uses."""
		with _Spy() as spy:
			fn()
		return spy.n
