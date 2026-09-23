"""Slice 010 group D, phase 4 · the portal page keeps the review-copy screens.

A pin for the hottest file in the repo (parallel-work.md §7): hrms-employee.html
changes in most slices. A merge that drops one of these fixes puts back a button
that deletes a live objective, or a rating box outside the review, so it should
fail here rather than in front of an employee.

Every check names the rule it keeps closed. Requirements: 00c (R2, R5, R11,
R12, R14), 00d (the page table in section 11), 01d (SEC-11, SEC-28) and 00e
(decisions 1, 2, 6, 9, 10, 12, 13, 19, 23, 29), which wins.
"""

import os
import re

from frappe.tests.utils import FrappeTestCase

import alvoraa_portal
from alvoraa_portal.tests import portal_source


def _page():
	# Read it the way Python reads a source file, BOM and all, and following
	# the page's Jinja includes (slice 034 US-10, AC-37).
	return portal_source.read_page(encoding="utf-8-sig")


def _between(page, start, end):
	return page[page.index(start):page.index(end)]


class TestR14NoRatingOutsideTheReview(FrappeTestCase):
	def test_r14_the_page_has_no_way_to_rate_a_kpi_outside_a_review(self):
		page = _page()
		# The retired endpoints have no caller left, and the dialog is gone.
		for gone in ("save_kpi_self_review", "save_kpi_manager_review", "pf-self-modal"):
			self.assertNotIn(gone, page, gone)
		# The handlers are named only in the comment that says they were removed.
		for gone in ("pfOpenSelfRating", "pfSubmitSelfRating", "pfSaveRating", "pfSuggest"):
			self.assertNotIn(f"window.{gone} =", page, gone)

	def test_r14_the_appraisal_screen_shows_no_item_rating_and_no_zero_score(self):
		page = _page()
		kra = _between(page, "KPI Performance</span>", "} else if (ap.kras")
		self.assertNotIn("g.score", kra)
		self.assertNotIn("score_earned", kra)
		self.assertIn("Rated inside the review", kra)

	def test_decision3_a_score_that_is_not_shared_yet_says_so(self):
		page = _page()
		scores = _between(page, 'var scoreHtml = "<div class=\\"gp-score-grid\\">"', "var kraHtml;")
		self.assertIn("Not shared yet", scores)
		self.assertIn("s.val === null", scores)


class TestR5BadgeOnLiveRecords(FrappeTestCase):
	def test_r5_the_badge_says_what_it_means_and_carries_nothing_else(self):
		page = _page()
		badge = _between(page, "window.riReviewBadge = function(badge)", "/* What changed inside the review")
		self.assertIn("updates dated after", badge)
		self.assertIn("gpFmtDate(badge.updates_after)", badge)
		# No review name, rating or link ever reaches the badge.
		for leak in ("appraisal", "rating", "<a "):
			self.assertNotIn(leak, badge, leak)

	def test_r5_the_tree_the_drawer_the_detail_and_the_log_box_all_draw_it(self):
		page = _page()
		self.assertIn("tvCycleTag(g.review_badge)", page)
		self.assertIn("tvCycleTag(k.review_badge)", page)
		self.assertIn("window.riReviewBadge(g.review_badge)", page)
		self.assertIn("riReviewBadge(g.review_badge)", page)
		log = _between(page, "window.pfOpenLog = function(kpiId, focusRow)", "window.pfLogFileChanged")
		self.assertIn("riReviewBadge(k.review_badge)", log)


