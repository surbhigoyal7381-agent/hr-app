---
slice: 082-event-attendee-qr-form
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-11-13
status: draft
inputs: [01a-ux-opportunities.md, 07-devops-inputs.md (§1), .claude/context/data-doors.md, .claude/context/no-over-engineering.md, docs/slices/057-amata-crm-demo/01-brief.md]
youtrack: ALV-339
---

# 082 · Event attendee QR form · Product brief

I recommend. Surbhi decides: build, change or drop.

## 0. The answer first

**Bad news first.**

- **This is not our core product.** Alvora is a talent and performance platform (product-context §1). An event-attendee form is a CRM job for a CRM customer. No priorities review ranks it, and I found no named event customer in the repo. **If there is no named organiser who will use it, I recommend the configuration-only version (§6, "could we not build it") and nothing more.**
- **The ready-made form would turn most of a hall away.** Frappe refuses the 11th submission a minute from one internet address, per form. At a venue on shared Wi-Fi, about 250 of 300 people would see an error (DevOps §1, read in code, not run).
- **We would be collecting members of the public's personal data.** The organiser is the one responsible for it under India's data law (DPDP). They need a notice, a retention period and a consent tick before the first event. The retention period does not exist yet (Q4).

**What I recommend if there is a customer:** use the public form builder that Frappe CRM already ships (`/crm-form/<route>`; each submission becomes a CRM Lead). Add only the five things that stop it working at a real event: a per-event submission limit, an event stamp on each lead, phone-sized inputs, a "Download QR" button, and the closed staff-name leak. **Rung: customisation plus a little new code. No new DocType, no new app.**

## 1. Job to be done

*"As the person running an event, when 300 people leave the hall at once, I want each of them to leave their details and a quick rating from their own phone, so that tomorrow I have one list per event that sales can follow up and I can see which events worked."*

- **Attendee** (a member of the public, not a login): fills one phone screen in under a minute, and goes.
- **Organiser staff** (Sales User in CRM): builds the form, prints the QR, stands at the door.
- **Organiser manager / CXO** (Sales Manager): reads results across events.
- **Employee portal: out.** The attendee is not an employee. No job is served by adding a door to the HR portal.

## 2. Current pain

I have no data. The story: today an organiser prints a Google Form QR or passes round a paper sheet `[ASSUMPTION]`. The paper sheet is typed into a spreadsheet days later, with half the mobile numbers unreadable. The Google Form lives outside the CRM, so sales follows up from a copy. Feedback is a separate form, so nobody links "rated the event 2 out of 5" to the person sales calls next week.

## 3. Competitive analysis (whole products)

All "read" claims come from the UX scan (01a §2), read on 13 Nov 2026.

| Capability | Frappe CRM (standard) | Zoho Backstage | Eventbrite | HubSpot | Google Forms | What we do |
|---|---|---|---|---|---|---|
| Public form, no login | Yes, read in code | Yes, read | Registration only, read | Yes, read | Yes `[recall — verify]` | Use CRM's |
| QR for the form | No, read in code | Yes, read | Ticket QR, read | No built-in, read | Yes `[recall — verify]` | One button |
| Event tied to each entry | No, read in code | Yes, read | Yes, read | Hidden field per page, read | One form per event `[recall — verify]` | Stamp the form on the lead |
| Feedback in the same record | Possible with custom fields | Separate product (Zoho Survey), read | No, third-party, read | Same form possible, read | Separate sheet `[recall — verify]` | Same lead |
| Crowd on one Wi-Fi | Fails at 10/min/address, read in code | Unknown | Unknown | Unknown | Works `[recall — verify]` | Limit per event |
| Phone-sized form | No (14 px inputs), read in code | Unknown | Yes, read | Yes `[recall — verify]` | Yes `[recall — verify]` | Fix the floors |

Pricing tier: I could not check how competitors price this; Backstage and Eventbrite sell it inside event plans `[recall — verify]`. For us it would sit inside the CRM add-on (`ERPNEXT_FEATURES["crm"]`, Confirmed by the UX scan), not a new plan.

**What we will deliberately NOT do that they do:** ticketing, check-in scanning, badges, seat maps, a separate survey product joined by Zapier, one-question-per-screen forms. **Why that is better for our user:** one record per attendee per event, inside the CRM sales already use, on a page that loads once and sends once on poor signal.

