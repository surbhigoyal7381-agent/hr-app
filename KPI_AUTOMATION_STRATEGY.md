# KPI Automation Strategy — ERP-Sourced Evidence & Credit Roll-Up

**Status:** Approved. All five open decisions resolved 2026-08-18 (see §16)
**Date:** 2026-08-18
**Scope:** `alvoraa_goals` primarily; touches `hrms`, `erpnext`, external ERP (Logic ERP)
**Author:** Engineering

---

## 1. Problem statement

Today every KPI number in the system is typed by a human and approved by another human.
`Goal Evidence` accepts a value and an attachment; `KPI Progress Log` accepts a value and a
comment. The app has no independent knowledge of whether either is true.

Three consequences:

1. **Effort** — every employee re-enters data that already exists in the ERP.
2. **Trust** — appraisal scores rest on self-reported numbers with manual spot checks.
3. **Blind spots** — managers who delegate entirely to their teams have no automatic number
   at all, because nothing in the system rolls a team's activity up to its leader.

This document proposes an ingestion, attribution and roll-up engine that sources KPI actuals
directly from transactional systems, across **all** business domains — not sales alone.

---

## 2. Goals and non-goals

### Goals

- KPI actuals derive from source-of-record transactions, with a document-level audit trail.
- One engine serves sales, marketing, production, inventory, procurement, HR, finance and service.
- A manager's KPI can be measured on their team's activity, whether or not the manager
  transacts personally, and whether or not their reports have KPIs of their own.
- Attribution survives reorganisations, resignations, vacancies and acting appointments.
- Corrections in the source system (returns, cancellations, recounts, payroll reruns) flow
  through without rewriting history.
- Manual entry remains a first-class path for KPIs that cannot or should not be automated.

### Non-goals

- **Not** real-time. Hourly/nightly sync is sufficient for appraisal-grade metrics.
- **Not** a commission or incentive calculation engine. This produces attainment, not payouts.
- **Not** universal automation. Judgement-based KPIs stay manual by design.
- **Not** a replacement for existing manual evidence flows, which continue unchanged.

---

## 3. Design principles

| # | Principle | Rationale |
|---|---|---|
| P1 | **Facts are immutable; corrections are new facts** | Preserves audit trail; matches accounting practice; makes re-sync safe |
| P2 | **Targets cascade down; actuals roll up from facts** | Roll-up computed from child KPI actuals double-counts, breaks on missing children, and diverges on filters |
| P3 | **Fact creation is independent of KPI existence** | Without this, a manager-only KPI over reports who have no KPIs produces nothing |
| P4 | **Ownership ≠ measurement scope** | One KPI is owned by exactly one employee but may be measured over a team |
| P5 | **Credit attaches to a position, not a person** | Reorgs, vacancies and acting managers stop being special cases |
| P6 | **Ratios and durations store components, not results** | Averaging averages and averaging percentages are the two most likely correctness bugs |
| P7 | **The ERP is the system of record** | ERP-sourced evidence auto-approves; humans handle exceptions and disputes, not routine confirmation |
| P8 | **Frappe-first** | Reuse `Sales Person`, `Sales Team`, `Employee` nested set, `Attendance`, `Work Order`, etc. before creating anything |
| P9 | **Source-agnostic core** | ERP specifics live in adapters. No Logic ERP knowledge in `alvoraa_goals` controllers |
| P10 | **Silent truncation is a bug** | Unmapped, unmatched or errored records go to a visible exception queue, never dropped |

---

## 4. Conceptual model

```
 Source systems              Ingestion            Attribution              Consumption
 ─────────────────           ──────────           ─────────────            ────────────
 ERPNext / HRMS   ─┐
 Logic ERP        ─┼─► Adapter ─► KPI Fact ─► Credit Rules ─► KPI Credit ─┬─► KPI actuals
 Ad platforms     ─┤   (per       (immutable,   (direct /      (one row    │   + Goal Evidence
 CSV / SFTP       ─┘    source)    append-only)  rollup /       per        └─► Reconciliation
                                                 split)         creditee)      reports
```

Read it as four questions:

