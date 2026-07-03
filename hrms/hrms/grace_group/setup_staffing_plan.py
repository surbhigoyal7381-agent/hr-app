"""
Grace Group FMCG Distribution - Frappe HR Staffing Plan (FY2026)

Creates a native "Staffing Plan" for Grace Global covering the FY2026
manpower ramp: fleet/last-mile scale-out, cold-chain, warehouse expansion
(the 1,15,000 sq.ft vicinity shed), and the new Q-Commerce (Swiggy/Zepto)
key-account desk.

The Staffing Plan controller auto-fetches current employee counts and open
job openings per designation, then derives `number_of_positions`
(= vacancies + current_count) and `total_estimated_cost`
(= vacancies * estimated_cost_per_position). So this script only needs to
declare, per designation: how many NEW positions (vacancies) and the annual
cost per position. Costs are annual CTC in INR.

Run: bench execute hrms.grace_group.setup_staffing_plan.setup_all
"""

import frappe

COMPANY = "Grace Group"
PLAN_NAME = "Grace Group FY2026 Manpower Plan"

# Plan horizon — aligned with the FY2026 calendar year.
FROM_DATE = "2026-01-01"
TO_DATE = "2026-12-31"


# ─────────────────────────────────────────────────────────────────────────────
# Manpower plan: (designation, new vacancies, annual cost/position, rationale)
# ─────────────────────────────────────────────────────────────────────────────

STAFFING_PLAN = [
    # Last-mile: scale delivery bench toward the 40-van fleet + Q-Comm morning shift
    ("Delivery Executive", 18, 240000,
     "Scale last-mile bench for the 40-van fleet and Q-Comm morning-shift coverage"),
    # Warehousing: staff the 1,15,000 sq.ft vicinity shed + Panchkula second shift
    ("Warehouse Supervisor", 4, 420000,
     "Staff the 1.15L sq.ft vicinity warehouse and Panchkula second shift"),
    # Cold chain: protect dairy/perishables, hit zero-spoilage KRA
    ("Cold Storage Supervisor", 2, 420000,
     "Expand cold-chain supervision for dairy/perishable zero-spoilage target"),
    # Q-Commerce key accounts: dedicated Swiggy/Zepto desk
    ("KAM - Q-Commerce", 2, 720000,
     "New Q-Commerce key-account desk for Swiggy/Zepto SLA ownership"),
    # Fleet control: manage 40 vehicles, RTO and route efficiency
    ("Fleet Supervisor", 2, 360000,
     "Fleet control for 40 vehicles — route efficiency and RTO reduction"),
    # GT order booking: telesales to widen General Trade reach
    ("Telesales Executive", 6, 216000,
     "General-Trade order booking to widen GT and HORECA reach"),
    # Back office: HR + Accounts to support the headcount ramp
    ("HR Executive", 1, 360000,
     "HR ops to support onboarding of the FY2026 headcount ramp"),
    ("Accounts Executive", 2, 300000,
     "Accounts bench for expanded billing and reconciliation volume"),
]


def _exists(doctype, name):
    return bool(frappe.db.exists(doctype, name))


def ensure_designations():
    """Staffing Plan rows link to Designation; create any that don't exist yet."""
    for designation, *_ in STAFFING_PLAN:
        if not _exists("Designation", designation):
            frappe.get_doc(
                {"doctype": "Designation", "designation_name": designation}
            ).insert(ignore_permissions=True)
            print(f"  [+] Designation: {designation}")
    frappe.db.commit()


def setup_staffing_plan():
    if _exists("Staffing Plan", PLAN_NAME):
        print(f"  [=] Staffing Plan already exists: {PLAN_NAME}")
        return

    doc = frappe.get_doc({
        "doctype": "Staffing Plan",
        "name": PLAN_NAME,
        "company": COMPANY,
        "from_date": FROM_DATE,
        "to_date": TO_DATE,
        "staffing_details": [
            {
                "doctype": "Staffing Plan Detail",
                "designation": designation,
                "vacancies": vacancies,
                "estimated_cost_per_position": cost,
            }
            for designation, vacancies, cost, _rationale in STAFFING_PLAN
        ],
    })
    # name is prompt-based; keep it explicit through the autoname prompt.
    doc.flags.name_set = True
    doc.insert(ignore_permissions=True)
    doc.submit()
    frappe.db.commit()

    print(f"  [+] Staffing Plan: {PLAN_NAME}")
    for row in doc.staffing_details:
        print(
            f"      {row.designation:<24} vacancies={row.vacancies:>2} "
            f"(current {row.current_count}, positions {row.number_of_positions}) "
            f"cost ~Rs.{int(row.total_estimated_cost):,}"
        )
    print(f"  [=] Total estimated FY2026 manpower budget: Rs.{int(doc.total_estimated_budget):,}")


# ─────────────────────────────────────────────────────────────────────────────
# Main Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def setup_all():
    frappe.set_user("Administrator")

    print("\n══ Grace Group FY2026 Staffing Plan ══")
    ensure_designations()
    setup_staffing_plan()

    print("\n✓ Staffing Plan setup complete!")
    print("  Open: HR > Recruitment > Staffing Plan > "
          f"'{PLAN_NAME}' — then 'Get Job Requisitions' to spin up Job Openings.")
