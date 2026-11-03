"""079 pre-onboarding: the gate, the account, the two clocks, and the erasure.

Five things carry this file, and they are the five that would make the slice
dishonest if they were wrong:

  * **The one-page gate**, and that it fails **CLOSED**. This is the only reason
    a login is safer than the bearer link it replaced: without it, a joiner
    account lands on the staff portal, which is WIDER than a link. The
    fail-closed test is the inverse of `test_it_fails_open` and is deliberately
    not copied from it.
  * **The account's shape** - a Website User, one role, that role in no
    doctype's permission rows anywhere, an opaque non-routable login id, and no
    Employee row, so no seat, no headcount and no Attendance.
  * **Two clocks, not one.** An identity document goes at 30 days and the record
    at 180, and a test ages a row to each.
  * **Erasure that is not theatre.** Every field, every file, **every `Version`
    row** and the `User` account - asserted by query, with an HR edit in the
    middle, because without that edit the history assertion proves nothing.
  * **Send ends the form, not the sign-in** (decision 4a).
"""

import frappe
import hrms.alvoraa_org_structure.people_fields as people_fields
import hrms.alvoraa_org_structure.settings as org_settings
from frappe.utils import add_to_date, now

from alvoraa_portal import auth, joiner_housekeeping as hk, joiner_invite, joiner_public
from alvoraa_portal import my_profile, people_settings
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_joiner_submission.alvoraa_joiner_submission import (
	COLUMN_FOR_TICK,
	JOINER_FIELDS,
	erase,
)
from alvoraa_portal.tests import fixtures_079 as fx
from alvoraa_portal.tests.fixtures_045 import Wave4Base, own_user

DOCTYPE = "Alvoraa Joiner Submission"


class _Base(Wave4Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hr = own_user("s079hr", ("Employee", "HR Manager"))
		cls.sm = own_user("s079sm", ("Employee", "System Manager"))

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		fx.clear_the_rows()
		# **The form ships OFF, so a run without this has proved nothing**
		# (AC-117). Switched on here rather than left to a tenant.
		fx.switch_the_form_on()
		self._mobile_login_was = frappe.db.get_single_value(
			"System Settings", "allow_login_using_mobile_number")
		fx.allow_sign_in_by_mobile(True)

	def tearDown(self):
		frappe.set_user("Administrator")
		fx.clear_the_rows()
		fx.switch_the_form_off()
		fx.allow_sign_in_by_mobile(bool(self._mobile_login_was))
		super().tearDown()

	def _sign_in(self, mobile="+91 98100 10079", name="S079 Priya Khanna"):
		"""HR writes the row down and presses the button. Returns (doc, reply)."""
		frappe.set_user(self.hr)
		row = fx.a_row(full_name=name, login_id=mobile)
		out = joiner_invite.make_sign_in(submission=row.name)
		frappe.set_user("Administrator")
		return frappe.get_doc(DOCTYPE, row.name), out

	def _as_the_joiner(self, doc):
		frappe.set_user(doc.user)


# ── US-1, US-2, US-4 · the account's shape ─────────────────────────────────

class TestTheAccount(_Base):
	def test_it_is_a_website_user_with_one_role_and_no_employee(self):
		"""AC-1, AC-3, AC-6. Every clause is a door we are not opening."""
		doc, out = self._sign_in()
		user = frappe.get_doc("User", doc.user)
		self.assertEqual(user.user_type, "Website User",
			"A System User joiner would be a billable seat and would be sent to "
			"the desk by Frappe itself.")
		self.assertEqual(user.enabled, 1)
		self.assertEqual([r.role for r in user.roles], [joiner_invite.JOINER_ROLE],
			"Exactly one role. Never Employee Self Service.")
		self.assertEqual(user.send_welcome_email, 0,
			"Frappe's welcome mail carries a password link.")
		# The login id is opaque and non-routable, and equals nothing HR typed.
		self.assertTrue(user.name.startswith("joiner-"))
		self.assertTrue(user.name.endswith("@" + joiner_invite.LOGIN_DOMAIN))
		self.assertNotIn("98100", user.name)
		self.assertNotIn("priya", user.name.lower())
		# The number HR typed lives here, where Frappe resolves it.
		self.assertEqual(user.mobile_no, "+91 98100 10079")
		self.assertFalse(user.get("user_image"))
		# No Employee, so no seat, no headcount, no chart and no Attendance.
		self.assertFalse(frappe.db.exists("Employee", {"user_id": user.name}))
		self.assertFalse(frappe.db.exists("Attendance", {"employee_name": doc.full_name}))
		self.assertEqual(out["username"], "+91 98100 10079")
		self.assertTrue(out["password"])

	def test_the_seat_count_has_not_moved(self):
		"""AC-3. **A joiner is not a billable seat.**

		`usage.py` counts **enabled System Users**, which is exactly why the
		account is a Website User - so this counts the same thing before and
		after, rather than asserting on a helper that may be renamed.
		"""
		before = frappe.db.count("User", {"user_type": "System User", "enabled": 1})
		doc, _out = self._sign_in()
		self.assertEqual(
			frappe.db.count("User", {"user_type": "System User", "enabled": 1}),
			before, "Inviting a joiner moved the seat count.")
		self.assertEqual(
			frappe.db.get_value("User", doc.user, "user_type"), "Website User")

	def test_the_role_has_no_desk_and_appears_in_no_permission_row(self):
		"""AC-2, and it is the `announcements.py:565-578` trap: **Frappe creates
		a role WITH desk access the first time it meets the name in a doctype's
		permission rows.** So the name must appear in none, anywhere, and a
		static read of the JSON is the only thing that can prove it."""
		import json
		import os

		joiner_invite._role()
		self.assertEqual(
			frappe.db.get_value("Role", joiner_invite.JOINER_ROLE, "desk_access"), 0)

		found = []
		for app in ("alvoraa_portal", "hrms", "alvoraa_goals"):
			try:
				root = frappe.get_app_path(app)
			except Exception:
				continue
			for base, _dirs, files in os.walk(root):
				for f in files:
					if not f.endswith(".json"):
						continue
					path = os.path.join(base, f)
					try:
						body = json.load(open(path, encoding="utf-8"))
					except Exception:
						continue
					if not isinstance(body, dict):
						continue
					for row in body.get("permissions") or []:
						if isinstance(row, dict) and row.get("role") == joiner_invite.JOINER_ROLE:
							found.append(path)
		self.assertEqual(found, [],
			"The joiner role is in a doctype's permission rows: %s. Frappe would "
			"recreate it WITH desk access, and the role grants read on nothing by "
			"design - the joiner's own row is reached by server code bound to "
			"their session." % found)

	def test_two_invites_get_two_different_credentials(self):
		"""AC-4. This is ALV-242, which is live in this product today: HR hands
		one password to a whole batch, and a batch of joiners is exactly where
		it would be repeated."""
		_a, one = self._sign_in(mobile="+91 98100 10001", name="S079 One")
		_b, two = self._sign_in(mobile="+91 98100 10002", name="S079 Two")
		self.assertNotEqual(one["password"], two["password"])

	def test_the_credential_is_in_no_row_and_no_log(self):
		"""AC-5. Greps the row and the logger, because "it is not stored" is the
		kind of claim that is true until somebody adds a field."""
		import io
		import logging

		stream = io.StringIO()
		handler = logging.StreamHandler(stream)
		logger = frappe.logger("alvoraa")
		logger.addHandler(handler)
		# **The level, deliberately.** Frappe's default is WARNING or ERROR and
		# no site sets `log_level`, so without this the stream is empty and an
		# assertion that the credential is ABSENT from it would pass for the
		# wrong reason. A test of an absence has to make the thing it is reading
		# non-empty first.
		was = logger.level
		logger.setLevel(logging.DEBUG)
		try:
			doc, out = self._sign_in()
		finally:
			logger.setLevel(was)
			logger.removeHandler(handler)
		secret = out["password"]
		self.assertNotIn(secret, frappe.as_json(doc.as_dict()))
		self.assertTrue(stream.getvalue().strip(),
			"Nothing was logged at all, so the assertion below would prove "
			"nothing. Check the logger's level before changing it.")
		self.assertNotIn(secret, stream.getvalue())
		rows = frappe.get_all("Version", filters={"ref_doctype": DOCTYPE,
		                                          "docname": doc.name},
		                      fields=["data"], ignore_permissions=True)
		for row in rows:
			self.assertNotIn(secret, row.data or "")

	def test_a_number_that_is_already_a_login_is_refused(self):
		"""AC-9, E2, E3. One credential per person, never a batch - and a
		re-hire whose staff login exists is the same case."""
		self._sign_in(mobile="+91 98100 10079")
		frappe.set_user(self.hr)
		row = fx.a_row(full_name="S079 Second", login_id="+91 98100 10079")
		with self.assertRaises(frappe.ValidationError):
			joiner_invite.make_sign_in(submission=row.name)
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.get_value(DOCTYPE, row.name, "user"))

	def test_hr_cannot_invite_before_the_employer_has_set_its_values(self):
		"""AC-11, AC-12. **No User is created and no credential is generated.**
		The block lands on the person who can fix it, which is why there is no
		joiner-facing "we do not know how long they keep this" screen."""
		for key in ("alvoraa_joiner_document_days", "alvoraa_joiner_notice_text",
		            "alvoraa_hr_contact_phone", "alvoraa_hr_contact_email"):
			frappe.db.set_default(key, "")
		frappe.db.commit()
		missing = joiner_invite.what_the_employer_has_not_set()
		self.assertTrue(missing)
		frappe.set_user(self.hr)
		row = fx.a_row(full_name="S079 Too early")
		with self.assertRaises(frappe.ValidationError):
			joiner_invite.make_sign_in(submission=row.name)
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.get_value(DOCTYPE, row.name, "user"))
		# And the refusal names exactly what is still missing, one at a time.
		frappe.db.set_default("alvoraa_joiner_document_days", "30")
		frappe.db.commit()
		keys = {m["key"] for m in joiner_invite.what_the_employer_has_not_set()}
		self.assertNotIn("alvoraa_joiner_document_days", keys)
		self.assertIn("alvoraa_joiner_notice_text", keys)

	def test_the_forced_password_change_does_not_catch_a_joiner(self):
		"""AC-10. `lock_until_password_chosen` keys on
		`frappe.db.exists("Employee", {"user_id": user})`, so it already excludes
		a joiner - and a later "fix" to that line would strand one on
		/update-password, a page they cannot use."""
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		frappe.local.request = fx.FakeRequest("/joining")
		frappe.local.form_dict = frappe._dict()
		try:
			auth.lock_until_password_chosen()      # must not raise
		finally:
			frappe.local.request = None
			frappe.set_user("Administrator")


