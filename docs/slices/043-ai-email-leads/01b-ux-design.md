---
slice: 043-ai-email-leads
artifact: 01b-ux-design
author: hrms-ux-designer
date: 2026-09-24
status: draft — recommendation only; Surbhi decides at the design check
inputs: [01-product-brief.md (§5 WOW, §6 thin slice, §10 — arrived while this was written), 07-devops-inputs.md §1–§3 (OPS-1, OPS-12 — same), 02-functional-spec.md (§4–§8, §13, "Decisions taken by the user, 24 Sep 2026"), 01c-security-privacy-requirements.md (§2, §3, SEC-8, SEC-10, SEC-16, SEC-17, PRIV-1, PRIV-8, PRIV-9), .claude/context/ux-learnings.md, product-context.md §2 and §6, nfr-budget.md §2, §5, §6, §7, handoff-contract.md, docs/sargam_metals/02-ceo-demo-storyline.md §6, alvoraa_portal/.../design_system.html (read, deliberately not used — see §3)]
---

# 043 — AI email leads: the design, with a clickable prototype

**Prototype:** `C:/Surbhi-Git/hr-app/docs/slices/043-ai-email-leads/prototype-043.html`
(one file, opens in any browser, no server). It holds **only invented data** from the
Sargam storyline, so it may live in the repo (the 15 Sep 2026 rule). **No Artifact tool
was available in this run; the session that ran me publishes it and gives Surbhi the
link.**

**Bad news first.**

1. **This design was written out of order, in parallel with the brief.** The contract
   wants `01` → `01b` → `01c` → `02`. Here `02` and `01c` existed first, and
   `01-product-brief.md` and `07-devops-inputs.md` landed in the folder while this was
   being written. I designed to the spec and the user's seven decisions of 24 Sep 2026,
   then read the brief before handing off: its §6 thin slice, §10 reconciliation
   (rows 1, 3, 7) and OPS-1/OPS-12 agree with what is drawn. Where `02` and `01c`
   disagree with each other, I did not pick one quietly: §11 lists the seven
   conflicts, each with my recommendation and an owner.
2. **Screen 3 (the lead page inside Frappe CRM) rests on one unverified fact:** that the
   CRM's "Fields layout" setting can show our read-only custom fields (Percent, Link,
   Small Text, Select) on its Vue lead page with no CRM code change. The spec marks it
   `[verify]` too. If it cannot, the badge lives only in the desk form of the lead and
   the CRM app shows nothing — which breaks PRIV-8 for the people who actually work in
   the CRM. The engineer must check this before the strategy (`00`).
3. **No current-state capture from the bench.** The task said no bench, no server. The
   local instance does not have the CRM installed anyway (`03-crm-install-notes.md` puts
   it on `sargam.dev.alvoraa.co`). Everything about how Frappe CRM looks is from its
   source and public screenshots read on 24 Sep 2026, labelled in §4.

---

## 1 · Frame

**A Sales Manager at Sargam Metals (Rohan Deshmukh, fictional), on a laptop between
calls or on his phone at a customer's yard, wants to clear the five emails the AI was
not sure about — accept the real enquiries, throw out the rest — in under five minutes,
and be certain nothing real was dropped.**

Two supporting jobs: the tenant admin (Priya Nair, System Manager) switches the feature
on for one mailbox, names Rohan, and can stop it in one action; the Sales User (Meera
Iyer) opens an AI-created lead and can tell at a glance what a machine wrote, how sure
it was, and who checked it.

**Personas in scope:** tenant admin (System Manager), Sales Manager (the named
reviewer), Sales User. **Deliberately out:** Employee, HR Manager, CXO without a Sales
role — they see none of these screens, by the spec's permission matrix (§7) and PRIV-2.
The three-persona check therefore reads: **CXO — nothing changes unless they hold a
Sales role; HR Manager — nothing changes, and must not; Employee — nothing changes, and
must not.** No frontline persona: nobody on a shared Android is asked to review leads.
The phone rules still apply to the review queue, because a Sales Manager travels.

**Which slice.** D-7 says slice one is the core loop on one mailbox: opt-in, rule
screen, extraction, lead creation with the email attached, review queue, audit fields.
Slice two adds several mailboxes, cross-sender dedupe, backfill, the cost cap and the
kill switch. This design draws slice one fully and shows the slice-two controls **where
they will sit**, labelled "next release", so the settings page does not have to be
redesigned twice. See conflict C6 in §11.

---

## 2 · Evidence

| What | Where | Label |
|---|---|---|
| Frappe desk look (navbar, form sections, buttons, list) | Frappe `version-16` source, desk CSS variables read 24 Sep 2026; my own use of the desk on `ppj.localhost` in earlier reviews | read + seen (earlier runs) |
| Frappe CRM lead page layout (sidebar, activity tabs, right-hand details panel, status button, "Convert to deal") | Frappe CRM `v1.84.0` source (`crm_lead.json`, front-end routes), public screenshots on github.com/frappe/crm read 24 Sep 2026 | read |
| CRM "Fields layout" and whether custom fields render | Spec §15 `[verify]`; not checked by me | `[recall — verify]` |
| Sargam sample data (Konkan Shipbuilders, Western Port Trust, Gulf Marine, Pipeline Infra Co, Andaman Ferries, anodes, USD pricing) | `docs/sargam_metals/02-ceo-demo-storyline.md` §6 | read; all fictional |
| Prototype renders, measured | `C:/Surbhi-Git/hrlocal-data/ux-review/2026-09-24/043/` — 40 PNGs: 4 screens × desktop/phone × light/dark × 3 people, 8 states, 2 dialogs, Hindi at 390 px, and a real 360 px window | seen, measured (§8) |

