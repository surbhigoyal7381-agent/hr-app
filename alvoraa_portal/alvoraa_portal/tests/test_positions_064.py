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


def _second_company():
	"""A company other than the one the tests' people are in, for the
	cross-company must-nots. Made once and kept, like the _Test companies
	ERPNext's own tests leave."""
	from hrms.alvoraa_org_structure.tests.test_org_structure import _company

	for name, abbr in (("Second Co 064", "SC064"), ("Third Co 064", "TC064")):
		if name == _company():
			continue
		if not frappe.db.exists("Company", name):
			frappe.get_doc({"doctype": "Company", "company_name": name, "abbr": abbr,
			                "default_currency": "INR", "country": "India"}).insert(ignore_permissions=True)
			frappe.db.commit()
		return name


class TestPeopleInNoSeat(Positions064Case):
	"""SEC-2 and PRIV-1: the "in no seat" list is for HR scope only, fails
	closed, and carries six named fields."""

	def setUp(self):
		super().setUp()
		self.delhi, self.noida = self.branch("Delhi 064"), self.branch("Noida 064")
		seat = self.pos("Seat 064", seats=5, branch=self.delhi)
		self.seated = self.person("Seated064")
		self.assign(self.seated, seat.name)
		self.in_delhi = self.person("Unseated Delhi064")
		self.in_noida = self.person("Unseated Noida064")
		self.no_branch = self.person("Unseated Nobranch064")
		self.left = self.person("Left064")
		frappe.db.set_value("Employee", self.in_delhi, "branch", self.delhi)
		frappe.db.set_value("Employee", self.in_noida, {"branch": self.noida, "reports_to": self.seated})
		frappe.db.set_value("Employee", self.left, {"status": "Left", "relieving_date": "2026-01-31"})
		other = frappe.get_doc({"doctype": "Employee", "first_name": "OtherCo064", "company": _second_company(),
		                        "date_of_birth": "1990-01-01", "date_of_joining": "2020-01-01",
		                        "gender": frappe.db.get_value("Gender", {}, "name"), "status": "Active"}
		                       ).insert(ignore_permissions=True)
		self._people.append(other.name)
		self.other_company = other.name
		frappe.db.commit()

	def tearDown(self):
		# reports_to was set without the nested-set update; clear it, or
		# deleting the people in tearDown trips ERPNext's tree code.
		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", self.in_noida, "reports_to", None)
		super().tearDown()

	def names(self, out):
		return {p["employee"] for p in out["unseated"]}

	def test_company_wide_hr_gets_every_active_unseated_person_of_their_company(self):
		frappe.set_user(self.hr_user("hr.all064@example.com"))
		got = self.names(register.position_table())
		self.assertTrue({self.in_delhi, self.in_noida, self.no_branch} <= got)
		self.assertNotIn(self.seated, got)

	def test_a_left_employee_is_not_listed(self):
		frappe.set_user(self.hr_user("hr.left064@example.com"))
		self.assertNotIn(self.left, self.names(register.position_table()))

	def test_another_companys_person_is_never_listed(self):
		frappe.set_user(self.hr_user("hr.co064@example.com"))
		self.assertNotIn(self.other_company, self.names(register.position_table()))

	def test_store_hr_gets_only_their_branch_and_nobody_with_no_branch(self):
		frappe.set_user(self.hr_user("hr.delhi064@example.com", branch=self.delhi))
		got = self.names(register.position_table())
		self.assertIn(self.in_delhi, got)
		self.assertNotIn(self.in_noida, got)
		self.assertNotIn(self.no_branch, got)

	def test_a_reader_without_hr_scope_gets_no_list_at_all(self):
		"""Absent, not empty: the page then shows no tile (fails closed)."""
		frappe.set_user(self.plain_reader("plain.list064@example.com"))
		out = register.position_table()
		self.assertNotIn("unseated", out)
		self.assertNotIn("active_people", out)

	def test_each_person_carries_exactly_the_six_allowed_fields(self):
		frappe.set_user(self.hr_user("hr.keys064@example.com"))
		out = register.position_table()
		self.assertTrue(out["unseated"])
		for p in out["unseated"]:
			self.assertEqual(set(p), set(register.UNSEATED_KEYS))
		noida = next(p for p in out["unseated"] if p["employee"] == self.in_noida)
		self.assertFalse(noida["no_manager"])
		self.assertTrue(next(p for p in out["unseated"] if p["employee"] == self.in_delhi)["no_manager"])

	def test_the_active_count_is_over_the_same_scope(self):
		frappe.set_user(self.hr_user("hr.count064@example.com", branch=self.delhi))
		out = register.position_table()
		# The store HR person's own record has no branch, so it is outside too.
		self.assertEqual(out["active_people"], frappe.db.count(
			"Employee", {"status": "Active", "company": frappe.db.get_value("Employee", self.in_delhi, "company"),
			             "branch": self.delhi}))


