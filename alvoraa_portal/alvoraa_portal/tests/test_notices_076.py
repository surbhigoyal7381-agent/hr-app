"""Slice 076, Part A: the one answer to "what notices have I not read?".

Uses the world of test_grooming_066 (the same people, one Notification Log row
per grooming mark), as test_grooming_cap_066 does.

Pin tests:
  test_bell_and_card_share_one_count
  test_a_colleague_cannot_read_or_mark_my_notice
"""

import json

import frappe
from frappe.desk.doctype.notification_log.notification_log import mark_as_read

import alvoraa_portal.grooming as grooming
from alvoraa_portal import notices
from alvoraa_portal.tests import test_grooming_066 as world
from alvoraa_portal.tests.test_grooming_066 import Case, P, _mark, as_user, user

setUpModule = world.setUpModule
tearDownModule = world.tearDownModule

FIELDS = {"name", "text", "link", "when", "read"}


def _more_notices(first, mark_name, n):
	"""n more notices for `first` about a real mark - the shape a busy month gives."""
	for i in range(n):
		frappe.get_doc({
			"doctype": "Notification Log", "for_user": user(first), "type": "Alert",
			"subject": "Extra notice %d" % i, "document_type": grooming.MARK,
			"document_name": mark_name,
		}).insert(ignore_permissions=True)


class _Spy:
	def __enter__(self):
		self.n = 0
		self._real = frappe.db.sql

		def spy(query, *a, **k):
			self.n += 1
			return self._real(query, *a, **k)

		frappe.db.sql = spy
		return self

	def __exit__(self, *exc):
		frappe.db.sql = self._real
		return False


class TestNoticesFeed(Case):
	def test_the_person_sees_their_own_unread_notice_with_a_fixed_set_of_keys(self):
		_mark("Ravi", "Rahul")
		with as_user("Rahul"):
			d = notices.notices_feed()
		self.assertEqual(d["unread"], 1)
		self.assertTrue(d["any"])
		self.assertEqual(len(d["items"]), 1)
		self.assertEqual(set(d["items"][0]), FIELDS)
		self.assertEqual(d["items"][0]["read"], 0)
		self.assertEqual(set(d), {"unread", "any", "items"})

	def test_a_colleague_cannot_read_or_mark_my_notice(self):
		name = _mark("Ravi", "Rahul")
		log = frappe.get_all("Notification Log", filters={
			"for_user": user("Rahul"), "document_name": name}, pluck="name")
		self.assertEqual(len(log), 1)
		with as_user("Olga"):
			d = notices.notices_feed(see_all=1)
			self.assertEqual((d["unread"], d["items"], d["any"]), (0, [], False))
			mark_as_read(log[0])       # Frappe's own call, aimed at somebody else's row
		self.assertEqual(frappe.db.get_value("Notification Log", log[0], "read"), 0,
		                 "somebody else's mark_as_read changed my notice")
		with as_user("Rahul"):
			self.assertEqual(notices.notices_feed()["unread"], 1)
			mark_as_read(log[0])
			d = notices.notices_feed()
			self.assertEqual((d["unread"], d["items"]), (0, []))
			self.assertTrue(d["any"], "an empty card must still know it has had notices")

	def test_guest_is_refused(self):
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				notices.notices_feed()
		finally:
			frappe.set_user("Administrator")

	def test_the_card_is_capped_at_five_and_the_count_is_the_truth(self):
		name = _mark("Ravi", "Rahul")
		_more_notices("Rahul", name, 7)
		with as_user("Rahul"):
			card = notices.notices_feed()
			sheet = notices.notices_feed(see_all=1)
		self.assertEqual(len(card["items"]), notices.CARD_ROWS)
		self.assertEqual(card["unread"], 8)
		self.assertEqual(sheet["unread"], 8)
		self.assertEqual(len(sheet["items"]), 8)

	def test_bell_and_card_share_one_count(self):
		"""The chip and the bell are both `unread` from this one function, whether
		the card (5 rows) or the sheet (everything) asked."""
		name = _mark("Ravi", "Rahul")
		_more_notices("Rahul", name, 3)
		with as_user("Rahul"):
			log = frappe.get_all("Notification Log", filters={"for_user": user("Rahul")},
			                     pluck="name", limit=1)
			mark_as_read(log[0])
			card, sheet = notices.notices_feed(), notices.notices_feed(see_all=1)
		self.assertEqual(card["unread"], sheet["unread"])
		self.assertEqual(sheet["unread"], sum(1 for i in sheet["items"] if not i["read"]))
		self.assertEqual(sheet["unread"], 3)

	def test_the_sheet_lists_unread_first_and_keeps_read_ones_for_thirty_days(self):
		name = _mark("Ravi", "Rahul")
		_more_notices("Rahul", name, 2)
		with as_user("Rahul"):
			log = frappe.get_all("Notification Log", filters={"for_user": user("Rahul")},
			                     pluck="name")
			mark_as_read(log[0])
			self.assertEqual(frappe.db.get_value("Notification Log", log[0], "read"), 1)
			sheet = notices.notices_feed(see_all=1)
		self.assertEqual(sorted(i["read"] for i in sheet["items"]), [0, 0, 1])
		self.assertEqual([i["read"] for i in sheet["items"]], [0, 0, 1], "unread first")
		# A read notice older than 30 days drops out; an unread one never does.
		frappe.db.set_value("Notification Log", log[0], "creation", "2020-01-01 10:00:00",
		                    update_modified=False)
		unread = frappe.get_all("Notification Log", filters={"for_user": user("Rahul"), "read": 0},
		                        pluck="name", limit=1)[0]
		frappe.db.set_value("Notification Log", unread, "creation", "2020-01-01 10:00:00",
		                    update_modified=False)
		with as_user("Rahul"):
			sheet = notices.notices_feed(see_all=1)
		self.assertEqual(len(sheet["items"]), 2, "the read one is gone, the old unread one stays")
		self.assertEqual(sheet["unread"], 2)

	def test_only_grooming_notices_in_part_a(self):
		_mark("Ravi", "Rahul")
		frappe.get_doc({"doctype": "Notification Log", "for_user": user("Rahul"), "type": "Alert",
		                "subject": "Not a notice", "document_type": "Employee",
		                "document_name": P["Rahul"]}).insert(ignore_permissions=True)
		with as_user("Rahul"):
			d = notices.notices_feed(see_all=1)
		self.assertEqual(len(d["items"]), 1)
		self.assertNotIn("Not a notice", json.dumps(d))

	def test_a_notice_is_hidden_when_its_reader_may_no_longer_read_the_mark(self):
		name = _mark("Ravi", "Rahul")
		with as_user("Rahul"):
			grooming.ask(name)
		with as_user("Hari"):
			self.assertEqual(notices.notices_feed()["unread"], 1)
		frappe.db.set_value("Employee", P["Hari"], "status", "Left")
		try:
			with as_user("Hari"):
				d = notices.notices_feed()
				self.assertEqual((d["unread"], d["items"]), (0, []))
		finally:
			frappe.db.set_value("Employee", P["Hari"], "status", "Active")

	def test_the_query_count_does_not_grow_with_the_number_of_notices(self):
		name = _mark("Ravi", "Rahul")
		with as_user("Rahul"):
			notices.notices_feed()          # warm
			with _Spy() as small:
				notices.notices_feed()
		_more_notices("Rahul", name, 40)
		with as_user("Rahul"):
			notices.notices_feed()
			with _Spy() as big:
				notices.notices_feed()
		self.assertEqual(small.n, big.n)
		self.assertLessEqual(big.n, 12)
