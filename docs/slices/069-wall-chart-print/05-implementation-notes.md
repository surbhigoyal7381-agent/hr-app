---
slice: 069-wall-chart-print
artifact: 05-implementation-notes (change-process steps 4 and 6; the contract calls it 03-implementation-notes, this folder's numbering is the lead session's)
author: hrms-fullstack-engineer
date: 2026-10-24
branch: slice/069-wall-chart in .claude/worktrees/069-wall-chart, cut from origin/dev 6aaf9ffd
status: built LOCALLY. Not pushed, not deployed, not merged into dev. No bench, no container, no site touched.
---

# 069 · Download wall chart (PDF) — implementation notes

## Bad news first

1. **Several sheets at 10× is very heavy.** 891 seats, All, A4, several sheets = **130 sheets**, about
   **116,000 boxes** in the print page (45 MB of markup). Building it: about 2 s. The browser laying it
   out: **35–44 s**. Chromium making the PDF: **83–115 s**. At DTC's size (90 seats) the same choice on
   A3 is 9 sheets and fast. As agreed (Q-D), **no limit was added.** Surbhi decides whether to add one.
2. **The iPhone page-size test (AC-43) was not done.** It needs a real iPhone and a site the phone can
   reach. The plan is below. Not tested at all: Safari, Firefox, the interactive Chrome/Edge print
   window (AC-42 by hand).
3. **One difference from prototype-v1 needs Surbhi's yes (§4, PD-1):** in a wrapped column, boxes sit at
   the column's left edge. The prototype centred them, which left the tick short of every box narrower
   than the widest one in its column (the line check found 3 boxes "joined to nobody").
4. **HR copy tick: HR only (Surbhi, 25 Oct 2026; changed in the last commit).** It used to follow
   the server's `may_see_leaving`, which a manager also gets for their own reports. It now needs **HR
   and** leaving dates sent. HR is the page's existing signal, so no server change was needed: the "in
   no seat" list (`unseated`) reaches only HR Manager, HR User, System Manager and Administrator
   (`permitted_employee_filters`, `access.py:194-215`). A plain manager is refused, so the key is absent
   for them. The page already uses `POS.unseated !== null` as "HR only" for the HR box and tiles.
5. `portal.js` grew by **578 lines**, not the strategy's estimate of about 350. Most of it is the panel
   (words for every state) and the layout sums.
6. The Python suite was **not run**: no Python changed, and AC-51's 064 refusal test needs a site. I did
   not create a container for it (§7).

## 1 · What was built, file by file (rung 4: new code, browser only)

| File | What | Mechanism, and why |
|---|---|---|
| `portal.js` `posPaintTree` | Print button removed; zoom row labelled "Zoom" | Extend. D-2: the old button printed flags, leaving tags and the HR box |
| `portal.js` `posPrintHead` | "printed by {name} ({role})" removed | Extend. D5 / AC-3a |
| `portal.js` `posGroupSiblings` | Optional third argument `all`: ignore `POS.ungrouped` | Extend. Paper merges identical seats as the data says (D-6, AC-26). Both old callers pass two arguments |
| `portal.js` `posLoad` | Button hidden at the start of every load, shown when rows came back | Extend. AC-4, including a failed reload |
| `portal.js` `posCloseSheet` | First line: the wall panel's clean-up | Extend. Phones may not fire `afterprint` |
| `portal.js` new `posWall*` block after `posWire` | Allowed copy, paper card and tree, the layout, the panel, print, clean-up | New code. One block, own prefix (hot file rule) |
| `panels.css` Positions print list | `#panel-positions .oc-flag`, `#panel-positions .oc-tag`, `.pos-nomgr-row` added before `.noprint` | Extend. SEC-3; 064's regex check still matches |
| `panels.css` new block after the Positions print block | Paper tokens (`:root`), paper rules, sheets, print rules while printing, panel controls, phone rules | New CSS |
| `positions.html` | One button, and a `<div class="tb-acts">` round the two buttons | Extend. P1, P2 |
| `scripts/check_wall_chart.js` + `alvoraa_portal/tests/portal_wall_chart_test.js` | CI checks (jsdom, real page source); 13th DOM test | New test |
| `scripts/run_dom_tests.js` | One `RUN` entry; `EXPECTED_BROWSER_TESTS` 12 → 13 | Edit |
| `scripts/check_positions_tree.js` 4f | Asserts no Print button, "Zoom" label, the three print selectors, a header with no PRINTER-SNTL / ROLE-SNTL / "printed by" | Edit, on purpose (bad news 2 of the strategy) |
| `scripts/check_wall_chart_browser.js` | Playwright, not CI: sizes, full-search comparison, lines on paper, PDF sizes, Ctrl+P, phone | New test (see §4, SD-1) |
| `scripts/lib/wall_chart_fixture.js` | F-DTC90 (with the sentinel option), F-OWNER, F-GROUP, F-NOLEAVE, 10× | New, shared by the two checks |

