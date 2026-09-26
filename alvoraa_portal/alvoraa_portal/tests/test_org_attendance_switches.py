"""Late coming rules and attendance scoring: organisation switches, not features.

Surbhi, 26 Sep 2026: "Every company has their own rules so we can't have these as
features on tenant configurations ... move these to organisation settings and make
them toggleable, by default keep them off."

What this file pins, so a bad merge cannot quietly undo it:

- the admin console's registry no longer offers `late_rules` or `attendance_scoring`;
- the modules they owned are still available - Alvoraa HR Core on every plan,
  Alvoraa Late Rules wherever payroll is sold - and `sync_site` does not hide them;
- both switches are off by default and only HR reads or changes them;
- a switch the plan cannot support is refused on the server;
- off means the weekly job does nothing, nothing is scored, and the screens'
  API answers say "not enabled"; on means the behaviour from before;
- the migration patch turns a switch on for exactly the sites that had the feature.

The "on means today's behaviour" proof is mostly the existing suites -
test_late_minutes_017, test_time_api_043, hrms test_attendance_score - which now
switch the rule on for their own classes and pass unchanged.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

import hrms.alvoraa_hr_core.features as org_features
import hrms.alvoraa_late_rules.late_rules as late_rules
from hrms.alvoraa_hr_core.features import org_switch

from alvoraa_portal import hr_api
from alvoraa_portal import module_access as ma
from alvoraa_portal import subscription as sub
from alvoraa_portal.patches.v1_0 import org_attendance_switches_from_features as mig
from alvoraa_portal.patches.v1_0 import resync_access_after_attendance_switches as resync
from alvoraa_portal.tests.utils import set_org_switch

LATE_RULES_SWITCH = org_features.LATE_RULES_SWITCH
ATTENDANCE_SCORING_SWITCH = org_features.ATTENDANCE_SCORING_SWITCH

OLD_KEYS = ("late_rules", "attendance_scoring")
SWITCHES = (LATE_RULES_SWITCH, ATTENDANCE_SCORING_SWITCH)
LATE_MODULE = "Alvoraa Late Rules"
CORE_MODULE = "Alvoraa HR Core"


def _user(first, *roles):
	email = f"{first.lower()}.oas@example.com"
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": first,
		                "send_welcome_email": 0}).insert(ignore_permissions=True)
	if roles:
		frappe.get_doc("User", email).add_roles(*roles)
	return email


class _SwitchCase(FrappeTestCase):
	"""Every test starts with both switches unset, and puts them back after."""

	def setUp(self):
		frappe.set_user("Administrator")
		for key in SWITCHES:
			self.addCleanup(set_org_switch(key, ""))

	def tearDown(self):
		frappe.set_user("Administrator")


# ── 1. The registry ──────────────────────────────────────────────────────────

class TestTheConsoleNoLongerSellsThem(FrappeTestCase):
	def test_neither_key_is_in_the_registry(self):
		for key in OLD_KEYS:
			self.assertNotIn(key, sub.FEATURES)
			self.assertNotIn(key, sub.ERPNEXT_FEATURES)
			self.assertNotIn(key, sub.OPT_IN)
			self.assertEqual(sub.feature_spec(key), {})

	def test_the_admin_catalogue_does_not_offer_them(self):
		ids = {f["id"] for g in sub.get_plan_catalogue()["groups"] for f in g["features"]}
		for key in OLD_KEYS:
			self.assertNotIn(key, ids)

	def test_no_plan_bundle_and_no_requires_chain_names_them(self):
		for plan in sub.PLANS:
			for key in OLD_KEYS:
				self.assertNotIn(key, sub.plan_features(plan))
		for spec in list(sub.FEATURES.values()) + list(sub.ERPNEXT_FEATURES.values()):
			for key in OLD_KEYS:
				self.assertNotIn(key, spec.get("requires") or [])

	def test_an_old_key_left_in_site_config_grants_nothing(self):
		"""PP Jewellers' config still names both. That is harmless now."""
		feats = ["payroll", *OLD_KEYS]
		allowed = sub.allowed_module_defs(sub.enabled_features({"features": feats}))
		self.assertEqual(set(allowed), set(sub.allowed_module_defs(["payroll", *sub.REQUIRED])))

	def test_the_portal_no_longer_gets_plan_flags_for_them(self):
		frappe.set_user("Administrator")
		f = hr_api.get_available_features()
		self.assertNotIn("plan_late_rules", f)
		self.assertNotIn("plan_attendance_scoring", f)


