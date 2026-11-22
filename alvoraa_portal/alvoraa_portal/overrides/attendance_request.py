"""Slice 087: Frappe HR's Attendance Request blocks a punch fix in three places.

All three are methods of the stock class and run before any hook of ours, so a
`doc_events` hook cannot stop them. This subclass changes them for a **punch fix**
(a request with a missing time or punches to set aside) and calls the stock method
for every other request, so an ordinary request behaves as it always did.

- `validate_request_overlap` refuses a second request for a day while ANY request that is
  not cancelled exists, a Declined draft included. A punch fix is refused only while
  another request for the day is waiting, or one that is not a punch fix is approved.
- `validate_no_attendance_to_create` refuses a day that already has the status the request would
  write ("status unchanged"). A punch fix does not write a status; `punch_fix.apply` does.
- `create_attendance_records` writes Present with no history. A punch fix writes the day
  once, in `punch_fix.apply`.

`override_doctype_class` takes the last app's class and needs a subclass of the stock
one (frappe/model/base_document.py); `tests/test_punch_fix_087.py` pins that this is
the only override of this DocType.
"""

import frappe
from frappe import _
from hrms.hr.doctype.attendance_request.attendance_request import AttendanceRequest

from alvoraa_portal.punch_fix import is_punch_fix


class AlvoraAttendanceRequest(AttendanceRequest):
	def validate_request_overlap(self):
		if not is_punch_fix(self):
			return super().validate_request_overlap()
		others = frappe.get_all(
			"Attendance Request",
			filters={"employee": self.employee, "docstatus": ("<", 2),
			         "name": ("!=", self.name or ""),
			         "from_date": ("<=", self.to_date), "to_date": (">=", self.from_date)},
			fields=["docstatus", "alvoraa_review_status", "alvoraa_missing_time", "alvoraa_set_aside"])
		for other in others:
			waiting = other.docstatus == 0 and other.alvoraa_review_status not in ("Declined", "Withdrawn")
			other_ordinary = other.docstatus == 1 and not (other.alvoraa_missing_time or other.alvoraa_set_aside)
			if waiting or other_ordinary:
				frappe.throw(_("You already have a request for this day that HR has not decided. "
				               "Withdraw it or wait for HR."))

	def validate_no_attendance_to_create(self):
		if not is_punch_fix(self):
			return super().validate_no_attendance_to_create()

	def create_attendance_records(self):
		if not is_punch_fix(self):
			return super().create_attendance_records()
