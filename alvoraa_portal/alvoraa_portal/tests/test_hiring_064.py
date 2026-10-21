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
		"""An HR User: writes Job Opening and Employee, may not place people."""
		return self.hr_user(email)

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
