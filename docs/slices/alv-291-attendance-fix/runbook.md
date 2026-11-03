# ALV-291 runbook: fix DTC's October 2026 attendance

Surbhi runs every step herself, on the server, one at a time. Read each step's output
before running the next. Stop if anything looks wrong.

Run every command inside the backend container, from `/home/frappe/frappe-bench`.
Every step below except undo takes these same three arguments. They are written as `K`:

```
K = "{'company': 'Durga Trading Company', 'from_date': '2026-10-01', 'to_date': '2026-10-31'}"
```

The start date is **1 Oct 2026** everywhere. The script only ever acts on the people
preview lists. The old count of 73 is out of date: on 3 Nov preview found 49, and missed 27
people whose Absent rows hid the fault. Preview now finds them too, so expect **76 or
more**. Surbhi approves the number.

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
- `PEOPLE (N)`. There is no approved number until you have read this list. **Read it, and
  have Surbhi approve it before step 3.** To change it, run preview again with the approved list:
  add `'employees': ['HR-EMP-…', …]` to the arguments. Every later step uses the list
  preview saved, and refuses without it. Once pause has run, preview refuses to change
  the list; see "Changing the list after pause" below.
- `DROPPED` (only when you pass a list): people preview found but your list leaves out.
  **This script will not mark their October.** On shifts that were off, nothing will. On
  shifts that were already on, the hourly job still processes October, as it did before.
  Check their days, and fix them by Attendance Request.
- `REFUSED`: nobody. If anyone is listed, stop.
- `RETAG`: about 23 people, each `TIMINGS DIFFER`. Abhishek (HR-EMP-00226)
  `AMBALA - 10:30 AM - 8:30 PM -> AMBALA - 10:00 AM - 7:00 PM`.
- `CANCEL`: **one line per date**: what the row is now, and what the job should make of the
  punches, with the hours. Compare these dates with the client's latest sheet before step 6.
  A cancelled day cannot be put right by the script afterwards. One punch on a shift with an
  Absent threshold rebuilds as Absent again, 0 hours; the line says so.
