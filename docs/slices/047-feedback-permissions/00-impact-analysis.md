# Slice 047 — ALV-117: row-level permissions on Employee Performance Feedback

Impact analysis and strategy. Written 2026-09-24. Local only.

## 0. The fault, verified in this worktree

`hrms/hrms/hr/doctype/employee_performance_feedback/employee_performance_feedback.json`
gives the plain **Employee** role, on the whole doctype:

| read | write | create | submit | cancel | export | print | share | report | email | delete | amend |
|---|---|---|---|---|---|---|---|---|---|---|---|
| yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | no | no |

`hrms/hrms/hooks.py` registers `permission_query_conditions` for nine doctypes and
`has_permission` for six. **Employee Performance Feedback is in neither.** There is no
row filter of any kind on it anywhere in the three apps.

Measured on production read-only on 2026-09-24: `dtc.alvoraa.co` has 302 Employee
records and 4 enabled logins; aahr has 5 records and 7 logins. Zero feedback rows on
either and **no `Custom DocPerm`**, so the JSON above is in force unmodified.

`hrms/hrms/alvoraa_org_structure/dotted_line.py:125-136` inserts feedback rows with
`ignore_permissions=True` the first time a manager puts a score on an appraisal. So the
data arrives right behind the 302 logins.

**This fault gets worse with no commit at all.** Creating the remaining 298 logins is a
data load: no diff, no CI run, no review. That is why it must land before the logins.

## 1. Functional impact

### Cross-module reach

| App / file | What it does with the doctype | Effect of the hooks |
|---|---|---|
| `hrms/hr/doctype/appraisal/appraisal.py:312` `get_feedback_history` (whitelisted) | `frappe.get_list` for one employee + appraisal | **Filtered** — this is the desk feedback panel. HR, the subject, the subject's manager and each author keep what they had; an unrelated employee now gets an empty list |
| same function, lines 330-346 | six `frappe.db.count` calls plus `frappe.db.get_value("Appraisal", ...)` | **NOT filtered** — `db.count` and `db.get_value` bypass query conditions. Residual leak: the star distribution and the average score of any appraisal, to any logged-in user. See finding F1 |
| `appraisal.py:213` `calculate_avg_feedback_score` | `frappe.qb.avg` | Not filtered, and must not be — it is the score maths, run as the system |
| `appraisal.py:253` `add_feedback` | `frappe.get_doc(...).insert()` with `reviewer` set to the caller's own Employee | Still works: the author branch allows `create` when they are the reviewer |
| `appraisal_cycle.py:278` `get_employees_without_feedback` (whitelisted, **no role gate**) | `frappe.qb` count | Not filtered. Returns one org-wide number for a cycle, no person named. Finding F2 |
| `hr/report/appraisal_overview/appraisal_overview.py:97` | `frappe.db.count` per appraisal row | Not filtered, but the report's own rows come from Appraisal, which the Employee role cannot read at all |
| `alvoraa_org_structure/dotted_line.py:125,154,185` | `frappe.db.exists` plus `insert(ignore_permissions=True)` | `db.exists` bypasses conditions and `ignore_permissions` bypasses `has_permission`, so the dotted-line flow is untouched. **To be proved by test, not assumed** |
| `dotted_line.pending_dotted_line_feedback` | `frappe.db.exists` | Not filtered, but gated by `frappe.only_for(["HR Manager","HR User","System Manager"])` |
| `alvoraa_portal`, `alvoraa_goals` | **nothing** — grep finds no reference to the doctype in either app | No effect |
| `public/js/performance/performance_feedback.js:180` | `frappe.model.can_create(...)` to show the "Add Feedback" button | Doctype-level check, unchanged. The button still appears for anyone with the Employee role; the server now decides what they may actually write |

`Appraisal` itself grants the Employee role **nothing**, so the desk Appraisal form is
already closed to ordinary staff. The portal reaches appraisals through its own
whitelisted endpoints, none of which touch this doctype.

### Persona impact

