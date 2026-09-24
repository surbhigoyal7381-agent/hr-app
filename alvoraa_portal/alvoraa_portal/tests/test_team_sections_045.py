"""045 AC-73 to AC-80 - the Team screen's two sections, and the eleven-row matrix.

Surbhi's decision of 24 September 2026: the Team screen separates the two
reasons a person is on it, and the actions follow.

**The eleven-row action matrix in the spec is an eleven-row PERMISSION matrix.**
045 SEC-18 makes that a requirement and adds the reason: a matrix is the shape
where one row gets missed, and the miss stays invisible until somebody presses
it. So every row is called by hand here, for every relationship, rather than
checked as a group.

Two things this file refuses to do, both because they would prove the screen
and not the rule:

* It does not only check which keys are absent from a payload. Absence in a
  payload is a screen fact. The matrix is called directly as well.
* It does not pass a section to anything. **The section is derived** (SEC-18b),
  and a test supplies one anyway and asserts it changes nothing.
"""

import frappe

from alvoraa_portal import team_api
from alvoraa_portal.tests.fixtures_045 import Wave4Base


class _Team(Wave4Base):
	def _team(self, user):
		self.as_user(user)
		d = team_api.get_team()
		self.assertFalse(d.get("no_employee"), "the caller has no Employee record")
		return d

	def _names(self, section):
		return [r["name"] for r in (section or {}).get("rows", [])]


class TestTwoSectionsAndNeverAnEmptyHeading(_Team):
	def test_a_plain_manager_gets_your_team_only(self):
		"""AC-73. Sandeep manages people and is NOT HR, so `covered` is not
		drawn at all - not drawn empty, not drawn hidden."""
		d = self._team(self.sandeep_user)
		self.assertTrue(d["has_direct"])
		self.assertFalse(d["is_hr_scope"])
		self.assertIsNone(d["covered"], "a non-HR caller was sent a covered section")
		self.assertFalse(d["has_covered"])

	def test_store_hr_with_no_reports_gets_you_cover_only(self):
		"""AC-73. Priya manages nobody, so "Your team" has no rows and the
		screen must not draw the heading."""
		d = self._team(self.priya_user)
		self.assertTrue(d["is_hr_scope"])
		self.assertIsNotNone(d["covered"])
		self.assertEqual(0, d["direct"]["total"])
		self.assertFalse(d["has_direct"], "an empty 'Your team' heading would be drawn")

	def test_a_covered_person_with_no_manager_at_all_is_still_covered(self):
		"""**A pin on something load-bearing that is easy to get wrong.**

		"You cover" is the HR scope minus the direct reports, written as
		`reports_to != me`. In plain SQL that drops every row whose
		`reports_to` is NULL, because `NULL != 'X'` is NULL - and most people
		in a real store have no manager recorded at all, so the section would
		come back nearly empty and look merely "small".

		Frappe wraps `!=` in `ifnull(...)`, so it works. This test is here
		because that is a fact about the framework, not about our code, and a
		framework change would break the screen silently.
		"""
		d = self._team(self.priya_user)
		covered = self._names(d["covered"])
		no_manager = [e for e in self.covered_only
		              if not frappe.db.get_value("Employee", e, "reports_to")]
		self.assertTrue(no_manager, "the fixture has nobody without a manager, "
		                            "so this proves nothing")
		for who in no_manager:
			self.assertIn(who, covered,
			              "somebody with no manager fell out of 'You cover'")

	def test_somebody_who_is_both_gets_both_headings(self):
		"""AC-73. Kamal holds HR Manager and manages people."""
		d = self._team(self.kamal_user)
		self.assertTrue(d["has_direct"])
		self.assertTrue(d["has_covered"])

	def test_there_is_no_combined_total_anywhere_in_the_payload(self):
		"""AC-74. A combined number would equal no list on the screen.

		Asserted by arithmetic rather than by naming keys: no value anywhere in
		the payload equals direct + covered, unless one of them is zero and the
		sum is therefore a real section's own total.
		"""
		d = self._team(self.kamal_user)
		a, b = d["direct"]["total"], d["covered"]["total"]
		if a and b:
			from alvoraa_portal.tests.test_team_payload_045 import walk

			for path, value in walk(d):
				if isinstance(value, int) and not isinstance(value, bool):
					self.assertNotEqual(a + b, value,
					                    f"a combined Team total appears at {path}")


