# Slice 064 — engineer findings on three Positions page bugs

Investigation only, 21 Oct 2026. No code changed, nothing committed, nothing written to
any server. DTC data was read with three read-only scripts on `dtc.alvoraa.co`
(counts, seat names and employee names only).

Code read: `origin/dev` at `76f15e1d` and `origin/main` at `a473c191`. Both hold the same
Positions code for everything below.

## The three answers first

1. **Bug 1 (Arrange by shows up late) — a code choice, not data.** The "Arrange by" box is
   hidden on purpose unless View is set to "As a structure". The page opens as a list, so
   the box only appears after you change the View dropdown, which sits in the same row as
   the filters. Fix: always show it.
2. **Bug 3 (Vaneet's branch is empty) — a data fault.** Vaneet's seat "Chief Finance
   Officer" has **no seats under it at all**. All 18 of his people sit in seats that report
   to the Owner seat (Vikas Garg), or to Samiron's seat. The chart is drawing the data
   correctly. The data went wrong on 16 Oct, when Vaneet was moved out of the Owner seat
   into a new CFO seat and his team's seats were not moved with him.
3. **Bug 4 (35 people in Samiron's position) — the data is real, but it is the wrong
   shape.** Samiron sits in a seat called "Back Office - Back Office - Chandigarh Sector 34"
   that holds **36 people** (Samiron plus 35 others). The "Set up the chart from your people"
   tool put every employee whose job role is "Back Office" at that branch into one seat.
   Samiron's job role is also "Back Office", so he landed in the same pool as 28 of his own
   reports, 6 of Vaneet's and 2 of Vikas's. The screen shows that faithfully.

---

## Bug 1 — "Arrange by" appears only after a filter

**Cause (fact, from the code).**
`alvoraa_portal/alvoraa_portal/templates/includes/ess/parts/positions.html` line 62 starts
the box hidden: `<div id="pos-arrange-wrap" style="display:none">`.
`alvoraa_portal/alvoraa_portal/public/js/ess/portal.js`, `posPaint()` (line ~519):

```js
var arr = document.getElementById("pos-arrange-wrap");
if (arr) arr.style.display = tree ? "" : "none";
```

`tree` is true only when the View dropdown says "As a structure". The View dropdown's first
option is "As a list", so the page opens as a list with the box hidden. The comment says this
was deliberate: "A list has no spine to rearrange".

**Why it looks like "after a filter" (inference).** View sits in the same row as Branch,
Department, Job role and Show, and every one of them calls `posPaint()`. Changing View to
"As a structure" feels like applying a filter, and that is the moment the box appears.

**Data or code:** code only.

**Smallest fix.**
- `positions.html`: remove `style="display:none"` from `pos-arrange-wrap`.
- `portal.js` `posPaint()`: delete the two lines that hide and show it.
- What "Arrange by" does on the list needs one decision (see question Q1). My recommended
  default: when somebody picks Branch or Department while on the list, switch View to
  "As a structure" in the same change handler, so the choice always has a visible effect.
  That is one line in the `onchange` of `pos-f-arrange`.

**Tests it would touch.** `scripts/check_positions_tree.js` — add one check that the box is
visible with View = list and with View = tree (the harness already creates
`pos-arrange-wrap`, line 53). `scripts/browser_check_positions.js` sets the arrangement
after switching to tree; it keeps working.

**NFR / cross-module impact.** Neutral on all seven: no server call, no data, no permission
change. Only this page uses these element ids. Accessibility improves slightly: a control
no longer appears and disappears mid-row.

---

## Bug 3 — Vaneet's hierarchy is missing in the default view

**What the data says (facts, read from DTC on 21 Oct 2026).**

| Fact | Value |
|---|---|
| Seats at DTC | 90, all Active, one company. Only one seat has no parent: the Owner seat. No broken parent links. |
| Vaneet's seat today | "Chief Finance Officer", reports to "Owner - Management - Chandigarh Sector 34". He holds it 100%, since 16 Oct. |
| Seats reporting to the CFO seat | **None.** |
| Vaneet's direct reports (Employee "Reports To") | 18 active people. |
| Where those 18 sit | 17 in seats whose parent is the **Owner seat**: Back Office pool (6), Office Executive (4), Reconcile (2), and one each in Payrol Executive, Payroll - HR, Data Analyst, Network Engineer and MIS. 1 (Shivam) in Accountant, whose parent is Samiron's Back Office seat. Every one of the 18 has a seat. |
| History | 14 Oct: the chart was built with the setup tool. Vaneet's job role was then "Owner", so he went into the Owner seat with Vikas Garg. 16 Oct 08:21: his job role was changed to "Chief Financial Officer". 08:26: Administrator made the CFO seat. His Owner assignment was ended (last day 15 Oct). |

**Cause.** The seats under Vaneet were never moved. When the chart was built, the setup tool
gave each seat the parent its people's managers sat in. Vaneet sat in the Owner seat then,
so his team's seats went under Owner. When he moved to the new CFO seat, nothing moved those
seats with him. So the CFO box is a leaf. His team is still on the chart, but under Vikas.

**Not the code (checked).**
- `_scope()` / `position_table`: Administrator and HR see all 90 seats. Nothing is dropped.
- The tree builder (`posKids`, `posNode`): the CFO seat is at depth 1. `POS_OPEN_DEPTH = 2`
  draws its children if it had any. It has none, so nothing is folded away.
- Grouping identical siblings: only seats with no children are grouped. It does not merge
  the CFO seat with anything (no sibling has the same title).
- Filter greying, status, dates: all seats Active; Vaneet's assignment is current.

**A real code gap behind it (inference).** The seat tree (`reports_to_position`) and the
person tree (Employee "Reports To") are two separate records. Nothing tells anybody when they
disagree. Here, Employee says 18 people report to Vaneet; the seat tree says 0. This is not a
display bug, but it is why the fault was silent.

**Side finding — please confirm it is intended.** If Vaneet himself opens the page, he sees
only the Chandigarh Sector 34 seats. He has a Branch user permission on "DTC Chandigarh
Sector 34" that applies to Employee, so `permitted_branches()` limits him to that branch
(the DEF-6 rule every HR screen follows). He is CFO and an Org Structure Editor. If he is
meant to edit the whole company's structure, that permission row stops him. That is a
setting, not code.

**Data or code:** data fault. The code is drawing it correctly.

**Smallest fix — data, done on the screen, no code.** In Positions, "Change" each seat and set
"Reports to" = "Chief Finance Officer":
- Seats that are wholly Vaneet's people: Payrol Executive, Payroll - HR, Reconcile,
  Data Analyst, Network Engineer.
- Seats that are mostly his: Office Executive (4 of 6 report to him).
- Mixed seats that cannot move whole: MIS (1 Vaneet, 1 Vikas); Accountant (1 Vaneet,
  4 Samiron); the Back Office pool (6 Vaneet). For these, his people need a seat of their
  own under CFO. That is a DTC decision about what those jobs are called, so the data
  change is theirs or Surbhi's to direct.

This is a change to a live tenant's records, so it needs Surbhi's explicit word and is
best done by DTC's own Org Structure Editor (Vaneet himself, once the branch permission is
settled), not by a script.

**Optional code change (not recommended now).** A note on the Positions page saying "18 people
report to Vaneet, but his seat has nobody under it", computed from data the page already
loads plus one Employee query. That is new behaviour, so it should go through the product
manager first. I do not recommend building it inside a bug fix.

**NFR / cross-module impact of the data fix.** Re-parenting a seat changes only
`reports_to_position`. It does not change who approves leave or expenses today: that follows
Employee "Reports To". **One knock-on to know about:** the seat tree does decide whose
approvals move when somebody later covers a seat with "Also move approvals to this seat"
ticked (`_people_under` in `alvoraa_position_assignment.py`). Today, a stand-in for the CFO
seat would get nobody's approvals, because nothing sits under it; after the fix they would
get Vaneet's team's, which is the correct answer. Existing delegations are not touched. The
org chart and `metrics.py` read the same seat tree, so they will show Vaneet's team under him
too. No performance or privacy effect.

---

## Bug 4 — 35 employees appear in Samiron's position

**What the data says (facts).**

| Fact | Value |
|---|---|
| Samiron Mondol | Job role "Back Office", branch Chandigarh Sector 34, reports to Vikas Garg. 64 active direct reports. |
| His seat | "Back Office - Back Office - Chandigarh Sector 34", seats = 36, **36 people in it today**, all at 100%, all Permanent. |
| Who those 36 report to | Samiron 28, Vaneet 6, Vikas 2 (Samiron himself). |
| Seats under it | 10 child seats (Accountant, Driver, Housekeeping, Tagging, and so on). |
| Others | Nobody at DTC holds more than one seat. 363 of 445 active employees hold a seat. |

So "35 employees" = Samiron plus 35 others sharing one seat. They are real assignments,
not a grouping of identical sibling boxes, and not a drawing fault. The card shows three
names and "+33 more in this seat", which adds up to 36.

**Cause (fact, from the code).** `hrms/hrms/alvoraa_org_structure/api.py`,
`propose_positions()` makes **one seat per job role + department + branch**
(`key()`, line 282). Every "Back Office" employee at Sector 34 became one seat, with seats
set to how many people there were. A manager whose job role is the same as his team's
lands in the same seat as them. The function's own docstring says this can happen and
"somebody has to split them". Nobody split this one.

**Data or code:** both.
- The **data** is wrong as a picture of the organisation: a 36-person pool with the
  department head inside it.
- The **code** that made it (`propose_positions`) has a known weakness: it cannot tell a
  manager from the people they manage when they share a job role.
- The **screen** is right. It shows the seat as it is stored.

**Smallest fix — data, on the screen.**
1. Add a one-person seat for Samiron (for example "Head - Back Office", seats 1), reporting
   to the Owner seat.
2. Put Samiron in it with "Take them out of other seats" chosen, so he leaves the pool.
3. Point the 10 child seats at his new seat, and the Back Office pool itself at his new seat.
4. Move Vaneet's 6 and Vikas's 2 out of the pool into seats under their own managers
   (this overlaps Bug 3).

The exact seat names are DTC's call.

**Optional code fix, to stop it happening at the next tenant.** In `propose_positions`,
give anybody who manages people in their own group a seat of their own (one extra key part
for "manages others in this group"). About five lines in `api.py`, plus one test in
`hrms/hrms/alvoraa_org_structure/tests/` (a manager and two reports with the same job role
must come out as two seats, one of one). It does not touch existing seats. I recommend it,
but as a separate approved change, not inside this bug fix.

**NFR / cross-module impact.** Data fix: none beyond Bug 3's. Optional code fix: only the
setup proposal changes; nothing already created is touched; performance neutral (same
single Employee query); no new data exposed.

---

## Questions for Surbhi

- **Q1.** With "Arrange by" always visible, what should picking Branch or Department do while
  the page is a list? My recommended default: switch to "As a structure". The other option
  is to make "As a structure" the page's opening view.
- **Q2.** Who makes the DTC data changes for Bugs 3 and 4 — DTC's own editor, or us on your
  word? Either way it is a change to live tenant data and needs your explicit approval.
- **Q3.** Should Vaneet see every branch on the Positions page? Today his Branch permission
  limits him to Chandigarh Sector 34.
- **Q4.** Do you want the optional setup-tool fix (managers get their own seat) as its own
  small change?

## Impact summary

| Dimension | Bug 1 fix | Bug 3/4 data fix | Optional setup fix |
|---|---|---|---|
| Performance | neutral | neutral | neutral |
| Security | neutral | neutral (no approval routing changes) | neutral |
| Reliability | neutral | improves (chart matches reporting) | improves |
| Scalability | neutral | neutral | neutral |
| Maintainability | improves (two lines removed) | neutral | neutral |
| Data integrity | neutral | improves | improves for new tenants |
| Compliance / privacy | neutral | neutral | neutral |

Personas: CXO and HR Manager see the corrected chart. An Employee does not open this page.
Cross-module: `reports_to_position` is read only inside `alvoraa_org_structure`
(`register.py`, `api.py`, `metrics.py`, the position, assignment and reporting-line doctypes)
and one patch (`hrms/patches/v16_0/mark_position_groups.py`). No Python in `alvoraa_goals`,
payroll, leave or attendance reads it. Leave and expense approvals read it only through
cover delegation, as noted under Bug 3.
