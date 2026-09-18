# Legal templates — read me first

> **I am not a lawyer. Nothing in this folder is legal advice.** These drafts were prepared by
> Alvoraa's security and privacy engineer (an AI agent) for Surbhi, the founder and interim
> compliance owner, on **17 September 2026**. They exist so that a DPDP lawyer can review a
> precise draft in hours instead of writing from nothing. **Neither template may be used with
> a customer or an employee until a qualified Indian data-protection lawyer has reviewed it.**

---

## 1. What is in this folder

| File | What it is for | Who uses it |
|---|---|---|
| `data-processing-agreement-template.md` | The contract between a customer company and Alvoraa. It says the customer decides (Data Fiduciary), Alvoraa processes on its behalf (Data Processor), and what Alvoraa must do: security, sub-processors, breach notice, help with employees' rights, deletion at the end. It has three annexes: what data is processed, the security measures **with an honest status for each**, and the sub-processor list | Alvoraa and each customer, signed alongside the main subscription agreement |
| `employee-privacy-notice-template.md` | A notice each customer adapts and gives to its own employees. Part A tells HR how to adapt it. Part B is the full notice. Part C is the short in-app notice for the mobile attendance app, with the "I agree" line. Part D is the Hindi placeholder | Each customer's HR team. The customer, not Alvoraa, publishes it |
| `README.md` | This file: the review checklist, open questions, and what the product must do before the first paying customer | Surbhi and the lawyer |

**Marks used in both templates:** `{placeholder}` to fill in · `[LAWYER TO CONFIRM]` needs legal
judgement · `[PRODUCT GAP]` the product cannot yet do what the clause says.

---

## 2. The working position these drafts use

Decided by Surbhi, recorded in `docs/slices/013-mobile-app/01c-security-privacy-requirements.md`
("User decisions" and "Consent gate", both 17 Sep 2026):

| Point | Working position |
|---|---|
| Roles | Each **customer company is the Data Fiduciary**. **Alvoraa is the Data Processor** |
| Legal basis — most HR data | **Legitimate use for employment**, DPDP Act s.7(i). Profile, attendance records, leave, pay, reviews, documents |
| Legal basis — mobile app photo and location | **Consent**, DPDP Act s.6. Explicit "I agree"; recorded with time, notice version, language and phone; withdrawable through "Remove this phone"; re-asked when the notice changes |
| Free consent | An employee who says no must have another way to mark attendance, with no penalty |
| Hosting | **France** (Contabo, Lauterbourg). Decision of 6 Sep 2026: stay, and state it plainly |
| Compliance owner | Surbhi, interim. No lawyer engaged yet |

---

## 3. What the lawyer should check — ranked

Ranked by how much each point could hurt a customer or Alvoraa if it is wrong, and how many
other clauses depend on it.

