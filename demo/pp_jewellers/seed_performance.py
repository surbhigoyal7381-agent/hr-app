"""
PP Jewellers demo - Block 8: performance management.

Company values, rating scale, leadership principles, feedback criteria and
appraisal template; two Appraisal Cycles (Q1 FY27 completed, Q2 FY27 live)
with Alvoraa Cycle Config; Goal Cascades with the store -> floor -> individual
tree; KPIs for every employee from data/kpi_library.csv; goal evidence and
KPI progress logs from data/sales_actuals_july.csv; Q1 manager ratings,
potential ratings, self ratings, Employee Performance Feedback, submitted
Appraisals, extensions with overall ratings, six calibration adjustments and
a sign-off; Q2 draft appraisals with partial manager ratings; upward feedback.

Both cycles include attendance in the score (build B6): targets 50 / manager
feedback 30 / attendance 20. The Q1 window has no attendance records in the
demo data, so Q1 appraisals use the average of the other two parts; the Q2
drafts show real attendance numbers.

Idempotent per section. Emails are muted.
"""
import json
import os
import random
import re
import sys

sys.path.insert(0, os.environ.get("PPJ_SCRIPT_DIR", "/tmp/ppj"))
from ppj_common import *  # noqa: F401,F403

connect()
frappe.flags.mute_emails = True
random.seed(20260907)

from alvoraa_goals.controllers.goal import recalculate_progress
from alvoraa_goals.controllers.cascade import run_alignment_check
from alvoraa_goals.controllers.kpi import rating_from_attainment
from alvoraa_portal.performance_api import _apply_kpis_to_appraisal, _sync_potential_to_extension

Q1 = "Q1 FY27 Performance Cycle"
Q2 = "Q2 FY27 Performance Cycle"
# Build B6: the cycle writes its own formula from these weights
# (goal_score * 0.5 + average_feedback_score * 0.3 + attendance_score * 0.2).
SCORING = {"include_attendance_score": 1, "goal_weight": 50, "feedback_weight": 30, "attendance_weight": 20,
           "attendance_reliability_weight": 60, "attendance_punctuality_weight": 40,
           "attendance_deduction_penalty": 0.25, "count_paid_leave_as_absent": 0,
           "attendance_when_no_data": "Use the average of the other parts",
           "attendance_exempt_grades": [{"employee_grade": g} for g in ("G5 Head", "G6 Leadership")]}
SCALE = "PPJ 5-Point"
HR_HEAD = first_employee("Head - Human Resources")
OWNER = first_employee("Owner & Managing Director")

# ── Values, scale, principles, criteria, template ──────────────────────────
log("Company values, rating scale, leadership principles, feedback criteria")
VALUES = [
    ("Purity & Trust", "💎", "We sell exactly what we say we sell. Hallmark and certificate shown before the customer asks."),
    ("Craftsmanship", "🔨", "We respect the work behind every piece. Done right the first time."),
    ("Customer Delight", "🤝", "Every visit should feel like a family occasion."),
    ("One Family", "👪", "We win as a store, not as individuals."),
    ("Discipline & Safety", "🔐", "Gold demands discipline. On time, in uniform, vault rules followed."),
]
for v, emoji, desc in VALUES:
    ensure("Company Value", {"value_name": v}, {"icon_emoji": emoji, "company": COMPANY, "is_active": 1, "description": desc})
ensure("Alvoraa Rating Scale", {"scale_name": SCALE}, {"is_default": 1, "description": "PP Jewellers standard scale",
       "items": [{"label": "Outstanding", "value": 5, "color": "#1a7f5a"}, {"label": "Exceeds Expectations", "value": 4, "color": "#4c9a2a"},
                 {"label": "Meets Expectations", "value": 3, "color": "#c8a415"}, {"label": "Needs Improvement", "value": 2, "color": "#e07b00"},
                 {"label": "Unsatisfactory", "value": 1, "color": "#c0392b"}]})
