"""078 step 6 - pre-onboarding, and what a stranger can learn from it.

The first public write path in this product, so this file is mostly about what
it refuses. Four tests carry it:

  * **one answer for every dead link.** Missing, unknown, expired and cancelled
    must be INDISTINGUISHABLE - Frappe's own validator gives four different
    answers and two different exception classes, and our page flattens them.
  * **no submission argument exists anywhere** on the guest path, so there is
    nothing a caller can post that reaches another person's row.
  * **the clear-text key is destroyed the moment the link stops working** -
    which is the narrowing that makes Surbhi's option (c) acceptable against
    078-SEC-9, and the thing a reviewer should check hardest.
  * **nothing ever becomes an Employee by itself**, and the naming series does
    not move.
"""

import frappe
import hrms.alvoraa_org_structure.settings as org_settings
from frappe.utils import add_to_date, now

from alvoraa_portal import joiner_housekeeping as hk
from alvoraa_portal import joiner_invite, joiner_public
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_joiner_submission.alvoraa_joiner_submission import (
	JOINER_FIELDS,
)
from alvoraa_portal.tests import fixtures_078 as fx
from alvoraa_portal.tests.fixtures_045 import Wave4Base, own_user

DOCTYPE = "Alvoraa Joiner Submission"


class _Base(Wave4Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.p = fx.people()
		cls.sm_user = own_user("s078sm", ("Employee", "System Manager"))

	def setUp(self):
		super().setUp()
		fx.clear_lists()
		frappe.db.set_default("alvoraa_joiner_form_on", "1")
		# A real contact, because the welcome screen REFUSES to render without
		# one - a notice telling somebody to get in touch, with nobody to get in
		# touch with, is the notice failing at the only thing it is for.
		frappe.db.set_default("alvoraa_hr_contact_phone", "+91 98100 00078")
		frappe.db.commit()
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.set_default("alvoraa_hr_contact_phone", "")
		fx.clear_lists()
		super().tearDown()

	def _invite(self, name="S078 Joiner"):
		frappe.set_user(self.p["hr_wide_user"])
		out = joiner_invite.invite_joiner(full_name=name)
		frappe.set_user("Guest")
		return out

	@staticmethod
	def _key(link):
		return link.split("#t=", 1)[1]


class TestTheSwitch(_Base):
	def test_it_ships_off(self):
		"""Off for the ordinary reason - a tenant turns a feature on
		deliberately. 078-PRIV-7's SPECIAL precondition is gone, because
		counsel answered the question it existed for on 29 Oct 2026."""
		self.assertEqual(org_settings.DEFAULTS["alvoraa_joiner_form_on"], 0)

	def test_nothing_works_while_it_is_off(self):
		frappe.db.set_default("alvoraa_joiner_form_on", "0")
		frappe.db.commit()
		frappe.set_user(self.p["hr_wide_user"])
		with self.assertRaises(frappe.ValidationError):
			joiner_invite.invite_joiner(full_name="S078 Nobody")

	def test_a_guest_cannot_tell_whether_it_is_off_or_their_link_is_wrong(self):
		"""Whether a feature is switched on is not a stranger's business
		either, so it is the same answer as a dead link."""
		out = self._invite()
		frappe.set_user("Administrator")
		frappe.db.set_default("alvoraa_joiner_form_on", "0")
		frappe.db.commit()
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError) as off:
			joiner_public.open_invite(web_form_request_key=self._key(out["link"]))
		with self.assertRaises(frappe.PermissionError) as junk:
			joiner_public.open_invite(web_form_request_key="not-a-key-at-all")
		self.assertEqual(str(off.exception), str(junk.exception))


