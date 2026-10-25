---
slice: 069-wall-chart-print
artifact: 02-design (the UX design and prototype; the agent file calls it 01b)
author: hrms-ux-designer
date: 2026-10-24
status: draft
inputs: [01-product-brief.md (revision 4 + "Decisions 24 Oct 2026"), ux-learnings.md, portal.js Positions section (ocNodeCard, ocRender, posPrintHead, the zoom row), panels.css 2015-2233, 064 prototype-old-v2.html and 10-old-design-improvements.md (the approved chart look), design_system.html, nfr-budget.md §2 §5 §7]
---

# 069 · Download wall chart (PDF) — design

**I recommend. You decide.** Prototype: `prototype-v1.html` in this folder (invented data only).
**Not published:** I have no Artifact tool in this run. The lead session should publish it.

## Bad news first

1. **The brief's "A1 at about 10 pt" holds only just.** I measured the real layout at DTC's shape
   (90 seats, 363 invented names). "All" on one A1 sheet prints names at **9.5 pt** ("readable close
   up"). **A0 gives 13.6 pt.** It got there only after two print-only changes (§4). Before them it was
   **7.5 pt**, below the brief's kill line of 8 pt.
2. **The Owner's print will not be a chart.** Decision D7 keeps his Branch User Permission. In the
   prototype, his branch's 8 seats all report to managers in other branches. So his "wall chart" is
   **8 loose boxes with no lines**. The panel says this in plain words. It is your decision, not a bug
   (Q2).
3. **Today's "Print" button still prints flags, leaving dates and the HR-only box** (brief bad news 4).
   This slice adds a safe print beside it but does not remove the unsafe one. Q1 asks whether to retire it.
4. **Working out the best layout took 2.5 s** in my first prototype (trying 90 layouts). I cut it to
   0.9 s. The product needs the preview line to update within **300 ms** (nfr-budget §2 skeleton bar).
   That is an engineering task (§9).

## 1 · Frame

HR (and the Owner, for what he can see), at a laptop or phone, wants a PDF of the seat chart that a
print shop can print on a big sheet and that reads clearly on a wall.

| Persona | What changes |
|---|---|
| **HR Manager** | New button on Positions. Prints the whole company, any levels, any paper. |
| **Owner / CXO** | Same button. Prints only his branch (D7). The panel tells him so. |
| **Employee / frontline** | Nothing on any screen. They read the wall. |
| Head of department | Not in this slice (D7). |

**Reused, not new** (ux-learnings P8 of 17 Oct, "count the surfaces"): the Positions page, its
`.pos-sheet` tray (the panel), `ocNodeCard`/`ocRender` (the boxes and lines on paper), `posPrintHead`'s
"as at" date, the existing "In no seat" tray (the "See who" link), the browser's print window. **New:**
one button, one panel body, a print-only stylesheet and a few lines of layout code.

**Rung:** new code in `portal.js` and `panels.css` only. Rejected cheaper rungs: today's Print (leaks,
A4 only, 3 names per seat); Frappe's Print Format / server PDF (cannot draw this layout, brief §4).

## 2 · Evidence

- **Not captured on the bench.** The task did not ask for it, and the design builds on code already
  read and on 064's measured screens (`C:/Surbhi-Git/hrlocal-data/ux-review/2026-10-22-old-chart/`).
- **Measured on the prototype:** screenshots and the script are in
  `C:/Surbhi-Git/hrlocal-data/ux-review/2026-10-24-slice069/` (`measure.js`, `v1/`, `v1-measure.txt`).
- **Fact (code):** `position_table` sends the "in no seat" list only to a reader with employee scope
  (`register.py` 446-448). Without it the page has no count. The panel then shows no number (§6).
- **Fact (code):** today's print header says "printed by {name}" (`posPrintHead`). D5 removes that
  for the wall chart.

## 3 · Benchmark

Unchanged from the brief §3 (Frappe HR: Expand All + PNG export, confirmed in code; Zoho, Keka, HiBob
`[recall — verify]`). I add nothing new: no competitor I could check offers paper size with a
readable-size warning. **Not copied:** photos in the export (a wall is seen by visitors).

