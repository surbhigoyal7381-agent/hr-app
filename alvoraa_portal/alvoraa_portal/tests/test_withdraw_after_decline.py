"""ALV-275: an employee must not be able to withdraw a decision HR has made.

**What went wrong.** A declined request deliberately stays a draft. Frappe will
not move a draft to cancelled, and deleting it would destroy the record, so
`decide` leaves it at docstatus 0 with HR's reason on it. `withdraw` only
checked `docstatus != 0`, so it could not see that.

The employee who raised it could therefore withdraw their own refusal. The
`db_set` in `withdraw` overwrote "Declined" with "Withdrawn" and put the
employee's own login into `alvoraa_reviewed_by` over HR's. HR's note stayed
behind. The record ended up saying the employee took back a request that HR had
in fact refused, with HR's words attached and HR's name gone.

Same shape as ALV-269: a `db_set` that asked one question and not the other.
There, the missing question was who you are. Here, it is what state the record
is already in. `DONE_STATES` existed for exactly this and was not asked.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from alvoraa_portal import attendance_correction as ac
# Reused rather than rebuilt - the company, the Holiday List Assignment an
# Attendance Request insists on, and the one-time field install.
from alvoraa_portal.tests.test_attendance_correction import (_company,
                                                             _holiday_list,
                                                             setUpModule)

REQUEST = "Attendance Request"


class WithdrawAfterDeclineCase(FrappeTestCase):
	"""One employee with a login, and an HR person who can refuse them."""

	# Per test, never committed - see test_decline_scope for what a committed
	# fixture cost the first time.
	_slot = 0

	def setUp(self):
		frappe.set_user("Administrator")
		WithdrawAfterDeclineCase._slot += 1
		tag = WithdrawAfterDeclineCase._slot
		self.company = _company()
		_holiday_list(self.company)

		# The employee, with a login, because `withdraw` works out who is
		# calling from their Employee record.
		self.staff_email = self._login("Alv275staff%d" % tag)
		self.staff = self._employee("Alv275staff%d" % tag, self.staff_email)

		# HR with no Employee record and no User Permission: entitled to the
		# whole site, which is how every HR login on our tenants is set up, so
		# the decline below is not itself what is under test.
		self.hr = self._login("Alv275hr%d" % tag, roles=("HR User",))

	def tearDown(self):
		frappe.set_user("Administrator")

	# ── fixtures ────────────────────────────────────────────────────────────

	def _login(self, first, roles=()):
		email = "%s.a275@example.com" % first.lower()
		if not frappe.db.exists("User", email):
			u = frappe.get_doc({"doctype": "User", "email": email,
			                    "first_name": first,
			                    "send_welcome_email": 0}).insert(ignore_permissions=True)
			for r in roles:
				u.add_roles(r)
		return email

	def _employee(self, first, user_id=None):
		doc = {"doctype": "Employee", "first_name": first, "company": self.company,
		       "date_of_birth": "1970-01-01", "date_of_joining": "2000-01-01",
		       "gender": frappe.db.get_value("Gender", {}, "name") or "Male",
		       "status": "Active"}
		if user_id:
			doc["user_id"] = user_id
		return frappe.get_doc(doc).insert(ignore_permissions=True).name

	def _request(self):
		day = add_days(nowdate(), -3)
		return frappe.get_doc({
			"doctype": REQUEST, "employee": self.staff,
			"from_date": day, "to_date": day,
			"reason": "Forgot to Punch In",
			"explanation": "I was at the gate by 9, the reader did not beep",
		}).insert(ignore_permissions=True).name

	def _declined(self):
		"""A request HR has refused, with a reason, the ordinary way."""
		name = self._request()
		frappe.set_user(self.hr)
		try:
			ac.decide(name, approve=0, note="The register shows you off that day")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(
			frappe.db.get_value(REQUEST, name, "alvoraa_review_status"), "Declined",
			"the fixture did not actually decline it")
		return name

	def _withdraw(self, name):
		frappe.set_user(self.staff_email)
		try:
			return ac.withdraw(name)
		finally:
			frappe.set_user("Administrator")

	# ── the fault ───────────────────────────────────────────────────────────

	def test_a_declined_request_cannot_be_withdrawn(self):
		"""The whole ticket. Before the fix this returned the document."""
		name = self._declined()
		with self.assertRaises(frappe.ValidationError):
			self._withdraw(name)

	def test_hrs_decision_survives_the_attempt(self):
		"""Not merely refused - nothing overwritten. The three fields the
		`db_set` would have changed must all still say what HR left."""
		name = self._declined()
		before = frappe.db.get_value(
			REQUEST, name, ["alvoraa_review_status", "alvoraa_reviewed_by",
			                "alvoraa_review_note"], as_dict=True)
		with self.assertRaises(frappe.ValidationError):
			self._withdraw(name)
		after = frappe.db.get_value(
			REQUEST, name, ["alvoraa_review_status", "alvoraa_reviewed_by",
			                "alvoraa_review_note"], as_dict=True)
		self.assertEqual(after.alvoraa_review_status, "Declined")
		self.assertEqual(after.alvoraa_reviewed_by, self.hr)
		self.assertEqual(after, before)

	def test_the_employee_is_told_what_to_do_next(self):
		"""The file's own rule: say what happened, why, and what to do next -
		never just "not allowed". The day may still be wrong."""
		name = self._declined()
		frappe.clear_messages()
		with self.assertRaises(frappe.ValidationError):
			self._withdraw(name)
		said = " ".join(m.get("message", "") for m in frappe.message_log)
		self.assertIn("already declined", said)
		self.assertIn("Raise it again", said)

	def test_withdrawing_twice_is_refused_too(self):
		"""`DONE_STATES` holds both states, so the second attempt is caught by
		the same line - and told plainly rather than silently re-stamped."""
		name = self._request()
		self._withdraw(name)
		frappe.clear_messages()
		with self.assertRaises(frappe.ValidationError):
			self._withdraw(name)
		said = " ".join(m.get("message", "") for m in frappe.message_log)
		self.assertIn("already withdrawn", said)

	# ── and what must keep working ─────────────────────────────────────────

	def test_a_waiting_request_can_still_be_withdrawn(self):
		"""The employee does not lose the thing withdraw is for."""
		name = self._request()
		out = self._withdraw(name)
		self.assertEqual(out["state"], "withdrawn")
		row = frappe.db.get_value(REQUEST, name,
		                          ["alvoraa_review_status", "alvoraa_reviewed_by"],
		                          as_dict=True)
		self.assertEqual(row.alvoraa_review_status, "Withdrawn")
		self.assertEqual(row.alvoraa_reviewed_by, self.staff_email)

	def test_somebody_elses_request_is_still_not_theirs(self):
		"""The ownership check above the new one is untouched."""
		other = self._employee("Alv275other%d" % WithdrawAfterDeclineCase._slot)
		day = add_days(nowdate(), -3)
		name = frappe.get_doc({
			"doctype": REQUEST, "employee": other, "from_date": day, "to_date": day,
			"reason": "Forgot to Punch In", "explanation": "not mine",
		}).insert(ignore_permissions=True).name
		with self.assertRaises(frappe.PermissionError):
			self._withdraw(name)
