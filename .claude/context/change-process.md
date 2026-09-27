# The change process — mandatory, in this order

**Source: `CLAUDE.md` §2 in this repo. That file is the authority; this one exists so
every agent applies it the same way.** If the two ever disagree, `CLAUDE.md` wins and
this file gets corrected.

Every change follows these steps **in order**. No agent skips or reorders them, however
small the change looks or however clearly the user seems to want speed.

---

## Before a single line of code

### Step 1 · Impact analysis

Do this **before opening any file for editing**. Cover all four functional dimensions
and all seven non-functional ones.

**Functional**

| Dimension | What to check |
|---|---|
| Cross-module | `alvoraa_goals`, `alvox_compensation`, `alvoraa_portal`, `hrms`, `erpnext`, `frappe` — which are touched, directly or through a hook? |
| Callers | **Grep every caller of every function being changed.** Not "probably fine" — the grep output |
| Persona | CXO, HR Manager, Employee — what changes for each? |
| HRMS domain | Leaves, attendance, payroll, appraisals, goals, compensation, org structure |

**Non-functional — state `improves` / `degrades` / `neutral` for each, with one line of
reasoning. Never leave a row blank, and never write "N/A" without saying why.**

| Dimension | What it means here |
|---|---|
| Performance | Query count, payload size, render time, N+1 risk, cache hit rate |
| Security | Permission checks, injection surface, data exposure, `ignore_permissions` scope |
| Reliability | Error handling, edge cases, graceful degradation, hook side-effects |
| Scalability | Behaviour at high employee count, multi-company, concurrent requests |
| Maintainability | Readability, coupling, duplication, testability |
| Data integrity | Stale data risk, cache invalidation correctness, transaction boundaries |
| Compliance / privacy | PII exposure, role-based data scoping |

### Step 2 · Propose the strategy

Present the approach, the risks, the trade-offs, and the path you recommend.

**The senior-developer standard, and it is the one most often missed:** anticipate the
consequences without being asked. If the change adds caching, the invalidation strategy
is in the *same* proposal. If it touches a shared doctype, the cross-module impact is
listed in the *same* proposal.

**Do not hand over a half-solution that forces the user to ask the obvious next
question.** That is the test of whether step 2 was done properly.

### Step 3 · Wait for explicit approval

Stop. The user reviews, approves, adjusts or redirects.

**"Go ahead with all changes" approves the implementation. It does not approve skipping
steps 4–7.**

---

## After implementation

### Step 4 · Run the tests

- `bench run-tests --app <app>` for any changed Python module
- Trace every affected UI flow by hand for JavaScript or HTML changes

Report what you ran and what it said — including failures. Never report a passing run
you did not execute.

### Step 5 · Senior architect review

Correctness, edge cases, regressions, security, consistency across **all** touched
files. **Re-check every non-functional dimension against the code that was actually
written**, not against the proposal.

### Step 6 · Present the findings

Test results, review outcome, non-functional assessment **before vs. after**, and a
clear statement of whether this is ready.

### Step 7 · Wait for deploy approval

Stop again. Explicit approval is required before any server command runs.

---

## The two rules people break

**1 · The checklist runs BEFORE `git commit`. Committing is part of the deployment
pipeline, not part of writing the code.**

**2 · Fixing a bug and deploying it are two separate steps. "Fix this" is not
permission to deploy.**

---

## A new requirement goes to the product manager FIRST

**Rule given 2026-09-27, after it was missed twice.**

When Surbhi raises something the product does not do yet, the first action is
`hrms-product-manager`, before any file is opened. Not after a look around, not
after the facts are gathered, not "once I know what we are dealing with".

**Why this keeps being missed:** a requirement usually arrives dressed as a
technical problem. *"Handle that in tenant configuration and handle all the
overriding cases"* names a file and a mechanism, so it reads like an engineering
task. It is not. It is a decision about what we sell and to whom, and that is the
product manager's, not the engineer's.

**How to tell the difference in one question:** does answering it change WHAT the
product does, or only HOW the existing behaviour is built? If what changes, it is
the PM's. A bug, a regression, a refactor, a performance problem and a security
hole are all HOW — keep those.

**The agent team is not only for the three skills.** `/product-priorities`,
`/slice-start` and `/slice-build` are the routine paths, but a requirement raised
in the middle of other work gets the same routing. Running the skills is not what
makes the team apply; the kind of question does.

**Groundwork is not a reason to skip the handoff — it is the handoff.** Facts
already established go INTO the brief so the agent does not start cold and does
not re-derive them at cost. What must never happen is the orchestrating session
quietly doing the product manager's thinking because the groundwork made it feel
close enough to an answer.

**On being told about it:** "why aren't you using my agents team" has now been
said twice. The second time is the signal that the rule was never written down
anywhere — so it is written here, not remembered.

---

## Commands that need explicit approval before they run

Never run any of these on your own initiative:

- `docker cp` — copying files into a container
- `bench clear-cache`, `bench migrate`, `bench build`
- `nginx -s reload`
- Any `git push` to a remote branch
- Any `scp` or file transfer to the production server

If you believe one of these is needed, **say so and wait.** An agent that deploys
because it seemed obviously right is the failure mode this section exists to prevent.

---

## How this maps onto the slice workflow

The five slice artifacts and this process are the same thing seen twice. Do not run one
instead of the other:

