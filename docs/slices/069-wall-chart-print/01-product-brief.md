# 069 · The whole hierarchy as a PDF, on the paper size you choose

**Product brief · 24 Oct 2026 · revision 4 · draft · I recommend, you decide.**

Surbhi's decisions so far:
1. The wall chart is mostly the heads of department (HODs).
2. People below HOD level must be printable too. The user picks how many levels, up to **All**.
3. The Owner prints his whole hierarchy from the top.
4. **Do not assume A4.** Give a PDF with all the boxes, and let the user pick the page size (A4, A3,
   A2, A1 and so on) so the chart reads clearly.

## Bad news first

1. **At DTC, a bigger sheet does not help unless the layout changes.** Today's chart, fully opened,
   is a tall strip about **1,450 px wide and 7,500 px tall** (about 1 : 5). On A0 it fills a quarter
   of the width and the text drops to about **6 pt**. So the PDF needs a print-only layout that
   **wraps the long columns into several side by side**, so the chart takes the shape of the paper.
   With that, "All" fits **A1 at about 10 pt** or **A0 at about 14 pt** (estimates, see §2).
2. **"All" is 363 people, not 445.** 82 active people sit in no seat, so no seat chart can show them.
   35 of those are at Pitampura, which has two branch records. Fix the data before the first print.
3. **The browser makes the PDF, not our server.** Frappe's own PDF tool (wkhtmltopdf) runs an old
   browser engine. It cannot draw this chart's layout. Section 4 explains.
4. **Today's Print leaks to paper.** It prints the HR-only "No reporting manager" box and the
   "leaving 30 Nov" flags. It hides the fold counts. It shows only 3 names per seat. (Confirmed:
   `portal.js` lines 602, 1201, 1277-1300; `panels.css` 2152-2167.)
5. **A head of department cannot be limited to their own team today.** Positions scopes by company
   and branch, not by reporting line (`register.py`, `_scope`). At DTC, HODs cannot open Positions.
6. **No UX scan (`01a`) and no DevOps notes (`07` §1) exist.** Every size here is my estimate from
   the CSS and DTC's counts. The UX designer must measure it before you approve.

## Recommendation in six lines

- A **"Download wall chart (PDF)"** button on Positions opens a small panel with four choices:
  **Start from** (top, or a seat), **Levels** (2 = HODs by default, each level down, up to **All**),
  **Paper** (A4, A3, A2, A1, A0) and **Sheets** (one sheet scaled to fit, or several sheets at a
  readable size).
- The panel says the result before you print: *"A1 · one sheet · names at 10 pt"*. Below 8 pt it
  says so and suggests the next size up.
- The print-only layout wraps long columns so the chart matches the paper's shape.
- The browser opens its print preview with that page size set. The user picks **Save as PDF**. Text
  stays text, so a print shop can enlarge it with no blur.
- Nothing private is ever drawn (§6). Print draws only what this person already sees on screen.
- **No server PDF, no new package, no new app. No server cost.**

## 1 · Job and personas

*"As DTC's owner, I want the whole company on my wall the way we always had it, readable from where I
stand."* HR wants the HOD sheet on the notice board.

| Persona | What changes |
|---|---|
| Owner / CXO | Whole company, any levels, any paper. |
| HR Manager | Same, for their companies. |
| Head of department | Not in this slice (§7). HR prints their team for them. |
| Employee / frontline | Reads the wall. Never prints. Nothing on their screen changes. |

## 2 · Facts and sizes

**DTC's structure** (064 team's read-only count, 21 Oct 2026): 3 levels. Owner; **22 seats under the
Owner** (5 team leads and 17 seats with nobody under them, including the CFO); **67 seats** under the
5 leads (14, 10, 13, 19, 11). 363 people in seats. Biggest seats: Back Office 36, RSO Noida 31. So at
DTC, "Levels" means 2 (HODs) or 3 (= All). Deeper customers get every level in turn.

**Sizes** (estimate: boxes 196-240 px, a name row 32 px, about 70 px per box; 1 px prints at 0.75 pt
at full size; names are 14 px = 10.5 pt at full size):

