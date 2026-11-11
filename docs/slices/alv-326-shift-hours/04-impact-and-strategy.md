# ALV-326 - Only shift hours count, a break allowance, and a late limit

Impact analysis and strategy (CLAUDE.md §2 steps 1 and 2). **Approved by Surbhi on
2026-11-11 (D1)**, with her later decisions the same day:

- D2: the 11:00-11:30 late window is cleared on DTC's rule set by Surbhi herself; no
  code change to ATT-04.
- D3: lateness is judged in whole minutes.
- Late up to the limit and leaving a little early (no-quarter red band) stays 2 reds.
- **Nothing company-specific in code or in the repository** (§3).

Branch `slice/alv-326-shift-hours`, worktree `.claude/worktrees/alv-326`, from `origin/dev`
814d540f. Revision 4, after the review and security review (2026-11-11).

**No real attendance is in this document** (security review B1). Every example below is
invented. The comparison against DTC's real days lives outside git
(`grace-ops/step29-alv326-dtc-november-match.py`).

---

## 0. Bad news first

1. **Releasing needs a migrate on every site** (two DocType JSON changes), then a build
   and the `sites/assets/assets.json` version bump for `portal.js`.
2. **Whole minutes change re-processed results for any tenant with an enabled rule set**
   (D3). A punch a few seconds past grace was late and is now on time; two punches 2 min
   59 s apart now merge into one; each day's percent can move by up to a minute, so a
   day on a band edge can change band. Nothing stored moves by itself; only a re-process
   changes it.
3. **"No red where a quarter is already cut" no longer holds for a late arrival** when
   the late rule is on: late and leaving early is a quarter and a red, as DTC asked.
4. **3 of DTC's 57 comparable days still differ** - all on punch data (their machine and
   ours hold different punches), not on rules.

## 1. The rule for one day

Each rule is a setting, off by default; with all three off the arithmetic is the old one.

1. **Arrival.** `late = first punch - shift start`, whole minutes. Within the grace in
   force (category, then shift, then rule set): no charge. With the late rule on: past
   grace up to the limit = 1 red; beyond it = 1 quarter, no red.
2. **Time.** With shift hours only: counted from the shift start (within grace) or the
   real first punch (past it), to the earlier of the last punch and the shift end.
   Otherwise first punch to last, capped at 100%. Breaks (gap 2-3, 4-5, ...) over the
   allowance are deducted; none on an odd punch count.
3. **Band** (the 12-row table, unchanged) gives quarters and a band red.
4. **Combine** (`charge_for`, shared with the banner): within grace or rule off, the band
   alone; late red, the band's quarters and one red (a band red is the same red); late
   quarter, the larger of 1 and the band's quarters, no red. The two-red rule stands.
   The reasons say plainly when the late rule changes the band's red (security M2).
5. **Unchanged:** doubling (the late quarter is never doubled), absent, leave, half-day
   leave, one punch held, greens and the late window from the real punches.

Invented worked examples (shift 08:30-18:30, grace 6, limit 30, allowance 40):

| In / out | Result | Why |
|---|---|---|
| 08:35 / 18:30 | nothing | within grace, counts from 08:30 |
| 08:44 / 18:30 | 1 red | 14 late; the band red is the same red |
| 09:05 / 18:40 | 1 quarter | 35 late; staying late does not help |
| 10:40 / 17:00 | 2 quarters | 63%: the band charges more than the late quarter |
| 08:50 / 16:10 | 1 quarter, 1 red | late and early |
| 08:30, 12:30, 13:30, 18:30 | 1 red | 60-minute break, 20 over, 96.7% |

## 2. Callers and copies

One judge: `payroll_rules.evaluate_day`, reached through `payroll_rules_apply.judge` by
the payslip, re-processing, the Salary Workings report and the ALV-291 verify step.
`leave_rules` reads only the punch count. The banner (`day_marks`) asks the engine
through `day_rules_on` for greens, grace (category first), whether the person earns
marks and the three settings, and costs every band through `charge_for`, so it cannot
disagree with the payslip (review P2-1). Break clipping and the starting point are
still written in both `payroll_rules` and `day_marks` (review P3-3, tracked).

