"""ALV-249 security review, doors 1 and 2: one extra word in a request must not skip
User Permissions or permissions.

Each test first shows the door open when the word reaches Frappe (so the test can
fail), then shut once request_guard has run on the same arguments, as it does on
every HTTP request.
"""

import ast
import json
import os
import re

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import request_guard

HOOK = "alvoraa_portal.request_guard.drop_permission_skips"


class DoorsCase(FrappeTestCase):
	_n = 0

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		DoorsCase._n += 1
		tag = "%d%s" % (DoorsCase._n, frappe.generate_hash(length=4))
		cls.company = frappe.db.get_value("Company", {}, "name")
		cls.me, cls.me_user = cls._person("G" + tag + "me")
		cls.other, _ = cls._person("G" + tag + "other")
		cls.rows = {}
		for doctype, extra in (
			("Expense Claim", {"posting_date": "2026-10-01", "approval_status": "Draft", "status": "Draft"}),
			("Attendance", {"attendance_date": "2026-10-01", "status": "Present", "docstatus": 1}),
			("Leave Application", {"from_date": "2026-10-01", "to_date": "2026-10-01", "status": "Open",
			                       "posting_date": "2026-10-01"}),
			("Salary Structure Assignment", {"from_date": "2026-10-01", "base": 50000, "docstatus": 1}),
		):
			cls.rows[doctype] = {who: cls._row(doctype, emp, extra) for who, emp in (("me", cls.me), ("other", cls.other))}

	@classmethod
	def _person(cls, label):
		email = "orpg%s@example.com" % label.lower()
		u = frappe.get_doc({"doctype": "User", "email": email, "first_name": label,
		                    "send_welcome_email": 0}).insert(ignore_permissions=True)
		u.add_roles("Employee")
		e = frappe.get_doc({"doctype": "Employee", "first_name": label, "company": cls.company,
		                    "date_of_birth": "1990-10-15", "date_of_joining": "2015-01-01",
		                    "gender": frappe.db.get_value("Gender", {}, "name") or "Male", "status": "Active",
		                    "user_id": email, "create_user_permission": 0, "cell_number": "9800000000"}
		                   ).insert(ignore_permissions=True)
		return e.name, email

	@classmethod
	def _row(cls, doctype, employee, extra):
		d = frappe.new_doc(doctype)
		d.update({"name": "ALV249G-%s" % frappe.generate_hash(length=10), "employee": employee,
		          "company": cls.company})
		d.update(extra)
		d.db_insert()
		return d.name

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local.form_dict = frappe._dict()

	def request(self, method, guarded, **args):
		"""Send args the way an HTTP request does: through form_dict, then frappe.call."""
		frappe.set_user(self.me_user)  # set_user clears form_dict, so it goes first
		frappe.local.form_dict = frappe._dict(args)
		if guarded:
			frappe.get_attr(HOOK)()
		try:
			return frappe.call(frappe.get_attr(method), **frappe.local.form_dict)
		finally:
			frappe.set_user("Administrator")
			frappe.local.form_dict = frappe._dict()

	def names(self, out):
		if isinstance(out, dict) and "keys" in out:  # reportview.get is compressed
			i = out["keys"].index("name")
			return {v[i] for v in out["values"]}
		return {(r.get("name") if isinstance(r, dict) else r[0]) for r in out or []}


class ListDoors(DoorsCase):
	def check(self, method, doctype, ids):
		args = {"doctype": doctype, "fields": json.dumps(["name"]),
		        "filters": json.dumps([["name", "in", ids]]), "limit_page_length": 0,
		        "ignore_user_permissions": 1}
		open_ = self.names(self.request(method, False, **args))
		self.assertIn(ids[1], open_, f"{method} {doctype}: the door is not open without the guard, so this test proves nothing")
		shut = self.names(self.request(method, True, **args))
		self.assertNotIn(ids[1], shut, f"{method} {doctype}: a colleague's record came back")

	def ids(self, doctype):
		if doctype == "Employee":
			return [self.me, self.other]
		return [self.rows[doctype]["me"], self.rows[doctype]["other"]]

	def test_reportview_get(self):
		for dt in ("Employee", "Expense Claim", "Attendance", "Leave Application", "Salary Structure Assignment"):
			self.check("frappe.desk.reportview.get", dt, self.ids(dt))

	def test_reportview_get_list(self):
		for dt in ("Employee", "Expense Claim", "Attendance", "Leave Application", "Salary Structure Assignment"):
			self.check("frappe.desk.reportview.get_list", dt, self.ids(dt))

	def test_reportview_get_count(self):
		for dt in ("Employee", "Expense Claim", "Attendance", "Leave Application", "Salary Structure Assignment"):
			args = {"doctype": dt, "filters": json.dumps([["name", "in", self.ids(dt)]]),
			        "ignore_user_permissions": 1}
			self.assertEqual(self.request("frappe.desk.reportview.get_count", False, **args), 2, dt)
			self.assertEqual(self.request("frappe.desk.reportview.get_count", True, **args), 1, dt)