| Persona | Before | After |
|---|---|---|
| CXO (System Manager) | everything | everything — unchanged, the hook returns no filter |
| HR Manager / HR User | everything in the tenant, whatever their company or branch | only within `permitted_employees` — the same HR scope the rest of the product uses. **A store's HR person loses company-wide sight of feedback. That is the intended fix from slice 030, not a regression** |
| Manager | everything | feedback about their own direct reports, read only |
| Employee (subject) | everything, and could **edit, submit or cancel** criticism of themselves | reads what is about them; cannot write, submit, cancel, email or share it |
| Employee (author) | everything | writes, submits and cancels what they wrote |
| Unrelated employee | everything, including export | nothing |
| Leaver with an enabled login | everything | own record and own authored rows only; the direct-reports branch requires the caller's own Employee record to be Active |
| Guest | nothing (no doctype permission) | nothing, and the condition is `1=0` as well |

### HRMS domain impact

Appraisals only. Leave, attendance, payroll and org structure are untouched. The
appraisal score maths is untouched: it runs as the system through `frappe.qb`.

## 2. The rule being built

* **Author** — `reviewer` is one of the Employee records linked to the login: read,
  write, create, submit, cancel, print, email, share.
* **Subject** — `employee` is one of theirs: **read only**, whatever roles they hold.
  Feedback the subject can edit or withdraw is not feedback. This also keeps SEC-10
  ("nobody acts on their own review") true for an HR Manager who is the subject.
* **Manager** — read only, and **direct reports only**, not the whole tree, matching
  `field_app_access.checkin_query_conditions`.
* **HR** — `hrms.alvoraa_hr_core.access.permitted_employees`, matched on the subject.
  No third definition of "who may I see".
* **Everyone else** — nothing. `1=0`, never an empty string.

**Decision asked for: does a manager see feedback their report WROTE about somebody
else? No.** It is not about their report; the subject never agreed to it; and a manager
who can read their team's outgoing opinions is how honest feedback stops being given.
The dotted-line flow makes this concrete — a report may be asked to review the
manager's own peer. The manager sees it only if they are HR for that subject, or the
subject's own manager.

Two hooks, not one. The query condition filters lists, reports and **exports**;
`has_permission` guards opening one record by name, and printing, emailing or sharing
it. A list filter alone leaves `/app/employee-performance-feedback/HR-FDBK-0001` open
at its own URL. `export` and `report` are doctype-level permission types with no
document, so the controller hook is never consulted for them — the query condition is
the only thing standing there. That is why both are tested.

## 3. Non-functional verdict

| Dimension | Verdict | Why |
|---|---|---|
| Performance | **degrades slightly** | One extra `Employee` query per call for the caller's own records, one for direct reports, and for HR one more through `permitted_employees`. The HR branch puts an `employee in (...)` list of up to one id per employee in scope into the SQL — 302 ids on dtc, about 1,000 on the slice 044 scale fixture (roughly 12 KB of SQL). Accepted deliberately: one shared definition of HR scope beats a faster second definition that can drift. Measured in the implementation notes |
| Security | **improves** | The whole point. Ten actions on every record in the tenant become ten actions inside a stated scope, enforced server side on both entry points |
| Reliability | **neutral** | Hooks only deny; they cannot grant what the role rows did not. `permission_query_conditions` and `has_permission` are the framework's own extension points, so nothing upstream is patched. The dotted-line insert keeps `ignore_permissions=True` |
| Scalability | **neutral to slightly negative** | See performance. Bounded by employees in HR scope, not by feedback rows |
| Maintainability | **improves** | One new module with the reasoning in its docstring, next to the existing pair it copies. No change to `access.py`, no change to any DocType JSON |
| Data integrity | **improves** | The subject can no longer edit, submit or cancel feedback about themselves. Today they can |
| Compliance / privacy | **improves** | Minimisation and purpose limitation on the most sensitive free text in the product. Fails closed. No personal data added to any log |

## 4. What is deliberately NOT done

* **No `Custom DocPerm` row.** One row for a doctype makes Frappe ignore **all** its
  standard rows (`module_access.py:245-263`, quoting `frappe/permissions.py`), which
  would silently strip HR Manager, HR User and System Manager.
