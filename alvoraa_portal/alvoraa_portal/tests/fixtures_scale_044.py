"""Slice 044: the two scale fixtures Wave 2's section 13 asked for.

Wave 2 wrote every performance number in its spec as a target and then said, in
its own notes, that **no fixture existed to test any of them** and called that
"dangerous debt". This file is the fixture.

Two shapes, because the two things we need to know are different:

    LARGE   1,000 people, 4 companies, 16 stores, a real manager tree.
            The shape nobody has ever measured, and the one the 16.4-second
            bell came from.
    SMALL   20 people, one store, one company.
            The shape most customers will actually be.

**A tenant is a site in this product**, not a company inside a site. That is not
a detail: `permitted_companies()` gives a System Manager *every company on the
site*, so a 20-person tenant measured on a site that also holds 1,000 people is
not a 20-person tenant at all. So each shape gets its own site, and
`build(shape)` is told which one it is building.

## How the records are made

Through the ORM and the normal flow: `frappe.get_doc(...).insert()`, and
`.submit()` where the doctype is submittable, with validation left on. A fixture
that writes its rows in their final shape can make a wrong answer look right,
and this project has paid for that three times (demo/README.md, first section).

**The two places this bends, and why each is the normal flow too:**

1. `ignore_update_nsm` during the bulk employee load, with one
   `rebuild_tree("Employee", "reports_to")` at the end. Frappe ships
   `rebuild_tree` for exactly this; updating the nested set once per insert is
   O(n) per row and turns a 1,000-person load into an hour. The tree that comes
   out is the same tree.
2. The holiday list is set as the **company default** rather than assigned per
   employee. That is how a real tenant is configured; per-employee assignment
   would be 1,000 extra submitted documents to reach the same answer.

## Reuse — the whole point

Building is idempotent and cheap to skip: `is_built(shape)` is one query. Call
`build()` again and it returns in well under a second. The site is the artifact;
nothing here needs rebuilding between test runs or between slices. Section
"Reuse" of `docs/slices/044-scale-fixtures/04-test-report.md` says how to take a
copy so a rebuild is never needed at all.

Every person here is invented. No real name, no real identifier, nothing copied
from any tenant.
"""

import time

import frappe
from frappe.utils import add_days, nowdate

TAG = "S044"

# ── The two shapes ───────────────────────────────────────────────────────────

SHAPES = {
	"large": {
		"prefix": "S044L",
		"companies": 4,
		"branches_per_company": 4,
		"leads_per_branch": 3,
		"staff_per_lead": 19,
		# Attendance history, in days back from today, for everybody.
		"attendance_days": 10,
		# Roughly one in this many people has an open leave request.
		"leave_every": 16,
		"corrections": 40,
		"goals_for": 240,
		"goal_updates": 60,
	},
	"small": {
		"prefix": "S044S",
		"companies": 1,
		"branches_per_company": 1,
		"leads_per_branch": 1,
		"staff_per_lead": 15,
		"attendance_days": 10,
		"leave_every": 6,
		"corrections": 3,
		"goals_for": 12,
		"goal_updates": 4,
	},
}

# The five personas, identical in both shapes so the comparison is like for like.
PERSONAS = (
	("emp", ("Employee",)),
	("mgr", ("Employee",)),
	("storehr", ("HR User", "Employee")),
	("companyhr", ("HR Manager", "Employee")),
	("sysmgr", ("System Manager", "Employee")),
)


def shape_of(name):
	if name not in SHAPES:
		raise ValueError("unknown shape %r - one of %s" % (name, sorted(SHAPES)))
	return SHAPES[name]


def login_of(shape, persona):
	return "%s.%s@example.com" % (shape_of(shape)["prefix"].lower(), persona)


def company_of(shape, n=1):
	return "%s Company %d" % (shape_of(shape)["prefix"], n)


def branch_of(shape, company_n, branch_n):
	return "%s Store %d-%d" % (shape_of(shape)["prefix"], company_n, branch_n)


