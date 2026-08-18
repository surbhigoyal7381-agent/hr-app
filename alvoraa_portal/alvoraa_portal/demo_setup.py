"""
Grace Portal Demo Data Setup
Run: bench --site hrms.localhost execute alvoraa_portal.alvoraa_portal.demo_setup
"""
import frappe
from frappe.utils import today, add_days, now_datetime
from datetime import datetime, timedelta
import random

NOW = now_datetime()
TODAY = today()


def make_user(email, first, last, roles=None):
    if frappe.db.exists("User", email):
        print(f"  [skip] User {email} already exists")
        return
    doc = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": first,
        "last_name": last,
        "full_name": f"{first} {last}",
        "enabled": 1,
        "user_type": "Website User",
        "new_password": "Grace@2024",
        "send_welcome_email": 0,
    })
    doc.insert(ignore_permissions=True)
    print(f"  [ok] User {email} created")


def make_vendor(vendor_name, email, phone, gst, balance):
    existing = frappe.db.get_value("Vendor", {"vendor_name": vendor_name}, "name")
    if existing:
        print(f"  [skip] Vendor {vendor_name} already exists ({existing})")
        return existing
    doc = frappe.get_doc({
        "doctype": "Vendor",
        "vendor_name": vendor_name,
        "company_name": vendor_name,
        "email": email,
        "phone": phone,
        "gst_number": gst,
        "account_status": "Active",
        "account_balance": balance,
    })
    doc.insert(ignore_permissions=True, ignore_links=True)
    print(f"  [ok] Vendor {vendor_name} created ({doc.name})")
    return doc.name


def make_vendor_user(vendor, email):
    existing = frappe.db.get_value("Vendor User", {"email": email}, "name")
    if existing:
        print(f"  [skip] Vendor User {email} already linked")
        return
    doc = frappe.get_doc({
        "doctype": "Vendor User",
        "vendor": vendor,
        "email": email,
        "frappe_user": email,
        "two_fa_enabled": 0,
        "account_locked": 0,
    })
    doc.insert(ignore_permissions=True, ignore_links=True)
    print(f"  [ok] Vendor User {email} -> {vendor}")


def make_vendor_order(vendor, vendor_name, order_date, address, status, amount, slot="Today"):
    doc = frappe.get_doc({
        "doctype": "Vendor Order",
        "vendor": vendor,
        "vendor_name": vendor_name,
        "order_date": order_date,
        "delivery_address": address,
        "delivery_slot": slot,
        "order_status": status,
        "total_amount": amount,
        "rating_submitted": 0,
    })
    doc.insert(ignore_permissions=True, ignore_links=True)
    print(f"  [ok] Vendor Order {doc.name} for {vendor_name} ({status})")
    return doc.name


def make_delivery_partner(partner_name, email, phone, vehicle_id, vehicle_reg, vehicle_type, hub):
    existing = frappe.db.get_value("Delivery Partner", {"primary_email": email}, "name")
    if existing:
        print(f"  [skip] Delivery Partner {email} already exists ({existing})")
        return existing
    doc = frappe.get_doc({
        "doctype": "Delivery Partner",
        "partner_name": partner_name,
        "partner_type": "Employee",
        "primary_phone": phone,
        "primary_email": email,
        "status": "Active",
        "is_active": 1,
        "vehicle_id": vehicle_id,
        "vehicle_registration": vehicle_reg,
        "vehicle_type": vehicle_type,
        "hub_assigned": hub,
        "can_access_portal": 1,
        "portal_username": email,
        "operational_status": "Active",
        "daily_delivery_capacity": 15,
        "total_deliveries": 0,
        "on_time_delivery_percentage": 0,
        "customer_satisfaction_rating": 0,
    })
    doc.insert(ignore_permissions=True, ignore_links=True)
    print(f"  [ok] Delivery Partner {partner_name} created ({doc.name})")
    return doc.name


def make_delivery_order(partner_id, customer_name, address, city, coords, status, delivery_date, total, slot="8AM-12PM"):
    assignment_status = "Not-Assigned" if status == "Pending" else ("In-Transit" if status in ("In Transit","At Location","Nearby","Picked Up") else "Assigned")
    doc = frappe.get_doc({
        "doctype": "Delivery Order",
        "source_order_type": "Sales Order",
        "delivery_date": delivery_date,
        "delivery_time_slot": slot,
        "customer_name": customer_name,
        "delivery_address": address,
        "delivery_city": city,
        "delivery_state": "Punjab",
        "delivery_coordinates": coords,
        "grand_total": total,
        "subtotal": total,
        "assigned_to_partner": partner_id,
        "assignment_status": assignment_status,
        "current_status": status,
        "status_updated_at": NOW,
        "feedback_provided": 0,
    })
    doc.insert(ignore_permissions=True, ignore_links=True)
    print(f"  [ok] Delivery Order {doc.name} ({status}) -> {partner_id}")
    return doc.name


