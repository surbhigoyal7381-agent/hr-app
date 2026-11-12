**Verdict: SHIP WITH FIXES.** The code does what was approved and I found no data leak, but one of my four runs of the new break tests failed and I could not find out why. There has also been no browser check of the two screens.

`SHIP WITH FIXES` means: ready to show Surbhi for the push-to-dev decision once the two P2 items are dealt with. It is not permission to push.

# ALV-328 - Senior architect review (step 5)

| | |
|---|---|
| Slice | ALV-328 (with ALV-332 and ALV-333 folded in) |
| Commit reviewed | `ccca2b6c` on `slice/alv-328-break-and-reason`, on top of `origin/dev` `c5d57333`. Local only, not pushed |
| Reviewer | `hrms-technofunctional-reviewer`, 12-13 Nov 2026 |
| Read | 01 brief, 02 design, 03-security-privacy, 03-devops, 04 spec (AC-1..48, 17a), 05-impact-and-strategy, 06-implementation-notes, `.claude/context/data-doors.md`, the whole diff, and the files it depends on (`payroll_rules.evaluate_day`, `_worked_percent`, `_judge_other_half`, `payroll_rules_apply._punches`, `judge`, `prepare`, `_employee_flags`, `attendance_correction.month`, `_day`, `_distinct_punches`) |
| Ran | the two new test modules in `hrlocal-328`, site `test328`; `node --check portal.js`; `ruff`; `scripts/check_app_integrity.py`; read-only SQL on `test328` |
| Not run | the full suite (the caller asked me not to); a browser; real HTTP calls through nginx; anything on DTC |

**About the file name.** The handoff contract names this file `05-review.md`. This slice already has a `05-impact-and-strategy.md`, so two files start with `05`. That is a naming clash only (P4).

---

## What came in with the rebase (lesson 4)

Between the strategy's base `75149184` and the new base `c5d57333`, 13 commits came in. All are from the same agent account, working in other sessions. None is a merge commit. **Proven** (`git log 75149184..c5d57333`).

- `cdfe3a2f` .. `47b887c0`: slice 083 (notifications). It changes `portal.js` heavily (about 527 lines), but not in `acRow`, `acPaint`, `acDetail` or `aiPerson`. `node --check` passes.
- `da9ec194` ALV-334: grooming test only.
- `c5d57333` ALV-315: adds `_distinct_punches` at the top of `attendance_correction._day`. This is the one that interacts with this slice. See finding P3-2.

Nothing has landed on `origin/dev` after `c5d57333` (fetched 13 Nov).

---

## Findings, worst first

There are no P0 and no P1 findings.

### P2-1 - The break test module failed on one of four runs, and I do not know why (Major)

- **What I saw (proven).** I ran `test_break_and_reason_alv328` four times in `hrlocal-328`. The first run, after the container had been idle, gave `Ran 16 ... FAILED (failures=1)`:
  `AssertionError: {} != {'2025-03-03': {'break_state': 'measured', [401 chars] 40}}`
  The next three runs gave `Ran 16 ... OK`. My first run filtered the output, so I do not have the test's name.
- **What it means (inferred).** The message is the shape of `breaks()` for a whole month. The empty dict comes first. That pattern only appears in `WhoSeesTheBreak`, in one of these tests:
  - `test_alv328_the_direct_manager_sees_what_the_person_sees`
  - `test_alv328_with_the_switch_on_the_skip_level_manager_sees_it`
  - `test_alv328_hr_sees_the_same_break_on_insights_and_no_reason`

  In each one, a viewer (Kavita, Arjun with the switch on, or Meena) got **no break**, while Rohan's own call did get one. So in that run, the permission layer decided the viewer could not read Rohan's punches.
- **Why it matters.** The failure went the safe way: someone saw less, not more. But there are only two explanations:
  1. The tests leak state into each other (cached roles, user permissions or the rule-set document across runs).
  2. A real timing problem in the punch rule.

  I could not tell which. Also, CI runs the whole suite on every push to dev. A test that fails one time in four will turn CI red and hold up deploys (the "CI red may be site state" lesson).
- **Smallest fix.** Before the push, run the module in a loop on a fresh container, with full output, until it fails. Name the test, and fix the isolation (or the code). Owner: `hrms-fullstack-engineer`.
- **Must-know question:** *Can the engineer reproduce this failure and name the test?* Until someone answers, I rank it P2. If the cause turns out to be in `field_app_access`, it goes up to P1.

### P2-2 - Nobody has looked at the two screens in a browser (Major)

