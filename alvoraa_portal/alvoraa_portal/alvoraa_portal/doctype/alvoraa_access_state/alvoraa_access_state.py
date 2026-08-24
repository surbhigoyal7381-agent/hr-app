"""What this site has denied, and what it looked like before.

A Single doctype rather than site config, because this is DATA - up to a few
hundred permission rows - and site config is configuration. It also means the
snapshot is included in a database backup, which matters: it is the only record
of how to put a tenant's permissions back.
"""

import frappe
from frappe.model.document import Document


class AlvoraaAccessState(Document):
	pass
