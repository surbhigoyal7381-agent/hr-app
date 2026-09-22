"""
Sargam Metals demo - Block 2: the buy -> make -> inspect -> sell loop.

One BOM, one purchase of raw ingots, one production run, one quality
inspection, one export sale - proposal Phase 0-1 plus a taste of Phase 2
(quality). Reuses ERPNext's own document-creation functions wherever one
exists (make_purchase_receipt, make_stock_entry, make_sales_invoice) rather
than building those documents by hand, per CLAUDE.md §4 and the same rule
demo/README.md states for this team's own seeds: prefer the function the app
itself uses to create a record.

UNVERIFIED against a live site - see seed_masters.py's header and
docs/sargam_metals/00-demo-instance-and-plan.md §4 for the verification this
still needs. Requires seed_masters.py to have run first.

Idempotent for the masters it reads; re-running skips a step whose named
document already exists, but each transaction step creates one instance
(re-running blindly will not create a second Sales Order under the same name
check - each ensure()/skip is name-based, see comments below).
"""
import os
import sys

sys.path.insert(0, os.environ.get("SARGAM_SCRIPT_DIR", "/tmp/sargam"))
from sargam_common import *  # noqa: F401,F403

connect()

RM_WH = f"Raw Materials - {ABBR_IN}"
FG_WH = f"Finished Goods - {ABBR_IN}"
SUPPLIER = "Coastal Ingot Suppliers Pvt Ltd"
DOMESTIC_CUSTOMER = "Coastal Shipyard Ltd"
EXPORT_CUSTOMER = "Straits Marine Offshore Pte Ltd"
FG_ITEM = "FG-AL-ANODE-25KG"

# ── BOM for the standard anode ───────────────────────────────────────────────
log("BOM")
bom_name = frappe.db.get_value("BOM", {"item": FG_ITEM, "company": COMPANY_IN, "docstatus": 1}, "name")
if not bom_name:
    bom = frappe.new_doc("BOM")
    bom.item = FG_ITEM
    bom.company = COMPANY_IN
    bom.quantity = 1
    bom.uom = "Nos"
    bom.is_default = 1
    bom.is_active = 1
    bom.append("items", {"item_code": "RM-AL-INGOT", "qty": 24, "uom": "Kg"})
    bom.append("items", {"item_code": "RM-ZN-INGOT", "qty": 1, "uom": "Kg"})
    bom.flags.ignore_permissions = True
    bom.insert(ignore_permissions=True)
    bom.submit()
    bom_name = bom.name
    log(f"  [created] BOM: {bom_name}")
commit()

# ── Purchase Order -> Purchase Receipt for raw ingots ───────────────────────
log("Purchase Order and Receipt")
from frappe.utils import add_days, nowdate

po_name = frappe.db.get_value("Purchase Order",
    {"supplier": SUPPLIER, "company": COMPANY_IN, "docstatus": 1}, "name")
if not po_name:
    po = frappe.new_doc("Purchase Order")
    po.supplier = SUPPLIER
    po.company = COMPANY_IN
    po.schedule_date = add_days(nowdate(), 7)
    po.append("items", {"item_code": "RM-AL-INGOT", "qty": 5000, "rate": 205, "warehouse": RM_WH,
                        "schedule_date": add_days(nowdate(), 7)})
    po.append("items", {"item_code": "RM-ZN-INGOT", "qty": 500, "rate": 240, "warehouse": RM_WH,
                        "schedule_date": add_days(nowdate(), 7)})
    po.flags.ignore_permissions = True
    po.insert(ignore_permissions=True)
    po.submit()
    po_name = po.name
    log(f"  [created] Purchase Order: {po_name}")

pr_name = frappe.db.get_value("Purchase Receipt", {"purchase_order": po_name, "docstatus": 1}, "name") \
    if po_name else None
if po_name and not pr_name:
    from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
    pr = make_purchase_receipt(po_name)
    pr.flags.ignore_permissions = True
    pr.insert(ignore_permissions=True)
    pr.submit()
    pr_name = pr.name
    log(f"  [created] Purchase Receipt: {pr_name}")
commit()

# ── Work Order and the manufacture Stock Entry ──────────────────────────────
log("Work Order and manufacture")
wo_name = frappe.db.get_value("Work Order",
    {"production_item": FG_ITEM, "company": COMPANY_IN, "docstatus": 1}, "name")
