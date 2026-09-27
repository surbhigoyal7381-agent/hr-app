"""045 AC-6 / US-12 - the Team screen's call stops handing over the Employee row.

`hr_api.get_manager_dashboard` returned `"manager": emp`, where `emp` is
`_get_employee()`'s complete record: date_of_birth, gender, cell_number,
branch, date_of_joining and reports_to. Every browser that drew a Team screen
was handed all of them. Nothing on the screen ever read one - which is the part
worth remembering, because a leak nobody uses is a leak nobody notices.

Two things make this test able to fail, and both are requirements, not style:

1. **The fixture populates all six fields.** Wave 3's AC-17 asserted that an
   email did not contain a rupee amount that was never in it, while the real
   leak went out beside it. A "must not contain" check against an empty
   fixture passes on the day it is written and proves nothing.
2. **The assertion searches the serialised payload recursively.** Not the
   `manager` key. The next leak will be under a different key, or three levels
   down inside a list of rows, and a named-key check would not see it.
"""

import json

import frappe

from alvoraa_portal import hr_api
from alvoraa_portal.frame_api import ME_FIELDS
from alvoraa_portal.tests.fixtures_045 import FORBIDDEN_VALUES, Wave4Base


def walk(node, path="$"):
	"""Every (path, scalar) pair in a nested payload.

	The recursion is the assertion's whole value. `json.dumps` alone would find
	a string but could not say where it was, and "somewhere in the payload" is
	not a bug report anybody can act on.
	"""
	if isinstance(node, dict):
		for key, value in node.items():
			yield from walk(value, f"{path}.{key}")
	elif isinstance(node, (list, tuple)):
		for i, value in enumerate(node):
			yield from walk(value, f"{path}[{i}]")
	else:
		yield path, node


def find_value(payload, needle):
	"""Every path whose value contains `needle`, as a string."""
	found = []
	for path, value in walk(payload):
		if value is None:
			continue
		if needle.lower() in str(value).lower():
			found.append(path)
	return found


def find_key(node, wanted, path="$"):
	"""Every path at which a key called `wanted` appears, however deep.

	Two of AC-6's six fields cannot be caught by searching for their value.
	`gender` holds "Male", and `reports_to` holds an Employee id that the team
	rows legitimately carry as their own `name` - so a value search would
	either miss them or report a hit that is not a leak. For those two the leak
	is the FIELD being carried at all, so the key is what is searched for.
	"""
	found = []
	if isinstance(node, dict):
		for key, value in node.items():
			if key == wanted:
				found.append(f"{path}.{key}")
			found += find_key(value, wanted, f"{path}.{key}")
	elif isinstance(node, (list, tuple)):
		for i, value in enumerate(node):
			found += find_key(value, wanted, f"{path}[{i}]")
	return found


class TestTheCallerBlockIsSixKeys(Wave4Base):
	def _dash(self, user):
		self.as_user(user)
		d = hr_api.get_manager_dashboard()
		self.assertFalse(d.get("no_employee"),
		                 "the fixture's caller has no Active Employee record")
		return d

	def test_the_fixture_really_does_populate_every_forbidden_field(self):
		"""The check on the check.

		If this fails, every "must not contain" test in this file is passing
		over nothing - which is the failure mode that is invisible from the
		outside, so it is asserted from the inside instead.
		"""
		row = frappe.db.get_value(
			"Employee", self.sandeep,
			["date_of_birth", "gender", "cell_number", "date_of_joining", "branch"],
			as_dict=True,
		)
		for field, value in row.items():
			self.assertTrue(value, f"fixture left {field} empty, so AC-6 proves nothing")
		self.assertTrue(frappe.db.get_value("Employee", self.rahul, "reports_to"),
		                "fixture left reports_to empty on Rahul")

	def test_the_caller_block_is_exactly_me_fields(self):
		"""AC-6, the positive half. Six keys, and the six are ME_FIELDS."""
		for user in (self.sandeep_user, self.kamal_user, self.priya_user):
			with self.subTest(user=user):
				d = self._dash(user)
				self.assertIn("me", d, "the caller block is gone entirely")
				self.assertIsNotNone(d["me"])
				self.assertEqual(set(d["me"].keys()), set(ME_FIELDS))

	def test_the_old_manager_key_is_gone(self):
		"""The key is renamed as well as narrowed.

		Calling a whole Employee record "manager" is what made it look like a
		reasonable thing to put in a payload. Nothing reads `d.manager` - the
		only caller is `portal.js:3474`, checked by hand.
		"""
		for user in (self.sandeep_user, self.kamal_user, self.priya_user):
			with self.subTest(user=user):
				self.assertNotIn("manager", self._dash(user))

	def test_no_forbidden_value_appears_anywhere_in_the_payload(self):
		"""AC-6, the half that catches the NEXT leak.

		Searched recursively over the serialised payload, per persona, for
		values that are really in the database. A named-key check would pass
		the moment somebody added a second key carrying the same row.
		"""
		for user in (self.sandeep_user, self.kamal_user, self.priya_user):
			d = self._dash(user)
			# Proves the payload is not empty, so absence means absence.
			self.assertTrue(json.dumps(d, default=str), "empty payload")
			for field, needle in FORBIDDEN_VALUES.items():
				with self.subTest(user=user, field=field):
					where = find_value(d, needle)
					self.assertEqual(
						[], where,
						f"{field} ({needle}) reached the Team payload at {where}")

	def test_gender_and_reports_to_are_not_carried_as_fields_at_all(self):
		"""AC-6's other two, checked by key rather than by value.

		`gender` holds "Male" and `reports_to` holds an Employee id the team
		rows carry legitimately as their own `name`, so a value search would
		lie in both directions. For these two the leak is the field being
		present, so that is what is asserted.
		"""
		for user in (self.sandeep_user, self.kamal_user, self.priya_user):
			d = self._dash(user)
			for field in ("gender", "date_of_birth", "cell_number", "branch",
			              "date_of_joining", "reports_to"):
				with self.subTest(user=user, field=field):
					where = find_key(d, field)
					self.assertEqual([], where,
					                 f"the Team payload carries {field} at {where}")

	def test_the_assertion_can_fail(self):
		"""Check the check, the other way round.

		A negative test that cannot go red is decoration. This proves the
		recursive search finds a forbidden value when one is genuinely there,
		including one buried in a list of rows.
		"""
		needle = FORBIDDEN_VALUES["cell_number"]
		planted = {"team": [{"name": "X", "nested": {"deep": needle}}]}
		self.assertEqual(["$.team[0].nested.deep"], find_value(planted, needle))
		self.assertEqual([], find_value({"team": [{"name": "X"}]}, needle))
		# And the key search, the same way round.
		self.assertEqual(["$.team[0].gender"],
		                 find_key({"team": [{"gender": "Male"}]}, "gender"))
		self.assertEqual([], find_key({"team": [{"name": "X"}]}, "gender"))
