"""Slice 065: replacement plans - who may see one, and that an erase leaves nothing.

A plan is HR's private note that the person in a seat may need replacing.
These tests prove the five things that matter (01c): one gate on every door
(SEC-1), no side doors (SEC-3), nothing in the Positions reply for anyone
outside the gate (SEC-4), a real erase (PRIV-2), and plans that end by
themselves (PRIV-3).

EVERY READER TEST RUNS AS THE NAMED USER, never as Administrator, who passes
every check by design and would prove nothing (01c §10).

Kept in alvoraa_portal's tests, beside 064's, because these run in CI.
"""

import json
import os
from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowdate

import hrms.alvoraa_org_structure.register as register
from alvoraa_portal.tests.test_positions_064 import Positions064Case, _second_company
import hrms.alvoraa_org_structure.plans as plans
from hrms.alvoraa_org_structure.tests.test_org_structure import _company, _gender

PLAN = plans.DOCTYPE
OWNERS = "Org Structure Editor"


def _role(name):
	if not frappe.db.exists("Role", name):
		frappe.get_doc({"doctype": "Role", "role_name": name, "desk_access": 1}).insert(
			ignore_permissions=True
		)


def insert_plan(assignment, note=None, reason="Personal reasons", ends=None):
	"""Straight through the record, as the desk or REST would - so the rules
	are proved to live in the record, not only in the portal's calls."""
	return frappe.get_doc({"doctype": PLAN, "assignment": assignment, "note": note, "reason": reason,
	                       "improvement_ends_on": ends}).insert().name


def _wipe_plans():
	"""Test hygiene only: every plan, and any copy a half-finished test left
	behind, which would otherwise trip every later self-check on this site."""
	frappe.db.delete(PLAN)
	for doctype, field in plans.TRACE_TABLES:
		frappe.db.delete(doctype, {field: PLAN})


# The readers, made once for the whole file: creating a user with roles is
# the slow part of every fixture here, and none of these tests changes one.
# (email, role, branch key, has an Employee record)
READERS = {
	"hrA": ("hra.065@example.com", "HR Manager", None, True),
	"hrA2": ("hra2.065@example.com", "HR Manager", None, True),
	"hrD": ("hrd.065@example.com", "HR Manager", "delhi", True),
	"hrSubj": ("hrsubj.065@example.com", "HR Manager", None, True),
	"own": ("own.065@example.com", OWNERS, None, True),
	"sys": ("sys.065@example.com", "System Manager", None, False),
	"head": ("head.065@example.com", "Projects User", "delhi", True),
	"emp": ("emp.065@example.com", "Employee", None, True),
	"hrLeft": ("hrleft.065@example.com", "HR Manager", None, True),
	"hrB": ("hrb.065@example.com", "HR Manager", None, True),
}
BRANCHES = {"delhi": "Delhi 065", "noida": "Noida 065"}


class Plan065Case(Positions064Case):
	"""F-PLAN, cut to what each test needs: one company with two branches,
	a second company, and the readers and must-nots the spec names."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		_role(OWNERS)
		cls.company_b = _second_company()
		for b in BRANCHES.values():
			if not frappe.db.exists("Branch", b):
				frappe.get_doc({"doctype": "Branch", "branch": b}).insert(ignore_permissions=True)
		for email, role, branch, has_employee in READERS.values():
			if not frappe.db.exists("User", email):
				frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split(".")[0].title(),
				                "enabled": 1, "send_welcome_email": 0}).insert(ignore_permissions=True)
			if has_employee and not frappe.db.exists("Employee", {"user_id": email}):
				frappe.get_doc({
					"doctype": "Employee", "first_name": email.split(".")[0].title() + "065",
					# HR for the second company works for it. ERPNext then gives the
					# login a Company User Permission of its own, which is its scope.
					"company": cls.company_b if email == READERS["hrB"][0] else _company(),
					"date_of_birth": "1990-01-01", "date_of_joining": "2020-01-01",
					"gender": _gender(), "status": "Active", "user_id": email,
				}).insert(ignore_permissions=True)
			user = frappe.get_doc("User", email)
			user.flags.ignore_permissions = True
			user.add_roles(role)
			if branch and not frappe.db.exists("User Permission", {"user": email, "allow": "Branch"}):
				frappe.get_doc({"doctype": "User Permission", "user": email, "allow": "Branch",
				                "for_value": BRANCHES[branch], "apply_to_all_doctypes": 0,
				                "applicable_for": "Employee"}).insert(ignore_permissions=True)
		# A leaver whose login still works, holding HR Manager (lesson 3).
		frappe.db.set_value("Employee", {"user_id": READERS["hrLeft"][0]},
		                    {"status": "Left", "relieving_date": add_days(nowdate(), -3)})
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		frappe.db.delete(PLAN)
		for email, *_rest in READERS.values():
			frappe.db.delete("User Permission", {"user": email})
			for emp in frappe.get_all("Employee", filters={"user_id": email}, pluck="name"):
				frappe.delete_doc("Employee", emp, force=True, ignore_permissions=True)
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)
		frappe.db.commit()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		_wipe_plans()
		for key, (email, *_rest) in READERS.items():
			setattr(self, key, email)
		# Who may open Positions here, as an administrator would set it.
		self.rows(("HR Manager", "write"), ("System Manager", "read"), (OWNERS, "write"),
		          ("Projects User", "read"))
		self.delhi, self.noida = BRANCHES["delhi"], BRANCHES["noida"]
		role = self._role_name()

		self.cashier = self.pos("Cashier 065", seats=4, branch=self.delhi, designation=role)
		self.rso = self.pos("RSO 065", seats=2, branch=self.noida, designation=role)
		self.recruiter = self.pos("Recruiter 065", seats=1, branch=self.delhi, designation=role)
		self.hr_head = self.pos("HR Head 065", seats=1, branch=self.delhi, designation=role)
		self.closed = self.pos("Closed 065", seats=1, branch=self.delhi)

		self.ritu, self.sunil = self.person("Ritu065"), self.person("Sunil065")
		self.noida_person, self.aarti = self.person("Noida065"), self.person("Aarti065")
		self.a_ritu = self.assign(self.ritu, self.cashier.name).name
		self.a_sunil = self.assign(self.sunil, self.cashier.name).name
		self.a_noida = self.assign(self.noida_person, self.rso.name).name
		self.a_aarti = self.assign(self.aarti, self.recruiter.name).name
		self.a_subj = self.assign(self._emp_of(self.hrSubj), self.hr_head.name).name
		frappe.db.set_value("Alvoraa Position", self.closed.name, "status", "Closed")
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		_wipe_plans()
		frappe.db.delete("Custom DocPerm", {"parent": PLAN})
		frappe.db.delete("Version", {"ref_doctype": "DocType", "docname": PLAN})
		frappe.clear_cache(doctype=PLAN)
		frappe.local.role_permissions = {}
		frappe.db.commit()
		super().tearDown()

	def _role_name(self):
		name = frappe.db.get_value("Designation", {}, "name")
		if not name:
			name = frappe.get_doc({"doctype": "Designation", "designation_name": "Role 065"}).insert(
				ignore_permissions=True).name
		return name

	def _emp_of(self, user):
		return frappe.db.get_value("Employee", {"user_id": user}, "name")

	def owners_see(self, on=True):
		"""The tenant's choice: the owners' role gets Read on plans, made the
		way Role Permissions Manager makes it (a Custom DocPerm table)."""
		frappe.set_user("Administrator")
		frappe.db.delete("Custom DocPerm", {"parent": PLAN})
		rows = [("HR Manager", dict(read=1, write=1, create=1, delete=1)), ("System Manager", dict(read=1))]
		if on:
			rows.append((OWNERS, dict(read=1)))
		for role, rights in rows:
			d = frappe.get_doc({"doctype": "Custom DocPerm", "parent": PLAN, "parenttype": "DocType",
			                    "parentfield": "permissions", "role": role, "permlevel": 0, **rights})
			d.flags.ignore_permissions = True
			d.db_insert()
		frappe.clear_cache(doctype=PLAN)
		frappe.local.role_permissions = {}
		frappe.db.commit()

	def make_plan(self, assignment, note=None, as_user=None, reason="Personal reasons", ends=None):
		frappe.set_user(as_user or self.hrA)
		name = insert_plan(assignment, note, reason, ends)
		frappe.set_user("Administrator")
		return name

	def performance_plan(self, assignment, ended_days_ago=None, as_user=None):
		"""P6 (on hold, ends in 60 days) or, with `ended_days_ago`, P7 (end date
		passed, no outcome). Made as on the day it was set, then moved back."""
		name = self.make_plan(assignment, as_user=as_user, reason="Performance",
		                      ends=add_days(nowdate(), 60))
		if ended_days_ago is not None:
			frappe.db.set_value(PLAN, name, "improvement_ends_on", add_days(nowdate(), -ended_days_ago),
			                    update_modified=False)
		frappe.db.commit()
		return name

	def age(self, plan, days):
		"""Set a plan's last confirmation `days` ago, as the calendar would."""
		frappe.db.set_value(PLAN, plan, "confirmed_on", add_days(nowdate(), -days), update_modified=False)


