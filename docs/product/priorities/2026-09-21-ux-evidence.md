---
artifact: ux-evidence
scope: usability evidence for the top-ranked candidates in 2026-09-21-kano-review.md §6
author: hrms-ux-designer
date: 2026-09-21
status: draft
inputs: [.claude/context/ux-learnings.md, .claude/context/product-context.md,
  .claude/context/nfr-budget.md, docs/product/priorities/2026-09-21-kano-review.md,
  docs/slices/010-portal-security-fixes/00-impact-analysis.md,
  docs/slices/009-ess-portal-redesign/00-assessment-and-plan.md,
  docs/slices/009-ess-portal-redesign/appendix-d-growth-team-people.md,
  docs/slices/003-ess-mobile-responsive/00-current-state-assessment.md,
  docs/slices/002-ess-home-redesign/01-product-brief.md,
  OBJECTIVES_KPI_REQUIREMENTS.md,
  alvoraa_portal/alvoraa_portal/www/hrms-employee.html (direct code read, this session)]
---

# UX evidence for the top Kano candidates

**No prototype in this document — this is evidence mode, not design mode.** Everything
below is either a direct read of the live source in this repo (labelled **seen — code,
21 Sep 2026**) or a citation of an earlier review already on file (labelled **seen —
prior review**, with its date). I did not redo the PM's ranking work in
`2026-09-21-kano-review.md`; I am adding what past screens and past reviews say about
each of the PM's top eight items, in their order.

**The local instance (`hrlocal-bench`, `http://127.0.0.1:8010`) is down this session** —
`curl` returned connection refused. I could not capture fresh screenshots or click
through real screens. Everything below is either a direct read of the checked-out
source code (which does not need the server running) or evidence already captured on a
prior session when the instance was up, cited by date. `[ASSUMPTION]` Nothing has
changed in the cited screens between their capture date and today; if the instance comes
back up, a fresh look before design work starts would confirm this cheaply.

**Read first, as instructed: `ux-learnings.md`.** Two entries apply directly here and I
have followed both: P5 ("check a fact in the data before calling it a UI bug" — see the
weightage finding below, which I verified against the actual JS, not a description of
it) and P4 ("measure, don't eyeball" — the mobile-audit citations below are measured
numbers from `003`, not my own impression).

---

## The one finding that should change how a candidate is scoped

**C1 (KPI weightage enforcement) is scoped in the Kano review as a backend fix
("enforce weightage + validate `KPI.py`"). The screen already has a place for the
live feedback that fix needs — and it has never been wired up.**

**Seen — code, 21 Sep 2026.** The "New KPI" form
(`alvoraa_portal/alvoraa_portal/www/hrms-employee.html:4703-4707`) has:

```html
<div class="gp-label">Weightage % *</div>
<input class="gp-input" id="pf-k-weightage" type="number" step="any" min="0" max="100" placeholder="60">
<div class="gp-hint" id="pf-k-weight-hint"></div>
```

`pf-k-weight-hint` is declared once and never referenced anywhere else in the file — I
grepped the whole page for it. **The hint div HR or the employee would see while typing
a KPI's weightage exists in the markup and has never had text put in it.** Nothing tells
the person, at the moment they type "60" into their third KPI, whether the set now
totals 100%.

The only places a weightage total is shown are all downstream of authoring, and all
worded softly:

| Where | Who sees it | Wording | Line |
|---|---|---|---|
| Goal creation dropdown hint | Employee, when picking a KRA | "Weightages total 87%, not 100%. HR may still be setting these up." | `:10219-10222` |
| Appraisal "Considered in This Cycle" card | Employee/manager, at review time | "Weightage allocated: 87% of 100%. Items at 0% ride along for context but are not scored." (amber alert) | `:10917-10920` |
| HR cycle-progress table | HR only | A number coloured green/amber (`weightage_ok`), no explanation text, no link to fix it | `:14130-14131` |

None of these is at the point of data entry, none blocks a save, and none offers "fix
it here" (rule 4, act where you see the problem) — the HR table just colours a number
amber and leaves HR to go find which KPI is wrong themselves.

**Why this matters for scoping, not just for design:** `OBJECTIVES_KPI_REQUIREMENTS.md`
(read, 18 Aug 2026) correctly diagnoses the backend gap — `KPI.py` is an empty `pass`,
nothing enforces the rule server-side (`KPIA-46`, "Critical"). But if C1 ships as a
server-side validation only, the most likely result is a **500 error or a rejected save
with no explanation** the first time someone hits the new rule — because the screen has
never told them the total as they built it up. A Must-be fix that surfaces as a
confusing failure is not a fix a frontline HR user or an employee typing their own KPIs
will trust. **Recommendation:** when C1's functional spec is written, scope the client
UI change (`pf-k-weight-hint`, wired to a running total as each KPI is added or edited,
plus a clear state when the set is complete) in the same slice as the server
enforcement — not as a follow-on. This does not change C1's rank; it changes what
"done" means for it, and it is worth roughly the same size band (S–M) the PM already
gave it, since the markup is already in place.

