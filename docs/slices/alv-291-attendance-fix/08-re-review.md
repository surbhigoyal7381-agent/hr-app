# ALV-291 re-review: the fixes in fc89205e

**Verdict: SHIP WITH FIXES.** The Blocker (B1) is fixed, and so are most of the five Majors.
But the two new behaviours open four new P2 gaps. Each one needs a small fix or Surbhi's
written yes before the script runs at DTC. Nothing found is P0 or P1.

Reviewed: `fc89205e` on top of `62e9f521`, branch `slice/alv-291-attendance-fix`, worktree
`.claude/worktrees/alv-291`. Reviewer: hrms-technofunctional-reviewer, 3 Nov 2026.

**What I could not do, said first:**

- **I ran nothing.** No tests, no linters, no site. This was read-only, as asked. Every
  finding comes from reading this script and Frappe HR's code in `hrms/` in this worktree.
- **I counted nothing at DTC.** Three of the new findings only matter if certain rows or
  settings exist there. For each, I name the number that settles it. Most are already
  printed by preview.
- I did not fetch `origin/dev`. By the local copy, the branch is `62e9f521` + `fc89205e`
  on top of `516e24bd`. No one else's commit came in. **Proven** (git log).
- There is still no impact analysis, spec or security note for this slice. The
  compliance axis stays unreviewable against a spec, as in 07.

---

## 1. Previous findings, checked against the code

| # | Status | Evidence |
|---|---|---|
| **B1** hand fixes cancelled | **Fixed** | `_plan` lines 337-365. A row is cancelled only if it holds the job's punches (`linked`), or it is an Absent with Frappe's own comment (`auto_absent`, lines 331-335). Amended rows (line 345), rows changed more than 5 minutes after they were made (line 355) and Absents with no comment ("not proven to be automatic", line 363) are kept, even as Administrator. Test rows FIXADM, AMEND, HANDABS, REQ, CONF (test lines 233-265, 327-329). **Proven** by reading. I checked that the Alvoraa verdict writer does not move `modified` (`payroll_rules_apply.py:444`, `update_modified=False`), so it does not make every row look "changed". |
| **M1** Absent on a badged day | **Fixed** | Pass 1 = punches on every shift, pass 2 = Absent days (lines 672-685). I traced it: in pass 2, Frappe's `mark_attendance` catches the overlap error and writes nothing (`attendance.py:368-370`), so no punch is flagged. New keys `absent_on_days_with_a_punch` and `skip_flagged_punches_on_absent_days` exist (lines 757-758). Test SAME asserts Present and flags 0 (lines 366-368). **Proven** by reading. |
| **M2** preview names, 1 Oct | **Fixed, one gap** | Every person with Absent days is printed with type and designation (lines 481-486). `START = "2026-10-01"` (line 43). The count matches the job in the test (line 352). **Gap (m-a below):** it is not exact for a person with a Shift Assignment. |
| **M3** frozen list | **Fixed, with a new gap** | `_scope` refuses without a list for the same company and period (lines 91-97). cancel_wrong, retag, enable_and_mark and verify use it. `_process` sees only the list: logs filtered (line 681), assigned people replaced (lines 679-680). **But** the shifts are then switched on for everyone (see N1, N2). "Refuses when it differs" only checks company and dates, not the people. A new preview simply replaces the list. |
| **M4** runbook | **Fixed** | `date` for set_start, `half_day_rows`, the verify keys, the undo wording (cancel, then Amend), the restore as last resort, and reds "before the 2 free reds" all match the code. The slip rule "reds minus 2, never below 0" matches `payroll_month.py:252`. **Proven.** Two lines over-promise; see m-c and m-d. |
| **M5** half-day rows | **Partly fixed** | Counted for the list only (lines 203-213, 661-664). Frappe's hourly job does the same thing to **everyone** on a shift once it is on (N1). |
| m1 cancel count drift | Fixed | lines 574-576, tested (lines 316-320) |
| m2 retag not finished | Fixed | lines 657-660, tested (line 336) |
| m3 assignment-only shifts | Fixed | `_target_shifts` lines 145-150. Not tested |
| m4 old shifts switched on | Fixed | line 696, tested (line 370) |
| m5 state file | Fixed | runbook step 10. Not web-served: nginx only maps `/assets` and `/files` (`deploy/nginx.conf:211, 222`). **Proven** |
| m6 tests | Fixed | real Salary Slip query (line 294), admin-only on all 8 steps (lines 168-178), the kept-row cases, SAME |
| m7 size | Not measured | Calling `_process` directly also avoids Frappe's queue above 1,000 punches |
| Nits | Fixed | `offshift`, `overtime_type` saved (line 53); no repeat names in `cancelled` (line 587) |

