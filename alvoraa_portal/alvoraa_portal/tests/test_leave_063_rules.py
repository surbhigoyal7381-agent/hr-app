"""Slice 063: DTC's leave rules on every door - filing, the month, the limit,
who approves, the lock, and "DTC only".

Each test names the requirement it pins (spec section 11), so a merge that
drops a rule fails here. Self-approval tests run as the person's own user,
never as Administrator.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, get_first_day, getdate, nowdate

from alvoraa_portal import hr_api, leave_rules
from alvoraa_portal.tests import leave_063_fixtures as fx

LWP = "Leave Without Pay"


def setUpModule():
	global P
	P = fx.ensure_world()


def tearDownModule():
	fx.leave_world(P.values())


class Rules063Case(FrappeTestCase):
	def setUp(self):
		fx.clear_leave(*P.values())
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		fx.clear_leave(*P.values())

	def need(self, *days):
		if not all(days):
			self.skipTest("too close to the month boundary for this case")
		return days


class TestDTCOnly(Rules063Case):
	"""SEC-15 / AC-27: every rule fires only where the rule set is enabled."""

	def test_apply_list_follows_the_rule_set_state(self):
		frappe.set_user(fx.user("Priya"))
		on = [t["leave_type"] for t in hr_api.get_leave_summary()["types_offered"]]
		self.assertIn(fx.PAID, on)
		self.assertIn(LWP, on)
		frappe.set_user(fx.user("Offco"))
		off = [t["leave_type"] for t in hr_api.get_leave_summary()["types_offered"]]
		self.assertNotIn(fx.PAID, off)
		self.assertNotIn(LWP, off)
		frappe.set_user(fx.user("Plain"))
		plain = hr_api.get_leave_summary()
		self.assertIn(LWP, [t["leave_type"] for t in plain["types_offered"]])
		self.assertNotIn("paid_leaves", plain)

	def test_a_switched_off_rule_set_refuses_both_types_on_the_server(self):
		"""AC-25: hiding an option is not a gate."""
		d = fx.future_day(1) or nowdate()
		for t in (fx.PAID, LWP):
			with self.assertRaises(frappe.PermissionError):
				fx.apply_as(fx.user("Offco"), leave_type=t, from_date=d, to_date=d)
		self.assertFalse(frappe.db.exists("Leave Application", {"employee": P["off"]}))

	def test_no_rule_set_means_no_month_rule_and_no_limit(self):
		"""AC-26: another tenant files LWP for a past month and over 5 days."""
		start = add_days(get_first_day(nowdate()), -20)
		res = fx.apply_as(fx.user("Plain"), leave_type=LWP, from_date=start,
		                  to_date=add_days(start, 6))
		self.assertTrue(res["name"])

	def test_switching_the_rule_set_off_takes_effect_at_once(self):
		"""AC-28: the cached rule set is dropped on save."""
		name = frappe.db.get_value("Alvoraa Payroll Rule Set", {"company": fx.COMPANY}, "name")
		rs = frappe.get_doc("Alvoraa Payroll Rule Set", name)
		rs.enabled = 0
		rs.flags.ignore_permissions = True
		rs.save()
		try:
			self.assertIsNone(leave_rules.rule_set_for(fx.COMPANY))
		finally:
			rs.reload()
			rs.enabled = 1
			rs.save()
			frappe.db.commit()


class TestFiling(Rules063Case):
	def test_paid_leaves_go_to_the_named_approver(self):
		"""AC-35: filed Open with leave_approver set, which the portal never did."""
		d, = self.need(fx.future_day(1))
		res = fx.apply_as(fx.user("Priya"), leave_type=fx.PAID, from_date=d, to_date=d)
		doc = frappe.get_doc("Leave Application", res["name"])
		self.assertEqual(doc.status, "Open")
		self.assertEqual(doc.docstatus, 0)
		self.assertEqual(doc.leave_approver, fx.user("Sunil"))

	def test_lwp_is_filed_with_no_named_approver(self):
		"""Spec 7.2: HR in scope decide, so nobody is named."""
		d, = self.need(fx.future_day(1))
		res = fx.apply_as(fx.user("Priya"), leave_type=LWP, from_date=d, to_date=d)
		self.assertFalse(frappe.db.get_value("Leave Application", res["name"], "leave_approver"))

	def test_no_named_approver_refuses_paid_leaves_but_not_lwp(self):
		"""AC-37 / SEC-12."""
		d, = self.need(fx.future_day(1))
		frappe.db.set_value("Employee", P["rohit"], "leave_approver", None)
		try:
			with self.assertRaisesRegex(frappe.ValidationError, "nobody is set to approve"):
				fx.apply_as(fx.user("Rohit"), leave_type=fx.PAID, from_date=d, to_date=d)
			self.assertTrue(fx.apply_as(fx.user("Rohit"), leave_type=LWP, from_date=d,
			                            to_date=d)["name"])
		finally:
			frappe.db.set_value("Employee", P["rohit"], "leave_approver", fx.user("Sunil"))

	def test_contract_staff_cannot_file_paid_leaves(self):
		"""AC-32: refused as not offered."""
		d, = self.need(fx.future_day(1))
		frappe.set_user(fx.user("Ritika"))
		with self.assertRaises(frappe.PermissionError):
			hr_api.apply_leave(fx.PAID, d, d, on_behalf_of=P["manoj"])

	def test_a_client_status_is_ignored(self):
		"""AC-36 / SEC-3a: the endpoint takes no status."""
		d, = self.need(fx.future_day(1))
		frappe.set_user(fx.user("Priya"))
		with self.assertRaises(TypeError):
			hr_api.apply_leave(LWP, d, d, status="Approved")


class TestCurrentMonthOnly(Rules063Case):
	"""SEC-6, AC-67..70 - every door, HR included."""

	def test_a_day_last_month_is_refused_through_the_portal(self):
		d = add_days(get_first_day(nowdate()), -2)
		with self.assertRaisesRegex(frappe.ValidationError, "Leave can only be asked for days in"):
			fx.apply_as(fx.user("Priya"), leave_type=LWP, from_date=d, to_date=d)

	def test_and_through_a_direct_insert(self):
		d = add_days(get_first_day(nowdate()), -2)
		doc = frappe.get_doc({"doctype": "Leave Application", "employee": P["priya"],
		                      "leave_type": LWP, "from_date": d, "to_date": d,
		                      "status": "Open", "company": fx.COMPANY})
		with self.assertRaisesRegex(frappe.ValidationError, "Leave can only be asked for days in"):
			doc.insert(ignore_permissions=True)

	def test_a_past_day_this_month_is_allowed(self):
		d, = self.need(fx.past_day(1))
		self.assertTrue(fx.apply_as(fx.user("Priya"), leave_type=LWP, from_date=d,
		                            to_date=d)["name"])

	def test_approval_after_the_month_has_turned_is_refused(self):
		"""AC-69: filed in an earlier month, approved now (desk, as HR)."""
		d = add_days(get_first_day(nowdate()), -1)
		doc = frappe.get_doc({"doctype": "Leave Application", "employee": P["priya"],
		                      "leave_type": LWP, "from_date": d, "to_date": d,
		                      "status": "Open", "company": fx.COMPANY})
		doc.flags.ignore_validate = True
		doc.insert(ignore_permissions=True)
		frappe.set_user(fx.user("Ritika"))
		doc = frappe.get_doc("Leave Application", doc.name)
		doc.status = "Approved"
		with self.assertRaisesRegex(frappe.ValidationError, "can no longer be approved"):
			doc.submit()


class TestLwpLimit(Rules063Case):
	"""SEC-13, AC-42..46."""

	def _lwp(self, start, end, half=0, status="Open"):
		doc = frappe.get_doc({"doctype": "Leave Application", "employee": P["rohit"],
		                      "leave_type": LWP, "from_date": start, "to_date": end,
		                      "half_day": half, "half_day_date": start if half else None,
		                      "status": status, "company": fx.COMPANY})
		doc.insert(ignore_permissions=True)
		return doc

	def test_four_and_a_half_plus_a_half_is_allowed_one_more_half_is_not(self):
		days = [fx.month_day(n) for n in range(1, 8)]
		self.need(*days)
		self._lwp(days[0], days[3])           # 4
		self._lwp(days[4], days[4], half=1)   # 4.5
		self._lwp(days[5], days[5], half=1)   # 5.0
		with self.assertRaisesRegex(frappe.ValidationError, "The limit is 5 days a month"):
			self._lwp(days[6], days[6], half=1)

	def test_rejected_and_paid_leaves_do_not_count(self):
		days = [fx.month_day(n) for n in range(1, 8)]
		self.need(*days)
		r = self._lwp(days[0], days[4])        # 5
		frappe.db.set_value("Leave Application", r.name, "status", "Rejected")
		self.assertEqual(leave_rules.lwp_in_play(P["rohit"], days[0]), 0)
		self.assertTrue(self._lwp(days[5], days[6]).name)

	def test_a_request_across_two_months_counts_each_day_in_its_own_month(self):
		"""AC-45: only this month's days count against this month."""
		last = getdate(frappe.utils.get_last_day(nowdate()))
		start = add_days(last, -1)
		if getdate(start) < getdate(nowdate()):
			self.skipTest("needs two days left in the month")
		doc = self._lwp(start, add_days(last, 1))
		self.assertEqual(leave_rules.lwp_in_play(P["rohit"], start), 2)
		self.assertEqual(leave_rules.lwp_in_play(P["rohit"], add_days(last, 1)), 1)
		doc.delete()

	def test_two_open_requests_over_the_limit_fail_at_the_first_approval(self):
		"""AC-44: put in directly, as if made before the check existed."""
		days = [fx.month_day(n) for n in range(1, 7)]
		self.need(*days)
		a = self._lwp(days[0], days[2])
		b = frappe.get_doc({"doctype": "Leave Application", "employee": P["rohit"],
		                    "leave_type": LWP, "from_date": days[3], "to_date": days[5],
		                    "status": "Open", "company": fx.COMPANY})
		b.flags.ignore_validate = True
		b.insert(ignore_permissions=True)
		frappe.db.commit()
		with self.assertRaisesRegex(frappe.ValidationError, "The limit is 5 days a month"):
			fx.approve(a.name, by=fx.user("Ritika"))