# ── US-1 · the record (AC-1, AC-2, AC-4; SEC-5) ───────────────────────────────


class TestTheRecord(Plan065Case):
	def test_ac1_seven_fields_and_no_history(self):
		meta = frappe.get_meta(PLAN)
		own = [(f.fieldname, f.fieldtype) for f in meta.fields]
		self.assertEqual(own, [("assignment", "Data"), ("confirmed_on", "Date"), ("note", "Small Text"),
		                       ("reason", "Select"), ("improvement_ends_on", "Date"),
		                       ("not_improved_on", "Date"), ("not_improved_by", "Data")])
		reason = meta.get_field("reason")
		self.assertTrue(reason.reqd and reason.set_only_once)
		# Blank first, or Frappe would give every plan "Performance" by default.
		self.assertEqual(reason.options.split("\n"),
		                 ["", "Performance", "Personal reasons", "Other business reason"])
		self.assertTrue(meta.get_field("improvement_ends_on").set_only_once)
		a = meta.get_field("assignment")
		self.assertTrue(a.reqd and a.unique and a.set_only_once)
		self.assertTrue(meta.get_field("note").set_only_once)
		for flag in ("track_changes", "track_views", "track_seen", "allow_import", "allow_rename"):
			self.assertFalse(meta.get(flag), flag)
		self.assertEqual(meta.autoname, "hash")
		self.assertFalse(meta.title_field)
		self.assertFalse(meta.has_web_view)
		self.assertFalse(meta.email_append_to)
		self.assertFalse([f.fieldname for f in meta.fields if f.in_global_search])

	def test_ac1_the_assignment_is_not_a_link(self):
		"""A Link would make Frappe's "linked documents" count tell anyone who
		can read the assignment that a plan exists (Surbhi, 22 Oct, Q1)."""
		from frappe.desk.form.linked_with import get_linked_doctypes

		self.assertNotIn(PLAN, get_linked_doctypes("Alvoraa Position Assignment"))

	def test_ac2_shipped_permissions_exactly(self):
		rights = ("read", "write", "create", "delete", "export", "print", "email", "share",
		          "report", "import", "submit", "cancel", "amend")
		got = {r.role: {k for k in rights if r.get(k)}
		       for r in frappe.get_all("DocPerm", filters={"parent": PLAN}, fields=["role", *rights])}
		self.assertEqual(got, {"HR Manager": {"read", "write", "create", "delete"},
		                       "System Manager": {"read"}})

	def test_ac4_the_name_says_nothing_about_the_person(self):
		name = self.make_plan(self.a_sunil)
		for part in (self.sunil, "Sunil", self.cashier.name, self.a_sunil):
			self.assertNotIn(part.lower(), name.lower())

	def test_ac6_a_201_character_note_is_refused_on_the_server(self):
		frappe.set_user(self.hrA)
		with self.assertRaises(frappe.ValidationError):
			insert_plan(self.a_sunil, "x" * 201)
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.count(PLAN))
		self.assertTrue(self.make_plan(self.a_sunil, "y" * 200))

	def test_ac10_confirmed_on_cannot_be_moved(self):
		name = self.make_plan(self.a_sunil)
		frappe.set_user(self.hrA)
		with self.assertRaises(frappe.ValidationError):
			frappe.client.set_value(PLAN, name, "confirmed_on", add_days(nowdate(), 30))
		frappe.set_user("Administrator")
		self.assertEqual(str(frappe.db.get_value(PLAN, name, "confirmed_on")), nowdate())

	def test_the_note_cannot_be_changed_after_saving(self):
		name = self.make_plan(self.a_sunil, "first")
		frappe.set_user(self.hrA)
		with self.assertRaises(frappe.ValidationError):
			frappe.client.set_value(PLAN, name, "note", "second")

	def test_ac78_reason_and_end_date_cannot_be_changed(self):
		p1 = self.make_plan(self.a_sunil, reason="Other business reason")
		p6 = self.performance_plan(self.a_ritu)
		ends = str(frappe.db.get_value(PLAN, p6, "improvement_ends_on"))
		frappe.set_user(self.hrA)
		for name, field, value in ((p1, "reason", "Performance"),
		                           (p6, "improvement_ends_on", str(add_days(nowdate(), 45)))):
			with self.assertRaises(frappe.ValidationError, msg=field):
				frappe.client.set_value(PLAN, name, field, value)
			doc = frappe.client.get(PLAN, name)
			doc[field] = value
			with self.assertRaises(frappe.ValidationError, msg=field):
				frappe.client.save(doc)  # what REST PUT does
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value(PLAN, p1, "reason"), "Other business reason")
		self.assertEqual(str(frappe.db.get_value(PLAN, p6, "improvement_ends_on")), ends)

	def test_ac24_an_ordinary_delete_is_refused_and_leaves_no_copy(self):
		name = self.make_plan(self.a_sunil)
		frappe.set_user(self.hrA)
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc(PLAN, name)
		frappe.set_user("Administrator")
		self.assertTrue(frappe.db.exists(PLAN, name))
		self.assertFalse(frappe.db.exists("Deleted Document", {"deleted_doctype": PLAN}))

	def test_ac9_refused_where_no_plan_may_be_set(self):
		ended = self.assign(self.person("Ended065"), self.cashier.name,
		                    to_date=add_days(nowdate(), -1)).name
		left = self.person("Left065")
		a_left = self.assign(left, self.cashier.name).name
		frappe.db.set_value("Employee", left, {"status": "Left", "relieving_date": add_days(nowdate(), -1)})
		in_closed = self.assign(self.person("InClosed065"), self.cashier.name).name
		frappe.db.set_value("Alvoraa Position Assignment", in_closed, "position", self.closed.name)
		other_co = _second_company()
		seat_b = self.pos("Cashier B 065", seats=1, company=other_co)
		emp_b = frappe.get_doc({"doctype": "Employee", "first_name": "OtherCo065", "company": other_co,
		                        "date_of_birth": "1990-01-01", "date_of_joining": "2020-01-01",
		                        "gender": _gender(), "status": "Active"}).insert(ignore_permissions=True)
		self._people.append(emp_b.name)
		a_b = self.assign(emp_b.name, seat_b.name).name
		frappe.db.commit()

		cases = [(self.hrA, ended), (self.hrA, a_left), (self.hrA, in_closed),
		         (self.hrD, self.a_noida), (self.hrA, a_b), (self.hrSubj, self.a_subj)]
		for user, assignment in cases:
			frappe.set_user(user)
			with self.assertRaises((frappe.ValidationError, frappe.PermissionError), msg=assignment):
				insert_plan(assignment)
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.count(PLAN))


# ── US-12, US-16 · one gate on every door (SEC-1) ─────────────────────────────


def _doors(user, names):
	"""What `user` gets for plans through each door: desk/REST list, count,
	one record by name (permission check and REST read), and link search."""
	from frappe.api.v1 import read_doc
	from frappe.desk.search import search_link

	frappe.set_user(user)
	got = {}
	try:
		got["list"] = {r["name"] for r in frappe.client.get_list(PLAN, fields=["name"], limit_page_length=0)}
		got["count"] = frappe.client.get_count(PLAN)
		got["search"] = {r["value"] for r in search_link(PLAN, "", page_length=50)}
	except frappe.PermissionError:
		got["list"], got["count"], got["search"] = set(), 0, set()
	got["one"] = {n for n in names if frappe.has_permission(PLAN, "read", doc=n)}
	rest = set()
	for n in names:
		try:
			read_doc(PLAN, n)
			rest.add(n)
		except frappe.PermissionError:
			pass
	got["rest"] = rest
	frappe.set_user("Administrator")
	return got


