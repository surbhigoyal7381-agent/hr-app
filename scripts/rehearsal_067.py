"""Slice 067 rehearsal (step R-5b of 063's runbook) on SYNTHETIC, DTC-shaped data.

Red and green money on real salary slips, made by a real Payroll Entry, checked
against the desk report. Builds on the world `tests/test_pay_slip_marks_067.py`
makes (company "L067 Slip Co", DTC's structure shape, a rule set with Junior
Rs 100 / Senior Rs 200, Contract earning no marks, 2 free reds) and adds class A
leave credits so the leave line can be checked too.

Never on a live site: refuses any site whose name ends in alvoraa.co. Every
person is fake. Prints one line per check and a RESULT line.

    docker exec -i -e SITE=test067 [-e BULK=445] <container> \\
        bash -c 'cd /home/frappe/frappe-bench/sites && ../env/bin/python -' \\
        < scripts/rehearsal_067.py

It needs slice 067's code on that container. Run it twice and it rebuilds the
month from scratch.

THE CHECKS (07-rehearsal-runbook, R-5b)
  M-1  a Payroll Entry makes every slip, and no slip logs a pricing failure
  M-2  each named slip equals its desk report row: paid days, Basic, red, green
  M-3  Contract and a grade with no rate: no line, no record
  M-4  five slips saved twice: no new record, nothing cancelled
  M-5  a back-dated fix removes a red, reprocess, re-save: one cancelled, one
       amended, the red line Rs 100 lower
  M-6  the Payroll Entry cancelled and run again: the same records, no duplicates
  M-7  a submitted slip and its record are untouched by a reprocess
  M-8  a full month worked, class A, no leave: paid days = days + 4, no Leave Encashment line
  M-9  year to date and month to date equal the slip's own net (first slip)
  M-10 timing: slip creation for everybody, with and without the red/green lines
  M-11 rollback, timed: switch off, cancel the month's engine records, re-run
"""

import os
import time

import frappe
from frappe.utils import add_days, flt

SITE = os.environ.get("SITE", "")
BULK = int(os.environ.get("BULK", "0") or 0)
if not SITE or SITE.endswith("alvoraa.co"):
	raise SystemExit("Refused: a synthetic rehearsal runs on a throwaway local site only.")

frappe.init(site=SITE, sites_path=".")
frappe.connect()
frappe.set_user("Administrator")

from alvoraa_portal import payroll_reprocess, payroll_slip  # noqa: E402
from alvoraa_portal.tests import test_pay_slip_marks_067 as w  # noqa: E402

from alvoraa_portal.alvoraa_portal.report.salary_components_and_workings import (  # noqa: E402
	salary_components_and_workings as report,
)

# Slips for more than 30 people are made by a background job; this container
# has no worker, so the job runs here and now instead.
_enqueue = frappe.enqueue
frappe.enqueue = lambda *a, **k: _enqueue(*a, **dict(k, now=True))

RED, GREEN = payroll_slip.RED_COMPONENT, payroll_slip.GREEN_COMPONENT
EXTERNAL = "L067 External"
results = []


def check(case, label, got, want):
	ok = (abs(flt(got) - flt(want)) < 0.01) if isinstance(want, (int, float)) else got == want
	results.append(ok)
	print("%-6s %-58s got %-10s want %-10s %s" % (case, label, got, want, "PASS" if ok else "FAIL"))


def line(slip, component):
	rows = [r for r in slip.earnings + slip.deductions if r.salary_component == component]
	return flt(rows[0].amount, 2) if rows else 0


def engine(emp, docstatus=None):
	f = {"employee": emp, "ref_doctype": payroll_slip.ENGINE_REF,
	     "payroll_date": ("between", [w.START, w.END])}
	if docstatus is not None:
		f["docstatus"] = docstatus
	return frappe.get_all("Additional Salary", filters=f,
	                      fields=["name", "salary_component", "amount", "docstatus", "amended_from"])


def report_row(emp):
	rows = report.execute({"company": w.COMPANY, "from_date": str(w.START),
	                       "to_date": str(w.END), "employee": emp})[1]
	return rows[0] if rows else {}


def slip_of(emp):
	name = frappe.db.get_value("Salary Slip", {"employee": emp, "start_date": w.START,
	                                           "docstatus": ("<", 2)})
	return frappe.get_doc("Salary Slip", name) if name else None


def payroll_entry(employees):
	co = frappe.get_cached_doc("Company", w.COMPANY)
	payable = co.default_payroll_payable_account or frappe.db.get_value(
		"Account", {"company": w.COMPANY, "account_type": "Payable", "is_group": 0})
	# Frappe refuses a payable account not typed Payable; the synthetic chart's isn't.
	frappe.db.set_value("Account", payable, "account_type", "Payable")
	pe = frappe.get_doc({"doctype": "Payroll Entry", "company": w.COMPANY, "posting_date": w.END,
	                     "payroll_frequency": "Monthly", "start_date": w.START, "end_date": w.END,
	                     "currency": "INR", "exchange_rate": 1, "validate_attendance": 0,
	                     "payroll_payable_account": payable, "cost_center": co.cost_center,
	                     "employees": [{"employee": e} for e in employees]})
	pe.flags.ignore_permissions = True
	pe.insert()
	pe.submit()
	frappe.db.commit()
	return pe