class TestTheQueryCountDoesNotGrow(Positions064Case):
	"""nfr-budget §2: the same number of statements for 20 people as for 200.
	The number itself is recorded in the implementation notes."""

	def test_position_table_is_flat_in_headcount(self):
		from alvoraa_portal.tests.leader_fixtures_012 import QueryCounter

		seat = self.pos("Flat 064", seats=300)
		for i in range(20):
			self.assign(self.person(f"Flat{i}x064"), seat.name)
		for i in range(5):
			self.person(f"Loose{i}x064")
		frappe.set_user(self.hr_user("hr.flat064@example.com"))
		register.position_table()
		with QueryCounter() as small:
			register.position_table()
		frappe.set_user("Administrator")
		for i in range(180):
			self.assign(self.person(f"More{i}x064"), seat.name)
		for i in range(20):
			self.person(f"LooseMore{i}x064")
		frappe.set_user("hr.flat064@example.com")
		register.position_table()  # warm the caches, as before the first count
		with QueryCounter() as big:
			register.position_table()
		print(f"\nposition_table statements: {small.count} at 20 people, {big.count} at 200")
		self.assertEqual(small.count, big.count)


class TestRecordsCheck(Positions064Case):
	"""SEC-5: the rewritten reporting_mismatches - scoped, flat, HR only."""

	def setUp(self):
		super().setUp()
		import hrms.alvoraa_org_structure.api as api

		self.api = api
		self.delhi, self.noida = self.branch("Delhi 064"), self.branch("Noida 064")
		top = self.pos("Top 064", branch=self.delhi)
		kid = self.pos("Kid 064", parent=top.name, seats=2, branch=self.delhi)
		other = self.pos("Other 064", parent=top.name, branch=self.delhi)
		pool = self.pos("Pool 064", parent=top.name, seats=3, branch=self.delhi)
		far = self.pos("Far 064", parent=top.name, branch=self.noida)
		self.m1, self.m2 = self.person("M1x064"), self.person("M2x064")
		self.e1, self.e2 = self.person("E1x064"), self.person("E2x064")
		self.p = [self.person(f"P{i}x064") for i in range(3)]
		self.far = self.person("Farx064")
		self.assign(self.m1, top.name)
		self.assign(self.m2, other.name)
		self.assign(self.e1, kid.name)
		self.assign(self.e2, kid.name)
		for e in self.p:
			self.assign(e, pool.name)
		self.assign(self.far, far.name)
		self.links = {self.e1: self.m2, self.e2: self.m1, self.p[0]: self.m1, self.p[1]: self.m2,
		              self.p[2]: self.m2, self.far: self.m2}
		for e, m in self.links.items():
			frappe.db.set_value("Employee", e, "reports_to", m)
		self.kid, self.pool, self.other = kid.name, pool.name, other.name
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		for e in self.links:
			frappe.db.set_value("Employee", e, "reports_to", None)
		super().tearDown()

	def test_hr_sees_a_person_whose_record_names_another_manager(self):
		frappe.set_user(self.hr_user("hr.rec064@example.com"))
		out = self.api.reporting_mismatches()
		got = {m["employee"]: m for m in out["mismatches"]}
		self.assertIn(self.e1, got)
		self.assertEqual(got[self.e1]["chart_says"], self.m1)
		self.assertEqual(got[self.e1]["reports_to_says"], self.m2)
		self.assertNotIn(self.e2, got)
		self.assertEqual(set(got[self.e1]), {"employee", "employee_name", "position", "parent_position",
		                                     "chart_says", "chart_says_name", "reports_to_says",
		                                     "reports_to_says_name"})

	def test_a_seat_holding_people_of_two_managers_is_reported_as_mixed(self):
		frappe.set_user(self.hr_user("hr.mixed064@example.com"))
		mixed = [m for m in self.api.reporting_mismatches()["mixed"] if m["position"] == self.pool]
		self.assertEqual({m["manager"]: m["count"] for m in mixed}, {self.m1: 1, self.m2: 2})
		self.assertEqual(next(m for m in mixed if m["manager"] == self.m2)["manager_position"], self.other)

	def test_store_hr_sees_only_their_branch(self):
		frappe.set_user(self.hr_user("hr.recnoida064@example.com", branch=self.noida))
		out = self.api.reporting_mismatches()
		self.assertNotIn(self.e1, {m["employee"] for m in out["mismatches"]})

	def test_a_reader_without_hr_scope_gets_nothing(self):
		frappe.set_user(self.plain_reader("plain.rec064@example.com"))
		self.assertEqual(self.api.reporting_mismatches(), {})

	def test_another_company_is_never_read(self):
		second = _second_company()
		frappe.set_user("Administrator")
		top = self.pos("Top B 064", company=second)
		kid = self.pos("Kid B 064", parent=top.name, company=second)
		a, b, c = [frappe.get_doc({"doctype": "Employee", "first_name": n, "company": second,
		                           "date_of_birth": "1990-01-01", "date_of_joining": "2020-01-01",
		                           "gender": frappe.db.get_value("Gender", {}, "name"), "status": "Active"}
		                          ).insert(ignore_permissions=True).name for n in ("BA064", "BB064", "BC064")]
		self._people.extend([c, b, a])
		self.assign(a, top.name)
		self.assign(b, kid.name)
		frappe.db.set_value("Employee", b, "reports_to", c)
		self.links[b] = c
		frappe.db.commit()
		frappe.set_user(self.hr_user("hr.recco064@example.com"))
		self.assertNotIn(b, {m["employee"] for m in self.api.reporting_mismatches()["mismatches"]})

	def test_the_statement_count_is_flat_and_the_call_is_fast(self):
		import time

		from alvoraa_portal.tests.leader_fixtures_012 import QueryCounter

		frappe.set_user(self.hr_user("hr.recflat064@example.com"))
		self.api.reporting_mismatches()
		with QueryCounter() as small:
			self.api.reporting_mismatches()
		frappe.set_user("Administrator")
		big = self.pos("Big 064", parent=self.kid, seats=400)
		for i in range(190):
			e = self.person(f"Many{i}x064")
			self.assign(e, big.name)
			frappe.db.set_value("Employee", e, "reports_to", self.m2)
			self.links[e] = self.m2
		frappe.db.commit()
		frappe.set_user("hr.recflat064@example.com")
		self.api.reporting_mismatches()
		started = time.monotonic()
		with QueryCounter() as large:
			out = self.api.reporting_mismatches()
		ms = (time.monotonic() - started) * 1000
		print(f"\nreporting_mismatches statements: {small.count} at ~10 assignments, "
		      f"{large.count} at ~200; {ms:.0f} ms; {len(out['mismatches'])} mismatches")
		self.assertEqual(small.count, large.count)
		self.assertLess(ms, 500)
