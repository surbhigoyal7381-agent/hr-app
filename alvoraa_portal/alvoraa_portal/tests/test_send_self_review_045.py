"""045 US-21 - Send: the self-review reaches the manager, whole.

**The failure this file is written against is a silent one.** A Send that
stored nothing would raise no error, show no red, and be found in a calibration
meeting weeks later. So most of these tests compare a **stored** value with the
value the person saw, rather than checking that nothing threw.

Two faults this branch really had, both found by reading the code and then
proved by running it:

* `get_self_review` handed back the whole `page_data` as `answers` while the
  save wrote under `page_data["wizard"]`. A draft did not survive a reload and
  each autosave buried the last one a level deeper (AC-97). A real browser
  showed `wizard.wizard.wizard.wizard` after two saves and a reload.
* `save_review_page` ran the SEC-1 row-key check only for the OLD screen's page
  key, so a `wizard` save stored unchecked keys (AC-92).

Everything here is driven as **Rahul**, a plain employee, and every assertion
that matters reads the database back.
"""

import json

import frappe
from frappe.utils import add_days, nowdate

from alvoraa_goals import review_items
from alvoraa_portal import growth_api, performance_api
from alvoraa_portal.tests.fixtures_045 import COMPANY
from alvoraa_portal.tests.test_growth_screen_045 import GrowthFixture

FOREIGN_GOAL = "S045 Not Rahul's Goal"

# The goal one test adds after everything was rated (AC-91). Named here
# because `setUp` has to take it out again - a send commits, and so does this.
ADDED_LATER = "S045 Added After Rating"


def ext_of(appraisal):
	return frappe.get_doc("Alvoraa Appraisal Extension", appraisal)


def rows_of(appraisal, item_type=None):
	ext = ext_of(appraisal)
	return [r for r in ext.review_items
	        if not r.removed and (item_type is None or r.item_type == item_type)]


