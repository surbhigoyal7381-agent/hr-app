"""A new feature must be OFF everywhere until somebody switches it on.

We ship one image to every tenant at once. Without this rule, adding a key to
the registry hands that feature to everyone the moment the container restarts -
tenants on a plan that never included it, customers who have not asked for it,
seen it, or been trained on it. A module appearing in somebody's desk overnight
is not a gift. It is a support call, and sometimes a question about who could
see what.

There were two ways it leaked on, and both are closed here:

  a site with no recorded feature list fell back to "everything the registry
  has", which by definition includes anything added this morning

  a plan bundle like enterprise is defined the same way, so every tenant on it
  gained the feature at the next sync

What must NOT change is the reason the fallback exists: a tenant with no
recorded list must never be locked out of what they already had. So the tests
below check both directions - the new thing is withheld, and every existing
thing still arrives.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import subscription as sub

# A feature that does not exist, injected for the length of one test. Using a
# real key would make the test pass or fail for reasons about that feature.
FAKE = "time_machine"


class OptInCase(FrappeTestCase):
	def setUp(self):
		self._features = dict(sub.FEATURES)
		self._plans = {k: list(v) for k, v in sub.PLANS.items()}
		self._default_on = list(sub.DEFAULT_ON)
		self._opt_in = list(sub.OPT_IN)

	def tearDown(self):
		sub.FEATURES.clear()
		sub.FEATURES.update(self._features)
		sub.PLANS.clear()
		sub.PLANS.update(self._plans)
		sub.DEFAULT_ON[:] = self._default_on
		sub.OPT_IN[:] = self._opt_in

	def ship_a_new_feature(self, opt_in=True):
		"""Add one to the registry, the way a release does."""
		sub.FEATURES[FAKE] = {"label": "Time Machine", "desc": "",
		                      "module_defs": ["HR"], "opt_in": opt_in}
		# Enterprise is defined as the whole product, so a release adds it here
		# too - which is exactly the leak this guards.
		for plan in ("enterprise", "custom"):
			sub.PLANS[plan] = sub.PLANS[plan] + [FAKE]
		sub.DEFAULT_ON[:] = [k for k, v in sub.FEATURES.items() if not v.get("opt_in")]
		sub.OPT_IN[:] = [k for k, v in sub.FEATURES.items() if v.get("opt_in")]


class TestANewFeatureIsOff(OptInCase):
	def test_a_site_with_no_recorded_features_does_not_get_it(self):
		"""The fallback path - and the one that would have hit every old tenant."""
		self.ship_a_new_feature()
		self.assertNotIn(FAKE, sub.enabled_features({}))

	def test_a_site_on_enterprise_does_not_get_it(self):
		"""Bought the top plan last year. Still has to be shown the new thing
		before it appears in their desk."""
		self.ship_a_new_feature()
		self.assertNotIn(FAKE, sub.enabled_features({"subscription_plan": "enterprise"}))
		self.assertNotIn(FAKE, sub.plan_features("enterprise"))

	def test_a_site_on_an_unknown_plan_does_not_get_it(self):
		"""Unknown falls back to enterprise, so it needs the same guard."""
		self.ship_a_new_feature()
		self.assertNotIn(FAKE, sub.enabled_features({"subscription_plan": "whatever"}))

	def test_it_is_reported_as_opt_in(self):
		self.ship_a_new_feature()
		self.assertTrue(sub.is_opt_in(FAKE))

	def test_a_feature_shipped_WITHOUT_the_flag_still_goes_everywhere(self):
		"""The flag has to be the thing doing the work. If a plain new feature
		were also withheld, the mechanism would be an accident of something else.
		"""
		self.ship_a_new_feature(opt_in=False)
		self.assertIn(FAKE, sub.enabled_features({}))


class TestSwitchingItOn(OptInCase):
	def test_naming_it_in_the_tenant_config_grants_it(self):
		"""One tick in the console writes the key. Explicit beats any default."""
		self.ship_a_new_feature()
		self.assertIn(FAKE, sub.enabled_features({"features": ["leaves", FAKE]}))

	def test_it_can_be_taken_away_again(self):
		self.ship_a_new_feature()
		self.assertNotIn(FAKE, sub.enabled_features({"features": ["leaves"]}))

	def test_has_feature_agrees(self):
		self.ship_a_new_feature()
		self.assertTrue(sub.has_feature(FAKE, {"features": [FAKE]}))
		self.assertFalse(sub.has_feature(FAKE, {}))


class TestNothingExistingChanged(FrappeTestCase):
	"""The fallback still has to do its old job. Locking an existing tenant out
	of something they had yesterday is a worse failure than the one being fixed.
	"""

	# Every feature that ships opt-in is named here on purpose. Adding one means
	# adding it to this list; removing the flag from an existing feature would
	# hand it to every tenant on the fallback path, which is the leak this guards.
	SHIPPED_OPT_IN = ["late_rules", "attendance_scoring", "employee_documents", "screening_forms", "policy_library"]

	def test_only_the_named_features_are_opt_in(self):
		"""If this ever fails, some existing feature just silently switched off
		for every tenant on the fallback path, or a new one leaked on."""
		self.assertEqual(sorted(sub.OPT_IN), sorted(self.SHIPPED_OPT_IN))

	def test_the_fallback_still_grants_the_whole_product(self):
		self.assertEqual(set(sub.enabled_features({})), set(sub.FEATURES) - set(self.SHIPPED_OPT_IN))

	def test_enterprise_is_still_the_whole_product(self):
		self.assertEqual(set(sub.plan_features("enterprise")), set(sub.FEATURES) - set(self.SHIPPED_OPT_IN))

	def test_required_features_are_never_withheld(self):
		for key in sub.REQUIRED:
			self.assertIn(key, sub.enabled_features({"features": []}))

	def test_an_empty_list_still_means_only_the_required_ones(self):
		self.assertEqual(set(sub.enabled_features({"features": []})), set(sub.REQUIRED))


class TestAdoption(FrappeTestCase):
	"""Something has to say a new feature is there and waiting, or it stays off
	for ever because nobody remembered it shipped."""

	TENANTS = [
		{"site_name": "a.alvoraa.co", "modules": ["leaves", "payroll"]},
		{"site_name": "b.alvoraa.co", "modules": ["leaves"]},
		{"site_name": "c.alvoraa.co", "modules": None},      # falls back
	]

	def rows(self):
		return {r["key"]: r for r in sub.feature_adoption(self.TENANTS)}

	def test_it_counts_who_actually_has_a_feature(self):
		self.assertEqual(self.rows()["payroll"]["count"], 2)   # a, and c by fallback
		self.assertIn("a.alvoraa.co", self.rows()["payroll"]["tenants"])

	def test_a_required_feature_is_held_by_everyone(self):
		self.assertEqual(self.rows()["leaves"]["count"], 3)

	def test_a_fallback_site_is_not_credited_with_an_opt_in_feature(self):
		"""It does not have it - that is the entire point of the flag."""
		saved = dict(sub.FEATURES["payroll"])
		try:
			sub.FEATURES["payroll"]["opt_in"] = True
			rows = self.rows()
			self.assertNotIn("c.alvoraa.co", rows["payroll"]["tenants"])
			self.assertEqual(rows["payroll"]["count"], 1)      # only a, explicitly
		finally:
			sub.FEATURES["payroll"] = saved

	def test_an_opt_in_feature_nobody_has_is_flagged_as_waiting(self):
		saved = dict(sub.FEATURES["vendor"])
		try:
			sub.FEATURES["vendor"]["opt_in"] = True
			rows = self.rows()
			self.assertTrue(rows["vendor"]["waiting"])
		finally:
			sub.FEATURES["vendor"] = saved

	def test_only_the_shipped_opt_in_features_are_waiting(self):
		"""None of the sample tenants has ticked them, so they show as waiting.
		Anything else waiting means a feature lost its place in a plan bundle."""
		self.assertEqual(sorted(r["key"] for r in sub.feature_adoption(self.TENANTS) if r["waiting"]),
		                 sorted(TestNothingExistingChanged.SHIPPED_OPT_IN))

	def test_no_tenants_is_not_a_crash(self):
		self.assertTrue(sub.feature_adoption([]))
		self.assertTrue(sub.feature_adoption(None))
