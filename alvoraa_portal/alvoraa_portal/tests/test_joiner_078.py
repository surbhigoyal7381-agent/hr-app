"""078 step 6 - pre-onboarding, re-keyed onto slice 079's sign-in.

**The token is gone, so the token tests are gone.** Slice 078 handed the joiner
a bearer link: a key in a URL fragment, stored in clear in Frappe's own
`Web Form Request`, against an unpublished `Web Form` record that existed only
so the request row had something to point at. Counsel's advice of 31 October and
Surbhi's decision of 1 November replaced all of it with a **restricted login**,
because a login identifies the person rather than trusting whoever holds a URL.

What that deleted from this file is listed at the bottom of this docstring, with
the reason for each, rather than quietly disappearing from a diff.

**What carries the file now:**

  * **only the closed allow-list is stored**, and an off-list field is dropped
    silently rather than refused - because an error naming a field somebody
    guessed at tells them the field exists;
  * **nothing ever becomes an Employee by itself**, and the naming series does
    not move. The reason is the absence-backfill trap: a back-dated joining date
    makes Frappe mark the person Absent for every day since, and deleting those
    rows does not help;
  * **the retention clocks**, every range check, and the fact that **no setting
    has a value meaning "for ever"**;
  * **the uploads** - magic bytes, the order of the checks, the re-encode that
    strips a photograph's metadata, and the site-wide guest-upload switch that
    stays off;
  * **the page itself**, which still reads nothing from the database, and now
    keeps nothing about the joiner in the browser either.

**Deleted, and why:**

  * `TestTheLink` - the fragment, the parameter name and the link's lifetime.
    There is no link and no token, so there is nothing to keep out of a query
    string and no form key for Frappe's error-snapshot redaction to mask. The
    one test in it whose intent survives - *there is no submission argument
    anywhere on the joiner's path* - is now
    `test_joiner_079.TestTheForm.test_the_endpoints_take_no_identifier`, which
    reads every whitelisted function rather than three named ones.
  * `TestTheClearTextKeyIsShortLived` - all four tests. `Web Form Request.key`
    was the clear-text secret and the purge was the narrowing that made it
    acceptable against 078-SEC-9. Both the secret and the purge are gone, and
    078-SEC-19's recorded deviation ceases to exist rather than being accepted
    again.
  * `TestWhatAStrangerLearns.test_missing_unknown_expired_and_cancelled_are_one_answer`
    and `test_a_used_link_is_indistinguishable_from_an_unknown_one` - both are
    about what a stranger learns from a *key*. The obligation survives in a
    different shape (one answer for every way the access can end, whoever is
    asking) and is
    `test_joiner_079.TestTheEndings.test_an_ended_account_gets_one_answer_whichever_ending_it_was`.
"""

import io

import frappe
import hrms.alvoraa_org_structure.settings as org_settings
from frappe.utils import add_to_date, now

from alvoraa_portal import joiner_housekeeping as hk
from alvoraa_portal import joiner_invite, joiner_public
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_joiner_submission.alvoraa_joiner_submission import (
	COLUMN_FOR_TICK,
	JOINER_FIELDS,
)
from alvoraa_portal.tests import fixtures_078 as fx
from alvoraa_portal.tests.fixtures_045 import Wave4Base, own_user

DOCTYPE = "Alvoraa Joiner Submission"

# The employer's own words. Invented, and short, because the point of the test
# is that they are the TENANT'S and not ours (counsel's ruling 6).
NOTICE = ("We ask for these details so your staff record is ready on your first "
          "day. Only our HR team reads them.")

# The new settings keys this suite writes. `fx.clear_lists()` does not know
# about them - it belongs to 078 and another session owns that file - so they
# are cleared here.
_OUR_KEYS = (
	"alvoraa_joiner_fields",
	"alvoraa_joiner_required_fields",
	"alvoraa_joiner_required_documents",
	"alvoraa_joiner_notice_text",
	"alvoraa_joiner_document_days",
	"alvoraa_my_profile_required_fields",
)


