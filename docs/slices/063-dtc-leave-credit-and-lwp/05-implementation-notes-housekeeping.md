---
slice: 063-dtc-leave-credit-and-lwp
artifact: 05-implementation-notes-housekeeping (the Housekeeping leave days and attendance part, built from strategy v2)
author: hrms-fullstack-engineer
date: 2026-10-27
status: built and tested on a local throwaway bench only. Nothing pushed. No server touched. The rule set stays OFF at DTC and nothing here switches it on.
branch: slice/063-housekeeping-leave, from origin/dev 5f423750 (see "What moved while I worked")
inputs: 04-impact-and-strategy.md v2, 03-functional-spec.md v4.0, 03a-surbhi-decisions.md, 03b-surbhi-answers-2026-10-25.md, 01c-security-privacy-requirements.md, prototype-v4.html (all read from the 067 worktree; 03a, 03b and the prototype are copied here)
scope split (Surbhi, 27 Oct 2026): DTC runs payroll outside the portal and only downloads the Salary Components and Workings report as Excel. So this slice builds the leave DAYS and attendance parts and HOLDS the payroll parts.
---

# 063 Housekeeping leave: implementation notes

## 0 · Bad news first

1. **Nothing here has been seen in a real browser.** The Leave page was walked with the jsdom
   page test (164 checks, 0 failed) but not on a phone or at 200 % zoom. AC-8 and AC-80 need
   a person with a screen. See section 7.
2. **The 14 Hindi lines are a draft in this file only.** No Hindi file is installed (X-5), so
   nothing on screen is in Hindi. A native speaker must check the draft first.
3. **"Not paid by DTC" and "DTC's attendance" are in the code as plain words.** The spec asks for
   them, but SEC-15 says no company name in code. The designation is read from the table row (as
   agreed, A-2); the company name is not. Section 6, item 2 asks Surbhi.
4. **The salary report was not changed, and its Net cannot change.** The new "Why" note and the
   Leave earned / used / encashed columns come from the same engine call. `paid_days` for a
   Housekeeping person is the same number with the table on or off (proved by a slip test).
5. **The payroll parts are held, as you said**: nothing about the Salary Slip, the Payroll Entry,
   the desk list filter or the 067 marks was built or changed. No stop-and-report was needed:
   reading the month summary read-only was enough.

## 1 · What was built, file by file

Ladder rung for each part is the one in strategy section 2.1. Nothing cheaper worked.

| File | Change | Rung and why |
|---|---|---|
| `doctype/alvoraa_leave_credit_row/` (new: json, py, `__init__`) | Child DocType, 5 fields: designation (Link), month length (28-29 / 30-31), days from, days to, credits. No permissions of its own | 5, new DocType. Nothing existing has a save check for uneven rows by designation and month length |
| `doctype/alvoraa_payroll_rule_set/*.json` | One Table field `leave_credit_rows`, after the leave classes | Part of the same step |
| `doctype/alvoraa_payroll_rule_set/*.py` | `_check_credit_rows`, called from `validate` | Refuses, naming the rows: a row that runs backwards, a first row not at 0, a gap, an overlap, a last row that stops short (31 for 30-31, 29 for 28-29), negative leave, leave that falls as days rise. Nothing runs if the table is empty. In memory, no query (SEC-19) |
| `payroll_month.py` | `summarise_month` takes `credit_rows` and `credit_designation`; two new summary fields (`credit_table`, `next_credit_at`) | 4. Whole days present pick the row, the class figure caps it, no 15-day gate. The credit is reported, never added to paid days, and Leave encashed stays 0 (SEC-20, Q-S5). The Why note names the designation from the row |
| `payroll_slip.py` | `credit_rows_for` (SEC-18: category earns no leave credit, the rule set has rows for the designation, the class gives credit, a 28 to 31 day period); `month_summary` reads `designation` in the Employee read it already made and passes the rows; one note for an odd period length | 4. No new query. A second caller needs the same decision, which is why it is a function |
| `leave_rules.py` | Card list two (`CARD_KEYS_TABLE`) beside list one (`CARD_KEYS_OFFICE`); `credit_facts` knows the table; `table_summary`, `paid_leaves_left`, `_table_card`; Apply list and preview carry the days figure and the Housekeeping facts; HR told of every approval; the "told" counters count managers only | 4. Everything stays in the module that already holds the leave rules, so `hr_api.py` and `hooks.py` are untouched |
| `portal.js` (lp- block) | `lpRenderTableCard`; the class sentence for a zero class; the Apply sentences R-91..R-95; X-9 help text | 4. Every number and the designation come from the server; only the words around them are in the file |
| `panels.css` | One class, `.lp-chip` (the "So far" chip) | No existing chip class fits |
| Tests | see section 4 | |