class TestTheLink(_Base):
	def test_it_is_in_the_fragment_and_never_in_a_query_string(self):
		"""078-SEC-9's actual requirement. A browser never sends a fragment to
		a server, so the token reaches no access log, no Referer and no proxy -
		and ours logs the full request line, which is why this matters."""
		out = self._invite()
		self.assertIn("#t=", out["link"])
		self.assertNotIn("?", out["link"])
		self.assertNotIn("web_form_request_key=", out["link"])

	def test_the_lifetime_is_the_setting(self):
		frappe.set_user(self.sm_user)
		from alvoraa_portal import people_settings

		people_settings.set_people_setting(key="alvoraa_joiner_link_days", value="21")
		out = self._invite()
		self.assertEqual(out["link_days"], 21)

	def test_the_parameter_is_named_so_frappe_redacts_it(self):
		"""Frappe's error-snapshot redaction masks any form key whose NAME
		contains key/token/secret/password/passwd/pwd. Rename this parameter and
		the redaction silently stops - so the name is pinned."""
		import inspect

		for fn in (joiner_public.open_invite, joiner_public.submit_invite,
		           joiner_public.upload_invite_file):
			with self.subTest(fn=fn.__name__):
				self.assertIn("web_form_request_key",
				              inspect.signature(fn).parameters)

	def test_there_is_no_submission_argument_on_any_guest_path(self):
		"""Stronger than a scope check: there is nothing to post."""
		import inspect

		for fn in (joiner_public.open_invite, joiner_public.submit_invite,
		           joiner_public.upload_invite_file):
			params = set(inspect.signature(fn).parameters)
			with self.subTest(fn=fn.__name__):
				self.assertFalse(params & {"submission", "name", "employee", "doc"})


class TestWhatAStrangerLearns(_Base):
	def test_missing_unknown_expired_and_cancelled_are_one_answer(self):
		"""**078-SEC-13, and the test that matters most in this file.**

		Frappe gives four different answers and two exception classes. A
		stranger must not be able to tell whether a key was wrong, whether it
		once existed, or whether anybody has been invited at all.
		"""
		live = self._invite()
		key = self._key(live["link"])

		# expired
		frappe.set_user("Administrator")
		frappe.db.set_value("Web Form Request",
		                    frappe.db.get_value(DOCTYPE, live["submission"],
		                                        "web_form_request"),
		                    "expires_on", add_to_date(now(), days=-1))
		frappe.db.commit()

		cancelled = self._invite("S078 Cancelled")
		frappe.set_user(self.p["hr_wide_user"])
		joiner_invite.cancel_invite(submission=cancelled["submission"],
		                            reason="By HR")

		frappe.set_user("Guest")
		said = set()
		for bad in ("", "   ", "no-such-key", "a" * 64, key,
		            self._key(cancelled["link"])):
			with self.assertRaises(frappe.PermissionError) as caught:
				joiner_public.open_invite(web_form_request_key=bad)
			said.add(str(caught.exception))
		self.assertEqual(len(said), 1,
		                 f"four cases must give ONE answer, got {len(said)}: {said}")

	def test_a_used_link_is_indistinguishable_from_an_unknown_one(self):
		"""**RECORDED, because it is not what the design asked for - and it is
		stronger than what the design asked for.**

		AC-112 allows a narrower "already used" answer, as a deliberate
		disclosure to somebody who once held a live token. We cannot give it:
		the purge that makes Surbhi's option (c) acceptable **deletes the row
		holding the key the moment it is used**, so a used key is afterwards
		simply an unknown key and there is nothing left to recognise.

		The purge wins. 078-SEC-13 is satisfied more strongly than it asks, and
		the joiner is not left in the dark either - the generic answer says
		"nothing you sent is lost", which is true, and J6 already told them the
		link would not open again.

		**AC-112 and AC-125 therefore need rewording**, like AC-101. Said here
		rather than quietly re-pointed.
		"""
		out = self._invite()
		key = self._key(out["link"])
		joiner_public.submit_invite(web_form_request_key=key,
		                            values=frappe.as_json({"mobile": "+91 90000 00078"}))
		with self.assertRaises(frappe.PermissionError) as used:
			joiner_public.open_invite(web_form_request_key=key)
		with self.assertRaises(frappe.PermissionError) as junk:
			joiner_public.open_invite(web_form_request_key="not-a-key-at-all")
		self.assertEqual(str(used.exception), str(junk.exception))
		self.assertIn("nothing you sent is lost", str(used.exception).lower())

	def test_no_response_carries_anybody_elses_data(self):
		"""AC-124. Not a name, not a count, not an email address, nothing about
		the tenant beyond its own public brand."""
		other = fx.people()["with_photo"]
		other_name = frappe.db.get_value("Employee", other, "employee_name")
		out = self._invite()
		body = frappe.as_json(
			joiner_public.open_invite(web_form_request_key=self._key(out["link"])))
		self.assertNotIn(other_name, body)
		self.assertNotIn("HR-EMP", body)

	def test_guest_cannot_read_or_list_the_doctype(self):
		"""AC-123. And the JSON carries no Guest permission row at all."""
		import json
		import os

		import alvoraa_portal

		path = os.path.join(os.path.dirname(alvoraa_portal.__file__),
		                    "alvoraa_portal", "doctype",
		                    "alvoraa_joiner_submission",
		                    "alvoraa_joiner_submission.json")
		j = json.load(open(path, encoding="utf-8"))
		self.assertNotIn("Guest", [p["role"] for p in j["permissions"]])

		self._invite()
		frappe.set_user("Guest")
		# `frappe.get_list`, NOT `frappe.get_all`. get_all ignores permissions
		# by design, so the first version of this test passed while proving
		# nothing - and `frappe.client.get_list`, which is what a guest can
		# actually reach over HTTP, is the one that checks them.
		with self.assertRaises(frappe.PermissionError):
			frappe.get_list(DOCTYPE, fields=["name", "full_name"])


