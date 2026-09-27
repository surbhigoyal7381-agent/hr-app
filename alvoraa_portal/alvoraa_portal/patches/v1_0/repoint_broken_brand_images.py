"""Repair the brand images on sites that already exist, without touching a choice.

`after_install` brands every NEW tenant. Tenants already live never run it, and
one of them is where the fault was reported: Website Settings on
`ppj.dev.alvoraa.co` held

    banner_image = /private/files/381140.jpg
    favicon      = /private/files/381140.jpg
    app_logo     = NULL
    splash_image = NULL

A browser cannot read `/private/files/...`, so the first two drew the broken-image
icon and the last two drew the Frappe framework logo.

WHAT THIS DOES NOT DO
---------------------
It does not set a logo on a tenant that chose one. That is the whole risk in a
patch like this - run once across every customer, it could quietly delete a
customer's own branding - so the judgement is a single function, `brand._verdict`,
and it has a test of its own that proves a deliberate logo survives:

    tests/test_brand_logo_025.py::test_the_patch_leaves_a_deliberate_logo_alone

Empty and `/private/files/...` are repaired. `/files/...`, an `http(s)://` URL, or
any other app's asset path is left exactly as it is.

Safe to run twice. The second run finds our own asset path in every slot it
touched and writes the same value back.
"""

import frappe

from alvoraa_portal import brand


def execute():
    # The control plane is a site too, and it should carry the product's brand
    # like any other. Nothing here is tenant-shaped, so there is no reason to
    # skip it - unlike module_access.sync_site, which refuses to run there.
    result = brand.apply_site_branding()

    changed = result["changed"]
    left = result["left_alone"]

    if changed:
        for slot, why in sorted(changed.items()):
            reason = {
                "empty": "was not set",
                "broken": "pointed at a private file a browser cannot read",
                "ours": "refreshed to the current asset name",
            }.get(why, why)
            print(f"  {slot}: {reason}")
    if left:
        for slot in sorted(left):
            print(f"  {slot}: left alone - the tenant set this one")
    if not changed and not left:
        print("  nothing to do")

    frappe.db.commit()
