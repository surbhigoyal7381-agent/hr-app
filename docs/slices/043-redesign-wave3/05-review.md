# 043 Wave 3 — senior architect review (step 5)

slice: 043-redesign-wave3 (Time and Pay)
branch: `slice/043-redesign-wave3`, on top of `slice/042-redesign-wave2` on top of
`slice/034-redesign-wave1`
reviewer: hrms-technofunctional-reviewer
date: 2026-09-25
inputs read: `00-impact-analysis.md`, `01c`, `02` revision 2, `03-implementation-notes.md`,
`07-devops-inputs.md`, Wave 1's `05-review.md`, my own Wave 2 review, and the full diff of
all 35 changed files against `slice/042-redesign-wave2`.

---

## 1. Verdict

**SHIP WITH FIXES.** This is the strongest of the three waves on evidence quality. Four
live defects were found and fixed — a whitelisted endpoint with no gate, a whole Employee
row on the Pay payload, an unscoped shift-type list, and an email telling a manager which
leave type a report's deduction came from — and each fix ships with a test that was
**proved able to fail** by breaking the thing it guards. The notes tell the truth about
what is not measured, which is rarer than it should be.

The blockers are one inherited file and two numbers that need your word.

`SHIP WITH FIXES` means "ready to present for deploy approval once F1 is fixed and F2–F3
have an owner". It is not itself permission to deploy.

**What I ran, and what I could not.**

| Ran | Result |
|---|---|
| `node scripts/run_dom_tests.js` | 5 run, 3 not run, **0 failed** (61 in the new Time/Pay file) |
| `python scripts/check_app_integrity.py` | 641 checks, OK |
| `python scripts/check_design_system.py` · `check_preview_flag.py` | OK |
| A div-balance walk of `parts/home.html` | **−1**, inherited from Wave 2. F1 |

**I could not run any `bench run-tests`** — there is no bench in this worktree. Every
Python figure below is the engineer's reported run, read from the notes. I did read the
new test files. **I also did not run `scripts/browser_check_time_pay.js`** — it needs a
served site, a real login and Chromium. See F5.

**No P0.** I traced `get_time`, `get_pay` and `get_deduction_explanation` end to end for a
cross-person read and did not find one. The one non-self path (`get_time(employee=…)`)
returns the month block and nothing else, and that is asserted.

---

## 2. Findings, worst first

### P1 — blocks the release

#### F1. The broken `home.html` comes through from Wave 2

`alvoraa_portal/alvoraa_portal/templates/includes/ess/parts/home.html:51` carries one
extra `</div>`, left behind when Wave 2 removed the week-presence card. I counted the tags
on this branch: depth **−1**, against **0** on Wave 1.

Effect: on the **live** portal Home, `home-left-col` closes 25 lines early, so the goals
sections fall out of the left column and the whole right-hand column falls out of the
grid. Nothing in CI sees it — the DOM tests drive the preview page.

Fix it on `slice/042-redesign-wave2` and rebase; do not fix it twice. Full write-up is
F1 of `docs/slices/042-redesign-wave2/05-review.md`.

---

### P2 — needs your decision or a written acceptance before release

#### F2. Three of five personas roughly doubled in wall-clock between 20 and 981 people, and the notes name only one

You asked me to judge the 656 ms. Here is the whole table from
`03-implementation-notes.md` §15, with the ratio added:

| `get_time` persona | 20 people (p50) | 981 people (p50) | ratio | p95 at 981 |
|---|---|---|---|---|
| employee | 97 ms | 75 ms | 0.8× | 128 ms |
| **manager** | 161 ms | **332 ms** | **2.1×** | **656 ms** |
| store HR | 94 ms | 84 ms | 0.9× | 110 ms |
| **company HR** | 75 ms | 127 ms | **1.7×** | 157 ms |
| **System Manager** | 66 ms | 129 ms | **2.0×** | 217 ms |

The notes call this "**the one number that is not good**" and treat it as a manager
problem. It is not one number. Three personas show the same shape, and the profile says
only 44 of 332 ms is SQL with no statement growing. So **something outside SQL costs about
twice as much on a 981-person tenant as on a 20-person one**, for three of the five
personas, and nobody knows what it is.

**Is it acceptable to ship?** Yes, for `dev`, and probably for production too — but not
silently, and this is why:

- The absolute number is small. 656 ms p95 on a local container with 981 people, on a
  screen a person opens a few times a month, is not a user-visible problem.
- The failure mode the budget exists to catch — a statement whose cost grows with the
  company — is genuinely absent. The query count is 35 at both sizes, the payload is
  byte-identical, and that was measured, not asserted.
- But "flat in queries, 2× in time" is exactly the shape that hides a real problem until
  a tenant is three times bigger. Two of the live tenants are small today. That will not
  always be true.

**What I would do**, in this order, and none of it blocks `dev`:

1. **Write the number down as an accepted miss with an owner and a date**, not as a
   sentence in the notes. A missed budget nobody answers becomes a number nobody believes.
2. **Spend one hour attributing it before production.** My first guess, and it is a guess:
   `_may_review()` calls `frappe.has_permission("Attendance Request", "submit")`, which
   builds a permission query and resolves User Permissions — and the three slow personas
   are the three where that returns True and a role set has to be walked. The cheap test
   is to measure `get_time` with `_may_review` stubbed to `True`. If the 2× disappears,
   it is Frappe's permission machinery and not this slice.
3. **Do not cap or cache anything to make the number go down.** The engineer already
   refused that and was right.

Owner: `hrms-devops-engineer` to attribute it; you to accept the miss meanwhile.

#### F3. `get_pay`'s "2 queries" measures the empty screen, and the full screen is unmeasured

You asked me to judge this too. **The engineer is right, is honest about it, and the
caveat is written in the notes** (`03` §15) — so this is not a reporting failure. But it
does mean **the Pay screen has no measured cost at scale at all**, and §13's budget of 15
queries is currently backed by nothing.

Reading the code, the shape is bounded and I can reason about it:
`_own_slips` is one `get_all` capped at 12; `_own_payslip` is one `get_doc`; there is one
`get_value` for the year-to-date; plus the feature-gate read. So roughly **5–6 statements
with a full payslip**, none of them per-person and none of them per-line. `_payslip_payload`
walks the child tables already loaded by `get_doc`.

*Inferred, not proven.* I would accept that reasoning and ship, **provided one thing
happens**: seed a handful of Salary Slips onto `test044` and re-run `measure_044.py` for
`get_pay`. It is one fixture function and one run. Until that is done, §13's Pay row
should say "not measured" rather than "2".

The real risk is not the query count. It is `get_doc` on a slip with a long salary
structure, and the PDF download path, neither of which is measured either
(`07-devops-inputs.md` flags the payslip PDF separately).

Owner: `hrms-test-automation-engineer` for the fixture; `hrms-devops-engineer` for the run.

---

### P3 — ship, but write it down with an owner

#### F4. Not retiring the two old endpoints is the right call

You asked me to judge it. **I agree with the engineer and would make the same decision.**

`get_attendance_calendar` and `submit_attendance_request` are AC-18 and AC-19. Their only
caller is `hrms-employee.html`, which is the page every tenant is on today. The screens
that replace them live on `/hrms-employee-next`, which is 404 on production behind two
locks (the `portal_preview` site flag, then a System Manager check). Deleting the
endpoints now takes a working calendar away from every customer and puts nothing in its
place — which is precisely what the slice's own release gate 2 forbids.

This is a clean **intentional trade-off**, not debt, and the thing that removes it is
named: the preview page becoming the real page, then the deletion as its own commit so a
revert is one step. Two conditions I would attach, both cheap:

1. **AC-18/AC-19 must be recorded as "not met, deferred with a reason"** in the
   traceability table, not left looking met. §13 of the notes says this; the AC table
   should too.
2. **The deletion commit must carry the same test shape as Wave 2's**
   `test_week_presence_retired_042.py` — a source walk with a positive control, plus a
   call-by-hand test. Write that requirement into the follow-up ticket now, while the
   reason is fresh.

Compare with Wave 2, where the equivalent endpoint **was** deleted: the difference is that
Wave 2 shipped the replacement card on the old page in the same commit, and Wave 3 cannot.
The rule being applied is consistent, and that is what matters.

#### F5. The Why? sheet's browser check skips itself when there is nothing to check

**Proven by reading.** `scripts/browser_check_time_pay.js:190-193`:

```js
if (pay.whys < 1) {
  console.log("  SKIP  the Why? sheet: this site has no deduction line with " +
              "an Additional Salary behind it. Seed one and run again.");
}
```

