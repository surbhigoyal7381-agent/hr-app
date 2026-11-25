"""Slice 088c: a reason for every punch a person adds or changes, and the notice that lists it.

**The first class is the guard rail and it was written first.** The reason rule sits on the
table the biometric machines and the phone app write to. A rule that refuses one of those
punches loses it for good (the sync tool skips what it cannot file), so these tests prove,
with the switch ON, that a machine, the phone app, the web check-in, the employee's own edit
and an approved 087 fix are never asked for a reason and never logged. Only then do the tests
below prove the rule itself.

Each test has a control: the same step done by a person is refused, or the same step with the
switch off is allowed, so "allowed" never silently means "the rule is not running".
"""

import frappe
from frappe.utils import add_days, add_months, get_first_day

from alvoraa_portal import punch_change, register_notice
from alvoraa_portal.tests import test_punch_fix_087 as p87
from alvoraa_portal.tests.test_punch_fix_087 import security_lines_from_a_fresh_process
from alvoraa_portal.tests.test_register_notice_088 import RegisterNoticeCase, _a_jpeg

CHECKIN = "Employee Checkin"
LOG = punch_change.LOG
REASON = "Punch machine was down or offline"


def setUpModule():
	p87.setUpModule()
	register_notice.after_migrate()
	punch_change.after_migrate()
	frappe.clear_cache()