class TestTheTwoSectionsShareNobody(_Team):
	def test_the_both_person_appears_once_and_only_under_your_team(self):
		"""AC-75. Kamal's report who is also in his HR scope."""
		d = self._team(self.kamal_user)
		direct, covered = self._names(d["direct"]), self._names(d["covered"])
		self.assertIn(self.kamal_both, direct)
		self.assertNotIn(self.kamal_both, covered,
		                 "the both-person is listed twice")
		self.assertEqual(set(), set(direct) & set(covered),
		                 "the two sections share people")

	def test_the_both_person_gets_the_manager_actions_plus_the_hr_only_ones(self):
		"""AC-75's second half, and the case an engineer would guess at.

		Being their manager must not take an HR caller's HR entitlements away.
		"""
		d = self._team(self.kamal_user)
		row = next(r for r in d["direct"]["rows"] if r["name"] == self.kamal_both)
		self.assertTrue(row["also_covered"])
		for act in (team_api.ACT_APPROVE_LEAVE, team_api.ACT_SET_GOALS,
		            team_api.ACT_SEE_SCORECARD):
			self.assertIn(act, row["actions"], "a manager action is missing")
		for act in (team_api.ACT_INVITE_OR_BLOCK_PHONE,
		            team_api.ACT_CANCEL_DEDUCTION, team_api.ACT_ACT_AS_HR):
			self.assertIn(act, row["actions"], "an HR-only action is missing")

	def test_each_count_equals_its_own_list_or_says_it_is_capped(self):
		"""AC-74 / AC-12."""
		for user in (self.sandeep_user, self.priya_user, self.kamal_user):
			d = self._team(user)
			for key in ("direct", "covered"):
				section = d[key]
				if not section:
					continue
				with self.subTest(user=user, section=key):
					rows = len(section["rows"])
					if section["capped"]:
						self.assertEqual(section["cap"], rows)
						self.assertGreater(section["total"], rows)
					else:
						self.assertEqual(section["total"], rows)


class TestTheElevenRowsCalledByHand(_Team):
	"""SEC-18(a). Eleven UI rows are eleven server checks."""

	def test_every_row_of_the_matrix_is_checked_for_a_direct_report(self):
		self.as_user(self.sandeep_user)
		for act, on_direct, _on_covered in team_api.ACTION_MATRIX:
			with self.subTest(action=act):
				ok, reason = team_api.may(act, self.rahul)
				self.assertEqual(on_direct, ok, f"{act} on a direct report")
				if not ok:
					self.assertTrue(reason, "a refusal with no sentence")

	def test_every_row_of_the_matrix_is_checked_for_a_covered_person(self):
		"""AC-77 / AC-80. Priya's people are covered, never her reports."""
		self.as_user(self.priya_user)
		target = self.covered_only[0]
		for act, _on_direct, on_covered in team_api.ACTION_MATRIX:
			with self.subTest(action=act):
				ok, _reason = team_api.may(act, target)
				self.assertEqual(on_covered, ok, f"{act} on a covered person")

	def test_a_manager_who_is_not_hr_gets_no_hr_only_action(self):
		"""AC-80. Sandeep manages nineteen people and holds no HR role."""
		self.as_user(self.sandeep_user)
		for act in (team_api.ACT_INVITE_OR_BLOCK_PHONE,
		            team_api.ACT_CANCEL_DEDUCTION, team_api.ACT_ACT_AS_HR):
			with self.subTest(action=act):
				ok, _r = team_api.may(act, self.rahul)
				self.assertFalse(ok, f"a plain manager was allowed {act}")

	def test_a_stranger_is_refused_every_row(self):
		"""Fail closed on anything about a person."""
		self.as_user(self.rahul_user)
		for act in team_api.ALL_ACTIONS:
			with self.subTest(action=act):
				ok, reason = team_api.may(act, self.covered_only[0])
				self.assertFalse(ok)
				self.assertIn("not part of your access", reason)

	def test_the_refusals_read_identically_whatever_the_cause(self):
		"""A different sentence for a different cause tells the caller which
		guess was closer."""
		self.as_user(self.priya_user)
		_ok_a, out_of_scope = team_api.may(team_api.ACT_OPEN_RECORD, "NO-SUCH-EMPLOYEE")
		_ok_b, not_allowed = team_api.may(team_api.ACT_APPROVE_LEAVE, self.covered_only[0])
		self.assertEqual(out_of_scope, not_allowed)

	def test_an_unknown_action_is_refused_and_not_ignored(self):
		self.as_user(self.kamal_user)
		ok, reason = team_api.may("delete_everything", self.kamal_both)
		self.assertFalse(ok)
		self.assertTrue(reason)