1. **What happened?** → `KPI Fact` — one immutable record per source transaction.
2. **Who gets credit, and how much?** → `KPI Credit` — one row per (fact, position) pair.
3. **Which KPI does that credit belong to?** → matched by metric + scope + period.
4. **What is the number?** → aggregation appropriate to the metric's calculation type.

---

## 5. Measurement shapes

Every KPI reduces to one of four calculation types. The engine implements all four.

| Type | Storage on fact | Aggregation | Existing `progress_mode` | Examples |
|---|---|---|---|---|
| **A · Event Sum** | `value` | `SUM(value)` | `Cumulative` | Revenue, cases sold, units produced, hires closed, collections |
| **B · Snapshot** | `value`, `as_of_date` | latest per scope; `SUM` only if additive | `Absolute` | Stock value, headcount, open positions, dead-stock ageing |
| **C · Ratio** | `numerator`, `denominator` | `SUM(num) / SUM(den)` | `Absolute` | Attrition %, defect PPM, conversion %, fill rate, absenteeism, DSO |
| **D · Duration** | `duration_seconds`, `event_count` | `SUM(dur) / SUM(count)` | `Absolute` | Time-to-hire, PO cycle time, SLA response, order-to-dispatch |

**Critical rule:** types C and D must never be aggregated by averaging child results.
`AVG(percentages)` and `AVG(averages)` produce plausible, wrong numbers — the worst failure
mode, because nothing looks broken. Storing components rather than results makes the correct
aggregation the only expressible one.

`KPI.direction` (`Higher is Better` / `Lower is Better`) already exists and is essential for
C and D, where lower is usually better (defects, cycle time, attrition).

---

## 6. Attribution and crediting

### 6.1 Credit types

A single fact produces one or more credit rows:

| Credit type | Who | When issued |
|---|---|---|
| **Direct** | The position that transacted | Always, if the source names an owner |
| **Rollup** | Every ancestor position up the chosen tree | When an ancestor has a team-scoped KPI on this metric |
| **Split** | Multiple positions at declared weights | Where the source declares shared credit (e.g. ERPNext `Sales Team.allocated_percentage`) |
| **Unattributed** | — | Source names no mappable owner → exception queue |

Credits reference facts; they do not consume them. Company totals are computed from **facts**,
never by summing `KPI.actual_value`.

> **⚠️ Reporting hazard — must be documented for dashboard authors.**
> Summing KPI actuals across an org double-counts by hierarchy depth. A three-level sales org
> would report 3× actual revenue. All company/BU roll-up reports read `KPI Fact`.

### 6.2 Attribution strategies

| Strategy | Mechanism | Typical domains |
|---|---|---|
| **Direct field** | Source doc names a person (`Sales Person`, buyer, recruiter, assignee) | Sales, procurement, recruitment, service |
| **Org unit ownership** | Warehouse / cost centre / workstation / branch → its owning position | Inventory, production, finance |
| **Population scope** | Attribution defines a *filter*, not credit (e.g. "attrition among my department") | HR, ratio metrics generally |
| **Explicit list** | Named member set | Project teams, matrix orgs |

### 6.3 Scope axis

Roll-up does not always follow the HR reporting line.

| Axis | Structure | Use for |
|---|---|---|
| `Reporting` | `Employee.reports_to` — a **nested set** (`lft`/`rgt` maintained via `update_nsm`) | HR, production, finance, default |
| `Sales Person` | ERPNext `Sales Person` tree (`parent_sales_person`) | Sales, where commercial hierarchy ≠ HR hierarchy |
| `Explicit` | Member list on the KPI | Matrix / project structures |

Because `Employee` is a genuine nested set, "all descendants at any depth" is a single indexed
range scan (`lft BETWEEN x AND y`), not recursion. Note that `alvoraa_goals` currently only ever
reads direct `reports_to` — multi-level traversal is new capability, not a config change.

### 6.4 Measurement scope on the KPI

Six configuration fields make both delegation scenarios pure configuration:

