"""ALV-149 (D5): tenant settings that still hold an old default say "Alvora HRMS".

Exact matches only - see brand_text.py for the list and the rule. Anything a
tenant typed is left alone, and printed as left alone. Surbhi reads the
dry-run (scripts/brand_text_dry_run.sh) for each server before this runs there.

Safe to run twice: the second run finds "Alvora HRMS" and nothing to change.
Never fails the migrate: a setting that cannot be changed goes to the Error Log.
"""

import frappe

from alvoraa_portal import brand_text


def execute():
	result = brand_text.apply()
	for line in result["changed"]:
		print(f"  changed: {line}")
	for setting in result["left_alone"]:
		print(f"  left alone, set by the tenant: {setting}")
	for setting in result["failed"]:
		print(f"  FAILED, see the Error Log 'brand_text: could not change a setting': {setting}")
	if not any(result.values()):
		print("  nothing to do")
	frappe.db.commit()
