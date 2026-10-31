"""ALV-249 / ALV-261: a staff login sees its own Employee record and nobody else's.

The table in docs/slices/alv-249-employee-list-exposure/05-test-results-standard-row-vs-code-rule.md,
as tests. If a merge drops the hooks or the module, these fail.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import own_record_permission as orp

FIELDS = ["name", "date_of_birth", "cell_number", "personal_email", "current_address"]
REFS = ["Employee", "ToDo", "Leave Application", "Expense Claim", "Attendance"]


def _company():
	return frappe.db.get_value("Company", {}, "name")


class OwnRecordCase(FrappeTestCase):
	_n = 0

	def setUp(self):
		self.caller = frappe.session.user
		frappe.set_user("Administrator")
		OwnRecordCase._n += 1
		self.tag = OwnRecordCase._n
		self.company = _company()

	def tearDown(self):
		frappe.set_user(self.caller)

	def person(self, label, roles=("Employee",), reports_to=None, **extra):
		email = "orp%s%d@example.com" % (label.lower(), self.tag)
		if not frappe.db.exists("User", email):
			u = frappe.get_doc({"doctype": "User", "email": email, "first_name": "Orp" + label,
			                    "send_welcome_email": 0}).insert(ignore_permissions=True)
			u.add_roles(*roles)
		doc = {"doctype": "Employee", "first_name": "Orp" + label + str(self.tag), "company": self.company,
		       "date_of_birth": "1990-10-15", "date_of_joining": "2015-01-01",
		       "gender": frappe.db.get_value("Gender", {}, "name") or "Male", "status": "Active",
		       "user_id": email, "create_user_permission": 0, "reports_to": reports_to,
		       "cell_number": "9800000000"}
		doc.update(extra)
		return frappe.get_doc(doc).insert(ignore_permissions=True).name, email

	def own_rows(self, user, employee):
		return frappe.get_all("User Permission", filters={"user": user, "allow": "Employee",
		                      "for_value": employee, "apply_to_all_doctypes": 1}, pluck="name")

	def claim(self, employee):
		"""A draft claim row, written straight to the table: these tests are about who can read it."""
		d = frappe.new_doc("Expense Claim")
		d.update({"name": "ALV249-%s-%s" % (employee, frappe.generate_hash(length=6)), "employee": employee,
		          "company": self.company, "posting_date": "2026-10-01", "docstatus": 0,
		          "approval_status": "Draft", "status": "Draft"})
		d.db_insert()
		return d.name

	def as_user(self, user, fn):
		frappe.set_user(user)
		try:
			return fn()
		finally:
			frappe.set_user("Administrator")


class StaffSeeOnlyThemselves(OwnRecordCase):
	def setUp(self):
		super().setUp()
		self.me, self.me_user = self.person("Staff")
		self.other, self.other_user = self.person("Colleague")

	def test_new_joiner_gets_the_exact_row(self):
		row = self.own_rows(self.me_user, self.me)
		self.assertEqual(len(row), 1)
		up = frappe.get_doc("User Permission", row[0])
		self.assertFalse(up.applicable_for)
		self.assertFalse(up.hide_descendants)

	def test_rest_list_is_own_record_only(self):
		got = self.as_user(self.me_user, lambda: frappe.client.get_list(
			"Employee", fields=FIELDS, limit_page_length=0))
		self.assertEqual([r["name"] for r in got], [self.me])

	def test_the_extra_word_reference_doctype_does_not_open_it(self):
		from frappe.desk.reportview import execute
		for ref in REFS:
			got = self.as_user(self.me_user, lambda ref=ref: execute(
				"Employee", fields=FIELDS, reference_doctype=ref, limit_page_length=0))
			self.assertEqual([r.name for r in got], [self.me], ref)

	def test_count_with_reference_doctype(self):
		from frappe.desk.reportview import get_count

		def count():
			frappe.local.form_dict = frappe._dict(doctype="Employee", reference_doctype="ToDo")
			try:
				return get_count()
			finally:
				frappe.local.form_dict = frappe._dict()
		self.assertEqual(self.as_user(self.me_user, count), 1)

	def test_one_record_and_one_value(self):
		self.assertFalse(frappe.has_permission("Employee", "read", doc=self.other, user=self.me_user))
		self.assertTrue(frappe.has_permission("Employee", "read", doc=self.me, user=self.me_user))
		got = self.as_user(self.me_user, lambda: frappe.client.get_value(
			"Employee", "date_of_birth", {"name": self.other}))
		self.assertFalse(got)

	def test_link_search_and_the_hrms_app(self):
		from frappe.desk.search import search_link
		got = self.as_user(self.me_user, lambda: search_link(
			"Employee", "", reference_doctype="Leave Application", page_length=1000))
		self.assertEqual([r["value"] for r in got], [self.me])
		got = self.as_user(self.me_user, lambda: frappe.get_attr("hrms.api.get_all_employees")())
		self.assertEqual([r.name for r in got], [self.me])

	def test_birthday_and_leave_balance_reports_show_no_colleague(self):
		from frappe.desk.query_report import run

		def names(report, filters):
			try:
				res = run(report, filters=filters)
			except frappe.PermissionError:
				return set()
			finally:
				frappe.local.message_log = []
			out = set()
			for row in res.get("result") or []:
				out.add(row.get("employee") if isinstance(row, dict) else row[0])
			return out
		b = self.as_user(self.me_user, lambda: names("Employee Birthday", {"month": "Oct", "company": self.company}))
		self.assertNotIn(self.other, b)
		lb = self.as_user(self.me_user, lambda: names("Employee Leave Balance", {
			"from_date": "2026-01-01", "to_date": "2026-12-31", "company": self.company}))
		self.assertNotIn(self.other, lb)


class ExpenseClaimsAlv261(OwnRecordCase):
	def setUp(self):
		super().setUp()
		self.me, self.me_user = self.person("Claimer")
		self.other, _ = self.person("Other")
		self.mine = self.claim(self.me)
		self.theirs = self.claim(self.other)

	def test_list_shows_only_own_claims(self):
		got = self.as_user(self.me_user, lambda: frappe.get_list(
			"Expense Claim", filters={"name": ["like", "ALV249-%"]}, pluck="name", limit_page_length=0))
		self.assertIn(self.mine, got)
		self.assertNotIn(self.theirs, got)

	def test_no_write_on_someone_elses_claim(self):
		self.assertFalse(frappe.has_permission("Expense Claim", "write", doc=self.theirs, user=self.me_user))
		self.assertFalse(frappe.has_permission("Expense Claim", "read", doc=self.theirs, user=self.me_user))

	def test_an_approver_still_reaches_a_claim_shared_with_them(self):
		frappe.share.add_docshare("Expense Claim", self.theirs, user=self.me_user, read=1, write=1, submit=1,
		                          flags={"ignore_share_permission": 1})
		self.assertTrue(frappe.has_permission("Expense Claim", "read", doc=self.theirs, user=self.me_user))
		self.assertTrue(frappe.has_permission("Expense Claim", "submit", doc=self.theirs, user=self.me_user))


class ManagerSeesSelfAndTree(OwnRecordCase):
	def test_manager_lists_self_reports_and_their_reports(self):
		boss, boss_user = self.person("Boss")
		mid, _ = self.person("Mid", reports_to=boss)
		low, _ = self.person("Low", reports_to=mid)
		peer, _ = self.person("Peer")
		got = set(self.as_user(boss_user, lambda: frappe.get_list("Employee", pluck="name", limit_page_length=0,
		                                                           reference_doctype="ToDo")))
		self.assertEqual(got, {boss, mid, low})
		self.assertNotIn(peer, got)
		# manager_scope's narrow rows are left alone
		self.assertTrue(frappe.db.exists("User Permission", {"user": boss_user, "for_value": mid,
		                                                     "applicable_for": "Leave Application"}))


class WhoNeverGetsTheRow(OwnRecordCase):
	def test_hr_manager_and_system_manager_get_none_and_keep_their_counts(self):
		_, hr_user = self.person("Hr", roles=("Employee", "HR Manager"))
		sm, sm_user = self.person("Sm", roles=("Employee", "System Manager"))
		self.person("Staff")
		self.assertFalse(frappe.get_all("User Permission", filters={"user": hr_user, "allow": "Employee",
		                                "apply_to_all_doctypes": 1}))
		self.assertFalse(self.own_rows(sm_user, sm))
		total = frappe.db.count("Employee")
		self.assertEqual(self.as_user(sm_user, lambda: len(frappe.get_list("Employee", limit_page_length=0))), total)
		self.assertEqual(self.as_user(hr_user, lambda: len(frappe.get_list("Employee", limit_page_length=0))), total)

	def test_system_manager_is_excluded_even_without_a_read_row(self):
		"""Found on the test site: System Manager may hold no read row on Employee."""
		self.assertIn("System Manager", orp.excluded_roles())
		self.assertIn("Administrator", orp.excluded_roles())
		self.assertNotIn("Employee", orp.excluded_roles())
		self.assertNotIn("Employee Self Service", orp.excluded_roles())

	def test_promotion_to_hr_removes_the_row_and_back_restores_it(self):
		me, me_user = self.person("Riser")
		self.assertTrue(self.own_rows(me_user, me))
		frappe.get_doc("User", me_user).add_roles("HR User")
		self.assertFalse(self.own_rows(me_user, me))
		frappe.get_doc("User", me_user).remove_roles("HR User")
		self.assertTrue(self.own_rows(me_user, me))

	def test_leaver_loses_the_row_with_the_login_and_a_rehire_gets_it_back(self):
		"""ERPNext disables the login of an employee who is not Active, and enables it
		again on the way back (employee.py validate_for_enabled_user_id). The row follows
		the login, so a leaver never holds an enabled login without it."""
		me, me_user = self.person("Leaver")
		e = frappe.get_doc("Employee", me)
		e.status = "Left"
		e.relieving_date = "2026-10-30"
		e.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("User", me_user, "enabled"), 0)
		self.assertFalse(self.own_rows(me_user, me))
		e = frappe.get_doc("Employee", me)
		e.status = "Active"
		e.relieving_date = None
		e.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("User", me_user, "enabled"), 1)
		self.assertTrue(self.own_rows(me_user, me))

	def test_an_enabled_login_on_a_left_record_keeps_the_row(self):
		"""Fail closed if somebody re-enables a leaver's login by hand."""
		me, me_user = self.person("Reenabled")
		frappe.db.set_value("Employee", me, "status", "Left")
		u = frappe.get_doc("User", me_user)
		u.save(ignore_permissions=True)
		self.assertTrue(self.own_rows(me_user, me))

	def test_login_moved_to_another_record(self):
		me, me_user = self.person("Mover")
		e = frappe.get_doc("Employee", me)
		e.user_id = None
		e.save(ignore_permissions=True)
		self.assertFalse(self.own_rows(me_user, me))


