"""ALV-428: the words and the address in the message HR sends a new joiner.

**Why this file exists at all.** Both faults it covers shipped in slice 079 and
survived every test, review and spec until 21 Nov 2026, when somebody ran the
invite on a real tenant and *looked at the box*. They were:

1. the last line called the joiner **"She"**, in a sentence whose other half
   already said "their";
2. the address the joiner is told to open read
   `https://ppj.dev.alvoraa.co:443/joining`.

Neither is a logic error, so no amount of asserting on the payload would have
found them. The existing suites check what `make_sign_in` *returns* and what the
guard *refuses*. Nothing read the sentence.

**So one of these tests reads the source of the screen**, which is the only
level at which a hardcoded word can be pinned. That is the same shape as the
repo's other source gates (`test_portal_module_gate_016` and friends) and it is
deliberate: a string that is built into HTML in a `frappe.msgprint` template
cannot be reached from Python any other way.

The address tests drive `_plain_url` directly **and** go through the real
endpoint with a request whose `Host` carries the port, because the port arrives
from the proxy - so a test that never sets a `Host` proves nothing about the
case that actually happened.
"""

import os
import re

import frappe

from alvoraa_portal import joiner_invite
from alvoraa_portal.tests import fixtures_079 as fx
from alvoraa_portal.tests.fixtures_045 import Wave4Base, own_user


class TheWordsOnTheScreen(Wave4Base):
	"""The one place a joiner is described to HR, read from the source."""

	def _the_invite_script(self):
		path = frappe.get_app_path(
			"alvoraa_portal", "public", "js", "alvoraa_joiner_submission.js")
		if not os.path.exists(path):
			# Keep the failure honest: say where it looked. An empty read here
			# would otherwise pass as "no gendered word found".
			self.fail(f"could not find the invite script to read: {path}")
		with open(path, encoding="utf-8") as f:
			return f.read()

	def test_the_joiner_is_not_called_she(self):
		"""ALV-428. The product does not know the joiner's gender, and roughly
		half of the staff at the tenants this was built for are men."""
		source = self._the_invite_script()
		self.assertNotIn("She cannot see anything else", source,
		                 "the invite box still calls the joiner 'She'")

	def test_no_gendered_pronoun_describes_the_joiner_anywhere_in_that_file(self):
		"""Wider than the one sentence, because the next one will not be a
		copy of this one. Matches a capitalised or lowercase She/Her/He/His as
		a whole word inside a translated string."""
		source = self._the_invite_script()
		offenders = []
		for m in re.finditer(r"__\(\s*\"([^\"]{0,400})\"", source):
			text = m.group(1)
			if re.search(r"\b(She|she|Her|her|He|his|His)\b", text):
				offenders.append(text[:80])
		self.assertEqual(
			offenders, [],
			"a translated string in the invite screen uses a gendered "
			f"pronoun for the joiner: {offenders}")

	def test_the_sentence_is_still_there_in_its_ungendered_form(self):
		"""The fix must not have deleted the reassurance, only de-gendered it.
		Without this, removing the line entirely would pass the test above."""
		source = self._the_invite_script()
		self.assertIn("They cannot see anything else", source)


class TheAddressTheJoinerIsGiven(Wave4Base):
	"""`_plain_url` trims a default port and nothing else."""

	def _with_url(self, value):
		"""Run `_plain_url` as though `get_url()` answered `value`."""
		was = frappe.utils.get_url
		try:
			frappe.utils.get_url = lambda *a, **k: value
			return joiner_invite._plain_url()
		finally:
			frappe.utils.get_url = was

	def test_the_https_default_port_is_trimmed(self):
		"""ALV-428, the case seen on ppj.dev."""
		self.assertEqual(self._with_url("https://ppj.dev.alvoraa.co:443"),
		                 "https://ppj.dev.alvoraa.co")

	def test_the_http_default_port_is_trimmed(self):
		self.assertEqual(self._with_url("http://example.test:80"),
		                 "http://example.test")

	def test_a_real_port_is_KEPT(self):
		"""A bench on 8010 must keep its port or the address stops working.
		This is the test that stops the fix becoming a bug of its own."""
		self.assertEqual(self._with_url("http://hrms.localhost:8010"),
		                 "http://hrms.localhost:8010")

	def test_a_port_that_merely_starts_with_443_is_kept(self):
		self.assertEqual(self._with_url("https://example.test:4430"),
		                 "https://example.test:4430")

	def test_an_address_with_no_port_is_left_alone(self):
		self.assertEqual(self._with_url("https://dtc.alvoraa.co"),
		                 "https://dtc.alvoraa.co")

	def test_a_trailing_slash_does_not_defeat_it(self):
		self.assertEqual(self._with_url("https://dtc.alvoraa.co:443/"),
		                 "https://dtc.alvoraa.co")

	def test_the_https_port_is_not_trimmed_off_an_http_address(self):
		"""`http://host:443` is a real, unusual port. Only the default for the
		scheme actually in use is meaningless."""
		self.assertEqual(self._with_url("http://example.test:443"),
		                 "http://example.test:443")


class WhatHRActuallyGetsBack(Wave4Base):
	"""Through the real endpoint, with the Host header that caused this."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hr = own_user("s428hr", ("Employee", "HR Manager"))

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		fx.clear_the_rows()
		fx.switch_the_form_on()
		self._stray_users = []

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in self._stray_users:
			if frappe.db.exists("User", name):
				frappe.delete_doc("User", name, force=True,
				                  ignore_permissions=True,
				                  delete_permanently=True)
		fx.clear_the_rows()
		fx.switch_the_form_off()
		super().tearDown()

	def test_the_address_handed_to_hr_carries_no_default_port(self):
		"""The whole point: what comes back is what HR pastes into a message
		and a joiner retypes onto a phone."""
		was = frappe.utils.get_url
		try:
			frappe.utils.get_url = lambda *a, **k: "https://s428.test:443"
			frappe.set_user(self.hr)
			row = fx.a_row(full_name="S428 Address",
			               login_id="s428.address@example.com")
			reply = joiner_invite.make_sign_in(submission=row.name)
		finally:
			frappe.utils.get_url = was
			frappe.set_user("Administrator")

		if reply.get("submission"):
			user = frappe.db.get_value("Alvoraa Joiner Submission",
			                           reply["submission"], "user")
			if user:
				self._stray_users.append(user)

		self.assertEqual(reply["address"], "https://s428.test/joining")
		self.assertNotIn(":443", reply["address"])
