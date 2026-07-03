"""
Grace Group FMCG Distribution - Master Setup Orchestrator

Runs every Grace Group phase in dependency order so a full site build can be
kicked off with a single command:

    bench execute hrms.grace_group.setup_all.run_all

Order:
  1. setup_grace_group   - company, departments, designations, employees,
                           fleet, geo-attendance, performance, dashboards
  2. setup_ats           - recruitment: requisition, opening, interviews, offer
  3. setup_staffing_plan - FY2026 manpower plan (reads open requisitions)
  4. setup_onboarding_leaves - onboarding templates + leave management
  5. setup_onboarding_process - role-based onboarding process (5 tasks)

Every phase is idempotent (guarded by existence checks), so re-running is safe.

Note: setup_q1_performance.py targets a different company ("Grace Drinks Pvt
Ltd") with its own entrypoint and is intentionally NOT part of this build.
"""

import frappe

from hrms.grace_group import (
    setup_ats,
    setup_grace_group,
    setup_onboarding_leaves,
    setup_onboarding_process,
    setup_staffing_plan,
)

# (label, module) in run order.
PHASES = [
    ("Core org, fleet, attendance, performance", setup_grace_group),
    ("Recruitment (ATS)", setup_ats),
    ("FY2026 staffing plan", setup_staffing_plan),
    ("Onboarding templates & leave management", setup_onboarding_leaves),
    ("Role-based onboarding process", setup_onboarding_process),
]


def run_all():
    frappe.set_user("Administrator")

    print("\n" + "=" * 70)
    print(" GRACE GROUP — FULL SITE BUILD")
    print("=" * 70)

    for i, (label, module) in enumerate(PHASES, start=1):
        print(f"\n########## [{i}/{len(PHASES)}] {label} ##########")
        module.setup_all()
        frappe.db.commit()

    print("\n" + "=" * 70)
    print(" ✓ Full Grace Group build complete.")
    print("=" * 70)