class TestOneGate(Plan065Case):
	def setUp(self):
		super().setUp()
		self.owners_see(True)
		seat_b = self.pos("Cashier B 065", seats=1, company=self.company_b)
		emp_b = frappe.get_doc({"doctype": "Employee", "first_name": "OtherCo065", "company": self.company_b,
		                        "date_of_birth": "1990-01-01", "date_of_joining": "2020-01-01",
		                        "gender": _gender(), "status": "Active"}).insert(ignore_permissions=True)
		self._people.append(emp_b.name)
		self.a_b = self.assign(emp_b.name, seat_b.name).name
		frappe.db.commit()
		self.p1 = self.make_plan(self.a_ritu, "Contract ends 31 Dec.")
		self.p2 = self.make_plan(self.a_noida)
		self.p3 = self.make_plan(self.a_aarti, as_user=self.hrA2)
		self.p4 = self.make_plan(self.a_subj)
		self.p5 = self.make_plan(self.a_b, as_user=self.hrB)
		self.all = {self.p1, self.p2, self.p3, self.p4, self.p5}
		frappe.db.commit()

	def assertSees(self, user, expected):
		got = _doors(user, self.all)
		for door in ("list", "search", "one", "rest"):
			self.assertEqual(got[door], expected, f"{user} through {door}")
		self.assertEqual(got["count"], len(expected), f"{user} count")

	def test_ac52_readers_get_their_company_and_nobody_else_gets_anything(self):
		company_a = {self.p1, self.p2, self.p3, self.p4}
		for user in (self.hrA, self.own):
			self.assertSees(user, company_a)
		# The System Manager stands in for the CXO, whose scope is every
		# company (`permitted_companies`). AC-52 wrote company A only because
		# DTC has one company; 01c's rule is "within _scope()".
		self.assertSees(self.sys, self.all)
		for user in (self.head, self.emp):
			self.assertSees(user, set())

	def test_ac53_a_broad_role_given_read_on_the_table_still_sees_nothing(self):
		"""Written straight to the table, skipping the refusal at the screen."""
		d = frappe.get_doc({"doctype": "Custom DocPerm", "parent": PLAN, "parenttype": "DocType",
		                    "parentfield": "permissions", "role": "Employee", "permlevel": 0, "read": 1})
		d.db_insert()
		frappe.clear_cache(doctype=PLAN)
		frappe.local.role_permissions = {}
		self.assertSees(self.emp, set())

	def test_ac54_leaver_branch_and_company(self):
		self.assertSees(self.hrLeft, set())
		self.assertSees(self.hrD, {self.p1, self.p3, self.p4})  # Delhi seats only
		self.assertSees(self.hrB, {self.p5})

	def test_ac55_print_export_email_share_refused_even_for_hr(self):
		frappe.set_user(self.hrA)
		for ptype in ("print", "export", "email", "share", "report", "import"):
			self.assertFalse(frappe.has_permission(PLAN, ptype, doc=self.p1), ptype)

	def test_ac56_owners_see_nothing_when_the_option_is_off(self):
		self.owners_see(False)
		self.assertSees(self.own, set())

	def test_ac64_the_subject_never_sees_their_own_plan(self):
		self.assertSees(self.hrSubj, {self.p1, self.p2, self.p3})

	def test_linked_documents_never_mention_a_plan(self):
		"""Frappe's "Links" count reads with no permission check; a Link field
		would tell the subject "1 hidden" (question 1, check B-5)."""
		from frappe.desk.form.linked_with import get as linked

		frappe.set_user(self.hrSubj)
		self.assertNotIn(PLAN, linked("Alvoraa Position Assignment", self.a_subj))

	def test_ac46_a_lapsed_plan_or_a_leavers_plan_is_hidden_before_any_job_runs(self):
		self.age(self.p1, 91)
		frappe.db.set_value("Employee", self.noida_person, {"status": "Left", "relieving_date": add_days(nowdate(), -1)})
		frappe.db.set_value("Alvoraa Position Assignment", self.a_aarti, "to_date", add_days(nowdate(), -1))
		frappe.db.commit()
		self.assertSees(self.hrA, {self.p4})
		self.age(self.p4, 90)  # day 90 is still shown
		self.assertSees(self.hrA, {self.p4})


# ── US-14 · no side doors (SEC-3) ─────────────────────────────────────────────


class TestNoSideDoors(Plan065Case):
	def setUp(self):
		super().setUp()
		self.owners_see(True)
		self.p1 = self.make_plan(self.a_ritu, "Contract ends 31 Dec.")
		frappe.db.commit()
		self.mail_before = frappe.db.count("Email Queue")

	def counts(self):
		return {
			"Comment": frappe.db.count("Comment", {"reference_doctype": PLAN}),
			"ToDo": frappe.db.count("ToDo", {"reference_type": PLAN}),
			"DocShare": frappe.db.count("DocShare", {"share_doctype": PLAN}),
			"Tag Link": frappe.db.count("Tag Link", {"document_type": PLAN}),
			"Tag": frappe.db.count("Tag", {"name": "Ritu resigning 065"}),
			"File": frappe.db.count("File", {"attached_to_doctype": PLAN}),
			"Document Follow": frappe.db.count("Document Follow", {"ref_doctype": PLAN}),
			"Email Queue": frappe.db.count("Email Queue") - self.mail_before,
		}

	def test_ac62_comment_assign_share_tag_file_and_follow_are_all_refused(self):
		from frappe.desk.doctype.tag.tag import add_tag
		from frappe.desk.form import assign_to
		from frappe.desk.form.document_follow import follow_document
		from frappe.desk.form.utils import add_comment

		for user in (self.hrA, self.own):
			frappe.set_user(user)
			attempts = {
				"comment": lambda: add_comment(PLAN, self.p1, "@head fyi", user, user),
				"assign": lambda: assign_to.add({"doctype": PLAN, "name": self.p1, "assign_to": [self.head]}),
				"share": lambda: frappe.share.add(PLAN, self.p1, self.head, read=1),
				"tag": lambda: add_tag("Ritu resigning 065", PLAN, self.p1),
				"file": lambda: frappe.get_doc({"doctype": "File", "file_name": "note065.txt", "content": "x",
				                                "attached_to_doctype": PLAN, "attached_to_name": self.p1,
				                                "is_private": 1}).insert(),
			}
			for what, attempt in attempts.items():
				with self.assertRaises((frappe.ValidationError, frappe.PermissionError), msg=f"{user} {what}"):
					attempt()
				frappe.db.rollback()
			self.assertFalse(follow_document(PLAN, self.p1))
		frappe.set_user("Administrator")
		self.assertEqual(set(self.counts().values()), {0}, self.counts())

	def test_a_normal_comment_still_saves(self):
		"""The hook sits on every comment, share, tag and upload in the
		system. It must refuse plans and nothing else."""
		frappe.set_user("Administrator")
		c = frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": "Employee",
		                    "reference_name": self.ritu, "content": "hello 065"}).insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Comment", c.name))
		frappe.delete_doc("Comment", c.name, ignore_permissions=True, delete_permanently=True)


# ── US-15 · careless grants refused, chosen ones recorded (SEC-2) ─────────────


class TestCarelessGrants(Plan065Case):
	def test_ac63_broad_roles_and_print_export_ticks_are_refused(self):
		from frappe.core.page.permission_manager import permission_manager as pm

		frappe.set_user(self.sys)
		for role in ("Employee", "All", "Guest", "Desk User"):
			with self.assertRaises(frappe.ValidationError, msg=role):
				pm.add(PLAN, role, 0)
			frappe.db.rollback()
			self.assertFalse(frappe.db.exists("Custom DocPerm", {"parent": PLAN, "role": role}))
		for right in ("export", "print", "email", "share", "report", "import"):
			with self.assertRaises(frappe.ValidationError, msg=right):
				pm.update(PLAN, "HR Manager", 0, right, 1)
			frappe.db.rollback()

	def test_ac63_owners_read_is_allowed_and_recorded(self):
		from frappe.core.page.permission_manager import permission_manager as pm

		frappe.set_user(self.sys)
		pm.add(PLAN, OWNERS, 0)
		frappe.set_user("Administrator")
		row = frappe.db.get_value("Custom DocPerm", {"parent": PLAN, "role": OWNERS},
		                          ["read", "export", "print", "email", "share", "report"], as_dict=True)
		# Frappe ticks print/email/export/share/report on a new row; they are unticked.
		self.assertEqual(row, {"read": 1, "export": 0, "print": 0, "email": 0, "share": 0, "report": 0})
		trail = " ".join(frappe.get_all("Version", filters={"ref_doctype": "DocType", "docname": PLAN},
		                                pluck="data"))
		self.assertIn(OWNERS, trail)


# ── US-2, US-4, US-5, US-17 · set, confirm, remove; the one erase (SEC-5, PRIV-2) ──


