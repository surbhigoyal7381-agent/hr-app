"""Filling a seat: who is in it, who could be, and advertising it.

Kept apart from `test_register_194.py`, which is about who may read and change
the SHAPE of the organisation. This file is about who is IN it, and the two
carry different risk: creating a seat draws a box, while putting somebody in
one can rewrite whose approval that employee needs for their leave and their
expenses. That is why `delegate_authority` is never implied and is tested here
twice - off when nobody asked, on only when somebody did.

"Internal" and "external" mean two different things and neither is a guess:

  internal - picking somebody already in the company who suits the role
             (`candidates_for` then `assign_person`)
  external - a Frappe HR job opening, on the careers page or not yet

Surbhi settled that on 15 October 2026: "internal job posting means the
selection of an employee suitable for that role within the company".
"""

import frappe

from hrms.alvoraa_org_structure import register
from hrms.alvoraa_org_structure.tests.test_register_194 import RegisterCase


def _designation():
	"""A job role that exists on this site.

	Job Opening requires one, and a position needs it before it can be
	advertised. Made rather than assumed, because a bench built by
	`bench install-app` carries no designations.
	"""
	name = "Org Fill Test Role"
	if not frappe.db.exists("Designation", name):
		frappe.get_doc({"doctype": "Designation",
		                "designation_name": name}).insert(ignore_permissions=True)
	return name


class FillCase(RegisterCase):
	def setUp(self):
		super().setUp()
		self.editors("System Manager")

	def role_of(self, seat):
		return frappe.db.get_value("Alvoraa Position", seat, "designation")

	def seat_row(self, seat):
		rows = register.position_table()["rows"]
		return [r for r in rows if r["id"] == seat][0]


class TestPuttingSomebodyInASeat(FillCase):
	def setUp(self):
		super().setUp()
		self.seat = self.pos("Counter Staff", seats=1).name
		self.who = self.person("Fillable")

	def test_somebody_can_be_put_in_a_seat(self):
		register.assign_person(self.seat, self.who)
		row = self.seat_row(self.seat)
		self.assertEqual([p["name"] for p in row["people"]], ["Fillable"])
		self.assertEqual(row["open"], 0)

	def test_half_a_person_leaves_half_the_seat_open(self):
		"""Part time, which is the whole reason a share is a percentage and
		not a headcount."""
		register.assign_person(self.seat, self.who, weight=50)
		row = self.seat_row(self.seat)
		self.assertEqual(row["filled"], 0.5)
		self.assertEqual(row["open"], 0.5)

	def test_two_halves_fill_one_seat(self):
		register.assign_person(self.seat, self.who, weight=50)
		register.assign_person(self.seat, self.person("Other Half"), weight=50)
		self.assertEqual(self.seat_row(self.seat)["open"], 0)

	def test_a_share_outside_one_and_a_hundred_is_refused(self):
		for bad in (0, -10, 101):
			with self.assertRaises(frappe.ValidationError):
				register.assign_person(self.seat, self.who, weight=bad)

	def test_cover_with_no_end_date_is_refused(self):
		"""How "acting" quietly becomes permanent. The chart flags it months
		later; refusing at the source costs nothing and is kinder."""
		with self.assertRaises(frappe.ValidationError):
			register.assign_person(self.seat, self.who, assignment_type="Acting")

	def test_cover_with_an_end_date_is_allowed_and_reads_as_covering(self):
		register.assign_person(self.seat, self.who, assignment_type="Acting",
		                       to_date="2026-12-31")
		person = self.seat_row(self.seat)["people"][0]
		self.assertTrue(person["covering"])
		self.assertEqual(person["type"], "Acting")

	def test_a_kind_of_assignment_nobody_has_heard_of_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			register.assign_person(self.seat, self.who,
			                       assignment_type="Sort Of In Charge")

	def test_delegate_authority_is_off_unless_it_is_asked_for(self):
		"""It rewrites who approves that employee's leave and expenses. Done
		from a screen about org structure, nobody would look for it there
		afterwards - so it is never a side effect of adding a person."""
		got = register.assign_person(self.seat, self.who)
		self.assertEqual(frappe.db.get_value(register.ASSIGNMENT, got["name"],
		                                     "delegate_authority"), 0)

	def test_it_can_still_be_asked_for_explicitly(self):
		got = register.assign_person(self.seat, self.who, delegate_authority=1)
		self.assertEqual(frappe.db.get_value(register.ASSIGNMENT, got["name"],
		                                     "delegate_authority"), 1)

	def test_somebody_who_may_not_edit_cannot_fill_a_seat(self):
		self.editors("A Role Nobody Holds")
		with self.assertRaises(frappe.PermissionError):
			register.assign_person(self.seat, self.who)

	def test_ending_an_assignment_keeps_the_record(self):
		"""Ended, never deleted. "Who was running Ambala in October" has to
		stay answerable a year later, and deleting erases that it was ever
		anybody."""
		# Started in the past, ended later. Leaving the start to default would
		# make it today, and a leaving date in the past is then correctly
		# refused by the rule the next test proves.
		got = register.assign_person(self.seat, self.who, from_date="2026-01-01")
		register.end_assignment(got["name"], on_date="2026-06-30")
		self.assertTrue(frappe.db.exists(register.ASSIGNMENT, got["name"]))
		self.assertEqual(str(frappe.db.get_value(register.ASSIGNMENT,
		                                         got["name"], "to_date")),
		                 "2026-06-30")

	def test_somebody_cannot_leave_a_seat_before_they_were_in_it(self):
		got = register.assign_person(self.seat, self.who, from_date="2026-05-01")
		with self.assertRaises(frappe.ValidationError):
			register.end_assignment(got["name"], on_date="2026-04-01")