class SendFixture(GrowthFixture):
	"""A review with its copies taken, put back to a draft before every test.

	**`submit_employee_review` commits**, so `tearDown`'s rollback does not undo
	a send. Each test therefore starts by putting the review back to
	`Employee Review` with no ratings and no page data - written here once, so
	no test can quietly depend on what the test before it left behind.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Sandeep's own review, in a cycle of its own, so the SEC-1 tests have
		# a real row belonging to somebody ELSE's review to name. Its own
		# cycle, because `test_growth_screen_045` makes one for Sandeep in the
		# shared cycle and a second Appraisal there would refuse its insert.
		cls.other_cycle = "S045 Send Other Cycle"
		if not frappe.db.exists("Appraisal Cycle", cls.other_cycle):
			frappe.get_doc({
				"doctype": "Appraisal Cycle", "cycle_name": cls.other_cycle,
				"company": COMPANY, "start_date": add_days(nowdate(), -30),
				"end_date": add_days(nowdate(), 60), "status": "In Progress",
			}).insert(ignore_permissions=True)
		cls.other_appraisal = frappe.db.get_value(
			"Appraisal", {"employee": cls.sandeep,
			              "appraisal_cycle": cls.other_cycle}, "name")
		if not cls.other_appraisal:
			cls.other_appraisal = frappe.get_doc({
				"doctype": "Appraisal", "employee": cls.sandeep,
				"appraisal_cycle": cls.other_cycle, "company": COMPANY,
			}).insert(ignore_permissions=True).name
		ext = performance_api._get_or_create_extension(cls.other_appraisal)
		cls.foreign_row = next(
			(r.name for r in ext.review_items if r.title == FOREIGN_GOAL), None)
		if not cls.foreign_row:
			row = ext.append("review_items", {
				"item_type": "Objective", "title": FOREIGN_GOAL,
				"target_value": 5, "weightage": 5})
			row.name = frappe.generate_hash(length=10)
			review_items.save_review_record(ext)
			cls.foreign_row = row.name
		frappe.db.commit()

	def setUp(self):
		super().setUp()
		self.as_user(self.rahul_user)
		# The first open takes the review's own copies of its items.
		performance_api.get_my_review(self.appraisal)
		reset_review(self.appraisal)
		self.goal_rows = rows_of(self.appraisal, "Objective")
		self.kpi_rows = [r for r in rows_of(self.appraisal)
		                 if r.item_type != "Objective"]
		self.values = growth_api.company_values_for(self.rahul)
		self.as_user(self.rahul_user)

	def every_value_rated(self, rating=4):
		return {v["name"]: {"rating": rating} for v in self.values}

	def full_answers(self, goal_rating=4, comment="shipped it early"):
		"""What a finished wizard posts: every goal and every value rated."""
		return {
			"goals": {row.name: {"rating": goal_rating, "comment": comment}
			          for row in self.goal_rows},
			"values": self.every_value_rated(),
			"open_items": {"text": "nothing left open"},
			"next": {"text": "the Diwali window again"},
			"overall": {"text": "a good period"},
		}

	def save_wizard(self, answers):
		return growth_api.save_self_review(self.appraisal, json.dumps(answers))

	def send(self, overall_comment=""):
		return performance_api.submit_employee_review(self.appraisal, overall_comment)

	@classmethod
	def tearDownClass(cls):
		"""**Leave the site as this file found it.**

		A send commits, so without this the review stays in `Manager Review`
		and every later file that saves a draft on it fails with "Your review
		is no longer editable". That really happened on the first run here, and
		it took five tests in `test_growth_screen_045` with it.

		**Sandeep's review is NOT deleted, and must not be.** A review record
		that holds copies is the record of how that review was decided, and
		`Alvoraa Appraisal Extension.on_trash` refuses to delete one (PRIV-14).
		It is fixture data in a cycle of its own instead.
		"""
		frappe.set_user("Administrator")
		reset_review(cls.appraisal)
		frappe.db.commit()
		super().tearDownClass()


def reset_review(appraisal):
	"""Put a review back to a clean draft, copies and all.

	`submit_employee_review` commits, and so does a removal, so a test that
	sends, removes a goal or adds one leaves it that way for every test after
	it - in this file and in every file that runs later.
	"""
	frappe.set_user("Administrator")
	ext = ext_of(appraisal)
	ext.review_status = "Employee Review"
	ext.page_data = "{}"
	ext.pages_completed = "[]"
	ext.next_period_goals_text = ""
	ext.overall_comment = ""
	# **Put the copies back too, not just the ratings.** The first run of this
	# file proved why: one test removed both goal copies to check AC-90 and
	# nine later tests then failed with an empty goal list.
	for row in list(ext.review_items):
		if row.title == ADDED_LATER:
			ext.remove(row)
			continue
		row.removed = 0
		row.removed_at_stage = None
		row.removed_on = None
		row.removed_by = None
		row.removal_reason = ""
		row.self_rating = 0
		row.self_comment = ""
		row.self_rated_on = None
	review_items.save_review_record(ext)
	frappe.db.commit()



class TestTheRatingLands(SendFixture):
	"""AC-87, AC-88. The whole reason US-21 exists."""

	def test_the_rating_lands_on_the_reviews_own_copy_with_its_stamp(self):
		row = self.goal_rows[0]
		before = frappe.db.get_value(
			"Alvoraa Review Item", row.name,
			["actual_value", "target_value", "weightage"], as_dict=True)
		answers = self.full_answers()
		answers["goals"][row.name] = {
			"rating": 4, "comment": "shipped the Diwali window two weeks early"}
		self.save_wizard(answers)
		self.send()

		stored = frappe.db.get_value(
			"Alvoraa Review Item", row.name,
			["self_rating", "self_comment", "self_rated_on", "self_flag",
			 "self_basis_actual", "self_basis_target", "self_basis_weightage"],
			as_dict=True)
		self.assertEqual(4.0, stored.self_rating)
		self.assertEqual("shipped the Diwali window two weeks early",
		                 stored.self_comment)
		self.assertTrue(stored.self_rated_on, "no stamp, so nobody can tell when")
		self.assertEqual(0, stored.self_flag)
		# The numbers the person was looking at, not the numbers today. This is
		# what makes AC-96 answerable a year later.
		self.assertEqual(before.actual_value, stored.self_basis_actual)
		self.assertEqual(before.target_value, stored.self_basis_target)
		self.assertEqual(before.weightage, stored.self_basis_weightage)

	def test_the_assertion_can_fail(self):
		"""Check the check: an unsent review has no rating on that row."""
		row = self.goal_rows[0]
		self.assertEqual(
			0.0, frappe.db.get_value("Alvoraa Review Item", row.name, "self_rating"),
			"the row was already rated before the test did anything, so the "
			"test above proves nothing")

	def test_a_half_point_is_refused_by_the_send_as_well_as_the_save(self):
		"""The save checks it; so does the send. Anybody can post to either."""
		answers = self.full_answers()
		answers["goals"][self.goal_rows[0].name] = {"rating": 3.5}
		ext = ext_of(self.appraisal)
		ext.page_data = json.dumps({"wizard": answers})
		review_items.save_review_record(ext)
		frappe.db.commit()
		self.as_user(self.rahul_user)
		with self.assertRaises(frappe.ValidationError) as caught:
			self.send()
		self.assertIn("whole points", str(caught.exception))

	def test_nothing_outside_the_review_is_written(self):
		"""AC-88. R13 re-asserted on the new path rather than trusted."""
		def snapshot():
			return {
				"goal": frappe.db.get_value(
					"Individual Goal", self.goal, "*", as_dict=True),
				"kpi": frappe.db.get_value("KPI", self.kpi, "*", as_dict=True),
			}

		before = snapshot()
		self.save_wizard(self.full_answers())
		self.send()
		after = snapshot()
		for what in ("goal", "kpi"):
			for field, value in before[what].items():
				self.assertEqual(value, after[what][field],
				                 f"Send changed {what}.{field}, which is not "
				                 "part of the review at all")


class TestAPartFinishedReviewCannotBeSent(SendFixture):
	"""AC-89, AC-90, AC-91 - and the endpoint is called directly, no browser.

	A rule only the screen keeps is not a rule.
	"""

	def test_an_unrated_goal_refuses_the_send_and_writes_nothing(self):
		answers = self.full_answers()
		answers["goals"].pop(self.goal_rows[0].name)
		self.save_wizard(answers)
		with self.assertRaises(frappe.ValidationError) as caught:
			self.send()
		message = str(caught.exception)
		self.assertIn("still needs a rating", message)
		self.assertIn(self.goal_rows[0].title, message,
		              "the refusal does not say WHICH goal")
		self.assertEqual("Employee Review",
		                 frappe.db.get_value("Alvoraa Appraisal Extension",
		                                     self.appraisal, "review_status"))
		for row in self.goal_rows:
			self.assertEqual(
				0.0,
				frappe.db.get_value("Alvoraa Review Item", row.name, "self_rating"),
				"a rating was written by a send that was refused")

	def test_an_unrated_company_value_refuses_the_send(self):
		answers = self.full_answers()
		answers["values"].pop(self.values[0]["name"])
		self.save_wizard(answers)
		with self.assertRaises(frappe.ValidationError) as caught:
			self.send()
		self.assertIn("still needs a rating", str(caught.exception))
		self.assertIn(self.values[0]["value_name"], str(caught.exception))

	def test_a_review_with_no_goals_can_still_be_sent(self):
		"""AC-90. With `goals and all(...)` the step could never be done."""
		frappe.set_user("Administrator")
		ext = ext_of(self.appraisal)
		for row in ext.review_items:
			if row.item_type == "Objective":
				row.removed = 1
				row.removed_at_stage = "Employee Review"
		review_items.save_review_record(ext)
		frappe.db.commit()
		self.as_user(self.rahul_user)
		answers = {"values": self.every_value_rated()}
		self.save_wizard(answers)
		self.assertIn(growth_api.STEP_GOALS,
		              growth_api._steps_answered(answers, self.values, []),
		              "a review with no goals could never finish step one")
		self.assertEqual("Manager Review", self.send()["review_status"])

	def test_a_goal_added_after_the_rating_blocks_the_send(self):
		"""AC-91. The check reads the review's live copies at the moment of
		Send, never the list the browser was holding."""
		self.save_wizard(self.full_answers())
		frappe.set_user("Administrator")
		ext = ext_of(self.appraisal)
		added = ext.append("review_items", {
			"item_type": "Objective", "title": ADDED_LATER,
			"target_value": 10, "weightage": 10,
		})
		review_items.save_review_record(ext)
		frappe.db.commit()
		self.as_user(self.rahul_user)
		with self.assertRaises(frappe.ValidationError) as caught:
			self.send()
		self.assertIn(ADDED_LATER, str(caught.exception))
		self.assertEqual(
			0.0, frappe.db.get_value("Alvoraa Review Item", added.name, "self_rating"))
		self.assertEqual("Employee Review",
		                 frappe.db.get_value("Alvoraa Appraisal Extension",
		                                     self.appraisal, "review_status"))

	def test_d13_is_one_line_and_the_written_steps_are_optional_today(self):
		"""D-13's recommended default, built and named.

		The ratings are required; the three written steps are not, and the ones
		left empty are listed so nobody sends a blank without noticing.
		"""
		self.assertEqual((growth_api.STEP_GOALS, growth_api.STEP_VALUES),
		                 growth_api.REQUIRED_STEPS)
		answers = self.full_answers()
		for step in ("open_items", "next", "overall"):
			answers.pop(step)
		self.save_wizard(answers)
		self.assertEqual(["open_items", "next", "overall"],
		                 growth_api.blank_optional_steps(answers))
		self.assertEqual("Manager Review", self.send()["review_status"])


class TestTheKeyCheckRunsOnTheWizardsPage(SendFixture):
	"""AC-92, AC-93. The guard that was not running on the new screen."""

	def test_a_row_from_somebody_elses_review_is_refused_by_the_save(self):
		foreign = self.foreign_row
		before = frappe.db.get_value("Alvoraa Appraisal Extension",
		                             self.appraisal, "page_data")
		self.as_user(self.rahul_user)
		with self.assertRaises(frappe.PermissionError):
			self.save_wizard({"goals": {foreign: {"rating": 5}}})
		self.assertEqual(before,
		                 frappe.db.get_value("Alvoraa Appraisal Extension",
		                                     self.appraisal, "page_data"),
		                 "the refused save was stored anyway")

	def test_a_row_that_was_removed_from_this_review_is_refused(self):
		frappe.set_user("Administrator")
		ext = ext_of(self.appraisal)
		gone = next(r for r in ext.review_items if r.item_type == "Objective")
		gone.removed = 1
		gone.removed_at_stage = "Employee Review"
		review_items.save_review_record(ext)
		frappe.db.commit()
		self.as_user(self.rahul_user)
		with self.assertRaises(frappe.PermissionError):
			self.save_wizard({"goals": {gone.name: {"rating": 5}}})

	def test_the_check_really_is_new_on_this_key(self):
		"""Check the check: the SAME payload under the OLD key is refused too,
		which is what makes this a guard that moved rather than one invented."""
		foreign = self.foreign_row
		self.as_user(self.rahul_user)
		with self.assertRaises(frappe.PermissionError):
			performance_api.save_review_page(
				self.appraisal, "past-objectives",
				json.dumps({"objectives": {foreign: {"reflection": "x"}}}))

	def test_a_kpi_row_name_in_the_goals_block_is_refused(self):
		"""AC-93. Surbhi's decision made enforceable: goals are rated, KPI
		figures are shown beside them."""
		kpi_row = self.kpi_rows[0]
		self.as_user(self.rahul_user)
		with self.assertRaises(frappe.PermissionError) as caught:
			self.save_wizard({"goals": {kpi_row.name: {"rating": 5}}})
		self.assertIn("not rated", str(caught.exception))
		self.assertEqual(
			0.0,
			frappe.db.get_value("Alvoraa Review Item", kpi_row.name, "self_rating"))


class TestTheKpiHalfIsLeftAlone(SendFixture):
	"""AC-94, in both directions."""

	def test_a_kpi_rated_on_the_old_screen_still_reads_the_same_after_a_send(self):
		kpi_row = self.kpi_rows[0]
		frappe.set_user("Administrator")
		frappe.db.set_value("Alvoraa Review Item", kpi_row.name,
		                    {"self_rating": 3, "self_rated_on": "2026-09-01 10:00:00"},
		                    update_modified=False)
		frappe.db.commit()
		before = frappe.db.get_value("Alvoraa Review Item", kpi_row.name,
		                             ["self_rating", "self_rated_on"], as_dict=True)
		self.as_user(self.rahul_user)
		self.save_wizard(self.full_answers())
		self.send()
		after = frappe.db.get_value("Alvoraa Review Item", kpi_row.name,
		                            ["self_rating", "self_rated_on"], as_dict=True)
		self.assertEqual(3.0, after.self_rating)
		self.assertEqual(before.self_rated_on, after.self_rated_on)

	def test_a_kpi_the_wizard_never_touched_stays_at_nothing(self):
		kpi_row = self.kpi_rows[0]
		self.save_wizard(self.full_answers())
		self.send()
		self.assertEqual(
			0.0,
			frappe.db.get_value("Alvoraa Review Item", kpi_row.name, "self_rating"),
			"the wizard derived a KPI rating from the goal's")

	def test_no_wave_four_code_names_self_rating_at_all(self):
		"""A static check, because 'nothing derives it' is the kind of rule
		that gets broken by a helpful line four commits later.

		`growth_api` never names `self_rating`. The only thing that writes one
		is `review_items.set_item_rating`, which is the shared function with the
		stamp in it - so there is no second place a KPI rating could be written
		from the wizard's side. Comments and docstrings do not count: this walks
		the parsed tree, not the text.
		"""
		import ast
		import inspect

		tree = ast.parse(inspect.getsource(growth_api))
		named = [node for node in ast.walk(tree)
		         if (isinstance(node, ast.Attribute) and node.attr == "self_rating")
		         or (isinstance(node, ast.Constant) and node.value == "self_rating")]
		self.assertEqual([], named,
		                 "growth_api names self_rating in code, so there is a "
		                 "second place a KPI rating could be written from")

	def test_that_static_check_can_fail(self):
		"""Check the check: the same walk over a module that DOES name it."""
		import ast
		import inspect

		from alvoraa_goals import review_items

		tree = ast.parse(inspect.getsource(review_items))
		named = [node for node in ast.walk(tree)
		         if (isinstance(node, ast.Attribute) and node.attr == "self_rating")
		         or (isinstance(node, ast.Constant) and node.value == "self_rating")]
		self.assertTrue(named, "the walk finds nothing anywhere, so it proves "
		                       "nothing above either")


class TestSendingTwiceChangesNothing(SendFixture):
	"""AC-95, and AC-36's 'one notification' with it."""

	def _notifications(self):
		return frappe.db.count("Notification Log", {"document_name": self.appraisal})

	def test_the_second_send_is_refused_and_nothing_moves(self):
		self.save_wizard(self.full_answers())
		self.send()
		after_one = {
			row.name: frappe.db.get_value(
				"Alvoraa Review Item", row.name,
				["self_rating", "self_comment", "self_rated_on"], as_dict=True)
			for row in self.goal_rows}
		notifications = self._notifications()
		goals_before = frappe.db.count("Individual Goal", {"employee": self.rahul})

		with self.assertRaises(frappe.ValidationError) as caught:
			self.send()
		self.assertIn("already been sent", str(caught.exception))
		self.assertEqual("Manager Review",
		                 frappe.db.get_value("Alvoraa Appraisal Extension",
		                                     self.appraisal, "review_status"))
		for name, was in after_one.items():
			self.assertEqual(
				was,
				frappe.db.get_value("Alvoraa Review Item", name,
				                    ["self_rating", "self_comment", "self_rated_on"],
				                    as_dict=True))
		self.assertEqual(notifications, self._notifications(),
		                 "a second notification went out")
		self.assertEqual(goals_before,
		                 frappe.db.count("Individual Goal", {"employee": self.rahul}),
		                 "a second next-period goal was created")

	def test_the_manager_is_notified_once_and_the_review_is_not_in_the_message(self):
		"""AC-36. The name and the cycle, and nothing from inside the review."""
		before = self._notifications()
		self.save_wizard(self.full_answers(comment="a private reflection"))
		self.send()
		rows = frappe.get_all(
			"Notification Log", filters={"document_name": self.appraisal},
			fields=["for_user", "subject", "email_content"],
			order_by="creation desc")
		self.assertEqual(before + 1, len(rows))
		manager_user = frappe.db.get_value("Employee", self.sandeep, "user_id")
		self.assertEqual(manager_user, rows[0]["for_user"])
		whole = rows[0]["subject"] + (rows[0]["email_content"] or "")
		self.assertNotIn("a private reflection", whole)
		self.assertNotIn(self.goal_rows[0].title, whole)


