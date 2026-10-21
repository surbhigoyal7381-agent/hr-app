# 064 · Implementation notes (22 Oct 2026; v10 and v11 applied)

**Status: built and checked locally, to the approved design prototype-v9. Nothing is pushed.**
The full test suite has not been run (it runs once, at the end, before a push is asked for).

Branch `slice/064-organogram` in `.claude/worktrees/064-organogram`, cut from
`slice/062-widget-after-checkin` so the unpushed `5a211f3f` is underneath. The earlier chart
built to the rejected v4 design is kept only on the local branch
`slice/064-organogram-v4-ui-archive`; none of it is on this branch.

## Commits (oldest first)

| Commit | What |
|---|---|
| 83c1c499 | Slice documents |
| c05d353c | `position_table`: `hired_on`, `may_see_leaving`, `may_edit_employee`; the JS check runs in CI's DOM tests |
| fb19ebcc | `position_table`: `unseated`, `active_people`, HR scope only (SEC-2, PRIV-1) |
| 6188a2c7 | `reporting_mismatches` rewritten: scoped, HR only, 2 statements (SEC-5) |
| ced2a4a5 | Seat-link guard on Job Opening; link editable; Job Opening history (SEC-8, PRIV-3) |
| bc594a83 | Hire placed in its seat on joining; filled opening closed; ignore_permissions ceilings (SEC-6/7/9/10) |
| 19db2be7 | Notes at the pause (superseded by this file) |
| 9c589925 | Darker amber token (Q12) - amber only; v9 has no blue |
| 398adb1f | The v9 chart, toolbar, filters, tiles, list, sheets, people panels, records chips |
| a549f911 | Find |
| e4f65633 | Phone outline |
| 42197914 | `created` / `first_seat_created` removed again - v9 has no "new seat" |
| 8cc06351, a3897b41 | Connector check on the real page; browser check rewritten |

## Surbhi's answers (21-22 Oct 2026), now in the build

- The placed seat's reason names the **Job Opening only**, not the applicant (Frappe HR names a
  Job Applicant by its email). AC-64 and PRIV-3 read: "Placed on joining from Job Opening {id}".