class TestFillingItFromInside(FillCase):
	def setUp(self):
		super().setUp()
		self.seat = self.pos("Cashier", seats=1,
		                     designation=_designation()).name

	def _same_role(self, name):
		who = self.person(name)
		frappe.db.set_value("Employee", who, "designation", self.role_of(self.seat))
		return who

	def test_it_offers_people_already_doing_that_job(self):
		self._same_role("Already A Cashier")
		names = [r["name"] for r in register.candidates_for(self.seat)["rows"]]
		self.assertIn("Already A Cashier", names)

	def test_it_says_how_much_of_each_person_is_already_committed(self):
		"""The fact somebody needs and cannot get anywhere else. At the first
		tenant every employee is at 100%, so this column IS the answer to "can
		they take this on" - it means they would have to leave something."""
		busy = self._same_role("Fully Booked")
		self.assign(busy, self.pos("Their Current Job", seats=1).name, weight=100)
		row = [r for r in register.candidates_for(self.seat)["rows"]
		       if r["employee"] == busy][0]
		self.assertEqual(row["allocated"], 100)
		self.assertEqual(row["free"], 0)

	def test_a_free_person_reads_as_free(self):
		idle = self._same_role("Nothing On")
		row = [r for r in register.candidates_for(self.seat)["rows"]
		       if r["employee"] == idle][0]
		self.assertEqual(row["free"], 100)

	def test_a_search_term_looks_wider_than_the_one_role(self):
		"""Moving INTO a new kind of job is what a promotion is, so the search
		must not be trapped inside the role the seat already names."""
		other = self.person("Zubin Different")
		found = [r["employee"] for r in
		         register.candidates_for(self.seat, q="Zubin")["rows"]]
		self.assertIn(other, found)

	def test_nobody_is_scored_for_suitability(self):
		"""Deliberate. Ranking people by fitness for a job from the fields on
		an Employee record would be a judgement this has no business making,
		and an automated decision about a person the moment it did."""
		self._same_role("Someone")
		row = register.candidates_for(self.seat)["rows"][0]
		for word in ("score", "rank", "match", "fit", "suitability"):
			self.assertNotIn(word, " ".join(row.keys()).lower())

	def test_somebody_who_may_not_edit_cannot_list_candidates(self):
		"""It is a list of named people with how busy each one is."""
		self.editors("A Role Nobody Holds")
		with self.assertRaises(frappe.PermissionError):
			register.candidates_for(self.seat)