def headcount(shape):
	s = shape_of(shape)
	per_company = 1 + s["branches_per_company"] * (
		1 + s["leads_per_branch"] * (1 + s["staff_per_lead"]))
	return s["companies"] * per_company


# ── Is it already there? ─────────────────────────────────────────────────────


def is_built(shape):
	"""One query. This is what makes the fixture free to reuse."""
	s = shape_of(shape)
	return bool(frappe.db.exists("Employee", {"last_name": s["prefix"],
	                                          "first_name": "Sysmgr"}))


def count_built(shape):
	s = shape_of(shape)
	return frappe.db.count("Employee", {"last_name": s["prefix"]})


# ── Small helpers, each the ordinary Frappe way ──────────────────────────────


class Clock:
	"""Says how long each step took, because 'how long does it take to build'
	is half of what makes a fixture get used."""

	def __init__(self):
		self.start = time.time()
		self.last = self.start
		self.steps = []

	def step(self, label, extra=""):
		now = time.time()
		took = now - self.last
		self.last = now
		self.steps.append((label, took, extra))
		print("  %-26s %7.1fs  %s" % (label, took, extra), flush=True)

	@property
	def total(self):
		return time.time() - self.start


def _commit_every(i, every=200):
	if i and i % every == 0:
		frappe.db.commit()


def ensure_user(shape, persona, roles):
	"""A login with the given roles, and nothing the site's plan would block.

	`module_access` points every new user at the site's plan profile. On a test
	site with no plan that profile blocks every Alvoraa module, so a measurement
	of OUR code would be measuring the plan instead.
	"""
	email = login_of(shape, persona)
	if frappe.db.exists("User", email):
		name = email
	else:
		doc = frappe.get_doc({
			"doctype": "User",
			"email": email,
			"first_name": persona.title(),
			"last_name": shape_of(shape)["prefix"],
			"send_welcome_email": 0,
			"enabled": 1,
		})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		name = doc.name
	doc = frappe.get_doc("User", name)
	have = {r.role for r in doc.roles}
	for role in roles:
		if role not in have:
			doc.append("roles", {"role": role})
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	frappe.db.set_value("User", name, "module_profile", None, update_modified=False)
	frappe.db.delete("Block Module", {"parent": name, "parenttype": "User"})
	frappe.clear_cache(user=name)
	return name


def ensure_holiday_list(shape):
	name = "%s Holidays" % shape_of(shape)["prefix"]
	if not frappe.db.exists("Holiday List", name):
		frappe.get_doc({
			"doctype": "Holiday List",
			"holiday_list_name": name,
			"from_date": add_days(nowdate(), -900),
			"to_date": add_days(nowdate(), 900),
		}).insert(ignore_permissions=True)
	return name


def ensure_companies(shape):
	"""One or four companies, each with the holiday list as its default.

	Company default rather than per-employee assignment: that is how a tenant is
	set up, and it is 1,000 fewer submitted documents for the same answer.
	"""
	from alvoraa_goals.tests.utils import _ensure_erpnext_company_prerequisites

	s = shape_of(shape)
	holidays = ensure_holiday_list(shape)
	out = []
	for n in range(1, s["companies"] + 1):
		name = company_of(shape, n)
		if not frappe.db.exists("Company", name):
			_ensure_erpnext_company_prerequisites()
			doc = frappe.get_doc({
				"doctype": "Company",
				"company_name": name,
				"abbr": "%s%d" % (s["prefix"][-3:], n),
				"default_currency": "INR",
				"country": "India",
			})
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
		frappe.db.set_value("Company", name, "default_holiday_list", holidays)
		out.append(name)
	frappe.db.commit()
	return out


def ensure_branches(shape):
	s = shape_of(shape)
	out = []
	for c in range(1, s["companies"] + 1):
		for b in range(1, s["branches_per_company"] + 1):
			name = branch_of(shape, c, b)
			if not frappe.db.exists("Branch", name):
				frappe.get_doc({"doctype": "Branch", "branch": name}).insert(
					ignore_permissions=True)
			out.append(name)
	frappe.db.commit()
	return out