---

## 2. New findings (P2 - each needs a fix or a written yes)

### N1 (P2). Switching the off shifts on marks November Absent, and changes half-day rows, for everyone on them, not only the 73

**Where:** `enable_and_mark` lines 689-697, and Frappe `shift_type.py:222-228, 432-463`.

- Inputs: one of the about 9 shifts that were off before the fix. Agency staff or drivers
  on it whose attendance is kept by hand, usually at month end.
- What happens: line 693 switches it on with start 1 Nov. From the next hourly run,
  Frappe marks Absent for **every** active person on that shift, on every November working
  day with no attendance so far (`shift_type.py:222-227`, start = `process_attendance_after`,
  line 358). When HR later enters those days by hand, Frappe refuses them as duplicates
  until someone cancels the Absent.
- Same run: `mark_absent_for_half_day_dates` (lines 432-463) has **no start date**. For
  everyone on that shift it sets the other half of any open half-day leave row, any month,
  to Absent. Moving the start to 1 Nov does not stop this. Preview counts these rows only
  for the 73 (line 488), so `half_day_rows=N` does not cover them.
- Why it is wrong: these are people outside the approved scope. Preview does not show them.
  `undo` does not reverse the half-day change.
- **Inferred** from a full trace. Not run.
- **Count that settles it:** for the shifts that were off at pause (from the state file),
  how many active people, and how many open half-day rows (`status = Half Day`,
  `modify_half_day_status = 1`) they have. If the people are all tracked by device and the
  rows are 0, close it.
- **Smallest fix:** in preview, for each shift that is off now and will be switched on,
  print the people on it who are not in the list, and their open half-day rows. Count those
  rows into `half_day_rows` too. Then Surbhi accepts it in writing.

### N2 (P2). The 1 Nov start means the job never marks a late October punch again, for anyone

**Where:** line 694. Frappe takes only punches with `time >= process_attendance_after`
(`shift_type.py:258`).

**This is the case I traced end to end:**

1. State: person Q has default shift G, one of the shifts that was off. Q has punches on
   5 Oct, no attendance. Preview without a list finds 74 people, Q among them.
2. The runbook says: not 73, so run preview again with the 73 approved ids (line 29).
   `_derive_people` uses only those ids (line 311). Q is dropped. **Preview does not print
   who was dropped.**
3. pause, set_start: G is in use, so it is paused and set to 1 Oct.
4. enable_and_mark pass 1: logs are filtered to the list (line 681), so Q's punches are
   skipped. Pass 2: Q is filtered out (line 680).
5. Switch on: G gets `enable_auto_attendance = 1` and start `max("2026-11-01", old)` = 1 Nov.
6. Every later hourly run asks for punches from 1 Nov. Q's 5 Oct punches are never picked.
   `verify` checks only the 73, so it does not show Q either.
7. Result: Q's October days stay empty. With 62e9f521's start date the job would have
   marked them. **Inferred** from the code path above; not run.

The same applies to any October punch that arrives **after** enable_and_mark, for anyone:
a device that syncs late, a punch HR adds by hand, or a wrong October day HR cancels so
the job can redo it. Before the fix, a shift that was already on would have picked these
up. Now nothing does, and nobody is told. (HR can still fix the day with an Attendance
Request or by hand.)

The next day's marking is fine. From November the hourly job works as before, **if** the
shift's last sync moves. Frappe only moves it when `auto_update_last_sync` is ticked
(`shift_type.py:468-471`). November punches are not lost.

