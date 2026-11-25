---
slice: 088c (the notice lists every manual punch change, with a reason code)
author: hrms-fullstack-engineer
date: 2026-11-25
worktree: /Users/mac/hr-app/.claude/worktrees/088-notice-scope, branch docs/088-notice-scope-analysis
built on: origin/main 7ebc5898 (not on the release branch; see "Base")
status: built and tested locally. NOT pushed.
---

# 088c implementation notes

## Needs sign-off before the switch is ticked anywhere
**The reason list is a draft and is not legal's.** It is the `reason_code` options in `alvoraa_punch_change.json` (7 codes). The employer and counsel must approve it before any tenant ticks `alvoraa_print_change_notices`. It is not a code blocker.

## Base
Built on `origin/main` 7ebc5898, not on `release/088-alv436`. Reason: the 5 commits that branch carries are not authorised for a push, and 4 of them (the page-count fix) cherry-pick onto this branch with no conflict (tried in a throwaway worktree). So they can go first or after, in either order. **Main still cannot record a two-page notice**; that fix is separate.

## What was built (rung per item)
| File | What | Rung |
|---|---|---|
| `alvoraa_portal/punch_change.py` (new) | `require_reason` (validate), `write_log` (on_update), `refuse_delete` (on_trash), `after_migrate` | new code |
| `alvoraa_punch_change/` DocType (new, 3 files) | append-only log; Select of reason codes; refuses create/edit/delete by hand | new DocType (approved, Q4) |
| Custom Field `alvoraa_change_reason` on Employee Checkin | where the person picks the reason; always blank once saved; options read from the log DocType | customisation |
| `hooks.py` | Employee Checkin: validate +1, on_update +1, on_trash string became a list; after_migrate in both lists; query-condition and has_permission for the log | existing, hot file |
| `register_notice.py` | `qualifying_changes` now = `_request_changes` + `_punch_changes`; Administrator no longer skipped; `_content_hash`, `sheet_rows`, `_latest_notices`, `_write_the_notice`, `record`/`_filed_by`, `_write_the_answer`; new `punch_change_query_conditions`; switch description | existing |
| notice child DocType | `punch_change` Link added; `request` no longer required | existing, ours |
| `en.csv` | brand row for the new DocType | existing |

Not changed: the JS (the screen draws `what` and `why` from the server), `punch_fix.py`, anything in hrms/erpnext.

