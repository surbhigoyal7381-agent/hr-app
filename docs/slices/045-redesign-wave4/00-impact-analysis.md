---
slice: 045-redesign-wave4
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-09-24
status: strategy proposed — build started on the five defect fixes, which the brief named
  as independent early commits. Local only: no push, no merge into `dev`, no server.
inputs: [02-functional-spec.md revision 2 (AC-1..86, US-1..20), 01c-security-privacy-requirements.md
  (SEC-1..19, PRIV-1..13), 07-devops-inputs.md (OPS-W4-1..24), .claude/context/nfr-budget.md,
  .claude/context/parallel-work.md, Surbhi's five answers of 2026-09-24]
---

# Wave 4 — impact analysis and strategy

## 0. Where this branch sits, and what came in

`slice/045-redesign-wave4` was **rebased onto `slice/043-redesign-wave3`** before any
file was opened. Wave 3 had finished and gained **six commits** since 045 was branched:

| Commit | What came in |
|---|---|
| `3152fe9` | the data behind the Time and Pay screens — **new `time_api.py` (579 lines)**, `pay_api.py`, `hr_api.py` |
| `f1de544` | leave encashment, and the half of a defect 043 had wrong |
| `469026f` | the Time and Pay screens — `next-time.js` (791), `next-pay.js` (353), their CSS and parts |
| `9706fe3` | 043's measured numbers and notes |
| `dfcae39` | hiring must not cost the Time or Pay screen anything either — `test_scale_flatness_044.py` |
| `a32719d` | a fixture that did not own its own roles, found by breaking it on purpose |

**My seven commits are documents only** (the spec, the `01c`, the `07`), so the rebase
replayed clean with no conflict. Nothing of Wave 3's was touched or lost. Read the incoming
diff: 26 files, +5,210 / -3,362, and the only overlap with my files is `hr_api.py`, whose
043 hunks are `get_payslips` and `get_shift_types` — **far from `get_manager_dashboard`
(364-548) and `get_team_scorecard` (1100-1215)**, which are mine.

**The order to `dev` is 034 -> 042 -> 043 -> 045.** 045 must not reach `dev` before 043.

## 1. Parallel-work check

| Question | Answer |
|---|---|
| Files I will change | `alvoraa_portal/alvoraa_portal/hr_api.py` (two regions only), **new** `team_api.py`, **new** `growth_api.py`, **new** `tests/fixtures_045.py` and `tests/test_*_045.py`, `hrms/alvoraa_portal/attendance_correction.py` (one new custom field), `docs/slices/045-redesign-wave4/` |
| Who else is in them | The board shows 042 and 043 both finished and **not pushed**. 042's `hr_api.py` hunk is near line 336; 043's are at 1598+. **Mine are 364-548 and 1100-1215.** No overlap on any line |
| Hot files | `hr_api.py` is the hot one. I edit **only the two named regions**, never reformat, never reorder |
| Other developers | `git log origin/dev --since="7 days ago"` over these paths shows nobody outside this machine. That is a check, not a guarantee |
| The plan | **Sequence, not split.** 043 lands first; I rebase again before any hand-off |
| Bench | **My own container `hrlocal-045`**, bind-mounting this worktree's three apps, on slice 044's sites volume `hrlocal-044-sites` (`test044` 981 people, `test044s` 20). `hrlocal-bench` is **not** used and **no `docker cp`** is run — the apps are bind-mounted, so the code the container runs is the code in this worktree |
| The shared parts | The sites volume, the MariaDB and **`hrlocal-044-redis`** are shared with `hrlocal-042s` and `hrlocal-044`. The Redis hook cache is rebuilt by whichever code ran last, so **one test run at a time**, claimed on the board. Checked before starting: no `run-tests` process in any container |

## 2. Functional impact

### Cross-module reach

| App | Touched how |
|---|---|
| `alvoraa_portal` | **Almost all of it.** `hr_api.py` two regions; new `team_api.py`, `growth_api.py`; **reuses** `frame_api.ME_FIELDS`, `home_api._presence_counts` / `_filter_list` / `_scope_filters` / `_suppress`, `inbox_api`'s approvals service, `staff_api.get_staff_list`, `goals_api._pending_approvals_scope_query`'s subquery shape |
| `hrms` (our fork) | `alvoraa_portal/attendance_correction.py` — one new custom field `alvoraa_decided_as` installed beside the three that already exist, plus the capacity derivation in `decide()`. `alvoraa_hr_core/access.permitted_employee_filters` **reused unchanged** |
| `alvoraa_goals` | Read. `Company Value` is read for the self-review (decision 2); `Individual Goal.trajectory` is read for "needs attention". `Alvoraa Appraisal Extension` gains no field — `page_data` already exists |
| `erpnext` | Read only — Employee, Department, Designation |
| `alvox_compensation` | **Not touched.** Not installed |

### Persona impact

| | Today | After Wave 4 |
|---|---|---|
| **Rahul** (no reports) | Team is not in his menu. His Growth screen is the old wizard | Growth becomes a five-step self-review rating **goals**, and **every** active Company Value for his company. People gains a directory with **work email only** |
| **Sandeep** (19 reports, not HR) | One Team list; sees his reports' leave type today | **"Your team (19)" only** — "You cover" is absent from the HTML, not hidden. He keeps leave type **and reason** on the approval row for his own reports, and loses them everywhere else. **Narrower than today** |
| **Priya** (store HR, no reports) | One list of up to 50, labelled as HR scope; **sees leave types for all 38** | **"You cover (38)" only.** Leave type and reason gone entirely for her. Gains HR-only actions (invite/block a phone, cancel a deduction) and, from day three, "Approve as HR" on a correction. **She sees the correction from day one, marked "with [manager] until [date]"** |
| **Kamal** (HR + 4 reports) | One mixed list of 50 | **Both sections.** Anyone who is both appears **once**, under "Your team", with manager actions **plus** HR-only actions |
| **Asha** (no Employee) | Not in her menu | Unchanged. Typed route gives Wave 1's no-permission sentence |

### HRMS domain impact

Appraisals (the self-review, its copies, its stages), goals and KPIs (approved figure,
pending amount, stored trajectory), attendance (presence, the correction and its two-day
rule), leaves (**status only** everywhere but one row), org structure (`reports_to` as the
single source of truth).

### Callers grepped

| Function | Callers found |
|---|---|
| `hr_api.get_manager_dashboard` | whitelisted; the portal's team panel. **`l2_reports` / `l2_size`: no reader anywhere in the repository** — grepped across `alvoraa_portal`, `alvoraa_goals`, `hrms` and `mobile/` |
| `hr_api.get_team_scorecard` | whitelisted; the manager scorecard panel |
| `attendance_correction.decide` | whitelisted; the Inbox and (now) the Team card |
| `frame_api.ME_FIELDS` | `frame_api.get_frame`; now also the Team payload's `me` block — **reused, not re-typed** |

## 3. Non-functional verdict — seven dimensions

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **improves** | Two raw-SQL statements with one bound parameter per person (`on_leave_today` at `hr_api.py:496-504`, `get_team_scorecard` at `:1172-1181`) become **subqueries**. That is the x5 slope `nfr-budget.md` now bans. `get_team_scorecard` also loses an `ORDER BY creation DESC` with **no `LIMIT`** and a filter done in Python at `:1183`. Presence reuses Wave 2's helper (12.0 ms at 981). Risk: two sections mean the scope is asked **twice** — two constant queries, not one per person, and flatness is the gate |
| **Security** | **improves** | Closes a live leak (`"manager": emp` — the whole Employee row). Eleven permission rows enforced **on the server**, section **derived** never taken from the request (SEC-18). `alvoraa_decided_as` written from the server's own derivation (SEC-19). Risk: eleven rows is the shape where one row is missed, so each gets its own by-hand test |
| **Reliability** | **degrades, then improves** | **This is the first redesign wave needing `bench migrate`** (section 4 below). Until the field exists, `decide()` writing to it fails **every** correction, managers included. Mitigated by making the write conditional on the column existing, so a deploy with migrations off degrades to "capacity not recorded" instead of breaking approvals |
| **Scalability** | **improves** | Every scope goes into the query. Both sections capped at 50 with their own totals. The month-leaves fix is an overlap test, still one query |
| **Maintainability** | **improves** | One filter builder (`hr_api.py:410` is a hand-rolled copy of `home_api._filter_list` — replaced, AC-84). Two dead fields deleted. Two person-sheet endpoints become one. Risk: two new modules |
| **Data integrity** | **neutral** | No backfill. `alvoraa_decided_as` empty means **"not recorded"**, never "Manager" — guessing backwards would put a claim in the record nobody made |
| **Compliance / privacy** | **improves** | Leave type **and** the employee's own written reason drop out of the payload at the SQL and at the `fields` list. The directory carries **work email only**. Risk: the directory widens visibility to every employee, which is why decision 4's limit matters |

## 4. Two things OPS-W4 flagged, answered

### 4a. The migration, and what a deploy and a rollback each do

`alvoraa_decided_as` installs from `after_migrate` (and `after_install`), the same wiring
as `install_review_fields:135`.

| | What happens |
|---|---|
| **Deploy with migrations ON** | The field appears. `decide()` stamps `Manager` or `HR`. Records decided before this ships keep an empty value, read as **"not recorded"** |
| **Deploy with migrations OFF** | The column does not exist. A naive `decide()` would write to it and **every attendance correction would fail, managers included** — not just HR ones. **So the write is guarded**: `decide()` checks the column exists before stamping and otherwise records nothing, logging once. The approval still works; only the capacity is lost. This is the difference between a degraded feature and a broken one |
| **Rollback (revert the commits)** | The Python goes back; **the custom field stays** — a revert does not drop a column, and it should not. It is read-only and unused by the old code, so it is inert. `alvoraa_decided_as` is the field a rollback keeps, exactly as the `07` says |
| **Rollback after data exists** | The stored capacities survive and become readable again the moment the code returns. Nothing is lost |

### 4b. `page_data`'s ceiling — measured on my own bench, not assumed

**Answer: it throws. It does not truncate silently.** Measured on `hrlocal-045` against
the real column.

| Fact | Measured |
|---|---|
| Column | `text`, `CHARACTER_MAXIMUM_LENGTH` 65535, **`CHARACTER_OCTET_LENGTH` 65535** — the ceiling is bytes |
| `sql_mode` | `STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION`, **the same at `@@GLOBAL` and `@@SESSION`** — Frappe does not set it; it is MariaDB 10.8's own default |
| 21,000 Devanagari characters (63,000 bytes) | stored whole |
| **21,845 characters (65,535 bytes)** | **stored whole — the exact boundary** |
| **21,846 characters (65,538 bytes)** | **raises `DataError (1406, "Data too long for column 'page_data' at row 1")`** |
| 30,000 characters (90,000 bytes) | raises the same |

**What this means for the build.** The danger is not silent loss of half an assessment —
it is an autosave that **fails** while the employee keeps typing and believes it saved.
So the self-review **counts bytes, not characters, and refuses before the write**, with a
plain sentence saying how much is over. A Devanagari answer gets **one third** the
characters of an English one for the same budget, which is Wave 5's problem arriving early.

**Caveat I cannot close from here:** this is my bench's MariaDB. Production runs the same
`mariadb:10.8` image, so it should behave the same, but confirming the production server's
`sql_mode` is the DevOps engineer's check, not a claim I can make.

## 5. Surbhi's five answers, and what each costs

| # | Her answer | What I build |
|---|---|---|
| 1 | The self-review rates **goals**, whole points, KPI figures beside them for reference | Rating scale is integer-only, validated server side. KPI figures are read-only context, never a rating target |
| 2 | **All** company values, not two | Read `Company Value` where `is_active` and `company` = the employee's company. **The count comes from the tenant** — seven values gets seven rows. One optional comment each |
| 3 | A short design pass on the wizard only | **Server side, data model and tests now**; the screen to the spec. Flagged: the design pass could change the step order, the rating control and the value-list layout — **not** the data model |
| 4 | The directory is for employees, **work contact in** | **`company_email` exists** on Employee and is genuinely a work field. **There is no work-phone or extension field at all** — `cell_number` is labelled "Mobile" and is personal. So: **work email only**, and adding a work-phone field needs her word. See section 6 |
| 5 | HR sees a correction from day one, may act from day three; `alvoraa_decided_as` records **HR** | The row is visible and marked "with [manager] until [date]" from day one. Two working days on the **requester's own holiday list**. This closes **D-12** (Wave 2's unbuilt D-2), so `review_queue_filters` changes here |

