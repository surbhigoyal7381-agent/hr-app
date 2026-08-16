"""
Grace Drinks Pvt Ltd – Q1 2026 Performance Tracking Fixture
=============================================================
Run via:  bench --site dev.alvoraa.co console < demo/setup_performance.py

What this script does (in order):
  1.  Verify / create Company, Departments, Designations
  2.  Verify / create all 11 Employee records
  3.  Create the Appraisal Cycle  "Q1 2026 Performance Cycle"
  4.  Create KRAs (one per functional area)
  5.  Create the CEO macro parent goal  (is_group, no cycle link)
  6.  Create each employee's two Q1 goals with progress %
  7.  Create Appraisals (appraisal_kra = automated, formula = goal_score)
       – insert → validate runs → scores calculated automatically
  8.  Submit every Appraisal (docstatus 0 → 1)
  9.  Wire parent_goal links via direct DB (bypasses same-employee rule)
 10.  Rebuild Goal NestedSet tree
 11.  Mark Appraisal Cycle as Completed
"""

import frappe
from frappe.utils import flt, nowdate
from frappe.utils.nestedset import rebuild_tree   # signature: rebuild_tree(doctype)

# ──────────────────────────────────────────────────────────────
COMPANY        = "Grace Drinks Pvt Ltd"
CYCLE_NAME     = "Q1 2026 Performance Cycle"
Q1_START       = "2026-01-01"
Q1_END         = "2026-03-31"
JOINING_DATE   = "2024-01-01"          # back-dated for all fixture employees
# ──────────────────────────────────────────────────────────────


# ════════════════════════════════════════════════════════════════
#  SECTION 1 – master data helpers
# ════════════════════════════════════════════════════════════════

def _ensure(doctype, name, **kwargs):
    """Insert a document if it does not already exist; return its name."""
    if not frappe.db.exists(doctype, name):
        doc = frappe.get_doc({"doctype": doctype, "name": name, **kwargs})
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"  [created] {doctype}: {name}")
    return name


