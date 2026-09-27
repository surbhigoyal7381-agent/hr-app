"""ALV-152: the desk's "Switch to Employee Portal" item becomes one that works.

Tenants carry it as a Route row, which Frappe 16's desk menu never acts on: the
click closed the menu and nothing else happened. module_access.sync_navbar_item
now writes an Action row, but it runs only at provisioning and plan change, so
existing tenants need this once.

Only an EXISTING row is upgraded. A site that never had the item - the control
plane, where sync_site refuses to run - does not gain one here.
"""

from alvoraa_portal import module_access


def execute():
	done = module_access.sync_navbar_item(add_if_missing=False)
	print("  navbar item upgraded to an Action" if done else "  no navbar item on this site")
