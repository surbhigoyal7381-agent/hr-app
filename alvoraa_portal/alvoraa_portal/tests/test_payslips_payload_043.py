"""Slice 043 AC-6: `get_payslips` returns six fields about the caller, not forty.

**What was live.** `get_payslips` returned

    {"payslips": [...], "employee": <the whole Employee row>}

and `_get_employee()` selects `date_of_birth`, `gender`, `cell_number`,
`branch`, `reports_to` and `date_of_joining` among others. So a person's date of
birth, gender and phone number travelled on every load of the Pay screen - the
screen people screenshot for a support ticket and send to a bank - and **nothing
read them.** `portal.js:2593` uses `data.payslips` and nothing else.

This is Wave 1's biggest finding (SEC-12, `frame_api.ME_FIELDS`) applied to the
third endpoint, which 043 `01c` SEC-3 named on purpose.

**Two checks, on purpose.** One asserts the payload of a real call, per persona.
The other reads the source and fails if any Wave 3 module hands a
`_get_employee()` result straight into a payload - because the first check only
sees the endpoints somebody remembered to test, and the leak got in by passing a
row through, not by naming a field.
"""

import ast
import io
import os

import frappe
from frappe.tests.utils import FrappeTestCase

import alvoraa_portal
from alvoraa_portal import hr_api
from alvoraa_portal.tests import fixtures_043 as fx

# Never, on any Wave 3 payload, for any persona.
NEVER = ("date_of_birth", "gender", "cell_number", "date_of_joining",
         "reports_to", "branch", "personal_email", "current_address",
         "bank_ac_no", "iban", "ctc", "salary_mode")


def _payroll_on():
	frappe.local.conf["features"] = ["portal", "leaves", "attendance",
	                                 "expenses", "payroll"]


def _payroll_clear():
	frappe.local.conf.pop("features", None)


class TestTheKeyListIsFixed(FrappeTestCase):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		fx.ensure_company()
		fx.ensure_branches()
		cls.rahul_login = fx.user("rahul", ["Employee"])
		cls.rahul = fx.employee("Rahul", branch=fx.STORE_A, login=cls.rahul_login)
		cls.sandeep_login = fx.user("sandeep", ["Employee"])
		cls.sandeep = fx.employee("Sandeep", branch=fx.STORE_A,
		                          login=cls.sandeep_login)
		# Rahul reports to Sandeep, so `reports_to` is genuinely SET on the row.
		# Asserting a field is absent when it was empty anyway proves nothing.
		fx.employee("Rahul", branch=fx.STORE_A, login=cls.rahul_login,
		            reports_to=cls.sandeep)
		frappe.db.set_value("Employee", cls.rahul, "cell_number", "9000000001")
		frappe.db.commit()
		cls.slip = fx.salary_slip(cls.rahul)

	def setUp(self):
		frappe.set_user(self.rahul_login)
		_payroll_on()

	def tearDown(self):
		_payroll_clear()
		frappe.set_user("Administrator")

	def test_the_fixture_really_has_the_sensitive_fields_set(self):
		"""Otherwise every assertion below passes for the wrong reason."""
		row = frappe.db.get_value(
			"Employee", self.rahul,
			["date_of_birth", "gender", "cell_number", "reports_to", "branch"],
			as_dict=True)
		for field, value in row.items():
			self.assertTrue(value, "%s is empty on the fixture" % field)

	def test_the_top_level_keys_are_exactly_two(self):
		self.assertEqual(sorted(hr_api.get_payslips().keys()), ["me", "payslips"])

	def test_the_me_block_is_exactly_the_six(self):
		me = hr_api.get_payslips()["me"]
		self.assertEqual(sorted(me.keys()), sorted(hr_api.ME_FIELDS))

	def test_none_of_the_forbidden_fields_is_anywhere_in_the_payload(self):
		"""Not just in `me` - anywhere, at any depth."""
		text = frappe.as_json(hr_api.get_payslips())
		for field in NEVER:
			self.assertNotIn(
				field, text,
				"%s is on the Pay payload. It is the screen people attach to a "
				"support ticket (AC-6)." % field)

	def test_the_value_of_the_phone_number_is_gone_too(self):
		"""A key can be renamed; the number is what leaks."""
		self.assertNotIn("9000000001", frappe.as_json(hr_api.get_payslips()))

	def test_the_six_fields_are_the_same_six_wave_one_fixed(self):
		from alvoraa_portal import frame_api
		self.assertEqual(set(hr_api.ME_FIELDS), set(frame_api.ME_FIELDS))

	def test_a_caller_with_no_employee_record_still_gets_a_clean_answer(self):
		asha = fx.user("asha", ["Employee"])
		frappe.set_user(asha)
		self.assertEqual(hr_api.get_payslips(), {"no_employee": True})


