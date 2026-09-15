"""Slice 010 group D: pin tests for review copies and review access.

Requirements: docs/slices/010-portal-security-fixes/00c (R1-R16), 00d (strategy),
01d (VIS / SEC / PRIV) and 00e (the approved decisions, which win).

Each test is named after the rule it keeps closed, so a merge that drops a fix
fails CI here. Refusals are tested, not only the allowed path.

These live in alvoraa_portal because CI runs only the alvoraa_portal and
alvoraa_goals suites. Synthetic people and records only, tagged S010D.
"""

import json
import random
import uuid
from unittest.mock import patch

import frappe
from frappe.utils import add_days, now_datetime

from alvoraa_goals.tests.utils import ensure_company
from alvoraa_portal.tests.test_portal_security_010 import _Base, _employee, _second_company, _user

TAG = "S010D"


# ── fixtures ────────────────────────────────────────────────────────────────


def _uid():
	return uuid.uuid4().hex[:8]


class _ReviewBase(_Base):
	"""A cycle, an appraisal and an Extension per test, cleaned up afterwards.

	Review endpoints commit, so the base class's rollback is not enough: every
	record made here is listed in self._cleanup and deleted in tearDown.
	"""

	def setUp(self):
		super().setUp()
		self._plan = patch("alvoraa_portal.subscription.has_feature", return_value=True)
		self._plan.start()

	def tearDown(self):
		self._plan.stop()
		frappe.set_user("Administrator")
		frappe.db.rollback()
		# Copies first: the Extension refuses a change to them otherwise, and a
		# plain delete of the child rows is the honest cleanup for a test.
		for doctype, name in self._cleanup:
			if doctype == "Alvoraa Appraisal Extension":
				frappe.db.delete("Alvoraa Review Item", {"parent": name, "parenttype": doctype})
		frappe.db.commit()
		super().tearDown()

	# A different far-future year per review keeps HRMS's "one appraisal per
	# overlapping period" rule from tripping over another test's records.
	def _window(self):
		year = random.randint(2100, 2899)
		return f"{year}-04-01", f"{year}-06-30"

	def _cycle(self, start=None, end=None, company=None):
		if not start:
			start, end = self._window()
		name = f"{TAG} Cycle {_uid()}"
		frappe.get_doc(
			{
				"doctype": "Appraisal Cycle",
				"cycle_name": name,
				"company": company or ensure_company(),
				"start_date": start,
				"end_date": end,
				"status": "In Progress",
			}
		).insert(ignore_permissions=True)
		self._cleanup.append(("Appraisal Cycle", name))
		return name

	def _appraisal(self, employee, cycle, status="Not Started", with_extension=True):
		company = frappe.db.get_value("Employee", employee, "company")
		ap = frappe.get_doc(
			{"doctype": "Appraisal", "employee": employee, "appraisal_cycle": cycle, "company": company}
		).insert(ignore_permissions=True)
		self._cleanup.append(("Appraisal", ap.name))
		if with_extension:
			ext = frappe.get_doc(
				{
					"doctype": "Alvoraa Appraisal Extension",
					"appraisal": ap.name,
					"employee": employee,
					"appraisal_cycle": cycle,
					"review_status": status,
				}
			).insert(ignore_permissions=True)
			self._cleanup.append(("Alvoraa Appraisal Extension", ext.name))
		frappe.db.commit()
		return ap.name

	def _set_status(self, appraisal, status):
		frappe.db.set_value("Alvoraa Appraisal Extension", appraisal, "review_status", status)
		frappe.db.commit()

	def _ext(self, appraisal):
		return frappe.get_doc("Alvoraa Appraisal Extension", appraisal)

	def _kpi(self, employee, cycle, target=100, mode="Cumulative", start=None, end=None, weightage=0,
	         direction="Higher is Better", goal=None):
		doc = frappe.get_doc(
			{
				"doctype": "KPI",
				"kpi_name": f"{TAG} KPI {_uid()}",
				"employee": employee,
				"appraisal_cycle": cycle,
				"target_value": target,
				"progress_mode": mode,
				"direction": direction,
				"weightage": weightage,
				"period_start": start,
				"period_end": end,
				"individual_goal": goal,
				"status": "Active",
			}
		)
		doc.insert(ignore_permissions=True)
		self._cleanup.append(("KPI", doc.name))
		frappe.db.commit()
		return doc.name

	def _goal(self, employee, cycle, start, end, target=100, mode="Cumulative", weightage=0, future=0):
		doc = frappe.get_doc(
			{
				"doctype": "Individual Goal",
				"employee": employee,
				"goal_name": f"{TAG} Goal {_uid()}",
				"appraisal_cycle": cycle,
				"target_value": target,
				"progress_mode": mode,
				"start_date": start,
				"end_date": end,
				"weightage": weightage,
				"is_future_plan": future,
			}
		)
		doc.insert(ignore_permissions=True)
		self._cleanup.append(("Individual Goal", doc.name))
		frappe.db.commit()
		return doc.name

	# Facts go straight into their tables, the way an approval leaves them. The
	# parent's own controller is not what these tests are about.
	def _row(self, doctype, parenttype, parentfield, parent, values):
		row = frappe.get_doc(
			dict(values, doctype=doctype, parent=parent, parenttype=parenttype, parentfield=parentfield)
		)
		row.name = frappe.generate_hash(length=10)
		row.db_insert()
		frappe.db.commit()
		return row.name

	def _reading(self, kpi, log_date, value, status="Approved", approved_on=None):
		return self._row(
			"KPI Progress Log", "KPI", "progress_log", kpi,
			{"log_date": log_date, "value": value, "approval_status": status,
			 "approved_on": approved_on or now_datetime()},
		)

	def _evidence(self, goal, value, extracted_date=None, upload_date=None, status="Approved"):
		return self._row(
			"Goal Evidence", "Individual Goal", "evidence_items", goal,
			{"evidence_type": "Manual Entry", "value": value, "validation_status": status,
			 "extracted_date": extracted_date, "upload_date": upload_date or now_datetime()},
		)

	def _goal_update(self, goal, log_date, value, status="Approved"):
		return self._row(
			"Goal Progress Update", "Individual Goal", "progress_updates", goal,
			{"log_date": log_date, "value": value, "approval_status": status, "approved_on": now_datetime()},
		)


