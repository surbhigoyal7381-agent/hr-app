# Alvoraa — Objectives & KPI Management
## Consolidated Software Requirements Specification

**Version:** 2.0 — single source of truth
**Date:** 2026-08-23
**Status:** Draft for review
**Scope:** `alvoraa_goals`, the objectives/KPI surface of `alvoraa_portal`, and the appraisal seam into the `hrms` fork

---

## 0. About this document

### 0.1 What it replaces

This document absorbs, reconciles and supersedes five documents. Once approved, **all five can be deleted.**

| File | Size | What was taken from it | Status |
|---|---|---|---|
| `OBJECTIVES_KPI_REQUIREMENTS.md` | 28 KB | Authoring requirements FR-1..24, gap analysis, enterprise competitive analysis | **Superseded** — gap analysis corrected in §4.2 |
| `KPI_AUTOMATION_STRATEGY.md` | 29 KB | Measurement engine: principles, four calculation shapes, credit model, position layer, adapters, sync orchestration, failure modes | **Superseded** — absorbed into §7.3, §9.F, §9.P, §9.Q |
| `KPI_BACKLOG_DECISION_RECORD.md` | 5 KB | Decisions D1–D10, backlog structure constraints | **Superseded** — consolidated in §12, **one contradiction corrected** |
| `backlog/KPI_AUTOMATION_BACKLOG.md` | 34 KB | 40 stories, 223 points, 7 epics | **Superseded** — every story mapped in §13 |
| `OBJECTIVES_AND_KPI_SRS.md` v1.1 | 111 KB | Code audit, market analysis, compliance, entitlement | **This file, rewritten** |

**Also affected, not deleted.** `backlog/kpi_automation_stories.json` and `backlog/kpi_automation_youtrack.csv` are *import artefacts*, not documents. They produced YouTrack issues **KIN-10 to KIN-56**, which still exist. §13 maps every one to its requirement here. Keep or delete the files as you prefer — but **do not re-import them**, because §4.1 shows they encode a superseded decision.

**Explicitly NOT superseded — keep these:**
`MODULE_ACCESS_STRATEGY.md` · `ARCHITECTURE.md` · `KNOWN_ISSUES.md` · `CLAUDE.md` · `Design_Theme_Guide.md`

### 0.2 What this document is for

Three jobs, in order of importance:

1. **Stop the features breaking each other.** Five documents written at different times against different assumptions. Several of their requirements collide. **§8 is the map of every collision found and how to sequence around it.** It is the most important section here and the reason this consolidation was worth doing.
2. **Be the only place a requirement lives.** Every requirement carries one ID. §13 maps every legacy ID onto it.
3. **Be honest about what is known.** §0.3.

### 0.3 Method and confidence

| Input | Method | Confidence |
|---|---|---|
| Current implementation (§3, §4) | Direct reading of source on the connected device, 22–23 Aug 2026 | **High for what the code says. Nothing was executed.** No test was run, no database inspected. Behavioural claims are readings of static source. Items needing a test to confirm are marked ⚠ |
| Contradictions between source documents (§4) | Textual comparison of the four documents against each other and against the code | **High** — each is quoted verbatim |
| Feature interactions (§8) | Reasoning over the merged requirement set and the code | **Analytical, not observed.** Each is stated as a mechanism so it can be checked or refuted |
| Market analysis (§5) | Four parallel research passes against vendor documentation, analyst releases and peer-reviewed literature, 22 Aug 2026 | **Mixed, sourced individually.** Vendor marketing tagged. Analyst projections distinguished from measurements. Unverifiable figures listed in §14.3 |
| Compliance (§6) | Primary legal texts plus law-firm commentary | **High on statute, flagged where commentary** |
| Requirements (§7–§11) | Synthesis | Proposals, not decisions |

**Two checks remain outstanding**, flagged inline: whether `Goal Check-In` is referenced by any live code path (§9.H), and the internals of `get_calibration_matrix` (§9.I).

---

## 1. Executive summary

**Alvoraa has a working objectives-and-KPI implementation, a well-designed measurement engine on paper, and five documents that disagree with each other about what to build next.**

The code is in better shape than the requirements documents claim: a cascade model, a KPI controller with real validation, direction-aware attainment, an org-tree permission layer, an appraisal projection that enforces weightage integrity, and calibration endpoints. That is more than most India mid-market competitors publicly document.

Six findings drive this specification.

**1. Nine defects produce wrong numbers or wrong behaviour today.** Three are severe: a zero-is-best KPI scores zero (DEF-2), the weightage budget counts KPIs while scoring counts KPIs *and* objectives (DEF-1), and cascade aggregation double-counts a multi-level tree (DEF-3). Three arrived with the 23 August subscription work (DEF-7 to DEF-9), including a Starter tenant receiving daily emails about a feature it never bought.

**2. The source documents contradict each other on decision D3, and the 40-story backlog encodes the losing side.** `KPI_AUTOMATION_STRATEGY.md` resolves D3 as "**both** `KPI` and `Individual Goal` are Phase 0 targets". The decision record and the backlog both say "**KPI first**, Individual Goal in Phase 4". **No story among the 40 mentions `Individual Goal`**, yet the strategy's Phase 0 exit criteria require it. The backlog as written cannot satisfy the strategy as approved. See §4.1.

**3. Eight feature pairs will break each other if built in the wrong order.** The sharpest: adding a `Pending Approval` status without patching `_set_status` causes KPIs to **silently approve themselves** the moment their period ends. §8 catalogues all eight with the guard for each.

**4. Goal governance is unbuilt across the entire India mid-market.** Across ten scanned vendors, not one publicly documents locking a goal after approval, versioning it, or a mid-cycle revision workflow. Every Indian company that ties a goal sheet to an increment has this problem and nobody sells the answer. Highest-conviction whitespace found.

**5. The goal-to-rating formula is a black box everywhere — and regulation is about to require the opposite.** No competitor publishes the arithmetic. EU AI Act Article 86 gives an affected person the right to a meaningful explanation of an AI system's role in a decision about them. A replayable derivation is simultaneously the differentiator and the compliance obligation.

**6. This is a module, not a product.** Talent management traded at **0.5× revenue** in 2026 forecasts against 5.2× for diversified HCM. Microsoft retired Viva Goals in December 2025. No performance-management funding rounds in Q1 2026. The 23 August subscription work already places Goals & KPIs on the Enterprise plan — the right call, with pricing consequences in §2.3.

**The shape of the work:** fix the scoring defects and the entitlement holes first; add the authoring governance nobody else has; make the scoring chain explainable end to end; then ship the ERP credit engine as the thing competitors cannot answer. OKR becomes a vocabulary over the same objects, never a second data model.

---

## 2. Scope and product position

### 2.1 In scope

The complete lifecycle of an objective or KPI, from authoring to defending a rating in a grievance:

```
AUTHOR ──► GOVERN ──► MEASURE ──► SCORE ──► MODERATE ──► EXPLAIN
library    plan,       facts,      bands,    calibration  derivation
templates  approval,   credits,    weights,  9-box,       record,
scoping    lock,       adapters,   override  distribution employee view
           revision    reversal
```

### 2.2 Out of scope

| Not building | Why |
|---|---|
| Commission or incentive payout calculation | This produces attainment, not payouts. An SPM engine is a different product |
| Real-time measurement | Hourly and nightly sync is sufficient for appraisal-grade metrics |
| Universal automation | Judgement-based KPIs stay manual **by design** — roughly 15% of a scorecard should never be automated |
| Writes back to any source system | One-way keeps the blast radius contained |
| An iPaaS dependency (Zapier, Workato) | Introduces a third-party processor holding HR and commercial data |
| Inbound webhooks in v1 | Requires firewall changes, replay handling and signature verification, for freshness appraisal KPIs do not need |
| Multi-approver goal approval chains | §5.5 — mid-market configures "manager approves" and never touches it again |
| Forced rating distribution as a default | §5.6 — the evidence is unfavourable. Available as configuration, off by default |
| Emotion recognition from biometric data | §6.1 — prohibited by law, penalties to €35m / 7% of turnover |

### 2.3 Commercial position — settled 2026-08-23

`subscription.py` places both `goals` and `performance` on the **Enterprise** plan.

| Plan | Features |
|---|---|
| Starter | portal, leaves, attendance, expenses, hr_setup |
| Business | + tenure, recruitment, payroll, tax_benefits |
| **Enterprise** | + **performance**, **goals**, analytics, vendor |
| Custom | Enterprise + individually chosen ERPNext modules |

This matches the market evidence in §5.1.

**One commercial question stays open.** Enterprise bundles performance + goals + analytics + vendor as one rung, mapping to the **₹100–150 PEPM suite tier** (§5.2). The greytHR anchor of **₹35–45 PEPM for a performance add-on** is what a buyer wanting *only* goals will quote at you. The registry already supports "Business + Goals" as a Custom combination, because the plan name is derived from what is ticked. Decide deliberately rather than by omission — **D-16**.

---

## 3. Current implementation — as built

### 3.1 Object model

```
Goal Cascade  (company target, unit, period, aggregate_progress_pct)
   │
   ├── Individual Goal  ── submittable, self-referencing via parent_goal
   │      ├── Goal Evidence        (child) → validation_status, value
   │      └── Goal Progress Update (child) → approval_status, value   ⚠ orphan, DEF-4
   │
   └── KPI  ── not submittable
          ├── KPI Progress Log        (child) → approval_status, value
          └── KPI Additional Reviewer (child) → dotted-line ratings

KPI.individual_goal ──► Individual Goal   (a KPI hangs off an objective)
KPI.goal_cascade    ──► derived from the linked objective, never set directly

Appraisal (HRMS)  ◄── projected from KPIs + weighted Goals
   └── Alvoraa Appraisal Extension → review_status, narratives, action_items,
                                     potential_rating, calibration_notes, page_data
```

Supporting: `Company Value`, `Leadership Principle`, `Upward Feedback`, `Alvoraa Rating Scale` (+ items), `Alvoraa Cycle Config`, `Cascade Alignment Report`, `Goal Progress Audit Log`, `Evidence Validator`, `Evidence Duplicate Check`, `Goal Check-In` ⚠.

**API surface:** `performance_api.py` 4,029 lines / 88 whitelisted endpoints · `hr_api.py` 2,127 / 47 · `goals_api.py` 1,187 / 22.

**Field asymmetry that matters later (§8, C-2):**

| | `KPI` | `Individual Goal` |
|---|---|---|
| `direction` (Higher/Lower is Better) | ✅ | ❌ **absent** |
| `attainment_pct` | ✅ | ❌ absent (`progress_pct` instead) |
| `progress_mode` | ✅ | ✅ |
| `trajectory` | ❌ | ✅ |
| submittable | ❌ | ✅ |

### 3.2 What works, and must not be rebuilt

- **Direction-aware attainment.** `Lower is Better` inverts to `target / actual`, so beating a collections-days or defect-rate target scores above 100.
- **Balanced Scorecard perspectives are a field, not a tag.** `KPI.category` is a fixed enum.
- **Cascade linkage is validated against the org tree.** `_validate_linked_objective` walks `descendants()`, rejects a KPI linked to a sibling branch's objective naming both parties, then **derives** `goal_cascade` from the objective so the two cannot disagree.
- **Row-level scoping is real.** Query conditions and document permissions narrow to self-plus-subtree; write and delete additionally restricted to the creator. Cross-tenant isolation is free from site-per-database.
- **Appraisal projection is idempotent.** `sync_appraisal_from_kpis` rewrites goal rows from current state and re-runs safely.
- **Matrix review exists natively.** `KPI Additional Reviewer` supports dotted-line reviewers with independent ratings.
- **Cascade alignment variance is half-built.** `Cascade Alignment Report` computes company target vs sum of child targets with a variance percentage and a verdict — the "quota coverage" concept sold as premium elsewhere.
- **Weightage integrity is enforced at two points.** Above-100% blocked at save; not-exactly-100% blocked at appraisal generation.

### 3.3 Defects

Readings of source. None confirmed by execution. Each needs a test before and after any fix.

| ID | Defect | Severity | Interacts with |
|---|---|---|---|
| DEF-1 | Weightage budget counts KPIs; scoring counts KPIs **and** objectives | High | §9.C weight rules |
| DEF-2 | `Lower is Better` scores a perfect result as zero | High | **C-2** |
| DEF-3 | Cascade aggregation double-counts a multi-level tree | Medium | **C-11** |
| DEF-4 | `Goal Progress Update` does not move progress | Medium | **C-3** |
| DEF-5 | Hourly recalculation saves and commits per goal | Medium | **C-6** |
| DEF-6 | Draft KPIs consume weightage budget | Low | — |
| DEF-7 | Calibration sign-off stored in an unstructured JSON blob | Medium | §9.I |
| DEF-8 | Entitlement is cosmetic — Goals & KPIs answers on every plan | High | §9.O |
| DEF-9 | Provisioning script contradicts the plan model | High | **C-9** |

---

**DEF-1 · Weightage budget ignores objectives**

`_validate_weightage_budget` (`controllers/kpi.py`) queries only `KPI`:

```python
others = frappe.get_all("KPI", filters={
    "employee": doc.employee, "appraisal_cycle": doc.appraisal_cycle,
    "status": ["!=", "Cancelled"], "name": ["!=", doc.name or ""],
}, pluck="weightage")
```

`_scored_items` (`performance_api.py`) sums both `KPI` and `Individual Goal`.

**Failure:** three KPIs at 40/30/30 (=100, every save passes) plus one weighted objective at 20. Appraisal generation throws "weightages total 120%, not 100%". Nothing in authoring showed a problem; the manager discovers it when trying to close the cycle.

---

**DEF-2 · "Lower is Better" scores a perfect result as zero**

```python
if doc.direction == "Lower is Better":
    doc.attainment_pct = 0 if actual == 0 else flt(target / actual * 100, 2)
```

The inline comment explains the intent — *"No actual logged yet is not the same as a perfect score."* Correct reasoning, wrong signal. It conflates **"no value recorded"** with **"the recorded value is zero"**.

**Failure:** a KPI of "safety incidents ≤ 5" where the employee achieves **0 incidents** — the best possible outcome — scores **0% attainment**, maps to a **0 rating**, and is stamped `Missed` at period end. Every zero-is-best KPI is affected: incidents, defects, escalations, complaints, attrition, rejections, stockouts.

**Fix — distinguish unset from zero.** `actual_value` is a `Float` defaulting to 0, so the field alone cannot carry the distinction. In order of preference: (1) treat "has at least one approved progress log row" as the has-been-measured signal, leaving attainment null and excluded from scoring until then; (2) an explicit `is_measured` check field; (3) cap and floor with a declared maximum. Do **not** simply special-case zero — that flips the bug to scoring an unmeasured KPI as perfect.

---

**DEF-3 · Cascade aggregation double-counts a multi-level tree**

