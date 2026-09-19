# Data Processing Agreement — TEMPLATE

> **I am not a lawyer. This is not legal advice.** This draft was written by Alvoraa's
> security and privacy engineer (an AI agent) for Surbhi, the interim compliance owner. It
> turns what the product actually does into contract words, so that a DPDP lawyer can
> correct it quickly. **It must not be sent to a customer or signed until a qualified
> Indian data-protection lawyer has reviewed it.** Every clause that needs legal judgement
> is marked `[LAWYER TO CONFIRM]`.

| | |
|---|---|
| Version | Draft 0.1 · 17 September 2026 |
| Status | For lawyer review. Not for use with customers |
| Prepared for | Surbhi (founder, interim compliance owner) |
| Law checked against | DPDP Act 2023 and DPDP Rules 2025 (sections and rules read on 17 Sep 2026 — sources in `README.md`) |
| Product facts checked against | Code on the local `dev` branch, 17 Sep 2026 (commit `9138251`), and the slice documents listed in `README.md` |

**How to read the marks in this document**

| Mark | Meaning |
|---|---|
| `{curly braces}` | A value to fill in for each customer or once for Alvoraa |
| `[LAWYER TO CONFIRM]` | A point of law or drafting that needs a lawyer's judgement |
| `[PRODUCT GAP]` | The clause describes something the product cannot fully do yet. Either the product is fixed before signing, or the clause is changed |
| **Drafting note** | An explanation for the lawyer. Delete before use |

---

## Parties

This Data Processing Agreement ("**DPA**") is made on {date} between:

1. **{Customer legal name}**, a company incorporated under {law}, with its registered office
   at {address} ("**Customer**"); and
2. **{Alvoraa contracting entity legal name}**, a {type of entity} with its registered office
   at {address} ("**Alvoraa**").

It forms part of the {name of main agreement, e.g. Subscription Agreement} dated {date}
between the same parties (the "**Main Agreement**").

> **Drafting note.** The legal entity that contracts as "Alvoraa" is not recorded anywhere I
> could read. The product documents mention AllAboutHR as the parent business, and the
> tenant set-up script uses a `kinexus.in` support address. Surbhi to confirm the entity.
> `[LAWYER TO CONFIRM]`

---

## 1. Words used in this DPA

1.1 **Act** means the Digital Personal Data Protection Act, 2023. **Rules** means the Digital
Personal Data Protection Rules, 2025. **Board** means the Data Protection Board of India.

1.2 **Data Fiduciary**, **Data Processor**, **Data Principal**, **personal data**,
**processing**, **consent** and **personal data breach** have the meanings given in the Act.

1.3 **Customer Personal Data** means personal data that Alvoraa processes on behalf of the
Customer in providing the Services.

1.4 **Services** means the Alvoraa platform and related support described in the Main
Agreement, including the web portal, the HR desk and (if the Customer turns it on) the
Alvoraa mobile attendance app.

1.5 **Sub-processor** means any third party that Alvoraa engages and that processes Customer
Personal Data.

1.6 **CERT-In Directions** means the directions issued by CERT-In on 28 April 2022 under
section 70B(6) of the Information Technology Act, 2000, as amended.

1.7 **Tenant** means the Customer's own separate site on the Alvoraa platform.

---

## 2. Roles

2.1 For Customer Personal Data, the **Customer is the Data Fiduciary** and **Alvoraa is the
Data Processor**. The Customer decides why and how its employees' personal data is
processed. Alvoraa processes it only to provide the Services, on the Customer's behalf.
`[LAWYER TO CONFIRM]`

2.2 Under section 8(1) of the Act, the Customer stays responsible for complying with the Act
for processing that Alvoraa does on its behalf. Alvoraa will do what this DPA says so that
the Customer can meet that duty.

2.3 **Outside this DPA.** Alvoraa is the Data Fiduciary for a small amount of data it
collects for its own purposes, for example: the Customer's billing and contract contacts,
people who contact Alvoraa sales, and people who visit Alvoraa's own website. That
processing is covered by Alvoraa's own privacy policy, not by this DPA.
`[LAWYER TO CONFIRM — also whether Alvoraa is a Fiduciary for any data linked to publishing
the mobile app under its own store account (for example, testers' email addresses in the
pilot, or data the app store gives the publisher). Open question Q-C4 in slice 013.]`

---

## 3. What is processed, and why

3.1 The subject matter, nature, purpose, duration, types of personal data and categories of
Data Principals are set out in **Annex 1**.

3.2 Alvoraa will process Customer Personal Data only for the purposes in Annex 1 and only
for as long as this DPA lasts, plus the deletion period in clause 14.

3.3 Alvoraa will not:
- sell Customer Personal Data;
- use it to train any artificial-intelligence model;
- use it for its own marketing or analytics about individuals;
- combine it with data from other customers, except anonymous, aggregated platform counts
  that contain no names, employee IDs or device IDs (for example, daily counts of app
  versions in use).

