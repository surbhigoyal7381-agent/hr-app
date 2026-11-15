"""An attendance correction can actually be approved.

**Why this file exists.** ALV-346. Approving a correction ran Frappe HR's
`create_or_update_attendance`, and the two halves of one question disagreed
about a **blank** shift:

* `AttendanceRequest.get_attendance_doc` - *"is there a row to update?"* - read
  `"shift": None` as **"only a row that also has no shift"**;
* `Attendance.get_duplicate_attendance_record` - *"may I insert?"* - read a
  blank shift as **"no shift filter at all"**, so any row for that employee and
  date was a clash.

Blank request shift against a day that HAS a shift therefore found nothing to
update, fell through to the insert, and was refused as a duplicate. **Nobody
could approve it** - not HR, not the manager, not the Desk.

The fix makes a blank mean the same thing in both places (`attendance_request.
py:271`). A request that NAMES a shift still matches that shift exactly, so a
tenant using Shift Assignment properly is untouched.

**Why the request is blank in the first place.** `validate_shifts` reads
`tabShift Assignment` only. Measured on DTC production 15 Nov 2026: **zero**
Shift Assignment rows, and `Employee.default_shift` on **479 of 481** people. So
every request there was blank and every approval deadlocked - a 100% failure
rate on a live site.

**This suite already knew, and wrote down the wrong conclusion.**
`CorrectionCase.person` in `test_attendance_correction.py` creates a Shift
Assignment with the comment *"Real employees have one."* They do not at DTC. The
fixture papered over a production failure and 117 green tests sat on top of it.
Nothing here creates a Shift Assignment, which is the real shape of the tenant.

**The fix that was tried first and rejected, which is what
`test_a_range_across_two_shifts_corrects_each_day_in_place` guards.** A
`before_validate` hook in our own app filled the blank from the day's own
Attendance row. It fixed one day and broke a range: one request carries one
shift, so the second day of a two-shift range matched no row, tripped no
duplicate check, and Frappe inserted a **second submitted Attendance** for it -
Present on a shift the person never worked, beside Absent on the one they did.
Reproduced on the bench, 15 Nov 2026, and it is the same payroll fault that
`Employee.default_shift` was rejected for (4,283 of 25,055 DTC rows in 90 days
carry a shift that is not the employee's default).

Guessing a shift cannot be made safe for a range. Not guessing needs no guard.

**The shift pair below does not overlap, deliberately.** With overlapping
timings Frappe raises `OverlappingShiftAttendanceError` and the duplicate row
never appears - so an overlapping pair would make these tests pass while proving
nothing about the fault they exist for.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import attendance_correction as ac
from alvoraa_portal.tests.test_attendance_correction import _company, _holiday_list

EARLY = "ALV346 Early"    # 06:00-10:00
LATE = "ALV346 Late"      # 14:00-18:00 - no overlap with EARLY, on purpose


def setUpModule():
	ac.after_migrate()
	frappe.clear_cache(doctype=ac.REQUEST)


class NoShiftAssignmentAnywhere(FrappeTestCase):
	"""The tenant shape that broke: default shifts, and no assignments."""

	_slot = 0

	def setUp(self):
		super().setUp()
		self.caller = frappe.session.user
		frappe.set_user("Administrator")
		self.company = _company()
		NoShiftAssignmentAnywhere._slot += 1
		self.offset = 900 + NoShiftAssignmentAnywhere._slot * 40
		for name, start, end in ((EARLY, "06:00:00", "10:00:00"),
		                         (LATE, "14:00:00", "18:00:00")):
			if not frappe.db.exists("Shift Type", name):
				frappe.get_doc({"doctype": "Shift Type", "name": name,
				                "start_time": start, "end_time": end}
				               ).insert(ignore_permissions=True)
		self.holidays = _holiday_list(self.company)

	def tearDown(self):
		frappe.set_user(self.caller)
		super().tearDown()

	def d(self, i=0):
		return add_days(nowdate(), -(self.offset + i))

	def person(self, first, default_shift=EARLY):
		"""An employee as DTC has them: a default shift, and NO assignment.

		The missing Shift Assignment is the point of this file, so it is said
		here rather than left as an absence somebody later helpfully fills in.
		"""
		return frappe.get_doc({
			"doctype": "Employee", "first_name": first, "company": self.company,
			"date_of_birth": "1970-01-01", "date_of_joining": "2000-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active", "default_shift": default_shift,
			"holiday_list": self.holidays,
		}).insert(ignore_permissions=True).name

	def day(self, employee, date, shift, status="Absent"):
		doc = frappe.get_doc({
			"doctype": "Attendance", "employee": employee, "attendance_date": date,
			"status": status, "shift": shift, "company": self.company,
		}).insert(ignore_permissions=True)
		doc.submit()
		return doc.name

	def request(self, employee, from_date, to_date=None, shift=None):
		doc = frappe.get_doc({
			"doctype": ac.REQUEST, "employee": employee, "company": self.company,
			"from_date": from_date, "to_date": to_date or from_date,
			"reason": "On Duty", "shift": shift,
		})
		doc.insert(ignore_permissions=True)
		return doc

	def rows_on(self, employee, date):
		return frappe.get_all("Attendance", filters={
			"employee": employee, "attendance_date": date, "docstatus": ("<", 2),
		}, fields=["shift", "status"], order_by="creation asc")

	# ── the fix ──────────────────────────────────────────────────────────────

	def test_approving_corrects_the_day_instead_of_refusing(self):
		"""The production failure, end to end.

		Through `submit()`, never through a helper: the bug existed only at
		submit, so a unit test one level up would have been green and useless -
		which is exactly what 117 of them were.
		"""
		emp = self.person("Approve346")
		date = self.d()
		self.day(emp, date, EARLY)
		self.request(emp, date).submit()      # threw DuplicateAttendanceError
		rows = self.rows_on(emp, date)
		self.assertEqual(len(rows), 1,
		                 "approving made a second attendance row for one day")
		self.assertEqual(rows[0].status, "Present", "the day was not corrected")
		self.assertEqual(rows[0].shift, EARLY,
		                 "the correction changed the day's shift; it must only "
		                 "change the status")

	def test_a_range_across_two_shifts_corrects_each_day_in_place(self):
		"""**The guard on the fix that was rejected.**

		Filling the blank from the day's own row looks safe and is not: one
		request carries one shift, so the second day of a two-shift range
		matched nothing, tripped no duplicate check, and Frappe inserted a
		SECOND submitted Attendance for it.

		Each day must be corrected against its own row, and each day must end
		with exactly one.
		"""
		emp = self.person("Range346")
		d1, d2 = self.d(1), self.d(0)
		self.day(emp, d1, EARLY)
		self.day(emp, d2, LATE)
		self.request(emp, d1, d2).submit()
		for date, shift in ((d1, EARLY), (d2, LATE)):
			rows = self.rows_on(emp, date)
			self.assertEqual(len(rows), 1,
			                 f"{date} ended with {len(rows)} attendance rows; a "
			                 f"duplicate day is a payroll fault, not a screen one")
			self.assertEqual(rows[0].status, "Present", f"{date} was not corrected")
			self.assertEqual(rows[0].shift, shift,
			                 f"{date} had its shift rewritten to the other day's")

	def test_no_attendance_row_still_creates_one(self):
		"""The insert path is not collateral damage.

		Widening the lookup must not stop a day with nothing on it getting a
		fresh row - that is the ordinary case for a day the biometric sync
		never reached.
		"""
		emp = self.person("Fresh346")
		date = self.d()
		self.request(emp, date).submit()
		rows = self.rows_on(emp, date)
		self.assertEqual(len(rows), 1, "no attendance was created")
		self.assertEqual(rows[0].status, "Present")

	# ── what must not change ─────────────────────────────────────────────────

	def test_a_named_shift_still_matches_only_that_shift(self):
		"""A tenant that really uses Shift Assignment is untouched.

		With a shift on the request the filter is applied exactly as before, so
		a day on a DIFFERENT shift is not the row to update. Frappe then inserts
		for that shift, which is the behaviour that tenant has today and is not
		this ticket's to change.
		"""
		emp = self.person("Named346")
		date = self.d()
		self.day(emp, date, LATE)
		doc = self.request(emp, date, shift=EARLY)
		self.assertEqual(doc.shift, EARLY, "the named shift was overwritten")
		doc.submit()
		shifts = {r.shift for r in self.rows_on(emp, date)}
		self.assertIn(EARLY, shifts,
		              "a request naming a shift no longer reaches that shift")

	def test_a_named_shift_updates_its_own_row(self):
		"""The exact-match path still finds and updates, rather than inserting.

		The fix only widens the BLANK case. If it widened this one too, the
		`if self.shift` would be dead and nobody would notice for a year.
		"""
		emp = self.person("Exact346")
		date = self.d()
		self.day(emp, date, EARLY)
		self.request(emp, date, shift=EARLY).submit()
		rows = self.rows_on(emp, date)
		self.assertEqual(len(rows), 1, "a second row was inserted for one day")
		self.assertEqual(rows[0].status, "Present")