## 6. One thing I must stop and say, not decide

**Decision 4 has a stop condition and it is half-met.**

- **Work email: yes.** `Employee.company_email`, label "Company Email". Safe to show.
- **Work phone or extension: the field does not exist.** ERPNext's Employee has
  `cell_number` ("Mobile"), `emergency_phone_number` and `personal_email` — all personal,
  and `emergency_phone_number` is somebody else's number entirely.

Her instruction was: *"If the data model has only a personal mobile field, say so and stop
rather than shipping a personal number."* **So I ship work email only and I ship no phone
number.** The directory is still useful and still safe. Adding a work-phone custom field
is a one-line change plus a way to populate it, and it needs her word — not mine.

**And the NDA point, written into the spec as she asked:** an NDA binds **the employee who
looks**. It is not the same as the employer's own duty to the person whose data it is.
A colleague promising not to share a home address does not make collecting and showing it
proportionate. Keeping the directory to work contact is what makes the wider audience safe.

## 7. Strategy — the order, and why

1. **The five defect fixes, each its own commit, each independent.** They close a live leak
   and two banned query shapes, and none of them needs a screen. Revertible one at a time.
2. **`alvoraa_decided_as` and the guarded `decide()`**, so the migration risk is handled
   before anything depends on it.
3. **The Team server side** — two sections, eleven permission rows called by hand, section
   derived.