class TestWhatIsStoredIsWhatWasOnScreen(SendFixture):
	"""AC-96 - the point of US-21, and the one that catches a silent Send."""

	def test_the_stored_answers_read_back_equal_to_what_was_posted(self):
		posted = self.full_answers(goal_rating=5, comment="काम पूरा हुआ")
		posted["open_items"] = {"text": "पिछली बार से कुछ बाकी नहीं"}
		self.save_wizard(posted)
		self.send()

		read_back = growth_api.get_self_review(self.appraisal)
		# **The WHOLE structure, key for key.** A spot check on one field is
		# how a half-written Send passes.
		self.assertEqual(posted, read_back["answers"])
		# Devanagari stored as itself, not escaped to \uXXXX.
		stored = frappe.db.get_value("Alvoraa Appraisal Extension",
		                             self.appraisal, "page_data")
		self.assertIn("काम पूरा हुआ", stored)

		# Every goal's rating equals the number the screen showed, and the
		# number of rated goals equals the number of ratings given.
		on_screen = {name: entry["rating"] for name, entry in posted["goals"].items()}
		in_database = {
			row.name: frappe.db.get_value("Alvoraa Review Item", row.name, "self_rating")
			for row in self.goal_rows}
		self.assertEqual({k: float(v) for k, v in on_screen.items()}, in_database)
		self.assertEqual(len(on_screen), sum(1 for v in in_database.values() if v > 0))

		# Every value he rated carries its rating.
		for value in self.values:
			self.assertEqual(
				posted["values"][value["name"]]["rating"],
				read_back["answers"]["values"][value["name"]]["rating"])

	def test_the_manager_receives_what_was_sent(self):
		"""AC-99, including the limitation this slice is NOT fixing."""
		posted = self.full_answers(goal_rating=3, comment="steady")
		self.save_wizard(posted)
		self.send()
		self.as_user(self.sandeep_user)
		payload = performance_api.get_manager_review(self.appraisal, "manager")
		self.assertEqual(posted, payload["page_data"]["wizard"])
		drawn = {g["name"]: g for g in payload["goals"]}
		for row in self.goal_rows:
			self.assertEqual(3.0, drawn[row.name]["self_rating"])
			self.assertEqual("steady", drawn[row.name]["self_comment"])
		frappe.set_user("Administrator")
		ext = ext_of(self.appraisal)
		self.assertEqual("the Diwali window again", ext.next_period_goals_text)
		self.assertEqual("a good period", ext.overall_comment)
		# **Declared limitation, asserted rather than promised.** The manager's
		# screen draws its pages from `page_config`, which does not know the
		# wizard's keys - so the company-value ratings travel in the payload
		# and are not drawn. Named in the notes with an owner; this asserts the
		# payload half, which is all this slice claims.
		self.assertNotIn("wizard", json.dumps(payload.get("page_config") or {}))


