# Compliance feature map — what the product must actually contain

**Version 0.1 · 24 August 2026 · Status: DRAFT — a proposal, not a plan**

The baseline (`security-compliance-baseline.md`) says what the law and the standards
oblige. **This file says what to build so those obligations are true, demonstrable, and
hard to regress.**

> **How to read the Status column.** I could not read the code at
> `C:\Surbhi-Git\hr-app`, so **every status is `?` — unknown until verified.** The
> first job for whoever gets repo access is to turn each `?` into `Built`, `Partial`
> or `Missing`. Do not schedule any of this until that pass is done: half of it may
> already exist, and building it twice is the expensive mistake.

**Sequencing principle.** Ship the **controls that produce evidence** before the
controls that produce policy. An auditor, a customer's security reviewer and a
regulator all ask the same question — *show me* — and a screenshot of a working feature
ends the conversation faster than a PDF.

Priority key: **P0** = blocks an enterprise deal or a legal obligation already in force ·
**P1** = needed before the measurement engine or AI ships · **P2** = maturity.

---

## A · Platform & tenant foundation

| # | Feature | Discharges | How it is proven | Pri | Status |
|---|---|---|---|---|---|
| A1 | **Field sensitivity classification** — every field on every DocType carries a class: `public / internal / sensitive / statutory-id`. The class drives masking, export inclusion, log redaction and prompt redaction **automatically** | DPDP minimisation & security; ISO 27001 data masking; GDPR Art 32 | A test that adds a new sensitive field and asserts it is absent from exports, logs and prompts without any further code | **P0** | ? |
| A2 | **Immutable audit ledger** — append-only, hash-chained, tamper-evident; who, when, from, to, why; queryable | DPDP security; CERT-In logging; ISO 27001; the grievance defence | Tamper test: mutate a row, assert the chain breaks and alerts | **P0** | ? |
| A3 | **Log residency + retention enforcement** — ICT logs centralised in an Indian region, 180-day rolling retention, configured in `deploy/` and asserted, not assumed | **CERT-In Directions 2022** | Deploy-time assertion + an admin health page showing region, retention and oldest log | **P0** | ? |
| A4 | **NTP conformance check** — all nodes synced to NIC/STQC (or traceable equivalent); drift surfaced | **CERT-In Directions 2022** | Health check fails on drift beyond threshold | **P0** | ? |
| A5 | **Breach / incident workbench** — one record, **three clocks**: CERT-In 6h, DPDP Board 72h, GDPR 72h (if applicable), plus immediate Data Principal intimation. Templates, affected-record query, decision tree, and an exportable timeline | CERT-In; DPDP; GDPR Art 33/34 | A **drill**, executed and documented, before GA. The 72-hour clock is not the moment to discover who writes the notice |
| | | | | **P0** | ? |
| A6 | **Retention & purge engine** — per-object retention policy, effective-dated, with **legal hold**; scheduled purge that emits an audit receipt | DPDP erasure & storage limitation; GDPR Art 17 | A test that seeds expired data, runs the job, and asserts deletion + receipt + that held records survived | **P0** | ? |
| A7 | **Consent & notice registry** — versioned privacy notice; per-employee record of version, timestamp and language; withdrawal path; notice available in the languages the workforce reads | DPDP notice & consent | Test: a new notice version requires re-acknowledgement and the old version stays retrievable | **P0** | ? |
| A8 | **Data-principal rights console** — access, correction, erasure, grievance; SLA clock; routed workflow; evidence of action | DPDP rights & grievance redressal; GDPR Art 15/16/17/20 | End-to-end test per right type, with the SLA timer asserted | **P0** | ? |
| A9 | **Sub-processor register**, tenant-visible, with change notification | DPDP; standard DPA terms; ISO 27001 supplier controls | Register renders; a change fires notification | P1 | ? |
| A10 | **Trust-centre / evidence-pack export** — one action produces the security-questionnaire bundle: policies, sub-processors, certifications, pen-test summary, uptime, DPA | Sales velocity, and it *is* the ISO/SOC evidence | Generated, not assembled by hand | P1 | ? |
| A11 | **DPIA register** linked to features, with a **hard gate before the measurement engine ships** | DPDP (SDF) / GDPR Art 35; the backlog's own FR-Q5 AC5 | The gate is in the release checklist and blocks | P1 | ? |
| A12 | **Records of processing (RoPA)** generated from purpose tags rather than maintained by hand | GDPR Art 30; ISO 27701 | RoPA regenerates from live metadata | P2 | ? |

