"""The joiner invite form can actually be saved.

**Why this file exists.** `invited_by` is `reqd` AND `read_only`, and it had no
default. Frappe's browser code checks mandatory fields BEFORE it sends anything,
and nobody can type into a read-only field - so the New Alvoraa Joiner
Submission form could never be saved, by anybody, on any tenant. The whole
joiner feature was unreachable through the screen HR is told to use.

Every test in slice 079 passed throughout, because `fixtures_079.a_row` hands
`invited_by` in by hand and inserts the document server-side. The server was
always right. Nobody pressed Save.

So these tests take the two things the old suite skipped:

1. what the FORM is handed when it opens - `frappe.new_doc`, which is what the
   browser builds a new document from, defaults applied;
2. what the server does for the doors a browser default never reaches - the
   REST API, a data import, a script.

A test that inserts a fully-populated document proves neither, which is the
whole lesson here: test what it SENDS, not just what it draws.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

DOCTYPE = "Alvoraa Joiner Submission"


class TheInviteFormCanBeSaved(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")

	def test_a_new_form_arrives_with_the_inviter_filled_in(self):
		"""The fix, where it has to work: the document the browser is given.

		`new_doc` is what Desk builds a new form from, so if the field is empty
		here it is empty on screen - and being `read_only` and `reqd`, the save
		button is then unreachable for ever.
		"""
		doc = frappe.new_doc(DOCTYPE)
		self.assertEqual(
			doc.invited_by, frappe.session.user,
			"a new joiner invite form opens with 'Invited by' empty, so its "
			"mandatory check can never be satisfied - the form cannot be saved")

	def test_the_field_still_cannot_be_typed_into(self):
		"""The default must not be bought by making the field editable.

		Who issued an invite is evidence. It is set by the system and read by
		people, never typed.
		"""
		meta = frappe.get_meta(DOCTYPE)
		field = meta.get_field("invited_by")
		self.assertTrue(field.read_only, "invited_by stopped being read-only")
		self.assertTrue(field.reqd, "invited_by stopped being required")
		self.assertEqual(field.default, "__user", "invited_by lost its default")

	def test_a_door_with_no_browser_default_still_gets_a_name(self):
		"""The REST API, a data import and a script never see `__user`.

		Frappe applies a field default when it BUILDS a new document. A payload
		posted straight at the server does not go through that, so without the
		controller line this insert is refused for a missing mandatory field.
		"""
		doc = frappe.get_doc({
			"doctype": DOCTYPE,
			"status": "Invited",
			"full_name": "ALV invited_by, posted not drawn",
			"login_id": "+91 98100 10341",
		})
		doc.insert(ignore_permissions=True)
		self.addCleanup(frappe.delete_doc, DOCTYPE, doc.name, force=True,
		                ignore_permissions=True)
		self.assertEqual(doc.invited_by, frappe.session.user)

	def test_an_inviter_already_named_is_kept(self):
		"""Never re-stamp a row with whoever happened to save it next.

		An import that names a real inviter keeps them, and a later edit by
		somebody else does not quietly rewrite who issued the invite.
		"""
		doc = frappe.get_doc({
			"doctype": DOCTYPE,
			"status": "Invited",
			"full_name": "ALV invited_by, named on the way in",
			"login_id": "+91 98100 10342",
			"invited_by": "Administrator",
		})
		doc.insert(ignore_permissions=True)
		self.addCleanup(frappe.delete_doc, DOCTYPE, doc.name, force=True,
		                ignore_permissions=True)
		self.assertEqual(doc.invited_by, "Administrator")

		doc.full_name = "ALV invited_by, saved again"
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.invited_by, "Administrator",
		                 "saving the row again re-stamped who invited them")
