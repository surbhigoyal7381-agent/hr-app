import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime

from hrms.alvoraa_policy_library.access import can_write


class PolicyDocument(Document):
	def validate(self):
		self.flags.ignore_links = False
		if not self.get("read_access"):
			self.append("read_access", {"access_type": "All Employees"})
		for row in list(self.read_access) + list(self.write_access or []):
			_check_rule(row)
		if self.status == "Published":
			if not (self.content or self.attachment):
				frappe.throw(_("A published policy needs content or an attachment."))
			if not self.versions:
				# published straight from the desk: version 1 is the current text
				self._snapshot(_("First published version."))
			else:
				last = self.versions[-1]
				self.has_unpublished_changes = int(
					(self.content or "") != (last.content_snapshot or "")
					or (self.attachment or "") != (last.attachment_snapshot or "")
					or (self.summary or "") != (last.summary_snapshot or "")
				)
		else:
			self.has_unpublished_changes = 0
		if self.status != "Published" and self.has_value_changed("status") and self.get_doc_before_save():
			pass

	def _snapshot(self, change_note=None):
		self.current_version = cint(self.current_version) + 1
		self.append(
			"versions",
			{
				"version": self.current_version,
				"published_on": now_datetime(),
				"published_by": frappe.session.user,
				"change_note": change_note,
				"summary_snapshot": self.summary,
				"attachment_snapshot": self.attachment,
				"content_snapshot": self.content,
			},
		)
		self.has_unpublished_changes = 0

	@frappe.whitelist()
	def publish(self, change_note=None):
		"""Make the working copy the version everyone reads."""
		if not can_write(self):
			frappe.throw(_("You cannot publish this policy."), frappe.PermissionError)
		if not (self.content or self.attachment):
			frappe.throw(_("Add the policy text or attach the PDF before publishing."))
		if self.status == "Published" and self.versions and not self.has_unpublished_changes:
			frappe.throw(_("Nothing has changed since version {0} was published.").format(self.current_version))
		self.status = "Published"
		self._snapshot(change_note)
		self.save()
		return {"name": self.name, "version": self.current_version}

	def published_view(self):
		"""What a reader sees: the last published snapshot, never the working copy."""
		if self.versions:
			last = self.versions[-1]
			return frappe._dict(
				version=last.version,
				published_on=last.published_on,
				published_by=last.published_by,
				change_note=last.change_note,
				summary=last.summary_snapshot,
				attachment=last.attachment_snapshot,
				content=last.content_snapshot,
			)
		return frappe._dict(
			version=self.current_version, summary=self.summary, attachment=self.attachment, content=self.content
		)


def _check_rule(row):
	need = {"Role": "role", "User": "user", "Designation": "designation", "Branch": "branch"}.get(row.access_type)
	if need and not row.get(need):
		frappe.throw(_("Row {0}: {1} needs a {2}.").format(row.idx, row.access_type, need))


def acknowledgement_status(policy, employee):
	"""(needed, done) for the policy's current version."""
	needed = bool(cint(policy.get("acknowledge_on_joining")) or cint(policy.get("acknowledge_on_new_version")))
	if not needed or not employee:
		return False, False
	done = bool(
		frappe.db.exists(
			"Policy Acknowledgement",
			{"policy_document": policy.name, "version": cint(policy.current_version), "employee": employee},
		)
	)
	return True, done