def cancel_entry(pe):
	pe.reload()
	pe.flags.ignore_permissions = True
	pe.cancel()
	frappe.db.commit()


def errors_since(t):
	return frappe.db.count("Error Log", {"creation": (">=", t), "method": ("like", "%" + "Sal Slip" + "%")})


# ── the world, plus class A credits and a grade with no rate ─────────────────
w.setUpModule()
rs = frappe.get_doc("Alvoraa Payroll Rule Set", w._rule_set())
rs.enabled = 1
rs.leave_class_field = "grade"
rs.accrual_month_days = 15
rs.set("leave_classes", [{"leave_class": w.JUNIOR, "period_days": 15, "credit_per_period": 4,
                          "monthly_credits": 4}])
rs.flags.ignore_permissions = True
rs.save()
if not frappe.db.exists("Employee Grade", EXTERNAL):
	w._insert({"doctype": "Employee Grade", "__newname": EXTERNAL})
frappe.db.commit()
frappe.clear_cache(doctype="Alvoraa Payroll Rule Set")

cases = {
	"J5": w._employee("RJunior", grade=w.JUNIOR),       # 5 reds -> 300
	"J2": w._employee("RJuniortwo", grade=w.JUNIOR),    # 2 reds -> free
	"S3": w._employee("RSenior", grade=w.SENIOR),       # 3 reds -> 200
	"C4": w._employee("RContract", grade=w.JUNIOR, category=w.CONTRACT),
	"X4": w._employee("RExternal", grade=EXTERNAL),     # no rate -> Rs 0
	"F0": w._employee("RFull", grade=w.JUNIOR),         # 31 full days, no leave
}
bulk = [w._employee("RBulk%03d" % i, grade=w.JUNIOR) for i in range(1, BULK + 1)]
everyone = list(cases.values()) + bulk

for pe_name in frappe.get_all("Payroll Entry", filters={"company": w.COMPANY, "start_date": w.START,
                                                        "docstatus": 1}, pluck="name"):
	cancel_entry(frappe.get_doc("Payroll Entry", pe_name))
w._wipe(*everyone)
w._wipe(*[e for e in frappe.get_all("Employee", filters={"company": w.COMPANY}, pluck="name")])
frappe.db.commit()

t0 = time.time()
for code, reds in (("J5", 5), ("J2", 2), ("S3", 3), ("C4", 4), ("X4", 4), ("F0", 0)):
	w._work(cases[code], red_days=reds)
for e in bulk:
	w._work(e, red_days=3)
frappe.db.commit()
print("built %d people in %.1f s, month %s to %s" % (len(everyone), time.time() - t0, w.START, w.END))

# ── M-10a: timing without the lines, then M-1 with them ─────────────────────
saved_lines = payroll_slip.ENGINE_LINES
payroll_slip.ENGINE_LINES = ()
t0 = time.time()
pe = payroll_entry(everyone)
without = time.time() - t0
cancel_entry(pe)
for e in everyone:
	frappe.db.delete("Additional Salary", {"employee": e})
frappe.db.commit()
payroll_slip.ENGINE_LINES = saved_lines

since = frappe.utils.now()
t0 = time.time()
pe = payroll_entry(everyone)
with_lines = time.time() - t0
made = frappe.db.count("Salary Slip", {"payroll_entry": pe.name, "docstatus": 0})
check("M-1", "slips made by the Payroll Entry", made, len(everyone))
check("M-1", "pricing failures in the Error Log", errors_since(since), 0)
check("M-10", "seconds for %d slips without lines (info)" % len(everyone), round(without, 1), round(without, 1))
check("M-10", "seconds for %d slips with lines (info)" % len(everyone), round(with_lines, 1), round(with_lines, 1))

# ── M-2, M-3, M-8, M-9 ───────────────────────────────────────────────────────
for code, red in (("J5", 300), ("J2", 0), ("S3", 200), ("C4", 0), ("X4", 0), ("F0", 0)):
	s, r = slip_of(cases[code]), report_row(cases[code])
	check("M-2", "%s red line" % code, line(s, RED), red)
	check("M-2", "%s red line = report" % code, line(s, RED), flt(r.get("red_deduction"), 2))
	check("M-2", "%s green line = report" % code, line(s, GREEN), flt(r.get("green_earning"), 2))
	check("M-2", "%s paid days = report" % code, flt(s.payment_days, 2), flt(r.get("paid_days"), 2))
	check("M-2", "%s Basic = report (to the rupee)" % code, round(line(s, w.BASIC)), round(flt(r.get("basic"))))
for code in ("C4", "X4"):
	check("M-3", "%s engine records" % code, len(engine(cases[code])), 0)