class TestWhoApproves(Rules063Case):
	"""SEC-3 rev. 3, AC-47..56."""

	def _filed(self, who, t):
		d, = self.need(fx.future_day(1))
		return fx.apply_as(fx.user(who), leave_type=t, from_date=d, to_date=d)["name"]

	def test_hr_in_scope_approves_lwp(self):
		name = self._filed("Priya", LWP)
		fx.approve(name, by=fx.user("Ritika"))
		self.assertEqual(frappe.db.get_value("Leave Application", name, "status"), "Approved")

	def test_hr_out_of_branch_cannot(self):
		"""AC-49: Anil looks after branch South only."""
		name = self._filed("Priya", LWP)
		frappe.set_user(fx.user("Anil"))
		self.assertFalse(hr_api._can_action_leave(name))
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.PermissionError):
			fx.approve(name, by=fx.user("Anil"))
		self.assertEqual(frappe.db.get_value("Leave Application", name, "docstatus"), 0)

	def test_our_scope_holds_where_frappes_own_check_would_not(self):
		"""A Branch permission set to apply to Employee records only: Frappe's
		own check on the Leave Application then lets Anil through, and
		permitted_employees() - the scope HR screens use - still does not."""
		up = frappe.db.get_value("User Permission", {"user": fx.user("Anil"), "allow": "Branch"},
		                         "name")
		frappe.db.set_value("User Permission", up, {"apply_to_all_doctypes": 0,
		                                            "applicable_for": "Employee"})
		frappe.clear_cache(user=fx.user("Anil"))
		try:
			name = self._filed("Priya", LWP)
			frappe.set_user(fx.user("Anil"))
			doc = frappe.get_doc("Leave Application", name)
			self.assertTrue(frappe.has_permission("Leave Application", "submit", doc=doc))
			self.assertFalse(hr_api._can_action_leave(name))
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("User Permission", up, {"apply_to_all_doctypes": 1,
			                                            "applicable_for": None})
			frappe.clear_cache(user=fx.user("Anil"))

	def test_nobody_approves_their_own_lwp(self):
		"""AC-50: Ritika's own LWP, as Ritika, refused on the portal and the desk."""
		name = self._filed("Ritika", LWP)
		with self.assertRaises(frappe.PermissionError):
			fx.approve(name, by=fx.user("Ritika"))
		frappe.set_user(fx.user("Ritika"))
		doc = frappe.get_doc("Leave Application", name)
		doc.status = "Approved"
		with self.assertRaises(frappe.PermissionError):
			doc.submit()

	def test_hr_who_is_not_the_named_approver_cannot_approve_paid_leaves(self):
		"""AC-51 (e)."""
		name = self._filed("Priya", fx.PAID)
		frappe.set_user(fx.user("Ritika"))
		self.assertFalse(hr_api._can_action_leave(name))

	def test_the_named_approver_approves_paid_leaves_but_not_lwp(self):
		"""AC-51 (f), AC-53."""
		pl = self._filed("Priya", fx.PAID)
		frappe.set_user(fx.user("Sunil"))
		self.assertTrue(hr_api._can_action_leave(pl))
		frappe.set_user("Administrator")
		lwp_d = fx.future_day(2)
		if not lwp_d:
			self.skipTest("too close to the month end")
		lwp = fx.apply_as(fx.user("Priya"), leave_type=LWP, from_date=lwp_d, to_date=lwp_d)["name"]
		frappe.db.set_value("Leave Application", lwp, "leave_approver", fx.user("Sunil"))
		frappe.set_user(fx.user("Sunil"))
		self.assertFalse(hr_api._can_action_leave(lwp))

	def test_elsewhere_lwp_keeps_the_named_approver_rule(self):
		"""AC-52: no rule set, so HR is not the approver of LWP."""
		frappe.db.set_value("Employee", P["plain"], "leave_approver", fx.user("Kavita"))
		d = add_days(nowdate(), 1)
		name = fx.apply_as(fx.user("Plain"), leave_type=LWP, from_date=d, to_date=d)["name"]
		frappe.db.set_value("Leave Application", name, "leave_approver", fx.user("Kavita"))
		frappe.set_user(fx.user("Ritika"))
		self.assertFalse(hr_api._can_action_leave(name))

	def test_hr_sees_lwp_in_the_inbox_and_the_scope_stays_in_the_database(self):
		"""AC-47: the HR row, with the "N of 5" figure and who will be told.

		The leave part is built on its own. Building all six parts also builds the
		policies part, which raises for anyone whose module profile blocks the
		policy library - as it does on a fresh site with no plan (CI run
		39714021470). That is a fault of its own, reported separately; it is not
		what this test is about."""
		from alvoraa_portal import inbox_api

		name = self._filed("Priya", LWP)
		frappe.set_user(fx.user("Ritika"))
		part = inbox_api._part_leave_approvals(inbox_api._Who(frappe.session.user))
		self.assertNotIn(P["priya"], str(part.filters), "no employee id list is shipped")
		rows = {r["name"]: r for r in part.rows()}
		self.assertIn(name, rows)
		self.assertEqual(rows[name]["lwp_in_play"], 1)
		self.assertEqual(rows[name]["chain_top"], "Kavita L063")
		frappe.set_user(fx.user("Anil"))
		part = inbox_api._part_leave_approvals(inbox_api._Who(frappe.session.user))
		self.assertNotIn(name, [r["name"] for r in part.rows()])
		frappe.set_user(fx.user("Sunil"))
		part = inbox_api._part_leave_approvals(inbox_api._Who(frappe.session.user))
		self.assertNotIn(name, [r["name"] for r in part.rows()])

	def test_a_withdrawn_request_writes_nothing_when_approved(self):
		"""AC-55."""
		name = self._filed("Priya", LWP)
		frappe.set_user(fx.user("Priya"))
		hr_api.cancel_leave(name)
		with self.assertRaisesRegex(frappe.ValidationError, "cancelled this request"):
			fx.approve(name, by=fx.user("Ritika"))