# ── US-5, US-6 · the gate ──────────────────────────────────────────────────

class TestTheOnePageGate(_Base):
	"""**P1.** Without this the slice is wider than the link it replaces."""

	def _ask(self, path, cmd=None):
		frappe.local.request = fx.FakeRequest(path)
		frappe.local.form_dict = frappe._dict({"cmd": cmd} if cmd else {})
		try:
			auth.lock_to_the_joining_page()
			return "allowed"
		except auth._GoToTheJoiningPage:
			return "redirected"
		except frappe.PermissionError:
			return "refused"
		finally:
			frappe.local.request = None
			frappe.local.form_dict = frappe._dict()

	def test_the_landing_is_the_joining_page(self):
		"""AC-20. One branch in the one function three doors share. Without it,
		`home_page_for` falls through to `_portal_home_for` -> /hrms-employee."""
		doc, _out = self._sign_in()
		self.assertEqual(auth.home_page_for(doc.user), "/joining")

	def test_every_other_page_is_refused(self):
		"""AC-21. One row per door, as the joiner's own session."""
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		for path in ("/", "/hrms-employee", "/goals-portal", "/vendor-portal",
		             "/driver-portal", "/checkin", "/alvoraa-admin", "/app",
		             "/app/employee", "/me"):
			with self.subTest(door=path):
				self.assertEqual(self._ask(path), "redirected")
		frappe.set_user("Administrator")

	def test_every_api_door_is_a_permission_error_not_a_redirect(self):
		"""AC-22. An XHR cannot follow a redirect usefully, and a caller at this
		level is asking for data rather than for a page."""
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		for path in ("/api/method/frappe.client.get_list",
		             "/api/method/frappe.client.get",
		             "/api/method/frappe.client.set_value",
		             "/api/resource/Employee",
		             "/api/resource/Alvoraa Joiner Submission",
		             "/api/method/frappe.desk.reportview.get",
		             "/api/method/frappe.desk.reportview.get_count",
		             "/api/method/frappe.desk.search.search_link",
		             "/api/method/frappe.desk.form.utils.add_comment",
		             "/api/method/frappe.share.add",
		             "/api/method/alvoraa_portal.hr_api.get_portal_context",
		             "/api/method/alvoraa_portal.my_profile.get_my_profile"):
			with self.subTest(door=path):
				self.assertEqual(self._ask(path), "refused")
		frappe.set_user("Administrator")

	def test_the_bare_root_with_a_cmd_is_refused(self):
		"""AC-24. **This product has paid for the missing-`cmd` half twice.** A
		website page's `frappe.call` posts to "/" with the method in a `cmd`
		field, so a test that asks only with a path proves nothing."""
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		for cmd in ("frappe.client.get_list", "frappe.client.get_value",
		            "frappe.desk.reportview.get", "frappe.client.set_value"):
			with self.subTest(cmd=cmd):
				self.assertEqual(self._ask("/", cmd=cmd), "redirected")
		frappe.set_user("Administrator")

	def test_files_are_not_on_the_allow_list(self):
		"""AC-26. Deliberately unlike `_FIRST_USE_MAY_REACH`, which allows
		/files/. The joiner needs no file door at all."""
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		for path in ("/files/anything.jpg", "/private/files/anything.jpg"):
			with self.subTest(door=path):
				self.assertEqual(self._ask(path), "redirected")
		frappe.set_user("Administrator")

	def test_their_own_page_and_endpoints_and_the_way_out_are_allowed(self):
		"""AC-23, AC-27. Leaving `/api/method/login` out makes the login reply
		carry "Logged In" and a 403 in one body - the person types the right
		password and is told it failed."""
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		for path in ("/joining", "/logout", "/login", "/alvoraa-login",
		             "/assets/x.js", "/favicon.ico",
		             "/api/method/login", "/api/method/logout",
		             # The second half of signing in. Refuse it and the first
		             # thing a joiner sees after typing the right password is the
		             # screen telling them they cannot be here.
		             "/api/method/alvoraa_portal.auth.get_portal_redirect",
		             "/api/method/alvoraa_portal.joiner_public.open_invite",
		             "/api/method/alvoraa_portal.joiner_public.save_draft",
		             "/api/method/alvoraa_portal.joiner_public.submit_invite",
		             "/api/method/alvoraa_portal.joiner_public.upload_invite_file"):
			with self.subTest(door=path):
				self.assertEqual(self._ask(path), "allowed")
		frappe.set_user("Administrator")

	def test_it_fails_closed(self):
		"""AC-25. **The inverse of `test_it_fails_open`, and it must never be
		copied from it.** `lock_until_password_chosen` fails open because locking
		441 staff out at shift change is worse than the hole it closes. Here a
		false denial costs ONE person a telephone call and a false allow puts an
		unidentified account inside a tenant's portal."""
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)

		def explode(*_a, **_k):
			raise RuntimeError("forced, from the test")

		# `_refuse` is the only thing left that can genuinely be buggy once the
		# gate knows who is asking, which is why it has its own function. Forcing
		# an exception in the ROLE lookup instead would be testing the block that
		# is MEANT to fail open, and would pass for the wrong reason.
		real = auth._refuse
		auth._refuse = explode
		try:
			frappe.local.request = fx.FakeRequest("/hrms-employee")
			frappe.local.form_dict = frappe._dict()
			with self.assertRaises(frappe.PermissionError):
				auth.lock_to_the_joining_page()
		finally:
			auth._refuse = real
			frappe.local.request = None
			frappe.set_user("Administrator")

	def test_a_member_of_staff_is_untouched(self):
		"""The other half of fail-closed, and the one that would cost a tenant
		its day: the gate must not have an opinion about anybody else."""
		frappe.set_user(self.kamal_user)
		for path in ("/hrms-employee", "/app", "/api/method/frappe.client.get_list"):
			with self.subTest(door=path):
				self.assertEqual(self._ask(path), "allowed")
		frappe.set_user("Administrator")
		self.assertEqual(self._ask("/app"), "allowed")

	def test_there_are_no_guest_endpoints_left(self):
		"""AC-29. The enumeration test that pinned three now pins **zero**.

		Read from **Frappe's own registry**, `frappe.guest_methods`, not from an
		attribute: `frappe.whitelist()` sets no `allow_guest` attribute, so
		`getattr(fn, "allow_guest", False)` is always False and an assertion
		written that way can never fail.
		"""
		import inspect

		for module in (joiner_public, joiner_invite, hk):
			guests = [name for name, fn in inspect.getmembers(module, inspect.isfunction)
			          if fn in frappe.guest_methods]
			with self.subTest(module=module.__name__):
				self.assertEqual(guests, [],
					"Pre-onboarding has a guest endpoint again: %s. The whole "
					"point of the login was that the public write surface went "
					"to zero." % guests)


