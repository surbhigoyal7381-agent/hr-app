"""Slice 076, Part B: sending a notice. Every SEC and PRIV item this part owns.

The world (every name ends N076): two companies, X and Y. X has branches A and
B. People with logins in each, plus the ones who must never be reached: a
leaver with a working login, a person whose login is switched off, a person
with no login, a person with no branch.

Senders:
  hra   HR User limited to company X, branch A (a store's HR)
  hrx   HR Manager for company X
  hrq   HR Manager WITHOUT Notice Sender
  dir   a director: Notice Sender, no HR role, Company permission X only (Q3=B)
  dirn  a director with no Company permission at all
  sm    System Manager with Notice Sender

The send commits after each chunk, as it does in real life, so every test
starts from a wiped slate (`_wipe`) instead of relying on a rollback.

Pin tests (a merge that drops the feature fails one of these):
  test_job_resolves_scope_as_the_sender
  test_no_id_outside_scope_is_accepted
"""

import json
import threading
from contextlib import contextmanager
from unittest.mock import patch

import frappe
import frappe.client
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_to_date, now_datetime, getdate, nowdate

from alvoraa_portal import announcements as ann
from alvoraa_portal import notices
from alvoraa_portal.tests.utils import ensure_fiscal_years

X, Y = "N076 Co X", "N076 Co Y"
A, B = "N076 Branch A", "N076 Branch B"
DOMAIN = "n076.test"
ROLE = ann.ROLE
E = ["Employee"]
P = {}


def user(first):
	return "%s@%s" % (first.lower(), DOMAIN)


def _insert(d):
	doc = frappe.get_doc(d)
	doc.insert(ignore_permissions=True)
	return doc


def _ensure_user(first, roles, enabled=1):
	email = user(first)
	if not frappe.db.exists("User", email):
		_insert({"doctype": "User", "email": email, "first_name": first, "last_name": "N076",
		         "send_welcome_email": 0, "enabled": 1})
	u = frappe.get_doc("User", email)
	u.enabled = enabled
	u.set("roles", [])
	for r in roles:
		u.append("roles", {"role": r})
	u.save(ignore_permissions=True)
	frappe.db.delete("User Permission", {"user": email})
	return email


def _permit(first, doctype, value):
	_insert({"doctype": "User Permission", "user": user(first), "allow": doctype, "for_value": value,
	         "apply_to_all_doctypes": 1})


def _employee(first, company=X, branch=A, status="Active", roles=E, enabled=1, designation=None):
	name = frappe.db.get_value("Employee", {"first_name": first, "last_name": "N076"}, "name")
	if not name:
		name = _insert({"doctype": "Employee", "first_name": first, "last_name": "N076",
		                "gender": frappe.db.get_value("Gender", {}, "name"), "date_of_birth": "1990-01-01",
		                "date_of_joining": add_days(nowdate(), -300), "company": company,
		                "create_user_permission": 0}).name
	frappe.db.set_value("Employee", name, {"company": company, "branch": branch, "status": "Active",
	                                       "designation": designation, "user_id": None})
	if roles is not None:
		frappe.db.set_value("Employee", name, "user_id", _ensure_user(first, roles, enabled))
		# ERPNext drops Employee from a login saved before an Employee points at
		# it (validate_employee_role); real staff hold it, so give it back.
		u = frappe.get_doc("User", user(first))
		if "Employee" in roles and not any(r.role == "Employee" for r in u.roles):
			u.append("roles", {"role": "Employee"})
			u.save(ignore_permissions=True)
	frappe.db.set_value("Employee", name, "status", status)
	P[first] = name
	return name


def setUpModule():
	ensure_fiscal_years(add_days(nowdate(), -60), nowdate())
	frappe.set_user("Administrator")
	ann.make_role()
	for b in (A, B):
		if not frappe.db.exists("Branch", b):
			_insert({"doctype": "Branch", "branch": b})
	for company, abbr in ((X, "N76X"), (Y, "N76Y")):
		if not frappe.db.exists("Company", company):
			_insert({"doctype": "Company", "company_name": company, "abbr": abbr,
			         "default_currency": "INR", "country": "India"})
	if not frappe.db.exists("Designation", "Store HR N076"):
		_insert({"doctype": "Designation", "designation_name": "Store HR N076"})

	# Recipients
	_employee("Asha")
	_employee("Arun")
	_employee("Bina", branch=B)
	_employee("Yash", company=Y, branch=None)
	_employee("Nobr", branch=None)                          # X, no branch
	_employee("Leah", status="Left")                        # leaver with a working login
	_employee("Dora", enabled=0)                            # login switched off
	_employee("Nolo", roles=None)                           # no login at all
	# Senders
	_employee("Hra", roles=["HR User", "Employee", ROLE], designation="Store HR N076")
	_permit("Hra", "Company", X)
	_permit("Hra", "Branch", A)
	_employee("Hrx", roles=["HR Manager", "Employee", ROLE])
	_permit("Hrx", "Company", X)
	_employee("Hrq", branch=B, roles=["HR Manager", "Employee"])
	_permit("Hrq", "Company", X)
	_employee("Dir", company=Y, branch=None, roles=["Employee", ROLE])
	_permit("Dir", "Company", X)
	_employee("Dirn", company=Y, branch=None, roles=["Employee", ROLE])
	_ensure_user("Sm", ["System Manager", ROLE])
	frappe.db.commit()