class TestTheDraftSurvivesAReload(SendFixture):
	"""AC-97 - the live loss this branch had, with the shape asserted."""

	def test_a_saved_draft_comes_back_at_the_top_level(self):
		answers = {"goals": {self.goal_rows[0].name: {"rating": 2}}}
		self.save_wizard(answers)
		out = growth_api.get_self_review(self.appraisal)
		self.assertEqual(answers, out["answers"])
		self.assertNotIn("wizard", out["answers"],
		                 "the whole page_data came back instead of the "
		                 "wizard's own block")

	def test_a_second_save_does_not_bury_the_first(self):
		"""What the browser really did: read the payload, post it back."""
		first = {"goals": {self.goal_rows[0].name: {"rating": 2}}}
		self.save_wizard(first)
		handed_back = growth_api.get_self_review(self.appraisal)["answers"]
		self.save_wizard(handed_back)          # exactly what the screen does
		stored = json.loads(frappe.db.get_value(
			"Alvoraa Appraisal Extension", self.appraisal, "page_data"))
		self.assertEqual(first, stored["wizard"])
		self.assertNotIn("wizard", stored["wizard"],
		                 "the answers were buried one level deeper")

	def test_the_step_count_counts_the_draft(self):
		""""Step n of 5" was reading an empty wizard too."""
		self.save_wizard({"overall": {"text": "something"}})
		out = growth_api.get_self_review(self.appraisal)
		self.assertIn(growth_api.STEP_OVERALL, out["steps_answered"])


