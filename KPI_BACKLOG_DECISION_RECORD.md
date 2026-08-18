# KPI Automation + Authoring Backlog — Decision Record

**Date:** 2026-08-18
**Scope:** KIN project (Kinexus) YouTrack backlog — KPIA-1..40 (measurement, created) and KPIA-41..56 (authoring, pending)
**Inputs:** `KPI_AUTOMATION_STRATEGY.md`, `OBJECTIVES_KPI_REQUIREMENTS.md`, `CLAUDE.md`

---

## 1. Decisions carried from the strategy document (already applied to KPIA-1..40)

| # | Decision | Resolution |
|---|---|---|
| D1 | Manager with own book: one `Team + Self` KPI or two? | **Two KPIs**, separate weightages |
| D2 | Position layer in scope, or denormalised fallback? | **In scope**, Phase 2 |
| D3 | Target path: `KPI.progress_log`, `Individual Goal`, or both? | **`KPI` first**; Individual Goal in Phase 4 |
| D4 | Metric library HR-configurable or developer-defined? | **HR-configurable from the UI** |
| D5 | Default scope axis for sales KPIs | **`Sales Person` tree** |

## 2. Decisions taken this session (authoring layer)

| # | Question | Resolution | Affects |
|---|---|---|---|
| D6 | Must weightages always total 100? (§11 Q5) | **Per-plan toggle** on Goal Plan Template, default ON. Customers running un-normalised weights are not broken on upgrade. | KPIA-46 (Critical), KPIA-44 |
| D7 | Quarterly goal periods inside an annual cycle? (§11 Q2) | **Yes — real customer practice.** Goal Plan defines periods independent of the appraisal cycle; KPIs roll up across periods within one annual review. | KPIA-44, interacts with KPIA-37 cycle freeze |
| D8 | Library per-company or shared? (§11 Q3) | **Shared catalogue with per-company overrides.** Starter library seeded once, not per company. | KPIA-41, KPIA-42, KPIA-4 (merged) |
| D9 | Attainment bands vs manager rating authority? (§11 Q4) | **Configurable per company.** See §3 below. | KPIA-55 |
| D10 | Calibration (G13) in scope? (§11 Q1) | **STILL OPEN.** Working assumption: out of scope, treated as a separate module. Not written as a story until confirmed. | — |

## 3. D9 in detail — rating authority

Resolved across three sub-decisions:

1. **Configurable, not fixed.** The company chooses whether the attainment band table or the
   manager's rating is authoritative. Per CLAUDE.md §4, organisation-level config belongs in
   Frappe Global Defaults / HR Settings or an existing settings singleton — **not** a new doctype
   and not hardcoded. Exact target singleton to be confirmed against the repo.
2. **Scoped per company**, not per tenant. Rules out a plain `HR Settings` global singleton as the
   sole home; needs a company dimension. Consistent with the CXO / HR Manager / Employee persona
   model and the multi-company isolation NFR.
3. **Mode is snapshotted onto the appraisal cycle at cycle open.** Changing the org setting affects
   future cycles only. Prevents a mid-cycle flip from silently re-deriving ratings on appraisals
   already computed — the stale-config / data-integrity hazard in CLAUDE.md §2.
4. **Manager override permitted in authoritative mode, with a mandatory reason, audited.**
   Satisfies BP8 (never let automation finalise a material outcome without human sign-off).
5. **Audit requirement.** The KPI records both the band applied (FR-24) *and* the authority mode in
   force, so the derivation is reconstructable in a grievance.

## 4. Structural decisions for the YouTrack backlog

| Area | Decision | Note |
|---|---|---|
| Hierarchy | Epic issue → Story subtask → Sub-task | 3 levels; KIN-10..16 are the 7 measurement epics |
| Priority mapping | Critical→Critical, High→Major, Medium→Normal | KIN has no Show-stopper/Minor usage |
| Type field | None — KIN has no `Type` custom field | Nothing is marked "User Story" |
| Story points | **BLOCKED** — no `Story points` field exists in KIN; `Estimation` is a time period, not points | Points currently recorded in issue description text only |
| Tags | **BLOCKED** — YouTrack MCP cannot create tags; `manage_issue_tags` rejects non-existent tags | No `points-N` / `phase-N` tags applied |
| Sequencing | Authoring precedes automation (requirements §10) | Contradicts the phase order baked into KPIA-1..40; existing stories need resequencing |

## 5. Required changes to the existing 40 stories

| Story | Change | Source |
|---|---|---|
| KPIA-4 | **Merge into KPIA-41.** Starter library must not be built twice | Requirements §9, FR-6 |
| KPIA-46 | Pull ahead of all other work — live scoring defect, not an enhancement | Requirements §9, §10 Wave 0 |
| All | Re-tag phases to the Wave model in §10 rather than the original Phase 0-4 order | Requirements §10 |
| KPIA-37 | Revisit against D7 — cycle freeze now interacts with independent goal periods | This session |

## 6. Outstanding blockers

1. **Repo access.** `C:\Surbhi-Git\hr-app` is not reachable from this cloud session. Verified by
   filesystem search — no `hr-app`, `alvoraa_goals` or `Surbhi-Git` anywhere, no device bridge, no
   Windows mount. Sub-tasks naming controllers, hooks, fields and callers cannot be written
   without it, and CLAUDE.md §2 requires grepping all callers before proposing any change.
2. **Story points field** must be created in YouTrack admin (integer type, attached to KIN).
3. **§11 Q1 (calibration)** unanswered.
