"""Who sees which policy, and what publishing does.

Four people: a plain employee in Sales, a manager (someone reports to them),
an HR Manager, and the head of the Purchase department. Five policies with
different read rules.
"""

import frappe
from frappe.tests import IntegrationTestCase

from hrms.alvoraa_policy_library.access import can_read, can_write, profile
from hrms.alvoraa_policy_library.doctype.policy_document.policy_document import acknowledgement_status
from hrms.alvoraa_policy_library.setup import make_custom_fields

PREFIX = "PolTest"


def _company():
	return frappe.get_all("Company", pluck="name", limit=1)[0]


def _user(email, roles):
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0],
		                "send_welcome_email": 0, "roles": [{"role": r} for r in roles]}).insert(ignore_permissions=True)
	else:
		u = frappe.get_doc("User", email)
		for r in roles:
			if r not in {x.role for x in u.roles}:
				u.append("roles", {"role": r})
		u.save(ignore_permissions=True)
	return email


def _department(name, company):
	full = frappe.db.get_value("Department", {"department_name": name, "company": company}, "name")
	if full:
		return full
	d = frappe.get_doc({"doctype": "Department", "department_name": name, "company": company})
	d.insert(ignore_permissions=True)
	return d.name


def _employee(first, last, company, department, user, reports_to=None):
	name = frappe.db.get_value("Employee", {"first_name": first, "last_name": last}, "name")
	if name:
		frappe.db.set_value("Employee", name, {"user_id": user, "department": department, "reports_to": reports_to, "status": "Active"})
		return name
	e = frappe.get_doc({"doctype": "Employee", "first_name": first, "last_name": last, "gender": "Female",
	                    "date_of_birth": "1990-01-01", "date_of_joining": "2026-01-01", "company": company,
	                    "status": "Active", "department": department, "user_id": user, "reports_to": reports_to})
	e.flags.ignore_permissions = True
	e.insert(ignore_mandatory=True)
	return e.name