4. **The Growth server side and the self-review data model**, with the byte budget.
5. **The People directory**, work email only.
6. **The screens**, to the spec, with the wizard's look left for the design pass.

**Measured on `test044` (981) and `test044s` (20), reused not rebuilt. Flatness is the
gate.** `scripts/check_app_integrity.py` before every commit.

## 8. What I will not do without being asked

Push, merge into `dev`, touch a server, touch production, run `docker cp`, run anything in
`hrlocal-bench`, or add a work-phone field to Employee.

---

# 9. Send — the impact analysis for revision 3 (US-21, AC-87 to AC-99)

Written 25 September 2026, before any file was opened. The strategy itself is the one
`02` revision 3 sets out; what follows is what it touches and what it costs.

## 9.1 The contradiction I resolved first

Two reports disagreed about whether the wizard's draft survives a reload. **The analyst
was right and the browser check was wrong**, and the browser check was wrong for the
reason this project has been caught by before: its "reload" was
`page.goto(<the same URL, same hash>)`, which Chrome treats as a **same-document**
navigation. Nothing reloaded, so the assertion read the value still sitting in the DOM.
Proof is in `03` §15.11b: a marker set on `window` survived the old "reload" and
disappeared on a real one, and on the real one the typed text was gone and the stored
answers were **four levels deep** (`wizard.wizard.wizard.wizard`).

