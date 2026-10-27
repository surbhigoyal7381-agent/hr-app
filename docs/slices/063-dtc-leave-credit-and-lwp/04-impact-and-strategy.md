---
slice: 063-dtc-leave-credit-and-lwp
artifact: 04-impact-and-strategy, version 2 (change process steps 1 and 2; the 00-impact-analysis of the handoff contract)
author: hrms-fullstack-engineer
date: 2026-10-25
status: waiting for Surbhi's approval. Paper only - no code written, nothing committed, nothing pushed, nothing run on any server.
replaces: version 1 of 21 Oct 2026, kept unchanged as 04-impact-and-strategy-v1.md (the office build it planned is now on dev)
inputs: 03-functional-spec.md v4.0; 01c rev. 4b (SEC-1..3, 6..20; PRIV-1..3, 5..7); 01g; 04c; 02-design.md v4 (W.1-W.5); prototype-v4.html; 04b-implementation-notes.md; 07-rehearsal-runbook.md; 07a-backup-and-rehearsal-runbook.md (read in worktree 060-manager-review); .claude/context change-process.md, no-over-engineering.md, nfr-budget.md, parallel-work.md
code read: origin/dev f207e82c (read-only, worktree 066-grooming-build) - leave_rules.py (whole), payroll_month.py (whole), payroll_slip.py (whole), alvoraa_payroll_rule_set.py and .json, hr_api.py 2306-2600, the salary report's leave columns, portal.js lp- block (6064-6560), hooks.py leave entries, scripts/rehearsal_063.py and seed_rehearsal_063.py, hrms leave_application.py on_submit; branch slice/063-field-rights (ALV-215) at 5c96a348; branches slice/070-readable-on-phone, slice/070-seats-follow-reporting, slice/071-unseated-names
decisions used: Surbhi, 25 Oct 2026, "go with recommendations" - Q-S1 (a), Q-S2 yes for Housekeeping, Q-S7 accept; the rule set stays OFF at DTC until five gates pass
---

# 063 · Impact analysis and strategy, version 2

## 0 · Bad news first

1. **Most of this slice is already built and on `dev`, but not on `main`.** The office part (credit
   on the 1st by settings, 15-day minimum, LWP limit of 5, HR approves LWP, cancel, chain notice,
   half days, the missed-punch correction) is commit 24ee6549 and its family on `origin/dev`. It is
   not on `origin/main` (a473c191). So no DTC employee can apply on production until a release.
   Version 2 adds only: the Housekeeping table, the Housekeeping card and Apply facts, HR being told
   of every approval, the "told" counter fix, and wording fixes. Everything else is re-proved, not
   rebuilt.
2. **Slice 070 (ALV-217, "readable on a cheap phone") is editing the same leave code in
   `portal.js`** - `lpSubmit`, `submitLeaveApp`, `openLeaveModal`, `renderLeaveApps` - and the same
   test file `portal_leave_063_test.js`. It is built, local only, not on `dev`. **One of us must
   go first** (section 8). I recommend 070 goes first and I rebase on it.
3. **Showing HR the Housekeeping figure on behalf (Q-S2) opens one hole if done the obvious way.**
   `get_leave_summary(employee_id)` checks HR's scope by **company only** (`_hr_target_employee`,
   finding F-3). The branch check lives only in `_leave_subject`. So an HR user limited to one
   branch could read a person's figure in another branch. The build must check
   `permitted_employee_filters()` (company **and** branch) before it adds any figure on behalf.
   This is in the plan (step 3); it costs one query.
4. **The engine's "Why" note must not name "Housekeeping" in code.** The spec's wording does
   ("Housekeeping table: ..."). SEC-15 forbids a designation name in code. The note and the card
   will print the designation **from the table row**, so DTC still reads "Housekeeping" - but the
   word is data, not code. Same words on screen; tell the analyst.
5. **Nobody will see the Housekeeping card on their own phone.** 0 of 42 Housekeeping staff have a
   login. With Q-S2 answered "yes", HR sees the figure when filing for them. That is the only
   viewer. The card itself (the "own" view) is still built, because it is in the prototype and costs
   little beside the office card.
6. **Payroll can still pay an agency worker by mistake.** Q-S1 (a) means HR deletes 42 rows from
   every month's Payroll Entry by hand. If missed, a slip pays worked days from DTC's payroll. The
   engine never adds the leave credit to it (SEC-20), but the worked days are still paid. The check
   afterwards is a desk list filter (section 6.4), not code.
7. **The "told" line already counts wrong once HR is told.** `told_for` counts every notice with
   " will be away on " in the subject. The HR notice must use the same subject (spec N-1b), so the
   employee's line "your managers ... have been told (n people)" would count HR as managers. The
   fix is two lines (AC-146), in step 4.
8. **One stale branch to report, not mine to delete:** `slice/063-dtc-leave` (worktree
   `063-dtc-leave`) holds 17 commits that are all already on `dev` under other hashes
   (`git cherry` shows every one as "-"). Its demo containers `hrlocal-063*` may still be running.
   Surbhi decides whether to remove it.

---

## 1 · Impact analysis

### 1.1 Cross-module reach

