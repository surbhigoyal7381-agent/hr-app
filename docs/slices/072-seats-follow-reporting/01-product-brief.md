---
slice: 072-seats-follow-reporting
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-10-24
status: draft - I recommend, you decide
inputs: [Surbhi 24 Oct 2026 ("Follow the reporting hierarchy. If people reporting to two different managers have the same role, show the position under both managers, with the different people in those seats."), 064 12-fix-cfo-reports-seats.md (read-only census of production DTC, 24 Oct), 064 10-old-design-improvements.md (connector rule), 069 01-product-brief.md rev 4 + decisions, code read in this worktree - register.py position_table, alvoraa_position_assignment.py, alvoraa_reporting_line.py, attendance_correction.py, hrms organizational_chart.py, portal.js ocNodeCard]
---

# 072 · Seats follow the reporting line

## Bad news first

1. **The chart and the Employee record disagree for 88 of 361 seated people at DTC.** The chart
   hangs a seat under one parent seat. The Employee record's "Reports To" says who the person's
   manager really is. Today the chart wins on screen, and the Employee record wins everywhere
   else: leave and attendance approvals, team views and appraisals all read "Reports To"
   (Confirmed: `attendance_correction.py` calls it "the single source of truth for who somebody's
   manager is"; `alvoraa_position_assignment.py` says `pms_cycle.py` routes reviews from it).
2. **64 of the 88 report to HR-EMP-00001, a "Backoffice Executive".** That looks like a default
   left over from an import, not a real team of 64. **If the chart follows "Reports To", it will
   faithfully draw that mistake.** Someone at DTC must confirm it first (Q2).
3. **A data fix alone goes stale.** Splitting seats (script Part B) fixes 12 people today. The
   next change to anyone's "Reports To", and the next new hire placed by the 064 hire hook, puts
   the chart out of step again. 164 people joined DTC in 60 days.
4. **No UX opportunities scan (`01a`) and no DevOps notes (`07` §1) exist for this slice.** I
   wrote the brief because you asked for it now. Neither should change much: no new app, worker
   or page.

## Recommendation in five lines

- **People follow "Reports To". Seats, counts and vacancies stay on the seat record.** (Option B.)
- In the **Reporting lines** view only, a seat whose people report to different managers is
  drawn **once per manager**: each copy hangs under that manager's seat and lists only that
  manager's people.
- The seat's own box (its "home", under its real parent seat) keeps the seat count, the open
  slots, the job opening and any child seats. Copies are always end boxes: nothing hangs below them.
- **Run script Part A** (5 seats, 6 people) on DTC anyway, so those seats' future vacancies
  appear in the right place. **Do not run Part B** if you choose Option B.
- No new DocType, no new field, no change to any Employee or seat record. New code in two files.

## 1 · What your rule means, in the product

My reading `[ASSUMPTION]`: "same role" means **one seat record holding people who report to
different managers**. Two different seats with the same title already show separately today.

Example, Office Executive (one seat, 6 slots, 6 people, parent: Owner):

| Today | With the rule |
|---|---|
| One box under the Owner, 6 names | Box under the Owner: 2 names, "6 seats in all" |
| Nobody under the CFO | Box under the CFO: 4 names, "Same seat as under Owner" |

The same mechanic covers a one-person seat: the Data Analyst (parent Owner, reports to the CFO)
shows under the CFO. Its home box under the Owner, now with nobody in it, no open slot and no
child seats, is not drawn, so it never says "Nobody in this seat" about a seat that is full.

**The connector rule still holds, with one change of meaning.** "No line may suggest a box reports
to anything but its real parent." For a box of people, the real parent is now **the seat their
manager sits in**. For the seat itself (its count, its vacancies, its child seats), it is still
`reports_to_position`. The 064 connector check must be taught this, or it will fail every copy.

## 2 · Which record drives the chart

| Thing on the chart | Follows | Why |
|---|---|---|
| A person's name | Employee "Reports To" | It is what approvals, appraisals and team views use. A chart that disagrees with your approvals is the bug |
| Seat count, "open" slots, job opening | The seat record, home box only | A vacancy has no person, so it has no "Reports To". It belongs to the seat's own parent |
| Child seats (Back Office's 10) | The seat record, home box only | Keeps one path to the top. A copy never has children, **so a copy can never make a loop** |
| Headcount | People, counted once | Copies split names, never add them. "363 in seats" stays 363 |
| By branch / By department views | Unchanged | They are not about reporting. One box per seat, as today |

**What stays the same, and why:** the seat record is not split, renamed or re-parented. Slice 065
replacement plans mark a **person** (064 I7: "a red flag before the person's name") `[needs
validation - 065 docs not in this worktree]`, so the mark travels with the person to their copy.
Job openings link to the seat (`Job Opening.alvoraa_position`), so they stay on the home box.

**Reversing it (make "Reports To" follow the seats) is a no.** The assignment code refuses it on
purpose: tidying a chart would silently move live appraisals and approvals.

## 3 · The edge cases, decided

| Case | What the chart does |
|---|---|
| Manager sits in no seat (84 unseated people exist) | The person stays in the home box, as today. No worse than now; the count is listed for HR in the release note |
| Manager sits in two seats | The copy hangs under the manager's Permanent seat with the highest weight |
| Manager's seat is outside what this reader may see (branch-limited reader) | Home box. Never draw a box that reveals a seat the reader cannot see |
| Manager has left / "Reports To" empty | Home box |
| Vacant slot in a seat split across two managers | Shown once, "1 open", on the home box only (Q3 if you want it per manager) |
| HR puts someone in a seat from a copy | They land in the seat record; the chart then places them by their own "Reports To". The dialog says so in one line |
| Same title already under that manager | Two boxes with one title side by side would confuse; the existing "identical seats grouped" rule must not merge a copy with a different seat. Test it |

## 4 · Three ways, and the cheaper rungs

| Rung | Option | Verdict |
|---|---|---|
| Already there | Frappe HR's own Organizational Chart draws people by "Reports To" (confirmed: `organizational_chart.py`) | **No** - no seats, no vacancies, 445 boxes. Not what you open Positions for |
| Data | **A. Split seats** - Part A + Part B, then extend B to the other 70 | Zero code. Meets the rule **today only**. Every split is a judgment about seat counts. Goes stale with the next "Reports To" change or hire. Kept as your fallback |
| Smaller than the rule | **C. A chip** on the seat: "4 here report to CFO" | Smallest code. Does not do what you asked ("show the position under both managers"). Fallback if you want the least code |
| New code | **B. Chart rule** (this brief) + Part A data fix | **Recommended.** Always true, because it reads "Reports To" every time the page opens. Nothing to keep in step |

**Effort for B:** `Evidence required` - the engineer sizes it. My guess `[ASSUMPTION]`: small to
medium. One extra field per person in `position_table` (whose seat their manager sits in, worked
out from data the page already loads plus one query for "Reports To"), and the copy-building step
in the Reporting lines view of `portal.js`. No server cost.

## 5 · Effect on what already exists

- **064 tests:** the connector check gains the new meaning of "real parent" and five cases: a split
  seat, a vacancy on the home box only, a hidden empty home box, a manager with no seat, a manager
  outside scope. Branch and department views must stay byte-for-byte the same.
- **069 wall chart:** prints what the screen draws, so copies print. Box count rises by about
  `Needs validation` (my guess 5-15 at DTC). The name count test stays "each person once"; the
  footer must count seat records, not boxes. 069's size estimates should be re-run.
- **The 82-84 unseated people:** not helped. The rule moves seated people; it does not seat anyone.
- **The other 70 mismatches:** fixed on screen automatically, **if** "Reports To" is right (Q2).
- **Part B script:** not needed under B. Running it as well does no harm but adds four seats nobody
  needs.

## 6 · Personas

| Persona | What changes |
|---|---|
| CXO / Owner | His chart matches who actually reports to whom. The CFO's box finally shows a team |
| HR Manager | Fixes a reporting line in one place (the Employee record) and the chart follows. No second hierarchy to maintain |
| CFO and other managers (if allowed into Positions) | See their own people under them |
| Employee | No change; employees do not open Positions |

## 7 · The WOW

The Owner opens the CFO's box. Under it: **"Office Executive · 4 people"** and, in small grey
text, **"Same seat as under Owner · 6 in all"**. The 12 who report to the CFO are where he expects
them, and nothing is counted twice.

## 8 · Kano and competitors

**Kano: proxy Must-be for DTC.** A chart that contradicts approvals breaks trust, and 069 will put
it on a wall. Evidence: seen - your request, 24 Oct; the 88-person census. In the market:
Performance `[recall - verify]`. Keka, Zoho People and HiBob draw the org chart from each person's
reporting manager; Darwinbox and Workday-style position management hang seats under parent seats
`[recall - verify]`. We do both: people by manager, vacancies by seat.

**What we will not do:** let a chart edit change anyone's manager.

## 9 · Privacy and NFR

- **Privacy:** neutral. Who reports to whom is already shown on the Organisation chart. The one
  rule: a copy must never reveal a seat outside the reader's scope (§3). No leaving dates or plans
  are added.
- **Performance:** one more query (from 7 to 8), about 360 rows at DTC. No cache. Fine at 10x.
- **Data integrity:** better. Read every time, so never stale.
- **Security, scalability, maintainability:** neutral; no new endpoint, no new record.

**Regulatory read.** 1) DPDP only, lightly: names and reporting lines are personal data. 2) The
duty is DTC's; a chart that agrees with their own records helps them. 3) Nothing new is collected
or shown. 4) Yes, we would defend it. I am not a lawyer.

