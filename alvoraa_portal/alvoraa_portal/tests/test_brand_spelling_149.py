"""ALV-149 and ALV-153: "Alvora" wherever a person reads the product's name.

Each test names what it keeps alive, so a merge that drops one of these fails
CI instead of a customer noticing.
"""

import os

import frappe
from frappe.tests.utils import FrappeTestCase

import alvoraa_portal
from alvoraa_portal import brand_text

APP_DIR = os.path.dirname(os.path.abspath(alvoraa_portal.__file__))
REPO = os.path.dirname(os.path.dirname(APP_DIR))


def _single(doctype, field):
	return frappe.db.get_single_value(doctype, field, cache=False)


class TestDeskLabelsSayAlvora(FrappeTestCase):
	def test_alv149_english_translation_turns_every_brand_name(self):
		"""Frappe 16 applies translations/en.csv for English; the desk draws
		doctype, module and workspace names through __()."""
		from frappe.translate import clear_cache, get_all_translations

		clear_cache()
		en = get_all_translations("en")
		for name in ("Alvoraa Position", "Alvoraa Subscription", "Alvoraa HR Core",
		             "Alvoraa Portal", "Alvoraa Goals", "Alvoraa Pricing Settings"):
			self.assertEqual(en.get(name), name.replace("Alvoraa", "Alvora"), name)

	def test_alv149_python_messages_translate_a_doctype_name(self):
		self.assertEqual(frappe._("Alvoraa Position", lang="en"), "Alvora Position")

	def test_alv149_app_titles(self):
		self.assertEqual(frappe.get_hooks("app_title", app_name="alvoraa_portal"), ["Alvora HRMS"])
		self.assertEqual(frappe.get_hooks("app_title", app_name="alvoraa_goals"), ["Alvora Goals"])


