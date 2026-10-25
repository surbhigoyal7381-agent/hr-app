---
slice: 069-wall-chart-print
artifact: 06b-security-verification
author: hrms-security-privacy-engineer
date: 2026-10-25
status: verification of the built slice against 01c rev 2, plus Surbhi's change of 25 Oct 2026 (HR copy for HR only)
code: branch slice/069-wall-chart, worktree .claude/worktrees/069-wall-chart, commits 9e9cf2c6..f4d4fe31 (8), diffed against origin/dev
---

# 069 · Security and privacy verification: the wall chart PDF

**I recommend. Surbhi decides.** I wrote the requirements (`01c`) that I am checking here. So this
is the builder of the rules marking the build against them (lesson 6). Please have a second reader
check two things: my verdict on SEC-3 and my reading of the HR-copy gate (§3).

## 0 · Bad news first

1. **Ctrl+P on the list view puts leaving dates on paper.** HR on Positions, View = "As a list",
   presses Ctrl+P. The printed table has a "Notice period" column with each leaver's date, plus
   "leaving 1 Jan" after the name, "key seat", "Frozen", "37%" and "covering". The spec (§7) says
   nobody, HR included, may put a leaving date on paper from Ctrl+P. The new CSS rule hides these
   only in the **chart** view. *Verified by running it* (headless Chromium, print media).
   **SEC-3 is partly met. This blocks the release (P1) until it is fixed or Surbhi accepts it in
   writing.** The fix is about one CSS rule.
2. **Ctrl+P with the "Only seats where somebody is leaving" filter tells the reader who is leaving.**
   The print header says "Show: Only seats where somebody is leaving", and only those seats print at
   full strength (3 of 91 in my run); the rest are faded. On a one-person seat that names the leaver.
   No date prints. P2: fix or accept in writing.
3. **Nothing blocks the build on the wall chart itself.** With every sensitive field filled with
   marker values, HR copy off, on and off again, through the real print path: no marker reached
   paper. *Verified by running it.*
4. **The HR-copy gate is a page rule, not a security control, and that is fine.** Anyone can switch
   it on in their own browser's developer tools. I did it as a manager: the tick appeared and the
   paper showed "leaving 30 Nov" — a date for that manager's own report, which the server had
   already sent to their screen. The server, not the tick, decides what each reader holds.

## 1 · What I ran