## 4. Kano class and demand (proxy, not surveyed)

| Part | Class | Evidence |
|---|---|---|
| Capture attendee details by QR into the CRM | **Must-be, proxy** | Every reference product above has some version (read, 13 Nov 2026). Demand: **seen — one request, from Surbhi, for an unnamed event organiser.** No demo note, ticket or lost deal found. |
| A form that survives a crowd on one Wi-Fi | **Must-be, proxy** | Its absence would be an angry first event. No product markets it, because it is assumed. |
| Feedback in the same record as the details | **Attractive, proxy** | Zoho and Eventbrite split it across products (read). |
| Live dashboards, NPS-style scores | **Indifferent, proxy** | Nobody asked. Do not build. |

**Evidence that would change this:** a named organiser saying which of these they would pay for. The survey questions are in §13.

## 5. Three ways, and "could we not build it at all"

| Way | What it is | Verdict |
|---|---|---|
| **Not at all** | CRM form as it ships, configured by us, one form per event, a static QR from any generator, and the setup guide. Rung 2. | **Fine for a small event (under ~30 people a minute from one address).** Fails a 300-person hall. If there is no named customer, stop here. |
| **Conventional** | New Event, Attendee and Feedback DocTypes, our own public page, a dashboard. | No. Three new record types to secure, a page to maintain, all for something CRM already does. |
| **Better (recommended)** | The CRM form plus the five fixes in §7. Rung 3 and a small rung 4. | Meets the job for a real crowd. |
| **Reimagined** | QR opens WhatsApp ("Hi from the Pune meet"); our AI intake (slice 057) makes the lead. | No for now. Needs a WhatsApp Business number per organiser, cost per chat, and a rating is clumsy in chat. Note it as an idea for the user. |

## 6. Persona enhancements (from 01a)

| Persona | Idea (01a ID) | Job it serves | In this slice? | Why |
|---|---|---|---|---|
| Attendee | A1 one short screen | Give details, go | **Yes** (config) | The core |
| Attendee | A2 16 px fields, 48 px button, no Discard | Finish with a thumb | **Yes** | Without it the phone zooms and Discard wipes answers |
| Attendee | A3 bilingual labels typed by organiser | Hindi-first attendee | **Yes** (config, zero code) | Free |
| Attendee | A4 keep answers on error | Wi-Fi drops at Submit | **Yes, the small half:** never clear the form on an error, plain "Not sent — press Submit again". **Auto-retry: later** | Losing typed answers is the worst moment; auto-retry is a size M we cannot justify yet |
| Attendee | A5 link works after the event | No signal in the hall | **Yes** (config) | Cheapest offline answer |
| Attendee | A6 "This is not a payment" under the QR | QR read as UPI | **Yes** (print text) | Free |
| Attendee | A7 thanks screen names the event | Know it worked | **Yes** (config) | Free. No echo of what they typed (OPS-5) |
| Organiser staff | S1 Download QR | Print without a third-party site | **Yes** | Free dynamic QR codes expire mid-event (01a) |
| Organiser staff | S2 event set in the link | Every entry on the right event | **Yes, one form per event** | No new Event record needed |
| Organiser staff | S3 test from your phone | Catch a broken field | **Already there** — setup guide only | — |
| Organiser staff | S4 walk-in by staff | Attendee without signal | **Already there** — staff open the same link | — |
| Organiser staff | S5 live count | Know it is working | **Later / decision** — see access conflict C1 | Door staff do not need the list to do their job |
| Manager / CXO | M1 one table across events | Which events worked | **Yes** (a saved Report view, config) | Group by event |
| Manager / CXO | M2 low ratings first | Act on the unhappy ones | **Yes** (sort order, config) | The WOW |
| Manager / CXO | M3 repeat attendees | Spot warm prospects | **Later** | Matching code; the brief says each entry is its own lead (Q3) |
| Employee (portal) | Event results in the HR portal | — | **No** | No job; adds a data door |

## 7. The thin slice

