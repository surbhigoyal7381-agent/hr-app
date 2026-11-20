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

**The first version of this file was green on a hook that never ran**, and that
is the reason `TestARealRequest` exists. The fix began life as a `before_request`
hook. `frappe/app.py:242` builds `HTTPRequest()`, which signs the person in and
raises, **two lines before** the `before_request` loop at :244 - so on the one
path the hook was written for, it was never reached. Every test below called the
function by hand with a fake request, so all sixteen passed against a no-op.

So one test here drives a real request through `frappe.app.application`, and it
is worth more than the other fifteen: it is the only one that can tell a working
feature from a working function. The rest check the behaviour of the function
once it is reached, which is a different and smaller question.
"""

import importlib
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

	def _typed_at_the_sign_in(self, typed):
		"""The function alone, called the way `run_trigger` calls it.

		**This is not proof that a sign-in works** - see the module docstring.
		It proves what the function does once Frappe reaches it, and nothing
		about whether Frappe reaches it. `TestARealRequest` answers that.
		"""
		frappe.local.form_dict = frappe._dict(usr=typed, pwd="unread here")
		auth.let_the_joiner_type_what_hr_gave_them(login_manager=None)
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

	def test_an_ordinary_request_never_reaches_it_at_all(self):
		"""`before_login` fires from `LoginManager.login()` and nowhere else
		(frappe/auth.py:147), so there is no path guard to test - there is no
		other path. The earlier shape of this fix had method and path checks
		because it sat on `before_request`, where every request in the product
		went past it. Those are gone, and so is that cost.
		"""
		self.assertIn("alvoraa_portal.auth.let_the_joiner_type_what_hr_gave_them",
		              frappe.get_hooks("before_login"))
		self.assertNotIn("alvoraa_portal.auth.let_the_joiner_type_what_hr_gave_them",
		                 frappe.get_hooks("before_request"))

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


# ── two LIVE rows on one address: refuse, do not choose ────────────────────

class TestTwoLiveSignInsAreRefused(_Base):
	"""Data that predates both this fix and ALV-396's guard.

	ALV-396 stops a second invite being made while the first is live and
	already has a sign-in. It cannot clean up a tenant where that already
	happened. On such a row `login_id` matches two **enabled** accounts, and
	the resolver's "prefer enabled" branch would have a choice to make.

	It must not make it. Picking either one signs the joiner into somebody
	else's record, and both parties then see a screen that works, which is why
	this would go unnoticed. Refusing leaves them exactly where this fix found
	them - told their password is wrong - which is bad, and is not the same
	kind of bad.
	"""

	def _two_live_rows_on_one_address(self):
		"""The legacy shape, built the only way the guard allows.

		The second invite is made while the first is Cancelled, because
		`_already_a_login` would otherwise refuse it - correctly. The first row
		and its account are then put back to live, which is what the old data
		looks like: two rows, two enabled accounts, one address.
		"""
		old, old_password = self._invited(AN_EMAIL, full_name="S394 Old Live")
		frappe.db.set_value(DOCTYPE, old.name, "status", "Cancelled",
		                    update_modified=False)
		frappe.db.commit()

		new, new_password = self._invited(AN_EMAIL, full_name="S394 New Live")

		frappe.db.set_value(DOCTYPE, old.name, "status", "Invited",
		                    update_modified=False)
		frappe.db.set_value("User", old.user, "enabled", 1,
		                    update_modified=False)
		frappe.db.commit()

		self.assertNotEqual(old.user, new.user)
		for who in (old.user, new.user):
			self.assertTrue(frappe.db.get_value("User", who, "enabled"),
			                f"{who} should be enabled for this test to mean "
			                f"anything")
		return old, old_password, new, new_password

	def test_what_was_typed_is_left_alone(self):
		"""The refusal, where it matters: no rewrite, so no wrong record."""
		old, _old_pw, new, _new_pw = self._two_live_rows_on_one_address()

		resolved = self._typed_at_the_sign_in(AN_EMAIL)

		self.assertEqual(
			resolved, AN_EMAIL,
			"the hook chose one of two live accounts instead of refusing")
		self.assertNotIn(resolved, (old.user, new.user))

	def test_neither_password_gets_anybody_in(self):
		"""Not just unrewritten - genuinely refused.

		`AN_EMAIL` is on no `User`, so authentication fails on the address
		itself. This is the assertion that would catch a future "helpful"
		fallback that tries each candidate in turn.
		"""
		_old, old_password, _new, new_password = \
			self._two_live_rows_on_one_address()

		for password in (old_password, new_password):
			self.assertFalse(
				self._the_password_is_accepted(AN_EMAIL, password),
				"a live-but-ambiguous address let somebody in")

	def test_hr_is_told_in_the_security_log(self):
		"""The joiner cannot report this usefully, so HR has to find it.

		`.warning` through `security_logger`, not `frappe.logger("security")`:
		the plain logger sits at ERROR in our images and would throw the line
		away in silence. That was ALV-391, and it is why this asserts the LINE
		and not merely that something was called.

		**No personal data in it** (079-PRIV-7). What the joiner typed is a real
		email address or mobile number and must not be written; the login ids
		may be, because 079 makes them opaque on purpose, and they are what HR
		needs to find the two rows.
		"""
		import json as _json

		access = importlib.import_module("hrms.alvoraa_hr_core.access")

		old, _old_pw, new, _new_pw = self._two_live_rows_on_one_address()

		written = []

		class _Recorder:
			def warning(self, line):
				written.append(line)

		real = access.security_logger
		access.security_logger = lambda: _Recorder()
		try:
			self._typed_at_the_sign_in(AN_EMAIL)
		finally:
			access.security_logger = real

		self.assertEqual(len(written), 1, written)
		line = _json.loads(written[0])
		self.assertEqual(
			line["event"],
			"joiner_sign_in_matched_more_than_one_live_account")
		self.assertEqual(line["count"], 2)
		self.assertEqual(sorted(line["accounts"]), sorted([old.user, new.user]))
		self.assertNotIn(AN_EMAIL, written[0],
		                 "the joiner's own address was written to the log")

	def test_the_sign_in_survives_a_broken_log(self):
		"""A sign-in must never fail on its own audit trail.

		It still refuses - that is the point of the branch - but it refuses by
		returning, not by raising into Frappe's login.
		"""
		access = importlib.import_module("hrms.alvoraa_hr_core.access")

		self._two_live_rows_on_one_address()

		def boom():
			raise RuntimeError("the log is gone")

		real = access.security_logger
		access.security_logger = boom
		try:
			resolved = self._typed_at_the_sign_in(AN_EMAIL)
		finally:
			access.security_logger = real

		self.assertEqual(resolved, AN_EMAIL)

# ── a cancelled invite whose account never closed ──────────────────────────

class TestAClosedInviteWithAnOpenAccount(_Base):
	"""The silent close failure, and why this hook must not resolve it.

	`joiner_invite.end_the_sign_in` catches every exception, writes an Error
	Log and returns False. `on_update` calls it and **discards the answer**
	(`alvoraa_joiner_submission.py:99`). So if the write to the `User` row
	fails, the save still succeeds: the invite reads Cancelled, HR's screen
	says Cancelled, and the login still works.

	The fallback in `_the_sign_in_hr_made_for` exists to resolve an ENDED
	sign-in to its old account, so Frappe says "disabled or missing" and the
	page says "this sign-in has finished its job". Hand it an account that is
	still OPEN and Frappe authenticates it instead - **a cancelled joiner signs
	in.**

	Before ALV-394 nothing mapped an emailed address to that account, so the
	fault sat there unreachable. This hook is what would make it a door. The
	fault itself is somebody else's ticket; keeping this hook out of it is
	this file's job.
	"""

	def _cancelled_but_still_open(self):
		"""Exactly what a failed close leaves behind: terminal row, live login."""
		doc, password = self._invited(AN_EMAIL)
		frappe.db.set_value(DOCTYPE, doc.name, "status", "Cancelled",
		                    update_modified=False)
		frappe.db.set_value("User", doc.user, "enabled", 1,
		                    update_modified=False)
		frappe.db.commit()

		self.assertTrue(frappe.db.get_value("User", doc.user, "enabled"),
		                "the account must be OPEN for this test to mean "
		                "anything")
		return doc, password

	def test_the_cancelled_joiner_is_not_let_in(self):
		"""The assertion that matters: the right password still does not work."""
		doc, password = self._cancelled_but_still_open()

		self.assertEqual(
			self._typed_at_the_sign_in(AN_EMAIL), AN_EMAIL,
			"the hook resolved a cancelled invite to an account that still "
			"works, so the joiner signs in after being cancelled")
		self.assertFalse(
			self._the_password_is_accepted(AN_EMAIL, password),
			"a cancelled joiner signed in with their old password")
		# The account really would have let them in - so the refusal above is
		# this hook's doing and not Frappe's.
		self.assertTrue(
			User.find_by_credentials(doc.user, password).get("is_authenticated"),
			"the account was already shut, so this test proves nothing")

	def test_hr_is_told_in_the_security_log(self):
		"""Nobody else can see this. The joiner is told their password is
		wrong, which is true-ish and useless, and HR's screen already says
		Cancelled. The log line is the only place the contradiction surfaces."""
		import json as _json

		access = importlib.import_module("hrms.alvoraa_hr_core.access")

		doc, _password = self._cancelled_but_still_open()

		written = []

		class _Recorder:
			def warning(self, line):
				written.append(line)

		real = access.security_logger
		access.security_logger = lambda: _Recorder()
		try:
			self._typed_at_the_sign_in(AN_EMAIL)
		finally:
			access.security_logger = real

		self.assertEqual(len(written), 1, written)
		line = _json.loads(written[0])
		self.assertEqual(
			line["event"],
			"joiner_sign_in_closed_invite_still_has_an_open_account")
		self.assertIn(doc.user, line["accounts"])
		self.assertNotIn(AN_EMAIL, written[0],
		                 "the joiner's own address was written to the log")

	def test_a_properly_closed_invite_still_resolves(self):
		"""The branch this must not break.

		A sign-in ended the normal way has a DISABLED account, and resolving to
		it is what gets the joiner "your sign-in has finished" instead of
		"wrong password". Refusing everything terminal would have thrown that
		away to fix the case above.
		"""
		doc, _ = self._invited(AN_EMAIL)
		joiner_invite.end_the_sign_in(doc, "test")
		frappe.db.commit()

		self.assertEqual(self._typed_at_the_sign_in(AN_EMAIL), doc.user)
		self.assertFalse(frappe.db.get_value("User", doc.user, "enabled"))


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


# ── the only test that can tell a feature from a function ──────────────────

class TestARealRequest(_Base):
	"""Drives `frappe.app.application` itself, the whole way through.

	Everything else in this file calls the hook by hand. This one does not know
	the hook exists: it posts what the browser posts and reads the status code.
	It is the test that would have caught the `before_request` mistake, and the
	only one here that goes near `frappe/app.py`.
	"""

	def _post_a_sign_in(self, usr, pwd):
		"""A real POST to /api/method/login. Returns the status code.

		The request runs `frappe.init` and `frappe.destroy` of its own, which
		tears down the connection this test is holding - so the context is
		rebuilt afterwards or every later assertion runs on a dead handle.
		"""
		from werkzeug.test import Client

		from frappe.app import application

		site = frappe.local.site
		frappe.db.commit()
		try:
			return Client(application).post(
				"/api/method/login",
				json={"usr": usr, "pwd": pwd},
				headers={"Host": site},
			).status_code
		finally:
			frappe.destroy()
			frappe.init(site=site)
			frappe.connect()
			frappe.set_user("Administrator")

	def test_a_joiner_invited_by_email_really_signs_in(self):
		"""The reported fault, end to end.

		Before the move to `before_login` this is 401 however green the rest of
		the file is, because the hook never ran.
		"""
		_doc, password = self._invited(AN_EMAIL)
		self.assertEqual(self._post_a_sign_in(AN_EMAIL, password), 200)

	def test_the_wrong_password_is_still_refused_over_HTTP(self):
		self._invited(AN_EMAIL)
		self.assertEqual(
			self._post_a_sign_in(AN_EMAIL, "not-the-password-99"), 401)

	def test_an_address_nobody_was_invited_on_is_refused_over_HTTP(self):
		self._invited(AN_EMAIL)
		self.assertEqual(
			self._post_a_sign_in("s394.nobody@example.com", "anything-at-all"),
			401)


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

	def test_the_eye_is_a_44px_target(self):
		"""079's reason for a 44 px reveal outlived the button it asked for.

		The eye was 18 px of SVG with 4 px of padding - a 26 px target on the
		one screen used by somebody who cannot ring our helpdesk. Surbhi asked
		for 44 px on 20 November 2026. Asserted here because a touch target is
		exactly the kind of thing that shrinks again in a tidy-up.
		"""
		html = _the_login_page()
		start = html.index(".kx-pw-toggle {")
		rule = html[start:html.index("}", start)]
		self.assertIn("min-width: 44px", rule)
		self.assertIn("min-height: 44px", rule)
		self.assertIn("justify-content: center", rule)

	def test_the_refusal_no_longer_names_a_button_that_is_gone(self):
		html = _the_login_page()
		self.assertIn("JOIN-BADPASS", html)
		self.assertIn("Press the eye beside the box", html)