# ── US-7, US-8, US-9, US-13 · filling it in and sending it ─────────────────

class TestTheForm(_Base):
	def test_the_endpoints_take_no_identifier(self):
		"""AC-45. A **static** test, because the claim is about the signatures:
		*"there is no submission argument anywhere in this module"*. It is what
		makes "a caller cannot reach another person's row" a fact rather than a
		promise about every code path."""
		import inspect

		banned = {"submission", "row", "name", "docname", "employee", "user",
		          "web_form_request_key", "key", "token"}
		for fname, fn in inspect.getmembers(joiner_public, inspect.isfunction):
			if fn not in frappe.whitelisted:
				continue
			args = set(inspect.signature(fn).parameters)
			with self.subTest(endpoint=fname):
				self.assertEqual(args & banned, set(),
					"%s takes %s. Resolve the row from frappe.session.user."
					% (fname, sorted(args & banned)))

	def test_the_draft_is_on_the_row_and_nowhere_else(self):
		"""AC-31. No new doctype and no new field holds a draft: a draft is the
		row with `status = Invited` and `submitted_at` empty."""
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		joiner_public.save_draft(values=frappe.as_json({
			"cell_number": "+91 90000 00001",
			"personal_email": "s079priya@example.com",
			# Not ticked, so it must be dropped silently rather than refused.
			"relation": "sister",
		}))
		frappe.set_user("Administrator")
		row = frappe.get_doc(DOCTYPE, doc.name)
		self.assertEqual(row.mobile, "+91 90000 00001")
		self.assertEqual(row.personal_email, "s079priya@example.com")
		self.assertFalse(row.emergency_relation,
			"A field nobody ticked must not be written, and must not be refused "
			"either - an error naming a field somebody guessed at tells them it "
			"exists.")
		self.assertEqual(row.status, "Invited")
		self.assertFalse(row.submitted_at)

	def test_the_counts_come_back_real(self):
		"""AC-30. *"nothing was lost"* is a claim; *"2 of 4"* is a fact."""
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		joiner_public.save_draft(values=frappe.as_json({"cell_number": "+91 90000 00002"}))
		back = joiner_public.open_invite()
		frappe.set_user("Administrator")
		# full_name is always asked, and it is pre-filled from HR's entry.
		self.assertEqual(back["answers_total"], 1 + len(fx.ASKED))
		self.assertEqual(back["answers_done"], 2)

	def test_a_document_already_sent_comes_back_as_sent(self):
		"""AC-30's other half, and the gap this test was written for: a joiner
		coming back on a second visit saw every document as *"nothing yet"*,
		because the screen started from an empty list - while the strip beside it
		said "1 of 1 sent". Worse than either answer on its own.

		The mapping from a stored file to a document type is worked out on the
		**server**, because the server is the only side that knows how the file
		was named.
		"""
		fx.a_document_type(required=True)
		doc, _out = self._sign_in()
		fx.attach_a_file(doc.name)
		self._as_the_joiner(doc)
		page = joiner_public.open_invite()
		# And a compulsory document that has arrived no longer blocks the send.
		joiner_public.submit_invite(values=frappe.as_json({"cell_number": "+91 9"}))
		frappe.set_user("Administrator")
		self.assertEqual(page["sent"], [fx.DOC_NAME])
		self.assertEqual(page["documents_done"], 1)
		self.assertEqual(page["documents_total"], 1)
		self.assertEqual(frappe.db.get_value(DOCTYPE, doc.name, "status"), "Submitted")

	def test_the_document_types_reach_a_joiner_at_all(self):
		"""The one a permission would have broken silently.

		**A joiner holds read on `Employee Document Type` nowhere** - their role
		appears in no permission row at all, which is the whole design. So
		reading the ticked list through `frappe.get_all`, as
		`employee_documents_read.ticked_types()` does, returns an empty list to
		the one caller that needs it: the form would never ask for a document and
		every upload would be refused as "not one we asked for", with nothing in
		any log.
		"""
		fx.a_document_type()
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		page = joiner_public.open_invite()
		frappe.set_user("Administrator")
		self.assertEqual([d["name"] for d in page["documents"]], [fx.DOC_NAME])

	def test_send_is_refused_until_what_hr_marked_is_answered(self):
		"""AC-38, AC-39. **A refusal costs the joiner nothing**: nothing is sent,
		nothing is burned, they stay signed in.

		It saves a draft first, and that is the real sequence rather than a
		convenience: the joiner presses Next before they reach Check and send.
		It also matters for what can honestly be asserted - a refused
		`submit_invite` throws **before** the write, so it stores nothing at all.
		AC-38's *"every input still holds what was typed"* is a promise about the
		BROWSER; the promise about the row is that a refusal does not destroy
		what was already kept, and that is what this asserts.
		"""
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		joiner_public.save_draft(values=frappe.as_json(
			{"personal_email": "s079priya@example.com"}))
		with self.assertRaises(frappe.ValidationError):
			joiner_public.submit_invite(values=frappe.as_json(
				{"personal_email": "s079priya@example.com"}))
		frappe.set_user("Administrator")
		row = frappe.get_doc(DOCTYPE, doc.name)
		self.assertEqual(row.status, "Invited")
		self.assertFalse(row.submitted_at)
		# The draft survived the refusal, and the session is untouched.
		self.assertEqual(row.personal_email, "s079priya@example.com")
		self.assertEqual(frappe.db.get_value("User", doc.user, "enabled"), 1)

	def test_no_field_name_is_required_by_us(self):
		"""AC-39, decision 2. **The only required list is the one HR ticked.**"""
		frappe.db.set_default("alvoraa_joiner_required_fields", "")
		frappe.db.commit()
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		joiner_public.submit_invite(values=frappe.as_json({"cell_number": "+91 1"}))
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value(DOCTYPE, doc.name, "status"), "Submitted")

	def test_a_required_mark_cannot_widen_what_is_asked(self):
		"""AC-40, 078-SEC-18. A name on the required list that is not being asked
		for is ignored at the READER as well as refused at the setter - and the
		reader is the only half that survives a future UI."""
		frappe.db.set_default("alvoraa_joiner_required_fields",
		                      "cell_number,emergency_phone_number")
		frappe.db.commit()
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		asked = {f["name"] for f in joiner_public.open_invite()["fields"]}
		frappe.set_user("Administrator")
		self.assertNotIn("emergency_phone_number", asked)
		_a, required = people_fields.asked_and_required(
			"alvoraa_joiner_fields", "alvoraa_joiner_required_fields")
		self.assertEqual(set(required), {"cell_number"})

	def test_bringing_it_on_the_first_day_is_a_real_answer(self):
		"""AC-42, AC-43. A compulsory document is **answered, never had**: a
		joiner may not own it yet, may be on somebody else's phone, or may not be
		able to scan anything."""
		fx.a_document_type(required=True)
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		# Without an answer it refuses, and the document is named.
		with self.assertRaises(frappe.ValidationError):
			joiner_public.submit_invite(values=frappe.as_json({"cell_number": "+91 2"}))
		joiner_public.submit_invite(values=frappe.as_json({"cell_number": "+91 2"}),
		                            bringing=frappe.as_json([fx.DOC_NAME]))
		frappe.set_user("Administrator")
		row = frappe.get_doc(DOCTYPE, doc.name)
		self.assertEqual(row.status, "Submitted")
		self.assertIn(fx.DOC_NAME, row.bring_on_day_one)

	def test_send_ends_the_form_and_not_the_sign_in(self):
		"""AC-72 to AC-75, **decision 4a**, which reverses 079-SEC-5's first row
		and M3's default. Somebody who finds their PAN card the next evening
		should not have to ring HR."""
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		joiner_public.submit_invite(values=frappe.as_json({"cell_number": "+91 3"}))
		# Still signed in, still holding the role, and the page still answers.
		self.assertEqual(frappe.db.get_value("User", doc.user, "enabled"), 1)
		self.assertTrue(frappe.db.exists("Has Role", {"parent": doc.user,
		                                             "role": joiner_invite.JOINER_ROLE}))
		again = joiner_public.open_invite()
		self.assertTrue(again["submitted"])
		# The typed answers are read-only to them, and a second Send is refused.
		with self.assertRaises(frappe.ValidationError):
			joiner_public.save_draft(values=frappe.as_json({"cell_number": "+91 4"}))
		with self.assertRaises(frappe.ValidationError):
			joiner_public.submit_invite(values=frappe.as_json({"cell_number": "+91 4"}))
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value(DOCTYPE, doc.name, "mobile"), "+91 3")


