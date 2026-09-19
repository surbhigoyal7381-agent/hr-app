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

E11, HR blocking a phone from the desk, joins this module in step 5.
"""

import frappe

from alvoraa_portal import field_app_errors as errors
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_field_device.alvoraa_field_device import (
	SERVER_FLAG,
)
from alvoraa_portal.field_app_errors import requires_field_app_plan
from alvoraa_portal.field_app_join import _employee, _phone_locked
from alvoraa_portal.field_app_limits import PHONE_KEY, _limited
from alvoraa_portal.field_checkin import _device_from_token, _private_request

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
