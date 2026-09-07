# Copyright (c) 2026, AllAboutHR and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AlvoraaTenantAccessLog(Document):
	"""One row per time the control plane reached into a tenant.

	Write-only in practice. Every field is read_only and no role holds create,
	write or delete - rows arrive through db_insert from _bench_run and nothing
	in the desk can edit or remove them afterwards.

	That matters more than it looks. The point of this log is to answer "did
	anyone open that customer's payroll", and a log the operator can quietly
	edit cannot answer it.
	"""

	pass
