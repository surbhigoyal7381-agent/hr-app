"""Five doors to attendance became two. This is what stops them coming back.

Surbhi approved the consolidation on 17 Oct 2026. Before it the sidebar had
FIVE entries that all led to attendance and nobody could tell them apart:
"Attendance & Leave", "Attendance Insights", "My Attendance", "Team View", and
"Attendance & Leave" a second time under a "Tools" heading, labelled
"Checkin Log".

WHY A TEXT CHECK RATHER THAN A BEHAVIOUR TEST. Every item below is a label, a
target or the absence of one. A rename is exactly the kind of change a careless
merge restores - "My Attendance" reads like an improvement if you did not know
it was removed on purpose - and nothing else in the suite would notice. These
assertions name the outcome, so a merge that undoes it goes red.

The page is read through the one shared expander, because the page itself is a
short list of Jinja includes: reading it alone would check a shell.
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal.tests import portal_source as PS
from alvoraa_portal.tests.leave_fixtures import ensure_user


def _page():
	return PS.read_page()


def _sidebar():
	"""Just the sidebar's own nav.

	Counting across the whole page would count the phone's bottom bar too,
	and that bar deliberately points at the same panel.
	"""
	page = _page()
	start = page.index('<nav class="sidebar-nav">')
	return page[start:page.index("</nav>", start)]


class TestTheSidebarHasOneAttendanceAndOneLeave(FrappeTestCase):
	def test_the_attendance_item_is_called_attendance_not_my_attendance(self):
		"""The heading is the constant word now, and `ac-sub` says whose
		record it is. "My Attendance" was wrong the moment a manager could
		open somebody else's month through the same screen."""
		page = _page()
		self.assertIn('<span class="nav-label">Attendance</span>', page)
		self.assertNotIn("My Attendance", page)

	def test_the_leave_item_is_called_leave(self):
		page = _page()
		self.assertNotIn("Attendance &amp; Leave", page)
		# re.S: the icon between the tag and the label is on its own line.
		self.assertIsNotNone(
			re.search(r'data-panel="attendance"[^>]*>.*?</span>\s*Leave\b',
			          _sidebar(), re.S),
			"the panel that holds Apply Leave must be labelled Leave")

	def test_attendance_comes_second_right_under_home(self):
		"""Position is part of what was approved: the thing people open most
		should not be eighth."""
		page = _page()
		order = re.findall(r'class="nav-item[^"]*"\s+data-panel="([a-z-]+)"', page)
		self.assertGreater(len(order), 5, "the nav was not found at all")
		self.assertEqual(order[0], "home")
		self.assertEqual(order[1], "att-record")
		self.assertEqual(order[2], "attendance")

	def test_only_one_sidebar_item_leads_to_each_of_them(self):
		bar = _sidebar()
		self.assertEqual(bar.count('data-panel="attendance"'), 1,
		                 "the Leave panel had TWO sidebar entries")
		self.assertEqual(bar.count('data-panel="att-record"'), 1)

	def test_the_checkin_log_duplicate_and_its_tools_heading_are_gone(self):
		"""It pointed at the same panel as "Attendance & Leave" - the same
		screen, a different name, under a heading of its own."""
		page = _page()
		self.assertNotIn("Checkin Log", page)
		self.assertNotIn('class="sidebar-section">Tools<', page)


class TestAttendanceInsightsIsGatedAndUnderManagement(FrappeTestCase):
	def test_it_starts_hidden_so_the_server_decides(self):
		"""It had NO `display:none` and nothing in portal.js referred to it,
		so every employee saw it with two of its three views greyed out."""
		page = _page()
		item = re.search(r'<div class="nav-item"[^>]*id="nav-att-insights"[^>]*>', page)
		self.assertIsNotNone(item, "the Attendance Insights item is gone entirely")
		self.assertIn("display:none", item.group(0),
		              "an ungated item is shown to people with nothing behind it")

	def test_the_script_actually_gates_it(self):
		"""A hidden item that nothing ever shows is a different bug."""
		page = _page()
		self.assertIn('getElementById("nav-att-insights")', page)
		self.assertIn("ctx.att_insights", page)

	def test_it_sits_after_the_management_heading(self):
		page = _page()
		self.assertLess(page.index('id="mgmt-section-hdr"'),
		                page.index('id="nav-att-insights"'),
		                "it is still in the employee's own list")


