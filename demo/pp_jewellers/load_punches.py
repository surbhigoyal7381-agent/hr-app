"""
PP Jewellers demo - push simulated punches into Employee Checkin and run auto attendance.

Run inside the backend container, piped into bench console:
  docker exec -i compose-backend-1 bash -c 'cd /home/frappe/frappe-bench && bench --site dev.alvoraa.co console' < /tmp/load_punches.py
Copy docs/pp_jewellers/data/punches.csv to /tmp/punches.csv in the container first.

Idempotent: a punch that already exists (same employee, time, log type) is skipped.
"""
import csv
import frappe
from frappe.utils import get_datetime
from hrms.hr.doctype.employee_checkin.employee_checkin import add_log_based_on_employee_field

PUNCHES = "/tmp/punches.csv"
SHIFTS = ["PPJ Store Shift", "PPJ Head Office Shift"]
LAST_SYNC = "2026-09-07 00:00:00"

created = skipped = unknown = 0
with open(PUNCHES) as f:
    for i, row in enumerate(csv.DictReader(f), 1):
        try:
            add_log_based_on_employee_field(
                employee_field_value=row["attendance_device_id"],
                timestamp=row["timestamp"],
                device_id=row["device_id"],
                log_type=row["log_type"],
            )
            created += 1
        except frappe.ValidationError as e:
            msg = str(e)
            if "already" in msg.lower() or "duplicate" in msg.lower():
                skipped += 1
            elif "No Employee" in msg or "not found" in msg.lower():
                unknown += 1
            else:
                raise
        if i % 1000 == 0:
            frappe.db.commit()
            print(f"{i} rows: created={created} skipped={skipped} unknown={unknown}")
frappe.db.commit()
print(f"done: created={created} skipped={skipped} unknown={unknown}")

# Let auto attendance see every punch, then process both shifts now instead of waiting for the hourly job
for name in SHIFTS:
    shift = frappe.get_doc("Shift Type", name)
    shift.db_set("last_sync_of_checkin", get_datetime(LAST_SYNC))
    shift.process_auto_attendance()
    frappe.db.commit()
    print(f"processed auto attendance for {name}")

print("Attendance rows:", frappe.db.count("Attendance", {"docstatus": 1}))
