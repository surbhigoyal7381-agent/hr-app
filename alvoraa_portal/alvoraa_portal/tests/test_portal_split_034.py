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
  * the styles and the script are static files under public/, loaded from
    /assets/ with a version stamp (OPS-31, OPS-34), and the page still loads
    every one of them.

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
		# Two pages now, not one (slice 034 Wave 1): the live page and the
		# preview page carrying the new frame until the swap. Every include
		# file must belong to ONE of them. A file belonging to neither is still
		# an orphan and still fails here.
		on_disk = {f for f in PS.ess_files_on_disk() if "/parts/" not in f}
		preview = PS.preview_reach()[0]
		self.assertEqual(set(tags) | preview, on_disk,
		                 "an include file belongs to neither portal page")
		self.assertFalse(set(tags) & preview,
		                 "an include file is pulled in by both pages - at the "
		                 "swap that would be the frame twice on one page")

	def test_only_the_pieces_that_need_jinja_are_templates(self):
		"""The whole point of the parts. Frappe compiles at most 32 templates
		per worker and this page's chain already uses about 25, so every piece
		of markup kept as an include file is a slot a later wave cannot have.
		Two pieces genuinely need Jinja - the tenant's brand and one modal's
		placeholder. A third appearing here is a mistake worth catching."""
		templates = {f for f in PS.ess_files_on_disk() if "/parts/" not in f}
		self.assertEqual(
			templates,
			{"templates/includes/ess/frame.html",
			 "templates/includes/ess/growth-modals.html",
			 # The new frame. Two lines in it need Jinja - the tenant's name
			 # and its brand mark - so it cannot be an ess_part, which refuses
			 # a file holding a template tag. It is the only template Wave 1
			 # adds, and OPS-31 freed three slots.
			 "templates/includes/ess/next/frame.html"},
			"a piece of markup became a Jinja template. If it really needs a "
			"Jinja tag, say so here; if it does not, it belongs in parts/.")
		for rel in sorted(templates):
			with open(os.path.join(PS.APP_ROOT, *rel.split("/")), encoding="utf-8") as fh:
				text = fh.read()
			self.assertTrue(any(t in text for t in ("{{", "{%")),
			                rel + " has no Jinja in it, so it belongs in parts/")

	def test_the_page_is_split_by_area(self):
		"""One file per area is what stops two sessions meeting in one file."""
		self.assertGreaterEqual(len(PS.ess_parts_on_disk()), 10)
		for name in ("home", "attendance", "pay", "team", "growth"):
			self.assertIn(name, PS.ess_parts_on_disk())

	def test_the_helper_refuses_a_page_that_asks_for_no_parts(self):
		work = tempfile.mkdtemp()
		try:
			with open(PS.PORTAL_PAGE, "rb") as fh:
				raw = fh.read()
			page = os.path.join(work, "hrms-employee.html")
			with open(page, "wb") as fh:
				fh.write(PS.PART_RE.sub(b"", raw))
			real = PS.PORTAL_PAGE
			PS.PORTAL_PAGE = page
			try:
				with self.assertRaises(PS.PortalSourceError):
					PS.page_bytes(page)
			finally:
				PS.PORTAL_PAGE = real
		finally:
			shutil.rmtree(work, ignore_errors=True)

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

	def test_the_styles_and_script_are_static_files_not_templates(self):
		"""OPS-31. A Jinja template takes one of Frappe's 32 compiled-template
		slots per worker; a static file takes none. That is the whole reason the
		page can be split as finely as it likes from here on, so a style or
		script file creeping back into templates/includes/ess/ fails here."""
		strays = [rel for rel in PS.ess_files_on_disk()
		          if rel.endswith((".css", ".js")) or ".css." in rel or ".js." in rel]
		self.assertEqual(strays, [],
		                 "styles and scripts belong in public/, not in the Jinja "
		                 "includes: " + ", ".join(sorted(strays)))
		self.assertEqual(
			PS.ess_assets_on_disk(),
			{"css/ess/frame.css", "css/ess/panels.css", "js/ess/portal.js",
			 # The new frame's own two, loaded by the preview page.
			 "css/ess/next-frame.css", "js/ess/next-frame.js",
			 # Slice 042, Wave 2: one file per panel, plus their stylesheet.
			 # Home and the Inbox are separate files on purpose - two sessions
			 # building two panels should not meet in one - and OPS-31 made the
			 # split cost nothing, because none of these is a template.
			 "css/ess/next-panels.css", "js/ess/next-home.js",
			 "js/ess/next-inbox.js"})

	def test_the_static_files_hold_no_jinja(self):
		"""They are served raw by nginx. A Jinja tag in one would reach the
		browser as text, so it would never be rendered and never be noticed."""
		offenders = []
		for rel in sorted(PS.ess_assets_on_disk()):
			path = os.path.join(PS.APP_ROOT, "public", *rel.split("/"))
			with open(path, encoding="utf-8") as fh:
				text = fh.read()
			for token in ("{{", "{%", "{#"):
				if token in text:
					offenders.append("%s holds %s" % (rel, token))
		self.assertEqual(offenders, [], "; ".join(offenders))

	def test_the_page_loads_every_static_file_with_a_version(self):
		"""OPS-34. Without ?v= a phone keeps last release's script for ever."""
		with open(PS.PORTAL_PAGE, "rb") as fh:
			raw = fh.read()
		loaded = set()
		for rx in (PS.LINK_RE, PS.SCRIPT_RE):
			for m in rx.finditer(raw):
				loaded.add(m.group(1).decode("utf-8"))
		preview = PS.preview_reach()[1]
		self.assertEqual(loaded | preview, PS.ess_assets_on_disk(),
		                 "a frame asset file is loaded by neither portal page")
		self.assertFalse(loaded & preview,
		                 "a frame asset file is loaded by both pages")
		for rel in sorted(loaded):
			self.assertIn(("/assets/alvoraa_portal/%s?v=" % rel).encode("utf-8"), raw,
			              rel + " is loaded without a version stamp")
		# The preview page needs the stamp just as much: it is served from
		# /assets/ with a month's cache, so an address that never changes means
		# a phone keeps last release's frame (OPS-34).
		with open(PS.PREVIEW_PAGE, "rb") as fh:
			preview_raw = fh.read()
		for rel in sorted(preview):
			self.assertIn(("/assets/alvoraa_portal/%s?v=" % rel).encode("utf-8"), preview_raw,
			              rel + " is loaded without a version stamp on the preview page")

	def test_the_helper_refuses_a_page_that_loads_no_static_files(self):
		"""The other half of AC-37. A page with its <link> and <script src> tags
		removed still has markup in it, so the include guard would pass it - and
		every check would then be reading a page with no CSS and no JavaScript."""
		work = tempfile.mkdtemp()
		try:
			with open(PS.PORTAL_PAGE, "rb") as fh:
				raw = fh.read()
			stripped = PS.SCRIPT_RE.sub(b"", PS.LINK_RE.sub(b"", raw))
			page = os.path.join(work, "hrms-employee.html")
			with open(page, "wb") as fh:
				fh.write(stripped)
			real = PS.PORTAL_PAGE
			PS.PORTAL_PAGE = page
			try:
				with self.assertRaises(PS.PortalSourceError):
					PS.page_bytes(page)
			finally:
				PS.PORTAL_PAGE = real
		finally:
			shutil.rmtree(work, ignore_errors=True)
