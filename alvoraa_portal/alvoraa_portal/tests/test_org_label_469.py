"""ALV-469: the portal names the person's own organisation, not the site's.

Each test name carries alv469 so a merge that drops the feature fails CI.
"""

import os
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from alvoraa_portal import org_label as ol
from alvoraa_portal.patches.v1_0 import alv469_org_fields_from_dtc as copy_patch

SITE = "Alv469 Site Name"
COMPANY_B = "Alv469 Company B"
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _company(name, abbr):
	if not frappe.db.exists("Company", name):
		if not frappe.db.exists("Warehouse Type", "Transit"):
			frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "Company", "company_name": name, "abbr": abbr,
		                "default_currency": "INR", "country": "India"}).insert(ignore_permissions=True)
	return name


def _gender():
	return (frappe.db.get_value("Gender", {}, "name")
	        or frappe.get_doc({"doctype": "Gender", "gender": "Other"}).insert(ignore_permissions=True).name)


def _user(label, *roles):
	email = f"alv469.{label}@example.com"
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": "Alv469" + label,
		                "send_welcome_email": 0}).insert(ignore_permissions=True)
	if roles:
		frappe.get_doc("User", email).add_roles(*roles)
	return email


def _employee(label, user, employment_type=None, agency=None, company=COMPANY_B):
	"""One Employee, linked to `user`. Fields are set on the row afterwards, so
	the test controls them exactly."""
	name = frappe.db.get_value("Employee", {"first_name": "Alv469" + label})
	if not name:
		name = frappe.get_doc({
			"doctype": "Employee", "first_name": "Alv469" + label, "company": company,
			"date_of_birth": "1990-01-01", "date_of_joining": "2015-01-01",
			"gender": _gender(), "status": "Active", "user_id": user,
			"create_user_permission": 0,
		}).insert(ignore_permissions=True).name
	frappe.db.set_value("Employee", name, {"employment_type": employment_type,
	                                       ol.AGENCY_FIELD: agency, "company": company})
	return name


def _type(name):
	if not frappe.db.exists("Employment Type", name):
		frappe.get_doc({"doctype": "Employment Type", "employee_type_name": name}).insert(ignore_permissions=True)