| Slice artifact | Change-process step |
|---|---|
| `docs/product/priorities/` → **user chooses the slices** | Deciding what is worth doing at all |
| `01a-ux-opportunities.md`, `07-devops-inputs.md` §1 | Evidence for the brief |
| `01-product-brief.md` → **human gate** | Deciding this slice is worth doing |
| `01b-ux-design.md` + clickable prototype, `07` §2 → **design check** | Agreeing what the user will see |
| `01c-security-privacy-requirements.md`, `07` §3 | Requirements that feed step 1 |
| `02-functional-spec.md` | Feeds step 1 |
| **`00-impact-analysis.md`** | **Step 1** — written by the engineer before any edit |
| Strategy in the impact analysis, with `07` §4 → **human gate** | Steps 2 and 3 |
| `03-implementation-notes.md` | Steps 4 and 6 |
| `04-test-report.md` | Step 4 |
| `05-review.md`, `06-security-review.md`, `07` §5 | Step 5 |
| → **human gate: push to dev**, then later **push to main** | Step 7 |

**Every gate is the user's.** Slices chosen, brief approved, design agreed, strategy
approved, and deploy approved — separately for dev and for main. Agents recommend; they
never approve.

---

## Learning: continuous, but never unchecked

Every agent here is expected to get better at its job over time. An agent that never
changes its own instructions is wasting what the last run cost. The UX designer already
does this through `ux-learnings.md`; the rest should too.

**But a lesson written down from one bad afternoon becomes a permanent rule nobody
questions.** That is how a wrong belief outlives the incident that produced it. Rule
given by the user on 2026-09-23: *"Make sure that the agents are confirming all their
learnings before they upgrade themselves, while definitely they should be continuously
learning."*

So before an agent writes a lesson into its own instructions or into a shared context
file:

1. **Name the evidence.** Which run, which file, which error, which commit. A lesson with
   no evidence is an opinion.
2. **Check the cause is the cause.** The obvious culprit is often the last thing that
   changed, not the thing that broke it. On 2026-09-22 three tests "failed" because
   another container shared one Redis — the tests were fine. A lesson written that
   afternoon would have blamed the tests for ever.
3. **Say what it would have prevented, and what it costs.** A rule that would not have
   caught the thing that happened is not worth carrying. A rule that makes every future
   run slower needs to earn that.
4. **Write it where it belongs.** Something true for one role goes in that agent's file.
   Something true for everyone goes in a shared context file, so all eight get it rather
   than the four that happened to be edited.
5. **Date it, and say who confirmed it.** A lesson whose evidence has since been fixed
   should be removable by the next person without archaeology.

A lesson that fails any of these is still worth recording — as a note with its evidence,
not as a rule. The difference matters: a note informs judgement, a rule replaces it.

---

## Doing the work without wasting it

**The governing principle:** Save on the clerical work. Never on the checking. This project's
thoroughness comes from a small number of habits, and none is expensive to keep. What has
been expensive is doing routine work at premium rates, running the same test suite four
times, and repeating the same paragraph in every brief.

**The one-line test:** If a task can be wrong in a way a test would not catch, it keeps the
strong model and the full process. A rebase cannot be wrong that way — git either succeeds
or conflicts. A bug fix can.

**How it goes wrong:** It starts with "this rebase is mechanical", and three weeks later
somebody is fixing a small bug on a cheap model because it looked small. Thoroughness is
never lost by decision, always by drift.

### Five cost-matched rules for how agents work

**1 · Match the model to the task.** Every agent runs on the parent's model unless told
otherwise. Reviews, security, and code judgment keep the strong model. Mechanical work —
rebases, moves, ticket updates, running known commands — goes on a cheaper one. Reason: the
redesign ran five waves through dozens of agents, all on the expensive model, even those
moving files.

**2 · Stop an agent the moment it reports.** No continued running after handoff. Two agents
in one worktree is how work gets lost — that nearly happened twice on 2026-09-25. Reason:
the same day, three agents kept running after handing back their report, and one burned a
very large amount of work before a duplicate notification gave it away.

**3 · Shared context, not every brief.** A brief carries the task, the constraints specific
to it, and the two or three lessons that bear on it. Repeating the same paragraph in twenty
briefs costs real money and buries what is specific.

**4 · Run the full test suite once, at the end.** A full suite is nearly two hours. After
each fix, the changed modules plus their neighbours answer the question. Reason: full runs
were being asked for after individual fixes, which is where hours went.

**5 · Do not ask for a measurement the machine cannot give.** Query counts and payload bytes
reproduce exactly. Wall-clock timings on this machine vary by more than the effect being
measured — an untouched call moved 46 ms to 122 ms between two sweeps minutes apart. Reason:
an agent spent an afternoon attributing a slowdown that turned out not to reproduce.

### Techniques that save real time and cost nothing

- **Reuse the fixtures.** `test044` (981 people) takes about 26 minutes; `test044s` under a
  minute. They exist. Rebuilding because it is easier than finding has happened.
- **Do not re-run what another agent just ran.** Read their log. If you doubt it, re-run that
  one thing, not everything.
- **Run independent work in parallel.** Two reviews side by side took the time of one.
- **Read the incoming diff once, and write down what came in.** Every agent re-deriving the
  same rebase is waste, and a half-read diff is how somebody's work gets undone.
- **Small commits, one concern each.** A revert that takes one command costs nothing;
  untangling a large commit costs an afternoon.

### What is never traded, whatever the budget

- A different agent reviews the work than wrote it.
- Every guard is broken on purpose to prove its test can fail. Eleven tests on this project
  proved nothing while looking green.
- Security checks the code, not the notes.
- Impact analysis before code, review after.
- What could not be proved is reported, not rounded off.
