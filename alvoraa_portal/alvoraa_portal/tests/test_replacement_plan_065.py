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


def insert_plan(assignment, note=None):
	"""Straight through the record, as the desk or REST would - so the rules
	are proved to live in the record, not only in the portal's calls."""
	return frappe.get_doc({"doctype": PLAN, "assignment": assignment, "note": note}).insert().name


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
		frappe.db.delete(PLAN)
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

	def make_plan(self, assignment, note=None, as_user=None):
		frappe.set_user(as_user or self.hrA)
		name = insert_plan(assignment, note)
		frappe.set_user("Administrator")
		return name

	def age(self, plan, days):
		"""Set a plan's last confirmation `days` ago, as the calendar would."""
		frappe.db.set_value(PLAN, plan, "confirmed_on", add_days(nowdate(), -days), update_modified=False)


# ── US-1 · the record (AC-1, AC-2, AC-4; SEC-5) ───────────────────────────────


class TestTheRecord(Plan065Case):
	def test_ac1_three_fields_and_no_history(self):
		meta = frappe.get_meta(PLAN)
		own = [(f.fieldname, f.fieldtype) for f in meta.fields]
		self.assertEqual(own, [("assignment", "Data"), ("confirmed_on", "Date"), ("note", "Small Text")])
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
