"""ALV-149: the desk's loading splash shows the ALVORA lockup on sites already live.

brand.SLOTS now puts the lockup in Website Settings.splash_image. New tenants
get it at install; this reaches the ones that exist. It runs the same
brand.apply_site_branding() as repoint_broken_brand_images, so the same rule
holds: only an empty slot, a broken /private/files/ path, or one of OUR asset
paths is written. A logo a tenant uploaded is left alone.
"""

import frappe

from alvoraa_portal import brand


def execute():
	result = brand.apply_site_branding()
	for slot, why in sorted(result["changed"].items()):
		print(f"  {slot}: {why}")
	for slot in sorted(result["left_alone"]):
		print(f"  {slot}: left alone - the tenant set this one")
	frappe.db.commit()
