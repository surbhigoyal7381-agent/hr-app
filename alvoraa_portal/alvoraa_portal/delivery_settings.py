"""Per-tenant settings for the vendor, driver and delivery module.

Slice 016 item 2. This module shipped with one customer's details written into
the source: a warehouse name and phone number, five named shops with their
coordinates, an "ops@" mailbox at that customer's domain in six places, and the
customer's name signed at the bottom of every outgoing email. The repository is
public, and - much worse - every tenant that ran this code sent its own
customers' names and addresses to that one mailbox.

Everything here reads `frappe.conf`, which is the site's own config file and a
tenant cannot edit it. Nothing here needs a DocType, a custom field or a
migration; the keys are optional and each has a neutral fallback.

Keys, all optional:

    portal_warehouse_name     shown as the pickup point on a vendor's order
    portal_warehouse_phone    the Call button on a vendor's order
    portal_ops_name           signed at the bottom of outgoing emails
    portal_ops_email          where operational alerts go
    portal_hub_coords         [lat, lng] of the dispatch hub, for the map
    portal_vendor_coords      {"<vendor name>": [lat, lng]} pins for the map
"""

import frappe
from frappe import _


def _conf(key, default=None):
    value = frappe.conf.get(key)
    return default if value in (None, "") else value


def warehouse_name():
    """The pickup point's name. Neutral word when nothing is configured."""
    return _conf("portal_warehouse_name") or _("Warehouse")


def warehouse_phone():
    """The pickup point's phone, or None.

    None is a real answer, not a failure: vendor-portal.html only draws the Call
    button when this is set, so an unconfigured tenant simply has no button.
    """
    return _conf("portal_warehouse_phone")


def ops_name():
    """Who the outgoing emails are from, in words.

    Falls back to the tenant's own company name from Global Defaults - which is
    where organisation-level configuration belongs - and only then to a generic
    word. It never names another tenant.
    """
    configured = _conf("portal_ops_name")
    if configured:
        return configured
    try:
        company = frappe.defaults.get_global_default("company")
    except Exception:
        company = None
    if company:
        return "%s %s" % (company, _("Operations"))
    return _("Operations")


def ops_recipients():
    """Where operational alerts go. An EMPTY list when nothing is configured.

    Empty means do not send, and that is deliberate. These alerts carry a
    customer's name, address and order value. The old code fell back to one
    customer's mailbox, so every other tenant's alerts were posted to a third
    party. There is no safe default address, so the safe behaviour is silence
    plus a log line - fail closed.
    """
    value = _conf("portal_ops_email")
    if not value:
        return []
    if isinstance(value, str):
        return [e.strip() for e in value.split(",") if e.strip()]
    return [str(e).strip() for e in value if str(e).strip()]


def send_ops_alert(subject, message, context):
    """Send an operational alert, or record plainly that it was not sent.

    `context` is the document name the alert is about - never its contents. The
    log line has to be enough for a person to open the record themselves and no
    more than that, because these alerts are about named customers and drivers.

    Returns True when the mail was handed to Frappe, False otherwise.
    """
    recipients = ops_recipients()
    if not recipients:
        frappe.log_error(
            "No portal_ops_email configured for this site; alert not sent. "
            "Reference: %s" % context,
            "Delivery ops alert not sent",
        )
        return False
    try:
        frappe.sendmail(recipients=recipients, subject=subject, message=message)
        return True
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Delivery ops alert failed: %s" % context)
        return False


# The map has to centre on something or it draws nothing. This is the point the
# module has always used and it names nobody, so it stays as the fallback while
# becoming configurable. The five NAMED shops are a different matter and have
# gone.
DEFAULT_HUB = (30.7060, 76.8001)


def hub_coords():
    """(lat, lng) of the dispatch hub."""
    lat, lng = _pair(_conf("portal_hub_coords"))
    if lat is None or lng is None:
        return DEFAULT_HUB
    return lat, lng


def vendor_coords(vendor_name):
    """(lat, lng) to pin this vendor at, or the hub, or (None, None).

    The five named shops that used to live here were five real businesses and
    their locations, in a public repository, serving every tenant. A tenant that
    wants pins configures its own; vendor-portal.html already copes with no
    position at all.
    """
    mapping = _conf("portal_vendor_coords") or {}
    if isinstance(mapping, dict) and vendor_name in mapping:
        return _pair(mapping[vendor_name])
    return hub_coords()


def _pair(value):
    try:
        return float(value[0]), float(value[1])
    except (TypeError, ValueError, IndexError, KeyError):
        return None, None
