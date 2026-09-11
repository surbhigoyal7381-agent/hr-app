# Non-functional budget — Alvora HR

**Version 0.1 · 24 August 2026 · Status: DRAFT — needs a 30-minute agreement session**
Tenant profile: **50–1,000 employees. Security-conscious buyer.** Frappe stack.

These are the numbers the engineer builds to, the test engineer asserts against, and
the reviewer checks. Two honesty rules:

1. **Every number here is a target derived from market practice and this product's own
   documents. None is a measurement.** Anything not yet observed on our own system is
   marked `[TARGET]`; anything I inferred rather than sourced is `[ASSUMPTION]`.
2. **A slice that cannot meet a number does not silently miss it.** It gets a dated,
   named exception recorded in its implementation notes.

**The standards and laws behind these numbers live in
`security-compliance-baseline.md`.** This file carries the *targets*; that file carries
the *obligations* and who must confirm them. Where they disagree, the baseline wins and
this file gets corrected.

**Where the market bar sits for this buyer.** A 50–1,000-employee company with a
security reviewer in the loop is not asking for hyperscale. They are asking four
questions: *can my competitor's employee see my data* (isolation), *can you prove who
did what* (audit), *what happens when you are breached* (response), and *how do I get
my data out and deleted* (portability and retention). Every number below should be
readable as an answer to one of those. **Design for 10× current scale, not 1000×** — a
bootstrapped company that gold-plates for hyperscale dies before it needs to.

---

## 1 · Volume — design and test to these

The single most important table here, because without it "it scales" is untestable.

| Dimension | Small tenant | Typical | Large | Design for | Notes |
|---|---|---|---|---|---|
| Employees per tenant | 50 | 250 | 1,000 | **1,000, with headroom to 2,000** | The project's own PRD targets 100–2,000 and load-tests at 2,000. Build for 1,000; prove at 2,000 so a large deal is not a re-architecture |
| Goals + KPIs per employee per cycle | 5 | 8 | 15 | **8 median, 20 ceiling** | The SRS load-test profile is 2,000 × 8 |
| Goal/KPI library templates per tenant | 50 | 300 | 1,000 | **1,000** | SAP's published ceiling per library, and FR-B9's stated bar |
| Concurrent users at peak | 15 | 80 | 300 | **300** | `[ASSUMPTION]` ~30% of headcount during goal-setting week and appraisal week. **Peak is not the average day** — goal-setting open, cycle close and appraisal release are the three load events |
| Bulk assignment in one operation | 100 | 500 | 1,000 | **500 in one background job (FR-K4); 1,000 must not fail, only queue** | |
| KPI Facts ingested per tenant per day | 200 | 2,000 | 20,000 | **20,000/day sustained, 50,000 burst** | `[ASSUMPTION]` Sales/ops transaction volume, not headcount, drives this. **Re-derive from a real customer's ERP before Stage 4 ships** |
| KPI Facts retained | — | — | — | **36 months online + archive** | Append-only. This is the biggest table in the system; partition it |
| Appraisal cycles concurrently open | 1 | 2 | 4 | **4** | Annual + probation + project + BU-specific (FR-C5) |

**Rule:** no test may claim scale on three seeded rows. Seed to the "Typical" column at
minimum, and to "Design for" on anything in the measurement engine or bulk path.

---

## 2 · Performance

| What | Budget | How it is proven |
|---|---|---|
| Core HR/manager view, broadband, p95 | **≤ 1.5 s** | Timed test at Typical volume |
| Employee self-service action, p95 | **≤ 1.5 s** | |
| Employee-facing surface on a 3G phone profile, p95 | **≤ 2.5 s**; skeleton within 300 ms | Frontline users are phone-first and often on poor connectivity |
| Whitelisted API call, p95 | **≤ 500 ms** | Timed integration test |
| Goal creation screen with a 1,000-entry library | **< 1 s** | FR-B9's own bar. Paginate; never load the tree eagerly |
| Report / dashboard | **≤ 3 s**, or it runs in the background with a visible progress state | |
| Evidence-pack / audit export | **< 30 s**, or async with notification | |
| Bulk assignment, 500 employees | **completes in one background job**, per-employee outcomes, no timeout | FR-K3/K4 |
| Period / cycle close, 1,000 employees | **< 10 min**; concurrent tenant closes queued fairly | Scaled from the PRD's 2,000-employee/<10-min figure `[TARGET]` |
| Nightly sync + recompute window | **completes within the window with 50% headroom** | FR-F9: recompute affected items **once, bottom-up** |
| Queries per request | **bounded and asserted** — no query inside a loop | Query-count assertion in test. This is the cheapest scale defence you have |
| Recalculation | **writes only on change**, commits in batches | FR-A5. A quiet tenant must not generate 28,800 pointless audit rows a day |
| Aggregation complexity | Aggregate-at-source **O(employees), not O(transactions)**; nested-set roll-up **O(log n)** per lookup | Stated in the SRS; assert it in a test, don't assume it |
| Anything > 2 s of work | **Background job, never a blocking request** | Review gate |

