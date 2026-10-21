"""Slice 063 release steps, for a LOCAL COPY of DTC's data first.

Read with docs/slices/063-dtc-leave-credit-and-lwp/07-rehearsal-runbook.md,
which says the order, who runs each step and what evidence to keep.

Run inside a bench container, with the site named in SITE, by piping this file:

    docker exec -i -e SITE=dtc-copy.local -e STEP=checks <container> \
        bash -c 'cd /home/frappe/frappe-bench/sites && ../env/bin/python -' \
        < scripts/rehearsal_063.py

STEP is one of:

  checks      READ ONLY. RC-7 to RC-11 and the rule set's current values, as
              counts - no names. Safe on any site.
  cost        READ ONLY. The month's paid days and Basic under the OLD rule set
              values and under the NEW ones, summed (01e section 5, item 6).
              Worked out in memory; nothing is saved. MONTH=2026-10 picks it.
  settings    WRITES. Puts the new values (spec 7.4) on the rule set, through the
              document, so a Version row keeps old and new, and adds a comment
              quoting Surbhi's decision. Local copy only.
  rollback    WRITES. Puts the old values back. Local copy only. Timed.
  paid-type   WRITES. Creates "Paid Leaves" with the spec 7.3 flags. Local copy.
  switch-on / switch-off
              WRITES. The rule set's enabled tick. Local copy only.

Every WRITE step refuses a site whose name ends in alvoraa.co. On production the
same changes are made by a System Manager in the desk, from the runbook's list -
AC-105: no script on production.
"""

import json
import os
import time

import frappe

SITE = os.environ.get("SITE", "")
STEP = os.environ.get("STEP", "checks")
COMPANY = os.environ.get("COMPANY", "Durga Trading Company")

# Spec 7.4 / 01e section 3. (period_days, credit_per_period, monthly_credits)
OLD = {"accrual_month_days": 30, "classes": {"A": (7.5, 1, 4), "B": (10, 1, 3), "C": (7.5, 0.5, 2)}}
NEW = {"accrual_month_days": 15, "classes": {"A": (15, 4, 4), "B": (15, 3, 3), "C": (15, 2, 2)}}
DECISION = ("Surbhi, 21 Oct 2026, after checking with DTC: \"there is no process of accrual, all "
            "leaves are credited in the beginning of the month and remaining ones encashed with the "
            "salary.\" The 15-day minimum stays. Slice 063, US-23.")
PAID_FLAGS = {"is_lwp": 0, "allow_negative": 1, "include_holiday": 1, "allow_encashment": 0,
              "is_carry_forward": 0, "is_earned_leave": 0}

WRITES = {"settings", "rollback", "paid-type", "switch-on", "switch-off"}


def say(*a):
	print(*a, flush=True)


def rule_set():
	name = frappe.db.get_value("Alvoraa Payroll Rule Set", {"company": COMPANY}, "name")
	if not name:
		raise SystemExit("No rule set for %s on %s" % (COMPANY, SITE))
	return frappe.get_doc("Alvoraa Payroll Rule Set", name)


def show(rs):
	say("rule set enabled:", rs.enabled, "| leave_threshold_days:", rs.leave_threshold_days,
	    "| accrual_month_days:", rs.accrual_month_days)
	for r in rs.leave_classes:
		say("  class", r.leave_class, ":", r.period_days, "/", r.credit_per_period, "/", r.monthly_credits)


def checks():
	rs = rule_set()
	show(rs)
	active = {"status": "Active", "company": COMPANY}
	lwp = frappe.get_all("Leave Type", filters={"is_lwp": 1}, pluck="name")
	say("RC-7 leave types marked leave without pay:", len(lwp),
	    "| types allowing encashment:", frappe.db.count("Leave Type", {"allow_encashment": 1}),
	    "| Leave Encashment records:", frappe.db.count("Leave Encashment"))
	if frappe.db.exists("Leave Type", "Paid Leaves"):
		row = frappe.db.get_value("Leave Type", "Paid Leaves", list(PAID_FLAGS), as_dict=True)
		say("RC-6 Paid Leaves flags as expected:", all(int(row[k] or 0) == v for k, v in PAID_FLAGS.items()))
	else:
		say("RC-6 Paid Leaves: not created yet")
	from hrms.hr.doctype.leave_application.leave_application import get_employee_leave_approver
	emps = frappe.get_all("Employee", filters=active, pluck="name")
	say("RC-8 active staff with no Paid Leaves approver:",
	    sum(1 for e in emps if not get_employee_leave_approver(e)), "of", len(emps))
	hr = set(frappe.get_all("Has Role", filters={"role": ["in", ["HR Manager", "HR User", "System Manager"]],
	                                              "parenttype": "User"}, pluck="parent"))
	logins = frappe.get_all("Employee", filters=dict(active, user_id=["is", "set"]), fields=["name", "user_id"])
	staff = [l for l in logins if l.user_id not in hr]
	missing = sum(1 for l in staff if not frappe.db.exists(
		"User Permission", {"user": l.user_id, "allow": "Employee", "for_value": l.name}))
	say("RC-9 non-HR logins without a User Permission on their own record:", missing, "of", len(staff))
	rows = {e.name: e for e in frappe.get_all("Employee", filters={"company": COMPANY},
	                                          fields=["name", "reports_to", "status"])}
	loops = inactive = 0
	for e in rows.values():
		if e.status != "Active":
			continue
		seen, node = {e.name}, e.reports_to
		while node:
			if node in seen:
				loops += 1
				break
			seen.add(node)
			m = rows.get(node)
			if not m or m.status != "Active":
				inactive += 1
				break
			node = m.reports_to
	say("RC-10 Reports To loops:", loops, "| lines that reach a non-Active manager:", inactive)
	for role in ("Leave Approver", "Location Manager"):
		users = frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent")
		say("RC-11 users holding", role, ":", len(set(users)) if users else 0,
		    "(each must not read DTC leave reasons on the desk - check their roles' Leave Application read)")
	say("half-day leave attendance rows:", frappe.db.count("Attendance", {
		"company": COMPANY, "status": "Half Day", "leave_application": ["is", "set"], "docstatus": 1}))


