"""The joining page can actually talk to its own server.

**Why this file exists.** ALV-343. `www/joining.html` is the only portal page
that does not extend `templates/web.html`, and that is deliberate: OPS-44 wants
inline-only assets on the one page used by people who cannot ring our helpdesk.

But Frappe hands a page its CSRF token by string-replacing the literal comment
`<!-- csrf_token -->`, which arrives from `frappe/templates/base.html`
(`website/page_renderers/base_template_page.py:18`). No base template, no
marker. `TemplatePage.render` still CALLS `add_csrf_token`; the replace simply
had nothing to replace.

The page's own `csrf()` helper then fell through all three of its options -
`window.frappe` undefined, and **Frappe sets no `csrf_token` cookie anywhere** -
to its literal `"fetch"` fallback. Every POST carried the token `"fetch"`,
`frappe/auth.py:97` answered *"Invalid Request"*, and `begin()`'s catch-all
painted that as JOIN-ENDED. So a joiner who signed in correctly was told their
sign-in had finished its job.

**Every endpoint on the page was dead** - `open_invite`, `save_draft`,
`submit_invite` and `upload_invite_file` - on every tenant, from the day the
slice shipped.

**Why 178 joiner tests were green over it.** They all call the whitelisted
methods in process. None goes through HTTP, so none goes through
`validate_csrf_token`. The server was always right. Nobody drove the page.

So these tests render the page the way the website renderer does and check the
token is really there, with a real value, in the right order. A test that only
asserted the marker string is in the file would pass on a page Frappe never
substitutes, which is most of the bug.
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase

PAGE = "joining"
# What `base_template_page.add_csrf_token` writes in place of the marker.
INJECTED = re.compile(r'frappe\.csrf_token\s*=\s*"([^"]*)"')
# The declaration that has to come first, or the line above throws on an
# undefined `frappe` and the page is just as dead, in a harder way to see.
DECLARED = "window.frappe = window.frappe || {}"


def render(path=PAGE):
	"""The page as the website renderer builds it, post-processing included.

	`get_response_content` is what runs `TemplatePage.render`, and the token is
	substituted THERE - outside `@cache_html` - so this is the only level at
	which the question can be answered honestly.
	"""
	from werkzeug.datastructures import Headers
	from werkzeug.test import EnvironBuilder
	from werkzeug.wrappers import Request

	from frappe.website.serve import get_response_content

	before = getattr(frappe.local, "request", None)
	frappe.local.request = Request(
		EnvironBuilder(path="/" + path, method="GET").get_environ())
	frappe.local.form_dict = frappe._dict()
	frappe.local.response_headers = Headers()
	try:
		return get_response_content(path)
	finally:
		frappe.local.request = before


class TheJoiningPageCanReachItsServer(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		# **`frappe.set_user` blanks the session, and that silently disarms this
		# whole file.** It does `local.session.data = _dict()` - an EMPTY dict,
		# which is FALSY - and `add_csrf_token`'s guard is
		# `if frappe.local.session and getattr(..., "data", None)`. So after any
		# `set_user` Frappe skips the substitution altogether and every test
		# here fails on a page whose markup is perfectly correct.
		#
		# A real signed-in joiner always has a token on the session, so putting
		# one back is restoring the normal case, not arranging a pass. Without
		# this line the first run of these tests blamed the fix for the
		# harness's own doing.
		frappe.local.session.data.csrf_token = frappe.generate_hash()

	def test_the_page_carries_a_real_csrf_token(self):
		"""The fix, where it has to work: a token with a value in it.

		Not the marker, not a placeholder - the session's own token, because
		that is the only string `frappe/auth.py:97` will accept.
		"""
		html = render()
		found = INJECTED.search(html)
		self.assertTrue(
			found,
			"the joining page renders with no CSRF token, so every POST from it "
			"is refused and the joiner is told their sign-in has ended")
		self.assertTrue(
			found.group(1),
			"the joining page renders a CSRF token with an empty value")
		self.assertEqual(
			found.group(1), frappe.local.session.data.csrf_token,
			"the token on the page is not this session's token")

	def test_frappe_is_declared_before_the_token_is_assigned(self):
		"""Order is load-bearing, and getting it wrong fails silently.

		Frappe's injected line assigns `frappe.csrf_token`. With no `frappe`
		object in front of it the script throws, the assignment never happens,
		and the page is dead again - but now with a token visibly present in
		the source, which is a worse place to debug from.
		"""
		html = render()
		declared = html.find(DECLARED)
		found = INJECTED.search(html)
		self.assertGreater(declared, -1, "window.frappe is never declared")
		self.assertTrue(found, "no CSRF token on the page")
		self.assertLess(
			declared, found.start(),
			"the CSRF token is assigned before window.frappe exists, so the "
			"script throws and the token never reaches the page")

	def test_the_page_does_not_fall_back_to_a_made_up_token(self):
		"""The `"fetch"` fallback is a tombstone, never a working path.

		It is kept because a page with no token at all is harder to read than
		one that fails the check, but if it is ever REACHED the page is broken.
		This asserts the real token is present so the fallback cannot be what
		runs - the fallback itself stays untested on purpose.
		"""
		html = render()
		self.assertIn(DECLARED, html)
		self.assertTrue(INJECTED.search(html))

	def test_an_ending_and_a_fault_do_not_share_a_code(self):
		"""ALV-343's second half, pinned in the markup.

		`begin()` used to paint every failure as JOIN-ENDED, so a CSRF refusal,
		an unset notice text and a genuinely closed invite all told the joiner
		the same thing. HR then looked at the invite when the fault was in the
		site. The two codes must stay distinct and both must stay on the page.
		"""
		html = render()
		self.assertIn("JOIN-ENDED", html, "the ending panel is gone")
		self.assertIn("JOIN-BROKEN", html,
		              "there is no panel for a fault that is not an ending, so "
		              "every failure is reported as a finished sign-in again")
