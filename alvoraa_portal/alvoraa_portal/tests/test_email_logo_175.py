"""ALV-175: the email header logo when no outgoing Email Account exists.

Each test names what it keeps alive, so a merge that drops one of these fails
CI instead of a customer noticing (parallel-work.md section 7).
"""

import os

import frappe
from frappe.tests.utils import FrappeTestCase

import alvoraa_portal
from alvoraa_portal import brand, email_brand

APP_DIR = os.path.dirname(os.path.abspath(alvoraa_portal.__file__))
REPO = os.path.dirname(os.path.dirname(APP_DIR))


class TestResolveHeaderLogo(FrappeTestCase):
	"""The pure function - no email involved, so no rendering needed to pin
	the "ours or theirs" rule itself."""

	def test_alv175_none_becomes_the_absolute_lockup(self):
		self.assertTrue(email_brand.resolve_header_logo(None).startswith("http"))
		self.assertTrue(email_brand.resolve_header_logo(None).endswith("alvoraa-logo.png"))

	def test_alv175_empty_string_becomes_the_absolute_lockup(self):
		self.assertTrue(email_brand.resolve_header_logo("").endswith("alvoraa-logo.png"))

	def test_alv175_the_relative_mark_becomes_the_absolute_lockup(self):
		"""The real shape of the ALV-175 bug: Website Settings.app_logo, the
		fallback when no outgoing account resolves, holds the relative mark -
		truthy, so Frappe's own template would try to load it and fail."""
		result = email_brand.resolve_header_logo(brand.MARK)
		self.assertTrue(result.startswith("http"))
		self.assertTrue(result.endswith("alvoraa-logo.png"))

	def test_alv175_our_own_absolute_logo_stays_the_logo(self):
		already = frappe.utils.get_url() + brand.LOGO
		self.assertEqual(email_brand.resolve_header_logo(already), already)

	def test_alv175_a_tenants_own_deliberate_logo_is_never_touched(self):
		"""A tenant's own Email Account.brand_logo, or a custom Website
		Settings.app_logo - anything that is not one of our own asset paths."""
		theirs = "https://acme.example.com/files/acme-logo.png"
		self.assertEqual(email_brand.resolve_header_logo(theirs), theirs)


class TestJinjaHookRegistered(FrappeTestCase):
	def test_alv175_resolve_header_logo_is_a_jinja_method(self):
		methods = frappe.get_hooks("jinja", app_name="alvoraa_portal").get("methods", [])
		self.assertIn("alvoraa_portal.email_brand.resolve_header_logo", methods)


class TestOurTemplateWinsTheSearch(FrappeTestCase):
	"""Frappe's Jinja loader searches installed apps in REVERSED install order
	(frappe/utils/jinja.py:_get_jloader). frappe is always the very first app
	on any site - not a provisioning choice that could get this wrong - so
	our copy, installed after it, is always found first. Proven by asking
	Jinja which file it actually resolved, not by reading the source and
	assuming."""

	def test_alv175_standard_html_resolves_to_our_own_copy(self):
		from frappe.utils.jinja import get_jenv

		tpl = get_jenv().get_template("templates/emails/standard.html")
		self.assertIsNotNone(tpl.filename)
		self.assertIn(os.sep.join(("alvoraa_portal", "alvoraa_portal", "templates",
		                          "emails", "standard.html")), tpl.filename)
		self.assertNotIn(os.sep.join(("apps", "frappe", "frappe", "templates",
		                              "emails", "standard.html")), tpl.filename)


class TestRenderedHeaderHasTheLockupWithNoOutgoingAccount(FrappeTestCase):
	"""Renders through the real pipeline with NO outgoing Email Account passed
	- the exact shape of the Sargam bug (mail resolving to the server's
	virtual "Notifications" account, which has no brand_logo field at all)."""

	def setUp(self):
		email_brand.apply()
		from alvoraa_portal import brand_text

		brand_text.apply()
		frappe.clear_cache()

	def test_alv175_the_header_logo_is_the_absolute_lockup_with_no_account(self):
		from frappe.email.email_body import get_formatted_html

		html = get_formatted_html(subject="Test", message="<p>Hello</p>",
		                          with_container=True, header="A header")
		self.assertIn('src="http', html)
		self.assertIn("alvoraa-logo.png", html)
		self.assertNotIn("alvoraa-mark.png", html)
		self.assertNotIn("frappe-framework-logo", html)

	def test_alv175_a_tenants_deliberate_account_logo_still_wins(self):
		"""If a tenant DID set their own logo on the sending account, this
		override must not paper over their choice."""
		from frappe.email.email_body import get_formatted_html

		name = "Alv175 Deliberate Logo"
		if not frappe.db.exists("Email Account", name):
			frappe.get_doc({"doctype": "Email Account", "email_account_name": name,
			                "email_id": "alv175deliberate@example.com",
			                "enable_incoming": 0, "enable_outgoing": 1,
			                "awaiting_password": 1}).insert(ignore_permissions=True)
		theirs = "https://acme.example.com/files/acme-logo.png"
		frappe.db.set_value("Email Account", name, "brand_logo", theirs)
		try:
			acc = frappe.get_doc("Email Account", name)
			html = get_formatted_html(subject="Test", message="<p>Hello</p>",
			                          with_container=True, header="A header",
			                          email_account=acc)
			self.assertIn(theirs, html)
			self.assertNotIn("alvoraa-logo.png", html)
		finally:
			frappe.delete_doc("Email Account", name, force=True, ignore_permissions=True)


class TestUpstreamShapeGuard(FrappeTestCase):
	def test_alv175_the_declared_hash_is_present_and_well_formed(self):
		path = os.path.join(APP_DIR, "templates", "emails", "standard.html")
		with open(path, encoding="utf-8") as f:
			text = f.read()
		self.assertRegex(
			text,
			r"sha256\s+of\s+the\s+unmodified\s+frappe/frappe/templates/emails/"
			r"standard\.html\s+this\s+file\s+was\s+copied\s+from\s*"
			r"\([^)]*\):\s*[0-9a-f]{64}")

	def test_alv175_check_upstream_shape_script_exists_and_is_wired_into_ci(self):
		script = os.path.join(REPO, "scripts", "check_email_template_overrides.py")
		if not os.path.exists(script):
			self.skipTest("scripts/ is not on this bench")
		with open(script, encoding="utf-8") as f:
			self.assertIn("--check-upstream-shape", f.read())
		ci = os.path.join(REPO, ".github", "workflows", "ci.yml")
		with open(ci, encoding="utf-8") as f:
			self.assertIn("check_email_template_overrides.py --check-upstream-shape", f.read())
