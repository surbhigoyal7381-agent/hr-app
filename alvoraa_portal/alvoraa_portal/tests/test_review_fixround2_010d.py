"""Slice 010 group D, fix round 2: decisions 37 and 38, after the ppj.localhost
rehearsal (08-ppj-rehearsal.md).

Decision 37: a review is opened from one of two lists, and the list sets the
view. "My team's reviews" opens it as the manager; the HR review list opens it
as HR. The server checks the right for the view asked for, and neither view
allows more than the rules before it. This fixes rehearsal F1 (a review stuck in
HR Review) and F2 (HR who gave a rating told the manager must answer).

Decision 38: C1 (the dry run on a site not yet migrated), F3 (a button for the
calibration note, showing the saved note), F5 and F6 (rollback helpers).

Starts from the shipped permissions, like the other 010 tests. Synthetic people
and records only, tagged S010D.
"""

import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date

import alvoraa_portal.tests.test_review_outside_010d as outside
from alvoraa_portal.tests.test_portal_security_010 import _employee, _user
from alvoraa_portal.tests.test_review_copies_010d import _Team, _day, _row_for, _uid
from alvoraa_portal.tests.test_review_line_hr_010d import ASK_ANOTHER, _LineHr

EXTENSION = "Alvoraa Appraisal Extension"
ITEM = "Alvoraa Review Item"


def _items(review):
	"""Every item of a review payload, KPIs under Objectives included."""
	out = list(review["goals"]) + list(review["standalone_kpis"])
	for goal in review["goals"]:
		out += goal.get("kpis", [])
	return {i["name"]: i for i in out}


class _Views(_LineHr):
	def _refused(self, user, call):
		"""Run call as user. Returns (message, [(rule, endpoint, name)]) of the refusal, or None."""
		logger = MagicMock()
		self._as(user)
		try:
			with patch("frappe.logger", return_value=logger):
				call()
			return None
		except frappe.PermissionError as e:
			rules = [json.loads(c[0][0]) for c in logger.warning.call_args_list]
			return str(e), [(r["rule"], r["endpoint"], r["name"]) for r in rules]
		finally:
			frappe.set_user("Administrator")

	def _review_as(self, user, ap, view):
		import alvoraa_portal.performance_api as pa

		self._as(user)
		try:
			return pa.get_manager_review(ap, view=view)
		finally:
			frappe.set_user("Administrator")

	def _rated_by_manager_then_flagged(self, subject, subject_user, manager_user):
		"""The manager rates one item and the overall rating in Manager Review; in
		HR Review a new fact dated in the period flags both. Returns (r, row)."""
		import alvoraa_portal.performance_api as pa

		r = self._review_for(subject, subject_user, "Manager Review")
		alone = _row_for(self._ext(r.ap), r.alone).name
		self._as(manager_user)
		pa.save_review_item_rating(r.ap, alone, 4)
		pa.save_manager_review(r.ap, "feedback", overall_rating=4)
		frappe.set_user("Administrator")
		self._set_status(r.ap, "HR Review")
		self._reading(r.alone, _day(r.start, 5), 7)
		self._review_as(self.hr_user, r.ap, "hr")          # the refresh raises the questions
		ext = self._ext(r.ap)
		self.assertEqual((_row_for(ext, r.alone).manager_flag, ext.overall_rating_flag), (1, 1))
		return r, alone


# ── Decision 37 · each view needs its own right ─────────────────────────────


