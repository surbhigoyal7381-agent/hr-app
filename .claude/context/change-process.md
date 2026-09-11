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
