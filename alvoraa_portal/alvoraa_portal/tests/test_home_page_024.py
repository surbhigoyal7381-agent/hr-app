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

from unittest import mock

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

	def make_user(self, roles=(), chose_own_password=True):
		user = frappe.new_doc("User")
		user.email = f"h024_{_rand()}@example.com"
		user.first_name = "Landing"
		user.send_welcome_email = 0
		user.insert(ignore_permissions=True)
		if roles:
			user.add_roles(*roles)
		if chose_own_password:
			# An employee who has never chosen their own password is sent to
			# /update-password, so a test about where an ESTABLISHED user lands
			# has to say that they have chosen one. Frappe stamps this field in
			# one place only — the whitelisted `update_password` behind the
			# /update-password page — so an empty value means "HR issued it and
			# nobody has replaced it yet".
			frappe.db.set_value(
				"User", user.name, "last_password_reset_date", frappe.utils.today()
			)
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

	def test_an_employee_on_an_issued_password_is_sent_to_change_it(self):
		"""HR hands one password to a whole batch of staff. Until a person has
		replaced it with their own, every door lands them on /update-password.

		We never compare the password or its hash — Frappe salts every hash
		separately, so a hundred people sharing one password have a hundred
		different hashes and there is nothing to match. The signal is only
		"has this person ever set their own password".
		"""
		user = self.make_user(chose_own_password=False)
		self.make_employee_for(user)
		self.assertEqual(self.landing_for(user), "update-password")
		# The branded login page is the door nearly all staff come through
		# (`www/alvoraa-login.html` calls this after a successful sign-in), and
		# /login redirects to it. It has to agree with the bare address.
		frappe.set_user(user)
		try:
			self.assertEqual(auth.get_portal_redirect()["url"], "/update-password")
		finally:
			frappe.set_user("Administrator")

	def test_an_operator_on_an_issued_password_is_left_alone(self):
		"""The password nudge is for staff. This function answers the front
		door of every tenant, so a platform operator who has never used
		/update-password must still reach the desk, not be herded off it."""
		user = self.make_user(roles=["System Manager"], chose_own_password=False)
		self.assertIsNone(auth.home_page_for(user))

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


class TestTheFirstUseJourney(LandingCase):
	"""Walk it, do not assume it.

	The nudge rests on one unwritten premise - that HR setting a password does
	not count as the person choosing one - and it ends at one step nobody owned:
	where Frappe sends them after the change. Both are tested here by calling
	the real functions, because a test that sets `last_password_reset_date` by
	hand proves only that our own `if` statement works.
	"""

	ISSUED = "Kx7#vRm2Zp9qLw"
	CHOSEN = "Tb4$nQy8Wd3rJm"
	FRAPPE_ENDPOINT = "frappe.core.doctype.user.user.update_password"

	def the_endpoint_the_page_reaches(self):
		"""Resolve the change-password endpoint the way a request does.

		`frappe.handler.execute_cmd` runs the name through
		`frappe.override_whitelisted_method` and then `get_attr` on whatever
		comes back, and that is the only path to the browser - /api/v1 funnels
		into the same handler, /api/v2 resolves it the same way. Calling
		`auth.update_password` by name here would pass even if the hook that
		puts it in the way were deleted, which is the whole fault this class was
		written to stop happening twice.
		"""
		return frappe.get_attr(frappe.override_whitelisted_method(self.FRAPPE_ENDPOINT))

	def make_user_with_an_issued_password(self):
		"""HR's own path: a password typed on the User form and saved."""
		user = frappe.new_doc("User")
		user.email = f"h024_{_rand()}@example.com"
		user.first_name = "Landing"
		user.send_welcome_email = 0
		user.new_password = self.ISSUED
		user.insert(ignore_permissions=True)
		return user.name

	def test_hr_setting_a_password_is_not_the_person_choosing_one(self):
		"""The premise the whole design rests on, and the only thing in this
		suite watching Frappe for us.

		If an upgrade ever made `User.save` stamp `last_password_reset_date`,
		the nudge would switch itself off for a whole batch and every other
		test in this file would still pass, because they all set the field by
		hand. Nothing observable would change until HR noticed that nobody was
		being asked.
		"""
		user = self.make_user_with_an_issued_password()
		self.assertFalse(
			frappe.db.get_value("User", user, "last_password_reset_date"),
			"Frappe now stamps the field when HR sets a password - the nudge is dead",
		)

		# And a second save with another password still does not stamp it.
		doc = frappe.get_doc("User", user)
		doc.new_password = self.CHOSEN
		doc.save(ignore_permissions=True)
		self.assertFalse(frappe.db.get_value("User", user, "last_password_reset_date"))

	def test_changing_the_password_stamps_the_date_and_lands_them_in_the_portal(self):
		"""The whole journey, through Frappe's real endpoint.

		Frappe's `update_password` ends `return get_default_path() or "/desk"`
		for a System User, and the page navigates to whatever comes back. Our
		wrapper replaces that path. Without it this test fails on the first
		assertion with /desk or /apps - the Frappe back office, handed to a
		frontline worker as the last step of first use.

		`login_manager` is a stand-in: the real one needs an HTTP request, and
		the old-password check is Frappe's job, not what this test is about.
		"""
		user = self.make_user_with_an_issued_password()
		self.make_employee_for(user)
		self.assertEqual(self.landing_for(user), "update-password")

		frappe.set_user(user)
		try:
			frappe.local.response.pop("http_status_code", None)
			with mock.patch.object(frappe.local, "login_manager", mock.MagicMock(), create=True):
				landed = self.the_endpoint_the_page_reaches()(
					new_password=self.CHOSEN, old_password=self.ISSUED
				)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(landed, "/" + PORTAL)
		self.assertTrue(frappe.db.get_value("User", user, "last_password_reset_date"))
		# And it clears itself - no list of who is still pending to keep in step.
		self.assertEqual(self.landing_for(user), PORTAL)

	def test_an_operator_changing_their_password_keeps_frappes_own_answer(self):
		"""This wrapper runs on every password change on every tenant. A
		platform operator must still be handed the desk, not herded into an
		employee portal."""
		user = self.make_user_with_an_issued_password()
		frappe.get_doc("User", user).add_roles("System Manager")

		frappe.set_user(user)
		try:
			frappe.local.response.pop("http_status_code", None)
			with mock.patch.object(frappe.local, "login_manager", mock.MagicMock(), create=True):
				landed = self.the_endpoint_the_page_reaches()(
					new_password=self.CHOSEN, old_password=self.ISSUED
				)
		finally:
			frappe.set_user("Administrator")

		self.assertNotEqual(landed, "/" + PORTAL)
		self.assertNotEqual(landed, "/update-password")

	def test_a_dead_reset_link_still_gets_its_message_not_a_portal_page(self):
		"""Frappe answers a used or invalid link with 410 and a sentence for
		the user. Replacing that with a portal path would send somebody who
		never proved anything into the portal."""
		frappe.local.response.pop("http_status_code", None)
		try:
			answer = self.the_endpoint_the_page_reaches()(
				new_password=self.CHOSEN, key="not-a-real-key"
			)
			self.assertEqual(frappe.local.response.get("http_status_code"), 410)
			self.assertNotIn(PORTAL, answer)
		finally:
			frappe.local.response.pop("http_status_code", None)


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