class TestD37EachViewNeedsItsOwnRight(_Views):
	def test_d37_the_manager_view_needs_the_manager_and_the_hr_view_needs_hr_at_hr_review(self):
		import alvoraa_portal.performance_api as pa

		r = self._review_for(self.subject, self.subject_user, "Manager Review")
		opens = lambda view: (lambda: pa.get_manager_review(r.ap, view=view))

		self.assertEqual(self._review_as(self.manager_user, r.ap, "manager")["viewer_role"], "manager")
		self.assertEqual(self._refused(self.manager_user, opens("hr"))[1], [("D37", "get_manager_review", r.ap)])
		self.assertEqual(self._refused(self.hr_user, opens("manager"))[1], [("D37", "get_manager_review", r.ap)])
		self.assertEqual(self._refused(self.hr_user, opens("hr"))[1], [("SEC-27", "get_manager_review", r.ap)])
		# No view, or one that is not a list, is refused even to the manager (fails closed).
		for view in (None, "", "admin", "HR"):
			self.assertEqual(self._refused(self.manager_user, opens(view))[1], [("D37", "get_manager_review", r.ap)],
			                 view)

		self._set_status(r.ap, "HR Review")
		self.assertEqual(self._review_as(self.hr_user, r.ap, "hr")["viewer_role"], "hr")
		self.assertEqual(self._review_as(self.manager_user, r.ap, "manager")["viewer_role"], "manager")
		self.assertTrue(self._refused(self.hr_user, opens("manager")))
		for user in (self.subject_user, self.stranger_user):
			for view in ("manager", "hr"):
				self.assertTrue(self._refused(user, opens(view)), (user, view))

	def test_d37_the_line_opens_the_hr_view_no_earlier_and_sees_no_more_than_before(self):
		import alvoraa_portal.performance_api as pa

		r = self._review_for(self.hr_report, self.hr_report_user, "Manager Review")
		# Before decision 37 the line read this stage only as the manager.
		refused = self._refused(self.hr_boss_user, lambda: pa.get_manager_review(r.ap, view="hr"))
		self.assertEqual(refused[1], [("SEC-27", "get_manager_review", r.ap)])

		self._set_status(r.ap, "HR Review")
		as_hr = self._review_as(self.hr_boss_user, r.ap, "hr")
		self.assertEqual((as_hr["viewer_role"], as_hr["hr_steps_elsewhere"]), ("hr", 1))
		# The line gets the manager's data in the HR view: not HR's upload dates or late facts.
		self.assertFalse(any("facts_dated_by_upload" in i for i in _items(as_hr).values()))
		other_hr = self._review_as(self.hr_user, r.ap, "hr")
		self.assertTrue(all("facts_dated_by_upload" in i for i in _items(other_hr).values()))
		as_manager = self._review_as(self.hr_boss_user, r.ap, "manager")
		self.assertEqual((as_manager["viewer_role"], as_manager["hr_steps_elsewhere"]), ("manager", 0))

	def test_d37_the_hr_view_follows_the_company_rule(self):
		import alvoraa_portal.performance_api as pa

		ap = self._review_of(self.subject_b, "HR Review", company=self.company_b)
		refused = self._refused(self.hr_user, lambda: pa.get_manager_review(ap, view="hr"))
		self.assertEqual(refused[1], [("SEC-13", "get_manager_review", ap)])


# ── F1 · a manager with an HR role answers from the manager view ────────────


class TestD37F1TheStuckReviewIsFinished(_Views):
	def test_f1_the_manager_with_an_hr_role_answers_as_manager_and_another_hr_person_finishes(self):
		import alvoraa_portal.performance_api as pa

		r, alone = self._rated_by_manager_then_flagged(self.hr_report, self.hr_report_user, self.hr_boss_user)

		# The HR view: the note, and no answer buttons, for the manager who is in the line.
		as_hr = self._review_as(self.hr_boss_user, r.ap, "hr")
		self.assertEqual((as_hr["hr_steps_elsewhere"], as_hr["overall_flag_answer"]), (1, ""))
		self.assertEqual(_items(as_hr)[alone]["flag_answer"], "")
		# The manager view: both questions are theirs to answer, in HR Review.
		as_manager = self._review_as(self.hr_boss_user, r.ap, "manager")
		self.assertEqual((as_manager["review_status"], as_manager["overall_flag_answer"]), ("HR Review", "rater"))
		self.assertEqual(_items(as_manager)[alone]["flag_answer"], "rater")
		# Another HR person does not answer for a manager who still acts, and cannot finish yet.
		other = self._review_as(self.hr_user, r.ap, "hr")
		self.assertEqual((other["overall_flag_answer"], _items(other)[alone]["flag_answer"]), ("", ""))
		self._as(self.hr_boss_user)
		team = {t["appraisal"]: t for t in pa.get_team_reviews(r.cycle)["team"] if t.get("appraisal")}
		frappe.set_user("Administrator")
		self.assertEqual(team[r.ap]["rating_needs_answer"], 1)

		message, _lines = self._refused(self.hr_user, lambda: pa.answer_rating_flag(r.ap, "overall", keep=1,
		                                                                           reason="x", view="hr"))
		self.assertIn("Only the person who gave this rating", message)
		self.assertTrue(self._refused(self.hr_user, lambda: pa.advance_review_status(r.ap)))
		# The manager in the line may not answer from the HR view (decision 34)...
		message, lines = self._refused(self.hr_boss_user, lambda: pa.answer_rating_flag(r.ap, "overall", keep=1,
		                                                                               view="hr"))
		self.assertIn(ASK_ANOTHER, message)
		self.assertEqual(lines, [("D34", "answer_rating_flag", r.ap)])

		# ...and does from the manager view.
		self._as(self.hr_boss_user)
		pa.answer_rating_flag(r.ap, alone, keep=1, view="manager")
		pa.answer_rating_flag(r.ap, "overall", keep=1, view="manager")
		frappe.set_user("Administrator")
		ext = self._ext(r.ap)
		self.assertEqual((ext.overall_rating_flag, _row_for(ext, r.alone).manager_flag), (0, 0))
		self.assertEqual((ext.overall_flag_answered_by, _row_for(ext, r.alone).manager_flag_answered_by),
		                 (self.hr_boss_user, self.hr_boss_user))

		self._as(self.hr_user)
		self.assertEqual(pa.advance_review_status(r.ap)["review_status"], "Completed")
		frappe.set_user("Administrator")

	def test_f1_a_manager_without_an_hr_role_answers_in_hr_review_too(self):
		import alvoraa_portal.performance_api as pa

		r, alone = self._rated_by_manager_then_flagged(self.subject, self.subject_user, self.manager_user)
		review = self._review_as(self.manager_user, r.ap, "manager")
		self.assertEqual((review["overall_flag_answer"], _items(review)[alone]["flag_answer"]), ("rater", "rater"))
		self._as(self.manager_user)
		pa.answer_rating_flag(r.ap, alone, keep=0, rating=3, view="manager")
		pa.answer_rating_flag(r.ap, "overall", keep=1, view="manager")
		frappe.set_user("Administrator")
		ext = self._ext(r.ap)
		self.assertEqual((ext.overall_rating_flag, _row_for(ext, r.alone).manager_rating), (0, 3))


