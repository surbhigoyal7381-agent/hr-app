"""Slice 010 group D fix round: pin tests for the code review (05) and security
review (06) findings.

Each test is named after the finding it keeps closed (B1, M1..M5, m1..m8 from the
security review; CR-M1..CR-M5 and CR-minor 1..9 from the code review; RR for the
release risks), so a merge that drops a fix fails CI here. Refusals are tested,
not only the allowed path. Synthetic people and records only, tagged S010D.
"""

import json

import frappe
from frappe.utils import now_datetime

from alvoraa_portal.tests.test_portal_security_010 import _user
from alvoraa_portal.tests.test_review_copies_010d import _day, _row_for, _uid
from alvoraa_portal.tests.test_review_screens_010d import _Screens

TAG = "S010D"


def _history_row(doctype, ref_doctype, ref_name, marker):
	"""A Version or Comment row about a record, written straight to the table.

	Frappe skips Version rows while tests run, so the test writes the row a real
	save would leave.
	"""
	if doctype == "Version":
		values = {"ref_doctype": ref_doctype, "docname": ref_name,
		          "data": json.dumps({"changed": [["potential_rating", 0, 5]], "marker": marker})}
	else:
		values = {"comment_type": "Info", "reference_doctype": ref_doctype, "reference_name": ref_name,
		          "content": f"Reason: {marker}"}
	doc = frappe.get_doc(dict(values, doctype=doctype))
	doc.name = frappe.generate_hash(length=10)
	doc.owner = "Administrator"
	doc.creation = doc.modified = now_datetime()
	doc.db_insert()
	frappe.db.commit()
	return doc.name


# ── Security B1 · Version and Comment rows follow the review record's rule ──


