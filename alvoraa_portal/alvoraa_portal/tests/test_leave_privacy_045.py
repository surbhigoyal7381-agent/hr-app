"""045 AC-76 and AC-21 - the leave reason, and a month filter that was never right.

**AC-76 closes D-1, and it covers two fields, not one.** `leave_type` is the
category - "Sick Leave". `description` is what the employee typed - "father in
hospital" - and **it is the more personal of the two**, so a rule written about
the category alone would leak the worse half and look like it had been
followed. Both travel on one row only: the approval row for the caller's own
direct report, where the caller is deciding that request.

Two things make these assertions able to fail:

* **The fixture populates both fields on both people.** An empty fixture passes
  while the leak survives - Wave 3's AC-17 all over again.
* **The payload is searched recursively for the fixture strings.** Not two
  named keys. A two-key check passes the moment somebody adds a third key
  carrying the same value, which is exactly how this leak reached two functions
  in the first place.

**AC-21** is the month filter. `from_date >= mo_start` missed leave that began
last month and was still running, and included leave that starts next month.
It has been wrong since it was written.
"""

import frappe
from frappe.utils import add_days, get_first_day, get_last_day, nowdate

from alvoraa_portal import hr_api
from alvoraa_portal.tests.fixtures_045 import Wave4Base
from alvoraa_portal.tests.test_team_payload_045 import find_key, find_value

# Distinctive on purpose. A recursive search needs a needle that could not be
# in the payload for any other reason.
DIRECT_TYPE = "S045 Sick Leave"
DIRECT_WHY = "S045 father in hospital"
COVERED_TYPE = "S045 Casual Leave"
COVERED_WHY = "S045 sister's wedding"


def _leave_type(name):
	if not frappe.db.exists("Leave Type", name):
		frappe.get_doc({"doctype": "Leave Type", "leave_type_name": name,
		                "max_leaves_allowed": 30}).insert(ignore_permissions=True)
	return name


def _allocate(employee, leave_type, days=30):
	"""A submitted Leave Allocation wide enough for every date this file uses.

	Found by the first run going red eight times: Frappe HR refuses a Leave
	Application whose period falls outside an allocation ("Application period
	cannot be outside leave allocation period"), and an UNSUBMITTED allocation
	grants no balance at all.

	The window is deliberately wide - a year either side - because this file
	deliberately applies for leave that began last month and leave that starts
	next month, which is the whole point of the AC-21 checks.
	"""
	if frappe.get_all("Leave Allocation",
	                  filters={"employee": employee, "leave_type": leave_type,
	                           "docstatus": 1}, limit=1):
		return
	doc = frappe.get_doc({
		"doctype": "Leave Allocation",
		"employee": employee,
		"leave_type": leave_type,
		"from_date": add_days(nowdate(), -365),
		"to_date": add_days(nowdate(), 365),
		"new_leaves_allocated": days,
		"carry_forward": 0,
	})
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	doc.submit()
	frappe.db.commit()


