"""The duplicate-sign-in guard, asked correctly (ALV-396, ALV-399).

One check in `joiner_invite` answers one question: does this number or email
already belong to a live sign-in here? It was wrong in both directions, and
each direction is its own ticket.

  * **ALV-399** - HR could not re-invite somebody whose invite was cancelled,
    and the refusal sent them to the email path, which was broken (ALV-394).
    It LOOKED like this guard counting dead invites, and the first fix taught
    it to ignore them. These tests proved that wrong: `User.mobile_no` is a
    UNIQUE column, so the database refused the re-invite on its own, with a
    duplicate-key error, before any check of ours was reached. The real cause
    is that closing an invite never gave the number back, so the fix is in
    `end_the_sign_in` and not here. (`User.username` is unique too, but Frappe
    already blanks a duplicate itself, so releasing it bought nothing and was
    deleted - a break run is what showed that.)
  * **ALV-396** - it could not see an EMAIL invite at all. An email is written
    to no `User` column, so two live invites could share one address. The
    second silently took the account and the first joiner was told, for ever,
    that their correct password was wrong. Nothing reached HR.

**Nothing is ignored.** Any `User` row holding the credential blocks, switched
off or not, because the unique index means such a row genuinely still holds it.
The special case for dead joiner accounts that an earlier version of this fix
carried is gone; these tests are written against the simple rule.

The two tests that matter most here are the ones that say **no**:

  * a switched-off STAFF login must still block, so an employee's number can
    never be handed to a joiner.
  * a row that HR has written down but not invited must NOT block. Counting
    those would refuse the FIRST invite as well as the second, and HR could
    invite nobody on that address at all.

**One test here belongs to ALV-394 as much as to these two tickets.** Giving the
number back means a closed MOBILE invite no longer resolves through Frappe's own
lookup, so resolution on that path now rests on ALV-394's `before_login` hook,
and `test_a_closed_MOBILE_invite_still_resolves_to_its_own_account` pins it.

**It is resolution only, and the release-ordering claim that once sat here was
wrong.** This work was described - in two ticket comments, a commit message and
a memory note - as something that must not land before ALV-394, on the grounds
that a closed mobile invite would otherwise read "Invalid credentials". Measured
on a bench, a closed invite reads that either way: closing destroys the password
and frappe tests the password before the disabled flag, so the kinder branch was
never reachable for a properly closed invite. Nothing a joiner reads changes.
"""

import frappe

from alvoraa_portal import joiner_invite
from alvoraa_portal.tests import fixtures_079 as fx
from alvoraa_portal.tests.fixtures_045 import Wave4Base, own_user

DOCTYPE = "Alvoraa Joiner Submission"


