"""Give HR records saved before slice 011 their branch.

Patches run before `after_migrate`, so on a site already live the field does not
exist yet when this runs. Create it first - that call is safe to run again when
after_migrate repeats it a moment later.

A new site has no old records, and Frappe marks its patches done without running
them; after_install adds the field there.
"""

from alvoraa_portal import branch_scope


def execute():
	branch_scope.after_migrate()
	branch_scope.fill_existing()