## Decisions applied (Surbhi, 25 Nov)
Q1 punches only: nothing for Attendance rows, no hook left for it. Q4 option B: done. Q5: a person cannot delete a punch while the switch is on. Q2 Administrator counts (shown as "HR" on paper, the real login in the log). Q6 notice only, no pay hold (`blocks_pay` False, no `pay_line`). Q7 a late edit is listed on the earlier month (by the punch's day). Q8 changes made while the switch is off are never logged: accepted. Q10 retention: no purge built; the log keeps `day` and `changed_on` so the date can be worked out; **a dated ticket for the expiry job is still to be raised** (5 years maximum). Q11 first release covers P1 to P7; undo (P10) left out. Reason codes start at switch-on, October untouched, no migration, nothing reads Version.
**Building changed none of my recommendations.**

## Tests, and what each break gave
Every test below was broken on purpose and restored. "Error" means the break made the test raise inside the step; for B1 to B5 that error is the rule's own refusal ("Pick a reason for this change"), which is the exact thing the guard rail forbids. "Wrong value" means an assertion failed on a value.

| Break | Test | Result |
|---|---|---|
| B1 machine exemption removed | machine punch filed and not logged | Error: refused with "Pick a reason" |
| B2 Guest exemption removed | phone punch | Error: same refusal |
| B3 own-user exemption removed | web check-in and own edit | Error: same refusal |
| B4 punch-fix flag exemption removed | approved 087 fix not logged twice | Error: same refusal |
| B5 switch check removed | switch off: nothing demanded | Error: same refusal |
| B6 reason not blanked | edit needs a fresh reason | Wrong value: `ValidationError not raised` |
| B7 kind always "Changed" | add with a reason, one record | Wrong value: `('Changed', ...) != ('Added', ...)` |
| B8 Administrator skipped again | Administrator-filed change is listed | Wrong value: `0 != 1` |
| B9 delete refusal removed | person cannot delete | Wrong value: `ValidationError not raised` |
| B10 month filter dropped | late edit on that month only | Wrong value: the row list was not empty for this month |
| B11 filer check blind to punch changes | filer cannot record own | Wrong value: `PermissionError not raised` |
| B12 signed row stays open | signing covers it | Wrong value: `'filer' != 'done'` |
| B13 scope removed | record scoped like the notice | Wrong value: `'' != "`tabAlvoraa Punch Change`.employee in (...)"` |
| B14 log not append-only | cannot create, edit or delete by hand | Wrong value: `PermissionError not raised` |
| reason demand removed | sync API closed to a person | Wrong value: got the log's own `MandatoryError`, not "Pick a reason" |
| commit removed from the 088 suite's switch restore | switch stays 0 after the suite | Wrong value: switch left at 1 |

Two weak tests found and fixed by breaking: the sync-API refusal first passed for the wrong reason (a duplicate-timestamp error, then the log's mandatory field), so the refusal tests now name "Pick a reason" or "cannot be deleted".

**A real fault found by running the neighbours:** the 088 suite left the notice switch at 1 in the database (its `log_view` commits mid-test). Before 088c that was harmless. Now it made the 087 suite fail on its first punch (about 28 errors in a row). Fixed in the 088 suite's cleanup (commit). **Any CI run order that puts a punch-filing suite after the 088 suite would have gone red.**

## Suites run (own stack, `test_site`, one at a time)
| Suite | Result |
|---|---|
| `test_punch_change_088c` (new) | 23 of 23 pass |
| `test_register_notice_088` | 80 of 80 pass |
| `test_punch_fix_087` | 134 pass |
| `test_held_team_086` | 33 pass |
| `test_alv302_sync_punch` | 62 pass |
| `test_held_p1_machine_accounts_085` | 3 pass |
| `test_punch_dedupe_alv337` | 26 pass |
| `test_checkin_security_014` | 14 pass (unchanged by me) |
| `test_field_checkin_fixes_013` | 16 pass |
| `test_held_day_085` | 39 pass, **6 fail**: all six need `scripts/alv392_held_backfill_grace.py` at `/home/frappe/frappe-bench/scripts/`, which my stack does not mount (assertion "the backfill script is not at ..."). Environmental, not caused by this change (proven for the one I opened; the other five are the same group by name: backfill, undo, other-site; not opened) |
| `test_portal_security_010` | 45 + 5 pass |
| `test_branch_geofence_alv338` | 23 pass |
| `test_attendance_doors_085` | 16 pass |
| `test_checkin_state_from_order` | 10 pass |
| `test_held_slip_085` | 1 + 7 pass |

Also run: `scripts/check_app_integrity.py` (OK, 1048 checks) and `scripts/check_brand_spelling.py` (OK). Not run: the DOM test `portal_register_notice_088_test.js` (no JS changed), the full app suite.

## NFRs, against the code
- Performance: neutral off. Off, the handler costs one cached Employee read plus the cached switch read per punch (measured with a warm cache: 0 database queries for a machine punch, and 0 for the phone's Guest punch). On, a machine punch costs 2 queries (`files_as_machine`), Guest still 0. Notice adds 2 queries per list (log rows, covering notices) plus one per signed-check parent: **N+1 on `outcome` lookup in `_punch_changes`** (one `get_value` per covering notice row). Bounded by changes per person per month; temporary debt, fix by one grouped query if a month shows more than a handful.
- Security: improves. Server-side `validate`; the log refuses hand edits; scope reuses the notice's.
- Reliability: a refusal on a person's save is the only new failure. Machines, Guest and own edits return before any write.
- Data integrity: the log row and the punch save in one transaction; `punch` is text so a row outlives a delete.
- Privacy: log holds two punch times in a sentence, a user and a code; no free text; log lines carry document names only. Retention not yet enforced (ticket).

## Known gaps
- **Intentional trade-off:** paths with no hook (P13 `alv291`, P14 raw SQL) leave no row. If `alv291` is ever run again after switch-on, its skip-flag changes will not be on a notice.
- **Not tested:** Data Import (P6) and the REST insert; both use the same `validate` hook but I did not drive them. Query count not measured. A real two-person (HR then employee) print on paper not looked at.
- **Temporary debt:** the N+1 above; no expiry job.
- **Corrected 25 Nov (review 05c, P1-1).** This section used to say an after-midnight punch is logged on its calendar day and that this "only matters on the last night of a month". That was wrong: it was wrong on every night-shift punch, and put a month-end night on the next month's notice. The log now uses the working day, `payroll_rules_apply.shift_day` (the date `shift_start` fell on, ALV-402), the same rule the engine and reports use.


## Review fixes (25 Nov, after reviews 05c and 06c)
The numbers match the coordinator's fix list.

1. **Working day.** `write_log` stores `getdate(shift_day(doc))`. Tests: a 00:30 punch on a 20:30 night shift prints on the evening before; the last night of a month is on that month's notice and not the next; a daytime punch is unchanged (control).
2. **Move between people: refused** while the switch is on (either person's company). `employee` is no longer a "material" field; the move is its own refusal.
3. **Paper volume:** recorded as Surbhi's decision in `00b` section 11. Nothing built.
4. and 5. **`before_validate`, and the shift tag.** *The choice I made, so the two do not cancel out:* the demand moved from `validate` to `before_validate` (it runs even with `ignore_validate`, as `guard_shift_type_change` already does). `shift` and `shift_start` are material, **compared against the saved copy**, so an edit or a retag that changes them needs a reason. On an INSERT the shift tag is not set yet at `before_validate` (Frappe HR's own `validate` sets it), so an insert is judged on being new and its day is worked out later in `write_log` from the saved punch. Cost: "Pick a reason" now comes before the geofence message; and the Desk list action "Fetch Shift" (`bulk_fetch_shift`, it saves with `ignore_validate`) is refused for a person while the switch is on, because a re-tag needs a reason and that action has no way to ask for one. `get_doc_before_save()` still gives what is needed in `before_validate` (proven by the tests).
6. **Import free text.** `_valid_reason` checks the reason against the log's own options in `require_reason` and again in `write_log`. Tested with `frappe.flags.in_import` set, after a control proving Frappe then accepts a bad Select value. **A real Data Import file was not driven.**
7. **Scope tests** now read as each persona (see below) instead of comparing two SQL strings.
8. **Refusals are written down:** `require_reason`, the move and delete refusals and the list check call `access.log_refusal` (rules `088c-reason`, `088c-reason-list`, `088c-move`, `088c-delete`) and then raise an ordinary validation message, so the person can act on it. Pinned by a test that reads the security log.
9. **Migrate exemption removed** from the log's `on_trash` (and from `validate`: nothing used either).
10. **Deleted:** `company` (written, read by nothing), `kind` (I chose to drop it: `what` already says "added", and nothing read it), the duplicate `employee` index (the composite `(employee, day)` stays), the duplicated `FLAG` literal in the controller (it imports the module's).
11. **Ceilings:** `punch_change.py` 1, `register_notice.py` 14 added to `test_portal_security_010`.
12. **Pair run:** see the report.
13. **Wording:** "every path through Frappe's document layer except where a script skips it". The fixture login now holds only `Biometric Sync` by default; one guard-rail test keeps the realistic sync-plus-HR-role shape on purpose.
14. **Tamper-evident, not tamper-proof:** written into the DocType description and `00b`.
15. **Two unlogged repair paths** noted for the runbook in `00b`.
16. **Two-page test** driven by six direct changes: prints two sheets, `page_count` 2, recording needs two photos. **Not fixed here:** the HR list row on this branch still carries no `pages` key (main's blocker, the 4 commits are Surbhi's push to authorise), so the screen still cannot ask for two photos; the server accepts them.

Not done (not on the list): review P3-7 (`_moved` compares uncast strings, a REST or import edit could print a false sentence), P3-10 (log rows for a company that unticks the switch), P3-11.
