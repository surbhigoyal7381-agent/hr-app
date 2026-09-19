# Product context — Alvora HR

**Version 0.1 · 24 August 2026 · Status: DRAFT for founder review**
Read by every agent on this team before it does anything.

> **How this file was built, and its one big weakness.** It was assembled from the
> AllAboutHR project documents — `alvora-brief.md` (v1, Aug 2026),
> `objectives-kpi-srs.md` and `objectives-kpi-backlog.md` (v2.0, 24 Aug 2026), and the
> competitive-intel pack (docs 00–25, Jul 2026). **It was NOT built by reading the
> code at `C:\Surbhi-Git\hr-app`** — folder access was not granted during the session
> that wrote it. Every claim about what the code does is marked
> `[UNVERIFIED — read the repo]`. The first agent with repo access should confirm or
> correct those lines and bump the version. Until then, treat this as a good brief,
> not a survey.

---

## 1 · What we are building

**Alvora HR** is a talent and performance management and people engagement platform,
built to raise the experience of people at work — professionally, visibly and
measurably.

It is **not positioned as an HRMS.** It contains the record-keeping an HRMS contains,
but that is the floor, not the product. An HRMS answers *what happened*. Alvora
answers *what is happening to performance and to people, and what to do about it*:
goals produce evidence, evidence produces ratings, ratings produce calibration,
calibration produces pay and progression, and the loop changes the next cycle.

**The two mechanics that carry the whole story:**

- **Evidence-first** — progress on a goal does not move because someone typed a
  number. It moves when evidence is submitted and approved, with per-type validation,
  duplicate detection, an audit log, and a rating-scale snapshot taken at generation so
  a rating can never be reinterpreted against a later scale. This is what makes a
  rating *defensible* rather than *asserted*. `[UNVERIFIED — read the repo]`
- **Closed-loop** — goals → appraisal → calibration → compensation worksheet → policy
  checks → approval → letters → payroll posting. Most mid-market platforms stop at the
  rating and hand the rest to a spreadsheet.

**The line:** *every rating traces to evidence; every decision closes into an outcome.*

**Portfolio placement.** AllAboutHR is the house (services business, since April 2019);
Alvora is the platform brand within it. Alvora HR is this product; Alvora Hire
(recruitment) and Alvora Gig (contractor workforce) are siblings in separate repos,
**not modules of this one.**

### Language discipline (agents: this binds your writing too)

**Use:** talent and performance management platform · people engagement · people
experience at work · evidence-first · closed-loop · defensible decisions · calibration
· pay-for-performance.

**Avoid:** *HRMS* as the headline noun · *HR software* · *employee database* ·
*engagement* as an unmeasured abstraction · any claim that the analytics or pulse layer
ships today.

---

## 2 · Who we serve

Target tenant: **50–1,000 employees.** Indian mid-market first. Highly security- and
privacy-conscious buyers — security review is a real gate in the sales cycle, not a
formality.