| What | Today's layout (tall strip) | Wrapped layout | Paper for about 10 pt names |
|---|---|---|---|
| HODs, 23 boxes, about 60 names | 1,400 x 1,900 px | about 1,500 x 1,000 px | **A3** (A2 gives about 14 pt) |
| All at DTC, about 90 boxes, 363 names | 1,450 x 7,500 px | about 3,800 x 2,600 px | **A1** (A0 gives about 14 pt) |

| Paper | All at DTC, one sheet, wrapped | Same, today's layout |
|---|---|---|
| A4 | about 3 pt - no; offer about 12 sheets instead | about 2 pt |
| A3 | about 5 pt - no; offer about 6 sheets | about 3 pt |
| A2 | about 7 pt - readable close up | about 4 pt |
| **A1** | **about 10 pt** | about 4.5 pt |
| A0 | about 14 pt | about 6 pt |

**Readable from where:** 10 pt reads at arm's length; 14 pt at about a metre `[recall — verify]`.

**One sheet or several:** one sheet scaled to fit is the default for A2 and up. For A4 and A3, "several
sheets" splits the chart into a grid of sheets at about 10 pt. A grid needs **join marks** - a thin
crop line and "B2 → right: B3" in each corner - because sheets now meet on four sides. Small, but
real: it is the one piece that exists only for office printers. Question 2 asks whether DTC needs it.

**What I could not measure:** real box heights (names wrap), how many level-3 seats group into one
box, and the wrapped layout's exact shape. I did not open DTC.

## 3 · Competitors

| | Frappe HR standard | Zoho People / Keka / HiBob | Us today |
|---|---|---|---|
| Expand all | Yes, "Expand All" (confirmed in `hierarchy_chart_desktop.js`) | `[recall — verify]` | No |
| Export | A PNG picture of the chart (confirmed) - blurs when enlarged | PDF or image `[recall — verify]` | Print what is on screen |
| Choose levels and paper | No | `[recall — verify]` | No |

**What we will not do that others do:** put every employee's photo in an export. A wall chart is seen
by visitors. Ours shows names and initials only.

## 4 · How to make the PDF - the choice

| | Server-made PDF (Frappe's wkhtmltopdf) | **Browser's Save as PDF, page size set by us** (recommended) |
|---|---|---|
| Draws this chart? | **No.** Its engine is about 2012 WebKit: no modern flex layout, no `:has`, no CSS variables. The chart would be redrawn a second way (tables or SVG) and kept in step for ever | Yes - the same drawing the user sees |
| Page size | Any, set by the server | Any; we set `@page size` before opening print. Chrome and Edge honour it `[recall — verify]`; **Safari on iPhone may ignore it** `[recall — verify]` |
| Sharp when enlarged | Yes (text) | Yes (text) |
| Server cost | A process per download, a few seconds, holding a web worker | None |
| Permissions | Must repeat the scoping on the server | Draws only rows already sent to this person |
| One file to download | Yes | The user clicks "Save as PDF" in the print preview |

**Recommendation: the browser.** The only thing the server version buys is a one-click file and
iPhone support. It costs a second drawing of the hierarchy. **Question 1** asks whether one click
matters enough to pay that.

## 5 · Options

| | What | Rung | Verdict |
|---|---|---|---|
| A | Today's Print | already there | **No** - leaks, 3 names per seat, A4 only, cannot expand |
| **B** | Panel (start, levels, paper, sheets) + wrapped print layout + every name + "N seats · N people below" on the last level + private marks stripped; browser PDF | new code in `portal.js` and `panels.css` only | **Recommended** |
| C | B without the wrapped layout | smaller | **No** - the numbers in §2 show big paper does not help the strip |
| D | Server PDF | new code + a second chart drawing | **No** (§4) |

**Effort:** `Evidence required` - the engineer sizes it. The wrapped layout is the risky part: the
064 chart's connector lines took three redesigns. Keep it print-only so the screen chart is untouched.

**Kano:** proxy **Must-be for DTC** (they work from a printed full hierarchy today - seen, Surbhi
24 Oct 2026); **Performance** in general (Frappe HR ships expand and export).

## 6 · Never in the PDF

Every flag chip, including leaving dates and "key seat"; "covering" and "%" tags; the "No reporting
manager" box; the "In no seat" list; anything marked `.private` or `[data-private]` (slice 065's
replacement-plan notes, when they exist); fold buttons. Photos, phone numbers, IDs, grade and pay are
never sent to the chart, so they cannot appear. **Vacant seats:** "Nobody in this seat" prints; "to
fill" does not (question 4). The footer prints the scope and date, not who printed it.

