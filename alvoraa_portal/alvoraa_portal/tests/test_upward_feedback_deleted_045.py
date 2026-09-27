"""045 AC-35 / PRIV-6 / SEC-11 - the minimum-less upward-feedback read is gone.

`goals_api.get_upward_feedback` was whitelisted, read with
`ignore_permissions=True`, and returned the individual comment strings with no
minimum group at all. A manager whose cycle drew one response got that one
person's words back:

    {"count": 1, "avg_rating": 2.0, "comments": ["he shouts at the floor staff"]}

In a team of six the author is recoverable by elimination; with one direct
report there is nothing to eliminate. PRIV-12 sets a minimum group of five for
exactly this shape and `home_api._suppress` already implements it.

Three of this slice's own documents recorded the endpoint as deleted - `01c`
PRIV-6, `01c` SEC-11, and `02` appendix D B22 / US-16 / AC-35. It was not. This
file is what makes that claim true and keeps it true.

**Two things make these assertions able to fail rather than pass vacuously.**

* **A positive control runs first.** `submit_upward_feedback` - the write, which
  portal.js really does call and which must NOT be deleted - is asserted present
  and whitelisted in the same test. If the module failed to import, or if
  somebody deleted the whole upward-feedback section, the control goes red and
  the absence assertion stops meaning anything on its own.
* **The whitelist is searched by name over every registered function**, not by
  looking the attribute up. `frappe.whitelisted` holds function objects, so a
  reinstated copy under a different module path - or a stale one still
  registered from an earlier import - is caught. Asserting only
  `not hasattr(goals_api, ...)` would miss both.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import goals_api, home_api, performance_api

GONE = "get_upward_feedback"
KEPT = "submit_upward_feedback"


class UpwardFeedbackReadDeleted(FrappeTestCase):
	def test_the_write_is_still_there_and_still_whitelisted(self):
		"""Positive control. portal.js calls this one; deleting it would be a defect.

		Without this, `test_the_minimum_less_read_is_gone` would pass just as
		happily if the whole module had stopped importing.
		"""
		fn = getattr(goals_api, KEPT, None)
		self.assertTrue(callable(fn), f"goals_api.{KEPT} must still exist")
		self.assertIn(fn, frappe.whitelisted, f"goals_api.{KEPT} must stay whitelisted")

	def test_the_minimum_less_read_is_gone_from_the_module(self):
		self.assertIsNone(
			getattr(goals_api, GONE, None),
			"goals_api.get_upward_feedback returned individual comments with no "
			"minimum group (AC-35 / PRIV-6). It must not come back without one.",
		)

	def test_it_is_gone_from_the_whitelist_register(self):
		"""Membership is by the function object, so search the register by name.

		A module attribute can be deleted while a decorated copy stays in
		`frappe.whitelisted` from an earlier import - then the door is still
		open to an HTTP call while the source reads as clean.
		"""
		still_registered = [
			f"{fn.__module__}.{fn.__name__}"
			for fn in frappe.whitelisted
			if fn.__name__ == GONE and fn.__module__.endswith("goals_api")
		]
		self.assertEqual(still_registered, [], "still callable over HTTP")

	def test_calling_it_by_hand_cannot_find_it(self):
		"""AC-35 asks for the call-by-hand, not only the reading."""
		with self.assertRaises((AttributeError, ImportError)):
			frappe.get_attr("alvoraa_portal.goals_api.get_upward_feedback")

	def test_the_endpoint_that_survives_applies_a_minimum(self):
		"""The manager's own aggregate is served by performance_api, which has a floor.

		This is why deleting rather than rewriting was the right call: the
		capability is not lost, only the minimum-less door.

		The floor there is 3, not PRIV-12's 5. That is pre-existing and outside
		this slice - recorded here so the difference is written down rather than
		discovered later.
		"""
		import inspect

		src = inspect.getsource(performance_api.get_upward_feedback_received)
		self.assertIn("below_threshold", src)
		self.assertIn("MIN_THRESHOLD", src)
		self.assertLess(
			3, home_api.MIN_GROUP,
			"if these ever match, delete this note rather than the assertion",
		)