# ── 2. Who owns the two modules now ──────────────────────────────────────────

class TestTheModulesStayAvailable(FrappeTestCase):
	def test_hr_core_is_allowed_on_every_plan(self):
		for plan in sub.PLANS:
			self.assertIn(CORE_MODULE, sub.allowed_module_defs(sub.plan_features(plan)), plan)
		# Even the bare minimum: only the required features.
		self.assertIn(CORE_MODULE, sub.allowed_module_defs(sub.enabled_features({"features": []})))

	def test_late_rules_module_follows_attendance_leaves_and_payroll(self):
		business = sub.plan_features("business")
		self.assertTrue({"attendance", "leaves", "payroll"} <= set(business))
		self.assertIn(LATE_MODULE, sub.allowed_module_defs(business))
		self.assertNotIn(LATE_MODULE, sub.blocked_module_defs(business, existing=[LATE_MODULE, CORE_MODULE]))

	def test_without_payroll_the_late_rules_module_stays_blocked(self):
		"""Deny by default still holds: starter sells no payroll."""
		starter = sub.plan_features("starter")
		blocked = sub.blocked_module_defs(starter, existing=[LATE_MODULE, CORE_MODULE])
		self.assertIn(LATE_MODULE, blocked)
		self.assertNotIn(CORE_MODULE, blocked)


class TestSyncSiteDoesNotHideThem(FrappeTestCase):
	"""The real sync, as tenant_api runs it, for a site selling attendance,
	leaves and payroll (the business plan)."""

	def test_sync_site_keeps_both_modules_and_their_doctypes(self):
		frappe.set_user("Administrator")
		# sync_site COMMITS Custom DocPerm rows; release them whatever happens.
		self.addCleanup(ma.release_permissions)
		ma.sync_site(sub.plan_features("business"))

		hidden = ma.get_hidden_modules()["profiles"]
		for profile in (ma.PROFILE_NAME, ma.HR_PROFILE_NAME):
			self.assertNotIn(LATE_MODULE, hidden[profile] or [], profile)
			self.assertNotIn(CORE_MODULE, hidden[profile] or [], profile)

		denied = set(ma.get_restricted_doctypes()["doctypes"])
		for doctype in ("Attendance Deduction Rule", "Attendance Deduction",
		                "Appraisal Cycle Exempt Grade"):
			if frappe.db.exists("DocType", doctype):
				self.assertNotIn(doctype, denied)