# ── US-14 · the endings ────────────────────────────────────────────────────

class TestTheEndings(_Base):
	def _assert_closed(self, user):
		self.assertEqual(frappe.db.get_value("User", user, "enabled"), 0)
		self.assertEqual(frappe.get_all("Has Role", filters={"parent": user,
		                                                     "parenttype": "User"}), [])
		# `tabSessions` is a table, not a DocType, so it is read with SQL - and
		# this is the assertion that matters most, because whether Frappe kills a
		# live session the moment `enabled` goes to 0 is not stated anywhere we
		# could read. That is exactly why the clearing is explicit.
		self.assertEqual(frappe.db.sql(
			"select count(*) from tabSessions where user = %s", (user,))[0][0], 0)

	def test_cancelling_closes_the_account(self):
		doc, _out = self._sign_in()
		frappe.set_user(self.hr)
		joiner_invite.cancel_invite(submission=doc.name, reason="The joiner is not coming")
		frappe.set_user("Administrator")
		self._assert_closed(doc.user)

	def test_being_turned_down_closes_it_at_that_moment(self):
		"""AC-78's last clause: at the moment HR records it, not at the next job
		run. And AC-77: the joiner gets the same answer as every other ending."""
		doc, _out = self._sign_in()
		frappe.set_user(self.hr)
		joiner_invite.cancel_invite(submission=doc.name, reason="They were turned down")
		frappe.set_user("Administrator")
		self._assert_closed(doc.user)

	def test_expiry_closes_the_account_even_after_send(self):
		"""Under 078 this read `Invited` only, because sending burned the link.
		Decision 4a means a `Submitted` row still has a live account."""
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		joiner_public.submit_invite(values=frappe.as_json({"cell_number": "+91 5"}))
		frappe.set_user("Administrator")
		frappe.db.set_value(DOCTYPE, doc.name, "expires_on",
		                    add_to_date(now(), days=-1), update_modified=False)
		frappe.db.commit()
		hk.expire_the_dead_sign_ins()
		self.assertEqual(frappe.db.get_value(DOCTYPE, doc.name, "status"), "Expired")
		self._assert_closed(doc.user)

	def test_being_hired_closes_it_and_never_promotes_it(self):
		"""AC-79, J9. **Closed, never promoted.** Carrying the joiner role onto
		their staff login would lock the new employee out of their own record
		through US-5's own gate - a deliberate failure mode worth a test."""
		doc, _out = self._sign_in()
		frappe.set_user("Administrator")
		row = frappe.get_doc(DOCTYPE, doc.name)
		row.employee = self.rahul
		row.flags.ignore_permissions = True
		row.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value(DOCTYPE, doc.name, "status"),
		                 "Made an employee")
		self._assert_closed(doc.user)
		# Their real staff login is a separate account and holds no joiner role.
		self.assertNotIn(joiner_invite.JOINER_ROLE, frappe.get_roles(self.rahul_user))
		self.assertNotEqual(self.rahul_user, doc.user)

	def test_an_ended_account_gets_one_answer_whichever_ending_it_was(self):
		"""079-SEC-5's "one answer out". A different answer for "turned down"
		would tell a candidate the outcome of their application through a web
		page instead of from their employer."""
		said = set()
		for i, reason in enumerate(("By HR", "They were turned down",
		                            "Sent to the wrong person")):
			doc, _out = self._sign_in(mobile="+91 98100 2000%d" % i,
			                          name="S079 Ending %d" % i)
			frappe.set_user(self.hr)
			joiner_invite.cancel_invite(submission=doc.name, reason=reason)
			# A session captured BEFORE the change is refused.
			frappe.set_user(doc.user)
			try:
				joiner_public.open_invite()
				self.fail("A closed account still opened the form")
			except frappe.PermissionError as e:
				said.add(str(e))
			frappe.set_user("Administrator")
		self.assertEqual(len(said), 1,
			"The endings give different answers: %s" % said)


# ── US-15 · export ─────────────────────────────────────────────────────────

