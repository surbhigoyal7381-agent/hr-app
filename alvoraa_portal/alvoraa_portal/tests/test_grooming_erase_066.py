"""Slice 066 retention: a leaver's grooming marks and reviews are erased 6
months after the relieving date, and nothing of them is left behind.

Counsel's rule (employment + 6 months, then erased, no soft delete), the
04b strategy, and Surbhi's D-1 (30 days after the last Employee edit) and
D-2 (a rehire on a new Employee record does not carry the old marks).

The job ships OFF: nothing is erased unless the site config holds
grooming_erase_enabled = 1. Every test that needs a real erase turns it on
for itself only.

Records are written straight to the tables: the erase must remove whatever
exists, including the things the rules would refuse to create today.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, getdate, now_datetime, nowdate

import alvoraa_portal.grooming as grooming

COMPANY = "R066 Co"
TODAY = getdate(nowdate())
DUE = add_days(add_months(TODAY, -6), -1)       # 6 months and a day ago
EDGE = add_months(TODAY, -6)                     # exactly 6 months ago: kept
OLD_EDIT = add_days(TODAY, -60)                  # D-1 satisfied
OTHER_TEXT = "R066 torn jacket sleeve"
ON = {"grooming_erase_enabled": 1}

# Every table that can hold a trace of a mark or a review, by its type field.
TRACES = (("Version", "ref_doctype", "docname"), ("Comment", "reference_doctype", "reference_name"),
          ("Notification Log", "document_type", "document_name"), ("ToDo", "reference_type", "reference_name"),
          ("DocShare", "share_doctype", "share_name"), ("Tag Link", "document_type", "document_name"),
          ("Event Participants", "reference_doctype", "reference_docname"))
P = {}


def _company():
	if not frappe.db.exists("Company", COMPANY):
		frappe.get_doc({"doctype": "Company", "company_name": COMPANY, "abbr": "R066C",
		                "default_currency": "INR", "country": "India"}).insert(ignore_permissions=True)


def _person(first, status="Left", relieved=DUE, edited=OLD_EDIT):
	name = frappe.db.get_value("Employee", {"first_name": first, "last_name": "R066"}, "name")
	if not name:
		gender = frappe.db.get_value("Gender", {}, "name")
		name = frappe.get_doc({"doctype": "Employee", "first_name": first, "last_name": "R066",
		                       "company": COMPANY, "gender": gender, "date_of_birth": "1990-01-01",
		                       "date_of_joining": add_days(TODAY, -900), "status": "Active",
		                       "create_user_permission": 0}).insert(ignore_permissions=True).name
	# Straight to the row, so `modified` is exactly what the test says (D-1).
	frappe.db.set_value("Employee", name, {"status": status, "relieving_date": relieved,
	                                       "modified": edited}, update_modified=False)
	P[first] = name
	return name


def _raw(d, docstatus=0):
	doc = frappe.get_doc(d)
	doc.name = frappe.generate_hash(length=10)
	doc.docstatus = docstatus
	doc.db_insert()
	for child in doc.get_all_children():
		child.parent = doc.name
		child.db_insert()
	return doc.name


def _mark(emp, docstatus=1, reason="Not in uniform", other=None):
	return _raw({"doctype": grooming.MARK, "employee": emp, "mark_date": add_days(TODAY, -300),
	             "reason": reason, "other_reason": other, "marked_as": "HR",
	             "employee_name": "R066"}, docstatus)


def _review(emp):
	return _raw({"doctype": grooming.REVIEW, "employee": emp,
	             "review_month": add_days(TODAY, -300), "review_note": "R066 review note"})


def _traces(doctype, name):
	"""One of each side record, written past the guard that refuses them now."""
	for table, type_field, name_field in TRACES:
		if table == "Event Participants":
			event = _raw({"doctype": "Event", "subject": "R066", "starts_on": now_datetime(),
			              "event_type": "Private"})
			_raw({"doctype": table, "parent": event, "parenttype": "Event",
			      "parentfield": "event_participants", type_field: doctype, name_field: name})
			continue
		row = {"doctype": table, type_field: doctype, name_field: name}
		row.update({"Version": {"data": "{}"}, "Comment": {"comment_type": "Info", "content": "x"},
		            "Notification Log": {"subject": "x", "for_user": "Administrator"},
		            "ToDo": {"description": "x", "allocated_to": "Administrator"},
		            "DocShare": {"user": "Administrator", "read": 1},
		            "Tag Link": {"tag": "R066"}}[table])
		_raw(row)


def _left(doctype, names):
	"""Every row anywhere that still names one of these records."""
	out = {doctype: frappe.db.count(doctype, {"name": ("in", names)})}
	for table, type_field, name_field in TRACES:
		out[table] = frappe.db.count(table, {type_field: doctype, name_field: ("in", names)})
	out["Deleted Document"] = frappe.db.count("Deleted Document", {"deleted_doctype": doctype})
	out["Deleted comment"] = frappe.db.count("Comment", {"reference_doctype": doctype,
	                                                     "comment_type": "Deleted"})
	return {k: v for k, v in out.items() if v}


def _records(emp):
	return (frappe.db.count(grooming.MARK, {"employee": emp})
	        + frappe.db.count(grooming.REVIEW, {"employee": emp}))


def _alerts(title=None):
	titles = [title] if title else [grooming.ERASE_FAILED, grooming.CHECK_FAILED]
	return frappe.get_all("Error Log", filters={"method": ("in", titles)}, fields=["method", "error"])


def _wipe():
	people = list(P.values()) or [""]
	marks = frappe.get_all(grooming.MARK, filters={"employee": ("in", people)}, pluck="name")
	reviews = frappe.get_all(grooming.REVIEW, filters={"employee": ("in", people)}, pluck="name")
	frappe.db.delete(grooming.MARK, {"employee": ("in", people)})
	frappe.db.delete(grooming.REVIEW, {"employee": ("in", people)})
	for doctype, names in ((grooming.MARK, marks), (grooming.REVIEW, reviews)):
		for table, type_field, name_field in TRACES:
			frappe.db.delete(table, {type_field: doctype, name_field: ("in", names or [""])})
	frappe.db.delete("Event", {"subject": "R066"})
	slips = frappe.get_all("Salary Slip", filters={"employee": ("in", people)}, pluck="name")
	frappe.db.delete("Salary Detail", {"parenttype": "Salary Slip", "parent": ("in", slips or [""])})
	frappe.db.delete("Salary Slip", {"employee": ("in", people)})
	frappe.db.delete("Additional Salary", {"employee": ("in", people)})
	frappe.db.delete("Error Log", {"method": ("in", [grooming.ERASE_FAILED, grooming.CHECK_FAILED])})


def setUpModule():
	frappe.set_user("Administrator")
	_company()
	frappe.db.commit()


def tearDownModule():
	frappe.set_user("Administrator")
	_wipe()
	frappe.db.commit()


class Case(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.local.request_cache.clear()
		_wipe()

	def tearDown(self):
		frappe.set_user("Administrator")
		_wipe()
		frappe.db.commit()

	def erase(self):
		with patch.dict(frappe.conf, ON):
			return grooming.erase_due()


class TestTheSwitch(Case):
	def test_it_ships_off_and_the_daily_run_then_erases_nothing(self):
		self.assertFalse(grooming.erase_switched_on(), "grooming_erase_enabled is set on the test site")
		emp = _person("Off")
		_mark(emp)
		self.assertEqual(grooming.erase_due(), {"switched_on": 0})
		self.assertEqual(_records(emp), 1)
		self.assertEqual(_alerts(), [])

	def test_the_daily_hook_line_exists(self):
		import alvoraa_portal.hooks as hooks

		self.assertIn("alvoraa_portal.grooming.erase_due", hooks.scheduler_events["daily"])


class TestWhatIsErased(Case):
	def test_a_due_leavers_marks_reviews_and_every_trace_are_gone(self):
		emp = _person("Gone")
		marks = [_mark(emp), _mark(emp, docstatus=2), _mark(emp, docstatus=0),
		         _mark(emp, reason=grooming.OTHER, other=OTHER_TEXT)]
		reviews = [_review(emp)]
		for m in marks:
			_traces(grooming.MARK, m)
		_traces(grooming.REVIEW, reviews[0])
		# As on a server whose worker is down: Frappe's own queued clean-up
		# never runs, so the erase must do it itself.
		with patch("frappe.enqueue"):
			out = self.erase()
		self.assertEqual(out["people"], 1)
		self.assertEqual((out["marks"], out["reviews"]), (4, 1))
		self.assertEqual(_left(grooming.MARK, marks), {})
		self.assertEqual(_left(grooming.REVIEW, reviews), {})
		self.assertEqual(_alerts(), [])

	def test_the_boundary_is_the_day_after_six_months(self):
		if add_months(EDGE, 6) != TODAY:
			self.skipTest("no date is exactly 6 months before today")
		kept, gone = _person("Edge", relieved=EDGE), _person("Past", relieved=DUE)
		_mark(kept)
		_mark(gone)
		self.erase()
		self.assertEqual((_records(kept), _records(gone)), (1, 0))

	def test_anyone_not_left_is_kept_whatever_the_date(self):
		people = [_person(s, status=s) for s in ("Active", "Inactive", "Suspended")]
		for emp in people:
			_mark(emp)
			_review(emp)
		self.erase()
		self.assertEqual([_records(e) for e in people], [2, 2, 2])

	def test_d1_an_employee_edited_in_the_last_30_days_waits(self):
		emp = _person("Typo", edited=now_datetime())
		_mark(emp)
		self.assertEqual(grooming.erase_due(dry_run=1)["people"], 0)
		self.erase()
		self.assertEqual(_records(emp), 1)

	def test_the_lock_recheck_spares_a_person_rehired_after_the_list_was_made(self):
		emp = _person("Back", status="Active", relieved=None)
		_mark(emp)
		self.assertIsNone(grooming._erase_person(emp, TODAY))
		self.assertEqual(_records(emp), 1)

	def test_d2_a_rehire_on_a_new_record_and_other_people_keep_their_marks(self):
		old, new, other = _person("Rehire"), _person("Rehire2", status="Active", relieved=None), \
			_person("Stays", status="Active", relieved=None)
		for emp in (old, new, other):
			_mark(emp)
		self.erase()
		self.assertEqual([_records(e) for e in (old, new, other)], [0, 1, 1])

	def test_it_still_erases_with_grooming_switched_off(self):
		if not frappe.db.exists("Salary Component", grooming.COMPONENT):
			frappe.get_doc({"doctype": "Salary Component", "salary_component": grooming.COMPONENT,
			                "salary_component_abbr": "GRV", "type": "Deduction"}).insert()
		was = frappe.db.get_value("Salary Component", grooming.COMPONENT, "disabled")
		frappe.db.set_value("Salary Component", grooming.COMPONENT, "disabled", 1)
		try:
			frappe.local.request_cache.clear()
			self.assertFalse(grooming.is_on())
			emp = _person("Switch")
			_mark(emp)
			_review(emp)
			self.erase()
			self.assertEqual(_records(emp), 0)
		finally:
			frappe.db.set_value("Salary Component", grooming.COMPONENT, "disabled", was)


class TestPayStays(Case):
	def test_the_slip_its_grooming_line_and_the_additional_salary_stay(self):
		emp = _person("Paid")
		_mark(emp)
		start = add_days(TODAY, -310)
		extra = _raw({"doctype": "Additional Salary", "employee": emp, "company": COMPANY,
		              "salary_component": grooming.COMPONENT, "amount": 300, "payroll_date": start,
		              "currency": "INR"}, docstatus=1)
		slip = _raw({"doctype": "Salary Slip", "employee": emp, "company": COMPANY,
		             "start_date": start, "end_date": add_days(start, 29), "posting_date": start,
		             "deductions": [{"salary_component": grooming.COMPONENT, "amount": 300,
		                             "additional_salary": extra}]}, docstatus=1)
		self.erase()
		self.assertEqual(_records(emp), 0)
		self.assertEqual(frappe.db.get_value("Salary Slip", slip, "docstatus"), 1)
		self.assertEqual(frappe.get_all("Salary Detail", filters={"parent": slip}, pluck="amount"), [300])
		self.assertEqual(tuple(frappe.db.get_value("Additional Salary", extra, ["docstatus", "amount"])),
		                 (1, 300))

	def test_a_draft_slip_holds_the_person_and_is_counted(self):
		emp = _person("Draft")
		_mark(emp)
		_raw({"doctype": "Salary Slip", "employee": emp, "company": COMPANY,
		      "start_date": TODAY, "end_date": TODAY, "posting_date": TODAY})
		self.assertEqual(grooming.erase_due(dry_run=1)["skipped_draft_slip"], 1)
		self.erase()
		self.assertEqual(_records(emp), 1)


class TestDryRunAndRepeat(Case):
	def test_the_dry_run_erases_nothing_and_counts_what_the_real_run_erases(self):
		emp = _person("Dry")
		marks = [_mark(emp), _mark(emp)]
		_review(emp)
		_traces(grooming.MARK, marks[0])
		dry = grooming.erase_due(dry_run=1)
		self.assertEqual(_records(emp), 3)
		self.assertEqual((dry["people"], dry["marks"], dry["reviews"], dry["notices"], dry["versions"]),
		                 (1, 2, 1, 1, 1))
		self.assertEqual(dry["employees"], [emp])
		real = self.erase()
		self.assertEqual((real["people"], real["marks"], real["reviews"]),
		                 (dry["people"], dry["marks"], dry["reviews"]))

	def test_a_second_run_does_nothing_and_raises_nothing(self):
		emp = _person("Twice")
		_mark(emp)
		self.erase()
		out = self.erase()
		self.assertEqual((out["people"], out["marks"], out["reviews"]), (0, 0, 0))
		self.assertEqual(_alerts(), [])

	def test_one_record_that_will_not_erase_stops_nobody_else_and_logs_an_id_only(self):
		stuck, fine = _person("Stuck", relieved=add_days(DUE, -5)), _person("Fine")
		bad = _mark(stuck, reason=grooming.OTHER, other=OTHER_TEXT)
		_mark(fine)
		real_erase = grooming._erase_one

		def fail_on_bad(doctype, name):
			if name == bad:
				raise frappe.ValidationError(OTHER_TEXT)
			return real_erase(doctype, name)

		with patch.object(grooming, "_erase_one", fail_on_bad):
			self.erase()
		self.assertEqual((_records(stuck), _records(fine)), (1, 0))
		logs = _alerts(grooming.ERASE_FAILED)
		self.assertEqual(len(logs), 1)
		self.assertEqual(logs[0].error, "Employee {0}".format(stuck))
		self.assertNotIn(OTHER_TEXT, logs[0].error)
		self.assertNotIn("R066", logs[0].error)


class TestSelfCheck(Case):
	def test_a_person_past_due_and_a_leaver_without_a_date_raise_one_alert(self):
		overdue, nodate = _person("Late", relieved=add_days(DUE, -3)), _person("Nodate", relieved=None)
		_mark(overdue)
		_mark(nodate)
		counts = grooming.erase_self_check()
		self.assertEqual((counts["people past due"], counts["left without a relieving date"]), (1, 1))
		logs = _alerts(grooming.CHECK_FAILED)
		self.assertEqual(len(logs), 1)
		self.assertNotIn(overdue, logs[0].error)
		self.assertEqual(grooming.erase_due(dry_run=1)["left_without_date"], 1)
		self.erase()
		self.assertEqual((_records(overdue), _records(nodate)), (0, 1))

	def test_a_clean_site_raises_nothing(self):
		emp = _person("Clean", status="Active", relieved=None)
		_mark(emp)
		self.assertEqual(sum(grooming.erase_self_check().values()), 0)
		self.assertEqual(_alerts(), [])


class TestNoHandDelete(Case):
	def test_the_administrator_cannot_delete_a_mark_or_a_review_from_the_desk(self):
		emp = _person("Desk", status="Active", relieved=None)
		removed, review = _mark(emp, docstatus=2), _review(emp)
		for doctype, name in ((grooming.MARK, removed), (grooming.REVIEW, review)):
			with self.assertRaises(frappe.ValidationError):
				frappe.delete_doc(doctype, name)
			self.assertTrue(frappe.db.exists(doctype, name))
			self.assertEqual(frappe.db.count("Deleted Document", {"deleted_doctype": doctype}), 0)
