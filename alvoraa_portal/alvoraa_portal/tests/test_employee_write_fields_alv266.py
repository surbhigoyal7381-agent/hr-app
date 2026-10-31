"""ALV-266: who may change which Employee record (Surbhi's rule, 31 Oct 2026).

1. Nobody but HR changes anything on another person's record - refused out loud.
2. A person changes only the SELF_EDITABLE fields on their own record; any other
   field is quietly put back, as ALV-215 does.
3. HR changes any record.
4. MANAGER_EDITABLE (empty) can grant a field to managers for their reports.

Every name carries alv266 so a merge that drops the feature fails CI.
"""

import json
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from alvoraa_portal import employee_field_rights as ef

COMPANY = "ALV266 Write Fields Co"
OLD = {"cell_number": "9000000000", "passport_number": "OLD-P", "current_address": "Old Street",
       "contract_end_date": "2030-01-01", "notice_number_of_days": 30, "image": None}


def _user(label, *roles):
	email = f"alv266.{label}@example.com"
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": "Alv266" + label,
		                "send_welcome_email": 0}).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles(*roles)
	return email


def _employee(label, user=None, reports_to=None):
	name = frappe.db.get_value("Employee", {"first_name": "Alv266" + label})
	doc = frappe.get_doc("Employee", name) if name else frappe.new_doc("Employee")
	doc.update({
		"first_name": "Alv266" + label, "company": COMPANY, "date_of_birth": "1990-01-01",
		"date_of_joining": "2015-01-01", "status": "Active", "user_id": user, "reports_to": reports_to,
		"gender": frappe.db.get_value("Gender", {}, "name"),
	})
	doc.save(ignore_permissions=True)
	return doc.name


def _own_row(user, employee):
	if not frappe.db.exists("User Permission", {"user": user, "allow": "Employee", "for_value": employee}):
		frappe.get_doc({"doctype": "User Permission", "user": user, "allow": "Employee",
		                "for_value": employee}).insert(ignore_permissions=True)