def _traces(name, tag=None):
	"""Every table a plan could leave a trace in: the 12 the spec names, plus
	the tag list itself (the 13th; tags are refused, so it never holds a
	plan's tag)."""
	return {
		"Replacement Plan": frappe.db.count(PLAN, {"name": name}),
		"Deleted Document": frappe.db.count("Deleted Document", {"deleted_doctype": PLAN, "deleted_name": name}),
		"Version": frappe.db.count("Version", {"ref_doctype": PLAN, "docname": name}),
		"Comment": frappe.db.count("Comment", {"reference_doctype": PLAN, "reference_name": name}),
		"DocShare": frappe.db.count("DocShare", {"share_doctype": PLAN, "share_name": name}),
		"ToDo": frappe.db.count("ToDo", {"reference_type": PLAN, "reference_name": name}),
		"View Log": frappe.db.count("View Log", {"reference_doctype": PLAN, "reference_name": name}),
		"Document Follow": frappe.db.count("Document Follow", {"ref_doctype": PLAN, "ref_docname": name}),
		"Notification Log": frappe.db.count("Notification Log", {"document_type": PLAN, "document_name": name}),
		"Tag Link": frappe.db.count("Tag Link", {"document_type": PLAN, "document_name": name}),
		"File": frappe.db.count("File", {"attached_to_doctype": PLAN, "attached_to_name": name}),
		"__global_search": frappe.db.sql("select count(*) from `__global_search` where doctype=%s and name=%s",
		                                 (PLAN, name))[0][0],
		"Tag": frappe.db.count("Tag", {"name": tag}) if tag else 0,
	}


class TestSetConfirmRemove(Plan065Case):
	def setUp(self):
		super().setUp()
		self.owners_see(True)

	def call(self, user, fn, *args):
		frappe.set_user(user)
		try:
			return fn(*args)
		finally:
			frappe.set_user("Administrator")

	def test_ac10_the_three_calls_take_post_only(self):
		for fn in (plans.set_plan, plans.confirm_plan, plans.remove_plan, plans.record_outcome):
			self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func.get(fn), ["POST"], fn.__name__)

	def test_ac7_set_and_ac3_no_history_anywhere(self):
		got = self.call(self.hrA, plans.set_plan, self.a_sunil, "Notice likely in December", "Personal reasons")
		self.assertEqual(got["confirmed_on"], nowdate())
		self.assertEqual(got["lapses_on"], str(add_days(nowdate(), 90)))
		self.assertEqual(frappe.db.get_value(PLAN, got["name"], "owner"), self.hrA)
		self.call(self.hrA2, plans.confirm_plan, got["name"])
		t = _traces(got["name"])
		self.assertEqual((t["Version"], t["View Log"], t["__global_search"]), (0, 0, 0))

	def test_ac9_two_hr_managers_saving_at_once_make_one_plan(self):
		self.call(self.hrA, plans.set_plan, self.a_sunil, None, "Personal reasons")
		with self.assertRaises(frappe.ValidationError) as caught:
			self.call(self.hrA2, plans.set_plan, self.a_sunil, None, "Personal reasons")
		self.assertIn("Someone else changed this plan", str(caught.exception))
		self.assertEqual(frappe.db.count(PLAN, {"assignment": self.a_sunil}), 1)

	def test_ac11_a_lapsed_plan_waiting_for_the_job_is_replaced_cleanly(self):
		old = self.make_plan(self.a_aarti)
		self.age(old, 91)
		new = self.call(self.hrA, plans.set_plan, self.a_aarti, None, "Personal reasons")["name"]
		self.assertEqual(frappe.get_all(PLAN, filters={"assignment": self.a_aarti}, pluck="name"), [new])
		self.assertEqual(str(frappe.db.get_value(PLAN, new, "confirmed_on")), nowdate())
		self.assertEqual(set(_traces(old).values()), {0})

	def test_ac18_confirm_moves_the_end_to_ninety_days_from_today(self):
		p = self.make_plan(self.a_ritu)
		self.age(p, 20)
		got = self.call(self.hrA2, plans.confirm_plan, p)
		self.assertEqual(got["lapses_on"], str(add_days(nowdate(), 90)))
		self.assertEqual(frappe.db.get_value(PLAN, p, "modified_by"), self.hrA2)

	def test_ac20_confirm_after_the_plan_lapsed_is_refused(self):
		p = self.make_plan(self.a_aarti)
		self.age(p, 91)
		with self.assertRaises(frappe.ValidationError) as caught:
			self.call(self.hrA, plans.confirm_plan, p)
		self.assertIn("Someone else changed this plan", str(caught.exception))
		self.assertEqual(str(frappe.db.get_value(PLAN, p, "confirmed_on")), str(add_days(nowdate(), -91)))

	def test_ac23_remove_leaves_nothing_in_any_of_the_13_places(self):
		"""Side records are seeded through Frappe's own paths with the refusal
		switched off, and Frappe's after-commit cleanup job switched off too,
		so the test cannot lean on a worker (PRIV-2)."""
		from frappe.desk.doctype.tag.tag import add_tag
		from frappe.desk.form import assign_to
		from frappe.desk.form.utils import add_comment

		p = self.make_plan(self.a_ritu, "Contract ends 31 Dec.")
		with patch("hrms.alvoraa_org_structure.plans.refuse_side_record"):
			frappe.set_user(self.hrA)
			add_comment(PLAN, p, "a comment", self.hrA, self.hrA)
			add_tag("tag065", PLAN, p)
			frappe.get_doc({"doctype": "File", "file_name": "n065.txt", "content": "x", "is_private": 1,
			                "attached_to_doctype": PLAN, "attached_to_name": p}).insert()
			frappe.set_user("Administrator")
			# Nobody may share a plan, and assigning shares it, so both as
			# Administrator: the gate refuses "share" to everybody else.
			frappe.share.add(PLAN, p, self.own, read=1)
			assign_to.add({"doctype": PLAN, "name": p, "assign_to": [self.hrA2]})
			for dt, row in (("Version", {"ref_doctype": PLAN, "docname": p, "data": "{}"}),
			                ("View Log", {"reference_doctype": PLAN, "reference_name": p, "viewed_by": self.hrA}),
			                ("Document Follow", {"ref_doctype": PLAN, "ref_docname": p, "user": self.hrA}),
			                ("Notification Log", {"document_type": PLAN, "document_name": p, "for_user": self.hrA,
			                                      "subject": "x"})):
				frappe.get_doc({"doctype": dt, **row}).db_insert()
			frappe.db.sql("insert into `__global_search` (doctype, name, content) values (%s, %s, 'x')", (PLAN, p))
		seeded = _traces(p)
		self.assertTrue(all(seeded[k] for k in seeded if k not in ("Deleted Document", "Tag")), seeded)

		with patch("frappe.enqueue"):
			self.call(self.hrA, plans.remove_plan, p)
		self.assertEqual(set(_traces(p).values()), {0}, _traces(p))
		frappe.db.delete("Tag", {"name": "tag065"})

	def test_ac23_the_test_can_fail_an_ordinary_delete_leaves_a_copy(self):
		"""Proves the trace check sees a Deleted Document copy: the same
		delete without `delete_permanently` leaves one."""
		p = self.make_plan(self.a_ritu)
		frappe.delete_doc(PLAN, p, flags={plans.ERASE_FLAG: True})
		self.assertEqual(_traces(p)["Deleted Document"], 1)
		frappe.db.delete("Deleted Document", {"deleted_doctype": PLAN})

	def test_ac24_rest_delete_is_refused(self):
		p = self.make_plan(self.a_ritu)
		frappe.set_user(self.hrA)
		with self.assertRaises(frappe.ValidationError):
			frappe.client.delete(PLAN, p)
		frappe.set_user("Administrator")
		self.assertTrue(frappe.db.exists(PLAN, p))

	def test_ac26_ac41_the_opening_carries_nothing_and_outlives_the_plan(self):
		p = self.make_plan(self.a_ritu, "Contract ends 31 Dec.", reason="Other business reason")
		frappe.set_user(self.hrA)
		opening = register.post_job(self.cashier.name, vacancies=1, publish=0)["name"]
		frappe.set_user("Administrator")
		before = frappe.get_doc("Job Opening", opening).as_dict()
		text = json.dumps(list(before.values()), default=str).lower()
		for bad in ("ritu", self.ritu.lower(), "contract ends", p.lower(), "other business reason",
		            "improvement"):
			self.assertNotIn(bad, text)
		words = " ".join(str(before.get(f) or "") for f in ("job_title", "route", "description")).lower()
		self.assertNotIn("replac", words)
		self.assertNotIn("planned", words)
		self.assertEqual(before.publish, 0)
		self.call(self.hrA, plans.remove_plan, p)
		after = frappe.get_doc("Job Opening", opening).as_dict()
		self.assertEqual({k: v for k, v in before.items() if k != "modified"},
		                 {k: v for k, v in after.items() if k != "modified"})
		frappe.delete_doc("Job Opening", opening, force=True, ignore_permissions=True, delete_permanently=True)

	def test_ac66_owners_and_the_system_manager_only_read(self):
		p = self.make_plan(self.a_ritu)
		for user in (self.own, self.sys):
			with self.assertRaises(frappe.PermissionError, msg=user):
				self.call(user, plans.set_plan, self.a_sunil, None, "Personal reasons")
			with self.assertRaises(frappe.PermissionError, msg=user):
				self.call(user, plans.confirm_plan, p)
			with self.assertRaises(frappe.PermissionError, msg=user):
				self.call(user, plans.remove_plan, p)
			frappe.set_user(user)
			with self.assertRaises(frappe.PermissionError, msg=user):
				frappe.client.insert({"doctype": PLAN, "assignment": self.a_sunil})
			with self.assertRaises(frappe.PermissionError, msg=user):
				frappe.client.delete(PLAN, p)
			frappe.set_user("Administrator")
		self.assertTrue(frappe.db.exists(PLAN, p))
		self.assertFalse(frappe.db.exists(PLAN, {"assignment": self.a_sunil}))

	def test_ac51_log_lines_name_nobody(self):
		lines = []

		class Capture:
			def warning(self, message):
				lines.append(json.loads(message))

		with patch("frappe.logger", return_value=Capture()):
			p = self.call(self.hrA, plans.set_plan, self.a_ritu, "Contract ends 31 Dec.", "Personal reasons")["name"]
			self.call(self.hrA, plans.confirm_plan, p)
			self.call(self.hrA, plans.remove_plan, p)
			# AC-92: "Not improved" is one line, and no line carries the reason.
			p7 = self.performance_plan(self.a_sunil, ended_days_ago=0)
			self.call(self.hrA, plans.record_outcome, p7, "not_improved")
		mine = [line for line in lines if line.get("event") == "replacement_plan"]
		self.assertEqual([line["reason"] for line in mine], ["set", "confirmed", "removed", "outcome recorded"])
		self.assertEqual(mine[-1]["name"], p7)
		for line in mine:
			self.assertEqual(set(line), {"event", "at", "user", "doctype", "name", "reason"})
		text = json.dumps(lines).lower()
		for bad in ("ritu", self.ritu.lower(), self.a_ritu.lower(), self.cashier.name.lower(), "contract",
		            "sunil", self.sunil.lower(), "performance", "personal reasons"):
			self.assertNotIn(bad, text)


