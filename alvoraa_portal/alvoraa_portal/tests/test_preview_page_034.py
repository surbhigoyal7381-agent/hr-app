"""Slice 034, SEC-1 / W1D-15: the preview page's two locks.

`/hrms-employee-next` must not exist on production. Not "be refused on
production" - **not exist**. The difference matters: a 403 tells a stranger the
page is there and that somebody can open it; a 404 tells them nothing.

So the page has two locks and this file tests them in that order:

- **AC-74, the one that removed residual risk R5.** With `portal_preview`
  absent, a **System Manager** gets 404. The flag is read BEFORE the role, which
  is what makes the role check the second of two locks rather than the only one.
  There is also a check that reads the repository: no production config file and
  no production compose environment sets the flag, which is why the page cannot
  appear on production at all.
- **AC-40.** With the flag set: System Manager gets the page, every other
  signed-in persona gets 403, and Guest is redirected to the login page.
- **AC-65 / OPS-12.** `no_cache` is set and the page is not in the sitemap.

The status codes are asserted from the exception classes Frappe maps them
through (`frappe/exceptions.py`, v16.33.1: `DoesNotExistError` is 404,
`PermissionError` is 403), because `get_context` is where both decisions are
made. A pass over real HTTP is still worth doing once on the bench; it is
recorded as owed rather than claimed here.

Synthetic people only, tagged S034.
"""

import io
import os

import frappe
from frappe.tests.utils import FrappeTestCase

import alvoraa_portal
from alvoraa_portal.tests.leave_fixtures import ensure_user
from alvoraa_portal.www import hrms_employee_next as page