class TestOnBehalf(Rules063Case):
	"""SEC-7, AC-91..93."""

	def test_hr_out_of_branch_cannot_file_for_someone(self):
		d, = self.need(fx.future_day(1))
		frappe.set_user(fx.user("Anil"))
		with self.assertRaisesRegex(frappe.PermissionError, "branches you look after"):
			hr_api.apply_leave(LWP, d, d, on_behalf_of=P["priya"])

	def test_the_picker_offers_only_people_in_scope_and_marks_no_login(self):
		frappe.set_user(fx.user("Anil"))
		ids = {e["name"] for e in hr_api.get_all_active_employees()["employees"]}
		self.assertNotIn(P["priya"], ids)
		frappe.set_user(fx.user("Ritika"))
		rows = {e["name"]: e for e in hr_api.get_all_active_employees()["employees"]}
		self.assertEqual(rows[P["manoj"]]["no_login"], 1)
		self.assertEqual(rows[P["priya"]]["no_login"], 0)
		self.assertNotIn("user_id", rows[P["priya"]])

	def test_hr_on_behalf_sees_the_days_left_but_not_the_card(self):
		"""Q-S2 / A-1 (Surbhi, 25 Oct 2026; replaces X-2): the days left, for a
		person in the caller's company AND branch. Still no card (SEC-1c)."""
		frappe.set_user(fx.user("Ritika"))
		s = hr_api.get_leave_summary(employee_id=P["rohit"])
		self.assertNotIn("paid_leaves", s)
		pl = [t for t in s["types_offered"] if t["leave_type"] == fx.PAID][0]
		self.assertEqual(pl["left"], 4)

	def test_hr_in_another_branch_sees_no_figure(self):
		"""Bad news 3: _hr_target_employee checks the company alone, so the days
		figure carries its own company-and-branch check."""
		frappe.set_user(fx.user("Anil"))
		s = hr_api.get_leave_summary(employee_id=P["rohit"])
		pl = [t for t in s["types_offered"] if t["leave_type"] == fx.PAID][0]
		self.assertNotIn("left", pl)