## 9.2 Files this changes

| File | Change |
|---|---|
| `alvoraa_portal/growth_api.py` | read the `wizard` block back (AC-97); the key check; the finished check (D-13); the wizard's ratings applied to the review's own copies |
| `alvoraa_portal/performance_api.py` | `save_review_page` runs the key check on the `wizard` key too (AC-92); `submit_employee_review` reads both blocks, old first (AC-98), and notifies the manager once (AC-36) |
| `alvoraa_goals/review_items.py` | **unchanged.** `set_item_rating` already writes a rating and its stamp together |
| `public/js/ess/next-growth.js` | the Send button on the last step, the list of blank optional steps, the sent state |
| tests | `test_send_self_review_045.py` (new), `scripts/browser_check_self_review.js` (new) |

**No new field, no new DocType, no patch, no migration.** `Alvoraa Review Item.self_rating`
already exists on every row.

## 9.3 Cross-module reach, and every caller

* `apply_self_review` — callers: `save_review_page:4400`, `submit_employee_review:4478`.
  **Not changed**, so the old Objectives & KPIs screen is untouched.
* `set_item_rating` — callers: `save_review_item_rating`, the manager path, and now the
  wizard. Signature unchanged.
* `save_review_page` — callers: `growth_api.save_self_review`, the old screen's page save.
  The new branch only runs for `page_key == "wizard"`, which only the wizard sends.