class TestWhatIsStored(_Base):
	def test_only_the_closed_allow_list_is_stored(self):
		"""078-PRIV-9, AC-108. An off-list field is not stored - and is dropped
		SILENTLY rather than refused, because an error naming a field a stranger
		guessed at tells them the field exists."""
		out = self._invite()
		joiner_public.submit_invite(
			web_form_request_key=self._key(out["link"]),
			values=frappe.as_json({
				"mobile": "+91 90000 00078",
				"bank_ac_no": "000111222",
				"ctc": "9900000",
				"date_of_birth": "1990-01-01",
			}))
		frappe.set_user("Administrator")
		doc = frappe.get_doc(DOCTYPE, out["submission"])
		self.assertEqual(doc.mobile, "+91 90000 00078")
		body = frappe.as_json(doc.as_dict())
		for never in ("000111222", "9900000", "1990-01-01"):
			self.assertNotIn(never, body)

	def test_the_allow_list_has_no_bank_salary_or_statutory_field(self):
		for never in ("bank_ac_no", "ctc", "pan_number", "aadhaar",
		              "date_of_birth", "salary"):
			self.assertNotIn(never, JOINER_FIELDS)
		self.assertEqual(len(JOINER_FIELDS), 7)

	def test_the_joiners_screen_states_the_configured_numbers(self):
		"""AC-106. The prototype's 90 days was ours, not counsel's, and a
		notice carrying a number we invented must never reach a joiner."""
		frappe.set_user(self.sm_user)
		from alvoraa_portal import people_settings

		people_settings.set_people_setting(key="alvoraa_joiner_not_hired_days",
		                                   value="200")
		people_settings.set_people_setting(key="alvoraa_joiner_backstop_days",
		                                   value="120")
		people_settings.set_people_setting(key="alvoraa_joiner_warn_days",
		                                   value="100")
		out = self._invite()
		d = joiner_public.open_invite(web_form_request_key=self._key(out["link"]))
		self.assertEqual(d["not_hired_days"], 200)
		self.assertEqual(d["backstop_days"], 120)

	def test_the_welcome_screen_refuses_to_render_with_no_contact(self):
		"""078-PRIV-8. It tells the joiner to get in touch, so there has to be
		somebody to get in touch with."""
		out = self._invite()
		frappe.set_user("Administrator")
		frappe.db.set_default("alvoraa_hr_contact_phone", "")
		frappe.db.set_default("alvoraa_hr_contact_email", "")
		frappe.db.set_value("Company", frappe.db.get_default("company") or "",
		                    "email", None) if frappe.db.get_default("company") else None
		frappe.db.commit()
		frappe.set_user("Guest")
		with self.assertRaises(frappe.ValidationError):
			joiner_public.open_invite(web_form_request_key=self._key(out["link"]))


