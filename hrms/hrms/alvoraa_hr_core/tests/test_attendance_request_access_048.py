"""ALV-127: the assertion that would have caught it - on the tenant shape.

The fault class is a doctype quietly dropping into custom-permission mode and a
role losing read, with nothing anywhere saying so. The health check in
`alvoraa_portal.permission_health` watches for it. This module is the other
half: it measures the thing that actually matters to a person, which is whether
an employee can still open their own attendance correction and whether the HR
person who runs that queue can still see it.

WHY IT REUSES SLICE 047's FIXTURES RATHER THAN MAKING A BARE SITE

A bare site has one company, no branches, no User Permissions and one
Administrator, and on a site like that almost any permission question answers
"yes". Every permission fault this product has had needed a real tenant to show
itself - two stores, HR limited to one of them, employees under different
managers. `FeedbackFixtures047` already builds exactly that, so the assertions
below run on the shape a customer actually has.

Names used come from that fixture:
  subj    an ordinary employee, store North, no special role
  hr_in   HR Manager, limited to store North by a Branch User Permission
  hr_out  HR Manager, limited to store South - must NOT see North's records

WHAT IS RESTORED, AND WHY IT IS DONE SO CAREFULLY

One test deliberately breaks `Attendance Request`, to prove the assertion is
capable of failing. A lone `Custom DocPerm` row makes Frappe ignore every
standard row for that doctype FOR THE REST OF THE RUN, so a sloppy restore
takes HR Manager away from every later test. The break goes in through
`frappe.permissions.add_permission` (which copies the standard rows first) and
comes out through `reset_perms`, and the DOCTYPE cache is cleared both times -
not the user cache, which is the mistake that cost this programme a day.
"""

import frappe
from frappe.permissions import add_permission, reset_perms

from .test_feedback_access_047 import COMPANY, FeedbackFixtures047, _email

DOCTYPE = "Attendance Request"

PERM_FIELDS = [
	"role", "permlevel", "if_owner", "read", "write", "create", "delete", "submit",
	"cancel", "amend", "report", "export", "import", "share", "print", "email", "select",
]


