# How long we keep review records, and how we track a driver's location

## Two proposals for legal review

| | |
|---|---|
| **For** | Alvoraa's external legal reviewer — an Indian data-protection lawyer or company counsel |
| **From** | Alvoraa's security and privacy engineer, for Surbhi (founder, interim compliance owner) |
| **Date** | 18 September 2026 |
| **Status** | **A proposal for your review. It is not legal advice, and nothing in it has been settled.** We are not lawyers. Where an answer turns on a point of law we have said so and asked you a question with our suggested answer, so you can agree or correct rather than draft. |
| **What we need back** | Answers to the 14 numbered questions in sections 1.4 and 2.5, and a mark-up of the two retention tables (1.2 and 2.2) and the four draft notices. |
| **Why now** | No customer is live yet. Every table described here is empty, so today we can still choose the rule instead of explaining a past choice. That freedom ends on the day the first customer switches either feature on. |
| **Companion documents** | A draft employee privacy notice and a draft data-processing agreement were prepared for you on 17 September 2026. This paper answers the two open retention questions those drafts left blank, and adds the driver module, which the employee notice deliberately does not cover. |
| **Working position we have used** | The **customer company is the Data Fiduciary**; **Alvoraa is the Data Processor**. Most HR processing rests on **legitimate use for employment, section 7(i)**. Photo and precise location taken through the attendance app rest on **consent, section 6**. This position was set by the founder on 17 September 2026 and is itself open to your correction. |

Everything stated below about what the product does was re-checked against the source code
on 18 September 2026. Where we could not verify something, we say so.

---

## Summary — what we are asking you to approve

**Question 1 — performance review records.**
When a review cycle opens, the system takes a frozen copy of every goal and measure the
person is judged on, so the numbers cannot move mid-review. Those copies then collect the
manager's rating and comments, an overall rating, a **"potential" rating the employee never
sees**, the reason if an item is taken out of the review, and the notes that let us
reconstruct the decision later. **Today nothing is ever erased.** Deletion is blocked by
design, for every role, and there is no retention setting and no deletion job. That was the
safe short-term choice, and it is not a lawful long-term one.

*Our proposal:* full detail for **5 years** from the date the cycle closes; then reduce to a
short decision summary for a further **3 years**; then erase. The unseen **potential rating
erased after 24 months** or on exit, whichever is sooner. A legal hold that stops erasure
while a grievance, claim or investigation is open, and for 3 years after it closes.

**Question 2 — driver location.**
The driver portal records a driver's position, speed and heading **every 10 seconds** while a
delivery is open, building a minute-by-minute trail. Tracking starts automatically when the
driver opens an active delivery. There is **no notice, no consent step, no retention rule, no
deletion job and no setting**. By contrast, an attendance check-in photograph is deleted after
90 days by default, with a hold for disputes. So the product deletes a photograph of a face
after 90 days and would keep a movement history of the same person for ever.

*Our proposal:* the detailed trail kept **30 days** from the delivery date, then reduced to a
per-delivery summary kept **12 months** for pay and billing, then erased. Derived
"driving-behaviour" judgements (harsh braking, speeding flags) **not stored at all**. Tracking
confined by the server to an open delivery assigned to that driver, inside a shift window, with
notice before the first point is recorded and a visible indicator throughout. **No tracking
outside working hours** — the app stops and the server refuses.

**One correction to what you may have been told.** We were told the safety scoring that turned
driving telemetry into a pay recommendation and an automatic written warning had been deleted.
Half of that is right. The **telemetry inputs are genuinely gone** from the code — we verified
that the queries were deleted, not disabled. But the scorecard still produces an **automatic
pay-increment recommendation and an automatic "written warning" flag** for the bottom
performance tier; it is now driven by on-time percentage, customer ratings, human-recorded
safety incidents and attendance rather than by the phone's sensors. An automated step that
flags a warning against a named worker is still an automated decision about a person, and we
flag it for you at question 13 rather than leave it implied.

---

# Part 1 · Performance review records

## 1.1 What we do today, stated honestly