**Measured, not eyeballed (P4):** after fixes, no target under 24 px on desktop or
44 px on the phone, no text under 12 px, no sideways scroll at 390 px in the frame or in
a real 360 px window, no script errors across 109 measured renders. The first pass found
a 528 px mailbox table overflowing the phone, a 367 px `<select>` in the review bar
pushing a 360 px window to 381 px, 15 px breadcrumb links, a 10 px badge and two
10–11 px labels — all fixed before this handoff. Looking (not measuring) found two more:
the desktop queue showed one column instead of two, and the phone detail opened 20 px
scrolled so the back button was clipped. Both fixed.

---

## 3 · Surface decisions — which Frappe surface each screen lives on, and why

Frappe CRM is a Vue app with its own look; the Frappe desk looks different. A person
sees both. The rule I used: **put a screen where the person who uses it already is,
unless that would need a change to Frappe CRM's own source.** Changing CRM source means
a fork of an AGPL app that we did not write and must upgrade — the slice-040 rule
("never uninstall on a live tenant") has a sibling: never patch it either.

| Screen | Surface | Why here | What the other surface would cost |
|---|---|---|---|
| 1 · Settings | **Desk** — the `FCRM Settings` form (tenant-wide fields) and the `Email Account` form (per-mailbox tick) | The tenant admin already configures mailboxes in the desk; desk forms show custom fields, sections, `depends_on` and `Version` history with zero front-end code (spec §5.3, G-7). The refusals (HR mailbox, both hooks on) are `validate` rules and surface as desk messages | The CRM app's settings dialog is a Vue component; adding fields means CRM code |
| 2 · Review queue | **Desk page** we own (`/app/ai-lead-review`, a Frappe `Page` under `alvoraa_portal`) | Needs a side-by-side email + fields view, per-field confidence, Accept / Reject / Edit-then-accept, a reason line, and a phone layout. None of that exists in the CRM's list or kanban, and adding it means CRM code. A Frappe Page is ours: our HTML, our CSS, our two whitelisted endpoints, and it inherits desk login, roles and the bell | Stay in the CRM app: the reviewer would open each "Needs review" lead, read the email in the activity tab, scroll to the fields on the right, then change the status by hand — six taps and no confidence per field, no reason line, no one-click reject with a recorded reason |
| 3 · Lead page | **CRM app** — Frappe CRM's own lead page, unchanged | The Sales User works here. We add only what the CRM already renders: a group of read-only custom fields ("AI intake") shown through its Fields layout setting `[verify]`, one ordinary note, the email in its own timeline | A desk-only badge would be invisible to the people who work the leads — PRIV-8 says anyone who can read the lead must see that AI filled it |
| 4 · States | Same surfaces as the screen they belong to | — | — |

**The bridge between surfaces.** The CRM app's sidebar gets a saved view "Needs
review" (filter `status = Needs review`, spec §5.4 status record, G-6 — configuration,
not code) with a count; its rows are ordinary CRM leads. The bell notification N-1
("1 email needs your review: {subject}") links to the **desk review page** for that
lead. The lead page in the CRM shows the same intake state in the AI block. So a person
who lives in the CRM sees the count where they are, and one tap takes them to the page
built for the decision. This is the design's biggest bet; §10 tests it.

**On the Alvoraa design system (P3).** `design_system.html` is the **portal's** palette.
Neither the desk nor the CRM app uses it, and painting Alvoraa purple onto a desk page
would make one page in the desk look foreign. So the prototype draws the desk with the
desk's own greys, black primary button and Inter type, and the CRM page with the CRM's
look. This is a deliberate exception to P3, for consistency with the surface the person
is standing on (priority ladder #9 says consistency with the design system never
excuses a design wrong for the context). The one Alvoraa token used is the brand mark
colour in the top-left corner, which the desk already shows.

---

## 4 · Benchmark — labelled

No trial accounts; these are what each product shows the market. Read 24 Sep 2026
unless marked.

| Product | What it does for email → lead | Label | Take or leave |
|---|---|---|---|
| **Frappe CRM v1.84.0** (our base) | Every unknown sender becomes a lead when the mailbox tick is on; no classification, no extraction; leads carry `first_name`, `email`, `source = Email` only | read (source) | The problem we are fixing. We switch this off on our mailboxes (spec G-3) |
| **Zoho CRM — Zia email parsing** | Parses inbound mail into lead fields; shows a confidence-free "parsed" record; the user corrects fields on the record itself | `[recall — verify]` | Take: fields land on the real record. Leave: no per-field confidence, no reason |
| **HubSpot — inbox / AI lead capture** | Conversations inbox; AI summarises the thread; lead creation is a button, not automatic | `[recall — verify]` | Take: the summary sits on the timeline as a labelled note. Leave: the human still types the fields |
| **Freshsales — Freddy AI** | Scores leads; scoring shown as a number with "top factors" listed | `[recall — verify]` | Take: factors in words beside the number. Leave: **lead scoring / ranking** — out of scope (spec §14) and close to a refusal in spirit |
| **Keka / Zoho People / Darwinbox** (HR suites, per P2) | No email-to-CRM-lead feature; not relevant to this slice | read (product pages) | — |

**What we deliberately do not copy:** a lead **score**; a "confidence" shown as a
colour only; auto-created leads with no trace of who or what created them; a review
that happens by editing the record silently (no recorded decision). Ours shows the
number, the reasons in words, the person who decided, and keeps the AI's original
answer in the log.

---

## 5 · Findings — what the spec's screens would have been without a design

IDs: `ST` settings, `RQ` review queue, `LP` lead page, `SX` states.