for p, desc, beh in [
    ("Leads by example on the floor", "Sells alongside the team on peak days.", "Takes the difficult customer\nIs on the floor before opening\nFollows the vault rules visibly"),
    ("Coaches every day", "Turns every sale into a lesson.", "Gives feedback the same day\nRuns a 10-minute product huddle\nLets juniors close"),
    ("Fair with targets and offs", "Targets and weekly offs are transparent.", "Explains how targets are split\nRotates festival duty\nNo favourites"),
]:
    ensure("Leadership Principle", {"principle_name": p}, {"is_active": 1, "description": desc, "expected_behaviours": beh})
CRITERIA = [(v, 12) for v, _e, _d in VALUES] + [("Customer handling", 25), ("Teamwork and coaching", 15)]
for c, _w in CRITERIA:
    ensure("Employee Feedback Criteria", c, {"criteria": c}, quiet=True)
TEMPLATE = "PPJ Standard"
ensure("KRA", "Targets achieved (KPIs)", {"title": "Targets achieved (KPIs)",
                                          "description": "Placeholder KRA; the appraisal's goal table is rebuilt from the employee's weighted KPIs."}, quiet=True)
if not frappe.db.exists("Appraisal Template", TEMPLATE):
    # Appraisal Template needs at least one KRA row; the KPI bridge replaces the goal table anyway.
    frappe.get_doc({"doctype": "Appraisal Template", "template_title": TEMPLATE,
                    "description": "Manager feedback on the five values, customer handling and teamwork.",
                    "goals": [{"key_result_area": "Targets achieved (KPIs)", "per_weightage": 100}],
                    "rating_criteria": [{"criteria": c, "per_weightage": w} for c, w in CRITERIA]}).insert(ignore_permissions=True)
    log(f"  [created] Appraisal Template {TEMPLATE}")
else:
    tpl = frappe.get_doc("Appraisal Template", TEMPLATE)
    if not tpl.rating_criteria:
        for c, w in CRITERIA:
            tpl.append("rating_criteria", {"criteria": c, "per_weightage": w})
        tpl.save(ignore_permissions=True)
        log(f"  [repaired] Appraisal Template {TEMPLATE}: criteria rows restored")
commit()

# ── Cycles and configs ──────────────────────────────────────────────────────
log("Appraisal Cycles")
emps = employees()
emp_ids = [e.name for e in emps]
by_id = {e.name: e for e in emps}


def ensure_cycle(name, start, end, status):
    if not frappe.db.exists("Appraisal Cycle", name):
        c = frappe.get_doc({"doctype": "Appraisal Cycle", "cycle_name": name, "company": COMPANY,
                            "start_date": start, "end_date": end, "kra_evaluation_method": "Manual Rating",
                            "calculate_final_score_based_on_formula": 1, "status": "Not Started",
                            "description": "Targets 50 / manager feedback 30 / attendance 20.", **SCORING})
        c.insert(ignore_permissions=True)     # the validate hook writes final_score_formula
        log(f"  [created] Appraisal Cycle {name}: {c.final_score_formula}")
    if not frappe.db.exists("Alvoraa Cycle Config", name):
        frappe.get_doc({"doctype": "Alvoraa Cycle Config", "appraisal_cycle": name,
                        "description": "Created by the PPJ seed (mirrors the cycle wizard).",
                        "employee_fields": "{}", "page_config": "[]",
                        "page_settings": json.dumps({"manager-feedback": {"overall_rating_scale": SCALE,
                                                                          "potential_rating_scale": SCALE,
                                                                          "show_potential": True},
                                                     "scoring": {"targets": 50, "manager_feedback": 30, "attendance": 20}}),
                        "selected_employees": json.dumps(emp_ids)}).insert(ignore_permissions=True)
    return name


