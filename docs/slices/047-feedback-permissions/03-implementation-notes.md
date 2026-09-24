# Slice 047 — ALV-117 implementation notes

Local only. **Not pushed, not merged into `dev`, no server, no tenant, no `docker cp`.**
Branch `slice/047-feedback-permissions`, worktree
`.claude/worktrees/047-feedback-permissions`, from `origin/dev` `8718f27`.

Four commits:

| Commit | What |
|---|---|
| `8ea713a` | the two hooks and the access module |
| `82e817e` | the persona-by-action tests |
| `ce98806` | the test corrections the first runs forced, and the three findings they exposed |
| `e02651b` | finding F1's gate in `get_feedback_history`, with its own test module |

## 1. What was built, file by file

| File | Mechanism | Why that one |
|---|---|---|
| NEW `hrms/hrms/alvoraa_hr_core/feedback_access.py` | **extend** — two framework hook functions | `permission_query_conditions` and `has_permission` are Frappe's own extension points. Nothing upstream is patched, so `bench update` cannot undo it |
| `hrms/hrms/hooks.py` | **configure** — one line at the end of each of the two existing dicts, with a comment | Hot-file rule: append, rewrite no block |
| NEW `hrms/hrms/alvoraa_hr_core/tests/test_feedback_access_047.py` | tests | The permission surface is the product, so it is walked action by action and persona by persona |
| `hrms/hrms/hr/doctype/appraisal/appraisal.py` | **extend** — one `frappe.has_permission` gate in `get_feedback_history` | Finding F1. Its own commit so it can be reverted alone |
| NEW `hrms/hrms/alvoraa_hr_core/tests/test_feedback_history_gate_047.py` | tests | Travels with F1's commit |

Nothing else was touched. **No DocType JSON, no `Custom DocPerm`, no fixture, no
migration, no new dependency, no config flag.**

## 2. The rule, and the decision that was asked for

* **author** — read, write, create, submit, cancel, print, email, share on what they wrote
* **subject** — **read only**, whatever roles they hold
* **manager** — read only, direct reports only, and only while the manager's own Employee
  record is Active
* **HR** — `hrms.alvoraa_hr_core.access.permitted_employees`, the one shared definition
* **everyone else** — nothing, and the query condition is `1=0`, never `""`

`create` additionally requires the caller to be the `reviewer`, so nobody can publish an
opinion under a colleague's name.

**A manager does not see feedback their report wrote about somebody else.** It is not
about their report, the subject never agreed to it, and a manager who can read their
team's outgoing opinions is how honest feedback stops being given. The dotted-line flow
makes it concrete: a report may be asked to review the manager's own peer. Written down
as `test_a_manager_does_not_see_what_their_report_wrote_about_someone_else`.

## 3. Test results — all real, all on `test047` in container `hrlocal-047`

| Module | Result |
|---|---|
| `test_feedback_access_047` | **27 OK** (9.4 s) |
| `test_feedback_history_gate_047` | **4 OK** (6.8 s) |
| `hr.doctype.employee_performance_feedback.test_employee_performance_feedback` | **5 OK** |
| `hr.doctype.appraisal.test_appraisal` | **11 OK** |
| `hr.doctype.appraisal_cycle.test_appraisal_cycle` | **2 OK** |
| `alvoraa_hr_core.tests.test_attendance_score` | **11 OK** |
| `alvoraa_org_structure.tests.test_org_structure` | **33 OK** |
| `alvoraa_org_structure.tests.test_reach` | **13 OK** |

**106 tests, 0 failures, 0 errors.** Six runs were needed to get there; runs 1–5 failed,
and three of those failures were the product of the tests being wrong about Frappe, not
the hooks being wrong (section 6).

The persona matrix inside `test_feedback_access_047`: ten actions (read, write, create,
submit, cancel, export, print, share, report, email) across fourteen personas — subject,
author, unrelated employee, manager of the subject, manager of someone else, the other
manager's report, a head-office person with no branch, a leaver with an enabled login,
the leaver's ex-report, store HR in scope, store HR out of scope, company HR, an HR User,
System Manager — plus Guest.

**Export and report are tested end to end**, through `frappe.desk.reportview.export_query`
and `frappe.desk.reportview.get`, for every persona, against the exact expected set of
records. They never reach `has_permission`, so the query condition is the only thing
standing there, and a filtered list with an unfiltered export is the same leak.

