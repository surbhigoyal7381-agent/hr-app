# ALV-337 — one punch per scan, and one rule for every shift

Built 13 Nov 2026. Strategy approved by Surbhi the same day, after the read-only
survey of the live DTC site that produced ALV-337.

## What the faults actually were

Three symptoms, one mechanism: **a punch Frappe cannot use disappears in
silence.** The day is then left holding an arrival with no departure, scores 0.0
hours, falls under the 2-hour threshold and is marked Absent. Paid days come from
that status, so every one of these reaches base salary.

| Cause | November 1–12 at DTC |
|---|---|
| No de-duplication where punches arrive | 984 repeats, 168 people, **11% of all 9,072 punches** |
| The 3-hour shift window cuts real work off | 86 punches past the end, 23 across midnight; **74 of the 86 within 30 minutes of the cut-off** |
| Configuration drift across 45 shifts | 8 marking off, 7 with no thresholds, 20 vs 25 split on the hours method |

Evidence the mechanism is right: of the 169 days marked Absent despite two or
more punches, **139 computed exactly 0.0 hours** and **117 had a duplicate pair
within two minutes**.

## What the red and green money does, and why it was never wrong

`payroll_rules_apply._punches` reads Employee Checkin directly and never
`Attendance.working_hours`, collapses duplicates itself, and takes first and
last. So the engine was always immune to all three faults. **What was broken is
Frappe's attendance status, which is the bigger number.** This slice does not
touch the engine.

## The code

### `punch_dedupe.py` — the rule, finally where the punches arrive

`DUPLICATE_PUNCH_MINUTES` has been applied in the pay engine, the day marks and
(since ALV-315) the correction screen. It had never run where punches are
created, so Frappe's own marking job had never seen clean data. One
`before_insert` hook covers every path — the biometric endpoint, the field app,
the Desk form, any script — rather than a guard per caller, so a path added later
cannot arrive unprotected.

The repeat row is **kept** and flagged `skip_auto_attendance`, never deleted. The
device really did send it, so it is evidence HR needs when a day is disputed, and
Frappe's `get_employee_checkins` already filters on that flag. Setting it back to
0 undoes everything, which is why there is no patch and no migration.

**`before_insert` has one deliberate consequence.** It runs before Frappe's
`fetch_shift`, so on a shift set to "Strictly based on Log Type in Employee
Checkin" a repeat read now carries the flag by the time the log-type check runs:
it is kept and ignored instead of being refused outright. A refused punch is
lost, so this is the better outcome. It changes nothing at DTC, where all 45
shifts use alternating entries and no punch carries a log type at all.

**ALV-302 already owned that event, as a single string.** Appending rather than
replacing is the whole of `test_both_before_insert_handlers_are_wired_in_order`:
replacing would have silently dropped the handler that stops a late machine punch
being refiled at the moment it arrived. The order matters too — ALV-302 files an
impossible date first, so such a row is never anybody's anchor.

### `flag_existing` — the step the sequence cannot do without

916 of November's 984 repeats are **already linked to an Attendance row**, and
Frappe never re-reads a linked punch. So flagging them changes nothing a person
would see; the wrong days have to be cancelled and marked again.

