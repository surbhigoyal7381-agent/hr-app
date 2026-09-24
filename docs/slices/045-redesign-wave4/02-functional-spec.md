---
slice: 045-redesign-wave4
artifact: 02-functional-spec
author: hrms-business-analyst
date: 2026-09-24
revision: 1
status: draft. **This slice has no `01c` and no `07` yet** — see "What is missing before this is ready" below. Waves 2 and 3 wrote their `02` at revision 1 before their `01c` landed and revised to 2 afterwards; this one expects the same
inputs: [../009-ess-portal-redesign/00-assessment-and-plan.md §4 Wave 4 and Appendix D, ../009-ess-portal-redesign/appendix-d-growth-team-people.md, ../009-ess-portal-redesign/01b-ux-design.md, ../009-ess-portal-redesign/00f-decisions-2026-09-22.md, ../034-redesign-wave1/00g-decision-register.md (W1D-01 to W1D-23), ../034-redesign-wave1/02-functional-spec.md revision 4, ../034-redesign-wave1/03-implementation-notes.md, ../042-redesign-wave2/02-functional-spec.md revision 2, ../042-redesign-wave2/03b-implementation-notes-044-followups.md, ../043-redesign-wave3/02-functional-spec.md revision 2, ../043-redesign-wave3/03-implementation-notes.md, .claude/context/nfr-budget.md, prototype-v2.html]
brief: there is no `01` for this slice. The approved brief is `../009-ess-portal-redesign/00-assessment-and-plan.md` (Wave 4), the design is `../009-ess-portal-redesign/01b-ux-design.md`, and the decisions are in `00f-decisions-2026-09-22.md` and `../034-redesign-wave1/00g-decision-register.md`
---

# Wave 4 — Growth, Team and People: functional spec

## Bad news first

**Five things, and the first is a live leak on the very screen this wave re-dresses.**

1. **The Team screen's endpoint hands the browser a whole Employee row today.**
   `hr_api.get_manager_dashboard:530` returns `"manager": emp`, where `emp` is
   `_get_employee()`'s complete record — **date of birth, gender, phone number, branch
   and reporting manager** (`hr_api.py:152-160`). **Confirmed fact**, read at line 530 on
   `slice/043-redesign-wave3` today. It is one of the five endpoints slice 043 pinned as
   declared debt (`043` `03-implementation-notes.md` §6 finding 1), and it is the only
   one of the five that Wave 4 opens anyway. **Wave 4 fixes this one**, with the
   six-key `me` block Wave 1 and Wave 3 both already built. AC-6, US-12.
2. **The Team screen sends a colleague's leave type to the caller, in two places.**
   `on_leave_today` (`hr_api.py:496-504`, raw SQL) and `month_leaves`
   (`hr_api.py:517-525`) both select `leave_type` for every person in `team_ids`. For a
   manager about their own reports, that is arguable — they approve the leave. **After
   W1D-20 an HR caller's `team_ids` is up to 50 people in their HR scope, not their
   reports**, and `01b` §14 rule 9 says no screen shows a colleague the reason for an
   absence. Wave 3 `02` §5 forbids it outright. **The two rules contradict each other and
   somebody must choose** — §21 D-1, and my recommendation is presence only on the
   screen, with leave type kept on the approval row where the approver needs it.
3. **`month_leaves` has been wrong since it was written, and the redesign puts it on a
   bigger card.** `from_date >= mo_start` (`hr_api.py:522`) **misses leave that began
   last month and is still running**, and **includes leave that starts next month**.
   Appendix D recorded it as B18/TM-05 on 14 September; it is unchanged on
   `origin/dev` at `8718f27`. AC-21.
4. **Three browser tests for the Growth screens have never run, and they are counted as
   coverage.** `scripts/run_dom_tests.js` skips `portal_tree_test.js`,
   `portal_redesign_test.js` and `portal_appraisal_test.js`. Two need a
   `get_performance_tree` payload that is in no file in this repository; the third drives
   `#panel-appraisals`, a panel the page does not have. **Its own comment says they belong
   to "Wave 3". That is wrong — they are the Growth screens and Growth is Wave 4.** This
   slice owns them: US-15, AC-62 to AC-64, and the fixtures are a requirement, not a
   nice-to-have.
5. **Peer feedback cannot be built on `Employee Performance Feedback` without new
   row-level rules, and the reason is worse than "it does not fit".** **Confirmed fact**,
   read in `hrms/hrms/hr/doctype/employee_performance_feedback/employee_performance_feedback.json`:
   `appraisal` is a **required** link (so there is no such thing as feedback outside a
   review cycle), and the **`Employee` role holds `read`, `write`, `create`, `submit`,
   `cancel`, `export`, `print` and `share` on the whole doctype**, with **no
   `permission_query_conditions` entry for it in `hrms/hooks.py`**. Extending it means
   every employee in the tenant can list and export every feedback record about everyone
   until we write those rules ourselves. That belongs in §23's go/no-go, not in the
   wave's main body.

**Good news, and it is most of the wave.** Everything Appendix D called a live security
hole in Growth — the self-review writing other people's records (B4), evidence approving
itself (B2), public evidence files (B3) — **is fixed and on `origin/dev`**. Verified by
reading: `performance_api.submit_employee_review:4419` checks `ap.employee != me` and
writes only to this review's copies through `review_items`;
`alvoraa_goals/api/goal_api.submit_goal_evidence` saves `validation_status: "Pending"`
and calls `claim_evidence_file` for a private, caller-owned attachment. **Wave 4's Growth
work is a screen on endpoints that are already safe**, which is exactly what the plan
asked for when it said "Wave 0a must be done".

---

## What is missing before this is ready

| Input | State | What it changes |
|---|---|---|
| `01c-security-privacy-requirements.md` (045) | **not written** | The permission matrix in §6 and the negatives are built from Wave 1's `01c` revision 4 and Waves 2 and 3's. A Wave 4 `01c` will almost certainly add checks around the review's manager-only fields and the person sheet's contact details. **This spec is revision 1 until it lands.** |
| `07-devops-inputs.md` (045) | **not written** | §14's numbers are marked "to be measured", not guessed — see §14. `OPS-W4-n` items become requirements when they exist |
| A design run for Growth, Team and People | **`01b` §11 says it was deliberately not done**: "Wave 4 Growth, Team and People beyond the two new behaviours. Feedback, the person sheet and the directory are v1 as they were" | §22 records every place this spec specifies something the prototype only sketches. **This is the one input the handoff contract calls required for a screen change, and it is partly absent.** §21 D-8 |

**Said plainly: this spec is ready to start a build and is not ready to finish one.**
The server work in §8's US-12 and US-5 can begin today. The Growth wizard and the person
sheet need §21 answered first.

---

## Lessons carried in from Waves 2 and 3, so they are not repeated

Both earlier specs were corrected at revision 2. Their corrections are rules here.

| Lesson | Where it came from | How this spec obeys it |
|---|---|---|
| **A check that would pass on the day it is written proves nothing.** Wave 3's AC-17 tested for a rupee amount that was never in the email, while the real leak — the leave type — went out | 043 revision 2, item 2 | Every "must not contain" check in §11 names a value that **is present today** and would be found, and says where it is present. AC-6, AC-20, AC-32, AC-33 |
| **Do not write a remedy the product does not have.** Wave 3 revision 1 told 400 people that correcting a day undoes a deduction. It does not | 043 revision 2, item 1 | §10's wording says what actually happens on send and on an approval that changes nothing. AC-36, AC-41 |
| **Extend the file that exists; do not plan to create it.** Wave 2 revision 1 planned to build `inbox_api.py`; Wave 1 had already built it | 042 revision 2, item 1 | §1 and §4 name every module that exists **today** — `inbox_api.py`, `home_api.py`, `frame_api.py`, `staff_api.py`, `pay_api.py`, `call_cache.py` — and say **extend** against each. A gap row that says "build" is only there where the file genuinely does not exist |
| **Do not count the same thing twice.** Wave 2 revision 1 had `get_home` carrying `counts` that the frame had already asked for | 042 revision 2, item 3 | §7 and AC-13: the Team screen does **not** re-ask for the nav counts, and Growth does not re-ask for the goal figures the Team card already has |
| **Adding a panel is free.** OPS-31 landed; markup parts are pasted by `ess_part()` and take no template cache slot. 12 parts measured faster than one include | 042 and 043 revision 2 | AC-52. Growth, Team and People each get their own markup, style and script file, and the pinned Jinja include set stays at three |
| **Set a budget by measuring it.** Four budgets were wrong the day they were written and failed at 20 people as badly as at 981 | 042 `03b` §3, `nfr-budget.md` | §14 carries **no invented query count.** It names the two fixture sites, the harness, and the property that is the gate |
| **A scope belongs in the query, never in an `IN (...)` of ids.** Measured: a ×5 slope | 042 `03b` R4, now in `nfr-budget.md` | AC-14. The Team screen's attendance and leave reads take a subquery, not a list of names — and today `on_leave_today` is raw SQL with one `%s` per person |

---

## 0. How to read the numbers in this file

**Story and check numbers are per slice.** This slice runs `US-1` to `US-17` and `AC-1`
to `AC-72`. Wave 1, Wave 2 and Wave 3 each have their own `US-1` and `AC-1`. Cite these
as "045 AC-12".

Claims carry a label: **Confirmed fact** (read in the source, with file and line),
**Stakeholder statement**, `[ASSUMPTION]`, **Recommendation**, **Risk**,
**Open question**, `[UNVERIFIED — engineer to confirm]`.

Line numbers are from `slice/043-redesign-wave3` at `042b6ee`, which contains
`origin/dev` `8718f27`, Wave 1, Wave 2 and slice 044. Read in
`.claude/worktrees/045-redesign-wave4` on 2026-09-24.

---

## 1. Cross-module reach — named before anything is specified

