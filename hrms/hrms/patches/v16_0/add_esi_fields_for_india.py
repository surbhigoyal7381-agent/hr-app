import frappe

from hrms.overrides.company import run_regional_setup


def execute():
	"""ESI number on Employee, PF/ESI switches on Salary Structure Assignment, ESI component
	types and the ESI Deductions report roles, for sites that already have Indian companies."""
	if frappe.db.exists("Company", {"country": "India"}):
		run_regional_setup("India")
