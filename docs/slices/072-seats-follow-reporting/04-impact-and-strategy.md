---
slice: 072-seats-follow-reporting
artifact: 04-impact-and-strategy (change-process steps 1 and 2; the engineer's 00-impact-analysis for this slice)
author: hrms-fullstack-engineer
date: 2026-10-25
status: proposal - waiting for Surbhi's approval. Paper only. No code written, nothing committed, nothing pushed, no server or container touched.
inputs: 01-product-brief.md, 02-design.md (approved by Surbhi on the designer's recommendations - Q1 "in all" counts people; Q3 the split advice goes, replaced in Reporting lines by "Where it shows on this chart"; Q4 one name "Reporting lines"; Q5 a manager in the same seat keeps people home; Q6 the new box words), prototype-v1.html (buildModel), rules decided in the task (below), 065 04-impact-and-strategy.md and 03-functional-spec.md (worktree 060-manager-review), .claude/context change-process, no-over-engineering, nfr-budget, parallel-work
code read: origin/dev af0b7cdf in worktree 069-wall-chart - register.py (position_table, _unseated, _scope, _may_see_who_is_leaving), api.py (reporting_mismatches), portal.js Positions section (ocNodeCard, ocRender, posKids, posNode, posGroupSiblings, posGroupNode, posFew, posPaintTree, posKeepRows, posFind*, posMarkFirst, posSeatSheet, posRecordNotes, posLoad, posWall*), panels.css Positions and wall blocks, parts/positions.html, scripts/check_positions_tree.js, check_positions_connectors.js, check_wall_chart.js, check_wall_chart_browser.js, lib/wall_chart_fixture.js, test_portal_security_010.py CEILINGS; branch diffs of slice/065-option-a and slice/066-grooming against origin/dev; Frappe v16.33.1 source on hrlocal-bench (read only): frappe/__init__.py get_all, frappe/database/query.py DynamicTableField / LinkTableField
measured: nothing. No bench, no container, no site was used for this paper. Every number below is worked out from the code and marked so; step 1 and step 8 measure them.
---

# 072 · Impact analysis and strategy: Seats follow the reporting line

## The rules this builds (decided, not proposed)

- The chart follows the Employee's **Reports To**.
- A seat whose people report to different managers is drawn once per manager. Each **copy** hangs
  under that manager's seat and lists only that manager's people.
- **Copies never have boxes under them.** So no loop is possible.
- A seat's own box (its **home**) is hidden only when it has no people, no open slot and no child seats.
- A vacancy shows **once**, on the home box.
- Slice 065 plans travel with the person, and stay absent for anyone who is not a plan reader.
- **Reporting lines view only.** Branch and Department stay as today.
- The CFO script: Part A only. Part B is skipped.
- The 64 people reporting to HR-EMP-00001 are real (brief Q2 is closed).

## 0 · Bad news first

1. **This slice has no functional spec, no security and privacy requirements (`01c`) and no DevOps
   inputs (`07`).** The engineer's rule is "no spec, no code". This paper works from the brief, the
   approved design and the rules above. *I recommend:* you approve this strategy, and the analyst
   writes a short spec from §2.3's test list before step 2 starts (Question 1). The server change
   (step 1) is small enough to build first.
2. **The wall chart may fall under 069's own kill line.** 069 measured 9.5 pt for "All on A1" at
   DTC's 91 seats *before* copies. The 64 are real, so a copy of Back Office with about 60 names
   hangs under the Backoffice Executive seat. A 60-name box prints in 4 columns of 15. That box, plus
   about 10 to 25 other copies, could take A1 under 8 pt (069 AC-32). **I cannot measure DTC's real
   shape without reading production.** Step 8 measures a fixture shaped from the 24 Oct census. If it
   is under 8 pt, the answer is A0 or several sheets, and that is your call (Question 5).
3. **Three small places the design does not cover would go wrong if left alone.** I propose a rule
   for each (§2.2): **Find** would outline a seat's home box when the person it found is drawn in a
   copy; **filters** would draw copies that are neither a match nor above one, which fails 064's
   filter check; and a manager who holds **two seats, one of them this seat's parent**, would get a
   needless copy.
4. **The design names an unseated manager in the tray** ("Reports to Neeraj Sood, who is in no
   seat"). For an HR reader the name is already on the page (the "in no seat" list). For anyone else
   naming them needs one more database read and a scope check, so I propose they read "Reports to a
   manager who is not on this chart" (Question 3).
5. **Two slices were numbered 070 (this one is now 072, Surbhi, 25 Oct).** `070-readable-on-phone` (ALV-217) is being built now. The branch
   and folder names differ, so git does not clash, but people will. I call this one **072 seats**.

---

## 1 · Impact analysis

### 1.1 Parallel-work check (done before this analysis)

| Check | Result |
|---|---|
| `git fetch origin` | `origin/dev` is at **`af0b7cdf`**. The 069 wall chart (12 commits, `9e9cf2c6..af0b7cdf`) is on it. Nothing newer came in. The code read for this paper is exactly that commit |
| Main checkout | On `dev` at `2cbcc4b5`, which is not `origin/dev`. It holds other sessions' uncommitted edits (`CLAUDE.md`, `.claude/context/*`, `.claude/skills/*`, untracked docs, `mobile/field-app/`). **Not mine; not touched** |
| This worktree (dev-integration-2026-10-24) | Holds other sessions' untracked slice docs (065, 069, 071) and a changed `ux-learnings.md`. **Not mine; not touched.** I add only this file |
| Work board | See "who else" below. The 069 row still says "not pushed"; it is on `origin/dev` now - the board is out of date |
| Other developers | I cannot see other machines. **Surbhi: is anyone else working in `register.py` or the Positions screen?** |

**Files 072 seats would change**

| File | Change | Hot? | Who else is in it | Plan |
|---|---|---|---|---|
| `hrms/.../alvoraa_org_structure/register.py` | `position_table`: two joined columns on the assignment read, one `manager` key per person (about 20 lines) | Yes | **065-option-a** (`AUDITED`, a plan block after the leaving read, the `opening` rule, `out["plans"]` just above `permitted_employee_filters()`) | **Split**: my lines are in the assignment read and one block after `_unseated`. Adjacent to 065's `out["plans"]` line, so whichever lands second keeps both |
| `alvoraa_portal/.../public/js/ess/portal.js` | Positions section only: `ocNodeCard` (two optional fields), one new `posPlace`, and edits in `posNode`, `posGroupSiblings`, `posGroupNode`, `posPaintTree`, `posFind*`, `posSeatSheet`, `posRecordNotes`, `posLoad` (catch only), `posWallCopy`, `posWallBelow`, `posWallCount`, `posWallDepth`, `posWallStarts`, `posWallCard` | **Yes, the hottest** | **065 screens** (not started; will edit `posNode`, `posOne`, `posSeatSheet`, `ocNodeCard`), **066-grooming** (`ac*`, `gm*`, `pf*` only, +719 lines elsewhere), **070-readable-on-phone** (`gpFetch`/`gpErr`, about 25 load sites) | **Sequence** with 065 screens (072 seats first, §3.3). **Split** with 066 and 070-phone: different functions |
| `panels.css` | New lines at the end of the Positions block and the `.pos-wall` block: dashed copy border, quiet line, related outline | Yes | 066-grooming (+85 lines, its own block), ALV-213 (768/640 blocks) | Split: new lines only, in the Positions blocks |
| `parts/positions.html` | One word change: "Who reports to whom" becomes "Reporting lines" (Q4) | Yes for Positions | 065 screens (one line under Filters, later) | Split |
| `scripts/check_positions_tree.js` | New section at the end | 064's / 069's | - | New section only |
| `scripts/check_positions_connectors.js` | New meaning of "real parent", copy rules, a fixture mode | 064's | - | Changed in place, §2.4 |
| `scripts/check_wall_chart.js`, `check_wall_chart_browser.js`, `lib/wall_chart_fixture.js` | Copies on paper; fixture gains managers; A1 re-measured | 069's | - | New cases at the end; `paperAudit` learns copies |
| NEW `hrms/.../alvoraa_org_structure/tests/test_reports_to_072.py` | Server tests | No | - | - |

**Pin tests that keep existing features alive:** 064's `test_positions_064.py` (16 calls),
`test_register_194.py` (17), `test_register_fill_194.py` (9) run unchanged - the new key is
additive and no test freezes a person's key set (checked: the only key-set assertions are on
`UNSEATED_KEYS` and `reporting_mismatches`). Every existing `check_positions_tree.js` and
`check_wall_chart.js` case runs unchanged, because their fixtures carry no `manager` key and so
draw no copies. 072's own checks name each feature, so a bad merge that drops one fails CI.

### 1.2 Functional: cross-module reach

| App | Touched? | How |
|---|---|---|
| `hrms` (our org-structure code) | **Yes** | `register.position_table` only. Reads `Employee.reports_to` and `Employee.status`; **writes nothing** |
| `alvoraa_portal` | **Yes** | Positions screen, its CSS and one template line; checks |
| `hrms` (Frappe HR's own code) | No | Reports To is read, never written. Leave approval, appraisal routing (`pms_cycle.py`), attendance corrections all keep reading it as today |
| `frappe` | **No edits.** Uses its link-field join in `get_all` (`"employee.reports_to as …"`, `database/query.py` `LinkTableField`, present in v16.33.1) | - |
| `erpnext` | No | Employee read only |
| `alvoraa_goals`, `alvox_compensation` | No | Nothing reads the chart |
| Organisation page (`api.py`, `ocPaint`) | **Shares `ocNodeCard`/`ocRender`** | Two optional fields on the card. Left out, the card is byte-for-byte as today - pinned by a test |

### 1.3 Functional: every caller of what I would change

| Function | Change | Callers (grep, `af0b7cdf`) | Effect on them |
|---|---|---|---|
| `register.position_table` | Each person gains `manager` (§2.1). Nothing else | `portal.js:330` (`posLoad`); tests `test_positions_064.py` (16), `test_register_194.py` (17), `test_register_fill_194.py` (9); `check_positions_tree.js`, `check_wall_chart.js`, `check_wall_chart_browser.js`, `lib/wall_chart_fixture.js` (stubbed replies) | Additive key. `test_position_table_is_flat_in_headcount` stays flat: no new statement |
| `ocNodeCard` | Optional `n.cls` (extra class on the box) and `n.quiet` (one grey line inside the button) | `ocRender` (`portal.js:242, 254`), `ocPaint` (`:3184`, Organisation page) | Organisation page never sets them: identical markup |
| `posKids` | **Unchanged** | `posPaintTree`, `posSeatsIn`, `posExtraRoots`, `posWallCopy`, `posWallPaint`, `posWallPrint`, `posWallChange`, `check_wall_chart_browser.js` | - |
| `posNode`, `posGroupSiblings`, `posGroupNode` | Read home people, and children = real child seats not hidden + copies, from `t.place` when present | `posPaintTree`, `posSeatsIn` (Branch/Department: no `t.place`, so unchanged), `posWallCopy` (`posGroupSiblings` 3rd arg) | Branch and Department byte-for-byte as today |
| `posSeatSheet` | Accepts a copy's id; new section and per-person line in Reporting lines | box clicks, `posNoMgrSheet`, `posUnseatedSheet`, `check_positions_tree.js` (3), `check_portal_trays.js`, `browser_check_positions.js` | Seat ids work as today |
| `posRecordNotes` | Split advice removed; in Reporting lines the two notes are replaced (Q3) | `posSeatSheet` only | - |
| `posFindPick`, `posFindFocus`, `posFocusFirst` | A person drawn in a copy is found in the copy | Find box, filters, `browser_check_positions.js:143` | Seats found as today |
| `posLoad` | The error words only (§2.2 F) | Positions menu, Try again | - |
| `posWallCopy`, `posWallBelow`, `posWallCount`, `posWallDepth`, `posWallStarts`, `posWallCard` | Walk the placed model | `posWallPaint`, `posWallChange`, `posWallPrint`, `posWallLevels`, `check_wall_chart.js` (17), `check_wall_chart_browser.js` (5) | 069 fixtures with no managers: identical paper |
| `api.reporting_mismatches` | **Unchanged** | `posLoadRecords` | Its notes still show in Branch and Department |

New: `posPlace(t)` (one function, two callers: the screen and the paper), a delegated hover/focus
handler for the related outline, and the tray's Show handler.

### 1.4 Personas

| Persona | What changes |
|---|---|
| **CXO / Owner** (DTC: Org Structure Editor, no HR scope) | Sees people under their real manager's seat. Copies drawn for every manager seated in a seat they can see. Tray says "a manager who is not on this chart" for anyone else |
| **HR Manager** | Same chart, plus the unseated manager's name in the tray (already on her page). Fixes a line in one place: the Employee record. The split advice is gone |
| **Branch-limited reader** (store head, 069 D7) | Copies only under seats they can see. No hidden seat is ever named, in a box, a line or the tray |
| **Employee** | Nothing. Employees do not open Positions; the Organisation page is unchanged |

**HRMS domains:** org structure only. Leaves, attendance, payroll, appraisals, goals and pay are
not touched - Reports To is read, never written.

### 1.5 The one database read (what it is and what it costs)

The brief expected one more query (7 to 8). **I recommend none.** The read the page already makes
for the people in seats gets two columns from their Employee record through a join:

```python
frappe.get_all("Alvoraa Position Assignment", ...,
    fields=[...today's nine..., "employee.reports_to as reports_to_emp", "employee.status as emp_status"])
```

| | Today | With 072 seats (worked out, measured in step 1) |
|---|---|---|
| Statements per page open | 6 (HR Manager) / 7 (System Manager), measured on test064 by 065 | **the same** - a LEFT JOIN on Employee's primary key inside the existing statement |
| Statement cost | One indexed read of current assignments | plus one primary-key lookup per assignment row: about 361 at DTC, 1,000 at 10x. Negligible |
| Reply size | about 62 KB at 150 people, 195 KB at 964 (065's measure) | **+ about 26 bytes per seated person** (`"manager": "HR-EMP-00123"`): about +9 KB at DTC, +26 KB at 1,000 |
| Browser | - | `posPlace` is one pass over people and seats per paint: linear, well under 5 ms at 1,000 people `[ASSUMPTION - checked in step 8]` |

The scope stays inside the database (nfr-budget §2): no list of ids is read and sent back.

*Fallback, only if the join misbehaves on DTC's Frappe 16.35:* one separate read,
`frappe.get_all("Employee", filters={"name": ("in", holders)}, fields=["name", "reports_to", "status"])`.
**+1 statement**, flat in headcount, but an id list - the same shape as today's leaving read, which
the budget names as a smell. Used only if step 1's test fails on the join.

### 1.6 The seven non-functional dimensions

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **neutral** | No new statement; +26 bytes a person; one linear pass in the browser. A1 size may drop (bad news 2) - that is readability, measured in step 8 |
| **Security** | **neutral** | No new endpoint, no new whitelisted call, no new write. `ignore_permissions` in `register.py` stays at 4 (CEILINGS unchanged). The join is a constant field string, no SQL built by hand. `manager` is sent only for a person this reply already carries |
| **Reliability** | **neutral** | A missing, Left or hidden manager falls back to the home box - the chart can only look like today, never lose a person. Old browser + new server ignores the key; new browser + old server draws no copies. Copies have no children, so no loop. One risk: the shared card - pinned by a byte-for-byte test |
| **Scalability** | **neutral** | Flat statements; payload and browser work grow linearly with people, as today. A manager with 400 reports is one copy, three names, "+397 more here" |
| **Maintainability** | **degrades, slightly** | About 150 lines of screen code and 20 of server code, one new function. Kept: one placement rule for screen and paper, no second idea of the tree |
| **Data integrity** | **improves** | The chart now agrees with what approvals and appraisals use. Worked out on every load, so never stale. No cache, no stored copy, nothing to keep in step |
| **Compliance / privacy** | **neutral** | Reporting lines are already on the Organisation page. `manager` is sent fail-closed (§2.1). No hidden seat or manager named. No new log line. 065 plans: no new key, they ride on the same person object and stay absent for non-readers |

---

## 2 · The strategy

**Rung of the ladder: 4, new code in our own app.** Cheaper rungs, checked again:
- *Already there:* Frappe HR's Organizational Chart draws people by Reports To, but has no seats,
  no vacancies and 445 boxes (brief §4).
- *Configuration / customisation:* nothing in Frappe draws a seat in two places.
- *Data fix (Part B):* you decided against it - it goes stale with the next Reports To change.
- *The chip (option C):* does not do what you asked.
No new DocType, field, setting, hook, endpoint, cache, job, patch or app.

### 2.1 Where the rule lives: the server says who, the browser says where

| Part | Lives in | Why |
|---|---|---|
| **Who is this person's manager**, and may this reader be told | **Server**, `position_table` | Only the server knows Reports To and the reader's scope. Fail-closed there |
| **Which box the person is drawn in** | **Browser**, one function `posPlace` | It depends on what is drawn: the view (Reporting lines only), a filter, the wall chart's start and levels. One function feeds the screen and the paper, so they cannot drift |

**Server rule (`manager` on each person):**
- **Absent** unless `as_at` is today (Reports To has no history; a past date draws as before).
- **`""`** when the person's Reports To is empty ("No manager on their record").
- **The manager's employee id** only when the manager is **Active and already in this reply**:
  seated in a seat this reader sees (from the same read), or - for an HR reader - in the "in no
  seat" list the reply already carries.
- **Absent** otherwise: a Left manager, a manager seated only outside the reader's scope, or an
  unseated manager for a reader with no HR scope. The page draws them home.
- Code shape: the seated set is built from the existing `people` dict **before** line 446, where
  `register.py` reuses the name `people` for the employee filter. Not renamed - not this slice.

**Reuse, in order:** the existing assignment read (no new statement); Frappe's own link-field join
(the same idea as `reporting_mismatches`' manager join); the `people` dict and the `unseated` list
already in the reply; `posKids`, `posGroupSiblings`, `ocRender`'s hanging column, the seat tray,
`posMarkFirst`. **Not reused:** `reporting_mismatches` itself - it is HR-only (owners get nothing),
Permanent-only, and loads after the chart paints, so the chart would jump.

### 2.2 The browser rule (`posPlace`), with the three gaps closed

For each person in seat S, in the Reporting lines view, among the **drawn** seats:

| Their manager | Drawn in |
|---|---|
| sits in S's parent seat, or in S itself (Q5) - in **any** of the manager's drawn seats | home |
| sits in another drawn seat | a copy of S under that seat. Two or more seats: Permanent first, then highest weight, then title (brief §3) |
| `""`, absent, or not seated in a drawn seat | home |

- **A. Copies** are end boxes: no fold button, nothing under them, dashed border, never grouped with
  another seat, placed after the real child seats. A seat with a copy under it is never grouped.
- **B. Home** keeps the open slots, the job opening and the child seats. It is hidden only when it
  has no people at home, no open slot and nothing under it; **a copy hanging under it counts as
  something under it**, because that copy has nowhere else to hang (the prototype does the same).
- **C. Filters** (gap 3b): with a filter on, copies are drawn only of **matching** seats and only
  under a manager seat that is drawn. A faded seat above a match keeps all its people at home.
  This keeps 064's filter rule true: nothing drawn is neither a match nor above one.
- **D. Find** (gap 3a): a person drawn in a copy is found in the copy - the path to the manager's
  seat opens and the copy is outlined.
- **E. Box words**, tray, view note, related outline, phone: as the approved design §5.2-5.5.
  Every new string through `drT`. A parent outside view reads "a seat above your view".
- **F. Error state** (§5.6): "The chart did not load…" with Try again and code POS-LOAD, never the
  raw server message. Only the `catch` in `posLoad`.
- **G. 065 plans:** a copy holds the same person objects, so a reader's `plan` key goes wherever
  the person is drawn. A non-reader's reply has no `plan` key, so nothing travels. 065's red edge
  "on the planned person's own seat box" lands on the box the person is drawn in.

### 2.3 Thin steps, in order. Each one stays green.

Worktree `.claude/worktrees/072-seats-follow-reporting`, branch `slice/072-seats-follow-reporting`
from `origin/dev` `af0b7cdf`. Python tests in a throwaway container `hrlocal-070s` with its own
site - never `hrlocal-bench`, and not `hrlocal-070`, which belongs to 070-phone. JS checks run in
node, no bench. Every guard is broken once on purpose to prove its test can fail.

| # | Step | Test that proves it |
|---|---|---|
| 1 | **Server:** the join and the `manager` key (§2.1) | NEW `test_reports_to_072.py`: id sent for a manager seated in view; `""` for no Reports To; absent for a Left manager, a manager seated only outside a store reader's branch, an unseated manager for a non-HR reader, and a past `as_at`; sent for an unseated manager to HR; statement count **equal** to before and equal at 20 and 200 people (number recorded); `test_positions_064`, `test_register_194`, `test_register_fill_194` unchanged |
| 2 | **Placement and copies on screen:** `posPlace`, `posNode`/`posGroup*` read it, copies as end boxes, hidden home, vacancy on home, two optional card fields | `check_positions_tree.js` new section: each placement row of §2.2; **the five cases** (split seat; vacancy on home only; hidden empty home; manager in no seat; manager outside scope); Q5; two-seat pick; parent-seat rule; copy has no toggle and no children; copies never grouped; **every person drawn exactly once** with all folds open; tiles unchanged; Branch and Department HTML identical with and without `manager` keys; Organisation card identical without the two fields; a stubbed `plan` key reaches the copy |
| 3 | **Words:** §5.2 box lines, §5.4 view note, dropdown "Reporting lines" (Q4) | Exact strings for each row of §5.2; "a seat above your view" when the parent is hidden; never a hidden seat's title anywhere in the HTML |
| 4 | **Tray:** "Where it shows on this chart" with Show, per-person "Reports to" line, split advice removed (Q3); copy ids open the seat's tray | Tray HTML per case; Show opens the path and focuses the copy; the old split sentences appear nowhere; `check_portal_trays.js` unchanged |
| 5 | **Find, filters, related outline** (§2.2 C, D; design §5.3 hover) | Find a person in a copy outlines the copy; filter on a seat with a copy; hover/focus outlines the seat's other boxes |
| 6 | **Error state** (§2.2 F) | A failed load shows the new words and Try again, not the server's message |
| 7 | **Wall chart (069):** the paper walks the placed model (§2.5) | `check_wall_chart.js` new cases: each person printed once; PRIV-1 key list (three new allowed keys); footer counts; start-from a seat with only copies under it |
| 8 | **Browser checks and size:** connector check (§2.4), `check_wall_chart_browser.js` (`paperAudit` learns copies), A1 re-measure, 1440 and 390 px, light and dark | Real Chromium; results written into the implementation notes |
| 9 | Implementation notes, subtract pass, `check_app_integrity.py`, the whole suite **once** | - |

**Size:** about 20 server lines + 120 test; about 150 JS/CSS lines + 250 check lines. About 2 to 3
working days. Steps 1 and 2 are the slice; 3 to 7 are the words and the paper.

### 2.4 The 064 connector check and `check_positions_tree.js`

**New meaning of "real parent"** in `check_positions_connectors.js` (`realParent`):
- a **home** box: its seat's `reports_to`, as today;
- a **copy**: the drawn seat where its people's manager sits - worked out in the check from
  `POS.rows` and the `manager` keys, **independently of `posPlace`**, so a bug in the rule cannot
  pass its own test;
- new failures: a copy with a fold button or anything under it; a hidden-by-rule home that is
  drawn; a home drawn with no people, no open slot and nothing under it.

**Five new cases**, each a named state in the check: a split seat; a vacancy on the home box only;
a hidden empty home; a manager in no seat (home); a manager outside scope (home, nothing named).

**Where the data comes from:** the check today needs a live site seeded by hand. The five cases go
into `lib/wall_chart_fixture.js` (069's invented DTC-shaped fixture, which gains `manager` keys
shaped from the 24 Oct census: 6 + 4 + 1 + 1 to the CFO, the 64 under HR-EMP-00001's seat). The
connector check gains a fixture mode that loads the page from this checkout with that reply, as
`check_wall_chart_browser.js` already does. One fixture then feeds the jsdom check, the screen
connector check and the paper check. Not CI (Playwright), like today.

**`check_positions_tree.js`:** its first promise, "every seat appears exactly once", stays true for
every existing fixture (no `manager` keys, no copies). The new section states the new invariant
instead: in Reporting lines, each seat has one home box unless hidden by rule, then at least one
copy; **each person is drawn exactly once**.

### 2.5 The 069 wall chart

Prints what the screen draws with every fold open (design §5.7).

| Function | Change |
|---|---|
| `posWallCopy` | Names = home people; copies appended after the real child seats, never grouped; hidden homes skipped. A copy carries `copy: true` and its line ("Same seat as under …" / "Set up under …"); a home carries its "N more shown under …" line |
| `posWallCard` | Dashed border class on a copy; one small grey line. **Vacant** only when the **whole seat** is empty - never on a home whose people are all in copies; such a home prints "None here: all N shown under …" |
| `posWallBelow`, `posWallCount`, `posWallDepth`, `posWallStarts` | Walk the placed model (real child seats not hidden, plus copies), so "below" counts, the levels list, the start list and the footer agree with what prints |
| Footer | "N seats · N people in seats": seat records once, names once |
| PRIV-1 | The allowed-key list gains `copy`, `same`, `more`. No id, no manager id, no plan reaches paper - `check_wall_chart.js`'s sentinel run proves it |
| Size | Re-measured in step 8 on the census-shaped fixture, A3 / A1 / A0, HR copy off and on. 069's quoted sizes are not repeated until then |

**One design line I build as an assumption:** §5.7 says the home prints "N open". 069's paper prints
only "Vacant". I print "N open" on a partly filled home, governed by the same "Show Vacant" tick
`[ASSUMPTION - your no removes one line]`.

### 2.6 Permission-bypass budget

| File | `ignore_permissions` now | After | CEILINGS row |
|---|---|---|---|
| `register.py` | 4 | **4** | unchanged (`test_portal_security_010.py:819`) |
| `portal.js` | - | - | - |

The join runs inside `frappe.get_all`, which already reads without permission checks, as today's
line does. The server still answers only after `may_view()` and within `_scope()`.

---

## 3 · Risks, rollback, hot files

### 3.1 Risks

| # | Risk | What I do about it |
|---|---|---|
| R-1 | A1 falls under 8 pt (bad news 2) | Measure in step 8; Question 5 |
| R-2 | The shared card changes the Organisation page | Two optional fields only; byte-for-byte test |
| R-3 | The join syntax behaves differently on DTC's Frappe 16.35 | Step 1's test fails first; the +1-statement fallback is written down (§1.5) |
| R-4 | A home box looks emptier ("people left?") | The approved "N more shown under …" line; home hidden only on the three conditions |
| R-5 | Phone has no lines, so a copy reads as "under the CFO" only by its words | Accepted in the design (SF3); the words say it |
| R-6 | A manager changed mid-month moves people between boxes the same day | Intended. Release note tells HR |
| R-7 | Deploys do not refresh `sites/assets` (memory, 23 Sep) | Release check: the served `portal.js` contains `posPlace`. A stale file draws today's chart - safe, but not the slice |

### 3.2 Rollback

Nothing is stored: no field, no record, no patch, no setting. Rolling back is reverting the slice's
commits. Old and new halves work with each other in either order (§1.6 Reliability), so a partly
deployed state is still a correct chart.

### 3.3 Hot-file rebase plan

| Other change | Where it meets 072 seats | Plan |
|---|---|---|
| **065 screens** (not started) | `ocNodeCard`, `posNode`, `posOne`, `posSeatSheet` ("Who is in it" rows), the filters' Show options | **072 seats first.** 065's screens are not begun and 065's server needs nothing from 072. 065 then builds its flag and red edge on the placed people, and re-walks its parity rows for copies. If you prefer 065 first, I rebase and re-run step 2's checks |
| **065-option-a** (server, not on dev) | `register.position_table`: their plan block and `out["plans"]` sit next to my block | Keep both; the plan key and the manager key are independent. Re-run 065's byte-for-byte reply test after the merge |
| **066-grooming** (on top of `af0b7cdf`, not pushed) | `portal.js` `ac*`, `gm*`, `pf*`; `panels.css` +85 lines in its own block | No shared function. Rebase on whichever reaches dev first; prove their lines survive with `git show <commit> -- portal.js \| grep '^+'` |
| **070-readable-on-phone** (building) | `gpFetch`/`gpErr` and about 25 load sites; `posLoad` may be one | My change is only `posLoad`'s `catch` body. If they change how errors arrive, I keep their call and my words |
| **ALV-213** | `panels.css` 768/640 blocks | Different blocks |

Rebase on `origin/dev` at the start of every sitting and before handing off. On any conflict in
`portal.js`: keep both sides, run `check_positions_tree.js`, `check_wall_chart.js` and the whole DOM
suite (`run_dom_tests.js`).

### 3.4 What I would NOT build

- Copies in Branch or Department; a "show only this manager's team" filter; lines on the phone.
- Any write to Reports To or to a seat from the chart.
- A setting to turn copies off, a stored "manager seat", a cache.
- A server-computed placement (it would need repeating in the browser for filters and paper).
- A naming read for unseated managers for non-HR readers (Question 3).
- Part B, or any seat split.

---

## 4 · Questions for Surbhi before I build

1. **Build from this paper, with a short spec written by the analyst in parallel?** No spec, `01c`
   or `07` exists. *My recommendation: yes; step 1 now, step 2 after the spec's test list exists.*
2. **No new statement (a join on the existing read), instead of the brief's one extra query?**
   *Recommendation: yes; the +1 read is kept as a written fallback.*
3. **In the tray, name an unseated manager only for HR** (the name is already on her page); others
   read "Reports to a manager who is not on this chart". *Recommendation: yes.*
4. **The three gap rules in §2.2:** a manager seated in the person's parent seat (any of their
   seats) keeps them home; under a filter, copies only of matching seats; Find goes to the copy.
   *Recommendation: yes to all three.*
5. **If "All on A1" falls under 8 pt with copies:** suggest A0 or several sheets in the panel, as
   069 does today? *Recommendation: yes; no new setting.*
6. **Order: 072 seats before 065's screens?** *Recommendation: yes.*

Built as stopgaps unless you say otherwise: the split advice goes in **every** view, not only
Reporting lines (it recommends what you decided against); "N open" prints on a partly filled home.

Not for you, before release: Part A runs on DTC on your word; the release note lists how many
seated people have a manager in no seat; DevOps checks the served `portal.js`.

---

## Subtract pass

Removed on this pass:
- The extra query the brief planned - a join on the read that already runs.
- A server-side "manager seat" key - the browser must place by what is drawn anyway.
- A `no_manager` flag on seated people - `manager: ""` says it.
- A naming read and scope check for unseated managers outside HR.
- A test-only attribute on paper boxes - the checks work out the real parent themselves.
- Seeding a live site for the five connector cases - one invented fixture feeds all three checks.

Kept, and why: `posPlace` as one function (two callers - screen and paper - and they must agree);
the two card fields (copies need a class and a line; the Organisation page passes neither); the
filter and Find rules (without them the slice breaks 064's own checks); the error words (approved).

## Assumptions

- `[ASSUMPTION]` DTC's Frappe 16.35 supports `"link_field.field as alias"` in `get_all` as 16.33.1
  does (`LinkTableField`). Step 1 proves it on the local version; dev proves the rest.
- `[ASSUMPTION]` Nothing ends a seat when a person leaves (no hook found), so a Left manager can
  still be seated. The server checks the manager's status for that reason.
- `[ASSUMPTION]` The screen never asks for a past `as_at` (`posLoad` sends none); the tests do.
- `[ASSUMPTION]` A manager with only a covering seat in view: the copy hangs there (Permanent is
  preferred, not required).
- `[ASSUMPTION]` The census numbers are as of 24 Oct 2026, after which Part A moves 5 seats and 6
  people under the CFO as real seats.
