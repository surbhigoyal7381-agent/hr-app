---
slice: 064-organogram-improvements
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-10-21
status: draft
inputs: [Surbhi's message of 21 Oct 2026 (items 2, 5, 6, 7, 8), product-context.md, no-over-engineering.md, ux-learnings.md, handoff-contract.md, legal-retention-rules-2026-09 (memory), code read in this worktree - hrms/alvoraa_org_structure/*, alvoraa_portal/org_job_link.py, portal.js Positions and Organisation chart sections, positions.html, hrms job_opening / job_offer / employee_master / job_requisition / organizational_chart, hrms/performance_management/pms_talent_flag, hrms/pms/permissions.py]
---

# 064 · Organogram improvements — product brief

**I recommend. You decide.** Build, change or drop.

## Gate summary

1. **Bad news first: two inputs are missing.** There is no UX opportunities scan (`01a`) and no DevOps first look (`07` §1) for this slice. I wrote the brief anyway because you asked for it now. The UX designer and DevOps should still write theirs before the design step. Nothing in this brief adds an app, a worker or a public page, so I expect DevOps to have little to say.
2. **Bad news second: "collapse after the second level" is already in the code in this worktree** (`POS_OPEN_DEPTH = 2`, added after your 16 Oct note). I could not check whether it reached dtc.alvoraa.co. If it did, then "second level" means one level fewer than we built. Decision D1.
3. **Item 6, the answer: no.** A hired person does **not** appear in the seat by themselves today. Four of the five links exist. The missing one is Employee → seat. It is one small piece of code to add.
4. **Item 7, the answer: no, not for planning.** The only thing close is the performance module's "talent flag", which is tied to a review cycle and is HR-only. I do not recommend reusing it. Details in §3.
5. **I recommend splitting this into two slices, each complete on its own:**
   - **064 (this one):** a big chart that people can read and search, that tells the truth about who sits where, and fills in new hires by itself. Items 2, 5, 6 and part of 8.
   - **065 (next):** "plan a replacement" — open a vacancy before a seat empties, for someone who is leaving or someone HR thinks may leave. Item 7. It needs four privacy decisions from you first (D7 to D10).
6. **WOW:** a folded box never hides a problem. It says "14 seats below · 2 to fill · 1 leaving".
7. **Kano is a proxy.** No survey, no customer quotes. The only demand evidence is you, using DTC.
8. **Eleven decisions for you** (§11). Each has my recommended answer.

---

## 1 · Job to be done

**HR Manager at DTC:** *"When I open Positions to fix a seat or plan hiring, I want to find the seat in seconds and see where the holes are, without scrolling a chart of 90 seats and 476 people."*

**CXO / owner:** *"When I look at the organisation, I want the top of it on one screen, with the problems counted, so I know where to ask questions."*

**Department or branch head (if your tenant lets them open Positions):** *"I want to see my part, and know which of my seats are empty."*

| Persona | What changes for them |
|---|---|
| CXO | Sees the top two levels, with counts on every folded box. Nothing hidden without a number |
| HR Manager | Can search; sees every seat with no manager in one place; new hires land in their seat on their first day |
| Employee | No change on Positions (they do not open it). On the Organisation chart, a new joiner shows in the right seat on day one |

## 2 · Current pain

**No numbers, a story.** You opened Positions at DTC and found it too big to use. 90 seats, 476 active staff (figures from your message; I did not count them). At that size:

- The reporting view puts every seat that has no manager at the top, beside the real top seat. The first row gets wide and reads as if the company had several heads.
- There is no search on Positions. The Organisation chart has one, but the Positions page does not.
- A folded box shows only how many seats sit directly under it. It does not say that two of them are empty.
- A seat you advertised stays "Nobody in this seat" after the person joins, until someone puts them in by hand.

Three related bugs (1, 3 and 4) are with the engineer. They are not designed here. Where this brief touches them, I say so.

## 3 · The factual answers (items 6 and 7)

### Item 6 — does a hired person appear in the seat by themselves?

**No.** This is what links to what today (confirmed in code):

| Step | Link | Exists? |
|---|---|---|
| Seat → Job Opening | Custom field `alvoraa_position` on Job Opening (`org_job_link.py`). Set only when the opening is raised from Positions ("Advertise it"). **Read-only**, so an opening made by hand on the desk can never be linked | Partly |
| Job Opening → applicant | Frappe HR standard: `Job Applicant.job_title` | Yes |
| Applicant → Job Offer | Frappe HR standard: `Job Offer.job_applicant` | Yes |
| Job Offer → Employee | Frappe HR standard: "Create Employee" on the offer copies `job_applicant` onto the Employee. Saving the Employee marks the applicant and offer "Accepted" | Yes |
| Employee → seat (Position Assignment) | **Nothing.** No code creates the assignment | **No** |
| Opening closes when filled | Frappe HR closes an opening only on its closing date, not when it is filled. So a filled job can stay on the careers page | **No** |

**The ladder:**

| Rung | Option | Verdict |
|---|---|---|
| Already there | HR clicks "Put somebody in it" on the seat. Takes a minute | Works today, but it is the step people forget. That is your complaint |
| Configuration | Nothing in Frappe creates one record from another across these doctypes | Rejected — not possible |
| Customisation | Make the Job Opening's seat link editable (one property change on our own custom field) | **Recommended**, so hand-made openings can be linked too |
| Customisation | A Server Script on Employee | Rejected — the logic belongs in the repo, tested, beside the code it depends on |
| New code | One hook when an Employee is saved with a job applicant: follow applicant → opening → seat, and create a Permanent assignment at 100%, starting on the joining date | **Recommended** |

**How it should behave** (Recommendation):
- The assignment starts on the joining date. The existing rule already refuses an earlier date, so the person shows in the seat from their first day, not before.
- **If the seat is full on that day** (for example, a replacement who overlaps with the leaver), do not block the Employee save. Skip it and say so: "Ramesh Kumar was hired for Store Manager – Noida, but that seat is full until 30 Nov. Put him in from Positions when it frees up."
- If the opening has no seat linked, do nothing.
- Close the opening when the hires reach its vacancies — your decision, D6.

### Item 7 — can we mark a person as a flight risk, for planning?

**No, not in a form that suits planning.** What exists (confirmed in code):

| What | Where | Why it does not fit |
|---|---|---|
| **PMS Talent Flag** with types "At Risk" and "Retention Priority" | Performance module (`pms_talent_flag.json`). HR-only by permission hook. Shown only on the PMS steering page | It needs a **performance review cycle**. "At Risk" sits next to "PIP Candidate", so it reads as a performance judgement. You said "if not performance management, just for planning". It also never reaches the Positions chart |
| **Leaving** | Positions already shows "leaving 30 Nov" from the Employee's relieving date. Visible to HR, leadership and the person's own reporting line only (`register.py`) | Covers someone who **has** resigned, not someone who might |
| **Key position** tick | On the seat | Says the seat matters, not that its holder may go |
| Frappe HR: Staffing Plan, Job Requisition, Designation Skill, Employee Skill Map, Employee Grade | Standard | None records a risk of leaving. **Job Requisition** is useful, though: it is an internal "please let us hire" request with an approval status, which is not public |

Nothing anywhere in the repo is named flight risk, attrition risk or retention risk.

**And the vacancy part:** "Advertise it" appears only when a seat has room. A full seat whose holder is leaving cannot be advertised from Positions today, even though the server would allow it.

**What I recommend for slice 065** (Recommendation, not a decision):
- Call it **"Plan a replacement"**, not "flight risk". It is a note about a business need, written by a person. It is **not a score**. Nothing calculates it. No attendance, login or behaviour data feeds it — that would be passive monitoring, which product-context §6 refuses.
- It sits on the person's seat assignment: a tick, a short private reason, and the date it was set.
- **Only the HR Manager may set or see it.** Not the line manager, not peers, never the employee's own screens (D8).
- It **lapses after 90 days** unless HR confirms it again. A mark nobody revisits becomes a label. It is **erased, not hidden,** when the person leaves the seat (D9).
- A seat with a planned replacement, or someone leaving, gets **"Request a replacement"**. It makes an internal, unpublished request (D10). Nothing goes on the careers page until HR chooses.
- **Risk:** both places this could live keep a full change history. A cleared note would survive in that history unless it is purged. The security engineer must rule on this in `01c`.

## 4 · Competitive analysis — large org charts

Labels: **read (21 Oct 2026)** = a vendor or help page I read today. `[recall — verify]` = from memory. Nothing is **seen** in a live product.

| Capability | Frappe HR standard | Others | Label | Us today | Us after 064 |
|---|---|---|---|---|---|
| Fold and unfold | Desk "Organizational Chart": people, not seats; unfold on click; shows total people below | PeopleForce: click to show direct and all reports, click again to fold | Frappe: confirmed in code. PeopleForce: read | Folds below two levels of children | Same, depth per D1 |
| Search and jump to a person | Not in the desk chart | PeopleForce: search box plus filters; managers who do not match stay greyed | Frappe: confirmed. PeopleForce: read | Organisation chart only, not Positions | **Find on Positions**, opens the path and highlights |
| Counts on boxes | Total people below | PeopleForce: direct and total reports on each card | read | Direct seats only | **Seats below, to fill, leaving** |
| Department view | No | PeopleForce: a separate Departments tab with counts and heads | read | Branch and Department arrangements exist | No change |
| Open roles on the chart | No | ChartHop: shows open roles from its recruiting integration | read (third-party profile) | Empty seats and "to fill" shown | Hires fill the seat by themselves |
| Span of control | No | Not confirmed for anyone in my search | — | Organisation chart flags "too many reporting in" and "a layer of one" (`metrics.py`) | No change |
| Risk of leaving | No | Workday talent review: managers rate "retention risk" and "loss impact", hidden from the employee. SAP SuccessFactors: "Risk of Loss" and "Impact of Loss" icons on its succession org chart. Lattice: talent reviews assess "risk" | read | None | 065, HR-only, no score |
| Export to PDF | No | PeopleForce: PDF of the current view, with an option to anonymise | read | Desk report view of Alvoraa Position exports to Excel for HR Manager | No change |
| Scenario planning, drag to restructure | No | ChartHop: model changes on the chart with approvals | read | `effective_from` dates on seats | **Not doing** |
| Keka, Darwinbox, Zoho People, HiBob | — | Org charts with department filters and search are common in all four | `[recall — verify]`. My searches found no detail on their org chart features | — | — |

**What we will deliberately NOT do that others do:**
- **No numeric "flight risk score", no predicted attrition.** Workday sells retention-risk analytics. A predicted score about a named person is an automated judgement. It invites self-fulfilling treatment, and we cannot explain it in plain words. We keep a human note with an expiry date.
- **No drag-and-drop restructuring.** At DTC's size HR needs to find and fix seats, not model reorganisations.
- **No PDF of the whole chart.** A 90-seat tree on paper is unreadable. The list view and the desk export already answer "give me the data".
- **No second chart.** Positions and the Organisation chart already share one drawing. I will not add a third.

## 5 · Kano class and demand

All **proxy**. The only demand evidence is **seen**: your own use of DTC on 16 and 21 Oct.

| Feature | Class (proxy) | Why | What would change it |
|---|---|---|---|
| Fold by level | Must-be | Every chart above has it; its absence made DTC unusable | — |
| Search on Positions | Must-be | PeopleForce has it; our own Organisation chart has it | — |
| "No reporting manager" in one place | Performance | Better data hygiene, the more the better | DTC HR not fixing the seats it lists |
| Counts on folded boxes | Performance | PeopleForce shows total reports | — |
| Hire fills the seat by itself | Attractive | No one in my search closes this loop | DTC not using Frappe recruitment at all (evidence required) |
| Plan a replacement (065) | Attractive for HR and CXO; **Reverse** for employees if anyone else can see it | Enterprise products have it; mid-market rarely | A Kano question to DTC HR and two staff |

## 6 · Three ways to solve it

- **Conventional:** a new org chart screen with zoom, a mini-map, PDF export and a settings page for depth. Rejected — a second chart, a settings page, and a lot of new surface.
- **Better (proposed):** keep the one chart. Fold it to two levels, put counts on folded boxes, add Find, move managerless seats into one box, and close the hire loop with one hook.
- **Reimagined:** open Positions on the problems, not the chart: "3 seats with no manager · 7 to fill · 2 leaving", each a link that opens the path. The tiles above the chart already do half of this. I recommend the "better" version, and keeping the tiles as they are.
- **Could we not build it?** Partly. The fold already exists. The rest needs small code.

## 7 · Persona enhancements through the portal

No `01a` exists, so these are my own ideas, not the designer's.

| Persona | Idea | Job it serves | In 064? | Why |
|---|---|---|---|---|
| Employee | Sees themselves in the right seat on the Organisation chart from day one | "Where do I sit, who is my boss" | Yes (comes free with item 6) | No extra build |
| Frontline employee | Nothing | — | No | They do not use Positions |
| Line manager / branch head | "Reports above your view" stays separate from "No reporting manager" | Not mistaking scope for a data error | Yes | Otherwise every branch head sees a false alarm |
| HR Manager | Find, counts, managerless box, hires placed by themselves | Find and fix seats fast | Yes | The core of the slice |
| HR Manager | Plan a replacement | Start hiring before the seat empties | 065 | Needs privacy decisions |
| CXO | Top two levels with counts | The shape and the holes at a glance | Yes | The WOW |
| CXO | PDF export | Board pack | No | Unreadable at this size; list export exists |

## 8 · The WOW

On Positions, the reporting view opens folded. Under "Head of Operations — Vaneet Garg", the fold button reads:

> **+ 14 seats below · 2 to fill · 1 leaving**

Before, it said "+ 3": three direct seats, and nothing about the two holes further down. Now no problem is hidden by folding. The "leaving" count follows the same visibility rule as the "leaving" tag today. Someone who may not see who is leaving gets no leaving count.

*(This uses Vaneet Garg's branch as the example. It is also bug 3. If that branch is still missing, the engineer's fix comes first.)*

## 9 · Thin slice

**In 064 (needed to validate now):**
1. Fold the reporting view to the depth you choose in D1. Branch and department views already start folded.
2. **Counts on every folded box:** seats below, to fill, leaving.
3. **Find on Positions:** type a seat title or a person's name. It opens the path to the match and highlights it. Uses the data the page already loads, with no new server call.
4. **"No reporting manager":** in the reporting view, the top seat stays at the top (rule in D4). Every other seat with no parent goes into one box called "No reporting manager — 6 seats", with its own branch kept underneath. Seats whose manager is outside the reader's view are **not** put there. They keep "reports above your view".
5. **New hire placed in the seat** on their joining date (§3), and the Job Opening's seat link made editable.

**Needed before it can ship:** test at DTC's real size on a copy (90 seats); keyboard access to Find (ux-learnings rule).

**Worth doing later:** a count of active people who hold no seat at all — wait for the engineer's findings on bugs 3 and 4 first.

**Not doing:** PDF export, zoom or mini-map, drag-and-drop, span-of-control on Positions (it is on the Organisation chart), a depth setting, any change to `Employee.reports_to`, flight risk (→ 065).

**Rung:** new code (one hook, client changes) plus one customisation (a property on our own custom field). No new DocType, no new page, no setting.

## 10 · Success, risks, regulatory read

**Success measures**

| Measure | Baseline | Target | How measured |
|---|---|---|---|
| Time for DTC HR to find a named seat | Unknown — measure first, with a stopwatch, on today's page | Under 15 seconds | Three timed tasks with DTC HR, before and after |
| Seats at DTC with no reporting manager (other than the top) | Unknown — count on the DTC copy first | Halved within 30 days of release | Count of root seats, read weekly |
| Hires from a linked opening that land in their seat with no manual step | 0% (nothing does it) | 100% where the seat has room | Assignments created by the hook ÷ Employees created with a linked applicant |

**Risks (red team)**
- **DTC may not use Frappe recruitment at all.** Its staff were loaded from sheets. Then item 6 helps nobody there yet. *Evidence required:* the number of Job Openings and Job Offers on DTC. The cheapest check before building.
- **Wrong top seat.** If the "most seats below" rule picks the wrong root, the chart looks broken. D4 lets you name the rule.
- **10x data:** Find and counts run in the browser over rows already loaded. At 900 seats this should still be fast. DevOps should confirm.
- **Hire overlaps a leaver:** handled by skipping and telling HR (§3).
- **Employee created twice from one applicant, or applicant moved to another opening:** the hook must create at most one assignment per Employee. The analyst writes this as an acceptance criterion.
- **Support tickets likely:** "the new joiner is not in the seat" (seat was full, or opening not linked). The message in §3 must say exactly why.

**Regulatory read**
1. *Regime:* 064 — none new; it uses data already shown. 065 — DPDP (new personal data about a named employee).
2. *Whose obligation:* the employer's. 065 helps them meet it: HR-only, no score, expiry, erasure.
3. *What becomes possible:* 064 — an automatic record of who sits in a seat (same data HR types today). 065 — a written note that someone may leave, and a replacement request.
4. *Front page test:* 064 yes. 065 only with the limits in D8 and D9. "HR software secretly flags staff as flight risks" is the headline to avoid. I am not a lawyer. ⚠ COMPLIANCE for 065: counsel should confirm the note falls under the "employment + 6 months, then erase" rule, and whether an employee's access request must include it. Owner: Surbhi.

**Thriving-workplace lens**

| Lens | Answer |
|---|---|
| Engagement | A new joiner sees themselves in the right place on day one |
| Collaboration | HR and the CXO read the same counts on the same chart |
| Inclusiveness | Find and counts must work by keyboard and screen reader; counts are words, not colour only |
| Transparency | More structure is visible, but no new personal fact. The leaving count follows today's rule. 065's note is deliberately **not** transparent: it is private planning |

## 11 · Decisions only you can make

| # | Question | My recommended answer |
|---|---|---|
| D1 | "Collapse after the second level": show the top seat plus **one** layer, or the top seat plus **two** layers (what is built now)? | **Top seat plus one layer.** That is your words read literally. With counts on folded boxes, nothing is lost |
| D2 | Should Positions open as the chart ("As a structure") instead of the list? | **Yes.** The chart is what you call the organogram. (The engineer is looking at the related bug 1.) |
| D3 | "Anyone without a reporting manager": do you mean **seats** with no parent seat on Positions, or **people** with no manager on their Employee record? | **Seats on Positions** in this slice. People without a seat wait for the engineer's findings on bugs 3 and 4 |
| D4 | Which seat counts as the real top? | **The seat with the most seats under it.** No setting. All other parentless seats go in the "No reporting manager" box |
| D5 | Place a hire in the seat automatically on joining, or ask HR to confirm with one click? | **Automatically**, and tell HR clearly when it was skipped |
| D6 | Close the Job Opening when the seat is filled, so it leaves the careers page? | **Yes**, when hires reach the opening's vacancies |
| D7 | Is flight risk its own slice (065), or part of this one? | **Its own slice, 065.** It is a different outcome and needs D8 to D10 first |
| D8 | (065) Who may set and see a "plan a replacement" note? | **HR Manager only.** Not line managers. Never the employee's peers or the employee's own screens |
| D9 | (065) How long does it last? | **Lapses after 90 days unless confirmed. Erased when the person leaves the seat. Never longer than employment + 6 months** |
| D10 | (065) Should "Request a replacement" make a **public** advert, or an internal request first? | **Internal first** (Frappe HR's Job Requisition, or an unpublished opening). Nothing public until HR chooses |
| D11 | (065) What is it called on screen? | **"Plan a replacement"**, not "flight risk" |

## Open questions

| Question | Owner | Blocks |
|---|---|---|
| D1–D6 above | Surbhi | The design step for 064 |
| D7–D11 above | Surbhi | Starting slice 065 |
| How many Job Openings and Job Offers exist on DTC? | Engineer (read-only count) | Whether item 6 helps DTC now |
| Does the "fold to two levels" code already run on dtc.alvoraa.co? | Engineer | D1 — what "second level" means |
| Can a cleared 065 note be purged from the change history? | Security engineer, in 065's `01c` | Whether 065 is safe to build |
| Must an employee's data access request include a planning note? | Counsel, via Surbhi | 065 release |
| `01a` and `07` §1 for this slice | UX designer, DevOps | Design step |

## Assumptions

- `[ASSUMPTION]` DTC has about 90 seats and 476 active staff, as stated in the request. I did not count them.
- `[ASSUMPTION]` The code in this worktree matches what is on dev for the Positions page. I could not check what is deployed.
- `[ASSUMPTION]` Only HR, leadership and possibly branch heads open Positions; employees do not.
- `[ASSUMPTION]` Bugs 1, 3 and 4 are fixed by the engineer separately, and this slice builds on their fixes.
- `[ASSUMPTION]` Keka, Darwinbox, Zoho People and HiBob all offer search and department filters on their org charts. Not verified today.

## Kill criteria

- DTC HR, given the new chart, still cannot find a named seat in under 30 seconds. Then the problem is the data, not the chart. Stop and fix the data.
- The "No reporting manager" box holds more than half the seats at DTC. Then the reporting lines were never entered, and a box will not help. Stop and run the existing "Build it from your people" set-up instead.
- For item 6: DTC has no Job Openings and no plan to use them. Drop item 6 from 064 and keep the rest.

## Subtract pass

Removed on this pass: PDF export; span-of-control on Positions; a depth setting; a count of people without a seat (moved to "later"); a "problems-first" landing view (kept as the reimagined option only); flight risk (moved to 065). I kept closing the Job Opening (D6) because a filled job left on the careers page does visible harm.

## Handoff note

To the UX designer: the fold, the grouping of identical seats and the "reports above your view" note already exist. Design only Find, the counts on folded boxes and the "No reporting manager" box, and test them at 90 seats. Do not design bugs 1, 3 or 4. To the engineer: item 6 must never block an Employee save. Check how many Job Openings DTC has before building it.

---

Sources (read 21 Oct 2026):
- [PeopleForce — Explore your company's organizational chart](https://help.peopleforce.io/en/articles/9145094-explore-your-company-s-organizational-chart)
- [ChartHop — Headcount Planning](https://www.charthop.com/platform/headcount-planning)
- [Contrary Research — ChartHop](https://research.contrary.com/company/charthop)
- [Workday admin guide — Talent reviews](https://doc.workday.com/admin-guide/en-us/human-capital-management/talent/talent-reviews/dan1370796671425.html)
- [Workday talent review job aid (Texas A&M)](https://tamuserp2.wpengine.com/workdayservices/training/job_aid/complete-talent-review-manager/)
- [SAP KBA 2377769 — Talent flag icons on the Succession Org Chart](https://userapps.support.sap.com/sap/support/knowledge/en/2377769)
- [SAP Learning — Discovering the Succession Org Chart](https://learning.sap.com/courses/sap-successfactors-succession-management-administration/discovering-the-succession-org-chart)
- [Lattice — April 2024 product updates](https://lattice.com/blog/april-product-updates-enabling-a-comprehensive-talent-strategy)
- [HiBob — Nucleus Research report](https://www.hibob.com/analyst-recognition/nucleus-research-analyst-report-awards-hibob-accelerator-status-in-hcm-for-enterprise/)
