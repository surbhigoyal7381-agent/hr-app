"""Slice 072: the `manager` key on each seated person in `position_table`.

The Positions chart now draws people under the seat of their Reports To
manager. The server says WHO the manager is; the page works out WHERE. This
pins the one rule that matters for privacy (SEC-1): the key holds a manager's
id only when that id is already somewhere in this reply. Otherwise it is ""
(no manager on record, HR readers only) or absent.

Kept in alvoraa_portal's tests, not hrms's, because these run in CI.
"""

import json

import frappe
from frappe.utils import add_days, nowdate

import hrms.alvoraa_org_structure.register as register
from alvoraa_portal.tests.test_positions_064 import Positions064Case, _second_company

# Every key a seated person may carry, written out here rather than read from
# the code, so a further key fails this test (SEC-2). `manager` is the one 072 adds.
PERSON_KEYS = {"assignment", "employee", "name", "weight", "type", "covering",
               "hired_on", "leaving", "manager"}


class ReportsTo072Case(Positions064Case):
	def setUp(self):
		super().setUp()
		self.a, self.b = self.branch("Noida 072"), self.branch("Delhi 072")
		top = self.pos("Top 072", branch=self.a, seats=3)
		seat = self.pos("Shared 072", parent=top.name, branch=self.a, seats=10)
		out = self.pos("SEAT-OUT-SNTL", parent=top.name, branch=self.b)
		self.top, self.seat = top.name, seat.name

		self.ok = self.person("MGR-OK-SNTL")
		self.out = self.person("MGR-OUT-SNTL")
		self.left = self.person("MGR-LEFT-SNTL")
		self.unseated = self.person("MGR-UNSEATED-SNTL")
		frappe.db.set_value("Employee", self.unseated, "branch", self.a)
		self.assign(self.ok, top.name)
		self.assign(self.left, top.name)
		self.assign(self.out, out.name)
		frappe.db.set_value("Employee", self.left, {"status": "Left", "relieving_date": "2026-01-31"})

		second = _second_company()
		otherco_top = frappe.get_doc({"doctype": "Alvoraa Position", "position_title": "OTHERCO-SEAT-SNTL",
		                              "company": second, "seats": 1, "status": "Active"}).insert(ignore_permissions=True)
		self._cleanup.append(("Alvoraa Position", otherco_top.name))
		otherco = frappe.get_doc({"doctype": "Employee", "first_name": "MGR-OTHERCO-SNTL", "company": second,
		                          "date_of_birth": "1990-01-01", "date_of_joining": "2020-01-01",
		                          "gender": frappe.db.get_value("Gender", {}, "name"), "status": "Active"}
		                         ).insert(ignore_permissions=True)
		self._people.append(otherco.name)
		self.otherco = otherco.name
		self.assign(self.otherco, otherco_top.name)

		# The people in the shared seat, each reporting to a different kind of manager.
		self.links = {}
		self.p = {}
		for key, boss in (("ok", self.ok), ("out", self.out), ("left", self.left),
		                  ("unseated", self.unseated), ("otherco", self.otherco), ("none", None),
		                  ("gone", self.ok)):
			e = self.person(f"P-{key}-072")
			self.assign(e, seat.name)
			self.p[key] = e
			if boss:
				frappe.db.set_value("Employee", e, "reports_to", boss)
				self.links[e] = boss
		# A person who has left but is still seated: no key, whoever they report to.
		frappe.db.set_value("Employee", self.p["gone"], {"status": "Left", "relieving_date": "2026-01-31"})
		frappe.db.commit()

	def tearDown(self):
		# reports_to was set without the nested-set update; clear it, or
		# deleting the people trips ERPNext's tree code.
		frappe.set_user("Administrator")
		for e in self.links:
			frappe.db.set_value("Employee", e, "reports_to", None)
		frappe.db.delete("User Permission", {"user": ("like", "%072@example.com")})
		super().tearDown()

	def people(self, out):
		return {p["employee"]: p for r in out["rows"] for p in r["people"]}

	def managers(self, out):
		return {e: p.get("manager", "ABSENT") for e, p in self.people(out).items()}