# ── F2 · HR who gave the rating answers from the HR view ────────────────────


class TestD37F2HrWhoRatedAnswers(_Views):
	def test_f2_hr_who_calibrated_answers_from_the_hr_view_and_the_manager_is_not_asked(self):
		import alvoraa_portal.performance_api as pa

		r = self._review_for(self.subject, self.subject_user, "Manager Review")
		self._as(self.manager_user)
		pa.save_manager_review(r.ap, "feedback", overall_rating=4)
		frappe.set_user("Administrator")
		self._set_status(r.ap, "HR Review")
		self._as(self.hr_user)
		pa.save_calibration_note(r.ap, "calibrated", 3)
		frappe.set_user("Administrator")
		self.assertEqual(self._ext(r.ap).overall_rated_by, self.hr_user)
		self._reading(r.alone, _day(r.start, 5), 7)
		self._review_as(self.hr_user, r.ap, "hr")
		self.assertEqual(self._ext(r.ap).overall_rating_flag, 1)

		as_manager = self._review_as(self.manager_user, r.ap, "manager")
		self.assertEqual(as_manager["overall_flag_answer"], "")
		self._as(self.manager_user)
		team = {t["appraisal"]: t for t in pa.get_team_reviews(r.cycle)["team"] if t.get("appraisal")}
		frappe.set_user("Administrator")
		self.assertEqual(team[r.ap]["rating_needs_answer"], 0)
		message, _lines = self._refused(self.manager_user, lambda: pa.answer_rating_flag(r.ap, "overall", keep=1,
		                                                                                view="manager"))
		self.assertIn("Only the person who gave this rating", message)

		self.assertEqual(self._review_as(self.hr_user, r.ap, "hr")["overall_flag_answer"], "rater")
		self._as(self.hr_user)
		pa.answer_rating_flag(r.ap, "overall", keep=0, rating=2, view="hr")      # no reason: it is their own
		frappe.set_user("Administrator")
		ext = self._ext(r.ap)
		self.assertEqual((ext.overall_rating, ext.overall_rating_flag, ext.overall_flag_answered_by),
		                 (2, 0, self.hr_user))
		notes = frappe.get_all("Comment", filters={"reference_doctype": EXTENSION, "reference_name": r.ap,
		                                           "comment_type": "Info", "content": ["like", "%Rating question%"]},
		                       pluck="content")
		self.assertTrue(notes and all("Reason:" not in n for n in notes), notes)


# ── Decision 37 · the two lists ─────────────────────────────────────────────


