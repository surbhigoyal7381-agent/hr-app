"""Slice 042, Wave 2: Home sends what the screen draws, and nothing else.

The payload is the control, not the screen. Every check here reads
`get_home`'s answer rather than a rendered page, because Wave 1's biggest
security finding was a start-up call whose EXTRA fields nobody could see.

The three that are easiest to write so they prove nothing, and what is done
about each:

* **AC-5** asserts the key set, per persona, and names the six fields that must
  never appear. A test that only looked for "does my name come back" would pass
  with a date of birth beside it.
* **AC-29** asserts on the payload. A card that draws no numbers while the
  payload carries them is a leak with a tidy screen in front of it.
* **AC-62** calls the REAL entitlement gate. It changes the site's own
  `features` list, which is what a tenant without payroll actually has, and
  patches nothing. A patched gate turns every entitlement test green while
  proving nothing.

Synthetic people only, all tagged S042, in this slice's own company.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import attendance_correction, home_api
from alvoraa_portal.frame_api import ME_FIELDS
from alvoraa_portal.tests import fixtures_042 as fx
from alvoraa_portal.tests.test_inbox_parts_042 import SCOPED_TABLES, _Recorder

# The six fields Wave 1 found in a start-up payload and took out. None of them
# may come back (SEC-12, 042 AC-5).
NEVER = ("date_of_birth", "gender", "cell_number", "date_of_joining",
         "reports_to", "branch")


class _HomeFixture(FrappeTestCase):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		fx.ensure_company()
		fx.ensure_branches()
		cls.rahul_login = fx.user("rahul", ("Employee",))
		cls.sandeep_login = fx.user("sandeep", ("Employee",))
		cls.priya_login = fx.user("priya", ("HR User", "Employee"))
		cls.kamal_login = fx.user("kamal", ("HR Manager", "Employee"))
		cls.asha_login = fx.user("asha", ("System Manager",))
		cls.lone_login = fx.user("lone", ("Employee",))

		cls.sandeep = fx.employee("Sandeep", branch=fx.STORE_A, login=cls.sandeep_login,
		                          designation="S042 Floor Manager")
		cls.rahul = fx.employee("Rahul", branch=fx.STORE_A, reports_to=cls.sandeep,
		                        login=cls.rahul_login)
		cls.priya = fx.employee("Priya", branch=fx.STORE_A, login=cls.priya_login)
		cls.kamal = fx.employee("Kamal", branch=None, login=cls.kamal_login)
		cls.in_b = fx.employee("InStoreB", branch=fx.STORE_B, reports_to=cls.kamal)
		cls.peers = [fx.employee("Peer%d" % i, branch=fx.STORE_A, reports_to=cls.sandeep)
		             for i in range(1, 5)]
		# Somebody with NO manager at all - AC-55 says they get no peer card.
		cls.lone = fx.employee("Lone", branch=fx.STORE_A, login=cls.lone_login)
		everyone = [cls.sandeep, cls.rahul, cls.priya, cls.kamal, cls.in_b,
		            cls.lone] + cls.peers
		fx.holiday_list(everyone)
		attendance_correction.after_migrate()
		frappe.db.commit()

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def _as(self, login):
		frappe.set_user(login)
		frappe.clear_cache(user=login)

	def _home(self, login):
		self._as(login)
		try:
			return home_api.get_home()
		finally:
			frappe.set_user("Administrator")


# ── AC-5 and AC-38: the payload's shape ──────────────────────────────────────


class TestThePayloadIsTheControl(_HomeFixture):

	def _personas(self):
		return (self.rahul_login, self.sandeep_login, self.priya_login,
		        self.kamal_login, self.asha_login)

	def test_the_key_set_is_exactly_home_keys_for_every_persona(self):
		for login in self._personas():
			payload = self._home(login)
			self.assertEqual(sorted(payload.keys()), sorted(home_api.HOME_KEYS),
			                 "%s got a different key set" % login)

	def test_the_me_block_is_exactly_me_fields(self):
		payload = self._home(self.rahul_login)
		self.assertIsNotNone(payload["me"], "the fixture gave Rahul no record, so "
		                                    "this test proved nothing")
		self.assertEqual(sorted(payload["me"].keys()), sorted(ME_FIELDS))

	def test_no_personal_field_wave_one_removed_comes_back(self):
		for login in self._personas():
			payload = self._home(login)
			blob = frappe.as_json(payload)
			for field in NEVER:
				self.assertNotIn(
					'"%s"' % field, blob,
					"%s reached Home's payload for %s" % (field, login))

	def test_get_home_carries_no_counts(self):
		"""042 AC-38, DevOps OPS-W2-6. One source for the badge's number."""
		for login in self._personas():
			payload = self._home(login)
			self.assertNotIn("counts", payload)
			self.assertNotIn("total", payload)

	def test_no_card_quietly_failed_on_a_healthy_fixture(self):
		"""The guard on the guard.

		`_card` turns a broken card into `{"error": True}` on purpose, so the
		page survives. That is also a very good way for a real bug to ship
		looking like an empty card. On a fixture where everything should work,
		nothing may be in the error state - and the first run of this file
		caught two wrong field names exactly this way.
		"""
		for login in self._personas():
			payload = self._home(login)
			for key, value in payload.items():
				if isinstance(value, dict) and value.get("error"):
					self.fail("%s: the %r card failed for %s - look in Error Log"
					          % (login, key, login))

	def test_guest_is_refused(self):
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				home_api.get_home()
		finally:
			frappe.set_user("Administrator")