class TestTheSectionIsDerivedNeverDeclared(_Team):
	def test_no_endpoint_here_takes_a_section_argument(self):
		"""SEC-18(b). `direct` means `reports_to = me` at this moment."""
		import inspect

		for fn in (team_api.get_team, team_api.may):
			params = set(inspect.signature(fn).parameters)
			with self.subTest(fn=fn.__name__):
				self.assertEqual(set(), params & {"section", "basis", "is_direct",
				                                  "is_hr", "covered", "direct"})

	def test_passing_a_section_anyway_changes_nothing(self):
		"""Called with a section in the arguments, the whitelisted endpoint
		must behave exactly as it does without one."""
		self.as_user(self.priya_user)
		plain = team_api.get_team()
		frappe.local.form_dict.update({"section": "direct", "basis": "direct"})
		try:
			with_hint = team_api.get_team()
		finally:
			for k in ("section", "basis"):
				frappe.local.form_dict.pop(k, None)
		self.assertEqual(self._names(plain["direct"]), self._names(with_hint["direct"]))
		self.assertEqual(self._names(plain["covered"]), self._names(with_hint["covered"]))

	def test_moving_reports_to_moves_the_person_between_sections(self):
		"""The derivation is live, which is the point of deriving it.

		This is also the check that the derivation is real rather than a
		constant: if the person does not move, the section was never being
		worked out.
		"""
		who = self.covered_only[1]
		before = self._team(self.kamal_user)
		self.assertIn(who, self._names(before["covered"]))
		self.assertNotIn(who, self._names(before["direct"]))

		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", who, "reports_to", self.kamal,
		                    update_modified=False)
		frappe.db.commit()
		try:
			after = self._team(self.kamal_user)
			self.assertIn(who, self._names(after["direct"]),
			              "the derivation did not follow reports_to")
			self.assertNotIn(who, self._names(after["covered"]))
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Employee", who, "reports_to", None,
			                    update_modified=False)
			frappe.db.commit()


class TestNoScopeHelperEverReturnsEverything(_Team):
	def test_a_caller_with_no_employee_id_and_hr_true_matches_nobody(self):
		"""AC-84 / SEC-6, the exact fail-open shape found this week."""
		conds = team_api.covered_conditions("Administrator", None)
		self.assertIn(["name", "in", []], conds,
		              "an HR caller with no employee id was not failed closed")

	def test_the_condition_list_is_never_empty(self):
		for emp in (None, self.kamal):
			with self.subTest(emp=emp):
				self.assertTrue(team_api.covered_conditions(self.kamal_user, emp))

	def test_wave_four_does_not_hand_roll_a_second_filter_builder(self):
		"""AC-84. `hr_api.py:410` grew a hand-rolled copy of
		`home_api._filter_list`; this wave calls the real one."""
		import inspect

		src = inspect.getsource(team_api)
		self.assertIn("_filter_list", src)
		self.assertNotIn("for field, value in", src,
		                 "team_api looks like it re-implements _filter_list")