* `submit_employee_review` — callers: `portal.js:12127` (the old screen) and now the
  wizard. The old screen sends no `wizard` block, so its behaviour is unchanged except
  for the notification, which is AC-36 and is wanted on both paths.
* `_steps_answered` — callers: `get_self_review` and its tests.

## 9.4 Persona impact

| | |
|---|---|
| **Employee (Rahul)** | Gains a Send that stores his goal ratings; his draft survives a reload. Refused, with a sentence, when a rating is missing |
| **HR Manager (Priya/Kamal)** | Nothing new is visible to HR before the review is sent — `get_my_review`'s PRIV-2 refusal is unchanged |
| **Manager (Sandeep)** | Receives one notification and the sent review. The **company-value ratings and the open-items note arrive in the payload and are not drawn** — declared debt, AC-99, unchanged by this work |
| **CXO** | No change |

## 9.5 The seven dimensions, before the code

| | Verdict | Why |
|---|---|---|
| Performance | neutral | Send adds one `Notification Log` insert and no query in a loop. The rows are the review's own child table, already in memory |
| Security | **improves** | The SEC-1 row-key check starts running on the `wizard` key (AC-92), and a KPI row name in the goals block is refused (AC-93) |
| Reliability | **improves** | A part-finished review is refused **before** anything is written; the second send is refused by the existing stage guard |
| Scalability | neutral | Bounded by one review's own copies and one tenant's value list |
| Maintainability | improves | One page key per screen, and the finished rule is one tuple (`REQUIRED_STEPS`) rather than a condition spread over a screen and a server |
| Data integrity | **improves** | The live loss AC-97 describes is fixed: the draft is read back from where it is written, and stops burying itself |
| Compliance / privacy | neutral | The notification carries the person's name and the cycle and **nothing from inside the review**. No personal text in any log line |

## 9.6 D-13, unanswered — the recommended default, in one line

`growth_api.REQUIRED_STEPS = (STEP_GOALS, STEP_VALUES)`. Ratings required, the three
written steps optional and listed on the last step. If Surbhi wants text required, add the
three step names to that tuple; the refusal sentences and the screen already follow it.

## 9.7 Parallel-work check

Worktree `.claude/worktrees/045-redesign-wave4`, branch `slice/045-redesign-wave4`, own
container `hrlocal-045`. Files claimed on the board: `growth_api.py`,
`performance_api.py` (`save_review_page`, `submit_employee_review`),
`public/js/ess/next-growth.js`, the new test file and the new browser check.
`performance_api.py` is a hot file — both hunks are named above so anybody else in it can
see exactly where I am. Local only: no push, no merge into `dev`, no server.

---

# Addendum, 2026-09-25 — two faults found while correcting the eleven-rows claim

Local only: no push, no merge into `dev`, no server, no production. Own container
`hrlocal-045`, own site `test045`. `hrlocal-bench` not used. No `docker cp`.

## A. The Inbox cannot approve leave, and has not since Wave 2

`next-inbox.js:49` sends `{ name, action, reason }`. The server declares
`hr_api.action_leave(leave_id, action)`. Frappe's `get_newargs`
(`apps/frappe/frappe/__init__.py:1168`, read in the container, not from memory) keeps
only the keys the function declares. So the call arrives as `action_leave(action="approve")`
and raises `TypeError: action_leave() missing 1 required positional argument: 'leave_id'`.
Every Approve and Decline on the new Inbox has failed since Wave 2.