Everything that makes this script worth having — the rendered page, the real Attendance
Deduction, the absence of revision 1's false remedy on a real screen — is inside that
`else`. If the site has no seeded deduction the script prints SKIP, exits 0, and reads as
a pass.

This is the shape of lesson 2: *ask what must be true in the data for the claim to be
observable*. The notes do not record a run where `pay.whys >= 1`, so I cannot tell whether
those seven assertions have ever executed. The jsdom file covers the same wording and I
ran it — 61 assertions, 0 failures — so the wording is proven **somewhere**. What is not
proven is the thing this script exists for: that it renders correctly in a real browser
engine.

Smallest fix: make the script **fail** rather than skip when it finds no `[data-why]`,
and put the seeding in `fixtures_043` so anyone can run it. Or, if a skip is genuinely
wanted, print it to stderr and exit 2 — never 0.

Owner: `hrms-test-automation-engineer`.

#### F6. Take-home is handled honestly, but the two numbers do not explain themselves

You asked whether the screen handles the 555-of-800 problem honestly. **Mostly yes.**

What is built (`pay_api.py:308`, `next-pay.js:142-163`):

- `take_home` is `rounded_total`, named once in a module constant so Wave 2's "your
  payslip is ready" row cannot disagree with it.
- The hero shows it big under the label **"Take-home"**.
- When `net_pay !== rounded_total`, a second line reads **"Exact amount on the payslip:
  ₹X"**.
- `test_take_home_is_the_rounded_total` and `test_pay_api_TAKE_HOME_FIELD_is_rounded_total`
  pin both.

That is the right choice, and showing both rather than one is the honest half. What is
missing is the sentence that makes it usable. An employee sees two different figures, a
few rupees apart, with no word about which one their bank credited or why they differ.
On a shop floor in go-live week that is a support ticket, not a feature.

Smallest fix: one sentence under the pair — something like *"Your bank is paid the rounded
figure. The payslip shows the exact amount before rounding."* — **if** that is true. I
cannot confirm it is: the underlying decision (which figure the bank actually receives) is
open and is yours. Until it is answered, the screen should not assert either way, and the
label "Take-home" is already an assertion.

So: ship the two-number display, and either add the sentence once you have decided, or
soften "Take-home" to "Paid this month (rounded)". Owner: you, then
`hrms-fullstack-engineer`.

#### F7. `_subject` is the whole control for another person's month, and it has no company scope

**Proven, and pre-existing — Wave 3 did not change it.**
`attendance_correction._subject:280` reads:

```python
if not _may_review():
    ... refuse unless the employee is in my reporting line ...
```

