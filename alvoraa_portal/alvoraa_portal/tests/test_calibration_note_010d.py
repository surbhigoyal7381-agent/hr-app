"""Slice 010 group D, decisions 35 and 36 (finding F-D8).

Decision 35: saving a calibration note used to fail for everyone, because the
review record (Alvoraa Appraisal Extension) had no `calibration_notes` field.
The field now exists and `save_calibration_note` sets it like any other field.

Calibration notes are HR-stage content (01c: "Manager line, HR. Never the
subject"). No portal screen returns them. In the desk and in the review's change
history (Version rows) they follow the review record's own rule: HR for the
companies they look after from HR Review on, never the subject, and nobody
without an HR role.

Decision 36: the HR stand-in (the HR Manager treated as manager for someone with
no manager) stays refused, like everyone else in the subject's line (decision 34).

Starts from the shipped permissions, like the other 010 tests. Synthetic people
and records only, tagged S010D.
"""

import json

import frappe

from alvoraa_portal.tests.test_portal_security_010 import _employee, _user
from alvoraa_portal.tests.test_review_copies_010d import _shipped_permissions, _uid
from alvoraa_portal.tests.test_review_line_hr_010d import ASK_ANOTHER, _LineHr

EXTENSION = "Alvoraa Appraisal Extension"


class _Notes(_LineHr):
	def _marker(self):
		return f"S010D calibration note {_uid()}"

	def _save_note(self, user, ap, note, rating=None):
		import alvoraa_portal.performance_api as pa

		self._as(user)
		try:
			return pa.save_calibration_note(ap, note, rating)
		finally:
			frappe.set_user("Administrator")

	def _portal_text(self, user, calls):
		"""Everything the given portal calls return to `user`, as one string."""
		out = []
		self._as(user)
		try:
			for call in calls:
				out.append(json.dumps(call(), default=str))
		finally:
			frappe.set_user("Administrator")
		return "\n".join(out)

	def _desk_reads_note(self, user, ap, marker):
		"""Can `user` see the note through the desk or REST, by name or by list?"""
		from frappe.client import get as desk_get

		self._as(user)
		try:
			try:
				if marker in json.dumps(desk_get(EXTENSION, ap), default=str):
					return True
			except frappe.PermissionError:
				pass
			try:
				rows = frappe.get_list(EXTENSION, filters={"name": ap}, fields=["name", "calibration_notes"])
			except frappe.PermissionError:
				rows = []
			return any(marker in (r.get("calibration_notes") or "") for r in rows)
		finally:
			frappe.set_user("Administrator")

	def _version_readable(self, user, name):
		from frappe.client import get as desk_get

		self._as(user)
		try:
			listed = name in frappe.get_list("Version", filters={"name": name}, pluck="name")
		except frappe.PermissionError:
			listed = False
		try:
			desk_get("Version", name)
			read = True
		except frappe.PermissionError:
			read = False
		finally:
			frappe.set_user("Administrator")
		return listed or read

	def _version_with_note(self, ap, marker):
		"""A real Version row that records a note change.

		Frappe skips Version rows while tests run, so this save asks for one; it is
		the row HR's portal save leaves on a live site (track_changes is on).
		"""
		ext = self._ext(ap)
		ext.calibration_notes = marker
		ext.save(ignore_version=False)
		frappe.db.commit()
		name = frappe.get_all(
			"Version", filters={"ref_doctype": EXTENSION, "docname": ap},
			order_by="creation desc", limit=1, pluck="name",
		)[0]
		self._cleanup.append(("Version", name))
		self.assertIn(marker, frappe.db.get_value("Version", name, "data"))
		return name


class TestD35TheFieldShips(_Notes):
	def test_d35_the_review_record_ships_a_calibration_notes_field_and_no_employee_role(self):
		import os
		import importlib

		root = os.path.dirname(importlib.import_module("alvoraa_goals").__file__)
		path = os.path.join(root, "alvoraa_goals", "doctype", "alvoraa_appraisal_extension",
		                    "alvoraa_appraisal_extension.json")
		with open(path, encoding="utf-8-sig") as f:
			shipped = json.load(f)
		field = [f for f in shipped["fields"] if f["fieldname"] == "calibration_notes"]
		self.assertEqual(len(field), 1)
		self.assertIn(field[0]["fieldtype"], ("Text", "Small Text", "Long Text"))
		self.assertIn("calibration_notes", shipped["field_order"])
		self.assertTrue(frappe.get_meta(EXTENSION).has_field("calibration_notes"), "run bench migrate")
		self.assertNotIn("Employee", {p["role"] for p in _shipped_permissions(
			"alvoraa_goals", "alvoraa_goals", "doctype", "alvoraa_appraisal_extension", "alvoraa_appraisal_extension.json")})


