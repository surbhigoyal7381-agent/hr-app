---
name: product-priorities
description: >-
  Review the current state of the product, pending and new features, and market
  demand, then propose a priority order using the Kano model. Runs the product
  manager, gathers usability evidence from the UX designer and effort and run-cost
  notes from the DevOps engineer, and stops for the user to decide. Use before
  starting new slices, and at least once a quarter.
argument-hint: "[optional focus, e.g. 'employee self-service' or 'learning']"
---

# Product priorities

Focus: **$ARGUMENTS** (blank means the whole product)

Run these steps in order. **The user decides what gets built. No agent does.**

## 1. Set up

- Read `.claude/context/product-context.md`. If it is still full of `TODO` placeholders,
  stop and tell the user to fill it in first.
- Create `docs/product/priorities/` if it does not exist. Use today's date,
  `YYYY-MM-DD`, in every file name below.
- Note the latest earlier priorities review, if any, so the new one can say what changed.

## 2. Current state, demand and Kano — product manager

Delegate to the **hrms-product-manager** in **priorities mode**. It writes
`<date>-kano-review.md`:

- the current state, verified against the repo — built, partial, not built
- pending features from the backlog, and new candidates
- market demand for each, every claim labelled with source and date, or `[recall — verify]`
- a Kano class for each feature, marked **survey** or **proxy**
- a draft priority order, and a Kano survey kit to test the proxies with real customers

## 3. Evidence on the top candidates — run these two at the same time

- **hrms-ux-designer** → `<date>-ux-evidence.md`: for each top candidate, the usability
  pain and opportunity seen on real screens and in earlier reviews. No prototypes at
  this stage.
- **hrms-devops-engineer** → `<date>-ops-notes.md`: for each top candidate, effort, the
  cost to run it, and the risks — extra apps, workers, storage, public pages.

## 4. Final order — product manager

Delegate to the **hrms-product-manager** again. It reads both evidence files and updates
the priority order. If the evidence changed a ranking, it says which and why. The
earlier draft is marked `status: superseded`, not overwritten.

## 5. HUMAN GATE — stop here

Show the user, in plain language and under 20 lines:

- what is built, partial and missing, in one line each area
- the top candidates in priority order, each with its Kano class, the demand evidence,
  the effort, and whether the Kano class is **survey-backed or a proxy**
- what the UX and DevOps evidence changed
- the features recommended **not** to build, and why
- whether a Kano survey with customers should run before committing

Then ask plainly: **which of these become slices, in what order?** Wait for an answer.
Do not start a slice on your own.

## 6. Report back

List the slices the user chose, and tell them the next step for each is
`/slice-start "<idea>"`.