def _with(rs, values):
	"""A copy of the rule set carrying `values`, in memory only."""
	copy = frappe.copy_doc(rs, ignore_no_copy=False)
	copy.name = rs.name
	copy.accrual_month_days = values["accrual_month_days"]
	for r in copy.leave_classes:
		v = values["classes"].get((r.leave_class or "").strip())
		if v:
			r.period_days, r.credit_per_period, r.monthly_credits = v
	return copy


def cost():
	from frappe.utils import get_first_day, get_last_day

	from alvoraa_portal.payroll_rules_apply import prepare
	from alvoraa_portal.payroll_slip import month_summary

	month = os.environ.get("MONTH") or frappe.utils.nowdate()[:7]
	start = get_first_day(month + "-01")
	end = get_last_day(start)
	rs = rule_set()
	out = {}
	for label, values in (("old (accrual)", OLD), ("new (given on the 1st)", NEW)):
		copy = _with(rs, values)
		ctx = prepare(copy, start, end)
		days = basic = credits = 0.0
		people = 0
		for e in frappe.get_all("Employee", filters={"company": COMPANY, "status": "Active"}, pluck="name"):
			s = month_summary(e, COMPANY, start, end, rule_set=copy, ctx=ctx)
			if not s:
				continue
			people += 1
			days += s.paid_days
			basic += s.earning_basic
			credits += s.leave_credits_earned
		out[label] = (people, round(days, 2), round(credits, 2), round(basic, 2))
		say(label, "| people:", people, "| paid days:", round(days, 2), "| credits:", round(credits, 2),
		    "| earning Basic:", round(basic, 2))
	(o, n) = (out["old (accrual)"], out["new (given on the 1st)"])
	say("EXTRA COST for", month, "against accrual: paid days +%.2f, Basic +%.2f" % (n[1] - o[1], n[3] - o[3]))


def put(values, note):
	rs = rule_set()
	t0 = time.time()
	rs.accrual_month_days = values["accrual_month_days"]
	for r in rs.leave_classes:
		v = values["classes"].get((r.leave_class or "").strip())
		if v:
			r.period_days, r.credit_per_period, r.monthly_credits = v
	rs.save()
	rs.add_comment("Comment", note)
	frappe.db.commit()
	say("saved in %.2f s" % (time.time() - t0))
	show(rs)


def paid_type():
	if frappe.db.exists("Leave Type", "Paid Leaves"):
		say("Paid Leaves already exists - nothing done")
		return
	doc = frappe.get_doc(dict({"doctype": "Leave Type", "leave_type_name": "Paid Leaves"}, **PAID_FLAGS))
	doc.insert()
	frappe.db.commit()
	say("Paid Leaves created")


def switch(on):
	rs = rule_set()
	rs.enabled = 1 if on else 0
	rs.save()
	frappe.db.commit()
	say("rule set enabled =", rs.enabled)


def main():
	if not SITE:
		raise SystemExit("Set SITE")
	if STEP in WRITES and SITE.endswith("alvoraa.co"):
		raise SystemExit("Refused: %s changes data, and %s is a live site. On production a "
		                 "System Manager makes this change in the desk from the runbook." % (STEP, SITE))
	frappe.init(site=SITE, sites_path=".")
	frappe.connect()
	frappe.set_user("Administrator")
	try:
		if STEP == "checks":
			checks()
		elif STEP == "cost":
			cost()
		elif STEP == "settings":
			put(NEW, DECISION)
		elif STEP == "rollback":
			put(OLD, "Rolled back to the accrual values (slice 063 rollback, rehearsed).")
		elif STEP == "paid-type":
			paid_type()
		elif STEP in ("switch-on", "switch-off"):
			switch(STEP == "switch-on")
		else:
			raise SystemExit("Unknown STEP %s" % STEP)
	finally:
		if STEP not in WRITES:
			frappe.db.rollback()
		frappe.destroy()


main()
