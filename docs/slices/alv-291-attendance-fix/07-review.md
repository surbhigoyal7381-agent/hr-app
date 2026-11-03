# ALV-291 review: one-time October attendance fix for DTC

**Verdict: BLOCK.** One way into the code can cancel a day that a person corrected by hand,
and that cancel cannot be undone safely. The fix is small (a few lines plus one read-only
count). Five Major findings need a fix or Surbhi's written yes before the script touches DTC.

Reviewed: commit `62e9f521` on `slice/alv-291-attendance-fix`, worktree
`.claude/worktrees/alv-291`. Reviewer: hrms-technofunctional-reviewer, 2 Nov 2026.

**What I could not do, said first:**

- **I ran nothing.** This review was read-only. I did not run the test suite or the
  linters, and I queried no site. Every finding comes from reading the code and tracing it.
- **I could not count anything on DTC.** Several findings depend on whether certain rows
  exist there. For each one I name the read-only count that settles it.
- **The slice has no impact analysis, spec, security note or test report.** The folder
  holds only `runbook.md`. The brief (`docs/slices/dtc-attendance-rebuild/01-brief.md`) is
  in the main checkout but not in this commit. The 2 Nov approval reaches me only through
  the task message. So the compliance axis cannot be reviewed against a spec (see section 5b).
- Frappe HR code: `shift_type.py`, `employee_checkin.py` and `attendance.py` are the same
  in this repo's `hrms/`, on `origin/main`, and in the `hrlocal-291` container (same md5).
  That DTC runs this exact code is **inferred** from the 2 Nov release to main. I did not
  check the DTC container.
- Incoming work: the branch has one commit on top of `origin/dev` (`516e24bd`). `dev` is
  not ahead. Nobody else's commit came in. The worktree is clean. **Proven** (git).

---

## 1. Blocker

### B1 (P1). A day corrected by hand as Administrator is cancelled

**Rule broken:** "It must NEVER cancel ... a hand-edited day." Priority rung 1 (loss of a
real decision) and rung 3 (the latest client sheet wins).

**Where:** `alv291_attendance_fix.py:305` and `:294`, `:307`.

The "made by a person" test is `owner` or `modified_by` not equal to `Administrator`
(line 43, line 305). But at DTC, Administrator is not only the scheduler. Bench scripts
run as Administrator (the 16 Oct rebuild was done that way), and so does anyone logged
into the Desk as Administrator. Their corrections look exactly like the scheduler's rows.

**Traced case (I followed this one through the code myself):**

1. State: on 10 Oct, the job marked person E Absent. Somebody then fixed the day by hand
   as Administrator: cancelled the row and made a new Absent (or amended it), because the
   client sheet says E was absent although E badged in.
2. Cancelling the first row ran `Attendance.on_cancel` (`hrms/.../attendance.py:86-87,
   247-262`), which cleared `attendance` on E's punches. The new hand-made row links no
   punches. So E now has an Absent row and an unlinked punch on 10 Oct.
3. `_plan` puts (E, 10 Oct) in `unlinked_days` (lines 277-289). The row is Absent, so
   `absent_badged` is true (line 294).
4. Not paid, no leave, no request, not confirmed (lines 297-304). Owner and modified_by
   are both Administrator, so line 305 does not keep it. Line 307 does not keep it because
   `absent_badged` is true. It goes on the cancel list (line 310).
5. `cancel_wrong` cancels it (line 510). `enable_and_mark` then rebuilds the day from the
   punch as Present or Half Day.
6. Result: the client's correction is gone. `undo` cannot bring it back (line 709). The
   runbook's only way back is a whole-database restore (see M4).

The same hole applies to a correction written with `frappe.db.set_value` on an automatic
row (punches stay linked, `modified_by` stays Administrator): if that day has wrong-tagged
punches, the row is cancelled through `linked` (line 270, line 310). The script also never
reads `amended_from`, which by itself proves a row was corrected.

**Must know before this can drop:** how many October Attendance rows at DTC, submitted,
owner Administrator, have `amended_from` set, or are Absent with no Frappe comment
"Employee was marked Absent due to missing Employee Checkins". If the answer is 0, B1
becomes a Minor. Until someone runs that count, I rank it as a Blocker. **Provisional.**

