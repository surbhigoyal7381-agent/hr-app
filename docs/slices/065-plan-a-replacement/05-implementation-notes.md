# 065 · Implementation notes: server side (22 Oct 2026)

**The server side is built and committed on `slice/065-plan-a-replacement`, local only.**
Nothing is pushed, nothing touched a server. The screens are not started: they wait for
Surbhi's sign-off on the Positions chart and the 065 prototype v3.

Branch: cut from `slice/064-organogram`, then rebased (new commits only) onto `origin/dev`
`747a4293`, which carries 063 (leave) and 064 (Positions v11). What came in: 064's screen and
docs commits (v10, v11, notes, demo guide) and 063's leave work. The only overlap with 065's
files was `test_portal_security_010.py` CEILINGS (063 raised `hr_api.py` to 70 and added
`leave_rules.py` at 0); both rows are still there after the rebase.

**Plan change (Surbhi, after this build):** the Positions chart goes back to the old hierarchy
design with the new dialogs and trays. 065's server side does not depend on the chart's
drawing; its screens will be redone on the old design later.

## What was built, file by file

| File | What | Rung, and why not cheaper |
|---|---|---|
| `doctype/replacement_plan/` (new) | 3 fields: `assignment` (**Data**, unique, set once), `confirmed_on`, `note` (set once). Hash name; change history, views, seen, import, rename off. Shipped rights: HR Manager RWCD, System Manager R. Controller: `no_feed_on_delete`, rules in `validate`, `on_trash` refuses any delete except the erase | New DocType - nothing in Frappe HR holds a private note on a seat; a field on the assignment keeps Version history for ever |
| `plans.py` (new) | The gate (`is_reader`, `_condition`, the two permission hooks), side-door and careless-grant refusals, `set_plan` / `confirm_plan` / `remove_plan` (POST only), `erase`, `_due`, the daily `erase_due_plans`, `self_check`, `erase_all_plans`, `table_view` | New code in our own app |
| `register.py` | `position_table`: one call into `plans.py`; `opening` empty on a full seat for non-readers; `AUDITED` gains the doctype | Extend the existing endpoint |
| `hooks.py` | Permission pair (2 lines), `validate` on Comment / ToDo / DocShare / Tag Link / File, `validate` on Custom DocPerm, one `daily` line. All appended | Hooks, the cheapest Frappe extension point |
| `test_portal_security_010.py` | CEILINGS: `plans.py` 0, the controller 0 | - |
| `test_replacement_plan_065.py` (new) | 49 tests | - |
| `scripts/check_positions_tree.js` | 064's "no plan anywhere" check renamed and proved to be the non-reader case (not deleted) | - |
| `DEPLOYMENT_RUNBOOK.md` | §5.12: erase after any restore; rollback order (erase all, then roll back, then stop the daily job); release check. §7 step 5 points to it | - |

## Stories and ACs (server side)