class TestB1ReviewHistoryAndNotes(_Screens):
	def _rows_about(self, doctype, ref_doctype, ref_name):
		marker = f"{TAG}-B1-{_uid()}"
		name = _history_row(doctype, ref_doctype, ref_name, marker)
		self._cleanup.append((doctype, name))
		return name

	def _listed(self, user, doctype, name):
		self._as(user)
		try:
			return name in frappe.get_list(doctype, filters={"name": name}, pluck="name")
		except frappe.PermissionError:
			return False
		finally:
			frappe.set_user("Administrator")

	def _readable(self, user, doctype, name):
		from frappe.client import get as desk_get

		self._as(user)
		try:
			desk_get(doctype, name)
			return True
		except frappe.PermissionError:
			return False
		finally:
			frappe.set_user("Administrator")

	def test_b1_history_and_notes_of_a_review_follow_its_stage_company_and_own_rule(self):
		website_manager = _user(f"d.webman.{_uid()}", ("Website Manager",))
		review = self._review("Manager Review")
		ap = review.ap
		copy = _row_for(self._ext(ap), review.alone).name
		rows = {
			("Version", "ext"): self._rows_about("Version", "Alvoraa Appraisal Extension", ap),
			("Comment", "ext"): self._rows_about("Comment", "Alvoraa Appraisal Extension", ap),
			("Version", "copy"): self._rows_about("Version", "Alvoraa Review Item", copy),
			("Version", "appraisal"): self._rows_about("Version", "Appraisal", ap),
			("Comment", "appraisal"): self._rows_about("Comment", "Appraisal", ap),
		}

		# Manager Review: the System Manager outside the line, HR, and a Website
		# Manager read none of it, by list or by name.
		for user in (self.sysman_user, self.hr_user, website_manager):
			for (doctype, what), name in rows.items():
				if user == website_manager and doctype == "Version":
					continue
				self.assertFalse(self._listed(user, doctype, name), f"{user} lists {doctype} {what}")
				self.assertFalse(self._readable(user, doctype, name), f"{user} reads {doctype} {what}")

		# HR Review: HR for the subject's company and the System Manager read it;
		# a Website Manager still does not; HR for another company does not.
		self._set_status(ap, "HR Review")
		for (doctype, what), name in rows.items():
			for user in (self.hr_user, self.sysman_user):
				self.assertTrue(self._listed(user, doctype, name), f"{user} lists {doctype} {what}")
				self.assertTrue(self._readable(user, doctype, name), f"{user} reads {doctype} {what}")
		self.assertFalse(self._listed(website_manager, "Comment", rows[("Comment", "ext")]))

		# Nobody below Administrator edits or deletes a review's audit note.
		from frappe.client import delete as desk_delete
		from frappe.client import set_value as desk_set_value

		self._as(self.sysman_user)
		with self.assertRaises(frappe.PermissionError):
			desk_set_value("Comment", rows[("Comment", "ext")], "content", "rewritten")
		with self.assertRaises(frappe.PermissionError):
			desk_delete("Comment", rows[("Comment", "ext")])

	def test_b1_a_system_manager_never_reads_their_own_reviews_history(self):
		ap = self._review_of(self.sysman, "HR Review")
		version = self._rows_about("Version", "Alvoraa Appraisal Extension", ap)
		comment = self._rows_about("Comment", "Alvoraa Appraisal Extension", ap)
		for doctype, name in (("Version", version), ("Comment", comment)):
			self.assertFalse(self._listed(self.sysman_user, doctype, name), doctype)
			self.assertFalse(self._readable(self.sysman_user, doctype, name), doctype)

	def test_b1_history_and_notes_of_other_doctypes_are_untouched(self):
		website_manager = _user(f"d.webman.{_uid()}", ("Website Manager",))
		todo = frappe.get_doc({"doctype": "ToDo", "description": f"{TAG} B1"}).insert(ignore_permissions=True)
		self._cleanup.append(("ToDo", todo.name))
		version = self._rows_about("Version", "ToDo", todo.name)
		comment = self._rows_about("Comment", "ToDo", todo.name)
		self.assertTrue(self._listed(self.sysman_user, "Version", version))
		self.assertTrue(self._readable(self.sysman_user, "Version", version))
		for user in (self.sysman_user, website_manager):
			self.assertTrue(self._listed(user, "Comment", comment), user)
			self.assertTrue(self._readable(user, "Comment", comment), user)

		# A list with no filter still works and still leaves out the review's rows.
		review_note = self._rows_about("Comment", "Alvoraa Appraisal Extension", self._review_of(self.subject, "Manager Review"))
		self._as(self.sysman_user)
		names = frappe.get_list("Comment", fields=["name"], limit_page_length=0, pluck="name")
		frappe.set_user("Administrator")
		self.assertIn(comment, names)
		self.assertNotIn(review_note, names)

	def test_b1_the_hooks_are_registered_for_version_and_comment(self):
		for key in ("permission_query_conditions", "has_permission"):
			hooks = frappe.get_hooks(key)
			for doctype in ("Version", "Comment", "Appraisal"):
				self.assertTrue(
					any(m.startswith("alvoraa_goals.permissions.") for m in hooks.get(doctype, [])),
					f"{key} {doctype}",
				)


# ── Security M4 · HRMS Appraisal in the desk follows the review's rule ──────


class TestM4HrmsAppraisalInTheDesk(_Screens):
	def _sees(self, user, ap):
		from frappe.client import get as desk_get

		self._as(user)
		try:
			listed = ap in frappe.get_list("Appraisal", filters={"name": ap}, pluck="name")
			try:
				desk_get("Appraisal", ap)
				read = True
			except frappe.PermissionError:
				read = False
			return listed, read
		finally:
			frappe.set_user("Administrator")

	def test_m4_hr_reads_appraisal_scores_only_under_the_stage_and_company_rule(self):
		ap = self._review_of(self.subject, "Manager Review")
		for user in (self.hr_desk_user, self.hr_user, self.sysman_user):
			self.assertEqual(self._sees(user, ap), (False, False), user)

		self._set_status(ap, "HR Review")
		for user in (self.hr_desk_user, self.hr_user, self.sysman_user):
			self.assertEqual(self._sees(user, ap), (True, True), user)

		# Another company, even in HR Review; and never your own.
		other = self._review_of(self.subject_b, "HR Review", company=self.company_b)
		self.assertEqual(self._sees(self.hr_desk_user, other), (False, False))
		own = self._review_of(self.hr_desk, "Completed")
		self.assertEqual(self._sees(self.hr_desk_user, own), (False, False))

	def test_m4_a_manager_who_holds_hr_sees_their_report_once_the_self_review_is_sent(self):
		ap = self._review_of(self.hr_report, "Employee Review")
		self.assertEqual(self._sees(self.hr_boss_user, ap), (False, False))
		self._set_status(ap, "Manager Review")
		self.assertEqual(self._sees(self.hr_boss_user, ap), (True, True))

	def test_m4_a_submitted_appraisal_with_no_review_record_is_history(self):
		start, end = self._window()
		ap = self._appraisal(self.subject, self._cycle(start, end), with_extension=False)
		self.assertEqual(self._sees(self.hr_desk_user, ap), (False, False))
		frappe.db.set_value("Appraisal", ap, "docstatus", 1)
		frappe.db.commit()
		self.assertEqual(self._sees(self.hr_desk_user, ap), (True, True))
		frappe.db.set_value("Appraisal", ap, "docstatus", 0)
		frappe.db.commit()


