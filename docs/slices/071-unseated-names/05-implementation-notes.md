---
slice: 071-unseated-names
artifact: 05-implementation-notes (the agent file calls it 03)
author: hrms-fullstack-engineer
date: 2026-10-25
status: BUILT LOCALLY. Not pushed. Nothing on any server.
branch: slice/071-unseated-names in .claude/worktrees/071-unseated-names, from origin/dev af0b7cdf
---

# 071 · Names in the "In no seat" tray — implementation notes

## Bad news first

1. **Two places where the build is not one commit per step.** Steps 3 and 4 share a commit
   (the "Place anyway" button calls the confirm, so neither works alone), and steps 8 and 9
   share one (their checks live in one file). Nothing was left out.
2. **The server test is in `alvoraa_portal/tests/test_unseated_071.py`, not under `hrms`** as
   the strategy said. CI runs only the `alvoraa_portal` and `alvoraa_goals` tests
   (`.github/workflows/ci.yml` "Run tests"), so a test under `hrms` would never fail CI.
3. **One DOM test file fails at random, on unchanged `origin/dev` too.**
   `alvoraa_portal/tests/portal_correction_test.js` ("an incomplete request was sent") failed
   3 of 6 runs on a clean `origin/dev` checkout. It is the attendance correction screen, not
   this slice. Not fixed here.
4. **The commit trailer says Opus 5.5, not Sonnet 5.5** as the brief asked: that is the model
   that wrote the code.

## What was built, file by file

| File | Change | Rung / why |
|---|---|---|
| `portal.js` `posUnseatedSheet` | One row per person under each role line: name linked to `/app/employee/<id>` (new tab), ID in grey, "Joined 17 Sep" (year when not this year, done in the row; `posDay` untouched), "No manager" chip only when true, sorted by name. Empty sentence. Success note at the top. Q3: of two matching seats, the first with room, else the first by title. | New code in an existing panel |
| `portal.js` new `posUnRoom`, `posUnPlace`, `posFullOpen`, `posFullClose`, `posFullGo`, `posPickSeat` | Room rule (half a place open, or 0 places = no limit, E1); the row button; the full-seat confirm; which seat the dialog fills | `posUnRoom` and `posPickSeat` each have 3+ callers |
| `portal.js` `posPickPerson`, `posPickSearch`, `posPickOne`, `posShowWhatTheyHold`, `posPickSave`, `posPickClose` | Optional `from` (no argument = today's behaviour); pre-pick by employee ID; context line; ID in each candidate line; stale pick cleared (PD14); candidate lines reachable by keyboard (as in the prototype); "Putting them in…" and the dialog stays open until the reload (PD8, both paths); `add_place`; error texts; the one re-read after no answer (R-3); focus back to the opener | Changes to existing functions |
| `portal.js` `posWire` keydown | Escape closes the confirm, then the dialog, then the tray; leaves the tray if any other dialog is open or already handled the key | Bug fix (PD6) |
| `parts/positions.html` | `#pos-person`: `role="dialog"`, `aria-modal`, `aria-labelledby`, `role="alert"` on its error, one `#pos-p-ctx` line. New `#pos-full` after `#pos-delete`, same shape | Markup |
| `panels.css` | `.pos-un*` rows, `.pos-sheet h2:focus`, phone floors for `#pos-person` and `#pos-full`, copied from the prototype's "071" block, after the Positions trays block | CSS |
| `register.py` `assign_person` | Optional `add_place=0`. When set and the person would over-fill a seat with a limit, `save_position(name, seats + 1)` before the insert, in the same request (D1) | Optional parameter on an existing endpoint |
| `tests/test_unseated_071.py` | 8 server tests incl. the pin test | — |
| `scripts/check_positions_tree.js` | Section 22: 42 new checks (rows, buttons, confirm, dialog, save, errors, Escape) | — |
| `scripts/browser_check_positions.js` | 17 new browser checks (1440 and 390 px, Escape, print with each layer open) | — |

No new DocType, field, endpoint, job, cache or index. No new `ignore_permissions`.

## Acceptance (from 04 §2 and 02 §9)

| Story | How it is met | Proved by |
|---|---|---|
| US-1 rows | `posUnseatedSheet` | node "071 rows" (8), browser "one row per person" |
| US-2 300 people | One string, one `innerHTML`, no call | Browser at 82; 300 not run in a browser (see gaps) |
| US-3 room | `posUnRoom`, `posUnPlace` → `posPickPerson(from)` | node "071 room", "071 E1", "071 dialog from the tray" (4) |
| US-4 full + confirm | `#pos-full`, `posFull*` | node "071 full", "071 confirm" (4); browser |
| US-5 saving | `posPickSave`, `add_place`, server D1 | node "071 save/success" (6); server pin test; one real save in a browser: 82 → 81, seat 2 of 2 → 3 of 3, note focused |
| US-6 errors | lost / refused / lost-but-saved | node (4) |
| US-7 empty | empty sentence | node (2) |
| US-8 HR User | buttons follow `POS.may_edit`; server refuses | node "071 HR User"; server "may not change seats" |
| US-9 no matching seat | no button | node |
| US-10 not HR | unchanged (no key → no tile) | existing checks still pass |
| US-11 print | `#pos-layer` and `.gp-backdrop` already hidden in print | browser: tray, dialog, confirm open → no unseated name or ID in the print view; wall chart browser check passes |
| US-12 keyboard | Escape order, focus return, candidate lines by keyboard | node (6), browser (3) |

Audit, seen on test071 after the real save: a Version row by the HR user with `seats`
changed, and the Assignment owned by the same user, approvals off.

## Prototype parity

Built as drawn, with PD1–PD14 as approved. Differences I know of, none visible with whole seats:

- The confirm's "N in all" and the context line use `seats + 1` (what the server does); the
  prototype used `ceil(seats) + 1`. Same for whole numbers; differs only for a 7.5-place seat.
- The dialog title stays a `div` with an id (the prototype drew an `h2`): no visual change.
- The dialog's field labels stay as today's `div`s; the prototype used `<label for>` while
  saying the markup was unchanged.
- `.pos-sheet h2:focus{outline:none}` (prototype 071 block) also applies to the seat tray and
  the "No reporting manager" tray headings when focus is placed there by script.

**Surbhi: please say yes or no to these four.**

## Non-functional, against the code written

| Dimension | Before → after | Why |
|---|---|---|
| Performance | neutral | Opening the tray: no call. A plain placement: 10 statements; with "Add a place": 26 (measured, `test_statement_count_is_a_fixed_handful`). Per click, not per person |
| Security | neutral | No new endpoint; `add_place` acts only after `_position_in_scope`, and `save_position` checks Write and scope again. Proved: another branch and no Write are refused with the count unchanged. `test_portal_security_010` 45 + 5 OK |
| Reliability | improves | Escape no longer drops the tray; a stale pick cannot be saved; place and person go in together or not at all (rollback test) |
| Scalability | neutral | List size already bounded by headcount and already sent |
| Maintainability | neutral | ~155 lines JS, 13 HTML, 20 CSS, 9 Python |
| Data integrity | improves | No state where the count rose and nobody was placed; every count change has a Version row |
| Compliance / privacy | neutral | Same six fields to the same readers; nothing new printed or logged |

## Commands run and what they said

- `node scripts/check_positions_tree.js`: 219 checks, 0 failures (177 before).
- `node scripts/run_dom_tests.js`: 13 files; 0 failed, except the random `portal_correction_test.js` failure above.
- `check_wall_chart.js` 183 checks; `check_portal_handlers.js`, `check_undefined_js.js`, `check_tag_balance.py`, `check_design_system.py`, `check_app_integrity.py`: all OK.
- Browser on test071 (127.0.0.1:8071): `browser_check_positions.js` 56 passed, 0 failed;
  `check_wall_chart_browser.js` all passed; `check_portal_trays.js` 342 checks, 0 failures;
  `check_positions_connectors.js` 0 failures.
- Every guard broken once on purpose (year, chip, E1, Q3, may_edit, focus, pre-pick, PD14, ID
  line, `posPickSeat`, `add_place`, network text, re-read, "Putting them in…", note once,
  three Escape rules, focus return, phone floor, print rule, server raise, `seats and`): each
  made its check fail.
- Python on test071 (own container): `test_unseated_071` 8 OK; `test_register_fill_194` 62 OK
  (2 skipped); `test_register_194` 38 OK; `test_positions_064` 17 OK; `test_portal_security_010`
  45 + 5 OK. Full suite: see below.

**Full suite: NOT completed.** `bench run-tests --app alvoraa_portal` on test071 ran 6.5 hours
(normally about 2) with no summary line, and was stopped on the coordinator's rule (silent 30+
minutes). `alvoraa_goals` and the other hrms org-structure modules did not run after it. The
frappe log ends with `RuntimeError: object is not bound`. I do not know which test it hung in.
The modules this slice touches all passed when run alone (above). **CI on a fresh site, or one
full run on a clean container, is still owed before a push.**

