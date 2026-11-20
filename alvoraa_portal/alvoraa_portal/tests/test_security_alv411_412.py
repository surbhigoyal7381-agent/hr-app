"""ALV-411 and ALV-412 (20 Nov 2026), two gaps found while writing slice 087's
security requirements.

ALV-411  the attendance calls that change something answer POST only, so a link
         clicked by a signed-in HR person cannot approve or decline a request.
ALV-412  HR reads punches (the list, and one punch opened by name, so its photo
         too) only for the employees it may act for - the same rule ALV-385
         gave the reports. A System Manager still reads everything.

Fixtures are borrowed from test_held_day_085 by composition, as
test_company_scope_085 does, so its tests do not run twice.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import attendance_correction as ac
from alvoraa_portal import field_app_access as faa
from alvoraa_portal.tests import test_held_day_085 as hd


class ALV411WritesArePostOnly(FrappeTestCase):
	WRITES = ("raise_correction", "withdraw", "decide", "raise_for_report")

	def test_every_call_that_changes_attendance_answers_post_only(self):
		for name in self.WRITES:
			with self.subTest(call=name):
				self.assertEqual(
					frappe.allowed_http_methods_for_whitelisted_func.get(getattr(ac, name)), ["POST"])


class ALV412HrReadsInScope(FrappeTestCase):
	_n = 0

	def setUp(self):
		self.h = hd.HeldDayCase("test_held_is_a_status_and_the_fields_exist")
		self.h.setUp()
		self.a_worker = self.h.worker                                   # company A
		self.b_worker = self.h._employee("Bworker", company=self.h.other_company)
		self.a_punch = self._punch(self.a_worker)
		self.b_punch = self._punch(self.b_worker)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _punch(self, employee):
		ALV412HrReadsInScope._n += 1
		return frappe.get_doc({"doctype": "Employee Checkin", "employee": employee, "log_type": "IN",
		                       "time": "%s 08:%02d:00" % (add_days(nowdate(), -5), ALV412HrReadsInScope._n % 60)}
		                      ).insert(ignore_permissions=True)

	def _listed(self, user):
		frappe.set_user(user)
		try:
			return set(frappe.get_list("Employee Checkin", pluck="name",
			                           filters={"name": ["in", [self.a_punch.name, self.b_punch.name]]}))
		finally:
			frappe.set_user("Administrator")

	def test_hr_lists_only_punches_of_their_own_company(self):
		self.assertEqual(self._listed(self.h.hr), {self.a_punch.name})

	def test_hr_cannot_open_another_companys_punch_by_name(self):
		self.assertTrue(faa.checkin_has_permission(self.a_punch, self.h.hr, "read"))
		self.assertFalse(faa.checkin_has_permission(self.b_punch, self.h.hr, "read"))

	def test_a_company_user_permission_widens_reading_too(self):
		other = self.h._login("hrread", ("HR Manager",))
		self.h._employee("Hrread", other)  # company A by the Employee record
		self.assertEqual(self._listed(other), {self.a_punch.name})
		frappe.get_doc({"doctype": "User Permission", "user": other, "allow": "Company",
		                "for_value": self.h.other_company}).insert(ignore_permissions=True)
		frappe.clear_cache()
		self.assertEqual(self._listed(other), {self.b_punch.name})

	def test_hr_with_no_company_reads_no_one_elses_punches(self):
		nobody = self.h._login("hrnobody", ("HR Manager",))
		self.assertEqual(self._listed(nobody), set())
		self.assertFalse(faa.checkin_has_permission(self.a_punch, nobody, "read"))

	def test_a_system_manager_still_reads_every_company(self):
		boss = self.h._login("bossread", ("System Manager",))
		self.assertEqual(self._listed(boss), {self.a_punch.name, self.b_punch.name})
		self.assertTrue(faa.checkin_has_permission(self.b_punch, boss, "read"))
