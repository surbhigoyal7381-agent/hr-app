"""
PP Jewellers demo - Block 7: the policy library (build B5).

Department heads on the departments, 16 policies from data/policies.csv
(real text for the five that are opened in the demo), all published, and the
acknowledgements existing staff gave on joining. The Old Gold Exchange policy
carries unpublished changes for the "publish a new version" demo moment.

Idempotent per section.
"""
import os
import sys

sys.path.insert(0, os.environ.get("PPJ_SCRIPT_DIR", "/tmp/ppj"))
from ppj_common import *  # noqa: F401,F403

connect()
if not frappe.db.exists("DocType", "Policy Document"):
    raise SystemExit("Policy Document doctype not found: build B5 is not installed on this site")

# ── Department heads ────────────────────────────────────────────────────────
log("Department heads")
HEADS = {"Information Technology": "IT Manager", "Administration": "Admin Manager",
         "Central Vault & Inventory": "Central Vault & Inventory Manager",
         "Legal & Compliance": "Legal & Compliance Officer", "Management": "Owner & Managing Director"}
set_heads = 0
for d in frappe.get_all("Department", filters={"company": COMPANY, "is_group": 0}, fields=["name", "department_name"]):
    desig = HEADS.get(d.department_name, f"Head - {d.department_name}")
    head = frappe.db.get_value("Employee", {"designation": desig, "status": "Active", "company": COMPANY}, "name")
    if not head:
        head = frappe.db.get_value("Employee", {"department": d.name, "status": "Active", "company": COMPANY,
                                                "designation": ["like", "Head - %"]}, "name")
    if head and frappe.db.get_value("Department", d.name, "department_head") != head:
        frappe.db.set_value("Department", d.name, "department_head", head, update_modified=False)
        set_heads += 1
commit()
log(f"  {set_heads} department heads set")

# ── Policies ────────────────────────────────────────────────────────────────
log("Policies")
CONTENT = {
    "Attendance and Late Coming Policy": """
<h3>Store hours and punching</h3>
<p>Every store is open from 9:30 to 18:30, seven days a week. Everyone punches in and out on the ESSL device at the
store entrance. Head office staff punch at the head office device and are off on Sundays; store staff have one fixed
weekly off that is never a Sunday.</p>
<h3>The quarter-day rule</h3>
<p>Arriving more than an hour late, or leaving more than an hour early, is one violation. The week runs Monday to
Sunday. The first violation in a week is free. Every further violation costs a quarter of a day. Three quarters or
more in one week becomes a full day.</p>
<p>The days come first from Casual Leave. When no Casual Leave is left they are a loss of pay on that month's salary.
Every deduction is shown to the employee on the portal with the dates behind it, and the Store In-charge sees the
team's list each week.</p>
<h3>Exceptions</h3>
<p>A late arrival with the Store In-charge's prior approval (a bank visit, a customer delivery) is regularised through an
Attendance Request within the same week. Grades G5 and above are outside the rule.</p>""",
    "Leave Policy": """
<h3>Leave types</h3>
<p>Casual Leave 8 days, Earned Leave 15 days, Sick Leave 7 days in the year April to March. Compensatory Off is
earned for a full day worked on a festival day and must be used within 60 days. Leave Without Pay is for when the
paid types are used up.</p>
<h3>Applying</h3>
<p>Apply on the portal at least three working days ahead, except Sick Leave, which can be applied on return with a
doctor's note for three days or more. The Store In-charge approves store staff; the department head approves head
office staff. Nobody approves their own leave.</p>
<h3>Festival season</h3>
<p>From Navratri to Diwali the stores run full strength. Planned leave in this window needs the Head of Retail's
approval and is limited to one person per floor at a time.</p>""",
    "Category Incentive Policy": """
<h3>Who earns it</h3>
<p>Sales Executives, Senior Sales Executives and Floor Managers earn a monthly incentive on their own billed sales,
paid with the next salary. Store In-charges earn on the store's total.</p>
<h3>Slabs by category</h3>
<p>Gold: 0.20% of billed value above the monthly target, 0.35% above 120% of target. Diamond: 0.50% and 0.80%.
Silver: 0.30% flat above target. Platinum: 0.60% above target. Targets are set per quarter on the goal cascade and
are visible on the portal.</p>
<h3>Clawback</h3>
<p>A sale returned within 30 days is taken off the next month's incentive. Incentives are not earned on staff
purchases, exchanges of old gold, or sales billed to another store.</p>""",
    "Vault, Stock Handling and Security Policy": """
<h3>Custody</h3>
<p>Stock leaves the vault only against a signed issue slip in the custodian's register and is counted back in before
the vault is locked. Two people are present whenever the vault is open: the custodian and the Store In-charge or a
Floor Manager.</p>
<h3>On the floor</h3>
<p>Trays hold at most twelve pieces. One piece is out of the tray at a time with a customer. The tray is counted before
the customer leaves the counter. Any difference is reported to the Store In-charge at once, before the customer has
left the store.</p>
<h3>Closing</h3>
<p>Every store runs the closing checklist: floor count, vault count, CCTV check, alarm set. The Store In-charge signs
it; the Central Vault team reviews the counts each morning.</p>""",
    "Performance Appraisal Policy": """
<h3>Quarterly cycle</h3>
<p>Everyone is appraised every quarter. The score has three parts: targets achieved (50%), the manager's feedback
against our values and the customer handling and teamwork criteria (30%), and attendance regularity (20%).</p>
<h3>How attendance counts</h3>
<p>Attendance is scored from the attendance records for the quarter: days present against days scheduled, and days
on time against days present. Each day deducted under the late-coming rule takes a quarter point off. Approved paid
leave does not lower the score.</p>
<h3>Calibration and outcomes</h3>
<p>Store In-charges rate their teams; the Head of Retail calibrates across stores; HR runs the sign-off. Ratings feed
the annual increment in April and the incentive slab for the next quarter.</p>""",
}
RULES = {"All Employees": [{"access_type": "All Employees"}],
         "Reporting Managers": [{"access_type": "Reporting Managers"}],
         "Department Only": [{"access_type": "Department Only"}],
         "HR Only": [{"access_type": "HR Only"}],
         "Top Leadership": [{"access_type": "Top Leadership"}]}