---

## B · Identity, access and segregation of duties

| # | Feature | Discharges | How it is proven | Pri | Status |
|---|---|---|---|---|---|
| B1 | **SSO (SAML/OIDC) + SCIM provisioning and de-provisioning** | ISO 27001 access control; the enterprise buyer's first question; instant revocation on exit | Test: SCIM deprovision revokes access on the next request, not the next login | **P0** | ? |
| B2 | **MFA**, session timeout, and optional per-tenant IP allowlist | ISO 27001; SOC 2 CC6 | Policy enforced server side | **P0** | ? |
| B3 | **Permission matrix as data** — role × doctype × action × row-scope, exportable and diffable, so a reviewer can be *shown* it | ISO 27001; SOC 2; the fastest way to end a security review | Export matches runtime behaviour, asserted by test | **P0** | ? |
| B4 | **`ignore_permissions` register** — every use recorded with a justification; **a CI counter that can only go down** | The single highest-risk pattern in a Frappe HR app | Build fails when the count rises | **P0** | ? |
| B5 | **Access recertification campaign** — quarterly, per tenant, with sign-off records | ISO 27001 access-rights review; SOC 2 | A campaign completes and produces an auditable record | P1 | ? |
| B6 | **Break-glass access** — dual approval, time-boxed, tenant-notified, session-audited; **no agent participation ever** | Provider isolation; ISO 27001 privileged access | Test: no non-break-glass path reaches tenant person-level data, enforced in CI | **P0** | ? |
| B7 | **Segregation of duties checks** — a manager cannot moderate their own reports' ratings (FR-I6); an approver cannot approve their own comp recommendation | SOC 2; audit expectation; basic fairness | Negative tests | P1 | ? |

---

## C · Core HR & employee master

| # | Feature | Discharges | How it is proven | Pri | Status |
|---|---|---|---|---|---|
| C1 | **Masked display with reveal-on-reason** — statutory IDs and bank details masked by default; reveal requires a reason and writes an audit entry | DPDP security; ISO 27001 masking | Test asserts mask by default and audit on reveal | **P0** | ? |
| C2 | **Field-level encryption vault** for statutory IDs and bank details, with documented key rotation and 100% access audit | DPDP reasonable safeguards; ISO 27001 crypto | Rotation runbook executed; access log complete | **P0** | ? |
| C3 | **Document vault with expiry and purge** — ID proofs, certificates, background checks | Retention limitation | Expired documents purge with a receipt | P1 | ? |
| C4 | **Purpose tag on employee data** collected for one purpose and reused for another is blocked, not warned | DPDP purpose limitation | Cross-purpose read fails closed **and** alerts | P1 | ? |
| C5 | **Employee self-view + portable export** of their own record | DPDP access; GDPR Art 15/20 | The employee can produce it without HR | P1 | ? |

---

## D · Goals, KPIs and the measurement engine

| # | Feature | Discharges | How it is proven | Pri | Status |
|---|---|---|---|---|---|
| D1 | **Fact & credit visibility scoped by role and hierarchy** — peers never see each other's commercial transactions (FR-Q4) | DPDP minimisation; the fairness claim | Negative permission tests at every level | **P0** | ? |
| D2 | **Aggregate-on-item, detail-behind-restricted-read** (FR-Q5) — customer names and invoice values do not spread into the HR system | DPDP minimisation; reduces breach blast radius | Assert the item row carries no commercial detail | **P0** | ? |
| D3 | **Adapter field allowlist** — an integration pulls only declared fields; a new field requires a config change and a review | Minimisation; supply-chain hygiene | Adapter test rejects undeclared fields | P1 | ? |
| D4 | **Credentials encrypted per company, never logged, never in a traceback** (FR-F13) | ISO 27001 crypto & logging | An explicit test that forces an exception and asserts the traceback is clean | **P0** | ? |
| D5 | **Dispute without edit** (FR-Q1) — an employee can challenge a synced number they cannot alter | GDPR Art 22 contest right; basic trust | The dispute raises HR review; the fact is unchanged | P1 | ? |
| D6 | **Period freeze** (FR-Q2) — a settled period cannot be reopened by a late transaction without an explicit, audited HR reopen | Auditability; fairness | Late fact lands in the exception queue with a reason | P1 | ? |
| D7 | **Self-produced-metric flag** (FR-Q3) — flag at design time where the scored person produces the data | Anti-gaming; audit expectation | Flag surfaces in the metric definition UI | P2 | ? |
| D8 | **Per-item automation off switch** (FR-F4) and **hold-last-value on outage** (FR-F10) | Fairness; reliability | An unreachable source never writes zero | P1 | ? |

