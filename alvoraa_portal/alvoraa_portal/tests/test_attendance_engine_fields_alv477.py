"""ALV-477: a person cannot rewrite the pay engine's figures on a submitted day record.

The fourteen engine fields on Attendance (eleven verdict fields, three release fields) were
`read_only` and `allow_on_submit`. Frappe does not enforce `read_only` on the server, and
`allow_on_submit` is what lets a submitted row be saved with a new value, so HR logins with API
access could change a day's quarters off and red marks. They are no longer `allow_on_submit`, so
Frappe itself refuses the change on every route, and the engine - which writes with
`frappe.db.set_value`, never through the document - is unaffected.

Each refusal test has a control beside it: the engine still writes those same fields, and a
person still confirms the out time (the two fields that are theirs).
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from alvoraa_portal import held_day, payroll_fields
from alvoraa_portal import payroll_rules_apply as pra
from alvoraa_portal.tests import test_payroll_reprocess as base
from alvoraa_portal.tests.test_payroll_reprocess import setUpModule  # noqa: F401  (company, shift, rule set)

ENGINE_FIELDS = tuple(pra.VERDICT_FIELDS) + ("alvoraa_release_how", "alvoraa_release_by", "alvoraa_release_on")
PERSONS_FIELDS = ("alvoraa_held_confirmed", "alvoraa_confirmed_out_time")

#: A value different from what the engine leaves, for each field's type.
FORGED = {"Check": 1, "Int": 9, "Percent": 55.5, "Small Text": "forged", "Data": "forged",
          "Datetime": "2020-01-01 10:00:00", "Select": "HR decision"}


class TestEngineFieldsAreTheEnginesAlone(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.date = getdate(add_days(nowdate(), -3))
		emp = frappe.get_doc({
			"doctype": "Employee", "first_name": "Alv477", "last_name": "Person", "company": base.COMPANY,
			"date_of_joining": add_days(nowdate(), -200), "date_of_birth": "1990-01-01",
			"gender": base._gender(), "status": "Active", "default_shift": base.SHIFT})
		emp.flags.ignore_permissions = True
		emp.insert()
		att = frappe.get_doc({"doctype": "Attendance", "employee": emp.name, "company": base.COMPANY,
		                      "attendance_date": self.date, "status": "Present", "shift": base.SHIFT})
		att.flags.ignore_permissions = True
		att.insert()
		att.submit()
		self.name = att.name

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		frappe.clear_cache(doctype="Attendance")

	def _forge(self, field, before):
		fieldtype = frappe.get_meta("Attendance").get_field(field).fieldtype
		if fieldtype == "Check":
			return 1 - int(before or 0)  # the engine may have left it 1 already
		return FORGED[fieldtype]

	def test_there_are_fourteen_engine_fields(self):
		# The count the ticket's scope was settled on. A new engine field must be added to the
		# list on purpose, not slip in as editable.
		self.assertEqual(len(ENGINE_FIELDS), 14)
		self.assertEqual(len(set(ENGINE_FIELDS)), 14)

	def test_a_save_that_changes_an_engine_field_is_refused_for_every_one(self):
		for field in ENGINE_FIELDS:
			with self.subTest(field=field):
				before = frappe.db.get_value("Attendance", self.name, field)
				doc = frappe.get_doc("Attendance", self.name)
				doc.set(field, self._forge(field, before))
				with self.assertRaises(frappe.UpdateAfterSubmitError):
					doc.save()
				self.assertEqual(frappe.db.get_value("Attendance", self.name, field), before)

	def test_the_api_set_value_is_refused_for_a_system_manager(self):
		# The ticket's own route family: an API login, not the Desk form.
		email = "alv477.sysmgr@example.com"
		user = frappe.get_doc({"doctype": "User", "email": email, "first_name": "Alv477", "send_welcome_email": 0})
		user.insert(ignore_permissions=True)
		user.add_roles("System Manager")
		frappe.set_user(email)
		with self.assertRaises(frappe.UpdateAfterSubmitError):
			frappe.client.set_value("Attendance", self.name, {"alvoraa_slab_quarters": 5, "alvoraa_reds": 9})
		frappe.set_user("Administrator")
		self.assertNotEqual(frappe.db.get_value("Attendance", self.name, "alvoraa_reds"), 9)

	def test_control_the_engine_still_writes_the_verdict_on_a_submitted_day(self):
		# on_submit already judged it (a rule set is on for this company).
		self.assertIsNotNone(frappe.db.get_value("Attendance", self.name, "alvoraa_evaluated_on"))
		frappe.db.set_value("Attendance", self.name, "alvoraa_evaluated_on", None, update_modified=False)
		pra.evaluate_attendance(self.name)
		self.assertIsNotNone(frappe.db.get_value("Attendance", self.name, "alvoraa_evaluated_on"))

	def test_control_the_engine_still_writes_the_release_fields(self):
		held_day._write_release(self.name, None, ("Present", 8, 0, 0, None, None), "HR decision", "x@example.com")
		got = frappe.db.get_value("Attendance", self.name,
		                          ["alvoraa_release_how", "alvoraa_release_by", "alvoraa_release_on"], as_dict=True)
		self.assertEqual((got.alvoraa_release_how, got.alvoraa_release_by), ("HR decision", "x@example.com"))
		self.assertIsNotNone(got.alvoraa_release_on)

	def test_control_a_person_still_confirms_the_out_time(self):
		doc = frappe.get_doc("Attendance", self.name)
		doc.alvoraa_held_confirmed = 1
		doc.alvoraa_confirmed_out_time = "18:00:00"
		doc.save()
		got = frappe.db.get_value("Attendance", self.name, list(PERSONS_FIELDS), as_dict=True)
		self.assertEqual(got.alvoraa_held_confirmed, 1)

	def test_a_migrate_closes_it_on_a_site_that_already_has_the_old_definition(self):
		frappe.db.set_value("Custom Field", {"dt": "Attendance", "fieldname": ("in", ENGINE_FIELDS)},
		                    "allow_on_submit", 1)
		frappe.clear_cache(doctype="Attendance")
		payroll_fields.after_migrate()
		held_day.after_migrate()
		frappe.clear_cache(doctype="Attendance")
		meta = frappe.get_meta("Attendance")
		open_ones = [f for f in ENGINE_FIELDS if meta.get_field(f).allow_on_submit]
		self.assertEqual(open_ones, [])
		# and the two that are a person's are left open
		self.assertTrue(all(meta.get_field(f).allow_on_submit for f in PERSONS_FIELDS))
