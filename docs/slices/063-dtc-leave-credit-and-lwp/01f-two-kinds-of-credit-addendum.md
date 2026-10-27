---
slice: 063-dtc-leave-credit-and-lwp
artifact: 01f-two-kinds-of-credit-addendum
author: hrms-product-manager
date: 2026-10-24
status: draft — recommendation only, waiting for Surbhi
amends: 01e-credit-at-start-of-month-addendum.md (now applies to office staff only)
inputs: Surbhi's message of 24 Oct 2026; payroll_slip.month_summary (lines 75-148), payroll_month.summarise_month (158-175), payroll_rules.leave_credits_for_month (201+), payroll_rules_apply.py (DOUBLE_YES line 36), alvoraa_payroll_rule_set.json, 067 impact notes (employment types, grades); read in worktree 067-pay-slip-marks
---

# 063 addendum · Two kinds of leave credit at DTC

**Surbhi, 24 Oct 2026:** ground staff earn their leave "after they completed a duration to earn that leave". Every other employee gets the whole month's leave credited on the 1st. The leave class (A, B, C and the zero classes) still decides how many days each person can get in a month.

**Bad news first.**

1. **I could not read DTC production.** This agent has no shell, so it cannot run the SSH command. Part 1 below names the fields to check, and §1.2 gives a read-only script to run. **Until the script is run, I do not know whether any existing field tells ground staff from office staff.** What I do know from the repo:
   - `employment_type` holds only "Permanent" and "Contract" (067 impact notes). That is not ground versus office.
   - `dtc_grade` is a pay-rate grade for red and green marks.
   - `dtc_leave_class` is the class.
   - None of the three is the ground/office split.
2. **What slice 063 built is right for office staff only.** If the DTC rule set were switched on as built, **every ground-staff person who misses days would be paid too much.** Example: a class A ground-staff person with 20 days attended would get 4 credits instead of 2. The rule set is still off, so nothing is live. **It must not be switched on until ground staff are marked.**
3. **The two kinds cannot both be set up as configuration of today's rule set.** The flat credit was set up through the rule set's own settings, not code (01e §3). It needs the "accrual month" setting at 15 days. Ground staff need it at 30 days. That setting covers the whole rule set, not each class, so one rule set cannot hold both. A small code change is needed (§2).

---

## What "completed a duration" most likely means

**The evidence points to days attended, not length of service.** The engine's own wording of DTC's rule, settled with Surbhi on 9 Oct, is "one credit per **completed period** of attendance" (`payroll_rules.py` line 210):
- class A: 1 per 7.5 days attended
- class B: 1 per 10
- class C: 0.5 per 7.5

Her phrase "after they completed a duration to earn that leave" matches it closely.

Nothing in the repo mentions a service-length rule for leave, such as "after 3 months". **Needs validation with DTC** (Q1).

---

## 1 · How the product tells ground staff from office staff

### 1.1 Recommendation (cost ladder)

| Rung | Option | Verdict |
|---|---|---|
| Already there | An existing Employee field that separates them cleanly (department, designation or branch) | **Use it if the script shows a clean split.** The rule set would then need a list of which values mean "ground", and that list must be kept up to date. That costs more than a single tick. |
| Configuration | Reuse `employment_type` with a new value | **Rejected.** It is a standard field already used by the contract rules, the doubling rule and the categories table. A third value would change those rules too. |
| Configuration | Split the classes into "A Ground" and "A Office" | **Rejected.** Surbhi said the class stays the single source of eligibility. It also does not get round the accrual-month problem. |
| **Customisation + small code** | **One Employee tick box at DTC, "Ground staff" (`dtc_ground_staff`).** The rule set names it in a new field, the same pattern the rule set already uses for other per-person fields. | **Recommended** unless the script finds a clean existing field. One field, one meaning, set from DTC's sheet. |

**Default for an unticked box:** office (credited on the 1st). That is the direction that overpays, so the rehearsal must prove that every ground-staff person is ticked before switch-on (§5).

### 1.2 The read-only check to run on DTC (counts only, no names)

Run it as briefed: `docker exec -i compose-backend-1 … python -I -`. It reads and counts only.