class TestTheClearTextKeyIsShortLived(_Base):
	"""**The narrowing that makes option (c) acceptable against 078-SEC-9.**

	`Web Form Request.key` is a plain `Data` field stored in clear, and nothing
	in Frappe ever purges the row. Surbhi's decision of 31 Oct 2026 was option
	(c) PLUS a purge, so these are the tests a reviewer should read first.
	"""

	def test_submitting_destroys_the_row_that_holds_the_key(self):
		out = self._invite()
		frappe.set_user("Administrator")
		request = frappe.db.get_value(DOCTYPE, out["submission"], "web_form_request")
		self.assertTrue(frappe.db.exists("Web Form Request", request))
		frappe.set_user("Guest")
		joiner_public.submit_invite(web_form_request_key=self._key(out["link"]),
		                            values=frappe.as_json({}))
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("Web Form Request", request),
		                 "the clear-text key must not outlive the link")

	def test_cancelling_destroys_it_too(self):
		out = self._invite()
		frappe.set_user("Administrator")
		request = frappe.db.get_value(DOCTYPE, out["submission"], "web_form_request")
		frappe.set_user(self.p["hr_wide_user"])
		joiner_invite.cancel_invite(submission=out["submission"], reason="By HR")
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("Web Form Request", request))

	def test_the_daily_job_destroys_an_expired_ones(self):
		out = self._invite()
		frappe.set_user("Administrator")
		request = frappe.db.get_value(DOCTYPE, out["submission"], "web_form_request")
		frappe.db.set_value(DOCTYPE, out["submission"], "expires_on",
		                    add_to_date(now(), days=-1))
		frappe.db.commit()
		hk.expire_the_dead_links()
		self.assertFalse(frappe.db.exists("Web Form Request", request))
		self.assertEqual(
			frappe.db.get_value(DOCTYPE, out["submission"], "status"), "Expired")

	def test_our_own_row_never_holds_the_key(self):
		"""Whatever Frappe does, OUR doctype has no field that could."""
		out = self._invite()
		frappe.set_user("Administrator")
		doc = frappe.get_doc(DOCTYPE, out["submission"])
		body = frappe.as_json(doc.as_dict())
		self.assertNotIn(self._key(out["link"]), body)
		meta = frappe.get_meta(DOCTYPE)
		for never in ("token", "key", "secret"):
			self.assertFalse([f for f in meta.fields if never in f.fieldname],
			                 f"a field named *{never}* on our own row")


