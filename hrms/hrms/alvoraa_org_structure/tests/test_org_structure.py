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
		_clear()
		self._people = []

	def tearDown(self):
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
