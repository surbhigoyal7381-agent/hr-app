# Handoff contract

Agents do not talk to each other. They talk to **files**. This is deliberate: a file
can be read by a human, corrected by a human, versioned in git, and reviewed a year
later. A conversation cannot.

**Every approval belongs to the user.** Agents write, recommend and flag. They never
approve their own work or anyone else's, and they never deploy.

## Before any slice — product priorities

Run with `/product-priorities`, before new slices and at least once a quarter.

    docs/product/priorities/
      <YYYY-MM-DD>-kano-review.md   ← hrms-product-manager
      <YYYY-MM-DD>-ux-evidence.md   ← hrms-ux-designer
      <YYYY-MM-DD>-ops-notes.md     ← hrms-devops-engineer

▶ **Gate: the user chooses what becomes a slice.**

## One slice, one folder

    docs/slices/<slice-id>/
      00-impact-analysis.md                  ← hrms-fullstack-engineer
      01-product-brief.md                    ← hrms-product-manager
      01a-ux-opportunities.md                ← hrms-ux-designer
      01b-ux-design.md  (+ prototype link)   ← hrms-ux-designer
      01c-security-privacy-requirements.md   ← hrms-security-privacy-engineer
      02-functional-spec.md                  ← hrms-business-analyst
      03-implementation-notes.md             ← hrms-fullstack-engineer
      04-test-report.md                      ← hrms-test-automation-engineer
      05-review.md                           ← hrms-technofunctional-reviewer
      06-security-review.md                  ← hrms-security-privacy-engineer
      07-devops-inputs.md  (one section per stage) ← hrms-devops-engineer

`<slice-id>` is `NNN-short-kebab-name`, e.g. `007-leave-team-coverage`.

## The order they run in

File numbers say where to find things. **This table says when they are written.**

| # | Step | Who | Writes | Reads first |
|---|---|---|---|---|
| 1 | UX opportunities | UX designer | `01a` | the idea, latest priorities review, `ux-learnings.md` |
| 1 | Run-side view of the idea | DevOps | `07` §1 Brief | the idea |
| 2 | Brief | Product manager | `01` | `01a`, `07` §1, priorities review |
| ▶ | **Gate: build, change or drop** | **User** | | `01` |
| 3 | Design and **clickable prototype** | UX designer | `01b` + prototype | `01`, `01a` |
| 3 | Design run-side notes | DevOps | `07` §2 Design | `01b`, prototype |
| ▶ | **Design check: go, change or drop** | **User** | feedback → `ux-learnings.md` | prototype, `01b`, `07` §2 |
| 4 | Security and privacy requirements | Security | `01c` | `01`, `01b` |
| 4 | Operational requirements | DevOps | `07` §3 Requirements | `01`, `01b` |
| 5 | Functional spec and user stories | Business analyst | `02` | `01`, `01b`, `01c`, `07` §3 |
| 6 | Impact analysis and strategy | Engineer | `00` | `02`, `01c`, `07` §1–3 |
| 6 | View on the strategy | DevOps | `07` §4 Strategy | `00` |
| ▶ | **Gate: approve the strategy** | **User** | | `00`, `07` §4 |
| 7 | Build — local only | Engineer | code + `03` | `00`, `02` |
| 8 | Tests | Test engineer | tests + `04` | `02`, `01c`, `07` §3, `03` |
| 9 | Review | Reviewer | `05` | everything above |
| 9 | Security review | Security | `06` | `01c`, the diff, `04` |
| 9 | Release readiness | DevOps | `07` §5 Release | the diff, `04` |
| ▶ | **Gate: push to dev — later, push to main** | **User** | | `05`, `06`, `07` §5 |

Rows with the same number run at the same time. **A Blocker from the reviewer, security
or DevOps blocks the slice.**

Steps 1 and 3 may be skipped for back-end-only slices — say so in the brief. Step 4 is
never skipped: "no personal data touched" is a valid finding, but it is written down.

## Rules

1. **Read your input artifacts before you start.** Missing or thin input → stop and
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
       inputs: [01-product-brief.md, 01b-ux-design.md, 01c-security-privacy-requirements.md]
       ---

4. Every artifact ends with the same three sections: **Open questions** (owner + the
   decision each blocks), **Assumptions** (each labelled `[ASSUMPTION]`), and
   **Handoff note** (one paragraph to the next agent: what to watch out for).
5. **You may disagree with the artifact above you.** Say it in your Handoff note and
   stop, rather than quietly building something different. Silent divergence is how
   teams ship the wrong thing confidently.
6. Never edit an artifact you do not own. Propose the change; the owner makes it. If
   an artifact is superseded, set `status: superseded` and write the new version — do
   not rewrite history. `07-devops-inputs.md` grows by dated sections; earlier sections
   are never rewritten.
7. **Requirement IDs travel.** Security writes `SEC-n` and `PRIV-n`, DevOps writes
   `OPS-n`, the analyst writes `US-n` stories and `AC-n` criteria. Every `SEC`, `PRIV`
   and `OPS` item must map to an `AC`, or be marked "not adopted" with the user's
   decision recorded.

