"""ALV-242 — the backfill must settle demo tenants and must never touch DTC.

This script turns the first-use lock OFF for everybody on the site it runs on.
That is correct for a demo tenant, where nobody has ever used the change
password screen, and it is the one thing that must never happen on DTC, whose
staff are exactly the people the lock exists for.

So the test that matters most here is the refusal.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import first_use_backfill as backfill


def _rand():
	return frappe.utils.random_string(6).lower()


class BackfillCase(FrappeTestCase):
	def setUp(self):
		self._site = frappe.local.site

	def tearDown(self):
		frappe.local.site = self._site
		frappe.db.rollback()

	def make_user(self, chose_own_password=False):
		user = frappe.new_doc("User")
		user.email = f"bf242_{_rand()}@example.com"
		user.first_name = "Backfill"
		user.send_welcome_email = 0
		user.insert(ignore_permissions=True)
		if not chose_own_password:
			frappe.db.set_value("User", user.name, "last_password_reset_date", None,
			                    update_modified=False)
		else:
			frappe.db.set_value("User", user.name, "last_password_reset_date",
			                    frappe.utils.today(), update_modified=False)
		return user.name


class TestItRefusesDTC(BackfillCase):
	def test_it_refuses_to_run_on_dtc(self):
		"""The guard that stops one typo disarming the whole feature."""
		frappe.local.site = "dtc.alvoraa.co"
		with self.assertRaises(frappe.ValidationError):
			backfill.settle_existing_users()

	def test_dtc_is_actually_in_the_list(self):
		"""If somebody 'tidies' the list away, the test above still passes for
		the wrong reason."""
		self.assertIn("dtc.alvoraa.co", backfill.NEVER_SETTLE)

	def test_the_refusal_changes_nothing(self):
		user = self.make_user()
		frappe.local.site = "dtc.alvoraa.co"
		try:
			backfill.settle_existing_users()
		except frappe.ValidationError:
			pass
		self.assertIsNone(
			frappe.db.get_value("User", user, "last_password_reset_date"))


class TestItSettlesEverybodyElse(BackfillCase):
	def test_a_user_with_no_date_gets_one(self):
		user = self.make_user()
		self.assertIsNone(
			frappe.db.get_value("User", user, "last_password_reset_date"))

		backfill.settle_existing_users()

		self.assertIsNotNone(
			frappe.db.get_value("User", user, "last_password_reset_date"))

	def test_it_reports_what_it_did(self):
		self.make_user()
		result = backfill.settle_existing_users()
		self.assertGreaterEqual(result["settled"], 1)
		self.assertEqual(result["left"], 0)

	def test_it_does_not_move_a_date_somebody_already_has(self):
		"""Somebody who chose their own password last year keeps that date.
		Overwriting it would lose a real fact for no reason."""
		user = self.make_user(chose_own_password=True)
		frappe.db.set_value("User", user, "last_password_reset_date", "2025-01-01",
		                    update_modified=False)

		backfill.settle_existing_users()

		self.assertEqual(
			str(frappe.db.get_value("User", user, "last_password_reset_date")),
			"2025-01-01")

	def test_running_it_twice_is_harmless(self):
		self.make_user()
		first = backfill.settle_existing_users()
		second = backfill.settle_existing_users()
		self.assertGreaterEqual(first["settled"], 1)
		self.assertEqual(second["settled"], 0)


class TestTheLockAgreesAfterwards(BackfillCase):
	"""The point of the whole exercise: a settled user is not locked."""

	def test_a_settled_user_is_no_longer_treated_as_first_use(self):
		from alvoraa_portal import auth

		user = self.make_user()
		frappe.cache().delete_key(auth._CHOSEN_CACHE)
		self.assertFalse(auth._has_chosen_own_password(user))

		backfill.settle_existing_users()
		frappe.cache().delete_key(auth._CHOSEN_CACHE)

		self.assertTrue(auth._has_chosen_own_password(user))
