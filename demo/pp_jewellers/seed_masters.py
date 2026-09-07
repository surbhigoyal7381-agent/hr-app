"""
PP Jewellers demo - Block 1: company and master data.

Creates: Company, Fiscal Years, Branches, Shift Locations, Departments,
Designations, Employee Grades, 21 Holiday Lists, Leave Types, Leave Policy,
Leave Period, Shift Types, Job Applicant Sources, Skills, Interview Types
are NOT here (see seed_recruitment.py).

Idempotent: safe to re-run.
"""
import os
import sys

sys.path.insert(0, os.environ.get("PPJ_SCRIPT_DIR", "/tmp/ppj"))
from ppj_common import *  # noqa: F401,F403

connect()

# ── Company and fiscal years ────────────────────────────────────────────────
log("Company")
if not frappe.db.exists("Company", COMPANY):
    doc = frappe.get_doc({
        "doctype": "Company", "company_name": COMPANY, "abbr": ABBR,
        "default_currency": "INR", "country": "India", "domain": "Retail",
        "chart_of_accounts": "Standard",
    })
    doc.insert(ignore_permissions=True)
    log(f"  [created] Company: {COMPANY}")
commit()

for year, start, end in [("2025-2026", "2025-04-01", "2026-03-31"), ("2026-2027", FY_START, FY_END)]:
    if not frappe.db.exists("Fiscal Year", year):
        fy = frappe.get_doc({"doctype": "Fiscal Year", "year": year,
                             "year_start_date": start, "year_end_date": end})
        fy.append("companies", {"company": COMPANY})
        fy.insert(ignore_permissions=True)
        log(f"  [created] Fiscal Year: {year}")
    else:
        fy = frappe.get_doc("Fiscal Year", year)
        if not any(c.company == COMPANY for c in fy.companies):
            fy.append("companies", {"company": COMPANY})
            fy.save(ignore_permissions=True)
commit()

# ── Branches and shift locations ────────────────────────────────────────────
log("Branches and Shift Locations")
BRANCHES = {
    "PPJ Chandigarh Sector 17": (30.7410, 76.7830),
    "PPJ Ambala City": (30.3782, 76.7767),
    "PPJ Noida Sector 18": (28.5708, 77.3260),
    "PPJ Delhi Karol Bagh": (28.6519, 77.1906),
    "PPJ Delhi South Extension": (28.5691, 77.2216),
    HEAD_OFFICE: (30.7046, 76.8010),
}
for branch, (lat, lon) in BRANCHES.items():
    ensure("Branch", branch, {"branch": branch})
    if frappe.db.exists("DocType", "Shift Location"):
        ensure("Shift Location", {"location_name": branch},
               {"checkin_radius": 150, "latitude": lat, "longitude": lon})
commit()

# ── Departments ─────────────────────────────────────────────────────────────
log("Departments")
DEPARTMENTS = [
    "Store Management", "Sales", "Customer Service", "Cashiering & Accounts",
    "Valuation & Karigari", "Vault & Inventory", "Security & Housekeeping",
    "Management", "Finance & Accounts", "Human Resources", "Purchase & Sourcing",
    "Central Vault & Inventory", "Marketing", "Information Technology",
    "Administration", "Design & Quality", "Legal & Compliance",
]
for d in DEPARTMENTS:
    ensure("Department", {"department_name": d, "company": COMPANY})
commit()

# ── Designations and grades ─────────────────────────────────────────────────
log("Designations and Employee Grades")
for row in read_csv("designations.csv"):
    ensure("Designation", row["designation"], {"designation_name": row["designation"]}, quiet=True)
GRADES = {
    "G1 Support": 16000, "G2 Executive": 23000, "G3 Senior Executive": 36000,
    "G4 Manager": 62000, "G5 Head": 115000, "G6 Leadership": 400000,
}
for g, base in GRADES.items():
    ensure("Employee Grade", g, {"default_base_pay": base, "currency": "INR"})
commit()

# ── Holiday lists (21) ──────────────────────────────────────────────────────
log("Holiday Lists")
NATIONAL = [("2026-08-15", "Independence Day"), ("2026-10-02", "Gandhi Jayanti"),
            ("2026-11-09", "Diwali next day (store closed for stock-take)"),
            ("2027-01-26", "Republic Day"), ("2027-03-23", "Holi")]
HO_EXTRA = [("2026-08-28", "Raksha Bandhan"), ("2026-10-20", "Dussehra"), ("2026-11-08", "Diwali"),
            ("2026-11-24", "Guru Nanak Jayanti"), ("2026-12-25", "Christmas"), ("2027-04-13", "Baisakhi")]
# Festival dates above are approximate demo values - verify against a calendar.


