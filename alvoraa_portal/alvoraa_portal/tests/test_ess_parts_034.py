"""Slice 034, OPS-31 follow-on - the markup parts, and what ess_part() refuses.

`ess_part` is registered as a Jinja global (hooks.py). That makes it reachable
from ANY template on the site, including ones a user with the right to write a
Web Page or a Print Format can author. So it is treated as an entry point, not
as an internal helper: it takes a name, never a path, and everything it will not
accept is pinned here.
"""

import os
import shutil
import tempfile

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import ess_parts
from alvoraa_portal.tests import portal_source as PS


class TestEssPartRefusals(FrappeTestCase):
	def test_a_path_is_not_a_name(self):
		"""The one that matters: no part of the filesystem is reachable."""
		for bad in ("../../../../etc/passwd", "../hooks", "parts/home",
		            "home.html", "/etc/passwd", "home/../../hooks",
		            "..%2f..%2fhooks", "HOME", "home ", ""):
			with self.assertRaises(frappe.ValidationError, msg=repr(bad)):
				ess_parts.ess_part(bad)

	def test_a_name_that_is_not_a_string_is_refused(self):
		for bad in (None, 1, ["home"], {"name": "home"}):
			with self.assertRaises(frappe.ValidationError, msg=repr(bad)):
				ess_parts.ess_part(bad)

	def test_a_name_that_does_not_exist_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			ess_parts.ess_part("no-such-part")

	def test_a_part_holding_a_template_tag_is_refused(self):
		"""A part is pasted, never compiled. A Jinja tag in one would reach the
		browser as text, so it must fail loudly instead of shipping."""
		work = tempfile.mkdtemp()
		try:
			for token in ("{{ 1 }}", "{% if 1 %}x{% endif %}", "{# c #}"):
				with open(os.path.join(work, "probe.html"), "w", encoding="utf-8") as fh:
					fh.write("<div>" + token + "</div>")
				real = ess_parts.PARTS_DIR
				ess_parts.PARTS_DIR = work
				try:
					with self.assertRaises(frappe.ValidationError, msg=token):
						ess_parts._read("probe")
				finally:
					ess_parts.PARTS_DIR = real
		finally:
			shutil.rmtree(work, ignore_errors=True)

	def test_a_real_part_comes_back_unescaped(self):
		"""If it came back escaped the page would show its own markup as text."""
		out = ess_parts.ess_part("home")
		self.assertTrue(hasattr(out, "__html__"), "a part must be marked safe")
		self.assertIn('id="panel-home"', str(out))
		self.assertNotIn("&lt;div", str(out))

	def test_the_cache_key_moves_with_the_release(self):
		"""Otherwise a worker serves last release's markup until it restarts."""
		from frappe.utils import get_build_version
		key = "ess_part:%s:home" % get_build_version()
		frappe.cache().delete_value(key)
		ess_parts.ess_part("home")
		self.assertIsNotNone(frappe.cache().get_value(key))


class TestThePartsAndThePageAgree(FrappeTestCase):
	def test_every_part_on_disk_is_asked_for_exactly_once(self):
		with open(PS.PORTAL_PAGE, "rb") as fh:
			raw = fh.read()
		asked = [m.group(1).decode("utf-8") for m in PS.PART_RE.finditer(raw)]
		self.assertTrue(asked, "the page asks for no markup parts")
		self.assertEqual(sorted(asked), sorted(set(asked)), "a part is asked for twice")
		# Slice 042: the preview page's frame asks for Home's and the Inbox's
		# skeletons. A part belongs to ONE of the two pages; belonging to
		# neither is still a failure here.
		preview = PS.preview_reach()[2]
		self.assertEqual(set(asked) | preview, PS.ess_parts_on_disk(),
		                 "a markup part belongs to neither portal page")
		self.assertFalse(set(asked) & preview,
		                 "a markup part is pasted into both pages")
		self.assertEqual(set(asked) | preview, ess_parts.parts_on_disk(),
		                 "the helper and the test helper disagree about the parts")

	def test_no_part_holds_a_template_tag(self):
		offenders = []
		for name in sorted(ess_parts.parts_on_disk()):
			with open(os.path.join(ess_parts.PARTS_DIR, name + ".html"),
			          encoding="utf-8") as fh:
				text = fh.read()
			for token in ("{{", "{%", "{#"):
				if token in text:
					offenders.append("%s holds %s" % (name, token))
		self.assertEqual(offenders, [], "; ".join(offenders))
