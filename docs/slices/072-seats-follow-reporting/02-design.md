---
slice: 072-seats-follow-reporting
artifact: 02-design (the UX design and prototype; the agent file calls it 01b)
author: hrms-ux-designer
date: 2026-10-25
status: draft
inputs: [01-product-brief.md (24 Oct), Surbhi's decisions 24 Oct 2026 (in the task), ux-learnings.md, 064 prototype-old-v2.html (approved chart look), 064 10-old-design-improvements.md (connector rule), 064 12-fix-cfo-reports-seats.md (production census), 069 prototype-v1.html and 02-design.md, portal.js Positions code (ocNodeCard, ocRender, posNode, posSeatSheet, posRecordNotes, posNothing, posPrintHead), positions.html]
---

# 072 · Seats follow the reporting line — design

**I recommend. You decide.** Prototype: `prototype-v1.html` in this folder (invented data only).
**Not published and not committed**, as instructed.

## Bad news first

1. **Today's seat tray tells HR to split seats.** `posRecordNotes` says "A seat shared with another
   manager's people needs splitting first" and "Give the head a seat of their own, then move each
   group under its own manager". With 072 that advice is wrong: Part B is skipped and the chart now
   draws those people under their manager by itself. In the Reporting lines view those two notes must
   go, replaced by the "Where it shows on this chart" list (§5.3). Q3.
2. **On the phone there are no connector lines** (existing 064 phone rule: boxes stack). A copy reads
   as "under the CFO" only by its order in the stack and by its own words. The words carry it
   ("Same seat as under Owner"), but a phone reader cannot see which box a copy hangs from. This was
   already true for every box; copies make it matter more. Risk R2, P3.
3. **The wall chart gets bigger.** In my invented 43-seat chart, copies add 8 boxes (50 boxes for 43
   seats), and "All on A1" prints names at **9.6 pt**. At DTC's real 91 seats, 069 measured 9.5 pt
   *before* copies. More boxes will push it lower, maybe under 9 pt. It must be re-measured on DTC's
   real shape before 069's numbers are quoted again (brief §5). I could not do that: I have no DTC data.
4. **Two names for one view.** The dropdown says "Who reports to whom"; the print heading and
   Surbhi's decisions say "Reporting lines". Pre-existing, but this slice makes the view mean more.
   Q4.

## 1 · Frame

**HR Manager (laptop) and Owner/CXO (laptop or phone), opening Positions, want to see who really
works under whom — and still see every seat, its open slots and its seats below, once.**

| Persona | In scope | What changes |
|---|---|---|
| HR Manager | Yes | The chart follows Reports To. She fixes a line in one place (the employee record). The tray tells her where each seat shows |
| CXO / Owner | Yes | The CFO's box finally shows his team. Counts do not change |
| Branch-limited reader (069 D7) | Yes | Copies only under seats they can see; otherwise people stay in the seat's own box. No hidden seat is named |
| Employee | No | Employees do not open Positions |
| Frontline | No | Not a frontline screen |

## 2 · Evidence

- **Fact:** the approved look is 064 `prototype-old-v2.html` (`ocNodeCard`, `ocRender`, the hanging
  column). I reused it through 069's compact copy, so copies use the same boxes and lines.
- **Fact:** live words read in `portal.js` (this worktree): "+N more in this seat", "Nobody in this
  seat", "reports above your view", "No seats yet", the seat tray, and `posRecordNotes`.
- **Fact:** production census (064 `12-fix-cfo-reports-seats.md`, 24 Oct): Back Office 36 slots,
  1 open, 10 child seats, 6 people report to the CFO; Office Executive 6/6, 4 to the CFO; MIS 2, 1 to
  the CFO; Accountant 5, 1 to the CFO; HR-EMP-00001's seat sits *below* Back Office, and 64 report to it.
- **Not done:** no bench capture. The task was design from the brief and the approved prototype.
  The prototype is invented data only, so it may live in the repo (learning of 15 Sep 2026).
- Screenshots and measuring scripts: `C:/Surbhi-Git/hrlocal-data/ux-review/2026-10-25-slice070/`
  (`measure.js`, `look.js`, `v1/`, `v1-measure.txt`).

## 3 · Benchmark

No new benchmark: the brief §8 covers it and nothing here depends on a competitor. Keka, Zoho People
and HiBob draw people by reporting manager; Darwinbox-style position charts hang seats under seats
`[recall — verify]`. Neither draws **one seat in two places with a marker saying so** that I know of
`[recall — verify]`. What we deliberately do not copy: a person chart with no seats (it loses
vacancies), and a "move on chart" drag that changes someone's manager (brief §8).

## 4 · Findings

| ID | Finding | Impact | Kind | Size | Severity |
|---|---|---|---|---|---|
| SF1 | Tray advice "split the seat" contradicts 072 and the Part B decision | High | Fix | S | **P1** — tells HR to do the opposite of what was decided |
| SF2 | A home box with all its people elsewhere would say "Nobody in this seat" — false | High | Fix | S | P1 (designed out: §5.2) |
| SF3 | Phone stack has no lines; copies rely on words | Medium | Improve | — | P3 (accept; words added) |
| SF4 | "Who reports to whom" vs "Reporting lines" | Low | Fix | S | P3 (Q4) |
| SF5 | Error state appends the raw server message ("Could not load the chart: …") | Medium | Fix | S | P3, pre-existing; §5.6 gives the words |
| SF6 | A1 size at DTC with copies is unmeasured | Medium | Improve | S | P2 for 069's quoted size |
| K1 | Connector rule: no line ever misleads | — | **Keep** | — | Holds with copies: 0 false links, 96 states |
| K2 | Counts (tiles, footer) count seat records and people once | — | **Keep** | — | Copies never add |
| K3 | Branch and Department views | — | **Keep** | — | Byte-for-byte unchanged |

## 5 · Design

### 5.1 The rule, as drawn (Reporting lines view only)

For each person in a seat, the chart reads which seat their **Reports To** manager sits in.

| Where their manager sits | The person is drawn in |
|---|---|
| The seat's own parent seat | The seat's own box (home) |
| Another seat the reader can see | A **copy** of the seat, hanging under the manager's seat |
| The same seat (a head and team in one seat) | Home `[recommendation — brief silent; Q5]` |
| No seat, left, empty, or outside the reader's scope | Home |
| Two seats | The Permanent seat with the highest weight (brief §3) |

- **Copies are always end boxes.** No fold button, nothing under them, so no loop is possible.
- **Open slots, the job opening and child seats stay on the home box only.** A vacancy shows once.
- **The home box is not drawn only when** it has no people, no open slot and nothing under it.
- People are never counted twice. Tiles and the print footer count seat records and people.
- A copy never sits in an "identical seats grouped" box with a different seat (brief §3).
- Copies follow the real seats under the same manager (real seats first, then copies).

### 5.2 The words on the boxes

| Box | Title | Second line | Names | Quiet line (icon + words, 12 px, grey) |
|---|---|---|---|---|
| Copy | Office Executive | Head Office · 4 people | first 3, then "+1 more here" | "Same seat as under Owner · 6 in all" |
| Copy whose home is not drawn | Store Auditor | Noida · 1 person | the name | "Set up under Owner" (adds "· N in all" only if more people exist elsewhere) |
| Home with some people elsewhere | Office Executive | Head Office · 6 of 6 filled | the 2 at home | "4 more shown under Chief Financial Officer" or "13 more shown under 2 other managers" |
| Home with nobody of its own | MIS **open** | Head Office · 1 of 2 filled | "None here: all 1 shown under Chief Financial Officer" | — |
| Home, nothing shared | as today | as today | "+N more in this seat" | — |

- "N in all" = people in the seat, whole company `[ASSUMPTION — Q1]`.
- The copy's box has a **dashed border**. The words, not the dash, carry the meaning.
- If the parent seat is outside the reader's view, the words say "a seat above your view", never its
  name (brief §3 privacy rule).

### 5.3 Relating the copies

- **Hover or keyboard focus** on any box of a shared seat: every other box of that seat on screen gets
  a dashed outline. Nothing moves. (Desktop only; touch has no hover.)
- **Click or tap** opens the existing seat tray, with one new section above "Who is in it":

> **Where it shows on this chart**
> Under Owner: its own box, 22 people, 1 open, 10 seats under it — **Show**
> Under Chief Financial Officer: 6 people · *You opened this one* — **Show**
> Under Backoffice Executive: 7 people — **Show**
>
> People are placed by Reports To on their employee record. To move someone, change their Reports To;
> the chart follows the next time it opens. The seat itself stays under Owner.

- If the home is not drawn: "Its own box under Owner is not drawn: nobody there reports along that
  line, no slot is open and no seat hangs under it."
- **Show** closes the tray, opens the folds down to that box, scrolls to it and puts focus on it.
- "Who is in it" adds one grey line per person: "Reports to Sneha Khanna (Chief Financial Officer)",
  "Reports to Neeraj Sood, who is in no seat", "Reports to Vikram Rana, also in this seat",
  "Reports to a manager outside your view", or "No manager on their record".
- The new section and the per-person line appear in the Reporting lines view only.

### 5.4 Reporting lines versus the other views

One line above the chart, so nobody is surprised when a seat holds fewer names in one view:

- **Who reports to whom:** "Each person is shown under the seat of their manager, as set in Reports To
  on their employee record. A seat shared by people with different managers shows once under each
  manager. Open slots and the seats under it stay on the seat's own box."
- **Branch / Department:** "One box per seat, with everyone in it. To see people under their managers,
  choose Arrange by: Who reports to whom."

### 5.5 Phone (390 px)

Same boxes, same words, stacked as today. Tap opens the tray as a bottom sheet; **Show** is 44 px.
No hover. Measured: no sideways scroll, no text under 12 px, no target under 44 px.

### 5.6 Empty and error states

- **No seats yet** (HR): today's words, unchanged, with "Build it from your people".
- **No seats yet** (reader): today's words, "…ask them", no button.
- **Error:** "**The chart did not load.** Nothing has changed in your seats or your people. Check your
  connection, then try again. If it keeps happening, tell your administrator: code POS-LOAD."
  Button: **Try again**. Never the raw server message (fixes SF5).
- **Nobody's manager sits in a seat:** the chart looks exactly as today. No message.
- **A reader whose scope hides every manager seat:** no copies; everyone stays home.

### 5.7 Wall chart (069), All on A1

Prints exactly what the screen draws with every fold open. A copy prints with a dashed border, its
names and its "Same seat as under …" line. The home prints "N open" (or "Vacant" when nobody is in
it at all) and its "N more under …" line. **Each person prints once**; the footer counts seat
records ("43 seats · 187 people in seats"). Measured on the invented chart: 50 boxes for 43 seats,
9.6 pt on A1, 187 names printed, 187 different. The 069 panel is unchanged.

## 6 · Accessibility and privacy

- Every box is a real button; the quiet line is part of its spoken name. The icon is `aria-hidden`.
- Dashed border and outline are never the only signal: words say "Same seat as under …".
- Show buttons carry a spoken name: "Show it on the chart: Under Chief Financial Officer: 6 people".
- Focus moves to the tray heading on open and back to the box on close; Escape closes.
- Privacy: neutral (brief §9). Reporting lines are already visible. A copy or a tray line never names
  a seat or manager outside the reader's scope. No leaving dates, plans or flags are added. 065 marks
  travel with the person into their copy `[ASSUMPTION, as brief]`.

## 7 · Connector rule

"No line may suggest a box reports to anything but its real parent." For a home box the real parent
is its parent seat; for a copy it is the seat its people's manager sits in. The prototype's
`connectorCheck()` reads every drawn box against that, on screen and on paper, and fails a copy that
has a fold button or anything under it. **Result: 0 false links in all 96 screen states and both
prints.** The 064 test must learn this meaning (brief §5).

## 8 · Checks before handoff

- **Measured** (`v1-measure.txt`): 12 states × 2 readers × 1440 and 390 × light and dark = 96. Sideways
  scroll 0; text under 12 px 0; targets under 24 px (desktop) or 44 px (phone) 0; script errors 0.
  First pass found 30 px Try again / Build buttons on the phone; fixed.
- **Nielsen:** visibility of status (quiet line, tray list); match with the real world (Reports To
  wins, as in approvals); recognition over recall (Show jumps there); error prevention (no edit from
  a copy); help (one-line note per view).
- **Red team:** a team of 400 under one manager is one copy, names folded to 3. A manager who leaves:
  people return home. Network drop: error state. Brand-new HR: the note says why a seat appears twice.
  The 64 case (Q2) needs no special design: if real, Back Office's home shrinks and a large copy hangs
  under Backoffice Executive, which sits under Back Office — legal, loop-free, and shown in the
  prototype with 7 people ("Back Office opened").

## 9 · What the analyst must turn into acceptance criteria

1. The placement table in §5.1, each row a test, in Reporting lines only; Branch/Department unchanged.
2. Copies: no fold button, nothing under them, dashed border, the quiet line words of §5.2.
3. Vacancy and job opening on the home box only; home hidden only on the three conditions.
4. Every person drawn once; tiles and print footer unchanged by copies.
5. Nothing outside the reader's scope is named, in boxes, lines or the tray.
6. Tray: the "Where it shows" list, Show behaviour, per-person "Reports to" line; `posRecordNotes`
   split advice removed in this view (Q3).
7. Connector check passes with the new meaning; copies of one seat never grouped with another seat.
8. Error state words of §5.6; no raw server message.
9. 069 print: copies print; names once; A1 size re-measured on DTC's shape.
10. Hover/focus outlines the other boxes of the same seat (desktop).

## 10 · Usability test plan (High impact)

Five people (2 HR, 2 owners/managers, 1 who has never used Positions), desktop, invented data.

| Task | Success | Would change the design if |
|---|---|---|
| "How many people does the CFO manage, and in which jobs?" | Answers 12 within 60 s | They add the Office Executive home names too |
| "How many people are in Office Executive in all?" | Says 6 | They say 4 or 2 — then the "in all" line is not doing its job |
| "Where is the open Back Office slot?" | Finds the home box | They look under the CFO |
| "Is Back Office under the CFO?" | Says no, it is set up under Owner | Most say yes — then the copy needs a stronger marker |

## Not in this slice (yours to decide later)

- A "show only this manager's team" filter.
- Copies in the Branch and Department views.
- Lines on the phone layout.

## Subtract pass

Removed: an "N places" count chip on every shared box (the quiet line and the tray already say it), a
hover tooltip listing the other places (not reachable on touch; the tray does it), a review switch
for the 64 case (the Back Office example shows it), a separate print panel option to hide copies
(Surbhi decided copies print), and a new error code list (one code).

## Parity with Surbhi's decisions (24 Oct)

| Her words | Prototype | Difference |
|---|---|---|
| "Office Executive - 4 people. Same seat as under Owner - 6 in all" | "Head Office · 4 people" + names + "Same seat as under Owner · 6 in all" | Separator "·" not "-"; names listed as on every box |
| Copies never have boxes under them | Same | None |
| Own box hidden only when no people, no open slot, no child seats | Same; copies hanging under it count as "something under it" | Interpretation, see Q5 |
| A vacancy shows once, on the seat's own box | Same | None |
| 065 plans travel with the person | Not drawn (no 065 data in this prototype) | Not shown |
| Reporting lines view only | Same | None |
| Copies print on the wall chart | Same | None |
| Part A re-points 5 seats, Part B skipped | Drawn as real seats under the CFO | None |
| — | New words: "N more shown under …", "None here: all N shown under …", "Set up under …", "+N more here", tray list | Need her yes |

## Open questions

| # | Question | Owner | Blocks | My recommendation |
|---|---|---|---|---|
| Q1 | "6 in all" — people in the seat (6) or slots (6)? They differ for Back Office (35 people, 36 slots) | Surbhi | Copy wording | People: the box is about people; slots are on the home box |
| Q2 | Are the 64 reporting to HR-EMP-00001 real? (still open) | Surbhi with DTC HR | Release at DTC, not the design | Fix the records first; the design works either way |
| Q3 | Remove the "split the seat" advice from the tray in Reporting lines? | Surbhi | Tray copy | Yes; replace with "Where it shows" |
| Q4 | One name for the view: "Who reports to whom" or "Reporting lines"? | Surbhi | Dropdown and print heading | "Reporting lines" in both (shorter, her word) |
| Q5 | People whose manager is in the same seat: stay home (my choice)? | Surbhi | Placement rule | Yes; a copy of a seat under itself reads as a loop |
| Q6 | Approve the new box words in the parity table's last row? | Surbhi | All copy | Yes |

## Assumptions

- `[ASSUMPTION]` The server sends, per person, the seat their manager sits in (brief §4); the
  prototype stores it directly.
- `[ASSUMPTION]` 065 replacement marks belong to a person, so they move into the copy.
- `[ASSUMPTION]` A branch-limited reader sees boxes only for seats in their scope (069 D7).
- `[ASSUMPTION]` Invented data: 43 seats, 187 people, DTC's shape, not DTC's size.

## Handoff note

To the analyst and engineer: the whole rule is one function in the prototype (`buildModel`), and it
is cheap — copies are just extra end boxes. The two things easy to miss are the tray (SF1: the old
split advice must not survive in this view) and the scope rule (never name a seat outside view, in
the quiet line or the tray). Re-measure 069's A1 size on DTC's real shape with copies before anyone
quotes a point size. Keep the connector check as a test; it now has two meanings of "real parent".