| Field | Options |
|---|---|
| `measurement_scope` | `Self` · `Team` · `Team + Self` · `Org Unit` · `Explicit List` |
| `scope_axis` | `Reporting` · `Sales Person` · `Explicit` |
| `scope_depth` | `Direct Reports` · `All Descendants` |
| `scope_org_unit` | Dynamic Link — Warehouse / Cost Center / Department / Workstation |
| `scope_members` | Child table, for `Explicit List` |
| `credit_weight` | Percent, for shared/split team KPIs |

**Scenario A** — manager delegates fully, carries no personal book:
`owner = Sunita`, `measurement_scope = Team`, `scope_depth = All Descendants`.

**Scenario B** — only the manager has a KPI; ERP entries are under reports who have no KPIs:
identical configuration. Works because of **P3** — facts and credits are generated for every
mapped position regardless of whether a KPI exists there.

**Scenario A′** — manager has both a personal book and a team:
Recommended as **two KPIs** with separate weightages (see §14, open decision D1), rather than
one `Team + Self` figure — it lets the two be rated and weighted independently.

---

## 7. Position layer and effective dating

### 7.1 Why

Credit must resolve to *who held the role when the transaction occurred*, not who holds it today.

> Ravi books ₹40L in April–June under Sunita, then moves to Manoj's team on 1 July.
> Sunita must retain the April–June credit.

Frappe's nested set stores only the *current* shape of the org. Resolving roll-up against
"today's tree" silently reassigns historical credit at every reorg — and reorgs mid-appraisal-cycle
are routine.

### 7.2 Design

A light position layer, modelled on standard SPM/HCM practice:

- **`Alvoraa Position`** — a durable role slot (`position_name`, `parent_position`, `company`,
  `department`, `scope_axis` anchor). Nested set on `parent_position`.
- **`Alvoraa Position Assignment`** — `position`, `employee`, `valid_from`, `valid_to`,
  `assignment_type` (`Primary` / `Acting` / `Dotted`). Effective-dated.

Credit resolves: `fact.date` → position holding the source's owner at that date → ancestors of
that position at that date → credit rows.

Benefits: reorgs are reassignments; vacant positions accrue credit that lands with the eventual
occupant or escalates to the parent; acting managers need no special handling; resigned employees'
contributions stay with the right manager.

### 7.3 Cost and the fallback

This is the most expensive element of the proposal — ERPNext/HRMS ship no position management,
so it is new ground. **Fallback if descoped:** denormalise `manager_position_at_date` onto the
fact at creation time. Cheap, solves the reorg case for roll-up, but does not give vacancy,
acting or dotted-line handling. Backfilling the full model later is painful; the denormalised
field is a deliberate partial hedge, not a stepping stone. See open decision D2.

---

## 8. Data model

### 8.1 New doctypes

| Doctype | Purpose | Key fields |
|---|---|---|
| **KPI Metric Definition** | Reusable metric library — the extensibility point | `metric_name`, `calculation_type` (A/B/C/D), `source_system`, `source_doctype`, `value_field`, `numerator_expr`, `denominator_expr`, `duration_from`/`duration_to`, `filters` (JSON), `attribution_strategy`, `owner_field`, `unit`, `direction`, `measured_by_role` |
| **KPI Data Source** | Binds one KPI to one metric + its scope | `kpi`, `metric_definition`, `scope_filters` (JSON), `sync_enabled`, `last_synced_on` |
| **KPI Fact** | Immutable transaction record | `source_system`, `external_reference` (**unique**), `source_doctype`, `source_docname`, `fact_date`, `company`, `metric_definition`, `value`, `numerator`, `denominator`, `duration_seconds`, `event_count`, `owner_position`, `owner_employee`, `dimensions` (JSON), `is_reversal`, `reverses_fact`, `raw_payload` |
| **KPI Credit** | One row per (fact, credited position) | `fact`, `position`, `employee`, `credit_type` (Direct/Rollup/Split), `weight_pct`, `credited_value`, `kpi` (nullable until matched) |
| **Alvoraa Position** | Durable role slot (nested set) | `position_name`, `parent_position`, `company`, `department` |
| **Alvoraa Position Assignment** | Effective-dated person↔position | `position`, `employee`, `valid_from`, `valid_to`, `assignment_type` |
| **KPI Sync Log** | Per-run observability | `source`, `window_from`, `window_to`, `pulled`, `matched`, `unattributed`, `errored`, `duration_ms`, `status`, `error_detail` |
| **KPI Attribution Exception** | Visible failure queue | `fact`, `reason`, `raw_owner_key`, `status`, `resolved_by`, `resolution_note` |

