---
slice: 088c (the notice covers every manual punch change, with a reason code)
artifact: 06c-security-review
author: hrms-security-privacy-engineer
date: 2026-11-25
status: recommendations only. Surbhi decides; I approve nothing.
scope: worktree /Users/mac/hr-app/.claude/worktrees/088-notice-scope, branch
       docs/088-notice-scope-analysis, HEAD 3d4591d4, 5 commits on origin/main 7ebc5898.
       Diff read in full: 12 files, +1,154 / -26.
verifies: the SEC-n and PRIV-n list in 06-security-review.md of slice 088
       (that file lives on branch release/088-alv436, not on main - see note below)
---

# 088c · Security and privacy verification

## 0 · Housekeeping, first

**The earlier review is not on this branch.** `06-security-review.md` exists only on
`release/088-alv436` (checked: `git cat-file -e` over every local and remote branch; 2
hits, both that branch). I read it from there. So the requirement list I am marking is
not visible to anyone working from `main` or from this worktree. One cherry-pick fixes
that; until then the list this slice must satisfy is invisible where the slice is built.

**What I did.** Read the whole diff; read `punch_change.py`, the new DocType's `.json`
and `.py`, the `register_notice.py` diff and its neighbours, `hooks.py` (both apps),
`access.py`, `employee_checkin.json`, `punch_dedupe.py`, `portal.js`'s employee card, and
the new test file. Read installed Frappe read-only in container `alv436rel-bench`
(`permissions.py`, `model/delete_doc.py`, `model/base_document.py`,
`core/doctype/data_import/*`, `company.json`).

**What I did not do.** I ran no tests, no site queries and nothing against production. I
did not re-verify `.claude/context/security-compliance-baseline.md`, which is still dated
24 Aug 2026 and therefore 93 days old - the earlier review's P3-6 stands unchanged and is
mine.

**I am relying, without re-deriving, on the caller's read-only measurement of 25 Nov:**
the switch `alvoraa_print_change_notices` is off on every company across all six
production sites, and `tabAlvoraa Register Notice` holds zero rows anywhere. Everything
below about live exposure rests on that. **Nothing in 088c does anything while the switch
is off** - proven in code: `punch_change._is_a_persons_change` returns False when
`notices_are_on(company)` is False (`punch_change.py:63-64`), and all three handlers go
through it (`:90`, `:103` via the stash, `:127`).

## 1 · Verdict in one line

**No P0. One P1 for the release-to-main question (the two-page notice, below), and five
items that must be closed or accepted in writing before any tenant ticks the switch.**
The core of the slice - a reason demanded at the point of entry, copied into a row no
browser and no Desk user can create, edit or delete - is sound, and it closes most of the
gap the earlier review recorded as R10. What it does not close is the set of paths that
write a punch without going through a document save, plus two field-level gaps that
matter in this product's own history.

## 2 · Requirement verification

Every reference is `file:line` in this worktree unless it says *installed Frappe*.
Verdicts: **MET** / **PARTIAL** / **NOT MET** / **NOT CHECKED**. "Unchanged" means 088c
does not touch the mechanism and I re-read it only far enough to confirm that.