class _Base(Wave4Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.p = fx.people()
		cls.sm_user = own_user("s078sm", ("Employee", "System Manager"))
		# A counter, so every sign-in in the run gets its own number. Two rows
		# can never share one credential (AC-9), so a reused number would refuse
		# the second invite and the failure would look like a product fault.
		cls._nth = 0

	def setUp(self):
		super().setUp()
		fx.clear_lists()
		frappe.db.set_default("alvoraa_joiner_form_on", "1")
		# **The employer's own three values, without which HR cannot invite
		# anybody at all** (US-2). Read raw by `what_the_employer_has_not_set`,
		# so our defaults do not satisfy them: the Fiduciary has to have chosen.
		frappe.db.set_default("alvoraa_joiner_not_hired_days", "180")
		frappe.db.set_default("alvoraa_joiner_document_days", "30")
		frappe.db.set_default("alvoraa_joiner_notice_text", NOTICE)
		# A real contact, because the welcome screen REFUSES to render without
		# one - a notice telling somebody to get in touch, with nobody to get in
		# touch with, is the notice failing at the only thing it is for.
		frappe.db.set_default("alvoraa_hr_contact_phone", "+91 98100 00078")
		# **All six ticked**, deliberately: it is the only way every row of
		# `COLUMN_FOR_TICK` is exercised, and the map between HR's tick names
		# (`Employee`'s own columns) and this doctype's differently-named columns
		# is the kind of thing that breaks silently.
		frappe.db.set_default("alvoraa_joiner_fields",
		                      ",".join(COLUMN_FOR_TICK))
		frappe.db.set_default("alvoraa_joiner_required_fields", "")
		frappe.db.commit()
		# Sign-in by mobile number needs this, and it is **site-wide**: turning
		# it on lets every employee at the tenant sign in with their mobile
		# number too. Surbhi accepted that side effect by name (decision 6b,
		# design D2), so the product refuses a mobile login id while it is off
		# rather than patching it - which means a test has to turn it on.
		self._mobile_login_was = frappe.db.get_single_value(
			"System Settings", "allow_login_using_mobile_number")
		frappe.db.set_single_value("System Settings",
		                           "allow_login_using_mobile_number", 1)
		frappe.db.commit()
		self._made = []
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		self._clear_what_i_made()
		frappe.db.set_default("alvoraa_hr_contact_phone", "")
		frappe.db.set_default("alvoraa_hr_contact_email", "")
		for key in _OUR_KEYS:
			frappe.db.set_default(key, "")
		frappe.db.set_single_value("System Settings",
		                           "allow_login_using_mobile_number",
		                           self._mobile_login_was or 0)
		frappe.db.commit()
		fx.clear_lists()
		super().tearDown()

	def _clear_what_i_made(self):
		"""The rows this test made, their files and their accounts.

		A disabled `User` left behind is not harmless: `_already_a_login` reads
		every account, so a leftover would refuse a later invite on the same
		number and the failure would read as a product fault.
		"""
		for name in self._made:
			if not frappe.db.exists(DOCTYPE, name):
				continue
			account = frappe.db.get_value(DOCTYPE, name, "user")
			for f in frappe.get_all("File", filters={
				"attached_to_doctype": DOCTYPE, "attached_to_name": name,
			}, pluck="name", ignore_permissions=True):
				frappe.delete_doc("File", f, force=True, ignore_permissions=True,
				                  delete_permanently=True)
			frappe.db.delete("Version", {"ref_doctype": DOCTYPE, "docname": name})
			frappe.delete_doc(DOCTYPE, name, force=True, ignore_permissions=True,
			                  delete_permanently=True)
			if account and frappe.db.exists("User", account):
				frappe.delete_doc("User", account, force=True,
				                  ignore_permissions=True, delete_permanently=True)
		self._made = []
		frappe.db.commit()

	# ── the two helpers that replaced the token ─────────────────────────────

	def _sign_in(self, name="S078 Joiner"):
		"""What HR actually does: write the person down, then press the button.

		Returns the submission's name. The reply - the username and the password,
		shown exactly once - is on `self.last`.
		"""
		type(self)._nth += 1
		number = "+91 98100 %05d" % (10000 + type(self)._nth)
		frappe.set_user("Administrator")
		row = frappe.get_doc({
			"doctype": DOCTYPE,
			"status": "Invited",
			"full_name": name,
			# **`login_id`, not `mobile`.** HR's own entry has its own field now.
			# It used to be written into `mobile`, which `COLUMN_FOR_TICK` maps
			# `cell_number` onto - so HR's number arrived as the joiner's own
			# answer, and a field HR marked compulsory was satisfied before the
			# joiner had typed anything. The run that found that is why this
			# field exists.
			"login_id": number,
			"invited_by": self.p["hr_wide_user"],
		}).insert(ignore_permissions=True)
		frappe.db.commit()
		self._made.append(row.name)
		frappe.set_user(self.p["hr_wide_user"])
		self.last = joiner_invite.make_sign_in(submission=row.name)
		frappe.set_user("Administrator")
		return row.name

	def _as_the_joiner(self, submission):
		"""Become the joiner. There is no token to carry - the session IS the
		credential, and the row is found from `frappe.session.user`."""
		frappe.set_user(frappe.db.get_value(DOCTYPE, submission, "user"))

	@staticmethod
	def _answers(**extra):
		"""One value per ticked detail, keyed on HR's TICK NAMES.

		Not the doctype's column names: `cell_number` is stored as `mobile`, and
		posting the column name writes nothing at all - which is exactly what the
		closed allow-list is for.
		"""
		out = {"full_name": "S078 Joiner"}
		for i, tick in enumerate(COLUMN_FOR_TICK):
			out[tick] = "s078value%d" % i
		out.update(extra)
		return out


class TestTheSwitch(_Base):
	def test_it_ships_off(self):
		"""Off for the ordinary reason - a tenant turns a feature on
		deliberately. 078-PRIV-7's SPECIAL precondition is gone, because
		counsel answered the question it existed for on 29 Oct 2026."""
		self.assertEqual(org_settings.DEFAULTS["alvoraa_joiner_form_on"], 0)

	def test_nothing_works_while_it_is_off(self):
		submission = self._sign_in()
		frappe.db.set_default("alvoraa_joiner_form_on", "0")
		frappe.db.commit()
		frappe.set_user(self.p["hr_wide_user"])
		row = frappe.get_doc({
			"doctype": DOCTYPE, "status": "Invited", "full_name": "S078 Nobody",
			"login_id": "+91 98100 99999",
			"invited_by": self.p["hr_wide_user"],
		}).insert(ignore_permissions=True)
		self._made.append(row.name)
		with self.assertRaises(frappe.ValidationError):
			joiner_invite.make_sign_in(submission=row.name)
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.get_value(DOCTYPE, row.name, "user"),
		                 "no account may be made while the feature is off")
		# And the joiner whose sign-in already existed gets the dead-page answer.
		self._as_the_joiner(submission)
		with self.assertRaises(frappe.PermissionError):
			joiner_public.open_invite()
		frappe.set_user("Administrator")

	def test_a_joiner_cannot_tell_whether_it_is_off_or_their_access_has_ended(self):
		"""Whether a feature is switched on is not a stranger's business either,
		so it is the same answer as an ended sign-in - byte for byte."""
		live = self._sign_in()
		ended = self._sign_in("S078 Ended")
		frappe.set_user(self.p["hr_wide_user"])
		joiner_invite.cancel_invite(submission=ended, reason="By HR")
		frappe.set_user("Administrator")

		frappe.db.set_default("alvoraa_joiner_form_on", "0")
		frappe.db.commit()
		self._as_the_joiner(live)
		with self.assertRaises(frappe.PermissionError) as off:
			joiner_public.open_invite()
		frappe.set_user("Administrator")
		frappe.db.set_default("alvoraa_joiner_form_on", "1")
		frappe.db.commit()
		self._as_the_joiner(ended)
		with self.assertRaises(frappe.PermissionError) as done:
			joiner_public.open_invite()
		frappe.set_user("Administrator")
		self.assertEqual(str(off.exception), str(done.exception))


