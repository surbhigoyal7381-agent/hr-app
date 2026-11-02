# ALV-291 runbook: fix DTC's October 2026 attendance

Surbhi runs every step herself, on the server, one at a time. Read each step's output
before running the next. Stop if anything looks wrong.

Run every command inside the backend container, from `/home/frappe/frappe-bench`.
Every step below except undo takes these same three arguments. They are written as `K`:

```
K = "{'company': 'Durga Trading Company', 'from_date': '2026-10-01', 'to_date': '2026-10-31'}"
```

The start date is **1 Oct 2026** everywhere. The script only ever acts on the people
preview lists (expected: **73**).

## 1. Backup

```
bench --site dtc.alvoraa.co backup
```
Must show: a new `-database.sql.gz` file. Keep it as a last resort only (see the end).

## 2. Preview (writes nothing to the database; freezes the list of people)

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.preview --kwargs "{'company': 'Durga Trading Company', 'from_date': '2026-10-01', 'to_date': '2026-10-31'}"
```
Must show:
- `PEOPLE (73)`. **If it is not 73, stop.** Run preview again with the approved list:
  add `'employees': ['HR-EMP-…', …]` to the arguments. Every later step uses the list
  preview saved, and refuses without it.
- `REFUSED`: nobody. If anyone is listed, stop.
- `RETAG`: about 23 people, each `TIMINGS DIFFER`. Abhishek (HR-EMP-00226)
  `AMBALA - 10:30 AM - 8:30 PM -> AMBALA - 10:00 AM - 7:00 PM`.
- `CANCEL` and every `SKIPPED` row with its reason. Kept: leave, attendance request,
  confirmed by a manager, made or changed by a person, changed after it was made,
  corrected by hand (amended), not proven to be automatic.
- `SHIFTS`: which are switched on in step 8, and which stay as they were (only on old
  punches). A `WARNING` on any shift with an empty or old last sync.
- `LOUD WARNING`: **every person who will get Absent days, with the count, employment type
  and designation.** Look for Contract (agency) staff and drivers. Absent is right only for
  a working day the person really missed.
- `HALF-DAY ROWS`: half-day leave rows whose other half Frappe may set to Absent, and the
  number to pass in step 8.

## 3. Pause

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.pause --kwargs K
```
Must show: `pause: N switched off, M were already off` (M about 9). Old values are saved
in `sites/dtc.alvoraa.co/alv291_before.json`.

## 4. Set the start date

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.set_start --kwargs "{'company': 'Durga Trading Company', 'from_date': '2026-10-01', 'to_date': '2026-10-31', 'date': '2026-10-01'}"
```
Must show: `process_attendance_after = 2026-10-01 on N shifts`. Last sync is not touched.

## 5. Preview again

Same command as step 2 (with the same `employees`, if you passed them). The numbers must
match step 2, apart from punches that arrived in between. Step 6 refuses if its count
differs from this preview.

## 6. Cancel the wrong attendance

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.cancel_wrong --kwargs K
```
Must show: `cancelled` equal to step 5's CANCEL, `failed 0`.

## 7. Retag the punches

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.retag --kwargs K
```
Must show: `retagged` equal to step 5's RETAG. No `NOT retagged` line and no `CHECK` line.
(Cancel must come first: Frappe does not move a punch that is still linked to attendance.)

## 8. Mark, then switch on

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.enable_and_mark --kwargs "{'company': 'Durga Trading Company', 'from_date': '2026-10-01', 'to_date': '2026-10-31', 'half_day_rows': N}"
```
`N` is the HALF-DAY ROWS number from step 5. It refuses if N is wrong, if any punch is
still on the wrong shift, or if anyone has a submitted slip.
Must show: one line per shift for punches, then one per switched-on shift for the absent
pass, then `switched on from 2026-11-01`. It marks the listed people only. The start date
moves to 1 Nov, so the hourly job never reaches anyone else's October.

## 9. Verify

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.verify --kwargs "{'company': 'Durga Trading Company', 'from_date': '2026-10-01', 'to_date': '2026-10-31', 'reds_for': ['HR-EMP-00226']}"
```
Must show (the keys are printed after `VERIFY`):
- `duplicates` 0, `wrong_tag_unlinked` 0, `days_punched_no_attendance` 0 (apart from
  days preview left for a person).
- `absent_on_days_with_a_punch` and `skip_flagged_punches_on_absent_days`: only the kept
  hand-made Absent days. Each one is also printed by name. Check every one against the sheet.
- `wrong_tag_on_kept_days`: punches on leave or hand-edited days, left alone on purpose.
- `reds_before_free_HR-EMP-00226`: Abhishek's reds **before** the 2 free reds a month are
  taken off. The slip charges reds minus 2 (never below 0). Compare with the client's
  figure on the same basis.

Then check the client's latest sheet. The sheet wins.

## 10. Delete the undo file (after sign-off)

```
rm sites/dtc.alvoraa.co/alv291_before.json
```
It holds the old punch times. Delete it once DTC has signed off October.

---

## Undo

**For a single day (the normal way back):** in the Desk, open the rebuilt Attendance for
that day and Cancel it. Then open the old, cancelled one and press **Amend**, then Submit.
That brings the old day back without touching anything else.

**For punch tags and shift settings:**
```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.undo
```
It puts back the shift switches, start dates and old punch tags. A punch still linked to
rebuilt attendance is listed and left alone: cancel that day first, then run undo again.
It does not touch attendance.

**Last resort, disaster only: restoring the step 1 backup.** This replaces the whole
database. **It wipes everything entered since the backup:** every punch, leave, request,
correction and payroll entry, for everyone. Use it only if the site itself is broken, and
only with Surbhi's decision.