| Req | Verdict now | Evidence, and what 088c changed | Label |
|---|---|---|---|
| **SEC-1** one scope rule on every reader and writer | **MET** | New reader, scoped the same way: `permission_query_conditions` for `Alvoraa Punch Change` → `punch_change_query_conditions` → `_scope_sql` (`hooks.py:669`, `register_notice.py:955-957`, `:913-940`), plus `has_permission` → `notice_has_permission`, which fails closed with no `employee` (`hooks.py:696`, `:948-952`). Role rows grant **read only**, to exactly three roles: HR Manager, HR User, System Manager (`alvoraa_punch_change.json:110-123`). **Unscoped siblings: I grepped every reference to the log outside its own folder and tests - 7 in `hooks.py` (registrations), 8 in `register_notice.py`. The only reader is `_punch_changes` (`:256-262`, `ignore_permissions=True`) and its `employees` argument is already narrowed to the caller's scope at `:205-207` before it is called.** | Proven in code. **Not run** - the scope test exists (`test_punch_change_088c.py:282-286`) but I did not execute it |
| **SEC-2** content leaves only through one logged call | **MET** | The HR list still carries no reason: `_punch_changes` adds `reason_code` and `what` only when `with_content` is true (`:277-279`), and `list_people` calls it without (`:365`). The notice row is still inserted before anything returns (`:635` then `:655`). | Proven in code. The named failure-injection test still does not exist (earlier P3-1) |
| **SEC-3** a signature covers exactly what was printed | **MET, but by immutability alone** | A hash is stored for punch rows over `name, from_date, reason_code, what` (`:533-536`), and a change made after the print shows as `changed_after_print` because the new row's name is not in `covered` (`:325-328`; test `:253-257`). **But `_write_the_answer` skips punch rows before `_still_the_same` is ever called (`:853-854`), so for a punch row the stored hash is written and never compared.** The control is therefore 100% the append-only property - see finding **F2**. | Proven in code |
| **SEC-4** nobody records a confirmation they have an interest in | **MET** | `_filed_by` reads `changed_by` from the log row, from the database, for punch rows (`:835-841`), and `record` refuses when any covered row is the caller's (`:812-817`). `i_filed` uses the same value (`_punch_changes` sets `owner=changed_by`, `:272`). Test `:236-251`. | Proven in code |
| **SEC-5** the confirmation fields are written by the record call only | **MET** | Nothing is written onto the punch for a punch row (`:853-854`). The notice's own `validate` and `on_trash` are unchanged (`alvoraa_register_notice.py:45-95`). One soft spot: the child row's "exactly one of Request and Punch Change is set" is a **description, not a check** (`alvoraa_register_notice_change.json:19-20`); nothing enforces it. Harmless today because only the server writes the notice. | Proven in code |
| **SEC-6** the photo reuses 081's checks | **MET (unchanged)** | Not touched by this diff. | Unchanged |
| **SEC-7** a reused photo refused; the dialog shows who it is | **PARTIAL (unchanged)** | Not touched. Earlier P3-2 stands. | Unchanged |
| **SEC-8** only HR in scope can open the photo | **PARTIAL (unchanged)** | Not touched. Earlier P2-3 stands. | Unchanged |
| **SEC-9** free text is shown as text, never as markup | **MET for rendering; the "no free text" premise breaks under one path** | The reason prints through `gpEsc` on the employee card (`portal.js:7787`) and the reason itself is a Select on both the punch and the log, so ordinary paths cannot carry markup at all. **Under a Data Import that guarantee is gone** - see finding **F3**. Rendering is still escaped, so this is a record-integrity problem, not an XSS one. | Proven in code; the import path proven in installed Frappe source, not run |
| **SEC-10** the photo access log is scoped | **MET (unchanged)** | Not touched. Earlier P2-2 (joiner rows invisible to HR Manager) stands and is still waiting on Surbhi. | Unchanged |
| **SEC-11** POST-only, with the CSRF token | **MET** | 088c adds **no endpoint**: `grep "@frappe.whitelist" punch_change.py` → 0. No new website page, no `allow_guest`. The new work hangs off document hooks only (`hooks.py:303`, `:306`, `:310`). | Proven in code |
| **PRIV-1** collect nothing new except the photo | **PARTIAL - newly in scope, and now deliberately widened** | 088c collects new personal data about an employee: a reason code, a sentence holding one or two punch times, the changer's login and the time (`alvoraa_punch_change.json:20-100`). That is counsel's 24 Nov requirement, and it is minimised - a fixed list, no free-text field anywhere, and the security log line carries ids only (`punch_change.py:122`). Two leaks remain: an unhandled exception inside `write_log` puts the local `pending` dict - reason code plus the punch times - into the Error Log, because Frappe formats tracebacks with variables (the mechanism the earlier review read in installed Frappe `utils/error.py:68`); and a Data Import keeps the uploaded CSV as an attachment on the `Data Import` record (`import_file`, installed Frappe `data_import.json:55`), reason column included. | Proven in code for the collection; the two leaks are **inference from installed Frappe source**, not demonstrated |
| **PRIV-2** what goes on paper | **MET** | A punch row prints the day, the fixed sentence, the reason code, "HR" and a date - and no name of the HR person (`:533-543`, `filed_by: None`). One employee per sheet, unchanged (`:630-660`). No colleague's data can reach the page. | Proven in code |
| **PRIV-3** the photo is handled as the most sensitive thing here | **PARTIAL (unchanged)** | Not touched. C1 (is a thumb impression biometric data?) still unanswered. | Unchanged |
| **PRIV-4** nothing deletes, and nothing is deletable by HR | **NOT MET - unchanged, and 088c did not change it** | **088c adds no `File` guard.** Across both apps there are exactly **two** `"File"` entries in a hook map, both `doc_events` → `validate` (`alvoraa_portal/hooks.py:613-615`, `hrms/hooks.py:343`), and **neither app has a `File` entry in `has_permission`** (`alvoraa_portal/hooks.py:681-700`, `hrms/hooks.py:172-185`). So the HR person who uploaded a signature photo still owns the File and still has delete on it (installed Frappe `file.py:999`, as the earlier review proved by running). **This is an open gap, not a new one.** 088c does improve the punch side: a person cannot delete a punch while the switch is on (`punch_change.py:125-130`, test `:174-186`). | Proven in code (the absence is an enumeration of 2 hits, not an empty grep) |
| **PRIV-5** the employee app shows the same facts, about them only | **MET** | `my_changes` is unchanged in shape: a month and nothing else, the person from the session (`:1002-1003`), and punch rows arrive with their reason (`:277-279`, test `:272-280`). The card renders `why` escaped and uses only `d.date` in its one button (`portal.js:7780-7793`), so the `PCH-` id never reaches another call. | Proven in code |
| **PRIV-6** the print record lives as long as what it proves | **PARTIAL** | The new log never deletes by any ordinary path (`alvoraa_punch_change.py:30-35`), which is the right default. But the 5-year **maximum** is now a decision with no mechanism, and it is in direct tension with append-only: any purge will need a deliberate exemption, and that exemption is itself the hole. See finding **F5**. | Proven in code |

