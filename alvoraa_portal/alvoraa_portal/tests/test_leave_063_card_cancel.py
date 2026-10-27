"""Slice 063: the Paid Leaves card (own record, days only) and cancelling.

SEC-1, SEC-8, SEC-9, PRIV-5, AC-1..AC-23 and AC-83..AC-90.
"""

import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import hr_api, leave_rules
from alvoraa_portal.tests import leave_063_fixtures as fx
from alvoraa_portal.tests.test_leave_063_rules import LWP, Rules063Case


def tearDownModule():
	fx.leave_world(P.values())


def setUpModule():
	global P
	P = fx.ensure_world()
	import alvoraa_portal.tests.test_leave_063_rules as rules
	rules.P = P


def _summary(as_user):
	frappe.set_user(as_user)
	try:
		return hr_api.get_leave_summary()
	finally:
		frappe.set_user("Administrator")


class TestTheCard(Rules063Case):
	def test_the_card_carries_only_the_named_keys(self):
		"""AC-17 / SEC-1a: a field added to MonthSummary later cannot leak."""
		card = _summary(fx.user("Priya"))["paid_leaves"]
		keys = set(leave_rules.CARD_KEYS_OFFICE)
		self.assertTrue(set(card) <= keys, set(card) - keys)
		# AC-17: under the gate the block is the list less the two keys that only
		# a person who has reached the gate does not get - nothing else is missing.
		self.assertEqual(keys - set(card), set() if "attended_so_far" in card else
		                 {"attended_so_far", "attended_up_to"})
		for never in ("daily_rate", "earning_basic", "gross", "net", "paid_days", "reds",
		              "greens", "notes", "red_deduction"):
			self.assertNotIn(never, card)

	def test_given_on_the_first_used_waiting_and_to_be_paid_out(self):
		"""AC-1, AC-5, AC-6: 4 given; an approved half and an open full day."""
		past, fut = fx.past_day(1), fx.future_day(1)
		self.need(past, fut)
		h = fx.apply_as(fx.user("Priya"), leave_type=fx.PAID, from_date=past, to_date=past,
		                half_day=1, half_day_date=past)["name"]
		fx.approve(h, by=fx.user("Sunil"))
		fx.apply_as(fx.user("Priya"), leave_type=fx.PAID, from_date=fut, to_date=fut)
		card = _summary(fx.user("Priya"))["paid_leaves"]
		self.assertEqual(card["credited"], 4)
		self.assertEqual(card["used"], 0.5)
		self.assertTrue(card["used_dates"][0]["half"])
		self.assertEqual(card["waiting"], 1)
		self.assertEqual(card["to_be_paid_out"], 2.5)
		self.assertEqual(card["approver"], "Sunil")
		self.assertEqual(card["waiting_from"], fut)

	def test_lwp_never_counts_as_used(self):
		"""AC-4."""
		d, = self.need(fx.future_day(1))
		n = fx.apply_as(fx.user("Priya"), leave_type=LWP, from_date=d, to_date=d)["name"]
		fx.approve(n, by=fx.user("Ritika"))
		card = _summary(fx.user("Priya"))["paid_leaves"]
		self.assertEqual(card["used"], 0)
		self.assertEqual(card["to_be_paid_out"], 4)
		self.assertEqual(card["lwp_in_play"], 1)

	def test_under_the_gate_the_attended_count_and_date_are_given(self):
		"""AC-9, X-3 (the 'up to' date, agreed 21 Oct)."""
		card = _summary(fx.user("Priya"))["paid_leaves"]
		self.assertEqual(card["gate"], 15)
		self.assertIn("attended_so_far", card)
		self.assertIn("attended_up_to", card)

	def test_contract_staff_get_one_sentence_and_no_figures(self):
		"""AC-12, via the card endpoint's own builder (Manoj has no login)."""
		emp = frappe.db.get_value("Employee", P["manoj"], ["name", "company"], as_dict=True)
		card = leave_rules.paid_leaves_card(emp)
		self.assertFalse(card["earns"])
		self.assertEqual(card["category"], "L063 Contract")
		self.assertNotIn("credited", card)

	def test_hr_passing_someone_gets_no_card(self):
		"""AC-19 / SEC-1c."""
		frappe.set_user(fx.user("Ritika"))
		self.assertNotIn("paid_leaves", hr_api.get_leave_summary(employee_id=P["priya"]))

	def test_a_colleague_id_from_a_non_hr_caller_gives_their_own(self):
		"""AC-20 / SEC-1d."""
		frappe.set_user(fx.user("Priya"))
		s = hr_api.get_leave_summary(employee_id=P["rohit"])
		self.assertEqual(s["employee"]["name"], P["priya"])

	def test_a_failure_says_so_and_logs_only_the_id(self):
		"""AC-16 / PRIV-5: the list and the Apply types still come back."""
		with patch("alvoraa_portal.leave_rules._card", side_effect=RuntimeError("boom 4321")):
			s = _summary(fx.user("Priya"))
		self.assertEqual(s["paid_leaves"], {"error": 1})
		self.assertIn("applications", s)
		self.assertTrue(s["types_offered"])
		log = frappe.get_all("Error Log", fields=["method"], order_by="creation desc", limit=1)
		self.assertIn(P["priya"], log[0].method)

	def test_the_query_count_does_not_grow_with_headcount(self):
		"""AC-23: the card reads one person; more staff in the company cost nothing."""
		def count():
			# The first call after a write refills Frappe's own caches (meta,
			# defaults); the second is the steady state a user meets.
			frappe.set_user(fx.user("Priya"))
			hr_api.get_leave_summary()
			with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as spy:
				hr_api.get_leave_summary()
			frappe.set_user("Administrator")
			return spy.call_count

		before = count()
		extra = [fx.ensure_employee("Extra%d" % i, grade="L063-A") for i in range(5)]
		try:
			after = count()
		finally:
			for e in extra:
				frappe.db.set_value("Employee", e, "status", "Left")
		self.assertEqual(before, after)