class TestTheTeamReviewMovedToTheAttendancePage(FrappeTestCase):
	def test_team_view_no_longer_has_an_attendance_review_tab(self):
		page = _page()
		self.assertNotIn("tvtab-review", page)
		self.assertNotIn("tv-review-panel", page)
		# The tab's own label. A plain search for the words would also catch
		# the comment in switchTeamTab that explains where the tab went.
		self.assertNotIn(">Attendance Review<", page)

	def test_the_list_is_now_inside_the_attendance_panel(self):
		"""Moved, not rewritten: the same ids the tab used."""
		page = _page()
		panel = page.index('id="panel-att-record"')
		for part in ('id="ac-team"', 'id="tr-bar"', 'id="tr-chips"',
		             'id="tr-body"', 'id="tr-pager"'):
			self.assertIn(part, page)
			self.assertGreater(page.index(part), panel,
			                   "%s is not inside the Attendance panel" % part)

	def test_the_picker_offers_whole_team(self):
		"""Still the first thing the picker offers, 19 Oct 2026 - but no longer
		an <option>. The dropdown became a searchable listbox, because HR's
		copy of it held 403 names. What matters has not changed: the words are
		there, and `AC_TEAM` is still the value behind them."""
		page = _page()
		self.assertIn('label: "Whole team"', page)
		self.assertIn('var AC_TEAM = "*team"', page)
		self.assertIn("value: AC_TEAM", page)

	def test_a_row_opens_that_persons_month(self):
		page = _page()
		self.assertIn("window.acFromTeam", page)
		self.assertIn("acFromTeam(", page)


class TestTheLeavePageKeepsLeaveAndNothingElse(FrappeTestCase):
	def test_the_month_calendar_and_the_four_tiles_are_gone(self):
		"""The Attendance page shows that month with the punches, the hours
		and the shift on it. This was the poorer of two answers."""
		page = _page()
		# The elements, and the two functions that drew them. Searched as
		# DEFINITIONS, because the comment left in their place names them.
		for gone in ('id="cal-grid-main"', 'id="att-present"', 'id="att-absent"',
		             'id="att-leave"', 'id="att-wfh"', 'id="cal-label"',
		             "function fetchCalendar(", "function renderCalendar(",
		             "get_attendance_calendar\""):
			self.assertNotIn(gone, page, "%s should have gone with the widget" % gone)

	def test_everything_leave_is_still_there(self):
		page = _page()
		for kept in ("openLeaveModal()", 'id="leave-rings"',
		             'id="leave-apps-tbody"', 'id="late-card"', 'id="late-tbody"'):
			self.assertIn(kept, page, "%s is part of the Leave page" % kept)


class TestThePhoneBarPointsAtTheRightPage(FrappeTestCase):
	def test_the_middle_item_opens_the_attendance_page(self):
		"""It said Attendance and opened the Leave page, which is the rename's
		one real trap."""
		page = _page()
		item = re.search(r'<div class="bnav-item"[^>]*data-panel="([a-z-]+)"[^>]*>'
		                 r'\s*<div class="bnav-icon">.*?</div>\s*<div>Attendance</div>',
		                 page, re.S)
		self.assertIsNotNone(item, "the phone bar has no Attendance item")
		self.assertEqual(item.group(1), "att-record")


