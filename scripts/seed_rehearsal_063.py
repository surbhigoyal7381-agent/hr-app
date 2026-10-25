"""Slice 063 rehearsal on SYNTHETIC, DTC-shaped data (07a section 3; Surbhi's choice).

Builds the named cases Test-901 .. Test-912 on a throwaway site, runs the pay
engine over a whole past 31-day month, and prints each case's figures beside
the figure 07a section 3.3 expects. Optionally adds BULK=n background staff
(Test-001 ..) for a timing.

Never on a live site: refuses any site whose name ends in alvoraa.co. Nothing
here reads or copies real people. Names, ids and emails are fake.

    docker exec -i -e SITE=test063 [-e BULK=40] <container> \
        bash -c 'cd /home/frappe/frappe-bench/sites && ../env/bin/python -' \
        < scripts/seed_rehearsal_063.py

It needs the slice's code on that container (leave_063_fixtures builds the
company, its enabled rule set at the NEW values, the leave types and the shift).
Run it twice and it rebuilds the cases from scratch.
"""

import os
import random
import time

import frappe
from frappe.utils import add_days, get_first_day, get_last_day, getdate

SITE = os.environ.get("SITE", "")
BULK = int(os.environ.get("BULK", "0") or 0)
if not SITE or SITE.endswith("alvoraa.co"):
	raise SystemExit("Refused: a synthetic rehearsal runs on a throwaway local site only.")

frappe.init(site=SITE, sites_path=".")
frappe.connect()
frappe.set_user("Administrator")

from alvoraa_portal.payroll_rules_apply import judge, prepare, rule_set_for  # noqa: E402
from alvoraa_portal.payroll_slip import month_summary  # noqa: E402
from alvoraa_portal.tests import leave_063_fixtures as fx  # noqa: E402

random.seed(63)
fx.ensure_world()
CO = fx.COMPANY
RS = rule_set_for(CO)
LWP = "Leave Without Pay"
PAID = fx.PAID

# The latest past month with 31 days, so every day can carry attendance and the
# figures match 07a's October worked cases (31 days, gate 15, class A gives 4).
m = get_first_day(add_days(get_first_day(frappe.utils.nowdate()), -1))
while (get_last_day(m) - m).days + 1 != 31:
	m = get_first_day(add_days(m, -1))
START, END = getdate(m), getdate(get_last_day(m))
DAYS = [add_days(START, i) for i in range(31)]
SPECIAL = DAYS[24]          # the 25th, as in the prototype
fx.set_special_day(SPECIAL, "Festive sale")


def emp(code, grade="L063-A"):
	return fx.ensure_employee("Test-%s" % code, grade=grade, branch="L063 North",
	                          reports_to=frappe.db.get_value("Employee", {"first_name": "Sunil"}, "name"))


def wipe(e):
	for la in frappe.get_all("Leave Application", filters={"employee": e}, fields=["name", "docstatus"]):
		if la.docstatus == 1:
			d = frappe.get_doc("Leave Application", la.name)
			d.flags.ignore_permissions = True
			d.cancel()
		frappe.delete_doc("Leave Application", la.name, force=True, ignore_permissions=True)
	for t in ("Attendance", "Employee Checkin", "Attendance Request"):
		frappe.db.delete(t, {"employee": e})


def punch(e, day, *times):
	for t in times:
		c = frappe.get_doc({"doctype": "Employee Checkin", "employee": e, "time": "%s %s" % (day, t)})
		c.flags.ignore_permissions = True
		c.insert()


def present(e, day, times=("10:30:00", "20:30:00"), status="Present"):
	a = frappe.get_doc({"doctype": "Attendance", "employee": e, "company": CO, "attendance_date": day,
	                    "status": status, "shift": fx.SHIFT})
	a.flags.ignore_permissions = True
	a.flags.ignore_validate = True
	a.insert()
	a.submit()
	punch(e, day, *times)
	return a.name


def leave(e, day, leave_type, half=False, approve=True, to=None):
	"""A leave in a past month: the month rule would refuse it today, so the
	seed puts it in directly (the rule itself is tested elsewhere)."""
	la = frappe.get_doc({"doctype": "Leave Application", "employee": e, "leave_type": leave_type,
	                     "from_date": day, "to_date": to or day, "half_day": 1 if half else 0,
	                     "half_day_date": day if half else None, "status": "Open", "company": CO,
	                     "leave_approver": "sunil@" + fx.DOMAIN})
	from hrms.hr.doctype.leave_application.leave_application import get_number_of_leave_days
	la.total_leave_days = get_number_of_leave_days(e, leave_type, day, to or day,
	                                               1 if half else 0, day if half else None)
	la.flags.ignore_validate = True
	la.flags.ignore_permissions = True
	la.insert()
	if approve:
		la.status = "Approved"
		la.flags.ignore_validate = True
		la.submit()
	# The leave's own attendance carries the shift, as DTC's rows do.
	frappe.db.sql("update `tabAttendance` set shift=%s where leave_application=%s", (fx.SHIFT, la.name))
	return la.name