| App | Touched | How |
|---|---|---|
| `alvoraa_portal` | **Yes** | One new child DocType; one Table field on `Alvoraa Payroll Rule Set`; `payroll_month.py`, `payroll_slip.py`, `leave_rules.py`, the rule set controller; `portal.js` lp- block; possibly a few lines in `panels.css`; tests; the two rehearsal scripts |
| `hrms` (our copy) | **No change** | `access.py` helpers called as they are (`permitted_employee_filters`, `refuse`). Leave Application, Leave Type, Attendance, Payroll Entry, Salary Slip used as shipped |
| `frappe`, `erpnext` | No | |
| `alvoraa_goals`, `alvox_compensation` | No | Nothing reads leave or the pay engine (grep: no import of `payroll_*` or `leave_rules`) |
| Slice 066 (grooming) | No coupling | Its own switch (the Grooming Red Value component). It shares `payroll_month.py` / `payroll_slip.py`, already on `dev` - I build on top of it |
| Slice 067 (pay-slip marks) | **Shares the one switch** | Same `enabled` box. Q-S7 accepted: 067's red and green lines wait for the same five gates. No code change |
| ALV-215 (field rights) | Gate G-A1, and one shared file | It adds `on_update` to the rule set controller; I add one check to its `validate`. Different methods. It locks `designation` (level 2), which this slice needs |
| Slice 070 (two branches) | `portal.js` | See section 8 |

