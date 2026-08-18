import frappe

# Two possible starting states, because environments diverged:
#   - a site built from `dev`                     -> doctypes are named "Grace *"
#   - a site built from the rebrand branch        -> doctypes are named "Alvox *"
# Both converge on "Alvoraa *". Whichever exists is renamed; the other is a no-op.
RENAMES = [
	("Grace Cycle Config", "Alvoraa Cycle Config"),
	("Alvox Cycle Config", "Alvoraa Cycle Config"),
	("Grace Rating Scale Item", "Alvoraa Rating Scale Item"),
	("Alvox Rating Scale Item", "Alvoraa Rating Scale Item"),
	("Grace Rating Scale", "Alvoraa Rating Scale"),
	("Alvox Rating Scale", "Alvoraa Rating Scale"),
	("Grace Appraisal Extension", "Alvoraa Appraisal Extension"),
	("Alvox Appraisal Extension", "Alvoraa Appraisal Extension"),
]


def execute():
	"""Rename the four Grace/Alvox doctypes to Alvoraa.

	Idempotent: a no-op where already renamed, and safe to re-run. Uses rename_doc so
	the table is renamed and Link references follow - never raw SQL, which would leave
	links pointing at a name that no longer exists.
	"""
	for old, new in RENAMES:
		if not frappe.db.exists("DocType", old):
			continue
		if frappe.db.exists("DocType", new):
			# Both present - the target already exists, so the stale one is left alone
			# rather than merged. Merging user data is not a decision for a patch.
			frappe.log_error(
				title="rename_doctypes_to_alvoraa",
				message="Both %r and %r exist; skipped. Resolve manually." % (old, new),
			)
			continue
		frappe.rename_doc("DocType", old, new, force=True, ignore_permissions=True)

	frappe.clear_cache()