class TestWhoGetsTheManager(ReportsTo072Case):
	def test_company_wide_hr(self):
		frappe.set_user(self.hr_user("hr.all072@example.com"))
		out = register.position_table()
		got = self.managers(out)
		# (a) a manager seated in view is sent: proves the test can see a key at all
		self.assertEqual(got[self.p["ok"]], self.ok)
		self.assertEqual(got[self.p["out"]], self.out)              # seated in Delhi, which this reader sees
		self.assertEqual(got[self.p["unseated"]], self.unseated)    # in this reader's "in no seat" list
		self.assertIn(self.unseated, {u["employee"] for u in out["unseated"]})
		self.assertEqual(got[self.p["none"]], "")                   # no manager on record: HR only
		self.assertEqual(got[self.p["left"]], "ABSENT")             # a Left manager, though still seated
		self.assertEqual(got[self.p["otherco"]], "ABSENT")          # another company
		self.assertEqual(got[self.p["gone"]], "ABSENT")             # the person has left
		text = json.dumps(out)
		for marker in (self.otherco, "MGR-OTHERCO-SNTL", "OTHERCO-SEAT-SNTL"):
			self.assertNotIn(marker, text)
		self.assertNotIn(self.left, {p.get("manager") for p in self.people(out).values()})

	def test_store_hr_tied_to_one_branch(self):
		frappe.set_user(self.hr_user("hr.noida072@example.com", branch=self.a))
		out = register.position_table()
		got = self.managers(out)
		self.assertEqual(got[self.p["ok"]], self.ok)
		self.assertEqual(got[self.p["unseated"]], self.unseated)
		self.assertEqual(got[self.p["none"]], "")
		self.assertEqual(got[self.p["out"]], "ABSENT")
		text = json.dumps(out)
		for marker in (self.out, "MGR-OUT-SNTL", "SEAT-OUT-SNTL", self.otherco, "MGR-OTHERCO-SNTL"):
			self.assertNotIn(marker, text)

	def test_hr_asking_for_one_branch_gets_no_manager_seated_only_in_another(self):
		"""(e) "in THIS reply": the branch argument narrows what may be named."""
		frappe.set_user(self.hr_user("hr.arg072@example.com"))
		out = register.position_table(branch=self.a)
		self.assertEqual(self.managers(out)[self.p["out"]], "ABSENT")
		self.assertEqual(self.managers(out)[self.p["ok"]], self.ok)

	def test_an_owner_with_positions_read_and_no_hr_role(self):
		"""Surbhi's yes (01c Q1): owners see the link when both people are on
		their page. Never "", never an unseated manager, never outside their branch."""
		frappe.set_user(self.plain_reader("owner.noida072@example.com", branch=self.a))
		out = register.position_table()
		self.assertNotIn("unseated", out)
		got = self.managers(out)
		self.assertEqual(got[self.p["ok"]], self.ok)
		for key in ("out", "left", "unseated", "otherco", "none", "gone"):
			self.assertEqual(got[self.p[key]], "ABSENT", key)
		text = json.dumps(out)
		self.assertNotIn('"manager": ""', text)
		for marker in (self.out, "MGR-OUT-SNTL", "SEAT-OUT-SNTL", self.unseated, "MGR-UNSEATED-SNTL",
		               self.otherco, "MGR-OTHERCO-SNTL"):
			self.assertNotIn(marker, text)

	def test_a_past_or_future_date_carries_no_manager_at_all(self):
		"""Reports To keeps no history, so a past chart with today's line would be false."""
		frappe.set_user(self.hr_user("hr.date072@example.com"))
		for day in (add_days(nowdate(), -1), add_days(nowdate(), 1)):
			out = register.position_table(as_at=day)
			self.assertFalse([p for p in self.people(out).values() if "manager" in p], day)

	def test_each_person_carries_exactly_the_written_keys(self):
		for user in (self.hr_user("hr.keys072@example.com"),
		             self.plain_reader("owner.keys072@example.com", branch=self.a)):
			frappe.set_user(user)
			for p in self.people(register.position_table()).values():
				self.assertLessEqual(set(p), PERSON_KEYS)
				self.assertEqual(set(p) - {"manager"}, PERSON_KEYS - {"manager"})
			frappe.set_user("Administrator")


