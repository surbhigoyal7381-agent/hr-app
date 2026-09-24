"""Slice 034, Wave 1: `frame_api.get_frame` - what it answers, and to whom.

Three things are pinned here, and each has cost somebody something before:

**SEC-12 / AC-46 - the fixed key list.** `get_portal_context` hands the browser
the whole Employee record and the whole role list. Date of birth, gender, phone
number, joining date, manager and branch were on every portal page, in every
screenshot and in every browser error report, to draw a menu that needs none of
them. The test walks the payload for every persona and fails if any of those
words appear anywhere in it, at any depth.

**AC-8 - the same answers as the three old calls.** `get_frame` replaces
`get_portal_context`, `get_available_features` and `get_switch_target`. If it
ever disagrees with them, one of the two menus is wrong.

**AC-10, AC-11, AC-47, AC-63 - the persona rules.** Rules 1 to 5 need an ACTIVE
Employee record. Without that line a platform operator is a System Manager, so
`is_hr` is true and `has_reports` is false, she matches rule 2, and she is given
a Time button with nothing behind it. AC-10 and AC-63 could not both be true.

Guest, wrong-persona and scope cases ship in this same commit, because the
preview page is not a data control: every function here is live on production
from the release that carries it, whatever page calls it (SEC-2 / M2).

Synthetic people only, tagged S030 and S034.
"""

import json

import frappe

from alvoraa_portal import frame_api, hr_api
from alvoraa_portal.module_access import get_switch_target
from alvoraa_portal.tests.leave_fixtures import ensure_user
from alvoraa_portal.tests.test_store_hr_scoping_030 import _Stores
import alvoraa_portal.subscription as sub

# SEC-12 names these. Not one of them may appear in the payload, at any depth.
NEVER = ("date_of_birth", "gender", "cell_number", "date_of_joining", "reports_to", "branch")


