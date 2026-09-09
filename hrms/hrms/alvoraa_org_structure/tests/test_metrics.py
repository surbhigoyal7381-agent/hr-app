"""What is wrong with the shape of this organisation.

Vacancies, people carrying more than one job, and the other things that mean a
seat needs looking at. Every number here is worked out on read, so these tests
mostly prove that it counts what a person would count by hand.

The one thing to be careful about: a flag that fires on a healthy organisation
is worse than no flag, because people stop reading a dashboard that cries wolf.
So most of these tests check the SILENCE as well as the noise.
"""

import frappe
from frappe.utils import add_days, nowdate

from hrms.alvoraa_org_structure import api, metrics, settings
from hrms.alvoraa_org_structure.tests.test_org_structure import OrgCase


class MetricsCase(OrgCase):
	def setUp(self):
		super().setUp()
		self._saved = {k: frappe.db.get_default(k) for k in settings.DEFAULTS}
		self._user = frappe.session.user
		frappe.local._alvoraa_leads = {}

	def tearDown(self):
		frappe.set_user(self._user)
		for k, v in self._saved.items():
			frappe.db.set_default(k, v if v is not None else "")
		frappe.local._alvoraa_leads = {}
		super().tearDown()

	def kinds(self, health):
		return {g["kind"]: g for g in health["by_kind"]}


class TestTheHeadlineNumbers(MetricsCase):
	def test_an_empty_seat_is_counted_as_vacant(self):
		self.pos("Shift Supervisor", seats=1)
		h = metrics.org_health()
		self.assertEqual(h["headline"]["seats_vacant"], 1.0)
		self.assertEqual(self.kinds(h)["vacant"]["count"], 1)

	def test_filling_it_makes_the_number_go_away(self):
		p = self.pos("Shift Supervisor", seats=1)
		self.assign(self.person("Asha"), p.name, weight=100)
		h = metrics.org_health()
		self.assertEqual(h["headline"]["seats_vacant"], 0.0)
		self.assertNotIn("vacant", self.kinds(h))

	def test_half_a_seat_open_is_not_worth_flagging(self):
		"""Somebody at 60% of a one-seat role leaves 0.4 open. Flagging that
		produces a list of rounding errors nobody reads."""
		p = self.pos("Analyst", seats=1)
		self.assign(self.person("Bo"), p.name, weight=60)
		self.assertNotIn("vacant", self.kinds(metrics.org_health()))

	def test_two_of_three_seats_filled_leaves_one(self):
		p = self.pos("Picker", seats=3)
		self.assign(self.person("Cai"), p.name, weight=100)
		self.assign(self.person("Dev"), p.name, weight=100)
		h = metrics.org_health()
		self.assertEqual(h["headline"]["seats_vacant"], 1.0)

	def test_a_key_seat_is_its_own_number(self):
		"""A missing chief financial officer should not sit in the same list as
		a spare picker."""
		self.pos("Chief Financial Officer", seats=1, is_key_position=1)
		self.pos("Picker", seats=1)
		k = self.kinds(metrics.org_health())
		self.assertEqual(k["key_vacant"]["count"], 1)
		self.assertEqual(k["key_vacant"]["severity"], "high")
		self.assertEqual(k["vacant"]["count"], 1)

	def test_the_worst_group_is_listed_first(self):
		"""A dashboard sorted by name makes the one urgent thing as easy to
		miss as if it were not there."""
		self.pos("Picker", seats=1)
		self.pos("Chief Financial Officer", seats=1, is_key_position=1)
		self.assertEqual(metrics.org_health()["by_kind"][0]["kind"], "key_vacant")

	def test_a_closed_seat_is_not_a_vacancy(self):
		"""Closed means the company decided it no longer needs the role."""
		self.pos("Fax Operator", seats=1, status="Closed")
		self.assertEqual(metrics.org_health()["headline"]["seats_vacant"], 0.0)


