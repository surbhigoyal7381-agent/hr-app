---
slice: 072-seats-follow-reporting
artifact: 05-implementation-notes (change-process steps 4 and 6)
author: hrms-fullstack-engineer
date: 2026-10-25
status: built LOCALLY. Nothing pushed, nothing deployed, no server or shared container touched.
branch: slice/072-seats-follow-reporting (renamed from slice/070-...; Surbhi renumbered the slice 072, 25 Oct) in .claude/worktrees/070-seats-reporting, built on origin/dev af0b7cdf, rebased onto f207e82c (066 grooming) and then onto 57d1a157 (ALV-217 readable on phone)
commits (after both rebases; the first 11 messages still say 070): 1562de5e (1) · 946fe5fd (2) · 3f24dede (3) · 39825076 (4) · d54a53cb (5) · b791f6b9 (6) · 4d05eceb (7) · f2cb3f33 (8) · dd8c3bbe (subtract pass) · 8fd54d51 (CSS "{#" fix) · 63231141 (check fix after the 066 rebase) · b6b88848 (renumbered 072) · then this docs commit
---

# 072 seats · Implementation notes

## Bad news first

1. **The rendered contrast check did not run.** `check_contrast_rendered.py` needs Python Playwright,
   which this machine does not have. New text uses token pairs the page already uses
   (`--text3` on `--surface`, `--primary` on `--primary-lt`, `--text2`), and `check_design_system.py`
   passes. Dark and light were looked at in screenshots, not measured for contrast.
2. **Nothing was seen on a live site.** Every browser check ran on the page built from this checkout
   with the census-shaped fixture (invented names). The real DTC shape is still unmeasured; the A1
   size below is the fixture's.
3. **Boxes still have 11 px text** (the second line and the avatar), from the design system's
   `--fs-xs: 11px` (slice 009 decision 5, still open). The prototype raised it to 12 px for itself.
   Nothing this slice adds is under 12 px; I did not change the token (it touches every page).
4. **One rule follows 01c, not the spec.** `manager: ""` (no manager on record) goes to HR readers only
   (01c SEC-1). AC-2 in the spec does not say "HR only". For an owner, a seated person with no Reports
   To therefore reads "Reports to a manager who is not on this chart". **Needs your yes**, or a one-line
   change to send `""` to everyone.

## What I built, file by file (rung 4: new code in our own app)

| File | Change | Mechanism and why |
|---|---|---|
| `hrms/.../register.py` | `position_table`: two joined columns on the existing assignment read (`employee.reports_to`, `employee.status`); new `_add_managers` writes one `manager` key per person, fail-closed | Frappe's own link-field join (`LinkTableField`, read in v16.33.1 source) - no new statement, no hand-built SQL |
| `alvoraa_portal/.../portal.js` (Positions section only) | `posPlace` (the one placement rule, screen and paper), copies as end boxes, hidden homes, box words, view note, tray section and per-person lines, Show, Find/filters/outline, error state, wall chart walks the placed model | Browser code, because placement depends on what is drawn (view, filter, paper start) |
| `ocNodeCard` | three optional fields: `cls`, `quiet`, `empty` | The Organisation page sets none, so its markup is byte-for-byte unchanged (pinned by a test). The strategy said two fields; the third (`empty`) carries "None here: all N shown under ..." in place of "Nobody in this seat", as drawn |
| `panels.css` | copy dashed border, grey line, outline, view note, tray list, 44 px empty/error buttons on a phone, paper copy and line | Lines added in the Positions and `.pos-wall` blocks only |
| `parts/positions.html` | "Who reports to whom" -> "Reporting lines" | Q4 |
| `scripts/lib/wall_chart_fixture.js` | `reporting()`: F-DTC90 with `manager` keys shaped from the 24 Oct census | One fixture feeds the jsdom checks, the screen connector check and the paper check |
| NEW `alvoraa_portal/tests/test_reports_to_072.py` | 7 server tests | In `alvoraa_portal`, so CI runs it (01c bad news 2) |
| `check_positions_tree.js` section 22, `check_wall_chart.js`, `check_wall_chart_browser.js`, `check_positions_connectors.js` | see Tests | |