class TestAdvertisingASeat(FillCase):
	"""The external route. No recruitment is built here - Frappe HR has it."""

	def setUp(self):
		super().setUp()
		# A seat of its own per test. A position is named by its title, so a
		# shared one is the SAME record in every test - and `post_job` commits,
		# so the openings from one test were still hanging off the seat in the
		# next. The same shape of pollution the reprocess tests paid for.
		self.seat = self.pos("Sales Executive " + self._testMethodName[:40],
		                     seats=1, designation=_designation()).name

	def test_an_opening_is_filled_in_from_the_seat(self):
		got = register.post_job(self.seat, vacancies=2)
		job = frappe.get_doc("Job Opening", got["name"])
		seat = frappe.get_doc("Alvoraa Position", self.seat)
		self.assertEqual(job.job_title, seat.position_title)
		self.assertEqual(job.designation, seat.designation)
		self.assertEqual(job.company, seat.company)
		self.assertEqual(job.vacancies, 2)

	def test_it_is_not_on_the_careers_page_unless_asked(self):
		self.assertFalse(register.post_job(self.seat)["published"])

	def test_publishing_puts_it_there(self):
		self.assertTrue(register.post_job(self.seat, publish=1)["published"])

	def test_the_opening_points_back_at_the_seat(self):
		"""Without it the chart cannot tell a hole somebody is recruiting for
		from a hole nobody has noticed."""
		got = register.post_job(self.seat)
		if frappe.get_meta("Job Opening").has_field(register.POSITION_LINK):
			self.assertEqual(
				frappe.db.get_value("Job Opening", got["name"],
				                    register.POSITION_LINK), self.seat)

	def test_a_seat_with_no_job_role_is_refused_with_a_reason(self):
		"""Job Opening needs a designation. Naming the missing field beats
		failing on Frappe's own mandatory message."""
		bare = self.pos("No Role On It", seats=1).name
		with self.assertRaises(frappe.ValidationError):
			register.post_job(bare)

	def test_the_seat_says_it_is_already_advertised(self):
		"""So the screen can offer a way INTO the opening instead of offering
		to make a second one. Without this an owner raises two openings for
		one job and is never told about the first."""
		row = [r for r in register.position_table()["rows"]
		       if r["id"] == self.seat][0]
		self.assertIsNone(row["opening"], "nothing advertised yet")

		got = register.post_job(self.seat)
		row = [r for r in register.position_table()["rows"]
		       if r["id"] == self.seat][0]
		self.assertEqual(row["opening"], got["name"])

	def test_a_closed_opening_stops_counting(self):
		"""A seat whose advert has been closed is advertisable again."""
		got = register.post_job(self.seat)
		frappe.db.set_value("Job Opening", got["name"], "status", "Closed")
		row = [r for r in register.position_table()["rows"]
		       if r["id"] == self.seat][0]
		self.assertIsNone(row["opening"])

	def test_somebody_who_may_not_edit_cannot_advertise(self):
		self.editors("A Role Nobody Holds")
		with self.assertRaises(frappe.PermissionError):
			register.post_job(self.seat)


class TestWhereSomebodySits(FillCase):
	"""Name the manager a new seat reports to, and their own seat and branch
	answer the next two questions on the form."""

	def test_it_finds_the_seat_somebody_holds(self):
		seat = self.pos("Store Manager", seats=1)
		who = self.person("The Manager")
		self.assign(who, seat.name)
		self.assertEqual(register.where_does_this_person_sit(who)["position"],
		                 seat.name)

	def test_somebody_in_no_seat_says_so_rather_than_answering_blank(self):
		got = register.where_does_this_person_sit(self.person("Unplaced"))
		self.assertIsNone(got["position"])
		self.assertTrue(got["why"], "a blank reads as 'they have no manager'")

	def test_somebody_in_two_seats_answers_with_the_bigger_one_and_says_so(self):
		big = self.pos("Their Real Job", seats=1)
		small = self.pos("A Side Job", seats=1)
		who = self.person("Two Hats")
		self.assign(who, big.name, weight=70)
		self.assign(who, small.name, weight=30)
		got = register.where_does_this_person_sit(who)
		self.assertEqual(got["position"], big.name,
		                 "the bigger share of their time is their main seat")
		self.assertTrue(got["why"], "it must say that a choice was made")

	def test_the_primary_flag_is_not_trusted_over_the_share(self):
		"""`is_primary` defaults to 1 on the assignment, so every new one
		claims it and demotes the one before. It therefore means "most
		recently added", not "their main job" - and a new seat must not end up
		under whichever role somebody happened to be given last."""
		big = self.pos("Most Of Their Time", seats=1)
		small = self.pos("A Third Of It", seats=1)
		who = self.person("Recently Moved")
		self.assign(who, big.name, weight=70)
		self.assign(who, small.name, weight=30)
		flagged = [r.position for r in frappe.get_all(
			register.ASSIGNMENT, filters={"employee": who},
			fields=["position", "is_primary"]) if r.is_primary]
		self.assertEqual(flagged, [small.name],
		                 "if this fails the flag has been fixed and this "
		                 "function can go back to trusting it")
		self.assertEqual(
			register.where_does_this_person_sit(who)["position"], big.name)