# ── AC-37: a caller with no Employee record ──────────────────────────────────


class TestACallerWithNoEmployeeRecord(_HomeFixture):

	def test_asha_gets_a_working_page_and_no_scoped_query_runs(self):
		self._as(self.asha_login)
		home_api.get_home()                       # warm any per-site caches
		with _Recorder() as rec:
			payload = home_api.get_home()
		frappe.set_user("Administrator")
		touched = rec.touched(SCOPED_TABLES)
		self.assertIsNone(payload["me"])
		self.assertEqual(payload["needs"], [])
		self.assertEqual(payload["leave"], [])
		self.assertEqual(payload["team_today"]["basis"], "none")
		self.assertEqual(
			touched, [],
			"a caller with no Employee record made these scoped queries: %s"
			% (touched,))
		# The recorder works: a real employee DOES touch them, so the assertion
		# above could have failed.
		self._as(self.rahul_login)
		with _Recorder() as rec2:
			home_api.get_home()
		frappe.set_user("Administrator")
		self.assertTrue(rec2.touched(SCOPED_TABLES))


# ── AC-4: the hero ───────────────────────────────────────────────────────────


class TestTheCheckInHero(_HomeFixture):

	SHIFT = "S042 Morning"

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("Shift Type", cls.SHIFT):
			frappe.get_doc({"doctype": "Shift Type", "name": cls.SHIFT,
			                "start_time": "09:30:00", "end_time": "18:30:00"}).insert(
				ignore_permissions=True)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", self.rahul, "default_shift", None,
		                    update_modified=False)
		frappe.db.commit()
		super().tearDown()

	def test_with_no_shift_at_all_there_is_no_hero(self):
		"""009 design decision 6: no hero, not an empty hero."""
		payload = self._home(self.kamal_login)
		self.assertIsNone(payload["today"]["shift"])

	def test_the_default_shift_is_used_when_there_is_no_assignment(self):
		frappe.db.set_value("Employee", self.rahul, "default_shift", self.SHIFT,
		                    update_modified=False)
		frappe.db.commit()
		payload = self._home(self.rahul_login)
		shift = payload["today"]["shift"]
		self.assertIsNotNone(shift, "the default shift was not picked up")
		self.assertEqual(shift["name"], self.SHIFT)
		self.assertTrue(shift["start"].startswith("9:30") or
		                shift["start"].startswith("09:30"),
		                "got %r" % shift["start"])

	def test_a_check_in_today_is_reported_with_the_sites_clock(self):
		doc = frappe.get_doc({"doctype": "Employee Checkin", "employee": self.rahul,
		                      "log_type": "IN",
		                      "time": nowdate() + " 09:24:00"})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		frappe.db.commit()
		try:
			payload = self._home(self.rahul_login)
			checkin = payload["today"]["checkin"]
			self.assertIsNotNone(checkin)
			self.assertEqual(checkin["type"], "IN")
			self.assertIn("09:24", checkin["time"])
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("Employee Checkin", doc.name, force=1,
			                  ignore_permissions=True)
			frappe.db.commit()


