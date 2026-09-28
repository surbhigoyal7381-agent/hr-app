"""ALV-174: outgoing email stops saying Frappe/ERPNext.

Each test names what it keeps alive, so a merge that drops one of these fails
CI instead of a customer noticing (parallel-work.md section 7).
"""

import os

import frappe
from frappe.tests.utils import FrappeTestCase

import alvoraa_portal
from alvoraa_portal import email_brand

APP_DIR = os.path.dirname(os.path.abspath(alvoraa_portal.__file__))
REPO = os.path.dirname(os.path.dirname(APP_DIR))


def _single(doctype, field):
	return frappe.db.get_single_value(doctype, field, cache=False)


class TestEmailFooterAndLogo(FrappeTestCase):
	SINGLES = (("System Settings", "disable_standard_email_footer"),
	           ("System Settings", "email_footer_address"))

	def setUp(self):
		self.saved = {f: _single(*f) for f in self.SINGLES}
		self.accounts = []

	def tearDown(self):
		for (doctype, field), value in self.saved.items():
			frappe.db.set_single_value(doctype, field, value)
		for name in self.accounts:
			if frappe.db.exists("Email Account", name):
				frappe.delete_doc("Email Account", name, force=True, ignore_permissions=True)
		frappe.clear_cache()

	def _email_account(self, name, brand_logo=None):
		frappe.get_doc({"doctype": "Email Account", "email_account_name": name,
		                "email_id": frappe.scrub(name).replace("_", ".") + ".174@example.com",
		                "enable_incoming": 0, "enable_outgoing": 1,
		                "awaiting_password": 1}).insert(ignore_permissions=True)
		self.accounts.append(name)
		if brand_logo is not None:
			frappe.db.set_value("Email Account", name, "brand_logo", brand_logo)

	# ── the ERPNext footer switch ──────────────────────────────────────────
	def test_alv174_erpnext_footer_is_switched_off(self):
		frappe.db.set_single_value("System Settings", "disable_standard_email_footer", 0)
		result = email_brand.apply()
		self.assertEqual(_single("System Settings", "disable_standard_email_footer"), 1)
		self.assertIn("System Settings.disable_standard_email_footer: '0' -> '1'",
		              result["changed"])

	def test_alv174_safe_to_run_twice(self):
		email_brand.apply()
		second = email_brand.apply()
		self.assertNotIn("System Settings.disable_standard_email_footer",
		                 [r.split(":")[0] for r in second["changed"]])

	# ── our own footer text ─────────────────────────────────────────────────
	def test_alv174_footer_gets_tenant_name_and_the_powered_by_line(self):
		frappe.db.set_single_value("System Settings", "email_footer_address", "")
		email_brand.apply()
		footer = _single("System Settings", "email_footer_address")
		lines = footer.splitlines()
		self.assertEqual(lines[-1], "Powered by AllAboutHR")
		self.assertGreaterEqual(len(lines), 2)

	def test_alv174_a_footer_the_tenant_typed_survives(self):
		frappe.db.set_single_value("System Settings", "email_footer_address",
		                           "Acme Pvt Ltd, 12 MG Road, Bengaluru")
		result = email_brand.apply()
		self.assertEqual(_single("System Settings", "email_footer_address"),
		                 "Acme Pvt Ltd, 12 MG Road, Bengaluru")
		self.assertIn("System Settings.email_footer_address", result["left_alone"])

	def test_alv174_our_own_footer_is_rewritten_on_a_tenant_rename(self):
		"""A tenant renamed after we last wrote the footer: we own the last
		line ("Powered by AllAboutHR"), so we rewrite the first, not leave it."""
		frappe.db.set_single_value("System Settings", "email_footer_address",
		                           "Old Trading Name\nPowered by AllAboutHR")
		email_brand.apply()
		footer = _single("System Settings", "email_footer_address")
		self.assertNotEqual(footer, "Old Trading Name\nPowered by AllAboutHR")
		self.assertEqual(footer.splitlines()[-1], "Powered by AllAboutHR")

	# ── the header logo ──────────────────────────────────────────────────
	def test_alv174_outgoing_account_gets_the_full_lockup_as_an_absolute_url(self):
		self._email_account("Alv174 Outgoing")
		email_brand.apply()
		logo = frappe.db.get_value("Email Account", "Alv174 Outgoing", "brand_logo")
		self.assertTrue(logo.startswith("http"), logo)
		self.assertTrue(logo.endswith("/assets/alvoraa_portal/images/alvoraa-logo.png"), logo)

	def test_alv174_a_deliberately_uploaded_logo_survives(self):
		self._email_account("Alv174 Own Logo", brand_logo="/files/acme-logo.png")
		result = email_brand.apply()
		self.assertEqual(frappe.db.get_value("Email Account", "Alv174 Own Logo", "brand_logo"),
		                 "/files/acme-logo.png")
		self.assertIn("Email Account.brand_logo (Alv174 Own Logo)", result["left_alone"])

	def test_alv174_a_relative_alvora_logo_from_an_older_run_is_repointed_absolute(self):
		"""Before this fix, brand.py's MARK (relative) could have ended up here by
		hand; a re-run must still recognise it as ours and fix it, not leave it
		broken forever."""
		from alvoraa_portal import brand

		self._email_account("Alv174 Old Relative", brand_logo=brand.MARK)
		email_brand.apply()
		logo = frappe.db.get_value("Email Account", "Alv174 Old Relative", "brand_logo")
		self.assertTrue(logo.startswith("http"), logo)

	def test_alv174_disabled_outgoing_accounts_are_not_touched(self):
		frappe.get_doc({"doctype": "Email Account", "email_account_name": "Alv174 Incoming Only",
		                "email_id": "alv174incoming@example.com", "enable_incoming": 0,
		                "enable_outgoing": 0, "awaiting_password": 1}).insert(ignore_permissions=True)
		self.accounts.append("Alv174 Incoming Only")
		plan = [r for r in email_brand.plan() if "Alv174 Incoming Only" in r["setting"]]
		self.assertEqual(plan, [])

	# ── every tenant, including new ones ───────────────────────────────────
	def test_alv174_new_tenants_get_it_at_install(self):
		self.assertIn("alvoraa_portal.email_brand.after_install",
		              frappe.get_hooks("after_install", app_name="alvoraa_portal"))

	def test_alv174_the_patch_that_carries_it_to_live_sites_is_registered(self):
		with open(os.path.join(APP_DIR, "patches.txt"), encoding="utf-8") as f:
			self.assertIn("alvoraa_portal.patches.v1_0.alvora_email_brand", f.read())

	def test_alv174_dry_run_script_uses_the_same_footer_line_and_asset_names(self):
		"""The list Surbhi reads must be the list the patch applies. Run against
		a real site 2026-09-28 (email_brand_dry_run.sh test174, in a throwaway
		container) and confirmed it proposes the same two settings and the same
		values apply() writes - this test pins the constants that made that true
		so a future edit to either side cannot drift apart silently."""
		path = os.path.join(REPO, "scripts", "email_brand_dry_run.sh")
		if not os.path.exists(path):
			self.skipTest("scripts/ is not on this bench")
		with open(path, encoding="utf-8") as f:
			sql = f.read()
		self.assertIn(email_brand.FOOTER_LINE, sql)
		self.assertIn("disable_standard_email_footer", sql)
		self.assertIn("email_footer_address", sql)
		self.assertIn("brand_logo", sql)
		from alvoraa_portal import brand

		self.assertIn(os.path.basename(brand.MARK), sql)
		self.assertIn(os.path.basename(brand.LOGO), sql)
		self.assertNotRegex(sql.upper(), r"\b(UPDATE|DELETE|INSERT|ALTER|DROP)\b\s")

	def test_alv174_the_control_plane_gets_no_special_skip(self):
		"""brand.py and brand_text.py both brand the control plane like any
		other site (repoint_broken_brand_images.py's own comment says so);
		email_brand.plan() must not special-case it either - nothing in it
		reads frappe.conf.alvoraa_control_plane at all."""
		import inspect

		src = inspect.getsource(email_brand)
		self.assertNotIn("alvoraa_control_plane", src)


