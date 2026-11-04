---
slice: 082-joiner-to-employee
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-11-04
status: built locally. NOT pushed. Nothing on dev, nothing on main, nothing on production.
scope_built: the button and the linking step. The document move is OUT of scope.
---

# 082 · Implementation notes

## 1 · What I built, file by file

| File | Mechanism | Why that one |
|---|---|---|
| **NEW** `alvoraa_portal/alvoraa_portal/joiner_to_employee.py` (~199 lines incl. docstrings) | **build** (ladder rung 4) | Two whitelisted methods: `details_for_a_new_employee` (read-only prefill) and `link_the_employee`. A new module rather than lines in `joiner_invite.py`, so its `ignore_permissions` ceiling starts and stays at **0** and 082-SEC-3 is proven for the file rather than hidden inside another file's headroom |
| `alvoraa_portal/alvoraa_portal/joiner_housekeeping.py` — `_erase_the_redundant_copies` + new `_still_holds_its_documents` | **extend** | The guard. Six lines in the pass this slice switches on, and one fail-closed helper |
| `.../doctype/alvoraa_joiner_submission/alvoraa_joiner_submission.py` — **two docstrings only, no code** | **correct the record** | The module docstring said "no code path anywhere creates an Employee from one of these (078-SEC-12)" and `_follow_the_employee` said "no endpoint that could be called with somebody else's id". Both are now false. A docstring that lies is a lesson this repo has already paid for, so they say what is true and name 082-SEC-1/2/3/4 |
| `alvoraa_portal/alvoraa_portal/public/js/alvoraa_joiner_submission.js` | **extend** | Two buttons, one guidance line, one confirmation naming the person, one honest result line. Already registered by `doctype_js`, so **`hooks.py` is untouched** |
| **NEW** `alvoraa_portal/alvoraa_portal/tests/test_joiner_to_employee_082.py` | **build** | 32 tests |
| `alvoraa_portal/alvoraa_portal/tests/test_portal_security_010.py` | **extend** | One `CEILINGS` row: `joiner_to_employee.py` at **0** |

**Not touched, deliberately:** `hooks.py`, `patches.txt`, every DocType JSON, `portal.js`,
`hr_api.py`, every `hrms` and `erpnext` file, `nginx.conf`, every workflow,
`_delete_the_documents_sooner`. **No new DocType, no new field, no new setting, no new
scheduled job, no new dependency, no migration, no patch, no feature flag.**

## 2 · The guard on the delete — what it is and why this mechanism

**The problem the scope creates.** Setting `employee` moves the status to *Made an employee*.
That status was unreachable in the product, so `_erase_the_redundant_copies` had never fired on
a real row. It calls `erase`, which calls `delete_the_documents`, which deletes the joiner's
uploaded identity documents permanently, bytes included — and it runs **first** in `run_daily`.
Building the link switches it on. The document move that would make the deletion safe is out of
scope on Surbhi's word.

**The mechanism: a hired row that still holds its uploaded files is skipped by that pass.**

```
done = kept = 0
for name in _todo({"status": "Made an employee"}):
        if _still_holds_its_documents(name):
                kept += 1
                continue
        ...
```

`_still_holds_its_documents` counts `File` rows attached to the submission and **returns True if
the count itself raises**. That is fail-closed in the literal sense: the failure mode is *keep
the documents*. A false yes costs one row an extra erase cycle; a false no destroys a person's
identity documents for good.

**Why this and not a switch.** A named switch was the obvious alternative and I rejected it:
it is a feature flag (banned by `no-over-engineering.md` §2), and it is a thing somebody has to
remember to flip, which is how controls die. **The guard I built retires itself** — when the
move ships, a moved row has no files attached any more, so the pass resumes on its own with
nothing to remember and nothing to clear.

**What it does not do, said plainly.** It does not touch `_delete_the_documents_sooner`, the
30-day clock, because I was told not to: that is counsel's ruling 4. **So a hired joiner's
documents still go 30 days after hire**, on the clock they were already on, exactly as for
every other terminal state. Nothing is destroyed sooner than today; the *overnight* destruction
is what the guard removes, and 30 days is the window the document move has to land inside.
`test_the_thirty_day_document_clock_is_untouched` pins that, and says in its own docstring that
changing it is counsel's question and not an engineering one.

**What it leaves alone.** `erase()` is unchanged, so HR's Purge on a person's own request, the
180-day not-hired clock and the 90-day backstop all still delete exactly as before. A hired row
with no uploads at all is still erased, which is the shipped intent.

