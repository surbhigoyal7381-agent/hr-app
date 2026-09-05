"""Remove tenant passwords left in clear text in the provisioning jobs file.

Until 2026-08-23 `create_tenant` wrote the new tenant's Administrator password
into `sites/kinexus_provision_jobs.json` as plain text, and that file is read
back by the control plane over HTTP. Credentials now live in Frappe's encrypted
store instead, but the historic values are still sitting on disk.

Changing the code does not remove them, so this does. It is deliberately a
patch rather than a cleanup on read: a value that should never have been written
should be gone whether or not anyone opens the Jobs page again.

Nothing is lost that matters. Every job in that file has already finished, and
its password was shown to the operator at the time.
"""

import frappe

from alvoraa_portal.tenant_api import _read_jobs, _write_jobs


def execute():
	jobs = _read_jobs()
	if not jobs:
		return

	scrubbed = 0
	for job in jobs.values():
		if job.get("admin_password"):
			job["admin_password"] = ""
			scrubbed += 1
		# The key itself is left in place. Removing it would change the shape of
		# records the console already knows how to read, for no benefit.

	if scrubbed:
		_write_jobs(jobs)

	frappe.logger().info(
		f"alvoraa_portal: scrubbed clear-text passwords from {scrubbed} provisioning job(s)"
	)