# ── US-10, US-19, US-21 · plans end by themselves; restore step (PRIV-3, PRIV-6) ──


class TestTheDailyErase(Plan065Case):
	def setUp(self):
		super().setUp()
		frappe.db.delete("Error Log", {"method": ("in", (plans.ERASE_FAILED, plans.CHECK_FAILED))})
		x1, x2 = self.person("Extra1065"), self.person("Extra2065")
		self.a_x1 = self.assign(x1, self.cashier.name).name
		self.a_x2 = self.assign(x2, self.cashier.name).name
		gone = self.person("Gone065")
		self.a_gone = self.assign(gone, self.rso.name).name
		frappe.db.commit()
		mk = self.make_plan
		self.p = {
			"a_91_days": mk(self.a_ritu), "b_89_days": mk(self.a_sunil), "c_confirmed_yesterday": mk(self.a_x1),
			"d_ended": mk(self.a_x2), "e_left": mk(self.a_noida), "f_closed": mk(self.a_aarti),
			"g_deleted": mk(self.a_gone),
		}
		self.age(self.p["a_91_days"], 91)
		self.age(self.p["b_89_days"], 89)
		self.age(self.p["c_confirmed_yesterday"], 1)
		frappe.db.set_value("Alvoraa Position Assignment", self.a_x2, "to_date", add_days(nowdate(), -1))
		frappe.db.set_value("Employee", self.noida_person, {"status": "Left", "relieving_date": add_days(nowdate(), -1)})
		frappe.db.set_value("Alvoraa Position", self.recruiter.name, "status", "Closed")
		frappe.db.delete("Alvoraa Position Assignment", {"name": self.a_gone})
		frappe.db.commit()
		self.due = {k for k in self.p if k[0] in "adefg"}

	def errors(self, title):
		return frappe.get_all("Error Log", filters={"method": title}, fields=["error"])

	def test_ac46_due_plans_are_erased_and_live_ones_kept(self):
		lines = []

		class Capture:
			def warning(self, message):
				lines.append(json.loads(message))

		with patch("frappe.enqueue"), patch("frappe.logger", return_value=Capture()):
			plans.erase_due_plans()
		for key, name in self.p.items():
			if key in self.due:
				self.assertEqual(set(_traces(name).values()), {0}, key)
			else:
				self.assertTrue(frappe.db.exists(PLAN, name), key)
		reasons = sorted(line["reason"] for line in lines if line.get("event") == "replacement_plan")
		self.assertEqual(reasons, ["lapsed", "left company", "left seat", "left seat", "seat closed"])
		self.assertFalse(self.errors(plans.CHECK_FAILED))

	def test_ac47_one_failure_does_not_stop_the_rest_and_logs_the_plan_name_only(self):
		bad = self.p["a_91_days"]
		real = plans.erase

		def erase(name, reason):
			if name == bad:
				raise RuntimeError("Ritu065 note text")
			return real(name, reason)

		with patch("hrms.alvoraa_org_structure.plans.erase", side_effect=erase):
			plans.erase_due_plans()
		for key in self.due - {"a_91_days"}:
			self.assertFalse(frappe.db.exists(PLAN, self.p[key]), key)
		self.assertTrue(frappe.db.exists(PLAN, bad))
		failed = self.errors(plans.ERASE_FAILED)
		self.assertEqual([e.error for e in failed], [f"Plan {bad}"])
		# The plan still due after the run raises the self-check alert too.
		self.assertEqual(len(self.errors(plans.CHECK_FAILED)), 1)

	def test_ac48_a_stray_copy_raises_the_self_check_with_counts_only(self):
		frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": PLAN,
		                "reference_name": "orphan065", "content": "Ritu065"}).db_insert()
		plans.erase_due_plans()
		alerts = self.errors(plans.CHECK_FAILED)
		self.assertEqual(len(alerts), 1)
		self.assertEqual(json.loads(alerts[0].error), {"Comment": 1})
		frappe.db.delete("Comment", {"reference_doctype": PLAN})

	def test_ac49_one_daily_line_and_never_the_long_cover_alert(self):
		events = frappe.get_hooks("scheduler_events")
		self.assertIn("hrms.alvoraa_org_structure.plans.erase_due_plans", events.get("daily", []))
		every = json.dumps(events)
		self.assertNotIn("alert_on_long_cover", every)

	def test_ac50_the_release_check_counts_zero_after_the_job(self):
		plans.erase_due_plans()
		self.assertEqual(set(plans.self_check().values()), {0})

	def test_ac50_the_release_check_sees_an_overdue_plan(self):
		"""The positive control: a plan 93 days past its confirmation, which
		the job has not erased, is counted."""
		self.age(self.p["b_89_days"], 93)
		self.assertGreaterEqual(plans.self_check()["plans past their end"], 1)

	def test_ac71_erase_all_after_a_restore(self):
		with patch("frappe.enqueue"):
			got = plans.erase_all_plans()
		self.assertEqual(got, {"erased": len(self.p), "left": 0})
		for name in self.p.values():
			self.assertEqual(set(_traces(name).values()), {0})


# ── US-13, US-3, US-16 · the Positions reply (SEC-4) ──────────────────────────


