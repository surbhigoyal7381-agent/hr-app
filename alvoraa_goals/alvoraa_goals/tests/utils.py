import frappe

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