class PunchChangeCase(RegisterNoticeCase):
	def punch(self, hhmm="10:00", day=None, user=None, reason=None, employee=None, **extra):
		doc = frappe.get_doc({"doctype": CHECKIN, "employee": employee or self.emp,
		                      "time": "%s %s:00" % (day or self.day, hhmm), "log_type": "IN", **extra})
		if reason:
			doc.set(punch_change.FIELD, reason)
		frappe.set_user(user or "Administrator")
		try:
			return doc.insert(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")

	def log(self, **filters):
		return frappe.get_all(LOG, filters={"employee": self.emp, **filters},
		                      fields=["*"], order_by="creation asc")

	def edit(self, name, user, reason=None, **changes):
		doc = frappe.get_doc(CHECKIN, name)
		doc.update(changes)
		if reason:
			doc.set(punch_change.FIELD, reason)
		frappe.set_user(user)
		try:
			doc.save(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")
		return doc

class TheGuardRail(PunchChangeCase):
	"""Nothing a machine, a phone or the employee does is refused or logged. Switch is ON."""

	def test_switch_is_on_and_a_person_is_refused_without_a_reason(self):
		"""The control for every test below: the rule is running."""
		with self.assertRaisesRegex(frappe.ValidationError, "Pick a reason"):
			self.punch(user=self.hr)

	def test_a_machine_punch_with_no_reason_is_filed_and_not_logged(self):
		before = frappe.db.count(CHECKIN, {"employee": self.emp})
		doc = self.punch(user=self._machine_user())
		self.assertEqual(frappe.db.count(CHECKIN, {"employee": self.emp}), before + 1)
		self.assertTrue(frappe.db.exists(CHECKIN, doc.name))
		self.assertEqual(self.log(), [])

	def test_a_sync_login_that_also_holds_an_hr_role_is_still_a_machine(self):
		"""The real accounts hold the sync role PLUS an HR role (ALV-302), so that is the shape
		that must pass. It is also the shape a person could use: see 03c, "what a person can do"."""
		doc = self.punch(user=self._machine_user(with_hr_role=True))
		self.assertTrue(frappe.db.exists(CHECKIN, doc.name))
		self.assertEqual(self.log(), [])

	def test_a_phone_app_punch_with_no_human_session_is_filed_and_not_logged(self):
		doc = self.punch(user="Guest", device_id="alvoraa-field-app")
		self.assertTrue(frappe.db.exists(CHECKIN, doc.name))
		self.assertEqual(self.log(), [])

	def test_the_web_checkin_and_the_employees_own_edit_are_not_logged(self):
		doc = self.punch(user=self.emp_user, device_id="web-portal")
		self.assertTrue(frappe.db.exists(CHECKIN, doc.name))
		self.edit(doc.name, self.emp_user, log_type="OUT")
		self.assertEqual(frappe.db.get_value(CHECKIN, doc.name, "log_type"), "OUT")
		self.assertEqual(self.log(), [])

	def test_an_approved_087_fix_adds_a_punch_and_is_not_logged_twice(self):
		self.held_on(self.day)
		req = self.fix(time="18:30", by=self.hr)
		self.decide(req, 1, by=self.h.hr2)
		added = frappe.get_all(CHECKIN, filters={"alvoraa_fix_added_request": req}, pluck="name")
		self.assertEqual(len(added), 1, "fixture: the approval should have added a punch")
		self.assertEqual(self.log(), [], "a fix is on the notice through its request; it must not appear twice")

	def _call_the_sync_api(self, user, at="07:00"):
		"""The whitelisted function the sync tools use, called as `user`."""
		from hrms.hr.doctype.employee_checkin.employee_checkin import add_log_based_on_employee_field

		device = "D" + frappe.generate_hash(length=8)      # unique: another run may have committed one
		frappe.db.set_value("Employee", self.emp, "attendance_device_id", device, update_modified=False)
		frappe.set_user(user)
		try:
			return add_log_based_on_employee_field(device, "%s %s:00" % (self.day, at), "reception", "IN")
		finally:
			frappe.set_user("Administrator")

	def test_the_sync_api_is_open_to_a_machine_and_closed_to_a_person_with_no_reason(self):
		"""A person can reach the same function a machine uses (P7). It has no reason argument,
		so for a person it is refused; for the machine account it is the normal punch."""
		doc = self._call_the_sync_api(self._machine_user(with_hr_role=True))
		self.assertTrue(frappe.db.exists(CHECKIN, doc.name))
		self.assertEqual(self.log(), [])
		with self.assertRaisesRegex(frappe.ValidationError, "Pick a reason"):
			self._call_the_sync_api(self.hr, at="08:00")

	def test_switch_off_nothing_is_demanded_or_logged(self):
		"""Decision 1: nothing starts before the switch."""
		self._set_notices(0)
		doc = self.punch(user=self.hr)
		self.assertTrue(frappe.db.exists(CHECKIN, doc.name))
		self.assertEqual(self.log(), [])


class TheReason(PunchChangeCase):
	def test_a_person_adds_a_punch_with_a_reason_and_one_record_is_written(self):
		doc = self.punch("10:00", user=self.hr, reason=REASON)
		self.assertIsNone(frappe.db.get_value(CHECKIN, doc.name, punch_change.FIELD),
		                  "the reason must not sit on the punch")
		rows = self.log()
		self.assertEqual(len(rows), 1)
		r = rows[0]
		self.assertEqual((r.reason_code, r.changed_by, r.punch, str(r.day)),
		                 (REASON, self.hr, doc.name, str(self.day)))
		self.assertEqual(r.what, "Punch at 10:00 added")

	def test_a_refused_punch_leaves_no_punch_and_no_record(self):
		before = frappe.db.count(CHECKIN, {"employee": self.emp})
		with self.assertRaisesRegex(frappe.ValidationError, "Pick a reason"):
			self.punch(user=self.hr)
		self.assertEqual(frappe.db.count(CHECKIN, {"employee": self.emp}), before)
		self.assertEqual(self.log(), [])

	def test_an_edit_needs_a_fresh_reason_every_time(self):
		doc = self.punch("10:00", user=self.hr, reason=REASON)
		self.edit(doc.name, self.hr, reason="Duplicate or accidental scan", time="%s 10:40:00" % self.day)
		rows = self.log()
		self.assertEqual([r.what for r in rows][0], "Punch at 10:00 added")
		self.assertEqual(rows[1].what, "Punch moved from 10:00 to 10:40")
		self.assertEqual(rows[1].reason_code, "Duplicate or accidental scan")
		# The last reason is not reusable: the next edit must give its own.
		with self.assertRaisesRegex(frappe.ValidationError, "Pick a reason"):
			self.edit(doc.name, self.hr, time="%s 10:55:00" % self.day)
		self.assertEqual(str(frappe.db.get_value(CHECKIN, doc.name, "time"))[11:16], "10:40")
		self.assertEqual(len(self.log()), 2)

	def test_changing_what_does_not_decide_the_day_needs_no_reason(self):
		doc = self.punch("10:00", user=self.hr, reason=REASON)
		self.edit(doc.name, self.hr, device_id="reception-1")
		self.assertEqual(len(self.log()), 1, "a device id is not a change to what the punch means")

	def test_not_counting_a_punch_is_a_change_and_says_so(self):
		doc = self.punch("10:00", user=self.hr, reason=REASON)
		self.edit(doc.name, self.hr, reason=REASON, skip_auto_attendance=1)
		self.assertEqual(self.log()[-1].what, "Punch at 10:00 not counted")

	def test_administrator_is_a_person_and_needs_a_reason(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Pick a reason"):
			self.punch(user="Administrator")
		doc = self.punch(user="Administrator", reason=REASON)
		self.assertEqual(self.log()[-1].changed_by, "Administrator")
		self.assertTrue(frappe.db.exists(CHECKIN, doc.name))

	def test_a_person_cannot_delete_a_punch_while_notices_are_on(self):
		doc = self.punch(user=self.hr, reason=REASON)
		frappe.set_user(self.hr)
		try:
			with self.assertRaisesRegex(frappe.ValidationError, "cannot be deleted"):
				frappe.delete_doc(CHECKIN, doc.name, ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")
		self.assertTrue(frappe.db.exists(CHECKIN, doc.name))
		# control: with the switch off the same delete works, so the refusal is the rule's.
		self._set_notices(0)
		frappe.delete_doc(CHECKIN, doc.name, ignore_permissions=True)
		self.assertFalse(frappe.db.exists(CHECKIN, doc.name))

	def test_the_record_cannot_be_made_edited_or_deleted_by_hand(self):
		self.punch(user=self.hr, reason=REASON)
		row = self.log()[0].name
		for user in (self.hr, "Administrator"):
			frappe.set_user(user)
			try:
				with self.assertRaises(frappe.PermissionError):
					frappe.get_doc({"doctype": LOG, "punch": "x", "employee": self.emp, "day": self.day,
					                "reason_code": REASON, "what": "x",
					                "changed_by": user, "changed_on": frappe.utils.now_datetime()}
					               ).insert(ignore_permissions=True)
				doc = frappe.get_doc(LOG, row)
				doc.what = "tampered"
				with self.assertRaises(frappe.PermissionError):
					doc.save(ignore_permissions=True)
				with self.assertRaises(frappe.PermissionError):
					frappe.delete_doc(LOG, row, ignore_permissions=True)
			finally:
				frappe.set_user("Administrator")

	def test_the_reason_options_on_the_punch_are_the_options_on_the_record(self):
		on_log = frappe.get_meta(LOG).get_field("reason_code").options
		on_punch = frappe.get_meta(CHECKIN).get_field(punch_change.FIELD).options
		self.assertEqual(on_punch.strip("\n"), on_log)


class TheNotice(PunchChangeCase):
	def _mine(self, month=None):
		return self._rows_for_me(month)

	def test_a_typed_punch_reaches_the_list_the_sheet_and_the_notice_record(self):
		self.assertEqual(self._mine(), [], "control: nothing before the change")
		doc = self.punch("10:00", user=self.hr, reason=REASON)
		rows = self._mine()
		self.assertEqual(len(rows), 1)
		self.assertEqual((rows[0]["state"], rows[0]["changed_days"]), ("not_printed", 1))
		out = self._print([self.emp])
		sheet = out["sheets"][0]
		line = sheet["changes"][0]
		self.assertEqual(line["what"], ["Punch at 10:00 added"])
		self.assertEqual(line["why"], REASON)
		self.assertEqual((line["filed_role"], line["filed_by"], line["blocks_pay"]), ("HR", None, False))
		self.assertFalse(sheet["pay_line"], "a direct punch must not promise a held slip")
		child = frappe.get_all("Alvoraa Register Notice Change", filters={"parent": sheet["notice"]},
		                       fields=["request", "punch_change"])
		self.assertEqual([(c.request, c.punch_change) for c in child],
		                 [(None, self.log()[0].name)])

	def test_signing_covers_it_and_the_filer_cannot_record_their_own(self):
		self.punch("10:00", user=self.hr, reason=REASON)
		notice = self._print([self.emp])["sheets"][0]["notice"]
		frappe.set_user(self.hr)
		try:
			with self.assertRaises(frappe.PermissionError):
				register_notice.record(notice, "Not right", reason="not me")
		finally:
			frappe.set_user("Administrator")
		frappe.set_user(self.h.hr2)
		try:
			out = register_notice.record(notice, "Signed", photos=[_a_jpeg()])
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(out["outcome"], "Signed")
		self.assertEqual(self._mine()[0]["state"], "done")

	def test_a_change_after_the_print_is_named_as_not_on_the_page(self):
		self.punch("10:00", user=self.hr, reason=REASON)
		self._print([self.emp])
		self.punch("11:00", user=self.hr, reason=REASON)
		self.assertEqual(self._mine()[0]["state"], "changed_after_print")

	def test_a_late_edit_of_an_earlier_month_is_listed_on_that_month_only(self):
		last = add_months(get_first_day(self.day), -1)
		self.punch("10:00", day=add_days(last, 3), user=self.hr, reason=REASON)
		self.assertEqual(len(self._mine(last)), 1)
		self.assertEqual(self._mine(), [], "it must not appear on this month's notice")

	def test_something_done_before_the_switch_is_never_listed(self):
		"""Decisions 1 and 2: October is untouched, with no backfill."""
		self._set_notices(0)
		self.punch("10:00", user=self.hr)
		self._set_notices(1)
		self.assertEqual(self._mine(), [])

	def test_the_employees_own_view_shows_it_with_its_reason(self):
		self.punch("10:00", user=self.hr, reason=REASON)
		frappe.set_user(self.emp_user)
		try:
			mine = register_notice.my_changes(self.day)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(len(mine["days"]), 1)
		self.assertEqual((mine["days"][0]["why"], mine["days"][0]["state"]), (REASON, "shown"))


class TheWorkingDay(PunchChangeCase):
	"""P1-1 of the review: the log and the paper use the day the punch's SHIFT started (ALV-402),
	not its calendar date. A daytime test could never have failed this."""

	NIGHT = "ALV088 Night"

	def night_employee(self):
		if not frappe.db.exists("Shift Type", self.NIGHT):
			frappe.get_doc({"doctype": "Shift Type", "name": self.NIGHT, "start_time": "20:30:00",
			                "end_time": "05:00:00", "working_hours_threshold_for_absent": 4,
			                "working_hours_threshold_for_half_day": 7,
			                "begin_check_in_before_shift_start_time": 240,
			                "allow_check_out_after_shift_end_time": 240,
			                "enable_auto_attendance": 1}).insert(ignore_permissions=True)
		was = frappe.db.get_value("Employee", self.emp, "default_shift")
		frappe.db.set_value("Employee", self.emp, "default_shift", self.NIGHT, update_modified=False)
		self.addCleanup(frappe.db.set_value, "Employee", self.emp, "default_shift", was, update_modified=False)
		frappe.clear_document_cache("Employee", self.emp)

	def test_a_00_30_punch_on_a_night_shift_is_logged_and_printed_on_the_evening_before(self):
		self.night_employee()
		evening = self.day                                 # the shift starts at 20:30 on this day
		doc = self.punch("00:30", day=add_days(evening, 1), user=self.hr, reason=REASON)
		self.assertEqual(str(frappe.db.get_value(CHECKIN, doc.name, "shift_start"))[:10], str(evening),
		                 "fixture is wrong: the night shift was not matched, so this proves nothing")
		row = self.log()[0]
		self.assertEqual(str(row.day), str(evening), "the log dated the punch by its calendar day")
		out = self._print([self.emp], month=evening)
		self.assertEqual(out["sheets"][0]["changes"][0]["day"], register_notice._day_words(evening))

	def test_the_last_night_of_a_month_is_on_that_months_notice_and_not_the_next(self):
		self.night_employee()
		last = frappe.utils.get_last_day(add_months(get_first_day(self.day), -1))
		self.punch("00:30", day=add_days(last, 1), user=self.hr, reason=REASON)
		self.assertEqual(len(self._rows_for_me(get_first_day(last))), 1, "missing from the month that was paid")
		self.assertEqual(self._rows_for_me(get_first_day(self.day)), [], "listed on the month after")

	def test_a_daytime_punch_keeps_its_own_day(self):
		"""The control: nothing changes for a day shift."""
		self.punch("10:00", user=self.hr, reason=REASON)
		self.assertEqual(str(self.log()[0].day), str(self.day))


class TheEscapes(PunchChangeCase):
	"""Review P2-2, P2-3, P2-4 and security F3: the ways round the rule that were found."""

	OTHER_SHIFT = "ALV088 Other Shift"

	def test_a_script_that_skips_validation_still_needs_a_reason(self):
		"""`doc.flags.ignore_validate = True` (alv291's retag does it) skips `validate` only."""
		doc = self.punch("10:00", user=self.hr, reason=REASON)
		again = frappe.get_doc(CHECKIN, doc.name)
		again.log_type = "OUT"
		again.flags.ignore_validate = True
		frappe.set_user(self.hr)
		try:
			with self.assertRaisesRegex(frappe.ValidationError, "Pick a reason"):
				again.save(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value(CHECKIN, doc.name, "log_type"), "IN")
		# control: with a reason the same save works and is logged
		again = frappe.get_doc(CHECKIN, doc.name)
		again.log_type = "OUT"
		again.flags.ignore_validate = True
		again.set(punch_change.FIELD, REASON)
		frappe.set_user(self.hr)
		try:
			again.save(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(self.log()[-1].what, "Punch type changed from In to Out")

	def test_re_tagging_the_shift_is_a_change_that_needs_a_reason(self):
		"""The shift tag decides which day a punch counts on, so it is watched."""
		if not frappe.db.exists("Shift Type", self.OTHER_SHIFT):
			frappe.get_doc({"doctype": "Shift Type", "name": self.OTHER_SHIFT, "start_time": "14:00:00",
			                "end_time": "22:00:00", "enable_auto_attendance": 1}).insert(ignore_permissions=True)
		doc = self.punch("10:00", user=self.hr, reason=REASON)
		before = len(self.log())
		again = frappe.get_doc(CHECKIN, doc.name)
		again.shift = self.OTHER_SHIFT
		again.shift_start = "%s 14:00:00" % add_days(self.day, -1)
		again.flags.ignore_validate = True            # as alv291's retag does
		frappe.set_user(self.hr)
		try:
			with self.assertRaisesRegex(frappe.ValidationError, "Pick a reason"):
				again.save(ignore_permissions=True)
			again = frappe.get_doc(CHECKIN, doc.name)       # a failed save stamps `modified` in memory
			again.shift = self.OTHER_SHIFT
			again.shift_start = "%s 14:00:00" % add_days(self.day, -1)
			again.flags.ignore_validate = True
			again.set(punch_change.FIELD, REASON)
			again.save(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(len(self.log()), before + 1)
		d = frappe.utils.getdate(add_days(self.day, -1))
		self.assertEqual(self.log()[-1].what, "Punch moved to the %d %s shift" % (d.day, d.strftime("%b")))

	def test_a_punch_cannot_be_moved_to_another_person(self):
		doc = self.punch("10:00", user=self.hr, reason=REASON)
		other = self.h._employee("Mover088")
		frappe.set_user(self.hr)
		try:
			again = frappe.get_doc(CHECKIN, doc.name)
			again.employee = other
			again.set(punch_change.FIELD, REASON)
			with self.assertRaisesRegex(frappe.ValidationError, "cannot be moved to another person"):
				again.save(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value(CHECKIN, doc.name, "employee"), self.emp)
		self.assertEqual(frappe.get_all(LOG, filters={"employee": other}), [])
		# control: with notices off the move is allowed, so the refusal is the rule's.
		self._set_notices(0)
		again = frappe.get_doc(CHECKIN, doc.name)
		again.employee = other
		again.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value(CHECKIN, doc.name, "employee"), other)

	def test_an_import_cannot_write_free_text_into_the_reason(self):
		"""Frappe skips the Select check for the whole of an import (`flags.in_import`)."""
		# The control: the premise is real, a bad Select value is accepted under the flag.
		frappe.flags.in_import = True
		self.addCleanup(setattr, frappe.flags, "in_import", False)
		accepted = self.punch("05:00", user=self._machine_user(), log_type="SIDEWAYS")
		self.assertEqual(frappe.db.get_value(CHECKIN, accepted.name, "log_type"), "SIDEWAYS",
		                 "fixture is wrong: Frappe did not skip the Select check, so this proves nothing")
		before = frappe.db.count(CHECKIN, {"employee": self.emp})
		with self.assertRaisesRegex(frappe.ValidationError, "not one of the reasons"):
			self.punch("11:00", user=self.hr, reason="Told by the manager, do not pay him")
		self.assertEqual(frappe.db.count(CHECKIN, {"employee": self.emp}), before)
		self.assertEqual(self.log(), [])
		# and a listed reason still goes through under the same flag
		self.punch("12:00", user=self.hr, reason=REASON)
		self.assertEqual(len(self.log()), 1)

	def test_the_reason_is_checked_again_when_the_record_is_written(self):
		"""The second line of defence, tested on its own by handing `write_log` a bad stash."""
		doc = frappe.get_doc({"doctype": CHECKIN, "employee": self.emp, "log_type": "IN",
		                      "time": "%s 13:00:00" % self.day})
		doc.name = "EMP-CKIN-NOT-SAVED"      # the record needs a punch name; only the reason is under test
		doc.flags[punch_change._STASH] = {"reason": "free text", "what": "Punch at 13:00 added"}
		frappe.set_user(self.hr)
		try:
			with self.assertRaisesRegex(frappe.ValidationError, "not one of the reasons"):
				punch_change.write_log(doc)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(self.log(), [])


class TheRefusalsAreWrittenDown(PunchChangeCase):
	def _rules(self, fn):
		import json
		out = []
		for line in security_lines_from_a_fresh_process(fn):
			try:
				out.append(json.loads(line).get("rule"))
			except Exception:
				pass
		return out

	def test_each_refusal_leaves_a_line_with_its_rule(self):
		doc = self.punch("10:00", user=self.hr, reason=REASON)

		def attempts():
			frappe.set_user(self.hr)
			try:
				for fn in (lambda: self.punch(hhmm="11:00", user=self.hr),
				           lambda: frappe.delete_doc(CHECKIN, doc.name, ignore_permissions=True),
				           lambda: self.punch(hhmm="12:00", user=self.hr, reason="free text")):
					try:
						fn()
					except frappe.ValidationError:
						pass
			finally:
				frappe.set_user("Administrator")

		rules = self._rules(attempts)
		self.assertEqual(sorted(set(rules)), ["088c-delete", "088c-reason", "088c-reason-list"])

	def test_a_refused_move_leaves_its_line_too(self):
		doc = self.punch("10:00", user=self.hr, reason=REASON)
		other = self.h._employee("Mover088b")

		def attempt():
			again = frappe.get_doc(CHECKIN, doc.name)
			again.employee = other
			frappe.set_user(self.hr)
			try:
				again.save(ignore_permissions=True)
			except frappe.ValidationError:
				pass
			finally:
				frappe.set_user("Administrator")

		self.assertEqual(self._rules(attempt), ["088c-move"])

	def test_the_record_cannot_be_deleted_even_during_a_migration(self):
		self.punch(user=self.hr, reason=REASON)
		row = self.log()[0].name
		frappe.flags.in_migrate = True
		self.addCleanup(setattr, frappe.flags, "in_migrate", False)
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc(LOG, row, ignore_permissions=True)
		self.assertTrue(frappe.db.exists(LOG, row))


class TheScopeReadAsEachPersona(PunchChangeCase):
	"""P2-5. Read the way the app reads it: `get_list` as each login, and `has_permission`."""

	def test_hr_in_scope_sees_the_row_hr_of_another_company_and_an_employee_do_not(self):
		self.punch(user=self.hr, reason=REASON)
		row = self.log()[0].name
		outsider = self.h._login("hrfar088c", ("HR Manager",))       # no company permission at all
		names = lambda u: [r.name for r in frappe.get_list(LOG, user=u, filters={"employee": self.emp},
		                                                    fields=["name"])]
		self.assertEqual(names(self.hr), [row], "HR who looks after this person cannot see the row")
		self.assertEqual(names(outsider), [], "HR of another company can list the row")
		self.assertTrue(frappe.has_permission(LOG, "read", doc=row, user=self.hr))
		self.assertFalse(frappe.has_permission(LOG, "read", doc=row, user=outsider),
		                 "HR of another company can open the row by name")
		self.assertFalse(frappe.has_permission(LOG, "read", doc=row, user=self.emp_user),
		                 "the employee can open the log row; they see their own through my_changes")
		with self.assertRaises(frappe.PermissionError):
			frappe.get_list(LOG, user=self.emp_user, fields=["name"])


class TwoPages(PunchChangeCase):
	"""Review P2-6 / F1: at 5 rows a page, direct changes make two pages ordinary."""

	def test_six_direct_changes_print_two_pages_and_can_be_signed_with_two_photos(self):
		first = get_first_day(self.day)
		for k in range(6):
			self.punch("10:%02d" % k, day=add_days(first, k), user=self.hr, reason=REASON)
		out = self._print([self.emp], month=first)
		self.assertEqual(sorted(s["page_no"] for s in out["sheets"]), [1, 2])
		self.assertEqual([len(s["changes"]) for s in sorted(out["sheets"], key=lambda s: s["page_no"])], [5, 1])
		notice = out["sheets"][0]["notice"]
		self.assertEqual(frappe.db.get_value("Alvoraa Register Notice", notice, "page_count"), 2)
		frappe.set_user(self.h.hr2)
		try:
			with self.assertRaises(frappe.ValidationError):
				register_notice.record(notice, "Signed", photos=[_a_jpeg()])
			done = register_notice.record(notice, "Signed", photos=[_a_jpeg(), _a_jpeg()])
		finally:
			frappe.set_user("Administrator")
		self.assertEqual((done["outcome"], done["photos"]), ("Signed", 2))
		self.assertEqual(self._rows_for_me(first)[0]["state"], "done")
