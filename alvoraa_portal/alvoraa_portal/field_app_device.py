"""What a phone may do to its own record (slice 013, step 4).

E6, "Remove this phone" (US-15): the person takes the company off their phone.
The record goes to **Removed**, the secret's hash is retired in the same save
(the controller does that), the acknowledgement history is untouched, and
nothing is erased - the row, its punches and its readings all stay, because
"which phone sent this punch" has to stay answerable (SEC-22, D10). The user's
17 Sep decision: this is *not* a withdrawal of agreement; that is
`field_app_join.withdraw_agreement`, a separate choice.

Only the phone's own secret can do it: the secret resolves to exactly one
record, so there is no way to name another phone. A phone that has already
stopped - blocked, replaced, removed - gets its own code and nothing changes
(AC-100). A phone parked in "Consent not given" may be removed like any other
(user decision, 17 Sep).

E11, "Block this phone" (US-17), is HR's side: one action from the Employee
record that stops a lost or misused phone for good, with a reason kept in the
record and never sent to the phone (PRIV-13). Blocked is final (D4): there is
no unblock here or anywhere, and the only way forward is a new code.
"""

import frappe
from frappe import _

from alvoraa_portal import field_app_errors as errors
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_field_device.alvoraa_field_device import (
	SERVER_FLAG,
)
from alvoraa_portal.field_app_desk import BLOCK_REASONS, BLOCKABLE, desk_request, hr_who_may_act
from alvoraa_portal.field_app_errors import requires_field_app_plan
from alvoraa_portal.field_app_join import _employee, _phone_locked
from alvoraa_portal.field_app_limits import HR_KEY, PHONE_KEY, _limited
from alvoraa_portal.field_checkin import DEVICE, _device_from_token, _private_request

# The states a phone can be in and still be removed by the person holding it.
_REMOVABLE = ("Active", "Consent not given")


@frappe.whitelist(allow_guest=True, methods=["POST"])
@_private_request()
@requires_field_app_plan
@_limited(PHONE_KEY, "token", limit=5)
def remove_my_phone(token):
	"""E6. Takes the fixed lock order - the employee, then the phone - and reads
	the phone AGAIN under the lock, so a block HR made a moment earlier wins
	and is answered with its own code rather than a crash (section 11: "HR
	blocks a phone while it is punching - never both").

	Safe to call twice: the second call finds the retired hash and is told
	`DEVICE_REMOVED` with the time.
	"""
	errors.check_app_version()
	device = _device_from_token(token, allowed=_REMOVABLE)

	_employee(device.employee, lock=True)
	_phone_locked(device.name)
	device = _device_from_token(token, allowed=_REMOVABLE)

	device.status = "Removed"
	device.flags[SERVER_FLAG] = True
	device.flags["alvoraa_change_source"] = "The employee"
	device.save(ignore_permissions=True)
	frappe.db.commit()
	return {}


# ── E11 · HR blocks a phone (desk) ───────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
@desk_request
@requires_field_app_plan
@_limited(HR_KEY, "user", limit=30)
def block_phone(device, reason=None):
	"""Block one phone from the Employee record (US-17, AC-110 to AC-113).

	The reason is required here AND in the phone record's own rules, so a
	block with no reason is refused on every door. The record goes to Blocked
	with `block_reason`, who and when (`status_changed_by` = this HR user,
	`status_change_source` = HR), and the secret's hash is retired in the same
	save. The phone's next call is answered `DEVICE_BLOCKED` with no reason.

	Locks in the fixed order - the employee, then the phone - and reads the
	phone again under the lock, so a phone the person removed a moment earlier
	is answered honestly rather than re-written.

	Safe to call twice: a phone that is already Blocked is left exactly as it
	is, reason included. A Replaced or Removed phone holds no live secret and
	cannot be blocked; the sentence says so.

	Saved as the signed-in user, with no permission bypass: on top of the
	employee check, Frappe's own write permission on the phone record and the
	company scoping hook (C-11c) both apply. Fail closed.
	"""
	row = None
	if device and isinstance(device, str) and len(device) <= 140:
		row = frappe.db.get_value(DEVICE, device, ["name", "employee", "status"], as_dict=True)
	if not row:
		frappe.throw(_("You cannot block this phone."), frappe.PermissionError)
	hr_who_may_act(row.employee, _("Only HR can block a phone."))
	if reason not in BLOCK_REASONS:
		frappe.throw(_("Choose a reason. It is kept in the record."), frappe.ValidationError)

	_employee(row.employee, lock=True)
	_phone_locked(row.name)
	doc = frappe.get_doc(DEVICE, row.name)
	if doc.status == "Blocked":
		return {}
	if doc.status not in BLOCKABLE:
		frappe.throw(
			_("This phone has already stopped ({0}). There is nothing to block.").format(
				_(doc.status)),
			frappe.ValidationError)

	doc.status = "Blocked"
	doc.block_reason = reason
	if row.status == "Consent not given":
		# The record's rules let a person move Active or Pending to Blocked. A
		# phone that joined but never agreed still holds a live secret, and a
		# lost one must be stoppable too, so this one move is made as the
		# server on HR's word. It is still recorded as HR's, by this user.
		doc.flags[SERVER_FLAG] = True
	doc.save()
	frappe.db.commit()
	return {}
