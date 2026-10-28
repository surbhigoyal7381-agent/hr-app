"""ALV-242 — mark the users who were here before the lock existed.

The lock (`auth.lock_until_password_chosen`) reads one signal: an empty
`User.last_password_reset_date` means "HR set this password, they never chose
their own". That is true of everybody HR onboards from now on. It is also true,
by accident, of every account ever created on a demo tenant — nobody there has
ever used the change-password screen, so nobody there has a date.

`hooks.py` belongs to the app, not to a tenant, so the lock switches on for
every site on the bench at once. Without this, the day it ships, every user on
demo, grace, alvoraa.co and aahr is stuck on the password screen.

Run once per site, by hand, immediately before the lock goes live:

    bench --site demo.alvoraa.co execute \
        alvoraa_portal.first_use_backfill.settle_existing_users

This is a one-off. It is not a patch and not scheduled, because it must never
run again: after the lock is live, an empty date is real information, and
stamping it would quietly let somebody keep a password HR handed out.
"""

import frappe

# The whole reason the lock exists. These people are exactly the ones who were
# handed a shared password and must change it, so settling them would disarm
# the feature on the tenant it was built for. A hard list, not a flag, because
# the cost of a typo here is silent and the cost of the list is nothing.
NEVER_SETTLE = {"dtc.alvoraa.co"}


def settle_existing_users():
	"""Stamp today onto every empty `last_password_reset_date` on this site."""
	site = frappe.local.site

	if site in NEVER_SETTLE:
		frappe.throw(
			f"Refusing to run on {site}. Its staff are the people the first-use "
			f"lock exists for; settling them would turn it off."
		)

	before = frappe.db.count("User", {"last_password_reset_date": ["is", "not set"]})

	# A bulk UPDATE rather than the ORM. There is no bulk `set_value`, and
	# walking several thousand User documents one at a time would fire every
	# User controller hook - welcome emails and permission rebuilds among them -
	# for a change that is pure bookkeeping.
	frappe.db.sql(
		"""UPDATE `tabUser`
		   SET `last_password_reset_date` = CURDATE()
		   WHERE `last_password_reset_date` IS NULL"""
	)
	frappe.db.commit()

	after = frappe.db.count("User", {"last_password_reset_date": ["is", "not set"]})

	print(f"site:    {site}")
	print(f"settled: {before - after}")
	print(f"left:    {after}")
	return {"site": site, "settled": before - after, "left": after}