class TestTenantBrandText(FrappeTestCase):
	"""D5: exact old defaults become "Alvora HRMS"; anything typed is left."""

	FIELDS = (("Website Settings", "app_name"), ("System Settings", "app_name"),
	          ("Website Settings", "copyright"), ("Website Settings", "footer_powered"))

	def setUp(self):
		self.saved = {f: _single(*f) for f in self.FIELDS}
		self.help_hidden = frappe.db.get_value(
			"Navbar Item", {"parent": "Navbar Settings", "parentfield": "help_dropdown",
			                "item_label": "Frappe Support"}, "hidden")

	def tearDown(self):
		for (doctype, field), value in self.saved.items():
			frappe.db.set_single_value(doctype, field, value)
		if self.help_hidden is not None:
			frappe.db.set_value("Navbar Item", {"parent": "Navbar Settings",
			                                    "parentfield": "help_dropdown",
			                                    "item_label": "Frappe Support"},
			                    "hidden", self.help_hidden)
		for name in ("Alvora", "Alvoraa", "Alvoraa Payroll Desk"):
			if frappe.db.exists("Email Account", name):
				frappe.delete_doc("Email Account", name, force=True, ignore_permissions=True)
		frappe.clear_cache()

	def test_alv149_frappe_defaults_become_alvora_hrms(self):
		frappe.db.set_single_value("Website Settings", "app_name", "Frappe")
		frappe.db.set_single_value("System Settings", "app_name", "ERPNext")
		result = brand_text.apply()
		self.assertEqual(_single("Website Settings", "app_name"), "Alvora HRMS")
		self.assertEqual(_single("System Settings", "app_name"), "Alvora HRMS")
		self.assertEqual(result["failed"], [])

	def test_alv149_a_value_the_tenant_typed_survives(self):
		frappe.db.set_single_value("Website Settings", "app_name", "Acme People")
		frappe.db.set_single_value("Website Settings", "copyright", "Acme Ltd, built on Alvoraa")
		result = brand_text.apply()
		self.assertEqual(_single("Website Settings", "app_name"), "Acme People")
		self.assertEqual(_single("Website Settings", "copyright"), "Acme Ltd, built on Alvoraa")
		self.assertIn("Website Settings.app_name", result["left_alone"])

	def test_alv149_exact_old_text_is_respelled(self):
		frappe.db.set_single_value("Website Settings", "copyright", "© Alvoraa")
		frappe.db.set_single_value("Website Settings", "footer_powered", "Powered by Alvoraa")
		brand_text.apply()
		self.assertEqual(_single("Website Settings", "copyright"), "© Alvora")
		self.assertEqual(_single("Website Settings", "footer_powered"), "Powered by Alvora")

	def test_alv149_safe_to_run_twice(self):
		frappe.db.set_single_value("Website Settings", "app_name", "Frappe")
		brand_text.apply()
		second = brand_text.apply()
		self.assertEqual(second["changed"], [])
		self.assertEqual(_single("Website Settings", "app_name"), "Alvora HRMS")

	def test_alv149_frappe_support_is_hidden_from_the_help_menu(self):
		if self.help_hidden is None:
			self.skipTest("this site has no Frappe Support help item")
		frappe.db.set_value("Navbar Item", {"parent": "Navbar Settings",
		                                    "parentfield": "help_dropdown",
		                                    "item_label": "Frappe Support"}, "hidden", 0)
		brand_text.apply()
		self.assertEqual(frappe.db.get_value(
			"Navbar Item", {"parent": "Navbar Settings", "parentfield": "help_dropdown",
			                "item_label": "Frappe Support"}, "hidden"), 1)

	def _email_account(self, name):
		frappe.get_doc({"doctype": "Email Account", "email_account_name": name,
		                "email_id": frappe.scrub(name).replace("_", "") + "149@example.com",
		                "enable_incoming": 0, "enable_outgoing": 0,
		                "awaiting_password": 1}).insert(ignore_permissions=True)

	def test_alv149_email_account_from_name_is_respelled_only_when_exact(self):
		self._email_account("Alvoraa")
		self._email_account("Alvoraa Payroll Desk")
		plan = {r["current"]: r for r in brand_text.plan()
		        if r["setting"].startswith("Email Account")}
		self.assertEqual(plan["Alvoraa"]["action"], "change")
		self.assertEqual(plan["Alvoraa"]["proposed"], "Alvora")
		self.assertEqual(plan["Alvoraa Payroll Desk"]["action"], "leave")
		brand_text.apply()
		self.assertTrue(frappe.db.exists("Email Account", "Alvora"))
		self.assertFalse(frappe.db.exists("Email Account", "Alvoraa"))
		self.assertTrue(frappe.db.exists("Email Account", "Alvoraa Payroll Desk"))

	def test_alv149_dry_run_script_uses_the_same_rules(self):
		"""The list Surbhi reads must be the list the patch applies."""
		path = os.path.join(REPO, "scripts", "brand_text_dry_run.sh")
		if not os.path.exists(path):
			self.skipTest("scripts/ is not on this bench")
		with open(path, encoding="utf-8") as f:
			sql = f.read()
		for value in brand_text.APP_NAME_DEFAULTS + brand_text.TEXT_DEFAULTS \
				+ brand_text.EMAIL_ACCOUNT_DEFAULTS + brand_text.HELP_ITEMS_TO_HIDE:
			self.assertIn(f"'{value}'", sql, value)
		for field in brand_text.TEXT_FIELDS:
			self.assertIn(f"'{field}'", sql, field)
		self.assertIn(brand_text.PRODUCT_NAME, sql)
		self.assertNotRegex(sql.upper(), r"\b(UPDATE|DELETE|INSERT|ALTER|DROP)\b\s")

	def test_alv149_new_tenants_get_the_name_at_install(self):
		self.assertIn("alvoraa_portal.brand_text.after_install",
		              frappe.get_hooks("after_install", app_name="alvoraa_portal"))


class TestPortalAvatarMenuHasOneDoorToTheDesk(FrappeTestCase):
	def test_alv153_portal_hides_frappe_desk_links(self):
		"""Frappe's "Apps" (/apps -> /desk) and "Switch To Desk" (/desk) are one
		screen twice; the portal's own sidebar switch is the door."""
		with open(os.path.join(APP_DIR, "public", "css", "ess", "frame.css"), encoding="utf-8") as f:
			css = f.read()
		self.assertIn("#website-post-login .switch-to-desk", css)
		self.assertIn("#website-post-login .apps{display:none !important}", css)

	def test_alv153_frappe_still_names_those_links_the_same_way(self):
		"""Pins the Frappe markup the rule targets."""
		path = os.path.join(os.path.dirname(os.path.abspath(frappe.__file__)),
		                    "templates", "includes", "navbar", "navbar_login.html")
		if not os.path.exists(path):
			self.skipTest("navbar_login.html not found")
		with open(path, encoding="utf-8") as f:
			html = f.read()
		self.assertIn('id="website-post-login"', html)
		self.assertIn("switch-to-desk", html)
		self.assertIn('class="dropdown-item apps', html)
