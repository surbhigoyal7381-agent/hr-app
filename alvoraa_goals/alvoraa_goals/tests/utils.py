import frappe
from frappe.utils import today

TEST_COMPANY = "Alvoraa Test Company"
TEST_GENDER = "Male"


def ensure_company():
	"""Return a usable Company name, creating one if the site has none.

	The tests used to do:

	    frappe.get_value("Company", {}, "name") or "Grace Drinks"

	which reads as a safe fallback but is not one: on a site with no companies it
	hands back the name of a company that does not exist, and every insert that
	links to it fails with LinkValidationError. It passed on developer machines
	only because a "Grace Drinks" company happened to be seeded there, and failed
	on every fresh CI site.

	A test should build the world it needs rather than assume someone else did.
	"""
	existing = frappe.get_value("Company", {}, "name")
	if existing:
		return existing

	company = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": TEST_COMPANY,
			"abbr": "ATC",
			"default_currency": "INR",
			"country": "India",
		}
	)
	company.flags.ignore_permissions = True
	company.insert(ignore_permissions=True)
	frappe.db.commit()
	return company.name


def ensure_gender(gender=TEST_GENDER):
	"""Return a Gender that exists, creating it if the site has none.

	Employee requires `gender` as a Link, and a bare frappe + erpnext + hrms site has
	no Gender records at all. Only `company` and `gender` are required Links on
	Employee - department, designation, employment_type and holiday_list are optional
	and the tests do not set them - so between this and ensure_company() an Employee
	insert has everything it needs.
	"""
	if frappe.db.exists("Gender", gender):
		return gender

	doc = frappe.get_doc({"doctype": "Gender", "gender": gender})
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return doc.name


def ensure_employee_prerequisites():
	"""Everything an Employee insert needs. Returns the company name."""
	company = ensure_company()
	ensure_gender()
	return company


def ensure_employee(first_name, last_name="Employee"):
	"""Create (or reuse) a test Employee with a complete, realistic field set.

	Employee creation kept failing one field at a time - gender, then date_of_birth -
	because the tests supplied only the fields that happened to be mandatory on a
	developer machine. The doctype JSON in this repo marks neither as required, yet a
	freshly installed site rejects both: hrms sets extra requirements during install,
	so a stale local bench and a fresh CI site do not agree on what is mandatory.

	The durable answer is not to chase each field but to populate a full, plausible
	Employee once, in one place. Callers no longer build the dict themselves.
	"""
	employee_name = f"{first_name} {last_name}"
	existing = frappe.get_value("Employee", {"employee_name": employee_name}, "name")
	if existing:
		return existing

	company = ensure_company()
	ensure_gender()

	emp = frappe.get_doc(
		{
			"doctype": "Employee",
			"first_name": first_name,
			"last_name": last_name,
			"company": company,
			"gender": TEST_GENDER,
			"date_of_birth": "1990-01-01",
			"date_of_joining": today(),
			"status": "Active",
		}
	)
	emp.flags.ignore_permissions = True
	emp.insert(ignore_permissions=True)
	return emp.name