**Test:** the print DOM holds no `.oc-flag`, no `.pos-nomgr`, no `.private`; the printed name count
equals the people in seats in scope.

## 7 · Who may print - never more than they see

The PDF is drawn from the rows `position_table` already sent. It cannot widen anything.

| Person | Recommended | At DTC |
|---|---|---|
| Owner / CXO | Whole company, any levels | He is an Org Structure Editor tied to one branch. **Remove his Branch User Permission** (064 release note 3), or "whole company" is one branch |
| HR Manager | Their companies | Give HR Manager Read on Alvoraa Position (064 release note 2) |
| Head of department | Own sub-tree | **Cannot be enforced today.** Giving them Positions shows the whole company or branch. A true limit needs server scoping by reporting line - a separate slice. Until then, HR prints for them |
| Employee | None | No change |

## 8 · The global A4 rule

`panels.css` sets `@page { A4 landscape }` for **every** print in the portal, so payslips and other
prints are forced landscape too. This slice must set the page size only while the wall chart prints
(add the rule just before printing, remove it after), and move today's Positions rule the same way.
That fixes the other prints as a side effect - say so in the release note.

## 9 · NFR and run cost

- **Render:** about 90 boxes and 363 names - small for a browser. Target: preview opens in under 2 s
  on a laptop at DTC size. `Needs validation`.
- **Server:** no new call - the page already has the rows (`position_table`, 7 queries).
- **PDF size:** text, no photos - well under 1 MB `[ASSUMPTION]`.
- **Security:** neutral. **Privacy:** better than today, which leaks two things to paper.
- **10x data:** at 900 seats "All" on one A0 drops below 5 pt. The panel says so and offers sheets or
  fewer levels.

## 10 · The WOW

The Owner picks **All · A1 · one sheet**. The panel reads *"A1 · one sheet · names at 10 pt"*. The
PDF goes to a print shop and comes back as one sheet: every team, every name, crisp. Footer: *"DTC ·
whole company · all levels · as at 24 Oct 2026 · 363 people in seats."*

## 11 · Success criteria

| Measure | Baseline | Target | How |
|---|---|---|---|
| DTC has it on the wall | Not today | Within 2 weeks of release | Ask DTC; a photo |
| Private marks in the PDF | Today: HR box, leaving flags | 0 | Print-DOM test (§6) |
| Names in "All" | Today: 3 per seat | Every person in a seat in scope | Count test |
| Text size on the chosen paper | n/a | At least 8 pt, or the panel warns | Shown before printing; checked in test |

## 12 · Risks

- **Wrong data, framed.** Seats and "Reports To" disagree (18 people under the CFO). Fix first.
- **"Everyone" without 82 people.** The footer says "people in seats".
- **A filter on** would drop seats silently - the wall chart clears it first.
- **iPhone.** If Safari ignores the page size, the Owner's phone PDF comes out A4. Test; if it fails,
  say "use a laptop" in the panel.
- **Stale paper.** 164 people joined DTC in 60 days. The "as at" date is printed for that reason.

**Thriving lens:** clarity for new joiners (engagement); people find the right team (collaboration);
the wall serves staff with no login, but anyone in no seat is missing (inclusiveness); roles and teams
shown, never resignations or HR gaps (transparency).

**Regulatory read:** DPDP - names and titles are personal data. The duty is DTC's, as employer; a
PDF that strips private marks by itself helps them. New: names visible to visitors. Defensible; a
chart showing who resigned would not be. I am not a lawyer; DTC should confirm it is happy to post
names.

## Open questions