# ── Security M1 · the older scoring calls follow the stage and company rule ─


class TestM1ScoringCallsFollowTheStageAndCompanyRule(_Screens):
	def _calls(self, ap, employee, cycle):
		import alvoraa_portal.performance_api as pa

		return (
			("suggest_ratings", lambda: pa.suggest_ratings(employee, cycle)),
			("sync_appraisal_from_kpis", lambda: pa.sync_appraisal_from_kpis(ap)),
			("submit_appraisal", lambda: pa.submit_appraisal(ap)),
		)

	def _refused(self, user, ap, employee, cycle):
		refused = []
		for name, call in self._calls(ap, employee, cycle):
			self._as(user)
			try:
				call()
			except frappe.PermissionError:
				refused.append(name)
			except frappe.ValidationError:
				pass   # allowed in, then stopped by the data (nothing weighted)
			finally:
				frappe.set_user("Administrator")
		return refused

	def test_m1_hr_for_another_company_is_refused_at_every_stage(self):
		start, end = self._window()
		cycle = self._cycle(start, end, company=self.company_b)
		self._kpi(self.subject_b, cycle, target=10)
		ap = self._appraisal(self.subject_b, cycle, status="Manager Review")
		self.assertEqual(len(self._refused(self.hr_user, ap, self.subject_b, cycle)), 3)
		self._set_status(ap, "HR Review")
		self.assertEqual(len(self._refused(self.hr_user, ap, self.subject_b, cycle)), 3)
		self.assertEqual(frappe.db.get_value("Appraisal", ap, "docstatus"), 0)

	def test_m1_hr_outside_the_line_waits_for_hr_review(self):
		review = self._review("Manager Review")
		self.assertEqual(len(self._refused(self.hr_user, review.ap, self.subject, review.cycle)), 3)
		self._set_status(review.ap, "HR Review")
		self.assertEqual(self._refused(self.hr_user, review.ap, self.subject, review.cycle), [])

	def test_m1_priv2_nobody_scores_a_self_review_that_has_not_been_sent(self):
		import alvoraa_portal.performance_api as pa

		review = self._review("Employee Review")
		self.assertEqual(len(self._refused(self.manager_user, review.ap, self.subject, review.cycle)), 3)
		self._set_status(review.ap, "Manager Review")
		self._as(self.manager_user)
		suggested = pa.suggest_ratings(self.subject, review.cycle)
		frappe.set_user("Administrator")
		self.assertEqual(len(suggested), 2)


# ── Security M2 · a rename cannot step round the lock ───────────────────────