**Not touched, on purpose:** `hr_api.py`, `hooks.py`, `employee_field_rights.py`, the salary report,
the Salary Slip hook, Payroll Entry, Additional Salary, anything in `scripts/` (the rehearsal scripts).

## 2 · Acceptance criteria: built, held

**Built and proved** (test names are in section 4):

| AC | What | How |
|---|---|---|
| AC-17, AC-18 | Card keys equal list one (office) or list two (table); no pay field, and the 12,000 Basic never appears | key-equality tests on both lists; a JSON search for pay names and the Basic |
| AC-119..AC-121 | Every row edge for 31, 30 and 28 days | pure tests, one assertion per edge |
| AC-122..AC-124 | Approved Paid Leaves days count as present, open ones and LWP do not; the class caps the row; No Leave earns 0 | pure and site tests |
| AC-125, AC-126, AC-127 | A Permanent person keeps the office rule; another designation and a deleted table give 0; no 15-day gate; Contract earns no marks | site tests on a real month |
| AC-128 (a, b, c, d, e) | Card has no pay; `payment_days` equals days worked alone (26, not 30); no Additional Salary; same with the rows deleted; office staff still get their credit (26 + 4) | real draft Salary Slips on the test site |
| AC-129 | Report row: earned 2, used, encashed 0, Why note from the row's designation | report test |
| AC-130, AC-131 | Seven refusals with the rows named; DTC's ten rows save; an empty table saves; HR Manager reads but cannot write; a row change shows in the Version row | site tests |
| AC-132 | Designation on the day decides | site test |
| AC-133..AC-139 | The card: figures, next step, the cap, short month, No Leave, 14.5 days, 0 days | server payload tests + the page test |
| AC-140..AC-143 | Apply list, preview and result sentences for Housekeeping; no special-day line; no "charged double" | server and page tests |
| AC-144 (as changed by Q-S2 and A-1) | HR sees days left on behalf, for people in their company AND branch; Anil (another branch) gets no figure | site tests |
| AC-145 | HR in scope told once each, not the approver, not the employee, not another branch; same subject; no type, no reason | site tests |
| AC-146 | The "told" line counts managers only | site test, both the approval reply and the employee's row |
| Q-S5 | Leave encashed shows 0 with the Why note | pure and report tests |
| X-8, X-9, R-16 wording | cap sentence, class sentence, "earn" | page test |

**Held (not built, by your scope split or because they are not leave days):**

| What | Why held |
|---|---|
| Anything changing a Salary Slip, a Payroll Entry or an Additional Salary | DTC now runs payroll outside the portal |
| AC-147 (Payroll Entry without Housekeeping), the desk list filter, Q-S1 | payroll |
| 067 pay-slip marks | payroll; untouched |
| AC-108 items 11-15 and the rehearsal scripts (`seed_rehearsal_063.py`, `rehearsal_063.py`) | strategy step 6; not in this brief's list. The site tests above cover the same cases |
| AC-148 / AC-149 (Way B) | no code; a desk procedure |
| AC-150 / AC-151 and the five gates | release steps, not code |
| AC-8, AC-80 by hand (390 px, 200 % zoom, keyboard only) | needs a person with a screen |

## 3 · The seven non-functional dimensions, against the code as written

| Dimension | Plan said | Code as written |
|---|---|---|
| Performance | degrades slightly, inside budget | A table person's card, Apply list and preview run one `month_summary` (the one the slip uses). The card query count is equal at 5 more staff (tested). No cache. Office people: one extra Employee column read, no extra query. The measured time of a full month is in section 4 |
| Security | neutral | No new endpoint, no `ignore_permissions`, no role change. The on-behalf figure is behind `permitted_employee_filters()` (company and branch) which the existing on-behalf path lacks (finding F-3, left alone). The rows can be edited by System Manager only; HR Manager reads |
| Reliability | improves | A wrong table cannot be saved. A period that is not 28 to 31 days gives 0 and a note. The HR notice sits inside the existing try/except, so it never blocks an approval |
| Scalability | neutral | Rows per rule set: a few dozen at most. Nothing per head |
| Maintainability | slightly degrades | One DocType, one check, one branch, one second key list. `leave_rules.py` grew; no helper is called once |
| Data integrity | improves | One source for the number: the card, Apply list, preview and report all read the same `month_summary`. Nothing stored. The "told" count is now true |
| Compliance / privacy | neutral | HR gets the same four facts they could already read. The table card carries no pay field; nothing goes to the agency (PRIV-7) |

## 4 · Tests: what I ran, with the real numbers

