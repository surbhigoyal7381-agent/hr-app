---
slice: 064-organogram-improvements
artifact: 00-impact-analysis (numbered 04 in this folder, because 01-03 are taken)
author: hrms-fullstack-engineer
date: 2026-10-21
status: for Surbhi's approval - NO CODE WRITTEN. Change process steps 1 and 2. Step 3 is yours.
inputs: 03-functional-spec.md v1.1 (27 stories, 102 ACs, 96 parity rows), 01d-security-privacy-requirements.md (SEC-1..11, PRIV-1..4), 01c-engineer-findings.md, 01-product-brief.md, 02-design.md (incl. 6.5c v4), prototype-v4.html, definition-of-ready-done.md (parity rule)
code read: worktree 060-manager-review at 59906139 (holds slice 061 and the unpushed 5a211f3f). register.py, api.py, metrics.py, the two position doctypes, access.py, org_job_link.py, hrms/hooks.py, alvoraa_portal/hooks.py, portal.js 95-1260, positions.html, check_positions_tree.js, test_portal_security_010.py CEILINGS. Frappe source on the local bench (v16.33.1).
measured: on the local bench, site ppj.localhost (120 seats, 403 assignments, 403 active people, 1 company), read-only console, rolled back. Logic timings in node on synthetic data.
---

# 064 · Impact analysis and strategy: the Positions organogram

**I recommend. You decide.** Nothing below is built. No file outside this one was changed.

## 0 · Bad news first

1. **This is a big change to one screen, about 82 points.** My estimate is **8 to 10 working days** of
   build and test, in about 13 commits. Most of it is browser code: the chart on Positions gets its own
   drawing (a three-row "window"), because the shared chart drawing cannot do rows that wrap and one
   open family at a time without changing the Organisation page too.
2. **The records check that the "records disagree" chip needs is slow today, and I measured it.** On
   the local copy of a DTC-sized tenant (120 seats, 403 people) `reporting_mismatches` runs
   **1,458 database queries and takes 1.4 seconds** for one call. The budget is 500 ms. The rewrite
   (SEC-5) brings it to a fixed handful of queries. I measured the replacement reads: **3 queries,
   11 ms**. The rewrite is in scope, as the spec says.
3. **The automatic placement of a new hire (US-18 to US-22) puts new code inside every Employee save.**
   That is the most shared save in the product. It is safe only if one thing is proven on the bench
   first: that a refusal inside the placement rolls back the seat record and nothing else, and that
   its error message does not reach the person saving the Employee. **I found one trap the spec does
   not mention:** Frappe adds the refusal's red message to the response *before* it raises, so even
   a rolled-back placement would show "Position is over-filled" to the HR user, unless the hook
   mutes messages while it tries. I have planned for it (§5.4).
4. **Nobody at DTC will see the placement work yet.** DTC has 0 employees who came through Frappe
   hiring. I recommend building it **last**, and only after you answer Q-2 (does DTC plan to hire
   through Frappe?).
5. **The local bench cannot test this slice as it stands.** The bench runs the main checkout's `dev`,
   which is **10 commits behind `origin/dev` and does not have slice 061**, the permission model this
   slice is built on. I will test in a throwaway container from the slice worktree (the parallel-work
   rule for anything bigger than one module), not by moving the shared bench.
6. **Another session is in the same files.** Slice 064a (`.claude/worktrees/064a-organogram-bugs`)
   has two unpushed commits in `portal.js`, `positions.html`, `check_positions_tree.js` and `api.py`.
   Its "Arrange by always visible" commit (e157de4d) is replaced by this slice's View control and should
   be dropped; its setup-tool fix (7cdbf0d4) is a separate change (OD-6) and does not touch what I
   change in `api.py`. Plan in §4.
7. **After 061 reaches `main`, DTC's HR Managers cannot open Positions** (OD-3). This slice does not
   change that, and must not reach `main` before 061.

---

## 1 · Impact analysis - functional

### 1.1 Cross-module reach