class TestM2RenameWhileHeld(_Screens):
	def test_m2_a_held_kpi_cannot_be_renamed_and_copies_follow_a_later_rename(self):
		review = self._review("Manager Review")
		new_name = f"{review.alone}-{_uid()}"
		with self.assertRaises(frappe.PermissionError):
			frappe.rename_doc("KPI", review.alone, new_name, force=True)
		self.assertTrue(frappe.db.exists("KPI", review.alone))

		# Once the review is completed the lock is gone; the copy follows the rename.
		self._set_status(review.ap, "Completed")
		frappe.rename_doc("KPI", review.alone, new_name, force=True)
		frappe.db.commit()
		self._cleanup.append(("KPI", new_name))
		self.assertIsNone(_row_for(self._ext(review.ap), review.alone))
		self.assertTrue(_row_for(self._ext(review.ap), new_name))

	def test_m2_a_held_objective_cannot_be_renamed_either(self):
		review = self._review("Manager Review")
		with self.assertRaises(frappe.PermissionError):
			frappe.rename_doc("Individual Goal", review.goal, f"{review.goal}-{_uid()}", force=True)

	def test_m2_minor7_rename_and_after_submit_hooks_are_registered(self):
		events = frappe.get_doc_hooks()
		for doctype in ("KPI", "Individual Goal"):
			self.assertIn("alvoraa_goals.review_items.refuse_rename_while_held", events[doctype]["before_rename"])
			self.assertIn("alvoraa_goals.review_items.follow_rename", events[doctype]["after_rename"])
		self.assertIn("alvoraa_goals.review_items.refresh_copies_of",
		              events["Individual Goal"]["on_update_after_submit"])
		# A submitted Objective's locked fields are closed by Frappe itself on every
		# path, because none of them may change after submit.
		import alvoraa_goals.review_items as review_items

		meta = frappe.get_meta("Individual Goal")
		for field in review_items.LOCKED_FIELDS["Individual Goal"]:
			self.assertFalse((meta.get_field(field) or frappe._dict()).allow_on_submit, field)


# ── Code review M2 · the live KPI number moves only on approval ─────────────


class TestCrM2LiveNumberMovesOnApproval(_Screens):
	def _kpi_ended(self, mode="Cumulative"):
		from frappe.utils import add_days, today

		cycle = self._cycle(add_days(today(), -90), add_days(today(), 60))
		return self._kpi(self.subject, cycle, target=100, mode=mode,
		                 start=add_days(today(), -90), end=add_days(today(), 60))

	def test_cr_m2_a_rejected_reading_never_reaches_the_live_number(self):
		import alvoraa_portal.performance_api as pa

		kpi = self._kpi_ended()
		self._as(self.subject_user)
		wrong = pa.log_kpi_progress(kpi, 50)["row_name"]
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("KPI", kpi, "actual_value"), 0)

		self._as(self.manager_user)
		pa.approve_kpi_update(kpi, wrong, "Rejected")
		self._as(self.subject_user)
		right = pa.log_kpi_progress(kpi, 5)["row_name"]
		self._as(self.manager_user)
		pa.approve_kpi_update(kpi, right, "Approved")
		# Deciding the same way twice changes nothing.
		pa.approve_kpi_update(kpi, right, "Approved")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("KPI", kpi, ["actual_value", "attainment_pct"]), (5, 5))

	def test_cr_m2_taking_an_approval_back_takes_the_amount_off_and_status_follows(self):
		import alvoraa_portal.performance_api as pa
		from frappe.utils import add_days, today

		kpi = self._kpi_ended()
		self._as(self.subject_user)
		row = pa.log_kpi_progress(kpi, 120, log_date=add_days(today(), -1))["row_name"]
		self._as(self.manager_user)
		pa.approve_kpi_update(kpi, row, "Approved")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("KPI", kpi, "actual_value"), 120)

		# The period ends; the end-of-period status follows the approved number.
		frappe.db.set_value("KPI", kpi, "period_end", add_days(today(), -1))
		frappe.db.commit()
		self._as(self.manager_user)
		pa.approve_kpi_update(kpi, row, "Rejected")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("KPI", kpi, ["actual_value", "status"]), (0, "Missed"))

	def test_m8_hr_approves_readings_only_for_the_companies_they_look_after(self):
		import alvoraa_portal.goals_api as goals_api
		import alvoraa_portal.performance_api as pa
		from frappe.utils import add_days, today

		start, end = add_days(today(), -30), add_days(today(), 30)
		cycle = self._cycle(start, end, company=self.company_b)
		kpi = self._kpi(self.subject_b, cycle, target=10, start=start, end=end)
		self._as(self.subject_b_user)
		row = pa.log_kpi_progress(kpi, 3)["row_name"]
		self._as(self.hr_user)
		with self.assertRaises(frappe.PermissionError):
			pa.approve_kpi_update(kpi, row, "Approved")
		self.assertNotIn(row, [u["row_name"] for u in goals_api.get_pending_approvals()["kpi_updates"]])
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("KPI Progress Log", row, "approval_status"), "Pending")

	def test_m2_approvers_see_when_a_reading_was_typed(self):
		import alvoraa_portal.goals_api as goals_api
		import alvoraa_portal.performance_api as pa
		from frappe.utils import add_days, today

		kpi = self._kpi_ended()
		self._as(self.subject_user)
		row = pa.log_kpi_progress(kpi, 3, log_date=add_days(today(), -20))["row_name"]
		self._as(self.manager_user)
		pending = next(u for u in goals_api.get_pending_approvals()["kpi_updates"] if u["row_name"] == row)
		logged = next(r for r in pa.get_kpi_update_log(kpi) if r["name"] == row)
		frappe.set_user("Administrator")
		for entry in (pending, logged):
			self.assertEqual(entry["log_date"], str(frappe.utils.getdate(add_days(today(), -20))))
			self.assertTrue(entry["logged_on"].startswith(str(frappe.utils.getdate(today()))))


