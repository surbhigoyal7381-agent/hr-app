"""Deployment helpers that must run BEFORE `bench migrate`.

Renaming an installed Frappe app cannot be done by a patch: patches are discovered
per installed app, so a patch shipped in `alvoraa_goals` is invisible while the site
still believes the app is called `alvox_goals`. The rename has to be recorded in the
database first.

The hazard if it is not: after the image swap, the old package name no longer exists
on disk, so every doctype in that module fails `get_controller()` with ImportError,
and `frappe.model.sync.remove_orphan_doctypes` DELETES them as abandoned. Silent, and
destructive.

Run once per site, with the new image in place and BEFORE migrate:

    bench --site <site> execute alvoraa_goals.deploy_utils.premigrate_rename

Idempotent: a no-op on a site already renamed, and safe to re-run.
"""

import json

import frappe

# Every historical name -> the final one. Sites diverged: some were built from `dev`
# (grace_*), the servers from the rebrand branch (alvox_*).
APP_RENAMES = {
	"grace_goals": "alvoraa_goals",
	"alvox_goals": "alvoraa_goals",
	"grace_vendor_portal": "alvoraa_portal",
	"alvox_portal": "alvoraa_portal",
}

MODULE_RENAMES = {
	"Grace Goals": "Alvoraa Goals",
	"Alvox Goals": "Alvoraa Goals",
	"Grace Vendor Portal": "Alvoraa Portal",
	"Alvox Portal": "Alvoraa Portal",
}


def premigrate_rename():
	changed = []

	# 1. installed_apps. frappe.get_installed_apps() reads this global; it is the value
	#    that decides which apps exist, and it has been observed carrying duplicates.
	raw = frappe.db.get_value(
		"DefaultValue", {"defkey": "installed_apps", "parent": "__global"}, "defvalue"
	)
	apps = json.loads(raw) if raw else []
	renamed, seen = [], set()
	for app in apps:
		app = APP_RENAMES.get(app, app)
		if app not in seen:            # dedupe: duplicates here break get_installed_apps()
			seen.add(app)
			renamed.append(app)
	if renamed != apps:
		frappe.db.set_global("installed_apps", json.dumps(renamed))
		changed.append("installed_apps %s -> %s" % (apps, renamed))

	# 2. The Installed Application child table, kept in step with the global.
	for old, new in APP_RENAMES.items():
		rows = frappe.get_all("Installed Application", filters={"app_name": old}, pluck="name")
		for name in rows:
			frappe.db.set_value("Installed Application", name, "app_name", new,
			                    update_modified=False)
		if rows:
			changed.append("Installed Application %s -> %s (%d row(s))" % (old, new, len(rows)))

	# 3. Module Def.app_name. If a module still points at a package that is no longer on
	#    disk, every doctype inside it becomes an orphan candidate on the next migrate.
	for old, new in APP_RENAMES.items():
		mods = frappe.get_all("Module Def", filters={"app_name": old}, pluck="name")
		for name in mods:
			frappe.db.set_value("Module Def", name, "app_name", new, update_modified=False)
		if mods:
			changed.append("Module Def app_name %s -> %s (%s)" % (old, new, ", ".join(mods)))

	# 4. Module Def names themselves. The in-app patches also do this, but they cannot run
	#    until migrate, and migrate is exactly what must be made safe first.
	for old, new in MODULE_RENAMES.items():
		if frappe.db.exists("Module Def", old) and not frappe.db.exists("Module Def", new):
			frappe.rename_doc("Module Def", old, new, force=True)
			frappe.db.set_value("Module Def", new, "module_name", new, update_modified=False)
			changed.append("Module Def %s -> %s" % (old, new))
		for doctype in ("DocType", "Workspace", "Report", "Page"):
			if not frappe.db.table_exists(doctype):
				continue
			try:
				stale = frappe.get_all(doctype, filters={"module": old}, pluck="name")
			except Exception:
				continue
			for name in stale:
				frappe.db.set_value(doctype, name, "module", new, update_modified=False)
			if stale:
				changed.append("%s.module %s -> %s (%d)" % (doctype, old, new, len(stale)))

	frappe.db.commit()
	frappe.clear_cache()

	if changed:
		print("premigrate_rename: %d change(s) on %s" % (len(changed), frappe.local.site))
		for c in changed:
			print("   " + c)
	else:
		print("premigrate_rename: nothing to do on %s (already renamed)" % frappe.local.site)
	return changed