| Rank | Check | Where | Why it matters |
|---|---|---|---|
| **1** | **Is consent the right basis for app photo and location, and can it be "free" between employer and employee?** Is "another way to mark attendance, with no penalty" enough? Should the web check-in page, which collects the same photo and location, also need consent? | DPA cl. 5.3–5.5; Notice §4, §5, Part C | If consent is not valid, the app's whole legal footing fails. If consent is not needed, the design adds friction for nothing. Every other app clause depends on this |
| **2** | **What must happen to photos and exact locations when an employee withdraws consent?** s.8(7) says erase on withdrawal unless a law requires keeping. The design keeps photos until the normal retention period ends | DPA cl. 5.7; Notice §5; Part C note 4 | The product cannot yet delete one person's photos on withdrawal. The answer decides what must be built |
| **3** | **Breach notice: the period Alvoraa promises the customer, and who reports to CERT-In.** DPDP Rule 7 says the Fiduciary tells people and the Board "without delay" and reports in 72 hours; CERT-In says 6 hours and may bind both parties. Does hosting in France change Alvoraa's CERT-In duty? | DPA cl. 12 | A short promise that the team cannot meet is a breach of contract on the worst day. Alvoraa has no tested incident runbook yet |
| **4** | **Cross-border transfer and CERT-In log residency.** Is France acceptable today under s.16(1) and Rule 15? What must the DPA promise if a restriction is notified? Does the CERT-In 180-day India log rule bind Alvoraa, and must it be disclosed? Is EU law engaged by EU hosting? | DPA cl. 10; Notice §7 | Logs are in France, so CERT-In log residency is not met today. Regulated buyers (banks, insurers, government) may be blocked outright |
| **5** | **Do the statutory rights to see, correct and erase (s.11, s.12) apply to data used under s.7(i)?** The notice offers them for all data as good practice — does that create obligations the customer does not want? | DPA cl. 11.2; Notice §10 | Decides what the customer must promise and what the product must build (rights console, export) |
| 6 | **Retention periods.** Minimum keeping periods for attendance, wage, leave and tax records under state Shops and Establishments Acts and wage laws; whether exact coordinates can be kept as long as attendance; whether "0 = keep photos for ever" may be offered; the boundary between erasure and keeping a review record that defends a decision | DPA Annex 1 A1.6, cl. 14; Notice §8 | No retention engine exists for anything except photos. The lawyer's periods become the build list |
| 7 | **Liability, indemnity and cap.** DPDP penalties fall on the Fiduciary and are large; customers will push them onto Alvoraa | DPA cl. 16 | Company-level financial exposure |
| 8 | **Roles at the edges.** Is Alvoraa a Fiduciary for anything — app store publishing, pilot testers' emails in Firebase, operator logs? Which Alvoraa entity signs? | DPA cl. 2.3, Parties | Affects Alvoraa's own notice and duties |
| 9 | **Notice content and language.** Does the short in-app screen meet Rule 3 (withdrawal link, rights, complaint to the Board)? Is Hindi (or another Eighth Schedule language) required? Must "hosted in France" appear in the app notice (slice 013 flag C-8)? Is an on-screen notice enough for field staff with no email? | Notice Part A, Part C, Part D | Consent to a notice a person cannot read is unlikely to be informed |
| 10 | **Modules outside the employee notice.** Delivery drivers (continuous location, speed and heading during deliveries), job applicants and vendor users | DPA Annex 1 A1.4, A1.5; Notice §3 note | The employee notice's "no tracking" line is **false** for drivers if the delivery module is used |
| 11 | **Sub-processor terms.** Is general permission with 30 days' notice acceptable? Are Contabo's standard terms enough? | DPA cl. 9, Annex 3 | Several sub-processors are still unknown (section 6) |
| 12 | **Audit and certification wording.** Audit rights on a shared platform; the plain statement that Alvoraa holds no certification | DPA cl. 15 | Must stay true |
| 13 | **Young workers.** Is the "not for under-18s" line enough under s.9? | DPA cl. 5.8; Notice §13 | Apprentices may exist in some customers |
| 14 | Governing law, dispute forum, order of documents | DPA cl. 17, 18 | Standard, but needs a decision |

---

## 4. Open questions

| # | Question | Who answers | What it blocks |
|---|---|---|---|
| L-1 | Is consent (s.6) the right basis for app photo and location, and what makes it free? (also slice 013 C-2) | Lawyer | Final app notice, spec changes, first real customer |
| L-2 | On withdrawal, erase photos and coordinates at once or at the end of the retention period? | Lawyer | A "delete this person's app data" function; DPA cl. 5.7 |
| L-3 | Does the web check-in page also need consent? | Lawyer, then Surbhi | Web page notice; whether the web page can be the "decline" alternative |
| L-4 | Breach notice period Alvoraa promises; who reports to CERT-In; effect of France hosting | Lawyer | DPA cl. 12; incident runbook design |
| L-5 | Transfer to France today and if restricted later; CERT-In log residency; EU law | Lawyer; Surbhi on EU exposure | DPA cl. 10; sales to regulated buyers |
| L-6 | Do s.11 and s.12 rights apply to s.7(i) data? | Lawyer | Notice §10; rights console scope |
| L-7 | Retention periods per record type, including exact coordinates (slice 013 C-3) and the "0 = for ever" setting | Lawyer, then Surbhi | Retention engine; Notice §8 |
| L-8 | Hindi required or optional (slice 013 C-4); on-screen notice enough for field staff | Lawyer | Part D; app rollout to Hindi-first staff |
| L-9 | Which Alvoraa legal entity contracts | Surbhi | Both templates' party details |
| L-10 | Liability cap and indemnities | Lawyer, Surbhi | DPA cl. 16 |
| L-11 | Separate notices for drivers, applicants, vendor users | Lawyer | Any customer using those modules |
| S-1 | Is off-site backup to S3 configured? Which region? How long are backup copies kept? | Surbhi | DPA Annex 2 S25–S26, Annex 3, cl. 14.3 |
| S-2 | Which email (SMTP) provider sends notifications? | Surbhi | DPA Annex 3 |
| S-3 | Are push notifications (Frappe relay / Firebase Cloud Messaging) or India Compliance online services turned on for any tenant? | Surbhi | DPA Annex 3 |
| S-4 | Do we process data of anyone in the EU? | Surbhi (founder) | GDPR questions in DPA cl. 10.7 |
| S-5 | Are there written confidentiality terms for everyone at Alvoraa who can reach customer data? | Surbhi | DPA cl. 7 |
| S-6 | Who is the named breach contact and CERT-In point of contact, with a backup? | Surbhi | DPA cl. 12 |

