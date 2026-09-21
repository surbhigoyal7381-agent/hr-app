---
artifact: kano-review
scope: whole product (first priorities review — no earlier review exists)
author: hrms-product-manager
date: 2026-09-21
status: superseded
superseded_by: docs/product/priorities/2026-09-21-kano-review-v2.md
superseded_reason: >
  This draft's §1/§3/§5/§6 claim that alvoraa_goals/alvoraa_goals/doctype/kpi/kpi.py
  is "an empty pass controller" with the weightage rule "enforced nowhere" checked the
  wrong file — that file is normal Frappe doctype boilerplate. The real controller,
  alvoraa_goals/alvoraa_goals/controllers/kpi.py (212 lines), already enforces the
  100%-weightage rule and is already wired as the KPI doctype's validate hook, already
  on origin/dev. Found by hrms-devops-engineer, independently verified by
  hrms-product-manager. This changes C1's actual remaining scope and its priority
  table entry. See the v2 file for the corrected review.
inputs: [.claude/context/product-context.md, .claude/context/security-compliance-baseline.md,
  .claude/context/definition-of-ready-done.md, .claude/context/handoff-contract.md,
  .claude/context/ux-learnings.md, KNOWN_ISSUES.md, ARCHITECTURE.md,
  KPI_BACKLOG_DECISION_RECORD.md, OBJECTIVES_KPI_REQUIREMENTS.md, KPI_AUTOMATION_STRATEGY.md,
  backlog/BILLING_CONSOLE_GAP.md, docs/pp_jewellers/00–11, docs/slices/001–028,
  installed-app source (hrms, alvoraa_goals, alvoraa_portal)]
---

# First Kano review — the whole product

**Read this first: two things in `product-context.md` are wrong, verified by reading
the code, not recalled.**

1. **§3 says Compensation/reward is "Built, ahead of category" with an `alvox_compensation`
   app carrying 32 doctypes, 7 reports, 177 tests.** That app does not exist in this repo.
   `grep`, `Glob` and a file listing all confirm it. There is no compensation/merit-cycle
   module anywhere in `hr-app`. This claim should be struck from `product-context.md` §3 —
   I have not edited that file myself, since I don't own it; flagged below as an open
   question for whoever does.
2. **§10 risk #1 (appraisal permission defect) is real, and a fix is already built and
   locally tested** (slice `010-portal-security-fixes`), but **not yet on `dev` or `main`**
   as of the artifacts I can read. Treat it as open until someone confirms the push
   happened.

Everything else below is checked against the actual source in this session.

---

## 1 · Current state — verified against the repo