```python
import frappe
frappe.init(site="dtc.alvoraa.co"); frappe.connect()
act = {"status": "Active"}
def counts(f):
    return frappe.db.sql(f"select ifnull(`{f}`,'(blank)') v, count(*) n from tabEmployee where status='Active' group by v order by n desc", as_dict=1)
for f in ("employment_type", "dtc_leave_class", "dtc_grade", "department", "designation", "branch"):
    rows = counts(f)
    print(f, "distinct:", len(rows), "top:", [(r.v, r.n) for r in rows[:12]])
print("custom fields:", frappe.get_all("Custom Field", filters={"dt": "Employee", "fieldname": ["like", "%"]},
      fields=["fieldname", "fieldtype"], limit_page_length=0))
frappe.destroy()
```

**What to look for:**
- A department or designation set where every active A/B/C person falls cleanly into "ground" or "not ground".
- Any custom field whose name contains ground, office, field, category or staff.

The custom-field list prints every field name. Read it for those words. Department and designation values are job labels, not personal data.

## 2 · What changes

| Part | Change | Rung |
|---|---|---|
| Employee (DTC only) | Custom field `dtc_ground_staff` (tick box), set from DTC's list by one import | Customisation |
| Rule set | New field "Field marking staff who earn leave by attendance". It is read the way the rule set already reads per-person yes/no fields: "Yes" or "1" means yes (`DOUBLE_YES`). Put `accrual_month_days` back to **30**. Put the class rows back to **7.5 / 1 / 4, 10 / 1 / 3, 7.5 / 0.5 / 2**. `monthly_credits` (4 / 3 / 2) stays: it is the office figure and the ground cap. | New field |
| `payroll_rules.leave_credits_for_month` | One added input, "earned by attendance". **Yes**: the current calculation, unchanged. **No**: the class figure if the 15-day minimum is met, otherwise 0. | New code, about 5 lines |
| `payroll_month.summarise_month` | Passes the input through. Adds a note to the desk report's "Why" column: "Ground staff: earned by attendance" or "Credited on the 1st". | New code, small |
| `payroll_slip.month_summary` | Reads the named Employee field with the class field and passes it on | New code, small |
| Desk report *Salary Components and Workings* | **No column change.** The "Why" note says which kind applied. | — |
| Card and Leave page | Two versions (§3). The office version is the one built. The ground version brings back prototype v2's "earned so far" drawing. | New code, small |
| Hindi and English strings | Office strings stay. Ground strings: v2's accrual strings (H-3, H-4), plus one new "next credit" line. | Words |
| Prototype v3 | Add the ground-staff card states: day 1, under 15 days, day 20, full month. The designer can reuse v2's accrual card. | Design |
| Spec parity table | Rows R-3 to R-12 and R-34 split into "office" (01e wording, built) and "ground" (v2 wording). §7.5 card keys gain `earns_by_attendance`, plus `days_attended`, `earned`, `next_credit_at` for ground. §7.7 reads the new rule-set field. | Analyst |
| Security file (01c) | Data inventory gains "ground staff yes/no", a job fact of low sensitivity. Only HR may change it. The card shows a person only their own. No new threat. | Security |

**Tests and rehearsal checks that change:**
- **Fixtures.** The 063 test fixtures and rehearsal scripts set the flat credit through `accrual_month_days` 15 with 15-day blocks. Those settings go back to the 7.5-day blocks. Files: `leave_063_fixtures.py` (3 places), `test_leave_063_engine.py` (2), `scripts/rehearsal_063.py` (9), `test_pay_slip_marks_067.py` and `scripts/rehearsal_067.py` (fixtures). Each office-staff case then relies on the new flat path, not on the settings trick. **The expected figures do not change.**
- **The 30/30 rehearsal checks** stay as the office-staff checks. Ground-staff checks are added in §5.
- **The accrual tests** in `test_payroll_rules.py` (lines 495-583) are correct again for ground staff. Only their wording needs "ground staff" added.

## 3 · The card for each kind

**Office staff, class A** (as built):

| | 1 Oct | 20 Oct (18 attended, 1 used, 1 waiting) |
|---|---|---|
| Paid Leaves this month | 4 credited | 4 credited |
| Used / waiting / to be paid out | 0 / 0 / 4 | 1 / 1 / 2 |
| Line | "These count once you have attended 15 days in October. You have attended 0 so far." | — |

**Ground staff, class A:**