| App | Touched? | How |
|---|---|---|
| `alvoraa_portal` | **Yes** | `portal.js` Positions section (window, roll-ups, Find, View control, sheets, list, phone outline); `positions.html`; `panels.css`; `design_system.html` (one token change, Q12 - touches every page); `org_job_link.py` (seat link editable, Job Opening change history on) |
| `hrms` - our org-structure code | **Yes** | `register.py` `position_table` (new keys); `api.py` `reporting_mismatches` (rewritten in place); **new** `alvoraa_org_structure/hiring.py` (placement hook + seat-link guard); `hrms/hooks.py` (two `doc_events` lines) |
| `hrms` - Frappe HR's own code | **No edits** | Employee, Job Applicant, Job Offer, Job Opening used as shipped. Frappe HR's own Employee `after_insert` (marks applicant and offer Accepted) runs first and is untouched |
| `erpnext`, `frappe` | No | |
| `alvoraa_goals`, `alvox_compensation` | No | Nothing there reads seats. Checked: `reports_to_position` is read only inside `alvoraa_org_structure` and one patch |

**Organisation page.** Not changed. It keeps the shared drawing (`ocRender`, `ocNodeCard`). Two
knock-ons from data, both intended: a placed hire shows in their seat on the Organisation chart from
the joining date, and `metrics.org_health` counts one fewer vacancy.

**Approval delegation (`_people_under`).** Not changed. A placed hire becomes one of the people under
the parent seat. A **later** cover of that parent with "also move approvals" moves theirs too. A cover
**already running** does not, because it recorded its list when it started (SEC-9, the safe
direction). The placement never writes `reports_to`, `leave_approver` or `expense_approver`.

**Organisation page reach.** A hire placed in a seat with seats under it gets the manager's view of the
Organisation chart while `alvoraa_org_managers_see_all` is on. That is the same as a manual placement
today, and it is why SEC-8 ships with the hook.

### 1.2 Every caller of every function I would change (grep, 21 Oct 2026)

| Function | Callers found | Effect |
|---|---|---|
| `register.position_table` | `portal.js:307` (`posLoad`); tests `test_register_194.py` (17 calls), `test_register_fill_194.py` (9 calls) | Keys **added** only. Every existing key keeps its name and meaning, so no caller changes |
| `api.reporting_mismatches` | **None.** Only its definition, a `.pyc` and `ux-learnings.md` | Rewritten in place, same name. Gate changes from "HR Manager or System Manager" to `may_view()` plus HR scope (SEC-2). The unused `count` key goes |
| `org_job_link.after_migrate` | `alvoraa_portal/hooks.py:441` (after_migrate), `:492` (after_install) | Same function, two more properties. Frappe's `create_custom_fields` updates an existing field (`update=True`, read in source), so `read_only` 1 → 0 reaches existing sites on the next migrate |
| `portal.js` Positions functions to delete or replace: `posPaint`, `posPaintTree`, `posNode`, `posToggle`, `posGroupNode`, `posHolderNode`, `posByBranch`, `posByDepartment`, `posSeatsIn`, `posCountSeats`, `POS_OPEN_DEPTH`, `POS.onPath`, `pos-f-view`, `pos-f-arrange` | Only `portal.js`, `positions.html`, `scripts/check_positions_tree.js`, `scripts/browser_check_positions.js` | Replaced inside the Positions section. No other screen uses them |
| `ocRender`, `ocNodeCard` (shared with the Organisation page) | `portal.js:1098` (Positions) and `:1948` (Organisation) | **Not changed.** Positions stops calling `ocRender`; the Organisation page keeps it |
| Assignment rules (`AlvoraaPositionAssignment.validate/on_update`), `AlvoraaPosition._current_assignments` | Called, not changed | The hook relies on them. `_check_one_primary` already sets `is_primary = 1` for a person with no other seat, which answers the spec's Q-1 |

New: one `doc_events` entry on Employee (`after_insert`, added at the end of the existing list) and a
new `Job Opening` key (`validate`) in `hrms/hooks.py`.

### 1.3 Personas

| Persona | What changes |
|---|---|
| **CXO / Owner** (at DTC: Org Structure Editor, no HR role, tied to one branch) | Positions opens on the chart, not the list. The top plus its family fits one screen, every box counts what is below it, Find, a phone reading mode. **Gets no people lists and no records chips** until you decide X-2 and X-3 (fail-closed interim) |
| **HR Manager** (main user) | All of the above, plus "In no seat" and "No reporting manager" lists for their companies or branches, the records and pooled-seat chips, and hires placed by themselves. **At DTC after 061 they cannot open the page at all** unless OD-3 adds a Read row |
| **HR User** without Positions edit | Nothing new on Positions. Saving an Employee from an applicant may now place them in a seat (one bounded bypass, SEC-7). **Can no longer** set an opening's seat link through the API (SEC-8) |
| **Store head** (if a tenant gives them Positions) | Seats and roll-ups within their own rows only; "reports above your view" as today; no company lists |
| **Employee** | No change on Positions (they never open it). A new joiner shows in their seat on the Organisation chart from day one |