def regularise(e, day, approve=True):
	"""The employee asks on the Attendance page (ordinary one-day form); HR decides."""
	from alvoraa_portal.attendance_correction import REQUEST

	req = frappe.get_doc({"doctype": REQUEST, "employee": e, "company": CO, "from_date": day,
	                      "to_date": day, "reason": "Forgot to Punch Out",
	                      "alvoraa_review_status": "Waiting"})
	req.flags.ignore_permissions = True
	req.insert()                       # the 063 hook runs here
	if approve:
		req.flags.ignore_permissions = True
		req.submit()
	return req


def summary(e):
	return month_summary(e, CO, START, END, rule_set=RS)


def day_credit(e, day):
	row = frappe.db.get_value("Attendance", {"employee": e, "attendance_date": day, "docstatus": 1},
	                          ["name", "employee", "attendance_date", "status", "shift", "company",
	                           "leave_type", "leave_application", "attendance_request"], as_dict=True)
	return judge(row, prepare(RS, day, day))


results = []


def check(case, label, got, want):
	ok = abs(float(got) - float(want)) < 1e-9
	results.append(ok)
	print("%-9s %-48s got %-6s want %-6s %s" % (case, label, got, want, "PASS" if ok else "FAIL"))


t0 = time.time()
cases = {c: emp(c) for c in ("901", "902", "903", "904", "905", "905d", "906", "907", "908",
                             "909", "910", "911", "912")}
for e in cases.values():
	wipe(e)

# 901: 14 days attended - gate not met
for d in DAYS[:14]:
	present(cases["901"], d)
# 902: exactly 15
for d in DAYS[:15]:
	present(cases["902"], d)
# 903: all 31
for d in DAYS:
	present(cases["903"], d)
# 904 / 906: 19 full days + the 19th as a half-day leave with the other half punched (15:30-20:30)
for code, lt in (("904", PAID), ("906", LWP)):
	for d in DAYS[:19]:
		if d != DAYS[18]:
			present(cases[code], d)
	present(cases[code], DAYS[20])
	leave(cases[code], DAYS[18], lt, half=True)
	punch(cases[code], DAYS[18], "15:30:00", "20:30:00")
# 905: as 904, one punch on the half day, HR approves the half-day correction; 905d: HR declines
for code, approve in (("905", True), ("905d", False)):
	for d in DAYS[:19]:
		if d != DAYS[18]:
			present(cases[code], d)
	present(cases[code], DAYS[20])
	leave(cases[code], DAYS[18], PAID, half=True)
	punch(cases[code], DAYS[18], "15:30:00")
	regularise(cases[code], DAYS[18], approve=approve)
# 907: 13 attended + 2 approved Paid Leaves; 908: 13 + 2 Open
for code, approve in (("907", True), ("908", False)):
	for d in DAYS[:13]:
		present(cases[code], d)
	leave(cases[code], DAYS[13], PAID, approve=approve, to=DAYS[14])
# 909: approved Paid Leaves on the special day; 910: absent on it
for d in DAYS[:20]:
	present(cases["909"], d)
	present(cases["910"], d)
leave(cases["909"], SPECIAL, PAID)
a = frappe.get_doc({"doctype": "Attendance", "employee": cases["910"], "company": CO,
                    "attendance_date": SPECIAL, "status": "Absent", "shift": fx.SHIFT})
a.flags.ignore_permissions = True
a.flags.ignore_validate = True
a.insert()
a.submit()
# 911: an automatic "Half Day" with no leave behind it (a short shift)
present(cases["911"], DAYS[0], times=("10:30:00", "15:30:00"), status="Half Day")
# 912: an Absent day later changed by a back-dated half-day leave
a = frappe.get_doc({"doctype": "Attendance", "employee": cases["912"], "company": CO,
                    "attendance_date": DAYS[5], "status": "Absent", "shift": fx.SHIFT})
a.flags.ignore_permissions = True
a.flags.ignore_validate = True
a.insert()
a.submit()
punch(cases["912"], DAYS[5], "15:30:00", "20:30:00")
leave(cases["912"], DAYS[5], PAID, half=True)
frappe.db.commit()
print("named cases built in %.1f s, month %s to %s, special day %s" % (time.time() - t0, START, END, SPECIAL))

