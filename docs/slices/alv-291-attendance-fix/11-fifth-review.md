# ALV-291 fifth review: commits 74c7adeb and fb4d12c5

**Verdict: SHIP WITH FIXES.** All my findings that were meant to close are closed, including
the block (B1). **But the B1 fix adds one new fault (N1): a person who worked the other half
of a half-day leave can now have that half marked Absent.** It takes about two lines. Fix it
before the script runs at DTC. Nothing is P0 or P1.

**What I could not do:** I ran no tests and touched no site. Only `ruff` and a Python compile
ran, both clean. I have no DTC data. I cannot confirm the test suite passes on `fb4d12c5`.
Everything below is from reading the code, and is **proven by reading, not run**, unless it
says otherwise.

## New fault

### N1 (P2, fix before running). The other half of a half-day leave is marked Absent on a day the person badged in

**Where:** `enable_and_mark`, the new `blocked` line (the kept days added for B1).

1. Person P has a half-day leave on 14 Oct: status Half Day, `leave_type` set,
   `modify_half_day_status = 1` (`leave_application.py:371`). P worked the other half, so
   there is an unused punch.
2. `_plan` puts the row in `skipped`, reason "leave". That is correct.
3. The new line adds every `skipped` day to `blocked`, so **pass 1 now leaves P's punches out**.
   Before this commit, pass 1 sent them to Frappe, which sets the other half to Present
   (`employee_checkin.py:298-312`).
4. Pass 2 runs `mark_absent_for_half_day_dates`, which has no date or punch check. It sets
   `half_day_status = Absent` and `modify_half_day_status = 0` (`shift_type.py:448-452`).
5. The hourly job cannot repair it later, because the row is no longer open.

**Why it is wrong:** a half the person worked counts as Absent, and pay follows. Undo does not
reverse it. Preview's `HALF-DAY ROWS` lists the row, but only as "may set to Absent", and the
same list holds the rows with no punch. The test has no such fixture.

**Size:** at most the rows for listed people in `HALF-DAY ROWS` that have an unused punch. Open
rows like this should mostly be on shifts that were off. **Not checked at DTC.**

**Smallest fix:** add `modify_half_day_status` to the `_attendance` fields, and leave those rows
out of the set added to `blocked`:
`{... for a in plan["skipped"] if not a.modify_half_day_status}`.
Add a fixture: an open half-day leave row with two punches, and assert the other half is Present.

## Are the findings closed?

| Finding | Status | Evidence |
|---|---|---|
| **B1** step 8 stuck | **Closed**, but see N1 | Step 8 uses `_plan`'s retag list, the same as retag. TYP fixture would fail without it |
| **F1** dates and outcome | **Closed** | One line per date with predicted status, hours and shift. Test compares all 8 with the real rebuild. One-punch, no-threshold days are now left for a person |
| **F2** declined request | **Closed** for a day with a row | `_declined_days`, DEC fixture. See question 2 for Waiting |
| **F3** left-for-a-person day cancelled | **Closed** | Flagged punches now count in `blocked`, before any cancel. FLG fixture |
| **F4** twin minute | **Closed** | An import's copy no longer counts. Of two Frappe flags in a minute, one clears. BDG4 now fails without the fix, because the shifts have thresholds |
| **F5** verify blind | **Closed** | `cancelled_no_row_now`, with a test that makes one |
| **F6** wording | **Closed**. The rule stays Surbhi's | Reason and runbook changed. The ALV-211 off-shift days are still only visible in verify |
| m1 no-punch number | Closed | `badged_people or [""]`, tested |
| m2 PEOPLE wording | Closed | Preview text |
| m3 undo count | Closed | `NOT flagged again` line. Runbook still says "Undo flags them again" (see below) |
| m4 preview after step 8 | Closed | People already fixed stay on the frozen list, tested |
| m5 cross-midnight days | **Open, P3** | Not changed. Harm is low; status does not change |
| m6 retag count | Closed | "at most N" printed |
| No log of who changed what | **Open**, Surbhi's call | Carried from 07 |
| Test faults | Closed | Thresholds added, exact ceiling value, Administrator Present fixture |

