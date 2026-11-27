"""ALV-475: HR's approved punch fix cannot be refused for having no location.

Frappe HR's `validate_distance_from_shift_location` refuses any Employee Checkin with
no latitude and longitude while HR Settings > Allow Geolocation Tracking is on (DTC has
it on). An approved punch fix (`punch_fix.apply` and `punch_fix._reverse`) adds, sets
aside or restores punches for HR. The person was never there to send a location, so the
approval failed with "Latitude and longitude values are required for checking in."

The check runs inside the stock `validate`, before any hook of ours, so a `doc_events`
hook cannot stop it. This subclass skips that ONE method while `punch_fix` is writing
(`frappe.flags.in_punch_fix_apply`, set only by `punch_fix.py` and cleared in a `finally`).
Phone and portal punches, machine punches and the branch geofence (ALV-338) are not
under that flag and are checked exactly as before.

`override_doctype_class` needs a subclass of the stock class (frappe/model/base_document.py).
`tests/test_punch_fix_location_alv475.py` pins that this is the only override of this DocType.
"""

import frappe
from hrms.hr.doctype.employee_checkin.employee_checkin import EmployeeCheckin


class AlvoraEmployeeCheckin(EmployeeCheckin):
	def validate_distance_from_shift_location(self):
		if frappe.flags.get("in_punch_fix_apply"):
			return
		return super().validate_distance_from_shift_location()