Not built, as decided: Part A/B of the CFO script, the "put someone in" dialog line (Q4), copies in
Branch/Department, copies across companies (Q6), any setting, cache, field, hook or endpoint.

## Acceptance criteria

| AC | How it is met | Proved by |
|---|---|---|
| AC-1..AC-7, AC-10 | `_add_managers`: id only if the manager is Active and in this reply (seated in its seats, or in HR's `unseated`); `""` HR only; absent for Left/outside/other company/past or future date/a person who left | `test_reports_to_072.py` (7 tests, shown to fail 4 with the "in this reply" check removed) |
| AC-8 | Same read, joined | 7 statements at ~10 and at ~200 seated, with managers; the base code measured 7 too (`test_positions_064` flat test on `af0b7cdf`) |
| AC-9 | No key-set assertion broke; `ignore_permissions` in `register.py` still 4 | full suite (below) |
| AC-11..AC-21, AC-65 | `posPlace` R1-R5, C1-C4, H1-H3, Q5, G3, Q6, loop | tree check 22a/22b with an oracle written in the test (fails 19 with R1 removed); connector check |
| AC-22..AC-26 | open tag, opening and child seats on the home only; home hidden on the three conditions | 22a |
| AC-27..AC-32 | box words through `drT` | 22c (exact strings) |
| AC-33 | dropdown, notes, print heading | 22e (fails with the old name) |
| AC-34, AC-52..AC-54 | tiles, Branch/Department and the Organisation card unchanged | 22d |
| AC-35..AC-42, AC-50 | `posWhereItShows`, `posReportsLine`, `posShowPlace`; split advice removed in every view (P-25) | 22f (fails with the line broken) |
| AC-43..AC-48 | outline (desktop only), Find into copies, G1/G2 | 22g (fails with G1 removed, and with Find pointed at the home) |
| AC-49 | nothing outside scope named: the page only reads the reply; unknown ids never echoed | 22c/22f marker checks (`SEAT-HIDDEN-SNTL`, `MGR-ABSENT-SNTL`); server AC-4 |
| AC-51, PRIV-1 b | copies hold the same person objects; private keys change no box | 22a, 22d |
| AC-55..AC-60, PRIV-2 | paper walks the placed model; keys gain `copy`, `same`, `more` only | `check_wall_chart.js` 072 block (fails 6 with `manager` copied onto paper) |
| AC-61, AC-62 | measured below; the panel's 069 warning is unchanged | `check_wall_chart_browser.js` |
| AC-63 | fixed words, `role="alert"`, Try again | 22h (fails on the previous code) |
| AC-64, AC-66 | measured at 390 and 1440, light and dark | one-off measurement (below) |
| AC-67 | Reports To is read on every load; nothing stored | by construction; not tested against a live edit |

## A1 with copies (AC-61) - the number Surbhi asked for

Census-shaped fixture (95 seats, 407 people, copies under the CFO, a 57-name Back Office copy
under the Backoffice Executive), All, one sheet, Show Vacant on:

| | A3 | A1 | A0 |
|---|---|---|---|
| F-DTC90, no managers (069's own measure, unchanged) | 4.4 pt | **9.0 pt** | 12.8 pt |
| With copies, HR copy off | 4.0 pt | **8.5 pt** | 12.2 pt |
| With copies, HR copy on | 3.9 pt | **8.4 pt** | 12.1 pt |
| With copies, 2 levels | 10.9 pt | 22.4 pt | 32.0 pt |

**All on A1 stays above 8 pt (8.5).** 069's kill line is not changed. If DTC's real shape falls under
8 pt, the panel already offers A0 or several sheets and never shrinks names (AC-62); that path was not
exercised, because the fixture stayed above 8.

## Seven non-functional dimensions, against the code written

| Dimension | Before -> after | Verdict |
|---|---|---|
| Performance | 7 statements -> 7 (measured both). Reply 41,483 bytes at ~200 seated with managers. Placement is one pass per paint; the jsdom and browser runs show no slowdown (wall panel changes 3-20 ms) | neutral |
| Security | No new endpoint, write or `ignore_permissions`. `manager` fail-closed, proved by markers that must never appear | neutral |
| Reliability | A missing, Left or unseen manager draws the person at home. Copies have no children, so no loop (AC-21 tested). Old browser + new server ignores the key | neutral |
| Scalability | Flat statements; browser work linear in people | neutral |
| Maintainability | portal.js +~420 code lines (more than the strategy's ~150: tray, Find, paper walkers). One placement function for screen and paper | degrades, slightly |
| Data integrity | The chart now agrees with approvals and appraisals. Nothing stored, nothing to go stale | improves |
| Compliance / privacy | Owners see the manager link only when both people are on their page (Surbhi's yes, 01c Q1). Unseated names HR only. No log lines | neutral |

## Commands run, real results

| Command | Result |
|---|---|
| `bench --site test070s run-tests --module alvoraa_portal.tests.test_reports_to_072` | 7 OK (and 4 failures with the "in this reply" check removed) |
| `test_positions_064` flat test on the base `register.py` | 7 statements at 20 and 200 |
| `node scripts/check_positions_tree.js` | 272 checks, 0 problems |
| `node scripts/check_wall_chart.js` | 199 checks, 0 problems |
| `node scripts/run_dom_tests.js` | 13 run, 0 failed |
| `FIXTURE=reporting node scripts/check_positions_connectors.js` | 0 failures; 1440/1280/1024/390 px, light and dark, incl. the five 072 cases; 8 failures with managers swapped |
| `node scripts/check_wall_chart_browser.js` | all passed (incl. 072 paper lines, A1 above) |
| `check_app_integrity.py`, `check_design_system.py`, `check_tag_balance.py`, `check_brand_spelling.py`, `check_api_paths.py`, `check_portal_assets_gate.py`, `check_portal_trays.js --static`, `check_portal_handlers.js`, `check_undefined_js.js` | all OK |
| One-off phone/a11y measure (scratchpad, design tokens injected) | 390 px: no sideways scroll, Show buttons 44 px, tray a bottom sheet, focus to the heading, Escape returns focus to the box, no new text under 12 px; 1440: same, Show 33 px |
| Full `bench --site test070s run-tests --app alvoraa_portal` (before the rebase) | 3,153 tests in three batches (16 OK; 962: 2 failures; 2,175 OK). Failure 1 was mine: `{#` in panels.css read as a Jinja comment by `test_portal_split_034` - fixed, module re-run OK. Failure 2, `test_nav_consolidation_060` HR-manager menu flag: failed alone too, then passed on base code AND on my code in later runs - leftover site state from the suite, not this change |
| `hrms...test_register_194`, `test_register_fill_194` (strategy pins) | fill: 62 OK. 194: 5 failures straight after the suite, then 38 OK on base and 38 OK on my code - same leftover state |
| After rebasing onto f207e82c (066) | every line 066 added to portal.js (558) and panels.css (83) is still there. **One check of mine failed**: `check_positions_tree.js` 22h "072 AC-63: Try again loads again" - it counted every gpFetch call and 066's bell calls it too (3 not 2). **Fixed** in 63231141: it counts position_table calls only |
| Python on the 066 code: a fresh site `test070t` in my own container (new-site + install-app, no `bench migrate`) | test_reports_to (7 OK; 7 statements at ~10 and ~200; 41,487 bytes), test_positions_064 17 OK, test_hiring_064 26 OK, test_register_fill_194 62 OK (2 skipped), test_portal_security_010 45 + 5 OK, test_grooming_066 64 + 1 OK, test_grooming_cap_066 42 OK |
| After rebasing onto 57d1a157 (ALV-217) and renumbering | clean rebase; all 515 portal.js and 5 run_dom_tests.js lines of theirs present; tree 272, wall 199, DOM suite 14/14 (their phone test included), integrity, undefined-JS, handlers OK; All on A1 re-measured: 8.5 pt (8.4 HR copy), unchanged. This slice adds no server call, so the 15 s timeout helper rule has nothing to apply to (the chart's one call is the existing `gpFetch`) |

Screenshots: `C:/Surbhi-Git/hrlocal-data/ux-review/2026-10-25-slice070-build/` (chart with the CFO
opened, Back Office tray, paper, at 1440 and 390, light and dark).

## What else moved while I worked

`origin/dev` stayed at `af0b7cdf` during the build. At handoff 20 commits of slice 066 (grooming red mark: `grooming.py`, payroll files, hooks, reports, its own `gm*` block in portal.js, its own CSS block, tests, docs) had arrived. Rebase was clean, no conflicts. Proof nothing of theirs was lost: every added line of theirs in portal.js and panels.css is present in the rebased files (0 missing). Then ALV-217 arrived (9 commits, "readable on phone": portal.js +785, frame.css, home, request-modals and requests templates, the leave test, `portal_phone_070_test.js`, run_dom_tests.js, its docs); the second rebase was clean too, 0 of their lines missing.

## Merging with slice 071 (slice/071-unseated-names, not on dev yet) - keep both

Read from its branch (bec85cb9). Three places meet; none changes the same behaviour, so each is "keep
both", never `--ours`/`--theirs`:

| Where | 071 | 072 seats | How the merge keeps both |
|---|---|---|---|
| `scripts/check_positions_tree.js`, end of file | adds "section 22" (In no seat names) and `async function unChecks()`, and ends with `deleteChecks().then(unChecks).then(...)` | adds "section 22" (seats follow reporting: `S70`, `oracle072`, `async function seats072()`) and ends with `deleteChecks().then(seats072).then(...)` plus `process.exit(0)` | Keep both blocks in commit order; renumber whichever lands second to **section 23**. One final chain: `deleteChecks().then(unChecks).then(seats072).then(() => { ... process.exit(0); })`. Keep 072's `process.exit(0)` (its jsdom window keeps Node waiting). Then check both: the run must report 071's checks and 072's (272 today) with 0 problems |
| `portal.js` `posWire` keydown handler | replaces the one Escape line with its "only the top layer closes" body | adds the `relate` mouseover/focusin listeners directly after that handler's `});` | Take 071's handler body unchanged, then 072's `relate` lines after it. Prove with `grep -n "posFullClose\|relate" portal.js` |
| `register.py` | `assign_person` gains `add_place` | `position_table` + new `_add_managers` | Different functions; no textual conflict expected |

Proof after the merge: every `+` line of each side's commits present in the merged files
(`git show <commit> -- <file> | grep '^+'`), then `check_positions_tree.js`, `run_dom_tests.js`,
`test_reports_to_072` and `test_unseated_071`.

## Rebase onto origin/dev 52fc3451 (slice 071, ALV-228, 066 network-error fix) - 26 Oct

Came in: 16 commits - slice 071 (In no seat names, Place in seat, the ALV-228 scope fix, Escape closes only the top layer, reads `e.kind` from gpFetch) and 066's "a grooming call with no answer" fix with `portal_grooming_066_test.js`.

- Two conflicts, both in `check_positions_tree.js`, resolved as planned above: 071's section 22 kept whole, this slice's became section 23, one chain `deleteChecks().then(unChecks).then(seats072)`. `portal.js` merged on its own: 071's Escape body, then this slice's outline listeners.
- Proof: every line 071/066 added to portal.js (153), panels.css (20), positions.html (16), register.py (24), run_dom_tests.js (4) and the check file (230) is present, except 071's old one-check chain, which is now the joint chain.
- This slice adds no server call, so the 15 s helper has nothing new to cover; its one error path (the chart load) shows fixed words for every error, so it needs no `e.kind`.
- Node: tree check 324 (071's and this slice's), wall chart 199, DOM suite 15/15, trays (static), handlers, integrity, undefined-JS, tag balance all OK. All on A1 with copies: 8.5 pt (8.4 HR copy), unchanged.
- Python on test070t (own container): test_reports_to_072 7 OK, test_unseated_071 12 OK, test_positions_064 17 OK, test_hiring_064 26 OK, test_register_fill_194 62 OK (2 skipped), test_portal_security_010 45 OK, test_grooming_066 64 + 1 OK.

## Review fixes (06-review.md) - 26 Oct

| Finding | Fix | Test that fails without it |
|---|---|---|
| M1 tray heading | Reporting lines: "... · set up under Owner", as the prototype (P-28) | tree check "072 review M1" |
| m3 "None here" on paper | follows Show Vacant (P-29) | wall check "072 review m3" |
| m1 missing tests | 4 new server tests: Suspended and Inactive manager not sent (AC-3), a manager whose only seat ended not sent and a current covering seat sent (AC-10), a changed Reports To shows next call with no seat or assignment `modified` changed (AC-67) | Suspended test fails with the status check removed (shown) |

**Why the reviewer's fresh site errored, and what a fresh site needs.** Read on `test072_fresh` (new-site + install-app only): `MandatoryError: [Alvoraa Position, Top 072]: company` - **a bare site has no Company**. CI's whole-app run gets ERPNext's test records (including companies); a one-module run does not. The second company the 064/072/071 tests make then also needs ERPNext's "Transit" Warehouse Type, which the setup wizard normally creates. Not slice 066, not migrate, not roles. **Fixed in the tests:** the shared helper `_company()` (hrms `test_org_structure.py`) now calls a new `ensure_company()` that makes the warehouse type and a company when missing; `_second_company()` (test_positions_064) uses it too. A fresh site now needs only `allow_tests` and `throttle_user_limit 1000`, as CI sets.

**Results (26 Oct), on a bare fresh site `test072_fresh` and on `test070t`, same numbers on both:** test_reports_to_072 11 OK (7 statements at ~10 and ~200) · test_unseated_071 12 OK · test_positions_064 17 OK · test_hiring_064 26 OK · test_register_fill_194 62 OK (2 skipped) · test_portal_security_010 45 + 5 OK. Node: tree 325, wall chart 200, DOM suite 15/15, trays, handlers, integrity, undefined-JS, tag balance OK. The sites `test072_sec` and `test072_rev` were not touched.

## Prototype parity - differences

| # | Difference | Status |
|---|---|---|
| D-1 | `""` HR only (bad news 4) | **needs your yes** |
| D-2 | Box second line and avatars 11 px (design system) | pre-existing, not changed |
| D-3 | The "+3 more here" line shows a "+M" avatar (today's rendering of the overflow line); the prototype shows "+" | pre-existing look, not changed |
| D-4 | A home box keeps "branch · department · N of M filled" (the prototype dropped the department) | as today (AC-54) |
| D-5 | "N open" prints on every partly filled seat on paper, not only shared ones - as the prototype's own print code does (P-27) | as approved; one 069 assertion updated |
| P-28 | Seat tray heading in Reporting lines: "... · set up under Owner" (was "reports to Owner"), as `prototype-v1.html` line 565 draws it; Branch and Department keep "reports to" | **matches prototype** (review M1, fixed; tree check fails without it) |
| P-29 | Paper: "None here: all N under ..." follows the Show Vacant tick like "Vacant" and "N open" | fixed on the coordinator's instruction (review m3); wall check fails without it |

## Known gaps and shortcuts

| Item | Label |
|---|---|
| Contrast not measured (no Python Playwright) | temporary debt - removed by running `check_contrast_rendered.py` where Playwright is installed |
| No live-site run; DTC's real A1 size unknown | temporary debt - removed by the dev run Surbhi approves |
| Fixture-mode browser checks do not load the shared design tokens (the page loader expands only `ess/` includes) | acceptable simplification: geometry and lines are real; the one-off measure injected the tokens |
| 065 plans not landed: PRIV-1 (a)/(c) run on 065's branch at merge | intentional trade-off (01c C3) |
| Seat ids are titles; `ocNodeCard` does not escape `'` in its onclick (pre-existing, seen while reading) | not touched - for you to decide |
| Connector and wall browser checks are not in CI (Playwright) | intentional trade-off (01c R5); the jsdom oracle is in CI |

## Subtract pass

Removed: a per-box "leaving" flag on copies and the two helpers behind it (not drawn in the prototype;
the person's own tag already travels). Kept the third card field (`empty`), because the approved box
words need it and the Organisation page never sets it.