class TestPolicyLibrary(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_custom_fields()
		frappe.clear_cache()
		frappe.conf.features = list(frappe.conf.get("features") or []) + ["policy_library"]
		cls.company = _company()
		cls.sales = _department(f"{PREFIX} Sales", cls.company)
		cls.purchase = _department(f"{PREFIX} Purchase", cls.company)
		cls.staff_user = _user("poltest.staff@example.com", ["Employee"])
		cls.manager_user = _user("poltest.manager@example.com", ["Employee"])
		cls.hr_user = _user("poltest.hr@example.com", ["Employee", "HR Manager"])
		cls.head_user = _user("poltest.head@example.com", ["Employee"])
		cls.manager = _employee(PREFIX, "Manager", cls.company, cls.sales, cls.manager_user)
		cls.staff = _employee(PREFIX, "Staff", cls.company, cls.sales, cls.staff_user, reports_to=cls.manager)
		cls.hr = _employee(PREFIX, "HR", cls.company, cls.sales, cls.hr_user)
		cls.head = _employee(PREFIX, "Head", cls.company, cls.purchase, cls.head_user)
		frappe.db.set_value("Department", cls.purchase, "department_head", cls.head)
		frappe.db.set_value("Department", cls.sales, "department_head", None)
		cls.policies = {}
		for key, rules, extra in (
			("everyone", [{"access_type": "All Employees"}], {"acknowledge_on_joining": 1}),
			("managers", [{"access_type": "Reporting Managers"}], {}),
			("hr", [{"access_type": "HR Only"}], {}),
			("purchase", [{"access_type": "Department Only"}], {}),
			("leaders", [{"access_type": "Top Leadership"}], {}),
		):
			cls.policies[key] = cls._policy(f"{PREFIX} {key}", cls.purchase if key == "purchase" else cls.sales, rules, **extra)
		cls.draft = cls._policy(f"{PREFIX} draft", cls.sales, [{"access_type": "All Employees"}], status="Draft")

	@classmethod
	def _policy(cls, title, department, rules, status="Published", **extra):
		name = frappe.db.get_value("Policy Document", {"title": title}, "name")
		if name:
			frappe.delete_doc("Policy Document", name, ignore_permissions=True, force=True)
		doc = frappe.get_doc({"doctype": "Policy Document", "title": title, "owner_department": department,
		                      "category": "HR", "status": status, "content": "<p>Rules.</p>", "summary": "s",
		                      "read_access": rules, **extra})
		doc.insert(ignore_permissions=True)
		return doc

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		frappe.local.policy_profiles = {}

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def _visible(self, user):
		frappe.local.policy_profiles = {}
		names = set(frappe.get_list("Policy Document", filters={"title": ["like", f"{PREFIX}%"]}, pluck="name",
		                            user=user, limit=0))
		return {k for k, v in self.policies.items() if v.name in names} | ({"draft"} if self.draft.name in names else set())

	def test_profiles(self):
		self.assertTrue(profile(self.manager_user).is_manager)
		self.assertFalse(profile(self.staff_user).is_manager)
		self.assertTrue(profile(self.head_user).is_leader)
		self.assertTrue(profile(self.hr_user).sees_all)

	def test_who_sees_what_in_the_list(self):
		self.assertEqual(self._visible(self.staff_user), {"everyone"})
		self.assertEqual(self._visible(self.manager_user), {"everyone", "managers"})
		self.assertEqual(self._visible(self.hr_user), {"everyone", "managers", "hr", "purchase", "leaders", "draft"})
		self.assertEqual(self._visible(self.head_user), {"everyone", "managers", "hr", "purchase", "leaders", "draft"})

	def test_department_only_follows_the_owner_department(self):
		purchase_staff_user = _user("poltest.purchase@example.com", ["Employee"])
		_employee(PREFIX, "Buyer", self.company, self.purchase, purchase_staff_user)
		self.assertEqual(self._visible(purchase_staff_user), {"everyone", "purchase"})

	def test_form_agrees_with_the_list(self):
		self.assertTrue(can_read(self.policies["everyone"], self.staff_user))
		self.assertFalse(can_read(self.policies["managers"], self.staff_user))
		self.assertTrue(can_read(self.policies["managers"], self.manager_user))
		self.assertFalse(can_read(self.draft, self.staff_user))
		self.assertTrue(frappe.has_permission("Policy Document", "read", self.policies["everyone"], user=self.staff_user))
		self.assertFalse(frappe.has_permission("Policy Document", "read", self.policies["hr"], user=self.staff_user))

	def test_who_may_write(self):
		self.assertFalse(can_write(self.policies["everyone"], self.staff_user))
		self.assertFalse(can_write(self.policies["everyone"], self.manager_user))
		self.assertTrue(can_write(self.policies["everyone"], self.hr_user))
		self.assertTrue(can_write(self.policies["purchase"], self.head_user))      # head of the owning department
		self.assertFalse(can_write(self.policies["everyone"], self.head_user))     # not of this one
		self.assertFalse(frappe.has_permission("Policy Document", "write", self.policies["everyone"], user=self.staff_user))

	def test_publish_snapshots_and_readers_keep_the_old_text(self):
		doc = self.policies["everyone"]
		self.assertEqual(doc.current_version, 1)
		self.assertEqual(len(doc.versions), 1)
		doc.content = "<p>New rules.</p>"
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.has_unpublished_changes, 1)
		self.assertEqual(doc.published_view().content, "<p>Rules.</p>")
		frappe.set_user(self.hr_user)
		doc = frappe.get_doc("Policy Document", doc.name)
		doc.publish("Tightened the rules.")
		self.assertEqual(doc.current_version, 2)
		self.assertEqual(doc.published_view().content, "<p>New rules.</p>")
		self.assertEqual(doc.versions[-1].change_note, "Tightened the rules.")
		self.assertEqual(doc.has_unpublished_changes, 0)
		with self.assertRaises(frappe.ValidationError):
			doc.publish("Nothing changed")

	def test_acknowledgement(self):
		doc = self.policies["everyone"]
		needed, done = acknowledgement_status(doc, self.staff)
		self.assertTrue(needed)
		self.assertFalse(done)
		ack = frappe.get_doc({"doctype": "Policy Acknowledgement", "policy_document": doc.name,
		                      "version": doc.current_version, "employee": self.staff, "source": "Manual"})
		ack.insert(ignore_permissions=True)
		self.assertTrue(acknowledgement_status(doc, self.staff)[1])
		dup = frappe.get_doc({"doctype": "Policy Acknowledgement", "policy_document": doc.name,
		                      "version": doc.current_version, "employee": self.staff})
		self.assertRaises(frappe.ValidationError, dup.insert)
		self.assertFalse(acknowledgement_status(self.policies["managers"], self.staff)[0])   # no flag, nothing to do
