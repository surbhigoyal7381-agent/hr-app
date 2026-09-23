"""Slice 042, Wave 2: what the panels cost, and what the tests are allowed to do.

Two rules, neither about behaviour, both about how the next change goes wrong.

**AC-44 - Wave 2 adds no Jinja template.** Frappe compiles at most 32 templates
per worker and this page's chain already uses about 25. OPS-31 landed in Wave 1,
so markup is pasted in by `ess_part()` - a file holding no template tag, which
is read and pasted rather than compiled and takes **no cache slot at all**. Home
and the Inbox therefore get their own markup, style and script files for free.
What must not happen is somebody reaching for `{% include %}` again out of
habit, so the set of real templates is pinned in
`test_portal_split_034.test_only_the_pieces_that_need_jinja_are_templates` and
what is checked here is the other half: the new pieces really are parts and
static files, loaded with a `?v=` stamp so a phone cannot keep last release's
script against this release's markup.

**AC-62 - no test in this slice may patch the feature gate.** A patched gate
turns every entitlement test green while proving nothing, and it has happened in
this repository before: `subscription.py`'s own docstring records it. So the
check is on the TEST FILES, not on the product code, and it is absolute - any
mention of patching `has_feature`, `requires_feature` or `enabled_features`
fails the build. The real way to test an entitlement is to change the site's own
`features` list, which is what a tenant without payroll actually has, and
`test_home_api_042.TestTheRealEntitlementGate` does exactly that.
"""

import os
import re

from frappe.tests.utils import FrappeTestCase

import alvoraa_portal
from alvoraa_portal import ess_parts
from alvoraa_portal.tests import portal_source as PS

# The markup, style and script files Wave 2 adds. Named, so that adding a fourth
# without a line here is a failure rather than a silent extra file.
NEW_PARTS = ("next-home", "next-inbox")
NEW_STYLES = ("css/ess/next-panels.css",)
NEW_SCRIPTS = ("js/ess/next-home.js", "js/ess/next-inbox.js")

# Every test file this slice added or touched.
SLICE_TESTS = (
	"test_inbox_parts_042.py",
	"test_home_api_042.py",
	"test_week_presence_retired_042.py",
	"test_panel_source_042.py",
	"fixtures_042.py",
)

# The three names a test must never patch, written in pieces so this file does
# not fail its own check.
GATE_NAMES = ("has_" + "feature", "requires_" + "feature", "enabled_" + "features")

# What a patch actually LOOKS LIKE, rather than the word "patch" anywhere on the
# line. The first version of this check matched its own docstring and the
# sentence in `test_home_api_042` explaining that it does NOT patch the gate -
# a check that fires on prose is a check somebody turns off.
_GATES = "|".join(GATE_NAMES)
PATCH_RE = re.compile(
	r"(?:patch|patch\.object|setattr|monkeypatch\.setattr)\s*\([^)]*(?:%s)" % _GATES
	+ r"|(?:%s)\s*=\s*(?:MagicMock|Mock|lambda)" % _GATES)


def _tests_dir():
	return os.path.join(os.path.dirname(os.path.abspath(alvoraa_portal.__file__)), "tests")


class TestWaveTwoAddsNoTemplate(FrappeTestCase):

	def test_the_new_markup_is_parts_and_holds_no_template_tag(self):
		on_disk = ess_parts.parts_on_disk()
		for name in NEW_PARTS:
			self.assertIn(name, on_disk, "%s is not a markup part" % name)
			with open(os.path.join(ess_parts.PARTS_DIR, name + ".html"),
			          encoding="utf-8") as fh:
				text = fh.read()
			for token in ("{" "{", "{" "%", "{" "#"):
				self.assertNotIn(
					token, text,
					"%s holds a template tag, so ess_part() would refuse it at "
					"run time and the skeleton would never load" % name)

	def test_ess_part_really_loads_them(self):
		"""The check above reads the file; this one asks the helper, which is
		what the page actually calls. A part that passes the first and fails the
		second is a part nobody sees."""
		for name in NEW_PARTS:
			body = str(ess_parts.ess_part(name))
			self.assertIn("nf-skeleton", body,
			              "%s came back without its skeleton markup" % name)

	def test_the_preview_page_pastes_both_skeletons_in(self):
		reached = PS.preview_reach()[2]
		for name in NEW_PARTS:
			self.assertIn(name, reached,
			              "%s exists but no page asks for it, so its contents "
			              "are checked by nobody" % name)

	def test_the_new_style_and_script_are_static_files_with_a_version_stamp(self):
		with open(PS.PREVIEW_PAGE, encoding="utf-8") as fh:
			page = fh.read()
		for rel in NEW_STYLES + NEW_SCRIPTS:
			self.assertIn(
				"/assets/alvoraa_portal/" + rel, page,
				"%s is not loaded by the preview page" % rel)
			# `?v={{ asset_version }}`: a new release is a new address, so no
			# phone keeps last release's script against this release's markup.
			pattern = re.escape("/assets/alvoraa_portal/" + rel) + r"\?v="
			self.assertRegex(page, pattern,
			                 "%s is loaded with no version stamp" % rel)

	def test_the_script_files_are_reached_and_not_orphans(self):
		reached = PS.preview_reach()[1]
		for rel in NEW_STYLES + NEW_SCRIPTS:
			self.assertIn(rel, reached)


class TestNoTestPatchesTheEntitlementGate(FrappeTestCase):

	def test_no_test_in_this_slice_patches_the_feature_gate(self):
		"""042 AC-62. A patched gate proves nothing, very convincingly."""
		root = _tests_dir()
		offenders = []
		checked = 0
		for name in SLICE_TESTS:
			path = os.path.join(root, name)
			if not os.path.isfile(path):
				offenders.append(name + " is missing from the slice")
				continue
			checked += 1
			with open(path, encoding="utf-8") as fh:
				for number, line in enumerate(fh, 1):
					if PATCH_RE.search(line):
						offenders.append("%s:%d replaces the real gate" % (name, number))
		self.assertEqual(
			checked, len(SLICE_TESTS),
			"only %d of this slice's %d test files were read, so the check "
			"below proved less than it looks" % (checked, len(SLICE_TESTS)))
		self.assertEqual(offenders, [], "; ".join(offenders))

	def test_the_check_would_notice(self):
		"""The check on the check. A line that DOES patch the gate must match,
		or the test above is a comment with a green tick beside it."""
		real = "with patch('alvoraa_portal.subscription.%s') as gate:" % GATE_NAMES[0]
		self.assertTrue(PATCH_RE.search(real),
		                "the pattern does not catch a real patch")
		also = "    %s = lambda name: True" % GATE_NAMES[0]
		self.assertTrue(PATCH_RE.search(also),
		                "the pattern does not catch a hand-rolled stand-in")
		# ...and it does NOT fire on a sentence about patching, which is what
		# the first version of this check got wrong.
		prose = "    # a test must never patch the %s gate" % GATE_NAMES[0]
		self.assertFalse(PATCH_RE.search(prose),
		                 "the pattern fires on prose, so somebody will turn it off")
