"""A phone punch must be made near the person's own branch (ALV-338).

Frappe HR's own rule measures a punch against the Shift Location on the person's
Shift Assignment, and it measures EVERY punch, machine punches included. That does
not fit a client who gives shifts through the employee's default shift and whose
staff punch at another store's machine: every such machine punch would be refused
(DTC, 26 Oct 2026, ALV-231).

So this rule is narrower:
- only a person's OWN punch is measured: our field app, our web portal, or any
  other way a staff login files one for itself (Frappe's API, Frappe HR's phone
  app) - see `_measured`;
- they are measured against the pin and radius on the employee's BRANCH;
- people whose designation is on the field-worker list in HR Settings (the field
  app's own list) may punch from anywhere;
- machine punches, punches loaded from another system and punches HR adds are
  never measured here.

"Allow Geolocation Tracking" in HR Settings is the master switch, as it is for
Frappe HR's rule. A branch with no pin, or a radius of 0, means "no limit".
Frappe HR's Shift Assignment rule is left as it is and still runs.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt

# The device_id our own two phone doors write on a punch (field_checkin.py,
# hr_api.do_checkin). Nothing else is measured.
PHONE_SOURCES = ("alvoraa-field-app", "web-portal")

# The Branch fields. These names are the ones DTC's site already holds (created by
# hand before this change), kept so their pins carry over with no data move.
F_LAT = "custom_latitude"
F_LNG = "custom_longitude"
F_RADIUS = "custom_geofence_radius_meters"


def tracking_on():
	return bool(cint(frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking")))


def is_field_worker(designation):
	"""On the field app's field-worker list in HR Settings."""
	if not designation:
		return False
	from alvoraa_portal.field_app_settings import CHILD, F_DESIGNATIONS, SETTINGS

	return bool(frappe.db.exists(CHILD, {
		"parent": SETTINGS, "parenttype": SETTINGS, "parentfield": F_DESIGNATIONS,
		"designation": designation}))


def branch_site(employee):
	"""The branch a phone punch is measured against, shaped like a Shift Location
	row (`location_name`, `checkin_radius`, `latitude`, `longitude`), or None.

	None for a field worker, for somebody with no branch, and on a site where the
	Branch fields do not exist yet (between a deploy and its migrate).
	"""
	emp = frappe.db.get_value("Employee", employee, ["branch", "designation"], as_dict=True)
	if not emp or not emp.branch or is_field_worker(emp.designation):
		return None
	meta = frappe.get_meta("Branch")
	if not all(meta.has_field(f) for f in (F_LAT, F_LNG, F_RADIUS)):
		return None
	row = frappe.db.get_value("Branch", emp.branch, [F_LAT, F_LNG, F_RADIUS], as_dict=True)
	if not row:
		return None
	return frappe._dict(
		location_name=emp.branch,
		checkin_radius=cint(row.get(F_RADIUS)),
		latitude=flt(row.get(F_LAT)) or None,
		longitude=flt(row.get(F_LNG)) or None,
	)


def _frappe_rule_applies(doc):
	"""Frappe HR's own rule will measure this punch: an active, submitted Shift
	Assignment for the punch's own shift names a Shift Location. The same filters
	as `validate_distance_from_shift_location`, so the two never leave a gap."""
	if not doc.shift:
		return False
	return bool(frappe.get_all(
		"Shift Assignment",
		filters={"employee": doc.employee, "shift_type": doc.shift, "docstatus": 1,
		         "status": "Active", "start_date": ["<=", doc.time], "shift_location": ["is", "set"]},
		or_filters=[["end_date", ">=", doc.time], ["end_date", "is", "not set"]],
		limit=1, pluck="name"))


