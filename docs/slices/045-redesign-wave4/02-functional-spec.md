---
slice: 045-redesign-wave4
artifact: 02-functional-spec
author: hrms-business-analyst
date: 2026-09-24
revision: 2
status: draft, revised 2026-09-24 after Surbhi's two decisions of that day — peer feedback is out of Wave 4 entirely, and the Team screen separates the two reasons a person is on it. Then extended the same day: the leave rule covers the written reason as well as the type, the `01c`'s two questions came back accepted, and SEC-17 became `ALV-117`. See "What changed in revision 2" below. **This slice's `01c` landed while revision 2 was being written** (`d1ef233`, revision 2, already carrying both of Surbhi's decisions), and its eight required spec changes are absorbed here. **There is still no `07`.** — see "What is missing before this is ready" below
inputs: [01c-security-privacy-requirements.md (045, revision 2, `d1ef233`), ../009-ess-portal-redesign/00-assessment-and-plan.md §4 Wave 4 and Appendix D, ../009-ess-portal-redesign/appendix-d-growth-team-people.md, ../009-ess-portal-redesign/01b-ux-design.md, ../009-ess-portal-redesign/00f-decisions-2026-09-22.md, ../034-redesign-wave1/00g-decision-register.md (W1D-01 to W1D-23), ../034-redesign-wave1/02-functional-spec.md revision 4, ../034-redesign-wave1/03-implementation-notes.md, ../042-redesign-wave2/02-functional-spec.md revision 2, ../042-redesign-wave2/03b-implementation-notes-044-followups.md, ../043-redesign-wave3/02-functional-spec.md revision 2, ../043-redesign-wave3/03-implementation-notes.md, .claude/context/nfr-budget.md, prototype-v2.html]
brief: there is no `01` for this slice. The approved brief is `../009-ess-portal-redesign/00-assessment-and-plan.md` (Wave 4), the design is `../009-ess-portal-redesign/01b-ux-design.md`, and the decisions are in `00f-decisions-2026-09-22.md` and `../034-redesign-wave1/00g-decision-register.md`
---

# Wave 4 — Growth, Team and People: functional spec

## What changed in revision 2

**Two decisions Surbhi took on 24 September 2026, and four things that followed from
them.** All are written into the spec in place; this list is so nobody works from a printout
of revision 1.

| # | Revision 1 said | The decision | Where it is written | Effect |
|---|---|---|---|---|
| **1** | Peer feedback is "last in Wave 4, with its own go/no-go", specified in §23 with a 4-day cost | **Peer feedback is out of Wave 4 entirely — not deferred inside it, removed.** Surbhi: *"leave the peer feedback we will build it as a specific process run intentionally, by the HR, with specific organisational level purpose, not open. we will do a separate market analysis and build the complete specification for this."* That is a **different product** from the always-available feature §23 costed: a programme HR starts, for a stated purpose, with a beginning and an end | §23 is now four sentences and a pointer. The reasoning and the route live in **ALV-116** | §23's body, its stories and **its 4-day estimate are struck** — the estimate was for a different thing and must not be carried forward. Nothing in Wave 4 depended on it |
| **2** | The Team screen was one list, with `is_hr_scope` as a label on the whole screen (W1D-20) | **The Team screen separates the two reasons a person is on it, and the actions follow.** Two sections — "Your team (4)" then "You cover (38)" — with a different action set on each. **Approved in full** | New **§6a**, with AC-73 to AC-82. §4, §5b, §6, §7, §8, §10, §19.3 and §22 follow it | **This closes D-1**: leave type appears on the approval row for a person's own reports and **nowhere else**. It also makes the server work bigger than revision 1 said — one capped list becomes two, each with its own count |
| **3** | "This spec is revision 1 until the `01c` lands" | **The `01c` landed** — `d1ef233`, and it is itself revision 2, written against these same two decisions. It sets `SEC-1` to `SEC-19` and `PRIV-1` to `PRIV-13`, and its verdict lists **eight changes `02` must make before code** | All eight are applied: AC-6, AC-14, AC-19, AC-23, AC-32, AC-33, AC-76, AC-77, AC-82, and three new checks AC-83 to AC-85. §20 carries the `SEC`/`PRIV` traceability | **The security verdict is "ready to build".** What is still missing is the `07` |
| **4** | The leave decision was written about `leave_type`. Revision 2's first pass mentioned `description` but **no acceptance criterion named it as a value to search for** | **The same rule and the same assertion now cover both fields.** `description` is the employee's own written reason, it travels in the same payload at `hr_api.py:508-516`, and **it is the more personal of the two** — "father in hospital" is worse to leak than "Sick Leave". A rule about the category would have looked followed while leaking the worse half | **AC-76 rewritten**: the fixture populates both fields on both people, each field is asserted independently, and **the payload is searched recursively for the fixture strings instead of checking two named keys** — a two-key check passes the moment a third key carries the same value. AC-33 follows it | Also §4, §5b, §6, §6a, §12, §19.1, §19.3, §20, §21 and release gate 3 |
| **5** | The `01c`'s two questions back to me were answered but still marked "his to correct" | **Both accepted, neither overruled**, and one came back better than I wrote it. **PRIV-8 / AC-86**: accepted as written, plus his requirement that every withhold reason says **why** a field is plumbing — "internal" is not a reason — and his framing of why an unclassified field must be reachable: **fail closed means fail towards the person the data is about.** **PRIV-10 / SEC-19**: there was no clash to win. PRIV-10 governs records **about the subject**; a capacity and a preference are **outside its scope, not exceptions to it** | AC-86, §15, §19.5, §20 | **§15 no longer proposes an amendment.** Two exceptions in a list become three, and the third would be a real performance field with a good story |
| **6** | `045 SEC-17` was an open check: is `Employee Performance Feedback` readable tenant-wide? | **Answered by a census run read-only on production, and re-homed as `ALV-117`** — a dated go-live blocker. **Not live today** (no readers, no rows); **live on the day the DTC staff load creates the logins**, because the load creates the readers and the appraisal cycle behind it creates the rows, and the two are scheduled together | §23, bad news 5, §20, §24, open questions | **Nothing from the `01c` is left hanging in this spec.** Peer feedback leaving the wave did not take the finding with it |

**Why decision 2 matters beyond the layout.** W1D-20 widened `team_ids` from a manager's
direct reports to an HR person's whole scope — up to 50 people — and the leave type went
with it. The approved design's rule 9 forbids exactly that. Two sections with two action
sets is what makes the narrowing buildable rather than a special case bolted onto one
list. **It is narrower than today, so it needs a release note** — release gate 3.

---

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
   absence. Wave 3 `02` §5 forbids it outright. **Surbhi settled it on 24 September and the rule wins:**
   presence only on every list, card and chip, with the leave type **and the employee's own
   written reason** kept **only** on the approval row for a person's **own direct reports**,
   where the approver is deciding that request. §6a, AC-76. **The reason matters more than
   the type** — "father in hospital" is worse to leak than "Sick Leave" — and it travels in
   the same payload at `hr_api.py:508-516`. **It is narrower than today, so it ships with a
   release note.**
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
5. **Peer feedback is out of Wave 4, and the permission finding is why it could never
   have been a quick add.** **Confirmed fact**, read in
   `hrms/hrms/hr/doctype/employee_performance_feedback/employee_performance_feedback.json`:
   the **`Employee` role holds `read`, `write`, `create`, `submit`, `cancel`, `export`,
   `print` and `share` on the whole doctype**, with **no `permission_query_conditions`
   entry for it in `hrms/hooks.py`** — so extending it means every employee in the tenant
   can list and **export** every feedback record about everyone until we write those rules
   ourselves. `appraisal` is also a **required** link, so it cannot hold feedback given
   outside a review cycle. **Feedback is a trust feature that one export ends
   permanently.** Surbhi removed it from the wave on 24 September; it becomes a process HR
   runs on purpose, and it gets its own market analysis and its own specification.
   **ALV-116**, §23. **And the doctype's own exposure now has a ticket and a date:
   `ALV-117`.** The census was run read-only on production — **it is not live today**, because
   nobody holds the role and there are no rows, **and it goes live on the day the DTC staff
   load creates the logins**, since the load creates the readers and the appraisal cycle
   behind it creates the rows. **Not Wave 4's to fix. Not anybody's to forget.**

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
| `01c-security-privacy-requirements.md` (045) | **landed — `d1ef233`, revision 2** | It added `SEC-1` to `SEC-19` and `PRIV-1` to `PRIV-13` and asked for **eight changes here**, all applied in this revision. The two that touch Surbhi's decisions are **SEC-18** (the action matrix is a permission matrix and every row is enforced on the **server**, with the section **derived** and never taken from the request) and **SEC-19** (`alvoraa_decided_as` is written from the server's own derivation, never from the request body). **Its verdict is "ready to build".** |
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