| | |
|---|---|
| **What is copied** | When a review cycle is generated, each goal and each measure the person is judged on is copied onto the review record: its title, description, target, baseline, weight, period, and the result achieved. |
| **What the copy then collects** | The employee's own rating and comment; the manager's rating and comment; who rated and when; the numbers the rating was given on (so a later change to the numbers can be flagged to the rater); an overall rating; a **potential rating and comment, which the employee is never shown**; the identity of anyone who removed an item, when, at what stage, and **why**; and the record of any definition change agreed in the review and written back afterwards. |
| **Why the copy exists** | So a rating can be explained and defended later — in a grievance, a promotion dispute or a termination challenge — against the numbers and definitions that actually applied at the time, not against later ones. |
| **How long it is kept** | **For ever.** There is no retention period, no setting, and no deletion job anywhere in this part of the product. |
| **Can anything delete it** | **No.** The review record refuses deletion once it holds copies — through the admin screens, through the API, and for the highest-privileged account. That was our own deliberate decision, recorded as "erasure waits for counsel". |
| **What an employee sees today** | Their own goals and results; their own self-rating; the overall rating and manager feedback from the "employee final review" stage onwards. They are **not** shown the potential rating, internal manager notes, calibration notes or rating-change flags. When an item is removed from their review they are shown **the item's label, the date, and the reason**, at the final stage. |
| **Who can switch anything** | Nobody. There is nothing to switch. |
| **What is missing, plainly** | No retention rule, no deletion job, no legal-hold mechanism, no way to give an employee a copy of their own data, and no workflow for a request to see, correct or erase. All four are unbuilt. |

## 1.2 Our proposal

Concrete enough to build. Every number is a proposal, and each is a number you can change.

