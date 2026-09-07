"""
PP Jewellers demo - wipe everything Block 4 creates so seed_payroll.py can run clean.
Dev-only, brute force (table deletes, no cancel workflow). Never run on a live tenant with real payroll.
Run:  env/bin/python /tmp/ppj/reset_payroll.py --site <site>
"""
import os
import sys

sys.path.insert(0, os.environ.get("PPJ_SCRIPT_DIR", "/tmp/ppj"))
from ppj_common import *  # noqa: F401,F403

connect()
jes = frappe.get_all("Journal Entry", filters={"voucher_type": ["in", ["Journal Entry", "Bank Entry"]],
                                               "user_remark": ["like", "%Salary%"]}, pluck="name")
jes += frappe.get_all("Salary Slip", filters={"journal_entry": ["is", "set"]}, pluck="journal_entry")
jes = list({j for j in jes if j})
if jes:
    frappe.db.delete("GL Entry", {"voucher_no": ["in", jes]})
    frappe.db.delete("Payment Ledger Entry", {"voucher_no": ["in", jes]})
    frappe.db.delete("Journal Entry Account", {"parent": ["in", jes]})
    frappe.db.delete("Journal Entry", {"name": ["in", jes]})
    log(f"  Journal Entries: {len(jes)} deleted")
for dt in ["Salary Detail", "Salary Slip Leave", "Salary Slip Timesheet", "Salary Slip", "Payroll Employee Detail", "Payroll Entry",
           "Additional Salary", "Employee Incentive", "Salary Structure Assignment", "Salary Structure"]:
    if frappe.db.exists("DocType", dt):
        n = frappe.db.count(dt)
        frappe.db.delete(dt)
        log(f"  {dt}: {n} rows deleted")
frappe.db.sql("update `tabSalary Structure Assignment` set docstatus=0 where 1=0")
commit()
log("payroll data reset (components, accounts and settings kept)")
