# The agent contract — how the eight agents work as one team

This is the index and the connective tissue. It does not repeat what other files
already own — it names them, and adds the handful of cross-agent rules that didn't
have a single home before now: a shared priority ladder, a shared escalation format, a
named conflict-resolution step, a named stop-the-line rule, and a risk scale.

**If this file and another context file disagree, the more specific file wins**
(`handoff-contract.md` for artifacts, `change-process.md` for gates,
`definition-of-ready-done.md` for the checklists, `parallel-work.md` for git). If any
of them disagree with `CLAUDE.md`, `CLAUDE.md` wins. This file gets corrected, not the
other way round.

---

## 1 · The organisation, in one table

| Agent | Owns | Primary artifact(s) | Boot sequence reads |
|---|---|---|---|
| **You (human Product Owner)** | Every approval. Strategy, material scope, risk acceptance, and the six gates below. | The decision itself — nothing else can make it for you. | — |
| `hrms-product-manager` | What gets built, why, in what order | `kano-review`, `01-product-brief.md` | `.claude/agents/hrms-product-manager.md` |
| `hrms-ux-designer` | How it feels to use | `01a-ux-opportunities.md`, `01b-ux-design.md` + prototype | `.claude/agents/hrms-ux-designer.md` |
| `hrms-security-privacy-engineer` | Security and privacy requirements, then their verification | `01c-security-privacy-requirements.md`, `06-security-review.md` | `.claude/agents/hrms-security-privacy-engineer.md` |
| `hrms-business-analyst` | The testable functional spec | `02-functional-spec.md` | `.claude/agents/hrms-business-analyst.md` |
| `hrms-fullstack-engineer` | Impact analysis, strategy, code | `00-impact-analysis.md`, `03-implementation-notes.md` | `.claude/agents/hrms-fullstack-engineer.md` |
| `hrms-test-automation-engineer` | Automated proof the slice works | `04-test-report.md` | `.claude/agents/hrms-test-automation-engineer.md` |
| `hrms-technofunctional-reviewer` | The independent senior-architect review | `05-review.md` | `.claude/agents/hrms-technofunctional-reviewer.md` |
| `hrms-devops-engineer` | Performance and security advice at every stage, the release plan | `07-devops-inputs.md` (one section per stage) | `.claude/agents/hrms-devops-engineer.md` |

**No agent approves its own work, anyone else's, or a deploy.** That is true for all
eight, without exception, every time. `CLAUDE.md` §7 says this in one line; this table
just makes it concrete per agent.

**The three skills are the orchestrator.** `/product-priorities`, `/slice-start` and
`/slice-build` already run the sequence below — parallel steps, gates, and the two-round
retry cap — as executable instructions. This file explains the rules behind those
skills; it does not replace them.

---

## 2 · A feature is a slice — there is no separate ID scheme

`Feature ID = <slice-id>` (`NNN-short-kebab-name`, e.g. `007-leave-team-coverage`).
Nothing new to track: the slice id already appears in every artifact's header block
(`handoff-contract.md` rule 3), the work-board row (`parallel-work.md` §2), the branch
name (`slice/<slice-id>`), and the folder `docs/slices/<slice-id>/`.

**The Feature Contract is not a YAML file — it's the folder.** `docs/slices/<slice-id>/`
*is* the shared source of truth: one file per concern, one owner per file, each one
readable, versionable and correctable by a human. `handoff-contract.md` defines exactly
what each of the eleven files must contain and who writes it. Read that file for the
full artifact contract — it is not repeated here.

---

## 3 · The lifecycle and its six gates

`change-process.md` and the three `SKILL.md` files are authoritative for this. In
outline:

```
IDEA → priorities gate → BRIEF → brief gate → DESIGN → design gate →
REQUIREMENTS (security + devops, parallel) → SPEC → STRATEGY → strategy gate →
BUILD (local only) → TEST (2-round retry cap) → REVIEW (reviewer + security + devops,
parallel, 2-round retry cap) → REPORT → dev gate → main gate
```

Six gates, all the user's, none skippable:

1. **Priorities** — which candidates become slices (`/product-priorities`).
2. **The brief** — build, change or drop (`/slice-start` step 4).
3. **The design check** — go, change or drop, against the clickable prototype
   (`/slice-start` step 6).
4. **The strategy** — approve the implementation approach before any code is written
   (`/slice-build` step 2; this *is* `CLAUDE.md` §2 steps 2–3).
5. **Push to `dev`** — after the reviewer, security and DevOps verdicts.
6. **Push to `main`** — separately, after the user has tested on `dev`.