class TestItNeverCreatesAnEmployee(_Base):
	def test_submitting_creates_no_employee_and_does_not_move_the_series(self):
		"""AC-127. The absence-backfill trap is the reason: a back-dated joining
		date makes Frappe mark the person Absent for every day since, and
		deleting those rows does not help."""
		before = frappe.db.count("Employee")
		out = self._invite()
		joiner_public.submit_invite(
			web_form_request_key=self._key(out["link"]),
			values=frappe.as_json({f: "x" for f in JOINER_FIELDS}))
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.count("Employee"), before)
		self.assertFalse(frappe.db.get_value(DOCTYPE, out["submission"], "employee"))

	def test_no_joining_date_is_anywhere_on_the_row(self):
		"""AC-128. Not from the form and not from the submission's own dates."""
		meta = frappe.get_meta(DOCTYPE)
		self.assertFalse([f for f in meta.fields if "joining" in f.fieldname])
		self.assertNotIn("date_of_joining", JOINER_FIELDS)

	def test_linking_the_employee_is_what_moves_it_on(self):
		"""AC-129. Declarative: there is no button to press by accident and no
		endpoint that could be called with somebody else's id."""
		out = self._invite()
		joiner_public.submit_invite(web_form_request_key=self._key(out["link"]),
		                            values=frappe.as_json({}))
		frappe.set_user("Administrator")
		doc = frappe.get_doc(DOCTYPE, out["submission"])
		doc.employee = self.p["no_photo"]
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.status, "Made an employee")

	def test_a_terminal_state_cannot_be_revived(self):
		out = self._invite()
		frappe.set_user(self.p["hr_wide_user"])
		joiner_invite.cancel_invite(submission=out["submission"], reason="By HR")
		frappe.set_user("Administrator")
		doc = frappe.get_doc(DOCTYPE, out["submission"])
		doc.status = "Invited"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)


class TestRetention(_Base):
	def _aged(self, days, status="Submitted"):
		"""One submission, aged by `days`, with something in it to erase.

		`creation` and `closed_on` are written with SQL, because `set_value`
		will not move `creation` and a controller save would stamp `closed_on`
		with today. Ageing a row is the one thing a test has to do behind the
		ORM's back.
		"""
		out = self._invite()
		frappe.set_user("Administrator")
		name = out["submission"]
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

	def test_counsel_s_four_defaults(self):
		"""Surbhi's decision, 31 Oct 2026, from counsel's 29 Oct answer."""
		self.assertEqual(org_settings.DEFAULTS["alvoraa_joiner_not_hired_days"], 180)
		self.assertEqual(org_settings.DEFAULTS["alvoraa_joiner_backstop_days"], 90)
		self.assertEqual(org_settings.DEFAULTS["alvoraa_joiner_warn_days"], 75)
		self.assertEqual(org_settings.DEFAULTS["alvoraa_joiner_link_days"], 7)

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

	def test_no_setting_can_mean_keep_for_ever(self):
		"""AC-131d. The check-in photo setting uses 0 that way; this must not."""
		frappe.set_user(self.sm_user)
		from alvoraa_portal import people_settings

		for key in ("alvoraa_joiner_not_hired_days",
		            "alvoraa_joiner_backstop_days", "alvoraa_joiner_warn_days"):
			for bad in ("0", ""):
				with self.subTest(key=key, bad=bad):
					with self.assertRaises(frappe.PermissionError):
						people_settings.set_people_setting(key=key, value=bad)

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
		out = self._invite()
		frappe.set_user("Administrator")
		f = frappe.get_doc({
			"doctype": "File", "file_name": "s078-joiner-doc.pdf",
			"attached_to_doctype": DOCTYPE, "attached_to_name": out["submission"],
			"is_private": 1, "content": fx._one_page_pdf(),
		}).insert(ignore_permissions=True)
		frappe.db.commit()
		from alvoraa_portal.alvoraa_portal.doctype.alvoraa_joiner_submission.alvoraa_joiner_submission import (
			erase,
		)

		erase(out["submission"], why="test")
		self.assertFalse(frappe.db.exists("File", f.name))

	def test_the_erase_is_real_deletion_not_a_flag(self):
		"""Counsel's September policy prohibits indefinite soft deletion."""
		name = self._aged(200)
		hk.run_daily()
		doc = frappe.get_doc(DOCTYPE, name)
		for field in JOINER_FIELDS:
			self.assertFalse(doc.get(field), f"{field} survived the erase")
		# The shell that remains carries NO personal data - only who issued the
		# link and when, which is what answers "who invited somebody" a year
		# later and is the judgement recorded in 03-implementation-notes.md.
		self.assertTrue(doc.invited_by)
		self.assertTrue(doc.erased_why)

	def test_hr_is_warned_before_the_backstop_and_only_once(self):
		name = self._aged(80)
		self.assertEqual(hk._warn_hr_before_the_backstop(), 1)
		self.assertTrue(frappe.db.get_value(DOCTYPE, name, "warned_on"))
		self.assertEqual(hk._warn_hr_before_the_backstop(), 0)

	def test_the_invariant_hr_watches(self):
		"""OPS-28. Submissions must never exceed links issued: more means one
		forwarded link is being used by several people."""
		frappe.set_user(self.p["hr_wide_user"])
		out = hk.joiner_counts(days=7)
		self.assertTrue(out["invariant_holds"])
		self.assertLessEqual(out["submissions"], out["links_issued"])