class TestTheBareRootBeatsTheTenantsOwnSettings(LandingCase):
	"""Surbhi, 28 Oct 2026: typing dtc.alvoraa.co gives an error.

	The hook above is real and works on a plain site, which is why slice 024's
	tests pass. But `get_home_page()` asks it FOURTH: a home_page on any role
	wins first, then Portal Settings, and after everything a default workspace
	REPLACES the answer outright. A tenant that has any of those set never
	reaches our hook.

	`route_the_bare_root` sets `frappe.local.flags.home_page`, which Frappe
	reads before all five, so these tests pin the one behaviour that holds
	whatever a tenant has been configured with.
	"""

	def at_root(self, user, path="/"):
		"""Run the before_request hook as `user` asking for `path`."""
		frappe.local.flags.pop("home_page", None)
		req = mock.Mock()
		req.path = path
		with mock.patch.object(frappe.local, "request", req, create=True):
			frappe.set_user(user)
			try:
				auth.route_the_bare_root()
			finally:
				frappe.set_user("Administrator")
		return frappe.local.flags.get("home_page")

	def test_the_hook_is_registered(self):
		"""Without this line the bare address goes back to being a lottery."""
		self.assertIn("alvoraa_portal.auth.route_the_bare_root",
		              frappe.get_hooks("before_request"))

	def test_staff_land_on_the_portal(self):
		user = self.make_user()
		self.make_employee_for(user)
		self.assertEqual(self.at_root(user), PORTAL)

	def test_the_answer_carries_no_leading_slash(self):
		"""Frappe returns this flag unstripped and then serves it as a route,
		so a leading slash would ask for a page called "/hrms-employee"."""
		user = self.make_user()
		self.make_employee_for(user)
		self.assertFalse((self.at_root(user) or "").startswith("/"))

	def test_a_visitor_gets_our_sign_in_page_not_frappes(self):
		"""The /login redirect never covered "/", so a visitor was being shown
		Frappe's own unbranded Login page on every tenant."""
		self.assertEqual(self.at_root("Guest"), "alvoraa-login")

	def test_somebody_still_on_an_issued_password_goes_to_change_it(self):
		"""The bare address must not be a way around ALV-232."""
		user = self.make_user(chose_own_password=False)
		self.make_employee_for(user)
		self.assertEqual(self.at_root(user), "update-password")

	def test_a_platform_operator_is_left_alone(self):
		"""A System Manager is what marks an operator - NOT the absence of an
		Employee record. My first version of this test assumed the latter and
		failed: a user with neither an Employee record nor a desk role is a
		vendor or driver login, and they do belong in a portal."""
		user = self.make_user(roles=["System Manager"])
		self.assertIsNone(self.at_root(user))

	def test_a_login_that_is_neither_staff_nor_operator_still_gets_a_portal(self):
		"""Vendor and driver logins have no Employee record and no desk role.
		The bare address must not strand them on the Frappe desk."""
		user = self.make_user()
		self.assertEqual(self.at_root(user), PORTAL)

	def test_no_other_address_is_touched(self):
		user = self.make_user()
		self.make_employee_for(user)
		for path in ("/hrms-employee", "/app", "/checkin", "/alvoraa-login", "/update-password"):
			self.assertIsNone(self.at_root(user, path), path)

	def test_it_fails_open(self):
		"""A front door that breaks must not take the site with it."""
		user = self.make_user()
		self.make_employee_for(user)
		with mock.patch.object(auth, "home_page_for", side_effect=RuntimeError("boom")):
			self.assertIsNone(self.at_root(user))
