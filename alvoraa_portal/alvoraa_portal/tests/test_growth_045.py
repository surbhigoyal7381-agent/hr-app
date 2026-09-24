"""045 Growth - the ceiling, the whole-point rule, and every company value.

Three of Surbhi's answers of 24 September 2026, each with a check that can go
red.

**The ceiling is the one worth reading.** `page_data` is a MariaDB `TEXT`:
65,535 **bytes**, not characters, and `sql_mode` is strict - so an oversize
write **raises** rather than truncating silently. That was measured on this
project's own bench against the real column, and the boundary is exact:
21,845 Devanagari characters fit, 21,846 raise `DataError 1406`.

Throwing is the better of the two failures. It is still the wrong one to leave
unhandled, because the write is an **autosave**: an employee would keep typing
while nothing saved and nothing told them. So there is a budget checked before
the write, and the tests below prove the budget is in BYTES - a character-count
budget would pass every English test in this file and fail the first employee
who writes in Hindi.
"""

import json

import frappe

from alvoraa_portal import growth_api
from alvoraa_portal.tests.fixtures_045 import COMPANY, Wave4Base

DEVANAGARI = "क"  # three bytes in utf-8


class TestTheCeilingIsCountedInBytes(Wave4Base):
	def test_the_budget_is_below_the_real_column_limit(self):
		"""The margin is for the JSON envelope the column also carries."""
		self.assertEqual(65535, growth_api.PAGE_DATA_MAX_BYTES)
		self.assertLess(growth_api.PAGE_DATA_BUDGET_BYTES,
		                growth_api.PAGE_DATA_MAX_BYTES)

	def test_devanagari_costs_three_times_what_english_does(self):
		"""The whole reason the budget is in bytes.

		A character-count budget would pass every English test and fail the
		first employee who writes in Hindi, which is Wave 5's problem arriving
		early.
		"""
		english = "a" * 1000
		hindi = DEVANAGARI * 1000
		self.assertEqual(1000, growth_api.page_data_bytes(english))
		self.assertEqual(3000, growth_api.page_data_bytes(hindi))
		self.assertEqual(len(english), len(hindi),
		                 "the two strings must be the same LENGTH, or this "
		                 "test is not about bytes at all")

	def test_an_answer_that_fits_is_accepted(self):
		payload = json.dumps({"step": "a" * 1000})
		self.assertEqual(growth_api.page_data_bytes(payload),
		                 growth_api.check_page_data_fits(payload))

	def test_an_oversize_answer_is_refused_before_the_database_sees_it(self):
		payload = json.dumps({"step": "a" * (growth_api.PAGE_DATA_BUDGET_BYTES + 100)})
		with self.assertRaises(frappe.ValidationError) as caught:
			growth_api.check_page_data_fits(payload)
		msg = str(caught.exception)
		# Says what happened, why, and what to do next - and reassures, because
		# the one thing somebody fears here is that they have lost the lot.
		self.assertIn("too long", msg.lower())
		self.assertIn("Shorten", msg)
		self.assertIn("has been lost", msg)

	def test_a_hindi_answer_is_refused_at_a_third_the_characters(self):
		"""The check that would have been missed.

		The same number of CHARACTERS: the English one fits and the Devanagari
		one does not. A character-count budget would accept both and the
		database would then throw on the second.
		"""
		chars = 24000
		english = json.dumps({"step": "a" * chars})
		hindi = json.dumps({"step": DEVANAGARI * chars}, ensure_ascii=False)
		growth_api.check_page_data_fits(english)   # fits
		with self.assertRaises(frappe.ValidationError):
			growth_api.check_page_data_fits(hindi)

	def test_the_assertion_can_fail(self):
		"""Check the check: the budget really does reject something."""
		with self.assertRaises(frappe.ValidationError):
			growth_api.check_page_data_fits("x" * (growth_api.PAGE_DATA_MAX_BYTES + 1))


