# Security & compliance baseline — Alvora HR

**Version 0.1 · 24 August 2026 · Status: DRAFT — needs counsel review before anything
here is quoted to a customer.**

Every agent on this team reads this file. It is the register of standards and laws we
build to, and — more usefully — what each one actually obliges the *product* to do.

> **Three honesty rules, and they are not decoration.**
>
> 1. **No agent on this team is a lawyer, and each must say so when it matters.** This
>    file states obligations as *engineering requirements derived from published
>    sources*, never as legal advice. Every ⚠ item names a human who must confirm it.
> 2. **Regulation moves faster than this file.** Each entry carries the date it was
>    last verified. Anything older than 90 days is stale — re-check before relying on
>    it, and say `[stale — re-verify]` if you use it anyway.
> 3. **A control that exists only in a document is not a control.** For every
>    obligation below, the question is: *what in the product, the pipeline or the
>    runbook makes this true, and what test proves it?* If there is no answer, that is
>    a gap, and it goes on the backlog — not into a policy PDF.

---

## 1 · Which regimes apply to us, and why

| Regime | Applies because | Status for us |
|---|---|---|
| **India — DPDP Act 2023 + DPDP Rules 2025** | India-primary customers; we process employee personal data | **Primary.** Non-negotiable |
| **India — IT Act 2000 (incl. s.43A, s.72A) & SPDI Rules 2011** | Predecessor regime; still relevant to contracts and liability | Confirm with counsel how much survives DPDP |
| **India — CERT-In Directions, 28 April 2022** (under IT Act s.70B(6)) | We are a service provider operating ICT infrastructure in India | **Primary, and routinely missed.** See §3 |
| **EU — GDPR** | Only if we process EU residents' data or target the EU | ⚠ **Founder must confirm.** If yes, this is a large workstream, not a checkbox |
| **EU — AI Act** | Our AI touches employment decisions | Article 5 binds us **today**; high-risk obligations deferred (see §4) |
| **ISO/IEC 27001:2022** | Buyer expectation at 50–1,000 with a security reviewer | Target — decide the date |
| **ISO/IEC 27701:2025** | Privacy management, now a **standalone** standard | Target after 27001 |
| **ISO/IEC 27017 / 27018** | Cloud security and cloud PII | Adopt as guidance; certify only if asked |
| **SOC 2 Type II (AICPA TSC)** | Alternative/parallel buyer expectation, esp. US-facing | Decide 27001 vs SOC 2 vs both |
| **NIST CSF 2.0** | A free organising frame for the security programme | Use as the internal map |
| **OWASP ASVS 5.0 / Top 10** | Application-level verification | **Adopt now** — costs nothing, structures the work |
| **PCI DSS** | Only if we ever touch cardholder data | Currently out of scope — keep it that way |

**Rule:** we build to the **strictest applicable obligation**, once. Building "DPDP now,
GDPR later" produces two half-systems. Where DPDP and GDPR differ, note the difference
and implement the tighter one unless there is a stated reason not to.

---

## 2 · India — DPDP Act 2023 and DPDP Rules 2025

*Verified 24 Aug 2026. Rules notified 14 November 2025; phased, with Data Fiduciary
obligations becoming fully effective roughly 18 months from notification — **around May
2027**. ⚠ Confirm exact phase dates and our Data Fiduciary vs Data Processor position
with counsel.*

### What it obliges the product to do

| Obligation | What must exist in the product |
|---|---|
| **Notice** — clear, itemised, in English or any language of the Eighth Schedule | A versioned privacy-notice object; per-employee record of which version they saw and when; the notice available in the languages our workforce actually reads |
| **Consent** — free, specific, informed, unconditional, affirmative; withdrawable as easily as given | A consent record per purpose, with version, timestamp, and a working withdrawal path. **Note:** much employment processing may rest on *legitimate uses* rather than consent — ⚠ counsel must tell us which basis applies to which processing, because the product design differs |
| **Purpose limitation** | A purpose tag on data and on every metric/adapter. Cross-purpose use blocked, not merely discouraged |
| **Data minimisation** | The measurement engine stores aggregates on the item and keeps document detail behind restricted read (FR-Q5). Adapters use a field allowlist |
| **Accuracy & correction** | Employee-initiated correction request with a routed workflow and an audit trail |
| **Erasure** on withdrawal or purpose completion | A retention & purge engine with per-object policies, **and a legal-hold override** — because a rating must stay defensible. ⚠ The erasure-vs-audit tension must be resolved in writing by counsel |
| **Reasonable security safeguards** — encryption, access control, logging | See §5 |
| **Breach handling** | **Immediate intimation to affected Data Principals and the Board, then a detailed report to the Board within 72 hours.** A breach workbench with a running clock, not an email thread |
| **Grievance redressal** | A named grievance officer, an in-product entry point, and an SLA clock on response |
| **Children's data** | Verifiable parental consent; no behavioural monitoring or targeted advertising at children. Almost certainly out of scope for us — **say so explicitly** rather than leaving it unanswered on a questionnaire |
| **Significant Data Fiduciary** duties, if we cross the threshold | DPO appointment, annual DPIA, independent audit, algorithmic fairness assessment. ⚠ Thresholds to be confirmed; we are unlikely to cross them soon, but our *customers* might, and they will ask us to support their obligations |