class OrgLabelAlv469(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		_company(COMPANY_B, "A469B")
		for t in ("Contract", "Full-time"):
			_type(t)
		cls.user = _user("one", "Employee")
		frappe.db.commit()

	def setUp(self):
		frappe.set_user("Administrator")
		self._old_name = frappe.conf.get("tenant_name")
		frappe.conf.tenant_name = SITE

	def tearDown(self):
		if self._old_name is None:
			frappe.conf.pop("tenant_name", None)
		else:
			frappe.conf.tenant_name = self._old_name
		frappe.db.rollback()

	def _label(self, **kw):
		_employee("One", self.user, **kw)
		return ol.org_label(self.user)

	# the five rules -------------------------------------------------------
	def test_alv469_a_permanent_person_sees_their_company_not_the_site_name(self):
		got = self._label(employment_type="Full-time")
		self.assertEqual(got, COMPANY_B)
		self.assertNotEqual(got, SITE)

	def test_alv469_no_employment_type_also_shows_the_company(self):
		self.assertEqual(self._label(employment_type=None), COMPANY_B)

	def test_alv469_a_contract_person_with_an_agency_sees_the_agency(self):
		self.assertEqual(self._label(employment_type="Contract", agency="Alv469 Agency"), "Alv469 Agency")

	def test_alv469_a_contract_person_with_no_agency_sees_their_own_name(self):
		self.assertEqual(self._label(employment_type="Contract"), "Alv469One")

	def test_alv469_a_gig_worker_and_a_freelancer_see_their_own_name(self):
		for kind in ol.OWN_NAME_TYPES:
			_type(kind)
			# the agency is ignored for these two, even when one is set
			self.assertEqual(self._label(employment_type=kind, agency="Alv469 Agency"), "Alv469One", kind)

	def test_alv469_a_user_with_no_employee_row_sees_the_site_name(self):
		lonely = _user("lonely")
		with patch("frappe.log_error") as logged:
			self.assertEqual(ol.org_label(lonely), SITE)
		self.assertFalse(logged.called, "no Employee row is normal, not an error")

	def test_alv469_any_error_gives_the_site_name_and_never_raises(self):
		_employee("One", self.user, employment_type="Full-time")
		with patch("frappe.get_all", side_effect=RuntimeError("boom")), \
		     patch("frappe.log_error") as logged:
			self.assertEqual(ol.org_label(self.user), SITE)
		self.assertTrue(logged.called, "the failure is logged, not swallowed")

	def test_alv469_the_agency_is_read_through_one_constant(self):
		self.assertEqual(ol.AGENCY_FIELD, "employment_agency")
		_employee("One", self.user, employment_type="Contract", agency="Alv469 Agency")
		with patch.object(ol, "AGENCY_FIELD", "no_such_field"):
			# a name that is not a field is treated as "no agency", not an error
			self.assertEqual(ol.org_label(self.user), "Alv469One")

	def test_alv469_the_page_context_carries_brand_label(self):
		from alvoraa_portal.www import hrms_employee

		_employee("One", self.user, employment_type="Full-time")
		frappe.set_user(self.user)
		context = frappe._dict()
		try:
			hrms_employee.get_context(context)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(context.brand_label, COMPANY_B)
		self.assertEqual(context.tenant_name, SITE)

	# the templates --------------------------------------------------------
	def _render(self, path):
		ctx = {"brand_label": "Alv469 Org Label", "tenant_name": "Alv469 Tenant Only",
		       "brand_mark_url": "/m.png", "primary_color": "#000", "accent_color": "#000"}
		return frappe.render_template(path, ctx)

	def test_alv469_the_classic_frame_shows_the_label_in_three_places_and_never_the_tenant_name(self):
		html = self._render("templates/includes/ess/frame.html")
		self.assertIn('sidebar-brand-logo">A<', html)
		self.assertIn('class="sidebar-brand-name" title="Alv469 Org Label">Alv469 Org Label<', html)
		self.assertIn('class="mob-brand" title="Alv469 Org Label">Alv469 Org Label<', html)
		self.assertNotIn("Alv469 Tenant Only", html)

	def test_alv469_the_next_frame_shows_the_label_in_two_places_and_never_the_tenant_name(self):
		html = self._render("templates/includes/ess/next/frame.html")
		self.assertIn('class="nf-brand-mark" aria-hidden="true">A', html)
		self.assertIn('class="nf-brand-name" title="Alv469 Org Label">Alv469 Org Label<', html)
		self.assertNotIn("Alv469 Tenant Only", html)

	def test_alv469_a_hostile_name_is_escaped_in_both_frames(self):
		for hostile in ('Ravi" onmouseover="alert(1)', "<b>x</b>"):
			for path in ("templates/includes/ess/frame.html", "templates/includes/ess/next/frame.html"):
				html = frappe.render_template(path, {"brand_label": hostile, "brand_mark_url": "/m.png"})
				self.assertNotIn('onmouseover="alert(1)', html, path)
				self.assertNotIn("<b>x</b>", html, path)
		html = frappe.render_template("templates/includes/ess/frame.html", {"brand_label": "<b>x</b>"})
		self.assertIn("&lt;b&gt;x&lt;/b&gt;", html)
		self.assertIn('sidebar-brand-logo">&lt;', html)

	def test_alv469_titles_and_the_app_name_stay_on_the_tenant_name(self):
		for page in ("www/hrms-employee.html", "www/hrms-employee-next.html"):
			with open(os.path.join(APP_ROOT, page), encoding="utf-8") as f:
				text = f.read()
			self.assertNotIn("brand_label", text, page)
			self.assertIn("tenant_name", text, page)
		for page in ("www/hrms_employee.py", "www/hrms_employee_next.py"):
			with open(os.path.join(APP_ROOT, page), encoding="utf-8") as f:
				self.assertIn("context.brand_label = org_label(frappe.session.user)", f.read(), page)


class OrgFieldsAlv469(IntegrationTestCase):
	"""The two fields, the two Employment Types, and the copy from DTC's fields."""

	OLD = ("dtc_agency", "dtc_employee_category")

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		_company(COMPANY_B, "A469B")
		cls.ess = _user("ess", "Employee", "Employee Self Service")
		frappe.db.commit()

	def _drop_fields(self, *names):
		for n in names:
			frappe.db.delete("Custom Field", {"dt": "Employee", "fieldname": n})
			frappe.db.delete("Property Setter", {"doc_type": "Employee", "field_name": n})
		frappe.clear_cache(doctype="Employee")

	def _old_fields(self, fieldtype="Select"):
		for n in self.OLD:
			if not frappe.db.exists("Custom Field", {"dt": "Employee", "fieldname": n}):
				frappe.get_doc({"doctype": "Custom Field", "dt": "Employee", "fieldname": n,
				                "label": n, "fieldtype": fieldtype, "insert_after": "employment_type",
				                "options": "\nABR\nMETI" if fieldtype == "Select" else ""}
				               ).insert(ignore_permissions=True)
		frappe.clear_cache(doctype="Employee")

	def tearDown(self):
		frappe.set_user("Administrator")
		self._drop_fields(*self.OLD)
		frappe.db.commit()  # adding a column commits anyway; keep the clean-up too

	def test_alv469_both_fields_and_both_types_exist_and_are_hr_only(self):
		ol.after_migrate()
		meta = frappe.get_meta("Employee")
		for f in (ol.AGENCY_FIELD, ol.CATEGORY_FIELD):
			df = meta.get_field(f)
			self.assertIsNotNone(df, f)
			self.assertEqual(df.fieldtype, "Select")
			self.assertEqual(df.permlevel, 2, f"{f} must be HR only")
		self.assertEqual(meta.get_field(ol.AGENCY_FIELD).depends_on, 'eval:doc.employment_type=="Contract"')
		self.assertFalse(meta.get_field(ol.CATEGORY_FIELD).depends_on)
		for t in ol.OWN_NAME_TYPES:
			self.assertTrue(frappe.db.exists("Employment Type", t), t)

	def test_alv469_an_employee_cannot_write_the_two_new_fields_on_their_own_record(self):
		ol.after_migrate()
		emp = _employee("Ess", self.ess, employment_type="Contract")
		frappe.db.set_value("Employee", emp, {ol.AGENCY_FIELD: None, ol.CATEGORY_FIELD: None})
		frappe.set_user(self.ess)
		doc = frappe.get_doc("Employee", emp)
		doc.update({ol.AGENCY_FIELD: "Sneaky Agency", ol.CATEGORY_FIELD: "Sneaky"})
		try:
			doc.save()
		except frappe.ValidationError:
			pass  # a refusal is as good as a silent skip; what matters is the value
		frappe.set_user("Administrator")
		after = frappe.db.get_value("Employee", emp, [ol.AGENCY_FIELD, ol.CATEGORY_FIELD], as_dict=True)
		self.assertFalse(after[ol.AGENCY_FIELD])
		self.assertFalse(after[ol.CATEGORY_FIELD])

	def test_alv469_creating_the_fields_copies_the_old_choices_and_a_second_run_leaves_site_edits_alone(self):
		self._drop_fields(ol.AGENCY_FIELD, ol.CATEGORY_FIELD)
		self._old_fields()
		ol.after_migrate()
		self.assertEqual(frappe.get_meta("Employee").get_field(ol.AGENCY_FIELD).options, "\nABR\nMETI")
		# HR edits the choices in Customize Form; migrate must not put them back.
		frappe.db.set_value("Custom Field", {"dt": "Employee", "fieldname": ol.AGENCY_FIELD},
		                    "options", "\nGI Staffing")
		frappe.clear_cache(doctype="Employee")
		ol.after_migrate()
		ol.after_migrate()
		self.assertEqual(frappe.get_meta("Employee").get_field(ol.AGENCY_FIELD).options, "\nGI Staffing")

	def test_alv469_a_site_with_no_dtc_fields_gets_empty_choices_and_the_patch_is_a_no_op(self):
		self._drop_fields(ol.AGENCY_FIELD, ol.CATEGORY_FIELD)
		ol.after_migrate()
		self.assertFalse((frappe.get_meta("Employee").get_field(ol.AGENCY_FIELD).options or "").strip())
		copy_patch.execute()  # must not raise
		self.assertFalse(frappe.db.exists("Property Setter", {"doc_type": "Employee", "property": "hidden",
		                                                       "field_name": ["in", list(self.OLD)]}))

	def test_alv469_the_patch_copies_hides_keeps_old_data_and_is_safe_twice(self):
		ol.after_migrate()
		self._old_fields()
		a = _employee("CopyA", _user("copya"), employment_type="Contract")
		b = _employee("CopyB", _user("copyb"), employment_type="Contract")
		c = _employee("CopyC", _user("copyc"))
		frappe.db.set_value("Employee", a, {"dtc_agency": "ABR", "dtc_employee_category": "METI"})
		# b already has a new value: it must not be overwritten
		frappe.db.set_value("Employee", b, {"dtc_agency": "ABR", ol.AGENCY_FIELD: "Kept Agency"})
		frappe.db.set_value("Employee", c, {ol.AGENCY_FIELD: None, "dtc_agency": None})

		copy_patch.execute()
		get = lambda n, f: frappe.db.get_value("Employee", n, f)
		self.assertEqual(get(a, ol.AGENCY_FIELD), "ABR")
		self.assertEqual(get(a, ol.CATEGORY_FIELD), "METI")
		self.assertEqual(get(b, ol.AGENCY_FIELD), "Kept Agency")
		self.assertFalse(get(c, ol.AGENCY_FIELD))
		# old data and old fields stay; the old fields are hidden
		self.assertEqual(get(a, "dtc_agency"), "ABR")
		self.assertEqual(get(a, "dtc_employee_category"), "METI")
		meta = frappe.get_meta("Employee")
		for old in self.OLD:
			self.assertTrue(meta.get_field(old).hidden, old)

		# second run: nothing changes, nothing is overwritten
		frappe.db.set_value("Employee", a, ol.AGENCY_FIELD, "Edited Since")
		copy_patch.execute()
		self.assertEqual(get(a, ol.AGENCY_FIELD), "Edited Since")
		self.assertEqual(get(b, ol.AGENCY_FIELD), "Kept Agency")
		self.assertEqual(get(a, "dtc_agency"), "ABR")

	def test_alv469_the_hooks_and_the_patch_list_carry_it(self):
		from alvoraa_portal import hooks

		self.assertEqual(hooks.after_migrate.count("alvoraa_portal.org_label.after_migrate"), 1)
		self.assertEqual(hooks.after_install.count("alvoraa_portal.org_label.after_migrate"), 1)
		with open(os.path.join(APP_ROOT, "patches.txt")) as f:
			lines = f.read().splitlines()
		self.assertIn("alvoraa_portal.patches.v1_0.alv469_org_fields_from_dtc", lines)
		self.assertIn("alvoraa_portal.patches.v1_0.alv469_email_footer_no_tenant_name", lines)


class GigWorkerPayRowsAlv469(IntegrationTestCase):
	"""Surbhi, 26 Nov 2026 (option A): on DTC a Gig Worker and a Freelancer earn
	no marks and no leave credit. That is two Categories rows in the rule set -
	data, not code. This proves the rows do what she asked, and that without
	them the type falls to the defaults (earns both)."""

	def _rule_set(self, with_rows):
		rs = frappe.new_doc("Alvoraa Payroll Rule Set")
		rs.company = COMPANY_B
		rs.category_field = "employment_type"
		if with_rows:
			for kind in ol.OWN_NAME_TYPES:
				# The same values as DTC's own "Contract" row (dtc_ruleset.json export).
				rs.append("categories", {"category": kind, "grace_minutes": 15, "earns_marks": 0,
				                         "earns_leave_credits": 0, "doubles_deduction": 0,
				                         "late_quarter_after_minutes": 0, "break_allowance_minutes": 0})
		return rs

	def setUp(self):
		frappe.set_user("Administrator")
		_company(COMPANY_B, "A469B")
		for kind in ol.OWN_NAME_TYPES:
			_type(kind)
		self.emp = _employee("Gig", _user("gig"), employment_type="Gig Worker")

	def tearDown(self):
		frappe.db.rollback()

	def test_alv469_gig_worker_row_with_zeros_stops_marks_and_leave_credit(self):
		from alvoraa_portal import leave_rules, payroll_rules_apply as pra

		rs = self._rule_set(with_rows=True)
		flags = pra._employee_flags(self.emp, frappe.utils.getdate("2026-11-10"), pra.prepare(rs))
		self.assertFalse(flags["earns_marks"])
		self.assertFalse(leave_rules.credit_facts(self.emp, rs)["category_earns"])

	def test_alv469_without_the_rows_a_gig_worker_earns_by_default(self):
		from alvoraa_portal import leave_rules, payroll_rules_apply as pra

		rs = self._rule_set(with_rows=False)
		flags = pra._employee_flags(self.emp, frappe.utils.getdate("2026-11-10"), pra.prepare(rs))
		self.assertTrue(flags["earns_marks"])
		self.assertTrue(leave_rules.credit_facts(self.emp, rs)["category_earns"])


class FooterPatchAlv469(IntegrationTestCase):
	"""The footer patch changes the footer text and nothing else."""

	FIELDS = ("email_footer_address", "disable_standard_email_footer")

	def setUp(self):
		self.saved = {f: frappe.db.get_single_value("System Settings", f, cache=False) for f in self.FIELDS}
		if frappe.db.exists("Email Account", "Alv469 Mail"):
			frappe.delete_doc("Email Account", "Alv469 Mail", force=True, ignore_permissions=True)
		frappe.get_doc({"doctype": "Email Account", "email_account_name": "Alv469 Mail",
		                "email_id": "alv469mail@example.com", "enable_incoming": 0,
		                "enable_outgoing": 1, "awaiting_password": 1}).insert(ignore_permissions=True)
		frappe.db.set_value("Email Account", "Alv469 Mail", "brand_logo", "")

	def tearDown(self):
		frappe.delete_doc("Email Account", "Alv469 Mail", force=True, ignore_permissions=True)
		for f, v in self.saved.items():
			frappe.db.set_single_value("System Settings", f, v)
			frappe.db.set_default(f, v)
		frappe.clear_cache()

	def _set(self, footer, flag=0):
		frappe.db.set_single_value("System Settings", "email_footer_address", footer)
		frappe.db.set_single_value("System Settings", "disable_standard_email_footer", flag)

	def _run(self):
		from alvoraa_portal.patches.v1_0 import alv469_email_footer_no_tenant_name as patch_

		patch_.execute()
		return (frappe.db.get_single_value("System Settings", "email_footer_address", cache=False),
		        frappe.utils.cint(frappe.db.get_single_value("System Settings", "disable_standard_email_footer", cache=False)),
		        frappe.db.get_value("Email Account", "Alv469 Mail", "brand_logo"))

	def test_alv469_our_old_footer_loses_the_name_and_the_switch_and_logo_are_left_alone(self):
		self._set("Old Co Ltd\nPowered by AllAboutHR", flag=0)
		footer, flag, logo = self._run()
		self.assertEqual(footer, "Powered by AllAboutHR")
		self.assertEqual(flag, 0, "the standard-footer switch must not be reset")
		self.assertFalse(logo, "a logo that was removed must not come back")

	def test_alv469_a_handwritten_or_empty_footer_is_left_alone(self):
		for text in ("Acme Pvt Ltd, 12 MG Road", ""):
			self._set(text)
			footer, flag, logo = self._run()
			self.assertEqual(footer or "", text)
			self.assertEqual(flag, 0)
			self.assertFalse(logo)

	def test_alv469_running_the_footer_patch_twice_changes_nothing_more(self):
		self._set("Old Co Ltd\nPowered by AllAboutHR")
		self._run()
		self.assertEqual(self._run()[0], "Powered by AllAboutHR")
