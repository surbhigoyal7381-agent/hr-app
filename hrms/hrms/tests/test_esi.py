"""ESI support for Indian companies: fields, default switch, report."""

import frappe
from frappe.tests import IntegrationTestCase

from hrms.regional.india.setup import make_custom_fields
from hrms.regional.india.utils import ESI_WAGE_CEILING, set_esi_applicable


class TestESI(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_custom_fields()
		frappe.clear_cache()

	def test_fields_exist(self):
		self.assertTrue(frappe.get_meta("Employee").has_field("esi_number"))
		meta = frappe.get_meta("Salary Structure Assignment")
		self.assertTrue(meta.has_field("esi_applicable"))
		self.assertTrue(meta.has_field("pf_applicable"))
		options = frappe.get_meta("Salary Component").get_field("component_type").options
		self.assertIn("ESI", options.split("\n"))
		self.assertIn("Employer ESI", options.split("\n"))

	def _assignment(self, base, country="India"):
		company = frappe.get_all("Company", filters={"country": country}, pluck="name", limit=1)
		if not company:
			company = [frappe.get_all("Company", pluck="name", limit=1)[0]]
			frappe.db.set_value("Company", company[0], "country", country)
		doc = frappe.new_doc("Salary Structure Assignment")
		doc.company = company[0]
		doc.base = base
		return doc

	def test_switch_defaults_from_base(self):
		below = self._assignment(ESI_WAGE_CEILING)
		set_esi_applicable(below)
		self.assertEqual(below.esi_applicable, 1)
		self.assertEqual(below.pf_applicable, 1)      # custom field default

		above = self._assignment(ESI_WAGE_CEILING + 1)
		set_esi_applicable(above)
		self.assertEqual(above.esi_applicable, 0)

	def test_explicit_switch_is_kept(self):
		doc = self._assignment(ESI_WAGE_CEILING + 5000)
		doc.esi_applicable = 1          # HR keeps a person covered after a raise
		set_esi_applicable(doc)
		self.assertEqual(doc.esi_applicable, 1)

	def test_report_without_components_is_empty(self):
		from hrms.payroll.report.esi_deductions.esi_deductions import execute

		frappe.db.sql("update `tabSalary Component` set component_type='' where component_type in ('ESI','Employer ESI')")
		columns, data = execute({"company": frappe.get_all("Company", pluck="name", limit=1)[0], "month": 8, "year": 2026})
		self.assertEqual(data, [])
