"""Slice 034 US-10 (ALV-89) - the page split, pinned.

AC-36  the page rendered from its includes is the page that was there before.
AC-37  every check reads it with the includes expanded, and cannot quietly
       read less.

The byte-for-byte comparison against the pre-split file was made once, at the
split, and is recorded in 03-implementation-notes.md. What can be pinned
forever is the structure that made it safe, and it is pinned here:

  * the page is a list of includes, not a flattened file again;
  * every include file on disk is pulled in, and pulled in once;
  * the shared expander refuses to hand back a shell;
  * the CSS and JS include files hold no Jinja, so moving them to cached
    static files later (OPS-31) stays a rename rather than another
    restructure.

A merge that flattens the page, drops an include tag or strands an include
file fails here rather than in front of an employee.
"""

import os
import shutil
import tempfile

from frappe.tests.utils import FrappeTestCase

from alvoraa_portal.tests import portal_source as PS


class TestThePageIsStillSplit(FrappeTestCase):
	def test_the_page_is_a_list_of_includes(self):
		with open(PS.PORTAL_PAGE, "rb") as fh:
			raw = fh.read()
		tags = PS.INCLUDE_RE.findall(raw)
		self.assertTrue(
			tags,
			"hrms-employee.html has no ess include tags. If the page was "
			"deliberately flattened, every check that calls portal_source is now "
			"reading it whole again and this test should be deleted with it.")
		# The page itself should stay short enough to read in one screenful.
		lines = raw.replace(b"\r\n", b"\n").split(b"\n")
		self.assertLess(len(lines), 120,
		                "the page is growing back; new markup belongs in an include file")

	def test_every_include_file_is_used_exactly_once(self):
		"""An orphaned include file is code that no check ever looks at."""
		with open(PS.PORTAL_PAGE, "rb") as fh:
			raw = fh.read()
		tags = [t.decode("utf-8") for t in PS.INCLUDE_RE.findall(raw)]
		self.assertEqual(sorted(tags), sorted(set(tags)),
		                 "the same include file is pulled in twice")
		self.assertEqual(set(tags), PS.ess_files_on_disk(),
		                 "the page's include list and the files on disk disagree")

	def test_the_expanded_page_is_the_whole_page(self):
		"""A shell would be a few thousand characters, not a million."""
		text = PS.read_page()
		self.assertGreater(len(text), 900000)
		# Landmarks from the far ends of the original file.
		for marker in ('class="emp-app"', "function switchPanel", "initSbCollapse()"):
			self.assertIn(marker, text, marker)

	def test_the_helper_refuses_to_hand_back_a_shell(self):
		"""AC-37. This is the whole point: a check must not pass on nothing."""
		work = tempfile.mkdtemp()
		try:
			shell = os.path.join(work, "hrms-employee.html")
			with open(shell, "wb") as fh:
				fh.write(b"<html>nothing here</html>\r\n")
			real = PS.PORTAL_PAGE
			PS.PORTAL_PAGE = shell
			try:
				with self.assertRaises(PS.PortalSourceError):
					PS.page_bytes(shell)
			finally:
				PS.PORTAL_PAGE = real
		finally:
			shutil.rmtree(work, ignore_errors=True)

	def test_the_helper_refuses_when_an_include_file_is_missing(self):
		work = tempfile.mkdtemp()
		try:
			page = os.path.join(work, "page.html")
			with open(page, "wb") as fh:
				fh.write(b'{% include "templates/includes/ess/gone/away.html" %}\r\n')
			with self.assertRaises(PS.PortalSourceError):
				PS.page_bytes(page, check=False)
		finally:
			shutil.rmtree(work, ignore_errors=True)

	def test_the_css_and_js_include_files_hold_no_jinja(self):
		"""So OPS-31 (move them to cached files) stays a rename, not a rewrite."""
		offenders = []
		for rel in sorted(PS.ess_files_on_disk()):
			if ".css." not in rel and ".js." not in rel:
				continue
			with open(os.path.join(PS.APP_ROOT, *rel.split("/")), encoding="utf-8") as fh:
				text = fh.read()
			for token in ("{{", "{%", "{#"):
				if token in text:
					offenders.append("%s holds %s" % (rel, token))
		self.assertEqual(offenders, [], "; ".join(offenders))