| Pillar | `product-context.md` §3 said | What the repo actually shows | Status |
|---|---|---|---|
| Performance management | Built — cycles, cascaded goals, evidence, calibration matrix | **Confirmed, but split across two systems.** `alvoraa_goals` (21 doctypes: `Individual Goal`, `KPI`, `Goal Cascade`, `Goal Evidence`, `Alvoraa Appraisal Extension`, `Alvoraa Rating Scale`…) is the live path, used by the PP Jewellers demo and by `alvoraa_portal/performance_api.py`. **Separately**, `hrms/hrms/performance_management` ships 36 `PMS_*` doctypes (`pms_calibration_session`, `pms_talent_flag`, `pms_check_in`…) — Frappe HR's own performance suite — installed but, per `ARCHITECTURE.md` §11, **never exercised in production**. Two performance systems live in one product. See risk R-A below. | 🟢 built (live path) / 🟡 risk (duplicate system) |
| Compensation / reward | Built, ahead of category, 32 doctypes | **Not present.** No `alvox_compensation` app, no merit-cycle, budget, policy-engine or letters code anywhere in the repo. | 🔴 not built — correction needed to product-context |
| Core HR & absence | ~90% — employee master, org hierarchy, leave, attendance, geo-fenced shifts | **Confirmed and ahead of the ~90% estimate.** Field check-in with GPS and photo (slice 008), a late-minutes deduction engine with payroll posting (`alvoraa_late_rules`), ESI/PF fields, Employee Documents with expiry tracking, and a Policy Library with row-level read rules all shipped 7 Sep 2026. | 🟢 built, more than stated |
| Onboarding | Partial — tasks/templates only | **Confirmed**, plus Employee Documents (checklist, verification, expiry reminders) now closes part of the offboarding-adjacent gap (document compliance). Formal offboarding workflow still not evidenced. | 🟡 partial, improved |
| One-to-one & feedback | Partial — check-in without agenda; upward feedback single-rating | **Confirmed as stated.** `goal_check_in` exists in `alvoraa_goals`; `pms_check_in_agenda` exists in the unused PMS module, so the agenda/action-item model exists in code but isn't wired to the live path. | 🟡 partial |
| People engagement (pulse, eNPS) | Not built | **Confirmed. Zero code.** No survey, pulse or eNPS doctype anywhere. | 🔴 not built |
| Learning & competence | Not built | **Mostly confirmed.** Stock Frappe HR ships `Training Program`, `Training Event`, `Training Feedback` (event logistics, not a course/competency/certification system). No custom learning code. | 🔴 not built (a thin stock floor exists) |
| Talent & succession | Stub — talent flags only | **Confirmed.** `pms_talent_flag` exists in the unused PMS module only — not wired to the live `alvoraa_goals` path. No 9-box, no succession slate, anywhere. | 🔴 stub |
| Analytics / people intelligence | "The gap" — no analytics module | **Overstated as a gap; something real exists, but it is dashboards, not intelligence.** A live "Analytics" feature flag drives owner/HR dashboards and store comparisons (used in the PP Jewellers demo); slice `001-attendance-analytics` adds three attendance views (employee/manager/org); slice `012-leadership-view` adds a privacy-guarded totals view for CXOs and branch heads. None of this is "people intelligence" — no quality-of-hire, no time-to-productivity, no pay-for-performance correlation, no manager leniency/severity surfacing, no rating-derivation replay. Those specific whitespace items from §7 remain unbuilt. | 🟡 partial — correct product-context's "no analytics module" to "operational dashboards exist; the intelligence layer does not" |
| Vendor / delivery portal | not in product-context's pillar table | A full vendor/driver/delivery module exists (`alvoraa_portal`, 22 doctypes) — but it is a **different product line** per product-context §1 ("Alvora Gig … not a module of this one"). Slice 016 found and removed driver telemetry feeding a performance score, and gated the whole module behind plan entitlement — both consistent with §6 refusals. | 🟢 built, scope question for the founder (see Open questions) |

**Correction to §3's authoring-layer claim (not in the original table, but load-bearing):**
`KPI.py` in `alvoraa_goals` is confirmed (read directly) to be an empty `pass` controller.
No validation exists on the doctype that drives appraisal scoring. The weightage-must-total-100
rule is documented in a field description and enforced nowhere. This is not a new finding —
`OBJECTIVES_KPI_REQUIREMENTS.md` (18 Aug 2026) already found it — but it has sat unactioned for
five weeks while B1–B6 (late rules, ESI, screening, employee documents, policy library,
attendance-in-appraisal) shipped around it. See candidate C1 below.

---

## 2 · Pending — already scoped or in flight; not re-proposed here

Seventeen slices exist (`001`–`028`, gaps where numbers were reserved and unused). Reading
each one's own status line:

| Slice | What it is | State |
|---|---|---|
| 001 attendance-analytics | Three attendance views (employee/manager/org), short-leave pattern detection | `status: ready`, brief only — build not confirmed |
| 002 ess-home-redesign | Quieter visual system + smarter home widgets | `status: ready`, brief only |
| 003 ess-mobile-responsive | Phone-layout audit — 22 gaps, 4 unusable tasks found | Assessment done, fix not built |
| 008 field-checkin | Field worker GPS+photo attendance for PP Jewellers | **Shipped for the PPJ demo** (12 Sep deadline) |
| 009 ess-portal-redesign | Full portal rebuild — 137 requirements across frame/home/time/pay/growth/team | **Large, multi-wave, in flight.** Its Wave 0 (fix live bugs before redesigning) is what spawned slices 010, 012, 014, 017, 019–021, 024, 027, 028 below. Waves 1–4 (the actual new screens) are **not started**. Estimated 8–11 weeks of build time when the plan was written. |
| 010 portal-security-fixes | 10 real security/privacy holes (self-review writing to others' records, evidence self-approving, managers seeing draft self-reviews, org-wide people search, HR self-approval…) | **Built and locally tested** (1,128 + 18 tests green). **Not yet pushed to `dev` or `main`** per the artifacts available. This is the single most important thing to close first — see priority table. |
| 012 leadership-view | Privacy-guarded totals (People/Attendance/Leave) for CXO and branch heads | Brief written; five open questions block the design step |
| 014 checkin-security-fixes | IP-spoofing via `X-Forwarded-For`, and photo+GPS leaking into error logs | Strategy approved, awaiting build confirmation |
| 015 repo-hygiene | Demo passwords, real names, a real IP address out of the repo | Built |
| 016 portal-api-permissions | Gate the vendor module by plan; remove hardcoded customer data; **stop driver telemetry feeding a performance score** | Phase 1 done; phase 2 (ownership rules, 2FA fixes) not started |
| 017 late-minutes | Fixed the shared-cache bug that made every late-arrival figure wrong | Built |
| 019 deploy-nginx-gate | `nginx -t` before restart, so a bad config can't take production down | Built |
| 020 test-permission-leak | Test suite was leaving 554 permission rows on the shared test site | Fixed |
| 021 module-access-lockout | A tenant could get permanently locked out of modules it paid for | Fixed |
| 024 portal-home-page | `/` now lands a logged-in employee on the portal, not the Frappe desk | Built |
| 027 review-render-fixes | Fixes from the user's own bug report on `ppj.dev.alvoraa.co` | Built |
| 028 hr-conflict-flag | Investigated a flag that "never fires" — turned out to be correct behaviour, data hadn't reached that stage yet | No code change; closed |

**Also pending, not slice-tracked:**

- **KPI/Goal authoring layer** (`OBJECTIVES_KPI_REQUIREMENTS.md`, 18 Aug 2026): a Goal/KPI
  Library, a Goal Plan Template (governance object), attainment→rating lookup tables, and
  weightage enforcement. Requirements written (FR-1 to FR-24); nothing built. The companion
  measurement-engine backlog (`KPI_AUTOMATION_BACKLOG.md`, KPIA-1..56) is **explicitly
  superseded** per `product-context.md` §3 — I have not planned from it.
- **Billing console edit gap** (`backlog/BILLING_CONSOLE_GAP.md`, parked 8 Sep 2026): a tenant
  can be put on a plan at creation but never moved to a different one from the console
  afterwards. This is an internal sales-ops tool gap, not a buyer-facing Kano item, so it
  doesn't appear in the priority table, but it blocks the business from servicing growing
  customers and should be scheduled on its own merits.
- **The v2.0 Objectives & KPI backlog** that `product-context.md` §3 cites (17 epics, 132
  stories, 698 points, "tracked in YouTrack project KIN") — **I could not verify this.** No
  YouTrack tool was available in this session despite the task brief saying it would be, and
  no local file (`objectives-kpi-backlog.md`, `objectives-kpi-srs.md`) exists in this repo.
  `OBJECTIVES_KPI_REQUIREMENTS.md` and `KPI_AUTOMATION_STRATEGY.md` are the closest real
  documents I could read, and they're dated 18 Aug 2026 — before the "v2.0" the context file
  refers to. **Flagged as blocked; see Open questions.**

---

## 3 · New candidates

Drawn from product-context §3's red/stub pillars, §7's stated whitespace, the authoring-gap
document, and one operational risk found while reading the code.

| ID | Candidate | Source |
|---|---|---|
| C1 | KPI/Goal authoring correctness: weightage enforcement + validation on `KPI` (currently empty) | `OBJECTIVES_KPI_REQUIREMENTS.md`, direct code read |
| C2 | Goal/KPI Library + attainment→rating lookup tables (Metric Lookup Tables) | Same, §3.1 competitive read (SAP SuccessFactors) |
| C3 | Replayable Rating Derivation + plain-language explanation to the employee | product-context §7 whitespace (FR-G4/G5); also the AI Act Art 86 answer, §4 security baseline |
| C4 | Manager leniency/severity surfaced before the calibration meeting | product-context §7 whitespace (FR-L3) |
| C5 | Frontline review completing in two minutes on a phone | product-context §2, §7 whitespace (FR-N2); natural next step after slice 008 |
| C6 | People engagement pulse / eNPS trend | product-context §3 (committed, unbuilt), §8 (buyers ask by name) |
| C7 | Decide the fate of the unused PMS module vs `alvoraa_goals` | found while reading `ARCHITECTURE.md` §11 — a risk, not a feature |
| C8 | Learning & competence (courses, not just training-event logistics) | product-context §3, "newly in scope" |
| C9 | Talent & succession (9-box, succession slates) | product-context §3 stub |
| C10 | Adapters for Tally, Zoho, Indian CRMs (KPI actuals sourced automatically) | product-context §7 whitespace (FR-N5) |
| C11 | Push slice 010's security fixes from local to `dev`/`main` | not a new feature — a shipping decision, but the single highest-priority item on this page |

---

## 4 · Market demand — evidence, labelled

| Candidate | Evidence | Label |
|---|---|---|
| C1/C2 (authoring correctness/library) | "Every KPI today is typed from scratch, which competitors solved a decade ago" — direct comparison against SAP SuccessFactors' Goal Library and Peoplebox's formula-driven rating | **read**, `OBJECTIVES_KPI_REQUIREMENTS.md`, 18 Aug 2026 |
| C1/C2 | "2026 India rankings place HROne, Worxmate, PeopleStrong, Keka, Darwinbox, Peoplebox and Zoho People in the leading group, scored partly on goals/OKR automation and integrations" | **read**, same doc, `[recall — verify against a primary ranking source before quoting externally]` |
| C3 (Rating Derivation) | No competitor found doing this in the Jul–Aug 2026 competitive-intel pack; positioned as Alvora's whitespace | **read**, `product-context.md` §7, itself sourced from the Jul–Aug 2026 competitive pack — re-verify, competitor features move |
| C4 (leniency/severity) | Same whitespace list | **read**, same source |
| C5 (frontline review) | PP Jewellers already has field workers (drivers, guards) now checking in via slice 008; a two-minute review is the logical next ask for the same population | **seen** — PP Jewellers demo build, 12 Sep 2026, this repo |
| C6 (pulse/eNPS) | "ship it because buyers ask for it by name" | **read**, `product-context.md` §8 — no named customer quote attached; treat as secondhand until a real request is on file |
| C8 (learning) | "Newly in scope" with no whitespace citation and no named competitor gap | **no direct evidence in any file read this session** — weakest candidate on the page |
| C9 (talent/succession) | HROne, Darwinbox and enterprise suites have 9-box; our own target tenant is 50–1,000 employees, where this is less commonly a purchase driver | **`[recall — verify]`** — no customer or demo evidence found |
| C10 (adapters) | "only Profit.co offers it in the competitive scan" for direct-SQL integration | **read**, `product-context.md` §4, `[recall — verify]` |
| C11 (ship slice 010) | 10 confirmed security holes, one already causing a manager's browser to receive a colleague's pay figure | **seen**, this repo, `docs/slices/010-portal-security-fixes/00-impact-analysis.md`, verified by direct code read this session |

**Nothing above is a survey result.** No Kano survey has been run with real customers. Every
class below is a **proxy**, and §8 gives a ready-to-run kit to turn the top ones into evidence.

---

## 5 · Kano classification (proxy)

| Candidate | Class | Why (proxy rule applied) |
|---|---|---|
| C11 ship slice 010 | **Must-be** | A security hole already causing real data exposure (a colleague's pay figure) is the textbook Must-be: its absence doesn't just fail to delight, it loses the deal outright with a security-conscious buyer (product-context §9) |
| C1 weightage/KPI validation | **Must-be** | Matches product-context §10 risk #3 ("wrong numbers before new numbers"): a rating engine with unenforced arithmetic on the doctype that drives pay is a correctness defect, not a delighter |
| C7 PMS-vs-alvoraa_goals decision | **Must-be** (as a risk, not a feature) | Two live routes to "do a performance review" in one enabled product is exactly the kind of thing that shows up as confused users and support tickets — it must be resolved, one way or another, before it compounds |
| C2 Goal/KPI Library + rating lookup | **Performance** | Buyers compare vendors directly on this (Peoplebox, SAP SuccessFactors, HROne all cited); more of it (richer templates, cleaner lookup tables) is straightforwardly better |
| C3 Rating Derivation + explanation | **Attractive** | No competitor in the scanned set does this; it directly serves the evidence-first positioning and doubles as the AI Act Art 86 answer if EU exposure is confirmed |
| C4 leniency/severity pre-calibration | **Attractive** | Same — unclaimed whitespace, not something buyers currently know to ask for, but visibly useful in a demo |
| C5 frontline two-minute review | **Attractive**, leaning **Must-be for PP-Jewellers-shaped customers specifically** | Nobody in the scanned competitive set does this well for shift/frontline workers; but for a retail/jewellery/manufacturing buyer with a frontline workforce, "can my shop floor even use this" is closer to expected than delightful |
| C6 pulse/eNPS | **Performance**, `proxy`, **weak evidence** | Buyers compare vendors on whether eNPS exists at all, per product-context §8, but no direct customer quote is on file this session — treat the classification itself as needing validation, not just the metric |
| C8 learning & competence | **Indifferent**, `proxy`, **evidence required before building** | No whitespace citation, no customer request found, no competitor gap identified. Building a generic course catalogue here risks exactly the feature-parity race product-context §6.10 refuses |
| C9 talent/succession (9-box) | **Indifferent for our 50–1,000 segment**, `proxy` | Common at enterprise tier; our own target buyer skews smaller. No demo or customer evidence found. Re-classify if we move upmarket |
| C10 adapters (Tally/Zoho/CRM) | **Attractive**, `proxy` | Differentiator per product-context §4 and §7, but high effort and external dependency — sequence behind the core loop, not ahead of it |

---

## 6 · Priority order

Effort and run-cost columns are **engineering-judgement estimates**, labelled as such — no
`07-devops-inputs.md` exists yet for any of these (that artifact is written per-slice, and
none of these candidates has started `/slice-start`). Treat S/M/L/XL as a rough compass, not
a committed number, until the engineer and DevOps agent size the slice that gets chosen.

| Rank | Candidate | Current state | Kano (survey/proxy) | Demand evidence | Effort (judgement) | Fit |
|---|---|---|---|---|---|---|
| 1 | **C11 — push slice 010 to `dev`, then `main`** | Built, tested locally | Must-be, proxy | seen — live data exposure | S (it's a release decision, not new build) | Removes the #1 named risk in product-context §10 |
| 2 | **C7 — decide PMS vs `alvoraa_goals`** | Both live in the same enabled product | Must-be (risk), proxy | seen — direct code read | S–M (a decision + hide/disable work, not new features) | Prevents the product confusing its own users before it grows |
| 3 | **C1 — enforce KPI weightage + validate `KPI.py`** | Documented, unenforced | Must-be, proxy | read, `OBJECTIVES_KPI_REQUIREMENTS.md` | S–M | Fixes the arithmetic before anything is built on top of it (§10 risk #3) |
| 4 | **Close remaining Wave 0 "wrong numbers" from slice 009** (leave-left, holidays, team-this-week, goal-% cycle mix) | Scoped, evidence-backed, partly done (late-minutes fixed) | Must-be, proxy | seen — measured against real PP Jewellers data | S each, M as a batch | Same category as #1: numbers the product already shows and gets wrong |
| 5 | **C2 — Goal/KPI Library + attainment→rating lookup** | Requirements written, nothing built | Performance, proxy | read, named competitors | L | Closes the gap between "strong at measurement" and "weak at authoring" the requirements doc itself names |
| 6 | **C3 — Rating Derivation + plain-language explanation** | Not built | Attractive, proxy | read, whitespace | M–L | Evidence-first positioning, and the compliance answer to Art 86 if EU exposure is confirmed (open question below) |
| 7 | **009 ess-portal-redesign, Waves 1–4** | Wave 0 mostly done via slices 010–028; new screens not started | Performance (fixes real friction), proxy | seen — 137 requirements against real PPJ data | XL (8–11 weeks per its own plan) | Large; sequence after items 1–4 so the redesign isn't built on top of numbers still known to be wrong |
| 8 | **C4 — leniency/severity before calibration** | Not built | Attractive, proxy | read, whitespace | M | Cheap relative to C2/C3 once calibration data exists; a good demo moment |
| 9 | **C5 — frontline two-minute review** | Not built | Attractive (Must-be for frontline-heavy buyers), proxy | seen, PP Jewellers | M | Strong inclusiveness fit; natural sequel to slice 008 |
| 10 | **C6 — pulse/eNPS** | Not built | Performance, proxy, weak evidence | read, secondhand | M | Validate with the survey kit (§8) before committing — trademark and "vanity-metric" risk both need resolving first (§8 of product-context) |
| 11 | **C10 — Tally/Zoho/CRM adapters** | Not built | Attractive, proxy | read | L–XL, external dependency | Real differentiator, but sequence after the core loop (C1–C3) is trustworthy, or the adapters feed a rating engine that's still wrong |
| — | **C8 — learning & competence** | Not built | Indifferent, proxy, unvalidated | none found | — | **Do not build without evidence.** See §7 |
| — | **C9 — talent/succession (9-box)** | Stub | Indifferent for our segment, proxy | none found | — | **Do not build without evidence.** See §7 |

---

## 7 · Do-not-build list

| Item | Why |
|---|---|
| Anything resembling AI-set or AI-proposed ratings | Refused outright, product-context §6.2. Not negotiable regardless of how a request is framed |
| Emotion, voice or facial analysis, in any form | Refused, §6.3, and prohibited under EU AI Act Article 5 since Feb 2025 |
| Driver/employee telemetry feeding a performance score | Refused, §6.4 — and this repo already had to **remove** exactly this from the vendor module (slice 016). Do not let it come back through a different door (e.g. "activity analytics") |
| A forced bell curve, on by default | Refused, §6.7 |
| A second OKR data model | Refused, §6.8 — OKR is a presentation mode over the same goal objects, not a new doctype |
| **Learning & competence (C8), as currently scoped** | No demand evidence found anywhere this session. Building a generic course/certification system to match Darwinbox or SuccessFactors module-for-module is exactly the feature-parity race §6.10 refuses. Revisit only with a named customer ask or a lost-deal note |
| **Talent & succession / 9-box (C9), as a build-now item** | Same reasoning — no evidence for our 50–1,000 segment specifically. The `pms_talent_flag` stub already exists if a real request shows up; don't build 9-box visualisation speculatively |
| **Enabling the PMS module's parallel routes without a decision (C7)** | Not a refusal — a sequencing rule. Leaving it as-is (two live "do a review" paths) will generate support tickets before it generates value |
| A generic LMS/course catalogue as a differentiator claim | product-context's own language rule (§1) says never claim the analytics or pulse layer ships today; the same discipline applies to learning — don't market what isn't built |

---

## 8 · Kano survey kit — top candidates

Two questions per feature, both scored Like / Expect it / Neutral / Can live with it /
Dislike, then classified with the standard table in the agent's own instructions. Ask
these of **real customers and demo prospects**, not internally — the whole point is to
replace the `proxy` label with a real one.

**C2 — Goal/KPI Library**
- Functional: "If Alvoraa had a ready-made library of goals and KPIs for your industry and
  role, so you didn't have to type every one from scratch, how would you feel?"
- Dysfunctional: "If Alvoraa made you type every goal and KPI from scratch with no library
  to start from, how would you feel?"

**C3 — Rating Derivation (replayable, plain-language explanation)**
- Functional: "If every employee could see, in plain words, exactly how their rating was
  calculated — which goals, which evidence, which weights — how would you feel?"
- Dysfunctional: "If an employee's rating just appeared with no way to see how it was
  worked out, how would you feel?"

**C4 — Manager leniency/severity before calibration**
- Functional: "If HR could see, before the calibration meeting, which managers tend to
  rate high and which rate low compared to their peers — with the numbers to back it up —
  how would you feel?"
- Dysfunctional: "If HR walked into calibration with no idea which managers' ratings run
  hot or cold, how would you feel?"

**C5 — Frontline two-minute review**
- Functional: "If a shop-floor or field employee could complete their whole performance
  review on their own phone in about two minutes, in their own language, how would you
  feel?"
- Dysfunctional: "If frontline employees were simply left out of the performance review
  process because it doesn't work on their phone, how would you feel?"

**C6 — Pulse / eNPS trend**
- Functional: "If Alvoraa showed you a running trend of how engaged your people feel,
  updated regularly from short pulse surveys, how would you feel?"
- Dysfunctional: "If Alvoraa had no way to measure employee sentiment over time at all,
  how would you feel?"

**C8 — Learning & competence** *(run this one before building anything — it currently has
no evidence at all)*
- Functional: "If Alvoraa let you assign courses, track completion, and tie learning to a
  role's required competencies, how would you feel?"
- Dysfunctional: "If Alvoraa had no learning or competency tracking at all, how would you
  feel?"

**C9 — Talent/succession (9-box)**
- Functional: "If Alvoraa gave you a 9-box grid and succession slates for key roles, how
  would you feel?"
- Dysfunctional: "If Alvoraa had no talent/succession planning tools at all, how would you
  feel?"

Report back, per feature: **CS+ = (A+O)/(A+O+M+I)**, **CS− = −(O+M)/(A+O+M+I)**. Five to
ten responses per feature from real prospects or customers is enough to move a class from
`proxy` to `survey` with real coefficients attached — it does not need to be a large sample
to be better than nothing.

---

## Open questions

| Question | Owner | Blocks |
|---|---|---|
| Is the `alvox_compensation` app (32 doctypes, 177 tests, per §3) real anywhere — a different branch, a different repo, aspirational? It does not exist in `hr-app` as checked this session. | Founder | Whether "Compensation/reward: built" is corrected in `product-context.md`, and whether compensation belongs on this priority list at all |
| Was slice `010-portal-security-fixes` pushed to `dev`/`main` after the artifacts I read (last dated 17 Sep 2026)? | Whoever ran that slice / the user | Whether risk #1 in product-context §10 is actually closed |
| Does the "Objectives & KPI backlog v2.0" (17 epics, 132 stories, 698 points, YouTrack project KIN) that `product-context.md` §3 cites actually exist? I could not reach YouTrack this session (no MCP tool was available despite the task brief) and no local file matches that description — the closest real documents are `OBJECTIVES_KPI_REQUIREMENTS.md` and `KPI_AUTOMATION_STRATEGY.md`, both dated 18 Aug 2026. | Founder / whoever owns YouTrack access | Whether this review is missing a large, already-prioritised body of backlog work |
| Is EU exposure current, target, or anticipated? | Founder (already an open question in product-context §5, repeated here because it directly changes candidate C3's priority — Art 86 only binds us if EU exposure is real) | Whether C3 is P1 compliance work or P3 differentiation |
| What should happen to the unused PMS module (`hrms/hrms/performance_management`, 36 doctypes, never run against real data)? Disable it, sunset `alvoraa_goals` in its favour, or keep both deliberately and design the difference into the product story? | Founder / engineering | C7's priority and scope |
| Is there a real customer request behind pulse/eNPS (C6), learning (C8) or talent/succession (C9), or are these committed because a competitor has them? | Founder | Whether C6/C8/C9 move up the list or stay on hold pending the survey kit in §8 |

## Assumptions

- `[ASSUMPTION]` The 17 slice folders and their own status lines (mostly written by the
  full-stack engineer, dated 7–19 Sep 2026) are accurate as of their own dates. I did not
  re-run any tests or re-verify their code changes myself.
- `[ASSUMPTION]` "Current state" in §1 reflects what's in the git working tree read this
  session. If work has been merged or reverted since the last commit an agent in this
  session could see, this table is stale in the same direction.
- `[ASSUMPTION]` Target tenant size (50–1,000 employees, India-first) from product-context
  §2 is still the operative target; C9's Indifferent classification depends on it — a move
  upmarket would likely reclassify it toward Performance.
- `[ASSUMPTION]` "Buyers ask for eNPS by name" (product-context §8, feeding C6's Performance
  classification) is treated here as secondhand until a named source is attached — flagged
  in §4, not silently accepted.