* **No edit to the doctype JSON.** Narrowing the Employee row there would be upstream
  drift on a standard Frappe HR doctype and would be reverted by an upstream merge.
  See finding F3 for the one place this leaves a gap.
* **No new doctype, no new field, no fixture, no migration.** Nothing to migrate.

## 5. Parallel-work check

`origin/dev` is `8718f27`; local `dev` is `98f0b7f` (ALV-119, a compose config line —
no overlap). Nothing incoming: `git log origin/dev..dev` is that one commit, and
`HEAD..origin/dev` is empty.

| File I will change | Hot file? | Who else is in it |
|---|---|---|
| NEW `hrms/hrms/alvoraa_hr_core/feedback_access.py` | no | nobody |
| `hrms/hrms/hooks.py` | **yes** | Slices 013 and 041 append to `after_migrate`, `doc_events` and `permission_query_conditions` in **alvoraa_portal's** hooks.py, not hrms's. No board row claims `hrms/hrms/hooks.py`. I add **one line at the end of each of the two existing dicts**, with a comment, and rewrite no block |
| `hrms/hrms/hr/doctype/appraisal/appraisal.py` | no | nobody on the board. One added permission gate in `get_feedback_history` (finding F1), as its own commit so it can be reverted alone |
| NEW `hrms/hrms/alvoraa_hr_core/tests/test_feedback_access_047.py` | no | nobody |
| NEW `docs/slices/047-feedback-permissions/` | no | nobody |

**Not on any redesign branch.** Branched straight from `origin/dev` so it can reach
`dev` on its own, ahead of 034, 042, 043 and 045.

Uncommitted work by others in the main checkout: the `mobile/field-app/android/**`
tree and four untracked `docs/` folders. None of my files. Not staged, not touched.

The board row for 047 is added. Bench: **own container `hrlocal-047` with its own redis
and its own site `test047`. `hrlocal-bench` is not used and no `docker cp` is run.**

### The pin tests

Every rule gets a test that names it, so a bad merge cannot drop it silently: ten
granted actions across ten personas, plus `export`, `report`, the record's own URL, the
dotted-line insert, and a fail-closed proof for each hook removed in turn.

## 6. Findings to report, not assume

* **F1 — `get_feedback_history` leaks aggregates.** Six `frappe.db.count` calls and one
  `frappe.db.get_value("Appraisal", ...)` bypass query conditions, so any logged-in user
  who knows an employee id and an appraisal id can read that person's star distribution
  and average feedback score. The only legitimate caller is the Appraisal desk form,
  which needs `Appraisal` read — a permission the Employee role does not have. Proposed:
  one `frappe.has_permission("Appraisal", "read", doc=appraisal)` gate at the top of the
  function. Separate commit.
* **F2 — `get_employees_without_feedback` has no role gate.** Whitelisted, `frappe.qb`,
  returns one org-wide count for a cycle. No person named. Reported, not fixed here.
* **F3 — a `DocShare` row widens lists.** `db_query.py` OR-s the share condition onto the
  permission conditions, so an author who shares a feedback record puts it in the
  recipient's list view. `has_permission` still refuses to open, print, email or share
  it, so the text is reachable only through a list `fields` request. Closing it fully
  means dropping `share` from the Employee row in the doctype JSON — upstream drift,
  outside this slice. Tested and reported.
* **F4 — `permitted_companies` does not check the HR user's own status.** A Left HR
  person with a Company User Permission keeps HR scope. Pre-existing, in shared code
  three slices depend on; not changed here.

## 7. Strategy

1. `feedback_access.py` with the two hook functions and the reasoning in the docstring.
2. Two lines in `hrms/hooks.py`, at the end of the two existing dicts.
3. The test module: personas by actions, export and report, the record URL, the
   dotted-line insert, and the fail-closed proofs.
4. F1's gate, as its own commit.
5. `scripts/check_app_integrity.py` before every commit. Own container, one test run at
   a time. No push, no merge into `dev`, no server.