**The product angle worth remembering:** most of these are obligations on *our customer*
as the employer. The product that helps them discharge their duties is the one that
wins the security review. Build for the customer's compliance, not only our own.

---

## 3 · India — CERT-In Directions, 28 April 2022

*Verified 24 Aug 2026. Issued under s.70B(6) of the IT Act 2000. ⚠ Confirm current text
and any amendments with counsel — this is the item teams most often assume is someone
else's problem.*

These are hard, specific, and they shape **infrastructure**, not just policy:

| Direction | What it means for us |
|---|---|
| **Report specified cyber incidents to CERT-In within 6 hours of becoming aware** | Six hours, from *awareness*, not from resolution. Twenty categories including data breach, unauthorised access, ransomware, and website defacement. **This clock is far tighter than DPDP's 72-hour Board report — the breach workbench must run both clocks side by side, and the 6-hour one is the binding constraint on our on-call design.** |
| **Maintain ICT system logs for a rolling 180 days, stored within Indian jurisdiction** | Default cloud log retention will not satisfy this. Centralised log storage in an Indian region, with retention configured and *evidenced*. This is an architecture requirement, not a setting |
| **Synchronise all ICT systems to NIC or STQC NTP servers** (or traceable equivalents) | A deployment requirement, and an admin health check that surfaces drift — forensic timestamps are worthless if clocks disagree |
| **Designate a point of contact** for CERT-In | A named person, registered, with a backup |
| **Extended retention duties for cloud / VPN / VASP providers** (subscriber records, five years) | ⚠ Confirm whether any of our services fall in these categories. Probably not — but *confirm and record the answer*, because a reviewer will ask |

**Engineering consequence:** log residency, retention and time-sync belong in the
deploy pipeline and in an admin-visible health page, and they must be verifiable
without a human going to look. Put them in `deploy/` and assert them.

---

## 3a · Where the data actually is  *(verified 6 Sep 2026)*

Measured on the host, not assumed:

| | |
|---|---|
| Provider | Contabo GmbH, AS51167 |
| Location | Lauterbourg, Grand Est, **France** |
| Timezone | Europe/Berlin |
| Sites on it | `alvoraa.co` (control plane), `demo.alvoraa.co`, and the dev stack |

**This contradicts an assumption recorded below.** §6 said *"India default; residency is
a deployment parameter"*. There is no India deployment. Every tenant, every backup and
every log is in France.

### What that is and is not a problem for

**DPDP: permitted.** Rule 15 of the DPDP Rules 2025 takes a blacklist approach - personal
data may be transferred anywhere except to countries the Central Government restricts, and
as of mid-2026 no list has been published. France is an unlikely candidate. No blanket
localisation requirement exists.

**CERT-In: not compliant.** §3 requires ICT logs held *within Indian jurisdiction* for a
rolling 180 days. Our logs are in France. This is the real residency gap, and it is an
infrastructure problem rather than a setting. ⚠ Confirm with counsel whether CERT-In binds
us as a body corporate operating in India - the answer is probably yes.

**Sectoral regulators: blocking for some buyers.** RBI (banks) and IRDAI (insurers) impose
their own India-residency rules, and public-sector procurement usually does too. Those
customers cannot be served from France whatever DPDP permits.

### The decision recorded

Do not move (6 Sep 2026). Hosting stays in France, is stated plainly in the privacy notice
and in security questionnaires, and an India region is built when a customer actually needs
one. Each tenant is a separate site, so a second region can serve the customers who require
it without moving anybody else - residency really is a per-tenant deployment choice, just
not one that has been exercised yet.

**Closed the same day:** the clock now synchronises to `samay1.nic.in` with Ubuntu as
fallback, satisfying the CERT-In NTP direction. It was on `ntp.ubuntu.com`.

**Still open:** 180-day India-resident log storage. Nothing else in CERT-In §3 is blocked
by hosting location.

---

## 4 · EU — GDPR and the AI Act

