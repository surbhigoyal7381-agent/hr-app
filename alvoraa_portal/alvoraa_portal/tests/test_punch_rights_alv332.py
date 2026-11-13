"""ALV-332, ALV-333 and ALV-328's switch: who may read and who may change a punch.

A punch decides pay. Outside HR it is read-only: a person may file a new punch
of their own and read the punches they are allowed to see, and nobody outside
HR edits, deletes or shares one (ALV-332 for managers, ALV-333 for the person
themselves). A manager reads their direct reports' punches; with the HR Settings
switch on, their whole Active line (ALV-328). Only a System Manager flips it.

The checks run through Frappe's own permission entry points - `has_permission`,
`get_list`, `frappe.client.*` and `delete_doc` - which are what REST GET, PUT and
DELETE call. EVERY PERSON HERE IS MADE UP.
"""

from unittest.mock import patch

import frappe
import frappe.client
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import field_app_access
from alvoraa_portal.field_app_access import WHOLE_LINE_SETTING, whole_line_on

CHECKIN = "Employee Checkin"
COMPANY = "ALV332 Punch Co"
WHEN = "2025-02-03 10:00:00"


def _gender():
	return frappe.db.get_value("Gender", {}, "name") or frappe.get_doc(
		{"doctype": "Gender", "gender": "Other"}).insert(ignore_permissions=True).name


def setUpModule():
	frappe.set_user("Administrator")
	if not frappe.db.exists("Company", COMPANY):
		frappe.get_doc({"doctype": "Company", "company_name": COMPANY, "abbr": "A332",
		                "default_currency": "INR", "country": "India"}).insert(ignore_permissions=True)
	frappe.db.set_single_value("HR Settings", WHOLE_LINE_SETTING, 0)
	frappe.db.commit()


class PunchCase(FrappeTestCase):
	_n = 0

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		PunchCase._n += 1
		t = "%s%d" % (cls.__name__[:5], PunchCase._n)
		# Arjun > Kavita > Rohan, and Arjun > Lena (left) > Sam, and Kavita > Ina (inactive).
		cls.arjun, cls.arjun_mail = cls.person("Arj" + t)
		cls.kavita, cls.kavita_mail = cls.person("Kav" + t, reports_to=cls.arjun)
		cls.rohan, cls.rohan_mail = cls.person("Roh" + t, reports_to=cls.kavita)
		cls.lena, cls.lena_mail = cls.person("Len" + t, reports_to=cls.arjun)
		cls.sam, cls.sam_mail = cls.person("Sam" + t, reports_to=cls.lena)
		cls.ina, cls.ina_mail = cls.person("Ina" + t, reports_to=cls.kavita)
		cls.priya, cls.priya_mail = cls.person("Pri" + t)
		cls.meena, cls.meena_mail = cls.person("Mee" + t, roles=("HR Manager",))
		cls.punches = {e: cls.punch(e) for e in (cls.arjun, cls.kavita, cls.rohan, cls.lena,
		                                          cls.sam, cls.ina, cls.priya)}
		frappe.db.set_value("Employee", cls.lena, "status", "Left")
		frappe.db.set_value("Employee", cls.ina, "status", "Inactive")

	@classmethod
	def person(cls, first, reports_to=None, roles=()):
		email = "%s.alv332@example.com" % first.lower()
		if not frappe.db.exists("User", email):
			u = frappe.get_doc({"doctype": "User", "email": email, "first_name": first,
			                    "send_welcome_email": 0}).insert(ignore_permissions=True)
			u.add_roles("Employee", *roles)
		e = frappe.get_doc({
			"doctype": "Employee", "first_name": first, "company": COMPANY,
			"date_of_birth": "1980-01-01", "date_of_joining": "2000-01-01",
			"gender": _gender(),
			"status": "Active", "user_id": email, "reports_to": reports_to,
		}).insert(ignore_permissions=True)
		return e.name, email

	@classmethod
	def punch(cls, employee):
		return frappe.get_doc({"doctype": CHECKIN, "employee": employee, "time": WHEN,
		                       "latitude": 28.6, "longitude": 77.2, "skip_auto_attendance": 1,
		                       }).insert(ignore_permissions=True).name

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("HR Settings", WHOLE_LINE_SETTING, 0)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("HR Settings", WHOLE_LINE_SETTING, 0)

	def may(self, user, ptype, employee):
		return frappe.has_permission(CHECKIN, ptype, doc=self.punches[employee], user=user)

	def listed(self, user):
		"""Whose punches this user's list shows - Frappe's get_list, our query condition."""
		frappe.set_user(user)
		try:
			return set(frappe.get_list(CHECKIN, filters={"time": WHEN}, pluck="employee",
			                           limit_page_length=0))
		finally:
			frappe.set_user("Administrator")

	def as_user(self, user, call):
		frappe.set_user(user)
		try:
			return call()
		finally:
			frappe.set_user("Administrator")


