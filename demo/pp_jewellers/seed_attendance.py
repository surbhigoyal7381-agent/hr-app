"""
PP Jewellers demo - Block 3 (config-only part): shift assignments, simulated
ESSL punches, auto attendance.

Reads data/punches.csv (45,232 rows, 1 Jul to 6 Sep 2026). Pushes each row
through the same whitelisted API a real ESSL bridge would call, then runs
auto attendance for both shifts immediately instead of waiting for the hourly
job. Absent days (no punch) are marked by the same process.

The quarter-day rule (build B1) is NOT here. Once B1 is deployed, run the
rule for 2026-07-01 to 2026-09-06 from the Attendance Deduction Rule form.

Idempotent: duplicate punches are skipped; attendance is only created where missing.
"""
import os
import sys

sys.path.insert(0, os.environ.get("PPJ_SCRIPT_DIR", "/tmp/ppj"))
from ppj_common import *  # noqa: F401,F403
from frappe.utils import get_datetime
from hrms.hr.doctype.employee_checkin.employee_checkin import add_log_based_on_employee_field

connect()

LAST_SYNC = "2026-09-07 00:00:00"

# ── Shift assignments ───────────────────────────────────────────────────────
log("Shift Assignments")
made = 0
for e in employees():
    if not e.default_shift:
        continue
    if frappe.db.exists("Shift Assignment", {"employee": e.name, "shift_type": e.default_shift, "docstatus": 1}):
        continue
    sa = frappe.get_doc({"doctype": "Shift Assignment", "employee": e.name, "shift_type": e.default_shift,
                         "company": COMPANY, "start_date": "2026-07-01", "status": "Active",
                         "shift_location": e.branch if frappe.db.exists("Shift Location", {"location_name": e.branch}) else None})
    sa.flags.ignore_permissions = True
    sa.insert()
    sa.submit()
    made += 1
    if made % 100 == 0:
        commit()
commit()
log(f"  {made} shift assignments created")

# ── Punches ─────────────────────────────────────────────────────────────────
log("Employee Checkins from punches.csv")
rows = read_csv("punches.csv")
have = frappe.db.count("Employee Checkin")
if have >= len(rows):
    log(f"  {have} checkins already present, skipping load")
else:
    created = skipped = unknown = 0
    for i, row in enumerate(rows, 1):
        try:
            add_log_based_on_employee_field(
                employee_field_value=row["attendance_device_id"], timestamp=row["timestamp"],
                device_id=row["device_id"], log_type=row["log_type"],
            )
            created += 1
        except frappe.ValidationError as e:
            msg = str(e).lower()
            if "already" in msg or "duplicate" in msg:
                skipped += 1
            elif "no employee" in msg or "not found" in msg:
                unknown += 1
            else:
                raise
        if i % 2000 == 0:
            commit()
            log(f"  {i}/{len(rows)} created={created} skipped={skipped} unknown={unknown}")
    commit()
    log(f"  done: created={created} skipped={skipped} unknown={unknown}")

# ── Auto attendance ─────────────────────────────────────────────────────────
log("Auto attendance")
for name in (STORE_SHIFT, HO_SHIFT):
    shift = frappe.get_doc("Shift Type", name)
    shift.db_set("last_sync_of_checkin", get_datetime(LAST_SYNC))
    shift.process_auto_attendance()
    commit()
    log(f"  processed {name}")

log("Block 3 done")
counts("Shift Assignment", "Employee Checkin", "Attendance")
for status in ("Present", "Absent", "Half Day"):
    log(f"  Attendance {status}: {frappe.db.count('Attendance', {'status': status, 'docstatus': 1})}")
for emp, dates in [("PPJ-0054", ["2026-08-18", "2026-08-20", "2026-08-22"]), ("PPJ-0058", ["2026-08-03", "2026-08-07"])]:
    for d in dates:
        a = frappe.db.get_value("Attendance", {"employee": emp, "attendance_date": d, "docstatus": 1},
                                ["status", "in_time", "out_time", "late_entry", "early_exit"], as_dict=True)
        log(f"  {emp} {d}: {a}")
