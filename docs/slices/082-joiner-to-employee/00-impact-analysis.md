---
slice: 082-joiner-to-employee
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-11-04
status: strategy, for Surbhi
scope_as_given: the button and the linking step ONLY. The document move is OUT.
---

# 082 · Impact analysis and strategy — the button, the link, and the delete I must stop

## 0 · The short version

Three things get built: a read-only prefill endpoint, two buttons on the Desk form, and the
linking step (which does not exist today — I re-verified: `employee` is `read_only: 1` and no
product code writes it).

**Building the link is what makes this risky, and the risk is not in the new code.** Setting
`employee` moves the status to *Made an employee*. That status is unreachable in the product
today, so the nightly pass `_erase_the_redundant_copies` has never fired on a real row. The
moment the link exists, it fires — and it calls `erase()`, which calls `delete_the_documents()`,
which deletes the joiner's uploaded identity documents permanently, bytes included
(`alvoraa_joiner_submission.py:198-220`). It runs **first** in `run_daily`
(`joiner_housekeeping.py:71`).

The document move that would make that deletion safe is out of scope. **So I build a guard, and
the guard is part of this change, not a note.** Mechanism and argument in §5.

## 1 · What I verified in the installed source today

Not from memory. Bench `hrlocal-bench`, frappe **v16.33.1**, erpnext and hrms installed.

| Claim | Where | Verdict |
|---|---|---|
| `Employee.date_of_joining` is `reqd: 1` | `erpnext/setup/doctype/employee/employee.json` | **True.** So are `first_name`, `company`, `status` (default `Active`), `gender`, `date_of_birth` |
| No `Employee` Date field carries a default | same file, all 16 Date fields read | **True.** So no date can arrive by accident |
| `frappe.has_permission(doctype, ptype, doc=, throw=)` | `frappe/__init__.py:600` | exists, and applies User Permissions when `doc` is passed |
| `Document.check_permission(permtype)` raises `PermissionError` | `frappe/model/document.py:397` | exists. This is the shape I use |
| `frappe.db.get_value(..., for_update=True)` | `frappe/database/database.py:527` | exists. This is my concurrency lock |
| `frappe.new_doc(doctype, opts)` opens the **full unsaved form** with values when the doctype has no quick entry | `create_new.js:364` → `quick_entry.js:57` → `is_quick_entry()` returns False because `Employee.quick_entry` is unset → `set_route("Form", ...)`; `create_new.js:60-67` applies `frappe.route_options` to the new doc | **True.** This is the `make_employee` mechanism without a Document payload |
| `frappe.model.can_create`, client `frappe.db.get_value` | `model.js:324`, `db.js:42` | exist |
| `Employee Document` child table and the private-file path | not touched by this scope | out of scope with the move |

