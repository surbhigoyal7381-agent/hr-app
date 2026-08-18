import frappe

OLD = "Grace Vendor Portal"
NEW = "Alvoraa Portal"

# The module's workspace is renamed alongside it - its name is user-visible in the
# Desk sidebar and its `module` Link must follow the module.
OLD_WORKSPACE = "Grace Vendor Portal"
NEW_WORKSPACE = "Alvoraa Portal"

MODULE_LINKED = (
	"DocType",
	"Workspace",
	"Report",
	"Page",
	"Print Format",
	"Web Form",
	"Dashboard Chart",
	"Notification",
	"Server Script",
	"Client Script",
)


def execute():
	"""Rename the module Grace Vendor Portal -> Alvoraa Portal, and its workspace.

	Idempotent: a no-op on a site that has already been renamed, and safe to re-run.
	Deliberately does not touch the app name - that is a separate, later phase.
	"""
	if frappe.db.exists("Module Def", OLD) and not frappe.db.exists("Module Def", NEW):
		frappe.rename_doc("Module Def", OLD, NEW, force=True, ignore_permissions=True)

	if frappe.db.exists("Module Def", NEW):
		frappe.db.set_value("Module Def", NEW, "module_name", NEW, update_modified=False)

	for doctype in MODULE_LINKED:
		if not frappe.db.table_exists(doctype):
			continue
		try:
			stale = frappe.get_all(doctype, filters={"module": OLD}, pluck="name")
		except Exception:
			continue
		for name in stale:
			frappe.db.set_value(doctype, name, "module", NEW, update_modified=False)

	# Workspace record rename. Done after the module repoint so the record is valid
	# at every step.
	if frappe.db.exists("Workspace", OLD_WORKSPACE) and not frappe.db.exists("Workspace", NEW_WORKSPACE):
		frappe.rename_doc("Workspace", OLD_WORKSPACE, NEW_WORKSPACE, force=True, ignore_permissions=True)

	if frappe.db.exists("Workspace", NEW_WORKSPACE):
		ws = frappe.get_doc("Workspace", NEW_WORKSPACE)
		ws.label = NEW_WORKSPACE
		ws.title = NEW_WORKSPACE
		ws.module = NEW
		ws.save(ignore_permissions=True)

	frappe.clear_cache()