| ID | Finding | Impact | Kind | Size | Severity | Evidence |
|---|---|---|---|---|---|---|
| RQ1 | The spec's review flow is "CRM list filtered by status + lead page actions" (US-4). The CRM lead page has no place for Accept/Reject, no per-field confidence and no reason line; the reviewer would read an email in one tab and fields in a panel and guess | High | New | M | P1 — core journey | Spec §8 US-4 "Screen" column; CRM `crm_lead.json` has no such fields |
| RQ2 | The reasons the model gave (`reasons[]`) are stored in the log only (spec §5.1) which a Sales User cannot read (§7, AC-36). "Why this looked like a lead" would be blank for the lead owner | High | Fix | S | P1 — breaks "explain every number" | Spec §5.1 vs `01c` SEC-16 |
| RQ3 | A fallback lead (AI down, cap) has no confidence and only header fields; without a distinct state it would look like the AI read it and found nothing | Medium | New | S | P2 | Spec U-2, U-3 |
| RQ4 | A phone number the model invented is dropped by code (AC-9) but nothing tells the reviewer a value was removed; they might re-type the same wrong number from memory of the list | Medium | New | S | P2 | AC-9, SEC-3 |
| ST1 | The switch-on notice (PRIV-1) must be accepted and recorded; the spec's field list has no acceptance field or version | High | Fix | S | P1 — privacy | `01c` PRIV-1; spec §5.3 |
| ST2 | The HR-mailbox refusal (SEC-8) is a `validate` error; on the settings overview the admin would not know why a mailbox is unavailable until they try | Low | Improve | S | P3 | `01c` SEC-8 |
| ST3 | Today's usage and cost are in the log only; the admin has no number to look at before raising a cap | Medium | New | S | P2 | Spec US-8 |
| LP1 | Provenance fields exist (SEC-16) but nothing says where they appear on the CRM page or what they say to a Sales User | High | New | S | P1 — PRIV-8 | `01c` PRIV-8; spec §15 |
| SX1 | No empty state, error state or no-permission state is written anywhere | Medium | New | S | P2 | — |
| RQ5 | **Keep:** the email is stored once on the `Communication`; the lead fields are a derived copy the salesperson may edit; the log keeps the AI's original. One truth per thing | — | Keep | — | — | Spec §3 "single source of truth" |
| ST4 | **Keep:** switch-off requires a reason and writes a `Version` row (AC-47/48), the slice-013 pattern | — | Keep | — | — | Spec §5.3 |

---

## 6 · Flows, with every state

### 6.1 Tenant admin switches it on (Screen 1 + state "First switch-on")

1. Opens CRM Settings in the desk. Sees "AI lead intake — Not switched on for Sargam
   Metals" if the feature is not sold (state `notbought`): explanation, then "Ask about
   it". No greyed control (learning: "a feature the tenant has not bought lives in
   settings under 'Not switched on for …'").
2. If sold: the notice card "Before you switch on AI lead intake" — what is sent, to
   whom, retention, the tenant's own duty — a checkbox "I accept this on behalf of
   Sargam Metals (notice v1)", the reviewer field (required), and the button "Switch on
   AI lead intake". Both must be filled; the button explains what is missing in a toast
   and moves focus to the field (N-8 wording).
3. Then: the "On" card, but with the banner "On, but no mailbox is ticked" until a
   mailbox is ticked in its own Email Account form (System Manager only). The banner
   carries the link to that form.
4. Ticking the mailbox: Frappe's validate refuses if CRM's own "Create Lead from
   Incoming Emails" or an `append_to = CRM Lead` folder is on (N-7 wording), or if the
   mailbox is HR-shaped (SEC-8). The refusal names the rule, not "validation failed".
5. History lists every change with name and time. Copy says honestly "Only the
   Administrator account can delete these records" (slice-012 learning).

**Turn off (kill switch):** one red-outlined button "Turn off AI lead intake" → dialog
that says what stops, what continues (mail still arrives; leads already made stay; the
queue stays for Rohan), a required reason (Select) and an optional note → "Turn off".
Without a reason: "Say why AI lead intake is being switched off." (AC-48).

### 6.2 Reviewer clears the queue (Screen 2)

Happy path, desktop: bell → "1 email needs your review: {subject}" → the desk page
opens on that email, list on the left (oldest first), detail on the right. The detail
leads with **why it needs a person** (amber box), then the email on the left (plain
text, exactly what the AI saw, with the phrases the AI used highlighted) and the fields
on the right (each with its confidence and "found in the email" phrase). Three actions:
**Accept** (primary, one click), **Edit, then accept**, **Reject**.

- **Accept** → toast "Accepted. Now a New lead, assigned to Meera Iyer. [Open lead]".
  The next email in the list is selected; focus lands on its subject.
- **Edit, then accept** → the fields become inputs (the email stays visible), buttons
  become "Save and accept" / "Cancel edit". Edits are recorded as `Version` rows.
- **Reject** → dialog: "Reject this lead? It moves to Junk in the CRM. The email stays
  on the mailbox timeline. You can reopen the lead in the CRM if this was wrong." A
  reason Select (Not an enquiry / Spam / Supplier or vendor offer / Duplicate / Other)
  feeds the accuracy signal; "Reject and move to Junk" / "Cancel".

Phone (390 px): the list is the page; tapping a row opens the detail full-screen with
"‹ Back to list", the why-box, then two tabs **Email | Extracted fields**, and a sticky
bottom bar with the three buttons (44 px, the primary one first). "Edit, then accept"
switches to the Fields tab.

Unhappy paths and states (all drawn on Screen 4):