| # | Question | Owner | Blocks | My recommended answer |
|---|---|---|---|---|
| 1 | Is clicking "Save as PDF" in the print preview fine, or must it be a one-click download (server PDF, much more work)? | Surbhi | §4 | Browser |
| 2 | Does DTC need A4 or A3 sheets with join marks, or will they use a print shop for A1? | Surbhi with DTC | The join-mark work | Print shop; keep join marks only if DTC says so |
| 3 | Are all 22 seats under the Owner heads of department? | Surbhi with DTC | Default view | Yes |
| 4 | Vacant seats: "Nobody in this seat" yes, "to fill" no? | Surbhi | Box content | Yes |
| 5 | Heads of department printing their own team: a separate slice? | Surbhi | §7 | Yes |
| 6 | Remove the Owner's Branch User Permission at DTC? | Surbhi | Whole-company print | Yes |

## Assumptions

- `[ASSUMPTION]` DTC's shape is as counted on 21 Oct 2026. Re-count before building.
- `[ASSUMPTION]` All sizes are estimates; the UX designer measures them.
- `[ASSUMPTION]` Chrome and Edge honour a custom page size in Save as PDF.

## Kill criteria

- The measured wrapped layout cannot reach 8 pt on A1 for DTC's "All". Then stop and bring Surbhi the
  numbers before building anything bigger.
- The seat data cannot be corrected before release.

## Subtract pass

Removed in this revision: the "one long strip" paper (Surbhi chose standard sizes), the
page-numbers-only tiling (sheets now meet on four sides), the server PDF, HOD sub-tree permission,
photos. Kept only because the numbers need it: the wrapped print layout.

---

## Decisions 24 Oct 2026

Surbhi's final decisions, recorded by `hrms-ux-designer` at her instruction on 24 Oct 2026. **Where
this section and anything above disagree, this section wins.**

| # | Decision | Answers |
|---|---|---|
| D1 | Build a **"Download wall chart (PDF)"** panel on the Positions page. The browser's own **Save as PDF** makes the file. We set the page size, A4 to A0. | Question 1 (browser, not server) |
| D2 | The panel has four choices: **Start from** (the top, or a seat), **Levels** (default 2 = heads of department, down to **All**), **Paper** (A4, A3, A2, A1, A0) and **Sheets** (one sheet scaled to fit, or several sheets at a readable size). A preview line says the result, such as *"A1 · one sheet · names at 10 pt"*. Below 8 pt it warns. | Recommendation, §2 |
| D3 | All **22 seats under the Owner** print at level 2, even though not all of them are heads of department. | Question 3 |
| D4 | An empty seat prints **"Vacant"**. "To fill" counts do not print. | Question 4 |
| D5 | **No "printed by" name** on the sheet. | §6 footer |
| D6 | The PDF **never** prints: flags, leaving dates, the HR-only "No reporting manager" box, private marks (`.private`, `[data-private]`), replacement-plan data, photos, phone numbers or IDs. | §6 |
| D7 | **HR prints the whole company.** The Owner **keeps his Branch User Permission**, so his print covers only what he sees on screen: his branch. Heads of department printing their own team is a **separate, later slice**. Employees cannot print. | Questions 5 and 6 (6 answered "no, keep it") |
| D8 | The PDF is made **for a print shop**. Join marks for office sheets are an optional fallback: **leave them out unless they are cheap.** | Question 2 |
| D9 | The **82 active people with no seat are not printed.** The panel says on screen how many people are not in a seat. HR placing them first is **recommended, not compulsory**. | Bad news 2 |
| D10 | The **global A4 print rule is left alone**, and a note is recorded. The wall chart sets its own page size only while it prints. | §8 |

**What changes above because of these:**
- §7: the Owner's row now reads "his branch only", not "whole company". The release note no longer
  asks to remove his Branch User Permission.
- §8: the portal-wide `@page { A4 landscape }` rule stays as it is. The payslip side effect is not
  fixed by this slice. Recorded here as the note D10 asks for.
- Open questions 1 to 6 are closed by D1, D8, D3, D4, D7 and D7.

---

## Decisions 24 Oct 2026 (2)

**Status: recommendation, waiting for Surbhi's answers (R1 to R5 below). Nothing here is decided yet.**
Written by `hrms-product-manager`. If she accepts, this section changes D4 and D6 above.

**Her words:** *"This should be an option to show replacement and vacant seat on the print version
chart or not. e.g. currently DTC keeps such charts for the HR departments."*

