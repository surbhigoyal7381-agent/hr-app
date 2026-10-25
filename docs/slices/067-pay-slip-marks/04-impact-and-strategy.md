---
slice: 067-pay-slip-marks
ticket: ALV-208 (red and green money never reaches a DTC payslip)
artifact: impact analysis and strategy (CLAUDE.md section 2, steps 1 and 2)
author: hrms-fullstack-engineer
date: 2026-10-22
status: APPROVED by Surbhi, 22 Oct 2026 ("I go with your recommendations"), relayed by the coordinator. Built locally on 23 Oct; see 03-implementation-notes.md.
code read: origin/dev 747a4293 (includes slice 063)
---

# 067 · Red and green money on the DTC payslip

## 0 · The answer in eight lines

1. **True: nothing calls `push_marks_to_additional_salary`.** Today a DTC slip would carry only
   the engine's paid days, and Basic worked out from them. No Red Value or Green Value line, ever.
2. **The function could not have worked anyway.** It never sets `currency`, which Additional
   Salary requires, so its first insert would fail. It also never updates a figure once written,
   and never removes one that should go to zero. It has never run on a site.
3. **Nobody is wrongly charged by the structure.** DTC's one live structure holds Red Value,
   Green Value, Grooming Red Value and Incentive at **Rs 0** fixed. All four drop off a slip
   when zero. Q2 of slice 066 is already answered: nothing to change.
4. **No Leave Encashment line exists or can appear today**, so there is no double count. Unused
   credits are paid inside paid days, as slice 063 decided.
5. **Recommended: the slip's own save writes the marks as Additional Salary**, in the hook that
   already sets paid days. Replace, never add. Each change leaves a cancelled-and-amended record.
6. **Three things found on the way that touch the same slip** (stale year-to-date, a wrong
   "entered by hand" sentence for the employee, an Arrear trap). They need your yes or no.
7. **Size: small.** One Python file, one test file, two lines in the portal, rehearsal checks.
   About one and a half days, including the rehearsal on synthetic data.
8. **Eight questions for you at the end.** Q1 and Q2 block the build.

---

## 1 · Facts first

### 1.1 What the code does today (origin/dev 747a4293)

| Question | Answer | Evidence |
|---|---|---|
| Does anything call `push_marks_to_additional_salary`? | **No.** The only mention outside its own `def` is its own body. No hook, no test, no script, no Payroll Entry event. | Grep of the whole repo (py, js, json, html). On the server too: the only `doc_events` for payroll are `Salary Slip.validate`. None on Payroll Entry or Additional Salary. No Server Scripts on those doctypes. |
| What runs when a slip is saved? | `payroll_slip.on_salary_slip_validate`, after Frappe's own `validate`. It sets `total_working_days` to the month's length, `payment_days` to the engine's paid days, `absent_days`, then re-runs `calculate_net_pay()`. Nothing else. | `payroll_slip.py` L194-228; `hooks.py` L110-112 |
| How does Basic get its amount? | From the structure: `Basic` = formula `base`, depends on payment days. So Basic = base x paid days / days in month. | DTC structure read on the server |
| How would Red, Green, Grooming, Incentive get an amount? | **Only from Additional Salary**, if anyone made one. The structure rows are fixed Rs 0 with no formula. | Server read |
| How would Leave Encashment get an amount? | It cannot today. `Leave Encashment` (LE) is **not in any structure**. No Leave Type at DTC allows encashment. **0 Leave Encashment documents.** The engine puts unused credits into paid days instead. | Server read; `payroll_month.py` L194-198 |
| How would Arrear get an amount? | Only from Additional Salary typed by HR. Not in the structure. | Server read |
| Has the slip hook ever run on a real slip? | **No.** The file says so ("NOT YET PROVEN ON A SITE"). No test builds a Salary Slip through it. Slice 063's 30 rehearsal checks all call `month_summary`, not a slip. | `payroll_slip.py` L35-36; tests grep; `scripts/seed_rehearsal_063.py` |

### 1.2 What is on DTC (read only, 22 Oct 2026, counts and amounts only)

