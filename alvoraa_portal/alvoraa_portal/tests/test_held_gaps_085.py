"""Slice 085 (ALV-392): the gaps the engineer's own tests left.

AC-9 and AC-11 through the real auto-attendance job (not a hand-made Attendance),
AC-62/63 and the "November only" promise of the backfill. Fixtures are borrowed
from test_held_day_085 by composition, so its 30 tests do not run twice.
"""

import importlib.util
import os

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, get_datetime, nowdate
from unittest.mock import patch

from alvoraa_portal.tests import test_held_day_085 as hd


class _Fixtures(FrappeTestCase):
	def setUp(self):
		self.h = hd.HeldDayCase("test_held_is_a_status_and_the_fields_exist")
		self.h.setUp()

	def tearDown(self):
		frappe.set_user("Administrator")

	def _run_auto_attendance(self):
		"""The 3-minute job, for the one shift, as the scheduler runs it."""
		shift = frappe.get_doc("Shift Type", hd.SHIFT)
		shift.process_attendance_after = add_days(self.h.day, -1)
		shift.last_sync_of_checkin = get_datetime("%s 23:00:00" % add_days(self.h.day, 1))
		shift.process_auto_attendance()

	def _rows(self, employee):
		return frappe.get_all("Attendance", filters={"employee": employee, "attendance_date": self.h.day,
		                                             "docstatus": ("<", 2)},
		                      fields=["name", "status", "creation", "docstatus"])


class AutoAttendance(_Fixtures):
	def test_ac9_the_job_itself_marks_a_one_punch_day_as_held(self):
		self.h._punch(self.h.worker, "09:00")
		self._run_auto_attendance()
		rows = self._rows(self.h.worker)
		self.assertEqual([r.status for r in rows], ["Held"])

	def test_ac11_three_more_ticks_leave_the_held_row_alone(self):
		self.h._punch(self.h.worker, "09:00")
		self._run_auto_attendance()
		before = self._rows(self.h.worker)
		self.assertEqual([r.status for r in before], ["Held"])
		for _ in range(3):
			self._run_auto_attendance()
		self.assertEqual(self._rows(self.h.worker), before)

	def test_ac10_switch_off_the_job_marks_a_one_punch_day_as_before(self):
		self.h.set_switch(0)
		self.h._punch(self.h.worker, "09:00")
		self._run_auto_attendance()
		self.assertEqual([r.status for r in self._rows(self.h.worker)], ["Absent"])


class Backfill(_Fixtures):
	def _script(self):
		spec = importlib.util.spec_from_file_location("held_backfill_gaps", hd.backfill_script_path())
		mod = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(mod)
		return mod

	def _marked_before_the_switch(self, day, company=None):
		"""A one-punch day marked by the real job while the switch was off."""
		self.h.day = day
		self.h.set_switch(0)
		emp = self.h._employee("Bf" + day[-2:] + frappe.generate_hash(length=3))
		self.h._punch(emp, "09:00")
		self._run_auto_attendance()
		self.h.set_switch(1)
		return emp, self._rows(emp)[0].name

	def test_a_one_punch_absent_day_from_the_real_job_is_a_candidate_and_only_november_is(self):
		mod = self._script()
		_, nov = self._marked_before_the_switch("2026-11-12")
		_, oct31 = self._marked_before_the_switch("2026-10-31")
		_, dec1 = self._marked_before_the_switch("2026-12-01")
		names = [r.name for r in mod.candidates(frappe, [self.h.company])]
		self.assertIn(nov, names)
		self.assertNotIn(oct31, names)
		self.assertNotIn(dec1, names)

	def test_a_company_with_the_switch_off_is_never_touched(self):
		mod = self._script()
		_, att = self._marked_before_the_switch("2026-11-13")
		self.assertNotIn(att, [r.name for r in mod.candidates(frappe, [self.h.other_company])])

	def test_ac62_a_day_inside_a_submitted_slip_is_skipped(self):
		mod = self._script()
		emp, att = self._marked_before_the_switch("2026-11-14")
		with patch("alvoraa_portal.held_day.is_in_final_slip", return_value=True):
			names = [r.name for r in mod.candidates(frappe, [self.h.company])]
		self.assertNotIn(att, names)


class SettingsSaveIsPostOnly(FrappeTestCase):
	"""ALV-411: saving the held-day settings changes data, so a GET link must
	never reach it. The portal already sends it as a POST (gpSend with args)."""

	def test_save_settings_accepts_post_only(self):
		from alvoraa_portal import held_day
		self.assertIn(held_day.save_settings, frappe.whitelisted)
		self.assertNotIn(held_day.save_settings, frappe.guest_methods)
		self.assertEqual(
			frappe.allowed_http_methods_for_whitelisted_func[held_day.save_settings], ["POST"])
