"""
PP Jewellers demo - employee master generator.

Produces docs/pp_jewellers/data/employees.csv : 400 employees across
5 stores (72 each) and the Chandigarh head office (40), with a full
reports_to tree, grades, monthly CTC, device IDs, PF/ESI numbers.

Deterministic (seeded) so re-running gives the same file.
Run from the repo root:  python3 demo/pp_jewellers/generate_employees.py
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(20260907)

OUT = Path(__file__).resolve().parents[2] / "docs" / "pp_jewellers" / "data" / "employees.csv"
COMPANY = "PP Jewellers Pvt Ltd"

FIRST_M = ["Aman", "Rohit", "Vikram", "Gurpreet", "Harpreet", "Manish", "Sandeep", "Rajat", "Ankit", "Deepak",
           "Karan", "Nitin", "Sahil", "Varun", "Mohit", "Rahul", "Sumit", "Arjun", "Jaspreet", "Tarun",
           "Pankaj", "Vishal", "Naveen", "Gaurav", "Yogesh", "Ravi", "Suresh", "Ramesh", "Balwinder", "Kuldeep",
           "Parveen", "Ashok", "Surinder", "Dinesh", "Mukesh", "Rakesh", "Sanjay", "Ajay", "Vinod", "Harish"]
FIRST_F = ["Priya", "Neha", "Simran", "Pooja", "Kiran", "Anjali", "Ritu", "Shweta", "Nidhi", "Kavita",
           "Manpreet", "Jasleen", "Sakshi", "Divya", "Aarti", "Sunita", "Meenakshi", "Preeti", "Swati", "Payal",
           "Komal", "Rashmi", "Bhavna", "Isha", "Tanvi", "Sonia", "Renu", "Seema", "Mamta", "Geeta"]
LAST = ["Sharma", "Verma", "Gupta", "Singh", "Kaur", "Malhotra", "Kapoor", "Bansal", "Aggarwal", "Jain",
        "Chopra", "Mehta", "Arora", "Bhatia", "Sethi", "Khanna", "Goel", "Mittal", "Saini", "Dhillon",
        "Sandhu", "Gill", "Bedi", "Sodhi", "Yadav", "Chauhan", "Rana", "Thakur", "Kumar", "Garg"]

STORES = [
    ("PPJ Chandigarh Sector 17", "Chandigarh", "Chandigarh Store", "CHD"),
    ("PPJ Ambala City", "Ambala", "Ambala Store", "AMB"),
    ("PPJ Noida Sector 18", "Noida", "Noida Store", "NOI"),
    ("PPJ Delhi Karol Bagh", "Delhi", "Delhi Store", "DKB"),
    ("PPJ Delhi South Extension", "Delhi", "Delhi Store", "DSE"),
]
# Stores open 7 days. Each store employee has one fixed weekly off, Monday to Friday,
# staggered across the team so weekends are fully staffed. Modelled as one Holiday List
# per city per off-day, e.g. "Chandigarh Store Holiday List - Off Tuesday".
WEEKLY_OFF_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
HEAD_OFFICE = ("PPJ Head Office Chandigarh", "Chandigarh", "Head Office Holiday List", "HO")

# grade -> (monthly CTC low, high)
GRADE_BAND = {
    "G1 Support": (14000, 18000),
    "G2 Executive": (18000, 28000),
    "G3 Senior Executive": (28000, 45000),
    "G4 Manager": (45000, 80000),
    "G5 Head": (80000, 150000),
    "G6 Leadership": (400000, 400000),
}

# Store roles: (designation, department, grade, count, reports_to designation key)
STORE_ROLES = [
    ("Store In-charge",                 "Store Management",       "G5 Head",             1,  "OWNER"),
    ("Assistant Store Manager",         "Store Management",       "G4 Manager",          1,  "Store In-charge"),
    ("Store HR & Admin Executive",      "Store Management",       "G3 Senior Executive", 1,  "Store In-charge"),
    ("Store Accountant",                "Cashiering & Accounts",  "G3 Senior Executive", 1,  "Store In-charge"),
    ("Vault & Inventory Custodian",     "Vault & Inventory",      "G3 Senior Executive", 2,  "Store In-charge"),
    ("Floor Manager - Gold",            "Sales",                  "G4 Manager",          1,  "Assistant Store Manager"),
    ("Floor Manager - Diamond",         "Sales",                  "G4 Manager",          1,  "Assistant Store Manager"),
    ("Floor Manager - Silver & Fashion","Sales",                  "G4 Manager",          1,  "Assistant Store Manager"),
    ("Customer Relationship Executive", "Customer Service",       "G2 Executive",        3,  "Assistant Store Manager"),
    ("Visual Merchandiser",             "Store Management",       "G2 Executive",        1,  "Assistant Store Manager"),
    ("Senior Sales Executive",          "Sales",                  "G3 Senior Executive", 12, "FLOOR"),
    ("Sales Executive",                 "Sales",                  "G2 Executive",        24, "FLOOR"),
    ("Trainee Sales Executive",         "Sales",                  "G2 Executive",        2,  "FLOOR"),
    ("Gold Valuer",                     "Valuation & Karigari",   "G3 Senior Executive", 2,  "Floor Manager - Gold"),
    ("Karigar",                         "Valuation & Karigari",   "G2 Executive",        3,  "Floor Manager - Gold"),
    ("Cashier",                         "Cashiering & Accounts",  "G2 Executive",        4,  "Store Accountant"),
    ("Security Guard",                  "Security & Housekeeping","G1 Support",          8,  "Store HR & Admin Executive"),
    ("Housekeeping Staff",              "Security & Housekeeping","G1 Support",          4,  "Store HR & Admin Executive"),
]
assert sum(r[3] for r in STORE_ROLES) == 72, sum(r[3] for r in STORE_ROLES)

# Head office roles: (designation, department, grade, count, reports_to designation)
HO_ROLES = [
    ("Owner & Managing Director",       "Management",              "G6 Leadership",       1, None),
    ("Executive Assistant to MD",       "Management",              "G3 Senior Executive", 1, "Owner & Managing Director"),
    ("Head - Finance & Accounts",       "Finance & Accounts",      "G5 Head",             1, "Owner & Managing Director"),
    ("Accountant",                      "Finance & Accounts",      "G3 Senior Executive", 3, "Head - Finance & Accounts"),
    ("Accounts Executive",              "Finance & Accounts",      "G2 Executive",        2, "Head - Finance & Accounts"),
    ("Internal Auditor",                "Finance & Accounts",      "G4 Manager",          1, "Head - Finance & Accounts"),
    ("Head - Human Resources",          "Human Resources",         "G5 Head",             1, "Owner & Managing Director"),
    ("HR Executive",                    "Human Resources",         "G2 Executive",        2, "Head - Human Resources"),
    ("Recruitment Executive",           "Human Resources",         "G2 Executive",        1, "Head - Human Resources"),
    ("Payroll & Compliance Executive",  "Human Resources",         "G3 Senior Executive", 1, "Head - Human Resources"),
    ("Training & Development Executive","Human Resources",         "G3 Senior Executive", 1, "Head - Human Resources"),
    ("Head - Purchase & Sourcing",      "Purchase & Sourcing",     "G5 Head",             1, "Owner & Managing Director"),
    ("Purchase Executive",              "Purchase & Sourcing",     "G2 Executive",        2, "Head - Purchase & Sourcing"),
    ("Bullion Officer",                 "Purchase & Sourcing",     "G3 Senior Executive", 1, "Head - Purchase & Sourcing"),
    ("Central Vault & Inventory Manager","Central Vault & Inventory","G4 Manager",        1, "Owner & Managing Director"),
    ("Inventory Executive",             "Central Vault & Inventory","G2 Executive",       2, "Central Vault & Inventory Manager"),
    ("Head - Marketing",                "Marketing",               "G5 Head",             1, "Owner & Managing Director"),
    ("Marketing Executive",             "Marketing",               "G2 Executive",        2, "Head - Marketing"),
    ("Graphic Designer",                "Marketing",               "G2 Executive",        1, "Head - Marketing"),
    ("IT Manager",                      "Information Technology",  "G4 Manager",          1, "Owner & Managing Director"),
    ("IT Support Executive",            "Information Technology",  "G2 Executive",        1, "IT Manager"),
    ("Admin Manager",                   "Administration",          "G4 Manager",          1, "Owner & Managing Director"),
    ("Admin Executive",                 "Administration",          "G2 Executive",        1, "Admin Manager"),
    ("Receptionist",                    "Administration",          "G2 Executive",        1, "Admin Manager"),
    ("Office Assistant",                "Administration",          "G1 Support",          2, "Admin Manager"),
    ("Driver",                          "Administration",          "G1 Support",          2, "Admin Manager"),
    ("Head - Design & Quality",         "Design & Quality",        "G5 Head",             1, "Owner & Managing Director"),
    ("Jewellery Designer",              "Design & Quality",        "G3 Senior Executive", 2, "Head - Design & Quality"),
    ("Hallmarking & QC Officer",        "Design & Quality",        "G3 Senior Executive", 1, "Head - Design & Quality"),
    ("Legal & Compliance Officer",      "Legal & Compliance",      "G4 Manager",          1, "Owner & Managing Director"),
]
assert sum(r[3] for r in HO_ROLES) == 40, sum(r[3] for r in HO_ROLES)

FIELDS = ["employee_id", "first_name", "last_name", "employee_name", "gender", "date_of_birth",
          "date_of_joining", "company", "branch", "city", "department", "designation", "employee_grade",
          "reports_to", "employment_type", "status", "holiday_list", "weekly_off_day", "default_shift",
          "attendance_device_id", "user_id", "monthly_ctc", "pf_uan", "esi_number",
          "persona_note"]

used_names = set()
rows = []
counter = [0]


def _name(gender):
    while True:
        fn = random.choice(FIRST_M if gender == "Male" else FIRST_F)
        ln = random.choice(LAST)
        if gender == "Female" and ln == "Singh":
            ln = "Kaur"
        if (fn, ln) not in used_names:
            used_names.add((fn, ln))
            return fn, ln


def _emp(designation, department, grade, branch, city, holiday_list, reports_to, gender=None, note=""):
    counter[0] += 1
    emp_id = f"PPJ-{counter[0]:04d}"
    if branch == HEAD_OFFICE[0]:
        weekly_off = "Sunday"
    else:
        weekly_off = WEEKLY_OFF_DAYS[counter[0] % len(WEEKLY_OFF_DAYS)]
        holiday_list = f"{holiday_list} Holiday List - Off {weekly_off}"
    gender = gender or random.choice(["Male", "Male", "Female"])  # ~1/3 women
    fn, ln = _name(gender)
    lo, hi = GRADE_BAND[grade]
    ctc = int(round(random.uniform(lo, hi) / 500.0) * 500)
    age = {"G1 Support": (21, 50), "G2 Executive": (21, 35), "G3 Senior Executive": (25, 42),
           "G4 Manager": (30, 48), "G5 Head": (35, 55), "G6 Leadership": (52, 52)}[grade]
    dob = date(2026, 1, 1) - timedelta(days=365 * random.randint(*age) + random.randint(0, 364))
    tenure_years = {"G1 Support": (0, 6), "G2 Executive": (0, 5), "G3 Senior Executive": (1, 9),
                    "G4 Manager": (3, 12), "G5 Head": (5, 15), "G6 Leadership": (20, 20)}[grade]
    doj = date(2026, 4, 1) - timedelta(days=365 * random.randint(*tenure_years) + random.randint(0, 364))
    device_id = f"{counter[0]:04d}"
    email = f"{fn.lower()}.{ln.lower()}{counter[0]}@ppjewellers.demo"
    uan = f"1{random.randint(10**10, 10**11 - 1)}"
    # ESI applies when gross wages are 21,000 or below (statutory ceiling - verify current value)
    esi = f"31{random.randint(10**7, 10**8 - 1)}" if ctc <= 21000 else ""
    shift = "PPJ Store Shift" if branch != HEAD_OFFICE[0] else "PPJ Head Office Shift"
    rows.append({
        "employee_id": emp_id, "first_name": fn, "last_name": ln, "employee_name": f"{fn} {ln}",
        "gender": gender, "date_of_birth": dob.isoformat(), "date_of_joining": doj.isoformat(),
        "company": COMPANY, "branch": branch, "city": city, "department": department,
        "designation": designation, "employee_grade": grade, "reports_to": reports_to or "",
        "employment_type": "Full-time", "status": "Active", "holiday_list": holiday_list,
        "weekly_off_day": weekly_off, "default_shift": shift, "attendance_device_id": device_id, "user_id": email,
        "monthly_ctc": ctc, "pf_uan": uan, "esi_number": esi, "persona_note": note,
    })
    return emp_id


# ---- Head office first (owner must exist before store in-charges) ----
ho_branch, ho_city, ho_hol, _ = HEAD_OFFICE
ho_by_desig = {}
for desig, dept, grade, count, rep_desig in HO_ROLES:
    for i in range(count):
        rep = ho_by_desig.get(rep_desig) if rep_desig else None
        note = ""
        if desig == "Owner & Managing Director":
            note = "PERSONA: Owner / CXO view"
        elif desig == "Head - Human Resources":
            note = "PERSONA: HR Manager view"
        emp_id = _emp(desig, dept, grade, ho_branch, ho_city, ho_hol, rep, note=note)
        ho_by_desig.setdefault(desig, emp_id)
owner_id = ho_by_desig["Owner & Managing Director"]

# ---- Stores ----
for s_idx, (branch, city, hol, code) in enumerate(STORES):
    by_desig = {}
    floor_managers = []
    for desig, dept, grade, count, rep_key in STORE_ROLES:
        for i in range(count):
            if rep_key == "OWNER":
                rep = owner_id
            elif rep_key == "FLOOR":
                rep = floor_managers[i % len(floor_managers)]
            else:
                rep = by_desig[rep_key]
            note = ""
            if desig == "Store In-charge":
                note = f"PERSONA: Store In-charge view ({code})"
            if desig == "Senior Sales Executive" and s_idx == 0 and i == 0:
                note = "PERSONA: Employee view (Senior Sales Executive, Chandigarh)"
            emp_id = _emp(desig, dept, grade, branch, city, hol, rep, note=note)
            by_desig.setdefault(desig, emp_id)
            if desig.startswith("Floor Manager"):
                floor_managers.append(emp_id)

assert len(rows) == 400, len(rows)
OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(rows)
print(f"wrote {len(rows)} employees to {OUT}")
