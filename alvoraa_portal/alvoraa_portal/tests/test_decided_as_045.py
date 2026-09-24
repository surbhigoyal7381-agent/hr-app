"""045 AC-81 / AC-82, SEC-19, and D-12 - an HR override is stored as an HR decision.

D-12 was Wave 2's D-2, left unbuilt: who may decide an attendance correction,
and from when. Surbhi answered it on 24 September 2026. HR sees a covered
person's correction **from day one** and may act **from day three**, counted as
two working days on the **requester's own** holiday list, and when HR acts the
record says **HR** decided, not the manager.

The criterion this file exists for is AC-82(d): **a test reads only the two
stored documents - no screen, no session, no `reports_to` lookup - and
distinguishes a manager's approval from an HR override.** If it cannot, the
check fails. That is the whole point of storing the capacity rather than
working it out later, because `reports_to` changes and the year somebody asks
is exactly the year it has changed.

And SEC-19's three conditions, which are the difference between an audit field
and a field a client can lie about:

* (f) the value is written from the server's own derivation;
* (g) supplying `decided_as` in the request body changes nothing;
* (h) changing `reports_to` afterwards does not change what was stored.
"""

import frappe
from frappe.utils import add_days, getdate, nowdate

from alvoraa_portal import attendance_correction as ac
from alvoraa_portal.tests.fixtures_045 import Wave4Base, own_employee

HOLIDAY_LIST = "S045 Requester Holidays"


def may_review_granted():
	"""Let the caller past `_may_review()`, WITHOUT touching site permissions.

	**Found by three `PermissionError: You do not review attendance
	corrections.`** `_may_review()` is `frappe.has_permission(REQUEST,
	"submit")` - deliberately not a role list of our own, so a tenant that
	hands the queue to a Shift Supervisor gets it for free. On a clean site the
	plain `Employee` role does not hold that permission, so the fixture's
	manager could not decide anything.

	**The first fix I wrote for this was dangerous and I backed it out.** It
	created a role and gave it a `Custom DocPerm` on Attendance Request. But
	`module_access.py:262` says it plainly: **once ANY Custom DocPerm row
	exists for a doctype, its standard permissions are ignored entirely.** A
	single row added by a fixture would therefore have stripped HR Manager's
	own permissions on Attendance Request for every other suite on the site -
	a test that breaks other tests by changing shared state, which is the
	opposite of owning your own fixture.

	So the guard is patched in this process instead. What is under test in this
	file is the CAPACITY and the WAIT WINDOW, not who may review;
	`test_the_guard_itself_still_refuses` keeps the guard honest separately.
	"""
	from unittest.mock import patch

	return patch.object(ac, "_may_review", return_value=True)


