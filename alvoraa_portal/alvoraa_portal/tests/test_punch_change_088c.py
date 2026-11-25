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

		frappe.db.set_value("Employee", self.emp, "attendance_device_id", "D088C", update_modified=False)
		frappe.set_user(user)
		try:
			return add_log_based_on_employee_field("D088C", "%s %s:00" % (self.day, at), "reception", "IN")
		finally:
			frappe.set_user("Administrator")

	def test_the_sync_api_is_open_to_a_machine_and_closed_to_a_person_with_no_reason(self):
		"""A person can reach the same function a machine uses (P7). It has no reason argument,
		so for a person it is refused; for the machine account it is the normal punch."""
		doc = self._call_the_sync_api(self._machine_user())
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
		self.assertEqual((r.kind, r.reason_code, r.changed_by, r.punch, str(r.day)),
		                 ("Added", REASON, self.hr, doc.name, str(self.day)))
		self.assertEqual(r.what, "Punch at 10:00 added")
		self.assertEqual(r.company, self.h.company)

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
		self.assertEqual([r.kind for r in rows], ["Added", "Changed"])
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
					                "kind": "Added", "reason_code": REASON, "what": "x",
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

	def test_the_record_is_scoped_exactly_as_the_notice_is(self):
		self.assertEqual(
			register_notice.punch_change_query_conditions(self.hr),
			register_notice.notice_query_conditions(self.hr).replace(
				"`tabAlvoraa Register Notice`", "`tabAlvoraa Punch Change`"))
