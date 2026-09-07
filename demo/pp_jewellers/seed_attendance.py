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
# Shift assignments carry a geofenced Shift Location, so a check-in must carry coordinates.
# A real ESSL bridge sends the store's coordinates with every punch; the loader does the same.
coords = {}
for e in employees():
    loc = frappe.db.get_value("Shift Location", {"location_name": e.branch}, ["latitude", "longitude"], as_dict=True)
    coords[e.name.split("-")[-1]] = (loc.latitude, loc.longitude) if loc else (None, None)
have = frappe.db.count("Employee Checkin")
if have >= len(rows):
    log(f"  {have} checkins already present, skipping load")
else:
    created = skipped = unknown = 0
    for i, row in enumerate(rows, 1):
        try:
            lat, lon = coords.get(row["attendance_device_id"], (None, None))
            add_log_based_on_employee_field(
                employee_field_value=row["attendance_device_id"], timestamp=row["timestamp"],
                device_id=row["device_id"], log_type=row["log_type"], latitude=lat, longitude=lon,
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

# ── Quarter-day late rule (build B1) ────────────────────────────────────────
if frappe.db.exists("DocType", "Attendance Deduction Rule"):
    log("Attendance Deduction Rule (build B1)")
    RULE = "PPJ Late Coming Rule"
    if not frappe.db.exists("Attendance Deduction Rule", RULE):
        frappe.get_doc({
            "doctype": "Attendance Deduction Rule", "rule_name": RULE, "company": COMPANY, "enabled": 1,
            "week_start_day": "Monday", "process_from": "2026-07-01",
            "late_threshold_minutes": 60, "count_early_exit": 1, "early_exit_threshold_minutes": 60,
            "free_violations_per_week": 1, "deduction_per_violation_days": 0.25,
            "round_up_from_days": 0.75, "round_up_to_days": 1.0, "deduct_from_leave_first": 1,
            "leave_types": [{"leave_type": "Casual Leave", "priority": 1}],   # Earned Leave is kept for encashment
            "lwp_salary_component": "Late Coming Deduction" if frappe.db.exists("Salary Component", "Late Coming Deduction") else None,
            "daily_wage_basis": "Base from Salary Structure Assignment",
            "exempt_grades": [{"employee_grade": g} for g in ("G5 Head", "G6 Leadership") if frappe.db.exists("Employee Grade", g)],
            "notify_employee": 1, "notify_manager": 1,
        }).insert(ignore_permissions=True)
        commit()
        log(f"  [created] {RULE}")
    if frappe.db.exists("Salary Structure Assignment", {"docstatus": 1}):
        from hrms.alvoraa_late_rules.late_rules import run_for_range
        frappe.set_user("Administrator")
        result = run_for_range(RULE, "2026-07-01", "2026-09-06")
        commit()
        log(f"  rule run: {result}")
        log(f"  Attendance Deductions: {frappe.db.count('Attendance Deduction', {'docstatus': 1})} (expected 231 from data/expected_deductions.csv)")
    else:
        log("  rule created; run it after Block 4 (loss of pay needs salary assignments): Attendance Deduction Rule > Run for Range")

log("Block 3 done")
counts("Shift Assignment", "Employee Checkin", "Attendance")
for status in ("Present", "Absent", "Half Day"):
    log(f"  Attendance {status}: {frappe.db.count('Attendance', {'status': status, 'docstatus': 1})}")
for emp, dates in [("PPJ-0054", ["2026-08-18", "2026-08-20", "2026-08-22"]), ("PPJ-0058", ["2026-08-03", "2026-08-07"])]:
    for d in dates:
        a = frappe.db.get_value("Attendance", {"employee": emp, "attendance_date": d, "docstatus": 1},
                                ["status", "in_time", "out_time", "late_entry", "early_exit"], as_dict=True)
        log(f"  {emp} {d}: {a}")