| Story | ACs proved here | Not here |
|---|---|---|
| US-1 record | AC-1 (Data, not Link - Surbhi Q1), AC-2, AC-4 | - |
| US-2 set | AC-6 (server), AC-7 (server), AC-9, AC-10, AC-11 | AC-5, AC-8, AC-74: screens |
| US-3 block | AC-12, AC-13 (the reply's `set_by` / `confirmed_by` text) | AC-14..17: screens |
| US-4 confirm | AC-18, AC-20 | AC-19: screen |
| US-5 remove | AC-23 (13 places), AC-24, AC-26 | AC-21, 22, 25: screens |
| US-9 request (server half) | AC-41 (opening carries nothing) | AC-38..40, 42..45: screens |
| US-10 lapse | AC-46, 47, 48, 50 | - |
| US-11 log lines | AC-51 (shape and content) | **see bad news 1** |
| US-12 gate | AC-52, 53, 54, 55, 56 | - |
| US-13 reply | AC-57, 58, 59 | AC-60, 61: browser checks with the screens |
| US-14 side doors | AC-62 (+ tags and files) | - |
| US-15 grants | AC-63 | - |
| US-16 subject | AC-64, 65 | - |
| US-17 read only | AC-66 | AC-44: screen |
| US-18 one place | AC-67, 68 | - |
| US-19 job | AC-49 (and B-4 below) | AC-69: release note |
| US-21 restore | AC-71 (`erase_all_plans`; runbook) | - |
| US-20, US-22 | release steps | wait for Surbhi's word |

## Bad news, and choices made

1. **Security-log lines are not written on a production server - mine or anyone's.**
   Surbhi (23 Oct): fix it as its own small change, not in 065. Ticket text below. **Until it
   lands, 065's PRIV-4 lines are dropped on dev and production, as every other security line
   is**; they use the same `frappe.logger("security").warning(...)` call as the rest, so the
   fix will cover them with no change in 065.
   `frappe.logger()` sets level ERROR unless the process is the development server
   (`frappe/utils/logger.py:12`). Every `.warning(...)` security line in the product
   (`access.log_refusal` SEC-17, `settings._log_access_change` SEC-18, and 065's PRIV-4
   lines) is dropped there. Found in bench check B-4: the real worker erased the plan, and
   `logs/security.log` stayed empty. AC-51's test captures the logger, so it proves the
   line's shape, not that it reaches the file. **Not fixed here - it changes logging for the
   whole product and needs a decision** (options: `logging` level in site config, or write
   security lines at a level that always passes).
2. **AC-52, System Manager (Surbhi, 23 Oct: yes, every company):** the spec says company A only; the System Manager is the CXO
   and `permitted_companies` gives every company. 01c's rule is "within `_scope()`". Built
   and tested as every company.
3. **New permission rows (Surbhi, 23 Oct: yes):** Frappe ticks print, email, export, share and report on every new
   Custom DocPerm row. For plans they are **unticked** on a new row (refusing would block the
   owners' Read for ever); ticking one on an existing row is refused.
4. **Assigning is refused twice over:** the ToDo hook refuses it, and the gate refuses "share",
   which "Assign to" needs. AC-23's test seeds both as Administrator.
5. **Statement count:** the estimate was +4 to +6; measured +5 with no plans and +7 with plans.
   Flat in people and plans, so inside the budget. Wall-clock time not measured (rule 5).
6. **Error Log titles** are fixed sentences; messages hold a plan's random name or counts.
   `frappe.log_error` also calls Sentry's `capture_exception`; Sentry is not configured at DTC.

## Bench checks (own container `hrlocal-065`, site `test065`; never production)

| # | Check | Result |
|---|---|---|
| B-1 | comment (@mention), assign, share, tag, file on a plan; follow | All refused, 0 rows anywhere, follow returns False (AC-62) |
| B-2 | ordinary delete vs the erase | Ordinary delete refused; with the refusal bypassed, a non-permanent delete leaves 1 Deleted Document row (the test can fail); the erase leaves 0 |
| B-3 | 13 places after remove, background job switched off | All 13 at 0 |
| B-4 | the scheduler's user | Real worker ran `erase_due_plans`: `user='Administrator'`, Scheduled Job Log Complete, plan gone, no Deleted Document, no Error Log |
| B-5 | `linked_with.get` as the subject | No plan in the answer (Data field) |
| B-6 | Comment `validate` fires on `add_comment`'s insert | Yes (B-1) |
| B-7 | one savepoint per plan on MariaDB | One forced failure: the other 4 due plans erased; one Error Log, `Plan <name>` only |
| B-8 | statements and bytes | Below |

**Every guard was broken once on purpose:** gate returning "" → 5 failures; side-door hook
off → 1; erase without `delete_dynamic_links` → 1; full-seat opening sent to everyone → 1.
Each restored and green.

### B-8: `position_table`, 90 seats, synthetic people in a rolled-back transaction

| Reader | 064 (no 065) | 065, no plans | 065, 50 plans | Bytes 1,002 people: 064 → 065 with 50 plans |
|---|---|---|---|---|
| HR Manager | 6 | 11 | 13 | 195,190 → 205,634 |
| System Manager | 8 | 14 | 16 | 219,909 → 231,054 |
| Store head (non-reader) | 7 | 7 | 7 | 186,445 → 186,445 (identical) |

Same counts at 150 and at 1,002 people. Store head's reply is byte for byte the 064 reply.

## Tests run

- `test_replacement_plan_065`: 49 tests, OK (each class run as it was written; full file in
  the one full run below).
- `test_positions_064` 17 OK, `test_register_fill_194` 62 OK (2 skipped) after step 6.
- `test_register_194`: 38 run, 1 error - `test_dtc_shaped_rows_let_the_owners_in_and_keep_hr_out`,
  pre-existing (fails the same with 064's own `hooks.py` and `register.py`; 064's notes list
  it too).
- `node scripts/check_positions_tree.js`: 123 checks.
- `scripts/check_app_integrity.py`: OK before every commit.
- **One full run, on the rebased code (own site `test065`, user-creation throttle lifted to
  1000 as CI does).** Docker stopped once during batch 3; the 51 modules that had not run
  were then run one at a time, so every module ran once on this code.

  | Part | Result |
  |---|---|
  | `alvoraa_goals` | 18 OK |
  | `alvoraa_portal` batch 1 | 16 OK |
  | `alvoraa_portal` batch 2 | 952 run: 3 errors, 1 failure (below) |
  | `alvoraa_portal` batch 3 | the modules that ran before the stop: 0 failures; the other 51 run one by one: 49 OK, 2 with one error each (below) |
  | `hrms.alvoraa_org_structure` (7 modules, earlier run on the same 065 code) | all OK except the pre-existing `test_register_194...dtc_shaped...` |
  | `test_replacement_plan_065` | 49 OK |

  The five non-OK results, and whose they are:

  | Test | Cause | 065? |
  |---|---|---|
  | `test_leave_year` x3 | This site carries ERPNext's `_Test Fiscal Year 2025`; the test's year overlaps it. 064's run saw the same 3 | No |
  | `test_shift_types_043.test_my_own_default_shift_is_always_offered` | Fails alone too, and fails the same with origin/dev's own `hooks.py` and `register.py` (065 switched off). Not one of the leave engineer's named failures as far as I can tell; possibly one of the 3 unnamed | No |
  | `test_hiring_064` x1 | `tabError Log is marked as crashed` - the Docker stop damaged that (non-InnoDB) table in my own test database. Repaired with `REPAIR TABLE` on my database only; the module then passed | No |
  | `test_leave_063_card_cancel` x1 | Failed once in the run (`Document.discard` permission); passes on rerun with 065's code and with origin/dev's - order-dependent | No |

## What waits for the screens

Commits 9-10 of the plan: flag, red edge, planned-first order, Show options, the line under
Filters, hide, print, the plan block and three dialogs, "Request a replacement" with the
warning, phone buttons; AC-5, 8, 14-17, 19, 21, 22, 25, 27-40, 42-45, 60, 61, 73, 74; the
Surbhi wording ("Only HR, owners and the system administrator see this"; "Backups expire
after 14 days. A replacement plan that has been erased from the system can still sit in a
backup until that backup expires.") - that text lives on the screens, so it is not in the
server code yet.

## Known gaps

| Gap | Label |
|---|---|
| Security-log lines dropped outside the dev server (bad news 1) | **dangerous debt for the whole product** - escalated, not fixed here |
| Release check counts a plan due because of a status change (left company without a relieving date, closed seat, deleted assignment) only through the job's own strict check, not the 2-day release check | acceptable simplification - the daily job's strict self-check counts every one |
| `register.py` still holds one occurrence-test exception (the doctype name in `AUDITED`) | intentional trade-off - allowed by SEC-7 |
| Findings N-1 (linked documents hidden count on other guarded doctypes) and N-2 (`add_tag` has no permission check) | separate tickets, not fixed here |

## Subtract pass

Removed: the second `is_reader()` call in `table_view` (saved one statement); a refusal of
print/export ticks on new permission rows (replaced by unticking - it would have blocked the
owners' row); a planned `BACKUP_DAYS` constant (only the screens use the number). Nothing else
found to delete.

## Ticket text: security-log lines are dropped outside the development server

**Summary:** Security-log lines are never written on dev or production.

**What happens:** `frappe.logger()` sets the logger level to ERROR unless the process is
Frappe's development server (`frappe/utils/logger.py:12`, `default_log_level`). Our security
lines are written with `.warning(...)`, so on gunicorn and the workers they are dropped:
`access.log_refusal` (SEC-17, every refusal), `settings._log_access_change` (SEC-18, every
access setting change), and slice 065's replacement-plan lines (PRIV-4). `logs/security.log`
stays empty. Seen on 22 Oct 2026 in slice 065's bench check B-4: a real worker erased a plan,
and no line was written.

**Why it matters:** the product's answer to "who was refused, who changed access, who erased
what" (and the CERT-In log duty) rests on these lines. Today there are none.

**Smallest fix to decide:** either raise the `security` logger alone to WARNING where it is
built (Frappe's own `frappe.utils.logger.set_log_level` exists, but it changes every logger in
the process), or write security lines at a level that always passes. Then a test that writes one line through a
logger built the way production builds it and finds it in the file.

**Not in this ticket:** what the lines contain (already ids only).
