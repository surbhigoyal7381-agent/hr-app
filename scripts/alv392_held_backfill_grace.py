"""ALV-392 slice 085: hold Grace's November odd-punch days, once.

Only for the site grace.alvoraa.co, and only for the days 1 to 30 November 2026.
It turns Present, Half Day and Absent rows that were marked from an odd number
of punches into Held, at the companies whose "hold days with a missing punch"
switch is already on. Nothing else is touched.

    DRY RUN (the default): counts and writes the list of rows it would change.
        env/bin/python apps/alvoraa_portal/../../scripts/alv392_held_backfill_grace.py \
            --site grace.alvoraa.co --undo-file /path/outside/the/repo/undo.jsonl
    APPLY:      add --apply
    UNDO:       --undo --undo-file the same file (puts each listed row back)

Run it with the bench's own python, from the bench folder, never piped into
`bench console` (a piped script loses multi-line blocks silently).

Safe to run twice: a row that is already Held is not a candidate. The undo file
is written and flushed BEFORE each change, so a crash half way can be undone.
Changes are made in chunks of 50 and committed per chunk. Output carries counts
and row names only: no employee name, no time, no reason.
"""

import argparse
import json
import os
import sys

SITE = "grace.alvoraa.co"
FIRST, LAST = "2026-11-01", "2026-11-30"
CHUNK = 50
HOLDABLE = ("Present", "Half Day", "Absent")


def candidates(frappe, companies):
	from alvoraa_portal.payroll_rules_apply import _punches

	rows = frappe.get_all(
		"Attendance",
		filters={"docstatus": 1, "company": ("in", companies), "status": ("in", HOLDABLE),
		         "attendance_date": ("between", [FIRST, LAST]), "in_time": ("is", "set"),
		         "attendance_request": ("is", "not set"), "leave_application": ("is", "not set")},
		fields=["name", "employee", "attendance_date", "status", "half_day_status"],
		order_by="attendance_date asc", limit_page_length=0)
	return [r for r in rows if _punches(r.employee, r.attendance_date)[2] % 2 == 1]


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--site", required=True)
	ap.add_argument("--undo-file", required=True)
	ap.add_argument("--apply", action="store_true")
	ap.add_argument("--undo", action="store_true")
	args = ap.parse_args()

	if args.site != SITE:
		sys.exit(f"Refused: this script runs only for {SITE}.")
	undo_path = os.path.abspath(args.undo_file)
	repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
	if undo_path.startswith(repo + os.sep):
		sys.exit("Refused: keep the undo file outside the repository.")

	import frappe

	frappe.init(site=SITE)
	frappe.connect()
	try:
		frappe.set_user("Administrator")
		options = (frappe.get_meta("Attendance").get_field("status").options or "").split("\n")
		if "Held" not in options:
			sys.exit("Refused: Attendance has no Held status on this site. Migrate first.")

		if args.undo:
			return undo(frappe, undo_path)

		companies = frappe.get_all("Company", filters={"alvoraa_hold_odd_punch_days": 1}, pluck="name")
		if not companies:
			sys.exit("Refused: no company has the hold switched on. Switch it on first.")
		todo = candidates(frappe, companies)
		print(f"{len(todo)} day(s) between {FIRST} and {LAST} would be held, in "
		      f"{len(companies)} company(ies).")
		if not args.apply:
			print("Dry run: nothing was changed. Add --apply to hold them.")
			return
		hold(frappe, todo, undo_path)
		print("Done. Draft slips re-price when they are next saved. Undo list: " + undo_path)
	finally:
		frappe.destroy()


def hold(frappe, todo, undo_path):
	done = 0
	for start in range(0, len(todo), CHUNK):
		chunk = todo[start:start + CHUNK]
		# The undo list is on disk BEFORE any row in the chunk changes.
		with open(undo_path, "a") as f:
			for r in chunk:
				f.write(json.dumps({"name": r.name, "status": r.status,
				                    "half_day_status": r.half_day_status}) + "\n")
			f.flush()
			os.fsync(f.fileno())
		for r in chunk:
			frappe.db.set_value("Attendance", r.name, "status", "Held")
			# set_value writes no Version row, so the audit trail is this Comment.
			frappe.get_doc("Attendance", r.name).add_comment(
				"Info", f"Held by the November backfill (ALV-392). It was {r.status}.")
		frappe.db.commit()
		done += len(chunk)
		print(f"held {done} of {len(todo)}")


def undo(frappe, undo_path):
	with open(undo_path) as f:
		entries = [json.loads(line) for line in f if line.strip()]
	back = 0
	for e in entries:
		if frappe.db.get_value("Attendance", e["name"], "status") != "Held":
			continue  # a human has released it since: leave their decision alone
		frappe.db.set_value("Attendance", e["name"], {"status": e["status"],
		                                              "half_day_status": e["half_day_status"]})
		frappe.get_doc("Attendance", e["name"]).add_comment(
			"Info", "Put back by the undo of the November backfill (ALV-392).")
		back += 1
		if back % CHUNK == 0:
			frappe.db.commit()
	frappe.db.commit()
	print(f"Put back {back} of {len(entries)} day(s). Days released since were left alone.")


if __name__ == "__main__":
	main()
