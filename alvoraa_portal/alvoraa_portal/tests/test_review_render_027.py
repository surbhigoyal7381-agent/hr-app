"""Slice 027 - the server half of the review render fixes.

Found by the user's own testing on ppj.dev on 2026-09-19, and each test here
names the thing it keeps alive:

  * an unrated potential must not travel as a rating of zero, because the
    calibration grid then puts that person in the bottom-left box - a
    judgement nobody made;
  * a cycle launched from the wizard must keep its page list, because when
    page_config is empty every review renders without the page that shows its
    objectives and KPIs, and says nothing about it;
  * the PP Jewellers demo seed must write the same shapes the app writes,
    because it is what put both of the above into a live-looking tenant;
  * review numbers must freeze at the point Org Settings says, and not before;
  * a call that arrives without something it cannot work without must answer
    400, not 500.

The client half - the band a rating falls into, and the figures above the
charts - is pinned by scripts/check_rating_bands.js, which carries the user's
own arithmetic from that cycle.
"""

import json
import os

import frappe
from frappe.tests.utils import FrappeTestCase

import alvoraa_portal.performance_api as pa
from alvoraa_goals import review_items

from alvoraa_portal.tests.test_review_outside_010d import _CycleScreens


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


# ══════════════════════════════════════════════════════════════════════════
# An unrated rating is not a rating of zero
# ══════════════════════════════════════════════════════════════════════════

class TestUnratedIsNotZero(FrappeTestCase):
	"""The rating fields are Floats, so "never rated" is stored as 0.0.

	Sending that 0.0 to the calibration grid put an unrated person in Risk -
	low performance, low potential - while the header still counted them as
	plotted. 0 is not an answer on any scale in the product, which starts at 1.
	"""

	def test_a_stored_zero_is_reported_as_no_rating(self):
		self.assertIsNone(pa._rating_or_none(0))
		self.assertIsNone(pa._rating_or_none(0.0))
		self.assertIsNone(pa._rating_or_none(None))
		self.assertIsNone(pa._rating_or_none(""))

	def test_a_real_rating_survives_unchanged_including_a_half_point(self):
		self.assertEqual(pa._rating_or_none(4.5), 4.5)
		self.assertEqual(pa._rating_or_none(1), 1.0)
		self.assertEqual(pa._rating_or_none("3.5"), 3.5)


class TestMatrixReportsUnratedAsNull(_CycleScreens):
	def test_an_unrated_potential_reaches_the_grid_as_null_not_as_zero(self):
		c = self._setup_cycle()

		# Take the potential rating off one review, the way a manager who never
		# answered that question leaves it.
		ext = self._ext(c.hrr.ap)
		ext.db_set("potential_rating", 0, update_modified=False)
		frappe.db.commit()

		self._as(self.hr_user)
		rows = {r["appraisal"]: r for r in pa.get_calibration_matrix(c.cycle)["rows"]}

		self.assertIn(c.hrr.ap, rows)
		self.assertIsNone(
			rows[c.hrr.ap]["potential_rating"],
			"an unrated potential must arrive as null - a 0 puts this person in Risk",
		)
		# Everyone else keeps their real rating.
		self.assertEqual(rows[c.own.ap]["potential_rating"], 5)
		self.assertEqual(rows[c.own.ap]["overall_rating"], 4)


# ══════════════════════════════════════════════════════════════════════════
# A cycle keeps the pages it was launched with
# ══════════════════════════════════════════════════════════════════════════