| Item | Value |
|---|---|
| Frappe / HRMS | 16.35.0 / 17.0.0-dev. **The HRMS payroll files on the server are byte-identical to the copy in this repo** (salary_slip, additional_salary, payroll_entry), so everything below about Frappe's behaviour was read from the code that will run. |
| Our payroll code on the server | **Older than origin/dev**: `payroll_slip.py` and `payroll_month.py` differ (slice 063 is not deployed). |
| Salary Structures | 2. **"DTC Salary Structure"**: submitted, active. **"Standard Salary Structure - Basic Only"**: inactive, every assignment cancelled. |
| DTC Salary Structure rows | Earnings: Basic (formula `base`, by payment days), Green Value **0**, Incentive **0**. Deductions: Red Value **0**, Grooming Red Value **0**, Advance Deduction **0**, Income Tax **0**, Other Deduction **0**. Every one of the 0 rows: fixed, no formula, no condition, not by payment days. |
| Components | 13. All have "remove if zero" on, so a 0 row never shows. **Arrear and Leave Encashment are set to depend on payment days**; Red, Green, Grooming, Incentive, Advance, Other are not. |
| Salary Structure Assignments | 748 in all: **378 submitted** (all on DTC Salary Structure), 370 cancelled. Base from Rs 12,000 to Rs 2,55,000, none zero. Nobody has two live ones. |
| Who sits on the live structure | Active: 297 Permanent Junior, 11 Permanent Senior, 1 Permanent External, 42 Contract. Plus 25 Inactive or Left. |
| **Active employees with no structure** | **94 of 445.** No slip can be made for them at all. |
| Active Permanent staff with **no `dtc_grade`** | **3.** The rule set finds no rate for them, so their reds and greens would cost and pay Rs 0. |
| Salary Slips / Additional Salary / Employee Incentive / Leave Encashment | **0 / 0 / 0 / 0**, ever. One cancelled Payroll Entry. One draft Payroll Period. |
| Rule set "Durga Trading Company" | **Not enabled.** Free reds 2. Mark rates: Junior Rs 100, Senior Rs 200, "No leaves" Rs 0 (and External is not listed, so Rs 0). Contract earns no marks and no credits. Leave classes still hold the **old** accrual values (063's runbook step R-9 not done yet). |
| Payroll Settings | Based on Attendance; unmarked days count as Absent; holidays not in working days. Our hook overrides the day counts anyway. |
| Attendance | 13,089 submitted. **Not one has a red or green stored** (the engine has never judged a day at DTC). This does not matter for the slip: `month_summary` judges every day again when the slip is saved. |

### 1.3 Answers to the six questions

**(1) Does anything call it, and what reaches a slip today?**
Nothing calls it. A slip today would get paid days (worked-day credits plus all leave credits),
absent days, the month's real length as working days, and Basic from those. No other line has an
amount. Red, Green, Grooming and Incentive could only arrive by Additional Salary; nobody makes
one. Leave Encashment cannot arrive at all. Arrear only if HR types one.

**(2) The structure's fixed amounts.** All **Rs 0**. Nobody would be wrongly charged or paid on
the first slip, and zero rows do not even show. No change is needed to the structure, now or for
grooming. (A useful side effect: Frappe only lets an Additional Salary "overwrite the structure
amount" if the component is in the structure. These four are, which is what we want.)

**(3) Where to put the marks.** See section 2. Recommended: Additional Salary, written by the
slip's own save.

**(4) Leave Encashment.** A slip shows the credits **only inside paid days**, not as an earning.
Example from 063: 31 days worked, class A, no leave taken: paid days **35**, working days 31,
Basic = base x 35/31. There is no LE line and nothing can create one at DTC today (no
encashable leave type, LE not in the structure, the portal's Leave Encashment panel needs an
encashable leave type). **So no double count.** The cost: the payslip never says "4 days paid
out". It only shows 35 paid days of 31. That is Q5.

**(5) Rehearsal checks.** Section 6. Note: the runbook cites "07a section 3", but **no file
named 07a exists** in any worktree or branch. The checks below are written to slot in as step
R-5b of `063/07-rehearsal-runbook.md`.

**(6) Grooming (slice 066).** The wiring below takes grooming as one more line in a list of
three. Section 2.4.

---

## 2 · Where the marks go: the options

### 2.1 The five ways

| | Way | Fresh after a fix? | Safe to run twice? | Audit trail | Cost | Verdict |
|---|---|---|---|---|---|---|
| **A** | **The slip's save writes one Additional Salary per line (Red, Green), replacing the old one** | **Yes**: every save works it out again, the same moment paid days are worked out | **Yes**, when the amount is compared first (no change, no write) | **Yes**: a record per person, line and month; a change leaves the old one cancelled and the new one "amended from" it | ~40 lines changed in `payroll_slip.py` | **Recommended** |
| B | A Payroll Entry step writes them for everyone before slips are made | No. A fix after the entry leaves them stale, so A is needed as well | Yes | Yes | A second place doing the same job | Rejected: two places, still needs A |
| C | HR (or a button, or the reprocess) makes them before payroll | No, and it can be forgotten | Depends on the person | Yes | HR time for 351 people each month | Rejected. **Kept as the hand fallback** if the code ever fails |
| D | Structure rows become formulas reading three new fields on the slip, which the hook fills | Yes | Yes | Only the slip's version history | **A formula needs "amount based on formula" ticked, and Frappe does not allow that on a submitted structure** (only formula and condition may change after submit, checked on the server). So: cancel and amend the structure, and re-make 378 assignments. Plus three new fields on every tenant's Salary Slip | Rejected: costs far more than it saves |
| E | The hook writes the amounts straight into the slip's rows | Yes | Fragile | None | Fights Frappe, which rebuilds rows from the structure on every save; gross, tax and totals would need redoing by hand | Rejected |

**Rung on the ladder: 4 (new code in a hook that already exists).** Rung 1 (already there) is
Frappe's Additional Salary itself, which we use. Rung 2 (configuration: HR types Additional
Salary by hand) works with no code, but means 351 entries a month worked out from a report, and
they go stale the moment attendance changes. It stays as the fallback. Rung 3 (a Server Script)
would duplicate code we already have. No new DocType, no new field, no new hook, no job.

### 2.2 How A behaves, case by case

| Case | What happens |
|---|---|
| Slip saved twice | Same figures. The Additional Salary is found, its amount equals the new one, nothing is written. |
| Late attendance fix, or reprocess, then the draft slip is saved again | Paid days and marks are worked out again together. If Red changed: the old Additional Salary is cancelled, a new one is made "amended from" it, and the slip picks up the new one in the same save. |
| Reds fall to the free allowance (2 or fewer) | The old Additional Salary is cancelled. The line disappears. |
| Payroll Entry cancelled and run again | Frappe deletes the draft slips. The Additional Salaries stay. The new slips find them, compare, and keep or replace them. No duplicates. |
| Slip submitted (paid) | The hook does nothing to a submitted slip (unchanged). Frappe refuses to cancel an Additional Salary that a submitted slip uses. The reprocess already skips paid slips. **A paid month is never changed.** |
| Contract staff, External grade, blank grade | Amount is 0, so no record is made. |
| Rule set switched off (the rollback) | The hook does nothing. **Records already made stay and still apply to draft slips.** Rollback therefore gains one step: cancel the month's engine-made records (one list filter, shown in section 5). |
| HR typed an Incentive, Advance or Other Deduction by hand | Untouched. The engine only ever touches records it made (see 2.3). |
| HR typed a Red Value by hand | Untouched by the engine, but the engine's own one is then refused by Frappe as a second "overwrite" for the same month. The slip is saved without the engine's line and an Error Log names it. **Rule for DTC HR: never type Red or Green Value by hand.** |
| Something fails while writing | Undone back to the start of the marks step (a database savepoint), so a slip never ends up with the old line cancelled and no new one. The slip is still saved with its paid days (today's rule: a slip that cannot be made is a person who cannot be paid), gets a visible comment "red and green lines not applied, see Error Log", and the Error Log carries the slip name only. Q3 asks whether you want the slip blocked instead. |
| Two saves at the same moment | Frappe's own check refuses a second "overwrite" record for the same person, line and month. One wins; the other is logged. |
| Mid-month leaver | The record's payroll date is the slip's end date, or the relieving date if earlier, because Frappe refuses a payroll date after relieving. |

**How the engine knows its own records.** Each one it makes carries
`ref_doctype = "Alvoraa Payroll Rule Set"` and `ref_docname = <the rule set>`. These are
standard Additional Salary fields. Frappe only acts on them for Gratuity and Leave Encashment, so
this is safe (checked in `salary_slip.py`). No new field. It also makes the rollback and the
breach-style question "which pay lines did the engine make in October?" one list filter.

### 2.3 Fixes to the existing function (it has never run)

| Bug in `_set_additional_salary` today | Fix |
|---|---|
| No `currency`; Additional Salary requires it; the first insert would fail | Use the slip's own currency |
| Finds a submitted record and returns, **never updating it** (the "update a draft" branch can never be reached, because new records are submitted at once) | Compare; if different, cancel and make an amended one |
| A zero amount only deletes a **draft**; a submitted record stays and keeps charging | Cancel it |
| Matches on exact payroll date | Match any engine-made record dated inside the slip's period |
| Called with no slip, outside any transaction | Called from inside the slip's save, so the slip and its lines are written together or not at all |

`push_marks_to_additional_salary` itself becomes a three-line loop inside the hook. If nothing
else needs it as a separate function (nothing does), it is removed rather than kept unused.

### 2.4 Grooming (066) without rework

The hook walks one short list of `(component, figure from the month summary)`:

```
("Red Value",   red_deduction)
("Green Value", green_earning)
```

Slice 066 adds one row, `("Grooming Red Value", grooming_deduction)`, and the count and price
inside `month_summary` (marks in the period x the same `mark_rates` rate, no free allowance,
zero for Contract). Same record type, same replace rule, same marker, same rollback filter, same
desk report. **Until 066 ships, the engine never touches Grooming Red Value**, so HR can use 066's
stopgap (typing GRV by hand) safely. In the month 066 goes live, HR stops typing it.

---

## 3 · Impact analysis

### 3.1 Functional

| Dimension | Impact |
|---|---|
| Cross-module | `alvoraa_portal` only (`payroll_slip.py`, a new test file, plus the optional portal sentence in `pay_api.py`, `portal.js`, `next-pay.js`). `hrms`: uses Additional Salary and Salary Slip as they are; no change to HRMS source. `erpnext`, `alvoraa_goals`: none. `grace_compensation`: not installed. |
| Callers of changed functions (grep) | `on_salary_slip_validate`: only `hooks.py` L111. `_set_additional_salary`, `push_marks_to_additional_salary`: no callers. `month_summary` (read, not changed): the hook, the desk report, `leave_rules.py`, the seed script, two tests. |
| Other tenants | None. Every path still starts with `rule_set_for(company)`, which is None for every company except DTC, and DTC's is off. |
| HRMS domain | Payroll: two new lines on DTC slips. Attendance and leave: read only, unchanged. |

**Personas**

| Persona | What changes |
|---|---|
| CXO | Payroll totals now include red deductions and green pay, matching DTC's own sheet. Nothing new to read. |
| HR Manager | Red Value and Green Value lines on each draft slip, equal to the desk report's "Red deduction" and "Green pay" columns. One Additional Salary record per person per line per month in the desk, with an amended chain when a figure changed. Must not type Red or Green Value by hand. After a late attendance fix, re-save the draft slip (or cancel and re-run the Payroll Entry), exactly as for paid days today. |
| Employee | Sees Red Value and Green Value on their payslip in the portal. **Today the "Why?" control on such a line would say "This was entered by hand, so there are no days behind it"** (and the heading says "taken off" even on Green Value). That would be false. Q4. |
| Contract staff | Nothing. No marks, no lines. |

### 3.2 Non-functional

| Dimension | Verdict | Why |
|---|---|---|
| Performance | **degrades, slightly** | Per slip: 1 lookup per line (2 now, 3 with grooming), and an insert plus submit (about 15-25 queries) only where a figure is new or changed. Saving an unchanged slip adds 2 small lookups. The 445-slip Payroll Entry already runs in a background job (Frappe enqueues above 30). To be **measured** in the rehearsal with BULK staff, not guessed. No cache, no index. |
| Security | **neutral** | No new endpoint. Records are written with `ignore_permissions` inside a slip save that Frappe has already permission-checked; same as Frappe's own Payroll Entry. Additional Salary is readable only by HR User, HR Manager and System Manager. No input from the client. |
| Reliability | **improves** | Turns a dead, broken function into a tested one. Savepoint means no half-written lines. A failure is visible on the slip, not only in the Error Log. |
| Scalability | **neutral** | Linear in employees, in a background job. Single company. 351 people with a structure today, about 700 records a month at most. |
| Maintainability | **improves** | Removes an unused function and dead branches. One place decides pay lines. Grooming is one row more. |
| Data integrity | **improves** | Lines are written in the same transaction as the slip. Replace, never add. Paid months are never touched. Stale-record risk named (rule set switched off) with its rollback step. |
| Compliance / privacy | **neutral** | No new personal data. Error logs carry the slip name only, never a name or an amount. The amended chain is the audit trail for a pay deduction, which Indian wage law expects. |

### 3.3 Parallel-work check

| File | Who else is in it | Plan |
|---|---|---|
| `payroll_slip.py` | `slice/063-dtc-leave` has two commits on it, but both are already in origin/dev as rebased copies (git cherry shows them as equivalent). Work board: nobody else. | Own worktree `.claude/worktrees/067-pay-slip-marks` on `slice/067-pay-slip-marks` from origin/dev. Fetch before each commit. |
| `pay_api.py`, `portal.js`, `next-pay.js` (only if Q4 is yes) | `portal.js` is a hot file; 066-attendance-decide edits its Attendance Request rows. Different block. | Touch only `renderWhy` (portal.js ~L5904) and next-pay.js ~L228. |
| Slice 066 grooming | Will add one line to the same list and a count in `month_summary`. | 067 lands first (Surbhi's Q1 on 066). |
| Tests | New file `tests/test_pay_slip_marks_067.py`, nobody else's. | Uses `leave_063_fixtures` (read only). |

---

## 4 · Three things found on the same slip (your yes or no)

1. **Year-to-date on every DTC slip will be wrong.** Frappe works out `year_to_date`,
   `month_to_date` and the per-component year-to-date during its own validate, *before* our hook
   changes paid days and net pay. Our hook then changes net pay but does not redo them. **The
   employee portal shows `year_to_date` straight off the slip.** This is true today for paid days
   alone; the marks make it worse. Fix: call Frappe's own three methods once more after our
   recalculation (three lines, same function). **Recommend: yes, in this slice.**
2. **The "Why?" sheet would tell the employee "entered by hand".** See personas. Smallest fix: the
   Why? endpoint returns "worked out from your attendance" for engine-made lines, and the two
   portal screens say: *"Worked out from your attendance this month. Ask HR for the day-by-day
   workings."* One condition in Python, one branch in each of two JS files. A day-by-day red view
   for the employee is **not** in this slice. **Recommend: yes.** (Q4)
3. **Arrear depends on payment days.** If HR types an Arrear as Additional Salary (the planned
   route for released held days), Frappe scales it by paid days / days in month: 35/31 makes it
   13% bigger, 20/31 cuts a third. Fix is configuration only: untick "Depends on Payment Days" on
   the Arrear component in the desk. Not code, not this slice. **Recommend: HR does it before the
   first Arrear.** (Q6)

---

## 5 · Thin steps, in order

**Build (local only, after your approval):**

1. Worktree `067-pay-slip-marks` from origin/dev; work board row.
2. `payroll_slip.py`: in `on_salary_slip_validate`, after setting paid days and **before**
   `doc.calculate_net_pay()`, write the Red and Green lines (2.2, 2.3) under a savepoint; then the
   three year-to-date calls (if Q2 is yes). Rewrite `_set_additional_salary`; fold
   `push_marks_to_additional_salary` into the hook.
3. If Q4 yes: `pay_api.py` one branch; `portal.js` and `next-pay.js` one sentence each.
4. Tests (section 6.1). Run `bench run-tests --app alvoraa_portal` once at the end, on the test
   site, plus the integrity check script.
5. Extend `scripts/seed_rehearsal_063.py` to give the named cases a structure like DTC's
   (Basic `base`; Green, Red, Grooming, Incentive at 0), make a Payroll Entry, and check the
   slip lines (section 6.2). Run on a throwaway local site with BULK=445 for the timing.
6. Review, notes, report. **Stop.** Push to dev only on your word.

**DTC switch-on order (each step on your word):**

| # | Step | Note |
|---|---|---|
| S-1 | Deploy 063 + 067 to dev, then production, **rule set still off** | Hook does nothing at DTC. Zero risk. |
| S-2 | Rehearsal on synthetic data, 063's ten checks plus section 6.2 | You see the cost and the lines. |
| S-3 | 063 runbook R-9 to R-11 (rule set values, Paid Leaves type, approvers) | Desk, by hand. |
| S-4 | Decide the 94 active staff with no structure, and the 3 with no grade (Q7, Q8) | Otherwise they get no slip, or reds at Rs 0. |
| S-5 | Tell DTC HR: never type Red or Green Value by hand | One line in the handover. |
| S-6 | Switch the rule set on | 063 R-12. |
| S-7 | First Payroll Entry for the month; slips stay **draft** | Background job. |
| S-8 | HR compares 5 named slips with the desk report row by row (paid days, Basic, Red, Green, net) | The report uses the same calculation. |
| S-9 | Submit | Paid month is now frozen. |

**Rollback:** untick `enabled`; then in Additional Salary list filter `ref_doctype = Alvoraa
Payroll Rule Set`, payroll date in the month, submitted; select all; cancel. Then cancel and
re-run the Payroll Entry. To be timed in the rehearsal.

---

## 6 · Tests

### 6.1 Automated (new file `test_pay_slip_marks_067.py`, real draft slips on the test site)

Each test names the behaviour, so a bad merge that drops it fails CI.

| # | Test |
|---|---|
| T1 | Junior, 5 reds, 3 greens: slip has Red Value 300 and Green Value 300; equal to the report row |
| T2 | Senior pays Rs 200 a red |
| T3 | 2 reds: no Red Value line and no record |
| T4 | Contract with reds: no lines, no records |
| T5 | Save twice: one record per line, no cancelled ones, same net |
| T6 | A day's reds change, save again: old record cancelled, new one amended from it, slip uses the new amount |
| T7 | Reds fall to 2: record cancelled, line gone |
| T8 | Hand-typed Incentive on the same slip: untouched, still on the slip |
| T9 | Rule set off: hook writes nothing |
| T10 | Forced failure in the marks step: nothing half-written, slip saved with paid days, comment present, Error Log has no name or amount |
| T11 | Paid days on the slip equal the report's; no Leave Encashment line |
| T12 | Year-to-date on the slip equals net pay for a first slip (if Q2 yes) |
| T13 | Submitted slip: its record cannot be cancelled; the hook does nothing |
| T14 | Leaver: payroll date is the relieving date |
| T15 | Why? on an engine-made line says "worked out from your attendance", not "entered by hand" (if Q4 yes) |

### 6.2 Rehearsal checks to add (synthetic DTC-shaped site, as step R-5b)

| # | Check | Pass when |
|---|---|---|
| M-1 | Payroll Entry for all named cases plus BULK=445; slips created | Every slip draft, Error Log empty for "Payroll rules could not price" |
| M-2 | For each named case: slip Red Value, Green Value, paid days, Basic, net **equal** the desk report row | All equal, to the rupee |
| M-3 | Contract and External cases | No Red or Green line, no record |
| M-4 | Save five slips twice | No new records, nothing cancelled |
| M-5 | Back-date one attendance fix that removes a red; reprocess; re-save the slip | One cancelled record, one amended, slip down by Rs 100 |
| M-6 | Cancel the Payroll Entry and run it again | Same records reused, same slips, no duplicates |
| M-7 | Submit one slip; reprocess the month | That slip and its records unchanged; reprocess lists it as skipped |
| M-8 | Leave credits: 31 worked, class A, no leave | Paid days 35, no Leave Encashment line |
| M-9 | Year-to-date and month-to-date on the slip | Equal to the slip's own net for a first slip |
| M-10 | Timing | Payroll Entry slip creation for 445, before and after this change; stated in seconds |
| M-11 | Rollback, timed | Switch off + cancel the month's engine records + re-run: lines gone, paid days back to Frappe's own |

---

## 7 · Risks

| Risk | What happens | Guard |
|---|---|---|
| Hook never proven on a real slip until now | Something in Frappe's slip flow we did not foresee | T1-T15 build real slips; M-1/M-2 on 445 synthetic staff before DTC |
| 94 active staff without a structure | No slip for them; Payroll Entry skips them silently | Q7 before S-6 |
| 3 active staff without a grade | Their reds cost Rs 0, greens pay Rs 0 | Q8 before S-6 |
| HR types Red Value by hand | Engine's line refused for that person; Error Log | S-5 instruction to DTC HR; the Error Log names the slip |
| Rule set switched off with records in place | Old lines stay on draft slips | Rollback step 2, timed in M-11 |
| A late attendance fix after slips are made | Draft slip stays stale until re-saved (true today for paid days) | Runbook line; Q5b offers the fix |
| Marks step fails in production | Slip has paid days but no red or green line | Visible comment, Error Log, S-8 comparison; Q3 offers blocking instead |
| Arrear scaled by paid days | Wrong arrear | Q6, configuration |

---

## 8 · What I would NOT build

- No change to the salary structure or its 378 assignments (the 0 rows are already right).
- No formula-based components, no custom fields on Salary Slip (option D).
- No Payroll Entry hook (option B), no button, no background job of our own.
- No "refresh all draft slips" action in the reprocess unless you ask (Q5b).
- No Leave Encashment line and no split of paid days on the slip unless you ask (Q5a).
- No day-by-day red view for the employee (a separate slice if wanted).
- No grooming code: 066 adds its one row after this lands.
- No configurable component names on the rule set: "Red Value" and "Green Value" stay as named
  constants, because only one tenant uses them. A second tenant with other names is when to move them.

**Subtract pass on this proposal:** removed a Payroll Entry pre-check (A already covers it),
removed a new "engine-made" checkbox on Additional Salary (the standard `ref_doctype` does it),
removed a structure change for GRV (already 0), removed keeping `push_marks_to_additional_salary`
as a separate public function (no caller).

---

## 9 · Size

**Small.** About 40 changed lines in `payroll_slip.py`; 3 lines for year-to-date; about 10 lines
across `pay_api.py`, `portal.js`, `next-pay.js` if Q4 is yes; one test file (about 15 tests,
mostly fixture work); about 60 lines added to the seed script. **About 1.5 days** including the
synthetic rehearsal. No migrate, no new field, no new DocType.

---

## 10 · Questions for Surbhi

**Must know (they block the build):**

| # | Question | My recommendation |
|---|---|---|
| Q1 | Approve option A: the slip's save writes Red and Green Value as Additional Salary, replacing never adding, with a cancelled-and-amended trail? | **Yes** |
| Q2 | Fix year-to-date in the same change (section 4.1)? | **Yes.** The employee sees it. |

**Should know (needed before DTC switch-on, not before the build):**

| # | Question | My recommendation |
|---|---|---|
| Q3 | If the marks step fails, keep saving the slip with a visible warning (today's rule), or refuse the slip so payroll stops? | **Keep saving, with the comment**, plus the S-8 comparison. Refusing one slip stops the whole 445-person batch (Frappe rolls the batch back). |
| Q4 | Change the employee's "Why?" sentence for engine-made lines to "Worked out from your attendance this month. Ask HR for the day-by-day workings."? | **Yes.** Otherwise it says "entered by hand", which is false. |
| Q5a | Should the payslip show unused credits as a separate "Leave Encashment" line (paid days then = days worked + leave used), instead of inside paid days? | **No, not now.** Same money. 063 chose paid days to match DTC's own sheet. Ask DTC if their staff are confused. |
| Q5b | After a reprocess, should draft slips be re-saved automatically? | **No for now.** HR re-saves, or cancels and re-runs the entry. Revisit after the first month. |
| Q6 | Ask DTC HR to untick "Depends on Payment Days" on the **Arrear** component before any arrear is paid? | **Yes.** Configuration only. |
| Q7 | **94 active staff have no salary structure assignment.** Who are they meant to be (new joiners, owners, agency staff paid elsewhere)? | Ask DTC HR for the list's reason before S-6. I have counts only. |
| Q8 | **3 active Permanent staff have no `dtc_grade`.** Set them, or accept Rs 0 marks? | **Set them.** Otherwise their reds are free. |

## Assumptions

- `[ASSUMPTION]` Red Value and Green Value are the only engine-made lines until 066. Incentive,
  Advance Deduction, Other Deduction and Arrear stay HR's, by hand.
- `[ASSUMPTION]` The desk report's figures are what DTC agreed to; the slip must equal them.
- `[ASSUMPTION]` The "07a" file the runbook cites was never written; the checks here stand in for it.
