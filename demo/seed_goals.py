"""
Seed SMART cascading goals + KPIs for dev.alvoraa.co demo.

Run via:
  # 1. Copy to app (first time only):
  #    docker cp demo/seed_goals.py compose-backend-1:/home/frappe/frappe-bench/apps/alvox_portal/alvox_portal/seed_goals_runner.py
  # 2. Execute:
  #    docker exec compose-backend-1 bash -c 'cd /home/frappe/frappe-bench && bench --site dev.alvoraa.co execute alvox_portal.seed_goals_runner.seed'

Hierarchy covered:
  Rajesh Krishnamurthy (MD)              HR-EMP-2026-00001
    ├── Anita Deshpande (CFO)            HR-EMP-2026-00002
    │     └── Alok Verma (Fin Mgr)       HR-EMP-2026-00011
    │           └── Sarika Bhagat        HR-EMP-2026-00010
    ├── Vikram Suryavanshi (VP Ops)      HR-EMP-2026-00003
    │     └── Mahesh Patil (Plant Head)  HR-EMP-2026-00006
    │           ├── Sandeep Kulkarni     HR-EMP-2026-00012
    │           └── Deepak Chauhan       HR-EMP-2026-00013
    ├── Priya Raghavan (HR Mgr)          HR-EMP-2026-00004
    │     └── Neha Kapoor (HR Exec)      HR-EMP-2026-00008
    └── Suresh Iyer (Sales Mgr)          HR-EMP-2026-00005
          └── Karthik Subramanian        HR-EMP-2026-00009
"""
import frappe


def _emp(eid):
    return frappe.db.get_value("Employee", eid, "employee_name") or eid


def make_goal(employee_id, goal_name, target, unit, actual_pct,
              status, trajectory, start="2026-01-01", end="2026-12-31",
              cascade=None, parent=None, goal_type="Business"):
    actual = round(target * actual_pct / 100, 2)
    doc = frappe.get_doc({
        "doctype":         "Individual Goal",
        "employee":        employee_id,
        "employee_name":   _emp(employee_id),
        "goal_name":       goal_name,
        "goal_type":       goal_type,
        "target_value":    target,
        "unit":            unit,
        "actual_progress": actual,
        "progress_pct":    actual_pct,
        "start_date":      start,
        "end_date":        end,
        "status":          status,
        "trajectory":      trajectory,
        "goal_cascade":    cascade,
        "parent_goal":     parent,
    })
    doc.flags.ignore_permissions = True
    doc.flags.ignore_mandatory   = True
    doc.flags.ignore_validate    = True
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc.name


def make_kpi(employee_id, kpi_name, category, unit, direction,
             baseline, target, actual, status, goal_id,
             start="2026-01-01", end="2026-12-31"):
    attainment = min(round(actual / target * 100) if target else 100, 100)
    doc = frappe.get_doc({
        "doctype":         "KPI",
        "employee":        employee_id,
        "employee_name":   _emp(employee_id),
        "kpi_name":        kpi_name,
        "category":        category,
        "unit":            unit,
        "direction":       direction,
        "baseline_value":  baseline,
        "target_value":    target,
        "actual_value":    actual,
        "attainment_pct":  attainment,
        "status":          status,
        "individual_goal": goal_id,
        "period_start":    start,
        "period_end":      end,
        "weightage":       100,
    })
    doc.flags.ignore_permissions = True
    doc.flags.ignore_mandatory   = True
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc.name


