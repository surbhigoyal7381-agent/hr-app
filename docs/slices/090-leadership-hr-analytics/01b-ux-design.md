---
slice: 090-leadership-hr-analytics
artifact: 01b-ux-design
author: hrms-ux-designer
date: 2026-11-23
status: draft, round 1, for Surbhi to click through and react
inputs: [01-product-brief.md (approved 23 Nov 2026), 01a-ux-opportunities.md, 07-devops-inputs.md OPS-1..10, slice 012 01b (leader screen), ux-learnings.md, design_system.html]
tier: 1 (scope, small-group hiding, aggregates over people)
---

# 090 · People trends: UX design

**I recommend. You decide.** Click the prototype, then say go, change or drop.

## Read this first

1. **I do not have the Artifact tool in this run, so the prototype is not published.** The file is `docs/slices/090-leadership-hr-analytics/prototype-v1.html`. A copy is at `/Users/mac/hrlocal-data/prototypes/090-leadership-hr-analytics/prototype-v1.html`. The lead session publishes it as "People Trends Prototype". Open the file in a browser. It needs no server.
2. **Every number and name in the prototype is invented** (a made-up "Kavya Retail" and "Kavya Foods", 420 people). The page carries a "Sample" tag. Nothing was read from any tenant. I did not open the local bench: this is a new page, so there is no "today" screen to describe. The "today" facts below come from the brief and 01a (read in this session), not from a screen I opened.
3. **I could not check three things** (see ⚠ DECISION list): whether you answered slice 012's question D17, how the leader's access page behaves, and the real speed. The prototype's phone layout was looked at once at about 390 px and desktop at 1440 px. I did not measure tap targets or test 200% text. That is still to do.

## 1 · Frame

A company head on a phone, Monday morning, one minute, wanting to know if people are leaving or staying away more than before. The HR Manager opens the same page for their own company. I leave out the line manager and the employee: the employee sees nothing org-wide and loses nothing; the line manager gets nothing new (the one-way rule).

| Persona | What this design gives them | What changes for them |
|---|---|---|
| **CXO / leader** (served first) | One page, one sentence, five period chips, totals only | New page; nothing is taken away |
| **HR Manager** | The same page for their company, plus the "no relieving date" fix link and "Data to review" | Sees figures leaders see; exact leaver counts under the minimum are still not shared here (names stay in Desk Employee Exits) |
| **Employee** | Nothing on screen. Their data is inside totals of 5 or more people only | Nothing |

## 2 · Evidence and benchmark

- **Fact (read):** brief §2, §3: today's HR Analytics page has no leavers, no attrition, no period choice. The leader screen of 012 was never built.
- **Competitors:** nothing seen. All competitor claims are in the brief, labelled "read 14 Sep" or `[recall — verify]`. I did not re-benchmark. Layout ideas (period chips, a headline sentence, one chart per area) are standard dashboard practice, not copied from a named product.
- **Reused from earlier design (my own work):** "Not shared" wording (012, your words 15 Sep), "Data up to" line, comparison with an equal earlier window (012), "Why is this hidden?" sheet, scope switcher idea.
- **Reused from the portal:** the design-system colours (light and dark), sidebar and top bar, card style, the phone bottom bar with short labels. I did not read `team.html` or `portal.js` line by line; I copied the tokens from `design_system.html` and the layout idea of sidebar plus cards. The real build must use the portal's own CSS classes, not mine.

## 3 · Findings and design decisions (D = design choice, one line each)

| ID | Impact | Kind | Size | Finding or decision |
|---|---|---|---|---|
| PT1 | High | New | M | One page, in the order a leader reads: scope line, period chips, filters, **headline sentence**, People, Early leavers, one chart, Attendance, Leave, By company. Exceptions-first is the headline sentence |
| PT2 | High | New | S | Period chips are a radio group of five, 44 px tall, scroll sideways if the screen is narrow. One tap changes **every** figure, chart and sentence at once, with focus kept on the chip and a screen-reader announcement |
| PT3 | High | New | S | Every figure compares with the equal window before. The comparison dates are written once under "People" ("the 3 months before, 27 May to 24 Aug 2026"), not on each tile |
| PT4 | High | New | M | Early leavers count **only people whose first stretch is over**: "2 of 17 joiners left within 1 month". People still inside the stretch are named as a count: "Too early to tell for 8 more". Where nobody has finished it: "Too early to tell". See ⚠ DECISION UX-2 |
| PT5 | High | New | M | Small groups say **Not shared** in cells, and the page says why in one sheet (012 wording) |
| PT6 | High | New | S | Colour never carries meaning here. Changes are words ("Up 3", "Down 0.4 points") in neutral text. Joined and left differ by direction (up/down) and a legend with words, not by colour alone. No red anywhere |
| PT7 | Medium | New | S | Every chart has a "Show as a table" fold. Chart text is 12 px or more, drawn at the real width, not scaled |
| PT8 | Medium | New | S | "Data up to 22 Nov 2026" sits in the scope line and the attendance card. Attendance says "3 days left out; HR is checking" (the 012 "Needs review" idea) and HR gets a link |
| PT9 | Medium | Keep | — | Keep the slice 012 rules: same formula for absence as `org_figures.py`, "Data up to", doubtful days left out of the headline |

