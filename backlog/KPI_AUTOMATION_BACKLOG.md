# Alvoraa — Objectives & KPI Product Backlog
**Version:** 2.0 — rebuilt 2026-08-24 · **Supersedes:** the 40-story KPI Automation backlog (KPIA-1..40)
**Requirements source of truth:** `OBJECTIVES_AND_KPI_SRS.md` · **Tracker:** YouTrack project KIN

---
## How to read this document
This is the **delivery view**. It carries every story, its user-story statement, points, priority, stage and the interaction guards that constrain it.
Three artefacts, three jobs — do not duplicate content between them:

| Artefact | Holds | Authority for |
|---|---|---|
| `OBJECTIVES_AND_KPI_SRS.md` | requirements, market analysis, compliance, feature interaction map | **what** and **why** |
| This document | epics, stories, points, sequencing, traceability | **planning and scope** |
| YouTrack KIN | full Given/When/Then acceptance criteria per story | **definition of done** |

> **Full acceptance criteria live in YouTrack**, where developers read them. Every story below links to its issue. Reproducing ~800 acceptance criteria here would create a second copy that drifts within a sprint.

---
## Summary

| | Count | Points |
|---|---|---|
| Epics | 17 | — |
| Stories | 132 | 698 |
| Superseded and closed | 47 (KIN-10 to KIN-56) | 223 |

### By epic