- **What I saw (proven).** The implementation notes say "No browser run" for AC-2, AC-6, AC-21 on screen, and the 360 px check. So the Break column, the "(15 over)" red, the tiles, "Why this day", and the Insights `.tbl-wrap` at 390 px have never been drawn.
- **What I checked by reading (proven).**
  - `acBreak` passes every value through `gpEsc`. `x.rules_why` goes through `gpEsc`. So AC-21 (no HTML from the reason text) holds in the code.
  - AC-8's wording works out from `acMins`: 105 minutes gives "1h 45m (1h 5m over)".
  - The colspan changes between 9 and 10 with the column.
  - I did not open the prototype side by side. The parity table in the spec says there are no differences.
- **Why it matters.** Surbhi's rule is "prototype parity". A phone layout that breaks is the first thing a DTC employee would see.
- **Smallest fix.** One browser pass at 360 px and 1440 px on the engineer's own stack, before the dev push. The engineer already calls this temporary debt.

### P3-1 - The loosened query-count test cannot catch what its message claims (Minor)

- **The test.** `test_break_and_reason_alv328.py`, `QueryCounts.test_alv328_month_costs_the_same_for_few_or_many_punches`, near the end of the file. It now counts only Employee Checkin queries whose SQL contains `` `attendance` ``, and says "the break adds no Employee Checkin read".
- **Failure scenario.** Someone later adds `frappe.get_all("Employee Checkin", fields=["time"], ...)` inside `breaks_by_day`. That query has no `` `attendance` `` column, so `own` stays 1. The read is the same for both people, so `many == less` still holds. **The test passes, and the extra read is not caught.**
- **Is the code itself right today? Proven, by reading.** `breaks_by_day`, `prepare` and `_employee_flags` never read Employee Checkin. The only punch read in `month()` is the existing one. The grooming line reads punches separately (`grooming.py:332`). So the loosening hides nothing **today**. The weakness is only in what the test would catch in future.
- **Smallest fix.** Count the Checkin queries twice: once normally, and once with `breaks_by_day` patched to return `(0, {})`. Assert the two counts are equal. `person()`'s test (exactly 1) is fine as it is.

### P3-2 - On one row, the punch list can disagree with the break figure (Minor)

The break agrees with the pay engine on every path I traced (see "Break = engine" below). But in two cases the **punch chips and the "Missing punch" tag** on the same row can tell a different story:

1. **A punch after midnight that is linked to the day before (AC-17a, by design).**
   - In the fixture, day 13 draws **5** punch chips. 5 is an odd number, and the punches have no In/Out label, so `_day` sets `missing_punch` True (`attendance_correction.py:858`).
   - The same row then says "Break 40 min", because the break counts by calendar date.
   - So the row shows "Missing punch" and a measured break side by side.
   - The spec accepted counting by calendar date. Nobody listed this visible contradiction.
2. **A punch with no attendance link on a day whose other punches are linked.**
   - `month()` passes `marks or punches.get(date)` (line ~598). If any punch is linked to the day, unlinked punches of that date are **not drawn**.
   - Example: HR adds a missing punch in Desk after the day was marked, so it stays unlinked. Linked 09:58, 13:00, 19:05 plus the unlinked 13:40. The row shows 3 chips and "Missing punch". The break (like the engine) counts 4 punches and says "Break 40 min".
   - The break is the right one, because it is what pay uses. The chips and the tag are the old behaviour.
   - **Not checked:** how often this happens at DTC.
- **The good news from ALV-315 (proven by reading).** The repeat-scan case is now consistent:
  - `_distinct_punches` folds a repeat scan exactly as `punch_minutes` does: whole minutes, 2 minutes measured from the last punch kept.
  - So AC-12's note "the Missing punch tag may still show" no longer applies.
  - No test pins this: nothing asserts `missing_punch` is False on fixture day 6.
- **Smallest fix.** No code change in this slice. Put case 2 on a ticket (the punch list should include unlinked punches of the same date). Add one assertion that day 6 has `missing_punch` False.

### P3-3 - AC-10 (category allowance) and AC-8/AC-9 wording have no test (Minor)

The implementation notes call this a "gap, small". `breaks_by_day` reads the allowance through `_employee_flags`, which ALV-326 tests, so the risk is low. AC-10's "Allowed 60 min" tile is untested end to end. Ship, tracked.

### P4 (backlog)