| | 1 Oct | 20 Oct (18 attended, 1 used, 1 waiting) |
|---|---|---|
| Earned so far | 0 of up to 4 | 2 of up to 4 |
| Used / waiting / to be paid out | 0 / 0 / 0 | 1 / 1 / 0 |
| Line | "You earn 1 day for every 7.5 days you attend, once you reach 15 days. You have attended 0." | "Your next day is earned at 22.5 days: 3.5 more." (18 attended + 1 approved Paid Leaves day = 19, under E6) |

**The "next" figure comes from the engine.** The card asks `leave_credits_for_month` at the next half-day steps until the number rises, at most 60 steps. It is never worked out a second way.

Approved Paid Leaves days count toward the days the card shows; that is decision E6 (see G2). The words should say "days attended, counting your approved Paid Leaves".

## 4 · Pay effect

**Method.** The engine's own sum: paid days = day pay + credits. Daily rate = Basic ÷ 31 for October. **₹23,000 is the engine tests' example Basic, not a DTC salary**, giving ₹741.94 a day. "Absent" means the missed days had no approved Paid Leaves.

| Class | Month | Ground staff credits | Office staff credits | Office gets more by |
|---|---|---|---|---|
| A | 31 attended | 4 | 4 | — |
| A | 28 attended + 3 Paid Leaves | 4 (E6 counts the 3) | 4 | — |
| A | 28 attended, 3 absent | 3 | 4 | 1 day, ₹741.94 |
| A | 20 attended | 2 | 4 | 2 days, ₹1,483.87 |
| A | 15 attended | 2 | 4 | 2 days, ₹1,483.87 |
| A | 14 attended | 0 | 0 | — |
| B | 28 attended, 3 absent | 2 | 3 | 1 day, ₹741.94 |
| B | 15 attended | 1 | 3 | 2 days, ₹1,483.87 |
| C | 28 attended, 3 absent | 1.5 | 2 | 0.5 day, ₹370.97 |
| C | 15 attended | 1 | 2 | 1 day, ₹741.94 |

- **Against what is built today** (flat for everyone), ground staff get less whenever they are absent without approved leave.
- **Against the 9 Oct rule**, ground staff get the same or more, because E6 now counts approved Paid Leaves days.
- **Evidence required:** how many active staff are ground staff, and October's attendance, to give a total. The rehearsal works it out from the desk report.

## 5 · Decisions only Surbhi can make

| # | Question | My recommendation |
|---|---|---|
| G1 | Does "completed a duration" mean days attended (1 per 7.5 days for A) or length of service (for example, after 3 months)? | **Days attended.** It is the rule DTC gave on 9 Oct, in the engine's own words. Please confirm with DTC. |
| G2 | For ground staff, do approved Paid Leaves days count toward the days that earn credits, as E6 already does for the 15-day minimum? | **Yes.** It is already built, and taking your own leave properly should never cost leave. |
| G3 | Do ground staff also need the 15-day minimum? | **Yes.** It was part of their 9 Oct rule. |
| G4 | Someone moves from ground staff to office staff, or back, mid-month. Which rule applies? | **The tick as it stands when the month's slip is worked out applies to the whole month.** HR changes the tick only on the 1st. |
| G5 | Do new joiners wait before earning? | **No extra wait.** The 15-day minimum already means a late joiner earns nothing in their first month. |
| G6 | Who sets the ground-staff tick, and who may change it? | **DTC's HR, on the Employee record.** Every change shows in the Employee's change history (**Needs validation** that change tracking is on for Employee at DTC). One import from DTC's own list sets it first. |
| G7 | Unticked means office (credited on the 1st). Accept, given it overpays if someone is missed? | **Accept, with the rehearsal gate below.** |
| G8 | If the script finds a department or designation that cleanly marks ground staff, use that instead of a new tick? | **Only if it is clean for every active A/B/C person**, and HR agrees to keep it exact. |

**What the rehearsal must prove** (a local copy of DTC data, never production):
1. The rule set saves with the 7.5 / 10-day blocks, a 30-day accrual month and the new field.
2. Office staff: the existing 30 checks give the same figures through the flat path.
3. Ground staff: class A gives 0 at 14 days, 2 at 15, 3 at 22.5 (with a half day), 4 at 30. B and C match the table in §4.
4. One ground-staff person with 28 attended plus 3 Paid Leaves earns 4 (G2).
5. The card's "next" figure equals the engine's.
6. The desk report's "Why" names the kind for every row.
7. **Count of active A/B/C staff by tick: none left to chance.** Surbhi or HR confirms the ticked count equals DTC's own ground-staff count.
8. Slip paid days equal the report's paid days for both kinds.

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| Q1 | G1, confirmed with DTC | Surbhi | The ground-staff rule |
| Q2 | Run the §1.2 count script on DTC | Coordinator (an agent with a shell) | The choice of identifier (G8) |
| Q3 | DTC's own list of ground staff | Surbhi / DTC HR | Setting the tick |
| Q4 | Is change tracking on for Employee at DTC? | Engineer | G6 audit |