class TestD37TwoLists(_Views):
	def test_d37_my_teams_reviews_lists_only_the_people_i_manage_whatever_my_roles(self):
		import alvoraa_portal.performance_api as pa

		start, end = self._window()
		cycle = self._cycle(start, end)
		aps = {e: self._appraisal(e, cycle, status="HR Review")
		       for e in (self.subject, self.hr_subject, self.hr_report, self.stranger)}

		def team(user):
			self._as(user)
			try:
				rows = pa.get_team_reviews(cycle)["team"]
				expected = set(pa._reports_of(pa._employee_id())) | set(pa._stand_in_subjects(pa._employee_id()))
				context = pa.get_performance_context()
				return {t["employee"] for t in rows}, rows, expected, context
			finally:
				frappe.set_user("Administrator")

		names, rows, expected, context = team(self.manager_user)
		self.assertTrue({self.subject, self.hr_subject} <= names)
		self.assertFalse({self.hr_report, self.stranger} & names)
		self.assertTrue(context["has_team_reviews"])
		self.assertFalse(any("hr_steps_elsewhere" in t for t in rows))

		names, _rows, expected, _context = team(self.hr_boss_user)
		self.assertEqual(names, expected)
		self.assertIn(self.hr_report, names)
		self.assertFalse({self.subject, self.hr_subject} & names)

		# A plain HR person manages nobody: no team list, and the HR list has the company.
		names, _rows, expected, context = team(self.hr_desk_user)
		self.assertEqual((names, expected, context["has_team_reviews"]), (set(), set(), False))
		self._as(self.hr_desk_user)
		listed = {a["name"] for a in pa.hr_list_appraisals(cycle)}
		frappe.set_user("Administrator")
		self.assertTrue({aps[self.subject], aps[self.hr_report]} <= listed)

	def test_d37_the_hr_stand_in_lists_people_with_no_manager_as_their_manager(self):
		import alvoraa_portal.performance_api as pa
		from alvoraa_goals.permissions import get_hr_manager_employee

		stand_in = get_hr_manager_employee()
		if not stand_in:
			self.skipTest("no HR Manager employee on this site")
		stand_in_user = frappe.db.get_value("Employee", stand_in, "user_id")
		company = frappe.db.get_value("Employee", stand_in, "company")
		user = _user(f"d.fr2.lone.{_uid()}", ("Employee",))
		lone = _employee(f"DFr2Lone{_uid()}", company=company, user=user)
		self._cleanup.append(("Employee", lone))
		ap = self._review_of(lone, "Manager Review", company=company)

		self._as(stand_in_user)
		team = {t["employee"] for t in pa.get_team_reviews()["team"]}
		self.assertIn(lone, team)
		self.assertTrue(pa.get_performance_context()["has_team_reviews"])
		self.assertEqual(pa.get_manager_review(ap, view="manager")["viewer_role"], "manager")
		frappe.set_user("Administrator")


# ── F3 · the calibration note box shows the saved note ──────────────────────


class TestF3CalibrationNoteIsRead(_Views):
	def test_f3_hr_who_may_calibrate_reads_the_saved_note_and_nobody_else(self):
		import alvoraa_portal.performance_api as pa

		marker = f"S010D-F3-{_uid()}"
		r = self._review_for(self.subject, self.subject_user, "HR Review")
		self._as(self.hr_user)
		pa.save_calibration_note(r.ap, marker)
		self.assertEqual(pa.get_calibration_note(r.ap), {"calibration_notes": marker})
		frappe.set_user("Administrator")

		for user in (self.subject_user, self.manager_user, self.stranger_user):
			self.assertTrue(self._refused(user, lambda: pa.get_calibration_note(r.ap)), user)
		for status in ("Manager Review", "Completed"):
			self._set_status(r.ap, status)
			self._as(self.hr_user)
			with self.assertRaises(frappe.ValidationError, msg=status):
				pa.get_calibration_note(r.ap)
			frappe.set_user("Administrator")

		# The subject's line with an HR role: refused, as for saving (decision 34).
		line = self._review_for(self.hr_report, self.hr_report_user, "HR Review")
		message, lines = self._refused(self.hr_boss_user, lambda: pa.get_calibration_note(line.ap))
		self.assertIn(ASK_ANOTHER, message)
		self.assertEqual(lines, [("D34", "get_calibration_note", line.ap)])
		# Another company's review.
		elsewhere = self._review_of(self.subject_b, "HR Review", company=self.company_b)
		self.assertTrue(self._refused(self.hr_user, lambda: pa.get_calibration_note(elsewhere)))


