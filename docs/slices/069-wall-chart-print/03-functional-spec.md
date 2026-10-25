---
slice: 069-wall-chart-print
artifact: 03-functional-spec (the contract calls this file 02-functional-spec; this folder already uses 02 for the design, so it is 03 here at the lead session's request)
author: hrms-business-analyst
date: 2026-10-24
status: revision 2 - Surbhi's final answers of 24 Oct 2026 applied; ready for build (DevOps notes waived)
inputs: [01-product-brief.md rev 4 + "Decisions 24 Oct 2026" + "Decisions 24 Oct 2026 (2)", 01c-security-privacy-requirements.md rev 1, 02-design.md, prototype-v1.html (approved by Surbhi), portal.js, panels.css, positions.html, register.py, alvoraa_position.json, hierarchy_chart_desktop.js]
---

# 069 · Download wall chart (PDF) — functional spec

**I recommend. Surbhi decides.** No code, no commit, no push from this step.

## What changed in revision 2

Surbhi answered every open question on 24 Oct 2026, all "yes" to the recommendations (recorded via
the lead session):

| Topic | Her answer | Where it lands |
|---|---|---|
| DevOps notes (`07` §1–3) | **Waived for this slice** — client-side print only. *Waived by Surbhi 24 Oct 2026* | Ready check, traceability |
| D-1 scope wording | "Covers {n} branches: {names}" | AC-17, AC-41 |
| D-3 several tops | Each top box prints with its own seats under it | AC-50 |
| Branch on the box | Stays, **if** All on A1 still reaches 8 pt (re-measure) | AC-32 |
| Ctrl+P (Q15, Q2) | Prints the screen chart; flags, tags and HR-only box hidden by one CSS rule; no "printed by" | AC-3, AC-3a |
| Two ticks (brief "Decisions (2)", option A) | "Show Vacant" and "HR copy: show replacements" | US-12, US-13, US-14 |
| Meaning of "replacement" | A seat being re-filled: the person in it is leaving, or a job opening was raised on it | AC-59 |
| Slice 065 replacement plans | **Never print**, unless counsel says yes in writing | AC-27b, US-5 |
| Residual risks R1, R2 (`01c`) | **Accepted by Surbhi, 24 Oct 2026** | §15, traceability |
| Privacy test | Runs twice, tick off and tick on; plus a test that the tick never shows to a reader without leaving dates | AC-27a, AC-27b, AC-65 |
| File-name date | `2026-10-24` | AC-38, AC-61 |
| Q14 designation | Under the title only when it differs | AC-18 |
| D-4, D-5, D-6 | **Still open** — the lead session is asking Surbhi (Q5, Q6). ACs are written to the recommendation | AC-20, AC-14, AC-21 |

## Bad news first

1. **The HR copy puts leaving dates on paper.** That reverses brief D6 for the HR copy only (brief
   question R3, answered yes). Paper cannot be taken back. The guards are: the tick is off every time
   the panel opens, only readers who already see leaving dates on screen get it, and every sheet says
   "HR use only - not for display". **This is a deliberate trade-off Surbhi accepted, not a control
   that stops misuse.** A careless HR person can still pin an HR copy on a wall.
2. **`01c` is now out of date in four places** and the security engineer must update it before the
   security review (Q13): the allowed list (designation, department, and the HR copy words); the
   sentinel test (runs twice; `designation` and `department` now allowed); the file-name pattern
   (optional "HR copy - " prefix); and SEC-3 (the "hide the screen chart" option is no longer
   allowed). This spec's ACs are the target. It does not block build start.
3. **The new ticks are not in the approved prototype.** Surbhi approved them in words, not on a
   drawing. Their place in the panel and three short pieces of wording are my proposal (§9 D-8,
   Q16). The engineer builds them as written here unless the UX designer changes them.
4. **The kill line must be re-checked with a fuller box.** Each box now carries designation and
   department as well. The prototype measured 9.5 pt for All on A1 without them. If the new figure is
   under 8 pt, the branch name comes off the box first (AC-32).

---

## 0 · Reach and personas

| App | Touched? | How |
|---|---|---|
| `alvoraa_portal` | **Yes** | `portal.js` (Positions section), `panels.css` (print rules), `positions.html` (one button), the jsdom test suite |
| `hrms` | No code | `register.py` `position_table` is read, not changed. Confirmed fact: it already returns every row the print needs, including `leaving`, `opening` and `may_see_leaving` for the HR copy |
| `erpnext`, `frappe` | No | — |
| `alvoraa_goals`, `alvox_compensation` | No | — |

**HRMS domain:** org structure only. Leaves, attendance, payroll, appraisals, goals, compensation and
learning are not touched. Two side notes: the portal-wide `@page { A4 landscape }` rule
(`panels.css:2154`) also shapes payslip prints. This slice leaves it alone (D10) and must not change
how a payslip prints (AC-42). The HR copy reads `opening` (an open Job Opening on the seat) but never
prints the opening's ID or links to recruitment.

| Persona | What changes |
|---|---|
| **HR Manager** | New button on Positions. Prints every seat they can see, any levels, any paper. Can print an HR copy with leaving dates and openings |
| **Owner / CXO** (DTC) | Same button. Prints his branch only (D7). Gets the HR copy tick only if the server already sends him leaving dates (brief R5) |
| **Head of department** | Nothing. Cannot open Positions, so no button. Their own print is a later slice (D7) |
| **Employee / frontline** | Nothing on any screen. Reads the wall. Never sees a leaving date on a wall copy |

## 1 · Is this the real problem?

**Stakeholder statement:** DTC works from a printed full hierarchy today, and keeps a version for the
HR department showing vacant and replacement seats (Surbhi, 24 Oct 2026).
**Confirmed fact:** today's Print (`portal.js:1212`) prints only 3 names per seat (`POS_NAMES_SHOWN`,
`:602`), on A4 only (`panels.css:2154`), with leaving dates, the HR-only box and "printed by {name}".
So the need is real and the current tool cannot meet it. The wall copy drives no decision; it is a
reference. The HR copy supports a decision — which seats HR must fill next — and the system already
answers that on screen (the "leaving" tile and openings), so the HR copy is a paper version of an
existing screen, not a new report.

## 2 · Gap analysis

| Requirement | What exists today (read in the source) | Verdict | Cost |
|---|---|---|---|
| A PDF of the seat chart on paper the user picks | Frappe HR Org Chart has "Export" (`hierarchy_chart_desktop.js:115`): a PNG of **Employee** reporting lines, desk only, blurs when enlarged. Frappe Print Format uses wkhtmltopdf, which cannot draw this layout (brief §4) | **Extend** `portal.js`: browser's own print, page size set by us | M |
| Choose where to start and how many levels | Screen folds to 1 level (`POS_OPEN_DEPTH = 1`, `:296`); no level choice | **Extend** | S |
| Paper size A4–A0 | One global `@page{size:A4 landscape}` (`panels.css:2154`) | **Extend**: a page-size rule added only while the wall chart prints | S |
| Every name in the seat | Screen shows 3 and "+N more" (`posFew`, `:611`) | **Extend**: the paper draws all | S |
| Nothing private on the wall copy | Today's print shows flags, tags, the HR box and "printed by {name}" (`posPrintHead`, `:1288-1299`) | **Extend**: an allowed-list copy (PRIV-1) | S |
| Same boxes and lines as the screen | `ocNodeCard` / `ocRender` with the hanging column (`:139`, `:228`) | **Already there** — reuse with print rules | — |
| Long columns wrapped to fit the paper's shape | Hanging column is a single column | **Extend** (print-only) | M — the risky part |
| Readable-size warning | None | **Build** (a few lines in the panel) | S |
| Several sheets for an office printer | None | **Build**: one clipped copy per page | S |
| Panel to hold the choices | The Positions tray `posSheet` (`:2296`) | **Already there** — reuse | — |
| Count of people in no seat | `POS.unseated` (`:342`), sent to HR scope only | **Already there** — show the count | — |
| Show or hide "Vacant" | Vacant worked out from empty `people` | **Extend**: one tick | S |
| HR copy with seats being re-filled | Server already sends `leaving` per person and `may_see_leaving` (`register.py:336-350`, `:435`) and `opening` per seat (`:388`). Screen already shows "leaving {d Mon}" (`posDay`, `:302`) | **Extend**: one tick, two extra words on paper, a banner. No server change | S–M |
| Ctrl+P with no "printed by" | `posPrintHead` adds "printed by {name} ({role})" (`:1299`) | **Extend**: drop that part | S |
| Join marks for office sheets | — | **Drop** (D8: only if cheap; the sheet label is enough) | — |
| Server-made PDF | — | **Drop** (D1) | — |
| Heads of department print their team | Cannot be scoped by reporting line today | **Drop** to a later slice (D7) | — |
| Remove the Owner's Branch permission | — | **Drop** (D7: he keeps it) | — |
| Fix the global A4 rule | — | **Drop** (D10) | — |
| Log who printed | — | **Drop** (01c R1, accepted by Surbhi 24 Oct 2026) | — |
| 065 replacement plans on paper | — | **Drop** unless counsel says yes in writing (brief "Decisions (2)" option B) | — |
| Named successor (offer accepted) | Job Offer is not read | **Drop** (needs server code; nobody asked) | — |
| Staff told before names go up | — | **Configure**: text in the release note (PRIV-3) | S |
| Per-person "do not name me" | — | **Drop** (01c Q2: HR handles by hand) | — |