- A hire is placed if the seat has room **on the joining date** (and today, when the joining
  date is already past); otherwise skipped and HR told (AC-66 over SEC-6's "and today").
- Only **seat-linked** openings close when filled (E-1).
- The people lists and records chips stay **HR scope only** (X-2, X-3); owners later.
- "Print this view": later, not built (X-4).
- "Who sees the complete hierarchy": no code - Branch User Permissions decide it (see release note).

## Release note

1. **064 reaches `main` only after 061.**
2. **At DTC, at release: give HR Manager Read AND Write on Alvoraa Position** (Desk, Role
   Permissions Manager). Configuration, not code; 064 changes no permission (SEC-11).
3. To let Vaneet (or anyone) see the complete hierarchy: remove their Branch User Permission, or
   set its "Applicable For" to a doctype other than Employee. Surbhi's production step.
4. The migrate makes Job Opening's Position field editable and adds one Property Setter
   (`Job Opening-main-track_changes`). Rollback: set the field read-only; delete the setter.

## Measured (own container `hrlocal-064`, site `test064`)

| What | Number |
|---|---|
| `reporting_mismatches`, before (ppj, 403 people) | 1,458 statements, 1.4 s |
| `reporting_mismatches`, after | 2 statements at ~10 and ~200 assignments; 6-8 ms |
| `position_table`, HR reader | 7 statements at 20 people and at 200 |
| Connector check, DTC-shaped site (120 seats) | 0 false or missing links in 40 states, light and dark, 1440 and 390 px; no script errors |

## Checks run

- `node scripts/check_positions_tree.js`: 105 checks OK (also runs in CI via `run_dom_tests.js`).
- `node scripts/run_dom_tests.js` (jsdom installed in the worktree with `npm ci`): 11 run, 0 failed.
  The "SyntaxError: Unexpected token '{'" lines it prints also appear on `origin/dev`.
- `scripts/check_positions_connectors.js` on the real page: 0 bad links. Broken on purpose (the
  line from a lead drawn straight through the lead below it) it fails on "Admin opened".
- `scripts/browser_check_positions.js` on the real page: 14 passed.
- Python, modules only: `test_positions_064` 17 OK, `test_hiring_064` 26 OK, the SEC-16 ceiling
  test OK; org-structure neighbours OK except the pre-existing
  `test_register_194.test_dtc_shaped_rows_let_the_owners_in_and_keep_hr_out` error.
- Static: app integrity, API paths, design system, portal handlers, undefined JS, tag balance: OK.
- Not run: `check_contrast_rendered.py` (needs Python Playwright, not installed). The amber token
  was checked by calculation: 4.76:1 on its tint.

## The prototype's crash

The approved prototype fails on "open Delhi, By branch, Open every level": it keeps the old view's
open-team choice. The product clears it on every view change, and a group only ever opens one of
its OWN leads. Tests: that exact sequence and every view switch after every open state (node), and
the same sequence on the real page (connector check).


## v11 (2b691c65, a2819790)

By branch and By department wrap into rows that fit the frame (5 / 4 / 3 per row at 1,128 /
1,006 / 830 px), one opens at a time below the whole row under "Under <name>" with its own line;
the rule repeats inside strips; a small family's opened child goes to a strip below the row;
switching view clears every open choice and stale choices are ignored. On this panel no text is
under 12 px and no target under 24 px (44 on a phone).

Connector and layout check on the real page (DTC-shaped seed, 120 seats, departments added):
1440 / 1280 / 1024 windows (frames 1,128 / 1,006 / 830) and a 390 phone, light and dark, every
branch and department opened in turn with up to four teams inside each: 180 states, 0 false or
missing links, 0 layout failures, and the chart never wider than its frame in any view.

Differences from v11, on purpose: the real frames are 1,006 and 830 px where the prototype says 970
and 820 (same column counts); nested departments (today's tree) open inside the strip by their own
box, one at a time, as the branches do; the panel's label and small-button sizes were raised to meet
the 12 px / 24 px rule.

## Full suite, once (22 Oct 2026, own site test064)

- `alvoraa_goals`: 18 OK.
- `alvoraa_portal`: three batches - 16 OK; 952 with 3 errors; 2,049 OK. The 3 errors are
  `test_leave_year` (TestLeaveYearStart): its Fiscal Year overlaps ERPNext's `_Test Fiscal Year 2025`
  on this site, which carries ERPNext's test records. Not from 064; CI avoids it with a separate site.
- `hrms.alvoraa_org_structure` modules: all OK except the pre-existing
  `test_register_194.test_dtc_shaped_rows_let_the_owners_in_and_keep_hr_out`.
- DOM suite (`run_dom_tests.js`): 11 run, 0 failed. Node Positions check: 122 checks.
- Not run: the hrms payroll doctype tests CI runs on its own site, and `check_contrast_rendered.py`
  (no Python Playwright here).

## Known gaps

- Fixed by v10 (29e57a52): the "No reporting manager" box is pinned to the chart's top-right
  corner and groups take 5 / 4 / 3 columns at 1,128 / ~1,000 / ~830 px frames. Connector check at
  those widths and 390: 0 bad links. By branch / By department "Open every level" still runs wide
  (v11 is being designed for it).
- "Seats with no seat above them" (B-14) are listed in the No-reporting-manager sheet with "Open
  this seat"; v9 does not draw them.
- The identical-seat grouping ("5 of these", K3) is gone: v9 does not draw it; the groups replace it.
- AC-66 (3) no joining date and (8) already holds a seat: guarded in code, cannot be built as tests.
- A placement does not follow a joining date changed later (OD-7).
