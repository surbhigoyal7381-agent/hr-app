"""ALV-213: the employee portal uses the whole screen.

Pins the six approved fixes in the source, so a merge that drops one fails here.
The layout itself was measured in Chrome (see the ALV-213 notes).
"""

import os

from frappe.tests.utils import FrappeTestCase

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
	with open(os.path.join(APP, *parts), encoding="utf-8") as f:
		return f.read()


class TestPortalUsesTheWholeScreen(FrappeTestCase):
	def test_1_no_frappe_container(self):
		self.assertIn("context.full_width = 1", _read("www", "hrms_employee.py"))

	def test_2_and_3_phone_column_and_bottom_space(self):
		css = _read("public", "css", "ess", "panels.css")
		self.assertIn("body.sb-collapsed .main-content{margin-left:0", css)
		self.assertIn("calc(var(--bottom-h) + 20px)", css)
		self.assertNotIn("calc(var(--bottom-h)+", css)

	def test_4_one_top_bar_with_the_account_menu(self):
		self.assertIn("nav.navbar,.page-header-wrapper{display:none}", _read("public", "css", "ess", "panels.css"))
		frame = _read("templates", "includes", "ess", "frame.html")
		self.assertIn('id="mob-acct-menu"', frame)
		self.assertIn('href="/me"', frame)
		self.assertIn('href="/logout"', frame)
		self.assertIn("window.toggleAcctMenu", _read("public", "js", "ess", "portal.js"))

	def test_5_finance_tabs_scroll_on_their_own(self):
		self.assertIn("scrollbar-width:none;flex-shrink:0;max-width:100%", _read("public", "css", "ess", "panels.css"))

	def test_6_leave_applications_as_cards_on_a_phone(self):
		self.assertIn('id="leave-apps-cards"', _read("templates", "includes", "ess", "parts", "attendance.html"))
		self.assertIn("#lv-apps-wrap > table{display:none}", _read("public", "css", "ess", "panels.css"))
		self.assertIn('getElementById("leave-apps-cards")', _read("public", "js", "ess", "portal.js"))