class TestOnePageKeyPerScreen(SendFixture):
	"""AC-98. A review half-typed on each screen keeps both."""

	def test_the_old_block_is_applied_first_and_the_wizard_wins(self):
		goal = self.goal_rows[0]
		kpi_row = self.kpi_rows[0]
		frappe.set_user("Administrator")
		ext = ext_of(self.appraisal)
		ext.page_data = json.dumps({
			# The OLD screen's block: a KPI rating and a goal reflection, plus
			# a goal rating the wizard disagrees with is not possible on that
			# screen - it only ever wrote a reflection - so the conflict is on
			# the comment.
			"past-objectives": {
				"kpis": {kpi_row.name: {"self_rating": 2,
				                        "self_comment": "the old screen's"}},
				"objectives": {goal.name: {"reflection": "typed on the old screen"}},
			},
			"wizard": self.full_answers(goal_rating=5, comment="typed in the wizard"),
		})
		review_items.save_review_record(ext)
		frappe.db.commit()
		self.as_user(self.rahul_user)
		self.send()

		# The KPI rating from the old screen survives...
		self.assertEqual(
			2.0,
			frappe.db.get_value("Alvoraa Review Item", kpi_row.name, "self_rating"))
		# ...and the wizard wins on the row both name.
		stored = frappe.db.get_value("Alvoraa Review Item", goal.name,
		                             ["self_rating", "self_comment"], as_dict=True)
		self.assertEqual(5.0, stored.self_rating)
		self.assertEqual("typed in the wizard", stored.self_comment)


