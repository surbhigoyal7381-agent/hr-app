import frappe

def run():
    frappe.set_user("Administrator")
    checks = {
        "Employees (Grace Group)": frappe.db.count("Employee", {"company": "Grace Group"}),
        "Vehicles": frappe.db.count("Vehicle"),
        "Vehicle Logs": frappe.db.count("Vehicle Log"),
        "Locations": frappe.db.count("Location"),
        "Shift Types": frappe.db.count("Shift Type"),
        "Custom DocType (Daily Route Log)": 1 if frappe.db.exists("DocType", "Daily Route Log") else 0,
        "KRAs": frappe.db.count("KRA"),
        "Goals (Grace Group)": frappe.db.count("Goal", {"company": "Grace Group"}),
        "Appraisal Cycles": frappe.db.count("Appraisal Cycle", {"company": "Grace Group"}),
        "Appraisal Templates": frappe.db.count("Appraisal Template"),
        "Number Cards": frappe.db.count("Number Card"),
        "Dashboard Charts": frappe.db.count("Dashboard Chart"),
        "Workspace (Promoter Command Center)": 1 if frappe.db.exists("Workspace", "Promoter Command Center") else 0,
        "Onboarding Templates": frappe.db.count("Employee Onboarding Template"),
        "Leave Period": frappe.db.count("Leave Period", {"company": "Grace Group"}),
        "Leave Types": frappe.db.count("Leave Type"),
        "Leave Policies": frappe.db.count("Leave Policy"),
        "Leave Policy Assignments": frappe.db.count("Leave Policy Assignment"),
    }
    print("\n=== Grace Group Demo Environment Verification ===")
    all_ok = True
    for name, val in checks.items():
        status = "OK" if val else "MISSING"
        if not val:
            all_ok = False
        print(f"  {'[+]' if val else '[!]'} {name}: {val}")
    print(f"\n{'All checks passed!' if all_ok else 'Some items are missing.'}")