**Story and check numbers are per slice.** This slice runs `US-1` to `US-20` and `AC-1`
to `AC-86`. Revision 2 added US-18 to US-20 and AC-73 to AC-82 for the Team screen's two
sections (§6a), AC-83 to AC-85 for the three checks the `01c` asked for, and AC-86 for
PRIV-8, whose oracle the `01c` left open; nothing already written moved. **Security and privacy items are cited as "045 SEC-n" and
"045 PRIV-n"** and come from this slice's own `01c` (`d1ef233`, revision 2). Wave 1, Wave 2 and Wave 3 each have their own `US-1` and `AC-1`. Cite these
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
reused from Wave 2), leaves (who is off — status only, §6a), org structure (who may see whom, the
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
| **Team — the list and its scope** | **Built in Wave 1.** W1D-20 rebuilt `get_manager_dashboard` on `permitted_employee_filters()`: HR scope for an HR caller, own direct reports for a plain manager, `status = Active` kept, capped at `TEAM_LIST_CAP = 50` (`hr_api.py:17`) with `team_total`, `team_capped` and `is_hr_scope` in the payload so the screen can say what it is not showing | **Extend — this grew in revision 2.** The scope rule W1D-20 decided is **not** re-decided; what changes is that it is now served as **two lists, not one**: direct reports, and HR scope minus direct reports (§6a). Each is capped and carries its own total. **Do** also fix the `manager` key (bad news 1) and the leave-type reads (bad news 2, now decided — §6a) |
| **Team — "in now / still to come"** | **Built in Wave 2** as `home_api._presence_counts` + `_scope_filters` + `_suppress`, rewritten in slice 044's follow-ups as two aggregates with the scope **in the query**. 12.0 ms for a System Manager at 981 people | **Reuse the helper.** A third presence calculation is the thing this project keeps being bitten by |
| **Team — "waiting on you"** | **Built in Wave 2** as the approvals service behind `inbox_api`, with `get_nav_counts` flat in headcount | **Reuse.** The Team screen's number is the Inbox's number filtered to this team, computed once (§7) |
| **People — the staff list** | **Built in Wave 1.** `staff_api.get_staff_list`, its own opt-in switch `staff_list` (W1D-21), five payload keys, Active only, capped at 50, **2 queries flat from 20 people to 981** | **Re-dress only.** Add the person sheet on top of it |
| **People — the org chart** | Unchanged, behind `plan_org_structure` (W1D-21). **`ALV-86` is open and Critical**: the chart shows every company and store (W1D-08) | **Not touched.** Wave 4 does not work around ALV-86 and does not wait for it |
| **People — search** | **Built in Wave 1.** `search_people` narrowed to the store for store HR, Active caller only, escaped wildcards, POST only | **Reuse unchanged** |
| **Growth — the endpoints** | **Fixed by slice 010 group D**, on `origin/dev`. Review copies, ownership checks, evidence Pending, private files, stage checks | **Genuinely new screens on safe endpoints** |
| **Growth — the 5-step wizard** | The current wizard hard-codes seven generic principles, has no goals page for a cycle with an empty `page_config`, and shows raw markup in its "Saved" line (B13, B14, B15) | **New build** |
| **Growth — the two behaviour changes** | `01b` §7.1 (a review works on its own copy) and §7.2 (a KPI reading is an increment, and the headline is the approved figure) | **New build.** These are the two `01b` §14 items most likely to be quietly lost |
| **Open action items** | `add_action_item:3353` and `update_action_item_status:3379` exist; the second has no caller | **Extend** — a "my open action items" read across appraisals |
| **Peer feedback** | Nothing fits, and the HRMS doctype is unsafe to extend (bad news 5) | **Out of Wave 4 entirely.** Surbhi, 24 Sep 2026. It becomes an HR-run process with a stated purpose, after its own market analysis and its own spec — **ALV-116**, §23 |

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
| The list and its scope | `hr_api.get_manager_dashboard:365`, rebuilt in Wave 1 on `permitted_employee_filters()`, Active only, capped at 50 with `team_total`, `team_capped`, `team_cap`, `is_hr_scope` | **Extend.** W1D-20's scope rule is reused unchanged; §6a splits the answer into **two lists** — `direct` (`reports_to = me`) and `covered` (the HR scope **minus** `direct`) — each Active only, each capped at `TEAM_LIST_CAP = 50`, each with its own total. `is_hr_scope` stays, and now decides whether the second section exists at all. AC-73, AC-74 | M |
| The `manager` key | `:530` returns `emp` — the **whole Employee row** | **Extend** — the six-key `me` block. **Live leak.** AC-6 | S |
| `l2_reports` / `l2_size` | Returned; **nothing in this repository reads them** (`hr_api.py:441-460` says so) | **Drop** — delete the keys with the screen that never used them. AC-16 | S |
| "In now / still to come" | `today_att` (`:482`) is Attendance only and never counts today (B18) | **Drop and reuse** `home_api._presence_counts` + `_scope_filters` + `_suppress` (Wave 2, rewritten in slice 044's follow-ups as two aggregates with the scope in the query). AC-14 | S |
| "Who is on leave today" | `:496-504` — **raw SQL**, `employee IN (...)` with one `%s` per person, and it selects **`leave_type`**; `:508-516` also carries **`description`**, the employee's own reason | **Extend.** **D-1 is closed** (§6a): presence only — the list says who is away, never why. **Both `leave_type` and `description` leave this read entirely**; they survive **only** on an approval row in "Your team". The `IN (...)` goes too (AC-14). AC-76 | S |
| "On leave this month" | `:517-525` — `from_date >= mo_start` **misses leave begun last month and includes next month's** (B18/TM-05), and also selects `leave_type` | **Extend** — a real overlap test (AC-21), and **`leave_type` and `description` are both dropped** from this read under D-1's closed answer (AC-76) | S |
| "Waiting on you" | Wave 2's approvals service behind `inbox_api` | **Reuse.** One definition, filtered to this team. AC-13 | S |
| "Needs attention" | No rule. The prototype's 75 % is invented (appendix D TM-03) | **Extend** — use the **stored `trajectory`**, not a percentage. §21 D-2 and D-3 | S |
| "Late this week" | `get_team_late_list:2898` — days only, no amount (Wave 3 AC-16 pins it) | **Reuse unchanged.** AC-33 pins it again because Wave 4 renders it | — |
| "New this month" | Nothing | **Build** — one `date_of_joining` filter inside the same scope subquery. AC-22 | S |
| Team cards with a cycle figure | `get_team_scorecard:1098` (10 queries, flat, measured by slice 044); `get_team_goals:2541` loops per person (22 queries for 19 people, appendix D §D) | **Extend** — one batched read per cycle. **Measure it; do not assume a number** | M |
| Tap a person → a sheet | `get_employee_scorecard:915` **or** `get_employee_detail_for_manager:1218` — two endpoints for one thing, and appendix D TM-08 records one of them returning `personal_email`, `cell_number` and `gender` to a manager | **Extend** — **one** person sheet endpoint with a fixed key list, opened from **both** Team sections (§6a: opening the employee record is HR's job as much as a manager's). §21 D-7 decides what contact detail it carries. AC-20, AC-79 | M |
| Direct reports versus everyone below | **Closed by W1D-20.** HR gets HR scope; a plain manager gets direct reports | **No work on the scope.** Q26 stays answered. What revision 2 adds is not a new scope but a **split of the same one**, so the actions can differ by reason (§6a) | — |

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
one field on Employee. **Nothing in Wave 4 creates a new record type any more** — peer
feedback, which was the only candidate, left the wave on 24 September (§23, ALV-116). The
one new *stored* thing is not a record but a value: an approval decided under HR authority
records that it was (AC-82), and §9 says which existing field carries it.

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

1. Team shows the stats line, then **Waiting on you**, then **Your team (19)**. Sandeep is
   a floor manager and not HR, so **there is no second section and no empty heading**
   (§6a, AC-73).
2. **Decision point — approve or decline?** He acts on the card. The row leaves the list
   and the Inbox count moves, because it is the same service (AC-13). The approval row for
   one of his own reports carries the **leave type and the reason**, because he is deciding
   that request and needs them. It is the only place on the screen where either appears
   (AC-76).
3. He taps a person. The sheet shows what he may see about them — never their leave
   reason, never their pay.

**Unhappy paths:** somebody else decided the same request a second earlier (one succeeds,
the other gets "This one has already been decided."); a report has left (not on the list —
`status = Active`); he has no reports at all (there is no Team entry in his menu — Wave 1
`frame_api` decides it).

### 5b2. Priya, store HR with no reports, opens Team

1. She sees **one** section: **You cover (38)**. There is no "Your team" heading, because
   she has no direct reports (§6a, AC-73).
2. Every row offers what HR does: open the employee record, invite or block their phone,
   cancel an attendance deduction. **No approve or decline on leave, no goal actions, no
   scorecard** — those belong to the person's own manager (AC-77).
3. **No leave type and no reason anywhere**, on any row, including the person who is off
   today. She sees that they are away, not why — in either form (AC-76).
4. **Decision point — the manager has not acted.** After the request has sat with the
   manager for two working days, an attendance correction becomes actionable for her, and
   the button says **"Approve as HR"** (AC-81, AC-82). **042 D-2 is still open**, so until
   Surbhi answers it the action is not offered at all — fail closed.

**Kamal is both.** He holds HR and has 4 direct reports, so he sees **both** sections. A
person who is a direct report **and** in his HR scope appears **once, in "Your team"**,
with the manager actions **plus** any HR-only action (AC-75).

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
| Team: a colleague's **leave type or their own written reason** on a list, chip or card | **— never** | **— never** | **— never** | **— never** | — |
| Team: the leave type **and the reason** on an **approval row** for a request they are deciding | — (not in his menu) | ✓ **own direct reports only** | **— never** | ✓ **own direct reports only** | — |
| Team: "Your team" section | — | ✓ | — (no reports) | ✓ | — |
| Team: "You cover" section | — | — (not HR) | ✓ HR scope minus her own reports | ✓ | — |
| Team: approve or decline leave, set goals, approve evidence, see a scorecard | — | ✓ **own direct reports only** | **— never** | ✓ **own direct reports only** | — |
| Team: invite or block a phone, cancel an attendance deduction | — | **— never as a manager** | ✓ covered people | ✓ covered people | — |
| Team: decide as HR over a manager who has not acted | — | **— never** | ✓ **after 042 D-2's two working days**, labelled and recorded as HR | ✓ same | — |
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
| A colleague's leave **type (`leave_type`) or their own written reason (`description`)**, anywhere except an approval row for one's own direct report | `01b` §14 rule 9; Wave 3 §5. **D-1 is closed this way, and it covers both fields** — §6a, AC-76, 045 PRIV-2 |
| An HR decision dressed as a manager's approval | §6a. Same outcome, different act — AC-82 |
| A manager action on somebody who is only covered, or an HR-only action on a report who is not covered | §6a's matrix — AC-77, AC-80 |
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

## 6a. The Team screen: two sections, and the actions that follow

**Decision taken by Surbhi on 24 September 2026, approved in full.** This is the Team
screen's design. **It closes D-1.**

### The shape: two sections, not one list with a label

```
Your team (4)
   Anita Sharma      Rahul Verma      ...
You cover (38)
   Deepak Rana       Farida Khan      ...
```

**Three reasons, recorded so nobody "simplifies" it back into one list:**

1. **A screen is scanned by shape before it is read.** Two headings say "these are two
   different relationships" before anybody reads a single name. A chip on a row in one
   long list has to be read, one row at a time, 42 times.
2. **Mixed buttons in one list is how somebody presses the wrong one.** Inside a section
   every row offers the same actions, so the hand learns the screen.
3. **It degrades well.** A manager who is not HR sees one section. An HR person with no
   reports sees one section. **Nobody ever sees an empty heading** (AC-73).

### The action matrix

**Every row here is a check, not a line in a table nobody tests.** The check number is in
the last column; each one has an observable oracle in §11.

| Action | Direct report ("Your team") | Covered ("You cover" — HR scope, not their report) | Check |
|---|---|---|---|
| Approve or decline leave | **yes** | **no** | AC-77 |
| See the leave type **and the employee's own reason** on that request | **yes — needed to decide** | **never, neither field** | **AC-76** |
| Approve an attendance correction | **yes** | **only after it has sat with the manager** — the two-working-day rule, **042 D-2** | AC-81 |
| Approve goal evidence / KPI progress | **yes** | **no** | AC-77 |
| Set or change goals | **yes** | **no** | AC-77 |
| See scorecard and trajectory | **yes** | **no** | AC-77 |
| See present / away / off today | **yes** | **yes — status only, never the reason** | AC-78 |
| Open the employee record (contact, department, joining date, manager) | **yes** | **yes — this is HR's job** | AC-79 |
| Invite or block their phone | **no** | **yes** | AC-80 |
| Cancel an attendance deduction | **no** | **yes — and it is the only remedy that exists** (**ALV-115**) | AC-80 |
| Act as HR, overriding a manager | **no** | **yes — as a differently labelled, separately recorded action** | **AC-82** |

**Confirmed facts behind four of those rows:**

- **Inviting or blocking a phone is already HR-only on the server.**
  `field_app_desk.hr_who_may_act:74` is the one check behind E7, E10, E11 and E12, and it
  scopes HR to their own companies. Wave 4 **adds no permission** — it puts an entry point
  where HR already is, and the server still decides.
- **Cancelling the deduction really is the only remedy.**
  `late_rules.py:208-215` skips any Attendance Deduction that is already submitted, in the
  weekly run and in HR's catch-up `run_for_range:251`, so correcting the day afterwards
  changes nothing. `attendance_deduction.on_cancel:171` is what puts the Leave Ledger Entry
  and the Additional Salary back. **It only helps while the Salary Slip is unsubmitted** —
  Wave 3 revision 2, **ALV-115**.
- **A decision already records who and when.** `attendance_correction.decide:804` stamps
  `alvoraa_reviewed_by` and `alvoraa_reviewed_on`, custom fields installed at
  `install_review_fields:135`. **What it does not record is the capacity** — see below.
- **The attendance-correction row for a covered person depends on a decision that is still
  open.** 042 D-2 — who may decide an attendance correction, and from when — was **not
  built** in Wave 2 (042 `03-implementation-notes.md` §1 item 2, and its §7 row "D-2 not
  built") and is still waiting. **Until it is answered the action is not offered on a
  covered row at all.** Fail closed. §21 D-12.

### Somebody who is both

**A person who reports to this HR user *and* is in their HR scope appears once, in
"Your team"** — with the manager actions **plus** any HR-only action from the right-hand
column. Not twice. Not in "You cover".

**Said as a rule an engineer can build:** `covered` is the HR scope **minus** `direct`.
`direct` wins. The two lists share nobody, and the two counts add up to the number of
distinct people the caller can act on. AC-75.

### The counts

**Per section, never on the total.** This is §7's standing rule, applied twice.

| Heading | When it is capped |
|---|---|
| `Your team (4)` | `Your team — showing the first 50 of 63` |
| `You cover (38)` | `You cover — showing the first 50 of 412` |

Each count equals the length of the list drawn beneath **that** heading. **There is no
combined "Team · 412" number anywhere on the screen**, because it would equal no list.
AC-74.

**What this changes on the server, stated plainly:** today `get_manager_dashboard` returns
**one** list capped at `TEAM_LIST_CAP = 50`, with `team_total`, `team_capped`, `team_cap`
and `is_hr_scope` (`hr_api.py:17`, Wave 1). Wave 4 returns **two** — `direct` and
`covered` — each with its own `total`, `capped` and `cap`. The scope rule W1D-20 decided is
not touched; it is asked twice, both times **as a subquery** (AC-14), never as an
`IN (...)` of names.

### The two rules that carry the most weight

**1 · The leave type *and the reason*, and why this closes D-1.**

**Two fields, not one.** `leave_type` is the category — "Sick Leave". **`description` is
what the employee typed** — "father in hospital". **The reason is the more personal of the
two**, so a rule written about the type alone would leak the worse half and look like it had
been followed.

**Both appear on the approval row for a person's own direct reports, and nowhere else.** Not
on a card, not on a chip, not in "on leave today", not in "on leave this month", not on a
covered row at any time, and not in the payload that draws any of them.

**Confirmed fact:** `on_leave_today` (`hr_api.py:496-504`) and `month_leaves` (`:517-525`)
both select `leave_type` today, and `hr_api.py:508-516` carries `description`. **W1D-20 widened who receives it** from a manager's own
direct reports to an HR person's whole scope — up to 50 people — and `01b` §14 rule 9 says
no screen shows a colleague the reason for an absence. That widening was never asked for;
it arrived with a scope change. This decision takes it back.

**It is narrower than today, so it needs a release note.** HR and managers have been
seeing leave types on this screen. Stopping is a narrowing, and they should be told rather
than surprised — **release gate 3**.

**2 · An HR override must not look like a manager approval.**

Same outcome, different act.

| | A manager's approval | An HR override |
|---|---|---|
| The button says | "Approve" | **"Approve as HR"** |
| The row afterwards says | "Approved by Sandeep Gupta" | **"Approved by Priya Nair (HR)"** |
| The stored record says | decided by that user, **as the manager** | decided by that user, **as HR** |

**The record must be able to tell the two apart on its own.** When somebody asks a year
later *who approved this, and why HR and not the manager*, the answer has to be in the
record and not in whoever remembers. **AC-82 fails if the stored record cannot tell the two
apart.**

**Recommendation for the carrier, and the alternative I rejected.** `Attendance Request`
already carries `alvoraa_reviewed_by` and `alvoraa_reviewed_on` as custom fields, in the
app's own idiom (`attendance_correction.install_review_fields:135`). Add **one** Select
custom field beside them — `alvoraa_decided_as`, options `Manager` / `HR`, default
`Manager`, read-only — and stamp it in `decide()`. **The alternative was to work the
capacity out at read time**, by asking whether the decider was the employee's `reports_to`
user. **I rejected it:** `reports_to` changes, so the same record would answer differently
next year, and §18 says this must be reconstructable a year later. One field, no backfill
(§15).

**No new notification.** The manager is not emailed when HR decides over them in Wave 4.
Their own row shows "Approved by Priya Nair (HR)" the next time they look, and the record
carries it. `[ASSUMPTION]` that is enough. If a manager should be told actively, it is one
row in §16 and it needs Surbhi's word, not mine.

---

## 7. Numbers must equal the lists they link to

Surbhi's standing rule. Team is the screen with the most totals in the product.

| Number on screen | The list it must equal | How |
|---|---|---|
| "Your team (4)" or "Your team — showing the first 50 of 63" | the cards under **that** heading | the `direct` list's own `total`, `capped` and `cap` (§6a) |
| "You cover (38)" or "You cover — showing the first 50 of 412" | the cards under **that** heading | the `covered` list's own `total`, `capped` and `cap`. **Per section, never a combined total** — a combined number would equal no list (AC-74) |
| "In now · 14" and "Still to come · 3" | the cards showing each chip | **one** call to `home_api._presence_counts` over the same scope condition, and the same `_suppress`. **Status only, never a reason**, in both sections (AC-78) |
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

**Revision 2 adds one rule to this one:** on Team the totals are **per section**. Two
sections mean two counts, two caps and two "showing the first 50 of n" sentences. **A
combined Team total is forbidden**, because there is no single list it could equal
(§6a, AC-74).

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
| **US-11** | As **Priya**, I must never learn which leave type anybody in my HR scope used **or read the reason they typed**, and as **Sandeep** I see either only on a request I am deciding about my own report. | Team | 3 | AC-33, AC-76 |
| **US-12** | As **Rahul**, the Team screen's call must not hand my date of birth, gender and phone number to somebody's browser. | Team | 3 | AC-6 |
| **US-13** | As **Rahul**, I want every state on all three screens named, so that an empty Growth screen never reads as "you have no goals". | all three | 5 | AC-42 to AC-51 |
| **US-14** | As **Kamal**, I want every number on Team to equal the list under it, so that I never have to ask which one is right. | Team | 3 | AC-12 |
| **US-15** | As the next engineer, I want the three dead browser tests either running or gone with a reason, so that nobody counts them as coverage again. | — | 5 | AC-62, AC-63, AC-64 |
| **US-16** | As the next engineer, I want the dead `l2_reports` keys and the unused upward-feedback endpoint deleted, so that a payload nobody reads cannot grow a reader later. | — | 2 | AC-16, AC-35 |
| **US-17** | As **Sandeep**, I want to approve or decline from the Team card and see the Inbox number move, so that the two screens are never out of step. | Team | 3 | AC-13 |
| **US-18** | As **Kamal**, who is both a manager and HR, I want my team and the people I cover in two separate sections, so that I can see at a glance which relationship I am in before I press anything. | Team | 3 | AC-73, AC-74, AC-75 |
| **US-19** | As **Priya**, I want each section to offer only the actions that belong to it, so that I never approve a leave request that was somebody else's to decide. | Team | 5 | AC-76 to AC-81 |
| **US-20** | As **the person asked a year later who approved this**, I want an HR override to be stored as an HR decision and not as the manager's approval, so that the record answers the question on its own. | Team | 3 | AC-82 |

**INVEST check on the three biggest.** US-1, US-5 and US-15 are all 8 or close to it.
US-1 and US-5 are split in the Points column into three deliverable pieces each. US-15
stays whole at 5 because its three parts share one fixture decision, and splitting them
would let two of the three be dropped quietly.

**The story deliberately not here:** peer feedback. It is **out of Wave 4 entirely**
(Surbhi, 24 Sep 2026) and becomes an HR-run process with its own market analysis and its
own specification — **ALV-116**, §23. Its old 4-day estimate does not travel with it.

**INVEST on the three new ones.** US-18 and US-20 are small and independently testable.
US-19 is a 5 because it is eleven rows of a matrix, but it does not split: half an action
matrix is worse than none, since the half that is missing is the half somebody presses.

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
| The Team screen says what it is showing | Two headings, two counts — "Your team (4)" and "You cover — showing the first 50 of 408" | Kamal | 2 | AC-15 |
| The negatives, asserted | Leave reason, internal note, unreleased rating, feedback author | Rahul | 5 | AC-32 to AC-35 |
| No leave type and no leave reason on the Team screen | Both fields, out of the payload at the read, searched recursively | Sandeep | 3 | AC-33, AC-76 |
| The Team call stops leaking the Employee row | Six-key `me` block on `get_manager_dashboard` | Rahul | 3 | AC-6 |
| Every state named on all three screens | Loading, empty, no data, error, no permission | Rahul | 5 | AC-42 to AC-51 |
| Every total equals its list | Enumerated from one place | Kamal | 3 | AC-12 |
| The three dead browser tests | Fixtures built, or deleted with a reason | engineer | 5 | AC-62 to AC-64 |
| Delete `l2_reports` and the minimum-less feedback endpoint | Payload keys nobody reads | engineer | 2 | AC-16, AC-35 |
| Approve from the Team card | The same service as the Inbox; the count moves | Sandeep | 3 | AC-13 |
| Team: two sections, "Your team" and "You cover" | Per-section counts and caps; no empty heading; somebody who is both appears once, in Your team | Kamal | 3 | AC-73 to AC-75 |
| Team: the actions follow the section | The eleven-row matrix in §6a, each row a check | Priya | 5 | AC-76 to AC-81 |
| An HR override is recorded as an HR decision | "Approve as HR"; `alvoraa_decided_as` on the record | Priya | 3 | AC-82 |

**Do not create these in YouTrack.** That is the user's call.

---

## 9. Data model

**No new DocType.** **One new custom field**, and only when 042 D-2 is answered: the
`alvoraa_decided_as` Select on `Attendance Request` that keeps an HR override distinct
from a manager's approval (§6a, AC-82). A second, `alvoraa_share_contact` on Employee,
appears only if §21 D-7 is answered "yes". **Neither needs a patch or a data backfill**
(§15).

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
| Team row | Employee · `name`, `employee_name`, `designation`, `department`, `user_id`, `image` | **already the fixed list** at `hr_api.py:371`. The same keys in **both** sections — what differs between them is the actions offered, never the fields carried (§6a) |
| Which section a row is in | not stored — **derived**: `direct` is `reports_to = me`, `covered` is the HR scope minus `direct` | It is a fact about the caller and the moment, not about the person. Storing it would be a second copy of `reports_to` that could go stale |
| **Whether an approval was made as the manager or as HR** | **one new Select custom field** on `Attendance Request` · `alvoraa_decided_as`, options `Manager` / `HR`, default `Manager`, read-only, beside the existing `alvoraa_reviewed_by` and `alvoraa_reviewed_on` | **No existing field can carry it.** `alvoraa_reviewed_by` says *who*, not *in what capacity*, and working the capacity out later from `reports_to` gives a different answer once the reporting line changes. §6a, AC-82. Needed only when 042 D-2 is answered |
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
| Sandeep | AC-42 | no reports at all → **Team is not in his menu**, Wave 1 decides it, and there is no empty Team screen to design (AC-49). He is not HR, so **"You cover" is not drawn at all** (AC-73) | nothing waiting → "All clear." and the cards still show (AC-45) | one list fails → that list says so; the stats and the cards still work (AC-46) | opening a person outside his line → the refusal sentence (AC-47) | AC-48 |
| Priya (HR, no reports) | AC-42 | **her HR scope is empty** → "Nobody is in your scope yet. Ask whoever set up your access." — **never a blank screen** (AC-49, and this is W1D-20's must-not-break case). She has no direct reports, so **"Your team" is not drawn at all** — never an empty heading (AC-73) | AC-45 | AC-46 | AC-47 | AC-48 |
| Kamal | AC-42 | AC-49. He is both, so **both** sections are drawn, and anyone who is in both appears once, under "Your team" (AC-75) | AC-45 | AC-46 | AC-47 | AC-48 |
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
| The two Team headings | "Your team (4)" and "You cover (38)" — the count in the heading, per section (§6a) |
| A capped Team section | "Your team — showing the first 50 of 63" · "You cover — showing the first 50 of 412". **Per section, never combined** |
| The HR override button | "Approve as HR" — never plain "Approve" on a covered row |
| A row decided by HR | "Approved by Priya Nair (HR)" — the manager's own row says the same, so nobody has to ask why it moved |
| An HR caller's Team list (retired) | ~~"Your HR scope · showing the first 50 of 412"~~ — **replaced in revision 2** by the two headings above. `is_hr_scope` now decides whether the second section exists, not what a one-line label says |
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
  while the leak survived. **The assertion searches the serialised payload recursively**
  (045 SEC-3) — not the `manager` key, because the next leak will be under a different key
  — and **the replacement reuses `frame_api.ME_FIELDS` rather than re-typing the six names
  in a new module**. A static check also fails if any Wave 4 module passes a
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
  `employee IN ({placeholders})`-shaped statement in any Wave 4 module. **There are two
  live instances, not one** (045 SEC-5): `hr_api.py:496-504` (`on_leave_today`) **and
  `hr_api.py:1172-1181` (`get_team_scorecard`)**, and §1 says this wave extends both
  functions — so the static check is written against **the module**, not a line number, and
  runs over both. *For the record: neither is injectable today; what is replaced is the
  habit and the ×5 slope.*
- **AC-15** *(rewritten in revision 2 for §6a's two sections)* *Given* Kamal, who has 4
  direct reports and an HR scope of 412, *then* his Team screen shows **"Your team (4)"**
  and **"You cover — showing the first 50 of 408"**, and **no screen anywhere calls the
  people he covers his direct reports**. *Given* Sandeep, a plain manager with 19 reports,
  *then* the screen shows **"Your team (19)"** and **no second heading at all**. *Given*
  Priya, store HR with no reports, *then* the screen shows **"You cover (38)"** and **no
  first heading at all**. The payload's `is_hr_scope` decides whether `covered` exists;
  `direct` decides whether "Your team" exists.
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
  prototype's 75 % has no source in the product. **And the chip's wording comes from one
  constant, shared with the employee's own Goals screen** (045 PRIV-9a), asserted by a test
  that the manager's string and the employee's string come from the same place — a manager
  must not see a judgement about a person in words the person never sees.
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
  Inbox row — **and, after §6a, from a row in either Team section** — *then* **the same
  endpoint** answers all of them, and a test asserts there is exactly one whitelisted
  person-sheet function in Wave 4's modules. **And the twin is retired in the same slice**
  (045 SEC-15): `get_employee_detail_for_manager:1218` carries the same over-wide field
  list as `get_employee_scorecard:915`, so a call-by-hand test proves the retired one is no
  longer callable. **Narrowing one door and leaving its twin open is not narrowing.**
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
  they were readable through the list API and an empty fixture would pass. **Plus a
  query-level assertion** (045 PRIV-5): **Confirmed fact**, `hr_api.py:1174-1181` selects
  `overall_rating` for the whole team and drops the unreleased ones in Python at `:1183`.
  The payload is right and the data is in the worker. **One `return rows` away is not a
  control** — the released condition belongs in the query, and the test asserts the
  unreleased rating was never read.
- **AC-33** *(D-1 is closed — revision 2)* *Given* a team where somebody is on **Sick
  Leave** today, *when* Sandeep and Priya open Team, *then* the string "Sick Leave" — and
  every other Leave Type name on the fixture — **does not appear anywhere in the serialised
  Team payload**, with the single exception AC-76 allows. **And the same is asserted for
  `description`, the employee's own free-text reason** (045 PRIV-2), which travels in the
  same payload at `hr_api.py:508-516` — **the reason is the more personal of the two**, and a
  decision applied to the type and not to the reason would leak the worse half.
  **The assertion searches the serialised payload recursively for each fixture string, not
  two named keys** — a two-key check passes the moment a third key carries the same value.
  It runs on the payload, never on the screen. **Confirmed fact:** `hr_api.py:498` and `:520`
  select `leave_type` today, so this test goes red before the change.
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
  this; the test is re-run because the screen moves. **The fixture's `features` list must
  genuinely lack `staff_list`**, and **no Wave 4 test may patch `has_feature`,
  `requires_feature` or `enabled_features` to `True`** — a static check enforces it, plus a
  decorator-order check (045 SEC-2). **A patched gate makes every entitlement test pass
  while proving nothing.**

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

### US-18, US-19, US-20 · the Team screen's two sections (§6a)

**All ten are driven from one fixture** with four people who are direct reports only, 38
who are covered only, and **one person who is both** — because the both case is the one an
engineer would otherwise guess at.

- **AC-73 · two sections, and never an empty heading.** *Given* **Kamal** (4 reports, HR
  scope of 412), *then* the screen draws **both** headings. *Given* **Sandeep** (19
  reports, not HR), *then* it draws **"Your team" only** — and the string "You cover" is
  **absent from the rendered HTML**, not merely hidden by CSS. *Given* **Priya** (HR, no
  reports), *then* it draws **"You cover" only**, and "Your team" is absent from the HTML.
  *Given* a caller with neither, *then* Team is not in the menu at all (AC-49, Wave 1's
  frame rule). The oracle is the rendered markup per persona, asserted four times.
- **AC-74 · each count equals its own list, and says so when capped.** *Given* a caller
  whose `direct` is 63 and whose `covered` is 412, *then* the first heading reads
  **"Your team — showing the first 50 of 63"** with exactly 50 rows under it, the second
  reads **"You cover — showing the first 50 of 412"** with exactly 50 rows under it, and
  **no number anywhere on the screen equals 475 or 412 + 63**. A test asserts, for each
  section independently, that the number in the heading equals the length of the array the
  rows were drawn from. Proved at **51** as well as at 981, because a cap that only
  misbehaves above a thousand is the defect slice 044 found.
- **AC-75 · somebody who is both appears once, under "Your team".** *Given* Kamal and an
  employee who both reports to him **and** sits in his HR scope, *then* that employee's
  row appears **exactly once** in the whole payload, in `direct`; `covered` does not
  contain them; and the row offers **the manager actions plus the HR-only actions**
  (invite or block their phone, cancel an attendance deduction). A test asserts the two
  lists share no employee id, and that `len(direct) + len(covered)` equals the number of
  distinct people the caller can act on.
- **AC-76 · the leave type *and the reason*, on one row and nowhere else (this closes D-1).**
  **The rule covers two fields, not one.** `leave_type` is the category; **`description` is
  the employee's own free-text reason**, and it travels in the same payload at
  `hr_api.py:508-516`. **The reason is the more personal of the two** — "father in hospital"
  is worse to leak than "Sick Leave" — so a decision applied to the type and not to the
  reason would leak the worse half. 045 PRIV-2 names both; revision 2 as first written named
  only the type in its assertion, and this is the correction.
  *Given* a fixture where **a direct report** is on **Sick Leave** with the reason
  **"father in hospital"**, and **a covered person** is on **Casual Leave** with the reason
  **"sister's wedding"** — both fields populated on both people, because an empty fixture
  passes while the leak survives — *then*, **for each of the two fields independently**:
  (a) it appears **nowhere** in `on_leave_today`, `month_leaves`, any card, any chip, any
      presence value or any count, for any persona;
  (b) the **direct report's** value appears **exactly once** — on the approval row of the
      leave request Sandeep is the approver of, inside `direct`;
  (c) the **covered person's** value appears **nowhere at all**, for anybody, because nobody
      on this screen is deciding that request;
  (d) for **Priya**, whose 38 people are all covered, **neither field appears anywhere**;
  (e) both are **dropped at the SQL and at the `fields` list, never in the renderer** — a
      field filtered in JavaScript is still in the response and still in the browser cache.
  **The assertion searches the serialised payload recursively for the four fixture strings.
  It does not check two named keys.** A two-key check passes the moment somebody adds a
  third key carrying the same value — which is exactly how this leak reached two functions
  in the first place. **It goes red on today's code**, because `hr_api.py:498` and `:520`
  select `leave_type` now and `:508-516` carries `description`.
  **One case an engineer will meet, and the rule does not soften for it** (045 Q4a): an HR
  person who is the **named `leave_approver`** for somebody who is **not** their direct
  report now decides that request **without seeing either field**. The decided rule is
  `reports_to`-based; the approval duty is `leave_approver`-based; the two do not always
  coincide. **They see the dates, the balance and the person — "why" stays withheld, in both
  its forms.** §21 open question 15 asks for a count of how often that combination actually
  occurs on the client tenants, so HR does not meet it for the first time on a Monday.
- **AC-77 · manager actions are absent on a covered row.** *Given* Priya's covered rows,
  *then* the payload carries **no** approve/decline control for leave, **no** goal-evidence
  or KPI approval, **no** set-or-change-goal control and **no** scorecard or trajectory
  value. Absent from the payload, not disabled on the screen — `01b` §14 rule 1 forbids a
  greyed control. And *when* the matching endpoints are called **by hand** as Priya for one
  of those people, *then* each refuses on the server with Wave 1's refusal sentence, logged
  without personal content. A screen that hides a button is not an access rule.
  **045 SEC-18 makes this a requirement and adds two things to it.** **(a) Every one of
  §6a's eleven rows gets its own by-hand server test** — eleven UI rows are eleven server
  checks, and a matrix is the shape where one row gets missed and the miss stays invisible
  until somebody presses it. **(b) The section a person is in is derived by the server on
  every action, never taken from the request:** a test that passing a `section`, `basis` or
  equivalent argument to any Wave 4 action endpoint **changes nothing**. `direct` means
  `reports_to = me` at that moment; `covered` means the HR scope minus that. **A test that
  only checks which keys are absent from a payload proves the screen, not the rule.**
- **AC-78 · presence yes, reason never.** *Given* both sections, *then* every row carries
  one of `present`, `away`, `off` and nothing else about the absence — no leave type, no
  note, no half-day reason, no `Attendance.status` free text. Asserted per row, in both
  sections, for every persona, and the small-group rule still applies (AC-34).
- **AC-79 · the employee record opens from both sections.** *Given* a row in `direct` and
  a row in `covered`, *then* tapping either opens **the same** person sheet, from the one
  endpoint AC-19 pins, carrying §9's fixed key list — contact block per §21 D-7, department,
  joining date, manager. Opening a covered person's record is **HR's job and is allowed**;
  the sheet is identical, and AC-20's forbidden keys stay forbidden in both.
- **AC-80 · the HR-only actions are on covered rows and on nobody else's.** *Given*
  Sandeep, a manager who is not HR, *then* **no** invite-a-phone, block-a-phone or
  cancel-a-deduction control appears on any of his 19 rows, **and** calling
  `field_app_desk.employee_app_section` by hand for one of them is refused on the server by
  `hr_who_may_act:74` — **Confirmed fact**, that guard exists and scopes HR to their own
  companies today, so Wave 4 adds no permission. *Given* Priya, *then* both controls appear
  on her covered rows. *Given* Kamal's both-person, *then* they appear there too (AC-75).
  **The cancel-a-deduction control says what it actually does:** it is the only remedy
  there is, and **it only helps while the Salary Slip is unsubmitted** — if the slip is
  submitted the screen says so in a sentence and offers nothing (Wave 3's lesson: do not
  write a remedy the product does not have). **ALV-115.**
- **AC-81 · an attendance correction on a covered row waits for the manager.** *Given* a
  correction raised today and still with the manager, *when* Priya opens Team, *then* the
  row is **visible and not actionable**, labelled "with Sandeep Gupta until 27 Sep".
  *Given* the same correction after **two working days counted on the requester's own
  holiday list**, *then* it becomes actionable for her and the button reads "Approve as
  HR" (AC-82). **This depends on 042 D-2, which is still open** (042
  `03-implementation-notes.md` §1 item 2). **Until Surbhi answers it, the fail-closed
  behaviour is the one that ships: the action is not offered on a covered row at all**, and
  the test asserts the absence. §21 D-12.
- **AC-82 · an HR override is stored as an HR decision, and the test fails if the record
  cannot tell.** *Given* Priya approves a covered person's attendance correction after the
  manager did not act, *then*:
  (a) the control she pressed read **"Approve as HR"**, and no control anywhere on a covered
      row reads plain "Approve";
  (b) the stored `Attendance Request` carries `alvoraa_reviewed_by = priya@…`,
      `alvoraa_reviewed_on` and **`alvoraa_decided_as = "HR"`**;
  (c) the same correction approved by **Sandeep, the manager**, carries
      `alvoraa_decided_as = "Manager"`;
  (d) **a test reads only the two stored documents — no screen, no session, no
      `reports_to` lookup — and distinguishes the two.** If it cannot, the check fails.
      This is the point of the criterion: when somebody asks a year later who approved this
      and why it was not the manager, the answer must be in the record;
  (e) the employee's own view and the manager's own row both say "Approved by Priya Nair
      (HR)", so nobody has to ask why it moved.
  **Confirmed fact:** `alvoraa_reviewed_by` and `alvoraa_reviewed_on` already exist
  (`attendance_correction.install_review_fields:135`) and `decide:804` stamps them.
  `alvoraa_decided_as` is the one field this adds (§9, §15).
  **045 SEC-19 adds three conditions, and they are the difference between an audit field and
  a field a client can lie about.** **(f)** the value is written **from the server's own
  derivation** of the caller's real relationship to the employee, never from an argument;
  **(g)** a test supplies `decided_as` in the request body and asserts **the stored value
  does not change**; **(h)** a test changes the employee's `reports_to` afterwards and
  asserts **the stored value still says what it said** — that is the whole point of storing
  it rather than working it out later.
  **Why this is stored and not worked out on the day somebody asks, in one sentence, because
  somebody will try to simplify it away:** the capacity of a decision can only be read off
  `reports_to`, and `reports_to` changes — so a derived answer would answer differently next
  year, and the year in question is exactly the year somebody raises a grievance about this
  approval. **A field that is cheap to remove is not cheap to lose.**

### From the `01c` — three checks revision 1 did not have

- **AC-83 (045 SEC-7) · the person sheet's gate is a scope, never an invented manager.**
  **Confirmed fact:** `alvoraa_goals/permissions.py:64-71` — `get_effective_manager` falls
  back to **the first active HR Manager** when `reports_to` is empty, and `hr_api.py:923`
  uses that result as a permission decision. **A helper written to answer "who do we
  notify" must not decide "who may read".** *Given* an employee whose `reports_to` is
  empty, *then* the person who merely happens to be the first active HR Manager is
  **refused** the person sheet unless their own scope allows them — and a static check
  fails if any Wave 4 module uses `get_effective_manager` in a permission branch.
- **AC-84 (045 SEC-6) · one filter builder, and it never returns "everything".**
  **Confirmed fact:** `permitted_employee_filters()` never returns `{}` (`access.py:259-261`),
  and **`hr_api.py:410` is a hand-rolled second copy of `home_api._filter_list`** — Wave 4
  is the commit that would give that copy more callers, so **it is replaced by a call to
  the real one before anything else is written**. *Given* a caller with no HR entitlement
  and no `reports_to`, *then* the generated condition list **matches nobody**; *given* a
  caller with **no employee id and `is_hr` true** — the exact fail-open shape found this
  week — *then* it still returns nothing. A static check fails if any Wave 4 module builds
  employee filters from `permitted_employee_filters()` inline.
- **AC-85 (045 SEC-16) · the three new panel scripts escape what they draw.** Wave 1's
  `034 SEC-10` check is **extended to Growth, Team and People**, not assumed to cover them.
  *Given* an employee whose designation is `<img src=x onerror=alert(1)>`, *then* all three
  screens render it as text, in both Team sections, and a scan finds no `innerHTML`
  receiving API data without `esc()`. Designation, department and company-value names are
  all tenant-editable text.

- **AC-86 (045 PRIV-8) · the employee's own screen is not narrower than their own record.**
  **Accepted by the security engineer as written**, with one addition of his that is in
  part (b) below.
  *Given* an employee whose own review is fully populated, *when* their own Growth screen is
  drawn, *then* **every content field on the review and its extension that holds a value is
  reachable from that screen**, with exactly two sets of exceptions:
  (a) **PRIV-5's three** — `manager_internal_notes`, `potential_rating` and an unreleased
      `overall_rating`, which are legitimately withheld;
  (b) **a withhold list that lives in one constant, with a reason against each entry that
      says *why* the field is plumbing** — links, naming, flags. **"internal" is not a
      reason** (the security engineer's requirement, and he is right): a content field with a
      plausible-sounding one-word label is the only way this check can be defeated, so the
      reason has to be readable by somebody who did not write it.
  **The field list is read from the doctype's own meta, not hand-written**, and **a field
  nobody has classified counts as "must be reachable"**. That means **adding a field about an
  employee without deciding whether they may see it fails a test** instead of quietly
  disappearing from their view.
  **Why that is not a breach of the fail-closed rule** — his framing, and it is clearer than
  mine: **fail closed means fail towards the person the data is about.** On every other path
  in this product that person is a **third party**, so refusing is the safe direction. On a
  subject-access path they are the **data subject**, and refusing them their own record is a
  **second harm**, not a safeguard. Same rule, and the direction follows from who is asking.
  **What this check is not:** it is not a screenshot test and it does not care where on the
  screen a value appears — only that the value is in the payload the employee's own screen
  receives.
  `[ASSUMPTION]` the content/plumbing split can be made from `fieldtype` plus a short
  reviewed list. If it cannot, PRIV-8 needs the security engineer's oracle rather than mine.

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
| **New** | An HR caller gets the leave type **and the employee's own written reason** for up to 50 people in their scope — a widening that arrived with W1D-20 and that nobody asked for | **Live today** (`hr_api.py:498`, `:520`, and `description` at `:508-516`) | **Closed by decision, 24 Sep.** AC-76 covers **both** fields — the reason was the half a rule about "leave type" would have missed — and a release note because it is a narrowing |
| **New** | Nothing in the record says whether an approval was made as the manager or as HR | Live today — `alvoraa_reviewed_by` says who, not in what capacity | **AC-82**, one Select field |

---

## 13. Out of scope for Wave 4, and where it goes instead

| Thing | Where it goes |
|---|---|
| **Peer feedback (give and ask)** | **Out of Wave 4 entirely** — Surbhi, 24 Sep 2026. Not deferred inside the wave; removed. It becomes a process HR runs on purpose, for a stated organisational purpose, with a beginning and an end, after **its own market analysis** and **its own specification**. **ALV-116** holds the reasoning and the route. §23. **Its old 4-day estimate does not travel with it** — that was costed for a different product |
| **Notifying a manager when HR decides over them** | **Not in Wave 4.** The record and the row carry it (§6a, AC-82); an active message is one row in §16 and needs Surbhi's word |
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
| Calls on Team | **1** (`get_team`) beyond the frame's two — **still one after §6a**, carrying both sections. Two sections must not become two calls. Today the page makes four (appendix D §D) |
| Calls on People | **1** (`get_staff_list`, which exists and costs **2 queries flat**) |
| Query counts | **Measured on `test044` (981 people) and `test044s` (20 people)** with slice 044's harness `measure_044.run` — three warm-up calls, then 20 measured — **before** any budget is written into this spec. The number is then recorded as a note |
| **The gate** | **The count is identical at 20 people and at 981**, for every persona. A change that moves a count by one and keeps flatness is fine; a change that keeps the count and breaks flatness is not |
| **The scope rule** | Every scope goes **into the query as a subquery**, never as an `IN (...)` of ids (`nfr-budget.md`, from a measured ×5 slope). AC-14 |
| p95 | ≤ **500 ms** on the W1D-09 rig, over 20 warm calls. Waves 1 and 2 pass everywhere at ≤ 215 ms, so this is generous and is not the thing to worry about |
| Payload size | `get_team` ≤ **40 KB**, `get_growth` ≤ **40 KB**, the person sheet ≤ **8 KB**, `get_staff_list` unchanged. **Asserted in bytes** in the same test as the query count, because a count stays honest while a payload grows. **Revision 2 note:** §6a's two sections mean `get_team` can now carry up to **100** rows (50 per section) rather than 50. Six keys per row, so the 40 KB budget still holds with room; **measure it rather than trusting this sentence** |
| Query count with two sections | The scope is asked **twice** — `direct` and `covered` — both as subqueries (AC-14). **Two constant queries, not one per person.** Flatness at 20 and at 981 is still the gate, and it is the thing a two-list rewrite is most likely to break |
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

**Almost nothing, and the two exceptions are both one field with no backfill.**

1. **`alvoraa_decided_as` on `Attendance Request`** — a Select (`Manager` / `HR`), default
   `Manager`, read-only, installed the same way the three review fields already are
   (`attendance_correction.install_review_fields:135`, wired to `after_migrate` **and**
   `after_install`). **No backfill.** Every request decided before this ships keeps an
   empty value, and the screen reads an empty value as **"not recorded"** — **not** as
   "Manager". Guessing backwards would put a claim in the record that nobody made. This
   field is only needed once 042 D-2 is answered (§6a, AC-82).
2. **`alvoraa_share_contact` on Employee** — only if §21 D-7 is answered "yes". A `Check`,
   default **0**, no backfill: everybody starts un-shared, which is the only safe default
   for a consent flag.

Both are custom fields in JSON and one `bench migrate`. **No data patch either way.**

**045 PRIV-10 and these two fields: settled, and not as an exception.** I first wrote this
up as a clash between PRIV-10 and SEC-19 that one of them had to lose. **The security
engineer's framing is better and it is the one that stands: there was no clash, because
neither field is in PRIV-10's scope.**

**PRIV-10 governs records about the subject** — no second copy of a performance record, no
derived store, so counsel's "employment + 6 months, then erased" applies unchanged. Measure
the two fields against that and neither is the kind of thing it is about:

| Field | What it is a fact about | In PRIV-10's scope? |
|---|---|---|
| `alvoraa_decided_as` | **the approver's capacity** — whether this person decided as the manager or as HR | **No.** It is not a record about the subject at all |
| `alvoraa_share_contact` (D-7, if it happens) | **a preference the person set themselves** | **No.** A choice, not a performance record |

**Why the framing matters more than the outcome, and this is his reason, kept because it is
worth keeping:** "two exceptions" in a list becomes three, and **the third will be a real
performance field with a good story**. A scope boundary does not rot that way. So PRIV-10 is
not amended and gains no exceptions; it simply does not reach these two, and the test still
asserts the slice adds no DocType, no store and no field beyond them.

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

| **An HR override** — HR decides an attendance correction the manager did not act on | §6a | **nobody is emailed** | **None in Wave 4.** The decision shows on the manager's own row and on the employee's, as "Approved by Priya Nair (HR)", and `alvoraa_decided_as` carries it on the record (AC-82). `[ASSUMPTION]` that is enough — open question 14 can overturn it in one row | — |

**Every on-screen message is in §10's table.** No notification, email or push preview in
this wave carries a rating, a self-assessment sentence, a leave reason or a pay figure.
**And no notification carries a leave type**, which is the leak Wave 3 found by email
(ALV-113) and the one §6a closes on screen.

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
- **The two Team sections are two real headings**, marked up as headings so a screen reader
  announces "Your team, heading" and "You cover, heading" and can jump between them. The
  count is part of the heading text, not a separate badge a screen reader reads out of
  order. On a 390 px phone the second heading must be reachable without horizontal scroll,
  and a section with nobody in it is **absent**, not collapsed — there is nothing to
  announce (AC-73, AC-56).
- **"Approve as HR" says so in words**, not by a different colour or a small icon. It is the
  clearest case in the wave of a control whose meaning must not depend on sight (AC-82).
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
| **Whether an approval was made as the manager or as HR** | **`alvoraa_decided_as` on the request**, stamped at the moment of the decision, beside `alvoraa_reviewed_by` and `alvoraa_reviewed_on` — plus Frappe's Version rows. **Working it out afterwards from `reports_to` does not count**: reporting lines change, so the same record would answer differently next year. AC-82 |
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
| A colleague's **leave type** | **sensitive** — it can imply a medical or family circumstance | leave administration | employment / statutory | No — and from this wave it is **shown less**: only to the approver of that request, about their own direct report (§6a, AC-76) |
| A colleague's **written leave reason** (`description`) | **sensitive, and the most sensitive field on this screen** — the employee typed it themselves and it can name a third party's illness, a bereavement or a family matter nobody asked about. "Father in hospital" is worse to leak than "Sick Leave" | leave administration | employment | No — and it is **shown less**, under exactly the same rule as the type (§6a, AC-76, 045 PRIV-2) |
| **Whether an approval was made as the manager or as HR** | internal — a fact about a decision, not about a person's character | accountability for a decision that affects pay or attendance | employment | **Yes, one new value** — and the outcome is impossible without it: "who approved this, and why not the manager" cannot be answered a year later if the record does not say. It is the smallest thing that answers it: one of two words |
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
| Sandeep | a colleague's **leave type, and the reason they typed** | **Narrower than today, in both fields.** Each survives only on the approval row of a request he is deciding about his own direct report. Both leave every card, chip and list (AC-76) |
| An HR caller | the leave types **and written reasons** of up to 50 people in their HR scope | **Narrower than today — removed, both fields.** W1D-20 had widened `team_ids` from a manager's reports to an HR person's scope and the leave type and reason came with it. **That widening is taken back** (§6a, AC-76). It needs a release note, because HR has been seeing it |
| An HR caller | **that** somebody in their scope is away today, without the reason | **Today: yes**, and unchanged. Status only, both sections (AC-78) |
| An HR caller | invite or block a phone, and cancel an attendance deduction, from the Team screen | **Today: yes, on the desk.** `field_app_desk.hr_who_may_act:74` already allows it and already scopes it to their own companies. **New entry point, no new permission** (AC-80) |
| A manager | any of the four HR-only actions | **No, and still no** — they are absent from the payload and refused on the server (AC-80) |
| Anyone | **that a decision was taken by HR rather than by the manager** | **New** — and deliberately so. The employee, the manager and an auditor all see the same thing (AC-82) |
| Any caller | their own `date_of_birth`, `gender`, `cell_number`, `branch`, `reports_to` in the Team payload | **Today: yes.** AC-6 **removes it** |
| A manager | a report's `personal_email`, `cell_number`, `gender` through the person sheet | **Today: yes** through `get_employee_scorecard`. AC-20 **removes it** |
| Anyone | a colleague's phone number or email in the directory | **No**, unless §21 D-7 says yes with consent |
| Anyone | who wrote upward feedback | **No** |
| Anyone | a colleague's draft self-review | **No** |

**Four rows get narrower. Nothing gets wider except one thing we wanted wider** — that a
decision taken by HR says so (AC-82). **The widening this product inherited from W1D-20,
where an HR caller received the leave types of up to 50 people, is taken back rather than
absorbed** (§6a, AC-76). The two HR actions that appear on the Team screen are not new
access: `field_app_desk.hr_who_may_act:74` already allows and already scopes them.

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

**A third place, added in revision 2, and it moves the other way.** §6a's HR override is
a decision about a person — an attendance correction that affects pay — taken by somebody
other than the person's manager. **It is not automation; it is the opposite.** A named
human presses a differently labelled button and the record says who they were and in what
capacity (AC-82). The employee sees the same words the auditor will. **The failure mode
this guards against is not a machine deciding — it is a human decision with no name on
it.**

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

**One new stored value, and it changes no period.** `alvoraa_decided_as` (§6a, AC-82) is a
field on a document that already exists, with the same life as the document — it is deleted
when the Attendance Request is. It is **not** a record about a person; it is a fact about a
decision. If the request survives an erasure request because it is decision-bearing, this
value survives with it, for the same reason. **And it is not an exception to 045 PRIV-10 —
it is outside its scope**: PRIV-10 governs records **about the subject**, and this is a fact
about the **approver's capacity**. §15 sets that out, in the security engineer's framing
rather than my first one.

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
| ~~May a manager, or an HR person, see which leave type a colleague used on a team screen?~~ | — | **CLOSED, Surbhi, 24 Sep 2026.** Own direct reports, on the approval row, only. §6a and AC-76. What is left is **release gate 3**: HR has been seeing it, and a narrowing is told, not sprung |
| **Is a "differently labelled, separately recorded" HR override enough, or must the employee also be told actively when HR decides over their manager?** Wave 4 shows it on the row and stores it on the record; it sends nothing | **Surbhi** | Nothing in the build — §6a's default is no new message. It would be one row in §16 |
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
| Plan §4 Wave 4 | "on leave" | US-5, US-19 | AC-21, AC-76 | covered — **D-1 closed 24 Sep**: presence on the list; leave type **and written reason** only on a direct report's approval row |
| Plan §4 Wave 4 | "new joiners" | US-5 | AC-22 | covered |
| Plan §4 Wave 4 | "one person sheet" | US-7 | AC-19, AC-20 | covered |
| Plan §4 Wave 4 | "a permission-scoped directory and search" | US-8 | AC-26, AC-27, AC-50, AC-51 | **mostly built already** — Wave 1's `staff_api` and `search_people` |
| Plan §4 Wave 4 | "Feedback (give and ask) needs a new record type" | — | §23 | **not adopted — Surbhi's decision of 24 Sep 2026.** Out of Wave 4 entirely; it becomes an HR-run process with its own market analysis and its own spec. **ALV-116** |
| Plan §4 Wave 4 | "Wave 0a must be done" | — | §12 | **done** — slice 010 groups A–D are on `origin/dev` at `8718f27`, verified by reading |
| Appendix D | G-01 to G-12 | US-1 to US-4 | AC-27b to AC-31, AC-36, AC-37 | covered; **G-07 (peer feedback) is out of the wave** — ALV-116 |
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
| Design `01b` §14 rule 9 | no screen shows a colleague the reason for an absence | US-11, US-19 | AC-33, AC-76 | **covered — the conflict is resolved, and the rule's own word is honoured.** It says *reason*, so it covers `description` as much as `leave_type`. Both win everywhere except the approval row of one's own direct report, where the approver needs them to decide |
| Design `01b` §14 rule 10 | minimum group of five, and the next-smallest too | US-10 | AC-34 | covered |
| Design `01b` §14 rule 11 | a figure that cannot be trusted says "Needs review" | US-6 | AC-67 | covered |
| Design `01b` §14 rule 12 | every total carries the date its data runs to | US-6 | AC-24 | covered |
| Design `01b` §14 rule 14 | every screen measured at 390 px in Hindi | US-13 | AC-55, AC-56 | covered |
| Design `01b` N4 | rating buttons 32 px on a phone | US-13 | AC-56 | covered — named explicitly |
| Design `01b` §9 | focus trapping in the sheet is not done | — | **D-11** | **open — inherited from Wave 1** |
| 009 design decision 3 | who's off: presence only | US-11, US-19 | AC-33, AC-76, AC-78 | **covered** — the same rule, now applied to Team in both sections |
| 009 design decision 4 | peer feedback last, with its own go/no-go | — | §23 | **superseded 24 Sep 2026** — the go/no-go did not happen inside this wave; the feature left it. **ALV-116** |
| 009 design decision 1 | the manager decides an attendance fix; HR steps in after two working days | US-19 | AC-81, **042 D-2** | **partly covered** — the Team screen's covered-row rule is written; the routing decision is still Wave 2's and still open. §21 D-12 |
| **Surbhi, 24 Sep 2026 (decision 1)** | peer feedback is out of Wave 4; it becomes an HR-run process with a stated purpose | — | §23, §13 | covered — **ALV-116** |
| **Surbhi, 24 Sep 2026 (decision 2)** | the Team screen separates the two reasons a person is on it, and the actions follow | US-18, US-19, US-20 | AC-73 to AC-82 | covered — §6a |
| **Surbhi, 24 Sep 2026 (decision 2)** | "an HR override must not look like a manager approval" | US-20 | **AC-82** | covered — the check fails if the stored record cannot tell the two apart |
| **Surbhi, standing rule** | a count equals its list, and says so when capped — **per section** | US-18 | AC-74 | covered |
| **ALV-115** | cancelling the deduction is the only remedy that exists | US-19 | AC-80 | covered — and the screen says so, including the unsubmitted-slip limit |
| Q21 | reporting line or org chart | US-6 | AC-25, **D-9** | **closed in code** (`reports_to`); the data fix is open |
| Q22 | who approves evidence; progress only after approval | US-3 | AC-29 | **closed by slice 010** — Pending by default, progress on approval |
| Q23 | values: pick 2 or rate all 7; which master list | US-1 | **D-5** | **open** |
| Q24 | rate goals or KPIs; whole or half points | US-1 | **D-4** | **open** |
| Q25 | peer feedback | — | §23 | **out of the wave** — ALV-116 |
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
| Prototype | Growth, self-review, Team, People screens | US-1 to US-9 | as above | covered, with §22's twelve differences |
| **045 SEC-1** | every whitelisted function safe on its own | US-13 | AC-53 | covered |
| **045 SEC-2** | the `staff_list` gate is server-side and no test patches it | US-8 | AC-51 | covered — strengthened in revision 2 |
| **045 SEC-3** | the caller's own block is `ME_FIELDS`, searched recursively | US-12 | AC-6 | covered — strengthened |
| **045 SEC-4** | every payload is a fixed key list, defined once | US-7, US-13 | AC-20, §9 | covered |
| **045 SEC-5** | no SQL built by concatenation — **both** instances | US-5 | AC-14 | covered — the second instance added |
| **045 SEC-6** | one filter builder; `hr_api.py:410` replaced; never an empty filter | US-5 | **AC-84** | covered — new |
| **045 SEC-7** | the person sheet's gate is a scope, not `get_effective_manager` | US-7 | **AC-83** | covered — new |
| **045 SEC-8** | one refusal message for all four causes | US-13 | AC-47 | covered |
| **045 SEC-9** | every Growth read ownership-checked | US-2, US-10 | AC-30, AC-47 | covered |
| **045 SEC-10** | scope before `ignore_permissions`, order proved | US-13 | AC-54 | covered |
| **045 SEC-11** | each deletion in its own commit, proved gone | US-16 | AC-16, AC-35, gate 2 | covered |
| **045 SEC-12** | Active-only resolution, one helper | — | AC-58, AC-65 | covered |
| **045 SEC-13** | no module-level mutable state | — | AC-54 | covered |
| **045 SEC-14** | a caller with no Employee record is refused explicitly | US-13 | AC-47 | covered |
| **045 SEC-15** | one person sheet — **and the twin retired** | US-7 | AC-19 | covered — strengthened |
| **045 SEC-16** | everything drawn from data is escaped, on all three new panels | US-13 | **AC-85** | covered — new |
| **045 SEC-17** | establish whether `Employee Performance Feedback` is readable tenant-wide | — | — | **CLOSED as a question, OPEN as a dated blocker — `ALV-117`.** The census was run read-only on production by the coordinator: **not live today**, because there are no readers and no rows. **It goes live on the day the DTC staff load creates the logins** — the load creates the readers, the appraisal cycle that follows creates the rows, and the two are scheduled together. **Not Wave 4's to fix and not Wave 4's to wait for**; it is a go-live blocker with a date |
| **045 SEC-18** | the eleven-row action matrix is enforced on the server, section derived | US-19 | AC-77 | covered — strengthened |
| **045 SEC-19** | `alvoraa_decided_as` is server-derived and unspoofable | US-20 | AC-82 | covered — strengthened |
| **045 PRIV-1** | no pay on any Team or People surface | US-10 | AC-20, AC-33 | covered |
| **045 PRIV-2** | leave type **and `description`** leave the read; approval row only | US-11, US-19 | AC-33, AC-76 | covered — **`description` is now first-class in both checks**, with a fixture that populates it and a **recursive** payload search rather than two named keys |
| **045 PRIV-3** | no phone, email, employee number or gender about anybody but the caller | US-7 | AC-20 | covered |
| **045 PRIV-4** | search and staff list stay inside Wave 1's scope, POST | US-8 | AC-27, AC-50 | covered |
| **045 PRIV-5** | manager-only fields never reach the employee — **in the query** | US-10 | AC-32 | covered — query assertion added |
| **045 PRIV-6** | upward feedback: totals only, minimum three, no author | US-10, US-16 | AC-35 | covered |
| **045 PRIV-7** | nothing sensitive in a log, error, notification or preview | US-1, US-13 | AC-36, AC-48 | covered |
| **045 PRIV-8** | Growth is not narrower than the employee's own record | US-1 | **AC-86** | **covered — accepted as written**, plus his requirement that each withhold reason says *why* a field is plumbing. **Fail closed means fail towards the person the data is about**, which is why an unclassified field counts as "must be reachable" |
| **045 PRIV-9** | the trajectory chip: same words to both, no ranking, no history | US-6, US-10 | AC-23, AC-24, §19.4 | covered — the shared constant added |
| **045 PRIV-10** | no second copy, no derived store | — | §15, §19.5 | **covered, and not by an exception.** PRIV-10 governs records **about the subject**; `alvoraa_decided_as` is a fact about the **approver's capacity** and D-7's flag is a **preference**, so both sit outside its scope. **No amendment, no exception list** — two exceptions become three, and the third would be a real performance field with a good story |
| **045 PRIV-11** | no control claims a route that does not exist | US-1 | AC-41, AC-80 | covered |
| **045 PRIV-12** | minimum group of five, reused, next-smallest too | US-10 | AC-34 | covered |
| **045 PRIV-13** | nothing AI-shaped, and no redaction boundary to pretend about | — | §19.7 | covered |

**Gaps, listed rather than hidden:**

| Gap | Why it is a gap |
|---|---|
| **045 SEC-17 — no longer a gap here; it is `ALV-117`** | Answered: the doctype is **not readable tenant-wide today** because nobody holds the role and no rows exist, **and it becomes readable on the day of the DTC staff load**. It left this spec's gap list and became a dated go-live blocker instead, which is the right home for it |
| **045 PRIV-8** | "Growth is not narrower than the record" has no acceptance criterion yet. The security engineer offered to give the oracle; I would rather ask than invent one |
| **No `07` for this slice** | §14 has no measured numbers yet, by design. `OPS-W4-n` items are not written |
| **No design run for Growth, Team and People** | `01b` §11 says so explicitly. §22 records every place this spec goes beyond the prototype |
| D-2 to D-12 | §21 — **D-1 is closed**, and D-12 is new: the covered-row attendance correction waits on Wave 2's D-2 |
| The other four whole-Employee-row endpoints | Pinned by slice 043; **their own slice, with a go-live date against it** |
| A retention job for performance records | §19.6, `[UNVERIFIED]` |
| Focus trapping in the sheet | D-11, inherited from Wave 1 |

---

## 21. Needs a decision

**Eleven live, one closed, and five of them stop something.** **D-1 is closed** — Surbhi answered it on
24 September with §6a's design, and the two peer-feedback questions left the wave with the
feature. **D-12 is new** and inherits a decision Wave 2 is still waiting on. Everything
else has a fail-closed default written into an acceptance check, so the build starts
without it.

| # | Question | My recommendation | Blocks? |
|---|---|---|---|
| ~~**D-1**~~ | ~~May a colleague's leave type appear on the Team screen?~~ | **CLOSED — Surbhi, 24 September 2026.** Presence only on every list, card and chip. **The leave type — and the reason the employee typed — appear on the approval row for a person's own direct reports and nowhere else.** For an HR caller looking at somebody they merely cover, never. **The decision was taken about `leave_type`; it is applied to `description` as well**, because the reason is the more personal field and a rule that covered only the category would have looked followed while leaking the worse half (045 PRIV-2). Written up in **§6a**; checked by **AC-76**; and because it is **narrower than today**, it ships with a release note (gate 3) | **No longer blocks anything** |
| **D-12** *(new in revision 2)* | **May an HR person approve a covered person's attendance correction, and from when?** §6a says "only after it has sat with the manager for two working days" — but **that is Wave 2's D-2, and Wave 2 did not build it** (042 `03-implementation-notes.md` §1 item 2). It is a permission change, not a routing change (042 `01c` SEC-8) | **Answer 042 D-2 once, for both waves.** My recommendation is unchanged from Wave 2's: HR sees every correction from day one and may act from day three, counted on the **requester's own** holiday list, with the row labelled "with \<manager\> until \<date\>". **Until then the fail-closed behaviour ships: the action is not offered on a covered row at all**, and AC-81 asserts its absence | **Blocks one row of §6a's matrix**, not the screen and not the sections |
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
| d | A feedback-received card, with "give" and "ask" controls | **Not built, and not pending either.** The feature left Wave 4 on 24 Sep 2026 | Surbhi's decision 1. It returns as an HR-run process with its own analysis and spec — **ALV-116** |
| e | "Leadership / other floors" in the directory | **Not built** | No field, no agreed definition (§13) |
| f | Contact details on the person sheet "when they choose" | **Not built** — five keys, no phone, no email | There is no consent field. D-7 |
| g | Example approvals, goal evidence and team status shown with a **Sample** tag | Built on real rules | `01b` D8 already moved three of them to real rules; this spec names the data source for each |
| h | "Switch to the full desk" beside a manager on the person sheet | Not drawn for a plain manager | W1D-19 — the server returns `None`, and the prototype was wrong, not the code |
| i | The Team screen implies every row is a direct report, in **one list** | **Two sections** — "Your team (4)" and "You cover (38)" — with a different action set on each, per-section counts and per-section caps | W1D-20 and W1D-22, then **Surbhi's decision of 24 Sep 2026**. The prototype predates all three. §6a, AC-73 to AC-75 |
| l | Every Team row carries the same buttons | Eleven actions split by reason; an HR override reads **"Approve as HR"** and is stored as an HR decision | §6a. Mixed buttons in one list is how somebody presses the wrong one — AC-77, AC-80, AC-82 |
| j | The self-review shows all seven generic principles | Two chosen values with an example, per D-5 | B13. The seven are hard-coded in the current wizard, and nobody reads the answers |
| k | Rating buttons 32 px tall on a phone | ≥ 44 px | `01b` finding N4, measured |

---

## 23. Peer feedback — considered, and pulled out of Wave 4

**Peer feedback is not part of Wave 4, and it is not deferred inside it either. It was
removed** — Surbhi, 24 September 2026. Revision 1 costed an always-available "give and ask"
feature at about four days; **that estimate is struck and does not travel forward**, because
what is being built instead is a different product: *a process HR runs on purpose, for a
stated organisational purpose, with a beginning and an end, not an open feature sitting on
three screens.* Two things pulled it. **The obvious reuse is unsafe** — **Confirmed fact**,
read in `hrms/hrms/hr/doctype/employee_performance_feedback/employee_performance_feedback.json`:
the **`Employee` role holds `read`, `write`, `create`, `submit`, `cancel`, `export`, `print`
and `share` on the whole doctype**, with **no `permission_query_conditions` entry in
`hrms/hooks.py`**, so every employee could list and **export** every feedback record about
everyone until we wrote those rules ourselves. And **feedback is a trust feature that one
export ends permanently** — it is not a feature you ship and then tighten.

**The full reasoning and the route it must take live in `ALV-116`:** market analysis first,
then the organisational purpose, then the process HR runs, then the specification and the
permission model. **Nothing in Wave 4 depends on it**, so nothing above changes.

**One thing had to survive the feature leaving, and it did.** Peer feedback was the work
that would have forced somebody to look at that doctype's permissions; the exposure does not
go away because the feature did. It is now **`ALV-117`**, with a census run read-only on
production behind it: **not live today** — no readers, no rows — and **live on the day the
DTC staff load creates the logins**, because the load creates the readers and the appraisal
cycle that follows creates the rows, and the two are scheduled together. **A dated go-live
blocker**, owned outside this slice.

---

## 24. Ready check

| Box | State |
|---|---|
| Brief approved | ✓ — the 009 plan (Wave 4) and the decisions stand in for `01` |
| Clickable prototype reviewed | **Partly** — reviewed 22 Sep, but `01b` §11 says Growth, Team and People were **deliberately not redesigned**. §22 records twelve differences. **D-8** asks for a short design pass on the wizard |
| `01c` security and privacy written | **✓ landed** (`d1ef233`, revision 2) and **absorbed**: all eight of its required changes are in this revision, and §20 traces every `SEC` and `PRIV` item. **PRIV-8 now has an oracle** (AC-86) and **PRIV-10's conflict with SEC-19 is answered in §15** — both are my reading, written to be corrected rather than left hanging. **And SEC-17 is answered** — the census was run on production and it became `ALV-117`, a dated go-live blocker rather than an open question. **Nothing from the `01c` is left hanging** |
| `07` DevOps inputs written | **✗ — not written.** §14 carries no measured number on purpose |
| Every state designed and specified per persona | ✓ §10 |
| Gap analysis verified in source | ✓ §4, with file and line |
| Stories: personas, sized, "must not" stories | ✓ §8 — US-10, US-11, US-12 and US-14 are the "must not" stories |
| Every story has checks with observable oracles | ✓ §11 |
| Traceability complete | ✓ §20, with the gaps listed |
| Permission matrix with negatives | ✓ §6, and **§6a is the feature** — eleven actions split by the reason a person is on the screen, each one a check |
| Edge cases | ✓ AC-57 to AC-72 |
| NFR numbers | **Deliberately unset** — §14 names the sites, the harness and the gate. Setting them before measuring is the mistake four earlier budgets made |
| Migration stated | ✓ §15 — **one Select custom field** (`alvoraa_decided_as`, no backfill, and an empty value reads as "not recorded"), plus D-7's optional second |
| Compliance sub-analysis | ✓ §19 — including the two places this wave shapes a judgement about a person |
| No prohibited capability | ✓ nothing AI-shaped; the two prohibitions approached (a ranking, an attention history) are refused in writing in §19.4 |
| Open questions owned, none blocks day 1 | **Partly, and better than revision 1.** The server work (US-12, US-5's lists) starts today, and §6a's two sections can be built now. **D-4, D-5 and D-8 block the wizard's commit; D-10 blocks People's menu rule; D-12 blocks one row of §6a's matrix.** **D-1 no longer blocks anything — it is answered.** Every remaining one has a fail-closed default |
| Frappe details verified in source | **Partly** — AC-40 (`page_data` size) and the evidence notification in §16 are `[UNVERIFIED]` and need one bench run |
| The three dead browser tests are owned | ✓ US-15, and the ticket's wave attribution is corrected |
| Nothing in the wave creates a new record type | ✓ — true since 24 Sep. Peer feedback was the only one, and it left (§23, ALV-116) |

**Verdict, plainly: ready to start, not ready to finish.** The five server items are
specified, verified in source and independent of every open decision — and one of them
closes a live leak on a screen HR uses every day. The wizard needs three answers and a
short design pass. **This is revision 2: Surbhi's two decisions of 24 September are in it,
the `01c` has landed and its eight required changes are absorbed, and what is still absent
is the `07`** — so §14 still names the sites, the harness and the gate rather than a
measured number. **The two decisions made the wave clearer and slightly bigger:** the Team
screen is two lists rather than one, and peer feedback is gone.

**The order I would build in:** the six-key `me` block on the Team call (P1, one hunk),
then the month-leave filter and the `IN (...)` scope, then the two deletions in their own
commits, then **§6a's split into two sections with the leave type dropped** (AC-73 to
AC-78 — it is a payload change, so it goes before the screen work), then the Team and
People re-dresses, then the wizard once D-4, D-5 and D-8 are answered. **The HR-only
actions (AC-80) and the override record (AC-82) come last**, because AC-81's row waits on
D-12.

---

## Open questions

| # | Question | Owner | Blocks | Can the build start without it? |
|---|---|---|---|---|
| — | ~~D-1 — a colleague's leave type on the Team screen~~ | — | — | **CLOSED 24 Sep** — §6a, AC-76. What survives is release gate 3, the note about the narrowing |
| 2 | D-2 — the "needs attention" rule | Surbhi | The card | Yes — AC-23 is the default |
| 3 | D-4 — rate goals or KPIs, whole or half points | Surbhi | Step 1 of the wizard | **No** — the step cannot be built either way |
| 4 | D-5 — values: pick two, and which master list | Surbhi | Step 2 of the wizard | **No** |
| 5 | D-6 — where the skill options come from | Surbhi | One field | Yes — free text |
| 6 | D-7 — contact details on the person sheet, and consent | Surbhi, **with an advisor** | One field, and a DPDP question | Yes — the default is "no contact detail" |
| 7 | D-8 — a design pass on the self-review wizard | Surbhi, with the UX designer | The wizard's commit | Yes for Team and People |
| 8 | D-9 — the reporting-line data fix | Surbhi, with tenant HR | Nothing in code | Yes |
| 9 | D-10 — does a plain employee get the staff directory | Surbhi | People's menu rule | **No** — one line either way, and it is a visibility decision |
| 10 | D-11 — focus trapping in the shared sheet | The engineer, then Surbhi | A WCAG 2.2 AA claim | Yes |
| 11 | ~~§23 — peer feedback: go or no-go~~ | — | — | **CLOSED 24 Sep — out of Wave 4 entirely.** It restarts as an HR-run process: market analysis, purpose, process, then spec. **ALV-116** |
| 13 | **D-12 / 042 D-2 — may HR decide a covered person's attendance correction, and from when?** It is a permission change and Wave 2 never built it | Surbhi | **One row of §6a's matrix** (AC-81), in Wave 2 as well as here | Yes — the action is simply not offered until she answers |
| 14 | Should a manager be told actively when HR decides over them, or is the row and the record enough? | Surbhi | One possible row in §16 | Yes — the default sends nothing |
| 15 | **045 Q4a** — how often is an HR person the named `leave_approver` for somebody who is **not** their direct report? Under the decided rule they now approve without seeing the leave type | The engineer, on a dev copy; then Surbhi if it is common | Nothing — the rule stands either way (AC-76) | Yes. **But find out before HR meets it on a Monday** |
| — | ~~045 SEC-17 / Q2 — is `Employee Performance Feedback` readable tenant-wide today?~~ | — | — | **ANSWERED and re-homed as `ALV-117`.** Census run read-only on production: **no**, not today — no readers, no rows. **Yes on the day the DTC staff load creates the logins**, because the load creates the readers and the appraisal cycle behind it creates the rows, and the two are scheduled together. **A go-live blocker with a date, not a Wave 4 question** |
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
- `[ASSUMPTION]` **The row and the record are enough when HR decides over a manager** — no
  new message is sent (§6a). It is a judgement, not a measurement, and it is listed as an
  open question so it can be overturned cheaply.
- `[ASSUMPTION]` **`alvoraa_decided_as` is the right carrier** for the capacity of a
  decision, following the idiom `install_review_fields:135` already set. **Confirmed fact:**
  `alvoraa_reviewed_by` and `alvoraa_reviewed_on` exist and are stamped by `decide:804`;
  **what is assumed is only that a fourth field beside them is acceptable** rather than, say,
  a comment. `[UNVERIFIED — engineer to confirm]` that adding it does not disturb the
  existing Desk layout of that section.
- **Confirmed fact:** inviting or blocking a phone is already HR-only and already
  company-scoped — `field_app_desk.hr_who_may_act:74`, the single guard behind E7, E10, E11
  and E12. §6a adds an entry point, not a permission.
- **Confirmed fact:** cancelling an Attendance Deduction is the only remedy that exists.
  `late_rules.py:208-215` skips a submitted deduction in the weekly run and in
  `run_for_range:251`; `attendance_deduction.on_cancel:171` is what restores the ledger entry
  and the Additional Salary. ALV-115.

## Release gates (not acceptance checks)

1. **Wave 4's panels wait for Wave 1 to reach `dev`**, and OPS-31 must not reach
   **production** until ALV-112's asset refresh is on `main` and one deploy has proved it.
   The same condition Waves 2 and 3 carry.
2. **Each deletion ships in its own commit** — `l2_reports` (AC-16) and
   `get_upward_feedback` (AC-35) — so a rollback is one step.
3. **The leave-type change goes with a release note, and this is now a commitment rather
   than a proposal.** D-1 is answered: leave type survives only on the approval row for a
   person's own direct reports — **and so does the reason the employee typed** (§6a, AC-76).
   **HR and managers have been seeing both on every Team list**, so stopping is a
   **narrowing** and they are told before the push, not after. One short note: what they
   will stop seeing, why, and where the two fields still appear.
4. **Demo data seeded on the local copy before the test run** (§15), or most Growth tests
   pass for the wrong reason.
5. **The three browser tests run in CI, or are deleted with a reason**, before the wave is
   called done (AC-62 to AC-64). A skipped test counted as coverage is how this was missed
   for months.
6. **The `staff_list` switch is ticked on the tenants that should have People**, per W1D-21
   and D-10. A configuration action on Surbhi's word on the day.
7. **The two Team sections and the HR-override label ship together.** "Approve as HR" with
   no `alvoraa_decided_as` behind it is a label that lies, and a covered row with a plain
   "Approve" is the thing §6a exists to prevent. AC-80, AC-82 — one commit or none.

## Handoff note

**To the security and privacy engineer:** your `01c` landed while this revision was being
written, and **all eight of its required spec changes are in** — AC-6, AC-14, AC-19, AC-23,
AC-32, AC-33, AC-76, AC-77, AC-82, plus three new checks: **AC-83** (SEC-7, the person
sheet's gate is a scope and never `get_effective_manager`), **AC-84** (SEC-6, one filter
builder and `hr_api.py:410` replaced) and **AC-85** (SEC-16, the three new panels escape
what they draw). §20 now traces every `SEC` and `PRIV` item. **Two answers and one thing still yours.**
**PRIV-8 now has an oracle — AC-86 — and it is my reading, not yours.** You offered to
supply it; the coordinator's call was that I write mine down rather than leave it hanging
between two documents, so **please read AC-86 and overrule any line of it you want**. The
one choice in it worth your attention: **a field nobody has classified counts as "must be
reachable"**, so adding a field about an employee without deciding whether they may see it
**fails a test** rather than quietly disappearing from their own view. **PRIV-10 and your own
SEC-19 contradict each other**, and §15 answers it: PRIV-10's **intent** holds untouched —
no second copy, no derived store, no changed retention period — and its **letter** needs one
word, because the slice now adds `alvoraa_decided_as` as well as D-7's flag. It is a fact
about a decision, on a document that already exists, deleted with it. **If you disagree, one
of the two has to move, and I think it should be PRIV-10.** **SEC-17 is answered and re-homed**, so nothing from your
`01c` is left hanging here: the census was run read-only on production, the doctype is **not
readable tenant-wide today** because nobody holds the role and no rows exist, and it
**becomes readable on the day the DTC staff load creates the logins** — the load creates the
readers, the appraisal cycle behind it creates the rows, and the two are scheduled together.
It is **`ALV-117`**, a dated go-live blocker, which is a better home for it than an
acceptance criterion in a slice that does not touch it. **R3's 2026-10-05 check date in your
`01c` should now point at that ticket.** **And §19.3's
paragraph about the W1D-20 widening is unsoftened** — it now reads better, because the
widening is taken back rather than merely named.

**To the DevOps engineer:** this slice needs its own `07`, and **revision 2 changed the
shape of what you will measure.** The Team screen is now **two scoped lists in one call**
(§6a), so the thing to watch is that two sections stay **two constant subqueries** and do
not become one query per person or a second call. `get_team` can now carry up to 100 rows
rather than 50, so the 40 KB budget wants measuring rather than believing. **And there are
two raw-SQL instances, not one** — `hr_api.py:496-504` and `hr_api.py:1172-1181`, the second
inside `get_team_scorecard`, which the `01c` also flags for reading every appraisal-extension
row with no limit and filtering in Python. §14 names no query budget on
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

**And three more from revision 2.** **§6a is two lists, not one list with a flag** —
`covered` is the HR scope **minus** `direct`, `direct` wins for anybody in both, each list
has its own count and cap, and there is no combined total anywhere (AC-73 to AC-75). **Two
sections must stay one call and two subqueries** — not one query per person and not an
`IN (...)` (AC-14, §14). **Drop `leave_type` and `description` at the SQL and at the `fields` list, not in the
renderer** — a field filtered in JavaScript is still in the response and still in the
browser cache, and `description` is the one that carries "father in hospital". **Both
fields, not just the type.** **And an HR override is a different act, not a different
label:**
"Approve as HR" on the button **and** `alvoraa_decided_as = "HR"` on the record, stamped in
`decide()` beside the `alvoraa_reviewed_by` it already writes (AC-82). A label with no field
behind it is worse than neither.

**To the test engineer — five tests here are easy to write so that they prove nothing.**
**AC-6** must use a fixture where all six forbidden Employee fields are **populated**; an
empty fixture passes while the leak survives (Wave 3's exact mistake). **AC-33** must name
"Sick Leave" against the serialised payload, and it must go **red on today's code** first —
`hr_api.py:498` and `:520` select `leave_type`, so it will. **AC-21** must be driven from
leave that **began last month**; written the other way round it passes and proves the
opposite. **AC-30** must assert **both** directions in one test. **AC-12** must enumerate
the totals from one place, so that a total added later with no list fails it rather than
being missed.

**Revision 2 adds three more of the same shape.** **AC-76** must use a fixture with **two
leave types and two written reasons** — one pair for a direct report whose request the caller
is deciding, one pair for a covered person — and assert, **per field**, that the first
appears exactly once and the second not at all. Written with one leave type it passes while
most of the leak survives; **written without `description` it passes while the worse half
survives.** And **search the serialised payload recursively for the fixture strings, not two
named keys** — a two-key check passes the moment somebody adds a third key carrying the same
value, which is how this reached two functions already. **AC-75** must include a
person who is in **both** lists, or the de-duplication is never exercised. **AC-82** must
read **only the two stored documents** — no screen, no session, no `reports_to` lookup — and
still tell a manager's approval from an HR override; if the test needs anything outside the
record, the record does not carry the answer and the check must fail.

**To the product manager:** two things in the plan did not survive contact with the code,
and you should know before the estimate is reused. **Wave 4 is smaller than it looks** —
Team's scope, the staff list, search, the presence calculation and the approvals service
are all already built, so the wave is one new screen (the wizard), two re-dresses and five
defect fixes. **And peer feedback has left the wave**, by Surbhi's decision of 24 September — not
deferred inside it, removed. It returns as **a process HR runs on purpose**, with a stated
organisational purpose, a beginning and an end, after its own market analysis and its own
specification (**ALV-116**). **Do not carry revision 1's four-day estimate into any plan**:
it costed an always-available feature, which is not what is being built. With it goes the
last new record type in the redesign, so **Wave 4 now creates none**.
