"""An org chart that shows seats has to keep the arithmetic honest.

Every test here is a chart that would otherwise lie, or a rule from the spec
that only bites later if it is not enforced now:

  a person counted twice because they hold two roles
  a vacancy that is stored and drifts the first time somebody resigns
  a reporting line that loops, so every subtree count runs for ever
  a position closed with somebody still in it
  a chart that stops working for the customers who never wanted positions
  appraisals silently reassigned by somebody tidying the chart
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import subscription as sub
from hrms.alvoraa_org_structure import api

COMPANY = None


def _company():
	global COMPANY
	if not COMPANY:
		COMPANY = frappe.db.get_value("Company", {}, "name")
	return COMPANY


def _gender():
	"""Whatever this site calls a gender. Hard-coding "Female" made every test
	fail on a bench that had never had the Gender fixtures loaded."""
	existing = frappe.db.get_value("Gender", {}, "name")
	if existing:
		return existing
	return frappe.get_doc({"doctype": "Gender", "gender": "Other"}
	                      ).insert(ignore_permissions=True).name


def _clear():
	for dt in ("Alvoraa Reporting Line", "Alvoraa Position Assignment"):
		for name in frappe.get_all(dt, pluck="name"):
			frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
	# Detach everything first, then delete. A nested set refuses to drop a parent
	# that still has children - the same rule that protects a real org chart - and
	# ordering by lft is not enough once a test has left the tree half-rebuilt.
	for name in frappe.get_all("Alvoraa Position", pluck="name"):
		frappe.db.set_value("Alvoraa Position", name, "reports_to_position", None,
		                    update_modified=False)
	frappe.db.commit()
	for name in frappe.get_all("Alvoraa Position", pluck="name"):
		if frappe.db.exists("Alvoraa Position", name):
			frappe.delete_doc("Alvoraa Position", name, force=True,
			                  ignore_permissions=True, ignore_on_trash=True)
	frappe.db.commit()


class OrgCase(FrappeTestCase):
	def setUp(self):
		# org_structure is opt-in, so it is OFF on every site until a tenant is
		# ticked. Without switching it on here the chart falls back to drawing
		# people and every position test silently checks nothing.
		self._features = frappe.conf.get("features")
		frappe.conf["features"] = list(sub.DEFAULT_ON) + ["org_structure"]
		_clear()
		self._people = []

	def tearDown(self):
		if self._features is None:
			frappe.conf.pop("features", None)
		else:
			frappe.conf["features"] = self._features
		_clear()
		for emp in self._people:
			frappe.delete_doc("Employee", emp, force=True, ignore_permissions=True)
		frappe.db.commit()

	def pos(self, title, parent=None, seats=1, **kw):
		return frappe.get_doc({
			"doctype": "Alvoraa Position", "position_title": title,
			"company": _company(), "reports_to_position": parent,
			"seats": seats, "status": kw.pop("status", "Active"), **kw,
		}).insert(ignore_permissions=True)

	def person(self, name):
		doc = frappe.get_doc({
			"doctype": "Employee", "first_name": name, "company": _company(),
			"date_of_birth": "1990-01-01", "date_of_joining": "2020-01-01",
			"gender": _gender(), "status": "Active",
		}).insert(ignore_permissions=True)
		self._people.append(doc.name)
		return doc.name

	def assign(self, employee, position, weight=100, **kw):
		return frappe.get_doc({
			"doctype": "Alvoraa Position Assignment", "employee": employee,
			"position": position, "weight": weight,
			"from_date": kw.pop("from_date", "2026-01-01"), **kw,
		}).insert(ignore_permissions=True)


class TestASeatExistsWithoutAPerson(OrgCase):
	def test_an_empty_position_still_has_a_vacancy(self):
		"""The whole argument. A person-based chart would not draw this at all."""
		p = self.pos("Regional Manager South", seats=1)
		self.assertEqual(p.filled_weight(), 0.0)
		self.assertEqual(p.vacancy(), 1.0)

	def test_filling_it_removes_the_vacancy(self):
		p = self.pos("Regional Manager West")
		self.assign(self.person("Arjun"), p.name)
		p.reload()
		self.assertEqual(p.vacancy(), 0.0)

	def test_vacancy_is_never_stored(self):
		"""A stored count drifts the first time somebody resigns on a Friday."""
		fields = {f.fieldname for f in frappe.get_meta("Alvoraa Position").fields}
		self.assertNotIn("vacancy", fields)
		self.assertNotIn("filled", fields)

	def test_a_frozen_position_shows_no_vacancy(self):
		"""Real but not to be filled. A hiring pause is not an open role."""
		p = self.pos("Buyer", status="Frozen")
		self.assertEqual(p.vacancy(), 0.0)


class TestWeights(OrgCase):
	def test_one_person_can_hold_two_positions(self):
		ops, qa = self.pos("Head of Operations"), self.pos("Head of Quality")
		who = self.person("Priya")
		self.assign(who, ops.name, weight=70)
		self.assign(who, qa.name, weight=30)
		self.assertEqual(frappe.db.count("Alvoraa Position Assignment", {"employee": who}), 2)

	def test_headcount_does_not_double_count(self):
		"""The reason weights exist. Without them a hundred people report as
		a hundred and twelve."""
		ops, qa = self.pos("Head of Operations"), self.pos("Head of Quality")
		who = self.person("Priya")
		self.assign(who, ops.name, weight=70)
		self.assign(who, qa.name, weight=30)
		ops.reload(); qa.reload()
		self.assertAlmostEqual(ops.filled_weight() + qa.filled_weight(), 1.0, places=2)

	def test_a_person_cannot_exceed_one_person(self):
		ops, qa = self.pos("Head of Operations"), self.pos("Head of Quality")
		who = self.person("Priya")
		self.assign(who, ops.name, weight=70)
		with self.assertRaises(frappe.ValidationError):
			self.assign(who, qa.name, weight=50)

	def test_a_three_way_split_is_allowed(self):
		"""34/33/33 must not be refused for being one hundredth short."""
		a, b, c = self.pos("A"), self.pos("B"), self.pos("C")
		who = self.person("Meera")
		self.assign(who, a.name, weight=34)
		self.assign(who, b.name, weight=33)
		self.assign(who, c.name, weight=33)
		self.assertEqual(frappe.db.count("Alvoraa Position Assignment", {"employee": who}), 3)

	def test_a_weight_of_zero_is_refused(self):
		p = self.pos("Analyst")
		with self.assertRaises(frappe.ValidationError):
			self.assign(self.person("Sam"), p.name, weight=0)

	def test_two_halves_fill_one_seat(self):
		"""A job share. One seat, two people, not over-filled."""
		p = self.pos("Store Manager", seats=1)
		self.assign(self.person("Asha"), p.name, weight=50)
		self.assign(self.person("Bela"), p.name, weight=50)
		p.reload()
		self.assertAlmostEqual(p.filled_weight(), 1.0, places=2)
		self.assertEqual(p.vacancy(), 0.0)

	def test_a_seat_cannot_be_over_filled(self):
		p = self.pos("Store Manager", seats=1)
		self.assign(self.person("Asha"), p.name, weight=100)
		with self.assertRaises(frappe.ValidationError):
			self.assign(self.person("Bela"), p.name, weight=100)

	def test_exactly_one_primary_per_person(self):
		ops, qa = self.pos("Ops"), self.pos("QA")
		who = self.person("Priya")
		self.assign(who, ops.name, weight=60, is_primary=1)
		self.assign(who, qa.name, weight=40, is_primary=1)
		primaries = frappe.get_all("Alvoraa Position Assignment",
		                           filters={"employee": who, "is_primary": 1}, pluck="name")
		self.assertEqual(len(primaries), 1)


class TestTheTreeHolds(OrgCase):
	def test_a_position_cannot_report_to_itself(self):
		p = self.pos("Chief Executive")
		p.reports_to_position = p.name
		with self.assertRaises(frappe.ValidationError):
			p.save(ignore_permissions=True)

	def test_the_chain_cannot_loop(self):
		a = self.pos("A")
		b = self.pos("B", parent=a.name)
		a.reports_to_position = b.name
		with self.assertRaises(Exception):
			a.save(ignore_permissions=True)

	def test_a_position_with_people_cannot_be_deleted(self):
		p = self.pos("Cashier")
		self.assign(self.person("Ravi"), p.name)
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Alvoraa Position", p.name, ignore_permissions=True)

	def test_seats_cannot_drop_below_the_people_in_them(self):
		p = self.pos("Cashier", seats=2)
		self.assign(self.person("Ravi"), p.name)
		self.assign(self.person("Sunil"), p.name)
		p.reload()
		p.seats = 1
		with self.assertRaises(frappe.ValidationError):
			p.save(ignore_permissions=True)


class TestMatrixLines(OrgCase):
	def test_a_dotted_line_is_not_in_the_tree(self):
		"""A second parent breaks the nested set and every count built on it."""
		fields = {f.fieldname for f in frappe.get_meta("Alvoraa Position").fields}
		self.assertEqual([f for f in fields if "reports_to" in f], ["reports_to_position"])

	def test_a_line_cannot_point_at_itself(self):
		p = self.pos("Finance Controller")
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "Alvoraa Reporting Line",
			                "from_position": p.name, "to_position": p.name}
			               ).insert(ignore_permissions=True)

	def test_it_cannot_duplicate_the_solid_line(self):
		"""Two lines between the same boxes tells a reader there are two
		relationships."""
		boss = self.pos("Head of Sales")
		rm = self.pos("Regional Manager", parent=boss.name)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "Alvoraa Reporting Line",
			                "from_position": rm.name, "to_position": boss.name}
			               ).insert(ignore_permissions=True)


class TestItNeverTouchesAppraisals(OrgCase):
	"""`reports_to` routes performance reviews - pms_cycle.py reads it. Deriving
	it from the chart would reassign live appraisals as a side effect of somebody
	tidying up, and nobody would connect the two."""

	def test_assigning_a_position_leaves_reports_to_alone(self):
		p = self.pos("Analyst")
		who = self.person("Nikhil")
		before = frappe.db.get_value("Employee", who, "reports_to")
		self.assign(who, p.name)
		self.assertEqual(frappe.db.get_value("Employee", who, "reports_to"), before)

	def test_the_code_never_writes_to_the_employee_record(self):
		"""Reading reports_to to REPORT a mismatch is fine. Writing it is not."""
		import inspect

		src = inspect.getsource(api).replace(" ", "")
		for forbidden in ('set_value("Employee"', 'db_set("reports_to"', '.reports_to='):
			self.assertNotIn(forbidden.replace(" ", ""), src, forbidden)


class TestItStillWorksWithoutPositions(OrgCase):
	"""A mid-market customer will not maintain a position register just to see a
	chart. If the fallback breaks, the feature is unusable for most tenants."""

	def test_no_positions_means_the_people_chart(self):
		nodes = api.get_children(company=_company())
		self.assertTrue(all(n.get("kind") == "person" for n in nodes), nodes[:2])


class TestTemporaryCover(OrgCase):
	"""A store in-charge covering a second store still does their own job in
	full. The cover is extra duty, not a reallocation - so it is not squeezed
	into the same 100, and the extra load is shown rather than hidden."""

	def test_cover_is_carried_on_top_of_a_full_role(self):
		ambala = self.pos("Store In-charge Ambala")
		chandigarh = self.pos("Store In-charge Chandigarh")
		ravi = self.person("Ravi")
		self.assign(ravi, ambala.name, weight=100)
		self.assign(ravi, chandigarh.name, weight=30,
		            assignment_type="Acting", to_date="2026-12-31")
		self.assertEqual(frappe.db.count("Alvoraa Position Assignment", {"employee": ravi}), 2)

	def test_a_second_permanent_role_is_still_refused(self):
		"""The cap has not been switched off - only cover is exempt from it."""
		a, b = self.pos("Store In-charge Ambala"), self.pos("Store In-charge Chandigarh")
		ravi = self.person("Ravi")
		self.assign(ravi, a.name, weight=100)
		with self.assertRaises(frappe.ValidationError):
			self.assign(ravi, b.name, weight=30)

	def test_cover_partly_fills_the_seat_it_covers(self):
		"""Honest arithmetic: a seat covered at 30 is still 70 vacant, because
		it is. Counting cover as a full head would hide the hole."""
		chandigarh = self.pos("Store In-charge Chandigarh", seats=1)
		self.assign(self.person("Ravi"), chandigarh.name, weight=30,
		            assignment_type="Acting", to_date="2026-12-31")
		chandigarh.reload()
		self.assertAlmostEqual(chandigarh.vacancy(), 0.7, places=2)

	def test_cover_is_never_the_primary_position(self):
		"""Somebody standing in for a fortnight must not become the person whose
		appraisal and approvals route through the covered seat."""
		own = self.pos("Store In-charge Ambala")
		cover = self.pos("Store In-charge Chandigarh")
		ravi = self.person("Ravi")
		self.assign(ravi, own.name, weight=100)
		row = self.assign(ravi, cover.name, weight=30,
		                  assignment_type="Acting", to_date="2026-12-31",
		                  is_primary=1)
		row.reload()
		self.assertFalse(row.is_primary)
		self.assertTrue(frappe.db.get_value(
			"Alvoraa Position Assignment",
			{"employee": ravi, "position": own.name}, "is_primary"))


class TestANewJoinerIsNotThereYet(OrgCase):
	def test_an_assignment_cannot_start_before_they_join(self):
		"""The seat is created and the offer signed weeks ahead. They must not
		appear in the chart on a day they do not work here."""
		p = self.pos("Senior Sales Executive")
		who = self.person("Ritika")
		frappe.db.set_value("Employee", who, "date_of_joining", "2026-11-01")
		with self.assertRaises(frappe.ValidationError):
			self.assign(who, p.name, from_date="2026-10-01")

	def test_from_their_joining_date_onwards_is_fine(self):
		p = self.pos("Senior Sales Executive")
		who = self.person("Ritika")
		frappe.db.set_value("Employee", who, "date_of_joining", "2026-11-01")
		self.assign(who, p.name, from_date="2026-11-01")   # no raise

	def test_they_do_not_fill_the_seat_before_they_arrive(self):
		"""The chart for today must show the seat empty, whatever is planned."""
		p = self.pos("Senior Sales Executive", seats=1)
		who = self.person("Ritika")
		frappe.db.set_value("Employee", who, "date_of_joining", "2099-01-01")
		self.assign(who, p.name, from_date="2099-01-01")
		people = api._people_in(p.name, nowdate())
		self.assertEqual(people, [])


class TestDottedLineInTheAppraisal(OrgCase):
	"""The person who judges half of somebody's work should have a say in their
	rating. Today the appraisal hears only the solid line."""

	def setUp(self):
		super().setUp()
		from hrms.alvoraa_org_structure import dotted_line

		self.dl = dotted_line

	def _wire(self):
		acct = self.pos("Accountant Chandigarh")
		fin = self.pos("Finance Controller")
		who, boss = self.person("Anita"), self.person("Meera")
		self.assign(who, acct.name)
		self.assign(boss, fin.name)
		frappe.get_doc({"doctype": "Alvoraa Reporting Line",
		                "from_position": acct.name, "to_position": fin.name,
		                "line_type": "Functional"}).insert(ignore_permissions=True)
		return who, boss

	def test_it_finds_the_dotted_line_manager(self):
		who, boss = self._wire()
		found = [b["employee"] for b in self.dl.dotted_line_managers(who)]
		self.assertEqual(found, [boss])

	def test_somebody_with_no_dotted_line_has_none(self):
		p = self.pos("Cashier")
		who = self.person("Sunil")
		self.assign(who, p.name)
		self.assertEqual(self.dl.dotted_line_managers(who), [])

	def test_cover_does_not_drag_somebody_into_an_appraisal(self):
		"""Standing in for a fortnight is not grounds to judge a whole quarter."""
		acct = self.pos("Accountant Chandigarh")
		fin = self.pos("Finance Controller")
		who, stand_in = self.person("Anita"), self.person("Temp")
		self.assign(who, acct.name)
		self.assign(stand_in, fin.name, weight=40,
		            assignment_type="Interim", to_date="2026-12-31")
		frappe.get_doc({"doctype": "Alvoraa Reporting Line",
		                "from_position": acct.name, "to_position": fin.name}
		               ).insert(ignore_permissions=True)
		self.assertEqual(self.dl.dotted_line_managers(who), [])

	def test_nobody_is_their_own_dotted_line_manager(self):
		"""Happens the moment one person holds two linked positions."""
		a, b = self.pos("Head of Ops"), self.pos("Head of Quality")
		who = self.person("Priya")
		self.assign(who, a.name, weight=60)
		self.assign(who, b.name, weight=40)
		frappe.get_doc({"doctype": "Alvoraa Reporting Line",
		                "from_position": a.name, "to_position": b.name}
		               ).insert(ignore_permissions=True)
		self.assertEqual(self.dl.dotted_line_managers(who), [])
