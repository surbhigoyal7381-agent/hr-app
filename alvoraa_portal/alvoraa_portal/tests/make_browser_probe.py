"""Set a site up so `scripts/browser_check_growth_team.js` has something to see.

**Its own company, its own store, its own people and its own login.** Nothing
here is added to a company another suite reads. That rule is not fussiness: this
slice already watched a fixture hire five people into a shared company and push
another test's person on to page two of the staff directory.

**And the probe gets its OWN login, not a fixture person's.** Slice 043 borrowed
a fixture employee for a browser probe and granted him System Manager; two
Python tests then failed because he could suddenly open a colleague's month, and
they looked like permission bugs in code that had not changed. A login is shared
state on a site.

Run it in your OWN container, on your OWN site:

    bench --site test045 execute alvoraa_portal.tests.make_browser_probe.main

It prints the login and the password to use as PROBE_USR / PROBE_PWD.
"""

import frappe
from frappe.utils import add_days, nowdate

COMPANY = "S045 Probe Company"
ABBR = "S45PB"
BRANCH = "S045 Probe Store"
USER = "s045.probe@example.com"
PASSWORD = "s045-probe-Aa1!"
CYCLE = "S045 Probe Cycle"
DESIGNATION = "S045 Probe Designation"


def _company():
	from alvoraa_goals.tests.utils import (
		_ensure_erpnext_company_prerequisites,
		ensure_company,
	)

	if not frappe.db.exists("Company", COMPANY):
		ensure_company()
		_ensure_erpnext_company_prerequisites()
		frappe.get_doc({
			"doctype": "Company", "company_name": COMPANY, "abbr": ABBR,
			"default_currency": "INR", "country": "India",
		}).insert(ignore_permissions=True)
	# Backdated, so `ensure_company()` never hands this one to another suite as
	# "the newest company on the site".
	frappe.db.set_value("Company", COMPANY, "creation", "2000-01-01 00:00:00",
	                    update_modified=False)
	if not frappe.db.exists("Branch", BRANCH):
		frappe.get_doc({"doctype": "Branch", "branch": BRANCH}).insert(
			ignore_permissions=True)
	return COMPANY


def _person(first, reports_to=None, user=None):
	name = frappe.db.get_value("Employee",
	                           {"first_name": first, "last_name": "S045Probe"}, "name")
	if name:
		doc = frappe.get_doc("Employee", name)
	else:
		doc = frappe.get_doc({"doctype": "Employee", "first_name": first,
		                      "last_name": "S045Probe"})
	doc.company = COMPANY
	doc.status = "Active"
	doc.branch = BRANCH
	doc.reports_to = reports_to
	doc.date_of_joining = "2020-01-01"
	doc.date_of_birth = "1990-01-01"
	# The Designation has to exist: Employee links to it, and a link that does
	# not exist refuses the save. Created here rather than assumed, because a
	# fresh site has none.
	if not frappe.db.exists("Designation", DESIGNATION):
		frappe.get_doc({"doctype": "Designation",
		                "designation_name": DESIGNATION}).insert(ignore_permissions=True)
	doc.designation = DESIGNATION
	# Gender is mandatory on Employee. `ensure_gender` is the existing helper;
	# writing a second one here is how the two come to disagree.
	from alvoraa_goals.tests.utils import ensure_gender

	doc.gender = ensure_gender()
	doc.company_email = first.lower() + ".probe@example.com"
	doc.create_user_permission = 0
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	if user:
		# After the save, with db.set_value: setting `user_id` on the document
		# makes ERPNext save the linked User inside the Employee save, and that
		# inner save trips its own timestamp check.
		frappe.db.set_value("Employee", doc.name, "user_id", user,
		                    update_modified=False)
	return doc.name