def make_delivery_assignment(vendor_order, driver_id, driver_name, vehicle_reg):
    doc = frappe.get_doc({
        "doctype": "Delivery Assignment",
        "vendor_order": vendor_order,
        "driver": driver_id,
        "driver_name": driver_name,
        "vehicle_reg": vehicle_reg,
        "assigned_datetime": NOW,
        "status": "Assigned",
        "otp_verified": 0,
    })
    doc.insert(ignore_permissions=True, ignore_links=True)
    frappe.db.set_value("Vendor Order", vendor_order, "delivery_assignment", doc.name)
    print(f"  [ok] Assignment {doc.name}: {vendor_order} -> {driver_name}")


def make_tracking(partner_id, vehicle_id, delivery_order, lat, lng, speed, heading, minutes_ago):
    ts = NOW - timedelta(minutes=minutes_ago)
    frappe.get_doc({
        "doctype": "Vehicle Tracking",
        "delivery_partner": partner_id,
        "vehicle_id": vehicle_id,
        "delivery_order": delivery_order,
        "latitude": lat,
        "longitude": lng,
        "speed": speed,
        "heading": heading,
        "accuracy": 8,
        "recorded_timestamp": ts,
        "speeding_alert": 1 if speed > 60 else 0,
    }).insert(ignore_permissions=True)