class TestTheChartReply(Plan065Case):
	def setUp(self):
		super().setUp()
		self.owners_see(True)

	def reply(self, user, **kw):
		frappe.set_user(user)
		register.position_table(**kw)  # warm the caches, as a second page load would be
		out = register.position_table(**kw)
		frappe.set_user("Administrator")
		return out

	def person_row(self, out, assignment):
		return next(p for r in out["rows"] for p in r["people"] if p["assignment"] == assignment)

	def seat_row(self, out, seat):
		return next(r for r in out["rows"] if r["id"] == seat)

	def test_ac57_non_readers_get_the_same_bytes_with_and_without_plans(self):
		"""Including a full one-person seat with a replacement opening, whose
		link a non-reader no longer receives (SEC-4.3)."""
		frappe.set_user(self.hrA)
		opening = register.post_job(self.recruiter.name, vacancies=1, publish=0)["name"]
		frappe.set_user("Administrator")
		self.owners_see(False)
		self.make_plan(self.a_ritu, "Contract ends 31 Dec.")
		self.make_plan(self.a_noida)
		self.make_plan(self.a_aarti)
		self.performance_plan(self.a_sunil)                   # P6, on hold
		self.performance_plan(self.a_subj, ended_days_ago=3)  # P7, outcome due
		with_plans = {u: frappe.as_json(self.reply(u)) for u in (self.head, self.own)}
		frappe.db.delete(PLAN)
		for user, before in with_plans.items():
			self.assertEqual(before, frappe.as_json(self.reply(user)), user)
			self.assertNotIn("plan", before.lower().replace("planned_vacancies", ""))
			for word in ("Performance", "Personal reasons", "Other business reason", "improvement", "on hold"):
				self.assertNotIn(word, before, user)
		self.assertIsNone(self.seat_row(self.reply(self.head), self.recruiter.name)["opening"])
		self.assertEqual(self.seat_row(self.reply(self.hrA), self.recruiter.name)["opening"], opening)
		frappe.delete_doc("Job Opening", opening, force=True, ignore_permissions=True, delete_permanently=True)

	def test_ac58_readers_get_the_head_key_and_exactly_the_named_plan_keys(self):
		out = self.reply(self.hrA)
		self.assertEqual(out["plans"], {"may_set": True, "owners_see": True})  # even with no plan
		self.make_plan(self.a_ritu, "Contract ends 31 Dec.")
		out = self.reply(self.hrA)
		# The literal list, not PLAN_KEYS, so a key added later cannot slip in.
		self.assertEqual(tuple(self.person_row(out, self.a_ritu)["plan"]), (
			"name", "set_on", "set_by", "confirmed_by", "confirmed_on", "lapses_on", "note",
			"reason", "improvement_ends_on", "not_improved_on", "not_improved_by"))
		self.assertNotIn("plan", self.person_row(out, self.a_sunil))
		for user in (self.own, self.sys):
			self.assertEqual(self.reply(user)["plans"]["may_set"], False, user)
		self.owners_see(False)
		self.assertEqual(self.reply(self.hrA)["plans"]["owners_see"], False)

	def test_ac12_ac13_who_set_and_confirmed_it(self):
		p = self.make_plan(self.a_ritu, "Contract ends 31 Dec.", reason="Other business reason")
		plan = self.person_row(self.reply(self.hrA), self.a_ritu)["plan"]
		self.assertEqual((plan["set_by"], plan["confirmed_by"], plan["note"], plan["reason"]),
		                 ("you", None, "Contract ends 31 Dec.", "Other business reason"))
		self.assertEqual((plan["improvement_ends_on"], plan["not_improved_on"], plan["not_improved_by"]),
		                 (None, None, None))
		self.assertEqual(plan["lapses_on"], str(add_days(nowdate(), 90)))
		# Confirmed later by somebody else: set a day back, confirm today.
		frappe.db.set_value(PLAN, p, {"creation": add_days(nowdate(), -5), "confirmed_on": add_days(nowdate(), -5)},
		                    update_modified=False)
		frappe.set_user(self.hrA2)
		plans.confirm_plan(p)
		frappe.set_user("Administrator")
		plan = self.person_row(self.reply(self.hrA), self.a_ritu)["plan"]
		hr_a2 = frappe.db.get_value("User", self.hrA2, "full_name")
		self.assertEqual((plan["set_by"], plan["confirmed_by"]), ("you", f"{hr_a2} (HR Manager)"))
		self.assertNotIn("@", json.dumps(plan))
		# Who recorded "Not improved", written the same way.
		p7 = self.performance_plan(self.a_sunil, ended_days_ago=1)
		frappe.set_user(self.hrA2)
		plans.record_outcome(p7, "not_improved")
		frappe.set_user("Administrator")
		plan = self.person_row(self.reply(self.hrA), self.a_sunil)["plan"]
		self.assertEqual((plan["reason"], plan["not_improved_on"], plan["not_improved_by"]),
		                 ("Performance", nowdate(), f"{hr_a2} (HR Manager)"))
		self.assertEqual(self.person_row(self.reply(self.hrA2), self.a_sunil)["plan"]["not_improved_by"], "you")
		self.assertNotIn("@", json.dumps(plan))

	def test_ac59_only_for_today(self):
		self.make_plan(self.a_ritu)
		for as_at in (add_days(nowdate(), 1), add_days(nowdate(), -30)):
			out = self.reply(self.hrA, as_at=str(as_at))
			self.assertNotIn("plans", out)
			self.assertNotIn('"plan"', frappe.as_json(out))

	def test_ac64_ac65_the_subjects_own_row_is_the_same_with_and_without_their_plan(self):
		self.make_plan(self.a_ritu)
		before = self.person_row(self.reply(self.hrSubj), self.a_subj)
		self.make_plan(self.a_subj)
		out = self.reply(self.hrSubj)
		self.assertEqual(self.person_row(out, self.a_subj), before)
		self.assertIn("plan", self.person_row(out, self.a_ritu))

	def test_the_query_count_is_the_same_for_one_plan_or_four(self):
		from alvoraa_portal.tests.leader_fixtures_012 import QueryCounter

		self.make_plan(self.a_ritu)
		counts = {}
		for label in ("one", "four"):
			if label == "four":
				for a in (self.a_sunil, self.a_noida, self.a_aarti):
					self.make_plan(a, "a note")
			for user in (self.hrA, self.head):
				frappe.set_user(user)
				register.position_table()
				with QueryCounter() as c:
					register.position_table()
				counts[(label, user)] = c.count
				frappe.set_user("Administrator")
		print(f"\nposition_table statements with plans: {counts}")
		self.assertEqual(counts[("one", self.hrA)], counts[("four", self.hrA)])
		self.assertEqual(counts[("one", self.head)], counts[("four", self.head)])


# ── US-18 · plans are read in one place only (SEC-7, PRIV-5) ──────────────────


def _offenders():
	"""Every Python, JS or JSON file in our three apps that names the plan
	doctype, outside the places allowed to: its own module and folder,
	register.py (one call, one name), hooks.py, and tests."""
	allowed = (
		os.path.join("alvoraa_org_structure", "plans.py"),
		os.path.join("alvoraa_org_structure", "register.py"),
		os.path.join("alvoraa_org_structure", "doctype", "replacement_plan") + os.sep,
		os.path.join("hrms", "hooks.py"),
	)
	found = []
	for app in ("hrms", "alvoraa_portal", "alvoraa_goals"):
		root = frappe.get_app_path(app)
		for folder, dirs, files in os.walk(root):
			dirs[:] = [d for d in dirs if d not in ("node_modules", "__pycache__", "tests", "dist")]
			for f in files:
				if not f.endswith((".py", ".js", ".json")):
					continue
				path = os.path.join(folder, f)
				if any(a in path for a in allowed):
					continue
				with open(path, encoding="utf-8", errors="ignore") as fh:
					if PLAN in fh.read():
						found.append(os.path.relpath(path, root))
	return found


class TestReadInOnePlace(Plan065Case):
	def test_ac67_nothing_else_names_the_plan_doctype(self):
		self.assertEqual(_offenders(), [])

	def test_ac67_the_check_catches_a_new_reader(self):
		"""The positive control: a fixture file naming the doctype dropped into
		alvoraa_portal is caught."""
		path = os.path.join(frappe.get_app_path("alvoraa_portal"), "zz_plan_reader_065.json")
		with open(path, "w", encoding="utf-8") as fh:
			fh.write(json.dumps([{"doctype": "Report", "ref_doctype": PLAN}]))
		try:
			self.assertEqual(_offenders(), ["zz_plan_reader_065.json"])
		finally:
			os.remove(path)

	def test_ac68_setting_confirming_and_removing_sends_nothing(self):
		mail, bell = frappe.db.count("Email Queue"), frappe.db.count("Notification Log")
		frappe.set_user(self.hrA)
		p = plans.set_plan(self.a_ritu, "Contract ends 31 Dec.", "Personal reasons")["name"]
		plans.confirm_plan(p)
		plans.remove_plan(p)
		frappe.set_user("Administrator")
		self.assertEqual((frappe.db.count("Email Queue"), frappe.db.count("Notification Log")), (mail, bell))
		for doctype, field in plans.READER_TABLES:
			self.assertFalse(frappe.db.count(doctype, {field: PLAN}), doctype)