class TestMoreManagerCases(ReportsTo072Case):
	"""Review m1: AC-3 (Inactive, Suspended), AC-10 (an ended or a covering
	seat) and AC-67 (a changed Reports To shows on the next call)."""

	def test_a_suspended_or_inactive_manager_is_not_sent(self):
		for status in ("Suspended", "Inactive"):
			frappe.set_user("Administrator")
			frappe.db.set_value("Employee", self.ok, "status", status)
			frappe.db.commit()
			frappe.set_user(self.hr_user(f"hr.{status.lower()}072@example.com"))
			self.assertEqual(self.managers(register.position_table())[self.p["ok"]], "ABSENT", status)
		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", self.ok, "status", "Active")
		frappe.db.commit()

	def test_a_manager_whose_only_seat_ended_is_not_sent(self):
		"""AC-10: not seated today, and an owner gets no "in no seat" list."""
		ended = self.person("MGR-ENDED-SNTL")
		self.assign(ended, self.top, from_date="2026-01-01", to_date=add_days(nowdate(), -1))
		frappe.db.set_value("Employee", self.p["none"], "reports_to", ended)
		self.links[self.p["none"]] = ended
		frappe.db.commit()
		frappe.set_user(self.plain_reader("owner.ended072@example.com", branch=self.a))
		out = register.position_table()
		self.assertEqual(self.managers(out)[self.p["none"]], "ABSENT")
		self.assertNotIn(ended, json.dumps(out))

	def test_a_manager_in_a_current_covering_seat_is_sent(self):
		"""AC-10: covering is still a seat in this reply."""
		cover = self.person("MGR-COVER-SNTL")
		# Cover must end (the organisation's rule), so it ends in a month.
		self.assign(cover, self.top, assignment_type="Acting", to_date=add_days(nowdate(), 30))
		frappe.db.set_value("Employee", self.p["none"], "reports_to", cover)
		self.links[self.p["none"]] = cover
		frappe.db.commit()
		frappe.set_user(self.plain_reader("owner.cover072@example.com", branch=self.a))
		self.assertEqual(self.managers(register.position_table())[self.p["none"]], cover)

	def test_a_changed_reports_to_shows_next_time_and_no_seat_changes(self):
		"""AC-67: the chart reads Reports To fresh; nothing about seats is written."""
		frappe.set_user(self.hr_user("hr.move072@example.com"))
		before = self.managers(register.position_table())[self.p["ok"]]
		frappe.set_user("Administrator")
		stamps = {d: frappe.get_all(d, filters={"name": ("in", names)}, fields=["name", "modified"], order_by="name")
		          for d, names in (("Alvoraa Position", [self.top, self.seat]),
		                           ("Alvoraa Position Assignment",
		                            frappe.get_all("Alvoraa Position Assignment", filters={"position": self.seat}, pluck="name")))}
		frappe.db.set_value("Employee", self.p["ok"], "reports_to", self.out)
		self.links[self.p["ok"]] = self.out
		frappe.db.commit()
		frappe.set_user("hr.move072@example.com")
		after = self.managers(register.position_table())[self.p["ok"]]
		frappe.set_user("Administrator")
		self.assertEqual((before, after), (self.ok, self.out))
		for d, rows in stamps.items():
			self.assertEqual(frappe.get_all(d, filters={"name": ("in", [r.name for r in rows])},
			                                fields=["name", "modified"], order_by="name"), rows, d)


class TestNoNewStatement(ReportsTo072Case):
	"""nfr-budget §2 and 04 Q2: the manager rides on the read the page already
	makes. The number is recorded in the implementation notes."""

	def test_the_count_is_flat_in_headcount_with_managers_on_record(self):
		from alvoraa_portal.tests.leader_fixtures_012 import QueryCounter

		frappe.set_user(self.hr_user("hr.flat072@example.com"))
		register.position_table()
		with QueryCounter() as small:
			register.position_table()
		frappe.set_user("Administrator")
		big = self.pos("Big 072", parent=self.top, seats=300, branch=self.a)
		for i in range(190):
			e = self.person(f"Many{i}x072")
			self.assign(e, big.name)
			frappe.db.set_value("Employee", e, "reports_to", self.ok)
			self.links[e] = self.ok
		frappe.db.commit()
		frappe.set_user("hr.flat072@example.com")
		register.position_table()
		with QueryCounter() as large:
			out = register.position_table()
		print(f"\nposition_table statements with managers: {small.count} at ~10 seated, "
		      f"{large.count} at ~200; reply {len(json.dumps(out, default=str))} bytes")
		self.assertEqual(small.count, large.count)
		self.assertEqual(sum(1 for p in self.people(out).values() if p.get("manager") == self.ok), 191)