---

## E · Appraisal, calibration and the decision record

*This is where the product's compliance story is strongest — and where it is most
saleable.*

| # | Feature | Discharges | How it is proven | Pri | Status |
|---|---|---|---|---|---|
| E1 | **Rating Derivation record** (FR-G4) — every rating replayable from stored inputs, with the rating-scale snapshot taken at generation | **GDPR Art 22 / AI Act Art 86**; grievance defence; the differentiator | Replay a historical rating and get the same number | **P0** | ? |
| E2 | **Plain-language derivation shown to the employee** (FR-G5) | The *practical* form of the explanation right — and no competitor offers it | An employee can read it without help | **P0** | ? |
| E3 | **Named human decision-maker on every rating**, with a meaningful-involvement attestation — not a rubber stamp | **GDPR Art 22(3)**; FR-J4 | No rating can exist without a named accountable human | **P0** | ? |
| E4 | **Human-intervention request** — an employee can formally ask for review of a decision, routed with an SLA | GDPR Art 22(3); DPDP grievance | End-to-end test | P1 | ? |
| E5 | **Calibration change log** (FR-I3) — who, when, from, to, why, for every moderated rating | Audit; grievance defence | Every change produces a record; none can be made without a reason | **P0** | ? |
| E6 | **Definition-change audit** (FR-E6) and **locked definition fields on approval** (FR-E3) | The goalposts cannot move quietly | Diff test on a locked field fails | **P0** | ? |
| E7 | **Aggregated fairness / distribution report** with **minimum-n suppression** and a separate access path | Adverse-impact awareness; SDF algorithmic fairness duty | Suppression asserted at small n. ⚠ **Counsel before building** — measuring this requires attributes we otherwise minimise | P2 | ? |
| E8 | **PIP documentation structured to withstand scrutiny** (FR-N4) | Indian labour-law exposure | ⚠ **Requires qualified employment-law review before release** | P2 | ? |

---

## F · Compensation

| # | Feature | Discharges | How it is proven | Pri | Status |
|---|---|---|---|---|---|
| F1 | **Approval chain with segregation of duties** and a full decision trail | SOC 2; audit | No self-approval path exists | **P0** | ? |
| F2 | **Letter render is variables-only** — a rendered letter that differs from its template by anything other than variable substitution is a hard fail and an alert | Tamper canary; document integrity | Diff test on every generated letter | P1 | ? |
| F3 | **Payroll posting carries no bank or statutory identifiers** beyond what the receiving system requires | Minimisation | Payload assertion test | **P0** | ? |
| F4 | **Comp data visibility scoped tightly** — the most sensitive data in the product | DPDP; ISO 27001 | Negative tests, including HR sub-roles | **P0** | ? |

---

## G · Portal / employee self-service

| # | Feature | Discharges | How it is proven | Pri | Status |
|---|---|---|---|---|---|
| G1 | **Privacy notice surfaced in-product**, versioned, in the employee's language | DPDP notice | Re-acknowledgement on version change | **P0** | ? |
| G2 | **"My data" view + export** | DPDP/GDPR access & portability | Self-service, no HR ticket | P1 | ? |
| G3 | **Grievance / rights-request entry point** with visible SLA | DPDP grievance redressal | Reaches the console in A8 | **P0** | ? |
| G4 | **AI disclosure notice** — where AI assisted, the employee is told, and can ask what it did | AI Act Art 26(7) / Art 86; FR-J8 | Disclosure renders wherever an AI-assisted artefact appears. **Must not read as a compliance guarantee to the customer** | P1 | ? |
| G5 | **Language parity** on all of the above (EN/HI at minimum) | DPDP notice-language duty; FR-N3 | Parity test in CI | P1 | ? |

---

## H · AI layer