### 1.4 HRMS domains

Org structure: core. Recruitment: Job Opening read, its seat link guarded, and closed by the hook when
filled. Leaves: no change (the X-5 fact check stands: Frappe HR's leave approver never reads
*Reports To*). Attendance, payroll, appraisals, goals, compensation: not touched. `reports_to` is never
written.

---

## 2 · Impact analysis - non-functional

### 2.1 Measured numbers (local bench, ppj.localhost, 120 seats, 403 people)

| What | Today | After 064 (measured where marked, otherwise from the code) |
|---|---|---|
| `position_table` queries | **6** (measured) | about **9 to 11** for an HR reader: + seat dates per company (1), + unseated list (1), + active count (1), + the scope helpers if not cached. **Same at 20 and 1,000 people**: none of these runs per row |
| `position_table` time | **28 ms** (measured) | unseated query alone **3 ms** (measured, `NOT EXISTS` form) |
| `position_table` payload | **134 KB raw, 10.6 KB gzipped** (measured) | about **160 KB raw, 13 KB gzipped** at DTC (estimate: `created` and `hired_on` per row, 82 unseated people at about 170 bytes) |
| Records check queries | **1,458** (measured) | about **5** (2 grouped reads + scope helpers). The two main reads measured at **3 queries, 11 ms** |
| Records check time | **1,422 ms** (measured) - over the 500 ms budget | well under 100 ms (estimate from the 11 ms reads) |
| Roll-up of every box | - | **0.08 ms** at 90 seats / 445 people; **0.55 ms** at 900 / 4,500 (node, synthetic) |
| Find, worst case per keystroke | - | **0.05 ms** at 90 / 445; **0.37 ms** at 900 / 4,500 (node, synthetic). No network request |
| Boxes drawn at DTC on open | today about 90 (everything opens at two levels - inference from the code) | **8**: the top, 5 team leads, 1 group box, 1 "No reporting manager" box |
| Side panel | - | one row per seat in the group: 17 to 20 at DTC, 60 on a flat tenant |

Wall-clock numbers on this machine move a lot between runs. The query counts and byte counts
reproduce; the milliseconds are a guide only.

