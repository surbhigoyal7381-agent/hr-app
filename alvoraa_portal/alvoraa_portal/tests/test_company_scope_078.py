"""078 · D-4 — cross-company isolation for the slice's two new READ endpoints.

**Why this file exists.** `04-test-report.md` raised D-4: the mini profile and
the employee documents are the two surfaces in this slice that hand a reader
another person's details and another person's files, and both were exercised
against **one company only**. Branch scoping was proved; company scoping was
not, and **no CXO persona appeared anywhere in the slice**. In an HRMS the
worst bug is not a crash, it is the wrong person reading the right data, so a
company boundary that is only reasoned about is an untested control.

**What is proved here, and nothing more.**

  * an HR Manager whose scope is one company is REFUSED a person in another
    company, on both endpoints and on the document stream;
  * the refusal is a refusal, not an empty answer - an empty profile or an
    empty list is still an answer, and an answer confirms that the person
    exists;
  * the refusal says nothing about the company, the branch, the person or the
    document type;
  * a **CXO** - System Manager, which is what `access.permitted_companies`
    treats as CXO - reads both companies. Without this the refusals above
    could all be passing because the data is simply unreachable;
  * an ordinary **Employee** holds neither surface at all;
  * a reader with no companies fails closed;
  * a refused read writes **no** access-log row, so the audit trail cannot be
    used to confirm that a person in another company exists.

**The fixtures are the ones that already exist.** `fixtures_078` records a real
reason it builds no second company - `ensure_company()` would then hand every
other suite a company with no holiday list and no fiscal year - so nothing in
that file is changed here. `fixtures_045.second_company()` is the company this
uses: backdated for exactly that reason, and already used this way by
`test_directory_contact_045`. The out-of-company person is put in **STORE_A**,
the same branch as everybody in scope, so the ONLY difference between them and
somebody readable is the company.

Every endpoint is called DIRECTLY, not through a screen, because a whitelisted
method is reachable without one.
"""

import frappe

from alvoraa_portal import employee_documents_read as docs
from alvoraa_portal import positions_profile
from alvoraa_portal.tests import fixtures_078 as fx
from alvoraa_portal.tests.fixtures_045 import (
	STORE_A,
	Wave4Base,
	own_employee,
	own_user,
	second_company,
)