class TestExport(_Base):
	def test_hr_holds_no_report_and_no_export_on_the_doctype(self):
		"""AC-80, AC-81, counsel's ruling 9, and 078 finding F3 turned from
		"accept in writing" into a requirement. A permission-row assertion, so
		an upgrade or a merge that re-widens it goes red.

		Those two rows were a spreadsheet of every joiner's name, mobile,
		personal email, home address and emergency contact - **unlogged**.
		"""
		import json

		path = frappe.get_app_path(
			"alvoraa_portal", "alvoraa_portal", "doctype",
			"alvoraa_joiner_submission", "alvoraa_joiner_submission.json")
		rows = {r["role"]: r for r in json.load(open(path, encoding="utf-8"))["permissions"]}
		for role in ("HR Manager", "HR User"):
			with self.subTest(role=role):
				self.assertFalse(rows[role].get("report"))
				self.assertFalse(rows[role].get("export"))
		# System Manager keeps the only one.
		self.assertTrue(rows["System Manager"].get("export"))

	def test_every_export_writes_exactly_one_line_and_says_if_it_was_masked(self):
		"""AC-82. A table test over **every** export endpoint, so a fourth
		cannot be added without a log line."""
		import io
		import logging

		doc, _out = self._sign_in()
		stream = io.StringIO()
		handler = logging.StreamHandler(stream)
		logger = frappe.logger("alvoraa")
		logger.addHandler(handler)
		# **The level is forced, and the reason is a finding rather than a test
		# detail.** Frappe's default is `WARNING` on a dev server and `ERROR`
		# everywhere else, `DEVSERVER` is unset in our images, and no site in
		# this product sets `log_level` - so NO line below `error` reaches a file
		# at any tenant. This test proves the line exists and is shaped right;
		# whether anybody can read it is configuration, and it is escalated as a
		# blocker for switch-on in `03-implementation-notes.md`.
		was = logger.level
		logger.setLevel(logging.DEBUG)
		frappe.set_user(self.hr)
		try:
			joiner_invite.export_submission(submission=doc.name)
		finally:
			logger.setLevel(was)
			logger.removeHandler(handler)
			frappe.set_user("Administrator")
		lines = [ln for ln in stream.getvalue().splitlines() if "exported" in ln]
		self.assertEqual(len(lines), 1, stream.getvalue())
		self.assertIn("masked=True", lines[0])
		self.assertNotIn(doc.full_name, lines[0])

	def test_there_is_no_bytes_included_export(self):
		"""AC-83. Dropped in the spec's §3: HR sends the files from the row,
		which is a read. A permission surface for a case nobody has reported."""
		doc, _out = self._sign_in()
		frappe.set_user(self.hr)
		joiner_invite.export_submission(submission=doc.name)
		body = frappe.local.response.filecontent.decode("utf-8")
		frappe.set_user("Administrator")
		self.assertIn('"files"', body)
		self.assertNotIn("base64", body)
		self.assertNotIn("content", body)


# ── US-16 · two clocks ─────────────────────────────────────────────────────

class TestTwoClocks(_Base):
	def _with_a_file(self, doc):
		fx.attach_a_file(doc.name)

	def _files(self, doc):
		return frappe.get_all("File", filters={"attached_to_doctype": DOCTYPE,
		                                       "attached_to_name": doc.name},
		                      pluck="name", ignore_permissions=True)

	def _age(self, doc, days, field="closed_on"):
		frappe.db.set_value(DOCTYPE, doc.name, field,
		                    add_to_date(now(), days=-days), update_modified=False)
		frappe.db.commit()

	def test_the_documents_go_at_thirty_one_days_and_the_fields_do_not(self):
		"""AC-84. **The row survives minus its attachments.** This is the whole
		of counsel's ruling 4 and the reason one setting could not do."""
		doc, _out = self._sign_in()
		frappe.db.set_value(DOCTYPE, doc.name, "status", "Cancelled",
		                    update_modified=False)
		self._with_a_file(doc)
		self._age(doc, 31)
		hk._delete_the_documents_sooner()
		self.assertEqual(self._files(doc), [])
		self.assertEqual(frappe.db.get_value(DOCTYPE, doc.name, "full_name"),
		                 "S079 Priya Khanna")

	def test_the_fields_go_at_a_hundred_and_eighty_one_days(self):
		"""AC-85, through the existing `erase()` path."""
		doc, _out = self._sign_in()
		frappe.db.set_value(DOCTYPE, doc.name, "status", "Cancelled",
		                    update_modified=False)
		self._age(doc, 181)
		hk._erase_the_ones_who_did_not_join()
		self.assertFalse(frappe.db.get_value(DOCTYPE, doc.name, "full_name"))

	def test_a_row_nobody_actioned_loses_its_documents_at_the_document_clock(self):
		"""AC-87. **Measured from `creation`, whatever state the row is in** -
		otherwise an ignored submission keeps an identity document until the
		90-day backstop, against counsel's 30 to 60."""
		doc, _out = self._sign_in()
		self._with_a_file(doc)
		self._age(doc, 31, field="creation")
		hk._delete_the_documents_sooner()
		self.assertEqual(self._files(doc), [])
		self.assertEqual(frappe.db.get_value(DOCTYPE, doc.name, "status"), "Invited")

	def test_legal_hold_wins_for_both_clocks(self):
		"""AC-88. Deleting something somebody has asked you to preserve is worse
		than keeping it too long. HR's Purge is the single exception."""
		doc, _out = self._sign_in()
		frappe.db.set_value(DOCTYPE, doc.name, {"status": "Cancelled",
		                                        "legal_hold": 1},
		                    update_modified=False)
		self._with_a_file(doc)
		self._age(doc, 400)
		hk._delete_the_documents_sooner()
		hk._erase_the_ones_who_did_not_join()
		hk._erase_the_untouched()
		self.assertEqual(len(self._files(doc)), 1)
		self.assertEqual(frappe.db.get_value(DOCTYPE, doc.name, "full_name"),
		                 "S079 Priya Khanna")

	def test_each_pass_keeps_its_own_count(self):
		"""AC-89. Without a separate count, *"did the documents actually go"* has
		no answer."""
		doc, _out = self._sign_in()
		frappe.db.set_value(DOCTYPE, doc.name, "status", "Cancelled",
		                    update_modified=False)
		self._with_a_file(doc)
		self._age(doc, 31)
		out = hk.run_daily()
		self.assertIn("documents", out)
		self.assertEqual(out["documents"], 1)

	def test_neither_clock_has_a_value_that_means_for_ever(self):
		"""AC-90. A blank, a 0, a non-number and anything outside counsel's range
		are all refused - **there is no "keep for ever" value to save.**"""
		frappe.set_user(self.sm)
		for bad in ("", "0", "abc", "29", "61", "-1"):
			with self.subTest(value=bad):
				with self.assertRaises(Exception):
					org_settings.set_cover_setting("alvoraa_joiner_document_days", bad)
		org_settings.set_cover_setting("alvoraa_joiner_document_days", "45")
		frappe.set_user("Administrator")
		self.assertEqual(org_settings.get("alvoraa_joiner_document_days"), 45)

	def test_the_notice_prints_both_numbers_separately(self):
		"""AC-92. One sentence covering both clocks would be wrong about one of
		them, and the numbers are the tenant's, never a literal."""
		frappe.db.set_default("alvoraa_joiner_document_days", "45")
		frappe.db.set_default("alvoraa_joiner_not_hired_days", "200")
		frappe.db.commit()
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		page = joiner_public.open_invite()
		frappe.set_user("Administrator")
		self.assertEqual(page["document_days"], 45)
		self.assertEqual(page["not_hired_days"], 200)


# ── US-17 · erased means erased ────────────────────────────────────────────