ensure_cycle(Q1, Q1_START, Q1_END, "Completed")
ensure_cycle(Q2, Q2_START, Q2_END, "In Progress")
frappe.db.set_value("Appraisal Cycle", Q1, "status", "In Progress", update_modified=False)   # completed at the end
frappe.db.set_value("Appraisal Cycle", Q2, "status", "In Progress", update_modified=False)
commit()

# ── Cascades and goal tree ──────────────────────────────────────────────────
log("Goal Cascades and goal tree")
targets = read_csv("sales_targets.csv")
store_q = {"Q1": {}, "Q2": {}}
store_att_q1 = {}
for r in targets:
    q = "Q1" if r["period"].startswith("Q1") else "Q2"
    store_q[q][r["branch"]] = store_q[q].get(r["branch"], 0) + flt(r["target_inr"]) / 1e5     # lakh
    if q == "Q1" and r["category"] == "Gold":
        store_att_q1[r["branch"]] = flt(r["actual_inr"]) / flt(r["target_inr"])
FLOOR = {"Floor Manager - Gold": ("Gold", 0.60), "Floor Manager - Diamond": ("Diamond & Platinum", 0.32),
         "Floor Manager - Silver & Fashion": ("Silver & Fashion", 0.08)}
SHARE = {"Senior Sales Executive": 1.5, "Sales Executive": 1.0, "Trainee Sales Executive": 0.5}
STORE_LABEL = {"PPJ Chandigarh Sector 17": "Chandigarh", "PPJ Ambala City": "Ambala", "PPJ Noida Sector 18": "Noida",
               "PPJ Delhi Karol Bagh": "Karol Bagh", "PPJ Delhi South Extension": "South Extension"}
CYCLE_OF = {"Q1": (Q1, Q1_START, Q1_END), "Q2": (Q2, Q2_START, Q2_END)}


def ensure_goal(employee, goal_name, cascade, parent, target, cycle, start, end):
    name = frappe.db.get_value("Individual Goal", {"employee": employee, "goal_name": goal_name, "appraisal_cycle": cycle,
                                                   "docstatus": ["!=", 2]}, "name")
    if name:
        return name
    g = frappe.get_doc({"doctype": "Individual Goal", "employee": employee, "goal_name": goal_name, "goal_type": "Business",
                        "goal_cascade": cascade, "parent_goal": parent, "target_value": target, "unit": "Lakh",
                        "progress_mode": "Cumulative", "start_date": start, "end_date": end, "status": "Active",
                        "appraisal_cycle": cycle, "weightage": 0, "company_value": "Customer Delight"})
    g.flags.ignore_permissions = True
    g.insert()
    # Goals stay in draft: that is how the portal creates them, and submitting one sends an
    # email whose template needs built assets. The KPI bridge and the roll-ups read drafts.
    return g.name


goal_of = {"Q1": {}, "Q2": {}}     # employee -> own-sales goal name (sales staff), store/floor goals for managers
for q, (cycle, start, end) in CYCLE_OF.items():
    cname = f"{q} FY27 Company Sales"
    cascade = frappe.db.get_value("Goal Cascade", {"cascade_name": cname}, "name")
    company_target = round(sum(store_q[q].values()), 2)
    if not cascade:
        c = frappe.get_doc({"doctype": "Goal Cascade", "cascade_name": cname, "company": COMPANY, "unit": "Revenue",
                            "period_start": start, "period_end": end, "company_target": company_target, "status": "Active",
                            "description": f"Company sales target {company_target} lakh across five stores."})
        c.insert(ignore_permissions=True)
        cascade = c.name
        log(f"  [created] Goal Cascade {cname}: {company_target} lakh")
    frappe.db.set_value("Goal Cascade", cascade, "status", "Active", update_modified=False)
    for store, label in STORE_LABEL.items():
        sic = first_employee("Store In-charge", store)
        store_goal = ensure_goal(sic.name, f"{label} store sales {q}", cascade, None, round(store_q[q][store], 2), cycle, start, end)
        goal_of[q][sic.name] = store_goal
        asm = first_employee("Assistant Store Manager", store)
        goal_of[q][asm.name] = store_goal
        for fm_desig, (floor_label, share) in FLOOR.items():
            fm = first_employee(fm_desig, store)
            floor_target = round(store_q[q][store] * share, 2)
            floor_goal = ensure_goal(fm.name, f"{floor_label} floor sales {q} ({label})", cascade, store_goal, floor_target, cycle, start, end)
            goal_of[q][fm.name] = floor_goal
            team = [e for e in emps if e.reports_to == fm.name and e.designation in SHARE]
            shares = sum(SHARE[e.designation] for e in team) or 1
            for e in team:
                t = round(floor_target * SHARE[e.designation] / shares, 2)
                goal_of[q][e.name] = ensure_goal(e.name, f"Own sales {q}", cascade, floor_goal, t, cycle, start, end)
    commit()
    log(f"  {q}: {frappe.db.count('Individual Goal', {'goal_cascade': cascade, 'docstatus': ['!=', 2]})} goals on the cascade")

