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
				+ brand_text.EMAIL_ACCOUNT_DEFAULTS + brand_text.HELP_ITEMS_TO_HIDE \
				+ tuple(brand_text.NAMED_EMAIL_RENAMES):
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


class TestTheAlvoraArtwork(FrappeTestCase):
	def test_alv149_splash_shows_the_lockup_banner_keeps_the_mark(self):
		"""The desk splash has 200 px for the ALVORA wordmark; the website navbar
		caps its banner at 22 px high, where only the mark reads."""
		from alvoraa_portal import brand

		slots = {(d, f): want for d, f, want in brand.SLOTS}
		self.assertEqual(slots[("Website Settings", "splash_image")], brand.LOGO)
		self.assertEqual(slots[("Website Settings", "banner_image")], brand.MARK)

	def test_alv149_the_patch_that_carries_it_to_live_sites_is_registered(self):
		with open(os.path.join(APP_DIR, "patches.txt"), encoding="utf-8") as f:
			self.assertIn("alvoraa_portal.patches.v1_0.alvora_splash_lockup", f.read())


def _dry_run_sql():
	"""The SELECT from scripts/brand_text_dry_run.sh, exactly as Surbhi runs it."""
	path = os.path.join(REPO, "scripts", "brand_text_dry_run.sh")
	with open(path, encoding="utf-8") as f:
		text = f.read()
	start = text.index("read -r -d '' SQL <<'SQL' || true\n") + len("read -r -d '' SQL <<'SQL' || true\n")
	return text[start:text.index("\nSQL\n", start)]


class TestTheDryRunListsWhatThePatchesDo(FrappeTestCase):
	"""Review P3: the list Surbhi approves must be the list that runs.

	MariaDB's default collation says 'frappe' = 'Frappe' = 'Frappe ', and the
	patch (Python) does not. So the site here holds near misses on purpose, and
	the dry-run's "change" rows must equal what brand_text, brand and the navbar
	patch would actually change - no more, no fewer.
	"""

	SINGLES = (("Website Settings", "app_name"), ("System Settings", "app_name"),
	           ("Website Settings", "copyright"), ("Website Settings", "footer_powered"),
	           ("Website Settings", "splash_image"), ("Website Settings", "favicon"))
	ACCOUNTS = ("alvoraa", "Alvoraa HR", "Alvora HR", "Alvoraa HRMS", "Alvoraa HR Admin",
	            "Alvora HRMS", "Alvora HR Admin")

	def setUp(self):
		if not os.path.exists(os.path.join(REPO, "scripts", "brand_text_dry_run.sh")):
			self.skipTest("scripts/ is not on this bench")
		self.saved = {f: _single(*f) for f in self.SINGLES}
		self.addCleanup(self._restore)
		frappe.db.set_single_value("Website Settings", "app_name", "frappe")          # wrong case
		frappe.db.set_single_value("System Settings", "app_name", "ERPNext ")         # trailing space
		frappe.db.set_single_value("Website Settings", "copyright", "© Alvoraa ")      # trailing space
		frappe.db.set_single_value("Website Settings", "footer_powered", "Powered by Alvoraa")  # exact
		frappe.db.set_single_value("Website Settings", "splash_image", "/ASSETS/alvoraa_portal/images/x.png")
		frappe.db.set_single_value("Website Settings", "favicon", "/private/files/f.png")
		for name in self.ACCOUNTS[:5]:
			if not frappe.db.exists("Email Account", name):
				frappe.get_doc({"doctype": "Email Account", "email_account_name": name,
				                "email_id": frappe.scrub(name).replace("_", ".") + ".dry149@example.com",
				                "enable_incoming": 0, "enable_outgoing": 0,
				                "awaiting_password": 1}).insert(ignore_permissions=True)

	def _restore(self):
		for (doctype, field), value in self.saved.items():
			frappe.db.set_single_value(doctype, field, value)
		for name in self.ACCOUNTS:
			if frappe.db.exists("Email Account", name):
				frappe.delete_doc("Email Account", name, force=True, ignore_permissions=True)
		frappe.local.conf.pop("alvoraa_control_plane", None)
		frappe.clear_cache()

	def _sql_changes(self, control_plane):
		frappe.db.sql("SET @alvoraa_cp = %s", (1 if control_plane else 0,))
		rows = frappe.db.sql(_dry_run_sql())
		return {(r[1], r[3]) for r in rows if r[0] == "change"}

	def _patch_changes(self):
		from alvoraa_portal import brand, module_access

		out = {(r["setting"], r["proposed"]) for r in brand_text.plan() if r["action"] == "change"}
		for doctype, field, want in brand.SLOTS:
			current = frappe.db.get_single_value(doctype, field, cache=False)
			verdict = brand._verdict(current)
			if verdict and not (verdict == "ours" and current == want):
				out.add((f"{doctype}.{field} (patch alvora_splash_lockup)", want))
		row = next((r for r in frappe.get_doc("Navbar Settings").settings_dropdown
		            if r.item_label == module_access.NAVBAR_LABEL), None)
		if row and not (row.item_type == "Action" and row.action == module_access.NAVBAR_ACTION
		                and not row.route):
			out.add(("Desk menu: Switch to Employee Portal (ALV-152)",
			         "Action " + module_access.NAVBAR_ACTION))
		return out

	def test_review_p3_dry_run_equals_the_patches_on_near_miss_values(self):
		sql, patch = self._sql_changes(False), self._patch_changes()
		self.assertEqual(sql, patch)
		# and the near misses are really left alone, the exact ones really change
		settings = {s for s, _ in sql}
		self.assertNotIn("Website Settings.app_name", settings)
		self.assertNotIn("System Settings.app_name", settings)
		self.assertNotIn("Website Settings.copyright", settings)
		self.assertIn(("Website Settings.footer_powered", "Powered by Alvora"), sql)
		self.assertIn(("Email Account (From name)", "Alvora HRMS"), sql)
		self.assertNotIn(("Email Account (From name)", "alvora"), sql)
		self.assertNotIn(("Email Account (From name)", "Alvora HR"), sql, "the new name exists")
		self.assertIn(("Email Account (From name)", "Alvora HR Admin"), sql, "Surbhi's named rename")

	def test_review_p3_control_plane_renames_only_the_named_account(self):
		frappe.local.conf["alvoraa_control_plane"] = 1
		sql, patch = self._sql_changes(True), self._patch_changes()
		self.assertEqual(sql, patch)
		# only the account Surbhi named is renamed on the control plane
		self.assertEqual([s for s in sql if s[0].startswith("Email Account")],
		                 [("Email Account (From name)", "Alvora HR Admin")])