**Counts: 11 SEC → 8 MET, 3 PARTIAL, 0 NOT MET. 6 PRIV → 2 MET, 3 PARTIAL, 1 NOT MET.**
Of these, 088c moved only SEC-3, SEC-9, PRIV-1, PRIV-2, PRIV-5 and PRIV-6; the rest are
the earlier review's verdicts, re-read but untouched.

### Counsel's condition and R10

R10 in the earlier review was: *the notice covers only 087-flow punch fixes, so
corrections made by editing check-ins directly produce no notice*. 088c **closes that for
every punch change made through a document save** - the portal, the Desk, the REST API, a
Data Import and `bench console` code that calls `doc.save()` all run `validate`, and
`require_reason` is on `validate` (`hooks.py:296-304`). That is the big win and it should
be said plainly.

What remains outside the notice, enumerated in §4: writes that never load a document, two
named repair scripts in this repository, three punch fields the rule does not watch, and
the person who *loses* a punch when it is moved to somebody else. Whether a notice with
those four holes is "the notice you described" is **counsel's call, not mine**, and it is
the same question C4 asked on 24 Nov - narrowed, not answered.

## 3 · The append-only claim, tested rather than taken

The claim is that nobody can create, edit or delete a row by hand, not even Administrator.
**For every path a browser or the Desk can reach, that holds, and it holds for the right
reason** - not role permissions (Administrator bypasses those: installed Frappe
`permissions.py:108-110`, `if user == "Administrator": return True`), but a controller
refusal that runs whatever the roles say (`alvoraa_punch_change.py:23-35`). The test drives
insert, save and delete as both an HR user and Administrator, with
`ignore_permissions=True`, and expects `PermissionError` each time
(`test_punch_change_088c.py:188-206`).

Now the harder question: **what else could remove or alter a row?** Enumerated from the
installed framework, not guessed.

| Path | Does it get through? | Trace |
|---|---|---|
| Desk / portal / REST delete | **No.** `frappe.client.delete` and the Desk both reach `delete_doc` without `ignore_on_trash`, so `on_trash` runs and refuses | installed Frappe `delete_doc.py:24-34` |
| Desk / REST create or edit | **No.** `validate` refuses; also no role has create or write (`alvoraa_punch_change.json:110-123`) | proven in code |
| Delete the parent punch | **Row survives.** `punch` is `Data`, not a `Link` (`alvoraa_punch_change.json:22-28`), so nothing cascades; and a person cannot delete the punch anyway while the switch is on | proven in code |
| `frappe.db.set_value` / `frappe.db.sql` / `frappe.db.delete` | **Yes, silently.** No controller, no `Version` row (the DocType sets `track_changes: 0`, `alvoraa_punch_change.json:128`), and with `update_modified=False` not even `modified` moves | installed Frappe behaviour; `track_changes` proven in code |
| `frappe.delete_doc(..., ignore_on_trash=True)` or `for_reload=True` | **Yes.** Both documented as skipping `on_trash`; `for_reload` also skips permissions and deletes permanently | installed Frappe `delete_doc.py:50-63` |
| Any patch run during `bench migrate` or `install` | **Yes.** `validate` and `on_trash` both return early when `frappe.flags.in_migrate` or `in_install` is set (`alvoraa_punch_change.py:24`, `:31`) | proven in code |
| Delete the DocType itself | **No**, on a production image. `delete_doc` throws "Standard DocType can not be deleted." unless `doc.custom`, `developer_mode`, `in_patch` or `force` | installed Frappe `delete_doc.py:127`, and `:294` for the non-Administrator case |
| `bench uninstall-app alvoraa_portal`, a restore, direct MariaDB | **Yes.** Inherent to any DocType; the same is true of the notice itself | not checked, stated as inherent |

