"""Keep the salary working in the Payroll menu, through every migrate.

Surbhi, 17 Oct 2026: "how can I open it from the navigation", and then the
right follow-up - "is it safe from any overrides in future, while migration."

IT WAS NOT. The Payroll workspace is a STANDARD workspace, shipped as a file
by Frappe HR:

    apps/hrms/hrms/payroll/workspace/payroll/payroll.json

Frappe re-imports that file whenever it changes, which is every Frappe HR
upgrade, and the import REPLACES the record. A link added by hand lives until
the next upgrade and then disappears without a word - and nobody connects a
missing menu entry to an upgrade that happened weeks earlier.

So the link is not added by hand. It is re-applied after every migrate, from
here, which is the only way it survives an upgrade that rewrites the workspace
underneath it.

WHERE IT GOES. Under **Payroll Reports**, directly after **Salary Register** -
the card that already holds Bank Remittance and the tax computations. That is
where a payroll person looks, one line below the register they already use.

RUNS BY ITSELF. If the link is already in place nothing changes, so a migrate
that re-applies it costs one read.

A NO-OP WHERE IT DOES NOT BELONG. A site without the report, or without the
Payroll workspace, is left alone rather than having an entry pointing at
nothing.
"""

import frappe

WORKSPACE = "Payroll"
REPORT = "Salary Components and Workings"
CARD = "Payroll Reports"
AFTER = "Salary Register"
SHORTCUT = "Salary Working"


def after_migrate():
	"""Put the link back, quietly, every time."""
	try:
		_ensure()
	except Exception:
		# A menu entry must never be the thing that fails a migrate. The site
		# is perfectly usable without it - the report is still reachable by
		# search and by URL - so this is logged and stepped over.
		frappe.log_error(title="payroll_menu: could not place the report link")


def _ensure():
	if not frappe.db.exists("Report", REPORT):
		return
	if not frappe.db.exists("Workspace", WORKSPACE):
		return

	w = frappe.get_doc("Workspace", WORKSPACE)
	changed = False

	if not any(l.link_to == REPORT for l in w.links):
		at = _where_it_goes(w)
		if at is not None:
			row = w.append("links", {
				"type": "Link",
				"label": REPORT,
				"link_type": "Report",
				"link_to": REPORT,
				"is_query_report": 1,
				"onboard": 0,
				"hidden": 0,
			})
			w.links.remove(row)
			w.links.insert(at, row)
			for i, l in enumerate(w.links):
				l.idx = i + 1
			changed = True

	if not any(s.link_to == REPORT for s in (w.shortcuts or [])):
		w.append("shortcuts", {
			"type": "Report",
			"label": SHORTCUT,
			"link_to": REPORT,
			"doc_view": "",
		})
		changed = True

	if changed:
		w.flags.ignore_permissions = True
		w.save()
		frappe.db.commit()
		frappe.clear_cache()


def _where_it_goes(w):
	"""Straight after Salary Register, or failing that under the card heading.

	Never appended to the end: the last card on this workspace is Accounting
	Reports, and a payroll working filed under accounting is a payroll working
	nobody finds.
	"""
	for i, l in enumerate(w.links):
		if l.link_to == AFTER:
			return i + 1
	for i, l in enumerate(w.links):
		if l.type == "Card Break" and (l.label or "") == CARD:
			return i + 1
	return None
