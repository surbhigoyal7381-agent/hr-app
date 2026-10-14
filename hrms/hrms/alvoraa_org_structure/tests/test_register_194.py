"""The position register as a working list: who may read it, who may change it.

The thing being proved here is the split. Reading the list and changing it are
two different permissions on purpose - a branch head planning next month's cover
needs to see the empty seats in their store, and letting them redraw the company
is a different decision entirely.

Who may change it is a SETTING, not a role fixed in code, because it genuinely
differs by customer: at the first one the owners keep the structure themselves
and HR does not touch it.
"""

import frappe

from hrms.alvoraa_org_structure import register, settings
from hrms.alvoraa_org_structure.tests.test_company_scope_194 import CompanyScopeCase
from hrms.alvoraa_org_structure.tests.test_org_structure import _company


class RegisterCase(CompanyScopeCase):
	def setUp(self):
		super().setUp()
		self._saved = {k: frappe.db.get_default(k) for k in settings.DEFAULTS}

	def tearDown(self):
		for k, v in self._saved.items():
			frappe.db.set_default(k, v if v is not None else "")
		super().tearDown()

	def editors(self, roles):
		frappe.db.set_default(register.EDITOR_ROLES_KEY, roles)

	def titles(self, result):
		return sorted(r["title"] for r in result["rows"])


class TestWhoMayReadTheList(RegisterCase):
	def test_hr_sees_every_seat(self):
		self.pos("Counter Staff Here", seats=2)
		self.pos("Head Office Role", seats=1)
		frappe.set_user(self.hr_user("reg194.hr@example.com"))
		self.assertEqual(self.titles(register.position_table()),
		                 ["Counter Staff Here", "Head Office Role"])

	def test_a_store_hr_person_sees_only_their_store(self):
		here, there = self.branch("Scope194 Here"), self.branch("Scope194 There")
		self.pos("Counter Staff Here", seats=2, branch=here)
		self.pos("Counter Staff There", seats=3, branch=there)
		frappe.set_user(self.hr_user("reg194.store@example.com", branch=here))
		self.assertEqual(self.titles(register.position_table()), ["Counter Staff Here"])

	def test_asking_for_somebody_elses_branch_does_not_widen_the_answer(self):
		"""The filter narrows what you may see. It never reaches past it."""
		here, there = self.branch("Scope194 Here"), self.branch("Scope194 There")
		self.pos("Counter Staff Here", seats=2, branch=here)
		self.pos("Counter Staff There", seats=3, branch=there)
		frappe.set_user(self.hr_user("reg194.store2@example.com", branch=here))
		self.assertEqual(self.titles(register.position_table(branch=there)), [])

	def test_an_ordinary_employee_is_refused(self):
		self.pos("Counter Staff Here", seats=1)
		emp = self.person("Plain")
		user = "reg194.plain@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc({"doctype": "User", "email": user, "first_name": "Plain",
			                "enabled": 1, "send_welcome_email": 0}).insert(ignore_permissions=True)
			self._cleanup.append(("User", user))
		frappe.db.set_value("Employee", emp, "user_id", user)
		frappe.db.commit()
		frappe.set_user(user)
		with self.assertRaises(frappe.PermissionError):
			register.position_table()


class TestHowFullEachSeatIs(RegisterCase):
	def test_an_empty_seat_reads_as_open(self):
		self.pos("Counter Staff Here", seats=2)
		frappe.set_user(self.hr_user("reg194.hr2@example.com"))
		row = register.position_table()["rows"][0]
		self.assertEqual(row["seats"], 2.0)
		self.assertEqual(row["filled"], 0.0)
		self.assertEqual(row["open"], 2.0)

	def test_half_a_person_leaves_half_a_seat(self):
		"""Two at 50% of a one-seat role leave nothing open; one leaves half.
		The half is the number somebody recruits against."""
		p = self.pos("Counter Staff Here", seats=1)
		self.assign(self.person("Asha"), p.name, weight=50)
		frappe.set_user(self.hr_user("reg194.hr3@example.com"))
		row = register.position_table()["rows"][0]
		self.assertEqual(row["open"], 0.5)
		self.assertEqual(row["people"][0]["weight"], 50.0)

	def test_the_parent_is_named_so_the_table_reads_on_its_own(self):
		top = self.pos("Store Manager", seats=1)
		self.pos("Counter Staff Here", parent=top.name, seats=1)
		frappe.set_user(self.hr_user("reg194.hr4@example.com"))
		rows = {r["title"]: r for r in register.position_table()["rows"]}
		self.assertEqual(rows["Counter Staff Here"]["reports_to_title"], "Store Manager")