- `06-implementation-notes.md` still says "Count E on DTC not run". `05-impact-and-strategy.md` records the result (0). One of them is stale.
- `tabEmployee` has no index on `reports_to`. **Proven:** `show index` lists only `status`. At DTC's size (about 600 staff) a full scan inside the punch rule costs nothing worth measuring. At 10,000 staff, with the switch on, each list call scans the table once per level of the reporting line. That is fine for now (OPS-5 says no index). Look again only if a large tenant switches it on.
- Two files start with `05` in this slice folder.
- Pre-existing ruff E741 at `attendance_correction.py:584` (`l`). Not from this slice.

---

## Your specific questions, answered

**1. Does the break equal what the pay engine counts? Yes, on every path I traced. Proven by reading.**

| Case | Engine (`evaluate_day` / `_worked_percent`) | Screen (`breaks_by_day`) | Same? |
|---|---|---|---|
| Seconds, repeat scans | `_punches`, then `punch_minutes` | `punch_minutes` | yes, one function |
| Sum of gaps | `minutes_on_break(gaps, start, end)` | the same function | yes |
| Window, shift hours only | `[max(counted_from, shift start), min(last, shift end)]`; `counted_from` is the shift start, or the first punch if late | `[shift start, min(last, shift end)]` | yes. Every break starts at or after the first punch, so the two windows clip the gaps the same way, late or not |
| Window, shift hours off | first punch to last punch | first punch to last punch | yes |
| Odd count (3 or more) | "a punch is missing ... none deducted" | `not_measured` | yes |
| 1 punch, confirmed later | count becomes 2, no gaps | 1 punch, no figure | yes |
| 2 punches | no gaps | no figure | yes (and "0 min" is never shown on 2-punch October) |
| On Leave | returns before the break | skipped | yes |
| Half day with leave | `_judge_other_half`, same window rule | treated as a normal day | yes, same window |
| Night shift (end before start) | held | skipped | yes |
| No shift | held | skipped | yes |
| Allowance | category value, else the rule set's; not tied to a date | read once at `dates[0]` | yes |
| Calendar date | `_punches` reads 00:00-23:59:59 of the date | `times_by_date` keyed by `str(time)[:10]` | yes (AC-17a) |
| Home banner | `day_marks._break_over` now calls `minutes_on_break` | - | same numbers |

AC-13's test is the real proof. The engine judges each fixture day when it is submitted. The test then compares the stored "Breaks: N minutes" with the screen, for at least 6 days (7 in the fixture). That test is sound.

The one place they can differ is accepted in the spec: if the category or allowance changes after a day was judged, the screen uses today's allowance, while the reason text keeps the old one and shows its date.

**2. After ALV-315, do the punch list, the break and the missing-punch flag agree?** For repeat scans, yes, and better than before. For the two link cases in P3-2, no. The break is the one that matches pay.

**3. The `has_permission("Employee Checkin", "read")` guard in `person()`: right. Proven by reading.**
- It is a doctype-level check, run before `get_list`. A login with no read right gets the page without a break. Before the guard, that login got a `PermissionError` for the whole page.
- It fails closed: no right means no break, never someone else's break.
- It adds no bypass. When the guard is True, `get_list` still applies `checkin_query_conditions`. So a skip-level manager still gets an empty list and no break (AC-26 is tested).
- It is better than catching `PermissionError`, which would also hide unrelated errors.
- One thing I did not check: whether such a login can reach `month()`. If it can, `month()` already had the same whole-page error before this slice. That is pre-existing, not new.

**4. The punch rights in `field_app_access.py`.**
- **Injection: none. Proven.** `_line_sql` puts only two things into the SQL text:
  - `frappe.db.escape(emp)`, where `emp` comes from the database; or
  - the fixed placeholder `'%(me)s'`, bound by `frappe.db.sql`.

  The switch value only picks which of two fixed strings is used. The caller supplies nothing.
- **Cost: fine at DTC's size.**
  - Switch off: one subquery that does not depend on the outer row. MariaDB runs it once.
  - Switch on: a recursive query. `UNION` (not `UNION ALL`) stops a loop in `reports_to`.
  - There is no index on `reports_to` (P4).
  - `whole_line_on()` adds one read per hook call. It is not cached, by design, so a change takes effect on the next request.
- **Rules. Proven by the tests I ran (17 OK).**
  - Outside HR, own punch: read and select only, plus create of a new punch.
  - Someone else's punch: read and select only, and only within the line.
  - The machine account can still create.
  - HR keeps every right.
  - The list and the single-record check give the same set (SEC-6 test, switch off and on, record by record).
  - Left and Inactive people at any level are excluded.
  - A negative-control test proves the refusal is real.