class TestCycleKeepsItsPages(FrappeTestCase):
	"""The gap that let the seed bug hide for a whole quarter.

	Nothing tested that Launch Cycle persists page_config, so when both PPJ
	cycles came back with an empty page list there was no way to tell the
	wizard apart from the thing that actually wrote it.
	"""

	CYCLE = "TEST-027-PAGES-CYCLE"

	def setUp(self):
		frappe.set_user("Administrator")
		self._ensure_company()
		self._cleanup()

	def tearDown(self):
		self._cleanup()
		frappe.set_user("Administrator")

	def _ensure_company(self):
		"""A cycle belongs to a company. A bare site has none."""
		if frappe.db.exists("Company", {"name": ["is", "set"]}):
			return
		frappe.get_doc({
			"doctype": "Company",
			"company_name": "Slice 027 Test Co",
			"abbr": "S027",
			"default_currency": "INR",
			"country": "India",
		}).insert(ignore_permissions=True)
		frappe.db.commit()

	def _cleanup(self):
		frappe.db.delete("Alvoraa Cycle Config", {"appraisal_cycle": self.CYCLE})
		frappe.db.delete("Appraisal Cycle", {"cycle_name": self.CYCLE})
		frappe.db.commit()

	def test_launching_a_cycle_keeps_its_page_list(self):
		pages = {"past-objectives": True, "future-objectives": True, "manager-feedback": True}
		pa.save_cycle_wizard(
			cycle_name=self.CYCLE,
			start_date="2026-01-01",
			end_date="2026-03-31",
			description="Slice 027 pin.",
			employee_fields=json.dumps({"designation": True}),
			page_config=json.dumps(pages),
			page_settings=json.dumps({"manager-feedback": {"show_potential": True}}),
			selected_employees=json.dumps([]),
		)

		stored = frappe.db.get_value("Alvoraa Cycle Config", self.CYCLE, "page_config")
		self.assertEqual(json.loads(stored), pages)

		read_back = pa.get_cycle_config(self.CYCLE)
		self.assertEqual(read_back["page_config"], pages)
		self.assertTrue(
			[k for k, on in read_back["page_config"].items() if on],
			"a launched cycle with no page is a review that can show nothing",
		)


class TestDemoSeedWritesWhatTheAppReads(FrappeTestCase):
	"""The PP Jewellers seed writes records the app then has to read.

	Twice it did not: page_config went in as "[]" (an empty page list, so no
	review could show an objective) and the calibration sign-off went in under
	"signed_on" while the app writes and reads "signed_at" (so the sign-off
	line stopped before the date). Neither is reachable from a unit test of the
	app, so the seed text itself is what is pinned.
	"""

	SEED = os.path.join(REPO_ROOT, "demo", "pp_jewellers", "seed_performance.py")

	def _seed_text(self):
		if not os.path.exists(self.SEED):
			self.skipTest("demo seed not present in this checkout")
		with open(self.SEED, encoding="utf-8") as fh:
			return fh.read()

	def test_the_seed_does_not_create_a_cycle_with_no_pages(self):
		text = self._seed_text()
		self.assertNotIn(
			'"page_config": "[]"', text,
			'the seed wrote an empty page list, so no review in the tenant could '
			'show an objective or a KPI',
		)
		self.assertIn("past-objectives", text)
		self.assertIn("manager-feedback", text)

	def test_the_seed_signs_off_under_the_field_the_app_reads(self):
		# The key it writes, not the word anywhere in the file - the comment
		# explaining the old name mentions it too.
		text = self._seed_text()
		self.assertNotIn('"signed_on":', text)
		self.assertIn('"signed_at":', text)

	def test_the_app_writes_signed_at(self):
		"""If the app ever renames this, the seed pin above must move with it."""
		import inspect
		self.assertIn('"signed_at"', inspect.getsource(pa.save_calibration_signoff))


# ══════════════════════════════════════════════════════════════════════════
# When a review's numbers close
# ══════════════════════════════════════════════════════════════════════════