class ReadOnlyOutsideHR(PunchCase):
	def test_alv333_a_person_reads_their_own_punch_and_cannot_change_it(self):
		self.assertTrue(self.may(self.rohan_mail, "read", self.rohan))
		for ptype in ("write", "delete", "share", "email", "print", None):
			self.assertFalse(self.may(self.rohan_mail, ptype, self.rohan), ptype)

	def test_alv332_a_manager_reads_a_report_punch_and_cannot_change_it(self):
		self.assertTrue(self.may(self.kavita_mail, "read", self.rohan))
		for ptype in ("write", "delete", "share", None):
			self.assertFalse(self.may(self.kavita_mail, ptype, self.rohan), ptype)

	def test_alv332_the_doors_rest_uses_refuse_a_change(self):
		"""PUT is `frappe.client.set_value`'s save; DELETE is `delete_doc`."""
		name = self.punches[self.rohan]
		for user in (self.rohan_mail, self.kavita_mail):
			with self.assertRaises(frappe.PermissionError):
				self.as_user(user, lambda: frappe.client.set_value(CHECKIN, name, "device_id", "X"))
			with self.assertRaises(frappe.PermissionError):
				self.as_user(user, lambda: frappe.client.delete(CHECKIN, name))
		self.assertTrue(frappe.db.exists(CHECKIN, name))
		self.assertFalse(frappe.db.get_value(CHECKIN, name, "device_id"))

	def test_alv332_the_refusal_is_real(self):
		"""Negative control: with the read-only rule removed, the same delete passes.
		If this ever fails, the tests above prove nothing."""
		with patch.object(field_app_access, "_READ_RIGHTS", ("read", "select", "write", "delete")):
			self.assertTrue(self.may(self.kavita_mail, "delete", self.rohan))
			self.assertTrue(self.may(self.rohan_mail, "write", self.rohan))

	def test_alv333_a_person_may_still_file_their_own_new_punch(self):
		doc = frappe.get_doc({"doctype": CHECKIN, "employee": self.rohan, "log_type": "IN",
		                      "latitude": 28.6, "longitude": 77.2})
		self.as_user(self.rohan_mail, doc.insert)
		self.assertTrue(frappe.db.exists(CHECKIN, doc.name))

	def test_alv332_a_manager_cannot_file_a_punch_for_a_report(self):
		"""D1 (Surbhi, 12 Nov 2026): only HR and the machine add someone else's punch."""
		doc = frappe.get_doc({"doctype": CHECKIN, "employee": self.rohan, "log_type": "IN",
		                      "latitude": 28.6, "longitude": 77.2})
		with self.assertRaises(frappe.PermissionError):
			self.as_user(self.kavita_mail, doc.insert)

	def test_alv332_hr_keeps_every_right(self):
		for ptype in ("read", "write", "delete"):
			self.assertTrue(self.may(self.meena_mail, ptype, self.rohan), ptype)

	def test_alv332_a_colleague_gets_nothing(self):
		for ptype in ("read", "write", "delete"):
			self.assertFalse(self.may(self.priya_mail, ptype, self.rohan), ptype)
		self.assertEqual(self.listed(self.priya_mail), {self.priya})