**What that means for the evidential claim.** The log is tamper-*evident* against users and
tamper-*proof* against the web. It is **not** tamper-proof against server-side code or a
database login, and because `track_changes` is 0 and `modified` can be frozen, a quiet edit
of one `reason_code` would leave **no** trace inside the application at all. That is a
reasonable place to land for this slice - the alternative is a signed or hash-chained ledger,
which is far more than the requirement asks for - but it should be written down in the
evidence pack in those words, rather than as "append-only, nobody can change it".

The two migrate exemptions are the one thing I would narrow. `validate`'s exemption may be
needed for fixtures; **`on_trash`'s is not needed by anything in this diff** (nothing
deletes rows during a migrate), and it is what would let a future patch in any of the three
apps delete audit rows during a routine `bench migrate`. Removing four words closes it.

## 4 · Can a change escape the record while the switch is on?

Enumerated from the code. Items 1-4 are intended and tested; 5-9 are the gaps.

1. **A biometric sync account** - `files_as_machine` (`field_app_access.py:59-77`): the sync
   role and **no Employee record**. Intended, tested (`test_punch_change_088c.py:69`).
2. **Guest / no session** - the phone app's own punch (`punch_change.py:57-59`). Intended.
3. **The employee's own punch or own edit** - matched on `Employee.user_id`
   (`punch_change.py:65-66`). Intended.
4. **An approved 087 punch fix** - `frappe.flags.in_punch_fix_apply` (`:55`); already on the
   notice through its request. Intended.
5. **`frappe.db.set_value` and raw SQL.** Inherent, and the engineer says so. But it is not
   hypothetical: **two tools in this repository already use it on the material field
   `skip_auto_attendance`** - `alv291_attendance_fix.py:937, :1194, :1205` and
   `punch_dedupe.flag_existing` / `unflag_existing` (`:253`, `:273`, both `_admin()`-gated
   bench-console functions that commit). Either one, run after switch-on, changes what days
   count for hundreds of people with no reason, no log row and no notice.
6. **A patch during `bench migrate`** (`punch_change.py:55`). Same exemption as §3.
7. **The three shift fields.** `MATERIAL` is `time, log_type, employee, skip_auto_attendance`
   (`punch_change.py:45`). It does **not** include `shift`, `shift_start` or `shift_end` -
   and in this product those decide which day a punch counts to (ALV-291's whole repair is
   wrong shift tags; the midnight-punch rule turns on them). On `Employee Checkin` `shift` is
   `read_only` and `shift_start`/`shift_end` are `hidden`
   (`employee_checkin.json:60-66`, `:99-111`) - which is a **form** control only, so the REST
   API, a Data Import and server code can all set them. Changing them is a change to what the
   day counts, and it is neither refused nor logged.
8. **Moving a punch to another person.** `_is_a_persons_change` and the log row both read
   `doc.employee` *after* the edit (`punch_change.py:62`, `:111`). So the person who **gains**
   the punch gets a row and a notice line ("Punch moved to another person"), and the person
   who **loses** it gets nothing - no row, no notice - even though their day's count, and
   possibly their pay, just changed.
9. **A login holding the sync role with no Employee record.** By design that is a machine. If
   an HR person is ever given `Biometric Sync` and has no Employee record, they can add or
   change any punch with no reason and no row. I cannot check who holds that role on the live
   sites - **unknown, and it needs a read-only role count per site before switch-on.** Worth
   noting that the 088 test suite *manufactures* exactly such a login - `Biometric Sync` plus
   `HR User`, no Employee record (`test_register_notice_088.py:56-62`) - which is one more
   reason the suite must never be run against a tenant site.