**Smallest fix (pick one; I recommend both small parts):**
- Use 1 Nov only for shifts that were **off** before pause. For shifts that were on, put
  back their old start date, as `undo` would. Frappe had already worked through October on
  those, so this puts back exactly what was there before. That is one condition on line 694
  (`old.get("enable_auto_attendance")`).
- When `employees` is passed, preview prints the people it found but left out, with a line
  saying the job will not mark their October.
- And one runbook line: after step 8, an October punch is no longer marked by the job;
  fix October days with an Attendance Request.

### N3 (P2). A shift that is skipped is still switched on, and then the retry is refused

**Where:** lines 676-678 print `SKIPPED` and carry on. Lines 689-697 then switch the shift
on with start 1 Nov. Line 666 refuses every later run because shifts are on.

- Inputs: a shift with an empty last sync and `auto_update_last_sync` off. Preview prints a
  WARNING for it, but nothing stops the run.
- What happens: its October punches for the 73 are not marked. The shift is switched on
  from 1 Nov, so the hourly job never reaches them either (N2). A second run is refused.
- Why it is wrong: this is warn-and-carry-on on a step that cannot be repeated. The way out
  is pause, then set_start, then fix the last sync, then enable_and_mark again. That does
  work (pause keeps the first saved values, because `setdefault` keeps the old ones), but
  **the runbook does not say so.**
- Any other failure is safe. I checked this. If marking or a save fails, `bench execute`
  does not commit, so the switch-on is lost and the shifts stay off. Each pass already
  committed is safe to run again, because Frappe only picks unlinked punches and unmarked
  days. So a retry is allowed and works. **Inferred** from `_process` (`shift_type.py:218-231`)
  and the single commit on line 698.
- **Smallest fix:** refuse before pass 1 if any shift would be skipped (move the check on
  lines 675-678 above the loop and `throw`). Add a runbook section: "If step 8 refuses, or a
  verify count is wrong after it: pause, set_start, then step 8 again. Pass the half-day
  number the refusal prints. Do not run preview again: it would change the list."

### N4 (P2, closes at 0). A day "left for a person" is still changed by the script

**Where:** `_plan` line 340; `enable_and_mark` pass 1, line 673 (all in-use shifts).