class TestTheSlipReadsPaidLeaves(Rules063Case):
	"""US-25 / AC-110: month_summary itself counts approved Paid Leaves days, so
	the slip, the desk report and the card all get E6 and U1 from one call."""

	def _day(self, day, status, leave_type=None, punches=True):
		att = frappe.get_doc({"doctype": "Attendance", "employee": P["rohit"],
		                      "company": fx.COMPANY, "attendance_date": day,
		                      "status": status, "shift": fx.SHIFT, "leave_type": leave_type})
		att.flags.ignore_permissions = True
		att.flags.ignore_validate = True
		att.insert()
		att.submit()
		if punches:
			for t in ("10:30:00", "20:30:00"):
				c = frappe.get_doc({"doctype": "Employee Checkin", "employee": P["rohit"],
				                    "time": "%s %s" % (day, t)})
				c.flags.ignore_permissions = True
				c.insert()

	def test_thirteen_worked_and_two_paid_leaves_reach_the_gate(self):
		from frappe.utils import add_days, get_first_day, get_last_day, nowdate

		from alvoraa_portal.payroll_slip import month_summary

		start = add_days(get_first_day(nowdate()), -31)
		start = get_first_day(start)
		for i in range(13):
			self._day(add_days(start, i), "Present")
		self._day(add_days(start, 13), "On Leave", fx.PAID, punches=False)
		self._day(add_days(start, 14), "On Leave", fx.PAID, punches=False)
		self._day(add_days(start, 15), "On Leave", LWP, punches=False)
		s = month_summary(P["rohit"], fx.COMPANY, start, get_last_day(start))
		self.assertEqual(s.days_worked, 13)
		self.assertEqual(s.days_for_gate, 15, "E6: approved Paid Leaves count toward 15")
		self.assertEqual(s.leave_credits_earned, 4)
		self.assertEqual(s.leave_used_for_approved, 2, "U1: the LWP day is not 'used'")
		self.assertEqual(s.leave_encashed, 2)