- **The switch guard. Proven.**
  - It runs first in `validate_hr_settings`, so Desk save, `frappe.client.save` and `frappe.client.set_value` all hit it (tested as HR Manager).
  - A save that does not change the field still goes through.
  - `frappe.db.set_single_value` skips it, but only server code can call that, not a user.
- **Writers checked by reading (proven).** The field app (`insert(ignore_permissions=True)`) and photo attach (`File` with `ignore_permissions`) are not affected. Auto-attendance and cancel use `qb`/`set_value`, also not affected.
- **Not checked:** whether the Frappe HR phone app attaches anything to a punch the person filed. That would need write, which is now refused.

**5. The loosened query-count test.** The code is fine today. The test is weaker than its message says. See P3-1.

---

## AC verification

| AC | Status | Evidence |
|---|---|---|
| AC-1, 3, 7, 11, 12, 14, 15 | met | `test_alv328_the_days_the_spec_names` (ran, OK in 3 of 4 runs; the failing run was a different class) |
| AC-2, 6 | partial | code read; no browser (P2-2) |
| AC-4 | met | leave and night-shift test; holiday, future and no-record days have no `att`, so `breaks` has no key for them (read) |
| AC-5 | met | `test_alv328_no_break_without_a_break_rule` |
| AC-8, 9 | met by reading | `acBreak` and `acMins`; no test (P3-3) |
| AC-10 | partial | not tested (P3-3) |
| AC-13 | met | engine-match test |
| AC-16 | met | helper test |
| AC-17 | met | proven: one `collapse_duplicate_punches`, one `minutes_on_break`, called by the engine, the banner and both screens |
| AC-17a | met | test; but see P3-2 for what the row then shows |
| AC-18, 19, 20 | met | keys only when set (test); `acDetail` draws section, h3 and date (read) |
| AC-21 | met by reading | `gpEsc`; no browser |
| AC-22 | met by reading | tiles in `acDetail`; `break_allowance_minutes` sent once per month |
| AC-23 | met | no extra warning (read) |
| AC-24, 25, 26, 30, 34 | met, but flaky | `WhoSeesTheBreak`; see P2-1 |
| AC-27, 31, 32, 33 | met | `test_punch_rights_alv332` (ran, 17 OK). Called through Frappe's own functions, not over HTTP |
| AC-28, 29, 36 | met | same module |
| AC-35 | not tested here | `log_photo_view` unchanged; accepted gap SEC-11 / R3 |
| AC-37, 38 | met, but flaky | Insights test; see P2-1 |
| AC-39 | met | `person()` uses `frappe.get_list` (read) |
| AC-40 | met | group-view test |
| AC-41, 42 | met | tests, including the negative control |
| AC-43 | met | no new `ignore_permissions`; `test_portal_security_010` not touched; the one `frappe.db.sql` is the permission rule itself and reads only `tabEmployee` |
| AC-44 | met | one HR Settings field; nothing written for break values |
| AC-45 | met | no new log or throw with a break value or reason (read) |
| AC-46 | partial | the code meets it; the test is weak (P3-1) |
| AC-47 | met | test |
| AC-48 | met | test |

## NFR verification

| Budget | Measured or reasoned | Result |
|---|---|---|
| No per-day queries (OPS-1, OPS-3) | `breaks_by_day` makes a fixed number of reads, then loops in memory (read); `person()` makes exactly 1 Checkin read (test) | pass |
| No extra Checkin read in `month()` | proven by reading; the test is weak | pass (code) |
| Payload (OPS-4) | keys only when they have a value (AC-48 test) | pass |
| No cache, no index, no job (OPS-5) | none added | pass |

**The seven dimensions: the impact analysis's claim vs. what the code does.**

| Dimension | Claimed | Found | Agree? |
|---|---|---|---|
| Performance | neutral | neutral. A fixed handful of reads, only when there are punches and a rule set | yes |
| Security | improves (degrades only with the switch on) | improves. Write, delete and share on punches are closed outside HR in `has_permission`; the switch is System Manager only | yes |
| Reliability | neutral | neutral in the code. **But the new tests are flaky (P2-1)** | partly |
| Scalability | neutral | neutral at DTC's size; no `reports_to` index at 10k with the switch on (P4) | yes |
| Maintainability | improves | improves. Three copies of the break sum are now one; one SQL text serves both hooks | yes |
| Data integrity | improves | improves. Fewer people can change a punch; nothing new is stored | yes |
| Compliance / privacy | improves | improves. A person sees their own pay reason; no break on group views | yes |

