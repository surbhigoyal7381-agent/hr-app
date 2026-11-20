"""ALV-394: a joiner signs in with what HR actually gave them.

**The bug this file exists for.** Slice 079 gives a joiner an opaque,
non-routable login id on purpose (079-SEC-1), and `make_sign_in` copies what HR
typed onto `User.mobile_no` **only when it is a telephone number**. Invite
somebody by EMAIL and that email is stored nowhere: Frappe's
`User.find_by_credentials` matches `User.name`, `mobile_no` and `username` and
none of them holds it, so the sign-in failed with "Invalid login credentials" -
which the login page turns into the wrong-password wording. The password was
correct and was never read. Nobody invited by email could ever get in, and the
product told them to check their typing.

Worse, `make_sign_in` RECOMMENDED that path: refusing a mobile login id while
`allow_login_using_mobile_number` is off, it says "Or use the joiner's email
address instead".

**Why no test caught it.** Every 079 fixture invites with a phone number
(`fixtures_079.a_row`, `login_id="+91 98100 10079"`). The email path had no
test at all, so a green suite said nothing about it.

**What these tests do not do.** They stop at Frappe's own credential check
rather than driving a real HTTP request, so they prove the resolution and the
password together but not the web layer around them. The browser side is
`portal_joiner_sign_in_test.js`.
"""

import os

import frappe
from frappe.core.doctype.user.user import User

from alvoraa_portal import auth, joiner_invite
from alvoraa_portal.tests import fixtures_079 as fx
from alvoraa_portal.tests.fixtures_045 import Wave4Base, own_user

DOCTYPE = "Alvoraa Joiner Submission"

AN_EMAIL = "s394.priya@example.com"
A_MOBILE = "+91 98100 10394"


def _the_login_page():
	"""The page's source, read off disk.

	**Not `frappe.get_app_path("alvoraa_portal", "www", "alvoraa-login.html")`**:
	that scrubs every part it is given, so the real file `alvoraa-login.html`
	comes back as `alvoraa_login.html` and the open fails. Caught by these very
	tests on their first run.
	"""
	path = os.path.join(frappe.get_app_path("alvoraa_portal"), "www",
	                    "alvoraa-login.html")
	with open(path, encoding="utf-8") as f:
		return f.read()


