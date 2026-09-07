"""
PP Jewellers demo - wipe everything Block 8 creates so seed_performance.py can run clean.
Dev-only. Run:  env/bin/python /tmp/ppj/reset_performance.py --site <site>
"""
import os
import sys

sys.path.insert(0, os.environ.get("PPJ_SCRIPT_DIR", "/tmp/ppj"))
from ppj_common import *  # noqa: F401,F403

connect()
# Employee Feedback Rating is shared with Appraisal Template: only the rows under appraisals and feedback go.
if frappe.db.exists("DocType", "Employee Feedback Rating"):
    frappe.db.delete("Employee Feedback Rating", {"parenttype": ["in", ["Appraisal", "Employee Performance Feedback"]]})
for dt in ["Alvoraa Appraisal Extension", "Appraisal Action Item", "Employee Performance Feedback",
           "Appraisal Goal", "Appraisal KRA", "Appraisal", "Appraisee", "Upward Feedback", "KPI Progress Log",
           "KPI Additional Reviewer", "KPI", "Goal Evidence", "Goal Progress Update", "Goal Progress Audit Log",
           "Goal Check In", "Cascade Alignment Report", "Individual Goal", "Goal Cascade Version", "Goal Cascade",
           "Alvoraa Cycle Config", "Appraisal Cycle"]:
    if frappe.db.exists("DocType", dt):
        n = frappe.db.count(dt)
        frappe.db.delete(dt)
        log(f"  {dt}: {n} rows deleted")
commit()
log("performance data reset")