class TestErasure(_Base):
	def test_nothing_of_theirs_survives_an_erasure(self):
		"""AC-93, AC-94, AC-97. **The one test that settles ⚠ C7 / M1.**

		Generated from the candidate constant, so a new field cannot escape it.
		And **HR edits the row between the submit and the erase**, because
		`track_changes: 1` writes history on HR's own save - without that edit
		the `Version` assertion is vacuous and the whole thing proves nothing.
		"""
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		values = {
			"full_name": "S079 Every Field",
			"cell_number": "+91 90000 99991",
			"personal_email": "s079every@example.com",
			"current_address": "19 Invented Lane, Nowhere",
		}
		joiner_public.save_draft(values=frappe.as_json(values))
		joiner_public.submit_invite(values=frappe.as_json(values))
		frappe.set_user("Administrator")

		fx.attach_a_file(doc.name)

		# **HR's own edit.** It writes a Version row holding the old values, and
		# it is the only thing the sweep can possibly be needed for.
		# **`ignore_version=False`, explicitly, and the test is worthless
		# without it.** Frappe turns version tracking OFF inside a test by
		# default - `self.flags.ignore_version = frappe.in_test if
		# ignore_version is None else ignore_version`
		# (`frappe/model/document.py:576`). So a test that saved the ordinary way
		# would write no history at all, and the sweep below would be asserted
		# against nothing. This is HR saving the row in production.
		row = frappe.get_doc(DOCTYPE, doc.name)
		row.emergency_contact_name = "S079 Someone Else"
		row.save(ignore_permissions=True, ignore_version=False)
		row.emergency_contact_name = "S079 A Third Name"
		row.save(ignore_permissions=True, ignore_version=False)
		frappe.db.commit()
		self.assertTrue(
			frappe.get_all("Version", filters={"ref_doctype": DOCTYPE,
			                                   "docname": doc.name},
			               ignore_permissions=True),
			"HR's edit wrote no history, so this test cannot prove the sweep "
			"works. Check `track_changes` before changing the assertion below.")

		account = doc.user
		self.assertTrue(erase(doc.name, why="a test"))

		shell = frappe.get_doc(DOCTYPE, doc.name)
		for field in JOINER_FIELDS:
			with self.subTest(field=field):
				self.assertFalse(shell.get(field))
		self.assertFalse(shell.bring_on_day_one)
		self.assertTrue(shell.erased_on)
		# The shell survives, and holds nothing about the person.
		self.assertTrue(shell.invited_by)
		self.assertTrue(shell.status)

		self.assertEqual(frappe.get_all("File", filters={
			"attached_to_doctype": DOCTYPE, "attached_to_name": doc.name},
			ignore_permissions=True), [])

		# **By query, against the database.**
		kept = frappe.db.sql(
			"""select count(*) from tabVersion
			   where ref_doctype = %s and docname = %s""", (DOCTYPE, doc.name))[0][0]
		self.assertEqual(kept, 0,
			"Values we told somebody we had deleted are still in tabVersion. "
			"Until this is 0, both of counsel's clocks are a claim.")

		self.assertFalse(frappe.db.exists("User", account))
		# **No `Deleted Document` holding the ACCOUNT, and none holding their
		# NAME** - which is what 079-PRIV-2 clause 4 is about: the point of
		# `delete_permanently=True` is that Frappe keeps no JSON copy.
		#
		# Scoped to `deleted_doctype = "User"` on purpose, and the reason is
		# worth knowing: `User.on_trash` deletes the account's
		# `Notification Settings`, which is named after the login id, so a row
		# with that `deleted_name` survives for a different doctype. It holds
		# nothing about the person - the login id is opaque and non-routable by
		# construction (079-SEC-1 clause 4) - and it is recorded as a known
		# residue in `03-implementation-notes.md` rather than chased.
		self.assertFalse(frappe.db.exists("Deleted Document",
		                                  {"deleted_doctype": "User",
		                                   "deleted_name": account}))
		for row in frappe.get_all("Deleted Document", fields=["data"],
		                          limit_page_length=0, ignore_permissions=True):
			self.assertNotIn("S079 Every Field", row.data or "",
				"A Deleted Document is holding a JSON copy of the person's name.")
		for value in values.values():
			with self.subTest(value=value):
				self.assertEqual(frappe.db.sql(
					"""select count(*) from `tabEmail Queue`
					   where message like %s""", ("%" + value + "%",))[0][0], 0)

	def test_the_joiners_own_saves_write_no_history_at_all(self):
		"""AC-95. The sweep is not belt and braces: an audit trail of *who issued
		and closed an invite* does not need the person's telephone number in it,
		so the two saves that carry personal data opt out in the first place.

		**`frappe.in_test` is turned off for the duration, and that is the whole
		test.** Frappe disables version tracking inside a test by default
		(`frappe/model/document.py:576`), so asserting "no rows" in the ordinary
		way would pass whatever the product did - and it did pass, for months of
		my own writing, while the code underneath was setting a flag that `save()`
		then overwrote. With the harness's own default out of the way, the only
		thing stopping a row here is the `ignore_version=True` we pass.
		"""
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		was = frappe.in_test
		frappe.in_test = False
		try:
			joiner_public.save_draft(values=frappe.as_json({"cell_number": "+91 7"}))
			joiner_public.submit_invite(values=frappe.as_json({"cell_number": "+91 7"}))
		finally:
			frappe.in_test = was
			frappe.set_user("Administrator")
		self.assertEqual(frappe.get_all("Version", filters={
			"ref_doctype": DOCTYPE, "docname": doc.name},
			ignore_permissions=True), [],
			"The joiner's own answers went into tabVersion, where the erasure we "
			"promise them does not reach.")

	def test_hrs_own_edits_still_write_history(self):
		"""AC-96. `track_changes` is NOT turned off: §14's promise to reconstruct
		who did what a year later depends on it."""
		doc, _out = self._sign_in()
		row = frappe.get_doc(DOCTYPE, doc.name)
		row.emergency_contact_name = "S079 Edited By HR"
		# `ignore_version=False` because Frappe turns tracking off in a test -
		# see `test_nothing_of_theirs_survives_an_erasure`. This is HR's save as
		# it happens in production.
		row.save(ignore_permissions=True, ignore_version=False)
		frappe.db.commit()
		self.assertTrue(frappe.get_all("Version", filters={
			"ref_doctype": DOCTYPE, "docname": doc.name}, ignore_permissions=True))

	def test_purge_works_and_ignores_legal_hold_on_purpose(self):
		"""AC-99. Counsel's ruling 8 in code, and **it had no test at all** until
		now (078 D5, R-8). The hold exists to stop a CLOCK deleting something
		somebody wants preserved, not to override a human acting on a request."""
		doc, _out = self._sign_in()
		frappe.db.set_value(DOCTYPE, doc.name, "legal_hold", 1, update_modified=False)
		frappe.db.commit()
		frappe.set_user(self.hr)
		out = joiner_invite.purge_submission(submission=doc.name)
		frappe.set_user("Administrator")
		self.assertTrue(out["erased"])
		row = frappe.get_doc(DOCTYPE, doc.name)
		self.assertFalse(row.full_name)
		self.assertTrue(row.erased_on)
		self.assertEqual(row.erased_why, "HR purged it on request")


# ── US-18, US-19 · My Profile and the settings ─────────────────────────────