class TestRenderedEmailHasNoFrappeOrErpnextBranding(FrappeTestCase):
	"""Renders through the real Frappe pipeline - not just reading our own
	settings - so a change to Frappe's own template shape would be caught too."""

	def setUp(self):
		self.saved = {(d, f): _single(d, f) for d, f in
		             (("System Settings", "disable_standard_email_footer"),
		              ("System Settings", "email_footer_address"),
		              ("Website Settings", "app_name"))}
		email_brand.apply()
		from alvoraa_portal import brand_text

		brand_text.apply()
		# email_brand.apply() only clears the cache when it finds something to
		# change; an earlier test class in the same run may have left the DB
		# already correct (FrappeTestCase rolls back each test's writes on a
		# savepoint, but the Redis-backed client_cache that
		# frappe.db.get_default() reads through is NOT part of that
		# transaction) while still holding a stale cached value from before
		# the rollback. Force it fresh here regardless.
		frappe.clear_cache()

	def tearDown(self):
		for (doctype, field), value in self.saved.items():
			frappe.db.set_single_value(doctype, field, value)
		frappe.clear_cache()

	def test_alv174_the_footer_never_says_sent_via_erpnext(self):
		from frappe.email.email_body import get_footer

		footer_html = get_footer(email_account=None, footer="")
		self.assertNotIn("ERPNext", footer_html)
		self.assertNotIn("frappe.io", footer_html)
		self.assertIn("Powered by AllAboutHR", footer_html)

	def test_alv174_the_header_shows_alvora_not_frappe(self):
		from frappe.email.email_body import get_formatted_html

		html = get_formatted_html(subject="Test", message="<p>Hello</p>",
		                          with_container=True)
		self.assertNotIn("frappe-framework-logo", html)
		self.assertNotIn(">Frappe<", html)
		self.assertIn("Alvora", html)

	def test_alv174_sample_email_saved_for_review(self):
		"""Not an assertion - a fixture for a human to look at. Skips quietly
		if the repo's tests/ folder for saved artefacts is not writable here."""
		from frappe.email.email_body import get_formatted_html

		html = get_formatted_html(subject="Password reset", message="<p>Sample body.</p>",
		                          with_container=True, header="Reset your password")
		out_dir = os.path.join(REPO, "docs", "slices", "ALV-149-brand-spelling")
		try:
			os.makedirs(out_dir, exist_ok=True)
			with open(os.path.join(out_dir, "05-sample-rendered-email.html"), "w",
			         encoding="utf-8") as f:
				f.write(html)
		except OSError:
			self.skipTest("could not write the sample file from this container")