class TestCoverDoesNotHideTheHole(MetricsCase):
	def test_a_covered_seat_still_counts_as_vacant(self):
		"""The point of the setting. Once somebody is standing in, urgency drops
		and the requisition quietly stalls - which is how three months becomes
		a year."""
		p = self.pos("Store Manager", seats=1)
		self.assign(self.person("Eve"), p.name, weight=100,
		            assignment_type="Acting", to_date=add_days(nowdate(), 30))
		h = metrics.org_health()
		k = self.kinds(h)
		self.assertEqual(k["vacant"]["count"], 1)
		self.assertTrue(k["vacant"]["items"][0]["covered"])
		# and the headline agrees with the list underneath it
		self.assertEqual(h["headline"]["seats_vacant"], 1.0)

	def test_cover_that_has_run_too_long_is_flagged(self):
		frappe.db.set_default("alvoraa_cover_max_days", 30)
		p = self.pos("Store Manager", seats=1)
		self.assign(self.person("Fay"), p.name, weight=100,
		            assignment_type="Acting",
		            from_date=add_days(nowdate(), -100),
		            to_date=add_days(nowdate(), 30))
		k = self.kinds(metrics.org_health())
		self.assertEqual(k["long_cover"]["count"], 1)
		self.assertEqual(k["long_cover"]["items"][0]["over_by"], 70)

	def test_cover_inside_the_limit_is_left_alone(self):
		frappe.db.set_default("alvoraa_cover_max_days", 90)
		p = self.pos("Store Manager", seats=1)
		self.assign(self.person("Gil"), p.name, weight=100,
		            assignment_type="Acting",
		            from_date=add_days(nowdate(), -10),
		            to_date=add_days(nowdate(), 30))
		self.assertNotIn("long_cover", self.kinds(metrics.org_health()))


class TestPeopleCarryingTooMuch(MetricsCase):
	def test_somebody_over_the_cap_is_counted(self):
		frappe.db.set_default("alvoraa_cover_max_load", 130)
		a = self.pos("Buyer", seats=1)
		b = self.pos("Planner", seats=1)
		who = self.person("Hana")
		self.assign(who, a.name, weight=100)
		self.assign(who, b.name, weight=50, assignment_type="Acting",
		            to_date=add_days(nowdate(), 30), load_exception_reason="Peak")
		h = metrics.org_health()
		self.assertEqual(h["headline"]["people_over_capacity"], 1)
		item = self.kinds(h)["over_capacity"]["items"][0]
		self.assertEqual(item["load"], 150)
		self.assertEqual(len(item["positions"]), 2)

	def test_exactly_at_the_cap_is_not_over_it(self):
		"""The cap is what the organisation decided is acceptable. Flagging the
		number they chose is noise."""
		frappe.db.set_default("alvoraa_cover_max_load", 130)
		a = self.pos("Buyer", seats=1)
		b = self.pos("Planner", seats=1)
		who = self.person("Ines")
		self.assign(who, a.name, weight=100)
		self.assign(who, b.name, weight=30, assignment_type="Acting",
		            to_date=add_days(nowdate(), 30))
		self.assertEqual(metrics.org_health()["headline"]["people_over_capacity"], 0)

	def test_one_job_is_never_over_capacity(self):
		p = self.pos("Buyer", seats=1)
		self.assign(self.person("Jai"), p.name, weight=100)
		self.assertEqual(metrics.org_health()["headline"]["people_over_capacity"], 0)


class TestTheOtherRedFlags(MetricsCase):
	def test_too_many_direct_reports(self):
		frappe.db.set_default("alvoraa_org_span_wide", 4)
		top = self.pos("Head of Retail", seats=1)
		self.assign(self.person("Kim"), top.name, weight=100)
		for i in range(4):
			seat = self.pos("Store %d" % i, parent=top.name, seats=1)
			self.assign(self.person("Store%dPerson" % i), seat.name, weight=100)
		k = self.kinds(metrics.org_health())
		self.assertEqual(k["span_wide"]["count"], 1)
		self.assertEqual(k["span_wide"]["items"][0]["reports"], 4)

	def test_a_normal_team_is_not_flagged(self):
		frappe.db.set_default("alvoraa_org_span_wide", 9)
		frappe.db.set_default("alvoraa_org_span_narrow", 0)
		top = self.pos("Head of Retail", seats=1)
		self.assign(self.person("Lee"), top.name, weight=100)
		for i in range(3):
			seat = self.pos("Store %d" % i, parent=top.name, seats=1)
			self.assign(self.person("S%dP" % i), seat.name, weight=100)
		k = self.kinds(metrics.org_health())
		self.assertNotIn("span_wide", k)
		self.assertNotIn("span_narrow", k)

	def test_a_layer_of_one(self):
		frappe.db.set_default("alvoraa_org_span_narrow", 1)
		top = self.pos("Director", seats=1)
		self.assign(self.person("Mia"), top.name, weight=100)
		only = self.pos("Deputy Director", parent=top.name, seats=1)
		self.assign(self.person("Nils"), only.name, weight=100)
		k = self.kinds(metrics.org_health())
		self.assertEqual(k["span_narrow"]["count"], 1)
		self.assertEqual(k["span_narrow"]["severity"], "low")

	def test_a_frozen_seat_with_somebody_in_it(self):
		"""Two facts that cannot both be current. Somebody has stopped keeping
		the register up to date."""
		p = self.pos("Merchandiser", seats=1, status="Frozen")
		self.assign(self.person("Omar"), p.name, weight=100)
		self.assertEqual(self.kinds(metrics.org_health())["frozen_but_filled"]["count"], 1)

	def test_a_seat_attached_to_nothing(self):
		self.pos("Floating Role", seats=1)
		self.assertEqual(self.kinds(metrics.org_health())["orphan"]["count"], 1)

	def test_a_seat_with_a_team_under_it_is_not_an_orphan(self):
		top = self.pos("Head", seats=1)
		self.pos("Assistant", parent=top.name, seats=1)
		self.assertNotIn("orphan", self.kinds(metrics.org_health()))

	def test_a_healthy_organisation_raises_nothing(self):
		"""The most important test here. A dashboard that always shows red is a
		dashboard nobody looks at."""
		frappe.db.set_default("alvoraa_org_span_narrow", 0)
		top = self.pos("Head", seats=1)
		self.assign(self.person("Pia"), top.name, weight=100)
		for i in range(3):
			seat = self.pos("Team %d" % i, parent=top.name, seats=1)
			self.assign(self.person("T%dP" % i), seat.name, weight=100)
		h = metrics.org_health()
		self.assertEqual(h["headline"]["flags"], 0)
		self.assertEqual(h["by_kind"], [])


