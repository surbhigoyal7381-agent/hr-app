"""Slice 024 — the employee portal is the landing page, for every tenant, in code.

Typing https://<tenant>/ used to drop a signed-in employee into the Frappe desk.
Frappe resolves "/" through `get_home_page()`, and nothing in our apps answered
it: no Role home page, no Portal Settings, no hook, no Website Settings. The
fallback for a System User is the desk, and every one of our staff accounts is a
System User.

The fix is one hook — `get_website_user_home_page` — pointed at the rule that
already governed login, so the bare address and the sign-in door can never give
different answers again.

These tests exist so a bad merge cannot quietly take the hook back out, and so
nobody later "simplifies" the rule into sending administrators, guests or a
tenant's vendor users somewhere they cannot use.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.website.utils import get_home_page, get_home_page_via_hooks

from alvoraa_portal import auth
from alvoraa_portal import subscription as sub

PORTAL = "hrms-employee"


def _rand():
	return frappe.utils.random_string(6).lower()


class LandingCase(FrappeTestCase):
	"""Shared fixtures: real users, real roles, real Employee records."""

	def setUp(self):
		self._features = frappe.conf.get("features")

	def tearDown(self):
		if self._features is None:
			frappe.conf.pop("features", None)
		else:
			frappe.conf["features"] = self._features
		frappe.set_user("Administrator")
		frappe.db.rollback()

	# ── fixtures ────────────────────────────────────────────────────────────

	def make_user(self, roles=()):
		user = frappe.new_doc("User")
		user.email = f"h024_{_rand()}@example.com"
		user.first_name = "Landing"
		user.send_welcome_email = 0
		user.insert(ignore_permissions=True)
		if roles:
			user.add_roles(*roles)
		return user.name

	def make_employee_for(self, user):
		emp = frappe.new_doc("Employee")
		emp.first_name = "Landing"
		emp.last_name = "Tester"
		emp.employee_name = "Landing Tester"
		emp.company = frappe.get_value("Company", {}, "name")
		emp.date_of_birth = frappe.utils.add_years(frappe.utils.today(), -30)
		emp.date_of_joining = frappe.utils.add_years(frappe.utils.today(), -1)
		# Whatever this site actually has. A fresh test site carries only "Male".
		emp.gender = frappe.get_value("Gender", {}, "name")
		emp.status = "Active"
		emp.user_id = user
		emp.flags.ignore_mandatory = True
		emp.insert(ignore_permissions=True)
		return emp.name

	# ── what Frappe itself resolves ─────────────────────────────────────────

	def landing_for(self, user):
		"""The answer Frappe's own hook chain gives for this user.

		This is the real path, not a call to our function: it proves the hook is
		registered and that Frappe reaches it.

		Careful with "no answer". When nothing in the chain replies, Frappe's
		`get_home_page_via_hooks` returns the empty list it got from
		`frappe.get_hooks("home_page")`, not None. It is falsy either way and
		every caller tests it with `if not home_page`, but a test that asserts
		`is None` fails for the wrong reason. Hence `assertNoOpinion` below.
		"""
		frappe.set_user(user)
		try:
			return get_home_page_via_hooks()
		finally:
			frappe.set_user("Administrator")

	def assertNoOpinion(self, got):
		"""Frappe was left to decide — which means the desk for a System User
		and the login page for Guest."""
		self.assertFalse(got, f"expected no landing page, got {got!r}")

	def full_landing_for(self, user):
		"""The whole of `get_home_page()`, cache cleared first."""
		frappe.cache.hdel("home_page", user)
		frappe.set_user(user)
		try:
			return get_home_page()
		finally:
			frappe.set_user("Administrator")
			frappe.cache.hdel("home_page", user)


class TestTheHookIsWired(LandingCase):
	def test_the_hook_is_registered(self):
		"""If this line ever goes missing, "/" silently returns to the desk."""
		hooks = frappe.get_hooks("get_website_user_home_page")
		self.assertIn("alvoraa_portal.auth.home_page_for", hooks)

	def test_frappe_actually_calls_it(self):
		"""Frappe passes the user and uses what comes back."""
		user = self.make_user()
		self.make_employee_for(user)
		self.assertEqual(self.landing_for(user), PORTAL)


class TestWhoLandsWhere(LandingCase):
	def test_an_employee_lands_on_the_portal(self):
		user = self.make_user()
		self.make_employee_for(user)
		self.assertEqual(self.landing_for(user), PORTAL)
		self.assertEqual(self.full_landing_for(user), PORTAL)

	def test_an_hr_manager_who_is_an_employee_lands_on_the_portal(self):
		"""Seniority does not route. HR do their work in the portal too, and a
		tenant's HR admin usually also holds System Manager."""
		user = self.make_user(roles=["HR Manager", "System Manager"])
		self.make_employee_for(user)
		self.assertEqual(self.landing_for(user), PORTAL)

	def test_a_system_manager_with_no_employee_record_keeps_the_desk(self):
		"""A platform operator. Sending them to an employee page every login is
		a daily annoyance, and the back office is their workplace."""
		user = self.make_user(roles=["System Manager"])
		self.assertIsNone(auth.home_page_for(user))
		self.assertNoOpinion(self.landing_for(user))
		self.assertNotEqual(self.full_landing_for(user), PORTAL)

	def test_administrator_keeps_the_desk(self):
		self.assertIsNone(auth.home_page_for("Administrator"))
		self.assertNoOpinion(self.landing_for("Administrator"))

	def test_guest_still_reaches_the_login_page(self):
		"""Nobody is bounced into a portal they cannot see."""
		self.assertIsNone(auth.home_page_for("Guest"))
		self.assertNoOpinion(self.landing_for("Guest"))
		self.assertEqual(self.full_landing_for("Guest"), "login")

	def test_a_user_with_no_employee_and_no_desk_role_gets_the_portal(self):
		"""Unchanged from what login already did."""
		user = self.make_user()
		self.assertEqual(self.landing_for(user), PORTAL)


