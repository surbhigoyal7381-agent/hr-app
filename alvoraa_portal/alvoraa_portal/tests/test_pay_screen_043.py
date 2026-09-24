"""Slice 043, Wave 3: the Pay screen's one call.

Its own company and people (tag `S043P`), for the reasons `fixtures_043`'s
docstring gives.

**The year-to-date figures are deliberately NOT the sum of the slips.** The
fixture stores 100,000 on the newest slip while the two slips add up to 62,000.
Any version of `get_pay` that adds slips up gets 62,000 and this file goes red.
A fixture where the stored figure happened to equal the sum would pass whether
the code read it or summed it, which is the shape of test that proves nothing.

**Payroll rounding is not touched by this slice**, and one test here exists to
keep it visible: 555 of 800 PP Jewellers slips print a net the bank does not
pay, that is an open decision, and a nicer Pay screen must not make the wrong
figure look more authoritative. So the payload carries the exact net AND the
rounded total, and `TestTheRoundingIsNotHidden` fails if either disappears.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import hr_api, pay_api

TAG = "S043P"
COMPANY = "S043P Pay Company"
ABBR = "S43P"

PAYROLL_ON = ("portal", "leaves", "attendance", "expenses", "payroll")
PAYROLL_OFF = ("portal", "leaves", "attendance", "expenses")

# Two slips, and a stored year-to-date that is NOT their sum. See the docstring.
OLDER = {"start": "2026-07-01", "end": "2026-07-31", "net": 30000.0,
         "rounded": 30000.0, "gross": 35000.0}
NEWER = {"start": "2026-08-01", "end": "2026-08-31", "net": 31999.61,
         "rounded": 32000.0, "gross": 37000.0}
STORED_YTD_NET = 100000.0
STORED_YTD_GROSS = 120000.0
SUM_OF_SLIPS = OLDER["net"] + NEWER["net"]


def _features(names):
	frappe.local.conf["features"] = list(names)


def _clear_features():
	frappe.local.conf.pop("features", None)


def _ensure(doctype, name, **values):
	if name and frappe.db.exists(doctype, name):
		return frappe.get_doc(doctype, name)
	doc = frappe.get_doc({"doctype": doctype, **values})
	if name:
		doc.name = name
		doc.set("__newname", name)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_mandatory=True)
	return doc


def _user(local):
	email = "s043p.%s@example.com" % local
	if not frappe.db.exists("User", email):
		doc = frappe.get_doc({"doctype": "User", "email": email,
		                      "first_name": local.title(),
		                      "send_welcome_email": 0,
		                      "roles": [{"role": "Employee"}]})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
	frappe.db.set_value("User", email, "module_profile", None,
	                    update_modified=False)
	frappe.db.delete("Block Module", {"parent": email, "parenttype": "User"})
	frappe.clear_cache(user=email)
	return email


def _employee(first, login, joined="2024-01-01"):
	name = frappe.db.get_value("Employee",
	                           {"first_name": first, "last_name": TAG}, "name")
	doc = frappe.get_doc("Employee", name) if name else frappe.get_doc({
		"doctype": "Employee", "first_name": first, "last_name": TAG,
		"date_of_birth": "1990-01-01",
		"gender": frappe.get_all("Gender", pluck="name", limit=1)[0]})
	doc.company = COMPANY
	doc.date_of_joining = joined
	doc.status = "Active"
	doc.user_id = login
	# The sensitive fields AC-6 is about. They are SET here on purpose, so a
	# payload leaking them has something real to leak.
	doc.cell_number = "9000000042"
	doc.create_user_permission = 0
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	if login:
		frappe.db.delete("User Permission", {"user": login})
		frappe.clear_cache(user=login)
	frappe.db.commit()
	return doc.name


class PayFixture(FrappeTestCase):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = _ensure("Company", COMPANY, company_name=COMPANY,
		                      abbr=ABBR, default_currency="INR",
		                      country="India").name
		cls.rahul_login = _user("rahul")
		cls.asha_login = _user("asha")
		cls.rahul = _employee("Rahul", cls.rahul_login)
		# Asha deliberately has NO Employee record.

		cls.older = cls._slip(OLDER, ytd=None)
		cls.newer = cls._slip(NEWER, ytd=(STORED_YTD_NET, STORED_YTD_GROSS))
		cls.cancelled = cls._slip(
			{"start": "2026-06-01", "end": "2026-06-30", "net": 29000.0,
			 "rounded": 29000.0, "gross": 33000.0}, ytd=None, docstatus=2)
		frappe.db.commit()

	@classmethod
	def _slip(cls, shape, ytd=None, docstatus=1):
		"""One Salary Slip, stored rather than calculated.

		`validate()` on a Salary Slip exists to CALCULATE one, and it needs a
		salary structure, an assignment and a payroll period. Nothing in this
		slice calculates a slip - every screen here reads one payroll already
		made - so the fixture stores the fields the portal returns and skips
		the calculation. Building the real chain would make the fixture the
		thing most likely to break.
		"""
		existing = frappe.db.get_value("Salary Slip", {
			"employee": cls.rahul, "start_date": shape["start"]}, "name")
		if existing:
			return existing
		doc = frappe.get_doc({
			"doctype": "Salary Slip", "employee": cls.rahul,
			"company": COMPANY, "start_date": shape["start"],
			"end_date": shape["end"], "posting_date": shape["end"],
			"currency": "INR", "payroll_frequency": "Monthly"})
		doc.flags.ignore_permissions = True
		doc.flags.ignore_validate = True
		doc.insert(ignore_permissions=True, ignore_mandatory=True)
		for field, value in (("net_pay", shape["net"]),
		                     ("rounded_total", shape["rounded"]),
		                     ("gross_pay", shape["gross"]),
		                     ("total_deduction", shape["gross"] - shape["net"]),
		                     ("total_working_days", 31),
		                     ("payment_days", 31)):
			doc.db_set(field, value, update_modified=False)
		if ytd:
			doc.db_set("year_to_date", ytd[0], update_modified=False)
			doc.db_set("gross_year_to_date", ytd[1], update_modified=False)
		doc.db_set("docstatus", docstatus, update_modified=False)
		return doc.name

	def setUp(self):
		_features(PAYROLL_ON)
		frappe.set_user(self.rahul_login)

	def tearDown(self):
		frappe.set_user("Administrator")
		_clear_features()


class TestWhoMayCallThePayScreen(PayFixture):

	def test_guest_is_refused(self):
		"""And refused with the one sentence, not answered with an empty page.

		This failed the first time it ran. `get_pay` answered a Guest with the
		same "no payslips yet" payload it gives a signed-in person who has no
		Employee record, because both reach `_get_employee() -> None`. The
		request layer would have stopped a real Guest, so nothing was exposed -
		but a soft answer sitting behind a hard door is a door somebody removes
		later.
		"""
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			pay_api.get_pay()

	def test_a_caller_with_no_employee_record_gets_no_slips(self):
		"""Asha has a login and no Employee record.

		Not a refusal: she has no payslips, and "not available" would suggest
		something is being kept from her. The frame does not offer Pay to her
		at all (034 §3), so this is the hand-typed path only.
		"""
		frappe.set_user(self.asha_login)
		payload = pay_api.get_pay()
		self.assertEqual(payload["payslips"], [])
		self.assertIsNone(payload["me"])
		self.assertEqual(payload["note"],
		                 "No payslips have been issued to you yet.")

	def test_a_tenant_without_payroll_is_refused(self):
		"""AC-30. The gate is real, called through the site config, never
		patched - a patched gate makes every entitlement test green while
		proving nothing."""
		_features(PAYROLL_OFF)
		with self.assertRaises(frappe.PermissionError):
			pay_api.get_pay()

	def test_the_refusal_is_the_same_sentence_as_a_missing_slip(self):
		"""AC-31. A refusal that varies tells the caller what the tenant
		bought, or what exists."""
		def message(fn):
			try:
				fn()
			except frappe.PermissionError as exc:
				return str(exc)
			raise AssertionError("nothing was refused")

		_features(PAYROLL_OFF)
		no_payroll = message(pay_api.get_pay)
		_features(PAYROLL_ON)
		no_such_slip = message(lambda: hr_api.get_payslip("NOT-A-SLIP"))
		cancelled = message(lambda: hr_api.get_payslip(self.cancelled))
		self.assertEqual(no_payroll, no_such_slip)
		self.assertEqual(no_payroll, cancelled)
		self.assertIn("not available", no_payroll)


class TestTheShapeOfThePayload(PayFixture):

	def test_the_keys_are_the_fixed_list(self):
		self.assertEqual(sorted(pay_api.get_pay().keys()),
		                 sorted(pay_api.PAY_KEYS))

	def test_the_me_block_is_the_six(self):
		"""AC-6. Not the whole Employee row - the screen people attach to a
		support ticket and send to a bank."""
		me = pay_api.get_pay()["me"]
		self.assertEqual(sorted(me.keys()), sorted(hr_api.ME_FIELDS))

	def test_the_phone_number_is_nowhere_in_the_payload(self):
		self.assertNotIn("9000000042", frappe.as_json(pay_api.get_pay()))

	def test_the_fixture_really_has_a_phone_number_set(self):
		"""The guard that stops the check above passing on an empty field."""
		self.assertEqual(
			frappe.db.get_value("Employee", self.rahul, "cell_number"),
			"9000000042")

	def test_the_newest_slip_is_returned_in_full(self):
		latest = pay_api.get_pay()["latest"]
		self.assertEqual(latest["name"], self.newer)
		for key in ("earnings", "deductions", "net_pay", "rounded_total",
		            "start_date", "end_date", "currency"):
			self.assertIn(key, latest)


class TestTheYearToDateIsReadNeverSummed(PayFixture):
	"""AC-25."""

	def test_it_is_the_stored_figure(self):
		ytd = pay_api.get_pay()["year_to_date"]
		self.assertEqual(ytd["net"], STORED_YTD_NET)
		self.assertEqual(ytd["gross"], STORED_YTD_GROSS)

	def test_it_is_not_the_sum_of_the_slips(self):
		"""The assertion that makes the one above mean something."""
		ytd = pay_api.get_pay()["year_to_date"]
		self.assertNotEqual(ytd["net"], SUM_OF_SLIPS)

	def test_the_two_really_do_differ(self):
		"""Without this, the test above could pass because both are zero."""
		self.assertNotEqual(STORED_YTD_NET, SUM_OF_SLIPS)
		self.assertGreater(SUM_OF_SLIPS, 0)

	def test_it_names_the_slip_it_came_off(self):
		"""So somebody who thinks the figure is wrong can point at a document
		rather than at the screen."""
		ytd = pay_api.get_pay()["year_to_date"]
		self.assertEqual(ytd["from_slip"], self.newer)
		self.assertEqual(str(ytd["up_to"]), NEWER["end"])

	def test_a_mid_year_joiner_whose_first_slip_is_not_april(self):
		"""AC-25's second half. Every slip on this fixture starts in June or
		later, so a figure derived from "April onwards" would be wrong and a
		figure READ off the slip is right whatever month it starts in."""
		ytd = pay_api.get_pay()["year_to_date"]
		self.assertEqual(ytd["net"], STORED_YTD_NET)
		self.assertEqual(str(pay_api.get_pay()["payslips"][-1]["start_date"]),
		                 OLDER["start"])


class TestTakeHome(PayFixture):
	"""§20 D-2: the ROUNDED amount, because that is what the bank paid."""

	def test_take_home_is_the_rounded_total(self):
		payload = pay_api.get_pay()
		self.assertEqual(payload["take_home"], NEWER["rounded"])

	def test_the_exact_net_is_still_there_to_be_seen(self):
		payload = pay_api.get_pay()
		self.assertEqual(payload["latest"]["net_pay"], NEWER["net"])

	def test_the_constant_says_which_field_it_is(self):
		"""Wave 2's "your payslip is ready" row has to make the same choice or
		the two screens disagree by a rupee. The choice is a named constant so
		there is one place to read it from."""
		self.assertEqual(pay_api.TAKE_HOME_FIELD, "rounded_total")


class TestTheRoundingIsNotHidden(PayFixture):
	"""555 of 800 PP Jewellers slips print a net the bank does not pay.

	That is an open decision and this slice does not touch it. What this slice
	must not do is make the wrong figure look more authoritative, so both
	figures stay on the payload and the difference stays visible.
	"""

	def test_both_figures_reach_the_screen(self):
		payload = pay_api.get_pay()
		self.assertEqual(payload["take_home"], NEWER["rounded"])
		self.assertEqual(payload["latest"]["net_pay"], NEWER["net"])

	def test_the_fixture_has_a_slip_where_they_differ(self):
		"""The guard: on a slip where net and rounded are equal, the test
		above passes whatever the code does."""
		self.assertNotEqual(NEWER["net"], NEWER["rounded"])

	def test_nothing_rounds_the_exact_net_on_the_way_out(self):
		payload = pay_api.get_pay()
		self.assertNotEqual(payload["latest"]["net_pay"],
		                    payload["latest"]["rounded_total"])


class TestNoComparisonWithLastMonth(PayFixture):
	"""§20 D-4. August was ₹11,851.61 above July because of a one-off
	incentive, and there is no field anywhere that says a component was
	one-off. "+₹11,851.61 more than July" reads as a raise."""

	def test_there_is_no_comparison_key(self):
		payload = pay_api.get_pay()
		for key in payload:
			self.assertNotIn("compar", key.lower())
			self.assertNotIn("previous", key.lower())
			self.assertNotIn("last_month", key.lower())

	def test_the_fixture_would_have_produced_one(self):
		"""Two slips with different nets - so a comparison was available to
		build and the absence above is a decision, not a missing fixture."""
		self.assertEqual(len(pay_api.get_pay()["payslips"]), 2)
		self.assertNotEqual(OLDER["net"], NEWER["net"])


class TestCancelledAndAmendedSlips(PayFixture):
	"""AC-53."""

	def test_a_cancelled_slip_is_not_listed(self):
		names = [s["name"] for s in pay_api.get_pay()["payslips"]]
		self.assertNotIn(self.cancelled, names)

	def test_a_cancelled_slip_cannot_be_opened(self):
		with self.assertRaises(frappe.PermissionError):
			hr_api.get_payslip(self.cancelled)

	def test_the_cancelled_slip_really_exists(self):
		"""The guard that proves the two above are not passing because the
		fixture never made it."""
		self.assertEqual(
			frappe.db.get_value("Salary Slip", self.cancelled, "docstatus"), 2)

	def test_the_submitted_slips_are_both_listed(self):
		names = [s["name"] for s in pay_api.get_pay()["payslips"]]
		self.assertEqual(sorted(names), sorted([self.older, self.newer]))


class TestNothingOnThisPathWrites(PayFixture):
	"""AC-61. Showing a person their own pay must not create a record about
	them - no read log, no "seen" flag, nothing inferred from opening it."""

	def test_a_full_call_writes_nothing(self):
		writes = []
		real = frappe.db.sql

		def spy(query, *args, **kwargs):
			if str(query).lstrip().lower().startswith(
					("insert", "update", "delete", "replace")):
				writes.append(" ".join(str(query).split())[:120])
			return real(query, *args, **kwargs)

		frappe.db.sql = spy
		try:
			pay_api.get_pay()
		finally:
			frappe.db.sql = real
		self.assertEqual(writes, [])
