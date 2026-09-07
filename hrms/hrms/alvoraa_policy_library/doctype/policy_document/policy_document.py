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
		if self.current_version > 1 and cint(self.acknowledge_on_new_version):
			frappe.enqueue(notify_new_version, policy=self.name, queue="long", enqueue_after_commit=True)
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


def readers_of(policy):
	"""Users who may read the policy: every active employee with a login is
	checked against the rules once. Runs in the background after a publish."""
	from hrms.alvoraa_policy_library.access import can_read

	doc = frappe.get_doc("Policy Document", policy) if isinstance(policy, str) else policy
	frappe.local.policy_profiles = {}
	users = frappe.get_all(
		"Employee", filters={"status": "Active", "user_id": ["is", "set"]}, fields=["user_id", "employee_name"]
	)
	return [u for u in users if can_read(doc, u.user_id)]


def notify_new_version(policy):
	"""Tell every reader a new version is out: a bell notification and an email."""
	doc = frappe.get_doc("Policy Document", policy)
	subject = _("New version of {0} (v{1}) to acknowledge").format(doc.title, doc.current_version)
	note = doc.versions[-1].change_note if doc.versions else ""
	body = "<p>{0}</p>{1}<p>{2}</p>".format(
		_("{0} has published version {1} of \"{2}\".").format(doc.owner_department, doc.current_version, doc.title),
		f"<p><em>{frappe.utils.escape_html(note)}</em></p>" if note else "",
		_("Open the Policies page on the portal to read and acknowledge it."),
	)
	sent = 0
	for user in readers_of(doc):
		try:
			frappe.get_doc(
				{
					"doctype": "Notification Log",
					"for_user": user.user_id,
					"type": "Alert",
					"document_type": "Policy Document",
					"document_name": doc.name,
					"subject": subject,
					"email_content": body,
				}
			).insert(ignore_permissions=True)
			sent += 1
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Policy new-version notification failed")
			continue
		try:  # the bell is the signal; email is best effort (a site may have no outgoing account)
			frappe.sendmail(recipients=[user.user_id], subject=subject, message=body,
			                reference_doctype="Policy Document", reference_name=doc.name)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Policy new-version email failed")
	if not frappe.flags.in_test:
		frappe.db.commit()
	return sent
