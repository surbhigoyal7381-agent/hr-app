"""Slice 012 push 1 · a data review record changes only through the morning check or a confirmation.

SEC-13, AC-24, AC-25. Nobody edits one by hand on any path; a Confirmed record
is never changed again; one finding is one record, however often the check runs.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from alvoraa_portal.alvoraa_portal.doctype.alvoraa_data_review_item import (
	alvoraa_data_review_item as dri,
)

BRANCH = "S012 DRI Lakeside"
DAY = "2026-09-08"


def _user(first, *roles):
	email = f"{first.lower()}.s012dri@example.com"
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": first,
		                "send_welcome_email": 0}).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles(*roles)
	return email


class ItemCase(FrappeTestCase):
	_n = 0

	def setUp(self):
		self.caller = frappe.session.user
		frappe.set_user("Administrator")
		self.company = frappe.db.get_value("Company", {}, "name")
		if not frappe.db.exists("Branch", BRANCH):
			frappe.get_doc({"doctype": "Branch", "branch": BRANCH}).insert(ignore_permissions=True)
		self.hrm = _user("PriyaDRI", "HR Manager")

	def tearDown(self):
		frappe.set_user(self.caller)

	def found(self, **counts):
		# A different day per test: the class shares one transaction.
		ItemCase._n += 1
		doc = frappe.get_doc({
			"doctype": dri.DOCTYPE, "item_type": "Doubtful day", "rule": "D5",
			"company": self.company, "alvoraa_branch": BRANCH,
			"check_date": frappe.utils.add_days(DAY, -ItemCase._n),
			"expected_count": 61, "absent_count": 59, "checked_in_count": 1,
			"status": "Open", "first_found_on": now_datetime(), **counts,
		})
		doc.flags.via_rule_check = True
		return doc.insert()

	def confirm(self, doc, user):
		frappe.set_user(user)
		try:
			doc = frappe.get_doc(dri.DOCTYPE, doc.name)
			doc.update({"status": "Confirmed", "confirmation": "Absence was real",
			            "confirmed_by": user, "confirmed_on": now_datetime(),
			            "figure_without": 96.1, "figure_with": 71.4})
			doc.flags.via_confirm = True
			doc.save()
			return doc
		finally:
			frappe.set_user("Administrator")


class TestOneFindingOneRecord(ItemCase):
	def test_the_name_is_the_finding(self):
		doc = self.found()
		self.assertEqual(doc.name, dri.item_name("D5", self.company, BRANCH, doc.check_date))

	def test_a_second_insert_for_the_same_finding_fails_cleanly(self):
		first = self.found()
		again = frappe.get_doc({**first.as_dict(), "name": None, "__islocal": 1, "creation": None})
		again.flags.via_rule_check = True
		with self.assertRaises(frappe.DuplicateEntryError):
			again.insert()

	def test_no_employee_field_and_no_name(self):
		fields = {df.fieldname for df in frappe.get_meta(dri.DOCTYPE).fields}
		self.assertFalse({"employee", "employee_name", "leave_type"} & fields)


class TestNobodyEditsByHand(ItemCase):
	def test_a_person_cannot_create_one(self):
		frappe.set_user(self.hrm)
		doc = frappe.get_doc({"doctype": dri.DOCTYPE, "item_type": "Leave used", "rule": "D6",
		                      "company": self.company, "status": "Open"})
		with self.assertRaises(frappe.PermissionError):
			doc.insert()

	def test_open_counts_cannot_be_changed_in_the_desk(self):
		doc = self.found()
		frappe.set_user(self.hrm)
		mine = frappe.get_doc(dri.DOCTYPE, doc.name)
		mine.absent_count = 1
		with self.assertRaises(frappe.PermissionError):
			mine.save()

	def test_a_confirmed_record_cannot_be_changed_on_any_path(self):
		"""AC-25."""
		doc = self.confirm(self.found(), self.hrm)
		frappe.set_user(self.hrm)
		for change in ({"confirmation": "Figure is right"}, {"confirmed_by": "Administrator"},
		               {"figure_with": 99.0}, {"figure_without": 1.0}, {"absent_count": 3},
		               {"status": "Open"}):
			with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
				frappe.client.set_value(dri.DOCTYPE, doc.name, change)
			rest = frappe.get_doc(dri.DOCTYPE, doc.name).as_dict()
			rest.update(change)
			with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
				frappe.client.save(rest)
		frappe.set_user("Administrator")
		stored = frappe.get_doc(dri.DOCTYPE, doc.name)
		self.assertEqual((stored.status, stored.confirmation, stored.confirmed_by,
		                  stored.figure_with, stored.absent_count),
		                 ("Confirmed", "Absence was real", self.hrm, 71.4, 59))

	def test_the_morning_check_cannot_change_a_confirmed_record(self):
		"""AC-24."""
		doc = self.confirm(self.found(), self.hrm)
		job = frappe.get_doc(dri.DOCTYPE, doc.name)
		job.status = "Cleared"
		job.flags.via_rule_check = True
		with self.assertRaises(frappe.PermissionError):
			job.save()

	def test_a_record_is_confirmed_once(self):
		doc = self.confirm(self.found(), self.hrm)
		with self.assertRaises(frappe.PermissionError):
			self.confirm(doc, self.hrm)

	def test_a_confirmation_must_carry_the_confirming_user(self):
		doc = self.found()
		frappe.set_user(self.hrm)
		mine = frappe.get_doc(dri.DOCTYPE, doc.name)
		mine.update({"status": "Confirmed", "confirmation": "Absence was real",
		             "confirmed_by": "Administrator", "confirmed_on": now_datetime()})
		mine.flags.via_confirm = True
		with self.assertRaises(frappe.PermissionError):
			mine.save()

	def test_the_check_may_clear_and_reopen_an_open_record(self):
		doc = self.found()
		doc.status = "Cleared"
		doc.flags.via_rule_check = True
		doc.save()
		doc.status = "Open"
		doc.absent_count = 60
		doc.save()
		self.assertEqual(frappe.db.get_value(dri.DOCTYPE, doc.name, ["status", "absent_count"]),
		                 ("Open", 60))