def _measured(doc):
	"""Whether this punch is a person's own, made from a phone or a browser.

	Decided by WHO files it, not only by the device name on it, because the device
	name is whatever the sender chooses: a person calling Frappe's API, or Frappe
	HR's own phone app, files a punch with no device name at all (ALV-338 review).
	- the machine account: never, whatever device name it sends (ALV-231);
	- our two phone doors: always (the field app runs as Guest);
	- HR and administrators adding a punch: never;
	- anybody else filing a punch for their own employee record: yes.
	"""
	from alvoraa_portal.field_app_access import _HR_ROLES, is_machine_account

	user = frappe.session.user
	if is_machine_account(user):
		return False
	if doc.device_id in PHONE_SOURCES:
		return True
	if set(frappe.get_roles(user)) & _HR_ROLES:
		return False
	return frappe.db.get_value("Employee", doc.employee, "user_id") == user


def check_phone_punch(doc, method=None):
	"""validate Employee Checkin, after Frappe HR's own validate has set the shift.
	Refuses a person's own punch made too far from their branch. A new punch only:
	HR correcting a saved one is never refused.

	Raises Frappe HR's own CheckinRadiusExceededError, so the field app's existing
	handling (field_checkin._geofence_message) rewrites it the same way it does
	Frappe HR's refusal.
	"""
	if not doc.is_new() or not tracking_on() or not _measured(doc):
		return
	if _frappe_rule_applies(doc):
		# A Shift Assignment names a Shift Location: Frappe HR's own rule measures
		# this punch, and the two must never disagree about one person.
		return
	site = branch_site(doc.employee)
	if not site or site.checkin_radius <= 0 or not (site.latitude or site.longitude):
		return
	if not (doc.latitude or doc.longitude):
		# Frappe HR's own validate refuses a punch with no position while tracking
		# is on, in words the two doors already explain. Nothing to measure here.
		return

	from hrms.hr.doctype.employee_checkin.employee_checkin import CheckinRadiusExceededError
	from hrms.hr.utils import get_distance_between_coordinates

	distance = get_distance_between_coordinates(
		site.latitude, site.longitude, flt(doc.latitude), flt(doc.longitude))
	if distance > site.checkin_radius:
		frappe.throw(
			_("You are about {0} m from {1}. You need to be within {2} m to check in.").format(
				int(distance), site.location_name, site.checkin_radius),
			exc=CheckinRadiusExceededError,
			title=_("Too far from your branch"),
		)


def after_migrate():
	"""Add the three Branch fields where they are missing. A site that already has
	them (DTC made them by hand) keeps its own fields and values untouched."""
	if not frappe.db.exists("DocType", "Branch"):
		return False
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	wanted = [
		{"fieldname": F_LAT, "label": "Latitude", "fieldtype": "Float", "precision": "6",
		 "insert_after": "branch",
		 "description": "The branch's map pin. Phone and portal punches are measured from here."},
		{"fieldname": F_LNG, "label": "Longitude", "fieldtype": "Float", "precision": "6",
		 "insert_after": F_LAT},
		{"fieldname": F_RADIUS, "label": "Check-in radius (m)", "fieldtype": "Int",
		 "insert_after": F_LNG, "default": "0",
		 "description": "A phone or portal punch further than this from the pin is refused when "
		                "HR Settings allows location tracking. 0 means no limit. Machine punches "
		                "and punches HR adds are never measured. Field workers (HR Settings, "
		                "Field attendance app) may punch from anywhere."},
	]
	missing = [f for f in wanted
	           if not frappe.db.exists("Custom Field", {"dt": "Branch", "fieldname": f["fieldname"]})]
	if missing:
		create_custom_fields({"Branch": missing}, ignore_validate=True)
	return True


def refuse_small_radius(doc, method=None):
	"""validate Branch: the same floor the Shift Location radius has. A radius a
	phone cannot measure would refuse people standing at the door."""
	from alvoraa_portal.field_checkin import MIN_RADIUS_M

	radius = cint(doc.get(F_RADIUS))
	if 0 < radius < MIN_RADIUS_M:
		frappe.throw(
			_("A check-in radius under {0} m cannot be checked by a phone. Use {0} m or more, "
			  "or 0 for no limit.").format(MIN_RADIUS_M),
			title=_("Radius too small"),
		)