| # | Feature | Discharges | How it is proven | Pri | Status |
|---|---|---|---|---|---|
| H1 | **No rating-writing tool exists for any model** (FR-J4) | GDPR Art 22; the whole trust position | Structural: the tool is absent. Test asserts the toolset | **P0** | ? |
| H2 | **No emotion, voice or facial analysis — architecturally impossible** (FR-J6) | **EU AI Act Art 5, in force since Feb 2025** | Test asserts no such capability or dependency exists | **P0** | ? |
| H3 | **Redaction proxy at the prompt boundary** — sensitive fields (driven by A1) never reach a model | DPDP; GDPR Art 32 | Assert on the captured outbound payload, not on intent | **P0** | ? |
| H4 | **AI action log** — inputs, prompt version, model version, grounding citations, and the human decision that followed; retained ≥12 months, built to 18 (FR-J5) | AI Act Art 26(6); DPDP | Log completeness monitored as a metric | **P0** | ? |
| H5 | **Untrusted text isolated as data** — employee free text, uploaded policies, ERP description fields never select a tool or code path | Prompt injection is the live attack surface here | Seeded injection tests on every agent reading user text | **P0** | ? |
| H6 | **Grounded-or-silent** — AI narrative comes strictly from that employee's own record; sparse data yields a short draft, never padding (FR-J3) | Accuracy; dignity; Art 5 GDPR | Fabrication tests with sparse fixtures | P1 | ? |
| H7 | **Per-feature kill switch and a working non-AI fallback** | Reliability; AI Act oversight | The feature degrades to a form or a queue; test with AI disabled | **P0** | ? |
| H8 | **Cost and latency per call, logged and alerted** | Budget discipline | Breach alerts fire | P1 | ? |

---

## I · Build pipeline — the controls that stop regression

These are not features, but without them everything above decays within two quarters.

| # | Gate | Discharges | Pri | Status |
|---|---|---|---|---|
| I1 | **Permission test suite blocking in CI**, covering every DocType including negative cases | The #1 risk in this codebase | **P0** | ? |
| I2 | **Cross-tenant isolation suite** — seeded two-tenant DB, every endpoint probed; any foreign data returned fails the build | Multi-tenant integrity | **P0** | ? |
| I3 | **`ignore_permissions` counter** — fails on increase | B4 | **P0** | ? |
| I4 | **PII/secret-in-logs scanner** on test output and forced tracebacks | A1, D4 | **P0** | ? |
| I5 | **Dependency vulnerability scan + SBOM** | ISO 27001; supply chain | P1 | ? |
| I6 | **ASVS 5.0 Level 2 requirement traceability** — the relevant requirements exist as test cases, not as a spreadsheet | Application security | P1 | ? |
| I7 | **Restore drill, quarterly, documented** | RPO/RTO; ISO 27001; the most-requested evidence item | **P0** | ? |
| I8 | **Breach drill, before GA** | CERT-In 6h clock | **P0** | ? |

---

## Where I would start

If the verification pass says most of this is missing, the order that buys the most in
the least time:

1. **I1–I4** — the four CI gates. They are cheap, they stop the bleeding, and they turn
   every later control into something that cannot silently regress.
2. **The reported appraisal permission defect** (see `product-context.md` §10 risk 1).
   Verify it first; if real, it is a Blocker, not a ticket.
3. **A1 field sensitivity classification.** One feature that makes masking, export
   hygiene, log redaction and prompt redaction mechanical instead of remembered. It is
   the highest-leverage item on this page.
4. **A3 + A4 — CERT-In log residency and NTP.** Small, infrastructural, in force now,
   and the thing teams discover too late.
5. **E1 + E3 — Rating Derivation and the named human decision-maker.** These are
   simultaneously the compliance answer, the grievance defence and the differentiator.
   Rarely does one feature do all three.
6. **A5 breach workbench + the drill.** Six hours is not long enough to improvise.

Everything else follows the backlog's own staging.

---

## Open questions

| Question | Owner |
|---|---|
| Repo access, so every `?` above becomes a real status | Surbhi |
| EU exposure yes/no — decides whether GDPR items are P0 or P2 | Founder |
| Counsel sign-off on E7 (fairness reporting) and E8 (PIP documentation) | Counsel |
| Which of these are already covered by existing backlog stories, so we do not create duplicates in YouTrack | BA + founder |

## Assumptions

- `[ASSUMPTION]` Module names above map to `hrms`, `alvoraa_goals`, `alvoraa_portal`,
  `alvox_compensation` and the platform layer. Correct them after the repo read.
- `[ASSUMPTION]` Nothing here duplicates an existing YouTrack story. **Check before
  creating tickets** — the backlog already covers many of the FR-numbered items cited.
