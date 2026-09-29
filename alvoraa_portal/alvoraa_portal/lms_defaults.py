"""Safe privacy defaults for Frappe LMS, applied once per site (slice 166/167).

`LMS Settings` ships open: `allow_guest_access=1` means anyone with no login
can view every course and lesson page; `allow_job_posting=1` turns on a public
jobs board tab that has nothing to do with internal training;
`disable_signup=1` (self sign-up already off) is kept here explicitly, so a
future change to the app's own default cannot silently reopen it without this
file's own test noticing.

Applied ONCE per site, right after `lms` is installed:
  - a new tenant: provision_tenant.sh calls `apply_safe_defaults` straight
    after `bench install-app lms`.
  - an existing tenant that ticks the feature later: tenant_api._run_install_modules
    calls it the same way, straight after the same install-app call.
  - belt and suspenders: `after_migrate` below runs on every `bench migrate`
    on every site, and is a no-op unless LMS is on that site AND the one-time
    write has never happened - covering a site where the app was installed by
    hand, outside either path above.

Never flips a value back. A sentinel (`frappe.db.get_default`) records that
the write has happened; every run after the first, including every later
`bench migrate`, is a no-op. This is deliberate, not an oversight: if HR later
turns guest access back on for a public course catalogue, or reopens the jobs
board, that choice must stick. There is no way to tell "still the untouched
factory default" apart from "HR set it back to the same value on purpose" by
reading the field alone - Check fields have no "unset" state - so the only
rule that can never fight HR is "touch it once, then never again."
"""

import frappe

SENTINEL = "alvoraa_lms_privacy_applied"

# field -> the safe value to write, once.
SAFE_VALUES = {
	"allow_guest_access": 0,
	"disable_signup": 1,
	"allow_job_posting": 0,
}


def apply_safe_defaults():
	"""Idempotent. A no-op unless LMS is installed on this site and the
	one-time write has never run here. Safe to call by hand."""
	if not frappe.db.exists("DocType", "LMS Settings"):
		return  # lms is not installed on this site
	if frappe.db.get_default(SENTINEL):
		return  # already applied once - never touched again, on purpose

	doc = frappe.get_single("LMS Settings")
	for field, value in SAFE_VALUES.items():
		doc.set(field, value)
	doc.save(ignore_permissions=True)

	frappe.db.set_default(SENTINEL, "1")
	frappe.db.commit()


def after_migrate():
	"""Runs on every `bench migrate`, on every site. See module docstring for
	why this is safe to run repeatedly and forever."""
	apply_safe_defaults()