class TestTheResyncPatchMovesExistingTenants(FrappeTestCase):
	"""Review fix 1. A tenant synced BEFORE the move still has the old deny rows
	on Alvoraa Late Rules. The patch re-runs the sync so they follow payroll."""

	DOCTYPE = "Attendance Deduction Rule"

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(ma.release_permissions)
		self.addCleanup(frappe.set_user, "Administrator")
		self.hr = _user("MeeraOas", "HR Manager")

	def _old_deny_state(self, feats):
		"""What sync_site wrote before 26 Sep: Late Rules owned by nobody sold."""
		with patch.dict(sub.FEATURES["payroll"], {"module_defs": ["Payroll"]}):
			ma.sync_site(feats)
		self.assertIn(self.DOCTYPE, ma.get_restricted_doctypes()["doctypes"])

	def _hr_can_read(self):
		frappe.clear_cache(doctype=self.DOCTYPE)
		return frappe.has_permission(self.DOCTYPE, "read", user=self.hr)

	def test_payroll_tenant_gets_the_rule_back(self):
		business = sub.plan_features("business")
		self._old_deny_state(business)
		self.assertFalse(self._hr_can_read(), "the old state really denied it")
		with patch.dict(frappe.conf, {"features": business}):
			self.assertTrue(resync.should_resync())
			resync.execute()
		self.assertNotIn(self.DOCTYPE, ma.get_restricted_doctypes()["doctypes"])
		self.assertTrue(self._hr_can_read())

	def test_tenant_without_payroll_stays_denied(self):
		starter = sub.plan_features("starter")
		self._old_deny_state(starter)
		with patch.dict(frappe.conf, {"features": starter}):
			resync.execute()
			resync.execute()     # twice: same state
		self.assertIn(self.DOCTYPE, ma.get_restricted_doctypes()["doctypes"])
		self.assertFalse(self._hr_can_read())

	def test_a_site_never_synced_is_left_alone(self):
		ma.release_permissions()
		self.assertFalse(resync.should_resync())
		with patch.object(ma, "sync_site", side_effect=AssertionError("synced")):
			resync.execute()

	def test_the_control_plane_is_left_alone(self):
		self._old_deny_state(sub.plan_features("business"))
		with patch.dict(frappe.conf, {"alvoraa_control_plane": 1}):
			self.assertFalse(resync.should_resync())

	def test_a_failed_sync_is_logged_and_does_not_stop_the_migrate(self):
		self._old_deny_state(sub.plan_features("business"))
		with patch.object(ma, "sync_site", side_effect=RuntimeError("boom")), \
		     patch("frappe.log_error") as logged:
			resync.execute()
		self.assertEqual(logged.call_args.kwargs["title"],
		                 "module_access: resync after attendance switches failed")


# ── 3. The switches themselves ───────────────────────────────────────────────

class TestTheSwitchesDefaultOff(_SwitchCase):
	def test_unset_is_off(self):
		for key in SWITCHES:
			self.assertFalse(org_switch(key))

	def test_anything_but_one_is_off_and_an_unknown_key_is_off(self):
		frappe.db.set_default(LATE_RULES_SWITCH, "yes")
		self.assertFalse(org_switch(LATE_RULES_SWITCH))
		self.assertFalse(org_switch("kra_link_mandatory"))

	def test_the_portal_sees_them_off(self):
		f = hr_api.get_available_features()
		self.assertIs(f["org_late_rules"], False)
		self.assertIs(f["org_attendance_scoring"], False)

	def test_the_portal_sees_them_on_once_hr_turns_them_on(self):
		for key in SWITCHES:
			frappe.db.set_default(key, "1")
		f = hr_api.get_available_features()
		self.assertIs(f["org_late_rules"], True)
		self.assertIs(f["org_attendance_scoring"], True)


