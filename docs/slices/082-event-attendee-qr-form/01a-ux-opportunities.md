# Slice 082 — Event attendee QR form · UX opportunities scan

**Author:** `hrms-ux-designer` · **Date:** 13 Nov 2026 · **Mode:** opportunities scan (no prototype)
**Feeds:** `hrms-product-manager` → `01-product-brief.md`. The PM decides what goes in. I do not.
**Learnings applied:** checklist "QR in India: plan for a UPI code scanned by mistake"; "a list that
ships empty… for a public form it is also the safe one"; slice 078's "a public page collecting
contact details is a DPDP question"; "read the eligibility gate, not just the flow".

---

## 0. The answer first

**Frappe CRM already ships a public, no-login form builder that turns each submission into a CRM
Lead.** It is in our image (CRM v1.84.0): organiser staff build a form in `/crm`, publish it, and
it lives at `/crm-form/<route>`. That is rung 1 of the ladder. This slice is mostly about the gaps
around it, not a new form.

**Four things stop it working at a real event as it stands. Two are P1:**

| # | Gap | Severity | Evidence |
|---|---|---|---|
| G1 | **Frappe refuses the 11th submission per minute from one internet address, per form.** A hall on venue Wi‑Fi shares one address. 300 people at the end of a talk: about 290 see an error. | **P1** | Fact, read in code: `web_form.py:741` `@rate_limit(key="web_form", limit=10, seconds=60)`; `rate_limiter.py:140-147` keys on IP + form name. Our nginx passes the real client IP. Not run. |
| G2 | **A Sales Manager can publish the staff user list to the internet with one click.** The builder offers "grant guest access" for any Link target on CRM Lead, and `lead_owner` links to **User**. The page then prints up to 500 names into public HTML. | **P1** (data door) | Fact, read in code: `crm/api/form.py:268-300`, `crm_form.py:14,95-130`. Not run. → `hrms-security-privacy-engineer` |
| G3 | **Nothing ties a lead to an event.** CRM Lead has no event or campaign field. The form stamps Source = "Web Form" only; which form was used is not kept on the lead. | P2 | Fact: CRM Lead field list; `form.py:565-600` |
| G4 | **The page is a desktop form, not a phone form.** Inputs 14 px (iPhones zoom in below 16), button ~34 px tall, 16 px checkbox, 13 px labels, a "Discard" button beside Submit that wipes everything, error text hard-coded English. | P2 | Fact, read in CSS/JS of `crm_form.html:72-146, 241, 588`. **Not rendered** — see §1. |

---

## 1. Current state — what we already have

**I could not see any of this on a running site.** CRM is not installed on `ppj.localhost`; it is
in the `hrlocal-328` container's apps but not installed on its site either. Everything below is
read from source, version-pinned. A screenshot pass needs CRM installed on a local site (an
engineer's five minutes; I did not change any data).

| Surface | Who uses it | Does part of the job? | Fact / gap |
|---|---|---|---|
| **Frappe CRM → Forms** (`crm/api/form.py`, `www/crm_form.py`) | Sales Manager builds; guest fills | **Yes — the core.** Public, no login, `allow_multiple=1`, sections/columns, conditional fields, success message or redirect, iframe embedding, draft preview | Gaps G1–G4. No QR. No offline. No per-form fixed value except for mandatory system fields (Status) |
| **Frappe standard Web Form** (desk, any doctype) | System Manager | Yes, but Desk-only to build | Supports hidden field + default (`web_form.py:140`). Same rate limit. CRM's form already wraps it, so this is the fallback, not the choice |
| **ERPNext Lead / Campaign** | ERPNext CRM users | Partly: Lead has `utm_campaign`, and there is a Campaign record | Different app from the CRM Amata uses (057). Two lead lists in one tenant would be "one idea under two names". **Do not use** |
| **Frappe core "Event"** | Calendar | No — a calendar entry | Word collision. Do not link leads to it |
| **Our email/WhatsApp lead intake** (`ai_leads/`, slices 043, 057) | Founders, sales | No | Its duplicate check (`intake.py:301`, same email → existing lead) is a pattern worth reusing for repeat attendees |
| **Feature gate** `ERPNEXT_FEATURES["crm"]` (`subscription.py:394`) | Platform | — | A tenant must have CRM switched on. The event customer is a CRM tenant, not an HR one |

---

## 2. Competitors — whole products

**No product screenshots were available; every claim is "read" from vendor or marketing pages on
13 Nov 2026, or recall.** Ratings reflect what each company shows the market.

| Product | Attendee on the phone | Organiser staff | Manager across events | Label |
|---|---|---|---|---|
| **Zoho Backstage** (+ Zoho Survey) | QR at venue → survey; walk-in registration by staff; per-attendee QR badge | Check-in staff role limited to check-in and badges | Event reports in Backstage; surveys live in a **separate product**, linked by Zapier | read, 13 Nov 2026 |
| **Eventbrite** | Ticket QR scanned at the door; **no built-in feedback survey** — third-party (SurveyMonkey, Zoho Survey) by email after | Organizer app = scanner + guest lookup + door sales | Ticket/attendance reports; ratings "gradually rolling out" | read, 13 Nov 2026 |
| **HubSpot** | QR → a HubSpot form or landing page; **no built-in QR generator** | One form, **hidden "event" field** set per landing page, rather than one form per event; then a list "Event = X" | Lists and attribution by UTM | read, 13 Nov 2026 (vendor and community pages) |
| **Google Forms + Sheets** | QR → form; works on any phone; **no offline**; language = form text | One form per event, copied | Sheet per form; no cross-event view without work | `[recall — verify]` |
| **Typeform** | One question per screen, very phone-friendly; slow on 3G | Hidden fields from the URL (`?event=…`) | Per-form results; CRM by integration | `[recall — verify]` |

**Patterns worth borrowing:** HubSpot's *one form, an event value in the link* (fewer forms to
maintain); Zoho's *walk-in by staff* fallback for people with no signal; Eventbrite's honesty that
check-in and feedback are **two moments**.

