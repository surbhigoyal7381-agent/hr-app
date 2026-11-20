---
slice: 084-employee-regularisation-window
artifact: 05-review
author: hrms-technofunctional-reviewer
date: 2026-11-19
tier: 1
reviewed: worktree /Users/mac/hr-app/.claude/worktrees/084-employee-window, branch slice/084-employee-window, HEAD c162374b, base fd658eff (six commits b1d57b0a..c162374b)
ran on: container alv084-bench (image ghcr.io/surbhigoyal7381-agent/hr-app:dev-3830ed3, the engineer's own stack, site test_site) and the Mac checkout
---

# 084 Senior architect review

## Verdict: SHIP WITH FIXES

The guard is correct, binds every way in I could find, and fails closed. **No P0 and no P1.**
Three P2 items need a decision before this goes to dev, and none of them is a code defect:
an unapproved difference from the prototype, an accountability control that was promised in
the impact analysis and not built, and a test file that exists but is not in the commit.

**`SHIP WITH FIXES` means ready to put in front of you for a deploy decision. It is not
permission to deploy.**

## 0. What I checked, and what I could not

**Read in full:** the diff of all nine files against `fd658eff`, plus the surrounding code
each change now depends on (`month()`, `_subject`, `_working_days_away`, `raise_correction`,
`submit_attendance_request`, `team_days`, `acSubmit`, `gpErr`, `refusalWords`,
`orgOnBehalfApply`, `employee_field_rights.py`, `next-time.js`), and all ten slice artifacts.

**Ran myself, today, and saw the output:**

| Command | Result |
|---|---|
| `node alvoraa_portal/tests/portal_correction_test.js` (NODE_PATH to the shared `node_modules`) | **57 passed, 0 failed** — matches `04-test-report.md` |
| `node --check .../public/js/ess/portal.js` | OK |
| `git diff --stat fd658eff...HEAD` | 9 files, 989 insertions. No `deploy/`, no workflow, no Dockerfile, no DocType folder, no patch, no Custom Field (**AC-64 proven**) |
| `@frappe.whitelist` / `ignore_permissions` counts, base vs head, both files | 10/10, 4/4, 69/69, 71/71 — **unchanged (AC-69 proven)** |
| AC-50 repo-wide phrase grep | output in §6 below |
| `CI=true bench --site test_site run-tests --app alvoraa_portal --module alvoraa_portal.tests.test_attendance_correction` on `alv084-bench` | see §7 |
| `sed` on `frappe/model/document.py` inside the container | `has_value_changed` converts a string to a date when the stored value is a date (lines 699-715). The engineer's correction to their own disagreement 2 is right |

**Not checked, and I say so rather than guess:**

- The **full `alvoraa_portal` suite** did not finish under me either. I ran one module, not
  4,433 methods. **CI on the exact SHA is the only thing that will prove the other ~210
  files.** Nobody should read `04-test-report.md`'s partial run as a suite result.
- **No browser, phone, screen reader or 200% text check.** Every statement about what a
  screen looks like here comes from reading the DOM test and the source.
- **Live tenants.** I did not open DTC, Grace, aahr or dev. `get_default` on those sites is
  not read by me; I rely on the design fact that nothing in this diff writes the key.
- The **DTC user manual** and any Desk help text held in a database record (AC-50's tail).
- `test_scale_flatness_044`, `next-time.js` in a browser, Hindi.

## 1. Blockers

**None.** I tried to break the guard and could not, by reading. Specifically ruled out, each
traced in the code rather than assumed:

| Way round I looked for | What I found |
|---|---|
| `submit_attendance_request` inserts with `ignore_permissions=True` | Doc-event hooks still run (`attendance_correction.py` hook on `validate`; proven by the engineer's and the test engineer's route (b) tests, and by my own module run) |
| Create for today, then edit `from_date` back | `validate`, not `before_insert`, and `has_value_changed("from_date")` fires. Break-tested by two sessions |
| Take over somebody else's old draft by putting your own name on it | `employee` is in the watched field list (`attendance_correction.py` `refuse_own_day_outside_window`), and `test_putting_your_own_name_on_somebody_elses_old_draft_is_refused` covers it |
| `frappe.client.set_value` / `frappe.client.insert` / REST POST | Both go through `save()`/`insert()`, so `validate` runs. Covered only by the **untracked** test file — see M-3 |
| Self-grant the joining-day exception by editing your own `date_of_joining` | `date_of_joining` is permlevel 2 (`employee_field_rights.py:55`), and `refuse_own_locked_change` (`:203`) refuses it even for an HR person on their own record. **Proven by reading both.** |
| Leak somebody else's joining date | `_subject` builds another person's record from a field list with no `date_of_joining` (`attendance_correction.py:406-408`), and the `joined_on` block is inside `if is_self`. **Leak is impossible by construction, not by a check.** Good design |
| A dead button somewhere else on the product | `can_request_from` has exactly two readers in JS (`acDetail`, `acOutsideWindow`), both handled; `team_days` builds `direct_ids` from `_reports_to(me.name)`, which does not contain the caller, so it never offers a button on your own row (**proven**: `_reports_to`, `attendance_analytics.py:102-109`, returns only employees whose `reports_to` is the caller) |
| An unreachable screen left unguarded | `next-time.js` is the third screen that calls `raise_correction`. It shows the server's sentence for a `ValidationError` (`refusalSentence`, `next-time.js:161-167`, used at `:700`). **Proven by reading.** It shows no boundary before typing — accepted, OPS-27 |

## 2. Majors (P2) — each needs your decision, not a code fix

### M-1 · The day detail is an inline row, not the prototype's modal `role="dialog"` (AC-72)

*What happens:* on the Time screen an employee taps a day; the detail opens as a row under
the table, as it has since slice 042. The approved prototype (P3) draws a modal sheet with
focus moved in and Escape to close. AC-72 names `role="dialog"` as the oracle.
*Why it matters:* your standing rule (21 Oct 2026) is that every feature in the approved
prototype is built as drawn, and any difference needs your yes first. This difference was
found during the build, so you have not been asked.

**My judgement: accept the inline row. Do not build the modal.** Turning the day detail into
a dialog rewrites a component the manager and HR flows also use, including its keyboard
behaviour — scope this slice never approved, and exactly the kind of "while we are here"
work `no-over-engineering.md` forbids. The accessibility intent of AC-72 is partly met by a
different mechanism: the new own-day sentence carries `role="status"` and the refusal box
`role="alert"`, so a screen reader is told; and there is no focus trap to escape from because
there is no modal. **If you want the modal, it is its own slice.**
*Ranked P2 provisionally until you say; it is P4 the moment you write "accepted".*

### M-2 · Nobody will know who set the number (Gate 3 decision C2 / SEC-12 / AC-45..47)

*What happens:* `set_org_setting` writes `frappe.db.set_default(key, value)` and commits
(`hr_api.py:3436-3437`). Nothing records who changed it, from what, when. A year later, in a
grievance about a refused correction, there is no answer to "who set this to 0, and when".
*The impact analysis claimed otherwise.* `00-impact-analysis.md` §8 marks Compliance/privacy
**"Improves"**, and its reason is "an attributable log line for every org-setting change,
which did not exist". **That line is not in the code.** The implementation notes re-rate the
dimension honestly as "Improves, with a gap" — that correction is right, and it is the one
dimension where the proposal and the built code disagree.

**The engineer was right to stop.** `frappe.logger("security")` sits at ERROR on this image,
`.warning` is discarded, and you confirmed `security.log` is 0 bytes on the live dev site. A
line written at `.warning` plus a test that patches the logger would have been a green test
over a silent production — the exact false green this slice exists to remove. **This is the
best thing in the slice.**

*What it blocks:* **not the release** — the slice ships blank. It blocks **the first tenant
that sets a number**, which is also the moment counsel is asked (Gate 3 C1). Option (b) in
`03-implementation-notes.md` §3 — give the `security` logger its own level in one place —
also fixes `log_refusal` (SEC-17), whose lines have probably never been written on dev or
production either. That is a bigger finding than this slice and belongs to ALV-391.

### M-3 · The 18 independent tests are untracked and will not run in CI

*What happens:* `alvoraa_portal/alvoraa_portal/tests/test_employee_window_084_independent.py`
is `??` in the worktree. It is the **only** automated proof of the `frappe.client.insert` /
REST route (route d), the only proof on fixtures **without** a Shift Assignment, and the
source of the statement counts in `04-test-report.md` §7. If the branch is pushed as it
stands, none of that can be re-run by anyone, and the test report cites evidence the repo
does not hold.
*Smallest fix:* `git add` that one file and commit it (DevOps already asked for this,
OPS-36, and costed it at ~60 s of CI). I would not merge the slice without it.

## 3. Minors (P3)

### m-4 · The refusal tells an HR Manager to tell HR

*Inputs:* an HR Manager who has an Employee record, employee window set to 3, raises their
own day from ten days ago — on the portal, the Desk or the REST API.
*What happens:* `refuse_own_day_outside_window` throws a sentence ending **"HR can still fix
it: tell HR which day it was and why."** They are HR.
*Why it is wrong:* this exact fault was paid for once already. `portal.js:131-134` carries
`whoToAsk()` with the comment *"ALV-350: who to go to. Telling HR to 'tell HR' sent them to
themselves."* The new strings are built on the server, where `whoToAsk` does not exist, so
the lesson did not travel.
*Smallest fix:* in the hook, when the caller holds an HR role, end with *"another HR person
can still fix it"*. Two lines. **Or** accept it and write it down — Gate 4 Q2 already
accepted that a one-HR-person tenant is a dead end, and this is the sentence that dead end
reads.

### m-5 · "this person's own holiday list", said to the person themselves

The basis phrase is shared with the manager window (`_working_days_away`, deliberately — one
counter, one phrase), so an employee's own refusal reads *"counted in working days on **this
person's** own holiday list"*. Gate 4 Q8 wrote it as *"on **your** own holiday list"*. Spec
AC-9 quotes the third-person form, so the build matches the spec and not the gate. Frontline
employee on a phone; small, but it is the slice's own flagship sentence.
*Smallest fix:* a second translated phrase for the own-day path, chosen where the sentence is
built, not a second counter. **Or** leave it and say so.

### m-6 · AC-35 is built but has no test

The sheet-side refusal box. I traced it end to end and it works: `acApi` → `gpFetch` →
`gpErr` sets `e.server` from `_server_messages` (`portal.js:16080-16092`), and `acSubmit`'s
catch writes `#ac-refusal` and leaves the typed reason alone because the form is not
re-rendered. **So this is a missing proof, not a defect.** One more case in
`portal_correction_test.js`, the file that already does this for the other screen.

### m-7 · The exact words of AC-3, AC-5, AC-29(iii) and AC-73 are checked by eye only

Three sessions have now read these strings and agreed. A page-source test of the hint and the
save lines would stop the next person rewording them. `test_org_settings_allowlist_012.py:87`
is the pattern. Backlog, with an owner.

### m-8 · AC-50 is clean in the repo and open outside it

My grep (§6) finds no remaining sentence in product text, comments or tests that says an
employee's own day is unlimited. **The DTC user manual and any Desk help text stored in a
database record were not searched by me or by anyone.** That blocks the first number set at
DTC, not the release.

## 4. Nits

<details><summary>Four, none worth a round trip</summary>

- The HR save line for n≥1 — *"Saved. An employee can now ask about the last {0} working
  days."* — types a number of days in the browser, which AC-51 asks the slice not to do, and
  says "working days" for an employee who has no holiday list and will get calendar days. It
  is HR's own screen showing the number HR just typed, so the risk is small. The dropped
  example date is your approved decision and I agree with it.
- `arWindowNote()` picks the "today only" wording by comparing the server's date to
  `localToday()`. A phone clock a day out shows the other sentence. Wording only; the server
  still refuses correctly. Already found by the test engineer.
- `acNiceDay` duplicates three lines of `dateInWords` in a different format. Not worth
  merging.
- `docs/slices/060-manager-records-attendance/01c-...:1585` now holds a sentence that is
  false after this slice ("neither setting may narrow what somebody asks about their own
  attendance"). It is a dated record of what was decided then. **Leave it.** It is only a
  risk if somebody quotes a year-old artifact as current product behaviour.

</details>

## 5. Acceptance criteria

Walked one by one against the code. 73 ACs; grouped where the evidence is the same.

| AC | State | Evidence |
|---|---|---|
| 1, 2, 7, 8 | **Met** | `ALLOWED_ORG_SETTINGS[EMPLOYEE_FILING_WINDOW_KEY] = range(0,31)`; blank branch takes both keys (`hr_api.py:3411`); `employee_filing_window_days` returns `None` for blank and `0` for `"0"`. Break-tested twice (narrow the branch → 3 tests fail with the right PermissionError) |
| 3 | **Met, unproven wording** | Row is in `org-settings.html` before `org-on-behalf-on` and outside `org-filing-window-field`; label, `min/max`, placeholder "No limit", `aria-describedby` all present. Read by me. No automated check (m-7) |
| 4 | **Met** | `orgOnBehalfApply` touches only `org-filing-window` and `org-filing-window-field` (`portal.js:23559-23566`). **I read it; the new box is never greyed by the manager switch.** Not run in a browser |
| 5 | **Met, one approved departure** | blank / 0 / n≥1 lines present; the 0 line uses `res.today` from the server. n≥1 names no date — your decision |
| 6 | **Met in code**, not run in a browser | |
| 9, 10, 11 | **Met** | One hook, all three routes. Route (b) carries `ignore_permissions=True` and is still refused |
| 12 | **Met, wider than written** | `validate` + dates **and** `employee`. Break-tested on `before_insert`: the right tests fail |
| 13-18 | **Met** | boundary / day-before / range / joining-day-alone / day-after-joining / blank joining date |
| 19 | **Partial** | The test proves the Python signature rejects an extra kwarg (`TypeError`), not that a web call ignores one. The hook reads `Employee` and never the payload — **that is the real control, and I read it**. Good enough; the test is the weak part |
| 20, 21 | **Met** | leaver refused earlier; blank costs 0 statements, break-tested |
| 22-24 | **Met** | 0 = today only; a holiday pushes the boundary back; no list = calendar days and says so; a future `to_date` passes (your decision, ALV-387) |
| 25 | **Met, and it holds for a browser too** | `has_value_changed` converts a string date — I read `frappe/model/document.py:699-715` in the container, so an HR or employee save from a web form that only changes the explanation is not refused |
| 26 | **Met** | HR bound on their own day, free for everybody else's. Break-tested the wrong way round too |
| 27 | **Met** | One derivation (`employee_filing_from`) feeds the guard, the month and the history |
| 28, 29 | **Met (i, ii); (iii) by eye** | No `log_refusal`, no `log_error`; no name, id, holiday list or company in any sentence. The "no digit before day/hour" rule is not a test |
| 30, 31 | **Met**, reworded as agreed (a key only for `outside`/`joining`) | |
| 32-34, 36 | **Met** | DOM test, 57 pass, run by me |
| 35 | **Built, not proven** | m-6 |
| 37-42 | **Met** | DOM test presses Submit, asserts the call went, asserts the alert box and that typed text survives |
| 43 | Accepted behaviour, no test | |
| 44, 69 | **Met** | counts identical to `fd658eff`, **I ran the grep** |
| **45, 46, 47** | **Not built, by decision** | M-2 / ALV-391 |
| 48, 49 | **Met** | twelve false strings, same commit as the code |
| 50 | **Partial** | repo clean (§6); DTC manual and stored Desk help not searched (m-8) |
| 51 | **Partial** | true for every employee-facing sentence; the HR save line for n≥1 names a number (nit) |
| 52-54 | **Met** | two keys, two readers, neither reads the other |
| 55 | **Met by construction** | `_subject`'s other-person field list has no `date_of_joining` |
| 56, 57, 58 | **Met** | store-HR refused and logged `030-D4`; plain employee refused both ways; allow-list page test still green |
| 59 | Deleted by you | |
| 60 | **Met in code** | nothing in the diff writes the key. Not checked on a live tenant |
| 61-63, 66, 67 | **Release steps, not run** | |
| 64, 65 | **Met**, I ran both | |
| 68 | **Met** | same statement count with 300 more holiday rows |
| 70 | **Met** | boundary is not in `get_portal_context` |
| 71 | **Met** | break-tests by two independent sessions, listed in both reports |
| 72 | **Partial** | label, `aria-describedby`, `role="status"`, `role="alert"` present; **not a dialog** (M-1) |
| 73 | **Met by reading**, no automated check (m-7) |

## 6. AC-50: the grep, run by me

In the worktree, over the whole tree excluding `.git`, `node_modules`, `__pycache__`, for
`does not limit`, `not bounded`, `their own month`, `neither setting`, `never asked for`,
`a manager can file within`:

- **Product text, comments and tests:** two hits, both in
  `alvoraa_portal/alvoraa_portal/attendance_correction.py:1399,1401` — *"HR's own manual
  route is deliberately not bounded by it"* (true) and *"An employee raising their OWN day is
  not bounded by **THIS** window"* (true, and it names the new key). One hit in
  `alvoraa_portal/tests/portal_correction_test.js:294`, which is the assertion that an
  employee **never** reads the manager's sentence. **Nothing false left.**
- **Slice docs:** hits in 060, 045, 078, 012 and this slice's own artifacts. History, left
  alone, except the note in the nits.
- **Not searched:** the DTC user manual (a Claude Doc) and Desk help text held in the
  database. "Twelve" remains a floor.

## 7. Non-functional: the seven dimensions, proposal vs. built code

| Dimension | Impact analysis claimed | What the code does | Verdict |
|---|---|---|---|
| **Performance** | Neutral blank, ~+5 statements when set | Measured by two sessions: self month 17→19, history 5→7, hook **0** statements when blank or when dates did not change. Flat with 300 extra holiday rows. `get_requests_history` is called by four panels and three of them pay for the fourth | **Matches.** Budget (p95 ≤ 500 ms) **not measured at volume** by anyone; ~17 ms at three rows is not a scale claim |
| **Security** | Improves | An unguarded own-day path on three routes is closed by one server-side hook on the document. No new endpoint, no new `ignore_permissions`, counts unchanged (I ran the grep) | **Matches, improves** |
| **Reliability** | Neutral | Four early returns; a malformed date throws and the save fails closed; `_working_days_away` already swallows an unreadable holiday list. Ships blank, so a bug in the hook reaches nobody at release | **Matches** |
| **Scalability** | Neutral | One person, one boundary, pure Python per day. Nothing grows with headcount | **Matches** |
| **Maintainability** | Improves, one watch | One derivation, one predicate, one counter, twelve false texts fixed in the same commit. The two settings do look alike; the hint, the key names and `test_the_two_windows_never_read_each_other` keep them apart | **Matches, improves** |
| **Data integrity** | Neutral, one real risk | Nothing stored changes. Blank and 0 never collapse (break-tested). The stored number **outlives an image rollback** — old code ignores it while HR believes a limit is on (OPS-17/22, AC-62) | **Matches.** The rollback risk is real and the release note must carry it |
| **Compliance / privacy** | **Improves** — and the reason given was a new attributable log line | **The log line is not in the code.** No new personal data, no refusal record, sentences carry dates and fixed words only; `joined_on` cannot reach another reader | **Degraded against the claim.** M-2 |

**NFR budget check.** `nfr-budget.md` §2 asks for p95 ≤ 500 ms on a whitelisted call. Measured
16.7 ms (month) and 4.5 ms (history) on a three-row site. **Pass by reasoning, not by
measurement at 1,000 employees.** No new index, job, cache or migration, so nothing I would
expect to bend at month-end.

## 8. Compliance

Taken from `02-functional-spec.md` §16, row by row.

| Obligation | Mechanism in this diff | Test that proves it | State |
|---|---|---|---|
| DPDP: the correction route stays open and named | HR's route is never bound (`is_own_record` returns early for anyone else's record); every refusal names HR; blank is the default and nothing writes the key | `test_hr_is_bound_on_their_own_day_and_free_for_everybody_elses`; `test_every_route_refuses_an_old_day_and_names_the_date_and_hr` | **Discharged** |
| DPDP: minimisation — store no record of a refusal | No `log_refusal`, no `log_error`, no counter | `test_a_refusal_is_dates_and_fixed_words_and_is_not_logged` (patches both and asserts not called) | **Discharged** |
| No personal data in a message | Dates and fixed words only; the joining date is the reader's own | same test asserts the employee id, name, holiday list and company are absent from all four sentences | **Discharged** |
| No widening of who sees what | `joined_on` and `own_window` are inside `if is_self`; another person's record is built from a field list with no joining date | `test_somebody_reading_my_month_gets_no_joining_date_and_no_flags`, with a **real manager** who has a boundary of their own (the first version of this test passed under the break and was rewritten — that correction is why it is worth anything) | **Discharged** |
| Accountability for a rule that removes a right (Gate 3 C2) | **None** | — | **Not discharged.** M-2 |
| Counsel before the first non-blank value (Gate 3 C1) | Process step; the release note must carry it (AC-63) | — | **Open, blocks the first number, not the release** |
| EU AI Act, CERT-In | Not engaged — no model, no incident surface | — | n/a |

## 9. What to delete

**The subtract pass went far enough. I would delete nothing.** I looked for the usual things
and did not find them: no new DocType, no Custom Field, no new endpoint, no feature flag, no
cache, no abstraction layer, no settings page, no compatibility shim, no new dependency, no
new test file in the app. The cost ladder is honest — rung 2 (a stored default) plus rung 4
(new code in two existing modules and one hook) — and rungs 1 and 3 are refused for reasons I
checked: Frappe HR's only back-date control is `restrict_backdated_leave_application`, which
is leave, not attendance.

One thing I weighed and would **keep**: `set_org_setting` now returns `{"ok": True, "today":
...}` for one key and one value. It is a key-specific wart in a generic endpoint. The
alternative is to drop the date from the 0 save line as well, which would delete three lines
of Python and one branch of JS — but the prototype names the day for 0 and you approved
dropping the date only for n≥1. **Not mine to subtract.**

The two helpers the engineer already folded in (`_own_refusal`, `ownRangeText`) were the
right two to fold.

## 10. What was done well

Named as decisions, so they can be copied.

1. **Stopping on the log line instead of shipping a test that patches the logger.** A
   `.warning` that never reaches `security.log` plus a green test is exactly the false
   confidence this slice was written to remove. Refusing to buy it is the best judgement in
   the slice, and it also uncovered that `log_refusal` (SEC-17) may never have written a line
   on dev or production.
2. **Correcting your own earlier claim in writing.** The engineer argued against
   `has_value_changed`, then read `frappe/model/document.py`, found they were wrong, said so
   in the notes with the line number, and used it. I re-read the same lines and they are
   right.
3. **A test that passed under the break, and was rewritten until it failed.** The
   manager-reads-my-month test passed because the reader was Administrator, who had no
   boundary of their own — it could never have shown the fault. Catching that is the whole
   point of the break-test habit.
4. **Making the leak impossible instead of checking for it.** Another person's month is built
   from a field list that has no `date_of_joining`. There is nothing to forget to guard.
5. **One derivation for the guard, the sheet, the history and the refusal.** The manager
   window's own comment says a second counter is how two screens come to disagree; this slice
   obeyed it rather than copying the number.
6. **Twelve false sentences fixed in the same commit as the code**, including two in tests and
   one the grep only found at build. The slice exists because of a sentence like those.
7. **Pressing the real button in the DOM test** and asserting what was sent, not what was
   drawn — your rule of 28 Oct.

## 11. Confidence

| Claim | Label |
|---|---|
| The guard binds all three documented routes and the REST insert, and fails closed | **Proven** — read end to end, plus two independent break-test runs and my own module run |
| `joined_on` cannot reach another reader | **Proven** — by construction, read in `_subject` |
| An employee cannot self-grant the joining-day exception | **Proven** — permlevel 2 plus `refuse_own_locked_change`, both read |
| `next-time.js` shows the server's sentence | **Proven by reading**; **not seen in a browser** |
| The `CorrectionCase.person()` Shift Assignment fixture is **not** a risk to this slice | **Inferred, with support.** The window reads the holiday list, the joining date and today — never a shift. And the test engineer re-proved the same behaviours on fixtures with no Shift Assignment. **It stays real test debt for whoever owns that file**, because it makes that file's other tests unlike DTC |
| Nothing else in the suite broke | **Not checked.** One module ran under me. **CI on the exact SHA is the gate** |
| Behaviour on a live tenant | **Not checked.** No live site opened |
| Phone, Hindi, screen reader, 200% text | **Unreviewable here** — AC-66 is a human gate with no owner named (Gate 4 Q4 still open) |

### Must know before this goes further

1. **M-1.** Is the inline day detail accepted in place of the prototype's modal? My reading:
   accept it. If you want the modal it is a separate slice. *Ranked P2 until you answer.*
2. **M-3.** Will the independent test file be committed? If not, say so out loud, because
   `04-test-report.md` then cites proof the repo does not hold.

### Should know

3. **M-2.** Which of the engineer's options (a), (b) or (c) for ALV-391 — and is the hand
   list of tenants-with-a-number the record until then? This blocks the first number, not the
   release.
4. **m-4.** Should the refusal say "another HR person" to an HR caller, or is telling HR to
   tell HR accepted?

---

## Appendix: my own test run

`CI=true bench --site test_site run-tests --app alvoraa_portal --module
alvoraa_portal.tests.test_attendance_correction`, inside `alv084-bench` (the engineer's stack,
which mounts this worktree), result recorded below as I saw it.

```
Ran 148 tests in 442.670s
OK
Ran 19 tests in 0.188s
OK
```

**Both batch summaries read** (`bench run-tests` prints two, and tailing the output hides
one). 148 + 19, no failures, no errors. This matches `04-test-report.md` exactly, so that
figure is now **proven under me** and not restated on trust. The 30 tests of
`TheEmployeesFilingWindow` and the 25 of `TheManagersFilingWindow` are inside the 148.

**This is one module out of 218.** It says nothing about the other ~4,270 test methods.

---

## Gate — Surbhi's decisions on the review, 19 November 2026

"Go ahead with all your recommendations", and "push to dev".

**M-1 — the inline row is ACCEPTED in place of the prototype's modal dialog.**
AC-72's `role="dialog"` is not built and will not be. Making the day detail a modal
would mean rewriting a component the manager and HR flows share, which this slice never
scoped. If the modal is wanted it is its own slice. **This is a deliberate exception to
the prototype-parity rule (21 Oct 2026), approved by name.**

**The HR Manager behaviour is ACCEPTED KNOWINGLY.**
The guard binds by whose record it is, not by which screen the request came from — which
is why it cannot be walked around. The consequence: **an HR Manager cannot raise their
own old day on any route, portal, Desk or REST.** Gate 3's recorded rationale said they
would fix it "through the HR route, which is deliberately unbounded". **That rationale
is wrong and is corrected here.** The real escape is another HR person; on a
one-HR-person tenant there is none, and for that reader the refusal's "HR can still fix
it" is false. No role exemption is being added — the mechanism is right, the old reason
was not.

**M-2 / ALV-391 — the logger fix is NOT part of this slice.** It is fixed before the
first tenant sets a non-blank value, not before release. Option (b): give the `security`
logger an explicit level in one place, which also revives `log_refusal`/SEC-17. Until
then OPS-30's hand list of tenants is the only record, and it needs a named owner.

**M-3 — done, not deferred.** The 18 independent tests were untracked, so
`04-test-report.md` cited evidence the repository did not hold. Committed as `0672731a`
on the slice branch; `check_app_integrity.py` 952 checks OK.

**Carried, unchanged, and still blocking the FIRST NUMBER rather than the release:**
counsel's answer (C1), the re-verified DPDP baseline (stale 22 Nov 2026), a native Hindi
reader, the DTC manual search, `next-time.js` usage, and ALV-391.

**Carried and blocking MAIN:** CI green on main's own SHA, and OPS-28 — the previous
production image tag proved to exist in `alvoraa-app`. Narrowed on 19 Nov: main is
`928b7a76`, so the target is `alvoraa-app:main-928b7a7`. **Not confirmed** — the token
available lacks the `read:packages` scope.

**P3 worth fixing in a later pass, not now:** `refuse_own_day_outside_window` hardcodes
"tell HR", so an HR Manager is told to tell themselves. `portal.js:131` already carries
`whoToAsk()` with the comment *"ALV-350: Telling HR to 'tell HR' sent them to
themselves."* The lesson never reached the server side.