---

## 5. What must be true in the product before the first paying customer

"Status" is what I found on 17 Sep 2026 in the repository (local `dev` at `9138251`) and the
slice documents. **Every item here either gets built, or the template clause that depends on
it is changed.** Nothing may be promised in a contract that the product does not do.

### 5a. Needed by the consent gate for the mobile app

| # | Must be true | Status today | Source |
|---|---|---|---|
| P-1 | The app asks for an explicit "I agree", with a "No, I do not agree" button, and sets nothing up without it | **Planned; spec still says the opposite** (AC-92, AC-97, PRIV-4 forbid "I agree"). Spec must be updated | Slice 013; consent gate |
| P-2 | Each agreement is stored as a new record (time, version, language, phone, app or web); old records never overwritten | **Not built** — today one version field and one date field on the phone record | Slice 013 PRIV-3 |
| P-3 | The text of every notice version is stored and can be shown again | **Not built** — version is a constant in code | Slice 013 PRIV-2 |
| P-4 | A changed notice blocks app check-ins until the employee agrees again | Planned | Slice 013 US-42 |
| P-5 | "Remove this phone" withdraws consent and stops collection at once | Planned. HR blocking works today | Slice 013 SEC-22 |
| P-6 | **A way to mark attendance without photo or location** for anyone who declines or withdraws | **Not built.** The web check-in page also takes a photo and location | Consent gate; **product gap** |
| P-7 | Whatever the lawyer decides for past photos and coordinates on withdrawal (L-2) | **Not built** — the purge only removes photos older than the retention period | **Product gap** |
| P-8 | The "decline" screen | Planned (new screen named in the consent gate) | Consent gate |

### 5b. Needed for any customer

| # | Must be true | Status today | Source |
|---|---|---|---|
| P-9 | Slice 014 released: rate limits cannot be dodged, and no photo, location or name reaches error logs | In progress | Slice 013 R5, OPS-19, OPS-20 |
| P-10 | The security fixes of slices 010 and 008 (check-in row rules, photo access log, photo purge, review access rules) are released to production | **In code on the development branch, not on `main`** | Git check, 17 Sep 2026 |
| P-11 | A breach runbook, named contacts, and **one drill** that meets the 6-hour CERT-In clock | **Not built** | Feature map A5, I8 |
| P-12 | A way for employees to raise a privacy request or grievance, and for HR to track it to a deadline | **Not built** — handled by hand | Feature map A8, G3 |
| P-13 | A way to give an employee a copy of their data | **Not built** — no export | Feature map C5, G2 |
| P-14 | Retention and deletion for records other than photos, with legal hold, to the lawyer's periods (L-7) | **Not built** | Feature map A6 |
| P-15 | A written, tested procedure to return and delete a customer's data at contract end, including backup copies | **Not built** | DPA cl. 14 |
| P-16 | Sub-processor list complete (S-1 to S-3 answered) | **Unknown items remain** | DPA Annex 3 |
| P-17 | Third-party loads removed or contracted: OpenStreetMap tiles, unpkg.com, Nominatim | **Present** in driver and vendor portals and the delivery module | `www/driver-portal.html`, `www/vendor-portal.html`, `controllers/delivery_order.py` |
| P-18 | A short DPIA (written privacy risk check) for photo and location | **Not written** | Slice 013 Q-U8, C-5 |
| P-19 | The security annex re-checked on the signing date, with only "In place" rows presented as current | To do at signing | DPA Annex 2 |
| P-20 | The lawyer's review done, and both templates updated | Not started | Surbhi's decision, 17 Sep 2026 |

