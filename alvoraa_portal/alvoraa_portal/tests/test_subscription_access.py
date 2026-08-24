"""What a subscription actually grants — plan by plan, front and back.

The existing suites test the registry (test_subscription) and the Module Profile
(test_module_access) in pieces. This one asserts the WHOLE picture for each plan
at once, because that is how the product is sold and how it broke: every
individual fact was correct while a live tenant on a custom plan still showed
Payroll and Recruitment in its desk, its Module Profile blocked 0 modules, and
its stored feature list was missing all five required features.

Three surfaces decide what a tenant can reach:

    Module Profile  -> User.block_modules   hides MODULES from the desk
    Workspace       -> is_hidden            hides WORKSPACES from the desk
    App install     -> doctypes absent      the only real denial we have

Roles are the fourth and the only true boundary. They are not applied yet, and
the tests at the bottom say so out loud rather than leaving a reader to assume
the product is enforced when it is not.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import module_access as ma
from alvoraa_portal import subscription as sub

# The ladder, stated once. Written from measured behaviour, not from the source,
# so a change to the source has to be a deliberate change here too.
PLAN_MATRIX = {
	"starter": {
		"features": ["portal", "leaves", "attendance", "expenses", "hr_setup"],
		"workspaces": ["Expenses", "HR Setup", "Leaves", "Shift & Attendance"],
		"apps": ["alvoraa_portal"],
		"modules_blocked": ["Payroll", "Performance Management", "Alvoraa Goals"],
		"modules_visible": ["HR"],
	},
	"business": {
		"features": ["portal", "leaves", "attendance", "expenses", "hr_setup",
		             "tenure", "recruitment", "payroll", "tax_benefits"],
		"workspaces": ["Expenses", "HR Setup", "Leaves", "Payroll", "Recruitment",
		               "Shift & Attendance", "Tax & Benefits", "Tenure"],
		"apps": ["alvoraa_portal"],
		"modules_blocked": ["Performance Management", "Alvoraa Goals"],
		"modules_visible": ["HR", "Payroll"],
	},
	"enterprise": {
		"features": ["portal", "leaves", "attendance", "expenses", "hr_setup",
		             "tenure", "recruitment", "payroll", "tax_benefits",
		             "performance", "goals", "analytics", "vendor"],
		"workspaces": ["Expenses", "HR Setup", "Leaves", "Payroll", "Performance",
		               "Recruitment", "Shift & Attendance", "Tax & Benefits", "Tenure"],
		"apps": ["alvoraa_goals", "alvoraa_portal"],
		"modules_blocked": [],
		"modules_visible": ["HR", "Payroll", "Performance Management", "Alvoraa Goals"],
	},
}


class TestPlanMatrix(FrappeTestCase):
	"""Every plan, every surface, in one place."""

	def test_features_match_the_ladder(self):
		for plan, want in PLAN_MATRIX.items():
			self.assertEqual(sub.plan_features(plan), want["features"], plan)

	def test_workspaces_match_the_ladder(self):
		for plan, want in PLAN_MATRIX.items():
			show, _hide = sub.sold_and_unsold_workspaces(sub.plan_features(plan))
			self.assertEqual(show, sorted(want["workspaces"]), plan)

	def test_everything_not_shown_is_hidden(self):
		"""No workspace may fall between the two lists and simply linger."""
		declared = {w for s in sub.FEATURES.values() for w in (s.get("workspaces") or [])}
		for plan in PLAN_MATRIX:
			show, hide = sub.sold_and_unsold_workspaces(sub.plan_features(plan))
			self.assertEqual(set(show) | set(hide), declared, plan)

	def test_apps_match_the_ladder(self):
		for plan, want in PLAN_MATRIX.items():
			self.assertEqual(sub.required_apps(sub.plan_features(plan)), want["apps"], plan)

	def test_module_blocking_matches_the_ladder(self):
		for plan, want in PLAN_MATRIX.items():
			blocked = set(sub.blocked_module_defs(sub.plan_features(plan)))
			for m in want["modules_blocked"]:
				self.assertIn(m, blocked, f"{plan} should block {m}")
			for m in want["modules_visible"]:
				self.assertNotIn(m, blocked, f"{plan} should NOT block {m}")

	def test_each_plan_is_a_superset_of_the_one_below(self):
		order = ["starter", "business", "enterprise"]
		for lower, higher in zip(order, order[1:]):
			self.assertTrue(
				set(sub.plan_features(lower)) <= set(sub.plan_features(higher)),
				f"{higher} must contain everything in {lower}")

	def test_upgrading_never_takes_a_workspace_away(self):
		order = ["starter", "business", "enterprise"]
		for lower, higher in zip(order, order[1:]):
			lo, _ = sub.sold_and_unsold_workspaces(sub.plan_features(lower))
			hi, _ = sub.sold_and_unsold_workspaces(sub.plan_features(higher))
			self.assertTrue(set(lo) <= set(hi), f"{higher} lost something {lower} had")

	def test_the_hr_module_is_never_blocked(self):
		"""Blocking `HR` would hide Leaves, Expenses and HR Setup - which every
		plan includes - because Frappe HR puts them all in that one module. This
		is precisely why workspace-level hiding had to exist."""
		for plan in list(PLAN_MATRIX) + ["custom"]:
			self.assertNotIn("HR", sub.blocked_module_defs(sub.plan_features(plan)), plan)


class TestCustomSubscriptions(FrappeTestCase):
	"""Custom is not a tier - it is "the ladder, plus whatever else was ticked".

	The plan NAME is derived from the selection, so ticking any ERPNext module
	makes a tenant custom automatically. There is no separate ERPNext flow.
	"""

	def test_custom_carries_every_hr_feature(self):
		self.assertEqual(sub.plan_features("custom"), sub.plan_features("enterprise"))

	def test_ticking_one_erpnext_module_reveals_exactly_that_one(self):
		feats = sub.plan_features("enterprise") + ["erp_accounts"]
		blocked = set(sub.blocked_module_defs(feats))
		self.assertNotIn("Accounts", blocked)
		for other in ("Stock", "Selling", "Buying", "Manufacturing", "CRM"):
			self.assertIn(other, blocked, f"{other} was not bought")

	def test_ticking_several_reveals_all_of_them_and_nothing_more(self):
		picked = ["erp_accounts", "erp_stock", "erp_selling"]
		feats = sub.plan_features("enterprise") + picked
		blocked = set(sub.blocked_module_defs(feats))
		for m in ("Accounts", "Stock", "Selling"):
			self.assertNotIn(m, blocked)
		for m in ("Buying", "CRM", "Projects", "Assets", "Support",
		          "Maintenance", "Quality Management", "Manufacturing"):
			self.assertIn(m, blocked)

	def test_a_starter_tenant_may_buy_one_erpnext_module(self):
		"""Nobody should be pushed up a tier to buy a single module."""
		feats = sub.plan_features("starter") + ["erp_accounts"]
		blocked = set(sub.blocked_module_defs(feats))
		self.assertNotIn("Accounts", blocked)
		self.assertIn("Payroll", blocked, "still Starter for HR")
		self.assertIn("Stock", blocked)

	def test_erpnext_infrastructure_is_hidden_however_much_is_bought(self):
		"""Setup, Regional, Utilities and the rest are plumbing Frappe HR needs.
		They are always installed, always hidden, and never sold."""
		everything = (sub.plan_features("enterprise")
		              + list(sub.ERPNEXT_FEATURES))
		blocked = set(sub.blocked_module_defs(everything))
		for m in sub.ERPNEXT_INFRASTRUCTURE:
			self.assertIn(m, blocked, f"{m} is plumbing and must stay hidden")

	def test_buying_every_erpnext_module_still_hides_frappe_clutter(self):
		everything = sub.plan_features("enterprise") + list(sub.ERPNEXT_FEATURES)
		blocked = set(sub.blocked_module_defs(everything))
		for m in sub.FRAPPE_HIDDEN:
			self.assertIn(m, blocked, f"{m} is framework clutter for a tenant")

	def test_erpnext_choices_never_change_the_hr_workspaces(self):
		"""ERPNext modules are gated by module, HR features by workspace. The two
		must not interfere."""
		base_show, base_hide = sub.sold_and_unsold_workspaces(sub.plan_features("starter"))
		with_erp, hide_erp = sub.sold_and_unsold_workspaces(
			sub.plan_features("starter") + ["erp_accounts", "erp_stock"])
		self.assertEqual(base_show, with_erp)
		self.assertEqual(base_hide, hide_erp)

	def test_every_sellable_erpnext_module_has_a_stable_id(self):
		for m in sub.ERPNEXT_SELLABLE:
			fid = sub.erp_feature_id(m)
			self.assertTrue(fid.startswith("erp_"))
			self.assertIn(fid, sub.ERPNEXT_FEATURES)
			self.assertEqual(sub.ERPNEXT_FEATURES[fid]["module_defs"], [m])

	def test_sellable_and_infrastructure_never_overlap(self):
		"""A module in both lists would be sold and force-hidden at once."""
		self.assertFalse(set(sub.ERPNEXT_SELLABLE) & set(sub.ERPNEXT_INFRASTRUCTURE))


class TestEdgeCases(FrappeTestCase):
	"""The inputs that are not a tidy plan name.

	Every one of these is reachable: a tenant provisioned before the registry
	existed, a downgrade, a typo in a support script, a hand-edited site config.
	"""

	def test_an_unknown_plan_grants_everything(self):
		"""Deliberately generous. Unknown means old or mistyped, and the safe
		direction is never to lock a paying customer out of what they had
		yesterday."""
		for junk in ("platinum", "STARTER_v2", "", "  ", "enterprise "):
			self.assertEqual(sub.plan_features(junk), sub.plan_features("enterprise"), junk)

	def test_a_none_plan_grants_everything(self):
		self.assertEqual(sub.plan_features(None), sub.plan_features("enterprise"))

	def test_plan_names_are_case_insensitive(self):
		for name in ("Starter", "STARTER", "sTaRtEr"):
			self.assertEqual(sub.plan_features(name), sub.plan_features("starter"), name)

	def test_a_site_with_no_features_key_gets_everything(self):
		"""Covers every tenant provisioned before this existed. A missing key
		must never lock anyone out."""
		self.assertEqual(sorted(sub.enabled_features({})), sorted(sub.FEATURES))

	def test_an_explicitly_empty_list_is_not_the_same_as_missing(self):
		"""[] is a real state a downgrade produces: "nothing beyond required".
		Treating it as unset would silently grant the whole product."""
		got = sub.enabled_features({"features": []})
		self.assertEqual(sorted(got), sorted(sub.REQUIRED))
		self.assertNotEqual(sorted(got), sorted(sub.FEATURES))

	def test_required_features_survive_any_input(self):
		for feats in ([], ["goals"], ["nonsense"], list(sub.FEATURES), ["erp_stock"]):
			got = sub.enabled_features({"features": feats})
			for r in sub.REQUIRED:
				self.assertIn(r, got, f"{r} missing for input {feats}")

	def test_an_unknown_feature_id_is_ignored_not_fatal(self):
		"""Garbage in a stored list must not break the desk for a real tenant."""
		feats = sub.plan_features("starter") + ["not_a_feature", "erp_not_real"]
		blocked = sub.blocked_module_defs(feats)     # must not raise
		self.assertIn("Payroll", blocked)
		show, _ = sub.sold_and_unsold_workspaces(feats)
		self.assertIn("Leaves", show)

	def test_duplicates_do_not_duplicate_the_output(self):
		feats = sub.plan_features("starter") * 3
		blocked = sub.blocked_module_defs(feats)
		self.assertEqual(len(blocked), len(set(blocked)))
		show, hide = sub.sold_and_unsold_workspaces(feats)
		self.assertEqual(len(show), len(set(show)))
		self.assertEqual(len(hide), len(set(hide)))

	def test_the_two_workspace_lists_never_overlap_for_any_input(self):
		"""A workspace in both would flip on every sync depending on loop order."""
		for feats in ([], ["goals"], ["junk"], sub.plan_features("business"),
		              list(sub.FEATURES), list(sub.ERPNEXT_FEATURES)):
			show, hide = sub.sold_and_unsold_workspaces(feats)
			self.assertFalse(set(show) & set(hide), str(feats)[:40])

	def test_has_feature_never_denies_a_required_one(self):
		for r in sub.REQUIRED:
			self.assertTrue(sub.has_feature(r, {"features": []}), r)

	def test_has_feature_denies_something_not_bought(self):
		self.assertFalse(sub.has_feature("payroll", {"features": []}))
		self.assertFalse(sub.has_feature("goals", {"features": ["payroll"]}))

	def test_blocking_is_stable_and_sorted(self):
		"""A profile rebuilt from an unstable list would churn on every sync."""
		feats = sub.plan_features("business")
		first = sub.blocked_module_defs(feats)
		self.assertEqual(first, sorted(first))
		self.assertEqual(first, sub.blocked_module_defs(list(reversed(feats))))


class TestAdminCatalogue(FrappeTestCase):
	"""What the control-plane console renders.

	The plan list used to be hardcoded in this page's JavaScript - a fourth copy
	that matched neither tenant_api nor the registry. It is now served from the
	registry, so these tests guard the contract the UI depends on.
	"""

	def setUp(self):
		frappe.set_user("Administrator")
		self.cat = sub.get_plan_catalogue()

	def test_it_offers_every_feature_and_every_erpnext_module(self):
		ids = {f["id"] for f in self.cat["features"]}
		self.assertEqual(ids, set(sub.FEATURES) | set(sub.ERPNEXT_FEATURES))

	def test_required_features_are_flagged_so_the_ui_can_lock_them(self):
		flagged = {f["id"] for f in self.cat["features"] if f.get("required")}
		self.assertEqual(flagged, set(sub.REQUIRED))

	def test_required_features_come_first(self):
		"""The console renders them at the top and disables the toggle."""
		flags = [bool(f.get("required")) for f in self.cat["features"]]
		self.assertEqual(flags, sorted(flags, reverse=True),
		                 "required features must be contiguous at the front")

	def test_erpnext_modules_are_marked_as_such(self):
		erp = [f for f in self.cat["features"] if f.get("erpnext")]
		self.assertEqual({f["id"] for f in erp}, set(sub.ERPNEXT_FEATURES))
		self.assertEqual(len(erp), len(sub.ERPNEXT_SELLABLE))

	def test_no_erpnext_module_is_ever_required(self):
		for f in self.cat["features"]:
			if f.get("erpnext"):
				self.assertFalse(f.get("required"), f["id"])

	def test_every_preset_only_names_ids_the_catalogue_offers(self):
		ids = {f["id"] for f in self.cat["features"]}
		for plan, feats in self.cat["plans"].items():
			self.assertTrue(set(feats) <= ids, f"{plan} names an unknown feature")

	def test_every_preset_includes_the_required_features(self):
		"""The console seeds a new tenant from a preset. A preset missing a
		required feature would create a tenant missing it."""
		for plan, feats in self.cat["plans"].items():
			for r in sub.REQUIRED:
				self.assertIn(r, feats, f"{plan} is missing required feature {r}")

	def test_every_feature_has_what_the_ui_needs_to_draw_it(self):
		for f in self.cat["features"]:
			for key in ("id", "label", "desc", "icon"):
				self.assertTrue(f.get(key) is not None, f"{f['id']} has no {key}")
			self.assertTrue(f["label"].strip(), f["id"])


class TestAppliedToThisSite(FrappeTestCase):
	"""Applying a plan for real: profile, workspaces and a user, together.

	Every one of these facts was individually true while a live tenant was still
	wrong, because nothing ran them end to end.
	"""

	EMP = "matrix.employee@access.test"

	def setUp(self):
		frappe.set_user("Administrator")
		self._plane = frappe.conf.get("alvoraa_control_plane")
		frappe.conf.pop("alvoraa_control_plane", None)
		if not frappe.db.exists("User", self.EMP):
			u = frappe.get_doc({"doctype": "User", "email": self.EMP,
			                    "first_name": "Matrix", "send_welcome_email": 0,
			                    "user_type": "System User"})
			u.flags.ignore_permissions = True
			u.insert(ignore_permissions=True)
		self._ws = {w: frappe.db.get_value("Workspace", w, "is_hidden")
		            for w in ("Payroll", "Recruitment", "Leaves")
		            if frappe.db.exists("Workspace", w)}

	def tearDown(self):
		frappe.set_user("Administrator")
		for w, v in self._ws.items():
			frappe.db.set_value("Workspace", w, "is_hidden", v, update_modified=False)
		if frappe.db.exists("User", self.EMP):
			frappe.delete_doc("User", self.EMP, force=True, ignore_permissions=True)
		if self._plane is not None:
			frappe.conf["alvoraa_control_plane"] = self._plane
		frappe.db.commit()

	def _apply(self, plan):
		feats = sub.plan_features(plan)
		ma.sync_module_profile(feats, ma.PROFILE_NAME)
		ma.sync_workspaces(feats)
		ma.apply_to_users([self.EMP])
		return feats

	def test_starter_hides_payroll_both_ways(self):
		"""Module AND workspace. Either alone leaves Payroll reachable in the
		sidebar, which is how a live tenant kept showing it."""
		self._apply("starter")
		blocks = set(frappe.get_doc("User", self.EMP).get_blocked_modules())
		self.assertIn("Payroll", blocks, "module not blocked")
		if "Payroll" in self._ws:
			self.assertEqual(frappe.db.get_value("Workspace", "Payroll", "is_hidden"), 1,
			                 "workspace not hidden")

	def test_business_reveals_payroll_both_ways(self):
		self._apply("business")
		blocks = set(frappe.get_doc("User", self.EMP).get_blocked_modules())
		self.assertNotIn("Payroll", blocks)
		if "Payroll" in self._ws:
			self.assertEqual(frappe.db.get_value("Workspace", "Payroll", "is_hidden"), 0)

	def test_recruitment_is_hidden_by_workspace_alone(self):
		"""It has no module of its own - Job Opening, Job Applicant and Interview
		all sit in `HR`. Module blocking can never reach it, which is why the
		desk showed Recruitment to a Starter tenant for weeks."""
		self._apply("starter")
		self.assertNotIn("Recruitment", sub.blocked_module_defs(sub.plan_features("starter")))
		if "Recruitment" in self._ws:
			self.assertEqual(frappe.db.get_value("Workspace", "Recruitment", "is_hidden"), 1)

	def test_a_downgrade_takes_it_away_again(self):
		self._apply("business")
		self._apply("starter")
		self.assertIn("Payroll", set(frappe.get_doc("User", self.EMP).get_blocked_modules()))
		if "Payroll" in self._ws:
			self.assertEqual(frappe.db.get_value("Workspace", "Payroll", "is_hidden"), 1)

	def test_an_upgrade_puts_it_back(self):
		self._apply("starter")
		self._apply("enterprise")
		blocks = set(frappe.get_doc("User", self.EMP).get_blocked_modules())
		for m in ("Payroll", "Performance Management"):
			self.assertNotIn(m, blocks, m)
		if "Recruitment" in self._ws:
			self.assertEqual(frappe.db.get_value("Workspace", "Recruitment", "is_hidden"), 0)

	def test_applying_twice_changes_nothing_the_second_time(self):
		self._apply("starter")
		first = sorted(frappe.get_doc("User", self.EMP).get_blocked_modules())
		self._apply("starter")
		self.assertEqual(sorted(frappe.get_doc("User", self.EMP).get_blocked_modules()), first)

	def test_required_workspaces_survive_the_harshest_plan(self):
		ma.sync_workspaces([])
		if "Leaves" in self._ws:
			self.assertEqual(frappe.db.get_value("Workspace", "Leaves", "is_hidden"), 0)


class TestWhatIsNotEnforced(FrappeTestCase):
	"""The gap, written down.

	A suite that only proved the hiding would let a reader believe the product is
	enforced. It is not. These tests pin the CURRENT truth so that when roles
	land (wave 4) they fail loudly and force this file to be updated, rather than
	quietly continuing to describe a system that no longer exists.
	"""

	def test_blocking_a_module_does_not_remove_doctype_permission(self):
		"""block_modules hides the desk sidebar. It changes no permission, so a
		hidden Payroll still answers /api/resource/Salary Slip for anyone whose
		ROLE allows it."""
		blocked = sub.blocked_module_defs(sub.plan_features("starter"))
		self.assertIn("Payroll", blocked)
		perms = frappe.get_all("DocPerm", filters={"parent": "Salary Slip"}, limit=1)
		self.assertTrue(perms, "Salary Slip still carries its permissions")

	def test_hiding_a_workspace_does_not_remove_its_doctypes(self):
		"""The Recruitment workspace can be hidden while Job Opening remains a
		perfectly usable doctype at its own URL."""
		self.assertTrue(frappe.db.exists("DocType", "Job Opening"))

	def test_withheld_roles_are_computed_but_never_applied(self):
		"""withheld_roles() is the real gate and nothing calls it yet. If this
		test starts failing, wave 4 has landed - update this file."""
		self.assertEqual(sub.withheld_roles(sub.plan_features("starter")), ["Interviewer"])
		import inspect

		from alvoraa_portal import tenant_api
		for mod in (ma, tenant_api):
			self.assertNotIn("withheld_roles", inspect.getsource(mod),
			                 f"{mod.__name__} now applies roles - wave 4 has landed")

	def test_only_three_features_are_backed_by_a_module_of_their_own(self):
		"""Everything else is workspace-gated only. Worth knowing before anyone
		assumes module blocking covers the product."""
		backed = {k for k, v in sub.FEATURES.items() if v.get("module_defs")}
		self.assertEqual(backed, {"payroll", "performance", "goals"})

	def test_uninstalling_an_app_is_the_only_real_denial_we_have(self):
		"""Goals doctypes cease to exist when alvoraa_goals is absent - that IS
		enforcement. It is also why a downgrade must never uninstall: dropping
		the app drops the customer's data."""
		self.assertIn("alvoraa_goals", sub.required_apps(sub.plan_features("enterprise")))
		self.assertNotIn("alvoraa_goals", sub.required_apps(sub.plan_features("starter")))

	def test_the_tenant_admin_keeps_everything_on_purpose(self):
		"""A deliberate trade: admins set up integrations and print formats, which
		live in the very modules this hides. It means a tenant admin still sees
		Payroll on a plan without it."""
		self.assertEqual(ma.ADMIN_ROLES, {"System Manager"})
		self.assertIsNone(ma._profile_for("Administrator"))