**One thing I did NOT verify and do not need to in this scope:** whether HR Manager's own rights
are enough to re-point a `File` row (082-SEC-3's open question, §7.3 of `01c`). No file is
touched by this scope, so the question stays open for the move.

## 2 · Cross-module reach

| App | Touched |
|---|---|
| `alvoraa_portal` | **All of it.** One new module, one existing controller (docstring only), one existing job function, one JS file, two test files |
| `hrms` | **Nothing.** No file changed |
| `erpnext` | **Nothing.** `Employee` is read for its meta in a test and written only by HR pressing Save |
| `frappe` | Nothing. No upstream edit |
| `alvoraa_goals`, `alvox_compensation` | Not touched |

**HRMS domains:** org structure (an `Employee` appears, created by HR as today), pre-onboarding
(status and retention). **Not** leaves, attendance, payroll, appraisals. The one link to
attendance is negative and deliberate: no date is prefilled, so the absence-backfill trap cannot
be reached by this code.

### Every caller of every function I change — grepped

| Function | Callers found | What my change does to them |
|---|---|---|
| `joiner_housekeeping._erase_the_redundant_copies` | `run_daily` (`:71`); `test_joiner_078.TestRetention.test_someone_who_joined_has_the_copy_erased` | Adds a skip for a row that still holds files. The test's row has **no** files, so it still erases and still passes |
| `alvoraa_joiner_submission.erase` | `joiner_housekeeping` ×4, `joiner_invite.purge_submission`, `test_joiner_078`, `test_joiner_079` | **Unchanged.** The guard is in the hired pass, not in `erase` — purge, the not-hired clock and the backstop must still delete |
| `alvoraa_joiner_submission.delete_the_documents` | `erase`, `_delete_the_documents_sooner`, tests | **Unchanged** |
| `AlvoraaJoinerSubmission._follow_the_employee` | the controller's own `validate` | **Unchanged code.** It becomes reachable for the first time |
| `COLUMN_FOR_TICK` | `joiner_public`, `joiner_invite`, `test_joiner_078/079` | Read, never changed. The prefill inverts it at runtime so no second list exists |

**New files start at zero `ignore_permissions`.** I add no bypass anywhere; the ceilings in
`test_portal_security_010` (submission **4**, housekeeping **6**) do not move, and I add one
`CEILINGS` row at **0** for the new module so the proof covers it.

## 3 · Persona impact

| Persona | Before | After |
|---|---|---|
| **HR Manager** | Reads the submission, opens a second window, retypes seven fields, and cannot record which Employee the person became at all | Two presses. A prefilled unsaved Employee form (they still type company, gender, date of birth and the joining date — four fields the joiner was never asked for), then a link that names the person before it writes, closes the joiner's sign-in, and tells them honestly that the documents have **not** moved |
| **HR User** | read-only on the submission | May prefill (read on the submission + create on `Employee`). **May not link** — write on the submission is HR Manager and System Manager only. Unchanged rights, no new surface |
| **Employee (plain staff login)** | No permission on the submission at all | **Unchanged.** Both endpoints refuse. No new field is readable, no new visibility |
| **Employee (the new joiner)** | Their words sit on a record HR retypes from | Their words reach their personnel record character for character. Their sign-in closes on hire (existing `on_update` behaviour, reachable for the first time) |
| **Line manager** | Cannot see a submission | **Unchanged.** Both endpoints refuse. **And because the document move is out, no identity document lands on `Employee`, so 082-PRIV-1's exposure is not created** |
| **CXO** | Nothing | Nothing |

## 4 · The seven non-functional dimensions — proposed verdict

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **neutral** | Prefill: 1 `get_doc` + 2 permission reads, no file touched. Link: 1 `get_doc` on each side, 1 locked `get_value`, 1 `count` on `File`, 1 save. No loop, no N+1, no new index, no job. Both well inside the 500 ms budget |
| **Security** | **improves** | Two server-side checked endpoints replace a step HR could not do at all. Zero new `ignore_permissions`. Every input type-checked; no client-supplied doctype or fieldname selects a code path. Rate-limited on the signed-in user. 078-SEC-12's intent is kept by name: no code writes any date |
| **Reliability** | **improves** | The row is re-read under `SELECT ... FOR UPDATE` inside the transaction, so two HR users pressing at once cannot both win. No `frappe.db.commit()` in the new path, so a failure rolls the whole step back. The erase guard **fails closed** |
| **Scalability** | **neutral** | A handful of submissions a week. Nothing per-employee, nothing in a loop over headcount |
| **Maintainability** | **improves slightly** | One new module of ~130 lines; the field map stays in exactly one place (`COLUMN_FOR_TICK`, inverted at runtime) so no second list can drift, including in the browser |
| **Data integrity** | **improves, and this is the load-bearing one** | Today, nothing records which Employee a joiner became. After this, it is recorded, terminal and confirmed by name. **And the guard stops the new path destroying the uploaded documents overnight** |
| **Compliance / privacy** | **neutral, deliberately** | No new field, no new collection, **no identity document moves anywhere**, so there is no visibility delta at all and 082-PRIV-1/PRIV-2 stay closed as gates. The joiner's sign-in closes sooner, which is a privacy improvement. Nothing personal in any log line I add — counts only |

## 5 · The guard on the delete — mechanism, and why this one

**The requirement:** the permanent deletion of a hired joiner's uploaded documents must not be
reachable until the document move exists, and if the code cannot tell whether they moved, it
keeps them.

**Two candidates were on the table.**

| | Mechanism | Verdict |
|---|---|---|
| **A** | **Skip a hired row in `_erase_the_redundant_copies` while it still has `File` rows attached to it.** | **Chosen** |
| **B** | A named switch that turns the hired-erase pass off until the move ships | **Rejected** |

**Why A.** It is three lines and one helper, in the one function this slice switches on. It asks
the only question that matters — *are the uploaded files still on the invite?* — and if the answer
is yes, they have not been moved, so the row is left alone. If the count query raises, it answers
yes. That is fail-closed in the literal sense: the failure mode is *keep the documents*.

**Its best property is that it retires itself.** When the move ships, a moved row has zero files
attached, so the pass resumes on its own with nothing to remember and nothing to switch. A switch
(B) is a feature flag — banned by `no-over-engineering.md` §2 — and it is a thing somebody has to
remember to flip, which is how controls die.

**What A does not do, said plainly.** It does not stop `_delete_the_documents_sooner`, the 30-day
clock. **I was told not to touch that** — it is counsel's ruling 4. So a hired joiner's documents
still go **30 days after hire**, on the clock they are already on, the same as every other
terminal state. Nothing is destroyed sooner than today; the overnight destruction is what the
guard removes. The 30-day window is what the document move has to land inside, and it is the
honest size of the remaining gap.

**What A leaves intact.** `erase()` itself is unchanged, so HR's Purge on a person's own request,
the 180-day not-hired clock and the 90-day backstop all still delete exactly as they do today. A
hired row with no uploads at all is still erased by the hired pass, which is the shipped intent
and keeps `test_joiner_078.TestRetention.test_someone_who_joined_has_the_copy_erased` green.

## 6 · Race conditions, edge cases, state transitions — settled before the code

**Races.**

1. **Two HR users link different Employees at the same moment.** Both read `employee` as empty
   from their loaded form. Fix: the endpoint re-reads `employee` from the database with
   `for_update=True`, which takes a row lock. The second caller blocks, then reads the value the
   first wrote, and refuses by name. Not the loaded form, not `modified`.
2. **The nightly job and HR linking at the same time.** The job's `get_all` ran before the status
   changed, so the row is not in its batch; the next run picks it up and the guard skips it.
3. **Second press of the same button.** Same lock, same refusal.
4. **Legal hold ticked mid-flight.** Hold stops erasure, not linking. No interaction.
5. **No cache anywhere in this path**, so there is no invalidation question to answer.

**Edge cases.**

- *None / one / many*: no files (link succeeds, the message says no documents); one; six
  (`MAX_FILES_PER_JOINER`). Nothing loops over bytes.
- A submission already erased (`erased_on` set) → refused, both endpoints. Prefilling from an
  erased row would look like data loss.
- A submission in *Invited*, *Expired*, *Cancelled* or *Made an employee* → refused, naming the
  state. **Deliberate narrowing:** `_follow_the_employee` would also accept *Invited*; I refuse it,
  because an *Invited* row has nothing in it to copy and the approved flow starts at *Submitted*.
- A joiner with no `full_name` → `first_name` comes back empty and Frappe's own mandatory check
  refuses the save. The screen says so; we do not invent a name.
- An `employee` that does not exist, or is empty, or is not a string → refused with a sentence.
- An Employee the caller may not write (User Permission) → refused by `check_permission`.
- A person with no company, no shift, no manager → not touched; the prefill sets none of them.
- Mid-month, back-dated, half day, cancelled document, fiscal boundaries → out of reach: nothing
  here reads a calendar.

**State transitions.** `Alvoraa Joiner Submission.status`, no new state:

| From | To | Legal? |
|---|---|---|
| Submitted | Made an employee | **Yes — this slice makes it reachable** |
| Invited | Made an employee | Refused by my guard (controller would allow it; I narrow it) |
| Made an employee | anything | Refused by `_refuse_a_revival`. **Terminal and irreversible — there is no undo, and I am not building one** |
| Expired / Cancelled | Made an employee | Refused by my guard and by `_refuse_a_revival` |

**The transition the spec forgot:** nothing says what happens when the **Employee** is later
deleted while the submission still points at it. Frappe's own Link integrity refuses the Employee
delete while the link exists, so the submission cannot end up pointing at nothing. Verified
behaviour of a Link field, not new code.

## 7 · Parallel-work check

Fetched `origin/dev` at the start: **HEAD is `a53b333a`, identical to `origin/dev`. Nothing came
in.** I will fetch again before every commit and say what arrived.

| File I will change | Who else is in it, per the work board | Plan |
|---|---|---|
| NEW `alvoraa_portal/alvoraa_portal/joiner_to_employee.py` | nobody | mine |
| NEW `alvoraa_portal/alvoraa_portal/tests/test_joiner_to_employee_082.py` | nobody | mine |
| `joiner_housekeeping.py` (`_erase_the_redundant_copies` only) | nobody | mine |
| `.../doctype/alvoraa_joiner_submission/alvoraa_joiner_submission.py` (docstring only) | nobody | mine |
| `public/js/alvoraa_joiner_submission.js` | nobody | mine |
| `tests/test_portal_security_010.py` (one `CEILINGS` row) | **slice 081 adds one `CEILINGS` entry too** | Different dictionary key, one line each. If 081 lands first I rebase and keep both rows |

Not touched, on purpose: `hooks.py` (the JS is already registered by `doctype_js`), `patches.txt`,
any DocType JSON, `portal.js`, `hr_api.py`, any `hrms` or `erpnext` file, `nginx.conf`, any
workflow. **Own container `hrlocal-082`; `hrlocal-bench` is used read-only to read installed
source.**

## 8 · Cost ladder

**Rung 4, new code — one module, two endpoints, ~130 lines, and six lines in an existing job.**

- Rung 1 (already there) rejected: `Employee Onboarding.make_employee` needs a mandatory
  `Job Applicant` and a submitted onboarding record with a Project and Tasks behind it. Three
  records and a submit to reach one Employee, for a one-person HR team. And nothing in Frappe
  writes a read-only Link with a confirmation.
- Rung 2 (configuration) rejected: no setting copies a row of one DocType onto a form of another,
  and no setting makes a read-only field settable-with-confirmation.
- Rung 3 (a Client Script alone) rejected for exactly one reason: the field map lives in Python
  (`COLUMN_FOR_TICK`) and a second copy in JavaScript is two lists that drift. One small
  read-only endpoint keeps one map.
- Rungs 5 and 6 not needed: **no new DocType, no new field, no new setting, no new job, no new
  app, no new dependency, no migration, no patch.**

## 9 · What I will NOT build, and what I am handing back

Out of scope and untouched: the document move, the photograph (US-8), ALV-270, ALV-311, the staff
login, bulk convert, `_delete_the_documents_sooner`.

Noticed and deliberately left alone, for Surbhi to decide separately:

1. **An `Employee` can be linked from two different submissions.** Nothing refuses it. It is a
   sibling of `01` Risk 5 and it is three lines, but no AC asks for it, so I am not building it.
2. **OQ-6, the submission has no `company` field**, so an HR Manager of one company sees every
   company's submissions. Inherited from 078, not widened here.
3. **`082-SEC-4`'s test as written cannot pass the spec's own design.** It says to fail if any
   payload key appears in `LEVEL_1` or `LEVEL_2` — but `first_name` **is** in `LEVEL_2`, and the
   spec requires it in the payload (§5). I will write the test as: no key in `LEVEL_1`, and the
   only `LEVEL_2` key permitted is `first_name`. That keeps the drift-stopping property. **Flagged
   rather than quietly softened.**
4. **A hired joiner's documents still go 30 days after hire** (§5). The remaining gap, by
   instruction.

## 10 · Subtract pass on this proposal

Removed before showing it: a "Converted by/on" stamp (`Version` answers it), a preview dialog
(the unsaved form is the preview), a duplicate-Employee check, a warning notification before the
hired erase, a second endpoint to read the employee's name for the confirmation (the client's own
`frappe.db.get_value` does it), and a setting for the guard. Nothing remains that an acceptance
criterion does not ask for.
