"""
link_employee_users.py — Create User accounts and link them to Employee records
================================================================================
For every active Employee that has no user_id:
  1. Resolve email (company_email → personal_email fallback)
  2. If a User already exists with that email → link it
  3. If no User exists → create one (System User, Employee role, demo password)
  4. Set Employee.user_id = email

Run via:
  scp demo/link_employee_users.py root@alvoraa.co:/tmp/link_employee_users.py
  ssh root@alvoraa.co "docker cp /tmp/link_employee_users.py compose-backend-1:/tmp/ && \
    docker exec compose-backend-1 \
      /home/frappe/frappe-bench/env/bin/python /tmp/link_employee_users.py"

Demo password for all newly created users: Hr@2026
"""
import frappe

frappe.init(site="dev.alvoraa.co")
frappe.connect()

DEMO_PASSWORD = "Hr@2026"
BATCH = 50  # commit every N records

employees = frappe.db.get_all(
    "Employee",
    filters={"status": "Active", "user_id": ["in", ["", None]]},
    fields=["name", "employee_name", "first_name", "last_name",
            "company_email", "personal_email"],
    order_by="name asc",
)

existing_users = set(
    frappe.db.get_all("User", pluck="name")
)

linked = created = skipped = 0

for i, emp in enumerate(employees, 1):
    email = emp.company_email or emp.personal_email
    if not email:
        print(f"  SKIP (no email): {emp.employee_name} ({emp.name})")
        skipped += 1
        continue

    email = email.strip().lower()

    if email not in existing_users:
        # Create the User
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": emp.first_name or emp.employee_name.split()[0],
            "last_name": emp.last_name or "",
            "send_welcome_email": 0,
            "user_type": "System User",
            "new_password": DEMO_PASSWORD,
            "roles": [{"role": "Employee"}],
        })
        user.insert(ignore_permissions=True)
        existing_users.add(email)
        created += 1
        print(f"  CREATED user: {email} for {emp.employee_name}")
    else:
        linked += 1

    frappe.db.set_value(
        "Employee", emp.name, "user_id", email, update_modified=False
    )

    if i % BATCH == 0:
        frappe.db.commit()
        print(f"  ... committed {i}/{len(employees)}")

frappe.db.commit()

print()
print(f"Done. Created: {created} | Linked (existing user): {linked} | Skipped: {skipped}")
print(f"Total processed: {created + linked}")

# Verify
still_missing = frappe.db.count("Employee", {
    "status": "Active", "user_id": ["in", ["", None]]
})
print(f"Active employees still without user_id: {still_missing}  (should be 0)")

frappe.destroy()
