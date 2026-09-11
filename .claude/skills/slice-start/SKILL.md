---
name: slice-start
description: >-
  Start a new work slice — creates docs/slices/<id>/, runs the UX opportunities scan
  and the DevOps first look, the product manager's brief (competitive analysis, Kano
  class, persona enhancements through the employee portal), a human gate, the UX
  design with a clickable prototype, a design check, then the security, privacy and
  DevOps requirements and the business analyst's functional spec with user stories.
  Every approval is the user's. Use when beginning any new feature, change or idea.
argument-hint: "[short description of the idea, feature or problem]"
---

# Start a slice

The idea: **$ARGUMENTS**

Run these steps in order. Do not skip a gate. **Every decision is the user's** — agents
recommend, flag and write; they never approve.

## 1. Set up

- Read `.claude/context/product-context.md`. If it is still full of `TODO`
  placeholders, stop and tell the user to fill it in first.
- Read the latest review in `docs/product/priorities/`. Tell the user whether this idea
  is in it, and at what rank. If it is not there, say so — it does not block, but the
  user should know.
- Look at `docs/slices/` for the highest existing number and pick the next one.
  Slice id = `NNN-short-kebab-name`. Create `docs/slices/<slice-id>/`.
- If the idea installs an existing Frappe app, tell every agent below to use
  `.claude/context/new-frappe-app-checklist.md`.

## 2. First look — run these two at the same time

- **hrms-ux-designer**, opportunities-scan mode → `01a-ux-opportunities.md`: current
  screens, how competitors' whole products handle it, and persona-by-persona ideas for
  how the employee portal could make this module better.
- **hrms-devops-engineer**, §1 Brief → `07-devops-inputs.md`: what this would add to run,
  rough run cost, red flags.

## 3. Product brief

Delegate to the **hrms-product-manager**, slice mode, with the slice id. It reads `01a`
and `07` §1 and writes `01-product-brief.md` — including the competitive analysis, the
Kano class and demand evidence, and which persona enhancements are in this slice.

## 4. HUMAN GATE — the brief

Show the user, in your own words and under 15 lines:

- the job to be done, in the user's words
- the thin slice and what is deliberately out of scope
- the competitive headline, and what we will deliberately not copy
- the Kano class (**survey or proxy**) and the demand evidence
- the persona enhancements in this slice, and those left for later
- the WOW moment and the success measures
- any DevOps red flag, the open questions and the kill criteria

Then ask plainly: **build this, change it, or drop it?** Wait for an answer.

## 5. Design and clickable prototype

Skip only for back-end-only slices, and say that you skipped it.

- Delegate to the **hrms-ux-designer**, design mode → `01b-ux-design.md` and
  `prototype-v1`. **A prototype is mandatory.**
- If the designer could not publish the prototype, **publish it yourself with the
  Artifact tool** and put the link in front of the user.
- Then delegate to the **hrms-devops-engineer**, §2 Design → `07`: page weight and load
  time on a 3G phone, media, caching, what must never be public.

## 6. HUMAN GATE — design check

Show the user, under 10 lines: **the prototype link**, the three biggest design decisions,
the DevOps §2 notes, and anything marked `⚠ DECISION`.

Ask plainly: **go with this design, change it, or drop it?** Wait for an answer.

- Every point of feedback is logged by the designer in `.claude/context/ux-learnings.md`.
- Changes produce `prototype-v2` — republish so the user sees the new version.
- After two rounds without agreement, stop and ask the user to choose between the options.

## 7. Requirements — run these two at the same time

- **hrms-security-privacy-engineer**, requirements → `01c-security-privacy-requirements.md`:
  threat model, data inventory, who must not see what, abuse cases, numbered `SEC` and
  `PRIV` requirements.
- **hrms-devops-engineer**, §3 Requirements → `07`: numbered `OPS` requirements — queues,
  rate limits, route rules, backups, monitoring, secrets.

## 8. Functional spec and user stories

Delegate to the **hrms-business-analyst** with the slice id. It reads `01`, `01b` with the
prototype, `01c` and `07` §3, and writes `02-functional-spec.md` — the epic, the user
stories, the acceptance criteria, and a traceability table that maps every brief line,
prototype screen, `SEC`, `PRIV` and `OPS` item to an acceptance criterion.

## 9. Report back

Summarise for the user in plain language:

- the gap analysis verdict — how much is configure, how much is new build, and what
  the analyst recommended dropping
- the number of user stories and their total points, and the number of acceptance criteria
- security and privacy requirements, and any not yet traced
- `OPS` recommendations **waiting for the user's decision**
- any ⚠ COMPLIANCE flags and who needs to decide them
- whether the Definition of Ready passes

If Ready fails, say so and name the missing pieces. Then tell them the next step is
`/slice-build <slice-id>`.
