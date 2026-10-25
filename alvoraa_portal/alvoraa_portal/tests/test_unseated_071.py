"""Slice 071: "Place anyway" adds one place to a full seat, in the same save.

`assign_person(..., add_place=1)` raises the seat count through
`save_position` and puts the person in, in one request. Either both happen
or neither does. Without the flag the endpoint behaves exactly as before.

Kept in alvoraa_portal's tests, not hrms's, because these run in CI.
"""

import frappe
from frappe.utils import flt

import hrms.alvoraa_org_structure.register as register
from hrms.alvoraa_org_structure.tests.test_register_194 import RegisterCase


class PlaceAnyway071(RegisterCase):
	def setUp(self):
		super().setUp()
		self.editors("HR User")
		self.full = self.pos("Cashier 071", seats=1).name
		self.assign(self.person("Sitting071"), self.full)
		self.newcomer = self.person("Newcomer071")
		frappe.db.commit()

	def seats(self, seat):
		return flt(frappe.db.get_value(register.POSITION, seat, "seats"))

	def holders(self, seat):
		return set(frappe.get_all(register.ASSIGNMENT, filters={"position": seat}, pluck="employee"))

	def test_place_anyway_adds_one_place_in_the_same_save(self):
		"""The pin test for slice 071: 1 of 1 becomes 2 of 2 with the person in."""
		frappe.set_user(self.hr_user("scope194.place071@example.com"))
		register.assign_person(self.full, self.newcomer, add_place=1)
		self.assertEqual(self.seats(self.full), 2)
		self.assertIn(self.newcomer, self.holders(self.full))

	def test_without_the_flag_a_full_seat_is_refused_as_before(self):
		frappe.set_user(self.hr_user("scope194.noflag071@example.com"))
		with self.assertRaises(frappe.ValidationError):
			register.assign_person(self.full, self.newcomer)
		frappe.db.rollback()
		self.assertEqual(self.seats(self.full), 1)
		self.assertNotIn(self.newcomer, self.holders(self.full))

	def test_a_refusal_after_the_place_is_added_leaves_the_count_as_it_was(self):
		"""Both or neither. The person is already 100% in another seat, so the
		assignment is refused AFTER the count went up. Frappe rolls a failed
		request back; the savepoint does the same here."""
		other = self.pos("Elsewhere 071", seats=1).name
		self.assign(self.newcomer, other)
		frappe.db.commit()
		frappe.set_user(self.hr_user("scope194.rollback071@example.com"))
		frappe.db.savepoint("t071")
		with self.assertRaises(frappe.ValidationError):
			register.assign_person(self.full, self.newcomer, add_place=1)
		frappe.db.rollback(save_point="t071")
		self.assertEqual(self.seats(self.full), 1)
		self.assertNotIn(self.newcomer, self.holders(self.full))

	def test_a_seat_with_room_gets_no_extra_place(self):
		roomy = self.pos("Roomy 071", seats=3).name
		frappe.set_user(self.hr_user("scope194.room071@example.com"))
		register.assign_person(roomy, self.newcomer, add_place=1)
		self.assertEqual(self.seats(roomy), 3)
		self.assertIn(self.newcomer, self.holders(roomy))

	def test_a_seat_with_no_limit_stays_with_no_limit(self):
		"""0 places means no limit to the over-fill rule; +1 would make it 1."""
		open_ended = self.pos("No Limit 071", seats=0).name
		frappe.set_user(self.hr_user("scope194.nolimit071@example.com"))
		register.assign_person(open_ended, self.newcomer, add_place=1)
		self.assertEqual(self.seats(open_ended), 0)

	def test_another_branch_seat_is_refused_and_keeps_its_count(self):
		here, there = self.branch("Here 071"), self.branch("There 071")
		far = self.pos("Far 071", seats=1, branch=there).name
		self.assign(self.person("FarSitter071"), far)
		frappe.db.commit()
		frappe.set_user(self.hr_user("scope194.branch071@example.com", branch=here))
		with self.assertRaises(frappe.PermissionError):
			register.assign_person(far, self.newcomer, add_place=1)
		frappe.set_user("Administrator")
		self.assertEqual(self.seats(far), 1)

	def test_somebody_who_may_not_change_seats_is_refused(self):
		self.rows(("HR User", "read"))
		frappe.set_user(self.hr_user("scope194.reader071@example.com"))
		with self.assertRaises(frappe.PermissionError):
			register.assign_person(self.full, self.newcomer, add_place=1)
		frappe.set_user("Administrator")
		self.assertEqual(self.seats(self.full), 1)

	def test_statement_count_is_a_fixed_handful(self):
		"""Recorded in the implementation notes; flat per click, not per person."""
		from alvoraa_portal.tests.leader_fixtures_012 import QueryCounter

		roomy = self.pos("Count 071", seats=5).name
		frappe.set_user(self.hr_user("scope194.count071@example.com"))
		warm, plain_one = self.person("Warm071"), self.person("Plain071")
		register.assign_person(roomy, warm)  # warm the caches
		with QueryCounter() as plain:
			register.assign_person(roomy, plain_one)
		with QueryCounter() as raised:
			register.assign_person(self.full, self.newcomer, add_place=1)
		print(f"\nassign_person statements: {plain.count} plain, {raised.count} with add_place")
		self.assertLessEqual(raised.count, 40)