# ── The attendance-gap rule (section 11) ─────────────────────────────────────


class TestTheGapRule(_HomeFixture):

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Attendance", {"employee": self.rahul})
		frappe.db.delete(attendance_correction.REQUEST, {"explanation": "S042 gap"})
		frappe.db.commit()
		super().tearDown()

	def _absent(self, day):
		doc = frappe.get_doc({"doctype": "Attendance", "employee": self.rahul,
		                      "attendance_date": day, "status": "Absent",
		                      "company": fx.COMPANY})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		doc.submit()
		frappe.db.commit()
		return doc.name

	def _gaps(self, login=None):
		payload = self._home(login or self.rahul_login)
		for item in payload["needs"]:
			if item["kind"] == "attendance_gap":
				return item
		return None

	def test_an_auto_marked_absent_day_is_a_gap_and_the_number_equals_the_days(self):
		"""042 AC-50 and AC-22 together: the number IS the list."""
		self._absent(add_days(nowdate(), -3))
		self._absent(add_days(nowdate(), -4))
		item = self._gaps()
		self.assertIsNotNone(item, "no gap was found, so this test proved nothing")
		detail = item["detail"]
		self.assertGreaterEqual(detail["total"], 2)
		# Newest first, so the two days just made are at the top of the list and
		# survive the cap. Oldest first put the 50 days FURTHEST from today on
		# the screen and hid the ones a person came to fix - this assertion is
		# what found that.
		self.assertIn(str(add_days(nowdate(), -3)), detail["days"])
		self.assertIn(str(add_days(nowdate(), -4)), detail["days"])
		# The number IS the list - and where the list is capped the payload says
		# so rather than quietly showing fewer (042 AC-22 with section 6.1's
		# rule 2). The first run of this test caught exactly that: 54 gaps and
		# 50 rows, which is right, with an assertion that was wrong.
		if detail["capped"]:
			self.assertEqual(len(detail["days"]), home_api.LIST_CAP)
			self.assertGreater(detail["total"], len(detail["days"]))
		else:
			self.assertEqual(detail["total"], len(detail["days"]))

	def test_a_day_covered_by_a_waiting_correction_is_not_a_gap(self):
		day = add_days(nowdate(), -5)
		self._absent(day)
		before = self._gaps()
		self.assertIn(str(day), before["detail"]["days"],
		              "the day was not a gap to begin with, so the next "
		              "assertion could not have failed")
		doc = frappe.get_doc({
			"doctype": attendance_correction.REQUEST, "employee": self.rahul,
			"from_date": day, "to_date": day, "reason": "On Duty",
			"explanation": "S042 gap"})
		doc.insert(ignore_permissions=True)
		frappe.db.commit()
		after = self._gaps()
		days = after["detail"]["days"] if after else []
		self.assertNotIn(str(day), days)

	def test_a_day_before_joining_is_never_a_gap(self):
		"""042 AC-45. The window starts at date_of_joining."""
		joined = add_days(nowdate(), -6)
		frappe.db.set_value("Employee", self.rahul, "date_of_joining", joined,
		                    update_modified=False)
		frappe.db.commit()
		try:
			item = self._gaps()
			days = item["detail"]["days"] if item else []
			for day in days:
				self.assertGreaterEqual(day, str(joined),
				                        "a day before joining was called a gap")
			self.assertTrue(days, "no gap at all, so this proved nothing")
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Employee", self.rahul, "date_of_joining",
			                    "2024-01-01", update_modified=False)
			frappe.db.commit()

	def test_today_and_the_future_are_never_gaps(self):
		item = self._gaps()
		days = item["detail"]["days"] if item else []
		self.assertNotIn(str(nowdate()), days)
		self.assertNotIn(str(add_days(nowdate(), 1)), days)