No DocType, field, endpoint, setting, flag, cache, package or Python. `ignore_permissions` count unchanged.

## 2 · Commits (all on `slice/069-wall-chart`, none pushed)

| Commit | Step |
|---|---|
| `9e9cf2c6` | 1 · Ctrl+P prints safely; old Print button goes |
| `b83f76eb` | 2 · Allowed-field copy and the paper drawing |
| `a84bb074` | 3 · Layout to the paper's shape; kill-line measured |
| `72cfe27f` | 4 · Button and panel |
| `d47f658b` | 5 · Open print preview: page size, file name, footer, clean-up |
| `16286caa` | 6 · Several sheets; PDF size checks (and two step-5 fixes the PDF check found) |
| (this commit) | 8 · Design-system tokens for the paper colours, subtract pass, these notes |

## 3 · Numbers

**Kill line (AC-32), F-DTC90, full box** (title, designation when different, branch · department,
names), Show Vacant on, one sheet:

| Chart | Laid out | A4 | A3 | A2 | A1 | A0 |
|---|---|---|---|---|---|---|
| 2 levels, HR copy off | 1128 × 608 px | 9.0 | **13.0** | 18.7 | 26.8 | 38.1 pt |
| All, HR copy off | 3344 × 2118 px | 3.0 | 4.4 | 6.3 | **9.0** | **12.8** pt |
| 2 levels, HR copy on | 1128 × 629 px | 9.0 | 13.0 | 18.7 | 26.8 | 38.1 pt |
| All, HR copy on | 3344 × 2138 px | 3.0 | 4.4 | 6.3 | 9.0 | 12.8 pt |
| All, every seat showing a designation (worst case) | 3344 × 2195 px | | | | 9.0 | 12.8 pt |

**All on A1 = 9.0 pt ≥ 8 pt, so the branch stays on the box.** Prototype reference: 13 / 9.5 / 13.6 pt.
All on A3, several sheets: 9 (3 × 3), as the prototype. The warning reads "Use A1 (names at 9 pt)" and
"Use 9 A3 sheets" (AC-33).

**Layout (strategy 2.2):** two drawings at DTC: 64–139 ms across runs; trying all 27 wraps for real:
775–1036 ms. Same choice (K 10, KU 2, 9.0 pt on A1). At 10×: 576–731 ms against 8–9 s, same choice.
The fallback ("draw the best three for real") was **not** built: it was never needed.