| # | Record | Clock starts | Keep in full | Then | Then |
|---|---|---|---|---|---|
| A | The review record: copied goals and measures, targets, results, self and manager ratings and comments, who decided and when, the numbers a rating was given on | The date the review cycle is **closed** (not the rating date, not the employee's exit date) | **5 years** | Reduce to a **decision summary**: employee, cycle, period, overall rating, the named person who decided, the date, and a statement that the process stages were completed. Item-level numbers, comments and free text are erased | Keep the summary **3 more years** (8 in total), then erase |
| B | The **potential rating** and its comment — a forward-looking talent judgement the employee never sees | Cycle close | **24 months**, or the employee's exit date, whichever is sooner | Erase outright. It is not needed to defend the performance rating | — |
| C | Removal records: what was taken out of a review, by whom, when, and why | Cycle close | **5 years**, with the review record it belongs to | Keep in the summary as a count and dates, without the reason text | Erase with the summary at 8 years |
| D | The audit trail of changes written back to a live goal after a review | Cycle close | **8 years** — it outlives the detail, because it is the record that the goalposts moved openly | — | Erase at 8 years |
| E | Calibration notes and internal manager notes | Cycle close | **3 years** | Erase. They are working notes, not the decision | — |

**What the end of the period means.** For row A the detail is **erased and replaced by a
summary**, not merely hidden. For rows B, C and E it is erasure with nothing left behind but
an audit line saying that erasure happened, on what date, under which rule.

**Legal hold — what is held back and for how long.**

- A hold may be placed on one employee's review records by an HR administrator, with a named
  person and a written reason. While a hold is on, nothing is erased and nothing is reduced.
- A hold is **required**, not optional, as soon as any of these is recorded: a grievance about
  the rating, a performance improvement plan, a disciplinary process, a resignation or
  termination dispute, a lawyer's letter, a statutory notice, or a data-principal complaint.
- A hold releases **3 years after the matter closes**, and the person who releases it is
  recorded. Every hold is reviewed at least once every 12 months so that "held" does not
  quietly become "kept for ever".
- Erasure that is due but blocked by a hold is logged as blocked, with the reason, so an
  auditor can see the difference between a rule that is working and a rule that is being
  ignored.

**Who may switch it, and where.** The **customer company** sets these periods, not Alvoraa,
because the customer is the Data Fiduciary and holds the employment-record duties. The setting
sits in the organisation's HR settings, editable by the HR Manager role only, with every change
version-stamped and attributed. We propose that Alvoraa enforces **limits** on what a customer
may choose: not less than **3 years** for row A, not more than **10 years**, and **no
"keep for ever" option** for rows A, B, C or E. A customer with a genuine longer duty would
use a legal hold, which has a reason attached, rather than a setting with none.

## 1.3 The legal reasoning, as we understand it

**We are not lawyers.** This is our reading of published sources, with the dates we checked
them. Please correct it.

- **Storage limitation and erasure.** Section 8(7) of the DPDP Act 2023 requires a Data
  Fiduciary to erase personal data on withdrawal of consent, or when the purpose is no longer
  being served, **unless retention is necessary for compliance with any law**. Rule 8 of the
  DPDP Rules 2025 carries this through and requires erasure when the purpose is served. *Our
  reading:* the purpose of a performance rating is served when the cycle closes **and** the
  window in which it can be challenged has passed — not on the day the cycle closes. The
  proposal in 1.2 is an attempt to put a number on that window. Only you can tell us whether
  5 years is the right one.
- **The Third Schedule does not help us.** The Third Schedule retention periods in the Rules
  apply to large e-commerce, online gaming and social-media platforms above user thresholds,
  with a 3-year default and a 48-hour warning before erasure. On our reading an HR platform is
  not in any of those classes, so **there is no prescribed period we can adopt**; the employer
  must set one. *(Checked 18 September 2026. Please confirm.)*
- **The employment exemption, and how far it reaches.** Section 7(i) permits processing "for
  the purposes of employment or those related to safeguarding the employer from loss or
  liability…". *Our reading:* running an appraisal and keeping the record that defends it sits
  squarely inside that clause, which is why we have not designed a consent gate for review
  data. But section 7 is a **basis for processing, not an exemption from storage limitation**.
  We do not read it as permitting indefinite retention, and we have assumed it does not.
  Question 3 asks you to confirm.
- **Rights of access, correction and erasure.** Sections 11 and 12 give a Data Principal the
  right to information about processing, and to correction and erasure. Rule 14 sets a period
  for responding to a grievance which the text we read gives as "a reasonable period not
  exceeding ninety days". *The open point:* whether sections 11 and 12 apply to data processed
  under a section 7 legitimate use at all is a question we cannot answer and have asked before
  (it is the sixth item on the 17 September list). Our design assumes **they do**, and offers
  the rights anyway.
- **The tension we cannot resolve ourselves.** An erasure request from a former employee, and
  the employer's need to defend a rating it gave, pull in opposite directions. Our proposal
  treats the review record as evidence rather than as ordinary personal data, and offers a
  shorter life to the parts that are not evidence (the potential rating, the internal notes).
  **You draw that boundary; we implement it.**
- **Other laws that pull the other way — flagged, not verified.** We did **not** verify any of
  the following and do not assert them: minimum keeping periods for wage, attendance and leave
  records under the state Shops and Establishments Acts and the wage and labour codes; the
  period for which books and records must be kept under the Income-tax Act and its rules, and
  the longer window in which an assessment can be reopened; provident-fund and ESI record
  duties; and limitation periods for a civil claim or an industrial dispute, which may run from
  a date later than the cycle close. If any of these requires longer than our row A, the longer
  period wins, and we would rather learn the number from you than guess it.
- **IT Act 2000 and the SPDI Rules 2011.** The 2011 Rules require that sensitive personal data
  is not kept longer than needed, and they impose a privacy policy and security practices. *Our
  reading:* performance ratings are unlikely to be "sensitive personal data or information" as
  that term is defined, but a face photograph may be, because the definition includes biometric
  information. We also do not know how much of the 2011 regime survives the DPDP Act's repeal
  of section 43A once fully notified. Both points are for you.
- **Significant Data Fiduciary duties.** If a customer is notified as a Significant Data
  Fiduciary, the Rules add an India-resident Data Protection Officer, an annual data-protection
  impact assessment, an annual audit and algorithmic due diligence. We assume **Alvoraa** is not
  one. Some **customers** may be, and they will expect the product to support those duties. We
  have not built for it.

## 1.4 Questions only a lawyer can settle — review records

Each has our suggested answer. Agreeing costs you a tick.

| # | Question | Our suggested answer | What it unblocks |
|---|---|---|---|
| **Q1** | How long may or must an employer keep a completed performance review record — item-level detail, ratings and comments — and does that change once the employee has left? | 5 years' full detail from cycle close, then a summary to 8 years. Leaving does not shorten it; the defence need survives exit | The whole retention build |
| **Q2** | What does an **erasure request from a former employee** do to a review record? Does the employer's need to defend a rating it gave amount to a lawful reason to refuse or defer? | Refuse for the detail while the defence need lasts, answer within the statutory period with the reason, and erase what is not decision-bearing (potential rating, internal notes) immediately | The erasure workflow and what we tell the employee |
| **Q3** | Does section 7(i) permit indefinite retention, or does storage limitation apply in full to data processed under it? | Storage limitation applies in full; 7(i) is a basis, not an exemption | Whether a period is needed at all |
| **Q4** | May a **rated** review item ever be discarded outright? Our engineering position is never — it is marked "Removed", with the reason, and kept. | Never discarded. Keep it marked | The removal behaviour, and whether a customer may choose otherwise |
| **Q5** | May the employer **withhold the potential rating** from the employee on a request to see their own data? | Yes for the forward-looking judgement, on the reading that it is the employer's opinion about future roles rather than a decision taken about the person; but erase it at 24 months so the question narrows | Whether "never shown to the employee" can stand |
| **Q6** | When an item is **removed from a review after the employee has submitted it**, what must the employee be told, and when? | Label, date and reason, no later than the final review stage — which is what the product does today | The notice wording in 1.5 |
| **Q7** | Is there any **minimum keeping period** under tax, wage, labour or limitation law that is longer than our row A, for a record that is performance rather than payroll? | We do not know and have not verified it. If there is, it replaces our number | The floor we enforce on the setting |
| **Q8** | May Alvoraa forbid a customer from choosing "keep for ever"? | Yes, and it should. A longer need is a legal hold with a reason, not a setting | The setting's limits |

## 1.5 Draft notice wording — review records

Short enough for a phone screen. Plain English. This is the employee-facing text, to sit
inside the review screen and in the privacy notice.

> **About your review record**
>
> When your review opens, we take a snapshot of your goals and measures, so the numbers
> cannot change while you are being reviewed.
>
> Your review record keeps: your goals and results, your own comments and rating, your
> manager's rating and comments, who decided and when, and any item that was added or removed.
>
> **We keep the full record for {5} years after the review closes.** After that we keep a short
> summary — your rating, the cycle, and who decided — for {3} more years, and then we delete it.
> If there is an open query, complaint or claim about your review, we keep it until that is
> finished.
>
> You can ask to see your record, ask us to correct a mistake in it, or raise a complaint.
> Contact {grievance officer name}, {email}, {phone}.

**When an item is removed from a review, after the employee has submitted it:**

> **An item was removed from your review**
>
> *{Item title}* was removed on {date}.
> Reason given: *{reason}*.
>
> If you disagree, you can raise it with {grievance officer} before your review is completed.

## 1.6 What we will build once you answer

1. A retention rule per record type, set by the customer, with the floor, ceiling and no-forever
   limits you approve — so the period is a setting, not a code change.
2. A nightly deletion job that erases what is due, reduces row A to a summary, writes a receipt
   for every erasure, and refuses to touch anything under hold.
3. A legal hold that an HR administrator sets with a named reason, that is applied
   automatically when a grievance or dispute is recorded, and that is reviewed every 12 months.
4. Erasure of the potential rating at the period you set, separately from everything else.
5. A route for a request to see, correct or erase, with the statutory clock visible to HR and a
   record of what was done — today this is handled by hand, which means it is handled
   inconsistently.
6. A "give me a copy of my own record" export for the employee.
7. Tests that prove it: seed expired data, run the job, assert what went, what stayed, and that
   a held record survived. A retention rule without that test decays in two quarters.

---

# Part 2 · Driver location tracking

## 2.1 What we do today, stated honestly

| | |
|---|---|
| **What is recorded** | Latitude, longitude, speed, heading, accuracy, altitude, timestamp, device type, app version, battery level and network type, against the named driver and the delivery. |
| **How often** | **Every 10 seconds**, while a delivery is open on the driver's phone. A continuous trail. |
| **When it starts** | **Automatically**, the moment the driver opens a delivery that is not yet finished. There is no "start tracking" step. |
| **When it stops** | When the driver closes the delivery or the page. The server does not check whether a point belongs to an open delivery — it checks only that the delivery is assigned to that driver. |
| **What the driver is told first** | **Nothing.** There is no notice, no consent screen, and no record of either. The screen shows a "Location Tracking" heading and a "GPS Active" indicator once it is already running. There is no off switch — the only button is a demo simulator. |
| **Derived judgements** | The server still marks a point as a **speeding alert** whenever the reported speed is over 60, and stores it on the driver's record. Fields also exist for harsh braking, harsh acceleration and sharp turns. |
| **What changed this week** | The path that turned those flags into a safety score, a performance level, a pay-increment recommendation and an automatic written warning was **deleted from the code** — we verified the queries are gone, not disabled. **Collection of the judgement continues.** And the scorecard still produces an automatic increment recommendation and an automatic "written warning" flag at the bottom tier, now from on-time delivery, customer ratings, human-recorded safety incidents and attendance. |
| **How long it is kept** | **For ever.** No retention rule, no deletion job, no setting. We searched the whole codebase: the only deletions of tracking data are in test fixtures. |
| **The contrast that matters** | An attendance check-in **photograph** is deleted after **90 days** by default, the period is a customer setting, the job runs daily, and a record flagged for legal hold is skipped. That is a working pattern the location trail does not use. |
| **Who can see the trail today** | On a tenant where the delivery module is switched on, **any logged-in user** can read a named driver's position history. The module is now off by default and off for new customers, which is why we treat this as a future risk rather than a present incident — but "off by default" is not "cannot happen". |
| **How much data exists** | **None.** Every delivery, driver, tracking and scorecard table is empty on every environment we may look at. No customer is live. |

## 2.2 Our proposal

| # | Record | Clock starts | Keep | Then |
|---|---|---|---|---|
| A | The detailed trail: every position, speed and heading point | The date the delivery is closed or cancelled | **30 days** | Erase the points |
| B | A per-delivery summary: start time, arrival time, completion time, distance travelled, whether the delivery was on time | Delivery closed | **12 months**, because it supports pay, billing and a customer complaint | Erase |
| C | Derived driving-behaviour judgements (harsh braking, harsh acceleration, sharp turn, speeding alert) | — | **Not collected at all.** Remove the fields and stop computing them | — |
| D | The live position shown on a map to the customer or the manager | — | Not stored separately; it is row A being read while the delivery is open | — |

**Held back for a dispute or a claim.** If a delivery is the subject of a customer complaint, a
damage or missing-item claim, a road accident, an insurance claim, a police or court request, or
a disciplinary matter about that driver, **that delivery's trail goes on hold** and is kept until
the matter closes **plus 90 days**. The hold is set by an operations or HR administrator with a
named reason, and is reviewed every 6 months. This is the same shape as the check-in photo hold,
which already works.

**When tracking may happen at all — enforced by the server, not by instruction.**

1. Only while a delivery is **open** and **assigned to that driver**. A point sent for a closed,
   cancelled or unassigned delivery is refused, not stored.
2. Only inside the driver's **shift or duty window** for that day. Outside it, refused.
3. **Never outside working hours.** The app stops posting when the delivery closes, and the
   server refuses a point that arrives anyway. Our view is that this is not a matter of
   configuration: there is no lawful purpose we can state for tracking a delivery worker when
   no delivery is open, so the product should make it impossible rather than discouraged.
4. A visible indicator whenever tracking is live, and a plain statement of when it will stop.
5. Notice shown, and acknowledged, **before the first point is recorded** — see 2.4.

**Who may switch the retention period, and where.** The customer sets row A within limits we
enforce: not less than **7 days**, not more than **90 days**, and **no "keep for ever"**. Row B
is fixed at 12 months unless you tell us otherwise. The setting sits with the operations
settings for the delivery module, editable by an administrator role, with changes attributed
and version-stamped. Row C is not a setting: we propose it simply stops.

## 2.3 The legal reasoning, as we understand it

- **Notice.** Rule 3 of the DPDP Rules 2025 sets what a consent notice must contain and requires
  it to be clear, standalone and plain, with the means to withdraw and to complain.
  **What we do not know:** whether a notice is legally required where processing rests on a
  section 7 legitimate use rather than on consent, since the Act's notice duty in section 5 is
  framed around consent. *Our position regardless:* give the driver a notice. Continuous location
  is the kind of processing a person will be angry to discover, and "we were not obliged to tell
  you" is not a defence anyone wants to run. Question 9.
- **Purpose limitation and minimisation.** Sections 4, 6 and 8 and Rule 8 together mean the data
  may be used only for the purpose stated, and no more of it collected than that purpose needs.
  *Our reading:* showing a customer and a manager where an open delivery is, is a stated
  operational purpose. Deriving a driving-style judgement about a worker from the same feed, and
  letting it move pay, is a **different** purpose, and one we have decided against on our own
  account. We have removed the scoring; row C removes the collection.
- **Storage limitation.** As Part 1: erase when the purpose is served. The purpose of a
  breadcrumb trail is served when the delivery is closed and the window for a dispute about that
  delivery has passed. That is days, not years. A minute-by-minute movement history of a named
  worker kept indefinitely is, in our engineering judgement, the single hardest thing to defend
  in this product.
- **Security safeguards, and one obligation that pulls the other way.** Rule 6 of the Rules sets
  minimum security measures, and Rule 6(1)(e) as we read it requires a Data Fiduciary to
  *"retain such logs and personal data for a period of one year, unless compliance with any law
  for the time being in force requires otherwise"*. *(Checked 18 September 2026.)* **This may
  conflict with our 30-day proposal** if a driver's position points count as "logs and personal
  data" for that purpose rather than as ordinary business data. Our reading is that the rule is
  about access and monitoring logs, not about every operational record — but we are not
  confident, and it is question 10, because if we are wrong the number changes from 30 days to
  12 months.
- **The employment exemption, again.** Section 7(i) covers processing "for the purposes of
  employment or those related to safeguarding the employer from loss or liability". *Our reading:*
  tracking an open delivery in progress is within it for an employed driver. Keeping the trail for
  years, or using it to judge driving style, is not. Section 7(i) is not a licence for
  surveillance.
- **Motor Vehicles rules — flagged, not verified.** A separate Indian regime, AIS-140 under the
  Motor Vehicles framework, requires vehicle location tracking devices in many classes of
  commercial and public-service vehicle, transmitting to government backends, with deadlines that
  sources put in and around March 2026. *(Checked 18 September 2026 against secondary sources
  only.)* That is **vehicle** tracking through a certified device, not our phone-based app, and it
  may carry its own keeping duties. We do not know whether a customer using our module is also
  under that regime, whether our data could be treated as serving it, and whether it creates a
  minimum retention we must respect. Question 11.
- **Income tax, wage and labour records.** A delivery driver's **pay** record may have to be kept
  far longer than the movement trail that helped calculate it. Our proposal separates them
  deliberately: the summary in row B survives for pay and billing; the detail in row A does not.
  We did not verify the statutory periods — question 7 covers them for both parts of this paper.
- **IT Act and SPDI Rules.** On our reading, location is **not** listed as "sensitive personal
  data or information" in the 2011 Rules, though a face photograph plausibly is. We have not
  confirmed either, and we do not know how much of that regime survives the DPDP Act.

## 2.4 Consent or legitimate use — our analysis, for you to correct

| Situation | Our view | Why | What changes if you disagree |
|---|---|---|---|
| **Driver is an employee of the customer** | Rely on **section 7(i), legitimate use for employment**, and give notice anyway | Tracking an open delivery is operationally necessary to the job, and the employer is the Data Fiduciary. Consent between an employer and an employee, for something the employee cannot decline and still do the job, is unlikely to be "free" | If you say consent is required, we must build a consent gate, a refusal path, and an answer to "what happens to a driver who says no" — which, for this job, may be "there is no alternative way to do it", and that is exactly why we prefer 7(i) |
| **Driver is an independent contractor or a gig worker** | **Section 7(i) probably does not reach them**, so the basis is **consent under section 6** — and we think this is the sharpest question in this paper | 7(i) speaks of employment. DPDP has **no "necessary for a contract" basis** of the kind GDPR provides, so if employment does not apply we see little between consent and nothing | If consent is the answer, it must be free, specific, informed and withdrawable as easily as given, recorded per version with time and device, and re-asked when the notice changes. Practically: the driver agrees at onboarding that tracked deliveries are tracked, and a refusal means not accepting tracked work rather than a penalty |
| **Tracking outside working hours** | **No, in every case.** The app must stop and the server must refuse | We can state no purpose for it. It is also the thing most likely to turn a private complaint into a public one | If you consider a narrow exception lawful — a vehicle recovery, for instance — we would build it as an explicit, logged, time-boxed act by a named person, not as continuous collection |
| **Reusing the trail to judge the driver** | **No.** Removed from the code, and row C stops the collection | Data collected to run a delivery being reused to set pay is purpose creep, and behavioural monitoring as a performance input is something the product has committed publicly not to do | If a customer insists, that is a separate purpose needing its own basis, its own notice and its own retention answer — and our position is that we do not build it |
| **The customer seeing the driver's live position** | Yes, while the delivery is open, limited to that delivery | Stated purpose, understood by everyone, and it ends when the delivery does | — |

## 2.5 Questions only a lawyer can settle — driver tracking

| # | Question | Our suggested answer | What it unblocks |
|---|---|---|---|
| **Q9** | On what basis do we process a driver's continuous location — the employment legitimate use, or consent? And is a notice legally required where we rely on a legitimate use? | 7(i) for employees, consent for contractors; give notice either way | Whether we build a consent gate; the notice; shipping the module to any live customer |
| **Q10** | How long may the detailed trail be kept? Does the Rule 6(1)(e) one-year retention of "logs and personal data" apply to operational position points, or only to access and monitoring logs? | 30 days' detail, 12 months' summary. Rule 6(1)(e) applies to security logs, not to every operational record | The number in row A, and whether it is 30 days or 12 months |
| **Q11** | Does any Motor Vehicles or transport rule — AIS-140 or similar — apply to a customer using this module, and does it create a minimum retention or a duty to transmit? | We do not know. Likely a separate, vehicle-level duty that does not lower our period | Whether 30 days is even available |
| **Q12** | Can a driver lawfully be required to accept tracking as a condition of the work, and does the answer differ for a contractor? | Employee: yes, within the purpose and hours. Contractor: yes if consented at onboarding, with refusal meaning "no tracked work", not a penalty | The onboarding flow and the contract clause |
| **Q13** | The scorecard still produces an **automatic pay-increment recommendation and an automatic written-warning flag** at the bottom tier. Is an automated flag of that kind acceptable under Indian law if a named human must confirm it before anything happens, and what must the driver be told and able to contest? | A named human must decide, the driver must be told the flag exists and be able to contest it, and the automatic step must never issue anything by itself | Whether the automatic warning stays, changes shape, or goes |
| **Q14** | Must a driver get a **separate notice** from the employee privacy notice, and does a screen-only notice suffice for a worker with no email? | Yes, separate, because the employee notice's "we do not track you between check-ins" line is false for drivers. Screen notice plus a printed copy at the hub | The notice set before the first live customer |

## 2.6 Draft notice wording — driver location

**Shown before the first position is ever recorded, on the driver's phone, with an
acknowledgement:**

> **About location on this app**
>
> While a delivery is open, this app sends your location, speed and direction to {Company},
> about once every 10 seconds. Your manager and the customer can see where the delivery is.
>
> **It stops when you close the delivery.** You are not tracked between deliveries, and not
> outside your shift.
>
> **We keep the detailed trail for {30} days** after the delivery. After that we keep only a
> summary of the delivery — when it started, when it arrived, the distance — for {12} months.
>
> We do **not** score your driving. Your location is not used to set your pay.
>
> You can ask to see what we hold about you, or raise a complaint, with {grievance officer name},
> {email}, {phone}.
>
> `[ I understand ]`

**The permanent indicator, on screen the whole time tracking is live:**

> **Location on** — sharing while this delivery is open. Stops when you close it.

**When the delivery closes:**

> **Location off.** Sharing has stopped for this delivery.

**How to raise a concern — the same wording in the app and on the hub notice board:**

> **Not happy about something we hold about you?**
>
> Tell {grievance officer name}: {email}, {phone}, {address}. We will reply within {30} days.
> If you are still not satisfied, you can complain to the Data Protection Board of India.

## 2.7 What we will build once you answer

1. Server-side limits on when a point may be recorded: open delivery, assigned driver, inside a
   shift window. Anything else is refused and logged.
2. A retention rule and a daily deletion job for the trail, copying the check-in photo pattern,
   including its legal hold — this is the smallest and highest-value item on the list.
3. Removal of the derived driving-behaviour fields and the code that computes them.
4. The notice and acknowledgement screens above, with the notice version recorded per driver.
5. A visible "location on / off" indicator and the automatic stop at delivery close.
6. Whatever question 13 decides for the automatic warning and the increment recommendation.
7. Ownership checks so that only the driver, their manager and the entitled customer can see a
   trail — today, on a tenant with the module on, any logged-in user can.
8. A one-off correction for any customer who used the old scoring, so that no pay recommendation
   survives that the phone's sensors helped set. Nobody has, and we want it written down before
   anybody does.

---

# Part 3 · Where we are today on obligations that are not yet due

Said plainly, because it affects the order in which we build.

- **No customer is live.** Every table described in this paper is empty. No individual is
  affected, and no reporting duty is engaged today. **That is a timing accident, not a control.**
- **The substantive DPDP obligations are not yet in force.** On the sources we read on
  18 September 2026, the Rules commence in phases: an initial set from mid-November 2025, consent
  manager registration from mid-November 2026, and the **core obligations — notice, security,
  breach reporting, retention and erasure, rights and transfer — from mid-May 2027**. Sources
  differ on whether the final date is the 13th or 14th of the month, and one report says the
  government proposed shortening the final phase without notifying it. **Please confirm the
  operative date**, because our build order depends on it.
- **The CERT-In directions of 2022 are in force now**, and are stricter on time than DPDP: cyber
  incidents reportable within **6 hours** of awareness, and ICT logs kept for a rolling 180 days
  **within Indian jurisdiction**. Our servers are in **France**. The clock synchronisation
  requirement has been met; the India log residency requirement has not. Whether CERT-In binds
  Alvoraa as a body corporate operating in India is a question we have already put to you.
- **What becomes due on the day the first customer goes live**, on our reading, and what is not
  built:

| Becomes due | Built today |
|---|---|
| A privacy notice, versioned, in a language the workforce reads, with a record of who saw which version | Draft written 17 September 2026; the app records one version only; no Hindi version |
| A named grievance officer and a working route for a complaint, with a clock | **Not built.** Handled by hand |
| A route for a request to see, correct or erase, answered inside the statutory period | **Not built** |
| Giving an employee a copy of their own record | **Not built** |
| Retention and erasure with legal hold, for everything except attendance photos | **Not built** — this paper is the request for the numbers |
| A breach procedure, named contacts, and **one rehearsal** that meets the 6-hour clock | **Not built.** A runbook nobody has exercised is a document, not a capability |
| A written privacy impact assessment for location and photographs | **Not written** |
| A tested procedure to return and delete a customer's data at the end of the contract | **Not built** |

**The honest consequence.** Certification evidence is retrospective: if nobody is collecting it
now, an ISO 27001 or SOC 2 date is roughly a year after the day collection starts. We say this
out loud so it is not discovered during a customer's security review.

---

# Part 4 · Residual risks — for the founder to accept or reject, by name and date

Nothing below is accepted yet. **An accepted risk with a name and a date is governance; an
unnamed one is an accident waiting for an owner.**

| # | Risk that remains | Why it remains | Accepted by | Date |
|---|---|---|---|---|
| 1 | Performance review records are kept for ever, and no role can delete anything | Deletion was deliberately blocked pending your answer to Q1 and Q2. Nothing is lost, and nothing can be erased on request either | | |
| 2 | A driver's minute-by-minute location history has no keeping limit and no deletion job | No retention mechanism for that module. Empty tables today | | |
| 3 | The product deletes an attendance photograph after 90 days and would keep a movement trail of the same person for ever | The inconsistency is real and is the first thing a reviewer will find | | |
| 4 | A driving-behaviour judgement (speeding flag) is still recorded against a named worker, with no stated purpose and no keeping limit | The scoring was removed; the collection was not | | |
| 5 | The scorecard still produces an automatic pay-increment recommendation and an automatic written-warning flag | Awaiting Q13 | | |
| 6 | On a customer tenant where the delivery module is switched on, any logged-in user can read a named driver's trail and position | Ownership and row-level checks are the next phase of work. The module is off by default | | |
| 7 | No notice, no consent record and no off switch before a driver's first position is recorded | Awaiting Q9 and Q14 | | |
| 8 | The potential rating is withheld from the employee in the product, and no lawyer has confirmed that it may be withheld on a data-access request | Awaiting Q5 | | |
| 9 | No route for a request to see, correct or erase; no employee copy of their own record; no grievance clock | Not built. Becomes due on the first live customer | | |
| 10 | Personal data, logs and backups are in France; CERT-In's 180-day India log residency is not met | Recorded decision of 6 September 2026: stay in France, state it plainly, build an India region when a customer needs one | | |
| 11 | No breach runbook and no rehearsal against the 6-hour clock | Not built | | |
| 12 | Statutory minimum keeping periods under tax, wage and labour law are unverified, so our proposed periods could be below a legal floor | Awaiting Q7 | | |

---

## Sources, and the date we checked each

Secondary sources that quote the official text. **Please check them against the Gazette.**

| Point | Source | Checked |
|---|---|---|
| DPDP Act 2023 s.7(i), legitimate use for employment — quoted in full in 2.3 | dpdpa.com, section 7 | 18 Sep 2026 |
| DPDP Act 2023 s.6 consent, s.8 duties and erasure, s.11 / s.12 rights, s.16 transfer | dpdpa.com, chapters 2–4 | 17 Sep 2026 |
| DPDP Rules 2025 — three-phase commencement; core rules (notice, security, breach, retention, rights, transfer) from mid-May 2027; proposal to shorten not notified | dpdpa.dcomply.in rules index; dpdprules.org timeline | 18 Sep 2026 |
| DPDP Rules 2025 Rule 6(1)(e) — retain logs and personal data one year | dpdpa.com, Rule 6 | 18 Sep 2026 |
| DPDP Rules 2025 Rule 8 and the Third Schedule — 3-year periods apply to large e-commerce, gaming and social media only; 48 hours' warning before erasure | dpdpa.com Rule 8; medianama summary | 18 Sep 2026 |
| DPDP Rules 2025 Rule 14 — grievance response "a reasonable period not exceeding ninety days" | dpdpa.com, Rule 14 | 17 Sep 2026 |
| CERT-In Directions of 28 April 2022 — 6-hour reporting, 180-day India-resident logs, NTP | Trilegal and Internet Society summaries | 24 Aug 2026 |
| AIS-140 vehicle location tracking devices under the Motor Vehicles framework, deadlines around March 2026 | Industry summaries only — **not a primary source** | 18 Sep 2026 |
| Hosting location: Contabo, Lauterbourg, France | Measured on the host | 6 Sep 2026 |
| What the product actually does, in both parts of this paper | The source code, read directly | 18 Sep 2026 |
| No live customer; all delivery tables empty | Founder's record of 17 Sep 2026, plus row counts measured | 18 Sep 2026 |

**Not verified, and deliberately not asserted:** state Shops and Establishments and wage-law
record periods; Income-tax record and reassessment periods; provident fund and ESI record
duties; limitation periods for a civil claim or an industrial dispute; how much of the IT Act
SPDI regime survives the DPDP Act; whether any transfer restriction has been notified under
section 16; and whether any Alvoraa customer is a Significant Data Fiduciary. We also did not
look at the production server: a security review is done against the code, never by probing a
live system.

**We are not lawyers.** Every number in this paper is a proposal we can build. None of it is
advice, and none of it is settled until you say so.