- Inputs: preview prints a day under `LEFT FOR A PERSON` (a punch would fall outside the new
  shift's window). Its punches keep the old tag and stay unlinked.
- What happens:
  - If that day has Frappe's automatic Absent, `absent_badged` is true and nothing checks
    `blocked_days`, so cancel_wrong **cancels it**.
  - Pass 1 then runs the old shift too (it is "in use"), and Frappe marks the day from
    those punches **on the old, wrong shift**.
  - `verify` filters these days out of `wrong_tag_*` (`_wrong_punches` line 269), so they
    do not show.
- Why it is wrong: the screen promises a person will decide, and the runbook's verify line
  allows for those days being empty. In fact they get a day worked out against the wrong
  timings, which is the fault this script exists to fix.
- **Inferred**; there is no test fixture for it.
- **It closes at 0:** if preview's `blocked_days` total is 0 at DTC, this does not happen.
- **Smallest fix:** in `_plan`, skip any day in `blocked_days`. In pass 1, leave out punches
  on those days.

---

## 3. Minors (P3)

- **m-a. The preview's Absent count is exact only when no one has a Shift Assignment.**
  Preview counts every date from `get_dates_for_attendance` (line 474). Frappe also checks
  each day that this shift is the person's shift that day (`shift_type.py:311-313`). So a
  person with a default shift and an assignment on another shift is counted twice.
  Preview shows too many, never too few. The test has no assignment, so it cannot see this.
- **m-b. enable_and_mark does not check the start date.** If set_start was skipped, or run
  with a different date, pass 2 marks Absent from whatever start date the shift has
  (perhaps September). Preview's numbers then do not match. Fix: refuse if any shift's
  start date is not `scope["start"]`.
- **m-c. Runbook line 91 says "the hourly job never reaches anyone else's October".** Not
  quite. Shifts that are not switched on but were on before keep 1 Oct (line 696 puts back
  only the switch). Half-day rows are changed for any month (N1).
- **m-d. Runbook line 101 expects Absent-with-a-punch only on kept hand-made days.** Frappe
  also marks Absent when someone worked fewer hours than the shift's minimum
  (`shift_type.py:291`). Those days show here too, and they are correct. Say so.
- **m-e. Global `undo` after step 8 re-opens October.** It puts back the old start dates and
  switches. The hourly job then marks the restored, wrong-tagged punches again. That is the
  meaning of undo, but the runbook should say it.
- **m-f. Thin tests:** no Half Day fixture, so `half_day_rows` is never tested with a value
  above 0, or with a wrong value. No assignment fixture. No `blocked_days` fixture. The
  names in the Absent list are not asserted, only the count. `[ASSUMPTION]` The comment
  match (line 333) assumes the site is in English. Frappe stores the translated text.

---

## 4. Do the tests fail without each fix? (by reading, not running)

| Fix | Would the test fail without it? |
|---|---|
| B1 | Yes. Without the comment check, HANDABS is cancelled (line 329). Without `amended_from`, AMEND is cancelled. Without the 5-minute rule, FIXADM is cancelled (line 327) |
| M1 | Yes. With the passes swapped, SAME is Absent and its punches are flagged (lines 366-368) |
| M2 | Count: yes (line 352 compares the real Absent rows with preview). Names: no, nothing checks them |
| M3 | Yes. The outsider would get Absent rows (line 355); the list is compared exactly (line 281) |
| M5 refusal | Yes for "no number given" (line 346). Not tested with a wrong number above 0 |
| cancel count drift | Yes (lines 316-320) |
| retag not finished | Yes (line 336; at that point the only refusal that can fire is the retag one) |
| salary slip | Yes, with the real query now (lines 294-299) |
| second run refused | Yes (line 373) |
| start moved to 1 Nov | Yes (lines 371-372) |
| N1-N4 | No test covers them |

---

## 5. Requirement check

| Requirement | Result |
|---|---|
| Never cancel a hand fix, an amended row, a hand-made Absent | Met (B1) |
| Scope = the 73 | Met for what the script writes. **Not met** for what the switched-on shifts then do (N1) |
| Preview names everyone who gets Absent days | Met for the 73. Not for people outside the list on newly switched-on shifts (N1) |
| Count matches the job | Met in the test; too high with assignments (m-a) |
| Half-day rows acknowledged | Met for the 73 (N1 for the rest) |
| Safe to repeat / undo | Met, except the skipped-shift case (N3) |

Seven dimensions, after the fix: performance fine by reading; security unchanged (no
whitelist, Administrator only, state file not served); reliability better, except N3;
data integrity better, except N2 and N4; privacy unchanged. There is still no impact
analysis to compare with.

## 6. What to delete

Nothing. `CHANGED_AFTER_SECONDS` and the comment check each carry part of B1.

## 7. What was done well

- The proof of "made by the job" is positive evidence, not a guess. Holding the job's
  punches, or Frappe's own comment, is the right rule.
- Two passes, with the reason in the code, and a test that fails if the order is wrong.
- The list is frozen in the file, and every writing step reads it, not a fresh guess.
- The verify keys can now show the failure the first review found.
- The runbook's undo is now the narrow one, with the restore marked as dangerous.

## 8. Confidence

- High that N1, N2 and N4 happen as written: traced line by line through this repo's
  Frappe HR code. Medium on N3's recovery path: read, not run.
- Low on size at DTC. The numbers that settle it: people and open half-day rows on the
  shifts that were off (N1); how many people preview finds before the 73 ids are passed
  (N2); shifts with an empty last sync and no auto-update (N3); preview's `blocked_days` (N4).
- Not run: tests, linters, any site.

## Questions

**Must know:**
1. N1: does Surbhi accept that switching on the off shifts marks November Absent and
   changes half-day rows for everyone on them? If not, preview must list them first.
2. N2: does she accept that October punches are never marked by the job after step 8?
   I recommend keeping the old start date on shifts that were already on.

**Should know:**
3. Does preview find exactly 73 people without an `employees` list? If yes, N2's first case
   does not arise. The late-punch case still does.

Subtract pass: I removed a worry about `max()` on date strings (they are always
`YYYY-MM-DD`, so the comparison is right), and one about the switch-on being half
saved (one commit, so a failure saves none of it). I removed nothing else.