def _subject(local):
	"""A plain employee with a login, in the ordinary test company."""
	user = _user(f"d.{local}", ("Employee",))
	return _employee(f"D{local}", company=ensure_company(), user=user), user


# ── R1 · The review's copies live on the review record (commit 1) ───────────


class TestR1ReviewItemStructure(_ReviewBase):
	def test_r1_copies_live_in_a_child_table_on_the_extension(self):
		item = frappe.get_meta("Alvoraa Review Item")
		self.assertTrue(item.istable)
		table = frappe.get_meta("Alvoraa Appraisal Extension").get_field("review_items")
		self.assertEqual((table.fieldtype, table.options), ("Table", "Alvoraa Review Item"))

		# Plain text, never a Link: a Link would make the live record impossible
		# to delete once any review copied it. Indexed, because the lock and the
		# refresh look copies up by it.
		source = item.get_field("source_name")
		self.assertEqual(source.fieldtype, "Data")
		self.assertTrue(source.search_index)

		ext = frappe.get_meta("Alvoraa Appraisal Extension")
		for field in ("items_taken_on", "review_window_start", "review_window_end", "freeze_point",
		              "removal_mode", "frozen", "frozen_on", "completed_on", "overall_rating_basis",
		              "overall_rating_flag", "overall_rated_by", "overall_rated_on"):
			self.assertTrue(ext.get_field(field), field)

	def test_r1_a_desk_or_rest_change_to_review_items_is_refused(self):
		employee, _u = _subject("structure")
		ap = self._appraisal(employee, self._cycle(), status="HR Review")

		ext = self._ext(ap)
		ext.append("review_items", {"item_type": "KPI", "title": "x", "manager_rating": 3})
		ext.flags.alvoraa_review_items_write = True
		ext.save(ignore_permissions=True)
		frappe.db.commit()

		# A changed rating, a new row, a removed row: all refused without the flag,
		# for Administrator too, and with ignore_validate set.
		changed = self._ext(ap)
		changed.review_items[0].manager_rating = 5
		with self.assertRaises(frappe.PermissionError):
			changed.save(ignore_permissions=True)

		added = self._ext(ap)
		added.append("review_items", {"item_type": "KPI", "title": "y"})
		with self.assertRaises(frappe.PermissionError):
			added.save(ignore_permissions=True)

		dropped = self._ext(ap)
		dropped.set("review_items", [])
		dropped.flags.ignore_validate = True
		with self.assertRaises(frappe.PermissionError):
			dropped.save(ignore_permissions=True)

		frappe.db.rollback()
		self.assertEqual(frappe.db.get_value("Alvoraa Review Item", {"parent": ap}, "manager_rating"), 3)

		# Saving the Extension for any other reason still works.
		other = self._ext(ap)
		other.archived = 1
		other.save(ignore_permissions=True)


# ── SEC-28 · The three settings: one audited place, validated (commit 1) ─────


class TestSec28ReviewSettings(_ReviewBase):
	FIELDS = ("alvoraa_review_freeze_point", "alvoraa_review_lock_release_days", "alvoraa_review_removal")

	def _reset(self):
		from alvoraa_goals import review_items

		for key, field in review_items.SETTING_FIELDS.items():
			frappe.db.set_single_value("HR Settings", field, review_items.DEFAULTS[key])
		# set_single_value leaves the cached settings document behind.
		frappe.clear_document_cache("HR Settings", "HR Settings")
		frappe.db.commit()

	def tearDown(self):
		self._reset()
		super().tearDown()

	def test_sec28_settings_are_installed_on_hr_settings_with_their_defaults(self):
		from alvoraa_goals import review_items

		meta = frappe.get_meta("HR Settings")
		self.assertEqual(meta.get_field("alvoraa_review_freeze_point").fieldtype, "Select")
		self.assertEqual(meta.get_field("alvoraa_review_lock_release_days").fieldtype, "Int")
		self.assertEqual(meta.get_field("alvoraa_review_removal").fieldtype, "Select")
		self.assertTrue(meta.track_changes, "HR Settings must keep a history of who changed what")

		# A site that never stored a value gets the defaults, and a second run
		# changes nothing that is already set.
		frappe.db.delete("Singles", {"doctype": "HR Settings", "field": ["in", self.FIELDS]})
		review_items.after_migrate()
		frappe.db.value_cache.pop("HR Settings", None)
		self.assertEqual(review_items.review_settings(), review_items.DEFAULTS)

		frappe.db.set_single_value("HR Settings", "alvoraa_review_lock_release_days", 45)
		review_items.after_migrate()
		frappe.db.value_cache.pop("HR Settings", None)
		self.assertEqual(review_items.review_settings()["lock_release_days"], 45)

	def test_sec28_reader_falls_back_on_unusable_values_and_never_throws(self):
		from alvoraa_goals import review_items

		frappe.db.set_single_value("HR Settings", "alvoraa_review_freeze_point", "whenever")
		frappe.db.set_single_value("HR Settings", "alvoraa_review_removal", "burn it")
		frappe.db.set_single_value("HR Settings", "alvoraa_review_lock_release_days", -5)
		frappe.db.value_cache.pop("HR Settings", None)
		settings = review_items.review_settings()
		self.assertEqual(settings["freeze_point"], review_items.FREEZE_HR_SENT)
		self.assertEqual(settings["removal_mode"], review_items.REMOVAL_DISCARD)
		# Below zero is read as 0: never released (SEC-22 fails closed).
		self.assertEqual(settings["lock_release_days"], 0)

	def test_sec28_bad_values_are_refused_and_only_hr_manager_may_change_them(self):
		hr_user = _user("d.settings.hruser", ("HR User", "Employee"))
		hr_manager = _user("d.settings.hrmanager", ("HR Manager", "Employee"))

		frappe.set_user(hr_user)
		doc = frappe.get_doc("HR Settings")
		doc.alvoraa_review_removal = "Keep the copy with a reason"
		with self.assertRaises(frappe.PermissionError):
			doc.save()

		frappe.set_user(hr_manager)
		for field, bad in (("alvoraa_review_lock_release_days", -1), ("alvoraa_review_freeze_point", "whenever")):
			doc = frappe.get_doc("HR Settings")
			doc.set(field, bad)
			with self.assertRaises(frappe.ValidationError, msg=field):
				doc.save()
			frappe.db.rollback()

		# The desk sends the whole settings form back; that save leaves a Version row.
		# Frappe skips Version rows while tests run (Document._save sets
		# ignore_version = frappe.in_test), so this save asks for one explicitly.
		frappe.db.rollback()
		frappe.clear_document_cache("HR Settings", "HR Settings")
		stored = frappe.db.get_single_value("HR Settings", "alvoraa_review_freeze_point", cache=False)
		changed = "Manager review sent" if stored != "Manager review sent" else "HR sent"
		versions = frappe.db.count("Version", {"ref_doctype": "HR Settings"})
		data = frappe.get_doc("HR Settings").as_dict()
		data["alvoraa_review_freeze_point"] = changed
		frappe.get_doc(data).save(ignore_version=False)
		self.assertEqual(frappe.db.count("Version", {"ref_doctype": "HR Settings"}), versions + 1)