## Assumptions

- `[ASSUMPTION]` "Other employees" means every A/B/C person who is not ground staff. The zero classes and Contract staff stay at 0, whichever kind they are.
- `[ASSUMPTION]` Ground staff use the same class rates DTC gave on 9 Oct.
- `[ASSUMPTION]` The DTC rule set is still off (coordinator, 24 Oct).

## Subtract pass

Removed:
- A dated history of the tick, so the value on the 1st could be used. That would add complexity, and G4's process rule does the job.
- A new report column. The "Why" note says it.
- A separate rule set per kind. One company can only have one rule set, and splitting would copy every other rule.

## Handoff note

To the coordinator: run §1.2 first. Its answer decides between a new tick and an existing field. To the engineer: the flat path becomes code, so the 15-day-block settings trick goes away. Do not switch the DTC rule set on until rehearsal check 7 passes.

---

## Update, 24 Oct 2026 — Housekeeping, from DTC's own table

**Surbhi:** "The people from the housekeeping department are the ones to be considered." She attached DTC's leave credit tables.

**This section replaces §1–§5 above for "ground staff".**
- The accrual rule (A: 1 per 7.5 days, with a 15-day minimum) is **dropped**. So is the `dtc_ground_staff` tick, and so is the code change to the flat credit. DTC's rule is a table of days attended, by month length.
- Office staff keep what 063 built, unchanged.

**Bad news first.**

1. **This contradicts a rule Surbhi set on 11 Oct, so she must confirm it is a deliberate exception.**
   - All 42 Housekeeping staff are on Contract (production read, 24 Oct).
   - On 11 Oct she decided "the leave class of all contractual are not applicable". The engine follows that: Contract staff earn no leave (`earns_leave_credits` = 0 on the Contract row of the rule set).
   - This table makes Housekeeping an exception, decided by their designation. **Q-H1.**
2. **The photo is cropped.** A row "23-29 Days" from **another** table shows at the top, probably another staff group's table for a 28/29-day month. **We need the full document** before building, or a second table will arrive after the code is built. **Q-H2.**
3. **Do Housekeeping staff get a salary slip from DTC at all?** Memory notes that some Contract staff are paid by an outside agency. If DTC does not pay them, a credit changes nothing on any DTC payslip. **Q-H3.**

### H1 · The rule as DTC wrote it

Credits by days attended in the month. The heading says "4 Leaves Allowed".

| Days attended (30- or 31-day month) | Credits | Days attended (28- or 29-day month) | Credits |
|---|---|---|---|
| 0–5 | 0 | 0–4 | 0 |
| 6–12 | 1 | 5–11 | 1 |
| 13–18 | 2 | 12–17 | 2 |
| 19–25 | 3 | 18–24 | 3 |
| 26–30 | 4 | 25–29 | 4 |

There is **no 15-day minimum** in this table.

**Not said, and my recommended default for each:**

| Gap | Recommended default |
|---|---|
| 31 days attended | **4.** The last row means "26 or more". |
| Do approved Paid Leaves days count as attended? | **Yes**, the same as office staff (E6). Otherwise taking your own leave lowers your credit. |
| A half day attended, for example 12.5 | **Round down** to the row below (12.5 gives 1). The rows are whole days. |
| The 6 Housekeeping staff in class "No Leave" | **Get nothing.** The class still decides who is eligible, and how many at most (Surbhi). So only the 36 in class A get the table. |
| Housekeeping staff in class B or C | None exist today. If one appears, their class figure caps the table (3 or 2). |
| Contract's other rules: no red or green marks, the longer grace period, half days and quarters | **Unchanged.** The exception covers leave credit only. |
| Other staff groups | Not covered until DTC sends their tables (Q-H2). |

### H2 · How the product finds them: an existing field, no new tick