⚠ **Applicability first.** If we have no EU data subjects and do not target the EU, most
of this is preparation, not obligation. **The founder must give a yes/no**, because the
answer changes the roadmap materially. The project's own backlog cites AI Act articles,
which suggests someone already assumed yes.

### GDPR — the parts that bite an HR performance product

| Article | Obligation | Product consequence |
|---|---|---|
| **Art 22** — automated decisions producing legal or similarly significant effects | A performance rating that drives pay, promotion or termination is squarely in scope. The data subject has the right to **obtain human intervention, express their point of view, and contest the decision** | This is why **FR-J4 (AI never rates)** is not merely an ethics position — it is the cheapest possible compliance posture. Keep it. Additionally: every rating records the **named human who decided**, and "meaningful human involvement" must be real, not a rubber stamp |
| **Art 15 / 20** — access and portability | The employee's own-data view and export |
| **Art 17** — erasure, against Art 17(3) exemptions | Retention engine plus legal hold |
| **Art 30** — records of processing | Maintained, and shareable with a customer's DPO |
| **Art 32** — security of processing | §5 |
| **Art 33 / 34** — breach notification, 72 hours to the supervisory authority | A third clock in the breach workbench |
| **Art 35** — DPIA for high-risk processing | Systematic evaluation of employees is a classic DPIA trigger. **DPIA is a gate before the measurement engine ships** |
| **Art 88** — Member State rules on employment data | Varies by country. ⚠ Counsel, per market |

### EU AI Act

*Verified 24 Aug 2026.*

- **Article 5 prohibitions — in force since 2 February 2025.** These include emotion-
  inference systems in the workplace. **This binds us today.** FR-J6 makes it
  architecturally impossible rather than merely unbuilt, which is the correct posture.
- **High-risk (Annex III) obligations — covering employment and worker management —
  were provisionally deferred from 2 August 2026 to 2 December 2027** under the Digital
  Omnibus agreement. As of the most recent source read (27 May 2026) the deferral was
  **agreed but not yet in force.** ⚠ **Re-check before relying on it.** The deferral
  buys build time; it removes nothing.
- Obligations to design toward regardless: **deployer duties (Art 26)** including human
  oversight and log retention; **the right to an explanation (Art 86)**; **worker
  notification** before putting a high-risk system into service (Art 26(7)); and **AI
  literacy (Art 4)**, in force since Feb 2025.
- The product answer to Art 86 is already specified: **FR-G4** (replayable Rating
  Derivation) plus **FR-G5** (plain-language explanation to the employee) plus **FR-J5**
  (AI action log). Ship those and the explanation obligation is met by a feature rather
  than a promise.

---

## 5 · International security standards — what we adopt and what we certify

**Adopt** means we build to it now. **Certify** means an auditor confirms it, on a date.

### ISO/IEC 27001:2022 — the ISMS *(certify)*

The Annex A control themes that touch product code directly, and where they land:

| Control area | Product consequence |
|---|---|
| Access control, privileged access, identity | RBAC + row-level scoping; MFA; SSO/SCIM; break-glass with dual approval and tenant notification |
| Access rights review | A **quarterly access recertification campaign** with a sign-off record — a feature, not a spreadsheet |
| Cryptography & key management | TLS 1.2+ in transit, AES-256 at rest, field-level vault for statutory IDs, documented rotation |
| Logging & monitoring | Immutable, time-synced, 180-day India-resident (see §3) |
| Secure development | ASVS-aligned requirements, code review, dependency scanning, SBOM |
| Supplier / cloud security | Sub-processor register, tenant-visible, change notification |
| Information deletion, data masking, DLP *(new in 2022)* | Retention engine, field-level masking, reveal-with-reason |
| Business continuity | RPO ≤1h / RTO ≤4h with **tested** restore drills |

### ISO/IEC 27701:2025 — privacy management *(certify after 27001)*

Revised in 2025 and now usable as a **standalone** PIMS rather than only an extension
to 27001. It is the cleanest way to answer "how do you manage privacy, not just
security" — which is precisely the question an HR-data buyer asks. Map DPDP and GDPR
obligations onto it once, rather than answering each questionnaire from scratch.

### ISO/IEC 27017 and 27018 *(adopt as guidance)*

Cloud-specific controls and cloud PII protection. Useful mostly as a checklist for the
shared-responsibility conversation with a customer's IT reviewer.

### SOC 2 Type II *(decide)*

Trust Services Criteria — Security is mandatory; add **Confidentiality** and
**Privacy** for an HR product; Availability if we commit to an SLA. **Type II is what
reviewers want** because it evidences operation over a period; Type I buys little.
Evidence is retrospective, so **starting late costs a year** — decide now, even if the
decision is "not yet, and here is when".