class WholeLineSwitch(PunchCase):
	def test_alv328_off_a_manager_sees_direct_reports_only(self):
		"""AC-27, AC-32 with the switch off."""
		self.assertEqual(self.listed(self.arjun_mail), {self.arjun, self.kavita})
		self.assertFalse(self.may(self.arjun_mail, "read", self.rohan))

	def test_alv328_on_the_whole_active_line_and_still_read_only(self):
		"""AC-31, AC-32, SEC-8: Rohan joins; Sam (under a leaver) and Ina (inactive) do not."""
		frappe.db.set_single_value("HR Settings", WHOLE_LINE_SETTING, 1)
		self.assertEqual(self.listed(self.arjun_mail), {self.arjun, self.kavita, self.rohan})
		self.assertTrue(self.may(self.arjun_mail, "read", self.rohan))
		self.assertFalse(self.may(self.arjun_mail, "write", self.rohan))
		self.assertFalse(self.may(self.arjun_mail, "read", self.sam))
		self.assertFalse(self.may(self.kavita_mail, "read", self.ina))

	def test_alv328_the_list_and_the_single_record_agree(self):
		"""SEC-6: for every manager, switch off and on, record by record."""
		people = list(self.punches)
		for on in (0, 1):
			frappe.db.set_single_value("HR Settings", WHOLE_LINE_SETTING, on)
			for user in (self.arjun_mail, self.kavita_mail, self.rohan_mail, self.sam_mail):
				one_by_one = {e for e in people if self.may(user, "read", e)}
				self.assertEqual(self.listed(user), one_by_one, (on, user))

	def test_alv328_off_again_on_the_very_next_request(self):
		"""AC-34."""
		frappe.db.set_single_value("HR Settings", WHOLE_LINE_SETTING, 1)
		self.assertIn(self.rohan, self.listed(self.arjun_mail))
		frappe.db.set_single_value("HR Settings", WHOLE_LINE_SETTING, 0)
		self.assertNotIn(self.rohan, self.listed(self.arjun_mail))

	def test_alv328_an_unreadable_switch_counts_as_off(self):
		"""AC-33, PRIV-4."""
		with patch.object(frappe.db, "get_single_value", side_effect=Exception("missing")):
			self.assertFalse(whole_line_on())

	def test_alv328_the_field_is_there_and_off_on_a_fresh_site(self):
		"""AC-28."""
		self.assertTrue(frappe.db.exists("Custom Field",
		                                 {"dt": "HR Settings", "fieldname": WHOLE_LINE_SETTING}))
		self.assertFalse(whole_line_on())


class OnlyASystemManagerFlipsIt(PunchCase):
	def flip(self, user, door):
		frappe.set_user(user)
		try:
			door()
		finally:
			frappe.set_user("Administrator")

	def test_alv328_hr_manager_is_refused_on_every_door(self):
		"""AC-36 (SEC-9)."""
		def desk_save():
			doc = frappe.get_doc("HR Settings")
			doc.set(WHOLE_LINE_SETTING, 1)
			doc.save()

		def client_save():
			doc = frappe.get_doc("HR Settings").as_dict()
			doc[WHOLE_LINE_SETTING] = 1
			frappe.client.save(doc)

		doors = (desk_save, client_save,
		         lambda: frappe.client.set_value("HR Settings", "HR Settings", WHOLE_LINE_SETTING, 1))
		for door in doors:
			with self.assertRaises(frappe.PermissionError):
				self.flip(self.meena_mail, door)
			self.assertFalse(whole_line_on())

	def test_alv328_hr_manager_may_still_save_other_settings(self):
		def save():
			doc = frappe.get_doc("HR Settings")
			doc.save()
		self.flip(self.meena_mail, save)

	def test_alv328_a_system_manager_may_flip_it_and_it_is_recorded(self):
		"""AC-29, SEC-10."""
		before = frappe.db.count("Version", {"ref_doctype": "HR Settings"})
		doc = frappe.get_doc("HR Settings")
		doc.set(WHOLE_LINE_SETTING, 1)
		# Frappe writes no Version row while tests run unless asked; Desk saves do.
		doc.save(ignore_version=False)
		self.assertTrue(whole_line_on())
		self.assertEqual(frappe.db.count("Version", {"ref_doctype": "HR Settings"}), before + 1)
