"""Slice 063 demo: a throwaway local site where Surbhi can see the leave rules work.

Synthetic, DTC-shaped data only (07a section 3). Never a live site: refuses any
site whose name ends in alvoraa.co. Run by piping into the demo container:

    docker exec -i -e SITE=leave-demo.localhost hrlocal-063 \
        bash -c 'cd /home/frappe/frappe-bench/sites && ../env/bin/python -' < demo/leave_demo_063.py

Builds, for the CURRENT month up to yesterday:
  Priya  (class A, login)  16 days attended; an approved half-day Paid Leaves
                           with only one punch on the other half (the missed punch)
  Rohit  (class A, login)  10 days attended - under the 15-day line
  Manoj  (Contract, no login)
  Sunil  (store manager, Priya's and Rohit's leave approver, login)
  Kavita (top of the chain, login)
  Ritika (HR Manager, login)
  Test-901..905 and 24 background staff, shaped like 07a's cases.
The demo passwords exist only on this site.
"""

import os
import random

import frappe
from frappe.utils import add_days, get_first_day, getdate, nowdate

SITE = os.environ.get("SITE", "")
if not SITE or SITE.endswith("alvoraa.co"):
	raise SystemExit("Refused: the demo runs on a throwaway local site only.")
PASSWORDS = {"Priya": "Priya@063demo", "Ritika": "Ritika@063demo", "Sunil": "Sunil@063demo",
             "Kavita": "Kavita@063demo", "Rohit": "Rohit@063demo"}

frappe.init(site=SITE, sites_path=".")
frappe.connect()
frappe.set_user("Administrator")
from frappe.utils.password import update_password  # noqa: E402

from alvoraa_portal.tests import leave_063_fixtures as fx  # noqa: E402

random.seed(631)
P = fx.ensure_world()
fx.clear_leave(*P.values())
CO = fx.COMPANY
today = getdate(nowdate())
first = get_first_day(today)
past = [add_days(first, i) for i in range((today - first).days)]   # 1st .. yesterday
if len(past) < 16:
	raise SystemExit("Run this after the 17th of the month, or the 15-day line cannot be shown.")

for name, pw in PASSWORDS.items():
	update_password(fx.user(name), pw)
# A special day later this month, so the preview can show its line.
fx.set_special_day(add_days(today, 3) if add_days(today, 3) <= frappe.utils.get_last_day(today)
                   else add_days(today, 1), "Festive sale")


def punch(e, day, *times):
	for t in times:
		c = frappe.get_doc({"doctype": "Employee Checkin", "employee": e, "time": "%s %s" % (day, t)})
		c.flags.ignore_permissions = True
		c.insert()


def present(e, day, times=("10:31:00", "20:34:00")):
	a = frappe.get_doc({"doctype": "Attendance", "employee": e, "company": CO, "attendance_date": day,
	                    "status": "Present", "shift": fx.SHIFT})
	a.flags.ignore_permissions = True
	a.flags.ignore_validate = True
	a.insert()
	a.submit()
	punch(e, day, *times)


def half_leave(e, day, approver, punches):
	la = frappe.get_doc({"doctype": "Leave Application", "employee": e, "leave_type": fx.PAID,
	                     "from_date": day, "to_date": day, "half_day": 1, "half_day_date": day,
	                     "status": "Open", "company": CO, "leave_approver": approver,
	                     "description": "Family function (demo)"})
	la.insert(ignore_permissions=True)
	frappe.set_user(approver)
	la = frappe.get_doc("Leave Application", la.name)
	la.status = "Approved"
	la.submit()
	frappe.set_user("Administrator")
	frappe.db.sql("update `tabAttendance` set shift=%s where leave_application=%s", (fx.SHIFT, la.name))
	punch(e, day, *punches)
	return la.name


def staff(code, grade="L063-A"):
	return fx.ensure_employee("Test-%s" % code, grade=grade, branch="L063 North",
	                          reports_to=P["sunil"], approver=fx.user("Sunil"))


# Priya: 16 days attended, and on the 3rd day a half-day leave whose other half
# has only one punch - the missed punch to correct.
missed = past[2]
for d in past[:17]:
	if d != missed:
		present(P["priya"], d)
half_leave(P["priya"], missed, fx.user("Sunil"), ("15:32:00",))
# Rohit: 10 days attended - the card's "under 15" view.
for d in past[:10]:
	present(P["rohit"], d)
# Manoj (Contract) and the managers attend too, so the Team page has a day.
for e in (P["manoj"], P["sunil"], P["kavita"], P["ritika"]):
	for d in past:
		present(e, d)

# 07a's named cases, this month so far (the desk report shows them).
cases = {c: staff(c) for c in ("901", "902", "903", "904", "905")}
fx.clear_leave(*cases.values())
for d in past[:14]:
	present(cases["901"], d)
for d in past[:15]:
	present(cases["902"], d)
for d in past:
	present(cases["903"], d)
for code, punches in (("904", ("15:30:00", "20:30:00")), ("905", ("15:30:00",))):
	for d in past[:16]:
		if d != past[5]:
			present(cases[code], d)
	half_leave(cases[code], past[5], fx.user("Sunil"), punches)
# Test-905's missed punch, put right the way OD-1 (iv) says: the ordinary
# correction, approved by someone other than the employee.
from alvoraa_portal.attendance_correction import REQUEST  # noqa: E402

req = frappe.get_doc({"doctype": REQUEST, "employee": cases["905"], "company": CO,
                      "from_date": past[5], "to_date": past[5], "reason": "Forgot to Punch Out",
                      "alvoraa_review_status": "Waiting"})
req.insert(ignore_permissions=True)
req.submit()

# Background staff, DTC-shaped punches.
hist = [1] * 6 + [2] * 88 + [3] * 3 + [4] * 3
for i in range(1, 25):
	e = staff("%03d" % i, grade=random.choice(["L063-A", "L063-A", "L063-B"]))
	fx.clear_leave(e)
	for d in past:
		if random.random() < 0.08:
			continue
		n = random.choice(hist)
		times = sorted(["10:%02d:00" % random.randint(20, 45), "20:%02d:00" % random.randint(0, 40),
		                "14:00:00", "14:40:00"][:n])
		present(e, d, times)

frappe.db.commit()
print("demo ready on", SITE, "| month so far:", past[0], "to", past[-1],
      "| Priya's missed punch:", missed)
frappe.destroy()
