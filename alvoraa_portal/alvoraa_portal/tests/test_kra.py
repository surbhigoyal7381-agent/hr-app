"""Objectives sit under a Key Result Area, when the organisation requires it.

The industry pattern, which Frappe HR already implements and this reuses rather
than reinventing:

    KRA                      the library - "Revenue Growth", "Team Development"
    Appraisal Template       groups KRAs for a ROLE, each with a weightage
    Appraisal Template Goal  one KRA + its per_weightage
    Appraisal / Appraisee    assigns a template to a person

KRAs belong to the JOB, not the person. So "this employee has no KRAs" always
means "HR has not assigned them a template yet" - never that the employee did
something wrong. That distinction is the whole reason the dialog exists.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import kra_api


class KraMixin:
	def setUp(self):
		frappe.set_user("Administrator")
		self._saved = frappe.db.get_default(kra_api.MANDATORY_KEY)
		# These endpoints ride the Goals feature gate, so a test bench without
		# Goals sold refuses them before the logic under test ever runs.
		self._feats = frappe.conf.get("features")
		frappe.conf["features"] = list(self._feats or []) + ["goals"]
		self._made = []

	def tearDown(self):
		frappe.set_user("Administrator")
		if self._feats is None:
			frappe.conf.pop("features", None)
		else:
			frappe.conf["features"] = self._feats
		frappe.db.set_default(kra_api.MANDATORY_KEY, self._saved or "0")
		for dt, name in reversed(self._made):
			if frappe.db.exists(dt, name):
				frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
		frappe.db.commit()

	def _make(self, doc):
		d = frappe.get_doc(doc)
		d.flags.ignore_permissions = True
		d.insert(ignore_permissions=True)
		self._made.append((d.doctype, d.name))
		return d


class TestTheSetting(KraMixin, FrappeTestCase):
	"""One switch, stored the same way as every other org-level setting."""

	def test_it_is_off_by_default(self):
		frappe.db.set_default(kra_api.MANDATORY_KEY, "0")
		self.assertFalse(kra_api.is_mandatory())

	def test_turning_it_on_is_read_back(self):
		frappe.db.set_default(kra_api.MANDATORY_KEY, "1")
		self.assertTrue(kra_api.is_mandatory())

	def test_an_unset_value_is_not_mandatory(self):
		"""A site that has never seen this setting must behave as before it
		existed. Defaulting to ON would block every employee on upgrade."""
		frappe.db.set_default(kra_api.MANDATORY_KEY, None)
		self.assertFalse(kra_api.is_mandatory())


class TestWhichKrasAnEmployeeGets(KraMixin, FrappeTestCase):
	"""Filtered to their own template, on purpose.

	Offering every KRA on the site would let someone in Finance file objectives
	under a Sales area - precisely what the link exists to prevent.
	"""

	def test_no_template_means_no_kras(self):
		"""And that is the case the portal has to explain, not fail on."""
		self.assertEqual(kra_api.kras_for_employee("EMP-does-not-exist"), [])

	def test_no_employee_means_no_kras(self):
		self.assertEqual(kra_api.kras_for_employee(None), [])

	def test_it_reads_the_template_not_the_whole_library(self):
		import inspect

		src = inspect.getsource(kra_api.kras_for_employee)
		self.assertIn("Appraisal Template Goal", src)
		self.assertIn("_employee_template", src)

	def test_the_template_lookup_tries_both_places(self):
		"""An Appraisal exists once a cycle is under way; before that the cycle's
		`appraisees` table carries the intended template."""
		import inspect

		src = inspect.getsource(kra_api._employee_template)
		self.assertIn("Appraisal", src)
		self.assertIn("Appraisee", src)


class TestValidation(KraMixin, FrappeTestCase):
	"""Enforced on the DOCUMENT, so the rule holds for the desk and the API too -
	not only for whoever happens to use the portal form."""

	class FakeGoal:
		def __init__(self, kra=None, status="Active"):
			self.kra = kra
			self.status = status

	def test_it_does_nothing_when_the_setting_is_off(self):
		frappe.db.set_default(kra_api.MANDATORY_KEY, "0")
		kra_api.validate_goal_kra(self.FakeGoal(kra=None))      # must not raise

	def test_it_blocks_an_active_objective_with_no_kra(self):
		frappe.db.set_default(kra_api.MANDATORY_KEY, "1")
		with self.assertRaises(frappe.ValidationError):
			kra_api.validate_goal_kra(self.FakeGoal(kra=None, status="Active"))

	def test_a_draft_is_always_allowed(self):
		"""Blocking outright would stop everyone writing objectives the moment HR
		forgets a template. The setting exists to keep goals tied to the role,
		not to hold people hostage to a configuration gap."""
		frappe.db.set_default(kra_api.MANDATORY_KEY, "1")
		kra_api.validate_goal_kra(self.FakeGoal(kra=None, status="Draft"))

	def test_an_objective_with_a_kra_passes(self):
		frappe.db.set_default(kra_api.MANDATORY_KEY, "1")
		kra_api.validate_goal_kra(self.FakeGoal(kra="Revenue Growth", status="Active"))

	def test_the_message_says_what_to_do(self):
		"""A refusal that does not say how to proceed is a dead end."""
		frappe.db.set_default(kra_api.MANDATORY_KEY, "1")
		try:
			kra_api.validate_goal_kra(self.FakeGoal(kra=None))
		except frappe.ValidationError:
			msg = str(frappe.message_log[-1]).lower()
			self.assertIn("draft", msg)
			self.assertIn("hr", msg)

	def test_it_is_wired_as_a_hook(self):
		"""A validation nothing calls is decoration."""
		hooks = frappe.get_hooks("doc_events") or {}
		wired = str(hooks.get("Individual Goal", {}))
		self.assertIn("validate_goal_kra", wired)


class TestReportingToHr(KraMixin, FrappeTestCase):
	"""The way out of the dialog. A mandatory field with no escape is the worst
	version of this feature."""

	def test_it_refuses_when_there_is_no_hr_to_tell(self):
		"""Better to say so than to accept the click and drop it silently."""
		from unittest.mock import patch

		with patch.object(kra_api, "_hr_users", return_value=[]):
			with self.assertRaises(frappe.ValidationError):
				kra_api.report_missing_kra()

	def test_administrator_is_not_counted_as_hr(self):
		"""It is everybody's account and nobody's inbox."""
		import inspect

		self.assertIn('!= "Administrator"', inspect.getsource(kra_api._hr_users))

	def test_it_uses_frappes_own_notification_log(self):
		"""So it lands in HR's bell, not a parallel inbox nobody checks."""
		import inspect

		self.assertIn("Notification Log", inspect.getsource(kra_api.report_missing_kra))

	def test_only_enabled_users_are_notified(self):
		import inspect

		self.assertIn('"enabled": 1', inspect.getsource(kra_api._hr_users))


class TestTheEndpointsAreGated(FrappeTestCase):
	"""Goals is an Enterprise feature, so these ride the same gate as the rest."""

	def test_get_my_kras_requires_the_goals_feature(self):
		self.assertEqual(
			getattr(kra_api.get_my_kras, "__alvoraa_feature__", None), "goals")

	def test_report_missing_kra_requires_the_goals_feature(self):
		self.assertEqual(
			getattr(kra_api.report_missing_kra, "__alvoraa_feature__", None), "goals")


class TestTheFieldExists(FrappeTestCase):
	def test_individual_goal_has_a_kra_link(self):
		if not frappe.db.exists("DocType", "Individual Goal"):
			self.skipTest("goals app not installed here")
		meta = frappe.get_meta("Individual Goal")
		field = meta.get_field("kra")
		self.assertIsNotNone(field, "Individual Goal needs a kra field")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "KRA", "it must link to Frappe HR's own KRA")

	def test_create_goal_accepts_one(self):
		import inspect

		from alvoraa_portal import goals_api

		self.assertIn("kra", inspect.signature(goals_api.create_goal).parameters)
