"""
PP Jewellers demo - Block 4: payroll.

Payroll Settings, Payroll Period, Income Tax Slab, accounts, 17 Salary
Components (ESI included as formula components; the esi_applicable switch on
Salary Structure Assignment is build B2), 5 Salary Structures, 400 Salary
Structure Assignments, Employee Incentives for July sales, Payroll Entries for
July and August 2026 with slips created and submitted.

Runs slips in-process (no background worker needed). Idempotent.
"""
import os
import sys

sys.path.insert(0, os.environ.get("PPJ_SCRIPT_DIR", "/tmp/ppj"))
from ppj_common import *  # noqa: F401,F403
from frappe.utils import getdate

connect()

# ── Payroll Settings ────────────────────────────────────────────────────────
log("Payroll Settings")
ps = frappe.get_single("Payroll Settings")
ps.payroll_based_on = "Attendance"
ps.consider_unmarked_attendance_as = "Absent"
ps.include_holidays_in_total_working_days = 1
ps.consider_marked_attendance_on_holidays = 1
ps.daily_wages_fraction_for_half_day = 0.5
ps.email_salary_slip_to_employee = 0
ps.encrypt_salary_slips_in_emails = 1
ps.password_policy = "{date_of_birth}"
ps.show_leave_balances_in_salary_slip = 1
ps.save(ignore_permissions=True)
commit()

# ── Payroll Period and Income Tax Slab ──────────────────────────────────────
log("Payroll Period and Income Tax Slab")
if not frappe.db.exists("Payroll Period", {"company": COMPANY, "start_date": FY_START}):
    pp = frappe.get_doc({"doctype": "Payroll Period", "name": "FY 2026-27", "__newname": "FY 2026-27",
                         "company": COMPANY, "start_date": FY_START, "end_date": FY_END})
    pp.insert(ignore_permissions=True)
    log(f"  [created] Payroll Period {pp.name}")
SLAB_NAME = "India New Regime FY 2026-27"
if not frappe.db.exists("Income Tax Slab", SLAB_NAME):
    # New-regime slabs as announced in Budget 2025 - VERIFY before the demo.
    slab = frappe.get_doc({
        "doctype": "Income Tax Slab", "name": SLAB_NAME, "__newname": SLAB_NAME,
        "effective_from": FY_START, "company": COMPANY, "currency": "INR",
        "standard_tax_exemption_amount": 75000, "allow_tax_exemption": 0,
        "slabs": [
            {"from_amount": 0, "to_amount": 400000, "percent_deduction": 0},
            {"from_amount": 400000, "to_amount": 800000, "percent_deduction": 5},
            {"from_amount": 800000, "to_amount": 1200000, "percent_deduction": 10},
            {"from_amount": 1200000, "to_amount": 1600000, "percent_deduction": 15},
            {"from_amount": 1600000, "to_amount": 2000000, "percent_deduction": 20},
            {"from_amount": 2000000, "to_amount": 2400000, "percent_deduction": 25},
            {"from_amount": 2400000, "to_amount": 0, "percent_deduction": 30},
        ],
        "other_taxes_and_charges": [{"description": "Health and Education Cess", "percent": 4}],
    })
    slab.flags.ignore_permissions = True
    slab.insert()
    slab.submit()
    log(f"  [created] Income Tax Slab: {slab.name}")
SLAB_NAME = frappe.db.get_value("Income Tax Slab", {"effective_from": FY_START, "company": COMPANY, "docstatus": 1}, "name")
commit()

# ── Accounts ────────────────────────────────────────────────────────────────
log("Accounts")


def account(name, parent_name, root_type=None, account_type=None):
    existing = frappe.db.get_value("Account", {"account_name": name, "company": COMPANY}, "name")
    if existing:
        return existing
    parent = frappe.db.get_value("Account", {"account_name": parent_name, "company": COMPANY, "is_group": 1}, "name")
    if not parent:
        raise Exception(f"Parent account {parent_name} not found for {COMPANY}")
    acc = frappe.get_doc({"doctype": "Account", "account_name": name, "parent_account": parent,
                          "company": COMPANY, "account_type": account_type})
    acc.insert(ignore_permissions=True)
    log(f"  [created] Account: {acc.name}")
    return acc.name


SALARY_ACC = frappe.db.get_value("Account", {"account_name": "Salary", "company": COMPANY}, "name") \
    or account("Salary", "Indirect Expenses")
