"""Slice 088, part 1: the record of a printed notice, and the seam with 087.

**What this file proves, and what it does not.** It covers the data model and the join
with slice 087: the three record types exist with the permissions the spec states, the
record refuses to be typed, edited or deleted by hand, signing the register marks the
changed days, and a marked day stops holding the salary slip. The page itself, the HR
list and the photos are later parts of the slice and are not tested here - and are not
built here either, so nothing below passes by accident on code that does not exist.

Three habits the earlier slices paid for:

- the new behaviour is also tested from the OTHER side: not only "a signed change leaves
  the unconfirmed list" but "the same change, unsigned, is still on it". A test that only
  asserts the new state passes just as well when the gate is removed altogether.
- the controller refusals each have a control beside them proving the module's own write
  works, so "refused" never silently means "broken".
- `record_register_signature` is tested through the stored row, not through its return
  value. The return value is what the code believes; the row is what payroll will read.
"""

import os

import frappe
from frappe.utils import now_datetime

from alvoraa_portal import punch_fix, register_notice
from alvoraa_portal.tests import test_punch_fix_087 as p87
from alvoraa_portal.tests.test_punch_fix_087 import PunchFixCase

NOTICE = "Alvoraa Register Notice"
REQUEST = "Attendance Request"
PKG = os.path.dirname(os.path.dirname(__file__))


def setUpModule():
	"""087's fixture, plus 088's own column and record types."""
	p87.setUpModule()
	register_notice.after_migrate()
	frappe.clear_cache()


class RegisterNoticeCase(PunchFixCase):
	def setUp(self):
		super().setUp()
		# **This suite tests the paper round, so its company has to ask for it.** The
		# notice switch is 088's own (23 Nov 2026) and ships OFF, so without this line
		# every list, print and employee view below is correctly empty and the whole
		# suite fails on fixtures rather than on behaviour. The same shape as 087's
		# confirm switch above it, restored after each test so no other suite inherits
		# the choice.
		self._notices_were = frappe.db.get_value("Company", self.h.company,
		                                         register_notice.NOTICE_SWITCH)
		self.addCleanup(self._put_the_notice_switch_back, self.h.company)
		self._set_notices(1)

	def _set_notices(self, on, company=None):
		frappe.db.set_value("Company", company or self.h.company,
		                    register_notice.NOTICE_SWITCH, on, update_modified=False)
		frappe.clear_cache()

	def _put_the_notice_switch_back(self, company):
		frappe.db.set_value("Company", company, register_notice.NOTICE_SWITCH,
		                    self._notices_were, update_modified=False)
		frappe.clear_cache()

	def notice(self, requests, pages=1, employee=None, month=None):
		"""A notice written the way the module writes one: under its own flag."""
		frappe.flags.in_register_notice = True
		try:
			doc = frappe.get_doc({
				"doctype": NOTICE,
				"employee": employee or self.emp,
				"month": month or frappe.utils.get_first_day(self.day),
				"printed_by": frappe.session.user,
				"printed_at": now_datetime(),
				"page_count": pages,
				"outcome": "Printed",
				"changes": [{"request": r, "page_no": 1,
				             "content_hash": "0" * 64} for r in requests],
			})
			doc.insert(ignore_permissions=True)
			return doc
		finally:
			frappe.flags.in_register_notice = False

	def held_on(self, day):
		"""Three punches on `day`, so the system holds it: nothing to pay against, which is
		the one case where HR may file a punch fix for somebody else."""
		from alvoraa_portal.tests import test_held_day_085 as hd

		for t, kind in (("09:00", "IN"), ("12:00", "OUT"), ("18:00", "OUT")):
			frappe.get_doc({"doctype": "Employee Checkin", "employee": self.emp,
			                "log_type": kind, "time": "%s %s:00" % (day, t)}
			               ).insert(ignore_permissions=True)
		att = frappe.get_doc({"doctype": "Attendance", "employee": self.emp,
		                      "company": self.h.company, "attendance_date": day,
		                      "status": "Present", "shift": hd.SHIFT,
		                      "in_time": "%s 09:00:00" % day})
		att.insert(ignore_permissions=True)
		att.submit()
		return att.name

	def _print(self, employees, month=None, user=None):
		frappe.set_user(user or self.hr)
		try:
			return register_notice.open_notices(employees, month or self.day)
		finally:
			frappe.set_user("Administrator")

	def _held_for(self, employee, day):
		"""Three punches and a submitted day for somebody other than the fixture's worker."""
		from alvoraa_portal.tests import test_held_day_085 as hd

		for t, kind in (("09:00", "IN"), ("12:00", "OUT"), ("18:00", "OUT")):
			frappe.get_doc({"doctype": "Employee Checkin", "employee": employee,
			                "log_type": kind, "time": "%s %s:00" % (day, t)}
			               ).insert(ignore_permissions=True)
		att = frappe.get_doc({"doctype": "Attendance", "employee": employee,
		                      "company": self.h.company, "attendance_date": day,
		                      "status": "Present", "shift": hd.SHIFT,
		                      "in_time": "%s 09:00:00" % day})
		att.insert(ignore_permissions=True)
		att.submit()
		return att.name

	def _list(self, month=None, start=0, user=None):
		frappe.set_user(user or self.hr)
		try:
			return register_notice.list_people(month or self.day, start)
		finally:
			frappe.set_user("Administrator")

	def _rows_for_me(self, month=None, user=None):
		"""This person's row, found by WALKING the pages.

		It used to read page one only, and that was fine until the site held more than 25
		people with changed days - then three tests started failing with IndexError and a
		paging assertion, because the fixture's worker had drifted onto page two. The list
		is sorted by name and `log_view` commits (which breaks this suite's per-test
		rollback), so how many people are ahead of this one is not something a test can
		assume. Walking the pages also means these tests exercise paging for free."""
		start, found, guard = 0, [], 0
		while guard < 40:
			guard += 1
			out = self._list(month, start=start, user=user)
			found += [r for r in out["rows"] if r["employee"] == self.emp]
			start += out["page"]
			if found or start >= out["total"]:
				return found
		return found

	def an_approved_hr_change(self, time="18:30"):
		"""One approved, unconfirmed, HR-filed change: exactly what a notice is printed for.

		**Each call needs its own day, and that is not test plumbing.** HR may only file a
		punch fix for a day the system has HELD (three punches, nothing to pay against). The
		approval fixes the day, so the same day is ordinary afterwards and HR is refused on
		it - 087 working exactly as it should. So a test that wants two approved HR changes
		has to hold two days, which is also what really happens."""
		day = self.day if not getattr(self, "_days", None) else \
			frappe.utils.add_days(self.day, -len(self._days))
		self._days = (getattr(self, "_days", None) or []) + [day]
		self.held_on(day)
		name = self.fix(time=time, by=self.hr, day=day)  # HR files it
		self.decide(name, 1, by=self.h.hr2)  # a second HR person decides: nobody decides their own
		self.assertEqual(frappe.db.get_value(REQUEST, name, "alvoraa_needs_confirm"), 1,
		                 "fixture is wrong: the change does not need a confirm, so there is "
		                 "nothing for a notice to be about")
		return name