# ── Evidence: monthly sales per salesperson ────────────────────────────────
log("Goal evidence and progress")
july = {r["employee_id"]: r for r in read_csv("sales_actuals_july.csv")}


def add_evidence(goal_name, date, value, approver):
    if frappe.db.exists("Goal Evidence", {"parent": goal_name, "extracted_date": date}):
        return
    ev = frappe.get_doc({"doctype": "Goal Evidence", "parenttype": "Individual Goal", "parentfield": "evidence_items",
                         "parent": goal_name, "evidence_type": "Manual Entry", "value": value, "extracted_date": date,
                         "validation_status": "Approved", "approved_by": approver, "upload_date": f"{date} 18:00:00",
                         "validation_notes": "Monthly POS sales report (manual entry)"})
    ev.flags.ignore_permissions = True
    ev.insert()
    # The evidence hook parks every manual entry as Pending for HR review; the seed plays HR.
    ev.db_set({"validation_status": "Approved", "approved_by": approver, "approved_on": f"{date} 18:30:00",
               "validation_notes": "Monthly POS sales report, approved by the floor manager"}, update_modified=False)


for e in emps:
    if e.designation not in SHARE:
        continue
    approver = frappe.db.get_value("Employee", e.reports_to, "user_id") or "Administrator"
    # Q1: three months around the store's Q1 attainment
    g1 = goal_of["Q1"].get(e.name)
    if g1:
        t = frappe.db.get_value("Individual Goal", g1, "target_value")
        att = store_att_q1.get(e.branch, 1.0)
        for i, month_end in enumerate(["2026-04-30", "2026-05-31", "2026-06-30"]):
            add_evidence(g1, month_end, round(t / 3 * att * random.uniform(0.85, 1.15), 2), approver)
    g2 = goal_of["Q2"].get(e.name)
    if g2 and e.name in july:
        j = flt(july[e.name]["july_actual_inr"]) / 1e5
        add_evidence(g2, "2026-07-31", round(j, 2), approver)
        add_evidence(g2, "2026-08-31", round(j * random.uniform(0.95, 1.10), 2), approver)
