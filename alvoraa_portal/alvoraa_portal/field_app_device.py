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
	JOIN_PASSWORD,
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

	# Read under the same lock as the BLOCKABLE check above, not the pre-lock
	# `row` — a phone the employee moved to "Consent not given" a moment ago
	# (withdrawing agreement) must still get the server-flag path, or its
	# block fails against the person-only transition table for no good reason.
	was_not_agreed = doc.status == "Consent not given"
	doc.status = "Blocked"
	doc.block_reason = reason
	if was_not_agreed:
		# The record's rules let a person move Active or Pending to Blocked. A
		# phone that joined but never agreed still holds a live secret, and a
		# lost one must be stoppable too, so this one move is made as the
		# server on HR's word. It is still recorded as HR's, by this user.
		doc.flags[SERVER_FLAG] = True
	doc.save()
	frappe.db.commit()
	return {}


# ── ALV-128 · a login that stops or is unlinked stops its phones ────────────
#
# A CHANGED PASSWORD is not here any more (26 Sep 2026 design change): it signs
# the phone out on its next call instead of blocking it, and it covers every
# path that can set a password - see `field_checkin._sign_out_if_password_changed`.

def block_phones_for_disabled_login(doc, method=None):
	"""doc_events User on_update. A phone that signed in with a password stops
	for good the moment that login is disabled - the same final Blocked state,
	with the secret retired, that HR's own block and the leaver hook give it.

	The leaver hook does not cover this: an employee can stay Active while
	their login is switched off. Phones that joined with a code from HR are
	left alone - they never depended on a login. The punch and the start
	screen also refuse a password phone whose login is disabled
	(`field_checkin._refuse_unless_app_phone_is_eligible`), so a disable made
	without this hook (a script, `db.set_value`) still stops the phone.

	Found by `activated_by` (the login that signed in) and by the employee
	record that names the login today, so an unlinked record is still caught.
	One phone that will not save does not stop the others or the User save.

	A new password is NOT handled here: it signs the phone out on its next
	call (the user's decision, 26 Sep 2026), which no hook could cover for
	every path that sets a password.
	"""
	if not frappe.db.exists("DocType", DEVICE):
		return
	if not doc.enabled:
		_block_password_phones(doc.name, "Login disabled")


def _block_password_phones(user, reason, employee=None):
	"""Block every live password phone this login signed in (or, with
	`employee`, that employee's password phones not signed in by `user`).
	The same final Blocked state, with the secret retired, that HR's own block
	gives. Returns the phone names it blocked."""
	live = ["in", list(BLOCKABLE)]
	if employee:
		names = set(frappe.get_all(DEVICE, filters={"join_method": JOIN_PASSWORD, "status": live,
		                                            "employee": employee,
		                                            "activated_by": ["!=", user or ""]},
		                           pluck="name"))
	else:
		employees = frappe.get_all("Employee", filters={"user_id": user}, pluck="name")
		names = set(frappe.get_all(DEVICE, filters={"join_method": JOIN_PASSWORD, "status": live,
		                                            "activated_by": user}, pluck="name"))
		if employees:
			names |= set(frappe.get_all(DEVICE, filters={"join_method": JOIN_PASSWORD, "status": live,
			                                             "employee": ["in", employees]}, pluck="name"))
	for name in sorted(names):
		try:
			phone = frappe.get_doc(DEVICE, name)
			phone.status = "Blocked"
			phone.block_reason = reason
			phone.flags[SERVER_FLAG] = True
			phone.flags["alvoraa_change_source"] = "System"
			phone.save(ignore_permissions=True)
		except Exception:
			# Named by the phone record only; nothing personal in the log.
			frappe.log_error(f"could not block field device {name} ({reason})",
			                 "Field app password phone")
	return sorted(names)


def block_phones_for_unlinked_login(doc, method=None):
	"""doc_events Employee on_update (SEC-28). When an employee record stops
	naming a login - changed to another, or emptied - the password phones the
	OLD login signed in are blocked, reason "Login unlinked". A phone signed in
	by the login the record names now is left alone. The punch refuses such a
	phone too (`LOGIN_UNLINKED`), so a change made without this hook still
	stops it."""
	if not doc.has_value_changed("user_id") or not frappe.db.exists("DocType", DEVICE):
		return
	_block_password_phones(doc.get("user_id"), "Login unlinked", employee=doc.name)
