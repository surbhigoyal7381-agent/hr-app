"""An attendance correction can actually be approved.

**Why this file exists.** ALV-346. Approving a correction ran Frappe HR's
`create_or_update_attendance`, which asks two questions with different rules:

* `get_attendance_doc` (*"is there a row to update?"*) matches the shift
  **exactly**, so a blank request shift only matches a blank attendance shift;
* `get_duplicate_attendance_record` (*"may I insert?"*) applies **no shift
  filter at all** when the new document has no shift, so any row for that
  employee and date is a clash.

Blank request shift + filled attendance shift = finds nothing to update, tries
to insert, refused as a duplicate. **Nobody could approve it** - not HR, not the
manager, not the Desk.

**This file's own test suite knew, and recorded the wrong conclusion.**
`CorrectionCase.person` in `test_attendance_correction.py` creates a Shift
Assignment with this comment:

    Frappe HR matches the day's existing Attendance row BY SHIFT ... the match
    misses, and it tries to insert a second row for the same day -
    DuplicateAttendanceError. **Real employees have one.**

Real employees at DTC do not. Measured on production 15 Nov 2026: **zero** Shift
Assignment rows, and `Employee.default_shift` set on **479 of 481** people. So
the fixture papered over a 100% production failure with a row no tenant creates,
and every test passed over it.

These tests therefore create **no Shift Assignment at all**, which is the real
shape of the tenant.

**Why the fix reads the day and not `Employee.default_shift`.** On DTC **4,283
of 25,055** attendance rows in 90 days carry a shift that is not the employee's
default - about one in six. A default-filled request matches no row AND trips no
duplicate check, so Frappe inserts a **second** attendance row for that day.
There are zero duplicate days on DTC today. `test_the_default_shift_is_not_used_
when_the_day_disagrees` is what stops that fix being reintroduced.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import attendance_correction as ac
from alvoraa_portal.tests.test_attendance_correction import _company, _holiday_list

SHIFT = "ALV346 Day Shift"        # 09:00-18:00
OTHER = "ALV346 Night Shift"      # 14:00-23:00, deliberately different


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
		for name, start, end in ((SHIFT, "09:00:00", "18:00:00"),
		                         (OTHER, "14:00:00", "23:00:00")):
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

	def person(self, first, default_shift=SHIFT):
		"""An employee exactly as DTC has them: a default shift, NO assignment.

		The missing Shift Assignment is the point of this file, so it is said
		here rather than left as an absence somebody later 'fixes'.
		"""
		e = frappe.get_doc({
			"doctype": "Employee", "first_name": first, "company": self.company,
			"date_of_birth": "1970-01-01", "date_of_joining": "2000-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active", "default_shift": default_shift,
			"holiday_list": self.holidays,
		}).insert(ignore_permissions=True)
		return e.name

	def day(self, employee, date, shift, status="Absent"):
		a = frappe.get_doc({
			"doctype": "Attendance", "employee": employee, "attendance_date": date,
			"status": status, "shift": shift, "company": self.company,
		}).insert(ignore_permissions=True)
		a.submit()
		return a.name

	def request(self, employee, date, shift=None):
		doc = frappe.get_doc({
			"doctype": ac.REQUEST, "employee": employee, "company": self.company,
			"from_date": date, "to_date": date, "reason": "On Duty",
			"shift": shift,
		})
		doc.insert(ignore_permissions=True)
		return doc

	def rows_on(self, employee, date):
		return frappe.get_all("Attendance", filters={
			"employee": employee, "attendance_date": date, "docstatus": ("<", 2),
		}, fields=["name", "shift", "status"])

	# ── the fix ──────────────────────────────────────────────────────────────

	def test_a_blank_request_takes_the_shift_off_the_day(self):
		"""The one line that unblocks every correction at a tenant like DTC."""
		emp = self.person("Dharmender346")
		date = self.d()
		self.day(emp, date, SHIFT)
		doc = self.request(emp, date)
		self.assertEqual(
			doc.shift, SHIFT,
			"the request saved with no shift, so approving it will look for a "
			"row with no shift, find none, and be refused as a duplicate")

	def test_approving_updates_the_day_instead_of_refusing(self):
		"""End to end: the thing a person actually presses.

		Not `take_the_shift_from_the_day` in isolation - the bug was only ever
		visible at `submit()`, which is why a suite full of green unit tests sat
		on top of a feature nobody could use.
		"""
		emp = self.person("Approve346")
		date = self.d()
		self.day(emp, date, SHIFT)
		doc = self.request(emp, date)
		doc.submit()                       # this threw DuplicateAttendanceError
		rows = self.rows_on(emp, date)
		self.assertEqual(len(rows), 1,
		                 "approving made a second attendance row for one day")
		self.assertEqual(rows[0].status, "Present",
		                 "the day was not corrected")

	def test_the_default_shift_is_not_used_when_the_day_disagrees(self):
		"""**The guard on the fix that was rejected.**

		Filling the request from `Employee.default_shift` looks obvious and is
		dangerous: on DTC about one row in six carries a shift that is not the
		employee's default. For those the request would match no row and trip no
		duplicate check, and Frappe would insert a SECOND attendance row for the
		day.

		So the day's own shift must win over the default, and one day must still
		end with one row.
		"""
		emp = self.person("Mismatch346", default_shift=SHIFT)
		date = self.d()
		self.day(emp, date, OTHER)         # the day disagrees with the default
		doc = self.request(emp, date)
		self.assertEqual(
			doc.shift, OTHER,
			"the request took the employee's default shift rather than the "
			"shift the day actually had - which inserts a duplicate row")
		doc.submit()
		self.assertEqual(len(self.rows_on(emp, date)), 1,
		                 "a second attendance row was created for one day")

	# ── what it must not do ──────────────────────────────────────────────────

	def test_a_shift_somebody_chose_is_never_overwritten(self):
		"""Only a blank is filled. A typed answer is a decision, not a gap."""
		emp = self.person("Chose346")
		date = self.d()
		self.day(emp, date, SHIFT)
		doc = self.request(emp, date, shift=OTHER)
		self.assertEqual(doc.shift, OTHER,
		                 "a shift chosen on the request was overwritten")

	def test_no_attendance_row_leaves_the_shift_alone(self):
		"""With nothing to correct there is nothing to copy.

		The blank then means what it has always meant and Frappe HR's own
		`validate_shifts` behaves exactly as it does today. This is the case
		where doing nothing is the right answer.
		"""
		emp = self.person("Empty346")
		doc = self.request(emp, self.d())
		self.assertFalse(doc.shift,
		                 "a shift was invented for a day with no attendance")

	def test_a_row_with_no_shift_is_not_copied_as_a_shift(self):
		"""A blank on the day is not an answer, so it must not become one.

		Picking it up would be harmless but untrue, and it would hide the case
		above behind a value that came from nowhere.
		"""
		emp = self.person("Blankday346")
		date = self.d()
		frappe.get_doc({
			"doctype": "Attendance", "employee": emp, "attendance_date": date,
			"status": "Absent", "company": self.company,
		}).insert(ignore_permissions=True).submit()
		doc = self.request(emp, date)
		self.assertFalse(doc.shift, "a blank shift was copied off the day")

	def test_an_empty_string_shift_counts_as_no_shift(self):
		"""NULL and '' are both blank, and only one of them is obvious.

		`("is", "set")` compiles to `shift != ''`, which excludes NULL as well -
		but that is a property of SQL's NULL comparison rather than something
		the filter says out loud, and a Link field can hold either. Production
		rows were not inspected for which, so both are pinned here instead of
		assumed.
		"""
		emp = self.person("Emptystr346")
		date = self.d()
		name = frappe.get_doc({
			"doctype": "Attendance", "employee": emp, "attendance_date": date,
			"status": "Absent", "company": self.company,
		}).insert(ignore_permissions=True).name
		frappe.db.set_value("Attendance", name, "shift", "", update_modified=False)
		doc = self.request(emp, date)
		self.assertFalse(doc.shift, "an empty-string shift was copied off the day")