def make_holiday_list(name, weekly_off, holidays):
    if frappe.db.exists("Holiday List", name):
        return
    hl = frappe.get_doc({"doctype": "Holiday List", "holiday_list_name": name,
                         "from_date": FY_START, "to_date": FY_END, "weekly_off": weekly_off})
    for d, desc in holidays:
        if FY_START <= d <= FY_END:
            hl.append("holidays", {"holiday_date": d, "description": desc})
    hl.insert(ignore_permissions=True)
    hl.get_weekly_off_dates()          # adds one row per weekly-off day
    hl.save(ignore_permissions=True)
    log(f"  [created] Holiday List: {name} ({len(hl.holidays)} days)")


for city in ["Chandigarh", "Ambala", "Noida", "Delhi"]:
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        make_holiday_list(f"{city} Store Holiday List - Off {day}", day, NATIONAL)
make_holiday_list("Head Office Holiday List", "Sunday", NATIONAL + HO_EXTRA)
frappe.db.set_value("Company", COMPANY, "default_holiday_list", "Head Office Holiday List")
commit()

# ── Leave types, policy, period ─────────────────────────────────────────────
log("Leave Types")
LEAVE_TYPES = {
    "Casual Leave": {"max_leaves_allowed": 8, "max_continuous_days_allowed": 2, "is_carry_forward": 0},
    "Earned Leave": {"max_leaves_allowed": 15, "is_carry_forward": 1, "maximum_carry_forwarded_leaves": 30,
                     "allow_encashment": 1, "is_earned_leave": 1, "earned_leave_frequency": "Monthly",
                     "rounding": "0.5", "allocate_on_day": "Last Day"},
    "Sick Leave": {"max_leaves_allowed": 7},
    "Compensatory Off": {"is_compensatory": 1, "expire_carry_forwarded_leaves_after_days": 60},
    "Loss of Pay": {"is_lwp": 1},
}
for lt, vals in LEAVE_TYPES.items():
    if frappe.db.exists("Leave Type", lt):
        # Frappe HR ships Casual, Sick and Compensatory Off; apply the PPJ rules to them too
        frappe.db.set_value("Leave Type", lt, vals, update_modified=False)
    else:
        ensure("Leave Type", lt, {"leave_type_name": lt, **vals})
commit()

log("Leave Policy and Leave Period")
ensure("Leave Policy", {"title": "PPJ Standard Leave Policy"}, {
    "leave_policy_details": [
        {"leave_type": "Casual Leave", "annual_allocation": 8},
        {"leave_type": "Earned Leave", "annual_allocation": 15},
        {"leave_type": "Sick Leave", "annual_allocation": 7},
    ]}, submit=True)
ensure("Leave Period", {"company": COMPANY, "from_date": FY_START, "to_date": FY_END},
       {"is_active": 1, "optional_holiday_list": "Head Office Holiday List"})
commit()

# ── Shift types ─────────────────────────────────────────────────────────────
log("Shift Types")
SHIFT_COMMON = {
    "start_time": "09:30:00", "end_time": "18:30:00", "enable_auto_attendance": 1,
    "determine_check_in_and_check_out": "Strictly based on Log Type in Employee Checkin",
    "working_hours_calculation_based_on": "First Check-in and Last Check-out",
    "begin_check_in_before_shift_start_time": 90, "allow_check_out_after_shift_end_time": 240,
    "working_hours_threshold_for_half_day": 4.5, "working_hours_threshold_for_absent": 2.0,
    "enable_late_entry_marking": 1, "late_entry_grace_period": 15,
    "enable_early_exit_marking": 1, "early_exit_grace_period": 15,
    "process_attendance_after": "2026-07-01", "auto_update_last_sync": 1,
}
ensure("Shift Type", STORE_SHIFT, {**SHIFT_COMMON, "mark_auto_attendance_on_holidays": 1})
ensure("Shift Type", HO_SHIFT, {**SHIFT_COMMON, "mark_auto_attendance_on_holidays": 0})
commit()

# ── HR Settings ─────────────────────────────────────────────────────────────
log("HR Settings")
hr = frappe.get_single("HR Settings")
# Employee naming stays "Naming Series"; the seed presets the PPJ-#### name in import mode (see seed_employees.py)
hr.leave_approver_mandatory_in_leave_application = 0   # seeds set approvers; keep the demo forgiving
hr.restrict_backdated_leave_application = 0
hr.send_interview_reminder = 1
hr.send_interview_feedback_reminder = 1
hr.check_vacancies = 1
hr.allow_employee_checkin_from_mobile_app = 1
hr.allow_geolocation_tracking = 1
hr.save(ignore_permissions=True)
commit()

log("Block 1 done")
counts("Branch", "Department", "Designation", "Employee Grade", "Holiday List", "Leave Type", "Shift Type")