class TestTheLock(Rules063Case):
	"""D1, AC-96..98."""

	def test_hr_cannot_change_or_delete_paid_leaves(self):
		frappe.set_user(fx.user("Ritika"))
		doc = frappe.get_doc("Leave Type", fx.PAID)
		doc.max_continuous_days_allowed = 3
		with self.assertRaisesRegex(frappe.PermissionError, "cannot be changed or deleted"):
			doc.save(ignore_permissions=True)
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("Leave Type", fx.PAID, ignore_permissions=True)

	def test_it_must_be_created_with_the_right_flags(self):
		frappe.delete_doc("Leave Type", fx.PAID, force=True, ignore_permissions=True)
		frappe.set_user(fx.user("Ritika"))
		bad = frappe.get_doc({"doctype": "Leave Type", "leave_type_name": fx.PAID,
		                      "is_lwp": 1, "allow_negative": 1})
		with self.assertRaisesRegex(frappe.ValidationError, "must be created with"):
			bad.insert(ignore_permissions=True)


class TestTheChainNotice(Rules063Case):
	"""PRIV-1, AC-57..62."""

	def test_each_manager_up_the_chain_gets_four_facts_and_never_the_reason(self):
		d, = self.need(fx.future_day(1))
		name = fx.apply_as(fx.user("Priya"), leave_type=fx.PAID, from_date=d, to_date=d,
		                   reason="SECRET-REASON-063")["name"]
		res = fx.approve(name, by=fx.user("Sunil"))
		logs = frappe.get_all("Notification Log",
		                      filters={"document_type": "Leave Application", "document_name": name,
		                               "subject": ["like", "%will be away on%"]},
		                      fields=["for_user", "subject", "email_content"])
		told = {l.for_user for l in logs}
		# Kavita, above Sunil, is told. Sunil approved it himself and is not told his
		# own approval (this Frappe alerts the sender too, so the code leaves him out);
		# the employee never.
		self.assertIn(fx.user("Kavita"), told)
		self.assertNotIn(fx.user("Sunil"), told)
		self.assertNotIn(fx.user("Priya"), told)
		for l in logs:
			text = l.subject + l.email_content
			self.assertIn("Priya L063", text)
			self.assertIn("has been approved", text)
			for never in ("SECRET-REASON-063", fx.PAID, "Sunil Mehra"):
				self.assertNotIn(never, text)
		self.assertEqual(res["told_top"], "Kavita L063")

	def _approved_by_sunil(self, reason="SECRET-REASON-063"):
		d, = self.need(fx.future_day(1))
		name = fx.apply_as(fx.user("Priya"), leave_type=fx.PAID, from_date=d, to_date=d,
		                   reason=reason)["name"]
		res = fx.approve(name, by=fx.user("Sunil"))
		logs = frappe.get_all("Notification Log",
		                      filters={"document_type": "Leave Application", "document_name": name,
		                               "subject": ["like", "%will be away on%"]},
		                      fields=["for_user", "subject", "email_content"])
		return name, res, logs

	def test_hr_in_scope_are_told_of_every_approval_once_with_the_same_four_facts(self):
		"""AC-145 / N-1b: Ritika (looks after Priya) is told; Anil (another branch),
		Priya and the approver are not; no type, reason or approver in the text."""
		_name, _res, logs = self._approved_by_sunil()
		told = [l.for_user for l in logs]
		self.assertIn(fx.user("Ritika"), told)
		self.assertEqual(len(told), len(set(told)), "once each")
		for u in (fx.user("Anil"), fx.user("Priya"), fx.user("Sunil")):
			self.assertNotIn(u, told)
		hr = [l for l in logs if l.for_user == fx.user("Ritika")][0]
		self.assertRegex(hr.subject, r"^Priya L063 will be away on ")
		self.assertIn("has been approved", hr.email_content)
		self.assertIn("You are told because you look after Priya's records in HR. "
		              "There is nothing for you to do.", hr.email_content)
		for never in ("SECRET-REASON-063", fx.PAID, "Sunil Mehra"):
			self.assertNotIn(never, hr.subject + hr.email_content)

	def test_hr_who_is_in_the_chain_is_told_once_with_the_chain_wording(self):
		"""AC-145: Ritika also manages Priya here; she gets one notice, not two."""
		frappe.db.set_value("Employee", P["sunil"], "reports_to", P["ritika"])
		try:
			_name, _res, logs = self._approved_by_sunil()
		finally:
			frappe.db.set_value("Employee", P["sunil"], "reports_to", P["kavita"])
			frappe.db.commit()      # the approval committed the change, so the undo must too
		mine = [l for l in logs if l.for_user == fx.user("Ritika")]
		self.assertEqual(len(mine), 1)
		self.assertIn("is in your team", mine[0].email_content)

	def test_lwp_approved_by_hr_tells_the_other_hr_but_not_the_approver(self):
		"""AC-145: the approver is never told her own approval."""
		d, = self.need(fx.future_day(1))
		name = fx.apply_as(fx.user("Priya"), leave_type=LWP, from_date=d, to_date=d)["name"]
		fx.approve(name, by=fx.user("Ritika"))
		told = frappe.get_all("Notification Log",
		                      filters={"document_name": name,
		                               "subject": ["like", "%will be away on%"]}, pluck="for_user")
		self.assertNotIn(fx.user("Ritika"), told)
		self.assertIn(fx.user("Kavita"), told)

	def test_the_told_line_counts_managers_only(self):
		"""AC-146: Sunil approves, Kavita is above him, Ritika (HR) is also told.
		The employee's line says one person, and so does the approver's reply."""
		name, res, logs = self._approved_by_sunil()
		self.assertGreaterEqual(len(logs), 2, "Kavita and Ritika were both told")
		self.assertEqual(res["told_n"], 1)
		self.assertEqual(res["told_top"], "Kavita L063")
		frappe.set_user(fx.user("Priya"))
		row = [a for a in hr_api.get_leave_summary()["applications"] if a["name"] == name][0]
		self.assertEqual(row["told_count"], 1)
		self.assertEqual(row["told_top_name"], "Kavita L063")

	def test_nothing_on_decline(self):
		d, = self.need(fx.future_day(1))
		name = fx.apply_as(fx.user("Priya"), leave_type=fx.PAID, from_date=d, to_date=d)["name"]
		fx.approve(name, by=fx.user("Sunil"), action="reject")
		self.assertFalse(frappe.get_all("Notification Log",
		                                filters={"document_name": name,
		                                         "subject": ["like", "%will be away on%"]}))

	def test_a_loop_stops_the_walk(self):
		frappe.db.set_value("Employee", P["kavita"], "reports_to", P["sunil"])
		try:
			chain = leave_rules.chain_of(P["priya"])
			self.assertEqual([c.name for c in chain], [P["sunil"], P["kavita"]])
		finally:
			frappe.db.set_value("Employee", P["kavita"], "reports_to", None)

	def test_a_manager_who_has_left_stops_the_walk(self):
		frappe.db.set_value("Employee", P["sunil"], "status", "Left")
		try:
			self.assertEqual(leave_rules.chain_of(P["priya"]), [])
		finally:
			frappe.db.set_value("Employee", P["sunil"], "status", "Active")


