import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class HolidayList(Document):
	def validate(self):
		self.validate_days()
		self.total_holidays = len([h for h in self.holidays if not h.weekly_off])

	def validate_days(self):
		if self.from_date and self.to_date and getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("'From Date' must be before 'To Date'"))


def is_holiday(holiday_list, date=None, daily_wages_applicable=False):
	if not date:
		date = frappe.utils.today()
	if not holiday_list:
		return False
	return bool(
		frappe.db.get_value(
			"Holiday",
			{"parent": holiday_list, "holiday_date": date, "weekly_off": 0},
			"name",
		)
	)


def is_half_holiday(holiday_list, date):
	if not holiday_list:
		return False
	return bool(
		frappe.db.get_value(
			"Holiday",
			{"parent": holiday_list, "holiday_date": date, "is_half_day": 1},
			"name",
		)
	)