class TestWhatAStrangerLearns(_Base):
	"""Two of this class's four tests were about an unknown, used or expired
	*key* and are gone with the key - see the module docstring, and
	`test_joiner_079.TestTheEndings` for the obligation in its new shape.
	"""

	def test_guest_reaches_no_endpoint_at_all(self):
		"""**The replacement for every "what does a stranger learn" test, and it
		is a much shorter answer: nothing, because there is no stranger.**

		Slice 078 made this the first public write path in the product. There is
		no public write path now - every endpoint requires a session.
		"""
		self._sign_in()
		frappe.set_user("Guest")
		for call in (joiner_public.open_invite,
		             joiner_public.save_draft,
		             joiner_public.submit_invite,
		             joiner_public.upload_invite_file):
			with self.subTest(endpoint=call.__name__):
				with self.assertRaises(frappe.PermissionError):
					call()
		frappe.set_user("Administrator")

	def test_no_response_carries_anybody_elses_data(self):
		"""AC-124. Not a name, not a count, not an email address, nothing about
		the tenant beyond its own public brand."""
		other = fx.people()["with_photo"]
		other_name = frappe.db.get_value("Employee", other, "employee_name")
		submission = self._sign_in()
		self._as_the_joiner(submission)
		body = frappe.as_json(joiner_public.open_invite())
		frappe.set_user("Administrator")
		self.assertNotIn(other_name, body)
		self.assertNotIn("HR-EMP", body)

	def test_the_joiner_cannot_read_or_list_the_doctype(self):
		"""AC-123, re-keyed. The JSON carries no `Guest` row and no joiner row:
		**the joiner role appears in no doctype's permission rows at all**, which
		is what makes a list read impossible rather than merely scoped. Their own
		row is reached by server code bound to their session.
		"""
		import json
		import os

		import alvoraa_portal

		path = os.path.join(os.path.dirname(alvoraa_portal.__file__),
		                    "alvoraa_portal", "doctype",
		                    "alvoraa_joiner_submission",
		                    "alvoraa_joiner_submission.json")
		j = json.load(open(path, encoding="utf-8"))
		roles = [p["role"] for p in j["permissions"]]
		self.assertNotIn("Guest", roles)
		self.assertNotIn(joiner_invite.JOINER_ROLE, roles)

		submission = self._sign_in()
		self._as_the_joiner(submission)
		# `frappe.get_list`, NOT `frappe.get_all`. get_all ignores permissions by
		# design, so a test written that way passes while proving nothing - and
		# `frappe.client.get_list` is what a caller can actually reach over HTTP.
		with self.assertRaises(frappe.PermissionError):
			frappe.get_list(DOCTYPE, fields=["name", "full_name"])
		frappe.set_user("Administrator")


class TestWhatIsStored(_Base):
	def test_only_the_closed_allow_list_is_stored(self):
		"""078-PRIV-9, AC-108. An off-list field is not stored - and is dropped
		SILENTLY rather than refused, because an error naming a field somebody
		guessed at tells them the field exists."""
		submission = self._sign_in()
		self._as_the_joiner(submission)
		joiner_public.submit_invite(values=frappe.as_json({
			"cell_number": "+91 90000 00078",
			"bank_ac_no": "000111222",
			"ctc": "9900000",
			"date_of_birth": "1990-01-01",
		}))
		frappe.set_user("Administrator")
		doc = frappe.get_doc(DOCTYPE, submission)
		self.assertEqual(doc.mobile, "+91 90000 00078")
		body = frappe.as_json(doc.as_dict())
		for never in ("000111222", "9900000", "1990-01-01"):
			self.assertNotIn(never, body)

	def test_the_allow_list_has_no_bank_salary_or_statutory_field(self):
		for never in ("bank_ac_no", "ctc", "pan_number", "aadhaar",
		              "date_of_birth", "salary"):
			self.assertNotIn(never, JOINER_FIELDS)
		self.assertEqual(len(JOINER_FIELDS), 7)

	def test_the_tick_names_and_the_column_names_are_mapped_both_ways(self):
		"""**New, because 079 introduced the map.** HR ticks `Employee`'s own
		column names and this doctype's columns were named differently in 078, so
		`COLUMN_FOR_TICK` is the join. A wrong entry would silently store
		nothing, which is the worst shape of failure available here.

		`full_name` is deliberately NOT in the map: it is HR's own entry at
		invite, pre-filled on the form, and never made compulsory by a tick.
		"""
		submission = self._sign_in()
		self._as_the_joiner(submission)
		joiner_public.submit_invite(values=frappe.as_json(self._answers()))
		frappe.set_user("Administrator")
		doc = frappe.get_doc(DOCTYPE, submission)
		for i, (tick, column) in enumerate(COLUMN_FOR_TICK.items()):
			with self.subTest(tick=tick, column=column):
				self.assertEqual(doc.get(column), "s078value%d" % i)
		self.assertNotIn("full_name", COLUMN_FOR_TICK)
		meta = frappe.get_meta(DOCTYPE)
		for column in COLUMN_FOR_TICK.values():
			with self.subTest(column=column):
				self.assertTrue(meta.get_field(column),
				                "%s is not a field on this doctype" % column)

	def test_the_joiners_screen_states_the_configured_numbers(self):
		"""AC-106, AC-92. The prototype's 90 days was ours, not counsel's, and a
		notice carrying a number we invented must never reach a joiner.

		**Both clocks, separately.** One sentence covering both would be wrong
		about one of them, which is why there are two settings.
		"""
		frappe.set_user(self.sm_user)
		from alvoraa_portal import people_settings

		people_settings.set_people_setting(key="alvoraa_joiner_not_hired_days",
		                                   value="200")
		people_settings.set_people_setting(key="alvoraa_joiner_document_days",
		                                   value="45")
		frappe.set_user("Administrator")
		submission = self._sign_in()
		self._as_the_joiner(submission)
		d = joiner_public.open_invite()
		frappe.set_user("Administrator")
		self.assertEqual(d["not_hired_days"], 200)
		self.assertEqual(d["document_days"], 45)

	def test_the_notice_is_the_employers_own_words(self):
		"""Counsel's ruling 6: the notice belongs to the Fiduciary, not to us."""
		submission = self._sign_in()
		self._as_the_joiner(submission)
		d = joiner_public.open_invite()
		frappe.set_user("Administrator")
		self.assertEqual(d["notice"], NOTICE)

	def test_the_welcome_screen_refuses_to_render_with_no_contact(self):
		"""078-PRIV-8. It tells the joiner to get in touch, so there has to be
		somebody to get in touch with."""
		submission = self._sign_in()
		frappe.db.set_default("alvoraa_hr_contact_phone", "")
		frappe.db.set_default("alvoraa_hr_contact_email", "")
		company = frappe.db.get_default("company")
		if company:
			frappe.db.set_value("Company", company, "email", None)
		frappe.db.commit()
		self._as_the_joiner(submission)
		with self.assertRaises(frappe.ValidationError):
			joiner_public.open_invite()
		frappe.set_user("Administrator")

	def test_the_screen_refuses_to_render_with_no_notice(self):
		"""079-PRIV-3, and it is the same mechanism as the contact above: **no
		words, no form.** That makes the employer's notice a precondition without
		inventing a new precondition mechanism."""
		submission = self._sign_in()
		frappe.db.set_default("alvoraa_joiner_notice_text", "")
		frappe.db.commit()
		self._as_the_joiner(submission)
		with self.assertRaises(frappe.ValidationError):
			joiner_public.open_invite()
		frappe.set_user("Administrator")