**Frappe-specific traps to test for, not hope about:** N+1 on child tables; unindexed
`Link` fields used as filters; `frappe.get_doc` in a loop where `get_all` would do;
list views without a page limit; report queries that re-derive what a stored field
already holds.

---

## 3 · Availability, reliability and recovery

| What | Budget |
|---|---|
| Platform availability | **99.5% monthly at MVP → 99.9% at GA** for employee-facing paths `[TARGET]` |
| Employee-facing paths during a cycle window | **99.9% monthly** — goal-setting week and appraisal release are the moments an outage is remembered |
| **RPO** | **≤ 1 hour** |
| **RTO** | **≤ 4 hours** |
| Restore drill | **Executed and documented at least quarterly.** A backup you have never restored is a hope, not a control. This is also the single most common security-questionnaire item we will be asked to evidence |
| Planned maintenance notice | **≥ 72 hours**, status page + in-app banner, EN/HI parity |
| Rollback | **≤ 15 min**, feature-flagged where possible — no deploy required to disable a feature |

**Every external call and every background job** gets: a timeout, a bounded retry, and
a **defined end state** — retry / fall back / escalate to a human queue / safe-stop.
Specifically for this product:

- **An unreachable source holds the last known value and never guesses** (FR-F10).
  Never zero: zero is indistinguishable from poor performance, and it lands on
  someone's appraisal.
- **Re-running any sync window never double-counts** (FR-F6). Idempotency key per
  source document. Fuzzy duplicate detection must **never** run on synced facts.
- **Cancelled or amended source documents post a reversal, never an edit** (FR-F7).
  The progress log reads as a ledger.
- **Bulk operations are transactional per row** with per-row outcomes. One bad row must
  not lose the other 799, and must not be lost silently either (FR-K3).
- **Per-source circuit breaking.** One misbehaving integration must not be able to
  force a customer to abandon automation (FR-F4 gives them the per-item off switch).

---

## 4 · Security — the section this buyer reads first

### Commercial baseline