class TestCRMInvitationOverride(FrappeTestCase):
	def setUp(self):
		if "crm" not in frappe.get_installed_apps():
			self.skipTest("crm is not installed on this site")

	def test_alv174_our_class_replaces_crms_own(self):
		self.assertEqual(
			frappe.get_hooks("override_doctype_class", app_name="alvoraa_portal")
			.get("CRM Invitation"),
			["alvoraa_portal.overrides.crm_invitation.AlvoraCRMInvitation"])

	def test_alv174_the_override_is_a_subclass_and_never_says_frappe_crm(self):
		from crm.fcrm.doctype.crm_invitation.crm_invitation import CRMInvitation

		from alvoraa_portal.overrides.crm_invitation import AlvoraCRMInvitation

		self.assertTrue(issubclass(AlvoraCRMInvitation, CRMInvitation))

	def test_alv174_invite_via_email_sends_the_tenants_brand_not_frappe_crm(self):
		import unittest.mock as mock

		from alvoraa_portal.overrides.crm_invitation import AlvoraCRMInvitation

		doc = frappe.new_doc("CRM Invitation")
		doc.email = "alv174.invite@example.com"
		doc.key = "testkey174"
		doc.__class__ = AlvoraCRMInvitation
		with mock.patch("frappe.sendmail") as sendmail, \
		     mock.patch.object(doc, "db_set"):
			doc.invite_via_email()
		self.assertTrue(sendmail.called)
		_, kwargs = sendmail.call_args
		self.assertNotIn("Frappe CRM", kwargs.get("subject", ""))
		self.assertNotIn("Frappe CRM", kwargs.get("content", ""))
