"""Screening rules on a Job Opening, applied to applicants as they come in."""

import frappe
from frappe.tests import IntegrationTestCase

from hrms.alvoraa_screening.screening import evaluate, rules_for
from hrms.alvoraa_screening.setup import make_custom_fields

GOOD = {
	"screening_retail_experience": "Yes",
	"screening_years_in_category": 5,
	"screening_product_knowledge": "Yes",
	"screening_roster_ok": "Yes",
	"screening_festival_ok": "Yes",
	"screening_expected_monthly_ctc": 40000,
}


def _company():
	return frappe.get_all("Company", pluck="name", limit=1)[0]


class TestScreening(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_custom_fields()
		frappe.clear_cache()
		frappe.conf.features = list(frappe.conf.get("features") or []) + ["screening_forms"]
		cls.company = _company()
		if not frappe.db.exists("Designation", "Screening Tester"):
			frappe.get_doc({"doctype": "Designation", "designation_name": "Screening Tester"}).insert(ignore_permissions=True)
		cls.opening = cls._opening("Screening Test Opening", screening_require_retail_experience=1, screening_min_years=3,
		                           screening_require_product_knowledge=1, screening_require_roster_ok=1,
		                           screening_require_festival_ok=1, screening_max_monthly_ctc=50000)
		cls.plain = cls._opening("Screening Test Plain Opening")

	@classmethod
	def _opening(cls, title, **rules):
		name = frappe.db.get_value("Job Opening", {"job_title": title}, "name")
		if name:
			doc = frappe.get_doc("Job Opening", name)
			doc.update(rules)
			doc.save(ignore_permissions=True)
			return doc
		doc = frappe.get_doc({"doctype": "Job Opening", "job_title": title, "company": cls.company,
		                      "designation": "Screening Tester", "status": "Open", "publish": 0, **rules})
		doc.insert(ignore_permissions=True)
		return doc

	def setUp(self):
		super().setUp()
		for name in frappe.get_all("Job Applicant", {"email_id": ["like", "%@screening-test.demo"]}, pluck="name"):
			frappe.delete_doc("Job Applicant", name, ignore_permissions=True, force=True)

	def _applicant(self, email, opening, **answers):
		doc = frappe.get_doc({"doctype": "Job Applicant", "applicant_name": "Screening " + email.split("@")[0],
		                      "email_id": email, "job_title": opening.name, "status": "Open", **answers})
		doc.insert(ignore_permissions=True)
		return doc

	def test_rules_are_read_from_the_opening(self):
		self.assertEqual(rules_for(self.opening.name)["screening_min_years"], 3)
		self.assertIsNone(rules_for(self.plain.name))

	def test_evaluate(self):
		self.assertEqual(evaluate(GOOD, rules_for(self.opening.name))[0], "Passed")
		result, reasons = evaluate({**GOOD, "screening_years_in_category": 2}, rules_for(self.opening.name))
		self.assertEqual(result, "Screened Out")
		self.assertIn("minimum 3", reasons[0])
		result, reasons = evaluate({**GOOD, "screening_expected_monthly_ctc": 60000, "screening_festival_ok": "No"},
		                           rules_for(self.opening.name))
		self.assertEqual(result, "Screened Out")
		self.assertEqual(len(reasons), 2)

	def test_applicant_is_screened_on_the_way_in(self):
		ok = self._applicant("ok@screening-test.demo", self.opening, **GOOD)
		self.assertEqual(ok.screening_result, "Passed")
		self.assertEqual(ok.status, "Open")
		out = self._applicant("out@screening-test.demo", self.opening, **{**GOOD, "screening_retail_experience": "No"})
		self.assertEqual(out.screening_result, "Screened Out")
		self.assertEqual(out.status, "Rejected")
		self.assertIn("retail experience", out.screening_notes)

	def test_no_rules_or_no_answers_means_no_verdict(self):
		plain = self._applicant("plain@screening-test.demo", self.plain, **GOOD)
		self.assertFalse(plain.screening_result)
		silent = self._applicant("silent@screening-test.demo", self.opening)
		self.assertFalse(silent.screening_result)
		self.assertEqual(silent.status, "Open")

	def test_the_web_form_ships_with_the_app(self):
		self.assertTrue(frappe.db.exists("Web Form", "screening-application"))
		wf = frappe.get_doc("Web Form", "screening-application")
		self.assertEqual(wf.doc_type, "Job Applicant")
		self.assertEqual(wf.login_required, 0)
		self.assertIn("screening_years_in_category", [f.fieldname for f in wf.web_form_fields])