class _Corrections(Wave4Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# The requester's OWN holiday list, with the next two days blocked out.
		# It is theirs and nobody else's - that is what "counted on the
		# requester's own holiday list" means, and a fixture that shared one
		# list between everybody could not tell the difference.
		if not frappe.db.exists("Holiday List", HOLIDAY_LIST):
			doc = frappe.get_doc({
				"doctype": "Holiday List",
				"holiday_list_name": HOLIDAY_LIST,
				"from_date": add_days(nowdate(), -30),
				"to_date": add_days(nowdate(), 60),
			})
			doc.insert(ignore_permissions=True)
		frappe.db.commit()

	def _request(self, employee, raised_on=None):
		"""One Attendance Request, raised by `employee`, optionally backdated."""
		# **The day being corrected is deliberately far from the days this
		# file blocks as holidays.** Found by
		# `ValidationError: [['Date','Reason','Action'],['2026-09-21','Holiday','Skip']]`
		# - Frappe HR skips a holiday when it writes the corrected Attendance
		# and refuses when every requested day was skipped. The holiday test
		# blocks today-3 and today-2, which is exactly where this used to sit.
		# A fixture whose dates collide with its own other fixture is a defect
		# slice 043 met too.
		day = add_days(nowdate(), -15)
		doc = frappe.get_doc({
			"doctype": ac.REQUEST,
			"employee": employee,
			"from_date": day,
			"to_date": day,
			"reason": "Forgot to Punch In",
			"explanation": "S045 fixture",
		})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		if raised_on:
			frappe.db.set_value(ac.REQUEST, doc.name, "creation", raised_on,
			                    update_modified=False)
		frappe.db.commit()
		self.addCleanup(self._drop, doc.name)
		return frappe.get_doc(ac.REQUEST, doc.name)

	def _drop(self, name):
		frappe.set_user("Administrator")
		if frappe.db.exists(ac.REQUEST, name):
			frappe.delete_doc(ac.REQUEST, name, force=True, ignore_permissions=True)
		frappe.db.commit()


class TestTheCapacityIsDerivedNotDeclared(_Corrections):
	def test_the_employees_own_manager_decides_as_manager(self):
		"""AC-82(c). Rahul reports to Sandeep, so Sandeep decides as Manager."""
		doc = self._request(self.rahul)
		self.assertEqual("Manager", ac.decided_as(doc, self.sandeep_user))

	def test_hr_who_is_not_their_manager_decides_as_hr(self):
		"""AC-82(b). Priya is HR and manages nobody, so she decides as HR."""
		doc = self._request(self.rahul)
		self.assertEqual("HR", ac.decided_as(doc, self.priya_user))

	def test_somebody_who_is_both_decides_as_manager_for_their_own_report(self):
		"""The order matters, and this is the case an engineer would guess at.

		Kamal holds HR Manager AND manages `kamal_both`. Deciding his own
		report's request, he decided as the manager - that is the act he
		performed. Being HR as well does not relabel it.
		"""
		doc = self._request(self.kamal_both)
		self.assertEqual("Manager", ac.decided_as(doc, self.kamal_user))

	def test_a_reviewer_who_is_neither_manager_nor_hr_is_not_called_hr(self):
		"""**W1D-14, and this is a regression Wave 4 nearly caused.**

		A tenant may give the submit permission on Attendance Request to a
		Shift Supervisor, who holds no HR entitlement and whose queue is
		deliberately not narrowed. The first version of `decided_as` returned
		"HR" for anybody who was not the manager - which would have written a
		false claim into an audit field AND put that supervisor behind the
		two-working-day wait, silently killing a flow that works today.

		Wave 4 was not asked to narrow that. They get None, which reads as
		"not recorded" - the honest answer, because the product has never had
		a word for the capacity they act in.
		"""
		supervisor = "s045.supervisor@example.com"
		if not frappe.db.exists("User", supervisor):
			doc = frappe.get_doc({"doctype": "User", "email": supervisor,
			                      "first_name": "S045 Supervisor",
			                      "send_welcome_email": 0})
			doc.append("roles", {"role": "Employee"})
			doc.insert(ignore_permissions=True)
			frappe.db.commit()
		req = self._request(self.rahul)
		self.assertIsNone(ac.decided_as(req, supervisor),
		                  "a non-HR, non-manager reviewer was labelled HR")

	def test_a_decided_as_in_the_request_body_changes_nothing(self):
		"""SEC-19(g). There is no argument for it, and adding one must be
		a change somebody makes on purpose rather than a thing that already
		half-works."""
		import inspect

		sig = inspect.signature(ac.decide)
		self.assertNotIn("decided_as", sig.parameters)
		# And the derivation takes no hint from anywhere but the caller.
		sig2 = inspect.signature(ac.decided_as)
		self.assertEqual(["doc", "user"], list(sig2.parameters))

	def test_the_derivation_reads_reports_to_and_not_the_effective_manager(self):
		"""AC-83 / SEC-7. `get_effective_manager` falls back to the first
		active HR Manager when `reports_to` is empty. A helper written to
		answer "who do we notify" must not decide "who may read" - or, here,
		who counts as the manager."""
		import inspect
		import re

		# Comments and docstrings stripped first. The first version of this
		# check went red on the DOCSTRING that explains why
		# `get_effective_manager` must not be used here - a test failing
		# because the code was documented. I made the same mistake in the
		# leave-privacy checks; this is the second time, so it is written down.
		src = (inspect.getsource(ac.decided_as)
		       + inspect.getsource(ac._manager_user_for))
		code = "\n".join(l for l in src.split("\n") if not l.strip().startswith("#"))
		code = re.sub(r'"""(.|\n)*?"""', "", code)
		self.assertNotIn("get_effective_manager", code)
		self.assertIn("reports_to", code)
		self.assertIn("def decided_as", code, "the stripper removed the code too")


class TestTheTwoWorkingDayWindow(_Corrections):
	def test_a_fresh_request_is_not_yet_hrs_to_decide(self):
		"""AC-81, the fail-closed half. Raised today, so HR waits."""
		doc = self._request(self.rahul)
		may_from, _basis = ac.hr_may_act_from(doc)
		self.assertGreater(getdate(may_from), getdate(nowdate()))

	def test_two_clear_days_are_enough_when_neither_is_a_holiday(self):
		doc = self._request(self.rahul, raised_on=f"{add_days(nowdate(), -5)} 09:00:00")
		may_from, _basis = ac.hr_may_act_from(doc)
		self.assertLessEqual(getdate(may_from), getdate(nowdate()))

	def _assign(self, employee, holiday_list):
		"""Point one person at one holiday list, the way this hrms resolves it.

		Found the hard way: this version reads a SUBMITTED "Holiday List
		Assignment", not the old `Employee.holiday_list` field. A test that set
		the field would have been asserting against a path the product does not
		take.
		"""
		frappe.db.delete("Holiday List Assignment", {"assigned_to": employee})
		doc = frappe.get_doc({
			"doctype": "Holiday List Assignment",
			"applicable_for": "Employee",
			"assigned_to": employee,
			"holiday_list": holiday_list,
			# **Inside the list's own range**, or Frappe HR refuses with
			# "Assignment start date cannot be outside holiday list dates".
			# Read from the list rather than hard-coded, so a list whose dates
			# move cannot break this silently.
			"from_date": frappe.db.get_value("Holiday List", holiday_list,
			                                 "from_date"),
		})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		doc.submit()
		frappe.db.commit()

	def test_the_requesters_own_holidays_push_the_date_out(self):
		"""The rule is two WORKING days, on THIS person's list.

		Two days are blocked on Rahul's own holiday list and on nobody else's.
		The date HR may act moves out by exactly those two days for him, and
		does not move for a colleague whose list is empty. A fixture that gave
		everybody one shared list could not tell the two apart, and the test
		would pass over nothing.
		"""
		raised = getdate(add_days(nowdate(), -4))
		blocked = [add_days(raised, 1), add_days(raised, 2)]
		hl = frappe.get_doc("Holiday List", HOLIDAY_LIST)
		hl.set("holidays", [])
		for d in blocked:
			hl.append("holidays", {"holiday_date": d, "description": "S045"})
		hl.flags.ignore_permissions = True
		hl.save(ignore_permissions=True)
		self._assign(self.rahul, HOLIDAY_LIST)
		self.addCleanup(self._restore_shared_list, self.rahul)

		with_holidays = self._request(self.rahul, raised_on=f"{raised} 09:00:00")
		without = self._request(self.covered_only[0], raised_on=f"{raised} 09:00:00")
		a, basis_a = ac.hr_may_act_from(with_holidays)
		b, _basis_b = ac.hr_may_act_from(without)

		self.assertGreater(getdate(a), getdate(b),
		                   "the requester's own holidays did not move their date")
		self.assertEqual(str(add_days(raised, 4)), a,
		                 "two blocked days should push two clear days out")
		self.assertEqual(str(add_days(raised, 2)), b)
		self.assertIn("holiday list", basis_a)

	def _restore_shared_list(self, employee):
		from alvoraa_portal.tests.leave_fixtures import assign_holiday_list

		frappe.set_user("Administrator")
		frappe.db.delete("Holiday List Assignment", {"assigned_to": employee})
		frappe.db.commit()
		assign_holiday_list(employee)

	def test_no_holiday_list_falls_back_to_calendar_days_and_says_so(self):
		"""A store that has not been set up must not make an approval
		unreachable - and must not pretend a weekend was counted either.

		The request is a plain dict rather than a saved document: **saving an
		Attendance Request for somebody with no holiday list is itself refused
		by Frappe HR**, so a fixture cannot both have no list and have a
		request. What is under test here is the wait-window arithmetic, and
		that takes only an employee and a date.
		"""
		naked = own_employee("S045NoHolidays")
		frappe.db.delete("Holiday List Assignment", {"assigned_to": naked})
		frappe.db.commit()
		raised = add_days(nowdate(), -10)
		doc = frappe._dict({"employee": naked, "creation": f"{raised} 09:00:00",
		                    "name": "ZZ-045-probe"})
		may_from, basis = ac.hr_may_act_from(doc)
		self.assertIn("calendar days", basis)
		self.assertEqual(str(add_days(getdate(raised), 2)), may_from)


class TestTheRecordAnswersOnItsOwn(_Corrections):
	def test_the_column_exists_after_migrate(self):
		"""The check on the check. Every assertion below is about a stored
		value, so if the column is missing they would all be passing over
		nothing."""
		self.assertTrue(frappe.db.has_column(ac.REQUEST, "alvoraa_decided_as"),
		                "alvoraa_decided_as is not installed - run bench migrate")

	def test_a_year_later_the_two_documents_can_be_told_apart(self):
		"""**AC-82(d), and this is the criterion the field exists for.**

		Two requests, decided by two people in two capacities. The assertion
		reads ONLY the stored documents - no session, no screen, no
		`reports_to` lookup - and then changes `reports_to` underneath both, to
		prove the stored answer is the stored answer (SEC-19(h)).
		"""
		by_manager = self._request(self.rahul,
		                           raised_on=f"{add_days(nowdate(), -9)} 09:00:00")
		by_hr = self._request(self.covered_only[2],
		                      raised_on=f"{add_days(nowdate(), -9)} 09:00:00")

		with may_review_granted():
			self.as_user(self.sandeep_user)
			ac.decide(by_manager.name, 1)
			self.as_user(self.priya_user)
			ac.decide(by_hr.name, 1)
		frappe.set_user("Administrator")

		stored = {
			name: frappe.db.get_value(ac.REQUEST, name,
			                          ["alvoraa_decided_as", "alvoraa_reviewed_by"],
			                          as_dict=True)
			for name in (by_manager.name, by_hr.name)
		}
		self.assertEqual("Manager", stored[by_manager.name].alvoraa_decided_as)
		self.assertEqual("HR", stored[by_hr.name].alvoraa_decided_as)

		# SEC-19(h). Move the reporting line and ask again. A derived answer
		# would change here; a stored one does not, and the year somebody asks
		# is exactly the year it has changed.
		frappe.db.set_value("Employee", self.rahul, "reports_to", self.kamal,
		                    update_modified=False)
		frappe.db.commit()
		self.assertEqual(
			"Manager",
			frappe.db.get_value(ac.REQUEST, by_manager.name, "alvoraa_decided_as"),
			"the stored capacity moved when reports_to moved")
		frappe.db.set_value("Employee", self.rahul, "reports_to", self.sandeep,
		                    update_modified=False)
		frappe.db.commit()

	def test_hr_is_refused_before_the_window_and_the_refusal_says_what_to_do(self):
		"""AC-81. Raised today, so Priya is refused - and the sentence names
		the manager and the date, because "not allowed" is not a next step."""
		doc = self._request(self.rahul)
		self.as_user(self.priya_user)
		with may_review_granted(), self.assertRaises(frappe.PermissionError) as caught:
			ac.decide(doc.name, 1)
		msg = str(caught.exception)
		self.assertIn("still with", msg)
		self.assertNotIn("S045-MOBILE", msg, "a refusal must carry no personal detail")

	def test_the_manager_is_not_made_to_wait(self):
		"""The window is HR's, not everybody's. Sandeep decides his own
		report's request the moment it is raised."""
		doc = self._request(self.rahul)
		with may_review_granted():
			self.as_user(self.sandeep_user)
			ac.decide(doc.name, 1)
		frappe.set_user("Administrator")
		self.assertEqual("Manager",
		                 frappe.db.get_value(ac.REQUEST, doc.name, "alvoraa_decided_as"))

	def test_an_undecided_record_says_not_recorded_and_never_manager(self):
		"""No backfill, and no default. An empty value belongs to a decision
		made before this field existed, and guessing backwards would put a
		claim in the record that nobody made."""
		doc = self._request(self.rahul)
		shaped = ac._shape(frappe.db.get_value(
			ac.REQUEST, doc.name, ac.request_fields(), as_dict=True))
		self.assertIsNone(shaped["decided_as"])

	def test_the_read_survives_a_site_without_the_column(self):
		"""The migration risk, asserted rather than described.

		`request_fields()` must not name a column that is not there - a
		`fields` list naming a missing column makes the READ fail, so every
		screen listing corrections would go blank on a deploy that skipped
		migrations.
		"""
		from unittest.mock import patch

		with patch.object(frappe.db, "has_column", return_value=False):
			fields = ac.request_fields()
		self.assertNotIn("alvoraa_decided_as", fields)
		# And it still returns a usable list, so the queue degrades to
		# "capacity not recorded" rather than to an error page.
		rows = frappe.get_all(ac.REQUEST, fields=fields, limit_page_length=1)
		self.assertIsInstance(rows, list)


class TestTheGuardItselfIsStillThere(_Corrections):
	"""The other half of patching `_may_review` in the tests above.

	Those tests are about the capacity and the wait window, so they step past
	the review permission on purpose. This one steps nowhere: it calls `decide`
	as somebody with no submit permission at all and asserts the refusal, so
	that patching the guard elsewhere cannot quietly become "there is no
	guard".
	"""

	def test_the_guard_itself_still_refuses(self):
		doc = self._request(self.rahul)
		self.as_user(self.rahul_user)
		with self.assertRaises(frappe.PermissionError) as caught:
			ac.decide(doc.name, 1)
		self.assertIn("do not review", str(caught.exception))