| Control | Position | Why |
|---|---|---|
| **ISO/IEC 27001:2022** (ISMS) | `TODO — decide, and set a date` | Indian and EU buyers typically ask for this one |
| **ISO/IEC 27701:2025** (privacy, now a **standalone** PIMS) | Target after 27001 | Answers "how do you manage *privacy*", which is the question an HR-data buyer actually asks. Map DPDP and GDPR onto it once instead of answering each questionnaire from scratch |
| **SOC 2 Type II** (AICPA TSC — Security, Confidentiality, Privacy; Availability if we commit to an SLA) | `TODO — decide vs/alongside ISO` | US-facing buyers typically ask for this one. **Type II** is what reviewers want; Type I buys little. Evidence is retrospective, so **deciding late costs a year** |
| **ISO/IEC 27017 / 27018** | Adopt as guidance | The shared-responsibility checklist for a customer's cloud reviewer |
| **NIST CSF 2.0** | Adopt as the internal map | Free. Its **Govern** function is the one small companies skip and auditors ask about |
| **OWASP ASVS 5.0** (released 30 May 2025) | **Adopt now. Target Level 2** — the level intended for applications handling sensitive data, which HR data plainly is | Turn the relevant requirements into test cases, not a spreadsheet. *(5.0 restructured the standard — confirm level definitions against the 5.0 document, not 4.0's.)* |
| **VAPT / third-party penetration test** | **Annually, plus before any major release that changes the authorisation model** | Report summary shareable under NDA |
| **Security questionnaire pack** | Maintained, versioned, owned by a named person | Answering these ad hoc is what turns a two-week review into two months |
| **Sub-processor register** | Published and tenant-visible; customers notified of changes | DPDP and standard DPA practice |
| **Vulnerability response SLA** | Critical ≤ 7 days, High ≤ 30, Medium ≤ 90, from confirmation `[ASSUMPTION — agree and publish]` | |

### Application security — non-negotiable

- **Permissions enforced server side, on every path.** A hidden button is not a
  permission. Validation runs in the controller so that **the portal, the desk, the
  REST API and bulk import are all guarded by the same rule** (FR-D1) — four entry
  paths, one policy.
- **Entitlement enforced server side on every endpoint** (FR-O1), fail-closed on module
  access, propagation ≤ 5 minutes. A priced feature that the API does not enforce is
  not priced.
- **Row-level scoping on every new object.** Employees never see peers' facts; managers
  see their subtree only (FR-Q4).
- **`ignore_permissions` is a budget that only goes down.** Every use is scoped to the
  single record being written and carries a comment justifying it. **Record the current
  count in CI and fail the build if it rises.** The project's own notes report ~169
  uses `[UNVERIFIED — count it, then hold the line]`.
- **Every `@frappe.whitelist()` endpoint**: validate and type-check every argument;
  check the caller's rights on the **specific document**; never let a client-supplied
  string select a doctype, field, file path or code path.
- **Parameterised queries only.** String-built SQL is a defect, not a style preference.
- **Secrets** from environment/site config. Integration credentials **encrypted
  per-company, never logged, and never present in a traceback** (FR-F13) — that last
  one needs its own explicit test, because it is the one that leaks.
- **Outbound polling only.** The customer is never asked for an inbound firewall rule.
- **Authentication:** MFA available on all accounts; **SAML/OIDC SSO and SCIM
  provisioning** for the upper plans `[TODO — confirm whether built]`. Session timeout,
  and immediate access revocation on role change or exit — assert the ex-employee case
  in a test.
- **Supply chain:** dependency vulnerability scan in CI, pinned dependencies, and an
  SBOM you can hand a reviewer. `TODO — name the tool and cadence.`

### India-specific infrastructure duties — CERT-In Directions, 28 April 2022

Routinely missed, and they constrain **architecture**, not policy. *Verified 24 Aug
2026; ⚠ confirm current text with counsel.*

| Duty | Budget |
|---|---|
| **Incident reporting to CERT-In** | **Within 6 hours of becoming aware**, for the specified incident categories (breach, unauthorised access, ransomware, defacement and others). From *awareness*, not resolution |
| **ICT log retention and residency** | **Rolling 180 days minimum, stored within Indian jurisdiction.** Default cloud retention will not satisfy this — configure it, and **assert it in the deploy pipeline** |
| **Time synchronisation** | All systems synced to **NIC or STQC NTP** (or a traceable equivalent), with drift surfaced on an admin health page. Forensic timestamps are worthless if clocks disagree |
| **Point of contact** | A named person registered with CERT-In, plus a backup |

**Design consequence, and it is the important one:** the **6-hour clock is tighter than
the 72-hour DPDP and GDPR clocks, so it sets the on-call design.** One breach workbench
runs all three clocks; the affected-record query must be runnable in minutes, not
reconstructed by hand. **Drill it before GA.**

### The CI gates that make the above real

These are the difference between a security posture and a security paragraph:

1. **Permission test suite is blocking in CI** and covers **every** DocType, including
   the negative cases (`test_permissions.py` extended to each new doctype — stated in
   the SRS as blocking; make sure it is).
2. **Cross-tenant isolation suite** — a seeded two-tenant database, every endpoint
   probed cross-tenant; **any success returning foreign data fails the build.**
3. **`ignore_permissions` counter** — fails on increase.
4. **Secret/PII-in-logs scanner** on test output and on tracebacks.

> 🔴 **Standing item until closed.** The project's notes report that Employee-role users
> can read and write colleagues' appraisals, including `manager_internal_notes` and
> `potential_rating`, with no row-scoping on `Appraisal Extension`. `[UNVERIFIED — read
> the repo]`. If true, this is a **Blocker**, not a backlog item: it is exactly the
> failure a security-conscious buyer's reviewer probes for, and it contradicts the
> product's core claim of fairness and defensibility. **Verify it before the next demo,
> and write the failing test before the fix.**

---

## 5 · Privacy — stricter than the rest, because this is HR

**Regulatory position.** India's DPDP Act 2023 with the **DPDP Rules 2025, notified
14 November 2025**, phasing in over ~18 months — Data Fiduciary obligations becoming
fully effective **around May 2027**. Breach handling: **immediate intimation to affected
Data Principals and the Board, then a detailed report to the Board within 72 hours**.
*Confirm the exact phase dates, our Data Fiduciary vs processor position, and any
Significant Data Fiduciary threshold with counsel — no agent on this team is a lawyer.*

| Requirement | Budget |
|---|---|
| Personal data in logs, error messages, telemetry, analytics events, tracebacks | **Never.** Log the document name and let an authorised human open it |
| Sensitive identifiers (national ID, bank, health, background checks) | Read only on a need-to-know path; **never** in list views, default exports or notifications. Field-level encryption at rest, with key rotation and 100% access audit |
| Commercial detail pulled in by the measurement engine | **Minimum necessary** (FR-Q5). Aggregates on the item; document detail in `KPI Fact` behind restricted read. Customer names and invoice values entering an HR system widens our PII scope — that is a design decision, not a side effect |
| Test fixtures | **Synthetic and anonymised. Never a copy of production.** No exceptions |
| Retention — operational HR records | 36 months online + archive `[ASSUMPTION — counsel]` |
| Retention — selection/appraisal decisions and their audit trail | Long, and **longer than the erasure request** — a rating must remain defensible years later. This tension between erasure and auditability is real: resolve it explicitly with counsel and write the answer down |
| Retention — AI action logs | **≥ 12 months (DPDP), build to 18** — the backlog's own note is "build to the longer" |
| Erasure and portability | A working, tested path — not a manual database operation. Reviewers ask for a demonstration |
| **DPIA** | **A gate before the measurement engine (Stage 4) ships** (FR-Q5 AC5), not a document produced afterwards |
| **Automated decisions about people** | Where a rating drives pay, promotion or exit, the person can obtain **human intervention, state their case, and contest it**. In this product that is satisfied by: **FR-J4** (AI never rates), a **named accountable human on every rating**, the **replayable derivation** (FR-G4), the **plain-language explanation** (FR-G5), and a routed **human-review request**. Treat these as one control, not five features |
| Data residency | India default `[ASSUMPTION — confirm]` |
| Breach runbook | Written, owned, and **drilled at least once before GA**. The 72-hour clock is not the time to discover who writes the notice |

---

## 6 · AI — where the guardrails are structural

Alvora's AI is **assistive and auditable, never decisive.**

| Rule | Enforcement |
|---|---|
| **AI never proposes or sets a rating** (FR-J4) | Structural — the model has no tool that writes a rating. Not a sentence in a prompt |
| **No emotion, voice or facial analysis** (FR-J6) | Architecturally impossible. The EU AI Act's Article 5 prohibitions — which include emotion inference in the workplace — have been **in force since 2 February 2025**. This constrains us today |
| **AI narrative comes strictly from that employee's own record** (FR-J3) | Sparse data produces a short draft, never padding. Test for fabricated specifics |
| **Every AI action logged** with inputs, prompt version, model version and the human decision that followed (FR-J5) | Retention ≥ 12 months, build to 18 |
| **An affected person can obtain an explanation of the AI's role** (FR-J7) | Satisfied jointly by the plain-language rating derivation (FR-G5) and the AI log |
| **Untrusted text is data, never instruction** | Employee free text, uploaded policies, candidate and customer names, ERP description fields. Isolate it; it must never select a tool or code path. Seeded injection tests on every agent that reads user text |
| **Sensitive identifiers never enter a prompt** | Redact at the boundary, with a test asserting on the captured payload |
| **Deterministic maths stays deterministic** | Attainment, weighted averages, balances and payouts are computed by code. The model may **explain** a number; it never produces one |
| **Every AI path has a non-AI fallback and a per-feature kill switch** | The product must work AI-down — degraded, not broken |
| **Cost and latency logged per call** | See below |

**Regulatory watch item.** High-risk (Annex III) obligations under the EU AI Act —
which cover employment and worker management — were **provisionally deferred from
2 August 2026 to 2 December 2027** under the Digital Omnibus agreement. As of the most
recent source read (27 May 2026) that deferral was **agreed but not yet in force**.
**Re-check status before relying on it.** The deferral buys build time; it does not
remove the obligation, and Article 5 was never deferred.

---

## 7 · Accessibility

- **Target: WCAG 2.2 level AA** on all user-facing surfaces. *(The project's older
  documents say 2.1 AA. 2.2 is the current W3C Recommendation and is backwards
  compatible — adopting it now costs little and avoids a re-audit. **Confirm which level
  your enterprise customers contractually require.**)*
- Every input labelled. Keyboard reachable. Focus visible. **Colour is never the only
  signal of a status** — and this product is full of statuses: at-risk, on-track,
  pending approval, disputed, frozen.
- Error text says what to do next, not "validation failed".
- Usable at **200% zoom** and on a **360 px** viewport.
- **EN/HI parity** on employee-facing surfaces at launch; Devanagari device-matrix QA.
- Automated checks catch roughly a third of real issues. **Budget a human pass**, and
  say in every test report what was automated and what was not.
- **Frontline bar (FR-N2):** a review that completes in **two minutes on a phone**.
  That is a requirement, not a nicety — it is the difference between frontline staff
  getting a review and being skipped.

---

## 8 · Observability and auditability

- **Structured logs at every boundary:** operation, document, duration, outcome. No
  personal data.
- **Every state transition evented and reconstructable.** Period and cycle close are
  **immutable post-lock** (FR-Q2 freezes at the smaller of goal period or cycle).
- **Every change to a goal definition audited** — who, when, from, to, why (FR-E6). The
  same for every calibration change (FR-I3). These are the artefacts that decide a
  grievance.
- **Sync run observability:** per-run log, records processed, exceptions queued,
  recompute count, duration. Plus **visible per-item freshness** to the employee
  (FR-F22) — "last updated 2 hours ago" is a trust feature.
- **Named alerts with named owners** for: failed background jobs, integration failures,
  permission-denied spikes, response-time breach, sync exception-queue growth, and
  **AI refusal-rate falling** (a falling refusal rate on unanswerable questions is a bad
  sign, not a good one).
- Test: **someone on call at 2 a.m. can answer "why is this employee's number wrong"
  from the logs and the audit trail alone.**

---

## 9 · Maintainability and upgrade-safety

- Customisation lives in our own apps as hooks and fixtures. **`apps/frappe`,
  `apps/erpnext` and `apps/hrms` are never edited.** If a change appears to require it,
  that is an escalation, not a coding decision.
- **`bench update` must be survivable**, and that must be *verified*, not assumed.
  `TODO — state how and how often.`
- Migrations are safe to run twice, and each states its rollback or states
  honestly that there is none.
- New dependency requires a stated reason and a stated cost.
- **One authoritative answer per number.** `KPI Fact` is the single authority for
  roll-up reporting (FR-L5). Two reports producing two revenue figures is a
  correctness defect, not a reporting preference.

---

## 10 · Cost

| Ceiling | Budget |
|---|---|
| Infrastructure per tenant per month | `TODO — set it; it constrains architecture more than any other number here` |
| **AI spend per employee per month** | `TODO`. For reference, the project's sibling documents budget **≤ ₹3–6 per employee per month** for assistive AI, and **≤ ₹5 per drafted artifact** |
| AI spend per action | Logged per call, alerted on breach |
| Cost review cadence | Monthly, per tenant, with AI spend broken out |

---

## Open questions

| Question | Owner | Blocks |
|---|---|---|
| SOC 2 Type II or ISO 27001 — which, and by when? | Founder | Enterprise deal cycle |
| Real KPI Fact volume from a live customer ERP | Engineering | Stage 4 sizing; the 20,000/day figure is a guess |
| Actual peak concurrency observed today | Engineering | The 300-user figure is a guess |
| WCAG 2.1 AA or 2.2 AA contractually? | Founder | Design system and audit scope |
| Data residency and Data Fiduciary position | Counsel | Hosting and DPA |
| Erasure vs audit-retention conflict — the written answer | Counsel | DPIA, and FR-Q5 |
| Is SSO/SCIM built? | Engineering | Enterprise plan claims |
| Infrastructure and AI cost ceilings | Founder | Architecture |

## Assumptions

- `[ASSUMPTION]` 50–1,000 employees per tenant, designed to 1,000, proven at 2,000.
- `[ASSUMPTION]` Peak concurrency ≈ 30% of headcount during cycle events.
- `[ASSUMPTION]` KPI Fact volume of 20,000/day sustained — **the weakest number in this
  document.** Replace it with an observation before Stage 4 ships.
- `[ASSUMPTION]` India-primary hosting and DPDP as the governing regime.
- `[ASSUMPTION]` The AI cost figures carried over from sibling project documents apply
  to this product.
