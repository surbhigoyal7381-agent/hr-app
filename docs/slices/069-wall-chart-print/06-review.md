---
slice: 069-wall-chart-print
artifact: 06-review (senior architect review, change-process step 5; the contract calls it 05-review, this folder's numbering is the lead session's)
author: hrms-technofunctional-reviewer
date: 2026-10-25
reviewed: branch slice/069-wall-chart, 9e9cf2c6..f4d4fe31 (8 commits) on origin/dev 6aaf9ffd, worktree .claude/worktrees/069-wall-chart
status: advice only. Surbhi decides whether the slice moves to dev.
---

# 069 · Download wall chart (PDF) — review

**Verdict: SHIP WITH FIXES.** The wall chart itself is sound: nothing private reached paper in any test I ran, the sizes and page sizes are right, and it is fast at DTC's size. But **Ctrl+P on the Positions "As a list" view still prints leaving dates, "key seat", "Frozen", "covering" and percentages** (proven in a browser). Four smaller print problems are proven too, and the manual release checks have not been done.

`SHIP WITH FIXES` is not permission to push. Pushing to dev still needs Surbhi's word.

## What I ran, and what I could not run

| Check | Result (proven, run by me on 25 Oct 2026) |
|---|---|
| `node scripts/run_dom_tests.js` (CI DOM suite) | **13 run, 0 not run, 0 failed.** Wall chart 171 checks, Positions tree 165 checks |
| `node scripts/check_wall_chart.js` alone | 171 checks, pass |
| `python scripts/check_app_integrity.py` | 798 checks, OK (doctype-shadowing part skipped: no bench) |
| `check_design_system.py`, `check_api_paths.py`, `check_portal_assets_gate.py`, `check_no_demo_passwords.py` | all OK |
| `check_portal_handlers.js`, `check_portal_trays.js --static`, `check_rating_bands.js`, `check_undefined_js.js` | all OK (exit 0) |
| `check_wall_chart_browser.js` (Playwright 1.59 Chromium, from the npx cache) | Every check up to and including SEC-4 passed: kill line 9.0 pt on A1, lines on paper 0 false or missing links in 6 states, dark theme stays light, AC-33 warning, AC-35 medians 2–58 ms, 10 PDF sizes exact, AC-40, 9 pages for 9 sheets, A4 back afterwards. **The 10× several-sheets stage had not finished when I wrote this.** So the Ctrl+P (AC-3, AC-3a) and phone (AC-5, AC-6) checks at the end of that script were **not seen by me**. The engineer reports them passing |
| My own probes (scratchpad, no source edited) | Four findings below, each with its output |

**Not run by anyone:** `bench run-tests` / AC-51 (no Python changed; needs a site). AC-42 interactive Chrome and Edge print window, plus a payslip afterwards. AC-43 iPhone Safari. Firefox. **Not checked by me:** the AC-29 mutation runs (the engineer reports them; I did not re-run them).

**Incoming work.** The branch is 8 linear commits by one author on top of `6aaf9ffd`. There are no merge commits. `origin/dev` is still at `6aaf9ffd` (fetched 25 Oct). Local `dev` has nothing unpushed. ALV-213 (`6aaf9ffd`) is already the base. Its CSS changes (phone rules, about lines 343–400) and its portal.js changes (leave cards, phone account menu) do not touch the Positions block, the print block or the toolbar. So nothing conflicts as text, and I found no clash in behaviour. The branch can fast-forward today.