class TestAttendanceRequestAccess048(FeedbackFixtures047):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.request = cls._attendance_request()
		# Attendance Request already has custom permission rows on every site we
		# build - Frappe HR's Employee Self Service user type writes them at
		# install. `reset_perms` would delete those too, so the break below is
		# undone by putting these exact rows back, not by wiping the doctype.
		cls.baseline = frappe.get_all(
			"Custom DocPerm", filters={"parent": DOCTYPE}, fields=PERM_FIELDS, limit_page_length=0
		)
		frappe.db.commit()
		frappe.clear_cache(doctype=DOCTYPE)

	@classmethod
	def _holiday_list(cls):
		"""Attendance Request refuses to save without one.

		Not incidental tidying: `AttendanceRequest.validate` calls
		`get_attendance_warnings` -> `Employee.is_holiday` -> Frappe HR's
		`get_holiday_list_for_employee`, which throws when neither the employee
		nor their company has one. A real tenant always has one.

		In this version the link is a SUBMITTED `Holiday List Assignment`, not a
		`holiday_list` field on Employee or Company - `hrms/utils/holiday_list.py`
		:119 reads `Holiday List Assignment` with `docstatus == 1`. Setting the
		old field does nothing at all, which is what the first attempt did.
		"""
		name = "ALV127 Holidays"
		if not frappe.db.exists("Holiday List", name):
			doc = frappe.get_doc(
				{
					"doctype": "Holiday List",
					"holiday_list_name": name,
					"from_date": "2026-01-01",
					"to_date": "2026-12-31",
				}
			)
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
		if not frappe.db.exists(
			"Holiday List Assignment",
			{"assigned_to": COMPANY, "holiday_list": name, "docstatus": 1},
		):
			assignment = frappe.get_doc(
				{
					"doctype": "Holiday List Assignment",
					"holiday_list": name,
					"applicable_for": "Company",
					"assigned_to": COMPANY,
					"from_date": "2026-01-01",
				}
			)
			assignment.flags.ignore_permissions = True
			assignment.insert(ignore_permissions=True)
			assignment.submit()
		frappe.db.commit()
		return name

	@classmethod
	def _attendance_request(cls):
		cls._holiday_list()
		existing = frappe.db.get_value(
			DOCTYPE, {"employee": cls.emp["subj"], "from_date": "2026-03-02"}, "name"
		)
		if existing:
			return existing
		doc = frappe.get_doc(
			{
				"doctype": DOCTYPE,
				"employee": cls.emp["subj"],
				"company": COMPANY,
				"from_date": "2026-03-02",
				"to_date": "2026-03-02",
				"reason": "Work From Home",
				"explanation": "ALV127 fixture - a correction raised by an ordinary employee",
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True, ignore_mandatory=True)
		return doc.name

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def _visible_to(self, key):
		"""The names this login actually gets back from a list, as the desk would."""
		frappe.set_user(_email(key))
		try:
			return frappe.get_list(
				DOCTYPE, filters={"employee": self.emp["subj"]}, pluck="name", limit_page_length=0
			)
		finally:
			frappe.set_user("Administrator")

	def _may_read(self, key):
		frappe.set_user(_email(key))
		try:
			return frappe.has_permission(DOCTYPE, "read", doc=self.request)
		finally:
			frappe.set_user("Administrator")

	# ── the assertion itself ────────────────────────────────────────────────

	def test_an_ordinary_employee_can_read_their_own_attendance_request(self):
		self.assertTrue(self._may_read("subj"))
		self.assertIn(self.request, self._visible_to("subj"))

	def test_hr_in_scope_can_read_it(self):
		self.assertTrue(self._may_read("hr_in"))
		self.assertIn(self.request, self._visible_to("hr_in"))

	def test_hr_for_another_store_still_cannot_see_it(self):
		"""The other half of "can read": putting access back must not widen it.

		hr_out holds HR Manager too. What keeps North's correction away from them
		is the Branch User Permission plus the `alvoraa_branch` field the portal
		copies onto the record - not the role.
		"""
		self.assertNotIn(self.request, self._visible_to("hr_out"))

	def test_both_roles_the_health_check_requires_really_do_hold_read(self):
		"""The same claim the health check makes, measured from the other side."""
		for role in ("Employee", "HR Manager"):
			self.assertTrue(
				frappe.db.exists(
					"DocPerm", {"parent": DOCTYPE, "role": role, "permlevel": 0, "read": 1}
				),
				f"{role} has no standard read row on {DOCTYPE}",
			)

	# ── proof that the assertion can fail ───────────────────────────────────

	def test_losing_the_employee_row_really_does_take_the_queue_away(self):
		"""Break it, watch both halves go red, put it back.

		Without this, the three tests above could pass for ever on a site where
		permissions no longer work at all, and nobody would know.
		"""
		try:
			# The Desk route: grants one role, copies every standard row in first.
			add_permission(DOCTYPE, "HR User", 0)
			frappe.db.commit()
			frappe.clear_cache(doctype=DOCTYPE)
			# Still fine - copying is why the Desk route is not the danger.
			self.assertTrue(self._may_read("subj"), "the copy should have kept Employee's read")

			# Now the danger: the tenant removes a row inside the same screen.
			for name in frappe.get_all(
				"Custom DocPerm", filters={"parent": DOCTYPE, "role": "Employee"}, pluck="name"
			):
				frappe.delete_doc("Custom DocPerm", name, ignore_permissions=True, force=True)
			frappe.db.commit()
			frappe.clear_cache(doctype=DOCTYPE)
			frappe.local.role_permissions = {}

			self.assertFalse(
				self._may_read("subj"),
				"an employee still read their own correction with the Employee row deleted - "
				"then this whole module proves nothing",
			)
			# Measured, not guessed: with no read row at all, `get_list` REFUSES
			# rather than returning an empty list. A queue that errors is at
			# least visible; the quiet version of this fault is the list coming
			# back empty, which is why both halves are asserted.
			with self.assertRaises(frappe.PermissionError):
				self._visible_to("subj")

			# And the health check must say so, in the same breath.
			from alvoraa_portal.permission_health import check_permission_freeze

			finding = next(
				f for f in check_permission_freeze(print_report=False)["findings"] if f["doctype"] == DOCTYPE
			)
			self.assertEqual(finding["status"], "broken")
			self.assertIn("Employee", finding["missing_required_roles"])
		finally:
			self._restore()

		# Prove the restore worked, in this test, rather than leaving the next
		# five tests - or another module later in the run - to discover it.
		self.assertEqual(
			sorted(
				frappe.get_all(
					"Custom DocPerm",
					filters={"parent": DOCTYPE},
					fields=PERM_FIELDS,
					limit_page_length=0,
				),
				key=lambda r: (r.role, r.permlevel, r.if_owner),
			),
			sorted(self.baseline, key=lambda r: (r.role, r.permlevel, r.if_owner)),
		)
		self.assertTrue(self._may_read("subj"))
		self.assertTrue(self._may_read("hr_in"))

	def _restore(self):
		"""Put the doctype back exactly as the install left it."""
		reset_perms(DOCTYPE)
		for row in self.baseline:
			doc = frappe.get_doc(
				{
					"doctype": "Custom DocPerm",
					"parent": DOCTYPE,
					"parenttype": "DocType",
					"parentfield": "permissions",
					**row,
				}
			)
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
		frappe.db.commit()
		frappe.clear_cache(doctype=DOCTYPE)
		frappe.local.role_permissions = {}
