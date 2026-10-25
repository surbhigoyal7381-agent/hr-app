---
slice: 069-wall-chart-print
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-10-24
status: revision 2 - updated to Surbhi's decisions of 24 Oct 2026 and the functional spec (03, Q12, Q13)
inputs: [01-product-brief.md rev 4 + "Decisions 24 Oct 2026" + "Decisions 24 Oct 2026 (2)", 03-functional-spec.md rev 2, 02-design.md, prototype-v1.html (approved), portal.js, panels.css, hrms/hrms/alvoraa_org_structure/register.py, slice 065 branch, slice 066 01c, security-compliance-baseline.md]
---

# 069 · Security and privacy requirements: the wall chart PDF

**I recommend. Surbhi decides.** I wrote these requirements, so the security review at `06` needs a
second reader for any part I also check (lesson 6).

**What changed in revision 2** (all from Surbhi's decisions of 24 Oct 2026, as relayed by the lead
session and written into `03`):
- PRIV-1: the allowed list now includes **designation and department** (and branch). Employee ID and
  grade stay forbidden. The sentinel test runs **twice**: HR copy off and HR copy on.
- SEC-3: test (a) checks the **Positions code only**. The Team notes prints (`portal.js:8754`,
  `:8775`) are out of scope (spec Q12: agreed). The "hide the screen chart" option is gone: Ctrl+P
  prints the screen chart with flags hidden.
- New **PRIV-4**: the "HR copy: show replacements" tick.
- PRIV-2: file name may start "HR copy - "; date format `2026-10-24`.
- R1 and R2 accepted by Surbhi, 24 Oct 2026. New R5 for the HR copy. Three counsel questions added.

## 0 · Bad news first

1. **The HR copy puts leaving dates on paper.** Paper cannot be taken back or erased. The guards are
   the tick (off every time), the gate (only readers whose page already holds leaving dates), and a
   banner on every sheet. **The banner is a label, not a control.** A careless HR person can still pin
   an HR copy on a wall, and nothing in the product can stop or detect that (R5).
2. **The brief was wrong that IDs and grade "are never sent to the chart".** They are.
   `position_table` sends every Positions reader each person's employee ID (`register.py:308`) and
   each seat's grade (`register.py:374`). HR also gets leaving dates (`:336-350`), the "in no seat"
   list, and, once slice 065 lands, replacement plans. So the print is safe only because it **copies
   an allowed list of fields** (PRIV-1). *Verified in code.*
3. **`may_see_leaving` is not the same as "HR".** It is true for HR and leadership, and also for a
   person's reporting line, who then gets leaving dates for their own line only (`register.py:336-347`).
   If a tenant ever gives a manager Read on Positions, that manager gets the HR copy tick for their
   own line. That is consistent (the paper never shows more than their screen), but it means "HR copy"
   is a name, not a role check. *Verified in code.*
4. **Edge ignores `A2`, `A1` and `A0` as page-size words.** Sizes in millimetres work (SEC-4).
   *Verified by running it* (Edge 155 headless; the interactive window still needs AC-42).
5. **Nobody will know who printed the company chart, or an HR copy.** No server log exists.
   Accepted by Surbhi (R1).

## 1 · What I checked

| Check | Result | Label |
|---|---|---|
| Who may open Positions | Frappe Read on `Alvoraa Position` (`register.py:68-72`); refused otherwise (`:264-265`). Shipped to HR Manager and System Manager only (`alvoraa_position.json`) | Verified in code |
| Rows on the page | One unfiltered fetch of `position_table`, scoped by company and branch on the server (`portal.js:327`, `register.py:267-278`) | Verified in code |
| Leaving dates | Sent only when `_may_see_who_is_leaving()` is true, and then only for the reader's reporting line unless they are HR or leadership (`register.py:335-350`). `may_see_leaving` returned at `:435` | Verified in code |
| Openings | `opening` is the Job Opening ID, sent to every Positions reader (`register.py:388`) | Verified in code |
| Other `window.print()` calls | Old Print button `portal.js:1212`. Team notes `printNote` (`:8746-8757`) and `printTeamNotes` (`:8759-8777`) open their own window and print manager notes. Not Positions, not this slice | Verified in code |
| Today's print | Prints "printed by {name}" (`portal.js:1291-1299`), the HR box, leaving flags and tags | Verified in code |
| Global `@page` | `panels.css:2154` sets A4 landscape for every print | Verified in code |
| Slice 065 plan keys | Sent only to plan readers; absent for everyone else. Tests `test_replacement_plan_065.py:830`, `:857` on branch `slice/065-plan-a-replacement`. **Not merged here yet** | Verified in code (on the branch) |
| PDF metadata from Edge | `/Title` = page title; no `/Author` | Verified by running it (headless) |
| DTC's role rows, DTC's real data | **I could not check that.** It needs read access to the DTC site's Role Permissions for `Alvoraa Position`, run by someone allowed to | Unknown |

