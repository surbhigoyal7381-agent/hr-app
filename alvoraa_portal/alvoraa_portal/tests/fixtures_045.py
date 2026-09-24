"""Wave 4's own fixture - its own company, its own branches, its own people,
and **its own roles**.

The roles are the point. Slice 043 found a fixture that did not own its own,
and it found it by breaking a guard on purpose and watching nothing go red: the
test had been passing because the caller happened to hold HR Manager from
another module's setup, so the guard was never the thing being tested. A
fixture that borrows a role proves whatever the site happens to be in the mood
for.

Three more rules this file follows, each paid for earlier in this project:

* **Its company is backdated.** `ensure_company()` hands every other test the
  NEWEST company on the site, so creating one here would silently become every
  other suite's company - one with no holiday list and no fiscal year. Slice
  010's `_second_company` learnt that; the creation date goes back to 2000.
* **Every field a negative check looks for is populated.** AC-6 asks that six
  Employee fields never reach a browser. An empty fixture would pass with the
  leak still live, which is Wave 3's AC-17 all over again. So date_of_birth,
  gender, cell_number, date_of_joining, reports_to and branch all carry real
  values on every person here.
* **Nobody here is a real person.** Everything carries the S045 tag.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_goals.tests.utils import (
	_ensure_erpnext_company_prerequisites,
	ensure_company,
	ensure_gender,
)
from alvoraa_portal.tests.leave_fixtures import ensure_user

TAG = "S045"
COMPANY = "S045 Wave Four Company"
ABBR = "S45W4"
STORE_A = "S045 Store A"
STORE_B = "S045 Store B"

# Every Employee field AC-6 says must never reach a browser, with a value that
# would be found if it did. The strings are distinctive on purpose: the
# assertion searches the serialised payload for them rather than checking named
# keys, because the next leak will be under a different key.
FORBIDDEN_VALUES = {
	"date_of_birth": "1988-03-17",
	"cell_number": "+91 98765 00045",
	"date_of_joining": "2019-06-03",
	"branch": STORE_A,
}


def own_company():
	"""Wave 4's company, kept the OLDEST on the site so it hijacks nobody."""
	if not frappe.db.exists("Company", COMPANY):
		ensure_company()  # on a fresh site the ordinary test company must exist first
		_ensure_erpnext_company_prerequisites()
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": COMPANY,
				"abbr": ABBR,
				"default_currency": "INR",
				"country": "India",
			}
		).insert(ignore_permissions=True)
	frappe.db.set_value("Company", COMPANY, "creation", "2000-01-01 00:00:00",
	                    update_modified=False)
	frappe.db.commit()
	return COMPANY


def own_branches():
	for branch in (STORE_A, STORE_B):
		if not frappe.db.exists("Branch", branch):
			frappe.get_doc({"doctype": "Branch", "branch": branch}).insert(
				ignore_permissions=True)
	frappe.db.commit()


def own_user(local, roles):
	"""A login holding EXACTLY the roles named, and nothing the site added.

	`ensure_user` adds roles; it does not take away the ones a previous suite
	left behind. Wave 4 needs a plain manager who is genuinely not HR, so the
	roles are set rather than added - otherwise "Sandeep is not HR" is a
	sentence in a docstring and not a fact about the fixture (043's lesson).
	"""
	user = ensure_user(f"s045.{local}@example.com", roles=roles)
	# `ensure_user` RESETS the roles rather than adding to them, which is what
	# makes "Sandeep is not HR" a fact about the fixture instead of a sentence
	# in a docstring. Asserted here rather than trusted, because the whole
	# lesson of 043 was a fixture that had quietly acquired a role from
	# somewhere else and a guard that therefore proved nothing.
	#
	# `All`, `Guest` and `Desk User` are Frappe's own - it adds `Desk User` to
	# every System User by itself, and the first run of this assertion caught
	# exactly that. They are excluded because they are the framework's, not
	# another suite's leftovers, which is what this guard is looking for.
	FRAMEWORK_ROLES = {"All", "Guest", "Desk User"}
	held = set(frappe.get_roles(user)) - FRAMEWORK_ROLES
	assert held <= set(roles), \
		f"{user} holds roles this fixture did not give it: {held - set(roles)}"
	# module_access points every new user at the site's plan profile. On a test
	# site with no plan that profile blocks every Alvoraa module, so a test
	# about OUR rules would pass or fail because of the plan.
	frappe.db.set_value("User", user, "module_profile", None, update_modified=False)
	frappe.db.delete("Block Module", {"parent": user, "parenttype": "User"})
	frappe.clear_cache(user=user)
	frappe.db.commit()
	return user


