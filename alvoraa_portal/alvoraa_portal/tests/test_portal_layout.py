"""A `position: fixed` dialog must anchor to the viewport, not to a huge page.

`will-change`, `transform`, `filter`, `perspective` and `contain` all turn an
element into a CONTAINING BLOCK. Every `position: fixed` descendant then anchors
to that element instead of the viewport - which is not what anybody writing
`position: fixed` expects, and is silent.

`.main-content` carried `will-change: margin-left`, a performance hint for the
sidebar animation. It cost nothing on a short page. On Objectives & KPIs with
3,510 rows that element is tens of thousands of pixels tall, so the Filters
dialog - centred at `top: 50%` - opened far below the fold. It looked exactly
like a button that did nothing.

The wrappers listed here are the ancestors of the portal's fixed dialogs. A hint
added to any of them breaks every one of those dialogs at once, on the longest
pages only, which is the hardest version of this bug to find.
"""

import os
import re

import frappe
from frappe.tests.utils import FrappeTestCase

# Properties that create a containing block for fixed descendants.
TRAPS = ("will-change", "transform", "filter", "perspective", "contain", "backdrop-filter")

# Ancestors of the portal's fixed dialogs.
WRAPPERS = ("main-content", "emp-app", "panel")


def _page():
	import alvoraa_portal

	path = os.path.join(os.path.dirname(os.path.abspath(alvoraa_portal.__file__)),
	                    "www", "hrms-employee.html")
	with open(path, encoding="utf-8", errors="replace") as fh:
		return fh.read()


def _rule_body(css, selector):
	"""The declarations of `.selector { ... }`, ignoring anything commented out."""
	css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
	m = re.search(r"(^|[},])\s*\." + re.escape(selector) + r"\s*\{([^}]*)\}", css)
	return m.group(2) if m else None


class TestFixedDialogsAnchorToTheViewport(FrappeTestCase):
	def test_the_wrappers_create_no_containing_block(self):
		css = _page()
		broken = []
		for wrapper in WRAPPERS:
			body = _rule_body(css, wrapper)
			if body is None:
				continue
			for trap in TRAPS:
				if re.search(r"(^|;)\s*" + trap + r"\s*:", body):
					broken.append(f".{wrapper} sets {trap}")
		self.assertEqual(
			broken, [],
			"These make position:fixed anchor to the element instead of the "
			"viewport, so every dialog inside opens off-screen on a long page:\n  "
			+ "\n  ".join(broken))

	def test_the_filter_dialog_is_still_fixed_and_centred(self):
		"""If it ever becomes absolute, it scrolls away with the page instead."""
		body = _rule_body(_page(), "tv-pop")
		self.assertIsNotNone(body, ".tv-pop rule is missing")
		self.assertIn("position:fixed", body.replace(" ", ""))
		self.assertIn("top:50%", body.replace(" ", ""))

	def test_the_sidebar_transition_survived_the_fix(self):
		"""The hint was removed, not the animation it was hinting at."""
		body = _rule_body(_page(), "main-content")
		self.assertIn("transition", body)
		self.assertIn("margin-left", body)