class SafeToRunTwice(OwnRecordCase):
	def test_sync_twice_is_one_row(self):
		me, me_user = self.person("Twice")
		self.assertIsNone(orp.sync(me_user, me))
		self.assertIsNone(orp.sync(me_user, me))
		self.assertEqual(len(self.own_rows(me_user, me)), 1)

	def test_run_once_dry_run_writes_nothing_then_runs_clean_twice(self):
		me, me_user = self.person("Run")
		frappe.db.delete("User Permission", {"user": me_user})
		orp.run_once(dry_run=1, samples=[me_user])
		self.assertFalse(self.own_rows(me_user, me))
		self.assertEqual(orp.run_once(dry_run=0, samples=[me_user]), 0)
		self.assertEqual(len(self.own_rows(me_user, me)), 1)
		self.assertEqual(orp.run_once(dry_run=0, samples=[me_user]), 0)
		self.assertEqual(len(self.own_rows(me_user, me)), 1)

	def test_run_once_and_rollback_refuse_anyone_but_administrator(self):
		_, me_user = self.person("NotAdmin")
		frappe.set_user(me_user)
		try:
			self.assertRaises(frappe.PermissionError, orp.run_once)
			self.assertRaises(frappe.PermissionError, orp.rollback)
		finally:
			frappe.set_user("Administrator")

	def test_rollback_removes_only_the_exact_shape(self):
		boss, boss_user = self.person("RbBoss")
		rep, _ = self.person("RbRep", reports_to=boss)
		orp.rollback()
		self.assertFalse(self.own_rows(boss_user, boss))
		self.assertTrue(frappe.db.exists("User Permission", {"user": boss_user, "for_value": rep,
		                                                     "applicable_for": "Attendance"}))


class Wiring(FrappeTestCase):
	def test_hooks_are_wired(self):
		hooks = frappe.get_hooks("doc_events")
		self.assertIn("alvoraa_portal.own_record_permission.on_employee_update", hooks["Employee"]["on_update"])
		self.assertIn("alvoraa_portal.own_record_permission.on_user_update", hooks["User"]["on_update"])
