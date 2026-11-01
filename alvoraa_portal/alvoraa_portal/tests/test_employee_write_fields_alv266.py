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

	def test_alv266_a_refused_bulk_edit_logs_no_value_of_the_report(self):
		from frappe.desk.doctype.bulk_update.bulk_update import submit_cancel_or_update_docs
		frappe.db.set_value("Employee", self.report, "cell_number", "9111111266")
		since = frappe.utils.now_datetime()
		frappe.set_user(self.manager)
		failed = submit_cancel_or_update_docs("Employee", [self.report], "update", {"cell_number": "9777777266"})
		frappe.set_user("Administrator")
		self.assertEqual(failed, [self.report])
		logs = frappe.get_all("Error Log", filters={"creation": [">=", since]}, pluck="error")
		self.assertTrue(logs, "the bulk edit should have logged its failure")
		self.assertFalse([e for e in logs if "9111111266" in (e or "")], "the report's real mobile is in a log")

	def test_alv266_refusal_says_what_to_do(self):
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.PermissionError) as caught:
			self._save(self.report, {"cell_number": "9000000267"})
		self.assertIn("Ask HR", str(caught.exception))

	def test_alv266_manager_may_not_write_a_report_but_still_reads_it(self):
		# The Desk form still opens editable (Frappe asks without a permission type);
		# a save is refused with the Ask HR message - see the tests above.
		frappe.set_user(self.manager)
		self.assertFalse(frappe.has_permission("Employee", "write", self.report))
		self.assertEqual(frappe.client.get("Employee", self.report).get("cell_number"), "9000000000")

	# Rule 2 -----------------------------------------------------------------
	def test_alv266_person_edits_own_mobile_and_address_but_not_passport(self):
		frappe.set_user(self.ess)
		self._save(self.ess_emp, {"cell_number": "9000000268", "current_address": "268 Own Street",
		                          "passport_number": "ALV266-SELF"})
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Employee", self.ess_emp,
		                                     ["cell_number", "current_address", "passport_number"]),
		                 ("9000000268", "268 Own Street", "OLD-P"), "D6: the passport is HR's to change")

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
		for f in ef.LEVEL_3:
			with self.subTest(field=f):
				self.assertNotIn(f, ef.SELF_EDITABLE)
				if meta.has_field(f):  # health insurance exists only where Frappe HR made it
					self.assertEqual(meta.get_field(f).permlevel, 3)

	# D6: passport, health and family details are HR's only ---------------------
	D6_SAMPLE = ("passport_number", "blood_group", "health_details", "family_background")

	def _d6_values(self, employee):
		frappe.db.set_value("Employee", employee, {"passport_number": "D6-P", "blood_group": "O+",
		                                           "health_details": "D6 health", "family_background": "D6 family"})

	def test_alv266_d6_manager_and_staff_cannot_read_passport_or_health(self):
		for emp in (self.report, self.ess_emp):
			self._d6_values(emp)
		for user, emp in ((self.manager, self.report), (self.ess, self.ess_emp), (self.manager, self.manager_emp)):
			with self.subTest(user=user, employee=emp):
				frappe.set_user(user)
				try:
					got = frappe.client.get("Employee", emp)
					listed = frappe.get_list("Employee", filters={"name": emp}, fields=["name", *self.D6_SAMPLE])
				finally:
					frappe.set_user("Administrator")
				for f in self.D6_SAMPLE:
					self.assertFalse(got.get(f), f"{f} read through the form")
					self.assertFalse(listed and listed[0].get(f), f"{f} read through a list")

	def test_alv266_d6_hr_reads_and_writes_passport_and_health(self):
		self._d6_values(self.report)
		frappe.set_user(self.hr_mgr)
		try:
			self.assertEqual(frappe.client.get("Employee", self.report).get("blood_group"), "O+")
			self._save(self.report, {"passport_number": "D6-HR", "health_details": "D6 by HR"})
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Employee", self.report, ["passport_number", "health_details"]),
		                 ("D6-HR", "D6 by HR"))

	def test_alv266_hr_refused_on_own_passport_with_an_accurate_message(self):
		frappe.set_user(self.hr_mgr)
		try:
			with self.assertRaises(frappe.PermissionError) as caught:
				self._save(self.hr_mgr_emp, {"passport_number": "ALV266-OWN-HR"})
		finally:
			frappe.set_user("Administrator")
		text = str(caught.exception)
		self.assertIn(frappe.get_meta("Employee").get_label("passport_number"), text)
		self.assertNotIn("job, pay or bank", text)
		self.assertNotIn("ALV266-OWN-HR", text, "a refusal names fields, never values")

	def test_alv266_d6_staff_and_managers_cannot_export_employees(self):
		self.assertFalse(frappe.db.get_value("Custom DocPerm", {"parent": "Employee", "role": "Employee Self Service",
		                                                        "permlevel": 0}, "export"))
		from frappe.desk.reportview import export_query

		def export(user):
			frappe.set_user(user)
			frappe.local.form_dict = frappe._dict(doctype="Employee", file_format_type="CSV",
			                                      fields=json.dumps(["`tabEmployee`.`name`", "`tabEmployee`.`cell_number`"]))
			try:
				return export_query()
			finally:
				frappe.set_user("Administrator")

		for user in (self.ess, self.manager):
			with self.subTest(user=user), self.assertRaises(frappe.PermissionError):
				export(user)
		export(self.hr_mgr)  # HR unchanged

	# Rule 3 -----------------------------------------------------------------
	def test_alv266_hr_changes_anything_on_a_report(self):
		frappe.set_user(self.hr_mgr)
		self._save(self.report, {"cell_number": "9000000269", "contract_end_date": "2032-01-01",
		                         "notice_number_of_days": 60, "passport_number": "ALV266-HR"})
		frappe.set_user("Administrator")
		values = self._values(self.report)
		self.assertEqual((values.cell_number, str(values.contract_end_date), values.notice_number_of_days,
		                  values.passport_number), ("9000000269", "2032-01-01", 60, "ALV266-HR"))

	def test_alv266_hr_user_and_system_manager_change_a_report(self):
		user = _user("hruser", "Employee", "HR User")
		frappe.db.delete("User Permission", {"user": user})
		frappe.set_user(user)
		self._save(self.report, {"cell_number": "9000000301", "contract_end_date": "2033-01-01"})
		frappe.set_user("Administrator")
		v = frappe.db.get_value("Employee", self.report, ["cell_number", "contract_end_date"])
		self.assertEqual((v[0], str(v[1])), ("9000000301", "2033-01-01"))
		# System Manager: our rule must let it through. (Whether the site's role rows
		# give System Manager Employee write at all is the tenant's own setting.)
		doc = frappe.get_doc("Employee", self.report)
		doc.cell_number = "9000000302"
		self.assertIs(ef.employee_has_permission(doc, "write", _user("sysmgr", "System Manager")), True)

	# Own saves that code touches (review M1) ------------------------------------
	def test_alv266_own_save_with_an_expired_document_still_saves(self):
		dtype = "Alv266 Licence"
		if not frappe.db.exists("Employee Document Type", dtype):
			frappe.get_doc({"doctype": "Employee Document Type", "document_type_name": dtype,
			                "category": "Identity", "collect_from": "Employee"}).insert(ignore_permissions=True)
		row = frappe.get_doc({"doctype": "Employee Document", "parent": self.ess_emp, "parenttype": "Employee",
		                      "parentfield": "employee_documents", "document_type": dtype,
		                      "status": "Received", "expiry_date": "2020-01-01"})
		row.db_insert()
		try:
			frappe.set_user(self.ess)
			self._save(self.ess_emp, {"cell_number": "9000000273"})
			frappe.set_user("Administrator")
			self.assertEqual(frappe.db.get_value("Employee", self.ess_emp, "cell_number"), "9000000273")
		finally:
			frappe.set_user("Administrator")
			frappe.db.delete("Employee Document", {"name": row.name})

	def test_alv266_own_save_with_a_work_history_row_still_saves(self):
		# A level-2 table on your own record must not trip the own-record rule.
		row = frappe.get_doc({"doctype": "Employee Internal Work History", "parent": self.ess_emp,
		                      "parenttype": "Employee", "parentfield": "internal_work_history",
		                      "from_date": "2016-01-01"})
		row.db_insert()
		try:
			frappe.set_user(self.ess)
			self._save(self.ess_emp, {"cell_number": "9000000275"})
			frappe.set_user("Administrator")
			self.assertEqual(frappe.db.get_value("Employee", self.ess_emp, "cell_number"), "9000000275")
		finally:
			frappe.set_user("Administrator")
			frappe.db.delete("Employee Internal Work History", {"name": row.name})

	def test_alv266_own_save_when_the_full_name_is_rebuilt_still_saves(self):
		frappe.db.set_value("Employee", self.ess_emp, "employee_name", "Alv266 Name From A Sheet")
		frappe.set_user(self.ess)
		self._save(self.ess_emp, {"cell_number": "9000000274"})
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Employee", self.ess_emp, "cell_number"), "9000000274")

	def test_alv266_a_new_custom_field_is_hr_only(self):
		self.assertIn("alvoraa_portal.employee_field_rights.lock_new_custom_field",
		              frappe.get_hooks("doc_events")["Custom Field"]["after_insert"])
		frappe.get_doc({"doctype": "Custom Field", "dt": "Employee", "fieldname": "alv266_tshirt",
		                "label": "Alv266 T-shirt", "fieldtype": "Data",
		                "insert_after": "blood_group"}).insert(ignore_permissions=True)
		try:
			frappe.clear_cache(doctype="Employee")
			self.assertEqual(frappe.get_meta("Employee").get_field("alv266_tshirt").permlevel, 2)
		finally:
			frappe.db.delete("Property Setter", {"doc_type": "Employee", "field_name": "alv266_tshirt"})
			frappe.delete_doc("Custom Field", "Employee-alv266_tshirt", force=True, ignore_permissions=True)
			frappe.db.commit()  # the column's DDL is committed; keep the site whole
			frappe.clear_cache(doctype="Employee")

	# Rename (06-security, blocker 2) --------------------------------------------
	def test_alv266_only_hr_renames_an_employee(self):
		self.assertEqual(frappe.get_hooks("doc_events")["Employee"]["before_rename"],
		                 ["alvoraa_portal.employee_field_rights.refuse_rename_unless_hr"])
		for user, old, new, merge in ((self.ess, self.ess_emp, "ALV266-OWN-ID", False),
		                              (self.manager, self.report, "ALV266-REPORT-ID", False),
		                              (self.ess, self.ess_emp, self.manager_emp, True)):
			with self.subTest(user=user, merge=merge):
				frappe.set_user(user)
				with self.assertRaises(frappe.PermissionError):
					frappe.rename_doc("Employee", old, new, merge=merge)
				frappe.set_user("Administrator")
				self.assertTrue(frappe.db.exists("Employee", old))
		spare = _employee("Spare")
		frappe.set_user(self.hr_mgr)
		try:
			frappe.rename_doc("Employee", spare, "ALV266-HR-RENAMED")
		finally:
			frappe.set_user("Administrator")
		self.assertTrue(frappe.db.exists("Employee", "ALV266-HR-RENAMED"))
		frappe.delete_doc("Employee", "ALV266-HR-RENAMED", force=True, ignore_permissions=True)

	# Share and assign (06-security, major 3) -------------------------------------
	def test_alv266_staff_cannot_share_or_assign_a_report_open(self):
		self.assertFalse(frappe.db.get_value("Custom DocPerm", {"parent": "Employee", "role": "Employee Self Service",
		                                                        "permlevel": 0}, "share"))
		from frappe.desk.form.assign_to import add as assign
		frappe.db.savepoint("alv266_share")
		frappe.set_user(self.manager)
		try:
			with self.assertRaises(frappe.PermissionError):
				frappe.share.add("Employee", self.report, self.ess, read=1)
			with self.assertRaises(frappe.PermissionError):
				assign({"doctype": "Employee", "name": self.report, "assign_to": [self.ess]})
		finally:
			frappe.set_user("Administrator")
			frappe.db.rollback(save_point="alv266_share")
		self.assertFalse(frappe.has_permission("Employee", "read", self.report, user=self.ess))

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
