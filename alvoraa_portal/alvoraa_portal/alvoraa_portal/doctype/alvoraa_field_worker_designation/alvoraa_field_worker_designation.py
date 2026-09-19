# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""One row of the field-worker designation list on HR Settings.

A child table and not a comma-separated text field, because Frappe's
`Table MultiSelect` needs one, and because a Link to Designation means a renamed
or deleted designation is followed or refused by the framework instead of
silently stopping every driver's app. The rules about the list - who may change
it, when a reason is needed - live in `alvoraa_portal.field_app_settings`, on the
parent, because that is where every door into the list meets.
"""

from frappe.model.document import Document


class AlvoraaFieldWorkerDesignation(Document):
	pass