**Rung:** new code in `portal.js` and `panels.css` only, plus one button in `positions.html`. Cheaper
rungs rejected: today's Print leaks and cannot show every name; a Print Format cannot draw the layout.
No new DocType, field, endpoint, package or app.

**One source of truth:** the rows `position_table` already returned to this reader. The paper never
reads anything else.

## 3 · Process flow

1. HR opens **Positions**. If the page has at least one seat, the toolbar shows **Download wall chart
   (PDF)**.
2. HR presses it. The panel opens with: the top, 2 levels, A3, one sheet, **Show Vacant** ticked,
   **HR copy** unticked (when shown at all). The result line says what will print.
3. HR changes any choice. The result line updates.
   - *Decision:* names under 8 pt? → amber warning with one or two fix buttons. HR presses one, or
     carries on anyway.
   - *Decision:* "Several sheets" but it fits on one at 10 pt or more? → prints as one, and says so.
   - *Decision:* HR copy ticked? → panel says "Print in the office, not at a print shop."; every sheet
     will carry "HR use only - not for display"; the file name starts "HR copy -".
4. HR presses **Open print preview**. We set the page size and the file name, then open the browser's
   print window.
5. In the print window HR picks **Save as PDF** → **Save**. The file goes to Downloads.
6. The print window closes. We remove our page size and put the page title back. The panel stays
   open for another try.
7. Wall copy: HR sends the PDF to a print shop. HR copy: HR prints it in the office.

**Unhappy paths**

| What happens | What the person sees |
|---|---|
| Page has no seats | No button (existing empty state) |
| Page failed to load | No button (existing error message) |
| A filter is on | Note: the filter does not apply; the print uses every seat they may see |
| Owner, branch-limited | Note: covers his branch only; seats print side by side with no lines above |
| Reader not sent leaving dates | No HR copy tick at all |
| Panel closed with HR copy ticked, then opened again | HR copy is unticked |
| Cancel in the print window | Same clean-up as step 6. Nothing saved |
| Close the panel without printing | Same clean-up as step 6 |
| Browser ignores the page size (iPhone Safari, untested) | The PDF comes out at the browser's own size. Tested by hand, then Q4 |
| Ctrl+P on the Positions page without the panel | The screen chart prints, with no flag, tag, HR box or "printed by" (SEC-3) |
| No permission | No Positions page, so no button (unchanged) |

## 4 · Epic and user stories

**Epic:** As HR, I can print the seat chart as a PDF on the paper I choose — a wall copy with
nothing private on it, or an HR copy showing which seats are being re-filled.

Stories are in build order. Each one can be built and tested before the next starts.

| ID | Story | Pts | Prototype screen | Carries | ACs |
|---|---|---|---|---|---|
| **US-1** | As an **HR Manager**, I want Ctrl+P on Positions to keep printing the chart, but never leaving dates, flags, the HR-only box or my name, so that a careless print cannot tell staff who is leaving | 2 | Zoom row (Print button replaced by the panel) | SEC-3 | AC-1 – AC-3a |
| **US-2** | As an **HR Manager**, I want a "Download wall chart (PDF)" button that opens a panel, so that I have one safe place to print from | 2 | Toolbar; "Panel as it opens" | SEC-1, SEC-2 | AC-4 – AC-8 |
| **US-3** | As an **HR Manager**, I want to choose where the chart starts, how many levels, the paper and the sheets, and be told what the print covers, so that I get the chart I need | 3 | "Panel as it opens" | SEC-1 | AC-9 – AC-17 |
| **US-4** | As an **HR Manager**, I want the paper to show every seat and every name in the same boxes and lines as the screen, wrapped to the paper's shape, so that the wall shows the real organisation | 5 | "Print preview: 23 boxes on A3"; "All on A1" | — | AC-18 – AC-26 |
| **US-5** | As an **employee whose leaving date HR knows**, I must never see it on the wall copy, nor my ID, grade or a replacement plan on any copy, so that my private news stays private | 3 | All preview states | PRIV-1 | AC-27a, AC-27b, AC-28, AC-29 |
| **US-6** | As an **HR Manager**, I want to know the name size before I print, and be offered a fix when it is too small, so that I do not pay a print shop for an unreadable sheet | 3 | "All levels on A3 (warning)" | — | AC-30 – AC-36 |
| **US-7** | As an **HR Manager**, I want "Open print preview" to set the paper size, file name and footer, and to clean up afterwards, so that the PDF is right and other prints are not affected | 3 | "Print preview" stand-ins | SEC-4, PRIV-2 | AC-37 – AC-44 |
| **US-8** | As an **HR Manager** with an office printer, I want the chart split over several sheets at 10 pt, each labelled with where it goes, so that I can tape it up | 3 | "All on A3, several sheets" | — | AC-45 – AC-47 |
| **US-9** | As **DTC's Owner**, I want to print what I see on screen, and be told plainly that it is my branch only, so that I am not surprised by loose boxes | 2 | Person = Owner | SEC-1 | AC-48 – AC-50 |
| **US-10** | As a **head of department or employee**, I must not be able to print the company chart, so that the staff list stays with HR | 1 | — (no screen) | SEC-2 | AC-51 – AC-52 |
| **US-11** | As a **DTC employee**, I must be told before my name goes on a wall, so that I can object first | 1 | — (release note) | PRIV-3, C1, C3 | AC-53 – AC-54 |
| **US-12** | As an **HR Manager**, I want to choose whether empty seats say "Vacant", so that a wall copy need not advertise gaps | 1 | Not drawn (D-8) | PRIV-1 | AC-55 – AC-57 |
| **US-13** | As an **HR Manager**, I want an HR copy that shows which seats are being re-filled — who is leaving and where an opening is raised — clearly marked "HR use only", so that the HR department can work from paper as DTC does today | 5 | Not drawn (D-8) | PRIV-1, PRIV-2 | AC-58 – AC-64 |
| **US-14** | As a **reader whose page holds no leaving dates**, I must not be offered the HR copy, so that the print never shows more than my screen | 1 | Not drawn (D-8) | SEC-1, PRIV-1 | AC-65 |

**Total: 35 points.** US-4 is a 5 because of the wrapped layout; it is not split because the wrap and
the boxes are tested together by the connector check. US-13 is a 5 because it touches the panel, the
paper, the banner, the file name and the second privacy test run; splitting it would leave an HR copy
without its banner, which must never ship.

**INVEST check:** every story is valuable on its own except US-6 to US-8 and US-12 to US-14, which
need US-4's drawing. US-1 can ship alone and closes today's leak. US-10, US-11 and US-14 are mostly
checks, kept as stories so they are not lost.

### YouTrack-ready table (do not create; Surbhi's call)

| Summary | Description | Persona | Pts | ACs | Requirements |
|---|---|---|---|---|---|
| 069 US-1 Replace Positions Print with the panel; Ctrl+P prints safely | Remove the zoom-row Print button; Ctrl+P still prints the chart, with flags, tags and HR box hidden by one CSS rule and no "printed by" | HR Manager | 2 | AC-1–3a | SEC-3 |
| 069 US-2 Wall chart button and panel | Toolbar button when rows exist; panel in the existing tray; no server call | HR Manager | 2 | AC-4–8 | SEC-1, SEC-2 |
| 069 US-3 Panel choices and notes | Start from, Levels, Paper, Sheets; scope, filter, people and privacy notes | HR Manager | 3 | AC-9–17 | SEC-1 |
| 069 US-4 Paper drawing | Every seat and name, designation, branch · department, Vacant, "below" counts, wrap, always light | HR Manager | 5 | AC-18–26 | — |
| 069 US-5 Allowed-field copy and sentinel test (two runs) | Only allowed keys reach paper; test with HR copy off and on | Employee | 3 | AC-27a, 27b, 28, 29 | PRIV-1 |
| 069 US-6 Name size and warning | Result line, reading words, warning with fixes, 300 ms, kill-line re-measure | HR Manager | 3 | AC-30–36 | — |
| 069 US-7 Print preview, file name, footer, clean-up | mm page size, title with 2026-10-24 date, footer, afterprint | HR Manager | 3 | AC-37–44 | SEC-4, PRIV-2 |
| 069 US-8 Several sheets | Clipped copy per page, sheet labels | HR Manager | 3 | AC-45–47 | — |
| 069 US-9 Owner's branch-only print | Scope note, side by side; several tops each with own seats | Owner | 2 | AC-48–50 | SEC-1 |
| 069 US-10 HOD and employee cannot print | Negative permission checks, switch-on C2 | HOD, Employee | 1 | AC-51–52 | SEC-2 |
| 069 US-11 Staff notice before switch-on | PRIV-3 note, DTC confirmation, 065 merge check | Employee | 1 | AC-53–54 | PRIV-3 |
| 069 US-12 "Show Vacant" tick | On by default; off removes the word, not the box | HR Manager | 1 | AC-55–57 | PRIV-1 |
| 069 US-13 "HR copy: show replacements" tick | Leaving dates and "Job opening raised" on paper; banner on every sheet; "HR copy -" file name; office-print note; off on every open | HR Manager | 5 | AC-58–64 | PRIV-1, PRIV-2 |
| 069 US-14 No HR copy tick without leaving dates | Tick absent when `may_see_leaving` is false | Reader without leaving dates | 1 | AC-65 | SEC-1, PRIV-1 |

## 5 · Data model

**No DocType, no field, no custom field, no new server data.** Confirmed fact: `position_table`
(`register.py:257`) already returns every value the paper needs.

### The allowed list (PRIV-1) — what may reach paper