class _Personas(_Stores):
	"""Slice 030's two stores, plus the two people the frame rules turn on.

	Asha is a System Manager with NO Employee record - a platform operator. The
	leaver is a manager whose Employee is Left and whose login still works; his
	reports have not been moved. Both must reach persona rule 6.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from alvoraa_portal.tests.test_portal_security_010 import _employee

		cls.asha_user = ensure_user("s034.asha@example.com", roles=("System Manager",))
		frappe.db.set_value("User", cls.asha_user, "module_profile", None, update_modified=False)
		frappe.db.delete("Block Module", {"parent": cls.asha_user, "parenttype": "User"})

		cls.leaver_user = ensure_user("s034.leaver@example.com", roles=("Employee",))
		cls.leaver = _employee("S034Leaver", company=cls.company_a, user=cls.leaver_user)
		cls.leaver_report = _employee("S034LeaverReport", company=cls.company_a, reports_to=cls.leaver)
		frappe.db.set_value("Employee", cls.leaver, "status", "Left", update_modified=False)
		frappe.clear_cache()
		frappe.db.commit()

	def setUp(self):
		super().setUp()
		# The review fixtures this class is built on patch
		# `subscription.has_feature` to return True for everything
		# (`_ReviewBase.setUp`), because a review test should not fail over a
		# plan. These tests are ABOUT the plan - which buttons a tenant's
		# entitlement produces - so the patch is stopped here and started again
		# in tearDown, where the base class expects to stop it itself.
		#
		# Without this, every `_sell()` below is silently ignored and five bar
		# tests pass or fail for a reason that is not in the code. That is
		# exactly what happened on the first run.
		self._plan.stop()
		self._saved_features = frappe.conf.get("features")
		self._clear_context_caches()

	def tearDown(self):
		frappe.set_user("Administrator")
		if self._saved_features is None:
			frappe.conf.pop("features", None)
		else:
			frappe.conf["features"] = self._saved_features
		self._clear_context_caches()
		# Put the patch back so `_ReviewBase.tearDown`'s stop() has something to
		# stop; stopping it twice raises.
		self._plan.start()
		super().tearDown()


	def _clear_context_caches(self):
		"""`get_portal_context` is cached per user for an hour, and the static
		half of `get_available_features` is cached for the whole site. A test
		that changed the plan and then read a stale cache would pass or fail for
		a reason that is not in the code."""
		for user in (self.subject_user, self.manager_user, self.hr_user, self.hr_boss_user,
		             self.sysman_user, self.store_hr_user, self.asha_user, self.leaver_user):
			try:
				frappe.cache().delete_value(f"portal_ctx_{user}")
			except Exception:
				pass
		try:
			frappe.cache().delete_value("portal_features_global")
		except Exception:
			pass

	def _sell(self, *keys):
		"""Give this site exactly these features (plus the required ones)."""
		frappe.conf["features"] = list(keys)
		self._clear_context_caches()

	def _frame_as(self, user):
		self._as(user)
		return frame_api.get_frame()


class TestWhoMayCallIt(_Personas):
	def test_the_plan_patch_really_is_off_in_this_file(self):
		"""The fixtures this file inherits force every plan feature on. This
		file switches that off in setUp. If this check ever fails, every
		feature and bottom-bar test below is meaningless."""
		self._sell()
		self.assertFalse(sub.has_feature("goals"))
		self._sell("goals")
		self.assertTrue(sub.has_feature("goals"))

	def test_guest_is_refused(self):
		"""SEC-6. get_portal_context allows guests; this call must not inherit that."""
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			frame_api.get_frame()

	def test_it_is_whitelisted_but_not_for_guests(self):
		"""frappe.whitelisted and frappe.guest_methods are sets of the functions
		themselves (frappe 16.33.1, frappe/__init__.py:423). Being in the first
		and not the second is what "signed-in callers only" actually means."""
		self.assertIn(frame_api.get_frame, frappe.whitelisted)
		self.assertNotIn(frame_api.get_frame, frappe.guest_methods)


class TestTheKeyListIsFixed(_Personas):
	def test_every_persona_gets_exactly_the_named_keys(self):
		"""AC-46. The same key set for everybody - only the values differ."""
		for user in (self.subject_user, self.manager_user, self.hr_user, self.store_hr_user,
		             self.sysman_user, self.asha_user, self.leaver_user):
			frame = self._frame_as(user)
			self.assertEqual(set(frame), set(frame_api.FRAME_KEYS), msg=user)

	def test_the_caller_block_carries_six_fields_and_no_more(self):
		frame = self._frame_as(self.subject_user)
		self.assertEqual(set(frame["me"]), set(frame_api.ME_FIELDS))

	def test_nothing_personal_beyond_those_six_reaches_the_browser(self):
		"""AC-46 / US-17, checked at every depth rather than on the top level."""
		for user in (self.subject_user, self.manager_user, self.hr_user, self.store_hr_user,
		             self.sysman_user, self.asha_user, self.leaver_user):
			blob = json.dumps(self._frame_as(user), default=str)
			for banned in NEVER:
				self.assertNotIn(banned, blob, msg=f"{banned} reached {user}")

	def test_the_full_role_list_is_not_sent(self):
		"""Four booleans, not the roles themselves (SEC-12)."""
		frame = self._frame_as(self.hr_user)
		self.assertNotIn("roles", frame)
		self.assertNotIn("HR Manager", json.dumps(frame, default=str))
		for key in ("is_hr", "is_manager", "is_system_manager", "is_control_plane"):
			self.assertIsInstance(frame[key], bool, msg=key)

	def test_a_new_field_cannot_slip_out_through_the_builder(self):
		"""The payload is filtered through FRAME_KEYS on the way out, so adding
		a field inside get_frame is not enough to ship it."""
		self.assertNotIn("manager_name", frame_api.FRAME_KEYS)
		self.assertNotIn("manager_name", self._frame_as(self.subject_user))


class TestItAgreesWithTheThreeOldCalls(_Personas):
	def test_roles_features_and_the_switch_target_match(self):
		"""AC-8, for each of the seven personas the spec names."""
		for user in (self.subject_user, self.manager_user, self.hr_user, self.store_hr_user,
		             self.sysman_user, self.asha_user, self.leaver_user):
			frame = self._frame_as(user)
			context = hr_api.get_portal_context()
			self.assertEqual(frame["is_hr"], bool(context["is_hr"]), msg=user)
			self.assertEqual(frame["is_manager"], bool(context["is_manager"]), msg=user)
			self.assertEqual(frame["is_system_manager"], bool(context["is_system_manager"]), msg=user)
			self.assertEqual(frame["is_control_plane"], bool(context["is_control_plane"]), msg=user)
			self.assertEqual(frame["features"], hr_api.get_available_features(), msg=user)
			self.assertEqual(frame["switch_target"], get_switch_target(), msg=user)

	def test_the_hr_review_badge_still_comes_from_with_review_count(self):
		"""AC-9c. HR gets the number; nobody else gets the key filled in."""
		frame = self._frame_as(self.hr_user)
		self.assertEqual(frame["review_open_count"], hr_api.get_portal_context().get("review_open_count"))
		self.assertIsNone(self._frame_as(self.subject_user)["review_open_count"])


class TestTheDeskLink(_Personas):
	"""AC-75 / W1D-19. The prototype offered every manager a desk link. The code
	never did, and the code was right - so the labels are asserted word for word
	and Sandeep's "no link at all" is a test, not a comment."""

	def test_hr_gets_hr_core_and_a_system_manager_gets_admin(self):
		self.assertEqual(self._frame_as(self.store_hr_user)["switch_target"],
		                 {"label": "Switch to HR Core", "url": "/app/hr"})
		self.assertEqual(self._frame_as(self.sysman_user)["switch_target"],
		                 {"label": "Switch to Admin", "url": "/app"})

	def test_somebody_who_is_both_gets_admin(self):
		frappe.set_user("Administrator")
		user = ensure_user("s034.hrsysman@example.com", roles=("HR Manager", "System Manager", "Employee"))
		frappe.db.commit()
		self.assertEqual(self._frame_as(user)["switch_target"],
		                 {"label": "Switch to Admin", "url": "/app"})

	def test_a_plain_manager_gets_no_link_at_all(self):
		"""Sandeep: 19 direct reports, no HR role, not a System Manager."""
		frame = self._frame_as(self.manager_user)
		self.assertTrue(frame["has_reports"])
		self.assertIsNone(frame["switch_target"])