## 2 · Threat model, four lines

1. **Who wants it, cheapest way:** a departing HR person wanting a staff list; a visitor reading the
   wall; a staff member reading an HR copy left on a desk or pinned up by mistake.
2. **Blast radius of one mistake:** one tenant. A wall copy with leaked fields, or a mishandled HR
   copy, shows every leaver's date to the people around them. Cross-tenant: none - no server code.
3. **What is new:** a durable, readable paper copy of the company's names and titles, seen by people
   with no login; and an HR paper copy of who is leaving and which seats are advertised.
4. **How we would find out:** a staff member sees their own leaving date on paper. So the prevention
   must be structural (PRIV-1, PRIV-4) and proved in CI, because detection is a complaint.

## 3 · Data inventory

| On the paper | Class | Purpose | Retention | Who may see |
|---|---|---|---|---|
| Person's name | Personal, directory level | Show who sits where | Paper: until replaced; DTC's choice (Q6). The "as at" date shows age | Anyone at the wall |
| Seat title, designation, branch, department | Organisational; personal once next to a name | Same | Same | Same |
| Counts, "Vacant", company, scope words, date, sheet label | Not personal | Read the chart | Same | Same |
| **HR copy only:** "leaving {d Mon}" after a name | Sensitive (private news, often unannounced) | HR plans which seats to fill | Paper: DTC's choice, **unconfirmed** (Q5, Q6) | HR in the office only |
| **HR copy only:** "Job opening raised" | Internal | Same | Same | Same |

No new field, no new store, no new server data.

## 4 · Who must NOT see what (on the paper)

**Never printed, on any copy, for any reader, by the panel or by Ctrl+P:** employee ID, assignment
name, grade, `hired_on`, assignment type, weight, "covering", "key seat", "Frozen", "%", "to fill",
"open"; the "No reporting manager" box; the "In no seat" list; anything `.private` or
`[data-private]`; the Job Opening's ID; **065 plan data of any kind** (mark, note, reason, who set
it); 066 grooming marks; photos and initials; the printing user's name or role.

**Wall copy (HR copy off) also never prints:** a leaving date, "Job opening raised", the banner.

**HR copy adds only:** "leaving {d Mon}" after a name, "Job opening raised" on a seat, and the banner
"HR use only - not for display".

## 5 · Obligations engaged

| Obligation | What it needs here | Checked |
|---|---|---|
| DPDP Act 2023 - names, titles and leaving dates are personal data; DTC is the Data Fiduciary for its staff `[ASSUMPTION]` our role is processor | Minimisation: wall copy prints names and job facts only (PRIV-1); leaving dates only on a marked HR copy for readers who already see them (PRIV-4). Notice before names go on a wall (PRIV-3) | Baseline §2, verified 24 Aug 2026 (61 days, fresh). Notice and consent duties take effect around 14 May 2027 (secondary source, checked 24 Oct 2026) |
| DPDP s.7(i), "legitimate uses" for employment | Likely basis for a staff chart and an HR working copy. **I am not a lawyer.** I read law-firm summaries only, not the Gazette text: **Unknown** at primary level | Bar & Bench, JSA summaries, checked 24 Oct 2026 |
| Counsel's retention rules (18 Sep 2026, memory note) | Performance records are erased after employment + 6 months, and there is no "keep for ever". This is why 065 plans never print: paper cannot be erased | Project note dated 18 Sep 2026; not re-read against counsel's letter, **Unknown** at source |
| CERT-In, ISO, GDPR, AI Act | Not engaged: no new system, log, transfer or automated decision | - |

## 6 · Abuse cases