| State | What the person sees |
|---|---|
| Empty | "Nothing to review" · what this area is · why it is empty ("the AI was sure about every email since 22 Sep 2026: 14 became leads, 31 were not enquiries") · "See today's AI-created leads" |
| Loading | Skeleton rows within 300 ms; list in ≤ 1.5 s on broadband (nfr §2) |
| AI unavailable | Red-edged banner: since when, that leads still arrive as "Needs review" with header fields only, that we retry on our own, that the admin was told once (AC-27). Rows show "AI: not read" instead of a percentage; the why-box says the email was not read |
| Daily limit reached | Amber banner: reached at 17:20, what happens to later emails (not sent later — the reviewer fills them in), resets at midnight India time, how to raise the limit, "Never treat as leads" for a flooding sender |
| Not allowed to decide | A Sales User who is not the owner or the reviewer sees the email and fields (they can read the lead) but no buttons; instead "Only Rohan Deshmukh (reviewer) or a Sales Manager can decide this one." No button that would fail (learning: no button where the rule says no) |
| Not allowed at all | Employee / HR Manager: the desk shows no CRM workspace; a typed URL gets Frappe's standard "Not permitted" page; the API answers 403 (AC-39–41). Nothing custom, nothing to leak |
| Network dropped on Accept | "Could not reach the server. Your decision on '{subject}' was not saved. Nothing has changed on the lead. Check your connection and try again; your edits are kept on this screen." Buttons: Try again / Keep for later. Leaving the page with unsaved edits warns |
| Long names, Hindi | A 60-character organisation and a Hindi UI rendered at 390 px; measured, nothing wraps out of its box. Devanagari strings are ~30 % longer; the sticky bar still fits three buttons at 390 px but at 360 px "बदलें, फिर स्वीकार करें" wraps to two lines — acceptable, still ≥ 44 px, noted for the native reviewer |
| 400 rows (spam night, E-21) | The list paginates at 20 (spec §11) with "Load more"; a bulk "Reject all from this sender" is **not** in slice one — the ignore list in settings is the tool; noted as a slice-two candidate |

### 6.3 Sales User opens an AI-created lead (Screen 3)

CRM app, lead page. Top of the right-hand panel: the **AI intake** block — "AI ·
Created from an email by AI" · Confidence 87 % · Reviewed by Rohan Deshmukh, 23 Sep
2026, 14:02 (or "Auto-accepted (no reviewer)") · Why reviewed · Mailbox · Email (a
link to the timeline item) · for Sales Manager and System Manager only, "Open the AI
record" · and the fixed line **"Filled from an email by an AI model. Check before you
rely on it."** (PRIV-8). The activity tab shows the email, the note "What they asked
for (AI summary)" prefixed "AI-generated summary — check against the email above", and
the review event with what was changed.

---

## 7 · Screen-by-screen words (English first, Hindi drafts marked)

Hindi strings are **machine drafts for a native reviewer** (open item, as in every
earlier slice). Everything goes through `_()`.

### 7.1 Settings (desk, FCRM Settings section "AI lead intake")

| Element | English | Hindi (draft) |
|---|---|---|
| Section title | AI lead intake | AI लीड इनटेक |
| Status line, on | On · Reading 1 mailbox. Uncertain leads go to {reviewer}. | चालू · 1 मेलबॉक्स पढ़ा जा रहा है। अनिश्चित लीड {reviewer} को जाती हैं। |
| Under it | Turning it off stops every AI call at once. Emails keep arriving in the mailbox as normal; none is sent to the AI and none becomes a lead until it is turned on again. | — (native) |
| Button | Turn off AI lead intake | AI लीड इनटेक बंद करें |
| Today card | {n} of {cap} emails sent to the AI today · Resets at midnight, India time. About ₹{x} spent so far today (₹0.25 an email). When the limit is reached, emails still become leads marked "Needs review", without the AI reading them. | आज AI को {n} में से {cap} ईमेल भेजी गईं |
| Field | Emails per day sent to the AI · hint: Cost stop, not a data stop. Alvoraa's ceiling is 500. | प्रति दिन AI को भेजी जाने वाली ईमेल |
| Field | Reviewer for uncertain leads · hint: Must hold Sales Manager or Sales User. Any Sales Manager can also decide. This person gets a bell notification per email. | अनिश्चित लीड के लिए समीक्षक |
| Field | Auto-accept when the AI is at least (%) · hint: Above this, the lead is created as New with no review. Below it, {reviewer} decides. | — |
| Field | Treat as "not an enquiry" when the AI is at least (%) · hint: Above this, no lead is made. The email stays in the mailbox as today. Nothing is deleted. | — |
| Mailboxes | Each mailbox is switched on in its own form (Email Account), by the tenant admin only. A mailbox used for HR or payroll mail is refused by the system, not by a warning. · states: On / Off / Cannot be used | चालू / बंद / उपयोग नहीं हो सकता |
| HR refusal | Cannot be used: "hr" is a protected mailbox name (HR and payroll mail must never go to the AI). | — |
| Ignore list | Never treat as leads · Addresses or domains, one per line · These are skipped before the AI sees them. Newsletters, auto-replies and your own domain are skipped automatically. | लीड न मानें |
| Data card | What is sent, and to whom · Only the email's subject, the sender's name and domain, and its plain text (up to 6,000 characters) are sent to {provider} to read it. Attachments, other recipients and headers are not sent. The provider keeps the text for up to 30 days and does not train on it. · Accepted by {name} on {date} (notice v1). | क्या भेजा जाता है, और किसे |
| Turn-off dialog | Turn off AI lead intake? · All AI calls stop at once … · Why is it being switched off? (required) · options: Provider problem / Too many wrong leads / Cost / Testing / Other · Turn off | AI लीड इनटेक बंद करें? |
| Refusals | Say why AI lead intake is being switched off. (N-6) · AI lead intake replaces 'Create Lead from Incoming Emails' and the 'Append To CRM Lead' folder setting. Untick those first. (N-7) · Name a reviewer for uncertain leads. (N-8) | as spec §13 |

The retention sentence must render from the model constant (PRIV-3): "up to 30 days"
for a Covered Model, "not retained" only if ZDR is signed and the model allows it.
Never a promise the constant does not back.

### 7.2 Review queue (desk page)