There is no fast lane that skips a gate because a change looks small or low-risk. A
change's risk classification (§6 below) changes **how much detail the gate shows the
user** — it never removes the gate. This is the one place this contract deliberately
scales back the ambition of a fully autonomous platform: this product handles the most
sensitive data most companies hold, so **every** stage gets a human decision, not just
the final release.

---

## 4 · Priority ladder — when requirements conflict

Two requirements will sometimes pull in different directions inside one slice. Don't
quietly pick a side. Weigh it against this order, highest first:

1. **Safety, legal, security, privacy and ethics.** Never traded for speed, revenue, a
   deadline or a loud stakeholder.
2. **The named persona's actual outcome.**
3. **Strategic product fit** (`product-context.md` §7).
4. **Business value** — never above customer trust or the product's long-term health.
5. **Agreed NFRs** (`nfr-budget.md`).
6. **AI trust and reliability**, where AI is in scope.
7. **Delivery feasibility** — real, but it doesn't silently override product value; a
   big trade-off gets surfaced, not absorbed.
8. **Time-to-value** — prefer what proves itself sooner and is easier to walk back.
9. **Competitive parity** — evidence, not a requirement.
10. **Internal stakeholder requests** — an input, never an automatic priority.
11. **Polish.** Last, once everything above is settled.

`hrms-product-manager` and `hrms-ux-designer` each carry a working copy of this ladder
already, tuned to their own document. This is the canonical version — any agent that
needs it and doesn't have its own copy should use this one, unchanged.

## 5 · Escalation format — never "please advise"

Whoever escalates, say all of this:

```
Decision needed:
Context:
Evidence:
Conflict — which requirements or principles are pulling apart:
Options, with a recommendation and why:
Risk if it waits:
Owner — who actually needs to decide:
Deadline, if there is one:
```

Use the `⚠ DECISION` / `⚠ COMPLIANCE` markers already in use across the agent files so
it's easy to find in a document.

**Who owns what kind of call**, so escalation goes to the smallest group that can
actually decide, never "everyone": a business-rule ambiguity is the analyst's to
validate; a UX/interaction conflict is the designer's, with the asker's recommendation
attached; technical feasibility is the engineer's; security, privacy or AI risk is the
security engineer's; run cost or release risk is DevOps's. **Strategy, material scope,
commercial commitment, legal/compliance rulings, security exceptions, and anything none
of the above own — that's the user, every time.**

## 6 · Risk classification — sizes the gate, never skips it

| Level | Examples | What it changes |
|---|---|---|
| **R0 — minimal** | Copy change, minor UI tweak, non-functional cleanup | Gates stay brief — one line each is enough |
| **R1 — low** | A new report, a filter, non-sensitive config | Normal gate detail |
| **R2 — moderate** | New workflow, new business process, new integration, real schema change | Full gate detail; specialist review named explicitly |
| **R3 — high** | Payroll, sensitive employee data, financial calculations, major permission changes, real AI automation | Full detail, and the gate names the specific residual risk and who is accepting it |
| **R4 — critical** | Legal/compliance impact, an irreversible data change, major security exposure, infrastructure that touches every tenant | Full detail, explicit written risk acceptance, and — per `parallel-work.md` and `frappe-conventions.md`'s production wall — extra care before anything server-side runs |

State the level in the brief and again at the strategy gate. It's a communication tool,
not a permission slip — see §3 above.

## 7 · Conflict resolution between two agents

This consolidates rules that already exist in `handoff-contract.md` and
`parallel-work.md` into one named step, so any agent can point to it:

1. **State it, don't silently resolve it.** Evidence, assumption, recommendation,
   risk, impact — from each side.
2. **Try the priority ladder (§4) and the documented product principles first.**
   Most disagreements resolve here.
3. **The product manager resolves what's within its authority** — see its own
   "Where your authority ends" section for the PM/BA, PM/UX and PM/engineer
   boundaries.
4. **Escalate to the user (§5) when it's strategy, material scope, material risk, a
   security exception, a legal question, an irreversible decision, or outside anyone's
   authority.** Never let one agent unilaterally overrule another's independent
   verdict — a reviewer's, security's or DevOps's Blocker is not the product manager's
   or the engineer's to waive.

This is the general form of two rules already in force: "you may disagree with the
artifact above you — say it in your handoff note and stop" (`handoff-contract.md` rule
5), and "if the two changes want different behaviour, stop and ask the user — do not
pick a winner yourself" (`parallel-work.md` §5).

## 8 · Stop-the-line

Any agent may stop a slice's progress — not just the reviewer, security and DevOps at
the review gate — on a credible, evidence-based:

- security or privacy risk
- data-integrity risk
- critical functional defect or major regression
- production-safety issue
- an NFR that genuinely can't be met

**A Blocker from the reviewer, security or DevOps already blocks the slice** —
`slice-build` step 5 is explicit about this, and it is not a suggestion the product
manager can override to hit a date. Stopping is a good outcome, named plainly, not
softened into a lesser verdict to keep things moving.

## 9 · Decision memory

Don't reopen a settled question without new evidence. This repo already has the
mechanism — this just names it:

- **Priority calls**: the Kano review's `status: superseded` pattern — mark the old
  draft superseded, write the new one, never rewrite history.
- **Point decisions**: `⚠ DECISION` and `⚠ COMPLIANCE` markers, each naming an owner and
  what it blocks.
- **Everything else**: every artifact's closing **Open questions** and **Assumptions**
  sections (`handoff-contract.md` rule 4) are the record. A later agent reads the
  artifact above it before asking a question that artifact already answered.

## 10 · Bounded retry — no infinite loops

Already enforced with a concrete number, not just a principle:

- **Test failures**: engineer fixes, tests rerun. **Cap at two rounds** — a third means
  the spec is wrong, not the code (`slice-build` step 4).
- **Review blockers**: fix and re-review, same **two-round cap** (`slice-build` step 5).

An agent capable of fixing a failure it caused should fix it without being asked —
that's the point of the cap existing at all, rather than escalating every red test.
Escalate once the cap is hit, the root cause is unclear, or fixing it would need a
different strategy (back to the strategy gate) or a different spec (back to the
business analyst).

## 11 · AI governance — where the rules actually live

There's no separate AI section here because the rules are already cross-cutting and
load-bearing where they live:

- **The hard refusals** (no AI-set ratings, no emotion/voice/facial inference, no
  passive behavioural monitoring, no surveillance dressed as transparency) —
  `product-context.md` §6, restated in the product manager's and UX designer's own
  files as things they will not propose or design.
- **The NFR budget for AI** — `nfr-budget.md` §6: the structural guardrails, not
  prompt-only ones.
- **The engineer's build rules** — untrusted text is data, never instruction; no
  irreversible action without a named human; a non-AI fallback and a kill switch on
  every AI path.
- **The spec's AI checklist** — objective, context, tools, permissions, boundaries,
  confidence threshold, human approval point, memory, audit, reversibility, failure
  handling — carried in the business analyst's and the engineer's own files.

If a slice includes AI, every agent that touches it applies its own AI rules; none of
them are optional because another agent "already checked."

---

## What this contract deliberately does not claim

Being honest about the gap between the platform this was adapted from and what
actually runs here, so nobody mistakes aspiration for capability:

- **No agent has live write access to YouTrack.** The product manager reads the backlog
  when it can, and asks for an export when it can't. The business analyst explicitly
  does not create issues there. There is no automated `Trigger → Condition → Action`
  engine updating YouTrack as work moves — if the user wants that, it's a real
  DevOps/tooling project of its own, not something this contract can assume into
  existence.
- **There is no autonomous release lane.** Every risk level still passes through all
  six gates in §3. A low-risk (R0/R1) change gets a shorter gate, never a skipped one.
- **There is no background "platform" enforcing any of this automatically.** The three
  skills are the orchestration; a human (or a session following a skill) runs them.
  Concurrency control, conflict detection and the worktree model are real, but they are
  git and file discipline followed by each agent (`parallel-work.md`), not a service
  watching for clashes.
- **Feature IDs are slice IDs.** No parallel `HRMS-FEAT-NNNN` numbering was introduced.

## Where to find the rest

| Question | File |
|---|---|
| What does each artifact contain, and who writes it? | `handoff-contract.md` |
| Is a slice ready to build? Ready to ship? | `definition-of-ready-done.md` |
| What are the seven steps, in order, and which commands need approval? | `change-process.md` |
| How do I avoid clashing with another session or developer? | `parallel-work.md` |
| Who do we serve, and what do we refuse to build? | `product-context.md` |
| What are the actual performance/security/privacy/accessibility numbers? | `nfr-budget.md` |
| Which laws and standards bind this product? | `security-compliance-baseline.md` |
| Which feature discharges which obligation? | `compliance-feature-map.md` |
| How do we build on Frappe here, and what's off limits? | `frappe-conventions.md` |
| What has UX feedback already taught us? | `ux-learnings.md` |
| What must every agent check when a slice installs an existing Frappe app? | `new-frappe-app-checklist.md` |
