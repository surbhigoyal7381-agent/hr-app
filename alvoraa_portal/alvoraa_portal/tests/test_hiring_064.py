"""Slice 064: a job opening's seat link, and the hire placed by it.

The link on Job Opening (`alvoraa_position`) decides who sits in which seat
once a hire from that opening is placed by itself. These tests run as the
people who would really do it - an HR User with no right to place people in
seats, and a Positions editor tied to one branch - never as Administrator,
for whom every check passes and proves nothing (SEC-7 c).

Kept in alvoraa_portal's tests so they run in CI.
"""

from unittest.mock import patch

import frappe

import hrms.alvoraa_org_structure.register as register
from hrms.alvoraa_org_structure.tests.test_register_194 import RegisterCase

import alvoraa_portal.org_job_link as org_job_link

OPENING = "Job Opening"
ASSIGNMENT = "Alvoraa Position Assignment"
EDITOR = "Positions Editor 064"


def _designation(name):
	if not frappe.db.exists("Designation", name):
		frappe.get_doc({"doctype": "Designation", "designation_name": name}).insert(ignore_permissions=True)
	return name


class HiringCase(RegisterCase):
	def setUp(self):
		super().setUp()
		org_job_link.after_migrate()
		frappe.clear_cache(doctype=OPENING)
		if not frappe.db.exists("Role", EDITOR):
			frappe.get_doc({"doctype": "Role", "role_name": EDITOR, "desk_access": 1}).insert(ignore_permissions=True)
		# DTC's shape: the structure belongs to System Manager and a role of the
		# owners' own. HR User may NOT place people in seats.
		self.rows(("System Manager", "write"), (EDITOR, "write"))
		self.rows(("System Manager", "write"), (EDITOR, "write"), doctype=ASSIGNMENT)
		self.delhi, self.noida = self.branch("Delhi 064"), self.branch("Noida 064")
		self.role = _designation("Store Manager 064")
		self.seat_delhi = self.pos("Store Manager 064", branch=self.delhi, designation=self.role).name
		self.seat_noida = self.pos("Store Manager Noida 064", branch=self.noida, designation=self.role).name
		frappe.db.commit()
		self._openings = []

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in self._openings:
			frappe.db.delete("Version", {"ref_doctype": OPENING, "docname": name})
			frappe.db.delete(OPENING, {"name": name})
		frappe.db.delete("User Permission", {"user": ("like", "%hire064@example.com")})
		frappe.db.commit()
		super().tearDown()

	def hr_u(self, email="hru.hire064@example.com"):
		"""An HR User: writes Job Opening and Employee, may not place people.

		ERPNext ties a user linked to an Employee to that one record with a
		User Permission. A real HR User creating employees has none, so the
		test person does not either."""
		self.hr_user(email)
		frappe.db.delete("User Permission", {"user": email, "allow": "Employee"})
		frappe.db.commit()
		return email

	def editor(self, email="editor.hire064@example.com", branch=None):
		"""A Positions editor tied to a branch, who can also edit openings."""
		self.hr_user(email, branch=branch)
		user = frappe.get_doc("User", email)
		user.flags.ignore_permissions = True
		user.add_roles(EDITOR)
		frappe.db.commit()
		return email

	def opening(self, seat=None, vacancies=1, **kw):
		frappe.set_user("Administrator")
		doc = frappe.get_doc({"doctype": OPENING, "job_title": kw.pop("title", "Store Manager 064"),
		                      "designation": self.role, "company": kw.pop("company", frappe.db.get_value(
		                          register.POSITION, self.seat_delhi, "company")),
		                      "status": "Open", "vacancies": vacancies, **kw})
		doc.flags.ignore_permissions = True
		doc.insert()
		if seat:
			frappe.db.set_value(OPENING, doc.name, register.POSITION_LINK, seat)
		self._openings.append(doc.name)
		frappe.db.commit()
		return doc.name


