# Handoff contract

Agents do not talk to each other. They talk to **files**. This is deliberate: a file
can be read by a human, corrected by a human, versioned in git, and reviewed a year
later. A conversation cannot.

Every unit of work is a **slice** with a folder:

    docs/slices/<slice-id>/
      01-product-brief.md          ← hrms-product-manager
      01b-ux-design.md             ← hrms-ux-designer (when the slice changes what
                                     a person sees or does on a screen). Read by
                                     the analyst before writing the spec.
      00-impact-analysis.md        ← hrms-fullstack-engineer, written AFTER the spec
                                     and BEFORE any code (CLAUDE.md §2 steps 1-2).
                                     Numbered 00 because it is read first at review.
      02-functional-spec.md        ← hrms-business-analyst
      03-implementation-notes.md   ← hrms-fullstack-engineer
      04-test-report.md            ← hrms-test-automation-engineer
      05-review.md                 ← hrms-technofunctional-reviewer
      06-security-review.md        ← hrms-security-privacy-engineer (only when the
                                     slice touches personal data, permissions,
                                     integrations, or AI — which is most of them)

`<slice-id>` is `NNN-short-kebab-name`, e.g. `007-leave-team-coverage`.

## Rules

1. **Read your input artifact before you start.** Missing or thin input → stop and
   say so. Do not reconstruct it from the chat message.
2. **Write your output artifact before you declare done.** Code without notes is not
   a handoff.
3. Every artifact starts with the same header block:

       ---
       slice: 007-leave-team-coverage
       artifact: 02-functional-spec
       author: hrms-business-analyst
       date: YYYY-MM-DD
       status: draft | ready | superseded
       inputs: [01-product-brief.md]
       ---

4. Every artifact ends with the same three sections: **Open questions** (owner + the
   decision each blocks), **Assumptions** (each labelled `[ASSUMPTION]`), and
   **Handoff note** (one paragraph to the next agent: what to watch out for).
5. **You may disagree with the artifact above you.** Say it in your Handoff note and
   stop, rather than quietly building something different. Silent divergence is how
   teams ship the wrong thing confidently.
6. Never edit an artifact you do not own. Propose the change; the owner makes it. If
   an artifact is superseded, set `status: superseded` and write the new version — do
   not rewrite history.

## What each artifact must contain

**01-product-brief** — job to be done in the user's words · current pain (data or a
story, never a manufactured number) · competitive read incl. what we will NOT do ·
the WOW moment, specified to the screen · the thin slice and what is out of scope ·
success measures with baseline, target and instrumentation · thriving-workplace
check (engagement / collaboration / inclusiveness / transparency) · risks and kill
criteria.

**01b-ux-design** *(when the slice changes a screen)* — personas in scope and their
jobs · evidence from real screens, with where the screenshots are stored (outside the
repo) · competitor benchmark with every claim labelled seen / read with date /
`[recall — verify]` · findings table (ID, impact, kind, size, evidence) · flows with the
empty, loading, error, no-permission and first-time states · screen-by-screen specs with
the exact words, English and Hindi · accessibility (WCAG 2.2 AA) and privacy notes ·
prototype link · usability test plan for high-impact changes · the behaviours the analyst
must turn into acceptance criteria. The designer also records what the run taught it in
`.claude/context/ux-learnings.md`.

**02-functional-spec** — gap analysis (configure / extend / build / drop) grounded in
the actual source · process flow with unhappy paths · data model with every field
justified · state table · permission matrix including the negative cases · numbered
Given/When/Then ACs with observable oracles · HR edge cases · slice-specific NFR
numbers · migration/backfill · notification copy · localisation and accessibility ·
audit trail · ⚠ COMPLIANCE flags with named owners · traceability table · Ready check.

**00-impact-analysis** — cross-module reach (`alvoraa_goals`, `alvox_compensation`,
`alvoraa_portal`, `hrms`, `erpnext`) · the grep output for every caller of every function
being changed · impact on all three personas · HRMS domain impact · a verdict of
`improves` / `degrades` / `neutral` on each of the seven non-functional dimensions with
one line of reasoning · the proposed strategy, its risks and trade-offs, and the
consequences nobody asked about yet. **Ends at a human gate.**

**03-implementation-notes** — what was built, file by file, with the mechanism chosen
and why · AC-by-AC status · NFR notes (query counts, indexes, background jobs,
permission enforcement points, sensitive fields, fallbacks) · commands actually run
and their real output · known gaps and declared shortcuts.

**04-test-report** — AC → test → pass/fail coverage table · extra cases added and why ·
NFR results with measured numbers · defects found with repro steps and severity ·
what is deliberately not automated and the human checklist · verdict.

**05-review** — verdict on line one · blockers, majors, minors with file:line and a
concrete failure scenario each · AC verification table · NFR verification table ·
**compliance verification table** (obligation → mechanism in the diff → test that proves
it → discharged / partial / not) · what to delete · what was done well · confidence and
what could not be verified.

**06-security-review** *(when applicable)* — threat model in four lines · findings with
file:line and a concrete actor-and-path scenario · the compliance verification table
from the security lens · what could not be verified and what access it would need ·
**residual risk, with the name of whoever accepted it and the date.**