class TestItNeverCreatesAnEmployee(_Base):
	def test_submitting_creates_no_employee_and_does_not_move_the_series(self):
		"""AC-127. The absence-backfill trap is the reason: a back-dated joining
		date makes Frappe mark the person Absent for every day since, and
		deleting those rows does not help."""
		before = frappe.db.count("Employee")
		submission = self._sign_in()
		self._as_the_joiner(submission)
		joiner_public.submit_invite(values=frappe.as_json(self._answers()))
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.count("Employee"), before)
		self.assertFalse(frappe.db.get_value(DOCTYPE, submission, "employee"))

	def test_no_joining_date_is_anywhere_on_the_row(self):
		"""AC-128. Not from the form and not from the submission's own dates."""
		meta = frappe.get_meta(DOCTYPE)
		self.assertFalse([f for f in meta.fields if "joining" in f.fieldname])
		self.assertNotIn("date_of_joining", JOINER_FIELDS)

	def test_linking_the_employee_is_what_moves_it_on(self):
		"""AC-129. Declarative: there is no button to press by accident and no
		endpoint that could be called with somebody else's id."""
		submission = self._sign_in()
		self._as_the_joiner(submission)
		joiner_public.submit_invite(
			values=frappe.as_json({"cell_number": "+91 90000 00375"}))
		frappe.set_user("Administrator")
		doc = frappe.get_doc(DOCTYPE, submission)
		doc.employee = self.p["no_photo"]
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.status, "Made an employee")

	def test_a_terminal_state_cannot_be_revived(self):
		submission = self._sign_in()
		frappe.set_user(self.p["hr_wide_user"])
		joiner_invite.cancel_invite(submission=submission, reason="By HR")
		frappe.set_user("Administrator")
		doc = frappe.get_doc(DOCTYPE, submission)
		doc.status = "Invited"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)