**Not touched, on purpose:** `hr_api.py` (the on-behalf figure and the scope check fit inside
`leave_rules.py`, which `hr_api` already calls), `hooks.py` (the HR notice rides on the existing
`on_submit` hook; the table check lives in the DocType's own `validate`), `inbox_api.py`, `payroll_rules.py`,
`payroll_rules_apply.py`, `attendance_correction.py`. No patch.

### 1.2 Every caller of every function I would change (grepped on origin/dev f207e82c, whole repo)

| Function | Callers | Effect on them |
|---|---|---|
| `payroll_month.summarise_month` | `payroll_slip.month_summary`; tests `test_payroll_month`, `test_leave_063_engine`, `test_grooming_cap_066`, `test_pay_slip_marks_067`, `test_salary_report` | One new keyword, `credit_rows=None`. Nobody passes it today, so every existing call gives the same answer. Two new fields on `MonthSummary` (`credit_table`, `next_credit_at`), default empty |
| `payroll_slip.month_summary` | the salary report (line 50); `on_salary_slip_validate` (291); `check_grooming_before_submit` (350); `leave_rules._card` (578); `scripts/rehearsal_063.py` (186); `scripts/seed_rehearsal_063.py` (130, 274) | Reads `designation` in the Employee read it already makes (no new query). Passes rows only when SEC-18 holds. For everyone else, unchanged. For a Housekeeping person the slip's paid days **drop** by the leave credit (that is SEC-20) and `leave_encashed` is 0 |
| `AlvoraaPayrollRuleSet.validate` | Frappe on every save | One more check, `_check_credit_rows`. An existing rule set with no rows passes it |
| `leave_rules.credit_facts` | `paid_leaves_left`, `_card`, `types_offered`, `refuse_type_not_offered`, `preview_facts` (all in `leave_rules.py`) | Adds `housekeeping`, `earned`, `cap`. `earns` becomes true for a table person with a class figure, so Paid Leaves is offered and not refused |
| `leave_rules.paid_leaves_left` | `types_offered`, `preview_facts` | For a table person: earned so far − used − waiting. Office: unchanged |
| `leave_rules._card` / `paid_leaves_card` | `hr_api.get_leave_summary` 2357 | A second fixed key list for a table person (SEC-1 list two). Office keys unchanged |
| `leave_rules.types_offered` | `hr_api.get_leave_summary` 2351; tests `test_leave_063_rules` 49-58, 366; `test_leave_063_card_cancel` 104 | On behalf: adds `left` for a Housekeeping person **only if** the person is inside the caller's company-and-branch scope (bad news 3) |
| `leave_rules.preview_facts` | `hr_api.preview_leave_request` 2561 | Housekeeping facts (`housekeeping`, `earned`, `next_at`); no `special_day` for them; the not-enough check also runs on behalf for Housekeeping |
| `leave_rules.notify_chain_on_approval` | hooks.py Leave Application `on_submit` (276) | Also tells HR in scope (N-1b), once each, never the employee or the approver |
| `leave_rules.told_top` | `decision_facts` (320) → `hr_api.action_leave` 1116; test `test_leave_063_rules` 414 | Counts chain managers only |
| `leave_rules.annotate_applications` | `hr_api.get_leave_summary` 2355 | `told_count` counts chain managers only |
| `leave_rules.CARD_KEYS` | test `test_leave_063_card_cancel` 40 (subset check) | Split into two lists; the test becomes an **equality** check per list (AC-17, AC-138) |
| `portal.js` `lpRenderCard`, `lpPopulateTypes`, `lpVerdict`, `lpShowResult` | the Leave page and Apply pop-up only | A Housekeeping branch in each; X-8 and X-9 wording |

Not changed and still pinned by their tests: `rule_set_for`, `validate_leave_application`,
`lock_paid_leaves`, `prepare_half_day_correction`, `chain_of`, `hr_users_in_scope`, `cancel_leave`,
`_can_action_leave`, the 70 ceiling in `hr_api.py`, the 0 ceiling in `leave_rules.py`.

### 1.3 Personas

| Persona | What changes in version 2 |
|---|---|
| **Employee, office, DTC** (10 with a login) | Nothing new on screen except: the "told" line counts managers only (AC-146). Their pay changes only at switch-on, as already planned |
| **Employee, Housekeeping, DTC** (42, no login) | Earn Paid Leaves days from days present, by the table. No DTC pay moves. They never see the card unless one is given a login |
| **Employee, other tenants** | None. No rule set, so nothing here runs |
| **HR Manager / HR User at DTC** (7) | Filing for a Housekeeping person: sees "Paid Leaves - n days left" and "has earned n so far" (Q-S2), only for people in their company **and** branch. **Told of every approved leave** of people in their scope (N-1b): up to about 6 bells per approval at DTC. Removes Housekeeping rows from each Payroll Entry and checks afterwards (Q-S1). Way B until switch-on |
| **Named approver / managers up the chain** | No change |
| **System Manager** | Types the 10 Housekeeping rows once; the rule set refuses a gap, an overlap or a falling figure |
| **CXO** | None, unless they hold HR Manager at DTC - then they get every HR approval bell too. I could not check who holds the role; say if that is unwanted |

### 1.4 HRMS domains

- **Leaves:** one type for both groups ("Paid Leaves", created by hand at DTC at release); no
  allocation, no policy, no ledger change.
- **Attendance:** read only. Days present = days worked + approved Paid Leaves days, halves 0.5 -
  the number the engine already makes (`days_for_gate`).
- **Payroll:** office staff as already built. Housekeeping: the credit is reported, never paid; HR
  keeps them out of Payroll Entry by hand.
- **Org structure:** `designation` now picks the table, so it becomes a leave field. ALV-215 makes it
  HR-only. `reports_to` still picks who is told.
- **Appraisals, goals, compensation:** not touched.

### 1.5 The seven non-functional dimensions (against the plan; re-checked against the code at step 5)

| Dimension | Before (dev today) | After (planned) | Verdict |
|---|---|---|---|
| **Performance** | Card: one `month_summary` for the caller (24 queries empty, about 3 more per attendance day, 52 ms measured). Approval: chain walk, 1 read per level | Table: **no new query** (rows come with the rule set; `designation` joins the Employee read already made). A Housekeeping person's Apply list and preview need days present, so they run `month_summary` too (about 100 queries for a full month). HR notice: about 2 + 7 queries at DTC plus one bell per HR user. All per request, not per head | **degrades slightly, inside budget** (500 ms per call, 1.5 s per approval). Measured in step 3 and step 4; no cache unless a number says so |
| **Security** | Card own-only; HR on behalf sees no figure | HR on behalf sees a Housekeeping person's **days** figure, after a company-and-branch check that today's code lacks on that path (bad news 3). Rows editable by System Manager only, refused on save if wrong (SEC-19). No new endpoint, no new bypass, no role change | **neutral** - one widening Surbhi chose, with a tighter scope check than the existing path |
| **Reliability** | Office rules on every door | A wrong table can no longer be saved. A month length the table does not cover (not 28-31 days) gives 0 and a note, never a guess. Notices still never block an approval | **improves** |
| **Scalability** | Nothing per head | Same. The table is at most a few dozen rows per rule set | **neutral** |
| **Maintainability** | DTC rules in `leave_rules.py` (0 bypasses) | One child DocType (5 fields), one check beside `_check_slabs`, one branch in `summarise_month`, a second key list. `portal.js` grows by one Housekeeping branch in four functions | **slightly degrades** (more surface), kept to one module and one table |
| **Data integrity** | One source per number | Still one source: the table credit and "next at" come out of the one `summarise_month` call that the slip, the desk report and the card share. Nothing stored, nothing cached, so nothing goes stale. A rule-set edit is a Version row | **improves** (the "told" count becomes true) |
| **Compliance / privacy** | Days only; chain gets four facts | HR gets the same four facts (they could already read every leave on the desk). The card for a table person carries no pay field (SEC-20). The table holds no personal data. Nothing goes to the agency (PRIV-7, instruction only) | **neutral**, one new push of data HR already holds |

---

## 2 · The strategy

### 2.1 The rung for each part

| Part | Rung | Why not cheaper |
|---|---|---|
| Office credit on the 1st, 15-day minimum | **2 - configuration** (rule set values, already in the runbook) | - |
| "Paid Leaves" Leave Type | **2 - one record by hand at DTC**, at release | A patch would run on every tenant (OPS-7) |
| LWP limit 5, current month, HR approves LWP, cancel, chain notice, half days, missed punch | **already built** (4 - on dev) | - |
| **Housekeeping table** | **5 - one child DocType** | Frappe Earned Leave accrues by calendar, not by days present, and needs allocations Surbhi ruled out. The rule set's `slabs` mean "percent of a shift". `leave_classes` holds one figure per class. A text box of ranges has no save check, and a typo goes straight to the agency (SEC-19). Numbers in code: the engine holds no numbers by design. Nothing cheaper names a designation, two month lengths and uneven edges (6, 13, 19, 26) with a save check |
| Housekeeping credit worked out | 4 - one branch in `summarise_month` | Config cannot read days present |
| HR told of every approval | 4 - a few lines in the existing `on_submit` hook | A Frappe Notification record can be edited by any System Manager to add the reason (PRIV-1) |
| "Told" count managers only | 4 - two lines | - |
| Keep Housekeeping out of payroll (Q-S1 a) | **2 - process** + a desk list filter for the check | Code (Q-S1 b) only if a mistake happens once |
| Way B (bridge) | **1 - already there** (desk Leave Application, LWP) | - |
| Rehearsal additions | scripts only (not shipped code paths) | - |
| New field, setting, job, cache, report, export, app | **none** | - |

### 2.2 The Housekeeping table - the one new DocType

**Child DocType `Alvoraa Leave Credit Row`** (`istable` 1, `editable_grid` 1, no permissions of its
own, no personal data). Name proposed by the spec; I keep it.

| Field | Type | Mandatory | Note |
|---|---|---|---|
| `designation` | Link → Designation | yes | Who the rows are for. A Link, so a deleted or mistyped designation is refused by Frappe |
| `month_length` | Select `28-29` / `30-31` | yes | |
| `days_from` | Int | yes | whole days |
| `days_to` | Int | yes | whole days |
| `credits` | Float | yes | days of Paid Leaves |

**On the rule set:** one Table field `leave_credit_rows`, label "Leave Earned by Days Present (by
Designation)", placed after `leave_classes`, description: "Only for staff whose category earns no
leave credit. The class figure caps every row." `track_changes` is already 1, so row edits land in the
rule set's Version rows.

