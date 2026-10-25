"""ALV-215 (slice 063 SEC-17): who may change which Employee field.

One test per rule. Every name carries alv215 so a merge that drops the feature
fails CI. Each guard was broken once on purpose and its test seen to fail
(05-implementation-notes-field-rights.md, "Guards broken on purpose").
"""

import frappe
from frappe.permissions import add_permission, reset_perms
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import employee_field_rights as ef
from alvoraa_portal import manager_scope as ms

COMPANY = "ALV215 Field Rights Co"
OTHER_COMPANY = "ALV215 Other Co"
PAY_FIELD = "alv215_pay_class"  # a tenant's own pay field, named by a rule set
PERM_FIELDS = ["role", "permlevel", "if_owner", "read", "write", "create", "delete", "submit",
               "cancel", "amend", "report", "export", "import", "share", "print", "email", "select"]


def _company(name, abbr):
	if not frappe.db.exists("Company", name):
		# A site that never ran the setup wizard has no "Transit" type, and Company needs it.
		if not frappe.db.exists("Warehouse Type", "Transit"):
			frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "Company", "company_name": name, "abbr": abbr,
		                "default_currency": "INR", "country": "India"}).insert(ignore_permissions=True)
	return name


def _user(label, *roles):
	email = f"alv215.{label}@example.com"
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": "Alv215" + label,
		                "send_welcome_email": 0}).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles(*roles)
	return email


def _employee(label, user=None):
	name = frappe.db.get_value("Employee", {"first_name": "Alv215" + label})
	if name:
		return name
	return frappe.get_doc({
		"doctype": "Employee", "first_name": "Alv215" + label, "company": COMPANY,
		"date_of_birth": "1990-01-01", "date_of_joining": "2015-01-01",
		"gender": frappe.db.get_value("Gender", {}, "name")
		or frappe.get_doc({"doctype": "Gender", "gender": "Other"}).insert(ignore_permissions=True).name,
		"status": "Active", "user_id": user,
	}).insert(ignore_permissions=True).name


def _level(fieldname):
	return frappe.get_meta("Employee").get_field(fieldname).permlevel


def _rows():
	return frappe.get_all("Custom DocPerm", filters={"parent": "Employee"}, fields=PERM_FIELDS,
	                      order_by="role, permlevel, if_owner")