**Process gap.** There is no `04-test-report.md` (this folder's `04` is the impact and strategy). AC-29, AC-32 and AC-43 say their results go there. They are in `05-implementation-notes.md` instead. That is fine as evidence, but the test-automation step left no artifact of its own.

---

## Blockers (P0 / P1)

None found.

## Majors

### M1 · P2 — Ctrl+P on "As a list" still prints leaving dates and every flag

- **What happens:** HR opens Positions, switches View to "As a list", and presses Ctrl+P. The table prints the Leaving column, "leaving 30 Nov" after a name, "key seat", the seat status ("Frozen"), "covering" and "50%".
- **Proof:** my probe (`probe_list.js`) loaded the sentinel payload into the list view and switched to print media. In the printed text it counted: `leaving` 2, `key seat` 90, `Frozen` 90, `covering` 198, `50%` 198.
- **The code:** `posCells`, `portal.js` about lines 625–665, uses `.pf-card-meta` spans and a plain `<td>` for the leaving date. The new print rule (`panels.css:2177`) hides only the chart's classes: `.oc-flag`, `.oc-tag` and `.pos-nomgr-row`.
- **Why it is wrong:** spec §7 says "Nobody, HR included, may put on paper ... from Ctrl+P: a leaving date, key seat, Frozen ... covering ... %". Surbhi's decision is that leaving dates, flags and private marks are never printed. The impact analysis (`04` §Security) says the slice "closes today's leak: Ctrl+P ... print flags, leaving tags".
- **Not new:** this was already true before the slice. AC-3 and SEC-3 test only the chart view, so the tests are green.
- **Smallest fix:** one selector in the Positions print block, so the list view does not print (for example, the list's table inside `#pos-body`). Or hide `#pos-body .pf-card-meta` and give the Leaving column a class to hide. One line of CSS, plus one assertion in `check_positions_tree.js`.
- **Question (must know):** I read "never on Ctrl+P" as covering every Positions view. If Surbhi meant only the chart, this drops to a P3 note. **Ranked P2 for now (provisional).** If she says the list was meant to be covered, it is P1.

### M2 · P2 — The release checks are not done, and some prototype differences have no yes

| Item | State |
|---|---|
| AC-42: Chrome and Edge print window by hand, A4–A0, then a payslip in the same tab | Not done. Headless Chromium only |
| AC-43: iPhone Safari page size | Not done. The plan is in `05` §8 |
| AC-51: slice 064's refusal test | Not run (needs a site) |
| PD-1: boxes at the left edge of wrapped columns, not centred | Waiting for Surbhi |
| D-4 "1 person below", D-5 no people note at 0, D-6 identical seats merged | Built to **"assumed answers (lead session)"** (`04` line 8). I found no record of Surbhi saying yes. The prototype-parity rule needs her yes |
| PD-3 / D-8: place and wording of the ticks, office note, banner | Approved in words only; Q16 is still open |

These are **temporary debt**. All of them close before the slice goes to DTC, not after.

---

## Minors (P3)

### m1 · The hidden paper stays on the page and adds a blank page to other prints

- **What happens:** HR opens the wall chart panel, chooses All (the paper is drawn off-screen into `#pos-wall-print`, about 2,118 px tall), then leaves Positions without closing the panel. The holder stays in `<body>`. Ctrl+P on another panel then prints **3 pages instead of 2**.
- **Proof:** my probe. The finances panel printed `{"pages":2}` before and `{"pages":3}` after.
- **Why it can happen:** `switchPanel` (`portal.js:3333`) never closes the Positions tray. The mouse cannot reach the sidebar past the scrim, but Tab can, because the dialog does not trap focus.
- **Smallest fix:** `posWallLayout` keeps `L.html` as a string already, so empty the holder once it has measured (`host.innerHTML = ""` before returning). `posWallPrint` builds it again anyway.

### m2 · If the browser never fires `afterprint`, another panel's Ctrl+P prints the HR copy

- **What happens:** HR presses "Open print preview" with HR copy on. The browser never sends `afterprint`. HR then leaves Positions with the panel still open. These stay in place: the `pos-wall-printing` class on `<body>`, the mm page-size `<style>` and the title "HR copy - Wall chart - …". Ctrl+P on any other panel then prints the HR copy on A3.
- **Proof:** my probe (print stubbed, no `afterprint` sent). Result: `{"cls":true,"title":"HR copy - Wall chart - …","sheets":1,"banner":"HR use only - not for display"}`, then a 1-page 420 × 297 mm PDF.
- **How likely:** it needs both a browser that skips `afterprint` (the spec names "some phone browsers"; I could not check which) and leaving the panel open. The person printing is the same HR user, so no one new sees anything. But it is the wrong document, at the wrong size, carrying leaving dates.
- **Smallest fix:** a `beforeprint` listener that runs `posWallCleanup()` when `#panel-positions` is not the active panel. About one line.

### m3 · On portrait A4 sheets, the footer cuts off "Sheet k of n"

- **What happens:** HR copy on, Several sheets, A4, with a chart taller than it is wide. The footer is 865 px of text in a 718 px box. `.pos-wall-foot` uses `white-space:nowrap;overflow:hidden`, and the sheet label is the last thing in the footer, so it is cut off the page.
- **Proof:** my probe `probe_foot.js`. With HR copy off, the same case fills exactly 718 of 718 px, so a longer company name or "from {seat title}" would cut it too.
- **Why it matters:** AC-46 makes the sheet label the only guide for taping the sheets together, and A4 is the office-printer case.
- **Smallest fix:** put "Sheet k of n (row r, column c)" straight after the HR tag, or let the footer wrap onto two lines inside its 7 mm.

### m4 · The spec and `01c` describe the old HR-copy rule

- **What happened:** on 25 Oct, Surbhi made the HR copy for HR only and added the soft warning over 20 sheets. The code is right: `posWallMayHr()` requires `POS.unseated !== null` and `may_see_leaving`. `unseated` is sent only when `permitted_employee_filters()` is not `NO_EMPLOYEES`, which means HR Manager, HR User or System Manager (`access.py:252-282`). I proved this by reading.
- **What is wrong:** spec AC-58 and AC-65 and `01c` PRIV-4 ("No role check of our own: the server is the control") still describe the old gate. Nothing in the spec covers the 20-sheet warning. The engineer listed the edits in `05` §12; nobody has made them yet.
- **Owner:** `hrms-business-analyst` and `hrms-security-privacy-engineer`. Not a code change.

### m5 · Question: does DTC's Owner get the HR copy?

- **What the code does:** if the Owner holds HR Manager or System Manager, he gets the tick.
- **Why it is a question:** the spec's own F-OWNER fixture has `unseated` set, which means he holds an HR role. "HR copy tick HR ONLY" could mean "HR roles" or "the HR department, not the Owner". Spec §7 still marks his role `[UNVERIFIED]`.
- **Question for Surbhi:** should the Owner get the HR copy if he holds an HR role? Should know, not must know. It does not change the verdict.

---

## Nits (P4)

- **Single seat:** with one seat and nothing under it, the Levels option reads "All 1 levels: every seat (1 seats, n people)". Proven by reading `posWallLevels` and `posWallCount`.
- **Sheet label not bold:** the prototype draws "Sheet k of n …" in bold. The build does not (parity difference PD-4).
- **`opening` is a count:** AC-28 says `true`/`false`; the code stores a number so a merged box can say "2 job openings raised". That makes sense. Fix the AC wording.
- **Script size:** `05` says `portal.js` grew by about 25 KB. It grew by **48,719 bytes** raw (948,668 vs 899,949). No NFR line covers script size; correct the note.
- **Test-count collision:** `run_dom_tests.js` sets `EXPECTED_BROWSER_TESTS = 13`. The main checkout holds another session's untracked `portal_appraisal_test.js`. Whichever lands second must set 14 when it rebases.

---

## AC verification

Legend: met (proven) · met (reported): the engineer's evidence, not re-run by me · partial · not met · not done.

| AC | State | Evidence |
|---|---|---|
| 1 | met (proven) | `check_positions_tree.js` 4f; diff `portal.js:1212` |
| 2 | met (proven) | `check_wall_chart.js` AC-2 |
| 3 | met for the chart (reported) · **list view not covered (M1)** | browser check end stage not seen by me; M1 probe |
| 3a | met (proven in jsdom) | `check_positions_tree.js` header check; `posPrintHead` diff |
| 4 | met (proven) | jsdom: rows, no rows, failed load |
| 5, 6 (phone) | met (reported) | browser check end stage not seen by me |
| 6, 7 | met (proven) | jsdom dialog, focus, Escape, scrim |
| 8 | met (proven) | jsdom traps incl. `Storage.prototype.setItem` |
| 9–17 | met (proven) | jsdom panel words and options |
| 18–21, 24, 26 | met (proven) | jsdom counts 90 / 363 / 23 / 11 / 72, 36 names in 4 columns, merge |
| 20 | met to an **assumed** D-4 answer | M2 |
| 22, 50 | met (proven) | browser: 0 false or missing links in 6 states |
| 23 | met (proven) | browser: white, `rgb(45,38,34)`, 2 px `#5B4B8A` |
| 25 | met (by reading) | status never copied |
| 27a, 27b, 28 | met (proven) | jsdom sentinel runs, off and on |
| 29 | met (reported) | `05` §5 |
| 30, 31, 33, 36 | met (proven) | browser sizes and warning |
| 32 | met (proven) | All on A1 = 9.0 pt (branch stays) |
| 34 | met (proven) | jsdom |
| 35 | met (proven at DTC size) | medians 2–58 ms. At 10× the first layout took 1.7 s; the code shows "Working out the size…" first (read, not timed by me) |
| 37–41, 44 | met (proven) | jsdom; PDF sizes in the browser |
| 42 | **not done** | M2 |
| 43 | **not done** | M2 |
| 45, 47, 63 | met (proven) | jsdom; 9 PDF pages |
| 46 | **partial** | label cut on portrait A4 (m3) |
| 48, 49 | met (proven) | jsdom F-OWNER |
| 51 | **not run** | needs a site |
| 52–54 | release-time | not code |
| 55–57 | met (proven) | jsdom |
| 58, 65 | met to Surbhi's 25 Oct rule (proven) | jsdom manager and HR runs. The spec text is out of date (m4) |
| 59–62, 64 | met (proven) | jsdom |
| 25 Oct: soft warning over 20 sheets | met (proven) | jsdom: message shown, Open print preview still enabled |

## Surbhi's decisions checked against the code

| Decision | State |
|---|---|
| HR copy tick for HR only | Met (`posWallMayHr`, also enforced inside `posWallCopy`). Owner question in m5 |
| Vacant tick on by default | Met (`vacant: true`) |
| No "printed by" | Met: wall chart footer and title, and `posPrintHead` |
| Page sizes in mm | Met: `@page{size:841mm 594mm…}`, never "A1" |
| Owner prints only what he sees | Met: the paper is built from `POS.rows` only, which the server scopes to his branch |
| Never printed: flags, leaving dates, HR-only box, private marks, plan data, ID, grade (except leaving dates and openings on the HR copy) | Met on the wall chart and on chart-view Ctrl+P. **Not met on list-view Ctrl+P (M1)** |
| Soft warning above 20 sheets | Met |

## Prototype parity (every difference I found)

| # | Difference from prototype-v1 | Surbhi's yes? |
|---|---|---|
| PD-1 | Wrapped-column boxes at the left edge, not centred | **Waiting** |
| PD-2 | Several tops each with their own seats, 40 px apart | D-3 yes; the spacing is the engineer's choice |
| PD-3 | Ticks in an "On the paper" group, amber office note, 7 mm banner | In words only (Q16 open) |
| PD-4 | "Sheet k of n" not bold in the footer | **No** (new, found here) |
| PD-5 | Footer cut with no ellipsis (the prototype had `text-overflow:ellipsis`), and it eats the sheet label (m3) | **No** (new, found here) |
| D-1, D-2, D-7, D-9 | Scope words, Print button removed, designation and department on the box, ISO date | Yes, 24 Oct |
| D-4, D-5, D-6 | "1 person", no note at 0, merged seats | **Assumed by the lead session, not recorded from Surbhi** |
| — | Soft warning over 20 sheets (not drawn) | Yes, 25 Oct, in words; no AC |
| — | The prototype's review bar, "Show at printed size" and "Saved" toast | Review aids, rightly not built |

## NFR verification

| Budget | Measured or reasoned | Pass or fail |
|---|---|---|
| 0 new server calls | jsdom traps, proven | pass |
| Result line ≤ 300 ms | DTC: medians 2–58 ms (proven). At 10×: the placeholder path in code (read) | pass |
| Print window under 2 s at DTC size | not measured by me (headless PDF is not the print window) | not checked |
| PDF under 1 MB at All on A1 | `wall-A1.pdf` = 40 KB (headless Chromium, proven) | pass |
| 10× several sheets | engineer: 130 sheets, 83–115 s for Chromium's PDF. My run had not finished after several minutes | soft warning added; Surbhi's trade-off |

**The seven dimensions: the impact analysis's claim against what I found**

| Dimension | `04` claimed | Found |
|---|---|---|
| Performance | neutral; about 15 KB of script | neutral for page views; script **+48.7 KB raw**, not 15 or 25 |
| Security | improves; "closes today's leak" on Ctrl+P | improves for the chart; **the list-view Ctrl+P route is still open (M1)** |
| Reliability | neutral | slightly worse: the hidden holder stays behind (m1); a missed `afterprint` plus leaving the panel prints the wrong document (m2) |
| Scalability | neutral, one watched risk | as claimed: 10× several sheets is slow, with a soft warning |
| Maintainability | degrades slightly | as claimed: one block with its own prefix, a second small drawing, checked by the ported 064 line rule |
| Data integrity | neutral | as claimed: writes nothing. The layout is not refreshed if rows reload while the panel is open (edge case, inferred) |
| Compliance / privacy | improves; new paper exposure by design | as claimed for the wall chart and HR copy; M1 stays open |

## Compliance verification

| Obligation | Mechanism in the diff | Test | State |
|---|---|---|---|
| PRIV-1 allowed fields | `posWallCopy` builds a fresh object with named keys only; the drawing never sees a row | `check_wall_chart.js` AC-27a, 27b, 28 (CI) | discharged |
| PRIV-2 file name, footer, metadata | `document.title` pattern; footer without user; Chrome writes no Author | jsdom AC-38, 41, 61; headless PDF Title | discharged (manual Edge check open) |
| PRIV-3 staff told | release note | — | release-time, open (C1) |
| PRIV-4 HR copy gate and banner | `posWallMayHr`; tick reset on open; banner and footer tag on every sheet | jsdom AC-58, 60, 63, 65, manager run | discharged (`01c` text out of date, m4) |
| SEC-1 nothing leaves the page | no fetch, storage or window | jsdom traps | discharged |
| SEC-2 button follows the page | `posLoad` shows it only with rows | jsdom; AC-51 not run | partial |
| SEC-3 Ctrl+P safe | one CSS rule; `posPrintHead` without the printer's name | tree check and browser check | **partial: chart view only (M1)** |
| SEC-4 page size only for its own print | `<style>` at the end of `body`, removed on `afterprint` and on close | jsdom; browser A4 back afterwards | discharged (m2 edge case) |
| 065 plans never print | not in the allowed keys | sentinel `PLAN-SNTL` | discharged |

## What to delete

Nothing significant. The two-drawing layout earns its 80 lines: trying every wrap took 2.3 s at DTC in my run, against 169 ms for two drawings. The shared fixture, the paper tokens and the phone rules are each needed by a check or a requirement. Small duplications could go, but I would not reopen the code for them: `POS_WALL_ORDER` repeats the keys of `POS_WALL_PAPER`, and the tree is walked three times (`posWallBelow`, `posWallCount`, `posWallDepth`). The non-CI `check_wall_chart_browser.js` (343 lines) will drift unless someone runs it at each Positions change. Keep it, but say in the notes when it must be run.

## What was done well

- **The paper never receives a row.** The copy is built key by key. The two sentinel runs prove it with the tick off and on, and the HR keys do not exist at all when the tick is off.
- **The HR-only gate reuses a signal the server already decides** (`unseated` present). No new role check and no server change. The gate is applied in `posWallCopy` as well as on the tick, so it holds even if the tick is forced on.
- **Measure once, work out every wrap, draw once.** It was proven equal to the full search at DTC and at 10×, with the timings recorded.
- **The page size goes in mm, at the end of `body`.** This was found by actually making PDFs, not by assuming.

## Confidence

- **Proven:** everything marked proven above, from my own runs on 25 Oct 2026.
- **Reported, not seen by me:** AC-3 / AC-3a in a real browser, AC-5 / AC-6 on a phone, and the AC-29 mutation runs.
- **Not checked:** any interactive print window, Safari, iOS, Firefox; which browsers skip `afterprint`; AC-51 on a site; DTC's real role list (C2) and the Owner's roles. To check these I would need a running site with DTC-like users and a real iPhone.

## Subtract pass on this review

Removed three things I could not turn into a failure scenario:
- a worry that `window.print()` called from a timer (print pressed while the size was still being worked out) is blocked on Safari — I could not check it;
- seats in a reporting loop being left off the paper — this is the spec's agreed behaviour;
- the screenshot `paper-All.png` showing other page text over the paper — it is a screenshot artifact; the PDFs are clean.

---

## Second look — 25 Oct 2026 (fixes `f4d4fe31`, `bf13049e`, `e42e5c48`)

**Verdict: SHIP WITH FIXES.** Every finding I was asked to re-check is fixed, and I could not break any of them in Chromium. Nothing stopped working. What is left is small: the list view still prints an "Open" column and "Nobody in this seat" (one spec line bans "open"), and the manual release checks from M2 are still not done. Neither is personal data. Pushing to dev is still Surbhi's call.

**Incoming work:** none. `origin/dev` is still `6aaf9ffd`. The three new commits are by the same author, in a straight line, with no merges. No Python changed.

### What I ran (all proven, run by me today)

| Check | Result |
|---|---|
| `node scripts/run_dom_tests.js` (`NODE_PATH` = the worktree's `node_modules`) | **13 run, 0 not run, 0 failed.** Wall chart 179 checks (171 + 8 new), Positions tree 168 |
| `python scripts/check_app_integrity.py` | 798 checks, OK (doctype-shadowing part skipped: no bench) |
| `check_wall_chart_browser.js`, in full (Playwright 1.64 driving the installed Chromium headless shell 1223) | **All passed, exit 0**, including the 10× stage. This time I saw AC-3, AC-3a, AC-5, AC-6, and the new M1 and m3 checks pass myself |
| My own Chromium probes (scratchpad, no source edited) | Below |

### Each finding, re-checked

| Finding | State | How I tried to break it |
|---|---|---|
| **M1 / F1** list view Ctrl+P | **Fixed** (proven) | DTC fixture, "As a list", print media. In the printed text: "leaving" 0, "Notice period" 0, "key seat" 0, "Frozen" 0, "covering" 0, "%" 0. Names, titles, branches and departments still print. The fix is one CSS rule plus two class names (`panels.css:2178`, `portal.js:587, 632-637, 652-653, 662`). `posCells` has one caller, so no other view is affected |
| **F2** "somebody is leaving" / "Only key seats" | **Fixed** (proven, with a synthetic `beforeprint`) | Through the tiles (`posShowOnly`) in the list view, and through the dropdown with a Branch filter as well. After `beforeprint` the Show filter is empty, all 90 rows (or the whole chart) print, the header says only "Branch: Ambala", and the Branch filter is kept. "Only seats with a vacancy" is left alone, as it should be. **Inferred, not checked:** that a real Ctrl+P paints the changes made in `beforeprint`. That is what the event is for, and Chromium's own PDF path fires it (I saw `afterprint` fire from `page.pdf`) |
| **m1** hidden drawing left in the page | **Fixed** (proven) | Opened the panel, chose All levels, left Positions with it open. No `#pos-wall-print` in the page. The finances panel printed **2 pages, same as before** (it was 3) |
| **m2 / F3** `afterprint` never fires | **Fixed** (proven) | HR copy on, `print` stubbed, no `afterprint`, moved to finances, sent `beforeprint`: the class, the mm page size, the holder and the "HR copy -" title were all gone. The finances PDF was 2 pages with no "HR use only" text. On Positions itself the wall chart's own print is kept, as it should be |
| Payslip and Team notes Ctrl+P | **Not affected** (proven by reading) | `printNote` and `printTeamNotes` (`portal.js:9360-9390`) print in a new window, so this page's print state never reaches them. A Ctrl+P on the payslip drawer is the same page, so it is covered by the m2 fix above |
| **m3** "Sheet k of n" cut on portrait A4 | **Fixed** (proven) | Portrait A4, 6 HR sheets, with DTC's name and again with a two-company name. The footer now starts "HR use only - not for display · Sheet 1 of 6 (row 1, column 1) · …" and wraps onto 2 lines. A 4× screenshot shows the first line whole. Note: the 2 lines are 30.4 px of text in a 26.5 px box. The extra 3.3 px is the empty space above the capitals, so nothing shows as cut. A third line would hide the sheet label. That needs about twice today's footer length, so I am not raising it |
| HR-only gate | **Intact** (proven) | `posWallMayHr` and `posWallCopy` have not changed since `f4d4fe31`. The manager fixture still gets no tick and no HR keys (CI) |

### New, from this look

**n1 · P3 — The list view still prints an "OPEN" column and "Nobody in this seat".**
- **What happens:** HR uses "As a list" and presses Ctrl+P. The paper has an OPEN column with the vacancy counts. Five seats read "Nobody in this seat".
- **Proof:** my probe's printed text.
- **Why it matters:** spec §7 (line 297-298) says nobody may put "to fill" or "open" on paper from Ctrl+P. AC-19 bans "Nobody in this seat" on the wall chart.
- **How serious:** this is not personal data, and the wall chart shows vacancies as "Vacant" anyway. So it is P3, not P1.
- **Smallest fix:** add the class `pos-leave-col` (or a new one) to the Open `th`/`td`. Or ask Surbhi whether the list view is covered by this line at all.
- **Also:** the "Change" and "and N more" buttons print on the list. That is polish (P4).

**n2 · P3 — Ctrl+P now changes HR's screen without saying so.**
- **What happens:** if HR has "somebody is leaving" or "key seats" chosen, Ctrl+P clears that filter. It stays cleared after the print, with no message.
- **Why it matters:** it is safe. But it is not the fix 06b suggested (leave "Show" out of the header and print the faded boxes at full strength), and Surbhi has not seen it. "Only key seats" was added beyond F2. That is consistent with the ban on "key seat", but nobody asked for it.
- **Question (should know):** is clearing the filter on screen acceptable to Surbhi? If not, a short toast is the smallest addition.

**n3 · P4 — After the m2 cleanup, "Open print preview" does nothing until a choice changes.**
- **What happens:** `afterprint` never fires → HR leaves Positions with the panel open → prints elsewhere → comes back. Clicking the button does nothing (proven: 0 prints after 1.5 s). The cleanup emptied the layout, and only a change of choice redraws it.
- **How to get out of it:** closing and reopening the panel, or changing any choice, fixes it.
- **Smallest fix:** in `posWallPrint`, call `posWallChange()` instead of just setting `printNext` when `w.key` is empty.

### Still open from the first look

- **M2** (P2): the manual checks AC-42 (Chrome and Edge print window, then a payslip), AC-43 (iPhone Safari) and AC-51 (needs a site). Also Surbhi's yes on PD-1, PD-4 and D-4/5/6.
- **m4**: spec AC-58 and AC-65, and `01c` PRIV-4, still describe the old HR-copy rule. The 20-sheet warning has no AC.
- **m5**: the Owner question.

None of these were in scope for this round.

### Over-engineering in the fixes

None. Each fix is the smallest one named in the review: two class names and one CSS selector, one line that removes the holder, one `beforeprint` listener inside the existing wire-up guard, and the footer reordered. Nothing to delete.

### Confidence

- **Proven:** everything marked proven above.
- **Inferred:** that real Ctrl+P paints the `beforeprint` changes.
- **Not checked:** the print windows of Edge, Firefox and Safari; which browsers skip `afterprint`, and whether they skip `beforeprint` too (if they do, m2's fix does not help them); a real site.

### Subtract pass

I removed two things:
- a worry about three-line footers, because the length needed is not realistic;
- a note on the test's `scrollHeight + 1` threshold. It passes at the boundary (27 against 26), but my screenshot shows nothing cut.