The print draws from a **copy** built by one function. The copy is a tree of seats; each seat in it
holds only these keys. Allowed list per Surbhi's decisions of 24 Oct 2026: name, designation, Vacant,
counts, seat and department titles, branch (if the kill line allows, AC-32); and, on the HR copy only,
"leaving {date}" and "Job opening raised".

| Key in the copy | Taken from | Printed as | When |
|---|---|---|---|
| `title` | row `title` (= `position_title`) | Box heading | Always |
| `designation` | row `designation` | Line under the heading, **only when it differs from the title** (avoids "Cashier / Cashier") | Always |
| `branch` | row `branch` | "{branch} · {department}" line — not on the starting box | Always, unless AC-32 removes it |
| `department` | row `department` | Same line as the branch | Always |
| `names` | `people[]`: each entry holds `name` (= `employee_name`) only | One line each | Always |
| `names[].leaving` | person `leaving` (a date) | " · leaving {d Mon}" after the name, as the screen's `posDay` writes it (e.g. "leaving 30 Nov") | **HR copy on only.** Absent from the copy otherwise |
| `opening` | row `opening` — **turned into true/false**; the Job Opening's ID is never copied | "Job opening raised" | **HR copy on only.** Absent from the copy otherwise |
| `vacant` | worked out: `people` is empty | The word `Vacant` | When "Show Vacant" is on |
| `below` | worked out: seats and people under this seat | `{n} seats · {p} people below`, last level drawn only | Always |
| `kids` | the seat's children, each a copy of the same shape | The boxes under it | Always |

### Every key `position_table` sends, and where it goes

| Key | Sensitivity | On paper? | Used for |
|---|---|---|---|
| row `id`, `reports_to` | internal | **No** | Building the tree before the copy is made |
| row `title`, `branch`, `department`, `designation` | internal (personal next to a name) | **Yes** (Surbhi, 24 Oct) | Box; `department` also groups identical seats |
| row `company` | internal | Footer and file name only | — |
| row `opening` | internal (record ID) | **Only as the words "Job opening raised", HR copy only. The ID never** | — |
| row `grade`, `status`, `key`, `seats`, `filled`, `open`, `leaving_on`, `reports_to_title` | internal / sensitive | **No** | — |
| person `name` | personal, directory level | **Yes** | Name line |
| person `leaving` | sensitive | **HR copy only**, as "leaving {d Mon}" | — |
| person `employee`, `assignment`, `weight`, `type`, `covering`, `hired_on` | statutory-id / sensitive | **No** — not even on the HR copy | — |
| `as_at` | not personal | Footer date and file name | — |
| `unseated` | sensitive (named list) | **No** — only its length, on screen, in the panel | People note |
| `may_see_leaving` | — | **No** | Decides whether the HR copy tick exists (AC-58, AC-65) |
| `may_edit`, `may_delete`, `may_edit_employee`, `departments`, `active_people` | — | **No** | — |
| 065 `plan`, `plans` (when merged) | sensitive | **No — on any copy, unless counsel says yes in writing** | — |
| The printing user (`#sb-name`, `#sb-desig`) | personal | **No** (D5) — not on the wall chart and not on Ctrl+P | — |
| Photos (`image`, `ocAvatar`) | personal | **No** | — |

## 6 · States

There is no document workflow. The panel's own states (from design §5, plus the ticks):

| State | Shown when | Text |
|---|---|---|
| Readable | names ≥ 8 pt | result line + reading words |
| Warning | names < 8 pt | amber, `Warning:` + fix buttons |
| Fits on one | Sheets = several, but one sheet ≥ 10 pt | "It fits on one sheet at this size, so it prints as one." |
| Working | layout takes over 300 ms | "Working out the size…" |
| Filter on | any Positions filter set | filter note |
| Branch-limited | the rows hold one branch, or a top seat reports outside the rows | Owner note |
| No "in no seat" list | server did not send `unseated` | "Only people placed in a seat are on the chart." |
| HR copy on | HR copy ticked | office-print note; changed privacy line (AC-62) |
| Printing | between "Open print preview" and `afterprint` | page size rule and file-name title in place |

Nothing is stored, so nothing needs reversing.

## 7 · Permission and visibility matrix

This slice adds **no role and no permission**. The button follows the page; the page follows Frappe
Read on `Alvoraa Position` (`register.py:68-72`), checked on the server. The HR copy tick follows the
server's `may_see_leaving` (`register.py:336`, `:435`).

| Persona / role | Read on Alvoraa Position | Positions page | Button | HR copy tick | What prints |
|---|---|---|---|---|---|
| HR Manager | Yes (shipped in `alvoraa_position.json`) | Yes | Yes | Yes, if `may_see_leaving` | Seats in their companies (and branches, if limited) |
| System Manager | Yes (shipped) | Yes | Yes | Yes, if `may_see_leaving` | Same rule |
| Owner at DTC | `[UNVERIFIED — engineer to confirm]` which DTC role gives him Read | Yes | Yes | Only if the server sends him leaving dates (brief R5) | His branch's seats only (Branch User Permission kept, D7) |
| Head of department | No (switch-on check C2) | No | No | No | Nothing |
| Employee / frontline | No | No | No | No | Nothing |
| Guest | No | No | No | No | `position_table` refuses |

**Negative cases — who must NOT see what:**

- A head of department or employee must not get the button, the page or the rows.
- The Owner must not print any seat outside his branch, even though the company's other branches
  exist.
- A reader whose page holds no leaving dates must not see the HR copy tick, and must not be able to
  print a leaving date by any route.
- **Nobody**, HR included, may put on paper — from the panel with HR copy **off**, or from
  **Ctrl+P**: a leaving date, "key seat", "Frozen", "to fill", "open", "%", "covering", a job opening,
  the "No reporting manager" box, the "In no seat" list, a photo, an employee ID, grade, a
  replacement plan, or who printed it.
- **With HR copy on**, the only additions allowed are "leaving {d Mon}" after a name and "Job opening
  raised" on a seat, plus the banner. Never a replacement plan, plan note, reason, who set it,
  employee ID, the opening's ID, "covering", "key seat" or "Frozen".
- A visitor at the wall sees names, seat titles, designations, branches and departments only.

## 8 · Acceptance criteria

**Fixtures.** `F-DTC90`: the prototype's invented data (1 top, 22 seats under it, 5 leads with
14 / 10 / 13 / 19 / 11 seats under them; 90 seats; 363 people), loaded as a `position_table` payload,
**plus** every PRIV-1 sentinel key filled, `may_see_leaving: true`, one person with
`leaving:"2026-11-30"`, and one seat with `opening:"HR-OPN-SNTL"`. `F-OWNER`: the 8 Pitampura seats of
`F-DTC90`, each reporting to a seat not in the payload, `unseated` = 35. `F-GROUP`: three sibling
seats titled "Cashier", same branch and department, no seats under them, holding 2, 1 and 0 people;
and three more "Cashier" siblings in another branch all empty. `F-NOLEAVE`: `F-DTC90` with
`may_see_leaving: false` and every `leaving` set to null, as the server sends it.

### US-1 · Print button replaced by the panel; Ctrl+P prints safely (SEC-3)

Surbhi, 24 Oct 2026: printing is required. The panel replaces the old button; Ctrl+P keeps working and
prints the screen chart with one hiding rule and no "printed by" (Q2, Q15).

- **AC-1** Given HR on Positions in the chart view, when the zoom row draws, then it holds −, the
  percentage, +, Reset and Fit to width, and **no** "Print" button. Its group label reads "Zoom". The
  "Download wall chart (PDF)" button (AC-4) is the way to print.
- **AC-2** Given `portal.js`, when the static check reads the **Positions code** (`posLoad` to
  `ocPaint`), then it finds no `onclick="window.print()"` and exactly one `window.print()` call, inside
  the wall chart's print function. The Team notes pop-ups (`:8754`, `:8775`) are outside this check
  (security engineer to agree, Q12).
- **AC-3** Given HR on a seeded site with a leaver, a key seat, a covering person and at least one
  person with no manager, and the screen chart open with the panel closed, when print media is
  emulated (Playwright, `check_positions_connectors.js`), then **the screen chart is visible and its
  seat titles and names print** (the chart is not hidden), and the count of visible `.oc-flag`,
  `.oc-tag`, `.pos-nomgr-row`, `.private` and `[data-private]` is 0. One CSS rule in the Positions
  print block does the hiding, and it applies to the wall chart's print too.
- **AC-3a** Given the same page with `#sb-name` = `PRINTER-SNTL` and `#sb-desig` = `ROLE-SNTL`, when
  print media is emulated, then the `.pos-printhead` text holds neither sentinel nor the words
  "printed by". It still holds "Positions", the view, the company, "seats as at {date}", the filter
  words and "on {date}".

### US-2 · Button and panel (SEC-1, SEC-2)

- **AC-4** Given a reader whose `position_table` returns at least one row, then the toolbar shows an
  outline button "Download wall chart (PDF)" before "+ Add a seat" (whether or not that button is
  shown). Given `rows: []`, or a failed load, then there is no such button.
- **AC-5** Given a screen 640 px wide or less, then the button spans the toolbar width and is at least
  44 px tall.
- **AC-6** When the button is pressed, then the panel opens in the existing Positions tray
  (`posSheet`) with `role="dialog"`, `aria-modal="true"`, labelled by the heading "Download wall chart
  (PDF)", and focus is on that heading. Desktop: right-hand drawer. Phone: bottom sheet.