**AC-35, median of 5 changes** (this laptop; wall-clock, reported not promised): Paper 1–2 ms, Sheets
1–2 ms, Start from 11–12 ms, Levels 1–2 ms, Show Vacant 14–18 ms, HR copy 14–16 ms. All under 300 ms.
"Working out the size…" shows only after a drawing that took over 150 ms (never at DTC's size).

**Server calls: 0. Payload bytes added: 0.**

## 4 · Differences — from prototype-v1, and from the strategy

**From the prototype (each needs Surbhi's yes; none is yet given):**

| # | What | Why |
|---|---|---|
| PD-1 | Boxes in a wrapped column sit at its left edge, not centred | Centred, a wide box (Security Guard, 2 columns of names) pushed its narrower neighbours right and their ticks stopped short: 3 boxes joined to nobody in "All". Visible only in a column that holds a wider box |
| PD-2 | Several tops each drawn with their own seats, 40 px apart | D-3 (approved); the spacing is my choice, nothing was drawn |
| PD-3 | HR copy tick under "Show Vacant" in an "On the paper" group; "Print in the office…" as an amber note under the group; HR banner 7 mm tall at 10 pt bold | D-8 / Q16, the spec's proposal. The banner height is fixed, so AC-30's "measured height" is the fixed 7 mm |

**From the strategy (how, not what):**

| # | What | Why |
|---|---|---|
| SD-1 | Browser checks run on the real page built from this checkout, served by Playwright with the server stubbed, in a new `check_wall_chart_browser.js` — not on a throwaway container and site, and not as new cases in `check_positions_connectors.js` | Cheaper and touches nothing shared (Q-C allowed my own container; none was needed). The fixtures load into `POS` either way. The 064 connector rule was ported into the new file, pointed at the paper |
| SD-2 | The page-size `<style>` goes at the end of `<body>`, not `<head>` | It must come after the portal's A4 rule wherever that rule sits. In the test page the A4 rule sat in the body and every PDF came out A4 |
| SD-3 | While printing, `body` is `visibility:hidden` and the paper is pinned to the top | Loose text in `<body>` is not an element, so "hide every other child" cannot hide it; in the test page it pushed a blank second page |
| SD-4 | A shared fixture file `scripts/lib/wall_chart_fixture.js` | Two checks use the same data |
| SD-5 | The worktree is `.claude/worktrees/069-wall-chart` on `slice/069-wall-chart` (the strategy said `069-wall-chart-print`) | The lead session's brief named it so |

## 5 · Acceptance criteria

| AC | How it is met | Proof |
|---|---|---|
| 1 | Print button gone, "Zoom" label | `check_positions_tree.js` 4f (CI) |
| 2 | One `window.print()` between `posLoad` and `ocPaint`, inside `posWallPrint` | `check_wall_chart.js` (CI) |
| 3, 3a | One CSS rule; header without "printed by" | Browser: 90 titles, 242 name lines print; 0 of 183 flags / 403 tags / 1 HR box; header names nobody. CI: CSS selectors and header |
| 4–7 | Button, dialog, focus, Escape, scrim | CI (jsdom); AC-5/6 on a 390 px phone in the browser check |
| 8 | No call, window, blob or storage write; print once | CI, with traps on `Storage.prototype` |
| 9–17 | Panel words, options, notes | CI |
| 18–21, 24–26 | Copy and drawing; counts 90 / 363 / 23 / 11 / 72; merges | CI |
| 22, 50 | Wrap and bars; several tops | Browser: 064 line rule on paper, 0 false or missing links in 6 states |
| 23 | Always light | Browser: white, `#2D2622`, 2 px `#5B4B8A` in the dark theme |
| 27a, 27b, 28, 29 | Allowed copy; sentinel run twice | CI. **AC-29 done:** copying `employee` into the copy and drawing it fails AC-27a, AC-27b, AC-28 (7 failures); copying it only fails AC-28 (3). Undone |
| 30, 31, 33, 36 | Plan sums from the measured size | Browser (numbers in §3); CI (words) |
| 32 | Kill line | §3: 9.0 pt |
| 34 | `role="status"`, `aria-live="polite"` | CI |
| 35 | Two drawings; "Working…" after a slow one; print waits | Browser timings; CI for the wait |
| 37–41, 44 | Style in mm, title, footer, clean-up both ways | CI; browser: each of A4–A0 both ways is a 1-page PDF of that size ±1 mm; A4 landscape back afterwards; PDF Title = file name, no Author |
| 42 | Manual Chrome / Edge window, payslip after | **Not done by hand.** Chromium headless only (above) |
| 43 | iPhone | **Not done** (plan §8) |
| 45–47, 63 | Several sheets | CI (labels, offsets, banner each sheet); browser: 9 pages for All on A3 |
| 48, 49 | Owner | CI |
| 51 | 064's refusal test | **Not run** (needs a site; no Python changed) |
| 52–54 | Switch-on checks C1–C3 | Release-time, not code |
| 55–65 | Ticks, HR copy, gate | CI |

Guards broken on purpose and seen to fail: step 1 (Print button, CSS rule, "printed by": 3 failures);
AC-27/28 (employee copied); AC-65 (gate removed: 2 failures); AC-8 (a storage write — first slipped
through because jsdom stores an item called "setItem"; the test was fixed and then failed as it should);
AC-58 (tick not reset); AC-37/39 (paper-name size, title not restored: 5 failures); AC-46 (no sheet
label); AC-22 (the real tick fault, before PD-1).

## 6 · The seven dimensions, against the code written

| Dimension | Before → after | Why |
|---|---|---|
| Performance | neutral for page views; slightly worse script size | 0 new calls or bytes from the server. `portal.js` +578 lines (about 25 KB). Layout runs only while the panel is open: two drawings, 64–139 ms at DTC |
| Security | improves | Ctrl+P and the old button no longer print flags, leaving tags, the HR box or the printer's name. No endpoint, role or `ignore_permissions` change |
| Reliability | neutral | Clean-up on `afterprint` and on every close. A print pressed mid-drawing waits. Risk: 10× several sheets takes minutes in the browser (bad news 1) |
| Scalability | **degrades at 10× for one choice** | Layout is fine at 891 seats (0.6 s). Several sheets copies the chart once per sheet: 130 copies at 10× on A4. Number reported; no limit added (Q-D) |
| Maintainability | degrades slightly | A second, small drawing of the tree, sharing the screen's classes and CSS; its lines are checked by the ported 064 rule |
| Data integrity | neutral | Reads rows already on the page; writes nothing; the layout is kept only while the panel is open |
| Compliance / privacy | improves in the system; new paper exposure by design | Allowed-field copy proved twice in CI; HR copy only with `may_see_leaving`, banner on every sheet, "HR copy -" file name |

## 7 · Commands run and what they said

- `node scripts/run_dom_tests.js` (full CI DOM suite, once at the end): **13 run, 0 failed.** Positions
  tree 165 checks; wall chart 162 checks.
- Earlier in the build one full run failed `portal_leave_063_test.js` R-39 (2 lines). It passed alone
  4 times, twice with this branch's `portal.js` and twice with origin/dev's, and passed in the final full
  run: a timing flake in that test, not this change.
- `check_portal_handlers.js`, `check_portal_trays.js --static`, `check_rating_bands.js`,
  `check_undefined_js.js`, `check_api_paths.py --max 0`, `check_app_integrity.py`,
  `check_nginx_conf.py`, `check_no_demo_passwords.py`, `check_portal_assets_gate.py`: all pass.
- `check_design_system.py`: **failed once** (6 loose colours: the paper's fixed hex colours). Fixed by
  naming them as `--paper*` tokens in a `:root` block; now passes.
- `check_wall_chart_browser.js` with Playwright 1.59.1 (Chromium): all passed (33 checks).
- **Not run:** `bench run-tests` (no Python changed; needs a site, and the bench is shared). AC-51.

## 8 · iPhone page-size test (AC-43) — plan, not done

What I could not test: anything on Safari or iOS. Playwright's WebKit cannot make a PDF, so it would not
answer the question. Steps for whoever has the phone (from strategy §2.5):
1. Real iPhone, Safari; record the iOS version.
2. Reach a local build over Tailscale; log in as a test HR Manager on that site only.
3. Positions → Download wall chart (PDF) → the top, All, **A1**, one sheet → Open print preview → Print →
   pinch the preview open → Share → Save to Files. Repeat for **A3**.
4. On the laptop: page width × height in mm (`pdfinfo` or PDF properties), page count, title, names
   readable at 100 %.
5. Record in `04-test-report.md`. If the size was ignored, Surbhi decides Q4.

## 9 · What else moved while I worked

`origin/dev` stayed at `6aaf9ffd` at every fetch (start of each step and before handoff). The one commit
in it that this slice's strategy had not seen, `6aaf9ffd ALV-213`, was read: phone rules in
`panels.css` (lines ~343–400), leave cards and a phone account-menu Escape handler in `portal.js`
(~5420, ~11860). None of it is in the Positions section or the print block; no conflict. The main
checkout's uncommitted `ux-learnings.md` and untracked folders belong to other sessions and were not
touched. The slice's other documents live untracked in `dev-integration-2026-10-24`; only this file is
committed here.

## 10 · Known gaps and shortcuts

| Item | Label |
|---|---|
| No limit on several sheets at 10× (bad news 1) | **Intentional trade-off**, waiting on Surbhi (Q-D) |
| iPhone, Firefox, manual Chrome/Edge window, AC-51 not run | **Temporary debt** — removed by the manual checks before release |
| HR copy tick gate = HR (the `unseated` key is present) AND `may_see_leaving`. A store HR person limited to a branch counts as HR | **Intentional trade-off**, per Surbhi 25 Oct 2026. If the HR scope rules in `access.py` ever let a non-HR role through, the tick follows them |
| The scope note's "Its seats report to managers in other branches" also shows for HR when a top seat's manager is a Closed seat (AC-25) | **Acceptable simplification** — the spec's state rule; rare |
| HR across two companies: names joined with ", " in footer and file name | **Acceptable simplification** (spec assumption) |
| Banner height fixed at 7 mm, not measured | **Acceptable simplification** |
| The filter list joins "and" without plural rules in other languages | **Acceptable simplification** — Positions is English-only today (Q9) |

## 11 · Subtract pass

Removed on this pass: the `:last-child` line rule on the paper (every last item already carries `ce`);
an earlier sum that reused the hanging-column maths for the tops grid and subtracted its gaps back out
(rewritten plainly). Not built: the "best three drawn for real" fallback (the 0.5 pt check never failed),
any limit on sheets, any memory of layouts across panel opens, any Python.

Noticed, not touched (Surbhi's to decide): filter selects on Positions are 32 px tall on a phone (WC9);
the global A4 rule still forces landscape on other prints (D10).

## 12 · Changes of 25 Oct 2026 (Surbhi, via the coordinator)

1. **HR copy for HR only.** `posWallMayHr()` = `POS.unseated !== null && POS.may_see_leaving`. Used
   by the tick and by `posWallCopy`, so asking for the HR copy without it still prints the wall copy.
   Tests (CI): a manager sent leaving dates for their own reports (`F.manager()`: `may_see_leaving`
   true, no `unseated`) gets no tick, and their copy holds no HR keys and prints no leaving date; an
   HR user gets the tick, unticked on each of three openings. Broken on purpose (gate back to
   `may_see_leaving` alone): 3 failures.
2. **Soft warning over 20 sheets.** When "Several sheets" would make more than 20 sheets, the result
   box turns amber and adds: *"This will make about {N} sheets and may take a minute. Choose a larger
   paper size to use fewer sheets."* Open print preview still works. DTC's own worst case (All on A4)
   is 16 sheets, so DTC never sees it today; 10× on A4 (130 sheets) does.
3. **PD-1 kept**, waiting for Surbhi's yes.

**Spec and 01c wording to change (I did not edit them: they are the lead session's untracked files in
`dev-integration-2026-10-24`):**
- Spec §7 matrix, "HR copy tick" column, and §0 personas: "Yes, if `may_see_leaving`" -> "Yes, for HR
  (HR Manager, HR User, System Manager) when leaving dates are sent". Owner: "Only if he holds an HR
  role".
- AC-58: "Given `may_see_leaving: true`" -> "Given an HR reader (the payload carries `unseated`) and
  `may_see_leaving: true`".
- AC-65 / US-14: add "A manager sent leaving dates for their own reports, with no `unseated` key, gets
  no HR copy tick and no HR words on paper."
- New AC under US-8: the 20-sheet soft warning, wording above.
- 01c PRIV-4 first bullet: "exists in the DOM only when the server sent `may_see_leaving: true`" ->
  "only for HR (the payload carries `unseated`) and when the server sent `may_see_leaving: true`"; bad
  news 3 is then closed.

## 13 · Review fixes of 25 Oct 2026 (06-review.md: M1, m1, m2, m3)

Surbhi: "never printed" covers every Positions view. D-4, D-5, D-6 stand (her yes). PD-1 still waits.

| Finding | Fix | Test (each broken on purpose and seen to fail) |
|---|---|---|
| **M1** Ctrl+P on "As a list" printed leaving dates, key seat, Frozen, covering and % (not new; the old tests covered only the chart) | The list's five flag notes carry `pos-flag`, the Notice period column `pos-leave-col`; the Positions print rule hides `#pos-body .pos-flag` and `#pos-body .pos-leave-col`. Names, titles, branch and department still print | `check_positions_tree.js` (CI): CSS selectors, and the list's printable markup holds no leaving date, key seat, Frozen, covering or %. Browser: list view in print media, 90 rows, none of those words |
| **m1** The hidden drawing stayed in the page and added a blank page to other panels' prints | `posWallLayout` keeps the drawing as markup only and removes the holder after measuring; `posWallPrint` draws it again | `check_wall_chart.js`: no holder after measuring |
| **m2** No `afterprint` + HR left Positions with the panel open = the next panel's Ctrl+P printed the HR copy | A `beforeprint` listener (in `posWire`) runs the wall chart's clean-up when the page is marked for the wall chart but Positions is not the active panel | `check_wall_chart.js`: on Positions the mark stays; from another panel, mark, page size, paper and title are gone before printing |
| **m3** Portrait A4, several sheets, HR copy: "Sheet k of n" cut off | Footer order is now HR tag, then "Sheet k of n (row r, column c)", then the rest; the footer may wrap to two lines inside its 7 mm | CI: footer order on every sheet. Browser: portrait A4 HR copy, 6 sheets, 0 footers cut |

**Change to spec wording (lead session's file, not edited):** AC-46 says the footer "adds" the sheet label
at the end. It now comes first, after the HR tag. AC-63 still holds: the footer starts "HR use only -
not for display ·".

**Not covered, for Surbhi:** the list view still prints its **Open** column (a vacancy count per seat).
Spec §7 bans the word "open" on the chart; it does not say whether a count column in the list counts.
Left printing; one more selector hides it if she says so.

Runs after these fixes: CI DOM suite and static checks below; browser check 35 passed.