| Element | English | Hindi (draft) |
|---|---|---|
| Page title | Leads to review · {count} | समीक्षा के लिए लीड |
| Filters | All mailboxes ({n}) · All reasons: Low confidence / Two organisations / Phone not found in email / AI unavailable / Daily limit reached · Oldest first | — |
| Row | {organisation or sender name} · {age} · {subject} · reason chip · "AI: 74 %" or "AI: not read" · owner if any | — |
| Detail header | From: {name} <p…@domain> [Show full address] · Received · Mailbox · chip "AI confidence 74 %" or "AI: not read" | भेजने वाला · मिला · मेलबॉक्स |
| Why box | **Why it needs you** — one of: "Confidence {n} % is below your auto-accept level of {t} %. The AI could not tell whether …" / "The email names two organisations: {A} and {B}. Only you can say which one is the lead. The AI never creates two leads from one email." / "The AI gave a phone number that does not appear anywhere in the email, so it was removed and the lead was sent to you." / "The AI service could not be reached at {time} … Nothing was read by the AI." / "Yesterday's limit of {cap} emails … was reached at {time}, before this one arrived." | आपकी ज़रूरत क्यों है |
| Email column | Email (plain text, as the AI saw it) · Attachments: {names} — not read by the AI, file name only · **Why this looked like a lead** + up to five reasons | ईमेल · यह लीड क्यों लगी |
| Fields column | Extracted fields — will become the lead · Email: always the sender's own address from the header. The AI cannot change it. · per field: value, {n} %, "{phrase}" found in the email / from your industry list / from the email header · blank: "Not in the email" · removed: "Removed: the number the AI gave is not in the email text." · free-mail: "Never taken from a free-mail domain (gmail.com)." · two organisations: chip "or: {B}" | निकाले गए फ़ील्ड · ईमेल में नहीं है |
| Footnote | Each percentage is how sure the AI was about that one value, and where in the email it found it. Anything you change is recorded against your name. | — |
| Buttons | Accept · Edit, then accept · Reject · (editing) Save and accept · Cancel edit · (phone) ‹ Back to list | स्वीकार करें · बदलें, फिर स्वीकार करें · अस्वीकार करें · सहेजें और स्वीकार करें · बदलाव रद्द करें · सूची पर लौटें |
| Rights line | You can accept or reject this one. / Only {reviewer} (reviewer) or a Sales Manager can decide this one. | इसे आप स्वीकार या अस्वीकार कर सकते हैं। / इसे केवल … तय कर सकते हैं। |
| Toasts | Accepted. Now a New lead, assigned to {owner}. [Open lead] · Rejected. Moved to Junk. [Reopen in the CRM] | स्वीकार। अब नई लीड, सौंपी गई {owner}. · अस्वीकार। Junk में भेजी गई। |
| Reject dialog | Reject this lead? · It moves to Junk in the CRM. The email stays on the mailbox timeline. You can reopen the lead in the CRM if this was wrong. · Reason (helps us see where the AI goes wrong) · Reject and move to Junk / Cancel | यह लीड अस्वीकार करें? |
| Empty | Nothing to review · Uncertain leads from the sales mailbox land here. Right now the AI was sure about every email since {date}: {a} became leads, {b} were not enquiries. · When an email needs a person, you will get a bell notification and it will appear here. · See today's AI-created leads | समीक्षा के लिए कुछ नहीं |

### 7.3 Lead page (CRM app, AI intake block)

| Element | English | Hindi (draft) |
|---|---|---|
| Block title | AI · Created from an email by AI | AI ने ईमेल से बनाया |
| Rows | Confidence {n} % · Reviewed by {name}, {date} **or** Auto-accepted (no reviewer) · Why reviewed: {one sentence} · Mailbox · Email: {subject, link} · AI record: Open the AI record (model {id}, prompt {version}) — Sales Manager and System Manager only | भरोसा · समीक्षा की · अपने-आप स्वीकार (कोई समीक्षक नहीं) |
| Fixed line | Filled from an email by an AI model. Check before you rely on it. | AI मॉडल ने ईमेल से भरा है। भरोसा करने से पहले जाँचें। |
| Note title | What they asked for (AI summary) · body prefix: AI-generated summary — check against the email above. | उन्होंने क्या माँगा (AI सारांश) |
| Review event | {reviewer} accepted this lead after review · Changed Phone from blank to {value} (typed from the signature). Status set to New. Assigned to {owner} by the assignment rule. | — |

### 7.4 Notifications (spec §13, confirmed as designed)

N-1 to N-8 as the spec proposes. Two changes: N-3 adds "We retry on our own; you do not
need to do anything" to stop admins toggling the switch; N-4 adds "Later emails still
become leads marked 'Needs review'". Subject line only, never body, phone or
organisation (AC-46, PRIV-9).

---

## 8 · Accessibility (WCAG 2.2 AA, nfr §7) and privacy on every screen

**Accessibility, checked in the prototype:**

- Every input has a visible `<label>`; every button has words (no icon-only control;
  the bell carries `aria-label` with the count).
- Keyboard: the list rows are buttons; the detail heading takes focus on selection
  (`tabindex=-1`) so a screen reader announces the subject; dialogs trap Tab, close on
  Escape, and return focus to the opener; the phone tabs use `role=tab` /
  `aria-selected`.