class TestR12RemovalFromTheReview(FrappeTestCase):
	def test_r11_r12_remove_no_longer_deletes_the_objective_or_the_kpi(self):
		page = _page()
		# Both old buttons now open the one dialog, which calls remove_review_item.
		self.assertIn("window.prRemoveGoalFromReview = function(rowName) { riOpenRemove(rowName); };", page)
		self.assertIn("window.prRemoveKpiFromReview  = function(rowName) { riOpenRemove(rowName); };", page)
		remove = _between(page, "window.riConfirmRemove = function()", "/* ── Rate one item")
		self.assertIn("remove_review_item", remove)
		self.assertIn("delete_review_item", remove)
		self.assertIn("acknowledge: 1", remove)
		# goals_api.delete_goal is still reachable from the ordinary Goals screen,
		# which is what the older pin test checks; it is not reachable from a review.
		review = _between(page, "window.riOpenRemove = function(rowName)", "/* ── Rate one item")
		self.assertNotIn("delete_goal", review)
		self.assertNotIn("delete_kpi", review)

	def test_r12_the_warning_says_what_is_lost_and_what_is_kept(self):
		page = _page()
		warn = _between(page, "window.riOpenRemove = function(rowName)", "window.riSwitchToDelete")
		self.assertIn("will be lost", warn)
		self.assertIn("stay on the live record", warn)

	def test_decision10_a_reason_is_required_of_everyone_but_the_subject(self):
		page = _page()
		self.assertIn("function riReasonRequired() { return !!_pr.viewerRole; }", page)
		confirm = _between(page, "window.riConfirmRemove = function()", "/* ── Rate one item")
		self.assertIn("riReasonRequired() && !reason", confirm)

	def test_decision10_removed_items_are_shown_with_who_when_and_why(self):
		page = _page()
		removed = _between(page, "window.riRemovedHtml = function(d)", "/* The numbers are closed")
		self.assertIn("line-through", removed)
		self.assertIn("removal_reason", removed)
		self.assertIn("removed_on", removed)
		self.assertIn("Taken out of this review", removed)


class TestR2EditInsideTheReview(FrappeTestCase):
	def test_r2_decision6_edit_changes_the_copy_not_the_live_record(self):
		page = _page()
		self.assertIn('id="ri-edit-modal"', page)
		save = _between(page, "window.riSaveEditItem = function()", "/* ── Take an item out")
		self.assertIn("save_review_item_definition", save)
		self.assertNotIn("gpOpenEditGoal", save)
		# The old route into the live objective's form is gone.
		self.assertIn("window.prOpenGoalEditForReview = function(rowName) { riOpenEditItem(rowName); };", page)

	def test_decision6_decision29_the_page_offers_each_action_only_at_its_stage(self):
		page = _page()
		edit = _between(page, "function riCanEditDefinition()", "function riCanRemove()")
		self.assertIn('_pr.viewerRole === "manager" && st === "Manager Review"', edit)
		remove = _between(page, "function riCanRemove()", "function riCanRateAsManager()")
		self.assertIn('_pr.viewerRole === "hr")      return st === "HR Review"', remove)


class TestR7RatingQuestions(FrappeTestCase):
	def test_decision12_the_manager_can_keep_or_change_a_flagged_rating(self):
		page = _page()
		# Decision 37: the answer carries the mode the server gave for this view.
		self.assertIn("window.riAnswerFlag = function(target, keep, mode)", page)
		self.assertIn("answer_rating_flag", page)
		self.assertIn("riAnswerFlag('overall',1,'\" + mode + \"')", page)
		self.assertIn("riAnswerFlag('overall',0,'\" + mode + \"')", page)

	def test_decision13_a_self_rating_question_is_information_only(self):
		page = _page()
		note = _between(page, "function riFlagNote(it)", "/* The manager's rating box")
		self_part = note[note.index("it.self_flag"):note.index("it.manager_flag")]
		self.assertIn("does not block", self_part)
		self.assertNotIn("riAnswerFlag", self_part)

	def test_sec23_hr_cannot_finish_while_a_rating_waits_for_an_answer(self):
		page = _page()
		finalize = _between(page, "function prRenderHrFinalizePage(d)", "window.prFinishHrReview")
		self.assertIn("open_blocking_flags", finalize)
		self.assertIn('(open ? " disabled', finalize)

	def test_r7_the_reviews_list_says_a_rating_needs_an_answer(self):
		page = _page()
		card = _between(page, "function pfTeamReviewCard(m)", "window.prOpenManagerReview")
		self.assertIn("m.rating_needs_answer", card)
		self.assertIn("Rating needs your answer", card)


class TestVis3ThePageSpeaksRowNames(FrappeTestCase):
	def test_vis3_review_screens_key_everything_by_the_copys_row_name(self):
		page = _page()
		index = _between(page, "window.riIndex = function(items)", "function riItem(rowName)")
		self.assertIn("_riItems[it.name] = it;", index)
		goals_page = _between(page, "function prRenderGoalsPage(d, saved, editable, title)",
		                      "function prRenderHierarchicalGoals")
		self.assertIn("riIndex(goals);", goals_page)
		self.assertIn("riIndex(standalone);", goals_page)

	def test_r3_progress_is_never_typed_into_a_review(self):
		page = _page()
		collect = _between(page, "function prCollectPageData(key)", "function prRenderPage(key, editable)")
		self.assertNotIn("actual_progress", collect)
		self.assertNotIn("pr-obj-progress-inp", page)

	def test_a_manager_opening_their_own_review_is_not_treated_as_a_manager(self):
		page = _page()
		open_own = _between(page, "window.prOpenReview = function(appraisalName)", "function prBuildNav()")
		self.assertIn("_pr.viewerRole = null;", open_own)