class TestHalfDayCorrection(Rules063Case):
	"""OD-1 remedy (iv): the hook lets Frappe's own half-day correction reach a
	half-day leave day; HR's approval then counts the other half."""

	def test_a_half_day_correction_reaches_a_half_day_leave_day(self):
		d, = self.need(fx.past_day(1))
		name = fx.apply_as(fx.user("Priya"), leave_type=fx.PAID, from_date=d, to_date=d,
		                   half_day=1, half_day_date=d)["name"]
		fx.approve(name, by=fx.user("Sunil"))
		att = frappe.db.get_value("Attendance", {"employee": P["priya"], "attendance_date": d,
		                                         "docstatus": 1}, "name")
		# DTC's rows carry a shift and DTC has no Shift Assignments.
		frappe.db.set_value("Attendance", att, "shift", fx.SHIFT)
		from alvoraa_portal import attendance_correction

		frappe.set_user(fx.user("Priya"))
		# The Attendance page's ordinary one-day form: no half-day tick.
		req = attendance_correction.raise_correction(d, d, "Forgot to Punch Out")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Attendance", att, "half_day_status"), "Absent")
		doc = frappe.get_doc("Attendance Request", req["name"])
		self.assertEqual(doc.shift, fx.SHIFT)
		self.assertEqual((doc.half_day, str(doc.half_day_date)), (1, d))
		doc.submit()
		row = frappe.db.get_value("Attendance", att, ["half_day_status", "attendance_request"],
		                          as_dict=True)
		self.assertEqual(row.half_day_status, "Present")
		self.assertEqual(row.attendance_request, doc.name)
		self.assertEqual(frappe.db.count("Attendance", {"employee": P["priya"],
		                                                "attendance_date": d,
		                                                "docstatus": 1}), 1,
		                 "no second attendance for the same day")
		from alvoraa_portal.payroll_rules_apply import judge, prepare, rule_set_for

		rs = rule_set_for(fx.COMPANY)
		row = frappe.db.get_value("Attendance", att, ["name", "employee", "attendance_date",
		                                              "status", "shift", "company",
		                                              "leave_type", "leave_application",
		                                              "attendance_request"], as_dict=True)
		v = judge(row, prepare(rs, d, d))
		self.assertTrue(v.half_leave)
		self.assertFalse(v.absent)
		self.assertEqual(v.day_credit, 0.5)

	def test_without_the_correction_the_half_is_absent_and_the_row_says_so(self):
		d, = self.need(fx.past_day(1))
		name = fx.apply_as(fx.user("Priya"), leave_type=fx.PAID, from_date=d, to_date=d,
		                   half_day=1, half_day_date=d)["name"]
		fx.approve(name, by=fx.user("Sunil"))
		frappe.set_user(fx.user("Priya"))
		app = [a for a in hr_api.get_leave_summary()["applications"] if a["name"] == name][0]
		self.assertEqual(app["missing_punch"], "check-in")

	def test_a_full_day_correction_is_untouched(self):
		d, = self.need(fx.past_day(1))
		doc = frappe.get_doc({"doctype": "Attendance Request", "employee": P["rohit"],
		                      "company": fx.COMPANY, "from_date": d, "to_date": d,
		                      "reason": "Forgot to Punch Out"})
		doc.insert(ignore_permissions=True)
		self.assertFalse(doc.shift)