def seed():
    """Entry point: bench --site <site> execute alvox_portal.seed_goals_runner.seed"""
    # ── Clean up previous demo run ─────────────────────────────────────────────
    for dt in ["KPI", "Individual Goal", "Goal Cascade"]:
        for r in frappe.get_all(dt, pluck="name"):
            frappe.delete_doc(dt, r, ignore_permissions=True, force=True)
    frappe.db.commit()
    print("Cleared existing goals/KPIs/cascades.")

    # ── Goal Cascade ───────────────────────────────────────────────────────────
    co = frappe.db.sql("SELECT name FROM tabCompany LIMIT 1")[0][0]
    cascade_doc = frappe.get_doc({
        "doctype":        "Goal Cascade",
        "cascade_name":   "FY2026 Company OKRs",
        "company":        co,
        "unit":           "Revenue",     # select options: Orders/Revenue/Skill Score/Units Sold
        "period_start":   "2026-01-01",
        "period_end":     "2026-12-31",
        "company_target": 100,
        "status":         "Active",
        "description":    "Company-wide strategic objectives for Financial Year 2026.",
    })
    cascade_doc.flags.ignore_permissions = True
    cascade_doc.flags.ignore_validate    = True
    cascade_doc.flags.ignore_mandatory   = True
    cascade_doc.insert(ignore_permissions=True)
    frappe.db.commit()
    CASCADE = cascade_doc.name
    print("Cascade created:", CASCADE)

    # Employee IDs
    MD   = "HR-EMP-2026-00001"   # Rajesh Krishnamurthy
    CFO  = "HR-EMP-2026-00002"   # Anita Deshpande
    VPOP = "HR-EMP-2026-00003"   # Vikram Suryavanshi
    HRM  = "HR-EMP-2026-00004"   # Priya Raghavan
    SM   = "HR-EMP-2026-00005"   # Suresh Iyer
    PLNT = "HR-EMP-2026-00006"   # Mahesh Patil
    FIN  = "HR-EMP-2026-00011"   # Alok Verma
    HREX = "HR-EMP-2026-00008"   # Neha Kapoor
    SEEX = "HR-EMP-2026-00009"   # Karthik Subramanian
    GMFG = "HR-EMP-2026-00012"   # Sandeep Kulkarni
    QAMG = "HR-EMP-2026-00013"   # Deepak Chauhan
    ACEX = "HR-EMP-2026-00010"   # Sarika Bhagat

    # ── L1: Rajesh Krishnamurthy (MD) ─────────────────────────────────────────
    g_md1 = make_goal(MD,
        "Achieve Rs.50 Crore Annual Revenue by Dec 2026",
        target=50, unit="Crore", actual_pct=70,
        status="Active", trajectory="On Track", cascade=CASCADE)
    make_kpi(MD, "Total Revenue (YTD)", "Financial", "Crore", "Higher is Better",
        baseline=0, target=50, actual=35, status="Active", goal_id=g_md1)

    g_md2 = make_goal(MD,
        "Reduce Employee Attrition Rate to Below 8% by Dec 2026",
        target=8, unit="Percent", actual_pct=100,
        status="Completed", trajectory="On Track", cascade=CASCADE)
    make_kpi(MD, "Annual Attrition Rate", "People", "Percent", "Lower is Better",
        baseline=12, target=8, actual=6.8, status="Achieved", goal_id=g_md2)

    g_md3 = make_goal(MD,
        "Achieve ISO 9001:2015 Certification by Q4 2026",
        target=100, unit="Percent", actual_pct=48,
        status="Active", trajectory="At Risk", cascade=CASCADE)
    make_kpi(MD, "Certification Milestone Completion", "Process", "Percent", "Higher is Better",
        baseline=0, target=100, actual=48, status="Active", goal_id=g_md3)
    print("MD goals done.")

    # ── L2: Anita Deshpande (CFO) ─────────────────────────────────────────────
    g_cfo1 = make_goal(CFO,
        "Reduce Operating Cost-to-Revenue Ratio by 12% vs 2025",
        target=12, unit="Percent", actual_pct=80,
        status="Active", trajectory="On Track", cascade=CASCADE, parent=g_md1)
    make_kpi(CFO, "OpEx as % of Revenue", "Financial", "Percent", "Lower is Better",
        baseline=38, target=33.4, actual=34.2, status="Active", goal_id=g_cfo1)

    g_cfo2 = make_goal(CFO,
        "Implement Automated Financial Reporting by Jun 2026",
        target=100, unit="Percent", actual_pct=100,
        status="Completed", trajectory="On Track", cascade=CASCADE, parent=g_md1)
    make_kpi(CFO, "Financial Reporting Automation Coverage", "Process", "Percent", "Higher is Better",
        baseline=0, target=100, actual=100, status="Achieved", goal_id=g_cfo2)
    print("CFO goals done.")

    # ── L2: Vikram Suryavanshi (VP Ops) ───────────────────────────────────────
    g_vp1 = make_goal(VPOP,
        "Achieve 95% On-Time Delivery Rate for All Dispatches by Dec 2026",
        target=95, unit="Percent", actual_pct=72,
        status="Active", trajectory="On Track", cascade=CASCADE, parent=g_md1)
    make_kpi(VPOP, "On-Time Delivery Rate", "Customer", "Percent", "Higher is Better",
        baseline=82, target=95, actual=88.4, status="Active", goal_id=g_vp1)

    g_vp2 = make_goal(VPOP,
        "Reduce Unplanned Production Downtime by 20% vs 2025",
        target=20, unit="Percent", actual_pct=40,
        status="Active", trajectory="At Risk", cascade=CASCADE, parent=g_md3)
    make_kpi(VPOP, "Unplanned Downtime Reduction (%)", "Process", "Percent", "Higher is Better",
        baseline=0, target=20, actual=8, status="Active", goal_id=g_vp2)
    print("VP Ops goals done.")

    # ── L2: Priya Raghavan (HR Manager) ───────────────────────────────────────
    g_hr1 = make_goal(HRM,
        "Drive Company Attrition Below 8% Through Retention Initiatives",
        target=8, unit="Percent", actual_pct=100,
        status="Completed", trajectory="On Track", cascade=CASCADE, parent=g_md2)
    make_kpi(HRM, "Voluntary Attrition Rate", "People", "Percent", "Lower is Better",
        baseline=12, target=8, actual=6.8, status="Achieved", goal_id=g_hr1)

    g_hr2 = make_goal(HRM,
        "Complete Mandatory Compliance Training for 80% of Workforce by Sep 2026",
        target=80, unit="Percent", actual_pct=68,
        status="Active", trajectory="On Track", cascade=CASCADE, parent=g_md2)
    make_kpi(HRM, "Mandatory Training Completion Rate", "People", "Percent", "Higher is Better",
        baseline=0, target=80, actual=54.4, status="Active", goal_id=g_hr2)
    print("HR Manager goals done.")

    # ── L2: Suresh Iyer (Sales Manager) ───────────────────────────────────────
    g_sm1 = make_goal(SM,
        "Close Rs.25 Crore in Sales Revenue for H2 2026 (Jul-Dec)",
        target=25, unit="Crore", actual_pct=56,
        status="Active", trajectory="At Risk", cascade=CASCADE, parent=g_md1)
    make_kpi(SM, "H2 Sales Revenue (YTD)", "Financial", "Crore", "Higher is Better",
        baseline=0, target=25, actual=14, status="Active", goal_id=g_sm1)

    g_sm2 = make_goal(SM,
        "Expand Active Client Base by 15 New Accounts by Dec 2026",
        target=15, unit="Number", actual_pct=67,
        status="Active", trajectory="On Track", cascade=CASCADE, parent=g_md1)
    make_kpi(SM, "New Client Accounts Added", "Customer", "Number", "Higher is Better",
        baseline=0, target=15, actual=10, status="Active", goal_id=g_sm2)
    print("Sales Manager goals done.")

    # ── L3: Mahesh Patil (Plant Head) ─────────────────────────────────────────
    g_pl1 = make_goal(PLNT,
        "Maintain Overall Equipment Effectiveness (OEE) Above 85% Monthly",
        target=85, unit="Percent", actual_pct=88,
        status="Active", trajectory="On Track", cascade=CASCADE, parent=g_vp1)
    make_kpi(PLNT, "Monthly OEE Average", "Process", "Percent", "Higher is Better",
        baseline=78, target=85, actual=88.2, status="Active", goal_id=g_pl1)
    print("Plant Head goals done.")

    # ── L3: Alok Verma (Finance Manager) ──────────────────────────────────────
    g_fin1 = make_goal(FIN,
        "Reduce Month-End Financial Closing Cycle to 3 Working Days by Jun 2026",
        target=3, unit="Days", actual_pct=100,
        status="Completed", trajectory="On Track", cascade=CASCADE, parent=g_cfo1)
    make_kpi(FIN, "Month-End Close Cycle Time (Days)", "Process", "Days", "Lower is Better",
        baseline=7, target=3, actual=3, status="Achieved", goal_id=g_fin1)
    print("Finance Manager goals done.")

    # ── L3: Neha Kapoor (HR Executive) ────────────────────────────────────────
    g_hrex1 = make_goal(HREX,
        "Ensure 100% New Joiner Onboarding Documents Completed Within 3 Days of Joining",
        target=100, unit="Percent", actual_pct=91,
        status="Active", trajectory="On Track", cascade=CASCADE, parent=g_hr2)
    make_kpi(HREX, "Onboarding Document Completion Rate (3-Day SLA)", "People", "Percent", "Higher is Better",
        baseline=70, target=100, actual=91, status="Active", goal_id=g_hrex1)
    print("HR Executive goals done.")

    # ── L3: Karthik Subramanian (Sales Executive) ─────────────────────────────
    g_seex1 = make_goal(SEEX,
        "Close 8 New Client Accounts in H2 2026 (Personal Target)",
        target=8, unit="Number", actual_pct=50,
        status="Active", trajectory="At Risk", cascade=CASCADE, parent=g_sm2)
    make_kpi(SEEX, "New Accounts Closed (H2)", "Customer", "Number", "Higher is Better",
        baseline=0, target=8, actual=4, status="Active", goal_id=g_seex1)
    print("Sales Executive goals done.")

    # ── L3: Sandeep Kulkarni (GM Manufacturing) ───────────────────────────────
    g_gmfg1 = make_goal(GMFG,
        "Achieve Zero Lost-Time Injuries (LTI) Across All Production Lines in 2026",
        target=1, unit="Number", actual_pct=100,
        status="Completed", trajectory="On Track", cascade=CASCADE, parent=g_vp2)
    make_kpi(GMFG, "Lost-Time Injuries (Count)", "Process", "Number", "Lower is Better",
        baseline=3, target=1, actual=0, status="Achieved", goal_id=g_gmfg1)
    print("GM Manufacturing goals done.")

    # ── L3: Deepak Chauhan (QA Manager) ───────────────────────────────────────
    g_qamg1 = make_goal(QAMG,
        "Reduce Customer Quality Complaints by 30% vs 2025 Baseline by Dec 2026",
        target=30, unit="Percent", actual_pct=33,
        status="Active", trajectory="Off Track", cascade=CASCADE, parent=g_vp2)
    make_kpi(QAMG, "Customer Complaint Reduction (%)", "Customer", "Percent", "Higher is Better",
        baseline=0, target=30, actual=10, status="Active", goal_id=g_qamg1)
    print("QA Manager goals done.")

    # ── L4: Sarika Bhagat (Accounts Executive) ────────────────────────────────
    g_acex1 = make_goal(ACEX,
        "Maintain Invoice Accuracy Rate Above 99% for All Processed Invoices",
        target=99, unit="Percent", actual_pct=73,
        status="Active", trajectory="On Track", cascade=CASCADE, parent=g_fin1)
    make_kpi(ACEX, "Invoice Accuracy Rate (%)", "Financial", "Percent", "Higher is Better",
        baseline=94, target=99, actual=97.3, status="Active", goal_id=g_acex1)
    print("Accounts Executive goals done.")

    # ── Summary ────────────────────────────────────────────────────────────────
    total_goals = frappe.db.count("Individual Goal")
    total_kpis  = frappe.db.count("KPI")
    print(f"\nDone. {total_goals} goals and {total_kpis} KPIs created on {frappe.local.site}")
    return {"goals": total_goals, "kpis": total_kpis}