class _OnLeave(Wave4Base):
	"""One direct report and one covered person, both off today, both with a
	written reason, and each with a different leave type."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_leave_type(DIRECT_TYPE)
		_leave_type(COVERED_TYPE)
		for who in [cls.rahul] + list(cls.covered_only):
			for lt in (DIRECT_TYPE, COVERED_TYPE):
				_allocate(who, lt)
		frappe.db.commit()

	def _leave(self, employee, leave_type, why, from_date=None, to_date=None,
	           approver=None, submitted=True):
		doc = frappe.get_doc({
			"doctype": "Leave Application",
			"employee": employee,
			"leave_type": leave_type,
			"from_date": from_date or nowdate(),
			"to_date": to_date or nowdate(),
			"description": why,
			"status": "Approved" if submitted else "Open",
			"leave_approver": approver,
		})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		if submitted:
			frappe.db.set_value("Leave Application", doc.name, "docstatus", 1,
			                    update_modified=False)
		frappe.db.commit()
		self.addCleanup(self._drop, doc.name)
		return doc.name

	def _drop(self, name):
		frappe.set_user("Administrator")
		frappe.db.sql("DELETE FROM `tabLeave Application` WHERE name=%s", (name,))
		frappe.db.commit()

	def _dash(self, user):
		self.as_user(user)
		return hr_api.get_manager_dashboard()


class TestNeitherFieldLeavesTheScreen(_OnLeave):
	def test_the_fixture_really_carries_both_fields_on_both_people(self):
		"""The check on the check.

		If the leave rows do not actually hold these strings, every assertion
		in this file is passing over nothing - the failure mode that is
		invisible from the outside, so it is asserted from the inside.
		"""
		a = self._leave(self.rahul, DIRECT_TYPE, DIRECT_WHY)
		b = self._leave(self.covered_only[0], COVERED_TYPE, COVERED_WHY)
		for name, lt, why in ((a, DIRECT_TYPE, DIRECT_WHY),
		                      (b, COVERED_TYPE, COVERED_WHY)):
			row = frappe.db.get_value("Leave Application", name,
			                          ["leave_type", "description", "docstatus"],
			                          as_dict=True)
			self.assertEqual(lt, row.leave_type)
			self.assertEqual(why, row.description)
			self.assertEqual(1, row.docstatus, "the fixture leave is not submitted")

	def test_no_reason_reaches_a_card_a_chip_or_a_count(self):
		"""AC-76(a). Neither field, anywhere, for any persona - searched
		recursively over the serialised payload."""
		self._leave(self.rahul, DIRECT_TYPE, DIRECT_WHY)
		self._leave(self.covered_only[0], COVERED_TYPE, COVERED_WHY)
		for user in (self.sandeep_user, self.priya_user, self.kamal_user):
			d = self._dash(user)
			on_leave = d.get("on_leave_today") or []
			month = d.get("month_leaves") or []
			for label, part in (("on_leave_today", on_leave), ("month_leaves", month)):
				for needle in (DIRECT_TYPE, DIRECT_WHY, COVERED_TYPE, COVERED_WHY):
					with self.subTest(user=user, part=label, needle=needle):
						self.assertEqual([], find_value(part, needle))

	def test_priya_sees_neither_field_anywhere_at_all(self):
		"""AC-76(d). Her people are all covered, so nobody on her screen is a
		request she is deciding as their manager."""
		self._leave(self.rahul, DIRECT_TYPE, DIRECT_WHY, approver=self.priya_user,
		            submitted=False)
		self._leave(self.covered_only[0], COVERED_TYPE, COVERED_WHY,
		            approver=self.priya_user, submitted=False)
		d = self._dash(self.priya_user)
		for needle in (DIRECT_TYPE, DIRECT_WHY, COVERED_TYPE, COVERED_WHY):
			with self.subTest(needle=needle):
				self.assertEqual([], find_value(d, needle),
				                 "a covered person's reason reached store HR")

	def test_a_covered_persons_reason_reaches_nobody_even_their_approver(self):
		"""AC-76(c) and 045 Q4a, the case the rule does not soften for.

		An HR person who is the named `leave_approver` for somebody who is NOT
		their direct report now decides that request without seeing either
		field. The decided rule is `reports_to`-based; the approval duty is
		`leave_approver`-based; the two do not always coincide. They see the
		dates, the days and the person - "why" stays withheld.
		"""
		self._leave(self.covered_only[0], COVERED_TYPE, COVERED_WHY,
		            approver=self.kamal_user, submitted=False)
		d = self._dash(self.kamal_user)
		rows = [r for r in (d.get("pending_approvals") or [])
		        if r.get("employee") == self.covered_only[0]]
		self.assertTrue(rows, "the fixture request is not in the approver's queue")
		for row in rows:
			self.assertNotIn("leave_type", row)
			self.assertNotIn("description", row)
			self.assertFalse(row.get("is_own_report"))
		self.assertEqual([], find_value(d, COVERED_WHY))
		self.assertEqual([], find_value(d, COVERED_TYPE))

	def test_a_direct_reports_reason_appears_on_exactly_one_row(self):
		"""AC-76(b). Sandeep is deciding Rahul's request, so he sees what he
		is deciding - and sees it once."""
		self._leave(self.rahul, DIRECT_TYPE, DIRECT_WHY, approver=self.sandeep_user,
		            submitted=False)
		d = self._dash(self.sandeep_user)
		where_type = find_value(d, DIRECT_TYPE)
		where_why = find_value(d, DIRECT_WHY)
		self.assertEqual(1, len(where_type), f"leave type at {where_type}")
		self.assertEqual(1, len(where_why), f"the written reason at {where_why}")
		self.assertTrue(where_type[0].startswith("$.pending_approvals"))
		self.assertTrue(where_why[0].startswith("$.pending_approvals"))

	def test_both_fields_are_dropped_at_the_query_not_in_the_renderer(self):
		"""AC-76(e). A field filtered in JavaScript is still in the response
		and still in the browser's cache, so the rule is about the `fields`
		list. Read from the source rather than trusted."""
		import inspect
		import re

		# **Comments stripped first.** The first version of this check read the
		# raw source and went red on the COMMENT that explains why the field
		# was removed - which is a test failing because the code was documented.
		# What matters is whether the field is asked of the database, so the
		# check reads the code and not the prose.
		src = inspect.getsource(hr_api.get_manager_dashboard)
		code = "\n".join(
			line for line in src.split("\n")
			if not line.strip().startswith("#"))
		code = re.sub(r'""".*?"""', "", code, flags=re.S)

		for field in ("leave_type", "description"):
			with self.subTest(field=field):
				self.assertNotIn(
					field, code,
					f"get_manager_dashboard's own code still names {field}")

	def test_the_comment_stripper_actually_strips(self):
		"""Check the check. If the stripper removed everything, the assertion
		above would pass over an empty string."""
		import inspect
		import re

		src = inspect.getsource(hr_api.get_manager_dashboard)
		code = "\n".join(line for line in src.split("\n")
		                 if not line.strip().startswith("#"))
		code = re.sub(r'""".*?"""', "", code, flags=re.S)
		self.assertIn("frappe.get_all", code, "the stripper removed the code too")
		self.assertNotIn("# 045 AC-76", code, "the stripper left comments behind")

	def test_the_field_lists_are_named_apart(self):
		"""So "what can this query return" is answerable by reading the query."""
		# And the two field lists are named apart, so "what can this query
		# return" is answerable by reading the query.
		self.assertEqual(("leave_type", "description"), hr_api.LEAVE_WHY_FIELDS)
		for f in hr_api.LEAVE_WHY_FIELDS:
			self.assertNotIn(f, hr_api.LEAVE_ROW_FIELDS)


class TestTheMonthCardAsksTheRightQuestion(_OnLeave):
	"""AC-21. Written to fail on the old code first."""

	def test_leave_that_began_last_month_and_is_still_running_is_counted(self):
		"""The person a manager most needs to see, and the one who was
		missing: off from before the first of the month, still off now."""
		start = add_days(get_first_day(nowdate()), -4)
		end = add_days(get_first_day(nowdate()), 2)
		self._leave(self.rahul, DIRECT_TYPE, DIRECT_WHY, from_date=start, to_date=end)
		d = self._dash(self.sandeep_user)
		names = [r.get("employee_name") for r in (d.get("month_leaves") or [])]
		self.assertTrue(names, "nothing at all in month_leaves")
		self.assertIn(
			frappe.db.get_value("Employee", self.rahul, "employee_name"), names,
			"leave that began last month and is still running was missed")

	def test_leave_that_starts_next_month_is_not_counted(self):
		"""The other half of the same defect."""
		start = add_days(get_last_day(nowdate()), 2)
		end = add_days(get_last_day(nowdate()), 4)
		self._leave(self.rahul, DIRECT_TYPE, DIRECT_WHY, from_date=start, to_date=end)
		d = self._dash(self.sandeep_user)
		rahul_name = frappe.db.get_value("Employee", self.rahul, "employee_name")
		rows = [r for r in (d.get("month_leaves") or [])
		        if r.get("employee_name") == rahul_name]
		self.assertEqual([], rows, "next month's leave is on this month's card")

	def test_the_month_card_carries_no_reason(self):
		"""AC-76 again, on this list specifically. It is a card, not an
		approval row."""
		self._leave(self.rahul, DIRECT_TYPE, DIRECT_WHY,
		            from_date=get_first_day(nowdate()),
		            to_date=add_days(get_first_day(nowdate()), 1))
		d = self._dash(self.sandeep_user)
		month = d.get("month_leaves") or []
		self.assertTrue(month, "nothing in month_leaves, so this proves nothing")
		self.assertEqual([], find_key(month, "leave_type"))
		self.assertEqual([], find_key(month, "description"))