class TestTheSeatLinkIsGuarded(HiringCase):
	"""SEC-8: only somebody who may place people in a seat may point an
	opening at it - by any door."""

	def test_the_field_is_editable_on_the_desk_with_the_new_description(self):
		df = frappe.get_meta(OPENING).get_field(register.POSITION_LINK)
		self.assertFalse(df.read_only)
		self.assertIn("Only someone who may place people", df.description)

	def test_an_hr_user_cannot_set_it_through_the_api(self):
		name = self.opening()
		frappe.set_user(self.hr_u())
		with patch("hrms.alvoraa_hr_core.access.log_refusal") as logged:
			with self.assertRaises(frappe.PermissionError):
				frappe.client.set_value(OPENING, name, register.POSITION_LINK, self.seat_delhi)
		self.assertEqual(logged.call_args[0][0], "SEC-8")
		self.assertFalse(frappe.db.get_value(OPENING, name, register.POSITION_LINK))

	def test_an_hr_user_cannot_set_it_by_saving_the_form(self):
		name = self.opening()
		frappe.set_user(self.hr_u("hru2.hire064@example.com"))
		doc = frappe.get_doc(OPENING, name)
		doc.set(register.POSITION_LINK, self.seat_delhi)
		with self.assertRaises(frappe.PermissionError):
			doc.save()

	def test_an_editor_may_link_a_seat_in_their_branch(self):
		name = self.opening()
		frappe.set_user(self.editor(branch=self.delhi))
		frappe.client.set_value(OPENING, name, register.POSITION_LINK, self.seat_delhi)
		self.assertEqual(frappe.db.get_value(OPENING, name, register.POSITION_LINK), self.seat_delhi)

	def test_an_editor_may_not_link_a_seat_in_another_branch(self):
		name = self.opening()
		frappe.set_user(self.editor("editor2.hire064@example.com", branch=self.delhi))
		with self.assertRaises(frappe.PermissionError):
			frappe.client.set_value(OPENING, name, register.POSITION_LINK, self.seat_noida)

	def test_a_seat_of_another_company_is_refused(self):
		from alvoraa_portal.tests.test_positions_064 import _second_company

		second = _second_company()
		frappe.set_user("Administrator")
		far = self.pos("Far Seat 064", company=second).name
		name = self.opening()
		frappe.set_user(self.editor("editor3.hire064@example.com"))
		with self.assertRaises(frappe.PermissionError):
			frappe.client.set_value(OPENING, name, register.POSITION_LINK, far)

	def test_an_hr_user_may_still_close_a_linked_opening(self):
		name = self.opening(seat=self.seat_delhi)
		frappe.set_user(self.hr_u("hru3.hire064@example.com"))
		frappe.client.set_value(OPENING, name, "status", "Closed")
		self.assertEqual(frappe.db.get_value(OPENING, name, "status"), "Closed")

	def test_advertise_it_still_makes_a_linked_opening(self):
		frappe.set_user(self.editor("editor4.hire064@example.com", branch=self.delhi))
		out = register.post_job(self.seat_delhi)
		self._openings.append(out["name"])
		self.assertEqual(frappe.db.get_value(OPENING, out["name"], register.POSITION_LINK), self.seat_delhi)

	def test_who_linked_it_is_recorded(self):
		"""PRIV-3: a Version row names the user and the old and new seat."""
		name = self.opening()
		user = self.editor("editor5.hire064@example.com", branch=self.delhi)
		frappe.set_user(user)
		doc = frappe.get_doc(OPENING, name)
		doc.set(register.POSITION_LINK, self.seat_delhi)
		# Frappe skips Versions under test unless asked; a real save keeps one.
		doc.save(ignore_version=False)
		frappe.set_user("Administrator")
		versions = frappe.get_all("Version", filters={"ref_doctype": OPENING, "docname": name},
		                          fields=["owner", "data"])
		self.assertTrue(any(v.owner == user and self.seat_delhi in v.data for v in versions))


def _messages():
	"""What the person who saved was shown, as plain text."""
	import json

	out = []
	for m in frappe.local.message_log or []:
		if isinstance(m, str):
			m = json.loads(m)
		out.append(str(m.get("message", "")))
	return out