s = slip_of(cases["F0"])
check("M-8", "F0 paid days = days in month + 4", flt(s.payment_days), w.DAYS + 4)
check("M-8", "F0 Leave Encashment line", line(s, "Leave Encashment"), 0)
check("M-9", "F0 year to date = net", flt(s.year_to_date, 2), flt(s.net_pay, 2))
check("M-9", "F0 month to date = net", flt(s.month_to_date, 2), flt(s.net_pay, 2))

# ── M-4 save twice ───────────────────────────────────────────────────────────
before = frappe.db.count("Additional Salary", {"ref_doctype": payroll_slip.ENGINE_REF})
for code in ("J5", "J2", "S3", "C4", "F0"):
	s = slip_of(cases[code])
	s.flags.ignore_permissions = True
	s.save()
frappe.db.commit()
check("M-4", "engine records after five re-saves", frappe.db.count(
	"Additional Salary", {"ref_doctype": payroll_slip.ENGINE_REF}), before)
check("M-4", "cancelled engine records", frappe.db.count(
	"Additional Salary", {"ref_doctype": payroll_slip.ENGINE_REF, "docstatus": 2}), 0)

# ── M-5 a back-dated fix removes one red ─────────────────────────────────────
j5 = cases["J5"]
net_before = slip_of(j5).net_pay
first_red_day = w.START
frappe.db.delete("Employee Checkin", {"employee": j5, "time": ("like", "%s 13:00:00" % first_red_day)})
w._insert({"doctype": "Employee Checkin", "employee": j5, "time": "%s 18:00:00" % first_red_day,
           "shift": w.SHIFT})
payroll_reprocess.apply(w.COMPANY, str(w.START), str(w.END), employees=[j5], confirmed=1)
s = slip_of(j5)
s.flags.ignore_permissions = True
s.save()
frappe.db.commit()
rows = sorted(engine(j5), key=lambda r: r.docstatus)
reds = [r for r in rows if r.salary_component == RED]
check("M-5", "J5 red records: one live, one cancelled", [r.docstatus for r in reds], [1, 2])
check("M-5", "J5 new record amended from the old", reds[0].amended_from, reds[1].name)
check("M-5", "J5 red line now", line(s, RED), 200)
check("M-5", "J5 net up by at least the Rs 100 red", round(flt(s.net_pay) - flt(net_before)) >= 100, True)

# ── M-6 cancel the entry and run it again ────────────────────────────────────
live_before = sorted(r.name for r in frappe.get_all(
	"Additional Salary", filters={"ref_doctype": payroll_slip.ENGINE_REF, "docstatus": 1}, fields=["name"]))
cancel_entry(pe)
pe = payroll_entry(everyone)
live_after = sorted(r.name for r in frappe.get_all(
	"Additional Salary", filters={"ref_doctype": payroll_slip.ENGINE_REF, "docstatus": 1}, fields=["name"]))
check("M-6", "the same live records after a re-run", live_after == live_before, True)

# ── M-7 a paid slip and a reprocess ──────────────────────────────────────────
s3 = cases["S3"]
s = slip_of(s3)
s.flags.ignore_permissions = True
s.submit()
frappe.db.commit()
rec = [(r.name, r.amount, r.docstatus) for r in engine(s3)]
out = payroll_reprocess.apply(w.COMPANY, str(w.START), str(w.END), employees=[s3], confirmed=1)
check("M-7", "reprocess lists the paid slip as skipped",
      any(x["employee"] == s3 for x in out["preview"]["skipped_paid"]), True)
check("M-7", "the paid slip's records unchanged", [(r.name, r.amount, r.docstatus) for r in engine(s3)], rec)
s.reload()
s.flags.ignore_permissions = True
s.cancel()
frappe.db.commit()

# ── M-11 rollback, timed ─────────────────────────────────────────────────────
t0 = time.time()
rs.reload()
rs.enabled = 0
rs.flags.ignore_permissions = True
rs.save()
frappe.clear_cache(doctype="Alvoraa Payroll Rule Set")
for name in frappe.get_all("Additional Salary", filters={
		"ref_doctype": payroll_slip.ENGINE_REF, "docstatus": 1,
		"payroll_date": ("between", [w.START, w.END])}, pluck="name"):
	d = frappe.get_doc("Additional Salary", name)
	d.flags.ignore_permissions = True
	d.cancel()
cancel_entry(pe)
pe = payroll_entry(everyone)
took = time.time() - t0
s = slip_of(cases["J5"])
check("M-11", "after rollback: no red line", line(s, RED), 0)
check("M-11", "after rollback: paid days are Frappe's own (no credits)", flt(slip_of(cases["F0"]).payment_days) != w.DAYS + 4, True)
check("M-11", "rollback seconds (info)", round(took, 1), round(took, 1))
cancel_entry(pe)
# Leave the world as the tests expect it: on, and no leave classes.
rs.reload()
rs.enabled = 1
rs.leave_class_field = None
rs.set("leave_classes", [])
rs.flags.ignore_permissions = True
rs.save()
frappe.db.commit()

print("RESULT: %d of %d checks passed" % (sum(results), len(results)))
frappe.destroy()
