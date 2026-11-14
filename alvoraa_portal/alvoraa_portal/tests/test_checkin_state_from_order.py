"""After a machine punch, the app and portal say "Check out", not "Check in".

DTC's readers send a time and no In/Out. The screens asked "is today's last punch
an IN?", got no answer from a machine punch, and offered "Check in" to somebody who
had badged in at the door (client question, 13 Nov 2026). The day is now read in
order, the way the shift and the pay engine read it: first In, next Out, repeat
scans folded, real labels kept.
"""

from datetime import datetime

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime, today

from alvoraa_portal import hr_api
from alvoraa_portal.home_api import _checkin_today
from alvoraa_portal.payroll_rules import label_punches


def is_checked_in(rows):
	labelled = label_punches(rows)
	return bool(labelled) and labelled[-1]["log_type"] == "IN"


def _r(t, label=None):
	return {"time": "2026-11-13 " + t, "log_type": label}


class TheRule(FrappeTestCase):
	def test_one_unlabelled_punch_is_an_arrival(self):
		self.assertTrue(is_checked_in([_r("10:00:00")]))

	def test_two_unlabelled_punches_are_in_then_out(self):
		self.assertEqual([x["log_type"] for x in label_punches([_r("10:00:00"), _r("19:00:00")])], ["IN", "OUT"])
		self.assertFalse(is_checked_in([_r("10:00:00"), _r("19:00:00")]))

	def test_a_repeat_scan_does_not_flip_the_day(self):
		"""The reader stores one arrival twice, seconds apart: still in."""
		self.assertTrue(is_checked_in([_r("10:00:00"), _r("10:00:40")]))
		self.assertEqual([x["log_type"] for x in label_punches([_r("10:00:00"), _r("10:00:40"), _r("19:00:00")])],
		                 ["IN", "IN", "OUT"])

	def test_repeats_are_counted_in_whole_minutes_like_the_engine(self):
		"""10:00:05 and 10:02:50 are 165 seconds apart but 2 whole minutes, and the
		engine folds them (collapse_duplicate_punches). The button must agree."""
		from alvoraa_portal.payroll_rules import punch_minutes
		times = [datetime(2026, 11, 13, 10, 0, 5), datetime(2026, 11, 13, 10, 2, 50)]
		self.assertEqual(len(punch_minutes(times)), 1)
		self.assertTrue(is_checked_in([{"time": t, "log_type": None} for t in times]))

	def test_a_real_label_is_kept_and_sets_the_state(self):
		"""Machine in, app out at lunch, machine back: in, out, in."""
		rows = label_punches([_r("10:00:00"), _r("13:00:00", "OUT"), _r("14:00:00")])
		self.assertEqual([x["log_type"] for x in rows], ["IN", "OUT", "IN"])

	def test_labelled_days_read_exactly_as_before(self):
		self.assertTrue(is_checked_in([_r("10:00:00", "IN")]))
		self.assertFalse(is_checked_in([_r("10:00:00", "IN"), _r("19:00:00", "OUT")]))
		self.assertFalse(is_checked_in([]))

	def test_frappe_dicts_keep_their_attribute_access(self):
		rows = label_punches([frappe._dict(time=datetime(2026, 11, 13, 10), log_type=None)])
		self.assertEqual(rows[0].log_type, "IN")

	def test_nothing_is_written(self):
		row = _r("10:00:00")
		label_punches([row])
		self.assertIsNone(row["log_type"], "the caller's row is untouched")


class TheScreens(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.email = "machinein.alv@example.com"
		if not frappe.db.exists("User", self.email):
			frappe.get_doc({"doctype": "User", "email": self.email, "first_name": "MachineIn",
			                "send_welcome_email": 0}).insert(ignore_permissions=True)
		self.emp = frappe.db.get_value("Employee", {"user_id": self.email, "status": "Active"})
		if not self.emp:
			self.emp = frappe.get_doc({
				"doctype": "Employee", "first_name": "MachineIn",
				"company": frappe.db.get_value("Company", {}, "name"),
				"date_of_birth": "1990-01-01", "date_of_joining": "2015-01-01",
				"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
				"status": "Active", "user_id": self.email,
			}).insert(ignore_permissions=True).name
		frappe.db.delete("Employee Checkin", {"employee": self.emp, "time": (">=", today() + " 00:00:00")})
		# A machine punch: a time and a device, no In/Out - as DTC's readers send it.
		frappe.get_doc({"doctype": "Employee Checkin", "employee": self.emp,
		                "time": now_datetime(),
		                "device_id": "DTCTEST1"}).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_the_portal_button_offers_check_out(self):
		frappe.set_user(self.email)
		out = hr_api.get_checkin_status()
		self.assertTrue(out["checked_in"])
		self.assertEqual(out["todays_checkins"][0]["log_type"], "IN")

	def test_the_home_banner_agrees(self):
		self.assertEqual(_checkin_today(self.emp, today())["type"], "IN")