That is where this becomes load-bearing. **ALV-291's `cancel_wrong` clears the
skip flag on every punch it frees** (`alv291_attendance_fix.py`, "so the job can
use them"). Freeing November's days and marking them again without flagging the
repeats in between would reproduce the same 169 wrong Absents. So:

```
ALV-291's cancel for November  ->  flag_existing  ->  mark again
```

There is **no default date range** — both dates must be named — so this can never
quietly reach into October, which is ALV-291's. It refuses outright if a
submitted salary slip covers the range: changing what a paid month counted is a
restatement, not a repair, and that is the user's decision.

### `shift_standard.py` — one rule for 45 shifts

A Shift Type should differ from its neighbours **only in its timings**.
Everything else is company policy, and when it varies two people doing the same
thing are paid differently.

| Setting | Standard | Was |
|---|---|---|
| Determine IN/OUT | Alternating entries | already all 45 |
| Hours based on | **First Check-in and Last Check-out** | 20 shifts on "Every Valid" |
| Absent under | 2.0 h | 7 shifts on 0.0 |
| Half day under | 4.5 h | 7 on 0.0, 1 on 6.0 |
| Window | **240 min either side** | 180 on all 45 |

**Four hours, not five.** A window is where data is *captured*, not where policy
is applied; overtime belongs in approval and in the pay rules, and a window that
cuts work off does not prevent overtime, it hides it and then calls the day
absent. Four hours catches 103 of November's 110 orphans. Five catches all 110
and was rejected: five hours either side of a shift ending at 10 PM reaches 3 AM,
and the day somebody holds two shift assignments a punch could be claimed by the
wrong one. The seven punches past four hours are genuinely exceptional and the
correction screen reads them correctly since ALV-315.

**The two fields it never writes are more important than the ones it does.**
`enable_auto_attendance` and `process_attendance_after` belong to ALV-291's
October repair, which switches the paused shifts back on itself from the day
after its period, and refuses to run while any of them is on. If this module
moved either, October would refuse or be re-processed for everybody on that
shift. `test_it_never_touches_the_switch_or_the_start_date` pins that.

Frappe caps shift length plus both windows at 24 hours
(`validate_circular_shift`). A shift that cannot take the standard is reported
and left alone rather than throwing half way through a run. DTC's longest shift
is twelve hours, so four hours each side leaves four hours of headroom.

### The index

One line in `data_review.py`: `("Employee Checkin", ("employee", "time"))`. The
hook asks "has this person a kept punch in the last two minutes" on every insert
— about 9,000 a month at DTC. The employee link index alone narrows to that
person's whole history, which only grows; the pair narrows to the two minutes.

## The order of work, corrected

The plan put to Surbhi had November before October. **That was wrong, and reading
ALV-291's guards is what showed it.** `_refuse_while_enabled` stops `retag` and
`enable_and_mark` while any shift in scope has marking on, and
`enable_and_mark` switches the paused shifts on itself from the day after its
period — which is 1 November, exactly what the config standard wants. So October
already does part of step 4, and doing it first avoids both the collision and the
duplicated work.

1. This code to dev, then main. Nothing touches a tenant.
2. **October, through ALV-291's runbook, unchanged.** Its frozen list of 109
   people is already waiting on the live site.
3. `shift_standard.preview`, read it, then `apply`.
4. ALV-291's cancel for November → `flag_existing` → mark again.

## What this does not do

- It does not fix the 169 existing wrong Absents. Those need step 4. The hook
  protects every punch from now on; it cannot reach back into a linked punch.
- It does not switch the 8 shifts on. October's repair does that itself.
- It does not change the red and green marks. They were never wrong.
- A day already marked keeps the hours it was given, so until a period is marked
  again a month holds some days counted the old way and some the new way.

## Subtract pass

Taken out, or never built:

- **No back-fill module of its own.** `flag_existing` is three short functions in
  `punch_dedupe`, beside the rule they share.
- **No new de-duplication rule.** `DUPLICATE_PUNCH_MINUTES` is imported, not
  restated. `test_repeat_scans_agrees_with_the_pay_engines_helper` pins the two
  together so one day cannot read two ways.
- **No new re-tag tool.** ALV-291's `retag` already re-derives an orphaned
  punch's shift, which is what widening the window needs.
- **No config dashboard and no validation DocType.** `preview` run with nothing
  outstanding prints a clean bill, so it is the drift check as well as the plan.
- **No feature flag.** A setting either matches the standard or it does not.
- **The three downstream collapse calls stay.** They cost nothing and they are
  the only protection for punches already stored.
- **No lock on punch insert.** Two parallel inserts of one scan could both
  survive; every reader collapses duplicates again, so the money is not exposed,
  and a lock on 9,000 inserts a month would cost more than the case is worth.

## Not tested, and said so

`flag_existing`'s refusal when a submitted salary slip covers the range has no
test. Building a submitted Salary Slip needs a structure, an assignment and a
payroll entry, and faking one past the ORM to exercise a two-line read guard
would be a test of the fake. DTC has zero salary slips, so the guard cannot fire
there today. It is read-only and three lines; it is listed here so the gap is on
the record rather than hidden.