class SearchDoors(DoorsCase):
	def test_search_widget_with_filter_fields(self):
		args = {"doctype": "Employee", "txt": "", "reference_doctype": "Employee",
		        "link_fieldname": "reports_to", "ignore_user_permissions": 1, "page_length": 1000,
		        "filter_fields": json.dumps(["date_of_birth", "cell_number"]),
		        "filters": json.dumps([["name", "in", [self.me, self.other]]])}
		other_name = frappe.db.get_value("Employee", self.other, "employee_name")

		def values(guarded):
			rows = self.request("frappe.desk.search.search_widget", guarded, **args) or []
			return {v for r in rows for v in (r.values() if isinstance(r, dict) else r)}
		self.assertTrue({self.other, other_name} & values(False))
		self.assertFalse({self.other, other_name} & values(True))

	def test_search_link(self):
		args = {"doctype": "Employee", "txt": "", "reference_doctype": "Employee",
		        "link_fieldname": "reports_to", "ignore_user_permissions": 1, "page_length": 1000,
		        "filters": json.dumps([["name", "in", [self.me, self.other]]])}
		got = lambda guarded: {r["value"] for r in self.request("frappe.desk.search.search_link", guarded, **args)}
		self.assertIn(self.other, got(False))
		self.assertNotIn(self.other, got(True))


class TheGuardItself(FrappeTestCase):
	def test_registered_before_our_other_request_hooks(self):
		hooks = frappe.get_hooks("before_request")
		self.assertIn(HOOK, hooks)
		self.assertLess(hooks.index(HOOK), hooks.index("alvoraa_portal.auth.lock_until_password_chosen"))

	def test_drops_both_words_on_any_path_including_root_with_cmd(self):
		frappe.local.form_dict = frappe._dict(cmd="frappe.desk.reportview.get", doctype="Employee",
		                                      ignore_user_permissions="1", ignore_permissions="1")
		try:
			request_guard.drop_permission_skips()
			self.assertEqual(dict(frappe.local.form_dict), {"cmd": "frappe.desk.reportview.get", "doctype": "Employee"})
		finally:
			frappe.local.form_dict = frappe._dict()

	def test_every_whitelisted_permission_skip_argument_is_dropped(self):
		"""CI check: a Frappe, ERPNext or Frappe HR upgrade that adds a new whitelisted
		argument that skips permissions fails here until it is added to DROP or to
		NOT_A_SKIP with a reason."""
		NOT_A_SKIP = {
			# frappe.desk.form.linked_with.get_linked_doctypes: lists link metadata only.
			"without_ignore_user_permissions_enabled",
		}
		pattern = re.compile(r"ignore_\w*permission")
		found = {}
		root = os.path.dirname(os.path.dirname(os.path.dirname(frappe.__file__)))
		for app in frappe.get_installed_apps():
			base = os.path.join(root, app, app)
			for dirpath, _dirs, files in os.walk(base):
				if "/tests" in dirpath.replace(os.sep, "/") or "node_modules" in dirpath:
					continue
				for f in files:
					if not f.endswith(".py"):
						continue
					path = os.path.join(dirpath, f)
					try:
						with open(path, encoding="utf-8") as fh:
							tree = ast.parse(fh.read())
					except (SyntaxError, UnicodeDecodeError):
						continue
					for node in ast.walk(tree):
						if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
								"whitelist" in ast.unparse(d) for d in node.decorator_list):
							for a in node.args.args + node.args.kwonlyargs:
								if pattern.search(a.arg) and a.arg not in NOT_A_SKIP:
									found.setdefault(a.arg, []).append(f"{path}:{node.name}")
		missing = {k: v for k, v in found.items() if k not in request_guard.DROP}
		self.assertFalse(missing, missing)
		self.assertIn("ignore_user_permissions", found)