### 5c. Needed only for some customers

| # | Must be true | When | Status |
|---|---|---|---|
| P-21 | A Hindi (or other language) notice, translated and checked by fluent speakers | Before Hindi-first staff are asked to agree | Not written (Part D) |
| P-22 | A separate notice and legal basis for delivery drivers' continuous location tracking | Before any customer uses the delivery module with real drivers | **Not written.** Also: `portal_api.update_driver_location` lets any logged-in user write a location for any delivery order (it uses `ignore_permissions` and checks no role). That is a security issue for the engineer's backlog, outside these templates |
| P-23 | India-resident logs (CERT-In), or an India region | Before a regulated buyer, or if the lawyer says it binds us now | Not built |

---

## 6. What I could not verify

- **Production.** I did not look at the live server, its nginx file, its site settings, its
  backups or its logs. The production wall forbids it. Annex 2 rows marked "Not verified" need
  someone with access to check them.
- **Off-site backups, email provider, push notifications, India Compliance services** — the
  repository does not say whether they are turned on or who provides them.
- **Encryption at rest and two-factor sign-in** — not visible in the repository.
- **How long logs are kept** — not visible in the repository.
- **Contabo's contract terms** — not read.
- **Whether any notification under s.16(1) or order under Rule 15 has been issued** — none found
  on the pages I read; that is not the same as proof that none exists.
- **The Data Protection Board's current complaint route** — not checked.
- **State Shops and Establishments and wage-law retention periods** — not checked.

---

## 7. Sources read on 17 September 2026

Secondary sources that quote the official text. The lawyer should check against the official
Gazette text.

- DPDP Act 2023, s.6 (consent): https://www.dpdpa.com/dpdpa2023/chapter-2/section6.html
- DPDP Act 2023, s.7 (legitimate uses): https://www.dpdpa.com/dpdpa2023/chapter-2/section7.html
- DPDP Act 2023, s.8 (Fiduciary duties, processor contract, breach, erasure): https://www.dpdpa.com/dpdpa2023/chapter-2/section8.html
- DPDP Act 2023, s.11, s.12, s.13, s.14 (rights, grievance, nomination): https://www.dpdpa.com/dpdpa2023/chapter-3/section11.html · https://www.dpdpa.com/dpdpa2023/chapter-3/section12.html · https://www.dpdpa.com/dpdpa2023/chapter-3/section13.html
- DPDP Act 2023, s.16 (transfer outside India): https://www.dpdpa.com/dpdpa2023/chapter-4/section16.html
- DPDP Rules 2025, Rule 1 (commencement), Rule 3 (notice), Rule 6 (security), Rule 7 (breach), Rule 8 (erasure and one-year logs), Rule 14 (rights; 90 days), Rule 15 (transfer): https://www.dpdpa.com/dpdparules/rule1.html · rule3.html · rule6.html · rule7.html · rule8.html · rule14.html · rule15.html
- CERT-In Directions of 28 April 2022 (6-hour reporting, 180-day India logs, NTP), summary: https://www.internetsociety.org/resources/doc/2022/internet-impact-brief-india-cert-in-cybersecurity-directions-2022/ and https://trilegal.com/wp-content/uploads/2022/07/How-to-comply-with-CERT-Ins-new-six-hour-time-frame-to-report-cyber-incidents.pdf
- Hosting location and CERT-In gap: `.claude/context/security-compliance-baseline.md` §3a (verified 6 Sep 2026)

**One conflict found:** one secondary page gave 30 days for answering a grievance; the Rule 14(3)
text as quoted gives "a reasonable period not exceeding ninety days". The templates use the Rule
text and ask each customer to publish a shorter period.

**Timing note:** Rule 1 brings Rules 3 and 5 to 16 (notice, security, breach, rights, transfer)
into force 18 months after the Rules were published (published November 2025, so around May
2027). Sources differ on 13 or 14 November 2025. No duty in these templates is overdue today, and
there is no live customer — but customers will ask for these documents now.