def main():
	frappe.set_user("Administrator")
	_company()

	if frappe.db.exists("User", USER):
		user = frappe.get_doc("User", USER)
	else:
		user = frappe.get_doc({"doctype": "User", "email": USER,
		                       "first_name": "S045 Probe",
		                       "send_welcome_email": 0})
	user.roles = []
	# The preview page needs System Manager, and HR Manager is what makes the
	# "You cover" section exist so the browser check can see two sections.
	for role in ("Employee", "HR Manager", "System Manager"):
		user.append("roles", {"role": role})
	user.new_password = PASSWORD
	user.flags.ignore_permissions = True
	user.save(ignore_permissions=True)
	frappe.db.delete("User Permission", {"user": USER})
	frappe.db.set_value("User", USER, "module_profile", None, update_modified=False)
	frappe.db.delete("Block Module", {"parent": USER, "parenttype": "User"})

	me = _person("Probe", user=USER)
	# Two direct reports and two people who are only covered, so BOTH sections
	# draw and the counts are worth comparing.
	_person("ProbeReportOne", reports_to=me)
	_person("ProbeReportTwo", reports_to=me)
	_person("ProbeCoveredOne")
	_person("ProbeCoveredTwo")

	# A cycle, a goal and a KPI, so the Growth screen has something on it and
	# the approved-versus-waiting pair is real rather than described.
	if not frappe.db.exists("Appraisal Cycle", CYCLE):
		frappe.get_doc({
			"doctype": "Appraisal Cycle", "cycle_name": CYCLE,
			"company": COMPANY, "start_date": add_days(nowdate(), -30),
			"end_date": add_days(nowdate(), 60), "status": "In Progress",
		}).insert(ignore_permissions=True)
	goal = frappe.db.get_value("Individual Goal",
	                           {"employee": me, "goal_name": "S045 Probe Goal"}, "name")
	if not goal:
		goal = frappe.get_doc({
			"doctype": "Individual Goal", "employee": me,
			"goal_name": "S045 Probe Goal", "appraisal_cycle": CYCLE,
			"target_value": 100, "unit": "Lakh",
			"start_date": add_days(nowdate(), -30), "end_date": add_days(nowdate(), 60),
			"weightage": 100,
		}).insert(ignore_permissions=True).name
	kpi = frappe.db.get_value("KPI", {"employee": me, "kpi_name": "S045 Probe KPI"}, "name")
	if not kpi:
		kpi = frappe.get_doc({
			"doctype": "KPI", "kpi_name": "S045 Probe KPI", "employee": me,
			"appraisal_cycle": CYCLE, "individual_goal": goal, "unit": "Lakh",
			"target_value": 100, "actual_value": 28.4, "weightage": 100,
		}).insert(ignore_permissions=True).name
	if not frappe.db.exists("KPI Progress Log",
	                        {"parent": kpi, "approval_status": "Pending"}):
		row = frappe.get_doc({
			"doctype": "KPI Progress Log", "parent": kpi, "parenttype": "KPI",
			"parentfield": "progress_log", "log_date": nowdate(),
			"value": 3.1, "approval_status": "Pending",
		})
		row.name = frappe.generate_hash(length=10)
		row.db_insert()
	if not frappe.db.exists("Appraisal", {"employee": me, "appraisal_cycle": CYCLE}):
		frappe.get_doc({"doctype": "Appraisal", "employee": me,
		                "appraisal_cycle": CYCLE,
		                "company": COMPANY}).insert(ignore_permissions=True)

	# Seven company values, because five would let a screen that assumed five
	# look right.
	for i in range(1, 8):
		name = f"S045 Probe Value {i}"
		if not frappe.db.exists("Company Value", name):
			frappe.get_doc({"doctype": "Company Value", "value_name": name,
			                "company": COMPANY, "is_active": 1,
			                "description": f"What value {i} means here."}
			               ).insert(ignore_permissions=True)

	# ── the two site switches the browser check needs ───────────────────────
	#
	# Written here rather than left as two lines in a comment somebody has to
	# remember. Both are ordinary local site config on your OWN site.
	#
	# `staff_list` is an OPT-IN feature: a site with no `features` key falls
	# back to the whole product LESS anything opt-in, so the People entry is off
	# until the key names it. Setting the list explicitly is what a real tenant
	# with the tick has.
	import alvoraa_portal.subscription as sub
	from frappe.installer import update_site_config

	# **This changes site config, and site config is shared state.** A site with
	# no `features` key falls back to "everything less opt-in"; writing the key
	# pins it. Tests that set `frappe.conf["features"]` themselves are
	# unaffected, but any that relied on the fallback would now be reading a
	# pinned list. So `undo()` below puts it back, and the implementation notes
	# say to run it when the browser check is finished - the same discipline as
	# the throttle setting in section 13.4.
	features = sorted(set(sub.DEFAULT_ON) | {"staff_list"})
	update_site_config("features", features)
	# The preview page refuses to render without this.
	update_site_config("portal_preview", 1)

	frappe.db.commit()
	print("site config: portal_preview=1, features includes staff_list")
	print("PROBE_USR=" + USER)
	print("PROBE_PWD=" + PASSWORD)
	print("employee=" + me + "  company=" + COMPANY)
	print("Both site switches are set. Restart `bench serve` if it was already "
	      "running, because site config is read at boot.")


def undo():
	"""Put the site config back the way it was found.

	**Run this when the browser check is finished.** `features` and
	`portal_preview` are shared state on the site, and leaving them set means a
	later test run reads a pinned feature list and a preview page that answers
	when it should not.

	The people, the company and the login are left alone on purpose: they are
	this file's own, in this file's own company, and deleting an Employee with a
	linked User is a bigger operation than it looks.
	"""
	from frappe.installer import update_site_config

	update_site_config("features", None)
	update_site_config("portal_preview", None)
	print("site config: features and portal_preview removed. "
	      "The probe's own company and people are left as they are.")