class TestCancel(Rules063Case):
	"""SEC-8, AC-83..AC-90."""

	def test_the_employee_withdraws_a_waiting_request(self):
		d, = self.need(fx.future_day(1))
		n = fx.apply_as(fx.user("Priya"), leave_type=LWP, from_date=d, to_date=d)["name"]
		frappe.set_user(fx.user("Priya"))
		res = hr_api.cancel_leave(n)
		frappe.set_user("Administrator")
		self.assertEqual(res["was"], "Open")
		self.assertEqual(frappe.db.get_value("Leave Application", n, "status"), "Cancelled")
		self.assertEqual(leave_rules.lwp_in_play(P["priya"], d), 0, "AC-90: the days are freed")
		told = frappe.get_all("Notification Log", filters={"document_name": n,
		                                                   "subject": ["like", "%cancelled%"]},
		                      pluck="for_user")
		self.assertIn(fx.user("Ritika"), told, "N-5: HR in scope are told")

	def test_the_employee_cancels_an_approved_leave_before_it_starts(self):
		d, = self.need(fx.future_day(1))
		n = fx.apply_as(fx.user("Priya"), leave_type=LWP, from_date=d, to_date=d)["name"]
		fx.approve(n, by=fx.user("Ritika"))
		frappe.set_user(fx.user("Priya"))
		res = hr_api.cancel_leave(n)
		frappe.set_user("Administrator")
		self.assertEqual(res["was"], "Approved")
		self.assertEqual(frappe.db.get_value("Leave Application", n, "docstatus"), 2)
		self.assertFalse(frappe.get_all("Notification Log", filters={
			"document_name": n, "for_user": fx.user("Kavita"),
			"subject": ["like", "%cancelled%"]}), "no chain notice on cancel (S2)")

	def test_a_leave_that_has_started_is_for_hr(self):
		"""AC-85."""
		d, = self.need(fx.past_day(1))
		n = fx.apply_as(fx.user("Priya"), leave_type=LWP, from_date=d, to_date=d)["name"]
		fx.approve(n, by=fx.user("Ritika"))
		frappe.set_user(fx.user("Priya"))
		with self.assertRaisesRegex(frappe.ValidationError, "only HR can cancel it"):
			hr_api.cancel_leave(n)

	def test_rest_still_cannot_cancel_for_the_employee(self):
		"""AC-86 / SEC-8d: nothing beyond Frappe."""
		d, = self.need(fx.past_day(1))
		n = fx.apply_as(fx.user("Priya"), leave_type=fx.PAID, from_date=d, to_date=d)["name"]
		fx.approve(n, by=fx.user("Sunil"))
		frappe.set_user(fx.user("Priya"))
		with self.assertRaises(frappe.PermissionError):
			frappe.client.cancel("Leave Application", n)

	def test_someone_elses_request_is_refused(self):
		"""AC-87: a non-HR login cannot cancel a colleague's leave."""
		d, = self.need(fx.future_day(1))
		n = fx.apply_as(fx.user("Rohit"), leave_type=LWP, from_date=d, to_date=d)["name"]
		frappe.set_user(fx.user("Priya"))
		with self.assertRaisesRegex(frappe.PermissionError, "only cancel your own leave"):
			hr_api.cancel_leave(n)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Leave Application", n, "status"), "Open")

	def test_hr_in_scope_withdraws_for_someone(self):
		"""AC-89."""
		d, = self.need(fx.future_day(1))
		n = fx.apply_as(fx.user("Rohit"), leave_type=LWP, from_date=d, to_date=d)["name"]
		frappe.set_user(fx.user("Ritika"))
		self.assertEqual(hr_api.cancel_leave(n)["was"], "Open")

	def test_the_bypass_is_the_one_the_ceiling_names(self):
		"""AC-88: hr_api.py at 70, and the use sits in cancel_leave."""
		import inspect

		self.assertIn("ignore_permissions", inspect.getsource(hr_api.cancel_leave))
