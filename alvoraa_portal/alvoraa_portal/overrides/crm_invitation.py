"""ALV-174: Frappe CRM's own invitation email names itself, not the tenant.

`crm.fcrm.doctype.crm_invitation.crm_invitation.CRMInvitation.invite_via_email`
hardcodes BOTH the subject (`title = "Frappe CRM"`, built into the f-string in
Python) and the body (`templates/emails/crm_invitation.html` says literally
"You have been invited to join Frappe CRM" - it never reads the `title` arg it
is passed). A template override cannot fix the subject line at all, and is
unreliable for the body: Frappe's Jinja loader searches installed apps in
REVERSED install order (frappe/utils/jinja.py:_get_jloader), and
`provision_tenant.sh` / `tenant_api._run_install_modules` install
`alvoraa_portal` BEFORE `crm` on every tenant - so CRM's own copy of the
template would still win, not ours. Confirmed by reading both files, not
assumed.

So this replaces the method itself, the mechanism `frappe-conventions.md`
already names for "replace standard logic wholesale":
`override_doctype_class` (`alvoraa_portal/hooks.py`). It builds the email
inline instead of through `template="crm_invitation"`, so nothing here depends
on which app's copy of a Jinja file the loader happens to pick.

Only `invite_via_email` changes. Every other CRM Invitation behaviour -
`before_insert`, `accept_invitation`, `expire_invitations` - is the parent
class's, untouched.
"""

import frappe
from crm.fcrm.doctype.crm_invitation.crm_invitation import CRMInvitation
from frappe.email.email_body import get_brand_name


class AlvoraCRMInvitation(CRMInvitation):
	def invite_via_email(self):
		invite_link = frappe.utils.get_url(
			f"/api/method/crm.api.accept_invitation?key={self.key}")
		if frappe.local.dev_server:
			print(f"Invite link for {self.email}: {invite_link}")  # nosemgrep

		title = get_brand_name() or "Alvora HRMS"

		frappe.sendmail(
			recipients=self.email,
			subject=frappe._("You have been invited to join {0}").format(title),
			content=(
				f"<p>{frappe._('You have been invited to join {0}').format(frappe.utils.escape_html(title))}</p>"
				f'<p><a class="btn btn-primary" href="{invite_link}">'
				f"{frappe._('Accept Invitation')}</a></p>"
			),
			now=True,
		)
		self.db_set("email_sent_at", frappe.utils.now())