class TestThePersonaRules(_Personas):
	def test_rule_six_needs_no_active_employee_record(self):
		"""AC-63 with AC-10. Asha is a System Manager, so is_hr is true - and she
		still reaches rule 6, because rules 1 to 5 need an Active Employee."""
		frame = self._frame_as(self.asha_user)
		self.assertTrue(frame["is_hr"])
		self.assertFalse(frame["has_employee"])
		self.assertIsNone(frame["me"])
		self.assertEqual(frame["persona_rule"], 6)
		self.assertNotIn("time", frame["bottom_bar"])
		self.assertNotIn("time", frame["allowed_pages"])
		self.assertFalse(frame["show_team"])

	def test_a_leaver_with_a_live_login_reaches_rule_six_too(self):
		"""AC-68 / SEC-14. His reports have not moved, so today's is_manager
		would still call him a manager. The Active-record test is what stops it."""
		frame = self._frame_as(self.leaver_user)
		self.assertFalse(frame["has_employee"])
		self.assertEqual(frame["persona_rule"], 6)
		self.assertFalse(frame["has_reports"])
		self.assertFalse(frame["show_team"])

	def test_hr_with_reports_is_rule_one_and_hr_without_reports_is_rule_two(self):
		self.assertEqual(self._frame_as(self.hr_boss_user)["persona_rule"], 1)
		self.assertEqual(self._frame_as(self.hr_user)["persona_rule"], 2)

	def test_hr_without_reports_still_gets_the_team_group(self):
		"""AC-47, changed by W1D-20. It used to be "no reports, no Team"."""
		frame = self._frame_as(self.store_hr_user)
		self.assertFalse(frame["has_reports"])
		self.assertTrue(frame["show_team"])
		self.assertIn("team", frame["bottom_bar"])

	def test_has_reports_is_not_todays_is_manager(self):
		"""AC-47. `is_manager` is also true for an HR user when anybody in the
		tenant has no manager. `has_reports` asks the real question."""
		self._as(self.hr_user)
		context = hr_api.get_portal_context()
		frame = frame_api.get_frame()
		self.assertFalse(frame["has_reports"])
		self.assertEqual(frame["is_manager"], bool(context["is_manager"]))
		self.assertEqual(
			frame["has_reports"],
			frappe.db.count("Employee", {"reports_to": frame["me"]["employee"], "status": "Active"}) > 0,
		)

	def test_a_manager_who_is_not_hr_is_rule_three(self):
		frame = self._frame_as(self.manager_user)
		self.assertFalse(frame["is_hr"])
		self.assertTrue(frame["has_reports"])
		self.assertEqual(frame["persona_rule"], 3)

	def test_an_employee_is_rule_four_with_payroll_and_rule_five_without(self):
		self._sell("payroll", "goals")
		self.assertEqual(self._frame_as(self.subject_user)["persona_rule"], 4)
		self._sell("goals")
		self.assertEqual(self._frame_as(self.subject_user)["persona_rule"], 5)


