---
slice: 063-dtc-leave-credit-and-lwp
artifact: 01d-half-day-addendum
author: hrms-product-manager
date: 2026-10-21
status: draft — recommendation only, waiting for Surbhi
amends: 01-product-brief.md §2 (half-day row), §9, §14, decision D4
inputs: Surbhi's correction of 21 Oct 2026; payroll_rules.py, payroll_rules_apply.py, payroll_month.py, payroll_slip.py, payroll_reprocess.py; tests test_payroll_rules.py, test_payroll_month.py; hrms leave_application.py, attendance.json, leave_application.json (read in worktree 060-manager-review)
---

# 063 addendum · A half day of leave counts as leave

**Surbhi's rule (21 Oct 2026):** "even the half day is accounted for as a leave." Everything in slice 063 is for DTC only.

**Bad news first.**

1. **This changes how the pay engine works out pay, not just what a screen shows.** Today the engine treats a half-day leave as a short working day. That is the opposite of the rule. Confirmed in code: the engine treats a day as leave only when the attendance status is "On Leave" (`payroll_rules_apply.py` line 399). Frappe records a half-day leave as "Half Day", so the engine measures it by punches.
2. **The correct rule can pay some people one credit less than today.** In a 30-day month, a class A employee who works 29 days and takes one half day of leave has attended 29.5 days. That earns 3 credits, not 4, because 4 credits need 30 days (4 × 7.5). Today the same person counts as 30 days attended and earns 4. A full day of leave already works this way. The half day now follows the same rule. See D2.
3. **Nothing live is affected yet.** The DTC rule set is still switched off, so no DTC payslip uses the engine today. The change must be proven in a rehearsal before the rule set is switched on.
4. **Brief D4 is withdrawn.** I had recommended hiding the half-day option at DTC. With this rule the option stays.

---

## 1 · The rule I recommend for a half-day leave

| Question | Recommended rule | Why |
|---|---|---|
| How much leave does it count? | **0.5 day.** | Surbhi's rule. Frappe already counts it as 0.5 (`total_leave_days`; tested in `test_leave.py::test_apply_half_day_leave_costs_half_a_day`). |
| Is the other half measured by punches? | **Yes.** Measure the minutes worked against **half the shift**, not the whole shift. | Paying the other half without measuring it would make a half-day leave plus one hour's work the cheapest day there is. Measuring it against the whole shift gives about 50% and charges the leave half as missing time, which is what goes wrong today. |
| Quarters lost on the worked half? | **Use the same slab table on that half-shift percentage, and lose at most 2 quarters.** A half day is worth 2 quarters, so it can never cost more than itself. | One table, no new rates to keep. |
| Red mark on the worked half? | **Only from the slab**, as on any day. **No late-arrival or early-departure judgement and no late-window quarter.** | Frappe does not record which half was taken. Someone with the morning off arrives "late" by design, and someone with the afternoon off leaves "early" by design. Judging either would charge the leave itself. |
| Green marks? | **None on a half-day leave day.** | Greens reward coming early or staying late on a full shift. Without knowing which half was taken, an early arrival cannot be judged fairly. This is a policy choice: D4. |
| No punches at all on a half-day leave day? | **0.5 leave, and the other half is absent.** On a special day that half is charged double: half an extra day lost. | It matches how a full absence is treated (WSD-04). Holding the day would wait on a manager for a day that is not in doubt. |
| Toward the 15-day gate and the credits earned? | **0.5 day attended.** | The same principle the engine already applies to a full leave day ("a leave day is not a day worked", `test_payroll_month.py` line 138). Counting a half-day leave as a full attended day would let leave earn the credit that pays for it. |
| Day pay | Worked half: 0.5 minus a quarter of a day for each quarter lost. Leave half: 0, paid from credits at month level, as a full leave day is today. | Same pattern as `day_credit` for a full leave day. |

**Credits by class (unchanged rates, now with half days):** A earns 1 per 7.5 days attended, up to 4. B earns 1 per 10, up to 3. C earns 0.5 per 7.5, up to 2. All need at least 15 days attended. With half days, attended days can be fractions: 14.5 is under the gate, and 15 meets it.

**Worked example (class A, 30-day month):** 29 full days worked plus one half-day leave where the person works their half fully.