class TheRecordExists(RegisterNoticeCase):
	def test_the_three_record_types_are_installed(self):
		for dt in (NOTICE, "Alvoraa Register Notice Change", "Alvoraa Register Notice Page"):
			self.assertTrue(frappe.db.exists("DocType", dt), dt + " is not installed")
		meta = frappe.get_meta(NOTICE)
		for field in ("employee", "month", "printed_by", "printed_at", "page_count", "outcome",
		              "recorded_by", "recorded_on", "dispute_reason", "changes", "pages"):
			self.assertTrue(meta.get_field(field), "no field " + field)
		self.assertEqual(meta.get_field("changes").options, "Alvoraa Register Notice Change")
		self.assertEqual(meta.get_field("pages").options, "Alvoraa Register Notice Page")

	def test_the_notice_switch_is_on_the_company_and_ships_off(self):
		"""23 Nov 2026. 088's own switch, beside ALV-430's rather than sharing it."""
		self.assertTrue(frappe.db.has_column("Company", register_notice.NOTICE_SWITCH))
		field = frappe.get_meta("Company").get_field(register_notice.NOTICE_SWITCH)
		self.assertEqual(field.fieldtype, "Check")
		self.assertEqual(field.default, "0", "the paper round must ship off")
		self.assertNotEqual(register_notice.NOTICE_SWITCH, punch_fix.CONFIRM_SWITCH,
		                    "the two switches have become one again")

	def test_the_switch_says_no_when_it_cannot_say_yes(self):
		"""Each refusal for its own reason, because one of them used to be the opposite.

		087's switch answers YES on a missing column, to keep the confirm alive between a
		deploy and its migrate. This one must answer NO: before the migrate there is no
		notice table to print into."""
		self.assertTrue(register_notice.notices_are_on(self.h.company), "the fixture is off")
		self.assertFalse(register_notice.notices_are_on(None), "an empty company said yes")
		self.assertFalse(register_notice.notices_are_on("No Such Company Ltd"),
		                 "an unknown company said yes")
		real = frappe.db.has_column
		frappe.db.has_column = lambda dt, col: False if col == register_notice.NOTICE_SWITCH \
			else real(dt, col)
		try:
			self.assertFalse(register_notice.notices_are_on(self.h.company),
			                 "a site whose migrate has not run yet was offered the print button")
		finally:
			frappe.db.has_column = real
		self.assertTrue(register_notice.notices_are_on(self.h.company),
		                "the patch was not undone")

	def test_the_signed_notice_column_is_on_the_request(self):
		self.assertTrue(frappe.db.has_column(REQUEST, punch_fix.SIGNED_NOTICE))
		self.assertTrue(punch_fix.signed_column_ready())
		self.assertTrue(register_notice.columns_ready())
		field = frappe.get_meta(REQUEST).get_field(punch_fix.SIGNED_NOTICE)
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, NOTICE)
		self.assertTrue(field.read_only, "a client must not be able to type a signature")

	def test_nobody_creates_exports_or_deletes_a_notice(self):
		"""Spec section 6, stated as a count: three roles read it and no role may do anything else."""
		perms = frappe.get_all("DocPerm", filters={"parent": NOTICE},
		                       fields=["role", "`read`", "`write`", "`create`", "`delete`",
		                               "report", "export"])
		self.assertEqual(sorted(p.role for p in perms),
		                 ["HR Manager", "HR User", "System Manager"])
		for p in perms:
			self.assertTrue(p.read, p.role + " cannot read")
			self.assertFalse(p.create, p.role + " can create a notice by hand")
			self.assertFalse(p.delete, p.role + " can delete a notice")
			self.assertFalse(p.report, p.role + " can report on notices")
			self.assertFalse(p.export, p.role + " can export notices")
			if p.role != "System Manager":
				self.assertFalse(p.write, p.role + " can edit a notice")

	def test_no_other_role_has_a_row_at_all(self):
		roles = {p.role for p in frappe.get_all("DocPerm", filters={"parent": NOTICE},
		                                        fields=["role"])}
		for outsider in ("Employee", "Employee Self Service", "All", "Biometric Sync"):
			self.assertNotIn(outsider, roles, outsider + " can see other people's notices")


class TheRecordRefusesToBeTyped(RegisterNoticeCase):
	def test_the_module_may_write_one_and_a_person_may_not(self):
		"""The control first: the module's own write works."""
		doc = self.notice([self.an_approved_hr_change()])
		self.assertTrue(doc.name.startswith("RN-"), doc.name)
		self.assertEqual(doc.outcome, "Printed")
		self.assertEqual(len(doc.changes), 1)
		# Now the same thing by hand, with no flag.
		self.refused(lambda: frappe.get_doc({
			"doctype": NOTICE, "employee": self.emp,
			"month": frappe.utils.get_first_day(self.day),
			"printed_by": "Administrator", "printed_at": now_datetime(),
			"page_count": 1, "outcome": "Printed",
			"changes": [{"request": self.an_approved_hr_change("19:30"), "page_no": 1,
			             "content_hash": "0" * 64}],
		}).insert(ignore_permissions=True), "created by printing it")

	def test_what_was_printed_cannot_be_edited_afterwards(self):
		doc = self.notice([self.an_approved_hr_change()])
		doc.reload()
		doc.page_count = 9
		self.refused(lambda: doc.save(ignore_permissions=True), "cannot be changed")
		doc.reload()
		doc.changes[0].page_no = 7
		self.refused(lambda: doc.save(ignore_permissions=True), "cannot be changed")
		self.assertEqual(frappe.db.get_value(NOTICE, doc.name, "page_count"), 1)

	def test_an_answer_cannot_be_rewritten_once_it_is_recorded(self):
		doc = self.notice([self.an_approved_hr_change()])
		frappe.flags.in_register_notice = True
		try:
			doc.outcome, doc.recorded_by, doc.recorded_on = "Signed", "Administrator", now_datetime()
			doc.save(ignore_permissions=True)
		finally:
			frappe.flags.in_register_notice = False
		doc.reload()
		doc.outcome = "Not right"
		self.refused(lambda: doc.save(ignore_permissions=True), "already been answered")
		self.assertEqual(frappe.db.get_value(NOTICE, doc.name, "outcome"), "Signed")

	def test_a_notice_is_never_deleted_by_anyone(self):
		doc = self.notice([self.an_approved_hr_change()])
		self.refused(lambda: frappe.delete_doc(NOTICE, doc.name, force=True,
		                                       ignore_permissions=True), "cannot be deleted")
		self.assertTrue(frappe.db.exists(NOTICE, doc.name),
		                "the record of what the employee was shown is gone")