class TestDecision19FutureObjectives(FrappeTestCase):
	def test_decision19_carrying_forward_has_no_delete_button_at_all(self):
		page = _page()
		carry = _between(page, "function prCarryItem(g, carryData, editable, showCycleLabel)",
		                 "function prRenderFutureObjectivesPage")
		self.assertNotIn("prRemoveGoalFromReview", carry)
		self.assertNotIn("prOpenGoalEditForReview", carry)
		self.assertIn("Unticking the box", carry)


class TestDecision1And2TheKpiUpdateBox(FrappeTestCase):
	def test_decision1_the_box_asks_for_the_amount_since_the_last_update(self):
		page = _page()
		self.assertIn("Amount since your last update *", page)
		log = _between(page, "window.pfOpenLog = function(kpiId, focusRow)", "window.pfLogFileChanged")
		self.assertIn("Not the running total", log)
		self.assertIn("The reading now *", log)

	def test_decision2_the_box_offers_the_day_the_reading_is_for(self):
		page = _page()
		self.assertIn('id="pf-log-date"', page)
		self.assertRegex(page, r'<label class="gp-label" for="pf-log-date">')
		submit = _between(page, "window.pfSubmitLog = async function()", "/* ── Update history")
		self.assertIn('log_date: pfVal("pf-log-date")', submit)
		log = _between(page, "window.pfOpenLog = function(kpiId, focusRow)", "window.pfLogFileChanged")
		# No future day can even be picked.
		self.assertIn('document.getElementById("pf-log-date").max', log)


class TestDecision23TheSettingsOnOrgSettings(FrappeTestCase):
	def test_decision23_the_three_settings_have_a_labelled_field_each(self):
		page = _page()
		self.assertIn('id="org-review-card"', page)
		for field in ("org-review-freeze", "org-review-lock", "org-review-removal"):
			self.assertIn(f'id="{field}"', page)
			self.assertIn(f'for="{field}"', page)

	def test_decision23_the_card_loads_with_the_screen_and_saves_through_hr_settings(self):
		page = _page()
		switch = _between(page, 'if (name === "org-settings")', "/* ── Live clock")
		self.assertIn("riLoadSettings()", switch)
		save = _between(page, "window.riSaveSettings = function()", "window.orgSaveKraMandatory")
		self.assertIn("save_review_settings", save)
		# Not the Global Defaults writer that slice 012 had to limit.
		self.assertNotIn("set_org_setting", save)

	def test_sec28_an_hr_user_who_cannot_save_is_not_offered_the_button(self):
		page = _page()
		load = _between(page, "window.riLoadSettings = function()", "window.riSaveSettings")
		self.assertIn("el.disabled = !s.can_edit;", load)
		self.assertIn('save.style.display = s.can_edit ? "" : "none";', load)


class TestSec11EverythingFromACopyIsEscaped(FrappeTestCase):
	def test_sec11_the_add_remove_dialog_escapes_every_name_it_draws(self):
		page = _page()
		modal = _between(page, "function _prShowSelectorModal(type, data)", "function prRefreshCurrentPage")
		self.assertIn('value=\\"" + gpEsc(item.name)', modal)
		self.assertIn('gpEsc(label)', modal)
		self.assertIn('gpEsc(parts.join(" · "))', modal)

	def test_sec11_removal_reasons_and_flag_text_are_escaped(self):
		page = _page()
		for block, start, end in (
			("removed", "window.riRemovedHtml = function(d)", "/* The numbers are closed"),
			("flags", "function riFlagNote(it)", "/* The manager's rating box"),
		):
			text = _between(page, start, end)
			# Nothing from the server is written into the page unescaped.
			raw = re.findall(r'"\s*\+\s*(?:r|it)\.[a-z_]+\s*\+', text)
			self.assertEqual(raw, [], f"{block}: {raw}")