PAYABLE_ACC = frappe.db.get_value("Account", {"account_name": "Payroll Payable", "company": COMPANY}, "name") \
    or account("Payroll Payable", "Current Liabilities", account_type="Payable")
PF_ACC = account("PF Payable", "Duties and Taxes")
ESI_ACC = account("ESI Payable", "Duties and Taxes")
PT_ACC = account("Professional Tax Payable", "Duties and Taxes")
IT_ACC = account("TDS on Salary Payable", "Duties and Taxes")
if frappe.db.get_value("Account", PAYABLE_ACC, "account_type") != "Payable":
    frappe.db.set_value("Account", PAYABLE_ACC, "account_type", "Payable")     # Payroll Entry insists on it
frappe.db.set_value("Company", COMPANY, "default_payroll_payable_account", PAYABLE_ACC)
COST_CENTER = frappe.db.get_value("Company", COMPANY, "cost_center") \
    or frappe.db.get_value("Cost Center", {"company": COMPANY, "is_group": 0}, "name")
commit()

# ── Salary Components ───────────────────────────────────────────────────────
log("Salary Components")
# (name, abbr, type, dict)
COMPONENTS = [
    ("Basic", "B", "Earning", {"formula": "base * 0.50", "depends_on_payment_days": 1, "is_tax_applicable": 1}),
    ("House Rent Allowance", "HRA", "Earning", {"formula": "base * 0.20", "depends_on_payment_days": 1, "is_tax_applicable": 1}),
    ("Conveyance Allowance", "CA", "Earning", {"amount": 1600, "depends_on_payment_days": 1, "is_tax_applicable": 1}),
    ("Special Allowance", "SA", "Earning", {"formula": "base - base * 0.50 - base * 0.20 - 1600", "depends_on_payment_days": 1, "is_tax_applicable": 1}),
    ("Gold Incentive", "INC_G", "Earning", {"amount": 0, "is_tax_applicable": 1, "remove_if_zero_valued": 1}),
    ("Diamond Incentive", "INC_D", "Earning", {"amount": 0, "is_tax_applicable": 1, "remove_if_zero_valued": 1}),
    ("Silver & Fashion Incentive", "INC_S", "Earning", {"amount": 0, "is_tax_applicable": 1, "remove_if_zero_valued": 1}),
    ("Platinum & Gemstone Incentive", "INC_P", "Earning", {"amount": 0, "is_tax_applicable": 1, "remove_if_zero_valued": 1}),
    ("Store Performance Incentive", "INC_ST", "Earning", {"amount": 0, "is_tax_applicable": 1, "remove_if_zero_valued": 1}),
    ("Festival Working Allowance", "FWA", "Earning", {"amount": 0, "is_tax_applicable": 1, "remove_if_zero_valued": 1}),
    ("Provident Fund", "PF", "Deduction", {"condition": "pf_applicable", "formula": "min(B, 15000) * 0.12", "exempted_from_income_tax": 1}),
    ("Employee State Insurance", "ESI", "Deduction", {"condition": "esi_applicable", "formula": "gross_pay * 0.0075", "remove_if_zero_valued": 1}),
    ("Professional Tax", "PT", "Deduction", {"amount": 0, "exempted_from_income_tax": 1}),
    ("Late Coming Deduction", "LCD", "Deduction", {"amount": 0, "remove_if_zero_valued": 1}),
    ("Income Tax", "IT", "Deduction", {"variable_based_on_taxable_salary": 1, "is_income_tax_component": 1, "remove_if_zero_valued": 1}),
    ("Employer PF Contribution", "EPF_ER", "Employer Contribution", {"condition": "pf_applicable", "formula": "min(B, 15000) * 0.12"}),
    ("Employer ESI Contribution", "ESI_ER", "Employer Contribution", {"condition": "esi_applicable", "formula": "gross_pay * 0.0325", "remove_if_zero_valued": 1}),
]
# Statutory rates (PF 12% on basic capped at 15,000; ESI 0.75% / 3.25% up to 21,000 gross) - applied for the demo; confirm before real payroll.
ACCOUNT_FOR = {"PF": PF_ACC, "ESI": ESI_ACC, "PT": PT_ACC, "IT": IT_ACC, "EPF_ER": PF_ACC, "ESI_ER": ESI_ACC}
UPDATABLE = ["formula", "condition", "amount", "depends_on_payment_days", "is_tax_applicable", "exempted_from_income_tax",
             "remove_if_zero_valued", "variable_based_on_taxable_salary", "is_income_tax_component"]