# ── Code review M1 · the add/remove dialog removes only what it listed ──────


class TestCrM1SelectionRemovesOnlyWhatWasListed(_Screens):
	def test_cr_m1_a_cascaded_kpi_is_listed_and_a_kpi_the_dialog_never_showed_is_kept(self):
		import alvoraa_portal.performance_api as pa

		start, end = self._window()
		cycle = self._cycle(start, end)
		managers_goal = self._goal(self.manager, cycle, start, end)
		cascaded = self._kpi(self.subject, cycle, target=10, goal=managers_goal, start=start, end=end)
		# Tagged to the cycle, so copied, but its own period is outside the review's.
		outside = self._kpi(self.subject, cycle, target=10, start=_day(end, 30), end=_day(end, 60))
		alone = self._kpi(self.subject, cycle, target=10, start=start, end=end)
		later = self._kpi(self.subject, None, target=10, start=start, end=end)
		ap = self._appraisal(self.subject, cycle, status="Employee Review")

		self._as(self.subject_user)
		pa.get_my_review(ap)
		listed = {k["name"]: k["selected"] for k in pa.get_available_for_review(ap)["kpis"]}
		self.assertTrue(listed.get(cascaded), "a cascaded KPI is listed, ticked")
		self.assertNotIn(outside, listed)

		# Adding one KPI with everything else as listed removes nothing and asks nothing.
		ticked = [n for n, sel in listed.items() if sel] + [later]
		result = pa.set_review_selection(ap, "[]", json.dumps(ticked), acknowledge_removal=0)
		self.assertEqual((result["added"], result["removed"]), (1, 0))

		# Unticking one listed KPI removes that one only; the unlisted KPI stays.
		ticked.remove(alone)
		result = pa.set_review_selection(ap, "[]", json.dumps(ticked), acknowledge_removal=1)
		frappe.set_user("Administrator")
		self.assertEqual(result["removed"], 1)
		ext = self._ext(ap)
		for name in (cascaded, outside, later):
			self.assertTrue(_row_for(ext, name), name)
		self.assertFalse(_row_for(ext, alone) and not _row_for(ext, alone).removed)


# ── Code review M3 · a manager who holds an HR role gets the manager's controls ─


class TestCrM3ManagerWithHrRole(_Screens):
	def test_cr_m3_viewer_role_is_manager_for_the_manager_and_hr_for_hr(self):
		import alvoraa_portal.performance_api as pa

		ap = self._review_of(self.hr_report, "Manager Review")
		self._as(self.hr_boss_user)
		self.assertEqual(pa.get_manager_review(ap)["viewer_role"], "manager")

		# HR Review is HR's step: an HR role holder keeps HR's controls there.
		self._set_status(ap, "HR Review")
		self._as(self.hr_boss_user)
		self.assertEqual(pa.get_manager_review(ap)["viewer_role"], "hr")
		other = self._review_of(self.subject, "HR Review")
		self._as(self.hr_user)
		self.assertEqual(pa.get_manager_review(other)["viewer_role"], "hr")


# ── Code review minor 9 · an overall rating of 0 is refused ─────────────────


class TestCrMinor9OverallRatingOfZero(_Screens):
	def test_cr_minor9_save_overall_rating_refuses_0_and_keeps_the_rating(self):
		import alvoraa_portal.performance_api as pa

		ap = self._review_of(self.subject, "Manager Review")
		self._as(self.manager_user)
		pa.save_overall_rating(ap, 3)
		with self.assertRaises(frappe.ValidationError):
			pa.save_overall_rating(ap, 0)
		frappe.set_user("Administrator")
		self.assertEqual(self._ext(ap).overall_rating, 3)


