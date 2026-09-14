"""Make evidence files that are already public private (slice 010, PRIV-7).

Until slice 010 the portal uploaded goal evidence, goal progress and KPI
progress files as PUBLIC files: a /files/... link that anyone on the internet
can open without logging in. New uploads are private now. This moves the old
ones.

For each distinct public link on Goal Evidence, Goal Progress Update and KPI
Progress Log - taken across all three together, because Frappe re-uses one
file on disk for identical uploads, so rows in different tables can share a
link:
  - the File record is set private, which makes Frappe move it on disk to
    /private/files/ and update every File record sharing that link;
  - it is attached to the goal or KPI of the first row using it, if it was not
    attached to anything, so reading it follows reading that record;
  - every row holding the old link, in any of the three tables, is pointed at
    the new one.

Safe to run twice: it only looks at links that still start with /files/, and
a link whose file was already moved is simply repointed.
One link at a time, committed as it goes, so one bad file cannot undo the rest.
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
	by_url = {}
	for child, parent_doctype in SOURCES:
		if not frappe.db.exists("DocType", child):
			continue
		for row in frappe.get_all(
			child,
			filters={"evidence_file": ["like", "/files/%"]},
			fields=["name", "parent", "evidence_file"],
			order_by="creation asc",
		):
			by_url.setdefault(row.evidence_file, []).append((child, parent_doctype, row))

	moved = failed = no_file = 0
	for url, rows in by_url.items():
		try:
			new_url = _make_private(url, rows)
			if not new_url:
				no_file += len(rows)
				frappe.log_error(
					title="Evidence link has no File record",
					message="; ".join(f"{child} {row.name}" for child, _parent, row in rows),
				)
				continue
			for child, _parent, row in rows:
				frappe.db.set_value(child, row.name, "evidence_file", new_url, update_modified=False)
			frappe.db.commit()
			moved += 1
		except Exception:
			frappe.db.rollback()
			failed += 1
			frappe.log_error(
				title="Evidence file could not be made private",
				message="; ".join(f"{child} {row.name}" for child, _parent, row in rows),
			)

	print(f"make_evidence_files_private: {moved} links made private, {failed} failed, {no_file} rows with no File record")


def _make_private(url, rows):
	"""The private URL for this public link, moving the file if needed. None if no File exists."""
	file_name = frappe.db.get_value("File", {"file_url": url, "is_private": 0, "is_folder": 0}, "name")
	if not file_name:
		# Already moved by an earlier link or run: the rows only need repointing.
		private_url = "/private" + url
		return private_url if frappe.db.exists("File", {"file_url": private_url, "is_folder": 0}) else None

	f = frappe.get_doc("File", file_name)
	f.is_private = 1
	if not f.attached_to_doctype:
		_child, parent_doctype, first = rows[0]
		f.attached_to_doctype = parent_doctype
		f.attached_to_name = first.parent
	f.save()
	return f.file_url