| Check | Result | Label |
|---|---|---|
| `node scripts/run_dom_tests.js` (CI DOM suite) | 13 run, 0 failed. Wall chart 171 checks, positions tree 165 | Verified by running it |
| `node scripts/check_wall_chart.js` alone | 171 checks, pass | Verified by running it |
| `check_app_integrity.py`, `check_no_demo_passwords.py`, `check_design_system.py`, `check_portal_assets_gate.py`, `check_api_paths.py --max 0`, `check_undefined_js.js`, `check_portal_handlers.js`, `check_portal_trays.js --static` | All pass | Verified by running it |
| `git diff origin/dev --stat` | 10 files, **no Python**, no new `@frappe.whitelist`, no `ignore_permissions` change | Verified in code |
| Added lines searched for `gpFetch`, `frappe.call`, `fetch(`, `window.open`, `createObjectURL`, `localStorage`, `sessionStorage`, `sendBeacon`, `XMLHttpRequest`, `console.*` | None | Verified in code |
| My own break script (scratch, not in the repo): real page, headless Chromium, print media, 25 marker values | Results in §4 and §5 | Verified by running it |
| PDF metadata of an HR copy (headless `page.pdf`) | `/Title` = "HR copy - Wall chart - Sample Fashions Pvt Ltd - 2 levels - A3 - 2026-10-24"; no `/Author`; `PRINTER-SNTL` absent | Verified by running it |
| `check_wall_chart_browser.js` (the build's Playwright check, not CI) | Sizes and the layout search passed (All on A1 = 9.0 pt, HR copy on and off). Then it **crashed** at the line audit (`check_wall_chart_browser.js:171`: the paper was gone when it was read). I ran it with Playwright 1.64.1 and Chromium headless shell 1223; the builder used 1.59.1. Its Ctrl+P part (AC-3) did not run for me. My own script covered Ctrl+P instead (§4). Likely a timing problem in the test, not the product: for the test engineer | Verified by running it |
| 064's server refusal test (SEC-2 b), `test_positions_064.py` | **Not run.** It needs a site; running it means copying the branch into the shared bench, which needs approval | Unknown |
| A real Chrome or Edge window, a payslip printed after, an iPhone | **Not done** | Unknown |
| The `ignore_permissions` counter and PII-in-logs gates | Not in `scripts/`; nothing to run. No Python changed, so the count cannot have moved | Unknown (programme gap, not this slice) |

## 2 · Requirement by requirement

| # | Verdict | Mechanism (file:line on the branch) | Test that proves it |
|---|---|---|---|
| **SEC-1** No new endpoint; nothing leaves the page but the print window | **Met** | No Python in the diff. Choices live in `POS.wall` only (`portal.js:2683-2686`). "See who is not in a seat" opens the existing tray (`portal.js:3045`), which makes no call either (read) | `check_wall_chart.js:204-268`: traps on `gpFetch`, `frappe.call`, `fetch`, `window.open`, `URL.createObjectURL`, `Storage.prototype.setItem`; every choice changed, both ticks; print runs; 0 calls. In CI |
| **SEC-2** Button shows exactly when rows show; no new role | **Met in code; (b) not re-run** | Hidden at load start, shown only for rows (`portal.js:321-323`, `:350`). Server gate unchanged: `register.py:264-265` | (a) `check_wall_chart.js:187-202` (rows, no rows, failed load). (b) 064 refusal test **not run** here. (c) switch-on check C2, open |
| **SEC-3** Old Print button gone; Ctrl+P prints no flag, tag, HR box or "printed by" | **Partly met** | Button gone (`portal.js:1214`, label "Zoom"). Print rule `panels.css:2175-2177`. `posPrintHead` drops the name (`portal.js:1298`). **Gaps: list view and the "leaving" filter (F1, F2)** | (a) `check_wall_chart.js:434-440` (one `window.print()`, no `onclick`). (c) `check_positions_tree.js` (CI): CSS selectors and header without `PRINTER-SNTL`. (b) Playwright in `check_wall_chart_browser.js`, **not CI**, chart view only. No test covers the list view |
| **SEC-4** Page size lives only for the wall chart's print | **Met** (one edge, F3) | `<style id="pos-wall-page">` appended last (`portal.js:2899-2901`); removed with the title and class on `afterprint` (`:2843-2850`, `:2906`) and on panel close (`:2318`, `:2853`) | `check_wall_chart.js:373-396` (mm sizes, last in body, cleaned both ways). My run: after afterprint and close, no style, title back, no class, no holder. Manual payslip-after (AC-42) **not done** |
| **PRIV-1** Paper carries only allowed fields | **Met** | `posWallCopy` builds a new object from named fields only (`portal.js:2376-2408`); leaving and opening only when `hr` (`:2385`, `:2404`); the card draws only the copy (`:2413`) | `check_wall_chart.js:82-135` (sentinel run twice, AC-27a/b), `:102-126` (exact keys, AC-28). AC-29 (break on purpose) recorded in `05-implementation-notes.md` §5. My run added 13 more markers (email, user id, plan on person, notes, effective date, reason, cover-for, unseated job role, seat counts) through the **real** layout and print: 0 on paper, HR copy off and on |
| **PRIV-2** File name, footer, metadata name nobody | **Met** (manual Chrome/Edge not done) | Title `portal.js:2902-2904`; footer `:2875-2881` (company, branch count, levels, start seat title, date, count) | `check_wall_chart.js:377-382`, `:397-401` (pattern, prefix iff tick, no name, no `PRINTER-SNTL`). My headless PDF: Title = file name, no Author |
| **PRIV-3** Staff told before names go on a wall | **Not met yet** — release-time | Not code | Switch-on check C1 and counsel Q1, both open |
| **PRIV-4** HR copy tick: who, off each open, banner, no plans | **Met, with Surbhi's 25 Oct change** | Gate `posWallMayHr()` (`portal.js:2368-2370`) = `unseated` present AND `may_see_leaving`; used by the tick (`:2815`) **and** by the copy (`:2377`), so asking without it prints the wall copy. Off every open (`:2686`). Banner and footer tag on every sheet (`:2881`, `:2888`). Office note (`:2818`) | `check_wall_chart.js:128-135` (forced leaving, no-leave reader), `:300-321` (manager gets no tick and no HR keys; HR gets it, off on 3 openings), `:397-416` (banner on every sheet, HR file name). Plans: PRIV-1 tick-on run (`PLAN-SNTL`, `WHO-SNTL`, `REASON-SNTL` absent) |

**01c wording to update** (I own it; I did not edit it in this pass): PRIV-4 first bullet should read
"exists only for HR (the payload carries `unseated`) and when the server sent `may_see_leaving: true`".
§0 item 3 is then closed. §4's list of what Ctrl+P never prints overstated SEC-3 (see F4).

## 3 · The HR-only gate: is it sound?

**My reading.** The tick shows when the server sent the "in no seat" list (`unseated`) and leaving
dates are allowed. The server sends `unseated` only when `permitted_employee_filters()` is not "nobody"
(`register.py:446-448`): Administrator, System Manager, or HR Manager / HR User with a company (a
Company User Permission, or their own Active Employee record) (`access.py:193-215`, `:252-286`).
*Verified in code.*

**Sound, for what it is.** It is a product rule: "the HR copy is an HR tool". It is not the control
that keeps leaving dates away from people. That control is on the server: `may_see_leaving` and the
reporting-line filter (`register.py:335-350`). Whatever the tick does, the paper can never show more
than the reader's own payload, because the copy reads only that payload. *Verified in code and by
running it.*

**It fails closed.** The key is absent, not empty, for a non-HR reader, and that is pinned on the
server by `test_positions_064.py:147-151` (a Positions reader with no HR role gets no `unseated`).
Absent key → no tick, and `posWallCopy` drops the HR fields even if `hr` is forced. *Verified in code;
the Python test not run by me.*

**What can spoof it.** Only the reader, in their own browser. Demonstrated: a manager sets
`POS.unseated = []` in the console; the tick appears and the paper shows their report's leaving date.
They already see that date on screen and can screenshot it. No data widens. Forcing `POS.wall.hr` alone
(without the marker) gives a banner and an "HR copy -" file name over a plain wall copy: over-labelled,
harmless.

**What can break it** (each changes who gets the tick without anyone touching this slice):

| Change | Effect | Direction |
|---|---|---|
| A future change sends `unseated` to managers (for example "my team, not in a seat") | Every such manager gets the HR copy tick for what they can see | Widens. The 064 test would need to change, which is the tripwire |
| A tenant gives line managers the HR User role for some other reason | Those managers become "HR" here, and with HR User in the full-reach roles they get **every** leaver in their scope, on screen and on the HR copy | Widens. A role decision, not code. Add to switch-on check C2 |
| An HR leaver whose role and Company User Permission were never removed | Keeps the tick. `permitted_companies` reads User Permissions before it checks for an Active Employee (`access.py:211-213`) | Same as R2, already accepted |
| HR with no Company permission and no Active Employee record; or a leadership role added to full-reach roles without an HR role | No tick, though they see leaving dates | Narrows. Fails closed: a support ticket, not a breach |
| The `unseated` key is renamed or removed | The tick disappears for everyone | Narrows. Fails closed |

**Recommendation:** keep the gate. Add one sentence at `register.py:440-448` saying the HR copy tick
depends on this key, so the next person who widens `unseated` knows what else moves. Cheap; your call.

## 4 · Break attempts

| Attempt | What happened | Label |
|---|---|---|
| 25 marker values in every sensitive field (person, seat, plan, unseated list, printer name), wall copy | 0 on paper; title "Wall chart - …"; no banner; no "leaving", no "Job opening" | Verified by running it |
| Same, HR copy on | 0 markers; 2 "leaving {d Mon}" lines; "Job opening raised"; banner; "HR copy - …" title; the Job Opening ID never appears | Verified by running it |
| Tick on, then off again in the same visit | Back to the wall copy exactly: 0 leaving lines, no banner | Verified by running it |
| Reader with `may_see_leaving: false`, leaving value forced in | Nothing prints (CI test `:128-135`) | Verified by running it |
| Manager (leaving dates for own line, no `unseated`) | No tick in the DOM; forced HR prints no date | Verified by running it |
| Panel open, paper drawn, Ctrl+P instead of Open print preview | The holder stays hidden (`panels.css:2194`, shown only under `body.pos-wall-printing`, `:2235-2239`); the panel is hidden in print | Verified in code |
| Ctrl+P, chart view, no filter | No flag, tag, HR box or printer name. Prints initials (242) and "3.33 of 7.77 filled" | Verified by running it (F4) |
| **Ctrl+P, list view** | **Leaving dates, "key seat", "Frozen", "%", "covering"** | Verified by running it (F1) |
| **Ctrl+P, chart view, Show = leaving** | **Header names the filter; 3 of 91 boxes at full strength** | Verified by running it (F2) |
| Print, `afterprint` never fires, leave Positions without closing the panel, Ctrl+P on Attendance | **The HR copy prints instead of the Attendance page**; title and page size stay | Verified by running it (F3) |
| Team notes prints (`portal.js:9334-9365`) | Their own `window.open` document; our style, class and title are in the main document and cannot reach them | Verified in code |
| Payslip | Opens a drawer in the same page; after a normal print our state is gone, so it prints as before. Only F3's stuck state would affect it | Inference |
| `@page` leak | The added style is removed on `afterprint` and on close; the global A4 rule is unchanged (R4) | Verified by running it |
| File name and PDF title | Company, levels, paper, date; optional "HR copy - ". No person, no seat title, no user | Verified by running it |
| Browser history | The tab title changes during the print; history may keep "HR copy - Wall chart - {company} - …". No personal data in it | Inference — not checked in a real Chrome profile |
| Browser cache | No new response or file. The PDF goes where the user saves it (R3) | Verified in code |
| Script injection via seat titles, branches, names | Every value passes through `posEsc` before it reaches HTML (`portal.js:2413-2436`, panel `:2793-2825`) | Verified in code |

## 5 · Findings

| # | Rank | Urgency | Finding | Scenario | Fix (smallest) |
|---|---|---|---|---|---|
| **F1** | **Major** | **P1 — blocks the release** | Ctrl+P on the list view prints leaving dates and the flags the spec bans | An HR Manager at DTC, on Positions, View = "As a list", presses Ctrl+P. The paper lists every seat with a "Notice period" column (`portal.js:661-663`) and "leaving {d Mon}", "key seat", "Frozen", "%", "covering" as `.pf-card-meta` (`:631-652`). `panels.css:2175-2177` hides only chart classes. Spec §7 says nobody, HR included, may do this | In the Positions print block, hide the list's Notice period column and the `.pf-card-meta` notes in `#pos-body`. Add the list view to the Playwright Ctrl+P check. About one CSS rule and one test |
| **F2** | Major | P2 — fix or accept in writing | Ctrl+P with Show = "Only seats where somebody is leaving" tells the reader who is leaving | Same HR Manager picks that filter, then Ctrl+P. The header prints "Filter: Show: Only seats where somebody is leaving" (`portal.js:1287-1294`, `:1303`); only the matching seats print at full strength (`ocNodeCard` opacity, `:219`). On a one-person seat that names the leaver | In print: leave "Show" out of the printed filter words, and print faded boxes at full strength. Or accept: HR chose a leavers view on purpose, and no date prints |
| **F3** | Minor | P3 | The wall chart's print state can outlive the Positions panel | A phone browser that never fires `afterprint` (the code's own comment, `:2318`). HR prints, then taps to another panel without closing the wall panel: `switchPanel` (`:3334`) does not close `#pos-layer`. Body keeps `pos-wall-printing`, the page-size style and the "HR copy -" title. Ctrl+P on any panel prints the HR copy. Same user, and the print preview shows it, so no new person sees anything | Also clean up when leaving the Positions panel. A one-line call; the engineer chooses where |
| **F4** | Minor | P4 | My `01c` §4 promised more than SEC-3 tests | Ctrl+P in the chart view prints initials (`.av`) and "x of y filled". Initials repeat the printed name; counts are about seats, not people. No code change needed | Correct 01c §4, not the code |

