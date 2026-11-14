---
slice: 082-event-attendee-qr-form
artifact: 01b-ux-design
author: hrms-ux-designer
date: 2026-11-13
status: draft
inputs: [01-product-brief.md, 01a-ux-opportunities.md, 07-devops-inputs.md (§1), .claude/context/ux-learnings.md, .claude/context/data-doors.md, .claude/context/no-over-engineering.md, CRM v1.84.0 source in hrlocal-328 (crm/www/crm_form.html, crm_form.py, crm/api/form.py, frontend/src/components/Settings/Forms/*, CRM View Settings)]
youtrack: ALV-339
---

# 082 · Event attendee QR form · UX design

**Prototype:** `docs/slices/082-event-attendee-qr-form/prototype-v2.html` (round 2, current)
and `prototype-v1.html` (round 1, kept). Open either file in a browser. **Neither is
published**, because these runs had no Artifact tool. The lead session publishes them. Both
hold Sample data only, which is why they can sit in the slice folder.

**Round 2 (13 Nov 2026):** the user agreed the design, with one change: *"we need to have
flexibility to add more fields beyond these standard fields."* D1-D6 are taken as agreed on
the recommended option. **§13 is the new design for extra fields. It adds ⚠ D7, ⚠ D8 and
⚠ D9.** None of D1-D6 is reversed. D3, D5 and D6 each grow by one rule (§13.6).

**Learnings applied:** "a public form for a crowd: check the rate limit per address"; "QR in
India: plan for a UPI code"; "a confirmation or error must appear where the action was taken";
"colour is never the only signal"; "no button where the rule says no"; "draw both answers
side by side when the user must choose" (slice 078); "look once, then fix what the look shows".

---

## 0. The answer first

**Bad news first.**

- **The brief's "organiser staff (Sales User) builds the form and prints the QR" is not how
  CRM works.** Only a Sales Manager or System Manager can build a CRM form (Fact,
  `crm/api/form.py` `_check_manager`, lines 234-239). Door staff need no login at all: they
  stand beside a printed card. I designed for that. The BA should correct the persona.
- **I could not see CRM running.** CRM is in the `hrlocal-328` container's apps but is not
  installed on any local site (Fact, from `01a`). Screens 2 and 3 are drawn from CRM's own
  source, not from screenshots.
- **The stock page's labels are 13 px grey at 4.17:1 contrast on white** (Fact, computed from
  `crm_form.html:72`, `--muted: oklch(0.586 0 0)`). That fails WCAG 2.2 AA for small text.
  The phone floors in this slice fix it.

**The three biggest design decisions:**

1. **The event is the form's title, and nothing else.** "Pune Dealer Meet, 14 Nov" is typed
   once, as the CRM form's title. Every lead from that form is stamped with it. No event
   picker for the attendee, no event setting for the organiser.
2. **The rating is stored as "1 · Very poor · बहुत खराब" … "5 · Very good · बहुत अच्छा".** CRM
   sorts a choice field by its text. The number at the front is what makes "lowest ratings
   first" a plain ascending sort, with no code.
3. **On every failure the answers stay, and the message sits directly above Send.** The stock
   page shows errors at the top of the card, out of the thumb's reach, and marks a missing
   field only by a red border. Ours says "Needed · ज़रूरी" beside the field and puts the
   message where the person just pressed.

**Five decisions are yours** (§9): where the QR button lives (D1), what "too many at once"
does (D2), how the rating is shown (D3), whether our fixed words are in Hindi too (D4), and
what a closed link shows (D5). Each has a recommendation and both options are drawn.

---

## 1. Frame

A member of the public, standing in a hall after an event, on their own phone over shared
venue Wi-Fi, wants to leave their details and a quick rating in under a minute and go.
Before that, a Sales Manager at the organiser prints one QR card per event. After it, the
same manager opens one saved list and calls the unhappy people first.

| Persona | In scope | What changes for them |
|---|---|---|
| **Attendee** (public, no login; the "Employee" slot of the three-persona check) | Yes, screen 1 | One phone page, two languages, answers never lost on a failed send |
| **Organiser manager** (Sales Manager in CRM; the "HR Manager" slot) | Yes, screens 2 and 3 | Prints a QR card without a third-party site; one saved view per event |
| **CXO** | Lightly, screen 3 "All events" | A count of entries per event. No average rating (would be new code; not in the brief) |
| Door staff (Sales User or no login) | Deliberately out | They need the printed card, not a list (conflict C1, narrower option) |
| Tenant's own employees (portal) | Out | No door into CRM Lead (brief §9) |

---

## 2. Evidence

- **Read in code (Fact):** CRM v1.84.0 in `hrlocal-328`: `crm/www/crm_form.html` (the public
  page), `crm_form.py` (who sees a draft; an unpublished form raises `DoesNotExistError`, so
  a guest gets Frappe's English 404), `crm/api/form.py` (who may build forms), the Forms
  settings screens (`FormsList.vue`, `FormBuilderPanel.vue`: "Link" panel with Copy and Open),
  and `CRM View Settings` (saved views with filters, sort, columns, group-by, pinned, public).
- **Stock page facts that shape the design:** labels 13 px grey; inputs 14 px; checkbox 16 px;
  a **Discard** button that clears the form; the error box sits at the **top** of the card
  (`crm_form.html:184`); a missing field gets only a red border; a failed send **does not
  clear** the form (good — kept); field descriptions are supported (`crm_form.html:231`);
  Select renders as a dropdown.
- **No screenshots of CRM** (not installed). **Prototype screenshots** (Sample data only) are in
  `C:/Surbhi-Git/hrlocal-data/ux-review/2026-11-13/082/`.
- **Measured on the prototype (Playwright, Chrome, 1440 × 900 window, phone frame 390 and
  360):** every input 16 px and 48 px tall; every rating row 48 px; consent rows 83-104 px;
  Send 48 px full width; nothing wider than the screen at 360 or 390; no script errors;
  answers still in the fields after a failed send.

## 3. Benchmark

Carried from `01a` §2 (all **read**, 13 Nov 2026, or `[recall — verify]`; no product
screenshots). What it gave this design: HubSpot's "event set in the link, not chosen by the
attendee" (we use one form per event); Zoho's "staff can fill it for a walk-in" (same link,
no new screen). **Not copied:** one question per screen (five round trips on venue Wi-Fi),
a separate survey product, free dynamic QR generators that expire.

## 4. Findings

| ID | Page | Finding | Impact | Kind | Size | Severity | Evidence |
|---|---|---|---|---|---|---|---|
| EF1 | Public form | Fields 14 px: iPhones zoom in; button ~34 px | High | Fix | S | P2 | `crm_form.html:79,114-116` |
| EF2 | Public form | **Discard** beside Submit wipes everything with one tap | High | Fix | S | P2 | `crm_form.html:241` |
| EF3 | Public form | Labels and intro 13-14 px grey, **4.17:1** contrast | Medium | Fix | S | P2 (WCAG 1.4.3) | computed |
| EF4 | Public form | Missing field shown by red border only; with 2+ missing the message does not name them | Medium | Fix | S | P2 (WCAG 1.4.1, 3.3.1) | `crm_form.html:106,552-555` |
| EF5 | Public form | Error box at top of card; on a phone, Send is a long scroll away from it | Medium | Fix | S | P3 | `crm_form.html:184` |
| EF6 | Public form | Failure messages English only, and generic ("Something went wrong") | Medium | Fix | S | P3 | `crm_form.html:460,588` |
| EF7 | Public form | A closed or unknown link shows Frappe's English 404 | Medium | Improve | S | P3 | `crm_form.py:35` |
| EF8 | Public form | Failed send keeps the answers | — | **Keep** | — | — | `crm_form.html:585-591` |
| EF9 | Public form | Page is one self-contained HTML file, no app bundle: good for 3G | — | **Keep** | — | — | `crm_form.html` |
| EF10 | Public form | Draft preview for Sales Managers already exists ("test from your phone") | — | **Keep** | — | — | `crm_form.py:28-33` |
| EF11 | CRM Forms | No QR anywhere | High | New | S | — | brief S1 |
| EF12 | CRM Leads | Saved views exist with filter, sort, columns, group-by, pin | — | **Keep** | — | — | `crm_view_settings.json` |
| EF13 | CRM Leads | A choice field sorts by text, and blanks sort first ascending | High | Fix (by option wording + a filter, not code) | S | P2 for the WOW | Frappe/MariaDB ordering `[ASSUMPTION: blanks sort first — confirm on the fresh site]` |
| EF14 | Brief | Organiser staff who build forms must be Sales Managers | Medium | Fix (brief) | — | — | `form.py:234-239` |

---

## 5. Flows and every state

### 5.1 Attendee (screen 1)

```
Scan card ─► Form page ─► Send ─► "Sending…" ─► Thank you
                │                     │
                │                     ├─ needed answer missing ─► message above Send + "Needed" by each field; focus on message
                │                     ├─ no signal / server error ─► "Not sent", answers kept, press Send again
                │                     ├─ too many at once (event limit hit) ─► D2: wait-and-press (A) or one auto retry (B)
                │                     └─ form closed while filling ─► "stopped taking answers", give details at the desk; Send hidden
                └─ link closed or unknown ─► "This form is not taking answers"
```

| State | What shows | Notes |
|---|---|---|
| Loading | Server-rendered page; no skeleton needed | Budget ≤ 2.5 s p95 on 3G (`nfr-budget.md` §2). Page weight to be measured (DevOps §1) |
| Empty form | Title, one-line intro, 7 fields, Send | First field visible without scrolling at 390 × 844 |
| Sending | Send disabled, reads "Sending… / भेजा जा रहा है…" | Stops a double tap making two leads |
| Needed missing | Message above Send naming each one; "Needed · ज़रूरी" under each; 2 px border | Message gets focus and is `role="alert"` |
| Not sent | Red-tinted message above Send; answers kept | Also for a server error and a **30 s timeout** with no answer `[ASSUMPTION: 30 s; a rare duplicate lead is accepted over a lost one]` |
| Too many (A) | Amber message: wait 10 s, press Send again; answers kept | Brief §7 default: no auto-retry |
| Too many (B) | Amber message counting down "Sending again in 10 s"; Send disabled; one retry only, then state "Not sent" | Only if you choose D2-B |
| Closed while filling | Message: not saved, give details at the desk; Send hidden | No button that would fail again (pattern, slice 008) |
| Closed / unknown link | Card: "This form is not taking answers…"; no event or organiser name | Same page for "closed" and "never existed", so a guest cannot probe which routes exist |
| Thank you | Tick, organiser's bilingual success message, "You can close this page." | **No echo** of any answer (OPS-5). Stock note "Your response has been recorded." removed |
| No permission | Not applicable: the page is public; nothing is read back | — |
| First-time | Every visit is first-time | — |
| Long name / Hindi | Labels wrap; tested at 360 px with bilingual text | — |

### 5.2 Organiser manager (screen 2)

1. CRM → Settings → Forms → New. **Title = event name and date** ("Pune Dealer Meet, 14 Nov").
   Add the fields (§6.1). Put the notice in the "I agree" field's description. Set the
   button label and success message (both bilingual). Publish.
2. Print the card: **D1-B** — press **Open** in the form's Link panel (already there). Signed in
   as Sales Manager, the form shows an organiser box with **Download QR card**. **D1-A** — a
   **Download QR card** button beside Copy link and Open, inside CRM's builder.
3. Draft form: the organiser box says "This form is a draft. Publish it in CRM before
   printing a QR — a QR for a draft opens a page attendees cannot use." **No button.**
4. After the event: unpublish when the organiser chooses (manual, brief §7).

### 5.3 Manager (screen 3)

1. CRM → Leads → pinned view **"Pune Dealer Meet – lowest first"**: filter *Event form =
   Pune Dealer Meet, 14 Nov* and *Event rating is set*; sort *Event rating ascending, then
   Created on ascending*; columns Name, Event rating, Event comment, Mobile, News OK,
   Created on, Assigned to. Ratings 1 and 2 show a "!" and a tinted chip (colour plus mark).
2. Assign each low rating to a sales person (CRM's own assign).
3. Pinned view **"Events – entries per form"**: filter *Event form is set*, group by Event
   form. A count per event, no average.
4. Empty view (no ratings yet): CRM's own empty list `[ASSUMPTION: CRM shows "No leads
   found" — not seen]`. Nothing to design.

All of screen 3 is **configuration**: two saved views the setup guide tells the manager to
create, or that we ship as a fixture `[ASSUMPTION — BA to choose; a fixture needs the event
value, so the guide is likelier]`.

---

## 6. Screen specs and exact words

Hindi is a **machine draft for a native reviewer.** Organiser-typed words are examples the
setup guide will give; our fixed words are what we ship.

### 6.1 Attendee form (organiser-typed, configuration)

| Item | English | Hindi | Field (CRM Lead) | Needed? |
|---|---|---|---|---|
| Title | Pune Dealer Meet, 14 Nov | — | form title | — |
| Intro | Takes about one minute. | लगभग एक मिनट लगेगा। | form description | — |
| Name | Your name | आपका नाम | `first_name` (or full name per CRM) | Yes |
| Mobile | Mobile number | मोबाइल नंबर | `mobile_no` (phone keypad) | Yes |
| Email | Email (optional) | ईमेल (वैकल्पिक) | `email` | No |
| Rating | How was the event? (optional) | कार्यक्रम कैसा रहा? (वैकल्पिक) | new: Event rating | No |
| Comment | Anything you want to tell us? (optional) | कुछ और बताना चाहें? (वैकल्पिक) | new: Event comment | No |
| Consent | I agree that Sharma Events keeps these details to follow up on this event. | मैं सहमत हूँ कि Sharma Events इस कार्यक्रम के बारे में संपर्क के लिए ये जानकारी रखे। | new: Consent: this event (unticked) | Yes |
| Notice (description under Consent) | Collected by Sharma Events for Pune Dealer Meet. We keep your details for 6 months after the event. If you tick "Send me news", we keep your contact until you ask us to stop. To see or remove your details: privacy@sharmaevents.example. For people aged 18 or over. | Sharma Events यह जानकारी Pune Dealer Meet के लिए ले रहा है। कार्यक्रम के 6 महीने बाद तक रखी जाएगी। "आगे की जानकारी" पर टिक करने पर, जब तक आप मना न करें। देखने या हटवाने के लिए: privacy@sharmaevents.example। केवल 18 वर्ष या उससे अधिक के लोगों के लिए। | field description | — |
| Marketing | Send me news of future events. (optional) | मुझे आगे के कार्यक्रमों की जानकारी भेजें। (वैकल्पिक) | new: Consent: news (unticked) | No |
| Button | Send my details | जानकारी भेजें | form button label | — |
| Thank you | Thank you. Your details are saved for Pune Dealer Meet, 14 Nov. | धन्यवाद। आपकी जानकारी Pune Dealer Meet, 14 Nov के लिए सहेज ली गई है। | success message | — |

**The notice moved from the top to under "I agree"** after the one look: at the top it took
about 300 px and pushed every field below the fold. Under the tick it is read at the moment
consent is given. "6 months" and "18 or over" are the brief's defaults (Q4, Q7), **not legal
answers**.

**Rating options** (fixed by us on the new field, same for every tenant):
`5 · Very good · बहुत अच्छा` / `4 · Good · अच्छा` / `3 · OK · ठीक-ठाक` / `2 · Poor · खराब` /
`1 · Very poor · बहुत खराब`. Shown best first to the attendee.

### 6.2 Fixed words we ship (D4 decides the Hindi half)

| Where | English | Hindi |
|---|---|---|
| Under a missing field | Needed | ज़रूरी |
| Missing message | Please fill these in: Your name, I agree. (names each missing label's English part) | कृपया ये भरें — ऊपर "ज़रूरी" लिखे खाने। |
| Sending | Sending… | भेजा जा रहा है… |
| Not sent | **Not sent.** Your answers are still here. Check your signal, then press Send again. | नहीं भेजा गया। आपके उत्तर यहीं हैं। नेटवर्क देखें, फिर दोबारा "भेजें" दबाएँ। |
| Too many (A) | **Many people are sending at the same moment.** Your answers are still here. Wait 10 seconds, then press Send again. | इस समय बहुत लोग एक साथ भेज रहे हैं। आपके उत्तर यहीं हैं। 10 सेकंड रुकें, फिर दोबारा "भेजें" दबाएँ। |
| Too many (B) | **Many people are sending at the same moment.** Sending again in 10 s. Keep this page open. | बहुत लोग एक साथ भेज रहे हैं। 10 सेकंड में फिर भेजेंगे। यह पेज खुला रखें। |
| Closed while filling | **This form has stopped taking answers**, so your details were not saved. Please give them at the organiser's desk. | यह फ़ॉर्म अब उत्तर नहीं ले रहा, इसलिए आपकी जानकारी सहेजी नहीं गई। कृपया आयोजक की डेस्क पर दें। |
| Closed / unknown link | **This form is not taking answers.** It may have closed after the event. If you are at the event, please ask at the organiser's desk. | यह फ़ॉर्म अभी उत्तर नहीं ले रहा है। हो सकता है कार्यक्रम के बाद बंद हो गया हो। अगर आप कार्यक्रम में हैं, तो आयोजक की डेस्क पर पूछें। |
| Thank you footer | You can close this page. | आप यह पेज बंद कर सकते हैं। |

"The server's own sentence" is shown only for a field-level refusal (for example an invalid
email); anything else maps to "Not sent". Never a raw server error.

### 6.3 Phone floors (the stylesheet change)

16 px inputs and textarea, 48 px tall; 48 px full-width Send; **no Discard**; labels 15 px in
the ink colour (not grey); description 14 px; checkbox 24 px inside a ≥ 48 px row where the
whole row is the target; rating as five 48 px rows (D3-A); card padding 16-20 px and page
padding 12 px on a phone (stock is 48 px top). CRM's own colours and font stay: this is
CRM's page and the organiser's event, not an Alvoraa screen, so **the Alvoraa palette is not
applied** (design-system consistency gives way to context here, priority ladder 9). No dark
theme: CRM's page has none, and adding one is not in the brief.

### 6.4 QR card (screen 2)

One PNG, A6 or larger: event title (bold) · organiser name · QR · "Scan to leave your details
and feedback" / "अपनी जानकारी और राय देने के लिए स्कैन करें" · a ruled band **"This is not a
payment. · यह भुगतान नहीं है।"** · the address in plain text. The QR and the printed address
are the **tenant's own address** (OPS-7). Showing the address in full is how a person spots a
dev address before printing. Engineering note: draw the card in the browser, where a
Devanagari font exists; a server-drawn PNG may have no Hindi font `[ASSUMPTION]`.

### 6.5 Manager view (screen 3)

Exact view names: "Pune Dealer Meet – lowest first", "Events – entries per form". Column
labels are the new fields' labels: **Event form, Event rating, Event comment, News OK**
(label for "Consent: news" in lists — BA to set as the field label or the column label).

---

## 7. Accessibility (WCAG 2.2 AA) and privacy

**Accessibility, for the screens this slice touches:**
- Every input has a real `<label for>` (stock page already does — checked, `crm_form.html:202`).
- Rating rows are a `fieldset` with a `legend` and native radios: keyboard and screen reader
  work without custom code.
- Missing answers: text plus a 2 px border (1.4.1); the message names them and gets focus
  with `role="alert"` (3.3.1, 4.1.3).
- Contrast: labels move to the ink colour; the remaining grey (`--muted` at 0.45 in the
  prototype) to be measured ≥ 4.5:1 in the build.
- Targets ≥ 48 px on the phone (2.5.8 needs 24; our phone rule 44).
- Focus visible: 3 px outline on every control.
- Low-rating chip in CRM: tint plus a "!" mark, so colour is not the only signal.
- Not checked: a real screen reader on CRM's page (brief §13 flagged it). One pass with
  TalkBack is in the test plan.

**Privacy (data-doors.md):**
- **Screen 3 shows other people's personal data** (names, mobiles, comments). The saved view
  is **not** the protection. CRM Lead's own permission rules must limit it: Sales Manager
  reads all; Sales User only assigned leads; Employee-only logins nothing. Flagged for
  `hrms-security-privacy-engineer` and the BA's door tests.
- Screen 1 reads nothing back: no list, no count, no echo, and the closed page names no
  event, so a guest cannot tell a closed form from one that never existed.
- The organiser box (D1-B) shows only the form's own address, and only to a signed-in Sales
  Manager or System Manager — the same check CRM already uses for drafts.
- G2 (guest access to the User list) is not drawn because no field in this form is a Link.
  The rule "no Link field on an event form" belongs in the spec.
- "News OK" is the only column that permits marketing (C3). Blank means do not email.
- Shared staff phone (walk-in entry): after a failed send, the next person could see the last
  person's answers. Low risk; the setup guide tells staff to reload after a failure.
- Retention (6 months) and minors (18+) are defaults pending counsel (Q4, Q7).

---

## 8. Checks before handoff

**Nielsen, where it applies:** status visible (Sending, countdown in B) · real-world words
("Not sent", not "Error 429") · user control (no Discard trap; answers kept) · consistency
(one word "Send" on button and messages) · error prevention (needed fields named before
sending) · recognition (rating options visible, D3-A) · minimal design (one page, notice at
the tick) · recover from errors (every failure says what to do next).

**Persona walkthrough:**

| Persona | Top task | Before (stock) | After |
|---|---|---|---|
| Attendee | Leave details and a rating | Zoom-in on tap; ~290 of 300 refused on one Wi-Fi; Discard can wipe it | 7 fields, no zoom, ~45-60 s `[ASSUMPTION: to test]`; per-event limit |
| Organiser manager | Print a QR | Third-party generator, may expire | Open → Download QR card → print (3 taps, D1-B) |
| Manager | Call the unhappy ones | No event on the lead; no way to sort by rating | One pinned view, worst first |

**The frontline bar (two minutes on a phone):** yes, about one minute, if the per-event limit
holds (OPS-9 load test).

**Refusals:** no AI, no ranking of a person, no pre-ticked box, no guilt wording, cancel is
"close the page". **Plain-language test:** passes in English; Hindi needs the native reviewer.

**Red team:**
- *Brand-new attendee who reads slowly:* bilingual labels, one page, Send says what it does.
- *Network drops mid-send:* answers kept; "Not sent"; press again. If the save landed and the
  reply was lost, a second press makes a **duplicate lead** — accepted (brief Q3: each entry
  its own lead; the manager can delete).
- *Closes the page after "Not sent":* answers are lost. Keeping a draft on the device is the
  brief's "later" (auto-retry), not in this slice.
- *Far too much data:* 287 rows is one CRM list page with paging; nothing assumes ten rows.
- *Poster photographed and spammed:* the per-event limit caps it; manager unpublishes.
- *Not allowed to see:* a Sales User opening the manager's view sees only their assigned
  rows, if CRM's rule holds — test it, do not assume it.

**Usability test plan (High impact: screen 1).** Five people, at least two Hindi-first, on
a mid-range Android throttled to 3G. Tasks: scan the card and leave your details with a
rating; then with Wi-Fi off, press Send and recover. Success: finish in ≤ 60 s median; nobody
loses typed answers; all five find the retry; nobody mistakes the card for a payment. Would
change the design: anyone scrolling past the notice without seeing what "I agree" means (move
the notice back up, shorter); anyone pressing Send repeatedly during "too many" (choose D2-B).

---

## 9. ⚠ DECISIONS for you

**Status, 13 Nov 2026:** D1-D5 agreed on the recommended option (and D6, our own page at
`/event-form/<route>`, DevOps OPS-12, engineer still to confirm). New decisions D7-D9 are in §13.

| # | Decision | Options (both drawn) | My recommendation and why | Blocks |
|---|---|---|---|---|
| **⚠ D1** | Where "Download QR card" lives | **A** in CRM's form builder, beside Copy link and Open. **B** on the form page itself, in a box only a signed-in Sales Manager sees | **B.** It changes no CRM screen, so there is nothing to carry through CRM upgrades, and it makes the organiser look at the real form before printing. Engineer to confirm B needs no edit inside CRM (`hrms-fullstack-engineer`) | Where the build lands |
| **⚠ D2** | "Too many at once" | **A** say "wait 10 seconds, press Send again" (brief: auto-retry later). **B** one automatic retry after 10 s with a countdown | **A**, as the brief chose. Choose B only if the load test or usability test shows people giving up | One small piece of page code |
| **⚠ D3** | How the rating is shown | **A** five tappable rows. **B** CRM's stock dropdown ("Select…") | **A**, for the rating field only. One tap instead of three, every choice visible. Standard radios, no new component | A change to how the page draws one field |
| **⚠ D4** | Our fixed words (errors, "Needed", closed page) | **A** English and Hindi always, like the labels. **B** English only | **A.** About 10 strings. Needs a native reviewer before switch-on | The native review |
| **⚠ D5** | A closed or unknown link | **A** our one bilingual card (same for both cases). **B** Frappe's English "Page not found" | **A.** An attendee who scans a poster after the event should be told it closed, not that the page is broken | Small page change |

Not decisions (I chose; easy to undo): rating wording with a number in front; notice under
the consent tick; "Rating is set" on the lowest-first view; the 30 s timeout.

## 10. What the BA must turn into acceptance criteria

1. The public page: inputs 16 px and ≥ 48 px; Send full width ≥ 48 px; **no Discard**; labels
   at ≥ 4.5:1 contrast.
2. A missing needed answer: message above Send names each one; "Needed" text under each field;
   focus moves to the message.
3. **Any failed send leaves every answer in place** — test by pressing Send with the network
   off, then on, and asserting the lead's values (test what it sends, not what it draws).
4. Each failure maps to its §6.2 sentence: no signal, server error, 30 s timeout → Not sent;
   event limit → Too many (per D2); form unpublished → Closed while filling.
5. Thank you shows the success message and nothing the attendee typed.
6. Closed and unknown links show the same card (per D5), with no event or organiser name.
7. New CRM Lead fields: Event form (stamped from the form used, not attendee-editable), Event
   rating (five options exactly as §6.1), Event comment, Consent: this event, Consent: news —
   both consents **unticked by default**.
8. No Link field on an event form (G2).
9. QR card: per §6.4, only for a published form, only for Sales Manager / System Manager,
   encodes the tenant's own address. Draft form → the sentence in §5.2 step 3 and no button.
10. Two saved views as §5.3, created from the setup guide.
11. Door tests (data-doors.md) on a fresh site with CRM: Guest, Employee-only, Sales User,
    Sales Manager, against the save path, `/api/resource/CRM Lead`, report view, link search
    on Event form, and the form page's HTML.
12. Rating sort check on the fresh site: blanks and order behave as §4 EF13 assumes.

## 11. Not in this slice (for you to decide later)

Automatic retry and an on-device draft · a "fill in for another person" button after Thank
you · an average rating per event · a live count for door staff (C1) · a date window that
closes the form by itself · a dark theme on the public page.

## 12. Subtract pass

Removed: a language switch (labels are bilingual); a review-bar theme switch (the product
screens have no dark mode, so drawing one would build one); the stock "Your response has been
recorded." line under Thank you (said twice); a separate "event settings" panel (the title is
the event); an "average rating" column (no code path, not asked); masking of mobile numbers in
the manager mock (a manager sees them in full, and drawing a mask would ship a mask). I kept
both options of D1-D5 drawn, because they are your calls.

---

## 13. Round 2: extra questions per event

### 13.1 What the user asked, and the frame

An organiser must be able to ask questions beyond the standard ones, per event ("Your shop
name", "How many shops do you run?", "Which products interest you?"). The attendee answers
them on the same single page. The manager finds and uses the answers.

**The fact that shapes everything:** CRM's form builder already offers **every** visible,
editable CRM Lead field of a supported type, custom fields included (Fact,
`crm/api/form.py` `_mappable_fields`, lines 127-151). It **skips hidden fields**. So a field
that exists on CRM Lead is one click away for the organiser, with no code.

### 13.2 ⚠ D7: where extra questions and answers live

Both are drawn side by side in prototype v2 (Organiser and Manager screens, "⚠ D7" switch).

| | **A · a real field on CRM Lead** (recommended) | **B · questions kept with the form, answers kept on the lead** |
|---|---|---|
| How a new question is made | A System Manager adds a Custom Field on CRM Lead (Frappe's own form), **once per question**. Then any organiser picks it in CRM's builder for any event | The organiser adds a row to a new "Extra questions" table on the Web Form record, **in Frappe Desk**, because CRM's builder can only place CRM Lead fields |
| Rung | **2-3: configuration.** No new code for the questions themselves | **4-5: new code and a new child table type** (plus a place for answers on the lead) |
| Where the organiser works | One place: CRM's builder | Two places: CRM for standard fields, Desk for extra ones. Sales Managers may not have Desk access `[ASSUMPTION]` |
| Answers | One column per question, typed (number, choice, date…) | One text block per lead ("Your shop name: …", "How many shops: 4") `[or a child table — same limits for the manager]` |
| Manager: filter | Yes, exact ("Products of interest = Air coolers") | Only "contains" on the text |
| Manager: sort | Yes ("Shops, most first") | No |
| Manager: group and count | Yes, CRM group-by | No |
| Export | One column per question | One text column |
| What grows | CRM Lead gains a column per question, blank on leads from other events | Nothing on CRM Lead beyond one answers field |
| Retiring a question | Tick "Hidden" on the field: answers stay, the builder stops offering it (Fact: builder skips hidden fields) | Delete the row |
| Attendee sees | **The same page under both** | |

**Recommendation: A.** It is the cheapest rung that fully meets the requirement, and it is the
only one where the manager can actually use an answer (filter, sort, count). B buys one thing:
CRM Lead does not grow. That growth is real but slow (a column per *new* question, not per
event), and it is managed by naming each field for what it asks, so the next event reuses it.
The cost of A is a System Manager step for a brand-new question (⚠ D8).
**Risk with A:** a tenant that adds hundreds of questions over years could reach the database's
row-size limit `[ASSUMPTION: MariaDB; Data fields are 140 characters]`. Long-text answers are
stored outside the row. I would not design for this until a tenant comes near it.

### 13.3 ⚠ D8: who may create a brand-new question field (option A only)

| Option | What it means |
|---|---|
| **A · System Manager only** (recommended) | As Frappe ships. The organiser asks their administrator once per new question. A new question is a new kind of personal data, so an accountable person decides it |
| B · Give Sales Managers the right to add Custom Fields to CRM Lead | Faster. But a Sales Manager could then add *any* field to every lead, including sensitive ones, and permission rows on Custom Field are site-wide |

Most events reuse existing questions, so the System Manager step is rare. If it proves a real
bottleneck, B can be revisited. It is easy to undo either way.

### 13.4 Which field types our page shows

Our page (D6) draws only these. **Anything else stops the form opening for attendees** and
the organiser box names the field (§13.5).

| Allowed | How it appears on the phone |
|---|---|
| Data (short text) | 16 px box. If set as Email or Phone, the matching keyboard |
| Phone | Phone keypad |
| Small Text, Text, Long Text | Text area, 16 px |
| Int, Float | Number keypad |
| Select | **Up to 6 choices: tappable 48 px rows** (as D3). More than 6: the phone's own dropdown |
| Check | 24 px tick inside a 48 px row |
| Date | The phone's own date picker |

| Banned | Why |
|---|---|
| **Link** | Lists records from the tenant's data. On CRM Lead it can publish up to 500 staff names (G2, OPS-14) |
| Attach, Attach Image | No public uploads: disk, backups, malware (DevOps §1, OPS-6) |
| Text Editor, HTML Editor, Markdown Editor | Formatted text and HTML typed by the public, stored on a lead and later drawn inside CRM. Plain text does the job |
| Datetime, Time | No event question needs a time; hard to use on a phone. Date covers it |
| Currency, Percent | Money and percent invite wrong answers ("₹ or lakh?"). Use a number with the unit in the label |
| Color | No job |

**Not enforceable by type, so a setup-guide rule plus D8:** no question that asks for
Aadhaar, PAN, bank details, health, religion, caste or similar. Flag for
`hrms-security-privacy-engineer`: the consent notice says "these details", so a sensitive
question would make it untrue.

### 13.5 Limit on extra questions, and ⚠ D9

Each extra question adds 80-270 px and roughly 5-10 seconds `[ASSUMPTION: untested]`. Five
extras take the form to about a minute and a half. That is inside the frontline bar of two
minutes. **I recommend a soft limit of 5 extra questions.**

| ⚠ D9 | Option |
|---|---|
| **A · warn** (recommended) | Above 5, the organiser box says: "This form has 8 extra questions. In a hall, most people stop after about 5. Consider removing some." The QR button stays |
| B · block | Above 5, no QR button and the form does not open for attendees |

A warning respects the organiser's own knowledge of their crowd. A block is a new refusal
state for a judgement call.

### 13.6 What changes in D1-D6

| Agreed | Change from this round |
|---|---|
| D1 organiser box | Gains two lines: "Extra questions: 3." and the D9 warning. A new state when a field cannot be shown (§13.5): no QR button, the field named |
| D2 | None |
| D3 five tappable rows | The same rows are used for any extra Select question with up to 6 choices |
| D4 fixed words EN + HI | None. Extra questions are typed by the organiser, in both languages, like the standard labels |
| D5 our closed page | Also shown to attendees when a form has a banned field |
| D6 our page at `/event-form/<route>` | Must draw the §13.4 types and refuse any other type on the server. **This rule is what keeps Link fields out.** It is stronger than the setup guide |

### 13.7 Screens (prototype v2)

- **Attendee:** "Nashik Retailer Day, 2 Nov" with three extra questions after Email and
  before the rating: *Your shop name (optional) / आपकी दुकान का नाम (वैकल्पिक)*; *How many
  shops do you run? (optional) / आपकी कितनी दुकानें हैं? (वैकल्पिक)*; *Which products interest
  you? (optional) / आपको कौन से उत्पाद पसंद हैं? (वैकल्पिक)* with four tappable rows. They
  look exactly like the standard questions. Switch to "Pune · standard only" for v1's form.
- **Organiser, A:** Step 1, Frappe's "New Custom Field" form (System Manager). Step 2, CRM's
  builder with "Add Field" listing Shop name, Shops, Products of interest. Press "Add these 3
  fields" to see them land after Email. **Organiser, B:** the Web Form record in Desk with a
  new "Extra questions" table, and what B costs.
- **Organiser box** states: Ready · Has a field we cannot show · 8 extra questions.
- **Manager, A:** "Nashik Retailer Day – answers", one column per question, filtered to Air
  coolers, sorted by Shops. **Manager, B:** the same view with one "Event answers" text
  column and only a "contains" filter.

Hindi in the extra questions is a machine draft, like the rest. Under A, a choice's stored
value is the whole option text, Hindi included ("Air coolers · एयर कूलर"). The manager mock
shows exactly that.

### 13.8 For the BA (added to §10)

13. Our page draws only the §13.4 types. A form with any other field shows attendees the
    closed card, and shows the organiser the field's label and no QR button.
14. An extra Select with 6 or fewer choices renders as 48 px tappable rows. More than 6
    renders as a dropdown.
15. Under D7-A: a Custom Field on CRM Lead of an allowed type appears in CRM's builder and on
    our page with no code. A field marked Hidden no longer appears in the builder, and its
    stored answers stay.
16. The organiser box counts extra questions (fields other than the standard seven) and shows
    the D9 warning above 5.
17. A Sales User or Employee-only login cannot read the new answer fields through any door in
    `data-doors.md` (same rule as the rest of CRM Lead).

### 13.9 Subtract pass, round 2

Removed from v2: the D1, D2 and D3 review switches (agreed, so the agreed option is drawn
alone); CRM's builder "Download QR" option A mock (D1 settled); a "required" mark on the
sample extra questions (the guide recommends optional); a per-question "help text" in B (not
asked). I did not add a question library, question templates or an editor of our own. Under
A, CRM's builder already is the editor.

---

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| D7, D8, D9 | §13 — **agreed 13 Nov 2026 on the recommended options:** D7-A real fields on CRM Lead, D8-A System Manager only, D9-A warn above 5. Design agreed ("go with this design") | — | — |
| Q-UX3 | Under D7-A, do new Lead fields show on CRM's lead page without a layout change ("Data Fields" layout)? The manager's views work either way | Engineer | Nothing in the views; only the lead page |
| Q-UX4 | Sensitive questions: setup-guide rule only, or something stronger? | `hrms-security-privacy-engineer` | The notice staying true |
| D1-D5 | §9 — agreed on the recommended options, 13 Nov 2026 | — | — |
| Q-UX1 | Can a page change at `/crm-form/<route>` (phone floors, rating rows, our words, organiser box, closed card) be made from our app without editing CRM? | `hrms-fullstack-engineer` | The whole of screen 1 and D1-B |
| Q-UX2 | Persona correction: form builders are Sales Managers, not Sales Users | BA, with Surbhi | The access rules |
| Q4, Q7 | Retention period and minors (brief) | Counsel via Surbhi | The notice wording; switch-on |
| — | Native Hindi reviewer for §6.1 and §6.2 (~25 strings) | Surbhi | Switch-on |

## Assumptions

- `[ASSUMPTION]` Blank choice values sort first in an ascending CRM list.
- `[ASSUMPTION]` A 30 s timeout is long enough on 3G and a rare duplicate lead is acceptable.
- `[ASSUMPTION]` CRM shows its own empty-list state for a view with no rows.
- `[ASSUMPTION]` A server-drawn PNG may lack a Devanagari font; drawing in the browser avoids it.
- `[ASSUMPTION]` About 45-60 s to fill, untested.

## Handoff note

To security and the BA: screen 3 is the one that shows other people's data, and only CRM
Lead's permission rules protect it — please test the Sales User case on a fresh site before
anyone trusts the "assigned only" assumption. To the engineer: Q-UX1 decides how much of
screen 1 is possible without touching CRM; if it is not, tell Surbhi before the spec, because
D1, D3 and D5 all depend on it. I disagree with the brief on one point only: organiser staff
who build forms must be Sales Managers (code fact), so the brief's Sales User row in §1
should change. Parity: every item in the prototype is something to build; the review bar and
the dashed "Note for review" boxes are not.
