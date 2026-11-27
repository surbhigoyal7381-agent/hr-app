"""ALV-475: HR approving a punch fix must not be refused for having no location.

With HR Settings > Allow Geolocation Tracking on (DTC), Frappe HR refuses any Employee
Checkin with no latitude and longitude. The punch HR adds on approval has none, so the
approval failed. The fix skips that one check while `punch_fix` writes, and nowhere else.
Fixtures come from the 087 punch-fix tests (shift 09:00-18:00, three punches, held day).
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import punch_fix
from alvoraa_portal.tests import test_punch_fix_087 as pf

CHECKIN = "Employee Checkin"
REQUEST = "Attendance Request"
WORDS = "Latitude and longitude values are required"


def setUpModule():
	pf.setUpModule()


class PunchFixNoLocationAlv475(FrappeTestCase):
	def setUp(self):
		self.p = pf.PunchFixCase("setUp")
		self.p.setUp()
		self._was = frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking")
		self.addCleanup(frappe.db.set_single_value, "HR Settings", "allow_geolocation_tracking", self._was)
		self.addCleanup(frappe.set_user, "Administrator")

	def _tracking(self, on):
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", on)
		frappe.clear_cache()

	def _added(self, req):
		return frappe.get_all(CHECKIN, filters={punch_fix.ADDED: req}, pluck="name")

	def test_alv475_hr_approves_a_missing_punch_with_tracking_on(self):
		att, _names = self.p.held_three()   # fixtures first: a plain punch needs a location once it is on
		req = self.p.fix("12:40", note="forgot")
		self._tracking(1)
		self.p.decide(req)
		self.assertEqual(len(self._added(req)), 1, "the added punch exists")
		self.assertEqual(self.p.row(att).status, "Present")

	def test_alv475_undoing_the_approval_works_with_tracking_on_too(self):
		p = self.p
		p.held_three()
		req = p.fix("12:40", by=p.hr, note="HR typed it")
		p.decide(req, by=p.h.hr2)
		frappe.db.set_value(REQUEST, req, {"alvoraa_disputed_by": p.emp_user,
		                                   "alvoraa_disputed_on": frappe.utils.now_datetime(),
		                                   "alvoraa_dispute_reason": "no"})
		self._tracking(1)
		frappe.set_user(p.h.hr2)
		punch_fix.undo_change(req, "the employee is right")
		frappe.set_user("Administrator")
		added = self._added(req)
		self.assertEqual(frappe.db.get_value(CHECKIN, added[0], punch_fix.ASIDE), req,
		                 "the added punch is marked not counted")

	def test_alv475_a_punch_with_no_location_is_still_refused_outside_a_fix(self):
		self._tracking(1)
		doc = frappe.get_doc({"doctype": CHECKIN, "employee": self.p.emp, "log_type": "IN",
		                      "time": "%s 10:00:00" % self.p.day})
		with self.assertRaisesRegex(frappe.ValidationError, WORDS):
			doc.insert(ignore_permissions=True)

	def test_alv475_the_flag_is_cleared_after_a_fix_so_a_later_punch_is_refused(self):
		self.p.held_three()
		req = self.p.fix("12:40")
		self._tracking(1)
		self.p.decide(req)
		self.assertFalse(frappe.flags.get("in_punch_fix_apply"))
		doc = frappe.get_doc({"doctype": CHECKIN, "employee": self.p.emp, "log_type": "IN",
		                      "time": "%s 10:30:00" % self.p.day})
		with self.assertRaisesRegex(frappe.ValidationError, WORDS):
			doc.insert(ignore_permissions=True)

	def test_alv475_the_subclass_is_the_only_override_of_employee_checkin(self):
		self.assertEqual(frappe.get_hooks("override_doctype_class")[CHECKIN],
		                 ["alvoraa_portal.overrides.employee_checkin.AlvoraEmployeeCheckin"])