> **Drafting note.** The last point matches the product design (slice 013, PRIV-11:
> "counts leave the tenant, people do not"). Whether such counts are still "personal data"
> for very small tenants is a question for the lawyer. `[LAWYER TO CONFIRM]`

---

## 4. The Customer's responsibilities

4.1 The Customer will:

(a) decide and record the legal basis for each kind of processing (see clause 5 for the
mobile app) `[LAWYER TO CONFIRM]`;

(b) give its employees a notice that meets section 5 of the Act and Rule 3 of the Rules. A
template is available from Alvoraa, but the Customer is responsible for the final notice;

(c) publish the business contact details of the person who answers Data Principals'
questions, or its Data Protection Officer if it must have one (section 8(9));

(d) run a grievance process (section 8(10) and section 13) and name a grievance officer;

(e) set the retention settings in the Services (for example, the number of days check-in
photos are kept) to match its own retention policy and the law that applies to it;

(f) give user accounts and roles only to people who need them, remove access when people
leave, and protect its own passwords;

(g) not load personal data into the Services that the Services do not need — for example
Aadhaar numbers, or health information beyond what the Customer's HR process strictly
requires; and

(h) tell Alvoraa in writing if any sector law that applies to the Customer (for example, a
banking, insurance or government rule) requires the data to stay in India or needs extra
controls. See clause 10.

4.2 The Customer's instructions to Alvoraa must comply with the Act.

---

## 5. The mobile attendance app — consent

> **Drafting note.** Working position decided by Surbhi on 17 Sep 2026 ("Consent gate"):
> the mobile app may only be used by an employee who gives consent. Photo and location at
> check-in through the app rest on **consent under section 6 of the Act**. All other HR
> processing (profile, pay, leave, reviews) rests on **legitimate use for employment under
> section 7(i)**. This clause puts that position into the contract. The whole clause is
> `[LAWYER TO CONFIRM]`, in particular whether consent can be "free" in an employment
> relationship, and whether this clause should instead sit only in the notice.

5.1 **Scope.** This clause applies only if the Customer turns on the Alvoraa mobile
attendance app for any of its employees.

5.2 **What the app collects.** At the moment an employee presses Check In or Check Out: a
photo, the phone's location and its accuracy, and the time. When the employee sets up the
phone: the phone's model name, platform and app version. The app does not collect location
between check-ins and does not run in the background.

5.3 **Consent is the legal basis for the app.** The Customer relies on each employee's
consent under section 6 of the Act for the photo and location collected through the app.
`[LAWYER TO CONFIRM]`

5.4 **How consent is asked for and recorded.** The Services will:

(a) show the employee a short notice before the phone is set up, with a box the employee
must tick, reading "I agree", and a clear way to say no;

(b) not set up the phone, and not allow any check-in through the app, unless the employee
agrees;

(c) record each agreement with the date and time, the notice version, the language and the
phone, and keep earlier records when a new one is added;

(d) ask the employee to agree again, and stop app check-ins until they do, whenever the
notice changes.

`[PRODUCT GAP — specified in slice 013 but not built yet. Today the phone record holds only
one "consent version" and one "consent date" field, which a new agreement would overwrite.
The notice text of each version is not yet stored.]`

5.5 **Consent must be freely given.** The Customer will:

(a) give every employee who does not agree, or who later withdraws, another way to mark
attendance that does **not** need their photo or precise location; and

(b) not treat, pay or discipline an employee differently because they did not agree or
withdrew.

`[LAWYER TO CONFIRM — whether this is enough for consent to be "free" under section 6(1),
and whether the alternative can be the Customer's existing method (register, reception
device, HR marking attendance).]`

`[PRODUCT GAP — the only other check-in path in the product today, the web check-in page,
also takes a photo and location. The product does not yet offer a no-photo, no-location
path for someone who declines, other than HR recording attendance by hand.]`

5.6 **Withdrawal.** An employee can withdraw consent at any time, as easily as they gave
it, by pressing "Remove this phone" in the app's settings or by asking HR, who can block the
phone. Within {X hours / the next request} of a withdrawal, Alvoraa will stop collecting
photos and location from that phone (section 6(4) and 6(6)).

`[PRODUCT GAP — "Remove this phone" is designed (slice 013) but not built. HR blocking a
phone exists today.]`

5.7 **What happens to data already collected when consent is withdrawn.** On withdrawal:
- the attendance record (the time of each punch) stays, as an employment record under
  section 7(i); and
