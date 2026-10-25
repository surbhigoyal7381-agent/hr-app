---
slice: 069-wall-chart-print
artifact: 04-impact-and-strategy (change-process steps 1 and 2; the engineer's 00-impact-analysis for this slice)
author: hrms-fullstack-engineer
date: 2026-10-24
status: proposal - waiting for Surbhi's approval. Paper work only. No feature code written, nothing committed, nothing pushed, no server or bench touched.
inputs: 03-functional-spec.md rev 2 (14 stories, 65 ACs, 40 parity rows), 01c-security-privacy-requirements.md rev 1 (SEC-1..4, PRIV-1..3; out of date in four places, spec Q13 - where they differ the spec wins), 02-design.md, prototype-v1.html, 01-product-brief.md
assumed answers (lead session, 24 Oct 2026): D-4 "1 person below" - yes; D-5 no people note when nobody is unseated - yes; D-6 identical seats merged on paper as on screen - yes
code read: worktree dev-integration-2026-10-24 (branch integration/dev-2026-10-24, 1 behind origin/dev at 6aaf9ffd): portal.js 78-1347 and 2270-2380 (ocNodeCard, ocRender, POS, posLoad, posFew, posKids, posNode, posGroupSiblings, posGroupNode, posPaintTree, zoom, posPrintHead, posSheet, posCloseSheet, posWire, posSeatSheet), panels.css 2100-2167, positions.html 1-20, scripts/check_positions_tree.js, check_positions_connectors.js, check_portal_trays.js, browser_check_positions.js, run_dom_tests.js, .github/workflows/ci.yml, prototype-v1.html layout code (lines 380-472)
measured: nothing. This step only reads. The sizes quoted are the designer's prototype measurements (02-design §4)
---

# 069 · Impact analysis and strategy: Download wall chart (PDF)

## 0 · Bad news first

1. **The spec says "reuse `ocNodeCard`" and "never call `ocAvatar`" for paper. Both cannot be true.**
   `ocNodeCard` draws an avatar for every person, with no way to turn it off (`portal.js:151`). It also
   draws the flag chips, the `covering` / `%` / leaving tags, the fold button and the words "Nobody in
   this seat". So the paper gets **its own small card and tree function** (about 40 lines). It writes
   the **same markup and CSS classes** as the screen (`oc-branch`, `oc-kids`, `oc-fam`, `oc-hang`,
   `oc-hang-item`, `oc-box`), so the boxes and lines are drawn by the same CSS. I do **not** add options
   to the shared `ocRender` / `ocNodeCard`: the Organisation chart uses them too (`portal.js:2572`).
   This is a "how" choice, but it differs from the spec's handoff wording, so I ask for your nod (Q-A).
2. **Removing the Print button breaks one existing CI check on purpose.** `check_positions_tree.js:294`
   asserts that the zoom row offers `window.print()`. Step 1 changes that line to assert the opposite.
   This is the old behaviour being retired (D-2), not a lost feature.
3. **The 300 ms target cannot be met the prototype's way.** The prototype draws 28 whole layouts and
   measures each (0.9-2.5 s). My plan draws **twice**: once to measure every box, once to draw the
   chosen layout. The choice between is plain arithmetic on the measured sizes (§2.2). **I cannot
   prove 300 ms until it is built.** Wall-clock times on this laptop are not reliable
   (change-process rule 5), so the guard is the property "two drawings per change, whatever the size",
   and the timing is reported, not promised.
4. **The kill line can still stop this slice at step 3.** Each box now carries designation and
   department too. The prototype measured 9.5 pt for All on A1 without them. If the new figure is under
   8 pt even with the branch removed, I stop and bring you the numbers (AC-32).
5. **"Several sheets" at ten times DTC's size may be too heavy for the browser.** Each sheet is a full
   clipped copy of the chart. DTC on A3 is 9 sheets of 90 boxes - fine. 900 seats on A4 could be
   about 150 sheets of 900 boxes. I will measure it at 10× and bring you the number before adding any
   limit (R-4).
6. **Rolling back step 1 brings the Ctrl+P leak back.** So if something goes wrong later, revert the
   later steps and keep step 1.

---

## 1 · Impact analysis

### 1.1 Parallel-work check (done before this analysis)

| Check | Result |
|---|---|
| `git fetch origin` | `origin/dev` is at `6aaf9ffd`. **One commit came in that this worktree does not have:** `6aaf9ffd ALV-213: the employee portal uses the whole screen` (Surbhi's session). It touches `portal.js` (hunks at lines 5420 and 11849: leave cards and the phone avatar menu), `panels.css` (phone rules at lines 343-393), `frame.html`, `frame.css`, `attendance.html`, `hrms_employee.py` and a new test. **None of it is in the Positions section or the print block.** No clash expected |
| This worktree | `dev-integration-2026-10-24`, branch `integration/dev-2026-10-24`. Holds another session's uncommitted `.claude/context/ux-learnings.md` and the untracked 069 folder. **Not mine; not touched.** I add only this file |
| Work board | 064-old-v2 / 064-old-chart rows claim `portal.js` Positions section, `positions.html`, `panels.css` Positions block, `scripts/check_positions_*.js`, `browser_check_positions.js`. Their code is on `origin/dev` (`5d565e10`, `4c82b288`). The rows look stale; I will ask before treating them as finished |
| Slice 065 | Branch `slice/065-plan-a-replacement` (`7c1cb9d5`) holds the server side and 11 lines in `check_positions_tree.js`. **Its screens (065 steps 9-10) are not built** and will edit the Positions section of `portal.js`, `panels.css` and `check_positions_tree.js` |
| Other developers | I cannot see other machines. **Surbhi: is anyone else in the Positions screen code this week?** |

**Files 069 would change**

| File | What | Hot? | Who else is in it | Plan |
|---|---|---|---|---|
| `alvoraa_portal/.../public/js/ess/portal.js` | (a) one new block of `posWall*` functions, placed after `posWire` in the Positions section, own name prefix; (b) five one-to-three-line edits: remove the Print button (`:1212`), drop "printed by" in `posPrintHead` (`:1291-1299`), an optional third argument on `posGroupSiblings` (`:815`, `:826`), one clean-up line at the top of `posCloseSheet` (`:2312`), one line in `posLoad` to show the button (`:346`) | **Yes** - 17,616 lines, changed by most slices | ALV-213 today (other sections); 065 screens next | **Split**: new code in its own block; edits to shared functions kept to the lines named. Rebase on `origin/dev` at the start of every step, before every bench test and before handoff (§2.6) |
| `alvoraa_portal/.../public/css/ess/panels.css` | (a) three selectors added to the Positions print list (`:2160`); (b) a new block of `.pos-wall` rules after `:2167`: always-light paper, print-only box sizes, the wrap grid and bar, the "while printing the wall chart" rules, the toolbar button on a phone | Yes | 065 screens may add to the print list | Split: the three selectors go **before** `.noprint` so 064's regex check (`check_positions_tree.js:308`) still matches; everything else is a new block |
| `alvoraa_portal/.../templates/includes/ess/parts/positions.html` | One button before "+ Add a seat", and one `<div>` round the two buttons | Positions part | 065 adds "one line under Filters" (other place) | Different lines |
| `scripts/check_positions_tree.js` | Section 4f: the Print button is gone, no "printed by", the three new print selectors (about 6 lines changed) | 064's, 065 appends | 065 | Edit inside 4f only |
| `scripts/check_wall_chart.js` | **New.** The CI checks for this slice (§2.4) | No | - | - |
| `alvoraa_portal/tests/portal_wall_chart_test.js` | **New**, 3 lines: requires the check above, so it runs in CI's DOM suite | No | - | - |
| `scripts/run_dom_tests.js` | One `RUN` entry; `EXPECTED_BROWSER_TESTS` 12 → 13 | Shared | 065 does not touch it | One line each, at the end of the list |
| `scripts/check_positions_connectors.js` | New cases at the end: Ctrl+P (AC-3, AC-3a), the wall chart's print DOM connectors (AC-22, AC-50), PDF page sizes, timings | 064's | - | New cases only. Not in CI (needs a site) |

**Why a new check file rather than new sections in `check_positions_tree.js`:** that file is 815 lines and
065 appends to its end too, so both slices appending there would conflict every time. The cost is
about 40 lines of the small fake-page setup copied from it. I judged that cheaper than a repeated
conflict in a file two slices share.

**Pin tests that keep existing features alive:** all of `check_positions_tree.js` (runs in CI through
`portal_positions_test.js`) runs unchanged except section 4f, which changes on purpose. The new
`check_wall_chart.js` names every feature this slice adds, one check per AC group, so a merge that drops
one fails CI.

### 1.2 Functional: cross-module reach

| App | Touched? | How |
|---|---|---|
| `alvoraa_portal` | **Yes** | `portal.js`, `panels.css`, `positions.html`, tests |
| `hrms` (our `alvoraa_org_structure`) | **No.** `register.position_table` is read, not changed. It already sends every value the paper needs, including `may_see_leaving`, `leaving`, `opening` and `as_at` | - |
| `frappe`, `erpnext`, `hrms` upstream | No | - |
| `alvoraa_goals`, `alvox_compensation` | No | - |

**`ignore_permissions` count: unchanged.** No Python changes at all, so `test_portal_security_010.py`
CEILINGS need no new row. `register.py` keeps its 4.

### 1.3 Functional: every caller of what I would change (grep of the worktree)

| Function | Change | Callers | Effect on them |
|---|---|---|---|
| `posPaintTree` (the zoom row) | Print button removed; group label "Zoom" | `posPaint` (`:566`) | Zoom buttons unchanged. `check_positions_tree.js:294` updated (bad news 2) |
| `posPrintHead` | "printed by {name} ({role})" removed; the rest kept | `posPaintTree` (`:1216`) only | Ctrl+P header keeps "Positions", the view, company, "seats as at", filter, "on {date}". `check_positions_tree.js:297-298` still passes |
| `posGroupSiblings(kids, t)` | Optional third argument `all`: when true, `POS.ungrouped` is ignored (AC-21) | `posNode` (`:789`), `posSeatsIn` area (`:974`) | Both call with two arguments, so nothing changes for them |
| `posCloseSheet` | First line: if the open tray is the wall chart panel, run its clean-up | Scrim and Close (`:2303`, `:2305`), Escape (`:2329`), `:2411`, `:2429`; tests `check_portal_trays.js:286`, `check_positions_tree.js:747`, `:791` | For every other tray the new line does nothing (`POS.sheet.kind` is not "wall") |
| `posLoad` | Shows the new button when `rows` is not empty | `positions.html` panel switch; tests | Failed load returns before the line, so no button (AC-4) |
| `ocNodeCard`, `ocRender`, `posKids`, `posGroupKey`, `posDay`, `posSheet`, `posUnseatedSheet`, `drT` | **Called, not changed** | - | - |

New functions (no existing callers), all prefixed `posWall`: open the panel, set a choice, build the
allowed copy, draw the paper, measure and choose the layout, write the result line, print, clean up.

### 1.4 Personas

| Persona | What changes |
|---|---|
| **CXO / Owner** (DTC Owner) | Same button as HR. Prints only the seats the server already sends him (his branch); the panel says so. HR copy tick only if the server sends him leaving dates |
| **HR Manager** | New button and panel. Wall copy or HR copy. Ctrl+P keeps working but no longer prints flags, tags, the HR box or their own name. The zoom-row Print button is gone |
| **Head of department** | Nothing. No Positions page, so no button |
| **Employee** | Nothing on any screen. Reads the wall: names, seat titles, designations, branches, departments |

**HRMS domains:** org structure only. Leaves, attendance, payroll, appraisals, goals, compensation:
not touched. The global `@page{size:A4 landscape}` rule (`panels.css:2154`) that payslips also use is
**not edited** (D10); the wall chart adds its own rule only while it prints and removes it after.

### 1.5 The seven non-functional dimensions

| Dimension | Before → after | Why |
|---|---|---|
| **Performance** | **neutral** for every page view; **slightly worse** script size | 0 new server calls, 0 new payload bytes. `portal.js` grows about 350 lines (about 15 KB on 916 KB, under 2 %). The layout work runs only while the panel is open: two drawings per change (§2.2) |
| **Security** | **improves** | Closes today's leak: Ctrl+P and the old Print button print flags, leaving tags, the HR-only box and the printer's name. No new endpoint, no new role, `ignore_permissions` unchanged. The paper can never hold more than the rows this reader already received |
| **Reliability** | **neutral** | Clean-up runs on `afterprint` **and** on panel close (phones may not fire `afterprint`). The only new failure is a browser that ignores the page size (iPhone, tested, Q4). Nothing stored, so nothing half-done |
| **Scalability** | **neutral**, one watched risk | Layout cost grows with seats, not with candidate layouts. 900 seats is tested. "Several sheets" copies the chart once per sheet: watched at 10× (R-4) |
| **Maintainability** | **degrades, slightly** | A second, small drawing of the hierarchy for paper. It shares the screen's markup and CSS, and the 064 connector check runs on its output, so a markup change that breaks it fails a check. About 350 lines in a hot file, in one block |
| **Data integrity** | **neutral** | Reads the rows already on the page; writes nothing. Stale paper is shown by the "as at {date}" footer. No cache: the last layout is kept only while the panel is open, and redone on every open and every change of start, levels or ticks |
| **Compliance / privacy** | **improves** in the system; **new exposure outside it, by design** | Wall copy: names, titles, designations, branches, departments on a wall (PRIV-1 allowed list, PRIV-3 notice, counsel Q8 before DTC gets it). HR copy: leaving dates on paper, only for readers who see them on screen, with a banner on every sheet. R1 (nobody knows who printed) accepted by Surbhi 24 Oct 2026 |

---

## 2 · The strategy

**Rung of the ladder: 4, new code, in the browser only.** Cheaper rungs, checked again:
- *Already there:* Frappe HR's Org Chart "Export" (`hierarchy_chart_desktop.js:115`) is a PNG of
  Employee reporting lines, desk only, and blurs when enlarged. Today's Positions Print leaks and shows
  3 names per seat on A4 only.
- *Configuration:* a Print Format renders with wkhtmltopdf, which cannot draw this layout (brief §4).
- *Customisation:* a Client Script runs on the desk, not the portal, and would be the same code anyway.

No new DocType, field, endpoint, package, app, cache, setting or flag.

### 2.1 What is reused

| Reused | For |
|---|---|
| `position_table` reply already in `POS` (`rows`, `may_see_leaving`, `unseated`, `as_at`) | The only data source |
| `posKids` | The reporting tree, tops, seats whose manager is out of view |
| `posGroupSiblings` + `posGroupKey` | Identical seats merged exactly as on screen (D-6) |
| `posDay` | "leaving 30 Nov" as the screen writes it |
| The screen's chart CSS (`oc-branch`, `oc-kids`, `oc-fam`, `oc-hang`, `oc-hang-item`, `oc-box`) | Same boxes and lines on paper |
| `posSheet`, `posCloseSheet`, `posWire` (Escape) | The panel: drawer on desktop, bottom sheet on a phone, focus, scrim |
| `posUnseatedSheet` | "See who is not in a seat" |
| `drT` | Every word on the panel and paper |
| The browser's print window | Save as PDF |
| `check_positions_connectors.js` (Playwright, print emulation, `page.pdf`) | Connector check on the print DOM, Ctrl+P check, PDF page sizes |
| The fake-page pattern of `check_positions_tree.js` | The new CI check |

### 2.2 How the 300 ms target is met

The prototype tries column heights 4-16 and 2-5 (28 layouts), drawing and measuring each. Drawing 90
boxes and 363 names takes about 30 ms on this laptop, so 28 drawings take about 0.9 s.

The plan:
1. **Draw once to measure.** Draw every box of the chosen start and levels, as it will print, in an
   off-screen holder (`visibility:hidden`, off the left edge, so it lays out but is never seen). Read
   each box's width and height. One layout.
2. **Choose by arithmetic.** For each of the 28 candidates, work out the chart's width and height from
   those numbers: a family is as wide as its box or the sum of its children plus the gaps; a wrapped
   column block is as wide as its columns and as tall as its tallest column. Pick the one that fills
   an A-series sheet best, as the prototype does. About 28 × 90 sums: well under a millisecond.
3. **Draw once more.** Draw the chosen layout, place the bars that join wrapped columns, and measure
   the real size. **The name size on the result line comes from this real measurement** (AC-30), so
   if the arithmetic is a little off, the layout is slightly less tight but the number is still true.
4. **Paper and Sheets changes do not redraw.** They only redo the scale sum on the last measured size.
   Changing Start from, Levels, Show Vacant or HR copy redraws (two drawings).
5. **"Working out the size…"** When a change needs a redraw, the result line says "Working out the
   size…" and the drawing runs on the next frame, so the words appear first (AC-35). If "Open print
   preview" is pressed meanwhile, the print waits for the size.

**How it is proved:** (a) Playwright on `F-DTC90`, median of 5 changes per control, reported as
measured; same at 900 seats for information. (b) The same Playwright run also runs the prototype's
full 28-drawing search once, **in the check only**, and asserts that my chosen layout's name size is
within 0.5 pt of the full search's best at DTC's shape and at 10×. **Only if that fails** do I add
the fallback: draw the best three candidates for real (three drawings, about 100 ms). Not built first.

### 2.3 Thin steps, in order. Each stays green.

Built in a new worktree `.claude/worktrees/069-wall-chart-print` on `slice/069-wall-chart-print`, cut
from `origin/dev`. One commit per step (two at most). Browser checks run on a throwaway container and
site of my own, never `hrlocal-bench`; the fixtures are loaded into `POS` in the page, so no seeding of
real records is needed.

**Step 1 · Ctrl+P prints safely; the old Print button goes (US-1; SEC-3). Can ship alone.**
- Remove the Print button from the zoom row; label the group "Zoom".
- `posPrintHead`: drop "printed by {name} ({role})", keep the rest.
- `panels.css:2160`: add `#panel-positions .oc-flag,#panel-positions .oc-tag,.pos-nomgr-row,` before
  `.noprint`. Scoped to Positions so the Organisation chart's own print is not changed.
- Tests: `check_positions_tree.js` 4f: no `window.print()` in the tools, no "printed by" in the
  header, the three selectors present (CI). `check_positions_connectors.js`: print media with the
  panel closed - seat titles and names visible, 0 visible `.oc-flag`, `.oc-tag`, `.pos-nomgr-row`,
  `.private`, `[data-private]`; header holds neither `PRINTER-SNTL` nor `ROLE-SNTL` (AC-1 to AC-3a).

**Step 2 · The allowed copy and the paper drawing (US-4, US-5, US-12, US-13 data; PRIV-1).**
- `posWallCopy(start, levels, vacant, hr)`: walks `posKids(POS.rows)` and builds a new tree whose seats
  hold **only** `title`, `designation` (only when it differs from the title), `branch`, `department`,
  `names[]` (`{name}`; plus `leaving` text **only when `hr` and `POS.may_see_leaving` are both true**),
  `opening` (**only when hr**; a number of seats with an opening - 0 or 1 for a seat, up to k for a
  merged box; never the ID), `vacant`, `below` (seats and people under it, on the last level only),
  `kids`. Groups with `posGroupSiblings(kids, t, true)`. Rows and person objects never leave it.
- `posWallHtml(copy, K, KU)`: the paper card and tree. Card: title; designation line; "{branch} ·
  {department}" (not on the starting box); names one per line in `ceil(n/10)` columns, at most 4;
  `Vacant` when ticked; "Job opening raised" / "{k} job openings raised" (HR copy); "{n} seats · {p}
  people below" with "1 seat" / "1 person" (D-4). Tree: the screen's markup classes, the wrap as a
  grid of K rows (KU under a row of leads), several tops side by side with their own seats (D-3), or a
  grid when no top has seats under it (Owner).
- Tests, new `check_wall_chart.js` (CI): the PRIV-1 sentinel payload **run twice** - HR copy off
  (AC-27a) and on (AC-27b) - checking the whole paper HTML for every sentinel string, `2099`,
  `Frozen`, "covering", `<img`, and the banned classes; names = 363; `DESIG-OK` and `DEPT-OK` present.
  Key-set test on the copy for each mode (AC-28). `F-NOLEAVE` with a forced leaving value (AC-65).
  Counts: 90 boxes before grouping, 363 names, 23 boxes at 2 levels, 11 boxes / 72 names from Back
  Office Manager (AC-21, AC-24); `F-GROUP` merges (D-6); Show Vacant off removes only the word
  (AC-56); paper identical whatever the screen's zoom, view, folds and groups (AC-26).
- **Break it on purpose (AC-29):** copy `employee` into the copy, watch AC-27a, AC-27b and AC-28 fail,
  record it in `04-test-report.md`, undo. Not committed.

**Step 3 · The layout and the kill-line re-measure (US-4, US-6; AC-32). A stop point.**
- The two-drawing layout of §2.2, the bars that join wrapped columns, the always-light paper (AC-23).
- Playwright: record the name size for `F-DTC90` on A3 (2 levels), A1 (All), A0 (All), HR copy off and
  on, in `04-test-report.md`. Connector check on the print DOM at 2 levels and All, and for several
  tops (AC-22, AC-50): 0 false, 0 missing links.
- **Gate:** All on A1 at 8 pt or more → keep the branch. Under 8 pt → remove the branch from the box
  and measure again. Still under 8 pt → **stop and bring Surbhi the numbers.**

**Step 4 · The button and the panel (US-2, US-3, US-6, US-9, US-12, US-13, US-14 screens; SEC-1, SEC-2).**
- Button in `positions.html`, shown by `posLoad` only when there are rows. Phone: full width, 44 px.
- Panel in `posSheet`: Start from, Levels, Paper, Sheets, "On the paper" group (Show Vacant; HR copy
  **only when `POS.may_see_leaving`**, absent from the DOM otherwise, unticked on every open), notes
  (scope, filter, people, privacy, office-print), the result line with reading words and the warning
  with its one or two fix buttons, "Open print preview". Choices kept in `POS.wall` for the page
  visit, never in browser storage (AC-16).
- Tests (CI): `gpFetch`, `frappe.call`, `fetch`, `window.open`, `URL.createObjectURL` and both
  storages' `setItem` replaced by functions that fail the test, `window.print` counted; open the
  panel, change all four choices and both ticks, press Open print preview → nothing called, print once
  (AC-8). Button with and without rows (AC-4). Panel words for `F-DTC90`, `F-OWNER`, filters on, no
  unseated list, 0 unseated (AC-9 to AC-17, AC-48, D-5). HR copy tick absent for `F-NOLEAVE`, unticked
  on reopen (AC-58, AC-65). Playwright: AC-35 timings and the 0.5 pt comparison (§2.2), focus and
  Escape (AC-6, AC-7).

**Step 5 · Print preview, file name, footer, clean-up (US-7, US-13 paper; SEC-4, PRIV-2).**
- On "Open print preview": add one `<style>` at the end of `<head>` (so after the global A4 rule) with
  `@page{size:{w}mm {h}mm;margin:10mm}` - millimetres only; set `document.title`; mark `<body>` so the
  print rules show only the wall chart; call `window.print()` once. Footer and, for the HR copy, the
  banner at the top and the start of the footer on every sheet.
- Clean-up on `afterprint` and on panel close: remove the style, the mark and the paper holder, restore
  the title. "See who is not in a seat" closes the panel properly first.
- Tests (CI): the style text matches `size:\s*\d+mm \d+mm`, never `A0`-`A4`; A1 landscape =
  `841mm 594mm`, A0 portrait = `841mm 1189mm` (AC-37). Title patterns for wall and HR copy, no person's
  name, no `PRINTER-SNTL` (AC-38, AC-61). Footer words, no "printed by" (AC-41). After `afterprint`,
  and after closing without printing: no style, title back, a later Ctrl+P is the screen chart
  (AC-39). The static check: between `posLoad` and `ocPaint`, no `onclick="window.print()"` and exactly
  one `window.print()` call, inside the wall chart's print function (AC-2).
- Playwright (not CI): `page.pdf({preferCSSPageSize:true})` after the style is in place, for A4-A0 in
  both orientations; read each PDF's page box and check it in mm, ±1 mm. Chromium only, so it does not
  replace the manual check.
- Manual (AC-42): Chrome and Edge on Windows, Save as PDF at each size; PDF properties show the title
  and no author; then a payslip printed in the same tab comes out as before.

**Step 6 · Several sheets (US-8).**
- One clipped copy of the chart per sheet, each moved to its row and column, at 10 pt; " · Sheet k of
  n (row r, column c)" in the footer; "It fits on one sheet at this size" when it does (AC-45 to AC-47).
- Tests: CI - n pages, labels, offsets cover the chart with no gap or overlap (arithmetic on the page
  boxes). Playwright - PDF page count = n for `F-DTC90` All on A3; time to build the print DOM at 900
  seats on A4 several sheets, reported (R-4).

**Step 7 · iPhone page-size test (AC-43) - plan below, §2.5.**

**Step 8 · Before handoff.** Rebase on `origin/dev`; run every CI node check (`run_dom_tests.js`,
`check_portal_handlers.js` - the new buttons call `window.posWall*` functions, `check_undefined_js.js`,
`check_portal_trays.js --static`) and `scripts/check_app_integrity.py`; run the 064 Python module
holding the SEC-8 refusal once to prove AC-51 still holds (no Python changed, so no full Python suite);
the Playwright checks once; then the review agents. Release note with the PRIV-3 text and switch-on
checks C1-C3 (AC-52 to AC-54).

### 2.4 The CI guard (what fails the build if a control is lost)

| Control | Check in CI | File |
|---|---|---|
| PRIV-1 wall copy | Sentinel payload, HR copy **off**: no sentinel, no `2099`, no "leaving", no "Job opening", no "HR use only", no `Frozen`, no "covering", no `<img`, none of `.oc-flag .oc-tag .oc-toggle .av .pos-nomgr .private [data-private]`; names = 363 | `check_wall_chart.js` |
| PRIV-1 HR copy | Same payload, HR copy **on**: "leaving 30 Nov", "leaving 1 Jan", "Job opening raised", banner top and foot; still none of the sentinels (so never `OPEN-SNTL`, `PLAN-SNTL`, `WHO-SNTL`, `REASON-SNTL`) | same |
| PRIV-1 shape | The copy holds exactly the allowed keys per mode; `opening` never a string | same |
| PRIV-1 gate | `may_see_leaving:false`: no HR copy tick in the DOM; forced `leaving` still never prints | same |
| SEC-1 | No server call, no new window, no blob URL, no storage write; print called once | same |
| SEC-3 code | No `onclick="window.print()"` and one `window.print()` in the Positions code, inside the wall print | same |
| SEC-3 CSS | `panels.css` Positions print list holds `#panel-positions .oc-flag`, `#panel-positions .oc-tag`, `.pos-nomgr-row`, and still `.private,[data-private]{display:none !important}` | `check_positions_tree.js` 4f |
| SEC-4 | Style text in mm only; exact A1 landscape and A0 portrait strings; removed after `afterprint` and after close | `check_wall_chart.js` |
| PRIV-2 | Title regexes; footer and title free of `PRINTER-SNTL` and every person's name | same |

The fixture carries a leaver, an opening, a key seat, a Frozen seat, a covering person and 065 plan
keys, because a check on data with none of them would pass and prove nothing (01c lesson 1). Every guard
is broken once on purpose during the build to show its check can fail.

### 2.5 iPhone page-size test plan (AC-43)

Safari on iPhone may ignore a CSS page size `[recall - verify]`. Chrome on iPhone uses the same engine,
so one test covers both.

1. **Device:** a real iPhone (not a simulator), Safari, iOS version recorded.
2. **Reach the build:** the local throwaway site over Tailscale (as the local bench is reached today).
   Log in as a test HR Manager on that site only.
3. **Print:** Positions → Download wall chart (PDF) → Start from the top, All levels, **A1**, one sheet
   → Open print preview → Print → pinch the preview open → Share → Save to Files.
4. **Repeat** for **A3** (so a result of "A4 / Letter" is told apart from "honoured").
5. **Measure** each PDF on the laptop: page width × height in mm (PDF properties or `pdfinfo`), page
   count, title, whether names are readable at 100 %.
6. **Record** in `04-test-report.md`: iOS and Safari versions, paper chosen, page size found, pages,
   title, pass or ignored.
7. **If ignored:** Surbhi decides Q4 (a line "Use a laptop for sizes above A4" on iPhone). Nothing is
   built for it until she answers.

### 2.6 Working beside other sessions in `portal.js`

- New code sits in one block with its own `posWall` prefix, so other slices' edits rarely meet it.
- The five edits to existing functions are one to three lines each and are listed in §1.3; on a
  conflict, both sides are kept and the incoming commit's added lines are grepped back (parallel-work
  §5).
- `git fetch origin && git rebase origin/dev` at the start of every step, before each Playwright run
  and before handoff. Any incoming commit that touches `portal.js`, `panels.css`, `positions.html` or
  `check_positions_*.js` is read and named in the notes.
- **If 065's screens land first:** rebase, then re-run `check_positions_tree.js`, `check_wall_chart.js`
  and the connector check. 065 marks its plan elements `.private`, which both prints already hide; the
  wall copy never reads `plan` or `plans` at all, and the AC-27 fixture keeps those keys (AC-54).
- A row on the work board once approved; removed when pushed or dropped.

### 2.7 Rollback

- **No data, no migration, no setting, no server code.** Rollback is `git revert` of the step commits
  and a normal deploy.
- **Revert from the top down and keep step 1** if possible: reverting step 1 brings back the old Print
  button and the Ctrl+P leak.
- After a deploy either way, check the served `portal.js` really changed (deploys have served stale
  assets before): compare the file in the container's `sites/assets` with the image.
- Browsers holding the old script keep the old behaviour until reload. Harmless both ways.

---

## 3 · Risks and trade-offs

| # | Risk | What I do about it |
|---|---|---|
| R-1 | The kill line fails with designation and department on the box | Step 3 gate; branch comes off first; stop if still under 8 pt |
| R-2 | The arithmetic layout choice is worse than the full search | Checked within 0.5 pt in Playwright; fallback (best three drawn for real) only if it fails |
| R-3 | The paper drawing and the screen drawing drift apart over time | Same markup classes and CSS; the 064 connector check runs on the paper too |
| R-4 | "Several sheets" at 10× builds a very large print page | Measured at 900 seats; if too slow I bring the number to Surbhi instead of adding a silent limit |
| R-5 | `afterprint` does not fire on some phones, leaving the page size in place | Clean-up also on panel close; Ctrl+P with the panel still open prints the wall chart, which is safe (it is the allowed copy) |
| R-6 | iPhone ignores the page size | Tested and recorded; Q4 |
| R-7 | Another session changes the Positions section mid-build | §2.6 |
| R-8 | `01c` still lists designation and department as never printed | Spec wins (Surbhi 24 Oct); security engineer updates `01c` before review (spec Q13) |
| R-9 | The HR copy reaches a wall | Accepted trade-off (spec bad news 1). Banner on every sheet, tick off on every open, office-print note |

**Two small points from the spec, settled my way unless you say otherwise:**
- `opening` in the copy is a **number** (0 or 1 for a seat, up to k for a merged box), so one key
  serves "Job opening raised" and "{k} job openings raised". AC-28's "never a string" holds; its
  "true or false" wording should read "a count".
- HR for two companies: footer and file name list both names, comma-separated (spec assumption).

**Noticed, not touched (yours to decide later):** filter selects on Positions are 32 px tall on a
phone (02-design WC9); the global A4 rule still forces landscape on other prints (D10).

---

## 4 · Questions for Surbhi

| # | Question | Blocks | My recommendation |
|---|---|---|---|
| Q-A | The paper uses its own small card and tree function, with the screen's markup and CSS, instead of adding options to the shared `ocRender` / `ocNodeCard` (which always draw avatars). Agree? | Step 2 | Yes |
| Q-B | Anyone else working in the Positions screen code this week? Are the 064-old-v2 and 064-old-chart rows on the work board finished? | Step 1 | - |
| Q-C | A throwaway container of my own for the browser checks (not `hrlocal-bench`, not 064's)? | Step 1 browser check | Yes |
| Q-D | If several sheets at 10× is too slow, do you want to hear the number first, before any limit is added? | Step 6 | Yes |

Still open from the spec, not blocking: Q12 (security engineer: AC-2's narrower scope), Q13 (`01c`
update), Q16 (UX wording of the ticks), Q4 (after the iPhone test), Q8 (counsel, before DTC).

---

## 5 · Subtract pass

**Removed on this pass:**
- Options on the shared `ocRender` / `ocNodeCard` (a paper card of its own is smaller and cannot
  change the Organisation chart).
- A `<div>` holder for the paper in `positions.html`: the holder is made by the code when needed and
  removed in the clean-up, so `positions.html` gets only the button.
- A change to `check_portal_trays.js`: the panel is the existing `.pos-sheet` tray, already covered.
- Any memo of layouts across panel opens: only the last layout, while the panel is open.
- The "best three drawn for real" fallback: built only if the 0.5 pt check fails.
- A full Python test run: no Python changes; one module run proves AC-51.
- A limit on the number of sheets: only if the 10× measurement says so, and with Surbhi's word.

**Kept only because the requirement fails without it:** the allowed copy (PRIV-1); the wrap and the
two-drawing layout (300 ms and the kill line); clean-up on close as well as `afterprint` (phones); the
banner on every HR copy sheet; the new CI check file (065 and 069 would otherwise collide at the end of
`check_positions_tree.js`).