# ── C1, F5, F6 · the dry run and the rollback helpers ───────────────────────


class TestC1F5F6ReleaseHelpers(_Team):
	_old_review = outside.TestBackfillCopiesExistingReviews._old_review
	_setup = outside.TestBackfillCopiesExistingReviews._setup

	def test_c1_the_dry_run_works_on_a_site_without_group_d_tables(self):
		import alvoraa_goals.review_backfill as review_backfill

		c = self._setup()
		real_get_all = frappe.get_all

		def old_schema_get_all(doctype, *args, **kwargs):
			"""A database from before this release: no copy table, no items_taken_on."""
			if doctype == ITEM:
				raise frappe.db.TableMissingError("DocType", ITEM)
			if doctype == EXTENSION and "items_taken_on" in json.dumps(kwargs.get("fields") or (args[1:2] or [""])[0]):
				raise Exception("(1054, \"Unknown column 'items_taken_on' in 'field list'\")")
			return real_get_all(doctype, *args, **kwargs)

		def old_schema_has_column(doctype, column):
			return not (doctype == EXTENSION and column == "items_taken_on")

		with patch("frappe.get_all", side_effect=old_schema_get_all), \
		     patch.object(frappe.db, "table_exists", side_effect=lambda doctype, cached=True: doctype != ITEM), \
		     patch.object(frappe.db, "has_column", side_effect=old_schema_has_column):
			out = review_backfill.report(c.names)
		self.assertEqual(out["site_already_has_group_d_tables"], 0)
		self.assertEqual(out["will_copy"], {"reviews": 2, "items": 4, "completed": 1, "open": 1, "open_already_frozen": 0})
		self.assertEqual(out["skipped"], {"not started: copied when first opened": 1})
		self.assertEqual(frappe.db.count(ITEM, {"parent": ["in", c.names]}), 0)
		self.assertEqual(review_backfill.report(c.names)["site_already_has_group_d_tables"], 1)

	def test_f5_copy_back_includes_a_review_completed_under_this_release_and_not_history(self):
		import alvoraa_goals.review_backfill as review_backfill
		import alvoraa_goals.review_items as review_items

		c = self._setup()
		review_backfill.run(c.names)
		opened = self._ext(c.open.ap)
		row = _row_for(opened, c.open.kpi)
		row.manager_rating = 2
		row.manager_rated_on = add_to_date(opened.items_taken_on, minutes=5)
		review_items.save_review_record(opened)
		frappe.db.set_value(EXTENSION, c.open.ap, {"review_status": "Completed",
		                                           "completed_on": add_to_date(opened.items_taken_on, minutes=10)})
		# History copied from a review completed before the release, then changed on its copy.
		frappe.db.set_value(ITEM, _row_for(self._ext(c.done.ap), c.done.kpi).name, "manager_rating", 1)
		frappe.db.commit()

		ratings = review_backfill.copy_ratings_back_for_rollback(dry_run=1, names=c.names)
		self.assertIn(c.open.kpi, ratings["kpis"])
		self.assertNotIn(c.done.kpi, ratings["kpis"])
		review_backfill.copy_ratings_back_for_rollback(dry_run=0, names=c.names)
		self.assertEqual(frappe.db.get_value("KPI", c.open.kpi, "manager_rating"), 2)
		self.assertEqual(frappe.db.get_value("KPI", c.done.kpi, "manager_rating"), 4)

	def test_f6_undo_keeps_a_review_whose_unrated_item_was_removed_and_discarded(self):
		import alvoraa_goals.review_backfill as review_backfill
		import alvoraa_goals.review_items as review_items
		import alvoraa_portal.performance_api as pa

		c = self._setup()
		review_backfill.run(c.names)
		frappe.db.set_value(EXTENSION, c.open.ap, "removal_mode", review_items.REMOVAL_DISCARD)
		frappe.db.commit()
		self.assertEqual(review_backfill.undo_backfill(dry_run=1, names=[c.open.ap])["undone"], 1)

		goal_row = _row_for(self._ext(c.open.ap), c.open.goal).name
		self._as(self.manager_user)
		outcome = pa.remove_review_item(c.open.ap, goal_row, reason="not this cycle", acknowledge=1)["outcome"]
		frappe.set_user("Administrator")
		self.assertEqual(outcome, "discarded")
		self.assertEqual(frappe.db.count(ITEM, {"parent": c.open.ap}), 1)

		plan = review_backfill.undo_backfill(dry_run=1, names=c.names)
		self.assertIn(c.open.ap, plan["kept_because_changed_since"])
		self.assertNotIn(c.done.ap, plan["kept_because_changed_since"])