**Smallest fix (about six lines):**
- Read `amended_from` in `_attendance` and keep any row that has it ("corrected by hand").
- Count a row as `absent_badged` only if it carries Frappe's own automatic-Absent comment
  (one `frappe.get_all("Comment", ...)` over the candidate names). Anything else is a
  person's Absent and is kept.
- In the runbook, pass the 73 employee ids to preview, cancel_wrong and retag (see M3).
  That shrinks the exposure to the people Surbhi approved.

---

## 2. Majors

### M1 (P2). Some people can end up Absent on days they badged in, and `verify` cannot see it

**Where:** `enable_and_mark` lines 591-597, `verify` lines 616-627, and Frappe's
`shift_type.py:222-227, 302-327`, `employee_checkin.py:280-282, 461-465`.

**Traced against the engineer's own test (fixture `SAME`, `test_alv291_attendance_fix.py:221-223`):**

1. `SAME`'s punch on d1 is tagged to shift `A291 Same`. The default shift is `RIGHT`, with
   the same times. Same times means no retag (line 229), and the day has no attendance.
2. `enable_and_mark` handles shifts in name order (line 136 `sorted`). `RIGHT` comes first.
3. After its own punches, `RIGHT` marks Absent for everyone assigned to it
   (`shift_type.py:222-227`). `SAME` has no attendance on `RIGHT` on d1
   (`get_marked_attendance_dates_between` only sees rows on this shift or with no shift,
   `:389`). So Frappe writes an **Absent on d1 for SAME**.
4. Then shift `A291 Same` processes SAME's punch. The new row clashes with the Absent,
   because the times overlap (`attendance.py:147-159`; identical times count as overlapping,
   `shift_assignment.py:185`). That raises `OverlappingShiftAttendanceError`, which is a
   `ValidationError`. Frappe catches it and sets `skip_auto_attendance = 1` on the punches
   (`employee_checkin.py:280-282, 485-491`).
5. Result: SAME is **Absent on a day they worked**, and the punches are now flagged skip.
6. `verify` only counts punches with `skip_auto_attendance = 0` (line 621). So the day
   does not show up in `days_punched_no_attendance`, and the test's `assertEqual(..., 0)`
   at line 302 passes. Nothing asserts what happened to SAME after step 5.

Status: **Inferred** from a full trace; not run. Whether it hits a DTC person depends on
the shift names (which one sorts first) and on whether same-timing-tagged punches sit on
days with no attendance. The cancelled `absent_badged` days (B1) are the most likely place.

**Smallest fix:** in `verify`, report per person "Absent (or no attendance) on a day with
any punch, skip flag or not", and count punches whose skip flag changed during the run.
This is the lesson from slice 028: the check must be able to show the failure.
Then either retag same-timing punches on any day that gets cancelled, or accept this in writing.

### M2 (P2). Switching shifts on marks Absent for everyone on them, and the preview gives a total, not names

**Where:** `set_start` lines 471-494, `enable_and_mark` lines 577-597, `preview` lines 409-433.

- **Proven:** the shift steps act on everyone on the shift, not just the 73. Frappe's
  `_process` calls `get_assigned_employees(process_attendance_after, True)`
  (`shift_type.py:222`): every active person with this default shift or an active
  assignment. For each one, it marks Absent on every working day from the start date to
  the ceiling where there is no attendance (`:302-327, 329-344`).
- So the 44 agency staff with an unknown device id, and the 7 third-party drivers whose
  attendance is kept by hand, get an Absent for every unrecorded October day if their
  shift is one of the ones switched on. The preview prints one total per shift
  (line 424) and one grand total (line 430). It does not name anyone. The brief asked for
  exactly this: "a person with no punches all month ... The preview names them."
- **The 30 Sep warning is right in its mechanism.** Frappe's start is inclusive
  (`shift_type.py:358`), and 30 Sep 2026 is a Wednesday, so a working day. But 30 Sep is
  **September**. The salary-slip guard only looks at 1-31 Oct (lines 103-116, 571). A
  September slip does not stop it. As far as I can see, 1 Oct is enough for day shifts
  (a 10:00 shift with a 3-hour window opens at 07:00 on the same day). 30 Sep adds only
  September writes. **Question for Surbhi:** why 30 Sep and not 1 Oct? If there is no
  night shift reason, 1 Oct is the safer default.