class TestTheOldScreenIsNotHeldToTheWizardsRule(SendFixture):
	"""The rule that was found by breaking three of somebody else's tests.

	The old Objectives & KPIs screen still ships. It has never required a
	rating on every goal - it rates KPIs and writes a reflection on a goal - so
	holding it to the wizard's finished rule refused three tests in
	`test_review_screens_010d`. The rule is scoped to the page key, and the KEY
	is what decides it, not whether the block has anything in it.
	"""

	def _write_page_data(self, page_data):
		frappe.set_user("Administrator")
		ext = ext_of(self.appraisal)
		ext.page_data = json.dumps(page_data)
		review_items.save_review_record(ext)
		frappe.db.commit()
		self.as_user(self.rahul_user)

	def test_a_review_with_no_wizard_block_sends_as_it_always_did(self):
		"""Not one goal is rated, and it still sends - because nothing here
		came from the wizard."""
		self._write_page_data({"past-objectives": {
			"kpis": {self.kpi_rows[0].name: {"self_rating": 3}},
			"objectives": {self.goal_rows[0].name: {"reflection": "a reflection"}},
		}})
		self.assertEqual("Manager Review", self.send()["review_status"])
		self.assertEqual(
			0.0,
			frappe.db.get_value("Alvoraa Review Item", self.goal_rows[0].name,
			                    "self_rating"),
			"the old screen's submit invented a goal rating")

	def test_an_empty_wizard_block_still_has_to_answer_for_itself(self):
		"""The key, not its contents. An empty wizard block is a wizard that
		was opened and saved, and it is refused like any other unfinished
		one."""
		self._write_page_data({"wizard": {}})
		with self.assertRaises(frappe.ValidationError) as caught:
			self.send()
		# Two goals are unrated here, so the sentence is the plural one - which
		# is why this is a pattern and not a fixed string. The first run of
		# this test looked for "still needs a rating" and went red on
		# "2 goals still need a rating", which is the sentence being right.
		self.assertRegex(str(caught.exception), "still needs? a rating")
