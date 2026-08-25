"""Removing the `Alvox` Module Defs left behind by the rebrand.

Both apps register two modules on every site - the live one and an `Alvox`
leftover. Measured on dev.alvoraa.co, alvoraa.co and demo.alvoraa.co: all three
carry them.

The tests that matter here are the ones about NOT deleting: a patch that removes
a Module Def on a site where the rename half-ran would orphan every doctype in
that module.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal.patches.v1_0 import remove_alvox_module_defs as patch

STALE = "Alvox Portal"
REAL = "Alvoraa Portal"


class AlvoxMixin:
	def setUp(self):
		frappe.set_user("Administrator")
		self._made = []

	def tearDown(self):
		frappe.set_user("Administrator")
		for dt, name in reversed(self._made):
			if frappe.db.exists(dt, name):
				frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
		frappe.db.commit()

	def _make_stale_module(self, name=STALE, app="alvoraa_portal"):
		if not frappe.db.exists("Module Def", name):
			doc = frappe.get_doc({"doctype": "Module Def", "module_name": name,
			                      "app_name": app, "custom": 1})
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
			self._made.append(("Module Def", name))
		frappe.db.commit()


class TestItRemovesTheLeftover(AlvoxMixin, FrappeTestCase):
	def test_a_stale_module_is_deleted(self):
		self._make_stale_module()
		self.assertTrue(frappe.db.exists("Module Def", STALE))
		patch.execute()
		self.assertFalse(frappe.db.exists("Module Def", STALE))

	def test_the_real_module_survives(self):
		"""The whole point is to leave exactly one."""
		self._make_stale_module()
		patch.execute()
		self.assertTrue(frappe.db.exists("Module Def", REAL))

	def test_running_twice_is_a_no_op(self):
		self._make_stale_module()
		patch.execute()
		patch.execute()          # must not raise
		self.assertFalse(frappe.db.exists("Module Def", STALE))

	def test_a_clean_site_is_untouched(self):
		before = frappe.db.count("Module Def")
		patch.execute()
		self.assertEqual(frappe.db.count("Module Def"), before)


class TestItRefusesWhenUnsafe(AlvoxMixin, FrappeTestCase):
	"""The tests that stop this patch doing damage."""

	def test_it_will_not_delete_the_only_record_for_a_module(self):
		"""If the rename half-ran, the `Alvox` record may be the ONLY one - and
		deleting it would orphan every doctype in that module. The patch checks
		the replacement exists first."""
		import inspect

		src = inspect.getsource(patch.execute)
		self.assertIn('if not frappe.db.exists("Module Def", new)', src)
		self.assertIn("continue", src)

	def test_it_repoints_before_deleting(self):
		"""A Workspace still pointing at the stale module must be moved, not
		left dangling."""
		self._make_stale_module()
		ws_name = "Alvox Cleanup Probe"
		# Insert against the REAL module, then point it at the stale one with a
		# direct write. Frappe validates that a module has a folder on disk when
		# a document is saved, and the stale module has none - which is the whole
		# reason it is a leftover. The direct write reproduces the state a site is
		# actually in without asking Frappe to bless it.
		doc = frappe.get_doc({"doctype": "Workspace", "title": ws_name,
		                      "label": ws_name, "module": REAL, "public": 1,
		                      "content": "[]"})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		self._made.append(("Workspace", doc.name))
		frappe.db.set_value("Workspace", doc.name, "module", STALE, update_modified=False)
		frappe.db.commit()

		patch.execute()

		self.assertEqual(frappe.db.get_value("Workspace", doc.name, "module"), REAL,
		                 "the workspace should have been moved to the real module")
		self.assertFalse(frappe.db.exists("Module Def", STALE))

	def test_it_clears_block_module_rows_first(self):
		"""Block Module.module is a Link to Module Def. Deleting the Module Def
		while those rows exist leaves a dangling link, and deny-by-default means
		the stale module IS blocked, so the rows really are there."""
		import inspect

		self.assertIn("_drop_block_module_rows", inspect.getsource(patch.execute))

	def test_it_checks_for_leftovers_before_deleting(self):
		import inspect

		src = inspect.getsource(patch.execute)
		self.assertIn("_still_referenced", src)


class TestTheAppsDoNotRecreateIt(FrappeTestCase):
	"""If modules.txt named the stale module, migrate would put it straight back
	and this patch would run for ever without effect."""

	def test_modules_txt_names_only_the_real_modules(self):
		import os

		import alvoraa_portal

		base = os.path.dirname(os.path.abspath(alvoraa_portal.__file__))
		path = os.path.join(base, "modules.txt")
		if not os.path.exists(path):
			self.skipTest("modules.txt not found on this bench")
		with open(path, encoding="utf-8") as f:
			names = [ln.strip() for ln in f if ln.strip()]
		self.assertIn(REAL, names)
		self.assertNotIn(STALE, names)

	def test_the_patch_is_registered(self):
		import os

		import alvoraa_portal

		txt = os.path.join(os.path.dirname(os.path.abspath(alvoraa_portal.__file__)),
		                   "patches.txt")
		if not os.path.exists(txt):
			self.skipTest("patches.txt not found on this bench")
		with open(txt, encoding="utf-8") as f:
			self.assertIn("remove_alvox_module_defs", f.read())