commit()
# Roll individual evidence up: goal progress, then parent goals get the sum of their children as their own evidence
for q in ("Q1", "Q2"):
    goals = frappe.get_all("Individual Goal", filters={"appraisal_cycle": CYCLE_OF[q][0], "docstatus": ["!=", 2]},
                           fields=["name", "parent_goal", "employee", "end_date"])
    children = {}
    for g in goals:
        children.setdefault(g.parent_goal, []).append(g.name)
    leaf = [g.name for g in goals if g.name not in children]
    for n in leaf:
        recalculate_progress(n)
    for level in range(2):   # floors, then stores
        for g in goals:
            kids = children.get(g.name)
            if not kids:
                continue
            total = sum(frappe.db.get_value("Individual Goal", k, "actual_progress") or 0 for k in kids)
            if not frappe.db.exists("Goal Evidence", {"parent": g.name, "validation_notes": "Roll-up of floor/team goals"}):
                ev = frappe.get_doc({"doctype": "Goal Evidence", "parenttype": "Individual Goal", "parentfield": "evidence_items",
                                     "parent": g.name, "evidence_type": "Manual Entry", "value": round(total, 2),
                                     "extracted_date": str(g.end_date), "validation_status": "Approved", "approved_by": "Administrator",
                                     "validation_notes": "Roll-up of floor/team goals"})
                ev.flags.ignore_permissions = True
                ev.insert()
                ev.db_set({"validation_status": "Approved", "approved_by": "Administrator",
                           "validation_notes": "Roll-up of floor/team goals"}, update_modified=False)
            else:
                frappe.db.set_value("Goal Evidence", {"parent": g.name, "validation_notes": "Roll-up of floor/team goals"}, "value", round(total, 2))
            recalculate_progress(g.name)
    commit()
    run_alignment_check(frappe.db.get_value("Goal Cascade", {"cascade_name": f"{q} FY27 Company Sales"}, "name"))
commit()

# ── KPIs from the library ───────────────────────────────────────────────────
log("KPIs")
library = {}
for r in read_csv("kpi_library.csv"):
    library.setdefault(r["designation"], []).append(r)
GENERIC = [{"kpi_name": "Core responsibilities delivered on time", "category": "Process", "unit": "Percent", "direction": "Higher is Better", "weightage": "50", "target_basis": "95%"},
           {"kpi_name": "Quality and accuracy", "category": "Process", "unit": "Percent", "direction": "Higher is Better", "weightage": "40", "target_basis": "98%"},
           {"kpi_name": "Living our values", "category": "People", "unit": "Score", "direction": "Higher is Better", "weightage": "10", "target_basis": "manager rated 0-5"}]
VALUE_FOR_KPI = {"Living our values": "One Family"}


def target_from(basis, kpi_name, e, q):
    if kpi_name.startswith("Own sales"):
        return frappe.db.get_value("Individual Goal", goal_of[q].get(e.name), "target_value") or 10
    if kpi_name.startswith("Floor sales"):
        return round(store_q[q][e.branch] * FLOOR[e.designation][1] / 100, 2)   # crore
    if kpi_name.startswith("Store sales"):
        return round(store_q[q][e.branch] / 100, 2)                              # crore
    if "manager rated" in basis or "owner rated" in basis:
        return 5
    m = re.search(r"(\d+(?:\.\d+)?)", basis.replace(",", ""))
    val = flt(m.group(1)) if m else 1
    if "per month" in basis:
        val *= 3
    return val or 1


# Employee-level potential band for the 9-box spread
POTENTIAL = {}
for e in emps:
    r = random.random()
    POTENTIAL[e.name] = 4.5 if r < 0.10 else (3.75 if r < 0.35 else (2.75 if r < 0.85 else 1.5))
POTENTIAL["PPJ-0054"] = 3.75


def actual_for(kpi_name, direction, target, e, q, basis):
    if kpi_name.startswith(("Own sales", "Floor sales", "Store sales")):
        g = goal_of[q].get(e.name)
        prog = frappe.db.get_value("Individual Goal", g, "actual_progress") if g else 0
        return round(prog / 100, 2) if kpi_name.startswith(("Floor", "Store")) else round(prog, 2)
    if "rated" in basis:
        return 0
    spread = random.uniform(0.80, 1.20) if q == "Q1" else random.uniform(0.45, 0.75)
    if direction == "Lower is Better":
        spread = random.uniform(0.7, 1.4) if q == "Q1" else random.uniform(0.3, 0.8)
    return round(target * spread, 2)


def half(x, lo=1.0, hi=5.0):
    return max(lo, min(hi, round(x * 2) / 2))