**Checked on save** - `_check_credit_rows`, a new method beside `_check_slabs`, called from
`validate()` (one line). Per designation and month length, sorted by `days_from`:
`days_from` ≤ `days_to`; first row starts at 0; each row starts the day after the last one ended
(no gap, no overlap); last row ends at 31 (`30-31`) or 29 (`28-29`); `credits` ≥ 0; credits never
fall as days rise. Each message names the rows, as `_check_slabs` does. Nothing runs if the table is
empty, so every other tenant's save is unchanged. Fully in memory: no query.

### 2.3 Who gets the table (SEC-18) - decided from data, one helper

`credit_rows_for(rule_set, designation, cat_row, cls_row, month_days)` in `payroll_slip.py`, beside
`month_summary`. It returns this month's rows, or None. All four must hold, else None:

1. the rule set is enabled (it is: `rule_set_for` returns only enabled ones);
2. the person's category row says `earns_leave_credits` = 0 (Contract at DTC; a Permanent
   Housekeeping person stays on the office rule);
3. the rule set has rows for the person's `designation`;
4. the class row exists and its `monthly_credits` > 0 ("No Leave" → None → 0 and the No Leave card).

Month length 28 or 29 → `28-29`; 30 or 31 → `30-31`; anything else → None, plus a note
`[ASSUMPTION: DTC's payroll periods are calendar months]`. Two callers: `month_summary` (slip,
report, card) and `leave_rules.credit_facts` (Apply list, preview, refusal). That is why it is a
helper and not inline. No company, site or designation name in code.

### 2.4 The calculation, in `summarise_month` (pure, no database)

New keyword `credit_rows=None` (a list of (from, to, credits) for this month), passed only by
`month_summary` when 2.3 holds. When given:

1. days present = `days_for_gate` (already: days worked + approved Paid Leaves days, halves 0.5);
2. whole days = round down (12.5 → 12);
3. earned = the row holding whole days, capped by the class figure (`monthly_cap`);
4. `next_credit_at` = `days_from` of the first row worth more than earned, if earned is under the
   cap; else empty. (The card shows "next at - days present", so 14.5 gives "4.5 more".)
5. `leave_credits_earned` = earned; `leave_used_for_approved` = min(earned, approved Paid Leaves);
   **`leave_encashed` = 0** (Q-S5 default, the figure is being drafted for Surbhi - one line to
   change if she says otherwise); `paid_days` = `day_credits` only - **the credit is never added**
   (SEC-20);
6. one note: "{designation} table: {n} days present in a {d}-day month gives {e}. Reported to the
   agency; not paid by DTC." - the designation from the row (bad news 4);
7. no 15-day minimum; the office gate note is not added.

`month_summary` does not touch Additional Salary for leave at all, so SEC-20's "no Additional
Salary" holds by construction; Contract staff earn no marks, so no red or green line either.

**Not a second calculation anywhere.** The card, the Apply list and the preview read `earned` and
`next_credit_at` from the summary. The rule box text is built in the page from the `rows` the card
sends (rule-set facts, no personal data), never from numbers typed into the page.

### 2.5 The card, the Apply list and the preview (in `leave_rules.py`)

- `credit_facts` gains `housekeeping` (2.3 holds), `cap`, and for a table person `earns` = True. It
  does **not** compute `earned` itself - the callers that need it call `month_summary`, once.
- `_card` for a table person returns **list two** exactly: `month`, `class`, `earns`,
  `housekeeping`, `earned`, `cap`, `attended_so_far`, `attended_up_to`, `next_at`, `days_to_next`
  (both left out at the cap), `used`, `used_dates`, `waiting`, `waiting_from`, `approver`,
  `month_length`, `rows`, `lwp_in_play`, `lwp_limit`. **Never `to_be_paid_out`.** Built by naming
  each key. `CARD_KEYS` becomes `CARD_KEYS_OFFICE` and `CARD_KEYS_TABLE`; the test checks
  equality with one of them.
- `types_offered`: Paid Leaves offered to a table person with `left` = earned − used − waiting.
  **On behalf (Q-S2):** `left` is added for a table person only when the target is inside
  `permitted_employee_filters()` for the caller (one `exists` query). Office persons on behalf stay
  as today (no figure) unless Surbhi widens Q-S2 (question A-1).
- `preview_facts`: for a table person adds `housekeeping`, `earned`, `next_at`; leaves out
  `special_day`; runs the not-enough check for own **and** on behalf (scope already checked by
  `_leave_subject`). The server still does not enforce "left" at filing (AC-34 unchanged).
- `refuse_type_not_offered` needs no edit: it asks `credit_facts(...)["earns"]`, which is now true for
  a table person.

### 2.6 HR told of every approval, and the counter (US-33, AC-145, AC-146)