| Who | What they try | What stops it |
|---|---|---|
| Curious colleague, employee | Print the chart | No Read on Positions, so no page and no button. Server refuses `position_table` (SEC-2) |
| Head of department | Print their team or the company | Same. Holds only while no HOD role has Read on `Alvoraa Position` (switch-on check C2) |
| Owner at DTC, branch-tied | Print the whole company | Rows scoped to his branch on the server; the print uses those rows only (SEC-1) |
| Reader without leaving dates | Get an HR copy | No tick in the DOM; the copy never holds `leaving` (PRIV-4) |
| HR printing for the wall | Print leaving dates by mistake | Tick off every open; allowed-field copy (PRIV-1); Ctrl+P safe too (SEC-3) |
| HR with an HR copy | Pin it on a wall, or send it to a print shop | **Not prevented.** Banner on every sheet, "HR copy -" file name, office-print note. Residual R5 |
| Departing HR person, valid session | Print the whole company, or an HR copy, to take away | Not prevented, not detected. Same data they can screenshot today. Residual R1 |
| Guest | Call the endpoint | `position_table` is not guest-allowed and checks Read first (`register.py:256-265`) |
| Visitor at the wall | Read names and titles | Intended. Only allowed fields are there (PRIV-1); staff told first (PRIV-3) |

## 7 · Requirements

Each says what must be true and how it is tested. The spec's acceptance criteria are the test target.

**SEC-1 · The print uses only the rows already on the page. No new endpoint, and nothing leaves the
page except through the browser's print window.**
No new `@frappe.whitelist`; no `gpFetch`/`frappe.call`/`fetch`, `window.open`,
`URL.createObjectURL` or storage write from the wall chart code; choices not remembered.
*Test:* jsdom in the CI DOM suite (`scripts/run_dom_tests.js`) replaces those functions with ones that
fail the test, opens the panel, changes every choice **including both ticks**, and runs "Open print
preview". Review check at `06`: the diff adds no Python.

**SEC-2 · The Download button shows exactly when the Positions page shows rows. No new role, no new
permission.**
The gate is the page's own: Frappe Read on `Alvoraa Position`, checked on the server. A button gate in
the browser is not a control, so this slice adds none.
*Test:* (a) jsdom: `rows: []` gives no button; rows give one. (b) The existing refusal of
`position_table` without Read (slice 064 SEC-8) still passes. (c) Switch-on check C2.

**SEC-3 · The old Print button is gone, and a browser print of the Positions screen shows the chart
with no flag, tag, HR box or "printed by".**
Remove the button at `portal.js:1212`. One CSS rule in the Positions print block hides `.oc-flag`,
`.oc-tag`, `.pos-nomgr-row`, `.private` and `[data-private]`. The screen chart itself stays visible in
print (Surbhi, Q15: Ctrl+P prints the screen chart). `posPrintHead` drops "printed by {name} ({role})".
*Test:* (a) static, DOM suite, **Positions code only** (`posLoad` to `ocPaint`): no
`onclick="window.print()"` and exactly one `window.print()` call, inside the wall chart's print
function. The Team notes prints at `portal.js:8754` and `:8775` are outside this check: they print
manager notes in their own window, not Positions (spec AC-2, Q12 agreed). (b) Playwright
(`check_positions_connectors.js`, print media) on a seeded site with a leaver, a key seat, a covering
person and a person with no manager: seat titles and names visible; visible count of the five
selectors = 0 (AC-3). (c) With `#sb-name` = `PRINTER-SNTL`, the print head holds neither sentinel nor
"printed by" (AC-3a).

**SEC-4 · The wall chart's page size lives only for its own print.**
One `<style>` with `@page{size:{w}mm {h}mm;margin:10mm}` (millimetres, never `A1`), added after the
global rule just before `window.print()`. Removed, and `document.title` restored, on `afterprint`
**and** when the panel closes. The global A4 rule stays (D10).
*Test:* AC-37, AC-39 in jsdom; manual: print A1, then a payslip in the same tab, payslip unchanged.

**PRIV-1 · The paper carries only allowed fields. This is the CI guard that stops removed data coming
back.**
One function builds the print copy. Each seat in it holds only: `title`, `designation` (printed only
when it differs from the title), `branch`, `department`, `names` (each the person's `name` only),
`vacant`, `below`, `kids`; and, **only when the HR copy tick is on**, `names[].leaving` and `opening`
turned into true/false (the Job Opening ID is never copied). With the tick off, those two keys do not
exist in the copy. The renderer never receives a row or person object and never calls `ocAvatar`.
Employee ID and grade are **not** allowed on any copy.
*Test (blocking, CI DOM suite):* the spec's sentinel payload (`F-DTC90` with every sensitive key
filled: `EMP-SNTL`, `ASG-SNTL`, `GRADE-SNTL`, `HIRED-SNTL`, `TYPE-SNTL`, `OPEN-SNTL`, `IMG-SNTL`,
`plan:{note:"PLAN-SNTL", set_by:"WHO-SNTL", reason:"REASON-SNTL"}`, `plans`, `UNSEATED-SNTL`,
`PRINTER-SNTL`, `covering`, `key`, `status:"Frozen"`, leaving dates `2099-01-01` and `2026-11-30`;
plus `designation:"DESIG-OK"`, `department:"DEPT-OK"`), "All" from the top, run **twice**:
- **Tick off (AC-27a):** no sentinel string, no `2099`, no "leaving", no "1 Jan", no "30 Nov", no
  "Job opening", no "HR use only", no `Frozen`, no "covering", no `<img`, none of `.oc-flag`,
  `.oc-tag`, `.oc-toggle`, `.av`, `.pos-nomgr`, `.private`, `[data-private]`. `DESIG-OK` and `DEPT-OK`
  **do** appear. Printed names = people in seats in scope (363).
