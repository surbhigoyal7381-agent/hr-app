# Usage discipline

Surbhi's Claude usage is limited. These rules save usage **without lowering quality**. They size the work to the risk. They never skip a step that guards money, access, personal data or deletion. Every agent reads this file. The session that orchestrates also follows it. (Written 27 Oct 2026.)

## 1 · Name the risk tier first

The orchestrator writes the tier in the brief and in the report. When unsure, go one tier up. Surbhi can always ask for more.

| Tier | What it touches | Engineer model | Review | Security |
|---|---|---|---|---|
| **1** | Who can see or change what (permissions, field rights, branch or company scope), pay or money, personal data, deletion or retention, scripts that write production data, migrations, deploys | strong (`opus`) | independent reviewer (strong) | separate security verification |
| **2** | New screens or flows, report logic, new fields that carry no Tier 1 element | `sonnet` | ONE independent review that also checks the slice's own SEC items | only if the reviewer flags it |
| **3** | Wording, labels, a report column that splits an existing figure, CSS, docs | `sonnet` | the orchestrator reads the whole diff (that is step 5 of the change process); no reviewer agent | none |

Steps 4 to 6 of CLAUDE.md still happen at every tier. The tier changes who does them and how much, not whether.

## 2 · Models

- Strong model: `hrms-technofunctional-reviewer` and `hrms-security-privacy-engineer`, always. Judging code and threats is where a cheaper model costs the most when it misses.
- Everything else defaults to `sonnet`. The orchestrator passes `model: opus` for a Tier 1 build.
- Mechanical work (rebase, file moves, ticket comments, a known command) never needs an agent. Do it in one or two tool calls.

## 3 · Briefs and reading

- A brief carries the task, the constraints specific to it and the tier. It points at files. It does not retype lessons that live in `.claude/context/`. Aim for 40 lines or fewer.
- Read the headings of a long document first, then only the sections you need. Do not read a 1,400-line spec to change one screen.
- Do not re-read a file you just wrote or edited.
- Before briefing a build, check what already exists. On 26 Oct a request for a grooming column was nearly built, but the report's Net already took grooming off.

## 4 · Tests

- Run the modules you touched plus their direct neighbours, one at a time. Slow modules (over 10 minutes) run in the background. Do not poll them.
- The full suite runs once, before a release candidate, and in CI. Never run it after each fix.
- Never re-run unchanged code only to double-check it. Re-run only after a change, or to settle a known flaky test (ALV-235).
- Each engineer uses its own container and site. Two sessions on one site break each other's runs, and every rerun costs usage.

## 5 · Reviews

- One review per round. A re-review reads the findings list and the fix diff, not the whole slice again.
- A reviewer that passes work with no findings does not get a second reviewer.

## 6 · Lifecycle

- One agent per worktree. Two in one worktree is how work is lost.
- An agent reports **only when finished or blocked**. No "waiting on background work" updates. No polling loops: one bounded wait, then report.
- Stop the containers you started when you finish.
- The orchestrator checks for a live agent the moment a report arrives, and stops it.
- Agents do not push, deploy or touch servers. Surbhi decides each step forward.
