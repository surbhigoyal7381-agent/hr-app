# ALV-291 third review: commit 742ffe45

**Verdict: SHIP WITH FIXES.** N1, N2 and N3 are fixed. N4 is only half fixed: the
script still writes an Absent on a "left for a person" day that has no attendance.
One new trap: preview's "or undo first" is a dead end. Both are P2. Nothing is P0 or P1.

Reviewed `742ffe45` on top of `fc89205e`, branch `slice/alv-291-attendance-fix`, 3 Nov 2026.
**I ran nothing** (read-only, as asked). Everything below comes from reading the script,
its test and Frappe HR's `shift_type.py` / `employee_checkin.py` in this worktree.

## P2 findings (each needs a fix or Surbhi's written yes)

**F1. A "left for a person" day with no attendance gets an Absent from the script (N4, half fixed).**
The case I traced end to end:
1. Person P is in the list. Punches on 12 Oct are tagged with old shift X (off, so no
   attendance that day). One punch falls outside the window of P's shift T. So 12 Oct is in
   `blocked_days` (`_wrong_punches` line 306).
2. cancel_wrong and retag skip the day (lines 392, 318). Correct.
3. enable_and_mark pass 1 leaves its punches out (line 779). Correct.
4. Pass 2 runs Frappe's `mark_absent_for_dates_with_no_attendance` on T. That function
   **does not look at punches** (`shift_type.py:302-344`). It only skips holidays and days
   with attendance. 12 Oct has none, and P's shift that day is T (line 313).
   So it writes **Absent on a day P badged in**.
5. Preview's LOUD WARNING does not count this day: `_absent_dates` skips any day with a
   punch (line 217). So the count is too low by exactly these days.
6. verify prints the day twice (left_for_a_person and absent_on_days_with_a_punch). But the
   runbook says "The script did not touch them" (line 122). That is wrong.
- **Proven** by reading. The test cannot see it: its blocked day already holds an
  Absent (test line 284), so pass 2 skips it.
- **Closes at 0** if preview's blocked days at DTC all have attendance already.
- **Smallest fix:** in pass 2, wrap `get_dates_for_attendance` on the shift object in memory,
  the same way line 776 wraps `get_assigned_employees`, and drop the blocked days.

**F2. Preview's "or undo first" does not unlock preview. That can push the operator into deleting the undo file.**
Preview refuses while `state["shifts"]` holds anything (line 442). `undo` puts the shifts
back but never empties `state["shifts"]` (lines 909-913). So after undo, preview still
refuses. The only way out is to delete `alv291_before.json`. Step 10 of the runbook makes
that look normal. After retag, deleting the file loses the old punch tags for good.
"Pass employees= the frozen list" fails too once cancel_wrong has run. The list
narrows to people who still have something to fix (line 362-364), so it no longer equals
the frozen list. **Proven** by reading.
- **Smallest fix:** undo empties `state["shifts"]` and `scope` after restoring them, and
  keeps `punches`. Also add one runbook line on how to change the list after pause.

## P3 (ship, tracked)

- **"Pass the numbers the message prints"** (runbook line 147, code line 766). The day count
  outside the list grows every day, because the ceiling is "now". So if step 5 and step 8
  are on different days, step 8 is sure to refuse. The operator then copies the new number
  without seeing the new names. Run preview with the frozen list before step 8 if days have
  passed, and read OUTSIDE THE LIST again.
- **The DROPPED line and runbook line 110 say too much.** "The job will NOT mark their
  October" is true only on shifts that were off. Shifts that were on get their old start
  date back (line 793), so the hourly job still processes October on them. That is how it
  worked before the fix, which is correct, but the wording should say so.
- **The empty-last-sync advice** (runbook line 146) tells the operator to tick "Auto Update
  Last Sync". undo does not save or restore that box. Write the change down.

## Rechecked and cleared

| Item | Result |
|---|---|
| N1 | Fixed. `_outside` names everyone outside the list on shifts that were off, with type and designation (lines 560-566). Half-day rows include them (line 568). Step 8 refuses unless both numbers match (764-767). Tested (lines 309-311, 380-385, 437-439). |
| N2 | Fixed. Only shifts that were off start on 1 Nov (788-790). The rest get their old start date back (791-793). DROPPED is printed (456-464). Tested (lines 314, 426-429). |
| N3 | Fixed. Every refusal (slip, wrong tag, a shift still on, start date, empty last sync, the two numbers) runs before line 773. Tested: no new attendance after the refusals (line 397). Recovery: pause keeps the first saved values (`setdefault`, line 180), so pause → set_start → step 8 works, and `_was_off` reads the saved values. **Inferred**, not run. |
| N4 | Partly fixed. See F1. Cancel and pass 1 are correct. |
| Half-failed step 8 | Safe. Pass 1 and pass 2 commit as they go. A crash leaves the shifts off. A rerun picks only punches with no attendance and days with no attendance. The half-day number may have moved; the refusal shows the new one. **Inferred.** |
| Runbook names and arguments | Match the code: `half_day_rows`, `absent_outside_list`, `left_for_a_person`, the heading "If step 8 refuses". |

## What I could not check

- I ran nothing: no tests, no linters, no site.
- At DTC: how many blocked days have no attendance (that decides F1), and how many people
  are outside the list on the shifts that were off. Preview prints both.
- Subtract pass: I removed a worry that a shift dropping out of the in-use list after retag
  stays off. If no punch carries it, nothing is lost. Nothing else removed.