class TestOnlyHrReadsAndChangesThem(_SwitchCase):
	def setUp(self):
		super().setUp()
		self.hr = _user("PriyaOas", "HR Manager")
		self.employee = _user("RaviOas", "Employee")

	def test_hr_sets_and_reads_both(self):
		frappe.set_user(self.hr)
		with patch("alvoraa_portal.subscription.has_feature", return_value=True), \
		     patch.object(hr_api, "_open_cycles_using_attendance", return_value=[]):
			for key in SWITCHES:
				self.assertEqual(hr_api.set_org_setting(key, "1"), {"ok": True})
				self.assertEqual(hr_api.get_org_setting(key), "1")
				self.assertTrue(org_switch(key))
				self.assertEqual(hr_api.set_org_setting(key, "0"), {"ok": True})
				self.assertFalse(org_switch(key))

	def test_an_employee_is_refused_both_ways(self):
		frappe.set_user(self.employee)
		for key in SWITCHES:
			with self.assertRaises(frappe.PermissionError):
				hr_api.set_org_setting(key, "1")
			with self.assertRaises(frappe.PermissionError):
				hr_api.get_org_setting(key)
		with self.assertRaises(frappe.PermissionError):
			hr_api.get_attendance_rule_switches()
		frappe.set_user("Administrator")
		for key in SWITCHES:
			self.assertFalse(org_switch(key))

	def test_only_zero_and_one_are_accepted(self):
		frappe.set_user(self.hr)
		for bad in ("2", "true", "on", " 1"):
			with self.assertRaises(frappe.PermissionError):
				hr_api.set_org_setting(LATE_RULES_SWITCH, bad)

	def test_the_card_lists_both_switches_for_hr(self):
		frappe.set_user(self.hr)
		with patch("alvoraa_portal.subscription.has_feature", return_value=True):
			res = hr_api.get_attendance_rule_switches()
		rows = {r["key"]: r for r in res["switches"]}
		self.assertEqual(set(rows), set(SWITCHES))
		for r in rows.values():
			self.assertIs(r["on"], False)
			self.assertIs(r["available"], True)
			self.assertEqual(r["needs"], [])


# ── 4. Prerequisites ─────────────────────────────────────────────────────────

class TestPrerequisitesAreEnforced(_SwitchCase):
	def setUp(self):
		super().setUp()
		self.hr = _user("PriyaOas", "HR Manager")

	@staticmethod
	def _without(*unsold):
		return patch("alvoraa_portal.subscription.has_feature", side_effect=lambda f, conf=None: f not in unsold)

	def test_late_rules_refused_without_payroll(self):
		frappe.set_user(self.hr)
		with self._without("payroll"):
			with self.assertRaises(frappe.ValidationError) as ctx:
				hr_api.set_org_setting(LATE_RULES_SWITCH, "1")
			self.assertIn("Payroll", str(ctx.exception))
			res = {r["key"]: r for r in hr_api.get_attendance_rule_switches()["switches"]}
		self.assertFalse(org_switch(LATE_RULES_SWITCH))
		self.assertIs(res[LATE_RULES_SWITCH]["available"], False)
		self.assertEqual(res[LATE_RULES_SWITCH]["needs"], ["Payroll"])

	def test_attendance_scoring_refused_without_performance(self):
		frappe.set_user(self.hr)
		with self._without("performance"):
			with self.assertRaises(frappe.ValidationError):
				hr_api.set_org_setting(ATTENDANCE_SCORING_SWITCH, "1")
		self.assertFalse(org_switch(ATTENDANCE_SCORING_SWITCH))

	def test_switching_off_is_always_allowed(self):
		"""A tenant that loses payroll must still be able to turn the rule off."""
		frappe.db.set_default(LATE_RULES_SWITCH, "1")
		frappe.set_user(self.hr)
		with self._without("payroll", "performance"):
			self.assertEqual(hr_api.set_org_setting(LATE_RULES_SWITCH, "0"), {"ok": True})
		self.assertFalse(org_switch(LATE_RULES_SWITCH))