**And one usability consequence that is really a control consequence.** With the switch on,
a Desk bulk edit of punches is refused one row at a time (each save demands a reason the
bulk editor cannot supply), so the only practical way to make a hundred corrections at once
is a script - which is exactly path 5, the unlogged one. A control people route around is
not a control. If DTC is going to keep doing month-end regularisations in bulk, the bulk
path needs a reason too, or the runbook has to forbid it in writing.

## 5 · The reason itself

- **Not approved.** The 7 options are the engineer's draft and the DocType says so in its own
  description field (`alvoraa_punch_change.json:76`: "DRAFT LIST. Needs sign-off..."). It is
  printed on a document meant to stand up in a wage dispute. **Employer and counsel sign-off
  blocks switch-on, not the merge.**
- **One list, two places** - the punch's Select options are read from the log's field at
  migrate time (`punch_change.py:176-179`), with a test that they match
  (`test_punch_change_088c.py:208-212`). Good; nothing can drift.
- **Free-text escape hatch: one, and it is real.** See **F3** below.
- **Where the value lives.** Blanked on the punch on every path, before any write
  (`punch_change.py:87-88`), and carried to `write_log` on the document's in-memory flags
  (`:96`). So: a refused save stores nothing anywhere (test `:137-142`); a successful save
  stores it only in the log row; `Employee Checkin` has `track_changes: 1`
  (`employee_checkin.json:288`) but the field goes null → null, so **no Version row records a
  reason**. The two unintended persistences are the Error Log traceback and the Data Import
  attachment, both named under PRIV-1.
- **Nothing commits inside the save.** I grepped every module hooked on `Employee Checkin`
  (`held_day`, `punch_dedupe`, `branch_geofence`, `punch_fix`, `field_app_checkin`): the only
  `frappe.db.commit()` calls are in `punch_dedupe`'s two console functions, which are not
  hooks. So the punch and its log row really do stand or fall together.

## 6 · Privacy of the new log

**One row holds:** the punch id, the employee, the company, the day, Added/Changed, the
reason code, a sentence with one or two punch times, the changer's login, the timestamp
(`alvoraa_punch_change.json:20-100`). No pay, no statutory id, no free text, no photo, no
location.

| Persona | What they see | How |
|---|---|---|
| **CXO / System Manager / Administrator** | **every company's rows**, reason included | `permitted_employee_filters` returns `ALL_EMPLOYEES` for Administrator and System Manager (`access.py:320-323`), and `_scope_sql` then returns `""` (`register_notice.py:920-921`). Same as the notice; established pattern, not new |
| **HR Manager / HR User** | only their companies, and only their branches when a Branch user permission exists | `_scope_sql` (`:913-940`) via the query condition and `has_permission` |
| **Employee** | their own rows only, through `my_changes`, with the reason | no Employee role row on the DocType at all (`:110-123`), so a direct `get_list` is refused before any hook runs; `my_changes` resolves the person from the session (`:1002-1003`) |
| **Line manager** | nothing | no manager surface reads this log (enumerated in SEC-1 above: the only reader is `_punch_changes`) |

**Export and report:** the role rows grant `read` and nothing else, so `report` and `export`
are 0 and the Desk offers neither. **Printed page:** one employee per sheet; a punch row
prints no HR name. **Signing flow:** `open_photo` and `record` are unchanged. **I found no
surface where an employee sees another person's row.**

## 7 · Findings, ranked by legal and privacy consequence

### F1 · P1 - a two-page notice cannot be signed on `main`, and 088c makes two pages normal
**Who is harmed and how.** HR at DTC prints November's notice for a storeman with 7 manual
punch corrections. `PER_PAGE = 5` (`register_notice.py:428`), so the notice is written with
`page_count = 2` (`:678`). `record` refuses unless it receives exactly `page_count` photos
(`:827-831`), and - the caller's verified fact, which I did not re-derive - `main` never
sends `pages` to the screen, so the second photo cannot be supplied. The worker signs paper
that the system cannot record. The evidence is the record, so there is no evidence.