## What each artifact must contain

**Priorities review** *(`kano-review`)* — current state verified against the repo
(built / partial / not built) · pending features from the backlog · new candidates ·
market-demand evidence, every claim labelled with source and date or `[recall — verify]`
· Kano class per feature, marked **survey** or **proxy** · a priority order that weighs
Kano class, demand, effort and strategic fit · a Kano survey kit to validate the proxies
· questions for the user. *(`ux-evidence`, `ops-notes`)* — usability pain and opportunity,
and effort, run cost and risk, for each top candidate.

**01a-ux-opportunities** — current screens and journeys for this module, with evidence ·
how competitors' whole products handle it, labelled seen / read / `[recall — verify]` ·
**persona by persona, how the employee portal could make this module better** — each
idea with the job it serves and the evidence behind it · what not to copy. No prototype
yet; rough sketches are fine.

**01-product-brief** — job to be done in the user's words · current pain (data or a
story, never a manufactured number) · **competitive analysis** across whole products,
incl. what we will NOT do · **Kano class and market demand** for this module ·
**persona enhancements through the employee portal** — which of the `01a` ideas are in
this slice and why · the WOW moment, specified to the screen · the thin slice and what is
out of scope · success measures with baseline, target and instrumentation ·
thriving-workplace check · risks and kill criteria.

**01b-ux-design** *(when the slice changes a screen)* — personas in scope and their
jobs · evidence from real screens, with where the screenshots are stored (outside the
repo) · findings table (ID, impact, kind, size, evidence) · flows with the empty,
loading, error, no-permission and first-time states · screen-by-screen specs with the
exact words, English and Hindi · accessibility (WCAG 2.2 AA) and privacy notes ·
**link to the clickable prototype — mandatory; there is no design check without one** ·
usability test plan for high-impact changes · the behaviours the analyst must turn into
acceptance criteria. The designer records what each run taught it in
`.claude/context/ux-learnings.md`.

**01c-security-privacy-requirements** — threat model in four lines · data inventory
(field → sensitivity class → purpose → retention) · access intent, including who must
NOT see what · obligations engaged, from the baseline, dated · abuse cases · numbered
`SEC-n` and `PRIV-n` requirements, each with how it will be tested · questions for
counsel or the compliance owner.

**02-functional-spec** — gap analysis (configure / extend / build / drop) grounded in
the actual source · process flow with unhappy paths · data model with every field
justified · state table · permission matrix including the negative cases · **epic and
user stories** (`US-n`, "As a… I want… so that…", INVEST-checked, sized, linked to
prototype screens) · numbered Given/When/Then ACs with observable oracles · HR edge
cases · slice-specific NFR numbers · migration/backfill · notification copy ·
localisation and accessibility · audit trail · compliance-impact sub-analysis ·
⚠ COMPLIANCE flags with named owners · traceability table (brief → story → AC, and every
`SEC`, `PRIV`, `OPS` → AC) · Ready check.

**00-impact-analysis** — cross-module reach (`alvoraa_goals`, `alvox_compensation`,
`alvoraa_portal`, `hrms`, `erpnext`) · the grep output for every caller of every function
being changed · impact on all three personas · HRMS domain impact · a verdict of
`improves` / `degrades` / `neutral` on each of the seven non-functional dimensions with
one line of reasoning · how each `SEC`, `PRIV` and `OPS` item will be met · the proposed
strategy, its risks and trade-offs, and the consequences nobody asked about yet. **Ends at
a human gate.**

**03-implementation-notes** — what was built, file by file, with the mechanism chosen
and why · AC-by-AC status · NFR notes (query counts, indexes, background jobs,
permission enforcement points, sensitive fields, fallbacks) · commands actually run
and their real output · known gaps and declared shortcuts.

**04-test-report** — AC → test → pass/fail coverage table, including every `SEC`,
`PRIV` and `OPS` item · extra cases added and why · NFR results with measured numbers ·
defects found with repro steps and severity · what is deliberately not automated and
the human checklist · verdict.

**05-review** — verdict on line one · blockers, majors, minors with file:line and a
concrete failure scenario each · AC verification table · NFR verification table ·
**compliance verification table** (obligation → mechanism in the diff → test that proves
it → discharged / partial / not) · does the built screen match the approved prototype ·
what to delete · what was done well · confidence and what could not be verified.

**06-security-review** — threat model re-checked against the code · every `SEC` and
`PRIV` requirement from `01c` marked **met / partial / not met**, with the mechanism and
the test · findings with file:line and a concrete actor-and-path scenario · what could not
be verified and what access it would need · **residual risk, with the name of whoever
accepted it and the date.**

**07-devops-inputs** — one dated section per stage (§1 Brief, §2 Design, §3 Requirements,
§4 Strategy, §5 Release readiness) · every item an `OPS-n` row: recommendation, why, cost
of ignoring it, Recommend / Consider / FYI, and a **Decision column left for the user** ·
§5 carries the rollout plan, migration dry run, deploy commands marked for approval,
post-deploy checks and rollback.