class TestTheBottomBar(_Personas):
	"""AC-11's five named cases, exactly as the spec writes them."""

	def test_rahul_with_payroll_and_no_goals_app(self):
		self._sell("payroll")
		self.assertEqual(self._frame_as(self.subject_user)["bottom_bar"],
		                 ["home", "time", "pay", "inbox"])

	def test_rahul_with_neither_payroll_nor_goals(self):
		"""Pay still exists, because Expenses is required on every plan."""
		self._sell()
		self.assertEqual(self._frame_as(self.subject_user)["bottom_bar"],
		                 ["home", "time", "inbox", "pay"])

	def test_asha_gets_three_buttons_not_four(self):
		"""When fewer than four pages are allowed the bar is shorter. It never
		pads itself with a button that opens a refusal."""
		self._sell()
		self.assertEqual(self._frame_as(self.asha_user)["bottom_bar"],
		                 ["home", "inbox", "company"])

	def test_priya_store_hr_with_no_reports(self):
		self._sell("goals", "payroll")
		self.assertEqual(self._frame_as(self.store_hr_user)["bottom_bar"],
		                 ["home", "inbox", "company", "team"])

	def test_sandeep_the_manager(self):
		self._sell("goals", "payroll")
		self.assertEqual(self._frame_as(self.manager_user)["bottom_bar"],
		                 ["home", "team", "inbox", "time"])

	def test_the_bar_never_offers_a_page_the_person_may_not_open(self):
		for keys in ((), ("goals",), ("payroll",), ("goals", "payroll", "policy_library", "org_structure")):
			self._sell(*keys)
			for user in (self.subject_user, self.manager_user, self.hr_user,
			             self.store_hr_user, self.asha_user, self.leaver_user):
				frame = self._frame_as(user)
				self.assertLessEqual(len(frame["bottom_bar"]), 4, msg=user)
				self.assertEqual(len(set(frame["bottom_bar"])), len(frame["bottom_bar"]), msg=user)
				for page in frame["bottom_bar"]:
					self.assertIn(page, frame["allowed_pages"], msg=f"{user} / {keys} / {page}")