class TestRetention(_Base):
	def _aged(self, days, status="Submitted"):
		"""One submission, aged by `days`, with something in it to erase.

		`creation` and `closed_on` are written with SQL, because `set_value` will
		not move `creation` and a controller save would stamp `closed_on` with
		today. Ageing a row is the one thing a test has to do behind the ORM's
		back.
		"""
		name = self._sign_in()
		frappe.set_user("Administrator")
		doc = frappe.get_doc(DOCTYPE, name)
		doc.status = status
		doc.mobile = "+91 90000 00078"
		doc.flags.ignore_permissions = True
		doc.save(ignore_permissions=True)
		when = add_to_date(now(), days=-days)
		frappe.db.sql(
			"update `tabAlvoraa Joiner Submission` set creation=%s, "
			"closed_on=if(closed_on is null, null, %s) where name=%s",
			(when, when, name))
		frappe.db.commit()
		return name

	def test_counsel_s_defaults(self):
		"""Surbhi's decision, 31 Oct 2026, from counsel's 29 Oct answer - plus
		the **document clock** that counsel's ruling 4 added on 31 October, which
		is the one number a single setting could not carry."""
		self.assertEqual(org_settings.DEFAULTS["alvoraa_joiner_not_hired_days"], 180)
		self.assertEqual(org_settings.DEFAULTS["alvoraa_joiner_backstop_days"], 90)
		self.assertEqual(org_settings.DEFAULTS["alvoraa_joiner_warn_days"], 75)
		self.assertEqual(org_settings.DEFAULTS["alvoraa_joiner_link_days"], 7)
		self.assertEqual(org_settings.DEFAULTS["alvoraa_joiner_document_days"], 30)

	def test_the_not_hired_window_is_range_checked_to_counsels_range(self):
		frappe.set_user(self.sm_user)
		from alvoraa_portal import people_settings

		for bad in ("0", "", "90", "179", "366", "for ever"):
			with self.subTest(bad=bad):
				with self.assertRaises(frappe.PermissionError):
					people_settings.set_people_setting(
						key="alvoraa_joiner_not_hired_days", value=bad)
		people_settings.set_people_setting(key="alvoraa_joiner_not_hired_days",
		                                   value="365")
		frappe.set_user("Administrator")

	def test_the_document_clock_is_range_checked_to_counsels_range(self):
		"""Counsel's ruling 4: **30 to 60 days**, against 180 to 365 for the
		record. 30 is the cautious end and is the shipped default."""
		frappe.set_user(self.sm_user)
		from alvoraa_portal import people_settings

		for bad in ("0", "", "29", "61", "180", "for ever"):
			with self.subTest(bad=bad):
				with self.assertRaises(frappe.PermissionError):
					people_settings.set_people_setting(
						key="alvoraa_joiner_document_days", value=bad)
		people_settings.set_people_setting(key="alvoraa_joiner_document_days",
		                                   value="60")
		frappe.set_user("Administrator")

	def test_the_warning_must_come_before_the_deletion(self):
		"""A warning after the thing it warns about is not a warning."""
		frappe.set_user(self.sm_user)
		from alvoraa_portal import people_settings

		people_settings.set_people_setting(key="alvoraa_joiner_backstop_days",
		                                   value="90")
		with self.assertRaises(frappe.PermissionError):
			people_settings.set_people_setting(key="alvoraa_joiner_warn_days",
			                                   value="90")
		with self.assertRaises(frappe.PermissionError):
			people_settings.set_people_setting(key="alvoraa_joiner_warn_days",
			                                   value="120")
		frappe.set_user("Administrator")

	def test_no_setting_can_mean_keep_for_ever(self):
		"""AC-131d, and 079's AC-90 for the new one. The check-in photo setting
		uses 0 that way; **none of these may**, because counsel's September
		policy prohibits indefinite retention in so many words."""
		frappe.set_user(self.sm_user)
		from alvoraa_portal import people_settings

		for key in ("alvoraa_joiner_not_hired_days",
		            "alvoraa_joiner_backstop_days", "alvoraa_joiner_warn_days",
		            "alvoraa_joiner_document_days"):
			for bad in ("0", ""):
				with self.subTest(key=key, bad=bad):
					with self.assertRaises(frappe.PermissionError):
						people_settings.set_people_setting(key=key, value=bad)
		frappe.set_user("Administrator")

	def test_the_backstop_erases_an_untouched_submission(self):
		name = self._aged(200)
		self.assertTrue(hk._erase_the_untouched())
		doc = frappe.get_doc(DOCTYPE, name)
		self.assertTrue(doc.erased_on)
		self.assertFalse(doc.mobile)
		self.assertFalse(doc.full_name)

	def test_legal_hold_wins_however_old(self):
		"""AC-131a. Deleting something somebody asked you to preserve is worse
		than keeping it too long."""
		name = self._aged(400)
		frappe.db.set_value(DOCTYPE, name, "legal_hold", 1)
		frappe.db.commit()
		hk.run_daily()
		doc = frappe.get_doc(DOCTYPE, name)
		self.assertFalse(doc.erased_on)
		self.assertTrue(doc.mobile)

	def test_a_recent_submission_is_untouched(self):
		name = self._aged(3)
		hk.run_daily()
		self.assertFalse(frappe.db.get_value(DOCTYPE, name, "erased_on"))

	def test_somebody_who_did_not_join_waits_for_counsels_window(self):
		"""Counsel REVERSED "erase the moment the status changes": the employer
		has its own candidate record-keeping duties."""
		name = self._aged(10, status="Cancelled")
		hk._erase_the_ones_who_did_not_join()
		self.assertFalse(frappe.db.get_value(DOCTYPE, name, "erased_on"),
		                 "10 days is inside the 180-day window")
		name2 = self._aged(200, status="Cancelled")
		hk._erase_the_ones_who_did_not_join()
		self.assertTrue(frappe.db.get_value(DOCTYPE, name2, "erased_on"))

	def test_someone_who_joined_has_the_copy_erased(self):
		name = self._aged(1, status="Made an employee")
		self.assertTrue(hk._erase_the_redundant_copies())
		self.assertFalse(frappe.db.get_value(DOCTYPE, name, "mobile"))

	def test_the_erase_takes_the_files_with_it(self):
		"""Counsel by name: a deleted parent that leaves its File rows behind is
		the obvious way to get this wrong, and those files are identity
		documents."""
		submission = self._sign_in()
		f = frappe.get_doc({
			"doctype": "File", "file_name": "s078-joiner-doc.pdf",
			"attached_to_doctype": DOCTYPE, "attached_to_name": submission,
			"is_private": 1, "content": fx._one_page_pdf(),
		}).insert(ignore_permissions=True)
		frappe.db.commit()
		from alvoraa_portal.alvoraa_portal.doctype.alvoraa_joiner_submission.alvoraa_joiner_submission import (
			erase,
		)

		erase(submission, why="test")
		self.assertFalse(frappe.db.exists("File", f.name))

	def test_the_document_clock_takes_the_files_and_leaves_the_fields(self):
		"""**Counsel's ruling 4, and the whole reason there are two clocks.** The
		row survives minus its attachments: an identity document is not a
		candidate record, so it goes at 30 days and the record waits for 180."""
		name = self._aged(31, status="Cancelled")
		f = frappe.get_doc({
			"doctype": "File", "file_name": "s078-identity.pdf",
			"attached_to_doctype": DOCTYPE, "attached_to_name": name,
			"is_private": 1, "content": fx._one_page_pdf(),
		}).insert(ignore_permissions=True)
		frappe.db.commit()
		self.assertEqual(hk._delete_the_documents_sooner(), 1)
		self.assertFalse(frappe.db.exists("File", f.name))
		self.assertTrue(frappe.db.get_value(DOCTYPE, name, "mobile"),
		                "the document clock must not touch the typed fields")
		self.assertFalse(frappe.db.get_value(DOCTYPE, name, "erased_on"))

	def test_the_erase_is_real_deletion_not_a_flag(self):
		"""Counsel's September policy prohibits indefinite soft deletion."""
		name = self._aged(200)
		hk.run_daily()
		doc = frappe.get_doc(DOCTYPE, name)
		for field in JOINER_FIELDS:
			self.assertFalse(doc.get(field), f"{field} survived the erase")
		# **`login_id` goes too, and it is not in `JOINER_FIELDS`.** It is HR's
		# own entry rather than one of HR's ticks, so the generated loop above
		# would never reach it - and it is still that person's telephone number
		# or email address, which is the only thing that decides whether it has
		# to be erased.
		self.assertFalse(doc.get("login_id"),
		                 "the number HR was given survived the erase")
		# The shell that remains carries NO personal data - only who issued the
		# sign-in and when, which is what answers "who invited somebody" a year
		# later and is the judgement recorded in 03-implementation-notes.md.
		self.assertTrue(doc.invited_by)
		self.assertTrue(doc.erased_why)

	def test_hr_is_warned_before_the_backstop_and_only_once(self):
		"""Written so it does not depend on what other tests left behind: it
		asserts about THIS row rather than about the batch's total, because the
		count is across every row that is due."""
		name = self._aged(80)
		self.assertGreaterEqual(hk._warn_hr_before_the_backstop(), 1)
		self.assertTrue(frappe.db.get_value(DOCTYPE, name, "warned_on"))
		hk._warn_hr_before_the_backstop()
		self.assertEqual(
			frappe.db.count("Notification Log", {"document_type": DOCTYPE,
			                                     "document_name": name}), 1,
			"the warning must be sent once, not every night")

	def test_the_invariant_hr_watches(self):
		"""OPS-28. Submissions must never exceed sign-ins made: more means one
		credential is being used by several people."""
		frappe.set_user(self.p["hr_wide_user"])
		out = hk.joiner_counts(days=7)
		frappe.set_user("Administrator")
		self.assertTrue(out["invariant_holds"])
		self.assertLessEqual(out["submissions"], out["links_issued"])


