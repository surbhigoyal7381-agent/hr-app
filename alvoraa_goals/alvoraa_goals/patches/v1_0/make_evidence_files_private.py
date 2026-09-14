"""Make evidence files that are already public private (slice 010, PRIV-7).

Until slice 010 the portal uploaded goal evidence, goal progress and KPI
progress files as PUBLIC files: a /files/... link that anyone on the internet
can open without logging in. New uploads are private now. This moves the old
ones.

For each distinct public link on Goal Evidence, Goal Progress Update and KPI
Progress Log:
  - the File record is set private, which makes Frappe move it on disk to
    /private/files/ and update every File record sharing that link;
  - it is attached to the goal or KPI, if it was not attached to anything, so
    reading it follows reading that record;
  - every row holding the old link is pointed at the new one.

Safe to run twice: it only looks at links that still start with /files/.
One file at a time, committed as it goes, so one bad file cannot undo the rest.
A link that cannot be moved is logged by File or row name only - never the
link, the value or a person - and left for HR to look at.

Rollback: none automatic. Setting a File back to public moves it back.

Dry run on a tenant before migrate (read-only):
  SELECT 'Goal Evidence', COUNT(*) FROM `tabGoal Evidence` WHERE evidence_file LIKE '/files/%'
  UNION ALL SELECT 'Goal Progress Update', COUNT(*) FROM `tabGoal Progress Update` WHERE evidence_file LIKE '/files/%'
  UNION ALL SELECT 'KPI Progress Log', COUNT(*) FROM `tabKPI Progress Log` WHERE evidence_file LIKE '/files/%';
"""

import frappe

SOURCES = (
	("Goal Evidence", "Individual Goal"),
	("Goal Progress Update", "Individual Goal"),
	("KPI Progress Log", "KPI"),
)


def execute():
	moved = failed = no_file = 0
	for child, parent_doctype in SOURCES:
		if not frappe.db.exists("DocType", child):
			continue
		rows = frappe.get_all(
			child,
			filters={"evidence_file": ["like", "/files/%"]},
			fields=["name", "parent", "evidence_file"],
			order_by="creation asc",
		)
		by_url = {}
		for row in rows:
			by_url.setdefault(row.evidence_file, []).append(row)

		for url, url_rows in by_url.items():
			file_name = frappe.db.get_value("File", {"file_url": url, "is_private": 0, "is_folder": 0}, "name")
			if not file_name:
				no_file += len(url_rows)
				frappe.log_error(
					title="Evidence link has no File record",
					message=f"{child} rows: {', '.join(r.name for r in url_rows)}",
				)
				continue
			try:
				f = frappe.get_doc("File", file_name)
				f.is_private = 1
				if not f.attached_to_doctype:
					f.attached_to_doctype = parent_doctype
					f.attached_to_name = url_rows[0].parent
				f.save()
				for row in url_rows:
					frappe.db.set_value(child, row.name, "evidence_file", f.file_url, update_modified=False)
				frappe.db.commit()
				moved += 1
			except Exception:
				frappe.db.rollback()
				failed += 1
				frappe.log_error(title="Evidence file could not be made private", message=f"File {file_name}")

	print(f"make_evidence_files_private: {moved} made private, {failed} failed, {no_file} rows with no File record")