class TestWhoMaySeeTheNumbers(MetricsCase):
	def test_an_ordinary_employee_is_refused(self):
		"""Where the holes are is a restructuring signal. It belongs to HR, and
		the refusal has to be in the endpoint - the page hiding a tile is not a
		control, it is a decoration."""
		p = self.pos("Analyst", seats=2)
		who = self.person("Quinn")
		self.assign(who, p.name, weight=100)
		email = "quinn.metrics@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": "Q",
			                "send_welcome_email": 0}).insert(ignore_permissions=True)
		frappe.db.set_value("Employee", who, "user_id", email)
		frappe.set_user(email)
		with self.assertRaises(frappe.PermissionError):
			metrics.org_health()

	def test_hygiene_flags_are_kept_off_an_employees_chart(self):
		"""An employee may see that the seat next to them is open - that is not
		a secret, it is why everybody there is busy. Register hygiene and span
		of control are HR's business and are not attached for them."""
		frappe.db.set_default("alvoraa_org_full_reach_roles", "")
		frappe.db.set_default("alvoraa_org_managers_see_all", 0)
		frappe.db.set_default("alvoraa_org_span_narrow", 1)
		top = self.pos("Director", seats=1)
		boss = self.person("Rhea")
		self.assign(boss, top.name, weight=100)
		only = self.pos("Deputy", parent=top.name, seats=1)
		self.assign(self.person("Sam"), only.name, weight=100)

		email = "rhea.metrics@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": "R",
			                "send_welcome_email": 0}).insert(ignore_permissions=True)
		frappe.db.set_value("Employee", boss, "user_id", email)
		frappe.set_user(email)
		frappe.local._alvoraa_leads = {}

		codes = {f["code"] for f in api.subtree(root=top.name)["flags"]}
		self.assertNotIn("span_narrow", codes)


class TestTheChartAndTheDashboardAgree(MetricsCase):
	def test_a_seat_the_dashboard_calls_vacant_is_tinted_on_the_chart(self):
		"""Two code paths, one truth. If these ever disagree, one of the two
		screens is lying to somebody making a headcount decision."""
		p = self.pos("Store Manager", seats=1)
		flagged = {i["position"] for i in
		           self.kinds(metrics.org_health())["vacant"]["items"]}
		codes = {f["code"] for f in api.subtree(root=p.name)["flags"]}
		self.assertIn(p.name, flagged)
		self.assertIn("vacant", codes)

	def test_every_flag_on_the_chart_explains_itself(self):
		"""Colour with no words is unreadable to roughly one man in twelve, and
		meaningless to everybody else by the second week."""
		self.pos("Chief Financial Officer", seats=1, is_key_position=1)
		p = self.pos("Store Manager", seats=1)
		for flag in api.subtree(root=p.name)["flags"]:
			self.assertTrue(flag["label"])
			self.assertTrue(flag["why"])
			self.assertIn(flag["severity"], ("high", "medium", "low"))