- The preview's count is close to Frappe's logic. It calls Frappe's own
  `get_assigned_employees` and `get_dates_for_attendance` on the shift with the new start
  and ceiling. It counts more than Frappe will (it skips the per-day check
  `get_employee_shift == this shift`, `:311-313`). It counts **less** for a day with a
  punch that will not turn into attendance (case M1). So "upper bound" is not quite true.
- `_ceiling` copies Frappe's rule in `update_last_sync_of_checkin` (`:466-485`) correctly.
  But it is worked out at preview time. If enable runs hours later, the ceiling is later
  and early-November days are added too.

**Smallest fix:** in preview, print each person with more than N new Absent days (id and
name, as everywhere else), and default `start` to 1 Oct unless Surbhi says otherwise.
Then Surbhi accepts the final number in writing before `enable_and_mark`.

### M3 (P2). The cancel step reaches beyond the 73 approved people

**Where:** `_plan` lines 274-295; runbook steps 2, 5, 6 pass no `employees`.

Retag only finds wrong-tagged punches, so it stays near the 30. But `absent_badged`
cancels **any** automatic Absent, for **anyone** in the company, on a day with an unlinked
punch. The approved scope is 73 named people. This rule was not in the approval as the
task describes it, and the tests only cover one fixture case (GRPA). How many people it
reaches at DTC is **not checked**. That is the same count as B1.

**Smallest fix:** pass the 73 ids as `employees` to preview, cancel_wrong and retag in the
runbook. Or ask Surbhi to approve the wider rule with its number.

### M4 (P2). The runbook's undo advice would wipe a live tenant's later data, and two commands do not match the code

**Where:** `runbook.md` lines 18-19, 37-39, 89, 99-101; `undo` lines 677-712.

- "Restore the step 1 backup" means restoring the whole database at a live client. It
  throws away every biometric punch, leave, request and correction made after the
  backup. That is rung 1 data loss, written as the safe path. The cancelled rows still
  exist (docstatus 2). The narrow way back is: cancel the rebuilt row, then **amend** the
  cancelled one. So "cannot be un-cancelled" is not true. It needs a step, not a restore.
- Runbook line 89 says verify must show `punches_on_wrong_shift_timings_differ 0`.
  **There is no such key.** `verify` returns `wrong_tag_unlinked` and
  `wrong_tag_on_kept_days` (lines 656-657). Someone checking the output will not find the line.
- Runbook line 38 says to use `'start': '2026-10-01'` in steps 2 **and 4**. Step 4
  (`set_start`) takes `date`, not `start` (line 471). That one fails loudly with a
  TypeError, so it is safe, but it is wrong.
- Line 91: "The per-day reds before free reds are taken off" is half a sentence. It does
  not say whether the client's "about 2" is before or after the 2 free reds. With
  `free_reds_per_month = 2`, that is the whole difference.
- Nothing risky comes before the backup. **Proven:** step 1 is the backup and step 2 writes nothing.

### M5 (P2). Switching on the shifts that were off also changes old half-day leave days, outside October

**Where:** Frappe `shift_type.py:228, 432-463`, reached from `enable_and_mark` line 594.

For every person on each switched-on shift, `mark_absent_for_half_day_dates` finds
**every** Half Day row with `modify_half_day_status = 1` on or before the ceiling. It has
no start date and no docstatus filter. It sets `half_day_status = "Absent"` with
`db.set_value`. For the roughly 9 shifts that were off, any half-day leave day whose other
half was never processed now becomes Absent for that half, in any month. These are
leave-linked rows (the "never touch" class), it is not in the preview, and `undo` does not
restore it. `leave_rules.py:461-477` reads `half_day_status`.

**Not checked:** whether such rows exist. **Count needed:** Attendance rows with Half Day,
`modify_half_day_status = 1`, for employees whose default shift is one of the shifts that
are now off. If 0, close it.

---

## 3. Minors (P3)

