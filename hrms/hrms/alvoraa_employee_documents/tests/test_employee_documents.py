"""The employee document checklist: filled on creation, moved along by
attachments and verifiers, expired by the daily job."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from hrms.alvoraa_employee_documents.employee_documents import (  # noqa: F401
	applicable_types,
	attach_document,
	employees_missing_mandatory,
	expire_documents,
	summary_text,
)
from hrms.alvoraa_employee_documents.setup import make_custom_fields

PREFIX = "Doc Test"


def _company():
	return frappe.get_all("Company", pluck="name", limit=1)[0]


def _type(name, **values):
	full = f"{PREFIX} {name}"
	if frappe.db.exists("Employee Document Type", full):
		return frappe.get_doc("Employee Document Type", full)
	doc = frappe.get_doc({"doctype": "Employee Document Type", "document_type_name": full, "category": "Identity",
	                      "collect_from": "Employee", **values})
	doc.insert(ignore_permissions=True)
	return doc


class TestEmployeeDocuments(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_custom_fields()
		frappe.clear_cache()
		frappe.conf.features = list(frappe.conf.get("features") or []) + ["employee_documents"]
		cls.company = _company()
		if not frappe.db.exists("Employee Grade", "Doc Test Vault Grade"):
			frappe.get_doc({"doctype": "Employee Grade", "__newname": "Doc Test Vault Grade"}).insert(ignore_permissions=True)
		cls.id_card = _type("Identity Card", mandatory_for_joining=1, verifier_roles=[{"role": "HR Manager"}])
		cls.address = _type("Address Proof", category="Address", mandatory_for_joining=1)
		cls.slips = _type("Salary Slips", category="Employment", mandatory_for_joining=0)
		cls.vault = _type("Vault Authorisation", category="Company Issued", collect_from="Manager",
		                  applies_to_grades=[{"employee_grade": "Doc Test Vault Grade"}])
		cls.licence = _type("Licence", category="Statutory", has_expiry=1, reminder_days_before_expiry=30,
		                    collect_from="HR")
		if not frappe.db.exists("Designation", "Doc Test Guard"):
			frappe.get_doc({"doctype": "Designation", "designation_name": "Doc Test Guard"}).insert(ignore_permissions=True)
		cls.guard_licence = _type("Guard Licence", category="Statutory", collect_from="HR",
		                          applies_to_designations=[{"designation": "Doc Test Guard"}])
		if not frappe.db.exists("User", "doc.tester@example.com"):
			user = frappe.get_doc({"doctype": "User", "email": "doc.tester@example.com", "first_name": "Doc Tester",
			                       "send_welcome_email": 0, "roles": [{"role": "Employee"}]})
			user.insert(ignore_permissions=True)

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		for name in frappe.get_all("Employee", {"first_name": "Doc", "last_name": "Tester"}, pluck="name"):
			frappe.delete_doc("Employee", name, ignore_permissions=True, force=True)

	def _employee(self, grade=None):
		emp = frappe.get_doc({"doctype": "Employee", "first_name": "Doc", "last_name": "Tester", "gender": "Female",
		                      "date_of_birth": "1995-01-01", "date_of_joining": "2026-01-01", "company": self.company,
		                      "status": "Active", "grade": grade})
		emp.flags.ignore_permissions = True
		emp.insert()
		return frappe.get_doc("Employee", emp.name)

	def _row(self, emp, doc_type):
		return next(r for r in emp.employee_documents if r.document_type == doc_type.name)

	def test_applicable_types_follow_the_grade(self):
		names = {t.name for t in applicable_types(None)}
		self.assertIn(self.id_card.name, names)
		self.assertNotIn(self.vault.name, names)
		self.assertIn(self.vault.name, {t.name for t in applicable_types("Doc Test Vault Grade")})
		self.assertNotIn(self.guard_licence.name, names)
		self.assertIn(self.guard_licence.name, {t.name for t in applicable_types(None, "Doc Test Guard")})

	def test_new_employee_gets_the_checklist(self):
		emp = self._employee()
		types = {r.document_type for r in emp.employee_documents}
		self.assertIn(self.id_card.name, types)
		self.assertIn(self.slips.name, types)
		self.assertNotIn(self.vault.name, types)
		self.assertTrue(all(r.status == "Pending" for r in emp.employee_documents))
		self.assertIn("pending", emp.documents_summary)

	def test_attachment_marks_received(self):
		emp = self._employee()
		self._row(emp, self.address).attachment = "/private/files/proof.pdf"
		emp.save(ignore_permissions=True)
		row = self._row(emp, self.address)
		self.assertEqual(row.status, "Received")
		self.assertEqual(str(row.received_on), today())
		self.assertEqual(row.received_by, "Administrator")
		self.assertIn("1 received", emp.documents_summary)

	def test_only_a_verifier_role_can_verify(self):
		emp = self._employee()
		self._row(emp, self.id_card).status = "Verified"
		frappe.set_user("doc.tester@example.com")
		try:
			with self.assertRaises(frappe.PermissionError):
				emp.save(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")
		emp.reload()
		self._row(emp, self.id_card).status = "Verified"
		emp.save(ignore_permissions=True)
		row = self._row(emp, self.id_card)
		self.assertEqual(row.verified_by, "Administrator")
		self.assertEqual(str(row.verified_on), today())
		# a type with no verifier roles can be verified by anyone who can edit the employee
		self._row(emp, self.address).status = "Verified"
		emp.save(ignore_permissions=True)
		self.assertEqual(self._row(emp, self.address).status, "Verified")

	def test_expiry_job(self):
		emp = self._employee()
		row = self._row(emp, self.licence)
		row.status = "Verified"
		row.expiry_date = add_days(today(), -1)
		emp.save(ignore_permissions=True)
		# validate already expires a row whose date has passed
		self.assertEqual(self._row(emp, self.licence).status, "Expired")
		row = self._row(emp, self.licence)
		row.status = "Verified"
		row.expiry_date = add_days(today(), 30)
		emp.save(ignore_permissions=True)
		self.assertEqual(self._row(emp, self.licence).status, "Verified")
		frappe.db.set_value("Employee Document", row.name, "expiry_date", add_days(today(), -2))
		frappe.db.set_value("Employee", emp.name, "user_id", "doc.tester@example.com")
		result = expire_documents()
		self.assertGreaterEqual(result["expired"], 1)
		self.assertEqual(frappe.db.get_value("Employee Document", row.name, "status"), "Expired")
		self.assertIn("expired", frappe.db.get_value("Employee", emp.name, "documents_summary"))
		# the employee is told on the portal bell, not only by email
		self.assertTrue(frappe.db.exists("Notification Log", {"for_user": "doc.tester@example.com",
		                                                      "document_name": emp.name}))

	def test_portal_attach_and_compliance(self):
		emp = self._employee()
		row = self._row(emp, self.address)
		attach_document(row.name, "/private/files/address.pdf", emp.name)
		self.assertEqual(frappe.db.get_value("Employee Document", row.name, "status"), "Received")
		with self.assertRaises(frappe.ValidationError):
			attach_document(self._row(emp, self.licence).name, "/private/files/x.pdf", emp.name)   # HR collects it
		with self.assertRaises(frappe.PermissionError):
			attach_document(row.name, "/private/files/x.pdf", "HR-EMP-NOBODY")
		missing = {m["employee"]: m for m in employees_missing_mandatory()}
		self.assertIn(emp.name, missing)
		self.assertEqual({m["document_type"] for m in missing[emp.name]["missing"]},
		                 {self.id_card.name, self.address.name})

	def test_backfill_fills_only_what_is_missing(self):
		from hrms.alvoraa_employee_documents.employee_documents import backfill_checklists
		emp = self._employee()
		before = len(emp.employee_documents)
		self.assertEqual(backfill_checklists([emp.name]), 0)
		extra = _type("Late Addition", category="Employment")
		try:
			self.assertEqual(backfill_checklists([emp.name]), 1)
			emp.reload()
			self.assertEqual(len(emp.employee_documents), before + 1)
			self.assertIn(extra.name, {r.document_type for r in emp.employee_documents})
		finally:
			frappe.delete_doc("Employee Document Type", extra.name, ignore_permissions=True, force=True)

	def test_summary_text(self):
		rows = [frappe._dict(status=s) for s in ("Verified", "Verified", "Received", "Pending", "Expired")]
		self.assertEqual(summary_text(rows), "1 pending · 1 received · 2 verified · 1 expired")