# ── AC-29 and AC-30: the team card ───────────────────────────────────────────


class TestTheTeamCardIsCountsOnly(_HomeFixture):

	def test_no_name_no_photo_no_reason_reaches_the_payload(self):
		payload = self._home(self.sandeep_login)
		card = payload["team_today"]
		self.assertEqual(sorted(card.keys()), sorted(home_api.TEAM_TODAY_KEYS))
		blob = frappe.as_json(card)
		self.assertNotIn(fx.TAG, blob, "a colleague's name reached the team card")
		for word in ("Leave", "Absent", "Sick", "reason", "image"):
			self.assertNotIn(word, blob)

	def test_a_group_below_five_carries_no_numbers_at_all(self):
		"""042 AC-29 (b). In a team of four, "1 away" names the person."""
		# Sandeep has four reports plus Rahul = five. Move one away so the group
		# drops to four.
		moved = self.peers[0]
		frappe.db.set_value("Employee", moved, "reports_to", self.kamal,
		                    update_modified=False)
		frappe.db.commit()
		try:
			payload = self._home(self.sandeep_login)
			card = payload["team_today"]
			self.assertTrue(card["suppressed"])
			self.assertIsNone(card["in"])
			self.assertIsNone(card["away"])
			self.assertIsNone(card["due"])
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Employee", moved, "reports_to", self.sandeep,
			                    update_modified=False)
			frappe.db.commit()

	def test_complementary_suppression_hides_the_next_smallest_too(self):
		"""042 AC-29 (c), on the numbers themselves.

		Six people, five in and one away. Publishing "in 5" and "due 0" beside a
		group of six recovers "away 1" by subtraction, so when `away` is
		suppressed the next smallest must go with it.
		"""
		counts = {"in": 5, "away": 1, "due": 0}
		out = home_api._suppress(counts, 6)
		self.assertTrue(out["suppressed"])
		self.assertIsNone(out["away"], "the small category was published")
		hidden = [k for k in ("in", "away", "due") if out[k] is None]
		self.assertGreaterEqual(
			len(hidden), 2,
			"only one category was suppressed, so the total and the remaining "
			"numbers recover it")

	def test_the_suppression_rule_written_out_as_a_table(self):
		"""Every case the rule has to get right, in one place.

		The second row is why the rule changed. "Hide one more to be safe" meant
		a nineteen-person team - Sandeep's, the spec's own manager persona -
		published no numbers at all, which is a card nobody reads. Two already
		hidden of three means one published, and one published pins neither, so
		the complement is added only when exactly ONE is hidden.
		"""
		cases = (
			# counts, group, what must be published
			({"in": 5, "away": 1, "due": 0}, 6, {"in"}),
			({"in": 15, "away": 2, "due": 2}, 19, {"in"}),
			({"in": 3, "away": 1, "due": 0}, 4, set()),
			({"in": 12, "away": 5, "due": 3}, 20, {"in"}),
			({"in": 10, "away": 0, "due": 0}, 10, {"in", "away", "due"}),
		)
		for counts, group, publishable in cases:
			out = home_api._suppress(dict(counts), group)
			shown = {k for k in ("in", "away", "due") if out[k] is not None}
			self.assertEqual(
				shown, publishable,
				"group %d with %r published %r, wanted %r"
				% (group, counts, sorted(shown), sorted(publishable)))
			# Where anything is hidden, at most ONE number is published - two of
			# three plus a total the reader can guess pins the third.
			if shown != {"in", "away", "due"}:
				self.assertLessEqual(len(shown), 1)

	def test_a_person_with_no_manager_gets_no_peer_card(self):
		"""042 AC-55 and D-3: no department fallback, ever."""
		payload = self._home(self.lone_login)
		self.assertEqual(payload["team_today"]["basis"], "none")
		self.assertIsNone(payload["team_today"]["in"])