## 4. Proving the tests bite — each hook removed in turn

| Hook removed from `hrms/hooks.py` | Result |
|---|---|
| `permission_query_conditions` | **42 failures.** Every list, report, export and count test for every persona, plus `test_both_hooks_are_registered`, the leaver test, the head-office test, the manager-decision test and the DocShare test |
| `has_permission` | **100 failures.** Every per-action cell for every persona who should be refused, on both the draft and the submitted record, plus the record-at-its-own-URL tests, the impersonation test and the subject-cannot-edit test |
| both present | **27 OK** |

Neither hook is redundant, and neither covers the other's job.

## 5. What else in the three apps reads the doctype — checked, not assumed

| Caller | Effect |
|---|---|
| `appraisal.get_feedback_history` — `frappe.get_list` | **now filtered** |
| the same function's six `frappe.db.count` and one `frappe.db.get_value` | **not filtered** — finding F1, now gated |
| `appraisal.calculate_avg_feedback_score` — `frappe.qb.avg` | not filtered, and must not be: it is the score maths, run as the system |
| `appraisal.add_feedback` | still works — the author branch allows `create` when they are the reviewer |
| `appraisal_cycle.get_employees_without_feedback` — `frappe.qb`, whitelisted, **no role gate** | not filtered; one org-wide count, no person named. Finding F2, reported, not fixed |
| `hr/report/appraisal_overview` | its rows come from Appraisal, which the Employee role cannot read at all |
| `alvoraa_org_structure/dotted_line.py` | **proved still working.** `test_the_dotted_line_insert_still_works` inserts with `ignore_permissions=True` as a user who cannot read the row, then checks `frappe.db.exists` still finds it — that is exactly the duplicate check at `dotted_line.py:125` |
| `dotted_line.pending_dotted_line_feedback` | not filtered, but gated by `frappe.only_for(["HR Manager","HR User","System Manager"])` |
| **`alvoraa_portal` and `alvoraa_goals`** | **no reference to the doctype at all** |

## 6. Findings — three of these the run found, and a document would have guessed wrong

* **F1 (fixed, own commit).** `get_feedback_history` leaked the star distribution and the
  average feedback score of any employee to any logged-in user who knew an employee id
  and an appraisal id. Gated on `Appraisal` read, which adds no new rule: `Appraisal`
  already has a row filter and a `has_permission` hook from `alvoraa_goals`, and the
  Employee role holds no permission on Appraisal at all.
* **F2 (reported).** `get_employees_without_feedback` is whitelisted with no role gate.
  One org-wide count per cycle, no person named. Low, but it should have a gate.
* **F3 (measured, worse than expected).** A `DocShare` beats **both** hooks, not just the
  list. Frappe ORs the share condition onto the query conditions **and** falls back to
  `false_if_not_shared()` after the controller has refused — covering read, write, share,
  submit, email and print. What still holds: creating the share needs `share`, which the
  hook governs, so only the author or HR in scope can share at all. The residue is "the
  author may hand their own feedback to anyone." **Closing it properly means dropping
  `share` (and probably `email`) from the Employee row in the doctype JSON — a change to
  a standard Frappe HR doctype, and a decision of its own. Recorded, not made quietly.**
* **F4 (reported).** `permitted_companies` does not check the HR user's own status, so a
  Left HR person with a Company User Permission keeps HR scope. Pre-existing, in shared
  code three slices depend on.
* **F5 (measured — the severity story for ALV-117 needs this).** ERPNext's Employee has
  `create_user_permission`, **on by default**, and linking a login to an Employee record
  writes a User Permission tying that login to its own Employee record on **every**
  doctype with an `employee` link — this one included. On the test site it was created
  for all fourteen fixture logins without being asked for. **So on a tenant where those
  rows exist, an ordinary employee was already limited to feedback about themselves.**
  That does not make ALV-117 smaller, for three reasons the test shows: the row is one
  tick away from not existing, it is per employee rather than per tenant, and while it is
  on it also blocks the manager and HR access the product needs. The setting gave an
  accident; the hooks give a rule.
  **This must be checked on `dtc.alvoraa.co` before the logins are created** — I have no
  server access and could not.
