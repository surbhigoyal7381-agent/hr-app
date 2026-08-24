"""Wave 2 — the Module Profile that hides unsold modules.

These tests assert what it does AND what it does not do. The second part matters:
hiding a module is not a boundary, and a test suite that only proves the hiding
would let someone believe otherwise.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import module_access as ma
from alvoraa_portal import subscription as sub


class TestModuleProfile(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.db.rollback()

	def test_profile_hides_unsold_modules(self):
		ma.sync_module_profile(sub.plan_features("starter"))
		hidden = set(ma.get_hidden_modules()["blocked"])
		self.assertIn("Payroll", hidden, "starter does not include payroll")
		self.assertIn("Accounts", hidden, "no ERPNext module was ticked")

	def test_profile_keeps_sold_modules_visible(self):
		ma.sync_module_profile(sub.plan_features("business"))
		hidden = set(ma.get_hidden_modules()["blocked"])
		self.assertNotIn("Payroll", hidden, "business includes payroll")

	def test_ticked_erpnext_module_is_not_hidden(self):
		selection = sub.plan_features("starter") + ["erp_accounts"]
		ma.sync_module_profile(selection)
		hidden = set(ma.get_hidden_modules()["blocked"])
		self.assertNotIn("Accounts", hidden)
		self.assertIn("Stock", hidden, "modules not ticked stay hidden")

	def test_only_modules_that_exist_here_are_blocked(self):
		"""A site without alvoraa_goals has no such Module Def, and Frappe
		rejects a link to one that does not exist."""
		ma.sync_module_profile(sub.plan_features("starter"))
		existing = {m.name for m in frappe.get_all("Module Def", fields=["name"])}
		for m in ma.get_hidden_modules()["blocked"]:
			self.assertIn(m, existing, "%s does not exist on this site" % m)

	def test_syncing_twice_does_not_duplicate(self):
		ma.sync_module_profile(sub.plan_features("starter"))
		first = ma.get_hidden_modules()["blocked"]
		ma.sync_module_profile(sub.plan_features("starter"))
		self.assertEqual(first, ma.get_hidden_modules()["blocked"])

	def test_a_plan_change_updates_the_profile(self):
		ma.sync_module_profile(sub.plan_features("starter"))
		self.assertIn("Payroll", ma.get_hidden_modules()["blocked"])
		ma.sync_module_profile(sub.plan_features("business"))
		self.assertNotIn("Payroll", ma.get_hidden_modules()["blocked"])


class TestUserApplication(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		ma.sync_module_profile(sub.plan_features("starter"))
		self.user = "module.access.test@example.com"
		if not frappe.db.exists("User", self.user):
			u = frappe.get_doc({
				"doctype": "User", "email": self.user, "first_name": "Module Access",
				"send_welcome_email": 0, "enabled": 1,
			})
			u.flags.ignore_permissions = True
			u.insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.rollback()

	def test_applying_copies_the_blocks_onto_the_user(self):
		ma.apply_to_users([self.user])
		user = frappe.get_doc("User", self.user)
		self.assertEqual(user.module_profile, ma.PROFILE_NAME)
		blocked = {d.module for d in user.block_modules}
		self.assertIn("Payroll", blocked, "Frappe should copy the profile on save")

	def test_administrator_is_never_touched(self):
		"""If a profile is ever built wrong, support still needs a way in."""
		before = frappe.db.get_value("User", "Administrator", "module_profile")
		ma.apply_to_users(["Administrator"])
		self.assertEqual(frappe.db.get_value("User", "Administrator", "module_profile"), before)


class TestThisIsNotABoundary(FrappeTestCase):
	"""Recorded deliberately: wave 2 hides, wave 4 denies."""

	def test_blocking_a_module_does_not_remove_doctype_access(self):
		"""A blocked module is still reachable by API if the role allows it.

		This test exists so nobody reads the suite above and concludes the
		subscription boundary is enforced. It is not, until roles land.
		"""
		ma.sync_module_profile(sub.plan_features("starter"))
		self.assertIn("Payroll", ma.get_hidden_modules()["blocked"])

		# Administrator still reads a Payroll doctype, blocked module or not.
		frappe.set_user("Administrator")
		self.assertTrue(
			frappe.has_permission("Salary Slip", "read"),
			"hiding a module does not deny doctype access - that is wave 4",
		)


class TestPlanChangesAfterProvisioning(FrappeTestCase):
	"""A plan is chosen once; the tenant then runs for years.

	Users arrive, roles change, and the plan itself gets upgraded or downgraded.
	If module access is decided only at provisioning it decays from day one.
	"""

	def setUp(self):
		frappe.set_user("Administrator")
		self.user = "plan.change.test@example.com"
		if not frappe.db.exists("User", self.user):
			u = frappe.get_doc({
				"doctype": "User", "email": self.user, "first_name": "Plan Change",
				"send_welcome_email": 0, "enabled": 1,
			})
			u.flags.ignore_permissions = True
			u.insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.rollback()

	def _blocked_for(self, user):
		return {d.module for d in frappe.get_doc("User", user).block_modules}

	def test_upgrade_gives_the_user_more(self):
		ma.sync_module_profile(sub.plan_features("starter"))
		ma.apply_to_users([self.user])
		self.assertIn("Payroll", self._blocked_for(self.user))

		ma.sync_module_profile(sub.plan_features("business"))
		ma.apply_to_users([self.user])
		self.assertNotIn("Payroll", self._blocked_for(self.user),
		                 "an upgrade must reach users who already existed")

	def test_downgrade_takes_it_away_again(self):
		ma.sync_module_profile(sub.plan_features("business"))
		ma.apply_to_users([self.user])
		self.assertNotIn("Payroll", self._blocked_for(self.user))

		ma.sync_module_profile(sub.plan_features("starter"))
		ma.apply_to_users([self.user])
		self.assertIn("Payroll", self._blocked_for(self.user),
		              "a downgrade must reach users who already existed")

	def test_a_user_created_later_still_gets_the_profile(self):
		"""Most of a tenant's users are created long after provisioning."""
		ma.sync_module_profile(sub.plan_features("starter"))
		later = "joined.later@example.com"
		if frappe.db.exists("User", later):
			frappe.delete_doc("User", later, force=True, ignore_permissions=True)
		u = frappe.get_doc({
			"doctype": "User", "email": later, "first_name": "Joined Later",
			"send_welcome_email": 0, "enabled": 1,
		})
		u.flags.ignore_permissions = True
		u.insert(ignore_permissions=True)          # after_insert hook fires here
		self.assertEqual(frappe.db.get_value("User", later, "module_profile"),
		                 ma.PROFILE_NAME,
		                 "a user added after provisioning must inherit the plan")


