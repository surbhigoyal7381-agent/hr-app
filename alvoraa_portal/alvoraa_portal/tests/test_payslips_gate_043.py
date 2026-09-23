"""Slice 043 AC-30, AC-31 (ALV-114): the payslip list is behind the payroll gate.

**What was live.** `hr_api.get_payslips` carried `@frappe.whitelist()` and
nothing else, while `get_payslip` and `download_payslip` beside it both carried
`@requires_feature("payroll")`. W1D-01 hides the salary parts of the menu on a
tenant without payroll. A hidden menu is not a permission: the list behind it
answered anybody who called it by hand, and it read with
`ignore_permissions=True`. So the entitlement claim was false for as long as it
shipped.

**The gate here is the real one.** `has_feature` reads the SITE CONFIG. These
tests change the site config - which is what a tenant without payroll actually
is - and never patch `has_feature`, `requires_feature` or `enabled_features`.
AC-30(b) makes that a rule rather than a habit: `test_no_test_in_this_slice_
patches_the_gate` reads this slice's own test files and fails the build if any
of them patches it. A patched gate makes every entitlement test green while
proving nothing, and it has happened in this repository before.

**AC-31's four causes.** A refusal that varies is an oracle. All four of these

    1. the slip belongs to somebody else
    2. the slip does not exist
    3. the slip is still a draft
    4. the tenant never bought payroll

give the byte-identical sentence, asserted TOGETHER in one test so that changing
any one of them fails.
"""

import ast
import io
import os

import frappe
from frappe.tests.utils import FrappeTestCase

import alvoraa_portal
from alvoraa_portal import hr_api
from alvoraa_portal.tests import fixtures_043 as fx


def _set_features(features):
	"""A real tenant's real entitlement list, written where has_feature reads it.

	Not a patch of the gate: `enabled_features` reads `frappe.conf["features"]`,
	so this IS the tenant's configuration. `frappe.local.conf` is the live
	object the request sees.
	"""
	frappe.local.conf["features"] = list(features)


def _clear_features():
	frappe.local.conf.pop("features", None)


class TestAPayrollTenantStillWorks(FrappeTestCase):
	"""The pin. Adding a gate must not take the screen away from the tenants
	that bought the thing - which is every tenant this ships to today."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		fx.ensure_company()
		fx.ensure_branches()
		cls.rahul_login = fx.user("rahul", ["Employee"])
		cls.rahul = fx.employee("Rahul", branch=fx.STORE_A, login=cls.rahul_login)
		cls.slip = fx.salary_slip(cls.rahul)

	def setUp(self):
		frappe.set_user(self.rahul_login)
		_set_features(["portal", "leaves", "attendance", "expenses", "payroll"])

	def tearDown(self):
		_clear_features()
		frappe.set_user("Administrator")

	def test_the_list_still_answers_and_still_has_the_slip_in_it(self):
		out = hr_api.get_payslips()
		self.assertIn("payslips", out)
		self.assertIn(self.slip, [row["name"] for row in out["payslips"]])


class TestATenantWithoutPayrollIsRefused(FrappeTestCase):
	"""AC-30(a). The refusal comes from the real gate reading the real config."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		fx.ensure_company()
		fx.ensure_branches()
		cls.rahul_login = fx.user("rahul", ["Employee"])
		cls.rahul = fx.employee("Rahul", branch=fx.STORE_A, login=cls.rahul_login)
		cls.slip = fx.salary_slip(cls.rahul)

	def setUp(self):
		frappe.set_user(self.rahul_login)
		# A real downgrade: an explicit list that does not name payroll.
		_set_features(["portal", "leaves", "attendance", "expenses"])

	def tearDown(self):
		_clear_features()
		frappe.set_user("Administrator")

	def test_the_gate_is_genuinely_shut(self):
		"""If this assertion fails, the rest of the class proves nothing."""
		from alvoraa_portal import subscription
		self.assertFalse(subscription.has_feature("payroll"))

	def test_get_payslips_refuses(self):
		with self.assertRaises(frappe.PermissionError):
			hr_api.get_payslips()

	def test_get_payslip_refuses(self):
		with self.assertRaises(frappe.PermissionError):
			hr_api.get_payslip(self.slip)

	def test_download_payslip_refuses(self):
		with self.assertRaises(frappe.PermissionError):
			hr_api.download_payslip(self.slip)