## 4 · Flows and every state

Happy path: sign in, open **People trends** (sidebar "Company" group on desktop, "Trends" in the phone bottom bar), see the sentence, tap a chip, read. Filters are optional.

| State | What the person sees | Words |
|---|---|---|
| Loading | Grey blocks where cards go, within 300 ms (nfr-budget §2) | "Loading People trends. The period bar stays usable; figures fill in as they arrive." |
| Normal | The full page | — |
| No people records | A banner, no charts | "No people records in this view yet" · "People trends counts joiners and leavers from Employee records, then adds attendance and leave. This company has no Employee records yet, so there is nothing to count." · HR: "Add employees in HR, or import them. This page fills in by itself." [Go to Employees] · Leader: "Ask your HR team to add the employee records." |
| Filters match nobody | Banner | "No one matches these filters" [Clear filters] |
| Group too small | Whole page replaced by one banner | "Not shared: too few people in this group for a fair picture" · "Try a wider group, such as the whole company." [Why is this not shared?] [Clear filters] |
| Big group hidden by subtraction | Same banner, other sentence | "Not shared: it would let someone work out a smaller group's figures" (⚠ DECISION UX-1) |
| Error | Banner, never a raw message | "We could not load People trends" · "Your data is safe. The page did not get an answer from the server in time." · "Try again. If it keeps happening, tell HR and quote Code PT-LOAD." [Try again] |
| No scope (Leadership role, no company linked) | Setup page, nothing else | "People trends is not set up for you yet" · "You have the Leadership role, but no company or branch is linked to your account. We show nothing rather than guess." · a message to copy: "Please link my user to a Company so I can open People trends." [Copy message] |
| Records start late | Note under People, comparisons switched off | "No earlier window to compare with: your records start on 14 Jan 2026. This window shows 313 days, from the start of your records." |
| Refused filter (another company's id) | Same page as "no scope" for that filter, never silently ignored | Words to be set in the spec (OPS-3) |
| Network drops mid-change | The old figures stay and a line says the new ones did not load, with Try again | to be set in the spec |

Large cases: a company of 400 or 40,000 sends the same few KB (numbers only). A branch list of 60 stays a single select (a type-ahead if over 30 is later, not now). Chips and filters never make the page wider than the screen.

## 5 · Screen spec (exact words)

**Top bar:** "People trends". Scope line: **"Showing:** All companies, 3 months" then the date range and "Data up to 22 Nov 2026". When filters apply: "Showing: Kavya Retail, Civil Lines, Stores, Contract, 1 year".

**Period chips:** 1 week · 1 month · 3 months · 6 months · 1 year. Rolling, ending the last full day of data. Remembered per person on the server, not on the device (phones are shared at some tenants).

**Filters** (a fold, closed on phone, open on desktop, "Filters · 2 applied"): Company · Branch · Department · Employment type. HR Manager sees Company as fixed text, not a choice. A branch too small to share appears as "Hilltop Kiosk (Not shared)" and opens the banner. "Clear filters" appears only when one is applied.

**Headline sentence** (built by rules, not AI): "**Headcount 420, down 8 in 3 months.** 25 joined, 33 left. Of those who joined and have passed their first month, 2 of 17 left within it. Absent on 4.6% of expected days, up 0.1 points on the 3 months before. 665 leave days taken, Casual the most." A clause whose figure is Not shared is left out, and the sentence says so ("Joiners and leavers are not shared for this group in this period.").

**People** tiles: Headcount, Joined, Left, Net change, Attrition. Under it: "Left means status Left and a relieving date on or before 22 Nov. Someone serving notice is not counted yet. Attrition is people who left divided by average headcount in this window, not a yearly rate." HR line: "8 leavers have no relieving date, so they cannot be placed in a window. [Open the list in Employees]". Leader line (only when 5 or more): "8 leavers have no relieving date. HR is asked to fix this."

**Early leavers:** three tiles, "Within 1 week / 1 month / 3 months", each "N of M" with "joiners left within 1 month (12%)". No comparison on this row (small groups, noise).

**Chart 1:** "Joined, left and running net change". Bars up for joined, bars down for left, a line for the net so far. Day buckets for 1 week, week for 1 month and 3 months, month for 6 months and 1 year (OPS-8; the day buckets for 1 week are 7 points, within the "no per-day beyond 3 months" rule; ⚠ DECISION UX-4 only if you disagree).

**Attendance:** "Absent" and "Data up to". One line chart. Note: "Days that look wrong (for example, everyone absent on one day) are left out of this rate until HR has checked them."

**Leave:** "Leave days taken" with comparison, "By leave type" bars with days (never people), "Small leave types are grouped under Other so no one can be picked out." One bar trend. "Waiting for approval: 12 requests (count only)".

**By company** (CXO with more than one company, no filter): one block per company, alphabetical. "In alphabetical order. This is not a ranking." No sort control.

**"How these figures are counted"** fold at the bottom. **Why-not-shared sheet:** "Not shared: too few people in this group for a fair picture. With a small group, a total can point at one person, and that person is a colleague. So we only show figures for 5 or more people. Sometimes a larger group is not shared either. That is when showing it would let someone work out a smaller group by subtraction. Try a longer period, or fewer filters. The whole-company totals are always shown. Leaders see totals only. Names and reasons for leave are never shown here."

Language: English only in v1 (brief). The Hindi parity rule binds employee screens. I did not machine-translate.

## 6 · Privacy and accessibility

- **Who sees it:** Leadership role with a Company or Branch scope; HR roles for their companies. Nothing else. **Totals only: no names, no reasons for leave or leaving, no per-person absence.**
- **Not shared rule in the prototype:** a group of fewer than 5 people shows Not shared everywhere. When a cut is narrowed by branch, department or type, a count of fewer than 5 (joined, left, an early-leaver cell, pending leave) also shows Not shared. Leave types under 5 people are folded into "Other"; if Other is still under 5, the smallest visible type joins it. Whole-scope totals are exact. Brief Q2 said "fewer than 5" below the total; I used "Not shared" because you chose those words for 012. ⚠ DECISION UX-3 asks you to confirm.
- **Consequence you will see when you click:** a narrow cut over a short window hides most figures (a branch of 59 people over 3 months shows about 4 leavers, so Left is Not shared). The 1 year window shows more. This is the rule working, and the sheet says "try a longer period".
- **WCAG 2.2 AA:** every filter has a visible label; chips are `role=radio` in a `radiogroup`; focus ring is visible; charts have a text label and a table; the dialog moves focus, closes on Escape and returns focus; colour is never the only signal. Chip height is 44 px. Selects are 16 px on a phone. Nothing is under 12 px. **Not yet measured:** target sizes by script, 200% text, 360 px width (I looked at about 390 px once). Test those at build.
- **Shared phones:** this page holds aggregate company figures, not a person's own data. It stores nothing in the browser. The period is remembered on the server.

## 7 · Checks

- **Heuristics:** visible state (Data up to, Showing line); plain words ("Left", not "attrition events"); user control (Clear filters, Escape on the sheet); error recovery (Try again plus a code); help (the counting fold and the sheet).
- **Persona walkthrough, CXO:** before, ask HR and wait. After: open, read the sentence (one step), tap a chip (two taps). Under one minute.
- **Frontline bar:** this page is not for frontline staff. A leader on the floor can do the top task in two taps on a phone.
- **Refusals:** no per-person risk score, no names, no ranking, no AI, no dark patterns. Branches are not ranked.
- **Red team:** a brand-new leader with no scope is covered; a group of 4 and a group hidden by subtraction are covered; no data and a late-start company are covered; a 100x bigger tenant sends the same few numbers. **Not covered:** a leader with scope that changes while the page is open.
- **Usability test (High impact, 5 leaders or HR heads):** tasks: (1) say how many left in the last 3 months and whether that is more than before; (2) find early leavers for 1 month; (3) explain what "Not shared" means; (4) find the branch they care about. Success: 4 of 5 finish each task in under a minute without help, and none reads Not shared as an error. Change the design if two people read "Too early to tell" as zero.

## 8 · Subtract pass

Removed: language switch (English only), a settings screen for the minimum (it already exists), saved filter sets, a compare-to-last-year toggle, a "what needs me" strip (the sentence does it), tooltips on chart bars (the table does it), and a sort control on the company list. I kept the table fold on each chart: it is the accessible alternative and costs one fold. I did not remove the By company block: it is how a leader with two companies sees the split; the brief calls it "total plus a table".

**Rung on the cost ladder:** new code in `alvoraa_portal`, using the portal's own components. A standard Frappe page cannot hide small groups.

**Not in this slice, for you to decide later:** named leaver lists, export, a grade filter, a weekly email, Hindi labels, a custom date range.

## 9 · ⚠ DECISIONS

| ID | Decision | Options | My recommendation | Owner | Blocks |
|---|---|---|---|---|---|
| ⚠ UX-1 | Wording when a **large** branch is hidden only so a smaller one cannot be worked out. This is slice 012's D17. I could not confirm you decided it | (a) your sentence everywhere ("too few people") (b) for that case only: "it would let someone work out a smaller group's figures" | (b). (a) is untrue for a branch of 38 people. Prototype: pick Kavya Retail, then Market Yard | Surbhi | Banner copy |
| ⚠ UX-2 | Early leavers: count **only people whose stretch is over** ("2 of 17"), or everyone who joined ("2 of 25", which can grow) | (a) closed only (b) the brief's "of 48" with a note | (a). A number that grows later is a wrong number. It differs from the brief's example text, so I need your yes | Surbhi | Early leavers row |
| ⚠ UX-3 | Under-the-minimum cells: "Not shared" (my build) or "fewer than 5" (brief Q2) | as stated | "Not shared": your own words, one idea. The subtraction rule needs the security engineer to confirm it also covers department and type cuts; the prototype applies the next-smallest rule to branches only | Surbhi, security engineer | Spec, ⚠ COMPLIANCE |
| ⚠ UX-4 | 1 week uses day buckets (7 points) | day buckets, or one bucket | Day buckets; OPS-8 allows it | Surbhi | Chart |

## 10 · For the business analyst: acceptance criteria to write

1. Five chips; one tap changes every figure, chart and the sentence; the previous equal window is used; dates are shown.
2. Each figure's rule: Left = status Left and relieving date on or before the last data day; headcount and attrition formulas as on screen; absence uses the shared `rate()`.
3. Early leavers: cohort rule (UX-2), "Too early to tell" when no one has finished the stretch, never a number that grows.
4. Small-group rule: below 5 → Not shared; narrowed cut below 5 → Not shared; leave types fold into Other; the subtraction rule (next-smallest) for branch, department, type and company × branch; hidden stays hidden on every view of the same figure, including the sentence, the chart, the By company block and the table fold.
5. Scope in the query: HR sees own companies; Leadership sees the linked Company or Branch; a filter outside scope is refused, never ignored; no scope shows the setup page.
6. States and words in §4 and §5, including loading within 300 ms and Try again.
7. A leave across a window edge counts only the days inside it (OPS-10); matches what payroll reads (Q5).
8. Data quality: HR sees the count and a working link; a leader sees a count only, and only at 5 or more.
9. Phone: no sideways page scroll at 360 px and at 200% text; chips scroll; targets 44 px; text 12 px minimum, fields 16 px.
10. Page stores nothing in the browser; the period is saved on the server.
11. Time: page answers within 3 s on a DTC-size copy (OPS-5); skeleton within 300 ms.

## 11 · Learning loop

Added to `ux-learnings.md`? **No.** This run produced no user feedback yet; I did not edit the file. After you react, log each point. Patterns worth recording if you agree: counting only finished cohorts; "Not shared" applied by narrowed cut; one-page sentence-first dashboard.

**Prototype:** switch person, phone or desktop, state and theme in the dark bar at the top. Try: 1 week; Kavya Foods plus 1 year (late records); Kavya Retail plus Hilltop Kiosk (a group of 4); Kavya Retail plus Market Yard (hidden by subtraction); HR persona.

---

## Design check decision

**Design approved — Surbhi, 23 Nov 2026:** "go with your recommendations" on prototype-v1 (https://claude.ai/artifact/4DWBeaviyCZYF2nCNwAidf). UX-1 → (b); UX-2 → (a) closed cohorts only; UX-3 → "Not shared" (the subtraction rule for department and type cuts still goes to the security engineer); UX-4 → day buckets.
