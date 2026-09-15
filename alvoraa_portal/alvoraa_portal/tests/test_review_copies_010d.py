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
		frappe.db.value_cache.pop("HR Settings", None)
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

		versions = frappe.db.count("Version", {"ref_doctype": "HR Settings"})
		doc = frappe.get_doc("HR Settings")
		doc.alvoraa_review_freeze_point = "Manager review sent"
		doc.save()
		self.assertEqual(frappe.db.count("Version", {"ref_doctype": "HR Settings"}), versions + 1)


# ── KPI indexes and change history (commit 1; slice 012 relies on the indexes) ─


class TestKpiIndexesAndHistory(_ReviewBase):
	def test_kpi_is_indexed_by_employee_and_cycle_and_keeps_change_history(self):
		meta = frappe.get_meta("KPI")
		self.assertTrue(meta.get_field("employee").search_index)
		self.assertTrue(meta.get_field("appraisal_cycle").search_index)
		# The write-back at completion needs a before/after record on the KPI.
		self.assertTrue(meta.track_changes)
		self.assertTrue(frappe.db.has_index("tabKPI", "employee"))
		self.assertTrue(frappe.db.has_index("tabKPI", "appraisal_cycle"))