made = 0
for q, (cycle, start, end) in CYCLE_OF.items():
    existing = {(k.employee, k.kpi_name) for k in frappe.get_all("KPI", filters={"appraisal_cycle": cycle}, fields=["employee", "kpi_name"])}
    for e in emps:
        rows = library.get(e.designation) or GENERIC
        for r in rows:
            if (e.name, r["kpi_name"]) in existing:
                continue
            target = target_from(r["target_basis"], r["kpi_name"], e, q)
            actual = actual_for(r["kpi_name"], r["direction"], target, e, q, r["target_basis"])
            att = (target / actual * 100 if actual else 0) if r["direction"] == "Lower is Better" else (actual / target * 100 if target else 0)
            k = frappe.get_doc({"doctype": "KPI", "kpi_name": r["kpi_name"], "employee": e.name, "appraisal_cycle": cycle,
                                "category": r["category"], "status": "Active", "unit": r["unit"], "progress_mode": "Cumulative",
                                "direction": r["direction"], "target_value": target, "actual_value": actual,
                                "weightage": flt(r["weightage"]), "period_start": start, "period_end": end,
                                "individual_goal": goal_of[q].get(e.name) if r["kpi_name"].startswith(("Own sales", "Floor sales", "Store sales")) else None,
                                "company_value": VALUE_FOR_KPI.get(r["kpi_name"]),
                                "description": f"Target basis: {r['target_basis']}. Source: {r.get('data_source', '')}"})
            rated = "rated" in r["target_basis"]
            if q == "Q1" or (q == "Q2" and e.name != "PPJ-0054" and hash(e.name) % 8 < 3):
                base = random.uniform(3.0, 4.8) if rated else rating_from_attainment(att)
                k.manager_rating = half(base + random.uniform(-0.5, 0.5))
                k.manager_comment = "Rated from the quarter's numbers and floor observation."
                k.potential_rating = half(POTENTIAL[e.name] + random.uniform(-0.5, 0.5))
            if q == "Q1":
                k.self_rating = half((k.manager_rating or 3) + random.uniform(-0.5, 0.8))
            if q == "Q2" and r["kpi_name"].startswith("Own sales") and e.name in july:
                j = flt(july[e.name]["july_actual_inr"]) / 1e5
                k.append("progress_log", {"log_date": "2026-07-31", "value": round(j, 2), "approval_status": "Approved", "note": "July POS report"})
                k.append("progress_log", {"log_date": "2026-08-31", "value": round(actual - j, 2), "approval_status": "Approved", "note": "August POS report"})
            k.flags.ignore_permissions = True
            k.insert()
            made += 1
            if made % 400 == 0:
                commit()
                log(f"  {made} KPIs")
    commit()
log(f"  {made} KPIs created; total {frappe.db.count('KPI')}")

# ── Q1 appraisals: self ratings, manager feedback, submit, extensions ──────
log("Q1 appraisals")


def manager_of(emp):
    rep = by_id[emp].reports_to if emp in by_id else None
    if not rep or rep == emp:
        return HR_HEAD.name          # the Owner has no manager; HR reviews the Owner's appraisal
    return rep


def stars(x):
    return max(0.2, min(1.0, round(x * 10) / 10))   # Rating field: 0-1 fraction of 5 stars, steps of 0.1