```python
goals = frappe.get_all("Individual Goal",
    filters={"goal_cascade": cascade_name, "docstatus": ["!=", 2]},
    fields=["actual_progress", "target_value"])
```

`Individual Goal` has a `parent_goal` self-link, so one cascade legitimately contains a division objective *and* the individual objectives rolling into it. This query flattens the tree and sums every level.

**Failure:** a cascade with a ₹10 cr division objective and five ₹2 cr children reports a ₹20 cr total target. `aggregate_progress_pct` is halved. `Cascade Alignment Report` reads the same shape, so the variance verdict is wrong too.

This is the same hazard the measurement strategy warns about for KPI actuals. The rule must apply to objectives as well.

---

**DEF-4 · Progress updates do not move progress**

`recalculate_progress` sums **approved `Goal Evidence` rows only**. The `Goal Progress Update` child table carries `value`, `approval_status`, `approved_by`, `approved_on` — a complete approval apparatus — and is never read. Decision required before fixing: **D-13**, and see **C-3**.

---

**DEF-5 · Hourly recalculation commits per goal**

`recalculate_all_progress` loops every active submitted goal and performs a full `get_doc`, `.save()` and explicit `frappe.db.commit()` **per goal**, plus an audit insert and a cascade aggregation. At 200 employees × 6 goals that is 1,200 loads, saves and commits every hour and 28,800 audit rows a day recording mostly nothing. It contradicts the measurement strategy's own recompute discipline — *"recompute each affected KPI exactly once, bottom-up"*.

---

**DEF-6 · Draft KPIs consume weightage budget**

The budget query excludes only `Cancelled`, so a `Draft` KPI counts against the ceiling and drafting two alternatives is blocked.

---

**DEF-7 · Calibration sign-off is stored in an unstructured JSON blob**

Added 2026-08-23:

```python
settings["calibration_signoff"] = {
    "summary": summary, "signed_by": frappe.session.user,
    "signed_at": frappe.utils.now(),
}
```

written into `Alvoraa Cycle Config.page_settings`. The function is correctly HR-gated, validates inputs, preserves neighbouring keys and carries eight tests — careful work as an implementation. As a **data model** it is the wrong shape: a calibration sign-off is the record that a committee accepted a set of ratings, and in a grievance it is evidence. Stored as JSON inside a UI-configuration field it is not queryable, single-valued (a second sign-off silently overwrites the first), unaudited, and un-migratable.

---

**DEF-8 · Entitlement is cosmetic**

`module_access.py` says so itself:

> *"This HIDES modules from the desk. It does not DENY anything… Roles are the boundary — that is wave 4. Shipping this alone would make the product look correctly gated while it is not."*

Verified: `has_feature()` is called **nowhere** outside `subscription.py` and its tests. A Business-plan tenant can call all 157 whitelisted endpoints across the three API modules directly. The portal hides the UI; the API does not.

Acknowledged and scheduled as Wave 4 of `MODULE_ACCESS_STRATEGY.md` — honest sequencing. It is here because the day a feature carries a price, an ungated API stops being a roadmap item.

---

**DEF-9 · The provisioning script contradicts the plan model**

`deploy/provision_tenant.sh` was not updated when `subscription.py` landed.

| # | Script does | Plan model says |
|---|---|---|
| 1 | `install-app alvoraa_goals` **unconditionally, every plan** | Goals is Enterprise-only. Conditional install is Wave 5, unbuilt |
| 2 | `business → [...,"goals"]` | `_BUSINESS` excludes goals; goals is in `_ENTERPRISE` |
| 3 | Writes `modules_enabled` | `enabled_features()` reads `features`. `modules_enabled` is dead config in a different vocabulary |

`tenant_api.py` **was** updated. The two provisioning paths now disagree.

**The consequence that reaches a customer:** because `alvoraa_goals` installs everywhere, its scheduler hooks are live everywhere. On a **Starter** tenant, `recalculate_all_progress` runs hourly, `check_cascade_alignment` daily, and **`send_progress_reminders` emails real employees daily** about goals belonging to a feature their company did not buy. Not covered by module blocking, roles, or Wave 4.

### 3.4 The entitlement layer as built

Three gating mechanisms, only two of which deny:

| Mechanism | Effect | Denies? |
|---|---|---|
| `module_defs` → Module Profile → `User.block_modules` | hides from the desk UI | ❌ |
| `roles` withheld | server-side doctype access | ✅ — not yet applied per plan |
| app not installed | doctypes do not exist | ✅ — not yet conditional |

**Design decisions worth preserving:** `enabled_features()` **fails open** so a missing key never locks out a paying customer; an explicitly empty list is distinguished from an unset one (`is not None`, not truthiness); **downgrade hides, never uninstalls**, because `bench uninstall-app` drops tables; two Module Profiles so HR staff keep the desk shell; `sync_site` refuses to run on the control plane; and `apply_on_user_insert` / `apply_on_user_update` stop the gate decaying as users and roles change. Both hang off User: role edits never load a Has Role document, so a hook there would never fire.

**And one decision this document dissents from — see D-1.** `MODULE_ACCESS_STRATEGY.md` §7 and `subscription.py` both record that PMS and Frappe HR Performance now ship as **one sellable feature**. Clean pricing; the delivery consequence is that **37 doctypes that have never executed against any database** are switched on for every Enterprise tenant, beside a live independent performance system.

---

## 4. Corrections to the source documents

Each correction is recorded because the losing version is currently encoded somewhere — in a backlog, in YouTrack, or in someone's plan.

### 4.1 🔴 D3 is resolved two different ways, and the backlog follows the wrong one

| Document | States |
|---|---|
| `KPI_AUTOMATION_STRATEGY.md` §16 | D3 → **"Both"**. §16.1: *"`Individual Goal` is no longer deferred to Phase 4. It is a Phase 0 target alongside `KPI`"* |
| `KPI_BACKLOG_DECISION_RECORD.md` §1 | D3 → **"`KPI` first; Individual Goal in Phase 4"** |
| `backlog/KPI_AUTOMATION_BACKLOG.md` header | **"D3 — KPI.progress_log is the target path first; Individual Goal follows in Phase 4"** |

The strategy explicitly flags its own answer as *"Differs from the recommendation"* — it is the later, deliberate resolution; the other two carry the superseded one.

**Consequence:** the strategy's Phase 0 exit criteria require the three proof metrics to land *"on **both** a `KPI` and an `Individual Goal`"*. **No story among KPIA-1..40 mentions `Individual Goal`.** The backlog cannot satisfy the strategy as approved, and KIN-10..56 inherit the gap.

**Resolution here: D3 = Both.** §9.F names both target paths, and §8 C-2 / C-3 set out the two structural prerequisites nobody has scheduled.

### 4.2 Two "Critical" gaps in the requirements document do not exist

`OBJECTIVES_KPI_REQUIREMENTS.md` was written **without repository access** — its own decision record lists that as outstanding blocker #1.

| Claim | Reality |
|---|---|
| G4 — *"`kpi.py` is `pass`. There is no validation of any kind."* | The doctype class is `pass` by Frappe convention. Validation lives in `controllers/kpi.py`, wired via `hooks.py` → `doc_events["KPI"]["validate"]`, running six checks. `Individual Goal` follows the identical pattern |
| G3 — *"An employee can carry KPIs totalling 60% or 340% and the appraisal will still score."* | 340% is blocked at save; 60% is blocked at appraisal generation with the number in the message. **The real defect is narrower** — DEF-1 |

**Consequence:** story **KPIA-46**, flagged as *"pull ahead of all other work — live scoring defect"*, is largely already built. Re-scope to DEF-1, a much smaller change.

Gaps G1, G2, G5, G6, G7, G8, G9 are **confirmed** and carried forward.

### 4.3 The strategy misstates current traversal capability

`KPI_AUTOMATION_STRATEGY.md` §6.3: *"`alvoraa_goals` currently only ever reads direct `reports_to` — multi-level traversal is new capability, not a config change."*

`permissions.py` contains `descendants()`, which walks the tree breadth-first to a depth cap of 12 and is used by `manageable_employees()`, both `permission_query_conditions` hooks, and `_validate_linked_objective`.

Multi-level traversal exists today. What is genuinely new is doing it as an indexed `lft`/`rgt` range scan rather than an iterative query loop — a **performance** change, not a capability one. The estimate for the roll-up story should reflect that.

### 4.4 KPIA-4 and FR-6 are not the same library

The decision record instructs: *"KPIA-4 — **Merge into KPIA-41.** Starter library must not be built twice."* They are different objects:

| | Contains | Answers |
|---|---|---|
| **Goal Template** library (§9.B) | name, description, perspective, unit, direction, default weight, scoping | *What should this person be measured on?* |
| **KPI Metric Definition** library (§9.F) | calculation type, source doctype, value field, filters, attribution strategy | *How is that number computed?* |

Merging them naively produces one object doing two jobs. **The correct relationship is a nullable foreign key:** a Goal Template optionally binds to a Metric Definition. The decision record's underlying concern — one starter dataset, not two — is satisfied by seeding both in one operation. See **C-13**.

### 4.5 Minor corrections

- The 40-story backlog totals **223 points across 7 epics**; the requirements document proposed a further **16 stories / 89 points across 5 epics**. Combined, the legacy plan is **56 stories / 312 points** — before any of the nine defects, entitlement, OKR mode, check-ins, AI or calibration. That total was never stated in one place and it matters for planning.
- `KPI_BACKLOG_DECISION_RECORD.md` §6 records blockers now cleared: repo access (resolved), and the YouTrack `Story points` field (present in the KIN schema, confirmed 2026-08-23).
- The KIN project's `State` enum is **To do / In Progress / Done** only. There is no "Won't fix" or "Obsolete" state, and the available tooling exposes no delete operation — so stories superseded by this document cannot be closed as obsolete without an admin adding a state. Noted for backlog hygiene.

---

## 5. Market analysis

Research conducted 2026-08-22. Re-run before external use after roughly 2026-11.

### 5.1 Category economics — the strategic frame

| Segment | EV/Revenue (2026E) | EV/EBITDA |
|---|---|---|
| Diversified HCM | 5.2× | 13.4× |
| Core HR | 3.5× | 10.1× |
| Talent Acquisition | 2.0× | 7.0× |
| **Talent Management** | **0.5×** | **5.2×** |

*Houlihan Lokey, "2025 HCM Technology Year in Review", March 2026.*

Corroborating: **Microsoft retired Viva Goals on 31 December 2025**; **WorkBoard acquired Quantive** (May 2025); **Q1 2026 HR-tech funding contained no performance-management or OKR round**, and only three Series A rounds across all of HR tech — the lowest since 2018 ⚠ *(analyst newsletter, not an audited database)*; **Q1 2026 M&A: 19 transactions, none in the category**. The one 2026 deal: **Lattice acquired Pando**, 19 August 2026, terms undisclosed.

**Read:** standalone objectives-and-KPI software is consolidating. Build the capability as the differentiating module inside the HRMS, which §2.3 now does.

### 5.2 The India mid-market feature floor

Present in seven or more of ten scanned vendors (Darwinbox, Keka, Zoho People, HROne, PeopleStrong, greytHR, Peoplebox, Worxmate, Kredily, sumHR).

| # | Capability | Alvoraa today | Requirement |
|---|---|---|---|
| 1 | **Dual vocabulary — KRA/KPI *and* OKR in one product** | ⚠ KPI/objective only | §9.M |
| 2 | Weightages summing to 100% at every level | ✅ (with DEF-1) | FR-A1 |
| 3 | Cascading with a visual alignment tree | ✅ | — |
| 4 | Goal templates / library with bulk assignment | ❌ **Absent** | §9.B, §9.K |
| 5 | Multiple cycle types incl. **probation**, per-BU | ⚠ Partial | FR-C5 |
| 6 | 360 with **nomination and manager approval** | ⚠ Reviewers exist, no nomination | FR-H8 |
| 7 | Continuous feedback and structured 1:1s | ⚠ Action items only | §9.H |
| 8 | Goal attainment auto-populating the rating, **with override** | ✅ | FR-G7 |
| 9 | Configurable rating scales | ✅ per cycle | — |
| 10 | **Normalisation / bell curve** — not optional in India | ❌ Absent | FR-I4 |
| 11 | 9-box on performance × potential | ⚠ Ratings captured, matrix unverified | FR-I5 |
| 12 | Cycle locking after launch | ❌ Absent | FR-E7 |

**Whitespace — consistently absent across the whole set:**

- **Goal governance.** Not one vendor documents locking a goal after approval, versioning it, or a mid-cycle revision workflow. Highest-conviction gap found.
- **Genuine background automation.** Keka — the deepest documented India module — requires a **manual click per goal** to sync Jira or Google Sheets. Peoplebox is the only India-adjacent vendor with real auto-sync.
- **A transparent goal-to-rating formula.** Everyone says "custom formulas"; nobody publishes the arithmetic.
- **Calibration as a facilitated process** rather than a grid — no pre-read packs, no manager leniency surfaced before the meeting.
- **India-specific fit** — variable pay against CTC structures, PIP documentation built for Indian labour-law scrutiny, vernacular review forms.
- **Frontline populations.** Every product assumes a desk-based employee with a laptop and a quarterly 1:1.
- **The systems Indian KPIs actually live in** — Tally, Zoho Books, Zoho/Salesforce CRM, LeadSquared, service-desk volumes. No vendor in the scan integrates with any of them.

**Price anchors.** Only two vendors publish an INR figure attributable to performance: **greytHR PMS add-on at ₹35–45 PEPM** (the only discrete published price found) and **sumHR Advanced at ₹119 PEPM** (full suite including 360). Peoplebox charges **USD 8/employee/month for Performance and another USD 8 for 360** — roughly ₹700–1,400 PEPM combined.

> **Working bands: ₹35–75 PEPM** for performance as a module on an existing HRMS; **₹100–150 PEPM** for the suite tier that contains it.

### 5.3 The OKR-specialist bar

**Table stakes:** Objective→KR hierarchy with parent-child alignment; at minimum four measurement types (numeric, percentage, currency, binary) plus milestone; goal cycles distinct from goals; a discrete status set at objective level; **status derived automatically from progress vs *expected* progress given time elapsed**; Slack *and* Teams with in-channel updating; overdue nudges; spreadsheet ingest; Jira auto-update; SSO/SAML + SCIM; public API; AI goal drafting.

**Where a new entrant can win:**

| # | Gap | Who has it | Requirement |
|---|---|---|---|
| 1 | **Configurable scoring bands / lookup tables** | Only Profit.co publicly | FR-G1 |
| 2 | Explicit per-KR weighting | Leapsome, Profit.co. Perdoo deliberately rejects it | FR-M4 |
| 3 | **Confidence separate from calculated status** | Only WorkBoard | FR-H2 |
| 4 | **Direct SQL / warehouse connectivity** | Only Profit.co | FR-F12 |
| 5 | Guardrail KR types — stay above / below / between | Perdoo; Profit.co's *Control KPI* | FR-M3 |
| 6 | KPIs modelled distinctly from OKRs | Perdoo, Profit.co | D-A |
| 7 | **AI quality *critique* of an existing goal** | **Nobody** | FR-J2 |
| 8 | Transparent per-seat pricing | Perdoo, Mooncamp, Weekdone | D-16 |