## 3 · Acceptance criteria — how each is met

| AC | How | State |
|---|---|---|
| AC-1 button present on a *Submitted*, unlinked row | `refresh` in the JS, gated on status, `employee` and `erased_on`, plus `frappe.model.can_create("Employee")` | met |
| AC-2 the six details and the name, character for character | `test_it_returns_the_six_details_and_the_name_character_for_character` asserts the whole dict | met |
| AC-3 the endpoint creates nothing | `test_it_creates_nothing_and_does_not_move_the_naming_series` | met |
| AC-4 absent/refused in every other state, when linked, when erased | `_must_be_ready`, three tests | met |
| AC-5 the key set is exactly the seven | `test_the_keys_are_the_one_map_inverted_and_nothing_else` | met |
| AC-6 the joining-date guidance line | `frm.dashboard.add_comment`, the brief's exact words | met — **wording still open** (§8) |
| AC-7 a blank joining date refuses the save | Frappe's own `reqd: 1`. Pinned by `test_the_joining_date_is_mandatory_on_employee_so_hr_must_type_it` | met, by the framework |
| AC-8 the confirmation names the person, dismissing writes nothing | `frappe.warn` with the name read from the **Employee row**, not from the form. `test_the_reply_names_the_employee_it_was_told_to_link` tests what the call sends and returns | met |
| AC-9 link, status, `closed_on`, sign-in closed | `test_it_links_moves_the_status_on_and_stamps_the_closing` | **met in part. The file half is out of scope** — no `File` row moves, no `Employee Document` row is written |
| AC-10 a failure part way writes nothing | `test_a_failure_part_way_through_writes_nothing`, plus the source pin for `frappe.db.commit` | met |
| AC-11 a second link is refused, nothing changes on either Employee | `test_a_second_link_is_refused_and_changes_nothing` | met |
| AC-12 no documents → it says so | `documents_left_behind` is 0 and the JS says "They uploaded no documents." | met |
| AC-13, AC-14, AC-15, AC-17 | about moved files and checklist rows | **NOT met — out of scope.** The result line is honest instead: it says how many documents are **still on the invite** and have not moved |
| AC-16 the green line with real counts | `test_it_reports_the_real_count_of_details` (6, and 5 when one is blank) | met, minus the document count it cannot claim |
| AC-18–AC-21 who must not | `TestWhoMayPrefill` and `test_a_plain_staff_login_and_a_joiner_are_both_refused`. **Unit calls as four real logins, not HTTP requests** — see §7 | met at the method; the HTTP door test is owed |
| AC-22 no date in the payload | `test_no_date_or_datetime_is_in_the_payload`, generated from `Employee`'s meta | met |
| AC-23 the ignore_permissions ceilings do not rise | `test_portal_security_010` ran 45 + 5 **OK** with a new row at 0, no existing row raised | met |
| AC-24 a hired joiner's documents survive the nightly job | `test_a_hired_joiners_documents_survive_the_nightly_job` | **met — this is the headline test** |
| AC-25 an unlinked row's files still go on the 30-day clock | unchanged code; `test_the_thirty_day_document_clock_is_untouched` | met |

## 4 · The seven dimensions, re-assessed against the code I actually wrote

