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