for e in emps:
    ap_name = frappe.db.get_value("Appraisal", {"employee": e.name, "appraisal_cycle": Q1, "docstatus": ["!=", 2]}, "name")
    if ap_name:
        continue
    ap = frappe.new_doc("Appraisal")
    ap.update({"employee": e.name, "appraisal_cycle": Q1, "company": COMPANY, "start_date": Q1_START, "end_date": Q1_END,
               "appraisal_template": TEMPLATE, "rate_goals_manually": 1})
    ap.set_kras_and_rating_criteria()
    perf = random.uniform(3.0, 4.8)
    for row in ap.self_ratings:
        row.rating = stars((perf + random.uniform(-0.6, 0.6)) / 5)
    ap.reflections = "Focused on converting walk-ins during the wedding season and on keeping the counter ready every morning."
    _apply_kpis_to_appraisal(ap)
    for g in ap.goals:           # Q1 is a finished quarter; the live "overdue" marker is noise there
        g.kra = g.kra.replace(" ⚠ overdue", "")
    ap.flags.ignore_permissions = True
    ap.insert()
    mgr = manager_of(e.name)
    mgr_user = frappe.db.get_value("Employee", mgr, "user_id") or "Administrator"
    fb = frappe.get_doc({"doctype": "Employee Performance Feedback", "employee": e.name, "appraisal": ap.name,
                         "appraisal_cycle": Q1, "reviewer": mgr, "user": mgr_user, "company": COMPANY,
                         "added_on": "2026-07-06 10:00:00",
                         "feedback": ("Consistent on the floor and reliable with the vault routine. "
                                      "Needs to push certified-stone add-ons harder in the festival season."),
                         "feedback_ratings": [{"criteria": c, "per_weightage": w, "rating": stars((perf + random.uniform(-0.7, 0.5)) / 5)}
                                              for c, w in CRITERIA]})
    fb.flags.ignore_permissions = True
    fb.insert()
    fb.submit()
    ap.reload()
    ap.flags.ignore_permissions = True
    ap.submit()
    ext = frappe.new_doc("Alvoraa Appraisal Extension")
    ext.update({"appraisal": ap.name, "employee": e.name, "appraisal_cycle": Q1, "review_status": "Completed",
                "overall_rating": half(ap.final_score + random.uniform(-0.4, 0.4)), "potential_rating": half(POTENTIAL[e.name]),
                "manager_feedback": fb.feedback, "overall_comment": "Reviewed and agreed in the Q1 dialogue.",
                "achievements_text": "Met the quarter's target and kept zero stock variance on my counter.",
                "challenges_text": "Walk-ins were slow in May; recovered in June with the Akshaya Tritiya push.",
                "development_needs_text": "Diamond certification training and a session on objection handling.",
                "pages_completed": json.dumps(["self-review", "manager-feedback", "final-review"])})
    if e.name == "PPJ-0054":
        ext.append("action_items", {"description": "Lead the Dhanteras solitaire counter", "assigned_to": e.name, "due_date": "2026-10-25", "status": "In Progress"})
        ext.append("action_items", {"description": "Complete IGI certification workshop", "assigned_to": e.name, "due_date": "2026-09-30", "status": "Open"})
    ext.flags.ignore_permissions = True
    ext.insert()
    _sync_potential_to_extension(ap.name, e.name, Q1)
    ext.reload()
    avg = flt(ext.avg_potential_rating) or flt(ext.potential_rating)
    ext.potential_category = ("Low Potential" if avg < 2 else "Moderate Potential" if avg < 3 else "High Potential" if avg <= 4 else "Exceptional Potential")
    ext.save(ignore_permissions=True)
    if frappe.db.count("Appraisal", {"appraisal_cycle": Q1}) % 50 == 0:
        commit()
        log(f"  {frappe.db.count('Appraisal', {'appraisal_cycle': Q1})} Q1 appraisals")
commit()

# Six calibration adjustments and the sign-off
log("Calibration")
cal = frappe.get_all("Alvoraa Appraisal Extension", filters={"appraisal_cycle": Q1}, fields=["name", "overall_rating", "employee"],
                     order_by="employee asc", limit=6)
for i, row in enumerate(cal):
    adj = half(flt(row.overall_rating) + (0.5 if i % 2 else -0.5))
    frappe.db.set_value("Alvoraa Appraisal Extension", row.name, {"overall_rating": adj, "manager_internal_notes": f"Calibrated 2026-07-12: {row.overall_rating} -> {adj} (store benchmark)."}, update_modified=False)