`portal.js:3235` (`scActionLeave`) has the same class of fault with a different wrong name,
`leave_name`. The other three `action_leave` call sites (portal.js 3404, 3432, 3627) are
correct.

**A second fault on the same call, found while fixing the first.** `reason` is not a
parameter of `action_leave` either, so `get_newargs` drops it. The Inbox prompts a manager
for a decline reason on a factory-floor phone and then throws it away. The code comment
claims "The server enforces it too". It does not. Recorded, not fixed — where a leave
decline reason should be stored is a product decision, not mine.

### Reach

| Dimension | Finding |
|---|---|
| Cross-module | None. `hr_api.action_leave` is unchanged; only the browser's key changes |
| Callers | 5 call sites of `action_leave` in JS, all listed above. No Python caller outside tests |
| CXO / System Manager | No change |
| HR Manager / manager | Approve and Decline on the Inbox start working. Today they fail |
| Employee | No change |
| HRMS domain | Leaves. Nothing else |

### Non-functional verdict

| Dimension | Verdict | Why |
|---|---|---|
| Performance | neutral | Same call, two keys instead of three |
| Security | neutral | Server-side permission path untouched |
| Reliability | improves | The call stops raising |
| Scalability | neutral | — |
| Maintainability | improves | The new check makes this class of fault visible |
| Data integrity | neutral | — |
| Compliance / privacy | neutral | No new field crosses the wire; one fewer (`reason`) does |

## B. The test that would have caught it

No test on this project can see a browser-to-server argument-name mismatch, because every
test calls the Python directly. That is the real gap — a whole class of fault with no
check.

New structural test, modelled on `test_frappe_api_calls.py`: read the portal's own
JavaScript, collect every whitelisted endpoint called with an object literal of arguments,
and compare those key names against the Python signature. Two failures:

* a **required** parameter the browser never sends — the `TypeError` class;
* a key the server **does not declare** — the silently-dropped class (`reason`).

**Scope, stated plainly.** Enforced over the redesign's own panels,
`public/js/ess/next-*.js`, and over `portal.js`'s `api("name", {...})` shape. Not covered:
calls built dynamically, `frappe.call` written by hand elsewhere in the repo, the desk, the
mobile app, and any endpoint reached by plain navigation rather than an argument call. A
narrow check that runs beats a wide one that does not exist.

The check fails loudly rather than quietly: it pins a minimum number of call sites, and
every `alvoraa_portal.*` endpoint named in those files must either be matched to a call
site or listed with a reason. A call shape it cannot parse fails the test.

## C. A goal can be set for anyone in the tenant by any HR role

`goals_api._require_manages:379` returns for any `FULL_ACCESS_ROLES` holder with **no
company scope at all**. Its sibling `approve_goal_update:1232` checks
`permitted_companies()`. On a multi-company tenant, HR at one company can create goals for
a person at another.

**The same shape elsewhere in the module** (all found by grepping `_is_hr()`):

| Line | Function | Act | Decision |
|---|---|---|---|
| 379 | `_require_manages` (create_goal, get_linkable_objectives) | write | fix |
| 600 | `_require_can_edit` (update_goal, delete) | write | fix |
| 837 | `set_goal_progress` | write | fix |
| 1152 | `submit_goal_update` | write | fix |
| 399 | `get_manageable_employees` | read — the picker `create_goal` is driven from | fix |
| 737 | `get_goal_detail` | read | fix |
| 1264 | `get_goal_update_log` | read | fix |
| 238, 300, 807, 1275 | `is_hr` / `can_edit` / `can_action` display flags | flag | leave — the write paths above are the gate |
| 1343, 1377, 1456 | `_pending_approvals_scope_query` and its two callers | read | already scoped |

`get_manageable_employees` is fixed with the writes on purpose: leaving it wide would draw
a picker full of people the server then refuses, which is the opposite of this codebase's
"a row that is drawn is a row that can be acted on" rule.