### 8.2 Changes to existing doctypes

| Doctype | Change | Note |
|---|---|---|
| `KPI` | Add the six scope fields (§6.4) | Defaults to `Self` — existing KPIs behave exactly as today |
| `KPI Progress Log` | Add `kpi_fact` link, `is_system_generated` | Distinguishes synced rows from manual ones |
| `Goal Evidence` | Reuse existing `synced_from_external`, `raw_extracted_data`; add `external_reference` | Fields already present and unused — original design anticipated this |
| `Employee` | Custom field `external_owner_key` (fallback where `Sales Person` mapping is unavailable) | Prefer `Sales Person.employee` |

No changes to `Goal Cascade` or `Individual Goal` structure; cascade continues to handle
downward target allocation, which this design deliberately leaves alone (**P2**).

---

## 9. Domain coverage

| Domain | Source | Example KPI | Type | Attribution | Automatable |
|---|---|---|---|---|---|
| Sales | `Sales Invoice` / `Sales Order` | Revenue, cases sold | A | Sales Person | ✅ |
| Sales | `Sales Invoice` + `Payment Entry` | DSO, collection efficiency | C | Sales Person | ✅ |
| Marketing | `Lead`, `Opportunity`, `Campaign` | MQLs, lead→opp conversion | A / C | Campaign owner | ✅ |
| Marketing | Ad platform APIs | CPL, spend, ROAS | A / C | Campaign owner | ⚠️ External |
| Production | `Work Order`, `Job Card` | Units produced, on-time completion | A / C | Workstation → position | ✅ |
| Production | `Quality Inspection`, `Stock Entry` | Defect PPM, scrap %, rework % | C | Line / plant | ✅ |
| Inventory | `Bin`, `Stock Ledger Entry` | Stock value, turns, dead stock | B / C | Warehouse → position | ✅ |
| Inventory | `Stock Reconciliation` | Count accuracy %, shrinkage | C | Warehouse manager | ✅ |
| Inventory | `Delivery Note` vs `Sales Order` | Fill rate, OTIF | C | Warehouse / logistics | ✅ |
| Procurement | `Purchase Order`, `Purchase Invoice` | Cost savings, PO cycle time | A / D | Buyer | ✅ |
| Procurement | `Purchase Receipt` vs PO | Supplier OTIF, GRN rejection % | C | Buyer | ✅ |
| HR | `Job Applicant`, `Job Opening` | Time-to-hire, offer acceptance % | D / C | Recruiter | ✅ |
| HR | `Employee` (`relieving_date`) | Attrition %, regretted attrition | C | HRBP / dept head | ✅ |
| HR | `Attendance`, `Leave Application` | Absenteeism, overtime, leave liability | C / B | Dept head | ✅ |
| HR | `Training Event` | Training coverage, hours per employee | A / C | L&D owner | ✅ |
| Finance | `GL Entry`, `Budget` | Cost centre variance | C | Cost centre owner | ✅ |
| Service | `Issue`, `Maintenance Visit` | SLA adherence, first response | C / D | Assigned agent | ✅ |
| Safety / ESG | none | LTIFR, incidents, energy per unit | A / C | Plant head | ❌ Manual |
| Customer | none | NPS, CSAT | B | Account owner | ⚠️ Survey API |
| Leadership | — | Behaviour, values, mentoring | — | — | ❌ Manual by design |

**Realistic coverage:** ~70% of a typical scorecard from in-house ERPNext/HRMS data,
~15% via external APIs, ~15% correctly remains manual.

---

## 10. Source adapters

All adapters normalise to the same `KPI Fact` shape. `alvoraa_goals` contains no
source-specific logic.

### 10.1 ERPNext / HRMS (native)

Direct ORM queries via `frappe.get_all` with filters from the metric definition.
No credentials, no network, no failure mode beyond a bad query. Covers the majority of §9.

### 10.2 Logic ERP