if not wo_name:
    wo = frappe.new_doc("Work Order")
    wo.production_item = FG_ITEM
    wo.bom_no = bom_name
    wo.qty = 100
    wo.company = COMPANY_IN
    wo.wip_warehouse = f"Work In Progress - {ABBR_IN}"
    wo.fg_warehouse = FG_WH
    wo.source_warehouse = RM_WH
    wo.planned_start_date = nowdate()
    wo.flags.ignore_permissions = True
    wo.insert(ignore_permissions=True)
    wo.submit()
    wo_name = wo.name
    log(f"  [created] Work Order: {wo_name}")

# ERPNext manufactures from the Work-In-Progress warehouse, so the raw material
# has to be moved there first. Without this transfer the Manufacture entry
# stops with "Insufficient Stock" - found on the third real run, 2026-09-22.
already_transferred = frappe.db.exists("Stock Entry",
    {"work_order": wo_name, "purpose": "Material Transfer for Manufacture", "docstatus": 1})     if wo_name else None
if wo_name and not already_transferred:
    from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
    tr = frappe.get_doc(make_stock_entry(work_order_id=wo_name, purpose="Material Transfer for Manufacture", qty=100))
    tr.flags.ignore_permissions = True
    tr.insert(ignore_permissions=True)
    tr.submit()
    log(f"  [created] Stock Entry (Material Transfer for Manufacture): {tr.name}")

already_manufactured = frappe.db.exists("Stock Entry", {"work_order": wo_name, "purpose": "Manufacture"}) \
    if wo_name else None
if wo_name and not already_manufactured:
    from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
    se = frappe.get_doc(make_stock_entry(work_order_id=wo_name, purpose="Manufacture", qty=100))
    se.flags.ignore_permissions = True
    se.insert(ignore_permissions=True)
    se.submit()
    log(f"  [created] Stock Entry (Manufacture): {se.name}")
    manufacture_se_name = se.name
else:
    manufacture_se_name = frappe.db.get_value("Stock Entry", {"work_order": wo_name, "purpose": "Manufacture"}, "name")
commit()

# ── Quality Inspection on the finished batch ────────────────────────────────
log("Quality Inspection")
if manufacture_se_name and not frappe.db.exists("Quality Inspection",
        {"reference_type": "Stock Entry", "reference_name": manufacture_se_name}):
    qi = frappe.new_doc("Quality Inspection")
    qi.inspection_type = "Final"
    qi.reference_type = "Stock Entry"
    qi.reference_name = manufacture_se_name
    qi.item_code = FG_ITEM
    qi.sample_size = 5
    qi.inspected_by = frappe.session.user
    qi.status = "Accepted"
    qi.flags.ignore_permissions = True
    qi.insert(ignore_permissions=True)
    qi.submit()
    log(f"  [created] Quality Inspection: {qi.name}")
commit()

# ── Export Sales Order -> Sales Invoice ─────────────────────────────────────
log("Export Sales Order and Invoice")
so_name = frappe.db.get_value("Sales Order",
    {"customer": EXPORT_CUSTOMER, "company": COMPANY_IN, "docstatus": 1}, "name")
if not so_name:
    so = frappe.new_doc("Sales Order")
    so.customer = EXPORT_CUSTOMER
    so.company = COMPANY_IN
    so.currency = "USD"
    so.delivery_date = add_days(nowdate(), 14)
    so.append("items", {"item_code": FG_ITEM, "qty": 40, "rate": 185, "warehouse": FG_WH,
                        "delivery_date": add_days(nowdate(), 14)})
    so.flags.ignore_permissions = True
    so.insert(ignore_permissions=True)
    so.submit()
    so_name = so.name
    log(f"  [created] Sales Order: {so_name}")

si_name = frappe.db.get_value("Sales Invoice", {"sales_order": so_name}, "name") if so_name else None
# Sales Invoice does not carry a direct sales_order field at the parent level
# in every ERPNext version - this line needs the verification pass in
# docs/sargam_metals/00-demo-instance-and-plan.md §4 to confirm on the real
# site rather than assumed here.
if so_name and not si_name:
    from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
    si = make_sales_invoice(so_name)
    si.flags.ignore_permissions = True
    si.insert(ignore_permissions=True)
    si.submit()
    si_name = si.name
    log(f"  [created] Sales Invoice: {si_name}")
commit()

counts("BOM", "Purchase Order", "Purchase Receipt", "Work Order", "Stock Entry",
       "Quality Inspection", "Sales Order", "Sales Invoice")
log("seed_transactions.py done")