**Needed to validate now (the build):**
1. **Per-event limit.** First measure: do 50 saves from one address in a minute succeed on the stock form? If not (expected), one small guest save path whose limit is keyed on the event, reusing slice 013's hashed limiter (`field_app_limits.py`). The security engineer sets the number. (DevOps OPS-1.)
2. **Event stamp.** One Custom Field on CRM Lead, "Event form" (a link to the CRM form used), filled on save. Plus Custom Fields for the rating (five worded choices), one comment, and two consent ticks. Nothing else on the lead.
3. **Phone floors** on the CRM form page: 16 px inputs, 48 px full-width Submit, no Discard, form not cleared on error.
4. **Close the staff-name leak (G2):** the public form must never list anything from the tenant's data. No guest access to the User link, or to any link.
5. **Download QR** beside the form's public link: a PNG of the tenant's own address, which never expires (OPS-7).

**Needed before it can ship:** the retention period and the notice text (Q4); counsel's view on minors (Q7); a 300-saves-in-5-minutes test from one address on dev with the customer's CRM rules on (OPS-9); the data-door tests (§9); a native Hindi reviewer for the labels.

**Worth doing later:** automatic retry on the phone; repeat-attendee matching; a live count for door staff; a date window that closes the form by itself (manual unpublish covers it today).

**Not doing:** ticketing, check-in, badges, per-session feedback, NPS or dashboards, AI comment summaries, WhatsApp follow-up, an offline app, captcha (no spam measured; OPS-3), file uploads (OPS-6), ERPNext Lead (OPS-10), a new Event DocType, sharing lists with sponsors, anything in the employee portal.

## 8. The WOW

The evening after the "Pune Dealer Meet, 14 Nov", the organiser manager opens one saved view in CRM: **"Pune Dealer Meet, 14 Nov — 287 entries. Lowest ratings first."** The first four rows are the people who rated it "Poor" or "Very poor", each with their comment beside their rating. They can call those four people before lunch.

The attendee's quieter moment: the 300th person in the hall presses Submit at the same second as everyone else and sees **"Thank you. Your details are saved for Pune Dealer Meet."** (Hindi: "धन्यवाद। आपकी जानकारी Pune Dealer Meet के लिए सहेज ली गई है।" — needs a native reviewer.)

## 9. Access expectations (who may see, change and share)

Kano-must = a breach if wrong. **C1–C5 are conflicts for Surbhi to decide.**

| Data | Persona | May see | May change | May share / export | Purpose | Must not have | Class |
|---|---|---|---|---|---|---|---|
| Attendee's details, rating, comment, consents | **Attendee** (guest) | Only the thanks screen | Only their own entry, while filling it | — | Leave details once | Any list, count, or echo of any entry, including their own after submit | **Must** |
| Same | **Organiser staff** (Sales User) | **Nothing**, unless a lead is assigned to them | Leads assigned to them | No | Follow up their assigned people | The event list as a whole (C1) | **Must** |
| Same | **Organiser manager** (Sales Manager) | All leads of their company's events | Yes: correct, assign, delete | Export: yes, in-company only (C2) | Run follow-up, judge events, delete on request | Reaching people who did not tick marketing (C3) | **Must** |
| Rating + comment with name | **Speaker / event host** (if a login) | Comments **without names** (C4) | No | No | Improve the talk | Who said what | Expectation |
| Event summaries (entries, average rating) | **CXO** | Counts and averages per event | No | Yes | Which events worked | Individual rows by default (C5) | Expectation |
| Any attendee data | **Tenant's own staff with only the Employee role** (HR portal users) | Nothing | Nothing | Nothing | None | CRM Lead read through any door | **Must** |
| Any attendee data | **Outside party: sponsor, agency** | Nothing in this slice | — | — | None named | Any list | **Must** |
| Any attendee data | **Alvora staff** (us, as the processor) | Only to fix a reported problem, on the organiser's request | No | No | Support | Routine browsing | **Must** |
| Staff names (User list) | **The public** | Nothing | — | — | None | Names in the form's page (G2) | **Must** |

**Conflicts for Surbhi to decide:**
- **C1 · Door staff want to see entries come in.** Least privilege says they need a count, not names. Recommend: no list for door staff; the manager watches the count.
- **C2 · Managers want to export to Excel.** Recommend: Sales Manager only, inside the organiser's company. Every export logged `[ASSUMPTION: Frappe logs report exports — verify]`.
- **C3 · Sales want to email everyone who attended.** Recommend: only people who ticked "Send me news of future events". This one is a legal line, not taste.
- **C4 · Speakers want to read feedback.** Recommend: comments without names, or not at all.
- **C5 · CXO wants to drill into people.** Recommend: summaries; the individual list only with a Sales Manager role.