class TestWhoMayChangeIt(RegisterCase):
	def test_reading_is_wider_than_changing(self):
		"""An HR User may read the list, and by default may not change it."""
		self.pos("Counter Staff Here", seats=1)
		frappe.set_user(self.hr_user("reg194.hr5@example.com"))
		self.assertFalse(register.position_table()["may_edit"])

	def test_the_setting_decides_and_nothing_else(self):
		self.pos("Counter Staff Here", seats=1)
		self.editors("HR User")
		frappe.set_user(self.hr_user("reg194.hr6@example.com"))
		self.assertTrue(register.may_edit())

	def test_somebody_the_setting_does_not_name_is_refused(self):
		self.editors("Some Role Nobody Has")
		frappe.set_user(self.hr_user("reg194.hr7@example.com"))
		with self.assertRaises(frappe.PermissionError):
			register.save_position(position_title="Sneaked In", seats=1)

	def test_an_editor_can_create_an_empty_seat(self):
		"""Which is how a vacancy becomes visible instead of living in a
		spreadsheet."""
		self.editors("HR User")
		frappe.set_user(self.hr_user("reg194.hr8@example.com"))
		register.save_position(position_title="Second Cashier", seats=1,
		                       company=_company())
		rows = {r["title"]: r for r in register.position_table()["rows"]}
		self.assertEqual(rows["Second Cashier"]["open"], 1.0)
		self.assertEqual(rows["Second Cashier"]["filled"], 0.0)

	def test_an_editor_can_move_a_seat_under_another(self):
		"""The hierarchy itself - which is the point of a position register."""
		top = self.pos("Store Manager", seats=1)
		child = self.pos("Counter Staff Here", seats=1)
		self.editors("HR User")
		frappe.set_user(self.hr_user("reg194.hr9@example.com"))
		register.save_position(name=child.name, reports_to_position=top.name)
		rows = {r["title"]: r for r in register.position_table()["rows"]}
		self.assertEqual(rows["Counter Staff Here"]["reports_to_title"], "Store Manager")

	def test_a_seat_cannot_report_to_itself(self):
		p = self.pos("Store Manager", seats=1)
		self.editors("HR User")
		frappe.set_user(self.hr_user("reg194.hr10@example.com"))
		with self.assertRaises(frappe.ValidationError):
			register.save_position(name=p.name, reports_to_position=p.name)

	def test_a_store_editor_cannot_create_a_seat_in_another_store(self):
		here, there = self.branch("Scope194 Here"), self.branch("Scope194 There")
		self.editors("HR User")
		frappe.set_user(self.hr_user("reg194.store3@example.com", branch=here))
		with self.assertRaises(frappe.PermissionError):
			register.save_position(position_title="Theirs Not Mine", seats=1,
			                       branch=there, company=_company())

	def test_a_store_editor_cannot_change_a_seat_in_another_store(self):
		here, there = self.branch("Scope194 Here"), self.branch("Scope194 There")
		theirs = self.pos("Counter Staff There", seats=1, branch=there)
		self.editors("HR User")
		frappe.set_user(self.hr_user("reg194.store4@example.com", branch=here))
		with self.assertRaises(frappe.PermissionError):
			register.save_position(name=theirs.name, seats=9)