- **AC-7** When Close, Escape or the dimmed background is pressed, then the panel closes and focus
  returns to the button.
- **AC-8** (SEC-1) Given the jsdom suite with `gpFetch`, `frappe.call`, `fetch`, `window.open`,
  `URL.createObjectURL`, `localStorage.setItem` and `sessionStorage.setItem` replaced by functions
  that fail the test, and `window.print` replaced by a counter, when the test opens the panel,
  changes all four choices and both ticks and presses "Open print preview", then no replaced function
  is called and `window.print` is called once. Review check: the diff adds no Python.

### US-3 · Choices and notes

- **AC-9** Given `F-DTC90` as HR, when the panel first opens, then: Start from = "The top: Owner and
  Managing Director"; Levels = "2 levels: the top and the 22 seats under it"; Paper = A3 with hint
  "A3 is 297 × 420 mm."; Sheets = "One sheet, scaled to fit"; Show Vacant ticked; HR copy unticked.
- **AC-10** Start from lists "The top: {title}" (one top) or "The top of what you can see ({n}
  seats)" (several tops), then every seat that has seats under it, in tree order, with "— " before
  it once per level below the top. `F-DTC90`: 6 options (the top and the 5 leads). A seat with
  nobody under it is never listed.
- **AC-11** For a start with `d` levels (counting the start), Levels lists "2 levels: {the top |
  seat title} and the {n} seats under it", then "3 levels" … "{d−1} levels", then "All {d} levels:
  every seat ({s} seats, {p} people)". `F-DTC90` from the top: exactly two options, the second "All 3
  levels: every seat (90 seats, 363 people)". A start with only one level under it offers only the
  "All" option. Changing Start from resets Levels to its first option. The words "head of department"
  appear nowhere (D3).
- **AC-12** Paper is five radios A4, A3, A2, A1, A0. Choosing one changes the hint to "{paper} is
  {w} × {h} mm." with: A4 210 × 297, A3 297 × 420, A2 420 × 594, A1 594 × 841, A0 841 × 1189.
- **AC-13** Given the Branch filter set to Noida, then the panel says "Your Branch filter does not
  apply here. The wall chart uses only the choices below." and the counts are those of all 90 seats.
  With Branch and Job role set: "Your Branch and Job role filters do not apply here. The wall chart
  uses only the choices below." With no filter: no such sentence.
- **AC-14** People note. Given `unseated` with 82 people and rows across several branches: "82 active
  people are not in any seat, so they are not on the chart. Placing them in a seat first is
  recommended, not required." and a link "See who is not in a seat" that opens the existing "In no
  seat" tray. Given rows in one branch (e.g. Pitampura): "35 active Pitampura people are not…".
  Given `unseated` absent: "Only people placed in a seat are on the chart." and no link. Given 0
  people in no seat: no people note at all (D-5, pending Surbhi, Q6).
- **AC-15** With HR copy off, the panel shows "Only seat names, job titles, departments and people's
  names print. Flags, leaving dates and HR notes never do." (D-7, approved) and the intro "A chart of
  seats and names for a wall, sized for the paper you choose." With HR copy on, see AC-62.
- **AC-16** Start from, Levels, Paper, Sheets and Show Vacant stay as set if the panel is closed and
  opened again on the same page visit. After a page reload they are back to the defaults. If the
  chosen start seat is no longer in the rows, Start from goes back to the top. **HR copy is the
  exception: it is unticked every time the panel opens** (AC-58).
- **AC-17** Scope note (blue). Rows across several branches → "Covers {n} branches: {names,
  comma-separated, A to Z}." (D-1, approved). `F-DTC90` with 6 branches: "Covers 6 branches: {six
  names}." Rows in one branch → see AC-48. The words "whole company" appear nowhere in the panel or on
  paper.

### US-4 · The paper

- **AC-18** Each box shows the seat title; the designation on the next line when it differs from the
  title (case-sensitive text compare `[ASSUMPTION]`); "{branch} · {department}" on the next line,
  leaving out an empty part (not on the starting box; branch only if AC-32 keeps it); every name, one
  per line, in `ceil(names ÷ 10)` columns, at most 4; box width 200 px plus 140 px for each extra
  column. `F-DTC90` "Back Office" (36 people): 4 columns, all 36 names.
- **AC-19** With Show Vacant on, a seat with nobody in it shows `Vacant` in italics. The words "Nobody
  in this seat", "to fill" and "open" never print.
- **AC-20** On the last level drawn, a box with seats under it shows "{n} seats · {p} people below",
  with "1 seat" and "1 person" when singular (D-4, pending Surbhi, Q6). A box with nothing under it has no such
  line. With "All", no box has it.
- **AC-21** Counts. `F-DTC90`, top, All: 90 boxes before grouping, 363 name lines, and 363 = the sum
  of people in the seats. `F-DTC90`, top, 2 levels: 23 boxes. `F-GROUP` (D-6, pending Surbhi, Q5): the first
  three Cashiers print as **one** box "Cashier" with 3 names and no `Vacant`; the three empty Cashiers
  in the other branch print as one box with `Vacant`. Seats with seats under them are never grouped.
  The paper groups exactly as the screen's `posGroupSiblings` does, ignoring `POS.ungrouped`.
- **AC-22** A run of 3 or more seats with nobody under them, under one manager, prints as several
  columns side by side joined by a bar, each box with a tick from the line. Under a row of team leads
  the run may spread to 2–5 rows across their width. The 064 connector check run on the print DOM for
  `F-DTC90` at 2 levels and at All finds 0 false and 0 missing links.
- **AC-23** Given the dark theme, the paper's background is white and its text `#2D2622` in the print
  DOM's computed styles. The starting box has a 2 px `#5B4B8A` border.
- **AC-24** Given Start from = "Back Office Manager", Levels = All, then exactly 11 boxes and 72 names
  print, the starting box has no branch line, and nothing above or beside it prints.
- **AC-25** A seat with status Frozen prints like any other seat, with no "Frozen" word. A seat whose
  manager is Closed (not sent by the server) prints as a top.
- **AC-26** Given the screen at zoom 60 %, arranged "By department", one group opened with "Show the
  N", and a seat folded, when the wall chart is drawn for top/All, then its print DOM is identical to
  the one drawn with the screen at its defaults. The paper always follows reporting lines.

### US-5 · Nothing private reaches paper (PRIV-1) — the test runs twice

Sentinel payload for both runs: `F-DTC90` with `employee:"EMP-SNTL"`, `assignment:"ASG-SNTL"`,
`grade:"GRADE-SNTL"`, `hired_on:"HIRED-SNTL"`, `type:"TYPE-SNTL"`, `weight:50`, `covering:true`,
`leaving:"2099-01-01"` on one person, `leaving:"2026-11-30"` on another, `leaving_on`, `key:true`,
`opening:"OPEN-SNTL"`, `status:"Frozen"`, `image:"IMG-SNTL"`, `plan:{note:"PLAN-SNTL",
set_by:"WHO-SNTL", reason:"REASON-SNTL"}`, `plans:{…}`, `unseated:[{name:"UNSEATED-SNTL"}]`,
`designation:"DESIG-OK"`, `department:"DEPT-OK"`, and `#sb-name` = `PRINTER-SNTL`. "All" from the
top is drawn.

- **AC-27a** (blocking, CI) **HR copy off.** The print DOM holds: no sentinel string (`EMP-SNTL`,
  `ASG-SNTL`, `GRADE-SNTL`, `HIRED-SNTL`, `TYPE-SNTL`, `OPEN-SNTL`, `IMG-SNTL`, `PLAN-SNTL`,
  `WHO-SNTL`, `REASON-SNTL`, `UNSEATED-SNTL`, `PRINTER-SNTL`); no `2099`; no "leaving"; no "1 Jan";
  no "30 Nov"; no "Job opening"; no "HR use only"; no `Frozen`; no "covering"; no `<img`; no element
  matching `.oc-flag`, `.oc-tag`, `.oc-toggle`, `.av`, `.pos-nomgr`, `.private`, `[data-private]`.
  Printed names = 363. `DESIG-OK` and `DEPT-OK` **do** appear (allowed, Surbhi 24 Oct 2026).
- **AC-27b** (blocking, CI) **HR copy on.** The print DOM holds: "leaving 30 Nov" after that
  person's name and "leaving 1 Jan" after the other; "Job opening raised" on the seat with the
  opening; "HR use only - not for display" at the top and foot of the sheet. It still holds **none**
  of the sentinel strings listed in AC-27a (so not `OPEN-SNTL` and never `PLAN-SNTL`, `WHO-SNTL` or
  `REASON-SNTL`), no `2099`, no `Frozen`, no "covering", no `<img` and none of the listed elements.
  Printed names = 363.
- **AC-28** The copy handed to the print drawing has, on every seat, exactly the keys in §5's allowed
  list for the mode in use and no others: with HR copy off, no `leaving` on any name and no
  `opening` key; with HR copy on, `opening` is `true` or `false`, never a string.
- **AC-29** The guard is shown to fail: with `employee` deliberately copied into the copy, AC-27a,
  AC-27b and AC-28 fail. Recorded in `04-test-report.md`, then undone.

### US-6 · Name size, warning, speed

- **AC-30** One sheet: the result line reads "{paper} {landscape|portrait} · one sheet · names at {pt}
  pt", where pt = names' 13 px × 0.75 × scale, rounded down; scale = the smaller of (printable width ÷
  chart width) and (printable height ÷ chart height); printable = paper minus 10 mm on each side and
  minus 8 mm more in height for the footer, and with HR copy on, minus the top banner's measured
  height as well; 96 px to the inch. Landscape when the chart is at least as wide as it is tall. Chart
  size is measured from the boxes as drawn with the current ticks.