- **Designation = "Housekeeping"** already exists on production as a Designation record, with 42 active people.
- It is the cheapest identifier: already there, and kept up to date by HR.
- "Pantry" (3 people) is a separate designation and is **not** included.

What this does to the decisions above:
- **G1** (what "duration" means): answered. It is days attended in the month.
- **G3** (15-day minimum): answered. There is none for Housekeeping.
- **G5** (joiners): answered. A joiner earns from 6 attended days.
- **G6** (who maintains the marker): it becomes the designation, which HR already maintains. **Needs validation:** whether a designation change shows in the Employee's history at DTC.
- **G7** (unticked means office): moot. There is no tick.
- **G8** (use an existing field?): answered. Yes, designation.
- **G4** (moving mid-month): becomes "the designation when the slip is worked out applies to the whole month".
- **Rehearsal check 7** becomes: **36 people** (Housekeeping in class A) get the table. The 6 in No Leave get 0. Anyone else gets the office rule. **Q-H4** confirms 36, not 42.

### H3 · The cheapest build

| Rung | Option | Verdict |
|---|---|---|
| Configuration | Express the table through today's leave-class settings (blocks of days) | **Not possible.** The rows are uneven (6, 13, 19, 26) and change with month length. No block size fits. |
| Configuration | Reuse the rule set's existing attendance-percentage table | **Rejected.** It means something else: the percentage of a shift worked, giving quarters lost. Mixing the two is a trap for the next reader. |
| Configuration | One text box on the rule set holding "6-12:1, 13-18:2 …" | **Rejected.** A typing error gives no warning and goes straight onto a payslip. |
| Code with the numbers written into it | | **Rejected.** The engine holds no numbers; every DTC figure lives on the rule set. |
| **New small table on the rule set** | Columns: designation, month length (28–29 or 30–31), days from, days to, credits. **Housekeeping is named on its rows, so no extra field is needed.** Saving refuses gaps or overlaps, as the attendance-percentage table already does. | **Recommended.** It is a new child table (a table inside the rule set) and so a new DocType. That is the cost. It is justified because DTC's numbers must be visible and checked, not buried in code. |

**What changes:**
- **`payroll_slip.month_summary`** also reads the person's designation. If the rule set has table rows for that designation, it passes them in. This is **the one place where the Contract "no leave" rule is overridden.**
- **`payroll_month.summarise_month`** uses the table for that person: find the row for the month length and days attended, and cap the result at the class figure. Everyone else goes through the existing path. **`leave_credits_for_month` is unchanged.**
- **Card** (Housekeeping, class A): "**2 of 4 earned so far** · from 14 days attended · **next at 19 days (5 more)**". The "next" figure is read from the same table rows, never worked out a second way. Today a Contract person's card says "Contract staff do not earn monthly Paid Leaves" and the Apply list offers only Leave Without Pay. **Both must change for Housekeeping**, so that they are offered Paid Leaves.
- **"Why" column in the report:** "Housekeeping table: 14 days attended in a 31-day month gives 2."
- **Tests built for the flat credit:** unchanged. Office staff are not touched. New tests:
  - Each row edge, for both month lengths.
  - 31 days attended.
  - A half day exactly on a row edge.
  - A No Leave Housekeeping person.
  - A Pantry person, who stays at 0.
  - Approved Paid Leaves counted as attended.
  - Marks still off.
- **Rehearsal additions:**
  - October (31 days): 5 days gives 0, 6 gives 1, 12 gives 1, 13 gives 2, 26 gives 4, 31 gives 4.
  - February 2027 (28 days): 4 gives 0, 5 gives 1, 25 gives 4.
  - 36 people get the table and 6 get 0.
  - The existing 30 office checks are unchanged.

### H4 · Pay effect

- **If DTC pays them** (Q-H3): the engine pays a Contract person per day worked, like everyone else. Each credit is **one extra paid day at Basic ÷ days in the month**. Example only, not a DTC figure: on a ₹12,000 Basic in October, one day is ₹387.10.
  - 14 days attended: 2 credits = +₹774.19.
  - 26 or more attended: 4 credits = +₹1,548.39.
  - Today, as Contract staff, they get 0. So this is new money for 36 people every month.
- **If an agency pays them:** no DTC payslip changes. The card would show credits that nobody pays. **Do not show the card** until Q-H3 is answered.

### H5 · Questions for Surbhi