**Thriving lens.** Engagement: the CFO's team is visible as his. Collaboration: people find the
right manager. Inclusiveness: the unseated 84 are still missing, as today. Transparency: shows the
real reporting line, nothing private.

## 10 · Success criteria

| Measure | Baseline | Target | How |
|---|---|---|---|
| Seated people drawn under their real manager's seat | 273 of 361 (88 wrong) | All whose manager sits in a visible seat | Census script in verify mode, before and after |
| People counted twice in a chart or print | 0 | 0 | Name-count test |
| False lines in the connector check | 0 | 0 | 064 check, with the new rule |
| HR edits needed after a "Reports To" change | 1 seat edit or split | 0 | Change one record on dev, reopen the chart |

## 11 · Risks

- **Bad "Reports To" data, drawn honestly** (the 64). Biggest risk. Q2.
- **A seat looks emptier at home.** Back Office's home box may fall from 36 names to a handful.
  Readers may think people left. The "N in all" text is there for that.
- **Mid-month manager change** moves a person between boxes the same day. That is the point, but
  HR should know.
- **Cheapest way to find out before building:** run the census on DTC grouped by "seat x manager"
  and show you the list of copies it would draw. Read-only, about an hour.

## Open questions (must know first)

| # | Question | Owner | Blocks | My recommendation |
|---|---|---|---|---|
| Q1 | Is the Employee "Reports To" the truth for who manages whom on the chart? | Surbhi | Option B | Yes |
| Q2 | Do 64 people really report to HR-EMP-00001? If not, who? | Surbhi with DTC HR | Release at DTC | Fix those records before release |
| Q3 | A vacancy in a shared seat: once, under the seat's own parent? Or one seat per manager so each has its own count (Part B)? | Surbhi | Vacancy display | Once, on the home box |
| Q4 | Run Part A on DTC now, and skip Part B? | Surbhi | The data fix | Yes and yes |
| Q5 | Copies print on the 069 wall chart? | Surbhi | 069 layout | Yes - print what the screen shows |

## Assumptions

- `[ASSUMPTION]` "Same role" means one seat record, not one designation across seats.
- `[ASSUMPTION]` 065 plans mark a person, not a seat. To be checked in 065's code before build.
- `[ASSUMPTION]` ERPNext refuses a loop in "Reports To" `[recall - verify]`. Copies have no
  children, so the chart cannot loop either way.
- `[ASSUMPTION]` The production counts are as of 24 Oct 2026.

## Kill criteria

- The read-only "seat x manager" preview shows most copies come from wrong "Reports To" data that
  DTC cannot fix soon. Then stop, run Part A only, and fix the records first.
- The connector check cannot be made to pass with copies. Then fall back to Option C, the chip.

## Subtract pass

Removed: a "seat disagrees" HR tile (the release note lists the count once), a per-copy vacancy
setting (Q3 answers it with no setting), copies in the branch and department views (not about
reporting), a person chart for the unseated (a different job), and a step that writes "Reports To"
from the seat (refused in §2).