def setup_company():
    if not frappe.db.exists("Company", COMPANY):
        doc = frappe.get_doc({
            "doctype": "Company",
            "company_name": COMPANY,
            "abbr": "GD",
            "default_currency": "INR",
            "country": "India",
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"  [created] Company: {COMPANY}")
    else:
        print(f"  [exists]  Company: {COMPANY}")


def setup_departments():
    departments = [
        "Management",
        "Finance",
        "Technology",
        "Sales",
        "Operations",
    ]
    for dept in departments:
        full_name = f"{dept} - GD"
        if not frappe.db.exists("Department", full_name):
            doc = frappe.get_doc({
                "doctype": "Department",
                "department_name": dept,
                "company": COMPANY,
            })
            doc.insert(ignore_permissions=True)
        frappe.db.commit()
    print("  Departments verified.")


def _dept(name):
    """Return the full department name as stored by Frappe (appends ' - GD')."""
    full = f"{name} - GD"
    if frappe.db.exists("Department", full):
        return full
    # fallback: try plain name
    if frappe.db.exists("Department", name):
        return name
    return full


def setup_designations():
    designations = [
        "Director - Strategy",
        "Director - Finance",
        "Director - Digital",
        "KAM - Dairy",
        "KAM - Snacks",
        "KAM - Processed Foods",
        "KAM - Hardware",
        "Cold Storage Supervisor",
        "Warehouse Supervisor",
        "Logistics Manager",
    ]
    for desig in designations:
        if not frappe.db.exists("Designation", desig):
            doc = frappe.get_doc({
                "doctype": "Designation",
                "designation_name": desig,
            })
            doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print("  Designations verified.")


# ════════════════════════════════════════════════════════════════
#  SECTION 2 – Employee records
# ════════════════════════════════════════════════════════════════

EMPLOYEE_DEFS = [
    # (full_name, first_name, last_name, designation, department, reports_to_name)
    ("D. K. Malhotra",       "D. K.",       "Malhotra",  "Director - Strategy",      "Management", None),
    ("Mukesh Mittal",        "Mukesh",      "Mittal",    "Director - Finance",       "Finance",    "D. K. Malhotra"),
    ("Chaitanya Malhotra",   "Chaitanya",   "Malhotra",  "Director - Digital",       "Technology", "D. K. Malhotra"),
    ("Gurpreet Singh",       "Gurpreet",    "Singh",     "Logistics Manager",        "Operations", "D. K. Malhotra"),
    ("Arjun Sandhu",         "Arjun",       "Sandhu",    "KAM - Dairy",              "Sales",      "D. K. Malhotra"),
    ("Neha Sharma",          "Neha",        "Sharma",    "KAM - Snacks",             "Sales",      "D. K. Malhotra"),
    ("Rohit Verma",          "Rohit",       "Verma",     "KAM - Processed Foods",    "Sales",      "D. K. Malhotra"),
    ("Priya Singh",          "Priya",       "Singh",     "KAM - Hardware",           "Sales",      "D. K. Malhotra"),
    ("Vikramjeet Singh",     "Vikramjeet",  "Singh",     "Cold Storage Supervisor",  "Operations", "Gurpreet Singh"),
    ("Amit Patel",           "Amit",        "Patel",     "Warehouse Supervisor",     "Operations", "Gurpreet Singh"),
    ("Sandeep Kaur",         "Sandeep",     "Kaur",      "Cold Storage Supervisor",  "Operations", "Gurpreet Singh"),
]


def _get_employee_id(full_name):
    return frappe.db.get_value("Employee", {"employee_name": full_name, "company": COMPANY}, "name")


def setup_employees():
    """
    Create employees in dependency order so reports_to links resolve.
    Returns dict: full_name → employee_id
    """
    emp_map = {}

    for (full_name, first, last, designation, department, reports_to_name) in EMPLOYEE_DEFS:
        existing = _get_employee_id(full_name)
        if existing:
            emp_map[full_name] = existing
            print(f"  [exists]  Employee: {full_name} ({existing})")
            continue

        reports_to_id = emp_map.get(reports_to_name) if reports_to_name else None

        doc = frappe.get_doc({
            "doctype": "Employee",
            "first_name": first,
            "last_name": last,
            "employee_name": full_name,
            "company": COMPANY,
            "designation": designation,
            "department": _dept(department),
            "reports_to": reports_to_id,
            "status": "Active",
            "gender": "Male",
            "date_of_birth": "1985-01-01",
            "date_of_joining": JOINING_DATE,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        emp_map[full_name] = doc.name
        print(f"  [created] Employee: {full_name} ({doc.name})")

    return emp_map


# ════════════════════════════════════════════════════════════════
#  SECTION 3 – Appraisal Cycle
# ════════════════════════════════════════════════════════════════

def setup_appraisal_cycle():
    if frappe.db.exists("Appraisal Cycle", CYCLE_NAME):
        cycle = frappe.get_doc("Appraisal Cycle", CYCLE_NAME)
        print(f"  [exists]  Appraisal Cycle: {CYCLE_NAME}")
        return cycle

    cycle = frappe.get_doc({
        "doctype": "Appraisal Cycle",
        "cycle_name": CYCLE_NAME,
        "company": COMPANY,
        "start_date": Q1_START,
        "end_date": Q1_END,
        "kra_evaluation_method": "Automated Based on Goal Progress",
        "calculate_final_score_based_on_formula": 1,
        # formula variable "goal_score" maps to total_score (out of 5) in the data dict
        "final_score_formula": "goal_score",
    })
    cycle.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"  [created] Appraisal Cycle: {CYCLE_NAME}")
    return cycle


# ════════════════════════════════════════════════════════════════
#  SECTION 4 – KRAs
# ════════════════════════════════════════════════════════════════

KRA_TITLES = {
    "CEO":          "Strategic Leadership & Revenue",
    "Finance":      "Financial Governance",
    "Digital":      "Digital Innovation",
    "Dairy":        "Dairy Channel Revenue",
    "Snacks":       "Snacks Distribution Revenue",
    "ProcFoods":    "Processed Foods Revenue",
    "Hardware":     "Hardware Channel Revenue",
    "ColdStore1":   "Cold Storage Operations",
    "Warehouse":    "Warehouse Operations",
    "ColdStore2":   "Cold Chain Quality Control",
    "Logistics":    "Logistics Efficiency",
}


def setup_kras():
    kra_map = {}
    for key, title in KRA_TITLES.items():
        if not frappe.db.exists("KRA", title):
            doc = frappe.get_doc({"doctype": "KRA", "title": title})
            doc.insert(ignore_permissions=True)
        kra_map[key] = title
    frappe.db.commit()
    print("  KRAs verified.")
    return kra_map


# ════════════════════════════════════════════════════════════════
#  SECTION 5 – Macro Parent Goal (CEO, no cycle link)
# ════════════════════════════════════════════════════════════════

MACRO_GOAL_NAME_TITLE = "Achieve Grace Drinks Pvt Ltd 200 Cr Annual Target"


def create_macro_goal(ceo_id):
    existing = frappe.db.get_value("Goal", {"goal_name": MACRO_GOAL_NAME_TITLE, "employee": ceo_id}, "name")
    if existing:
        print(f"  [exists]  Macro Goal: {existing}")
        return existing

    doc = frappe.get_doc({
        "doctype": "Goal",
        "goal_name": MACRO_GOAL_NAME_TITLE,
        "employee": ceo_id,
        "is_group": 1,
        "start_date": Q1_START,
        "end_date": Q1_END,
        # no appraisal_cycle → excluded from automated scoring queries
        # no kra       → not mandatory when appraisal_cycle is absent
        "description": (
            "Organizational macro-goal: Grace Drinks Pvt Ltd 200 Cr Annual Revenue Target. "
            "Q1 2026 Milestone: ₹45 Cr.  All functional goals cascade under this anchor."
        ),
    })
    doc.flags.ignore_validate = True          # skip active-cycle & employee checks
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"  [created] Macro Goal: {doc.name}")
    return doc.name


# ════════════════════════════════════════════════════════════════
#  SECTION 6 – Employee Goals
# ════════════════════════════════════════════════════════════════

def _calc_progress(actual, target, lower_is_better=False, zero_target_miss=False):
    """
    Return goal progress as a percentage (0–100).
    - lower_is_better  : progress = target/actual * 100 (meeting target = 100 %)
    - zero_target_miss : target == 0 means any non-zero actual is a complete miss → 0 %
    """
    if zero_target_miss:
        return 0.0
    if lower_is_better:
        if flt(actual) == 0:
            return 100.0
        return min(100.0, flt(target) / flt(actual) * 100)
    return min(100.0, flt(actual) / flt(target) * 100)


# goal_data: list of (employee_full_name, kra_key, goal_name, progress_pct, description)
def _goal_rows(emp_map, kra_map):
    return [
        # ── CEO – D. K. Malhotra ────────────────────────────────
        ("D. K. Malhotra", "CEO",
         "Secure new national multinational brand partnerships",
         _calc_progress(4, 3),          # actual=4, target=3 → 100 %
         "Target: 3 new MNC partnerships | Actual: 4 secured (UPWARD +33 %)"),

        ("D. K. Malhotra", "CEO",
         "Group Strategic Revenue Target Realization – Q1",
         _calc_progress(48, 45),        # actual=48 Cr, target=45 Cr → 100 %
         "Q1 Revenue Target: ₹45 Cr | Actual: ₹48 Cr (UPWARD +6.7 %)"),

        # ── Director Finance – Mukesh Mittal ────────────────────
        ("Mukesh Mittal", "Finance",
         "Reduce Accounts Receivable turnaround across Modern Trade",
         _calc_progress(44, 30, lower_is_better=True),   # 30/44 → 68.18 %
         "Target: ≤30 days AR | Actual: 44 days (DOWNWARD – collection lag)"),

        ("Mukesh Mittal", "Finance",
         "Group OpEx control and compliance mapping",
         _calc_progress(102, 100),      # 102 % efficiency → 100 %
         "Target: 100 % OpEx efficiency | Actual: 102 % (UPWARD)"),

        # ── Director Digital – Chaitanya Malhotra ───────────────
        ("Chaitanya Malhotra", "Digital",
         "Deploy automated systems to cut manual operations burden",
         _calc_progress(100, 100),      # 100 %
         "Target: 100 % automation deployment | Actual: 100 % (MET)"),

        ("Chaitanya Malhotra", "Digital",
         "Integrate partner-specific automated billing portals",
         _calc_progress(2, 5),          # 2/5 → 40 %
         "Target: 5 billing portals | Actual: 2 (DOWNWARD – legacy ERP constraints)"),

        # ── KAM Dairy – Arjun Sandhu ────────────────────────────
        ("Arjun Sandhu", "Dairy",
         "Amul & Verka institutional Q1 revenue scaling",
         _calc_progress(14.5, 12),      # 14.5/12 → 100 % (capped)
         "Target: ₹12 Cr | Actual: ₹14.5 Cr (UPWARD +20.8 %)"),

        ("Arjun Sandhu", "Dairy",
         "Minimize distribution stockouts at Key Modern Trade Outlets",
         100.0,                         # target <2 %, actual 1.5 % → met
         "Target: <2 % stockout | Actual: 1.5 % (UPWARD – target beat)"),

        # ── KAM Snacks – Neha Sharma ────────────────────────────
        ("Neha Sharma", "Snacks",
         "Lay's & Kurkure high-velocity channel distribution volume",
         _calc_progress(12.8, 15),      # 12.8/15 → 85.33 %
         "Target: ₹15 Cr | Actual: ₹12.8 Cr (DOWNWARD – supply-side shortfalls)"),

        ("Neha Sharma", "Snacks",
         "Direct delivery SLA compliance with Quick-Commerce channels",
         _calc_progress(99, 98),        # 99/98 → 100 % (capped)
         "Target: 98 % SLA | Actual: 99 % (UPWARD – Swiggy/Blinkit/Zepto)"),

        # ── KAM Processed Foods – Rohit Verma ───────────────────
        ("Rohit Verma", "ProcFoods",
         "Expand regional penetration for Del Monte & Wingreens Farms",
         _calc_progress(2.9, 3.5),      # 2.9/3.5 → 82.86 %
         "Target: ₹3.5 Cr | Actual: ₹2.9 Cr (DOWNWARD)"),

        ("Rohit Verma", "ProcFoods",
         "Modern Trade relationship health index",
         _calc_progress(90, 85),        # 90/85 → 100 % (capped)
         "Target: 85 % | Actual: 90 % (UPWARD)"),

        # ── KAM Hardware – Priya Singh ──────────────────────────
        ("Priya Singh", "Hardware",
         "Drive channel distribution growth for Dulux & Roff",
         _calc_progress(4.8, 4),        # 4.8/4 → 100 % (capped)
         "Target: ₹4 Cr | Actual: ₹4.8 Cr (UPWARD +20 %)"),

        ("Priya Singh", "Hardware",
         "Collection cycle containment for general trade paint dealers",
         _calc_progress(48, 35, lower_is_better=True),   # 35/48 → 72.92 %
         "Target: ≤35 days | Actual: 48 days (DOWNWARD – dealer credit overrun)"),

        # ── Cold Storage Supervisor – Vikramjeet Singh ──────────
        ("Vikramjeet Singh", "ColdStore1",
         "Perishable product spoilage containment (McCain/Amul/Epigamia)",
         _calc_progress(0.8, 0, zero_target_miss=True),  # 0 % target breached → 0 %
         "Target: 0 % spoilage | Actual: 0.8 % (DOWNWARD – partial cooling failure)"),

        ("Vikramjeet Singh", "ColdStore1",
         "Cold Storage physical infrastructure uptime",
         _calc_progress(99.9, 99.5),    # exceeds → 100 %
         "Target: 99.5 % uptime | Actual: 99.9 % (UPWARD)"),

        # ── Warehouse Supervisor – Amit Patel ───────────────────
        ("Amit Patel", "Warehouse",
         "Maximize warehouse capacity utilization indices",
         _calc_progress(92, 85),        # exceeds → 100 %
         "Target: 85 % | Actual: 92 % (UPWARD)"),

        ("Amit Patel", "Warehouse",
         "Cross-docking dispatch turnaround time minimization",
         _calc_progress(58, 45, lower_is_better=True),   # 45/58 → 77.59 %
         "Target: <45 min | Actual: 58 min (DOWNWARD – local labour shortage)"),

        # ── Cold Storage Supervisor – Sandeep Kaur ──────────────
        ("Sandeep Kaur", "ColdStore2",
         "High-velocity inward inspection processing times",
         _calc_progress(24, 30, lower_is_better=True),   # 24/30 → 100 % (beat target)
         "Target: <30 min | Actual: 24 min (UPWARD)"),

        ("Sandeep Kaur", "ColdStore2",
         "Perishable inventory expiration mitigation",
         _calc_progress(2, 0, zero_target_miss=True),    # 0 errors target, 2 actual → 0 %
         "Target: 0 expiration errors | Actual: 2 batch identification slip-ups (DOWNWARD)"),

        # ── Logistics Manager – Gurpreet Singh ──────────────────
        ("Gurpreet Singh", "Logistics",
         "Outward logistics scheduling efficiency index",
         _calc_progress(91, 95),        # 91/95 → 95.79 %
         "Target: 95 % | Actual: 91 % (DOWNWARD)"),

        ("Gurpreet Singh", "Logistics",
         "Primary and secondary route optimization cost savings",
         _calc_progress(7.2, 5),        # exceeds → 100 %
         "Target: 5 % cost reduction | Actual: 7.2 % (UPWARD)"),
    ]


def create_all_goals(emp_map, kra_map):
    """
    Insert all employee goals linked to the Appraisal Cycle and their KRA.
    Returns list of dicts with employee, kra_key, and goal name for later use.
    """
    created = []
    rows = _goal_rows(emp_map, kra_map)

    for (emp_full, kra_key, goal_title, progress, description) in rows:
        emp_id  = emp_map[emp_full]
        kra_title = kra_map[kra_key]

        existing = frappe.db.get_value(
            "Goal",
            {"goal_name": goal_title, "employee": emp_id},
            "name",
        )
        if existing:
            print(f"  [exists]  Goal: {goal_title[:60]}…")
            created.append({
                "emp_full": emp_full, "emp_id": emp_id,
                "kra_key": kra_key,  "kra_title": kra_title,
                "goal_name": existing, "progress": progress,
            })
            continue

        doc = frappe.get_doc({
            "doctype": "Goal",
            "goal_name": goal_title,
            "employee": emp_id,
            "appraisal_cycle": CYCLE_NAME,
            "kra": kra_title,
            "start_date": Q1_START,
            "end_date": Q1_END,
            "progress": round(progress, 2),
            "description": description,
        })
        doc.insert(ignore_permissions=True, ignore_mandatory=True)
        frappe.db.commit()
        created.append({
            "emp_full": emp_full, "emp_id": emp_id,
            "kra_key": kra_key,  "kra_title": kra_title,
            "goal_name": doc.name, "progress": progress,
        })
        print(f"  [created] Goal ({round(progress,1):5.1f}%): {goal_title[:70]}")

    return created


# ════════════════════════════════════════════════════════════════
#  SECTION 7 – Appraisals
# ════════════════════════════════════════════════════════════════

def create_appraisals(emp_map, kra_map, goal_rows):
    """
    For each employee:
      - Build one Appraisal doc with one Appraisal KRA row (100 % weightage)
      - The validate() hook calls set_goal_score() which averages the two
        goals' progress for that KRA / employee / cycle → goal_completion
      - calculate_final_score() uses formula 'goal_score' = total_score (out of 5)
    """
    appraisal_names = {}

    # Group goals by employee
    from collections import defaultdict
    emp_kras = defaultdict(set)
    for row in goal_rows:
        emp_kras[row["emp_full"]].add(row["kra_title"])

    for emp_full, emp_id in emp_map.items():
        existing = frappe.db.get_value(
            "Appraisal",
            {"employee": emp_id, "appraisal_cycle": CYCLE_NAME, "docstatus": ["!=", 2]},
            "name",
        )
        if existing:
            print(f"  [exists]  Appraisal for {emp_full}: {existing}")
            appraisal_names[emp_full] = existing
            continue

        kras_for_emp = list(emp_kras.get(emp_full, []))
        if not kras_for_emp:
            print(f"  [skip]   No goals found for {emp_full}, skipping appraisal.")
            continue

        # Equal weightage across KRAs
        per_kra_weight = round(100.0 / len(kras_for_emp), 2)
        # Adjust last row to ensure sum == 100
        weights = [per_kra_weight] * len(kras_for_emp)
        weights[-1] = round(100.0 - per_kra_weight * (len(kras_for_emp) - 1), 2)

        appraisal_kra_rows = []
        for i, kra_title in enumerate(kras_for_emp):
            appraisal_kra_rows.append({
                "kra": kra_title,
                "per_weightage": weights[i],
            })

        doc = frappe.get_doc({
            "doctype": "Appraisal",
            "naming_series": "HR-APR-.YYYY.-",
            "employee": emp_id,
            "company": COMPANY,
            "appraisal_cycle": CYCLE_NAME,
            "rate_goals_manually": 0,
            "appraisal_kra": appraisal_kra_rows,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        appraisal_names[emp_full] = doc.name
        print(
            f"  [created] Appraisal {doc.name} for {emp_full} "
            f"| total_score={doc.total_score:.2f} | final_score={doc.final_score:.2f}"
        )

    return appraisal_names


# ════════════════════════════════════════════════════════════════
#  SECTION 8 – Submit Appraisals
# ════════════════════════════════════════════════════════════════

def submit_appraisals(appraisal_names):
    for emp_full, apr_name in appraisal_names.items():
        doc = frappe.get_doc("Appraisal", apr_name)
        if doc.docstatus == 1:
            print(f"  [already submitted] {apr_name}")
            continue
        doc.submit()
        frappe.db.commit()
        print(
            f"  [submitted] {apr_name} ({emp_full}) "
            f"| final_score={doc.final_score:.2f}"
        )


# ════════════════════════════════════════════════════════════════
#  SECTION 9 – Wire parent_goal links via direct DB
#              (bypasses same-employee validation)
# ════════════════════════════════════════════════════════════════

def wire_parent_goals(emp_map, macro_goal_id, goal_rows, ceo_id):
    """
    Set parent_goal on every individual Q1 goal to the CEO macro goal.
    CEO's own two Q1 goals (same employee) also link to the macro goal.
    Uses frappe.db.set_value to bypass the Frappe same-employee rule –
    valid for fixture/simulation purposes.
    """
    for row in goal_rows:
        if row["goal_name"] == macro_goal_id:
            continue                    # don't self-link the macro goal

        existing_parent = frappe.db.get_value("Goal", row["goal_name"], "parent_goal")
        if existing_parent:
            continue                    # already linked

        frappe.db.set_value("Goal", row["goal_name"], "parent_goal", macro_goal_id)

    frappe.db.commit()
    print(f"  parent_goal links set → {macro_goal_id}")


# ════════════════════════════════════════════════════════════════
#  SECTION 10 – Rebuild NestedSet & Complete Cycle
# ════════════════════════════════════════════════════════════════

def finalize_cycle():
    # Mark cycle Completed (bypasses the UI check for unsubmitted appraisals
    # since we've already submitted them all above)
    frappe.db.set_value("Appraisal Cycle", CYCLE_NAME, "status", "Completed")
    frappe.db.commit()
    print(f"  Appraisal Cycle '{CYCLE_NAME}' → Completed")


# ════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ════════════════════════════════════════════════════════════════

def execute():
    frappe.set_user("Administrator")

    print("\n" + "═" * 60)
    print("  Grace Drinks Q1 2026 Performance Setup")
    print("═" * 60)

    # ── Step 1: Master data ──────────────────────────────────────
    print("\n[1/11] Company …")
    setup_company()

    print("\n[2/11] Departments …")
    setup_departments()

    print("\n[3/11] Designations …")
    setup_designations()

    # ── Step 2: Employees ────────────────────────────────────────
    print("\n[4/11] Employees …")
    emp_map = setup_employees()

    # ── Step 3: Appraisal Cycle ──────────────────────────────────
    print("\n[5/11] Appraisal Cycle …")
    cycle = setup_appraisal_cycle()

    # ── Step 4: KRAs ─────────────────────────────────────────────
    print("\n[6/11] KRAs …")
    kra_map = setup_kras()

    # ── Step 5: CEO Macro Goal ───────────────────────────────────
    print("\n[7/11] CEO Macro Parent Goal …")
    ceo_id = emp_map["D. K. Malhotra"]
    macro_goal_id = create_macro_goal(ceo_id)

    # ── Step 6: Employee Goals ───────────────────────────────────
    print("\n[8/11] Q1 Employee Goals …")
    goal_rows = create_all_goals(emp_map, kra_map)

    # ── Step 7: Appraisals (scores auto-calculated in validate) ──
    print("\n[9/11] Appraisals …")
    appraisal_names = create_appraisals(emp_map, kra_map, goal_rows)

    # ── Step 8: Submit Appraisals ────────────────────────────────
    print("\n[10/11] Submitting Appraisals …")
    submit_appraisals(appraisal_names)

    # ── Step 9: Wire parent_goal (post-submission, no re-scoring) ─
    print("\n[10b] Wiring parent_goal hierarchy …")
    wire_parent_goals(emp_map, macro_goal_id, goal_rows, ceo_id)

    # ── Step 10: Rebuild NestedSet ───────────────────────────────
    print("\n[10c] Rebuilding Goal tree (NestedSet) …")
    rebuild_tree("Goal")
    frappe.db.commit()

    # ── Step 11: Complete Cycle ──────────────────────────────────
    print("\n[11/11] Completing Appraisal Cycle …")
    finalize_cycle()

    # ── Summary ──────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("  FINAL SCORES SUMMARY – Q1 2026")
    print("═" * 60)
    print(f"  {'Employee':<28}  {'Appraisal':<18}  {'Final Score':>11}")
    print("  " + "─" * 58)
    for emp_full, apr_name in sorted(appraisal_names.items()):
        score = frappe.db.get_value("Appraisal", apr_name, "final_score") or 0
        print(f"  {emp_full:<28}  {apr_name:<18}  {flt(score):>10.2f}")
    print("═" * 60)
    print("  Setup complete. Access: http://localhost:8000")
    print("═" * 60 + "\n")