def _designation(name):
	if not frappe.db.exists("Designation", name):
		frappe.get_doc({"doctype": "Designation",
		                "designation_name": name}).insert(ignore_permissions=True)
	return name


def make_employee(shape, first, company, branch=None, reports_to=None,
                  login=None, designation=None, joined="2023-04-01"):
	"""One person, saved through the document so every hook runs."""
	from alvoraa_goals.tests.utils import ensure_gender

	prefix = shape_of(shape)["prefix"]
	existing = frappe.db.get_value(
		"Employee", {"first_name": first, "last_name": prefix}, "name")
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Employee",
		"first_name": first,
		"last_name": prefix,
		"gender": ensure_gender(),
		"date_of_birth": "1992-06-15",
		"date_of_joining": joined,
		"status": "Active",
		"company": company,
		"branch": branch,
		"reports_to": reports_to,
		"user_id": login,
		"designation": _designation(designation) if designation else None,
		# No automatic "Employee = self" User Permission: it narrows every list
		# the user sees, so a measurement of OUR scoping would be measuring
		# Frappe's instead.
		"create_user_permission": 0,
	})
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	if login:
		frappe.db.delete("User Permission", {"user": login})
		frappe.clear_cache(user=login)
	return doc.name


def user_permission(login, allow, value):
	if not frappe.db.exists("User Permission",
	                        {"user": login, "allow": allow, "for_value": value}):
		frappe.get_doc({"doctype": "User Permission", "user": login,
		                "allow": allow, "for_value": value,
		                "apply_to_all_doctypes": 1}).insert(ignore_permissions=True)
	frappe.clear_cache(user=login)


# ── The build ────────────────────────────────────────────────────────────────


def build(shape, verbose=True):
	"""Build the shape. Idempotent, and a rebuild of a built shape is one query."""
	if is_built(shape):
		if verbose:
			print("%s already built: %d people. Nothing to do."
			      % (shape, count_built(shape)), flush=True)
		return {"rebuilt": False, "people": count_built(shape), "seconds": 0.0}

	s = shape_of(shape)
	clock = Clock()
	print("Building %s: expecting %d people" % (shape, headcount(shape)), flush=True)

	companies = ensure_companies(shape)
	branches = ensure_branches(shape)
	clock.step("companies + branches", "%d companies, %d branches"
	           % (len(companies), len(branches)))

	logins = {p: ensure_user(shape, p, roles) for p, roles in PERSONAS}
	clock.step("five persona logins")

	people = _build_tree(shape, companies, logins)
	clock.step("employees", "%d people" % len(people))

	_scope_the_hr_people(shape, logins)
	clock.step("HR scoping")

	leave_type = _leave(shape, people, logins)
	clock.step("leave allocations + open requests")

	_attendance(shape, people)
	clock.step("attendance", "%d days x %d people"
	           % (s["attendance_days"], len(people)))

	_corrections(shape, people)
	clock.step("attendance corrections")

	_goals(shape, people)
	clock.step("goals + pending updates")

	_policies(shape)
	clock.step("policies")

	frappe.db.commit()
	total = clock.total
	print("%s built in %.0f s (%.1f min), %d people"
	      % (shape, total, total / 60.0, len(people)), flush=True)
	return {"rebuilt": True, "people": len(people), "seconds": total,
	        "steps": clock.steps, "leave_type": leave_type}


