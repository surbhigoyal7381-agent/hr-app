"""Slice 043 AC-52 (`01c` SEC-7): `get_shift_types` gets a caller check and a scope.

**What was live.** `@frappe.whitelist()` and nothing else,
`ignore_permissions=True`, no caller check, no scope. Every Shift Type in the
tenant went to anybody with a login - including a person who had left and whose
account was still open. A tenant's shift names are a map of its operation.

**The scope, and why the spec had to be rewritten to get it.** Revision 1 asked
for "the caller's company's shift types". `Shift Type` has no `company` field,
so there was nothing to filter on and the sentence could not be built. D-6's
recommendation, built here: the Shift Types **in use in the caller's own
company through Shift Assignment**, plus the caller's own `default_shift`.

Three things AC-52 holds whatever scope is chosen, and each has a test:

  (a) the caller must have an **Active** Employee record, or nothing comes back
  (b) the read carries **no `ignore_permissions`**
  (c) the list is **not** every Shift Type in the tenant, proved by a second
      company whose night shift must be absent

The fixture has two companies on purpose. A one-company fixture cannot tell a
scoped list from an unscoped one.
"""

import ast
import io
import os

import frappe
from frappe.tests.utils import FrappeTestCase

import alvoraa_portal
from alvoraa_portal import hr_api
from alvoraa_portal.tests import fixtures_043 as fx


class TestTheShiftListIsScoped(FrappeTestCase):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		company_a = fx.ensure_company()
		company_b = fx.ensure_company(fx.COMPANY_B, fx.ABBR_B)
		fx.ensure_branches()

		cls.day = fx.ensure_shift(fx.SHIFT_A, "09:30:00", "18:30:00")
		cls.night = fx.ensure_shift(fx.SHIFT_B, "22:00:00", "06:00:00")
		cls.unused = fx.ensure_shift(fx.SHIFT_UNUSED, "07:00:00", "15:00:00")

		cls.rahul_login = fx.user("rahul", ["Employee"])
		cls.rahul = fx.employee("Rahul", branch=fx.STORE_A, login=cls.rahul_login,
		                        company=company_a)
		cls.bhavna_login = fx.user("bhavna", ["Employee"])
		cls.bhavna = fx.employee("Bhavna", login=cls.bhavna_login,
		                         company=company_b)
		cls.asha_login = fx.user("asha", ["Employee"])
		cls.leaver_login = fx.user("leaver", ["Employee"])
		cls.leaver = fx.employee("Leaver", branch=fx.STORE_A,
		                         login=cls.leaver_login, status="Left",
		                         company=company_a)

		fx.assign_shift(cls.rahul, cls.day, company_a)
		fx.assign_shift(cls.bhavna, cls.night, company_b)

	def setUp(self):
		frappe.set_user(self.rahul_login)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _names(self):
		return [row["name"] for row in hr_api.get_shift_types()]

	# ── The fixture itself ───────────────────────────────────────────────

	def test_all_three_shift_types_really_exist(self):
		"""Otherwise "the night shift is absent" is true for the wrong reason."""
		for name in (self.day, self.night, self.unused):
			self.assertTrue(frappe.db.exists("Shift Type", name))

	def test_the_two_people_really_are_in_different_companies(self):
		self.assertNotEqual(
			frappe.db.get_value("Employee", self.rahul, "company"),
			frappe.db.get_value("Employee", self.bhavna, "company"))

	# ── (c) the list is not everything ───────────────────────────────────

	def test_my_own_companys_shift_is_offered(self):
		self.assertIn(self.day, self._names())

	def test_the_other_companys_night_shift_is_not(self):
		self.assertNotIn(
			self.night, self._names(),
			"company B's shift type reached company A's employee (AC-52c)")

	def test_a_shift_type_nobody_is_assigned_to_is_not_offered(self):
		self.assertNotIn(self.unused, self._names())

	def test_the_other_person_sees_their_own_and_not_mine(self):
		frappe.set_user(self.bhavna_login)
		names = self._names()
		self.assertIn(self.night, names)
		self.assertNotIn(self.day, names)

	def test_the_payload_keys_are_the_three_it_always_had(self):
		rows = hr_api.get_shift_types()
		self.assertTrue(rows)
		for row in rows:
			self.assertEqual(sorted(row.keys()),
			                 ["end_time", "name", "start_time"])

	# ── (a) the caller check ─────────────────────────────────────────────

	def test_a_login_with_no_employee_record_gets_nothing(self):
		frappe.set_user(self.asha_login)
		self.assertEqual(hr_api.get_shift_types(), [])

	def test_a_leaver_gets_nothing(self):
		"""`_get_employee` filters on status Active, so a login that still
		works after the person left finds no employee and no shifts."""
		frappe.set_user(self.leaver_login)
		self.assertEqual(hr_api.get_shift_types(), [])

	def test_guest_is_refused(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			frappe.is_whitelisted(hr_api.get_shift_types)

	# ── Own default shift, even with no assignment anywhere ──────────────

	def test_my_own_default_shift_is_always_offered(self):
		"""The pin for the shift-change modal: the person whose shift is set on
		the Employee record and who has no Shift Assignment must still see it."""
		lonely_login = fx.user("lonely", ["Employee"])
		lonely_company = fx.ensure_company("S043 Lonely Company", "S43L")
		fx.employee("Lonely", login=lonely_login, company=lonely_company,
		            default_shift=self.unused)
		frappe.set_user(lonely_login)
		names = self._names()
		self.assertEqual(names, [self.unused])

	def test_an_empty_scope_returns_an_empty_list_not_everything(self):
		"""The rule that matters most. An empty filter dict means "everything"
		to frappe.get_all, which is the defect being fixed."""
		empty_login = fx.user("empty", ["Employee"])
		empty_company = fx.ensure_company("S043 Empty Company", "S43M")
		fx.employee("Empty", login=empty_login, company=empty_company)
		frappe.set_user(empty_login)
		self.assertEqual(hr_api.get_shift_types(), [])


class TestTheShapeOfTheFunction(FrappeTestCase):
	"""(b), and the no-empty-filter rule, read from the source."""

	def _function_source(self):
		path = os.path.join(
			os.path.dirname(os.path.abspath(alvoraa_portal.__file__)), "hr_api.py")
		tree = ast.parse(io.open(path, encoding="utf-8").read())
		for node in tree.body:
			if isinstance(node, ast.FunctionDef) and node.name == "get_shift_types":
				return node
		self.fail("get_shift_types is gone")

	def test_it_carries_no_ignore_permissions(self):
		node = self._function_source()
		for inner in ast.walk(node):
			if isinstance(inner, ast.keyword):
				self.assertNotEqual(
					inner.arg, "ignore_permissions",
					"get_shift_types reads with ignore_permissions (AC-52b)")

	def test_no_filters_dict_it_builds_is_empty(self):
		"""An empty filter dict means "everything". No scope helper in this
		slice may return one."""
		node = self._function_source()
		for inner in ast.walk(node):
			if isinstance(inner, ast.keyword) and inner.arg == "filters":
				if isinstance(inner.value, ast.Dict):
					self.assertTrue(
						inner.value.keys,
						"get_shift_types builds an empty filters dict, which "
						"means every row")

	def test_this_check_can_actually_fail(self):
		tree = ast.parse("def f():\n    return get_all('X', ignore_permissions=True)\n")
		found = [k.arg for k in ast.walk(tree) if isinstance(k, ast.keyword)]
		self.assertIn("ignore_permissions", found)
