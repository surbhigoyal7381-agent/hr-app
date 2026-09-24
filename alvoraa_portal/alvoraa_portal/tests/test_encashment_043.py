"""Slice 043, AC-55: leave encashment, which never worked.

**The defect, corrected after this file went red.** `leave_period` and
`currency` are both `reqd` on Leave Encashment - read field by field in
`leave_encashment.json` - and `hr_api.submit_leave_encashment` set neither. I
first wrote that both therefore crashed. Only one does:

  * **`leave_period` genuinely fails.** Nothing fetches it, nothing defaults
    it, and the mandatory check stops the insert. So every claim an employee
    sent through the portal failed, and the portal showed a generic error.
    Appendix C recorded the button as never proven end to end (F-5); this is
    why. `test_it_fails_without_the_period` is the proof.
  * **`currency` never crashed.** It is `read_only` AND `reqd`, and Frappe
    fills a Link field named `currency` from the site's Global Defaults before
    the mandatory check runs. So it was quietly stamped with the SITE's
    currency rather than the one the employee is paid in - which then goes
    into a payroll component. That is a smaller bug and a worse kind.

**What this file proves, and what it does not.** It proves the period is set
and a claim saves; that taking the period away still breaks it; and that the
currency now follows the employee's own Salary Structure Assignment rather
than the site, using a second employee paid in USD. It does NOT prove the
encashment amount is right: valuing one needs a real payroll run, and nothing
in this slice calculates a figure.

Its own company and people, tag `S043E2`.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import hr_api

TAG = "S043E2"
COMPANY = "S043E2 Encashment Company"
ABBR = "S4E2"
LEAVE_TYPE = "S043E2 Encashable Leave"
STRUCTURE = "S043E2 Structure"
STRUCTURE_USD = "S043E2 Structure USD"
EARNING = "S043E2 Basic"
ENCASH_COMPONENT = "S043E2 Encashment"

FROM_DATE = "2026-01-01"
TO_DATE = "2026-12-31"
ENCASH_ON = "2026-09-01"


def _ensure(doctype, name, **values):
	if name and frappe.db.exists(doctype, name):
		return frappe.get_doc(doctype, name)
	doc = frappe.get_doc({"doctype": doctype, **values})
	if name:
		doc.name = name
		doc.set("__newname", name)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_mandatory=True)
	return doc


def _user(local):
	email = "s043e2.%s@example.com" % local
	if not frappe.db.exists("User", email):
		doc = frappe.get_doc({"doctype": "User", "email": email,
		                      "first_name": local.title(),
		                      "send_welcome_email": 0,
		                      "roles": [{"role": "Employee"}]})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
	frappe.db.set_value("User", email, "module_profile", None,
	                    update_modified=False)
	frappe.db.delete("Block Module", {"parent": email, "parenttype": "User"})
	frappe.clear_cache(user=email)
	return email


class EncashmentFixture(FrappeTestCase):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = _ensure("Company", COMPANY, company_name=COMPANY,
		                      abbr=ABBR, default_currency="INR",
		                      country="India").name
		cls.login = _user("rahul")
		cls.employee = cls._employee()

		_ensure("Salary Component", EARNING, salary_component=EARNING,
		        salary_component_abbr="S4E2B", type="Earning")
		_ensure("Salary Component", ENCASH_COMPONENT,
		        salary_component=ENCASH_COMPONENT,
		        salary_component_abbr="S4E2E", type="Earning")

		# `allow_encashment` and an earning component, or Frappe HR refuses the
		# type before it ever reaches the mandatory fields this test is about.
		_ensure("Leave Type", LEAVE_TYPE, leave_type_name=LEAVE_TYPE,
		        allow_encashment=1, earning_component=ENCASH_COMPONENT,
		        max_encashable_leaves=5, non_encashable_leaves=0)

		cls.period = cls._leave_period()
		cls._allocation(cls.employee)
		cls._salary_structure(cls.employee, STRUCTURE, "INR")

		# A second person, paid in USD. Without them "the currency is right"
		# passes on a site whose default happens to be the right answer.
		cls.usd_login = _user("dollar")
		cls.usd_employee = cls._employee(first="Dollar", login=cls.usd_login)
		cls._allocation(cls.usd_employee)
		cls._salary_structure(cls.usd_employee, STRUCTURE_USD, "USD")
		frappe.db.commit()

	@classmethod
	def _employee(cls, first="Rahul", login=None):
		login = login or cls.login
		name = frappe.db.get_value("Employee",
		                           {"first_name": first, "last_name": TAG},
		                           "name")
		doc = frappe.get_doc("Employee", name) if name else frappe.get_doc({
			"doctype": "Employee", "first_name": first, "last_name": TAG,
			"date_of_birth": "1990-01-01",
			"gender": frappe.get_all("Gender", pluck="name", limit=1)[0]})
		doc.company = COMPANY
		doc.date_of_joining = "2024-01-01"
		doc.status = "Active"
		doc.user_id = login
		doc.create_user_permission = 0
		doc.flags.ignore_permissions = True
		doc.save(ignore_permissions=True)
		frappe.db.delete("User Permission", {"user": login})
		frappe.clear_cache(user=login)
		return doc.name

	@classmethod
	def _leave_period(cls):
		"""Leave Period autonames from a series (`HR-LPR-.YYYY.-.#####`), so a
		name cannot be forced on it. The first version of this fixture tried,
		got a series name back, then failed to link to the name it thought it
		had made."""
		existing = frappe.db.get_value("Leave Period", {"company": COMPANY,
		                                               "from_date": FROM_DATE},
		                               "name")
		if existing:
			return existing
		doc = frappe.get_doc({
			"doctype": "Leave Period",
			"from_date": FROM_DATE, "to_date": TO_DATE,
			"company": COMPANY, "is_active": 1})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True, ignore_mandatory=True)
		return doc.name

	@classmethod
	def _allocation(cls, employee):
		if frappe.db.exists("Leave Allocation",
		                    {"employee": employee, "leave_type": LEAVE_TYPE,
		                     "docstatus": 1}):
			return
		doc = frappe.get_doc({
			"doctype": "Leave Allocation", "employee": employee,
			"leave_type": LEAVE_TYPE, "from_date": FROM_DATE,
			"to_date": TO_DATE, "new_leaves_allocated": 5,
			"leave_period": cls.period, "company": COMPANY, "carry_forward": 0})
		doc.flags.ignore_permissions = True
		doc.flags.ignore_validate = True
		doc.insert(ignore_permissions=True, ignore_mandatory=True)
		doc.db_set("total_leaves_allocated", 5, update_modified=False)
		doc.db_set("docstatus", 1, update_modified=False)
		entry = frappe.get_doc({
			"doctype": "Leave Ledger Entry", "employee": employee,
			"leave_type": LEAVE_TYPE, "company": COMPANY,
			"transaction_type": "Leave Allocation", "transaction_name": doc.name,
			"from_date": FROM_DATE, "to_date": TO_DATE,
			"leaves": 5, "is_carry_forward": 0, "is_expired": 0})
		entry.flags.ignore_permissions = True
		entry.insert(ignore_permissions=True, ignore_mandatory=True)
		entry.db_set("docstatus", 1, update_modified=False)

	@classmethod
	def _salary_structure(cls, employee, structure, currency):
		"""A real structure and assignment.

		`get_employee_currency` reads the currency off the Salary Structure
		Assignment and throws a plain sentence when there is none, and
		`LeaveEncashment.set_salary_structure` needs an assigned structure too.
		Both are real setup, not decoration: an employee with no structure
		genuinely cannot be paid an encashment.
		"""
		if not frappe.db.exists("Salary Structure", structure):
			doc = frappe.get_doc({
				"doctype": "Salary Structure", "__newname": structure,
				"company": COMPANY, "currency": currency,
				"payroll_frequency": "Monthly",
				"earnings": [{"salary_component": EARNING, "amount": 30000}],
				"docstatus": 0})
			doc.name = structure
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True, ignore_mandatory=True)
			doc.db_set("docstatus", 1, update_modified=False)
		if frappe.db.exists("Salary Structure Assignment",
		                    {"employee": employee, "docstatus": 1}):
			return
		assignment = frappe.get_doc({
			"doctype": "Salary Structure Assignment", "employee": employee,
			"salary_structure": structure, "from_date": FROM_DATE,
			"company": COMPANY, "currency": currency, "base": 30000})
		assignment.flags.ignore_permissions = True
		assignment.flags.ignore_validate = True
		assignment.insert(ignore_permissions=True, ignore_mandatory=True)
		assignment.db_set("docstatus", 1, update_modified=False)

	def setUp(self):
		frappe.set_user(self.login)

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in frappe.get_all(
				"Leave Encashment",
				filters={"employee": ["in", [self.employee, self.usd_employee]]},
				pluck="name"):
			frappe.delete_doc("Leave Encashment", name, force=True,
			                  ignore_permissions=True)
		frappe.db.commit()


class TestTheTwoFieldsThatWereNeverSet(EncashmentFixture):

	def test_a_claim_actually_saves(self):
		"""The whole point. Before this fix it threw on a mandatory field."""
		result = hr_api.submit_leave_encashment(LEAVE_TYPE,
		                                        encashment_date=ENCASH_ON)
		self.assertTrue(result["name"])
		self.assertTrue(frappe.db.exists("Leave Encashment", result["name"]))

	def test_the_leave_period_is_the_one_covering_the_date(self):
		result = hr_api.submit_leave_encashment(LEAVE_TYPE,
		                                        encashment_date=ENCASH_ON)
		self.assertEqual(
			frappe.db.get_value("Leave Encashment", result["name"],
			                    "leave_period"), self.period)

	def test_the_currency_comes_from_the_salary_structure_assignment(self):
		result = hr_api.submit_leave_encashment(LEAVE_TYPE,
		                                        encashment_date=ENCASH_ON)
		self.assertEqual(
			frappe.db.get_value("Leave Encashment", result["name"], "currency"),
			"INR")

	def test_both_fields_are_still_mandatory(self):
		"""The guard that makes the three tests above mean something.

		If a later Frappe HR release made either field optional, they would all
		still pass while the fix had stopped mattering - and nobody would know
		the portal had gone back to relying on luck.
		"""
		meta = frappe.get_meta("Leave Encashment")
		self.assertTrue(meta.get_field("leave_period").reqd)
		self.assertTrue(meta.get_field("currency").reqd)

	def test_it_fails_without_the_period(self):
		"""Proving the fix is what makes it work, by taking it away.

		The same document the endpoint builds, minus `leave_period`. If this
		saved, the endpoint's fix would be decoration.
		"""
		frappe.set_user("Administrator")
		doc = frappe.get_doc({
			"doctype": "Leave Encashment", "employee": self.employee,
			"leave_type": LEAVE_TYPE, "encashment_date": ENCASH_ON,
			"currency": "INR"})
		doc.flags.ignore_permissions = True
		with self.assertRaises(frappe.MandatoryError):
			doc.insert(ignore_permissions=True)

	def test_the_currency_is_filled_from_the_site_default_when_nobody_sets_it(self):
		"""**A correction to what I first wrote about this defect.**

		I claimed both mandatory fields failed. Only `leave_period` does. This
		test asserted `currency` failed too, and went red - because `currency`
		is `read_only` AND `reqd`, and Frappe fills a Link field named
		`currency` from the site's Global Defaults before the mandatory check
		ever sees it.

		So the currency was never a crash. It was something quieter: the
		SITE's currency, silently, whatever the employee is actually paid in.
		`test_the_currency_is_the_employees_own_not_the_sites` is the one that
		matters now.
		"""
		frappe.set_user("Administrator")
		doc = frappe.get_doc({
			"doctype": "Leave Encashment", "employee": self.employee,
			"leave_type": LEAVE_TYPE, "encashment_date": ENCASH_ON,
			"leave_period": self.period})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		self.assertTrue(doc.currency)

	def test_the_currency_is_the_employees_own_not_the_sites(self):
		"""The real currency defect, and why setting it server-side matters.

		This employee is paid in USD - their Salary Structure Assignment says
		so. Left to Frappe's default the encashment would be stamped with the
		site's INR, and an amount in the wrong currency goes straight into a
		payroll component.
		"""
		frappe.set_user(self.usd_login)
		result = hr_api.submit_leave_encashment(LEAVE_TYPE,
		                                        encashment_date=ENCASH_ON)
		self.assertEqual(
			frappe.db.get_value("Leave Encashment", result["name"], "currency"),
			"USD")

	def test_the_site_default_really_is_something_else(self):
		"""The guard that makes the test above mean something: if the site
		default were already USD, it would pass whatever the code did."""
		self.assertNotEqual(frappe.defaults.get_defaults().get("currency"),
		                    "USD")


class TestWhenTheSetupIsMissing(EncashmentFixture):
	"""A setup gap must say what to do next, not "mandatory field"."""

	def test_no_leave_period_covering_the_date_says_so_plainly(self):
		try:
			hr_api.submit_leave_encashment(LEAVE_TYPE,
			                               encashment_date="2030-06-01")
		except frappe.ValidationError as exc:
			message = str(exc)
		else:
			raise AssertionError("a date outside every period was accepted")
		self.assertIn("no leave period covers that date", message)
		self.assertIn("Ask HR", message)

	def test_the_message_does_not_name_a_field(self):
		"""'Leave Period is mandatory' tells an employee nothing they can act
		on. It is HR's setting, and the sentence has to say so."""
		try:
			hr_api.submit_leave_encashment(LEAVE_TYPE,
			                               encashment_date="2030-06-01")
		except frappe.ValidationError as exc:
			message = str(exc)
		self.assertNotIn("leave_period", message)
		self.assertNotIn("mandatory", message.lower())