- **AC-31** Under the result line, the reading words: under 8 pt "Too small to read."; 8 to under 10
  "Readable close up."; 10 to under 14 "Readable at arm's length."; 14 and over "Readable from about a
  metre away." Then "{s} seats · {p} people" for the chosen start and levels.
- **AC-32** **Kill-line re-measure (before US-4 is called done).** The engineer draws `F-DTC90`, All,
  one sheet, with the full box (title, designation when different, "{branch} · {department}", names),
  Show Vacant on, HR copy off, and records the name size on A3 (2 levels), A1 (All) and A0 (All),
  within ±1 pt, in `04-test-report.md`. Then:
  - All on A1 **8 pt or more** → the branch stays on the box. AC-32, AC-33 and the design's sizes take
    the measured numbers.
  - All on A1 **under 8 pt** → remove the branch from the box (department stays) and measure again.
    If now 8 pt or more, build without the branch and tell Surbhi the numbers. If still under 8 pt,
    **stop — the brief's kill line is hit**; bring Surbhi the numbers before building more.
  - The same three figures are also recorded with HR copy on, for information. The HR copy is not
    held to the kill line; the warning (AC-33) covers it.
  Reference figures without designation and department (prototype): 2 levels on A3 13 pt; All on A1
  9 pt; All on A0 13 pt.
- **AC-33** `F-DTC90`, All, A3, one sheet: the result box is amber and reads "Warning: that is too
  small to read on a wall." with buttons "Use {paper} (names at {pt} pt)" (the first larger paper that
  reaches 8 pt; A1 in the prototype) and "Use {n} A3 sheets" (prototype 9, ±2). The first sets Paper;
  the second sets Sheets to several. If no paper reaches 8 pt, only the sheets button shows. The word
  "Warning:" is text, not only colour.
- **AC-34** The result box has `role="status"` and `aria-live="polite"`.
- **AC-35** Changing Paper or Sheets updates the result line within 300 ms. Changing Start from,
  Levels, Show Vacant or HR copy on `F-DTC90` shows either the final result line or "Working out the
  size…" within 300 ms, and the final line after. Measured with Playwright, median of 5 changes, on the
  engineer's laptop; the numbers are reported, not rounded off. If "Open print preview" is pressed
  while working, the print opens once the size is ready.
- **AC-36** Choosing a bigger paper never makes the stated name size smaller.

### US-7 · Print preview, file name, footer, clean-up (SEC-4, PRIV-2)

- **AC-37** When "Open print preview" is pressed, then exactly one added `<style>` sits after the
  portal's global rule and contains `@page{size:{w}mm {h}mm;margin:10mm}` matching
  `size:\s*\d+mm \d+mm` — never the words A0–A4. A1 landscape = `841mm 594mm`; A0 portrait = `841mm
  1189mm`. Then `window.print()` is called once.
- **AC-38** While printing with HR copy off, `document.title` = "Wall chart - {Company} - {n levels |
  all levels} - {paper} - {yyyy-mm-dd}", the date being the server's `as_at`, e.g. "Wall chart - DTC -
  all levels - A1 - 2026-10-24" (D-9, approved). It matches
  `^Wall chart - .+ - (\d+ levels|all levels) - A[0-4] - \d{4}-\d{2}-\d{2}$` and holds no person's
  name, no seat title and not `PRINTER-SNTL`. ("all levels" when the deepest Levels option is chosen.)
- **AC-39** When `afterprint` fires, or when the panel is closed without printing, then the added
  style is gone, `document.title` is back to what it was, and a later Ctrl+P prints the screen chart
  (AC-3), not the wall chart.
- **AC-40** While the wall chart prints, only the wall chart is visible in print media: no navbar,
  sidebar, tiles, filters, panel or screen chart. On screen the wall chart container is never visible.
- **AC-41** Every sheet carries a 9 pt footer: "{Company} · {scope words} · {all levels | n levels}
  from {the top | start seat title} · as at {d Mon yyyy} · {p} people in seats". Scope words: "{n}
  branches" or "{branch} branch" (D-1, approved). The date is the server's `as_at`. No "printed by".
  With `F-DTC90` the footer does not contain `PRINTER-SNTL`.
- **AC-42** (manual, Chrome and Edge on Windows) For each of A4, A3, A2, A1 and A0, Save as PDF gives
  a PDF whose page is the chosen size in mm (either way round, per AC-30). The PDF's properties show
  Title = the file name and no Author. Then a payslip printed in the same tab comes out as it did
  before this slice.
- **AC-43** (manual, Safari on iPhone) Print A1 and record whether the page size was honoured. If
  not, Surbhi decides Q4. The AC passes when the result is recorded in `04-test-report.md`.
- **AC-44** After the print window closes, the panel is still open.

### US-8 · Several sheets

- **AC-45** Given Sheets = several and one sheet would be under 10 pt, then the result line reads
  "{paper} {orientation} · {n} sheets ({c} across, {r} down) · names at 10 pt", with scale = 10 ÷
  9.75, c = chart width × scale ÷ printable width rounded up, r likewise. `F-DTC90` All on A3: 9
  sheets, 3 across, 3 down (±2 sheets; re-measured per AC-32).
- **AC-46** The print has n pages. Page k shows the part of the chart at row r, column c; side by
  side the pages cover the whole chart with no gap and no overlap. Each footer adds " · Sheet {k} of
  {n} (row {r}, column {c})". No join marks (D8).
- **AC-47** Given Sheets = several and one sheet at this paper is 10 pt or more, then it prints as one
  sheet and the second line reads "It fits on one sheet at this size, so it prints as one." followed
  by the reading words.

### US-9 · The Owner's print (SEC-1)

- **AC-48** Given `F-OWNER`, the scope note reads "You can see 1 branch, Pitampura, so the chart
  covers Pitampura only. Its seats report to managers in other branches, so they print side by side
  with no lines above them." Start from has one option, "The top of what you can see (8 seats)";
  Levels has one option, "All: 1 level, 8 seats side by side". The paper shows 8 boxes in a grid with
  no lines above them. Footer scope words: "Pitampura branch".
- **AC-49** Given `F-OWNER`, the printed names equal the people in his 8 seats and nothing else; no
  seat outside the payload appears.
- **AC-50** (D-3, approved) Given several tops of which at least one has seats under it (e.g.
  `F-DTC90` plus one HR-view seat with no manager and 2 seats under it), each top prints side by side
  with its own seats under it, to the chosen levels, and the 064 connector check finds 0 false and 0
  missing links. Levels counts from the tops. When no top has seats under it, the result is AC-48's
  grid.

### US-10 · No print for heads of department or employees (SEC-2)

- **AC-51** Given a user with no Read on `Alvoraa Position`, the existing refusal of
  `position_table` (slice 064 SEC-8 test) still passes, and the page shows no Positions panel and no
  button.
- **AC-52** (switch-on C2) Before DTC gets the release, someone with access lists every role with Read
  on `Alvoraa Position` at DTC, in the release note. No head-of-department or employee role is on it.

### US-11 · Staff told first (PRIV-3, C1, C3)

- **AC-53** The release note to DTC carries the PRIV-3 text word for word, with the date filled in.
  DTC's written confirmation is filed in this slice folder, and counsel's answer to `01c` Q1 is
  recorded, before the feature is handed to DTC.
- **AC-54** When slice 065 merges, `test_replacement_plan_065.py:830` and `:857` still pass and the
  AC-27a and AC-27b fixture still carries the `plan` keys.

### US-12 · "Show Vacant" tick

- **AC-55** Given any reader with the button, the panel shows a checkbox "Show Vacant" in an "On the
  paper" group placed after Sheets and before the result box (D-8). It is ticked the first time the
  panel opens on a page visit, and keeps its state per AC-16.
- **AC-56** Given `F-DTC90`, All, with Show Vacant **off**, then the word "Vacant" appears nowhere in
  the print DOM; the number of boxes is the same as with it on; each empty seat still shows its title,
  designation line and "{branch} · {department}" line. With it on, AC-19 holds. `F-GROUP` with it off:
  the empty Cashier group still prints as one box, with no "Vacant".
- **AC-57** The tick never changes Ctrl+P's screen print (AC-3).

### US-13 · "HR copy: show replacements" tick

"Replacement" means a seat being re-filled: the person in it is leaving, or a job opening was raised
on it (Surbhi, 24 Oct 2026). Slice 065 replacement plans never print.

- **AC-58** Given `may_see_leaving: true`, the "On the paper" group also shows a checkbox "HR copy:
  show replacements", **unticked every time the panel opens**, including when it was ticked and the
  panel was closed and opened again on the same page visit.
- **AC-59** Given `F-DTC90` with HR copy on, then: the person with `leaving:"2026-11-30"` prints as
  "{name} · leaving 30 Nov"; the seat with an opening shows "Job opening raised" on its own line under
  the names (or under "Vacant"); nothing else is added. A grouped box (D-6) shows "Job opening raised"
  once if one of its seats has an opening, or "{k} job openings raised" if k > 1 `[ASSUMPTION]`.
  "covering", "key seat", "Frozen", "%", "to fill", the opening's ID and any plan data never print.
- **AC-60** Given HR copy on, every sheet — the one sheet, or each of the n sheets of AC-46 — carries
  "HR use only - not for display" at the top, in at least 9 pt bold, and at the start of the footer.
  With HR copy off, the words appear nowhere.