class _Base(Wave4Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.p = fx.people()
		cls.ticked, cls.unticked = fx.document_types()

		# The other company, and one person in it - same branch, so the company
		# is the only thing that differs.
		cls.other_company = second_company()
		cls.far = own_employee("S078FarCompany", branch=STORE_A,
		                       company=cls.other_company)
		cls.far_rows = fx.give_documents(cls.far)

		# Somebody readable, for the control case in every test below.
		cls.near = cls.p["no_photo"]
		cls.near_rows = fx.give_documents(cls.near)

		# **The CXO.** `access.permitted_companies` treats System Manager as
		# CXO, and `Alvoraa Position` grants it Read - so this one login spans
		# both companies and is the persona the whole slice was missing.
		cls.cxo_user = own_user("s078cxo", ("Employee", "System Manager"))
		# A plain Employee, holding neither surface.
		cls.staff_user = cls.p["no_photo_user"]

	def setUp(self):
		super().setUp()
		# The plan, or every documents case tests the plan gate instead.
		self._plan = fx.with_documents_plan().__enter__()
		self.addCleanup(self._plan.__exit__)
		fx.set_lists(profile_fields=["designation", "branch", "company"],
		             document_types=[self.ticked])
		self._clear_views()

	def tearDown(self):
		frappe.set_user("Administrator")
		fx.clear_lists()
		super().tearDown()

	def _clear_views(self):
		for row in fx.document_views():
			frappe.delete_doc("Alvoraa Photo Access Log", row.name, force=True,
			                  ignore_permissions=True)
		frappe.db.commit()

	def _stream(self, row):
		"""Open one document, with `frappe.local.response` PUT BACK afterwards.

		The response object belongs to the request, not to this test: a test
		that leaves a replacement behind is the kind of leak that makes the
		next module fail for a reason that is in nobody's code.
		"""
		before = frappe.local.response
		frappe.local.response = frappe._dict()
		try:
			docs.open_employee_document(row=row)
			return frappe.local.response
		finally:
			frappe.local.response = before


class TestTheCompanyBoundary(_Base):
	"""An HR Manager scoped to one company, asking about another."""

	def test_the_mini_profile_refuses_a_person_in_another_company(self):
		frappe.set_user(self.p["hr_wide_user"])
		# The control: somebody in their own company reads fine, so the refusal
		# below is about the company and not about the fixture.
		self.assertTrue(positions_profile.get_positions_profile(
			employee=self.near)["employee_name"])
		with self.assertRaises(frappe.PermissionError):
			positions_profile.get_positions_profile(employee=self.far)

	def test_the_documents_list_refuses_a_person_in_another_company(self):
		"""A REFUSAL, not `{"documents": []}`."""
		frappe.set_user(self.p["hr_wide_user"])
		self.assertEqual(
			[d["document_type"]
			 for d in docs.get_employee_documents(employee=self.near)["documents"]],
			[self.ticked])
		with self.assertRaises(frappe.PermissionError):
			docs.get_employee_documents(employee=self.far)

	def test_a_document_row_in_another_company_cannot_be_opened(self):
		"""The row id is real and its type is ticked, so the only thing
		stopping this read is the company."""
		frappe.set_user(self.p["hr_wide_user"])
		self.assertEqual(self._stream(self.near_rows[self.ticked]).type, "download")
		with self.assertRaises(frappe.PermissionError):
			self._stream(self.far_rows[self.ticked])

	def test_the_refusal_names_no_company_person_branch_or_type(self):
		"""A message is a disclosure too."""
		frappe.set_user(self.p["hr_wide_user"])
		secrets = [self.other_company, self.far, self.ticked, STORE_A]
		far_name = frappe.db.get_value("Employee", self.far, "employee_name")
		if far_name:
			secrets.append(far_name)
		calls = {
			"profile": lambda: positions_profile.get_positions_profile(
				employee=self.far),
			"list": lambda: docs.get_employee_documents(employee=self.far),
			"stream": lambda: self._stream(self.far_rows[self.ticked]),
		}
		for label, call in calls.items():
			with self.subTest(call=label):
				with self.assertRaises(frappe.PermissionError) as caught:
					call()
				said = str(caught.exception)
				for secret in secrets:
					self.assertNotIn(str(secret), said)

	def test_a_refused_read_writes_no_access_log_row(self):
		"""The log is a record of real reads. A row written on a refusal would
		itself confirm that a person in another company exists."""
		frappe.set_user(self.p["hr_wide_user"])
		with self.assertRaises(frappe.PermissionError):
			self._stream(self.far_rows[self.ticked])
		frappe.set_user("Administrator")
		self.assertEqual(fx.document_views(self.far), [])


class TestTheCxo(_Base):
	"""The persona the slice had none of. This is what stops every refusal
	above passing because the data is simply unreachable."""

	def test_a_cxo_reads_a_profile_in_either_company(self):
		self.assertEqual(
			frappe.db.get_value("Employee", self.far, "company"), self.other_company)
		frappe.set_user(self.cxo_user)
		for employee in (self.near, self.far):
			with self.subTest(employee=employee):
				out = positions_profile.get_positions_profile(employee=employee)
				self.assertTrue(out["employee_name"])

	def test_a_cxo_opens_a_document_in_either_company(self):
		frappe.set_user(self.cxo_user)
		for label, rows in (("near", self.near_rows), ("far", self.far_rows)):
			with self.subTest(rows=label):
				self.assertEqual(self._stream(rows[self.ticked]).type, "download")


class TestTheOtherTwoPersonas(_Base):
	def test_an_ordinary_employee_holds_neither_surface(self):
		"""Persona three. `may_view()` is Read on `Alvoraa Position`, which the
		Employee role does not hold - in their own company or in any other."""
		frappe.set_user(self.staff_user)
		for employee in (self.near, self.far):
			with self.subTest(employee=employee):
				with self.assertRaises(frappe.PermissionError):
					positions_profile.get_positions_profile(employee=employee)
				with self.assertRaises(frappe.PermissionError):
					docs.get_employee_documents(employee=employee)

	def test_a_reader_with_no_company_of_their_own_fails_closed(self):
		"""HR Manager, no Company User Permission and no Employee record of
		their own - so `permitted_companies` comes back empty and every name is
		refused, in either company."""
		frappe.set_user(self.p["nobody_user"])
		for employee in (self.near, self.far):
			with self.subTest(employee=employee):
				with self.assertRaises(frappe.PermissionError):
					positions_profile.get_positions_profile(employee=employee)
				with self.assertRaises(frappe.PermissionError):
					docs.get_employee_documents(employee=employee)