### 5.4 The enterprise authoring model worth copying

**Object A — Goal Library.** A versionable tree:

```
GoalLibrary        (id, guid, name, locale)
 └─ Category       (id, name, sequence, parent_category_id)
     └─ GoalLibraryEntry (name, metric, [start], [due], [weight], ...)
```

Identity is a **GUID**, referenced by the plan, so a library can be renamed and re-imported without breaking bindings. **One library per plan, many per tenant** — the library *is* the scoping mechanism. Transport is a **typed CSV**, one row per node discriminated by a `type` column, round-trippable; the file is the artefact, diffable in git. SAP publishes hard sizing guidance (10–15 categories, ≤4 sub-categories, 10–15 goals per sub-category, **≤1,000 entries per library**) because library rendering sits on the goal-creation hot path.

**Steal from Oracle instead of proliferating libraries:** scoping attributes **on the entry itself** — Business Unit, Department, Legal Employer, **Job Family** — plus an **External ID** and a **Status defaulting to Inactive** so nothing publishes by accident.

**Object B — Goal Plan Template.** Owns the cycle window, cardinality and weight constraints, the field schema and its permissions, and **state-conditioned permissions**.

The key abstraction, and it is cheap: **permission = f(role, field, plan_state)**. SAP's framing is that this lets you *"restrict editing after approval without requiring formal workflows"*. A three-dimensional lookup replaces a workflow engine for most governance requirements.

Take Workday's conflict rules verbatim: a field **hides only if every** applicable group is in Hidden For; it is **required if any** group is in Required For; **Required beats Hidden**.

