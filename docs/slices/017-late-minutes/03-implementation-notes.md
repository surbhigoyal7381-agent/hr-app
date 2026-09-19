# Slice 017 — what changed, and how it was proved

Branch `slice/017-late-minutes`, cut from local `dev` at `c83b37d`. **Not merged into local
`dev`, not pushed.** The other session is mid-release; the user sequences the merge.

Read `00-impact-analysis.md` first. It holds the numbers, the personas, the seven-dimension
verdict and — importantly — **the one decision I did not make** (§7 there: which grace the
screen's late count should use).

---

## 1. The rule, in plain English

**How late somebody was is the number of minutes between when their shift was due to start
and when they actually clocked in. If they clocked in before the shift started, they were
not late at all.**

Where each part comes from:

| Part | Source |
|---|---|
| When the shift was due to start | the **Shift Type**'s `start_time` for that day's shift, falling back to the employee's `default_shift` |
| When they clocked in | the Attendance row's `in_time` |
| No shift on the day | no lateness. No shift means no expectation, so no accusation |
| A shift that crosses midnight | judged from when it begins (22:00), not from its length |
| Clocked in before the start | zero, never a negative |

**What this rule does *not* say, on purpose:** it does not say how many minutes late is
*allowed*. Today the screen allows none, so a one-minute arrival is counted as a late day,
while only 60 minutes or more costs money. That gap is a product decision and it is written
up in `00-impact-analysis.md` §7 with three costed options and my recommendation. **I did
not guess it.** Pay is not a place to guess.

## 2. What changed, file by file

| File | Mechanism | Change | Why this mechanism |
|---|---|---|---|
| `alvoraa_portal/alvoraa_portal/attendance_analytics.py` | **extend** | New `_shift_row(cache, shift)` caches the Shift Type **row**. `_shift_minutes` now derives the length from it. Signature and return value unchanged. | The cache holding a *derived* number under the shift's name was the defect. Caching the fact and deriving per helper makes the whole class of mistake impossible, and reads each shift once instead of twice. |
| `alvoraa_portal/alvoraa_portal/attendance_correction.py` | **extend** | `_shift_start` now reads the same row through `_shift_row` instead of writing its own answer into the shared cache. One import line added. | Same reason. Smallest change that removes the cause rather than the symptom. |
| `alvoraa_portal/alvoraa_portal/tests/test_late_minutes_017.py` | **new** | 11 pin tests in three classes. | Every fixture uses a shift whose start and length are **different numbers**. |
| `docs/slices/017-late-minutes/` | **new** | This note and the impact analysis. | |

**Nothing else was touched.** No DocType, no hook, no patch, no page, no endpoint, no
permission, no field, no `ignore_permissions`. `hrms-employee.html` already reads
`late_by_mins`, `shift_starts` and `shift_ends` from the payload and needed no change — it
was drawing the right fields with the wrong values.

No data migration and no backfill: the figure is computed per request, so all 22,570 rows
start reading correctly the moment the code ships.

## 3. What each acceptance point needed, and how it is met

| Point | How |
|---|---|
| The late figure is measured from the shift start | `_shift_start` reads `start_time`; pinned by `test_late_is_counted_from_the_shift_start_not_its_length` (09:47 on a 09:30 shift = 17) |
| Arriving early is not late | pinned by `test_arriving_before_the_shift_starts_is_not_late_at_all` (09:10 = 0, was 10) |
| The month total agrees | pinned by `test_the_month_does_not_count_an_early_arrival_as_a_late_day` |
| The drawn shift matches the real one | pinned by `test_the_strip_shows_the_shift_the_employee_actually_works` (09:30–18:30, was 09:00–18:00) |
| Night shifts | pinned by `test_a_night_shift_is_judged_from_when_it_begins` (22:05 = 5, was 845) |
| No shift / unknown shift fails safe | pinned by `test_a_shift_that_does_not_exist_is_not_late` |
| The defect itself cannot come back | pinned by `test_the_two_helpers_do_not_read_each_others_answers` (both call orders) and `test_the_cache_holds_the_row_not_a_derived_number` |
| **The deduction amount is right** | pinned by three tests in `TheMoneyThatFollows`, below |
| Which grace the count uses | **not satisfied — deliberately open.** `00-impact-analysis.md` §7 |

### The money tests, and why they matter even though nothing was broken there

The late-coming rule reads the shift start through its **own** cache and has always
measured from the true 09:30. Verified against stored data on `ppj.localhost`: 341
`Late Arrival` violations, minimum 61 minutes against a 60-minute threshold.

So these three tests are not proof of a bug. They are a **guard on pay**: the arrivals are
chosen to tell the two readings apart. 10:15 is 45 minutes past 09:30 and costs nothing,
but it is 75 minutes past 09:00 and would cost a quarter day. If anyone ever "tidies up" by
feeding the screen's figure into the rule, these fail:

- `test_the_rule_measures_lateness_from_the_shift_start` — no violation at all
- `test_no_deduction_and_no_rupee_leaves_pay_for_a_45_minute_arrival` — no deduction document, no Additional Salary
- `test_a_real_late_week_costs_the_exact_amount_it_should` — three arrivals 75 minutes late, first free, two counted at a quarter day = 0.5 day; 31,000 over a 31-day month is 1,000 a day, so **₹500 exactly**, asserted on both the deduction and the Additional Salary

## 4. The seven dimensions, against the code actually written

| Dimension | Before → after | Verdict | One line |
|---|---|---|---|
| **Performance** | 2 queries per shift → 1 | **improves** | `_shift_minutes` and `_shift_start` now share one read. `attendance_correction.month` was the Time page's slowest call at 15 queries / 702 ms. |
| **Security** | unchanged | **neutral** | No endpoint, permission or `ignore_permissions` touched. The `attendance_analytics.py` CEILINGS entry stays at 0 and still passes. |
| **Reliability** | a shared key with two meanings → one fact, own sums | **improves** | Missing or unknown shift still returns `None` and produces no lateness. |
| **Scalability** | one fewer query per distinct shift | **improves** | Matters most on the month view, which loops every day. |
| **Maintainability** | two helpers silently coupled → one documented helper | **improves** | The comment names the bug and why the shape prevents it. |
| **Data integrity** | 22,570 rows read wrong → all read right | **improves** | Nothing stored was wrong, so nothing to migrate. |
| **Compliance / privacy** | an employee told a wrong fact about their own conduct, next to a pay deduction | **improves** | No new personal data read, shown or logged. No widened visibility anywhere. |

## 5. NFR notes

- **Query counts:** one Shift Type read per distinct shift per request, down from two. No
  new query anywhere. No N+1 introduced; the month loop reuses the one cache it already had.
- **Indexes:** none added, none needed. No new filter or join.
- **Background jobs:** none added. The weekly deduction job is untouched.
- **Permission enforcement points:** untouched. `attendance_correction.month` still resolves
  the subject server-side and refuses somebody else's month; its 42 existing tests cover
  that and all pass.
- **Sensitive fields touched:** none. Attendance `in_time` and Shift Type `start_time` only,
  both already on this screen.
- **Fallbacks:** no shift, unknown shift, or missing `in_time` all yield no late figure.
- **Internationalisation / accessibility:** no user-facing string and no markup changed.

## 6. Commands run, and what they said

All runs in a **throwaway container** `hrlocal-017` built from the same image as the bench,
mounting **this worktree's** app folders plus the shared sites volume. Reason: the shared
bench mounts only the main checkout, and I was told not to merge into local `dev` — and
copying files between checkouts is forbidden. Verified before running that the container
saw `_shift_row` (2 and 3 hits) and the shared bench did not (0 hits), so the two never
mixed. Container removed afterwards.

| Command | Result |
|---|---|
| `python scripts/check_app_integrity.py` | **583 checks, "OK - all consistent"** |
| `run-tests --module ...test_late_minutes_017` | **11 OK** (3 + 8, two category blocks) |
| `run-tests --module ...test_attendance_correction` | **42 OK + 9 OK** |
| `run-tests --module ...test_attendance_analytics` | **17 OK** |
| `run-tests --module ...test_attendance_scope_012` | **13 OK** |
| `run-tests --app hrms --module ...test_late_rules` | **Fails to start** — `LinkValidationError: Could not find Parent Item Group: All Item Groups`. **Pre-existing and not mine:** the identical failure occurs on the unmodified shared bench. An ERPNext fixture that `test_site` has never had. |
| Full `alvoraa_portal` suite | see §7 |
| Full `alvoraa_goals` suite | see §7 |

`ruff` is not installed on the host and the container has no app-local env, so linting was
not run. Nothing was reformatted; the diff is 4 small hunks in the style of the surrounding
code.

### The fail-without-fix proof

Two temp scripts piped on stdin into the container's python, each switching the fix off
**in process** and then running the tests directly.

1. **Display** — restored the two old helpers (each writing its own derived number into the
   shared cache) onto `attendance_correction`:
   **7 of 8 failed** — `ran=8 failures=6 errors=1`. The one that passed,
   `test_a_shift_that_does_not_exist_is_not_late`, is a fail-safe guard and is correct
   either way; it is not a bug pin and is not claimed as one.
2. **Pay** — put the rule's `_shift_times` onto the same mistake, returning the shift's
   length as its start:
   **all 3 failed** — `ran=3 failures=3 errors=0`. Notably
   `test_no_deduction_and_no_rupee_leaves_pay_for_a_45_minute_arrival` failed with
   `1 != 0`: a deduction document **was** created for a 45-minute arrival against a
   60-minute threshold. That is exactly the money the pin exists to protect.

One honest note: the first run of `test_attendance_correction` reported 5 errors. It was
clean (42 OK) on re-run, and the 5 were leftover rows from the switch-off script above,
which runs tests outside the normal runner and does not roll back as cleanly. The module
passes on a clean run.

## 7. Test results — full suite, and why it cannot be read at face value

**`test_site` is contaminated, and the full-suite numbers below are mostly that, not this
slice.** I confirmed it read-only during my run: **554 leftover `Custom DocPerm` rows across
338 doctypes**, 322 of them written on 17 Sep. The subscription and access suites apply a
starter plan's module blocking and never restore it. A single `Custom DocPerm` row
**replaces** a doctype's shipped permissions, so unrelated classes then die in
`setUpClass`.

Full `alvoraa_portal` in the throwaway container:

```
Ran 578 tests in 1911.679s   FAILED (failures=5, errors=9, skipped=4)
Ran 624 tests in 1907.978s   FAILED (failures=4, errors=24)
```

1,202 tests, 9 failures and 33 errors. **I cannot name them** — I filtered the run's output
to the summary lines and the names were lost, and `frappe.testing.log` records only module
starts, not results. I am not going to claim they are all contamination without the names.

What I *can* say, with evidence:

- **Every module I touched or that exercises my code passes, run on its own:**
  `test_late_minutes_017` **11 OK**, `test_attendance_correction` **42 OK + 9 OK**,
  `test_attendance_analytics` **17 OK**, `test_attendance_scope_012` **13 OK**.
- **`test_portal_security_010`** — 45 tests, **6 errors**, and I traced them. They throw
  `PermissionError: Insufficient Permission for Attendance Deduction` and two goal-evidence
  refusals. `Attendance Deduction` has **exactly one** leftover `Custom DocPerm` row —
  `System Manager`, created 2026-09-18 — which wipes HR Manager, HR User and Employee
  access to the doctype. `Individual Goal` has the same, one row, same date. **Contamination,
  not this slice.** Its 5-test `ignore_permissions` CEILINGS block, which covers
  `attendance_analytics.py` at 0, is **OK**.
- The known local-only failures still apply on top: `test_leave_year` 3 errors,
  `test_invoicing` 1 failure + 10 errors, plus the hrms bootstrap failure in §6.

**`alvoraa_goals` was not run**, and the clean full run is still owed. Another session is
repairing `test_site`; per instruction I did not run the repair and did not re-run the
suites on a dirty site. **One clean full run of `alvoraa_portal` and `alvoraa_goals` after
the repair is an outstanding item before this slice ships.**

## 8. What else moved while I worked

- My branch is cut from local `dev` at `c83b37d`, **33 commits ahead of `origin/dev`** —
  the other session's slice 014, 015 and 016 fixes. I read the incoming log; none of it
  touches attendance, shifts, late minutes or the deduction path.
- **No conflicts.** My two files were changed by slices 010 and 012 earlier, but in
  different functions, and that work is already in `dev` beneath my commit.
- **Nothing of theirs was lost:** `test_attendance_correction` (slice 010's area) and
  `test_attendance_analytics` and `test_attendance_scope_012` (slice 012's area) all pass
  unchanged, and the full suite shows only the known failures.
- Another session's uncommitted work sits in the main checkout. I staged nothing there and
  changed nothing there except adding my row to the git-ignored work board.

## 9. Known gaps and shortcuts — declared

1. **The grace decision is open.** After this fix PPJ's Time screen counts 8,280 late days
   where 594 cost money. Correct, but not yet reconcilable with the deduction card beside
   it. Three options, costed, in `00-impact-analysis.md` §7. **This is the next thing to
   do and it needs the user's word.**
2. **Early exit past midnight creates a false violation** in the **pay** path —
   `late_rules.violations_for` :82. A day shift ending 18:30 with an `out_time` of 00:30
   reads as 1,080 minutes early. Not live today (no tenant has post-midnight punches on a
   day shift) but it is real money and should be fixed before anyone works past midnight.
   Out of this slice's scope, which is late minutes only.
3. **The projection can disagree with the deduction** (F-11). `hr_api._late_rule_for`
   ignores exempt grades, `process_from` and date of joining, which
   `late_rules.covered_employees` applies; and `get_team_late_list` looks up **the first
   team member's rule and applies it to everyone**. `get_team_late_list` is claimed by
   slice 010 on the work board, so I did not touch it, and the fix needs decision §7 first.
4. **No browser trace.** The page reads the same three fields it always did, so the change
   is invisible to the markup, but nobody has looked at the corrected Time screen in a
   browser. Worth five minutes before release.
5. **hrms's own test modules cannot run on `test_site`** (§6). Pre-existing. It means the
   late-rule tests in `hrms` are not exercised locally; my deduction pins live in
   `alvoraa_portal` and do run, which is why they were put there.
6. **`ruff` not run** (§6).