class TestMyProfileAndTheSettings(_Base):
	def test_a_save_goes_through_with_something_still_needed(self):
		"""AC-100, decision 3. *Blocking would mean somebody with no permanent
		address could never change anything on that page again - not even their
		own phone number - and their only way out is a call to HR.*"""
		frappe.db.set_default("alvoraa_my_profile_fields",
		                      "cell_number,current_address")
		frappe.db.set_default("alvoraa_my_profile_required_fields",
		                      "cell_number,current_address")
		frappe.db.set_value("Employee", self.rahul, "current_address", "",
		                    update_modified=False)
		frappe.db.commit()
		frappe.set_user(self.rahul_user)
		out = my_profile.save_my_profile(values=frappe.as_json(
			{"cell_number": "+91 90000 00123"}))
		page = my_profile.get_my_profile()
		frappe.set_user("Administrator")
		self.assertEqual(out["saved"], 1)
		self.assertEqual(frappe.db.get_value("Employee", self.rahul, "cell_number"),
		                 "+91 90000 00123")
		marks = {f["fieldname"]: f["needed"] for f in page["fields"]}
		self.assertTrue(marks["current_address"])
		self.assertTrue(marks["cell_number"])

	def test_the_joiner_candidate_list_is_the_same_six_by_identity(self):
		"""AC-104. The prototype drew **sixteen** rows, including bank account
		and IFSC. **The drawing was wrong, not the code** (decision 6b): offering
		those would give an employee self-service write on their own bank
		details, which is how payroll fraud happens."""
		self.assertIs(
			people_fields.LIST_KEYS["alvoraa_joiner_fields"],
			people_fields.MY_PROFILE_WRITE_FIELDS)
		frappe.set_user(self.sm)
		card = people_settings.get_people_settings()
		frappe.set_user("Administrator")
		self.assertEqual(card["joiner_choices"],
		                 list(people_fields.MY_PROFILE_WRITE_FIELDS))
		for banned in ("bank_ac_no", "ifsc_code", "date_of_birth",
		               "permanent_address", "ctc", "pan_number"):
			with self.subTest(field=banned):
				self.assertNotIn(banned, card["joiner_choices"])

	def test_full_name_is_not_a_ticked_field(self):
		"""AC-104's second half. It is HR's own entry at invite, pre-filled on the
		form, correctable by the joiner, and **never made compulsory by a
		tick** - making it required would be a rule of ours."""
		self.assertNotIn("full_name", people_fields.MY_PROFILE_WRITE_FIELDS)
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		rows = {f["name"]: f for f in joiner_public.open_invite()["fields"]}
		frappe.set_user("Administrator")
		self.assertIn("full_name", rows)
		self.assertFalse(rows["full_name"]["required"])
		self.assertEqual(rows["full_name"]["value"], "S079 Priya Khanna")

	def test_every_deny_name_is_refused_at_the_setter(self):
		"""AC-106. Including **made-up statutory field names**, so the assertion
		is never vacuous on a site without the India regional pack installed."""
		frappe.set_user(self.sm)
		for bad in ("bank_ac_no", "ifsc_code", "date_of_birth", "ctc",
		            "aadhaar_no", "pan_card_number", "uan", "permanent_address"):
			for key in ("alvoraa_joiner_fields", "alvoraa_joiner_required_fields",
			            "alvoraa_my_profile_required_fields"):
				with self.subTest(field=bad, key=key):
					with self.assertRaises(Exception):
						org_settings.set_cover_setting(key, bad)
		frappe.set_user("Administrator")

	def test_a_compulsory_detail_nobody_is_asked_for_is_refused(self):
		"""AC-40's setter half. A required mark on a detail that is not being
		asked for cannot mean anything."""
		frappe.db.set_default("alvoraa_joiner_fields", "cell_number")
		frappe.db.commit()
		frappe.set_user(self.sm)
		with self.assertRaises(Exception):
			org_settings.set_cover_setting("alvoraa_joiner_required_fields",
			                               "current_address")
		frappe.set_user("Administrator")

	def test_a_fresh_site_asks_a_joiner_for_nothing(self):
		"""AC-107. **All four tick keys ship empty**, which is the safest value at
		every existing tenant: nothing changes until a System Manager ticks
		something."""
		for key in ("alvoraa_joiner_fields", "alvoraa_joiner_required_fields",
		            "alvoraa_my_profile_required_fields",
		            "alvoraa_joiner_required_documents", "alvoraa_joiner_notice_text"):
			with self.subTest(key=key):
				self.assertEqual(org_settings.DEFAULTS[key], "")
		self.assertEqual(org_settings.DEFAULTS["alvoraa_joiner_document_days"], 30)
		frappe.db.set_default("alvoraa_joiner_fields", "")
		frappe.db.set_default("alvoraa_joiner_required_fields", "")
		frappe.db.commit()
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		page = joiner_public.open_invite()
		frappe.set_user("Administrator")
		# Only `full_name`, which is HR's own entry rather than a tick.
		self.assertEqual([f["name"] for f in page["fields"]], ["full_name"])

	def test_the_new_keys_are_system_manager_only(self):
		"""§7.1. An HR Manager is refused and logged, because these keys decide
		what a stranger is asked for and how long it is kept."""
		frappe.set_user(self.hr)
		for key in ("alvoraa_joiner_fields", "alvoraa_joiner_required_fields",
		            "alvoraa_my_profile_required_fields",
		            "alvoraa_joiner_required_documents",
		            "alvoraa_joiner_document_days", "alvoraa_joiner_notice_text"):
			with self.subTest(key=key):
				self.assertIn(key, org_settings.ACCESS_GRANTING)
				with self.assertRaises(Exception):
					org_settings.set_cover_setting(key, "cell_number")
		frappe.set_user("Administrator")

	def test_the_hr_contact_can_finally_be_set(self):
		"""The gap nobody had noticed: `alvoraa_hr_contact_phone` and `_email`
		were read by every joiner screen since 078 and written by **nothing but a
		test**, so at every real tenant the page would have refused to render for
		ever. They are ordinary cover settings - a phone number is HR's own
		detail, not a decision about who sees whom."""
		for key in ("alvoraa_hr_contact_phone", "alvoraa_hr_contact_email"):
			with self.subTest(key=key):
				self.assertIn(key, org_settings.DEFAULTS)
				self.assertIn(key, org_settings.LABELS)
				self.assertNotIn(key, org_settings.ACCESS_GRANTING)
		frappe.set_user(self.hr)
		org_settings.set_cover_setting("alvoraa_hr_contact_phone", "+91 11 4000 0079")
		frappe.set_user("Administrator")
		self.assertEqual(joiner_invite.hr_contact()["phone"], "+91 11 4000 0079")


# ── US-21, US-25 · the notice, and the one number HR glances at ────────────

class TestTheNoticeAndTheCount(_Base):
	def test_no_words_no_form(self):
		"""AC-111. The page refuses to render without the employer's own words,
		exactly as it already refuses with no contact. **That makes the notice a
		precondition without inventing a new precondition mechanism.**"""
		doc, _out = self._sign_in()
		frappe.db.set_default("alvoraa_joiner_notice_text", "")
		frappe.db.commit()
		self._as_the_joiner(doc)
		with self.assertRaises(frappe.ValidationError):
			joiner_public.open_invite()
		frappe.set_user("Administrator")

	def test_the_notice_is_the_employers_own_words(self):
		"""AC-112. Counsel's ruling 6: the notice belongs to the Fiduciary."""
		doc, _out = self._sign_in()
		self._as_the_joiner(doc)
		page = joiner_public.open_invite()
		frappe.set_user("Administrator")
		self.assertEqual(page["notice"],
		                 fx.TENANT["alvoraa_joiner_notice_text"])
		self.assertTrue(page["contact"].get("phone"))

	def test_the_invariant_is_still_there(self):
		"""AC-118. **No new tool**: two numbers we already have. More submissions
		than sign-ins means one credential is being used by several people."""
		frappe.set_user(self.hr)
		out = hk.joiner_counts(days=7)
		frappe.set_user("Administrator")
		self.assertIn("invariant_holds", out)
		self.assertTrue(out["invariant_holds"])


# ── The page itself ────────────────────────────────────────────────────────