Before 088c this was rare: only 087-flow requests qualified, and there were none on either
live tenant. After 088c **every** manual punch change qualifies, and DTC's own October shape
(~2,007 hand-made check-ins and 1,315 Administrator edits across ~440 people, from the
memory note) averages well over five per person per month. **The 4-commit page fix on
`release/088-alv436` must land before or with 088c, not after.** Label: **dangerous debt if
the switch is ticked without it.** Owner: Surbhi.

### F2 · P2 - three punch fields change what a day counts and are not watched
**Who is harmed and how.** HR corrects a night-shift punch by setting `shift_start` through
the REST API or a Data Import (the field is `hidden`, not `read_only`:
`employee_checkin.json:99-105`). The punch now counts on the previous day. The employee's
pay for both days changes. No reason is demanded, no row is written, the monthly notice is
silent, and the employee's own card shows nothing. This is not a hypothetical shape of error
in this product - ALV-291 exists because wrong shift tags produced wrong reds.
**Smallest fix:** add `shift`, `shift_start`, `shift_end` to `MATERIAL`
(`punch_change.py:45`). **Or** write down, in the evidence pack, that shift re-tagging is
not a notified change. Label: **temporary debt**, removed by one line plus a test.

### F3 · P2 - a Data Import can put arbitrary free text into the append-only record, for ever
**Who is harmed and how.** `Employee Checkin` has `"allow_import": 1`
(`employee_checkin.json:3`). A System Manager imports a punch sheet with the
"Reason For This Change" column filled in with free text - say *"told by the manager, do not
pay him"*. `require_reason` accepts any non-empty value (`punch_change.py:92`). The log row is
inserted inside the same import, and Frappe's Select validation **returns early when
`frappe.flags.in_import` is set** (installed Frappe `base_document.py:1101-1103`), a flag the
importer sets for the whole run (`importer.py:74`). So the string lands in `reason_code`,
prints on the employee's notice, shows on their own card - and because the row is
append-only, **nobody can ever correct it**. (Outside an import the same attempt fails: the
Select is validated and the whole save rolls back. I verified the mechanism in installed
Frappe source; I did not run an import.)
**Smallest fix:** validate `pending["reason"]` against the log's own options inside
`write_log` before inserting - the options are already read there at migrate time, so it is a
few lines and no new concept. Label: **dangerous debt** - an unchangeable sentence written by
one person about another is the worst shape this record can take.

### F4 · P2 - the person who loses a punch is never told
**Who is harmed and how.** HR realises a punch was filed against the wrong employee and edits
`employee` on the punch. Priya gains the punch, gets a log row and a notice line. Ravi loses
it, his day may drop to a missing-punch or held day, and he gets **nothing** - because both
the switch test and the log row read `doc.employee` after the edit
(`punch_change.py:62`, `:111`). **Smallest fix:** in `require_reason`, when `employee`
changed, stash the old employee too and write a second row against them. Label: **temporary
debt.** (A cheaper answer is to refuse the edit and make HR delete-and-re-add - but deletion
is refused while the switch is on, so that door is shut; worth knowing when choosing.)

### F5 · P2 - retention is a decision with no mechanism, and it fights the append-only rule
No purge exists for the new log; `on_trash` refuses deletion to everybody. The 5-year maximum
is Surbhi's decision of 25 Nov. **The gap, stated precisely:** today the rows are kept for
ever, which contradicts a stated maximum; and whatever eventually enforces the maximum must be
able to delete rows that the controller refuses to delete, so it will need an exemption flag -
and that flag is then the supported way to remove audit rows.
**Smallest correct mechanism** (not built, as instructed): one daily scheduled function that
`frappe.db.delete`s rows whose `day` is older than the period, skipping any row covered by a
notice under dispute or under legal hold, with its own dated ticket and one test that proves a
held row survives. The legal-hold question - *does a live wage dispute suspend the 5-year
clock, and who sets the hold?* - is **a question for counsel**, not mine. Label: **temporary
debt with a named tension**; it must not be "phase 2 will fix it" once a tenant is live.

### F6 · P3 - the switch can be ticked, and there is no record of who did it with their IP
Who can tick it: anyone who can write a `Company` - in practice System Manager, and HR Manager
where the tenant grants it. The field is a plain Custom Field with no permlevel
(`register_notice.py:77-86`). **What exists:** `Company` has `"track_changes": 1` (installed
Frappe/ERPNext `company.json:1117`), so a `Version` row records the user, the timestamp and
the old and new value. **What does not exist:** the IP address, and any protection of that
Version row. Counsel's recommended shield (per the earlier review's §5 and the 24 Nov answer)
asks for an immutable record of who turned a default off, **with their IP**. Frappe records IP
for logins in `Activity Log`, not for field changes - so today the two would have to be
correlated by user and time. **This is a gap in the shield, not in the code**, and it is for
Surbhi and counsel to decide whether correlation is enough. Label: **intentional simplification
if accepted in writing.**

