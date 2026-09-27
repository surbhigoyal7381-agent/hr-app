# Building your HRMS agent team — step by step

A five-agent software team for an HRMS built on Frappe, Frappe HR and ERPNext,
designed to run inside Claude Code in `C:\Surbhi-Git\hr-app`.

The agents are **generic and reusable** — nothing in them is wired to a specific
product. All product-specific truth lives in one file you fill in
(`.claude/context/product-context.md`), so the same team can work a second product
by swapping that file.

---

## What you're getting

```
C:\Surbhi-Git\hr-app\
├── CLAUDE.md                                  team charter — auto-loaded by every agent
├── .claude\
│   ├── agents\
│   │   ├── hrms-product-manager.md            what & why
│   │   ├── hrms-business-analyst.md           unambiguous, testable spec
│   │   ├── hrms-fullstack-engineer.md         working code, NFRs built in
│   │   ├── hrms-test-automation-engineer.md   automated proof
│   │   └── hrms-technofunctional-reviewer.md  final gate
│   ├── context\
│   │   ├── product-context.md                 ← YOU FILL THIS IN
│   │   ├── nfr-budget.md                      ← YOU AGREE THESE NUMBERS
│   │   ├── definition-of-ready-done.md        the two gates
│   │   ├── frappe-conventions.md              how we build here
│   │   └── handoff-contract.md                what each artifact must contain
│   └── skills\
│       ├── slice-start\SKILL.md               /slice-start — PM → human gate → BA
│       └── slice-build\SKILL.md               /slice-build — Dev → Test → Review
└── docs\slices\                               where the work actually accumulates
```

---

## The five agents, in one table

| # | Agent | Its one job | Writes |
|---|---|---|---|
| 1 | `hrms-product-manager` | Decide what's worth building and cut it thin. Names one WOW moment per slice. First to say "no", first to say "smaller". | `01-product-brief.md` |
| 2 | `hrms-business-analyst` | Remove every ambiguity. Gap-analyses against what Frappe HR already ships, then writes testable ACs, the permission matrix and the edge cases. | `02-functional-spec.md` |
| 3 | `hrms-fullstack-engineer` | Build the thin vertical slice with NFRs designed in, not bolted on. | code + `03-implementation-notes.md` |
| 4 | `hrms-test-automation-engineer` | Prove it works — and find where it doesn't. Owns permission and privacy tests. | tests + `04-test-report.md` |
| 5 | `hrms-technofunctional-reviewer` | Final gate on four axes: technical, functional, non-functional, AI. Ship / Fix / Block. | `05-review.md` |

All five share the same base: HCM/HRM domain knowledge, Frappe/Frappe HR/ERPNext
techno-functional grounding, NFR literacy, plain example-driven language, and a hard
rule against over-engineering.

---

## Step 1 — Put the files in place (5 minutes)

