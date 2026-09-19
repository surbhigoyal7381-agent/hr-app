"""Slice 012 push 1 · the portal page keeps its Data to review panel and HR Analytics lines.

A pin for a hot file (parallel-work.md §7): hrms-employee.html changes in most
slices, and a careless merge that drops the panel, its menu entry or the
"not linked" handling should fail here rather than in front of HR.
"""

import os
import re

from frappe.tests.utils import FrappeTestCase

import alvoraa_portal
from alvoraa_portal import data_review


def _page():
	path = os.path.join(os.path.dirname(alvoraa_portal.__file__), "www", "hrms-employee.html")
	with open(path, encoding="utf-8-sig") as f:
		return f.read()


class TestThePageKeepsDataToReview(FrappeTestCase):
	def test_the_menu_entry_panel_and_dialog_exist(self):
		page = _page()
		self.assertIn('id="nav-data-review"', page)
		self.assertIn('id="panel-data-review"', page)
		self.assertIn('id="sb-dr-badge"', page)
		self.assertRegex(page, r'(?s)id="dr-confirm".*?role="alertdialog"')

	def test_opening_the_panel_loads_it_and_the_menu_follows_the_analytics_rule(self):
		page = _page()
		switch = page[page.index("function switchPanel("):page.index("/* ── Live clock")]
		self.assertIn('if (name === "data-review")', switch)
		self.assertIn("drLoad()", switch)
		plan = page[page.index("function applyPlanNav()"):page.index("function loadAvailableFeatures()")]
		self.assertIn('getElementById("nav-data-review")', plan)

	def test_hr_analytics_draws_not_linked_and_the_review_lines(self):
		page = _page()
		render = page[page.index("function renderAnalyticsData(d)"):page.index("/* ── Data to review (slice 012)")]
		self.assertIn("drAnalyticsNotes(d);", render)
		self.assertIn("if (d.not_linked) return;", render)
		self.assertIn('id="ana-dr-notes"', page)
		# "No figures yet" is a dash, never 0%.
		self.assertNotIn("(kpi.attendance_rate || 0)", render)

	def test_the_badge_is_set_from_the_page_load_call(self):
		"""DEF-3 / AC-31: the menu badge must be there on page load, not only after
		HR opens one of the two panels.
		"""
		page = _page()
		context = page[page.index("function loadPortalContext()"):page.index("function loadAvailableFeatures()")]
		self.assertIn("drSetBadge(ctx.review_open_count", context)

	def test_the_page_calls_real_post_endpoints(self):
		import frappe

		page = _page()
		for fn in ("data_review_items", "data_review_confirm"):
			self.assertIn(f"alvoraa_portal.data_review.{fn}", page)
			self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func.get(getattr(data_review, fn)),
			                 ["POST"])
		# The page sends its calls through gpFetch, which posts when it has arguments.
		self.assertTrue(re.search(r'gpFetch\("alvoraa_portal\.data_review\.data_review_items", \{\}\)', page))
