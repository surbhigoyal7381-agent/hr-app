"""ALV-305: the words a joiner reads live in two files, so they must agree.

The settings picker tells HR what the joiner will actually see on the joining
form - the one honest answer to "what does this tick do to somebody else's
screen". Those words exist twice:

  * ``joining.html``'s ``LABELS``, Jinja-translated when the page renders, and
  * ``portal.js``'s ``OCS_JOINER_READS``, translated in the browser.

They cannot be one source: the two use different translation mechanisms, and a
server constant rendered through both would be more code than the copy. The
duplication is the deliberate, cheaper choice (design open question 5), and
**this test is what pays for it.** If one is reworded and the other is not, the
settings screen starts lying about somebody else's form, and CI says so here.
"""

import os
import re
import unittest

import alvoraa_portal

APP_DIR = os.path.dirname(os.path.abspath(alvoraa_portal.__file__))
JOINING = os.path.join(APP_DIR, "www", "joining.html")
PORTAL_JS = os.path.join(APP_DIR, "public", "js", "ess", "portal.js")

# The six the joiner picker offers, which are `MY_PROFILE_WRITE_FIELDS` by
# identity. `full_name` is HR's own entry at invite, never a tick, so the
# picker never shows it and it is not compared here.
SIX = (
	"cell_number",
	"personal_email",
	"current_address",
	"person_to_be_contacted",
	"relation",
	"emergency_phone_number",
)


def _block(text, start, end="};"):
	"""The body of one `var NAME = {...};` literal, by text."""
	at = text.index(start)
	return text[at : text.index(end, at)]


def _joining_labels():
	"""`field: [{{ _("Label") | tojson }}, {{ _("Hint") | tojson }}]`."""
	body = _block(open(JOINING, encoding="utf-8").read(), "var LABELS = {")
	out = {}
	for name, rest in re.findall(r"(\w+):\s*\[(.*?)\],?\s*\n", body):
		words = re.findall(r'_\(\s*"((?:[^"\\]|\\.)*)"\s*\)', rest)
		# `personal_email: [..., ""]` has no hint, so the list is shorter.
		out[name] = [words[0] if words else "", words[1] if len(words) > 1 else ""]
	return out


def _portal_reads():
	"""`field: ["Label", "Hint"]`."""
	body = _block(open(PORTAL_JS, encoding="utf-8").read(), "var OCS_JOINER_READS = {")
	out = {}
	for name, rest in re.findall(r"(\w+):\s*\[(.*?)\],?\s*\n", body):
		words = re.findall(r'"((?:[^"\\]|\\.)*)"', rest)
		out[name] = [words[0] if words else "", words[1] if len(words) > 1 else ""]
	return out


class TestTheJoinerWordsAgree(unittest.TestCase):
	def test_the_picker_quotes_the_joining_form_exactly(self):
		"""Both files, word for word, for all six fields."""
		page = _joining_labels()
		picker = _portal_reads()
		# Not vacuous: if either regex stops matching, this is what fails first.
		self.assertGreaterEqual(len(page), len(SIX) + 1)  # the six plus full_name
		self.assertEqual(len(picker), len(SIX))
		for field in SIX:
			with self.subTest(field=field):
				self.assertIn(field, page, "joining.html no longer asks for it")
				self.assertEqual(
					picker[field],
					page[field],
					"the settings picker and the joining form disagree about "
					f"{field}, so HR is being told the wrong thing about the "
					"joiner's screen",
				)

	def test_the_picker_never_shows_a_database_column(self):
		"""ALV-305 itself. `ocsWord()` fell through to `return field` for the
		joiner key, so the dialog printed `cell_number` and
		`person_to_be_contacted`. The plain words were twenty lines above it."""
		source = open(PORTAL_JS, encoding="utf-8").read()
		body = _block(source, "function ocsWord(key, field) {", "\n}")
		self.assertIn(
			"OCS_JOINER_KEY",
			body,
			"the joiner key must reach the plain words, or the dialog "
			"falls through to the raw column name again",
		)
		words = _block(source, "var OCS_MY_WORDS = {")
		for field in SIX:
			with self.subTest(field=field):
				self.assertIn(field + ":", words)
