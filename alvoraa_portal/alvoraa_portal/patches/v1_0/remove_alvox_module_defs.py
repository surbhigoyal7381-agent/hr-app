"""Remove the `Alvox` Module Defs left behind by the rebrand.

Both of our apps register TWO modules on every site - the live one and an
`Alvox` leftover from an intermediate rebrand step:

    Alvoraa Portal   +   Alvox Portal      (both app_name = alvoraa_portal)
    Alvoraa Goals    +   Alvox Goals       (both app_name = alvoraa_goals)

Measured on dev.alvoraa.co, alvoraa.co and demo.alvoraa.co - all three carry
them. MODULE_ACCESS_STRATEGY.md section 8 recorded this and said "worth deleting
before this work, not during"; it was never done.

Neither name appears in either app's modules.txt, so `bench migrate` does not
recreate them. They are database leftovers and nothing else.

Harmless but not free: they appear in every module list, in Module Profile block
lists, and in any support query about what a tenant can see - three places where
a name nobody recognises costs somebody time.

Safe by construction:

  * Never deletes a module unless its Alvoraa replacement exists. If the rename
    somehow half-ran on a site, deleting the only surviving record would take
    real doctypes with it.
  * Repoints anything still linked to the stale module first, then refuses to
    delete if anything still references it.
  * Idempotent. A site that has already been cleaned is a no-op.
"""

import frappe

STALE = {
	"Alvox Portal": "Alvoraa Portal",
	"Alvox Goals": "Alvoraa Goals",
}

# Doctypes carrying a `module` Link. Same list the rename patch used, because
# anything it had to repoint, this has to repoint too.
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
	"Workspace Sidebar",
	"Desktop Icon",
)


def _repoint(old, new):
	"""Move anything still pointing at the stale module onto the real one."""
	moved = 0
	for doctype in MODULE_LINKED:
		if not frappe.db.table_exists(doctype):
			continue
		try:
			stale = frappe.get_all(doctype, filters={"module": old}, pluck="name")
		except Exception:
			continue                      # doctype has no `module` field here
		for name in stale:
			frappe.db.set_value(doctype, name, "module", new, update_modified=False)
			moved += 1
	return moved


def _drop_block_module_rows(old):
	"""Remove Module Profile / User block rows naming the stale module.

	`Block Module.module` is a Link to Module Def, so deleting the Module Def
	while these rows exist leaves a dangling link. They are also redundant: the
	real module is blocked or allowed on its own merits, and deny-by-default
	means a module nobody sold is blocked whether or not a row says so.
	"""
	if not frappe.db.table_exists("Block Module"):
		return 0
	rows = frappe.get_all("Block Module", filters={"module": old}, pluck="name")
	for name in rows:
		frappe.db.delete("Block Module", {"name": name})
	return len(rows)


def _still_referenced(old):
	"""Anything left pointing at it. Refuse to delete if so."""
	for doctype in MODULE_LINKED + ("Block Module",):
		if not frappe.db.table_exists(doctype):
			continue
		try:
			if frappe.db.count(doctype, {"module": old}):
				return doctype
		except Exception:
			continue
	return None


def execute():
	removed, skipped = [], []

	for old, new in STALE.items():
		if not frappe.db.exists("Module Def", old):
			continue                      # already clean

		if not frappe.db.exists("Module Def", new):
			# The rename never completed on this site. Deleting the only record
			# for this module would orphan every doctype in it.
			skipped.append(f"{old}: {new} does not exist here")
			continue

		_repoint(old, new)
		_drop_block_module_rows(old)

		blocker = _still_referenced(old)
		if blocker:
			skipped.append(f"{old}: still referenced by {blocker}")
			continue

		frappe.delete_doc("Module Def", old, force=True, ignore_permissions=True)
		removed.append(old)

	if removed:
		frappe.db.commit()
		frappe.clear_cache()

	msg = f"removed: {removed or 'none'}"
	if skipped:
		msg += f" | skipped: {skipped}"
	print(msg)
	frappe.logger().info("alvoraa_portal: alvox module cleanup - " + msg)
