"""The product's NAME in a tenant's own settings: "Alvora HRMS" (ALV-149, D3/D5).

Screens and code are fixed in the repository. Four things a person reads live in
each tenant's database instead, and no code change reaches them:

    Website Settings.app_name     the desk's tab title, the sign-in page and the
                                  name Frappe puts in its own emails
                                  (frappe/www/desk.py:61, www/login.py:53,
                                  email/email_body.py:712)
    System Settings.app_name      the fallback for the same three
    Website Settings brand_html, copyright, footer_powered, title_prefix
    Email Account names           Frappe sends the account's name as the From
                                  name (email/email_body.py:323-325). The
                                  address - noreply@alvoraa.co - does not change.

Plus one Frappe-branded door: "Frappe Support" in the desk's Help menu, hidden
on every tenant (Surbhi, 27 Sep 2026).

THE ONE RULE: a value is rewritten only when it is EXACTLY one of the defaults
below. A value a tenant typed is left alone - the same "ours or theirs" rule
brand.py uses for the logo. Replacing Frappe's own "Frappe"/"ERPNext" was
Surbhi's decision of 27 Sep 2026.

BEFORE IT RUNS ON A SERVER: scripts/brand_text_dry_run.sh prints, per site, what
this would change and what it would leave. It is read-only SQL and needs no
code on the server. Surbhi reads that list before the patch runs. A value that
changed after the dry-run no longer matches exactly, so it is left alone.

    bench --site <site> execute alvoraa_portal.brand_text.report   # same list, from here
"""

import frappe

PRODUCT_NAME = "Alvora HRMS"

# Website Settings.app_name and System Settings.app_name
APP_NAME_DEFAULTS = ("", "Frappe", "ERPNext", "Alvoraa", "Alvoraa HR", "Alvoraa HRMS")

# Website Settings text fields: the brand word is swapped, nothing else moves.
TEXT_FIELDS = ("brand_html", "copyright", "footer_powered", "title_prefix")
TEXT_DEFAULTS = ("Alvoraa", "Alvoraa HR", "Alvoraa HRMS", "© Alvoraa", "Powered by Alvoraa")

EMAIL_ACCOUNT_DEFAULTS = ("Alvoraa", "Alvoraa HR", "Alvoraa HRMS")

HELP_ITEMS_TO_HIDE = ("Frappe Support",)


def _respell(value):
	return value.replace("Alvoraa", "Alvora").replace("ALVORAA", "ALVORA")


def _is_control_plane():
	return bool(frappe.conf.get("alvoraa_control_plane"))


def plan():
	"""What would change on this site, and what would be left alone.

	Rows of {"setting", "current", "proposed", "action"}; action is "change",
	"leave" or "report". Reads only.
	"""
	rows = []

	for doctype in ("Website Settings", "System Settings"):
		current = frappe.db.get_single_value(doctype, "app_name", cache=False) or ""
		if current == PRODUCT_NAME:
			continue
		ours = current in APP_NAME_DEFAULTS
		rows.append({"setting": f"{doctype}.app_name", "current": current,
		             "proposed": PRODUCT_NAME if ours else current,
		             "action": "change" if ours else "leave"})

	for field in TEXT_FIELDS:
		current = frappe.db.get_single_value("Website Settings", field, cache=False) or ""
		if "Alvoraa" not in current and "ALVORAA" not in current:
			continue
		ours = current in TEXT_DEFAULTS           # exact: case and spaces count
		rows.append({"setting": f"Website Settings.{field}", "current": current,
		             "proposed": _respell(current) if ours else current,
		             "action": "change" if ours else "leave"})

	for name in frappe.get_all("Email Account", filters={"name": ["like", "%Alvoraa%"]},
	                           pluck="name"):
		ours = name in EMAIL_ACCOUNT_DEFAULTS and not _is_control_plane()
		new = _respell(name)
		if ours and frappe.db.exists("Email Account", new):
			ours = False
		rows.append({"setting": "Email Account (From name)", "current": name,
		             "proposed": new if ours else name,
		             "action": "change" if ours else "leave"})

	for item in frappe.get_all("Navbar Item",
	                           filters={"parent": "Navbar Settings", "parentfield": "help_dropdown",
	                                    "item_label": ["in", HELP_ITEMS_TO_HIDE], "hidden": 0},
	                           fields=["name", "item_label"]):
		rows.append({"setting": "Desk Help menu item", "current": item.item_label,
		             "proposed": "hidden", "action": "change"})

	unsent = frappe.db.count("Email Queue", {"status": "Not Sent"})
	if unsent:
		rows.append({"setting": "Emails queued, not sent (keep their old text)",
		             "current": str(unsent), "proposed": "", "action": "report"})
	return rows


def apply():
	"""Make the changes plan() lists. Safe to run twice. Never raises.

	Returns {"changed": [...], "left_alone": [...], "failed": [...]} with setting
	names and the old and new product-name values only - never personal data.
	"""
	result = {"changed": [], "left_alone": [], "failed": []}
	for row in plan():
		if row["action"] == "leave":
			result["left_alone"].append(row["setting"])
			continue
		if row["action"] != "change":
			continue
		try:
			_change(row)
			result["changed"].append(f'{row["setting"]}: {row["current"]!r} -> {row["proposed"]!r}')
		except Exception:
			frappe.log_error(title="brand_text: could not change a setting",
			                 message=f'{row["setting"]}\n{frappe.get_traceback()}')
			result["failed"].append(row["setting"])

	if result["changed"]:
		from frappe.website.utils import clear_website_cache

		frappe.clear_cache()
		clear_website_cache()

	frappe.logger("alvoraa.brand").info({"operation": "brand_text.apply",
	                                     "site": frappe.local.site, **result})
	return result


def _change(row):
	setting = row["setting"]
	if setting.endswith(".app_name") or setting.startswith("Website Settings."):
		doctype, field = setting.split(".", 1)
		frappe.db.set_single_value(doctype, field, row["proposed"])
	elif setting.startswith("Email Account"):
		frappe.rename_doc("Email Account", row["current"], row["proposed"], force=True)
	elif setting == "Desk Help menu item":
		frappe.db.set_value("Navbar Item",
		                    {"parent": "Navbar Settings", "parentfield": "help_dropdown",
		                     "item_label": row["current"]},
		                    "hidden", 1)
		frappe.clear_document_cache("Navbar Settings", "Navbar Settings")


def report():
	"""Print plan() for `bench --site <site> execute alvoraa_portal.brand_text.report`."""
	rows = plan()
	print(f"site: {frappe.local.site}")
	if not rows:
		print("  nothing to change")
	for row in rows:
		print(f'  [{row["action"]}] {row["setting"]}: {row["current"]!r} -> {row["proposed"]!r}')
	return rows


def after_install():
	"""A new tenant starts as Alvora HRMS. Never fails an install over a name."""
	try:
		result = apply()
		print(f"brand text: {len(result['changed'])} setting(s) set")
	except Exception:
		frappe.log_error(title="brand_text: after_install failed", message=frappe.get_traceback())