**What not to copy:**
- Zoho's and Eventbrite's split of event and survey into two products joined by Zapier. Our
  promise is one record per attendee per event, in the CRM, without glue.
- Typeform's one-question-per-screen. Each screen is a round trip; on venue Wi‑Fi that is five
  chances to fail instead of one.
- Free QR generators. HubSpot users report codes that **stop working** unless they pay — a printed
  banner would die mid-event.
- Ticketing, badges, seat maps. Not asked for.

---

## 3. Ideas, persona by persona

Size: S under a day, M a few days, L a week or more. Rung = ladder step.

### 3.1 Attendee — public, on their own phone, standing in a hall, often on poor signal

| # | Idea | Job it serves | Evidence | Size · rung |
|---|---|---|---|---|
| A1 | **One short screen:** name, mobile, email (optional), "How was it?" as five worded buttons, one comment box, consent. Submit. Thanks. Under 60 seconds | "Let me give my details and go" | CRM form already does the shape; G4 is the gap | S · 2 (config) |
| A2 | **Phone floors on the CRM page:** 16 px fields, 48 px buttons, full-width Submit, **remove Discard** | Finish it with a thumb, no zoom | G4 | S · 3–4 (a stylesheet override; engineer to say if CRM allows it without forking) |
| A3 | **Bilingual labels typed by the organiser** ("Your name / आपका नाम") rather than a language switch | Hindi-first attendee can fill it | Labels are free text in the builder: zero code | S · 2 |
| A4 | **Keep what was typed if sending fails, and retry by itself;** a clear "Not sent yet — we will try again" line; never clear the form on an error | Venue Wi‑Fi drops at the exact moment 300 people press Submit | Learnings: never silently discard; CRM page shows a generic error | M · 4 |
| A5 | **The link keeps working after the event** (no expiry), and the thanks screen says so — "No signal? This link works until <date>." | Fill it on the way home | Cheapest offline answer; no app | S · 2 |
| A6 | **Under the printed QR: "Scan to register for <event>. This is not a payment."** | A QR in India is read as a UPI code | Checklist item from slice 013 | S · print only |
| A7 | **Thanks screen names the event and what happens next** ("Thank you. <Organiser> will send the slides to your email.") — only if true | Know it worked | CRM success message is configurable | S · 2 |

### 3.2 Organiser staff — set up the event, print the QR, stand at the door

| # | Idea | Job it serves | Evidence | Size · rung |
|---|---|---|---|---|
| S1 | **"Download QR" beside the form's public link**, a PNG that never expires | Print a banner without a third-party site | No QR in CRM forms (fact). Frappe already bundles a QR library for 2FA `[recall — verify]` | S · 4 |
| S2 | **The event is set in the link, not chosen by the attendee** (HubSpot pattern): either one form per event, or one form with `?event=` stamped on the lead | Every entry lands on the right event with no attendee effort | G3 | S–M · 3–4. ⚠ Q2 |
| S3 | **"Test it from your phone" check before printing** — the draft preview already exists | Find the broken field before 300 people do | `crm_form.py` draft preview (fact) | — · 1 (already there; say it in the setup guide) |
| S4 | **Walk-in entry by staff** on their own phone, same form, when an attendee has no signal | Nobody is lost at the door | Zoho pattern | — · 1 (staff open the same link) |
| S5 | **Live count on the form's row** ("142 entries today") | Know it is working during the event | CRM list view count, filtered by event `[ASSUMPTION]` | S · 2 |

### 3.3 Organisation manager / CXO — reads results across many events

| # | Idea | Job it serves | Evidence | Size · rung |
|---|---|---|---|---|
| M1 | **One table: event · entries · average rating · comments needing a reply**, newest first, one tap into the leads for an event | "Which events worked?" | Report Builder group-by on the event field `[ASSUMPTION: works on CRM Lead]` | S · 2 |
| M2 | **Low ratings first** ("4 people rated Mumbai 1 or 2 — read them") — exceptions before lists | Act on the unhappy ones | Principle 5 | S · 2 (sort/filter) |
| M3 | **Repeat attendees visible** ("Seen at 3 events") on the lead | Spot the warm prospect | Our intake's email match (fact) | M · 4. ⚠ Q3 |