class TestAHireIsPlacedInTheirSeat(HiringCase):
	"""SEC-6, SEC-7, SEC-9, SEC-10: the hook, run as the HR User who saves
	the Employee - who may not place anybody by hand."""

	JOINS = "2030-11-02"

	def setUp(self):
		super().setUp()
		self.jo = self.opening(seat=self.seat_delhi, vacancies=2)
		self.hru = self.hr_u("hru.place.hire064@example.com")
		self._applicants = []

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.delete(ASSIGNMENT, {"employee": ("in", self._people or [""])})
		for e in self._people:
			frappe.db.set_value("Employee", e, "job_applicant", None)
		for a in self._applicants:
			frappe.db.delete("Job Applicant", {"name": a})
		frappe.db.delete("Custom DocPerm", {"parent": OPENING})
		frappe.clear_cache(doctype=OPENING)
		frappe.db.commit()
		super().tearDown()

	def applicant(self, opening=None, tag="a"):
		frappe.set_user("Administrator")
		doc = frappe.get_doc({"doctype": "Job Applicant", "applicant_name": "Applicant " + tag,
		                      "email_id": f"applicant.{tag}.{frappe.generate_hash(length=6)}@example.com",
		                      "job_title": opening or self.jo, "status": "Open"}).insert(ignore_permissions=True)
		self._applicants.append(doc.name)
		frappe.db.commit()
		return doc.name

	def hire(self, applicant=None, joins=None, status="Active", name="Ramesh"):
		"""Save an Employee as the HR User, the way "Create Employee" does."""
		company = frappe.db.get_value(register.POSITION, self.seat_delhi, "company")
		frappe.set_user(self.hru)
		frappe.local.message_log = []
		doc = frappe.get_doc({"doctype": "Employee", "first_name": name, "company": company,
		                      "date_of_birth": "1990-01-01", "date_of_joining": joins or self.JOINS,
		                      "gender": frappe.db.get_value("Gender", {}, "name"), "status": status,
		                      "job_applicant": applicant}).insert()
		self._people.append(doc.name)
		frappe.set_user("Administrator")
		return doc

	def placed(self, employee):
		return frappe.get_all(ASSIGNMENT, filters={"employee": employee},
		                      fields=["position", "weight", "assignment_type", "from_date",
		                              "delegate_authority", "covering_for", "owner", "reason"])

	def occupy(self, seat, from_date="2026-01-01", to_date=None):
		other = self.person("Occupant064")
		self.assign(other, seat, from_date=from_date, to_date=to_date)
		frappe.db.commit()
		return other

	def test_a_hire_is_placed_from_their_joining_date(self):
		ja = self.applicant()
		emp = self.hire(ja)
		rows = self.placed(emp.name)
		self.assertEqual(len(rows), 1)
		a = rows[0]
		self.assertEqual((a.position, a.weight, a.assignment_type, str(a.from_date), a.delegate_authority),
		                 (self.seat_delhi, 100, "Permanent", self.JOINS, 0))
		self.assertFalse(a.covering_for)
		self.assertEqual(a.owner, self.hru)
		self.assertEqual(a.reason, f"{register.PLACED} {self.jo}")
		# No name, and not the applicant either: Frappe HR names a Job
		# Applicant by its email address.
		self.assertNotIn("Ramesh", a.reason)
		self.assertNotIn(ja, a.reason)
		self.assertTrue(any("is now in the seat Store Manager 064" in m and "2 Nov 2030" in m
		                    for m in _messages()), _messages())

	def test_the_placement_changes_no_approver_or_manager(self):
		"""SEC-9: what HR saved on the Employee is what stays."""
		emp = self.hire(self.applicant())
		saved = frappe.db.get_value("Employee", emp.name,
		                            ["reports_to", "leave_approver", "expense_approver"], as_dict=True)
		self.assertEqual(dict(saved), {"reports_to": None, "leave_approver": None, "expense_approver": None})

	def test_nobody_is_placed_without_an_applicant_or_when_not_active(self):
		self.assertFalse(self.placed(self.hire(None, name="NoApplicant").name))
		self.assertFalse(self.placed(self.hire(self.applicant(tag="i"), status="Inactive", name="Inactive").name))

	def test_an_opening_with_no_seat_places_nobody_and_says_nothing(self):
		plain = self.opening(title="Unlinked 064")
		emp = self.hire(self.applicant(opening=plain, tag="u"))
		self.assertFalse(self.placed(emp.name))
		self.assertFalse(any("seat" in m for m in _messages()))

	def test_a_second_employee_from_the_same_applicant_is_not_placed(self):
		ja = self.applicant()
		self.hire(ja, name="First")
		second = self.hire(ja, name="Second")
		self.assertFalse(self.placed(second.name))
		self.assertTrue(any("Another employee was already created from this applicant" in m for m in _messages()))

	def test_a_closed_seat_is_not_filled(self):
		frappe.db.set_value(register.POSITION, self.seat_delhi, "status", "Closed")
		emp = self.hire(self.applicant())
		self.assertFalse(self.placed(emp.name))
		self.assertTrue(any("that seat is closed" in m for m in _messages()))

	def test_a_seat_of_another_company_is_not_filled(self):
		from alvoraa_portal.tests.test_positions_064 import _second_company

		far = self.pos("Far Seat 064", company=_second_company()).name
		frappe.db.set_value(OPENING, self.jo, register.POSITION_LINK, far)
		emp = self.hire(self.applicant())
		self.assertFalse(self.placed(emp.name))
		self.assertTrue(any("belongs to another company" in m for m in _messages()))

	def test_a_seat_full_today_is_not_filled(self):
		self.occupy(self.seat_delhi)
		emp = self.hire(self.applicant())
		self.assertFalse(self.placed(emp.name))
		self.assertTrue(any("but that seat is full. Put" in m for m in _messages()), _messages())

	def test_a_seat_free_today_but_full_on_the_joining_date_is_not_filled(self):
		self.occupy(self.seat_delhi, from_date="2030-10-01")
		emp = self.hire(self.applicant())
		self.assertFalse(self.placed(emp.name))

	def test_a_seat_that_frees_before_the_joining_date_is_filled(self):
		self.occupy(self.seat_delhi, to_date="2030-10-31")
		emp = self.hire(self.applicant())
		self.assertEqual(len(self.placed(emp.name)), 1)

	def test_full_until_a_known_date_says_until_when(self):
		self.occupy(self.seat_delhi, to_date="2030-12-31")
		self.hire(self.applicant())
		self.assertTrue(any("but that seat is full until 31 Dec" in m for m in _messages()), _messages())

	def test_editing_an_existing_employee_never_places_anybody(self):
		emp = self.hire(None, name="Existing")
		ja = self.applicant(tag="e")
		frappe.set_user(self.hru)
		doc = frappe.get_doc("Employee", emp.name)
		doc.job_applicant = ja
		doc.save()
		frappe.set_user("Administrator")
		self.assertFalse(self.placed(emp.name))

	def test_a_refusal_inside_the_write_leaves_nothing_and_no_red_message(self):
		"""SEC-7 / AC-68: the assignment's own over-fill rule refuses inside the
		savepoint. The Employee is saved; nothing half-written remains; the
		refusal's text never reaches the save; the Error Log names ids only."""
		from hrms.alvoraa_org_structure.doctype.alvoraa_position.alvoraa_position import AlvoraaPosition

		ja = self.applicant()
		frappe.db.delete("Error Log", {"method": "Hire not placed in a seat"})
		frappe.db.commit()
		with patch.object(AlvoraaPosition, "filled_weight", return_value=99):
			emp = self.hire(ja)
		self.assertTrue(frappe.db.exists("Employee", emp.name))
		self.assertFalse(self.placed(emp.name))
		# Nothing the refusal itself said - its title or its text - reached the save.
		raw = [m if isinstance(m, dict) else __import__("json").loads(m) for m in frappe.local.message_log or []]
		self.assertFalse([m for m in raw if m.get("raise_exception") or "over-filled" in str(m.get("title"))
		                  or "times over" in str(m.get("message"))], raw)
		self.assertTrue(any("is saved, but could not be put in" in m for m in _messages()))
		logs = frappe.get_all("Error Log", filters={"method": "Hire not placed in a seat"}, pluck="error")
		self.assertTrue(logs and emp.name in logs[0] and "Ramesh" not in logs[0], logs)

	def test_the_opening_closes_when_its_places_are_filled(self):
		frappe.db.set_value(register.POSITION, self.seat_delhi, "seats", 2)
		self.hire(self.applicant(tag="one"), name="One")
		self.assertEqual(frappe.db.get_value(OPENING, self.jo, "status"), "Open")
		self.hire(self.applicant(tag="two"), name="Two")
		self.assertEqual(frappe.db.get_value(OPENING, self.jo, "status"), "Closed")
		self.assertTrue(any(f"Job Opening {self.jo} is now closed" in m for m in _messages()), _messages())

	def test_an_opening_with_no_places_set_never_closes(self):
		frappe.db.set_value(OPENING, self.jo, "vacancies", 0)
		self.hire(self.applicant())
		self.assertEqual(frappe.db.get_value(OPENING, self.jo, "status"), "Open")

	def test_a_saver_who_may_not_edit_the_opening_is_told_and_it_stays_open(self):
		frappe.db.set_value(OPENING, self.jo, "vacancies", 1)
		self.rows(("System Manager", "write"), ("HR User", "read"), doctype=OPENING)
		emp = self.hire(self.applicant())
		self.assertTrue(frappe.db.exists("Employee", emp.name))
		self.assertEqual(frappe.db.get_value(OPENING, self.jo, "status"), "Open")
		self.assertTrue(any("but you cannot close it" in m for m in _messages()), _messages())


class TestTheHookBypassesPermissionsOnly(HiringCase):
	"""SEC-7 / AC-69: the hook's one bypass is permissions; it never skips a
	rule (no ignore_validate, ignore_mandatory or ignore_links)."""

	def test_no_rule_is_skipped(self):
		import inspect

		import hrms.alvoraa_org_structure.hiring as hiring

		src = inspect.getsource(hiring)
		for flag in ("ignore_validate", "ignore_mandatory", "ignore_links"):
			self.assertNotIn(flag, src)