class TestAnEmptySubmission(_Base):
	"""**AC-110a, AC-110b, AC-110c**, and the harm has changed shape.

	Under the bearer link the defect was irreversible for the person it happened
	to: tapping Start, Next, Next, Send without typing was accepted, and sending
	BURNED THE KEY and deleted the row that held it - so HR got a blank record
	and the joiner had no way back in.

	**Send no longer burns anything** (decision 4a), so the cost is now a blank
	row for HR rather than a lost joiner. The rule survives anyway: one ticked
	field with a value, or one document. HR ticks the list and we add no
	restriction on top of it.
	"""

	def test_an_entirely_empty_submission_is_refused(self):
		"""AC-110a and the spec's AC-41: *"at least one ticked field with a
		value, or one document"* survives.

		**This test found two product defects, and both are now fixed.** It is
		kept exactly as it was written, because a test that is re-keyed to match
		what the code does would not have found either of them:

		**One.** `what_is_still_needed` guarded the empty send with
		`if not asked and not documents:` - "nothing is ASKED FOR", where the
		rule is "nothing is marked REQUIRED". The guard only ever fired at a
		tenant that asked for nothing at all, which is the one tenant where there
		was nothing to fill in anyway. It reads `required` now.

		**Two, and it killed the guard even there.** HR's own entry was written
		into the `mobile` column, which `COLUMN_FOR_TICK` maps `cell_number`
		onto - so *"has this joiner sent us anything?"* was answered **yes by
		HR**, on every row, before the joiner had touched the form. HR's number
		has its own field now, `login_id`.

		Here the six are ticked and none is compulsory, which is the exact
		configuration both defects hid in.
		"""
		submission = self._sign_in()
		self._as_the_joiner(submission)
		with self.assertRaises(frappe.ValidationError):
			joiner_public.submit_invite(
				values=frappe.as_json({t: "" for t in COLUMN_FOR_TICK}))
		frappe.set_user("Administrator")
		doc = frappe.get_doc(DOCTYPE, submission)
		self.assertEqual(doc.status, "Invited")
		self.assertFalse(doc.submitted_at)

	def test_a_refusal_costs_the_joiner_nothing(self):
		"""**AC-38, and the whole point of the rule.** Re-keyed from "it does not
		burn the link", which was about a key that no longer exists.

		Nothing is sent, the row stays `Invited`, **everything already typed is
		still there**, the account is still enabled, the session still works, and
		a second attempt with something in it succeeds. A refused send is not a
		punishment.

		**`cell_number` is the compulsory field, which it could not be before
		`login_id` existed:** HR's own number used to be written into the same
		`mobile` column that `COLUMN_FOR_TICK` maps `cell_number` onto, so this
		field was already satisfied before the joiner had typed anything.
		"""
		frappe.db.set_default("alvoraa_joiner_required_fields", "cell_number")
		frappe.db.commit()
		submission = self._sign_in()
		account = frappe.db.get_value(DOCTYPE, submission, "user")
		self._as_the_joiner(submission)
		# The real sequence, and it is not a workaround: pressing Next keeps the
		# draft on the employer's row, and only then does the joiner reach Check
		# and send. **A refused send writes nothing at all** - it throws before
		# `_keep` - so what survives a refusal is what the draft had already
		# saved. Asserting on a value posted only to the refused send would be
		# asserting on something the server never promised to store.
		joiner_public.save_draft(values=frappe.as_json({
			"personal_email": "s078keep@example.com",
		}))
		# Something real in one field, nothing in the compulsory one.
		with self.assertRaises(frappe.ValidationError):
			joiner_public.submit_invite(values=frappe.as_json({
				"cell_number": "   ",
				"personal_email": "s078keep@example.com",
			}))

		frappe.set_user("Administrator")
		doc = frappe.get_doc(DOCTYPE, submission)
		self.assertEqual(doc.status, "Invited")
		self.assertFalse(doc.submitted_at)
		self.assertEqual(doc.personal_email, "s078keep@example.com",
		                 "a refused send must not discard the saved draft")
		self.assertEqual(frappe.db.get_value("User", account, "enabled"), 1,
		                 "a refused send must not end the sign-in")

		# The session still works, and the form still opens.
		self._as_the_joiner(submission)
		self.assertTrue(joiner_public.open_invite())
		joiner_public.submit_invite(
			values=frappe.as_json({"cell_number": "+91 90000 00110"}))
		frappe.set_user("Administrator")
		self.assertEqual(
			frappe.db.get_value(DOCTYPE, submission, "status"), "Submitted")

	def test_exactly_one_field_is_enough(self):
		"""AC-110c, AC-41. We impose no mandatory field of our own - not even a
		name."""
		submission = self._sign_in()
		self._as_the_joiner(submission)
		joiner_public.submit_invite(
			values=frappe.as_json({"emergency_phone_number": "+91 90000 00111"}))
		frappe.set_user("Administrator")
		self.assertEqual(
			frappe.db.get_value(DOCTYPE, submission, "status"), "Submitted")

	def test_the_doctype_makes_no_joiner_field_mandatory(self):
		"""AC-110c's second half, read off the schema rather than the prose. A
		`reqd` here would be our restriction on top of HR's ticked list."""
		meta = frappe.get_meta(DOCTYPE)
		for field in JOINER_FIELDS:
			with self.subTest(field=field):
				self.assertFalse(meta.get_field(field).reqd)

	def test_one_document_and_nothing_typed_is_enough(self):
		"""AC-110c. A joiner who sends only their PAN card has sent us something,
		so the submission is not empty.

		Nothing is marked compulsory, so the rule is the only thing standing
		between HR and a blank row - and it is asserted **both ways round**: the
		same send is refused without the document and accepted with it. Nothing
		has to be arranged or cleared off the row for that to be observable any
		more.
		"""
		ticked, _un = fx.document_types()
		fx.set_lists(document_types=[ticked])
		frappe.db.commit()
		submission = self._sign_in()
		self._as_the_joiner(submission)
		# Without the document, the same send is refused.
		with self.assertRaises(frappe.ValidationError):
			joiner_public.submit_invite(values=frappe.as_json({}))
		with fx.with_documents_plan():
			joiner_public.upload_invite_file(
				document_type=ticked, filename="pan.pdf",
				data=fx.as_b64(fx._one_page_pdf()))
			joiner_public.submit_invite(values=frappe.as_json({}))
		frappe.set_user("Administrator")
		self.assertEqual(
			frappe.db.get_value(DOCTYPE, submission, "status"), "Submitted")


