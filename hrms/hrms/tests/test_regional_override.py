"""Regional override wrapper in hrms.hr.utils.

frappe.get_hooks merges every app's hook values into lists, so a regional override
registered as a string in hooks.py arrives here as ["dotted.path"]. The wrapper must
accept both shapes; it used to call frappe.get_attr on the list and fail with
"'list' object has no attribute 'split'" for every income-tax payslip in India.
"""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from hrms.hr.utils import allow_regional


def override_impl(*args, **kwargs):
	return ("regional", args, kwargs)


@allow_regional
def plain_impl(*args, **kwargs):
	return ("plain", args, kwargs)


class TestRegionalOverride(IntegrationTestCase):
	def _hooks(self, target):
		country = frappe.get_system_settings("country")
		return {"regional_overrides": {country: {"hrms.hr.utils.plain_impl": target}}}

	def _run(self, target):
		hooks = self._hooks(target)

		def fake_get_hooks(hook=None, default=None, app_name=None):
			return hooks.get(hook, default)

		with patch.object(frappe, "get_hooks", side_effect=fake_get_hooks):
			return plain_impl(1, two=2)

	def test_override_given_as_list_is_used(self):
		"""The shape frappe.get_hooks actually returns."""
		result = self._run(["hrms.tests.test_regional_override.override_impl"])
		self.assertEqual(result[0], "regional")
		self.assertEqual(result[1], (1,))
		self.assertEqual(result[2], {"two": 2})

	def test_last_installed_app_wins(self):
		result = self._run(["hrms.hr.utils.get_company_currency", "hrms.tests.test_regional_override.override_impl"])
		self.assertEqual(result[0], "regional")

	def test_override_given_as_string_still_works(self):
		result = self._run("hrms.tests.test_regional_override.override_impl")
		self.assertEqual(result[0], "regional")

	def test_no_override_falls_back_to_plain(self):
		with patch.object(frappe, "get_hooks", side_effect=lambda *a, **k: {}):
			self.assertEqual(plain_impl(3)[0], "plain")