**Where:** my own throwaway bench: containers `hrlocal-063h` and `hrlocal-063h-redis`, site `test063h`
(a fresh site, ERPNext setup wizard run on it, the shared MariaDB with its own database). No server,
no shared site, no `docker cp` to anywhere but this container. Each module was run alone and waited
for. `bench run-tests` prints two batch summaries; I read both. The full suite was NOT run (CI does that).

| Module | Result (final run, after the last code change) |
|---|---|
| `test_leave_credit_rows_063` (new, 42 tests: save checks, who the table reaches, slip not moved, card, Apply facts, scope) | 18 + 24 = **42 OK** |
| `test_payroll_month` (12 new pure tests: every row edge, half days, cap, next-at, never paid) | **41 OK** (ran before the last two small edits to `leave_rules.py`, which this module does not import) |
| `test_leave_063_rules` (6 new: HR told once, not the approver or employee or another branch; told count; on-behalf scope) | **43 OK** |
| `test_leave_063_card_cancel` (key-equality changed to the two lists) | **17 OK** |
| `test_leave_063_engine` | **23 OK** (ran once, before the final edits; pure, imports no file I changed afterwards) |
| `test_payroll_flags` | **9 OK** |
| `test_salary_report` | **18 + 4 OK** |
| `test_pay_slip_marks_067` (neighbour of the slip hook) | **18 + 2 OK** |
| `test_leave`, `test_leave_permissions`, `test_leave_endpoint_access_173`, `test_leave_privacy_045`, `test_leave_ledger_035`, `test_leave_year` | **10, 12, 9, 11, 9, 3 OK** (the permissions, endpoint and privacy modules were re-run after the last change: 12, 9, 11 OK) |
| `portal_leave_063_test.js` (jsdom; the Housekeeping block of checks is new, and one old wording check changed) | **164 passed, 0 failed** |
| `portal_phone_070_test.js` (touches `lpSubmit`) | **93 passed, 0 failed** |
| `portal_dom_test.js` | **8 passed, 0 failed** |
| `scripts/check_app_integrity.py` (run in the container against the bind-mounted apps) | **OK, 1137 checks** |

**Failures along the way, honestly:**
- First run of my new module: 13 errors, all in my own test code (a keyword-argument slip, the test site
  had no ERPNext masters until I ran the setup wizard, leftover attendance and slips, and a Version row
  that Frappe skips in tests unless asked). Fixed in the tests, not in the product code.
- First run of `test_leave_063_rules`: 3 failures. They showed a real thing: **this Frappe sends a desk
  alert to its own sender**, so the approver, if also a manager in the chain, was already being told
  their own approval (Sunil told Sunil). That made "told (1 person)" untrue in the paper's own example.
  Fixed in `notify_chain_on_approval` (the approver is left out of both notices). See section 5, N-8.
- One of my tests had changed Sunil's manager and the approval committed it, leaving the test data
  polluted for the next test. Fixed (the undo now commits).
- `portal_correction_test.js` (the known flaky one, ALV-235) was not run.

**Speed and queries (one measurement, local, warm, 26 days of attendance so far this month):**
card for a Housekeeping person: 64 queries, 168 ms; for an office person: 63 queries, 64 ms. Budget 500 ms
per call. Query count is equal with 5 more staff in the company (tested). These are not DTC's numbers.

## 5 · Differences from prototype v4

The 14 differences Surbhi decided on 25 Oct (03a) are built as decided. Anything else is below.
Each needs a yes from Surbhi before it stays.

| # | Difference | Why | Recommendation |
|---|---|---|---|
| N-1 | The "So far" chip has its own small class (`.lp-chip`) | No existing chip style fits; the strategy allowed it | Keep |
| N-2 | The three figures sit in the page's four-column grid (a gap at the right), as drawn. On a phone they go two per row, as the prototype's phone view | Same as the prototype | Nothing to decide |
| N-3 | "Your leave class (No Leave) does not **earn** monthly Paid Leaves" now replaces "does not get" for **every** zero-class person, office and Housekeeping (R-16, v4 wording). The Apply help line keeps "does not **get**" (X-9, as specced) | The spec has the two words on purpose; they read oddly side by side | Ask Surbhi whether one word should do for both |
| N-4 | The card for a Contract person with a zero class now says the class sentence, not "Contract staff do not get...". That was the prototype's own change (Sushila) but it also moves the card of a non-Housekeeping Contract person who has a zero class | The rule is "a set class that gives nothing is the reason" | Keep; confirm |
| N-5 | The rule box's "one day earlier / later" wording is fixed text. The numbers beside it come from the table. If DTC's two tables ever differ by more than one day at each edge, the sentence would be untrue | Prototype wording, as drawn | Keep for DTC's table; say if the tables may change shape |
| N-6 | A-1 applied wider than the brief's wording: HR sees "days left" on behalf for **office** staff as well as Housekeeping, and the not-enough check runs on behalf for both | Surbhi's 25 Oct answer A-1 says so; the code is simpler without the exception | Keep |
| N-7 | "Not paid by DTC" and "DTC's attendance" are literal words in two strings | The spec and prototype use them | See section 6 |
| N-8 | The person who approves is no longer told their own approval in the chain notice. Before, a manager in the chain who approved got the alert too (this Frappe alerts the sender), so "told (1 person)" in the paper's own example would have read 2 | Needed to make AC-145 and AC-146 true. One line in `notify_chain_on_approval` | Keep |