### F7 · P3 - the two refusals this slice adds are written down nowhere
`require_reason` and `refuse_delete` use `frappe.throw` directly (`punch_change.py:93`,
`:129`) rather than `access.refuse`, so they never reach `log_refusal`. **This is not
ALV-391** - that is fixed, in the sense that `access.security_logger()` now raises the level
to INFO (`access.py:61-66`), and the earlier review proved a line landing in `security.log`.
It is simpler: these two refusals never call the logger at all. So "an HR user tried forty
times to add punches with no reason" leaves no trace anywhere. The successful case *is*
logged, with ids only (`punch_change.py:122`). The log DocType's own refusals **do** go
through `access.refuse` (`alvoraa_punch_change.py:26`, `:33`), so an attempt to tamper is
logged - for up to 2 MB of rotation, which is recent-misuse evidence and not a year-later
answer. **Smallest fix:** route both through `access.refuse` with the rule id `088c-SEC-1`
already used in the DocType. Label: **temporary debt.**

### F8 · P3 - the two new files are outside the `ignore_permissions` ceiling gate
`CEILINGS` in `test_portal_security_010.py:731` is a dict the test loops over (`:1075`), so a
file with no entry is simply not counted. `punch_change.py` has 1 `ignore_permissions` and
`register_notice.py` now has 14 (it had 12 when the earlier review raised this as P3-5).
**16 bypasses in this slice's two files are uncounted, and so is the seventeenth.** Each one
is argued in a comment and sits inside a scope check, so this is decay risk, not exposure.
Two lines in a dict that already exists. Label: **temporary debt.**

### F9 · P4 - three smaller notes
- The child row's "exactly one of Request and Punch Change" is a description, not a check
  (`alvoraa_register_notice_change.json:19-20`).
- A punch moved across a month boundary is logged on the **new** day's month
  (`punch_change.py:113`), so the month that lost a punch says nothing - the same shape as the
  accepted after-midnight simplification, and worth one sentence in the notes rather than code.
- A punch row prints `counts: None` (`register_notice.py:537`), so the paper says what changed
  but not what the day now counts. That is an information-quality call for the analyst, not a
  security finding; I mention it because the 087 rows *do* carry it, and a worker holding one
  page with two kinds of row will see the difference.

## 8 · Worries - no actor, path and result yet

1. **The reason list cannot express "I was told to".** Every option attributes the correction
   to a fact about the machine or the worker. A reason list that cannot say *"instructed by
   the branch manager"* quietly pushes real cases into "Other (details are in the HR file)" -
   and the HR file is outside this product, so the evidence trail ends there.
2. **Two HR people can still agree a reason that is not true.** 088c records *a* reason, not a
   true one. That is R1's collusion worry in a new place.
3. **Nobody has printed a real two-page notice on paper and recorded it.** Carried over from
   the earlier review's worry 3, now sharper because two pages becomes the normal case (F1).

## 9 · What must be true before any tenant ticks that switch

1. **The reason list is approved** by the employer and by counsel, and the "DRAFT LIST"
   sentence is gone from the DocType description.
2. **The two-page fix is on `main`** (F1), and somebody has printed, signed and recorded a
   real two-page notice once, end to end.
3. **F3 is closed** - the reason is validated against the options inside `write_log` - or the
   Data Import route is closed off for `Employee Checkin`.
4. **PRIV-4's File-delete gap** is fixed or accepted in writing, by name and date. It is the
   only **NOT MET** on the list and it predates this slice.
5. **F2 and F4 are fixed or written down** as changes the notice does not cover.
6. **The unlogged script paths are named and controlled** after switch-on:
   `alv291_attendance_fix.py` and `punch_dedupe.flag_existing` / `unflag_existing`. Either they
   write rows, or the runbook forbids them on a tenant whose switch is on, in writing.
7. **A read-only check per live site**, before the tick: does the switch column exist, is it 0,
   and **who holds the `Biometric Sync` role and has no Employee record** (path 9).
