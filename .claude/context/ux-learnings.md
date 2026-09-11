# UX learnings — Alvoraa

**Owner:** `hrms-ux-designer` · **Started:** 11 Sep 2026
Read first by the UX designer on every run, and written to at the end of every run.
The rules for adding, promoting and retiring entries are in
`.claude/agents/hrms-ux-designer.md` → *The learning loop*.

**Status ladder:** `heard` → `applied` → `confirmed` → `principle` · or `retired`.
Nothing here holds personal data, passwords or screenshots. Evidence lives in
`C:/Surbhi-Git/hrlocal-data/ux-review/`, outside the repo.

---

## Principles — confirmed

Rules the user has stated, or that the evidence has settled. These override the
defaults in the agent file.

| # | Principle | Why | Source |
|---|---|---|---|
| P1 | Plain, everyday English in documents **and** on screens. | The user's standing rule. | `CLAUDE.md` §6 |
| P2 | Benchmark competitors' **whole products** — manager, HR, performance, analytics — not only their self-service pages. | The user corrected a narrow benchmark mid-task. | Surbhi, 11 Sep 2026 |
| P3 | Build on the Alvoraa design-system tokens. Do not invent a palette. | The project's own system comes before a designer's taste. | `design_system.html`; review 11 Sep 2026 |
| P4 | Measure phone layouts; do not eyeball them. Check width beyond the screen, tap targets under 44px, field text under 16px, text under 12px. | Five root causes found by measuring, not by looking. | Mobile audit, slice 003 |
| P5 | Check a fact in the data before calling it a UI bug. | "Holiday" on Thursdays turned out to be the store's weekly off. The real bug was the label. | Review 11 Sep 2026 |
| P6 | Every design run ends with a clickable prototype. No design check without one. | The user reviews by clicking, not by reading a document. | Surbhi, 11 Sep 2026 |
| P7 | Persona-by-persona ideas for the employee portal come before the brief, in the opportunities scan. | The PM needs UX evidence to shape the slice, not a design after it is fixed. | Surbhi, 11 Sep 2026 |

---

## Patterns — applied, not yet tested with users

Used in the 11 Sep 2026 prototype. Promote to `confirmed` only after the user agrees,
a usability test shows it, or the same need comes up again.

| Pattern | What it solves | Where it was used | Status |
|---|---|---|---|
| **Needs you** strip at the top of Home | Nothing told people what was due (review H1) | Prototype, Home | applied |
| Labelled menu grouped **Me · Time · Pay · Growth · Team · Company** | Icon-only menu; five attendance entries (G2, G3) | Prototype, menu | applied |
| Bell on every screen plus an **Inbox** with "Waiting on me" and "My requests" | No approvals entry on desktop (G4) | Prototype, Inbox | applied |
| **Exceptions before lists** for managers, with inline Approve / Decline | Off-track goal buried at the bottom (MH1, MH2) | Prototype, manager Home | applied |
| **Act in place** — tap an absent day to apply leave or fix attendance | Absent days had no action (AL1) | Prototype, Time | applied |
| **Explain the money** — "Why ₹548?" walks through the late rule, day by day | Lateness shown but never explained (MA3) | Prototype, Pay and Late rule | applied |
| **Guided self-review** — 5 steps, guidance per step, autosave, check before sending | Two equal buttons and no guidance (PF2, PF3) | Prototype, Self-review | applied |
| Phone bottom bar with **short labels** ("Time", not "Attendance & leave") | Long labels wrapped onto two lines | Prototype, phone | applied |
| **Check In** as the largest control on a phone | Check-in is the phone's main daily job (PH3) | Prototype, phone Home | applied |
| **Sample** tag on every invented number or name | Keeps a prototype honest with real tenant data | Review and prototype | applied |
| Rules-based suggestion that explains why it appeared ("Because a new joiner has a full-quarter target") | Nudges without AI, each with its reason | Prototype, manager Home | applied |

---

## Anti-patterns seen in Alvoraa

Each one was seen on a real screen. Check new designs against this list.