class TheSeamWith087(RegisterNoticeCase):
	def test_signing_marks_the_changed_day_and_the_row_says_so(self):
		name = self.an_approved_hr_change()
		doc = self.notice([name])
		marked = punch_fix.record_register_signature([name], doc.name)
		self.assertEqual(marked, [name])
		self.assertEqual(frappe.db.get_value(REQUEST, name, punch_fix.SIGNED_NOTICE), doc.name,
		                 "the stored row does not carry the notice")

	def test_an_unsigned_change_still_holds_the_slip_and_a_signed_one_does_not(self):
		"""Both directions. Without the first assertion the second proves nothing:
		removing the gate entirely would also make the list empty."""
		name = self.an_approved_hr_change()
		before = punch_fix.unconfirmed_changes([self.emp], self.day, self.day)
		self.assertEqual([r["name"] for r in before], [name],
		                 "fixture is wrong: the change was not holding the slip to begin with")
		doc = self.notice([name])
		punch_fix.record_register_signature([name], doc.name)
		after = punch_fix.unconfirmed_changes([self.emp], self.day, self.day)
		self.assertEqual([r["name"] for r in after], [],
		                 "a change signed on the register is still holding the salary slip")

	def test_a_change_the_employee_already_confirmed_in_the_app_is_left_alone(self):
		name = self.an_approved_hr_change()
		self.confirm_as_employee(name)
		doc = self.notice([name])
		self.assertEqual(punch_fix.record_register_signature([name], doc.name), [])
		self.assertFalse(frappe.db.get_value(REQUEST, name, punch_fix.SIGNED_NOTICE),
		                 "a confirm in the app was overwritten by a paper signature")

	def test_an_undone_or_declined_change_is_left_alone(self):
		undone = self.an_approved_hr_change("18:30")
		frappe.db.set_value(REQUEST, undone, "alvoraa_undone_on", now_datetime())
		declined = self.an_approved_hr_change("19:30")
		frappe.db.set_value(REQUEST, declined, "alvoraa_review_status", "Declined")
		doc = self.notice([undone, declined])
		self.assertEqual(punch_fix.record_register_signature([undone, declined], doc.name), [])
		for name in (undone, declined):
			self.assertFalse(frappe.db.get_value(REQUEST, name, punch_fix.SIGNED_NOTICE))

	def test_signing_twice_marks_nothing_the_second_time(self):
		name = self.an_approved_hr_change()
		first = self.notice([name])
		second = self.notice([name])
		self.assertEqual(punch_fix.record_register_signature([name], first.name), [name])
		self.assertEqual(punch_fix.record_register_signature([name], second.name), [],
		                 "a reprint re-signed a day that was already signed")
		self.assertEqual(frappe.db.get_value(REQUEST, name, punch_fix.SIGNED_NOTICE), first.name,
		                 "the second page took the first page's signature")

	def test_a_notice_that_does_not_exist_is_refused(self):
		name = self.an_approved_hr_change()
		self.refused(lambda: punch_fix.record_register_signature([name], "RN-99999"),
		             "does not exist")
		self.refused(lambda: punch_fix.record_register_signature([name], None),
		             "does not exist")
		self.assertFalse(frappe.db.get_value(REQUEST, name, punch_fix.SIGNED_NOTICE))

	def test_a_client_cannot_sign_its_own_change(self):
		"""Two walls, and the first run of this test found the second one.

		On an APPROVED request Frappe itself refuses the field outright, because it is not
		`allow_on_submit` - the same as 087's confirm fields, and the reason both are written
		with `db.set_value` rather than a save. On a request still WAITING there is no such
		wall, so `_own_the_confirm_fields` puts the stored value back and the client's value
		is silently dropped. Tested both ways round, because either on its own would let the
		other regress unnoticed."""
		name = self.an_approved_hr_change()
		doc = self.notice([name])

		approved = frappe.get_doc(REQUEST, name)
		approved.set(punch_fix.SIGNED_NOTICE, doc.name)
		self.refused(lambda: approved.save(ignore_permissions=True), "after submission")
		self.assertFalse(frappe.db.get_value(REQUEST, name, punch_fix.SIGNED_NOTICE))

		waiting = self.fix(time="09:30", by=self.emp_user, day=self.day)
		req = frappe.get_doc(REQUEST, waiting)
		req.set(punch_fix.SIGNED_NOTICE, doc.name)
		req.save(ignore_permissions=True)
		self.assertFalse(frappe.db.get_value(REQUEST, waiting, punch_fix.SIGNED_NOTICE),
		                 "a client signed its own waiting change by sending the field")

		# And the module's own write still works on the approved one.
		punch_fix.record_register_signature([name], doc.name)
		self.assertEqual(frappe.db.get_value(REQUEST, name, punch_fix.SIGNED_NOTICE), doc.name)

	def test_a_new_request_never_arrives_already_signed(self):
		doc = self.notice([self.an_approved_hr_change()])
		frappe.set_user(self.emp_user)
		try:
			req = frappe.get_doc({"doctype": REQUEST, "employee": self.emp,
			                      "from_date": self.day, "to_date": self.day,
			                      "reason": "Forgot to Punch In", "alvoraa_missing_time": "19:45",
			                      "alvoraa_review_status": "Waiting"})
			req.set(punch_fix.SIGNED_NOTICE, doc.name)
			req.insert(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")
		self.assertFalse(frappe.db.get_value(REQUEST, req.name, punch_fix.SIGNED_NOTICE),
		                 "a request was created pre-signed")

	def test_the_signature_is_written_to_the_security_log(self):
		from alvoraa_portal.tests.test_punch_fix_087 import security_lines_from_a_fresh_process

		name = self.an_approved_hr_change()
		doc = self.notice([name])
		lines = security_lines_from_a_fresh_process(
			lambda: punch_fix.record_register_signature([name], doc.name))
		self.assertTrue(any("register signature" in l and doc.name in l for l in lines),
		                "no security line for a recorded signature: " + repr(lines))


class TheHRList(RegisterNoticeCase):
	"""US-1, AC-1 to AC-10: who needs a notice this month, and nothing more than that."""

	def test_a_change_hr_filed_puts_the_person_on_the_list_not_printed_yet(self):
		"""AC-1."""
		self.an_approved_hr_change()
		# Through the page-walking helper, not off page one. This test was the last one
		# still reading `rows` directly, and it failed in two runs back to back once the
		# site held more than 25 people with changed days - the fixture's worker was on
		# page two. The same fault I fixed in the helper, left behind in one caller.
		mine = self._rows_for_me()
		out = self._list()
		self.assertEqual(len(mine), 1, "this person is not in the month list at all")
		self.assertEqual(mine[0]["changed_days"], 1)
		self.assertEqual(mine[0]["open_days"], 1)
		self.assertEqual(mine[0]["state"], "not_printed")
		# The summary counts everybody in HR's scope. It cannot be asserted as an absolute
		# here: `log_view` commits, which breaks this suite's per-test rollback, so rows
		# from earlier tests are still in the month. Asserted as arithmetic plus this
		# person's share - which is what the screen actually needs to be right.
		self.assertEqual(out["done"] + out["waiting"], out["total"])
		self.assertGreaterEqual(out["waiting"], 1)

	def test_the_employees_own_change_and_a_break_glass_one_are_not_on_the_list(self):
		"""AC-2, two of its cases. The control is in the test above: an HR-filed change IS listed."""
		self.held_on(self.day)
		own = self.fix(time="18:30", by=self.emp_user)
		self.decide(own, 1, by=self.hr)
		self.assertEqual(self._rows_for_me(), [], "the employee's own change needs no notice")

		day2 = frappe.utils.add_days(self.day, -1)
		self.held_on(day2)
		admin = self.fix(time="18:30", by="Administrator", day=day2)
		self.decide(admin, 1, by=self.hr)
		self.assertEqual(self._rows_for_me(), [],
		                 "a break-glass change was treated as somebody filing for the employee")

	def test_a_waiting_or_declined_change_is_not_on_the_list(self):
		"""AC-2, its other cases: only an approved change can say what a day now counts."""
		self.held_on(self.day)
		waiting = self.fix(time="18:30", by=self.hr)
		self.assertEqual(self._rows_for_me(), [], "a change nobody has approved yet was listed")
		self.decide(waiting, 0, by=self.h.hr2, note="Punch already counted")  # declined
		self.assertEqual(self._rows_for_me(), [], "a declined change was listed")

	def test_a_managers_addition_is_on_the_list_even_though_it_never_blocks_pay(self):
		"""AC-3 and design gate D-4. A manager's plain addition needs no confirm (087), so it
		holds nobody's slip - and it is still a change somebody made FOR the employee, which
		is what the paper is about. The two rules are independent and this proves it."""
		mgr = self.h._login("mgr088", ())
		self.h._employee("Mgr088", mgr)
		self.held_on(self.day)
		req = self.fix(time="18:30", by=mgr)
		self.assertEqual(frappe.db.get_value(REQUEST, req, "alvoraa_needs_confirm"), 0,
		                 "fixture is wrong: a manager's addition should not need a confirm")
		self.decide(req, 1, by=self.hr)
		rows = self._rows_for_me()
		self.assertEqual(len(rows), 1, "a manager's addition is not on the list")
		self.assertEqual(rows[0]["state"], "not_printed")

	def test_a_person_whose_changes_are_all_answered_shows_done_and_cannot_be_ticked(self):
		"""AC-4."""
		name = self.an_approved_hr_change()
		self.confirm_as_employee(name)
		rows = self._rows_for_me()
		self.assertEqual(len(rows), 1, "a done person left the month list altogether")
		self.assertEqual(rows[0]["state"], "done")
		self.assertEqual(rows[0]["open_days"], 0)
		self.assertFalse(rows[0]["can_tick"], "a done person can still be ticked for printing")
		out = self._list()
		# The summary counts everybody in HR's scope, so this asserts the arithmetic and
		# this person's share of it, not a total that other fixtures can move.
		self.assertEqual(out["done"] + out["waiting"], out["total"])
		self.assertGreaterEqual(out["done"], 1, "the done person is not counted as done")

	def test_the_state_follows_the_print_and_a_later_change_warns(self):
		"""AC-1 state ladder, and section 5.3's "changed after printing"."""
		first = self.an_approved_hr_change()
		notice = self.notice([first])
		# Read as hr2: `self.hr` FILED this change, so for them the row is "filer", which the
		# test below covers. The state ladder is about the paper, not about who is looking.
		self.assertEqual(self._rows_for_me(user=self.h.hr2)[0]["state"], "printed")

		self.an_approved_hr_change("19:30")              # its own held day, filed after the print
		row = self._rows_for_me(user=self.h.hr2)[0]
		self.assertEqual(row["state"], "changed_after_print")
		self.assertEqual(row["uncovered"], 1,
		                 "the row does not say how many changes are not on the printed page")
		self.assertEqual(row["notice"], notice.name)

	def test_the_filer_is_not_offered_the_record_button_and_another_hr_person_is(self):
		"""Section 5.3 "Filer", and SEC-4. Both sides, because a button only hidden for one
		user proves nothing about the other."""
		name = self.an_approved_hr_change()              # filed by self.hr
		self.notice([name])
		as_filer = self._rows_for_me(user=self.hr)[0]
		self.assertEqual(as_filer["state"], "filer")
		self.assertTrue(as_filer["i_filed"])
		self.assertFalse(as_filer["can_record"], "the filer is offered the record button")
		as_other = self._rows_for_me(user=self.h.hr2)[0]
		self.assertEqual(as_other["state"], "printed")
		self.assertTrue(as_other["can_record"], "another HR person cannot record the signature")

	def test_a_month_with_nothing_is_empty_and_says_which_month(self):
		"""AC-6."""
		self.an_approved_hr_change()
		out = self._list(month=frappe.utils.add_months(self.day, -3))
		self.assertEqual(out["rows"], [])
		self.assertEqual((out["total"], out["done"], out["waiting"]), (0, 0, 0))
		self.assertEqual(out["month"], str(frappe.utils.get_first_day(
			frappe.utils.add_months(self.day, -3))))

	def test_the_response_carries_no_reason_no_time_and_no_request(self):
		"""AC-8, the one the spec marks "fails first". The reason text is the most sensitive
		thing on the sheet and a list is the one screen that puts many people in one payload,
		so the test names the forbidden keys rather than trusting the code's shape."""
		name = self.an_approved_hr_change()
		frappe.db.set_value(REQUEST, name, "explanation", "secret words about this person")
		out = self._list()
		blob = frappe.as_json(out)
		for forbidden in ("explanation", "reason", "alvoraa_missing_time", "alvoraa_set_aside",
		                  "from_date", "content_hash", "secret words about this person"):
			self.assertNotIn(forbidden, blob, forbidden + " left the server in the list payload")
		self.assertEqual(sorted(out["rows"][0].keys()),
		                 sorted(["employee", "employee_name", "employee_number", "branch",
		                         "changed_days", "open_days", "state", "uncovered", "i_filed",
		                         "printed_at", "printed_by", "recorded_by", "recorded_on",
		                         "said", "notice", "can_tick", "can_record"]))

	def test_an_employee_and_a_line_manager_are_refused(self):
		"""AC-9 and US-8. The control is every other test here, which calls it as HR."""
		self.an_approved_hr_change()
		for who in (self.emp_user, self.h._login("mgrnope", ())):
			frappe.set_user(who)
			try:
				self.refused(lambda: register_notice.list_people(self.day), "for HR")
			finally:
				frappe.set_user("Administrator")

	def test_hr_in_another_company_sees_nobody(self):
		"""AC-9's scope half: in scope is not the same as having the role."""
		self.an_approved_hr_change()
		outsider = self.h._login("hrfar", ("HR Manager",))   # no company permission at all
		frappe.set_user(outsider)
		try:
			out = register_notice.list_people(self.day)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(out["rows"], [], "HR with no company permission can see this person")

	def test_the_list_is_empty_when_the_organisation_does_not_print_notices(self):
		"""The paper round is a per-company choice, and it ships off.

		Asserted in both directions in one test, because "empty" on its own is also what a
		broken query returns."""
		self.an_approved_hr_change()
		self.assertEqual(len(self._rows_for_me()), 1, "fixture is wrong: nothing to hide")
		self._set_notices(0)
		self.assertEqual(self._rows_for_me(), [],
		                 "a company that does not print notices is still being told to")

	def test_the_confirm_switch_does_not_decide_the_paper_round(self):
		"""23 Nov 2026. The fault this split exists to fix.

		DTC and Grace run with confirmations OFF, because their staff have no app - and
		until today that is exactly what hid the paper round from them. The two switches
		now answer two different questions, so turning the confirm off must leave the
		notice list alone."""
		self.an_approved_hr_change()
		frappe.db.set_value("Company", self.h.company, punch_fix.CONFIRM_SWITCH, 0,
		                    update_modified=False)
		frappe.clear_cache()
		self.assertEqual(len(self._rows_for_me()), 1,
		                 "switching confirmations off still empties the notice list")

	def test_paging_holds_the_page_size_and_the_true_total(self):
		"""AC-7. Four people is enough to prove the arithmetic; 25 would only prove patience."""
		self.an_approved_hr_change()
		out = self._list()
		self.assertEqual(out["page"], 25)
		self.assertEqual(out["start"], 0)
		# A page holds at most 25 and the total is the TRUE number, which is the whole point
		# of sending both: "Showing 25 of 60" cannot be written from one of them. Asserted
		# as min(), not as equality - the suite's own site has more than 25 people with
		# changed days, which is how this assertion was caught being wrong.
		self.assertEqual(len(out["rows"]), min(out["total"], 25))
		later = self._list(start=1)
		self.assertEqual(later["start"], 1)
		self.assertEqual(later["total"], out["total"],
		                 "the total changed between pages, so the summary cannot be trusted")
		self.assertEqual(later["rows"][:len(out["rows"]) - 1], out["rows"][1:])

	def test_the_call_is_post_only_and_rate_limited_per_user(self):
		"""AC-17's share of this story: the limit is on the user, never the address, because
		a store shares one address (spec section 8)."""
		self.assertEqual(register_notice.list_people.__alvoraa_limit__[1:],
		                 ("user", 60, 60))
		self.assertIn("POST", getattr(register_notice.list_people, "methods", ["POST"]))

	# ── helpers ─────────────────────────────────────────────────────────





class ThePrintCall(RegisterNoticeCase):
	"""US-2, AC-11 to AC-17: the record is written before any content leaves the server."""

	def test_nothing_prints_where_the_organisation_does_not_print_notices(self):
		"""The gap the first version of the switch left.

		The list and the employee's view each had a test for being switched off; the print
		call had none, so a reader could have been added here and nobody would have known.
		It is the one that matters most: printing WRITES a permanent record."""
		self.an_approved_hr_change()
		self.assertTrue(self._print([self.emp])["sheets"], "fixture is wrong: nothing to hide")
		before = frappe.db.count(NOTICE)
		self._set_notices(0)
		# It REFUSES rather than returning an empty page, which is the better of the two:
		# an HR person who reaches this call anyway is told, instead of staring at a blank
		# screen. The words are deliberately about the days, not about the setting - a
		# refusal should not read out a tenant's configuration.
		self.refused(lambda: self._print([self.emp]), "no changed days waiting")
		self.assertEqual(frappe.db.count(NOTICE), before,
		                 "a notice record was written for a company that is switched off")

	def test_printing_writes_one_notice_then_returns_the_sheet(self):
		"""AC-11. The row is checked first and the content second, in that order, because
		that is the order the requirement is about."""
		name = self.an_approved_hr_change()
		out = self._print([self.emp])
		rows = frappe.get_all(NOTICE, filters={"employee": self.emp,
		                                       "month": str(frappe.utils.get_first_day(self.day))},
		                      fields=["name", "printed_by", "printed_at", "page_count", "outcome"])
		self.assertEqual(len(rows), 1, rows)
		self.assertEqual(rows[0].printed_by, self.hr)
		self.assertTrue(rows[0].printed_at)
		self.assertEqual(rows[0].page_count, 1)
		self.assertEqual(rows[0].outcome, "Printed")
		covered = frappe.get_all("Alvoraa Register Notice Change",
		                         filters={"parent": rows[0].name},
		                         fields=["request", "page_no", "content_hash"])
		self.assertEqual(len(covered), 1)
		self.assertEqual(covered[0].request, name)
		self.assertEqual(covered[0].page_no, 1)
		self.assertEqual(len(covered[0].content_hash), 64, "the hash is not a SHA-256")
		self.assertEqual(len(out["sheets"]), 1)
		self.assertEqual(out["sheets"][0]["notice"], rows[0].name)

	def test_the_sheet_says_the_day_what_changed_and_what_it_now_counts(self):
		"""US-3's content, as the approved prototype words it."""
		self.an_approved_hr_change("18:30")
		sheet = self._print([self.emp])["sheets"][0]
		change = sheet["changes"][0]
		self.assertRegex(change["day"], r"^[A-Z][a-z]{2} \d{1,2} [A-Z][a-z]{2}$")
		self.assertEqual(change["what"], ["Out time 18:30 added"])
		self.assertRegex(change["counts"], r"^\d+ h \d+ m$")
		self.assertEqual(change["filed_role"], "HR")
		self.assertIsNone(change["filed_by"],
		                  "the sheet names the HR person; Surbhi's OQ-1 decision says it "
		                  "prints HR with no name")

	def test_a_managers_change_is_named_and_hr_is_not(self):
		"""Surbhi's OQ-1 decision and 087 decision 7, both halves in one test."""
		mgr = self.h._login("mgrprint", ())
		self.h._employee("Mgrprint", mgr)
		self.held_on(self.day)
		req = self.fix(time="18:30", by=mgr)
		self.decide(req, 1, by=self.hr)
		change = self._print([self.emp])["sheets"][0]["changes"][0]
		self.assertEqual(change["filed_role"], "Manager")
		self.assertTrue(change["filed_by"], "a manager's change is not named on the sheet")

	def test_the_reason_reaches_the_page_exactly_as_it_is_stored(self):
		"""Spec 5.2 ("the filer's reason as written, in full") and SEC-9.

		**Measured, and it changes what this test can honestly claim.** Frappe sanitises a
		Small Text field on insert (`frappe.utils.html_utils.clean_html` via
		`sanitize_html`), so a reason typed with angle brackets is altered the moment the
		change is FILED - on 087's surface, before slice 088 ever sees it. My first version
		of this test asserted the page carries what the filer typed and failed with
		`<img src=x onerror=...>` stored as `<img src="x">`.

		So what 088 can promise is the thing 088 controls: the page carries exactly what is
		stored, unaltered, and nothing executable survives to the page. Whether the storage
		should be changing HR's words at all is a question about 087's field, not this slice,
		and it is raised separately rather than papered over here.
		"""
		self.held_on(self.day)
		nasty = '<img src=x onerror=window.__x=1> he said he forgot'
		req = self.fix(time="18:30", by=self.hr, note=nasty)
		self.decide(req, 1, by=self.h.hr2)
		stored = frappe.db.get_value(REQUEST, req, "explanation")
		change = self._print([self.emp])["sheets"][0]["changes"][0]
		self.assertEqual(change["why"], stored,
		                 "the page does not carry what is actually on the record")
		self.assertNotIn("onerror", change["why"], "an event handler reached the page")
		self.assertIn("he said he forgot", change["why"],
		              "the filer's actual words were lost on the way to the page")

	def test_the_pay_line_prints_only_where_the_page_holds_a_change_that_holds_pay(self):
		"""D-7. A page of manager additions must not carry it, because it would be false:
		a manager's addition does not hold the salary slip (087)."""
		self.an_approved_hr_change()                     # HR-filed: needs a confirm
		self.assertTrue(self._print([self.emp])["sheets"][0]["pay_line"])

		mgr = self.h._login("mgrpay", ())
		self.h._employee("Mgrpay", mgr)
		other = self.h._login("worker2pay", ())
		emp2 = self.h._employee("Worker2Pay", other)
		self._held_for(emp2, self.day)
		req = self.fix(time="18:30", by=mgr, employee=emp2)
		self.assertEqual(frappe.db.get_value(REQUEST, req, "alvoraa_needs_confirm"), 0)
		self.decide(req, 1, by=self.hr)
		sheet = self._print([emp2])["sheets"][0]
		self.assertFalse(sheet["pay_line"],
		                 "a page of manager additions tells the worker their pay is held")

	def test_five_changes_fill_a_page_and_the_sixth_starts_another(self):
		"""Spec 5.2: five per page, and the SERVER decides which page, not the browser."""
		for n in range(6):
			self.an_approved_hr_change("1%d:30" % (n + 2))
		out = self._print([self.emp])
		self.assertEqual(len(out["sheets"]), 2)
		self.assertEqual([len(s["changes"]) for s in out["sheets"]], [5, 1])
		self.assertEqual([s["page_no"] for s in out["sheets"]], [1, 2])
		self.assertEqual({s["pages"] for s in out["sheets"]}, {2})
		notice = frappe.get_doc(NOTICE, out["sheets"][0]["notice"])
		self.assertEqual(notice.page_count, 2)
		self.assertEqual(sorted(r.page_no for r in notice.changes), [1, 1, 1, 1, 1, 2],
		                 "the stored record disagrees with the pages that were printed")

	def test_the_reference_carries_the_month_the_page_and_the_print_number(self):
		"""Parity P-9, which Surbhi approved: a reprint must be tellable from the page
		before it."""
		self.an_approved_hr_change()
		sheet = self._print([self.emp])["sheets"][0]
		self.assertTrue(sheet["ref"].endswith("/2026-11/1-1"), sheet["ref"])
		self.assertTrue(sheet["print_no"].startswith("RN-"), sheet["print_no"])
		again = self._print([self.emp])["sheets"][0]
		self.assertNotEqual(again["print_no"], sheet["print_no"],
		                    "a reprint carries the same print number as the first page")

	def test_more_than_a_hundred_people_is_refused_and_nothing_is_written(self):
		"""AC-13. The count before and after proves "nothing was written", which a refusal
		message on its own does not."""
		self.an_approved_hr_change()
		before = frappe.db.count(NOTICE)
		self.refused(lambda: self._print([self.emp] * 2 + ["HR-EMP-%05d" % n for n in range(101)]),
		             "up to 100 at a time")
		self.assertEqual(frappe.db.count(NOTICE), before, "a refused batch still wrote rows")

	def test_a_person_who_is_already_done_is_not_printed(self):
		name = self.an_approved_hr_change()
		self.confirm_as_employee(name)
		before = frappe.db.count(NOTICE)
		self.refused(lambda: self._print([self.emp]), "no changed days waiting")
		self.assertEqual(frappe.db.count(NOTICE), before,
		                 "a page with nothing on it still wrote a record saying the employee "
		                 "was shown something")

	def test_an_employee_and_an_out_of_scope_hr_user_are_refused(self):
		"""AC-9's share of this story, and US-8."""
		self.an_approved_hr_change()
		frappe.set_user(self.emp_user)
		try:
			self.refused(lambda: register_notice.open_notices([self.emp], self.day), "for HR")
		finally:
			frappe.set_user("Administrator")
		outsider = self.h._login("hrfarprint", ("HR Manager",))
		before = frappe.db.count(NOTICE)
		self.refused(lambda: self._print([self.emp], user=outsider),
		             "outside the ones you look after")
		self.assertEqual(frappe.db.count(NOTICE), before)

	def test_no_reason_no_hours_and_no_change_text_are_stored_on_the_notice(self):
		"""AC-15 and OPS-20. The record is a log, not a copy of the page."""
		self.held_on(self.day)
		req = self.fix(time="18:30", by=self.hr, note="secret words on the record")
		self.decide(req, 1, by=self.h.hr2)
		out = self._print([self.emp])
		doc = frappe.get_doc(NOTICE, out["sheets"][0]["notice"])
		blob = frappe.as_json(doc.as_dict())
		for forbidden in ("secret words on the record", "18:30", "Out time"):
			self.assertNotIn(forbidden, blob, forbidden + " is stored on the notice record")

	def test_the_call_is_rate_limited_to_ten_a_minute_per_user(self):
		"""AC-17's share: keyed on the user, never the address - a store shares one."""
		self.assertEqual(register_notice.open_notices.__alvoraa_limit__[1:], ("user", 10, 60))

	def test_the_printed_page_is_written_to_the_security_log(self):
		from alvoraa_portal.tests.test_punch_fix_087 import security_lines_from_a_fresh_process

		self.an_approved_hr_change()
		lines = security_lines_from_a_fresh_process(lambda: self._print([self.emp]))
		self.assertTrue(any("register_notice printed" in l for l in lines),
		                "no security line for a released page: " + repr(lines))



def _a_jpeg(colour=None, size=(40, 40)):
	"""A real JPEG, because 081's decoder reads magic bytes and then asks Pillow. A made-up
	byte string would be refused for the wrong reason and prove nothing.

	**Every call gives DIFFERENT bytes unless a colour is named**, and that is not a detail.
	The first version returned the same grey square each time, and thirteen tests died on
	"That photo was already used" - the SEC-7 reuse check doing its job on a fixture that
	was lying about the world. Two HR people photographing two signed pages never produce
	byte-identical files. The reuse test names its colour so it can hand the same photo in
	twice on purpose."""
	import base64, io as _io, random

	from PIL import Image

	if colour is None:
		colour = (random.randrange(256), random.randrange(256), random.randrange(256))
	buf = _io.BytesIO()
	Image.new("RGB", size, colour).save(buf, format="JPEG")
	return base64.b64encode(buf.getvalue()).decode()


class RecordingTheSignature(RegisterNoticeCase):
	"""US-4 and US-5, AC-27 to AC-43."""

	def test_a_second_hr_person_records_signed_and_the_slip_block_lifts(self):
		"""AC-27, end to end: the stored values, the photo, and the pay gate."""
		name = self.an_approved_hr_change()
		out = self._print([self.emp])
		notice = out["sheets"][0]["notice"]
		self.assertEqual(punch_fix.unconfirmed_changes([self.emp], self.day, self.day)[0]["name"],
		                 name, "fixture is wrong: the change is not holding the slip")

		res = self._record(notice, "Signed", photos=[_a_jpeg()], user=self.h.hr2)
		self.assertEqual(res["marked"], 1)
		doc = frappe.get_doc(NOTICE, notice)
		self.assertEqual(doc.outcome, "Signed")
		self.assertEqual(doc.recorded_by, self.h.hr2)
		self.assertTrue(doc.recorded_on)
		self.assertEqual(len(doc.pages), 1)
		self.assertEqual(frappe.db.get_value(REQUEST, name, punch_fix.SIGNED_NOTICE), notice)
		self.assertEqual(punch_fix.unconfirmed_changes([self.emp], self.day, self.day), [],
		                 "the slip is still held after the register was signed")

	def test_one_photo_per_page_is_required_and_the_message_counts_both(self):
		"""AC-28."""
		for n in range(6):
			self.an_approved_hr_change("1%d:30" % (n + 2))
		notice = self._print([self.emp])["sheets"][0]["notice"]
		self.assertEqual(frappe.db.get_value(NOTICE, notice, "page_count"), 2)
		self.refused(lambda: self._record(notice, "Signed", photos=[_a_jpeg()],
		                                 user=self.h.hr2), "Add 2 photos", "You added 1")
		self.assertEqual(frappe.db.get_value(NOTICE, notice, "outcome"), "Printed")
		res = self._record(notice, "Signed",
		                   photos=[_a_jpeg((10, 20, 30)), _a_jpeg((40, 50, 60))],
		                   user=self.h.hr2)
		self.assertEqual(res["photos"], 2)

	def test_a_change_edited_since_the_print_stays_open_and_is_named_back(self):
		"""AC-29, the one the spec marks "fails first". The employee signed a page that said
		something else, so that change is not marked - and the others on the page still are."""
		first = self.an_approved_hr_change("18:30")
		second = self.an_approved_hr_change("19:30")
		notice = self._print([self.emp])["sheets"][0]["notice"]
		frappe.db.set_value(REQUEST, second, "explanation", "HR changed the words after printing")

		res = self._record(notice, "Signed", photos=[_a_jpeg()], user=self.h.hr2)
		self.assertEqual(res["marked"], 1)
		self.assertEqual(res["stale"], [second])
		self.assertEqual(frappe.db.get_value(REQUEST, first, punch_fix.SIGNED_NOTICE), notice)
		self.assertFalse(frappe.db.get_value(REQUEST, second, punch_fix.SIGNED_NOTICE),
		                 "a change edited after the print was marked as signed anyway")

	def test_the_caller_cannot_choose_which_days_are_covered(self):
		"""AC-31. The covered days come from the record; a list in the body is ignored."""
		name = self.an_approved_hr_change("18:30")
		notice = self._print([self.emp])["sheets"][0]["notice"]
		other = self.an_approved_hr_change("19:30")      # printed on no page
		self._record(notice, "Signed", photos=[_a_jpeg()], user=self.h.hr2,
		             extra={"requests": [other], "changes": [other]})
		self.assertEqual(frappe.db.get_value(REQUEST, name, punch_fix.SIGNED_NOTICE), notice)
		self.assertFalse(frappe.db.get_value(REQUEST, other, punch_fix.SIGNED_NOTICE),
		                 "a day the caller named was marked although it was on no page")

	def test_an_older_notice_cannot_be_recorded_once_a_newer_one_is_printed(self):
		"""AC-33, D-10: stops an old paper being produced after a reprint."""
		self.an_approved_hr_change()
		first = self._print([self.emp])["sheets"][0]["notice"]
		second = self._print([self.emp])["sheets"][0]["notice"]
		self.assertNotEqual(first, second)
		self.refused(lambda: self._record(first, "Signed", photos=[_a_jpeg()],
		                                 user=self.h.hr2), "A newer notice was printed")
		self._record(second, "Signed", photos=[_a_jpeg()], user=self.h.hr2)

	def test_a_notice_cannot_be_answered_twice(self):
		self.an_approved_hr_change()
		notice = self._print([self.emp])["sheets"][0]["notice"]
		self._record(notice, "Signed", photos=[_a_jpeg()], user=self.h.hr2)
		self.refused(lambda: self._record(notice, "Not right", reason="later", user=self.hr),
		             "already been answered")

	def test_the_filer_is_refused_on_the_endpoint_and_another_hr_person_succeeds(self):
		"""AC-58. The screen hides the button; this proves the server refuses it anyway."""
		self.an_approved_hr_change()                     # filed by self.hr
		notice = self._print([self.emp])["sheets"][0]["notice"]
		self.refused(lambda: self._record(notice, "Signed", photos=[_a_jpeg()], user=self.hr),
		             "another HR person records")
		self.assertEqual(frappe.db.get_value(NOTICE, notice, "outcome"), "Printed")
		res = self._record(notice, "Signed", photos=[_a_jpeg()], user=self.h.hr2)
		self.assertEqual(res["marked"], 1)

	def test_a_photo_cannot_be_used_twice(self):
		"""AC-36, SEC-7: one clear photo of one signed page must not stand for a shop."""
		self.an_approved_hr_change()
		notice = self._print([self.emp])["sheets"][0]["notice"]
		same = _a_jpeg((7, 8, 9))
		self._record(notice, "Signed", photos=[same], user=self.h.hr2)

		other = self.h._login("worker2reuse", ())
		emp2 = self.h._employee("Worker2Reuse", other)
		self._held_for(emp2, self.day)
		req = self.fix(time="18:30", by=self.hr, employee=emp2)
		self.decide(req, 1, by=self.h.hr2)
		notice2 = self._print([emp2])["sheets"][0]["notice"]
		self.refused(lambda: self._record(notice2, "Signed", photos=[same], user=self.h.hr2),
		             "already used")

	def test_a_pdf_and_rubbish_are_refused_and_nothing_is_recorded(self):
		"""AC-34's share: a PDF is a scan made somewhere else, not a photo of a page
		somebody just signed."""
		import base64

		self.an_approved_hr_change()
		notice = self._print([self.emp])["sheets"][0]["notice"]
		pdf = base64.b64encode(b"%PDF-1.4 not really").decode()
		self.refused(lambda: self._record(notice, "Signed", photos=[pdf], user=self.h.hr2),
		             "not a PDF")
		zip_as_jpg = base64.b64encode(b"PK\x03\x04 pretending").decode()
		self.refused(lambda: self._record(notice, "Signed", photos=[zip_as_jpg],
		                                 user=self.h.hr2))
		self.assertEqual(frappe.db.get_value(NOTICE, notice, "outcome"), "Printed")
		self.assertEqual(frappe.db.count("File", {"attached_to_name": notice}), 0,
		                 "a refused photo was stored anyway")

	def test_the_stored_photo_is_private_named_by_us_and_carries_no_exif(self):
		"""AC-34, AC-35 and AC-44's first half."""
		self.an_approved_hr_change()
		notice = self._print([self.emp])["sheets"][0]["notice"]
		self._record(notice, "Signed", photos=[_a_jpeg()], user=self.h.hr2)
		f = frappe.get_doc("File", {"attached_to_doctype": NOTICE, "attached_to_name": notice})
		self.assertTrue(f.is_private, "the signed page is a public file")
		self.assertEqual(f.attached_to_doctype, NOTICE,
		                 "the photo hangs off something the employee can read")
		name = frappe.db.get_value("Employee", self.emp, "employee_name")
		self.assertNotIn(name.lower(), f.file_name.lower())
		self.assertNotIn(self.emp.lower(), f.file_name.lower())
		self.assertTrue(f.file_name.endswith(".jpg"), f.file_name)
		self.assertLessEqual(len(f.get_content()), 1024 * 1024)

	def test_says_it_is_not_right_needs_a_reason_keeps_the_block_and_stores_no_photo(self):
		"""AC-40, AC-41."""
		name = self.an_approved_hr_change()
		notice = self._print([self.emp])["sheets"][0]["notice"]
		self.refused(lambda: self._record(notice, "Not right", reason="  ", user=self.h.hr2),
		             "Write what they said")
		self.assertEqual(frappe.db.get_value(NOTICE, notice, "outcome"), "Printed")

		res = self._record(notice, "Not right", reason="I was there till 7", user=self.h.hr2)
		self.assertEqual(res["marked"], 0)
		doc = frappe.get_doc(NOTICE, notice)
		self.assertEqual(doc.outcome, "Not right")
		self.assertEqual(doc.dispute_reason, "I was there till 7")

		self.assertEqual(doc.recorded_by, self.h.hr2)
		self.assertEqual(len(doc.pages), 0, "a dispute stored a photo")
		self.assertFalse(frappe.db.get_value(REQUEST, name, punch_fix.SIGNED_NOTICE))
		self.assertEqual([r["name"] for r in
		                  punch_fix.unconfirmed_changes([self.emp], self.day, self.day)], [name],
		                 "the slip stopped being held although the worker objected")

	def test_a_disagreement_that_would_empty_itself_is_refused(self):
		"""ALV-436 on the one surface where the employee gets to disagree.

		`dispute_reason` is a Small Text like 087's `explanation`, so the same save would
		have cleaned it away. This is the worse of the two places for it to happen: the
		employee's own words, on the record of a page they refused to accept. Both sides
		asserted, and the notice is checked to be untouched by the refusal."""
		self.an_approved_hr_change()
		notice = self._print([self.emp])["sheets"][0]["notice"]
		self.refused(lambda: self._record(notice, "Not right", reason="<I was there till 7>",
		                                  user=self.h.hr2), "without < and >")
		self.assertEqual(frappe.db.get_value(NOTICE, notice, "outcome"), "Printed",
		                 "a refused disagreement changed the notice")
		self.assertFalse(frappe.db.get_value(NOTICE, notice, "dispute_reason"),
		                 "a refused disagreement was stored anyway")
		# The control: ordinary words go through, character for character.
		self._record(notice, "Not right", reason="I was there till 7 & told the guard",
		             user=self.h.hr2)
		self.assertEqual(frappe.db.get_value(NOTICE, notice, "dispute_reason"),
		                 "I was there till 7 & told the guard")

	def test_the_row_then_says_what_the_worker_said(self):
		"""AC-42: the objection reaches the HR list, as text."""
		self.an_approved_hr_change()
		notice = self._print([self.emp])["sheets"][0]["notice"]
		self._record(notice, "Not right", reason="I was there till 7", user=self.h.hr2)
		row = self._rows_for_me(user=self.h.hr2)[0]
		self.assertEqual(row["state"], "not_right")
		self.assertEqual(row["said"], "I was there till 7")
		self.assertEqual(row["recorded_by"], self.h.hr2)

	def test_only_signed_or_not_right_is_accepted(self):
		self.an_approved_hr_change()
		notice = self._print([self.emp])["sheets"][0]["notice"]
		for bad in ("signed", "Yes", "", None, "Deleted"):
			self.refused(lambda b=bad: self._record(notice, b, photos=[_a_jpeg()],
			                                        user=self.h.hr2),
			             "signed or not right")

	def test_the_record_call_is_rate_limited_to_twenty_a_minute_per_user(self):
		self.assertEqual(register_notice.record.__alvoraa_limit__[1:], ("user", 20, 60))

	# ── helpers ─────────────────────────────────────────────────────────
	def _record(self, notice, outcome, photos=None, reason=None, user=None, extra=None):
		frappe.set_user(user or self.h.hr2)
		try:
			if extra:
				frappe.form_dict.update(extra)
			return register_notice.record(notice, outcome, photos=photos, reason=reason)
		finally:
			for k in (extra or {}):
				frappe.form_dict.pop(k, None)
			frappe.set_user("Administrator")


class ThePhotoStaysPrivate(RegisterNoticeCase):
	"""US-6, AC-44 to AC-50."""

	def _signed(self):
		self.an_approved_hr_change()
		notice = self._print([self.emp])["sheets"][0]["notice"]
		frappe.set_user(self.h.hr2)
		try:
			register_notice.record(notice, "Signed", photos=[_a_jpeg()])
		finally:
			frappe.set_user("Administrator")
		return notice

	def test_hr_in_scope_can_open_the_photo_and_one_log_row_is_written(self):
		"""AC-45."""
		notice = self._signed()
		before = frappe.db.count("Alvoraa Photo Access Log")
		frappe.set_user(self.h.hr2)
		try:
			register_notice.open_photo(notice, 1)
		finally:
			frappe.set_user("Administrator")
		self.assertTrue(frappe.local.response.get("filecontent"), "no bytes were streamed")
		rows = frappe.get_all("Alvoraa Photo Access Log",
		                      filters={"reference_name": notice},
		                      fields=["source", "viewed_by", "employee"])
		self.assertEqual(frappe.db.count("Alvoraa Photo Access Log"), before + 1)
		self.assertEqual(rows[0].source, "Register signature photo")
		self.assertEqual(rows[0].viewed_by, self.h.hr2)
		self.assertEqual(rows[0].employee, self.emp)

	def test_an_employee_and_a_manager_cannot_open_the_photo_and_nothing_is_logged(self):
		"""AC-44's permission half, AC-54."""
		notice = self._signed()
		before = frappe.db.count("Alvoraa Photo Access Log")
		for who in (self.emp_user, self.h._login("mgrphoto", ())):
			frappe.set_user(who)
			try:
				self.refused(lambda: register_notice.open_photo(notice, 1), "for HR")
			finally:
				frappe.set_user("Administrator")
		self.assertEqual(frappe.db.count("Alvoraa Photo Access Log"), before,
		                 "a refused look was logged as a look")

	def test_an_employee_cannot_read_the_notice_record_at_all(self):
		"""AC-55: no role row, so no list and no single record."""
		notice = self._signed()
		frappe.set_user(self.emp_user)
		try:
			# Measured: Frappe refuses outright rather than returning an empty list,
			# because the employee holds no role row on this doctype at all. AC-55 allows
			# either ("a permission error and the list is empty"); the refusal is the
			# stronger of the two and it is what actually happens, so that is what is
			# asserted - not the weaker claim I guessed first.
			self.refused(lambda: frappe.get_list(NOTICE, ignore_permissions=False),
			             "Insufficient Permission")
			self.assertFalse(frappe.has_permission(NOTICE, "read", user=self.emp_user))
		finally:
			frappe.set_user("Administrator")

	def test_hr_outside_the_scope_sees_no_notice_rows_and_cannot_open_one(self):
		"""AC-57, and the row filter the spec marks "fails first" - a company-only check
		would let this pass wrongly."""
		notice = self._signed()
		outsider = self.h._login("hrfarphoto", ("HR Manager",))
		frappe.set_user(outsider)
		try:
			self.assertEqual(register_notice.notice_query_conditions(outsider), "1=0")
			self.assertFalse(register_notice.notice_has_permission(
				frappe.get_doc(NOTICE, notice), outsider))
			self.refused(lambda: register_notice.open_photo(notice, 1), "outside the ones")
		finally:
			frappe.set_user("Administrator")

	def test_hr_scoped_to_one_branch_cannot_reach_another_branchs_signed_page(self):
		"""AC-57, and the gap the break-and-restore pass found.

		**This test exists because breaking the branch rule broke nothing.** I dropped
		`branch` from the scope condition and all 65 tests still passed: the only
		out-of-scope HR user in the suite had no company permission either, so the filter
		answered "nobody" for the wrong reason. The spec predicted exactly this - AC-57's
		"fails first" is "replace the helper with a company-only check and watch the branch
		test pass wrongly" - and there was no branch test to watch. A store's HR person
		being able to read another store's signatures is the whole reason the rule is
		company AND branch.
		"""
		notice = self._signed()
		for b in ("A88A", "A88B"):
			if not frappe.db.exists("Branch", b):
				frappe.get_doc({"doctype": "Branch", "branch": b}).insert(ignore_permissions=True)
		# **Everything this test changes is put back.** `log_view` commits, which defeats
		# this suite's per-test rollback, so a branch left on the shared fixture worker and
		# two User Permissions left on a login outlive the test and change what the NEXT
		# run sees. That is not hypothetical: the run straight after this test was written
		# failed on restored, correct code, purely on the state it had left behind. A suite
		# whose result depends on what ran before it is not evidence of anything.
		was_branch = frappe.db.get_value("Employee", self.emp, "branch")
		self.addCleanup(lambda: frappe.db.set_value("Employee", self.emp, "branch",
		                                            was_branch, update_modified=False))
		frappe.db.set_value("Employee", self.emp, "branch", "A88B", update_modified=False)
		branch_hr = self.h._login("hrbranch088", ("HR Manager",))
		for allow, value in (("Company", self.h.company), ("Branch", "A88A")):
			perm = frappe.get_doc({"doctype": "User Permission", "user": branch_hr,
			                       "allow": allow, "for_value": value,
			                       "apply_to_all_doctypes": 1}).insert(ignore_permissions=True)
			self.addCleanup(frappe.delete_doc, "User Permission", perm.name,
			                force=True, ignore_permissions=True)
		self.addCleanup(frappe.clear_cache, user=branch_hr)
		frappe.clear_cache(user=branch_hr)

		# The control: the same user IS in the right company, so a company-only rule would
		# let them straight in. That is what makes this test able to catch the break.
		condition = register_notice.notice_query_conditions(branch_hr)
		self.assertIn("branch", condition,
		              "the row filter does not mention the branch at all: " + condition)
		self.assertIn("A88A", condition)
		self.assertFalse(register_notice.notice_has_permission(
			frappe.get_doc(NOTICE, notice), branch_hr),
			"HR scoped to branch A88A can read a branch A88B employee's signed page")
		frappe.set_user(branch_hr)
		try:
			self.refused(lambda: register_notice.open_photo(notice, 1), "outside the ones")
			self.assertEqual(self._list(user=branch_hr)["rows"], [],
			                 "another branch's people are on this HR user's list")
		finally:
			frappe.set_user("Administrator")

	def test_the_photo_access_log_is_scoped_too(self):
		"""AC-47, SEC-10. The log had no row filter at all before this slice."""
		self._signed()
		outsider = self.h._login("hrfarlog", ("HR Manager",))
		self.assertEqual(register_notice.photo_log_query_conditions(outsider), "1=0")
		inside = register_notice.photo_log_query_conditions(self.hr)
		self.assertIn("tabEmployee", inside)
		self.assertIn("company", inside)

	def test_no_role_can_export_or_delete_and_nothing_in_088_deletes(self):
		"""AC-46, AC-48, AC-49."""
		notice = self._signed()
		for role in ("HR Manager", "HR User", "System Manager"):
			perm = frappe.get_all("DocPerm", filters={"parent": NOTICE, "role": role},
			                      fields=["export", "`delete`", "report"])[0]
			self.assertFalse(perm.export, role + " can export notices")
			self.assertFalse(perm.get("delete"), role + " can delete notices")
			self.assertFalse(perm.report, role + " can report on notices")
		self.refused(lambda: frappe.delete_doc(NOTICE, notice, force=True,
		                                      ignore_permissions=True), "cannot be deleted")
		source = open(os.path.join(PKG, "register_notice.py")).read()
		for forbidden in ("delete_doc", "frappe.db.delete", "DROP ", "TRUNCATE"):
			self.assertNotIn(forbidden, source, forbidden + " appears in slice 088's code")

	def test_the_notice_stores_the_month_so_a_purge_can_be_worked_out_later(self):
		"""AC-50: no `retain_until` field, because no period has been decided (D-9)."""
		notice = self._signed()
		doc = frappe.get_doc(NOTICE, notice)
		self.assertTrue(doc.month)
		self.assertTrue(doc.employee)
		self.assertIsNone(frappe.get_meta(NOTICE).get_field("retain_until"),
		                  "a retention date nobody has chosen is stored on the record")



class TheEmployeesOwnView(RegisterNoticeCase):
	"""US-7, AC-51 to AC-53: the small list in the app, for the employee who has one."""

	def _mine(self, month=None, user=None):
		frappe.set_user(user or self.emp_user)
		try:
			return register_notice.my_changes(month or self.day)
		finally:
			frappe.set_user("Administrator")

	def test_the_employee_sees_their_own_changed_days_with_the_reason(self):
		"""AC-51. Unlike HR's list, this one carries the reason: it is their own record."""
		self.held_on(self.day)
		req = self.fix(time="18:30", by=self.hr, note="You forgot to punch out")
		self.decide(req, 1, by=self.h.hr2)
		out = self._mine()
		self.assertEqual(out["changed"], 1)
		day = out["days"][0]
		self.assertEqual(day["request"], req)
		self.assertEqual(day["date"], str(self.day))
		self.assertEqual(day["what"], ["Out time 18:30 added"])
		self.assertEqual(day["why"], "You forgot to punch out")
		self.assertEqual(day["filed_role"], "HR")
		self.assertEqual(day["state"], "waiting")

	def test_the_state_follows_the_confirm_and_the_signature(self):
		"""AC-51's three sentences, each from a different real event."""
		first = self.an_approved_hr_change("18:30")
		self.assertEqual(self._mine()["days"][0]["state"], "waiting")

		self.confirm_as_employee(first)
		self.assertEqual(self._mine()["days"][0]["state"], "confirmed")

		second = self.an_approved_hr_change("19:30")
		notice = self._print([self.emp])["sheets"][0]["notice"]
		self._record_as_hr2(notice)
		states = {d["request"]: d["state"] for d in self._mine()["days"]}
		self.assertEqual(states[second], "signed")
		self.assertEqual(states[first], "confirmed",
		                 "a confirm in the app was relabelled as a register signature")

	def test_a_managers_addition_says_it_was_shown_not_that_it_is_waiting(self):
		"""AC-53. A manager's plain addition never waited for a confirm, so "not confirmed
		by you yet" would be a demand the system is not actually making."""
		mgr = self.h._login("mgrmine", ())
		self.h._employee("Mgrmine", mgr)
		self.held_on(self.day)
		req = self.fix(time="18:30", by=mgr)
		self.decide(req, 1, by=self.hr)
		day = self._mine()["days"][0]
		self.assertEqual(day["state"], "shown")
		self.assertEqual(day["filed_role"], "Manager")
		self.assertTrue(day["filed_by"], "the manager who changed the day is not named")

	def test_the_response_carries_no_photo_no_file_and_no_address(self):
		"""AC-52, PRIV-5. A signature photo is HR's evidence about the employee, not
		something to hand back through an API."""
		self.an_approved_hr_change()
		notice = self._print([self.emp])["sheets"][0]["notice"]
		self._record_as_hr2(notice)
		out = self._mine()
		# Checked as KEYS, not as substrings of the whole payload. The first version looked
		# for "file" anywhere in the JSON and failed on `filed_by` and `filed_role` - a
		# test finding its own carelessness rather than a leak.
		keys = set(out) | {k for d in out["days"] for k in d}
		for forbidden in ("photo", "file", "url", "notice", "content_hash", "pages"):
			self.assertNotIn(forbidden, keys, forbidden + " is a key in the employee's view")
		blob = frappe.as_json(out)
		for forbidden in ("/private/", "/files/", notice, ".jpg"):
			self.assertNotIn(forbidden, blob, forbidden + " reached the employee's own view")

	def test_the_employee_cannot_ask_for_anybody_else(self):
		"""AC-52. There is no id to swap: the person is read from the session."""
		import inspect

		self.an_approved_hr_change()
		args = inspect.signature(register_notice.my_changes).parameters
		self.assertEqual(list(args), ["month"],
		                 "my_changes takes something other than a month, so a caller can "
		                 "ask about somebody else")
		other = self.h._login("peerview", ())
		self.h._employee("Peerview", other)
		self.assertEqual(self._mine(user=other)["days"], [],
		                 "a colleague saw this person's changed days")

	def test_somebody_with_no_employee_record_is_refused(self):
		self.an_approved_hr_change()
		nobody = self.h._login("noemp088", ())
		self.refused(lambda: self._mine(user=nobody), "not linked to an employee")

	def test_the_view_is_empty_where_the_organisation_does_not_print_notices(self):
		"""The same per-company choice as the HR list, asserted both ways round."""
		self.an_approved_hr_change()
		self.assertEqual(self._mine()["changed"], 1, "fixture is wrong: nothing to hide")
		self._set_notices(0)
		self.assertEqual(self._mine()["days"], [])

	def test_the_confirm_switch_does_not_decide_the_employees_view(self):
		"""The employee half of the 23 Nov split: confirmations off, the page still shows."""
		self.an_approved_hr_change()
		frappe.db.set_value("Company", self.h.company, punch_fix.CONFIRM_SWITCH, 0,
		                    update_modified=False)
		frappe.clear_cache()
		self.assertEqual(self._mine()["changed"], 1,
		                 "switching confirmations off still empties the employee's view")

	def test_the_call_is_rate_limited_per_user(self):
		self.assertEqual(register_notice.my_changes.__alvoraa_limit__[1:], ("user", 60, 60))

	def _record_as_hr2(self, notice):
		frappe.set_user(self.h.hr2)
		try:
			return register_notice.record(notice, "Signed", photos=[_a_jpeg()])
		finally:
			frappe.set_user("Administrator")
