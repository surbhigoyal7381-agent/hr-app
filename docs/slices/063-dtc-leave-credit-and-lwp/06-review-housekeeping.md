---
slice: 063-dtc-leave-credit-and-lwp
artifact: 06-review-housekeeping (senior architect review, change-process step 5, for the Housekeeping leave days part)
author: hrms-technofunctional-reviewer
date: 2026-10-27
branch: slice/063-housekeeping-leave, tip f65227a9, 5 commits on origin/dev ba974baf
tier: 1 (an on-behalf figure gated by company and branch; a new child table on the pay rule set)
---

# 063 Housekeeping leave: review

## 1 · Verdict

**SHIP WITH FIXES.** The code does what the approved paper asks, the pay figures cannot move, and
the on-behalf figure is behind a company-and-branch check on both doors. One fix is needed before a
push to dev: the approved paper this build follows is not committed anywhere (M-1). The rest are
small and can be written down.

"Ship" here means ready to show Surbhi for her push decision. It is not permission to push.

**What I ran and what I did not, said first:**

- **I did not run the Python test suite.** I did not start my own containers. I read the code and
  the tests instead, and I rely on the engineer's reported numbers (section 4 of
  `05-implementation-notes-housekeeping.md`) for the site tests. Every finding below is from reading
  the code, and none needed a run to confirm it.
- I ran: the Leave page jsdom test (`portal_leave_063_test.js`) - **164 passed, 0 failed**; a syntax
  check of the five changed Python files (`py_compile`, OK), of `portal.js` (`node --check`, OK) and
  of both DocType JSON files (OK).
- Nothing was seen in a real browser (phone width, 200 % zoom, keyboard). Same gap the engineer names.

Incoming work: one commit came in on `origin/dev` while the branch was built, `ba974baf`
(surbhigoyal7381-agent, `.claude` agent notes, `[skip ci]`). It touches no file in this diff. No
merge commits from anyone else. **Proven** (`git log`).

---

## 2 · Blockers

None.

The five things the brief asked me to look hardest at all hold. Detail in sections 4 and 5b.

| Check | Result | Label |
|---|---|---|
| (1) HR on-behalf figure needs company AND branch | Held on both doors. `types_offered` checks `permitted_employee_filters()` itself (`leave_rules.py:763-765`); `preview_leave_request` goes through `_leave_subject`, which checks the same filters (`hr_api.py:2517-2521`). An HR user in another branch gets no `left`, no `earned`, no `next_at` | Proven (code), test `test_hr_in_another_branch_gets_no_figure` reads right |
| (2) Nothing changes a Salary Slip, Payroll Entry or the report's Net | Held. For a person on the table, `paid_days = day_credits + 0` (`payroll_month.py:239`). Before this change the same person had `earns_leave_credits = False`, so `leave_credits_earned` was 0 and `paid_days` was also `day_credits + 0`. Net, gross, Basic, marks and grooming read only `paid_days` and marks. No Additional Salary is made from the credit. Office staff take the `elif earns_leave_credits` branch, unchanged | Proven (line-by-line read of both diffs) |
| (3) No designation name in code (SEC-15) | Held for designations. The word "Housekeeping" on screen comes from the table row. **"DTC" is in three strings** (see m-5) | Proven (grep of added lines) |
| (4) Rule set save check | Matches SEC-19 and AC-130: backwards row, not starting at 0, gap, overlap, short last row, negative, falling. Messages name the rows. Empty table skips. In memory | Proven (code + tests read) |
| (5) HR notice once each, never approver or employee, name/dates/days only | Held. HR list minus chain minus approver; `_notice_users` drops the employee and de-duplicates; body has name, dates, day count and two fixed sentences | Proven (code `leave_rules.py:285-295`) and 4 tests read |

---

## 3 · Majors

### M-1 (P2) · The approved paper is not committed anywhere

