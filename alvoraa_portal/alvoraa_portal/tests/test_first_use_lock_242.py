"""ALV-242 — a first-use session reaches nothing but the password screen.

ALV-232 chose where somebody LANDS after signing in with the password HR
issued. Surbhi found what that leaves open: land on /update-password, press the
browser's back button, and the whole app is there, payslips included, with the
shared password never changed. HR hands one password to a whole batch, so that
is not "a user skipping a step" — it is one worker signing in as another and
reading their pay.

These tests exist so that hole cannot be reopened by a tidy-up, and — just as
important — so the lock cannot quietly become a cage. Half of them are about
the ways somebody must still get OUT: the password screen itself, the files it
loads, the two methods it calls, and sign-out.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import auth


def _rand():
	return frappe.utils.random_string(6).lower()


class _FakeRequest:
	"""Only `path` is read, so only `path` is supplied."""

	def __init__(self, path):
		self.path = path


class LockCase(FrappeTestCase):
	def setUp(self):
		self._real_request = getattr(frappe.local, "request", None)
		self._real_form = getattr(frappe.local, "form_dict", None)

	def tearDown(self):
		frappe.local.request = self._real_request
		frappe.local.form_dict = self._real_form
		frappe.set_user("Administrator")
		frappe.cache().delete_key(auth._CHOSEN_CACHE)
		frappe.db.rollback()

	# ── fixtures ────────────────────────────────────────────────────────────

	def make_user(self, roles=(), chose_own_password=False):
		user = frappe.new_doc("User")
		user.email = f"lock242_{_rand()}@example.com"
		user.first_name = "Lock"
		user.send_welcome_email = 0
		user.insert(ignore_permissions=True)
		if roles:
			user.add_roles(*roles)
		if chose_own_password:
			frappe.db.set_value("User", user.name, "last_password_reset_date",
			                    frappe.utils.today(), update_modified=False)
		return user.name

	def make_employee_for(self, user):
		emp = frappe.new_doc("Employee")
		emp.first_name = "Lock"
		emp.last_name = "Tester"
		emp.employee_name = "Lock Tester"
		emp.company = frappe.get_value("Company", {}, "name")
		emp.date_of_birth = frappe.utils.add_years(frappe.utils.today(), -30)
		emp.date_of_joining = frappe.utils.add_years(frappe.utils.today(), -1)
		emp.gender = frappe.get_value("Gender", {}, "name")
		emp.status = "Active"
		emp.user_id = user
		emp.flags.ignore_mandatory = True
		emp.insert(ignore_permissions=True)
		return emp.name

	def staff_on_an_issued_password(self):
		user = self.make_user()
		self.make_employee_for(user)
		return user

	# ── the call under test ─────────────────────────────────────────────────

	def ask_for(self, path, user, cmd=None):
		"""Run the hook as `user` asking for `path`. Returns what happened.

		`cmd` is what a website page sends instead of a path - see
		`auth._FIRST_USE_MAY_CALL`. Left out, the form is emptied, so a test
		that says nothing about `cmd` is really asking with no `cmd` at all.
		"""
		frappe.local.request = _FakeRequest(path)
		frappe.set_user(user)
		# After set_user, never before: `frappe.set_user` empties form_dict.
		frappe.local.form_dict = frappe._dict({"cmd": cmd} if cmd else {})
		try:
			auth.lock_until_password_chosen()
			return "allowed"
		except auth._GoChooseAPassword as e:
			self._last_redirect = e
			return "redirect:" + (e.get_response().headers.get("Location") or "")
		except frappe.PermissionError:
			return "refused"
		finally:
			frappe.set_user("Administrator")


class TestTheHookIsWired(LockCase):
	def test_the_hook_is_registered(self):
		"""If this goes missing the back button works again, silently."""
		self.assertIn("alvoraa_portal.auth.lock_until_password_chosen",
		              frappe.get_hooks("before_request"))


class TestTheDoorIsShut(LockCase):
	"""The bug Surbhi found, and the other ways round it."""

	def test_the_portal_sends_them_back_to_the_password_screen(self):
		user = self.staff_on_an_issued_password()
		self.assertEqual(self.ask_for("/hrms-employee", user),
		                 "redirect:/update-password")

	def test_the_back_button_cannot_reach_the_portal(self):
		"""The exact report: back, from the password screen, to the home page."""
		user = self.staff_on_an_issued_password()
		self.assertTrue(self.ask_for("/", user).startswith("redirect:"))

	def test_the_desk_is_shut_too(self):
		"""Every staff account is a System User, so /app is a real door."""
		user = self.staff_on_an_issued_password()
		self.assertTrue(self.ask_for("/app", user).startswith("redirect:"))

	def test_the_other_portals_are_shut(self):
		user = self.staff_on_an_issued_password()
		for path in ("/me", "/checkin", "/vendor-portal", "/driver-portal"):
			with self.subTest(path=path):
				self.assertTrue(self.ask_for(path, user).startswith("redirect:"))

	def test_an_api_call_is_refused_not_redirected(self):
		"""Closing the page but leaving the data open would be theatre. An XHR
		cannot follow a redirect usefully, so this one is refused outright."""
		user = self.staff_on_an_issued_password()
		self.assertEqual(
			self.ask_for("/api/method/alvoraa_portal.pay_api.get_payslip", user),
			"refused")

	def test_the_payslip_resource_route_is_refused(self):
		user = self.staff_on_an_issued_password()
		self.assertEqual(self.ask_for("/api/resource/Salary%20Slip", user),
		                 "refused")


class TestFrappeActuallyReturnsTheRedirect(LockCase):
	"""The tests that were missing on 28 Oct, and the reason the first attempt
	reached production broken.

	The old tests asserted only that the hook RAISED a redirect. Every one of
	them passed. But `before_request` runs where `app.py` turns an escaping
	exception into a page through `handle_exception` - which has branches for
	401, 403, 404, 429 and 500 and none for a redirect - so what the browser
	actually got was an "Uncaught Exception" error page wearing a 301.

	"It raised the right thing" is not the same claim as "the browser is sent
	to the password screen". These test the second one.
	"""

	def test_it_is_the_kind_of_exception_frappe_turns_into_a_response(self):
		"""`app.py`: `e.get_response(environ) if isinstance(e, HTTPException)`.
		Miss this and it falls through to the error page again."""
		from werkzeug.exceptions import HTTPException

		self.assertTrue(issubclass(auth._GoChooseAPassword, HTTPException))

	def test_the_browser_gets_a_real_redirect(self):
		user = self.staff_on_an_issued_password()
		self.ask_for("/hrms-employee", user)
		response = self._last_redirect.get_response()

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.headers["Location"], "/update-password")

	def test_it_is_never_a_permanent_redirect(self):
		"""Werkzeug's own RequestRedirect is a 308. A browser caches a
		permanent redirect, so after the password was changed the phone would
		keep bouncing every page back here, with nothing on the server able to
		clear it."""
		user = self.staff_on_an_issued_password()
		self.ask_for("/hrms-employee", user)
		response = self._last_redirect.get_response()

		self.assertNotIn(response.status_code, (301, 308))
		self.assertEqual(response.headers.get("Cache-Control"), "no-store")

	def test_it_carries_no_error_page_body(self):
		"""If a body full of "Uncaught Exception" ever comes back, we are in the
		old failure again."""
		user = self.staff_on_an_issued_password()
		self.ask_for("/hrms-employee", user)
		body = self._last_redirect.get_response().get_data(as_text=True)

		self.assertNotIn("Uncaught Exception", body)


class TestTheWayOutStaysOpen(LockCase):
	"""The failure mode that would be worse than the bug: 441 people who can
	neither use the portal nor change their password."""

	def test_the_password_screen_itself(self):
		user = self.staff_on_an_issued_password()
		self.assertEqual(self.ask_for("/update-password", user), "allowed")

	def test_the_files_that_screen_loads(self):
		"""Measured from the real page, not assumed: it pulls the frappe-web
		bundle and /website_script.js."""
		user = self.staff_on_an_issued_password()
		for path in ("/assets/frappe/dist/js/frappe-web.bundle.SJKG74LB.js",
		             "/website_script.js", "/favicon.ico"):
			with self.subTest(path=path):
				self.assertEqual(self.ask_for(path, user), "allowed")

	def test_the_two_methods_that_screen_calls(self):
		"""The page calls exactly these two. Block either and the lock has no
		key."""
		user = self.staff_on_an_issued_password()
		for method in ("frappe.core.doctype.user.user.update_password",
		               "frappe.core.doctype.user.user.test_password_strength"):
			with self.subTest(method=method):
				self.assertEqual(
					self.ask_for("/api/method/" + method, user), "allowed")

	def test_our_own_wrapper_is_reachable(self):
		"""hooks.py points Frappe's update_password at ours, and a request can
		arrive addressed either way."""
		user = self.staff_on_an_issued_password()
		self.assertEqual(
			self.ask_for("/api/method/alvoraa_portal.auth.update_password", user),
			"allowed")

	def test_signing_in_is_not_blocked_by_the_lock(self):
		"""Found live on 28 Oct, by a real HTTP request, after every unit test
		had passed.

		Frappe completes the login inside `init_request`, which is also where
		this hook runs - so by the time we are called the session is already
		the new user and looks exactly like first use. Without this entry the
		login reply came back carrying "Logged In" AND a 403 in the same body:
		the person types the right password and is told it failed.
		"""
		user = self.staff_on_an_issued_password()
		self.assertEqual(self.ask_for("/api/method/login", user), "allowed")

	def test_signing_out_is_always_possible(self):
		"""Nobody is ever trapped in a session they cannot end."""
		user = self.staff_on_an_issued_password()
		for path in ("/logout", "/api/method/logout"):
			with self.subTest(path=path):
				self.assertEqual(self.ask_for(path, user), "allowed")

	def test_the_forgot_password_route_still_works(self):
		user = self.staff_on_an_issued_password()
		self.assertEqual(
			self.ask_for("/api/method/frappe.core.doctype.user.user.reset_password",
			             user),
			"allowed")


class TestNobodyElseIsLocked(LockCase):
	def test_somebody_who_chose_their_own_password(self):
		user = self.make_user(chose_own_password=True)
		self.make_employee_for(user)
		self.assertEqual(self.ask_for("/hrms-employee", user), "allowed")

	def test_administrator(self):
		self.assertEqual(self.ask_for("/app", "Administrator"), "allowed")

	def test_guest(self):
		self.assertEqual(self.ask_for("/alvoraa-login", "Guest"), "allowed")
		self.assertEqual(self.ask_for("/some-public-page", "Guest"), "allowed")

	def test_a_platform_operator_with_no_employee_record(self):
		"""Their account is not handed out on a card, and locking the back
		office out of its own site would be worse than the hole this closes."""
		user = self.make_user(roles=["System Manager"])
		self.assertEqual(self.ask_for("/app", user), "allowed")


class TestItNeverTakesTheSiteDown(LockCase):
	def test_it_fails_open(self):
		"""A lock that breaks must not become a workforce that cannot work."""
		user = self.staff_on_an_issued_password()
		real = frappe.db.get_value

		def boom(*args, **kwargs):
			raise RuntimeError("database gone")

		frappe.db.get_value = boom
		try:
			self.assertEqual(self.ask_for("/hrms-employee", user), "allowed")
		finally:
			frappe.db.get_value = real

	def test_no_request_no_opinion(self):
		"""Background jobs and the scheduler have no request at all."""
		frappe.local.request = None
		self.assertIsNone(auth.lock_until_password_chosen())


class TestItStaysOffTheDatabase(LockCase):
	"""This runs on every request of every tenant, so the ordinary case has to
	be cheap."""

	def test_a_settled_user_is_answered_from_cache_the_second_time(self):
		user = self.make_user(chose_own_password=True)
		self.assertTrue(auth._has_chosen_own_password(user))

		real = frappe.db.get_value

		def boom(*args, **kwargs):
			raise AssertionError("the cache should have answered this")

		frappe.db.get_value = boom
		try:
			self.assertTrue(auth._has_chosen_own_password(user))
		finally:
			frappe.db.get_value = real

	def test_an_allowed_path_never_reaches_the_database(self):
		"""The path test comes first on purpose: /assets/ is most of the
		requests on the site and must not cost a query."""
		user = self.staff_on_an_issued_password()
		real = frappe.db.get_value

		def boom(*args, **kwargs):
			raise AssertionError("an allowed path must not query")

		frappe.db.get_value = boom
		try:
			self.assertEqual(self.ask_for("/assets/x.js", user), "allowed")
		finally:
			frappe.db.get_value = real


class TestTheWayTheScreenActuallyCalls(LockCase):
	"""The live fault of 29 Oct, and the shape of test that would have caught it.

	Every test above asks with a path, because that is what the lock reads.
	The password screen never sends one. It is a website page, and
	`frappe.call` on a website page (`frappe/website/js/website.js`, not
	`request.js`) posts to "/" with the method in a `cmd` field. So the real
	Confirm button arrived as a bare POST to "/", matched nothing, and was
	answered with our own 302 - which jQuery followed, landing on HTML where
	it wanted JSON. No error was shown and the password never changed.
	"""

	def test_the_confirm_button_gets_through(self):
		"""The one that was broken. Press it and the lock must stand aside."""
		user = self.staff_on_an_issued_password()
		self.assertEqual(
			self.ask_for("/", user,
			             cmd="frappe.core.doctype.user.user.update_password"),
			"allowed")

	def test_every_method_that_screen_calls_gets_through(self):
		user = self.staff_on_an_issued_password()
		for cmd in ("frappe.core.doctype.user.user.update_password",
		            "frappe.core.doctype.user.user.test_password_strength",
		            "frappe.core.doctype.user.user.reset_password",
		            "alvoraa_portal.auth.update_password",
		            "login", "logout"):
			with self.subTest(cmd=cmd):
				self.assertEqual(self.ask_for("/", user, cmd=cmd), "allowed")

	def test_the_bare_root_is_still_shut(self):
		"""Opening the site itself is not a password change."""
		user = self.staff_on_an_issued_password()
		self.assertTrue(self.ask_for("/", user).startswith("redirect:"))

	def test_another_method_at_the_root_is_still_shut(self):
		"""The cage must not open for everything that posts to "/"."""
		user = self.staff_on_an_issued_password()
		self.assertTrue(
			self.ask_for("/", user, cmd="frappe.client.get_list")
			.startswith("redirect:"))

	def test_cmd_cannot_unlock_another_path(self):
		"""Frappe routes an /api/ request by its URL and ignores the body's
		`cmd`, so trusting `cmd` anywhere but "/" would be a way straight
		past the lock."""
		user = self.staff_on_an_issued_password()
		self.assertEqual(
			self.ask_for("/api/method/frappe.client.get_list", user,
			             cmd="login"),
			"refused")
