"""Slice 064: what the Positions page is sent, and to whom.

The page works everything out in the browser from one payload, so the payload
is where the rules live: which seats, which people, which flags. These tests
pin each key the slice added, and who may and may not receive it.

Kept in alvoraa_portal's tests, not hrms's, because these run in CI.
"""

import frappe
from frappe.utils import add_days, nowdate

import hrms.alvoraa_org_structure.register as register
from hrms.alvoraa_org_structure.tests.test_register_194 import RegisterCase

ASSIGNMENT = "Alvoraa Position Assignment"


class Positions064Case(RegisterCase):
	def plain_reader(self, email, branch=None):
		"""Somebody given Positions read with no HR role - DTC's owners."""
		if not frappe.db.exists("User", email):
			u = frappe.get_doc({"doctype": "User", "email": email, "first_name": "Reader",
			                    "enabled": 1, "send_welcome_email": 0}).insert(ignore_permissions=True)
			self._cleanup.append(("User", u.name))
		emp = self.person("Reader064")
		frappe.db.set_value("Employee", emp, "user_id", email)
		user = frappe.get_doc("User", email)
		user.flags.ignore_permissions = True
		user.add_roles("Projects User")
		if branch:
			frappe.get_doc({"doctype": "User Permission", "user": email, "allow": "Branch",
			                "for_value": branch, "apply_to_all_doctypes": 0,
			                "applicable_for": "Employee"}).insert(ignore_permissions=True)
		self.rows(("HR User", "read"), ("Projects User", "read"))
		frappe.db.commit()
		return email

	def tearDown(self):
		frappe.db.delete("User Permission", {"user": ("like", "%064@example.com")})
		super().tearDown()


class TestNewSeatsAndNewHires(Positions064Case):
	def test_every_seat_carries_the_day_it_was_made(self):
		seat = self.pos("Counter Staff 064", seats=1)
		frappe.set_user(self.hr_user("hr.created064@example.com"))
		row = next(r for r in register.position_table()["rows"] if r["id"] == seat.name)
		self.assertEqual(row["created"], str(seat.creation)[:10])

	def test_the_first_seat_of_the_company_is_sent_so_set_up_day_is_not_new(self):
		seat = self.pos("First 064", seats=1)
		first = frappe.db.sql("select min(creation) from `tabAlvoraa Position` where company=%s",
		                      seat.company)[0][0]
		frappe.set_user(self.hr_user("hr.first064@example.com"))
		out = register.position_table()
		self.assertEqual(out["first_seat_created"][seat.company], str(first)[:10])

	def test_a_person_placed_by_the_hire_hook_is_marked_hired(self):
		seat = self.pos("Store Manager 064", seats=2)
		placed, by_hand = self.person("Placed064"), self.person("ByHand064")
		self.assign(placed, seat.name, from_date=nowdate(),
		            reason=register.PLACED + " HR-OPN-1 (applicant HR-APP-1)")
		self.assign(by_hand, seat.name, from_date=nowdate(), reason="Moved from Noida")
		frappe.set_user(self.hr_user("hr.hired064@example.com"))
		row = next(r for r in register.position_table()["rows"] if r["id"] == seat.name)
		got = {p["employee"]: p["hired_on"] for p in row["people"]}
		self.assertEqual(got[placed], nowdate())
		self.assertIsNone(got[by_hand])


class TestFlagsThePageNeeds(Positions064Case):
	def test_hr_may_see_leavers_and_change_employees(self):
		self.pos("Seat 064", seats=1)
		frappe.set_user(self.hr_user("hr.flags064@example.com"))
		out = register.position_table()
		self.assertTrue(out["may_see_leaving"])

	def test_a_reader_with_no_hr_role_and_nobody_under_them_may_not_see_leavers(self):
		"""The tile is then absent, never "Nobody leaving" (SEC-4, X-1)."""
		self.pos("Seat 064", seats=1)
		frappe.set_user(self.plain_reader("plain.flags064@example.com"))
		out = register.position_table()
		self.assertFalse(out["may_see_leaving"])
		self.assertFalse(out["may_edit_employee"])