**Object C — Metric Lookup Table.** The declarative answer to "how did 92% become 3.5?". The modelling insight is that it is **a field on the goal**, not on the form — so different goals in one plan can use different tables. Two modes: **interpolate** (92% between a 90%→3.0 row and a 100%→4.0 row yields 3.2 — SAP's recommended mode) and **step** (snaps to 3.0). Boundary behaviour separately declared. Rows bulk-importable.

⚠ **Caveat:** per SAP KBA 2457856, goal-plan XML min/max produce **soft warnings only**; hard enforcement lives in the performance form template. Decide deliberately per constraint whether it is advisory at authoring or blocking at submit — SAP's split is a known source of customer confusion, not a feature to imitate.

**Object D — Oracle's weighted-average engine.**

```
decimal_score(item)  = item_rating / max(item_rating_model)
weighted_score(item) = decimal_score × weight
section_rating       = (Σ weighted_score / Σ max_weighted_score) × max(section_rating_model)
overall_rating       = (Σ section_decimal × section_weight / 100) × max(model)
```

with **precise values carried throughout and rounding applied only at the end**, un-weighted items ignored, and mixed rating models normalised each against its own maximum.

### 5.5 What to deliberately not build

1. **XML-as-configuration** — cut the mechanism, keep the schema. Render as UI, version as JSON.
2. **Category-level weight and count quotas** — cut. Every specialist studied ships without goal-count rules and none lose deals over it.
3. **Forced rating distribution** — cut as a default; see §5.6. Per-company configuration, advisory default.
4. **Multi-approver chains with transaction caching** — cut the chain, keep the lock.
5. **Relationship-role permission algebra** — collapse to four principals: owner, manager, HR admin, other. Keep the **state** dimension.
6. **Development goals as a separate module** — a goal *type* enum suffices; `Individual Goal.goal_type` already does this.
7. **Goal-setting window vs execution window — DO NOT cut.** Oracle shipped this only in 25D and it is the highest-leverage governance feature in the study.

### 5.6 What the evidence says — and what it forbids

**Goal setting works, with boundary conditions.** Locke & Latham (2002), 100+ tasks, 40,000+ participants: specific difficult goals beat "do your best" at **d = 0.42–0.80**. The effect **attenuates with complexity — d = 0.48 complex vs 0.67 simple** — and on complex or novel work, *learning* goals outperform *performance* goals. Goals plus feedback beats goals alone.

**Goals have documented side effects.** Ordóñez et al. (2009), "Goals Gone Wild": narrowed focus, increased unethical behaviour, distorted risk preferences, eroded culture, reduced intrinsic motivation. ⚠ **Publicly contested by Locke & Latham in the same journal**, with a reply. A live disagreement, not a settled finding.

**The finding that should change the product.** Salgado & Moscoso (2019, K=219, N=43,203): rating reliability is **.45 for administrative purposes** (pay, promotion) versus **.61–.69 for developmental purposes**. Attaching consequences **degrades measurement quality**. Zhou et al. (2024, k=132) find a higher overall figure (r = .65) and warn against a single grand-mean reliability.

> **Product implication:** the more the system automates evidence into an administratively-consequential rating, the more it must show its working and preserve dissent. The strongest argument for §9.G and for keeping manager override authoritative by configuration.

**More feedback is not better feedback.** Kluger & DeNisi (1996): positive on average, but **over a third of interventions decreased performance**. ⚠ The quoted "38%" could not be confirmed against the primary text. Feedback directing attention to the **self** rather than the **task** degrades performance.

**Electronic performance monitoring does not work.** Siegel, König & Lazar (2022), 70 samples / 233 effect sizes: performance **r = −0.01**, satisfaction **−0.10**, stress **+0.11**, counterproductive behaviour **+0.09**.

**Forced distribution is unfavourable.** Scullen et al. (2005) shows gains in early years only ⚠ *(full text inaccessible; do not quote magnitudes)*. McEntire (2025) reports a **32–53% error rate** in forced-ranking decisions ⚠ *(unrefereed preprint, simulation not field data)*.

**The counter-evidence on removing ratings.** CEB (2016): performance dropped ~10%, manager feedback quality 14%. ⚠ **Vendor press release, no methodology disclosed, underlying study not public.** The strongest counterweight to the "kill ratings" consensus, and not verifiable.

**OKRs have no evidence base.** Silva & Santos (2024), 47 studies: *"OKR use is under-documented from a theoretical point of view."* **No meta-analytic or experimental evidence that OKRs as a framework improve organisational performance.** The components that do have evidence come from goal-setting theory.

**The most actionable single finding.** Gallup (2017): only **3 in 10 employees strongly agree their manager involves them in goal setting — and those employees are 4× more likely to be engaged.** Participation in *setting* goals, not sophistication in *tracking* them. ⚠ Pre-2020.

McKinsey (2018, n=1,761): **linking goals to business priorities** (46% vs 16%), **manager coaching** (74% vs 15%), **differentiated compensation** (54% vs 16%). All three: **84%, 12× the rate of organisations doing none.** Perceived fairness is the strongest single driver.

### 5.7 Buyer complaints and the AI reality check

Recurring review themes by frequency: **rigid templates and weak customisation** (most consistent), **reporting inflexibility**, **navigation friction**, **integration fragility**, **setup complexity**, **AI features rated immature**, **missing operational basics**. ⚠ Secondary synthesis from sites with affiliate relationships; treat themes as reliable, ratings as soft.

Only **31% of organisations use any AI-enabled HR technology**; embedded-AI HR applications sit at **9% adoption** (Sapient Insights, n = 9,886 across 4,670 organisations). **88% of HR leaders report no significant business value from AI tools**; **only 8% believe their managers have the skills to use AI effectively** (Gartner, Oct 2025).

> The 2026 opportunity is not "add AI to reviews". It is **governed, explainable AI assistance a manager can defend**.

---

## 6. Compliance requirements

### 6.1 EU AI Act — performance evaluation is explicitly high-risk

**Annex III, point 4(b)** covers AI systems intended for decisions affecting *"terms of work-related relationships, the promotion or termination of work-related contractual relationships… or **to monitor and evaluate the performance and behaviour of persons**."* Not a grey area.

**The timeline changed on 27 July 2026.** The Digital Omnibus on AI — **Regulation (EU) 2026/1744** — deferred Annex III obligations:

| Obligation | Original | New |
|---|---|---|
| Stand-alone Annex III high-risk (incl. performance evaluation) | 2 Aug 2026 | **2 Dec 2027** |
| Article 50 transparency | 2 Aug 2026 | **unchanged — in force** |
| Article 5 prohibitions | 2 Feb 2025 | unchanged — in force |

⚠ Commentary written before mid-2026 still says "comply by 2 August 2026". Superseded for Chapter III. It is a **deferral, not a repeal**.

**Article 26 deployer duties** (customers inherit them; the product must enable them): human oversight by competent persons; representative input data; monitoring with suspension and notification; **automatically generated logs retained at least six months**; **worker notification before use**; informing affected persons where the system makes or assists decisions about them.

**Article 86 — right to explanation.** A person subject to a decision based on an Annex III system's output has the right to *"clear and meaningful explanations of the role of the AI system"* where the decision produces legal effects or similarly significantly affects them. **A performance decision affecting promotion, pay or termination very likely qualifies.**

**Article 5(1)(f) — emotion recognition in the workplace is PROHIBITED** since 2 February 2025, where a system **infers emotions of a natural person in the workplace based on biometric data**. Explicitly excluded per Future of Privacy Forum analysis: inference of *intentions*; emotion detection from **written text**; **group** rather than individual analysis; systems not based on biometric data.

> **Encode this:** sentiment analysis on written feedback is outside the prohibition. **Voice-tone or facial-expression analysis in 1:1s or recorded reviews is inside it and must never be built.**

**Penalties:** Article 5 up to **€35m or 7% of worldwide turnover**; deployer and transparency obligations up to **€15m or 3%**. SMEs pay the lower.

### 6.2 India DPDP Act

Rules notified 13 November 2025, phased. **Substantive obligations commence ~May 2027** (sources differ by one day).

**Section 7(i)** permits processing without consent *"for the purposes of employment…"*. Practitioner commentary reads performance evaluation as covered. ⚠ **Commentary, not statute** — the Act does not enumerate "performance management". Processing must still be proportionate, purpose-specific, transparent and securely safeguarded; **retention beyond purpose fulfilment is not covered**.

**The sharpest open question:** how employer processing rights interact with an employee's right to correction and erasure. A correction request against a manager's rating has no clear resolution in the current text.

**Operational duties:** itemised notices in English and India's 22 scheduled languages; encryption, access control, monitoring; **logs retained at least one year**; breach notification with a **detailed report to the Board within 72 hours**; deletion on purpose fulfilment. Penalties up to **₹250 crore**.

**What DPDP does not do:** no automated-decision-making provision, no right to explanation, no algorithmic risk tiering.

> **Architectural consequence: build to EU AI Act Articles 26 and 86 and inherit India compliance. Never the reverse.**

---

## 7. Target architecture

### 7.1 Design position

| # | Decision | Rationale |
|---|---|---|
| **D-A** | **One goal object, two vocabularies.** OKR is a presentation and validation mode over `Individual Goal` + `KPI`, not a second data model | India buyers write "KRA" and expect OKR mechanics underneath (§5.2 #1). Two models diverge within a cycle |
| **D-B** | **KPIs stay distinct from objectives.** A KPI is a health metric you hold; an objective is a change you drive | Perdoo and Profit.co both model this; conflating them is the most common modelling error in the category |
| **D-C** | **Governance is data, not workflow code.** `permission = f(role, field, plan_state)` | SAP's own framing. Replaces a workflow engine for most requirements |
| **D-D** | **Every rating is replayable from stored inputs.** The derivation is an artefact, not a calculation | Article 86; .45 administrative rating reliability; the black-box gap across the India set |
| **D-E** | **Distribution is shown and flagged, never enforced by default.** Per-company config | Evidence is unfavourable but India expects a bell curve. Configuration resolves the conflict honestly |
| **D-F** | **Facts are immutable; corrections are new facts** | Audit trail; safe re-sync; matches accounting practice |
| **D-G** | **Targets cascade down; actuals roll up from facts** | Roll-up computed from child KPI actuals double-counts, breaks on missing children, and diverges on filters |
| **D-H** | **Ownership ≠ measurement scope.** One KPI is owned by exactly one employee but may be measured over a team | Makes both delegation scenarios pure configuration |
| **D-I** | **Credit attaches to a position, not a person** | Reorgs, vacancies and acting managers stop being special cases |
| **D-J** | **Ratios and durations store components, not results** | Averaging averages and averaging percentages are the two most likely correctness bugs |
| **D-K** | **Source-agnostic core.** ERP specifics live in adapters | Adding a source becomes configuration, not a project |
| **D-L** | **Silent truncation is a bug.** Unmapped or errored records go to a visible queue | Never drop |
| **D-M** | **Frappe-first.** Reuse `Appraisal`, `Appraisal Cycle`, `Employee` nested set, `Sales Person`, `Sales Team` before creating anything | `CLAUDE.md` §4 |

### 7.2 Object map

```
┌─ AUTHORING ─────────────────────────────────────────────────────────┐
│  Goal Library            NEW   scoping tree, GUID identity           │
│   └─ Goal Library Category   NEW   ≤4 deep                           │
│       └─ Goal Template       NEW   content: name, metric, unit,      │
│                                    direction, default weight,        │
│                                    perspective, job_family/dept      │
│                                    scope, external_id, status        │
│                                    (Inactive by default), version,   │
│                                    ► optional FK to KPI Metric       │
│                                      Definition  (§4.4, C-13)        │
│                                                                      │
│  Goal Plan               NEW   per-cycle rulebook: authoring window, │
│                                min/max goals, weight rules + toggle, │
│                                mandatory perspectives, goal periods, │
│                                approval route, band table binding,   │
│                                rating authority mode                 │
│   └─ Goal Plan Period        NEW   quarterly periods in an annual    │
│                                    cycle (D-7)                       │
│   └─ Goal Plan Field Rule    NEW   field × principal × plan_state    │
│                                                                      │
│  Attainment Band Table   NEW   from_pct, to_pct, rating, label       │
│                                mode: interpolate | step; boundaries  │
└──────────────────────────────────────────────────────────────────────┘

┌─ EXECUTION (existing, extended) ────────────────────────────────────┐
│  Individual Goal   + direction ◄── REQUIRED BY C-2                   │
│                    + attainment_pct (or computed at read)            │
│                    + source_template, template_version, plan,        │
│                      goal_period, approval_state, locked, is_measured│
│                    + the six measurement-scope fields (D3=Both)      │
│                    + key_results[]                                   │
│  KPI               + source_template, template_version, plan,        │
│                      approval_state, locked, is_measured, confidence,│
│                      guardrail_min/max, measurement_type,            │
│                      band_applied, authority_mode                    │
│                    + the six measurement-scope fields                │
│  Key Result        NEW child — OKR mode: type (numeric|percentage|   │
│                      currency|binary|milestone), weight, start/      │
│                      current/target                                  │
│  Goal Check-In     EXISTING — promote to the check-in loop ⚠         │
└──────────────────────────────────────────────────────────────────────┘

┌─ MEASUREMENT ───────────────────────────────────────────────────────┐
│  KPI Metric Definition   NEW   the extensibility point (D-4)         │
│  KPI Data Source         NEW   binds one goal/KPI to one metric+scope│
│  KPI Fact                NEW   immutable, append-only, unique        │
│                                external_reference                    │
│  KPI Credit              NEW   one row per (fact, position)          │
│  KPI Sync Log            NEW   per-run observability                 │
│  KPI Attribution Exception NEW the visible failure queue             │
│  Alvoraa Position        NEW   durable role slot (nested set)        │
│  Alvoraa Position Assignment NEW effective-dated person↔position     │
└──────────────────────────────────────────────────────────────────────┘

┌─ ASSESSMENT ────────────────────────────────────────────────────────┐
│  Rating Derivation       NEW   the replayable record                 │
│  Calibration Session     NEW   (or adopt PMS equivalent — D-1)       │
│  Calibration Sign-off    NEW   replaces the JSON blob (DEF-7)        │
│  Goal Definition Audit   NEW   or extend Goal Progress Audit Log     │
└──────────────────────────────────────────────────────────────────────┘
```

### 7.3 The measurement engine, in four questions

```
 Source systems              Ingestion            Attribution              Consumption
 ─────────────────           ──────────           ─────────────            ────────────
 ERPNext / HRMS   ─┐
 Logic ERP        ─┼─► Adapter ─► KPI Fact ─► Credit Rules ─► KPI Credit ─┬─► KPI actuals
 Ad platforms     ─┤   (per       (immutable,   (direct /      (one row    │   + Goal Evidence
 CSV / SFTP       ─┘    source)    append-only)  rollup /       per        └─► Reconciliation
                                                 split)         creditee)
```

1. **What happened?** → `KPI Fact`, one immutable record per source transaction.
2. **Who gets credit, and how much?** → `KPI Credit`, one row per (fact, position).
3. **Which goal or KPI does that credit belong to?** → matched by metric + scope + period.
4. **What is the number?** → aggregation appropriate to the metric's calculation type.

**Four calculation shapes. Every KPI reduces to one:**

| Type | Stored on the fact | Aggregation | Examples |
|---|---|---|---|
| **A · Event Sum** | `value` | `SUM(value)` | Revenue, cases sold, units produced, hires closed |
| **B · Snapshot** | `value`, `as_of_date` | latest per scope | Stock value, headcount, open positions |
| **C · Ratio** | `numerator`, `denominator` | `SUM(num)/SUM(den)` | Attrition %, defect PPM, conversion %, fill rate, DSO |
| **D · Duration** | `duration_seconds`, `event_count` | `SUM(dur)/SUM(count)` | Time-to-hire, PO cycle time, SLA response |

> **Critical rule.** Types C and D must never be aggregated by averaging child results. `AVG(percentages)` and `AVG(averages)` produce plausible, wrong numbers — the worst failure mode, because nothing looks broken. **Storing components rather than results makes the correct aggregation the only expressible one.**

**Credit types:** *Direct* (the position that transacted) · *Rollup* (every ancestor position with a team-scoped goal on this metric) · *Split* (multiple positions at declared weights, e.g. ERPNext `Sales Team.allocated_percentage`) · *Unattributed* (→ exception queue).

**Scope axis** — roll-up does not always follow the HR reporting line: `Reporting` (Employee nested set, default) · `Sales Person` (ERPNext tree, where commercial hierarchy ≠ HR hierarchy) · `Explicit` (member list).

**Realistic coverage:** ~70% of a typical scorecard from in-house ERPNext/HRMS data, ~15% via external APIs, **~15% correctly remains manual**.

---

## 8. Feature interaction map

**This is the section that makes the consolidation worth doing.** Each entry is a pair of requirements that, built independently, breaks one or both. Each carries a **guard** — the thing that must be true for both to coexist.

### 8.1 The interaction table

| ID | A | B | What breaks | Severity |
|---|---|---|---|---|
| **C-1** | FR-E1 approval state | `_set_status` in `controllers/kpi.py` | **KPIs silently approve themselves** | 🔴 Showstopper |
| **C-2** | D3 = Both (goals are a measurement target) | `Individual Goal` has no `direction` | Goals cannot express Lower-is-Better; DEF-2 gets reimplemented | 🔴 Showstopper |
| **C-3** | DEF-4 fix (`Goal Progress Update`) | Strategy §16.1 writes goal actuals to `Goal Evidence` | Two write paths, divergent totals | 🔴 Showstopper |
| **C-4** | FR-E3 lock after approval | Six measurement-scope fields on KPI | Either automation cannot re-scope, or a locked KPI's number changes silently | 🟠 High |
| **C-5** | FR-C3 goal periods inside a cycle | FR-Q2 cycle freeze | Undefined what "freeze on cycle close" freezes | 🟠 High |
| **C-6** | DEF-5 fix (batch recompute) | FR-F9 sync recompute discipline | Two recompute loops racing on the same rows | 🟠 High |
| **C-7** | FR-G1 attainment bands | `rating_from_attainment` serves KPIs **and** goals | Two kinds score differently on one appraisal | 🟠 High |
| **C-8** | FR-P1 position tree | `permissions.py` `descendants()` on `reports_to` | Credited for facts you cannot see, or vice versa | 🟠 High |
| **C-9** | FR-O4 scheduler suppression | DEF-9 unconditional app install | Guard is the only boundary; if it is skipped, emails go out | 🟠 High |
| **C-10** | FR-F4 exact idempotency | `duplicate_detector` fuzzy matching | Machine facts fuzzy-matched and silently dropped | 🟠 High |
| **C-11** | DEF-3 fix (leaf-only aggregation) | FR-L5 reporting reads facts | Two competing org totals, neither declared authoritative | 🟡 Medium |
| **C-12** | FR-B1 Goal Template library | FR-F1 KPI Metric Definition library | One object doing two jobs, or two catalogues diverging | 🟡 Medium |
| **C-13** | FR-A1 weightage budget | FR-M4 per-KR weighting | Three weight scopes, no declared precedence | 🟡 Medium |
| **C-14** | FR-I1 calibration | Two calibration implementations + bundled SKU | Users meet the untested one | 🟡 Medium |

### 8.2 The showstoppers, in detail

---

**C-1 · Adding an approval state without patching `_set_status` un-approves KPIs**

`_set_status` in `controllers/kpi.py`:

```python
def _set_status(doc):
    # Draft and Cancelled are explicit human decisions; never overwrite them.
    if doc.status in ("Draft", "Cancelled"):
        return
    if not doc.period_end or frappe.utils.getdate(doc.period_end) >= frappe.utils.getdate():
        doc.status = "Active"
    else:
        doc.status = "Achieved" if flt(doc.attainment_pct) >= 100 else "Missed"
```

It preserves exactly two states. **FR-E1 introduces `Pending Approval` into the same field.** The moment that KPI is saved — and it is saved on every progress log, every sync, every recalculation — `_set_status` sees a status that is neither Draft nor Cancelled and **overwrites it with `Active`**.

An unapproved KPI therefore becomes approved and scoreable without anyone approving it. The governance layer in §9.E would appear to work in a demo and be void in production.

> **Guard.** Approval state must **not** live in `KPI.status`. Add a separate `approval_state` field with its own enum (`Draft → Pending Approval → Approved → Locked`), and leave `status` as the lifecycle field it already is (`Active / Achieved / Missed / Cancelled`). If they must share a field, `_set_status` needs an explicit preserve-list extended in the same commit, and a test asserting that a Pending KPI survives a save after its period end.
>
> **Sequencing.** FR-E1 and the `_set_status` change ship together, or neither ships.

---

**C-2 · Goals cannot express direction, so the measurement engine cannot target them**

`KPI_AUTOMATION_STRATEGY.md` §16.1 states this plainly and nobody scheduled it:

> *"`Individual Goal` lacks the fields `KPI` has. It has `progress_mode` and `actual_progress` but no `direction` and no `attainment_pct`. Either those are added, or attainment is computed at read time for goals. **Decide before Phase 0 starts.**"*

Verified against the doctype JSON: correct. `Individual Goal` carries `progress_mode`, `actual_progress`, `progress_pct`, `trajectory` — and no `direction`.

Three consequences follow, and only the first is obvious:

1. A goal cannot be Lower-is-Better. Every zero-is-best objective is unrepresentable.
2. **DEF-2's fix is KPI-only.** When goals eventually gain `direction`, whoever adds it will write the same `0 if actual == 0` line, because that is the pattern in the codebase.
3. `_scored_items` maps goal `progress_pct` through `rating_from_attainment`, so goals and KPIs already share a scoring function while carrying different fields into it.

> **Guard.** Add `direction` to `Individual Goal` **in the same change as the DEF-2 fix**, with one shared attainment function used by both doctypes. Not two implementations that happen to agree today.
>
> **Sequencing.** This is a prerequisite of Stage 4 (measurement), but it must be done in Stage 0 alongside DEF-2 — doing it later means fixing the same bug twice.

---

**C-3 · Two write paths for goal actuals**

Three positions are currently live in the documents and the code:

| Source | Says goal actuals arrive via |
|---|---|
| `controllers/goal.py` (code) | approved `Goal Evidence` rows only |
| `KPI_AUTOMATION_STRATEGY.md` §16.1 | *"`KPI Progress Log` for KPIs, `Goal Evidence` for goals"* |
| DEF-4 / v1.1 OQ-3 recommendation | unify `Goal Progress Update` with `KPI Progress Log` |

The v1.1 recommendation **contradicts the approved strategy.** If `Goal Progress Update` is unified into `KPI Progress Log`, goals then have two inbound paths — evidence (automation) and progress log (manual) — and `recalculate_progress` must sum both without double-counting a manually-logged value that later arrives as a synced fact.

> **Guard.** Decide **D-13** before either the DEF-4 fix or Stage 4 starts, and make the answer explicit in one sentence in the code. Recommended: **`Goal Evidence` is the single write path for goals**, automation and manual alike, with `evidence_type` distinguishing them. `Goal Progress Update` is then removed, not unified — it duplicates an approval workflow `Goal Evidence` already has.
>
> **Migration risk.** If any customer data exists in `Goal Progress Update`, removal needs a patch that folds it into `Goal Evidence`. Check before deleting the doctype.

### 8.3 The high-severity interactions

---

**C-4 · Locking a KPI vs re-scoping it**

FR-E3 locks definition fields after approval. The measurement engine adds six scope fields (`measurement_scope`, `scope_axis`, `scope_depth`, `scope_org_unit`, `scope_members`, `credit_weight`) that **change the number a KPI reports**.

If scope fields are not in the locked set, an approved, locked KPI can be silently re-scoped from `Self` to `Team` and its attainment can triple with no audit and no re-approval. If they *are* in the locked set, HR cannot correct a mis-scoped KPI mid-cycle without a full unlock.

> **Guard.** Scope fields are **definition fields** and are locked. Changing them requires the FR-E4 revision request, which produces a new version and an audit row. Add a targeted HR unlock for scope alone, so a genuine mis-configuration does not require unlocking targets and weights too.

---

**C-5 · Cycle freeze vs goal periods**

Decision D-7 permits quarterly goal periods inside an annual appraisal cycle. FR-Q2 freezes KPI values when a cycle closes. `KPI_BACKLOG_DECISION_RECORD.md` flagged this interaction and left it open.

If a KPI rolls up across four quarterly periods inside one annual cycle, "freeze on cycle close" is ambiguous: does Q1's value freeze at Q1 close, or at annual close? If the latter, a Q1 credit note in December silently reopens a Q1 number the employee was already rated against.

> **Guard.** **Freeze at the smaller unit.** A goal period closes and snapshots independently; the annual cycle freeze is the union of its periods' snapshots. Late facts against a closed period post to the exception queue with a "period closed" reason and require an explicit HR reopen — never a silent restatement.

---

**C-6 · Two recompute loops**

DEF-5's fix batches `recalculate_all_progress`. FR-F9 introduces the sync-run recompute — *"collect affected positions → resolve distinct ancestors in one lft/rgt pass → recompute each affected KPI exactly once, bottom-up."*

Built separately, an hourly scheduled loop and a per-sync-run loop both write `actual_progress`, `progress_pct` and `attainment_pct` on the same rows, on overlapping schedules, each committing independently.

> **Guard.** **One recompute function, two callers.** The DEF-5 fix should build the batched, change-detecting recompute that Stage 4 will call, rather than a cheaper fix that Stage 4 then replaces. This is the one case where doing the defect fix *properly* saves the later work rather than duplicating it.

---

**C-7 · Bands must cover both goals and KPIs**

`_scored_items` maps KPI `manager_rating` and goal `progress_pct` into the same appraisal table, the latter via `rating_from_attainment`. Introducing FR-G1 bands for KPIs only means a goal at 92% and a KPI at 92% score differently on the same appraisal, with no visible reason.

> **Guard.** The band table binds at the **Goal Plan**, and applies to every scored item in the cycle regardless of doctype. One function, both paths — the same rule as C-2.

---

**C-8 · Two trees, two authorities**

`permissions.py` scopes visibility by walking `Employee.reports_to`. FR-P1 introduces `Alvoraa Position` as the credit tree, deliberately decoupled from the person hierarchy so reorgs do not rewrite history.

Once credit follows positions and visibility follows `reports_to`, the two disagree at exactly the moments the position layer exists to handle: an acting manager is credited for facts they cannot open; a moved employee's historical credit sits with a manager whose permission query no longer returns those rows.

> **Guard.** When the position layer lands, `permission_query_conditions` for `KPI Fact` and `KPI Credit` must resolve through **positions as at the fact date**, not through today's `reports_to`. Goals and KPIs themselves keep the current person-based scoping. State in one place which tree governs which object.

---

**C-9 · Scheduler suppression is the only boundary that exists**

FR-O4 guards the three scheduled jobs. FR-O5 makes app install conditional. If FR-O5 ships, FR-O4 becomes belt-and-braces. **If FR-O5 slips — and it is Wave 5 of a six-wave plan — FR-O4 is the only thing standing between a Starter tenant and daily emails about a product they did not buy.**

> **Guard.** Treat FR-O4 as **permanent**, not as a stopgap for FR-O5. Guard at the top of each job, tested independently of installation state.

---

**C-10 · Exact idempotency vs fuzzy duplicate detection**

`alvoraa_goals/validators/duplicate_detector.py` matches evidence on value and date with a similarity threshold. The measurement engine relies on an exact unique `external_reference`. The strategy says the fuzzy detector *"stays on the manual path only"* — a sentence in a document, not a constraint in code.

If a synced fact passes through the manual validator, two legitimate invoices for the same amount on the same day are flagged as duplicates and one is dropped. Silently, and exactly during month-end when identical round-number transactions are most common.

> **Guard.** Branch on `synced_from_external` / `is_system_generated` at the top of the validator chain and exit before fuzzy matching. Add a test that two synced facts with identical value and date both persist.

### 8.4 The medium interactions

**C-11 · Two org totals.** DEF-3's fix makes cascade aggregation leaf-only; FR-L5 makes facts the reporting source. Both compute an org total by different routes. **Guard:** declare `KPI Fact` authoritative for all roll-up reporting; `Goal Cascade.aggregate_progress_pct` becomes a cached convenience with a documented refresh, not a second answer.

**C-12 · Two libraries.** §4.4 sets out the resolution: `Goal Template` holds content, `KPI Metric Definition` holds computation, joined by a nullable FK. **Guard:** one team owns both, or they fragment within a cycle. Seed both from one starter dataset in one operation.

**C-13 · Three weight scopes.** FR-A1 governs weights across an employee's cycle; FR-M4 governs weights across a Key Result's parent objective; FR-G3 governs weights within an appraisal section. These are legitimately different scopes, but nothing currently declares their precedence. **Guard:** state the hierarchy explicitly — KR weights sum to 100 *within an objective*; objective and KPI weights sum to 100 *within an employee-cycle*; section weights sum to 100 *within an appraisal*. Three independent invariants, validated separately, never summed together.

**C-14 · Two calibration implementations, now bundled.** `performance_api.py` endpoints vs the unrun `PMS Calibration Session` module, sold as one SKU since 2026-08-23. **Guard:** D-1.

### 8.5 Sequencing constraints derived from the above

Read this as the hard ordering rules; §11 turns them into stages.

```
DEF-2 fix ──must ship with── C-2 (direction on Individual Goal)
FR-E1     ──must ship with── C-1 (_set_status patch or separate field)
D-13      ──must precede──── DEF-4 fix AND Stage 4
DEF-5 fix ──must anticipate─ FR-F9 (build the shared recompute once)
FR-G1     ──must cover────── goals and KPIs together
FR-P1     ──must update───── fact/credit permission queries
FR-O4     ──is permanent──── independent of FR-O5
D-1       ──must precede──── any calibration work
```


---

## 9. Functional requirements

**Priority:** P0 blocks correct operation today · P1 competitive parity · P2 differentiator · P3 later.
**Origin:** DEF defect · FLOOR India feature floor (§5.2) · DIFF differentiation (§5.3) · ENT enterprise pattern (§5.4) · EVID research evidence (§5.6) · REG compliance (§6) · KPIA legacy backlog story.

---

### A. Defect remediation — P0

| ID | Requirement | Acceptance criteria | Origin |
|---|---|---|---|
| **FR-A1** | The weightage budget counts `Individual Goal` weightages alongside `KPI` weightages for the same employee and cycle | A save that would take the combined total above the plan ceiling is blocked, naming the current total and both contributing sources. Test: KPI 100% + objective 20% rejected at save, not at appraisal generation | DEF-1, KPIA-46 |
| **FR-A2** | Attainment distinguishes *unmeasured* from *measured as zero*. A `Lower is Better` item achieving zero scores at or above 100% | Test: target "≤5 incidents", actual 0 with an approved log → attainment ≥100%, status Achieved. Same item with no approved log → attainment null, excluded from scoring, shown as "Not yet measured". **Implemented once, used by both `KPI` and `Individual Goal`** | DEF-2, **C-2** |
| **FR-A3** | Cascade aggregation counts each level of the goal tree once | Test: one parent objective (₹10 cr) and five children (₹2 cr) reports ₹10 cr, not ₹20 cr. `Cascade Alignment Report` computed on the same basis | DEF-3, **C-11** |
| **FR-A4** | `Goal Progress Update` is removed, and any existing rows are folded into `Goal Evidence` by patch | Blocked on **D-13**. No child table with an approval workflow may exist without affecting the number it appears to affect | DEF-4, **C-3** |
| **FR-A5** | Recalculation writes only on change, commits in batches, and aggregates each cascade once per run. **Built as the shared recompute function Stage 4 will call** | Measured: 200 employees × 6 goals with no changes produces zero saves and zero audit rows. Completes in one `long`-queue slot | DEF-5, **C-6**, KPIA-27 |
| **FR-A6** | Draft items do not consume the weightage budget | Test: two Draft alternatives at 60% each both save | DEF-6 |
| **FR-A7** | `Individual Goal` gains `direction`, and attainment for goals is computed by the same function as for KPIs | Test: a Lower-is-Better objective scores identically to an equivalent KPI | **C-2**, D3=Both |

> **FR-A1, A2, A3 and A7 must ship before any measurement work.** They produce wrong numbers today, and A2/A7 must ship together or the same bug is written twice.

### B. Goal and KPI content library — P1

| ID | Requirement | Acceptance criteria | Origin |
|---|---|---|---|
| **FR-B1** | HR maintains a `Goal Library`: a tree of categories (≤4 deep) containing `Goal Template` entries carrying name, description, perspective, unit, direction, progress mode, measurement type, default weightage, suggested target basis | — | ENT, FLOOR #4 |
| **FR-B2** | A template carries scoping attributes **on the entry**: company, department, designation, job family, plus `external_id` | Filtering at read time returns only applicable templates. Scoping does not require a separate library per population | ENT (Oracle) |
| **FR-B3** | A template's `status` defaults to **Inactive**; only Active templates are selectable | Test: a new template does not appear in goal creation until activated | ENT (Oracle) |
| **FR-B4** | Libraries export and re-import as **typed CSV**, one row per node discriminated by a `type` column | Round-trip produces no duplicates. Import upserts on a stable template code, never on name. A malformed row reports its line number and does not abort the file | ENT (SAP) |
| **FR-B5** | Templates are **versioned**; a goal records `source_template` and `template_version` at creation | Test: editing a template does not alter any goal already created from it | ENT |
| **FR-B6** | Library identity is a stable GUID referenced by the `Goal Plan`, not a name | Test: renaming a library breaks no plan binding | ENT (SAP) |
| **FR-B7** | A `Goal Template` may bind to a `KPI Metric Definition` by **nullable foreign key** — content and computation are configured together, never merged into one object | Test: a template with no metric binding is fully usable for a manual goal | **C-12**, §4.4 |
| **FR-B8** | A starter dataset seeds **both** the goal library and the metric library in one operation | Merges KPIA-4 with the library story without conflating the two objects | D-8, KPIA-4 |
| **FR-B9** | Library rendering paginates and stays responsive at 1,000 entries | Goal creation renders under 1s at SAP's published ceiling | ENT sizing |

### C. Goal plan and cycle governance — P1

| ID | Requirement | Acceptance criteria | Origin |
|---|---|---|---|
| **FR-C1** | HR defines a `Goal Plan` per cycle carrying: authoring window, min/max goal count, weightage rules, mandatory perspectives, target-required flag, approval route, band table binding, rating authority mode | The plan is the governance object; goals inherit and cannot override | ENT |
| **FR-C2** | **The authoring window is separate from the execution window.** After it closes the employee cannot add, edit, delete or cancel goals, but **can still update progress and submit for approval**. Managers and HR unaffected | Test all six permutations | ENT (Oracle 25D) |
| **FR-C3** | The plan defines **goal periods independent of the appraisal cycle** | Test: four quarterly periods inside one annual cycle; items roll up across periods to one review. **Interacts with FR-Q2 — see C-5** | D-7, FLOOR #5 |
| **FR-C4** | "Weightages must total 100" is a **per-plan toggle, default ON** | Customers running un-normalised weights are not broken on upgrade | D-6 |
| **FR-C5** | Cycle types include annual, half-yearly, quarterly, **probation** and project-based, assignable per business unit | Probation review is a standard India requirement absent today | FLOOR #5 |
| **FR-C6** | Rules produce a per-employee **readiness state** (Complete / Incomplete / Out of policy) visible before the cycle opens, naming the failing rule | — | ENT |
| **FR-C7** | Field visibility and editability are declared as `field × principal × plan_state → None/Read/Write`, principal ∈ {owner, manager, HR admin, other} | Collapsed from the enterprise nine-role algebra per §5.5 | ENT |
| **FR-C8** | Conflict resolution is unambiguous: hides only if **every** applicable rule hides; required if **any** rule requires; **Required beats Hidden** | Test each conflict case | ENT (Workday) |
| **FR-C9** | Each constraint is individually configurable as **advisory (warn) or blocking (throw)** | Avoids SAP's soft/hard split | ENT, KBA 2457856 |

### D. Validation — P0/P1

| ID | Requirement | Acceptance criteria | Origin |
|---|---|---|---|
| **FR-D1** | All validation executes in the document controller, so portal, desk, REST and bulk-import paths are guarded identically | Test each of the four paths against the same invalid input | Existing pattern |
| **FR-D2** | A numeric item requires a target; a `Lower is Better` item requires a baseline | Blocked at save, naming the missing field | FR-11 legacy |
| **FR-D3** | Period falls inside the plan period; end after start | Blocked at save | FR-12 legacy |
| **FR-D4** | Goal count outside min/max **warns** by default (blocking configurable per FR-C9) | 6–10 is guidance, not policy | EVID |
| **FR-D5** | A measurability check flags a numeric item with no target, no unit, or a purely qualitative description | Warning naming the deficiency | EVID |
| **FR-D6** | Perspective coverage against mandatory perspectives is reported per employee | Advisory | Existing strength |

### E. Lifecycle — approval, locking, revision — P1

| ID | Requirement | Acceptance criteria | Origin |
|---|---|---|---|
| **FR-E1** | Items gain a **Pending Approval** state between Draft and Active. Only an Approved item scores. **This lives in a separate `approval_state` field, not in `status`** | Test: an unapproved item is excluded from `_scored_items`. Test: a Pending item survives a save after its period end without becoming Active | ENT, **C-1** |
| **FR-E2** | Approval is **single-step manager approval**. While pending the plan is locked; only employee and approver see changes; rejection reverts | Multi-approver routing explicitly out of scope | §5.5 |
| **FR-E3** | On approval the item **locks**: target, weightage, unit, direction, period **and the six measurement-scope fields** become read-only. HR can unlock individually, in bulk, or scope-only, with a reason | Test: a locked item rejects a target change and a scope change from employee, manager and API | ENT, **C-4** |
| **FR-E4** | A mid-cycle change to a locked item requires a **revision request** carrying a reason, routed to the manager. On approval a new version is written and the prior retained | Test: the original definition remains readable. **No vendor in the India scan documents this** | Whitespace |
| **FR-E5** | An abandoned item moves to a terminal **No Longer Pursued** state with a reason. Deletion of an approved item is prohibited | Copy Oracle's action matrix: cancelled disables move/copy/extend/align/assign | ENT, BP6 |
| **FR-E6** | **Every change to a definition** writes an audit row: actor, timestamp, field, old, new, reason where required | Distinct from the existing progress-only audit. Retention matches the appraisal record | REG |
| **FR-E7** | Cycle settings freeze on launch — rating scale, reviewers, form structure, weightage rules | Matches the one competitor that documents this precisely | FLOOR #12 |

### F. Measurement engine — P2

Absorbs `KPI_AUTOMATION_STRATEGY.md` and KPIA epics E1, E2, E3, E4, E6.

| ID | Requirement | Acceptance criteria | Origin |
|---|---|---|---|
| **FR-F1** | HR defines a reusable `KPI Metric Definition` — name, calculation type, source, filters, attribution — **without a developer** | Ratio requires numerator and denominator; Duration requires from and to; Event Sum/Snapshot require a single value field and hide the others. Non-HR gets read-only | KPIA-1, D-4 |
| **FR-F2** | A metric can be **previewed against live data before saving** | Up to 20 sample rows with resolved value, date and owner. Unmapped rows flagged with the raw owner key. **No facts written.** Zero rows returns an explicit "no matching records", not an empty success | KPIA-2 |
| **FR-F3** | A metric binds to a KPI **or an `Individual Goal`** with scope filters | **Both target paths, per D3=Both.** Test the same metric bound to one of each | KPIA-3, §4.1 |
| **FR-F4** | Automation can be **turned off per item**, reverting to manual entry without data loss | Test: disabling sync leaves existing facts and the current value intact | KPIA-5 |
| **FR-F5** | A scheduled job ingests source transactions as immutable `KPI Fact` rows | Hourly incremental over a trailing 24h overlapping window; nightly reconcile over the full open period; nightly snapshot for type-B | KPIA-6 |
| **FR-F6** | **Re-running a sync never double-counts.** `external_reference` carries a unique index; sync is upsert by that key | Test: the same window run three times produces identical totals. **Fuzzy duplicate detection must not run on synced facts — see C-10** | KPIA-7, **C-10** |
| **FR-F7** | A cancelled or amended source document posts a **compensating reversal fact**, never an edit | Test: the original fact is unchanged and the log reads as a ledger | KPIA-8, D-F |
| **FR-F8** | Unmappable owners land in a **visible exception queue**, resolvable by mapping the owner key | Test: an unmappable row appears with its reason and raw key; resolving it re-credits without re-ingesting. Silent dropping is a defect | KPIA-9, KPIA-10, D-L |
| **FR-F9** | Every sync run writes a log; recompute is **batched bottom-up, each affected item exactly once**. **This is the same function as FR-A5** | Per-fact cascading is O(facts × depth) and will not survive month-end | KPIA-11, KPIA-27, **C-6** |
| **FR-F10** | Source unreachable **holds the last value**. Never zero, never partial commit | Test: adapter failure leaves attainment unchanged and raises a visible staleness flag | KPIA-12, D-L |
| **FR-F11** | The four calculation shapes aggregate correctly. **Ratio and Duration store components, never results** | Test: aggregating child ratios produces `SUM(num)/SUM(den)`, not `AVG(pct)`. Unit tests per shape | KPIA-13..16, D-J |
| **FR-F12** | Five adapter patterns normalise to one fact shape, in preference order: native ORM · vendor REST · **read-only SQL view on a replica** · scheduled SFTP drop · manual CSV | No source-specific logic outside its adapter. The SQL option is a differentiator — only Profit.co offers it | KPIA-32/33, D-K, DIFF #4 |
| **FR-F13** | **Outbound polling only.** Frappe initiates; no inbound firewall rule is ever required. Credentials encrypted, per-company, read-only service accounts | Removes the largest customer-IT objection | KPIA-34 |
| **FR-F14** | An employee can **see which source documents produced their number**, and drill from a team figure to per-person contribution | Test: every aggregate is traceable to its facts | KPIA-17, KPIA-23 |
| **FR-F15** | **Synced evidence auto-approves** (`approved_by = System`); manual entry keeps manager review | The ERP is the system of record; manager confirmation adds no signal | KPIA-18 |
| **FR-F16** | A manager's item can be measured on **their team's activity**, at any depth, including where reports have no items of their own | Scenario A (manager delegates fully) and Scenario B (only the manager has a KPI) both produce correct numbers at 3+ levels. Works because facts are created for every mapped position regardless of whether an item exists there | KPIA-19, KPIA-20, KPIA-21, D-H |
| **FR-F17** | **Split credit** is honoured where the source declares it | ERPNext `Sales Team.allocated_percentage`. Test: a shared deal credits both parties at declared weights, summing to the fact value | KPIA-22 |
| **FR-F18** | Sales rolls up the **`Sales Person` tree**, not the HR reporting line, where configured | Commercial hierarchy diverges from the HR chart in multi-tier distribution | KPIA-24, D-5 |
| **FR-F19** | **Company and BU reports read `KPI Fact`, never `SUM(item.actual_value)`** | Enforced in code and documented for dashboard authors. A three-level sales org must not report 3× revenue | KPIA-25, D-G, **C-11** |
| **FR-F20** | **Quota coverage** is shown at cascade time: allocated child targets ÷ parent target. The system does **not** force equality — over-assignment (typically 110–130%) is deliberate | Extends the half-built `Cascade Alignment Report` | KPIA-26 |
| **FR-F21** | External ERP totals **reconcile to item totals** within a declared tolerance, reported | Test: a deliberate discrepancy is surfaced, not absorbed | KPIA-35 |
| **FR-F22** | Sync is **scheduled and automatic**, with a visible last-sync timestamp and staleness indicator per item | Keka requires a manual click per goal. Automatic sync is the differentiator | Whitespace |

### G. Scoring and explainability — P1 (differentiator)

| ID | Requirement | Acceptance criteria | Origin |
|---|---|---|---|
| **FR-G1** | An **Attainment Band Table** maps attainment ranges to ratings, as configuration. Bound at the plan, overridable per item, **applied to goals and KPIs alike** | Rows: from_pct, to_pct, rating, label. Bulk-importable | ENT, DIFF #1, **C-7** |
| **FR-G2** | **Interpolate** and **step** modes, one per plan, with declared boundary behaviour above and below the table | Test: 92% between a 90%→3.0 row and 100%→4.0 yields 3.2 interpolated, 3.0 stepped | ENT (SAP) |
| **FR-G3** | Item ratings roll to a section rating and an overall rating by weighted average, **precise values carried throughout, rounding applied only at the end** | Oracle's arithmetic exactly. Un-weighted items ignored; mixed rating models normalised each against its own maximum | ENT (Oracle) |
| **FR-G4** | **Every rating produces a `Rating Derivation` record** capturing every input, the band applied, the mode, all weights, the arithmetic, the authority mode, and every override with its reason | Given the record alone, the rating recomputes and must match | REG Art. 86, DIFF |
| **FR-G5** | The employee can **see their own derivation in plain language** — "Your KPI attained 92%. Under the FY27 band table (interpolate) that maps to 3.2. At 30% weight it contributed 0.96 of your 4.1 overall." | The feature no competitor in the scan offers, and the Article 86 obligation | REG, Whitespace |
| **FR-G6** | Rating authority — band-derived or manager-authoritative — is configurable **per company** and **snapshotted onto the cycle at cycle open** | Changing the org setting affects future cycles only. Prevents a mid-cycle flip silently re-deriving completed appraisals | D-9 |
| **FR-G7** | Manager override is permitted in band-authoritative mode with a **mandatory reason**, and is audited | Never let automation finalise a material outcome without human sign-off | EVID, BP8 |
| **FR-G8** | Attainment cap and floor are declared configuration, not hardcoded | Over-attainment policy is a business decision | — |

### H. Continuous performance — P1

| ID | Requirement | Acceptance criteria | Origin |
|---|---|---|---|
| **FR-H1** | **Check-ins** are first-class on a configurable cadence: value, note, and a red/amber/green **confidence** | `Goal Check-In` exists in the schema ⚠ — promote rather than replace. **Outstanding: confirm whether it is referenced by any live code path** | FLOOR #7 |
| **FR-H2** | **Confidence is a separate field from calculated status.** Status derives objectively from progress vs *expected* progress; confidence is the human narrative on top | Only WorkBoard documents this split. A team "behind pace but confident" must be able to say so | DIFF #3 |
| **FR-H3** | Status derives automatically from time-elapsed vs attainment; the existing `_update_trajectory` thresholds become configurable | Generalise the right shape already in the code | Existing strength |
| **FR-H4** | **1:1 meetings** with agendas, carry-forward of open items, and action items linked to goals | `Appraisal Action Item` exists but is bound to the appraisal, not a recurring conversation | FLOOR #7 |
| **FR-H5** | Nudges and reminders on overdue check-ins, in-product and by email. **Suppressed where the feature is unentitled (FR-O4)** | Table stakes across the OKR category | §5.3, **C-9** |
| **FR-H6** | Feedback prompts are **task-focused, never person-focused**, by design of the templates | Kluger & DeNisi: feedback directing attention to the self degrades performance. A design constraint, not a preference | EVID |
| **FR-H7** | **No passive behavioural monitoring.** No keystroke, screen-time, activity or presence signal is captured as a performance input | Meta-analytic evidence: performance r = −0.01, stress +0.11. Also a defensible market position | EVID |
| **FR-H8** | 360 / multi-rater with **nomination and manager approval of nominees** | The mid-market refinement. Reviewers exist today; the nomination flow does not | FLOOR #6 |

### I. Calibration and 9-box — P1

| ID | Requirement | Acceptance criteria | Origin |
|---|---|---|---|
| **FR-I1** | Resolve the **duplicate calibration implementations** before building anything new | Blocked on **D-1** | **C-14** |
| **FR-I2** | A session scopes a population, names facilitators, and shows a **rating distribution histogram** against an optional target | Mid-market calibration is a table with a distribution and an activity log, not a succession suite | §5.5 |
| **FR-I3** | Every rating change records **who, when, from, to and a mandatory reason** | The audit artefact in a grievance | REG |
| **FR-I4** | Distribution is **shown and outliers flagged; enforcement is off by default**, configurable per company | Evidence against forced distribution is strong; India expects a bell curve | D-E, FLOOR #10 |
| **FR-I5** | **9-box on performance × potential**, the two scores **never collapsed into one** | `potential_rating` and `avg_potential_rating` already exist | FLOOR #11 |
| **FR-I6** | Managers of employees under review cannot change their own reports' ratings in-session unless named facilitator | Standard control | ENT |
| **FR-I7** | Scoped administrators see only their scope and are **read-only** outside it | Consistent with existing row-level scoping | ENT |
| **FR-I8** | **Calibration sign-off is a first-class record**, not a JSON value in `page_settings`: one row per sign-off, linked to cycle and signer, history preserved on re-sign | Test: signing off twice yields two retrievable records. Queryable by signer, cycle and date | DEF-7 |

### J. AI assistance — P2

Every requirement gated by §6.1. Read FR-J6 before building any other.

| ID | Requirement | Acceptance criteria | Origin |
|---|---|---|---|
| **FR-J1** | **AI goal drafting** from role, department, strategy context and library content, each suggestion accompanied by an explanation of the data used | Table stakes: Perdoo, Betterworks, Leapsome, WorkBoard, SAP all ship it | §5.3 |
| **FR-J2** | **AI goal *critique*** — score an existing goal against declared quality criteria and propose a rewrite | **No vendor in the study offers this.** Genuine whitespace | DIFF #7 |
| **FR-J3** | AI-drafted narrative sourced **strictly from that employee's own goals, check-ins and feedback** — never invented, never cross-employee | Test: every sentence traces to a retrievable source record | REG, EVID |
| **FR-J4** | **AI never proposes or sets a rating.** It surfaces evidence and drafts language | Given .45 administrative rating reliability, an AI-proposed rating is a liability | EVID, REG |
| **FR-J5** | Every AI-assisted action is logged with model, inputs, output and the human decision that followed. **Logs retained at least six months** | Art. 26(6) | REG |
| **FR-J6** | **Prohibited by design:** no emotion recognition from biometric data; no voice-tone analysis; no facial-expression analysis. Sentiment analysis on **written text** is permitted | Art. 5(1)(f), in force since Feb 2025, penalties to €35m / 7%. A hard architectural boundary | REG |
| **FR-J7** | Where AI assists a decision with legal or similarly significant effect, the affected person can obtain a clear explanation of the system's role | Art. 86. Satisfied by FR-G5 plus FR-J5 | REG |
| **FR-J8** | The customer can inform workers and their representatives that a high-risk system is in use, with product support for that notification | Art. 26(7) places the duty on the employer; the product must make it possible | REG |

### K. Assignment at scale — P1

| ID | Requirement | Acceptance criteria | Origin |
|---|---|---|---|
| **FR-K1** | HR assigns a template or set of templates to many employees at once, filtered by designation, department, grade, company or reporting line | An HR team of three configuring 800 employees will not hand-build goal trees | FLOOR #4 |
| **FR-K2** | Bulk assignment is **preview-then-commit**, listing what will be created and every conflict before commit | Test: an employee who already holds the template appears in the conflict list | ENT |
| **FR-K3** | Bulk assignment applies the same validation as single creation, is transactional per employee, and reports per-employee outcomes | A single bad row never aborts the batch silently | NFR |
| **FR-K4** | 500 employees complete within one background job without per-employee round trips | Measured | NFR |
| **FR-K5** | Bulk operations that cannot be undone say so before commit, and record what was done | A documented competitor complaint pattern | §5.7 |

### L. Reporting — P1

| ID | Requirement | Acceptance criteria | Origin |
|---|---|---|---|
| **FR-L1** | Cascade alignment: parent target vs sum of child targets, with variance and verdict | Half-built already. Fix per FR-A3 and surface | Existing strength |
| **FR-L2** | Goal-setting completion and readiness by org unit, before the cycle opens | FR-C6 as a report | ENT |
| **FR-L3** | Rating distribution by manager, department and company, with **manager leniency/severity surfaced before calibration**, not after | Nobody in the India scan does this pre-meeting | Whitespace |
| **FR-L4** | Exports are structured for re-use without manual restructuring | The single most consistent buyer complaint. CSV and XLSX, flat, stable column names | §5.7 |
| **FR-L5** | All roll-up reporting reads facts (FR-F19). `Goal Cascade.aggregate_progress_pct` is a cached convenience with a documented refresh, **not a second answer** | Declare one authority | **C-11** |

### M. OKR mode — P2

| ID | Requirement | Acceptance criteria | Origin |
|---|---|---|---|
| **FR-M1** | OKR is a **mode, not a second model**: an Objective is an `Individual Goal`, Key Results are a child table, and `KPI` continues to represent held health metrics | Test: switching a cycle between KRA and OKR presentation migrates no data | D-A, D-B |
| **FR-M2** | Key Result types: **numeric, percentage, currency, binary, milestone** | The category's table stakes | §5.3 |
| **FR-M3** | **Guardrail types** — stay above X, stay below X, between X and Y | Only Perdoo and Profit.co offer these | DIFF #5 |
| **FR-M4** | Per-KR weighting with a "distribute remaining" helper and equal weights by default at publish. **KR weights sum to 100 within an objective — a separate invariant from FR-A1** | Only Leapsome and Profit.co document weighting | DIFF #2, **C-13** |
| **FR-M5** | Objective progress rolls from Key Results by a **declared, configurable** method | Perdoo's weakest-child and weighted-average are both legitimate; make it configuration | §5.3 |
| **FR-M6** | Terminology is configurable per tenant — a customer that says "KRA" sees "KRA" | greytHR renames OKR constructs into KRA language as a positioning decision, and it works | FLOOR #1 |

### N. India-specific — P2 (uncontested ground)

| ID | Requirement | Acceptance criteria | Origin |
|---|---|---|---|
| **FR-N1** | Rating outcome drives **variable pay and increment computation against India CTC structures**, with bulk appraisal-letter generation | HROne is the only vendor doing this, and it is where the module earns its budget in India | Whitespace |
| **FR-N2** | A **frontline performance model**: supervisor-observed competencies and output-linked KPIs, completing in under two minutes on a phone | No vendor in the scan offers a distinct frontline model | Whitespace |
| **FR-N3** | Review forms and employee-facing notices in **English plus India's scheduled languages** | DPDP notice obligation and a genuine frontline requirement | REG, Whitespace |
| **FR-N4** | **PIP documentation** structured for Indian labour-law scrutiny: dated objectives, recorded support, evidence of review meetings, outcome record | Unaddressed across the entire scan | Whitespace |
| **FR-N5** | Adapters for the systems Indian mid-market KPIs actually live in — Tally, Zoho Books, Zoho/Salesforce CRM, LeadSquared, service-desk volumes | No vendor in the India scan integrates with any of them | Whitespace |

### O. Entitlement and plan lifecycle — P0/P1

Sits alongside `MODULE_ACCESS_STRATEGY.md` Waves 4–6; states what those waves must deliver **for this feature**.

| ID | Requirement | Acceptance criteria | Origin |
|---|---|---|---|
| **FR-O1** | **Every whitelisted endpoint touching goals, KPIs, cascades, evidence or appraisal scoring checks entitlement server-side** before doing anything | Test: a Business-plan site returns a structured "not included in your plan" from `performance_api`, `goals_api` and the goals endpoints in `hr_api` — not a traceback, not an empty list. A decorator, not 157 hand-written checks | DEF-8 |
| **FR-O2** | **Downgrade hides; it never destroys.** Goals, KPIs, evidence, logs and appraisal history survive intact and reappear on re-upgrade | Test: Enterprise → Business → Enterprise leaves every record byte-identical | MODULE_ACCESS §7 |
| **FR-O3** | The **fail-open default is bounded by a provisioning backfill** — every existing tenant has an explicit `features` list | Audit: zero tenant sites lack the key. The fail-open branch stays as a safety net, not the normal path | §3.4 |
| **FR-O4** | **Scheduled jobs and outbound email are suppressed for unentitled features.** `recalculate_all_progress`, `check_cascade_alignment` and `send_progress_reminders` return immediately on a site without `goals`. **Permanent, not a stopgap** | Test: a Starter site with `alvoraa_goals` installed sends zero reminder emails and performs zero recalculation writes | DEF-9, **C-9** |
| **FR-O5** | App installation is conditional, or FR-O4 is documented as the permanent boundary | `provision_tenant.sh` and `tenant_api.py` agree on which apps a plan installs | DEF-9 |
| **FR-O6** | **One provisioning path, one plan vocabulary.** Both writers emit the same `features` list from the same registry | Test: a site provisioned by script and one by API, same plan, produce identical `enabled_features()` output. Retire `modules_enabled` or derive it | DEF-9 |
| **FR-O7** | The portal hides goals and performance navigation when unentitled — **cosmetic layered on FR-O1, never instead of it** | Test hidden UI and denied API independently | MODULE_ACCESS Wave 6 |
| **FR-O8** | Duplicate `Alvox Goals` / `Alvox Portal` Module Defs are deleted before any Module Profile is built from a module list | A stale Module Def in a block list is a silent mis-gate | MODULE_ACCESS §8 |

### P. Positions and effective dating — P2

Absorbs KPIA epic E5. Resolves **D-2** as in scope.

| ID | Requirement | Acceptance criteria | Origin |
|---|---|---|---|
| **FR-P1** | `Alvoraa Position` (durable role slot, nested set) and `Alvoraa Position Assignment` (effective-dated person↔position, type Primary / Acting / Dotted) | Credit resolves: `fact.date` → position holding the source's owner at that date → ancestors at that date → credit rows | KPIA-28, D-2 |
| **FR-P2** | Positions **backfill from the existing reporting structure** | Test: backfill on a live org produces a position tree congruent with today's `reports_to` | KPIA-29 |
| **FR-P3** | **A mid-cycle reorganisation leaves historical credit intact** | Test: an employee moves teams on 1 July; April–June credit stays with the former manager | KPIA-30, D-I |
| **FR-P4** | Vacant and acting positions are ordinary cases, not exceptions | Vacant positions accrue credit that lands with the eventual occupant or escalates to the parent | KPIA-31 |
| **FR-P5** | **Fact and credit visibility resolves through positions as at the fact date**, while goals and KPIs keep person-based scoping. One statement declares which tree governs which object | Test: an acting manager can open the facts they are credited for | **C-8** |
| **FR-P6** | **Fallback if descoped:** denormalise `manager_position_at_date` onto the fact at creation | Solves reorg roll-up only. Does not give vacancy, acting or dotted-line. A deliberate partial hedge, not a stepping stone — backfilling the full model later is painful | Strategy §7.3 |

### Q. Trust, dispute and anti-gaming — P2

Absorbs KPIA epic E7.

| ID | Requirement | Acceptance criteria | Origin |
|---|---|---|---|
| **FR-Q1** | An employee can **dispute a synced entry without editing it** | Necessary in Scenario B, where reports have no items yet their transactions drive a manager's score. Test: dispute raises an HR review; the fact is unchanged | KPIA-36 |
| **FR-Q2** | **Values freeze when a period closes.** Syncing stops for that period and the value is snapshotted. Late facts post to the exception queue with a "period closed" reason and require explicit HR reopen | **Freezes at the goal-period level, not only the cycle level — see C-5.** Without this a January credit note reopens a settled appraisal | KPIA-37, **C-5** |
| **FR-Q3** | Metrics where **the scored person produces the data** are flagged at design time | `measured_by_role` on the metric definition. Cheap now; expensive once appraisals depend on it | KPIA-38 |
| **FR-Q4** | Fact visibility is **scoped by role and hierarchy** — employees never see peers' facts; managers see their subtree only | Extends existing row-level scoping to the new objects | KPIA-39 |
| **FR-Q5** | **Personal and commercial data held in HR is limited.** Aggregates live on the item; document detail stays in `KPI Fact` with restricted read | Customer names and invoice values entering an HR system widens PII scope | KPIA-40, REG |

---

## 10. Non-functional requirements

| Dimension | Requirement | Verification |
|---|---|---|
| **Performance** | Library and bulk screens paginate. Goal creation renders <1s at 1,000 entries. 500-employee bulk assignment in one background job. Recalculation writes only on change. Aggregate-at-source is O(employees), not O(transactions). Nested-set roll-up is O(log n) per lookup | Load test at 2,000 employees × 8 goals |
| **Security** | All validation server-side. **Entitlement enforced server-side (FR-O1).** Library edit restricted to HR Manager / System Manager. Row-level scoping on every new object. Credentials encrypted, per-company, never logged. `ignore_permissions` scoped to the single record being written | `test_permissions.py` extended to every new doctype, **blocking in CI** |
| **Reliability** | Bulk operations transactional per row with per-row outcomes. Sync degrades to last-known value, never zero. No partial commits. Per-source circuit breaking. Idempotent replay | Fault injection on the adapter layer |
| **Scalability** | Templates and plans scale with roles, not employees. `KPI Credit` grows with org depth — a 3-deep org triples rows per fact; index on `(position, kpi, fact_date)`, partition by cycle if needed. One connection **per company**, never one global | Volume test at 3 levels × 100k facts |
| **Maintainability** | Content and computation libraries joined by FK, owned by one team (**C-12**). One recompute function (**C-6**). One attainment function across both doctypes (**C-2**). Source specifics never leak out of adapters | Architectural review against §8 |
| **Data integrity** | Template edits never mutate in-flight goals. Approved definitions versioned, never overwritten. Facts immutable; corrections are compensating entries. Rating authority snapshotted at cycle open. Unique `external_reference` | Test each invariant |
| **Auditability** | Definition audit (FR-E6), rating derivation (FR-G4), calibration decisions (FR-I3), AI actions (FR-J5), sync runs (FR-F9). Retention matches the appraisal record; AI logs ≥6 months; DPDP logs ≥1 year | Retention policy test |
| **Multi-company** | Library shared with per-company overrides. Every library read enforces company isolation. Rating authority scoped per company. One source connection per company | `test_permissions.py` |
| **Explainability** | Every rating replayable from stored inputs | Given a derivation record alone, recomputation matches |
| **Entitlement** | Gating fails **closed** at the API while `enabled_features()` fails **open** at the registry — deliberate opposites: an unknown plan grants, an unentitled call refuses | Business-plan site tested against every endpoint |
| **Compliance / privacy** | PII scope widens when commercial data enters HR. Aggregates on the item, detail in facts with restricted read. Encryption at rest is required, not optional — Frappe's `encryption_key` protects stored credentials, **not** employee PII columns | DPIA before Stage 4 |

---

## 11. Delivery plan

Named **Stages** to avoid colliding with `MODULE_ACCESS_STRATEGY.md`'s Waves 1–6 and the strategy's Phases 0–4. Mapping to both is in §13.3.

**Every stage boundary carries the §8 guards that apply to it.** A stage is not done until its guards are demonstrated, not just its requirements.

| Stage | Content | Guards that must hold | Why here |
|---|---|---|---|
| **0 — immediate** | FR-A1, **FR-A2 + FR-A7 together**, FR-A3, FR-A6 · FR-O1, FR-O4 · FR-E6 | **C-2** (one attainment function), **C-9** (FR-O4 permanent) | Four defects produce wrong numbers today. FR-O1 makes a priced feature priced. FR-O4 stops a Starter tenant getting daily emails. All small, all independent |
| **1** | **D-13 decided**, then FR-A4 · **FR-A5 built as the shared recompute** · FR-O2, O3, O5, O6, O8 · §B Library · §C Goal Plan · §D Validation | **C-3** (one write path), **C-6** (one recompute), **C-12** (two libraries, one FK) | Authoring foundation on a provisioning path that agrees with itself. Unblocks the metric library Stage 4 needs |
| **2** | §E Lifecycle — approval, lock, revision, terminal states · §K Bulk assignment | **C-1** (approval state must not live in `status`), **C-4** (scope fields are locked) | The India whitespace. Governance and scale once there is content to govern |
| **3** | §G Scoring and explainability | **C-7** (bands cover goals and KPIs) | The defensible position and the Art. 86 prerequisite. Needs the plan and band table from Stage 1 |
| **4** | §F Measurement engine — Strategy Phases 0–1 · FR-F12, FR-F22 | **C-3**, **C-6**, **C-10** (fuzzy detector off the synced path) | The differentiator competitors cannot answer. Now sits on sound authoring and sound scoring |
| **5** | §P Positions — Strategy Phase 2 · §Q Trust and dispute | **C-5** (freeze at the smaller unit), **C-8** (fact visibility follows positions) | Credit belongs to the role. Trust features need facts to be trustworthy about |
| **6** | §H Continuous performance · §I Calibration (**after D-1**) | **C-14** (one calibration implementation) | Parity features. Calibration blocked on the duplication decision |
| **7** | §M OKR mode · §J AI assistance | **FR-J6 prohibitions enforced before any AI ships** | AI last, deliberately — 9% of HR applications have embedded AI in use and buyers rate shipped AI immature. Build the substrate first |
| **8** | §N India-specific · §L advanced reporting · FR-O7 · Logic ERP (Strategy Phase 3) | **C-11** (one authoritative org total) | Uncontested ground, but it only matters once the core is credible |

**Two sequencing rationales, both carried forward and both still correct:**

1. *From the requirements document:* **authoring precedes automation.** Building the engine first computes precise numbers for goals that are inconsistently defined, unapproved and unlocked — a harder problem to explain to a customer than a delay.
2. *From this consolidation:* **defect remediation precedes authoring**, and **governance protects nothing until FR-O1 exists**, because any authenticated user with a role can read the data regardless of what their company paid for.

**The strategy's own Phase 0 recommendation stands** and maps to Stage 4: prove all four measurement shapes and the crediting model with **zero external dependencies** — no vendor negotiation, no credentials, no firewall — using three in-house metrics spanning three shapes and three attribution strategies. If the engine is right there, Logic ERP becomes a transport problem rather than a modelling one.

---

## 12. Decisions register

**Status:** ✅ settled · 🔵 settled, dissent recorded · 🟠 open, blocking · ⚪ open, non-blocking.

| ID | Legacy | Question | Decision | Status |
|---|---|---|---|---|
| **D-1** | OQ-1 | PMS module vs Frappe HR Performance | **One sellable feature, both ship** (2026-08-23). *Dissent: this switches on 37 doctypes that have never executed against any database, beside a live independent system. **Proposed middle path, no pricing change:** keep the single SKU and the enabled Module Def, but hold the four PMS routes (`/pms-employee`, `/pms-manager`, `/pms-calibration`, `/pms-steering`) behind a site-config flag, default off, until exercised on `dev`.* Blocks §I | 🔵 |
| **D-2** | D2 | Position layer, or denormalised fallback? | **Position layer, in scope.** Fallback FR-P6 retained as a hedge | ✅ |
| **D-3** | D3 | Target path: `KPI`, `Individual Goal`, or both? | **Both.** ⚠ The decision record and the 40-story backlog encode the superseded "KPI first" — see §4.1. Requires FR-A7 and D-13 | ✅ corrected |
| **D-4** | D4 | Metric library HR-configurable or code-defined? | **HR-configurable from the UI** | ✅ |
| **D-5** | D5 | Default scope axis for sales KPIs | **`Sales Person` tree** | ✅ |
| **D-6** | D6 | Must weightages always total 100? | **Per-plan toggle, default ON** | ✅ |
| **D-7** | D7 | Quarterly goal periods inside an annual cycle? | **Yes.** Interacts with cycle freeze — resolved by **C-5** | ✅ |
| **D-8** | D8 | Library per-company or shared? | **Shared catalogue with per-company overrides**, seeded once | ✅ |
| **D-9** | D9 | Attainment bands vs manager rating authority | **Configurable per company, snapshotted at cycle open.** Override permitted with a mandatory reason, audited. Given .45 administrative reliability, **manager-authoritative is the recommended default** | ✅ |
| **D-10** | D1 | Manager with a personal book: one KPI or two? | **Two KPIs**, separate weightages | ✅ |
| **D-11** | D10 | Calibration in scope? | **Yes** — but blocked on D-1 | ✅ |
| **D-12** | OQ-2 | Do bands replace or supplement the manager rating? | Folded into **D-9** | ✅ |
| **D-13** | OQ-3 | Single write path for goal actuals? | **OPEN and blocking Stage 1 and Stage 4.** Recommendation: `Goal Evidence` is the single path, automation and manual alike, distinguished by `evidence_type`; `Goal Progress Update` is **removed**, not unified — it duplicates an approval workflow `Goal Evidence` already has. Check for existing rows before deleting | 🟠 |
| **D-14** | OQ-4 | Is `Goal Check-In` referenced by any live code path? | **OPEN.** One grep settles it. Determines whether FR-H1 promotes or creates | ⚪ |
| **D-15** | OQ-6 | Does Alvoraa sell into the EU within 18 months? | **OPEN, non-blocking.** Build to Art. 26 and 86 regardless — the explainability work is the strongest differentiator independent of the regulation, so the compliance cost is near zero | ⚪ |
| **D-16** | OQ-5 extension | Should "Business + Goals" be a sellable Custom combination? | **OPEN.** Enterprise bundles four features at ₹100–150 PEPM; the greytHR anchor for a performance add-on is ₹35–45. The registry already supports it | ⚪ |
| **D-17** | OQ-7 | Should distribution enforcement ever be available? | **Configuration, default off**, with the evidence surfaced in the admin UI. Refusing outright loses India deals; enabling by default does harm | ✅ |
| **D-18** | OQ-8 | What does FR-O1 gate on, and what does a refused call return? | Gate `goals_api` and goals endpoints in `hr_api` on `goals`; `performance_api` on `performance`; endpoints touching both require **both**. Return a structured upgrade-prompt payload, never a traceback, never an empty success | ✅ |
| **D-19** | OQ-9 | May a downgraded tenant still *read* historical goals and appraisals? | **Recommended: read-only retention.** Past cycles readable, no new authoring, no scoring, no scheduler. An employee's past appraisal is their record, not a feature. Confirm with whoever owns commercial policy | 🟠 |
| **D-20** | new | Which tree governs which object once positions exist? | **Facts and credits resolve through positions as at the fact date; goals and KPIs keep person-based scoping.** Stated once, in FR-P5 | ✅ |

**Blocking now:** D-13 (Stage 1), D-1 (Stage 6), D-19 (Stage 1 scope).

---

## 13. Traceability

### 13.1 Legacy backlog → requirements

`KPIA-n` from `backlog/KPI_AUTOMATION_BACKLOG.md`. `KIN-n` is the live YouTrack issue.

| YouTrack | Story | Requirement |
|---|---|---|
| KIN-10 | KPIA-E1 Metric Library & Data Sources | §9.F (epic) |
| KIN-11 | KPIA-E2 Fact Ingestion, Idempotency & Exceptions | §9.F (epic) |
| KIN-12 | KPIA-E3 Aggregation Engine & Employee Experience | §9.F (epic) |
| KIN-13 | KPIA-E4 Team Roll-Up & Crediting | §9.F (epic) |
| KIN-14 | KPIA-E5 Positions & Effective Dating | §9.P (epic) |
| KIN-15 | KPIA-E6 Logic ERP Integration | §9.F (epic) |
| KIN-16 | KPIA-E7 Governance, Trust & Compliance | §9.Q (epic) |
| KIN-17 | KPIA-1 Define a reusable metric | **FR-F1** |
| KIN-18 | KPIA-2 Preview a metric against live data | **FR-F2** |
| KIN-19 | KPIA-3 Bind a metric with scope filters | **FR-F3** ⚠ widened to goals per D-3 |
| KIN-20 | KPIA-4 Ship a starter metric library | **FR-B8** ⚠ re-scoped — see §4.4 |
| KIN-21 | KPIA-5 Turn automation off per KPI | **FR-F4** |
| KIN-22 | KPIA-6 Nightly ingest as KPI Facts | **FR-F5** |
| KIN-23 | KPIA-7 Re-running a sync never double-counts | **FR-F6** ⚠ add C-10 guard |
| KIN-24 | KPIA-8 Cancelled documents post a reversal | **FR-F7** |
| KIN-25 | KPIA-9 Unmappable owners → exception queue | **FR-F8** |
| KIN-26 | KPIA-10 Resolve an exception by mapping | **FR-F8** |
| KIN-27 | KPIA-11 Observe every sync run | **FR-F9** |
| KIN-28 | KPIA-12 Source unavailable degrades gracefully | **FR-F10** |
| KIN-29 | KPIA-13 Event-sum KPIs total correctly | **FR-F11** |
| KIN-30 | KPIA-14 Ratio KPIs aggregate components | **FR-F11** |
| KIN-31 | KPIA-15 Duration KPIs | **FR-F11** |
| KIN-32 | KPIA-16 Snapshot KPIs | **FR-F11** |
| KIN-33 | KPIA-17 See which documents produced my number | **FR-F14** |
| KIN-34 | KPIA-18 Synced evidence auto-approves | **FR-F15** |
| KIN-35 | KPIA-19 Manager KPI on team activity | **FR-F16** |
| KIN-36 | KPIA-20 Roll up from reports with no KPIs | **FR-F16** |
| KIN-37 | KPIA-21 Roll up through every level | **FR-F16** ⚠ re-estimate per §4.3 |
| KIN-38 | KPIA-22 Honour split credit | **FR-F17** |
| KIN-39 | KPIA-23 Drill into per-person contribution | **FR-F14** |
| KIN-40 | KPIA-24 Roll sales up the Sales Person tree | **FR-F18** |
| KIN-41 | KPIA-25 Company reports read facts | **FR-F19** |
| KIN-42 | KPIA-26 Show quota coverage | **FR-F20** |
| KIN-43 | KPIA-27 Recompute once per run, bottom-up | **FR-F9 / FR-A5** ⚠ same function |
| KIN-44 | KPIA-28 Maintain positions and assignments | **FR-P1** |
| KIN-45 | KPIA-29 Backfill positions | **FR-P2** |
| KIN-46 | KPIA-30 Reorg leaves credit intact | **FR-P3** |
| KIN-47 | KPIA-31 Vacant and acting positions | **FR-P4** |
| KIN-48 | KPIA-32 Confirm Logic ERP surface | **FR-F12** |
| KIN-49 | KPIA-33 Ingest Logic ERP | **FR-F12** |
| KIN-50 | KPIA-34 Store credentials securely | **FR-F13** |
| KIN-51 | KPIA-35 Reconcile ERP totals | **FR-F21** |
| KIN-52 | KPIA-36 Dispute a synced entry | **FR-Q1** |
| KIN-53 | KPIA-37 Freeze KPI values at cycle close | **FR-Q2** ⚠ widened per C-5 |
| KIN-54 | KPIA-38 Flag self-produced metrics | **FR-Q3** |
| KIN-55 | KPIA-39 Scope fact visibility | **FR-Q4** ⚠ add C-8 guard |
| KIN-56 | KPIA-40 Limit personal/commercial data | **FR-Q5** |

**Not yet in YouTrack:** the 16 authoring stories KPIA-41..56 proposed by the requirements document were never created. They map to §9.B, §9.C, §9.E, §9.K and FR-G1. **KPIA-46 is largely already built — re-scope to FR-A1 (§4.2).**

### 13.2 Legacy requirement IDs → requirements

| Legacy | Requirement |
|---|---|
| FR-1..FR-6 (library) | FR-B1, B2, B5, B4, B5, B8 |
| FR-7..FR-9 (goal plan) | FR-C1, C3, C6 |
| FR-10..FR-15 (validation) | FR-A1, D2, D3, D4, D5, D1 |
| FR-16..FR-20 (lifecycle) | FR-E1, E3, E4, E5, E6 |
| FR-21..FR-23 (bulk) | FR-K1, K2, K3 |
| FR-24 (bands) | FR-G1 |
| G1..G13 (gaps) | G1→§9.B · G2→§9.C · **G3, G4 → corrected, §4.2** · G5→FR-E1/E3 · G6→FR-E6 · G7→FR-G1 · G8→§9.K · G9→FR-E4 · G10→FR-M2 · G11→FR-C3 · G12→FR-D6 · G13→§9.I |

### 13.3 Phase and wave mapping

| This document | Strategy phases | Module-access waves | Requirements doc waves |
|---|---|---|---|
| Stage 0 | — | needs Wave 4 *or* FR-O1 | Wave 0 (partly) |
| Stage 1 | — | Wave 5, 6 | Wave 1 |
| Stage 2 | — | — | Wave 3 |
| Stage 3 | — | — | Wave 5 |
| Stage 4 | Phase 0, 1 | — | Wave 2, 4 |
| Stage 5 | Phase 2, 4 | — | — |
| Stage 6 | — | — | — |
| Stage 7 | — | — | — |
| Stage 8 | Phase 3 | Wave 6 | Wave 5 |

---

## 14. Sources

### 14.1 Code

**Read 2026-08-22:** `alvoraa_goals/alvoraa_goals/controllers/kpi.py` · `controllers/goal.py` · `permissions.py` · `scheduled_jobs.py` · `hooks.py` · `alvoraa_goals/doctype/*/*.json` · `alvoraa_portal/alvoraa_portal/performance_api.py` · `hr_api.py` · `goals_api.py` · `hooks.py` · `hrms/hrms/hooks.py` · `hrms/hrms/pms/` · `hrms/hrms/performance_management/doctype/`

**Read 2026-08-23:** `alvoraa_portal/alvoraa_portal/subscription.py` · `module_access.py` · `tenant_api.py` · `hooks.py` · `performance_api.py` (calibration sign-off) · `tests/test_subscription.py`, `test_module_access.py`, `test_calibration_signoff.py` · `deploy/provision_tenant.sh` · `MODULE_ACCESS_STRATEGY.md`

**Verified unchanged 2026-08-23:** every file under `alvoraa_goals/` carries an mtime of 21 August. DEF-1 to DEF-6 stand as written.

### 14.2 Market and evidence

**Enterprise reference** — SAP Learning: [Managing Goal Libraries](https://learning.sap.com/courses/sap-successfactors-performance-and-goals-academy/managing-goal-libraries) · [Configuring the Goal Plan Fields](https://learning.sap.com/learning-journeys/configure-sap-successfactors-performance-and-goals/configuring-the-goal-plan-fields_d5d09fee-f784-466e-afc3-266228505aeb) · [Goal Plan Categories](https://learning.sap.com/learning-journeys/configure-sap-successfactors-performance-and-goals/configuring-the-goal-plan-categories_df629b66-4cd9-494a-b75e-4ff458675b40) · [Goal Plan Permissions](https://learning.sap.com/learning-journeys/configure-sap-successfactors-performance-and-goals/configuring-goal-plan-permissions_edb5ebd4-0531-40b0-b5ba-b776297cfa35). SAP KBAs: [2072202 Metric Lookup Tables](https://userapps.support.sap.com/sap/support/knowledge/en/2072202) · [2457856 Enforcing Min/Max Goals](https://userapps.support.sap.com/sap/support/knowledge/en/2457856). SAP Help: [Goal Plan States](https://help.sap.com/docs/successfactors-performance-and-goals/implementing-and-managing-goal-management/goal-plan-states). Workday: [Hide and Require Goal Fields by Security Group](https://doc.workday.com/admin-guide/en-us/human-capital-management/talent/goals/concept--hide-and-require-goal-fields-by-security-.html). Oracle: [Library Goals](https://docs.oracle.com/en/cloud/saas/talent-management/faugm/how-you-create-library-goals-in-goal-management.html) · [Approval Process](https://docs.oracle.com/en/cloud/saas/talent-management/24d/faugm/approval-process-for-performance-goals.html) · [Validations for Goal Actions](https://docs.oracle.com/en/cloud/saas/talent-management/faugm/validations-for-goal-actions.html) · [Average-Method Rating Calculation](https://docs.oracle.com/en/cloud/saas/talent-management/faipm/how-performance-ratings-using-the-average-method-are-calculated.html) · [Goal Setting Dates, 25D](https://docs.oracle.com/en/cloud/saas/readiness/hcm/25d/tama-25d/25D-talent-mgmt-wn-f40678.htm)

**OKR specialists** — [WorkBoard acquires Quantive](https://www.workboard.com/news/workboard-acquires-quantive) · [WorkBoard Confidence and Predictions](https://www.workboard.com/blog/results-confidence-predictions.php) · [Perdoo KR types](https://www.perdoo.com/resources/blog/different-types-of-key-results-and-when-to-use-them) · [Perdoo goal statuses](https://support.perdoo.com/en/articles/4640875-goal-statuses) · [Profit.co grading approaches](https://www.profit.co/blog/okr-university/what-are-the-approaches-to-grading-okrs-in-profit-co/) · [Profit.co integrations](https://www.profit.co/integrations/) · [Leapsome Goals & OKRs](https://help.leapsome.com/hc/en-us/articles/115003558313-Creating-a-new-goal-OKR) · [Mooncamp Goal Types](https://mooncamp.com/docs/goal-types) · [Microsoft — Viva Goals retirement](https://learn.microsoft.com/en-us/viva/goals/goals-retirement)

**India** — [Keka performance help centre](https://help.keka.com/admin/performance) · [Keka calibration, bell curve, 9-box](https://help.keka.com/hc/en-us/articles/39946630148625-Use-Calibration-in-Keka-for-Fair-Reviews-Bell-Curve-9-Box-Grid-New-Comparison-Tools) · [Keka JIRA integration](https://help.keka.com/hc/en-us/articles/39946748950161-Integrating-JIRA-with-Performance-Module) · [Zoho People KRA settings](https://help.zoho.com/portal/en/kb/people/administrator-guide/performance/settings/articles/kra-settings) · [greytHR PMS](https://www.greythr.com/performance-management-system/) · [greytHR pricing](https://www.greythr.com/pricing/) · [Darwinbox OKRs](https://explore.darwinbox.com/okrs-on-darwinbox) · [HROne performance](https://hrone.cloud/performance-management-software/) · [PeopleStrong goal management](https://www.peoplestrong.com/goal-management/) · [Peoplebox pricing](https://www.peoplebox.ai/pricing/) · [sumHR pricing](https://sumhr.com/pricing-signup/)

**Market and M&A** — [Houlihan Lokey 2025 HCM Year in Review](http://cdn.hl.com/pdf/2026/hcm-year-in-review-2025-mar-2026.pdf) · [Sapient Insights 2025–26 HR Systems Survey](https://sapientinsights.com/sapient-insights-group-releases-the-2025-2026-hr-systems-survey-report/) · [Gartner — 88% no significant AI value](https://www.gartner.com/en/newsroom/press-releases/2025-10-28-gartner-survey-shows-88-percent-of-hr-leaders-say-their-organizations-have-not-realized-significant-business-value-from-ai-tools) · [Lattice acquires Pando](https://www.prnewswire.com/news-releases/lattice-acquires-pando-to-advance-continuous-ai-native-performance-302855048.html) · [HrFlow M&A Q1 2026](https://blog.hrflow.ai/hrtech-m-a-report-q1-2026-2/)

**Evidence** — Locke & Latham (2002) [PDF](https://med.stanford.edu/content/dam/sm/s-spire/documents/PD.locke-and-latham-retrospective_Paper.pdf) · Ordóñez et al. (2009) [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1332071) and [rebuttal](https://journals.aom.org/doi/10.5465/AMP.2009.37008000) · Kluger & DeNisi (1996) [record](https://cris.huji.ac.il/en/publications/the-effects-of-feedback-interventions-on-performance-a-historical/) · Zhou et al. (2024) [PubMed](https://pubmed.ncbi.nlm.nih.gov/38270992/) · Salgado & Moscoso (2019) [full text](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2019.02281/full) · Scullen et al. (2005) [Wiley](https://onlinelibrary.wiley.com/doi/10.1111/j.1744-6570.2005.00361.x) · Siegel et al. (2022) [DOAJ](https://doaj.org/article/a9f8274a727d4d06ac046c146cd7a394) · Silva & Santos (2024) [open access](https://journals-sol.sbc.org.br/index.php/isys/article/view/3885) · [McKinsey 2018](https://www.mckinsey.com/~/media/McKinsey/Business%20Functions/Organization/Our%20Insights/Harnessing%20the%20power%20of%20performance%20management/Harnessing-the-power-of-performance-management.pdf) · [Gallup 2017](https://news.gallup.com/opinion/gallup/219863/give-performance-reviews-actually-inspire-employees.aspx)

**Regulatory** — [EU AI Act Annex III](https://artificialintelligenceact.eu/annex/3/) · [Article 26](https://artificialintelligenceact.eu/article/26/) · [Article 86](https://artificialintelligenceact.eu/article/86/) · [Article 99](https://artificialintelligenceact.eu/article/99/) · [Implementation timeline](https://artificialintelligenceact.eu/implementation-timeline/) · [White & Case — EU AI Omnibus in force](https://www.whitecase.com/insight-alert/eu-ai-omnibus-enters-force-amending-ai-act) · [FPF — emotion recognition prohibition](https://fpf.org/blog/red-lines-under-eu-ai-act-unpacking-the-prohibition-of-emotion-recognition-in-the-workplace-and-education-institutions/) · [AZB — DPDP phased rollout](https://www.azbpartners.com/bank/indias-digital-personal-data-protection-act-phased-rollout-and-key-compliance-milestones/) · [Fisher Phillips — India privacy rules](https://www.fisherphillips.com/en/insights/insights/indias-new-data-privacy-rules-are-here) · [Vaish — consent and employee data](https://www.mondaq.com/india/data-protection/1755320/is-consent-required-to-process-employees-personal-data-under-the-dpdp-act)

### 14.3 Claims that could not be verified

Recorded so nobody repeats them as fact:

- **"Performance drops ~10% when ratings are removed"** (CEB 2016) — press release exists; no sample size, methodology or underlying study is public.
- **"58% of executives say performance management is not an effective use of time"** — attributed to Deloitte c.2015, no traceable primary source. **Do not use.**
- **Kluger & DeNisi's exact "38%"** — the over-one-third finding is established; the precise figure could not be confirmed against the primary text.
- **Scullen et al. (2005) magnitudes** — paper is real and peer-reviewed; full text inaccessible. Do not quote numbers unretrieved.
- **Keka and Zoho People INR pricing** — listicle and partner-page sourced only; neither publishes performance pricing on its own site.
- **Darwinbox and PeopleStrong bell curve / calibration** — absent from their own documentation. Documentation gaps, not confirmed absences.
- **Q1 2026 funding figures** — analyst newsletter, not an audited database.
- **Vendor characterisations in the strategy's competitive table** (SPM, OKR tools, HCM suites) — the source document itself flags these as general market knowledge, not independently verified.

---

*End of specification. Supersedes the five documents listed in §0.1.*