| | Today (wrong) | Recommended |
|---|---|---|
| Attended days | 30 | 29.5 |
| Credits earned | 4 | 3 |
| Leave used from credits | 0 | 0.5 |
| To be paid out | 4 | 2.5 |
| Day pay | 29 + 0.5 (two quarters lost) | 29 + 0.5 |
| Red mark | Possibly 1 (slab under 50–75%) | None |
| **Paid days** | **33.5** | **32.5** |

In a 31-day month the attended days stop counting at 30, so the person in this example would still earn 4.

**What the card shows for a half day:**
- **Used:** 0.5, with the date and the word "half day".
- **Waiting:** 0.5 for a half-day request not yet approved. This comes from Frappe's `total_leave_days`, which is already 0.5.
- **To be paid out:** credits earned minus leave used. It can end in .5, as class C already can.

## 2 · Leave without pay half days, and the "5-day limit"

**The half day is the same rule.** The engine does not look at the leave type, so an LWP half day counts as 0.5 leave. Credits cover it first and anything beyond them is unpaid, exactly as for a full LWP day. Nothing extra is needed.

**⚠ The 5-day limit contradicts the brief.** On 21 Oct Surbhi said LWP has "no limit". This request mentions a 5-day limit. I have not seen her words for it. **Open question O1.**

If the limit is real, there are two ways to read it:
- **"No more than 5 days in a row."** This is configuration: set "Max Continuous Days Allowed" = 5 on the leave type. Frappe checks it against the request's day count, so a half day should count as 0.5. **Needs validation:** I did not trace how Frappe adds up joined requests that include a half day.
- **"No more than 5 days in a month."** Frappe has no setting for a monthly cap on unpaid leave. It would be new code: one check when someone applies, counting approved and pending requests in the month, with half = 0.5.

I recommend the first if a limit is wanted. It costs nothing to build.

## 3 · What must change, and which tests notice

**How Frappe records a half-day leave (confirmed in `leave_application.py` lines 341–374 and the doctype files):**
- **Leave Application:** `half_day` = 1 and `half_day_date`. There is **no field for which half** (morning or afternoon) in this Frappe version.
- **Attendance on approval:** status "Half Day", with `leave_type` and `leave_application` filled in. If no attendance exists for that day, `half_day_status` is "Present". If an Absent day already exists, Frappe rewrites it to Half Day directly and sets `modify_half_day_status` = 1, without running our attendance hook.
- **⚠ "Half Day" also happens without any leave.** A shift with a half-day hours threshold marks a short day "Half Day" by itself (`working_hours_threshold_for_half_day` appears in `test_day_marks.py`). So the status alone does not prove leave.

**So the engine must not rely on the status alone. It also does not need to read the Leave Application.** The test is: status "Half Day" **and** `leave_application` (or `leave_type`) filled on the attendance. Frappe writes those fields itself. A short day with no leave behind it keeps today's treatment.

| Where | Change |
|---|---|
| `payroll_rules.py`, `evaluate_day` and `DayVerdict` | A new input, "half-day leave". When set: 0.5 on leave; the other half measured against half the shift; quarters capped at 2; no late, early or late-window charge; no greens; no punches means the half is absent. `day_credit` follows. |
| `payroll_rules_apply.py`, `judge` | Pass the half-day-leave flag from the attendance (status "Half Day" plus `leave_application`). |
| The three places that read Attendance for the engine: `payroll_slip.month_summary` (fields list), `evaluate_attendance`, `payroll_reprocess.py` (fields list at line 62) | Add `leave_application` (and `leave_type`) to the fields read. Without this, `judge` never sees the flag. |
| `payroll_month.summarise_month` | Count days in halves: a half-day leave adds 0.5 to days worked and 0.5 to days on leave. These counters become decimals. The 15-day gate and the credit rule already take decimals. |
| `payroll_slip.on_salary_slip_validate` | **No change.** It already writes the engine's paid days and absent days. Check that `absent_days` copes with a half. |
| Report *Salary Components and Workings* | **No change** to its logic. Its "Worked" and "On leave" columns are whole numbers and must show halves. |
| Portal (slice 063 card) | Shows 0.5 values from `month_summary`. Keeps the half-day box in the Apply pop-up. No logic of its own. |