def execute():
    print("\n=== Grace Portal Demo Setup ===\n")

    # ── FRAPPE USERS ──────────────────────────────────────────────────────────
    print("Creating Frappe user accounts...")
    make_user("raj.wine@gracedemo.in",   "Raj",     "Wines")
    make_user("metro.wines@gracedemo.in","Metro",    "Wines")
    make_user("quickstop@gracedemo.in",  "QuickStop","Beverages")
    make_user("driver.rajan@gracedemo.in","Rajan",   "Kumar")
    make_user("driver.suresh@gracedemo.in","Suresh", "Yadav")
    frappe.db.commit()

    # ── VENDORS ───────────────────────────────────────────────────────────────
    print("\nCreating Vendors...")
    v1 = make_vendor("Raj Wine Shop",         "raj.wine@gracedemo.in",    "98761-00001", "03AABCR1234A1Z5", 85000)
    v2 = make_vendor("Metro Wines & Spirits", "metro.wines@gracedemo.in", "98761-00002", "03AABCM5678B1Z5", 120000)
    v3 = make_vendor("QuickStop Beverages",   "quickstop@gracedemo.in",   "98761-00003", "03AABCQ9012C1Z5", 45000)
    frappe.db.commit()

    # ── VENDOR USERS (email → vendor link) ───────────────────────────────────
    print("\nLinking Vendor Users...")
    make_vendor_user(v1, "raj.wine@gracedemo.in")
    make_vendor_user(v2, "metro.wines@gracedemo.in")
    make_vendor_user(v3, "quickstop@gracedemo.in")
    frappe.db.commit()

    # ── VENDOR ORDERS ─────────────────────────────────────────────────────────
    print("\nCreating Vendor Orders...")
    # Raj Wine Shop — 3 orders
    make_vendor_order(v1, "Raj Wine Shop",
        add_days(TODAY, -5), "15 Sector 22-C, Chandigarh", "Delivered", 48500, "Today")
    vo2 = make_vendor_order(v1, "Raj Wine Shop",
        add_days(TODAY, -1), "15 Sector 22-C, Chandigarh", "In Transit", 32000, "Tomorrow")
    make_vendor_order(v1, "Raj Wine Shop",
        TODAY, "15 Sector 22-C, Chandigarh", "Approved", 27500, "Next 2 Days")

    # Metro Wines — 3 orders
    make_vendor_order(v2, "Metro Wines & Spirits",
        add_days(TODAY, -3), "Sector 35 Market, Chandigarh", "Delivered", 75000, "Today")
    vo5 = make_vendor_order(v2, "Metro Wines & Spirits",
        TODAY, "Sector 35 Market, Chandigarh", "In Transit", 62000, "Tomorrow")
    make_vendor_order(v2, "Metro Wines & Spirits",
        add_days(TODAY, 1), "Sector 35 Market, Chandigarh", "Draft", 41000, "Next 2 Days")

    # QuickStop — 2 orders
    make_vendor_order(v3, "QuickStop Beverages",
        add_days(TODAY, -2), "Phase 7, Mohali", "Delivered", 18500, "Today")
    make_vendor_order(v3, "QuickStop Beverages",
        TODAY, "Phase 7, Mohali", "Approved", 22000, "Tomorrow")
    frappe.db.commit()

    # ── DELIVERY PARTNERS ─────────────────────────────────────────────────────
    print("\nCreating Delivery Partners (Drivers)...")
    d1 = make_delivery_partner(
        "Rajan Kumar", "driver.rajan@gracedemo.in",
        "98762-11001", "PB-01-AA-1234", "PB-01-AA-1234", "Truck", "Chandigarh Hub"
    )
    d2 = make_delivery_partner(
        "Suresh Yadav", "driver.suresh@gracedemo.in",
        "98762-22002", "PB-02-BB-5678", "PB-02-BB-5678", "Van", "Chandigarh Hub"
    )
    frappe.db.commit()

    # ── DELIVERY ORDERS ───────────────────────────────────────────────────────
    print("\nCreating Delivery Orders...")
    # Rajan Kumar — 4 orders
    do1 = make_delivery_order(d1, "Raj Wine Shop",
        "15 Sector 22-C, Chandigarh", "Chandigarh",
        "30.7404,76.7871", "In Transit", TODAY, 48500, "8AM-12PM")
    make_delivery_order(d1, "Hotel Regent (Bar)",
        "Hotel Regent, Sector 17, Chandigarh", "Chandigarh",
        "30.7181,76.7918", "Assigned", TODAY, 18200, "12PM-3PM")
    make_delivery_order(d1, "Celebrations Banquets",
        "Celebrations Banquets, Panchkula", "Panchkula",
        "30.6440,76.8180", "Delivered", add_days(TODAY, -1), 31500, "8AM-12PM")
    make_delivery_order(d1, "Super Mart Sector 8",
        "Super Mart, Sector 8, Chandigarh", "Chandigarh",
        "30.7308,76.7726", "Delivered", add_days(TODAY, -2), 12800, "8AM-12PM")

    # Suresh Yadav — 4 orders
    do5 = make_delivery_order(d2, "Metro Wines & Spirits",
        "Sector 35 Market, Chandigarh", "Chandigarh",
        "30.7333,76.8000", "At Location", TODAY, 62000, "12PM-3PM")
    make_delivery_order(d2, "QuickStop Beverages",
        "Phase 7, Mohali", "Mohali",
        "30.7110,76.7220", "Assigned", TODAY, 22000, "3PM-6PM")
    make_delivery_order(d2, "Star Wines Panchkula",
        "Star Wines, Sector 5, Panchkula", "Panchkula",
        "30.6950,76.8530", "Delivered", add_days(TODAY, -1), 29000, "8AM-12PM")
    make_delivery_order(d2, "City Beverages Mohali",
        "Phase 3, Mohali", "Mohali",
        "30.6970,76.7130", "Delivered", add_days(TODAY, -3), 16500, "8AM-12PM")
    frappe.db.commit()

    # ── DELIVERY ASSIGNMENTS (link vendor orders to drivers) ──────────────────
    print("\nCreating Delivery Assignments...")
    make_delivery_assignment(vo2, d1, "Rajan Kumar",  "PB-01-AA-1234")
    make_delivery_assignment(vo5, d2, "Suresh Yadav", "PB-02-BB-5678")
    frappe.db.commit()

    # ── VEHICLE TRACKING (GPS breadcrumb trail for active drivers) ────────────
    print("\nInserting GPS tracking data...")

    # Rajan (do1): hub → Raj Wine Shop (30.7404, 76.7871), currently In Transit
    rajan_route = [
        (30.7060, 76.8001, 0,   0,   25),
        (30.7130, 76.7980, 35, 330,  20),
        (30.7220, 76.7950, 42, 340,  15),
        (30.7310, 76.7910, 38, 345,  10),
        (30.7380, 76.7880, 20, 350,   5),
        (30.7395, 76.7875,  5, 355,   1),
    ]
    for lat, lng, spd, hdg, mins in rajan_route:
        make_tracking(d1, "PB-01-AA-1234", do1, lat, lng, spd, hdg, mins)

    # Suresh (do5): hub → Metro Wines (30.7333, 76.8000), currently At Location
    suresh_route = [
        (30.7060, 76.8001, 0,   0,  40),
        (30.7140, 76.8010, 32,  10, 30),
        (30.7230, 76.8005, 40,   5, 20),
        (30.7310, 76.8002, 35,   2, 12),
        (30.7333, 76.8000,  0,   0,  5),
        (30.7333, 76.8000,  0,   0,  1),
    ]
    for lat, lng, spd, hdg, mins in suresh_route:
        make_tracking(d2, "PB-02-BB-5678", do5, lat, lng, spd, hdg, mins)

    frappe.db.commit()

    print("\n=== Setup Complete ===")
    print("\n📦 VENDOR ACCOUNTS:")
    print("  Raj Wine Shop        → raj.wine@gracedemo.in     / Grace@2024  (3 orders)")
    print("  Metro Wines          → metro.wines@gracedemo.in  / Grace@2024  (3 orders)")
    print("  QuickStop Beverages  → quickstop@gracedemo.in    / Grace@2024  (2 orders)")
    print("\n🚛 DRIVER ACCOUNTS:")
    print("  Rajan Kumar (Truck)  → driver.rajan@gracedemo.in  / Grace@2024  (4 deliveries)")
    print("  Suresh Yadav (Tempo) → driver.suresh@gracedemo.in / Grace@2024  (4 deliveries)")
    print("\n🔗 PORTAL URLS:")
    print("  Vendor Portal → http://hrms.localhost:8000/vendor-portal")
    print("  Driver Portal → http://hrms.localhost:8000/driver-portal")