- **m1. Preview and the real step can drift apart.** `cancel_wrong` and `retag` call the
  same `_plan` as preview (lines 334, 504, 536). **Proven:** same code path, so with the
  same arguments and the same data they list the same rows. But nothing checks this.
  Preview runs before `pause`, so the hourly job and live device syncs can change the
  data in between. **Fix:** in the runbook, run preview again after `set_start`, just
  before `cancel_wrong`. Or let `cancel_wrong` take `expected=N` and refuse if the count
  is different.
- **m2. `enable_and_mark` does not check that retag finished.** If `retag` was skipped,
  or left some punches with "NOT retagged", step 5 rebuilds those days on the wrong shift
  again and links the punches. **Fix:** refuse while `_plan(...)["retag"]` still has
  unlinked punches.
- **m3. A target shift that comes only from a Shift Assignment** (not anyone's default,
  and not on any October punch yet) is not paused and not saved in the state file
  (line 119-136). It becomes "in use" only after retag, so `undo` never puts it back.
- **m4. Old shifts kept alive.** Any shift that is only on old punches gets switched on
  for good in step 5 (lines 577-582) under "stays on". Preview lists it, but nobody is
  asked about it.
- **m5. The state file** `sites/<site>/alv291_before.json` keeps per-punch shift times
  with no end date. It is not web-served (**inferred**: it is outside `public/`). Add a
  runbook line to delete it after sign-off.
- **m6. Tests that cannot fail where it matters.**
  - The salary-slip refusal is tested only with `_paid` mocked (test line 246). The real
    query (lines 103-116) never runs in a test.
  - There is no test for a day made by an Attendance Request, a manager-confirmed day, a
    half-day leave with only `leave_type`, an amended row, or a correction made as Administrator (B1).
  - `assertGreater(out["absent"], 0)` (line 237) passes with any wrong positive number.
  - Nothing asserts SAME's attendance after step 5 (M1).
  - The admin-only refusal is tested for 2 of the 8 steps (lines 150-153).
  - The ceiling test (lines 157-174) checks Frappe's behaviour, not the script. That is
    fine as a guard, but it proves nothing about this code.
- **m7. DTC size is not tested.** At about 600 people and about 20,000 punches I expect
  this to be fine. The heavy loops are about 30 people times about 40 punches in
  `_wrong_punches`, and about 600 people times about 6 queries per shift in preview. A
  shift with more than 1,000 unlinked punches is queued (`shift_type.py:155`) and needs
  the worker running. **Not measured.**

## 4. Nits (P4)

- `undo` does not save or restore `overtime_type` or `offshift`, which `fetch_shift`
  changes (`employee_checkin.py:114, 120`; `PUNCH_FIELDS` line 44).
- `state["cancelled"]` gets the same names again on a re-run (line 515). This affects
  the count only.

---

## 4. Requirement check (the 2 Nov list, as given in the task)

| Requirement | Result | Evidence |
|---|---|---|
| Steps run one by one from bench, Administrator only | Met | `_admin()` first in all 8 steps; no `@frappe.whitelist` (grep). **Proven** |
| Preview writes nothing | Met | Only reads; the shift doc is changed in memory and never saved (lines 411-412). Test line 227-231 checks counts and the state file, not Shift Type |
| Pause affected shifts | Met, with gap m3 | lines 452-468 |
| Process Attendance After = 30 Sep, never touch last_sync | Met as written; 30 Sep questioned (M2) | lines 471-494; `last_sync_of_checkin` is never written by the script. **Proven** |
| Cancel before retag | Met and justified | `employee_checkin.py:113` keeps the shift on a linked punch; test line 260 would fail without it. **Proven** |
| enable_and_mark uses Frappe's own update_last_sync then process_auto_attendance | Met | lines 587, 594 |
| verify | Partial | Cannot see Absent-on-a-badged-day (M1); runbook key mismatch (M4) |
| undo | Partial | Shifts and unlinked punch tags only; runbook's way back is unsafe (M4) |
| Scope = 73 people | **Not met as run by the runbook** | `absent_badged` is company-wide (M3); shift steps reach everyone (M2) |
| Never cancel a leave day | Met | `leave_application`, `leave_type` or On Leave are kept (line 299). This covers half day with leave |
| Never cancel a request day | Met | line 301 |
| Never cancel a hand-edited day | **Not met** | B1 |
| Nothing for a person with a submitted overlapping slip | Met for October; not for 30 Sep | lines 297, 316, 571-576; M2 |