⚠ **Decision needed: ISO 27001, SOC 2, or both?** Rough guide, not advice: Indian and
EU buyers tend to ask for ISO; US buyers tend to ask for SOC 2. If the customer base is
India-first with EU ambition, ISO 27001 + 27701 is usually the better first spend.

### NIST CSF 2.0 *(adopt as the internal map)*

Free, and its six functions — **Govern, Identify, Protect, Detect, Respond, Recover** —
are a good way to see what the programme is missing. The **Govern** function added in
2.0 is the one small companies skip and auditors ask about.

### OWASP ASVS 5.0 and Top 10 *(adopt now)*

ASVS 5.0.0 was released 30 May 2025. **Target Level 2** for the application — the level
intended for applications handling sensitive data, which HR data plainly is. *(5.0
restructured the standard; confirm the current level definitions against the 5.0
document rather than assuming 4.0's.)* Practical use: turn the relevant ASVS
requirements into test cases, not into a spreadsheet nobody opens.

---

## 6 · The conflicts you must resolve deliberately

Real compliance work is mostly resolving these, and each needs a written, dated
decision — not a default.

| Tension | The two pulls | How to resolve |
|---|---|---|
| **Erasure vs defensibility** | DPDP/GDPR erasure vs a rating that must stay defensible for years | Legal hold on decision records; erase what is not decision-bearing; **counsel signs the boundary** |
| **CERT-In 180-day India log retention vs data minimisation** | Keep more logs, longer, in India vs keep less personal data | Logs carry document identifiers, never personal content. Then residency is cheap |
| **6-hour CERT-In clock vs 72-hour DPDP/GDPR clock** | Different triggers, different recipients | One workbench, three clocks, one decision tree. **The 6-hour clock sets the on-call design** |
| **Transparency vs surveillance** | Managers want visibility; employees have rights | Aggregate and suppress below a minimum n. FR-H7 already bans passive behavioural monitoring — keep it |
| **Fairness reporting vs collecting protected attributes** | You cannot measure adverse impact without the attribute you should minimise | Aggregate-only, minimum-n suppression, strict purpose tag, separate access path. ⚠ Counsel before building |
| **AI usefulness vs Art 22 / FR-J4** | An AI-suggested rating would be popular and is a liability | Already resolved: AI drafts and critiques; a named human decides. **Do not reopen this** |
| **Data residency vs a cheaper region** | | ⚠ **Corrected 6 Sep 2026:** there is no India deployment - everything is in France (§3a). DPDP permits it; CERT-In log residency does not |

---

## 7 · How this file is used

- **Product manager** — names the regime in every brief; never proposes a capability
  §4 prohibits.
- **Business analyst** — produces the **compliance-impact sub-analysis** on every spec
  (mandatory; see the agent definition), with a control-mapping table.
- **Engineer** — implements the control and says which obligation each one discharges.
- **Test engineer** — writes the test that *is* the evidence. A compliance control
  without an automated test is an assertion.
- **Reviewer** — verifies the mapping and blocks on an unmet obligation.
- **Security & privacy engineer** — owns this file, keeps the dates fresh, and owns the
  gaps that no slice has picked up.

**Nobody on this team gives legal advice.** We prepare precise questions for counsel and
implement the answers.

---

## Open questions

| Question | Owner | Blocks |
|---|---|---|
| Do we process EU personal data, or target the EU? | Founder | Whether §4 is obligation or preparation |
| Are we Data Fiduciary, Data Processor, or both, per contract? | Counsel | Almost every entry in §2 |
| ISO 27001 / 27701, SOC 2, or both — and by when? | Founder | Enterprise deal cycle; evidence starts accruing from the decision date |
| Written boundary between erasure and audit retention | Counsel | Retention engine design |
| Do any CERT-In extended-retention categories apply to us? | Counsel | §3 |
| Named grievance officer, DPO (if required), CERT-In point of contact | Founder | Three obligations that need a person, not a function |
| Data residency contractual commitment | Founder / counsel | Hosting — note §3a: it is France today |
| 180-day India-resident log storage (CERT-In) | Founder | Selling to any regulated buyer |

## Assumptions

- ~~`[ASSUMPTION]` India-primary~~ — **wrong, corrected 6 Sep 2026.** Hosting is France
  (§3a). DPDP + CERT-In remain the binding regimes; CERT-In log residency is unmet.
- `[ASSUMPTION]` GDPR and the AI Act are anticipatory until the founder confirms EU
  exposure — the backlog's AI Act citations suggest someone has already assumed yes.
- `[ASSUMPTION]` No cardholder data anywhere in the system, so PCI DSS is out of scope.
- `[ASSUMPTION]` We are not a Significant Data Fiduciary today.