- **Tick on (AC-27b):** the HR copy words appear as PRIV-4 allows; still no sentinel string (so never
  `OPEN-SNTL`, `PLAN-SNTL`, `WHO-SNTL`, `REASON-SNTL`), no `2099` as a raw value, no `Frozen`, no
  "covering", no `<img`, none of the listed elements.
- **Key check (AC-28):** every seat in the copy has exactly the keys for the mode in use.
- **The guard is shown to fail (AC-29):** copying `employee` in on purpose makes all three fail;
  recorded in `04-test-report.md`, then undone.
*Observability (lesson 1):* this proves the control only because the fixture carries leavers, an
opening, a plan and a key seat. DTC has 0 future leavers today, so real data would show "0 leaks" and
prove nothing.

**PRIV-2 · The file name, footer and PDF metadata name nobody.**
File name = `document.title` = `Wall chart - {Company} - {n levels | all levels} - {paper} - {date}`,
or with the HR copy on, the same with `HR copy - ` in front. The date is the server's `as_at`, written
`2026-10-24`. No person's name, no seat title, no user. Footer has no "printed by".
*Test:* (a) jsdom, same fixture: during print the title matches
`^(HR copy - )?Wall chart - .+ - (\d+ levels|all levels) - A[0-4] - \d{4}-\d{2}-\d{2}$`; the prefix
is present if and only if the tick is on; no fixture person name and not `PRINTER-SNTL` in the title
or footer (AC-38, AC-61). (b) Manual, Chrome and Edge: saved PDF's Title = file name, no Author.

**PRIV-3 · Staff are told before their names go on a wall.**
Not code. The release note to DTC carries this HR note, and DTC confirms it in writing:
> *"We are putting up a chart of seats and names, showing your name, job title and department.
> Visitors to the office may see it. It never shows leaving dates, pay or personal details. If you
> have a reason not to be named on it, tell HR before {date}. Old copies are taken down when a new
> one goes up."*
*Test:* review check at release: the note is in the release note, and DTC's written confirmation is
filed with the slice. **I am not a lawyer**: Q1 asks whether this is enough.

**PRIV-4 · The "HR copy: show replacements" tick shows only to readers whose page already holds
leaving dates, starts off every time, marks every sheet, and never prints plan data.**
- The tick exists in the DOM only when the server sent `may_see_leaving: true`. For anyone else it is
  absent, not hidden. No role check of our own: the server is the control.
- Unticked every time the panel opens, even after it was ticked and the panel reopened on the same
  page visit. Not remembered (SEC-1).
- When on: "HR use only - not for display" at the top (at least 9 pt bold) and at the start of the
  footer of **every** sheet; file name starts `HR copy - `; the panel says "Print in the office, not
  at a print shop."
- Adds only "leaving {d Mon}" and "Job opening raised". **Slice 065 plan data never prints, on any
  copy, in any form**, unless counsel says yes in writing and this requirement is changed. "Covering"
  stays off (spec Q17).
*Test (blocking, CI DOM suite):*
(a) **Never for non-readers (AC-65):** `F-NOLEAVE` (`may_see_leaving: false`): no HR copy checkbox in
the DOM, no office note, and the print DOM is identical to the tick-off print. A second run with a
`leaving:"2099-01-01"` value forced into that fixture still prints no "leaving" and no "1 Jan".
(b) **Off every open (AC-58):** tick it, close, reopen: unticked.
(c) **Banner on every sheet (AC-60, AC-63):** one sheet and several sheets; with the tick off the
words appear nowhere.
(d) **Plans never print:** covered by PRIV-1's tick-on run (`PLAN-SNTL`, `WHO-SNTL`, `REASON-SNTL`
absent). Merge check C3 keeps the `plan` keys in the fixture when 065 lands.
(e) **Office note (AC-62)** present only with the tick on.

## 8 · Questions