Logic ERP is typically an on-premise Windows/SQL Server deployment for retail and
distribution, with integration capability varying by edition and version. The adapter accepts
whichever transport their team confirms, in order of preference:

| Option | Pros | Cons |
|---|---|---|
| **1. REST/JSON API** | No schema coupling; survives their upgrades | May not exist in the licensed edition |
| **2. Read-only SQL view on a replica** | Fast, reliable | Couples to their schema — insist on a **view** we specify (`vw_hr_kpi_facts`), never base tables |
| **3. Scheduled export to SFTP** | Works behind a corporate firewall with no inbound path | Latency; file-handling edge cases |

**Network posture:** Frappe polls **outbound** in all three options. This avoids requesting an
inbound firewall rule from customer IT, which is frequently the difference between a two-week
and a two-month integration.

**Open questions for Logic ERP's team** — these gate the estimate, not the design:
API availability in the licensed edition; cloud vs on-premise; how salespersons/operators are
keyed; how returns and credit notes are represented; whether a sandbox exists; rate limits.

### 10.3 External APIs

Ad platforms, survey tools. Same adapter interface. Credentials in `site_config.json` or
`Password` fieldtype — never plaintext in a doctype.

### 10.4 Manual and file

Existing manual evidence path, unchanged, plus a CSV import that lands in `KPI Fact` for
sources with no API at all (e.g. safety incident logs).

---

## 11. Sync orchestration

| Job | Frequency | Window | Purpose |
|---|---|---|---|
| Incremental | Hourly | Last 24h, overlapping | Fresh numbers during the day |
| Reconcile | Nightly | Full open cycle period | Catches backdated entries and source-side edits |
| Snapshot | Nightly | Point-in-time | Type-B metrics |

**Idempotency.** `external_reference` carries a unique index. Sync is *upsert by that key*, so
overlapping windows, re-runs and manual replays are safe. The existing fuzzy
`duplicate_detector` stays on the manual path only — machine data uses an exact key.

**Restatement.** Source cancellations/amendments post a **compensating fact** (`is_reversal = 1`,
`reverses_fact` set) rather than editing the original. The progress log reads as a ledger and any
manager can see why a number moved.

**Recompute discipline.** Do **not** cascade per fact. Once per sync run: collect affected
positions → resolve distinct ancestors in one `lft`/`rgt` pass → recompute each affected KPI
exactly once, bottom-up. Per-fact cascading is O(facts × depth) and will not survive month-end.

**Failure posture.** ERP unreachable → KPI holds its last known value. Never zero, never partial.
Every run writes a `KPI Sync Log` row whether it succeeds or fails.

---

## 12. Trust, approval and governance

| Path | Validation status | Rationale |
|---|---|---|
| ERP-sourced | `Approved`, `approved_by = "System"` | The ERP is the system of record (**P7**); manager confirmation adds no signal |
| Manual entry | `Pending` → manager review | Unchanged from today |
| Unattributed | Exception queue → HR | Never silently dropped (**P10**) |

- **Dispute path.** Employees can flag a synced row for HR review; they cannot edit it.
  Necessary in Scenario B, where reports have no KPI yet their transactions drive a manager's score.
- **Cycle freeze.** On appraisal cycle close, syncing stops for that period and the value is
  snapshotted. Without this, a January credit note reopens a settled appraisal.
- **Coverage ratio.** At cascade time, display allocated child targets ÷ manager target. Under
  100% means the manager is exposed; well over means sandbagging. Industry-standard practice
  (*quota over-assignment*, typically targeted 110–130%). The system must **not** force equality —
  over-assignment is deliberate.
- **Measured-by separation.** `KPI Metric Definition.measured_by_role` flags metrics where the
  scored person also produces the data (e.g. stock accuracy measured by the person counting).
  Surfaces self-scoring at design time. Cheap now; expensive once appraisals depend on it.

---

## 13. Non-functional analysis

