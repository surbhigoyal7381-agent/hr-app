"""The position register as a working list: who may read it, who may change it.

The thing being proved here is the split. Reading the list and changing it are
two different permissions on purpose - a branch head planning next month's cover
needs to see the empty seats in their store, and letting them redraw the company
is a different decision entirely.

Who may change it is Frappe's own permission on Alvoraa Position, set in Role
Permissions Manager, because it genuinely differs by customer: at the first one
the owners keep the structure themselves and HR does not touch it.
"""

import frappe

from hrms.alvoraa_org_structure import register, settings
from hrms.alvoraa_org_structure.tests.test_company_scope_194 import CompanyScopeCase
from hrms.alvoraa_org_structure.tests.test_org_structure import _company

ASSIGNMENT = "Alvoraa Position Assignment"
# Not one of the two: a change here must leave no record.
OTHER = "Alvoraa Reporting Line"
TOUCHED = (register.POSITION, ASSIGNMENT, OTHER)


def _forget_permissions():
	"""Make Frappe re-read who may do what, as Role Permissions Manager does."""
	for dt in TOUCHED:
		frappe.clear_cache(doctype=dt)
	frappe.local.role_permissions = {}


def _trail():
	"""Every row a permission change on these doctypes can leave behind: the
	rows themselves, our Version record, and Frappe's own Permission Log."""
	return {
		"Custom DocPerm": set(frappe.get_all("Custom DocPerm",
		                                     filters={"parent": ("in", TOUCHED)}, pluck="name")),
		"Version": set(frappe.get_all("Version", filters={"ref_doctype": "DocType",
		                                                  "docname": ("in", TOUCHED)}, pluck="name")),
		"Permission Log": set(frappe.get_all("Permission Log",
		                                     filters={"for_document": ("in", TOUCHED)}, pluck="name")),
	}


class RegisterCase(CompanyScopeCase):
	def setUp(self):
		super().setUp()
		self._before = _trail()
		# These tests are about scope and editing, and they run as an HR User.
		# The shipped table gives HR User nothing, so they say exactly what the
		# HR User may do here - the way an administrator would, in Role
		# Permissions Manager. Who may open the page with NO extra rows is
		# pinned in TestWhoMayOpenThePage.
		self.rows(("HR User", "read"))

	def tearDown(self):
		"""Everything this test added to the permission trail goes, committed,
		or it leaks onto test_site and changes the next run."""
		frappe.set_user("Administrator")
		for doctype, names in _trail().items():
			for name in names - self._before[doctype]:
				frappe.db.delete(doctype, {"name": name})
		frappe.db.commit()
		_forget_permissions()
		super().tearDown()

	def rows(self, *grants, doctype=None):
		"""Replace the permission table with exactly these rows, as Custom
		DocPerm - which Frappe then uses INSTEAD OF the shipped rows.

		Each grant is (role, "read") or (role, "write").
		"""
		self.no_rows(doctype or register.POSITION)
		for role, level in grants:
			frappe.get_doc({
				"doctype": "Custom DocPerm", "parent": doctype or register.POSITION,
				"parenttype": "DocType", "parentfield": "permissions",
				"role": role, "permlevel": 0, "read": 1,
				"write": int(level == "write"), "create": int(level == "write"),
			}).insert(ignore_permissions=True)
		frappe.db.commit()
		_forget_permissions()

	def no_rows(self, doctype=None):
		"""Back to the shipped table, for one doctype or all of them."""
		for name in _trail()["Custom DocPerm"] - self._before["Custom DocPerm"]:
			if doctype and frappe.db.get_value("Custom DocPerm", name, "parent") != doctype:
				continue
			frappe.db.delete("Custom DocPerm", {"name": name})
		frappe.db.commit()
		_forget_permissions()

	def editors(self, role):
		self.rows((role, "write"))

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

	def test_the_permission_row_decides_and_nothing_else(self):
		self.pos("Counter Staff Here", seats=1)
		self.editors("HR User")
		frappe.set_user(self.hr_user("reg194.hr6@example.com"))
		self.assertTrue(register.may_edit())

	def test_somebody_the_rows_do_not_name_is_refused(self):
		self.editors("System Manager")      # and nothing for HR User
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


