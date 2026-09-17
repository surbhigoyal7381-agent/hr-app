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
