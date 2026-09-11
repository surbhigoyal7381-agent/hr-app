---
name: slice-build
description: >-
  Build, test and review an existing slice — the engineer's impact analysis with the
  DevOps view on the strategy, a human gate, the build on the local instance, tests,
  then the reviewer, the security review against the slice's own requirements and the
  DevOps release readiness together. Reports the verdicts and stops: deploying to dev,
  and later to main, is the user's decision. Use after /slice-start has produced a
  spec that passes its Ready check.
argument-hint: "[slice-id, e.g. 007-leave-team-coverage]"
---

# Build a slice

Slice: **$ARGUMENTS**

**Every approval is the user's. Nothing in this skill deploys.**

## 0. Preflight

Read `docs/slices/$ARGUMENTS/`: `01-product-brief.md`, `02-functional-spec.md`,
`01c-security-privacy-requirements.md` and `07-devops-inputs.md` §1–3 — plus
`01b-ux-design.md` and the approved prototype when the slice changes a screen.

**Stop and tell the user** if any of these is true:

- the spec is missing, or its Ready check fails
- open questions block the first day of work
- `01c` is missing — security and privacy are specified before build, not after
- a `SEC`, `PRIV` or `OPS` item is neither traced to an acceptance criterion nor marked
  "not adopted" with the user's decision recorded

Building against a soft spec is how a team ships the wrong thing on time.

## 1. Impact analysis and strategy — NO CODE YET

- Delegate to the **hrms-fullstack-engineer**: **impact analysis and strategy only, do
  not write code.** It writes `00-impact-analysis.md` — cross-module reach, every caller
  grepped, persona and HRMS domain impact, a verdict on each of the seven non-functional
  dimensions, how each `SEC`, `PRIV` and `OPS` item will be met, and the proposed approach.
- Then delegate to the **hrms-devops-engineer**, §4 Strategy → `07`: install order, image
  and Compose changes, migration risk, CI gates, version pinning — and where it agrees or
  disagrees with the engineer.

## 2. HUMAN GATE — the strategy

`CLAUDE.md` §2 requires explicit approval before implementation. Show the user, in plain
English and under 15 lines:

- what will change, and which apps and personas it reaches
- the recommended approach and the main trade-off
- any dimension marked **degrades**, and what is being done about it
- the consequences anticipated without being asked — cache invalidation, hook
  side-effects, shared doctypes
- **where DevOps and the engineer disagree — both views, plainly**
- any `OPS` recommendation still waiting for the user's decision

Then ask: **approve this approach, change it, or stop?** Wait for an answer.

**"Go ahead" here approves the implementation only. It does not approve deploying.**

## 3. Implement — on the local instance only

Delegate to the **hrms-fullstack-engineer** to build it. It writes code and
`03-implementation-notes.md`, including the seven dimensions re-assessed against the code
actually written. **No push, and no deploy commands.**

If it comes back with unresolved blockers, stop and surface them rather than pushing on
to tests.

## 4. Test

Delegate to the **hrms-test-automation-engineer**. It writes tests and `04-test-report.md`
covering every acceptance criterion, every `SEC`, `PRIV` and `OPS` item, the journeys
against the approved prototype, and — when an existing Frappe app is added — an install
on a fresh site the way CI builds one. It runs `bench run-tests --app <app>` for every
changed app.

If the verdict is **Fail**, send the defects back to the engineer and repeat step 3.
Cap this loop at **two** rounds — then stop and bring the user in. A third automated
round usually means the spec is wrong, not the code.

## 5. Review round — run these three at the same time

- **hrms-technofunctional-reviewer** → `05-review.md`, including whether the built
  screens match the approved prototype.
- **hrms-security-privacy-engineer**, review → `06-security-review.md`, marking every
  `SEC` and `PRIV` requirement from `01c` met / partial / not met.
- **hrms-devops-engineer**, §5 Release readiness → `07`: rollout from local to dev to
  main, a migration dry run on a copy, the deploy commands **marked for the user to
  approve**, checks to run after deploying, rollback, and monitoring.

They use different lenses and none waits on another. **A Blocker from any of the three
blocks the slice.**

- **BLOCK** → fix the blockers — back to step 1 if the strategy changes, otherwise step 3
  — then re-review. Same two-round cap.
- **SHIP WITH FIXES** → do the fixes, then re-review.
- **SHIP** → done. Ready to present — not permission to deploy.

## 6. Report back — and stop

In plain language, under 25 lines:

- any defect that looks like a privacy or compliance exposure, **at the top** —
  cross-tenant leakage, a permission bypass, a statutory identifier in a log, or
  personal data reaching a model are stop-the-line findings
- the three verdicts — reviewer, security, DevOps — each with its one-sentence reason
- what was built, whether it matches the approved prototype, and what the reviewer
  recommends deleting
- NFR results against the budget — measured numbers, not adjectives
- `SEC` and `PRIV` requirements met vs still open, and any residual risk that needs a
  named human to accept it
- the release plan in brief: rollout steps, rollback, and what to watch after deploying
- what is not automated and still needs a human to check
- the seven non-functional dimensions, **before vs. after**

Then **stop.** Deploying is the user's decision, and it happens in stages
(`CLAUDE.md` §1): push to **dev** only when the user says so; push to **main** only when
the user says so after testing on dev. The checklist runs **before `git commit`**. Never
run `git push`, `bench migrate`, `bench build`, `bench clear-cache`, `docker cp`,
`nginx -s reload` or any `scp` to the server on your own initiative.

Never soften a BLOCK. Never report a test run that did not happen.
