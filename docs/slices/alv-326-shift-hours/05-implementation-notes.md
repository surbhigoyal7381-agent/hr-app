# ALV-326 - implementation notes

Built on branch `slice/alv-326-shift-hours` in `.claude/worktrees/alv-326`, from
`origin/dev` 814d540f (fetched again before each round; nothing new came in). Local only:
nothing pushed, no server touched, no shared-bench migrate. No rule-set value was
changed on any real site.

**No real attendance is in this branch** (security review B1, fixed in round 2). The
tests use invented days. The comparison against DTC's real days is outside git:
`C:\Users\Dell\grace-ops\step29-alv326-dtc-november-match.py` (read only).

Decisions followed (Surbhi, 2026-11-11): D1 the strategy; D2 the late window is cleared
on DTC's rule set by Surbhi, ATT-04 unchanged in code; D3 whole minutes; the two-red rule
stands; nothing company-specific in code or in the repository.

## What changed, file by file

Rung: configuration fields on an existing DocType, plus code in the files that already
hold the rule. No new DocType, no job, no patch.

| File | Change |
|---|---|
| `alvoraa_payroll_rule_set.json` | `count_shift_hours_only` (Check, 0), `late_quarter_after_minutes` (Int, 0), `break_allowance_minutes` (Int, 0). |
| `alvoraa_employee_category.json` | `late_quarter_after_minutes`, `break_allowance_minutes` (Int, 0 = use the rule set's). |
| `alvoraa_payroll_rule_set.py` | Blank becomes 0; negatives refused; a late limit at or below the grace in force refused, on the rule set and on each category row (security M1). |
| `payroll_rules.py` | `break_gaps`, `late_charge`, `charge_for` (shared with the banner), `_worked_percent`. `evaluate_day` takes the three settings and the gaps, all off by default. Reasons say "the same red" or "no red: the late quarter replaces the band's red" when the late rule changes the band's red (security M2). |
| `payroll_rules_apply.py` | `prepare` reads the settings; `_employee_flags` applies category overrides. `_punches` works in whole minutes (D3) and returns the gaps as a fourth value. `day_rules_on` (formerly `green_eligibility_on`) returns greens, the grace in force, whether the person earns marks, and the three settings. |
| `day_marks.py` | Uses `day_rules_on` for grace and marks (review P2-1): contract staff see their own grace; staff without marks are shown no red and no red window, but a late quarter still. Ladder counts as the engine does when shift hours only is on. `_grace_minutes` now serves only tenants with no rule set. |
| `public/js/ess/portal.js` | `dmWhere` measures from the server's anchor, less finished breaks over the allowance, clock stopped at the shift end only with shift hours only. `dmMarks` says what lateness costs; no red sentence for staff without marks. |
| `tests/test_shift_hours_alv326.py` | New, pure, invented days only (see the strategy §6). |
| `tests/test_payroll_flags.py` | Defaults, overrides, negatives, the M1 limit checks, and an Employee Checkin made on the test site at 10:36:40 proving whole minutes (review P3-2). |
| `tests/test_day_marks.py` | The banner with the settings on, and a contract category with 15 minutes' grace and no marks. The 42 older banner tests are untouched. |

Each company's values are set on its own rule set. DTC's go on through
`C:\Users\Dell\grace-ops\step28-alv326-dtc-settings.py`, outside git: it prints what it
would change and writes only with `DRY_RUN=False`. Not run by me.
`grace-ops/step26-greens-and-shift-hours.py` was fixed for the four-value punch reader.

## Results against DTC

54 of 57 comparable days matched DTC exactly on quarters, reds and greens; 3 differ
because DTC's machine and ours hold different punches for those days. Details stay in
the ops script outside git.

## Seven dimensions, against the code written

| Dimension | Before → after |
|---|---|
| Performance | Neutral. No new engine query; the banner asks the engine once, as before. |
| Security | Neutral. No endpoint or permission change. Validation stops a limit that would silently turn reds into quarters. |
| Reliability | Improves slightly. A missing mid-day punch never costs a break. |
| Scalability | Neutral. |
| Maintainability | Improves. Figures are data; one `charge_for`. Two copies of the clipping rule remain (review P3-3, tracked). |
| Data integrity | **Degrades slightly for re-processed months.** Whole minutes (D3) apply to every enabled rule set: a punch a few seconds past grace is now on time, two punches 2 min 59 s apart merge, and a day on a band edge can move. Nothing stored changes until a re-process. |
| Compliance / privacy | Neutral in code; the real-data leak in the first round is removed from history. Security M3 (staff cannot read the "why" text) is left for Surbhi. |

## Release

A **migrate on every site** (two DocType JSON changes), then a **build** and the
**`sites/assets/assets.json` version bump** for `portal.js`. Code that lands before the
migrate reads the settings as off.

## Known gaps

- **Whole minutes for every tenant** - intentional trade-off (D3).
- **Two copies of the clipping and starting-point rule** (`payroll_rules`, `day_marks`) -
  acceptable simplification, review P3-3.
- **The banner reads an even punch count as "gone home"** for the night green; with every
  punch loaded it may mean "out at lunch". Older than this slice, display only.
- **Reason text order and the half-day wording changed for every tenant**; the figures
  are the same.
- **Security M3** - Surbhi's decision.
- **The banner JS was not driven in a browser**; traced by hand.

## Commands run

Throwaway containers only: `hrlocal-326` (image `alvoraa-app:dev-d3afcaa`, apps mounted
from this worktree), `hrlocal-326-db`, `hrlocal-326-redis`, network and volume of the
same name. Fresh site `test326` built like CI, then `migrate` there for the new fields.
The shared bench was not touched. Results are in the round-2 table below.

Round 2, one module at a time, `run-tests --app alvoraa_portal --module ...`, both batch
summaries read:

| Module | Result |
|---|---|
| `test_shift_hours_alv326` | 29, OK |
| `test_payroll_rules` (untouched) | 76, OK |
| `test_payroll_flags` | 16, OK |
| `test_day_marks` | 50, OK |
| `test_payroll_reprocess` | 12, OK |
| `test_salary_report` | 24 + 4, OK |
| `test_pay_slip_marks_067` | 18 + 2, OK |
| `test_alv291_attendance_fix` | 5, OK |
| `test_grooming_cap_066` | 42, OK |
| `test_leave_063_rules` | 43, OK |
| `test_leave_063_engine` | 23, OK |

Also `scripts/check_app_integrity.py` OK; ruff clean on every changed file; `node --check`
on `portal.js` OK. The full suite was not run (as asked).

Clean up: `docker rm -f hrlocal-326 hrlocal-326-db hrlocal-326-redis; docker volume rm
hrlocal-326-sites; docker network rm hrlocal-326`.

## Subtract pass

Round 1: removed the two constants (now settings) and edits to six existing tests (they
pass unchanged and now prove the old behaviour). Round 2: removed every real day from
the tests and documents; removed `_grace_minutes`'s rule-set branch, which nothing
reaches any more.