## 4 · Findings

| ID | Finding | Impact | Kind | Size | Sev. | Evidence |
|---|---|---|---|---|---|---|
| WC1 | The approved chart drawing (064 old-v2) can draw the paper too: same boxes, same lines, flags and avatars left out | High | **Keep** | S | — | Prototype renders paper with the screen's CSS; 0 banned elements |
| WC2 | Measured sizes at DTC's shape (table below) | High | New | — | — | `v1-measure.txt` |
| WC3 | The long column under the team leads made "All" tall; letting it spread into 2 rows across the leads' width moved A1 from 8.3 to 9.5 pt | High | New | S | — | Prototype, layout search |
| WC4 | Screen box padding is generous; print-only tighter padding and 200 px boxes moved A1 from 7.5 to 8.3 pt | Medium | New | S | — | Prototype |
| WC5 | The Owner's branch-only print is loose boxes, no lines | High | — | — | **P2** | Prototype, Owner person; D7 |
| WC6 | Today's Print still leaks flags, leaving dates, the HR box | High | Fix | S | **P2** | `portal.js` 1212, 602; brief bad news 4 |
| WC7 | "Heads of department" as the level-2 label would be untrue for some of the 22 (D3) | Medium | Fix | S | P3 | D3; label checklist |
| WC8 | Several sheets of A3 for "All" = 9 sheets, 2-3 of them nearly blank | Low | — | — | P4 | Prototype, several sheets |
| WC9 | Filter selects on the page are 32 px tall on a phone (existing, not this slice) | Low | Fix | S | P3 | `positions.html` inline `height:32px` |
| WC10 | Brute-force layout search: 2.5 s, then 0.9 s | Medium | Fix | M | P2 | Prototype timing, this laptop |

**Measured sizes** (names at 13 px in print = 9.75 pt at full size; 10 mm margins; 8 mm footer):

| Chart | Laid out | A4 | A3 | A2 | A1 | A0 |
|---|---|---|---|---|---|---|
| 2 levels: 23 boxes, 21 people | 1,128 × 608 px | 9 pt | **13 pt** | 18 pt | 26 pt | 38 pt |
| All 3 levels: 90 boxes, 363 people | 3,100 × 2,201 px | 3 pt | 4 pt | 6 pt | **9.5 pt** | **13.6 pt** |
| All, several sheets at 10 pt | — | 16 sheets | 9 sheets | 4 sheets | 4 sheets | 1 sheet |

Names are invented, so real name lengths may move these by a point. `[ASSUMPTION]` DTC's names are
about as long as the invented ones.

## 5 · Flow

1. **Positions → "Download wall chart (PDF)"** (page toolbar, beside "+ Add a seat"). The panel opens
   (the existing tray: a right-hand drawer on desktop, a bottom sheet on a phone). Focus moves to its
   heading.