### 3.4 Employee portal

**It does not fit, and I recommend leaving it out.** The attendee is not an employee; organiser
staff work in `/crm`; the manager reads CRM reports. Putting event results in the HR portal would
add a door for no job.

---

## 4. The thin flow, and the choices that shape it

```
Scan QR ──► form (1 screen, ~6 fields, bilingual labels) ──► Submit ──► Thanks (names the event)
                 │                                  │
                 └ no signal: link works later (A5) └ send fails: keep answers, retry (A4)
```

| Choice | Options | My recommendation |
|---|---|---|
| **Registration vs feedback** | (a) one form, feedback optional; (b) two forms, gate and exit; (c) two forms joined by mobile number | **(a)** for the first slice. (b) makes two leads per person; (c) is matching code. Ask the customer when their attendees scan — ⚠ Q1 |
| **Event link** | (a) one form per event; (b) one form, event in the URL | **(a)** if events have different questions; **(b)** if every event asks the same. Either needs a small stamp on the lead (G3) |
| **Repeat attendees** | (a) a new lead every time; (b) match on mobile, add a note to the existing lead | **(a)** matches the brief's words ("each submission becomes an entry"); (b) keeps the sales list clean. ⚠ Q3 |
| **Language** | (a) bilingual labels; (b) a switch | **(a)**. System words (Submit, errors, "required") still English until translated — count them, not the portal |
| **Consent** | Notice in the intro; **one unticked "I agree"** to record details for this event; **a second, separate, unticked tick** for "Send me news of future events" | Never pre-ticked (refusal). The notice names the **organiser** as the collector, the purpose, how long it is kept, and a contact to withdraw. Retention is a policy gap — ⚠ Q4 |

**Draft words** (English, then Hindi — **machine-drafted, needs a native reviewer**):

| Where | English | Hindi |
|---|---|---|
| Consent tick | I agree that <Organiser> keeps these details for this event. | मैं सहमत हूँ कि <Organiser> इस कार्यक्रम के लिए ये जानकारी रखे। |
| Marketing tick | Send me news of future events. (Optional) | मुझे आगे के कार्यक्रमों की जानकारी भेजें। (वैकल्पिक) |
| Thanks | Thank you. Your details are saved for <Event>. | धन्यवाद। आपकी जानकारी <Event> के लिए सहेज ली गई है। |
| Not sent | Not sent yet. Keep this page open — we will try again. | अभी नहीं भेजा गया। यह पेज खुला रखें — हम फिर से कोशिश करेंगे। |
| Under the QR | Scan to register for <Event>. This is not a payment. | <Event> के लिए स्कैन करें। यह भुगतान नहीं है। |

---

## 5. Privacy and data doors (flag for security)

- **The attendee sees only their own answers and a thanks screen.** No list, no count, no other
  name. Keep it that way.
- **G2** (guest access to the User list) is the one screen-shaped data door. Recommend: never offer
  the grant for `User`, or hide `lead_owner` from the field picker. `hrms-security-privacy-engineer`.
- **Who among organiser staff reads which event?** In slice 057 a Sales User saw only leads they own
  or are assigned. Form leads are created by Guest, so a plain Sales User may see **none** of them.
  The PM's access table must say who reads what.
- **A public form with no captcha** is protected only by the limit in G1. Raising it for a crowd
  also raises it for a bot. That trade is the security engineer's, not mine.

---

## 6. Questions for the PM

| # | Question | Why it changes the design | Temporary assumption |
|---|---|---|---|
| Q1 | When do attendees scan — at the door, at the end, or both? | One form or two; whether feedback is asked before the event happened | One scan, at the end |
| Q2 | Does an "event" need more than a name and a date (venue, capacity, organiser)? | Name + date fits the form title; more means a record of its own | Name + date only |
| Q3 | Same person at three events: three leads, or one lead with three entries? | Sales list clutter vs. the brief's literal words | Three leads |
| Q4 | How long does the organiser keep attendee data, and who deletes it? | The consent notice cannot be honest without it (slice 078's lesson) | Blocks switch-on |
| Q5 | Is G1 acceptable to raise per form, and to what? | Decides whether a 300-person rush works at all | Must be raised; security sets the number |

## 7. Not in this slice (for the user to decide)

Ticketing and check-in scanning · badges · per-session feedback · NPS dashboards · AI summary of
comments · WhatsApp follow-up · an offline app. None is needed to record attendee details and
feedback against an event.

## 8. Three personas, one line each

- **CXO / manager:** one table across events (M1), low ratings first (M2).
- **HR Manager equivalent (organiser staff):** a form per event and a QR they can print (S1, S2).
- **Employee (here: the attendee):** one phone screen, in their language, that does not lose their
  answers.

## 9. Subtract pass

Removed: an "event home page" idea (the form's intro does the job); a per-event settings screen
(the CRM form is the settings); a language switcher (bilingual labels cost nothing); an
employee-portal row (no job); a kiosk mode for a shared tablet (staff can open the same link, S4);
a separate Hindi form per event.