made = 0
frappe.set_user("Administrator")
for r in read_csv("policies.csv"):
    if frappe.db.exists("Policy Document", {"title": r["title"]}):
        continue
    version_label = r.get("version") or "1.0"
    doc = frappe.get_doc({"doctype": "Policy Document", "title": r["title"], "owner_department": dept(r["owner_department"]),
                          "category": r["category"], "company": COMPANY, "status": "Draft",
                          "effective_from": r.get("effective_from") or "2026-04-01",
                          "review_due": "2027-03-31", "summary": r["summary"],
                          "content": CONTENT.get(r["title"], f"<p>{r['summary']}</p>"),
                          "acknowledge_on_joining": 1 if r["acknowledge_on_joining"] == "Yes" else 0,
                          "acknowledge_on_new_version": 1 if r["acknowledge_on_joining"] == "Yes" else 0,
                          "pinned": 1 if r["title"] in ("Attendance and Late Coming Policy", "Category Incentive Policy") else 0,
                          "read_access": RULES.get(r["visibility"], RULES["All Employees"])})
    doc.flags.ignore_permissions = True
    doc.insert()
    doc.publish(f"Imported as version {version_label}.")
    made += 1
commit()
log(f"  {made} policies published, {frappe.db.count('Policy Document', {'status': 'Published'})} in total")

# The Purchase head has started a new version of the old-gold policy (demo moment)
old_gold = frappe.db.get_value("Policy Document", {"title": "Old Gold Exchange and Valuation Policy"}, "name")
if old_gold and not frappe.db.get_value("Policy Document", old_gold, "has_unpublished_changes"):
    doc = frappe.get_doc("Policy Document", old_gold)
    doc.content = (doc.content or "") + ("<h3>Deduction norm (draft change)</h3><p>The making-charge deduction on exchanged "
                                         "old gold is 8% of the assessed value, down from 10%, for hallmarked pieces bought "
                                         "from any PP Jewellers store.</p>")
    doc.flags.ignore_permissions = True
    doc.save()
    commit()
    log("  Old Gold Exchange and Valuation Policy: unpublished changes saved (v1.1 draft)")

# ── Acknowledgements ────────────────────────────────────────────────────────
log("Acknowledgements on joining")
need = frappe.get_all("Policy Document", filters={"status": "Published", "acknowledge_on_joining": 1},
                      fields=["name", "current_version", "effective_from"])
have = {(a.policy_document, a.version, a.employee) for a in frappe.get_all(
    "Policy Acknowledgement", fields=["policy_document", "version", "employee"])}
added = 0
for e in frappe.get_all("Employee", filters={"company": COMPANY, "status": "Active", "date_of_joining": ["<", "2026-08-01"]},
                        fields=["name", "user_id", "date_of_joining"]):
    for p in need:
        if (p.name, p.current_version, e.name) in have:
            continue
        when = max(getdate(e.date_of_joining), getdate(p.effective_from or "2026-04-01"))
        frappe.get_doc({"doctype": "Policy Acknowledgement", "policy_document": p.name, "version": p.current_version,
                        "employee": e.name, "user": e.user_id, "acknowledged_on": f"{when} 10:00:00",
                        "source": "Onboarding"}).insert(ignore_permissions=True)
        added += 1
        if added % 500 == 0:
            commit()
commit()
log(f"  {added} acknowledgements added ({frappe.db.count('Policy Acknowledgement')} in total); "
    f"September joiners are still pending")

log("Block 7 done")
counts("Policy Document", "Policy Acknowledgement")