### 2.2 The seven dimensions

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **improves** | The records check goes from 1,458 queries to about 5. The chart draws 8 boxes at DTC instead of about 90. `position_table` gets 3 to 5 more queries and about 20% more payload for HR, all flat in headcount - a small cost on one call, inside budget |
| **Security** | **improves**, with one new bounded bypass | Closes three existing findings: F1 (`reporting_mismatches` reads every company - SEC-5), F3 (any HR User can set an opening's seat link through the API - SEC-8), F4 (`register.py` has no ignore_permissions ceiling - SEC-7). Adds one `ignore_permissions` in the new `hiring.py`, on one insert, with every rule still running |
| **Reliability** | **neutral, if the savepoint check passes; degrades if it does not** | A new hook inside every Employee save is a new way for that save to go wrong. The design never raises out of the hook and rolls back to a savepoint. That must be proven on the bench before the hook is built (§6) |
| **Scalability** | **improves** | Every query count is flat in headcount. The window never draws more than three rows, however wide the company. Roll-up and Find stay under 1 ms at ten times DTC |
| **Maintainability** | **degrades** | About +1,000 lines of browser code net, and a second drawing of a hierarchy (Positions' window beside the Organisation page's tree). The old tree path is deleted, not kept beside it, and the JS check is rewritten, so there is one path, not two. Still more to maintain |
| **Data integrity** | **improves** | Hires land in their seat; openings close when filled; the records chip makes silent disagreements visible (like bug 3). Two weak spots, stated: a placement does not follow a joining date changed later (OD-7), and "hired for this seat" is read from the assignment's fixed `reason` sentence |
| **Compliance / privacy** | **neutral** | New: named lists of people with no seat or no manager, on a page. Bounded: HR scope only, fail closed, a fixed set of six fields (PRIV-1), nothing stored. Better: who linked an opening to a seat is now recorded (PRIV-3) |

---

## 3 · Rung on the ladder

| Part | Rung | Why the cheaper rung was rejected |
|---|---|---|
| Window, roll-ups, Find, group box, sheets, phone outline | **4 - new code** in the existing page | Nothing in Frappe draws this. No setting does it. The prototype is the approved contract |
| People lists, records check | **4 - new code inside existing endpoints** | No new endpoint, no report, no DocType. A Query Report would be a second screen and a second permission surface |
| Seat link editable | **2 - configuration** (one property on our own custom field) | - |
| Job Opening change history | **2 - configuration** (Property Setter `track_changes = 1`) | A Comment can be deleted; a log DocType is more surface for one field |
| Seat-link guard (SEC-8) | **4 - a `validate` hook on Job Opening** | `read_only` is not enforced by the server; `permlevel` cannot express a branch scope, and a Custom DocPerm on Job Opening at DTC would replace all its shipped rows (01d) |
| Placement | **4 - one Employee `after_insert` hook** | "Put somebody in it" by hand already exists and is the step people forget (the complaint). A Server Script is not in the repo and not tested |
| Blue colour and darker amber | **3 - one design-token change** | The existing amber text on its tint measures 4.42:1, under the 4.5:1 line, so the darker amber is a fix, not a taste |

No new DocType, field, page, report, setting, cache, background job or app.

---

## 4 · Parallel-work check

**Fetched 21 Oct 2026.** `origin/dev` is at 76f15e1d. This worktree's branch holds everything on
`origin/dev` plus 7 commits not pushed: six slice-063 document commits and **5a211f3f** ("A refused
seat delete says why inside the dialog"), which touches `portal.js`, `positions.html`, `panels.css`
and `check_positions_tree.js`. Recent `origin/dev` work in these files: slice 061 (19183b7f, 2d821449,
f7af5ac0, 6e98a545) and ALV-199's attendance picker (d83367ab). I read them; nothing in them conflicts
with the plan.

| File | Hot? | Who else is in it | Plan |
|---|---|---|---|
| `alvoraa_portal/.../public/js/ess/portal.js` - Positions section only | Yes (shared file) | 064a (e157de4d, 7 lines in `posPaint`; 7cdbf0d4 not in this file); 5a211f3f (delete dialog, not pushed); 060 picker (`ac*`, done) | **Sequence:** 5a211f3f reaches `dev` first, or 064 is built on it. **e157de4d is dropped** - this slice replaces it (you already said so on the work board). I touch only `pos*` functions and the Positions block; shared helpers (`gpFetch`, `ocRender`) untouched |
| `.../templates/includes/ess/parts/positions.html` | No | 064a (e157de4d, dropped); 5a211f3f (delete dialog lines) | Same sequence. I change the toolbar and body, not the delete dialog |
| `.../public/css/ess/panels.css` | No | 5a211f3f (2 lines) | New `pos-*` classes only, added at the end of the Positions block |
| `.../templates/includes/design_system.html` | **Yes - every page** | Nobody on the board | Its own commit, so it can be reverted alone |
| `scripts/check_positions_tree.js`, `scripts/browser_check_positions.js` | No | 064a (section 21, dropped with e157de4d); 5a211f3f | Rewritten for the window. 5a211f3f's delete-dialog checks kept |
| `hrms/.../alvoraa_org_structure/register.py` (`position_table` only) | No | Nobody | - |
| `hrms/.../alvoraa_org_structure/api.py` (`reporting_mismatches` only) | No | 064a 7cdbf0d4 (`propose_positions`, ~line 282) | **Split:** different functions, no shared lines |
| **new** `hrms/.../alvoraa_org_structure/hiring.py` | - | - | - |
| `hrms/hrms/hooks.py` (`doc_events`) | **Yes** | Nobody on the board | One line added at the end of Employee `after_insert`, one new `Job Opening` key, each with a comment. Never rewrite the block |
| `alvoraa_portal/alvoraa_portal/org_job_link.py` | No | Nobody | - |
| `alvoraa_portal/.../tests/test_portal_security_010.py` (`CEILINGS`) | Yes (shared fixture list) | Many slices add rows | Rows added at the end only |
| **new** tests: `hrms/.../tests/test_positions_064.py`, `test_hiring_064.py` | - | 064a adds a class at the end of `test_org_structure.py` | New files, so no clash |

**Main checkout:** has many untracked files from other sessions (docs, mobile). None are mine; none
are in the files above. **Local `dev` is 10 commits behind `origin/dev` with nothing of its own.**

**Pin tests (a bad merge must fail CI, not users):** the rewritten `check_positions_tree.js` names
each feature (window, roll-up, group box, Find with no request, View control); `test_positions_064.py`
pins the people lists' scope and key set and the records check's flat count;
`test_hiring_064.py` pins placement, SEC-8 and the opening close; `CEILINGS` pins the bypass count.
Existing pins kept: K3 grouping, circle and depth notices, 5a211f3f's delete-dialog checks.

**Other developers:** I cannot see other machines. `git log` shows only this account in these files
in the last 10 days. **Please tell me if anyone else is working on Positions or Job Opening.**

---

## 5 · Strategy

### 5.1 The order - thin steps that each stay green

Every step ends with the JS check passing, the changed Python modules' tests passing, and a commit.
The order follows the risk: browser-only work first (nothing on the server can break), scoped data
next, then the rewritten records check before the chip that uses it, then the hook and its guard
together, last.

| Step | What | Stories | Files | Proven by |
|---|---|---|---|---|
| **1** | Colour tokens: add a blue pair, darken light `--amber` until amber-on-tint ≥ 4.5:1 | US-9 (part), Q12 | `design_system.html` | `scripts/check_contrast_rendered.py`; screenshots of every page at review (RK-4) |
| **2** | The window, browser only: one View control (replaces both dropdowns, fixes bug 1); home = real top + its family; one family open at a time (band); slide down; sticky breadcrumb with Up one level / Back to the top; rows wrap to the frame; roll-up "Below:" line on every box; holder views use the same window; X-7 several-roots home. **Delete** the old depth-folding tree path | US-1..6 | `portal.js`, `positions.html`, `panels.css`, `check_positions_tree.js` | JS check: at most three rows, no sideways scroll, roll-ups equal row counts incl. a parent whose child is missing (SEC-1 b) |
| **3** | Group box and side panel: 5 or more childless seats under one parent become one dashed box; "Show the N seats below" opens the panel directly when the whole family is childless; the seat sheet for every reader ("Change this seat" opens today's dialog unchanged; "Advertise it" as today; "Back to the N seats"); focus returns to the opener | US-26, US-11 | same | JS check on F-DTC shape: AC-85..90 |
| **4** | Tiles, key, filters that grey with "N matching below", states (loading, could not load, nothing matches), List columns and caption, new-seat and new-hire marks. Server: add `created` per seat, `first_seat_created` per company, `hired_on` per person (from fields already read), `may_edit_employee` | US-8, 9, 10, 15, 17, 22 (display) | `register.py` + the three browser files | JS check; `test_positions_064.py` for the new keys |
| **5** | Find, in the browser over loaded rows only, incl. B-8 (a seat inside a group opens its panel at that row) | US-7 | browser files | JS check: no match → the right sentence; browser check: **no network request** while typing (SEC-3) |
| **6** | Phone outline at 390 px, incl. the dashed "No reporting manager" row | US-16, B-13 | browser files | browser check at 390 px: no sideways scroll, targets ≥ 44 px |
| **7** | **Scoped data:** `unseated` and `active_people` inside `position_table`, from one `NOT EXISTS` query over `permitted_employee_filters()`; **no key at all** for a reader without HR scope; the six PRIV-1 fields named one by one | SEC-2, PRIV-1 | `register.py` | `test_positions_064.py` on F-SEC: AC-46 (a)-(h); query count equal at 20 and 200 people |
| **8** | "In no seat" tile and sheet; "No reporting manager" box, tile and panel (people from `unseated.no_manager`, plus parentless seats other than the top); look-alike branch note | US-12, US-27 | browser files | JS check; AC-41..45, 93..97, 100..102 |
| **9** | **Rewrite `reporting_mismatches`** in place: `may_view()` first; nothing when the reader has no HR scope; seats from `_scope()`, people from `permitted_employee_filters()`; two grouped reads joined in Python; returns `mismatches` (today's keys) and `mixed` | SEC-5 | `api.py` | `test_positions_064.py`: AC-50 (a)-(d) on F-SEC; timed on ppj (403 people) against the 500 ms budget |
| **10** | Records chip and pooled-seat chip, from one call per page load, made only when `unseated` came back | US-13, US-14 | browser files | JS check; browser check: the call is made once, and never for `head` or `editorD` (AC-49, 51) |
| **11** | **SEC-8 first:** seat link editable (`read_only` 0, new description), Job Opening `track_changes` on (Property Setter), the `validate` guard on Job Opening | US-20, SEC-8, PRIV-3 | `org_job_link.py`, `hiring.py`, `hooks.py` | `test_hiring_064.py`: AC-72..74, run as `hrU` |
| **12** | **Then the hook**, in the same push as step 11: placement on Employee `after_insert`, the opening closed when filled, the messages N-1..N-8; `CEILINGS` rows | US-18, 19, 21, SEC-6, 7, 9, 10 | `hiring.py`, `hooks.py`, `test_portal_security_010.py` | `test_hiring_064.py`: AC-64..71, 76..78, **as `hrU`, never as Administrator** |
| **13** | Must-not pins and the browser walk: AC-79 (no Print), AC-81 (no "replacement" or "planned" anywhere), AC-80, 82, 83; the parity table walked row by row on the running screen | US-23, 24, 25 | tests only | full `alvoraa_portal` and `hrms` suites, **once, at the end** |

Steps 11 and 12 are separate commits so no commit ever has the hook without its guard, and they are
pushed together.

### 5.2 The ignore_permissions budget (SEC-7)

| File | Today (counted by the SEC-16 method) | After 064 | Ceiling row |
|---|---|---|---|
| `alvoraa_org_structure/register.py` | 4, **no ceiling** | 4 | **added at 4** |
| `alvoraa_org_structure/hiring.py` (new) | - | **1** - the assignment insert, with a comment saying why | added at 1 |
| `alvoraa_org_structure/api.py` | 2 | 2 (the rewrite adds none) | stays 2 |
| `alvoraa_position_assignment.py`, `alvoraa_position.py`, `metrics.py`, `org_job_link.py` | 0 | 0 | added at 0 |

I put the hook in a new file rather than in `register.py`, so `register.py`'s ceiling stays at its
true count and the one new bypass sits alone in a file the test names. The hook sets no
`ignore_validate`, `ignore_mandatory` or `ignore_links`, so every assignment rule still runs. The
opening close uses **no** bypass (SEC-10).

### 5.3 SEC-8 ships with the hook

The guard is a `validate` on Job Opening. It runs only when the seat link is **set to a new value**
(desk, REST, data import or `post_job`). It checks, in order: Write on Alvoraa Position (`may_edit`);
the seat inside the caller's `_scope()` (company and branch); the seat's company equals the opening's.
Any failure refuses through `refuse()`, so the security log records it, with message N-9. A save that
does not change the link (closing, editing the description, Frappe HR's nightly close-by-date job) is
never checked. `post_job` keeps working for an editor in scope because it passes the same check. The
guard holds whether or not the field is editable on the desk - the API can set it today.

### 5.4 How the hook stays out of the Employee save's way

```text
on Employee after_insert:
  stop quietly unless: Active, job_applicant set, date_of_joining set,
                       the applicant's opening has a seat link
  stop with a message (N-2..N-6) if: another Employee has this applicant; seat Closed;
       seat company differs; they already hold a seat; no room today or on the joining date
  savepoint
    mute messages                       <- the trap: frappe.throw records its message first
    insert the assignment (one ignore_permissions; every rule runs; on_update over-fill check runs)
  on any error: roll back to the savepoint, write an Error Log with ids only, show N-6b
  otherwise: release the savepoint, show N-1
  then: close the opening if its hires reach vacancies (>= 1), as the user, no bypass;
        if they may not, leave it open and show N-8
  never raise out of this function
```

Room on the joining date uses the seat's own `_current_assignments(on=joining_date)`, so the hook and
the chart count fill the same way. The doctype's own over-fill check counts today only, which is why
the hook checks both dates (SEC-6).

### 5.5 What I would NOT build

- Group C (Plan a replacement) - not one line. Only the negative test AC-81.
- Print this view (X-4).
- A server search for Find; reuse of `search_people` or `_descendant_count`.
- A setting for the 5-seat group, the 30-day "new" window or the 60-day leaving tile.
- A cache, index, background job or stored count. Every number is worked out on each load.
- Any change to `ocRender` or the Organisation page.
- Any permission row, shipped or DTC's (SEC-11, OD-3 is yours).
- The setup-tool fix (OD-6, it lives on 064a) and the DTC data fixes for bugs 3 and 4.
- A rule to follow a joining date changed after placement (OD-7).
- A backfill of seats for past hires.
- A "placed automatically" field - the assignment's `owner` and fixed `reason` sentence answer it.

---

## 6 · Risks, trade-offs, and the checks I must run on the local bench

### 6.1 Risks

| # | Risk | What I do about it |
|---|---|---|
| R-1 | A placement refusal leaves a half-written record, or its red message reaches the HR user | Savepoint + muted messages, proven on the bench **before** step 12 (check B-1). If it cannot be proven, I stop and tell you; the hook does not ship |
| R-2 | The hook's queries grow with a big data import of Employees | Fixed queries per Employee (about 8); nothing per seat or per person |
| R-3 | The token change alters colours on every page | Own commit; contrast script; screenshots of every page at review |
| R-4 | The JS check rewrite drops an existing pin | Every existing check is either kept or replaced by a named equivalent; I list them in the implementation notes |
| R-5 | `hired_on` is read from the `reason` sentence, which a person could type by hand | Acceptable simplification: the worst case is a "new hire" mark on a hand-made assignment for 30 days. The sentence is stored in English, untranslated, so the match is stable |
| R-6 | The records check counts "primary" holders, but `is_primary` really means "most recently added" (noted in `register.py`) | I use **Permanent, current** assignments instead of `is_primary`. At DTC nobody holds two seats, so the result is the same. `[ASSUMPTION]` - say if you want `is_primary` |
| R-7 | 064 reaches `main` before 061 | Release note and AC-99; I will list every commit before any push |
| R-8 | A second drawing of a hierarchy (Positions' window vs the Organisation tree) | Intentional trade-off: the window cannot be drawn by the shared recursive tree without changing the Organisation page. The box styles (`oc-box`, tones) are shared, so the two still look alike |

### 6.2 Bench checks - local only, never production

All in a throwaway container from the slice worktree with its own site, because local `dev` lacks 061.
Claimed on the work board first. One run at a time.

| # | Check | Pass means |
|---|---|---|
| B-1 | **Savepoint inside Employee `after_insert`.** As `hrU`, create an Employee whose placement fails the over-fill check in `on_update` | Employee saved; no assignment row; no orphan child row; no Version row for the assignment; no "over-filled" text in the response messages; Error Log has ids only |
| B-2 | **`read_only` on the server.** As `hrU`, `frappe.client.set_value` on `Job Opening.alvoraa_position` before SEC-8 | Succeeds (proves F3 on v16.33.1); after SEC-8, refused and logged. I will also read Frappe v16.35.0's `document.py` (the version the image pins) to confirm nothing changed there - read only |
| B-3 | Migrate twice | Field `read_only` goes 1 → 0 once; exactly one Property Setter for `track_changes` |
| B-4 | Query counts | `position_table` and the records check: same count at 20 and 200 people, numbers recorded |
| B-5 | Records check timed on a DTC-sized copy (ppj.localhost, 403 people) | p95 ≤ 500 ms |
| B-6 | Browser checks: F-DEEP at 1440 px and 390 px, light and dark | At most three rows; no sideways scroll; text ≥ 12 px; targets ≥ 24 / 44 px; no script error; no request while typing in Find |
| B-7 | The full `hrms` and `alvoraa_portal` suites | Once, at the end |

Nothing here touches dev or production. No `bench migrate`, `bench build`, `clear-cache` or `docker cp`
on the shared bench without your word.

---

## 7 · Size and commit plan

| Group | Steps | Estimate |
|---|---|---|
| Window, group box, sheets, tiles, filters, list, Find, phone (US-1..11, 15..17, 26) | 1-6 | 4 to 5 days, most of it the window and the JS check rewrite |
| People lists and their screens (US-12, 27, SEC-2) | 7-8 | 1 day |
| Records check and chips (US-13, 14, SEC-5) | 9-10 | 1 day |
| Seat link, placement, closing (US-18..22, SEC-6..10, PRIV-3) | 11-12 | 1.5 days |
| Must-nots, parity walk, full suites (US-23..25) | 13 | 1 day |
| **Total** | **13 commits** | **8 to 10 working days** |

Rough size: about +1,000 lines of browser code net (after deleting the old tree path), about +200
lines of Python, about +700 lines of tests.

---

## 8 · What I would build now, and what waits for you

**Build now** - nothing blocks it, and every conflict has a fail-closed interim from the spec:
steps 1 to 10. That is US-1 to US-17 and US-26, US-27, US-23 to US-25. The X-1, X-2, X-3, X-5, X-6 and
X-7 interims are built as the spec's §6.3 says, each with a one-line note, so your answer is a small
edit.

**Waits for a decision:**
- **Steps 11 and 12 (US-18 to US-22, the hire placement and SEC-8)** wait for **Q-2** (does DTC plan
  to hire through Frappe?) and **E-1** below. If the answer is "not soon", I recommend leaving them out
  of 064: it is new code in every Employee save, and nobody would see it work.
- **The DTC release** waits for **OD-3** whatever else happens.
- **Parity sign-off** waits for X-1 to X-8 and Q18.

---

## 9 · Questions for you

**Must answer before I build:**

1. **Approve the strategy?** Steps 1 to 10 now; steps 11 and 12 after Q-2.
2. **Q-2 · Does DTC plan to hire through Frappe** (Job Opening → applicant → offer → employee)? Today
   it has 0 such hires. My recommendation: if not within a month or two, leave the placement out of
   064.
3. **E-1 · Close only openings linked to a seat?** The spec says "close the opening when filled" but
   not which openings. Closing every Frappe HR opening when its vacancies fill would change hiring for
   the whole tenant, not just Positions. **My default: only openings with a seat link.**

**Can answer after the build (the spec's defaults are built meanwhile):**

4. **OD-3 · DTC's HR Managers after 061:** add one Read row on Alvoraa Position at DTC? (Blocks the DTC
   release, not the build.)
5. **X-1 to X-8**, each with the interim in spec §6.3. The two that matter most:
   **X-2** (should DTC's owners see the named "In no seat" and "No reporting manager" lists?) and
   **X-3** (the records chips, same readers).
6. **OD-1, OD-2** · Confirm the designer's Q1-Q17 and the PM's D1-D6 as the spec lists them.
7. **OD-5** · "Leaving": tile 60 days, everything else any future date (today's split)?
8. **OD-6** · The setup-tool fix on 064a as its own small change? (And may 064a's e157de4d be dropped?)
9. **OD-7** · Should a placement follow a joining date changed after it? (Default no.)
10. **OD-8** · Group C built with 065, not shipped dormant here? (Default yes.)
11. **OD-9 / Q18** · Group seats with nobody under them from 5 or more? (Default 5.)
12. **OD-10 / Q19, X-8** · For 065: the group box never turns red for a plan? (Not built in 064.)
13. **Q12** · Add the blue pair and darken `--amber` on every page? (Default yes, own commit.)

**Small ones, my default stated:**

14. **E-2 · K3 grouping with the v4 group box.** Today identical leaf seats (same title, branch,
    department) are drawn as one box. With v4, five or more leaf seats go into the group box anyway.
    **My default:** K3 still groups identical seats among four or fewer leaves; inside the group panel
    every seat is its own row.
15. **E-3 · Clearing an opening's seat link.** **My default:** allowed without the SEC-8 check,
    because clearing it cannot place anyone.
16. **5a211f3f** (the delete-dialog fix in this worktree) is not on `origin/dev`. **My default:** it
    goes to `dev` before 064, and 064 is built on top of it.
17. **Anyone else** (another developer) working on Positions or Job Opening?

Answered by me from the code, so no longer open: **Q-1** - the assignment controller sets
`is_primary = 1` by itself for a person with no other seat, and the hook only places people with no
seat. **Q-3** - SEC-8 holds whether or not the server enforces `read_only`; B-2 checks it anyway.
**Q-4** - is check B-1.

---

## Assumptions

- `[ASSUMPTION]` The records check counts Permanent, current holders, not `is_primary` (R-6).
- `[ASSUMPTION]` The unseated list uses Frappe's query builder with `NOT EXISTS` (pypika's
  `ExistsCriterion`, present in the bench source). If it cannot express the scope filters cleanly, I
  write one parameterised SQL statement the way `org_figures.py` already does. Either way the scope
  stays in the database and no list of ids is sent back.
- `[ASSUMPTION]` A manager's name in the records check may be shown to HR even when the manager sits in
  another branch, because it is the value HR already sees on the employee's own record. Say if not.
- `[ASSUMPTION]` Bench measurements on ppj.localhost (pre-061 code) stand in for DTC. The read path
  measured did not change in 061.

## Subtract pass

Removed on the final read:
- A separate endpoint for the records check's per-seat counts: the browser works them out from the two
  lists and the seats it already has.
- Folding the records check into `position_table`: cheaper by one round trip, but it is a change to the
  spec's call pattern for little gain, so I kept the spec's separate call.
- Skipping the hook during data import or migrate: the spec wants an import to place people, and a
  migrate creates no Employees.
- A second test file for the people lists: they share `test_positions_064.py` with the records check.
- The `count` key on `reporting_mismatches`: nothing reads it.

Kept, and why: the deletion of the old tree path (two paths would be worse than one); the muted
messages in the hook (without them a rolled-back placement still shows an error to HR); the new
`hiring.py` (keeps the one new bypass in its own counted file).
