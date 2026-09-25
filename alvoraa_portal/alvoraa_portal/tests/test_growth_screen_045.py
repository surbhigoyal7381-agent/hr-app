"""045 - the Growth screen and the self-review wizard, on the server.

`test_growth_045` covers the three rules Surbhi decided (bytes, whole points,
every value). This file covers the two endpoints the SCREENS call, and the
three things about them that are easiest to get wrong:

**1. The approved figure and the waiting one never meet.** `01b` §7.2 and
AC-29: a goal at 28.4 with 3.1 waiting shows 28.4, names the 3.1 on its own
line, and **31.5 appears nowhere**. The assertion searches the serialised
payload for the sum rather than checking two named keys, because the next time
this leaks it will be under a key nobody listed.

**2. "Step 3 of 5" means three steps have answers**, not three steps were
opened (AC-28).

**3. The byte budget is reported back on every save**, so the screen can warn
while somebody is still typing. The write that fails is an autosave: without a
warning an employee keeps typing while nothing is being saved and nothing tells
them.

Everything here is driven as **Rahul**, a plain employee with no HR role and no
reports, because the Growth screen is the employee's own.
"""

import json

import frappe
from frappe.utils import add_days, nowdate

from alvoraa_portal import growth_api
from alvoraa_portal.tests.fixtures_045 import COMPANY, Wave4Base

DEVANAGARI = "क"  # three bytes in utf-8

# The two figures AC-29 is written about, and the one that must never appear.
APPROVED = 28.4
WAITING = 3.1
THE_SUM = 31.5