**What happens.** This build follows spec v4.0, strategy v2, `01c` revision 4b, `01f`, `01g` and
design v4. None of them is on this branch. On this branch, `03-functional-spec.md` is still
**version 3.0**. In v3, AC-117 and AC-118 are the half-day missed-punch blocker, and AC-119..AC-146 do
not exist. The only copies of v4 are **uncommitted edits** in another session's worktree
(`.claude/worktrees/067-pay-slip-marks`, `git status` shows ` M 03-functional-spec.md`,
` M 04-impact-and-strategy.md`, ` M 01c-...`, `?? 01f-...`, `?? 01g-...`).

**Why it is wrong.** The implementation notes and this review cite AC numbers that mean something
else in the committed spec. If the 067 worktree is cleaned or reset, the approved paper is gone, and
nobody can check this build against what Surbhi approved. On a pay-adjacent change at a live client,
that trail is what answers "who decided this".

**Smallest fix.** A docs-only commit, on this branch or on dev before this branch lands: spec v4.0,
strategy v2 (and the kept v1), 01c rev 4b, 01f, 01g, 02-design v4, 04c. No code. Then the AC numbers in
`05-implementation-notes-housekeeping.md` and in this file point at real text.

**Proven** (`git status` in the 067 worktree; `head` of this branch's spec).

---

## 4 · Minors

### m-1 (P3) · A Housekeeping person with an empty leave class is told an untrue sentence

*Input:* Contract, designation with table rows, leave class empty. *What happens:* `credit_facts`
gives `earns` False and `category_earns` False; `class_is_why` is False because the class is empty;
so `_card` sends `category = "Contract"` (`leave_rules.py:603`), and the page says "**Contract staff
do not get monthly Paid Leaves.**" The Apply help says "Your work type does not get Paid Leaves".
*Why wrong:* Housekeeping Contract staff do earn leave; the real reason is the missing class. AC-124
asks for the AC-14 sentence ("No leave class is set for you ... Ask HR if this is wrong").
*Who meets it:* nobody at DTC today [inferred from 01c: 36 on the table plus 6 on No Leave = all 42].
*Fix:* in `_card`, also send `category = None` when `facts["housekeeping"]`; and in `types_offered`
skip the "work type" reason the same way (one flag). A few lines.
**Proven** by reading; **not run**. AC-124 is **partial**.

### m-2 (P3) · HR in another branch can see a person's leave class name

*Input:* HR user in the same company but another branch calls `get_leave_summary(employee_id=...)`
for a No Leave person. *What happens:* `_hr_target_employee` lets them in (company only, the known
F-3), and `types_offered` adds `no_paid_class: "No Leave"` to the LWP row with no branch check
(`leave_rules.py:768-771`). *Why wrong:* the slice gates `left` by branch but not this new key. It is
small - a class label, not a figure - but it is a widening nobody wrote down.
*Fix:* put the key behind the same `own or exists(...)` check as `left`, or fix F-3 (below).
**Proven** by reading.

**Related, pre-existing, and live on main: F-3.** The same company-only door
(`hr_api.py:2286-2302`, unchanged on `origin/main`) returns another branch's employee's leave
balances and their last ten leave applications **including the reason text** (`description`,
`hr_api.py:2334-2343`, `ignore_permissions=True`). This slice did not cause it and worked around it
correctly. But it is a live exposure wherever an HR user is limited to a branch. I could not check
whether any production HR user is branch-limited today. **Escalation below (section 9).**

### m-3 (P3) · A designation with rows for one month length gets 0 in the other, silently

*Input:* a System Manager enters only the five `30-31` rows. *What happens:* the save passes (each
group is checked on its own; nothing asks for both lengths). In February `credit_rows_for` returns
None, so Housekeeping staff earn 0 and their card says "Contract staff do not get monthly Paid
Leaves." *Why it matters:* an incomplete table looks like a rule, which is lesson 3 of September.
DTC's ten rows cover both, and Surbhi checks the rows at gate G-A3, so the risk is low.
*Recommendation:* either one more refusal in `_check_credit_rows` (a designation with rows must
have both month lengths), or one line in the release checklist. Not in the spec, so it is
Surbhi's call. I lean to the checklist line (no code).

### m-4 (P3) · A Housekeeping person's own Leave page works out the month twice

`get_leave_summary` for one's own record calls `types_offered` → `paid_leaves_left` →
`table_summary`, then `paid_leaves_card` → `_table_card` → `table_summary` again. That is two full
`month_summary` runs (the engineer measured one at 168 ms locally). Not reachable today: none of the
42 has a login, and HR on behalf gets only the first. **Inferred** from the call chain; **not
measured**. *Temporary debt:* fix when Housekeeping logins are planned, by passing the card's summary
into `types_offered`.

### m-5 (P3) · "DTC" is written into three strings (SEC-15, the engineer's N-7)

"Reported to the agency; not paid by **DTC**." (`payroll_month.py:201-203`), "Your leave is recorded
for **DTC's** attendance..." and "...leave without pay on **DTC's** attendance" (`portal.js`). The
approved prototype uses exactly these words, and only DTC has a rule set, so today it is correct.
If a second tenant ever gets a rule set, its staff would read "DTC". *Recommendation:* accept in
writing as an **intentional trade-off** for go-live, with a ticket. Do not change the approved
wording without Surbhi.

### Nits (P4)

- `preview_facts(..., own)` no longer uses `own` (`leave_rules.py:811`). Dead parameter.
- The odd-period note in `month_summary` (`payroll_slip.py:189-192`) also fires for a Permanent
  person who shares the designation, where it says "it gave no leave" though the office rule ran.
  Only for a period that is not 28 to 31 days, which DTC's monthly payroll never makes.
- For a table person in a class below 4 (class B, cap 3) the rule box reads "26 or more days
  attended earns 4, never more than 3". True, but reads oddly. Not in the spec; nobody at DTC hits it
  [ASSUMPTION: the 36 are all class A].

---

## 4b · The engineer's open decisions N-3..N-8

| # | Engineer recommends | My view |
|---|---|---|
| N-3 "earn" on the card, "get" in the Apply help | Ask Surbhi | **Agree, and keep as specced meanwhile.** AC-13 says "earn", AC-30 says "get". Both read fine alone; changing one is a wording choice, not a defect |
| N-4 A non-Housekeeping Contract person with a zero class now reads the class sentence | Keep | **Agree.** AC-13 says a No Leave class gets the class sentence, "office or Housekeeping", and both sentences are true. The class is the field HR would change. Note m-1 is the opposite case and does need fixing |
| N-5 "one day earlier / later" is fixed text | Keep | **Agree.** It is true for DTC's ten rows. Add one line to the release checklist: if the rows ever change shape, re-read the rule box |
| N-6 A-1 gives HR the days-left figure on behalf for office staff too | Keep | **Agree.** 03b says so in plain words (A-1), and the check is the same company-and-branch check |
| N-7 "DTC" in strings | Ask Surbhi | **Agree to ask;** my recommendation is m-5: accept for go-live, ticket it |
| N-8 the approver is no longer told their own approval | Keep | **Agree.** This is not new scope: spec N-1 already says "not the approver", and AC-145/146 cannot be true without it. The strategy assumed Frappe skipped the sender; the engineer found it does not, and the test now proves it (`assertNotIn(Sunil, told)`) |

---

## 5 · Acceptance criteria

AC-117 and AC-118 in v4 are the half-day correction, which belongs to the office build already on
dev, not to this part. Not reviewed here.

| AC | Result | Evidence |
|---|---|---|
| AC-13 | met | `portal.js` card: "does not earn"; test `test_a_class_with_no_leave_gets_the_class_sentence` |
| AC-17, AC-18 | met | Office key list equality now asserted both ways (`test_leave_063_card_cancel.py`); table key list equality; JSON has no pay key and no "12000" |
| AC-23 | met (one person) | Query count equal with 5 more staff (test read). Full-page cost: see m-4 |
| AC-119..AC-121 | met | Pure tests per row edge (engineer); logic `payroll_month.py:189-199` read: `int()` rounds down, row lookup, cap |
| AC-122, AC-123 | met | `days_for_gate` already adds approved Paid Leaves days and halves; Open and LWP not counted (read) |
| AC-124 | **partial** | Class cap and No Leave met; empty class gives the Contract sentence, not AC-14 (m-1) |
| AC-125, AC-126, AC-127 | met | `credit_rows_for` four conditions (`payroll_slip.py:87-93`); no gate in the table branch; site tests read |
| AC-128 (a-e) | met | Real draft slips: 26 not 30; no Additional Salary; same with rows deleted; Hari 30. A wrong `paid_days` would fail these tests (not hollow) |
| AC-129 | met | Report test asserts earned 2, encashed 0 and the Why text |
| AC-130 | met | Seven refusals, ten rows save, empty saves, a second designation checked alone |
| AC-131 | met | HR read yes, write no; Version row holds `leave_credit_rows` |
| AC-132 | met | Designation read at the time of working out (test) |
| AC-133..AC-139 | met (server and jsdom) | Strings match prototype v4 word for word (grep of the prototype); 164 jsdom checks pass. **Not seen in a browser** |
| AC-140..AC-143 | met | Server and page tests; special-day line dropped for agency staff; "The leave is paid" not said |
| AC-144 (as changed by Q-S2 and A-1) | met | Both doors gated by company AND branch |
| AC-145 | met | HR in scope told once, not approver, not employee, not other branch; same subject; no type, reason or approver name |
| AC-146 | met | `told_top` and `annotate_applications` count chain members only |
| Q-S5 | met | `leave_encashed` stays 0 for a table credit |
| AC-147, AC-148/149, AC-150/151, AC-108 items 11-15 | held / not code | Payroll held by Surbhi (27 Oct); Way B is a desk procedure; release gates; rehearsal scripts not extended (temporary debt, noted by the engineer) |
| AC-8, AC-80 | not checked | Needs a person with a screen |

---

## 5a · NFRs, and the seven dimensions against strategy v2

| Budget | Measured or reasoned | Result |
|---|---|---|
| 500 ms per call | One table card 168 ms local, warm (engineer's measure, not mine). Own page runs it twice (m-4) | pass for HR on behalf; own page not measured |
| Query count flat with headcount | Test: equal at +5 staff | pass |
| 1.5 s per approval | HR notice adds one scope check per HR user (7 at DTC) | reasoned pass, not measured |

| Dimension | Strategy v2 said | Code as written | Match? |
|---|---|---|---|
| Performance | degrades slightly, inside budget | Same, plus the double summary on the own page (m-4) | mostly; m-4 not in the claim |
| Security | neutral, one widening Surbhi chose | The `left` widening is gated as planned. The `no_paid_class` key is a small unplanned widening (m-2) | mostly |
| Reliability | improves | Bad table refused on save; notice stays inside the try/except | yes |
| Scalability | neutral | Nothing per head | yes |
| Maintainability | slightly degrades | One child DocType, one check, one branch, one key list | yes |
| Data integrity | improves | One `month_summary` feeds slip, report, card, Apply, preview; nothing stored | yes |
| Compliance / privacy | neutral | HR notice carries the four facts only; card has no pay field | yes |

---

## 5b · Compliance verification

| Obligation | Mechanism in the diff | Test that proves it | Status |
|---|---|---|---|
| SEC-15 one DTC check, no names in code | `rule_set_for` gates every path; designation from data | AC-27 table test (existing) + grep | **partial** - "DTC" in three strings (m-5) |
| SEC-18 who the table reaches | `credit_rows_for`, four conditions | Geeta, Sushila, Hari, Pooja, rows-deleted tests | discharged |
| SEC-19 table cannot be saved wrong | `_check_credit_rows`, System Manager write only, Version row | seven refusal tests, permission test, Version test | discharged (see m-3 for the one-length gap, not in SEC-19) |
| SEC-20 credit never pay | `paid_days` excludes it; `leave_encashed` 0; no Additional Salary path | real slip tests (a)-(e) | discharged |
| SEC-1 card keys, two lists | `_table_card` names each key | key-equality tests both lists | discharged |
| Q-S2 on-behalf scope | `permitted_employee_filters` on both doors | in-scope and other-branch tests | discharged (m-2 for the class label) |
| PRIV-1 / N-1b fixed fields | built in code, not a Notification record | `SECRET-REASON-063`, type and approver absent | discharged |
| PRIV-7 nothing to the agency | nothing built | review | discharged by absence |

---

## 6 · What to delete

- **Nothing that matters.** The new DocType is needed (SEC-19 needs a save check; no cheaper rung
  names a designation, two month lengths and uneven edges). The second key list is needed (SEC-1,
  SEC-20). `.lp-chip` is one CSS rule the prototype draws.
- Optional: the odd-period note (`payroll_slip.py:187-192`, four lines). `credit_rows_for` already
  returns nothing for such a period, and DTC's monthly payroll never makes one. Deleting it loses a
  hint nobody at DTC will see.
- Optional: the unused `own` parameter of `preview_facts`.

## 7 · What was done well

- **The pay guard is one condition in one place.** `paid_days` leaves the table credit out at the
  single line every slip, report and card reads, so there is no second calculation to drift.
- **The scope check sits on the figure, not just on the door.** The engineer saw that the existing
  on-behalf door checks the company alone, and put the branch check on the new figure instead of
  trusting the door.
- **The slip tests use a real Salary Structure Assignment with a real Basic.** That is what makes
  (b)-(d) able to fail. The September lesson about tests that cannot fail was applied.
- **The engineer found a real fact while testing** (this Frappe alerts the sender) and made the
  "told" count true, instead of loosening the test.
- **Scope was held.** `hr_api.py`, `hooks.py`, the report, Payroll Entry and 067 are untouched, as
  Surbhi's 27 Oct split asked.

## 8 · Confidence

| Claim | Label |
|---|---|
| Pay figures cannot move | Proven by line-by-line read; the engineer's slip tests back it |
| Scope gate on both doors | Proven by read |
| Site tests green | **Not checked by me** - the engineer's report |
| Page strings and layout | jsdom proven (I ran it); **real browser not checked** |
| Production exposure of F-3 | **Not checked** - needs a read of production User Permissions on Branch for HR users |
| DTC's rows equal DTC's document | **Not checked** - Surbhi's gate G-A3 |

Subtract pass on this review: I removed a finding on the `approved_leave_unpaid` figure dropping to
0 for table staff (it is never shown or used in money, so it is not a defect), and a finding on
missing tests for the disabled rule set (the HR notice sits after the same early return the chain
notice tests already cover).

## 9 · Escalation

**Decision needed:** whether F-3 is fixed now, separately from this slice.
**Context:** `_hr_target_employee` checks the company only. A branch-limited HR user can read
another branch's leave balances and leave reasons through `get_leave_summary(employee_id=...)`. It
is on `origin/main`.
**Conflict:** none with this slice; it is older.
**Who is affected:** employees in other branches, if any HR user is branch-limited.
**Options:** (a) one line - use `permitted_employee_filters()` in `_hr_target_employee`, as
`_leave_subject` already does (recommended); (b) leave it and ticket.
**Risk if it waits:** leave reasons (sometimes health) seen by the wrong HR person.
**Owner:** `hrms-security-privacy-engineer` to confirm exposure, then Surbhi to decide, then
`hrms-fullstack-engineer` for the line.
