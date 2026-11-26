"""ALV-355 / ALV-474: one rule for which punches count.

A punch counts unless HR set it aside; a repeat scan within DUPLICATE_PUNCH_MINUTES is
folded by time. `skip_auto_attendance` and `offshift` are not read by the held-day and
punch-fix readers, so they judge a day exactly as the pay engine does.
"""

import frappe
from frappe.utils import getdate

from alvoraa_portal import held_day, punch_fix
from alvoraa_portal.payroll_rules_apply import _punches
from alvoraa_portal.tests.test_punch_fix_087 import CHECKIN, REQUEST, PunchFixCase, setUpModule  # noqa: F401


class OneRule(PunchFixCase):
	def four(self):
		return self.day_of([("09:00", "IN"), ("12:00", "OUT"), ("13:00", "IN"), ("18:00", "OUT")])

	def logs(self):
		return [x.time.strftime("%H:%M") for x in punch_fix.counted(self.emp, self.day)]

	def test_a_flagged_real_punch_counts_and_gives_hours(self):
		att, names = self.four()
		frappe.db.set_value(CHECKIN, names[2], "skip_auto_attendance", 1)
		self.assertEqual(self.logs(), ["09:00", "12:00", "13:00", "18:00"])
		row = frappe._dict(employee=self.emp, attendance_date=getdate(self.day), shift="ALV085 Shift")
		status, hours, *_ = held_day.worked_out(row)
		self.assertEqual((status, round(hours, 1)), ("Present", 8.0))  # 3 h + 5 h
		self.assertEqual(_punches(self.emp, self.day)[2], 4)  # the engine agrees

	def test_an_offshift_punch_counts(self):
		att, names = self.four()
		frappe.db.set_value(CHECKIN, names[1], "offshift", 1)
		self.assertEqual(len(self.logs()), 4)

	def test_a_repeat_scan_is_folded_not_double_counted(self):
		att, names = self.day_of([("09:00", "IN"), ("09:01", "IN"), ("18:00", "OUT")])
		frappe.db.set_value(CHECKIN, names[1], "skip_auto_attendance", 0)  # flagged or not, time decides
		self.assertEqual(self.logs(), ["09:00", "18:00"])
		self.assertEqual(_punches(self.emp, self.day)[2], 2)

	def test_a_punch_hr_set_aside_does_not_count(self):
		att, names = self.four()
		frappe.db.set_value(CHECKIN, names[1], punch_fix.ASIDE, "X")
		self.assertEqual(self.logs(), ["09:00", "13:00", "18:00"])

	def test_alv474_a_day_with_no_counting_punch_does_not_raise(self):
		att, names = self.day_of([("09:00", "IN"), ("18:00", "OUT")])
		for n in names:
			frappe.db.set_value(CHECKIN, n, punch_fix.ASIDE, "X")
		self.assertEqual(self.logs(), [])
		row = frappe._dict(employee=self.emp, attendance_date=getdate(self.day), shift="ALV085 Shift",
		                   company=self.h.company, status="Present")
		status, hours, late, early, first, last = held_day.worked_out(row)
		self.assertEqual((status, hours, first, last), ("Absent", 0, None, None))
		self.assertEqual(punch_fix.outcome(row)["count"], 0)

	def test_alv474_the_card_opens_when_every_punch_is_set_aside(self):
		"""An earlier approved fix set every punch aside, so the day has none left. Frappe's
		get_attendance read logs[0] and raised IndexError; `card` swallows the exception, so HR
		saw a card with no "what changes" half and no reason why (ALV-474). The request carries
		no time, so nothing is added back and the after-state really has zero punches - with a
		time the empty path is never reached and this test cannot fail."""
		att, names = self.held_three()
		req = self.fix(aside=[names[1]], note="wrong scan")  # filed while the day still had punches
		for n in names:
			frappe.db.set_value(CHECKIN, n, punch_fix.ASIDE, "X")
		frappe.set_user(self.hr)
		try:
			card = punch_fix.card(frappe.get_doc(REQUEST, req).as_dict())
		finally:
			frappe.set_user("Administrator")
		self.assertEqual([p["aside"] for p in card["now"]["punches"]], [True, True, True])
		self.assertIn("after", card)  # ALV-474: the what-changes half was calculated, not swallowed
		self.assertEqual((card["after"]["status"], card["after"]["hours"]), ("Absent", 0.0))

	def test_hr_may_set_aside_a_real_flagged_punch_but_not_one_already_set_aside(self):
		att, names = self.held_three()
		frappe.db.set_value(CHECKIN, names[2], "skip_auto_attendance", 1)
		self.fix("12:40", aside=[names[2]])  # a real punch Frappe flagged: allowed

	def test_hr_may_not_set_aside_a_punch_already_set_aside(self):
		att, names = self.held_three()
		frappe.db.set_value(CHECKIN, names[1], punch_fix.ASIDE, "X")
		self.refused(lambda: self.fix("12:40", aside=[names[1]]), "does not count already")

	def test_the_day_sheet_marks_a_flagged_real_punch_as_counted_and_a_repeat_scan_as_not(self):
		att, names = self.day_of([("09:00", "IN"), ("09:01", "IN"), ("12:00", "OUT"), ("18:00", "OUT")])
		frappe.db.set_value(CHECKIN, names[2], "skip_auto_attendance", 1)
		frappe.set_user(self.emp_user)
		try:
			sheet = punch_fix.day_sheet(self.day)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual({p["time"]: p["counted"] for p in sheet["punches"]},
		                 {"09:00": True, "09:01": False, "12:00": True, "18:00": True})
