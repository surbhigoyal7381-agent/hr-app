"""A message must never be painted underneath a dialog.

THE BUG THIS PINS, 18 Oct 2026. `.toast-wrap` sat at `z-index: 300` and
`.gp-backdrop` at 1200, so every message raised while a dialog was open
rendered BEHIND that dialog's own backdrop. The action failed, the error was
announced, and nobody could see it.

Two features were reported as "the button does nothing" because of it. The
button did plenty: it failed, and said so, into a layer nobody can see.

WHY THIS IS WORTH A TEST, when it is three numbers in a stylesheet. An
invisible error is worse than a crash. A crash gets reported with a stack; this
teaches people the screen lies, and they stop reporting anything. It also cost
real time to find, because every test passed the whole way through.

WHY IT IS WRITTEN AS A RULE rather than two pinned numbers. Pinning
`.toast-wrap: 3000` would pass while somebody added a NEW dialog at 4000, which
is the same bug with different numbers. The rule is the invariant: whatever
announces something must sit above whatever covers the page.
"""

import os
import re

from frappe.tests.utils import FrappeTestCase

CSS_DIR = os.path.join(
	os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
	"public", "css", "ess")

# What announces something to the person, and what covers the page while a
# decision is pending. Matched on the selector, so a new toast stack or a new
# dialog is caught without this list being updated.
ANNOUNCES = re.compile(r"toast", re.I)
COVERS = re.compile(r"backdrop|modal|overlay|sheet", re.I)

RULE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)
Z = re.compile(r"z-index\s*:\s*(-?\d+)")


def _page_of(filename):
	"""Which PAGE a stylesheet belongs to.

	z-index only orders things inside ONE document, so layers from two
	stylesheets that never load together cannot hide each other. The portal
	and the `-next` page are separate documents with separate stylesheets
	(see `test_portal_split_034`), and comparing across them reported a
	false fault the first time this test was written: `.nf-toasts` at 70
	against `.gp-backdrop` at 1200, two pages apart.
	"""
	return "next" if filename.startswith("next-") else "portal"


def _layers():
	"""Every selector in the ESS stylesheets that sets a z-index."""
	out = []
	for name in sorted(os.listdir(CSS_DIR)):
		if not name.endswith(".css"):
			continue
		path = os.path.join(CSS_DIR, name)
		with open(path, encoding="utf-8") as fh:
			text = fh.read()
		# Comments can hold braces and example rules; drop them first so a
		# commented-out z-index cannot fail a real one.
		text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
		for selector, body in RULE.findall(text):
			found = Z.search(body)
			if found:
				out.append((name, " ".join(selector.split()),
				            int(found.group(1)), _page_of(name)))
	return out


class TestAMessageIsNeverHiddenByADialog(FrappeTestCase):
	def test_the_stylesheets_set_some_layers_at_all(self):
		"""Guards the test itself: a parser that silently matched nothing
		would make every assertion below pass for the wrong reason."""
		layers = _layers()
		self.assertGreater(len(layers), 3,
		                   "no z-index rules were found - the parser is wrong, "
		                   "not the stylesheet")
		self.assertTrue(any(ANNOUNCES.search(s) for _f, s, _z, _p in layers),
		                "no toast layer found; this test is no longer checking "
		                "what it claims to")
		self.assertTrue(any(COVERS.search(s) for _f, s, _z, _p in layers),
		                "no dialog layer found; this test is no longer checking "
		                "what it claims to")

	def test_every_message_sits_above_every_dialog(self):
		"""The invariant, not the numbers.

		Pinning today's values would pass while somebody adds a new dialog
		above today's toasts - the same bug with different numbers.
		"""
		layers = _layers()
		checked = 0
		for page in sorted({p for _f, _s, _z, p in layers}):
			here = [r for r in layers if r[3] == page]
			messages = [r for r in here if ANNOUNCES.search(r[1])]
			dialogs = [r for r in here if COVERS.search(r[1])
			           and not ANNOUNCES.search(r[1])]
			if not messages or not dialogs:
				continue        # nothing on this page can hide anything
			highest = max(dialogs, key=lambda r: r[2])
			for f, s, z, _p in messages:
				checked += 1
				self.assertGreater(
					z, highest[2],
					"on the %s page, %s sets %s to z-index %d, under %s at %d "
					"(%s). A message raised while that dialog is open would be "
					"painted beneath it, so the person sees nothing happen."
					% (page, f, s, z, highest[1], highest[2], highest[0]))
		self.assertGreater(checked, 0,
		                   "no page had both a message layer and a dialog "
		                   "layer, so nothing was actually compared")

	def test_the_two_toast_stacks_agree_with_each_other(self):
		"""There are two of them, and they must not disagree. One sat at 300
		and the other at 3000; the page used whichever the caller reached for,
		so the same error was visible or invisible depending on which helper
		raised it."""
		layers = _layers()
		stacks = {s: z for _f, s, z, p in layers
		          if ANNOUNCES.search(s) and "wrap" in s and p == "portal"}
		self.assertGreaterEqual(len(stacks), 2,
		                        "expected more than one toast container; if one "
		                        "was removed, delete this test with it")
		self.assertEqual(
			len(set(stacks.values())), 1,
			"the toast containers sit at different heights: %s. Whether an "
			"error is visible then depends on which helper raised it."
			% stacks)