## Compliance and SEC / PRIV / OPS items

| Item | Mechanism | Test | Status |
|---|---|---|---|
| SEC-1 new values only through `month()`/`person()` after their checks | no new endpoint, no new parameter | AC-41 test | discharged |
| SEC-2 no new bypass | `get_list` in `person()` | AC-39 read; ceiling unchanged | discharged |
| SEC-3 break only from punches the caller may read | `breaks_by_day` uses only what `get_list` returned | AC-25, AC-26 (flaky, P2-1) | discharged, pending P2-1 |
| SEC-4 Frappe doors closed to a colleague | own-record User Permission (existing) | AC-42 with negative control | discharged |
| SEC-5 reason as text | `gpEsc` | read only | partial (no browser) |
| SEC-6 list = single record | `_line_sql` shared | SEC-6 test | discharged |
| SEC-7 read only outside HR | `checkin_has_permission` | rights tests + negative control | discharged |
| SEC-8 Left/Inactive excluded | `status = 'Active'` at every level | test | discharged |
| SEC-9 System Manager only | `_refuse_whole_line_change` | 3 doors as HR Manager | discharged |
| SEC-10 history | Version row | test | discharged |
| SEC-11 photo log only on Desk | unchanged | - | not adopted; Surbhi accepted (R3) |
| PRIV-1 no break on group views | breaks only in two per-person endpoints | AC-40 test | discharged |
| PRIV-2 nothing stored | computed per request | read | discharged |
| PRIV-3 nothing in logs | no new log or throw | read | discharged |
| PRIV-4 off by default, off when unreadable | `whole_line_on` try/except, default 0 | tests | discharged |
| OPS-1..5 | see NFR table | | discharged (OPS-3 test weak) |
| OPS-6..9 | release steps | DevOps | not mine; open release gates |

Decision record: the engine decides; HR is the accountable human through corrections (spec §4). Unchanged.

## What to delete

Nothing. Every new piece has a caller and a test, or a decision behind it:
- `punch_minutes` and `minutes_on_break` stop the rules being written twice.
- `breaks_by_day` is the one place the "when to show a break" rules live.
- The whole-line switch is code that runs for nobody until a System Manager ticks it. It exists because Surbhi asked for it (Q-1, Q-D). If no tenant turns it on by the next review of punch rights, deleting the recursive branch would be the cheapest simplification.

## What was done well

- **The break is worked out by the engine's own functions, not a copy.** And the AC-13 test compares against the reason the engine actually stored. That is the right proof for "the screen equals pay".
- **The screens never decide who may see punches.** They take whatever `get_list` returns, so the limit lives in the permission layer (`data-doors.md`), and a skip-level manager gets no break without any extra check in the portal.
- **One SQL text for the list and the single record,** with a record-by-record test that they agree, switch off and on. Plus a negative control showing the refusal test can fail.
- **The switch fails closed** and is guarded at `validate`, so every save door is covered with one check.
- **The rebase was read, and named** in the strategy, including the overlap with ALV-315.

## Confidence

- **Proven:** the break math matches the engine (traced line by line); the SQL is injection-free; the punch rights rules and the switch guard (17 tests run, OK); the code adds no Checkin read to `month()`; `node --check` OK; integrity check OK (923 checks); ruff shows only the old E741.
- **Inferred:** the failing run (P2-1) was in `WhoSeesTheBreak` and was a viewer getting less, not more. This rests on the shape of the assertion message.
- **Not checked:**
  - the cause of P2-1;
  - any browser rendering, and parity with the prototype;
  - real HTTP calls through nginx (all door tests call Frappe functions directly);
  - the MariaDB version on dev and production;
  - how often DTC has the P3-2 link cases;
  - whether the Frappe HR phone app writes to a punch after filing it.

  To close these I would need: the engineer's stack with a browser, a read-only query on DTC, and repeated runs of the module with full output.

## Questions

- **Must know:** P2-1. Can the failure be reproduced and named? Ranked P2 until then. It becomes P1 if the cause is in the punch rule.
- **Should know:** is a browser pass planned before the dev push (P2-2)?
- **Nice to know:** a ticket for unlinked punches missing from the punch list (P3-2, case 2).

## Subtract pass on this review

Removed:
- a speculative note about stale Redis caches as the cause of P2-1, because I could not show it;
- a Minor about Desk showing a Save button to managers, which is already accepted as K5;
- a Nit on the CSS.

Nothing else could go without losing a finding.
