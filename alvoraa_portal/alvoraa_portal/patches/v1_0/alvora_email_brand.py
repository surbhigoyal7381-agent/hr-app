"""ALV-174: sites that already exist get the same email fix a new tenant gets
from `after_install` - the ERPNext footer off, the Alvora footer and lockup on.

Safe to run twice: the second run finds its own footer and logo already there
and writes the same values back. Never fails the migrate: a setting that
cannot be changed goes to the Error Log, same as brand.py and brand_text.py's
patches. The control plane is a site too, and gets it like any other - see
email_brand.py's module docstring for the one thing this patch deliberately
does NOT touch (the control plane's Reply-To).
"""

import frappe

from alvoraa_portal import email_brand


def execute():
	result = email_brand.apply()

	if result["changed"]:
		for line in sorted(result["changed"]):
			print(f"  changed: {line}")
	if result["left_alone"]:
		for setting in sorted(result["left_alone"]):
			print(f"  left alone, set by the tenant: {setting}")
	if result["failed"]:
		for setting in sorted(result["failed"]):
			print(f"  FAILED, see the Error Log 'email_brand: could not change a setting': {setting}")
	if not any(result.values()):
		print("  nothing to do")

	frappe.db.commit()