# ── Security m7 · HR screens list no items of an unsent self-review ─────────


class TestM7HrScreensHideDraftItems(_Screens):
	def test_m7_an_hr_role_line_manager_sees_no_item_of_a_draft_on_hr_screens(self):
		import alvoraa_portal.performance_api as pa

		start, end = self._window()
		cycle = self._cycle(start, end)
		kpi = self._kpi(self.hr_report, cycle, target=10)
		ap = self._appraisal(self.hr_report, cycle, status="Employee Review")
		self._as(self.hr_report_user)
		pa.get_my_review(ap)
		row = _row_for(self._ext(ap), kpi).name

		def seen():
			self._as(self.hr_boss_user)
			try:
				listed = row in {r["name"] for r in pa.hr_list_kpis(cycle)}
				exported = row in pa.export_cycle_kpis_csv(cycle)["csv"]
				return listed, exported
			finally:
				frappe.set_user("Administrator")

		self.assertEqual(seen(), (False, False))
		self._set_status(ap, "Manager Review")
		self.assertEqual(seen(), (True, True))


# ── Security m1 · lock release days are stamped on each review ──────────────


class TestM1LockReleaseDaysStamped(_Screens):
	def tearDown(self):
		frappe.db.set_single_value("HR Settings", "alvoraa_review_lock_release_days", 30)
		frappe.db.value_cache.pop("HR Settings", None)
		frappe.db.commit()
		super().tearDown()

	def test_m1_a_settings_change_does_not_release_a_running_reviews_lock(self):
		from unittest.mock import patch

		import alvoraa_goals.review_items as review_items
		from frappe.utils import add_days

		frappe.db.set_single_value("HR Settings", "alvoraa_review_lock_release_days", 30)
		frappe.db.value_cache.pop("HR Settings", None)
		frappe.db.commit()
		r = self._review()
		self.assertEqual(self._ext(r.ap).lock_release_days, 30)
		end = frappe.db.get_value("Appraisal Cycle", r.cycle, "end_date")

		frappe.db.set_single_value("HR Settings", "alvoraa_review_lock_release_days", 1)
		frappe.db.value_cache.pop("HR Settings", None)
		frappe.db.commit()
		with patch("alvoraa_goals.review_items.nowdate", return_value=str(add_days(end, 5))):
			self.assertIn(r.alone, review_items.holds("KPI", [r.alone]))

		# A review opened after the change takes the new value.
		later = self._review()
		self.assertEqual(self._ext(later.ap).lock_release_days, 1)

	def test_m1_the_patch_is_listed_after_the_copy_backfill(self):
		import os

		import alvoraa_goals

		with open(os.path.join(os.path.dirname(alvoraa_goals.__file__), "patches.txt"), encoding="utf-8") as f:
			lines = [line.strip() for line in f if line.strip()]
		self.assertGreater(lines.index("alvoraa_goals.patches.v1_0.stamp_lock_release_days"),
		                   lines.index("alvoraa_goals.patches.v1_0.take_review_copies"))


# ── Security m3, m5 · names and values stay out of logs and live-record notes ─