| Dimension | Proposed | After the code | Note |
|---|---|---|---|
| **Performance** | neutral | **neutral** | Prefill: 1 `has_permission`, 1 `db.exists`, 1 `get_doc`, 1 doc permission check. Link: 2 `db.exists`, 2 `get_doc`, 1 locked `get_value`, 1 `db.count`, 1 save. **No loop over anything that grows**, no file byte read, no new index, no job. The slowest test was 5.5 s and that is two PDF fixtures being written, not the endpoint |
| **Security** | improves | **improves** | Zero `ignore_permissions` in the new file, pinned twice (the 010 ceiling and a source test in this slice's own suite). Both endpoints check rights **on the document**, so User Permissions apply. Every argument type-checked; no client value selects a doctype, a fieldname or a code path. Both POST-only, both rate-limited on the signed-in user |
| **Reliability** | improves | **improves** | The row lock works: `test_the_link_is_read_from_the_database_not_from_the_form` refuses a second writer. **One correction to my own proposal:** `end_the_sign_in` (existing, 079) calls `frappe.db.commit()` inside `on_update`. So the step is not one uncommitted transaction end to end — but that commit runs *after* the link row is written and *nothing of mine runs after it*, so the link and the status always land together. I over-claimed in the proposal and I am correcting it here rather than leaving it |
| **Scalability** | neutral | **neutral** | Nothing per-employee, nothing per-month |
| **Maintainability** | improves slightly | **improves** | The field map exists once. The subtract pass took out a one-use constant, a one-use tuple unpack and two unused return keys |
| **Data integrity** | improves | **improves, most of all** | Which Employee a joiner became is recorded for the first time, terminally, confirmed by name — **and the guard stops the new path destroying the uploaded documents overnight** |
| **Compliance / privacy** | neutral | **neutral, and that is the point** | No new field, no new collection, **no file moves anywhere**, so there is no visibility delta at all: 082-PRIV-1 (who can read an `Employee`) and 082-PRIV-2 (no retention clock for an employee document) stay closed as gates and nothing was pre-empted. The joiner's sign-in closes sooner, which is an improvement. Every log line I added carries a row reference, a count and a user — **never a name, a field value or a file name** |

## 5 · NFR notes

- **Query counts.** Prefill 4 reads, 0 writes. Link 6 reads, 1 save (the save's own writes are
  the row, its `Version` row, and the existing sign-in closing where there is a sign-in).
- **Indexes added:** none. The `File` count filters on `attached_to_doctype` +
  `attached_to_name`, which Frappe already indexes on `File`.
- **Background jobs added:** none.
- **Permission enforcement points:** `has_permission("Employee", "create")` and
  `doc.check_permission("read")` on the prefill; `doc.check_permission("write")` on the
  submission and `person.check_permission("write")` on the Employee for the link. All server
  side. The two buttons are hidden by role, which is a courtesy and not a control.
- **Sensitive fields touched:** mobile, personal email, home address, emergency contact name,
  relation and phone — read and handed to one HR browser, stored nowhere by this code. **No
  statutory identifier, no bank field, no salary, no identity document.**
- **Fallbacks:** none needed. There is no external call, no AI, no queue and no cache in this
  path, so there is nothing to time out, retry or invalidate.
- **Rate limit:** 30 per hour per signed-in user on each endpoint, reusing
  `field_app_limits._limited(HR_KEY, "user")`. Both are `methods=["POST"]` **because the limiter
  only bites on POST** — a GET-able read endpoint would have had an unenforced limit. The
  prefill is still read-only; it inserts nothing.

## 6 · Commands I ran, and what they said

| Command | Result |
|---|---|
| `bench --site test_site run-tests --module alvoraa_portal.tests.test_joiner_to_employee_082` | **32 tests, OK.** Run twice: 31 OK at 96.6 s, then 32 OK at 22.7 s after the late changes (the three-field locked read, the guest sweep, the HTML escaping) |
| `bench ... --module alvoraa_portal.tests.test_portal_security_010` | **45 OK + 5 OK** — both batches, including the new ceiling row at 0 |
| `bench ... --module alvoraa_portal.tests.test_joiner_078` | see §9 |
| `bench ... --module alvoraa_portal.tests.test_joiner_079` | see §9 |
| `python scripts/check_api_paths.py --max 0` | 288 paths, **0 unresolved** — both new front-end method paths resolve |
| `python scripts/check_app_integrity.py` | **916 checks, OK** |
| `python scripts/check_design_system.py` | **OK**, emoji 0 on every page |
| `node scripts/check_portal_handlers.js` | **all reachable and callable** |
| `node scripts/check_undefined_js.js` | **none** |
| `node scripts/check_rating_bands.js` · `python scripts/check_nginx_conf.py` · `python scripts/check_no_demo_passwords.py` | **OK** |
| `semgrep --config hrms/semgrep` | **NOT RUN — semgrep is not installed on this machine.** The CI step is `continue-on-error` anyway. Checked by hand against what those rules catch: no `frappe.db.sql` in the new module at all, the one `sql` call in the test is parameterised with `%s`, every `_()` takes a literal and is `.format()`-ed **after** translation (never an f-string inside `_()`), and no endpoint takes `allow_guest` |
| `ruff check` on my two new files + `joiner_housekeeping.py` | **1 error, pre-existing**: `I001` on `joiner_housekeeping.py`'s import block, which I did not touch. My new files are clean. The CI step is `continue-on-error` against a 1,050-violation backlog |

### Two things about running these tests that cost me an hour

**1. Repeated `--module` flags do not stack.** The last one wins, so a command that names three
suites runs one. My first "three suites, all green" was `test_portal_security_010` alone. Check
the `Running N tests` line against the number you expected.

**2. The shared `hrlocal-bench` runs `frappe worker --queue default,short,long` against the same
database.** I found it with `ps` after `test_joiner_078` came back red twice with *different*
numbers — 18 errors, then 27 errors and 1 failure. **20 of the 27 were
`frappe.exceptions.QueryDeadlockError`**, which is a concurrency artefact and not a logic
failure: the worker executes queued jobs inside its own transactions while a suite holds row
locks, and either side can lose. `docker ps` and `pgrep -af run-tests` do **not** show this —
the worker is not a test run, so the board can honestly say "bench free" while the DB is still
busy. **Add `ps -eo args | grep worker` to the checks before trusting a red result.** I did not
stop the worker: it belongs to every session and to the main checkout, and stopping it is a
"say it on the board and ask" action.

## 5a · The UI flow, traced by hand — and what I could not click

The change process asks for a hand trace of every affected UI flow for a JavaScript change.
This JS is a **Desk form script** registered through `doctype_js` (so `hooks.py` is unchanged),
and **no DOM test suite covers Desk scripts** — `run_dom_tests.js` and `check_design_system.py`
scan the portal pages, not this file. So the trace is what there is, plus four static gates.

| Step | What happens | Verified how |
|---|---|---|
| HR opens a *Submitted*, unlinked, un-erased row | the guidance line about the joining date appears; two buttons appear, each gated on a right (`can_create("Employee")`, `frm.perm[0].write`) | read, line by line, against the existing patterns in the same file |
| HR presses **Make their employee record** | `frappe.call` → the prefill → `frappe.new_doc("Employee", values)` → `frappe.route_options` set → `get_new_doc` copies the seven values → `Employee.quick_entry` is unset, so `is_quick_entry()` is false → `set_route("Form", "Employee", "new-employee-…")`: **the full unsaved form, filled, with no date** | every link in that chain read in the installed frappe v16.33.1 source, cited in `00-impact-analysis.md` §1 |
| HR abandons the form | nothing exists. No Employee, no change to the submission | `test_it_creates_nothing_and_does_not_move_the_naming_series` |
| HR presses Save with no joining date | Frappe refuses, naming Date of Joining | `reqd: 1`, pinned by a test |
| HR presses **Link the employee record** | `frappe.prompt` with a Link field → `frappe.db.get_value` reads `employee_name` **from the Employee row** → `frappe.warn` names that person → on yes, the link call | the name is read from the record, not the form, so a confirmation cannot agree with the mistake |
| HR dismisses the confirmation | nothing is called, nothing is written | `frappe.warn`'s own contract; and the server refuses a second link anyway |
| Afterwards | a green box names the person, the real count of details, and **how many documents are still on the invite and have not moved** | `test_it_says_how_many_documents_it_did_not_move` |

**What I could not do: click it in a browser.** There is no Desk browser session in this run, so
the rendering of the two buttons, the dialog and the green box is reasoned from source and from
the three other dialogs already in this same file, not seen. **A human should press both buttons
once before this goes anywhere.** Said plainly rather than left as an assumption.

## 6a · The door list from `data-doors.md`, walked

**The thing that makes this slice easy to answer: it adds no readable data anywhere.** No new
field, no new DocType, no new record type, and **no file and no value moves to any record a
wider audience can read**. The prefill payload is never stored; it lives in one unsaved form in
one browser. So doors 1 to 6, 8 and 10 have nothing new behind them.

| # | Door | This slice |
|---|---|---|
| 1 | `/api/resource/<DocType>` CRUD | **No new doctype and no new field.** `Alvoraa Joiner Submission` permissions are untouched: HR Manager read/write/create, HR User read, Employee role **nothing**. `employee` is still `read_only: 1`, so even an HR Manager cannot PUT it through the REST API — the endpoint is the only writer |
| 2 | `reportview.get` / `get_list` / `get_count` | Nothing new to list. No field added to any list view, export, report or notification — **I did not widen a single visibility surface, and I am saying so because the temptation was there**: it would have been one line to put the Employee's name on the submission's list view |
| 3 | `frappe.client.*` | `get_value` on `Employee.employee_name` is called by the confirmation dialog. It is Frappe's own endpoint with its own permission check (`client.py:135`), and it reads a name the caller must already hold read on. Nothing else |
| 4 | Link search | The confirmation dialog's Link field searches `Employee`, through Frappe's own `search_link` with its own permissions. No `filter_fields`, no new search surface |
| 5 | Report view, CSV export, print, standard reports | Nothing added |
| 6 | Share, assign, comment, tag, like | Nothing added. No record becomes shareable that was not |
| 7 | **Whitelisted methods — the only new surface** | Two. Both POST-only, both rate-limited per signed-in user, both check rights **on the document** so User Permissions apply. Tested as **HR Manager (allowed), HR User (prefill yes, link no), a plain Employee login (refused both), a joiner-role session (refused both)**. **Guest is not tested and neither is the raw HTTP form — that is gap G2** |
| 8 | Child tables on their own | **None touched.** No `Employee Document` row is written by this slice, which is exactly why 082-PRIV-1's exposure is not created |
| 9 | The role's own write rights | Unchanged. Nothing grants a role anything |
| 10 | Background and bulk paths | One scheduled job function changed, and the change only ever **refuses to delete**. No Data Import, no bulk edit, no patch |

**Bypasses counted: zero new.** `joiner_to_employee.py` contains no `ignore_permissions`, pinned
by the 010 ceiling at 0 **and** by a source test in this slice's own suite. The submission
controller's ceiling stays 4 and the housekeeping module's stays 6 — the guard I added uses
`frappe.db.count`, which needs no bypass.

**What I did not test, plainly:** the HTTP form through `/api/method` on a freshly created site,
and Guest. The refusals are server-side and document-level, so I expect them to hold — but
expecting is not proving, and ALV-249 is exactly what happens when a portal-shaped test is
mistaken for a door test.

## 7 · Known gaps and shortcuts

| # | What | Label |
|---|---|---|
| **G1** | **A hired joiner's documents still go 30 days after hire**, on counsel's ruling-4 clock, which I was told not to touch. The guard removes the overnight deletion, not the 30-day one. **This is the window the document move has to land inside.** | **intentional trade-off**, by instruction |
| **G2** | **AC-18 to AC-21 are proved as four real logins calling the methods, not as HTTP requests through `/api/method` on a fresh site.** `data-doors.md` asks for the HTTP form and `01c` §4.2 asks for five principals including Guest. The method-level proof is real (the refusal is server side and document-level), but the door list is not fully run. | **temporary debt.** What removes it: the test automation engineer's HTTP door test on a fresh site |
| **G3** | **AC-9's file half, and AC-13/14/15/17 entirely, are not met** — no file moves, no checklist row is written, nothing is marked *Received*. The result line says so honestly rather than claiming a tick. | out of scope, Surbhi 4 Nov |
| **G4** | **An `Employee` can be linked from two different submissions.** Nothing refuses it. It is a sibling of `01` Risk 5 and about three lines, but no AC asks for it. | **noted, not built** — needs Surbhi's word |
| **G5** | **082-SEC-4's test as written cannot pass the spec's own design**: it says to fail if any payload key is in `LEVEL_1` or `LEVEL_2`, but `first_name` **is** in `LEVEL_2` and the spec requires it (§5). I wrote it as *nothing at level 1, and `first_name` is the only level-2 key*, generated from both constants so adding a field to either still tightens it. | **flagged, not softened quietly.** Needs the security engineer's nod |
| **G6** | The prefill and the link refuse an **`Invited`** row, although the controller's `_follow_the_employee` would accept one. A person can be hired without ever sending the form back. | **acceptable simplification.** An `Invited` row holds nothing to copy; widening it is one line if Surbhi wants it |
| **G7** | `run_daily()` in a test operates on the whole site, so a leftover row from another suite could be erased by my test run. `test_joiner_078` already does this, so it is the house pattern, not new. | **acceptable simplification** |
| **G8** | **Three wordings are still the product manager's draft, not an approved design** (§13 of the spec): the button labels, the joining-date line and the result line. There is no `01b` and no prototype for this slice, so **prototype parity could not be checked — there is nothing to check against.** | **needs Surbhi.** A label is a one-line edit |

**Nothing is labelled dangerous debt.** The one item that would have been — the overnight
destruction of a hired joiner's identity documents — is the thing the guard fixes, and it is
proved by a test.

## 8 · What I would do with more time

Run the HTTP door list properly (G2), and put G4's three lines in. Nothing else: the rest of the
list is either out of scope by decision or a question for a human.

## 9 · What else moved while I worked

`origin/dev` was at **a53b333a** when I started and my branch was identical to it. I fetched
again before each commit. **To be completed at the final commit with what, if anything, came in,
and how each conflict was resolved.**