**The five questions, answered for this slice:**
1. **Who can read this, and which door stops everyone else?** Organiser Sales Managers read all event leads; Sales Users read only leads assigned to them; guests and Employee-only logins read nothing. CRM Lead's own permission rules (role rights plus CRM's owner/assignee rule) must enforce it, not our page.
2. **Was it tested as a plain staff login through the API?** It must be: the guest save path, `/api/resource/CRM Lead`, report view, link search on the new "Event form" field, and the CRM form page's HTML, each as Guest, Employee-only, Sales User and Sales Manager. **CRM is not installed on any local site, so a fresh site with CRM is needed first.**
3. **Fresh site and real tenant?** Fresh site with CRM installed for the tests. Before release, a read-only count on the organiser's tenant: how many logins can list CRM Lead, and by which role.
4. **How many bypasses?** One expected: the guest save inserts a lead without a login (the stock form does the same, DevOps §1 point 3). It must be counted and listed. Nothing a guest calls may read a lead back.
5. **What could a manager change or share?** A Sales Manager can edit, assign, delete and export event leads, and share a lead record with another user. Sharing to an outside login is the gap to watch (C2).

## 10. Regulatory read

1. **Regime:** DPDP (personal data of the public, notice and consent). Possibly children's data (C-Q7). CERT-In if it leaks.
2. **Whose duty:** **the organiser's**; we are their processor `[ASSUMPTION — counsel to confirm]`. This slice helps them discharge it: a notice, an unticked consent, a separate marketing tick, a retention period they declare.
3. **New:** collection from the public through a no-login page; a new guest write path.
4. **Front page test:** we would defend it **if** the notice is honest and the staff-name leak is closed. We would not defend it with a pre-ticked marketing box. I am not a lawyer.

## 11. Run side (DevOps §1)

No new app, container, worker or scheduled job. About 1-2 MB of database per 300-person event (estimate). **The risk is the 8 shared worker slots on production**: a 300-person rush lands alongside DTC's biometric posts. The OPS-9 load test settles it. **If nginx needs its own limit, that edit restarts the live proxy, so it ships as its own approved change** (OPS-4). This does not change the size of the slice.

## 12. Success criteria

| Measure | Baseline | Target | How measured |
|---|---|---|---|
| Submit presses that become a lead, at the first event | Stock form: ~17% at 300 in 5 min from one address (estimate, not measured) | ≥ 99% | Leads with the event stamp ÷ save calls for that form (server log) |
| Entries ÷ people in the room | Unknown — ask the organiser for their last paper or Google Form rate | ≥ 60% `[ASSUMPTION]` | Leads per event ÷ organiser's headcount |
| Time for an attendee to fill it | Unknown | Median ≤ 60 s on a throttled 3G phone | Five-person test before the first event |
| Low ratings followed up | Unknown | Every "Poor"/"Very poor" entry has a note or task within 2 working days | CRM activity on those leads |

Plus a quality bar: zero data-door test failures (§9) on a fresh site.

## 13. Thriving-workplace lens and Kano survey kit

- **Engagement:** attendees' views reach a named person who can act on them.
- **Collaboration:** door staff, manager and sales work from one list per event.
- **Inclusiveness:** no app, no login, bilingual labels, staff can fill it for someone without a phone. Excluded today: screen-reader users on CRM's page `[ASSUMPTION — UX to check at design]`.
- **Transparency:** the notice tells the attendee who keeps their details, why, and for how long.

**Survey kit** (ask 5+ event organisers; each answered Like / Expect it / Neutral / Can live with it / Dislike):
- "If attendees could scan a QR and land straight in your CRM, how would you feel?" / "...if they could not?"
- "If the form kept working with 300 people on one Wi-Fi..." / "...if some were refused?"
- "If feedback sat on the same record as the contact details..." / "...if it was a separate survey?"

## 14. Risks and red-team