class TestTenantAdminExemption(FrappeTestCase):
	"""Tenant admins keep the full module list so they can set up integrations."""

	def setUp(self):
		frappe.set_user("Administrator")
		ma.sync_module_profile(sub.plan_features("starter"))
		self.admin = "tenant.admin.test@example.com"
		if not frappe.db.exists("User", self.admin):
			u = frappe.get_doc({
				"doctype": "User", "email": self.admin, "first_name": "Tenant Admin",
				"send_welcome_email": 0, "enabled": 1,
			})
			u.flags.ignore_permissions = True
			u.insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.rollback()

	def test_a_system_manager_is_not_blocked(self):
		u = frappe.get_doc("User", self.admin)
		u.append("roles", {"role": "System Manager"})
		u.flags.ignore_permissions = True
		u.save(ignore_permissions=True)

		res = ma.apply_to_users([self.admin])
		self.assertEqual(res["admins_exempt"], 1)
		self.assertFalse(frappe.db.get_value("User", self.admin, "module_profile"),
		                 "a tenant admin must keep Integrations, Email and the rest")

	def test_core_and_desk_are_hidden_from_ordinary_users(self):
		"""Decision 2026-08-23: the desk's own machinery is not for employees.

		They keep it only where it is needed - tenant admins are exempted, and
		sync_site refuses to run on the control plane at all.
		"""
		blocked = set(sub.blocked_module_defs(sub.plan_features("starter")))
		self.assertIn("Core", blocked)
		self.assertIn("Desk", blocked)

	def test_the_control_plane_is_never_gated(self):
		"""It is not a tenant. Its admins provision tenants and need everything."""
		frappe.conf["alvoraa_control_plane"] = 1
		try:
			res = ma.sync_site()
			self.assertTrue(res.get("skipped"))
		finally:
			frappe.conf.pop("alvoraa_control_plane", None)

	def test_frappe_clutter_is_hidden_from_ordinary_users(self):
		blocked = set(sub.blocked_module_defs(sub.plan_features("starter")))
		for m in ("Website", "Integrations", "Automation"):
			self.assertIn(m, blocked)