Unzip the bundle and copy its contents into `C:\Surbhi-Git\hr-app\`, preserving the
folder structure. In PowerShell, from the folder where you unzipped:

```powershell
Copy-Item -Path .\hrms-agent-team\* -Destination C:\Surbhi-Git\hr-app\ -Recurse -Force
```

If `C:\Surbhi-Git\hr-app\CLAUDE.md` already exists, **do not overwrite it** — open
both and merge by hand. Your existing project memory is worth more than my template.

Commit it. These files are team assets, not personal config:

```powershell
cd C:\Surbhi-Git\hr-app
git add CLAUDE.md .claude docs/slices
git commit -m "Add HRMS agent team: 5 agents, shared context pack, slice workflow"
```

---

## Step 2 — Fill in the product context (20–30 minutes, and the highest-value step)

Open `.claude\context\product-context.md` and replace every `TODO`.

This is the step people skip, and it is the one that decides output quality. The
agents are instructed to **stop and ask you** when this file is still placeholders —
that is correct behaviour, not a bug, but it wastes your time in a loop.

Be honest in it. Where you're guessing, write `[ASSUMPTION]`. The agents inherit the
labels, so your uncertainty travels with the work instead of hardening into a
false fact three documents later.

The most useful section on that page is **"What we deliberately do NOT do."** Fill it
in properly. It's what stops the PM agent proposing a feature-parity clone of
Darwinbox.

---

## Step 3 — Agree the NFR numbers (30 minutes with your engineer)

Open `.claude\context\nfr-budget.md`. Every number in it is a **starting default I
supplied, not a measurement.** Replace each with a figure your team actually agrees
to, and mark anything unagreed `[ASSUMPTION]`.

Pay particular attention to:

- **Volume** — employees per tenant, records per employee per year, peak concurrency.
  Without real numbers, "it scales" is untestable, and the test agent will (correctly)
  refuse to claim it does.
- **Privacy** — the retention and deletion rules, and your data-residency position.
- **Accessibility** — which WCAG level your customers actually require.
- **AI cost ceilings** — per employee per month, and per action.

A budget nobody agreed to is decoration. This half hour is what turns three of the
five agents from opinionated into accountable.

---

## Step 4 — Verify the agents loaded (2 minutes)

Start Claude Code in the repo and check:

```
/agents
```

Then test one directly:

```
Ask hrms-product-manager to summarise what it needs from me before it can work.
```

It should tell you it needs `product-context.md` filled in. If it instead launches
into a confident product strategy, the context file isn't being read — check the file
path and that you're running Claude Code from the repo root.

**Two things worth verifying yourself rather than taking from me:** the exact
frontmatter fields Claude Code supports for subagents, and the `/agents` behaviour,
both change across versions. If a field is rejected, delete that line — `name`,
`description` and the markdown body are the parts that matter; `tools`, `model` and
`color` are refinements.

---

## Step 5 — Dry-run on something you already understand (1 hour)

**Do not start with a new feature.** Start with something already built, where you
know the right answer — that's how you calibrate the team before you trust it.

Pick a small feature that already exists in your app. Then:

```
/slice-start Employees can see who else on their team is off in the same week, on the leave approval screen
```

Watch for three things:

1. **Does the PM agent cut it thin enough?** If the brief still has three user roles
   in it, tell it to cut harder. Push once and see if it holds its ground with a
   reason or just folds — you want an agent that argues.
2. **Does the BA's gap analysis find what Frappe HR already ships?** This is the
   single highest-value output on the whole team. If it invents fields that already
   exist, the codebase grounding isn't working — check that Claude Code can actually
   read `apps/hrms` from where you launched it.
3. **Does the human gate actually stop?** `/slice-start` is built to pause after the
   brief and wait for your decision. If it barrels through to the spec, the skill
   isn't loading.

Then run `/slice-build <slice-id>` and read `05-review.md` closely. The reviewer is
instructed to prove every finding with a concrete failure scenario before reporting
it — if you're getting vague style nits, tell it so, and consider raising its model.

---

## Step 6 — Run it for real

The loop, once you trust it:

```
/slice-start <the idea>          → brief → YOU DECIDE → spec
/slice-build <slice-id>          → code → tests → review → verdict
```

Two human gates, deliberately: **after the brief** (is this the right thing?) and
**after the review** (does it ship?). Everything in between is the team's.

You can also call any agent directly for one-off work, without the full relay:

```
Ask hrms-technofunctional-reviewer to review the diff on this branch.
Ask hrms-business-analyst to write acceptance criteria for the existing attendance regularisation flow.
Ask hrms-test-automation-engineer to reproduce this bug as a failing test.
```

---

## How the relay works, and why it's built this way

```
  idea
    │
    ▼
 [ PM ] ──01-product-brief──▶ ★ YOU DECIDE ★
                                   │
                                   ▼
                                [ BA ] ──02-functional-spec──┐
                                                             ▼
                                                       [ ENGINEER ] ──03-notes──┐
                                                                                ▼
                                                                          [ TESTER ] ──04-report──┐
                                                                                                  ▼
                                                                                          [ REVIEWER ] ──05-review──▶ ★ YOU DECIDE ★
