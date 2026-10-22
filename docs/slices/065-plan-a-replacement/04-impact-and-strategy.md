---
slice: 065-plan-a-replacement
artifact: 04-impact-and-strategy (change-process steps 1 and 2; the engineer's 00-impact-analysis for this slice)
author: hrms-fullstack-engineer
date: 2026-10-22
status: proposal - waiting for Surbhi's approval. No feature code written, nothing committed, nothing pushed, no server touched.
inputs: 00-decisions.md (wins), 01-product-brief.md, 01c-security-privacy-requirements.md (SEC-1..7, PRIV-1..6; a revision is in progress - where it conflicts with 00-decisions, the decisions win), 02-design.md, prototype-v2.html (v3 in progress), 03-functional-spec.md v2 (22 stories, 74 ACs, 57 parity rows)
code read: worktree 064-organogram, branch slice/064-organogram at a9c00b95 (register.py, hiring.py, api.py, settings.py, hooks.py, portal.js Positions section, the two position doctypes, test_portal_security_010.py CEILINGS); worktree 060-manager-review (read-only); Frappe source on the local bench, v16.33.1 (988e54f): model/delete_doc.py, permissions.py, share.py, desk/form/assign_to.py, desk/form/document_follow.py, desk/form/linked_with.py, desk/doctype/tag/tag.py, core/doctype/file/file.py, core/doctype/custom_docperm, utils/background_jobs.py, core/doctype/scheduled_job_type
measured: position_table on site test064 (container hrlocal-064), read-only; synthetic people added inside one transaction and rolled back - 0 rows left, checked
---

# 065 · Impact analysis and strategy: Plan a replacement

## 0 · Bad news first

1. **Two places the spec does not cover would leak a plan, and one would keep a copy after the
   erase.** I found them in Frappe's own code. Neither is built yet, so nothing leaks today.
   - **"Linked documents" tells people a plan exists.** Frappe's `frappe.desk.form.linked_with.get`
     is open to anyone who can read a seat assignment. It counts every record that links to that
     assignment with **no permission check** (`linked_with.py:498-506`, `frappe.get_all`), and returns
     the hidden ones as `hidden_count`. With the spec's `assignment` **Link** field, an HR Manager who
     is the subject can ask about their own assignment and get "Replacement Plan: 1 hidden". That
     breaks decision 9. The same call works for anyone else who can read assignments.
     *Fix I recommend:* store the assignment's id in a plain text (Data) field, not a Link. Frappe
     then never finds the plan as a "linked document". This also removes risk RK-5 (the
     "cannot delete, linked with Replacement Plan …" message). It changes AC-1 and PRIV-1's wording
     (Question 1).
   - **A tag outlives the plan.** Anyone who can open a plan can tag it. The tag link is erased with
     the plan, but the tag's own name (say "Ritu resigning") stays in Frappe's tag list for ever and
     is offered to every user as a suggestion (`tag.py:88-95`). *Fix:* refuse tags and file
     attachments on a plan, with the same small hook that refuses comments, to-dos and shares
     (Question 2).
2. **065 has to be built on top of 064's branch, which is not on `dev` yet.** 065 changes
   `position_table` and the Positions screen code, and 064 is rebuilding that same screen code
   (prototype-v9) right now. I can build the whole server side now. **The screens should wait until
   064's chart code is final**, or the two slices will fight over the same functions (Question 3).
3. **Taking a plan back needs Delete rights on a plan that is already hidden.** When HR sets a new
   plan on a person whose old plan has lapsed but not yet been erased, the old record must go first
   (the database allows one plan per assignment). The gate hides lapsed plans, so HR's own delete
   would be refused, and the only other way is a permission bypass, which SEC-7 forbids. My answer:
   the gate allows **delete only** on a hidden plan, for an HR Manager in scope who is not the
   subject. Nobody can read it that way (Question 4).
4. **No DevOps inputs (`07-devops-inputs.md`) exist for this slice.** The spec already marks this
   as its one failed Ready box. The daily job's worst-case run time is my estimate, not DevOps's.
5. **I measured the chart call without plans only.** The plan table does not exist yet, so the
   "with plans" numbers below are worked out from the code I will write, not measured. They will be
   measured in the build (check B-8).

---

## 1 · Impact analysis

### 1.1 Parallel-work check (done before this analysis)

| Check | Result |
|---|---|
| `git fetch origin` | `origin/dev` is at `76f15e1d`. **Nothing new came in.** The 064 branch is 23 commits ahead of `origin/dev` and 0 behind |
| Base for 065 | `slice/064-organogram` at `a9c00b95` (not `origin/dev`): 065 needs 064's seat sheet, Filters box, groups and `post_job` hand-off |
| Main checkout | On `dev`. Not touched |
| This worktree (060-manager-review) | Holds other sessions' uncommitted edits (`.claude/context/definition-of-ready-done.md`, `ux-learnings.md`) and the untracked 063/064/065 slice docs. **Not mine; not touched.** I add only this file |
| Work board | 064 owns `register.py` (`position_table`, `_scope`), `hooks.py` (Employee and Job Opening lines), portal.js Positions section, `panels.css` Positions block, both `scripts/*positions*` checks, `test_portal_security_010.py` CEILINGS. 063 owns `hooks.py` leave blocks, portal.js leave block, CEILINGS rows. 064's container `hrlocal-064` is running for its UI rework |
| Other developers | I cannot see other machines. **Surbhi: is anyone else working in `register.py`, `hooks.py` or the Positions screen?** |

**Files 065 would change**

| File | New or changed | Hot? | Who else is in it | Plan |
|---|---|---|---|---|
| `hrms/.../alvoraa_org_structure/doctype/replacement_plan/` (json, py, `__init__`) | New | DocType JSON (hot rule: one slice per DocType) | Nobody | Claim on the board |
| `hrms/.../alvoraa_org_structure/plans.py` | New | No | Nobody | - |
| `hrms/.../alvoraa_org_structure/register.py` | Changed: `position_table` (one call into `plans.py`, and the `opening` rule), `AUDITED` (one name) | Yes for 064 | **064** | **Sequence**: built on 064's branch; rebase whenever 064 moves |
| `hrms/hrms/hooks.py` | 7 new lines (below) | Yes | 063 (leave blocks), 064 (Employee, Job Opening) | **Split**: new keys and new lines at the end of each block, nothing rewritten |
| `alvoraa_portal/.../public/js/ess/portal.js` | Positions section only, new `posPlan*` functions plus small edits in `posSeatBox`, `posWho`, `posOutline`, `posMatches`, `posPaintTiles`, `posPaintPeople`, `posPeopleActions` | Yes | **064, actively** | **Sequence**: screens start only after 064's v9 chart code is final |
| `panels.css` (Positions block), `parts/positions.html` (one line under Filters) | Changed | Yes for 064 | **064** | Sequence, as above |
| `scripts/check_positions_tree.js`, `scripts/browser_check_positions.js` | New sections at the end | 064's | **064** | Sequence; new sections only |
| `alvoraa_portal/.../tests/test_portal_security_010.py` | 2 rows at the end of CEILINGS | Yes | 063, 064 | Rows at the end |
| `hrms/.../alvoraa_org_structure/tests/test_replacement_plan_065.py` | New | No | - | - |
| `DEPLOYMENT_RUNBOOK.md` | One step in the restore section | No | - | - |

**Pin tests that keep existing features alive:** 064's own tests (`test_positions_064.py`,
`test_register_194.py`, `test_register_fill_194.py`) run unchanged, and 064's "no plan word anywhere"
check (`check_positions_tree.js:378`) is changed to run as a non-reader, not deleted. 065's new file
names every feature it adds (one test per AC group), so a bad merge that drops one fails.