class TestWhoMayOpenThePage(RegisterCase):
	"""Surbhi, 19 Oct 2026: "I want the position access to be provided through
	the Frappe interface like other standard Frappe modules".

	So the page asks Frappe: Read on Alvoraa Position opens it, Write changes
	it. An administrator sets that in Role Permissions Manager. The rows these
	tests write are Custom DocPerm, which is exactly what that screen writes.
	"""

	OWNER_ROLE = "Org061 Structure Editor"

	def setUp(self):
		super().setUp()
		self.no_rows()          # the shipped table, as on a tenant nobody customised
		self.seat = self.pos("Counter Staff Here", seats=1).name

	def user(self, email, roles=(), employee=None):
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": "Open",
			                "enabled": 1, "send_welcome_email": 0}).insert(ignore_permissions=True)
			self._cleanup.append(("User", email))
		if employee:
			frappe.db.set_value("Employee", employee, "user_id", email)
		u = frappe.get_doc("User", email)
		u.flags.ignore_permissions = True
		if roles:
			u.add_roles(*roles)
		frappe.db.commit()
		return email

	def hr_manager(self, email):
		return self.user(email, roles=("HR Manager",), employee=self.person("Open061 HRM"))

	def refused_everywhere(self, employee):
		for call in (lambda: register.position_table(),
		             lambda: register.where_does_this_person_sit(employee),
		             lambda: register.what_they_hold(employee)):
			with self.assertRaises(frappe.PermissionError):
				call()

	def test_the_shipped_rows_are_hr_manager_and_system_manager_only(self):
		"""Pinned on the files, so the shipped table cannot quietly widen again.
		Employee read and HR User write were in it until 19 Oct 2026, which
		would have opened the page to every member of staff."""
		import json
		import os

		for dt in ("alvoraa_position", "alvoraa_position_assignment"):
			path = os.path.join(os.path.dirname(register.__file__), "doctype", dt, dt + ".json")
			with open(path) as f:
				roles = sorted(p["role"] for p in json.load(f)["permissions"])
			self.assertEqual(roles, ["HR Manager", "System Manager"], dt)

	def test_the_role_list_settings_are_gone(self):
		"""Retired for Frappe's own table. Two places to set one thing is how
		DTC came to have its owners refused by one and allowed by the other."""
		for key in ("alvoraa_org_positions_view_roles", "alvoraa_org_position_editor_roles"):
			self.assertNotIn(key, settings.DEFAULTS)
			self.assertNotIn(key, settings.LABELS)
			self.assertNotIn(key, settings.ACCESS_GRANTING)

	def test_an_hr_manager_row_gives_view_and_edit(self):
		frappe.set_user(self.hr_manager("open061.hrm@example.com"))
		self.assertTrue(register.may_view())
		self.assertTrue(register.may_edit())
		self.assertIn("Counter Staff Here", self.titles(register.position_table()))

	def test_taking_the_hr_manager_row_away_takes_both(self):
		"""Grace's rows: System Manager only."""
		self.rows(("System Manager", "write"))
		self.rows(("System Manager", "write"), doctype=ASSIGNMENT)
		emp = self.person("Open061 Other")
		frappe.set_user(self.hr_manager("open061.hrm2@example.com"))
		self.assertFalse(register.may_view())
		self.assertFalse(register.may_edit())
		self.refused_everywhere(emp)
		with self.assertRaises(frappe.PermissionError):
			register.save_position(position_title="Sneaked In", seats=1)

	def test_read_alone_opens_the_page_but_changes_nothing(self):
		self.rows(("HR Manager", "read"))
		frappe.set_user(self.hr_manager("open061.hrm3@example.com"))
		self.assertTrue(register.may_view())
		self.assertFalse(register.may_edit())
		self.assertFalse(register.position_table()["may_edit"])
		with self.assertRaises(frappe.PermissionError):
			register.save_position(position_title="Sneaked In", seats=1)
		with self.assertRaises(frappe.PermissionError):
			register.assign_person(self.seat, self.person("Open061 Somebody"))

	def test_dtc_shaped_rows_let_the_owners_in_and_keep_hr_out(self):
		"""DTC's own rows, 15 Oct 2026: System Manager, and a role of their own
		with read, write and create on Alvoraa Position. On the Assignment
		doctype, System Manager ONLY. HR Manager has no row on either.

		The owners can still put people in seats: one capability, governed by
		Alvoraa Position. And they see their own company's seats, though they
		hold no HR role."""
		if not frappe.db.exists("Role", self.OWNER_ROLE):
			frappe.get_doc({"doctype": "Role", "role_name": self.OWNER_ROLE,
			                "desk_access": 1}).insert(ignore_permissions=True)
			self._cleanup.insert(0, ("Role", self.OWNER_ROLE))
		self.rows(("System Manager", "write"), (self.OWNER_ROLE, "write"))
		self.rows(("System Manager", "write"), doctype=ASSIGNMENT)

		owner = self.person("Open061 Owner")
		report = self.person("Open061 Report")
		frappe.db.set_value("Employee", report, "reports_to", owner)
		hrm = self.hr_manager("open061.hrm4@example.com")
		try:
			frappe.set_user(self.user("open061.owner@example.com",
			                          roles=(self.OWNER_ROLE,), employee=owner))
			self.assertTrue(register.may_view())
			self.assertTrue(register.may_edit())
			self.assertIn("Counter Staff Here", self.titles(register.position_table()))
			made = register.save_position(position_title="Open061 New Seat", seats=1)
			got = register.assign_person(made["name"], report)
			self.assertEqual(frappe.db.get_value(ASSIGNMENT, got["name"], "employee"), report)

			frappe.set_user(hrm)
			self.assertFalse(register.may_view())
			self.refused_everywhere(report)
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Employee", report, "reports_to", None)

	def test_a_plain_employee_is_refused(self):
		emp = self.person("Open060 Plain")
		frappe.set_user(self.user("open060.plain@example.com", employee=emp))
		self.assertFalse(register.may_view())
		self.refused_everywhere(emp)

	def test_a_manager_with_direct_reports_is_refused(self):
		"""THE CASE THAT MATTERS. Such a manager still sees the whole org
		chart - `reach()` is untouched - but not this page, because no
		permission row names them."""
		from hrms.alvoraa_org_structure.api import reach

		frappe.db.set_default("alvoraa_org_managers_see_all", 1)
		boss = self.person("Open060 Boss")
		report = self.person("Open060 Report")
		frappe.db.set_value("Employee", report, "reports_to", boss)
		try:
			frappe.set_user(self.user("open060.boss@example.com", employee=boss))
			frappe.local._alvoraa_leads = {}
			self.assertTrue(reach()["unlimited"], "the chart must still be open to them")
			self.assertFalse(register.may_view())
			self.refused_everywhere(report)
			with self.assertRaises(frappe.PermissionError):
				register.assign_person(self.seat, report)
		finally:
			# The tear-down deletes people in the order they were made, and a
			# manager cannot be deleted while somebody reports to them.
			frappe.db.set_value("Employee", report, "reports_to", None)

	def test_an_hr_user_is_refused_by_default(self):
		"""HR Manager, as she said - not every HR role."""
		frappe.set_user(self.hr_user("open060.hru@example.com"))
		self.assertFalse(register.may_view())
		with self.assertRaises(frappe.PermissionError):
			register.position_table()

	def test_a_system_manager_can_view_and_edit(self):
		email = self.user("open060.sm@example.com", roles=("System Manager",))
		frappe.set_user(email)
		self.assertTrue(register.may_view())
		self.assertTrue(register.may_edit())

	def test_the_proposal_endpoints_follow_the_edit_rule(self):
		"""They write seats, so Read alone is not enough, and the old fixed
		HR Manager check is gone: whoever may change the structure may use
		them."""
		from hrms.alvoraa_org_structure import api

		self.rows(("HR Manager", "read"))
		frappe.set_user(self.hr_manager("open061.hrm5@example.com"))
		with self.assertRaises(frappe.PermissionError):
			api.propose_positions()
		with self.assertRaises(frappe.PermissionError):
			api.create_proposed_positions([])

		frappe.set_user("Administrator")
		self.rows(("HR Manager", "write"))
		frappe.set_user("open061.hrm5@example.com")
		self.assertIn("positions", api.propose_positions())
		self.assertEqual(api.create_proposed_positions([])["positions_created"], 0)


