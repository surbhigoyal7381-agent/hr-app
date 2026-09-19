"""One figure whose data looks wrong (slice 012, SEC-13).

A record is keyed by what it is about - rule, company, branch, day - and its
name IS that key. So the morning check can run twice, or twice at once, and
never make two records for one finding: the second insert meets a primary key.
(A unique index would not do: MariaDB lets empty branch or date values repeat.)

Nobody edits a record by hand, on any path - desk, REST, set_value or import.
Only two server paths may change one, each through a flag a client cannot set:

  via_rule_check  the morning check and the page re-check: counts, and Open <-> Cleared
  via_confirm     the confirm endpoint: Open -> Confirmed, once, with who, when and the figures

A Confirmed record is never changed again by either.
"""

import hashlib

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate

DOCTYPE = "Alvoraa Data Review Item"

KEY_FIELDS = ("item_type", "rule", "company", "alvoraa_branch", "check_date")
COUNT_FIELDS = ("expected_count", "absent_count", "checked_in_count",
                "affected_count", "people_count", "days_allocated")
CONFIRM_FIELDS = ("confirmation", "confirmed_by", "confirmed_on", "figure_without", "figure_with")

CONFIRMATIONS = ("Absence was real", "Figure is right")


def item_name(rule, company, branch=None, check_date=None):
	"""The record name for one finding. The same finding always gets the same name."""
	day = str(getdate(check_date)) if check_date else ""
	raw = "|".join((rule or "", company or "", branch or "", day))
	return "DRI-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def _same(a, b, field):
	if field in ("days_allocated", "figure_without", "figure_with"):
		return (a in (None, "") and b in (None, "")) or flt(a, 2) == flt(b, 2)
	if field in COUNT_FIELDS:
		return cint(a) == cint(b)
	if field in ("check_date",):
		return (str(getdate(a)) if a else "") == (str(getdate(b)) if b else "")
	return (a or None) == (b or None) or str(a or "") == str(b or "")


class AlvoraaDataReviewItem(Document):
	def autoname(self):
		self.name = item_name(self.rule, self.company, self.alvoraa_branch, self.check_date)

	def validate(self):
		if self.is_new():
			if not self.flags.via_rule_check:
				self._refuse()
			if self.status != "Open" or any(self.get(f) for f in CONFIRM_FIELDS):
				self._refuse()
			return

		before = self.get_doc_before_save()
		if before is None:
			self._refuse()
		if any(not _same(self.get(f), before.get(f), f) for f in KEY_FIELDS):
			self._refuse()

		if self.flags.via_rule_check:
			self._check_rule_update(before)
		elif self.flags.via_confirm:
			self._check_confirmation(before)
		else:
			self._refuse()

	def _check_rule_update(self, before):
		if before.status == "Confirmed" or self.status not in ("Open", "Cleared"):
			self._refuse()
		if any(not _same(self.get(f), before.get(f), f) for f in CONFIRM_FIELDS):
			self._refuse()

	def _check_confirmation(self, before):
		if before.status != "Open" or self.status != "Confirmed":
			self._refuse()
		if self.confirmation not in CONFIRMATIONS or self.confirmed_by != frappe.session.user:
			self._refuse()
		if not self.confirmed_on:
			self._refuse()
		if any(not _same(self.get(f), before.get(f), f) for f in COUNT_FIELDS + ("first_found_on",)):
			self._refuse()

	def _refuse(self):
		from hrms.alvoraa_hr_core.access import refuse

		refuse(
			_("Data review records are kept by Alvoraa's morning check. Fix the data behind "
			  "them, or confirm them from Data to review in the portal."),
			"SEC-13", "Alvoraa Data Review Item save", DOCTYPE, self.name,
		)