class TestHrKeepsTheDesk(FrappeTestCase):
	"""An HR Manager sent to /app/hr must land on a working screen.

	Employees lose the desk shell; HR staff keep it. Both still lose everything
	the plan does not include - that distinction is the whole point.
	"""

	def setUp(self):
		frappe.set_user("Administrator")
		ma.sync_site(sub.plan_features("starter"))
		self.hr = "hr.desk.test@example.com"
		if not frappe.db.exists("User", self.hr):
			u = frappe.get_doc({
				"doctype": "User", "email": self.hr, "first_name": "HR Desk",
				"send_welcome_email": 0, "enabled": 1,
			})
			u.flags.ignore_permissions = True
			u.insert(ignore_permissions=True)
		else:
			# apply_to_users() COMMITS, so a role added by a sibling test survives
			# tearDown's rollback. Reset the user rather than depend on ordering -
			# the same trap the leave tests hit with hr_api.apply_leave.
			u = frappe.get_doc("User", self.hr)
			u.set("roles", [])
			u.module_profile = None
			u.set("block_modules", [])
			u.flags.ignore_permissions = True
			u.save(ignore_permissions=True)
			frappe.db.commit()

	def tearDown(self):
		frappe.db.rollback()

	def test_hr_profile_keeps_core_and_desk(self):
		hidden = ma.get_hidden_modules()["profiles"][ma.HR_PROFILE_NAME]
		self.assertNotIn("Core", hidden, "an HR Manager needs a working desk")
		self.assertNotIn("Desk", hidden)

	def test_employee_profile_still_hides_them(self):
		hidden = ma.get_hidden_modules()["profiles"][ma.PROFILE_NAME]
		self.assertIn("Core", hidden)
		self.assertIn("Desk", hidden)

	def test_hr_still_loses_what_the_plan_excludes(self):
		"""Keeping the desk is not a way round the subscription."""
		hidden = ma.get_hidden_modules()["profiles"][ma.HR_PROFILE_NAME]
		self.assertIn("Payroll", hidden, "starter has no payroll, HR or not")
		self.assertIn("Accounts", hidden)

	def test_an_hr_user_gets_the_hr_profile(self):
		u = frappe.get_doc("User", self.hr)
		u.append("roles", {"role": "HR Manager"})
		u.flags.ignore_permissions = True
		u.save(ignore_permissions=True)

		ma.apply_to_users([self.hr])
		self.assertEqual(frappe.db.get_value("User", self.hr, "module_profile"),
		                 ma.HR_PROFILE_NAME)

	def test_an_ordinary_user_gets_the_employee_profile(self):
		ma.apply_to_users([self.hr])
		self.assertEqual(frappe.db.get_value("User", self.hr, "module_profile"),
		                 ma.PROFILE_NAME)