| # | Question | For | Blocks | Default meanwhile |
|---|---|---|---|---|
| Q1 | **Must know.** Names, job titles and departments on a wall that visitors can see: is that covered by DTC's employment basis (DPDP s.7(i)) with the PRIV-3 note, or does it need more (consent, an opt-out)? | Counsel, via Surbhi | Switch-on at DTC, not the build | Do not hand the feature to DTC until answered |
| Q4 | **Must know.** A paper copy of an HR-only screen (leaving dates, open roles): may HR make one at all, and on what conditions (who may hold it, where it may be kept)? Leaving dates are often not yet announced | Counsel, via Surbhi | Switching on the HR copy tick at DTC | Build it; tell DTC not to use the HR copy until answered |
| Q5 | **Must know.** How long may printed copies be kept, and how must they be destroyed? Wall copy and HR copy separately. Our erasure promises (065, counsel's 18 Sep rules) cannot reach paper | Counsel, via Surbhi | Release note wording to DTC | Release note says: wall copy taken down when replaced; HR copy shredded once the leaving dates on it have passed |
| Q2 | **Should know.** If someone asks not to be named, how does HR leave them off? No per-person opt-out in the build | Surbhi | Nothing now | HR handles requests by hand |
| Q3 | **Should know.** Frozen seats print without the word "Frozen" | Analyst | Closed by spec §7 | As written |
| Q6 | **Should know.** Does DTC have its own rule for destroying printed HR papers? | Surbhi, asking DTC | Nothing in the build | Q5's default |

Q12 (spec): **agreed.** The Team notes prints are not Positions and stay out of SEC-3 test (a).
Q13 (spec): **done** in this revision.

## 9 · What blocks what

**Blocks the build** (must be in the spec and pass before `06` signs off): SEC-1, SEC-2, SEC-3,
SEC-4, PRIV-1, PRIV-2, PRIV-4. All in `portal.js`, `panels.css` and the DOM test suite. No counsel
needed to build.

**Blocks switch-on at DTC:**
- C1. PRIV-3 note in the release note, and DTC's written confirmation (Q1).
- C2. Someone with access lists the roles holding Read on `Alvoraa Position` at DTC. No HOD or
  employee role may be on it. *I could not check that.*
- C3. Merge order: when 065 lands, `test_replacement_plan_065.py:830` and `:857` still pass, and the
  PRIV-1 fixture still holds the `plan` keys.
- C4. HR copy at DTC: counsel's answers to Q4 and Q5, and the release note tells DTC how to keep and
  destroy HR copies.

## 10 · Residual risk

| # | Risk | Label | Owner | Accepted |
|---|---|---|---|---|
| R1 | Nobody can tell who printed the company chart or an HR copy, or when. A server log would need a new call the design rightly removed | Intentional trade-off | Surbhi | **Yes - Surbhi, 24 Oct 2026** (relayed by the lead session; spec Q7) |
| R2 | A leaver whose login and HR role were never removed can still open Positions: `may_view` checks the role only (`register.py:68-72`). Existing, not new; this slice makes the copy neater | Temporary debt - removed when offboarding disables the login or the role | Surbhi | **Yes - Surbhi, 24 Oct 2026** (relayed by the lead session; spec Q7) |
| R3 | The PDF sits in Downloads and goes to a print shop. Outside the product | Acceptable simplification - DTC's handling | DTC, via PRIV-3 | With Q1 |
| R4 | The global `@page` A4 rule still forces landscape on other portal prints (D10) | Intentional trade-off | Surbhi | 24 Oct 2026 (D10) |
| R5 | An HR copy with leaving dates is mishandled: pinned on a wall, left on a desk, sent to a print shop, kept after the people have left. The product cannot stop or see this | Intentional trade-off - the banner, file name and office note are labels only | Surbhi for the decision; DTC for handling | **Decision accepted by Surbhi, 24 Oct 2026** (brief "Decisions (2)" R3, as relayed; the brief's header still says "waiting" and its author should update it). Handling rules wait on Q4, Q5 |

## Subtract pass

**Removed in revision 2:** the "hide the screen chart in print" option in SEC-3 (Surbhi wants Ctrl+P
to print the chart); "covering" on the HR copy (spec Q17); a separate requirement for the HR copy's
file name (folded into PRIV-2); a separate test for "plans never print" (PRIV-1's tick-on run already
proves it); a diagonal watermark and a role check on the tick (the banner and the server's
`may_see_leaving` do the job).

**Still out from revision 1:** a print audit log (R1); a button-level permission check (SEC-2 says
why); a static check on which functions the renderer may call (the sentinel test proves the outcome).

**Kept:** eight requirements, each closing a path I could name with a file and line.
