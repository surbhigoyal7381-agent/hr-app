# 064 · Implementation notes (paused part-way, 21 Oct 2026)

**Status: the server side is built and tested. The chart UI is ON HOLD.** Surbhi chose to keep
the first organogram design (prototype-v1; a v5 is being drawn), so the browser work built from
prototype-v4 stops here. Nothing is pushed. The full test suite has not been run; it waits until
the UI direction is settled.

Branch `slice/064-organogram` in `.claude/worktrees/064-organogram`, cut from
`slice/062-widget-after-checkin` so the unpushed `5a211f3f` is underneath.

## Commits

| Commit | What | Part |
|---|---|---|
| 83c1c499 | The slice documents | docs |
| cbb54b55 | Colour tokens: a blue pair, a darker amber (`design_system.html`) | **UI, on hold** |
| e34ba982 | The three-row window, View control, group box, panels, tiles, filters, list | **UI, on hold** |
| 17418181 | `position_table`: `created`, `first_seat_created`, `hired_on`, `may_see_leaving`, `may_edit_employee`; the JS check runs in CI's DOM tests | server (keys) + CI wiring |
| fb7594ce | Find | **UI, on hold** |
| a0404288 | The phone outline | **UI, on hold** |
| c702071f | `position_table`: `unseated`, `active_people` (SEC-2, PRIV-1) | server |
| 60959366 | In-no-seat and no-manager tiles and panels | **UI, on hold** |
| eeab7d78 | `reporting_mismatches` rewritten (SEC-5) | server |
| d2be0e62 | Records-chip checks | **UI, on hold** |
| adeb5b1d | Seat-link guard on Job Opening, link editable, Job Opening history (SEC-8, PRIV-3) | server |
| 336ba619 | The hire placement hook and closing a filled opening (SEC-6, 7, 9, 10); ceilings | server |

The UI commits were made step by step before the pause, so they are not one WIP commit. They are
listed above so they can be dropped or reworked together. Two server commits carry small UI-only
pieces with them: 17418181 registers `scripts/check_positions_tree.js` in `scripts/run_dom_tests.js`.

## Measured (local, own container `hrlocal-064`, site `test064`)

| What | Number |
|---|---|
| `reporting_mismatches` before the rewrite (ppj.localhost, 403 people) | 1,458 statements, 1.4 s |
| `reporting_mismatches` after | 2 statements at about 10 and about 200 assignments; 8 ms at 200 |
| `position_table` after, HR reader | 8 statements at 20 people and at 200 |
| `position_table` payload (ppj, before) | 134 KB raw, 10.6 KB gzipped |

## Tests run (modules only - the full suite is deferred)

- `alvoraa_portal.tests.test_positions_064`: 19 OK
- `alvoraa_portal.tests.test_hiring_064`: 26 OK
- `test_portal_security_010` SEC-16 ceiling test: OK
- `node scripts/check_positions_tree.js`: 148 checks OK (UI, on hold)
- Each guard was broken on purpose and its test failed: the unseated scope and the non-HR gate,
  the records-check scope, the seat-link guard (4 fail), the savepoint rollback, the muted
  messages, a second `ignore_permissions`.
- Bench check B-1 (savepoint inside Employee `after_insert`): proven by the test above.
- Bench check B-2 (`read_only` on the server): an HR User could set the link before SEC-8; the
  guard now refuses it (test). Production's Frappe v16.35.0 was not read.
- Pre-existing, not 064's: `test_register_194.test_dtc_shaped_rows_let_the_owners_in_and_keep_hr_out`
  errors on a fresh `test064` with or without this slice's changes.

## Decisions taken while building

- **E-1:** only openings linked to a seat are closed when filled (Surbhi).
- **Room on the joining date.** SEC-6 says "room on the joining date and today"; AC-66 says a seat
  full today but free by the joining date IS filled. Built as AC-66, with today also checked when
  the joining date is already past. The assignment's own over-fill rule counts today only, and a
  future-dated assignment is not in today's count, so nothing over-fills.
- **The reason sentence names the opening only, not the applicant** (a change from AC-64 and
  PRIV-3). Frappe HR names a Job Applicant by its email address, so "(applicant {id})" would have
  written an email onto the seat record and the Error Log. The Employee already links the applicant.
- **"Who can see the complete hierarchy in Positions" needs no code and no setting.** Positions
  already follows Frappe's User Permissions: a reader with no Branch permission that applies to
  Employee sees every branch of their companies. Removing (or re-scoping) Vaneet's Branch permission
  is the whole change - Surbhi's production step. Lifting the branch limit for the full-reach roles
  instead was rejected: HR User is in those roles by default, so every store's HR person would
  suddenly see every store, against slice 030's rule and SEC-1.
- **Records check:** "the holder of the seat above" is its current Permanent holders, not
  `is_primary` (which in practice means "added last"). Same answer at DTC.

## Release note (for whoever releases 064)

1. **064 reaches `main` only after 061.**
2. **At DTC, at release, add one permission row** (Desk, Role Permissions Manager, Alvoraa
   Position): **HR Manager - Read** (and Write if HR should change seats). Without it DTC's six HR
   Managers cannot open Positions once 061 is live. This is configuration, not code; 064 changes
   no permission (SEC-11).
3. To let Vaneet (or anyone) see the complete hierarchy: remove their Branch User Permission, or
   set its "Applicable For" to a doctype other than Employee. Production data step, Surbhi's.
4. The migrate makes Job Opening's Position field editable and turns on Job Opening's change
   history (one Property Setter). Rollback: set the field back to read-only; delete the Property
   Setter `Job Opening-main-track_changes`.

## Known gaps

- **On hold, by decision:** all chart UI (window, View control, group box, panels, Find, tiles,
  filters, phone outline, colour tokens, people panels, records chips).
- **Temporary debt:** AC-66 cases (3) no joining date and (8) already holds a seat cannot be built
  as tests - ERPNext requires a joining date, and a brand-new Employee holds no seat. Both are
  guarded in code.
- **Acceptable simplification:** a placement does not follow a joining date changed later (OD-7).
- **Not run:** the full suite, the browser check, the contrast check on a rendered page.