2. The person changes any of four choices. The **result line updates** each time.
3. **Open print preview.** We set the page size and the document title (the PDF's file name), then
   open the browser's print window.
4. In the print window: **Destination: Save as PDF → Save.** The file goes to Downloads.
5. The print window closes. The panel is still open, so they can try another size. Close or Escape
   returns focus to the button.

**Every state:**

| State | What the person sees |
|---|---|
| First open | Start from: the top. Levels: 2. Paper: A3. Sheets: one. Result line filled in. |
| Result readable | "A3 landscape · one sheet · names at 13 pt" / "Readable at arm's length." / "23 seats · 21 people" |
| Under 8 pt | Amber box, the word **Warning:**, "that is too small to read on a wall." Two buttons: "Use A1 (names at 9 pt)" and "Use 9 A3 sheets". If no paper reaches 8 pt, only the sheets button. |
| Several sheets, fits on one | "It fits on one sheet at this size, so it prints as one." |
| A filter is on | Blue note: "Your Branch filter does not apply here. The wall chart uses only the choices below." |
| Owner (branch scope) | Blue note: "You can see 1 branch, Pitampura, so the chart covers Pitampura only. Its seats report to managers in other branches, so they print side by side with no lines above them." Start from has one choice; Levels says "All: 1 level, 8 seats side by side". |
| Reader with no "in no seat" list | The people note drops its number: "Only people placed in a seat are on the chart." |
| No seats at all | No button (the page shows its existing empty state). |
| Working out the size takes a moment | Result line reads "Working out the size…" until it is ready (only if over 300 ms, §9). |
| Browser blocks or ignores the page size | Not designed yet: test first (Q4). |
| No permission | No Positions page, so no button (unchanged). |

## 6 · Screen spec — exact words

**Toolbar button:** `Download wall chart (PDF)` (outline button; full width, 44 px on a phone).

**Panel heading:** `Download wall chart (PDF)` · button `Close`.
**Intro:** `A chart of seats and names for a wall, sized for the paper you choose.`

**Scope note** (blue):
- HR: `Covers the whole company: {n} branches.`
- Branch-limited reader: `You can see {n} branch(es), {names}, so the chart covers {names} only.` and,
  when its top seats report outside it, `Its seats report to managers in other branches, so they print
  side by side with no lines above them.`
- Filter on: `Your {Branch/Department/Job role/Show} filter does not apply here. The wall chart uses
  only the choices below.`

**Start from** (select): `The top: {top seat title}` (or `The top of what you can see ({n} seats)`
when there are several tops), then every seat that has seats under it, indented by level.

**Levels** (select):
- `2 levels: the top and the {n} seats under it` (or `{seat} and the {n} seats under it`)
- `3 levels`, `4 levels` … for deeper companies
- `All {d} levels: every seat ({n} seats, {p} people)`
- Default: 2. If the start has only one level below it, the only option is All.

**Paper** (radio chips): `A4 A3 A2 A1 A0` · hint `{paper} is {w} × {h} mm.`

**Sheets** (radios):
- `One sheet, scaled to fit` — `For a print shop. The usual choice from A2 up.`
- `Several sheets, names at 10 pt` — `For an office printer. Each sheet says where it goes.`

**Result line** (live region): `{paper} {landscape|portrait} · one sheet · names at {pt} pt` or
`{paper} {orientation} · {n} sheets ({c} across, {r} down) · names at 10 pt`, then the reading band,
then `{n} seats · {p} people`.

**Reading bands** (plain words for "pt"; `[recall — verify]`, from the brief's own note):

| Names | Words |
|---|---|
| under 8 pt | Too small to read. (Warning) |
| 8 to 9 | Readable close up. |
| 10 to 13 | Readable at arm's length. |
| 14 and up | Readable from about a metre away. |

**People note** (grey): `{n} active people are not in any seat, so they are not on the chart. Placing
them in a seat first is recommended, not required.` · link `See who is not in a seat` (opens the
existing tray). Branch-limited: `{n} active {branch} people …`.

**Privacy line:** `Only seat names and people's names print. Flags, leaving dates and HR notes never do.`

**Footer of the panel:** button `Open print preview` · hint `Your browser opens its print window.
Choose Save as PDF as the printer, then Save.`

**The sheet:**
- Each box: seat title; branch (not on the top box); every name, in up to 4 columns of 10; `Vacant`
  for an empty seat; on the last level drawn, `{n} seats · {p} people below`.
- Never: flags, "to fill", "%", "covering", "leaving", "key seat", avatars or photos, the "No reporting
  manager" box, the "In no seat" list, fold buttons, anything `.private` or `[data-private]`.
- Footer on every sheet, 9 pt: `{Company} · {whole company | {branch} branch} · {all levels | n levels}
  from {the top | seat} · as at {date} · {p} people in seats`. Several sheets add
  `· Sheet {k} of {n} (row {r}, column {c})`. **No "printed by"** (D5).
- Always printed light, whatever the screen theme.
- **File name** (from the document title while printing): `Wall chart - {Company} - {levels} - {paper}
  - {date}.pdf`.

## 7 · The print layout

- **Same drawing as the screen.** The boxes and lines are `ocNodeCard`/`ocRender` with print rules.
  The connector check from 064 (`old-audit.js`) should run on the print DOM too.
- **Wrap:** a column of 3 or more seats with nobody under them becomes several columns side by side
  (a grid, `grid-auto-flow: column`). A bar joins the tops of the columns. Every tick still comes from
  the real manager.
- **The column under the team leads** (064 Q2) may spread to 2-5 rows across the leads' width.
- **How many rows per column:** the one that fills an A-series sheet best. All A sizes share one
  shape, so one layout serves every paper; only the scale changes.
- **Orientation:** landscape when the chart is wider than tall, else portrait. Chosen for the person.
- **Several sheets:** the browser cannot split a wide page across sheets. So each sheet is its own
  clipped copy of the chart, one per printed page.
- **Print-only sizes:** box padding 7/9 px, boxes 200 px wide (wider for 11+ names), names 13 px.

## 8 · Accessibility and privacy

- Panel: `role="dialog"`, `aria-modal`, labelled by its heading; focus moves to the heading; Escape
  closes; focus returns to the button.
- Native select and radio inputs, all labelled. Paper chips are radios with a visible focus ring.
- Result line is `role="status"` with `aria-live="polite"`. The warning says **Warning:** in words, not
  only amber.
- **Measured** (`v1-measure.txt`): 44 states (2 widths × light/dark × HR/Owner × 6 states, less two
  that do not apply): **0 sideways scroll, 0 text under 12 px on screen, 0 targets under 44 px on the
  phone or 24 px on desktop, 0 script errors.** The paper itself is excluded from the text rule.
- **Privacy:** the PDF is drawn from rows already sent to this reader, so it can never show more than
  the screen. The print DOM holds 0 flags, tags, avatars, images, private marks or HR boxes (measured).
  Names on a wall are DTC's call as employer (brief §12). No new personal data, no server call.

## 9 · What the analyst must turn into acceptance criteria

1. The button shows for anyone who can open Positions and has at least one seat. Nobody else.
2. Defaults: the top, 2 levels, A3, one sheet.
3. The result line and the warning follow §6 exactly, including "Use {paper}" and "Use {n} sheets".
4. **The result line updates within 300 ms** of a change at DTC's size (90 seats). If it cannot, it
   shows "Working out the size…" within 300 ms. The prototype's trial-and-error search took 0.9-2.5 s:
   the engineer should work out rows-per-column from measured box heights, not by redrawing many times.
5. Print DOM contains no `.oc-flag`, `.oc-tag`, `.oc-toggle`, `.av`, `img`, `.pos-nomgr`, `.private`,
   `[data-private]`. Names printed = people in seats within the chosen start and levels. Boxes printed =
   seats within them. Empty seats print `Vacant`.
6. On "Open print preview": add `@page { size: {paper} {orientation}; margin: 10mm }` **after** the
   portal's global A4 rule, set `document.title` to the file name, call `window.print()`, and on
   `afterprint` remove the rule and restore the title. The global A4 rule is not edited (D10).
7. While the wall chart prints, everything else on the page is hidden; the wall chart container is
   hidden on screen.
8. Footer on every sheet as §6; no "printed by"; always light colours.
9. Filters are ignored, and the panel says so when one is on.
10. A branch-limited reader's panel and footer name their branch(es).
11. Several sheets: one clipped copy per sheet, labelled `Sheet k of n (row r, column c)`.
12. Chrome and Edge on Windows produce a PDF at the chosen size (manual check). Safari on iPhone: test
    and record (Q4).
13. The connector check finds 0 false or missing links on the print DOM for 2 levels and All.

## 10 · Checks before handoff

**Heuristics (Nielsen):** status visible (live result line); match the real world (paper names, "pt"
explained in words); user control (Close, Escape, panel stays after printing); consistency (the same
tray and chart as Positions); error prevention (warning before an unreadable print, one-tap fixes);
recognition over recall (mm size shown); minimal design (four choices, no settings page).

**Persona walkthrough:**

| Task | Before | After |
|---|---|---|
| HR: HOD chart for the notice board | Print → A4 strip, flags and HR box on paper | Button → Open print preview → Save as PDF → Save: **4 steps**, defaults are right |
| HR: whole company for a print shop | Not possible (3 names per seat, A4) | Button → Levels All → A1 or A0 → Open print preview → Save: **6 steps** |
| Owner: his chart | Same as HR before | Prints his branch only; told why in the panel |

**Frontline bar:** not their task; nothing changes for them.

**Red team:** brand-new tenant with no seats → no button. 900 seats → the warning offers sheets or
fewer levels. 36 names in one seat → 4 columns in one box (drawn). Network drops → no server call, so
nothing to lose. A filter on → said. Someone not allowed → the rows they cannot see were never sent.

## 11 · Usability test plan (High impact)

Five people: 2 HR managers, 1 owner, 2 office admins who use print shops.

| Task | Success |
|---|---|
| Make a PDF of the top two levels for an A3 notice board | PDF at A3, 23 boxes, under 2 minutes, no help |
| Make a PDF of everyone that a print shop will print, readable at arm's length | Chooses All and A1 or A0; can say what "names at 9 pt" means |
| Make a PDF of one manager's team only | Uses Start from |
| After a warning appears, make it readable | Uses one of the two buttons |

**Would change the design:** 2 or more miss Save as PDF in the print window (then put the steps on
screen as numbered steps); 2 or more read "pt" as meaningless even with the words (then lead with the
reading band); anyone thinks the 82 unseated people are on the chart.

## Not in this slice (yours to decide later)

- A title line at the top of the sheet (the footer holds the facts today).
- Join marks for office sheets (D8: only if cheap; the sheet label is the minimum).
- Skipping nearly blank sheets in "several sheets".
- Heads of department printing their own team (D7).

## Subtract pass

**Removed:** avatars on paper (space and D6); an automatic paper pick; a remembered last choice; a
mini-map on each sheet; join marks; a sheet title; an iPhone warning line (test first); a server call
for the Owner's unseated count (shows no number instead). **Kept** only because the numbers need them:
the wrap, the wider column under the leads, and tighter print padding.

## Open questions

| # | Question | Owner | Blocks | My recommendation |
|---|---|---|---|---|
| Q1 | Retire the existing **Print** button on the zoom row? It prints flags, leaving dates and the HR-only box, which D6 bans for the wall chart. Keeping both gives two print buttons with different rules. | Surbhi | The toolbar | **Retire it.** "Start from a seat" covers printing part of the chart |
| Q2 | With his Branch User Permission (D7), the Owner's print is loose boxes. Is that acceptable, with HR printing the company chart for him? | Surbhi | Nothing in the build; DTC's expectation | **Yes**, keep D7; HR prints for him. The panel already says why |
| Q3 | Several sheets carry "Sheet k of n (row r, column c)" and no join marks. Enough? | Surbhi | Several-sheet printing | **Yes** (D8) |
| Q4 | If Safari on iPhone ignores the page size, add "Use a laptop for sizes above A4" on iPhone? | Surbhi, after the engineer's test | The phone path | Test first; add the line only if it fails |

## Assumptions

- `[ASSUMPTION]` DTC's real names are about as long as the invented ones, so the measured sizes hold to
  within about a point.
- `[ASSUMPTION]` Chrome and Edge honour an injected `@page size` that comes after the global A4 rule.
- `[ASSUMPTION]` The reading bands (10 pt at arm's length, 14 pt at a metre) are `[recall — verify]`.
- `[ASSUMPTION]` The Owner may or may not get the "in no seat" list from the server; both states are
  designed.

## Handoff note

To the analyst and engineer: the prototype's print layout is the screen chart with print rules, not a
second drawing — keep it that way. The sizes in §4 come from a real render, but the search that found
them is too slow; meet the 300 ms bar another way. The `@page` rule must be added after the global
A4 rule and removed after printing (D10 leaves the global rule alone). Run 064's connector check on the
print DOM. Q1 decides whether the old Print button goes; do not leave two print buttons with different
privacy rules without her answer.
