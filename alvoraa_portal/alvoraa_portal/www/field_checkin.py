"""The field check-in app, in the tenant's own colours.

Public on purpose. A driver has no login - proving who they are is the device
secret's job, checked inside `alvoraa_portal.field_checkin`, not the session's.
So this page must render for Guest, unlike every other portal page here.

There is no colour logic in this file. It briefly had its own, in Python, which
made a third implementation alongside the design system's and the login page's.
All three now share `templates/includes/brand_color.html`.
"""

import frappe

from alvoraa_portal.tenant_context import get_branding

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.no_header = 1
	context.no_sidebar = 1
	context.update(get_branding())
	# The notice states the real retention period, read from settings, so it
	# can never promise one thing while the organisation does another.
	from alvoraa_portal.field_checkin import notice_facts
	context.update(notice_facts())
	return context