**Severity if this scope gap is missed:** P2 — high, not a blocker on its own, but it
would make a Must-be fix land as a worse experience than today's (a save that silently
worked with a wrong total now silently fails with no explanation).

---

## 1. C11 — push slice 010 to dev/main

**This is a release decision, not a new design.** The UX-relevant evidence is what
these ten holes actually expose to a person, drawn from
`docs/slices/010-portal-security-fixes/00-impact-analysis.md` (**seen — prior review,
14 Sep 2026, re-read this session**):

- **S4** — a manager can read a colleague's **draft** self-review before it is sent.
  This is not a hypothetical: it directly contradicts a decision Surbhi already made in
  `009`'s own plan (Q-d: "May managers see a self-review before it is sent? **No**").
  The product is currently doing the opposite of an agreed privacy rule. This is exactly
  the one-way rule's failure mode: a manager's convenience (seeing progress early)
  costing an employee the ability to write a draft without an audience.
- **S3** — an employee can read and, through a plain REST call, **write** their own
  `overall_rating` on their own appraisal record. No screen shows this is possible; it
  is invisible to the employee using the portal normally, but it means the rating shown
  to them on screen cannot be trusted as evidence of anything, which cuts against the
  whole "evidence-first, defensible decision" promise this product sells.
- **S5** — a manager's browser today receives a report's exact loss-of-pay amount
  (₹548.39 for Rahul), even though Surbhi already decided (Q-b) "days at most, never the
  amount." Same pattern as S4: a decision already made, not yet reflected on screen.
- **S8** — the goal drawer renders an employee's own free-text evidence note, unescaped,
  and it opens **in the manager's session** when the manager reviews a report's goal. A
  planted script would run as the manager, not the employee who planted it.

**What is reassuring:** the fix already includes the copy changes a person would see —
"Evidence sent to your manager for approval" instead of a false "approved" toast, and "Not
sent yet — you can read it once {name} sends it" for a draft self-review a manager opens
too early. That is plain language done at the point of the fix, not bolted on after
(rule 11). I have no design work to add here; the wording already proposed is right.

**Severity: P0.** This is a safety/privacy item at the top of the priority ladder
(§1: safety, legal, privacy, security) — it does not compete with anything else on
value grounds. It confirms, rather than changes, the PM's #1 ranking.

**Persona note:** Employee loses the most today (draft privacy, pay-figure exposure,
tamperable rating) and gains the most once shipped. Manager loses nothing they were
supposed to have. HR/CXO unaffected except a real reduction in support-ticket and
grievance risk.

---

## 2. C1 — KPI weightage enforcement

Covered in full above. Summary: **seen — code, 21 Sep 2026**, the authoring screen has
a dead hint element and only soft, buried, downstream warnings; no live running total,
no block, no "fix it here." This matches and sharpens the PM's Must-be classification.

**Persona note.** HR Manager: this is exactly the "sees who is not ready before a cycle
opens" need named in the persona table, and it is currently unmet — the HR cycle table
(`:14130`) shows an amber number with no path to the offending row. Employee: a wrong
weightage silently changes their derived score with no way for them to notice, which
breaks rule 3 ("explain every number that touches pay... one tap away") at its root
cause, before any rating explanation screen (C3) could even be honest about the number
it is explaining.

---

## 3. Wave 0 remaining "wrong numbers" (009, W2–W5)

**Seen — prior review, `009-ess-portal-redesign/appendix-d` and `00-assessment-and-plan.md`,
14 Sep 2026.** Already fully evidenced there; I am not re-discovering it, only naming
the UX consequence of each:

- **W2 — leave left overstated** (portal shows 3 for Rahul; Frappe HR's own ledger says
  0). This is shown as a bare number on Home with no "why" available — a direct rule-3
  violation, and it is money-adjacent (a wrong leave balance can lead to unpaid leave a
  person didn't plan for).
- **W3 — holidays from every holiday list in the company**, not the employee's own.
  Breaks rule 6 (one date, one source, everywhere) — an employee could plan around a
  holiday that isn't theirs.
- **W4 — "team this week" shows the wrong people entirely**: the whole department
  across stores, using the *viewer's own* weekly-off pattern applied to everyone else,
  and it never shows anyone as "in" today. This is the worst of the four for real-world
  consequence: a manager glancing at this widget could believe coverage exists that
  doesn't, or that someone is off when they're working. It is confidently wrong on a
  screen designed to be glanced at, not studied.
- **W5 — goal percentages mix review cycles**. An employee could see "73%" next to a
  goal with no visible cycle label, and not know which quarter it is being measured
  against — undermines trust in every other number nearby.

**Recommendation, not a reorder:** the PM's own `009` document already says this
correctly — "the redesign would put wrong numbers on bigger, clearer screens" — and
ranks Wave 0b fixes (#4) ahead of the redesign itself (#7). I agree with that
sequencing: rule 8 (honest states) and the priority ladder's #2 (the person's actual
outcome) both say a wrong number shown more prominently is a worse outcome than the
same wrong number shown quietly. Do not let Waves 1–4 UX work start on these widgets
until W2–W5 are confirmed fixed on real PP Jewellers data, not just in code.

**Severity: P1** for the redesign (a release-blocking dependency for any wave that
touches these numbers); **P2, arguably P1**, on today's live portal, since real PP
Jewellers employees see these numbers today, independent of any redesign.

---

## 4. C2 — Goal/KPI Library + attainment→rating lookup

Not built; no screen exists to review. The one relevant piece of live evidence: the
same "New KPI" form covered under C1 has **no template picker, no library search, no
suggested weightage** — every field is typed from a blank box (`hrms-employee.html:4695-4780`,
**seen — code, 21 Sep 2026**). This is the concrete, on-screen version of the
requirements doc's claim ("every KPI today is typed from scratch") — I confirmed it
directly rather than taking the claim on trust.

**Sequencing note, not a new finding:** a library that suggests a weightage per
template is only useful once the running-total problem from C1 is fixed — otherwise the
library speeds up typing a KPI set that still silently fails to sum to 100. The PM's
order (C1 before C2) is right for this reason as well as the ones already given.

**Experiment flag:** C6/C8/C9-style, this candidate has real competitor evidence
(read, `OBJECTIVES_KPI_REQUIREMENTS.md`) but no direct customer request on file for
Alvoraa specifically. The Kano survey kit in the review (§8) already covers C2 — worth
running before committing to a large template taxonomy, so the L-sized effort doesn't
outrun demand.

---

## 5. C3 — Rating Derivation + plain-language explanation

Not built. **Seen — code, 21 Sep 2026:** the employee-facing endpoints
(`get_my_appraisals`, `get_employee_final_review`, both grep'd this session in
`performance_api.py`) return `overall_rating` as a bare number. No screen anywhere in
`hrms-employee.html` shows which KPIs, evidence or weights produced it — I searched for
a "why" or breakdown pattern near the rating display and found none. This confirms the
PM's whitespace claim directly, not just by citation.

**This product already has the right pattern to reuse, proven elsewhere.** The
late-rule "Why ₹548?" explanation (built for Pay, `applied` in `ux-learnings.md`'s
pattern table from the 11 Sep prototype work) walks a deduction through the rule,
day by day, using the server's own real numbers. **Recommendation:** C3 should reuse
that exact interaction shape — a plain-language, numbered walk-through anchored to
real evidence — rather than invent a new pattern for rating. This is a design-mode
recommendation, not yet applied; flagging it now so it travels into C3's brief.

**Risk, not mine to resolve:** the PM's open question on EU exposure (Art 86) changes
whether this is compliance-critical or a differentiator. Either way, the UX shape is
the same; only the urgency changes.

---

## 6. `009` Waves 1–4 (the full portal redesign)

**Seen — prior review**, extensively documented already and not re-done here:

- `003-ess-mobile-responsive/00-current-state-assessment.md` (11 Sep 2026): 22 phone
  gaps, **4 blocking tasks** — M01 (Calibration Sign Off cannot be tapped, the top bar
  sits over it), M02 (four creation dialogs open cut off on the right — Create Goal,
  New KPI, New Review Cycle, New Expense Claim), M03 (the menu opens as an unlabelled
  56px icon strip, last items off-screen), M04 (the performance review wizard's step
  labels run together — "EMPLOYEEMANAGER" — and the desktop two-column layout squeezes
  the right column to two visible letters).
- `009-ess-portal-redesign`'s four appendices (14 Sep 2026): 137 requirements, each with
  its own evidence.
- The anti-pattern table already logged in `ux-learnings.md` from the earlier prototype
  review: title never changes (G1), icon-only nav (G2), a 40-row grid on Home (H2), red
  used for an ordinary count (PF4, AL2), "Holiday" used for weekly off (MA2), a raw
  server error shown to a user (TV1), two equal-weight buttons for one decision (PF2), a
  red Delete beside every row (OS2), inconsistent HR dashboards (AI1–AI3).

**My addition here is sequencing, not new findings:** M01 (Calibration Sign Off
unreachable on a phone) sits directly in the path of C4 below — if HR or a manager ever
needs to review or sign off calibration data from a phone between meetings (the line
manager persona's stated context), today's screen cannot be tapped at all, independent
of whether C4's leniency data ever gets built. That fix is already scheduled under Wave
1 (frame, ranked #6) ahead of C4 (#8) in the PM's order, which is the right sequence —
noted here only so nobody scopes C4 without noticing the ground it stands on is
currently broken.

**Severity: P1** for the redesign as a whole (a core journey — completing a review on a
phone — is currently broken, not merely rough). Confirms, does not change, rank #7's
position behind the Wave 0 fixes.

---

## 7. C4 — manager leniency/severity before calibration

Not built. I found no screen showing a leniency/severity spread for HR — grep of
`hrms-employee.html` for "calibration" surfaces only the Sign Off action referenced in
M01 above, which is a decision step, not a distribution report. **Seen — code, 21 Sep
2026** (grep, no positive result for a leniency/severity view) plus **seen — prior
review**, `003`'s M01 finding that the one calibration-adjacent screen that does exist
cannot be used on a phone today.

**No new UX finding beyond confirming the whitespace and naming the dependency above.**
This candidate needs a design-mode opportunities scan (persona-by-persona ideas,
competitor screenshots of what HROne/Darwinbox show for this) before a brief is
written — that scan has not happened yet and would be premature in evidence mode.

---

## 8. C5 — frontline two-minute review

Building on slice 008 (field-checkin) and 003 (mobile audit), both **seen — prior
review**:

- Slice 008 is the strongest proof this product can ship a genuinely two-minute,
  sunlight-readable flow for a persona who "may be barely literate in English, may
  never have used a work app" (008's own brief §2, read): one-screen-per-failure, a
  15/17/19/22/28/34 type scale with nothing under 15px, no action button where no
  action would work, camera-off degrades rather than blocks. These are logged
  `applied` in `ux-learnings.md`, **not yet `confirmed` with real users** — that gap is
  already on the open-items list there and should stay open until a usability test
  happens, whichever candidate uses the pattern next.
- `003`'s M04 is the direct, current blocker for C5 specifically: the existing
  performance-review wizard is unreadable on a phone today for *any* employee, not only
  a frontline one. "Two minutes on a phone" (the frontline bar this role's own
  instructions set) is not possible on the current screen at any reading level.
- The existing wizard's copy ("Went well / would do differently", "One thing to get
  better at") assumes office-worker vocabulary and English fluency — the opposite of
  what slice 008 deliberately built for. **Recommendation:** C5 should start from slice
  008's type scale and one-screen-per-step shape, not from the desktop wizard's, and
  its copy needs the same plain-vocabulary pass 008 got, not a port of the existing
  wizard's wording.

**Severity:** not a release blocker (not built), but flagged **P1-equivalent priority
if C5 is chosen next**, given the frontline bar is a standing rule in this role's own
brief, not just a nice-to-have for this one candidate.

---

## What I did not do, and why

- No prototype. This is evidence mode (`.claude/agents/hrms-ux-designer.md`, "Evidence"
  row) — a prototype is mandatory only in design mode, after a candidate becomes a
  slice.
- No fresh screenshots. The local instance was unreachable this session (checked,
  connection refused). Everything above that needed a running server is cited from a
  prior, dated capture rather than invented or eyeballed.
- No re-ranking. The Kano order in `2026-09-21-kano-review.md` §6 stands; my one scope
  note (C1 needs its client UI fixed alongside the server validation) changes what
  "done" means for that item, not its position.

## Open questions

| Question | Owner | Blocks |
|---|---|---|
| Has anything changed in the cited screens (`009`, `003`, `010`) since their capture dates (11–17 Sep 2026)? I could not re-check this session. | Whoever runs the next local-instance session | Confidence in this document's citations before design work starts |
| Should C1's functional spec include the client-side running-total UI, or is that a separate follow-on slice? | `hrms-business-analyst` / `hrms-product-manager` | C1's scope and size estimate |
| Is there a usability test scheduled for any of the `applied` (not yet `confirmed`) patterns from slice 008, before C5 reuses them? | Surbhi | Whether C5 inherits validated or unvalidated patterns |

## Assumptions

- `[ASSUMPTION]` The screens and line numbers cited from `009`, `003` and `010` are
  still accurate as of today; I re-verified only what I could read from the checked-out
  source this session (the weightage-hint finding, and the absence of a rating-breakdown
  screen), not the mobile-audit measurements themselves, which need a running instance.
- `[ASSUMPTION]` "PP Jewellers" remains the only tenant with real usage data referenced
  here; other tenants (dev, `alvoraa.co`, `minda`) are unverified for all of the above,
  matching the same caveat `010`'s own impact analysis carries.
