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

# Part B added `kind` and `from` (who sent an announcement) on purpose.
FIELDS = {"name", "kind", "from", "text", "link", "when", "read"}


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
		# Slice 083 (PRIV-1, AC-56d): `capped` is the ONE key this slice adds.
		# Extended, never loosened - the set is still exact.
		self.assertEqual(set(d), {"unread", "capped", "any", "can_send", "items"})
		self.assertFalse(d["capped"], "one notice is not a capped list")
		self.assertEqual((d["items"][0]["kind"], d["items"][0]["from"]), ("alert", None))

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

	def test_only_grooming_notices_and_announcements(self):
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
		# The FLATNESS line is the property gate and it does not move.
		self.assertEqual(small.n, big.n)
		# Slice 083 raised the note from 12 to 14: the true uncapped count
		# costs exactly two more statements - one COUNT for announcements and
		# one uncapped three-field read of unread grooming rows. Both flat in
		# headcount and in row count. A THIRD would mean somebody called
		# `_readable` twice, which is the mistake this number catches.
		self.assertLessEqual(big.n, 14)


def _notice(first, doctype, document_name, subject, read=0):
	"""One Notification Log row, straight in, of any kind."""
	doc = frappe.get_doc({
		"doctype": "Notification Log", "for_user": user(first), "type": "Alert",
		"subject": subject, "document_type": doctype, "document_name": document_name,
	})
	doc.insert(ignore_permissions=True)
	if read:
		frappe.db.set_value("Notification Log", doc.name, "read", 1, update_modified=False)
	return doc.name


class TestTheTrueUnreadCount(Case):
	"""Slice 083, US-8. `unread` used to be counted from a list cut at 100."""

	def test_a_hundred_and_fifty_unread_notices_count_as_a_hundred_and_fifty(self):
		"""AC-24. This fails against the code before slice 083, which said 100."""
		name = _mark("Ravi", "Rahul")
		_more_notices("Rahul", name, 149)
		with as_user("Rahul"):
			d = notices.notices_feed(see_all=1)
		self.assertEqual(d["unread"], 150, "the count is the truth, not the page's 100")
		self.assertEqual(len(d["items"]), notices.READ_CAP, "the list is still capped at 100")
		self.assertTrue(d["capped"], "AC-25: and it says the list was cut")

	def test_an_announcement_and_a_grooming_notice_are_both_counted(self):
		"""The two statements are split by kind (OPS-13); neither half may be lost."""
		_mark("Ravi", "Rahul")
		_notice("Rahul", notices.ANNOUNCEMENT, "ANN-083-1", "Diwali hours")
		_notice("Rahul", notices.ANNOUNCEMENT, "ANN-083-2", "Read the new policy", read=1)
		with as_user("Rahul"):
			d = notices.notices_feed(see_all=1)
		self.assertEqual(d["unread"], 2, "one grooming notice and one unread announcement")
		self.assertEqual(len(d["items"]), 3, "the read announcement is still in the list")

	def test_the_count_ignores_a_notice_whose_mark_the_reader_may_no_longer_read(self):
		"""AC-26. A plain uncapped COUNT(*) passes the other tests and fails this
		one: a manager may read a mark notice only on the mark's own day, so the
		count has to go through the same `_readable` gate the list does."""
		name = _mark("Ravi", "Rahul")
		with as_user("Rahul"):
			grooming.ask(name)
		with as_user("Hari"):
			self.assertEqual(notices.notices_feed()["unread"], 1)
		frappe.db.set_value("Employee", P["Hari"], "status", "Left")
		try:
			with as_user("Hari"):
				d = notices.notices_feed(see_all=1)
			self.assertEqual((d["unread"], d["items"]), (0, []),
			                 "the count fell with the list, no row changed")
		finally:
			frappe.db.set_value("Employee", P["Hari"], "status", "Active")

	def test_the_count_is_the_caller_s_own_and_is_smaller_than_the_site_s(self):
		"""AC-56 / SEC-1. `frappe.db.count` applies NO permission condition, so
		the explicit `for_user` term is the only protection there is. Delete it
		and this fails on the second assertion."""
		_mark("Ravi", "Rahul")
		# Deepa, not Ritika: Ritika is an HR Manager and does not report to Ravi,
		# so grooming refuses the mark. Deepa reports to him and has a login -
		# somebody with no login would need the "told in person" tick as well.
		_mark("Ravi", "Deepa")
		_notice("Olga", notices.ANNOUNCEMENT, "ANN-083-3", "For Olga only")
		site_wide = frappe.db.count(
			"Notification Log",
			{"read": 0, "document_type": ["in", list(notices.NOTICE_DOCTYPES)]})
		with as_user("Rahul"):
			mine = notices.notices_feed(see_all=1)["unread"]
		self.assertEqual(mine, 1, "Rahul's own one notice")
		self.assertLess(mine, site_wide, "and strictly fewer than the whole site holds")

	def test_the_capped_flag_is_false_for_a_short_list(self):
		_mark("Ravi", "Rahul")
		with as_user("Rahul"):
			self.assertFalse(notices.notices_feed(see_all=1)["capped"])

	def test_the_two_doctype_sets_stay_disjoint(self):
		"""AC-20 / OPS-8. The badge adds notices to work owed, so one doctype on
		both sides would be counted twice. This fails if anyone adds a doctype to
		either list."""
		from alvoraa_portal import inbox_api

		inbox_doctypes = {
			"Leave Application", "Expense Claim", "Attendance Request",
			"Shift Request", "Policy Document", "Individual Goal", "KPI",
		}
		self.assertEqual(set(notices.NOTICE_DOCTYPES) & inbox_doctypes, set())
		self.assertEqual(
			set(notices.NOTICE_DOCTYPES),
			{"Grooming Mark", "Grooming Review", "Announcement"},
			"the notice kinds changed - check the badge is not double counting")
		self.assertEqual(len(inbox_api.ROW_KEYS), 7,
		                 "a new inbox part - check it against NOTICE_DOCTYPES by hand")