class TestSwitchTarget(FrappeTestCase):
	"""Where the portal's switch control sends each kind of user."""

	def setUp(self):
		frappe.set_user("Administrator")
		self.u = "switch.target.test@example.com"
		if not frappe.db.exists("User", self.u):
			d = frappe.get_doc({
				"doctype": "User", "email": self.u, "first_name": "Switch Target",
				"send_welcome_email": 0, "enabled": 1,
			})
			d.flags.ignore_permissions = True
			d.insert(ignore_permissions=True)
		else:
			d = frappe.get_doc("User", self.u)
			d.set("roles", [])
			d.flags.ignore_permissions = True
			d.save(ignore_permissions=True)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _as(self, *roles):
		d = frappe.get_doc("User", self.u)
		d.set("roles", [])
		for r in roles:
			if frappe.db.exists("Role", r):
				d.append("roles", {"role": r})
		d.flags.ignore_permissions = True
		d.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.set_user(self.u)

	def test_an_employee_gets_no_switch_control(self):
		"""They have no business in the desk, so no door is offered."""
		self._as("Employee")
		self.assertIsNone(ma.get_switch_target())

	def test_hr_is_sent_to_frappe_hr(self):
		self._as("HR Manager")
		t = ma.get_switch_target()
		self.assertEqual(t["label"], "Switch to HR Core")
		self.assertEqual(t["url"], "/app/hr")

	def test_an_admin_is_sent_to_the_desk(self):
		self._as("System Manager")
		t = ma.get_switch_target()
		self.assertEqual(t["label"], "Switch to Admin")
		self.assertEqual(t["url"], "/app")

	def test_admin_wins_when_someone_holds_both(self):
		"""A System Manager who is also HR Manager should land on the desk."""
		self._as("System Manager", "HR Manager")
		self.assertEqual(ma.get_switch_target()["url"], "/app")

	def test_the_navbar_gets_a_way_back(self):
		"""Frappe's own top-right menu should offer a route to the portal."""
		ma.sync_navbar_item()
		labels = [r.item_label for r in frappe.get_doc("Navbar Settings").settings_dropdown]
		self.assertIn(ma.NAVBAR_LABEL, labels)

	def test_adding_the_navbar_item_twice_does_not_duplicate(self):
		ma.sync_navbar_item()
		ma.sync_navbar_item()
		labels = [r.item_label for r in frappe.get_doc("Navbar Settings").settings_dropdown]
		self.assertEqual(labels.count(ma.NAVBAR_LABEL), 1)


class TestWorkspaceSync(FrappeTestCase):
	"""Hiding the desk workspaces a tenant did not buy.

	A live tenant on a custom plan was measured showing Payroll, Recruitment and
	Tenure in its desk sidebar. Its Module Profile blocked 0 modules - and even
	a correct one could not have helped, because those workspaces sit inside the
	shared `HR` and `Payroll` modules.
	"""

	WS = "Recruitment"

	def setUp(self):
		frappe.set_user("Administrator")
		self._existed = frappe.db.exists("Workspace", self.WS)
		if self._existed:
			self._saved = frappe.db.get_value("Workspace", self.WS, "is_hidden")

	def tearDown(self):
		if self._existed:
			frappe.db.set_value("Workspace", self.WS, "is_hidden", self._saved,
			                    update_modified=False)
			frappe.db.commit()
		frappe.set_user("Administrator")

	def test_it_hides_a_workspace_the_plan_excludes(self):
		if not self._existed:
			self.skipTest("this site has no Recruitment workspace")
		ma.sync_workspaces(sub.plan_features("starter"))
		self.assertEqual(frappe.db.get_value("Workspace", self.WS, "is_hidden"), 1)

	def test_an_upgrade_puts_it_back(self):
		"""Hiding without revealing would make every plan change one-way."""
		if not self._existed:
			self.skipTest("this site has no Recruitment workspace")
		ma.sync_workspaces(sub.plan_features("starter"))
		self.assertEqual(frappe.db.get_value("Workspace", self.WS, "is_hidden"), 1)
		ma.sync_workspaces(sub.plan_features("business"))
		self.assertEqual(frappe.db.get_value("Workspace", self.WS, "is_hidden"), 0)

	def test_required_workspaces_are_never_hidden(self):
		ma.sync_workspaces([])
		for ws in ("Leaves", "Expenses", "HR Setup"):
			if frappe.db.exists("Workspace", ws):
				self.assertEqual(frappe.db.get_value("Workspace", ws, "is_hidden"), 0, ws)

	def test_it_ignores_workspaces_the_registry_does_not_name(self):
		"""ERPNext's own workspaces, and anything a customer built, are not ours
		to touch."""
		if not frappe.db.exists("Workspace", "Build"):
			self.skipTest("no Build workspace here")
		before = frappe.db.get_value("Workspace", "Build", "is_hidden")
		ma.sync_workspaces(sub.plan_features("starter"))
		self.assertEqual(frappe.db.get_value("Workspace", "Build", "is_hidden"), before)

	def test_it_survives_a_missing_workspace(self):
		"""Not every feature ships a workspace on every site."""
		ma.sync_workspaces(sub.plan_features("enterprise"))   # must not raise