| Dimension | Assessment |
|---|---|
| **Performance** | *Improves* where aggregation happens at source. Risks: N+1 on per-fact recompute (mitigated §11), and `KPI Credit` row growth (a 3-deep org triples rows per fact — indexed on `(position, kpi, fact_date)`, partitioned by cycle if needed). |
| **Security** | *Degrades unless handled.* New external credentials at rest, new inbound data path, background jobs writing as Administrator. Mitigations: credentials in `site_config`/`Password` fields; `ignore_permissions` scoped to the single KPI being written; outbound-only network posture. |
| **Reliability** | *Degrades* — new external dependency. Mitigated by hold-last-value, full sync logging, per-source circuit breaking, and idempotent replay. |
| **Scalability** | Aggregate-at-source is O(employees), not O(transactions). Multi-company means one connection **per company**, not one global. Nested-set roll-up is O(log n) per lookup. |
| **Maintainability** | *Improves* — the metric library makes new KPIs configuration, not code. *Would degrade sharply* if source specifics leak out of adapters (**P9**). |
| **Data integrity** | The crux. Addressed by unique `external_reference`, immutable facts, compensating reversals, effective-dated attribution, and cycle freeze. |
| **Compliance / privacy** | Customer names and invoice values entering an HR system widens PII scope. Aggregates live on the KPI; document detail stays in `KPI Fact` with restricted read. Employees must not see peers' facts; managers see their subtree only. |

---

## 14. Known failure modes

| Risk | Severity | Mitigation |
|---|---|---|
| Dashboard sums KPI actuals → double-counts by depth | **High** — plausible wrong numbers | Documented rule; reporting reads facts; add a guard view |
| Ratio/duration KPIs averaged instead of component-summed | **High** — silent | Components stored, results never; unit tests per calculation type |
| Reorg reassigns historical credit | **High** | Position layer (§7); fallback denormalisation |
| Unmapped ERP owner keys dropped silently | Medium | Exception queue; sync log counts |
| ERP-side edits not reflected | Medium | Nightly full reconcile of open period |
| Goodhart / metric gaming | Medium | `measured_by_role` separation; manual KPIs retained |
| Logic ERP has no usable integration surface | Medium | Three transport options; SFTP fallback always viable |
| Credit row volume at scale | Low–Medium | Indexing; cycle-based archival |

---

## 15. Phasing

| Phase | Scope | Exit criteria |
|---|---|---|
| **0 · Engine proof** | `KPI Fact`, `KPI Credit`, `KPI Metric Definition`, `KPI Data Source`, sync log, exception queue. Three metrics spanning three shapes and three attribution strategies, all from **in-house** data: Revenue (A, direct), Absenteeism % (C, population), Stock value (B, org unit). Self-scope only. **Per D3, both `KPI` and `Individual Goal` are targets from the start** | The three metrics update nightly from ERPNext/HRMS with correct aggregation per shape, on **both** a KPI and an Individual Goal; re-run produces identical results |
| **1 · Roll-up** | Scope fields on KPI, nested-set traversal, rollup + split credit, batched bottom-up recompute, drill-down UI, coverage ratio | Scenarios A and B both produce correct manager numbers at 3+ levels with no double-counting |
| **2 · Positions** | `Alvoraa Position`, `Alvoraa Position Assignment`, effective-dated credit resolution, backfill from current `reports_to` | A simulated mid-cycle reorg leaves historical credit unchanged |
| **3 · Logic ERP** | Adapter for the confirmed transport, credential management, reconciliation report | Logic ERP totals reconcile to KPI totals within tolerance |
| **4 · Hardening** | Restatement/reversal at scale, dispute flow, cycle freeze, external API adapters, remaining domains | Cycle close is immutable; disputes auditable |

**Phasing note (D3):** `Individual Goal` is no longer deferred to Phase 4. It is a Phase 0 target
alongside `KPI`, which widens Phase 0 and requires the field gap in §16.1 to be closed first.

**Phase 0 is the recommendation to start.** It proves all four measurement shapes and the
crediting model with **zero external dependencies** — no vendor negotiation, no credentials, no
firewall. If the engine is right there, Logic ERP becomes a transport problem rather than a
modelling one. Phases 1 and 2 can be reordered only if D2 resolves to the fallback.

---

## 16. Decisions — RESOLVED 2026-08-18

All five are decided. Nothing in this document is now waiting on an answer.