- Focus is a 3 px outline with 2 px offset on every control, both themes.
- Colour is never the only signal: every chip carries words ("Low confidence", "AI:
  not read"), every confidence bar has its number, the reason code is spelled out.
- Contrast, computed for the desk tokens I used: body text #1F272E on white 15:1;
  secondary #4C5560 7.6:1; muted #5B6770 5.5:1; link #1366AE 5.9:1; amber chip #7A4B00
  on #FDF1D6 7.1:1; green chip #0B5E3B on #DDF3E7 7.3:1; red #A8231A on white 6.1:1;
  dark theme #EAEAEA on #1E1E1E 14:1, link #7CB8F0 8.0:1. All ≥ 4.5:1. **The real desk
  page must use Frappe's own CSS variables; the engineer re-checks those pairs, because
  Frappe's default muted grey is close to the line.**
- Targets: ≥ 24 px on desktop (WCAG 2.5.8), ≥ 44 px on the phone (our rule); field
  text 16 px on the phone; no text under 12 px. Measured (§2).
- Usable at 200 % zoom: the grid collapses to one column under 520 px CSS width, which
  is what 200 % zoom on a 1024 px window produces.
- Hindi: rendered with Noto Sans Devanagari; the sticky bar holds three buttons at
  390 px; at 360 px the long Hindi button wraps to two lines (still ≥ 44 px).

**Privacy on every screen:**

| Screen | Who sees it | Least data? | Small groups? |
|---|---|---|---|
| Settings | System Manager (all); Sales Manager (reviewer, thresholds, cap, ignore list — not mailboxes) | Yes: no email content; usage is a count and a rupee figure | n/a |
| Review queue | System Manager, Sales Manager, the named reviewer; a Sales User only for leads assigned to them (spec §6) | The email text is what the reviewer needs to decide; the sender's local part is masked by default and revealed on a click (the reviewer can read the lead anyway, so the reveal is a convenience, not a permission — see C5). Attachments are names only. cc/bcc are not shown | n/a |
| Lead page | Whoever can read the lead (CRM rule) | Provenance only; the AI's raw JSON stays in the log, which Sales Users cannot open (AC-36) | n/a |
| Notifications | Reviewer / System Managers | Subject only (AC-46) | n/a |
| Employee, HR Manager, CXO without Sales role | **Nothing**, by every door (AC-39–41) | — | — |

The prototype holds fictional people at `example.*` domains and reserved-looking phone
numbers; the screenshots therefore hold no real personal data, but they still live
outside the repo by habit.

**Refusals check:** no rating, no ranking, no emotion or activity signal, no
surveillance of an employee — the mailbox is a shared sales address and the settings
notice says "never a person's own mailbox". The AI is labelled, explains itself in one
line, and every result can be rejected. Nothing from product-context §6 crept in.

---

## 9 · Check before hand-off

**Nielsen, where it applies.** Visibility of status: the why-box and the "AI: not
read" chip say what the machine did or could not do. Match to the real world: "Not an
enquiry", "Junk", "mailbox" — the sales team's words, not "classification" or
"inference". User control: reject moves to Junk and says how to reopen; edits are
recorded, never silent. Consistency: one word per thing — "Needs review" on the list,
the lead status, the CRM view and the bell; "AI lead intake" everywhere, never
"extraction" on screen. Error prevention: the HR mailbox cannot be ticked; the
turn-off needs a reason; a missing reviewer blocks switch-on. Recognition over recall:
the email and the fields sit side by side, with the source phrase highlighted.
Flexibility: one-click accept for the common case, edit for the rare one. Minimalist:
the log's model id and prompt version appear only for the Sales Manager, behind one
link. Help people recover: the network-drop state keeps the edits. Help: the footnote
under the fields explains what a percentage means, once.

**Persona walkthrough, top task, before and after.** Reviewer, clear one uncertain
email: before (spec as written) — bell → CRM list → open lead → Emails tab → read →
Details panel → judge → status dropdown → "New" → back; **9 steps, no confidence, no
reason.** After — bell → page opens on that email → read why-box, glance at fields →
Accept; **3 steps, ~40 seconds.** Tenant admin, switch on: before — find three custom
fields on two forms with no notice; after — one card, notice, reviewer, one button, then
one tick on the mailbox form. Sales User, trust a lead: before — nothing said AI made
it; after — one block at the top of the panel says who, how sure, who checked.

**The frontline bar** does not apply (no frontline persona). The equivalent bar here:
accept one lead on a phone in under 60 seconds — the prototype does it in three taps.

**Red team.** *Brand new reviewer:* the why-box is the first thing on the screen and
says what to do; the empty state explains what the page is. *Expert in a hurry:*
Accept is one click and the next email is selected automatically; no confirmation on
Accept (it is reversible in the CRM); confirmation on Reject (it changes status to
Junk). *No data:* empty state with real counts. *Far too much:* pagination at 20; a
spam night produces 200 fallback rows, which is a chore — noted as slice-two "reject
all from sender". *Network drops mid-accept:* nothing changes on the lead; the edits
stay; retry. *Not allowed:* no buttons and a sentence naming who is. *AI wrong and the
person cannot tell why:* the reasons are in words beside the email; a removed value
says it was removed; a fallback says the AI never read it. *Recover without support:*
reject → reopen in the CRM; accept by mistake → change the CRM status; turned off by
mistake → turn on again, with the notice already accepted.

**What could still go wrong (design risks, ranked):**

1. **Screen 3 depends on the CRM rendering custom fields** through Fields layout. If
   it does not, the AI block is invisible in the CRM app and PRIV-8 fails where it
   matters. Owner: engineer, before `00`. If it fails, the fallback is a CRM code
   change (fork) or a desk-only lead form — both bad; raise it as a decision then.
2. **Two surfaces for one job.** The reviewer lives in `/crm` and decides in `/app`.
   If the jump feels like leaving the product, the queue rots. Mitigation: the CRM
   "Needs review" view with a count, and the bell link. Test in §10.
3. **Reasons readable by the wrong people, or by nobody.** `02` puts them in a log
   Sales Users cannot read; `01c` puts them on the lead. If the BA keeps `02`'s
   placement, "Why this looked like a lead" disappears for the lead owner. Conflict C1.

---

## 10 · Usability test plan (High-impact items RQ1, LP1, the surface bridge)

Five people: two Sales Managers, two Sales Users, one tenant admin — from Sargam if
they will, else from the team, on their own laptops and one on a phone. Prototype, not
the product. Tasks:

| # | Task | Success | Result that changes the design |
|---|---|---|---|
| T1 | "You got a bell notification. Deal with this email." (Western Port Trust) | Accepts or rejects within 90 s without asking what the percentage means | 2 of 5 ask "what is 74 %?" → move the footnote into the why-box |
| T2 | "This one names two companies. Which is the lead?" (Gulf Marine) | Uses "or: Al Bahr Offshore" or edits the organisation; does not try to make two leads | Anyone looks for "split" → add a line "one lead; note the other in the summary" |
| T3 | "Find the lead the AI made from Konkan Shipbuilders and tell me who checked it." | Names Rohan and the date from the AI block within 30 s | 2 of 5 miss the block → move it above the status button, which needs a CRM change; escalate |
| T4 | "Switch the feature on for the sales mailbox." (admin) | Accepts the notice, names a reviewer, finds the mailbox tick on the other form | 2 of 5 cannot find the mailbox tick → put a direct button on the settings card |
| T5 | Phone: "Clear the two oldest emails." | Both decided in under 2 min with no sideways scroll or mis-tap | Any mis-tap on the sticky bar → reorder or enlarge |
| T6 | "You are in the CRM. Where do you go to review?" | Uses the "Needs review" view or the bell; does not hunt | 2 of 5 hunt → add a "Review in the queue" button on the CRM lead page (CRM change; escalate) |

---

## 11 · Decisions and conflicts for the human (⚠ DECISION)

| # | Decision needed | Conflict | Options | Recommendation | Owner | Risk if it waits |
|---|---|---|---|---|---|---|
| C1 | Where the model's `reasons` live | `02` §5.1: log only, Sales User cannot read (§7). `01c` SEC-16: `alvoraa_ai_reasons` on the lead. Brief §10 row 1 also says "on the lead/queue row" | (a) on the lead, read-only (SEC-16); (b) log only and the queue reads it through a Sales-Manager-only endpoint — then the lead owner never sees why | **(a)** — the promise "explain every number" needs the reasons wherever the number is | BA (`02` §5.1) with security | The queue and the lead page cannot be built as drawn |
| C2 | Auto-accept default | `02`: 80 %, 50–100. `01c` SEC-3: 0.85 default, floor 0.7 | either number; the screen shows whatever is chosen | 85 % with a 70 % floor (`01c`) — safer first month; lower it after the 200-email measurement (D-2) | BA + security | Settings copy quotes a number; pick one |
| C3 | Log doctype: name and whether it holds `model_output` | `02` §5.2 `Alvoraa AI Action Log` with the raw JSON and an `error` text. `01c` SEC-17 `Alvoraa AI Call Log` with **no content** | affects only "Open the AI record" (Sales Manager) | Keep `02`'s content (a year-later audit needs what the model said) but under `01c`'s access (System Manager + Sales Manager, nobody else) | BA + security | None for the screens; matters for `00` |
| C4 | Who may decide | `02` §6: Sales Manager, named reviewer, **the lead owner**; D-3: named reviewer + Sales Manager. `01c`: Sales User only by a tenant grant | as drawn: reviewer, Sales Manager, System Manager, plus the lead owner for leads assigned to them | as drawn — the owner deciding their own assigned lead is the CRM's own rule for status; it matches AC-20 | Surbhi | The "not yours" state's sentence changes |
| C5 | Sender masking on the reviewer's screen | `01c` SEC-10 masks the local part **for the model**, not for people. The task asked the reviewer's screen to mask "as the security requirements say" | (a) masked by default, "Show full address" reveals (drawn); (b) full address always (the reviewer can read the lead anyway); (c) masked with no reveal (the reviewer cannot tell a real buyer from a squatter) | **(a)** — same data as the model saw, one click to the truth, no new permission | Security | Wording of the address line |
| C6 | Cap and kill switch on Screen 1 in slice one | D-7 puts the cap and the kill switch in slice two; the task put both on Screen 1 | The tenant-wide "AI lead intake" Check **is** the kill switch (US-14 uses the same field the opt-in needs), so it exists in slice one by construction; the cap field is drawn read-only with "next release" | Ship the switch and the usage count in slice one; the editable cap and per-mailbox limits in slice two | Surbhi / PM | None; the page is drawn so slice two adds fields without moving anything |
| C7 | The CRM header chip ("AI · 87 % · reviewed") beside the status button | Not possible without a CRM change | (a) none — the panel block only (drawn); (b) fork the CRM for a header chip | **(a)** until T3 says people miss it | Surbhi | None |

---

## 12 · What the business analyst must turn into acceptance criteria

1. The review page is a Frappe `Page` at `/app/ai-lead-review`, System Manager, Sales
   Manager and the named reviewer can open it; a Sales User can open it and sees only
   leads assigned to them (or nothing, with the empty state); Employee / HR Manager get
   Frappe's standard not-permitted page. Reads through `frappe.get_list` (SEC-18).
2. `?lead=<name>` opens the page with that lead selected; N-1's link uses it.
3. The page shows, per lead: subject, sender display name + masked address, a reveal
   control, received time, mailbox, confidence or "AI: not read", the reason code in
   the exact words of §7.2, the plain text the model saw (from `Communication.
   text_content` after the same trimming, ≤ 6,000 chars), attachment names, the
   reasons, and each extracted field with its per-field confidence and source phrase.
   **Per-field confidence and source phrase must therefore be in the model schema and
   stored** (today `02` §5.1 has one confidence for the lead and a `source_span` for
   phones only — extend to every field, or the screen shows one number for all).
4. Accept = `accept_intake_lead(lead)`; Edit-then-accept = `frappe.client.set_value`
   on the editable fields **then** accept, producing `Version` rows; Reject =
   `reject_intake_lead(lead, reason)` with the reason Select values fixed as in §7.2
   plus the optional note, ≤ 500 chars.
5. After a decision the row leaves the list; the next-oldest is selected; the toast
   names the assignee.
6. A fallback lead (`AI_UNAVAILABLE`, `CAP`) shows "AI: not read", no percentages, and
   the fallback why-box sentence; a removed phone (`SPAN_CHECK_FAILED`) shows the
   "Removed" sentence under the blank field.
7. Settings: the notice acceptance is stored (user, time, version) on FCRM Settings;
   enabling without it is refused; a version bump disables until re-accepted (PRIV-1);
   the retention sentence renders from the model constant (PRIV-3).
8. The settings section shows today's count and cost from the log (cache-backed), and
   the mailbox table with the three states; the HR refusal message is the exact
   sentence in §7.1.
9. Turn-off dialog requires the Select reason; AC-47/48 hold.
10. CRM lead page: the "AI intake" field group is visible to anyone who can read the
    lead, all read-only, with the fixed PRIV-8 sentence; "Open the AI record" is
    rendered only for Sales Manager / System Manager (a `depends_on` on a role check,
    or a separate field they alone can read).
11. The CRM sidebar saved view "Needs review" exists per tenant on switch-on (fixture).
12. Phone: list-first at ≤ 520 px, detail full-screen with back, tabs Email / Extracted
    fields, sticky three-button bar, targets ≥ 44 px, inputs 16 px.
13. Empty, loading, AI-down, cap, no-permission and network-drop states carry the
    sentences in §6.2 and §7.2, with real counts where a count is shown.
14. Notifications: N-3 and N-4 with the two added sentences in §7.4.
15. **CRM list column** (the brief's WOW moment, §5, shows a ninth row reading
    "AI-created, 91 %"): `alvoraa_intake_state` and `alvoraa_ai_confidence` are
    addable as columns in the CRM's Leads list through its column settings `[verify —
    same Fields-layout question as Screen 3]`; the default saved view "Needs review"
    shows both. Words on the row: "AI · 91 %" for auto-accepted, "Needs review" for
    the queue, "AI · 87 % · reviewed" after a decision — never a colour alone.
16. **Queue age** (OPS-12 alert 4): each row shows its age; a row older than two
    working days gets a red "Overdue" chip with the words, the only red on the page
    (principle 9: red means overdue or wrong), and the reviewer and then the Sales
    Manager are told through the OPS-12 alert, not through a second notification.

---

## Open questions

| Question | Owner | Blocks |
|---|---|---|
| C1–C7 above | as listed | C1 and C3 block the queue's spec; C2 blocks the settings copy; the rest are wording |
| Does Frappe CRM v1.84.0's Fields layout render read-only custom Percent, Link, Select and Small Text fields on the lead page? | Engineer, before `00` | Screen 3 as drawn; PRIV-8 |
| Is a saved view with a filter (`status = Needs review`) creatable per tenant as a fixture in the CRM (`CRM View Settings`)? | Engineer | The bridge from the CRM app to the queue |
| Hindi drafts in §7 | Native reviewer | Showing Hindi to a customer |
| Can this prototype be published for Surbhi (no Artifact tool in this run)? | Lead session | The design check |

## Assumptions

- `[ASSUMPTION]` The reviewer holds Sales Manager or is the named reviewer, and decides
  on a laptop most of the time; the phone layout is for travel, not the main case.
- `[ASSUMPTION]` Frappe's desk on a phone is acceptable for this one page because the
  page carries its own responsive CSS; the rest of the desk is not in the journey.
- `[ASSUMPTION]` Per-field confidence and a source phrase per field can be asked of the
  model in the same schema at no material cost (a few hundred output tokens).
- `[ASSUMPTION]` Frappe CRM's lead page shows custom fields via Fields layout (spec
  §15's own assumption; unverified).
- `[ASSUMPTION]` The cost line "₹0.25 an email" is the spec's Haiku estimate, unverified
  (`02` §11); the screen shows whatever the price table holds.
- `[ASSUMPTION]` Nobody outside the Sales roles needs the queue count anywhere (no
  Home card, no CXO figure); the CXO persona is untouched.

## Handoff note

To the business analyst, who owns `02`: three things change your spec, in this order.
First, C1 — put `alvoraa_ai_reasons` on the lead (SEC-16) or the queue and the lead
page cannot show "why", and please add per-field confidence and a source phrase for
every field to the schema (§12 item 3), because a single lead-level number is what every
competitor shows and it is not enough to trust a phone number. Second, US-4's "Screen"
column: the queue is a desk `Page` we own, not the CRM list plus lead page — §3 says
why, and the endpoints stay exactly as you named them. Third, the settings need an
acceptance record for the PRIV-1 notice (fields, version, re-ask). To the security
engineer: C5 is your call — I masked the sender by default with a one-click reveal,
which gives the reviewer the same view the model had and no new permission; say if you
want the reveal logged. To the engineer, before `00`: the Fields-layout question is the
one thing that can sink Screen 3, so please check it on the dev tenant first. I disagree
with nothing in the user's seven decisions; I disagree with `02` on where the reasons
live and on the review surface, and I have said so above rather than drawing something
else.


## Feedback, 24 Sep 2026 (the user)

- "Is the reviewer box an autofill?" — In the product it is a Frappe Link field to User, so it is a
  picker: type a name, choose from the list, sales roles only. The prototype had drawn it as plain
  text; it now shows the picker affordance and says so in the hint.
- "Simplify the questions" — the three settings are now plain questions: "Who checks the doubtful
  ones?", "How sure must the AI be to create a lead without a check?", "How sure must the AI be that
  an email is not an enquiry, to ignore it?". Defaults aligned with the reconciled spec: 85 %, floor 70.
- "Rest of the design is fine" — design approved. C4 (lead owner may decide their own lead) and C7
  (no header chip) taken as recommended.


## Scope note, 24 Sep 2026

The user moved every screen in this design to slice two. Slice one is the pipeline only;
doubtful leads appear in the CRM's own list under a "Needs review" filter with the reasons in
the lead's note. The prototype stays as the agreed design for slice two.