- **CRM upgrade breaks our CSS or save path.** CRM is pinned (v1.84.0); re-test on every pin change.
- **Wrong tenant on the QR.** A dev address on a printed banner sends real people's data to dev (OPS-7). The button prints only the tenant's own address.
- **Spam on a photographed poster.** The per-event limit caps the volume; the manager unpublishes the form after the event. Captcha only if spam is measured.
- **300 emails at once** if the customer's CRM sends a notification per lead (OPS-11).
- **Staff leaves mid-event:** leads are owned by nobody until assigned, so nothing is lost.
- **Cheapest way to find out first:** install CRM on a local site, build one form, fire 300 saves from one address. Half a day.

## Open questions

**Must know**

| # | Question | My default if you want me to keep moving | Owner | Blocks |
|---|---|---|---|---|
| MK1 | Is there a named event organiser who will use this, on a CRM tenant? | None known → build only the configuration version (§5) and stop | Surbhi | Whether to build at all |
| Q4 | How long does the organiser keep attendee data, and who deletes it? | 6 months after the event for people without marketing consent; the Sales Manager deletes with a saved filter. **Not a legal answer** | Organiser + counsel | Switch-on (the notice cannot be honest without it) |

**Should know**

| # | Question | Default | Owner | Blocks |
|---|---|---|---|---|
| Q1 | When do attendees scan: door, end, or both? | One scan, at the end; feedback optional | Surbhi / organiser | One form or two |
| Q2 | Does an event need more than a name and a date? | No; the form title carries them; no Event record | Surbhi | A new record type |
| Q3 | Same person at three events: three leads or one? | Three leads | Surbhi | Matching code |
| Q5 | Raise the limit per event, and to what? | Yes; keyed per event; security sets the number | Security engineer | Whether a crowd works |
| DevOps Q1 | Venue Wi-Fi or mobile data? | Both share addresses; plan for the per-event limit | Organiser | Stock form or our save path |
| Q6 | Frappe CRM Lead, not ERPNext Lead? | Frappe CRM Lead (OPS-10) | Surbhi | Which record to secure |
| Q7 ⚠ COMPLIANCE | Can attendees be under 18 (school or college events)? DPDP needs a parent's consent for children. | Notice says "for attendees aged 18 or over" | Counsel, via Surbhi | Switch-on for any event with minors |
| Q8 ⚠ COMPLIANCE | Do we need a processor agreement with the organiser? | Yes | Founder + counsel | First live event |
| C1–C5 | Access conflicts in §9 | My recommendations in §9 | Surbhi | The BA's permission rules |

## Assumptions

- `[ASSUMPTION]` The event customer runs Frappe CRM on an Alvora tenant (DevOps Q2).
- `[ASSUMPTION]` Organisers today use paper or Google Forms; no evidence either way.
- `[ASSUMPTION]` A 60% entry rate is a fair first target; no baseline exists.
- `[ASSUMPTION]` The organiser is the Data Fiduciary and Alvora the processor.
- `[ASSUMPTION]` CRM's owner/assignee rule (seen in slice 057) means Sales Users see no guest-created lead. To be confirmed on a fresh site.
- `[ASSUMPTION]` Frappe logs report exports.

## Kill criteria

- No named organiser by the gate → ship the configuration version only, or drop.
- The 300-in-5-minutes test fails on dev even with the per-event limit, because of the shared worker slots → stop and come back with numbers.
- Counsel says tick-box consent on a public form is not enough, or minors cannot be excluded → stop until the notice is fixed.
- First real event: fewer than 30% of the room submit → the form is the wrong tool; find out why before adding anything.

## Subtract pass

Removed: an Event DocType (the CRM form is the event); a date window that closes the form by itself (manual unpublish does it); a honeypot field (no spam measured); automatic retry (kept only "do not clear on error"); a live count for door staff (moved to conflict C1); a dashboard (a saved report view does it); an export log of our own (Frappe's, if it exists). I kept "Download QR", though it is the most cuttable item: without it the organiser depends on a third-party generator, and dynamic ones expire.

## Handoff note

To the UX designer: design only the five fixes in §7 and the saved manager view; everything else is CRM as it ships. To security: §9 is the access intent; G2 and the guest save path are the two doors that matter. To the BA: one form per event, three leads per repeat attendee, no new record type, unless Surbhi says otherwise at the gate. If MK1 comes back "no named customer", stop after the setup guide.