Inside `notify_chain_on_approval`, after the chain notice: `hr = hr_users_in_scope(employee)`
minus the chain's users (told once, with the chain wording - E-44); `_send` the N-1b body with the
**same subject**. Frappe already skips the approver (the acting user) and `_notice_users` skips the
employee. The second line reads "You are told because you look after {first}'s records in HR. There is
nothing for you to do." - **wording pending Surbhi's yes (X-6)**, one string. Same four facts, same
exclusions as AC-59. Wrapped by the same try/except, so it never blocks an approval.

Counter: `told_top` and `annotate_applications` count only users who are in `chain_of(employee)`.
`decision_facts` follows automatically. No new query (the chain is already walked there).

### 2.7 Screens (`portal.js` lp- block only)

- `lpRenderCard`: if `pl.housekeeping`, draw W.1 - three figures, the "So far" chip, the next line
  (or X-8's first sentence alone at the cap), the agency sentence, the rule box built from `pl.rows`.
  The chip reuses an existing chip class if one fits; otherwise a few lines appended to the lp- block
  in `panels.css`.
- `lpPopulateTypes`: X-9 - a zero class reads "Your leave class ({c}) does not get Paid Leaves, so
  only Leave Without Pay is offered."; Contract keeps the drawn sentence.
- `lpVerdict` / `lpShowResult`: Housekeeping sentences R-90..R-95 (no "The leave is paid", no
  special-day line, no "charged double", the LWP "recorded ... on DTC's attendance" sentence), third
  person on behalf.
- Every new string through `drT`. No Hindi file (X-5). The three wrong Hindi drafts (spec §16) are
  the designer's to fix before native review.
- The 13 differences (X-2, X-4, X-5, X-8, X-9, D-1..D-8) keep the build's interim until Surbhi
  answers the analyst's plain list. Each answer is a wording or placement change, not a design
  change.

### 2.8 What I will NOT build

- No agency export, report filter or print format (PRIV-7: Alvoraa produces nothing).
- No Payroll Entry filter or slip refusal for agency staff (Q-S1 b) - only if the manual step is
  missed once.
- No Way C (monthly allocation script).
- No second switch for 067's lines (Q-S7).
- No server cap on "Paid Leaves left" (AC-34).
- No change to `hr_api.py`, `hooks.py`, `inbox_api.py`, the report's columns, or any DocType but the
  rule set and the new child.
- Not the findings F-1..F-7 - including F-3 (`_hr_target_employee` company-only), which I work
  around in 2.5 rather than fix. Each is a ticket for Surbhi to decide.

---

## 3 · Build order - small steps, each with its own tests

Already built and on `dev` (version 1). **Not rebuilt; re-proved** by the existing tests in the full
run and by rehearsal items 1-10:

| Item from the brief | Where it lives | What proves it |
|---|---|---|
| Office credit on the 1st, 15-day minimum | rule set values (configuration) + `summarise_month` gate, E6 | `test_payroll_month`, `test_leave_063_engine`; rehearsal Test-901..903, 907/908 |
| LWP limit 5, current month | `validate_leave_application` | `test_leave_063_rules` |
| HR approves LWP | `_can_action_leave` LWP branch | `test_leave_063_rules`, `test_leave_permissions` |
| Cancellation | `hr_api.cancel_leave`, N-5, N-6 | `test_leave_063_card_cancel`; ceiling 70 |
| Chain notice | `notify_chain_on_approval` | `test_leave_063_rules` (chain cases) |
| "Paid Leaves" type | **release step** (desk, by hand) + `lock_paid_leaves` | lock tests; RC-6 reads the flags back |
| Way B | **no code** - desk procedure (section 6.2) | AC-148/149 by hand on the synthetic site |

New work, in order. Each step: tests first where a guard is involved, then break the guard on purpose
and see the test go red (change-process rule). Neighbour modules after each step; **the full suite
once, at the end**.

| Step | What | Files | Tests (new unless marked) | ACs |
|---|---|---|---|---|
| **0** | Worktree `.claude/worktrees/063-v4` on `slice/063-v4` from `origin/dev` **after** ALV-215 lands on `dev` (else rebase onto it before step 1 ends). Work-board row. Bring the 063 v4 documents across | - | - | - |
| **1** | Child DocType + Table field + `_check_credit_rows` | new `alvoraa_leave_credit_row/` (json, py, `__init__`), rule set `.json` (one field), rule set `.py` (one method, one call) | `test_leave_credit_rows_063.py`: each refusal (from > to, not from 0, gap, overlap, short last row per length, negative, falling credits), DTC's 10 rows save, an empty table saves, HR Manager reads but cannot write, a row change shows in the Version row | AC-130, AC-131 |
| **2** | Engine: `credit_rows_for` (SEC-18) + the `summarise_month` branch (round down, halves, cap, next at, not in paid days, encashed 0, note from the row's designation) | `payroll_month.py`, `payroll_slip.py` | Pure, in `test_leave_063_engine.py`: every edge of AC-119..121, 12.5 → 1, 25.5 → 3, 31 → 4, cap by class B, 14.5 → next 4.5 more, cap leaves next empty, old callers unchanged. Site, in `test_leave_credit_rows_063.py`: SEC-18 a-g, SEC-20 a-e with a **submitted Salary Structure Assignment, Basic 12,000**, desk report row and note, designation changed mid-month (W4) | AC-119..AC-129, AC-132 |
| **3** | Card list two, Apply list, preview, Q-S2 on behalf with the scope check | `leave_rules.py` | Key **equality** per list (office and table); table payload holds none of `to_be_paid_out`, `paid_days`, `daily_rate`, `earning_basic`, `gross`, `net`; Basic 31,000 never in the response (AC-18 restored - the fixture carries a salary); Anil (other branch) on behalf gets no figure; Ritika gets it; No Leave and Contract sentences; query count **equal** at 20 and 400 staff for an office and a table person, number recorded | AC-17, AC-18, AC-23, AC-133..AC-144 (server side), AC-19 as amended by Q-S2 |
| **4** | HR notice + the counter | `leave_rules.py` | HR in scope told once, approver not, employee not, Anil not, an HR user in the chain told once with chain wording; `SECRET-REASON-063` absent from HR notices too; the "told" line counts managers only; decline / withdraw / cancel tell no one new | AC-59 (HR), AC-61, AC-145, AC-146 |
| **5** | Screens | `portal.js` lp- block; `panels.css` only if no chip class fits | `portal_leave_063_test.js` gains the 23 Housekeeping rows (R-76..R-98) and X-8 / X-9; by hand: walk the 98 rows on the running page, 390 px and 200 % zoom, keyboard only | R-76..R-98, AC-8, AC-80 |
| **6** | Rehearsal additions (synthetic only) | `scripts/seed_rehearsal_063.py` (new cases Test-913..920), `scripts/rehearsal_063.py` (`shape` adds the Housekeeping counts) | Items 11-15 of AC-108 (section 5) | AC-108 |
| **7** | Full suite once in my own throwaway container (both batch summaries read, not tailed); `scripts/check_app_integrity.py`; DOM checks; then **stop for review** | - | - | - |

**Size, honestly:** about 250-350 lines of Python, 150-250 of JS, 1 new DocType, 2 new test files,
35-50 new tests. One to two working sessions plus the rehearsal.

**Commits** (one concern each, in the worktree, never pushed without Surbhi's word):
1. The rule set holds a checked table of leave earned by days present
2. The engine reports table credit for agency staff and never pays it
3. The Leave page and Apply form show earned-so-far for table staff; HR in scope sees it on behalf
4. HR is told of every approved leave; the told line counts managers only
5. The Leave page draws the Housekeeping card and sentences (prototype v4)
6. Rehearsal: Housekeeping cases and shape counts
7. (docs) implementation notes

---

## 4 · How the rule set switches, and how each gate is evidenced

**The switch is the one existing box: `enabled` on DTC's `Alvoraa Payroll Rule Set`.** Ticking it
turns on, in one request: the card, Paid Leaves and LWP on the portal, the limit and month rule, HR
approval of LWP, the chain and HR notices, half-day pay, the Housekeeping table, the engine's paid days
on every DTC slip, and 067's red and green lines. Unticking it turns all of that off. Only System
Manager can tick it, and the Version row records who and when.

**It stays off until all five gates hold, in this order** (spec 15.3; AC-150):

| Gate | Evidence (kept in 07 §5 / the release record; anything naming a person stays outside the repo) | Who |
|---|---|---|
| **G-A1** ALV-215 field rights on every tenant | Deploy run for the ALV-215 release; read-only query on DTC: the job and pay fields at level 2, ESS read-only (RC-14); AC-151 passes on the synthetic site | Engineer reads; Surbhi releases |
| **G-A2** Synthetic rehearsal passes | The rehearsal note: AC-108 items 1-15, each with pass/fail and its number; the extra October cost line shown to Surbhi; rollback timed | Engineer runs; Surbhi reads |
| **G-A3** Surbhi checks the 10 Housekeeping rows | Her dated "checked" against DTC's document; a photo of the document kept with the evidence. The builder typed them, so the builder is not the checker (SEC-19) | **Surbhi** |
| **G-A4** A fresh, checked DTC backup | 07a §1.1 take, §1.2 verify (`GZIP-OK`, size near 6.5 MB, `-- Dump completed`, four files incl. the site config json), §1.3 copy off the server - taken **after** the last desk data step and before the tick. The 25 Oct 14:41 backup does not count (Q-S10) | Surbhi runs (server access) |
| **G-A5** Surbhi's word | Dated, in her own message | **Surbhi** |

Q-S7 is accepted, so 067's lines need nothing more: they ride on the same five gates.

---

## 5 · Rehearsal plan (synthetic data, throwaway container)

**Where:** a new container built from the slice branch (CRLF stripped from `.sh` files first, as the
Windows trap requires), its own Redis, its own site `rehearsal063.localhost` on its own database.
**Never** `hrlocal-bench`'s shared sites (`test_site`, `ppj.localhost`), never dev's DTC, never
production, never a copy of production data. Both scripts already refuse any site ending in
`alvoraa.co`. Mute email and pause the scheduler on the site first.

**Data:** `seed_rehearsal_063.py` as today (Test-901..912, items 1-10, passed 30 of 30 on 22 Oct) -
re-run on the new code to prove nothing moved - plus new cases:

| Case | Set-up | Expected |
|---|---|---|
| Test-913 | Housekeeping, Contract, A; October; days present 5, 6, 12, 12.5, 13, 18, 19, 20, 25, 26, 31 (one person per value or one person re-seeded) | 0, 1, 1, 1, 2, 2, 3, 3, 3, 4, 4 |
| Test-914 | Same, November (30 days): 20, 26, 30 | 3, 4, 4 |
| Test-915 | Same, February 2027 (28 days): 4, 5, 11, 12, 17, 18, 24, 25, 28 | 0, 1, 1, 2, 2, 3, 3, 4, 4 |
| Test-916 | 24 worked + 2 approved Paid Leaves / + 2 Open / + 2 approved LWP | 4 / 3 / 3 |
| Test-917 | Housekeeping, No Leave, 31 present; Permanent Housekeeping A, 20 present; Contract Pantry A; Housekeeping rows deleted | 0 / office rule (4, in paid days) / 0 / 0 |
| Test-918 | Housekeeping A, Basic 12,000, 26 present: slip saved twice | `payment_days` = worked days only, same both times; no Additional Salary; identical with the rows deleted |
| Test-919 | A Payroll Entry for the month; HR deletes the Housekeeping rows from "Get Employees"; slips made | zero slips for anyone marked agency-paid (AC-147); their Salary Structure Assignments unchanged |
| Test-920 | Rule set rows edited mid-month; designation changed mid-month | next working-out uses the new rows / the current designation (E-43, W4) |

Item 14 (shape) is a **read-only count on DTC, on Surbhi's word**: 42 Housekeeping, 36 with a class
that earns, 6 "No Leave", 0 Permanent Housekeeping. Counts only, any cell under 5 printed as "<5".

**Also on the synthetic site:** the 10 rows typed **in the desk** (not by script) from the written list,
to time the release step; the rollback (delete the rows; untick) timed; AC-148/149 (Way B) by hand;
one card load timed for a full-month Housekeeping person (budget 500 ms) and its query count recorded.

**What it cannot prove:** DTC's real punch quirks, the real shift mix, and whether DTC's document
matches what Surbhi told us - that last one is G-A3.

---

## 6 · Migration and release

### 6.1 What the release creates

| By | Where | What | One-line rollback |
|---|---|---|---|
| `bench migrate` (deploy) | every tenant | Table `tabAlvoraa Leave Credit Row`, empty; one Table field on the rule set. No patch, no backfill, nothing recomputed | Code rollback (DevOps, about 35 min); the empty table is harmless if left |
| System Manager, desk | DTC | Leave Type "Paid Leaves" (spec 7.5 flags); read the flags back (RC-6) | Leave it; Frappe refuses a delete once used, and it does nothing while the rule set is off |
| DTC HR, desk | DTC | Leave approvers for staff with none (RC-8, count to refresh) | Clear the field |
| System Manager, desk | DTC | Office values (7.6) + a comment quoting Surbhi | Put the old values back from the Version row (30; 7.5/1/4, 10/1/3, 7.5/0.5/2) |
| System Manager, desk | DTC | The 10 Housekeeping rows (7.1) | Delete the rows |
| System Manager, desk | DTC | Tick `enabled` (last) | **Untick it** - the fastest rollback for everything above |

**The backup rule (07a OPS-10):** before **each** DTC data step above, take, verify and copy off a
backup (07a §1.1-1.3). Roll back by hand from the written list, never by restoring the dump - a
restore erases everything entered since. The last backup before the tick is gate G-A4.

### 6.2 Way B - the bridge, now until switch-on (no code)

Works on production today and keeps working after Way A is deployed with the rule set off
(`validate_leave_application` returns at once when no rule set is enabled - read in the code).

1. Desk → Leave Application → New. Employee in your scope; type "Leave Without Pay"; dates in the
   current month only; half day if asked.
2. Status Approved, Save, Submit. Never for yourself (the existing `refuse_own_submit` stops it).
3. Keep each person to 5 days a calendar month, waiting and approved together - **the system does
   not check this before switch-on.**

**One read-only check before HR starts:** HR Settings "Leave Approver Mandatory In Leave Application"
at DTC. If on, HR must also fill the approver field, or the save fails. I could not check the value.

What Way B does not do: no card, no notice, no limit, no month rule. Once switched on, a Way B LWP in
that month counts toward the 5 (AC-149, E-42). Stop using it at switch-on.

### 6.3 Release order

Each step only on Surbhi's word; evidence into 07 §5.

1. ALV-215 to dev, then main (its own slice) - G-A1.
2. This slice to dev; prove it landed (pin file, container, file - deploy-trap memory); AC-25 holds
   on a dev tenant with a rule set switched off.
3. To main; production deploy with DTC's rule set **off** (AC-25 on DTC: both types refused, no card).
   `bench migrate` adds the empty table.
4. On DTC, each with a backup first: "Paid Leaves" (RC-6), approvers (RC-8), RC-7, RC-9..RC-11 reads,
   office values (RC-12), the 10 rows (RC-12), Surbhi checks the rows (RC-13 = G-A3), RC-14, RC-15.
5. Fresh checked backup (G-A4), then Surbhi's word (G-A5), then the tick.
6. After: AC-104 on two named staff; the first Payroll Entry without Housekeeping, then the check
   (6.4); slips stay draft until HR compares five against the desk report.
7. Tell DTC HR in writing: never send *Salary Components and Workings* to an agency (PRIV-7); the
   agency's Excel comes from outside Alvoraa; take Housekeeping out of every Payroll Entry.

### 6.4 Q-S1 (a): the monthly check, with no code

After HR makes slips each month: desk → Salary Slip list → filter Payroll Entry = this month's,
Designation = Housekeeping (Salary Slip carries `designation`, read in hrms' salary_slip.json) →
must show **zero** rows, draft or submitted. A saved list filter, so HR clicks one link. It cannot see
a Permanent Housekeeping person (there are none today); the engineer's read-only release check
(AC-147) uses `dtc_agency` on Employee instead. If a slip is ever found, HR deletes the draft (or
cancels a submitted one) and Surbhi decides on Q-S1 (b).

---

## 7 · Rollback, in one place

| What went wrong | Rollback | Time |
|---|---|---|
| Anything after switch-on | Untick `enabled` | one save; next request is off |
| A wrong Housekeeping row | Edit or delete the row (Version row records it); untick if pay already moved | minutes |
| Wrong office values | Old values from the Version row | minutes |
| The code itself | DevOps code rollback (07·OPS-4) | about 35 min |
| Data | Never restore the dump for a desk change; it is the last resort | - |

Open requests stay Open after a rollback; HR declines them. Submitted leave stays.

---

## 8 · Parallel-work check

**Incoming:** `origin/dev` is at f207e82c (slice 066's switch). 067 (e0fe3f22) and 063 version 1
(24ee6549) are both inside it. Nothing new arrived since the spec was written. I read the 066 and 067
diffs to `payroll_month.py` and `payroll_slip.py`: grooming fields and engine lines; my change sits
in the leave block and the Employee read, not in their lines.

| File I will change | Hot? | Who else is in it (branches not on dev, work board) | Plan |
|---|---|---|---|
| new `alvoraa_leave_credit_row/` | new DocType | nobody | claim on the board |
| rule set `.json` | DocType JSON | nobody | claim on the board; one field |
| rule set `.py` | medium | **ALV-215** (`slice/063-field-rights`, 8 commits, not pushed): adds `on_update` | **Sequence**: ALV-215 lands first, I rebase. Different methods, so no clash expected |
| `payroll_month.py`, `payroll_slip.py` | medium | 066, 067 - both already on dev | Build on top; rebase before each step |
| `leave_rules.py` | mine | nobody | - |
| `portal.js` lp- block | **yes** | **070-readable-on-phone** (ALV-217, built, not pushed) changes `lpSubmit`, `submitLeaveApp`, `openLeaveModal`, `renderLeaveApps`, `lpIsDtc`, `lpDoCancel` and `portal_leave_063_test.js`. 070-seats, 071, 064, 065 change `pos*`/`oc*` only | **Sequence**: 070 lands on dev first, I rebase before step 5 and run its phone test too. If Surbhi wants 063 first, 070 rebases on me. **Ask** (question A-3). Steps 1-4 do not touch `portal.js`, so they can start now |
| `panels.css` | yes | 070-seats, 071, 065, 064 append blocks | Append to the lp- block only, if at all |
| `portal_leave_063_test.js` | test | 070-readable-on-phone | Same sequence as `portal.js` |
| `scripts/seed_rehearsal_063.py` | script | 067 appended R-5b checks (on dev) | Append new cases at the end |

**Main checkout** (`C:/Surbhi-Git/hr-app`, branch `slice/066-grooming-switch`) holds another
session's uncommitted edits to `CLAUDE.md`, `.claude/context/*`, two skills and many untracked docs.
Not mine; not touched. **This worktree** (`067-pay-slip-marks`) holds the 063 v4 documents,
uncommitted - also not mine to commit; they come across in step 0.

**Other developers:** I cannot see other machines. Surbhi, is anyone else working in the pay engine
or the leave screens?

**Pin tests:** each step's test file names the feature (`test_leave_credit_rows_063`, the HR-notice
and counter tests in `test_leave_063_rules`), so a bad merge fails CI.

---

## 9 · Questions for Surbhi before I build

| # | Question | My recommendation |
|---|---|---|
| **A-1** | Q-S2 said HR may see **Housekeeping** leave days on behalf. Should office staff (Rohit) get the same on behalf? | **Yes** - same days, already in HR's desk report, and the code is simpler without the exception. Until you say so, I build Housekeeping only, as you said |
| **A-2** | The engine's note and the card print the designation from the table row, so the code never names "Housekeeping" (SEC-15). DTC sees the same words. OK? | **Yes** |
| **A-3** | Slice 070 (phone) and this slice both change the leave screens. Which lands on dev first? | **070 first**; I start the server steps now and rebase before the screens |
| **A-4** | ALV-215 lands on dev before I start step 1? | **Yes** - it is gate G-A1 anyway |
| **A-5** | Remove the stale `slice/063-dtc-leave` worktree and its demo containers (all 17 commits are on dev)? | Yes, but it is your call - the demo on :8063 may still be in use |

Waiting on drafts already in hand (no answer needed from me): the HR notice wording (X-6/Q-S3), the
Housekeeping "Leave encashed" figure (Q-S5, built as 0), the analyst's plain list of the 13
differences (Q-S4). Each lands as a one-line change whenever it arrives.

Security must reword SEC-1(c) to match Q-S2 and add the extra card keys (spec Q-1) - paperwork, not
a blocker for steps 1-2.

---

## Subtract pass

Removed while writing this version:

- **`hr_api.py` and `hooks.py` changes** - the on-behalf figure, its scope check and the HR notice all
  fit inside `leave_rules.py` functions that `hr_api` and the existing hook already call.
- **A separate "table credit" helper function** - its only caller would be `summarise_month`, so it is
  a branch there; "next at" rides on the summary instead of a second calculation.
- **A stored "earned" figure or cache** for the Apply list - it re-runs `month_summary`; only if the
  measured time misses 500 ms would I reuse the card's figure.
- **A Payroll Entry filter or slip refusal for agency staff** - Q-S1 (a) is a desk filter.
- **A "which designations" field on the rule set** - the rows name their designation.
- **The spec's literal "Housekeeping" in the note** - the row's designation instead (SEC-15).
- **A new chip style** - reuse an existing class first.

Kept, and why: the child DocType (SEC-19 needs a save check, nothing cheaper has one); the own-view
Housekeeping card (in the prototype, cheap beside the office card); `month_length` in the card (the
server's date decides the month, so the page and the server can never disagree at midnight).