class TestTheNamedSendingAccount(FrappeTestCase):
	"""Surbhi, 27 Sep 2026: alvoraa.co's sending account "Alvoraa HR Admin" is
	renamed "Alvora HR Admin" - by Frappe's own rename, so links follow - on the
	control plane too, and never over an account that already has the new name."""

	OLD, NEW = "Alvoraa HR Admin", "Alvora HR Admin"

	def _account(self, name):
		frappe.get_doc({"doctype": "Email Account", "email_account_name": name,
		                "email_id": frappe.scrub(name).replace("_", ".") + ".named149@example.com",
		                "enable_incoming": 0, "enable_outgoing": 0,
		                "awaiting_password": 1}).insert(ignore_permissions=True)

	def tearDown(self):
		for name in (self.OLD, self.NEW):
			if frappe.db.exists("Email Account", name):
				frappe.delete_doc("Email Account", name, force=True, ignore_permissions=True)
		frappe.local.conf.pop("alvoraa_control_plane", None)

	def test_alv149_named_account_is_renamed_on_the_control_plane(self):
		frappe.local.conf["alvoraa_control_plane"] = 1
		self._account(self.OLD)
		result = brand_text.apply()
		self.assertEqual(result["failed"], [])
		self.assertTrue(frappe.db.exists("Email Account", self.NEW))
		self.assertFalse(frappe.db.exists("Email Account", self.OLD))
		self.assertEqual(frappe.db.get_value("Email Account", self.NEW, "email_account_name"), self.NEW)

	def test_alv149_named_account_is_left_when_the_new_name_exists(self):
		self._account(self.OLD)
		self._account(self.NEW)
		plan = {r["current"]: r for r in brand_text.plan() if r["setting"].startswith("Email Account")}
		self.assertEqual(plan[self.OLD]["action"], "leave")
		brand_text.apply()
		self.assertTrue(frappe.db.exists("Email Account", self.OLD))