8. **The retention ticket exists and is dated** (F5), with counsel's answer on legal hold.
9. **The switch audit question is answered** (F6): is a `Version` row without an IP enough?
10. **The test suites are never run against a tenant site.** The 088 suite commits a `Company`
    switch change (`test_register_notice_088.py:83-85`) and creates a `Biometric Sync` login.
    The commit is correct and necessary; the blast radius if it is ever pointed at a tenant is
    a feature switching itself on.

## 10 · Residual risk - proposed. Nothing is accepted until Surbhi says so

| # | Risk | From | Label | Owner / date |
|---|---|---|---|---|
| R4 | The uploading HR person owns the signature File and can delete it | earlier P2-1, **unchanged by 088c** | dangerous debt if left unnamed | **Surbhi, before switch-on** |
| R6 | Joiner export rows invisible to HR Manager in the photo access log | earlier P2-2 | intentional trade-off if accepted | **Surbhi** |
| R9 | An in-scope HR Desk view of a photo writes no row in our own log | earlier P2-3 | temporary debt | removed when a viewer is built |
| R10 | The notice now covers punch saves, but not raw writes, not shift re-tagging, not the person who loses a punch | **narrowed by 088c; F2, F4, path 5** | **a question for counsel, not a debt** | **Surbhi + counsel** |
| R11 | The record is tamper-evident, not tamper-proof: server code or a DB login can edit or delete a row with no trace | **new, §3** | acceptable simplification **if the evidence pack says so in these words** | **Surbhi** |
| R12 | A Data Import can write permanent free text into the record | **new, F3** | dangerous debt | **engineer, before switch-on** |
| R13 | 5-year maximum has no mechanism, and the purge will need an exemption from append-only | **new, F5** | temporary debt | **dated ticket, Surbhi** |
| R14 | A thumb impression is stored as a signature is - one photo per page, no separate consent wording, 5 years - **against counsel's written view of 24 Nov that a thumb impression is biometric data under the DPDP Act**. Surbhi's decision, 25 Nov 2026. | Surbhi's decision | **accepted risk, recorded once, not reopened here** | **Surbhi, 25 Nov 2026** |
| R8 | The compliance baseline is 93 days old and the feature map is a 24 Aug draft | earlier P3-6 | temporary debt | **me, scheduled by Surbhi** |

## 11 · What I could not check, and what I would need

- **Nothing was run.** No test, no site query, no API call. Every verdict above is a code or
  installed-source read. To raise F3 from "proven in source" to "demonstrated" I would need a
  bench and about ten minutes: one Data Import of two punches with a free-text reason, then
  read the stored `reason_code`.
- **Nothing on production or dev tenants.** The switch state and the zero row count are the
  caller's measurement of 25 Nov, used as given.
- **Who holds `Biometric Sync` on each live site** - path 9. A read-only role count per site.
- **The real data shape for observability.** For these controls to be *visible* at all, a
  tenant needs: the switch on for a company, at least one punch added or edited by a person
  (not a machine, not the employee), and - for F1 - at least six in one month for one person.
  **With the switch off on every company, "zero findings" from any production check means
  nothing.** That is lesson 1 of the September list, and it applies to this whole slice.
- **The baseline** (R8). I did not re-verify DPDP or CERT-In; the two live questions it would
  touch (C1 biometric classification, C2 retention) are counsel's.
- **I am not a lawyer.** Whether the remaining holes leave the notice short of what counsel
  described on 24 Nov is counsel's judgement. The precise question to put to them is in §2
  under R10 and in F5 for legal hold.

## 12 · Subtract pass

I read this back asking only what I could delete.

**Removed:** a fresh four-line threat model (01c §2 is unchanged and 088c adds no new actor);
a performance paragraph (the engineer measured it and it is DevOps' column); a table of the
new DocType's fields repeated from the json; two P4s that were naming preferences; and a
re-description of the photo controls, which this slice does not touch - the SEC-6 to SEC-8 and
SEC-10 rows now just say "unchanged" and point at the earlier review.

**Kept deliberately:** the escape-path enumeration in §4 and the tamper table in §3, because
the whole value of this review is the difference between "append-only" as a claim and as a
measured property - and on two points (the `in_import` Select skip, the `on_trash` migrate
exemption) the claim and the framework differ.

**I added no new requirement, no new gate and no new control.** F3, F7 and F8 are a few lines
each inside mechanisms that already exist; F5 is the only new mechanism and I did not design
it beyond naming the smallest shape.