class TestWhatEachPersonaMayOpen(_Personas):
	def test_growth_needs_the_goals_feature(self):
		self._sell("goals")
		self.assertIn("growth", self._frame_as(self.subject_user)["allowed_pages"])
		self._sell("payroll")
		self.assertNotIn("growth", self._frame_as(self.subject_user)["allowed_pages"])

	def test_time_pay_and_growth_need_an_employee_record(self):
		"""AC-63: Asha is offered none of them, on the richest plan there is."""
		self._sell(*[k for k, v in sub.FEATURES.items() if not v.get("required")])
		allowed = self._frame_as(self.asha_user)["allowed_pages"]
		for page in ("time", "pay", "growth", "team"):
			self.assertNotIn(page, allowed, msg=page)
		self.assertEqual(allowed, ["home", "inbox", "company"])

	def test_a_plain_employee_gets_company_only_when_the_tenant_bought_something_in_it(self):
		self._sell()
		self.assertNotIn("company", self._frame_as(self.subject_user)["allowed_pages"])
		self._sell("policy_library")
		self.assertIn("company", self._frame_as(self.subject_user)["allowed_pages"])
		self._sell("org_structure")
		self.assertIn("company", self._frame_as(self.subject_user)["allowed_pages"])

	def test_the_staff_list_switch_opens_the_group_for_a_plain_employee(self):
		"""**045: this behaviour turns over, and it needs its own pin.**

		Until 24 September 2026 `plan_staff_list` deliberately did NOT open the
		Company group for a non-HR caller, because `get_staff_list` refused
		them - opening it would have offered a group whose only new entry then
		refused. Surbhi opened the directory to employees, so that reason has
		gone and the group has to open, or the server allows a screen the frame
		never offers.

		**This test exists because removing the menu entry's own `is_hr` made
		no difference at all** - `allowed_pages` was a second gate in front of
		it and the jsdom assertion stayed green. A guard you can remove with
		nothing going red is not the guard doing the work.
		"""
		self._sell()
		self.assertNotIn("company", self._frame_as(self.subject_user)["allowed_pages"],
		                 "with nothing sold, a plain employee has no Company group")
		self._sell("staff_list")
		self.assertIn("company", self._frame_as(self.subject_user)["allowed_pages"],
		              "the staff-list switch did not open the Company group for "
		              "a plain employee, so the directory is unreachable for them")

	def test_hr_always_has_the_company_group(self):
		"""Org settings is HR's on every tenant, whatever the plan says."""
		self._sell()
		for user in (self.hr_user, self.store_hr_user, self.sysman_user, self.asha_user):
			self.assertIn("company", self._frame_as(user)["allowed_pages"], msg=user)


class TestTheSaveSettingsFlagMatchesTheServer(_Personas):
	"""AC-67 / W1D-03. A flag that says "yes" where the endpoint says "no" is a
	Save button that refuses - which is the exact thing this replaces. So the
	flag is not tested against a rule written twice; it is tested against the
	real endpoint, for every persona."""

	def _try_to_save(self):
		"""Call the real endpoint and put the setting back exactly as it was, so
		a test about permissions does not quietly change the site."""
		before = frappe.db.get_default("kra_link_mandatory")
		try:
			hr_api.set_org_setting("kra_link_mandatory", before if before in ("0", "1") else "0")
			return True
		except frappe.PermissionError:
			return False
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_default("kra_link_mandatory", before or "")
			frappe.db.commit()

	def test_the_flag_and_the_endpoint_agree_for_every_persona(self):
		for user in (self.subject_user, self.manager_user, self.hr_user,
		             self.store_hr_user, self.sysman_user, self.asha_user):
			frame = self._frame_as(user)
			self.assertEqual(frame["may_save_settings"], self._try_to_save(), msg=user)

	def test_store_hr_may_not_save_and_company_wide_hr_may(self):
		self.assertFalse(self._frame_as(self.store_hr_user)["may_save_settings"])
		self.assertTrue(self._frame_as(self.hr_user)["may_save_settings"])

	def test_a_plain_employee_and_a_plain_manager_may_not(self):
		self.assertFalse(self._frame_as(self.subject_user)["may_save_settings"])
		self.assertFalse(self._frame_as(self.manager_user)["may_save_settings"])