class TestEveryPermissionChangeLeavesARecord(RegisterCase):
	"""Surbhi, 19 Oct 2026: yes to a change record. The old settings left a
	Version row for each change (SEC-18); Custom DocPerm leaves none of its own
	that an auditor could read.

	Driven through Role Permissions Manager's own functions - add, update,
	remove - so this proves the screen's real path fires the hook.
	"""

	def setUp(self):
		super().setUp()
		self.no_rows()          # the shipped table: the next change is the first
		self._seen = _trail()["Version"]

	def new_records(self):
		"""What was written since the last call, oldest first, as readable rows."""
		names = _trail()["Version"] - self._seen
		self._seen |= names
		out = []
		for v in frappe.get_all("Version", filters={"name": ("in", list(names))},
		                        fields=["docname", "owner", "data"], order_by="creation asc"):
			out.append((v.docname, v.owner, frappe.parse_json(v.data)["changed"]))
		return out

	def label(self, fieldname):
		return frappe.get_meta("Custom DocPerm").get_label(fieldname)

	def test_adding_ticking_and_removing_each_leave_one_readable_record(self):
		from frappe.core.page.permission_manager import permission_manager as screen

		screen.add(register.POSITION, "HR User", 0)
		got = self.new_records()
		added = [r for r in got if r[2][0][2] == "added"]
		self.assertEqual(len(added), 1, got)
		docname, owner, changed = added[0]
		self.assertEqual((docname, owner), (register.POSITION, "Administrator"))
		# Frappe gives a new row Export as well as Read, and the record says so.
		self.assertEqual(changed, [["Role row: HR User", "not on the list", "added"],
		                           ["HR User: " + self.label("read"), "No", "Yes"],
		                           ["HR User: " + self.label("export"), "No", "Yes"]])

		screen.update(register.POSITION, "HR User", 0, "write", 1)
		self.assertEqual(self.new_records(), [(register.POSITION, "Administrator",
		                 [["HR User: " + self.label("write"), "No", "Yes"]])])

		screen.remove(register.POSITION, "HR User", 0)
		got = self.new_records()
		self.assertEqual(len(got), 1, got)
		self.assertEqual(got[0][2], [["Role row: HR User", "on the list", "removed"],
		                             ["HR User: " + self.label("read"), "Yes", "No"],
		                             ["HR User: " + self.label("write"), "Yes", "No"],
		                             ["HR User: " + self.label("export"), "Yes", "No"]])

	def test_the_first_change_copies_do_not_read_as_grants(self):
		"""Frappe copies every shipped row the first time anything changes.
		Its own Permission Log calls those rows "Added"; ours must not."""
		from frappe.core.page.permission_manager import permission_manager as screen

		screen.add(register.POSITION, "HR User", 0)
		copies = [r for r in self.new_records() if r[2][0][2] != "added"]
		self.assertEqual(sorted(c[2][0][0] for c in copies),
		                 ["Role row: HR Manager", "Role row: System Manager"])
		for c in copies:
			self.assertEqual(c[2], [[c[2][0][0], "shipped table",
			                         "copied as it was - nobody gained or lost a right"]])

	def test_resetting_says_the_shipped_rows_apply_again(self):
		"""Reset deletes every row of the doctype's own. Read one by one that
		looks like HR losing everything; in fact the shipped table is back."""
		from frappe.core.page.permission_manager import permission_manager as screen

		screen.add(register.POSITION, "HR User", 0)
		self.new_records()
		screen.reset(register.POSITION)
		last = self.new_records()[-1][2][-1]
		self.assertEqual(last, ["Permission table", "this organisation's own rows",
		                        "the shipped rows apply again: HR Manager, System Manager"])

	def test_the_assignment_doctype_is_recorded_too(self):
		from frappe.core.page.permission_manager import permission_manager as screen

		screen.add(ASSIGNMENT, "HR User", 0)
		self.assertIn(ASSIGNMENT, {r[0] for r in self.new_records()})

	def test_a_change_on_another_doctype_writes_nothing(self):
		from frappe.core.page.permission_manager import permission_manager as screen

		screen.add(OTHER, "HR User", 0)
		screen.update(OTHER, "HR User", 0, "write", 1)
		self.assertEqual(self.new_records(), [])

	def test_a_migrate_writes_nothing(self):
		"""Skipped on purpose: nobody chose it on the screen."""
		from frappe.core.page.permission_manager import permission_manager as screen

		frappe.flags.in_migrate = True
		try:
			screen.add(register.POSITION, "HR User", 0)
		finally:
			frappe.flags.in_migrate = False
		self.assertEqual(self.new_records(), [])
