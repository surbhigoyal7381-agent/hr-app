---
name: slice-build
description: >-
  Build, test and review an existing slice — runs the full-stack engineer, then the
  test automation engineer, then the techno-functional reviewer, and reports the
  ship verdict. Use after /slice-start has produced an approved functional spec.
argument-hint: "[slice-id, e.g. 007-leave-team-coverage]"
---

# Build a slice

Slice: **$ARGUMENTS**

## 0. Preflight

Read `docs/slices/$ARGUMENTS/01-product-brief.md` and `02-functional-spec.md`.

If the spec is missing, or its Ready check fails, or it has open questions that block
the first day of work — **stop and tell the user**. Building against a soft spec is
how a team ships the wrong thing on time.

## 1. Impact analysis and strategy — NO CODE YET

Delegate to the **hrms-fullstack-engineer** agent with the slice id, and tell it
explicitly: **impact analysis and strategy only, do not write code.** It writes
`00-impact-analysis.md` — cross-module reach, every caller grepped, persona impact,
HRMS domain impact, a verdict on each of the seven non-functional dimensions, and the
proposed approach with its risks and trade-offs.

## 2. HUMAN GATE — stop here

`CLAUDE.md` §2 requires explicit approval before implementation. Show the user, in plain
English and under 15 lines:

- what will change, and which apps and personas it reaches
- the recommended approach and the main trade-off
- any dimension marked **degrades**, and what is being done about it
- the consequences the engineer anticipated without being asked — cache invalidation,
  hook side-effects, shared doctypes

Then ask: **approve this approach, change it, or stop?** Wait for an answer.

**"Go ahead" here approves the implementation only. It does not approve deploying.**

## 3. Implement

Once approved, delegate to the **hrms-fullstack-engineer** again to build it. It writes
code and `03-implementation-notes.md`, including the seven dimensions re-assessed
against the code actually written.

If it comes back with unresolved blockers, stop and surface them rather than pushing
on to tests.

## 4. Test

Delegate to the **hrms-test-automation-engineer** agent with the slice id. It writes
tests and `04-test-report.md`, and runs `bench run-tests --app <app>` for every changed
app plus a hand-traced pass over affected UI flows.

If the verdict is **Fail**, send the defects back to the engineer and repeat step 3.
Cap this loop at **two** rounds — if it is still failing after two, stop and bring the
user in. A third automated round usually means the spec is wrong, not the code.

## 5. Review

Delegate to the **hrms-technofunctional-reviewer** agent with the slice id. It writes
`05-review.md` with a verdict.

**If the slice touches personal data, permissions, integrations or AI — which is most of
them — also delegate to the `hrms-security-privacy-engineer`** in the same round. It
writes `06-security-review.md`. Run the two concurrently; they use different lenses and
neither waits on the other. **A Blocker from either one blocks the slice.**

- **BLOCK** → fix the blockers (back to step 1), then re-review. Same two-round cap.
- **SHIP WITH FIXES** → do the fixes, then re-review.
- **SHIP** → done.

## 6. Report back — and stop

In plain language, under 20 lines:

- the verdict and the one-sentence reason
- what actually got built, and what the reviewer recommended deleting
- NFR results against the budget — measured numbers, not adjectives
- any defect that looks like a privacy or compliance exposure, **at the top** —
  cross-tenant leakage, a permission bypass, a statutory identifier in a log, or
  personal data reaching a model are stop-the-line findings
- compliance obligations discharged vs still open, and any residual risk that needs a
  named human to accept it
- what is not automated and still needs a human to check
- the rollback plan
- the seven non-functional dimensions, **before vs. after**

Then **stop.** This is step 6 of the change process. Deploying is step 7 and needs its
own explicit approval — and the checklist runs **before `git commit`**, because
committing is part of the deployment pipeline. Never run `git push`, `bench migrate`,
`bench build`, `bench clear-cache`, `docker cp`, `nginx -s reload` or any `scp` to the
server on your own initiative.

Never soften a BLOCK. Never report a test run that did not happen.
