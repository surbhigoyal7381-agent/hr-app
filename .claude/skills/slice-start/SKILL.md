---
name: slice-start
description: >-
  Start a new work slice — creates docs/slices/<id>/, runs the product manager to
  write the brief, pauses for a human decision, then runs the business analyst to
  write the functional spec. Use when beginning any new feature, change or idea.
argument-hint: "[short description of the idea, feature or problem]"
---

# Start a slice

The idea: **$ARGUMENTS**

Run these steps in order. Do not skip the human gate.

## 1. Set up

- Read `.claude/context/product-context.md`. If it is still full of `TODO`
  placeholders, stop and tell the user to fill it in first — everything downstream
  inherits its emptiness.
- Look at `docs/slices/` for the highest existing number and pick the next one.
  Slice id = `NNN-short-kebab-name` derived from the idea above.
- Create `docs/slices/<slice-id>/`.

## 2. Product brief

Delegate to the **hrms-product-manager** agent. Give it: the idea above, the slice id,
and the folder path. It writes `01-product-brief.md`.

## 3. HUMAN GATE — stop here

Show the user, in your own words and under 15 lines:

- the job to be done, in the user's words
- the thin slice and what is deliberately out of scope
- the WOW moment
- the success measures
- the open questions and the kill criteria

Then ask plainly: **build this, change it, or drop it?** Wait for an answer. Do not
run the analyst until the user has decided. A brief nobody agreed to is the most
expensive document in software.

## 3b. UX design — when the slice changes a screen

If the approved brief changes what a person sees or does on a screen — which is most
portal slices — delegate to the **hrms-ux-designer** agent with the slice id. It writes
`01b-ux-design.md` with a prototype link, and records what it learned in
`.claude/context/ux-learnings.md`.

Show the user, under 10 lines: the prototype link, the top three findings, and anything
marked `⚠ DECISION`. Ask plainly: **go with this design, change it, or drop it?** Wait
for an answer. What the user says is feedback — make sure the designer logs it.

Skip this step for back-end-only slices, and say that you skipped it.

## 4. Functional spec

Once approved, delegate to the **hrms-business-analyst** agent with the slice id. It
reads `01-product-brief.md` and, when it exists, `01b-ux-design.md`, then writes
`02-functional-spec.md`.

## 5. Report back

Summarise for the user in plain language:

- the gap analysis verdict — how much is configure, how much is new build, and what
  the analyst recommended dropping
- the number of acceptance criteria
- any ⚠ COMPLIANCE flags and who needs to decide them
- whether the Definition of Ready passes

If Ready fails, say so and name the missing pieces. Then tell them the next step is
`/slice-build <slice-id>`.