| # | Decision | Resolved | Note |
|---|---|---|---|
| **D1** | Manager with own book: one `Team + Self` KPI, or two? | **Two KPIs**, each with its own weightage | As recommended. Lets personal delivery and team delivery be rated and weighted independently |
| **D2** | Effective-dated position layer, or the denormalised fallback? | **Position layer, in scope** | As recommended. `Alvoraa Position` → **`Alvoraa Position`** and `Alvoraa Position Assignment`. Reorgs, vacancies, acting and dotted-line all become ordinary cases |
| **D3** | Target path: `KPI`, `Individual Goal`, or both? | **Both** | *Differs from the recommendation*, which was KPI first. See §16.1 |
| **D4** | Metric library HR-configurable, or code-defined? | **HR-configurable from the UI** | As recommended. A new metric must not require a developer |
| **D5** | Default scope axis for sales KPIs | **Sales Person tree** | As recommended. Commercial hierarchy diverges from the HR chart in multi-tier distribution |

### 16.1 What D3 changes

The original phasing put `KPI` first because it already carries `progress_mode`, `direction`,
`weightage` and `attainment_pct`, and deferred `Individual Goal` to Phase 4. Building both from
the start is a wider Phase 0, and three things follow:

1. **Two consumption paths, one engine.** Facts and credits stay shared; only the final write
   differs — `KPI Progress Log` for KPIs, `Goal Evidence` for goals. The aggregation, crediting
   and reversal logic must not be duplicated per path.
2. **`Individual Goal` lacks the fields `KPI` has.** It has `progress_mode` and `actual_progress`
   but no `direction` and no `attainment_pct`. Either those are added, or attainment is computed
   at read time for goals. Decide before Phase 0 starts.
3. **Roll-up applies to goals too.** The scope fields in §6.4 were specified for `KPI`. Under D3
   they belong on `Individual Goal` as well, which already has `parent_goal` and `goal_cascade` —
   so the tree exists, but the *measurement* scope is still a new concept there.

Phase 0's exit criteria widen accordingly: the three proof metrics must land correctly on both a
`KPI` and an `Individual Goal`.

---

## 17. Competitive positioning

| Capability | SPM (Xactly, Varicent, Anaplan) | OKR tools (Lattice, Betterworks, Quantive) | HCM suites | **Alvoraa (proposed)** |
|---|---|---|---|---|
| Manager with no personal book | ✅ Rollup credit | ⚠️ Weighted avg of children | ⚠️ Manual | ✅ |
| Reports without KPIs (Scenario B) | ✅ | ❌ Cannot express | ⚠️ Manual | ✅ |
| Roll-up from source facts | ✅ | ❌ Child rollup | ⚠️ Imported numbers | ✅ |
| Effective-dated attribution | ✅ | ❌ | ✅ Workday, ⚠️ others | ✅ Phase 2 |
| Ratio aggregation correctness | ✅ | ❌ Common bug | ⚠️ Varies | ✅ |
| Restatement / clawback | ✅ | ❌ | ❌ | ✅ |
| Multi-domain beyond sales | ❌ Sales only | ✅ | ✅ | ✅ |
| Feeds appraisal, not payout | ❌ | ✅ | ✅ | ✅ |

*Vendor characterisations are from general market knowledge and are not independently verified;
they should be re-checked before external use.*

The gap this occupies: SPM engines credit brilliantly but only for sales and only for
commissions. OKR and HCM tools span all domains but treat actuals as an imported number with no
audit trail. **Credit-engine-grade attribution applied across every domain, feeding appraisal
scores with document-level evidence** sits between the two categories.

Honest caveat: SPM-grade crediting is the expensive part of this build. Worth an explicit
decision on whether that is the differentiator being funded, or whether v1 ships simpler
roll-up and earns the right to it later.

---

## 18. Approval

Per the change process, this document is **step 2 (propose strategy)**. No code has been written.

**Approved 2026-08-18**, with all five decisions resolved (§16). Next step is the Phase 0 design
at doctype-field and function-signature level, for a second review before code.

Open item carried forward from §16.1: `Individual Goal` has no `direction` or `attainment_pct`.
Decide whether to add them or compute attainment at read time, before Phase 0 begins.