def tearDownModule():
	frappe.set_user("Administrator")
	_wipe()
	frappe.db.commit()


def _wipe():
	mine = frappe.get_all("Announcement", filters={"owner": ["like", "%@" + DOMAIN]}, pluck="name")
	if mine:
		frappe.db.delete("Notification Log", {"document_type": "Announcement", "document_name": ["in", mine]})
		frappe.db.delete("Email Queue", {"reference_doctype": "Announcement", "reference_name": ["in", mine]})
		frappe.db.delete("Version", {"ref_doctype": "Announcement", "docname": ["in", mine]})
		frappe.db.delete("Error Log", {"reference_doctype": "Announcement", "reference_name": ["in", mine]})
		frappe.db.delete("Announcement", {"name": ["in", mine]})
	frappe.db.commit()


@contextmanager
def as_user(first):
	frappe.set_user(user(first) if first not in ("Administrator", "Guest") else first)
	try:
		yield
	finally:
		frappe.set_user("Administrator")


def _send(first, message="Notice N076", kind="everyone", later_minutes=None, **kw):
	args = dict(message=message, audience_kind=kind, confirmed=1)
	if later_minutes is not None:
		args.update(when="later", send_at=str(add_to_date(now_datetime(), minutes=later_minutes)))
	args.update(kw)
	with as_user(first):
		return ann.create_notice(**args)


def _due_now(name):
	"""A scheduled notice whose time has come (create refuses a past time)."""
	frappe.db.set_value("Announcement", name, "send_at", add_to_date(now_datetime(), minutes=-1),
	                    update_modified=False)


def _rows(name):
	return set(frappe.get_all("Notification Log", filters={"document_type": "Announcement",
	                                                        "document_name": name}, pluck="for_user"))


def _users(*firsts):
	return {user(f) for f in firsts}


@contextmanager
def email_on():
	"""Email active for the tenant: not muted, and a mail server to send through."""
	with patch.dict(frappe.local.conf, {"mute_emails": 0, "mail_server": "smtp.n076.test"}), \
	     patch.dict(frappe.local.flags, {"mute_emails": False}):
		yield