class EmployeeWriteRulesAlv266(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		if not frappe.db.exists("Company", COMPANY):
			if not frappe.db.exists("Warehouse Type", "Transit"):
				frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(ignore_permissions=True)
			frappe.get_doc({"doctype": "Company", "company_name": COMPANY, "abbr": "A266",
			                "default_currency": "INR", "country": "India"}).insert(ignore_permissions=True)
		if not frappe.db.exists("Gender", {}):
			frappe.get_doc({"doctype": "Gender", "gender": "Other"}).insert(ignore_permissions=True)
		cls.dept = frappe.db.get_value("Department", {"department_name": "Alv266 Dept", "company": COMPANY}) 			or frappe.get_doc({"doctype": "Department", "department_name": "Alv266 Dept",
			                   "company": COMPANY}).insert(ignore_permissions=True).name
		ef.apply()

		cls.manager = _user("manager", "Employee", "Employee Self Service")
		cls.plain_manager = _user("plainmgr", "Employee")  # no Employee Self Service
		cls.ess = _user("ess", "Employee", "Employee Self Service")
		cls.hr_mgr = _user("hrmgr", "Employee", "HR Manager")
		cls.manager_emp = _employee("Manager", cls.manager)
		cls.plain_manager_emp = _employee("PlainMgr", cls.plain_manager)
		cls.report = _employee("Report", reports_to=cls.manager_emp)
		cls.plain_report = _employee("PlainReport", reports_to=cls.plain_manager_emp)
		cls.ess_emp = _employee("Ess", cls.ess)
		cls.hr_mgr_emp = _employee("HrMgr", cls.hr_mgr)
		# ERPNext strips Employee Self Service from a user who had no Employee yet.
		for user in (cls.manager, cls.ess):
			frappe.get_doc("User", user).add_roles("Employee Self Service")
		# The own-record row ALV-249 gives every staff login; it covers the tree below.
		for user, emp in ((cls.manager, cls.manager_emp), (cls.plain_manager, cls.plain_manager_emp),
		                  (cls.ess, cls.ess_emp)):
			_own_row(user, emp)
		frappe.db.delete("User Permission", {"user": cls.hr_mgr})
		frappe.db.commit()

	def setUp(self):
		frappe.set_user("Administrator")
		for emp in (self.report, self.plain_report, self.ess_emp):
			frappe.db.set_value("Employee", emp, dict(OLD, reports_to=frappe.db.get_value(
				"Employee", emp, "reports_to"), status="Active"))

	def tearDown(self):
		frappe.set_user("Administrator")

	def _values(self, employee):
		return frappe.db.get_value("Employee", employee, list(OLD) + ["reports_to", "status", "department"],
		                           as_dict=True)

	# The four ways a write reaches an Employee ---------------------------------
	def _desk_save(self, employee, values):
		doc = frappe.get_doc("Employee", employee).as_dict()
		doc.update(values)
		from frappe.desk.form.save import savedocs
		savedocs(json.dumps(doc, default=str), "Save")

	def _rest_put(self, employee, values):
		from frappe.api.v1 import update_doc
		frappe.local.form_dict = frappe._dict(data=json.dumps(values))
		update_doc("Employee", employee)

	def _set_value(self, employee, values):
		frappe.client.set_value("Employee", employee, values)

	def _save(self, employee, values):
		doc = frappe.get_doc("Employee", employee)
		doc.update(values)
		doc.save()

	PATHS = ("_desk_save", "_rest_put", "_set_value", "_save")

	def _changes(self):
		return {
			"cell_number": "9000000266", "passport_number": "ALV266-P", "current_address": "266 New Street",
			"contract_end_date": "2031-01-01", "notice_number_of_days": 90,
			"reports_to": self.hr_mgr_emp, "status": "Inactive", "image": "/files/alv266.png",
			"department": self.dept,
		}

	def _assert_refused(self, user, employee):
		before = self._values(employee)
		for path in self.PATHS:
			for field, value in self._changes().items():
				with self.subTest(user=user, path=path, field=field):
					frappe.set_user(user)
					with self.assertRaises(frappe.PermissionError):
						getattr(self, path)(employee, {field: value})
					frappe.set_user("Administrator")
					self.assertEqual(self._values(employee), before)

	# Rule 1 -----------------------------------------------------------------
	def test_alv266_manager_with_ess_is_refused_on_a_report_on_every_path(self):
		frappe.set_user(self.manager)
		self.assertTrue(frappe.has_permission("Employee", "read", self.report),
		                "the test needs the manager to reach the report, as on ALV-249")
		frappe.set_user("Administrator")
		self._assert_refused(self.manager, self.report)

	def test_alv266_manager_without_ess_is_refused_on_a_report_on_every_path(self):
		self._assert_refused(self.plain_manager, self.plain_report)

	def test_alv266_refusal_says_what_to_do(self):
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.PermissionError) as caught:
			self._save(self.report, {"cell_number": "9000000267"})
		self.assertIn("Ask HR", str(caught.exception))

	def test_alv266_manager_opens_a_report_read_only_but_still_reads_it(self):
		frappe.set_user(self.manager)
		self.assertFalse(frappe.has_permission("Employee", "write", self.report))
		self.assertEqual(frappe.client.get("Employee", self.report).get("cell_number"), "9000000000")

	# Rule 2 -----------------------------------------------------------------
	def test_alv266_person_edits_own_mobile_and_passport(self):
		frappe.set_user(self.ess)
		self._save(self.ess_emp, {"cell_number": "9000000268", "passport_number": "ALV266-SELF"})
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Employee", self.ess_emp, ["cell_number", "passport_number"]),
		                 ("9000000268", "ALV266-SELF"))

	def test_alv266_person_cannot_change_own_contract_end_or_notice(self):
		frappe.set_user(self.ess)
		self._save(self.ess_emp, {"contract_end_date": "2031-01-01", "notice_number_of_days": 1})
		frappe.set_user("Administrator")
		values = frappe.db.get_value("Employee", self.ess_emp, ["contract_end_date", "notice_number_of_days"],
		                             as_dict=True)
		self.assertEqual((str(values.contract_end_date), values.notice_number_of_days), ("2030-01-01", 30))

	def test_alv266_a_manager_edits_own_personal_details_but_not_own_hr_fields(self):
		"""A manager is an employee too: their own record works like anyone's."""
		frappe.db.set_value("Employee", self.manager_emp, {"cell_number": "9000000000",
		                    "current_address": "Old Street", "notice_number_of_days": 30, "department": None})
		boss = frappe.db.get_value("Employee", self.manager_emp, "reports_to")
		frappe.set_user(self.manager)
		self._save(self.manager_emp, {"cell_number": "9000000271", "current_address": "271 Own Street",
		                              "department": self.dept, "notice_number_of_days": 1,
		                              "reports_to": self.hr_mgr_emp})
		frappe.set_user("Administrator")
		v = frappe.db.get_value("Employee", self.manager_emp, ["cell_number", "current_address", "department",
		                        "notice_number_of_days", "reports_to"], as_dict=True)
		self.assertEqual((v.cell_number, v.current_address), ("9000000271", "271 Own Street"))
		self.assertEqual((v.department, v.notice_number_of_days, v.reports_to), (None, 30, boss),
		                 "HR-only fields on your own record are put back")

	def test_alv266_without_ess_a_manager_cannot_edit_even_own_record_today(self):
		"""Not new: the plain Employee role has no write on Employee. Open decision for Surbhi."""
		frappe.set_user(self.plain_manager)
		with self.assertRaises(frappe.PermissionError):
			self._save(self.plain_manager_emp, {"cell_number": "9000000272"})

	def test_alv266_levels_follow_the_self_editable_list(self):
		meta = frappe.get_meta("Employee")
		for f in ef.SELF_EDITABLE:
			with self.subTest(field=f):
				self.assertTrue(meta.has_field(f), f"{f} is not on Employee - is the list stale?")
				self.assertEqual(meta.get_field(f).permlevel, 0)
		for f in ("contract_end_date", "notice_number_of_days", "company_email", "employee_number",
		          "create_user_permission", "reason_for_leaving", "internal_work_history"):
			with self.subTest(field=f):
				self.assertEqual(meta.get_field(f).permlevel, 2)

	# Rule 3 -----------------------------------------------------------------
	def test_alv266_hr_changes_anything_on_a_report(self):
		frappe.set_user(self.hr_mgr)
		self._save(self.report, {"cell_number": "9000000269", "contract_end_date": "2032-01-01",
		                         "notice_number_of_days": 60, "passport_number": "ALV266-HR"})
		frappe.set_user("Administrator")
		values = self._values(self.report)
		self.assertEqual((values.cell_number, str(values.contract_end_date), values.notice_number_of_days,
		                  values.passport_number), ("9000000269", "2032-01-01", 60, "ALV266-HR"))

	# Rule 4 -----------------------------------------------------------------
	def test_alv266_a_granted_field_and_only_that_field(self):
		with patch.object(ef, "MANAGER_EDITABLE", ("cell_number",)):
			frappe.set_user(self.manager)
			self.assertTrue(frappe.has_permission("Employee", "write", self.report))
			self._save(self.report, {"cell_number": "9000000270"})
			with self.assertRaises(frappe.PermissionError):
				self._save(self.report, {"passport_number": "ALV266-GRANT"})
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Employee", self.report, ["cell_number", "passport_number"]),
		                 ("9000000270", "OLD-P"))