for name, abbr, ctype, vals in COMPONENTS:
    acc = ACCOUNT_FOR.get(abbr, SALARY_ACC if ctype != "Deduction" else PAYABLE_ACC)
    if frappe.db.exists("Salary Component", name):
        # Frappe HR's India setup pre-creates Basic, HRA, PF and PT without formulas; apply the PPJ rules to them
        sc = frappe.get_doc("Salary Component", name)
        sc.salary_component_abbr = abbr
        sc.type = ctype
        sc.amount_based_on_formula = 1 if vals.get("formula") else 0
        for f in UPDATABLE:
            sc.set(f, vals.get(f, 0 if f != "condition" and f != "formula" else ""))
        if not any(a.company == COMPANY for a in sc.accounts):
            sc.append("accounts", {"company": COMPANY, "account": acc})
        changed = True
    else:
        sc = frappe.get_doc({"doctype": "Salary Component", "salary_component": name, "salary_component_abbr": abbr,
                             "type": ctype, "amount_based_on_formula": 1 if vals.get("formula") else 0, **vals})
        sc.append("accounts", {"company": COMPANY, "account": acc})
        changed = False
    if abbr in ("PF", "EPF_ER") and frappe.get_meta("Salary Component").has_field("component_type"):
        sc.component_type = "Provident Fund"
    if abbr == "PT" and frappe.get_meta("Salary Component").has_field("component_type"):
        sc.component_type = "Professional Tax"
    if abbr in ("ESI", "ESI_ER") and frappe.get_meta("Salary Component").has_field("component_type"):
        sc.component_type = "ESI" if abbr == "ESI" else "Employer ESI"     # build B2
    sc.flags.ignore_permissions = True
    if changed:
        sc.save()
        log(f"  [updated] Salary Component: {name}")
    else:
        sc.insert()
        log(f"  [created] Salary Component: {name}")
commit()

# ── Salary Structures ───────────────────────────────────────────────────────
log("Salary Structures")
EARN = ["Basic", "House Rent Allowance", "Conveyance Allowance", "Special Allowance", "Gold Incentive",
        "Diamond Incentive", "Silver & Fashion Incentive", "Platinum & Gemstone Incentive",
        "Store Performance Incentive", "Festival Working Allowance"]
DED = ["Provident Fund", "Employee State Insurance", "Professional Tax", "Late Coming Deduction", "Income Tax"]
EC = ["Employer PF Contribution", "Employer ESI Contribution"]
STRUCTURES = {"PPJ-G1": ["G1 Support"], "PPJ-G2": ["G2 Executive"], "PPJ-G3": ["G3 Senior Executive"],
              "PPJ-G4": ["G4 Manager"], "PPJ-G5": ["G5 Head", "G6 Leadership"]}
comp_meta = {c.name: c for c in frappe.get_all("Salary Component", fields=["name", "salary_component_abbr", "type",
                                                                            "amount", "formula", "condition",
                                                                            "amount_based_on_formula",
                                                                            "depends_on_payment_days", "is_tax_applicable",
                                                                            "variable_based_on_taxable_salary",
                                                                            "remove_if_zero_valued",
                                                                            "exempted_from_income_tax"])}


def row_for(name):
    c = comp_meta[name]
    return {"salary_component": name, "abbr": c.salary_component_abbr, "amount": c.amount, "formula": c.formula,
            "condition": c.condition, "amount_based_on_formula": c.amount_based_on_formula,
            "depends_on_payment_days": c.depends_on_payment_days, "is_tax_applicable": c.is_tax_applicable,
            "variable_based_on_taxable_salary": c.variable_based_on_taxable_salary,
            "exempted_from_income_tax": c.exempted_from_income_tax}


for sname, grades in STRUCTURES.items():
    if frappe.db.exists("Salary Structure", sname):
        continue
    ss = frappe.get_doc({"doctype": "Salary Structure", "__newname": sname, "name": sname, "company": COMPANY,
                         "currency": "INR", "payroll_frequency": "Monthly", "is_active": "Yes",
                         "earnings": [row_for(n) for n in EARN], "deductions": [row_for(n) for n in DED],
                         "employer_contributions": [row_for(n) for n in EC]})
    ss.flags.ignore_permissions = True
    ss.insert()
    ss.submit()
    for g in grades:
        frappe.db.set_value("Employee Grade", g, "default_salary_structure", sname)
    log(f"  [created] Salary Structure: {sname}")
