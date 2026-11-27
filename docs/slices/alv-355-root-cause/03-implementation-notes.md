# ALV-355 / ALV-474 - one rule for which punches count: implementation notes

Worktree `/Users/mac/hr-app/.claude/worktrees/alv355-one-rule`, branch `alv355-one-rule`, built on `origin/dev` f043dfa7. Not pushed.

## What changed and why
`skip_auto_attendance` is set for four reasons (Frappe: day already marked; repeat scan; out-of-range machine date; HR set a punch aside). Three of the four are real punches. The pay engine already ignored the flag; the held-day and punch-fix screens did not, so they and the engine could disagree. They now follow the engine.

Ladder rung: new code, smallest possible (two small helpers, no new DocType, field or setting).

| File | Change |
|---|---|
| `payroll_rules_apply.py` | Two shared helpers: `aside_filter()` (the one "does it count" filter, guarded on the column) and `fold_repeat_scans(rows, day)` (keeps the rows the engine's `punch_minutes` keeps). `_punches` now calls `aside_filter()` - same behaviour as before. |
| `held_day.py` | `_day_logs` uses both helpers, drops `skip_auto_attendance: 0` and `offshift: 0`; docstring rewritten. `worked_out` returns ("Absent", 0, False, False, None, None) when no punch counts (ALV-474). |
| `held_team.py` | `_shaped` uses `aside_filter()` and folds each day. |
| `punch_fix.py` | `_check_aside` refuses only an already-set-aside punch. Day sheet `counted` = not set aside and not a folded repeat. Card `aside` = ticked or set aside. Card `logs` = same list as `_day_logs`, from memory. The two unused fetched fields removed from `day_punches` and `card_context`. |
| tests | New `tests/test_one_rule_alv355.py` (9 tests). `test_punch_fix_087.py` one assertion updated (it asserted the old rule). |

Left alone, confirmed by reading: `held_day.py` `files_as_machine() or doc.skip_auto_attendance` (a write-time hook on a new punch, asks "did the dedupe flag this one"); `punch_fix.py` lines that WRITE the flag in `apply`/`undo` and the `if punch.skip_auto_attendance` check after inserting an added punch (a write-path check). `punch_dedupe.py`, `field_app_access.py`, `punch_change.py`, `alv291_attendance_fix.py` (data repair scripts, not readers of the screens) not touched. HRMS's own `shift_type.py` is upstream - not touched.

Not touched on purpose: `seen_token` / SEC-1 (`punch_fix._token` still hashes the day's punch ids); ALV-473.

## Seven dimensions, against the code written
- Performance: neutral. Same single `get_all` per read; folding is in memory.
- Security: neutral. No permission path changed. `_check_aside` still refuses punches not on this employee/day and already set-aside ones.
- Reliability: improves. ALV-474 IndexError gone; before the migrate adds the column `aside_filter()` returns {} so every punch counts, as the engine did before slice 087.
- Scalability: neutral. No new query, no loop with queries.
- Maintainability: improves. One filter and one fold in one file instead of four copies.
- Data integrity: improves. No write path touched. Screens and engine now count the same punches.
- Compliance/privacy: neutral. Same fields shown; two fetched fields removed.

## Behaviour changes users will see
- A real punch Frappe had flagged now counts on the card, the day sheet and the manager list, so some held days will read differently (that is the fix).
- A day where HR set every punch aside reads Absent, 0 hours, count 0 - and the card opens.
- HR can now set aside a flagged real punch.

## Residual risk
- The card's "now" list still shows a folded repeat scan as a normal punch (it is only left out of the "after" count). Cosmetic; not changed to keep the diff small.
- Setting aside a repeat-scan row is allowed (harmless: the first scan still counts).
- A day left with count 0 and approved becomes Absent. That is what "no punch counts" means to Frappe; HR sees it in "If approved" first.
- Ran against a fresh own stack (alv355-*, since removed), not DTC data. The full `alvoraa_portal` suite was NOT run.

## Tests run (proven)
New `test_one_rule_alv355` 9/9 OK. Regression: `test_punch_fix_087` 134 OK, `_087_proof` 11 OK, `test_held_team_086` 33 OK, `_086_proof` 11 OK, `test_odd_punch_held_alv351` 15 OK. `test_held_day_085`: 39 OK, 6 fail only because `scripts/alv392_held_backfill_grace.py` is not mounted in my stack (environment, not code; not checked on a stack that has it).
Break-tests (production code broken, one at a time, then restored): old filter back in `_day_logs` -> flagged-punch and offshift tests failed; ALV-474 guard removed -> IndexError in the no-counting-punch test; `_check_aside` re-refusing flagged punches -> real-flagged-punch test failed; fold removed -> repeat-scan test failed. The card test does NOT fail without the guard (the card swallows the error), so the `worked_out` test is the one that proves ALV-474.