| Persona | Their day | What they need from us | Device / context |
|---|---|---|---|
| **HR Manager / HR head** (economic buyer's proxy, our densest user) | Runs cycles for the whole company with a team of two or three. Chases completion, defends ratings, answers "why is my number wrong". | Configure a cycle once and have it run. Bulk-assign to hundreds. See who is not ready *before* the cycle opens. Defend a rating with a record, not a recollection. | Laptop, many tabs, month-end pressure |
| **Line manager** | Sets goals for 5–15 people, approves, reviews, calibrates. Performance work competes with the day job and loses. | Approve in one action, not a routing workflow. A running 1:1 agenda that remembers what was left open. Judgement informed by automation, never replaced by it. | Laptop and phone, between meetings |
| **Employee** | Wants to know what they are measured on, where they stand, and that it is fair. | See how a rating was calculated, in words they understand. See the documents behind their number. Challenge it without being able to edit it. | Mixed; a large share are phone-only |
| **Frontline / shift employee and their supervisor** | Plant, retail, field. Often skipped by performance processes entirely. | A review that completes in two minutes on a phone. Their own language. `[roadmap — FR-N2/N3, Stage 8]` | Shared or low-end phone, poor connectivity |
| **CXO / founder** | Wants one number they can trust and act on. | Company and BU roll-ups that are arithmetically correct — one authoritative total, not two reports disagreeing. | Phone, five minutes |
| **Customer IT / security reviewer** | Gates the purchase. | No inbound firewall rule. Encrypted per-tenant credentials. Evidence of isolation, audit and retention. A security review that takes two weeks, not two months. | Their own questionnaire |
| **Data protection officer / compliance** | Owns the DPDP and (where relevant) AI Act exposure. | Retention that is declared and enforced, an auditable AI decision chain, minimum PII footprint. | — |

**The dependency runs one way:** experience is the input, engagement is the sentiment,
performance is the output, talent is the compounding asset. A slice that improves the
manager's convenience by degrading the employee's experience has failed, whatever the
adoption number says.

---

## 3 · Stage and honest build status

The MVP is complete and real; the intelligence layer is the build. **In any
client-facing document, state built vs roadmap explicitly.** Overclaiming here is the
fastest way to lose a mid-market CHRO.

| Pillar | Status | Note |
|---|---|---|
| Performance management | 🟢 Built | Appraisal cycles, cascaded goals, evidence, calibration matrix with boundary flags and locked audit trail |
| Compensation / reward | 🟢 Built, ahead of category | Merit cycles, budgets, policy engine, approvals, letters, payroll posting. Reported as 32 DocTypes, 7 reports, 177 tests `[UNVERIFIED — read the repo]` |
| Core HR & absence | 🟢 ~90% | Employee master, org hierarchy, leave, attendance, geo-fenced shifts |
| Onboarding | 🟡 Partial | Tasks and templates built; offboarding not evidenced |
| One-to-one & feedback | 🟡 Partial | Check-in exists without agenda/action items; upward feedback single-rating |
| People engagement (pulse, eNPS) | 🔴 In scope, not built | Committed direction, no code |
| Learning & competence | 🔴 Not built | Newly in scope |
| Talent & succession | 🔴 Stub | Talent flags only; 9-box and slates not built |
| Analytics / people intelligence | 🔴 **The gap** | No analytics module |

*Source: `alvora-brief.md` v1, Aug 2026, whose build-status claims came from a direct
read of this repo. Re-verify before quoting externally — the code has moved since.*

### Current work in flight

The active plan is the **Alvoraa Objectives & KPI backlog v2.0** (24 Aug 2026):
17 epics, 132 stories, 698 points, tracked in **YouTrack project KIN**, with full
Given/When/Then acceptance criteria living in YouTrack rather than in the backlog file.

⚠ **`backlog/KPI_AUTOMATION_BACKLOG.md` in this repo is superseded.** It is the
40-story KPIA-1..40 backlog; all 47 of its issues (KIN-10 to KIN-56) are marked
Obsolete. It was rebuilt rather than edited for three reasons: it encoded a superseded
decision (KPI-only, when the strategy required Individual Goal too), two of its
Critical gaps did not actually exist in the code, and it covered measurement only.
**Agents must not plan from that file.** Read `objectives-kpi-backlog.md` v2.0 and its
SRS instead, and treat YouTrack as the definition of done.

---

## 4 · Deployment and architecture

- **Framework:** Frappe. Apps in this bench include `hrms`, `alvoraa_goals`,
  `alvoraa_portal`, `alvox_compensation`. `[folder names observed; versions and app
  list UNVERIFIED — run `bench version` and `ls apps/`]`
- **Repo also contains:** `backlog/`, `deploy/`, `scripts/`, `demo/`, `.github/`,
  `.claude/`.
- **Tenancy:** multi-tenant SaaS with per-tenant provisioning and plan-based
  entitlement (Starter / Business / Enterprise).
- **Integrations:** outbound polling only — no inbound firewall rule required of the
  customer. Per-company encrypted credentials. Target sources: Logic ERP, Tally, Zoho,
  customer CRM, and direct SQL (a differentiator — only Profit.co offers it in the
  competitive scan).

> ⚠ **A discrepancy the team must resolve, not paper over.** The competitive-intel pack
> (docs 15/16/25) describes a Postgres + row-level-security + purpose-tag architecture
> with a `platform/db` layer. That is **not** the Frappe/MariaDB stack this repo runs
> on. Either those documents describe a greenfield platform that is a different product
> from Alvora HR, or they are aspirational. Agents must build against **this repo's
> actual stack** and flag any requirement that assumes the other one. Owner: founder.
> Until resolved, docs 15/16/25 are context, not specification.

---

## 5 · Geography, language, compliance

- **Countries:** India primary. EU exposure is real enough that the backlog carries AI
  Act obligations — confirm whether that is current customers, target customers, or
  anticipation. `[ASSUMPTION — founder to confirm]`
- **Languages:** English and Hindi at parity on employee-facing surfaces; other
  scheduled languages on the frontline roadmap (FR-N3).
- **Data protection:** India's **DPDP Act 2023**, with the **DPDP Rules 2025 notified
  14 November 2025** and a phased schedule — Data Fiduciary obligations becoming fully
  effective roughly 18 months from notification (**around May 2027**). Breach handling:
  immediate intimation to affected Data Principals and the Board, detailed report to
  the Board within 72 hours. *Confirm the exact phase dates and our Data Fiduciary /
  processor position with counsel — we are not lawyers.*
- **AI regulation:** the EU AI Act's **Article 5 prohibitions have been in force since
  2 February 2025** and include emotion-inference systems in the workplace — that
  constrains us **today**, not in future. The high-risk (Annex III, which covers
  employment and worker management) obligations were **provisionally deferred from
  2 August 2026 to 2 December 2027** by the Digital Omnibus agreement; as of the most
  recent source read (27 May 2026) that deferral was **provisionally agreed but not yet
  in force**. **Re-check current status before relying on it** — and note the deferral
  buys time, it does not remove the obligation.
- **Data residency:** India default. `[ASSUMPTION — confirm the contractual position]`
- **Statutory surfaces we touch:** performance-linked increments and variable pay
  against CTC (FR-N1), PIP documentation intended to withstand Indian labour-law
  scrutiny (FR-N4 — **requires qualified employment-law review before release**).
- **Named compliance owner:** `TODO — founder to name a person, not a function.`

---

## 6 · What we deliberately do NOT do

The most useful list on this page. These are refusals, not gaps.

1. **No payroll processing.** We post to payroll; we do not run it.
2. **No AI-set or AI-proposed ratings, ever** (FR-J4). The number that affects
   someone's pay is chosen by an accountable human. Administrative rating reliability
   is low enough that an AI rating is a liability, not a feature.
3. **No emotion, voice or facial analysis** (FR-J6). Architecturally impossible, not
   merely unbuilt — so a well-meaning feature request cannot add it later.
4. **No passive behavioural monitoring as a performance input** (FR-H7). We measure
   outcomes, not activity signals. The evidence is unambiguous: monitoring does not
   improve performance and does raise stress.
5. **No name matching to attribute a transaction to a person** (FR-F8). Unmappable
   records go to a visible queue; nothing is silently dropped or silently guessed.
6. **Never zero when a source is unreachable** (FR-F10). Hold the last known value —
   zero is indistinguishable from poor performance.
7. **No forced bell curve by default** (FR-I4). Distribution is visible; enforcement is
   off unless a customer switches it on.
8. **No second data model for OKRs** (FR-M1). OKR is a presentation mode over the same
   objects.
9. **No inbound firewall rule** asked of the customer (FR-F13). Outbound polling only.
10. **No feature-parity race with Darwinbox, Keka or Workday.** We win on evidence,
    explainability and the closed loop, not on module count.

---

## 7 · Competitive frame

Positions below come from the project's competitive analysis (Jul–Aug 2026) and are
**recall-risk by nature** — competitor feature sets move. Agents must mark any claim
they did not re-verify as `[recall — verify]`.

| Product | What they are good at | What we do differently |
|---|---|---|
| Frappe HR (standard) | The record-keeping floor, free and solid | The consequence loop above it: evidence, calibration, pay |
| Keka | Strong Indian mid-market presence; documents cycle-settings freeze precisely | Automated sync with visible freshness — Keka requires a manual click per goal (FR-F22) |
| Darwinbox | Broad enterprise suite | We are smaller, sharper, explainable, and priced for 50–1,000 |
| HROne | The only vendor found driving increments/variable pay from ratings | We intend parity there (FR-N1) plus the evidence chain underneath it |
| Profit.co / Perdoo | Configurable rating bands; guardrail Key Results | Both, plus goals-and-KPIs in one model rather than an OKR silo |
| Peoplebox, Betterworks, Culture Amp, WorkBoard, SAP, Oracle, Workday | Each strong somewhere the backlog cites explicitly | See below |

**Our claimed whitespace** — the things the scan found nobody doing, and therefore the
things worth building well:

- Mid-cycle goal revision with reason, approval and versioning (FR-E4)
- A replayable **Rating Derivation** record, and showing the employee their own
  derivation in plain language (FR-G4, FR-G5)
- Manager leniency/severity surfaced *before* the calibration meeting (FR-L3)
- AI that critiques an existing goal rather than only drafting one (FR-J2)
- A frontline review that completes in two minutes on a phone (FR-N2)
- Adapters for Tally, Zoho and Indian mid-market CRMs (FR-N5)
- Rating-driven increment and variable pay against CTC (FR-N1)

---

## 8 · Success measures

Per pillar, from the positioning brief. Baselines are not yet instrumented — that is
itself the top analytics gap.

| Pillar | Measure | Baseline | Target |
|---|---|---|---|
| Talent | Quality of hire, time-to-productivity, internal fill rate | not measured | `TODO` |
| Performance | Goal completion, rating distribution integrity, pay-for-performance correlation | not measured | `TODO` |
| Engagement | eNPS **trend**, participation rate, action-closure rate on raised themes | not built | `TODO` |
| Experience *(the driver)* | Task completion without HR intervention, cycle turnaround time, self-service adoption | not measured | `TODO` |

**On eNPS:** ship it because buyers ask for it by name, but position it as a trend line,
not a diagnostic — it collapses an 11-point scale into three buckets and discards
passives. Also: "Net Promoter", "Net Promoter Score" and "NPS" are registered marks;
the calculation is public but the name carries commercial-use risk in branded UI.
Confirm with counsel before it ships.

**Banned as success measures:** logins, page views, "engagement" with no instrument
behind it.

---

## 9 · Constraints

- **Team:** small. `TODO — state the actual number; it changes what "thin slice" means.`
- **Cost ceilings:** see `nfr-budget.md` §Cost. AI spend is budgeted per action and per
  employee per month, not left open.
- **The sales gate is security review.** For a 50–1,000-employee buyer with a security
  reviewer in the loop, an unanswered isolation or retention question costs more
  calendar time than a missing feature. Treat security work as go-to-market work.
- **Deadlines:** `TODO — and say why each is hard.`

---

## 10 · Open risks the team must not lose

| # | Risk | Why it matters | Owner |
|---|---|---|---|
| 1 | 🔴 **Appraisal permission defect** — Employee-role users reportedly can read and write colleagues' appraisals including `manager_internal_notes` and `potential_rating`; ~169 uses of `ignore_permissions=True`; no row-scoping on `Appraisal Extension`. Estimated ~1 engineer-day. `[UNVERIFIED — read the repo. Verify FIRST.]` | For a platform sold on fairness and defensibility this is a positioning risk, not just a bug. For a security-conscious buyer it is a lost deal. Fix before the next demo. | Engineering |
| 2 | **Entitlement is cosmetic** — `has_feature()` reportedly called nowhere outside `subscription.py`; the shell provisioner and the API disagree on which plan includes Goals. `[UNVERIFIED]` (FR-O1, FR-O6) | A priced feature that is not enforced is not priced. | Engineering |
| 3 | **Wrong numbers before new numbers** — Epic A: weightage budget ignores objectives; attainment cannot tell unmeasured from measured-as-zero (a perfect safety record scores as failure); cascade double-counts. | Building measurement on top of arithmetic that is wrong multiplies the error. Stage 0 exists for this. | Engineering |
| 4 | **Architecture doc mismatch** (see §4) | Two incompatible pictures of the stack in one project. | Founder |
| 5 | **`PRODUCT_STRATEGY.md` §10 still lists learning, succession, pulse and 360° as "will not build"** — four things the current positioning promises. | Engineering will keep de-scoping what sales sells. | Founder |
| 6 | **Analytics is the gap** and nothing in §8 is instrumented. | Every success measure above is currently aspirational. | Founder |
| 7 | **"Alvora" trademark search not done** in Indian HR-services and software classes. | Rename risk after brand spend. | Founder / counsel |

---

## Open questions

| Question | Owner | Blocks |
|---|---|---|
| Grant repo access so this file can be verified against code | Surbhi | Everything marked `[UNVERIFIED]` |
| Actual employees-per-tenant distribution today and at 12 months | Founder | NFR volume targets |
| Is EU exposure current, target, or anticipated? | Founder | Whether AI Act work is P0 or P2 |
| Data residency contractual position | Founder / counsel | Hosting decisions |
| Named compliance owner | Founder | Every ⚠ COMPLIANCE flag |
| Which architecture doc set is authoritative | Founder | Any slice citing docs 15/16/25 |

## Assumptions

- `[ASSUMPTION]` Target tenant size 50–1,000 employees, per the instruction that
  created this file. Note the project's own PRD says Indian mid-market **100–2,000**
  and load-tests at 2,000 — the NFR budget resolves this by designing for 1,000 with
  headroom to 2,000.
- `[ASSUMPTION]` India-primary, EN/HI, DPDP-governed.
- `[ASSUMPTION]` Frappe/MariaDB is the real stack; docs 15/16/25 are not.
- `[ASSUMPTION]` All build-status and defect claims inherited from `alvora-brief.md`
  are still true as of today. They date from 19 August 2026.
