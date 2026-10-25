---
slice: 064-organogram-improvements
artifact: 02-design (review, design and prototype; plays the role of 01b-ux-design)
author: hrms-ux-designer
date: 2026-10-21
status: draft
inputs: [Surbhi's message of 21 Oct 2026 (items 2, 5, 6, 7, 8), 01-product-brief.md, 01c-engineer-findings.md, ux-learnings.md, product-context.md, nfr-budget.md, no-over-engineering.md, code in worktree 060-manager-review (positions.html, portal.js Positions and Organisation sections, panels.css, hrms/alvoraa_org_structure/*), read-only counts on dtc.alvoraa.co]
---

# 064 · The Positions organogram at 90 seats and 445 people

**I recommend. You decide.** Prototype: `prototype-v1.html` in this folder.

## Gate summary — bad news first

1. **At DTC the chart is wide, not deep. Folding by level alone will not fix it.** DTC has one top seat (Owner) with **22 seats directly under it**, and the whole tree is only **three rows deep**. Today's rule opens two layers below the top, so at DTC **every one of the 90 seats is drawn**, with about 84 boxes in the bottom rows. From the CSS, that is roughly **18,000 px wide** (inference; I did not see it in a browser). Even "top plus one layer" (PM D1) leaves 22 boxes side by side, about 4,700 px. **The fix that matters is drawing the seats with nobody under them as one compact card.** With that, the default view measures **1,382 px** in the prototype and fits a 1440 screen.
2. **82 of 445 active people (18%) are in no seat.** They are not on the chart and not in any number on the page. Nothing says so. 35 of them work at Pitampura, where the seats use a second branch record, "DTC - PITAMPURA", while the people use "DTC Pitampura".
3. **I disagree with PM decision D3.** A "No reporting manager" box built from **seats** would be **empty at DTC**: the Owner seat is the only seat with no parent. The **19 people** with no manager are all people with no seat. To show what Surbhi asked for, the box has to count **people**. Details in §6.2.
4. **The prototype is not published.** I have no Artifact tool in this run. The lead session should publish `prototype-v1.html` and give Surbhi the link.
5. **Nothing was seen on the real product in a browser.** There is no local admin password in reach, and DTC is production. The review comes from the code, read-only counts on DTC, and the measured prototype. Every layout claim about today's page is marked as inference.

**Recommendation in five lines**
1. Open on "Reporting lines" with the top seat and one layer below it. Fold everything else.
2. Draw seats that have nobody under them as one compact card under their manager, not as a row of boxes.
3. Put a roll-up line on every box with seats under it: "19 seats below · 75 people · 1 to fill".
4. Add "Find a person or a seat", plus one always-visible View control (Reporting lines · By branch · By department · List).
5. Say what is missing: a "No reporting manager · 19 people" box, and an "82 in no seat" tile, each opening the list behind it.

---

## 1 · Frame

**Who, when, what device, what job.** An HR Manager at DTC on a laptop, at a month-end or during hiring, wants to find a seat, see where the holes are, and fix what is wrong. The owner (CXO), often on a phone, wants the shape and the problems in five minutes. A department or store head wants their own part and its empty seats.

| Persona | In scope? | What changes for them |
|---|---|---|
| HR Manager | Yes, main user | Finds any seat or person in seconds. Sees every gap (no manager, no seat, record mismatch) with the list behind it. Can plan a replacement (slice 065) |
| CXO / owner | Yes | Top of the company on one screen, with counts on every box. A reading mode on the phone |
| Department or store head | Yes, if the tenant opens Positions to them | Their own line, with counts. "Reports above your view" as today. Sees no company-wide gaps and no private notes |
| Employee | No | Nothing changes on Positions; they never open it. **One-way rule check:** nothing here shows an employee anything new about a colleague. The replacement note (065) is designed to be invisible to them and to their manager |
| Frontline employee | No | Not a Positions user |

**Fact:** at DTC only **System Manager** and **Org Structure Editor** can open Positions today. DTC has Custom DocPerm rows on Alvoraa Position, and in Frappe those replace the standard ones `[recall — verify the Frappe rule]`. So an "HR Manager" without the editor role, and every department head, cannot open the page at DTC now. The department-head review below is "if the tenant opens it".

## 2 · Evidence

### 2.1 DTC's real shape (read-only, 21 Oct 2026)

Read through standard input on the production backend container, reading only. No names are written here.

| Fact | Value |
|---|---|
| Seats | 90, all Active. Sum of places: 364 |
| Top seats (no parent) | **1**, the Owner seat |
| Seats directly under the top | **22**: 5 lead teams (Admin · Ambala, Back Office · Chandigarh 34, FM · Chandigarh 22, Manager · Delhi, S-RE Manager · Noida), 17 have nobody under them |
| Depth | 3 rows (top, 22, then 67 seats under the 5 team leads) |
| Seats under the 5 team leads | 14, 10, 13, 19, 11 — **all** with nobody under them |
| Biggest seats by people | Back Office · Chandigarh 34: 36. RSO · Noida: 31. Housekeeping · Chandigarh 34: 13 |
| Active employees | 445 (the request says 476; the gap is probably inactive or contract records `[ASSUMPTION]`) |
| In a seat | 363. **In no seat: 82** (RSO 38, FSE 23, Cashier 6, others 15; Pitampura 35, Noida 20) |
| No reporting manager on their Employee record | 20, of which 19 excluding the Owner. **All 19 are in no seat** |
| Biggest spans by Employee "Reports To" | 116, 77, 74, 64, 55 people under five managers |
| On notice today | 0 |
| Key seats | 0 |
| Open Job Openings | 2. **Employees who came through Frappe hiring (job_applicant set): 0** |
| Joined in the last 60 days | 164 |
| Branch records | Two for one store: "DTC Pitampura" (people) and "DTC - PITAMPURA" (seats) |
| Span settings | "too wide" at 9 direct reports; "a layer of one" at 1 |

### 2.2 The code (read in this worktree)

- `POS_OPEN_DEPTH = 2` opens the top and two layers below it. At DTC that is everything.
- Arrange-by is hidden unless View is "As a structure"; View defaults to "As a list" and sits among the filters (`posPaint`). Matches the engineer's bug 1.
- A folded box says only "N more below" (direct seats), not people or holes further down.
- `reporting_mismatches` (seat tree vs Employee "Reports To") exists, HR Manager and System Manager only, **with no screen**. It runs `frappe.db.get_value` inside a loop over every assignment: about three queries per seated person, so roughly 1,000 at DTC. That breaks the NFR rule that the query count must be the same for 20 people as for 1,000 (nfr-budget §2).
- `post_job` makes an **unpublished** Job Opening by default. Useful for the replacement flow.
- Screenshots of the **prototype** (sample data only): `C:/Surbhi-Git/hrlocal-data/ux-review/2026-10-21-slice064/`.

### 2.3 Surfaces that already answer these questions (counted before designing)

| Surface | Who | What it already does | Fate |
|---|---|---|---|
| Positions page, list | Editors | Every seat, filters that narrow each other, tiles over the filtered rows | **Keep**, add a caption count |
| Positions page, structure | Editors | Same boxes as the Organisation chart, fold, grey-and-open-path filters, groups identical seats, three arrangements | **Extend**: compact card, roll-ups, Find, one View control |
| Organisation page | Everyone, reach-limited | Re-root on click, breadcrumb, "Up one level", people search, HR health tiles with drill lists, span flags | **Keep**. Reuse its "one level at a time" idea for the phone reading mode. Not merged with Positions (different audiences) |
| Desk "Organizational Chart" (Frappe HR) | Desk users | People tree, unfold on click | Leave alone |
| Desk Employee list / form | HR | Edits "Reports To" | **Reuse** as the "Set manager" action |
| `reporting_mismatches` | HR, no screen | Finds seat-vs-person disagreements | **Reuse after a rewrite** to grouped queries |
| `org_health` metrics | HR on Organisation page | Vacant, over capacity, span flags | Keep; not repeated on Positions |
| `post_job` | Editors | Unpublished Job Opening from a seat | **Reuse** for "Make an opening, not advertised" |

No new page, no new chart, no setting.

## 3 · Benchmark (short; the PM's brief §4 has the full table)

Read 21 Oct 2026, search summaries only, **no product screenshots seen**.

- **Keka** (read): fold and unfold on cards; "Top of the Org" and "Me" views; search lives in the directory, not the tree; download of the expanded tree, and it exports only what is open. [Keka help](https://help.keka.com/hc/en-us/articles/50141197218321-How-to-Download-an-Expanded-Organisation-Chart), [Keka directory and tree](https://help.keka.com/hc/en-us/articles/39946766647313-Using-the-employee-directory-and-organization-tree).
- **PeopleForce** (read): PDF of the current view and filters. [PeopleForce](https://help.peopleforce.io/en/articles/9145094-explore-your-company-s-organizational-chart).
- **ChartHop** (read): open roles on the chart from recruiting; role-restricted views. [ChartHop](https://www.charthop.com/platform/headcount-planning).
- **BambooHR** (read): PDF of a large chart gets unwieldy; PNG suggested. [BambooHR](https://bamboohr.screenstepslive.com/a/587751).
- **Zoho People, CatalystOne**: nothing found today. `[recall — verify]`: both have a people org chart with department filters.
- Compact "stacked" layout for leaf boxes in large charts: `[recall — verify]` common in charting tools (OrgChart JS, Lucidchart).

**Deliberately not copied:** a predicted flight-risk score (an automated judgement about a named person); drag-and-drop restructuring; a PDF of the whole 90-seat tree (unreadable on paper); a zoom canvas or minimap (a second renderer).

## 4 · Heuristic review of today's page, ranked by what hurts most at 90 seats and 445 people

IDs `OG` (organogram). P-levels say whether it should block a release of this slice.

| ID | Finding | Who it hurts most | Impact | Kind | Size | P | Evidence |
|---|---|---|---|---|---|---|---|
| OG1 | **The chart is far wider than the screen.** At DTC everything opens (three rows, "two levels" is all of it); about 84 boxes in the bottom rows, roughly 18,000 px. Even top-plus-one is 22 boxes, about 4,700 px. The reader scrolls sideways and loses the parent | CXO, HR | High | Fix | M | P2 | DTC shape §2.1; CSS `.oc-box` min-width 196 px + 18 px gap (inference, not seen) |
| OG2 | **82 people (18%) are in no seat, and nothing says so.** The "SEATS 90" tile reads as the whole company | CXO (wrong picture), HR | High | Fix | S | P2 | DTC counts |
| OG3 | **The seat lines and people's managers disagree, silently.** The CFO seat has nobody under it while 18 people report to the CFO on their records. The CFO, opening the Organisation page, also sees an empty team | CXO, department head, HR | High | Improve | M | P2 | Engineer bug 3; `reporting_mismatches` has no screen |
| OG4 | **A pooled seat that also leads 10 seats reads as one person's seat.** "Back Office" holds the department head and 35 others, reporting to three different managers. The box says a name "+35" | HR, CXO | High | Improve (words and a chip; the data fix is the engineer's) | S | P3 | Engineer bug 4 |
| OG5 | **Arrange-by hides until View is changed, and both sit among the filters.** Two dropdowns where one is dead half the time | HR, CXO | High | Fix | S | P2 | Bug 1, `posPaint` |
| OG6 | **No way to find a person or a seat.** Organisation has search; Positions does not. Finding one RSO among 445 means filters and scrolling | HR | High | New | S | P2 | Code |
| OG7 | **A folded box hides its problems.** "14 more below" counts direct seats only. No people, no "to fill" or "leaving" further down | CXO | High | Improve | S | P2 | `posNode` / `ocRender` |
| OG8 | **No place for people with no reporting manager** (Surbhi's item 5). 19 people at DTC | HR | Medium | New | S | P2 | DTC counts |
| OG9 | **"Seat" means two things.** The tile "SEATS 90" counts seat records; a box says "31 of 31 filled"; the dialog asks "How many people". One record called RSO · Noida is "a seat" that holds 31 seats | HR, CXO | Medium | Fix (words) | S | P3 | positions.html, portal.js (anti-pattern MA2) |
| OG10 | **Opens as a list**, while Surbhi calls the page the organogram | CXO | Medium | Fix | S | P3 | `pos-f-view` default |
| OG11 | **No phone reading mode.** A sideways-scrolling tree on 390 px | CXO on a phone | Medium | Improve | M | P3 | Code; nothing measured on the real page |
| OG12 | **The filter row is a full row of five controls before the chart** | HR, CXO | Low | Improve | S | P4 | positions.html |
| OG13 | No print for a board pack | CXO | Low | New | S | P4 | Code |
| OG14 | Two branch records for one store make Pitampura's people unseatable by any match | HR | Medium | Data (not design) | S | P3 | DTC Branch list |
| K1 | **Keep:** tiles counted over the filtered rows | | | Keep | | | Code |
| K2 | **Keep:** filters grey what does not match and open the path to every match | | | Keep | | | Code |
| K3 | **Keep:** identical sibling seats grouped into one box | | | Keep | | | Code |
| K4 | **Keep:** boxes are real buttons, keyboard reachable | | | Keep | | | Code |
| K5 | **Keep:** "leaving" shown only to HR, leadership and the person's own reporting line | | | Keep | | | `register.py` |
| K6 | **Keep:** branch and department groups start closed, with counts | | | Keep | | | Code |
| K7 | **Keep:** "Reports above your view" for a reader whose top is not the company's | | | Keep | | | Code |
| K8 | **Keep:** empty states that name the next step; "Reset view" only when something is set | | | Keep | | | Code |

**By persona, what hurts most:**
- **CXO:** OG1 (cannot see the shape), OG2 (the number is not the company), OG7 (folded boxes hide holes), OG3 (the CFO looks like he has no team).
- **HR Manager:** OG6 (cannot find), OG5 (control hides), OG3 and OG4 (cannot see why the chart is wrong), OG2 and OG8 (who is missing).
- **Department head:** OG3 (my team is not under me), then OG1. Today they cannot open the page at DTC at all.

**UX causes behind the three engineer bugs** (not designing the fixes):
- **Bug 1:** two controls for one choice (View and Arrange-by), one of them hidden in half the states, both placed among filters. The design in §6.3 removes the second control.
- **Bug 3:** the page draws one relationship (seat to seat) while people know another (person to person), and nothing on screen says when they differ.
- **Bug 4:** the seat card cannot tell a seat's head from a pool of people, and the setup tool keyed seats by job role, so a head who shares a job role with the team joins the pool.

## 5 · Flows

**HR finds a person.** Type two letters in "Find a person or a seat" → a list of seats and people (12 at most, "N more, type more of the name") → choose one → the path opens, the box or the row in a compact card is outlined and scrolled into view, a line says "Showing Sunil Arora in RSO · Delhi. Clear". Someone in no seat appears as "In no seat yet · RSO · Pitampura" and opens the "In no seat" list.

**CXO reads the top.** Page opens on Reporting lines: the top seat, the 5 team leads, and a card "Also under Owner: 17 seats with nobody under them · 31 people". Every lead box says "19 seats below · 75 people · 1 to fill". "Open every level" opens all; "Fold back to two levels" returns.

**HR fixes a missing manager.** Tile "19 no manager" or the dashed box beside the top → sheet with the 19 (name, job role, branch, joined) → "Set manager" opens their Employee record at Reports To (already in Frappe HR).

**HR plans a replacement (slice 065).** Seat sheet → person row → "Plan a replacement" → private note explained in four lines, optional reason from a short list → "Save the plan" → "Start hiring now?" with a warning → "Make an opening, not advertised" or "Not now".

**States** (in the prototype's State control): loading ("Loading the seats…" with skeleton tiles and chart), could not load ("We could not load the seats. Check your connection, then try again. Nothing you changed is lost." + Try again), nothing matches ("No seat matches those filters." + "Show every seat"), no seats yet and no permission (unchanged from today, K8). First-time tenant: unchanged ("Build it from your people").

**Hard cases drawn:** a 36-person pooled seat; a 31-person seat; a store head with 19 seats under them; the CFO with 18 people on records and no seats under the seat; Pitampura's second branch record; the reader whose top is not the company (store head).

## 6 · Design

### 6.1 Item 2 — fold after the second level

- **Rule:** the top level and one layer below it are open. Everything deeper is folded (agrees with PM D1). Branch and department groups start closed with their counts (as today, K6).
- **Every box with seats under it carries a roll-up line**, open or folded: `19 seats below · 75 people · 1 to fill · 1 leaving`. "Leaving" appears only for readers who may see leavers today (K5). Nothing is hidden without a number (the PM's WOW, made always-on).
- **Seats with nobody under them, when five or more share one manager, become one compact card** under that manager's row: `Also under Owner: 17 seats with nobody under them · 31 people`, then two columns of rows: `Chief Finance Officer — Chandigarh Sector 34 · [name]`, `RSO — Noida · 31 of 31 filled`, with "1 to fill", "1 leaving", "new hire placed" in bold words in the row. Each row is a button that opens the seat. Fewer than five stay as boxes. This is what keeps DTC's default view at 1,382 px.
- **Controls:** under each box, `Show the 19 below` / `Fold the 19 below` (a button with `aria-expanded`). In the toolbar, one button: `Open every level` / `Fold back to two levels`.
- Find and filters open the path to every match (as today).

### 6.2 Item 5 — "No reporting manager"

- **A dashed box beside the top seat** in Reporting lines: title `No reporting manager`, line `Not in any seat, and no manager on their record`, count `19 people`, chip `Needs a manager`. A tile `19 no manager` says the same.
- **It holds two kinds** (my recommendation; PM D3 differs): people with no manager on their Employee record (19 at DTC), and any seat other than the top with no parent (0 at DTC). The top is the parentless seat with most seats under it (PM D4).
- **The sheet:** heading `No reporting manager · 19 people`; text `These people have no reporting manager on their employee record, and no seat. Until they have one, nobody approves their leave, and they appear nowhere on this chart.` Table: Name, Job role, Branch, Joined, and for editors a `Set manager` link to the Employee record.
- **Who sees it:** HR and CXO (full-reach readers). A store head does not: it is company-wide, and their own top already says "reports above your view" (K7), which must never be mixed up with "no reporting manager".
- `[ASSUMPTION]` "Nobody approves their leave" is true when Leave Approver is unset as well. **The analyst must check this sentence against Frappe HR's leave approver rules before it ships** (ux-learnings: trace a consequence sentence).

### 6.3 The arrange-by control (bug 1)

- **One control, always visible, above the chart, outside the filters:** `View: Reporting lines · By branch · By department · List`. A segmented control on desktop; a 2 × 2 grid of 44 px buttons on a phone. It replaces both "View" and "Arrange by". No combination is ever dead, so nothing has to hide.
- **Opens on `Reporting lines`** (agrees with PM D2).
- The engineer's alternative (keep two dropdowns and switch to the chart when Branch is picked on the list) also works. Mine removes a control instead of adding a rule.
- Filters move into a `Filters` disclosure under the toolbar. It opens by itself and says `Filters (on)` when a filter is set. The sentence about greying stays inside it.

### 6.4 Improvements for the big chart

Counted against existing surfaces first (§2.3). Rung: client code unless stated.

| # | Improvement | Must / should / later | Already there? | Rung and why |
|---|---|---|---|---|
| 1 | Compact card for seats with nobody under them | **Must** | No | Client code in `posNode` / `kidsHTML`. Without it OG1 stays |
| 2 | Roll-up line on every box with seats under it | **Must** | Partly ("N more below") | Client code; all rows are already loaded |
| 3 | Find a person or a seat, opening the path | **Must** | On the Organisation page only | Client code over loaded rows; reuses the path-opening the filters use. No new server call for seats and seated people |
| 4 | One View control (fixes bug 1) | **Must** | Two dropdowns | Template and client code; removes one control |
| 5 | "No reporting manager" box, tile and sheet | **Must** | No | New code: one grouped query for active people with no manager and no seat, returned with `position_table` |
| 6 | "82 in no seat" tile and list, grouped by branch, with the matching seat named | **Must** (PM said later; I disagree, see Q2) | No | Same query as 5, widened to every active person with no seat. No auto-placement |
| 7 | "18 report here on their records" chip and list, on a seat whose people's managers disagree | Should | `reporting_mismatches`, no screen | Reuse **after rewriting it to grouped queries** (it does ~3 queries per seated person) |
| 8 | "Holds people of 3 managers" chip on a pooled seat | Should | No | Client code if the payload carries each person's manager; one extra field |
| 9 | "Joined 14 Oct, hired for this seat" chip for 30 days | Should | No | Comes with PM item 6 (the hook). **At DTC it shows nothing yet: 0 employees came through Frappe hiring** |
| 10 | Vacancy shown on the box | — | **Yes** ("to fill", dashed empty seat) | Keep |
| 11 | Dense list | — | **Yes** | Keep; add a caption `24 of 90 seats` |
| 12 | Phone reading mode: one level at a time, rows with counts, "Up one level" | Should | The Organisation page's re-root model | Client code; the same idea, not the same screen |
| 13 | Span-of-control flag on Positions | Later | On the Organisation page | Roll-up line already shows "19 seats below" |
| 14 | `Print this view` with a print stylesheet (what is open prints; private chips never print; header "Confidential, for management") | Later | No | CSS only. The PM said no PDF; this is not a PDF export, so Surbhi decides (Q8) |
| 15 | One word for one thing: "seat" is the record; capacity reads "31 of 31 filled"; the first tile reads `90 seats · 363 people in them` | Should | No | Words only |

### 6.5 Item 7 — where "Plan a replacement" sits (for slice 065)

Drawn in the prototype for the **HR Manager** persona only. The CXO and the store head never see any of it.

- **Seat sheet, per person:** a `Plan a replacement` link. When set: chip `Replacement planned until 19 Jan 2027` and `Remove the plan`.
- **Confirm sheet:** heading `Plan a replacement for [name]?`. Body: `A private note so HR can start finding cover before a seat empties. It is not a score, and nothing works it out for you.` Then four lines: `Only people with the HR Manager role see it.` · `[First name] does not see it on any screen, and neither does their manager.` · `It is never used in reviews, ratings or pay.` · `It ends by itself after 90 days unless HR renews it. It is erased when [first name] leaves this seat.` Optional reason from a short list (`Has said they may leave`, `Contract ends soon`, `Long leave expected`), with `A short list on purpose: no free text about a person's private life.` Buttons `Cancel` · `Save the plan`.
- **Then the offer:** `Start hiring now?` `We can make a job opening for RSO · Noida now. It is not advertised: it stays with HR until somebody publishes it.` Warning: `Anyone who can read job openings will see this one. If [first name] might hear of it, wait.` Buttons `Not now` · `Make an opening, not advertised`. Result: `Opening made: [id], not advertised. Open it`.
- **On the chart:** chip `Replacement planned · HR only` on the box; a tile `1 replacement planned · Only HR sees this`; a filter option `Only seats with a replacement planned`. **All of it is marked private: never printed, never in an export, never on the Organisation page, never in the list for anyone else.**
- Words follow PM D11 ("Plan a replacement", not "flight risk").

⚠ **COMPLIANCE / ⚠ DECISION (owner: Surbhi with hrms-security-privacy-engineer):** (a) an unpublished Job Opening is still readable by every role that reads Job Opening, so the opening can reveal the plan; (b) at DTC the HR Manager role may not be able to open Positions at all (§1), so "HR Manager only" may mean nobody; (c) the change history of a cleared note must be erased too (PM §3). Nothing in 065 should be built until these three are settled.

### 6.5a Round 2 (v2) — colour code and the private red flag

Surbhi approved v1 on 21 Oct 2026 ("looks amazing") and asked: *"use colour coding to highlight replacement planning employees, new seats, and existing vacant seats. For the replacement plan employees show a small red flag in front of their name."* Built in `prototype-v2.html`; v1 is kept.

**⚠ Bad news first: this puts slice 065's private note on the chart.** The red flag and the red tone are drawn from the "Plan a replacement" note. So **065 must be built together with them, with its privacy rules (PM D8–D10 and §6.5), and no flag may appear before that note exists.** The colour code for new and vacant seats does not depend on 065 and can ship in 064 on its own.

**What a "new seat" is (recommendation).** A seat made in the **last 30 days**, and **after the day the chart was first set up**. The date is the seat's own creation date, which Frappe keeps on every record; the first set-up day is the earliest creation date among the company's seats. No new field, no setting.
- Why the second part: **fact**, at DTC 89 seats were made by the set-up tool on 14 Oct and the CFO seat on 16 Oct. "Made in the last 30 days" alone would mark all 90 seats new until mid-November, which tells nobody anything. With the rule, only the CFO seat is new today.
- Not `effective_from`: it is empty on all 90 DTC seats.
- 30 days is a fixed number in the code, not a setting (no-over-engineering §2).

**The three tones** (a 4 px left bar, a light tint, and always a word):

| Tone | Meaning | Word or shape that goes with it | Who sees it |
|---|---|---|---|
| Blue | New seat | Outlined pill `New seat · 16 Oct`; in rows `new seat` | Everyone who sees the seat |
| Amber | Place to fill in an **existing** seat | `1 to fill` | Everyone who sees the seat |
| Red | Somebody in the seat has a replacement planned | A red **flag icon** before their name (spoken as "Replacement planned"), and `1 replacement planned` when the name is not on the box | **HR Manager only** |

**When two apply, one rule:** red (plan) beats blue (new) beats amber (existing vacancy).
- **New and empty → blue**, with `1 to fill` still written in blue. Why: a new empty seat is a new job to hire for, and Surbhi asked to tell new seats apart from existing vacancies. The words keep the vacancy visible, and every "to fill" count includes it, split as `2 to fill (1 new)`.
- **Plan beats both** for HR, because it is about a person and needs action first. Underneath, the public tone is still there: for anyone else, in print, or with plans hidden, the same box shows its blue, amber or plain tone.

**Count lines on folded boxes** now take two lines: size first (`20 seats below · 75 people`), then what needs somebody (`1 to fill (1 new) · 1 leaving · ⚑ 1 planned`). "Leaving" and "planned" appear for HR only. The tile `2 to fill` reads `1 in existing seats, 1 in new`; a new tile `2 new seats · Made in the last 30 days` filters to them.

**Key:** one line under the filters: `New seat (made in the last 30 days)` · `To fill (existing seat)` · for HR only `⚑ Replacement planned · only HR Managers see this`. `Hide the key` / `Show the colour key`. Not remembered between visits (no setting).

**Privacy, not negotiable:**
- The Owner (CXO) and the store head get **no flag, no red tone, no key entry, no count, no tile, no filter option and no "Plan a replacement" link**. A planned person's box looks exactly like any other. Measured in the prototype: 0 private elements and no words "replacement" or "planned" on their screens, in all 12 of their combinations.
- **Leaving is HR-only in v2** (coordinator's instruction). The leaving tile is then **absent** for others, never "Nobody leaving", which would be untrue. ⚠ This narrows today's rule (HR, leadership and the person's reporting line see leaving dates, K5). Q13.
- **Never in print or export:** every private mark carries a class that print removes, and the red tone exists only on screen. Measured with print emulation: 0 flags, no plan words, plan rows print in their public tone.
- **Screen sharing:** there is no "share" mode in the product. HR gets one link in the key, `Hide replacement plans (before you share your screen)`, which removes every flag, the red tone, the tile and the filter until they turn it back on. Q14 asks whether it should start hidden.
- Search results never show a flag.

**Clashes checked:** "Holds people of 3 managers" and "18 report here on their records" stay purple (information), so they cannot be mistaken for the three tones. "New hire placed" stays green: a person, not a seat. The "Covered" tag lives on the Organisation page in purple, so there is no clash. The red flag sits beside amber and blue only, never beside red-for-wrong (nothing else on this page is red).

**Contrast, measured (light and dark):** blue pill 5.7:1 and 6.5:1; red words 6.5:1 and 6.8:1; secondary text on a tint 6.4:1 after moving it from `--text3` to `--text2` (it measured 4.4:1 before). **One existing token pair fails narrowly:** `--amber` text on `--amber-lt` measures **4.42:1** for 12 px text, under the 4.5:1 AA line. It is the product's existing "to fill" chip, not new in v2. Q12.

**Measured, v2:** 3 persons × 2 devices × light and dark × 3 views. No sideways page scroll, no text under 12 px, no control under 24 px on desktop or 44 px on the phone, no script errors. The default chart still fits at 1,382 px. With Delhi opened it grows to 1,610 px and scrolls inside the chart frame only.

### 6.5b Round 3 (v3) — a chart that cannot outgrow the screen; plans as a filter

Surbhi on v2: *"The design breaks when a lot of reporting hierarchies are open. Find a good solution to this."* and *"When we show above the hierarchy '2 planned replacements' it seems like the replacements are planned for that specific position - remove that; instead keep a filter on the top for showing replacements planned."* Built in `prototype-v3.html`; v1 and v2 are kept. **v3 replaces two things above:** the "Open every level" button (§6.1, §6.4) and the replacement-plan tile and count lines (§6.5, §6.5a).

**What broke (reproduced on v2, measured).** I opened every level on DTC's shape plus a synthetic deep branch (Sample): Owner › Head of Operations › Regional Manager › 10 Area Managers › Store Manager › Floor Supervisor › Section Lead › 6 seats, which is 8 levels and 30 extra seats.
- **Width:** the chart was 5,326 px inside a 1,384 px frame.
- **Unreadable lines:** one connector line ran 5,086 px. You could never see both ends.
- **Lost context:** the top box sat about 2,600 px to the right, so the frame opened on blank space. The deepest seat was 1,087 px below the top and 821 px to one side.
- **Height:** the chart was 2,043 px tall, the page 2,549 px.
- **Phone:** nothing overflowed (one level at a time), but at 7 levels deep the only way back was "Up one level", with no path shown.
- **No overlaps:** 0 boxes overlapped. It was size and lost context, not collision.
- Same in light and dark.

**Surfaces counted first.**
- The Organisation page already re-roots on a box, with a breadcrumb, "Up one level" and "Top".
- The Positions phone view already shows one level at a time.
- The List view already shows "everything".

v3 reuses those patterns. It adds no new screen and no new component.

**Chosen: a sliding three-row window.** One rule: the chart never shows more than three rows.
- **Row 1:** the current top box.
- **Row 2:** its family.
- **Row 3:** at most **one** opened family, drawn as a full-width band under row 2, headed "Under Manager · Delhi · 20 seats below · 75 people", with a Fold button.
- **Opening a second box in row 2 folds the first** (one family at a time).
- **"Show the N below" on a box in row 3 slides the window down one level.** That box's parent becomes row 1. The chart never grows; it moves.
- **A sticky breadcrumb above the chart** ("You are here: Owner › Head of Operations › … › Section Lead"). Every step is a link, plus "Up one level" and "Back to the top". The phone view gets the same breadcrumb.
- **Rows that do not fit the frame wrap into rows of boxes** under one connector, headed "10 seats lead teams under Regional Manager North. Shown in rows so they fit the screen." The number per row comes from the frame width, not a setting.
- **Compact cards over 12 seats spread across the frame** instead of growing tall. Sales by department: chart height went from 2,050 px to 1,127 px.
- **Find puts the target in row 3**, with its parent and grandparent above it.
- **Filters still grey what does not match** (Surbhi, 15 Oct). Because only one family is open at a time, the path to every match can no longer open by itself. Instead, every box says "3 matching below", and its count leads you down. **This replaces the "open every match" rule** (ux-learnings checklist), on purpose.
- "Everything at once" is the List view, which already exists.

**Rejected:**
- **Indented outline on desktop:** robust, but it throws away the chart Surbhi approved. Kept for the phone.
- **Focus re-root alone:** fixes depth but not width. Ten wide team leads still overflow.
- **Accordion alone:** fixes width, but depth still grows the page.
- **Wrapping alone:** fixes width, but depth and lost context remain.
- **Mini-map or pan and zoom:** a second renderer and a bespoke component (no-over-engineering §2). Zoomed out, text goes under 12 px; zoomed in, context is lost. Neither works by keyboard.

The window combines re-root, accordion and wrap because each one alone left one failure open.

**Measured on v3 at the worst case.**
- **Combinations:** HR Manager, Owner and store head × desktop 1440 and phone 390 × light and dark × Reporting lines, By branch, By department and List.
- **Worst-case steps:** home; the biggest family opened; then sliding down all 8 levels.
- **Result:** 0 failures. No sideways scroll of the page or the chart frame. No text under 12 px. No control under 24 px on desktop or 44 px on the phone. 0 boxes overlapping. No script errors.
- **The default view still fits:** 1,382 px in a 1,382 px frame.
- **Chart height at each step of the deep slide:** 1,032 → 1,302 → 812 → 818 → 608 → 608 → 699 px.
- **Context kept:** with the page scrolled to the bottom, the breadcrumb was still on screen, 52 px from the top.

**Replacement plans.**
- **Gone:** the planned-replacements tile and every "N planned" in count lines and rows.
- **Every count line now starts with "Below:"**, so it cannot read as being about the box beside it ("Below: 2 to fill (1 new) · 1 leaving"). Checked on every rendered line: 0 without "Below:".
- **A multi-person seat names the flagged person first**, flag before the name, instead of showing a count.
- **The tiles ignore the plan filter**, so no tile turns into a count of plans. With the filter on, the tiles stay "91 seats | 2 to fill | …", unchanged.
- **The filter:** the filter bar is visible again, not folded, as in today's product. In it sits `⚑ Replacement plans`, with "Show every seat" / "Only seats with a replacement planned". It greys like the others.
- **Privacy:** the filter, flag and red tone are for the HR Manager only. For the Owner and store head the control **does not exist**: not hidden, not greyed. Measured: 0 private elements, no plan words and no plan filter on their screens in every combination.
- **Print and "Hide replacement plans"** still strip every flag, and hiding also clears the filter.

### 6.5c Round 4 (v4) — seats with nobody under them become one box in the hierarchy

Surbhi on v3, about the band "Also under Owner: 17 seats with nobody under them · 31 people": *"keep this section same as no reporting manager, under the hierarchy itself, instead of a separate section, on clicking it can have this panel visible, in some better way"*. Built in `prototype-v4.html`; v1–v3 are kept.

**Surfaces counted first.**
- The "No reporting manager" box already opens a side panel.
- Every seat already opens the seat panel (the editor's read view).
- The Organisation page opens nothing in place.

So the side panel is already this page's one pattern for "what is behind a box". v4 uses it for both group boxes and adds no new component.

**The rule.**
- **Five or more seats with nobody under them**, under one manager, become **one box in that manager's row**, beside the team leads, joined by the same connectors.
  - Title: `Seats with nobody under them`.
  - Second line: `Report to Owner`.
  - Count: `17 seats · 31 people`.
  - Words line: `Inside: 1 new seat filled`.
  - Last line: `Select to see the 17`.
  - It is drawn dashed, exactly like `No reporting manager`. Fewer than five stay as ordinary boxes.
- **A manager whose whole team is childless seats** (Delhi's 20, Noida's 11) has no lone group box. Its "Show the 20 seats below" opens the panel directly, so it is one click, not two. The window (§6.5b) only ever opens families that contain team leads.
- **The panel:**
  - **Placement:** the right-hand side panel on desktop, a bottom sheet on the phone. It is the same component as the seat panel and `No reporting manager`.
  - **Contents:** heading `17 seats with nobody under them`, a line `Seats that report to Owner · Chandigarh Sector 34 and have nobody under them. 31 people.`, then one row per seat. Each row keeps its colour (blue new, amber to fill, red plus flag for HR only) and words.
  - **A row opens the seat panel**, which offers `Back to the 17 seats`.
  - **Closing:** `Close`, Escape, or a click outside. Focus moves to the heading on open and **returns to the box that opened it** on close.
- **Find:** picking a seat that lives in a group shows its manager's family, then opens the panel with that row outlined, scrolled into view and focused.
- **Filters:** a group box with no matches is greyed; one with matches says `2 matching inside`. In the panel, rows that do not match are greyed and say `does not match the filters`. Nothing is dropped.
- **Colour:** the group box takes the same order as a seat, over its members: red (HR only, screen only) > blue > amber. The words line says what is inside. `No reporting manager` is no longer tinted amber, because amber means "to fill" in the key; its chip `Needs a manager` carries the meaning.
- **Phone:** the phone list already shows every seat as a row, so it has no group row. `No reporting manager` opens the same bottom sheet.

**Rejected:**
- **An inline panel anchored under the box:** a second kind of expansion inside the three-row window. Two things open at once break the "one open family" rule. A box at the right end of a row would push the panel off the frame.
- **Reusing the row-3 band:** that is the separate-looking section Surbhi asked to remove, and a group has no deeper levels to slide into.
- **A popover:** too small for 20 rows, and weak with a keyboard and a screen reader.

**Measured on v4.**
- **Worst-case run as in v3:** 3 persons × desktop and phone × light and dark × all views × the deep test branch, sliding all 8 levels. **0 failures:**
  - no sideways scroll of the page or the chart
  - no text under 12 px
  - no control under 24 px on desktop or 44 px on the phone (the phone panel's `Close` was 40 px and was fixed)
  - no overlaps, no script errors
  - every count line starts with `Below:` or `Inside:`
  - no private mark for the Owner or store head
- **The default view fits exactly:** 1,382 px in a 1,382 px frame. The old band is gone (0 found).
- **Keyboard:** Enter on the group box opens the panel with focus on its heading (17 rows); Escape returns focus to the box.
- **Find:** "Payroll" opens the panel with that row focused.
- **Branch filter:** the box shows `2 matching inside`, and 15 of 17 panel rows are greyed.
- **Print:** no flags. **Hide:** no flags and no plan filter.

### 6.6 Words (English; Hindi not drafted)

| Place | Words |
|---|---|
| Page | `Positions` / `Every seat in the organisation, who is in it, and which are empty.` Store head: `Your part of the organisation: Manager · Delhi and the seats under it.` |
| Data line | `Figures as at 21 Oct 2026, 09:40.` |
| Tiles | `90 seats` / `363 people in them` · `1 to fill` / `Show these seats` · `1 leaving` / `in the next 60 days` · `82 in no seat` / `Not on this chart yet` · `19 no manager` / `No reporting manager` · `1 replacement planned` / `Only HR sees this`. Zero states: `None to fill` / `Every seat is filled`; `Nobody leaving` |
| Toolbar | `View` · `Reporting lines` `By branch` `By department` `List` · `Find a person or a seat` (placeholder `Type a name or a seat, e.g. RSO`) · `Open every level` / `Fold back to two levels` · `Print this view` (later) |
| Find | `No seat or person called that.` Store head: `…in your part of the organisation.` Overflow: `8 more. Type more of the name.` Focus line: `Showing [name] in RSO · Delhi. Clear` |
| Box | `19 seats below · 75 people · 1 to fill` · `36 of 36 filled · [name] +35` · `Nobody in this seat` · chips `1 to fill`, `1 leaving`, `New hire placed`, `18 report here on their records`, `Holds people of 3 managers` |
| Fold | `Show the 19 below` / `Fold the 19 below` |
| Compact card | `Also under Owner: 17 seats with nobody under them · 31 people` |
| No manager | as §6.2 |
| In no seat | `In no seat · 82 people` / `82 of 445 active people hold no seat, so they are not on this chart and not in the counts above. Most joined in the last two months.` Pitampura: `There is no seat at Pitampura. The Pitampura seats use a second branch record, "DTC - PITAMPURA". HR should merge the two branch records, or move these people.` Row: `20 RSO · matching seat: RSO · Noida (31 of 31)` or `· no matching seat` |
| Record mismatch | `18 people report to this person on their employee records` / `Their seats sit under other seats on this chart, so nobody shows under this box:` (list) / editor: `To fix it, open each seat and set Reports to to this seat. A seat shared with another manager's people needs splitting first.` / CXO: `HR can move these seats under this one.` |
| Pooled seat | `This seat holds the people of 3 managers` (list) `That is why it reads like one person with 35 others in their seat.` Editor: `Give the head a seat of their own, then move each group under its own manager.` |
| Error | `We could not load the seats. Check your connection, then try again. Nothing you changed is lost.` · `Try again` |

**Hindi:** not drafted. This is an HR and management screen, and nfr-budget §7 asks for EN/HI parity on employee-facing surfaces. ⚠ DECISION for Surbhi if DTC's HR wants Hindi here. If it does, every string above runs about 30% longer; the 208 px boxes and the compact card would need a check at that length.

## 7 · Accessibility and privacy

- Every box, compact-card row, fold control and tile is a `button`. Fold controls carry `aria-expanded`. The View control is a labelled group of buttons with `aria-pressed`. Find has a visible label; Escape clears it. Sheets are `role="dialog"`, `aria-modal`, focus moves to the heading, Escape closes.
- Colour is never alone: every amber box also says `1 to fill` or `1 leaving` in words; the dashed "No reporting manager" box also has a chip in words.
- Measured in the prototype (Playwright, 21 Oct 2026, 3 personas × 3 views × 2 devices): no page wider than the screen, no text under 12 px, no control under 24 px on desktop or 44 px on the phone, no script errors. The prototype's own body text is 13 px (`--fs-base`), above our 12 px floor.
- **Privacy:** no new personal fact appears for anyone who cannot already see it, except the "No reporting manager" and "In no seat" lists (names, job role, branch, joining date) for full-reach readers, who can already read the Employee list. The store head sees neither. The replacement note is HR-only, never printed, never exported (§6.5). Print carries `Confidential, for management`.
- **Small groups:** the roll-ups are headcounts of seats the reader can already open one by one, not leave, pay or rating figures, so the small-group rule does not apply. "Leaving" counts follow today's visibility rule (K5); a "1 leaving" on a store head's one-person seat names the person exactly, as the tag does today.

## 8 · Prototype

- **v4 (current):** `docs/slices/064-organogram-improvements/prototype-v4.html`: seats with nobody under them as one box in the hierarchy, opening the side panel (§6.5c). Not published.
- v3 (kept): `docs/slices/064-organogram-improvements/prototype-v3.html`: the sliding three-row window and breadcrumb, and the HR-only "Replacement plans" filter (§6.5b). Use the new **Shape** control ("DTC + a deep sample branch (8 levels)") to try the worst case. Not published.
- v2 (kept): `docs/slices/064-organogram-improvements/prototype-v2.html`: the colour code, the private flag and the key (§6.5a). Switch Person between HR Manager and Owner (CXO) to compare. Not published (no Artifact tool). v2 data is Sample: two plans, one new empty Pitampura seat. The new CFO seat (16 Oct) is real.
- v1 (kept): `docs/slices/064-organogram-improvements/prototype-v1.html` (invented names only, so it may live in the repo; the shape is DTC's).
- **Not published**: no Artifact tool in this run. The lead session publishes it.
- Controls: Person (HR Manager · Owner (CXO) · Store head, Delhi), Device (Desktop 1440 · Phone 390), Theme, State (Loaded · Loading · Could not load).
- Try: the tiles; View; type `RSO` or a name in Find; `Open every level`; click a compact-card row; the CFO row (record mismatch); the Back Office box (pooled seat); the dashed "No reporting manager" box; `82 in no seat`; as HR, open RSO · Noida and `Plan a replacement`.
- What is not real: `+ Add a seat`, `Change this seat`, `Advertise it`, `Set manager` show a note saying they open today's screens unchanged.

## 9 · Checks

**Nielsen, where it bites:** visibility of status (roll-ups, data line, focus line); match with the real world (one word for "seat"); user control (Clear, Fold back, Reset view); consistency (one View control, the same box everywhere); error prevention (the opening warning in 065); recognition over recall (Find instead of filters); flexibility (Find for experts, folding for readers); minimalist design (filters folded); help users recover (the "In no seat" and "No manager" lists say what to do).

**Persona walkthrough (steps to finish the top task):**

| Persona | Task | Today (inference) | After |
|---|---|---|---|
| HR | Find the seat of one named RSO | Change View, pick branch, pick role, scan a list or scroll a wide chart: 4–6 steps | Type 3 letters, pick: 2 steps |
| CXO | "Where are we short?" | Tiles, then hunt in the chart | Tiles, then the roll-up line on each lead box: 1 look |
| CXO | "Is everyone on the chart?" | Not answerable | Tile `82 in no seat`: 1 look |
| HR | Who has no manager? | Desk report, by hand | Tile, then the list: 2 steps |
| Store head | My empty seats | Not open to them at DTC | Their line with roll-ups, `Only seats with places to fill` |

**Frontline bar:** not applicable; no frontline person uses this page.

**Red team:** brand-new tenant → unchanged empty state. 10× data (900 seats, 4,500 people) → Find and roll-ups run over rows already loaded; DevOps should time it, and the "no seat" query must stay one grouped query. A team lead with 4 leaf seats and 1 team → 5 boxes, no card (fine). A card with 60 rows (a flat tenant) → the card needs its own scroll at about 12 rows; **not drawn**, flag for the engineer. Network drops → the error state; nothing is edited on this page except through today's dialogs. A reader who may not see leavers → no "leaving" in roll-ups or tiles. Wrong top (two big parentless seats) → the smaller goes into "No reporting manager"; Q4 covers it.

## 10 · Usability test plan (High-impact items 1–6)

Five people: two from DTC HR, the DTC owner or a manager who reads the chart, two HR people from another tenant or a demo. Laptop, then a phone for the owner. On the prototype first, then on a copy with real data.

| Task | Success | What would change the design |
|---|---|---|
| Find where a named RSO sits | Under 15 seconds, no help | Over 30 s for two people → Find moves to the top of the page and gets a keyboard shortcut |
| Say how many seats are empty under the Delhi manager without opening it | Correct answer from the roll-up | Wrong or opened it → roll-up wording changes |
| Say whether everyone at DTC is on the chart | Mentions the 82 | Missed by two → the tile goes first |
| Find the people with no manager | Opens the box or the tile | Missed by two → the box moves inside the tree as the first item |
| Read the compact card as "these report to the Owner" | Says so unprompted | Read as a separate group by two → card goes beside the row instead of below it |

## 11 · What the business analyst must turn into acceptance criteria

1. Default view: Reporting lines; top plus one layer open; deeper folded; groups in branch and department views start closed.
2. Five or more leaf seats under one manager draw as one card below the row; four or fewer as boxes. Card rows are buttons and carry to-fill, leaving and new-hire words.
3. Roll-up line on every box with seats under it: seats below, people, to fill (if any), leaving (only for permitted readers).
4. Find: from two characters; seats by title, people by name; at most 12 results; choosing one opens the path, outlines the target, scrolls it into view, and shows the focus line with Clear. Store head finds only within their own line.
5. One View control, always visible, four options, keyboard operable.
6. "No reporting manager": people with no manager and (if any) parentless seats other than the top; hidden from readers without full reach; the sheet's "Set manager" opens the Employee record.
7. "In no seat" tile and list over active Employees, grouped by branch, naming a matching seat by job role and branch, or "no matching seat". The query count does not grow with headcount.
8. If 7 (record mismatch) is taken: `reporting_mismatches` rewritten so its query count is the same at 20 and 1,000 people.
9. Every count on the page is over the same rows the reader can see (K1).
10. Desktop default view at DTC's shape fits within 1,440 px; nothing on a 390 px phone scrolls sideways; text ≥ 12 px; targets ≥ 24 px desktop, ≥ 44 px phone.
11. The consequence sentence in the "No reporting manager" sheet is checked against Frappe HR's leave approver rules.
12. (v2) "New seat" = creation date within 30 days **and** later than the company's earliest seat creation date. Tone order: plan > new > existing vacancy. A new empty seat is blue and still counted in "to fill", shown as "(1 new)".
13. (v2) For any reader who may not see the replacement note: no flag, no red tone, no key entry, no tile, no count, no filter option, no link, and no change in layout that hints at one. Tested as an automated check over the rendered page.
14. (v2) Print and export never contain a flag, the red tone or plan words. "Hide replacement plans" removes all of them on screen until turned back on.
15. (v2) No flag is drawn unless a replacement note exists, so the flag ships only with slice 065.
16. (v3) The chart shows at most three rows: the top, its family, and one opened family. Opening a second family folds the first. "Show the N below" in row 3 slides the window down. A breadcrumb with "Up one level" and "Back to the top" is always on screen. At an 8-level, 10-wide test branch, neither the page nor the chart frame scrolls sideways, and no boxes overlap.
17. (v3) A row of team leads wider than the frame wraps into rows. A compact card with more than 12 seats spreads across the frame.
18. (v3) Every count line on a box starts with "Below:". No tile or count line ever counts replacement plans. The tiles ignore the Replacement plans filter.
19. (v3) The "Replacement plans" filter exists only for the HR Manager. It greys non-matching seats, and boxes show "N matching below".
20. (v3) "Open every level" is removed. The List view is the "everything" view.

## Open questions (for Surbhi, each with my recommendation)

| # | Question | My recommendation | Owner | Blocks |
|---|---|---|---|---|
| Q1 | "No reporting manager": seats with no parent (PM D3), or **people** with no manager? At DTC the seat version is empty | **People, plus any parentless seat other than the top** | Surbhi; PM | §6.2 |
| Q2 | Show the 82 people in no seat in this slice (PM said later)? | **Yes, tile and list, no auto-placement.** Without it the CXO's first number is wrong by 18% | Surbhi; PM | §6.4 item 6 |
| Q3 | One View control (4 options) or the engineer's "switch to the chart when Branch is picked"? | **One control.** It removes a control instead of adding a rule | Surbhi; engineer | Bug 1 fix |
| Q4 | Compact card from how many leaf seats? | **5** | Surbhi | §6.1 |
| Q5 | "Seat" for the record and "31 of 31 filled" for capacity, everywhere? | **Yes.** First tile `90 seats · 363 people in them`, never `SEATS` alone | Surbhi | Words |
| Q6 | Who sees the "18 report here on their records" chip? | **HR and CXO.** Not store heads | Surbhi; security | §6.4 item 7 |
| Q7 | Replacement plan (065): HR Manager only, or HR and the owner? At DTC the HR Manager role may not open Positions | **HR Manager only, as the PM says, and first fix who can open Positions at DTC** | Surbhi; security | Slice 065 |
| Q8 | `Print this view` (CSS only) in 064 or later? | **Later.** Cheap if the board pack is a real need | Surbhi; PM | Nothing in 064 |
| Q9 | Phone reading mode in 064? | **Should, after the musts**. Only if the owner reads the chart on a phone | Surbhi | §6.4 item 12 |
| Q10 | Hindi on this HR screen? | **No for now**; employee-facing only | Surbhi | Words |
| Q11 | Merge the two Pitampura branch records? | **Yes, as data work by DTC's HR**, before judging "in no seat" | Surbhi; DTC HR | OG14 |
| Q12 | v2 adds a text blue (`#1F5F99` light, `#8DBDEB` dark) that is not in `design_system.html`. The existing amber "to fill" chip measures 4.42:1, just under AA. Add a blue pair to the design system, and darken `--amber` slightly? | **Yes to both, as one token change.** It touches every page, so it is a decision, not a fix | Surbhi; engineer | Shipping the colour code |
| Q13 | Leaving dates HR-only, as in v2, or today's rule (HR, leadership, the person's reporting line)? | **Keep today's rule.** A leaving date is an announced fact the reporting line needs to cover the gap. Only the replacement plan needs HR-only. I drew HR-only as instructed so you can see it | Surbhi; security | §6.5a |
| Q14 | Replacement plans: shown by default for HR, with "Hide … before you share your screen", or hidden until HR turns them on each visit? | **Shown, with the hide link**, because HR uses the page alone more often than in a meeting. Choose "hidden until turned on" if HR at DTC often shares this screen | Surbhi | §6.5a |
| Q15 | "New seat" = made in the last 30 days and after the first set-up day? | **Yes.** At DTC this marks only the CFO seat today | Surbhi | §6.5a |
| Q16 | With one family open at a time, filters no longer open the path to every match; boxes say "N matching below" instead. Acceptable? | **Yes.** Opening every match is exactly what made the chart break. The count leads you down, and the List view shows all matches at once | Surbhi | §6.5b |
| Q17 | The filter bar is visible again (v1 had folded it into "Filters"), because the plan filter has to sit "on the top". Keep it visible for everyone? | **Yes.** One visible bar, as in today's product | Surbhi | §6.5b |

## Assumptions

- `[ASSUMPTION]` 445 active employees today is the right base; the request's 476 includes people who are not Active.
- `[ASSUMPTION]` The Frappe rule that Custom DocPerm rows replace standard DocPerm for a doctype holds on DTC's version.
- `[ASSUMPTION]` "Nobody approves their leave" is true for a person with no manager; to be checked (§6.2).
- `[ASSUMPTION]` Today's page widths (18,000 px; 4,700 px) are worked out from the CSS, not seen.
- `[ASSUMPTION]` The prototype's leaf card connector (a dashed line from the row) reads as "also reports to the manager above". To be tested (§10).

## Handoff note

To the business analyst and the engineer: **the fold rule is not the fix at DTC; the compact card is.** Build items 1–6 of §6.4 together, or the page stays too wide or keeps hiding 18% of people. I disagree with the PM on D3 (the seat-based box is empty at DTC) and on putting "in no seat" later; both are Surbhi's call (Q1, Q2). Do not reuse `reporting_mismatches` as it stands: it queries inside a loop. The engineer's bug 3 and 4 fixes are data work at DTC and need Surbhi's word; my chips only make the next such fault visible. Slice 065 must not start until the three points in §6.5 are settled with security.

## Subtract pass

Removed on this pass: a span-of-control chip (the roll-up says the same); a "scenario" switch showing the chart after the CFO's seats are moved; Hindi strings; a "remember my last view" setting; list grouping by the View choice (the single View control makes it unnecessary); a separate fold button on branch and department boxes (the box itself folds); the job role filter in the prototype (unchanged in the product). Kept "Print this view" only as a "later" line, not in the musts.

v2 subtract pass: no "presenting" mode (one hide link does the job); no remembered key setting; no flag in search results; no colour on branch and department group boxes (their count line says it in words); no fourth tone for "leaving" (it stays an amber word).

## Parity rows that change from v3 to v4 (for the analyst writing the 064 spec)

| # | Area | v3 behaviour (spec may say this) | v4 behaviour (use this) |
|---|---|---|---|
| PV-1 | Seats with nobody under them | Five or more under one manager are drawn as a compact card **below** the row ("Also under Owner: 17 seats with nobody under them · 31 people") | They are **one dashed box inside the manager's row**, beside the team leads, joined by the same connectors: `Seats with nobody under them` / `Report to Owner` / `17 seats · 31 people` / `Inside: …` / `Select to see the 17`. Fewer than five stay as ordinary boxes (unchanged) |
| PV-2 | Opening that group | Not applicable (always visible) | Selecting the box opens the **side panel** (desktop right panel, phone bottom sheet): heading `17 seats with nobody under them`, one row per seat with its colour and words. A row opens the seat panel, which offers `Back to the 17 seats` |
| PV-3 | A manager whose whole family is childless seats | "Show the N below" opened the row-3 band holding the compact card | "Show the N seats below" opens the **side panel directly**. No row-3 band, and the window does not move |
| PV-4 | Long compact cards (more than 12 seats spread across the frame) | Rule existed | **Removed**: no card is drawn on the chart any more |
| PV-5 | "No reporting manager" | Dashed box with an amber tint; opens a side panel | Same dashed **group** box as PV-1, with **no amber tint** (amber means "to fill"), plus `Select to see the 19`. Same panel, same close and focus rules |
| PV-6 | Closing a panel | Close / Escape / outside click | Same, and **focus returns to the box that opened it**; focus moves to the panel heading on open |
| PV-7 | Find | A seat inside a compact card was outlined on the chart | Picking a seat that sits in a group shows its manager's family, then **opens the panel with that row outlined and focused** |
| PV-8 | Filters | Card rows greyed in place; boxes say `N matching below` | The group box is greyed when nothing inside matches, otherwise says **`N matching inside`**. Panel rows that do not match are greyed and say `does not match the filters` |
| PV-9 | Count-line wording check | Every count line starts with `Below:` | Every count line starts with **`Below:` (a seat) or `Inside:` (a group box)** |
| PV-10 | Colour on a group | Not applicable | The group box takes the member order: red (replacement plan, HR only, screen only) > blue (new) > amber (to fill) |
| PV-11 | Phone | Outline rows; the phone has no card | Unchanged: every seat is a row. `No reporting manager` opens the bottom sheet; its `Close` is at least 44 px |