and `_may_review()` is `frappe.has_permission("Attendance Request", "submit")` — a
**doctype-level** check with no document and no company narrowing. So anybody a tenant
grants that permission to (the code's own example is a Shift Supervisor) can open **any**
employee's month, in any company on the site, including their punch times.

Wave 3 does not widen this — `get_time(employee=…)` routes through the same function and
returns strictly less than `attendance_correction.month` already did (month only; no
leave, no rule, no pay, asserted by
`TestSomebodyElsesMonthCarriesNothingElse.test_no_leave_no_rule_and_no_pay_reach_a_manager`).
`01c` SEC-9 names `_subject` as the control on purpose, and `02` §5 records "whoever
`_may_review()` allows" as the intended store-HR rule.

So this is **not a Wave 3 finding**. It is recorded here because Wave 3 is the slice that
puts this data on a new, prettier screen, and because "whoever holds a submit permission,
across every company" is a wider rule than the phrase "a store HR person" suggests. Worth
one row in the risk register and a look in Wave 4 or 5, where `permitted_employees()`
could narrow it without changing anybody's screen who is correctly scoped today.

---

### P4 — backlog

- The static "no whole Employee row in a payload" check scans `hr_api.py`, `pay_api.py`
  and `time_api.py` only. `frame_api`, `inbox_api`, `home_api`, `staff_api` and
  `goals_api` are outside it, so the pinned debt list cannot grow *there* without anyone
  noticing. Widen the file list; the walker already works.
- `pay_api._accountable_contact` has a docstring whose bullet list is indented with
  spaces inside a tab-indented file. Cosmetic; the formatter's job.
- Three DOM test files are still "NOT RUN" for Wave 1's reasons, and one of the reasons
  names Wave 3 (ALV-111). They stayed not-run. Fine, but the reason string is now stale.

---

## 3. AC verification

Only rows where I disagree with the notes, or where the evidence deserves a word, are
listed. The rest I read and agree with.

| AC | Notes say | I find | Evidence |
|---|---|---|---|
| AC-6 (fixed key list on Pay) | met | **met, and well** | `hr_api.ME_FIELDS` + `_me_block`; `test_payslips_payload_043` asserts the payload, the *value* of the phone number, **and** that the fixture really had those fields set. Plus a source walk with a working positive and negative control (`test_this_check_can_actually_fail`, `test_it_does_not_fire_on_the_fixed_version`) |
| AC-17 (manager's email) | met | **met** | `attendance_deduction.notify` now sends one mail per recipient with its own body; the manager's body names days and no leave type. Three assertions, including the two bodies being unequal |
| **AC-18 / AC-19** (retire two endpoints) | not done, deliberate | **not met, correctly deferred** | F4. Record it as such in the AC table |
| AC-27 (every figure read, never recomputed) | met | **met** | `pay_api._explanation` reads `doc.*` throughout; nothing recomputes from the rule |
| AC-30 / AC-31 (payroll gate, one refusal sentence) | met | **met** | `PAYSLIP_UNAVAILABLE` is one module constant used by all four causes; `requires_feature(..., message=…)`. The decorator-order correction to AC-30(c) is right and the reasoning (`frappe/__init__.py:465`/`:483`) checks out |
| AC-43 (no `ignore_permissions` in the new files) | met | **met** | `_own_slips` keeps the flag in `hr_api`, where the pattern is declared and tested; `pay_api` and `time_api` carry none. The registry test now covers `pay_api.py` and `time_api.py` |
| AC-52 (shift types scoped) | met | **met** | Scope is "shift types in use in my company via submitted Shift Assignments, plus my own default", fails closed to `[]`, never an empty filter dict |
| AC-55 (encashment) | met | **met, and the diagnosis was corrected** | `leave_period` resolved per company; `currency` from `get_employee_currency`. §16 finding 3 is the engineer correcting their own earlier claim, found by a test that asserted a crash that does not happen |
| AC-57 / AC-58 (the Why? sheet's words) | met | **met in jsdom; unproven in a browser** | F5 |
| **§13 payload/query budgets for Pay** | measured | **partial** | Empty path only. F3 |

---

## 4. The seven dimensions — claim vs. what was written

| Dimension | Impact analysis claimed | I find | Note |
|---|---|---|---|
| Performance | improves | **improves, with F2 open** | Several calls became one call of 35 queries, flat in headcount; wall-clock is not flat for three personas |
| Security | improves | **improves** | A whitelisted ungated payslip list, an unscoped shift-type list and a whole-row payload all closed, each with a test proved able to fail |
| Reliability | neutral | **neutral** | No new job, no new external call. Notification sends are now independent, so one failure no longer stops the other |
| Scalability | neutral | **neutral for Time; unmeasured for Pay** | F3 |
| Maintainability | improves | **improves** | `_own_slips` and `_payslip_payload` as single definitions is the right call; the Why? chain has one place to change |
| Data integrity | improves | **improves** | Every figure on the Why? sheet is read from the stored record, not recomputed — so editing a rule cannot retro-change what a person was told |
| Compliance / privacy | improves | **improves** | See §5 |

---

## 5. Compliance verification

| Obligation | Mechanism in the diff | Test that proves it | Verdict |
|---|---|---|---|
| DPDP minimisation on the Pay payload | `ME_FIELDS` + `_me_block`, replacing a whole Employee row | `test_none_of_the_forbidden_fields_is_anywhere_in_the_payload`, plus a source walk with both controls | **discharged** |
| Purpose limitation — a colleague's leave type | `manager_body()`, separate sends | `test_deduction_email_043`, 3 assertions incl. the two bodies differing | **discharged** |
| Entitlement enforced on the server, not by a hidden menu | `requires_feature` on `get_payslips` | 4 assertions incl. "PermissionError not raised" when the gate is removed | **discharged** |
| A refusal must not be an oracle | one `PAYSLIP_UNAVAILABLE` for all four causes | `test_why_sheet_043`'s AC-28/AC-31 cases | **discharged** |
| **Automated decision — the person is told it was automated** | `how_it_was_decided` names the rule and the date and says nobody looked | 61 jsdom assertions passed here; the browser proof is F5 | **discharged** |
| **Automated decision — a named accountable human** | `_accountable_contact` falls back to *"your HR team — no individual is named on this rule yet"* | `accountable_named: False` is in the payload and asserted | **partial** — the fail-closed wording is correct and honest, but **no human is named**, and `legal-retention-rules-2026-09.md` records counsel's requirement of access and grievance for automated decisions. **D-7 is unanswered.** The fix is a field on the rule; `_accountable_contact` is the only place that changes |
| Showing a decision must not create a record about it | nothing written on the read path | `test AC-61: closing the Why? sheet sends nothing to the server` (I ran it) | **discharged** |
| Retention | nothing new stored | `03` §14 | **discharged** |

**No AI in this slice.** The late-coming rule is deterministic code on a schedule, and the
Why? sheet renders stored values. The AI-specific axis does not apply.

The one compliance item I would not let slip quietly is **D-7**. Counsel's note of
18 September requires a route to a human for an automated decision. What ships names no
human. The wording is the right fail-closed default — it does not pretend somebody
reviewed the case — but it is a default, and it is the only thing between an employee and
"the computer decided". One field on `Attendance Deduction Rule` closes it.

---

## 6. What to delete

Nothing. Wave 3 built less than it was asked to, on purpose, and said so. The only
deletions worth making are the two old endpoints, and F4 explains why not yet.

---

## 7. What was done well

- **Every guard was broken on purpose to see it bite** (`03` §17). Removing the
  `weekly_off` flag reddened four Python and three DOM assertions; removing the "it does
  not undo this deduction" line reddened one; writing the false remedy into
  `next-pay.js` fired the static check, which also proved that check reaches the new
  JavaScript and not only the Python. That is lesson 10 done properly, six times.
- **The fixture that recomputed itself was caught** (`03` §16 finding 6):
  `Attendance Deduction.validate` throws away a passed-in `deduction_days`, the year table
  summed to 0.0, and every assertion passed because 0 equals 0. Lesson 2 held.
- **The AC was corrected rather than obeyed.** AC-30(c) asked for `@requires_feature`
  above `@frappe.whitelist()`; written that way the endpoint refuses everybody. The
  engineer read `frappe/__init__.py`, wrote down why, and made the test assert *sameness
  with the two endpoints beside it* instead of a line order. That is the right shape of
  fix.
- **The pinned debt list is pinned with `assertEqual`, not `assertNotIn`** — so the five
  pre-existing whole-row endpoints can neither grow nor silently disappear. Lesson 5 held
  and no fifth was added.
- **The honest paragraphs.** "Where the rest of the time goes I could not attribute";
  "its query count at scale is not measured, and I am not claiming it is"; "I had half the
  diagnosis wrong". Those sentences are why this review is short.

---

## 8. Confidence

- **Proven:** F1 (counted the tags), F5 and F7 (read the code and the call sites), the
  DOM and static-check results (I ran them), and every AC row in §3 that I read line by
  line.
- **Read, not re-run:** every `bench run-tests` figure and every measurement in §15 of the
  notes. There is no bench in this worktree.
- **Inferred, and marked as such:** F3's reasoning that the full Pay path is about 5–6
  statements. That comes from reading `get_pay`, `_own_slips`, `_own_payslip` and
  `_payslip_payload`, not from a measurement.
- **Not checked:** the Hindi fixture, 200 % zoom, the payslip PDF path, and the browser
  script itself. The notes already say the first two were not run.
- **Unreviewable here:** whether the Why? sheet renders correctly in a real browser
  against a real deduction. The script that would answer it may have skipped itself
  (F5), and I have no served site to run it on.

---

## 9. The two questions I would put to you before production

Sorted must-know first.

1. **Which figure does the bank actually pay — `net_pay` or `rounded_total`?** (F6)
   I am reading the code as "the rounded total is what leaves the bank account", because
   that is what `pay_api`'s docstring says. If that is right, one sentence on the screen
   closes this and it is a P4. If it is not right, the hero is showing 400 people a number
   their bank did not pay, and it becomes a P1. **Ranked P3 provisionally**, on the
   engineer's reading.
2. **D-7 — who is accountable for a late-coming deduction?** (§5)
   A name on the rule, or "your HR team"? The fail-closed wording ships either way, but
   counsel's note asks for a route to a person. **Ranked partial, not discharged.**