```

**Agents hand off through files, not conversation.** A file can be read by a human,
corrected by a human, versioned in git and reviewed a year later. A conversation
can't. This one decision is what makes the team auditable — which matters more in HR
software than in most domains, because someone will eventually ask *why does the
system do this* and the answer needs to survive staff turnover.

**Nobody signs off their own work.** The engineer doesn't decide the tests are
enough; the reviewer doesn't write the fix. This is the oldest rule in software
quality and the easiest one to lose when a single AI does everything in one context.

**Each agent gets a fresh context.** The reviewer has not seen the engineer talk
itself into a shortcut. That independence is most of the value of using five agents
instead of one long conversation.

**Every agent has a stop condition.** Each one is told, explicitly, when to stop and
ask a human rather than guess: legal or statutory rulings, missing numbers that
change the decision, conflicting requirements, an API it cannot verify. A team that
never stops is a team that's guessing.

---

## The practices I built in, and why

| Practice | Where it lives | Why it matters for HRMS specifically |
|---|---|---|
| **Verify, don't recall** | Every agent's boot sequence | Frappe's APIs move between versions. An agent quoting a remembered function signature writes code that doesn't run. All five are told: find it in `apps/` or it doesn't exist. |
| **Gap analysis before spec** | BA agent | Frappe HR ships a lot. The most expensive bug on this team is specifying something that already exists. |
| **Configure → extend → build → new app** | Charter, BA, engineer | Your anti-over-engineering ladder. Each agent must say which rung it chose and why the cheaper one failed. |
| **Permission negative-tests** | Tester, reviewer | In an HRMS the worst bugs aren't crashes — they're the wrong person seeing a salary or a leave reason. So the tests assert who *cannot* see, not just who can. |
| **No personal data in logs, prompts, fixtures** | NFR budget, all agents | HR data is the most sensitive data most companies hold. Made a hard rule, not a guideline. |
| **Transparency ≠ surveillance** | PM agent, charter | You asked for transparency. The PM agent is explicitly barred from proposing anything that lets a manager surveil, rank or infer sensitive attributes about an individual. Aggregate, or don't show it. |
| **One WOW moment per slice, specified to the screen** | PM agent | "Delightful UX" is unbuildable. "A one-line team-coverage bar under the approve button" is buildable this week. |
| **Structural AI guardrails, not prompt guardrails** | Engineer, tester, reviewer, NFR budget | A guardrail that's a sentence in a prompt isn't a guardrail. The reviewer treats prompt-only guardrails as a Blocker. |
| **Findings must be proven** | Reviewer | Five real defects beat thirty maybes. Thirty maybes teach the team to skim your reviews. |
| **Label what you don't know** | Charter, every agent | `[ASSUMPTION]`, `[UNVERIFIED]`, `[recall — verify]`. Uncertainty travels with the work instead of hardening into a false fact downstream. |
| **Definition of Ready / Done** | Two checklists, enforced at both ends | Gates, not paperwork. An agent that can't tick a box says so instead of passing soft work on. |

---

## Tuning

**Models.** All five ship with `model: inherit`, so they use whatever your session
uses. If reviews feel shallow or specs feel thin, pin the thinking-heavy roles to your
strongest model and leave the mechanical ones inheriting:

```yaml
model: opus     # in hrms-product-manager, hrms-business-analyst, hrms-technofunctional-reviewer
```

**Tools.** The reviewer is deliberately restricted to read-only tools plus `Write`
(for its report) — it reviews, it doesn't fix. Don't loosen this; a reviewer that can
edit stops being a gate. The engineer and tester inherit all tools because they need
`bench`, git and the test runner.

**Permissions.** Consider pre-approving your routine bench and test commands in
`.claude/settings.json` so the engineer and tester don't stall on prompts. Add only
the specific commands you actually want run unattended — do not blanket-approve, and
do not turn permission checks off wholesale on a repo that can reach a live bench.

**Tone.** If output drifts into consultant vocabulary, the fix is one line in
`CLAUDE.md` under house rule 3 — that file is loaded by all five, so it's the cheapest
place to correct the whole team at once.

**When an agent is wrong**, fix the agent file, not the conversation. That's the
difference between a team and a chat session: corrections compound.

---

## The roles I'd add next (you asked me to flag the gaps)

You asked for five and got five. Here's honestly what the five don't cover, ranked by
how soon it will bite you.

**1. UX / product designer — the biggest gap.** You said "best end-user experience"
and "wow in the simplest way." Right now the PM specifies the WOW moment in words and
the engineer implements it. Nobody designs the interaction, the information hierarchy,
the empty states, the mobile layout for a frontline worker on a shared phone. On an
HRMS whose whole promise is *simple and delightful*, this is the role whose absence
shows up in the product first.

**2. Security & data-privacy specialist (DPDP / GDPR).** Privacy rules are currently
distributed across the NFR budget, the engineer and the reviewer — which is far better
than nothing, but nobody *owns* it. HR is the most regulated data in most companies:
consent, retention, cross-border transfer, subject access requests, the right to
erasure against an audit trail that must be retained. And every agent correctly says
"I'm not a lawyer." At some point you need one, and a specialist agent to prepare the
questions for them.

**3. DevOps / release & migration engineer.** Who runs `bench update` against real
tenant data? Who writes the migration for 200 live sites, and the rollback when it
half-fails at 2am? This is where multi-tenant Frappe deployments actually hurt, and
none of the five owns it.

**4. Data & analytics / AI evals engineer.** The PM defines success measures; nobody
instruments them, builds the dashboard, or maintains the golden eval sets that keep
the AI features honest as prompts and models change. Without this, "we'll measure it"
stays aspirational and your AI quality silently drifts.

**5. Technical writer / enablement.** In-product help, admin guides, release notes,
what support answers at 9am on a Monday. Cheap to add, disproportionate effect on
adoption of an HR product where the buyer and the user are different people.

**6. An orchestrator / tech lead agent.** Only once you're running several slices at
once. Adding it before then is exactly the over-engineering you asked me to avoid.

My advice: **run the five for two or three real slices first.** You'll discover which
gap actually hurts you rather than which one sounds most important on paper. Then add
one. Adding four at once gives you a team nobody understands.

---

## Honest caveats

Things I could not verify, and you should:

- **I have not seen `C:\Surbhi-Git\hr-app`.** No folder was connected to this session,
  so the agents' shell commands (`ls apps/`, `find apps/hrms ...`) assume a standard
  Frappe bench layout with the app checked out under `apps/`. If your repo is a
  single custom app rather than a bench, adjust those paths in
  `frappe-conventions.md` and in the agents' boot sequences — it's a find-and-replace,
  not a redesign.
- **Claude Code's subagent frontmatter schema changes across versions.** I verified
  the fields I used against current documentation, but if your version rejects one,
  delete that line. `name`, `description` and the body are what matter.
- **I have deliberately not written any Frappe API calls into these agents** — no
  function names, no hook names beyond the widely-stable `hooks.py` concepts, no field
  names. Every agent is instead instructed to verify against your installed source
  before using anything. That's not caution for its own sake: an agent that confidently
  calls a function that doesn't exist in your version is worse than one that looks it
  up.
- **The NFR numbers are defaults, not recommendations for your scale.** I don't know
  your tenant sizes. Step 3 exists for that reason.
- **Competitor names in the PM agent are illustrative.** Their current feature sets
  should be checked, not recalled — the agent is told to mark recall as
  `[recall — verify]`, and you should hold it to that.

---

*Bundle version 1.0 · 24 August 2026*