# ── The page ────────────────────────────────────────────────────────────────


class TestFixRound2Page(FrappeTestCase):
	def test_d37_each_list_opens_reviews_in_its_own_view(self):
		from alvoraa_portal.tests.test_review_page_010d import _between, _page

		page = _page()
		team = _between(page, "function pfTeamReviewCard(m)", "window.pfSubmitReview")
		self.assertIn("','manager')", team)
		self.assertNotIn("','hr')", team)
		self.assertNotIn("pfFinishHrReview", team)
		hr = _between(page, "function pfHrAppraisalTable(appraisals, cycle)", "function pfHrSummary")
		self.assertIn("','hr')", hr)
		self.assertNotIn("','manager')", hr)
		self.assertIn("HR review list", hr)
		self.assertIn("My team's reviews", _between(page, 'id="rev-sec-team-reviews"', 'id="rev-body-team-reviews"'))
		self.assertIn("if (ctx.has_team_reviews) {", _between(page, "window.pfBoot = function", "var scopeSel"))

		opener = _between(page, "window.prOpenManagerReview = function(appraisalName, employeeName, view)",
		                  "function prRenderManagerFeedbackForm")
		self.assertIn('pf("get_manager_review", {appraisal: appraisalName, view: view})', opener)
		reload_ = _between(page, "function riReload()", "function prRenderFutureDevPage")
		self.assertIn('pf("get_manager_review", {appraisal: _pr.appraisal, view: _pr.viewerRole})', reload_)
		answer = _between(page, "window.riAnswerFlag = function(target, keep, mode)", "/* ── Shared bits of markup")
		self.assertIn("view: _pr.viewerRole", answer)
		self.assertIn('if (mode === "hr") {', answer)

	def test_f1_f2_answer_buttons_follow_what_the_server_says(self):
		from alvoraa_portal.tests.test_review_page_010d import _between, _page

		page = _page()
		flag = _between(page, "function riFlagNote(it)", "function riManagerRatingHtml(it)")
		self.assertIn("it.flag_answer", flag)
		self.assertIn("The person who gave this rating must keep or change it.", flag)
		submit = _between(page, "function prRenderManagerSubmitPage(d, editable)", "window.prSubmitManagerReview")
		self.assertIn('if (_pr.viewerRole === "hr") {', submit)
		self.assertIn('var inManagerReview = d.review_status === "Manager Review";', submit)
		self.assertIn("riOverallFlagHtml(d, overallMode, !!overallHtml)", submit)
		self.assertNotIn("hr_steps_elsewhere", submit)
		finalize = _between(page, "function prRenderHrFinalizePage(d)", "window.prFinishHrReview")
		self.assertIn("riOverallFlagHtml(d, overallMode, false)", finalize)
		self.assertIn("The person who gave ", finalize)
		self.assertNotIn("The manager who gave", finalize)

	def test_f3_the_calibration_note_has_buttons_and_the_box_loads_the_saved_note(self):
		from alvoraa_portal.tests.test_review_page_010d import _between, _page

		page = _page()
		hr = _between(page, "function pfHrAppraisalTable(appraisals, cycle)", "function pfHrSummary")
		in_line = _between(hr, 'a.review_status === "HR Review" && a.hr_steps_elsewhere',
		                   '} else if (a.review_status === "HR Review")')
		self.assertNotIn("pfOpenCalibNoteModal", in_line)
		hr_stage = _between(hr, '} else if (a.review_status === "HR Review")', '} else if (a.review_status === "Completed")')
		self.assertIn("pfOpenCalibNoteModal(", hr_stage)
		finalize = _between(page, "function prRenderHrFinalizePage(d)", "window.prFinishHrReview")
		self.assertIn("(hrSteps\n        ? \"<button class=\\\"btn btn-outline\\\" onclick=\\\"pfOpenCalibNoteModal(",
		              finalize.replace("\r\n", "\n"))
		box = _between(page, "window.pfOpenCalibNoteModal = function(appraisal, employeeName, from)",
		               "window.pfSubmitCalibNote")
		self.assertIn('pf("get_calibration_note", {appraisal: appraisal})', box)
