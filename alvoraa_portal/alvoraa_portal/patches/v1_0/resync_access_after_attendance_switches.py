"""Re-run the module access sync once, so two moved modules follow their new owners.

On 26 Sep 2026 two modules changed owner in the feature registry:

    Alvoraa HR Core     opt-in `attendance_scoring`  ->  `attendance` (every plan)
    Alvoraa Late Rules  opt-in `late_rules`          ->  `payroll`

A site's access is only recalculated when `module_access.sync_site` runs, and
nothing runs it on a deploy. So without this patch a tenant synced earlier keeps
its old deny rows: HR turns late rules on in Organisation Settings and still
cannot open Attendance Deduction Rule, because it has no permissions at all.

When it runs, and when it does not:

- Only on a site that is in a deny state right now (`module_access` has recorded
  restrictions). A site never synced - a developer site, a freshly created test
  site, one whose test run released its rows - is left exactly as it is. Syncing
  those would impose deny-by-default on a site that never had it.
- Never on the control plane: `sync_site` refuses to run there.
- Safe to run twice: the sync is built from the site's own feature list, so a
  second run writes the same state.

A failure is logged ("module_access: resync after attendance switches failed")
and does not stop the migrate - the same trade tenant_api makes when a plan
change's sync fails. The operator can rerun it by hand:

    bench --site <site> execute alvoraa_portal.module_access.sync_site

Rollback: none needed. It only re-applies the site's current plan.
"""

import frappe


def should_resync():
	from alvoraa_portal import module_access as ma

	if frappe.conf.get("alvoraa_control_plane"):
		return False
	if not frappe.db.exists("DocType", ma.STATE_DOCTYPE):
		return False
	return bool(ma._recorded_restrictions())


def execute():
	if not should_resync():
		return
	from alvoraa_portal import module_access as ma

	try:
		ma.sync_site()
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="module_access: resync after attendance switches failed",
		                 message=frappe.get_traceback())
