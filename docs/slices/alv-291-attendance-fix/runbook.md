# ALV-291 runbook: fix DTC's October 2026 attendance

Surbhi runs every step herself, one at a time, on the server. Each step is a separate
command. Read each step's output before running the next one. Stop if any output looks
wrong.

Run every command inside the backend container, from `/home/frappe/frappe-bench`.
`S=dtc.alvoraa.co`, `C="Durga Trading Company"`, period `2026-10-01` to `2026-10-31`.

**Order matters: cancel BEFORE retag.** Frappe only re-tags a punch that is not linked to
attendance, and cancelling is what unlinks it.

## 1. Backup (cannot be skipped)

```
bench --site dtc.alvoraa.co backup
```
Must show: the path of a new `-database.sql.gz` file. Cancelled attendance cannot be
un-cancelled. This backup is the only way back for it.

## 2. Preview (writes nothing)

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.preview --kwargs "{'company': 'Durga Trading Company', 'from_date': '2026-10-01', 'to_date': '2026-10-31', 'start': '2026-09-30'}"
```
Must show:
- `REFUSED`: nobody (October slips are not submitted). If anyone is listed, stop.
- `RETAG`: about 23 people, every line `TIMINGS DIFFER`. Abhishek (HR-EMP-00226)
  `AMBALA - 10:30 AM - 8:30 PM -> AMBALA - 10:00 AM - 7:00 PM`.
- `Not retagged, same timings`: about 7 people.
- `LEFT FOR A PERSON`: days where a punch falls outside the new shift's window. Fix by hand.
- `CANCEL` count, and every `SKIPPED` row with its reason (leave, attendance request,
  confirmed by a manager, made or changed by a person, no linked punches).
- `SHIFTS`: each in-use shift with its current switch, start date and last sync, and a
  `WARNING` if last sync is empty or before 1 Nov.
- `LOUD WARNING`: the number of Absent records the job would create. Check it is
  believable (people with no punches at all on working days). The `of which on
  2026-09-30` number is September: if it is large, use `'start': '2026-10-01'` in steps 2
  and 4 instead.

To check one person first, add `'employees': ['HR-EMP-00226']` (the shift steps still
act on everyone on the shift).

## 3. Pause

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.pause --kwargs "{'company': 'Durga Trading Company', 'from_date': '2026-10-01', 'to_date': '2026-10-31'}"
```
Must show: `pause: N switched off, M were already off`. M should be about 9.
Old values are saved in `sites/dtc.alvoraa.co/alv291_before.json`.

## 4. Set the start date

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.set_start --kwargs "{'company': 'Durga Trading Company', 'from_date': '2026-10-01', 'to_date': '2026-10-31', 'date': '2026-09-30'}"
```
Must show: `process_attendance_after = 2026-09-30 on N shifts`. Last sync is NOT touched.

## 5. Cancel the wrong attendance

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.cancel_wrong --kwargs "{'company': 'Durga Trading Company', 'from_date': '2026-10-01', 'to_date': '2026-10-31'}"
```
Must show: `cancelled` equal to the preview's CANCEL count, `failed 0`.

## 6. Retag the punches

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.retag --kwargs "{'company': 'Durga Trading Company', 'from_date': '2026-10-01', 'to_date': '2026-10-31'}"
```
Must show: `retag: N punches retagged` equal to the preview's RETAG count. No `NOT retagged`
line and no `CHECK` line. To include the 7 same-timing people, add
`'include_same_timings': 1` to steps 2, 5 and 6 alike.

## 7. Switch on and mark

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.enable_and_mark --kwargs "{'company': 'Durga Trading Company', 'from_date': '2026-10-01', 'to_date': '2026-10-31'}"
```
Must show: one line per shift, "Attendance has been marked" or "queued" (above 1,000
punches; needs the worker running, wait a few minutes). No `WARNING: last_sync`. All
shifts stay switched on afterwards (Surbhi's rule).

## 8. Verify

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.verify --kwargs "{'company': 'Durga Trading Company', 'from_date': '2026-10-01', 'to_date': '2026-10-31', 'reds_for': ['HR-EMP-00226']}"
```
Must show: `duplicates 0`, `punches_on_wrong_shift_timings_differ 0`,
`days_punched_no_attendance` 0 apart from the "left for a person" days and skip-flagged
punches, and `reds_HR-EMP-00226` near 2 (the client's figure). The per-day reds before
free reds are taken off. Then check the client's latest sheet: the sheet wins.

## Undo (only if needed)

```
bench --site dtc.alvoraa.co execute alvoraa_portal.alv291_attendance_fix.undo
```
Puts back the shift switches, start dates and old punch tags. It **cannot** un-cancel
attendance: restore the step 1 backup for that. Punches already linked to rebuilt
attendance are listed and left alone; cancel that attendance first, then run undo again.
