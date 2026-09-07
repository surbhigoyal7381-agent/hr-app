"""Screen an application against the rules on its Job Opening."""

import frappe
from frappe import _
from frappe.utils import cint, flt

from hrms.alvoraa_hr_core.features import feature_enabled

FEATURE = "screening_forms"
ANSWER_FIELDS = (
	"screening_retail_experience",
	"screening_years_in_category",
	"screening_product_knowledge",
	"screening_roster_ok",
	"screening_festival_ok",
	"screening_current_employer",
	"screening_category_experience",
	"screening_expected_monthly_ctc",
	"screening_availability",
)
RULE_FIELDS = (
	"screening_require_retail_experience",
	"screening_min_years",
	"screening_require_product_knowledge",
	"screening_require_roster_ok",
	"screening_require_festival_ok",
	"screening_max_monthly_ctc",
)


def rules_for(job_opening):
	if not job_opening:
		return None
	rules = frappe.db.get_value("Job Opening", job_opening, list(RULE_FIELDS), as_dict=True)
	if not rules or not any(rules.get(f) for f in RULE_FIELDS):
		return None
	return rules


def evaluate(answers, rules):
	"""(result, reasons). Result is Passed or Screened Out."""
	reasons = []
	if cint(rules.get("screening_require_retail_experience")) and answers.get("screening_retail_experience") == "No":
		reasons.append(_("no relevant retail experience"))
	min_years = cint(rules.get("screening_min_years"))
	if min_years and cint(answers.get("screening_years_in_category")) < min_years:
		reasons.append(_("{0} year(s) in the category, minimum {1}").format(
			cint(answers.get("screening_years_in_category")), min_years))
	if cint(rules.get("screening_require_product_knowledge")) and answers.get("screening_product_knowledge") == "No":
		reasons.append(_("cannot explain the product to a customer"))
	if cint(rules.get("screening_require_roster_ok")) and answers.get("screening_roster_ok") == "No":
		reasons.append(_("not comfortable with the store roster"))
	if cint(rules.get("screening_require_festival_ok")) and answers.get("screening_festival_ok") == "No":
		reasons.append(_("not available on festival days"))
	max_ctc = flt(rules.get("screening_max_monthly_ctc"))
	if max_ctc and flt(answers.get("screening_expected_monthly_ctc")) > max_ctc:
		reasons.append(_("expected CTC {0} above the band's {1}").format(
			frappe.format(flt(answers.get("screening_expected_monthly_ctc")), "Currency"),
			frappe.format(max_ctc, "Currency")))
	return ("Screened Out" if reasons else "Passed"), reasons


def screen(doc, method=None):
	"""Job Applicant validate: apply the opening's rules to the answers.
	Nothing happens without rules, or when the applicant answered nothing."""
	if not feature_enabled(FEATURE):
		return
	rules = rules_for(doc.get("job_title"))
	answered = any(doc.get(f) not in (None, "", 0) for f in ANSWER_FIELDS)
	if not rules or not answered:
		return
	result, reasons = evaluate({f: doc.get(f) for f in ANSWER_FIELDS}, rules)
	doc.screening_result = result
	doc.screening_notes = (
		_("Screened out: {0}.").format("; ".join(reasons)) if reasons else _("Passed every screening rule.")
	)
	if result == "Screened Out" and doc.is_new() and (doc.status or "Open") == "Open":
		doc.status = "Rejected"