class Case(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		_wipe()

	def tearDown(self):
		frappe.set_user("Administrator")
		_wipe()


# ── US-2 · scope ─────────────────────────────────────────────────────────────

class TestScope(Case):
	def test_job_resolves_scope_as_the_sender(self):
		"""AC-23 (SEC-4): the job runs as Administrator, who would reach everybody.
		The rows must be branch A's, because the SENDER is branch A's HR."""
		name = _send("Hra", later_minutes=30)["name"]
		_due_now(name)
		self.assertEqual(frappe.session.user, "Administrator")
		ann.send_one(name)
		self.assertEqual(_rows(name), _users("Asha", "Arun", "Hrx"))
		self.assertEqual(frappe.db.get_value("Announcement", name, "status"), "Sent")

	def test_no_id_outside_scope_is_accepted(self):
		"""AC-8 and AC-9 (SEC-3): the dict(..., name=X) trap. A sender with no
		companies picks one valid id; branch A's HR adds one branch B id."""
		with self.assertRaises(frappe.PermissionError):
			_send("Dirn", kind="people", people=json.dumps([P["Asha"]]))
		with self.assertRaises(frappe.PermissionError) as e:
			_send("Hra", kind="people", people=json.dumps([P["Asha"], P["Bina"]]))
		self.assertIn("1 of the people", str(e.exception))
		self.assertNotIn("Bina", str(e.exception))
		self.assertFalse(frappe.get_all("Announcement", filters={"owner": ["like", "%@" + DOMAIN]}))

	def test_another_branch_or_company_is_refused(self):
		"""AC-5, AC-6 (SEC-2)."""
		with self.assertRaises(frappe.PermissionError):
			_send("Hra", kind="branch", branch=B)
		with self.assertRaises(frappe.PermissionError):
			_send("Hrx", kind="company", company=Y)
		self.assertFalse(frappe.get_all("Announcement", filters={"owner": ["like", "%@" + DOMAIN]}))

	def test_everyone_is_active_people_with_a_login_in_the_branch(self):
		"""AC-7, PRIV-2: no leaver, no switched-off login, no person without a
		login, nobody with an empty branch, not the sender."""
		with as_user("Hra"):
			r = ann.notice_reach()
		self.assertEqual(r["everyone"]["n"], 3)          # Asha, Arun, Hrx
		self.assertEqual([t["value"] for t in r["targets"]], [A])
		self.assertNotIn(Y, json.dumps(r))

	def test_a_leaver_a_switched_off_login_or_no_login_is_refused_by_id(self):
		"""AC-10."""
		for first in ("Leah", "Dora", "Nolo"):
			with self.assertRaises(frappe.PermissionError, msg=first):
				_send("Hrx", kind="people", people=json.dumps([P[first]]))

	def test_a_director_reaches_only_their_company_permissions(self):
		"""AC-11 (Q3=B): Company permission X; their own company is Y."""
		with as_user("Dir"):
			r = ann.notice_reach()
		self.assertEqual(r["everyone"]["n"], 7)   # Asha Arun Bina Nobr Hra Hrx Hrq, all X
		res = _send("Dir", kind="everyone", message="Director N076")
		self.assertNotIn(user("Yash"), _rows(res["name"]))
		with self.assertRaises(frappe.PermissionError):
			_send("Dir", kind="people", people=json.dumps([P["Yash"]]), message="Director 2 N076")

	def test_a_director_with_no_company_permission_reaches_nobody(self):
		"""AC-12: no fallback to their own company."""
		with as_user("Dirn"):
			r = ann.notice_reach()
		self.assertEqual((r["everyone"]["n"], r["targets"]), (0, []))
		with self.assertRaises(frappe.ValidationError) as e:
			_send("Dirn")
		self.assertIn("No one is in your scope", str(e.exception))

	def test_a_system_manager_reaches_every_company(self):
		"""AC-13 (documented)."""
		with as_user("Sm"):
			r = ann.notice_reach()
		labels = [t["value"] for t in r["targets"] if t["kind"] == "company"]
		self.assertIn(X, labels)
		self.assertIn(Y, labels)

	def test_the_scope_helper_never_returns_an_empty_condition(self):
		from hrms.alvoraa_hr_core.access import notice_audience_conditions
		for first in ("Hra", "Hrx", "Dir", "Dirn", "Asha"):
			self.assertTrue(notice_audience_conditions(user(first)), first)
		self.assertEqual(notice_audience_conditions(user("Dirn")), [["name", "in", []]])


# ── US-1, US-3 · who may send, and the limits ────────────────────────────────

class TestWhoMaySend(Case):
	def test_without_the_role_every_endpoint_refuses(self):
		"""AC-14 (SEC-1): Guest, a plain employee, an HR Manager without the role."""
		name = _send("Hra", later_minutes=30)["name"]
		for first in ("Guest", "Asha", "Hrq"):
			with as_user(first):
				for call in (lambda: ann.create_notice(message="x", audience_kind="everyone"),
				             ann.notice_reach, lambda: ann.search_notice_people("A"),
				             lambda: ann.cancel_notice(name), ann.my_sent_notices):
					with self.assertRaises(frappe.PermissionError, msg=first):
						call()
		self.assertEqual(frappe.db.count("Announcement", {"owner": ["like", "%@" + DOMAIN]}), 1)

	def test_a_rest_insert_or_edit_does_not_go_round_the_checks(self):
		"""The REST door would skip scope and limits; the record refuses it."""
		with as_user("Hra"):
			with self.assertRaises(frappe.PermissionError):
				frappe.client.insert({"doctype": "Announcement", "message": "x", "status": "Scheduled",
				                      "audience_kind": "Everyone in my scope", "send_at": str(now_datetime())})
		name = _send("Hra", later_minutes=30, kind="branch", branch=A)["name"]
		with as_user("Hra"):
			doc = frappe.get_doc("Announcement", name)
			doc.audience_kind, doc.audience_branch = "Branch", B
			with self.assertRaises(frappe.ValidationError):
				doc.save()

	def test_the_role_is_given_once_and_never_again(self):
		"""AC-1, AC-2: the patch on a site without the role gives it to HR Managers;
		on a second run nobody changes, and someone it was taken from stays without."""
		from alvoraa_portal.patches.v1_0 import notice_sender_role
		frappe.get_doc("User", user("Hrq")).remove_roles(ROLE)
		real, first = frappe.db.exists, []

		def as_if_new(dt, *a, **k):
			# Only the patch's own first question, "does the role exist yet?".
			if (dt, a[:1]) == ("Role", (ROLE,)) and not first:
				first.append(1)
				return None
			return real(dt, *a, **k)

		with patch.object(frappe.db, "exists", side_effect=as_if_new):
			notice_sender_role.execute()
		self.assertIn(ROLE, frappe.get_roles(user("Hrq")), "an HR Manager at install time gets it")
		self.assertEqual(frappe.db.get_value("Role", ROLE, "desk_access"), 0)
		frappe.get_doc("User", user("Hrq")).remove_roles(ROLE)
		before = sorted(frappe.get_all("Has Role", filters={"role": ROLE}, pluck="parent"))
		notice_sender_role.execute()
		self.assertNotIn(ROLE, frappe.get_roles(user("Hrq")), "taken away stays taken away")
		self.assertEqual(sorted(frappe.get_all("Has Role", filters={"role": ROLE}, pluck="parent")), before)

	def test_an_hr_manager_cannot_give_the_role(self):
		"""AC-3: only who may edit Users (System Manager) gives it."""
		with as_user("Hrx"):
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("User", user("Asha")).add_roles(ROLE)
		self.assertNotIn(ROLE, frappe.get_roles(user("Asha")))

	def test_the_role_is_in_no_profile_and_no_default(self):
		"""AC-4."""
		self.assertFalse(frappe.get_all("Has Role", filters={"role": ROLE, "parenttype": ["!=", "User"]}))
		self.assertNotEqual(frappe.db.get_single_value("Portal Settings", "default_role"), ROLE)

	def test_a_sender_who_left_is_refused(self):
		"""T12: a leaver whose login still works sends nothing."""
		frappe.db.set_value("Employee", P["Hra"], "status", "Left")
		try:
			with self.assertRaises(frappe.PermissionError):
				_send("Hra")
		finally:
			frappe.db.set_value("Employee", P["Hra"], "status", "Active")


class TestLimits(Case):
	def test_text_is_trimmed_and_capped_at_300(self):
		"""AC-15."""
		for bad in ("", "   ", "x" * 301):
			with self.assertRaises(frappe.ValidationError):
				_send("Hra", message=bad, later_minutes=30)
		ok = _send("Hra", message="  " + "y" * 300 + "  ", later_minutes=30)
		self.assertEqual(len(frappe.db.get_value("Announcement", ok["name"], "message")), 300)

	def test_more_than_25_people_needs_a_confirm(self):
		"""AC-16. Patched to 2 so the fixture's 3 people are 'more'."""
		with patch.object(ann, "CONFIRM_ABOVE", 2):
			with self.assertRaises(frappe.ValidationError):
				_send("Hra", confirmed=0, later_minutes=30)
			self.assertTrue(_send("Hra", confirmed=1, later_minutes=30, message="Two")["name"])
		self.assertTrue(_send("Hra", confirmed=0, later_minutes=30, message="Three")["name"],
		                "3 people is under the real 25: no confirm needed")

	def test_the_sixth_notice_of_the_day_is_refused_and_cancelled_ones_count(self):
		"""AC-17."""
		first = _send("Hra", message="N1", later_minutes=30)["name"]
		with as_user("Hra"):
			ann.cancel_notice(first)
		for i in range(2, 6):
			_send("Hra", message="N%d" % i, later_minutes=30)
		with self.assertRaises(frappe.ValidationError) as e:
			_send("Hra", message="N6", later_minutes=30)
		self.assertIn("limit for one day", str(e.exception))

	def test_two_parallel_fifth_notices_give_one(self):
		"""AC-17: two requests at once, on two database connections, when four
		are already sent. The sender's row lock lets exactly one through."""
		for i in range(1, 5):
			_send("Hra", message="P%d" % i, later_minutes=30)
		frappe.db.commit()
		site, sites_path, results = frappe.local.site, frappe.local.sites_path, []
		gate = threading.Barrier(2)

		def go(text):
			frappe.init(site=site, sites_path=sites_path)
			frappe.connect()
			try:
				frappe.set_user(user("Hra"))
				gate.wait()
				ann.create_notice(message=text, audience_kind="everyone", confirmed=1, when="later",
				                  send_at=str(add_to_date(now_datetime(), minutes=30)))
				frappe.db.commit()
				results.append("ok")
			except Exception as e:
				frappe.db.rollback()
				results.append(type(e).__name__)
			finally:
				frappe.destroy()

		threads = [threading.Thread(target=go, args=(t,)) for t in ("P5a", "P5b")]
		for t in threads:
			t.start()
		for t in threads:
			t.join(60)
		frappe.set_user("Administrator")
		self.assertEqual(sorted(results), ["ValidationError", "ok"], results)
		self.assertEqual(frappe.db.count("Announcement", {"owner": user("Hra")}), 5)

	def test_the_same_text_twice_in_two_minutes_is_one_notice(self):
		"""AC-18 (SEC-7): a double tap, or a retry after a lost answer."""
		a = _send("Hra", message="Same N076")
		b = _send("Hra", message="Same N076")
		self.assertEqual(a["name"], b["name"])
		self.assertEqual(b["repeat"], 1)
		self.assertEqual(len(_rows(a["name"])), 3)
		self.assertEqual(frappe.db.count("Announcement", {"owner": user("Hra")}), 1)

	def test_a_time_that_has_passed_is_refused(self):
		"""AC-19."""
		with self.assertRaises(frappe.ValidationError) as e:
			_send("Hra", later_minutes=-5)
		self.assertIn("has not passed yet", str(e.exception))

	def test_html_is_stored_escaped_and_read_back_as_text(self):
		"""AC-20 (SEC-9) and AC-63's server half."""
		bad = "<img src=x onerror=alert(1)>"
		name = _send("Hra", message=bad)["name"]
		row = frappe.get_all("Notification Log", filters={"document_name": name, "for_user": user("Asha")},
		                     fields=["subject", "email_content", "title", "type"])[0]
		for f in ("subject", "email_content", "title"):
			self.assertTrue(row[f].startswith("&lt;img"), f)
		self.assertEqual(row["type"], "Alert")
		with as_user("Asha"):
			item = notices.notices_feed()["items"][0]
		self.assertEqual(item["text"], bad)   # the page escapes it on the way in

	def test_the_record_answers_who_sent_what_to_whom(self):
		"""AC-21 (PRIV-3): sent, cancelled and held, each with its fields; a
		Version row for the cancel."""
		sent = _send("Hra", message="Sent one")["name"]
		cancelled = _send("Hra", message="Cancelled one", later_minutes=30)["name"]
		with as_user("Hra"):
			ann.cancel_notice(cancelled)
		held = _send("Hra", message="Held one", later_minutes=30)["name"]
		_due_now(held)
		frappe.get_doc("User", user("Hra")).remove_roles(ROLE)
		try:
			ann.send_one(held)
		finally:
			frappe.get_doc("User", user("Hra")).add_roles(ROLE)
		for name, status in ((sent, "Sent"), (cancelled, "Cancelled"), (held, "Not sent")):
			d = frappe.get_doc("Announcement", name)
			self.assertEqual((d.owner, d.status), (user("Hra"), status))
			self.assertTrue(d.creation and d.send_at and d.audience_kind and d.sender_label)
		self.assertEqual(frappe.db.get_value("Announcement", sent, "reached"), 3)
		self.assertTrue(frappe.db.get_value("Announcement", sent, "sent_at"))
		self.assertTrue(frappe.db.get_value("Announcement", held, "status_reason"))
		v = [x for x in frappe.get_all("Version", filters={"ref_doctype": "Announcement", "docname": cancelled},
		                               fields=["owner", "data"]) if "Cancelled" in (x.data or "")]
		self.assertEqual(len(v), 1, "one Version row says who cancelled it, and when")
		self.assertEqual(v[0].owner, user("Hra"))
		self.assertIn("Store HR N076", frappe.db.get_value("Announcement", sent, "sender_label"))

	def test_search_and_reach_return_counts_and_ids_only(self):
		"""AC-22."""
		with as_user("Hrx"):
			found = ann.search_notice_people("N076")
			reach = ann.notice_reach()
		self.assertTrue(found)
		self.assertLessEqual(len(found), 20)
		for f in found:
			self.assertEqual(set(f), {"id", "name"})
		names = {f["name"] for f in found}
		self.assertFalse({"Leah N076", "Dora N076", "Nolo N076", "Yash N076", "Hrx N076"} & names)
		self.assertEqual(set(reach), {"everyone", "targets", "email_active", "sent_today", "per_day",
		                              "confirm_above", "max_chars"})
		self.assertNotIn("@", json.dumps(reach))


# ── US-4, US-5, US-6 · the send ──────────────────────────────────────────────

class TestSend(Case):
	def test_running_twice_gives_one_row_each(self):
		"""AC-24 (SEC-7)."""
		name = _send("Hra", later_minutes=30)["name"]
		_due_now(name)
		ann.send_one(name)
		frappe.db.set_value("Announcement", name, "status", "Scheduled", update_modified=False)
		ann.send_one(name)
		rows = frappe.get_all("Notification Log", filters={"document_name": name}, pluck="for_user")
		self.assertEqual(len(rows), len(set(rows)))
		self.assertEqual(len(rows), 3)

	def test_rows_are_alerts_from_the_sender_and_the_notice_says_sent(self):
		"""AC-25."""
		name = _send("Hra")["name"]
		rows = frappe.get_all("Notification Log", filters={"document_name": name},
		                      fields=["type", "document_type", "from_user", "read"])
		self.assertEqual({(r.type, r.document_type, r.from_user, r.read) for r in rows},
		                 {("Alert", "Announcement", user("Hra"), 0)})
		d = frappe.get_doc("Announcement", name)
		self.assertEqual((d.status, d.reached), ("Sent", len(rows)))
		self.assertTrue(d.sent_at)

	def test_a_leaver_is_skipped_and_a_joiner_is_included_at_send_time(self):
		"""AC-26."""
		name = _send("Hra", later_minutes=30)["name"]
		_due_now(name)
		frappe.db.set_value("Employee", P["Arun"], "status", "Left")
		frappe.db.set_value("Employee", P["Bina"], "branch", A)
		try:
			ann.send_one(name)
		finally:
			frappe.db.set_value("Employee", P["Arun"], "status", "Active")
			frappe.db.set_value("Employee", P["Bina"], "branch", B)
		self.assertEqual(_rows(name), _users("Asha", "Bina", "Hrx"))

	def test_the_sender_is_checked_again_at_send_time(self):
		"""AC-27 (SEC-5): role removed, login off, sender left, no scope."""
		def role_off():
			frappe.get_doc("User", user("Hra")).remove_roles(ROLE)
			return lambda: frappe.get_doc("User", user("Hra")).add_roles(ROLE)

		def login_off():
			frappe.db.set_value("User", user("Hra"), "enabled", 0)
			return lambda: frappe.db.set_value("User", user("Hra"), "enabled", 1)

		def left():
			frappe.db.set_value("Employee", P["Hra"], "status", "Left")
			return lambda: frappe.db.set_value("Employee", P["Hra"], "status", "Active")

		def no_scope():
			frappe.db.delete("User Permission", {"user": user("Hra"), "allow": "Branch"})
			frappe.db.delete("User Permission", {"user": user("Hra"), "allow": "Company"})
			frappe.db.set_value("Employee", P["Hra"], "company", Y)
			frappe.db.set_value("Employee", P["Hra"], "branch", None)
			frappe.clear_cache(user=user("Hra"))

			def back():
				frappe.db.set_value("Employee", P["Hra"], {"company": X, "branch": A})
				_permit("Hra", "Company", X)
				_permit("Hra", "Branch", A)
			return back

		for i, change in enumerate((role_off, login_off, left, no_scope)):
			name = _send("Hra", message="Check %d" % i, later_minutes=30, kind="branch", branch=A)["name"]
			_due_now(name)
			undo = change()
			try:
				ann.send_one(name)
			finally:
				undo()
				frappe.clear_cache(user=user("Hra"))
			d = frappe.get_doc("Announcement", name)
			self.assertEqual(d.status, "Not sent", change.__name__)
			self.assertTrue(d.status_reason, change.__name__)
			self.assertFalse(_rows(name), change.__name__)

	def test_a_person_whose_login_is_gone_is_skipped_quietly(self):
		"""AC-28: the Employee still points at a login that no longer exists."""
		name = _send("Hra", later_minutes=30)["name"]
		_due_now(name)
		frappe.db.set_value("Employee", P["Arun"], "user_id", "gone-arun@" + DOMAIN)
		errors = frappe.db.count("Error Log")
		try:
			ann.send_one(name)
		finally:
			frappe.db.set_value("Employee", P["Arun"], "user_id", user("Arun"))
		self.assertEqual(_rows(name), _users("Asha", "Hrx"))
		self.assertEqual(frappe.db.count("Error Log"), errors)

	def test_rows_are_committed_chunk_by_chunk(self):
		"""AC-29: chunks of 200 (patched to 2 here), a commit after each; a send
		that dies after the first chunk keeps it."""
		name = _send("Hrx", later_minutes=30)["name"]   # 6 people in X
		_due_now(name)
		real, calls = ann._write_rows, []

		def dies_on_second(doc, users):
			calls.append(len(users))
			if len(calls) == 2:
				raise RuntimeError("worker killed")
			real(doc, users)

		with patch.object(ann, "CHUNK", 2), patch.object(ann, "_write_rows", side_effect=dies_on_second):
			with self.assertRaises(RuntimeError):
				ann.send_one(name)
		frappe.db.rollback()
		self.assertEqual(len(_rows(name)), 2, "the first chunk was committed")
		self.assertEqual(frappe.db.get_value("Announcement", name, "status"), "Sending")

	def test_now_to_200_or_fewer_is_sent_before_the_reply(self):
		"""AC-30, first half."""
		res = _send("Hra")
		self.assertEqual((res["status"], res["reached"]), ("Sent", 3))

	def test_now_to_more_than_200_is_queued_on_long(self):
		"""AC-30, second half (200 patched to 2)."""
		with patch.object(ann, "SEND_IN_REQUEST", 2), patch("frappe.enqueue") as q:
			res = _send("Hra")
		self.assertEqual(res["status"], "Scheduled")
		self.assertFalse(res["later"], "Now over 200 is due at once: the page says Sending")
		self.assertFalse(_rows(res["name"]))
		self.assertEqual(q.call_args.kwargs["queue"], "long")
		self.assertEqual(q.call_args.kwargs["name"], res["name"])

	def test_one_tick_hands_out_at_most_two_and_writes_nothing(self):
		"""AC-31 and AC-34: due order, oldest first."""
		names = [_send("Hra", message="Tick %d" % i, later_minutes=30)["name"] for i in range(3)]
		for i, name in enumerate(names):
			frappe.db.set_value("Announcement", name, "send_at", add_to_date(now_datetime(), minutes=-30 + i),
			                    update_modified=False)
		with patch("frappe.enqueue") as q:
			ann.send_due_announcements()
		self.assertEqual([c.kwargs["name"] for c in q.call_args_list], names[:2])
		self.assertTrue(all(c.kwargs["queue"] == "long" for c in q.call_args_list))
		self.assertFalse(frappe.get_all("Notification Log", filters={"document_name": ["in", names]}))

	def test_a_stopped_send_resumes_without_duplicates(self):
		"""AC-32: Sending, untouched for 11 minutes, part written."""
		name = _send("Hrx", later_minutes=30)["name"]
		_due_now(name)
		doc = frappe.get_doc("Announcement", name)
		ann._write_rows(doc, [user("Asha"), user("Arun")])
		frappe.db.set_value("Announcement", name, {"status": "Sending", "reached": 2,
		                                           "modified": add_to_date(now_datetime(), minutes=-11)},
		                    update_modified=False)
		with patch("frappe.enqueue") as q:
			ann.send_due_announcements()
		self.assertIn(name, [c.kwargs["name"] for c in q.call_args_list])
		ann.send_one(name)
		rows = frappe.get_all("Notification Log", filters={"document_name": name}, pluck="for_user")
		self.assertEqual(len(rows), len(set(rows)))
		self.assertEqual(set(rows), _users("Asha", "Arun", "Bina", "Nobr", "Hra", "Hrq"))
		self.assertEqual(frappe.db.get_value("Announcement", name, "status"), "Sent")

	def test_a_sending_notice_that_is_still_moving_is_left_alone(self):
		name = _send("Hra", later_minutes=30)["name"]
		frappe.db.set_value("Announcement", name, "status", "Sending")   # modified = now
		ann.send_one(name)
		self.assertFalse(_rows(name))

	def test_three_stalls_end_in_failed_with_one_clean_error_row(self):
		"""AC-33, SEC-21: the id and counts; no text, no name, no email."""
		name = _send("Hra", message="Secret pay text N076", later_minutes=30)["name"]
		frappe.db.set_value("Announcement", name, {"status": "Sending", "stalled": 3,
		                                           "modified": add_to_date(now_datetime(), minutes=-11)},
		                    update_modified=False)
		ann.send_one(name)
		self.assertEqual(frappe.db.get_value("Announcement", name, "status"), "Failed")
		logs = frappe.get_all("Error Log", filters={"reference_name": name}, fields=["error", "method"])
		self.assertEqual(len(logs), 1)
		text = json.dumps(logs)
		self.assertIn(name, text)
		for bad in ("Secret pay", "@", "Hra"):
			self.assertNotIn(bad, text)

	def test_a_notice_not_sent_says_why_and_reaches_nobody(self):
		"""AC-35."""
		name = _send("Hra", later_minutes=30)["name"]
		_due_now(name)
		frappe.get_doc("User", user("Hra")).remove_roles(ROLE)
		try:
			ann.send_one(name)
		finally:
			frappe.get_doc("User", user("Hra")).add_roles(ROLE)
		with as_user("Hra"):
			row = [r for r in ann.my_sent_notices() if r["name"] == name][0]
		self.assertEqual(row["status"], "Not sent")
		self.assertIn("Notice Sender", row["reason"])
		self.assertFalse(_rows(name))


class TestCancel(Case):
	def test_cancel_leaves_a_version_and_the_job_sends_nothing(self):
		"""AC-36 (SEC-11)."""
		name = _send("Hra", later_minutes=30)["name"]
		with as_user("Hra"):
			self.assertEqual(ann.cancel_notice(name)["status"], "Cancelled")
		self.assertTrue(frappe.db.exists("Version", {"ref_doctype": "Announcement", "docname": name}))
		_due_now(name)
		with patch("frappe.enqueue") as q:
			ann.send_due_announcements()
		self.assertFalse(q.called, "a cancelled notice is not handed out")
		ann.send_one(name)
		self.assertFalse(_rows(name))

	def test_only_the_owner_and_only_while_scheduled(self):
		"""AC-37."""
		name = _send("Hra", later_minutes=30)["name"]
		with as_user("Hrx"):
			with self.assertRaises(frappe.PermissionError):
				ann.cancel_notice(name)
		sent = _send("Hra", message="Gone already")["name"]
		with as_user("Hra"):
			with self.assertRaises(frappe.ValidationError):
				ann.cancel_notice(sent)
		self.assertEqual(frappe.db.get_value("Announcement", name, "status"), "Scheduled")

	def test_cancel_and_send_end_in_one_outcome(self):
		"""AC-38, both orders: the loser sees the winner's status under the lock."""
		a = _send("Hra", message="Race A", later_minutes=30)["name"]
		_due_now(a)
		ann.send_one(a)
		with as_user("Hra"):
			with self.assertRaises(frappe.ValidationError):
				ann.cancel_notice(a)
		b = _send("Hra", message="Race B", later_minutes=30)["name"]
		with as_user("Hra"):
			ann.cancel_notice(b)
		_due_now(b)
		ann.send_one(b)
		self.assertEqual((frappe.db.get_value("Announcement", a, "status"), len(_rows(a))), ("Sent", 3))
		self.assertEqual((frappe.db.get_value("Announcement", b, "status"), len(_rows(b))), ("Cancelled", 0))


# ── US-7 · counts, never names ───────────────────────────────────────────────

class TestNoticesISent(Case):
	KEYS = {"name", "message", "audience_label", "scheduled_for", "status", "reason", "reached", "read",
	        "created"}

	def test_counts_only_with_a_fixed_set_of_keys(self):
		"""AC-39, AC-40, PRIV-4."""
		name = _send("Hra", message="Counted")["name"]
		_send("Hra", message="Later one", later_minutes=30)
		log = frappe.get_all("Notification Log", filters={"document_name": name, "for_user": user("Asha")},
		                     pluck="name")[0]
		frappe.db.set_value("Notification Log", log, "read", 1)
		with as_user("Hra"):
			rows = ann.my_sent_notices()
		self.assertEqual([r["message"] for r in rows], ["Later one", "Counted"], "newest first")
		for r in rows:
			self.assertEqual(set(r), self.KEYS)
		self.assertEqual((rows[1]["reached"], rows[1]["read"]), (3, 1))
		self.assertEqual((rows[0]["status"], rows[0]["reached"]), ("Scheduled", 0))
		self.assertNotIn("@", json.dumps(rows))
		self.assertNotIn("N076 ", json.dumps([r["audience_label"] for r in rows]))

	def test_a_recipient_cannot_read_the_notice_record(self):
		"""AC-41 (SEC-10), AC-119."""
		name = _send("Hra")["name"]
		with as_user("Asha"):
			try:
				self.assertEqual(frappe.get_list("Announcement"), [])
			except frappe.PermissionError:
				pass
			with self.assertRaises(frappe.PermissionError):
				frappe.client.get("Announcement", name)

	def test_a_sent_notice_cannot_be_changed_and_only_a_system_manager_deletes(self):
		"""AC-42."""
		name = _send("Hra")["name"]
		with as_user("Hra"):
			doc = frappe.get_doc("Announcement", name)
			doc.message = "Changed"
			with self.assertRaises(frappe.ValidationError):
				doc.save()
			with self.assertRaises(frappe.PermissionError):
				frappe.delete_doc("Announcement", name)
		with as_user("Sm"):
			frappe.delete_doc("Announcement", name)
		self.assertFalse(frappe.db.exists("Announcement", name))

	def test_a_sender_sees_only_their_own(self):
		"""AC-43."""
		_send("Hra", message="Hra's")
		with as_user("Hrx"):
			self.assertEqual(ann.my_sent_notices(), [])
			self.assertEqual(frappe.get_list("Announcement"), [])


# ── US-9 · email, only when active ───────────────────────────────────────────

def _queued(since, *firsts):
	emails = [frappe.db.get_value("User", user(f), "email") for f in firsts]
	return frappe.db.count("Email Queue Recipient", {"recipient": ["in", emails], "creation": [">=", since]})


class TestEmail(Case):
	def test_the_tick_is_refused_while_email_is_off(self):
		"""AC-53. A mail server is set, so only the mute makes email inactive."""
		with patch.dict(frappe.local.conf, {"mute_emails": 1, "mail_server": "smtp.n076.test"}):
			with self.assertRaises(frappe.ValidationError):
				_send("Hra", email=1)

	def test_muted_after_scheduling_sends_the_notice_not_the_email(self):
		"""AC-54."""
		since = now_datetime()
		with email_on():
			name = _send("Hra", email=1, later_minutes=30)["name"]
		_due_now(name)
		with patch.dict(frappe.local.conf, {"mute_emails": 1, "mail_server": "smtp.n076.test"}):
			ann.send_one(name)
		self.assertEqual(len(_rows(name)), 3)
		self.assertEqual(_queued(since, "Asha", "Arun", "Hrx"), 0)
		self.assertEqual(frappe.db.get_value("Announcement", name, "email_note"), "email not sent: email is off")

	def test_no_tick_means_no_email_even_for_people_who_get_notification_emails(self):
		"""AC-55 (SEC-17, bad news 2): the rows are Alerts, which never email."""
		since = now_datetime()
		with email_on():
			_send("Hra", email=0)
		self.assertEqual(_queued(since, "Asha", "Arun", "Hrx"), 0)

	def test_ticked_and_active_queues_escaped_mail_and_logs_no_text(self):
		"""AC-56."""
		since = now_datetime()
		with email_on(), patch.object(frappe, "logger") as logger:
			name = _send("Hra", email=1, message="<b>Gate</b> N076")["name"]
		self.assertEqual(_queued(since, "Asha", "Arun", "Hrx"), 3)
		q = frappe.get_all("Email Queue", filters={"reference_name": name}, fields=["message"])
		self.assertTrue(q)
		html_part = q[0].message.split("Content-Type: text/html", 1)[1]
		self.assertIn("&lt;b&gt;Gate", html_part)
		self.assertNotIn("<b>Gate", html_part)
		for c in logger.return_value.info.call_args_list:
			self.assertNotIn("Gate", str(c))
		self.assertEqual(frappe.db.get_value("Announcement", name, "email_note"), "Emailed")


# ── US-10 · what a recipient sees ────────────────────────────────────────────

class TestRecipientFeed(Case):
	def test_pinned_first_with_the_sender_and_the_bell_equals_the_card(self):
		"""AC-57, AC-58 for three people with different data."""
		_send("Hra", message="To branch A")
		_send("Hrx", message="To company X")
		for first, n in (("Asha", 2), ("Bina", 1), ("Yash", 0)):
			with as_user(first):
				card, sheet = notices.notices_feed(), notices.notices_feed(see_all=1)
			self.assertEqual(card["unread"], sheet["unread"], first)
			self.assertEqual(card["unread"], n, first)
			for item in card["items"]:
				self.assertEqual(item["kind"], "announcement")
				self.assertTrue(item["from"])
		with as_user("Asha"):
			d = notices.notices_feed()
		self.assertEqual(d["items"][0]["text"], "To company X", "newest first")
		self.assertIn("Store HR N076", d["items"][1]["from"])
		self.assertEqual(d["can_send"], 0)
		with as_user("Hra"):
			self.assertEqual(notices.notices_feed()["can_send"], 1)

	def test_a_colleague_sees_none_of_my_notices(self):
		"""AC-62 for announcements, AC-119."""
		name = _send("Hra", kind="people", people=json.dumps([P["Asha"]]))["name"]
		with as_user("Arun"):
			self.assertEqual(notices.notices_feed(see_all=1)["items"], [])
		self.assertEqual(_rows(name), _users("Asha"))

	def test_the_holder_list_is_names_for_hr_only(self):
		"""AC-107 (PRIV-8)."""
		with as_user("Hrx"):
			names = ann.notice_sender_holders()
		self.assertIn("Hra N076", names)
		self.assertTrue(all(isinstance(n, str) and "@" not in n for n in names))
		for first in ("Asha", "Hra"):     # a plain employee; an HR User
			with as_user(first):
				with self.assertRaises(frappe.PermissionError):
					ann.notice_sender_holders()