class TestM3M5WriteBackNoteAndMarkers(_Screens):
	def test_m3_the_live_records_note_names_fields_and_the_values_sit_on_the_review(self):
		import alvoraa_goals.review_items as review_items

		r = self._review(status="HR Review")
		ext = self._ext(r.ap)
		review_items.change_definition(ext, _row_for(ext, r.alone), {"target_value": 73})
		review_items.save_review_record(ext)
		ext = self._ext(r.ap)
		self.assertEqual(review_items.write_back(ext), 1)
		review_items.save_review_record(ext)
		frappe.db.commit()

		live = frappe.get_all("Comment", filters={"reference_doctype": "KPI", "reference_name": r.alone,
		                                          "comment_type": "Info"}, pluck="content")
		self.assertEqual(len(live), 1)
		self.assertIn("target_value", live[0])
		self.assertIn(r.ap, live[0])
		self.assertNotIn("73", live[0])
		on_review = frappe.get_all("Comment", filters={"reference_doctype": "Alvoraa Appraisal Extension",
		                                               "reference_name": r.ap, "content": ["like", "%written back%"]},
		                           pluck="content")
		self.assertTrue(any("to 73" in c for c in on_review), on_review)

	def test_m5_priv15_a_marker_in_a_title_a_reason_and_an_answer_never_reaches_logs_or_messages(self):
		import alvoraa_portal.performance_api as pa

		marker = f"PRIV15MARK{_uid()}"
		started = now_datetime()
		r = self._review("Employee Review")
		ext = self._ext(r.ap)
		alone, under = _row_for(ext, r.alone).name, _row_for(ext, r.under).name

		# The subject renames an item inside the review (it is written back later).
		self._as(self.subject_user)
		pa.save_review_item_definition(r.ap, alone, title=f"{marker} title")
		pa.submit_employee_review(r.ap, overall_comment=f"{marker} comment")
		# The manager rates one item and removes another with a reason.
		self._as(self.manager_user)
		pa.save_review_item_rating(r.ap, alone, 4, comment=f"{marker} rating comment")
		pa.remove_review_item(r.ap, under, reason=f"{marker} removal reason", acknowledge=1)
		frappe.set_user("Administrator")

		# A new fact flags the rating; the rater has since left, so HR answers with a reason.
		self._reading(r.alone, _day(r.start, 5), 7)
		frappe.db.set_value("Alvoraa Review Item", alone, "manager_rated_by", "left.the.company@example.com")
		self._set_status(r.ap, "HR Review")
		self._as(self.hr_user)
		pa.get_manager_review(r.ap)
		pa.answer_rating_flag(r.ap, alone, keep=1, reason=f"{marker} answer reason")
		self.assertEqual(pa.advance_review_status(r.ap)["review_status"], "Completed")
		frappe.set_user("Administrator")

		self.assertIn("Written back", _row_for(self._ext(r.ap), r.alone).write_back_note)
		self.assertEqual(frappe.db.get_value("KPI", r.alone, "kpi_name"), f"{marker} title")
		for doctype, fields in (("Error Log", ["method", "error"]),
		                        ("Email Queue", ["message"]),
		                        ("Notification Log", ["subject", "email_content"])):
			rows = frappe.get_all(doctype, filters={"creation": [">=", started]}, fields=fields)
			self.assertNotIn(marker, json.dumps(rows, default=str), doctype)
		# The live record's own note names the field, never the new title (m3).
		live_notes = frappe.get_all("Comment", filters={"reference_doctype": "KPI", "reference_name": r.alone},
		                            pluck="content")
		self.assertNotIn(marker, json.dumps(live_notes))


# ── Security m4 · PRIV-14 · a review record with copies is never deleted ────


class TestM4Priv14ReviewRecordIsNotDeleted(_Screens):
	def test_m4_priv14_no_path_deletes_a_review_record_that_holds_copies(self):
		r = self._review("Completed")
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("Alvoraa Appraisal Extension", r.ap, force=True, ignore_permissions=True)
		frappe.db.rollback()
		self.assertTrue(frappe.db.exists("Alvoraa Appraisal Extension", r.ap))
		self.assertTrue(frappe.db.count("Alvoraa Review Item", {"parent": r.ap}))

		# A record with no copies yet is not a decision record, and can still go.
		start, end = self._window()
		empty = self._appraisal(self.stranger, self._cycle(start, end), status="Not Started")
		frappe.delete_doc("Alvoraa Appraisal Extension", empty, force=True, ignore_permissions=True)
		frappe.db.commit()
		self.assertFalse(frappe.db.exists("Alvoraa Appraisal Extension", empty))


# ── Code review minor 6 · two people opening one review at once ─────────────


class TestCrMinor6OpeningTogether(_Screens):
	def test_cr_minor6_a_second_open_that_loses_the_save_race_carries_on(self):
		import alvoraa_goals.review_items as review_items

		r = self._review("Manager Review")
		first, second = self._ext(r.ap), self._ext(r.ap)
		self._reading(r.alone, _day(r.start, 6), 3)
		self.assertTrue(review_items.open_review(first))
		frappe.db.commit()
		# The second copy of the record is now stale; before the fix its save failed.
		self.assertFalse(review_items.open_review(second))
		self.assertEqual(second.modified, first.modified)
		self.assertEqual(_row_for(second, r.alone).actual_value, 13)


