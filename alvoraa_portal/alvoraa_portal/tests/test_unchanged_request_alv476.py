"""ALV-476: a request for a day that already has the asked-for status reaches HR.

Seen 26 Nov 2026: an employee asked for 7 Nov from the portal, and Frappe HR refused
before saving - "No attendance records to create ... Attendance status unchanged" -
so HR never saw it. Surbhi chose option B: save it; approving changes the day only
if the status differs, declining changes nothing, and no Attendance is ever cancelled.

Built to pass when run first on an empty site (ALV-470): every record it needs is
made here. Test users take no password: none is needed.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_goals.tests.utils import ensure_company
from alvoraa_portal import attendance_correction as ac
from alvoraa_portal import hr_api
from alvoraa_portal.tests.utils import ensure_gender

TAG = "ALV476"
HOLIDAYS = "ALV476 Holidays"
REFUSAL = "'Holiday', 'Skip'"  # stock raises the reasons table, not its title


def setUpModule():
	frappe.set_user("Administrator")
	ac.after_migrate()
	company = ensure_company()
	ensure_gender()
	if not frappe.db.exists("Holiday List", HOLIDAYS):
		frappe.get_doc({
			"doctype": "Holiday List", "holiday_list_name": HOLIDAYS,
			"from_date": add_days(nowdate(), -400), "to_date": add_days(nowdate(), 400),
			"holidays": [{"holiday_date": add_days(nowdate(), -9), "description": "A day off"}],
		}).insert(ignore_permissions=True)
	if not frappe.db.exists("Holiday List Assignment", {"assigned_to": company, "docstatus": 1}):
		frappe.get_doc({
			"doctype": "Holiday List Assignment", "holiday_list": HOLIDAYS,
			"applicable_for": "Company", "assigned_to": company,
			"from_date": add_days(nowdate(), -400),
		}).insert(ignore_permissions=True).submit()
	frappe.clear_cache(doctype="Attendance Request")
	frappe.db.commit()


class UnchangedDayRequest(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.caller = frappe.session.user
		frappe.set_user("Administrator")
		self.company = ensure_company()
		self.email = f"{frappe.generate_hash(length=8)}.alv476@example.com"
		frappe.get_doc({"doctype": "User", "email": self.email, "first_name": TAG,
		                "send_welcome_email": 0, "roles": [{"role": "Employee"}]}
		               ).insert(ignore_permissions=True)
		self.emp = frappe.get_doc({
			"doctype": "Employee", "first_name": TAG, "last_name": self.email[:8],
			"company": self.company, "gender": ensure_gender(),
			"date_of_birth": "1990-01-01", "date_of_joining": add_days(nowdate(), -300),
			"status": "Active", "user_id": self.email, "create_user_permission": 0,
		}).insert(ignore_permissions=True).name
		self.day = add_days(nowdate(), -3)

	def tearDown(self):
		frappe.set_user(self.caller)
		super().tearDown()

	def mark(self, date, status="Present"):
		doc = frappe.get_doc({"doctype": "Attendance", "employee": self.emp, "company": self.company,
		                      "attendance_date": date, "status": status}).insert(ignore_permissions=True)
		doc.submit()
		return doc.name

	def ask_from_portal(self, date, reason="On Duty"):
		frappe.set_user(self.email)
		try:
			return hr_api.submit_attendance_request(date, date, reason, "I was at the store all day")["name"]
		finally:
			frappe.set_user("Administrator")

	def the_day(self, date):
		return frappe.get_all("Attendance", {"employee": self.emp, "attendance_date": date},
		                      ["name", "status", "docstatus", "attendance_request", "modified"])

	def test_alv476_the_portal_saves_a_request_for_a_day_already_present(self):
		self.mark(self.day)
		name = self.ask_from_portal(self.day)
		req = frappe.get_doc("Attendance Request", name)
		self.assertEqual(req.docstatus, 0)
		self.assertEqual(req.explanation, "I was at the store all day", "HR must see the reason")

	def test_alv476_approving_it_leaves_the_day_exactly_as_it_was(self):
		self.mark(self.day)
		before = self.the_day(self.day)
		name = self.ask_from_portal(self.day)
		ac.decide(name, 1, note="Seen")
		self.assertEqual(frappe.db.get_value("Attendance Request", name, "docstatus"), 1, "not approved")
		self.assertEqual(self.the_day(self.day), before, "approving changed or added an attendance row")
		# Cancelling the approved request later must not take the day with it.
		frappe.get_doc("Attendance Request", name).cancel()
		self.assertEqual(self.the_day(self.day), before, "cancelling the request cancelled the day")

	def test_alv476_declining_it_changes_nothing(self):
		self.mark(self.day)
		before = self.the_day(self.day)
		name = self.ask_from_portal(self.day)
		ac.decide(name, 0, note="Nothing to change")
		self.assertEqual(frappe.db.get_value("Attendance Request", name, "alvoraa_review_status"), "Declined")
		self.assertEqual(self.the_day(self.day), before)

	def test_alv476_a_day_that_would_change_is_still_corrected_in_place(self):
		absent = self.mark(self.day, "Absent")
		name = self.ask_from_portal(self.day)
		ac.decide(name, 1, note="Seen")
		rows = self.the_day(self.day)
		self.assertEqual(len(rows), 1, "a second row was made")
		self.assertEqual((rows[0].name, rows[0].status, rows[0].docstatus), (absent, "Present", 1))

	def test_alv476_a_holiday_is_still_refused(self):
		"""Only "status unchanged" was let through. On Leave takes the same stock path
		as Holiday and is not built here (it needs a leave type and allocation)."""
		holiday = add_days(nowdate(), -9)
		with self.assertRaisesRegex(frappe.ValidationError, REFUSAL):
			self.ask_from_portal(holiday)