class TestMarkAllSeen(Case):
	"""Slice 083, US-9 and US-18. Three separate assertions, because a wrong
	write here is silent, unlogged, and nobody would report it. Each one fails
	when its own filter term is removed, so a failure names its cause."""

	def test_assertion_one_every_notice_of_the_three_kinds_is_read(self):
		"""AC-30."""
		name = _mark("Ravi", "Rahul")
		with as_user("Rahul"):
			grooming.ask(name)
		_notice("Rahul", notices.ANNOUNCEMENT, "ANN-083-4", "Diwali hours")
		with as_user("Rahul"):
			self.assertEqual(notices.notices_feed()["unread"], 2)
			notices.mark_all_seen()
			self.assertEqual(notices.notices_feed()["unread"], 0)
		left = frappe.db.count("Notification Log", {
			"for_user": user("Rahul"), "read": 0,
			"document_type": ["in", list(notices.NOTICE_DOCTYPES)]})
		self.assertEqual(left, 0, "not one of the caller's own notices is left unread")

	def test_assertion_two_my_own_desk_notifications_are_untouched(self):
		"""AC-31. Drop the `document_type` term and ONLY this fails. DTC carries
		902 unread `Employee` rows and PPJ's heaviest user 406."""
		_mark("Ravi", "Rahul")
		desk = [_notice("Rahul", "Employee", P["Rahul"], f"Employee row {i}")
		        for i in range(2)]
		with as_user("Rahul"):
			notices.mark_all_seen()
		for row in desk:
			self.assertEqual(frappe.db.get_value("Notification Log", row, "read"), 0,
			                 "a Desk notification this page never showed was cleared")

	def test_assertion_three_a_colleague_s_notices_are_untouched(self):
		"""AC-32. Drop the `for_user` term and ONLY this fails. This is the
		riskiest line in the slice."""
		_mark("Ravi", "Rahul")
		# Deepa, not Ritika: Ritika is an HR Manager who does not report to Ravi,
		# so the mark would be refused before the test reached its point. Deepa
		# reports to him and has a login, so no "told in person" tick is needed.
		theirs = [_notice("Olga", notices.ANNOUNCEMENT, "ANN-083-5", "For Olga"),
		          _notice("Deepa", grooming.MARK, _mark("Ravi", "Deepa"), "For Deepa")]
		with as_user("Rahul"):
			notices.mark_all_seen()
		for row in theirs:
			self.assertEqual(frappe.db.get_value("Notification Log", row, "read"), 0,
			                 "a colleague's notice was cleared")

	def test_it_is_one_statement_for_a_long_backlog(self):
		"""AC-33. One set-based UPDATE for 86 unread rows, not 86."""
		name = _mark("Ravi", "Rahul")
		_more_notices("Rahul", name, 85)
		with as_user("Rahul"):
			with _Spy() as spy:
				notices.mark_all_seen()
		self.assertLessEqual(spy.n, 2, "86 unread notices cost one UPDATE, not 86")

	def test_it_is_safe_to_run_twice(self):
		"""E-14. Two handsets, or a retry. The second call matches nothing."""
		_mark("Ravi", "Rahul")
		with as_user("Rahul"):
			notices.mark_all_seen()
			notices.mark_all_seen()
			self.assertEqual(notices.notices_feed()["unread"], 0)

	def test_it_takes_no_arguments_at_all(self):
		"""AC-56a / SEC-3. There is no doctype, user, field or filter a browser
		can post, because there is no parameter to post it into."""
		import inspect

		_mark("Ravi", "Rahul")
		desk = _notice("Rahul", "Employee", P["Rahul"], "Employee row")
		theirs = _notice("Olga", notices.ANNOUNCEMENT, "ANN-083-6", "For Olga")
		self.assertEqual(list(inspect.signature(notices.mark_all_seen).parameters), [],
		                 "mark_all_seen takes no arguments and must keep taking none")
		with as_user("Rahul"):
			notices.mark_all_seen()
		self.assertEqual(frappe.db.get_value("Notification Log", desk, "read"), 0)
		self.assertEqual(frappe.db.get_value("Notification Log", theirs, "read"), 0)

	def test_the_rate_limit_is_thirty_an_hour_per_user_and_post_only(self):
		"""AC-34's three numbers, pinned so the decorator cannot be quietly
		loosened. The refusal itself is proved by exceeding the limit, which
		needs a real request - that test lives with the other request-shaped
		ones. `methods=["POST"]` matters: Frappe's limiter returns early for
		anything else, so a GET-shaped write would be unlimited while looking
		limited, and the browser therefore sends an arguments object."""
		field, source, limit, window = notices.mark_all_seen.__alvoraa_limit__
		self.assertEqual((source, limit, window), ("user", 30, 3600))
		self.assertEqual(field, "self_user_key", "keyed on the hashed signed-in user")

	def test_guest_is_refused(self):
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				notices.mark_all_seen()
		finally:
			frappe.set_user("Administrator")