class TestTheUploads(_Base):
	def _ticked(self):
		ticked, _un = fx.document_types()
		fx.set_lists(document_types=[ticked])
		return ticked

	def test_an_exe_renamed_as_a_pdf_is_refused_on_its_bytes(self):
		kind = self._ticked()
		out = self._invite()
		with fx.with_documents_plan():
			with self.assertRaises(frappe.ValidationError):
				joiner_public.upload_invite_file(
					web_form_request_key=self._key(out["link"]),
					document_type=kind, filename="cv.pdf",
					data=fx.as_b64(b"MZ\x90\x00" + b"\x00" * 300))

	def test_a_type_nobody_asked_for_is_refused(self):
		self._ticked()
		out = self._invite()
		with fx.with_documents_plan():
			with self.assertRaises(frappe.ValidationError):
				joiner_public.upload_invite_file(
					web_form_request_key=self._key(out["link"]),
					document_type="S078 Not Asked For", filename="x.pdf",
					data=fx.as_b64(fx._one_page_pdf()))

	def test_an_image_is_re_encoded_so_its_metadata_is_gone(self):
		"""AC-115. A photograph of a document taken at home carries the location
		of somebody's home."""
		kind = self._ticked()
		out = self._invite()
		with fx.with_documents_plan():
			res = joiner_public.upload_invite_file(
				web_form_request_key=self._key(out["link"]),
				document_type=kind, filename="aadhaar.png",
				data=fx.as_b64(fx.png_with_gps()))
		frappe.set_user("Administrator")
		url = frappe.db.get_value("File", {"file_name": res["file_name"]}, "file_url")
		self.assertEqual(fx.exif_of(fx.file_bytes(url)), {})

	def test_an_oversized_payload_is_refused_before_anything_is_decoded(self):
		kind = self._ticked()
		out = self._invite()
		with fx.with_documents_plan():
			with self.assertRaises(frappe.ValidationError):
				joiner_public.upload_invite_file(
					web_form_request_key=self._key(out["link"]),
					document_type=kind, filename="big.pdf",
					data="A" * (joiner_public.MAX_FILE_B64 + 10))

	def test_the_guest_upload_switch_stays_off(self):
		"""**AC-103 and AC-104, as DevOps re-worded them (OPS-40).**

		With our own token-checked endpoint, Frappe's site-wide guest-upload
		switch never has to go on at all - so the test is that the hole is SHUT,
		which is cheaper and stronger than a procedure for opening it carefully.
		Frappe's own `test_guest_upload_for_empty_whitelist` proves an empty
		allow-list with the switch ON lets a guest attach a file to ANY doctype.
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
		"""AC-120. The shape slice 013's own table test uses, so a reviewer can
		pin what each guest path is keyed on and how many."""
		table = {
			joiner_public.open_invite: 20,
			joiner_public.submit_invite: 3,
			joiner_public.upload_invite_file: 12,
		}
		for fn, limit in table.items():
			field, source, got, window = fn.__alvoraa_limit__
			with self.subTest(fn=fn.__name__):
				self.assertEqual(got, limit)
				self.assertEqual(source, "web_form_request_key")
				# Keyed on the HASH, never the token: Frappe writes a limiter's
				# key value into Redis in clear.
				self.assertIn("key", field)
