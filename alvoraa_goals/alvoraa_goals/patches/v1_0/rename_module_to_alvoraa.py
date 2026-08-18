import frappe

OLD = "Grace Goals"
NEW = "Alvoraa Goals"

# Metadata doctypes that carry a `module` Link. rename_doc updates Link references,
# but any row left pointing at the old module makes its records unloadable, so each
# is repointed explicitly afterwards.
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
	"""Rename the module Grace Goals -> Alvoraa Goals.

	Idempotent: a no-op on a site that has already been renamed, and safe to re-run.
	Deliberately does not touch the app name - that is a separate, later phase.
	"""
	if frappe.db.exists("Module Def", OLD) and not frappe.db.exists("Module Def", NEW):
		frappe.rename_doc("Module Def", OLD, NEW, force=True)

	if frappe.db.exists("Module Def", NEW):
		# `module_name` is the label and is not updated by the rename itself.
		frappe.db.set_value("Module Def", NEW, "module_name", NEW, update_modified=False)

	for doctype in MODULE_LINKED:
		if not frappe.db.table_exists(doctype):
			continue
		try:
			stale = frappe.get_all(doctype, filters={"module": OLD}, pluck="name")
		except Exception:
			# Doctype exists but has no `module` column on this version - nothing to do.
			continue
		for name in stale:
			frappe.db.set_value(doctype, name, "module", NEW, update_modified=False)

	frappe.clear_cache()