class TestTheDoorsToSomebodyElsesNotices(Case):
	"""AC-55 / SEC-5. The ALV-249 canary, as a test rather than a one-off check.

	This is the most important test in slice 083, because the page it guards is a
	durable address holding thirty days of one person's HR messages, on handsets
	shared by 441 logins at DTC.

	`Notification Log` grants role **All** read, report, export, print, email and
	share, so the protection is not the DocType's permissions - it is Frappe's own
	`get_permission_query_conditions` and `has_permission`, which pin `for_user`
	to the session user. Every door below has to land on that, including the ones
	nobody uses from our own screens.

	Rahul holds only `Employee` (`roles=E` in the world's fixture), so this is a
	plain staff login, not an HR one.
	"""

	def setUp(self):
		super().setUp()
		# One row each for three different people, so "only mine" has something
		# to be wrong about.
		self.mine = _notice("Rahul", notices.ANNOUNCEMENT, "ANN-DOORS-1", "Mine")
		self.theirs = _notice("Olga", notices.ANNOUNCEMENT, "ANN-DOORS-2", "Olga's")
		self.alsotheirs = _notice("Ritika", notices.ANNOUNCEMENT, "ANN-DOORS-3", "Ritika's")
		frappe.db.commit()

	def _form(self, **kw):
		"""reportview reads its arguments from form_dict, not from parameters."""
		frappe.local.form_dict = frappe._dict({
			"doctype": "Notification Log",
			"fields": json.dumps(["name", "for_user", "subject"]),
			"limit_page_length": 0,
		}, **kw)

	def test_every_door_returns_only_my_own_rows(self):
		from frappe.desk import reportview
		from frappe.desk.search import search_link

		with as_user("Rahul"):
			mine = user("Rahul")

			# 1. The list API, which is what our own page uses. `get_list`, not
			#    `get_all`: get_all is get_list with the permission check switched
			#    off, so testing it would prove nothing. That is also why notices.py
			#    reads these rows with get_list (lines 84 and 97).
			rows = frappe.get_list("Notification Log", fields=["name", "for_user"],
			                       limit_page_length=0)
			self.assertTrue(rows, "the caller should see their own rows")
			self.assertEqual({r.for_user for r in rows}, {mine}, "another person's row came back")

			# 2. A hostile filter naming somebody else. Frappe ANDs its own
			#    condition on, so this is empty rather than Olga's row.
			self.assertEqual(
				frappe.get_list("Notification Log", filters={"for_user": user("Olga")},
				                fields=["name"], limit_page_length=0), [])

			# 3. reportview.get - the Desk list view's own door.
			self._form()
			got = reportview.get()
			col = got["keys"].index("for_user")
			self.assertEqual({v[col] for v in got["values"]}, {mine})

			# 4. reportview.get_count, which has its own query path.
			self._form()
			self.assertEqual(int(reportview.get_count()), len(rows))

			# 5. The client API, all three readers.
			self.assertEqual(
				{r["for_user"] for r in frappe.client.get_list(
					"Notification Log", fields=json.dumps(["for_user"]), limit_page_length=0)},
				{mine})
			self.assertEqual(int(frappe.client.get_count("Notification Log")), len(rows))
			# Empty, not None: get_value hands back {} when the row is out of reach.
			self.assertFalse(frappe.client.get_value(
				"Notification Log", "subject", {"name": self.theirs}),
				"a colleague's subject came back through get_value")

			# 6. Link search, which is the door a permission gate is most often
			#    forgotten on.
			found = search_link("Notification Log", "", page_length=50) or frappe.response.get("results") or []
			names = {d.get("value") for d in found}
			self.assertNotIn(self.theirs, names)
			self.assertNotIn(self.alsotheirs, names)

	def test_a_colleagues_named_row_is_refused(self):
		with as_user("Rahul"):
			with self.assertRaises(frappe.PermissionError):
				frappe.client.get("Notification Log", self.theirs)

	def test_the_export_door_hands_over_nobody_elses_words(self):
		"""`export` is granted to role All, so this is the door that would hand
		over the actual message text. It goes through the same DatabaseQuery, and
		`DISALLOWED_PARAMS` strips `user` and `ignore_permissions` from the
		request - so asking for somebody else's subject returns only your own."""
		from frappe.desk import reportview

		with as_user("Rahul"):
			self._form(file_format_type="CSV",
			           fields=json.dumps(["name", "for_user", "subject"]))
			reportview.export_query()
			# Which key carries the file has moved between versions, so read every
			# string the response holds rather than pin one name.
			parts = []
			for v in frappe.response.values():
				if isinstance(v, bytes):
					parts.append(v.decode("utf-8", "replace"))
				elif isinstance(v, str):
					parts.append(v)
			body = chr(10).join(parts)
			self.assertIn("Mine", body, "the caller's own notice should be in their export")
			self.assertNotIn("Olga's", body, "a colleague's words left the server")
			self.assertNotIn("Ritika's", body, "a colleague's words left the server")

	def test_the_rows_are_never_read_with_get_all(self):
		"""SEC-1. `frappe.get_all` is `get_list` with the permission check turned
		off, and `frappe.db.count` applies no condition at all. So every read of
		Notification Log in notices.py must be `get_list`, and the one count must
		carry an explicit `for_user`. Delete that term and the badge starts
		reporting the whole site's unread."""
		import inspect

		src = inspect.getsource(notices)
		self.assertNotIn('get_all("Notification Log"', src,
		                 "get_all skips the permission check; use get_list")
		self.assertIn('"Notification Log"', src, "the feed must read the rows itself")
		count_call = src[src.index('frappe.db.count("Notification Log"'):][:400]
		self.assertIn('"for_user"', count_call,
		              "frappe.db.count applies no permission condition of its own")