class TestRatingsAreWholePoints(Wave4Base):
	"""Surbhi, 24 September 2026: whole points, no halves."""

	def test_whole_numbers_in_range_are_accepted(self):
		for value in (1, 2, 3, 4, 5, "3", 5.0):
			with self.subTest(value=value):
				self.assertEqual(int(float(value)), growth_api.check_whole_point(value))

	def test_a_half_point_is_refused_on_the_server(self):
		"""Hiding the half-point from a slider is not a rule. Anybody with a
		browser console sends 3.5."""
		with self.assertRaises(frappe.ValidationError) as caught:
			growth_api.check_whole_point(3.5)
		self.assertIn("whole points", str(caught.exception))

	def test_out_of_range_is_refused(self):
		for value in (0, 6, -1, 99):
			with self.subTest(value=value):
				with self.assertRaises(frappe.ValidationError):
					growth_api.check_whole_point(value)

	def test_nonsense_is_refused_rather_than_coerced(self):
		with self.assertRaises(frappe.ValidationError):
			growth_api.check_whole_point("excellent")

	def test_no_rating_at_all_is_allowed(self):
		"""Not every value has to be rated for the call to be valid - the STEP
		is what requires all of them, and that is a different check."""
		self.assertIsNone(growth_api.check_whole_point(None))
		self.assertIsNone(growth_api.check_whole_point(""))


class TestEveryCompanyValueNotTwo(Wave4Base):
	"""Surbhi overruled the 'pick two' recommendation:

	*"Most companies dont have more than 5 values. it is important to include
	all."* So the count comes from the tenant, and nothing here assumes five.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# SEVEN, deliberately. Five would let an assumed-five implementation
		# pass, and seven is the number Surbhi's instruction called out.
		cls.value_names = [f"S045 Value {i}" for i in range(7)]
		for i, name in enumerate(cls.value_names):
			if not frappe.db.exists("Company Value", name):
				frappe.get_doc({
					"doctype": "Company Value",
					"value_name": name,
					"company": COMPANY,
					"is_active": 1,
					"description": f"S045 description {i}",
				}).insert(ignore_permissions=True)
		# One switched off, which must never be offered.
		if not frappe.db.exists("Company Value", "S045 Retired Value"):
			frappe.get_doc({
				"doctype": "Company Value",
				"value_name": "S045 Retired Value",
				"company": COMPANY,
				"is_active": 0,
			}).insert(ignore_permissions=True)
		frappe.db.commit()

	def test_all_seven_are_returned_and_the_count_comes_from_the_tenant(self):
		values = growth_api.company_values_for(self.rahul)
		names = {v["value_name"] for v in values}
		for wanted in self.value_names:
			self.assertIn(wanted, names, f"{wanted} is missing - this is not "
			                             "'all the values'")
		self.assertGreaterEqual(len(values), 7,
		                        "seven active values, and the code returned fewer")

	def test_an_inactive_value_is_never_offered(self):
		names = {v["value_name"] for v in growth_api.company_values_for(self.rahul)}
		self.assertNotIn("S045 Retired Value", names)

	def test_nothing_in_the_code_assumes_five(self):
		"""A static check, because 'assumes five' is the kind of thing that
		hides in a slice or a range rather than in a sentence."""
		import inspect

		src = inspect.getsource(growth_api)
		for literal in ("[:5]", "[:2]", "range(5)", "range(2)"):
			self.assertNotIn(literal, src, f"growth_api contains {literal}")

	def test_the_step_is_done_only_when_every_value_has_a_rating(self):
		"""AC-28. A step that was merely opened is not progress.

		And 'every' means every, because Surbhi's answer was all of them - six
		out of seven is not a finished step.
		"""
		values = [{"name": f"v{i}"} for i in range(7)]
		none = {}
		some = {f"v{i}": {"rating": 3} for i in range(6)}
		all_of = {f"v{i}": {"rating": 3} for i in range(7)}
		self.assertFalse(growth_api.values_step_is_answered(none, values))
		self.assertFalse(growth_api.values_step_is_answered(some, values),
		                 "six of seven counted as a finished step")
		self.assertTrue(growth_api.values_step_is_answered(all_of, values))

	def test_a_comment_is_optional_and_its_absence_never_blocks_the_step(self):
		values = [{"name": "v0"}]
		self.assertTrue(growth_api.values_step_is_answered(
			{"v0": {"rating": 4}}, values))
		self.assertTrue(growth_api.values_step_is_answered(
			{"v0": {"rating": 4, "comment": ""}}, values))

	def test_the_endpoint_says_the_scale_is_whole_points(self):
		"""So the screen cannot invent a half-point control and then be
		corrected by the server."""
		self.as_user(self.rahul_user)
		out = growth_api.get_company_values()
		self.assertEqual(1, out["rating_step"])
		self.assertEqual(growth_api.RATING_MIN, out["rating_min"])
		self.assertEqual(growth_api.RATING_MAX, out["rating_max"])
		self.assertEqual(len(out["values"]), out["count"],
		                 "the count does not equal the list it describes")