- **AC-61** Given HR copy on, during print `document.title` = "HR copy - Wall chart - {Company} -
  {n levels | all levels} - {paper} - {yyyy-mm-dd}", e.g. "HR copy - Wall chart - DTC - all levels -
  A3 - 2026-10-24". It matches `^HR copy - Wall chart - .+ - (\d+ levels|all levels) - A[0-4] -
  \d{4}-\d{2}-\d{2}$` and holds no person's name. With HR copy off, it starts "Wall chart - " (AC-38).
- **AC-62** Given HR copy on, the panel shows "Print in the office, not at a print shop." and the
  privacy line reads "This HR copy also prints leaving dates and job openings. Replacement plans and
  HR notes never print." `[ASSUMPTION — wording, Q16]`. With HR copy off: the office note is absent
  and the privacy line is AC-15's.
- **AC-63** Given HR copy on, Sheets = several, then the footer of every sheet starts "HR use only -
  not for display ·" before AC-46's sheet label.
- **AC-64** Turning HR copy on or off re-works the name size from the boxes as drawn, within AC-35's
  timing. On `F-DTC90`, All, A1, the name size with HR copy on is never larger than with it off.

### US-14 · No HR copy without leaving dates

- **AC-65** (blocking, CI) Given `F-NOLEAVE` (`may_see_leaving: false`), when the panel opens, then
  there is **no** "HR copy" checkbox in the DOM (absent, not hidden), no office-print note, and the
  print DOM is identical to the HR-copy-off print of the same payload. A second run with
  `may_see_leaving: false` but a `leaving:"2099-01-01"` value forced into the fixture still prints no
  "leaving" and no "1 Jan".

## 9 · Prototype parity table

Every feature and state in `prototype-v1.html`. "Same" means build exactly as drawn. Every difference
below has Surbhi's yes (24 Oct 2026) **except D-4, D-5 and D-6, which are still being asked** (Q5, Q6).

| # | Prototype feature or state | Story | Given / When / Then | Parity |
|---|---|---|---|---|
| P1 | Toolbar button "Download wall chart (PDF)", outline, before "+ Add a seat" | US-2 | AC-4 | Same |
| P2 | Phone: button full width, 44 px | US-2 | AC-5 | Same |
| P3 | Panel in the tray: heading, Close, focus on heading; drawer / bottom sheet | US-2 | AC-6 | Same |
| P4 | Escape, scrim, Close → focus back to button | US-2 | AC-7 | Same |
| P5 | Intro sentence | US-3 | AC-15 | Same |
| P6 | Scope note for HR: "Covers the whole company: {n} branches." | US-3 | AC-17 | **D-1 — "Covers {n} branches: {names}". Approved 24 Oct 2026** |
| P7 | Scope note for the Owner (two sentences) | US-9 | AC-48 | Same |
| P8 | Filter note | US-3 | AC-13 | Same (adds the plural for two filters, from design §6) |
| P9 | Start from options, indented with "— " | US-3 | AC-10 | Same |
| P10 | Levels options, default 2, reset when Start changes | US-3 | AC-11 | Same |
| P11 | Paper chips A4–A0 and mm hint | US-3 | AC-12 | Same |
| P12 | Sheets radios with their hints | US-3 | AC-9 | Same |
| P13 | Result line, reading words, seats · people | US-6 | AC-30, AC-31 | Same |
| P14 | Warning state with "Use {paper} (names at {pt} pt)" and "Use {n} {paper} sheets" | US-6 | AC-33 | Same (numbers re-measured, AC-32) |
| P15 | "It fits on one sheet at this size, so it prints as one." | US-8 | AC-47 | Same |
| P16 | People note with count and "See who is not in a seat" | US-3 | AC-14 | Same. The link opens the existing tray (the prototype's link did nothing) |
| P17 | Privacy line | US-3 | AC-15, AC-62 | **D-7 — wording adds "job titles, departments". Approved 24 Oct 2026.** HR copy wording: D-8 |
| P18 | "Open print preview" and its hint | US-7 | AC-37 | Same |
| P19 | Box: title, branch (not on the top box), names in up to 4 columns of 10, Vacant | US-4 | AC-18, AC-19 | **D-7 — adds designation (only when different) and department. Approved 24 Oct 2026. Branch stays if AC-32 passes** |
| P20 | "{n} seats · {p} people below" on the last level | US-4 | AC-20 | **D-4 — "1 person" for one (prototype says "1 people"). Pending Surbhi (Q6)** |
| P21 | No flags, tags, avatars, toggles on paper | US-5 | AC-27a | Same |
| P22 | Wrapped columns with a bar; wider spread under the leads | US-4 | AC-22 | Same |
| P23 | Starting box with a 2 px purple border | US-4 | AC-23 | Same |
| P24 | Paper always light | US-4 | AC-23 | Same |
| P25 | Orientation chosen for the person | US-6 | AC-30 | Same |
| P26 | Preview side panel: Save as PDF, paper, layout, pages, file name | US-7 | AC-37, AC-38, AC-42 | Same — in the product this is the browser's own window; we set the size and file name only |
| P27 | Footer on the sheet | US-7 | AC-41 | Same, except scope words (D-1) |
| P28 | Several sheets, clipped, "Sheet k of n (row r, column c)" | US-8 | AC-45, AC-46 | Same |
| P29 | Owner: tops side by side, "All: 1 level, 8 seats side by side" | US-9 | AC-48 | Same |
| P30 | Several tops: only the top boxes are drawn | US-9 | AC-50 | **D-3 — each top with its own seats (same result when tops have nobody under them). Approved 24 Oct 2026** |
| P31 | The zoom row still has "Print" | US-1 | AC-1 | **D-2 — replaced by the panel. Approved 24 Oct 2026** |
| P32 | Screen chart with flags and the HR box on screen | US-1 | AC-3, AC-3a | Unchanged on screen. **Ctrl+P prints it with flags, tags and the HR box hidden, and no "printed by"** (Surbhi, 24 Oct 2026) |
| P33 | "Show at printed size" button and "Saved (sample)" toast | — | — | Review aid only. Not built |
| P34 | Dark review bar (Person, Device, Theme, Jump to) | — | — | Review aid only. Not built |
| P35 | File name "Wall chart - … - 24 Oct 2026" | US-7 | AC-38 | **D-9 — date as 2026-10-24. Approved 24 Oct 2026** |
| — | **Not drawn in the prototype** | | | |
| P36 | "Working out the size…" (design §5) | US-6 | AC-35 | From the approved design |
| P37 | No "in no seat" list (design §5) | US-3 | AC-14 | From the approved design |
| P38 | 0 people in no seat → no people note | US-3 | AC-14 | **D-5 — pending Surbhi (Q6)** |
| P39 | Identical sibling seats grouped into one box | US-4 | AC-21 | **D-6 — pending Surbhi (Q5)** |
| P40 | "On the paper" group: "Show Vacant", "HR copy: show replacements"; office note; HR banner; "HR copy -" file name | US-12, US-13, US-14 | AC-55 – AC-65 | **D-8 — the ticks are approved (brief "Decisions (2)" option A, 24 Oct 2026). Their place in the panel and the wording "Job opening raised" and the HR privacy line are my proposal (Q16)** |

## 10 · Edge cases

| Case | What happens | AC |
|---|---|---|
| Vacant seat | `Vacant` (Show Vacant on), nothing (off). The box always prints. No "to fill" (D4) | AC-19, AC-56 |
| Empty seat with seats under it, Show Vacant off | Box and title print; the tree stays joined | AC-56 |
| Multi-person seat partly filled (3 seats, 1 person) | The one name prints. Nothing says it is partly empty | AC-19 |
| Vacant seat with an opening, HR copy on | "Vacant" (if on) then "Job opening raised" | AC-59 |
| Filled seat with an opening (someone leaving, replacement advertised), HR copy on | Name · leaving {d Mon}, then "Job opening raised" | AC-59 |
| Grouped seats, one with an opening | "Job opening raised" once on the group box | AC-59 |
| Grouped seats, one person leaving, HR copy on | That name carries "· leaving {d Mon}"; the others do not | AC-59 |
| Leaver on notice, HR copy off | Name prints; the leaving date never does | AC-27a |
| Leaving date outside the reader's reporting line | Server sends `leaving: null`, so nothing prints, even on the HR copy | AC-65 |
| DTC today: 0 future leavers | HR copy shows only openings; still carries the banner | AC-60 |
| Reader not sent leaving dates | No HR copy tick | AC-65 |
| HR copy ticked, panel closed and reopened | Unticked | AC-58 |
| 82 people in no seat | Not printed. Count on screen only, in the panel | AC-14 |
| 0 people in no seat | No people note | AC-14 |
| 363 people at All | 90 seats, 363 names; sizes re-measured | AC-21, AC-32 |
| 36 people in one seat | 4 columns of 9 | AC-18 |
| 41 or more in one seat | 4 columns, more than 10 rows each | AC-18 |
| Same person in two seats (two part-time assignments) | Printed in both boxes and counted twice in "people in seats" `[ASSUMPTION]` — the count is name lines | AC-21 |
| Joiner today | Shows if the assignment's start date is today or earlier (server rule) | — |
| Leaver past last day | Not sent by the server once the assignment has ended | — |
| Seat reporting in a circle | Not reachable from a top, so not printed, as on screen. The seat Doctype refuses circles | — |
| Very deep chain | Stops at 40 levels, as the screen does (`POS_MAX_DEPTH`) | — |
| Seat whose manager is Closed | Prints as a top | AC-25 |
| Seat with no manager, HR view | Prints as an extra top beside the real one, with its own seats under it (D-3) | AC-50 |
| Frozen seat | Prints with no label | AC-25 |
| Filter, fold, zoom, view, "Show the N" on screen | All ignored by the paper | AC-13, AC-26 |
| HR for two companies | Tops of both print side by side; footer and file name list both company names, comma-separated `[ASSUMPTION]` | — |
| Pitampura has two branch records | Two branch names appear in the scope note. Data fix before first print (brief risk) | AC-17 |
| 900 seats (10× DTC) | All on A0 goes under 8 pt; warning offers sheets or the user picks fewer levels | AC-33 |
| Layout slower than 300 ms | "Working out the size…" | AC-35 |
| Cancel in the print window | Clean-up runs | AC-39 |
| `afterprint` never fires (some phone browsers) | Clean-up runs when the panel closes | AC-39 |
| iPhone Safari | Page size may be ignored. Tested and recorded | AC-43 |
| Firefox | Not tested in this slice `[ASSUMPTION]` Chrome and Edge are what DTC uses | — |

Not relevant here: half-days, balances, holidays, time zones beyond the server's `as_at`, approvals.

## 11 · Non-functional requirements for this slice

| Item | Number |
|---|---|
| Record volume | DTC: 90 seats, 363 people. Test at 10×: 900 seats |
| New server calls | **0**. No new query, no new payload byte |
| Result line after a change | ≤ 300 ms, or "Working out the size…" within 300 ms (nfr-budget §2). Prototype measured 0.9–2.5 s for its trial-and-error search. **Recommendation:** work out rows per column from measured box heights rather than drawing many layouts |
| Print window opening at DTC size | Under 2 s on a laptop (brief §9). `Needs validation` |
| PDF size | Under 1 MB at All on A1 `[ASSUMPTION]`, checked by hand in AC-42 |
| Background job, cache, queue | None |
| Retention in the system | Nothing stored |
| Personal data | Names next to seat titles (wall copy). Leaving dates as well (HR copy only). Protected by the allowed list (PRIV-1) and the `may_see_leaving` gate |
| DevOps `OPS` items | None — `07` §1–3 **waived by Surbhi 24 Oct 2026** (client-side print only). DevOps still writes `07` §5 release readiness as usual |

## 12 · Data migration and backfill

**Nothing.** No field, no record, no setting. Rollback: revert the commit; nothing to undo in data.
Data fixes at DTC (seats under the wrong manager, the two Pitampura branch records, placing unseated
people) are recommended before the first print, but they are HR's work, not this slice's.

## 13 · Notifications and messages

**No email, notification or toast.** Every on-screen and on-paper word is in §8 and design §6.

## 14 · Localisation and accessibility

- Every panel string, and every word the paper adds ("Vacant", "leaving", "Job opening raised", "HR
  use only - not for display"), goes through the portal's `drT` (confirmed at `portal.js:7371`).
  Paper names (A4–A0) and "mm" are not translated.
- English only for now (Q9 default). Positions is English-only today.
- Dates: footer "24 Oct 2026"; leaving "30 Nov" (the screen's `posDay`); file name "2026-10-24".
  Counts as plain numbers.
- Panel: native selects, radios and checkboxes, all labelled; visible focus ring; Escape closes; focus
  returns. Result is a polite live region. Warning says "Warning:" in words. On a phone, targets
  44 px; on desktop 24 px; screen text 12 px or more (the paper is not held to the screen rule).
- Frontline workers: nothing changes on their phones.

## 15 · Audit and traceability

Nothing is recorded. The PDF is made in the browser, so no server log exists. **Residual risk R1 in
`01c` — nobody can tell who printed the company chart, or an HR copy — was accepted by Surbhi on
24 Oct 2026.** R2 (a leaver whose HR login was never removed can still open Positions) was accepted by
Surbhi on the same date; it is offboarding's job. The footer's "as at" date lets anyone tell how old a
copy is; the banner tells anyone that a copy on a wall is an HR copy that should not be there.

## 16 · Compliance-impact sub-analysis

I am not a lawyer. Nothing below is a legal ruling.

### 16.1 Data touched

| Field | Class | Purpose | Lawful basis (as recorded) | New collection? |
|---|---|---|---|---|
| Person's name | internal (personal, directory) | Show who sits where | DPDP s.7(i) employment, **unconfirmed** (01c Q1) | No |
| Seat title, designation, branch, department | internal | Same | Same | No (already on the screen box) |
| Leaving date (HR copy only) | sensitive | HR plans who to replace | Same, **unconfirmed** | No (already on HR's screen) |
| "Job opening raised" (HR copy only) | internal | Same | Same | No |
| Company, date, counts | not personal | Read the chart | — | No |

### 16.2 Obligations engaged

| Obligation | Source | What this slice must do | Feature that does it |
|---|---|---|---|
| DPDP minimisation | Baseline §2 | Print only names and titles; leaving dates only on a marked HR copy for readers who already see them | PRIV-1 allowed list (AC-27a, AC-27b, AC-28), gate (AC-65) |
| DPDP notice | Baseline §2 | Staff told before names go up | PRIV-3 release note (AC-53). Compliance map G1 (in-product notice) is not this slice |
| CERT-In, ISO, GDPR, AI Act | Baseline | Not engaged | — |

### 16.3 Visibility delta

**New:** people with no login (visitors, staff) can read names and seat titles on a wall. **New:** a
paper HR copy can show leaving dates and openings to anyone who sees it, if HR mishandles it.
**Not new:** nobody in the system sees anything they could not see before.
**Must not:** leaving dates on a wall copy or a Ctrl+P print; IDs, grades, plans, the unseated list
or the printer's name on any paper; heads of department and employees cannot print; the Owner cannot
print beyond his branch; a reader without leaving dates cannot make an HR copy.

### 16.4 Decision automation

None. The panel suggests a paper size; a person chooses. The HR copy shows facts already decided
(a leaving date, an opening); it does not decide anything.

### 16.5 Retention and deletion

Nothing stored in the system. Paper and PDF copies are DTC's to manage; the PRIV-3 note says old
copies come down when a new one goes up. An erasure request cannot reach a printed sheet; HR reprints.
An HR copy shows a leaving date that will be out of date once the person leaves; the banner and the
"as at" date are the only guard. **Risk:** HR copies kept in a drawer outlive the leaver. DTC's
handling, via the release note.

### 16.6 Open compliance questions

| Question | Who decides | What it blocks |
|---|---|---|
| Is a names-and-titles wall chart seen by visitors covered by DTC's employment basis with the PRIV-3 note? (01c Q1) | Counsel, via Surbhi | Switch-on at DTC, not the build |
| May slice 065 replacement plans ever appear on paper? Default: **never** | Counsel in writing, via Surbhi | Nothing in this slice; a later change only |
| A person asks not to be named: HR handles it by hand (01c Q2)? | Surbhi | Nothing now |

### 16.7 AI

No AI. Nothing prohibited is asked for.

## 17 · Traceability

| Source | Item | Story | ACs | Status |
|---|---|---|---|---|
| Brief D1 | Browser Save as PDF, A4–A0 | US-7 | AC-37, AC-42 | covered |
| Brief D2 | Four choices, result line, warning under 8 pt | US-3, US-6 | AC-9–12, AC-30–33 | covered |
| Brief D3 | 22 seats under the Owner at level 2, no HOD label | US-3 | AC-9, AC-11 | covered |
| Brief D4 | "Vacant", no "to fill" — now behind the Show Vacant tick | US-4, US-12 | AC-19, AC-55, AC-56 | covered |
| Brief D5 | No "printed by" (also on Ctrl+P, Q2) | US-7, US-1 | AC-38, AC-41, AC-3a | covered |
| Brief D6 | Never flags, leaving dates, HR box, private marks, plans, photos, phones, IDs — leaving dates allowed on the HR copy only (R3) | US-5, US-13 | AC-27a, AC-27b, AC-28, AC-29 | covered |
| Brief D7 | HR whole company; Owner his branch; HOD/employee none | US-9, US-10 | AC-48–52 | covered |
| Brief D8 | For a print shop; join marks only if cheap | US-8 | AC-46 | covered (no join marks) |
| Brief D9 | 82 unseated not printed; count on screen | US-3 | AC-14 | covered |
| Brief D10 | Global A4 rule left alone | US-7 | AC-37, AC-42 | covered |
| Brief Decisions (2) R1 | "Replacement" = seat being re-filled (leaving or opening) | US-13 | AC-59 | covered |
| Brief Decisions (2) R2 | 065 plans never print unless counsel says yes in writing | US-5 | AC-27b, AC-54 | covered |
| Brief Decisions (2) R3 | HR copy may show leaving dates | US-13 | AC-59 | covered |
| Brief Decisions (2) R4 | Vacant off removes the word only | US-12 | AC-56 | covered |
| Brief Decisions (2) R5 | HR copy gate = `may_see_leaving` (Owners included if sent) | US-13, US-14 | AC-58, AC-65 | covered |
| Brief Decisions (2) rules | Off on every open; banner top and foot; "HR copy -" file name; office note; never plans, notes, reasons, IDs | US-13 | AC-58, AC-60–63 | covered |
| Brief Decisions (2) checks | 8 pt worked out with the ticks; privacy test twice; no tick without `may_see_leaving` | US-5, US-6, US-14 | AC-27a, AC-27b, AC-64, AC-65 | covered |
| Brief bad news 4 | Today's Print leaks | US-1 | AC-1–3a | covered |
| Brief §6 test | No flag / HR box / private in print DOM; name count | US-5 | AC-27a | covered |
| Brief §11 | Every person in a seat in scope | US-4 | AC-21 | covered |
| Brief §11 | At least 8 pt or a warning | US-6 | AC-32, AC-33 | covered |
| Brief §12 | A filter would drop seats | US-3 | AC-13, AC-26 | covered |
| Brief §12 | Stale paper → "as at" date | US-7 | AC-41 | covered |
| Brief §12 | iPhone page size | US-7 | AC-43 | covered (test, then Q4) |
| Brief kill criterion | A1 under 8 pt | US-6 | AC-32 | covered (re-measure with full box; branch drops first) |
| Prototype | P1–P40 | see §9 | see §9 | covered; D-1 to D-3 and D-7 to D-9 approved 24 Oct 2026; **D-4, D-5, D-6 pending Surbhi** |
| Security | SEC-1 no new call, nothing stored | US-2, US-14 | AC-8, AC-65 | covered |
| Security | SEC-2 button follows the page | US-2, US-10 | AC-4, AC-51, AC-52 | covered |
| Security | SEC-3 old Print replaced by panel, Ctrl+P still prints, safely | US-1 | AC-1–3a | covered (AC-2 narrows test (a); security engineer to agree, Q12) |
| Security | SEC-4 mm page size, clean-up | US-7 | AC-37, AC-39, AC-42 | covered |
| Privacy | PRIV-1 allowed-field copy (name, designation, Vacant, counts, seat and department titles, branch; HR copy words) — sentinel test twice | US-5, US-12, US-13 | AC-18, AC-27a, AC-27b, AC-28, AC-29 | covered (`01c` to be updated, Q13) |
| Privacy | PRIV-2 file name, footer, metadata | US-7, US-13 | AC-38, AC-41, AC-42, AC-61 | covered (date 2026-10-24, matches `01c`'s pattern) |
| Privacy | PRIV-3 staff told | US-11 | AC-53 | covered (release check) |
| Security | Switch-on C1 / C2 / C3 | US-11, US-10 | AC-53, AC-52, AC-54 | covered |
| Security | R1, R2 residual risk | — | — | **accepted by Surbhi, 24 Oct 2026** |
| DevOps | OPS items | — | — | **not adopted: `07` §1–3 waived by Surbhi 24 Oct 2026** (client-side print only) |

## Open questions

None blocks the build start. Closed on 24 Oct 2026 by Surbhi: Q1 (D-1), Q2, Q3 (D-3), Q7 (R1, R2
accepted), Q10 (DevOps waived), Q11 (date 2026-10-24), Q14 (keep branch if AC-32 allows; designation
only when different), Q15 (Ctrl+P prints the screen chart).

| # | Question | Owner | Blocks | My recommendation / default |
|---|---|---|---|---|
| Q5 | **D-6.** The screen already merges identical seats side by side (same title, branch and department, nobody under them) into one box. Do the same on paper? | Surbhi | AC-21 box count; US-4 done | Yes |
| Q6 | **D-4.** Write "1 person below", not the prototype's "1 people below"? **D-5.** When every active person is in a seat, show no people note at all? | Surbhi | AC-20, AC-14 wording | Yes to both |
| Q12 | SEC-3 test (a) skips the Team notes pop-ups (`portal.js:8754`, `:8775`); agree AC-2's narrower scope? | Security engineer | AC-2 | Yes |
| Q4 | If iPhone Safari ignores the page size, add "Use a laptop for sizes above A4" on iPhone? | Surbhi, after AC-43 | Phone path only | Test first |
| Q8 | Counsel's answer on names on a wall (01c Q1) | Counsel via Surbhi | Switch-on at DTC, not the build | Do not hand to DTC until answered |
| Q9 | Hindi copy for the panel — needed now? | Surbhi / UX designer | Nothing now | English now; Positions is English-only today |
| Q13 | Edit `01c` to match: allowed list (designation, department, HR copy words), sentinel test twice, "HR copy -" file-name pattern, SEC-3 option removed | Security engineer | Security review at `06`, not build start | As written in this spec |
| Q16 | Wording and place for the new parts: "On the paper" group after Sheets; "Job opening raised"; the HR copy privacy line (AC-62); "{k} job openings raised" on a grouped box | UX designer (Surbhi if changed) | Nothing — build as written unless changed | As written in AC-55, AC-59, AC-62 |
| Q17 | The brief's option A folded "covering" into the HR copy; Surbhi's definition of replacement does not mention it. Leave "covering" off the HR copy? | Surbhi | Nothing — default is off | Off. Add later only if DTC asks |

## Assumptions

- `[ASSUMPTION]` The prototype's invented data has DTC's real shape; re-count before building (brief).
- `[ASSUMPTION]` DTC's names are about as long as the invented ones, so sizes hold to about 1 pt.
- `[ASSUMPTION]` Chrome and Edge honour a millimetre `@page` size added after the global rule
  (verified headless by security for Edge; interactive check is AC-42).
- `[ASSUMPTION]` "People in seats" counts name lines; a person in two seats counts twice.
- `[ASSUMPTION]` A Frozen seat belongs on the wall like any seat (01c Q3 default).
- `[ASSUMPTION]` HR across two companies is rare; footer lists both names.
- `[ASSUMPTION]` DTC uses Chrome or Edge on a laptop; Firefox is not tested.
- `[ASSUMPTION]` Designation is compared with the title as exact text to decide whether to print it.
- `[ASSUMPTION]` A grouped box with several openings says "{k} job openings raised".
- `[ASSUMPTION]` Surbhi's answers relayed by the lead session on 24 Oct 2026 count as her decisions;
  the brief's "Decisions 24 Oct 2026 (2)" header still says "waiting" and should be updated by its
  author to record them.

## Ready check (Definition of Ready)

| Box | Status |
|---|---|
| One named user, one outcome | Yes — HR gets a wall chart PDF (and an HR copy) |
| Job in the user's words, competitive analysis, Kano, WOW, out of scope | Yes (brief) |
| Brief approved | Yes — Decisions 24 Oct 2026 and Surbhi's answers to "Decisions (2)" on 24 Oct 2026 |
| Clickable prototype reviewed | Yes — approved by Surbhi; differences D-1 to D-3 and D-7 to D-9 approved. D-4, D-5, D-6 pending (Q5, Q6): wording or one AC each, built to the recommendation meanwhile |
| Feedback logged in `ux-learnings.md` | Yes — slice 069 entries (lines 88-90, 215-219). The two-ticks decision should be added by the UX designer at its next run |
| Every state designed | Yes. The iPhone fallback is decided after the AC-43 test (Q4) |
| `01c` written | Yes (rev 1). Edits for Surbhi's decisions due before review `06` (Q13) |
| `07` §1–3 written with OPS items | **Waived by Surbhi 24 Oct 2026** — client-side print only, no server change. The only waiver |
| Gap analysis, stories, ACs with oracles, traceability, permission matrix with negatives, edge cases, NFR numbers, migration, compliance section | Yes |
| Every compliance question has an owner | Yes |
| Nothing prohibited | Yes |
| Open questions do not block day one | Yes — none blocks the build |

**Verdict: ready for build.** Nothing is waived except DevOps `07` §1–3. Three things gate later
steps, not the start: Surbhi's answers on D-4, D-5, D-6 gate US-3 and US-4 being called done; the
AC-32 kill-line re-measure gates US-4 being called done; counsel's answer (Q8) gates handing the
feature to DTC.

## Subtract pass

**Removed in revision 2:** "covering" on the HR copy (her definition of replacement does not include
it; Q17); the opening's ID and link on paper (the words "Job opening raised" are enough); a separate
"keep HR copy ticked" memory (she said off every open); any change to `register.py` for the HR copy
(`may_see_leaving` already exists); a diagonal watermark (the banner does the job, brief); a named
successor (needs server code); a separate story for the Ctrl+P "printed by" fix (one line, folded into
US-1).

**Removed in revision 1, still out:** sorting names alphabetically inside a box; a disabled "Open
print preview" while working out the size; a panel note for seats in a reporting circle; Firefox
support; a server flag for "whole company"; join marks.

**Kept only because the requirement fails without it:** the allowed-list copy (PRIV-1); the wrapped
layout (design §4 numbers); the clean-up on close as well as `afterprint` (phones may not fire it);
the banner on every sheet of the HR copy (the only thing on paper that says "do not post this").

## Handoff note

To the engineer: build in story order; US-1 can ship alone. The paper is the screen's `ocNodeCard` /
`ocRender` drawing with print rules, fed by the allowed-list copy — never pass a row or person object
to the drawing, and never call `ocAvatar` for paper. Build the copy with only the keys for the mode in
use: the HR copy keys must not exist in the copy when the tick is off. Turn `opening` into true/false
when copying. Show the HR copy tick only when `POS.may_see_leaving` is true; do not add a role check
of your own. Group identical seats with the existing `posGroupSiblings`, ignoring `POS.ungrouped`.
Reuse `posSheet` for the panel and `posUnseatedSheet` for the link. Page size in millimetres only.
Meet 300 ms by working out the wrap from measured box heights, not by drawing many layouts. In
`posPrintHead` drop the "printed by {name} ({role})" part and keep the rest (AC-3a). Do the AC-32
re-measure as soon as the box draws, before the panel work — it can stop the slice. Do not touch
`register.py`.