class TestScoringCannotBeSwitchedOffUnderAnOpenCycle(_SwitchCase):
	"""Review fix 2. An open cycle that counts attendance would break: its
	formula keeps a stale score and completing it saves the cycle, which the
	switched-off check refuses. So switching off waits until it is finished."""

	CYCLE = "OAS Open Attendance Cycle"

	def setUp(self):
		super().setUp()
		self.hr = _user("PriyaOas", "HR Manager")
		frappe.db.set_default(ATTENDANCE_SCORING_SWITCH, "1")
		self.addCleanup(self._drop_cycle)
		self._drop_cycle()
		company = frappe.get_all("Company", pluck="name", limit=1)[0]
		cycle = frappe.get_doc({
			"doctype": "Appraisal Cycle", "cycle_name": self.CYCLE, "company": company,
			"start_date": "2026-04-01", "end_date": "2026-09-30",
			"include_attendance_score": 1, "goal_weight": 50, "feedback_weight": 30,
			"attendance_weight": 20, "attendance_reliability_weight": 60,
			"attendance_punctuality_weight": 40,
		})
		cycle.insert(ignore_permissions=True, ignore_mandatory=True)
		self.cycle = cycle.name

	def _drop_cycle(self):
		frappe.set_user("Administrator")
		for name in frappe.get_all("Appraisal Cycle", filters={"cycle_name": self.CYCLE}, pluck="name"):
			frappe.delete_doc("Appraisal Cycle", name, force=True, ignore_permissions=True)
		frappe.db.commit()

	def test_refused_while_the_cycle_is_open_and_the_cycle_is_named(self):
		frappe.set_user(self.hr)
		with self.assertRaises(frappe.ValidationError) as ctx:
			hr_api.set_org_setting(ATTENDANCE_SCORING_SWITCH, "0")
		self.assertIn("Finish or change these appraisal cycles first", str(ctx.exception))
		self.assertIn(self.cycle, str(ctx.exception))
		self.assertTrue(org_switch(ATTENDANCE_SCORING_SWITCH))

	def test_allowed_once_the_cycle_is_completed(self):
		frappe.db.set_value("Appraisal Cycle", self.cycle, "status", "Completed")
		frappe.set_user(self.hr)
		self.assertEqual(hr_api.set_org_setting(ATTENDANCE_SCORING_SWITCH, "0"), {"ok": True})
		self.assertFalse(org_switch(ATTENDANCE_SCORING_SWITCH))

	def test_allowed_once_the_cycle_stops_counting_attendance(self):
		frappe.db.set_value("Appraisal Cycle", self.cycle, "include_attendance_score", 0)
		frappe.set_user(self.hr)
		self.assertEqual(hr_api.set_org_setting(ATTENDANCE_SCORING_SWITCH, "0"), {"ok": True})

	def test_late_rules_are_not_held_by_cycles(self):
		frappe.db.set_default(LATE_RULES_SWITCH, "1")
		frappe.set_user(self.hr)
		self.assertEqual(hr_api.set_org_setting(LATE_RULES_SWITCH, "0"), {"ok": True})


# ── 5. Off means nothing happens; on means what happened before ──────────────

