import frappe
import subprocess

def execute():
    print("Installing grace_goals app...")
    # This script is called from outside via bench execute
    # The app must already be pip-installed before calling this
    frappe.db.commit()
    print("Done. Run: bench --site hrms.localhost install-app grace_goals")