# ── AC-61 / D-8: the joiners card is not built ───────────────────────────────


class TestCelebrations(_HomeFixture):

	def test_no_joiners_list_is_built_at_all(self):
		"""D-8 is unanswered, so the fail-closed default ships: own anniversary
		only. A test, not a comment, because an empty list is the kind of thing
		somebody fills in later without asking."""
		for login in (self.rahul_login, self.sandeep_login, self.kamal_login):
			payload = self._home(login)
			self.assertEqual(payload["celebrations"]["joiners"], [])

	def test_an_anniversary_is_the_callers_own_and_nobody_elses(self):
		joined = add_days(nowdate(), -365 * 3)
		frappe.db.set_value("Employee", self.rahul, "date_of_joining", joined,
		                    update_modified=False)
		frappe.db.commit()
		try:
			payload = self._home(self.rahul_login)
			years = payload["celebrations"]["own_anniversary_years"]
			# Only true when today is the anniversary day; either way the
			# payload names nobody else.
			blob = frappe.as_json(payload["celebrations"])
			self.assertNotIn(fx.TAG, blob)
			self.assertIn(years, (None, 3))
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Employee", self.rahul, "date_of_joining",
			                    "2024-01-01", update_modified=False)
			frappe.db.commit()


# ── AC-62: the entitlement gate is the real one ──────────────────────────────


class TestTheRealEntitlementGate(_HomeFixture):

	def test_a_tenant_without_payroll_gets_no_payslip_row(self):
		"""042 AC-62. The site's own `features` list is changed - the gate is
		NOT patched. `subscription.has_feature` reads `frappe.conf`, which is
		exactly what a tenant without payroll has.
		"""
		from alvoraa_portal.subscription import REQUIRED, has_feature

		original = frappe.local.conf.get("features")
		try:
			frappe.local.conf["features"] = [f for f in REQUIRED]
			frappe.clear_cache()
			self.assertFalse(has_feature("payroll"),
			                 "the real gate still says payroll is bought, so "
			                 "this test could not have failed")
			payload = self._home(self.rahul_login)
			kinds = [item["kind"] for item in payload["needs"]]
			self.assertNotIn("payslip", kinds)
		finally:
			frappe.set_user("Administrator")
			if original is None:
				frappe.local.conf.pop("features", None)
			else:
				frappe.local.conf["features"] = original
			frappe.clear_cache()


# ── AC-32: one card failing is one card failing ──────────────────────────────


class TestOneCardFailingIsOneCard(_HomeFixture):

	def test_the_rest_of_home_still_renders_when_a_card_throws(self):
		real = home_api._team_today

		def boom(*args, **kwargs):
			raise RuntimeError("S042 deliberate failure")

		home_api._team_today = boom
		try:
			payload = self._home(self.rahul_login)
		finally:
			home_api._team_today = real
		self.assertEqual(payload["team_today"], {"error": True})
		self.assertIsNotNone(payload["me"], "the whole page went down with one card")
		self.assertEqual(sorted(payload.keys()), sorted(home_api.HOME_KEYS))


# ── 042 review F3: the team goal summary is gone ─────────────────────────────


def _names_used(source):
	"""Every identifier the PARSER sees in a module: imports, calls, attributes.

	Deliberately not a text search. A text search over this module would match
	the paragraph explaining why the thing was deleted, which is how the first
	version of the test below failed on its own documentation. Prose cannot
	call a function; only code can.
	"""
	import ast

	names = set()
	for node in ast.walk(ast.parse(source)):
		if isinstance(node, ast.ImportFrom):
			names.update(alias.name for alias in node.names)
		elif isinstance(node, ast.Import):
			names.update(alias.name for alias in node.names)
		elif isinstance(node, ast.Name):
			names.add(node.id)
		elif isinstance(node, ast.Attribute):
			names.add(node.attr)
	return names