commit()

# ── Salary Structure Assignments ────────────────────────────────────────────
log("Salary Structure Assignments")
GRADE_TO_STRUCTURE = {g: s for s, gs in STRUCTURES.items() for g in gs}
ctc = {r["employee_id"]: flt(r["monthly_ctc"]) for r in read_csv("employees.csv")}
made = 0
for e in employees():
    if frappe.db.exists("Salary Structure Assignment", {"employee": e.name, "docstatus": 1}):
        continue
    base = ctc.get(e.name) or flt(frappe.db.get_value("Employee", e.name, "ctc")) / 12   # joiners outside the CSV
    from_date = FY_START if e.name in ctc else str(e.date_of_joining)
    ssa = frappe.get_doc({"doctype": "Salary Structure Assignment", "employee": e.name,
                          "salary_structure": GRADE_TO_STRUCTURE[e.employee_grade], "company": COMPANY,
                          "currency": "INR", "from_date": from_date, "base": base,
                          "income_tax_slab": SLAB_NAME, "payroll_payable_account": PAYABLE_ACC})
    if ssa.meta.has_field("esi_applicable"):      # build B2 switches (the India hook defaults them the same way)
        ssa.esi_applicable = 1 if base <= 21000 else 0
        ssa.pf_applicable = 1
    ssa.flags.ignore_permissions = True
    ssa.insert()
    ssa.submit()
    made += 1
    if made % 100 == 0:
        commit()
        log(f"  {made} assignments")
commit()
log(f"  {made} assignments created")

# ── Late-coming rule (build B1): the loss-of-pay lines must exist before the slips
RULE = "PPJ Late Coming Rule"
if frappe.db.exists("Attendance Deduction Rule", RULE) and not frappe.db.exists("Attendance Deduction", {"rule": RULE, "docstatus": 1}):
    log("Attendance Deduction Rule run (build B1)")
    from hrms.alvoraa_late_rules.late_rules import run_for_range
    frappe.set_user("Administrator")
    result = run_for_range(RULE, "2026-07-01", "2026-09-06")
    commit()
    log(f"  rule run: {result}; Attendance Deductions: {frappe.db.count('Attendance Deduction', {'docstatus': 1})} "
        f"(expected 212 from data/expected_deductions.csv), with loss of pay "
        f"{frappe.db.count('Attendance Deduction', {'docstatus': 1, 'lwp_days': ['>', 0]})}")

# ── Employee Incentives for July sales (paid with August salary) ───────────
log("Employee Incentives (July sales)")
PAY_DATE = "2026-08-31"
CAT_COMPONENT = {"Gold": "Gold Incentive", "Diamond": "Diamond Incentive", "Silver & Fashion": "Silver & Fashion Incentive"}
JULY_ATT = {}
Q2_STORE = {}
for r in read_csv("sales_targets.csv"):
    if r["period"].startswith("Q2"):
        Q2_STORE[r["branch"]] = Q2_STORE.get(r["branch"], 0) + flt(r["target_inr"])
        if r["actual_inr"] and r["category"] == "Gold":
            JULY_ATT[r["branch"]] = flt(r["actual_inr"]) / (flt(r["target_inr"]) / 3)


def rate(att, slabs):
    for lo, rt in slabs:
        if att >= lo:
            return rt
    return 0


incentives = []   # (employee, component, amount)
for r in read_csv("sales_actuals_july.csv"):
    if flt(r["incentive_inr"]) > 0:
        incentives.append((r["employee_id"], r["incentive_component"], flt(r["incentive_inr"])))
FLOOR_SHARE = {"Floor Manager - Gold": 0.60, "Floor Manager - Diamond": 0.32, "Floor Manager - Silver & Fashion": 0.08}
for e in employees():
    if str(e.date_of_joining) > PAY_DATE:     # September joiners earn nothing for July
        continue
    att = JULY_ATT.get(e.branch, 0)
    store_month = Q2_STORE.get(e.branch, 0) / 3 * att
    if e.designation in FLOOR_SHARE:
        amt = store_month * FLOOR_SHARE[e.designation] * rate(att, [(1.2, 0.0020), (1.0, 0.0015), (0.9, 0.0010)])
        comp = {"Floor Manager - Gold": "Gold Incentive", "Floor Manager - Diamond": "Diamond Incentive",
                "Floor Manager - Silver & Fashion": "Silver & Fashion Incentive"}[e.designation]
    elif e.designation in ("Store In-charge", "Assistant Store Manager"):
        amt = store_month * rate(att, [(1.2, 0.0010), (1.0, 0.0008), (0.9, 0.0005)])
        comp = "Store Performance Incentive"
    elif e.designation in ("Cashier", "Customer Relationship Executive"):
        amt = rate(att, [(1.2, 4000), (1.0, 2500), (0.9, 1500)])
        comp = "Store Performance Incentive"
    else:
        continue
    amt = round(amt / 100) * 100
    if amt > 0:
        incentives.append((e.name, comp, amt))