class TestTheJoiningPage(_Base):
	"""**Does it render at all?** Nothing else asks.

	The page is a standalone document full of Jinja - `{{ _("…") | tojson }}`
	inside a `<script>`, a conditional refusal block, the tenant's colour in a
	CSS variable - and a single mistake in any of it is a dead form on the one
	screen in this product used by somebody who cannot ring our helpdesk. There
	is no browser test for this page yet (named as a gap in
	`03-implementation-notes.md` §7), so this is the floor: it compiles, it
	renders, and the four properties that must hold in the markup do.
	"""

	@staticmethod
	def _render(one_page=False, keep_comments=False):
		"""The page as the browser receives it, **with the comments taken out.**

		That is not tidying. This page's own comments explain what 079 removed -
		the token, the `#t=` fragment, `localStorage`, `replaceState` - and they
		name `hrms-employee.html` while explaining why the assets are inline. An
		HTML comment is served to the browser, so a test that searched the raw
		output for those words would find them in the paragraph saying they are
		gone and go red for the opposite of the right reason.

		What the browser RUNS is what is being asserted, so that is what the
		assertions read.
		"""
		import os
		import re

		from frappe.utils.jinja import get_jenv

		body = open(os.path.join(frappe.get_app_path("alvoraa_portal"), "www",
		                         "joining.html"), encoding="utf-8").read()
		out = get_jenv().from_string(body).render(
			tenant_name="S079 Employer", brand_colour="#1f6feb", lang="en",
			one_page=one_page)
		if keep_comments:
			return out
		out = re.sub(r"<!--.*?-->", "", out, flags=re.S)
		return re.sub(r"/\*.*?\*/", "", out, flags=re.S)

	def test_it_renders(self):
		out = self._render()
		self.assertIn("Before your first day", out)
		self.assertIn("joiner_public.", out)
		self.assertNotIn("{{", out, "Jinja was left unrendered on the page.")
		self.assertNotIn("{%", out)

	def test_the_documents_step_sends_people_to_uidais_masked_download(self):
		"""Slice 079 §6d. These words are the WHOLE of the Aadhaar control.

		There is no masker, nothing checks the upload and nothing refuses an
		unmasked card - Surbhi dropped US-11 and US-12 on 2 Nov 2026 and chose
		guidance instead. So if this sentence goes, the control goes with it and
		nothing else notices.

		**The negative assertion is the one that matters.** UIDAI's Secure QR
		carries only the last four digits, so the masked download really is
		masked. But OLDER prints used QR formats that could hold the full number
		in plain text, so a photograph of an old card with the digits inked over
		still hands us all twelve. "Cover the digits yourself" is the helpful
		rewrite of this instruction, and it is the one that fails.
		"""
		out = self._render()
		self.assertIn("masked Aadhaar from the UIDAI website", out,
		              "The documents step no longer sends people to UIDAI's masked "
		              "download. That sentence is the only Aadhaar control there is.")
		self.assertIn("Do not black out the numbers yourself", out,
		              "The warning against self-masking is gone. An older card's QR "
		              "can still carry all twelve digits under the ink.")

	def test_the_notice_comes_before_the_first_input_in_the_dom(self):
		"""AC-112, the same property the 078 browser test asserts for My
		Profile's notice with `compareDocumentPosition`. Here it is asserted on
		the markup, because the page has no browser test yet - **before the first
		question, not under a tick at the end.**"""
		out = self._render()
		notice = out.find('id="j0-notice"')
		inputs = [i for i in (out.find("<input"), out.find("<textarea")) if i > 0]
		self.assertGreater(notice, 0, "The notice block is not on the page.")
		self.assertLess(notice, min(inputs),
			"The notice comes after the first input. It has to be the first "
			"thing a stranger reads.")

	def test_the_three_sentences_we_write_are_there(self):
		"""AC-113. The employer should not have to write these, and a person
		given a login reasonably expects to sign back in and look - so if we do
		not say otherwise we have misled them."""
		out = self._render()
		for sentence in ("opens this one page and nothing else",
		                 "What you send is sent",
		                 "ask your employer"):
			with self.subTest(sentence=sentence):
				self.assertIn(sentence, out)

	def test_it_never_promises_that_WE_mask_anything(self):
		"""AC-113's closing clause, kept after its mechanism stopped working.

		**This test used to say "the page must not mention Aadhaar at all",
		and that was right while we said nothing.** US-11 and US-12 were held,
		so the page named Aadhaar nowhere. On 2 November 2026 Surbhi dropped the
		masker for good and chose guidance instead (006d), so the page now names
		Aadhaar on purpose and the old assertion was pinning a decision she had
		reversed.

		**What survives is the property the old test existed for**, and it is
		the one that would actually hurt: the joiner must never be told that
		ALVORA masks anything. Nothing masks, nothing checks, and nothing
		refuses an unmasked card. A page implying otherwise would leave somebody
		relying on a protection that is not there - worse than saying nothing.

		So the words we DO show must stay in the imperative, addressed to the
		joiner. `test_the_documents_step_sends_people_to_uidais_masked_download`
		pins that they are present; this pins that they never become a promise.
		"""
		out = self._render().lower()
		for promise in ("we will mask", "we mask", "we black out",
		                "we will black out", "we hide", "we will hide",
		                "first 8 digits", "first eight digits",
		                "automatically masked", "is masked for you"):
			with self.subTest(promise=promise):
				self.assertNotIn(promise, out,
				                 "The page implies Alvora does the masking. It does "
				                 "not: there is no masker, nothing checks the upload "
				                 "and nothing refuses an unmasked card (079 6d).")

	def test_nothing_of_the_token_or_the_browser_draft_is_left(self):
		"""The subtraction, asserted rather than claimed. `localStorage` and
		`web_form_request_key` were both on this page in 078; the login replaced
		the first and removed the second."""
		out = self._render()
		for gone in ("localStorage", "sessionStorage", "web_form_request_key",
		             "#t=", "replaceState"):
			with self.subTest(gone=gone):
				self.assertNotIn(gone, out)

	def test_the_one_page_refusal_is_drawn_only_when_the_gate_sent_them(self):
		"""AC-21. One button, and it works. No page name, no menu, no count."""
		plain = self._render(one_page=False)
		refused = self._render(one_page=True)
		self.assertNotIn("JOIN-ONEPAGE", plain)
		self.assertIn("JOIN-ONEPAGE", refused)
		self.assertIn("This sign-in only opens your joining form", refused)
		self.assertIn('href="/joining"', refused)
		for leak in ("hrms-employee", "goals-portal", "/app"):
			with self.subTest(leak=leak):
				self.assertNotIn(leak, refused)

	def test_the_old_page_is_gone(self):
		"""P1, the rename. It was free exactly once - the feature ships off at
		every tenant, so nothing points at the old address - and it will never be
		free again."""
		import os

		root = os.path.join(frappe.get_app_path("alvoraa_portal"), "www")
		for gone in ("joiner.html", "joiner.py"):
			with self.subTest(gone=gone):
				self.assertFalse(os.path.exists(os.path.join(root, gone)))


class TestTheRoleReachesANewSite(_Base):
	"""The role must arrive on a site built from scratch, not only on one migrated.

	This is the bug these tests exist for. The `Alvoraa Joiner` role was created
	only by `patches/v1_0/joiner_sign_in_replaces_the_link.py`, and **Frappe marks
	every patch as already done when a site is built from scratch**. So no new
	site ever ran it: `joiner_invite._role()` then refused every invite with "this
	site has not finished setting up pre-onboarding". CI builds a fresh site each
	run and reported it as 79 errors from 2 November; a tenant provisioned after
	079 would have hit the same wall the day the form was switched on.
	"""

	def test_make_role_is_registered_in_after_install(self):
		"""The one line that fixes it, pinned. A patch is for sites that already
		exist; after_install is for one being born. Both are needed, and the
		precedent is `announcements.make_role`, which 079's own comment cites."""
		self.assertIn(
			"alvoraa_portal.joiner_invite.make_role",
			frappe.get_hooks("after_install", app_name="alvoraa_portal") or [],
			"A new site would have no Alvoraa Joiner role, and every joiner "
			"invite on it would refuse. The patch cannot reach a fresh site.")

	def test_make_role_creates_it_with_the_desk_shut(self):
		"""Run on a site where it is missing, it comes back - and with no desk
		access, because giving the role to a joiner must never make them a desk
		user."""
		if frappe.db.exists("Role", joiner_invite.JOINER_ROLE):
			frappe.delete_doc("Role", joiner_invite.JOINER_ROLE,
			                  force=True, ignore_permissions=True)
		joiner_invite.make_role()
		self.assertTrue(frappe.db.exists("Role", joiner_invite.JOINER_ROLE))
		self.assertEqual(
			0, frappe.db.get_value("Role", joiner_invite.JOINER_ROLE, "desk_access"))

	def test_it_shuts_the_desk_on_a_role_that_already_exists(self):
		"""Frappe creates a role WITH desk access the first time it meets the
		name in a permission row. If that ever happened, the second run must take
		the desk away rather than leave it and return."""
		joiner_invite.make_role()
		frappe.db.set_value("Role", joiner_invite.JOINER_ROLE, "desk_access", 1)
		joiner_invite.make_role()
		self.assertEqual(
			0, frappe.db.get_value("Role", joiner_invite.JOINER_ROLE, "desk_access"))

	def test_make_role_runs_twice_without_complaint(self):
		"""Both callers may run it again on any later upgrade."""
		joiner_invite.make_role()
		joiner_invite.make_role()
		self.assertTrue(frappe.db.exists("Role", joiner_invite.JOINER_ROLE))