| App | Touched how |
|---|---|
| `alvoraa_portal` | **Most of the work.** **Extends** `hr_api.py` (`get_manager_dashboard`, `get_team_scorecard`, `get_team_goals`, `get_team_late_list`, `get_goals_portal_data`, `get_employee_scorecard`), `performance_api.py` (the review read and send, action items, upward feedback), `goals_api.py` (evidence, updates), `home_api.py` (**reuses** `_presence_counts`, `_scope_filters`, `_suppress`), `staff_api.py` (**reuses** `get_staff_list`), `inbox_api.py` (**reuses** — the approvals service is Wave 2's, not a second one). **New:** `growth_api.py`, `team_api.py`, and markup, style and script files per screen |
| `hrms` (our fork) | `alvoraa_org_structure/api.py` — read; `search_people` and `_search_scope` were narrowed in Wave 1 and are **reused unchanged**. `alvoraa_hr_core/access.py` — `permitted_employees` / `permitted_employee_filters` reused unchanged. `alvoraa_policy_library` untouched |
| `alvoraa_goals` | Read, and one existing write path: `api/goal_api.submit_goal_evidence` (already Pending by default) and `controllers/goal._update_trajectory`. **The trajectory staleness in §21 D-3 lives in this app** |
| `erpnext` | Read only — Employee, Department, Designation |
| `frappe` | Read only, plus `__()` |
| `alvox_compensation` | **Not touched.** Not installed on either client tenant |

**HRMS domains involved:** appraisals (the self-review, its copies, its stages), goals
and KPIs (progress, evidence, trajectory), attendance (the Team screen's "in now",
reused from Wave 2), leaves (who is off — §21 D-1), org structure (who may see whom, the
chart and the staff list).

**Personas** are Wave 1's (034 §2, W1D-02, W1D-20, W1D-22), unchanged:

| Short name | Who | Persona rule |
|---|---|---|
| **Rahul** | sales executive, no reports, not HR | 4 or 5 |
| **Sandeep** | floor manager, 19 reports, not HR | 3 |
| **Kamal** | owner who holds HR, 4 reports | 1 |
| **Priya** | store HR, no reports | 2 |
| **Asha** | platform operator, no Employee record | 6 |

**One persona this wave adds nothing for, and says so:** Asha. Growth, Team and People
are not in her menu, and typing the route gives Wave 1's no-permission sentence.

---

## 2. What is new, and what Wave 4 only re-dresses

The plan describes Wave 4 as if all of it were new. **It is not, and pretending otherwise
would double-build two screens that already work.**

| Screen | State today | Wave 4's job |
|---|---|---|
| **Team — the list and its scope** | **Built in Wave 1.** W1D-20 rebuilt `get_manager_dashboard` on `permitted_employee_filters()`: HR scope for an HR caller, own direct reports for a plain manager, `status = Active` kept, capped at `TEAM_LIST_CAP = 50` (`hr_api.py:17`) with `team_total`, `team_capped` and `is_hr_scope` in the payload so the screen can say what it is not showing | **Re-dress only.** Do not re-decide the scope. **Do** fix the `manager` key (bad news 1) and the two leave-type reads (bad news 2) |
| **Team — "in now / still to come"** | **Built in Wave 2** as `home_api._presence_counts` + `_scope_filters` + `_suppress`, rewritten in slice 044's follow-ups as two aggregates with the scope **in the query**. 12.0 ms for a System Manager at 981 people | **Reuse the helper.** A third presence calculation is the thing this project keeps being bitten by |
| **Team — "waiting on you"** | **Built in Wave 2** as the approvals service behind `inbox_api`, with `get_nav_counts` flat in headcount | **Reuse.** The Team screen's number is the Inbox's number filtered to this team, computed once (§7) |
| **People — the staff list** | **Built in Wave 1.** `staff_api.get_staff_list`, its own opt-in switch `staff_list` (W1D-21), five payload keys, Active only, capped at 50, **2 queries flat from 20 people to 981** | **Re-dress only.** Add the person sheet on top of it |
| **People — the org chart** | Unchanged, behind `plan_org_structure` (W1D-21). **`ALV-86` is open and Critical**: the chart shows every company and store (W1D-08) | **Not touched.** Wave 4 does not work around ALV-86 and does not wait for it |
| **People — search** | **Built in Wave 1.** `search_people` narrowed to the store for store HR, Active caller only, escaped wildcards, POST only | **Reuse unchanged** |
| **Growth — the endpoints** | **Fixed by slice 010 group D**, on `origin/dev`. Review copies, ownership checks, evidence Pending, private files, stage checks | **Genuinely new screens on safe endpoints** |
| **Growth — the 5-step wizard** | The current wizard hard-codes seven generic principles, has no goals page for a cycle with an empty `page_config`, and shows raw markup in its "Saved" line (B13, B14, B15) | **New build** |
| **Growth — the two behaviour changes** | `01b` §7.1 (a review works on its own copy) and §7.2 (a KPI reading is an increment, and the headline is the approved figure) | **New build.** These are the two `01b` §14 items most likely to be quietly lost |
| **Open action items** | `add_action_item:3353` and `update_action_item_status:3379` exist; the second has no caller | **Extend** — a "my open action items" read across appraisals |
| **Peer feedback** | Nothing fits (§23) | **Its own go/no-go at the end of the wave** — 009 design decision 4 |

**Recommendation, stated once:** build in the order US-12, then the Team and People
server work, then the screens. The server fixes are independent of every screen and one
of them closes a live leak.

---

## 3. Questioning the ask before specifying it

**The brief's problem is named with evidence, and it is the right one.** Appendix D did
not say "people do not trust reviews"; it measured a self-review that could write a
colleague's goal progress, a manager who could read a draft, and an approvals call making
706 queries. Those causes are fixed. **What is left is the second half of the same
problem: a correct number nobody can act on is still not useful.** So Wave 4's job is
*acting where you are standing* — approve from the Team card, log a reading from the goal
card, send a review from the step you are on.

**What happens after each thing we put on the screen:**

| Thing | Decision it drives | Who decides | Could the system act instead? |
|---|---|---|---|
| "2 people need you" on Team | approve or decline | the named approver | No. A person must decide about a person (§19.4) |
| "Needs attention · 3" | have the conversation | the manager | **No, and this is the one to watch.** A stored trajectory is one design step from a ranking. §19.4 refuses it in writing |
| A goal card's approved figure | log a reading, or nothing | the employee | No |
| "Still open from last time · 2" | close it, or move it | whoever it is assigned to | **Partly, and we deliberately do not.** The system could close an item on a date; it must not, because an unclosed item is information |
| "Late this week · 2" | a conversation, not a deduction | the manager | It already acts — the weekly rule decides the money (Wave 3). This screen must not imply the manager decides it |
| The staff directory | find and contact a colleague | the employee | No. **And if nobody uses it, it is a habit, not a requirement** — `01b` §12's usability test decides |
| New joiners this month | say hello | anyone | No |

**One thing I would push back on if it were still open.** The prototype's Growth screen
shows a goal progress bar as the headline. `01b` "Bad news" point 2 already says that is
the wrong lead number for a KPI. **I agree, and §22 row (a) records that the built screen
leads with the approved figure and names the pending amount separately.**

---

## 4. Gap analysis — what already exists, checked in the source

### Growth (the plan's G-01 to G-12, SR-01 to SR-08)

| Requirement | What exists today (file : line) | Verdict | Cost |
|---|---|---|---|
| Cycle header: name, dates, "day n of m", stage | `performance_api.get_performance_context`, `get_my_appraisals` | **Reuse**; the client computes days | S |
| "Start / Continue step n of 5 / Sent to Sakshi" | `get_my_review:4125` returns `pages_completed` | **Extend** — today a page counts as done on any save, even an empty one (appendix D G-02) | S |
| The review works on its own copy | **Built.** `review_items.open_review`, `apply_self_review`, `save_review_record`; `submit_employee_review:4419` refuses a review that is not the caller's and writes to copies only | **Reuse, unchanged.** The screen must **never** re-read the live goal — AC-30 | — |
| Five steps with guidance | The current wizard builds pages from the cycle's `page_config`; a cycle with `page_config = []` gets no goals page (B14) | **Build** — a fixed five-step shape that does not depend on a cycle being configured | M |
| Rate each goal, 1–5, with a note | `self_rating` / `self_comment` on the review's KPI copies; goal reflection in `page_data` JSON | **Reuse**, with §21 D-4 deciding goals or KPIs and whole or half points | S–M |
| Pick up to two values with an example | Nothing stores chosen values. `get_company_values:3436`; HRMS's own template rates **all seven** criteria | **Build** — one new JSON key, no schema change. §21 D-5 chooses the master list | S |
| Went well / would do differently | `achievements_text`, `challenges_text` on the extension | **Reuse** | S |
| One thing to get better at, and what would help | `development_needs_text`, `support_needed` | **Reuse**. The prototype's skill options are invented (SR-05) — §21 D-6 | S |
| Check and send; a notification to the manager | `submit_employee_review:4419` sets `Manager Review` and **sends nothing** (appendix D B25). `advance_review_status` does notify | **Extend** — one notification, reusing the existing helper. AC-36 | S |
| "Saved at HH:MM", debounced | `save_review_page:4381` fires on step change only; `01b` and appendix D both ask for 3–5 s idle, at most every 15 s | **Extend** — a debounce on the client, a server-confirmed time in the answer | S |
| Goal cards with the approved figure and the pending amount | `hr_api.get_goals_portal_data:2155`; `goals_api.get_goal_detail:712`, `get_goal_update_log:1259`; `submit_goal_update:1148`, `approve_goal_update:1219` | **Extend** — the payload must name the approved figure and the pending rows **separately**, never summed. `01b` §7.2, AC-29 | M |
| Evidence rows with a real status | **Built.** `goal_api.submit_goal_evidence` saves `validation_status: "Pending"` and claims a private file | **Reuse** | — |
| "Progress moves when evidence is approved" | `alvoraa_goals/controllers/evidence.approve_evidence` and `goal.recalculate_progress` | **Reuse** — and the screen must say so in words. AC-29 | S |
| Trajectory chip (On Track / At Risk / Off Track) | **Stored field**, computed in `alvoraa_goals/controllers/goal._update_trajectory:39` on **validate** | **Reuse the field**; **name the staleness** — §21 D-3, AC-24 | S |
| Manager sees upward feedback about themselves, with a minimum group | `get_upward_feedback_received:3639` hides detail below three responses | **Reuse.** `goals_api.get_upward_feedback:1113` has **no** minimum and no caller — **drop it** (appendix D B22). AC-35 | S |
| "Still open from last time" | `add_action_item:3353`; `update_action_item_status:3379` has no caller | **Extend** — a read across the caller's appraisals | M |
| "What your manager will see" | Static copy, and it was false when it was written | **Build** the sentence from what the code actually does. AC-41 | S |

### Team (TM-01 to TM-09)

| Requirement | What exists today | Verdict | Cost |
|---|---|---|---|
| The list and its scope | `hr_api.get_manager_dashboard:365`, rebuilt in Wave 1 on `permitted_employee_filters()`, Active only, capped at 50 with `team_total`, `team_capped`, `team_cap`, `is_hr_scope` | **Reuse, unchanged.** W1D-20 decided it | — |
| The `manager` key | `:530` returns `emp` — the **whole Employee row** | **Extend** — the six-key `me` block. **Live leak.** AC-6 | S |
| `l2_reports` / `l2_size` | Returned; **nothing in this repository reads them** (`hr_api.py:441-460` says so) | **Drop** — delete the keys with the screen that never used them. AC-16 | S |
| "In now / still to come" | `today_att` (`:482`) is Attendance only and never counts today (B18) | **Drop and reuse** `home_api._presence_counts` + `_scope_filters` + `_suppress` (Wave 2, rewritten in slice 044's follow-ups as two aggregates with the scope in the query). AC-14 | S |
| "Who is on leave today" | `:496-504` — **raw SQL**, `employee IN (...)` with one `%s` per person, and it selects **`leave_type`** | **Extend or drop** — §21 D-1. Whatever is decided, the `IN (...)` goes (AC-14) | S |
| "On leave this month" | `:517-525` — `from_date >= mo_start` **misses leave begun last month and includes next month's** (B18/TM-05), and also selects `leave_type` | **Extend** — a real overlap test. AC-21 | S |
| "Waiting on you" | Wave 2's approvals service behind `inbox_api` | **Reuse.** One definition, filtered to this team. AC-13 | S |
| "Needs attention" | No rule. The prototype's 75 % is invented (appendix D TM-03) | **Extend** — use the **stored `trajectory`**, not a percentage. §21 D-2 and D-3 | S |
| "Late this week" | `get_team_late_list:2898` — days only, no amount (Wave 3 AC-16 pins it) | **Reuse unchanged.** AC-33 pins it again because Wave 4 renders it | — |
| "New this month" | Nothing | **Build** — one `date_of_joining` filter inside the same scope subquery. AC-22 | S |
| Team cards with a cycle figure | `get_team_scorecard:1098` (10 queries, flat, measured by slice 044); `get_team_goals:2541` loops per person (22 queries for 19 people, appendix D §D) | **Extend** — one batched read per cycle. **Measure it; do not assume a number** | M |
| Tap a person → a sheet | `get_employee_scorecard:915` **or** `get_employee_detail_for_manager:1218` — two endpoints for one thing, and appendix D TM-08 records one of them returning `personal_email`, `cell_number` and `gender` to a manager | **Extend** — **one** person sheet endpoint with a fixed key list. §21 D-7 decides what contact detail it carries. AC-20 | M |
| Direct reports versus everyone below | **Closed by W1D-20.** HR gets HR scope; a plain manager gets direct reports | **No work.** Appendix D's Q26 is answered — record it, do not re-open it | — |

### People (PE-01 to PE-08)

| Requirement | What exists today | Verdict | Cost |
|---|---|---|---|
| A searchable staff list | **Built in Wave 1.** `staff_api.get_staff_list`, feature `staff_list` (opt-in, W1D-21), five keys, Active only, 12 shown / 50 maximum, **2 queries at 20 people and at 981** | **Reuse unchanged** | — |
| The list's empty, no-permission and feature-off states | Wave 1 built them; an absent switch hides the entry and the endpoint refuses on the server | **Reuse.** AC-51 re-asserts them because the screen moves | — |
| You and your manager | `org_structure.my_view:397` (31 queries, walks the tree one step at a time) | **Extend** — the manager comes from `Employee.reports_to`, one read. **§21 D-9: the chart and `reports_to` still disagree** (W6/B12) | S |
| "Also reporting to <manager>" | `my_view.peers` means *same position*, not *same manager* — a different thing with the same label | **Build** — peers by `reports_to`, inside the caller's own scope. AC-26 | S |
| New this month | Nothing | **Build** — the same query as Team's. AC-22 | S |
| "Leadership" / other floors | No flag, no definition | **Drop from Wave 4** — §13. There is no field and no agreed meaning; inventing one is how a directory becomes an org chart nobody approved | — |
| Search by name **or role** | `search_people:581` matches the name only | **Extend** — designation as well, inside the same scope. AC-27 | S |
| A person sheet with contact details "when they choose" | `_card` returns name, designation, department, branch, image. **There is no consent field anywhere** | **Build or drop** — §21 D-7. Until it is answered, **no phone number and no email address**, which is Wave 1's `staff_api` rule already | M |
| Org-health numbers on the chart | `metrics.org_health` is HR-only and was called for everyone (F3) | **Out of scope** — it belongs to the chart, which Wave 4 does not touch | — |

**No new DocType and no new custom field are needed for anything in §8**, with one
exception that depends on a decision: **§21 D-7's contact-visibility consent** would be
one field on Employee. Peer feedback (§23) is the only part of Wave 4 that needs a new
record type, and it is deliberately outside the wave's body.

**Where two models describe the same thing.** *Who is my manager* is described by
`Employee.reports_to` and by the org chart's position tree, and **they disagree on the
live demo tenant** (Rahul: Sandeep Gupta on the chart, Sakshi Verma on `reports_to`).
**The single source of truth is `Employee.reports_to`** — reviews, leave and approvals
all already route on it. The chart is a drawing of positions. AC-25 pins it and §21 D-9
carries the data fix.

---

## 5. Process flow — what actually happens

### 5a. Rahul does his self-review (the common path)

1. Growth shows the cycle header and a **Start** or **Continue, step 3 of 5** control.
2. Step 1 shows his goals **as the review copied them**, above the sentence `01b` §7.1
   wrote: "These figures were copied into your review on 1 Oct 2026."
3. He rates and writes. **Decision point — has he answered enough?** The screen does not
   block him; the last step lists what is still empty.
4. Autosave: 3–5 s after he stops typing, at most every 15 s, plus on step change, blur
   and page hide. The screen shows the **server's** confirmed time, not its own clock.
5. Step 5 lists what is empty, then **Send**.
6. On send the status becomes Manager Review, the screen says who it went to, and **his
   manager is notified** (new — AC-36). The steps become read-only.

**Unhappy paths:** no active cycle (a sentence, not an empty wizard); no review record
for him yet (it is created on first save, not on read); he presses Send twice (the second
gets "This has already been sent." and nothing moves); he is in the subject's reporting
line for somebody else's review (slice 010's rule — he sees the note, not a disabled
button); his session expires mid-typing (the draft is in `page_data` from the last
autosave and the screen says when that was).

### 5b. Sandeep opens Team and deals with two people

1. Team shows the stats line, then **Waiting on you**, then the cards.
2. **Decision point — approve or decline?** He acts on the card. The row leaves the list
   and the Inbox count moves, because it is the same service (AC-13).
3. He taps a person. The sheet shows what he may see about them — never their leave
   reason, never their pay.

**Unhappy paths:** somebody else decided the same request a second earlier (one succeeds,
the other gets "This one has already been decided."); a report has left (not on the list —
`status = Active`); he has no reports at all (there is no Team entry in his menu — Wave 1
`frame_api` decides it); he is HR as well, so the list is his HR scope and the screen
**says so** rather than calling fifty people his direct reports.

### 5c. Priya, store HR, opens People

1. The staff list is there only if the tenant has the `staff_list` switch (W1D-21).
2. She searches. Results are **her store**, because Wave 1 narrowed `_search_scope`.
3. **Decision point — is the person she wants missing?** The empty sentence names her
   real scope, so she knows to ask rather than concluding the person does not exist.

**Unhappy paths:** the switch is off (no entry at all; a typed route gives the
no-permission sentence, never an empty list); a term of one character (not a search — the
plain list); a term of `%` (escaped — it does not return everyone).

---

## 6. Permission and visibility matrix

| | Rahul | Sandeep (manager) | Priya (store HR) | Kamal (HR + reports) | Asha (no Employee) |
|---|---|---|---|---|---|
| Growth: own review, own goals, own evidence | ✓ | ✓ | ✓ | ✓ | — (not in her menu) |
| Growth: **another person's** draft self-review | — | **— never, until it is sent** | — until HR Review | — until HR Review | — |
| Growth: a sent review of a direct report | — | ✓ | ✓ within HR scope | ✓ | — |
| Growth: `manager_internal_notes` | **— never** | ✓ own reports | ✓ | ✓ | — |
| Growth: overall / potential rating before release | **— never** | ✓ | ✓ | ✓ | — |
| Growth: HR steps on a review inside one's own reporting line | — | — | **— refused, with a note** (slice 010 decision 34) | **— same** | — |
| Growth: upward feedback about oneself | — | ✓ totals only, 3+ responses | ✓ | ✓ | — |
| Growth: **who wrote** upward feedback | **— never, for anyone** | — | — | — | — |
| Team: the list | not in his menu | ✓ direct reports | ✓ HR scope | ✓ HR scope | — |
| Team: a report's late **days** | — | ✓ | ✓ | ✓ | — |
| Team: a report's late **amount** or the stored explanation | **— never** | **— never** | **— never** | **— never** | — |
| Team: a colleague's **leave type** | **— never** | **§21 D-1** | **§21 D-1** | **§21 D-1** | — |
| Team: a colleague's payslip or pay figure | **— never, including HR** | — | — | — | — |
| People: the staff list | ✓ where `staff_list` **and** §21 D-10 | ✓ | ✓ their store | ✓ their companies | — |
| People: phone number, email, employee number | **— never, until §21 D-7** | — | — | — | — |
| People: a leaver | **— never** | — | — | — | — |
| The org chart | behind `plan_org_structure`, unchanged | | | | — |

### The negative cases, stated on purpose

**The Growth screen must NOT show:**

| Must not | Why |
|---|---|
| The live goal figure inside the review | `01b` §7.1. The review has its own copy, and the two must never be mixed. AC-30 |
| The review's frozen figure on the Goals page | The same rule, the other way round. AC-30 |
| A pending KPI amount folded into the headline | `01b` §7.2 and §14 rule 6. AC-29 |
| `manager_internal_notes`, `potential_rating`, or `overall_rating` before release | appendix D §C. **These were readable through the list API on 14 Sep** — AC-32 asserts they are gone from every Wave 4 payload |
| Another employee's draft self-review, to anyone | appendix D §C; Q-d of 14 Sep: "No" |
| Who wrote a piece of upward feedback | appendix D §C |
| A figure below the minimum group of five | `01b` §9 and §14 rule 10. `home_api.MIN_GROUP = 5` and `_suppress` already do this — AC-34 reuses them |
| A rating, score or ranking of a person against their colleagues | §19.4, refused in writing |

**The Team screen must NOT show:**

| Must not | Why |
|---|---|
| The caller's own `date_of_birth`, `gender`, `cell_number`, `branch` or `reports_to` | The live leak in bad news 1. AC-6 |
| A colleague's leave **reason or type** | `01b` §14 rule 9; Wave 3 §5. §21 D-1 |
| A report's loss-of-pay amount | Q-b of 14 Sep, pinned by Wave 3 AC-16 |
| A leaver | `status = Active` stays on the query — W1D-20's first condition |
| A count that does not equal the list beside it | §7. `team_total` and `team_capped` exist for this |
| `l2_reports` for an HR caller | Wave 1 removed it deliberately (`hr_api.py:441-460`); Wave 4 deletes the keys |

**The People screen must NOT show:**

| Must not | Why |
|---|---|
| Anyone outside the caller's scope, in the list **or** in search | Wave 1 SEC-3, SEC-4, W1D-07 |
| A phone number, an email address or an employee number | `staff_api.ROW_KEYS` — five keys, and that is the whole payload. §21 D-7 may change it, by decision, not by drift |
| A person's name in a URL | Search is POST (Wave 1 PRIV-3) |
| "Leadership" as if it meant something | §13 — there is no field and no agreed definition |

---

## 7. Numbers must equal the lists they link to

Surbhi's standing rule. Team is the screen with the most totals in the product.

| Number on screen | The list it must equal | How |
|---|---|---|
| "Team · 19" or "Showing the first 50 of 412" | the cards drawn | `team_total`, `team_capped`, `team_cap` — **already in the payload**; the screen must render them |
| "In now · 14" and "Still to come · 3" | the cards showing each chip | **one** call to `home_api._presence_counts` over the same scope condition, and the same `_suppress` |
| "Waiting on you · 2" | the rows in Waiting on you | Wave 2's approvals service, filtered to this team, computed **once** — never re-derived from the cards |
| "Needs attention · 3" | the cards carrying the chip | one pass over the same array, on the stored `trajectory` |
| "Late this week · 2" | the rows in Late this week | `get_team_late_list` returns the rows; the number is their length |
| "On leave this month · 6" | the rows in that list | one overlap query (AC-21); the total is the length of what is drawn |
| "New this month · 3" | the rows | one `date_of_joining` query inside the same scope |
| "Step 3 of 5" | the steps marked done | `pages_completed` — and a step counts as done only when it has an answer, not when it was merely opened (AC-28) |
| "2 still open from last time" | the action items listed | one query; the total is their length |
| Goal "28.4 of 39.7" | the approved reading rows | the approved figure, never approved + pending (AC-29) |
| Staff list "Showing 12 of 412" | the rows | Wave 1 already returns the total beside the capped rows |

**Rule:** where a total and a list could be computed two ways, they are computed **once**
and the list is rendered from the same array the total came from. **AC-12 enumerates
every total on all three screens from one place**, so a new total with no matching list
fails the test.

---

## 8. Stories

| # | Story | Screen | Points | Carries |
|---|---|---|---|---|
| **US-1** | As **Rahul**, I want a guided five-step self-review that saves as I go, so that I can finish it between customers without losing what I typed. | Growth · review | 8 — **split**: (a) the five steps and the read, (b) debounced autosave with a server time, (c) check and send | AC-27b, AC-28, AC-36, AC-37 |
| **US-2** | As **Rahul**, I want my review to work on its own copy of my goals, so that my manager and I are looking at the same numbers. | Growth · review | 3 | AC-30 |
| **US-3** | As **Rahul**, I want my goal card to lead with the figure that has been approved, so that I never believe a number that has not been checked. | Growth · goals | 5 | AC-29 |
| **US-4** | As **Rahul**, I want to see what is still open from last time, so that a promise made in a review does not vanish. | Growth · goals | 3 | AC-31 |
| **US-5** | As **Sandeep**, I want one Team screen that tells me who needs me today, so that I act on the two people who need me and not the nineteen who do not. | Team | 8 — **split**: (a) the stats and the list, (b) waiting on you, (c) the four lists | AC-13, AC-14, AC-15, AC-21, AC-22 |
| **US-6** | As **Sandeep**, I want "needs attention" to come from a stored trajectory and not an invented percentage, so that I can explain to a person why their name is on the list. | Team | 5 | AC-23, AC-24 |
| **US-7** | As **Sandeep**, I want one person sheet, wherever I tap a person, so that Team, People, search and the Inbox agree about who somebody is. | Team, People, search | 5 | AC-19, AC-20 |
| **US-8** | As **Priya**, I want to look a colleague up and find only the people I am allowed to find, so that a search never becomes a company directory I was not given. | People | 3 | AC-26, AC-27 |
| **US-9** | As **Kamal**, I want my Team screen to say it is my HR scope and not call fifty people my direct reports, so that the screen does not lie about what it is. | Team | 2 | AC-15 |
| **US-10** | As **Rahul**, I must never see a colleague's leave reason, a manager's internal note, a rating before release, or the name of whoever gave upward feedback — so that the portal stays safe to use in front of other people. | all three | 5 | AC-32, AC-33, AC-34, AC-35 |
| **US-11** | As **Sandeep**, I must never learn which leave type a report used from the Team screen. | Team | 3 | AC-33, D-1 |
| **US-12** | As **Rahul**, the Team screen's call must not hand my date of birth, gender and phone number to somebody's browser. | Team | 3 | AC-6 |
| **US-13** | As **Rahul**, I want every state on all three screens named, so that an empty Growth screen never reads as "you have no goals". | all three | 5 | AC-42 to AC-51 |
| **US-14** | As **Kamal**, I want every number on Team to equal the list under it, so that I never have to ask which one is right. | Team | 3 | AC-12 |
| **US-15** | As the next engineer, I want the three dead browser tests either running or gone with a reason, so that nobody counts them as coverage again. | — | 5 | AC-62, AC-63, AC-64 |
| **US-16** | As the next engineer, I want the dead `l2_reports` keys and the unused upward-feedback endpoint deleted, so that a payload nobody reads cannot grow a reader later. | — | 2 | AC-16, AC-35 |
| **US-17** | As **Sandeep**, I want to approve or decline from the Team card and see the Inbox number move, so that the two screens are never out of step. | Team | 3 | AC-13 |

**INVEST check on the three biggest.** US-1, US-5 and US-15 are all 8 or close to it.
US-1 and US-5 are split in the Points column into three deliverable pieces each. US-15
stays whole at 5 because its three parts share one fixture decision, and splitting them
would let two of the three be dropped quietly.

**The story deliberately not here:** peer feedback is §23, behind its own go/no-go.

### YouTrack-ready table

| Summary | Description | Persona | Points | ACs |
|---|---|---|---|---|
| Guided five-step self-review with autosave | Fixed five steps, not cycle-configured; debounce 3–5 s idle, max every 15 s; server-confirmed save time | Rahul | 8 (3/3/2) | AC-27b, AC-28, AC-36, AC-37 |
| The review works on its own copy | The review never reads the live goal; the Goals page never shows the review's frozen figure | Rahul | 3 | AC-30 |
| Goal card leads with the approved figure | Pending amounts named separately, never summed into the headline | Rahul | 5 | AC-29 |
| Still open from last time | Open action items across the caller's appraisals | Rahul | 3 | AC-31 |
| One Team screen | Stats, waiting on you, four lists, on Wave 1's scope and Wave 2's helpers | Sandeep | 8 (3/3/2) | AC-13 to AC-15, AC-21, AC-22 |
| Needs attention from the stored trajectory | No invented percentage; staleness named (D-3) | Sandeep | 5 | AC-23, AC-24 |
| One person sheet everywhere | One endpoint, one fixed key list, four entry points | Sandeep | 5 | AC-19, AC-20 |
| Scoped people search and staff list | Reuse Wave 1's; add designation matching | Priya | 3 | AC-26, AC-27 |
| The Team screen says what it is showing | "Your HR scope · showing the first 50 of 412" | Kamal | 2 | AC-15 |
| The negatives, asserted | Leave reason, internal note, unreleased rating, feedback author | Rahul | 5 | AC-32 to AC-35 |
| No leave type on the Team screen | Payload and screen | Sandeep | 3 | AC-33 |
| The Team call stops leaking the Employee row | Six-key `me` block on `get_manager_dashboard` | Rahul | 3 | AC-6 |
| Every state named on all three screens | Loading, empty, no data, error, no permission | Rahul | 5 | AC-42 to AC-51 |
| Every total equals its list | Enumerated from one place | Kamal | 3 | AC-12 |
| The three dead browser tests | Fixtures built, or deleted with a reason | engineer | 5 | AC-62 to AC-64 |
| Delete `l2_reports` and the minimum-less feedback endpoint | Payload keys nobody reads | engineer | 2 | AC-16, AC-35 |
| Approve from the Team card | The same service as the Inbox; the count moves | Sandeep | 3 | AC-13 |

**Do not create these in YouTrack.** That is the user's call.

---

## 9. Data model

**No new DocType. No new custom field**, unless §21 D-7 is answered "yes", which is one
`Check` field on Employee. **No patch and no migration** either way (§15).

| Shown | Doctype · field | Why an existing field carries it |
|---|---|---|
| The review's copies of goals and KPIs | the Appraisal extension's review-item child rows, written by `review_items` | slice 010 group D built them for exactly this |
| Self-rating and comment | the review item's `self_rating`, `self_comment` | on the copy, never on the live record |
| Chosen values and their example | one new key in the extension's `page_data` JSON | Text, about 64 KB. No schema change. `[ASSUMPTION]` long answers fit — AC-40 measures it |
| Went well / would do differently | `achievements_text`, `challenges_text` | already copied on submit |
| Next quarter | `development_needs_text`, `support_needed` | already there |
| Review stage | `review_status` on the extension | the existing flow: Not Started → Employee Review → Manager Review → Employee Final Review → HR Review → Completed |
| Goal approved figure | `Individual Goal.actual_progress`, `progress_pct` | written only by the approval path |
| Goal pending amount | Goal Progress Update rows still awaiting a decision | **read separately and never added** — AC-29 |
| Trajectory chip | `Individual Goal.trajectory` (`On Track` / `At Risk` / `Off Track` / `Not Started`) | **stored**, computed in `controllers/goal._update_trajectory:39`. §21 D-3 is its staleness |
| Evidence row | Goal Evidence · `validation_status`, `value`, `evidence_file` | already Pending by default, already a private file |
| Open action items | the Appraisal extension's action-item rows · `description`, `assigned_to`, `due_date`, `status` | `add_action_item:3353` writes them |
| Team row | Employee · `name`, `employee_name`, `designation`, `department`, `user_id`, `image` | **already the fixed list** at `hr_api.py:371` |
| The caller's own block | the six-key `me`: `employee`, `employee_name`, `designation`, `department`, `image`, `company` | `frame_api.ME_FIELDS:43`. **This replaces `"manager": emp`** |
| Staff row | `staff_api.ROW_KEYS` — `employee`, `name`, `title`, `department`, `image` | five keys, Wave 1's decision |
| New joiners | Employee · `date_of_joining` | one filter inside the scope subquery |
| Who reports to whom | Employee · `reports_to` | **the single source of truth** (AC-25) |

**`get_growth`'s, `get_team`'s and the person sheet's payload keys are fixed lists**, the
same discipline as `frame_api.FRAME_KEYS:49`, `ME_FIELDS:43` and `staff_api.ROW_KEYS:63`.
AC-6 and AC-20 assert them per persona, and a static check fails if any Wave 4 module
passes a `_get_employee()` result into a payload — the same check Wave 3 built.

---

## 10. Every state, on all three screens, per persona

### Growth

| Persona | Loading | Empty | No data | Error on one card | No permission | Page error |
|---|---|---|---|---|---|---|
| Rahul | skeleton ≤ 300 ms (AC-42) | no active cycle → "There is no review running right now. Your goals are below." — **never an empty wizard** (AC-43) | no goals at all → "No goals have been set for you yet. Ask your manager." (AC-44); no evidence → the goal card still shows its figure, with "No evidence has been added yet." | the card says what failed and offers Try again; the rest of Growth works (AC-46) | a review that is not his → Wave 1's no-permission sentence (AC-47) | Wave 1's page-error sentence (AC-48) |
| Sandeep | AC-42 | the same, plus "None of your team has a review open." | AC-44 | AC-46 | a review in his own reporting line on which he may not do the HR step → **the note, not a disabled button** (AC-47, slice 010 decision 34) | AC-48 |
| Priya / Kamal | AC-42 | AC-43 | AC-44 | AC-46 | AC-47 | AC-48 |
| Asha | Growth is not in her menu. `#growth` gives Wave 1's no-permission sentence | — | — | — | AC-47 | AC-48 |

### Team

| Persona | Loading | Empty | No data | Error | No permission | Page error |
|---|---|---|---|---|---|---|
| Sandeep | AC-42 | no reports at all → **Team is not in his menu**, Wave 1 decides it, and there is no empty Team screen to design (AC-49) | nothing waiting → "All clear." and the cards still show (AC-45) | one list fails → that list says so; the stats and the cards still work (AC-46) | opening a person outside his line → the refusal sentence (AC-47) | AC-48 |
| Priya (HR, no reports) | AC-42 | **her HR scope is empty** → "Nobody is in your scope yet. Ask whoever set up your access." — **never a blank screen** (AC-49, and this is W1D-20's must-not-break case) | AC-45 | AC-46 | AC-47 | AC-48 |
| Kamal | AC-42 | AC-49 | AC-45 | AC-46 | AC-47 | AC-48 |
| Rahul / Asha | Team is not in their menu | — | — | — | AC-47 | AC-48 |

### People

| Persona | Loading | Empty | No data | Error | No permission | Page error |
|---|---|---|---|---|---|---|
| Priya | AC-42 | a search with no match → the sentence that **names her real scope** ("Nobody in your store matches that.") — Wave 1's `scope_is_store` exists for this (AC-50) | the tenant has nobody but her → "There is nobody else here yet." | AC-46 | **the `staff_list` switch is off** → no entry at all, and a typed route gives the no-permission sentence, never an empty list (AC-51) | AC-48 |
| Rahul | AC-42 | AC-50 | — | AC-46 | AC-51, plus §21 D-10 | AC-48 |
| Asha | People is not in her menu | — | — | — | AC-47 | AC-48 |

**Wording** (translatable, `__()`; taken from `01b` where the designer wrote it):

| Where | Exact words |
|---|---|
| The review's copied figures | "These figures were copied into your review on 1 Oct 2026. They stay as they are while the review is open, so you and your manager are looking at the same numbers. Your live goals keep moving on the Goals page." *(`01b` §7.1, as written)* |
| A pending KPI reading | "₹3.1 L is waiting for Sakshi Verma. Logged on 10 Sep 2026 for 1 – 10 Sep. The figure above does not move until it is approved, so nobody sees a number that has not been checked." *(`01b` §7.2)* |
| The logging sheet's question | "How much since your last update? (₹ lakh) — Only the new amount. It is added to ₹28.4 L once it is approved." *(`01b` §7.2)* |
| After logging | "Sent. Your figure changes only when Sakshi Verma approves it." *(`01b` §7.2 — honest, not congratulatory)* |
| After sending a review | "Your self-review is with Sakshi Verma. You can read it, but you cannot change it now." |
| Sending it twice | "This has already been sent." |
| No cycle | "There is no review running right now. Your goals are below." |
| No goals | "No goals have been set for you yet. Ask your manager." |
| No evidence on a goal | "No evidence has been added yet." |
| An HR step inside one's own line | slice 010's existing note, reused unchanged — **do not write a second wording** |
| An HR caller's Team list | "Your HR scope · showing the first 50 of 412" |
| An empty HR scope | "Nobody is in your scope yet. Ask whoever set up your access." |
| Nothing waiting | "All clear." *(`01b` §5.7)* |
| An empty search, store HR | "Nobody in your store matches that." |
| An empty search, company HR | "Nobody in the companies you look after matches that." |
| No permission | "This page is not part of your access. Ask HR if you think it should be." *(`01b` §5.7 — Wave 1's sentence, reused, not rewritten)* |
| Already decided | "This one has already been decided." |

---

## 11. Acceptance criteria

### The live fixes — US-12, US-16

- **AC-6** *Given* any persona calls `get_manager_dashboard` (or whatever Wave 4 renames
  it to), *then* the payload's caller block is exactly `employee`, `employee_name`,
  `designation`, `department`, `image`, `company` — and **not** `date_of_birth`,
  `gender`, `cell_number`, `date_of_joining`, `reports_to` or `branch`.
  **The test must be driven from a fixture where all six forbidden fields are populated**,
  because they are populated on the real tenant today and an empty fixture would pass
  while the leak survived. A static check also fails if any Wave 4 module passes a
  `_get_employee()` result straight into a payload — the same check slice 043 built.
  **Confirmed fact:** today `hr_api.py:530` returns `"manager": emp`.
- **AC-16** *Given* the Wave 4 Team payload, *then* `l2_reports` and `l2_size` are gone,
  and a repository search finds no reader for them. **Confirmed fact:** Wave 1 recorded at
  `hr_api.py:441-460` that nothing reads them.

### US-14 · every total equals its list

- **AC-12** For every total in §7, on all three screens, for each persona fixture, the
  number equals the length of the list it links to — or, where the list is capped, the
  screen shows the capped length **and** the true total, and the test asserts both.
  **The test enumerates the totals from one place**, so a new total with no matching list
  fails it. The capped case is proved at **51 people** as well as at 981, because a cap
  that only misbehaves above a thousand is the defect slice 044 found in
  `_presence_counts`.

### US-5, US-17 · the Team screen

- **AC-13** *Given* Sandeep approves a leave request from the Team card, *then* the row
  leaves Waiting on you, **the nav count from `inbox_api.get_nav_counts` decreases by
  one**, and no second approvals query was made to draw the Team screen — asserted by
  counting calls, not by reading the screen. The Team number and the Inbox number come
  from **one** service.
- **AC-14** *Given* a tenant of 981 people and a caller whose scope is all of them,
  *then* neither the presence read, nor the leave read, nor the joiners read contains a
  literal `IN (...)` list of employee names: each carries the scope **as a subquery**, the
  way `goals_api._pending_approvals_scope_query` does. A static check fails on an
  `employee IN ({placeholders})`-shaped statement in any Wave 4 module. **Confirmed
  fact:** that exact shape is in `hr_api.py:496-504` today.
- **AC-15** *Given* Kamal, whose Team list is his HR scope and is capped, *then* the
  screen says "Your HR scope · showing the first 50 of 412" — it uses `is_hr_scope`,
  `team_total`, `team_capped` and `team_cap`, which are **already in the payload**, and it
  never calls fifty people his direct reports. *Given* Sandeep, a plain manager, *then* it
  says "Your team · 19" and `is_hr_scope` is false.
- **AC-21** *Given* a leave application from **28 August to 3 September** and another from
  **2 October to 4 October**, *when* the September Team screen is opened, *then* the first
  appears in "On leave this month" and the second does not. **This fails today**:
  `hr_api.py:522` filters `from_date >= mo_start`. The test is written to fail on the
  current code first.
- **AC-22** *Given* three people joined on 1 September, *then* "New this month · 3" lists
  exactly those three, inside the caller's scope, Active only, and a fourth who joined in
  another company that the caller cannot see is absent.

### US-6 · needs attention

- **AC-23** *Given* a team where one goal's stored `trajectory` is `Off Track`, one is
  `At Risk` and one is `On Track`, *then* "Needs attention" lists the first two and not
  the third, and **no percentage appears anywhere in the rule**. A static check finds no
  numeric threshold literal (`75`, `0.75`) in the Team modules. **Confirmed fact:** the
  prototype's 75 % has no source in the product.
- **AC-24 (D-3) · a stale chip is named, not shown as fact.** **Confirmed fact:**
  `trajectory` is written in `validate` only (`alvoraa_goals/controllers/goal.py:36-54`),
  so a goal nobody saves keeps September's answer in December. *Given* a goal whose
  `modified` is more than **14 days** old, *then* the chip carries the date it was last
  worked out ("On Track, as of 10 Sep") — `01b` §14 rule 12 — **and a stale `On Track` is
  not counted in "Needs attention"**. The interval is a constant in one place, not a
  literal in three. **Recommendation, not built:** recomputing on read would be a write on
  a read path, which §19.5 rules out; a nightly recompute is the right answer and is
  **its own ticket**, not Wave 4's.
- **AC-25** *Given* the demo tenant, where the org chart and `reports_to` disagree about
  Rahul's manager, *then* every Wave 4 screen names the manager from
  **`Employee.reports_to`**, and a test asserts the chart's answer is not used. §21 D-9
  carries the data fix; the code does not wait for it.

### US-8 · People

- **AC-26** *Given* Sakshi has 13 direct reports, *when* Rahul opens People, *then*
  "Also reporting to Sakshi Verma" lists the people whose `reports_to` is Sakshi —
  **not** the people who share Rahul's position. **Confirmed fact:** `my_view.peers`
  means the latter today. The count says 13 and the list has 13 rows, or says what it is
  capped at.
- **AC-27** *Given* a search for "cashier", *then* people whose **designation** matches
  are returned as well as people whose name matches, inside the caller's existing scope,
  with `%` and `_` still escaped and the call still POST. Wave 1's scope tests still pass
  unchanged.

### US-7 · one person sheet

- **AC-19** *Given* a person is tapped on Team, on People, in a search result and on an
  Inbox row, *then* **the same endpoint** answers all four, and a test asserts there is
  exactly one whitelisted person-sheet function in Wave 4's modules.
- **AC-20** *Given* the person sheet, *then* its payload keys are exactly §9's fixed list
  for the caller's persona, and **`personal_email`, `cell_number` and `gender` are absent
  for every persona**, including a manager about a direct report. The fixture populates
  all three. **Confirmed fact:** appendix D TM-08 recorded `get_employee_scorecard`
  returning them to a manager on 14 Sep.

### US-1, US-2, US-3, US-4 · Growth

- **AC-27b** *(numbered `b` on purpose, so nothing already written moves; cite as
  045 AC-27b)* *Given* a cycle whose `page_config` is **empty**, *then* the review still
  shows five steps including the goals step. **Confirmed fact:** the current wizard shows
  no goals page for such a cycle (B14), and Q2 on the demo tenant is exactly that cycle.
- **AC-28** *Given* Rahul opens step 2 and types nothing, *then* step 2 is **not** marked
  done and "step n of 5" does not move. **Confirmed fact:** today any save marks a page
  done (appendix D G-02).
- **AC-29 (`01b` §14 rule 6)** *Given* a goal with an approved figure of 28.4 and a
  pending reading of 3.1, *then* the headline reads **28.4**, the pending amount is named
  in its own line in §10's wording, and **no payload key anywhere carries 31.5**. A test
  asserts the two numbers travel as separate keys and that no code adds them.
- **AC-30 (`01b` §14 rule 5)** *Given* an open review, *when* the live goal's approved
  figure changes, *then* the review's figure does **not** move; and *when* the review's
  copy is rated, *then* the Goals page's figure does **not** move. Asserted in both
  directions in one test, because one direction alone has passed before while the other
  leaked.
- **AC-31** *Given* two action items from the previous cycle, one assigned to Rahul and
  one to his manager, *then* "Still open from last time" lists both with who owns each,
  and Rahul can close only the one assigned to him.
- **AC-36** *Given* Rahul sends his review, *then* his manager is notified — one
  notification, to the manager from `reports_to` only, carrying the employee's name and
  the cycle and **nothing from inside the review**. **Confirmed fact:**
  `submit_employee_review:4419` sends nothing today (B25). The notification must **not**
  use the `eval_js` helper appendix D recorded as B26.
- **AC-37** *Given* Rahul stops typing, *then* a save happens after 3–5 s of idle, at most
  once every 15 s, plus on step change, blur and page hide, and **the time shown is the
  server's confirmed time**, not the browser's. An unchanged step sends nothing. A test
  counts the calls over a scripted typing pattern.
- **AC-40** *Given* a 60 KB answer in one step, *then* it saves and reloads unchanged, or
  the screen refuses it with a sentence before it is lost. `[ASSUMPTION]` `page_data` is
  Text at about 64 KB — **confirm on the bench before the wizard commit**.
- **AC-41** *Given* the "What your manager will see" block, *then* every line in it is
  true of the code on the day it ships, and a static check fails on any sentence in the
  Growth modules that asserts a behaviour the product does not have. **This is Wave 3's
  lesson applied before the mistake** — its revision 1 shipped a false remedy.

### US-10, US-11 · the negatives

- **AC-32** *Given* a review with `manager_internal_notes`, `potential_rating` and an
  unreleased `overall_rating` all populated, *when* the employee's own Growth screen and
  every Wave 4 endpoint are called as that employee, *then* none of the three values
  appears in any payload. **The fixture populates all three**, because on 14 September
  they were readable through the list API and an empty fixture would pass.
- **AC-33** *Given* a team where somebody is on **Sick Leave** today, *when* Sandeep and
  Priya open Team, *then* per §21 D-1's answer either the leave type is absent from the
  payload entirely, or it appears **only** on an approval row that person is the approver
  of. The assertion names "Sick Leave" and every other Leave Type on the fixture, against
  the serialised payload. **Confirmed fact:** `hr_api.py:498` and `:520` select
  `leave_type` today, so this test goes red before the change.
- **AC-34** *Given* a group of four people, *then* every aggregate about them is
  suppressed, **and the next-smallest group in the same table is suppressed with it**
  (`01b` §14 rule 10). Reuses `home_api._suppress` and `MIN_GROUP = 5` — a second
  implementation fails the test.
- **AC-35** *Given* upward feedback with two responses, *then* no detail is shown and no
  author name appears in any payload. `goals_api.get_upward_feedback:1113`, which has
  **no** minimum and no caller, is **deleted**, and a call-by-hand test proves it is gone
  from the whitelist. **Confirmed fact:** appendix D B22.

### US-13 · states

- **AC-42** Skeletons for Growth, Team and People are in the server-rendered HTML and
  paint within **300 ms**, median of 5, on the W1D-09 rig ("Slow 4G", 4× CPU slow-down,
  cache off).
- **AC-43** No active cycle → §10's sentence and the goals still render. Never an empty
  wizard and never a spinner that stops.
- **AC-44** No goals → §10's sentence. The cycle header still renders.
- **AC-45** Nothing waiting → "All clear." and the cards still show.
- **AC-46** One card or list failing leaves the rest of the screen working, with
  Try again.
- **AC-47** A review that is not the caller's, a person outside their scope, and an HR
  step inside their own reporting line each give **a sentence** — and the third is
  slice 010's existing note, **not a disabled control**. Three wordings, none a raw error.
- **AC-48** `get_growth` or `get_team` failing shows Wave 1's page-error sentence with a
  code holding no personal data.
- **AC-49 (W1D-20's must-not-break case)** *Given* Priya, store HR with no direct reports,
  *then* her Team screen is **not empty** — it is her store. *Given* an HR person whose
  scope genuinely contains nobody, *then* §10's sentence, never a blank.
- **AC-50** An empty search names the caller's **real** scope, using Wave 1's
  `scope_is_store`.
- **AC-51** *Given* a tenant **without** the `staff_list` switch, *then* there is no
  People entry anywhere, and calling `get_staff_list` by hand is refused on the server
  with the refusal written to the security log with no personal content. Wave 1 built
  this; the test is re-run because the screen moves.

### Cross-cutting

- **AC-52** Wave 4 adds **no new Jinja include template** — the pinned set stays at the
  three in `test_only_the_pieces_that_need_jinja_are_templates`, and a fourth fails it.
  Growth, Team and People each get their own markup file under
  `templates/includes/ess/parts/`, containing **no `{{` and no `{%`** (or `ess_part()`
  refuses it at run time), and their own static style and script files under `public/`
  with a `?v=` stamp. **Confirmed fact:** OPS-31 landed as `a2439e3`; 12 parts measured
  faster than one include file (0.1541 s against 0.1600 s).
- **AC-53** Every whitelisted function in `growth_api.py` and `team_api.py` is in the
  registry test with Guest-refused, wrong-persona and scope cases (Wave 1 SEC-2).
- **AC-54** `growth_api.py` and `team_api.py` contain no `ignore_permissions`, no `global`
  and no module-level mutable state (Wave 1 SEC-6, SEC-15). Where existing code uses
  `ignore_permissions` after a scope check, the check is **before** the flag and a test
  proves the order, not merely its presence.
- **AC-55** Every string added is inside `__()`; no sentence is assembled from fragments;
  the review's guidance is one message per block with placeholders, so Hindi and Punjabi
  word order works (Wave 5).
- **AC-56** At 390 px, light and dark, for all personas: no text under 12 px, no target
  under 44 px, no sideways scroll. **The rating buttons are measured explicitly** — `01b`
  finding N4 measured them at 32 px on a phone, on the one screen that has to finish in
  two minutes. The same passes with the Hindi fixture (W1D-12).

### The edge cases that bite

- **AC-57** *Mid-cycle joiner.* Somebody who joined halfway through the quarter is not
  drawn as Off Track for having had half the elapsed time. The rule names the case; it
  does not silently divide.
- **AC-58** *Leaver.* A person set to Left does not appear on any Team list, any People
  list, any search result or any "needs attention" count — `status = Active` is on the
  query, not applied afterwards.
- **AC-59** *Employee with no manager.* Their Growth screen says who their review would go
  to, or says plainly that nobody is set, and Send is refused with a sentence rather than
  failing.
- **AC-60** *Circular reporting line.* Two people who report to each other do not make any
  Team or People read loop or time out. A fixture proves it.
- **AC-61** *Concurrent decisions.* Two people approving the same goal update: one
  succeeds, the other gets "This one has already been decided.", and the goal's approved
  figure moved exactly once.
- **AC-65** *Re-hired employee.* A second Employee record for the same person appears once
  per record and is not merged or de-duplicated by the screen — the screen shows what the
  data says.
- **AC-66** *Multi-company.* An HR person for company A sees nobody from company B on any
  of the three screens, including in "New this month" and "Needs attention".
- **AC-67** *A goal with no target value.* `_update_trajectory` returns early and leaves
  `trajectory` unset; the card shows "Not set yet", never "Off Track" and never 0 %
  (`01b` §14 rule 11).
- **AC-68** *A cycle with no rating scale.* The review shows the scale it has or says it
  has none; it does not fall back to a hard-coded 1–5 list. **Confirmed fact:**
  `get_rating_scales:1956` exists and `get_my_review` does not return the scale today.
- **AC-69** *Cancelled and amended.* A cancelled Appraisal is not listed; an amended one is
  listed once, under its current name.
- **AC-70** *Time zone.* "New this month" and "On leave this month" use the **site's**
  month, and a browser in another time zone does not shift them.
- **AC-71** *Bulk import.* 400 employees imported with no `reports_to` do not turn any
  manager's Team screen into the whole tenant. **This is the exact leak W1D-20 closed**,
  and it is pinned here because Wave 4 rebuilds the screen on top of it.
- **AC-72** *An employee who is their own manager.* `reports_to` pointing at itself does
  not put the person on their own Team list or in their own "also reporting to" list.

### US-15 · the three dead browser tests

- **AC-62** `scripts/run_dom_tests.js` has an **empty `SKIP` map**, or every remaining
  entry names a ticket and a date. **Confirmed fact:** today it skips
  `portal_tree_test.js`, `portal_redesign_test.js` and `portal_appraisal_test.js`, and its
  own comment attributes them to "Wave 3" — **which is wrong; they are the Growth screens,
  and Growth is Wave 4.** Correct the comment in the same commit.
- **AC-63** The `get_performance_tree` fixture the first two need **exists as a tracked
  file** — captured from a real call on the `test044s` fixture site, with names replaced
  by fixture names, and with a test that fails if the payload's shape drifts from what the
  endpoint returns. Two of the three then run in CI.
- **AC-64** `portal_appraisal_test.js` either drives a panel that exists — the new Growth
  panel — **or it is deleted in a commit that says why**, and the count of browser tests in
  CI is asserted so a fourth cannot go missing unnoticed. **A deleted test with a reason is
  honest; a skipped test counted as coverage is not.**

---

## 12. Known defects Wave 4 meets, and what it does about each

| # | Defect (appendix D) | State at `8718f27` | What Wave 4 does |
|---|---|---|---|
| B4 | The self-review writes records the employee does not own | **Fixed** (slice 010 group D; `submit_employee_review:4419`) | Renders it; AC-30 guards the copy rule |
| B2 | Evidence approves itself | **Fixed** — `validation_status: "Pending"` | Renders it; AC-29 says so in words |
| B3 | Evidence files are public | **Fixed** — `claim_evidence_file`, private | No change |
| B6 | Ratings leak before release; manager-only fields via the list API | **Fixed** by slice 010 | **AC-32 re-asserts it on every Wave 4 payload**, because Wave 4 adds new payloads |
| B7, B9 | A manager reads a draft; the HR guard is skipped | **Fixed** by slice 010 | AC-47 renders the note |
| B11 | `my_view` and `chain_to_top` skip the reach limit | **Fixed** by slice 010 | Not touched |
| B12 / W6 | The org chart names a different manager than `reports_to` | **Unchanged — a data problem** | AC-25 picks one source; §21 D-9 carries the data fix |
| B13 | The wizard hard-codes seven generic principles | Unchanged | Replaced; §21 D-5 picks the master list |
| B14 | A cycle with an empty `page_config` has no goals page | Unchanged | AC-27b |
| B15 | "Saved `<i class=ic-check></i>`" shows raw markup | Unchanged | Fixed while the wizard is rebuilt |
| B18 | "In now" never counts today; the month-leave filter is wrong | **Unchanged** (`hr_api.py:482`, `:522`) | AC-14 (reuse Wave 2's presence) and **AC-21** |
| B22 | An upward-feedback endpoint with no minimum and no caller | **Unchanged** (`goals_api.py:1113`) | **Deleted**; AC-35 |
| B24 | A goal update moves progress before approval, and a reject does not undo it | **Fixed** by slice 010 | Rendered honestly; AC-29 |
| B25 | No manager notification when a review is sent | **Unchanged** | **AC-36** |
| B26 | A notification helper pushes a script to the browser | **Fixed** by slice 010 | AC-36 must not reintroduce that path |
| TM-03 | "Needs attention" has no rule; 75 % is invented | Unchanged | AC-23 on the stored trajectory |
| TM-05 | The month-leave filter | see B18 | AC-21 |
| TM-06 | "New this month" does not exist | Unchanged | AC-22 |
| TM-08 | One person sheet, two endpoints, and one leaks contact details | Unchanged | AC-19, AC-20 |
| TM-09 | Direct versus any-level reports are mixed | **Closed by W1D-20** | Recorded, not re-opened |
| PE-02 | "Peers" means same position, not same manager | Unchanged | AC-26 |
| PE-06 | Search matches the name only | Unchanged | AC-27 |
| **New** | `get_manager_dashboard:530` returns the whole Employee row | **Live today** | **AC-6** |
| **New** | `on_leave_today` is raw SQL with one `%s` per person | **Live today** | AC-14 |
| **New** | `l2_reports` / `l2_size` have no reader | Live today | AC-16 |
| **New** | `trajectory` is only recomputed when the goal is saved | Live today | AC-24; the nightly recompute is its own ticket |
| **New** | Three browser tests have never run and are attributed to the wrong wave | Live today | AC-62 to AC-64 |

---

## 13. Out of scope for Wave 4, and where it goes instead

| Thing | Where it goes |
|---|---|
| **Peer feedback (give and ask)** | **§23 — its own go/no-go at the end of this wave**, 009 design decision 4. Not in the wave's body, not in its estimate, and not a dependency of anything above |
| The org chart | **Not touched.** It stays behind `plan_org_structure` (W1D-21). Its cross-company leak is **`ALV-86`, Critical**, and Wave 4 neither waits for it nor works around it (W1D-08) |
| "Leadership" and "other floors" in the directory | **Dropped.** No field, no agreed definition (PE-05). It needs a brief, not a spec line |
| Calibration, performance setup and policy compliance as designed screens | **Later** — `01b` §11: each needs its own design run. They stay in their current look inside the new frame |
| HR's own review queues and the calibration matrix | **Later**, same reason. Slice 010 built them; Wave 4 does not redraw them |
| Org-health numbers on the chart | With the chart |
| A nightly trajectory recompute | **Its own ticket.** AC-24 makes the staleness visible; fixing it properly is a scheduled job and belongs with `alvoraa_goals` |
| Trimming the other four whole-Employee-row endpoints (`get_portal_context`, `get_employee_dashboard`, `get_expense_claims`, `get_checkin_status`) | **Their own small slice**, as slice 043 recorded, **with a go-live date against it**. Wave 4 fixes **only** the one it opens |
| Skill and designation-skill options in the review | §21 D-6. Until answered, a free-text box, which is what the data supports |
| Hindi and Punjabi for users | **Wave 5 (046)**; Wave 4 wraps strings and measures in Hindi fixtures only (W1D-12) |
| Compression | Slice 036 |

---

## 14. Non-functional requirements for this slice

**This section deliberately carries no invented query count.** Four budgets in Waves 1
and 2 were wrong the day they were written and failed at twenty people as badly as at 981
(042 `03b` §3). **The rule now is: measure, then write it down, and flatness is the gate.**

| What | Requirement |
|---|---|
| Calls on Growth | **1** (`get_growth`) beyond the frame's two, plus one per action |
| Calls on Team | **1** (`get_team`) beyond the frame's two. Today the page makes four (appendix D §D) |
| Calls on People | **1** (`get_staff_list`, which exists and costs **2 queries flat**) |
| Query counts | **Measured on `test044` (981 people) and `test044s` (20 people)** with slice 044's harness `measure_044.run` — three warm-up calls, then 20 measured — **before** any budget is written into this spec. The number is then recorded as a note |
| **The gate** | **The count is identical at 20 people and at 981**, for every persona. A change that moves a count by one and keeps flatness is fine; a change that keeps the count and breaks flatness is not |
| **The scope rule** | Every scope goes **into the query as a subquery**, never as an `IN (...)` of ids (`nfr-budget.md`, from a measured ×5 slope). AC-14 |
| p95 | ≤ **500 ms** on the W1D-09 rig, over 20 warm calls. Waves 1 and 2 pass everywhere at ≤ 215 ms, so this is generous and is not the thing to worry about |
| Payload size | `get_team` ≤ **40 KB**, `get_growth` ≤ **40 KB**, the person sheet ≤ **8 KB**, `get_staff_list` unchanged. **Asserted in bytes** in the same test as the query count, because a count stays honest while a payload grows |
| Skeleton painted | ≤ 300 ms, median of 5 (AC-42) |
| Screen usable | ≤ 2.5 s p95 of 20 loads, with slice 036's compression live |
| Every list | capped, with the true total shown. Team at `TEAM_LIST_CAP = 50`, staff at 12 shown / 50 maximum — **both already built** |
| Background work | **None.** The review's autosave is a foreground call by design: a person needs to know it saved |
| Record volume assumed | 1,000 employees; 2–4 goals each; 4 reviews per person per year; about 212 evidence rows per quarter on the real PP Jewellers copy |
| Retention | **Nothing new is stored**, unless §21 D-7 adds one consent field. Counsel's rule of 18 Sep 2026 — performance records kept for employment + 6 months, then erased — **is engaged by this slice's subject matter** and is not changed by it. §19.5 |
| Personal or sensitive data | Self-assessments, manager notes, ratings, trajectories. **A self-review is among the most sensitive text an employee writes**, and it is free text, so it can contain anything |
| Accessibility | WCAG 2.2 AA; 390 px; 200 % zoom; 12 px floor; 44 px targets. **The rating buttons are the named risk** (`01b` N4) |

**One thing measured and reusable, so nobody rebuilds it:** `home_api._presence_counts`
runs in **12.0 ms for a System Manager at 981 people** (042 `03b` D6), driving off
Attendance's date index. The `LEFT JOIN` shape was 51.9 ms and the name-list shape
52.9 ms. **Use the helper.**

---

## 15. Data migration and backfill

**Nothing, with one conditional exception.**

No patch, no backfill, no schema change — **unless §21 D-7 is answered "yes"**, which adds
one `Check` field on Employee (`alvoraa_share_contact`, default **0**). That is a JSON
field and one `bench migrate`, with **no data backfill**: everybody starts un-shared, which
is the only safe default for a consent flag. If D-7 is answered "no" or "later", this
section stays "nothing".

**Two things that are not migrations and must still happen:**

1. **Seed the demo copy.** Appendix D records that the Q2 cycle has an empty `page_config`,
   that every evidence row in demo data is Approved, that there are almost no open
   requests, and that check-ins stop on 6 September. **Without seeding, most of §11 passes
   for the wrong reason.** A Growth test on a tenant with no open review proves nothing.
2. **Fix the reporting-line mismatch** (§21 D-9). A data action for HR on the tenant, not a
   code change.

**Rollback:** reverting the Wave 4 commits restores today's Growth, Team and People panels.
**Two exceptions worth naming:** AC-16 and AC-35 **delete** payload keys and an endpoint; a
revert brings them back, so rollback is clean, but **each deletion ships in its own commit**
so the revert is one step (release gate 2). About ten minutes, like Wave 1's (W1D-10).

---

## 16. Notifications and messages

Wave 4 adds **one** notification and changes none.

| Message | Trigger | Recipient | Change | Must never carry |
|---|---|---|---|---|
| "Your report has sent their self-review" | `submit_employee_review` sets Manager Review | **the manager from `reports_to` only** | **New — AC-36.** Reuses the existing notification helper; it must **not** use the `eval_js` path appendix D recorded as B26 | **Anything from inside the review.** Not a rating, not a sentence, not a value the employee chose. The name and the cycle, and a link |
| Goal update needs approval | `submit_goal_update` | the approver | none (`_notify_manager_of_goal_update:1195` exists) | the employee's other goals |
| Goal update decided | `approve_goal_update` | the employee | none | the approver's private comment, unless the product already shows it |
| Evidence needs approval | `submit_goal_evidence` | the approver | **Extend** — it should notify; whether it does today is `[UNVERIFIED — engineer to confirm]` | the file's contents |
| Review stage advanced | `advance_review_status` | as today | none | manager-only fields |

**Every on-screen message is in §10's table.** No notification, email or push preview in
this wave carries a rating, a self-assessment sentence, a leave reason or a pay figure.

---

## 17. Localisation and accessibility

- Every string in `__()`. The review's guidance and the "copied on" sentence are **whole
  messages with placeholders**, never joined fragments — a date and a name move in word
  order between English, Hindi and Punjabi (AC-55).
- Dates and numbers through the existing formatter. A goal's `unit` is free text and is
  **not** translated — it is the tenant's own word, and translating it would change data.
- Measured at 390 px in light and dark with the Hindi fixture (AC-56, W1D-12).
- **Rahul is a shop-floor worker with no laptop, doing a five-step review on his own phone
  between customers.** On a phone: one step per screen, the rating buttons at least 44 px
  (`01b` N4 measured 32 px — this is the single most likely accessibility regression in the
  wave), the step rail collapses to "3 of 5", and the autosave time is visible without
  scrolling.
- Colour is never the only signal. Every trajectory chip says its state in words —
  "On Track, as of 10 Sep" — which is also how AC-24's staleness is shown.
- `01b` §9 records one gap Wave 1 owed: **focus is not yet trapped inside the sheet and
  returned to the control that opened it**. The person sheet is a sheet. **If Wave 1 did
  not close it, Wave 4 inherits it** — §21 D-11.

---

## 18. Audit and traceability

| What must be reconstructable a year later | How |
|---|---|
| What an employee wrote in their review, and when | The Appraisal extension's `page_data` and named fields, plus Frappe's Version rows (change tracking is on) |
| What the manager rated, and what they wrote privately | The review's copies and `manager_internal_notes`, with Versions |
| Who approved a goal reading or a piece of evidence, and when | Goal Progress Update and Goal Evidence rows carry the approver and the date; `alvoraa_goals` writes an audit log entry (`_append_audit_log`) |
| Why a person was on "needs attention" on a given day | **Not reconstructable, and we are not making it so.** The trajectory is a current-state field; AC-24 shows the date it was worked out. **Storing a daily per-person attention history would be a new record about a person with no purpose tag** — §19.5 |
| Who read whose review | **Not recorded today.** Wave 1's residual risk R3 owns read-logging (W1D-17: a cheap logging first step by 2026-10-15). Wave 4 adds no signal and does not pretend to |
| The deleted endpoint and payload keys | The deletion commits are the record; AC-16 and AC-35 keep them gone |

---

## 19. Compliance-impact sub-analysis

*The analyst is not a lawyer. Nothing below is a legal ruling.*

### 19.1 Data touched

| Field / object | Sensitivity | Purpose it was collected for | Lawful basis (as recorded) | New collection? |
|---|---|---|---|---|
| Own self-assessment text | **sensitive** — free text about a person, written by them, which can contain health, family or grievance content nobody asked for | performance management | employment | No |
| Own ratings and comments on the review's copies | **sensitive** | performance management | employment | No |
| `manager_internal_notes` | **sensitive** — written about a person, not by them | performance management | employment | No |
| Overall and potential rating | **sensitive** — it affects pay and progression | performance management | employment | No |
| Goal progress, evidence and trajectory | internal, and **sensitive in aggregate** — a trajectory is a judgement about a person | performance management | employment | No |
| Upward feedback about a manager | **sensitive**, and the author must stay hidden | management development | employment | No |
| A colleague's name, designation, department, photo | internal | working together | employment | No |
| A colleague's **leave type** | **sensitive** — it can imply a medical or family circumstance | leave administration | employment / statutory | No, but §21 D-1 decides whether it keeps being **shown** |
| A colleague's phone number or email | internal, and **a contact detail is the thing people most object to sharing** | contact | employment | **Only if §21 D-7 says yes** — and then with a consent flag, default off |

**Nothing new is collected** by the wave as specified. §21 D-7 is the only path to a new
field, and it is a consent flag, which collects nothing about a person beyond their own
choice.

### 19.2 Obligations engaged

| Obligation | Source | What this slice must do | Feature that does it |
|---|---|---|---|
| DPDP minimisation | baseline §5 | Fixed payload key lists on every new endpoint; the six-key `me` block replacing a whole Employee row | AC-6, AC-20 |
| DPDP access — a person may see their own record | baseline §4 | Growth is the access path to a person's own review for 400 people with no desk login | US-1 to US-4 |
| Purpose limitation on performance data | baseline §5 | Manager-only fields never reach the employee; the employee's draft never reaches the manager | AC-32, AC-47 |
| Retention: performance records for employment + 6 months, then erased | **counsel's note, 18 Sep 2026** | Wave 4 stores no second copy and creates no new per-person record | §19.5, AC-24's "no write on a read path" |
| Small-group suppression | `01b` §9, §14 rule 10 | Minimum of five, and the next-smallest group suppressed too | AC-34 |
| Logging duties — no personal content | baseline §5, CERT-In | Refusals logged without names or document ids | AC-54, Wave 1 PRIV-5 |
| OWASP ASVS 5.0 L2 access control | baseline §4 | Scope checked **before** any `ignore_permissions`, order proved | AC-54 |

**Checked `compliance-feature-map.md` first:** `access.permitted_employees`,
`access.log_refusal`, `home_api._suppress` and slice 010's conflict-of-interest rule all
exist and are **reused, not respecified**.

### 19.3 Visibility delta

| Who | Can now see | Could they before? |
|---|---|---|
| Rahul | his own review's own copy of his goals, and the date it was taken | **New on screen**; the copy already existed |
| Rahul | the approved figure and the pending amount as two numbers | **New, and narrower in effect** — today one bar implies the pending amount has landed |
| Rahul | "still open from last time" | **New**; the records existed with no reader |
| Sandeep | his team's trajectory chips with the date they were worked out | **New on screen**; the field existed |
| Sandeep | a colleague's **leave type** | **Today: yes, on the Team screen.** §21 D-1 decides; my recommendation makes it **narrower than today** |
| An HR caller | the leave types of up to 50 people in their HR scope | **Today: yes**, since W1D-20 widened `team_ids` from a manager's reports to an HR person's scope. **This is a widening nobody asked for, and it is recorded here rather than absorbed** |
| Any caller | their own `date_of_birth`, `gender`, `cell_number`, `branch`, `reports_to` in the Team payload | **Today: yes.** AC-6 **removes it** |
| A manager | a report's `personal_email`, `cell_number`, `gender` through the person sheet | **Today: yes** through `get_employee_scorecard`. AC-20 **removes it** |
| Anyone | a colleague's phone number or email in the directory | **No**, unless §21 D-7 says yes with consent |
| Anyone | who wrote upward feedback | **No** |
| Anyone | a colleague's draft self-review | **No** |

**Three rows get narrower and one is a widening inherited from W1D-20.** Nothing else
gets wider. The inherited widening is named rather than absorbed — §21 D-1.

### 19.4 Decision automation

**Wave 4 touches two places where the product makes, or shapes, a judgement about a
person.** Neither is new; both become visible here.

| Question | Answer |
|---|---|
| What is automated | **(a) The trajectory chip.** `_update_trajectory` decides "On Track / At Risk / Off Track" from elapsed time against progress, with no human involved. **(b) "Needs attention", which is built on it** and puts a person's name on a manager's screen |
| Is it a decision about a person? | **It shapes one.** It does not set pay or a rating, but it decides whose name a manager reads first, and that reliably shapes a conversation and sometimes a review |
| Accountable human | **The manager.** The chip is input to their judgement, and the screen must say so: it describes a goal's progress against its dates, not a person's worth |
| Where they intervene — before | Real: the goal's target and dates are set by a person |
| Where they intervene — during | **Nowhere, and it does not need one** — nothing is decided and nothing moves |
| Where they intervene — after | The manager decides what to do, and the employee sees the same chip on their own goal, so there is no hidden list |
| What the employee is told | **The same chip, with the same words, on their own Goals screen.** AC-24's "as of" date applies to both. **A manager must not see a judgement about a person that the person cannot see** — that is this wave's rule, and AC-23 pins the wording to one place so the two screens cannot drift |
| How they contest it | By changing the facts — logging a reading, adding evidence, asking for the target to be changed — and by talking to the manager. **There is no recorded, clocked grievance route in the product**; counsel's note of 18 Sep 2026 records it as "not built, handled by hand". **Wave 4 must not draw a "contest this" control that leads nowhere** |
| Is the system deciding alone? | **No**, and it must stay that way. §21 D-2's answer must not turn "needs attention" into a score |

**No AI in this slice.** No rating set by a model, no inference, no emotion, voice or
facial analysis, no passive behavioural monitoring, no individual-level surveillance.
§19.7 is empty by construction.

**Two prohibitions genuinely approached, and refused here in writing:**

1. **A ranking of people.** "Needs attention" is one design step from a league table, and a
   stored trajectory makes it a one-line query. **Wave 4 shows a manager a list of goals
   that are behind their own dates, in the order the goals appear. No score, no ordering by
   performance, no comparison between colleagues, no "most improved", anywhere.** If a
   ranking is ever asked for, it needs the baseline read first, not a spec.
2. **A per-person attention history.** Storing who was on the list, day by day, would
   create a shadow performance record with no purpose tag and no retention period. §18
   records that it is **not** built.

### 19.5 Retention and deletion

**Nothing changes, and one rule is engaged rather than inherited.**

Counsel's binding note of 18 September 2026 sets **performance records at employment +
6 months, then erased**. That period covers precisely the records this wave renders:
appraisals, review copies, ratings, manager notes, goals and evidence. **Wave 4 adds no new
record, no second copy and no derived store**, so the period applies unchanged and this
slice does not need a new answer.

Three things deliberately **not** stored, each of which would be a new personal record:

1. **That a person read their own review, or that their manager read it.** Read-logging is
   Wave 1's R3 (W1D-17), not Wave 4's, and doing half of it here would be worse than
   neither.
2. **A daily trajectory or "needs attention" history** (§19.4).
3. **That the employee was shown the "what your manager will see" block.** The record is the
   review; the screen is a rendering of it.

**AC-24's consequence, stated:** showing a stale chip with its date is a *rendering*
choice. **Recomputing on read would be a write on a read path**, which is exactly the shape
§19.4 and Wave 3 AC-61 both rule out. That is why the nightly recompute is its own ticket.

### 19.6 Open compliance questions

| Question | Who must decide | What it blocks |
|---|---|---|
| **May a manager, or an HR person, see which leave type a colleague used on a team screen?** Today they can. `01b` §14 rule 9 says no screen shows a colleague the reason for an absence | **Surbhi**, and it is worth a privacy view | Nothing in the build — §21 D-1 has a fail-closed default (drop it from the payload). It blocks the release note, because this is a **narrowing** and HR should be told, not surprised |
| **May a colleague's work phone number and email appear in the directory, and does that need consent under DPDP, or is it employment context?** | **Surbhi, with an advisor.** `01b` §13 and appendix D PE-07 both flagged it and neither ruled | Nothing — the default is "no contact detail", which is what `staff_api` ships |
| **Does a trajectory chip shown to a manager amount to a decision about a person that must be explainable and contestable?** It is not a rating and it triggers no automated action, but it puts a name on a list | **Surbhi, with an advisor** | Nothing in the build. AC-23 and AC-24 are written to be truthful either way |
| **Is "employment + 6 months, then erased" being applied to Appraisal, its extension, Individual Goal and Goal Evidence today?** Counsel set the period; I could not find the job that enforces it | **Surbhi, with the security engineer.** `[UNVERIFIED — I found no retention job for performance records in this repository]` | Nothing in Wave 4. It is **recorded debt, not a silent assumption** |

### 19.7 AI features

**None.** Nothing in this slice is AI-shaped. See §19.4's two refusals.

---

## 20. Traceability

| Source | ID or line | Story | Acceptance criteria | Status |
|---|---|---|---|---|
| Plan §4 Wave 4 | "the guided 5-step self-review on existing endpoints" | US-1 | AC-27b, AC-28, AC-37 | covered |
| Plan §4 Wave 4 | "with debounced autosave" | US-1 | AC-37 | covered |
| Plan §4 Wave 4 | "and a notification to the manager on send" | US-1 | AC-36 | covered — **new work; B25 was never fixed** |
| Plan §4 Wave 4 | "goals with evidence on one progress model" | US-3 | AC-29 | covered — one model, chosen: the approved figure |
| Plan §4 Wave 4 | "open action items" | US-4 | AC-31 | covered |
| Plan §4 Wave 4 | "one Team call" | US-5 | AC-13, AC-14 | covered |
| Plan §4 Wave 4 | "needs attention" | US-6 | AC-23, AC-24 | covered |
| Plan §4 Wave 4 | "late this week" | US-5 | AC-33 | covered — reused from Wave 3, unchanged |
| Plan §4 Wave 4 | "on leave" | US-5 | AC-21, **D-1** | covered; the visibility half needs D-1 |
| Plan §4 Wave 4 | "new joiners" | US-5 | AC-22 | covered |
| Plan §4 Wave 4 | "one person sheet" | US-7 | AC-19, AC-20 | covered |
| Plan §4 Wave 4 | "a permission-scoped directory and search" | US-8 | AC-26, AC-27, AC-50, AC-51 | **mostly built already** — Wave 1's `staff_api` and `search_people` |
| Plan §4 Wave 4 | "Feedback (give and ask) needs a new record type" | — | §23 | **its own go/no-go** — 009 design decision 4 |
| Plan §4 Wave 4 | "Wave 0a must be done" | — | §12 | **done** — slice 010 groups A–D are on `origin/dev` at `8718f27`, verified by reading |
| Appendix D | G-01 to G-12 | US-1 to US-4 | AC-27b to AC-31, AC-36, AC-37 | covered; G-07 is §23 |
| Appendix D | SR-01 to SR-08 | US-1, US-2 | AC-27b, AC-28, AC-30, AC-36 | covered |
| Appendix D | TM-01 to TM-09 | US-5, US-6, US-7, US-9 | AC-12 to AC-25 | covered; TM-09 closed by W1D-20 |
| Appendix D | PE-01 to PE-08 | US-8 | AC-26, AC-27, AC-50, AC-51 | covered; PE-05 dropped (§13); PE-08 out of scope |
| Appendix D | B1 to B28 | — | §12 | every one placed: fixed, fixed here, or out of scope with a reason |
| Design `01b` §7.1 | a review works on its own copy | US-2 | AC-30 | covered |
| Design `01b` §7.2 | a KPI reading is an increment; the headline is the approved figure | US-3 | AC-29 | covered |
| Design `01b` §14 rule 1 | no greyed items | US-13 | AC-51 | covered |
| Design `01b` §14 rule 5 | the review never reads the live goal | US-2 | AC-30 | covered |
| Design `01b` §14 rule 6 | a pending amount is never folded in | US-3 | AC-29 | covered |
| Design `01b` §14 rule 8 | one's own reporting line cannot do the HR step, and sees a note | US-13 | AC-47 | covered — slice 010's note reused |
| Design `01b` §14 rule 9 | no screen shows a colleague the reason for an absence | US-11 | AC-33, **D-1** | **conflicts with what the code does today** — D-1 |
| Design `01b` §14 rule 10 | minimum group of five, and the next-smallest too | US-10 | AC-34 | covered |
| Design `01b` §14 rule 11 | a figure that cannot be trusted says "Needs review" | US-6 | AC-67 | covered |
| Design `01b` §14 rule 12 | every total carries the date its data runs to | US-6 | AC-24 | covered |
| Design `01b` §14 rule 14 | every screen measured at 390 px in Hindi | US-13 | AC-55, AC-56 | covered |
| Design `01b` N4 | rating buttons 32 px on a phone | US-13 | AC-56 | covered — named explicitly |
| Design `01b` §9 | focus trapping in the sheet is not done | — | **D-11** | **open — inherited from Wave 1** |
| 009 design decision 3 | who's off: presence only | US-11 | AC-33 | the same rule, applied to Team — **D-1** |
| 009 design decision 4 | peer feedback last, with its own go/no-go | — | §23 | covered by construction |
| Q21 | reporting line or org chart | US-6 | AC-25, **D-9** | **closed in code** (`reports_to`); the data fix is open |
| Q22 | who approves evidence; progress only after approval | US-3 | AC-29 | **closed by slice 010** — Pending by default, progress on approval |
| Q23 | values: pick 2 or rate all 7; which master list | US-1 | **D-5** | **open** |
| Q24 | rate goals or KPIs; whole or half points | US-1 | **D-4** | **open** |
| Q25 | peer feedback | — | §23 | **its own go/no-go** |
| Q26 | team scope: direct or everyone below | US-5, US-9 | AC-15 | **closed by W1D-20** |
| Q27 | "needs attention" rule and new joiners | US-6 | AC-23, AC-57, **D-2** | covered; the exact rule needs D-2 |
| Q28 | what "Leadership" means; work phone and email | US-8 | §13, **D-7** | Leadership **dropped**; contact detail open |
| W1D-20 | the Team screen follows HR scope | US-5, US-9 | AC-15, AC-49, AC-71 | covered, including both must-not-break cases |
| W1D-21 | the staff list has its own switch | US-8 | AC-51 | covered |
| W1D-22 | a tenant System Manager sees the whole tenant on Team | US-9 | AC-15 | covered — the screen says what it is showing |
| W1D-08 | the org chart's cross-company leak is ALV-86 | — | §13 | **not worked around**; recorded |
| W1D-09 | the measurement rig | — | AC-42, §14 | covered |
| W1D-12 | Hindi measured in fixtures only | US-13 | AC-56 | covered |
| W1D-23 | a budget moves when the measurement says so | — | §14 | covered — **no budget is written here before it is measured** |
| Wave 1 SEC-2, SEC-6, SEC-12, SEC-15 | endpoints safe on their own; fixed key lists | US-12, US-13 | AC-6, AC-53, AC-54 | covered |
| Wave 2 `home_api` | one presence calculation | US-5 | AC-14 | covered by reuse |
| Wave 2 `inbox_api` | one approvals service | US-17 | AC-13 | covered by reuse |
| Wave 3 AC-16 | a manager learns days, never the amount | US-11 | AC-33 | covered — pinned again because Wave 4 renders it |
| Slice 043 finding 1 | five endpoints leak the whole Employee row | US-12 | AC-6 | **one of the five fixed**; the other four stay pinned (§13) |
| ALV-111 | three jsdom tests have never run | US-15 | AC-62 to AC-64 | covered — **and the ticket's wave attribution is corrected** |
| `nfr-budget.md` | a scope belongs in the query | US-5 | AC-14 | covered |
| Prototype | Growth, self-review, Team, People screens | US-1 to US-9 | as above | covered, with §22's eleven differences |

**Gaps, listed rather than hidden:**

| Gap | Why it is a gap |
|---|---|
| **No `01c` for this slice** | The permission matrix is built from Waves 1–3. A Wave 4 `01c` will add checks; this spec goes to revision 2 when it lands |
| **No `07` for this slice** | §14 has no measured numbers yet, by design. `OPS-W4-n` items are not written |
| **No design run for Growth, Team and People** | `01b` §11 says so explicitly. §22 records every place this spec goes beyond the prototype |
| D-1 to D-11 | §21 |
| The other four whole-Employee-row endpoints | Pinned by slice 043; **their own slice, with a go-live date against it** |
| A retention job for performance records | §19.6, `[UNVERIFIED]` |
| Focus trapping in the sheet | D-11, inherited from Wave 1 |

---

## 21. Needs a decision

**Eleven, and only four of them stop a commit.** Everything else has a fail-closed default
written into an acceptance check, so the build starts without it.

| # | Question | My recommendation | Blocks? |
|---|---|---|---|
| **D-1** | **May a colleague's leave type appear on the Team screen?** `on_leave_today:498` and `month_leaves:520` select it today, and after W1D-20 an HR caller gets it for up to 50 people. `01b` §14 rule 9 and Wave 3 §5 both say no | **Presence only on the Team screen.** The lists say who is away, not why. **Leave type stays on the approval row**, where the approver is deciding that specific request and needs it. This is narrower than today, so it goes in the release note. Until answered, the **default is to drop it from the payload** — fail closed | **Blocks the two leave lists**, not the screen |
| **D-2** | **What exactly is "needs attention"?** (Q27) The prototype's 75 % is invented; the stored `trajectory` is real | **Stored `trajectory` in (`At Risk`, `Off Track`)**, with AC-24's staleness rule and AC-57's joiner rule. No percentage anywhere. It is explainable to the person named, which a percentage is not | While building |
| **D-3** | **The trajectory is only recomputed when a goal is saved.** A goal nobody touches keeps an old answer | **Ship AC-24** — show the date it was worked out, and do not count a stale On Track as attention-worthy — **and raise the nightly recompute as its own ticket.** Recomputing on read is a write on a read path and §19.5 rules it out | While building |
| **D-4** | **Rate goals or KPIs, and whole or half points?** (Q24) Rahul has 11 Q2 KPIs, 6 of them linked to goals | **Rate the goals, in whole points**, with the KPI figures shown beside each goal. Eleven rating boxes on a phone between customers is the review nobody finishes. `[ASSUMPTION]` — the usability test in `01b` §12 is the evidence that would settle it | **Blocks step 1 of the wizard** |
| **D-5** | **Values: pick two with an example, or rate all seven criteria? Which master list —** `Company Value` **or HRMS's** `Employee Feedback Criteria`**?** (Q23) Two sources describe the same thing | **Pick two with an example, from `Company Value`** — it is the tenant's own list and PP Jewellers has five real ones. Rating seven generic criteria is what the current wizard does, and it is why nobody reads the answers. **HRMS's template stays the desk's; the portal does not write it** | **Blocks step 2 of the wizard** |
| **D-6** | **Where do the "one thing to get better at" options come from?** (SR-05) The prototype's list is invented; `Skill` has 9 rows and `Designation Skill` is empty | **A free-text box for v1.** Nine skills is not a list, and an empty designation table means most people would see nothing. Revisit when a tenant has filled it in | While building |
| **D-7** | **May a colleague's work phone number and email appear in the person sheet, and does it need an opt-in?** (Q28, PE-07) There is no consent field anywhere today | **Not in Wave 4.** Ship the sheet with `staff_api`'s five keys. If it is wanted, it is **one `Check` field on Employee, default 0** (§15) and a row on the person's own account screen — a small, honest feature, not a line in this spec | While building; the default is "no" |
| **D-8** | **There is no design run for these three screens** — `01b` §11 says so. This spec specifies behaviour the prototype only sketches | **Run a short design pass on the self-review wizard only**, before its commit. Team and People are re-dresses of screens that exist and can proceed. The wizard is the one screen with a two-minute budget and a 32 px control that already failed measurement | **Blocks the wizard's commit**, not the wave |
| **D-9** | **The org chart and `reports_to` disagree about who somebody's manager is** (W6/B12) | **Fix the data.** `reports_to` is the source of truth in code (AC-25) whatever happens, but leaving the chart wrong means two screens in one product name two different managers. `reporting_mismatches` already exists for HR. A tenant action on Surbhi's word | No — the code does not wait |
| **D-10** | **Does a plain employee get the staff directory at all, or is it HR-only?** `staff_api`'s docstring calls it "a plain searchable staff list **for HR**"; the prototype shows People to everyone; W1D-21 left the commercial question open | **Employees too, on tenants with the switch.** The scope helper already gives an employee their own reporting line and nothing more (W1D-07), so there is no new exposure — and "look a colleague up" is the most-used feature of every portal we benchmarked. **Confirm, because the code's own comment says HR** | **Blocks People's menu rule** |
| **D-11** | **Focus is not trapped in the shared sheet and not returned to the control that opened it** (`01b` §9). The person sheet is a sheet | **Confirm whether Wave 1 closed it.** If it did not, Wave 4 cannot claim WCAG 2.2 AA for the person sheet, and it should be fixed in the frame, once, not per screen | No, unless AA is claimed |

**Not decisions, stated so they are not mistaken for one:** `get_manager_dashboard`'s
whole-Employee-row payload (**P1** — live, on both client tenants, on a screen HR uses
daily), the month-leave filter (**P2**), the `IN (...)` scope in `on_leave_today` (**P3**),
the dead `l2_reports` keys and the minimum-less upward-feedback endpoint are **defects**.
They are fixed by AC-6, AC-21, AC-14, AC-16 and AC-35 and need no ruling. **The order I
would fix them in:** the Employee row first, the month filter second, the `IN (...)` third.

---

## 22. Differences from the approved prototype

The prototype is a review artifact and **is not changed**; this is the record. **`01b` §11
says Growth, Team and People were deliberately not redesigned in the design run**, so this
list is longer than Wave 3's and that is expected, not a surprise.

| # | Prototype | Built | Why |
|---|---|---|---|
| a | A single progress bar per goal | The **approved** figure leads, with the pending amount named separately | `01b` "Bad news" 2 and §7.2. A single bar makes a person think their number moved when it did not |
| b | "Needs attention (Q2 < 75 %)" | The stored `trajectory`, with the date it was worked out | The 75 % has no source in the product (appendix D TM-03) |
| c | "Also reporting to Sakshi · 9" showing 8 people | Peers by `reports_to`, and the count equals the list | Sakshi has **13** reports. Design correction D5 already fixed the number; the meaning was still wrong |
| d | A feedback-received card, with "give" and "ask" controls | **Not built in the wave's body.** §23's go/no-go decides | 009 design decision 4 |
| e | "Leadership / other floors" in the directory | **Not built** | No field, no agreed definition (§13) |
| f | Contact details on the person sheet "when they choose" | **Not built** — five keys, no phone, no email | There is no consent field. D-7 |
| g | Example approvals, goal evidence and team status shown with a **Sample** tag | Built on real rules | `01b` D8 already moved three of them to real rules; this spec names the data source for each |
| h | "Switch to the full desk" beside a manager on the person sheet | Not drawn for a plain manager | W1D-19 — the server returns `None`, and the prototype was wrong, not the code |
| i | The Team screen implies every row is a direct report | For an HR caller it says "Your HR scope · showing the first 50 of 412" | W1D-20 and W1D-22. The prototype predates both |
| j | The self-review shows all seven generic principles | Two chosen values with an example, per D-5 | B13. The seven are hard-coded in the current wizard, and nobody reads the answers |
| k | Rating buttons 32 px tall on a phone | ≥ 44 px | `01b` finding N4, measured |

---

## 23. Peer feedback — the separate go/no-go

**This is not part of Wave 4's body.** 009 design decision 4: *"Last in Wave 4, with its
own go/no-go before it is built."* It is specified here so the decision can be taken with
real numbers, and it is deliberately outside §8's stories, §14's budgets and the wave's
estimate. **Nothing above depends on it.**

### What it would be

Give feedback to a colleague, and ask a colleague for feedback: who it is from, who it is
about, the text, an optional company value, whether it is public or private to the
recipient, and when.

### What it would cost, said plainly

| Part | Cost |
|---|---|
| A new DocType with its permission rules and a `permission_query_conditions` hook | 1 day |
| Give, ask, list-mine and list-about-me endpoints, each with Guest / wrong-persona / scope tests | 1 day |
| The screen, on three surfaces (Growth, Team, People) | 1 day |
| The visibility rules and their tests — the expensive part, see below | 1 day |
| **Total** | **about 4 days**, matching the plan's estimate |

### What it risks

1. **The obvious reuse is not safe.** **Confirmed fact**, read in
   `hrms/hrms/hr/doctype/employee_performance_feedback/employee_performance_feedback.json`:
   the **`Employee` role holds `read`, `write`, `create`, `submit`, `cancel`, `export`,
   `print` and `share`** on `Employee Performance Feedback`, and **`hrms/hooks.py` has no
   `permission_query_conditions` entry for it**. Extending that doctype means every
   employee in the tenant can list and **export** every feedback record about everyone
   until we write those rules ourselves. A new DocType of our own, with the rules written
   alongside it, is the safer build and probably the cheaper one.
2. **`appraisal` is a required field on it**, so it cannot hold feedback given outside a
   review cycle — which is most of the point.
3. **Nobody has asked for it.** `01b` §10 point 2: *"the least evidenced… nobody has asked
   for it in any evidence I can see."* The frontline job — "know what I am measured on, and
   that it is fair" — is served by Waves 2 and 3.
4. **It is the one feature in the redesign that creates new personal data about a person,
   written by another person.** That engages counsel's retention rule, a visibility
   decision, and a question nobody has asked: **can a person see feedback written about
   them, and can they contest it?** If the answer is "not always", it is a hidden record
   about an employee, which is exactly what §19.4 exists to stop.
5. **Anonymity is the trap.** "Ask for feedback" tends to become anonymous feedback, and
   anonymous feedback about an individual, retained and readable by a manager, is a
   different product with a different compliance profile. `get_upward_feedback_received`
   already sets the precedent that got this right: **totals only, minimum three responses,
   author hidden.**

### My recommendation

**No-go for now, and say why rather than letting it slip.** Build Wave 4's body, run
`01b` §12's usability test, and put peer feedback in front of real PP Jewellers people as a
question rather than a screen. **If it is a go**, three conditions before a line is
written: a new DocType of our own (not the HRMS one), the visibility rules decided before
the build and not during it, and a `01c` of its own — because it is the only part of this
redesign that creates a new personal record.

**Rough sizing if it goes ahead:** US-F1 give (5), US-F2 ask (5), US-F3 see what is about
me (3), US-F4 the must-not stories (5). **18 points, about 4 days**, plus the `01c`.

---

## 24. Ready check

| Box | State |
|---|---|
| Brief approved | ✓ — the 009 plan (Wave 4) and the decisions stand in for `01` |
| Clickable prototype reviewed | **Partly** — reviewed 22 Sep, but `01b` §11 says Growth, Team and People were **deliberately not redesigned**. §22 records eleven differences. **D-8** asks for a short design pass on the wizard |
| `01c` security and privacy written | **✗ — not written.** This spec is revision 1 until it lands |
| `07` DevOps inputs written | **✗ — not written.** §14 carries no measured number on purpose |
| Every state designed and specified per persona | ✓ §10 |
| Gap analysis verified in source | ✓ §4, with file and line |
| Stories: personas, sized, "must not" stories | ✓ §8 — US-10, US-11, US-12 and US-14 are the "must not" stories |
| Every story has checks with observable oracles | ✓ §11 |
| Traceability complete | ✓ §20, with the gaps listed |
| Permission matrix with negatives | ✓ §6 |
| Edge cases | ✓ AC-57 to AC-72 |
| NFR numbers | **Deliberately unset** — §14 names the sites, the harness and the gate. Setting them before measuring is the mistake four earlier budgets made |
| Migration stated | ✓ nothing, unless D-7 (§15) |
| Compliance sub-analysis | ✓ §19 — including the two places this wave shapes a judgement about a person |
| No prohibited capability | ✓ nothing AI-shaped; the two prohibitions approached (a ranking, an attention history) are refused in writing in §19.4 |
| Open questions owned, none blocks day 1 | **Partly** — the server work (US-12, US-5's lists) starts today. **D-4, D-5 and D-8 block the wizard's commit; D-1 blocks two lists; D-10 blocks People's menu rule.** All five have a fail-closed default |
| Frappe details verified in source | **Partly** — AC-40 (`page_data` size) and the evidence notification in §16 are `[UNVERIFIED]` and need one bench run |
| The three dead browser tests are owned | ✓ US-15, and the ticket's wave attribution is corrected |

**Verdict, plainly: ready to start, not ready to finish.** The five server items are
specified, verified in source and independent of every open decision — and one of them
closes a live leak on a screen HR uses every day. The wizard needs three answers and a
short design pass. **And this spec is revision 1 by construction: it has no `01c` and no
`07`, and it goes to revision 2 when they land, exactly as Waves 2 and 3 did.**

**The order I would build in:** the six-key `me` block on the Team call (P1, one hunk),
then the month-leave filter and the `IN (...)` scope, then the two deletions in their own
commits, then the Team and People re-dresses, then the wizard once D-4, D-5 and D-8 are
answered.

---

## Open questions

| # | Question | Owner | Blocks | Can the build start without it? |
|---|---|---|---|---|
| 1 | D-1 — a colleague's leave type on the Team screen | Surbhi | Two lists, and the release note | Yes — the default drops it |
| 2 | D-2 — the "needs attention" rule | Surbhi | The card | Yes — AC-23 is the default |
| 3 | D-4 — rate goals or KPIs, whole or half points | Surbhi | Step 1 of the wizard | **No** — the step cannot be built either way |
| 4 | D-5 — values: pick two, and which master list | Surbhi | Step 2 of the wizard | **No** |
| 5 | D-6 — where the skill options come from | Surbhi | One field | Yes — free text |
| 6 | D-7 — contact details on the person sheet, and consent | Surbhi, **with an advisor** | One field, and a DPDP question | Yes — the default is "no contact detail" |
| 7 | D-8 — a design pass on the self-review wizard | Surbhi, with the UX designer | The wizard's commit | Yes for Team and People |
| 8 | D-9 — the reporting-line data fix | Surbhi, with tenant HR | Nothing in code | Yes |
| 9 | D-10 — does a plain employee get the staff directory | Surbhi | People's menu rule | **No** — one line either way, and it is a visibility decision |
| 10 | D-11 — focus trapping in the shared sheet | The engineer, then Surbhi | A WCAG 2.2 AA claim | Yes |
| 11 | **§23 — peer feedback: go or no-go** | **Surbhi** | Nothing above it | Yes — by construction |
| 12 | Is "employment + 6 months" being enforced on performance records today? | Surbhi, with the security engineer | Nothing here | Yes — recorded debt |

## Assumptions

- `[ASSUMPTION]` `page_data` on the Appraisal extension is a Text field of about 64 KB and
  holds a long five-step answer. Appendix D says it was never tested with long answers.
  **Confirm on the bench before the wizard commit** — AC-40.
- `[ASSUMPTION]` `submit_goal_evidence` notifies the approver. I could not find the call.
  `[UNVERIFIED — engineer to confirm]`.
- `[ASSUMPTION]` Fourteen days is the right staleness window for a trajectory chip
  (AC-24). It is a judgement, not a measurement; it is a constant in one place so it can be
  changed in one place.
- `[ASSUMPTION]` `get_team_goals`'s 22 queries for 19 people and `my_view`'s 31 are still
  true. They were measured on 14 Sep and slice 044 did not re-measure them. **They are the
  two calls most likely to break flatness**, so measure them first.
- `[ASSUMPTION]` The demo copy can be seeded with an open review cycle, pending evidence and
  open requests through `demo/` scripts. Without it most of §11 passes for the wrong reason
  (§15).
- **Confirmed fact, not an assumption:** slice 010 groups A–D are on `origin/dev` at
  `8718f27`. `submit_employee_review:4419` checks ownership and writes to copies;
  `submit_goal_evidence` saves Pending with a private file. Wave 4's Growth work stands on
  that being true, and it is.
- **Confirmed fact:** `hr_api.py:530` returns `"manager": emp`, the whole Employee row.
  Read today, on the branch this spec was written on.

## Release gates (not acceptance checks)

1. **Wave 4's panels wait for Wave 1 to reach `dev`**, and OPS-31 must not reach
   **production** until ALV-112's asset refresh is on `main` and one deploy has proved it.
   The same condition Waves 2 and 3 carry.
2. **Each deletion ships in its own commit** — `l2_reports` (AC-16) and
   `get_upward_feedback` (AC-35) — so a rollback is one step.
3. **The leave-type change (D-1) goes with a release note.** HR and managers have been
   seeing it; stopping is a narrowing and they should be told, not surprised.
4. **Demo data seeded on the local copy before the test run** (§15), or most Growth tests
   pass for the wrong reason.
5. **The three browser tests run in CI, or are deleted with a reason**, before the wave is
   called done (AC-62 to AC-64). A skipped test counted as coverage is how this was missed
   for months.
6. **The `staff_list` switch is ticked on the tenants that should have People**, per W1D-21
   and D-10. A configuration action on Surbhi's word on the day.

## Handoff note

**To the security and privacy engineer:** this slice needs its own `01c`, and four things
deserve your eye first. **The `manager` key** — `hr_api.py:530` hands the whole Employee row
to the Team screen today, on both client tenants, and it is the one of slice 043's five
that this wave opens anyway. **The leave type** — `on_leave_today` and `month_leaves` both
carry it, and W1D-20 widened who receives it from a manager's reports to an HR person's
scope; D-1 is a privacy decision, not a design one. **§19.4** — the trajectory chip shapes
a judgement about a person, and the employee must see the same chip the manager does;
please read that as a requirement. **§23** — peer feedback is the only part of this
redesign that creates a new personal record, and the HRMS doctype's `Employee` role
permissions are the reason not to reuse it.

**To the DevOps engineer:** this slice needs its own `07`. §14 names no query budget on
purpose — four earlier budgets were wrong the day they were written. The two calls to
measure first are `get_team_goals` (22 queries for 19 people on 14 Sep) and `my_view` (31),
because they are the two most likely to be **not flat**. Use `test044` and `test044s` and
slice 044's harness. The scope rule from `nfr-budget.md` is AC-14, and there is a live
`employee IN ({placeholders})` in `hr_api.py:496-504` to prove it against.

**To the fullstack engineer:** three things are easy to build the old way and are the ones
`01b` §14 warns about. **The review must never read the live goal, and the Goals page must
never show the review's frozen figure** (AC-30 asserts both directions, because one has
passed alone before). **A KPI reading is an increment and the headline is the approved
figure** (AC-29 fails if any code adds the two). **Reuse Wave 2's `_presence_counts`,
Wave 2's approvals service and Wave 1's `staff_api`** — a third presence calculation is how
"in now" got wrong in the first place. Build §7's "one total, one list" rule before any
card, not after.

**To the test engineer — five tests here are easy to write so that they prove nothing.**
**AC-6** must use a fixture where all six forbidden Employee fields are **populated**; an
empty fixture passes while the leak survives (Wave 3's exact mistake). **AC-33** must name
"Sick Leave" against the serialised payload, and it must go **red on today's code** first —
`hr_api.py:498` and `:520` select `leave_type`, so it will. **AC-21** must be driven from
leave that **began last month**; written the other way round it passes and proves the
opposite. **AC-30** must assert **both** directions in one test. **AC-12** must enumerate
the totals from one place, so that a total added later with no list fails it rather than
being missed.

**To the product manager:** two things in the plan did not survive contact with the code,
and you should know before the estimate is reused. **Wave 4 is smaller than it looks** —
Team's scope, the staff list, search, the presence calculation and the approvals service
are all already built, so the wave is one new screen (the wizard), two re-dresses and five
defect fixes. **And peer feedback is the only genuinely new record type in the whole
redesign**, which is why §23 keeps it separate. My recommendation there is no-go for now,
with a reason rather than a slip.
