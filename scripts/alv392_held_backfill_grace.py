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
import getpass
import json
import os
import sys

SITE = "grace.alvoraa.co"
FIRST, LAST = "2026-11-01", "2026-11-30"
CHUNK = 50
HOLDABLE = ("Present", "Half Day", "Absent")


def candidates(frappe, companies):
	import alvoraa_portal.held_day as held
	from alvoraa_portal.payroll_rules_apply import _punches

	rows = frappe.get_all(
		"Attendance",
		filters={"docstatus": 1, "company": ("in", companies), "status": ("in", HOLDABLE),
		         "attendance_date": ("between", [FIRST, LAST]), "in_time": ("is", "set"),
		         "attendance_request": ("is", "not set"), "leave_application": ("is", "not set")},
		fields=["name", "employee", "attendance_date", "status", "half_day_status"],
		order_by="attendance_date asc", limit_page_length=0)
	# AC-62: a day inside a SUBMITTED salary slip is skipped. That slip is final;
	# holding the day now would leave the slip and the record disagreeing.
	out = []
	for r in rows:
		r.punches = _punches(r.employee, r.attendance_date)[2]
		if r.punches % 2 == 1 and not held.is_in_final_slip(r.employee, r.attendance_date):
			out.append(r)
	return out


def split_line(todo):
	"""AC-63's kill criterion reads these two splits: one punch against three or
	five, and what the day was marked before. Counts only."""
	count = lambda f: sum(1 for r in todo if f(r))
	return (f"one punch: {count(lambda r: r.punches == 1)}, three or more punches: "
	        f"{count(lambda r: r.punches > 1)}. Was Absent: {count(lambda r: r.status == 'Absent')}, "
	        f"Present: {count(lambda r: r.status == 'Present')}, "
	        f"Half Day: {count(lambda r: r.status == 'Half Day')}.")


def run(site, undo_file, apply=False, undo=False, _in_test_site=None, operator=None):
	"""The whole job. `_in_test_site` is for tests only: a test passes its own site
	name (and an already-open connection) so this path can run end to end. The
	command line never sets it, and any site that is neither Grace nor that name
	is refused, so no real site but Grace can be reached."""
	if site != SITE and site != _in_test_site:
		sys.exit(f"Refused: this script runs only for {SITE}.")
	undo_path = os.path.abspath(undo_file)
	repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
	if undo_path.startswith(repo + os.sep):
		sys.exit("Refused: keep the undo file outside the repository.")

	import frappe

	if not _in_test_site:
		frappe.init(site=site)
		frappe.connect()
	try:
		frappe.set_user("Administrator")
		options = (frappe.get_meta("Attendance").get_field("status").options or "").split("\n")
		if "Held" not in options:
			sys.exit("Refused: Attendance has no Held status on this site. Migrate first.")

		if undo:
			return undo_run(frappe, undo_path)

		companies = frappe.get_all("Company", filters={"alvoraa_hold_odd_punch_days": 1}, pluck="name")
		if not companies:
			sys.exit("Refused: no company has the hold switched on. Switch it on first.")
		todo = candidates(frappe, companies)
		print(f"{len(todo)} day(s) between {FIRST} and {LAST} would be held, in "
		      f"{len(companies)} company(ies).")
		print(split_line(todo))
		dry_path = undo_path + ".dryrun"
		if not apply:
			with open(dry_path, "w") as f:
				json.dump({"count": len(todo)}, f)
			print("Dry run: nothing was changed. Add --apply to hold them.")
			return {"count": len(todo)}
		# AC-63: the real run is only for the count the dry run showed.
		if not os.path.exists(dry_path):
			sys.exit("Refused: run the dry run first, with the same undo file.")
		with open(dry_path) as f:
			expected = json.load(f)["count"]
		if expected != len(todo):
			sys.exit(f"Refused: the dry run found {expected} day(s) and there are {len(todo)} "
			         "now. Something changed. Run the dry run again and read both numbers.")
		# AC-59: who ran it and which run, on every row's Comment (the session is Administrator).
		run_id = frappe.generate_hash(length=8)
		who = operator or getpass.getuser()
		print(f"Run id {run_id}, operator {who}.")
		hold(frappe, todo, undo_path, run_id, who)
		print("Done. Draft slips re-price when they are next saved. Undo list: " + undo_path)
		return {"count": len(todo)}
	finally:
		if not _in_test_site:
			frappe.destroy()


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--site", required=True)
	ap.add_argument("--undo-file", required=True)
	ap.add_argument("--apply", action="store_true")
	ap.add_argument("--undo", action="store_true")
	ap.add_argument("--operator", help="who is running it; defaults to the login name on this computer")
	args = ap.parse_args()
	run(args.site, args.undo_file, apply=args.apply, undo=args.undo, operator=args.operator)


def hold(frappe, todo, undo_path, run_id="", who=""):
	# AC-58: the WHOLE id list is on disk before any row changes.
	with open(undo_path, "a") as f:
		for r in todo:
			f.write(json.dumps({"name": r.name, "status": r.status,
			                    "half_day_status": r.half_day_status}) + "\n")
		f.flush()
		os.fsync(f.fileno())
	done = 0
	for start in range(0, len(todo), CHUNK):
		chunk = todo[start:start + CHUNK]
		for r in chunk:
			frappe.db.set_value("Attendance", r.name, "status", "Held")
			# set_value writes no Version row, so the audit trail is this Comment.
			frappe.get_doc("Attendance", r.name).add_comment(
				"Info", f"Held by the November backfill (ALV-392), run {run_id} by {who}. "
				f"It was {r.status}.")
		frappe.db.commit()
		done += len(chunk)
		print(f"held {done} of {len(todo)}")


def undo_run(frappe, undo_path):
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