class TestNobodyLandsOffPlan(LandingCase):
	"""The part most likely to be got wrong.

	`portal` is a required feature, so every tenant has /hrms-employee whatever
	the plan. The vendor and driver portals are not: slice 016 made both pages
	404 when the tenant does not have the `vendor` feature. Routing somebody
	there off-plan is landing them on a missing page.
	"""

	def make_vendor_user(self):
		user = self.make_user()
		vendor = frappe.new_doc("Vendor")
		vendor.vendor_name = f"Landing Vendor {_rand()}"
		vendor.company_name = "Landing Co"
		vendor.email = user
		vendor.phone = "9999999999"
		vendor.account_status = "Active"
		vendor.insert(ignore_permissions=True)

		vu = frappe.new_doc("Vendor User")
		vu.vendor = vendor.name
		vu.email = user
		vu.frappe_user = user
		vu.insert(ignore_permissions=True)
		return user

	def test_the_employee_portal_is_on_every_plan(self):
		"""The fallback has to be safe, so it must be a required feature."""
		self.assertTrue(sub.FEATURES["portal"]["required"])
		self.assertTrue(sub.has_feature("portal", {"features": []}))
		self.assertTrue(sub.has_feature("portal", {"subscription_plan": "starter"}))

	def test_an_employee_on_a_stripped_plan_still_lands_on_the_portal(self):
		user = self.make_user()
		self.make_employee_for(user)
		frappe.conf["features"] = []
		self.assertEqual(self.landing_for(user), PORTAL)

	def test_a_vendor_user_off_plan_does_not_land_on_the_vendor_portal(self):
		"""Starter tenant, vendor row left behind. The page 404s; do not send
		them to it."""
		user = self.make_vendor_user()
		frappe.conf["features"] = []
		self.assertFalse(sub.has_feature("vendor"))
		self.assertEqual(self.landing_for(user), PORTAL)

	def test_a_vendor_user_on_plan_still_lands_on_the_vendor_portal(self):
		"""The gate must not become a one-way door."""
		user = self.make_vendor_user()
		frappe.conf["features"] = list(sub.FEATURES)
		self.assertTrue(sub.has_feature("vendor"))
		self.assertEqual(self.landing_for(user), "vendor-portal")


class TestTheDoorsAgree(LandingCase):
	"""The bare address, the login moment and the branded login page must give
	one answer. They used to be two rules in two files."""

	def test_on_login_and_the_bare_address_agree(self):
		user = self.make_user()
		self.make_employee_for(user)
		frappe.set_user(user)
		try:
			frappe.local.response.pop("home_page", None)
			auth.on_login()
			self.assertEqual(frappe.local.response.get("home_page"), "/" + PORTAL)
			self.assertEqual(auth.get_portal_redirect()["url"], "/" + PORTAL)
		finally:
			frappe.local.response.pop("home_page", None)
			frappe.set_user("Administrator")

	def test_an_operator_is_left_to_frappe_at_login(self):
		"""No opinion means no key written, so Frappe's own logic decides."""
		user = self.make_user(roles=["System Manager"])
		frappe.set_user(user)
		try:
			frappe.local.response.pop("home_page", None)
			auth.on_login()
			self.assertIsNone(frappe.local.response.get("home_page"))
			self.assertEqual(auth.get_portal_redirect()["url"], "/app")
		finally:
			frappe.local.response.pop("home_page", None)
			frappe.set_user("Administrator")


class TestItNeverBreaksTheFrontDoor(LandingCase):
	def test_a_failed_lookup_gives_up_the_redirect_not_the_site(self):
		user = self.make_user()
		real = frappe.db.exists

		def boom(*args, **kwargs):
			raise RuntimeError("database gone")

		frappe.db.exists = boom
		try:
			self.assertIsNone(auth.home_page_for(user))
		finally:
			frappe.db.exists = real