| Epic | Stage | Stories | Points | Priority | YouTrack |
|---|---|---|---|---|---|
| **A · Defect Remediation** | 0 | 7 | 33 | Critical | [KIN-57](https://kinexus.youtrack.cloud/issue/KIN-57) |
| **B · Goal and KPI Content Library** | 1 | 9 | 42 | Critical | [KIN-58](https://kinexus.youtrack.cloud/issue/KIN-58) |
| **C · Goal Plan and Cycle Governance** | 1 | 9 | 48 | Critical | [KIN-59](https://kinexus.youtrack.cloud/issue/KIN-59) |
| **D · Validation** | 1 | 6 | 18 | Major | [KIN-60](https://kinexus.youtrack.cloud/issue/KIN-60) |
| **E · Lifecycle — Approval, Locking, Revision** | 2 | 7 | 40 | Critical | [KIN-61](https://kinexus.youtrack.cloud/issue/KIN-61) |
| **F · Measurement Engine — Facts, Credits, Adapters** | 4 | 22 | 141 | Normal | [KIN-62](https://kinexus.youtrack.cloud/issue/KIN-62) |
| **G · Scoring and Explainability** | 3 | 8 | 44 | Major | [KIN-63](https://kinexus.youtrack.cloud/issue/KIN-63) |
| **H · Continuous Performance** | 6 | 8 | 37 | Major | [KIN-64](https://kinexus.youtrack.cloud/issue/KIN-64) |
| **I · Calibration and 9-Box** | 6 | 8 | 37 | Major | [KIN-65](https://kinexus.youtrack.cloud/issue/KIN-65) |
| **J · AI Assistance** | 7 | 8 | 38 | Normal | [KIN-66](https://kinexus.youtrack.cloud/issue/KIN-66) |
| **K · Assignment at Scale** | 2 | 5 | 23 | Major | [KIN-67](https://kinexus.youtrack.cloud/issue/KIN-67) |
| **L · Reporting** | 8 | 5 | 22 | Major | [KIN-68](https://kinexus.youtrack.cloud/issue/KIN-68) |
| **M · OKR Mode** | 7 | 6 | 30 | Normal | [KIN-69](https://kinexus.youtrack.cloud/issue/KIN-69) |
| **N · India-Specific Capability** | 8 | 5 | 50 | Normal | [KIN-70](https://kinexus.youtrack.cloud/issue/KIN-70) |
| **O · Entitlement and Plan Lifecycle** | 0/1 | 8 | 33 | Critical | [KIN-71](https://kinexus.youtrack.cloud/issue/KIN-71) |
| **P · Positions and Effective Dating** | 5 | 6 | 36 | Normal | [KIN-72](https://kinexus.youtrack.cloud/issue/KIN-72) |
| **Q · Trust, Dispute and Anti-Gaming** | 5 | 5 | 26 | Normal | [KIN-73](https://kinexus.youtrack.cloud/issue/KIN-73) |

### By stage

| Stage | Stories | Points | Content |
|---|---|---|---|
| **0** | 9 | 46 | Defects, entitlement, definition audit — starts immediately |
| **1** | 30 | 130 | Authoring foundation: library, goal plan, validation, plan lifecycle |
| **2** | 11 | 58 | Governance and scale: lifecycle, bulk assignment |
| **3** | 8 | 44 | Scoring and explainability |
| **4** | 21 | 136 | Measurement engine |
| **5** | 11 | 62 | Positions, trust and dispute |
| **6** | 16 | 74 | Continuous performance and calibration |
| **7** | 14 | 68 | OKR mode and AI |
| **8** | 12 | 80 | India-specific, reporting, Logic ERP |

---
## Sequencing rules

Hard ordering constraints from SRS §8. A stage is not done until its guards are demonstrated, not just its stories closed.

```
DEF-2 fix ──must ship with── C-2 (direction on Individual Goal)
FR-E1     ──must ship with── C-1 (separate approval_state field)
D-13      ──must precede──── FR-A4 AND Stage 4
FR-A5     ──must anticipate─ FR-F9 (build the shared recompute once)
FR-G1     ──must cover────── goals and KPIs together
FR-P1     ──must update───── fact and credit permission queries
FR-O4     ──is permanent──── independent of FR-O5
D-1       ──must precede──── any calibration work
```

### Open decisions blocking work

| Decision | Blocks | Recommendation |
|---|---|---|
| **D-13** — single write path for goal actuals | FR-A4, all of Stage 4 | `Goal Evidence` is the single path; remove `Goal Progress Update`, do not unify |
| **D-1** — which calibration implementation survives | all of Epic I | Keep the live one; hold PMS routes behind a flag until exercised on dev |
| **D-19** — may a downgraded tenant read history | FR-O2 scope | Read-only retention |
| **D-14** — is `Goal Check-In` referenced anywhere | FR-H1 shape | One grep settles it |

---
## INVEST compliance

Every story below was written against INVEST. Where a principle was deliberately traded, it is noted on the story.

| Principle | How it is met | Known exceptions |
|---|---|---|
| **Independent** | Stories within an epic can be worked in most orders | Eight documented pairs must ship together — see Sequencing rules. Treating these as independent is the failure mode this backlog exists to prevent |
| **Negotiable** | Each states intent and acceptance, not implementation | FR-J6 and FR-J4 are prohibitions and are **not** negotiable |
| **Valuable** | Each names a role and the value to them | FR-P6 is a recorded alternative, not planned work |
| **Estimable** | All carry points | FR-F12 and FR-N5 need their integration surface confirmed before their estimates are trustworthy |
| **Small** | 87 of 132 are 5 points or fewer | Five at 13 points (FR-F11, F12, F16, N1, N5) should be split at sprint planning |
| **Testable** | Every acceptance criterion is Given/When/Then in YouTrack | Nine defect stories are readings of source, not execution — each requires a failing test **before** the fix |

---
## Stories

---

### Epic A · Defect Remediation

**[KIN-57](https://kinexus.youtrack.cloud/issue/KIN-57)** · Stage 0 · 7 stories · 33 points · Critical

Stop the system producing wrong numbers before anything is built on top of it.

**Guards:** C-2 (FR-A2+A7 ship together) · C-3 (FR-A4 blocked on D-13) · C-6 (FR-A5 builds the shared recompute) · C-11 (FR-A3 must agree with FR-L5)

| ID | Story | Pts | Pri | Stage |
|---|---|---|---|---|
| [FR-A1](https://kinexus.youtrack.cloud/issue/KIN-74) | Weightage budget counts objectives alongside KPIs | 3 | Critical | 0 |
| [FR-A2](https://kinexus.youtrack.cloud/issue/KIN-75) | Attainment distinguishes unmeasured from measured-as-zero | 8 | Critical | 0 |
| [FR-A3](https://kinexus.youtrack.cloud/issue/KIN-76) | Cascade aggregation counts each level of the tree once | 5 | Critical | 0 |
| [FR-A4](https://kinexus.youtrack.cloud/issue/KIN-77) | Resolve the orphan Goal Progress Update table | 3 | Major | 1 |
| [FR-A5](https://kinexus.youtrack.cloud/issue/KIN-78) | Recalculation writes only on change and commits in batches | 8 | Major | 0 |
| [FR-A6](https://kinexus.youtrack.cloud/issue/KIN-79) | Draft items do not consume the weightage budget | 1 | Minor | 0 |
| [FR-A7](https://kinexus.youtrack.cloud/issue/KIN-80) | Individual Goal gains direction and shares one attainment function | 5 | Critical | 0 |

#### FR-A1 · Weightage budget counts objectives alongside KPIs

`Critical` · 3 points · Stage 0 · [KIN-74](https://kinexus.youtrack.cloud/issue/KIN-74)

> **As a** HR Manager setting up an employee's cycle
> **I want** the weightage check to count their objectives as well as their KPIs
> **So that** I find out I am over 100% while I am still authoring, not when the manager tries to close the cycle

DEF-1. Re-scopes KPIA-46, which assumed no enforcement existed — it does.

#### FR-A2 · Attainment distinguishes unmeasured from measured-as-zero

`Critical` · 8 points · Stage 0 · [KIN-75](https://kinexus.youtrack.cloud/issue/KIN-75)

> **As a** employee with a zero-is-best target
> **I want** achieving zero to score as success
> **So that** a perfect safety, defect or complaint record is not recorded as a failed KPI

DEF-2. **Guard C-2 — ships with FR-A7.** Affects every zero-is-best KPI.

#### FR-A3 · Cascade aggregation counts each level of the tree once

`Critical` · 5 points · Stage 0 · [KIN-76](https://kinexus.youtrack.cloud/issue/KIN-76)

> **As a** CXO reading a cascade roll-up
> **I want** the aggregate to count each objective once
> **So that** the company progress figure is not halved by the shape of the org

DEF-3. Guard C-11.

#### FR-A4 · Resolve the orphan Goal Progress Update table

`Major` · 3 points · Stage 1 · [KIN-77](https://kinexus.youtrack.cloud/issue/KIN-77)

> **As a** employee logging progress against an objective
> **I want** an approved progress entry to actually move the number
> **So that** I am not filling in a form that does nothing

DEF-4. **BLOCKED on D-13.** Guard C-3.

#### FR-A5 · Recalculation writes only on change and commits in batches

`Major` · 8 points · Stage 0 · [KIN-78](https://kinexus.youtrack.cloud/issue/KIN-78)

> **As a** platform operator
> **I want** the hourly recalculation to do nothing when nothing has changed
> **So that** a quiet tenant does not generate 28,800 pointless audit rows a day

DEF-5. **Guard C-6 — build the shared recompute Stage 4 will call.**

#### FR-A6 · Draft items do not consume the weightage budget

`Minor` · 1 points · Stage 0 · [KIN-79](https://kinexus.youtrack.cloud/issue/KIN-79)

> **As a** HR Manager drafting alternative KPIs
> **I want** drafts to sit outside the 100% ceiling
> **So that** I can prepare two versions and choose between them

DEF-6. Good first ticket.

#### FR-A7 · Individual Goal gains direction and shares one attainment function

`Critical` · 5 points · Stage 0 · [KIN-80](https://kinexus.youtrack.cloud/issue/KIN-80)

> **As a** employee whose objective is to reduce something
> **I want** to express lower-is-better on an objective, not only on a KPI
> **So that** a cost-reduction or cycle-time objective can be scored at all

**Guard C-2 — ships with FR-A2.** Prerequisite of Epic F.

---

### Epic B · Goal and KPI Content Library

**[KIN-58](https://kinexus.youtrack.cloud/issue/KIN-58)** · Stage 1 · 9 stories · 42 points · Critical

HR maintains reusable goal content so no employee's goal is typed from scratch.

**Guards:** C-12 — content and computation libraries joined by nullable FK, never merged

| ID | Story | Pts | Pri | Stage |
|---|---|---|---|---|
| [FR-B1](https://kinexus.youtrack.cloud/issue/KIN-89) | Maintain a Goal Library as a categorised tree of templates | 8 | Critical | 1 |
| [FR-B2](https://kinexus.youtrack.cloud/issue/KIN-90) | Scope templates by company, department, designation and job family | 5 | Major | 1 |
| [FR-B3](https://kinexus.youtrack.cloud/issue/KIN-91) | Templates are Inactive by default and published deliberately | 2 | Major | 1 |
| [FR-B4](https://kinexus.youtrack.cloud/issue/KIN-92) | Export and re-import a library as typed CSV | 8 | Major | 1 |
| [FR-B5](https://kinexus.youtrack.cloud/issue/KIN-93) | Template edits never alter goals already created from them | 5 | Major | 1 |
| [FR-B6](https://kinexus.youtrack.cloud/issue/KIN-94) | Library identity is a stable GUID, not a name | 3 | Normal | 1 |
| [FR-B7](https://kinexus.youtrack.cloud/issue/KIN-95) | Bind a Goal Template to a Metric Definition by nullable FK | 3 | Major | 1 |
| [FR-B8](https://kinexus.youtrack.cloud/issue/KIN-96) | Seed a starter goal library and metric library in one operation | 5 | Major | 1 |
| [FR-B9](https://kinexus.youtrack.cloud/issue/KIN-97) | Library stays responsive at a thousand templates | 3 | Normal | 1 |

#### FR-B1 · Maintain a Goal Library as a categorised tree of templates

`Critical` · 8 points · Stage 1 · [KIN-89](https://kinexus.youtrack.cloud/issue/KIN-89)

> **As a** HR Manager
> **I want** a curated catalogue of goal content organised by category
> **So that** a manager setting goals picks from vetted content instead of typing from scratch

Gap G1 confirmed — zero matches for template/library/catalog in alvoraa_goals.

#### FR-B2 · Scope templates by company, department, designation and job family

`Major` · 5 points · Stage 1 · [KIN-90](https://kinexus.youtrack.cloud/issue/KIN-90)

> **As a** HR Manager in a multi-company group
> **I want** each template to declare who it applies to
> **So that** a warehouse supervisor is not offered a template written for a regional sales head

Oracle's per-entry scoping, avoiding a library per population.

#### FR-B3 · Templates are Inactive by default and published deliberately

`Major` · 2 points · Stage 1 · [KIN-91](https://kinexus.youtrack.cloud/issue/KIN-91)

> **As a** HR Manager drafting library content
> **I want** a new template to be invisible until I publish it
> **So that** a half-written template cannot be assigned to 800 people by accident

Small, prevents a specific expensive accident.

#### FR-B4 · Export and re-import a library as typed CSV

`Major` · 8 points · Stage 1 · [KIN-92](https://kinexus.youtrack.cloud/issue/KIN-92)

> **As a** HR Manager maintaining several hundred templates
> **I want** to edit the library as a file
> **So that** I can bulk-author and review changes in a diff

SAP's typed CSV. The file becomes the reviewable artefact.

#### FR-B5 · Template edits never alter goals already created from them

`Major` · 5 points · Stage 1 · [KIN-93](https://kinexus.youtrack.cloud/issue/KIN-93)

> **As a** employee mid-cycle
> **I want** my goal to stay as it was agreed
> **So that** an HR edit to library content cannot silently change what I am measured on

Data integrity, and a grievance risk if omitted.

#### FR-B6 · Library identity is a stable GUID, not a name

`Normal` · 3 points · Stage 1 · [KIN-94](https://kinexus.youtrack.cloud/issue/KIN-94)

> **As a** HR Manager renaming a library
> **I want** the rename to break nothing
> **So that** presentation and identity are not the same thing

Binding by name is the mistake this avoids.

#### FR-B7 · Bind a Goal Template to a Metric Definition by nullable FK

`Major` · 3 points · Stage 1 · [KIN-95](https://kinexus.youtrack.cloud/issue/KIN-95)

> **As a** HR Manager
> **I want** to say both what a goal measures and how it is computed, in one place
> **So that** authoring and measurement are configured together instead of drifting apart

**Guard C-12.** See SRS §4.4 — the original merge instruction was wrong.

#### FR-B8 · Seed a starter goal library and metric library in one operation

`Major` · 5 points · Stage 1 · [KIN-96](https://kinexus.youtrack.cloud/issue/KIN-96)

> **As a** new customer
> **I want** usable goal content on day one
> **So that** I am not staring at an empty catalogue during implementation

Merges legacy KPIA-4 (KIN-20) without conflating the two objects.

#### FR-B9 · Library stays responsive at a thousand templates

`Normal` · 3 points · Stage 1 · [KIN-97](https://kinexus.youtrack.cloud/issue/KIN-97)

> **As a** manager creating a goal
> **I want** the template picker to open immediately
> **So that** goal-setting season does not stall on a slow screen

SAP's published ceiling: 1,000 entries per library.

---

### Epic C · Goal Plan and Cycle Governance

**[KIN-59](https://kinexus.youtrack.cloud/issue/KIN-59)** · Stage 1 · 9 stories · 48 points · Critical

The rules of a cycle are declared configuration, not code or convention.

**Guards:** C-5 — goal periods and freeze must agree; freeze at the smaller unit

| ID | Story | Pts | Pri | Stage |
|---|---|---|---|---|
| [FR-C1](https://kinexus.youtrack.cloud/issue/KIN-98) | Define a Goal Plan as the per-cycle rulebook | 8 | Critical | 1 |
| [FR-C2](https://kinexus.youtrack.cloud/issue/KIN-99) | Separate the goal-setting window from the execution window | 8 | Critical | 1 |
| [FR-C3](https://kinexus.youtrack.cloud/issue/KIN-100) | Goal periods run independently of the appraisal cycle | 5 | Major | 1 |
| [FR-C4](https://kinexus.youtrack.cloud/issue/KIN-101) | Weights-must-total-100 is a per-plan toggle, default on | 3 | Major | 1 |
| [FR-C5](https://kinexus.youtrack.cloud/issue/KIN-102) | Support probation, project and per-business-unit cycles | 5 | Major | 1 |
| [FR-C6](https://kinexus.youtrack.cloud/issue/KIN-103) | Per-employee goal-setting readiness before the cycle opens | 5 | Major | 1 |
| [FR-C7](https://kinexus.youtrack.cloud/issue/KIN-104) | Field permissions declared as field x principal x plan state | 8 | Major | 1 |
| [FR-C8](https://kinexus.youtrack.cloud/issue/KIN-105) | Unambiguous conflict resolution for hidden and required fields | 3 | Major | 1 |
| [FR-C9](https://kinexus.youtrack.cloud/issue/KIN-106) | Each constraint is configurable as advisory or blocking | 3 | Normal | 1 |

#### FR-C1 · Define a Goal Plan as the per-cycle rulebook

`Critical` · 8 points · Stage 1 · [KIN-98](https://kinexus.youtrack.cloud/issue/KIN-98)

> **As a** HR Manager opening a cycle
> **I want** one object that declares the rules for that cycle
> **So that** governance is configuration a customer can see, not behaviour buried in code

Gap G2 confirmed. Alvoraa Cycle Config holds UI config only.

#### FR-C2 · Separate the goal-setting window from the execution window

`Critical` · 8 points · Stage 1 · [KIN-99](https://kinexus.youtrack.cloud/issue/KIN-99)

> **As a** HR Manager
> **I want** goal authoring to close while progress tracking stays open
> **So that** goals are locked after Q1 planning is enforced rather than requested

**The highest-leverage governance feature in the study.** Oracle 25D semantics exactly.

#### FR-C3 · Goal periods run independently of the appraisal cycle

`Major` · 5 points · Stage 1 · [KIN-100](https://kinexus.youtrack.cloud/issue/KIN-100)

> **As a** HR Manager running quarterly objectives inside an annual review
> **I want** goal periods that are not the same thing as the appraisal cycle
> **So that** a company that plans quarterly and appraises annually can do both

D-7. **Guard C-5** — interacts with FR-Q2 freeze.

#### FR-C4 · Weights-must-total-100 is a per-plan toggle, default on

`Major` · 3 points · Stage 1 · [KIN-101](https://kinexus.youtrack.cloud/issue/KIN-101)

> **As a** HR Manager whose company does not normalise weights
> **I want** to switch the 100% rule off for my plan
> **So that** an upgrade does not break a working process

D-6. AC4 is the one people forget: turning the rule off still needs a defined score.

#### FR-C5 · Support probation, project and per-business-unit cycles

`Major` · 5 points · Stage 1 · [KIN-102](https://kinexus.youtrack.cloud/issue/KIN-102)

> **As a** HR Manager
> **I want** to run a three-month probation review alongside the annual cycle
> **So that** new joiners are reviewed on the schedule their employment follows

FLOOR #5. Concurrent-cycle weightage isolation is the risky part.

#### FR-C6 · Per-employee goal-setting readiness before the cycle opens

`Major` · 5 points · Stage 1 · [KIN-103](https://kinexus.youtrack.cloud/issue/KIN-103)

> **As a** HR Manager about to open a cycle
> **I want** to see who is not ready and why
> **So that** I chase eight people now instead of discovering it at appraisal time

Legacy FR-9.

#### FR-C7 · Field permissions declared as field x principal x plan state

`Major` · 8 points · Stage 1 · [KIN-104](https://kinexus.youtrack.cloud/issue/KIN-104)

> **As a** HR Manager
> **I want** to declare who can edit which field at which stage
> **So that** post-approval editing is restricted without building a workflow engine

permission = f(role, field, plan_state). Role dimension collapsed to four principals.

#### FR-C8 · Unambiguous conflict resolution for hidden and required fields

`Major` · 3 points · Stage 1 · [KIN-105](https://kinexus.youtrack.cloud/issue/KIN-105)

> **As a** support engineer
> **I want** field conflicts to resolve by a rule I can state in one sentence
> **So that** why can't this user see the target field is a two-minute answer

Workday's rules verbatim: hide needs unanimity, required needs one, required beats hidden.

#### FR-C9 · Each constraint is configurable as advisory or blocking

`Normal` · 3 points · Stage 1 · [KIN-106](https://kinexus.youtrack.cloud/issue/KIN-106)

> **As a** HR Manager
> **I want** to decide which rules warn and which rules stop the save
> **So that** guidance and policy are not the same thing

Avoids SAP KBA 2457856's documented soft/hard confusion.

---

### Epic D · Validation

**[KIN-60](https://kinexus.youtrack.cloud/issue/KIN-60)** · Stage 1 · 6 stories · 18 points · Major

A goal that breaks policy cannot be saved, on any path.

| ID | Story | Pts | Pri | Stage |
|---|---|---|---|---|
| [FR-D1](https://kinexus.youtrack.cloud/issue/KIN-107) | All validation runs in the controller, guarding every entry path | 5 | Critical | 1 |
| [FR-D2](https://kinexus.youtrack.cloud/issue/KIN-108) | Numeric goals require a target; lower-is-better requires a baseline | 3 | Major | 1 |
| [FR-D3](https://kinexus.youtrack.cloud/issue/KIN-109) | Goal period must sit inside the plan period and end after it starts | 2 | Major | 1 |
| [FR-D4](https://kinexus.youtrack.cloud/issue/KIN-110) | Warn when goal count falls outside the plan's range | 2 | Normal | 1 |
| [FR-D5](https://kinexus.youtrack.cloud/issue/KIN-111) | Flag goals that cannot actually be measured | 3 | Normal | 1 |
| [FR-D6](https://kinexus.youtrack.cloud/issue/KIN-112) | Report scorecard perspective coverage per employee | 3 | Normal | 1 |

#### FR-D1 · All validation runs in the controller, guarding every entry path

`Critical` · 5 points · Stage 1 · [KIN-107](https://kinexus.youtrack.cloud/issue/KIN-107)

> **As a** compliance-minded HR Manager
> **I want** the same rules to apply however a goal is created
> **So that** the desk and the API are not a way around the policy the portal enforces

Four entry paths: portal, desk, REST, bulk import.

#### FR-D2 · Numeric goals require a target; lower-is-better requires a baseline

`Major` · 3 points · Stage 1 · [KIN-108](https://kinexus.youtrack.cloud/issue/KIN-108)

> **As a** employee
> **I want** to be told at save time that my goal cannot be measured
> **So that** I do not discover at appraisal time that it scores zero

Legacy FR-11. Extends the existing KPI check to objectives.

#### FR-D3 · Goal period must sit inside the plan period and end after it starts

`Major` · 2 points · Stage 1 · [KIN-109](https://kinexus.youtrack.cloud/issue/KIN-109)

> **As a** HR Manager
> **I want** goal dates constrained to the cycle they belong to
> **So that** a goal cannot quietly measure a window nobody is reviewing

Legacy FR-12.

#### FR-D4 · Warn when goal count falls outside the plan's range

`Normal` · 2 points · Stage 1 · [KIN-110](https://kinexus.youtrack.cloud/issue/KIN-110)

> **As a** employee setting goals
> **I want** to be told when I have too many or too few
> **So that** I notice, without being blocked by guidance

Legacy FR-13. Goal effects attenuate with complexity — a count range is a crude proxy.

#### FR-D5 · Flag goals that cannot actually be measured

`Normal` · 3 points · Stage 1 · [KIN-111](https://kinexus.youtrack.cloud/issue/KIN-111)

> **As a** manager approving goals
> **I want** unmeasurable goals surfaced before I approve them
> **So that** I am not asked at year end to rate improve sales out of five

Legacy FR-14. Deterministic checks first; FR-J2 adds judgement later.

#### FR-D6 · Report scorecard perspective coverage per employee

`Normal` · 3 points · Stage 1 · [KIN-112](https://kinexus.youtrack.cloud/issue/KIN-112)

> **As a** HR Manager
> **I want** to see who has a purely financial scorecard
> **So that** the Balanced Scorecard is actually balanced

Builds on an existing strength — category is already a field, not a tag.

---

### Epic E · Lifecycle — Approval, Locking, Revision

**[KIN-61](https://kinexus.youtrack.cloud/issue/KIN-61)** · Stage 2 · 7 stories · 40 points · Critical

An approved goal cannot be quietly changed, and every definition change is on the record.

**Guards:** C-1 (approval_state must not live in status) · C-4 (scope fields are locked)

| ID | Story | Pts | Pri | Stage |
|---|---|---|---|---|
| [FR-E1](https://kinexus.youtrack.cloud/issue/KIN-113) | Add a Pending Approval state in a separate approval_state field | 8 | Critical | 2 |
| [FR-E2](https://kinexus.youtrack.cloud/issue/KIN-114) | Single-step manager approval with the plan locked while pending | 5 | Critical | 2 |
| [FR-E3](https://kinexus.youtrack.cloud/issue/KIN-115) | Lock definition fields on approval, including measurement scope | 8 | Critical | 2 |
| [FR-E4](https://kinexus.youtrack.cloud/issue/KIN-116) | Mid-cycle revision request with reason, approval and versioning | 8 | Major | 2 |
| [FR-E5](https://kinexus.youtrack.cloud/issue/KIN-117) | No Longer Pursued as a terminal state, deletion prohibited | 3 | Major | 2 |
| [FR-E6](https://kinexus.youtrack.cloud/issue/KIN-118) | Audit every change to a goal definition | 5 | Major | 0 |
| [FR-E7](https://kinexus.youtrack.cloud/issue/KIN-119) | Freeze cycle settings once the cycle launches | 3 | Major | 2 |

#### FR-E1 · Add a Pending Approval state in a separate approval_state field

`Critical` · 8 points · Stage 2 · [KIN-113](https://kinexus.youtrack.cloud/issue/KIN-113)

> **As a** HR Manager
> **I want** goals to require approval before they can be scored
> **So that** what an employee is measured on has been agreed by someone

**Guard C-1 — the sharpest interaction in the specification.** _set_status would silently re-activate a pending KPI.

#### FR-E2 · Single-step manager approval with the plan locked while pending

`Critical` · 5 points · Stage 2 · [KIN-114](https://kinexus.youtrack.cloud/issue/KIN-114)

> **As a** manager
> **I want** to approve my report's goals in one action
> **So that** goal-setting completes in a conversation rather than a routing workflow

Keep the lock, cut the chain.

#### FR-E3 · Lock definition fields on approval, including measurement scope

`Critical` · 8 points · Stage 2 · [KIN-115](https://kinexus.youtrack.cloud/issue/KIN-115)

> **As a** employee
> **I want** my agreed target to be unchangeable without a visible process
> **So that** the goalposts cannot move quietly after I have started

**Guard C-4** — scope fields change the number and must be locked.

#### FR-E4 · Mid-cycle revision request with reason, approval and versioning

`Major` · 8 points · Stage 2 · [KIN-116](https://kinexus.youtrack.cloud/issue/KIN-116)

> **As a** manager whose team was reorganised in month five
> **I want** a way to change an agreed target that leaves a record
> **So that** a legitimate change does not require unlocking everything

**Highest-conviction whitespace — not one of ten India vendors documents this.**

#### FR-E5 · No Longer Pursued as a terminal state, deletion prohibited

`Major` · 3 points · Stage 2 · [KIN-117](https://kinexus.youtrack.cloud/issue/KIN-117)

> **As a** HR Manager
> **I want** an abandoned goal marked rather than deleted
> **So that** the record of what was agreed survives the decision to stop

Oracle's action matrix. AC3 (weight redistribution) is hit immediately after go-live.

#### FR-E6 · Audit every change to a goal definition

`Major` · 5 points · Stage 0 · [KIN-118](https://kinexus.youtrack.cloud/issue/KIN-118)

> **As a** HR Manager defending a rating in a grievance
> **I want** a chronological record of every change to the goal itself
> **So that** I can show what was agreed, when it changed, who changed it and why

Existing audit covers progress only. Scheduled in Stage 0 — cheap, and everything later benefits.

#### FR-E7 · Freeze cycle settings once the cycle launches

`Major` · 3 points · Stage 2 · [KIN-119](https://kinexus.youtrack.cloud/issue/KIN-119)

> **As a** HR Manager
> **I want** the rating scale and form structure fixed at launch
> **So that** everyone in the cycle is measured on the same instrument

FLOOR #12. Keka is the only vendor documenting this precisely.

---

### Epic F · Measurement Engine — Facts, Credits, Adapters

**[KIN-62](https://kinexus.youtrack.cloud/issue/KIN-62)** · Stage 4 · 22 stories · 141 points · Normal

KPI actuals derive from source-of-record transactions, with a document-level audit trail.

**Guards:** C-3 (D-13 first) · C-6 (one recompute) · C-10 (fuzzy detector off synced path) · D-3=Both

| ID | Story | Pts | Pri | Stage |
|---|---|---|---|---|
| [FR-F1](https://kinexus.youtrack.cloud/issue/KIN-120) | Define a reusable metric in the metric library without a developer | 8 | Critical | 4 |
| [FR-F2](https://kinexus.youtrack.cloud/issue/KIN-121) | Preview a metric against live data before saving it | 5 | Major | 4 |
| [FR-F3](https://kinexus.youtrack.cloud/issue/KIN-122) | Bind a metric to a KPI or an Individual Goal with scope filters | 5 | Critical | 4 |
| [FR-F4](https://kinexus.youtrack.cloud/issue/KIN-123) | Turn automation off for an item and revert to manual entry | 3 | Major | 4 |
| [FR-F5](https://kinexus.youtrack.cloud/issue/KIN-124) | Scheduled jobs ingest source transactions as immutable KPI Facts | 8 | Critical | 4 |
| [FR-F6](https://kinexus.youtrack.cloud/issue/KIN-125) | Re-running a sync never double-counts | 5 | Critical | 4 |
| [FR-F7](https://kinexus.youtrack.cloud/issue/KIN-126) | Cancelled or amended documents post a reversal, never an edit | 5 | Major | 4 |
| [FR-F8](https://kinexus.youtrack.cloud/issue/KIN-127) | Unmappable owners land in a visible queue and can be resolved | 8 | Critical | 4 |
| [FR-F9](https://kinexus.youtrack.cloud/issue/KIN-128) | Log every sync run and recompute affected items once, bottom-up | 8 | Critical | 4 |
| [FR-F10](https://kinexus.youtrack.cloud/issue/KIN-129) | An unreachable source holds the last value and never guesses | 3 | Major | 4 |
| [FR-F11](https://kinexus.youtrack.cloud/issue/KIN-130) | Four calculation shapes aggregate correctly, storing components | 13 | Critical | 4 |
| [FR-F12](https://kinexus.youtrack.cloud/issue/KIN-131) | Five adapter patterns normalise to one fact shape | 13 | Major | 4 |
| [FR-F13](https://kinexus.youtrack.cloud/issue/KIN-132) | Outbound polling only, credentials encrypted per company | 5 | Critical | 4 |
| [FR-F14](https://kinexus.youtrack.cloud/issue/KIN-133) | See source documents behind a number and drill team to person | 8 | Major | 4 |
| [FR-F15](https://kinexus.youtrack.cloud/issue/KIN-134) | Synced evidence auto-approves; manual keeps manager review | 3 | Major | 4 |
| [FR-F16](https://kinexus.youtrack.cloud/issue/KIN-135) | Measure a manager on their team's activity, at any depth | 13 | Critical | 4 |
| [FR-F17](https://kinexus.youtrack.cloud/issue/KIN-136) | Honour split credit on shared deals | 5 | Major | 4 |
| [FR-F18](https://kinexus.youtrack.cloud/issue/KIN-137) | Roll sales up the Sales Person tree, not the HR reporting line | 5 | Major | 4 |
| [FR-F19](https://kinexus.youtrack.cloud/issue/KIN-138) | Company and BU reports read facts, never the sum of item actuals | 5 | Critical | 4 |
| [FR-F20](https://kinexus.youtrack.cloud/issue/KIN-139) | Show quota coverage when targets are cascaded | 5 | Major | 4 |
| [FR-F21](https://kinexus.youtrack.cloud/issue/KIN-140) | Reconcile external ERP totals against computed item totals | 5 | Major | 8 |
| [FR-F22](https://kinexus.youtrack.cloud/issue/KIN-141) | Sync runs automatically, with visible freshness per item | 3 | Major | 4 |

#### FR-F1 · Define a reusable metric in the metric library without a developer

`Critical` · 8 points · Stage 4 · [KIN-120](https://kinexus.youtrack.cloud/issue/KIN-120)

> **As a** HR Manager
> **I want** to define a metric once and reuse it across many goals
> **So that** adding a new automated KPI is configuration rather than a code change

D-4. The extensibility point for the whole engine. Replaces KPIA-1.

#### FR-F2 · Preview a metric against live data before saving it

`Major` · 5 points · Stage 4 · [KIN-121](https://kinexus.youtrack.cloud/issue/KIN-121)

> **As a** HR Manager
> **I want** to see the rows a metric would produce before attaching it to anyone
> **So that** a wrong filter is caught before it silently feeds an appraisal

Replaces KPIA-2. **Do not descope** — highest-leverage story for data quality.

#### FR-F3 · Bind a metric to a KPI or an Individual Goal with scope filters

`Critical` · 5 points · Stage 4 · [KIN-122](https://kinexus.youtrack.cloud/issue/KIN-122)

> **As a** HR Manager
> **I want** to attach a metric to either a KPI or an objective
> **So that** both kinds of measured item can be automated

**D-3 = Both.** The superseded backlog covered only KPI. Depends on FR-A7.

#### FR-F4 · Turn automation off for an item and revert to manual entry

`Major` · 3 points · Stage 4 · [KIN-123](https://kinexus.youtrack.cloud/issue/KIN-123)

> **As a** HR Manager
> **I want** to switch a specific item back to manual
> **So that** one misbehaving integration does not force me to abandon automation

Replaces KPIA-5. ~15% of a scorecard should stay manual by design.

#### FR-F5 · Scheduled jobs ingest source transactions as immutable KPI Facts

`Critical` · 8 points · Stage 4 · [KIN-124](https://kinexus.youtrack.cloud/issue/KIN-124)

> **As a** platform operator
> **I want** source transactions pulled on a schedule into an append-only fact table
> **So that** every number can be traced to the document that produced it

Replaces KPIA-6. Hourly incremental, nightly reconcile, nightly snapshot.

#### FR-F6 · Re-running a sync never double-counts

`Critical` · 5 points · Stage 4 · [KIN-125](https://kinexus.youtrack.cloud/issue/KIN-125)

> **As a** platform operator
> **I want** to re-run any sync window safely
> **So that** a retry or replay cannot inflate someone's appraisal score

**Guard C-10 — fuzzy duplicate detection must never run on synced facts.**

#### FR-F7 · Cancelled or amended documents post a reversal, never an edit

`Major` · 5 points · Stage 4 · [KIN-126](https://kinexus.youtrack.cloud/issue/KIN-126)

> **As a** manager whose report's number dropped
> **I want** to see why it dropped
> **So that** a restatement is explainable rather than mysterious

Replaces KPIA-8. The progress log reads as a ledger.

#### FR-F8 · Unmappable owners land in a visible queue and can be resolved

`Critical` · 8 points · Stage 4 · [KIN-127](https://kinexus.youtrack.cloud/issue/KIN-127)

> **As a** HR Manager
> **I want** every record the engine could not attribute to appear in a queue
> **So that** nothing is silently dropped from someone's score

Replaces KPIA-9 and KPIA-10. **Never name matching.**

#### FR-F9 · Log every sync run and recompute affected items once, bottom-up

`Critical` · 8 points · Stage 4 · [KIN-128](https://kinexus.youtrack.cloud/issue/KIN-128)

> **As a** platform operator
> **I want** each run observable and its recompute bounded
> **So that** month-end does not take the tenant down

**Guard C-6 — same function as FR-A5.** Replaces KPIA-11 and KPIA-27.

#### FR-F10 · An unreachable source holds the last value and never guesses

`Major` · 3 points · Stage 4 · [KIN-129](https://kinexus.youtrack.cloud/issue/KIN-129)

> **As a** employee
> **I want** my number to stay where it was when an integration breaks
> **So that** an outage elsewhere does not make my performance look worse

Replaces KPIA-12. Never zero — zero is indistinguishable from poor performance.

#### FR-F11 · Four calculation shapes aggregate correctly, storing components

`Critical` · 13 points · Stage 4 · [KIN-130](https://kinexus.youtrack.cloud/issue/KIN-130)

> **As a** CXO reading a company defect rate
> **I want** the number to be arithmetically correct
> **So that** I am not looking at an average of averages

Merges KPIA-13 to 16. AVG(percentages) is the worst failure mode — nothing looks broken.

#### FR-F12 · Five adapter patterns normalise to one fact shape

`Major` · 13 points · Stage 4 · [KIN-131](https://kinexus.youtrack.cloud/issue/KIN-131)

> **As a** platform engineer
> **I want** every source to arrive through an adapter producing the same fact shape
> **So that** adding a source is configuration rather than a project

Replaces KPIA-32/33. Direct SQL is a differentiator — only Profit.co offers it.

#### FR-F13 · Outbound polling only, credentials encrypted per company

`Critical` · 5 points · Stage 4 · [KIN-132](https://kinexus.youtrack.cloud/issue/KIN-132)

> **As a** customer IT manager
> **I want** the integration to require no inbound firewall rule
> **So that** security review takes two weeks rather than two months

Replaces KPIA-34. AC3 (no credentials in tracebacks) needs an explicit test.

#### FR-F14 · See source documents behind a number and drill team to person

`Major` · 8 points · Stage 4 · [KIN-133](https://kinexus.youtrack.cloud/issue/KIN-133)

> **As a** employee
> **I want** to see which documents produced my number
> **So that** I can check it, and challenge it if it is wrong

Replaces KPIA-17 and KPIA-23. Underpins the dispute flow.

#### FR-F15 · Synced evidence auto-approves; manual keeps manager review

`Major` · 3 points · Stage 4 · [KIN-134](https://kinexus.youtrack.cloud/issue/KIN-134)

> **As a** manager
> **I want** to stop confirming numbers the ERP already knows
> **So that** my review time goes to judgement rather than data entry

Replaces KPIA-18. The ERP is the system of record.

#### FR-F16 · Measure a manager on their team's activity, at any depth

`Critical` · 13 points · Stage 4 · [KIN-135](https://kinexus.youtrack.cloud/issue/KIN-135)

> **As a** sales director who does not carry a personal book
> **I want** my KPI measured on my whole team's activity
> **So that** I have a real number instead of a manual estimate

Replaces KPIA-19/20/21. **Scenario B is what OKR tools cannot express.** Re-estimate per SRS §4.3.

#### FR-F17 · Honour split credit on shared deals

`Major` · 5 points · Stage 4 · [KIN-136](https://kinexus.youtrack.cloud/issue/KIN-136)

> **As a** salesperson who closed a deal jointly
> **I want** my declared share credited to me
> **So that** collaboration is not penalised by all-or-nothing attribution

Replaces KPIA-22. Deterministic rounding matters more than it sounds.

#### FR-F18 · Roll sales up the Sales Person tree, not the HR reporting line

`Major` · 5 points · Stage 4 · [KIN-137](https://kinexus.youtrack.cloud/issue/KIN-137)

> **As a** national sales head
> **I want** my number to follow the commercial hierarchy
> **So that** it reflects how the business is actually run

D-5. Replaces KPIA-24.

#### FR-F19 · Company and BU reports read facts, never the sum of item actuals

`Critical` · 5 points · Stage 4 · [KIN-138](https://kinexus.youtrack.cloud/issue/KIN-138)

> **As a** CXO
> **I want** company revenue reported once
> **So that** a three-level sales org does not appear to have tripled turnover

**Guard C-11.** Replaces KPIA-25. The hazard must be documented for dashboard authors.

#### FR-F20 · Show quota coverage when targets are cascaded

`Major` · 5 points · Stage 4 · [KIN-139](https://kinexus.youtrack.cloud/issue/KIN-139)

> **As a** sales director cascading a target
> **I want** to see how much of my number I have allocated
> **So that** I know whether I am exposed or my team is sandbagging

Replaces KPIA-26. Must NOT force equality — over-assignment is deliberate.

#### FR-F21 · Reconcile external ERP totals against computed item totals

`Major` · 5 points · Stage 8 · [KIN-140](https://kinexus.youtrack.cloud/issue/KIN-140)

> **As a** finance-minded HR Manager
> **I want** proof that the appraisal system matches the ERP
> **So that** a discrepancy is found by a report rather than by an employee

Replaces KPIA-35.

#### FR-F22 · Sync runs automatically, with visible freshness per item

`Major` · 3 points · Stage 4 · [KIN-141](https://kinexus.youtrack.cloud/issue/KIN-141)

> **As a** employee
> **I want** my number to update by itself, and to know when it last did
> **So that** I am not clicking a sync button and guessing whether it is current

**Whitespace — Keka requires a manual click per goal.**

---

### Epic G · Scoring and Explainability

**[KIN-63](https://kinexus.youtrack.cloud/issue/KIN-63)** · Stage 3 · 8 stories · 44 points · Major

Every rating can be reconstructed from stored inputs and explained to the employee it describes.

**Guards:** C-7 — bands cover goals and KPIs alike

| ID | Story | Pts | Pri | Stage |
|---|---|---|---|---|
| [FR-G1](https://kinexus.youtrack.cloud/issue/KIN-142) | Attainment band table maps attainment to rating as configuration | 8 | Critical | 3 |
| [FR-G2](https://kinexus.youtrack.cloud/issue/KIN-143) | Interpolate and step modes with declared boundary behaviour | 5 | Major | 3 |
| [FR-G3](https://kinexus.youtrack.cloud/issue/KIN-144) | Weighted-average engine, rounding only at the end | 8 | Critical | 3 |
| [FR-G4](https://kinexus.youtrack.cloud/issue/KIN-145) | Every rating produces a replayable Rating Derivation record | 8 | Critical | 3 |
| [FR-G5](https://kinexus.youtrack.cloud/issue/KIN-146) | Show the employee their own derivation in plain language | 5 | Critical | 3 |
| [FR-G6](https://kinexus.youtrack.cloud/issue/KIN-147) | Rating authority per company, snapshotted at cycle open | 5 | Critical | 3 |
| [FR-G7](https://kinexus.youtrack.cloud/issue/KIN-148) | Manager override with mandatory reason, always audited | 3 | Major | 3 |
| [FR-G8](https://kinexus.youtrack.cloud/issue/KIN-149) | Attainment cap and floor are declared configuration | 2 | Normal | 3 |

#### FR-G1 · Attainment band table maps attainment to rating as configuration

`Critical` · 8 points · Stage 3 · [KIN-142](https://kinexus.youtrack.cloud/issue/KIN-142)

> **As a** HR Manager
> **I want** to declare how attainment becomes a rating
> **So that** why did 92% become 3.5 has an answer I can point at

**Guard C-7.** Only Profit.co documents configurable bands publicly.

#### FR-G2 · Interpolate and step modes with declared boundary behaviour

`Major` · 5 points · Stage 3 · [KIN-143](https://kinexus.youtrack.cloud/issue/KIN-143)

> **As a** HR Manager
> **I want** to choose whether ratings move smoothly or in steps
> **So that** the scoring matches the philosophy my company uses

92% yields 3.2 interpolated, 3.0 stepped.

#### FR-G3 · Weighted-average engine, rounding only at the end

`Critical` · 8 points · Stage 3 · [KIN-144](https://kinexus.youtrack.cloud/issue/KIN-144)

> **As a** employee
> **I want** my overall rating to be arithmetically defensible
> **So that** it does not shift depending on where rounding happened

Oracle's arithmetic exactly. Intermediate rounding is how two people disagree.

#### FR-G4 · Every rating produces a replayable Rating Derivation record

`Critical` · 8 points · Stage 3 · [KIN-145](https://kinexus.youtrack.cloud/issue/KIN-145)

> **As a** HR Manager facing a grievance
> **I want** to reconstruct exactly how a rating was produced
> **So that** I can defend it with a record rather than a recollection

**REG Article 86. The single most differentiating requirement here.**

#### FR-G5 · Show the employee their own derivation in plain language

`Critical` · 5 points · Stage 3 · [KIN-146](https://kinexus.youtrack.cloud/issue/KIN-146)

> **As a** employee receiving a rating
> **I want** to see how it was calculated, in words I understand
> **So that** I can accept it, or challenge it on specifics

No competitor offers this. Also the practical form of the Article 86 obligation.

#### FR-G6 · Rating authority per company, snapshotted at cycle open

`Critical` · 5 points · Stage 3 · [KIN-147](https://kinexus.youtrack.cloud/issue/KIN-147)

> **As a** HR Manager
> **I want** to choose whether the band table or the manager is authoritative
> **So that** the system matches my policy rather than imposing one

D-9. Snapshot prevents a mid-cycle flip re-deriving completed appraisals.

#### FR-G7 · Manager override with mandatory reason, always audited

`Major` · 3 points · Stage 3 · [KIN-148](https://kinexus.youtrack.cloud/issue/KIN-148)

> **As a** manager
> **I want** to override a derived rating when the number misses context
> **So that** automation informs my judgement instead of replacing it

BP8. Override frequency by manager is a calibration input.

#### FR-G8 · Attainment cap and floor are declared configuration

`Normal` · 2 points · Stage 3 · [KIN-149](https://kinexus.youtrack.cloud/issue/KIN-149)

> **As a** HR Manager
> **I want** to decide how far over-attainment counts
> **So that** a salesperson at 300% is treated the way my company intends

Currently a constant in code.

---

### Epic H · Continuous Performance

**[KIN-64](https://kinexus.youtrack.cloud/issue/KIN-64)** · Stage 6 · 8 stories · 37 points · Major

Progress is a conversation on a cadence, not a form filled in once a year.

**Guards:** C-9 — nudges suppressed where unentitled

| ID | Story | Pts | Pri | Stage |
|---|---|---|---|---|
| [FR-H1](https://kinexus.youtrack.cloud/issue/KIN-155) | Check-ins as a first-class object on a configurable cadence | 8 | Major | 6 |
| [FR-H2](https://kinexus.youtrack.cloud/issue/KIN-156) | Confidence is a separate field from calculated status | 5 | Major | 6 |
| [FR-H3](https://kinexus.youtrack.cloud/issue/KIN-157) | Status derives from attainment against expected progress | 3 | Normal | 6 |
| [FR-H4](https://kinexus.youtrack.cloud/issue/KIN-158) | One-to-ones with agendas, carry-forward and linked actions | 8 | Major | 6 |
| [FR-H5](https://kinexus.youtrack.cloud/issue/KIN-159) | Nudge on overdue check-ins, in product and by email | 3 | Normal | 6 |
| [FR-H6](https://kinexus.youtrack.cloud/issue/KIN-160) | Feedback prompts are task-focused, never person-focused | 3 | Normal | 6 |
| [FR-H7](https://kinexus.youtrack.cloud/issue/KIN-161) | No passive behavioural monitoring as a performance input | 2 | Normal | 6 |
| [FR-H8](https://kinexus.youtrack.cloud/issue/KIN-162) | 360 feedback with nomination and manager approval | 5 | Major | 6 |

#### FR-H1 · Check-ins as a first-class object on a configurable cadence

`Major` · 8 points · Stage 6 · [KIN-155](https://kinexus.youtrack.cloud/issue/KIN-155)

> **As a** employee
> **I want** to record where a goal stands on a regular rhythm
> **So that** the year-end review is a summary, not a reconstruction

**Blocked on D-14** — is Goal Check-In referenced by any live code path?

#### FR-H2 · Confidence is a separate field from calculated status

`Major` · 5 points · Stage 6 · [KIN-156](https://kinexus.youtrack.cloud/issue/KIN-156)

> **As a** team lead behind pace who knows the deal closes next week
> **I want** to say I am confident even though the numbers say at risk
> **So that** my manager reads the situation rather than the arithmetic

**Only WorkBoard documents this split.**

#### FR-H3 · Status derives from attainment against expected progress

`Normal` · 3 points · Stage 6 · [KIN-157](https://kinexus.youtrack.cloud/issue/KIN-157)

> **As a** manager
> **I want** at-risk goals identified by pace, not absolute progress
> **So that** 30% in month two differs from 30% in month eleven

Generalises the existing _update_trajectory shape.

#### FR-H4 · One-to-ones with agendas, carry-forward and linked actions

`Major` · 8 points · Stage 6 · [KIN-158](https://kinexus.youtrack.cloud/issue/KIN-158)

> **As a** manager
> **I want** a running agenda that remembers what we left open
> **So that** the conversation builds instead of restarting every fortnight

FLOOR #7.

#### FR-H5 · Nudge on overdue check-ins, in product and by email

`Normal` · 3 points · Stage 6 · [KIN-159](https://kinexus.youtrack.cloud/issue/KIN-159)

> **As a** employee
> **I want** a reminder when a check-in is due
> **So that** the cadence survives a busy month

**Guard C-9** — these are exactly the emails FR-O4 must suppress.

#### FR-H6 · Feedback prompts are task-focused, never person-focused

`Normal` · 3 points · Stage 6 · [KIN-160](https://kinexus.youtrack.cloud/issue/KIN-160)

> **As a** employee receiving feedback
> **I want** it directed at the work rather than at me
> **So that** it helps me improve instead of making me defensive

**EVID — Kluger and DeNisi: over a third of feedback interventions decreased performance.**

#### FR-H7 · No passive behavioural monitoring as a performance input

`Normal` · 2 points · Stage 6 · [KIN-161](https://kinexus.youtrack.cloud/issue/KIN-161)

> **As a** employee
> **I want** to be measured on outcomes rather than activity signals
> **So that** my record reflects what I achieved, not how my mouse moved

**EVID — monitoring meta-analysis: performance r = -0.01, stress +0.11.**

#### FR-H8 · 360 feedback with nomination and manager approval

`Major` · 5 points · Stage 6 · [KIN-162](https://kinexus.youtrack.cloud/issue/KIN-162)

> **As a** employee
> **I want** to nominate who gives feedback on me, subject to approval
> **So that** the panel is relevant and neither hand-picked nor imposed

FLOOR #6. AC4 anonymity threshold is the one that matters legally.

---

### Epic I · Calibration and 9-Box

**[KIN-65](https://kinexus.youtrack.cloud/issue/KIN-65)** · Stage 6 · 8 stories · 37 points · Major

Ratings are moderated in a session that leaves an audit trail.

**Guards:** C-14 — one calibration implementation. BLOCKED on D-1

| ID | Story | Pts | Pri | Stage |
|---|---|---|---|---|
| [FR-I1](https://kinexus.youtrack.cloud/issue/KIN-168) | Resolve which calibration implementation survives | 3 | Critical | 6 |
| [FR-I2](https://kinexus.youtrack.cloud/issue/KIN-169) | Calibration session with population, facilitators and histogram | 8 | Major | 6 |
| [FR-I3](https://kinexus.youtrack.cloud/issue/KIN-170) | Every calibration change records who, when, from, to and why | 5 | Critical | 6 |
| [FR-I4](https://kinexus.youtrack.cloud/issue/KIN-171) | Show distribution and flag outliers; enforcement off by default | 5 | Major | 6 |
| [FR-I5](https://kinexus.youtrack.cloud/issue/KIN-172) | Nine-box with the two scores never collapsed into one | 5 | Major | 6 |
| [FR-I6](https://kinexus.youtrack.cloud/issue/KIN-173) | Managers cannot change their own reports' ratings in session | 3 | Major | 6 |
| [FR-I7](https://kinexus.youtrack.cloud/issue/KIN-174) | Scoped administrators see only their scope, read-only outside | 3 | Major | 6 |
| [FR-I8](https://kinexus.youtrack.cloud/issue/KIN-175) | Calibration sign-off becomes a first-class record | 5 | Major | 6 |

#### FR-I1 · Resolve which calibration implementation survives

`Critical` · 3 points · Stage 6 · [KIN-168](https://kinexus.youtrack.cloud/issue/KIN-168)

> **As a** product owner
> **I want** one calibration implementation
> **So that** customers do not meet an untested one by accident

**Guard C-14. BLOCKS the whole epic.** D-1 dissent and middle path recorded.

#### FR-I2 · Calibration session with population, facilitators and histogram

`Major` · 8 points · Stage 6 · [KIN-169](https://kinexus.youtrack.cloud/issue/KIN-169)

> **As a** calibration facilitator
> **I want** a session that scopes a population and shows its distribution
> **So that** the meeting has a shared picture to work from

Mid-market calibration is a table with a histogram and a log — not a succession suite.

#### FR-I3 · Every calibration change records who, when, from, to and why

`Critical` · 5 points · Stage 6 · [KIN-170](https://kinexus.youtrack.cloud/issue/KIN-170)

> **As a** HR Manager defending a moderated rating
> **I want** every change made in calibration on the record
> **So that** the committee changed it is a documented decision

The audit artefact in a grievance.

#### FR-I4 · Show distribution and flag outliers; enforcement off by default

`Major` · 5 points · Stage 6 · [KIN-171](https://kinexus.youtrack.cloud/issue/KIN-171)

> **As a** HR Manager
> **I want** the bell curve available but not imposed
> **So that** I meet an India expectation without doing statistical harm

D-17. Evidence and market expectation in tension, resolved by configuration.

#### FR-I5 · Nine-box with the two scores never collapsed into one

`Major` · 5 points · Stage 6 · [KIN-172](https://kinexus.youtrack.cloud/issue/KIN-172)

> **As a** HR Manager
> **I want** performance and potential plotted as independent axes
> **So that** a high performer with low potential is visible as exactly that

FLOOR #11. A grid is a conversation aid, never a decision.

#### FR-I6 · Managers cannot change their own reports' ratings in session

`Major` · 3 points · Stage 6 · [KIN-173](https://kinexus.youtrack.cloud/issue/KIN-173)

> **As a** calibration facilitator
> **I want** managers excluded from adjusting their own reports
> **So that** moderation is moderation rather than a second bite

Standard control across Betterworks and SAP.

#### FR-I7 · Scoped administrators see only their scope, read-only outside

`Major` · 3 points · Stage 6 · [KIN-174](https://kinexus.youtrack.cloud/issue/KIN-174)

> **As a** divisional HR partner
> **I want** to calibrate my division without seeing other divisions
> **So that** access matches responsibility

Culture Amp's model. Consistent with existing row-level scoping.

#### FR-I8 · Calibration sign-off becomes a first-class record

`Major` · 5 points · Stage 6 · [KIN-175](https://kinexus.youtrack.cloud/issue/KIN-175)

> **As a** HR Manager
> **I want** sign-offs stored as records I can query
> **So that** who signed off Q2 and when is a search, not a hunt through JSON

DEF-7. Currently a JSON value in page_settings — not queryable, silently overwritten.

---

### Epic J · AI Assistance

**[KIN-66](https://kinexus.youtrack.cloud/issue/KIN-66)** · Stage 7 · 8 stories · 38 points · Normal

AI drafts and critiques, a human decides, and the whole chain is auditable.

**Guards:** FR-J6 prohibitions enforced before any AI ships

| ID | Story | Pts | Pri | Stage |
|---|---|---|---|---|
| [FR-J1](https://kinexus.youtrack.cloud/issue/KIN-183) | AI drafts goals from role, department and strategy context | 8 | Normal | 7 |
| [FR-J2](https://kinexus.youtrack.cloud/issue/KIN-184) | AI critiques an existing goal against declared quality criteria | 8 | Normal | 7 |
| [FR-J3](https://kinexus.youtrack.cloud/issue/KIN-185) | AI narrative comes strictly from that employee's own record | 5 | Major | 7 |
| [FR-J4](https://kinexus.youtrack.cloud/issue/KIN-182) | AI never proposes or sets a rating | 3 | Critical | 7 |
| [FR-J5](https://kinexus.youtrack.cloud/issue/KIN-186) | Log every AI action and retain logs at least six months | 5 | Critical | 7 |
| [FR-J6](https://kinexus.youtrack.cloud/issue/KIN-181) | Hard prohibitions — no emotion, voice or facial analysis | 3 | Critical | 7 |
| [FR-J7](https://kinexus.youtrack.cloud/issue/KIN-187) | An affected person can obtain an explanation of the AI's role | 3 | Major | 7 |
| [FR-J8](https://kinexus.youtrack.cloud/issue/KIN-188) | Support the customer's duty to notify workers | 3 | Major | 7 |

#### FR-J1 · AI drafts goals from role, department and strategy context

`Normal` · 8 points · Stage 7 · [KIN-183](https://kinexus.youtrack.cloud/issue/KIN-183)

> **As a** manager setting goals for eight people
> **I want** a first draft I can edit
> **So that** I start from something rather than a blank field

Table stakes. Each suggestion must explain its basis.

#### FR-J2 · AI critiques an existing goal against declared quality criteria

`Normal` · 8 points · Stage 7 · [KIN-184](https://kinexus.youtrack.cloud/issue/KIN-184)

> **As a** manager approving goals
> **I want** a quality assessment of a goal someone already wrote
> **So that** I catch a vague goal before I approve it

**DIFF #7 — the one AI capability nobody in the scan has.**

#### FR-J3 · AI narrative comes strictly from that employee's own record

`Major` · 5 points · Stage 7 · [KIN-185](https://kinexus.youtrack.cloud/issue/KIN-185)

> **As a** employee
> **I want** any AI-written text about me grounded in my actual record
> **So that** my review does not contain plausible sentences about things that never happened

AC4 — sparse data produces a short draft, not padding.

#### FR-J4 · AI never proposes or sets a rating

`Critical` · 3 points · Stage 7 · [KIN-182](https://kinexus.youtrack.cloud/issue/KIN-182)

> **As a** employee
> **I want** a human to decide my rating
> **So that** the number that affects my pay was chosen by someone accountable

**A prohibition.** .45 administrative rating reliability makes an AI rating a liability.

#### FR-J5 · Log every AI action and retain logs at least six months

`Critical` · 5 points · Stage 7 · [KIN-186](https://kinexus.youtrack.cloud/issue/KIN-186)

> **As a** compliance officer
> **I want** a record of every AI action and the human decision that followed
> **So that** we can meet the deployer logging obligation

REG Article 26(6). DPDP requires one year — build to the longer.

#### FR-J6 · Hard prohibitions — no emotion, voice or facial analysis

`Critical` · 3 points · Stage 7 · [KIN-181](https://kinexus.youtrack.cloud/issue/KIN-181)

> **As a** compliance officer
> **I want** certain capabilities to be architecturally impossible
> **So that** they cannot be added later by a well-meaning feature request

**REG Article 5(1)(f) — in force now. EUR 35m or 7% of turnover. Read before any other J story.**

#### FR-J7 · An affected person can obtain an explanation of the AI's role

`Major` · 3 points · Stage 7 · [KIN-187](https://kinexus.youtrack.cloud/issue/KIN-187)

> **As a** employee affected by a decision AI helped shape
> **I want** a clear explanation of what the AI did
> **So that** I can understand and challenge the decision

REG Article 86. Satisfied by FR-G5 plus FR-J5.

#### FR-J8 · Support the customer's duty to notify workers

`Major` · 3 points · Stage 7 · [KIN-188](https://kinexus.youtrack.cloud/issue/KIN-188)

> **As a** customer HR director
> **I want** the product to help me notify my workforce
> **So that** I can meet a duty the law places on me as deployer

REG Article 26(7). AC7 — must not read as a compliance guarantee.

---

### Epic K · Assignment at Scale

**[KIN-67](https://kinexus.youtrack.cloud/issue/KIN-67)** · Stage 2 · 5 stories · 23 points · Major

An HR team of three can configure goals for 800 employees.

| ID | Story | Pts | Pri | Stage |
|---|---|---|---|---|
| [FR-K1](https://kinexus.youtrack.cloud/issue/KIN-150) | Assign templates to many employees at once, by org attributes | 8 | Major | 2 |
| [FR-K2](https://kinexus.youtrack.cloud/issue/KIN-151) | Bulk assignment is preview-then-commit | 5 | Major | 2 |
| [FR-K3](https://kinexus.youtrack.cloud/issue/KIN-152) | Transactional per employee with per-employee outcomes | 5 | Major | 2 |
| [FR-K4](https://kinexus.youtrack.cloud/issue/KIN-153) | Five hundred employees complete in one background job | 3 | Normal | 2 |
| [FR-K5](https://kinexus.youtrack.cloud/issue/KIN-154) | Irreversible bulk operations say so before commit | 2 | Normal | 2 |

#### FR-K1 · Assign templates to many employees at once, by org attributes

`Major` · 8 points · Stage 2 · [KIN-150](https://kinexus.youtrack.cloud/issue/KIN-150)

> **As a** HR Manager in a three-person HR team
> **I want** to assign goals to hundreds of people in one operation
> **So that** goal-setting season is a morning rather than a fortnight

FLOOR #4.

#### FR-K2 · Bulk assignment is preview-then-commit

`Major` · 5 points · Stage 2 · [KIN-151](https://kinexus.youtrack.cloud/issue/KIN-151)

> **As a** HR Manager about to create 800 goals
> **I want** to see exactly what will happen before it happens
> **So that** I find the mistake while it is still a preview

#### FR-K3 · Transactional per employee with per-employee outcomes

`Major` · 5 points · Stage 2 · [KIN-152](https://kinexus.youtrack.cloud/issue/KIN-152)

> **As a** HR Manager
> **I want** one bad row not to lose the other 799
> **So that** a single data problem does not mean starting over

Two failure modes to avoid: losing the run, and losing one row silently.

#### FR-K4 · Five hundred employees complete in one background job

`Normal` · 3 points · Stage 2 · [KIN-153](https://kinexus.youtrack.cloud/issue/KIN-153)

> **As a** HR Manager
> **I want** a large assignment to finish without timing out
> **So that** I can assign to the whole company in one action

#### FR-K5 · Irreversible bulk operations say so before commit

`Normal` · 2 points · Stage 2 · [KIN-154](https://kinexus.youtrack.cloud/issue/KIN-154)

> **As a** HR Manager
> **I want** to be told when an action cannot be undone
> **So that** I pause before doing it rather than after

AC5 — do not over-warn, or warnings get ignored.

---

### Epic L · Reporting

**[KIN-68](https://kinexus.youtrack.cloud/issue/KIN-68)** · Stage 8 · 5 stories · 22 points · Major

The numbers leaders act on are correct, and the exports do not need re-typing.

**Guards:** C-11 — one authoritative org total

| ID | Story | Pts | Pri | Stage |
|---|---|---|---|---|
| [FR-L1](https://kinexus.youtrack.cloud/issue/KIN-163) | Surface cascade alignment variance as a report | 3 | Major | 8 |
| [FR-L2](https://kinexus.youtrack.cloud/issue/KIN-164) | Goal-setting completion and readiness by organisational unit | 3 | Major | 8 |
| [FR-L3](https://kinexus.youtrack.cloud/issue/KIN-165) | Manager leniency and severity surfaced before calibration | 8 | Major | 8 |
| [FR-L4](https://kinexus.youtrack.cloud/issue/KIN-166) | Exports structured for re-use without manual restructuring | 5 | Major | 8 |
| [FR-L5](https://kinexus.youtrack.cloud/issue/KIN-167) | Declare KPI Fact as the single authority for roll-up reporting | 3 | Major | 8 |

#### FR-L1 · Surface cascade alignment variance as a report

`Major` · 3 points · Stage 8 · [KIN-163](https://kinexus.youtrack.cloud/issue/KIN-163)

> **As a** CXO
> **I want** to see where cascaded targets do not add up
> **So that** I know which parts of the plan are uncovered

Completes an existing half-built strength. Depends on FR-A3.

#### FR-L2 · Goal-setting completion and readiness by organisational unit

`Major` · 3 points · Stage 8 · [KIN-164](https://kinexus.youtrack.cloud/issue/KIN-164)

> **As a** HR Manager
> **I want** completion reported by department and manager
> **So that** I chase three managers rather than emailing everyone

Renders FR-C6 as a report.

#### FR-L3 · Manager leniency and severity surfaced before calibration

`Major` · 8 points · Stage 8 · [KIN-165](https://kinexus.youtrack.cloud/issue/KIN-165)

> **As a** calibration facilitator
> **I want** to know which managers rate high or low before the meeting
> **So that** the session discusses people rather than discovering patterns

**Whitespace — nobody in the India scan does this pre-meeting.** AC3 keeps it honest at small n.

#### FR-L4 · Exports structured for re-use without manual restructuring

`Major` · 5 points · Stage 8 · [KIN-166](https://kinexus.youtrack.cloud/issue/KIN-166)

> **As a** HR analyst
> **I want** an export I can use immediately
> **So that** I am not rebuilding the file every month

**The single most consistent buyer complaint in the category.**

#### FR-L5 · Declare KPI Fact as the single authority for roll-up reporting

`Major` · 3 points · Stage 8 · [KIN-167](https://kinexus.youtrack.cloud/issue/KIN-167)

> **As a** developer building a new report
> **I want** one documented answer to where org totals come from
> **So that** two reports do not produce two different revenue figures

**Guard C-11.** Depends on FR-A3 and FR-F19.

---

### Epic M · OKR Mode

**[KIN-69](https://kinexus.youtrack.cloud/issue/KIN-69)** · Stage 7 · 6 stories · 30 points · Normal

A customer that runs OKRs sees OKRs; one data model underneath.

**Guards:** C-13 — three independent weight invariants

| ID | Story | Pts | Pri | Stage |
|---|---|---|---|---|
| [FR-M1](https://kinexus.youtrack.cloud/issue/KIN-195) | OKR is a presentation mode, not a second data model | 5 | Normal | 7 |
| [FR-M2](https://kinexus.youtrack.cloud/issue/KIN-196) | Five Key Result types including milestone | 5 | Normal | 7 |
| [FR-M3](https://kinexus.youtrack.cloud/issue/KIN-197) | Guardrail Key Results — stay above, below, between | 5 | Normal | 7 |
| [FR-M4](https://kinexus.youtrack.cloud/issue/KIN-198) | Per-Key-Result weighting, summing to 100 within its objective | 5 | Normal | 7 |
| [FR-M5](https://kinexus.youtrack.cloud/issue/KIN-199) | Objective progress rolls up by a declared, configurable method | 5 | Normal | 7 |
| [FR-M6](https://kinexus.youtrack.cloud/issue/KIN-200) | Terminology is configurable per tenant | 5 | Normal | 7 |

#### FR-M1 · OKR is a presentation mode, not a second data model

`Normal` · 5 points · Stage 7 · [KIN-195](https://kinexus.youtrack.cloud/issue/KIN-195)

> **As a** product owner
> **I want** OKR support without a parallel object graph
> **So that** the two vocabularies cannot diverge into two half-maintained products

D-A and D-B. An Objective IS an Individual Goal.

#### FR-M2 · Five Key Result types including milestone

`Normal` · 5 points · Stage 7 · [KIN-196](https://kinexus.youtrack.cloud/issue/KIN-196)

> **As a** employee writing Key Results
> **I want** the right measurement type for each one
> **So that** a launch date and a revenue target are not forced into the same shape

Four are table stakes; milestone makes five the credible set.

#### FR-M3 · Guardrail Key Results — stay above, below, between

`Normal` · 5 points · Stage 7 · [KIN-197](https://kinexus.youtrack.cloud/issue/KIN-197)

> **As a** service manager
> **I want** to express keep response time under four hours
> **So that** a metric I must hold within a band is not forced into a grow-this shape

**DIFF #5 — only Perdoo and Profit.co.** AC5 breach history is what makes it meaningful.

#### FR-M4 · Per-Key-Result weighting, summing to 100 within its objective

`Normal` · 5 points · Stage 7 · [KIN-198](https://kinexus.youtrack.cloud/issue/KIN-198)

> **As a** employee
> **I want** to weight my Key Results by importance
> **So that** the objective's progress reflects what actually matters

**Guard C-13 — three independent weight invariants, never summed together.**

#### FR-M5 · Objective progress rolls up by a declared, configurable method

`Normal` · 5 points · Stage 7 · [KIN-199](https://kinexus.youtrack.cloud/issue/KIN-199)

> **As a** HR Manager
> **I want** to choose how an objective takes progress from its Key Results
> **So that** the method matches our philosophy rather than a default

Weighted average vs Perdoo's weakest-child. Neither is wrong; make it configuration.

#### FR-M6 · Terminology is configurable per tenant

`Normal` · 5 points · Stage 7 · [KIN-200](https://kinexus.youtrack.cloud/issue/KIN-200)

> **As a** HR Manager whose company says KRA
> **I want** the product to say KRA
> **So that** my employees are not learning a new vocabulary

FLOOR #1. greytHR makes this an explicit positioning decision.

---

### Epic N · India-Specific Capability

**[KIN-70](https://kinexus.youtrack.cloud/issue/KIN-70)** · Stage 8 · 5 stories · 50 points · Normal

Fit the market Alvoraa actually sells into, in ways no competitor has attempted.

| ID | Story | Pts | Pri | Stage |
|---|---|---|---|---|
| [FR-N1](https://kinexus.youtrack.cloud/issue/KIN-201) | Drive variable pay and increments from ratings, against CTC | 13 | Normal | 8 |
| [FR-N2](https://kinexus.youtrack.cloud/issue/KIN-202) | A frontline model that completes in two minutes on a phone | 8 | Normal | 8 |
| [FR-N3](https://kinexus.youtrack.cloud/issue/KIN-203) | Review forms and notices in English and scheduled languages | 8 | Normal | 8 |
| [FR-N4](https://kinexus.youtrack.cloud/issue/KIN-204) | PIP documentation structured for Indian labour-law scrutiny | 8 | Normal | 8 |
| [FR-N5](https://kinexus.youtrack.cloud/issue/KIN-205) | Adapters for the systems Indian mid-market KPIs live in | 13 | Normal | 8 |

#### FR-N1 · Drive variable pay and increments from ratings, against CTC

`Normal` · 13 points · Stage 8 · [KIN-201](https://kinexus.youtrack.cloud/issue/KIN-201)

> **As a** HR Manager in an Indian company
> **I want** the rating to compute the increment and variable payout
> **So that** the module connects to the decision it exists to support

**Whitespace — HROne is the only vendor doing this.** Where the module earns its budget in India.

#### FR-N2 · A frontline model that completes in two minutes on a phone

`Normal` · 8 points · Stage 8 · [KIN-202](https://kinexus.youtrack.cloud/issue/KIN-202)

> **As a** plant supervisor with forty operators
> **I want** a review I can complete between shifts
> **So that** frontline staff get a real review instead of being skipped

**Whitespace — every product in the scan assumes a desk.** AC2 is the requirement, not a nicety.

#### FR-N3 · Review forms and notices in English and scheduled languages

`Normal` · 8 points · Stage 8 · [KIN-203](https://kinexus.youtrack.cloud/issue/KIN-203)

> **As a** frontline employee
> **I want** my review and privacy notice in a language I read
> **So that** I can participate rather than sign something I do not understand

Product need and DPDP obligation in one. AC3 — customer content too, not just ours.

#### FR-N4 · PIP documentation structured for Indian labour-law scrutiny

`Normal` · 8 points · Stage 8 · [KIN-204](https://kinexus.youtrack.cloud/issue/KIN-204)

> **As a** HR Manager managing a performance improvement plan
> **I want** the documentation to hold up if it is examined
> **So that** a difficult decision rests on a defensible record

**Whitespace.** Requires qualified employment-law review before release.

#### FR-N5 · Adapters for the systems Indian mid-market KPIs live in

`Normal` · 13 points · Stage 8 · [KIN-205](https://kinexus.youtrack.cloud/issue/KIN-205)

> **As a** Indian mid-market customer
> **I want** my KPIs to pull from Tally, Zoho and my CRM
> **So that** automation applies to the systems I actually run on

**Whitespace — no vendor in the scan integrates with any of these.** Split per system after AC5.

---

### Epic O · Entitlement and Plan Lifecycle

**[KIN-71](https://kinexus.youtrack.cloud/issue/KIN-71)** · Stage 0/1 · 8 stories · 33 points · Critical

A priced feature is actually priced, and a downgrade never destroys history.

**Guards:** C-9 — FR-O4 is permanent, not a stopgap for FR-O5

| ID | Story | Pts | Pri | Stage |
|---|---|---|---|---|
| [FR-O1](https://kinexus.youtrack.cloud/issue/KIN-81) | Server-side entitlement on every goals and performance endpoint | 8 | Critical | 0 |
| [FR-O2](https://kinexus.youtrack.cloud/issue/KIN-83) | Downgrade hides the feature and keeps every record | 5 | Major | 1 |
| [FR-O3](https://kinexus.youtrack.cloud/issue/KIN-84) | Backfill an explicit features list onto every existing tenant | 3 | Major | 1 |
| [FR-O4](https://kinexus.youtrack.cloud/issue/KIN-82) | Scheduled jobs and email suppressed for unentitled features | 3 | Critical | 0 |
| [FR-O5](https://kinexus.youtrack.cloud/issue/KIN-86) | Install alvoraa_goals only where the plan includes it | 5 | Major | 1 |
| [FR-O6](https://kinexus.youtrack.cloud/issue/KIN-85) | One provisioning path and one plan vocabulary | 5 | Major | 1 |
| [FR-O7](https://kinexus.youtrack.cloud/issue/KIN-87) | Portal hides goals and performance when unentitled | 3 | Normal | 8 |
| [FR-O8](https://kinexus.youtrack.cloud/issue/KIN-88) | Delete duplicate Alvox Module Defs before building profiles | 1 | Normal | 1 |

#### FR-O1 · Server-side entitlement on every goals and performance endpoint

`Critical` · 8 points · Stage 0 · [KIN-81](https://kinexus.youtrack.cloud/issue/KIN-81)

> **As a** business owner selling Goals on the Enterprise plan
> **I want** the API to refuse callers whose tenant did not buy the feature
> **So that** the price is real rather than cosmetic

DEF-8. has_feature() is called nowhere outside subscription.py.

#### FR-O2 · Downgrade hides the feature and keeps every record

`Major` · 5 points · Stage 1 · [KIN-83](https://kinexus.youtrack.cloud/issue/KIN-83)

> **As a** customer downgrading from Enterprise to Business
> **I want** my goal and appraisal history preserved
> **So that** nothing is destroyed if I upgrade again or need it in a dispute

D-19 open — read-only retention recommended.

#### FR-O3 · Backfill an explicit features list onto every existing tenant

`Major` · 3 points · Stage 1 · [KIN-84](https://kinexus.youtrack.cloud/issue/KIN-84)

> **As a** platform operator
> **I want** every tenant to carry an explicit features list
> **So that** the fail-open branch is a safety net rather than the normal path

#### FR-O4 · Scheduled jobs and email suppressed for unentitled features

`Critical` · 3 points · Stage 0 · [KIN-82](https://kinexus.youtrack.cloud/issue/KIN-82)

> **As a** employee at a company on the Starter plan
> **I want** to stop receiving daily emails about goals
> **So that** I am not chased about a product my employer never bought

DEF-9. **Guard C-9 — permanent, not a stopgap for FR-O5.**

#### FR-O5 · Install alvoraa_goals only where the plan includes it

`Major` · 5 points · Stage 1 · [KIN-86](https://kinexus.youtrack.cloud/issue/KIN-86)

> **As a** platform operator
> **I want** apps installed according to the plan
> **So that** an unsold feature's doctypes and hooks are not present at all

MODULE_ACCESS Wave 5.

#### FR-O6 · One provisioning path and one plan vocabulary

`Major` · 5 points · Stage 1 · [KIN-85](https://kinexus.youtrack.cloud/issue/KIN-85)

> **As a** platform operator
> **I want** the shell script and the API to provision identically
> **So that** two tenants on the same plan are actually on the same plan

DEF-9. provision_tenant.sh puts goals in Business; subscription.py puts it in Enterprise.

#### FR-O7 · Portal hides goals and performance when unentitled

`Normal` · 3 points · Stage 8 · [KIN-87](https://kinexus.youtrack.cloud/issue/KIN-87)

> **As a** employee at a company on the Business plan
> **I want** the portal not to show me navigation I cannot use
> **So that** I am not offered a door that leads nowhere

Cosmetic layer on FR-O1, never instead of it.

#### FR-O8 · Delete duplicate Alvox Module Defs before building profiles

`Normal` · 1 points · Stage 1 · [KIN-88](https://kinexus.youtrack.cloud/issue/KIN-88)

> **As a** platform operator
> **I want** the leftover Alvox module definitions removed
> **So that** a Module Profile cannot silently mis-gate a tenant

MODULE_ACCESS §8 housekeeping. Do it before profile work, not during.

---

### Epic P · Positions and Effective Dating

**[KIN-72](https://kinexus.youtrack.cloud/issue/KIN-72)** · Stage 5 · 6 stories · 36 points · Normal

Credit belongs to the role, so a reorganisation never rewrites history.

**Guards:** C-8 — fact visibility must follow positions

| ID | Story | Pts | Pri | Stage |
|---|---|---|---|---|
| [FR-P1](https://kinexus.youtrack.cloud/issue/KIN-189) | Alvoraa Position and effective-dated Position Assignment | 13 | Major | 5 |
| [FR-P2](https://kinexus.youtrack.cloud/issue/KIN-190) | Backfill positions from the existing reporting structure | 5 | Major | 5 |
| [FR-P3](https://kinexus.youtrack.cloud/issue/KIN-191) | A mid-cycle reorganisation leaves historical credit intact | 5 | Major | 5 |
| [FR-P4](https://kinexus.youtrack.cloud/issue/KIN-192) | Vacant and acting positions are ordinary cases | 5 | Major | 5 |
| [FR-P5](https://kinexus.youtrack.cloud/issue/KIN-193) | Fact visibility resolves through positions; goals stay person-based | 5 | Critical | 5 |
| [FR-P6](https://kinexus.youtrack.cloud/issue/KIN-194) | Denormalised fallback if the position layer is descoped | 3 | Minor | 5 |

#### FR-P1 · Alvoraa Position and effective-dated Position Assignment

`Major` · 13 points · Stage 5 · [KIN-189](https://kinexus.youtrack.cloud/issue/KIN-189)

> **As a** sales director whose team was restructured in July
> **I want** credit for April to June to stay where it was earned
> **So that** a reorganisation does not silently rewrite performance history

D-2. Replaces KPIA-28. **Guard C-8 follows.**

#### FR-P2 · Backfill positions from the existing reporting structure

`Major` · 5 points · Stage 5 · [KIN-190](https://kinexus.youtrack.cloud/issue/KIN-190)

> **As a** platform operator
> **I want** positions generated from the org chart we already have
> **So that** adopting the position layer is not a data-entry project

Replaces KPIA-29. AC3 origin date determines how far back credit resolves.

#### FR-P3 · A mid-cycle reorganisation leaves historical credit intact

`Major` · 5 points · Stage 5 · [KIN-191](https://kinexus.youtrack.cloud/issue/KIN-191)

> **As a** manager who ran a team for two quarters
> **I want** to keep credit for what my team delivered while I ran it
> **So that** my appraisal reflects the period I was accountable for

**The acceptance test for the whole position layer.** Replaces KPIA-30.

#### FR-P4 · Vacant and acting positions are ordinary cases

`Major` · 5 points · Stage 5 · [KIN-192](https://kinexus.youtrack.cloud/issue/KIN-192)

> **As a** HR Manager
> **I want** vacancies and acting appointments handled by the model
> **So that** six weeks between a leaver and a replacement is not a hole in the data

Replaces KPIA-31. Where the position layer earns much of its keep.

#### FR-P5 · Fact visibility resolves through positions; goals stay person-based

`Critical` · 5 points · Stage 5 · [KIN-193](https://kinexus.youtrack.cloud/issue/KIN-193)

> **As a** acting manager
> **I want** to open the facts I am credited for
> **So that** I can explain my own number

**Guard C-8. D-20.** Two trees, one stated authority.

#### FR-P6 · Denormalised fallback if the position layer is descoped

`Minor` · 3 points · Stage 5 · [KIN-194](https://kinexus.youtrack.cloud/issue/KIN-194)

> **As a** product owner facing a scope decision
> **I want** a cheaper option that solves the main case
> **So that** descoping does not mean shipping known-wrong roll-up

**Recorded alternative, not planned work.** Close as Won't fix if FR-P1 proceeds.

---

### Epic Q · Trust, Dispute and Anti-Gaming

**[KIN-73](https://kinexus.youtrack.cloud/issue/KIN-73)** · Stage 5 · 5 stories · 26 points · Normal

An automated number is disputable, freezable, permission-scoped and gaming-resistant.

**Guards:** C-5 — freeze at the goal-period level

| ID | Story | Pts | Pri | Stage |
|---|---|---|---|---|
| [FR-Q1](https://kinexus.youtrack.cloud/issue/KIN-176) | Dispute a synced entry without being able to edit it | 5 | Major | 5 |
| [FR-Q2](https://kinexus.youtrack.cloud/issue/KIN-177) | Freeze at period close, at the smaller of period or cycle | 8 | Critical | 5 |
| [FR-Q3](https://kinexus.youtrack.cloud/issue/KIN-178) | Flag metrics where the scored person produces the data | 3 | Normal | 5 |
| [FR-Q4](https://kinexus.youtrack.cloud/issue/KIN-179) | Scope fact and credit visibility by role and hierarchy | 5 | Critical | 5 |
| [FR-Q5](https://kinexus.youtrack.cloud/issue/KIN-180) | Limit the personal and commercial data the HR system retains | 5 | Major | 5 |

#### FR-Q1 · Dispute a synced entry without being able to edit it

`Major` · 5 points · Stage 5 · [KIN-176](https://kinexus.youtrack.cloud/issue/KIN-176)

> **As a** employee whose score is driven by transactions I did not enter
> **I want** to flag a number as wrong
> **So that** I can challenge it without being able to alter the record

Replaces KPIA-36. Necessary because of Scenario B.

#### FR-Q2 · Freeze at period close, at the smaller of period or cycle

`Critical` · 8 points · Stage 5 · [KIN-177](https://kinexus.youtrack.cloud/issue/KIN-177)

> **As a** employee already rated for Q1
> **I want** my Q1 number to stay settled
> **So that** a credit note in December cannot reopen a review I signed in April

**Guard C-5.** Replaces KPIA-37, widened from cycle-level to period-level.

#### FR-Q3 · Flag metrics where the scored person produces the data

`Normal` · 3 points · Stage 5 · [KIN-178](https://kinexus.youtrack.cloud/issue/KIN-178)

> **As a** HR Manager designing a scorecard
> **I want** self-produced metrics identified at design time
> **So that** I notice the conflict before an appraisal depends on it

Replaces KPIA-38. Cheap now, expensive later.

#### FR-Q4 · Scope fact and credit visibility by role and hierarchy

`Critical` · 5 points · Stage 5 · [KIN-179](https://kinexus.youtrack.cloud/issue/KIN-179)

> **As a** employee
> **I want** my commercial transactions invisible to my peers
> **So that** a performance system does not become a window into everyone's book

**Guard C-8.** Replaces KPIA-39, widened.

#### FR-Q5 · Limit the personal and commercial data the HR system retains

`Major` · 5 points · Stage 5 · [KIN-180](https://kinexus.youtrack.cloud/issue/KIN-180)

> **As a** data protection officer
> **I want** the HR system to hold the minimum commercial detail it needs
> **So that** automating appraisals does not widen our PII exposure

Replaces KPIA-40. AC5 DPIA is a gate before Stage 4 ships.

---

## Traceability — superseded backlog

All 47 issues below are **Obsolete** in YouTrack, each carrying its replacement in its summary.

| Superseded | Story | Replaced by |
|---|---|---|
| [KIN-10](https://kinexus.youtrack.cloud/issue/KIN-10) | KPIA-E1 Metric Library | Epic F |
| [KIN-11](https://kinexus.youtrack.cloud/issue/KIN-11) | KPIA-E2 Fact Ingestion | Epic F |
| [KIN-12](https://kinexus.youtrack.cloud/issue/KIN-12) | KPIA-E3 Aggregation Engine | Epic F |
| [KIN-13](https://kinexus.youtrack.cloud/issue/KIN-13) | KPIA-E4 Team Roll-Up | Epic F |
| [KIN-14](https://kinexus.youtrack.cloud/issue/KIN-14) | KPIA-E5 Positions | Epic P |
| [KIN-15](https://kinexus.youtrack.cloud/issue/KIN-15) | KPIA-E6 Logic ERP | Epic F |
| [KIN-16](https://kinexus.youtrack.cloud/issue/KIN-16) | KPIA-E7 Governance | Epic Q |
| [KIN-17](https://kinexus.youtrack.cloud/issue/KIN-17) | KPIA-1 Define a reusable metric | FR-F1 |
| [KIN-18](https://kinexus.youtrack.cloud/issue/KIN-18) | KPIA-2 Preview a metric | FR-F2 |
| [KIN-19](https://kinexus.youtrack.cloud/issue/KIN-19) | KPIA-3 Bind a metric | FR-F3 (widened to goals) |
| [KIN-20](https://kinexus.youtrack.cloud/issue/KIN-20) | KPIA-4 Starter metric library | FR-B8 (re-scoped) |
| [KIN-21](https://kinexus.youtrack.cloud/issue/KIN-21) | KPIA-5 Turn automation off | FR-F4 |
| [KIN-22](https://kinexus.youtrack.cloud/issue/KIN-22) | KPIA-6 Nightly ingest | FR-F5 |
| [KIN-23](https://kinexus.youtrack.cloud/issue/KIN-23) | KPIA-7 No double-counting | FR-F6 |
| [KIN-24](https://kinexus.youtrack.cloud/issue/KIN-24) | KPIA-8 Reversals | FR-F7 |
| [KIN-25](https://kinexus.youtrack.cloud/issue/KIN-25) | KPIA-9 Exception queue | FR-F8 |
| [KIN-26](https://kinexus.youtrack.cloud/issue/KIN-26) | KPIA-10 Resolve exception | FR-F8 |
| [KIN-27](https://kinexus.youtrack.cloud/issue/KIN-27) | KPIA-11 Observe sync runs | FR-F9 |
| [KIN-28](https://kinexus.youtrack.cloud/issue/KIN-28) | KPIA-12 Degrade gracefully | FR-F10 |
| [KIN-29](https://kinexus.youtrack.cloud/issue/KIN-29) | KPIA-13 Event-sum | FR-F11 |
| [KIN-30](https://kinexus.youtrack.cloud/issue/KIN-30) | KPIA-14 Ratio | FR-F11 |
| [KIN-31](https://kinexus.youtrack.cloud/issue/KIN-31) | KPIA-15 Duration | FR-F11 |
| [KIN-32](https://kinexus.youtrack.cloud/issue/KIN-32) | KPIA-16 Snapshot | FR-F11 |
| [KIN-33](https://kinexus.youtrack.cloud/issue/KIN-33) | KPIA-17 Source documents | FR-F14 |
| [KIN-34](https://kinexus.youtrack.cloud/issue/KIN-34) | KPIA-18 Auto-approve synced | FR-F15 |
| [KIN-35](https://kinexus.youtrack.cloud/issue/KIN-35) | KPIA-19 Manager on team activity | FR-F16 |
| [KIN-36](https://kinexus.youtrack.cloud/issue/KIN-36) | KPIA-20 Reports with no KPIs | FR-F16 |
| [KIN-37](https://kinexus.youtrack.cloud/issue/KIN-37) | KPIA-21 Every level | FR-F16 (re-estimate) |
| [KIN-38](https://kinexus.youtrack.cloud/issue/KIN-38) | KPIA-22 Split credit | FR-F17 |
| [KIN-39](https://kinexus.youtrack.cloud/issue/KIN-39) | KPIA-23 Drill to person | FR-F14 |
| [KIN-40](https://kinexus.youtrack.cloud/issue/KIN-40) | KPIA-24 Sales Person tree | FR-F18 |
| [KIN-41](https://kinexus.youtrack.cloud/issue/KIN-41) | KPIA-25 Reports read facts | FR-F19 |
| [KIN-42](https://kinexus.youtrack.cloud/issue/KIN-42) | KPIA-26 Quota coverage | FR-F20 |
| [KIN-43](https://kinexus.youtrack.cloud/issue/KIN-43) | KPIA-27 Recompute once | FR-A5 + FR-F9 (one function) |
| [KIN-44](https://kinexus.youtrack.cloud/issue/KIN-44) | KPIA-28 Positions | FR-P1 |
| [KIN-45](https://kinexus.youtrack.cloud/issue/KIN-45) | KPIA-29 Backfill positions | FR-P2 |
| [KIN-46](https://kinexus.youtrack.cloud/issue/KIN-46) | KPIA-30 Reorg keeps credit | FR-P3 |
| [KIN-47](https://kinexus.youtrack.cloud/issue/KIN-47) | KPIA-31 Vacant and acting | FR-P4 |
| [KIN-48](https://kinexus.youtrack.cloud/issue/KIN-48) | KPIA-32 Logic ERP surface | FR-F12 |
| [KIN-49](https://kinexus.youtrack.cloud/issue/KIN-49) | KPIA-33 Ingest Logic ERP | FR-F12 |
| [KIN-50](https://kinexus.youtrack.cloud/issue/KIN-50) | KPIA-34 Credentials | FR-F13 |
| [KIN-51](https://kinexus.youtrack.cloud/issue/KIN-51) | KPIA-35 Reconcile totals | FR-F21 |
| [KIN-52](https://kinexus.youtrack.cloud/issue/KIN-52) | KPIA-36 Dispute | FR-Q1 |
| [KIN-53](https://kinexus.youtrack.cloud/issue/KIN-53) | KPIA-37 Freeze | FR-Q2 (widened to periods) |
| [KIN-54](https://kinexus.youtrack.cloud/issue/KIN-54) | KPIA-38 Self-produced metrics | FR-Q3 |
| [KIN-55](https://kinexus.youtrack.cloud/issue/KIN-55) | KPIA-39 Fact visibility | FR-Q4 (position guard added) |
| [KIN-56](https://kinexus.youtrack.cloud/issue/KIN-56) | KPIA-40 Limit PII | FR-Q5 |

### Why the old backlog was rebuilt rather than edited

Three reasons, all in SRS §4:

1. **It encoded a superseded decision.** `KPI_AUTOMATION_STRATEGY.md` resolved D-3 as *both* `KPI` and `Individual Goal` are Phase 0 targets. The decision record and the backlog both said *KPI first*. **No story among the 40 mentioned `Individual Goal`**, while the strategy's own Phase 0 exit criteria required it.
2. **Two of its Critical gaps did not exist.** The requirements document was written without repository access — its own decision record lists that as blocker #1. KPI validation and weightage enforcement both exist. KPIA-46, flagged as *pull ahead of all other work*, was largely already built.
3. **It covered measurement only.** Nine defects, entitlement, authoring governance, scoring explainability, calibration, OKR mode and India-specific capability had no representation at all.

---

*Generated from OBJECTIVES_AND_KPI_SRS.md v2.0. Full acceptance criteria in YouTrack project KIN.*