| # | Question | My recommendation |
|---|---|---|
| Q-H1 | Housekeeping are all Contract, and on 11 Oct you said Contract staff get no leave. Is Housekeeping a deliberate exception, for leave credit only? | **Yes, leave credit only.** No marks, as for all Contract staff. |
| Q-H2 | The photo shows part of another table ("23-29 Days"). Can we have DTC's full document, with every staff group's table? | **Yes, before we build.** One table design should serve every group. |
| Q-H3 | Does DTC pay Housekeeping staff through its own payroll, or does an agency? | — your answer decides whether this changes anyone's pay |
| Q-H4 | The 6 Housekeeping staff in class "No Leave": do they get the table? | **No.** The class decides eligibility, as you said. So 36 people. |
| Q-H5 | Do approved Paid Leaves days count as days attended in the table? | **Yes**, as for office staff. |
| Q-H6 | 31 days attended: 4? A half day on a row edge (12.5): round down? | **4, and round down.** |
| Q-H7 | Is "Housekeeping" the designation, and only that one? Pantry is separate. | **Housekeeping only**, until DTC's other tables say otherwise. |

**Subtract pass on this update.** Removed:
- The ground-staff tick and its import.
- The accrual code change.
- The 7.5-day class settings.
- A separate "which designations" field on the rule set. The designation sits on the table rows instead.

Kept: the designation column on the table rows. The cropped second table is evidence that more than one group has a table.

---

## Result of the §1.2 count on DTC production, 24 Oct 2026 (read-only, counts only)

Run by the coordinator over SSH. 445 active employees.

| Field | Counts |
|---|---|
| employment_type | Permanent 403, Contract 42 |
| dtc_leave_class | A 341, B 63, C 29, No Leave 8, blank 2, Sundays Off 1, 5-Day Week 1 |
| dtc_grade | Junior 428, Senior 13, blank 3, External 1 |
| department | Sales 278, Back Office 116, Management 21, Accounts 8, Admin 8, Production 7, HR 3, others 1 each |
| designation | 55 values: RSO 94, Housekeeping 42, Back Office 40, FSE 34, Cashier 27, Set 21, Bangle 18, Ring 15, ... |
| branch | Chandigarh 34: 97, Chandigarh 22: 92, Delhi 83, Noida 80, Ambala 57, Pitampura 36 |
| **dtc_employee_category** | **EXISTS (a Select: Regular, Pantry, Security Guard, Social Media/Output-based, Field Worker (FSE), Accountant (Exempt)) but is EMPTY for all 445 active staff.** Its own description: "Behavioural exemptions only; it does not change salary structure." |
| dtc_pay_type | FIX 292, VAR 151, blank 2 |

Conclusion: **no existing field marks ground staff versus other staff.** `dtc_employee_category` is the closest by name but is unused and was made for pay-rule exemptions. A clean split by department or designation is not obvious (Sales alone is 278 people and mixes shop-floor roles with others). The PM's recommendation of one new tick on the Employee record (`dtc_ground_staff`) stands unless Surbhi defines ground staff by department or designation list.

---

## Surbhi's answers on the housekeeping table, 24 Oct 2026

| Question | Her answer |
|---|---|
| Q-H1 Is housekeeping an exception to "Contract staff earn no leave credit"? | **Yes, and only for the Housekeeping designation.** |
| Q-H4 Do the 6 Housekeeping people on class "No Leave" get the table? | **No.** "The class says they get nothing." (36 people on the table, 6 at 0.) |
| Q-H5 Do "days attended" mean present days only? | **Present days only; and approved paid leave days DO count** ("whether approved paid leave days count is the same question as before: yes"). |
| Q-H6 What does 31 days attended earn? | **"As per the leave eligibility for the leave class assigned"**: the class figure (class A = 4). Half-day rounding on a row edge was not answered: default stays "round down" (12.5 gives 1), to confirm in the spec. |
| Q-H7 Do the housekeeping tables apply to other staff groups? | **No.** Only Housekeeping. Everyone else keeps the flat credit on the 1st (15-day minimum). |
| Contract limits (no red/green marks, longer grace) | **Kept.** |
| Q-H2 The full document | Not needed for other groups: the tables are for Housekeeping only. |
| **Q-H3 Does DTC pay Housekeeping through its own payroll, or does an agency?** | **NOT YET ANSWERED.** It decides whether anyone's DTC payslip changes, and whether the card is shown. |
