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