cfg = frappe.get_doc("Alvoraa Cycle Config", Q1)
ps = json.loads(cfg.page_settings or "{}")
ps["calibration_signoff"] = {"summary": "Q1 calibrated 2026-07-12; 6 ratings adjusted against store benchmarks.", "signed_by": HR_HEAD.user_id, "signed_on": "2026-07-12"}
cfg.page_settings = json.dumps(ps)
cfg.save(ignore_permissions=True)
frappe.db.set_value("Appraisal Cycle", Q1, "status", "Completed", update_modified=False)
frappe.db.set_value("Goal Cascade", {"cascade_name": "Q1 FY27 Company Sales"}, "status", "Completed", update_modified=False)
commit()

# ── Q2 draft appraisals ─────────────────────────────────────────────────────
log("Q2 appraisals (draft)")
n = 0
for e in emps:
    if frappe.db.exists("Appraisal", {"employee": e.name, "appraisal_cycle": Q2, "docstatus": ["!=", 2]}):
        continue
    ap = frappe.new_doc("Appraisal")
    ap.update({"employee": e.name, "appraisal_cycle": Q2, "company": COMPANY, "start_date": Q2_START, "end_date": Q2_END,
               "appraisal_template": TEMPLATE, "rate_goals_manually": 1})
    ap.set_kras_and_rating_criteria()
    ap.flags.ignore_permissions = True
    ap.insert()
    rated = frappe.db.count("KPI", {"employee": e.name, "appraisal_cycle": Q2, "manager_rating": [">", 0]}) > 0
    frappe.get_doc({"doctype": "Alvoraa Appraisal Extension", "appraisal": ap.name, "employee": e.name, "appraisal_cycle": Q2,
                    "review_status": "Manager Review" if rated else "Employee Review"}).insert(ignore_permissions=True)
    n += 1
    if n % 100 == 0:
        commit()
commit()
log(f"  {n} Q2 appraisals created")

# ── Upward feedback (Q1) ────────────────────────────────────────────────────
log("Upward feedback")
n = 0
for e in emps:
    if e.designation in SHARE and hash(e.name) % 10 < 3 and e.reports_to:
        if frappe.db.exists("Upward Feedback", {"from_employee": e.name, "about_employee": e.reports_to, "appraisal_cycle": Q1}):
            continue
        frappe.get_doc({"doctype": "Upward Feedback", "from_employee": e.name, "about_employee": e.reports_to,
                        "appraisal_cycle": Q1, "submitted_on": "2026-07-03", "rating": half(random.uniform(3.0, 5.0)),
                        "comments": "Runs the morning huddle every day and takes the difficult customers himself. Could rotate festival duty more evenly."}).insert(ignore_permissions=True)
        n += 1
commit()
log(f"  {n} upward feedback records")

log("Block 8 done")
counts("Company Value", "Goal Cascade", "Individual Goal", "Goal Evidence", "KPI", "Appraisal", "Employee Performance Feedback",
       "Alvoraa Appraisal Extension", "Upward Feedback")
for emp in ("PPJ-0054", "PPJ-0041"):
    ap = frappe.db.get_value("Appraisal", {"employee": emp, "appraisal_cycle": Q1, "docstatus": 1},
                             ["name", "total_score", "avg_feedback_score", "self_score", "final_score"], as_dict=True)
    ext = frappe.db.get_value("Alvoraa Appraisal Extension", {"employee": emp, "appraisal_cycle": Q1},
                              ["overall_rating", "avg_potential_rating", "potential_category"], as_dict=True)
    log(f"  {emp} Q1: {ap} | {ext}")
for cname in ("Q1 FY27 Company Sales", "Q2 FY27 Company Sales"):
    c = frappe.db.get_value("Goal Cascade", {"cascade_name": cname}, ["company_target", "aggregate_progress_pct", "status"], as_dict=True)
    log(f"  {cname}: {c}")