## 3. Config, not code - decided by Surbhi, 2026-11-11

| Where | Field | Default (today's behaviour) |
|---|---|---|
| Alvoraa Payroll Rule Set | Count Only Time Inside Shift Hours (Check) | off |
| Alvoraa Payroll Rule Set | Late Minutes Before A Quarter (Int) | 0, no late rule |
| Alvoraa Payroll Rule Set | Break Allowance (Minutes) (Int) | 0, no break rule |
| Alvoraa Employee Category row | the same two Int fields | 0, use the rule set's |

Save refuses negatives, and refuses a late limit at or below the grace in force on the
rule set and on each category row (security M1). No patch: new columns take 0. Each
company's values are set on its own rule set; DTC's go on through an ops script kept
outside the repository (`grace-ops/step28-alv326-dtc-settings.py`), which prints only
unless `DRY_RUN=False`.

## 4. The home banner (invented: shift 10:30-20:30, grace 6, limit 30)

- **20 minutes late (10:50):** "Arriving by 11:00 costs 1 red." Leave at or after 19:50:
  no pay lost; leaving 19:50-20:29 is a second red (two-red rule); 17:20 to 19:50 a
  quarter. No rung after 20:30.
- **40 minutes late (11:10):** "Arriving after 11:00 costs a quarter of a day and no red.
  Staying late does not win it back." Leave at or after 17:40: a quarter; 15:10 to 17:40
  half a day.
- **Staff who earn no marks** see their own grace and no red at all.

## 5. The seven dimensions

| Dimension | Verdict |
|---|---|
| Performance | Neutral: no new query; the banner asks once where it asked once before. |
| Security | Neutral: no endpoint, no permission change; rule-set writers unchanged. |
| Reliability | Improves slightly: a missing mid-day punch never costs a break; bad limits refused at save. |
| Scalability | Neutral. |
| Maintainability | Improves: figures are data; one `charge_for` for payslip and banner. |
| Data integrity | **Degrades slightly for re-processed months**: whole minutes (D3) change some results for any enabled rule set. Nothing stored changes until a re-process. |
| Compliance / privacy | Neutral in code. The test data is invented; the real comparison stays outside git. Security M3 (staff cannot read the "why" text themselves) is Surbhi's decision. |

## 6. Tests

Invented days only: `test_shift_hours_alv326.py` (one rule per day, plus each rule on
its own, the two-red rule, doubling, no-marks staff, the window off and on, half-day
leave, and a class proving a rule set with none of the settings is unchanged);
`test_payroll_flags.py` (defaults, overrides, validation, and a real Employee Checkin at
10:36:40 proving whole minutes); `test_day_marks.py` (the banner with the settings on,
and a contract category). The owning suites are listed in the notes.

## 7. Switch-on and past months

On deploy with the rule set off, only the report preview and the banner can change. At
switch-on, set the values and clear the late window in the same step; switch on from the
first month with every punch and re-process that month once. Do not re-process months
paid outside the portal. The muster upload must stop for days that already have every
punch, or its rows make fake gaps.

## 8. DevOps view (mine; the DevOps agent has not reviewed it)

Two DocType JSON changes, so a **migrate on every site**; then a **build** and the
**`assets.json` bump** for `portal.js`. Code that lands before the migrate reads the
settings as off, so the order is safe. Rollback: revert; the new columns are harmless
left in place. The one live data change is the rule-set values, run by Surbhi.

## 9. Open

- Security M3 (self-service access to the "why" text): Surbhi's decision.
- Review P3-3 (two copies of the clipping rule): tracked, not blocking.

## Subtract pass

Removed in this revision: every real day, date and employee ID; the per-day comparison
table (now only its totals); the October evidence figures, which were measured before
the late rule and are out of date.