class TestHomeCarriesNoTeamGoalSummary(_HomeFixture):
	"""The review's F3.

	`_goals` used to return a `team` block holding `{"people": N, "goals": M}`
	where `people` counted EVERYBODY the caller may see and `goals` counted the
	goals of the first fifty of them. On the 981-person fixture, company-wide HR
	got "981 people, N goals" with N taken from 50 people - the same "a heading
	said 4 over a list of nine" shape this programme has paid for four times.

	It also read every permitted employee id into Python to do it, which is the
	exact thing this branch wrote into `nfr-budget.md` as forbidden: *"A cap is
	the wrong answer - it makes the number wrong instead of slow."*

	And nothing drew it. `next-home.js` reads `g.mine` only.

	So it was deleted. These tests fail on the version that still has it.
	"""

	def test_the_goals_card_has_no_team_block_at_all(self):
		for login in (self.rahul_login, self.sandeep_login, self.priya_login,
		              self.kamal_login):
			payload = self._home(login)
			goals = payload["goals"]
			self.assertIsInstance(goals, dict, "%s got no goals card" % login)
			self.assertEqual(
				sorted(goals.keys()), ["mine"],
				"%s still gets a team goal summary: %s" % (login, goals))

	def test_no_wrong_number_can_be_read_off_the_payload(self):
		"""The number that was wrong is not merely hidden - it is not computed."""
		blob = frappe.as_json(self._home(self.priya_login))
		self.assertNotIn('"people"', blob)

	def test_home_api_no_longer_reads_a_list_of_employee_ids(self):
		"""The structural half, so the deletion cannot quietly come back.

		`permitted_employees()` returns a SET OF IDS. Home's remaining scoped
		queries all go through `permitted_employee_filters()`, which pushes the
		same rule into the query instead. The difference is the whole point: one
		is flat in headcount, the other ships 981 ids to the database as an
		`IN (...)`.

		This asserts on the source, not on a call, so it holds even where a
		fixture is too small for the difference to show.
		"""
		import inspect

		names = _names_used(inspect.getsource(home_api))
		self.assertTrue(
			names, "the walk read no names at all, so it proved nothing")
		self.assertNotIn(
			"permitted_employees", names,
			"home_api reads a list of employee ids again. Use "
			"permitted_employee_filters() and push the rule into the query.")
		# And the thing it IS allowed to use is still there, so this is not
		# passing because Home stopped scoping anything.
		self.assertIn("permitted_employee_filters", names)
		self.assertFalse(
			hasattr(home_api, "_hr_scope"),
			"_hr_scope is back. Its only caller was the deleted team summary.")

	def test_this_check_can_actually_fail(self):
		"""The positive control for the source walk above.

		A source assertion that would pass over an empty string proves nothing,
		and the first version of this walk DID pass wrongly: it matched raw text,
		so the docstring explaining the deletion set it off. It reads names the
		parser sees now, and this proves that reading still bites.
		"""
		bad = _names_used(
			"def f():\n"
			'    """A docstring naming permitted_employee_filters only."""\n'
			"    from hrms.alvoraa_hr_core.access import permitted_employees\n"
			"    return sorted(permitted_employees())\n")
		self.assertIn("permitted_employees", bad,
		              "the walk cannot see the thing it forbids")

		good = _names_used(
			"def f():\n"
			'    """Mentions permitted_employees in prose, and does not call it."""\n'
			"    from hrms.alvoraa_hr_core.access import permitted_employee_filters\n"
			"    return permitted_employee_filters()\n")
		self.assertNotIn("permitted_employees", good,
		                 "the walk fires on prose, so it would be turned off")