**Bad news first.**
1. **Printing slice 065 replacement plans breaks two promises she already approved:** "No copy is kept
   in the system" and "Erased within a day of them leaving". Paper cannot be erased. Since 065 Rev 3
   a plan can carry the reason "Performance" and an improvement end date. A paper sheet saying a
   person is being replaced while still in an improvement period is the kind of document that could
   be used against DTC in a dispute. **I am not a lawyer.** ⚠ COMPLIANCE: counsel, via Surbhi.
2. **Leaving dates are private too.** The server sends them only to HR, leadership and the person's
   reporting line (`register.py` 316-350). An HR copy that shows them reverses D6 for that copy.
3. **DTC has 0 future leavers today** (065 `01c`, bad news 6), so a "replacements" tick would print
   almost nothing at DTC this week. Openings on seats I could not count.

**What "replacement" can mean, and what the chart already holds** (confirmed in `register.py`):

| Meaning | Already on the page? | Who receives it |
|---|---|---|
| a. A 065 replacement plan on a person | Yes, once 065 merges (`plan` key) | Plan readers only; hidden from the person |
| b. A seat being re-filled: holder leaving, and/or a job opening raised on it | Yes: `leaving`, `opening` | Leaving: HR, leadership, reporting line. Opening: every Positions reader |
| c. A named successor (offer accepted, not joined) | **No.** Job Offer is not read. New server code | - |
| d. A person covering the seat for now | Yes: `covering` | Every Positions reader |

**Most likely: b.** `[ASSUMPTION]` In Indian HR use, a "replacement" is a seat re-filled after a
leaver, as against a new seat. Paired with "vacant seat" on an HR manpower chart, that is what DTC's
paper charts most likely show. Confirm with her (R1).

**Options**

| | What | Rung | Verdict |
|---|---|---|---|
| A | Two ticks. **Show "Vacant"** for any printer, default on. **HR copy: show replacements** (meaning b, plus d as "Covering"), default off | New code in `portal.js` and `panels.css`. No server change | **Recommended** |
| B | A, plus 065 plans (a mark only, never the note, reason or who set it) | Same rung; heavy compliance cost | **No**, unless counsel says yes in writing |
| C | Vacant tick only | Smallest | Fallback if R1 says "she meant plans" and counsel says no |

**Rules for the HR copy tick (option A):**
- It appears only when the page already holds that data for this reader (`may_see_leaving` true).
  The server stays the real control; the print can never show more than the screen received.
- Off every time the panel opens (SEC-1 already forbids remembering choices).
- When on: every sheet carries **"HR use only - not for display"** at top and foot; the file name
  starts **"HR copy -"**; the panel adds *"Print in the office, not at a print shop."*
- Never printed even when on: plan data, notes, reasons, employee ID, who set anything.

**Vacant as its own tick:** on by default, so staff wall copies keep "Vacant". Off removes the word
only; the box and title stay, because an empty seat with people below holds the tree together.

**Effect on checks:** the 8 pt figure must be worked out from the layout as drawn with the ticks,
and re-shown when a tick changes (extra lines make boxes taller). The PRIV-1 sentinel test runs
twice: tick off (no leaving date, no opening, no banner) and tick on (only the allowed words, never
a plan sentinel, banner on every sheet). One more test: no tick when `may_see_leaving` is false.

**Questions for Surbhi**

| # | Question | Blocks | My recommendation |
|---|---|---|---|
| R1 | By "replacement", do you mean b (seat being re-filled) or a (065 plan)? | Which option | b |
| R2 | If a: will you ask counsel before any paper copy of a plan exists? | Option B | Yes; build C meanwhile |
| R3 | HR copy may show leaving dates, reversing D6 for that copy only? | Option A content | Yes, HR copy only |
| R4 | "Vacant" off: remove the word only, or drop empty end seats too? | Box content | Word only |
| R5 | Owners (Org Structure Editor) get the HR copy tick too? | Tick gate | Yes, they already see the same data on screen |

**Subtract pass:** removed a diagonal watermark (the banner on each sheet does the job), a named
successor (needs server code, nobody asked), and a separate "Covering" tick (folded into the HR copy).