class JoinerDuplicateGuard(Wave4Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hr = own_user("s396hr", ("Employee", "HR Manager"))

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		fx.clear_the_rows()
		fx.switch_the_form_on()
		self._mobile_login_was = frappe.db.get_single_value(
			"System Settings", "allow_login_using_mobile_number")
		fx.allow_sign_in_by_mobile(True)
		self._stray_users = []

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in self._stray_users:
			if frappe.db.exists("User", name):
				frappe.delete_doc("User", name, force=True,
				                  ignore_permissions=True,
				                  delete_permanently=True)
		fx.clear_the_rows()
		fx.switch_the_form_off()
		fx.allow_sign_in_by_mobile(bool(self._mobile_login_was))
		super().tearDown()

	# ── helpers ─────────────────────────────────────────────────────────────

	def _invite(self, login_id, full_name):
		"""What HR does: write the person down, then press the button."""
		frappe.set_user(self.hr)
		row = fx.a_row(full_name=full_name, login_id=login_id)
		reply = joiner_invite.make_sign_in(submission=row.name)
		frappe.set_user("Administrator")
		return row, reply

	def _row_only(self, login_id, full_name):
		"""Written down, NOT invited. No sign-in exists for this one."""
		frappe.set_user(self.hr)
		row = fx.a_row(full_name=full_name, login_id=login_id)
		frappe.set_user("Administrator")
		return row

	def _end_it(self, row, status="Cancelled"):
		"""Close the invite the way HR does, through the row's own status."""
		frappe.set_user("Administrator")
		doc = frappe.get_doc(DOCTYPE, row.name)
		doc.status = status
		doc.save(ignore_permissions=True)
		frappe.db.commit()
		return doc

	def _account_of(self, row):
		return frappe.db.get_value(DOCTYPE, row.name, "user")

	# ── ALV-399: a dead invite must not block the living ────────────────────

	def test_a_cancelled_invite_does_not_block_the_same_number_again(self):
		"""ALV-399. HR invites, cancels, and invites the same person again.

		Before the fix the second invite was refused, because the cancelled
		invite's disabled account still carried the number.
		"""
		number = "+91 98100 13991"
		first, _ = self._invite(number, "S399 First Go")
		account = self._account_of(first)
		self.assertTrue(account, "the first invite made no account, so this "
		                         "test would pass without proving anything")

		self._end_it(first, "Cancelled")
		self.assertEqual(
			frappe.db.get_value("User", account, "enabled"), 0,
			"cancelling did not disable the account, so the case this test "
			"exists for was never set up")

		# The whole point: HR can invite the same person again.
		second, reply = self._invite(number, "S399 Second Go")
		self.assertTrue(self._account_of(second))
		self.assertNotEqual(self._account_of(second), account,
		                    "the new invite reused the dead account")
		self.assertEqual(reply.get("username"), number)

	def test_an_expired_invite_does_not_block_either(self):
		"""ALV-399. Expired is a terminal status too, not only Cancelled."""
		number = "+91 98100 13992"
		first, _ = self._invite(number, "S399 Expired")
		self._end_it(first, "Expired")
		second, _ = self._invite(number, "S399 After Expiry")
		self.assertTrue(self._account_of(second))

	def test_a_live_invite_still_blocks_the_same_number(self):
		"""The guard must still do its job. Without this the fix above could
		be 'return False' and every test here would pass."""
		number = "+91 98100 13993"
		self._invite(number, "S399 Live")
		frappe.set_user(self.hr)
		row = fx.a_row(full_name="S399 Would Be Second", login_id=number)
		with self.assertRaises(frappe.ValidationError):
			joiner_invite.make_sign_in(submission=row.name)
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.get_value(DOCTYPE, row.name, "user"))

	def test_a_disabled_STAFF_login_still_blocks(self):
		"""The line the fix must not cross.

		A member of staff whose account is switched off still keeps their
		number. Handing it to a joiner would mean two logins share it the day HR
		switches that employee back on - and the unique index would refuse the
		second account anyway, so HR would get a duplicate-key error instead of
		a sentence.

		**This no longer pins a special case, because there is no longer one.**
		An earlier version of the fix ignored switched-off joiner accounts and
		this test was the line it must not cross. The final fix ignores nothing,
		so this passes under the simple rule too. It stays as a regression pin:
		if anybody teaches the guard to skip disabled accounts again, this is
		what says no.
		"""
		number = "+91 98100 13994"
		staff = frappe.get_doc({
			"doctype": "User", "email": "s399.disabled.staff@example.com",
			"first_name": "S399 Disabled Staff", "mobile_no": number,
			"enabled": 0, "send_welcome_email": 0, "user_type": "Website User",
		}).insert(ignore_permissions=True)
		self._stray_users.append(staff.name)
		frappe.db.commit()

		frappe.set_user(self.hr)
		row = fx.a_row(full_name="S399 Blocked By Staff", login_id=number)
		with self.assertRaises(frappe.ValidationError):
			joiner_invite.make_sign_in(submission=row.name)
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.get_value(DOCTYPE, row.name, "user"))

	# ── ALV-396: the guard can see an email invite ──────────────────────────

	def test_two_live_rows_cannot_share_an_email(self):
		"""ALV-396, and AC-9 for the email path.

		Before the fix both invites went out, the second took the address, and
		the first joiner was told their correct password was wrong - for ever,
		with no signal to HR.
		"""
		email = "s396.shared@example.com"
		first, _ = self._invite(email, "S396 Elder Brother")
		self.assertTrue(self._account_of(first))

		frappe.set_user(self.hr)
		second = fx.a_row(full_name="S396 Younger Brother", login_id=email)
		with self.assertRaises(frappe.ValidationError):
			joiner_invite.make_sign_in(submission=second.name)
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.get_value(DOCTYPE, second.name, "user"),
		                 "the second invite made an account anyway")

	def test_an_email_is_matched_whatever_the_letter_case(self):
		"""The same address typed with different capitals is the same address.

		**The upper-case form is derived, not written down.** Writing the
		domain out with a capital letter counts as a hardcoded email address to
		`test_016_no_bare_email_address_is_hardcoded`, because its allowlist
		matches the placeholder domain case-sensitively - and it took dev's CI
		going red to find that out. (The first draft of this very docstring
		tripped the same gate by quoting the offending form, which is the trap
		twice over: the prose that explains a rule can break it.) Deriving the
		shouted form also makes the test stronger, because it varies the case of
		the domain as well as the mailbox, which is what somebody actually
		types.
		"""
		email = "s396.case@example.com"
		first, _ = self._invite(email, "S396 Lower")
		self.assertTrue(self._account_of(first))
		shouted = email.upper()
		self.assertNotEqual(shouted, email)
		frappe.set_user(self.hr)
		second = fx.a_row(full_name="S396 Upper", login_id=shouted)
		with self.assertRaises(frappe.ValidationError):
			joiner_invite.make_sign_in(submission=second.name)
		frappe.set_user("Administrator")

	def test_a_row_written_down_but_not_invited_blocks_nobody(self):
		"""The trap. The guard reads rows, so it can see the row HR is inviting
		and the ones they have only typed.

		If either counted, HR could invite NOBODY on that address: the first
		invite would refuse itself, or refuse because of a twin that has no
		sign-in. A row is only a sign-in once the button has been pressed.
		"""
		email = "s396.notyet@example.com"
		twin = self._row_only(email, "S396 Twin Not Invited")
		first, reply = self._invite(email, "S396 Invited First")
		self.assertTrue(self._account_of(first),
		                "a row with no sign-in blocked the first invite")
		self.assertEqual(reply.get("username"), email)
		# The twin is still only a row, and it still has no account.
		self.assertFalse(frappe.db.get_value(DOCTYPE, twin.name, "user"))

	def test_a_cancelled_row_does_not_block_the_same_email(self):
		"""ALV-396 and ALV-399 meeting: the email path needs the dead-row rule
		too, or it would trade one blockage for another."""
		email = "s396.again@example.com"
		first, _ = self._invite(email, "S396 First Go")
		self._end_it(first, "Cancelled")
		second, _ = self._invite(email, "S396 Second Go")
		self.assertTrue(self._account_of(second))

	# ── a close that did not reach the account (hr-app-08's finding) ────────

	def test_a_cancelled_invite_whose_account_stayed_OPEN_still_blocks(self):
		"""The state nobody meant to allow, and it is reachable.

		`end_the_sign_in` catches every exception, logs it and returns `False`,
		and `on_update` does not look at what it returned. So a close that could
		not reach the `User` row leaves the invite `Cancelled` and the account
		still open - still holding the number.

		**This test asserted the opposite first, and that was my mistake.** I
		read "the invite is closed" as "the number is free" and wrote a guard
		that waved HR through. It cannot be free: the number is still on a `User`
		row under a unique index, so the only thing waving HR through buys is a
		duplicate-key error instead of a sentence. Refusing is the honest answer
		while that account still holds it.

		(That a cancelled joiner keeps a working login is its own defect and has
		its own ticket. This test only pins what the guard does about it.)
		"""
		number = "+91 98100 13995"
		first, _ = self._invite(number, "S399 Close Failed")
		account = self._account_of(first)
		self._end_it(first, "Cancelled")
		# Put the account back exactly as a failed close leaves it: switched on,
		# and still holding the number.
		frappe.db.set_value("User", account, {"enabled": 1, "mobile_no": number})
		frappe.db.commit()
		self.assertEqual(frappe.db.get_value("User", account, "mobile_no"), number,
		                 "the state this test exists for was never set up")

		frappe.set_user(self.hr)
		row = fx.a_row(full_name="S399 Re-invite Attempt", login_id=number)
		with self.assertRaises(frappe.ValidationError):
			joiner_invite.make_sign_in(submission=row.name)
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.get_value(DOCTYPE, row.name, "user"))

	def test_an_OPEN_joiner_account_with_no_invite_behind_it_still_blocks(self):
		"""The other side of the same rule, and it must not be crossed.

		An enabled joiner account whose row is gone is a working credential that
		nothing will ever close. Ignoring it would let HR mint a second sign-in
		on the same number while the first still opens the door - two people on
		one credential, which is the one outcome worse than refusing HR.
		"""
		number = "+91 98100 13996"
		first, _ = self._invite(number, "S399 Orphan Maker")
		account = self._account_of(first)
		self._stray_users.append(account)
		frappe.db.delete(DOCTYPE, {"name": first.name})
		frappe.db.commit()
		self.assertFalse(frappe.db.exists(DOCTYPE, first.name))
		self.assertEqual(frappe.db.get_value("User", account, "enabled"), 1)

		self.assertTrue(joiner_invite._already_a_login(number),
		                "an open account with no invite behind it was ignored")

	# ── ALV-399's real fix: closing an invite gives the number back ─────────

	def test_closing_an_invite_gives_the_number_back(self):
		"""The fix itself, asserted on the column rather than through a reply.

		`mobile_no` is UNIQUE on `User`. While a closed account still held the
		number, no second account could be made on it at all - so ALV-399 was
		never about the duplicate check, and no change to that check could have
		fixed it.
		"""
		number = "+91 98100 13997"
		row, _ = self._invite(number, "S399 Released")
		account = self._account_of(row)
		self.assertEqual(frappe.db.get_value("User", account, "mobile_no"), number)

		self._end_it(row, "Cancelled")
		self.assertEqual(frappe.db.get_value("User", account, "enabled"), 0)
		self.assertIsNone(frappe.db.get_value("User", account, "mobile_no"),
		                  "the number was not given back")

	def test_the_SAME_person_can_be_re_invited_under_the_same_name(self):
		"""The case HR actually hits, and the one the first fix still broke.

		Re-inviting the same person means the same name as well as the same
		number, and the name becomes `User.username`, which is unique too. This
		passes without any code of ours: Frappe blanks a duplicate username for
		a Website User (`User.validate_username`) and stores an empty unique
		field as NULL (`get_valid_dict`). The test is here so that stays true -
		if Frappe ever stops doing it, this is what says so.
		"""
		number = "+91 98100 13998"
		name = "S399 Priya Khanna"
		first, _ = self._invite(number, name)
		account = self._account_of(first)
		self._end_it(first, "Cancelled")

		second, reply = self._invite(number, name)
		self.assertTrue(self._account_of(second), "the same person could not be "
		                                         "re-invited under the same name")
		self.assertNotEqual(self._account_of(second), account)
		self.assertEqual(reply.get("username"), number)

	def test_a_SUBMITTED_row_blocks_the_same_email(self):
		"""The state most live rows actually sit in, and it was untested.

		`TERMINAL` is Made an employee, Expired and Cancelled. `Submitted` is
		not among them, on purpose: decision 4a keeps the sign-in working after
		the form is sent, so a submitted row still holds its address. Every
		other liveness test here uses `Invited`, so without this one the rule
		was only proved for the narrower state.
		"""
		email = "s396.submitted@example.com"
		first, _ = self._invite(email, "S396 Already Sent")
		self._end_it(first, "Submitted")
		self.assertEqual(frappe.db.get_value(DOCTYPE, first.name, "status"),
		                 "Submitted")
		self.assertTrue(self._account_of(first),
		                "sending must not have closed the account - if it did, "
		                "this test is pinning the wrong state")

		frappe.set_user(self.hr)
		second = fx.a_row(full_name="S396 Second On It", login_id=email)
		with self.assertRaises(frappe.ValidationError):
			joiner_invite.make_sign_in(submission=second.name)
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.get_value(DOCTYPE, second.name, "user"))

	# ── the MOBILE path, which this fix made depend on ALV-394 ──────────────

	def test_a_closed_MOBILE_invite_still_resolves_to_its_own_account(self):
		"""Resolution on the mobile path, which nothing covered.

		**What this proves, and deliberately no more:** a closed mobile invite
		still resolves to its own account rather than to nothing.

		Giving the number back is what puts this test here. Before, the mobile
		path worked by accident - Frappe's own lookup finds a typed number
		through `User.mobile_no`, so a closed account was found because it still
		carried the number. Release it and that lookup finds nothing, so
		resolution now rests entirely on ALV-394's `before_login` hook, which
		keys on `login_id` on the submission row. ALV-394's suite proves that
		branch for an **email** invite; the mobile path is what this change
		moved onto it, so pinning it belongs here.

		**It does NOT prove 079 AC-17, and AC-17 is not met for this case by
		anything.** AC-17 promises an ended joiner "This sign-in has finished
		its job", never "Invalid credentials" - but only for "the CORRECT
		password", and `end_the_sign_in` destroys the password. So no correct
		password exists, and `frappe/auth.py` tests `is_authenticated` BEFORE
		`enabled`: the password check fails first and answers "Invalid login
		credentials", which never reaches the ENDED wording. The requirement
		contradicts itself. Found by the ALV-397 session; confirmed here by
		reading the order in frappe's `authenticate`, because this test used to
		claim the AC-17 wording in its own name.

		**Two earlier versions of this test were wrong, recorded so neither
		comes back.** The first called `User.find_by_credentials` with the raw
		number - the lookup the hook runs *in front of* - so it could not pass
		however correct the product was. The second passed, but its name said it
		proved the joiner is told their sign-in ended, which no code does.
		"""
		from frappe.core.doctype.user.user import User

		from alvoraa_portal import auth

		number = "+91 98100 13999"
		row, _ = self._invite(number, "S399 Ended Mobile")
		account = self._account_of(row)
		self._end_it(row, "Cancelled")

		# The number really is gone from the account - otherwise this test
		# would pass on the old behaviour and prove nothing about the hook.
		self.assertIsNone(frappe.db.get_value("User", account, "mobile_no"))
		self.assertIsNone(
			User.find_by_credentials(number, "x", validate_password=False),
			"Frappe can still find the account by the number, so this test is "
			"not exercising the hook at all")

		was = getattr(frappe.local, "form_dict", None)
		try:
			frappe.local.form_dict = frappe._dict(usr=number, pwd="unread here")
			auth.let_the_joiner_type_what_hr_gave_them(login_manager=None)
			resolved = frappe.local.form_dict.get("usr")
		finally:
			if was is not None:
				frappe.local.form_dict = was

		self.assertEqual(resolved, account,
		                 "the hook did not resolve the number to the closed "
		                 "account, so the attempt is not even attributed to it")
		self.assertEqual(frappe.db.get_value("User", resolved, "enabled"), 0,
		                 "resolved, but to an account Frappe would let in")

	# ── the guard called directly, for the cases above in isolation ─────────

	def test_the_guard_says_no_to_an_address_nobody_holds(self):
		"""The negative control: without it every assertFalse above could pass
		because the guard always says no."""
		self.assertFalse(joiner_invite._already_a_login("nobody@example.com"))
		self.assertFalse(joiner_invite._already_a_login("+91 90000 00000"))
		self.assertFalse(joiner_invite._already_a_login("   "))
