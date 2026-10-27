---
slice: 072-seats-follow-reporting
artifact: 03-functional-spec (the handoff contract calls this file 02-functional-spec; numbered 03 here to follow this folder's order)
author: hrms-business-analyst
date: 2026-10-25
status: draft - I recommend, you decide
inputs: [01-product-brief.md (24 Oct), 02-design.md (25 Oct) + prototype-v1.html, approved by Surbhi on the designer's recommendations (Q1 "in all" counts people; Q3 the split advice goes, replaced in Reporting lines by "Where it shows on this chart" with Show buttons; Q4 one name, "Reporting lines"; Q5 people whose manager is in the same seat stay on the seat's own box; Q6 the box words), 04-impact-and-strategy.md (approved: no new query; an unseated manager is named in the tray only for HR; the three gap rules; under 8 pt on A1 print on A0 or several sheets instead of shrinking text; build before 065's screens), 064 12-fix-cfo-reports-seats.md (worktree 060-manager-review), 069 03-functional-spec.md, .claude/context handoff-contract, change-process, no-over-engineering, definition-of-ready-done, nfr-budget]
code read: this worktree (integration/dev-2026-10-24, contains origin/dev af0b7cdf) - register.py position_table (lines 257-449), _unseated (457-495), may_view / may_edit (68-86), _may_see_who_is_leaving (184); access.py permitted_employee_filters (252); portal.js posLoad (327), posMatches (538), posGroupSiblings (815), posKeepRows (1329), posMarkFirst / posFocusFirst (1346-1369), posFind / posFindPick / posFindFocus (1376-1443), posRecordNotes (2375-2408), the error line (2585), ocNodeCard (139); parts/positions.html (line 66)
---

# 072 · Seats follow the reporting line - functional spec

## Bad news first

1. **This slice has no `01c` (security and privacy requirements) and no `07` (DevOps inputs).** My
   rules say I stop without them. I wrote the spec anyway because you approved the engineer's plan
   to build from a short spec written alongside (04, Question 1). I wrote the security and privacy
   requirements I need as **proposals** (`pSEC-n`, `pPRIV-n`, §8). **The Ready check fails on those
   two boxes** (§17). The security engineer should adopt, change or renumber them before step 2 of
   the build.
2. **The real DTC chart will draw one very large copy.** The 64 people who report to HR-EMP-00001
   are real (brief Q2, closed). Most of them sit in the shared Back Office seat, so a copy of Back
   Office with about 60 names hangs under the Backoffice Executive seat. On screen that is one box
   with 3 names and "+57 more here". On paper it is 4 columns of 15 names. **That box alone may push
   "All on A1" under 8 pt.** Your rule applies: use A0 or several sheets, never smaller text (§11).
3. **One tray line in the prototype cannot be built as drawn.** The prototype says "Reports to a
   manager outside your view". The server sends nothing for a manager the reader may not see, a
   manager who has left, or (for non-HR readers) a manager in no seat - so the page cannot tell
   these apart. I specify one wording for all of them: **"Reports to a manager who is not on this
   chart"** (the wording you already approved for non-HR readers). This needs your yes (parity row
   P-23, Q1 below).
4. **The engineer's stopgap removes the split advice in every view, not only Reporting lines.** Your
   Q3 answer named Reporting lines. I specify the stopgap (the advice recommends what you decided
   against) and ask you to confirm (Q2 below).

---

## 1 · Cross-module reach

| App | Touched | How |
|---|---|---|
| `hrms` (our org-structure code, `register.py`) | **Yes** | `position_table` reads `Employee.reports_to` and `Employee.status` through a join on the read it already makes. Writes nothing |
| `alvoraa_portal` | **Yes** | Positions screen, its CSS, one word in `parts/positions.html`, the 069 wall chart code, the checks |
| `hrms` (Frappe HR's own code) | No | Reports To is read, never written. Leave approval, attendance corrections and appraisal routing keep reading it as today |
| `erpnext`, `frappe` | No edits | Employee is read only. Frappe's own link-field join is used |
| `alvoraa_goals`, `alvox_compensation` | No | Nothing there reads the chart |

**HRMS domains:** org structure only. Leaves, attendance, payroll, appraisals, goals and pay are not
touched, because Reports To is read and never written.

**Personas:** CXO/Owner (all companies), HR Manager (their companies), branch-limited reader (a store
head or store HR with a Branch permission), Employee (does not open Positions; unchanged).

---

## 2 · Question the ask

- **Symptom or cause?** The cause is named and checked: the chart hangs people by seat parent, while
  approvals, appraisals and team views use the Employee's Reports To (Confirmed fact: brief §1,
  `attendance_correction.py` comment). 88 of 361 seated people disagree. Fixing the chart's rule
  fixes the cause; a data fix (Part B) only fixes today.
- **What decision does it drive?** The owner and HR read who manages whom, spot wrong Reports To
  records (the chart now shows them honestly), and plan seats. The fix for a wrong line is to edit
  Reports To on the Employee record, which the tray says.
- **Could the system act instead?** It could write Reports To from the seat. **Refused** (brief §2):
  a chart edit must never move live approvals or appraisals.

---

## 3 · Gap analysis

| Requirement | What exists today (read in the source) | Verdict | Cost |
|---|---|---|---|
| Draw people under their real manager | Frappe HR's Organizational Chart draws people by Reports To, but has no seats and no vacancies (brief §4). Positions draws seats by `reports_to_position` (`register.py:285`) | **Extend** - placement rule on the Positions page | M |
| Know each seated person's manager | `position_table` reads assignments (`register.py:294-299`) with no manager. `_unseated` reads `reports_to` but sends only a yes/no (`register.py:476, 492`) | **Extend** - two joined columns on the existing assignment read; one optional `manager` key per person | S |
| Name the manager in the tray | Seated managers' names are already in the reply (`people[].name`). Unseated people are in `out["unseated"]` for HR only (`register.py:446-448`) | **Configure-free reuse** - no new data | S |
| Vacancy, job opening, child seats once | Home box already shows `open`, `opening`, children | **Reuse** - stays on the home box only | S |
| Remove split advice | `posRecordNotes` (`portal.js:2393, 2405`) | **Extend** - two sentences removed; two notes hidden in Reporting lines | S |
| Find and filters | `posFind*` finds by seat id; `posKeepRows` keeps matches and their parents | **Extend** - Find goes to the copy; copies only of matching seats | S |
| Wall chart prints copies | 069 paper copy walks seats (`posWall*`) | **Extend** - walk the placed model | M |
| Rename the view | `parts/positions.html:66` "Who reports to whom" | **Configure** - one word change | S |
| Better error words | `portal.js:2585` "Could not load the chart: " + server message | **Extend** - fixed words | S |
| Option C (a chip) / Part B (split seats) | - | **Drop** - you chose the chart rule (04 §2) | - |
| A setting to turn copies off; a cache; a stored "manager seat" | - | **Drop** - nothing needs them | - |

**Rung:** 4, new code in our own app. Already-there fails (no seats, no vacancies). Configuration and
customisation cannot draw a seat in two places. The data fix goes stale. No new DocType, field,
setting, hook, endpoint, cache, job, patch or app.

**Single source of truth:** who manages whom = `Employee.reports_to`. Where a seat sits and how many
slots it has = `Alvoraa Position`. The chart reads both every time; nothing is copied, so nothing
needs keeping in step.

---

## 4 · Process flow

1. HR (or the owner) opens Positions. The page asks `position_table` for today.
2. The server returns the seats and people in the reader's scope, each person with a `manager` key
   when allowed (§6).
   - *Unhappy:* the call fails → error state (AC-63). Nothing changes.
3. The reader is in **Reporting lines** (the default). For each person, the page finds the seat their
   manager sits in, among the drawn seats.
   - Manager in the seat's parent seat, in the same seat, nowhere, or not sent → person stays home.
   - Manager in another drawn seat → person goes into a **copy** under that seat.
4. Homes with nothing left (no people, no open slot, nothing under them) are not drawn.
5. The reader opens a box → the seat tray. In Reporting lines it lists where the seat shows, with
   Show buttons, and each person's manager.
6. HR sees a wrong line → opens the Employee record and changes Reports To (outside this slice).
   Reopening the chart draws the person under the new manager. No seat edit.
7. Branch or Department view → one box per seat, as today, no copies.
8. Download wall chart → the paper prints what Reporting lines draws with every fold open.
   - *Unhappy:* names under 8 pt → 069's existing warning offers a larger paper or several sheets.

---

## 5 · Data model

**Nothing new is stored.** No DocType, field, setting, patch or index.

| Object | Change |
|---|---|
| `Alvoraa Position`, `Alvoraa Position Assignment`, `Employee` | None. Read only |
| `position_table` reply | Each person object may gain one key, `manager` (§6). Nothing else changes |
| Page model (browser only, not stored) | A copy is a box made from a seat row and a subset of its people. It carries `copy: true` and the manager seat it hangs under |
| 069 paper copy (browser only) | The allowed-key list gains `copy`, `same`, `more` (the dashed-border flag and the two quiet lines). Nothing else |

**Why no existing field carries the manager:** `people[]` entries carry assignment data only. The
`_unseated` rows carry `no_manager` as yes/no on purpose (`register.py:464`). The new key is the
smallest addition, and it is sent fail-closed.

**States and transitions:** none. There is no workflow, no status and nothing to submit.

---

## 6 · The `manager` key rules (server)

One key per person in `rows[].people[]`. Worked out on every call; never stored.

| Case | `manager` | Confirmed / assumption |
|---|---|---|
| `as_at` is not today (a past or future date) | **absent** on every person | Reports To has no history, so a past date draws as before |
| The person's Reports To is empty | `""` | |
| Manager is Active **and** holds a current assignment in a seat that is in this reply | the manager's employee id, e.g. `"HR-EMP-00412"` | "Current" = the same rule today's read uses: `from_date <= as_at` and no `to_date` or `to_date >= as_at` |
| Manager is Active, holds no current seat, and is in this reply's `unseated` list (HR readers only) | the manager's employee id | `unseated` is sent only when `permitted_employee_filters()` allows (`register.py:446`) |
| Manager's status is Left, Inactive or Suspended | **absent** | `[ASSUMPTION]` nothing ends a seat when someone leaves, so a Left manager can still be "seated" - hence the status check |
| Manager is seated only in seats outside this reader's scope | **absent** | |
| Manager holds no seat and the reader gets no `unseated` list (non-HR) | **absent** | |
| Manager holds no seat and is outside an HR reader's scope | **absent** | Not in `unseated`, so not in the reply |

**Rule in one line:** `manager` holds an id only if that id is already somewhere in this reply.
Otherwise it is `""` (no manager on record) or absent.

**Constraints on how (from 04, approved):**
- No new database statement. The two columns come from the existing assignment read through a join
  on the Employee link. Statements per page open stay at 6 (HR Manager) and 7 (System Manager).
- The scope stays in the database (nfr-budget §2). No list of ids is read and sent back for this key.
- `ignore_permissions` uses in `register.py` stay at 4.
- *Fallback only if the join fails on Frappe 16.35:* one extra read of Employee by the holders' ids
  (+1 statement). The engineer reports it if used.

---

## 7 · The placement rules (browser, Reporting lines only)

For each person P in seat S, among the seats **drawn** right now:

| # | Where P's manager sits | P is drawn in |
|---|---|---|
| R1 | In S's parent seat - in **any** of the manager's drawn seats | home (S's own box) |
| R2 | In S itself (a head and team in one seat) - Q5 | home |
| R3 | In one other drawn seat M | a copy of S under M |
| R4 | In two or more other drawn seats (and none is S's parent or S) | a copy under one of them: Permanent assignment first, then the highest weight, then seat title A-Z, then seat id A-Z |
| R5 | `manager` is `""`, absent, or the manager is in no drawn seat | home |

**Copies**
- C1. A copy is an end box: **no fold button and no boxes under it, ever.** So no loop is possible.
- C2. One copy per (seat, manager seat) pair. It lists only the people placed there.
- C3. Under a manager seat, its real child seats come first, then its copies, each in the order the
  seat list has them.
- C4. A copy is never grouped with another box. A seat that has a copy of itself elsewhere, or a copy
  hanging under it, is never grouped either (`posGroupSiblings` would otherwise list all its people
  again).
- C5. A copy never shows the open-slot tag, the job opening or "Vacant".

**Home**
- H1. The home box keeps the seat count, the open slots, the job opening and the child seats.
- H2. **The home box is not drawn only when all three are true:** no people at home, no open slot,
  nothing under it. A copy hanging under the home counts as "something under it".
- H3. A vacancy shows **once**, on the home box.

**Counting**
- N1. **Each person is drawn exactly once** with every fold open. (A person with two assignments,
  in two seats, appears once per assignment, as today.)
- N2. Tiles (Seats, People in seats, To fill, In no seat) count seat records and people, never boxes.
  Copies change no tile.
- N3. "N in all" = people in the seat (Q1), not slots.

**Lines (connector rule)**
- L1. No line may suggest a box reports to anything but its real parent. For a home, the real parent
  is its parent seat. For a copy, it is the seat its people's manager sits in (worked out by the
  check on its own, not by calling the placement code).

**Gap rules (approved in 04)**
- G1. **Filters:** with any filter on, copies are drawn only of **matching** seats, and only under a
  manager seat that is drawn (a match or above one). A faded seat above a match keeps all its people
  at home.
- G2. **Find:** a person drawn in a copy is found in the copy. A seat whose home is not drawn is found
  at its first copy in reading order.
- G3. R1 above: a manager who holds two seats, one of them S's parent, keeps P at home.

**Other views:** Branch and Department draw one box per seat with everyone in it, exactly as today.

---

## 8 · Permission and visibility matrix

No new role, permission, endpoint or write. Who may open Positions is unchanged: Frappe Read on
`Alvoraa Position` (`may_view`, `register.py:68`).

| Reader | Opens Positions | Sees copies | `manager` id sent for | Unseated manager's name in tray | Edits a seat from a copy tray |
|---|---|---|---|---|---|
| System Manager / CXO with System Manager | Yes | Under every seat in their companies | Seated managers in their companies; unseated managers (gets `unseated`) | Yes | Yes (Write) |
| HR Manager / HR User, no Branch permission | Yes | Under every seat in their companies | Same, within their companies | Yes | If Write on Alvoraa Position |
| HR with a Branch permission (store HR) | Yes | Only under seats in their branches | Seated managers in their branches; unseated managers in their branches | Yes, within their branches | If Write |
| Owner / CXO with Positions read but no HR role (DTC owners) | Yes | Under every seat they can see | Seated managers in seats they can see only | **No** - "a manager who is not on this chart" | If Write |
| Branch-limited non-HR reader (store head) | If given Read | Only under seats in their branches | Seated managers in their branches only | No | If Write |
| Employee / line manager without Read | **No** - refused as today | - | - | - | - |

**Negative cases - who must NOT see what:**
- A branch-limited reader must not see, in any box, quiet line, tray line, Find result or printed
  sheet, the title of a seat outside their branches or the name of a manager seated only there.
  They read "a seat above your view" or "a manager who is not on this chart".
- A non-HR reader must not receive the name or id of a manager who holds no seat.
- Nobody receives the id of a Left, Inactive or Suspended manager through this key.
- Nobody gains a leaving date, a replacement plan (065) or a job opening id through a copy. Those
  keys ride on the same person and seat objects and keep today's rules.
- An employee without Read gets nothing: the call is refused before any of this runs.

**Proposed security and privacy requirements (for `01c`; the security engineer owns them):**

| ID | Requirement | AC |
|---|---|---|
| pSEC-1 | No new whitelisted call and no new write. `ignore_permissions` count in `register.py` stays 4 (CEILINGS row unchanged) | AC-9 |
| pSEC-2 | `manager` is fail-closed: an id only when that id is already in the reply | AC-1 - AC-7 |
| pPRIV-1 | No seat title or manager outside the reader's scope appears in HTML, tray, Find or paper | AC-49, AC-50 |
| pPRIV-2 | The paper's allowed-key list gains only `copy`, `same`, `more`; no id, manager id or plan reaches paper | AC-58 |
| pPRIV-3 | Leaving dates and 065 plans reach a copy only for readers who get them today | AC-51 |

---

## 9 · Epic and user stories

**Epic:** the Positions chart draws people under the seat of their real manager, while every seat,
vacancy and child seat still shows once.

| ID | Story | Pts | Prototype state | Requirements | ACs |
|---|---|---|---|---|---|
| US-1 | As an **HR Manager**, I want each person drawn under the seat their Reports To manager sits in, so that the chart agrees with approvals and appraisals | 5 | "CFO opened", "Back Office opened", "Deep store chain opened" | Brief §1-2 | AC-11 - AC-21, AC-65 |
| US-2 | As a **CXO / Owner**, I want each copy to say it is the same seat and how many are in it in all, so that I do not think people were counted twice | 3 | "CFO opened" | Q1, Q4, Q6 | AC-27 - AC-34 |
| US-3 | As an **HR Manager**, I want open slots, the job opening and child seats to stay on the seat's own box, and that box hidden only when it has nothing, so that a vacancy shows once and no box says "Nobody" about a full seat | 3 | "Tray: MIS", "Tray: Store Auditor" | Brief §2 | AC-22 - AC-26 |
| US-4 | As an **HR Manager**, I want the seat tray to list where the seat shows, jump there, and say whom each person reports to, so that I know where to fix a wrong line | 5 | "Tray: Back Office (3 places)", "Tray: MIS", "Tray: Store Auditor" | Q3 | AC-35 - AC-42 |
| US-5 | As an **HR Manager** on a laptop, I want the other boxes of a seat to light up when I point at one, so that I can see a seat drawn in two places | 1 | "Hover on a copy" | Design §5.3 | AC-43 |
| US-6 | As an **HR Manager**, I want Find and the filters to treat copies correctly, so that Find lands where the person is drawn and a filter never draws unrelated boxes | 3 | not drawn (04 gap rules) | 04 Q4 | AC-44 - AC-48 |
| US-7 | As a **store head with a Branch permission**, I must not see any seat or manager outside my branches through a copy or the tray, so that the chart never shows me more than my scope | 3 | Person: "Store reader (Noida)" | pPRIV-1 | AC-49 |
| US-8 | As an **employee in no seat who manages others**, I must not be named to a non-HR reader, so that the "in no seat" list stays HR-only | 1 | "Tray: Packing" person (HR view) | 04 Q3, pSEC-2 | AC-50, AC-51 |
| US-9 | As any **reader**, I want the Branch and Department views and the Organisation page to stay exactly as they are, so that nothing I rely on moves | 2 | "Arrange by Branch" | Brief §2 | AC-52 - AC-54 |
| US-10 | As an **HR Manager**, I want the wall chart to print the copies, each person once, so that the paper matches the screen | 3 | "Wall chart: All on A1" | Brief Q5 | AC-55 - AC-60 |
| US-11 | As an **HR Manager**, I want to be told the true name size with copies and offered A0 or several sheets when A1 is too small, so that I never print an unreadable sheet | 2 | "Wall chart: All on A1" | 04 Q5 | AC-61, AC-62 |
| US-12 | As an **HR Manager**, I want a plain error that does not show the server's message, so that I know nothing broke in my data | 1 | "Error" | Design §5.6 | AC-63 |
| US-13 | As an **HR Manager**, I want the chart to read Reports To fresh every time it opens, so that a change I make on the Employee record shows next time without a seat edit | 3 | all | pSEC-2 | AC-1 - AC-10, AC-67 |
| US-14 | As a **CXO on a phone**, I want copies to read correctly without lines, so that I can still tell where a box belongs | 1 | Device "Phone 390" | Design §5.5 | AC-64 |
| US-15 | As a **screen-reader user**, I want the copy words spoken and the tray reachable by keyboard, so that the dashed border is never the only signal | 1 | all | Design §6 | AC-66 |

**INVEST check:** US-1 and US-4 are the largest (5). US-1 cannot split further without leaving copies
half-drawn. US-13 is server-only and can be built first (04 step 1). US-9 is a guard story ("nothing
else moves"); kept because a shared card (`ocNodeCard`) changes. No 8s.

**YouTrack import (do not create; your call):** summary = the story text up to "so that"; description
= the full story + its ACs; persona, points, ACs and requirements as in the table above.

---

## 10 · Acceptance criteria

All screen ACs run in **Reporting lines** unless they say otherwise. The fixture is 069's
`lib/wall_chart_fixture.js` with `manager` keys added, shaped from the 24 Oct census (CFO seat with
6 + 4 + 1 + 1 people from shared seats; about 60 Back Office people reporting to HR-EMP-00001's seat;
one manager in no seat; one Left manager; one loop pair). Names are invented.

### US-13 · The `manager` key (server, `test_reports_to_072.py`)

- **AC-1** Given P reports to M, M is Active and holds a current seat in the reply, when HR calls
  `position_table()`, then P's entry has `manager` = M's employee id.
- **AC-2** Given P's Reports To is empty, then P's entry has `manager` = `""`.
- **AC-3** Given M has status Left (and still holds an assignment), then P's entry has no `manager`
  key. Same for Inactive and for Suspended.
- **AC-4** Given a store reader limited to Noida, and M is seated only in a Delhi seat, when the store
  reader calls, then P (a Noida seat) has no `manager` key, and the string M's id appears nowhere in
  the reply.
- **AC-5** Given M is Active and holds no seat, and the reader is HR whose scope includes M, then P's
  `manager` = M's id, and M's id is in `unseated`.
- **AC-6** Given the same M, and the reader is a non-HR Owner with Positions read, then P has no
  `manager` key, the reply has no `unseated` key, and M's id appears nowhere in the reply.
- **AC-6b** Given M holds no seat and is outside a store HR's branches, then P has no `manager` key.
- **AC-7** Given `as_at` is yesterday (or tomorrow), then no person has a `manager` key, and every
  other key equals today's reply for that date.
- **AC-8** The number of database statements per call is **equal** before and after this slice, and
  equal at 20 and at 200 seated people. The numbers are recorded in the test report.
- **AC-9** `test_positions_064.py`, `test_register_194.py`, `test_register_fill_194.py` pass
  unchanged; the `ignore_permissions` count for `register.py` in `test_portal_security_010.py`
  CEILINGS stays 4.
- **AC-10** Given M's only assignment ended yesterday (`to_date` < today) and M is not in `unseated`
  for this reader, then P has no `manager` key. Given M holds a current **covering** assignment in a
  seat in the reply, then P's `manager` = M's id.

### US-1 · Placement and copies

- **AC-11** (R1) Given seat S's parent is seat A and P's manager sits in A, then P is listed in S's
  home box, and no copy of S exists.
- **AC-12** (R3) Given Office Executive (parent Owner) holds 6 people, 2 reporting to the Owner and 4
  to the CFO, then the Owner's seat has the Office Executive home box with 2 names, and the CFO's seat
  has one dashed copy of Office Executive with exactly those 4 names.
- **AC-13** (R2, Q5) Given Floor Supervisor Noida holds 2 people and one reports to the other, then
  both are in the home box and no copy of Floor Supervisor Noida exists.
- **AC-14** (R5) Given P's `manager` is `""`, absent, or the id of a manager in `unseated`, then P is
  in S's home box.
- **AC-15** (R1, G3) Given P's manager holds two drawn seats, one of them S's parent, then P is at
  home.
- **AC-16** (R4) Given P's manager holds a Permanent seat X (weight 60) and a covering seat Y (weight
  100), both drawn and neither S's parent, then P's copy hangs under X. Given two Permanent seats of
  weight 50 each titled "Area Manager North" and "Area Manager East", the copy hangs under "Area
  Manager East".
- **AC-17** Given RSO Noida (parent Senior RSO Noida) holds 23 people reporting to Senior RSO, 6 to
  Floor Supervisor Noida and 1 to Store Manager Delhi, then there is one home box (23) and two copies
  (6 under Floor Supervisor Noida, 1 under Store Manager Delhi).
- **AC-18** (C1, C3) No copy has a fold button (`.oc-toggle`) or any box nested under it. Under the
  CFO's seat, the 5 real child seats come before the copies.
- **AC-19** (N1) With every fold open, the number of drawn name entries equals the number of
  assignment entries in the reply, and no assignment entry is drawn twice.
- **AC-20** (C4) Given two identical sibling seats with no children, where one has a copy of itself
  elsewhere, then they are drawn as two separate boxes, not one grouped box. No copy is ever inside a
  grouped box.
- **AC-21** Given P1 (seat X) reports to P2 (seat Y) and P2 reports to P1 [Reports To loop - only if
  the data holds one], then the page draws: a copy of X under Y and a copy of Y under X, each an end
  box. The page finishes drawing and no box repeats.
- **AC-65** (L1) The connector check passes on the fixture, on screen (1440 and 390 px) and on paper:
  0 false links. It fails (proved by breaking it once on purpose) when a copy has a fold button or a
  box under it, when a home hidden by H2 is drawn, and when a home with no people, no open slot and
  nothing under it is drawn.
- **AC-67** Given P's Reports To changes from the Owner to the CFO on the Employee record, when HR
  reopens Positions, then P is in the copy under the CFO's seat, and no seat or assignment record was
  changed (their `modified` values are unchanged).

### US-3 · The home box

- **AC-22** (C5, H1, H3) Given Back Office has 36 slots and 35 people, 6 of them in a copy under the
  CFO, then the "open" tag appears on the home box only, and no copy shows an open tag, "Vacant" or a
  job-opening link. A seat with an open Job Opening shows the opening on its home box only.
- **AC-23** (H2) Given Store Auditor (parent Owner, 1 slot) holds 1 person reporting to Retail Head,
  and has no child seats, then its home box is not drawn, and a copy hangs under Retail Head.
- **AC-24** Given MIS (2 slots) holds 1 person, in a copy under the CFO, then the home box is drawn
  with the open tag and reads "None here: all 1 shown under Chief Financial Officer".
- **AC-25** Given a seat with no people at all (Legal Counsel), then it reads "Nobody in this seat",
  as today.
- **AC-26** Given Back Office's home has 10 child seats, then all 10 hang under the home and none
  under any copy. Given a home with no people and no open slot, but a copy of another seat hanging
  under it, then the home is drawn.

### US-2 · Box words and view name

- **AC-27** A copy box reads: title; second line "{branch} · {n} person" or "{branch} · {n} people";
  the names (the same number of names any box shows today), then "+{k} more here" if more; then the
  quiet line "Same seat as under {parent seat title} · {all} in all", where {all} = people in the
  seat (Q1). Example: "Head Office · 4 people" … "Same seat as under Owner · 6 in all".
- **AC-28** A copy whose home is not drawn reads "Set up under {parent seat title}", plus " · {all} in
  all" only when the seat has more people than this copy. Example: "Set up under Owner".
- **AC-29** A home with people at home and one copy reads "{k} more shown under {manager seat title}";
  with copies under several manager seats, "{k} more shown under {c} other managers". Example: "4 more
  shown under Chief Financial Officer"; "13 more shown under 2 other managers".
- **AC-30** On a home or copy of a shared seat, overflow reads "+{k} more here"; on a seat that is not
  shared, "+{k} more in this seat" (as today).
- **AC-31** When the seat's parent is outside the reader's scope, every place that would name it
  reads "a seat above your view"; a top seat reads "the top of the chart". The parent's title never
  appears.
- **AC-32** A copy box has the class that draws a dashed border, and its quiet line text is inside the
  box's button (part of its accessible name).
- **AC-33** The Arrange by option reads "Reporting lines" (Q4). The note above the chart reads,
  exactly: in Reporting lines, "Each person is shown under the seat of their manager, as set in
  Reports To on their employee record. A seat shared by people with different managers shows once
  under each manager. Open slots and the seats under it stay on the seat's own box."; in Branch or
  Department, "One box per seat, with everyone in it. To see people under their managers, choose
  Arrange by: Reporting lines." The wall chart's heading also says "Reporting lines".
- **AC-34** (N2) The four tiles show the same numbers with and without `manager` keys in the reply.

### US-4 · The seat tray

- **AC-35** Given a seat with at least one copy, when the reader opens any of its boxes in Reporting
  lines, then a section headed "Where it shows on this chart" lists: first the home (if drawn) as
  "Under {parent}: its own box, {n} people[, {o} open][, {s} seats under it]", then each copy as
  "Under {manager seat title}: {n} people", each with a **Show** button; the line for the box that was
  opened carries "You opened this one".
- **AC-36** If the home is not drawn, the section also reads "Its own box under {parent} is not drawn:
  nobody there reports along that line, no slot is open and no seat hangs under it."
- **AC-37** The section ends with: "People are placed by Reports To on their employee record. To move
  someone, change their Reports To; the chart follows the next time it opens. The seat itself stays
  under {parent}."
- **AC-38** Pressing Show closes the tray, opens every fold down to that box, scrolls it into view and
  puts keyboard focus on it.
- **AC-39** Under "Who is in it", each person has one grey line, exactly one of: "Reports to {name}
  ({seat title})" (manager seated in a drawn seat; the seat is the one R1-R4 picks); "Reports to
  {name}, also in this seat" (R2); "Reports to {name}, who is in no seat" (manager in `unseated`, HR
  only); "Reports to a manager who is not on this chart" (`manager` absent); "No manager on their
  record" (`manager` is `""`).
- **AC-40** The sentences "A seat shared with another manager's people needs splitting first." and
  "Give the head a seat of their own, then move each group under its own manager." appear in no tray
  in any view [Q2]. In Reporting lines, the two records-check notes ("{n} people report to this
  person on their employee records…" and "This seat holds the people of {n} managers") are not shown.
  In Branch and Department they show as today, minus those two sentences.
- **AC-41** A seat with no copies shows no "Where it shows" section. In Branch and Department no tray
  shows the section or the per-person line.
- **AC-42** Opening a copy opens the same seat's tray (title, facts "{filled} of {slots} filled",
  "to fill"). "Change this seat" (shown to editors only) edits the seat record, exactly as from the
  home box.

### US-5 · Related outline

- **AC-43** On a desktop, when the pointer rests on, or keyboard focus lands on, any box of a shared
  seat, then every other box of that seat on screen gets a dashed outline; when it leaves, the outline
  goes. No box moves. Nothing happens on touch.

### US-6 · Find and filters

- **AC-44** (G2) Given P is drawn in a copy under the CFO, when HR finds "P" and picks it, then the
  path to the CFO's seat opens, the copy is outlined and has keyboard focus.
- **AC-45** Finding a person at home outlines the home, as today. Finding the seat Store Auditor (home
  not drawn) outlines its first copy in reading order.
- **AC-46** (G1) Given the filter Department = Accounts, then copies are drawn only of seats in
  Accounts, and only under manager seats that are drawn. A faded seat (not a match, kept only because
  a match is below it) shows all its people in its home box.
- **AC-47** With any filter on, every drawn box is a match or above a match (064's filter rule).
- **AC-48** The "{n} matching" line counts seat records, not boxes; the first outlined box is the first
  box (home or copy) of a matching seat in reading order.

### US-7 and US-8 · Must not

- **AC-49** Given the Noida store reader opens Positions, then no Head Office or Delhi seat title and
  no Delhi manager's name appears anywhere in the page HTML, any tray, any Find result or the paper;
  the RSO Noida person whose manager sits in Store Manager Delhi is in the home box and their tray line
  reads "Reports to a manager who is not on this chart".
- **AC-50** Given a Packing person reports to Neeraj Sood, who holds no seat: the HR reader's tray
  reads "Reports to Neeraj Sood, who is in no seat"; the non-HR Owner's tray reads "Reports to a
  manager who is not on this chart", and "Neeraj Sood" appears nowhere in the Owner's page HTML.
- **AC-51** For a reader whose reply has no `leaving` date, no copy shows one. For a reader without
  065 plans, no copy shows a plan mark. For a reader with them, the mark shows on the box where the
  person is drawn (home or copy) and nowhere else.

### US-9 · Nothing else moves

- **AC-52** Branch and Department views produce byte-identical HTML for the same reply with and
  without `manager` keys.
- **AC-53** The Organisation page (`ocPaint`) produces byte-identical HTML before and after this slice.
- **AC-54** A reply with no `manager` keys draws Reporting lines exactly as today, except the words of
  AC-33 and AC-63.

### US-10 · Wall chart (069)

- **AC-55** The paper prints what Reporting lines draws with every fold open: each copy with a dashed
  border and its quiet line; each home with its "{k} more shown under …" line. The number of printed
  names equals the number of assignment entries (each person once).
- **AC-56** The footer reads "{s} seats · {p} people in seats", counting seat records and people once
  (example: "43 seats · 187 people in seats" for 50 boxes).
- **AC-57** "Vacant" prints only when the whole seat has nobody. A home whose people are all in
  copies prints "None here: all {n} under {…}". A partly filled home prints "{o} open". Both words
  follow 069's "Show Vacant" tick [ASSUMPTION - 04 §2.5].
- **AC-58** (pPRIV-2) 069's sentinel run passes with the allowed-key list plus `copy`, `same`,
  `more` only: no employee id, `manager` value, plan or opening id reaches the paper, HR copy off and
  on.
- **AC-59** "{n} seats · {p} people below" on the last drawn level counts seat records and people
  under the box once each, over real child seats and copies, and never counts the box's own seat.
- **AC-60** The Start-from list and the Levels list walk the same placed model; starting from a seat
  whose only boxes below are copies prints those copies.

### US-11 · Size

- **AC-61** The engineer prints the census-shaped fixture (91 seats, the copies of AC-12/AC-17 shape,
  the ~60-name Back Office copy), All, one sheet, Show Vacant on, HR copy off and on, and records the
  name size on A3 (2 levels), A1 (All) and A0 (All) in the test report. 069's sizes are not quoted again
  until then.
- **AC-62** If All on A1 is under 8 pt: the page does not shrink names below 8 pt and no new setting
  is added; 069's existing warning (069 AC-33) offers the first paper that reaches 8 pt (A0) and "Use
  {n} sheets". 069 AC-32's "stop" does not block this slice (your rule, 04 Q5). The numbers go to
  Surbhi.

### US-12 · Error

- **AC-63** Given the `position_table` call fails, then the chart area reads "The chart did not load.
  Nothing has changed in your seats or your people. Check your connection, then try again. If it
  keeps happening, tell your administrator: code POS-LOAD." with a **Try again** button, inside an
  element with `role="alert"`; the server's own message text does not appear. Try again calls the
  load again.

### US-14 · Phone

- **AC-64** At 390 px: boxes stack as today; under a manager seat, copies follow its real child seats;
  every copy carries its quiet line; no sideways scroll; no text under 12 px; Show buttons at least 44
  px tall; the tray opens as a bottom sheet; no hover outline.

### US-15 · Accessibility

- **AC-66** The quiet-line icon is `aria-hidden`; each Show button's accessible name is "Show it on the
  chart: {line text}"; opening the tray moves focus to its heading; Escape closes it and focus returns
  to the box that opened it. Light and dark themes both pass the 064 contrast checks.

---

## 11 · Edge cases

| Case | What happens | AC |
|---|---|---|
| **The 64 under HR-EMP-00001 (real)** | Most sit in Back Office, above HR-EMP-00001's own seat. A copy of Back Office with about 60 names hangs under the Backoffice Executive seat, which sits under Back Office's home. Legal and loop-free: the copy has no children. Back Office's home shrinks and reads "{k} more shown under 2 other managers" | AC-12, AC-29, AC-65 |
| A seat with 60 names in one copy | Screen: 3 names (today's limit) + "+57 more here". Tray: all 60 listed with their Reports-to line; the tray scrolls. Paper: 069 layout, up to 4 columns | AC-27, AC-39, AC-61 |
| Reports To loop (A→B→A) | Each person goes into a copy under the other's seat. Copies have no children, so drawing ends. `[UNVERIFIED - recall]` ERPNext Employee is a tree on `reports_to` and refuses a loop on save; the test proves the page survives either way | AC-21 |
| Seat parent loop | Already refused by the seat code (064 census: 0 loops). Not changed | - |
| Deep chains | A copy adds one level below its manager seat, never more. The existing depth cap (`POS_MAX_DEPTH` 40) is unchanged | AC-18 |
| Manager in two seats | R1/R4 | AC-15, AC-16 |
| Manager covering only | Copy hangs under the covering seat (Permanent is preferred, not required) `[ASSUMPTION - 04]` | AC-10, AC-16 |
| Manager left / re-hired under a new id | Left: absent → home. Re-hired: Reports To must point at the new id; until HR changes it, people stay home | AC-3 |
| Manager in no seat | Home; HR sees the name in the tray, others do not | AC-14, AC-50 |
| Manager outside the reader's scope | Home; nothing named | AC-4, AC-49 |
| Same seat (head and team in one seat) | Home (Q5) | AC-13 |
| Person in two seats | Placed once per assignment, as today | AC-19 |
| Mid-day Reports To change | Shown at the next page open. No cache | AC-67 |
| Back-dated Reports To change / past date | Reports To has no history: a past `as_at` draws without copies. The screen never asks for a past date `[ASSUMPTION - 04]` | AC-7 |
| Multi-company: Reports To crosses companies (a group CFO) | If the manager's seat is in the reply, the copy hangs under it, even in another company. That is the true line `[ASSUMPTION]` | AC-12 |
| Filters | G1 | AC-46, AC-47 |
| Find | G2 | AC-44, AC-45 |
| Phone without lines | Words carry it; copies follow real child seats | AC-64 |
| Identical seats grouped | Never with a copy or a split seat | AC-20 |
| Nobody's manager in a seat | Chart looks exactly as today; no message | AC-54 |
| Old browser + new server / new browser + old server | Old page ignores the key; new page draws no copies | AC-54 |
| Concurrent edits, cancelled or amended documents, bulk import, time zones | Nothing here writes or submits. "Today" is the server's date, as today | - |

---

## 12 · Non-functional requirements for this slice

| Item | Number | How checked |
|---|---|---|
| Database statements per page open | **Unchanged**: 6 (HR Manager), 7 (System Manager); flat at 20 and 200 people | AC-8 (counts reproduce exactly) |
| Reply size | + about 26 bytes per seated person: about +9 KB at DTC (361), +26 KB at 1,000 | Measured bytes in the test report |
| Server call p95 | Within the 500 ms whitelisted-call budget, as today | Not re-timed (the join adds one primary-key lookup per row) |
| Browser placement | One pass over people and seats, per paint | Reported, not gated (wall-clock on this machine is not reliable, change-process rule 5) |
| Page p95 | Core HR view ≤ 1.5 s, as today | Unchanged |
| Background jobs, queues, caches | None | - |
| Volume | DTC: 91 seats, 361 seated, about 10-25 copies `[needs validation - AC-61]`. 10x: ~1,000 seated | - |
| Retention | Nothing stored | - |
| Sensitive data | Names and reporting lines (personal, internal). No statutory or sensitive class | §15 |

---

## 13 · Migration, backfill, rollback

**Nothing.** No field, record, patch or setting. Rollback = revert the slice's commits. Old and new
halves work in either order (AC-54).

**CFO script, Part A - separate, not part of this slice.** `12-fix-cfo-reports-seats.md` (064) Part A
re-points 5 seats (6 people) from the Owner's seat to the CFO's seat on production DTC. It runs only
on your word, as its own step, with its own dry run and verify (`6 of 18` expected after Part A
only). **Part B must not run.** With or without Part A, 072 draws the same people under the CFO:
without it they show as copies ("Set up under Owner"); with it, as real seats. Part A matters for
where those seats' **future vacancies** appear. No AC in this spec depends on it.

**Release notes (DevOps, not this spec):** the count of seated people whose manager holds no seat;
check the served `portal.js` contains the new placement code (deploys do not refresh `sites/assets`).

---

## 14 · Notifications, localisation, audit

- **Notifications:** none. No email, no bell, no toast.
- **Localisation:** every new string goes through `drT` (the portal's translation call), including the
  numbers inside them as `{0}` placeholders. Hindi copy is not in the design; strings fall back to
  English until translated. No dates or currency are added.
- **Audit:** nothing is written, so there is nothing new to audit. A wrong line is fixed on the
  Employee record, which Frappe's version history already records.

---

## 15 · Compliance-impact sub-analysis

I am not a lawyer. Nothing below is a legal ruling.

**1 · Data touched**

| Field / object | Class | Purpose | Lawful basis (as recorded) | New collection? |
|---|---|---|---|---|
| `Employee.reports_to` (as `manager` id) | internal (personal) | Draw the reporting line | Employment (as for approvals today) `[as recorded by the tenant - not checked]` | No - read only |
| `Employee.status` (used, not sent) | internal | Fail-closed check | Same | No |
| Names on boxes and paper | internal (personal) | Already shown | Same | No |

**2 · Obligations engaged**

| Obligation | Source | What this slice must do | Feature |
|---|---|---|---|
| Purpose limitation / minimisation (DPDP) | security-compliance-baseline | Send the manager id only when it is already in the reply | §6, pSEC-2 |
| Role-based scoping | baseline; 030 scope rules | No seat or manager outside scope named | pPRIV-1 |
| Staff told before names go on a wall | 069 PRIV-3 | Unchanged; copies print names already printed | 069 |

**3 · Visibility delta**

- New: a non-HR reader learns, for a seated person, whether they have a manager on record ("No manager
  on their record") and, if the manager is seated in view, who. Both were already visible on the
  Organisation page.
- New for HR: the unseated manager's name next to a seated person. Already on HR's "in no seat" list.
- **Nobody** gains a seat, manager, leaving date, plan or opening outside their scope.

**4 · Decision automation:** none. The chart decides nothing about a person.

**5 · Retention and deletion:** nothing changes. Nothing is stored.

**6 · Open compliance questions:** none for counsel.

**7 · AI features:** none. No prohibited capability.

---

## 16 · Prototype parity table

Every state and feature in `prototype-v1.html`. "Same" = build exactly as drawn. A difference needs
Surbhi's yes; rows marked **yes given** cite where.

| # | Prototype state / feature | Story | Given / When / Then (short) | Difference |
|---|---|---|---|---|
| P-1 | Chart as it opens: top seats open, view note, tiles | US-2, US-9 | Given HR opens Positions, then roots are open, the note of AC-33 shows, tiles as AC-34 | Note's last words "Reporting lines" (Q4, **yes given**) |
| P-2 | "CFO opened": 5 real seats, then copies of Office Executive (4), Back Office (6), MIS (1), Accountant (1) | US-1, US-2 | AC-12, AC-18, AC-27 | Same |
| P-3 | "Back Office opened": copy of Back Office (7) under Backoffice Executive, a seat below it | US-1 | Given Back Office is opened, then Backoffice Executive holds a dashed Back Office copy; AC-65 passes | Same (at DTC about 60 names) |
| P-4 | "Deep store chain": RSO Noida home 23, copies 6 and 1; Floor Supervisor head-and-team at home | US-1 | AC-13, AC-17 | Same |
| P-5 | "Hover on a copy": other boxes outlined | US-5 | AC-43 | Same |
| P-6 | "Tray: Back Office (3 places)": list, Show, "You opened this one", note, per-person lines | US-4 | AC-35, AC-37, AC-38, AC-39 | Same, except P-22, P-23 |
| P-7 | "Tray: MIS": home with nobody keeps the vacancy, "None here: all 1 shown under …" | US-3, US-4 | AC-24, AC-35 | Same |
| P-8 | "Tray: Store Auditor": home not drawn, "Set up under Owner", the not-drawn line | US-3, US-4 | AC-23, AC-28, AC-36 | Same |
| P-9 | "Arrange by Branch": no copies, other note | US-9 | AC-52, AC-33 | Note words "Reporting lines" (Q4, **yes given**) |
| P-10 | "Wall chart: All on A1": copies dashed, quiet lines, footer, each name once | US-10, US-11 | AC-55 - AC-61 | The preview window's side panel ("50 boxes for 43 seats…", "Pages 1", "Names 9.6 pt") is a **stand-in**: the product uses the browser's own print window and 069's panel, unchanged (design §5.7). Not built |
| P-11 | "Empty: no seats yet", HR (with "Build it from your people") and reader | US-12 | Given no seats, then today's words and button, unchanged | Same as today |
| P-12 | "Error": new words, Try again, POS-LOAD | US-12 | AC-63 | Same |
| P-13 | Person: "Store reader (Noida)": Noida seats only, "reports above your view", Delhi manager kept home | US-7 | AC-31, AC-49 | Tray line wording, see P-23 |
| P-14 | Device "Phone 390" | US-14 | AC-64 | Same |
| P-15 | Theme dark | US-15 | AC-66 | Same |
| P-16 | Dropdown "Who reports to whom" | US-2 | AC-33 | **Becomes "Reporting lines"** (Q4, **yes given**) |
| P-17 | Copy box: dashed border, "{branch} · N people", "+N more here", quiet line with icon | US-2 | AC-27, AC-30, AC-32 | Same (Q6, **yes given**) |
| P-18 | Home box: "N of M filled", open tag, "N more shown under …" | US-2, US-3 | AC-22, AC-29 | Same (Q6, **yes given**) |
| P-19 | Tiles unchanged by copies | US-2 | AC-34 | Same |
| P-20 | "No reporting manager" box for HR | US-9 | Unchanged from today | Not a 072 feature; same as today |
| P-21 | Zoom tools, "+ Add a seat", "Download wall chart (PDF)" | US-9 | Unchanged | Same as today |
| P-22 | Tray line "Reports to Neeraj Sood, who is in no seat" for every reader | US-8 | AC-50 | **HR only**; others "a manager who is not on this chart" (04 Q3, **yes given**) |
| P-23 | Tray line "Reports to a manager outside your view" | US-7 | AC-39, AC-49 | **Becomes "Reports to a manager who is not on this chart"** for every absent key (outside scope, Left, unseated for non-HR). **Needs your yes (Q1)** |
| P-24 | Tray "Reports to {name}" picks a sample person from the manager's seat | US-4 | AC-39 | Product uses the real manager's name. Prototype artefact, no change in meaning |
| P-25 | Split advice | US-4 | AC-40 | Prototype shows none in Reporting lines (Q3, **yes given**). Removing the two sentences in Branch and Department too **needs your yes (Q2)** |
| P-26 | Not in the prototype: Find, filters, two-seat manager, Left manager, past date | US-6, US-13 | AC-3, AC-7, AC-15, AC-16, AC-44 - AC-48 | Rules from 04 (gap rules **yes given**) and brief §3 |
| P-27 | "N open" printed on a partly filled home | US-10 | AC-57 | Prototype prints it; governing it by 069's "Show Vacant" tick is an assumption (Q3) |

---

## 17 · Traceability

| Source | ID or line | Story | ACs | Status |
|---|---|---|---|---|
| Brief | "People follow Reports To" | US-1, US-13 | AC-1 - AC-21, AC-67 | covered |
| Brief | "Copies are always end boxes" | US-1 | AC-18, AC-65 | covered |
| Brief | Seat count, open slots, opening, child seats on home only | US-3 | AC-22 - AC-26 | covered |
| Brief | Headcount counted once | US-2, US-10 | AC-19, AC-34, AC-55, AC-56 | covered |
| Brief | Branch / Department unchanged | US-9 | AC-52 | covered |
| Brief §3 | Manager in no seat / two seats / outside scope / left | US-1, US-13 | AC-3, AC-4, AC-14 - AC-16, AC-49 | covered |
| Brief §3 | Same title under one manager not merged | US-1 | AC-20 | covered |
| Brief §3 | "HR puts someone in a seat from a copy… the dialog says so in one line" | - | - | **gap - not in the approved design**; the tray note (AC-37) carries the same message. Q4 |
| Brief Q5 | Copies print | US-10 | AC-55 | covered |
| Brief §5 | 064 connector check, five cases | US-1 | AC-65 | covered |
| Design §5.1-5.7 | Placement, words, tray, note, phone, error, wall | US-1 - US-14 | see parity table | covered |
| Design Q1, Q3, Q4, Q5, Q6 | Decisions | US-2, US-4, US-1 | AC-27, AC-40, AC-33, AC-13 | covered |
| 04 | No new query | US-13 | AC-8 | covered |
| 04 Q3 | Unseated manager named only for HR | US-8 | AC-50 | covered |
| 04 Q4 | Gap rules | US-1, US-6 | AC-15, AC-44 - AC-47 | covered |
| 04 Q5 | Under 8 pt → A0 or sheets | US-11 | AC-62 | covered |
| 04 Q6 | Build before 065 screens | - | - | sequencing, not an AC |
| 04 G | 065 plans travel with the person | US-8 | AC-51 | covered |
| Organisation page | Unchanged | US-9 | AC-53 | covered |
| Prototype | P-1 - P-27 | see §16 | see §16 | covered; P-23, P-25, P-27 wait for your yes |
| Security | `01c` | - | - | **missing**; pSEC-1, pSEC-2, pPRIV-1 - 3 proposed → AC-1 - AC-9, AC-49 - AC-51, AC-58 |
| DevOps | `07` §3 OPS items | - | - | **missing**; nothing to trace |

---

## 18 · Ready check (Definition of Ready)

| Box | Status |
|---|---|
| Brief: one user, one outcome, JTBD, competitors, Kano (proxy), WOW, out of scope | Yes |
| Brief approved by the user | Yes, through her decisions on the brief's questions (04 header) |
| Persona enhancements decided against `01a` | **No `01a`** (brief bad news 4) |
| Clickable prototype reviewed at the design check | Yes (Q1-Q6) |
| Feedback logged in `ux-learnings.md` | I could not check |
| Every state designed: empty, loading, error, no permission, first-time | Empty, error yes; no permission = refused as today; loading and first-time are today's |
| **`01c` written** | **No - fails** |
| **`07` §1-3 written** | **No - fails** |
| Gap analysis grounded in source | Yes |
| Stories INVEST-checked, sized, linked, with must-nots | Yes |
| Every story has an AC with an oracle | Yes |
| Traceability complete | One gap (brief §3 dialog line, Q4); `SEC`/`PRIV`/`OPS` cannot be complete without `01c`/`07` |
| Permission matrix with negative cases | Yes |
| Edge cases | Yes |
| NFR numbers | Yes |
| Migration stated | Yes - nothing |
| Compliance sub-analysis | Yes |
| No prohibited capability | Yes |
| Open questions do not block day one | Yes - step 1 (server) can start |

**Verdict: not ready by the book.** Two boxes fail (`01c`, `07`), a third is unchecked
(`ux-learnings.md`). That is at the "goes back" line of more than two. **My recommendation:** the
server step (US-13) can start on your word, as 04 proposed; the security engineer adopts the proposed
`pSEC`/`pPRIV` items before the screen work starts.

---

## Open questions

| # | Question | Owner | Blocks | My recommendation |
|---|---|---|---|---|
| Q1 | For every manager the reply does not carry (outside scope, left, or in no seat for a non-HR reader), the tray reads "Reports to a manager who is not on this chart" instead of the prototype's "a manager outside your view". Yes? | Surbhi | AC-39, AC-49 (P-23) | Yes - the page cannot tell these cases apart without being told more than the reader may know |
| Q2 | Remove the two split sentences in Branch and Department too, not only in Reporting lines? | Surbhi | AC-40 (P-25) | Yes - they recommend what you decided against |
| Q3 | "N open" and "None here…" on paper follow 069's "Show Vacant" tick? | Surbhi | AC-57 (P-27) | Yes - one tick for every vacancy word |
| Q4 | The brief wanted the "put someone in" dialog to say, in one line, that the person is then placed by their own Reports To. The approved design dropped it. Leave it out (the tray note says it)? | Surbhi | Traceability gap | Leave it out |
| Q5 | `01c` and `07` for this slice: write them now, or accept the proposed `pSEC`/`pPRIV` items? | Surbhi, security engineer, DevOps | Ready check; screen steps | Security adopts the proposals before step 2 |
| Q6 | A Reports To that crosses companies draws a copy under the other company's seat. Fine? | Surbhi | AC-12 edge row | Yes - it is the true line |

## Assumptions

- `[ASSUMPTION]` Nothing ends a seat when a person leaves, so a Left manager can still be seated (04).
- `[ASSUMPTION]` The screen never asks for a past date (`posLoad` sends `{}`, confirmed at `portal.js:327`; tests do).
- `[ASSUMPTION]` A manager with only a covering seat in view gets the copy there.
- `[ASSUMPTION]` 065 replacement marks belong to a person (04 §2.2 G), so they move with the person.
- `[ASSUMPTION]` Census numbers are as of 24 Oct 2026.
- `[ASSUMPTION]` Reports To crossing companies is rare and is drawn as it is (Q6).
- `[ASSUMPTION]` The final seat-id tie-break in R4 is added only so the result never changes between loads; it is not in the brief.

## Subtract pass

Removed on this pass:
- A per-copy vacancy count and a "copies on/off" setting (H3 and the decisions answer both).
- A separate story for the view rename (folded into US-2).
- A browser timing gate (not reproducible; reported instead).
- An AC for loading and first-time states (unchanged from today).
- A Hindi copy requirement (not in the design; strings are translatable).
- A request for a release-note tile on mismatches (the brief already cut it).

Kept and why: the seat-id tie-break (one line; without it the chart can flip between loads); the
loop AC (the 64-person data shows Reports To is messy, and the test is cheap); the byte-identical ACs
(the shared card and the old views are the most likely things to break silently).

## Handoff note

To the engineer and the test engineer: the two easy misses are the **tray wording for an absent
`manager`** (one wording for every case, Q1) and the **scope rule** - no seat or manager outside
scope may appear in HTML, tray, Find or paper; test it with the Noida reader and grep the HTML.
The connector check must work out a copy's real parent by itself, never by calling the placement
code. Re-measure A1 (AC-61) before anyone quotes a point size; under 8 pt, the answer is A0 or
sheets, not smaller text. Part A of the CFO script is a separate, on-her-word data step; Part B
must not run. Build 072 before 065's screens; `portal.js` is also being changed by 066, 070-phone
and 071 - rebase and check their lines survive.