### 1.2 Functional: cross-module reach

| App | Touched? | How |
|---|---|---|
| `hrms` (our org-structure code) | **Yes** | New DocType; new `plans.py`; `register.py` (one call, one name); `hooks.py` (7 lines) |
| `alvoraa_portal` | **Yes** | Positions screen code; two CEILINGS rows |
| `frappe` | **No edits.** Five of its doctypes get a `validate` hook from our `hooks.py`: Comment, ToDo, DocShare, Tag Link, File. Each costs one comparison of a doctype name; nothing is read | Every comment, to-do, share, tag and upload in the whole system passes through it, so it is pinned by tests that a normal comment still saves |
| `hrms` (Frappe HR's own code) | No edits | Job Opening made through our existing `post_job` |
| `alvoraa_goals` | No | It has its own permission hooks on **Comment** (`comment_query`, `has_review_history_permission`). Mine is a `validate` hook, a different event; they do not meet |
| `erpnext`, `alvox_compensation` | No | Nothing reads plans. SEC-7's occurrence test makes sure of it |

### 1.3 Functional: every caller of what I would change

| Function | Change | Callers (grep, 064 branch) | Effect on them |
|---|---|---|---|
| `register.position_table` | Adds `plans` and `plan` keys for plan readers only; sends `opening` empty on a **full** seat to non-readers | `portal.js:329`; tests `test_positions_064.py` (11 calls), `test_register_194.py` (17), `test_register_fill_194.py` (9); `scripts/check_positions_tree.js` (stubbed reply) | Readers' existing keys unchanged. `test_register_fill_194.py:296-314` reads `opening` as an HR Manager - a plan reader - so it still passes. No test asserts the exact top-level key set (checked) |
| `register.record_permission_change` | Only `AUDITED` gains the doctype name | `hooks.py:323-324` (Custom DocPerm on_update/on_trash) | Role Permissions Manager changes on plans get a Version, like Positions |
| `register.post_job` | **Unchanged** | `portal.js:1244, 1522`; tests | The request calls it with `vacancies` 1, `publish` 0, no description |
| `settings.alert_on_long_cover` | **Not scheduled, not touched** | none | F1 stays dormant |

New functions (no existing callers): the doctype controller, and in `plans.py` the gate, the list
condition, the permission check, `set_plan` / `confirm_plan` / `remove_plan`, the erase function,
the daily job with its self-check, the side-record refusal and the careless-grant refusal.

### 1.4 Personas

| Persona | What changes |
|---|---|
| **CXO** (System Manager stands in) | Reads plans on seats in scope, all companies they act for. Cannot set, confirm, remove, or request because of a plan (decision 10) |
| **HR Manager** | Sets, confirms, removes plans; requests an unadvertised opening. Never sees a plan about themselves |
| **Owners** (DTC: Org Structure Editor) | Option on: read plans, no buttons. Option off: nothing at all |
| **Store head / other Positions reader** | Nothing new. **One loss:** on a full seat they no longer get the link to an open job opening (SEC-4.3). At DTC nobody is in this group today |
| **HR User** | Sees the unpublished Job Opening in the Job Opening list (decision 8, accepted with a warning) |
| **Employee** | Nothing, on any screen. The Organisation page (`api.py`) is not touched |

**HRMS domains:** org structure (core), recruitment (unpublished Job Opening). Not touched: leaves,
attendance, payroll, appraisals, PMS, goals, compensation.

### 1.5 Measured numbers (and what is estimated)

Measured on `test064`, 120 seats (DTC has 90), as a real HR Manager and a real System Manager, after
one warm-up call. People raised to 1,000 Active (964 in seats) by synthetic rows inside one
transaction, then rolled back; 0 rows left. Query counts and bytes only - wall-clock times on this
machine are not reliable (change-process rule 5).

| `position_table` reply | Queries | Bytes |
|---|---|---|
| HR Manager, 149 people in seats | **6** | 61,715 |
| HR Manager, 964 people in seats | **6** | 194,535 |
| System Manager, 149 people | **7** | 65,266 |
| System Manager, 964 people | **7** | 198,087 |

**With plans (estimated from the design, to be measured in check B-8):**

| Reader | Extra queries | Extra bytes |
|---|---|---|
| Plan reader (HR Manager, owner-on, System Manager) | **+4 to +6, the same at 1 plan or 400 and at 150 or 1,000 people**: the reader's own Employee status (1), the plan list with its permission condition (1-2), "do owners see plans" (1), the names of who set and confirmed (1), which of them hold HR Manager (1, only when a plan exists) | about 60 for the `plans` key, plus 250-450 per live plan (the note is at most 200 characters). 20 plans: about +7 KB on 195 KB |
| Everyone else | **0** in the normal case (the gate fails on the cached role list before any query) | **0** - the reply is byte-for-byte the same with and without plans |

So an HR Manager's chart call goes from 6 to about 10-12 queries, flat in headcount and in plans.
Budget (nfr-budget §2): bounded and the same for 20 people as for 1,000. Met.

Other costs: set, confirm and remove are one save or one erase each (about 10-15 statements for an
erase, all on one record). The daily job is one grouped query to find what is due, plus one erase
per due plan, plus one self-check of about 10 counts. The five side-record hooks read nothing.

### 1.6 The seven non-functional dimensions

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **degrades, slightly** | The chart call gains about 4-6 fixed queries and a few KB for plan readers; zero for everyone else. Every comment, to-do, share, tag and upload pays one name comparison |
| **Security** | **degrades, slightly, then guarded** | A new record holding a judgement about a named person is new attack surface. It is guarded on every door I could find: desk, REST, `get_list`/`get_count`, link search, linked documents (Data field), comments, assignment, share, tag, attach, follow, print/export/email, careless grants. One improvement: the job-opening link on a full seat stops reaching non-readers (01c F4) |
| **Reliability** | **neutral** | New daily job: each plan erased in its own savepoint, a failure logged by plan name only, a self-check that raises a titled alert the control plane already collects. Lapsed plans are hidden on read, so a stopped job never shows one. Risk: a bug in the side-record hook would block every comment in the system - pinned by a test that a normal comment still saves |
| **Scalability** | **neutral** | Every query is flat in headcount and in plan count. The list condition keeps the scope inside the database (a sub-query), never a list of ids sent back as `IN (...)` |
| **Maintainability** | **degrades** | One new DocType, one new module (about 250 lines), 7 hook lines, about 350 lines of screen code on a screen 064 has just rebuilt. Kept to one module and one gate function |
| **Data integrity** | **neutral** | "Live" is worked out on every read from dates and statuses, never stored. One plan per assignment is a unique index, so two HR Managers saving at once cannot make two. No cache anywhere, so nothing to go stale |
| **Compliance / privacy** | **degrades inside the system, by design; improves against today's habit** | It writes down sensitive data that today lives in WhatsApp. Controls: tiny audience, hidden from the subject, no history, a real erase, 90-day life, erased within a day of leaving, ids-only log lines, no email ever. Open with counsel: C1-C4 |

---

## 2 · The strategy

**Rung of the ladder: 5, a new DocType.** Every cheaper rung was rejected in the brief and 01c, and
I checked each again:
- *Already there / configuration:* nothing in Frappe HR holds a private note on a seat. PMS Talent
  Flag is a performance record; Job Requisition is readable by HR User.
- *Custom field on the assignment:* the assignment keeps change history (`track_changes: 1`), so the
  note could never be erased.
- *New code without a DocType:* there is nowhere to store it.

Inside the DocType, everything else is rung 4 (hooks and functions in our own app). No new page,
report, setting, role, cache or app.

### 2.1 Thin steps, in order. Each one stays green.

Each step is one commit (or two), with its tests, on branch `slice/065-plan-a-replacement` in
worktree `.claude/worktrees/065-plan-a-replacement`, cut from `slice/064-organogram`. Tests run in a
throwaway container `hrlocal-065` with its own site `test065` - never `hrlocal-bench`, which runs
the main checkout.

**Step 1 · The record (US-1).** DocType "Replacement Plan", module Alvoraa Org Structure.
- Fields: `assignment` (**Data**, mandatory, unique, set only once - see Question 1), `confirmed_on`
  (Date, mandatory, read only), `note` (Small Text, set only once).
- Settings: `autoname: hash` (random name); `track_changes` 0, `track_views` 0, `track_seen` 0;
  `allow_import` 0, `allow_rename` 0; no `title_field`; no field in global search; no web view; no
  `email_append_to`.
- Shipped permissions: HR Manager Read, Write, Create, Delete; System Manager Read. No Export,
  Print, Email, Share, Report or Import for anyone.
- Controller: `no_feed_on_delete = True` (so Frappe never writes its "Deleted" comment). `validate`
  holds every SEC-5 rule: note at most 200 characters (counted on the server); `confirmed_on` may only
  ever be today; the assignment exists, has started, has not ended, its Employee is Active, its seat
  is not Closed and is in the writer's scope; not the writer's own assignment. `on_trash` refuses
  any delete that did not come through the erase function: "Use Remove the plan".
- Tests: AC-1, AC-2, AC-4, the SEC-5 refusals that need no gate (AC-6 server half, AC-10 set_value).

**Step 2 · One gate for every door (US-12, US-16; SEC-1).** In `plans.py`, the same hook pair as the
ALV-117 feedback guard (`hooks.py:155-181`):
- `permission_query_conditions["Replacement Plan"]` returns a SQL condition for every list, count,
  report, link search and REST list. For a reader it is one `EXISTS` sub-query: the plan's
  assignment exists, has started, has not ended, its Employee is Active, its seat is not Closed,
  the seat's company (and branch, for a store-tied reader) is in the reader's scope, the assignment
  is not the reader's own, and `confirmed_on` is within the last 90 days. Values are escaped with
  `frappe.db.escape`, as `feedback_access.py` does. For anyone who fails the gate it returns
  `1=0`, which does not depend on the data, so a count is 0 whether plans exist or not.
- `has_permission["Replacement Plan"]` guards one record: print, email, export, share, report and
  import are refused for everyone; a reader may read or write a live plan in scope that is not their
  own; may create (the controller checks the rest); and may **delete** a plan in scope that is not
  their own **even when it is hidden** (Question 4) - delete never shows the plan.
- **Who is a reader** (one function, used by both hooks and by `position_table`): Frappe Read on
  Replacement Plan through a role that is **not** broad (`All`, `Guest`, `Desk User`, `Employee`,
  `Employee Self Service`) - checked with Frappe's `get_valid_perms`; may open Positions
  (`may_view`); and, if linked to an Employee, that Employee is Active.
- Tests: AC-52 to AC-56, AC-64, AC-46 "hidden before the job runs".

**Step 3 · No side doors (US-14, US-15; SEC-2, SEC-3).**
- One function, registered as `validate` on **Comment, ToDo, DocShare, Tag Link and File**, refuses
  any row that points at a Replacement Plan. This stops comments and @mention emails, "Assign to"
  (its to-do, its automatic share and its email), "Share", tags (and the tag name left behind) and
  attachments. Following is already refused by Frappe because the record has no change history
  (`document_follow.py:54`).
- Careless grants: a new `validate` hook on Custom DocPerm refuses, for this doctype only, any right
  for a broad role and any tick of Export, Print, Email, Share, Report or Import. `AUDITED` gains the
  doctype, so every allowed change (Read for Org Structure Editor) writes a Version naming the role.
  I checked that Role Permissions Manager saves through the document (`custom_docperm.py:44-47`,
  `permissions.py:699-725`), so the hook fires.
- Tests: AC-62 (plus tag and attach refused), AC-63, and "a normal comment on an Employee still saves".

**Step 4 · The erase path and the three calls (US-2, US-4, US-5, US-11, US-17; PRIV-2, PRIV-4).**
- **One erase function.** It calls `frappe.delete_doc("Replacement Plan", name,
  delete_permanently=True, flags={...})` - so no "Deleted Document" copy (`delete_doc.py:225`) -
  then runs Frappe's own `delete_dynamic_links` **in the same transaction** instead of trusting the
  job Frappe queues after the commit (`delete_doc.py:200-208`). Tags, files and the global-search row
  are already removed inside `delete_doc`. No feed comment (`no_feed_on_delete`). Then one
  security-log line.
- **Three calls, POST only** (`@frappe.whitelist(methods=["POST"])`), each running as the user,
  with no permission bypass:
  - `set_plan(assignment, note)`: erases a hidden record on that assignment first (the database
    allows one), then inserts. Two HR Managers saving at once: the unique index refuses the second,
    who gets "Someone else changed this plan a moment ago. Here is the latest."
  - `confirm_plan(plan)`: sets `confirmed_on` to today. Refused when the plan is no longer live.
  - `remove_plan(plan)`: checks delete rights, then the erase function.
- **Log lines (PRIV-4):** one JSON line per set, confirm, remove and erase, in the same shape as
  `settings._log_access_change`: event, time, user, doctype, the plan's random name, a reason word.
  Never the note, the employee, the seat or the assignment.
- **Who set and confirmed (Y-2 stopgap):** from Frappe's own `owner` and `modified_by`. No new field.
- Tests: AC-3, AC-5 to AC-11 (server half), AC-18 to AC-24, AC-26, AC-51, AC-66.

**Step 5 · The daily lapse job (US-10, US-19; PRIV-3).**
- **One line** at the end of `hooks.py` `scheduler_events["daily"]`:
  `"hrms.alvoraa_org_structure.plans.erase_due_plans"`. **`alert_on_long_cover` is not scheduled.**
- One grouped query finds every plan that is due, with its reason (lapsed, left seat, left company,
  seat closed). It reads names and reasons only, **never the note**, so no traceback can carry one.
- Each plan is erased inside its own savepoint. A failure rolls back that one plan, writes
  `frappe.log_error(title="Replacement plan erase failed", message=<plan name>)`, and the job moves
  on. Nothing is allowed to escape the job, because Frappe stores a failed job's traceback **with its
  local variables** (`scheduled_job_type.py:182`).
- Self-check after each run: counts of (a) plans more than 2 days past an erase condition, (b)
  Version, Comment, DocShare, ToDo, Document Follow, Tag Link, Deleted Document rows that point at
  the doctype, (c) Notification, Webhook, Auto Email Report, Assignment Rule rows that name it. Any
  non-zero count: one Error Log titled "Replacement plan self-check failed", counts only. The control
  plane already collects Error Log titles (`health.py:68-92`).
- The same self-check is the **release check** (AC-50): `bench --site <site> execute
  hrms.alvoraa_org_structure.plans.self_check` returns the counts.
- The job runs as the scheduler's user. Frappe's worker connects as Administrator
  (`frappe.connect`, `__init__.py:281`), so it needs no bypass. Proven by check B-4, not assumed.
- Tests: AC-46 to AC-49.

**Step 6 · The chart reply (US-13; SEC-4).** In `position_table`, one call into `plans.py`:
- **Only** when the reader passes the gate **and** `as_at` is today: a top-level `plans` key
  (`may_set`, `owners_see`), and on each person whose assignment has a live plan a `plan` object with
  exactly `name, set_on, set_by, confirmed_by, confirmed_on, lapses_on, note`. `set_by` and
  `confirmed_by` are display text written by the server ("you", or "{full name} (HR Manager)", or the
  full name) - never a user id or email.
- The plans are read with `frappe.get_list` (so the gate's condition applies), never `get_all`.
- For everyone else the keys are **absent**, not false or empty, and on a **full** seat `opening` is
  sent empty. Nothing else changes: row order never depends on a plan (the browser puts planned
  people first), no count includes a plan, nothing is cached.
- Tests: AC-57 (byte-for-byte), AC-58, AC-59, AC-65, and the query count equal at 20 and 200 people
  with 0 and 50 plans.

**Step 7 · One place only (US-18; SEC-7, PRIV-5).** A test walks every Python and JS file in our apps
and fails if the words "Replacement Plan" appear anywhere other than the plan's own module and
doctype folder, `register.py`, `hooks.py` and tests. CEILINGS rows: `plans.py` 0 and the doctype
controller 0. Tests: AC-67, AC-68.

**Step 8 · 064's "no plan anywhere" check becomes a non-reader check.** It is changed, not deleted
(`check_positions_tree.js:378`; the 065 spec calls it 064 AC-75, the 064 spec copy calls it AC-81 -
the analyst should align the number).

**Step 9 · The marks on the chart (US-6, US-7, US-8), built on 064's final v9 code.**
- The flag before a name (an image spoken "Replacement planned"), planned people first (in the
  browser), the 4 px red left edge on the planned person's own seat box and phone row only - never on
  a group, strip or branch box - and "· ⚑ replacement planned" on the phone row.
- Two Show options inside the Filters box for plan readers with marks shown; choosing one greys
  non-matching seats and opens the path to each match, as v9's filters do.
- **Tiles ignore the two plan options** (Y-6 stopgap), so a tile can never become a count of plans.
- The line under Filters: the flag, "Replacement planned for this person. Only HR and owners see
  this." (option off: "Only HR sees this."), and "Hide replacement plans (before you share your
  screen)". Hiding removes every mark, clears a chosen plan option, and is **not remembered** between
  visits (no `localStorage`).
- Print: every plan element carries one private class that a print rule removes; the red edge exists
  only on screen.
- Phone: one CSS line makes every sheet button at least 44 px, v9's own Close included.
- Tests: AC-27 to AC-37, AC-73 in `check_positions_tree.js` and `browser_check_positions.js`.

**Step 10 · The seat sheet, the dialogs and "Request a replacement" (US-2, US-3, US-4, US-5, US-9).**
- The plan block, `Plan a replacement` (never on the reader's own row, not while marks are hidden),
  Confirm (no dialog), Remove (asks first), the plan dialog with the 200-character counter, and
  **Surbhi's reworded promises**, not prototype-v2's words.
- **"Request a replacement"** on a full seat with no open opening and a job role, when either the
  reader may set plans and a person there has a live plan and marks are shown (Y-5 stopgap), or a
  person there has a leaving date the reader already receives (Y-3, as drawn). The dialog shows the
  "Before you do" warning first (decision 8). It calls the existing `post_job` with `vacancies` 1,
  `publish` 0 and **no description**, and opens the opening in a new tab as today
  (`portal.js:1254`). Nothing links the opening and the plan.
- **Leak rule:** a non-reader's footer is identical with and without a plan, because they never get
  a `plan` key and get `opening` empty on a full seat.
- The "To start hiring now…" sentence appears only when the button is on the sheet (Y-7 stopgap).
- Character count: the browser's `maxlength` counts emoji as two, the server as one, so the browser
  may stop a little early but **never lets through what the server refuses** (answers OQ-8).
- Tests: AC-5 to AC-9 (browser half), AC-12 to AC-25, AC-38 to AC-45, AC-74.

**Step 11 · The runbook and the release note (US-21, US-22, US-19, US-20).**
- `DEPLOYMENT_RUNBOOK.md`, restore section: "After restoring a tenant, run `bench --site <site>
  execute hrms.alvoraa_org_structure.plans.erase_all_plans`, then tell HR to set any plan still
  needed." (`erase_all_plans` uses the same erase function for every plan; it is not whitelisted.)
- Release note: the new daily line and its check (the Scheduled Job Type exists, the scheduler is on,
  `self_check` returns zeros); order 061 → 064 → 065; DTC's owners' Read row only on Surbhi's word,
  after 064's HR Manager Read and Write row.

### 2.2 The permission-bypass budget

| File | `ignore_permissions` now | After 065 | CEILINGS row |
|---|---|---|---|
| `plans.py` (new) | - | **0** | new, 0 |
| `doctype/replacement_plan/replacement_plan.py` (new) | - | **0** | new, 0 |
| `register.py` | 4 | **4** | unchanged |
| `hiring.py` | 1 | 1 | unchanged |
| `hooks.py` | not counted | - | - |

The erase from `set_plan` and `remove_plan` runs as the HR Manager, who holds Delete (with Question
4's rule). The daily job and `erase_all_plans` run as Administrator. Nothing needs a bypass.

### 2.3 Tests per requirement

| Requirement | Test (AC) | Runs as |
|---|---|---|
| SEC-1 one gate | AC-52, 53, 54, 56, 64; `linked_with.get` returns no plan (new) | each named user, never Administrator |
| SEC-2 careless grants | AC-2, AC-63 | System Manager |
| SEC-3 side doors | AC-62 + tag and attach refused (new) + a normal comment still saves | HR Manager, owner-on |
| SEC-4 the reply | AC-57 (byte-for-byte), 58, 59, 60, 61, 31, 37 | store head, owner-off, HR Manager |
| SEC-5 rules in the record | AC-4, 6, 9, 10, 66 | HR Manager, owner-on, System Manager |
| SEC-6 the opening | AC-40, 41, 26 | HR Manager |
| SEC-7 one place | AC-67 (occurrence test, broken on purpose to prove it fails), CEILINGS | - |
| PRIV-1 least data, no history | AC-1, AC-3 | HR Manager |
| PRIV-2 real erase | AC-23 with `frappe.enqueue` patched to do nothing; AC-24 | HR Manager |
| PRIV-3 lapse and erase | AC-46, 47, 48, 49, 50 | scheduler (Administrator) |
| PRIV-4 log lines | AC-51 | HR Manager, scheduler |
| PRIV-5 one purpose | AC-67, 68 | - |
| PRIV-6 restore | AC-71 (runbook line; `erase_all_plans` leaves the 13 places empty) | Administrator |

Every guard is broken once on purpose during the build to prove its test can fail.

### 2.4 Bench checks I will run (own container `hrlocal-065`, site `test065`; never production)

| # | Check | What proves it |
|---|---|---|
| B-1 | Comment with @mention, `assign_to.add`, `frappe.share.add`, `add_tag`, file upload on a plan | Each refused; 0 Comment, ToDo, DocShare, Tag Link, Tag, File, Email Queue rows; `follow_document` returns False |
| B-2 | A normal delete keeps a "Deleted Document" copy; the dedicated path does not | With the `on_trash` refusal switched off for the check, a plain `frappe.delete_doc` writes a Deleted Document row (so the test can fail); the erase function writes none |
| B-3 | Nothing is left in the **13** places: Replacement Plan, Deleted Document, Version, Comment, DocShare, ToDo, View Log, Document Follow, Notification Log, Tag Link, File, `__global_search` (the spec's 12) **plus Tag** (the tag name) | Counts all 0 after an erase with `frappe.enqueue` patched to a no-op |
| B-4 | The scheduler's user | Run the daily event through the real worker in the container; the log line's `user` is Administrator |
| B-5 | `frappe.desk.form.linked_with.get` | With a Link field the subject sees `hidden_count: 1`; with the Data field, no plan at all (proves Question 1) |
| B-6 | `validate` on Comment fires for `add_comment`'s insert without permissions | B-1's comment is refused |
| B-7 | One savepoint per plan on MariaDB | One erase forced to fail; the others are erased; one Error Log, name only |
| B-8 | Query count and bytes | `position_table` at 120 seats, 150 and 1,000 people, 0 and 50 plans, three personas; non-reader reply byte-identical |

---

## 3 · Risks, trade-offs, and what I would not build

### 3.1 Risks

| # | Risk | What I do about it |
|---|---|---|
| R-1 | 064 changes its chart code again after 065's screens are built | Screens wait for 064's final v9 (Question 3); rebase on every 064 change; parity rows re-walked |
| R-2 | A bug in the side-record hook blocks every comment, share, tag or upload in the system | The hook only compares one field; a pin test proves a normal comment, share and upload still work |
| R-3 | The daily job stops at a tenant (scheduler off) | Plans stay hidden anyway; the release check and the self-check alert catch it |
| R-4 | 065 reaches DTC before 064's HR Manager rows: only owners and the System Manager would see plans | Release order in the note; AC-70 |
| R-5 | A Webhook, Report or Server Script made on the desk reads the table | Plan readers only could make one, and the self-check counts Webhooks. Reports and Server Scripts are not counted today (Question 6) |
| R-6 | The subject sees "a plan changed somewhere" through Frappe's live list refresh if they have the plan list open on the desk | Carries only the random name; their own plan never appears in the list. Accepted (01c W3) |
| R-7 | Using a Data field instead of a Link loses Frappe's built-in "does this assignment exist" check | The controller checks it on every save, which it must do anyway for "current" and "Active" |

### 3.2 Two findings outside this slice (reported, not fixed here)

| # | Finding | Where | Live? |
|---|---|---|---|
| N-1 | `linked_with.get` tells anyone who can read a record how many hidden records link to it, for **every** doctype guarded by a permission hook (PMS records, feedback, policy). Same family as 01c F2 | Frappe `desk/form/linked_with.py:498-517` | Mechanism read in code; which of our guarded doctypes it exposes I did not check. Owner: a separate ticket |
| N-2 | `frappe.desk.doctype.tag.tag.add_tag` is whitelisted and checks no permission: any login can tag any record whose name it knows | Frappe `tag.py:35-40, 88-95` | Upstream Frappe; random names make it hard to use. Report only |

### 3.3 What I would NOT build

- A hook on Employee or on `end_assignment` to erase at the same moment someone leaves. Hidden at
  once and erased within a day is what Surbhi accepted, and it needs no bypass.
- A setting or page for "owners see plans". It is one permission row in Role Permissions Manager.
- A `confirmed_by` field. Frappe's `modified_by` already holds it.
- A list, report, export, tile, count or dashboard of plans. An email, bell or reminder.
- Editing a note. Remove and set again.
- A cache of any kind.
- A link from the job opening to the plan.
- Scheduling `alert_on_long_cover`.
- "Print this view" (064 decision 4: later).
- Fixing N-1, N-2 or 01c F2 for other doctypes. Separate tickets.

---

## 4 · Size and commit plan

**About 2,000 lines, half of them tests. About 4-5 working days**, in two halves.

| # | Commit | Stories | Rough size |
|---|---|---|---|
| 1 | Replacement Plan record: three fields, no history, rules in the record | US-1 | 120 + 150 test |
| 2 | One gate for every door (list condition + permission check) | US-12, US-16 | 150 + 250 test |
| 3 | No comments, assignments, shares, tags or files on a plan; careless grants refused | US-14, US-15 | 60 + 150 test |
| 4 | Set, confirm and remove; one erase that leaves nothing behind; log lines | US-2, 4, 5, 11, 17 (server) | 130 + 250 test |
| 5 | Plans end by themselves: one daily line, self-check | US-10, US-19 | 90 + 150 test |
| 6 | The chart reply carries plans only for readers | US-13 | 60 + 150 test |
| 7 | Plans are read in one place only (occurrence test, CEILINGS rows) | US-18 | 10 + 60 test |
| 8 | 064's "no plan anywhere" check runs as a non-reader | US-22 | 10 |
| 9 | Flag, red edge, Show options, hide and print on the chart | US-6, 7, 8 | 200 JS/CSS + 120 check |
| 10 | Plan block, dialogs and Request a replacement on the seat sheet | US-2, 3, 4, 5, 9 (screens) | 250 JS + 120 check |
| 11 | Restore step in the runbook; release note | US-21, US-22 | 20 |

**Build now (server side, commits 1-8, 11):** US-1, US-4, US-5, US-10, US-11, US-12, US-13, US-14,
US-15, US-16, US-17, US-18, US-19, US-21, and the server half of US-2 and US-9. None of these is
touched by an open disagreement, and none touches 064's screen code.

**Wait:** the screens (commits 9-10: US-2, US-3, US-6, US-7, US-8 and the screen half of US-5 and
US-9) until 064's v9 chart code is final and its crash is fixed. US-20 (DTC owners' row) and US-22
(release order) are release steps that wait for Surbhi's word at the time.

---

## 5 · Questions for Surbhi before I build

1. **Store the assignment as plain text, not a Link?** A Link lets Frappe's "linked documents" call
   tell an HR Manager that a plan exists about them, and tell anyone else who reads assignments.
   Plain text closes that and removes the "cannot delete, linked with Replacement Plan" message.
   The cost: the record checks the assignment exists itself (it must anyway). *My recommendation:
   plain text.* It changes AC-1 and PRIV-1's wording; the security engineer should agree.
2. **Refuse tags and file attachments on a plan?** A tag's name stays in Frappe for ever and is
   suggested to everybody. *My recommendation: refuse both, with the same hook as comments.* AC-23's
   test then proves tags and files are refused, instead of attaching them first.
3. **Build 065 on 064's branch, server side now, screens after 064's chart is final?** *My
   recommendation: yes.* Otherwise both slices edit the same screen functions at the same time.
4. **Let an HR Manager in scope delete a plan that is already hidden (lapsed, not yet erased)?**
   Needed so "Plan a replacement" works on someone whose old plan lapsed today, without a permission
   bypass. Nobody can read a hidden plan this way, and the subject is still refused. *My
   recommendation: yes.*
5. **The open screen questions (Y-5, Y-6, Y-7, Y-8):** may I build the spec's stopgaps now - no
   request button from a plan while marks are hidden; tiles ignore the plan options; "To start hiring
   now…" only when the button shows; "Ends in 0 days" as drawn? Each is a one-line change if you
   answer differently later.
6. **Should the daily self-check also count saved Reports and Server Scripts that name the plan
   record?** Two more counts in the same check. *My recommendation: yes* - it is how we would notice
   a desk-made report reading plans.

Not for Surbhi, but needed before release: DevOps's `07-devops-inputs.md` (job timeout, backup
retention for C3); the security engineer's answers to OQ-1, OQ-2, OQ-4; the analyst aligning 064's
AC number for the "no plan anywhere" check.

---

## Subtract pass

Removed on this pass:
- A separate "erase stale plan" bypass in `set_plan` - replaced by Question 4's delete rule, so the
  bypass count stays 0.
- A Custom DocPerm refusal inside `record_permission_change` - a separate `validate` line is clearer
  and keeps `register.py`'s change to one name and one call.
- A `confirmed_by` field and an "is live" stored flag - worked out from Frappe's own columns on read.
- Same-moment erase hooks on Employee and on the assignment.
- Wall-clock timings - not reliable on this machine; counts and bytes only.

Kept, and why: the byte-for-byte reply test (the only test that catches a hint nobody thought of);
the self-check (otherwise a stopped job goes unnoticed); refusing tags and files (otherwise the erase
is not complete); the Data field (otherwise the subject can find their own plan).

## Assumptions

- `[ASSUMPTION]` 064 ships as its v9 build, with decision 5's HR Manager rows, before 065.
- `[ASSUMPTION]` "Today" is the site date everywhere (Asia/Kolkata).
- `[ASSUMPTION]` Frozen seats keep their plans; only Closed ends them (spec).
- `[ASSUMPTION]` Frappe 16.35 on DTC behaves as the local 16.33.1 in the code paths named here; 01c
  confirmed the delete path on 16.35, I did not check `linked_with.py` or `tag.py` there.