made = 0
for emp, comp, amt in incentives:
    if frappe.db.exists("Employee Incentive", {"employee": emp, "salary_component": comp, "payroll_date": PAY_DATE, "docstatus": 1}):
        continue
    inc = frappe.get_doc({"doctype": "Employee Incentive", "employee": emp, "incentive_amount": amt,
                          "payroll_date": PAY_DATE, "salary_component": comp, "company": COMPANY, "currency": "INR"})
    inc.flags.ignore_permissions = True
    inc.insert()
    inc.submit()          # creates and submits the Additional Salary
    made += 1
    if made % 50 == 0:
        commit()
commit()
log(f"  {made} incentives created ({len(incentives)} in plan)")

# ── Payroll Entries: July and August 2026 ───────────────────────────────────
from hrms.payroll.doctype.payroll_entry.payroll_entry import (
    create_salary_slips_for_employees, submit_salary_slips_for_employees)


def run_payroll(year, month):
    start, end = month_range(year, month)
    start, end = start.isoformat(), end.isoformat()
    name = frappe.db.get_value("Payroll Entry", {"company": COMPANY, "start_date": start, "end_date": end,
                                                 "docstatus": ["!=", 2]}, "name")
    if name:
        pe = frappe.get_doc("Payroll Entry", name)
    else:
        pe = frappe.get_doc({"doctype": "Payroll Entry", "company": COMPANY, "posting_date": end,
                             "payroll_frequency": "Monthly", "start_date": start, "end_date": end,
                             "currency": "INR", "exchange_rate": 1, "cost_center": COST_CENTER,
                             "payroll_payable_account": PAYABLE_ACC, "validate_attendance": 1})
        pe.flags.ignore_permissions = True
        pe.insert()
        unmarked = pe.fill_employee_details() or []
        if unmarked:
            log(f"  WARNING: {len(unmarked)} employees have unmarked attendance in {start}..{end}")
        pe.save()
        pe.submit()
        log(f"  [created] Payroll Entry {pe.name}: {pe.number_of_employees} employees")
    if not pe.salary_slips_created:
        args = frappe._dict({"salary_slip_based_on_timesheet": 0, "payroll_frequency": "Monthly",
                             "start_date": start, "end_date": end, "company": COMPANY, "posting_date": end,
                             "deduct_tax_for_unsubmitted_tax_exemption_proof": 0, "payroll_entry": pe.name,
                             "exchange_rate": 1, "currency": "INR"})
        create_salary_slips_for_employees([d.employee for d in pe.employees], args, publish_progress=False)
        commit()
        pe.reload()
        log(f"  slips created for {pe.name}")
    if not pe.salary_slips_submitted:
        slips = pe.get_sal_slip_list(ss_status=0)
        submit_salary_slips_for_employees(pe, slips, publish_progress=False)
        commit()
        pe.reload()
        log(f"  slips submitted for {pe.name}: {frappe.db.count('Salary Slip', {'payroll_entry': pe.name, 'docstatus': 1})}")


log("Payroll Entries")
run_payroll(2026, 7)
run_payroll(2026, 8)

log("Block 4 done")
counts("Salary Component", "Salary Structure", "Salary Structure Assignment", "Employee Incentive",
       "Additional Salary", "Payroll Entry", "Salary Slip")
for emp in ("PPJ-0054", "PPJ-0058"):
    slip = frappe.db.get_value("Salary Slip", {"employee": emp, "start_date": "2026-08-01", "docstatus": 1},
                               ["name", "payment_days", "total_working_days", "gross_pay", "net_pay"], as_dict=True)
    log(f"  {emp} August slip: {slip}")
    if slip:
        for d in frappe.get_all("Salary Detail", filters={"parent": slip.name}, fields=["salary_component", "amount"]):
            if d.amount:
                log(f"      {d.salary_component}: {d.amount}")
