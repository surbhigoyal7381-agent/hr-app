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
  preview saved, and refuses without it. Once pause has run, preview refuses to change
  the list.
- `DROPPED` (only when you pass a list): people preview found but your list leaves out.
  **The job will not mark their October.** Fix their days by Attendance Request.
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
- `OUTSIDE THE LIST`: **the shifts that were off (about 9) get switched on in step 8, and
  from the next hourly run Frappe acts on EVERYONE on them, not only the 73.** Each person
  outside the list on those shifts is named, with the Absent days Frappe will mark from
  1 Nov, their employment type and designation. Look hard at Contract (agency) staff and
  drivers whose days are entered by hand.
- `HALF-DAY ROWS`: half-day leave rows, for the list AND for those outside people, whose
  other half Frappe may set to Absent (any month).
- The last line gives the two numbers step 8 needs: `half_day_rows` and
  `absent_outside_list`.

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
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.enable_and_mark --kwargs "{'company': 'Durga Trading Company', 'from_date': '2026-10-01', 'to_date': '2026-10-31', 'half_day_rows': H, 'absent_outside_list': A}"
```
`H` and `A` are the two numbers from step 5's last line. Before marking anything, it
refuses if either number is wrong, if any punch is still on the wrong shift, if anyone has
a submitted slip, if a shift does not start on 2026-10-01 (step 4 not run), or if a shift
has an empty last sync that will not move.

Must show: one line per shift for punches, then one per switched-on shift for the absent
pass, then the last line:
- the formerly-off shifts are **on from 2026-11-01**, for everyone on them;
- the shifts that were already on are back on **with their old start date**, as before;
- shifts only on old punches are put back as they were.

The script itself marks only the listed people.

**After step 8, the job no longer fixes October.** An October punch that arrives late, an
October day HR cancels, and the October days of anyone dropped in step 2: fix them by
Attendance Request.

## 9. Verify

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.verify --kwargs "{'company': 'Durga Trading Company', 'from_date': '2026-10-01', 'to_date': '2026-10-31', 'reds_for': ['HR-EMP-00226']}"
```
Must show (the keys are printed after `VERIFY`):
- `duplicates` 0, `wrong_tag_unlinked` 0, `days_punched_no_attendance` 0.
- `left_for_a_person`: the days preview listed as LEFT FOR A PERSON, each printed by name.
  The script did not touch them. Fix each by hand.
- `absent_on_days_with_a_punch` and `skip_flagged_punches_on_absent_days`: each day is
  printed by name. Expect two kinds, both correct: the kept hand-made Absent days, and
  days Frappe marked Absent because the person worked fewer hours than the shift's
  minimum. Check every one against the sheet.
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

## If step 8 refuses, or a verify count is wrong after it

- **Step 8 refused:** nothing was marked and the shifts are still off. Fix what the message
  names, then run step 8 again. For "empty last sync that will not move": in the Desk,
  tick "Auto Update Last Sync" on that shift. Pass the numbers the message prints.
- **A count is wrong after step 8** (the shifts are now on): run pause (step 3), then
  set_start (step 4), then step 8 again. Pause keeps the first saved values, so undo still
  works. **Do not run preview again:** it refuses to change the list after pause.

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

**Warning, undo after step 8:** it puts back the old start dates and switches, so on every
shift that was on, the hourly job starts marking October again from the restored,
wrong-tagged punches. After step 8, use the single-day way above instead.

**Last resort, disaster only: restoring the step 1 backup.** This replaces the whole
database. **It wipes everything entered since the backup:** every punch, leave, request,
correction and payroll entry, for everyone. Use it only if the site itself is broken, and
only with Surbhi's decision.