## What else moved while I worked

`origin/dev` stayed at `af0b7cdf` through every step. At the end 20 commits came in, all slice
066 grooming (its docs, `grooming.py`, `payroll_slip.py`, its tests, a `gm*` block in
`portal.js` and its own block in `panels.css`). Rebased onto `f207e82c` with no conflicts.
Their 33 `gm` functions are still in `portal.js`. After the rebase: positions tree 219,
wall chart 183, DOM 13/13, handlers, undefined, tags, design, integrity all OK, and
`test_unseated_071` 8 OK. 065-option-a and 072-seats-follow-reporting (renumbered from 070) are still not on `dev`.

## Environment

Own containers `hrlocal-071` (bench), `hrlocal-071-redis`, `hrlocal-071-proxy`
(127.0.0.1:8071 only), volume `hrlocal-071-sites`, site `test071`, database `_071unseat`
(copied from test_site, then migrated on test071 only). Seed: invented company "Demo071 Retail"
with 82 unseated people and login `probe071@example.com`. `hrlocal-bench` and every other
container were not touched.

## Known gaps and shortcuts

| Item | Label |
|---|---|
| 300 people not rendered in a real browser (82 were). The code path is the same string build | acceptable simplification |
| The friendly "Could not reach the server" text is used only from the tray; the editor path still shows the raw message | intentional trade-off (not in scope) |
| If the network stays down for the re-read too, the message says "not in the seat" even if the first save landed | intentional trade-off (R-3 as approved) |
| `positions.html` strings are not wrapped for translation, like the rest of that file | temporary debt (removed when that file is translated) |
| Dialog labels are `div`s, not `<label for>` (existing) | temporary debt |
| `portal_correction_test.js` fails at random on `origin/dev` | not this slice; worth a ticket |

## Subtract pass

Removed: a check line that always passed (`|| true`), a debug script. Considered and kept:
`posUnRoom` (3 callers), the R-3 re-read (approved), the keyboard handlers on candidate lines
(in the prototype).