class TestNumbersFreezeWhenTheSettingSays(FrappeTestCase):
	"""numbers_frozen reading 0 at Manager Review was questioned as a bug.

	It is not, on the shipped default: "HR sent" means the numbers close when
	HR sends, so a review still with its manager is genuinely still open. What
	matters is that the answer follows the setting rather than a guess, at
	every stage - so all three settings are pinned here.
	"""

	def test_manager_review_follows_the_freeze_setting(self):
		self.assertEqual(review_items.FREEZE_POINTS,
		                 (review_items.FREEZE_HR_SENT,
		                  review_items.FREEZE_MANAGER_SENT,
		                  review_items.FREEZE_SELF_SENT))

		frozen_at_manager_review = {
			point: review_items.is_past_freeze_point("Manager Review", point)
			for point in review_items.FREEZE_POINTS
		}
		self.assertEqual(frozen_at_manager_review, {
			# the shipped default: still open with the manager
			review_items.FREEZE_HR_SENT: False,
			review_items.FREEZE_MANAGER_SENT: False,
			# the self-review has been sent, so the numbers are already closed
			review_items.FREEZE_SELF_SENT: True,
		})

	def test_the_default_is_hr_sent_so_zero_at_manager_review_is_right(self):
		self.assertEqual(review_items.DEFAULTS["freeze_point"],
		                 review_items.FREEZE_HR_SENT)

	def test_every_stage_closes_at_the_point_it_should(self):
		expected = {
			("Employee Review", review_items.FREEZE_SELF_SENT): False,
			("Manager Review", review_items.FREEZE_SELF_SENT): True,
			("Manager Review", review_items.FREEZE_MANAGER_SENT): False,
			("Employee Final Review", review_items.FREEZE_MANAGER_SENT): True,
			("HR Review", review_items.FREEZE_HR_SENT): False,
			("Completed", review_items.FREEZE_HR_SENT): True,
		}
		got = {k: review_items.is_past_freeze_point(*k) for k in expected}
		self.assertEqual(got, expected)

	def test_an_unknown_stage_or_setting_counts_as_closed(self):
		"""Fails closed: no new fact slips into a review nobody can place."""
		self.assertTrue(review_items.is_past_freeze_point("Who Knows", review_items.FREEZE_HR_SENT))
		self.assertTrue(review_items.is_past_freeze_point("Manager Review", "Some Other Setting"))


# ══════════════════════════════════════════════════════════════════════════
# An incomplete request is a 400, not a 500
# ══════════════════════════════════════════════════════════════════════════

class TestIncompleteRequestIsFourHundred(FrappeTestCase):
	"""A missing required argument used to reach the caller as a 500.

	Frappe already drops keyword arguments a method does not declare, so an
	unknown argument was never the problem; a *required* one being absent
	raised a plain TypeError, and a 500 reads as "the server is broken" when
	the truth is "that request was incomplete".
	"""

	def setUp(self):
		frappe.set_user("Administrator")

	def test_the_error_class_answers_four_hundred(self):
		self.assertEqual(pa.MissingArgument.http_status_code, 400)

	def test_listing_appraisals_without_a_cycle_is_a_clean_400(self):
		for missing in (None, ""):
			with self.assertRaises(pa.MissingArgument) as caught:
				frappe.call(pa.hr_list_appraisals, cycle=missing)
			self.assertEqual(getattr(type(caught.exception), "http_status_code", 500), 400)

	def test_opening_a_review_without_an_appraisal_is_a_clean_400(self):
		with self.assertRaises(pa.MissingArgument):
			frappe.call(pa.get_manager_review)

	def test_an_unknown_argument_is_ignored_rather_than_fatal(self):
		"""Frappe drops it. Pinned so nobody 'fixes' a problem that is not there."""
		self.assertEqual(
			frappe.get_newargs(pa.get_manager_review, {"appraisal": "X", "bogus": 1}),
			{"appraisal": "X"},
		)

	def test_the_message_names_the_argument_and_nothing_else(self):
		"""No record, no person, no value in an error a stranger can trigger."""
		with self.assertRaises(pa.MissingArgument) as caught:
			frappe.call(pa.hr_list_appraisals)
		message = str(caught.exception)
		self.assertIn("cycle", message)
		self.assertNotIn("@", message)