def _build_tree(shape, companies, logins):
	"""The manager tree: head -> store manager -> lead -> staff.

	Built with the nested set switched off and rebuilt once at the end, which is
	what `rebuild_tree` is for. Every other hook runs normally.
	"""
	from frappe.utils.nestedset import rebuild_tree

	s = shape_of(shape)
	people = []
	frappe.local.flags.ignore_update_nsm = True
	try:
		for ci, company in enumerate(companies, start=1):
			head = make_employee(shape, "Head%d" % ci, company,
			                     designation="%s Company Head" % s["prefix"])
			people.append(head)
			for bi in range(1, s["branches_per_company"] + 1):
				branch = branch_of(shape, ci, bi)
				mgr = make_employee(shape, "Store%d-%d" % (ci, bi), company,
				                    branch=branch, reports_to=head,
				                    designation="%s Store Manager" % s["prefix"])
				people.append(mgr)
				for li in range(1, s["leads_per_branch"] + 1):
					# The five personas take the first slots of company 1,
					# store 1, so they sit in a real team rather than beside it.
					lead_login = (logins["mgr"] if (ci, bi, li) == (1, 1, 1)
					              else None)
					lead = make_employee(
						shape, "Lead%d-%d-%d" % (ci, bi, li), company,
						branch=branch, reports_to=mgr, login=lead_login,
						designation="%s Team Lead" % s["prefix"])
					people.append(lead)
					for si in range(1, s["staff_per_lead"] + 1):
						login = None
						if (ci, bi, li) == (1, 1, 1):
							login = {1: logins["emp"], 2: logins["storehr"],
							         3: logins["companyhr"],
							         4: logins["sysmgr"]}.get(si)
						person = make_employee(
							shape, "Staff%d-%d-%d-%d" % (ci, bi, li, si),
							company, branch=branch, reports_to=lead, login=login,
							designation="%s Associate" % s["prefix"])
						people.append(person)
						_commit_every(len(people))
		frappe.db.commit()
	finally:
		frappe.local.flags.ignore_update_nsm = False
	rebuild_tree("Employee", "reports_to")
	frappe.db.commit()
	return people


def _scope_the_hr_people(shape, logins):
	"""Store HR is a Branch permission; company HR is a Company permission.

	System Manager gets neither, which is the point: `permitted_companies()`
	hands them every company on the site.
	"""
	user_permission(logins["storehr"], "Branch", branch_of(shape, 1, 1))
	user_permission(logins["storehr"], "Company", company_of(shape, 1))
	user_permission(logins["companyhr"], "Company", company_of(shape, 1))
	frappe.db.commit()


def _leave(shape, people, logins):
	"""A real allocation per person, so the balances on Home are real ledger
	rows, plus a realistic scatter of open requests pointed at real approvers."""
	from alvoraa_portal.tests.leave_fixtures import ensure_leave_type

	s = shape_of(shape)
	leave_type = ensure_leave_type("%s Casual" % s["prefix"])
	start = add_days(nowdate(), -120)
	end = add_days(nowdate(), 240)
	for i, emp in enumerate(people):
		doc = frappe.get_doc({
			"doctype": "Leave Allocation",
			"employee": emp,
			"leave_type": leave_type,
			"from_date": start,
			"to_date": end,
			"new_leaves_allocated": 12,
			"carry_forward": 0,
		})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		doc.submit()
		_commit_every(i)
	frappe.db.commit()

	# Open requests. Every one goes to the person's real approver, because who
	# the approver is decides which caller sees it.
	approvers = {}
	day = add_days(nowdate(), 30)
	n = 0
	for i, emp in enumerate(people):
		if i % s["leave_every"]:
			continue
		reports_to = frappe.db.get_value("Employee", emp, "reports_to")
		if not reports_to:
			continue
		if reports_to not in approvers:
			approvers[reports_to] = frappe.db.get_value(
				"Employee", reports_to, "user_id")
		approver = approvers[reports_to]
		if not approver:
			continue
		doc = frappe.get_doc({
			"doctype": "Leave Application",
			"employee": emp,
			"leave_type": leave_type,
			"from_date": add_days(day, n % 20),
			"to_date": add_days(day, n % 20),
			"leave_approver": approver,
			"status": "Open",
		})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		n += 1
		_commit_every(n)
	frappe.db.commit()
	return leave_type