# ── KPI indexes and change history (commit 1; slice 012 relies on the indexes) ─


class TestKpiIndexesAndHistory(_ReviewBase):
	def test_kpi_is_indexed_by_employee_and_cycle_and_keeps_change_history(self):
		meta = frappe.get_meta("KPI")
		self.assertTrue(meta.get_field("employee").search_index)
		self.assertTrue(meta.get_field("appraisal_cycle").search_index)
		# The write-back at completion needs a before/after record on the KPI.
		self.assertTrue(meta.track_changes)
		self.assertTrue(frappe.db.get_column_index("tabKPI", "employee", unique=False))
		self.assertTrue(frappe.db.get_column_index("tabKPI", "appraisal_cycle", unique=False))


# ── R1, R3, R4, R16, R7 · Copies, facts by date, stamps (commit 2) ──────────


def _day(start, days):
	return add_days(start, days)


def _row_for(ext, source_name):
	return next(r for r in ext.review_items if r.source_name == source_name)


class TestR1CopiesAreTakenOnFirstOpen(_ReviewBase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.employee, cls.user = _subject("copies")

	def test_vis4_copies_are_taken_once_when_the_review_is_first_opened(self):
		import alvoraa_goals.review_items as review_items
		import alvoraa_portal.performance_api as pa

		start, end = self._window()
		cycle = self._cycle(start, end)
		goal = self._goal(self.employee, cycle, start, end)
		kpi_under_goal = self._kpi(self.employee, cycle, goal=goal)
		kpi_alone = self._kpi(self.employee, cycle)
		ap = self._appraisal(self.employee, cycle)
		self.assertFalse(self._ext(ap).items_taken_on, "nothing is copied before the review is opened")

		frappe.set_user(self.user)
		pa.get_my_review(ap)
		frappe.set_user("Administrator")

		ext = self._ext(ap)
		self.assertTrue(ext.items_taken_on)
		self.assertEqual(sorted(r.source_name for r in ext.review_items), sorted([goal, kpi_under_goal, kpi_alone]))
		self.assertEqual(_row_for(ext, kpi_under_goal).parent_item, _row_for(ext, goal).name)
		self.assertEqual(_row_for(ext, kpi_alone).parent_item, "")
		self.assertEqual(str(ext.review_window_start), start)
		self.assertEqual(str(ext.review_window_end), end)
		names = sorted(r.name for r in ext.review_items)

		# A second open adds nothing. An item tagged to the cycle afterwards is
		# not slipped into the review behind the employee's back.
		self._kpi(self.employee, cycle)
		frappe.set_user(self.user)
		pa.get_my_review(ap)
		frappe.set_user("Administrator")
		self.assertFalse(review_items.ensure_review_items(self._ext(ap)))
		self.assertEqual(sorted(r.name for r in self._ext(ap).review_items), names)

	def test_vis14_vis15_other_cycle_cancelled_and_future_items_get_no_copy(self):
		import alvoraa_goals.review_items as review_items

		start, end = self._window()
		cycle = self._cycle(start, end)
		other_cycle = self._cycle(*self._window())
		kept = self._kpi(self.employee, cycle)
		self._kpi(self.employee, other_cycle)
		cancelled = self._kpi(self.employee, cycle)
		frappe.db.set_value("KPI", cancelled, "status", "Cancelled")
		self._goal(self.employee, cycle, start, end, future=1)
		ap = self._appraisal(self.employee, cycle)

		self.assertTrue(review_items.ensure_review_items(self._ext(ap)))
		self.assertEqual([r.source_name for r in self._ext(ap).review_items], [kept])

	def test_no_copies_for_a_completed_review(self):
		import alvoraa_goals.review_items as review_items

		start, end = self._window()
		cycle = self._cycle(start, end)
		self._kpi(self.employee, cycle)
		ap = self._appraisal(self.employee, cycle, status="Completed")
		# History is copied by the migration as it was stored, never rebuilt from
		# today's live records.
		self.assertFalse(review_items.ensure_review_items(self._ext(ap)))
		self.assertFalse(self._ext(ap).review_items)

	def test_sec21_period_freeze_point_and_removal_setting_are_stamped_when_copies_are_taken(self):
		import alvoraa_goals.review_items as review_items

		start, end = self._window()
		cycle = self._cycle(start, end)
		self._kpi(self.employee, cycle)
		ap = self._appraisal(self.employee, cycle, status="Employee Review")
		try:
			frappe.db.set_single_value("HR Settings", "alvoraa_review_freeze_point", review_items.FREEZE_MANAGER_SENT)
			frappe.db.set_single_value("HR Settings", "alvoraa_review_removal", review_items.REMOVAL_KEEP)
			frappe.db.value_cache.pop("HR Settings", None)
			review_items.ensure_review_items(self._ext(ap))
		finally:
			frappe.db.set_single_value("HR Settings", "alvoraa_review_freeze_point", review_items.FREEZE_HR_SENT)
			frappe.db.set_single_value("HR Settings", "alvoraa_review_removal", review_items.REMOVAL_DISCARD)
			frappe.db.value_cache.pop("HR Settings", None)
			frappe.db.commit()

		# The settings changed back, and the running review keeps what it started with.
		ext = self._ext(ap)
		self.assertEqual(ext.freeze_point, review_items.FREEZE_MANAGER_SENT)
		self.assertEqual(ext.removal_mode, review_items.REMOVAL_KEEP)
		self.assertFalse(ext.frozen)

	def test_r6_freeze_point_steps_and_unknown_values_fail_closed(self):
		import alvoraa_goals.review_items as review_items

		past = review_items.is_past_freeze_point
		self.assertFalse(past("Employee Review", review_items.FREEZE_SELF_SENT))
		self.assertTrue(past("Manager Review", review_items.FREEZE_SELF_SENT))
		self.assertFalse(past("Manager Review", review_items.FREEZE_MANAGER_SENT))
		self.assertTrue(past("Employee Final Review", review_items.FREEZE_MANAGER_SENT))
		self.assertFalse(past("HR Review", review_items.FREEZE_HR_SENT))
		self.assertTrue(past("Completed", review_items.FREEZE_HR_SENT))
		self.assertTrue(past("Employee Review", "whenever"))
		self.assertTrue(past("Somewhere", review_items.FREEZE_HR_SENT))


class TestR4CopiesCountApprovedFactsDatedInThePeriod(_ReviewBase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.employee, cls.user = _subject("facts")

	def _open(self, ap):
		import alvoraa_goals.review_items as review_items

		review_items.ensure_review_items(self._ext(ap))
		return self._ext(ap)

	def test_r4_kpi_cumulative_sums_and_absolute_takes_the_latest_approved_reading(self):
		start, end = self._window()
		cycle = self._cycle(start, end)
		summed = self._kpi(self.employee, cycle, target=100, mode="Cumulative")
		latest = self._kpi(self.employee, cycle, target=100, mode="Absolute")
		lower = self._kpi(self.employee, cycle, target=10, mode="Absolute", direction="Lower is Better")
		for day, value in ((10, 30), (20, 20)):
			self._reading(summed, _day(start, day), value)
		self._reading(summed, _day(start, 25), 100, status="Pending")
		self._reading(summed, _day(start, 26), 50, status="Rejected")
		self._reading(latest, _day(start, 10), 30)
		self._reading(latest, _day(start, 20), 45)
		self._reading(latest, _day(start, 30), 90, status="Pending")
		self._reading(lower, _day(start, 5), 20)
		ext = self._open(self._appraisal(self.employee, cycle))

		row = _row_for(ext, summed)
		self.assertEqual((row.actual_value, row.facts_count, row.attainment_pct), (50, 2, 50))
		row = _row_for(ext, latest)
		self.assertEqual((row.actual_value, row.facts_count), (45, 2))
		# Lower is Better uses the same formula as the KPI itself: target / actual.
		self.assertEqual(_row_for(ext, lower).attainment_pct, 50)

	def test_r3_facts_dated_outside_the_period_do_not_count(self):
		start, end = self._window()
		cycle = self._cycle(start, end)
		kpi = self._kpi(self.employee, cycle, mode="Cumulative")
		narrow = self._kpi(self.employee, cycle, mode="Cumulative", start=_day(start, 15), end=end)
		self._reading(kpi, _day(start, -1), 11)
		self._reading(kpi, _day(end, 1), 13)
		self._reading(kpi, end, 7)
		self._reading(narrow, _day(start, 5), 5)
		self._reading(narrow, _day(start, 20), 9)
		ext = self._open(self._appraisal(self.employee, cycle))

		self.assertEqual(_row_for(ext, kpi).actual_value, 7)
		# The copy's own period narrows the review period.
		self.assertEqual(_row_for(ext, narrow).actual_value, 9)

	def test_r3_new_facts_reach_the_copy_until_it_freezes(self):
		import alvoraa_goals.review_items as review_items

		start, end = self._window()
		cycle = self._cycle(start, end)
		kpi = self._kpi(self.employee, cycle)
		self._reading(kpi, _day(start, 1), 10)
		ap = self._appraisal(self.employee, cycle)
		self._open(ap)

		self._reading(kpi, _day(start, 2), 5)
		self.assertTrue(review_items.refresh_review_items(self._ext(ap)))
		self.assertEqual(_row_for(self._ext(ap), kpi).actual_value, 15)
		self.assertFalse(review_items.refresh_review_items(self._ext(ap)), "nothing changed, nothing written")

		ext = self._ext(ap)
		ext.frozen = 1
		review_items.save_review_record(ext)
		self._reading(kpi, _day(start, 3), 100)
		self.assertFalse(review_items.refresh_review_items(self._ext(ap)))
		self.assertEqual(_row_for(self._ext(ap), kpi).actual_value, 15)

	def test_r4_objective_evidence_is_summed_and_goal_updates_count_as_readings(self):
		start, end = self._window()
		cycle = self._cycle(start, end)
		summed = self._goal(self.employee, cycle, start, end, target=50, mode="Cumulative")
		readings = self._goal(self.employee, cycle, start, end, target=100, mode="Absolute")
		evidence_only = self._goal(self.employee, cycle, start, end, target=100, mode="Absolute")
		self._evidence(summed, 10, extracted_date=_day(start, 1))
		self._evidence(summed, 15, extracted_date=_day(start, 2))
		self._evidence(summed, 99, extracted_date=_day(start, 3), status="Pending")
		self._evidence(summed, 7, extracted_date=_day(end, 5))
		self._goal_update(readings, _day(start, 5), 40)
		self._goal_update(readings, _day(start, 10), 60)
		self._goal_update(readings, _day(start, 12), 90, status="Pending")
		self._evidence(readings, 5, extracted_date=_day(start, 11))
		self._evidence(evidence_only, 20, extracted_date=_day(start, 4))
		self._evidence(evidence_only, 35, extracted_date=_day(start, 8))
		ext = self._open(self._appraisal(self.employee, cycle))

		row = _row_for(ext, summed)
		self.assertEqual((row.actual_value, row.facts_count, row.attainment_pct), (25, 2, 50))
		self.assertEqual(_row_for(ext, readings).actual_value, 60)
		self.assertEqual(_row_for(ext, evidence_only).actual_value, 35)

	def test_decision5_evidence_without_its_own_date_is_dated_by_upload_and_marked(self):
		start, end = self._window()
		cycle = self._cycle(start, end)
		goal = self._goal(self.employee, cycle, start, end, target=100)
		self._evidence(goal, 12, extracted_date=None, upload_date=f"{_day(start, 3)} 10:00:00")
		self._evidence(goal, 8, extracted_date=_day(start, 4))
		self._evidence(goal, 50, extracted_date=None, upload_date=f"{_day(end, 2)} 10:00:00")
		ext = self._open(self._appraisal(self.employee, cycle))

		row = _row_for(ext, goal)
		self.assertEqual((row.actual_value, row.facts_count, row.facts_dated_by_upload), (20, 2, 1))

	def test_r16_overlapping_reviews_split_facts_by_date(self):
		year = random.randint(2100, 2899)
		first = self._cycle(f"{year}-04-01", f"{year}-06-30")
		second = self._cycle(f"{year}-07-01", f"{year}-09-30")
		kpi = self._kpi(self.employee, first, start=f"{year}-04-01", end=f"{year}-09-30")
		self._reading(kpi, f"{year}-06-30", 10)
		self._reading(kpi, f"{year}-07-01", 20)
		q1 = self._appraisal(self.employee, first, status="Manager Review")
		self._open(q1)
		q2 = self._appraisal(self.employee, second)
		# The KPI is tagged to the first cycle, but that review is still open, so
		# the second review copies it too.
		self._open(q2)

		self.assertEqual(_row_for(self._ext(q1), kpi).actual_value, 10)
		self.assertEqual(_row_for(self._ext(q2), kpi).actual_value, 20)


class TestR7RatingStampsAndFlags(_ReviewBase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.employee, cls.user = _subject("stamps")

	def test_r7_a_changed_number_flags_every_rating_given_on_the_old_numbers(self):
		import alvoraa_goals.review_items as review_items

		start, end = self._window()
		cycle = self._cycle(start, end)
		kpi = self._kpi(self.employee, cycle, target=100)
		self._reading(kpi, _day(start, 1), 40)
		ap = self._appraisal(self.employee, cycle, status="Manager Review")
		ext = self._ext(ap)
		review_items.ensure_review_items(ext)

		ext = self._ext(ap)
		row = _row_for(ext, kpi)
		row.self_rating = 3
		review_items.stamp_rating(row, "self")
		row.manager_rating = 4
		review_items.stamp_rating(row, "manager")
		ext.overall_rating = 4
		review_items.stamp_overall_rating(ext)
		review_items.save_review_record(ext)
		frappe.db.commit()

		# Same numbers: nothing is flagged, nothing is written.
		self.assertFalse(review_items.refresh_review_items(self._ext(ap)))
		self.assertEqual(review_items.open_blocking_flags(self._ext(ap)), 0)

		self._reading(kpi, _day(start, 2), 15)
		self.assertTrue(review_items.refresh_review_items(self._ext(ap)))
		ext = self._ext(ap)
		row = _row_for(ext, kpi)
		self.assertEqual((row.self_flag, row.manager_flag, ext.overall_rating_flag), (1, 1, 1))
		# The stamp still says what the rating was given on.
		self.assertEqual((row.manager_basis_actual, row.actual_value), (40, 55))
		# Self-rating flags are information only (decision 13).
		self.assertEqual(review_items.open_blocking_flags(ext), 2)

	def test_sec23_a_rating_with_no_stamp_counts_as_flagged(self):
		import alvoraa_goals.review_items as review_items

		start, end = self._window()
		cycle = self._cycle(start, end)
		kpi = self._kpi(self.employee, cycle)
		ap = self._appraisal(self.employee, cycle, status="Manager Review")
		review_items.ensure_review_items(self._ext(ap))

		ext = self._ext(ap)
		_row_for(ext, kpi).manager_rating = 3
		ext.overall_rating = 2
		self.assertTrue(review_items.raise_rating_flags(ext))
		self.assertEqual(_row_for(ext, kpi).manager_flag, 1)
		self.assertEqual(ext.overall_rating_flag, 1)


class TestQueryCountOfRefresh(_ReviewBase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.employee, cls.user = _subject("querycount")

	def _review_with(self, goals, kpis):
		import alvoraa_goals.review_items as review_items

		start, end = self._window()
		cycle = self._cycle(start, end)
		for _i in range(goals):
			goal = self._goal(self.employee, cycle, start, end)
			self._evidence(goal, 1, extracted_date=_day(start, 1))
		for _i in range(kpis):
			self._reading(self._kpi(self.employee, cycle), _day(start, 1), 1)
		ap = self._appraisal(self.employee, cycle)
		review_items.ensure_review_items(self._ext(ap))
		return ap

	def _queries_to_refresh(self, ap):
		import alvoraa_goals.review_items as review_items

		ext = self._ext(ap)
		with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as sql:
			review_items.refresh_review_items(ext, save=False)
		return sql.call_count

	def test_query_count_refreshing_a_review_does_not_grow_with_its_items(self):
		small = self._queries_to_refresh(self._review_with(goals=1, kpis=2))
		large = self._queries_to_refresh(self._review_with(goals=3, kpis=8))
		self.assertEqual(small, large)
		self.assertLessEqual(large, 6)


# ── SEC-5, PRIV-1, PRIV-2, SEC-6, SEC-10, SEC-27 · Review access (commit 3) ──


def _shipped_permissions(app, *path):
	import importlib
	import os

	root = os.path.dirname(importlib.import_module(app).__file__)
	with open(os.path.join(root, *path), encoding="utf-8-sig") as f:
		return json.load(f)["permissions"]


class _Team(_ReviewBase):
	"""A manager and their report, HR in two companies, a System Manager and a stranger."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company_b = _second_company()
		cls.company_a = ensure_company()

		def person(local, roles, company=None, reports_to=None):
			user = _user(f"d.team.{local}", roles)
			return _employee(f"DTeam{local}", company=company or cls.company_a, reports_to=reports_to, user=user), user

		cls.manager, cls.manager_user = person("manager", ("Employee",))
		cls.subject, cls.subject_user = person("subject", ("Employee",), reports_to=cls.manager)
		cls.stranger, cls.stranger_user = person("stranger", ("Employee",))
		cls.hr, cls.hr_user = person("hr", ("HR Manager", "Employee"))
		cls.hr2, cls.hr2_user = person("hrtwo", ("HR Manager", "Employee"))
		cls.hr_desk, cls.hr_desk_user = person("hrdesk", ("HR User", "Employee"))
		cls.sysman, cls.sysman_user = person("sysman", ("System Manager", "Employee"))
		# An HR Manager with a review of their own, reporting to the manager.
		cls.hr_subject, cls.hr_subject_user = person("hrsubject", ("HR Manager", "Employee"), reports_to=cls.manager)
		cls.subject_b, cls.subject_b_user = person("subjectb", ("Employee",), company=cls.company_b)
		# An HR Manager who is also someone's manager.
		cls.hr_boss, cls.hr_boss_user = person("hrboss", ("HR Manager", "Employee"))
		cls.hr_report, cls.hr_report_user = person("hrreport", ("Employee",), reports_to=cls.hr_boss)

	def _review_of(self, employee, status, company=None, **values):
		start, end = self._window()
		ap = self._appraisal(employee, self._cycle(start, end, company=company), status=status)
		if values:
			frappe.db.set_value("Alvoraa Appraisal Extension", ap, values)
			frappe.db.commit()
		return ap

	def _as(self, user):
		frappe.set_user(user)


class TestSec5ReviewRecordHasNoEmployeeRole(_Team):
	def test_sec5_employee_and_manager_cannot_reach_the_review_record_through_the_desk_or_rest(self):
		from frappe.client import get as desk_get

		roles = {p["role"] for p in _shipped_permissions(
			"alvoraa_goals", "alvoraa_goals", "doctype", "alvoraa_appraisal_extension", "alvoraa_appraisal_extension.json")}
		self.assertNotIn("Employee", roles)
		self.assertNotIn("Employee", {p.role for p in frappe.get_meta("Alvoraa Appraisal Extension").permissions})

		ap = self._review_of(self.subject, "Completed", overall_rating=4, potential_rating=5)
		for user in (self.subject_user, self.manager_user):
			self._as(user)
			with self.assertRaises(frappe.PermissionError, msg=user):
				desk_get("Alvoraa Appraisal Extension", ap)
			# The copies are child rows: they follow the record's permission.
			with self.assertRaises(frappe.PermissionError, msg=user):
				frappe.get_list("Alvoraa Review Item", parent_doctype="Alvoraa Appraisal Extension", fields=["name"])

	def test_m3_report_lists_a_tenant_grant_to_employee_and_changes_nothing(self):
		import alvoraa_goals.review_items as review_items

		grant = frappe.get_doc({
			"doctype": "Custom DocPerm", "parent": "Alvoraa Appraisal Extension", "parenttype": "DocType",
			"parentfield": "permissions", "role": "Employee", "permlevel": 0, "read": 1, "write": 1,
		})
		grant.name = frappe.generate_hash(length=10)
		grant.db_insert()
		try:
			found = review_items.custom_docperm_report()
			self.assertIn(
				("Alvoraa Appraisal Extension", "Employee"), {(r["doctype"], r["role"]) for r in found}
			)
			self.assertTrue(frappe.db.exists("Custom DocPerm", grant.name), "the report must never remove a row")
		finally:
			frappe.db.rollback()

	def test_decision22_employee_cannot_write_or_create_an_hrms_appraisal(self):
		employee = [p for p in _shipped_permissions("hrms", "hr", "doctype", "appraisal", "appraisal.json")
		            if p["role"] == "Employee"]
		# Decision 26 (phase 3) removed read too, so the row is gone; write and
		# create must never come back with it.
		for row in employee:
			self.assertFalse(row.get("write"))
			self.assertFalse(row.get("create"))

	def test_sec27_hr_desk_reads_follow_the_stage_and_company_rule_and_nobody_writes(self):
		from frappe.client import get as desk_get
		from frappe.client import set_value as desk_set_value

		ap = self._review_of(self.subject, "Manager Review")
		self._as(self.hr_desk_user)
		with self.assertRaises(frappe.PermissionError):
			desk_get("Alvoraa Appraisal Extension", ap)
		self.assertNotIn(ap, frappe.get_list("Alvoraa Appraisal Extension", filters={"name": ap}, pluck="name"))

		self._set_status(ap, "HR Review")
		self._as(self.hr_desk_user)
		self.assertEqual(desk_get("Alvoraa Appraisal Extension", ap)["name"], ap)
		self.assertIn(ap, frappe.get_list("Alvoraa Appraisal Extension", filters={"name": ap}, pluck="name"))

		# Another company, and the reader's own review: refused even in HR Review.
		other = self._review_of(self.subject_b, "HR Review", company=self.company_b)
		own = self._review_of(self.hr_desk, "HR Review")
		self._as(self.hr_desk_user)
		for name in (other, own):
			with self.assertRaises(frappe.PermissionError, msg=name):
				desk_get("Alvoraa Appraisal Extension", name)

		# Writes in the desk skip every portal rule, so nobody below Administrator makes one.
		self._as(self.hr_user)
		with self.assertRaises(frappe.PermissionError):
			desk_set_value("Alvoraa Appraisal Extension", ap, "overall_rating", 5)


class TestPriv1SubjectNeverSeesPotential(_Team):
	def test_priv1_subject_never_receives_potential_and_sees_the_overall_rating_from_final_review(self):
		import alvoraa_portal.performance_api as pa

		ap = self._review_of(self.subject, "Manager Review", overall_rating=4, potential_rating=5,
		                     avg_potential_rating=3.5, potential_category="High Potential")
		for status in ("Employee Review", "Manager Review", "Employee Final Review", "HR Review", "Completed"):
			self._set_status(ap, status)
			self._as(self.subject_user)
			ext = pa.get_appraisal_extension(ap)
			self.assertFalse({"avg_potential_rating", "potential_category", "potential_rating"} & set(ext), status)
			own = next(r for r in pa.get_my_appraisals()["own"] if r["name"] == ap)
			if status in ("Employee Final Review", "HR Review", "Completed"):
				self.assertEqual(ext["overall_rating"], 4, status)
				self.assertEqual(own["overall_rating"], 4, status)
			else:
				self.assertIsNone(ext["overall_rating"], status)
				self.assertIsNone(own["overall_rating"], status)
			if status == "Employee Final Review":
				final = pa.get_employee_final_review(ap)
				self.assertFalse({"potential_rating", "potential_category"} & set(final))

		# The manager still sees it.
		self._set_status(ap, "Manager Review")
		self._as(self.manager_user)
		self.assertEqual(pa.get_appraisal_extension(ap)["avg_potential_rating"], 3.5)

	def test_priv1_team_reviews_hide_your_own_potential_and_strangers_ratings_before_hr_review(self):
		import alvoraa_portal.performance_api as pa

		start, end = self._window()
		cycle = self._cycle(start, end)
		own = self._appraisal(self.hr, cycle, status="Manager Review")
		theirs = self._appraisal(self.stranger, cycle, status="Manager Review")
		for ap in (own, theirs):
			frappe.db.set_value("Alvoraa Appraisal Extension", ap, {"overall_rating": 4, "potential_rating": 5})
		frappe.db.commit()

		def rows():
			self._as(self.hr_user)
			return {r["employee"]: r for r in pa.get_team_reviews(cycle)["team"]}

		team = rows()
		self.assertEqual((team[self.hr]["overall_rating"], team[self.hr]["potential_rating"]), (None, None))
		self.assertEqual((team[self.stranger]["overall_rating"], team[self.stranger]["potential_rating"]), (None, None))

		self._set_status(own, "Completed")
		self._set_status(theirs, "HR Review")
		team = rows()
		self.assertEqual((team[self.hr]["overall_rating"], team[self.hr]["potential_rating"]), (4, None))
		self.assertEqual((team[self.stranger]["overall_rating"], team[self.stranger]["potential_rating"]), (4, 5))


class TestPriv2Sec6ManagerReviewOrder(_Team):
	def test_priv2_nobody_else_opens_a_self_review_before_it_is_sent_or_after_it_is_returned(self):
		import alvoraa_portal.performance_api as pa

		marker = f"{TAG}-DRAFT-{_uid()}"
		ap = self._review_of(self.subject, "Employee Review", achievements_text=marker,
		                     page_data=json.dumps({"past-dev": {"achievements": marker}}))

		self._as(self.manager_user)
		with self.assertRaises(frappe.PermissionError):
			pa.get_manager_review(ap)
		self.assertNotIn(marker, json.dumps(pa.get_appraisal_extension(ap)))
		# An HR person who is also the manager does not get round it through the
		# employee's own screen.
		line_ap = self._review_of(self.hr_report, "Employee Review", achievements_text=marker)
		self._as(self.hr_boss_user)
		with self.assertRaises(frappe.PermissionError):
			pa.get_my_review(line_ap)
		with self.assertRaises(frappe.PermissionError):
			pa.get_manager_review(line_ap)

		self._as(self.subject_user)
		pa.submit_employee_review(ap)
		self._as(self.manager_user)
		self.assertIn(marker, json.dumps(pa.get_manager_review(ap)["page_data"]))

		pa.return_for_revision(ap, "")
		self._as(self.manager_user)
		with self.assertRaises(frappe.PermissionError):
			pa.get_manager_review(ap)

	def test_sec6_calls_from_people_who_may_not_act_create_no_review_record(self):
		import alvoraa_portal.performance_api as pa

		start, end = self._window()
		ap = self._appraisal(self.subject, self._cycle(start, end), with_extension=False)
		calls = [
			lambda: pa.get_manager_review(ap),
			lambda: pa.save_manager_review(ap, "x"),
			lambda: pa.submit_manager_review(ap, "x"),
			lambda: pa.save_overall_rating(ap, 3),
			lambda: pa.invite_reviewer(ap, self.hr),
			lambda: pa.invite_reviewers_batch(ap, "[]"),
			lambda: pa.advance_review_status(ap),
			lambda: pa.return_for_revision(ap, ""),
			lambda: pa.add_action_item(ap, "x"),
			lambda: pa.update_action_item_status(ap, "nope", "Open"),
			lambda: pa.get_reviewer_view(ap),
			lambda: pa.submit_reviewer_comments(ap, "x"),
			lambda: pa.get_employee_final_review(ap),
			lambda: pa.acknowledge_final_review(ap),
			lambda: pa.get_appraisal_extension(ap),
		]
		for user in (self.stranger_user, self.hr_user):
			for i, call in enumerate(calls):
				self._as(user)
				try:
					call()
				except (frappe.PermissionError, frappe.ValidationError):
					pass
				else:
					if user == self.stranger_user:
						self.fail(f"call {i} was allowed for a stranger")
				frappe.set_user("Administrator")
				self.assertEqual(frappe.db.count("Alvoraa Appraisal Extension", {"appraisal": ap}), 0, f"{user} call {i}")

		# And the stranger is refused as a permission matter, not a stage message.
		self._as(self.stranger_user)
		for i, call in enumerate(calls):
			with self.assertRaises(frappe.PermissionError, msg=f"call {i}"):
				call()

	def test_manager_draft_save_keeps_the_ratings_already_given(self):
		import alvoraa_portal.performance_api as pa

		ap = self._review_of(self.subject, "Manager Review")
		self._as(self.manager_user)
		pa.save_manager_review(ap, "first", "notes", overall_rating=4, potential_rating=3)
		# What "Save draft" sends when the manager did not touch the ratings.
		pa.save_manager_review(ap, "second", "notes", overall_rating=0, potential_rating="0")

		frappe.set_user("Administrator")
		ext = self._ext(ap)
		self.assertEqual((ext.manager_feedback, ext.overall_rating, ext.potential_rating), ("second", 4, 3))
		self.assertEqual(ext.overall_rated_by, self.manager_user)
		self.assertTrue(ext.overall_rating_basis)


class TestSec10NobodyRatesTheirOwnReview(_Team):
	def test_sec10_an_hr_manager_cannot_rate_calibrate_or_close_their_own_review(self):
		import alvoraa_portal.performance_api as pa

		start, end = self._window()
		cycle = self._cycle(start, end)
		kpi = self._kpi(self.hr_subject, cycle)
		ap = self._appraisal(self.hr_subject, cycle, status="Manager Review")

		self._as(self.hr_subject_user)
		for name, call in (
			("get_manager_review", lambda: pa.get_manager_review(ap)),
			("save_manager_review", lambda: pa.save_manager_review(ap, "x", overall_rating=5)),
			("submit_manager_review", lambda: pa.submit_manager_review(ap, "x", overall_rating=5)),
			("save_overall_rating", lambda: pa.save_overall_rating(ap, 5)),
			("invite_reviewer", lambda: pa.invite_reviewer(ap, self.stranger)),
			("return_for_revision", lambda: pa.return_for_revision(ap, "")),
			("advance_review_status", lambda: pa.advance_review_status(ap)),
			("submit_appraisal", lambda: pa.submit_appraisal(ap)),
			("sync_appraisal_from_kpis", lambda: pa.sync_appraisal_from_kpis(ap)),
			("suggest_ratings", lambda: pa.suggest_ratings(self.hr_subject, cycle)),
			("save_kpi_manager_review", lambda: pa.save_kpi_manager_review(kpi, 5)),
		):
			with self.assertRaises(frappe.PermissionError, msg=name):
				call()

		self._set_status(ap, "HR Review")
		self._as(self.hr_subject_user)
		for name, call in (
			("advance_review_status", lambda: pa.advance_review_status(ap)),
			("save_calibration_note", lambda: pa.save_calibration_note(ap, "", 5)),
		):
			with self.assertRaises(frappe.PermissionError, msg=name):
				call()
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Alvoraa Appraisal Extension", ap, "review_status"), "HR Review")
		self.assertFalse(frappe.db.get_value("Alvoraa Appraisal Extension", ap, "overall_rating"))

		# Another HR Manager closes it.
		self._as(self.hr2_user)
		self.assertEqual(pa.advance_review_status(ap)["review_status"], "Completed")


class TestDecisions15And16HrScope(_Team):
	def test_decision15_system_manager_follows_the_stage_rule(self):
		import alvoraa_portal.performance_api as pa

		ap = self._review_of(self.subject, "Manager Review")
		self._as(self.sysman_user)
		with self.assertRaises(frappe.PermissionError):
			pa._assert_hr_can_view(ap)
		self._set_status(ap, "HR Review")
		self._as(self.sysman_user)
		pa._assert_hr_can_view(ap)

	def test_decision16_hr_acts_only_for_the_companies_they_look_after(self):
		import alvoraa_portal.performance_api as pa

		start, end = self._window()
		mine = self._appraisal(self.subject, self._cycle(start, end), status="HR Review")
		elsewhere = self._appraisal(self.subject_b, self._cycle(start, end, company=self.company_b), status="HR Review")

		self._as(self.hr_user)
		pa._assert_hr_can_view(mine)
		with self.assertRaises(frappe.PermissionError):
			pa._assert_hr_can_view(elsewhere)
		with self.assertRaises(frappe.PermissionError):
			pa.advance_review_status(elsewhere)
		names = {r["name"] for r in pa.list_appraisals()["appraisals"]}
		self.assertIn(mine, names)
		self.assertNotIn(elsewhere, names)
		team = {r["employee"] for r in pa.get_team_reviews()["team"]}
		self.assertIn(self.subject, team)
		self.assertNotIn(self.subject_b, team)


class TestHrStandInManager(_Team):
	def test_the_hr_stand_in_for_a_manager_less_employee_reviews_in_manager_review_but_is_not_exempt_elsewhere(self):
		"""get_effective_manager makes the first HR Manager the manager of anyone
		with no manager. That must let them do the manager review, and must NOT
		let them read that person's review at other stages through the HR guard."""
		import alvoraa_portal.performance_api as pa
		from alvoraa_goals.permissions import get_hr_manager_employee

		stand_in = get_hr_manager_employee()
		if not stand_in:
			self.skipTest("no HR Manager employee on this site")
		stand_in_user = frappe.db.get_value("Employee", stand_in, "user_id")
		company = frappe.db.get_value("Employee", stand_in, "company")
		user = _user(f"d.nomanager.{_uid()}", ("Employee",))
		lone = _employee(f"DNoManager{_uid()}", company=company, user=user)
		self._cleanup.append(("Employee", lone))

		ap = self._review_of(lone, "Manager Review", company=company)
		self._as(stand_in_user)
		pa.get_manager_review(ap)
		pa.save_manager_review(ap, "feedback", overall_rating=3)

		self._set_status(ap, "Employee Review")
		self._as(stand_in_user)
		with self.assertRaises(frappe.PermissionError):
			pa._assert_hr_can_view(ap)


class TestScorecardsHideUnreleasedRatings(_Team):
	def test_scorecards_show_an_overall_rating_only_once_it_is_released(self):
		import alvoraa_portal.hr_api as hr_api

		start, end = self._window()
		cycle = self._cycle(start, end)
		ap = self._appraisal(self.subject, cycle, status="Manager Review")
		frappe.db.set_value("Alvoraa Appraisal Extension", ap, "overall_rating", 4)
		frappe.db.commit()

		def seen():
			self._as(self.manager_user)
			history = [r for r in hr_api.get_employee_scorecard(self.subject)["appraisal_history"]
			           if r["cycle_label"] == cycle]
			member = next(m for m in hr_api.get_team_scorecard()["members"] if m["name"] == self.subject)
			return history[0]["overall_rating"], member["appraisal_rating"]

		self.assertEqual(seen(), ("", ""))
		self._set_status(ap, "Employee Final Review")
		self.assertEqual(seen(), (4, 4))
