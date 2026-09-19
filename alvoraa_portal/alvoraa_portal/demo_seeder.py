"""
Demo data only, and the vendor names and addresses below are invented.

Slice 016: this file used to carry five real businesses with their street
addresses, in a public repository, for a demo nobody calls - nothing in the app
imports it.

demo_seeder.py — creates realistic Vendor Orders at every pipeline stage.
Run via:  bench --site hrms.localhost execute alvoraa_portal.demo_seeder.run
"""
import frappe
from frappe.utils import today, add_days, now_datetime


# ── Vendor IDs (the ones with portal logins) ─────────────────────────────────
VENDORS = {
    "Northside Store":     "1remqvgub0",
    "Metro Outlet":        "1rehkmb8k3",
    "City Hotel":          "248lq6ac5b",
    "QuickStop Kiosk":     "248q68666h",
    "Riverside Banquets":  "248didtq4e",
}

ADDRESSES = {
    "Northside Store":     "Unit 4, Demo Market, Demo City - 100001",
    "Metro Outlet":        "Plot 12, Demo Industrial Area, Demo City - 100002",
    "City Hotel":          "Demo Club Road, Demo City - 100003",
    "QuickStop Kiosk":     "Booth 7, Demo Market, Demo City - 100004",
    "Riverside Banquets":  "Demo Complex, Demo Highway, Demo Town - 100005",
}

# Each order: (vendor_key, slot, items, target_status, special_instructions)
ORDERS = [
    # Draft — freshly placed, not yet reviewed
    (
        "Northside Store", "Tomorrow",
        [
            ("GD-WHI-750",  6, 1200),
            ("GD-BEE-650", 12,  180),
            ("GD-SDR-300", 24,   45),
        ],
        "Draft",
        "Please ensure bottles are packed upright.",
    ),
    # Under Review — submitted, pending admin approval
    (
        "Metro Outlet", "Next 2 Days",
        [
            ("GD-WHI-CS12",  1, 13500),
            ("GD-VOD-750",   4,   900),
        ],
        "Under Review",
        "",
    ),
    # Approved
    (
        "City Hotel", "Next 2 Days",
        [
            ("GD-GIN-750",   3, 1100),
            ("GD-RUM-750",   3,  850),
            ("GD-SDR-300",  48,   45),
        ],
        "Approved",
        "Deliver to bar entrance on lower ground floor.",
    ),
    # Packing
    (
        "QuickStop Kiosk", "Tomorrow",
        [
            ("GD-BEE-CS24",  2, 3500),
            ("GD-WAT-CS24",  3,  350),
            ("GD-JUI-MNG-1L", 12, 120),
        ],
        "Packing",
        "",
    ),
    # Ready for Dispatch — triggers auto DO creation + manager email
    (
        "Riverside Banquets", "Today",
        [
            ("GD-WHI-750",   10, 1200),
            ("GD-RUM-750",    5,  850),
            ("GD-BEE-CS24",   3, 3500),
            ("GD-WAT-CS24",   5,  350),
        ],
        "Ready for Dispatch",
        "Event on same day — on-time delivery critical.",
    ),
    # Second Ready for Dispatch (different vendor)
    (
        "Northside Store", "Today",
        [
            ("GD-WHI-CS12",  2, 13500),
            ("GD-GIN-750",   4,  1100),
        ],
        "Ready for Dispatch",
        "",
    ),
]


def _make_items(rows):
    return [{"sku": sku, "quantity": qty, "unit_price": price} for sku, qty, price in rows]


def _advance_status(vo_name, from_status, to_status):
    """Walk a VO through statuses using db.set_value to bypass submit flow."""
    transitions = [
        "Draft", "Under Review", "Approved", "Packing",
        "Ready for Dispatch", "Dispatched", "In Transit", "Delivered",
    ]
    start = transitions.index(from_status) + 1
    end = transitions.index(to_status) + 1
    for status in transitions[start:end]:
        frappe.db.set_value("Vendor Order", vo_name, "order_status", status)
        frappe.db.commit()
        # Trigger pipeline at Ready for Dispatch
        if status == "Ready for Dispatch":
            from alvoraa_portal.controllers.vendor_order import _prepare_delivery_pipeline
            vo = frappe.get_doc("Vendor Order", vo_name)
            _prepare_delivery_pipeline(vo_name, vo)


def run():
    created = []
    for vendor_key, slot, item_rows, target_status, notes in ORDERS:
        vendor_id = VENDORS[vendor_key]
        address = ADDRESSES[vendor_key]

        # Check if a similar order already exists at this status (avoid dupes on re-run)
        existing = frappe.db.get_value(
            "Vendor Order",
            {"vendor": vendor_id, "order_status": target_status},
            "name",
        )
        if existing:
            print(f"SKIP (exists at {target_status}): {vendor_key} -> {existing}")
            continue

        # Insert as Draft
        vo = frappe.get_doc({
            "doctype":              "Vendor Order",
            "vendor":               vendor_id,
            "order_date":           today(),
            "delivery_slot":        slot,
            "delivery_address":     address,
            "special_instructions": notes,
            "items":                _make_items(item_rows),
        })
        vo.insert(ignore_permissions=True)
        frappe.db.commit()

        if target_status == "Draft":
            print(f"OK Draft: {vo.name} | {vendor_key}")
            created.append(vo.name)
            continue

        # Submit → Under Review
        vo.reload()
        vo.submit()
        frappe.db.commit()

        if target_status != "Under Review":
            _advance_status(vo.name, "Under Review", target_status)

        print(f"OK {target_status}: {vo.name} | {vendor_key} | "
              f"total Rs.{vo.total_amount:,.0f}")
        created.append(vo.name)

    print(f"\nDone. Created {len(created)} Vendor Orders: {created}")
    return created
