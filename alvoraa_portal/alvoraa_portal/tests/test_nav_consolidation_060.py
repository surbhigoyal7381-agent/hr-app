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

from frappe.tests.utils import FrappeTestCase

from alvoraa_portal.tests import portal_source as PS


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
		self.assertIn(">Whole team</option>", _page())

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
