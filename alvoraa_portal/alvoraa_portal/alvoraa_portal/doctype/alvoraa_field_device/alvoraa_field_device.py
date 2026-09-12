# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now


class AlvoraaFieldDevice(Document):
	def validate(self):
		if not self.registered_on:
			self.registered_on = now()

	def on_update(self):
		"""Record who turned a device on.

		HR activating a second phone for somebody is the one moment in this
		feature where a human decision matters, so it is worth being able to
		answer "who allowed this" six months later.
		"""
		if self.has_value_changed("status") and self.status == "Active":
			if not self.activated_by:
				self.db_set("activated_by", frappe.session.user, update_modified=False)