class TestD35HrSavesTheNote(_Notes):
	def test_d35_an_eligible_hr_person_saves_a_note_and_a_calibrated_rating_and_both_persist(self):
		r = self._review_for(self.subject, self.subject_user, "HR Review")
		marker = self._marker()
		result = self._save_note(self.hr_user, r.ap, marker, 2)
		self.assertEqual(result["message"], "Calibration note saved.")

		frappe.db.rollback()   # read what was committed, not what is in memory
		stored = frappe.db.get_value(
			EXTENSION, r.ap, ["calibration_notes", "overall_rating", "overall_rated_by", "review_status"], as_dict=True)
		self.assertEqual(stored.calibration_notes, marker)
		self.assertEqual(stored.overall_rating, 2)
		self.assertEqual(stored.overall_rated_by, self.hr_user)
		self.assertEqual(stored.review_status, "HR Review")

		# A second save replaces the note; a note with no rating keeps the rating.
		self._save_note(self.hr_user, r.ap, marker + " (revised)")
		stored = frappe.db.get_value(EXTENSION, r.ap, ["calibration_notes", "overall_rating"], as_dict=True)
		self.assertEqual((stored.calibration_notes, stored.overall_rating), (marker + " (revised)", 2))

	def test_d35_a_note_that_is_not_text_is_refused(self):
		r = self._review_for(self.subject, self.subject_user, "HR Review")
		with self.assertRaises(frappe.ValidationError):
			self._save_note(self.hr_user, r.ap, {"not": "text"})
		frappe.db.rollback()
		self.assertFalse(frappe.db.get_value(EXTENSION, r.ap, "calibration_notes"))

	def test_d35_the_note_is_saved_only_in_hr_review(self):
		r = self._review_for(self.subject, self.subject_user, "Manager Review")
		for status in ("Manager Review", "Employee Final Review", "Completed"):
			self._set_status(r.ap, status)
			with self.assertRaises((frappe.ValidationError, frappe.PermissionError), msg=status):
				self._save_note(self.hr_user, r.ap, self._marker())
			frappe.db.rollback()
			self.assertFalse(frappe.db.get_value(EXTENSION, r.ap, "calibration_notes"), status)