- the photos and exact locations collected through the app are **{deleted within X days of
  withdrawal / kept until the Customer's normal photo retention period ends}**.

`[LAWYER TO CONFIRM — section 8(7) says data is to be erased when consent is withdrawn,
unless keeping it is needed to comply with a law. The current product design keeps photos
until the normal retention period runs out (default 90 days). That may not be enough.]`

`[PRODUCT GAP — there is no function today that deletes one employee's photos and exact
coordinates when they withdraw. The daily purge only removes photos older than the
retention period.]`

5.8 **Employees under 18.** The Customer will not turn the app on for any employee under
18 years of age without first agreeing the process with Alvoraa in writing.
`[LAWYER TO CONFIRM — section 9 (children) and whether apprentices or young workers are
likely in customers' workforces.]`

---

## 6. Processing only on the Customer's instructions

6.1 Alvoraa will process Customer Personal Data only on the Customer's documented
instructions. The instructions are:
(a) this DPA and the Main Agreement;
(b) the settings the Customer's authorised users choose in the Services; and
(c) any further written instructions agreed by both parties.

6.2 If a law requires Alvoraa to process Customer Personal Data in another way, Alvoraa will
tell the Customer first, unless that law forbids telling.

6.3 Alvoraa will tell the Customer promptly if, in its opinion, an instruction breaks the
Act. Alvoraa is not required to give legal advice. `[LAWYER TO CONFIRM]`

---

## 7. Alvoraa's people

7.1 Alvoraa will make sure that everyone who can access Customer Personal Data:
(a) is bound by a written duty of confidentiality that continues after their work ends;
(b) accesses it only when needed to provide, support or secure the Services; and
(c) has been told about their duties under this DPA.

7.2 Alvoraa will keep access for its own staff to the smallest group of named people it
can.

7.3 Alvoraa will keep a record of actions its operators take on a Customer's Tenant through
the Alvoraa control plane (for example, creating, suspending or changing a Tenant).

> **Drafting note.** Clause 7.3 is true in code: the control plane writes an "Alvoraa Tenant
> Access Log" row, which nobody can edit or delete through the desk. **It does not record
> direct server access** (for example, an engineer connecting to the server to run a
> command). `[PRODUCT GAP]` Either add a record of direct server access, or narrow the
> promise to what is recorded. Also: Alvoraa has no written confidentiality or security
> training records for staff that I could find. Surbhi to confirm.

---

## 8. Security

8.1 Alvoraa will take reasonable security safeguards to protect Customer Personal Data, as
section 8(5) of the Act and Rule 6 of the Rules require. The measures in place are listed in
**Annex 2**.

8.2 Alvoraa will not reduce the overall level of security during the term of this DPA.
Alvoraa may replace a measure with one that protects at least as well.

8.3 The Customer is responsible for the security settings it controls: which users have
which roles, password rules, two-factor sign-in (if the Customer turns it on), and removing
access for leavers.

> **Drafting note.** Annex 2 separates what exists in code from what is planned. Planned
> items must not be presented as existing. If a customer asks for a planned item as a
> contract promise, add a date and make it a commitment only when the engineering plan
> supports it.

---

## 9. Sub-processors

9.1 The Customer gives Alvoraa general permission to use the Sub-processors listed in
**Annex 3**.

9.2 Before adding or replacing a Sub-processor, Alvoraa will tell the Customer at least
**{30} days** in advance, by email to {Customer privacy contact} and on {page or place in
the product}.

9.3 The Customer may object in writing within that period, on reasonable data-protection
grounds. The parties will then discuss it in good faith. If they cannot agree, the Customer
may end the affected part of the Services and receive a refund of prepaid fees for the
unused period. `[LAWYER TO CONFIRM]`

9.4 Alvoraa will put in place a written contract with each Sub-processor with data
protection duties that are no less protective than those in this DPA, as far as they apply
to the service that Sub-processor provides. `[LAWYER TO CONFIRM — the hosting provider's
standard terms may not be negotiable; state what is realistic.]`

9.5 Alvoraa remains responsible to the Customer for its Sub-processors' performance of those
duties.

> **Drafting note.** The Sub-processor register in the product (feature map A9) is **not
> built**. Notice will be given by email until it is. `[PRODUCT GAP]`

---

## 10. Where the data is stored, and transfers outside India

10.1 **Storage location.** Customer Personal Data, including backups on the same server and
the application logs, is stored in **France**, on servers rented from the hosting provider
named in Annex 3. Alvoraa's staff and support may access it from **India**.

10.2 **Transfer outside India.** Under section 16(1) of the Act, the Central Government may
restrict transfers of personal data to countries it notifies. On {date checked}, Alvoraa was
not aware of any notification that restricts transfers to France. Rule 15 of the Rules
applies requirements that the Central Government may set by order about making personal
data available to a foreign State. `[LAWYER TO CONFIRM — whether any order under Rule 15 or
notification under section 16(1) exists on the signing date, and what the clause should
promise if one is issued later.]`

10.3 **If the rules change.** If a notification or order restricts the transfer, Alvoraa will
tell the Customer promptly and the parties will agree how to comply, which may include
moving the Customer's Tenant to a region in India. `[LAWYER TO CONFIRM — who pays.]`

10.4 **Sector laws.** Section 16(2) keeps in force any Indian law that gives stricter
protection or restriction on transfers. If such a law applies to the Customer (clause
4.1(h)), the Services as hosted today may not be suitable, and the Customer must tell
Alvoraa before signing.

10.5 **Moving region.** Each Tenant is a separate site, so a Tenant can be hosted in another
region on request, on terms agreed in writing. `[Commercial — Surbhi to decide. No India
region exists today.]`

10.6 **Logs under the CERT-In Directions.** The CERT-In Directions require ICT system logs to
be kept for a rolling 180 days within India. Today Alvoraa's logs are kept in France.
`[LAWYER TO CONFIRM — whether this binds Alvoraa, the Customer, or both, and whether it
should be disclosed here. PRODUCT GAP — India-resident log storage is not built; the founder
decided on 6 Sep 2026 to keep hosting in France and build an India region when a customer
needs one.]`

10.7 **Foreign law.** `[LAWYER TO CONFIRM — whether storage with an EU hosting provider
brings EU law (for example, the GDPR, or access by EU authorities) into play for the
Customer or for Alvoraa, and whether that should be disclosed. The founder has not yet
confirmed whether Alvoraa processes data of people in the EU.]`

---

## 11. Helping with Data Principals' rights and grievances

11.1 If an employee or other Data Principal contacts Alvoraa directly about Customer Personal
Data, Alvoraa will not answer the request itself. Within **{5} working days** it will send the
request to the Customer and tell the person that it has done so. `[LAWYER TO CONFIRM]`

11.2 Alvoraa will help the Customer respond to requests to access, correct, complete, update
or erase personal data, to withdraw consent, to nominate another person, and to grievances
(sections 11 to 14 of the Act and Rule 14), by:
(a) providing features in the Services, where they exist (see the table below); and
(b) where a feature does not exist, doing the work on the Customer's written request within
**{10} working days**, so the Customer can answer within the period it has published, which
must not be more than 90 days (Rule 14(3)).

| Request | What the product can do today | Status |
|---|---|---|
| See own data | Employees see their own profile, attendance, leave, payslips and review pages in the portal. There is no single "download all my data" export | Partial `[PRODUCT GAP]` |
| See what the app records | "What this app records" screen with the notice version and date agreed | Planned (slice 013) |
| Correct attendance | Attendance correction request with approval | In code on the development branch; not yet released |
| Correct other data | HR edits the record. No employee-initiated request for other fields | Manual `[PRODUCT GAP]` |
| Erase | Check-in photos are deleted after the retention period, unless on hold. No other automatic deletion. Other erasure is done by Alvoraa by hand on request | Partial `[PRODUCT GAP]` |
| Withdraw app consent | HR can block a phone today. "Remove this phone" by the employee is planned | Partial |
| Grievance | No in-product entry point. Handled through the Customer's own process | Not built `[PRODUCT GAP]` |
| Nominate | Handled through the Customer's own process | Not built |
| Who looked at my check-in photo | Photo views by anyone other than the employee are logged | In code on the development branch |

`[LAWYER TO CONFIRM — sections 11(1) and 12(1) give the access and correction/erasure rights
for data processed on consent (including section 7(a)). It is not clear to me whether they
apply as statutory rights to data processed under section 7(i). The DPA should help the
Customer either way.]`

11.3 Alvoraa may charge for help under 11.2(b) that goes beyond {X hours per year}, at the
rates in the Main Agreement. `[Commercial — Surbhi to decide.]`

---

## 12. Personal data breaches

> **Drafting note — the clocks, as I understand them. `[LAWYER TO CONFIRM all of this.]`**
>
> | Clock | Who has the duty | To whom | When |
> |---|---|---|---|
> | DPDP section 8(6), Rule 7(1) | Data Fiduciary (the Customer) | Each affected Data Principal | Without delay |
> | DPDP Rule 7(2)(a) | Data Fiduciary (the Customer) | The Board | Without delay |
> | DPDP Rule 7(2)(b) | Data Fiduciary (the Customer) | The Board, detailed report | Within 72 hours of becoming aware, or longer if the Board allows |
> | CERT-In Directions | Service providers, intermediaries, data centres, body corporates and government organisations — so possibly **both** Alvoraa and the Customer | CERT-In | Within 6 hours of noticing or being told of the incident |
>
> The Customer cannot meet a "without delay" duty unless Alvoraa tells it fast. The
> 6-hour CERT-In clock is the tightest. **Honest position today:** Alvoraa has no breach
> workbench, no written incident runbook that has been tested, and no on-call rota
> (feature map A5, I8). Do not sign a short notice period until those exist, or sign a
> period the team can really meet.

12.1 **Telling the Customer.** Alvoraa will tell the Customer without undue delay after
becoming aware of a personal data breach affecting Customer Personal Data, and in any case
within **{6 / 12 / 24} hours**. `[LAWYER TO CONFIRM the period.]` The first notice will go to
{Customer security contact} by {email and phone} and will include what is known at that
time. Alvoraa will send updates as it learns more.

12.2 **What the notice will contain,** as far as known: what happened and when; when Alvoraa
became aware; the kinds and approximate number of people and records affected; the likely
consequences; what Alvoraa has done and will do to contain it; what affected people can do
to protect themselves; and a contact person at Alvoraa. This matches the content the
Customer must give under Rule 7.

12.3 **Who tells whom.**
(a) The Customer decides whether and how to inform affected Data Principals and the Board
under the Act, and sends those intimations. Alvoraa will not contact the Customer's employees
or the Board about the breach unless the Customer asks it to in writing or the law requires
it.
(b) Alvoraa will give the Customer the information and help it reasonably needs for the
intimation to Data Principals, the intimation to the Board and the 72-hour report.
(c) For a cyber incident on systems Alvoraa operates (for example, the servers, the platform
or Alvoraa's own accounts), **Alvoraa will report to CERT-In** within the time the CERT-In
Directions set and will tell the Customer at the same time. For an incident on systems the
Customer operates (for example, its own staff's devices or accounts), **the Customer reports
to CERT-In**. `[LAWYER TO CONFIRM — whether both parties must report the same incident, and
whether hosting in France changes Alvoraa's duty.]`

12.4 Alvoraa will keep a record of every personal data breach affecting Customer Personal
Data: the facts, the effects and the steps taken.

12.5 Telling the Customer about a breach is not an admission of fault or liability.

---

## 13. Risk assessments

13.1 Alvoraa will give the Customer reasonable information about the Services to help the
Customer carry out any data protection impact assessment or audit the Customer does or must
do.

> **Drafting note.** Alvoraa's own recommendation (slice 013, Q-U8) is a short written privacy
> risk check (DPIA) for photo and location capture before the first real customer uses the
> app. Not yet written.

---

## 14. Retention during the contract, and return and deletion at the end

14.1 **During the contract,** Customer Personal Data is kept as the Customer's settings and
instructions say. Where the Services have no setting for a kind of data, it is kept until the
Customer deletes it or the contract ends.

> **Drafting note.** Today only check-in photos have an automatic retention setting (default
> 90 days, with a legal-hold flag on each check-in). An organisation may set "0" to keep photos
> for ever. There is no retention engine for attendance, leave, pay, reviews, documents or
> logs (feature map A6). `[PRODUCT GAP]`

14.2 **Export.** For **{30} days** after the Main Agreement ends, the Customer may ask for a
copy of its Customer Personal Data. Alvoraa will provide it in a common machine-readable
format {a full database backup of the Tenant and its files / CSV exports per record type}.
`[Surbhi to decide the format. A full site backup exists as a function; a customer-friendly
export does not.]`

14.3 **Deletion.** After that period, Alvoraa will delete the Customer's Tenant, including its
database and files, within **{30} days**. Copies in backups will be deleted or overwritten
within **{X} days** after that, as backups rotate. `[PRODUCT GAP — there is no written deletion
procedure, and I could not confirm how long backup copies are kept on the server or off
it.]`

14.4 On request, Alvoraa will confirm deletion in writing.

14.5 Alvoraa may keep Customer Personal Data after the end only where an Indian law requires
it, only for as long as that law requires, and only for that purpose. It will keep such data
confidential and will not otherwise process it. `[LAWYER TO CONFIRM — including the logs that
Rule 8(3) says must be kept for at least one year from the date of processing, and whether that
duty sits with Alvoraa after the contract ends.]`

---

## 15. Records, information and audits

15.1 Alvoraa will keep records of the processing it does for the Customer, including the logs
described in Annex 2. `[LAWYER TO CONFIRM — Rule 6(1)(e) and Rule 8(3) require logs to be kept
for one year. Check whether Alvoraa's logs are kept that long today — not verified.]`

15.2 Once a year, and after any personal data breach, Alvoraa will answer the Customer's
reasonable written security and privacy questionnaire.

15.3 **Certifications.** On the date of this DPA, Alvoraa holds **no** independent security
certification (such as ISO/IEC 27001 or a SOC 2 report). Alvoraa will tell the Customer if it
obtains one. `[Keep this sentence true. Remove it only when a certificate exists.]`

15.4 **Audit.** If the answers under 15.2 are not enough to show that Alvoraa meets this DPA,
the Customer (or an independent auditor bound by confidentiality, who is not a competitor of
Alvoraa) may audit Alvoraa's compliance, no more than once a year, with at least {30} days'
written notice, during business hours, at the Customer's cost. The audit must not give
access to other customers' data. `[LAWYER TO CONFIRM]`

15.5 Alvoraa will not allow any audit to include probing or testing the live platform without
a separate written agreement, because the platform is shared.

---

## 16. Liability and indemnity

16.1 {Placeholder. Link to the liability clause of the Main Agreement, or set a separate cap
for data protection claims.} `[LAWYER TO CONFIRM]`

16.2 {Placeholder for indemnities: for example, each party for penalties and third-party claims
caused by its own breach of this DPA or the Act.} `[LAWYER TO CONFIRM]`

> **Drafting note.** Penalties under the Act fall on the Data Fiduciary and can be very large.
> Customers will likely ask Alvoraa to indemnify them for breaches Alvoraa causes, without a
> cap. The lawyer should advise on a cap, what is excluded from it, and whether Alvoraa's
> insurance (if any — none that I know of) covers it.

---

## 17. Term, order of documents, changes in law

17.1 This DPA lasts as long as Alvoraa processes Customer Personal Data for the Customer.

17.2 If this DPA and the Main Agreement conflict about personal data, this DPA wins.
`[LAWYER TO CONFIRM]`

17.3 If the Act, the Rules or the CERT-In Directions change, or the Board issues guidance
that affects this DPA, the parties will agree the changes needed in good faith.

---

## 18. Governing law and disputes

18.1 This DPA is governed by the laws of **India**.

18.2 {Placeholder: courts at {city} have exclusive jurisdiction / disputes go to arbitration
seated at {city} under the Arbitration and Conciliation Act, 1996, with {number} arbitrator(s),
in English.} `[LAWYER TO CONFIRM]`

---

## Signatures

| For the Customer | For Alvoraa |
|---|---|
| Name: | Name: |
| Title: | Title: |
| Date: | Date: |
| Signature: | Signature: |

---

## Annex 1 — Details of the processing

### A1.1 Subject matter and duration

Providing the Alvoraa platform to the Customer for the term of the Main Agreement, plus the
export and deletion period in clause 14.

### A1.2 Nature of the processing

Collection through the portal, the desk, the mobile app and imports; storage; organisation;
retrieval and display to authorised users; calculation (for example attendance totals and
review scores); sending notifications; backup; deletion.

### A1.3 Purposes

Running the Customer's HR processes: employee records, attendance, leave, payroll records and
payslips, performance goals and reviews, employee documents, and the related security,
support and audit of the platform.

### A1.4 Categories of Data Principals

| Category | When it applies |
|---|---|
| The Customer's current and former employees | Always |
| People named in an employee's record (emergency contacts, family members, nominees) | If the Customer records them |
| The Customer's users of the platform (HR staff, managers, leaders, administrators) | Always |
| Field workers using the mobile attendance app | If the Customer turns on the app |
| Contractors, delivery partners and drivers | If the Customer uses the delivery or driver modules |
| Job applicants | If the Customer uses recruitment and screening forms |
| Vendor portal users | If the Customer uses the vendor portal |

> **Drafting note.** The employee privacy notice template covers employees only. Job
> applicants, delivery partners and vendor users need their own notices if the Customer uses
> those modules. `[LAWYER TO CONFIRM]`

### A1.5 Types of personal data

"Module" means a part of the product the Customer may or may not use.

| Area | Personal data (examples from the product) | Notes |
|---|---|---|
| **Identity and job** | Name, employee ID, photo, date of birth, gender, contact details, company, branch, department, designation, manager, date of joining, date of leaving, status | Standard Frappe HR employee record |
| **Sensitive fields in the employee record** | PAN, bank account number, passport number, cost to company (CTC), health details, blood group | Held only if the Customer fills them. Extra field-level restrictions exist in the framework for some (CTC, PAN, bank); masking and field encryption are **not built** |
| **Attendance** | Check-in and check-out times, attendance status, late arrival and early exit flags, working hours, attendance correction requests with reasons | |
| **Attendance by app or web check-in** | **Photo taken at the moment of check-in**; **precise location (latitude, longitude, accuracy) at that moment**; phone clock time; offline flag; the phone record (model name, platform, app version, status, block reason, who activated or blocked it); notice agreement records; record of who viewed a check-in photo | Photo and location are collected **only at the moment of a punch**. No face matching. See clause 5 |
| **Leave** | Leave type, dates, balance, reason written by the employee, approver | The reason may reveal health information |
| **Pay** | Salary slips (payslips), salary components, loss-of-pay days and amounts, deductions, additional salary | The product posts to payroll and shows payslips |
| **Performance** | Goals, KPIs, evidence submitted (including files), self-review text and ratings, manager ratings and comments, potential rating, calibration notes, review history and frozen review copies, invited reviewer comments | Decision-bearing records. See A1.6 |
| **Documents** | Employee documents (type, number, issue and expiry dates, file, who received and verified it) and policy acknowledgements | Files may contain ID proof |
| **Leader totals** | Totals of attendance and leave for a branch, department or company, with small groups hidden | Counts, not names. Still treated as personal data |
| **System and security records** | User accounts, roles, sign-in records, change history of records, refused-access records (user, endpoint, record name, time), control-plane access records | |
| **Delivery and driver module** | Delivery partner name, phone, email, PAN, UPI ID, driving licence number, vehicle; **location, speed and heading sent from the driver's browser during deliveries**; speeding flags; ratings | Only if used. **This is continuous tracking during a delivery, unlike the attendance app.** Needs its own basis and notice `[LAWYER TO CONFIRM]` |
| **Recruitment module** | Applicant details and screening answers (for example experience, current employer, expected monthly CTC, availability) | Only if used |

**Data the Services do not collect by design:** in the attendance app — IMEI, Android ID,
serial number, advertising ID, phone number, SIM details, contacts, installed apps, gallery
contents, and location outside the moment of a punch.

### A1.6 How long data is kept

| Data | Kept for | Who sets it |
|---|---|---|
| Check-in photos | {Default 90 days}, then deleted automatically, unless the check-in is on hold | Customer setting (0 = keep for ever `[LAWYER TO CONFIRM whether "for ever" should be allowed]`) |
| Attendance records, including location at punch | {Customer's policy} — no automatic deletion today | Customer `[PRODUCT GAP]` |
| Phone records and app agreement records | While any attendance record made by that phone exists (proposed) | Proposed in slice 013 `[LAWYER TO CONFIRM]` |
| Leave, pay, documents | {Customer's policy} — no automatic deletion today | Customer `[PRODUCT GAP]` |
| Performance reviews and review copies | {Customer's policy}. Treated as decision records: no role can delete them through the product | Customer `[LAWYER TO CONFIRM the boundary between erasure and keeping a defensible record]` |
| Logs | At least 1 year (Rule 6(1)(e), Rule 8(3)) | Alvoraa `[Not verified that logs are kept this long today]` |
| All Customer Personal Data after the contract ends | Clause 14 | — |

---

## Annex 2 — Security measures

**Status words used below**

| Status | Meaning |
|---|---|
| **In place** | Exists in the code or configuration that runs the platform today, as far as I could check from the repository |
| **In code, not released** | Built on the development branch; not yet released to production |
| **Local only** | Built on a developer's machine; not yet shared to the development branch |
| **Planned** | Specified in a slice, not built |
| **Not built** | A known gap with no slice yet |
| **Not verified** | May exist, but I could not check it without access I do not have (for example, production) |

> **Drafting note.** Before sending this Annex to a customer, remove every row that is not
> "In place", or keep it visibly marked as planned with no date promised. **Never present a
> planned row as a current control.** Re-check every row on the signing date.

| # | Area | Measure | Status | Evidence |
|---|---|---|---|---|
| S1 | Tenant separation | Each customer is a separate site with its own database | In place | `deploy/provision_tenant.sh` (`bench new-site` per tenant) |
| S2 | Tenant separation | Automated test that proves one tenant cannot read another's data | Not built | Compliance feature map I2 |
| S3 | Access control | Role-based permissions (Employee, manager, HR User, HR Manager, System Manager) from the Frappe framework | In place | Framework |
| S4 | Access control | Check-in records and photos: an employee sees their own; a manager sees their direct reports'; HR sees all; a user with no employee record sees none | In code, not released | `field_checkin.py` `checkin_query_conditions`, `checkin_has_permission` |
| S5 | Access control | Performance reviews: stage rules, no self-rating or self-approval, pay amounts hidden from managers | In code, not released (partly local only) | Slice 010 |
| S6 | Access control | Leader totals only, with small groups hidden so individuals cannot be picked out | Local only | Slice 012 |
| S7 | Access control | Two-factor sign-in | Not verified (the framework supports it; I could not confirm it is on) | — |
| S8 | Encryption in transit | HTTPS with TLS 1.2 and 1.3; plain HTTP redirected to HTTPS | In place in the repository's web server config. **Live config not verified** | `deploy/nginx.conf` |
| S9 | Encryption in transit | HSTS header (tells browsers to use HTTPS only) | Not built in the repository copy | `deploy/nginx.conf` |
| S10 | Encryption at rest | Disk or database encryption | Not verified — **do not claim** | — |
| S11 | Encryption at rest | Password-type fields (for example stored credentials) encrypted with a per-site key | In place (framework behaviour) | Framework |
| S12 | Secrets | App device secrets and set-up codes stored only as hashes | Device secret hash: in code, not released. Set-up codes: planned | Slices 008, 013 |
| S13 | File privacy | Check-in photos stored as private files, not public links | In code, not released | `field_checkin.py` (`is_private: 1`) |
| S14 | Access logs | Record of who viewed a check-in photo (other than the employee) | In code, not released | `log_photo_view`, "Alvoraa Photo Access Log" |
| S15 | Access logs | Record of refused access attempts (user, endpoint, record, time; no personal content) | In code, not released | `hrms/alvoraa_hr_core/access.py` `log_refusal` |
| S16 | Access logs | Record of Alvoraa operator actions on tenants through the control plane; rows cannot be edited or deleted through the desk | In place | `tenant_api.py` `_log_tenant_access` |
| S17 | Access logs | Record of direct server access by Alvoraa staff | Not built | — |
| S18 | Change history | Change history on key records (for example phone records) | Partial — not on every record type (for example KPI has none) | Doctype settings |
| S19 | Log retention | Logs kept at least 1 year | Not verified | Rules 6(1)(e), 8(3) |
| S20 | Log residency | ICT logs kept 180 days in India (CERT-In) | Not built — logs are in France | Baseline §3a |
| S21 | Time sync | Server clock synchronised to NIC time server | In place (since 6 Sep 2026) | Baseline §3a |
| S22 | Retention | Automatic deletion of check-in photos after the organisation's retention period, with a per-check-in legal hold | In code, not released | `purge_old_checkin_photos` |
| S23 | Retention | Retention and deletion for all other data, with legal hold | Not built | Feature map A6 |
| S24 | Backups | Backup of all tenant sites, with files, before every production deployment | In place | `.github/workflows/deploy.yml` |
| S25 | Backups | Off-site copy of backups | Not verified (runs only if a storage bucket is configured) | `.github/workflows/deploy.yml` |
| S26 | Backups | Regular scheduled backups, backup encryption, and a tested restore | Not verified / restore drill not done | Feature map I7 |
| S27 | Vulnerability management | Container image scanned for known vulnerabilities on every build | In place | `.github/workflows/build-image.yml` (Trivy) |
| S28 | Secure development | Automated tests run in CI; code review before release | In place | `.github/workflows/ci.yml`; change process |
| S29 | Secure development | CI gates: permission test suite, cross-tenant suite, counter for permission bypasses, scan for personal data in logs, secret scan | Not built | Feature map I1–I4; slice 013 SEC-23 |
| S30 | Abuse protection | Rate limits on attendance endpoints | In code, but can be bypassed until slice 014 is released | Slice 013 R5, slice 014 |
| S31 | Logs hygiene | No photo, location or name written to error logs | Known problem, being fixed in slice 014 | Slice 013 OPS-20 |
| S32 | Minimisation | App collects no device identifiers, no background location; no face matching; no photo sent to any third party or model | Web check-in: in code, not released. App: planned with CI checks | Slices 008 PRIV-11, 013 SEC-20, PRIV-1 |
| S33 | Admin access | Server administration only over a private network, not the public address | In place as practice. Not verified in code | Operations note |
| S34 | Incident response | Breach workbench, written runbook, drill before first customer | Not built | Feature map A5, I8 |
| S35 | Certifications | ISO/IEC 27001, SOC 2 | None | — |

---

## Annex 3 — Sub-processors

**Status on 17 September 2026. Items marked "Unknown" must be answered before this Annex is
used.**

| Sub-processor | What it does | Personal data it can reach | Location | Status |
|---|---|---|---|---|
| **Contabo GmbH** | Server hosting (compute and storage) for every tenant, their backups on the server and the logs | All Customer Personal Data | Lauterbourg, **France** (measured 6 Sep 2026) | **Confirmed** (baseline §3a). Contract terms with Contabo not reviewed `[LAWYER TO CONFIRM]` |
| **Off-site backup storage** (Amazon Web Services S3, if configured) | Copy of pre-deployment backups | All Customer Personal Data | **Unknown** region | **Unknown** whether it is configured. The deploy workflow syncs to S3 only if a bucket is set. Surbhi to confirm |
| **Email delivery provider** (SMTP relay) | Sends notification emails (for example approvals, alerts to HR) | Names, email addresses, and the content of notifications | **Unknown** | **Unknown** provider. The deployment example names an "SMTP relay" without a provider |
| **Google Firebase App Distribution** | Sends test builds of the Android app to named pilot testers | Testers' email addresses and install records | **Unknown** (Google) | **Pilot only.** On Surbhi's own Google account (slice 013 decision). Not for customer employees' HR data. Whether Alvoraa is a Fiduciary rather than a Processor for this is open (clause 2.3) |
| **Push notification relay** (Frappe push relay and Google Firebase Cloud Messaging) | Phone and browser push notifications from the Frappe HR mobile web app | Notification text, device tokens | **Unknown** | **Unknown** whether turned on. The upstream Frappe HR app includes the code |
| **India Compliance app services** | GST and other Indian compliance lookups, if the optional app's online services are used | Company tax details; possibly PAN | **Unknown** | **Unknown.** The app is installed only if selected at tenant set-up |

**Third parties that receive data but are not contracted Sub-processors today** — these need a
decision (remove, self-host, or add to this list):

| Third party | What it receives | Where in the product | Recommendation |
|---|---|---|---|
| OpenStreetMap map tile servers | The user's IP address and the map area being viewed (which can show where a driver is) | Driver portal and vendor portal maps | Self-host map assets or use a contracted map provider `[PRODUCT GAP]` |
| unpkg.com (a public code delivery network) | The user's IP address and browser details | Driver portal, vendor portal, one front-end page | Bundle the Leaflet library locally `[PRODUCT GAP]` |
| OpenStreetMap Nominatim (address lookup) | Delivery addresses typed into the delivery module | `controllers/delivery_order.py` | Contracted geocoder or remove `[PRODUCT GAP]` |

**Not Sub-processors** (no Customer Personal Data), to be confirmed:
- GitHub — source code, automated tests on invented data, and container images.
- Let's Encrypt — website certificates.
- Tailscale — private network for server administration. `[Confirm whether admin traffic that
  carries personal data passes through its relays.]`
- Bitwarden — stores Alvoraa's own passwords and app signing key backup.

---

*End of template.*
