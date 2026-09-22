"""
Sargam Metals demo - Block 1: companies, warehouses, items, suppliers, customers.

Written against standard ERPNext doctypes (Company, Warehouse, Item, Item
Group, Supplier, Customer) using their well-documented core field names.
UNVERIFIED against a live site - this session has no bench/docker access
(see docs/sargam_metals/00-demo-instance-and-plan.md). Run the verification
pass in that file's §4 before this is shown to anyone.

Supplier and customer names below are fictional demo placeholders, not real
companies - the same convention demo/pp_jewellers uses for its store list.

Idempotent: safe to re-run.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SARGAM_SCRIPT_DIR", "/tmp/sargam"))
from sargam_common import *  # noqa: F401,F403

connect()

# ── Companies and fiscal years ──────────────────────────────────────────────
log("Companies")
ensure("Company", COMPANY_IN, {
    "company_name": COMPANY_IN, "abbr": ABBR_IN, "default_currency": "INR",
    "country": "India", "domain": "Manufacturing", "chart_of_accounts": "Standard",
})
ensure("Company", COMPANY_SG, {
    "company_name": COMPANY_SG, "abbr": ABBR_SG, "default_currency": "USD",
    "country": "Singapore", "domain": "Distribution", "chart_of_accounts": "Standard",
})
commit()

log("Fiscal Year")
if not frappe.db.exists("Fiscal Year", "2026-2027"):
    fy = frappe.get_doc({"doctype": "Fiscal Year", "year": "2026-2027",
                         "year_start_date": FY_START, "year_end_date": FY_END})
    fy.append("companies", {"company": COMPANY_IN})
    fy.append("companies", {"company": COMPANY_SG})
    fy.insert(ignore_permissions=True)
    log("  [created] Fiscal Year: 2026-2027")
else:
    fy = frappe.get_doc("Fiscal Year", "2026-2027")
    have = {c.company for c in fy.companies}
    for c in (COMPANY_IN, COMPANY_SG):
        if c not in have:
            fy.append("companies", {"company": c})
    fy.save(ignore_permissions=True)
commit()

# ── Warehouses ───────────────────────────────────────────────────────────────
log("Warehouses")
for wh in ["Raw Materials", "Work In Progress", "Finished Goods"]:
    ensure("Warehouse", f"{wh} - {ABBR_IN}", {"warehouse_name": wh, "company": COMPANY_IN})
commit()

# ── Item Groups ──────────────────────────────────────────────────────────────
log("Item Groups")
ensure("Item Group", "Raw Materials", {"item_group_name": "Raw Materials",
       "parent_item_group": "All Item Groups", "is_group": 0})
ensure("Item Group", "Cathodic Protection Products", {"item_group_name": "Cathodic Protection Products",
       "parent_item_group": "All Item Groups", "is_group": 1})
ensure("Item Group", "Standard Catalog", {"item_group_name": "Standard Catalog",
       "parent_item_group": "Cathodic Protection Products", "is_group": 0})
ensure("Item Group", "Custom Engineered-to-Order", {"item_group_name": "Custom Engineered-to-Order",
       "parent_item_group": "Cathodic Protection Products", "is_group": 0})
commit()

# ── Items ────────────────────────────────────────────────────────────────────
log("Items - raw materials, with reorder levels")
RAW_MATERIALS = [
    # item_code, item_name, uom, reorder_level_kg, reorder_qty_kg
    ("RM-AL-INGOT", "Aluminium Ingot (99.7% purity)", "Kg", 2000, 5000),
    ("RM-ZN-INGOT", "Zinc Ingot (Special High Grade)", "Kg", 1500, 4000),
    ("RM-MG-INGOT", "Magnesium Ingot", "Kg", 500, 1500),
]
for code, name, uom, reorder_level, reorder_qty in RAW_MATERIALS:
    ensure("Item", code, {
        "item_code": code, "item_name": name, "item_group": "Raw Materials",
        "stock_uom": uom, "is_stock_item": 1, "include_item_in_manufacturing": 1,
        "reorder_levels": [{
            "warehouse": f"Raw Materials - {ABBR_IN}",
            "warehouse_reorder_level": reorder_level,
            "warehouse_reorder_qty": reorder_qty,
            "material_request_type": "Purchase",
        }],
    })
commit()

log("Items - finished goods, standard vs. custom")
ensure("Item", "FG-AL-ANODE-25KG", {
    "item_code": "FG-AL-ANODE-25KG", "item_name": "Aluminium Jacket Anode, 25kg (offshore platform grade)",
    "item_group": "Standard Catalog", "stock_uom": "Nos", "is_stock_item": 1,
})
ensure("Item", "FG-ICCP-NAVAL-LS", {
    "item_code": "FG-ICCP-NAVAL-LS", "item_name": "ICCP System, low-signature (naval vessel, engineered-to-order)",
    "item_group": "Custom Engineered-to-Order", "stock_uom": "Nos", "is_stock_item": 1,
})
commit()

# ── Suppliers ────────────────────────────────────────────────────────────────
log("Suppliers (fictional demo placeholders)")
for name, group in [
    ("Coastal Ingot Suppliers Pvt Ltd", "Raw Material"),
    ("Southern Alloys Trading Co", "Raw Material"),
]:
    ensure("Supplier", name, {"supplier_name": name, "supplier_group": "All Supplier Groups",
           "country": "India"})
commit()

# ── Customers ────────────────────────────────────────────────────────────────
log("Customers (fictional demo placeholders)")
ensure("Customer", "Coastal Shipyard Ltd", {"customer_name": "Coastal Shipyard Ltd",
       "customer_group": "All Customer Groups", "territory": "India", "default_currency": "INR"})
ensure("Customer", "Straits Marine Offshore Pte Ltd", {"customer_name": "Straits Marine Offshore Pte Ltd",
       "customer_group": "All Customer Groups", "territory": "Rest Of The World", "default_currency": "USD"})
commit()

counts("Company", "Warehouse", "Item Group", "Item", "Supplier", "Customer")
log("seed_masters.py done")