class TestFourCausesOneSentence(FrappeTestCase):
	"""AC-31. One assertion over all four, so changing one of them fails."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		fx.ensure_company()
		fx.ensure_branches()
		cls.rahul_login = fx.user("rahul", ["Employee"])
		cls.rahul = fx.employee("Rahul", branch=fx.STORE_A, login=cls.rahul_login)
		cls.sandeep_login = fx.user("sandeep", ["Employee"])
		cls.sandeep = fx.employee("Sandeep", branch=fx.STORE_A, login=cls.sandeep_login)
		cls.mine = fx.salary_slip(cls.rahul)
		cls.somebody_elses = fx.salary_slip(cls.sandeep)
		cls.draft = fx.salary_slip(cls.rahul, start=frappe.utils.add_days(
			frappe.utils.nowdate(), -200), end=frappe.utils.add_days(
			frappe.utils.nowdate(), -171), submit=False)

	def setUp(self):
		frappe.set_user(self.rahul_login)

	def tearDown(self):
		_clear_features()
		frappe.set_user("Administrator")

	def _message(self, fn, *args):
		try:
			fn(*args)
		except frappe.PermissionError as exc:
			return str(exc)
		self.fail("%s did not refuse" % getattr(fn, "__name__", fn))

	def test_all_four_causes_give_the_same_sentence(self):
		_set_features(["portal", "leaves", "attendance", "expenses", "payroll"])
		somebody_elses = self._message(hr_api.get_payslip, self.somebody_elses)
		does_not_exist = self._message(hr_api.get_payslip, "SAL-SLIP-NOPE-0001")
		still_a_draft = self._message(hr_api.get_payslip, self.draft)

		_set_features(["portal", "leaves", "attendance", "expenses"])
		never_bought = self._message(hr_api.get_payslip, self.mine)

		self.assertEqual(
			[somebody_elses, does_not_exist, still_a_draft, never_bought],
			[hr_api.PAYSLIP_UNAVAILABLE] * 4,
			"a refusal that varies tells the caller what the tenant bought, or "
			"whose slips exist (AC-31)",
		)

	def test_the_list_endpoint_refuses_with_the_same_sentence(self):
		_set_features(["portal", "leaves", "attendance", "expenses"])
		self.assertEqual(
			self._message(hr_api.get_payslips), hr_api.PAYSLIP_UNAVAILABLE)

	def test_download_refuses_with_the_same_sentence(self):
		_set_features(["portal", "leaves", "attendance", "expenses"])
		self.assertEqual(
			self._message(hr_api.download_payslip, self.mine),
			hr_api.PAYSLIP_UNAVAILABLE)


class TestTheShapeOfTheGateItself(FrappeTestCase):
	"""AC-30(c), and a correction to the spec.

	AC-30(c) asks for `@requires_feature` to sit textually ABOVE
	`@frappe.whitelist()`. Written that way the endpoint stops working for
	everybody: `frappe.whitelist()` does `whitelisted.add(fn)` on the object it
	is handed (frappe/__init__.py:465) and `is_whitelisted` tests the object the
	module name resolves to (:483). Put the gate outermost and the module name
	resolves to a wrapper that was never added, so every call is refused.

	So what is asserted is what the requirement is actually about: the gate is
	present on all three, it names payroll, and the three are built the SAME
	WAY as each other.
	"""

	def test_all_three_payslip_endpoints_carry_the_payroll_gate(self):
		for name in ("get_payslips", "get_payslip", "download_payslip"):
			fn = getattr(hr_api, name)
			self.assertEqual(
				getattr(fn, "__alvoraa_feature__", None), "payroll",
				"%s has no payroll gate" % name)

	def test_all_three_are_still_callable_over_the_api(self):
		"""The order check that matters. A gate that unregisters the endpoint
		refuses everybody, which would look like a working gate in a test that
		only asserted "it refused"."""
		for name in ("get_payslips", "get_payslip", "download_payslip"):
			self.assertIn(
				getattr(hr_api, name), frappe.whitelisted,
				"%s is no longer whitelisted - check the decorator order" % name)

	def test_all_three_refuse_with_the_one_sentence(self):
		for name in ("get_payslips", "get_payslip", "download_payslip"):
			source = _source_of(name)
			self.assertIn(
				"message=PAYSLIP_UNAVAILABLE", source,
				"%s's gate would give the plan's own wording, which differs "
				"from the ownership refusal (AC-31)" % name)


def _dotted(node):
	"""`mock.patch.object` for the node behind that call, or ""."""
	parts = []
	while isinstance(node, ast.Attribute):
		parts.append(node.attr)
		node = node.value
	if not isinstance(node, ast.Name):
		return ""
	parts.append(node.id)
	return ".".join(reversed(parts))


def _patch_targets(source):
	"""What every patch call in this source is pointed at, as text.

	A patch names its target one of two ways: a dotted string
	(`mock.patch("a.b.has_feature")`) or an object plus an attribute name
	(`mock.patch.object(subscription, "has_feature")`). Both end up as string
	arguments, so the strings inside a patch call are what this returns, plus
	any dotted names passed to it.
	"""
	found = []
	for node in ast.walk(ast.parse(source)):
		if not isinstance(node, ast.Call):
			continue
		name = _dotted(node.func)
		# Exactly `…patch(…)` or `…patch.object(…)`. A substring match on
		# "patch" was the third wrong version of this check: it fired on this
		# file's own helper, `_patch_targets(...)`, whose argument is a patched
		# gate written out on purpose.
		parts = name.split(".")
		is_patch = parts[-1] == "patch" or parts[-2:] == ["patch", "object"]
		if not is_patch:
			continue
		for arg in list(node.args) + [kw.value for kw in node.keywords]:
			if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
				found.append(arg.value)
			else:
				dotted = _dotted(arg)
				if dotted:
					found.append(dotted)
	return found


def _hr_api_source():
	path = os.path.join(os.path.dirname(os.path.abspath(alvoraa_portal.__file__)),
	                    "hr_api.py")
	return io.open(path, encoding="utf-8").read()


def _source_of(fn_name):
	"""The decorator lines immediately above `def <fn_name>(`."""
	text = _hr_api_source()
	marker = "\ndef %s(" % fn_name
	at = text.index(marker)
	return text[max(0, at - 300):at]


class TestNoTestInThisSlicePatchesTheGate(FrappeTestCase):
	"""AC-30(b). A patched gate makes every entitlement test green while
	proving nothing. This reads this slice's own test files."""

	BANNED = ("has_feature", "requires_feature", "enabled_features")

	def _my_test_files(self):
		here = os.path.dirname(os.path.abspath(__file__))
		found = []
		for name in sorted(os.listdir(here)):
			if name.endswith("_043.py") and name.startswith("test_"):
				found.append((name, os.path.join(here, name)))
		return found

	def test_there_are_some_files_to_check(self):
		self.assertTrue(self._my_test_files(),
		                "no 043 test files found - this check would be vacuous")

	def test_none_of_them_patches_the_gate(self):
		"""Look at the patch CALLS, not at the file.

		Two earlier versions of this check were wrong in two different ways,
		and both were green-or-red for the wrong reason:

		  1. reading the raw text failed on this file's own docstring, which
		     promises the gate is not patched - the opposite of the point. Wave
		     1 and Wave 2 both hit that trap;
		  2. stripping the strings and then asking "does this file mention
		     patching anywhere, and also mention has_feature anywhere" failed on
		     a genuine `subscription.has_feature()` CALL sitting in a file whose
		     own test METHOD is called `..._patches_the_gate`.

		So it walks the syntax tree, finds the calls that are patches, and looks
		only inside those.
		"""
		for name, path in self._my_test_files():
			for target in _patch_targets(io.open(path, encoding="utf-8").read()):
				for banned in self.BANNED:
					self.assertNotIn(
						banned, target,
						"%s patches %s. The gate must be exercised for real - "
						"change the tenant's `features` config instead (AC-30b)"
						% (name, banned))

	def test_this_check_can_actually_fail(self):
		"""Wave 1 shipped two assertions that could never go red. This one is
		run against a patched gate written out in full, and must find it."""
		targets = _patch_targets(
			"import mock\n"
			"def f():\n"
			"    with mock.patch('alvoraa_portal.subscription.has_feature'):\n"
			"        pass\n"
		)
		self.assertTrue(
			any("has_feature" in t for t in targets),
			"the patch check cannot see a patched gate, so it proves nothing")

	def test_it_does_not_fire_on_a_genuine_call(self):
		"""The false positive that cost this check two rounds."""
		targets = _patch_targets(
			"def test_patches_nothing():\n"
			"    assert subscription.has_feature('payroll') is False\n"
		)
		self.assertEqual(targets, [])
