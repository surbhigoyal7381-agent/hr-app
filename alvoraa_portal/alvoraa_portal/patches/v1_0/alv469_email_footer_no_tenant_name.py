"""ALV-469: the email footer is only "Powered by AllAboutHR".

Changes ONE thing: the footer text, and only where the current footer is one
this product wrote (its last line is "Powered by AllAboutHR") and it still has
another line above it. It does not call email_brand.apply(), which would also
reset the standard-footer switch and put back logos somebody removed on
purpose. An empty or hand-written footer is left alone.
"""

import frappe

from alvoraa_portal import email_brand


def execute():
	current = frappe.db.get_single_value("System Settings", "email_footer_address", cache=False) or ""
	lines = current.splitlines()
	if len(lines) > 1 and lines[-1].strip() == email_brand.FOOTER_LINE:
		email_brand._save_system_setting("email_footer_address", email_brand.FOOTER_LINE)
		frappe.clear_cache()
		print("  email footer: tenant name line removed")
	else:
		print("  email footer: nothing to change")
	frappe.db.commit()