class TestTheJoinersOwnPhotograph(_Base):
	"""**AC-108a, AC-108b, AC-108c.** J4, which did not exist at all.

	It travels under one reserved type name through the documents endpoint, so
	there is no fourth endpoint for one optional picture - which mattered more
	when every endpoint was public, and still saves a surface now.
	"""

	def test_it_gets_the_employees_own_treatment(self):
		"""AC-108c. 512 px, no EXIF, private, on the submission row - the same
		constants an employee's own photograph uses, not a second code path."""
		from PIL import Image

		from alvoraa_portal import employee_photo

		submission = self._sign_in()
		source = fx.png_with_gps(size=(1600, 1200))
		self.assertIn(0x8825, fx.exif_of(source))
		self._as_the_joiner(submission)
		res = joiner_public.upload_invite_file(
			document_type=joiner_public.PHOTO_TYPE,
			filename="me.png", data=fx.as_b64(source))

		frappe.set_user("Administrator")
		row = frappe.db.get_value(
			"File", {"file_name": res["file_name"]},
			["file_url", "is_private", "attached_to_doctype", "attached_to_name"],
			as_dict=True)
		self.assertEqual(row.is_private, 1)
		# On the submission row, never on an Employee - there is no Employee yet.
		self.assertEqual(row.attached_to_doctype, DOCTYPE)
		self.assertEqual(row.attached_to_name, submission)
		blob = fx.file_bytes(row.file_url)
		with Image.open(io.BytesIO(blob)) as img:
			self.assertEqual(img.format, "JPEG")
			self.assertEqual(max(img.size), employee_photo.STORED_EDGE)
		self.assertEqual(fx.exif_of(blob), {})

	def test_a_pdf_is_not_a_photograph(self):
		"""AC-108c, refused with AC-4's own plain words."""
		submission = self._sign_in()
		self._as_the_joiner(submission)
		with self.assertRaises(frappe.ValidationError):
			joiner_public.upload_invite_file(
				document_type=joiner_public.PHOTO_TYPE,
				filename="me.pdf", data=fx.as_b64(fx._one_page_pdf()))
		frappe.set_user("Administrator")

	def test_skipping_it_stores_nothing_and_refuses_nothing(self):
		"""AC-108b. It is optional, so a submission with no picture succeeds and
		no `File` is left behind.

		A ticked field carries a value as well as the name, so this stays a test
		about the PICTURE rather than about the empty-send rule.
		"""
		submission = self._sign_in()
		self._as_the_joiner(submission)
		joiner_public.submit_invite(values=frappe.as_json({
			"full_name": "S078 No Picture",
			"cell_number": "+91 90000 00690",
		}))
		frappe.set_user("Administrator")
		self.assertEqual(
			frappe.db.get_value(DOCTYPE, submission, "status"), "Submitted")
		self.assertEqual(frappe.get_all("File", filters={
			"attached_to_doctype": DOCTYPE,
			"attached_to_name": submission,
		}), [])

	def test_the_reserved_name_is_not_a_type_anybody_can_make(self):
		"""The collision guard, asserted rather than assumed: a document type is
		named by its own title, and `__photo__` is not a title."""
		self.assertFalse(
			frappe.db.exists("Employee Document Type", joiner_public.PHOTO_TYPE))

	def test_the_public_surface_is_now_zero_endpoints(self):
		"""**AC-126, re-keyed from three to zero, and kept rather than deleted
		because this is the file that pinned the number.**

		Slice 078's answer was "exactly three `allow_guest` endpoints". 079's is
		**none**: the public write surface of this product went from one page and
		three guest endpoints to zero of each, which is what paid for the gate in
		`auth.py`. `test_joiner_079` sweeps all three joiner modules; this pins
		the one module that used to carry the surface.

		Read from **Frappe's own registry**, `frappe.guest_methods`, and not from
		an attribute on the function. `frappe.whitelist()` sets NO `allow_guest`
		attribute - it adds the function to a module-level set - so
		`getattr(fn, "allow_guest", False)` is always False and an assertion
		written that way can never fail.
		"""
		import inspect

		guests = sorted(name for name, fn
		                in inspect.getmembers(joiner_public, inspect.isfunction)
		                if fn in frappe.guest_methods)
		self.assertEqual(guests, [],
			"Pre-onboarding has an unauthenticated write surface again: %s. "
			"Every endpoint here must resolve its row from the session." % guests)
		# And every endpoint is still POST only.
		for name in ("open_invite", "save_draft", "submit_invite",
		             "upload_invite_file"):
			with self.subTest(endpoint=name):
				fn = getattr(joiner_public, name)
				self.assertEqual(
					list(frappe.allowed_http_methods_for_whitelisted_func[fn]),
					["POST"], "%s must be POST only" % name)


class TestTheJoinersPage(_Base):
	"""The template itself, which no Python test read before.

	It was the most attacked page in the product and is now behind a sign-in, so
	what it does NOT do still matters as much as what it draws.
	`test_browser_call_args_045` reads the portal's JavaScript only, so nothing
	else looks at this file.
	"""

	@staticmethod
	def _read(name):
		import os

		return open(os.path.join(frappe.get_app_path("alvoraa_portal"),
		                         "www", name), encoding="utf-8").read()

	def test_every_screen_the_design_draws_is_there(self):
		"""The joiner's own screens, including the photograph one that did not
		exist at all before 078 (AC-108a)."""
		page = self._read("joining.html")
		for screen in ("loading", "gone", "j0", "j1", "j2", "j3", "j4", "j5"):
			with self.subTest(screen=screen):
				self.assertIn('id="%s"' % screen, page)
		self.assertIn("Skip this", page)
		self.assertIn("nobody checks your face against it", page)

	def test_it_sends_the_photo_under_the_servers_own_reserved_name(self):
		"""A name the page and the server disagreed on would be a dead screen,
		and no argument-names gate reads this file."""
		self.assertIn('var PHOTO = "%s"' % joiner_public.PHOTO_TYPE,
		              self._read("joining.html"))

	def test_nothing_about_the_joiner_is_left_in_the_browser(self):
		"""**Stronger than 078's version, because 079 took the draft off the
		device.**

		078 kept the typed answers in `localStorage` and the token in the URL
		fragment. Both are gone: what the joiner typed is on the employer's own
		row, which is what makes *"nothing was lost"* true on a different phone
		AND leaves a borrowed handset with nothing on it - two things a browser
		draft could never promise at once. It also deletes a state: the silent
		`localStorage` quota failure an uploaded image causes.

		**The HTML comments are stripped before the assertion**, and that is not
		a loophole: the page's own comment names every one of these in order to
		say it was removed, so a grep over the raw file would fail on the
		explanation rather than on the code. The test reads what the browser
		runs.
		"""
		import re

		page = re.sub(r"<!--.*?-->", "", self._read("joining.html"), flags=re.S)
		page = re.sub(r"/\*.*?\*/", "", page, flags=re.S)
		for gone in ("localStorage", "sessionStorage", "history.replaceState",
		             "location.hash", "web_form_request_key", "#t="):
			with self.subTest(gone=gone):
				self.assertNotIn(gone, page)

	def test_the_page_reads_nothing_from_the_database(self):
		"""**D-7, asserted as behaviour rather than as a grep.**

		It used to compute `context.joiner_on` - a settings read - on every
		anonymous hit of the most attacked page in the product, and no template
		ever read the value. So the test is the stronger statement: this page
		touches the database **not at all**. Slice 013's `enrol.html` is held to
		the same rule, and this is its test.

		It checks the three security headers in the same breath. In 078 they were
		set inside a bare `try/except Exception: pass`, so a failure to set them
		was silent - finding F5 of that review. **That bare except is gone**: the
		one case where the headers genuinely cannot be set, a render with no HTTP
		request behind it, is named, and every other failure now escapes.
		"""
		from unittest import mock

		from alvoraa_portal.www import joining as page

		# Put back an object of ITS OWN class afterwards: slice 013 learned that
		# leaving a plain dict here fails another suite 900 tests later.
		original = frappe.local.response_headers
		frappe.local.response_headers = original.__class__()
		try:
			with mock.patch.object(
					frappe.db, "sql",
					side_effect=AssertionError("the joiner page read the database")):
				context = page.get_context(frappe._dict())
			said = frappe.local.response_headers
			self.assertEqual(said.get("X-Robots-Tag"), "noindex, nofollow")
			self.assertEqual(said.get("Cache-Control"), "no-store")
			self.assertEqual(said.get("Referrer-Policy"), "no-referrer")
		finally:
			frappe.local.response_headers = original

		self.assertNotIn("joiner_on", context)
		self.assertNotIn("joiner_on", self._read("joining.html"))

	def test_a_guest_is_sent_to_the_sign_in_page(self):
		"""079-SEC-3. Guest gets the sign-in page in its joiner state, not the
		form - the way `hrms_employee.py` already redirects."""
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.Redirect):
				from alvoraa_portal.www import joining as page

				page.get_context(frappe._dict())
			self.assertEqual(frappe.local.flags.redirect_location,
			                 "/alvoraa-login?for=joining")
		finally:
			frappe.local.flags.redirect_location = None
			frappe.set_user("Administrator")

	def test_the_old_address_is_gone(self):
		"""The rename was free exactly once - the feature ships off at every
		tenant, so nothing anywhere points at `/joiner` - and it will never be
		free again. A leftover file would serve the token page."""
		import os

		www = os.path.join(frappe.get_app_path("alvoraa_portal"), "www")
		for gone in ("joiner.html", "joiner.py"):
			with self.subTest(gone=gone):
				self.assertFalse(os.path.exists(os.path.join(www, gone)))