class TestD35TheSubjectAndManagerNeverReadTheNote(_Notes):
	def test_d35_portal_screens_never_return_the_note_to_the_subject_or_the_manager(self):
		import alvoraa_portal.goals_api as ga
		import alvoraa_portal.performance_api as pa

		r = self._review_for(self.subject, self.subject_user, "HR Review")
		marker = self._marker()
		self._save_note(self.hr_user, r.ap, marker, 3)
		self.assertEqual(frappe.db.get_value(EXTENSION, r.ap, "calibration_notes"), marker)

		# HR Review, Completed, and back in Manager Review after a send-back.
		for status in ("HR Review", "Completed", "Manager Review"):
			self._set_status(r.ap, status)
			subject_sees = self._portal_text(self.subject_user, (
				lambda: pa.get_my_review(r.ap),
				ga.get_appraisal_data,
			))
			manager_sees = self._portal_text(self.manager_user, (
				lambda: pa.get_manager_review(r.ap),
				lambda: pa.get_team_reviews(r.cycle),
			))
			self.assertNotIn(marker, subject_sees, f"subject at {status}")
			self.assertNotIn("calibration_notes", subject_sees, f"subject at {status}")
			self.assertNotIn(marker, manager_sees, f"manager at {status}")
			self.assertNotIn("calibration_notes", manager_sees, f"manager at {status}")

		# HR's own screens do not echo it either: the note is written, not listed.
		self._set_status(r.ap, "HR Review")
		hr_sees = self._portal_text(self.hr_user, (
			lambda: pa.hr_list_appraisals(r.cycle),
			lambda: pa.get_calibration_overview(r.cycle),
			lambda: pa.export_cycle_kpis_csv(r.cycle),
		))
		self.assertNotIn(marker, hr_sees)

	def test_d35_rest_and_version_rows_follow_the_review_rule_even_for_a_subject_with_an_hr_role(self):
		# hr_subject holds HR Manager and reports to manager, who holds no HR role.
		r = self._review_for(self.hr_subject, self.hr_subject_user, "HR Review")
		self._save_note(self.hr_user, r.ap, self._marker())
		# A second, different note, so the save changes the field and Frappe
		# writes a Version row holding the new text.
		marker = self._marker()
		version = self._version_with_note(r.ap, marker)

		# The subject (with an HR role) and their manager (without) read neither.
		for user in (self.hr_subject_user, self.manager_user):
			self.assertFalse(self._desk_reads_note(user, r.ap, marker), user)
			self.assertFalse(self._version_readable(user, version), user)

		# In HR Review the rule lets HR for the company read the record, and a
		# System Manager its history - so the checks above are not empty.
		self.assertTrue(self._desk_reads_note(self.hr_user, r.ap, marker))
		self.assertTrue(self._version_readable(self.sysman_user, version))

		# Sent back to Manager Review, HR outside the line reads neither again.
		self._set_status(r.ap, "Manager Review")
		self.assertFalse(self._desk_reads_note(self.hr_user, r.ap, marker))
		self.assertFalse(self._version_readable(self.sysman_user, version))
		for user in (self.hr_subject_user, self.manager_user):
			self.assertFalse(self._desk_reads_note(user, r.ap, marker), user)
			self.assertFalse(self._version_readable(user, version), user)

	def test_d35_nobody_below_administrator_writes_the_note_from_the_desk(self):
		from frappe.client import set_value as desk_set_value

		r = self._review_for(self.subject, self.subject_user, "HR Review")
		for user in (self.hr_user, self.sysman_user, self.subject_user):
			self._as(user)
			try:
				with self.assertRaises((frappe.PermissionError, frappe.ValidationError), msg=user):
					desk_set_value(EXTENSION, r.ap, "calibration_notes", "desk edit")
			finally:
				frappe.set_user("Administrator")
			frappe.db.rollback()
		self.assertFalse(frappe.db.get_value(EXTENSION, r.ap, "calibration_notes"))


class TestD34D36TheLineStillDoesNotCalibrate(_Notes):
	def test_d34_the_hr_person_in_the_subjects_line_is_refused_and_no_note_is_stored(self):
		r = self._review_for(self.hr_report, self.hr_report_user, "HR Review")
		with self.assertRaises(frappe.PermissionError) as refused:
			self._save_note(self.hr_boss_user, r.ap, self._marker(), 5)
		self.assertIn(ASK_ANOTHER, str(refused.exception))
		frappe.db.rollback()
		stored = frappe.db.get_value(EXTENSION, r.ap, ["calibration_notes", "overall_rating"], as_dict=True)
		self.assertFalse(stored.calibration_notes)
		self.assertFalse(stored.overall_rating)

	def test_d36_the_hr_stand_in_for_someone_with_no_manager_is_refused_calibration(self):
		from alvoraa_goals.permissions import get_hr_manager_employee

		stand_in = get_hr_manager_employee()
		if not stand_in:
			self.skipTest("no HR Manager employee on this site")
		stand_in_user = frappe.db.get_value("Employee", stand_in, "user_id")
		company = frappe.db.get_value("Employee", stand_in, "company")
		user = _user(f"d.note.lone.{_uid()}", ("Employee",))
		lone = _employee(f"DNoteLone{_uid()}", company=company, user=user)
		self._cleanup.append(("Employee", lone))
		ap = self._review_of(lone, "HR Review", company=company)
		with self.assertRaises(frappe.PermissionError) as refused:
			self._save_note(stand_in_user, ap, self._marker(), 5)
		self.assertIn(ASK_ANOTHER, str(refused.exception))
		frappe.db.rollback()
		self.assertFalse(frappe.db.get_value(EXTENSION, ap, "calibration_notes"))