class GrowthFixture(Wave4Base):
	"""A cycle, an appraisal, one goal with a waiting reading, and one KPI.

	**Everything here belongs to Wave 4's own company and to Rahul.** Nobody new
	is hired, and nothing is added to a company another suite reads - the trap
	this slice walked into once already.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.cycle = "S045 Growth Cycle"
		if not frappe.db.exists("Appraisal Cycle", cls.cycle):
			frappe.get_doc({
				"doctype": "Appraisal Cycle",
				"cycle_name": cls.cycle,
				"company": COMPANY,
				"start_date": add_days(nowdate(), -30),
				"end_date": add_days(nowdate(), 60),
				"status": "In Progress",
			}).insert(ignore_permissions=True)

		cls.goal = frappe.db.get_value(
			"Individual Goal", {"employee": cls.rahul, "goal_name": "S045 Screen Goal"},
			"name")
		if not cls.goal:
			cls.goal = frappe.get_doc({
				"doctype": "Individual Goal",
				"employee": cls.rahul,
				"goal_name": "S045 Screen Goal",
				"appraisal_cycle": cls.cycle,
				"target_value": 100,
				"unit": "Lakh",
				"start_date": add_days(nowdate(), -30),
				"end_date": add_days(nowdate(), 60),
				"weightage": 100,
			}).insert(ignore_permissions=True).name

		# A goal whose trajectory says somebody should look.
		cls.off_track = frappe.db.get_value(
			"Individual Goal", {"employee": cls.rahul, "goal_name": "S045 Off Track Goal"},
			"name")
		if not cls.off_track:
			cls.off_track = frappe.get_doc({
				"doctype": "Individual Goal",
				"employee": cls.rahul,
				"goal_name": "S045 Off Track Goal",
				"appraisal_cycle": cls.cycle,
				"target_value": 100,
				"start_date": add_days(nowdate(), -30),
				"end_date": add_days(nowdate(), 60),
			}).insert(ignore_permissions=True).name
		frappe.db.set_value("Individual Goal", cls.off_track, "trajectory", "Off Track",
		                    update_modified=False)

		cls.kpi = frappe.db.get_value(
			"KPI", {"employee": cls.rahul, "kpi_name": "S045 Screen KPI"}, "name")
		if not cls.kpi:
			cls.kpi = frappe.get_doc({
				"doctype": "KPI",
				"kpi_name": "S045 Screen KPI",
				"employee": cls.rahul,
				"appraisal_cycle": cls.cycle,
				"individual_goal": cls.goal,
				"unit": "Lakh",
				"target_value": 100,
				# **The approved figure.** The waiting reading below is never
				# added to it by anything.
				"actual_value": APPROVED,
				"weightage": 100,
			}).insert(ignore_permissions=True).name

		# One reading, logged and NOT approved. Written straight into the child
		# table, which is where an unapproved reading really sits.
		if not frappe.db.exists("KPI Progress Log",
		                        {"parent": cls.kpi, "approval_status": "Pending"}):
			row = frappe.get_doc({
				"doctype": "KPI Progress Log",
				"parent": cls.kpi, "parenttype": "KPI", "parentfield": "progress_log",
				"log_date": nowdate(), "value": WAITING, "approval_status": "Pending",
			})
			row.name = frappe.generate_hash(length=10)
			row.db_insert()

		cls.appraisal = frappe.db.get_value(
			"Appraisal", {"employee": cls.rahul, "appraisal_cycle": cls.cycle}, "name")
		if not cls.appraisal:
			cls.appraisal = frappe.get_doc({
				"doctype": "Appraisal", "employee": cls.rahul,
				"appraisal_cycle": cls.cycle, "company": COMPANY,
			}).insert(ignore_permissions=True).name
		frappe.db.commit()


def serialised(payload):
	return json.dumps(payload, default=str)


class TestTheGrowthScreen(GrowthFixture):
	def test_a_plain_employee_gets_their_own_goals(self):
		self.as_user(self.rahul_user)
		out = growth_api.get_growth()
		drawn = {g["goal"] for g in out["goals"]}
		self.assertIn(self.goal, drawn)
		self.assertIn(self.off_track, drawn)

	def test_the_screen_reads_nobody_elses_goals(self):
		"""There is no employee argument, so there is nothing to change."""
		self.as_user(self.rahul_user)
		out = growth_api.get_growth()
		owners = set(frappe.get_all(
			"Individual Goal", filters={"name": ["in", [g["goal"] for g in out["goals"]]]},
			pluck="employee"))
		self.assertEqual({self.rahul}, owners)

	def test_the_approved_figure_and_the_waiting_one_are_separate_keys(self):
		"""AC-29. 28.4 is shown, 3.1 is named, and 31.5 exists nowhere."""
		self.as_user(self.rahul_user)
		out = growth_api.get_growth()
		kpi = next(k for g in out["goals"] for k in g["kpis"] if k["kpi"] == self.kpi)
		self.assertEqual(APPROVED, kpi["approved"])
		self.assertEqual([WAITING], [w["amount"] for w in kpi["waiting"]])
		# Searched over the whole serialised payload, not over two named keys.
		# A two-key check passes the moment somebody adds a third key carrying
		# the same value, which is exactly how this kind of leak spreads.
		self.assertNotIn(str(THE_SUM), serialised(out),
		                 "the approved and waiting figures were added together "
		                 "somewhere in the payload")

	def test_the_assertion_about_the_sum_can_actually_fail(self):
		"""Check the check.

		If `serialised` were not really searching the payload, the assertion
		above would pass over nothing. This proves the search finds a number
		that IS there.
		"""
		self.as_user(self.rahul_user)
		out = growth_api.get_growth()
		self.assertIn(str(APPROVED), serialised(out))

	def test_needs_attention_is_the_same_list_it_is_a_count_of(self):
		"""Surbhi's standing rule, on the one list where the count is a
		judgement about a person."""
		self.as_user(self.rahul_user)
		out = growth_api.get_growth()
		by_flag = [g["goal"] for g in out["goals"]
		           if g["trajectory"]["needs_attention"]]
		self.assertEqual(sorted(by_flag), sorted(out["needs_attention"]))
		self.assertIn(self.off_track, out["needs_attention"])

	def test_no_percentage_threshold_is_written_into_the_module(self):
		"""AC-23. The prototype's 75 % has no source in the product, and a
		threshold here would be a second definition of a judgement the goal
		controller already makes."""
		import inspect
		import re

		src = inspect.getsource(growth_api)
		# Strip comments and docstrings first, or this fails on the sentence
		# explaining why the number is not here - a test going red because the
		# code was documented.
		body = re.sub(r"#.*", "", src)
		body = re.sub(r'"""[\s\S]*?"""', "", body)
		for literal in ("75", "0.75", "0.8"):
			self.assertNotIn(literal, body,
			                 f"growth_api contains the threshold literal {literal}")

	def test_a_stale_trajectory_carries_the_date_it_was_worked_out(self):
		"""AC-24 / `01b` §14 rule 12. `trajectory` is written in `validate`
		only, so a goal nobody saves keeps September's answer in December."""
		frappe.db.set_value(
			"Individual Goal", self.goal, "modified",
			add_days(nowdate(), -(growth_api.TRAJECTORY_STALE_DAYS + 5)),
			update_modified=False)
		self.as_user(self.rahul_user)
		out = growth_api.get_growth()
		row = next(g for g in out["goals"] if g["goal"] == self.goal)
		self.assertTrue(row["trajectory"]["stale"])
		self.assertTrue(row["trajectory"]["as_of"],
		                "a stale chip with no date is a judgement presented as "
		                "today's fact")

	def test_a_goal_with_no_trajectory_is_not_off_track(self):
		"""AC-67. Never "Off Track" and never 0 % for a goal with no target."""
		frappe.db.set_value("Individual Goal", self.goal, "trajectory", None,
		                    update_modified=False)
		self.as_user(self.rahul_user)
		out = growth_api.get_growth()
		row = next(g for g in out["goals"] if g["goal"] == self.goal)
		self.assertEqual("", row["trajectory"]["state"])
		self.assertFalse(row["trajectory"]["needs_attention"])

	def test_the_review_block_names_the_manager_from_reports_to(self):
		"""AC-25 / AC-83. `Employee.reports_to`, never the org chart and never
		`get_effective_manager`'s first-active-HR-Manager fallback."""
		self.as_user(self.rahul_user)
		out = growth_api.get_growth()
		self.assertTrue(out["review"]["has_manager"])
		self.assertEqual(
			frappe.db.get_value("Employee", self.sandeep, "employee_name"),
			out["review"]["goes_to"])

	def test_an_employee_with_no_manager_is_told_plainly(self):
		"""AC-59. Said on the screen, not discovered when Send refuses."""
		frappe.db.set_value("Employee", self.rahul, "reports_to", None,
		                    update_modified=False)
		self.as_user(self.rahul_user)
		out = growth_api.get_growth()
		self.assertFalse(out["review"]["has_manager"])
		self.assertEqual("", out["review"]["goes_to"],
		                 "a manager was invented for somebody who has none")

	def test_the_manager_name_comes_from_the_employee_record_and_can_move(self):
		"""Check the check: the previous two tests would both pass if the key
		were hard-coded, so this moves `reports_to` and asserts the answer
		follows it."""
		frappe.db.set_value("Employee", self.rahul, "reports_to", self.kamal,
		                    update_modified=False)
		self.as_user(self.rahul_user)
		out = growth_api.get_growth()
		self.assertEqual(
			frappe.db.get_value("Employee", self.kamal, "employee_name"),
			out["review"]["goes_to"])