# ── the expected figures (07a section 3.3) ──────────────────────────────────
s = summary(cases["901"]); check("Test-901", "gate not met: credits", s.leave_credits_earned, 0)
check("Test-901", "paid days = the 14 worked", s.paid_days, 14)
s = summary(cases["902"]); check("Test-902", "exactly 15: credits / paid out", s.leave_encashed, 4)
s = summary(cases["903"]); check("Test-903", "full month: paid out", s.leave_encashed, 4)
check("Test-903", "no absence", s.days_absent, 0)
check("Test-903", "paid days 31 + 4", s.paid_days, 35)
s = summary(cases["904"])
check("Test-904", "half day: days worked", s.days_worked, 19.5)
check("Test-904", "attended for the gate (E6)", s.days_for_gate, 20)
check("Test-904", "used", s.leave_used_for_approved, 0.5)
check("Test-904", "paid out", s.leave_encashed, 3.5)
v = day_credit(cases["904"], DAYS[18])
check("Test-904", "the half day: quarters / reds / greens", v.total_quarters + v.reds + v.greens, 0)
check("Test-904", "the half day pays 0.5 + the leave half", v.day_credit, 0.5)
pay904 = s.paid_days
s = summary(cases["905"]); v = day_credit(cases["905"], DAYS[18])
check("Test-905", "approved correction: half counts as worked", v.day_credit, 0.5)
check("Test-905", "no quarters", v.total_quarters, 0)
check("Test-905", "paid out", s.leave_encashed, 3.5)
v = day_credit(cases["905d"], DAYS[18])
check("Test-905d", "declined: other half absent, pays only the leave", v.day_credit, 0)
check("Test-905d", "two quarters lost", v.total_quarters, 2)
s = summary(cases["906"])
check("Test-906", "half-day LWP pays the same as 904", s.paid_days, pay904)
check("Test-906", "LWP is not 'used'", s.leave_used_for_approved, 0)
s = summary(cases["907"]); check("Test-907", "13 + 2 approved Paid Leaves: credits", s.leave_credits_earned, 4)
s = summary(cases["908"]); check("Test-908", "13 + 2 Open: credits", s.leave_credits_earned, 0)
v = day_credit(cases["909"], SPECIAL); check("Test-909", "approved leave on the special day: day", v.day_credit, 0)
check("Test-909", "not doubled", 1 if v.doubled else 0, 0)
v = day_credit(cases["910"], SPECIAL); check("Test-910", "absent on the special day: doubled", 1 if v.doubled else 0, 1)
check("Test-910", "costs one extra day", v.day_credit, -1)
v = day_credit(cases["911"], DAYS[0])
check("Test-911", "automatic Half Day judged as a full day", 1 if v.half_leave else 0, 0)
check("Test-911", "50% of the shift: 2 quarters", v.total_quarters, 2)
v = day_credit(cases["912"], DAYS[5])
check("Test-912", "Absent changed by a half-day leave", 1 if v.half_leave else 0, 1)
check("Test-912", "the punched half is worked", v.day_credit, 0.5)
s1 = summary(cases["904"]).paid_days
s2 = summary(cases["904"]).paid_days
check("check 4", "the same month twice gives the same paid days", s1, s2)

# ── a timing at a believable size ───────────────────────────────────────────
if BULK:
	t0 = time.time()
	hist = [1] * 6 + [2] * 88 + [3] * 3 + [4] * 3    # punches per day, roughly DTC-shaped
	bulk = []
	for i in range(1, BULK + 1):
		e = emp("%03d" % i, grade=random.choice(["L063-A", "L063-A", "L063-B"]))
		wipe(e)
		for d in DAYS:
			if random.random() < 0.08:
				continue
			n = random.choice(hist)
			times = ["10:%02d:00" % random.randint(20, 45), "20:%02d:00" % random.randint(0, 40),
			         "14:00:00", "14:40:00"][:n]
			present(e, d, times=sorted(times))
		bulk.append(e)
	frappe.db.commit()
	print("bulk: %d staff seeded in %.1f s" % (len(bulk), time.time() - t0))
	t0 = time.time()
	ctx = prepare(RS, START, END)
	for e in bulk:
		month_summary(e, CO, START, END, rule_set=RS, ctx=ctx)
	took = time.time() - t0
	print("month close for %d staff: %.1f s (%.2f s each; 445 staff would take about %.0f s)"
	      % (len(bulk), took, took / len(bulk), took / len(bulk) * 445))

print("RESULT: %d of %d checks passed" % (sum(results), len(results)))
frappe.destroy()