def _attendance(shape, people):
	"""Today marked for everyone, plus history, so the presence card and the
	attendance-gap rule both have something real to read.

	One day in the window is left unmarked for a slice of people, so the gap
	rule has gaps to find rather than a clean sheet that would make it free.
	"""
	s = shape_of(shape)
	days = [add_days(nowdate(), -d) for d in range(s["attendance_days"])]
	n = 0
	for pi, emp in enumerate(people):
		company = frappe.db.get_value("Employee", emp, "company")
		for di, day in enumerate(days):
			# One in seven has no row for the day three back: that is the gap.
			if di == 3 and pi % 7 == 0:
				continue
			status = "Present"
			if di and (pi + di) % 11 == 0:
				status = "Absent"
			elif di and (pi + di) % 13 == 0:
				status = "On Leave"
			doc = frappe.get_doc({
				"doctype": "Attendance",
				"employee": emp,
				"attendance_date": day,
				"status": status,
				"company": company,
			})
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
			doc.submit()
			n += 1
			_commit_every(n, 300)
	frappe.db.commit()
	return n


def _corrections(shape, people):
	"""Pending attendance corrections, spread over stores so a store's HR person
	sees their own and a company's HR person sees more."""
	from alvoraa_portal import attendance_correction

	s = shape_of(shape)
	attendance_correction.after_migrate()
	frappe.clear_cache(doctype=attendance_correction.REQUEST)
	day = add_days(nowdate(), -20)
	made = 0
	for emp in people:
		if made >= s["corrections"]:
			break
		doc = frappe.get_doc({
			"doctype": attendance_correction.REQUEST,
			"employee": emp,
			"from_date": add_days(day, made % 9),
			"to_date": add_days(day, made % 9),
			"reason": "On Duty",
			"explanation": "%s fixture" % s["prefix"],
		})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		made += 1
		_commit_every(made, 50)
	frappe.db.commit()
	return made


def _goals(shape, people):
	"""Individual Goals with pending progress updates: the part that reads
	`goals_api._pending_approvals_scope`, the helper behind the 16.4-second bell."""
	if not frappe.db.exists("DocType", "Individual Goal"):
		return 0
	s = shape_of(shape)
	start = add_days(nowdate(), -120)
	end = add_days(nowdate(), 240)
	goals = []
	for i, emp in enumerate(people[:s["goals_for"]]):
		doc = frappe.get_doc({
			"doctype": "Individual Goal",
			"employee": emp,
			"goal_name": "%s Goal %d" % (s["prefix"], i),
			"target_value": 100,
			"start_date": start,
			"end_date": end,
			"status": "Active",
		})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		goals.append(doc.name)
		_commit_every(i, 100)
	frappe.db.commit()

	for i, goal in enumerate(goals[:s["goal_updates"]]):
		doc = frappe.get_doc("Individual Goal", goal)
		doc.append("progress_updates", {
			"log_date": add_days(nowdate(), -3),
			"value": 10 + i,
			"approval_status": "Pending",
			"note": "%s update" % s["prefix"],
		})
		doc.flags.ignore_permissions = True
		doc.save(ignore_permissions=True)
		_commit_every(i, 50)
	frappe.db.commit()
	return len(goals)


def _policies(shape):
	"""One policy everybody still has to acknowledge, so the policies part is
	not silently zero for every persona."""
	if not frappe.db.exists("DocType", "Policy Document"):
		return None
	s = shape_of(shape)
	name = "%s Code of Conduct" % s["prefix"]
	if frappe.db.exists("Policy Document", {"title": name}):
		return name
	meta = frappe.get_meta("Policy Document")
	doc = frappe.get_doc({"doctype": "Policy Document", "title": name})
	for field, value in (("status", "Published"), ("published", 1),
	                     ("effective_from", add_days(nowdate(), -30)),
	                     ("requires_acknowledgement", 1), ("version", "1.0"),
	                     ("body", "%s fixture policy" % s["prefix"]),
	                     ("content", "%s fixture policy" % s["prefix"])):
		if meta.has_field(field):
			doc.set(field, value)
	doc.flags.ignore_permissions = True
	try:
		doc.insert(ignore_permissions=True)
	except Exception as exc:          # the doctype's own rules win, not ours
		print("  policy not created: %s" % exc, flush=True)
		return None
	frappe.db.commit()
	return doc.name