## 5. NFR and the seven dimensions

There is no impact analysis to compare with, so the "claimed" column is empty. That gap is itself a finding.

| Dimension | Claimed | What I found |
|---|---|---|
| Performance | none | Fine at DTC size by reasoning (m7). Not measured |
| Security | none | No new door. Not whitelisted; the Administrator check refuses Desk's System Console and Server Scripts (the session user is not Administrator) |
| Reliability | none | Batches commit every 100 with a savepoint per row (lines 508-519). The state file is saved before writes. A crash leaves a consistent state. M1 and m2 are the gaps |
| Scalability | none | One company per site; no queue flood (cancel is synchronous; Attendance has no enqueuing hook, `hooks.py:158-160`) |
| Maintainability | none | Clear, well commented, one file. Proportionate for a one-time job |
| Data integrity | none | B1, M1, M5 |
| Compliance / privacy | none | The console shows id, name and attendance id. The reason "leave" is printed to the operator only. State file retention: m5 |

## 5b. Compliance

**Cannot be reviewed against a spec on this axis:** there is no compliance-impact section
anywhere for this slice. What I can say from the code:

| Obligation | How the code meets it | Test | Result |
|---|---|---|---|
| No bypass of permissions | None in code; `TestSec16` ceiling is 0, counted on code with docstrings removed (`test_portal_security_010.py:986-997`) | ceiling test | Discharged. The ceiling line is honest |
| Direct DB write justified | One: `undo` line 696, with a comment (a save would re-run fetch_shift). Bench only | undo test lines 307-320 | Discharged |
| Personal data accurate before pay decisions (brief's DPDP note) | Preview, then steps | partial | Partial: B1, M1 |
| Log of who changed what | None beyond the state file and console | none | Not discharged. The brief's log was dropped for the one-time route; Surbhi should confirm |

Door I checked myself: I traced `frappe.handler` and the Server Script / System Console
route. Neither can reach a function that is not whitelisted under a user other than
Administrator. `_admin` (line 50) refuses everyone else. **Inferred** from the code; not
run against a site.

## 6. What to delete

Nothing big. The size fits a fix with preview and undo. `include_same_timings` is an
extra option nobody asked for. Keep it only if Surbhi wants the 7 same-timing people
handled (M1 suggests she might).

## 7. What was done well

- Putting cancel before retag, with the reason taken from Frappe's own `fetch_shift`, and
  a test (`still_linked == 4`) that fails if the order is wrong.
- Preview and the real steps share one `_plan`, so preview is not a separate guess.
- Never writing `last_sync_of_checkin` by hand, and letting Frappe's own hourly step move it.
- Saving the old punch tags **before** the first write (line 542).
- `enable_and_mark` refuses outright if any slip is submitted. It fails closed and does
  not warn and carry on.
- Zero bypasses, and the ceiling test entry is real.

## 8. Confidence

- High that B1, M1, M2 (the mechanism) and M5 (the mechanism) happen as described.
  Each is traced line by line through this repo's Frappe HR code.
- Low on how big each one is at DTC. Every size question needs a read-only count I could
  not run: B1/M3 (Administrator-made or amended October rows; Absent rows with an unlinked
  punch, per person), M1 (same-timing-tagged punches on days with no attendance), M2
  (Absent days per person), M5 (half-day rows that are still open).
- Not run: the test suite, linters, any site. I did not check the numbers in the runbook
  (23, 7, 9) or the 73.

## Questions

**Must know (these hold the verdict):**
1. The B1 count. If it is 0, B1 becomes a Minor.
2. M2: Surbhi accepts the per-person Absent list in writing, and says whether it is 30 Sep or 1 Oct.

**Should know:**
3. M3: is `absent_badged` meant to cover the whole company, or only the 73?
4. M5 count.

Subtract pass: I removed four findings I could not turn into a real failure. They were:
a worry about queue flooding on cancel (there is no enqueue), the ceiling-test count
(docstrings are stripped), half-day leave being cancelled (`leave_type` keeps it), and
retag changing `log_type` or device (`fetch_shift` does not touch them).