class TestGatingReadsTheSiteConfig(FrappeTestCase):
	"""The step every other test skipped.

	Every test in this file and in test_module_access passes `features` in by
	hand. None of them exercised sync_site() reading it from the site's OWN
	config - so when provisioning failed to WRITE that config, 217 tests stayed
	green while a live tenant was entitled to the entire product.

	The chain has three links and the tests only covered the last one:

	    provisioning writes  ->  config holds  ->  gating reads  ->  desk hides
	                                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
	                                              all the coverage was here
	"""

	def setUp(self):
		frappe.set_user("Administrator")
		self._saved = {k: frappe.conf.get(k)
		               for k in ("features", "subscription_plan", "alvoraa_control_plane")}
		frappe.conf.pop("alvoraa_control_plane", None)
		self._ws = {w: frappe.db.get_value("Workspace", w, "is_hidden")
		            for w in ("Payroll", "Recruitment", "Performance", "Leaves")
		            if frappe.db.exists("Workspace", w)}

	def tearDown(self):
		for k, v in self._saved.items():
			if v is None:
				frappe.conf.pop(k, None)
			else:
				frappe.conf[k] = v
		for w, v in self._ws.items():
			frappe.db.set_value("Workspace", w, "is_hidden", v, update_modified=False)
		frappe.db.commit()

	def _configure(self, **conf):
		for k in ("features", "subscription_plan"):
			frappe.conf.pop(k, None)
		frappe.conf.update(conf)

	def test_a_starter_config_hides_payroll(self):
		"""No argument passed - sync_workspaces must read the config itself."""
		self._configure(features=sub.plan_features("starter"))
		ma.sync_workspaces()
		if "Payroll" in self._ws:
			self.assertEqual(frappe.db.get_value("Workspace", "Payroll", "is_hidden"), 1)

	def test_the_exact_config_a_broken_provision_left_behind(self):
		"""features missing + plan `custom`. This is what a real tenant had, and
		it entitles the site to everything - so NOTHING gets hidden. If this ever
		starts hiding things, the fallback changed and the comment above it is
		wrong."""
		self._configure(subscription_plan="custom")
		self.assertEqual(sorted(sub.enabled_features()), sorted(sub.FEATURES))
		ma.sync_workspaces()
		if "Payroll" in self._ws:
			self.assertEqual(frappe.db.get_value("Workspace", "Payroll", "is_hidden"), 0,
			                 "no feature list means no gating - by design, and why "
			                 "provisioning must write one")

	def test_writing_the_feature_list_is_what_makes_the_difference(self):
		"""Same plan name, one extra config key, opposite outcome. That single
		key was the whole bug."""
		self._configure(subscription_plan="custom")
		ma.sync_workspaces()
		before = frappe.db.get_value("Workspace", "Payroll", "is_hidden") \
			if "Payroll" in self._ws else None

		self._configure(subscription_plan="custom",
		                features=sub.plan_features("starter"))
		ma.sync_workspaces()
		after = frappe.db.get_value("Workspace", "Payroll", "is_hidden") \
			if "Payroll" in self._ws else None

		if "Payroll" in self._ws:
			self.assertEqual((before, after), (0, 1))

	def test_an_empty_feature_list_in_config_still_gates(self):
		"""[] is a real downgrade state and must not be read as "unset"."""
		self._configure(features=[])
		self.assertEqual(sorted(sub.enabled_features()), sorted(sub.REQUIRED))
		ma.sync_workspaces()
		for w in ("Payroll", "Recruitment", "Performance"):
			if w in self._ws:
				self.assertEqual(frappe.db.get_value("Workspace", w, "is_hidden"), 1, w)
		if "Leaves" in self._ws:
			self.assertEqual(frappe.db.get_value("Workspace", "Leaves", "is_hidden"), 0)

	def test_the_profile_is_built_from_the_config_too(self):
		"""sync_module_profile has the same default-argument shape, so it has the
		same exposure."""
		self._configure(features=sub.plan_features("starter"))
		ma.sync_module_profile()
		doc = frappe.get_doc("Module Profile", ma.PROFILE_NAME)
		blocked = {d.module for d in doc.block_modules}
		self.assertIn("Payroll", blocked)

	def test_config_and_explicit_arguments_agree(self):
		"""If these ever diverge, one of the two callers is silently wrong."""
		feats = sub.plan_features("business")
		self._configure(features=feats)
		from_config = sub.enabled_features()
		self.assertEqual(sorted(from_config), sorted(feats))
		self.assertEqual(sub.sold_and_unsold_workspaces(from_config),
		                 sub.sold_and_unsold_workspaces(feats))