| Anti-pattern | Where it was seen | Finding |
|---|---|---|
| The top bar title never changes ("Home" on every page) | All 34 desktop screens | G1 |
| Icon-only navigation | Portal sidebar | G2 |
| A 40-row people grid on Home | Employee Home | H2 |
| Red used for an ordinary count, or for a full leave balance | Performance, leave rings | PF4, AL2 |
| One idea under two names (weekly off shown as "Holiday") | My Attendance vs Home | MA2 |
| A raw failure shown to a user ("Could not load progress approvals") | Team View | TV1 |
| Two buttons of equal weight for one decision | Self-review | PF2 |
| A red Delete beside every row | Org Settings | OS2 |
| Analyst words for one person ("person-days") | Attendance Insights | AI3 |
| Greyed-out tabs a person cannot open | Attendance Insights | AI2 |
| A different default month on screens that show the same data | Attendance Insights vs My Attendance | AI1 |
| Desktop layout rules leaking onto the phone | Mobile audit causes R1–R5 | PH1 |

---

## Checklist additions

Items learned the hard way. Add these to the standard pre-handoff check.

- [ ] Hindi and Punjabi strings run longer. Check the layout with them, not only English.
- [ ] Notification badges sit outside the icon, not on top of it.
- [ ] Keyboard hints like "Ctrl K" never wrap.
- [ ] Links in section headers use the same style everywhere (no stray underline).
- [ ] Stock photos and decorative illustrations are not competitor evidence.
- [ ] Label each competitor claim: seen / read with date / `[recall — verify]`.

---

## Open items for the human

| Item | Owner | Blocks |
|---|---|---|
| My Attendance marks a 09:25 arrival "25 min late", but the shift starts at 09:30. Likely an engineering bug, not a design issue. Not yet investigated. | Engineering | Trust in lateness numbers; the late-rule explanation |
| Hindi and Punjabi labels in the prototype are machine drafts. | Surbhi, or a native reviewer | Any language work shipping |
| Competitor scorecard is not verified with trial accounts. | Surbhi | Quoting the scorecard externally |
| None of the prototype patterns has been tested with real users yet. | Surbhi | Promoting patterns to `confirmed` |

---

## Feedback log — newest first

| Date | Source | What was said | What it teaches | What changed | Status |
|---|---|---|---|---|---|
| 2026-09-11 | Surbhi, chat | "It must create a prototype for review" | A written design is not something the user can react to | Principle P6: no design check without a clickable prototype; versions kept as v1, v2 | principle |
| 2026-09-11 | Surbhi, chat | "PM must also do the competitive analysis and using the support from the UX agent suggest how the user experience of this module can be enhanced by Employee Self Service Portal for different personas" | UX evidence should shape the brief, not arrive after it | Principle P7: new opportunities-scan mode writes `01a` before the brief | principle |
| 2026-09-11 | Surbhi, chat | "write a reverse prompt to create an agent for UX design … keep learning based on the feedbacks" | UX work needs a standing owner with memory kept in a file | Created this file and `hrms-ux-designer` | applied |
| 2026-09-11 | Own look before publishing | Search box wrapped; badge covered the bell; bottom-bar labels wrapped; one underlined link | Small layout slips show up only on a real render | Added four checklist items | applied |
| 2026-09-11 | Surbhi, chat | "Based on the feedback on the UX, design a new prototype" | A review is expected to lead to a clickable prototype | Added *Prototype* as a standard method step | applied |
| 2026-09-11 | Surbhi, chat | "don't just focus on employee self service only for the competitors application assessment" | Benchmark whole products | Principle P2 | principle |
| 2026-09-11 | Surbhi, chat | "complete end to end document of key improvements page by page", with screenshots | Reviews go page by page, with real screenshots as evidence | Findings table with page-prefixed IDs | confirmed |
| 2026-09-11 | Mobile audit, slice 003 | 22 phone gaps, mostly from 5 page-frame causes | Fix the frame before individual screens | Principle P4 | principle |
| standing | `CLAUDE.md` §6 | "Write in simple, plain English" | Applies to screens, not only documents | Principle P1 | principle |

---

## Archive

Nothing archived yet.
