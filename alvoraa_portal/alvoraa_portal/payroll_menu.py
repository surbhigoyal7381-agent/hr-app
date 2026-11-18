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

ALV-358 (18 Nov 2026) adds the second report the same way: Daily Attendance
Workings under Shift & Attendance -> Reports, straight after Monthly Attendance
Sheet. In Frappe v16 that section is drawn twice - as a card on the workspace
page, and as a section of the left-hand Workspace Sidebar, which is also a
standard file (apps/hrms/hrms/workspace_sidebar/shift_&_attendance.json) and is
replaced the same way. So that link is placed, and re-placed, in both.
"""

import frappe

# (workspace, card heading, link to follow, report, shortcut label or None)
WORKSPACE_LINKS = [
	("Payroll", "Payroll Reports", "Salary Register", "Salary Components and Workings",
	 "Salary Working"),
	("Shift & Attendance", "Reports", "Monthly Attendance Sheet", "Daily Attendance Workings",
	 None),
]
# (workspace sidebar, section heading, link to follow, report)
SIDEBAR_LINKS = [
	("Shift & Attendance", "Reports", "Monthly Attendance Sheet", "Daily Attendance Workings"),
]


def after_migrate():
	"""Put the links back, quietly, every time."""
	for spec in WORKSPACE_LINKS:
		try:
			_ensure(*spec)
		except Exception:
			# A menu entry must never be the thing that fails a migrate. The site
			# is perfectly usable without it - the report is still reachable by
			# search and by URL - so this is logged and stepped over.
			frappe.log_error(title="payroll_menu: could not place the report link")
	for spec in SIDEBAR_LINKS:
		try:
			_ensure_sidebar(*spec)
		except Exception:
			frappe.log_error(title="payroll_menu: could not place the sidebar link")


def _ensure(workspace, card, after, report, shortcut):
	if not frappe.db.exists("Report", report):
		return
	if not frappe.db.exists("Workspace", workspace):
		return

	w = frappe.get_doc("Workspace", workspace)
	changed = False

	if not any(l.link_to == report for l in w.links):
		at = _where_it_goes(w, card, after)
		if at is not None:
			row = w.append("links", {
				"type": "Link",
				"label": report,
				"link_type": "Report",
				"link_to": report,
				"is_query_report": 1,
				"onboard": 0,
				"hidden": 0,
			})
			w.links.remove(row)
			w.links.insert(at, row)
			for i, l in enumerate(w.links):
				l.idx = i + 1
			changed = True

	if shortcut and not any(s.link_to == report for s in (w.shortcuts or [])):
		w.append("shortcuts", {
			"type": "Report",
			"label": shortcut,
			"link_to": report,
			"doc_view": "",
		})
		changed = True

	if changed:
		w.flags.ignore_permissions = True
		w.save()
		frappe.db.commit()
		frappe.clear_cache()


def _ensure_sidebar(sidebar, section, after, report):
	"""The same link in the left-hand sidebar, inside its section, after `after`."""
	if not frappe.db.exists("Report", report):
		return
	if not frappe.db.exists("Workspace Sidebar", sidebar):
		return

	s = frappe.get_doc("Workspace Sidebar", sidebar)
	if any(i.link_to == report for i in s.items):
		return
	at = None
	for i, item in enumerate(s.items):
		if item.link_to == after:
			at = i + 1
			break
	if at is None:
		for i, item in enumerate(s.items):
			if item.type == "Section Break" and (item.label or "") == section:
				at = i + 1
				break
	if at is None:
		return
	row = s.append("items", {
		"type": "Link",
		"label": report,
		"link_type": "Report",
		"link_to": report,
		"child": 1,
	})
	s.items.remove(row)
	s.items.insert(at, row)
	for i, item in enumerate(s.items):
		item.idx = i + 1
	s.flags.ignore_permissions = True
	s.save()
	frappe.db.commit()
	frappe.clear_cache()


def _where_it_goes(w, card, after):
	"""Straight after `after`, or failing that under the card heading.

	Never appended to the end: on the Payroll workspace the last card is
	Accounting Reports, and a payroll working filed under accounting is a
	payroll working nobody finds.
	"""
	for i, l in enumerate(w.links):
		if l.link_to == after:
			return i + 1
	for i, l in enumerate(w.links):
		if l.type == "Card Break" and (l.label or "") == card:
			return i + 1
	return None