- `LEFT FOR A PERSON`: each date, with the reason. A one-punch day on a shift with no Absent
  threshold is here, because the job would make it a full Present. The script leaves these
  days alone. HR fixes each by hand. (Surbhi's decision is pending; one switch changes it.)
- Every `SKIPPED` row with its reason. Kept: leave, attendance request,
  confirmed by a manager, made or changed by a person, changed after it was made,
  corrected by hand (amended), not proven to be automatic.
- `BADGED IN BUT MARKED ABSENT OR HALF DAY`: the job marked these rows on days the person
  has a punch no attendance uses. The first line gives rows and people in the list, and
  **the whole company, read-only: the true size of the fault.** One line per person: rows
  to cancel by status, rows kept with a punch, and Absent rows with no punch that day. Only
  Absent and Half Day rows the job provably made are cancelled. Kept: an Absent that holds a
  punch while another punch that day is unused (a person must check the hours: it may be
  too few hours, or an out-punch that came late), and anything amended, from leave or a
  request, or on a day HR declined a request,
  confirmed, or made or changed by a person. An Absent with no punch that day is never
  touched. A Present row is never cancelled by this rule. Then the number of punches whose
  skip flag cancel_wrong will clear.
- `END DATE`: step 8 does not stop at 31 Oct. It marks up to the last finished shift, so it
  also writes November rows for the listed people. The line gives how many.
- `SHIFTS`: which are switched on in step 8, and which stay as they were (only on old
  punches). A `WARNING` on any shift with an empty or old last sync.
- `LOUD WARNING`: **every person who will get Absent days, with the count, employment type
  and designation.** Look for Contract (agency) staff and drivers. Absent is right only for
  a working day the person really missed. Its `PLUS` line lists days LEFT FOR A PERSON that
  the hourly job will still mark Absent although the person badged in (on shifts that were
  already on). Fix each of those by hand.
- `OUTSIDE THE LIST`: **the shifts that were off (about 9) get switched on in step 8, and
  from the next hourly run Frappe acts on EVERYONE on them, not only the list.** Each person
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
Must show: `cancelled` equal to step 5's CANCEL, `failed 0`, and `Skip flag cleared on N
punches` equal to step 5's number. It clears the flag only on a punch Frappe itself flagged
(it left its own comment), on a day now free, with no second punch in that minute. A flag
from an import stays. Undo flags them again.

## 7. Retag the punches

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.retag --kwargs K
```
Must show: `retagged` no lower than step 5's RETAG, and higher by at most the number step 5
printed on its "Retag's count can be higher" line, because punches with a
cleared skip flag can now be retagged too. No `NOT retagged` line and no `CHECK` line.
(Cancel must come first: Frappe does not move a punch that is still linked to attendance.)

## 8. Mark, then switch on

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.enable_and_mark --kwargs "{'company': 'Durga Trading Company', 'from_date': '2026-10-01', 'to_date': '2026-10-31', 'half_day_rows': H, 'absent_outside_list': A}"
```
`H` and `A` are the two numbers from step 5's last line. The outside count grows day by
day, so if step 5 was on an earlier day, run preview again first (with the same
`employees`, if you passed them) and **re-read OUTSIDE THE LIST and HALF-DAY ROWS** before
you enter the numbers. Before marking anything, it
refuses if either number is wrong, if any punch is still on the wrong shift, if anyone has
a submitted slip, if a shift does not start on 2026-10-01 (step 4 not run), or if a shift
has a last sync, empty or before 1 Nov, that will not move. It can run at any hour: the
script uses the end of the last finished shift, not Frappe's hourly step, which waits for
today's shift to end.

Must show: one line per shift for punches, then one per switched-on shift for the absent
pass, then the last line:
- the formerly-off shifts are **on from 2026-11-01**, for everyone on them;
- the shifts that were already on are back on **with their old start date**, as before;
- shifts only on old punches are put back as they were.

The script itself marks only the listed people, and never a day left for a person.

**After step 8, on the formerly-off shifts the job no longer fixes October.** On the shifts
that were already on, the hourly job processes October as it did before. An October punch
that arrives late, an October day HR cancels, and the October days of anyone dropped in
step 2: check them, and fix them by Attendance Request.

## 9. Verify

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.verify --kwargs "{'company': 'Durga Trading Company', 'from_date': '2026-10-01', 'to_date': '2026-10-31', 'reds_for': ['HR-EMP-00226']}"
```
Must show (the keys are printed after `VERIFY`):
- `duplicates` 0, `wrong_tag_unlinked` 0, `days_punched_no_attendance` 0.
- `left_for_a_person`: the days preview listed as LEFT FOR A PERSON, each printed by name.
  The script did not cancel, retag or mark them. On a shift that was already on, the
  hourly job may still mark such a day (preview's `PLUS` line lists the Absent ones).
  Fix each by hand.
- `absent_on_days_with_a_punch` and `skip_flagged_punches_on_absent_days`: each day is
  printed by name. Not all of these are right, so **check each one against the sheet**. They
  are: the kept rows (a person may need to fix them), rebuilt days where one punch gave 0
  hours, and days Frappe marked Absent because the person worked fewer hours than the shift's
  minimum. Check every one against the sheet.
- `cancelled_no_row_now`: must be 0. Each one is printed: this run cancelled the day and it
  was not rebuilt. Amend the cancelled row, or fix the day by hand.
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

- **Refused, "still on the wrong shift":** run step 7 (retag) again, then step 8. A kept day
  never causes this: its punches are left alone.

- **Step 8 refused:** nothing was marked and the shifts are still off. Fix what the message
  names, then run step 8 again. For "last sync that will not move": in the Desk,
  tick "Auto Update Last Sync" on that shift (undo puts the box back as it was). If the
  numbers were refused: run preview again with the frozen list and **re-read OUTSIDE THE
  LIST and HALF-DAY ROWS** before you enter the new numbers. Never copy them blind.
- **A count is wrong after step 8** (the shifts are now on): run pause (step 3), then
  set_start (step 4), then step 8 again. Pause keeps the first saved values, so undo still
  works. Preview may be run again at any time to read the numbers. The list stays frozen.

## Changing the list after pause

Preview refuses a different list once pause has run. To change it: run **undo** (it puts
the shift settings back and unlocks the list; it keeps the record of old punch tags), then
preview with the new list, then pause and set_start again.

If cancel_wrong has already run, the days it cancelled now have no attendance, so preview
will find those people again: compare its PEOPLE line with the approved list before going on.
**Never delete the undo file to unlock the list:** after retag it is the only record of the
old punch tags.

## Undo

**For a single day (the normal way back):** in the Desk, open the rebuilt Attendance for
that day and Cancel it. Then open the old, cancelled one and press **Amend**, then Submit.
That brings the old day back without touching anything else.

**For punch tags and shift settings:**
```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.undo
```
It puts back the shift switches, start dates, the "Auto Update Last Sync" box and old punch
tags, and unlocks the list (see "Changing the list after pause"). A punch still linked to
rebuilt attendance is listed and left alone: cancel that day first, then run undo again.
It does not touch attendance.

**Warning, undo after step 8:** it puts back the old start dates and switches, so on every
shift that was on, the hourly job starts marking October again from the restored,
wrong-tagged punches. After step 8, use the single-day way above instead.

**Last resort, disaster only: restoring the step 1 backup.** This replaces the whole
database. **It wipes everything entered since the backup:** every punch, leave, request,
correction and payroll entry, for everyone. Use it only if the site itself is broken, and
only with Surbhi's decision.