No P0. No Blocker against the wall chart's own output.

**Worries** (not findings: I cannot yet write "this actor, this path, sees this data"):
- Safari and Android may fire `afterprint` early or never. Early could print the screen instead of
  the wall chart; never is F3. Nobody has tested an iPhone (AC-43).
- When slice 065 lands, its plan keys arrive in the rows. The copy is an allowed list, so any shape is
  safe, but C3 (065's tests at `:830`, `:857` still pass, the fixture keeps `plan`) is still open.
  065 is not on `origin/dev` yet.
- The browser keeps no record of who printed; so does the server (R1). If an HR copy turns up on a
  wall, nobody can say who made it.

## 6 · Residual risk

| # | Risk | Label | Owner | Status |
|---|---|---|---|---|
| R1 | Nobody can tell who printed the chart or an HR copy. Confirmed: the slice makes no server call | Intentional trade-off | Surbhi | Accepted 24 Oct 2026. Unchanged |
| R2 | A leaver with a live login and HR role still opens Positions; now also keeps the HR copy tick (`access.py:211-213`) | Temporary debt — removed when offboarding disables the login or role | Surbhi | Accepted 24 Oct 2026. Widened slightly by the HR-only gate; same people, same data |
| R4 | The global A4 landscape rule still applies to other portal prints | Intentional trade-off | Surbhi | Accepted 24 Oct 2026 (D10) |
| R5 | An HR copy is mishandled: pinned up, left on a desk, sent to a print shop | Intentional trade-off — the banner (every sheet, verified), the "HR copy -" file name (verified) and the office note (verified) are labels only | Surbhi; DTC for handling | Decision accepted 24 Oct 2026. Handling rules wait on counsel Q4, Q5 |
| F1 | Ctrl+P on the list view prints leaving dates | **Dangerous debt if shipped — escalate now** | Surbhi | **Open.** Fix, or accept in writing with a name and date |
| F2 | Ctrl+P with the leavers filter names leavers | Temporary debt | Surbhi | Open: fix or accept |
| F3 | Print state survives leaving the panel when `afterprint` never fires | Temporary debt | Engineer | Open |

## 7 · What blocks what

**Blocks the release (push to dev for DTC use):** F1. Everything else in the build is met or waits on
manual checks.

**Blocks switch-on at DTC** (unchanged from 01c, plus one):
- C1. PRIV-3 note in the release note, and DTC's written confirmation; counsel Q1.
- C2. Someone with access lists the roles holding Read on `Alvoraa Position` at DTC, **and now also
  who holds HR Manager or HR User**, because that decides who gets the HR copy tick. *I could not
  check that; it needs read access to DTC's Role Permissions and User roles.*
- C3. When 065 lands, its tests and the plan keys in the fixture.
- C4. HR copy at DTC: counsel's answers to Q4 and Q5 in the release note. Until then, tell DTC not to
  use the HR copy.
- Manual: AC-42 (Chrome/Edge window, payslip after), AC-43 (iPhone), and the 064 refusal test on a site.

## 8 · What I could not verify, and what I would need

- 064's server refusal test (SEC-2 b): a site with this branch, run by someone allowed to use the bench.
- Real Chrome and Edge windows, browser history titles, an iPhone, Android `afterprint`: the devices.
- DTC's roles (C2): read access to DTC's site.
- The build's own Playwright check, end to end: it crashed part-way with my Playwright and Chromium
  versions (§1). It needs a re-run with the builder's versions, or a fix to the test.

## Subtract pass

Removed from this document: a full NFR table (no server change, nothing to say beyond §2), a
re-check of the baseline obligations (no new obligation is engaged; the baseline was verified 24 Aug
2026, 62 days ago, still fresh), and a proposed server test for the gate (064's test already pins the
key). Kept: four findings, each with a scenario I ran.