class _Base(Wave4Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hr = own_user("s394hr", ("Employee", "HR Manager"))

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		fx.clear_the_rows()
		fx.switch_the_form_on()
		# **Deliberately OFF.** The whole point of the fix is that a joiner no
		# longer needs this tenant-wide setting, which also lets every employee
		# here sign in by mobile number (079 decision 6b).
		self._mobile_login_was = frappe.db.get_single_value(
			"System Settings", "allow_login_using_mobile_number")
		fx.allow_sign_in_by_mobile(False)
		self._request_was = getattr(frappe.local, "request", None)

	def tearDown(self):
		frappe.local.request = self._request_was
		frappe.set_user("Administrator")
		fx.clear_the_rows()
		fx.switch_the_form_off()
		fx.allow_sign_in_by_mobile(bool(self._mobile_login_was))
		super().tearDown()

	# ── the helpers ───────────────────────────────────────────────────────

	def _invited(self, login_id, full_name="S394 Priya Khanna"):
		"""HR writes the row and presses the button. Returns (doc, password)."""
		frappe.set_user(self.hr)
		row = fx.a_row(full_name=full_name, login_id=login_id)
		reply = joiner_invite.make_sign_in(submission=row.name)
		frappe.set_user("Administrator")
		return frappe.get_doc(DOCTYPE, row.name), reply["password"]

	def _typed_at_the_sign_in(self, typed, method="POST",
	                          path="/api/method/login"):
		"""What the browser sends, put where Frappe itself reads it.

		`make_form_dict` fills `form_dict` (frappe/app.py:239) BEFORE the
		`before_request` hooks run (:244), and `LoginManager.authenticate`
		reads `form_dict.usr` (frappe/auth.py:261). So this is the same seam
		the real request passes through.
		"""
		frappe.local.request = frappe._dict(method=method, path=path)
		frappe.local.form_dict = frappe._dict(usr=typed, pwd="unread here")
		auth.let_the_joiner_type_what_hr_gave_them()
		return frappe.local.form_dict.get("usr")

	def _the_password_is_accepted(self, login_id, password):
		"""The whole chain: what they type, resolved, then really checked."""
		resolved = self._typed_at_the_sign_in(login_id)
		found = User.find_by_credentials(resolved, password)
		return bool(found and found.get("is_authenticated"))


# ── the bug itself ─────────────────────────────────────────────────────────

class TestAnEmailInviteCanSignIn(_Base):
	def test_a_joiner_invited_by_email_signs_in(self):
		"""The reported fault, as the joiner meets it.

		Before the fix this is False no matter what the password is, because
		nothing anywhere holds the typed email.
		"""
		doc, password = self._invited(AN_EMAIL)
		self.assertTrue(self._the_password_is_accepted(AN_EMAIL, password))

	def test_and_it_reaches_the_account_HR_actually_made(self):
		doc, _ = self._invited(AN_EMAIL)
		self.assertEqual(self._typed_at_the_sign_in(AN_EMAIL), doc.user)

	def test_the_wrong_password_is_still_refused(self):
		"""Resolving the username must not wave anybody through."""
		self._invited(AN_EMAIL)
		resolved = self._typed_at_the_sign_in(AN_EMAIL)
		found = User.find_by_credentials(resolved, "not-the-password-99")
		self.assertFalse(found and found.get("is_authenticated"))


class TestAMobileInviteNoLongerNeedsTheSiteWideSetting(_Base):
	def test_it_signs_in_with_allow_login_using_mobile_number_off(self):
		"""`allow_sign_in_by_mobile(False)` is set in setUp.

		Before the fix a mobile invite could not even be MADE with the setting
		off - `make_sign_in` refuses one - so this path needed a tenant-wide
		change that also let every employee there sign in by mobile.
		"""
		fx.allow_sign_in_by_mobile(True)      # only so HR may create it
		doc, password = self._invited(A_MOBILE)
		fx.allow_sign_in_by_mobile(False)     # and now take it away again
		self.assertTrue(self._the_password_is_accepted(A_MOBILE, password))


# ── US-4: it must not become an oracle ─────────────────────────────────────

class TestItTellsAStrangerNothing(_Base):
	def test_an_address_nobody_was_invited_on_is_left_alone(self):
		"""Untouched means Frappe refuses it exactly as it always did.

		That is the whole no-oracle argument: there is no new endpoint and no
		new wording, so a guess cannot be told apart from a wrong password.
		"""
		self._invited(AN_EMAIL)
		stranger = "s394.nobody@example.com"
		self.assertEqual(self._typed_at_the_sign_in(stranger), stranger)

	def test_a_cancelled_invite_with_no_account_is_left_alone(self):
		doc, _ = self._invited(AN_EMAIL)
		frappe.db.set_value(DOCTYPE, doc.name, "user", None,
		                    update_modified=False)
		frappe.db.commit()
		self.assertEqual(self._typed_at_the_sign_in(AN_EMAIL), AN_EMAIL)


# ── everybody else's sign-in is untouched ──────────────────────────────────

class TestItLeavesEveryOtherSignInAlone(_Base):
	def test_a_member_of_staff_is_not_rewritten(self):
		self._invited(AN_EMAIL)
		self.assertEqual(self._typed_at_the_sign_in(self.hr), self.hr)

	def test_nothing_happens_on_a_GET(self):
		self._invited(AN_EMAIL)
		self.assertEqual(
			self._typed_at_the_sign_in(AN_EMAIL, method="GET"), AN_EMAIL)

	def test_nothing_happens_on_another_path(self):
		self._invited(AN_EMAIL)
		self.assertEqual(
			self._typed_at_the_sign_in(AN_EMAIL, path="/api/method/frappe.ping"),
			AN_EMAIL)

	def test_an_empty_username_is_left_alone(self):
		self.assertEqual(self._typed_at_the_sign_in(""), "")


# ── a sign-in that has ENDED says so (AC-13) ───────────────────────────────

class TestAnEndedSignInSaysSo(_Base):
	def test_it_resolves_to_the_disabled_account_not_to_nothing(self):
		"""Frappe answers "User disabled or missing" for a disabled account,
		and the page turns THAT into "this sign-in has finished its job".

		Resolve to nothing instead and the joiner is told their password is
		wrong, tries again, and locks themselves out - which is the failure
		079 decision 4a was written to avoid. For an email invite that could
		not work at all before this fix.
		"""
		doc, _ = self._invited(AN_EMAIL)
		joiner_invite.end_the_sign_in(doc, "test")
		frappe.db.commit()

		resolved = self._typed_at_the_sign_in(AN_EMAIL)
		self.assertEqual(resolved, doc.user)
		self.assertFalse(frappe.db.get_value("User", resolved, "enabled"))


# ── one address, two rows: the order is chosen, not left to the database ───

class TestOneAddressOnTwoRows(_Base):
	def test_the_live_invite_wins_over_a_cancelled_one(self):
		"""`login_id` is not unique on the submission - only `user` is.

		A cancelled invite keeps its (disabled) account, and for an EMAIL
		invite nothing on that account holds the address, so
		`_already_a_login` does not stop HR inviting the same person again.
		Both rows then carry one address and the newest live one must win.
		"""
		old, _ = self._invited(AN_EMAIL, full_name="S394 Old Row")
		frappe.db.set_value(DOCTYPE, old.name, "status", "Cancelled",
		                    update_modified=False)
		frappe.db.commit()

		new, password = self._invited(AN_EMAIL, full_name="S394 New Row")

		self.assertNotEqual(old.user, new.user)
		self.assertEqual(self._typed_at_the_sign_in(AN_EMAIL), new.user)
		self.assertTrue(self._the_password_is_accepted(AN_EMAIL, password))


# ── it can never lock a tenant out of its own login ────────────────────────

class TestItFailsOpen(_Base):
	def test_a_lookup_that_explodes_leaves_what_was_typed_alone(self):
		"""The inverse of `lock_to_the_joining_page`'s fail-CLOSED test, and
		deliberately not copied from it: this hook stands in front of every
		sign-in at every tenant, so a fault here must cost one joiner their
		convenience and never cost everybody their login.
		"""
		def boom(_typed):
			raise RuntimeError("the database is having a day")

		was = auth._the_sign_in_hr_made_for
		auth._the_sign_in_hr_made_for = boom
		try:
			self._invited(AN_EMAIL)
			self.assertEqual(self._typed_at_the_sign_in(AN_EMAIL), AN_EMAIL)
		finally:
			auth._the_sign_in_hr_made_for = was


# ── the screen (ALV-394, second half) ──────────────────────────────────────

class TestTheLoginPageHasOneReveal(_Base):
	def test_the_extra_show_the_password_button_is_gone(self):
		"""079 added a full-width button to REPLACE the eye icon, and the eye
		was never removed - so the screen carried two controls doing one job.
		Surbhi chose the eye on 20 November 2026.
		"""
		html = _the_login_page()
		self.assertNotIn("kx-reveal", html)
		# The translatable string, not the words: the comment above the CSS
		# explains why the button went, and says its name while doing so.
		self.assertNotIn('_("Show the password")', html)
		self.assertNotIn('_("Hide the password")', html)

	def test_the_eye_is_still_there(self):
		html = _the_login_page()
		self.assertIn("kx-pw-toggle", html)

	def test_the_refusal_no_longer_names_a_button_that_is_gone(self):
		html = _the_login_page()
		self.assertIn("JOIN-BADPASS", html)
		self.assertIn("Press the eye beside the box", html)