class FieldRightsAlv215(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		_company(COMPANY, "A215")
		_company(OTHER_COMPANY, "A215O")
		if not frappe.db.exists("Employment Type", "Contract"):
			frappe.get_doc({"doctype": "Employment Type", "employee_type_name": "Contract"}).insert(ignore_permissions=True)
		for d in ("Alv215 Clerk", "Alv215 Lead"):
			if not frappe.db.exists("Designation", d):
				frappe.get_doc({"doctype": "Designation", "designation_name": d}).insert(ignore_permissions=True)
		if not frappe.db.exists("Custom Field", {"dt": "Employee", "fieldname": PAY_FIELD}):
			frappe.get_doc({"doctype": "Custom Field", "dt": "Employee", "fieldname": PAY_FIELD,
			                "label": "Alv215 Pay Class", "fieldtype": "Data",
			                "insert_after": "employment_type"}).insert(ignore_permissions=True)
		ef.apply()

		cls.ess = _user("ess", "Employee", "Employee Self Service")
		cls.hr_user = _user("hruser", "Employee", "HR User")
		cls.hr_mgr = _user("hrmgr", "Employee", "HR Manager")
		cls.ess_emp = _employee("Ess", cls.ess)
		cls.hr_user_emp = _employee("HrUser", cls.hr_user)
		cls.hr_mgr_emp = _employee("HrMgr", cls.hr_mgr)
		cls.colleague = _employee("Colleague")
		# ERPNext ties every login to its own Employee and Company by User Permission.
		# HR people work across records, so a tenant switches that off for them.
		frappe.db.delete("User Permission", {"user": ["in", [cls.hr_user, cls.hr_mgr]]})
		cls.old_boss = _employee("OldBoss", _user("oldboss", "Employee"))
		cls.new_boss = _employee("NewBoss", _user("newboss", "Employee"))
		if not frappe.db.exists("User Permission", {"user": cls.ess, "allow": "Employee",
		                                            "for_value": cls.ess_emp}):
			frappe.get_doc({"doctype": "User Permission", "user": cls.ess, "allow": "Employee",
			                "for_value": cls.ess_emp}).insert(ignore_permissions=True)
		e = frappe.get_doc("Employee", cls.ess_emp)
		e.reports_to = cls.old_boss
		e.save(ignore_permissions=True)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")

	def _save_as(self, user, employee, **values):
		frappe.set_user(user)
		doc = frappe.get_doc("Employee", employee)
		doc.update(values)
		doc.save(ignore_version=False)  # Frappe skips Version rows in tests unless told
		frappe.set_user("Administrator")
		return frappe.get_doc("Employee", employee)

	# R1 ------------------------------------------------------------------
	def test_alv215_employee_cannot_change_own_job_pay_or_approver_fields(self):
		before = frappe.get_doc("Employee", self.ess_emp)
		after = self._save_as(self.ess, self.ess_emp, designation="Alv215 Lead",
		                      reports_to=self.new_boss, leave_approver=self.hr_user,
		                      employment_type="Contract",
		                      attendance_device_id="ALV215-X", **{PAY_FIELD: "A"})
		# Not company: the Company User Permission refuses that save outright.
		for f in ("designation", "reports_to", "leave_approver", "employment_type",
		          "attendance_device_id", PAY_FIELD):
			self.assertEqual(after.get(f), before.get(f), f"{f} must not change")
		old_boss_user = frappe.db.get_value("Employee", self.old_boss, "user_id")
		self.assertTrue(frappe.get_all("User Permission", filters={"user": old_boss_user,
		                "for_value": self.ess_emp}), "the real manager keeps access")

	def test_alv215_employee_still_changes_own_phone(self):
		after = self._save_as(self.ess, self.ess_emp, cell_number="9000000215")
		self.assertEqual(after.cell_number, "9000000215")

	def test_alv215_hr_user_changes_a_colleague_and_history_says_so(self):
		new = "Alv215 Lead" if frappe.db.get_value("Employee", self.colleague, "designation") != "Alv215 Lead" else "Alv215 Clerk"
		after = self._save_as(self.hr_user, self.colleague, designation=new)
		self.assertEqual(after.designation, new)
		v = frappe.get_all("Version", filters={"ref_doctype": "Employee", "docname": self.colleague},
		                   fields=["owner", "data"], order_by="creation desc", limit=1)[0]
		self.assertEqual(v.owner, self.hr_user)
		self.assertIn("designation", v.data)

	# R2 ------------------------------------------------------------------
	def test_alv215_only_hr_manager_changes_or_sees_bank_details(self):
		frappe.db.set_value("Employee", self.colleague, "bank_ac_no", "111")
		after = self._save_as(self.hr_user, self.colleague, bank_ac_no="222")
		self.assertEqual(after.bank_ac_no, "111", "HR User's bank change is put back")
		after = self._save_as(self.hr_mgr, self.colleague, bank_ac_no="333")
		self.assertEqual(after.bank_ac_no, "333")
		frappe.set_user(self.hr_user)
		self.assertFalse(frappe.client.get("Employee", self.colleague).get("bank_ac_no"))

	# R4 ------------------------------------------------------------------
	def test_alv215_hr_cannot_change_own_locked_fields(self):
		for user, emp, values in (
			(self.hr_user, self.hr_user_emp, {"company": OTHER_COMPANY}),
			(self.hr_user, self.hr_user_emp, {"attendance_device_id": "ALV215-OWN"}),
			(self.hr_mgr, self.hr_mgr_emp, {"bank_ac_no": "999"}),
		):
			with self.assertRaises(frappe.PermissionError):
				self._save_as(user, emp, **values)
		after = self._save_as(self.hr_user, self.hr_user_emp, cell_number="9000000216")
		self.assertEqual(after.cell_number, "9000000216")

	def test_alv215_hr_cannot_promote_themselves(self):
		frappe.set_user(self.hr_mgr)
		p = frappe.get_doc({"doctype": "Employee Promotion", "employee": self.hr_mgr_emp,
		                    "promotion_date": add_days(nowdate(), -1),
		                    "promotion_details": [{"property": "Designation", "fieldname": "designation",
		                                           "current": "", "new": "Alv215 Lead"}]})
		p.flags.ignore_permissions = True  # the plan may switch the doctype off; the Employee save is the point
		p.insert()
		with self.assertRaises(frappe.PermissionError):
			p.submit()

	def test_alv215_another_hr_person_changes_it(self):
		after = self._save_as(self.hr_mgr, self.hr_user_emp, designation="Alv215 Lead")
		self.assertEqual(after.designation, "Alv215 Lead")

	# Migration -----------------------------------------------------------
	def test_alv215_apply_sets_levels_and_rows_and_runs_twice_for_nothing(self):
		for f in ef.LEVEL_2:
			if frappe.get_meta("Employee").has_field(f):
				self.assertEqual(_level(f), 2, f)
		for f in ef.LEVEL_1:
			if frappe.get_meta("Employee").has_field(f):
				self.assertEqual(_level(f), 1, f)
		self._assert_rows()
		before = (_rows(), frappe.db.count("Property Setter", {"doc_type": "Employee"}))
		ef.apply()
		self.assertEqual((_rows(), frappe.db.count("Property Setter", {"doc_type": "Employee"})), before)

	def _assert_rows(self):
		rows = _rows()
		at = {(r.role, r.permlevel): r for r in rows if not r.if_owner}
		for r in [r for r in rows if r.permlevel == 0 and not r.if_owner and (r.read or r.write)]:
			self.assertTrue(at.get((r.role, 2)) and at[(r.role, 2)].read, f"{r.role} reads level 2")
			if r.write and r.role in ef.LEVEL_2_WRITERS:
				self.assertTrue(at[(r.role, 2)].write, f"{r.role} writes level 2")
			if r.role not in ef.LEVEL_2_WRITERS:
				self.assertFalse(at[(r.role, 2)].write, f"{r.role} must not write level 2")
		self.assertEqual({r.role for r in rows if r.permlevel == 1}, {"HR Manager"})
		self.assertTrue(at[("HR Manager", 1)].write)

	def test_alv215_apply_never_lowers_a_field_and_drops_other_level_1_rows(self):
		frappe.db.set_value("Property Setter", {"doc_type": "Employee", "field_name": "middle_name",
		                                        "property": "permlevel"}, "value", "1")
		if not frappe.db.exists("Role", "Payroll User"):
			frappe.get_doc({"doctype": "Role", "role_name": "Payroll User"}).insert(ignore_permissions=True)
		add_permission("Employee", "Payroll User", 0)
		add_permission("Employee", "Payroll User", 1)
		frappe.clear_cache(doctype="Employee")
		try:
			ef.apply()
			self.assertEqual(_level("middle_name"), 1, "a field already above 0 is never lowered")
			self.assertFalse(frappe.db.exists("Custom DocPerm", {"parent": "Employee", "role": "Payroll User",
			                                                     "permlevel": 1}), "D2: HR Manager only")
		finally:
			frappe.db.set_value("Property Setter", {"doc_type": "Employee", "field_name": "middle_name",
			                                        "property": "permlevel"}, "value", "2")
			frappe.db.delete("Custom DocPerm", {"parent": "Employee", "role": "Payroll User"})
			frappe.clear_cache(doctype="Employee")

	def test_alv215_apply_on_a_site_with_no_custom_rows_keeps_every_role(self):
		snapshot = _rows()
		reset_perms("Employee")
		frappe.clear_cache(doctype="Employee")
		try:
			standard = {(r.role, r.permlevel) for r in frappe.get_all("DocPerm", filters={"parent": "Employee"},
			                                                          fields=["role", "permlevel"])}
			ef.apply()
			got = {(r.role, r.permlevel) for r in _rows()}
			self.assertTrue(standard <= got, "no standard row lost")
			self._assert_rows()
		finally:
			reset_perms("Employee")
			for r in snapshot:
				frappe.get_doc(dict(r, doctype="Custom DocPerm", parent="Employee", parenttype="DocType",
				                    parentfield="permissions")).insert(ignore_permissions=True)
			frappe.clear_cache(doctype="Employee")

	# Rule set ------------------------------------------------------------
	def test_alv215_a_field_a_rule_set_names_is_locked_on_save(self):
		frappe.db.delete("Property Setter", {"doc_type": "Employee", "field_name": PAY_FIELD})
		frappe.clear_cache(doctype="Employee")
		self.assertEqual(_level(PAY_FIELD), 0)
		for name in frappe.get_all("Alvoraa Payroll Rule Set", filters={"company": COMPANY}, pluck="name"):
			frappe.delete_doc("Alvoraa Payroll Rule Set", name, force=True, ignore_permissions=True)
		rs = frappe.get_doc({
			"doctype": "Alvoraa Payroll Rule Set", "company": COMPANY, "enabled": 0,
			"leave_class_field": PAY_FIELD, "category_field": "employment_type",
			"slabs": [{"percent_from": 0, "percent_to": 100, "quarters_off": 0, "raises_red": 0}],
		})
		frappe.set_user(self.hr_mgr)  # an HR Manager's save must be able to lock it too
		rs.insert(ignore_permissions=True)
		self.assertEqual(_level(PAY_FIELD), 2)
		frappe.set_user("Administrator")
		frappe.delete_doc("Alvoraa Payroll Rule Set", rs.name, force=True, ignore_permissions=True)

	# Step B --------------------------------------------------------------
	def test_alv215_field_picker_does_not_leak_bank_number(self):
		hooks = frappe.get_hooks("override_whitelisted_methods")
		self.assertEqual(hooks["hrms.hr.utils.get_employee_field_property"][-1],
		                 "alvoraa_portal.employee_field_rights.get_employee_field_property")
		frappe.db.set_value("Employee", self.colleague, "bank_ac_no", "444")
		frappe.set_user(self.hr_user)
		with self.assertRaises(frappe.PermissionError):
			ef.get_employee_field_property(self.colleague, "bank_ac_no")
		self.assertIn("value", ef.get_employee_field_property(self.colleague, "designation"))
		frappe.set_user(self.hr_mgr)
		self.assertEqual(ef.get_employee_field_property(self.colleague, "bank_ac_no")["value"], "444")

	# Import --------------------------------------------------------------
	def test_alv215_import_with_a_locked_column_is_refused_loudly(self):
		self.assertIn("alvoraa_portal.employee_field_rights.refuse_import_of_locked_columns",
		              frappe.get_hooks("doc_events")["Data Import"]["validate"])
		f = frappe.get_doc({"doctype": "File", "file_name": "alv215.csv", "is_private": 1,
		                    "content": "ID,%s\n%s,555\n" % (
		                        frappe.get_meta("Employee").get_field("bank_ac_no").label, self.colleague)}).insert(ignore_permissions=True)
		di = frappe.get_doc({"doctype": "Data Import", "reference_doctype": "Employee",
		                     "import_type": "Update Existing Records", "import_file": f.file_url})
		frappe.set_user(self.hr_user)
		with self.assertRaises(frappe.PermissionError):
			ef.refuse_import_of_locked_columns(di)
		frappe.set_user(self.hr_mgr)
		ef.refuse_import_of_locked_columns(di)  # HR Manager may import bank details