# ── Option A · reason, improvement period, outcome, hiring hold (US-23..US-26) ──


class TestOptionA(Plan065Case):
	"""Spec v3 §22 and SEC-5 Rev 3. P6: a Performance plan on hold. P7: one
	whose improvement period has ended with no outcome."""

	def setUp(self):
		super().setUp()
		self.owners_see(True)
		# The System Manager may edit seats here, so AC-80 can show the hold
		# refusing them - not the seat permission.
		self.rows(("HR Manager", "write"), ("System Manager", "write"), (OWNERS, "write"),
		          ("Projects User", "read"))
		self.store = self.pos("Store Executive 065", seats=1, branch=self.noida,
		                      designation=self._role_name())
		self.karan = self._emp_of(self.emp)  # empK: his own login has the Employee role only
		self.a_karan = self.assign(self.karan, self.store.name).name
		# Owners who may make a job opening, so AC-80 and AC-84 (a) test the
		# hold and not Job Opening's own permission. Added beside the shipped
		# rows, not instead of them.
		d = frappe.get_doc({"doctype": "DocPerm", "parent": "Job Opening", "parenttype": "DocType",
		                    "parentfield": "permissions", "role": OWNERS, "permlevel": 0, "read": 1,
		                    "write": 1, "create": 1, "idx": 99})
		d.db_insert()
		frappe.clear_cache(doctype="Job Opening")
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in frappe.get_all("Job Opening", filters={
				register.POSITION_LINK: ("in", [self.store.name, self.cashier.name, self.hr_head.name])},
				pluck="name"):
			frappe.delete_doc("Job Opening", name, force=True, ignore_permissions=True, delete_permanently=True)
		frappe.db.delete("DocPerm", {"parent": "Job Opening", "role": OWNERS})
		# empK's Employee lives for the whole file; AC-84 (c) gives it a leaving date.
		frappe.db.set_value("Employee", self.karan, "relieving_date", None)
		frappe.clear_cache(doctype="Job Opening")
		frappe.db.commit()
		super().tearDown()

	def as_user(self, user, fn, *args, **kw):
		frappe.set_user(user)
		try:
			return fn(*args, **kw)
		finally:
			frappe.set_user("Administrator")

	def openings(self, seat):
		return frappe.db.count("Job Opening", {register.POSITION_LINK: seat})

	def assertHeld(self, user, seat):
		with self.assertRaises(frappe.ValidationError, msg=user) as caught:
			self.as_user(user, register.post_job, seat, vacancies=1, publish=0)
		self.assertIn("Hiring for this seat is on hold", str(caught.exception))
		frappe.db.rollback()
		self.assertEqual(self.openings(seat), 0, user)

	# US-23 · reason

	def test_ac76_a_reason_is_required_and_must_be_one_of_three(self):
		for reason in (None, "", "Attitude"):
			with self.assertRaises(frappe.ValidationError, msg=repr(reason)):
				self.as_user(self.hrA, plans.set_plan, self.a_sunil, None, reason)
			frappe.set_user(self.hrA)
			with self.assertRaises(frappe.ValidationError, msg=repr(reason)):
				frappe.client.insert({"doctype": PLAN, "assignment": self.a_sunil, "reason": reason})
			frappe.set_user("Administrator")
		self.assertFalse(frappe.db.count(PLAN))

	def test_ac77_readers_get_the_reason(self):
		self.make_plan(self.a_ritu, reason="Other business reason")
		for user in (self.hrA, self.own, self.sys):
			out = self.as_user(user, register.position_table)
			plan = next(p for r in out["rows"] for p in r["people"] if p["assignment"] == self.a_ritu)["plan"]
			self.assertEqual(plan["reason"], "Other business reason", user)

	# US-24 · improvement period and hold

	def test_ac79_the_end_date_is_30_to_60_days_out_and_performance_only(self):
		for days in (29, 61, None):
			ends = add_days(nowdate(), days) if days else None
			with self.assertRaises(frappe.ValidationError, msg=days):
				self.as_user(self.hrA, plans.set_plan, self.a_sunil, None, "Performance", ends, 1)
		with self.assertRaises(frappe.ValidationError):
			self.as_user(self.hrA, plans.set_plan, self.a_sunil, None, "Personal reasons",
			             add_days(nowdate(), 40))
		self.assertFalse(frappe.db.count(PLAN))
		for days in (30, 60):
			ends = str(add_days(nowdate(), days))
			name = self.as_user(self.hrA, plans.set_plan, self.a_sunil, None, "Performance", ends, 1)["name"]
			self.assertEqual(str(frappe.db.get_value(PLAN, name, "improvement_ends_on")), ends)
			_wipe_plans()

	def test_ac81_performance_needs_the_told_tick(self):
		ends = add_days(nowdate(), 45)
		for told in (0, None, "0"):
			with self.assertRaises(frappe.ValidationError, msg=repr(told)):
				self.as_user(self.hrA, plans.set_plan, self.a_sunil, None, "Performance", ends, told)
		self.assertFalse(frappe.db.count(PLAN))
		self.as_user(self.hrA, plans.set_plan, self.a_sunil, None, "Performance", ends, 1)
		self.assertEqual(frappe.db.count(PLAN), 1)
		self.assertNotIn("told", frappe.get_meta(PLAN).get_valid_columns())

	def test_ac80_ac83_post_job_is_held_for_plan_readers_until_the_outcome(self):
		p6 = self.performance_plan(self.a_karan)
		for user in (self.hrA, self.own, self.sys):
			self.assertHeld(user, self.store.name)
		# AC-83: still held on the end date itself, while no outcome is recorded.
		frappe.db.set_value(PLAN, p6, "improvement_ends_on", nowdate(), update_modified=False)
		frappe.db.commit()
		self.assertHeld(self.hrA, self.store.name)

	def test_the_desk_job_opening_form_is_held_too(self):
		"""Surbhi's one extra check: a Job Opening made on the desk or by REST
		and pointed at the held seat is refused for a plan reader. One with no
		seat link is not checked - a stated limit."""
		self.performance_plan(self.a_karan)
		frappe.set_user(self.hrA)
		row = {"doctype": "Job Opening", "job_title": "Store Executive 065", "designation": self._role_name(),
		       "company": self.store.company, "status": "Open", "publish": 0,
		       "route": "jobs/test065/held-" + frappe.generate_hash(length=6)}
		with self.assertRaises(frappe.ValidationError) as caught:
			frappe.client.insert({**row, register.POSITION_LINK: self.store.name})
		self.assertIn("Hiring for this seat is on hold", str(caught.exception))
		frappe.db.rollback()
		self.assertEqual(self.openings(self.store.name), 0)
		unlinked = frappe.client.insert(row)["name"]
		frappe.set_user("Administrator")
		frappe.delete_doc("Job Opening", unlinked, force=True, ignore_permissions=True, delete_permanently=True)

	def test_ac84a_a_non_reader_is_never_held_and_sees_the_same_with_and_without_p6(self):
		self.owners_see(False)
		without = self.as_user(self.own, register.post_job, self.store.name)
		without["name"] = None
		frappe.set_user("Administrator")
		for name in frappe.get_all("Job Opening", filters={register.POSITION_LINK: self.store.name}, pluck="name"):
			frappe.delete_doc("Job Opening", name, force=True, ignore_permissions=True, delete_permanently=True)
		before = frappe.as_json(self.as_user(self.own, register.position_table))
		self.performance_plan(self.a_karan)
		self.assertEqual(frappe.as_json(self.as_user(self.own, register.position_table)), before)
		with_p6 = self.as_user(self.own, register.post_job, self.store.name)
		with_p6["name"] = None
		self.assertEqual(with_p6, without)

	def test_ac84b_a_hiring_allowed_plan_beside_it_lets_hiring_start(self):
		self.performance_plan(self.a_ritu)
		self.make_plan(self.a_sunil, reason="Personal reasons")
		# The cashier seat holds four; fill the other two so it is full.
		for n in ("Fill1065", "Fill2065"):
			self.assign(self.person(n), self.cashier.name)
		frappe.db.commit()
		self.assertTrue(self.as_user(self.hrA, register.post_job, self.cashier.name)["name"])

	def test_ac84c_a_leaving_date_lets_hiring_start(self):
		self.performance_plan(self.a_karan)
		self.assertHeld(self.hrA, self.store.name)
		frappe.db.set_value("Employee", self.karan, "relieving_date", add_days(nowdate(), 20))
		frappe.db.commit()
		self.assertTrue(self.as_user(self.hrA, register.post_job, self.store.name)["name"])

	def test_a_seat_with_room_is_never_held(self):
		"""Spec §7.2: the hold is for a FULL seat. Advertising spare room is
		not replacing anybody."""
		self.performance_plan(self.a_ritu)  # the cashier seat holds four, two are in it
		self.assertTrue(self.as_user(self.hrA, register.post_job, self.cashier.name)["name"])

	def test_sec5_o_the_subject_is_treated_as_if_there_were_no_plan(self):
		"""SEC-5 test (o): an HR Manager whose own plan is on hold learns
		nothing from post_job or the desk form - while another HR Manager is
		held on the same seat, which proves the plan is really there."""
		self.performance_plan(self.a_subj)
		self.assertHeld(self.hrA, self.hr_head.name)
		self.assertTrue(self.as_user(self.hrSubj, register.post_job, self.hr_head.name)["name"])

	# US-25 · recording the outcome

	def test_ac83_ac88_the_outcome_waits_for_the_end_date(self):
		p6 = self.performance_plan(self.a_karan)
		frappe.db.set_value(PLAN, p6, "improvement_ends_on", add_days(nowdate(), 1), update_modified=False)
		frappe.db.commit()
		for outcome in ("improved", "not_improved"):
			with self.assertRaises(frappe.ValidationError, msg=outcome):
				self.as_user(self.hrA, plans.record_outcome, p6, outcome)
		self.assertFalse(frappe.db.get_value(PLAN, p6, "not_improved_on"))

	def test_ac86_improved_erases_the_plan_and_logs_removed(self):
		lines = []

		class Capture:
			def warning(self, message):
				lines.append(json.loads(message))

		p7 = self.performance_plan(self.a_karan, ended_days_ago=0)
		with patch("frappe.enqueue"), patch("frappe.logger", return_value=Capture()):
			self.as_user(self.hrA, plans.record_outcome, p7, "improved")
		self.assertEqual(set(_traces(p7).values()), {0}, _traces(p7))
		self.assertEqual([line["reason"] for line in lines if line.get("event") == "replacement_plan"], ["removed"])
		self.assertNotIn("improved", json.dumps(lines))

	def test_ac87_not_improved_records_who_and_when_and_unlocks_hiring(self):
		p7 = self.performance_plan(self.a_karan, ended_days_ago=5)
		self.age(p7, 50)
		self.assertHeld(self.hrA, self.store.name)
		got = self.as_user(self.hrA2, plans.record_outcome, p7, "not_improved")
		row = frappe.db.get_value(PLAN, p7, ["not_improved_on", "not_improved_by", "confirmed_on", "modified_by"],
		                          as_dict=True)
		self.assertEqual({k: str(v) for k, v in row.items()},
		                 {"not_improved_on": nowdate(), "not_improved_by": self.hrA2, "confirmed_on": nowdate(),
		                  "modified_by": self.hrA2})
		self.assertEqual(got["lapses_on"], str(add_days(nowdate(), 90)))
		self.assertTrue(self.as_user(self.hrA, register.post_job, self.store.name)["name"])

	def test_ac88_every_refusal_changes_nothing(self):
		p1 = self.make_plan(self.a_ritu, reason="Other business reason")
		p7 = self.performance_plan(self.a_karan, ended_days_ago=1)
		subj = self.performance_plan(self.a_subj, ended_days_ago=1)
		cases = [
			(self.hrA, p1, "not_improved", frappe.ValidationError),       # not Performance
			(self.hrA, p7, "maybe", frappe.ValidationError),              # unknown outcome
			(self.own, p7, "not_improved", frappe.PermissionError),       # owners only read
			(self.own, p7, "improved", frappe.PermissionError),
			(self.sys, p7, "not_improved", frappe.PermissionError),       # so does the System Manager
			(self.sys, p7, "improved", frappe.PermissionError),
			(self.hrSubj, subj, "not_improved", frappe.ValidationError),  # their own plan: "someone else changed"
			(self.head, p7, "not_improved", frappe.PermissionError),      # no Read on plans at all
		]
		for user, plan, outcome, error in cases:
			with self.assertRaises(error, msg=f"{user} {outcome}"):
				self.as_user(user, plans.record_outcome, plan, outcome)
			frappe.db.rollback()
		for plan in (p1, p7, subj):
			self.assertTrue(frappe.db.exists(PLAN, plan))
			self.assertFalse(frappe.db.get_value(PLAN, plan, "not_improved_on"))
		# The two outcome fields cannot be written any other way.
		frappe.set_user(self.hrA)
		for field, value in (("not_improved_on", nowdate()), ("not_improved_by", self.hrA)):
			with self.assertRaises(frappe.ValidationError, msg=field):
				frappe.client.set_value(PLAN, p7, field, value)
			doc = frappe.client.get(PLAN, p7)
			doc[field] = value
			doc["flags"] = {plans.OUTCOME_FLAG: True}  # Frappe drops it; the record refuses
			with self.assertRaises(frappe.ValidationError, msg=field):
				frappe.client.save(doc)
		# Both fields, exactly as record_outcome would write them: only the
		# flag (which a request cannot carry) tells the two apart.
		doc = frappe.client.get(PLAN, p7)
		doc.update({"not_improved_on": nowdate(), "not_improved_by": self.hrA,
		            "flags": {plans.OUTCOME_FLAG: True}})
		with self.assertRaises(frappe.ValidationError):
			frappe.client.save(doc)
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.get_value(PLAN, p7, "not_improved_on"))

	def test_ac89_a_second_outcome_or_a_lapsed_plan_gets_here_is_the_latest(self):
		p7 = self.performance_plan(self.a_karan, ended_days_ago=1)
		self.as_user(self.hrA, plans.record_outcome, p7, "not_improved")
		for outcome in ("improved", "not_improved"):
			with self.assertRaises(frappe.ValidationError) as caught:
				self.as_user(self.hrA2, plans.record_outcome, p7, outcome)
			self.assertIn("Someone else changed this plan", str(caught.exception))
		self.assertTrue(frappe.db.exists(PLAN, p7))
		lapsed = self.performance_plan(self.a_ritu, ended_days_ago=40)
		self.age(lapsed, 91)
		with self.assertRaises(frappe.ValidationError) as caught:
			self.as_user(self.hrA, plans.record_outcome, lapsed, "improved")
		self.assertIn("Someone else changed this plan", str(caught.exception))
		self.assertTrue(frappe.db.exists(PLAN, lapsed))

	# US-10 addition, US-26

	def test_ac90_the_reason_never_keeps_a_plan_past_ninety_days(self):
		h = self.performance_plan(self.a_karan)
		self.age(h, 91)
		i = self.performance_plan(self.a_ritu, ended_days_ago=10)
		self.age(i, 85)
		frappe.set_user(self.hrA)
		seen = set(frappe.get_list(PLAN, pluck="name"))
		frappe.set_user("Administrator")
		self.assertEqual(seen, {i})
		with patch("frappe.enqueue"):
			plans.erase_due_plans()
		self.assertFalse(frappe.db.exists(PLAN, h))
		self.assertTrue(frappe.db.exists(PLAN, i))
		self.assertFalse(frappe.get_meta(PLAN).get_link_fields() + frappe.get_meta(PLAN).get_dynamic_link_fields())

	def test_ac91_nothing_reaches_pms_pay_or_the_person(self):
		watched = [d for d in ("PMS Talent Flag", "Appraisal", "Goal", "KPI", "Employee")
		           if frappe.db.exists("DocType", d)]

		def state():
			return {d: (frappe.db.count(d), str(frappe.db.sql(f"select max(modified) from `tab{d}`")[0][0]))
			        for d in watched}

		def replies():
			out = {}
			for user in (self.emp, self.head):
				try:
					out[user] = frappe.as_json(self.as_user(user, register.position_table))
				except frappe.PermissionError:
					out[user] = "refused"
			return out

		before_state, before = state(), replies()
		p6 = self.performance_plan(self.a_karan)
		p7 = self.performance_plan(self.a_ritu, ended_days_ago=1)
		self.as_user(self.hrA, plans.record_outcome, p7, "not_improved")
		self.assertEqual(replies(), before)
		for text in before.values():
			self.assertNotIn("improvement period", text.lower())
			self.assertNotIn("on hold", text.lower())
		with patch("frappe.enqueue"):
			for p in (p6, p7):
				self.as_user(self.hrA, plans.remove_plan, p)
		self.assertEqual(state(), before_state)