class TestTheUploads(_Base):
	def _ticked(self):
		ticked, _un = fx.document_types()
		fx.set_lists(document_types=[ticked])
		return ticked

	def test_an_exe_renamed_as_a_pdf_is_refused_on_its_bytes(self):
		kind = self._ticked()
		submission = self._sign_in()
		self._as_the_joiner(submission)
		with fx.with_documents_plan():
			with self.assertRaises(frappe.ValidationError):
				joiner_public.upload_invite_file(
					document_type=kind, filename="cv.pdf",
					data=fx.as_b64(b"MZ\x90\x00" + b"\x00" * 300))
		frappe.set_user("Administrator")

	def test_a_type_nobody_asked_for_is_refused(self):
		self._ticked()
		submission = self._sign_in()
		self._as_the_joiner(submission)
		with fx.with_documents_plan():
			with self.assertRaises(frappe.ValidationError):
				joiner_public.upload_invite_file(
					document_type="S078 Not Asked For", filename="x.pdf",
					data=fx.as_b64(fx._one_page_pdf()))
		frappe.set_user("Administrator")

	def test_an_image_is_re_encoded_so_its_metadata_is_gone(self):
		"""AC-115. A photograph of a document taken at home carries the location
		of somebody's home."""
		kind = self._ticked()
		submission = self._sign_in()
		self._as_the_joiner(submission)
		with fx.with_documents_plan():
			res = joiner_public.upload_invite_file(
				document_type=kind, filename="licence.png",
				data=fx.as_b64(fx.png_with_gps()))
		frappe.set_user("Administrator")
		url = frappe.db.get_value("File", {"file_name": res["file_name"]}, "file_url")
		self.assertEqual(fx.exif_of(fx.file_bytes(url)), {})

	def test_an_oversized_payload_is_refused_before_anything_is_decoded(self):
		kind = self._ticked()
		submission = self._sign_in()
		self._as_the_joiner(submission)
		with fx.with_documents_plan():
			with self.assertRaises(frappe.ValidationError):
				joiner_public.upload_invite_file(
					document_type=kind, filename="big.pdf",
					data="A" * (joiner_public.MAX_FILE_B64 + 10))
		frappe.set_user("Administrator")

	def test_documents_stay_open_after_send(self):
		"""**Decision 4a, and it is why Send no longer ends the sign-in.**
		Somebody who finds their PAN card the next evening sends it here rather
		than ringing HR."""
		kind = self._ticked()
		submission = self._sign_in()
		self._as_the_joiner(submission)
		joiner_public.submit_invite(
			values=frappe.as_json({"cell_number": "+91 90000 00813"}))
		with fx.with_documents_plan():
			out = joiner_public.upload_invite_file(
				document_type=kind, filename="pan.pdf",
				data=fx.as_b64(fx._one_page_pdf()))
		frappe.set_user("Administrator")
		self.assertTrue(out["stored"])

	def test_the_guest_upload_switch_stays_off(self):
		"""**AC-103 and AC-104, as DevOps re-worded them (OPS-40).**

		With our own session-checked endpoint, Frappe's site-wide guest-upload
		switch never has to go on at all - so the test is that the hole is SHUT,
		which is cheaper and stronger than a procedure for opening it carefully.
		Frappe's own `test_guest_upload_for_empty_whitelist` proves an empty
		allow-list with the switch ON lets a guest attach a file to ANY doctype.

		After 079 there are **zero** guest endpoints that could ever need it.
		"""
		self.assertFalse(
			frappe.db.get_single_value("System Settings",
			                           "allow_guests_to_upload_files"),
			"our own endpoint does the uploads; this switch must stay off")
		self.assertFalse(
			(frappe.db.get_single_value(
				"System Settings", "allowed_doctypes_for_guest_uploads") or "").strip(),
			"and the allow-list must stay empty, because an empty list with the "
			"switch ON opens every doctype")

	def test_the_limits_are_readable_off_each_endpoint(self):
		"""AC-120, re-keyed. The shape slice 013's own table test uses, so a
		reviewer can pin what each path is keyed on and how many.

		**Every one is keyed on the USER now**, not on a token (079-SEC-4). The
		field's name still contains "key", because that is what makes Frappe's
		own error-snapshot redaction mask the value in a log line - renaming it
		silently stops the redaction.
		"""
		table = {
			joiner_public.open_invite: 40,
			joiner_public.save_draft: 40,
			joiner_public.submit_invite: 10,
			joiner_public.upload_invite_file: 20,
		}
		for fn, limit in table.items():
			field, source, got, _window = fn.__alvoraa_limit__
			with self.subTest(fn=fn.__name__):
				self.assertEqual(got, limit)
				self.assertEqual(source, "user")
				self.assertIn("key", field)