def own_employee(first, reports_to=None, user=None, branch=STORE_A, company=None):
	"""A person in Wave 4's company, with every AC-6 field populated.

	Saved through the document so Employee's nested set (lft/rgt) follows
	`reports_to` - the people-search scope reads it.
	"""
	name = frappe.db.get_value("Employee", {"first_name": first, "last_name": TAG}, "name")
	if name:
		doc = frappe.get_doc("Employee", name)
	else:
		doc = frappe.get_doc({"doctype": "Employee", "first_name": first, "last_name": TAG})
	doc.company = company or COMPANY
	doc.status = "Active"
	doc.reports_to = reports_to
	doc.user_id = user
	doc.gender = ensure_gender()
	doc.date_of_birth = FORBIDDEN_VALUES["date_of_birth"]
	doc.date_of_joining = FORBIDDEN_VALUES["date_of_joining"]
	doc.cell_number = FORBIDDEN_VALUES["cell_number"]
	doc.branch = branch
	# No automatic "Employee = self" User Permission. It narrows every list the
	# user sees, so a test about OUR rules would pass or fail because of it.
	doc.create_user_permission = 0
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	if user:
		frappe.db.delete("User Permission", {"user": user})
		frappe.clear_cache(user=user)
	frappe.db.commit()
	return doc.name


class Wave4Base(FrappeTestCase):
	"""The four personas Wave 4 is specified against, and nobody else.

	`Rahul` has no reports and is not HR. `Sandeep` manages people and is NOT
	HR - that is what makes "You cover" absent from his screen a real check.
	`Priya` is store HR with no reports. `Kamal` is both.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Start from the shipped permissions. Other suites apply plan
		# restrictions and never release them; on a fresh site that leaves the
		# Employee role without Individual Goal and Attendance Deduction, and
		# tests fail for a reason that is not ours.
		from alvoraa_portal import module_access

		module_access.release_permissions()
		own_company()
		own_branches()

		cls.rahul_user = own_user("rahul", ("Employee",))
		cls.sandeep_user = own_user("sandeep", ("Employee",))
		cls.priya_user = own_user("priya", ("Employee", "HR User"))
		cls.kamal_user = own_user("kamal", ("Employee", "HR Manager"))

		cls.sandeep = own_employee("S045Sandeep", user=cls.sandeep_user)
		cls.kamal = own_employee("S045Kamal", user=cls.kamal_user)
		cls.priya = own_employee("S045Priya", user=cls.priya_user)
		cls.rahul = own_employee("S045Rahul", reports_to=cls.sandeep, user=cls.rahul_user)

		# Sandeep's own reports. Rahul is one of them.
		cls.sandeep_reports = [cls.rahul]
		for i in range(2):
			cls.sandeep_reports.append(
				own_employee(f"S045SanReport{i}", reports_to=cls.sandeep))

		# Kamal's own report, who is ALSO in his HR scope - the "somebody who is
		# both" case AC-75 is about, and the one an engineer would guess at.
		cls.kamal_both = own_employee("S045KamalBoth", reports_to=cls.kamal)

		# People in the company who report to nobody Wave 4 cares about: the
		# covered-only population.
		cls.covered_only = [own_employee(f"S045Covered{i}") for i in range(3)]
		frappe.db.commit()

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		frappe.db.commit()

	def as_user(self, user):
		frappe.set_user(user)
		frappe.local._alvoraa_leads = {}