class TestOffMeansNothingHappens(_SwitchCase):
	def _run_scheduler(self):
		with patch.object(late_rules, "process_week") as process_week, \
		     patch("frappe.get_all", return_value=["OAS Rule"]), \
		     patch("frappe.get_doc", return_value=frappe._dict(name="OAS Rule", week_start_day="Monday")):
			result = late_rules.process_previous_week()
		return result, process_week

	def test_the_weekly_job_does_nothing_when_off(self):
		result, process_week = self._run_scheduler()
		process_week.assert_not_called()
		self.assertEqual(result, {"skipped": "late rules are switched off"})

	def test_the_weekly_job_runs_every_rule_when_on(self):
		frappe.db.set_default(LATE_RULES_SWITCH, "1")
		_result, process_week = self._run_scheduler()
		process_week.assert_called_once()

	def test_hr_catch_up_run_is_refused_when_off(self):
		with self.assertRaises(frappe.ValidationError) as ctx:
			late_rules.run_for_range("Any Rule", "2026-09-01", "2026-09-07")
		self.assertIn("Organisation Settings", str(ctx.exception))

	def test_no_rule_reaches_any_screen_when_off(self):
		"""Off: the rule lookup behind every late screen answers None without
		even asking the database, so each screen reports "not enabled"."""
		with patch.object(hr_api.frappe.db, "exists", side_effect=AssertionError("queried")):
			self.assertIsNone(hr_api._late_rule_for("HR-EMP-OAS"))

	def test_screens_answer_not_enabled_when_off(self):
		emp = frappe._dict(name="HR-EMP-OAS")
		with patch.object(hr_api, "_get_employee", return_value=emp):
			self.assertEqual(hr_api.get_my_attendance_deductions(),
			                 {"enabled": False, "rows": [], "this_week": None})

	def test_the_time_tab_is_hidden_when_off_and_shown_when_on(self):
		from alvoraa_portal.time_api import _rule_explained

		emp = frappe._dict(name="HR-EMP-OAS")
		off = _rule_explained(emp)
		self.assertIs(off["switched_on"], False)
		self.assertIs(off["covered"], False)
		frappe.db.set_default(LATE_RULES_SWITCH, "1")
		with patch.object(hr_api, "_late_rule_for", return_value=None):
			on = _rule_explained(emp)
		self.assertIs(on["switched_on"], True)

	def test_the_lookup_asks_the_database_again_when_on(self):
		frappe.db.set_default(LATE_RULES_SWITCH, "1")
		with patch.object(hr_api.frappe.db, "exists", return_value=False) as exists:
			self.assertIsNone(hr_api._late_rule_for("HR-EMP-OAS"))
		exists.assert_called()

	def test_the_cycle_wizard_ignores_attendance_when_off(self):
		from alvoraa_portal.performance_api import _apply_scoring

		cycle = frappe._dict(include_attendance_score=0)
		_apply_scoring(cycle, {"include_attendance": 1, "attendance_weight": 20})
		self.assertEqual(cycle.include_attendance_score, 0)

		frappe.db.set_default(ATTENDANCE_SCORING_SWITCH, "1")
		cycle = frappe._dict(include_attendance_score=0)
		cycle.set = cycle.__setitem__
		_apply_scoring(cycle, {"include_attendance": 1, "attendance_weight": 20})
		self.assertEqual(cycle.include_attendance_score, 1)
		self.assertEqual(cycle.attendance_weight, 20)


# ── 6. The migration patch ───────────────────────────────────────────────────

class TestThePatchTurnsOnExactlyTheSitesThatHadThem(_SwitchCase):
	def _state(self):
		return {key: org_switch(key) for key in SWITCHES}

	def test_a_site_that_named_both_gets_both(self):
		mig.execute({"features": ["payroll", "performance", "late_rules", "attendance_scoring"]})
		self.assertEqual(self._state(), {LATE_RULES_SWITCH: True, ATTENDANCE_SCORING_SWITCH: True})

	def test_a_site_that_named_one_gets_one(self):
		mig.execute({"features": ["payroll", "late_rules"]})
		self.assertEqual(self._state(), {LATE_RULES_SWITCH: True, ATTENDANCE_SCORING_SWITCH: False})

	def test_a_site_that_named_neither_gets_neither(self):
		for conf in ({"features": ["payroll", "performance"]}, {"features": []}, {},
		             {"subscription_plan": "enterprise"}, {"subscription_plan": "custom"}):
			mig.execute(conf)
			self.assertEqual(self._state(), {k: False for k in SWITCHES}, conf)

	def test_a_value_hr_already_set_is_left_alone(self):
		frappe.db.set_default(LATE_RULES_SWITCH, "0")
		mig.execute({"features": ["late_rules", "attendance_scoring"]})
		self.assertEqual(self._state(), {LATE_RULES_SWITCH: False, ATTENDANCE_SCORING_SWITCH: True})

	def test_running_it_twice_changes_nothing(self):
		conf = {"features": ["late_rules"]}
		mig.execute(conf)
		mig.execute(conf)
		self.assertEqual(self._state(), {LATE_RULES_SWITCH: True, ATTENDANCE_SCORING_SWITCH: False})

	def test_it_is_registered(self):
		import os

		path = os.path.join(frappe.get_app_path("alvoraa_portal"), "patches.txt")
		with open(path, encoding="utf-8") as fh:
			lines = [line.strip() for line in fh]
		self.assertIn("alvoraa_portal.patches.v1_0.org_attendance_switches_from_features", lines)