One helper, `_hr_may_act_for()`, wrapping `permitted_companies()`. No third definition of
"which companies".

### Whose behaviour changes

| Who | Before | After |
|---|---|---|
| System Manager / Administrator | everyone | everyone — `permitted_companies` returns every company |
| HR with no Company user-permission, on a single-company tenant | everyone | everyone — falls back to their own Employee's company |
| HR with Company user-permissions (store or single-company HR) | **every company** | their permitted companies only |
| HR with **no** Company user-permission and **no** active Employee record | everyone | **nothing** — fails closed |
| Manager, non-HR | own subtree | own subtree, unchanged |
| Employee | self | self, unchanged |

Rows 3 and 4 are the release note. Row 4 is a deliberate fail-closed, and it is the rule
`approve_goal_update` and `get_pending_approvals` already apply — this makes the module
agree with itself.

### Non-functional verdict

| Dimension | Verdict | Why |
|---|---|---|
| Performance | neutral | One `get_value` for the company and one `permitted_companies()` per guarded call |
| Security | improves | Closes cross-company goal writes and reads by an HR role |
| Reliability | neutral | Refusals are named sentences with a next step |
| Scalability | neutral | — |
| Maintainability | improves | One definition of company scope instead of two-and-a-gap |
| Data integrity | neutral | — |
| Compliance / privacy | improves | Another company's employees stop being readable and writable |

## D. Recorded, not fixed

1. **`cancel_deduction` has no endpoint anywhere.** Cancelling is a desk action on
   `Attendance Deduction`, where `hrms/alvoraa_late_rules/permissions.py:35` returns `True`
   for an HR role with no company narrowing. Not an exposure — a row with no endpoint
   cannot be called — but the Team screen names an action the product cannot perform
   outside the desk.
2. **`see_presence` has no per-person rule** because there is no per-person read at all.
3. **`approve_evidence` navigates to a dead end.** `GOES_TO.approve_evidence = "inbox"`,
   and the new Inbox maps only leave and attendance.
4. **Nothing in CI checks that `main.pot` is current.** That is why it drifted for a day
   unseen. Deliberately not added here: it needs git in CI, and it is its own decision.
5. **The Inbox's decline reason is discarded** (section A).
6. **`goals_api` defines `_is_hr` twice** — line 17 and line 386. The second wins at import.
   Both resolve to the same three roles today, so nothing is wrong now; it is a trap.
7. **`get_alignment_options` has never been able to answer for another employee.**
   Found by the new check, not by a person. `portal.js:5414` sent
   `{employee: pfGoalEmployee()}`; the server declares
   `goals_api.get_alignment_options()` with no parameters, so Frappe dropped the key and
   answered with the CALLER's reporting line. Raising a goal for somebody else therefore
   offered parents from the wrong chain - and `create_goal` then refused the save,
   because it checks the parent against the SUBJECT's chain. The key is removed from the
   browser (sending a name the server does not declare asks for nothing), which changes
   no behaviour. Making the picker right needs `get_alignment_options(employee)` on the
   server, guarded by `_require_manages`. **That is a decision, not a typo fix.**
8. **The new reader's own first version read next-inbox.js's whole ACTIONS table as
   nothing, and passed.** It searched a copy of the source with string bodies blanked,
   so the endpoint paths - which live inside quotes - were invisible. The orphan guard
   caught it. The reader now keeps a second copy with comments blanked and strings
   intact. Worth remembering: the guard, not the check, found the hole in the check.

## E. Parallel-work check

`git fetch origin dev`: nothing came in. `slice/045-redesign-wave4` contains all of
`origin/dev` (0 behind, 162 ahead). Worktree clean at the start.

Work board: every `045` row says the bench is released; `048` is finished and its container
stopped. No other row claims `goals_api.py`, `hr_api.py`, `next-inbox.js` or `portal.js`.

Files I will change: `alvoraa_portal/alvoraa_portal/goals_api.py`,
`public/js/ess/next-inbox.js`, `public/js/ess/portal.js` (one line, 3235), and two new test
files. `portal.js` is a hot file — the one changed line is named here.