class TestNoWaveThreeModuleHandsAnEmployeeRowToAPayload(FrappeTestCase):
	"""AC-6's static half.

	The leak got in by passing a row through, not by naming a field. A test of
	the payload only sees the endpoints somebody remembered to test; this sees
	the shape of the mistake.
	"""

	# The functions whose result is a whole Employee row.
	ROW_SOURCES = ("_get_employee",)

	# ── Declared debt, not an exemption ──────────────────────────────────
	#
	# This check found FOUR more endpoints doing exactly what `get_payslips`
	# did, all of them older than Wave 3. A hand grep found three of them; the
	# syntax walk found the rest, which is the argument for having it:
	#
	#     get_portal_context      -> portal.js:2715 reads `ctx.employee`
	#     get_employee_dashboard  -> portal.js reads `d.employee`
	#     get_manager_dashboard   -> same. **PAID OFF by slice 045** (AC-6 /
	#                                AC-16): the Team call stopped handing
	#                                over the whole Employee row and now
	#                                sends a six-key `me` block. It is out
	#                                of the list below because the list is
	#                                debt, and this debt is gone.
	#     get_expense_claims      -> same
	#     get_checkin_status      -> portal.js:3071 reads `d.employee`
	#
	# Each returns `_get_employee()`'s whole row, so each carries
	# date_of_birth, gender, cell_number, branch and reports_to to the browser.
	# Unlike `get_payslips`, all five are READ by the live screens, so trimming
	# them changes working pages and needs its own impact analysis - it is not
	# a line Wave 3 can quietly add. It is reported as a finding instead.
	#
	# They are listed here rather than excluded by a looser rule, so that:
	#   (a) the number cannot grow without somebody editing this list;
	#   (b) the debt has a name and appears in the slice's notes;
	#   (c) a Wave 3 function can never be added to it - the test below refuses.
	KNOWN_PRE_EXISTING = (
		("hr_api.py", "get_checkin_status"),
		("hr_api.py", "get_employee_dashboard"),
		("hr_api.py", "get_expense_claims"),
		("hr_api.py", "get_portal_context"),
	)

	# Everything Wave 3 writes or changes. None of these may ever be excused.
	WAVE_THREE_FUNCTIONS = ("get_payslips", "get_payslip", "download_payslip",
	                        "get_shift_types")

	# ── The files this walks (045 F6) ────────────────────────────────────
	#
	# It was three. Wave 4 added `team_api.py` and `growth_api.py` - two
	# modules whose whole job is building payloads about people - and neither
	# was scanned, so the check that exists to catch this shape of mistake did
	# not look at the two newest places it could happen.
	#
	# Neither offends today: `team_api` builds every row key by key from
	# `ROW_FIELDS` and the caller's own block from `me_block`, and `growth_api`
	# puts no Employee row in a payload at all. That is the point - the guard is
	# for the SIXTH one, and it now runs where the sixth would be written.
	SOURCES = ("hr_api.py", "pay_api.py", "time_api.py",
	           "team_api.py", "growth_api.py")

	def _wave_three_sources(self):
		root = os.path.dirname(os.path.abspath(alvoraa_portal.__file__))
		found = []
		for name in self.SOURCES:
			path = os.path.join(root, name)
			if os.path.isfile(path):
				found.append((name, path))
		return found

	def test_every_named_source_really_exists(self):
		"""A file renamed away would silently stop being scanned, and the list
		above would still read as though it covered five modules."""
		self.assertEqual([n for n, _ in self._wave_three_sources()],
		                 list(self.SOURCES),
		                 "a file in SOURCES is missing - it is no longer scanned")

	def test_there_is_something_to_check(self):
		self.assertTrue(self._wave_three_sources())

	def _offenders(self):
		found = []
		for name, path in self._wave_three_sources():
			source = io.open(path, encoding="utf-8").read()
			for fn in _functions_putting_a_row_in_a_payload(source, self.ROW_SOURCES):
				found.append((name, fn))
		return sorted(found)

	def test_no_wave_three_function_hands_a_row_to_a_payload(self):
		for name, fn in self._offenders():
			self.assertNotIn(
				fn, self.WAVE_THREE_FUNCTIONS,
				"%s.%s puts a whole Employee row straight into a payload. "
				"Build a fixed key list instead (AC-6)." % (name, fn))

	def test_the_list_of_pre_existing_offenders_has_not_grown(self):
		"""Declared debt, pinned. A new one fails here and must either be
		fixed or added deliberately, with a reason, by a person."""
		self.assertEqual(
			self._offenders(), sorted(self.KNOWN_PRE_EXISTING),
			"a payload that hands out a whole Employee row has appeared or "
			"disappeared. Fixing one? Take it out of KNOWN_PRE_EXISTING. "
			"Adding one? It needs its own impact analysis (AC-6).")

	def test_this_check_can_actually_fail(self):
		"""The version that shipped, written out, must be found."""
		fns = _functions_putting_a_row_in_a_payload(
			"def get_payslips():\n"
			"    emp = _get_employee()\n"
			"    return {'payslips': slips, 'employee': emp}\n",
			self.ROW_SOURCES)
		self.assertEqual(fns, ["get_payslips"],
		                 "the check cannot see the leak it exists for")

	def test_it_does_not_fire_on_the_fixed_version(self):
		fns = _functions_putting_a_row_in_a_payload(
			"def get_payslips():\n"
			"    emp = _get_employee()\n"
			"    return {'payslips': slips, 'me': _me_block(emp)}\n",
			self.ROW_SOURCES)
		self.assertEqual(fns, [])


def _functions_putting_a_row_in_a_payload(source, row_sources):
	"""Top-level functions that put a whole-Employee-row variable in a dict."""
	offenders = []
	for node in ast.parse(source).body:
		if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
			continue
		holders = set()
		for inner in ast.walk(node):
			if not isinstance(inner, ast.Assign) or not isinstance(inner.value, ast.Call):
				continue
			func = inner.value.func
			called = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
			if called not in row_sources:
				continue
			for target in inner.targets:
				if isinstance(target, ast.Name):
					holders.add(target.id)
		if not holders:
			continue
		for inner in ast.walk(node):
			if not isinstance(inner, ast.Dict):
				continue
			if any(isinstance(v, ast.Name) and v.id in holders for v in inner.values):
				offenders.append(node.name)
				break
	return sorted(offenders)