class TestTheSelfReviewWizard(GrowthFixture):
	def test_the_wizard_offers_every_company_value(self):
		"""Seven on this fixture. An implementation that assumed five fails."""
		for i in range(7):
			name = f"S045 Wizard Value {i}"
			if not frappe.db.exists("Company Value", name):
				frappe.get_doc({
					"doctype": "Company Value", "value_name": name,
					"company": COMPANY, "is_active": 1,
				}).insert(ignore_permissions=True)
		frappe.db.commit()
		self.as_user(self.rahul_user)
		out = growth_api.get_self_review(self.appraisal)
		self.assertEqual(len(out["values"]), out["values_count"],
		                 "the count does not equal the list it describes")
		self.assertGreaterEqual(out["values_count"], 7)

	def test_somebody_elses_review_is_refused(self):
		other = frappe.get_doc({
			"doctype": "Appraisal", "employee": self.sandeep,
			"appraisal_cycle": self.cycle, "company": COMPANY,
		}).insert(ignore_permissions=True).name
		self.as_user(self.rahul_user)
		with self.assertRaises(frappe.PermissionError):
			growth_api.get_self_review(other)
		with self.assertRaises(frappe.PermissionError):
			growth_api.save_self_review(other, {"overall": {"text": "x"}})

	def test_a_step_that_was_only_opened_is_not_done(self):
		"""AC-28. "Step 3 of 5" has to mean three steps have answers."""
		values = [{"name": "v0"}, {"name": "v1"}]
		self.assertEqual([], growth_api._steps_answered({}, values, ["g1"]))
		self.assertEqual(
			[growth_api.STEP_OVERALL],
			growth_api._steps_answered({"overall": {"text": "done"}}, values, ["g1"]))

	def test_a_step_with_only_blank_text_is_not_done(self):
		"""Typing a space is not an answer.

		**Updated for AC-90 (25 Sep 2026).** This used to pass NO goals and
		assert the answer was `[]` - which was pinning the old rule that a
		review with no goals could never finish step one, and that rule made
		Send unreachable for anybody with no goals. So the goals step is given
		a goal here, and the blank-text rule is what this test is about again.
		"""
		self.assertEqual(
			[], growth_api._steps_answered({"overall": {"text": "   "}}, [], ["g1"]))

	def test_a_review_with_no_goals_has_its_goals_step_answered(self):
		"""AC-90. Nothing to rate is not the same as not finished."""
		self.assertEqual(
			[growth_api.STEP_GOALS], growth_api._steps_answered({}, [], []))

	def test_a_half_point_rating_is_refused_by_the_save(self):
		self.as_user(self.rahul_user)
		with self.assertRaises(frappe.ValidationError) as caught:
			growth_api.save_self_review(
				self.appraisal, {"goals": {self.goal: {"rating": 3.5}}})
		self.assertIn("whole points", str(caught.exception))

	def test_a_save_reports_the_room_left_and_the_servers_own_time(self):
		"""AC-37 / AC-40. The screen can warn while somebody is still typing,
		and the time shown is the server's, not the browser's."""
		self.as_user(self.rahul_user)
		out = growth_api.save_self_review(
			self.appraisal, {"overall": {"text": "A short answer."}})
		self.assertTrue(out["saved_at"])
		self.assertGreater(out["room_left_characters"], 0)
		self.assertEqual(growth_api.PAGE_DATA_BUDGET_BYTES, out["budget_bytes"])

	def test_the_room_left_is_counted_in_the_language_being_typed(self):
		"""The number a Hindi writer is shown must be a number of THEIR
		characters.

		A fixed divisor would tell them to cut three times more than they need
		to, which is wrong in the direction that matters.
		"""
		english = json.dumps({"a": "x" * 3000})
		hindi = json.dumps({"a": DEVANAGARI * 3000}, ensure_ascii=False)
		room_en = growth_api.room_left_characters(english)
		room_hi = growth_api.room_left_characters(hindi)
		self.assertGreater(room_en, room_hi,
		                   "the same number of characters left room for the "
		                   "same amount in both scripts, so the count is not "
		                   "in bytes at all")
		self.assertAlmostEqual(3.0, growth_api.bytes_per_character(hindi), delta=0.2)
		self.assertAlmostEqual(1.0, growth_api.bytes_per_character(english), delta=0.2)

	def test_an_oversize_save_is_refused_with_a_sentence_and_loses_nothing(self):
		self.as_user(self.rahul_user)
		growth_api.save_self_review(self.appraisal, {"overall": {"text": "keep me"}})
		with self.assertRaises(frappe.ValidationError) as caught:
			growth_api.save_self_review(
				self.appraisal,
				{"overall": {"text": "y" * (growth_api.PAGE_DATA_BUDGET_BYTES + 500)}})
		self.assertIn("has been lost", str(caught.exception))
		# What was already saved is still there - which is exactly what the
		# sentence promises.
		out = growth_api.get_self_review(self.appraisal)
		self.assertIn("keep me", json.dumps(out["answers"]))

	def test_a_hindi_answer_is_refused_at_a_third_the_characters(self):
		"""The check a character-count budget would pass."""
		self.as_user(self.rahul_user)
		# The same number of CHARACTERS in both scripts. The English one fits
		# in the budget; the Devanagari one is three times the bytes and does
		# not. A character-count budget would accept both and the database
		# would then throw on the second.
		chars = 22000
		growth_api.save_self_review(self.appraisal, {"overall": {"text": "a" * chars}})
		with self.assertRaises(frappe.ValidationError):
			growth_api.save_self_review(
				self.appraisal, {"overall": {"text": DEVANAGARI * chars}})

	def test_the_stored_value_is_not_ascii_escaped(self):
		"""Writing `\\uXXXX` costs six bytes for a character that costs three.

		With the default, this code path was quietly giving a Hindi writer half
		the room the column allows.
		"""
		self.as_user(self.rahul_user)
		growth_api.save_self_review(
			self.appraisal, {"overall": {"text": DEVANAGARI * 10}})
		stored = frappe.db.get_value(
			"Alvoraa Appraisal Extension", {"appraisal": self.appraisal}, "page_data")
		self.assertIn(DEVANAGARI, stored)
		self.assertNotIn("\\u0915", stored)

	def test_no_cycle_gives_a_sentence_and_not_an_empty_wizard(self):
		"""AC-43."""
		frappe.db.set_value("Appraisal Cycle", self.cycle, "status", "Completed",
		                    update_modified=False)
		self.as_user(self.rahul_user)
		out = growth_api.get_self_review()
		self.assertEqual("", out["appraisal"])
		self.assertIn("no review running", out["note"])