class TestThePositionsItemFollowsTheServer(FrappeTestCase):
	"""Surbhi, 19 Oct 2026: "I want the position access to be provided through
	the Frappe interface like other standard Frappe modules".

	The menu reads the server's answer - Frappe's Read on Alvoraa Position -
	rather than a copy of the rule.
	"""

	ROLE = "Nav061 Positions Reader"

	def setUp(self):
		from hrms.alvoraa_org_structure.tests.test_register_194 import _trail

		self._saved = {"alvoraa_org_managers_see_all":
		               frappe.db.get_default("alvoraa_org_managers_see_all")}
		frappe.db.set_default("alvoraa_org_managers_see_all", "")
		self._made = []
		self._before = _trail()

	def tearDown(self):
		frappe.set_user("Administrator")
		self._drop_rows()
		for doctype, name in reversed(self._made):
			try:
				frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
			except Exception:
				pass
		for k, v in self._saved.items():
			frappe.db.set_default(k, v if v is not None else "")
		frappe.db.commit()

	def _drop_rows(self):
		"""Every permission row, change record and Permission Log row this test
		made goes, committed, so nothing leaks onto test_site."""
		from hrms.alvoraa_org_structure.tests.test_register_194 import _forget_permissions, _trail

		for doctype, names in _trail().items():
			for name in names - self._before[doctype]:
				frappe.db.delete(doctype, {"name": name})
		frappe.db.commit()
		_forget_permissions()

	def _grant_read(self, role):
		"""Through Role Permissions Manager's own function, as an admin would.
		Once any Custom DocPerm row exists for a doctype, Frappe uses those rows
		and not the shipped ones."""
		from frappe.core.page.permission_manager import permission_manager as screen

		if not frappe.db.exists("Role", role):
			# Kept, like the users ensure_user makes: a role still held by a
			# user cannot be deleted, and it grants nothing once the row goes.
			frappe.get_doc({"doctype": "Role", "role_name": role,
			                "desk_access": 0}).insert(ignore_permissions=True)
		screen.add("Alvoraa Position", role, 0)
		frappe.db.commit()

	def _employee(self, name, user=None, reports_to=None):
		doc = frappe.get_doc({
			"doctype": "Employee", "first_name": name,
			"company": frappe.db.get_value("Company", {}, "name"),
			"gender": frappe.db.get_value("Gender", {}, "name"),
			"date_of_birth": "1990-01-01", "date_of_joining": "2020-01-01",
			"status": "Active", "user_id": user, "reports_to": reports_to,
		}).insert(ignore_permissions=True)
		self._made.append(("Employee", doc.name))
		return doc.name

	def _context_as(self, user):
		from alvoraa_portal import hr_api

		frappe.set_user(user)
		frappe.local._alvoraa_leads = {}
		frappe.cache().delete_value(f"portal_ctx_{user}")
		return hr_api.get_portal_context()

	def test_the_menu_reads_the_flag_not_the_manager_role(self):
		plan = _page()
		plan = plan[plan.index("function applyPlanNav()"):plan.index("function loadAvailableFeatures()")]
		line = plan[plan.index('getElementById("nav-positions")'):]
		line = line[:line.index(";", line.index("style.display"))]
		self.assertIn("roles.positions", line)
		self.assertIn("plan_org_structure", line)
		self.assertNotIn("is_manager", line)
		self.assertNotIn("is_hr", line)
		self.assertIn("window._roles.positions  = !!ctx.positions", _page())

	def test_a_plain_employee_gets_no_flag(self):
		user = ensure_user("nav060.plain@example.com", roles=("Employee",))
		self._employee("Nav060 Plain", user=user)
		self.assertIs(self._context_as(user)["positions"], False)

	def test_a_manager_with_direct_reports_gets_no_flag(self):
		frappe.db.set_default("alvoraa_org_managers_see_all", 1)
		user = ensure_user("nav060.boss@example.com", roles=("Employee",))
		boss = self._employee("Nav060 Boss", user=user)
		self._employee("Nav060 Report", reports_to=boss)
		ctx = self._context_as(user)
		self.assertTrue(ctx["is_manager"], "the case needs a real manager")
		self.assertIs(ctx["positions"], False)

	def test_an_hr_manager_gets_the_flag(self):
		user = ensure_user("nav060.hrm@example.com", roles=("Employee", "HR Manager"))
		self._employee("Nav060 HRM", user=user)
		self.assertIs(self._context_as(user)["positions"], True)

	def _context_cached(self, user):
		"""What the menu would get on the user's next page load: the cached
		context if there is one. Nothing here clears it by hand."""
		from alvoraa_portal import hr_api

		frappe.set_user(user)
		frappe.local._alvoraa_leads = {}
		frappe.local.role_permissions = {}
		return hr_api.get_portal_context()

	def test_the_flag_follows_a_row_added_and_taken_away_at_once(self):
		"""Surbhi asked when the menu can lag. Without a hook, for up to the
		hour the context is cached. Now a change in Role Permissions Manager
		clears it for every holder of that role, so the next page load is
		right. Nothing in this test deletes the cache itself."""
		from frappe.core.page.permission_manager import permission_manager as screen

		user = ensure_user("nav061.reader@example.com", roles=("Employee",))
		self._employee("Nav061 Reader", user=user)
		if not frappe.db.exists("Role", self.ROLE):
			frappe.get_doc({"doctype": "Role", "role_name": self.ROLE,
			                "desk_access": 0}).insert(ignore_permissions=True)
		u = frappe.get_doc("User", user)
		u.flags.ignore_permissions = True
		u.add_roles(self.ROLE)
		frappe.db.commit()
		self.assertIs(self._context_as(user)["positions"], False)
		key = f"portal_ctx_{user}"
		self.assertIsNotNone(frappe.cache().get_value(key), "the case needs a cached menu")

		frappe.set_user("Administrator")
		self._grant_read(self.ROLE)
		self.assertIsNone(frappe.cache().get_value(key), "the hook should have cleared it")
		self.assertIs(self._context_cached(user)["positions"], True)

		frappe.set_user("Administrator")
		screen.remove("Alvoraa Position", self.ROLE, 0)
		frappe.db.commit()
		self.assertIs(self._context_cached(user)["positions"], False)