* **F6 (measured).** The "read-only" HR User role is not read-only on this doctype. Every
  HR person also holds the Employee role, and that row grants write, create, submit and
  cancel. The hooks do not widen it — before them the same person could write on every
  record in the tenant, and now only inside their HR scope — but the doctype's read-only
  HR row has never meant what it says.

## 7. The seven non-functional dimensions, against the code actually written

| Dimension | Before → after | One line |
|---|---|---|
| Performance | **degrades slightly** | Two extra `Employee` queries per list call, three for HR. The HR branch puts an `employee in (...)` list of one id per employee in scope into the SQL: 302 ids on dtc, about 1,000 on slice 044's scale fixture, roughly 12 KB of SQL. Accepted deliberately — one shared definition of HR scope beats a faster second one that can drift. **Not measured at 1,000 employees; see section 9** |
| Security | **improves** | Ten actions on every record in the tenant become ten actions inside a stated scope, enforced server side on both entry points, proved persona by persona |
| Reliability | **neutral** | Controller hooks can only deny, so nothing is granted that the role rows did not already allow. No upstream patch. The dotted-line insert is proved still working |
| Scalability | **neutral to slightly negative** | Bounded by employees in HR scope, not by feedback rows |
| Maintainability | **improves** | One new module, the reasoning in its docstring, next to the pair it copies. `access.py` untouched, no DocType JSON touched |
| Data integrity | **improves** | The subject can no longer edit, submit or cancel feedback about themselves. Today they can |
| Compliance / privacy | **improves** | Minimisation and purpose limitation on the most sensitive free text in the product. Fails closed. No personal data in any log — the module logs nothing at all |

## 8. Parallel work

`origin/dev` `8718f27`; local `dev` `98f0b7f` (ALV-119, a compose config line, no
overlap). Nothing came in from anyone during the slice. No other session claims
`hrms/hrms/hooks.py`, `feedback_access.py` or `appraisal.py` on the work board.
Uncommitted work by others in the main checkout — the `mobile/field-app/android/**` tree
and four untracked `docs/` folders — was not staged, reverted or touched.

**Deliberately not on any redesign branch**, so it can reach `dev` on its own, ahead of
034 → 042 → 043 → 045.

## 9. Known gaps and shortcuts

* **Escalate now: F5 must be checked on production before the 302 logins are created.**
  Whether `Employee` User Permission rows exist on `dtc.alvoraa.co` decides how exposed
  the tenant is today, and it is a read-only query. I could not run it.
* **Decision needed (F3):** drop `share` and `email` from the Employee row in the
  doctype JSON, or accept that an author can hand their own feedback to anyone.
  **Intentional trade-off** — a JSON change to a standard Frappe HR doctype is not
  something to slip into a permissions fix.
* **The 1,000-employee HR scope is not measured.** Slice 044's fixtures exist on another
  container. **Temporary debt** — one measurement run on `test044` removes it.
* **F2 has no gate.** **Acceptable simplification** — one org-wide count, no person named.
* **No browser click-through.** Everything is proved through the same server entry points
  the desk uses (`reportview.get`, `reportview.export_query`, `client.get`), which is
  where the permissions actually are. **Acceptable simplification.**
* **`_make_leaver` writes the row directly.** ERPNext refuses to relieve somebody who
  still has reports (`InactiveEmployeeStatusError`) — a good rule that closes most of
  that case in practice but not all of it, since `reports_to` can be set afterwards and
  imports skip the validation. The fixture forces the state so the hook is proved to fail
  closed anyway. Commented in the file.

## 10. Commands run

* `python scripts/check_app_integrity.py` before every commit — **629 checks, all
  consistent**, four times
* `ruff check` on every file touched — clean (the one `RUF005` in the tree is
  pre-existing, in `test_attendance_score.py`, not mine)
* `bench --site test047 run-tests --module ...` — eleven runs in total: six on the main
  module while the expectations were corrected, one on the gate module, two fail-closed
  proofs, and the eight-module regression sweep
* `docker run --rm <image>` read-only reads of Frappe 16.33.1 source to verify
  `has_controller_permissions`, `get_doc_permissions`, `false_if_not_shared`,
  `DatabaseQuery.get_permission_query_conditions`, `reportview.export_query` and
  `frappe.client.get` before relying on any of them

Own container `hrlocal-047`, own redis `hrlocal-047-redis`, own volume
`hrlocal-047-sites`, own site `test047`. **`hrlocal-bench` was never used. No
`docker cp`. One test run at a time.**