## Smaller new points (P3)

- **The `PLUS` line is wrong for a one-punch day.** It says the hourly job will mark Absent. On a
  shift that was on, with an unflagged punch, the job marks **Present** (question 1).
- **"Left for a person" says "no full Present", but a shift with a half-day threshold and no Absent
  threshold gives Half Day.** This errs on the safe side, only the words are off.
- **A declined request on a day with no row does not protect it.** The script builds the day from
  the punches. Rare, because the job normally writes an Absent there.
- **The two switches** (`ONE_PUNCH_LEFT_FOR_A_PERSON`, `REBUILD_ABSENT_WITH_UNUSED_PUNCH`) are fine
  for a pending decision in a one-time script. Delete the unused branch once Surbhi decides.

## Question 1: a left-for-a-person day with no row, on a shift already on

**No, it is not worse than today. It is the same behaviour.**

- Step 8 gives that shift back its old switch and start date. It does not change the punch: same
  shift tag, same flag. The last sync in the database is not moved, because the ceiling is only in
  memory. So the hourly job sees what it would have seen if the script had never run.
- If the job could mark that day today, it already would have, and there would be a row. So this
  day can only exist in rare cases, such as a punch that arrived during the pause. **Inferred.**
- If the start date is later than the day, or the punch is flagged, the job will not make a Present
  from it, now or before.
- The script's own passes skip the day, so the script adds no Present.

**What is wrong is the promise, not the behaviour.** The runbook says "The script leaves these days
alone. HR fixes each by hand". It should add: "On a shift that was already on, the hourly job may
mark the day first, as it does today, so check the row before you fix it." With that and the `PLUS`
wording, this can be closed. Accepting it needs no code.

## Question 2: a Waiting request does not protect its day

**Risk: low, but one line closes it, so I recommend closing it.**

- **If HR later approves:** safe. Frappe updates the rebuilt row (`attendance_request.py:165-170`).
- **If HR later declines:** the rebuilt row stays. Two real punches make it Present, so HR's "no"
  changes nothing, and nobody is told. This is F2 in the other order. It needs HR to decline a day
  with real punches, so it should be rare.
- **Number that settles it:** Waiting requests whose dates cover a row on the CANCEL list.

**Smallest fix:** one filter in `_declined_days`, and new words for the reason:

```python
"alvoraa_review_status": ("not in", ["Approved", "Withdrawn"])
```

Reason: "HR declined a request for this day, or has not decided yet". `not in` also catches a request
that was never labelled, which the code comment in `attendance_correction.py` says still counts as
waiting. **Cost:** those days stay as they are until HR decides. They are in HR's queue already, and
are listed as SKIPPED. Add one Waiting fixture.

## Is the runbook followable by a non-programmer?

**Yes, once four small wording changes are made.** The steps, numbers and refusals now match the
code, and step 8's stuck case has an entry.

1. **Step 6: "Undo flags them again."** Add: "except punches already used by rebuilt attendance".
2. **"One switch changes it."** A non-programmer cannot flip it: it is a code change and a deploy.
   Say: "Surbhi decides before step 2. If she does not, the default stands."
3. **"Fix by hand" is not explained** (lines 49, 72, 162, 169). Say once: "by Attendance Request".
4. **Line 3 says Surbhi runs every step. Line 32 says "have Surbhi approve it".** Use one voice.

Also add question 1's sentence, and N1's change makes the half-day warning true again.

## Still open for Surbhi

1. Fix N1 (no decision needed).
2. Close Waiting? I recommend yes.
3. Do the two defaults stand: one-punch days left for a person, and an Absent holding a punch kept?
4. Were October's ALV-211 late out-punch days re-marked? If not, they stay Absent after this run.

**Subtract pass:** I removed a worry that the prediction breaks on "Strictly based on Log Type" (no DTC
shift uses it, per the 12 Oct note), and one that verify could misreport after a list change (only
over-reports, the safe way).