class _PreviewBase(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.sysman = ensure_user("s034.preview.sysman@example.com", roles=("System Manager",))
		cls.hr = ensure_user("s034.preview.hr@example.com", roles=("HR Manager", "Employee"))
		cls.hr_user_role = ensure_user("s034.preview.hruser@example.com", roles=("HR User", "Employee"))
		cls.employee = ensure_user("s034.preview.employee@example.com", roles=("Employee",))
		for user in (cls.sysman, cls.hr, cls.hr_user_role, cls.employee):
			frappe.db.set_value("User", user, "module_profile", None, update_modified=False)
			frappe.db.delete("Block Module", {"parent": user, "parenttype": "User"})
		frappe.db.commit()

	def setUp(self):
		frappe.set_user("Administrator")
		self._saved = frappe.conf.get("portal_preview")

	def tearDown(self):
		if self._saved is None:
			frappe.conf.pop("portal_preview", None)
		else:
			frappe.conf["portal_preview"] = self._saved
		frappe.local.flags.redirect_location = None
		frappe.set_user("Administrator")

	def _flag_off(self):
		frappe.conf.pop("portal_preview", None)

	def _flag_on(self):
		frappe.conf["portal_preview"] = 1

	def _open(self):
		return page.get_context(frappe._dict())


class TestLockOneTheSiteFlag(_PreviewBase):
	def test_a_system_manager_gets_404_when_the_flag_is_absent(self):
		"""AC-74. Absent, not 0 - the handoff note asks for this exact case."""
		self._flag_off()
		self.assertNotIn("portal_preview", frappe.conf)
		frappe.set_user(self.sysman)
		with self.assertRaises(frappe.DoesNotExistError):
			self._open()

	def test_the_404_is_really_a_404(self):
		self.assertEqual(frappe.DoesNotExistError.http_status_code, 404)
		self.assertEqual(frappe.PermissionError.http_status_code, 403)

	def test_everybody_gets_404_when_the_flag_is_absent(self):
		self._flag_off()
		for user in (self.sysman, self.hr, self.hr_user_role, self.employee, "Guest"):
			frappe.set_user(user)
			with self.assertRaises(frappe.DoesNotExistError, msg=user):
				self._open()

	def test_a_flag_of_zero_is_the_same_as_no_flag(self):
		frappe.conf["portal_preview"] = 0
		frappe.set_user(self.sysman)
		with self.assertRaises(frappe.DoesNotExistError):
			self._open()

	def test_the_flag_is_read_before_the_role(self):
		"""The whole point of the ordering. With the flag off, somebody who would
		be refused by the role check gets 404 - the page's non-existence, not its
		refusal. If the role check ran first they would get 403 and learn the
		page is there."""
		self._flag_off()
		frappe.set_user(self.employee)
		with self.assertRaises(frappe.DoesNotExistError):
			self._open()

	def test_the_helper_says_the_same_thing_the_page_says(self):
		self._flag_off()
		self.assertFalse(page.preview_is_enabled())
		self._flag_on()
		self.assertTrue(page.preview_is_enabled())


class TestLockTwoTheRole(_PreviewBase):
	def test_a_system_manager_may_open_it(self):
		"""AC-40. No exception, and the page gets its branding and its title."""
		self._flag_on()
		frappe.set_user(self.sysman)
		context = frappe._dict()
		page.get_context(context)
		self.assertEqual(context.no_cache, 1)
		self.assertEqual(context.title, "Portal preview")
		self.assertTrue(context.get("tenant_name"))

	def test_every_other_signed_in_persona_gets_403(self):
		"""AC-40. HR, an HR User and a plain employee - all refused, with the
		flag ON, which is the case the role check actually has to hold."""
		self._flag_on()
		for user in (self.hr, self.hr_user_role, self.employee):
			frappe.set_user(user)
			with self.assertRaises(frappe.PermissionError, msg=user):
				self._open()

	def test_guest_is_sent_to_the_login_page(self):
		self._flag_on()
		frappe.set_user("Guest")
		with self.assertRaises(frappe.Redirect):
			self._open()
		location = frappe.local.flags.redirect_location or ""
		self.assertIn("login", location)
		self.assertIn("/hrms-employee-next", location)

	def test_hr_is_refused_even_though_the_portal_calls_them_hr(self):
		"""The portal's is_hr includes HR Manager and HR User. This page does
		not use it: an unfinished build of an HR screen is not an HR screen."""
		self._flag_on()
		frappe.set_user(self.hr)
		self.assertIn("HR Manager", frappe.get_roles(self.hr))
		with self.assertRaises(frappe.PermissionError):
			self._open()


class TestTheCachingAndSitemapRules(_PreviewBase):
	def test_the_page_module_sets_no_cache_and_drops_out_of_the_sitemap(self):
		"""AC-65 / OPS-12. Frappe reads both off the page module
		(website/page_renderers/template_page.py, v16.33.1)."""
		self.assertEqual(page.no_cache, 1)
		self.assertEqual(page.sitemap, 0)

	def test_the_template_also_carries_the_no_sitemap_marker(self):
		html = _app_file("www", "hrms-employee-next.html")
		self.assertIn("no-sitemap", html)
		self.assertIn("noindex", html)


def _app_file(*parts):
	"""A file inside the installed alvoraa_portal package, read as text."""
	root = os.path.dirname(os.path.abspath(alvoraa_portal.__file__))
	return io.open(os.path.join(root, *parts), encoding="utf-8").read()


def _deploy_dir():
	"""The repository's deploy folder, reached from the installed app.

	The app is <repo>/alvoraa_portal/alvoraa_portal, so the repository is three
	levels up. On a bench where the app is mounted rather than checked out in
	place this may not resolve; the test says so instead of passing quietly.
	"""
	app_pkg = os.path.dirname(os.path.abspath(alvoraa_portal.__file__))
	return os.path.join(os.path.dirname(os.path.dirname(app_pkg)), "deploy")


class TestNoProductionConfigTurnsThePreviewOn(_PreviewBase):
	"""AC-74's second half, and the reason the page cannot reach production.

	The flag is allowed to appear in a dev or test config. It must never appear
	in a production one, or in the shared compose file that production runs.
	"""

	def test_the_deploy_folder_is_where_this_test_thinks_it_is(self):
		deploy = _deploy_dir()
		if not os.path.isdir(deploy):
			self.skipTest(f"deploy/ not reachable from the installed app at {deploy}; "
			              f"run this check in the repository (CI) as well")
		self.assertTrue(os.path.isfile(os.path.join(deploy, "compose", "docker-compose.app.yml")))

	def test_no_production_config_or_compose_environment_sets_the_flag(self):
		deploy = _deploy_dir()
		if not os.path.isdir(deploy):
			self.skipTest("deploy/ not reachable from the installed app")
		offenders = []
		for folder, _dirs, files in os.walk(deploy):
			for name in files:
				path = os.path.join(folder, name)
				try:
					text = io.open(path, encoding="utf-8", errors="ignore").read()
				except OSError:
					continue
				if "portal_preview" not in text:
					continue
				lowered = name.lower()
				# Only a file that is plainly a dev or test one may name it.
				if "dev" in lowered or "test" in lowered:
					continue
				offenders.append(os.path.relpath(path, deploy))
		self.assertEqual(
			offenders, [],
			f"portal_preview is set in a production deployment file: {offenders}. "
			f"The preview page would then exist on production (SEC-1).",
		)
