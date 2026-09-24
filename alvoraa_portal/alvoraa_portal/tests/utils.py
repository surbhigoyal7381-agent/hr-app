import frappe


def ensure_item_group():
	"""Return an Item Group, creating one only if the site has none."""
	existing = frappe.get_value("Item Group", {"is_group": 0}, "name") or frappe.get_value(
		"Item Group", {}, "name"
	)
	if existing:
		return existing
	doc = frappe.get_doc({"doctype": "Item Group", "item_group_name": "Alvoraa Test Group"})
	doc.insert(ignore_permissions=True)
	return doc.name


def ensure_uom():
	"""Return a UOM, creating one only if the site has none."""
	for candidate in ("Nos", "Unit"):
		if frappe.db.exists("UOM", candidate):
			return candidate
	existing = frappe.get_value("UOM", {}, "name")
	if existing:
		return existing
	doc = frappe.get_doc({"doctype": "UOM", "uom_name": "Nos"})
	doc.insert(ignore_permissions=True)
	return doc.name


def ensure_item(item_code):
	"""Create (or reuse) an Item so a Vendor Order Item can link to it.

	`Vendor Order Item.sku` is a required Link to Item. The tests use literal SKU codes
	- SKU-A, TEST-SKU-001 and so on - which exist on a developer machine that has been
	seeded but on no fresh site, so every order insert failed with LinkValidationError.

	Same lesson as the goals suite: a test should create what it links to.
	"""
	if frappe.db.exists("Item", item_code):
		return item_code

	doc = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": item_code,
			"item_group": ensure_item_group(),
			"stock_uom": ensure_uom(),
			"is_stock_item": 0,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return doc.name


def ensure_items(*item_codes):
	"""Convenience wrapper for the several SKUs a test module uses."""
	return [ensure_item(code) for code in item_codes]


def ensure_fiscal_years(*dates):
	"""Active April-March fiscal years covering `dates` (default: today and a year ago).

	A brand-new test site has no Fiscal Year at all. Tests that post a Sales Invoice
	or a Salary Structure Assignment used to get one only because another module
	(test_leave_year) happened to run earlier and commit it. Frappe discovers test
	files in directory order, and adding a file changes that order: on 24 Sep 2026
	CI started failing 15 tests with "Date 2026-09-24 is not in any active Fiscal
	Year" after a new test file was added. So a test that needs a year makes it.

	Reuses the names test_leave_year uses, never creates an overlapping year, and
	commits: get_fiscal_year runs its own cached query.
	"""
	from erpnext.accounts.utils import FiscalYearError, get_fiscal_year
	from frappe.utils import add_days, getdate, nowdate

	for d in (dates or (nowdate(), add_days(nowdate(), -365))):
		d = getdate(d)
		try:
			get_fiscal_year(d)
			continue
		except FiscalYearError:
			pass
		start = d.year if d.month >= 4 else d.year - 1
		name = f"TEST-{start}-{start + 1}"
		if frappe.db.exists("Fiscal Year", name):
			frappe.db.set_value("Fiscal Year", name, "disabled", 0)
		else:
			doc = frappe.get_doc({
				"doctype": "Fiscal Year",
				"year": name,
				"year_start_date": f"{start}-04-01",
				"year_end_date": f"{start + 1}-03-31",
				"auto_created": 0,
				"disabled": 0,
			})
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
		frappe.db.commit()
		frappe.cache.delete_value("fiscal_years")