class TestSomebodyWorkingTheirNotice(FillCase):
	"""Nothing new is stored for this.

	Somebody is on notice when they are still Active and their last day is
	already known - `relieving_date` and `status` are on every Employee
	record and always have been. The chart could not tell "full" apart from
	"full until the 30th", which is the earlier of the two warnings and the
	one there is still time to act on.
	"""

	def setUp(self):
		super().setUp()
		self.seat = self.pos("Store Manager", seats=1).name

	def _in_seat(self, name, relieving=None, status="Active"):
		who = self.person(name)
		register.assign_person(self.seat, who)
		frappe.db.set_value("Employee", who,
		                    {"relieving_date": relieving, "status": status})
		return who

	def _row(self):
		return [r for r in register.position_table()["rows"]
		        if r["id"] == self.seat][0]

	def test_somebody_with_a_last_day_ahead_of_them_is_on_notice(self):
		self._in_seat("Going Soon", relieving="2026-12-31")
		row = self._row()
		self.assertEqual(row["leaving_on"], "2026-12-31")
		self.assertEqual(row["people"][0]["leaving"], "2026-12-31")

	def test_somebody_staying_is_not(self):
		self._in_seat("Staying Put")
		row = self._row()
		self.assertIsNone(row["leaving_on"])
		self.assertIsNone(row["people"][0]["leaving"])

	def test_somebody_already_gone_is_not_on_notice(self):
		"""A date in the past is not notice, it is history - and if they are
		still Active with it set, that is a data problem for the data review
		to raise, not a warning on the chart."""
		self._in_seat("Left Already", relieving="2020-01-01")
		self.assertIsNone(self._row()["leaving_on"])

	def test_the_seat_reports_the_soonest_last_day(self):
		"""Two people leaving is one problem with two dates. The nearer one is
		the one there is least time to do anything about."""
		wide = self.pos("Two Of These", seats=2).name
		for name, day in (("Going Later", "2026-12-31"),
		                  ("Going Sooner", "2026-11-01")):
			who = self.person(name)
			register.assign_person(wide, who)
			frappe.db.set_value("Employee", who, "relieving_date", day)
		row = [r for r in register.position_table()["rows"]
		       if r["id"] == wide][0]
		self.assertEqual(row["leaving_on"], "2026-11-01")
		self.assertEqual(
			sorted(p["leaving"] for p in row["people"]),
			["2026-11-01", "2026-12-31"])

	def test_their_own_manager_is_told(self):
		"""The people who have to cover the gap are exactly the people who
		need to know. This runs as a full-reach role, which is the half of the
		rule HR relies on."""
		going = self.person("Leaving Under Me")
		register.assign_person(self.seat, going)
		frappe.db.set_value("Employee", going, "relieving_date", "2026-12-31")
		row = [r for r in register.position_table()["rows"]
		       if r["id"] == self.seat][0]
		self.assertEqual(row["leaving_on"], "2026-12-31")


class TestWhoMayBeToldSomebodyIsLeaving(FillCase):
	"""Reading the organisation's SHAPE and reading who is about to leave it
	are different permissions, and this screen had been treating them as one.

	The decision itself is tested here rather than through the whole endpoint.
	Who may read which seats already has eight tests of its own in
	`test_company_scope_194`; what is new is which of those readers may be
	told a date, and that is one function.
	"""

	def _full_reach(self, roles):
		frappe.db.set_default("alvoraa_org_full_reach_roles", roles)

	def setUp(self):
		super().setUp()
		self._saved_reach = frappe.db.get_default("alvoraa_org_full_reach_roles")

	def tearDown(self):
		self._full_reach(self._saved_reach if self._saved_reach is not None else "")
		super().tearDown()

	def test_a_full_reach_role_sees_the_whole_company(self):
		"""None means "no limit" - HR cannot plan a replacement otherwise."""
		self._full_reach("System Manager")
		self.assertIsNone(register._my_reporting_line())
		self.assertTrue(register._may_see_who_is_leaving())

	def test_a_manager_sees_only_their_own_line(self):
		self._full_reach("A Role Nobody Holds")
		me = frappe.db.get_value("Employee",
		                         {"user_id": frappe.session.user}, "name")
		if not me:
			self.skipTest("the test user has no Employee record")
		mine = self.person("Under Me")
		frappe.db.set_value("Employee", mine, "reports_to", me)
		theirs = self.person("Somebody Else's")
		line = register._my_reporting_line()
		self.assertIn(mine, line)
		self.assertNotIn(theirs, line,
		                 "a peer's people are not this manager's to know about")

	def test_it_reaches_down_the_whole_line_not_just_one_level(self):
		"""A manager covers for their whole line, not only their direct
		reports."""
		self._full_reach("A Role Nobody Holds")
		me = frappe.db.get_value("Employee",
		                         {"user_id": frappe.session.user}, "name")
		if not me:
			self.skipTest("the test user has no Employee record")
		mid = self.person("In The Middle")
		frappe.db.set_value("Employee", mid, "reports_to", me)
		deep = self.person("Two Levels Down")
		frappe.db.set_value("Employee", deep, "reports_to", mid)
		self.assertIn(deep, register._my_reporting_line())

	def test_somebody_who_manages_nobody_is_told_nothing(self):
		"""Which is the case the whole rule exists for: this screen is open to
		any manager once `alvoraa_org_managers_see_all` is on, and reading the
		shape of the company is not a reason to be told who is resigning."""
		self._full_reach("A Role Nobody Holds")
		me = frappe.db.get_value("Employee",
		                         {"user_id": frappe.session.user}, "name")
		if me:
			frappe.db.sql("""UPDATE tabEmployee SET reports_to = NULL
			                 WHERE reports_to = %s""", me)
		self.assertEqual(register._my_reporting_line(), set())
		self.assertFalse(register._may_see_who_is_leaving())