**Tests that encode the old behaviour:** none directly. I searched the tests for "Half Day" and `marked_on_leave`. No engine test feeds a half-day attendance to the engine. The full-day leave tests (`test_payroll_rules.py` lines 313–334; `test_payroll_month.py` lines 118–155) should keep passing, because `assertEqual(20, 20.0)` passes. **Needs validation:** the engineer should run the suite once to confirm nothing compares the counters by type.

**New tests needed:**
- A half-day leave with the worked half complete.
- A half-day leave with the worked half short.
- A half-day leave with no punches, on a normal day and on a special day.
- A "Half Day" with no leave behind it, which must behave as today.
- 29.5 days attended in a 30-day month.
- A half day just under and on the 15-day gate.
- Class C with a half day.
- A half-day LWP, which must give the same answer as any half-day leave.

**Risk to DTC:** none live today, because the rule set is off. Once it is on, a mistake here moves pay for anyone who takes a half day.

**What the rehearsal must prove**, on a local copy of DTC data with the rule set switched on there only:
1. A half-day leave, approved through the portal, gives 0.5 leave and no red, late or early charge.
2. An automatic "Half Day" with no leave behind it is judged exactly as before.
3. The month figures for 5 named staff with half days match a hand calculation, including the 30-day example above.
4. Slip paid days equal the report's paid days, and saving the slip twice gives the same answer.
5. An Absent day later changed by a half-day leave is judged correctly when the slip is saved, even though the attendance hook did not run.
6. A half-day LWP behaves the same as any half-day leave.

## 4 · Decisions only Surbhi can make

| # | Question | My recommendation |
|---|---|---|
| D1 | On a half-day leave, is the other half measured by punches, or paid in full? | **Measured against half the shift, losing at most 2 quarters.** |
| D2 | A half-day leave counts as 0.5 day attended. In a 30-day month that can drop a class A person from 4 credits to 3 (example above). Accept? | **Accept.** A full leave day already works this way. Treating halves differently would make two half days cheaper than one full day. |
| D3 | On a half-day leave, should late arrival, early leaving and the late window be ignored? | **Yes, ignore them.** Frappe does not record which half was taken, so either could be the leave itself. Red marks come only from the slab. |
| D4 | Can someone earn a green mark on a half-day leave day? | **No.** |
| D5 | Half-day leave with no punches at all: is the other half absent (doubled on a special day)? | **Yes.** |
| D6 | Is there a 5-day limit on leave without pay? If yes, is it 5 days in a row, or 5 days in a month? | **Only if you want one; "in a row" if so.** That is a setting on the leave type. A monthly cap needs new code. |
| D7 | Should staff choose "first half" or "second half" when applying? | **Not now.** Frappe has no such field, and the rules above do not need it. |

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| O1 | Where does the 5-day limit come from? Surbhi earlier said "no limit". | Surbhi | The LWP setup |
| O2 | DTC's slab table: does it raise a red at about 50%? This sets how much today's wrong treatment costs, and how a short worked half is charged. | Engineer (read the rule set) | The size of the change shown to Surbhi |
| O3 | Do any DTC shifts mark "Half Day" automatically from hours worked? | Engineer (read Shift Types) | How common the "Half Day without leave" case is |
| O4 | Does Frappe's consecutive-days check count a half day as 0.5? | Engineer | D6, if "in a row" is chosen |

## Assumptions

- `[ASSUMPTION]` The DTC rule set is still switched off, as the coordinator states.
- `[ASSUMPTION]` Frappe always fills `leave_application` on attendance it creates or rewrites for a leave. It does in `create_or_update_attendance`. Attendance typed by hand as "Half Day" with a leave type, but with no application, is treated as leave only if `leave_type` is filled. The engineer should pick one field and test it.
- `[ASSUMPTION]` "Half the shift" means half the shift's own length, the same measure the engine already uses for a full day (ATT-01).

## Subtract pass

Removed: a first-half/second-half choice (D7: not needed), a separate slab table for half days (the existing one with a 2-quarter cap does the job), a hook on Leave Application to judge the day again (the slip judges it again anyway; only the stored daily verdict goes stale, and no portal screen reads it), and reading the Leave Application from the engine (the attendance already carries the link).

## Handoff note

To the engineer: this is a pay-rule change inside the engine. Decide half-day leave from the attendance (status "Half Day" plus the leave link), never from the status alone. Every number on the card must still come from `month_summary`. Prove it in the rehearsal before anyone switches the DTC rule set on.