## 6 · Needs Surbhi's decision

1. **N-3** one word or two ("earn" on the card, "get" in the Apply help).
2. **N-7** the company name in two strings (SEC-15). Rule set is per company, so "your company" in
   place of "DTC" would be safe, but the approved wording says DTC.
3. **Hindi** (section 8): a native speaker to read the draft before any Hindi file is installed.
4. **A-1 on office staff** (N-6) is live in this build. Say if you want it narrowed back.
5. **N-4 and N-8** (a zero-class Contract person's card wording; the approver no longer told their own approval) are small changes the paper did not spell out. Say if either is unwanted.

## 7 · What I could not verify

- A real browser: phone width, 200 % zoom, keyboard only, screen reader (AC-8, AC-80, R-75).
- The measured time of a full-month card on DTC-sized data. The local numbers are in section 4;
  they are not DTC's.
- That DTC's written table matches the ten rows (gate G-A3 is Surbhi's).
- The tests' behaviour on a site with real DTC data, on 1 or 2 of the month (several tests skip
  themselves near the 1st or the month end, as the older 063 tests do).

## 8 · Hindi draft (machine draft, for a native reader; no Hindi file installed)

The three lines the spec found wrong for Housekeeping, redrafted:

| Where | English (as built) | Hindi draft |
|---|---|---|
| Paid Leaves preview | Until {who} decides, {n} day is set aside from the {e} {you have} earned so far. Approved Paid Leaves days count as days attended. | {who} के फ़ैसले तक {n} दिन, अब तक मिली {e} दिन में से, अलग रखा जाएगा। मंज़ूर Paid Leaves के दिन हाज़िरी में गिने जाते हैं। |
| Half-day block | ... until then the other half counts as absent. (no special-day clause) | ... तब तक दूसरा आधा दिन गैरहाज़िर गिना जाएगा। |
| Leave without pay, result | If approved, it is recorded as leave without pay on DTC's attendance. {u} of 5 days of Leave Without Pay are now waiting or approved in {Month}. | मंज़ूर होने पर यह DTC की हाज़िरी में Leave Without Pay के रूप में दर्ज होगी। {Month} में 5 में से {u} दिन की Leave Without Pay इंतज़ार में है या मंज़ूर हो चुकी है। |

The new lines (card and Apply) follow the prototype's Hindi where it has one (prototype lines 344-362,
496-505). Two new lines have no draft in the prototype: the zero-class help line (spec H-24 has one)
and "told" counts. Nothing was added to any translation file.

## 9 · Subtract pass

Read the diff once more asking only what can go.

Removed or never added:
- A helper `in_my_scope` (called once) was folded into its one caller.
- A `.lp-three` grid class: the prototype uses the four-column grid with three figures.
- A designation key on the card: the designation rides inside `rows`, so key list two is exactly the
  spec's list.
- No new setting, flag, patch, cache, index, job or endpoint.

Kept: the child DocType (SEC-19 needs a save check), the second key list (SEC-1 and SEC-20), the
period-length note (the spec's own assumption, three lines).

Nothing else could be deleted and still meet the paper.

## 10 · What else moved while I worked

`origin/dev` was 5f423750 at the start. One commit came in later: `ba974baf` (`.claude` agent notes,
`[skip ci]`; no file I touch). Nothing of anyone's was overwritten: this worktree is mine only.
Compared with strategy v2 (written at f207e82c), `dev` now also carries ALV-215 (field rights),
ALV-217 (readable on a phone), 066 retention, 070 and 072 (seats), 075 (the 11 AM column). I read the
leave files and the report on the new dev; the leave code and the lp- block were as strategy v2 described.

## 11 · Known gaps, labelled

- **Intentional trade-off:** `rows.other_starts` is sent as numbers only; the "one day earlier/later"
  words are fixed (N-5).
- **Intentional trade-off:** the preview's not-enough check also runs for office staff on behalf (N-6).
- **Acceptable simplification:** a period that is not 28 to 31 days gives no leave and a note, and no
  guess.
- **Temporary debt:** the rehearsal scripts (strategy step 6) were not extended; the site tests cover
  the same cases. Removed by building step 6 when payroll comes back into scope.
- **Dangerous debt:** none found.
