---
slice: 078-positions-faces
artifact: 01b-ux-design.md
author: hrms-ux-designer (design mode)
date: 2026-10-31
status: draft for Surbhi's design gate. A clickable prototype exists and must be reviewed with this document.
inputs: [ux-learnings.md, product-context.md §1 §2 §5 §6, nfr-budget.md §2 §5 §7, no-over-engineering.md,
  handoff-contract.md, definition-of-ready-done.md, change-process.md, design_system.html,
  01a-ux-opportunities.md, 01-product-brief.md (revision 2), 07-devops-inputs.md §1,
  slices 059 / 064 / 065 / 069 / 070 / 071 / 072 / 076,
  portal.js, positions.html, home.html, org-settings.html, drawers.html, settings.py, register.py,
  employee_field_rights.py, auth.py, employee_document_type.json,
  PPJ local copy — read-only queries AND browser capture, 31 Oct 2026]
prototype: C:/Surbhi-Git/hrlocal-data/prototypes/078-positions-faces/prototype-v5.html  (v1-v4 kept beside it; not yet published - see sections 12 and 17.11)
revision: v5, 31 Oct 2026 - after Surbhi decided HR may mark fields and document types required. v5 adds section 17, which supersedes 6.5.3 (the list of lists), 6.5.5 and 6.6's fixed six screens. DECISIONS 10, 11, 14 and 15 are open; 14 is the one to answer first.
screens: C:/Surbhi-Git/hrlocal-data/ux-review/2026-10-31/
---

# 078 · Faces, My profile, the mini profile, the settings card and the pre-onboarding form — design

## The answer first

**Good news, and it is the first in five slices: I got a login and looked at the real
screens today.** Positions, My profile, Organisation Settings and the password page were
all captured at 1440 × 900 and 390 × 844 on the PPJ local copy. Images are in
`C:/Surbhi-Git/hrlocal-data/ux-review/2026-10-31/`. Three things only a browser could
have shown are in §2.

**Bad news, and it is small but real.** On that copy the **Positions chart itself does
not load** — the page draws, the filters draw, and the body says *"The chart did not
load… code POS-LOAD"*. DevOps already found the cause: `Replacement Plan` is not
migrated on this site. So the chart boxes, the seat tray and the "Change this seat"
dialog are **still read from code**, not from a render. Everything else in this design was
seen. §2 says exactly which parts are which.

**What I designed.** Everything Surbhi asked for, as she asked for it, in one slice:

| Part | What it is |
|---|---|
| **My profile** | Photo upload from a phone camera, the six details HR has ticked, a link to the password page that already exists |
| **Faces** | On the hierarchy cards **and** in the table, with six measures so they do not break the page (§5) |
| **Mini profile** | In the existing `.emp-drawer`, from the table, the seat tray, and **expanded in place** inside the "Change this seat" dialog |
| **Settings card** | One card on Organisation Settings, four lists, and a save button that names the consequence before it happens |
| **Pre-onboarding** | The joiner's phone screens, no account, both ways of configuring it drawn so you can choose |

**The one thing I would still push back on, and only on the words.** The setting screen
now carries all 18 document types, as you decided. I have not narrowed the list. What I
have done instead is make the consequence impossible to miss **before** the tick is saved:
a category chip on every row, a red line under any identity, statutory, verification,
employment or address type the moment it is ticked, a "What you are about to share"
summary, and a save button that reads **"Save — 3 document types, seen by 7 people"**.
That is the whole weight of decision 3 and it lives in one screen.

---

## 1 · Frame

| Who | At what moment | On what | Trying to |
|---|---|---|---|
| **Employee / frontline worker** (primary for My profile) | On the shop floor, between customers | A cheap Android, 360–390 px, patchy signal | Put their face and their right phone number on their own record, in under two minutes, without asking HR |
| **HR Manager** (primary for everything else) | Month-end, laptop, many tabs | 1440 × 900 | Recognise a person in a seat, answer one question about them, and decide once what everyone else may see |
| **CXO / founder** | Five minutes, often a phone | Phone or laptop | Recognise a face across six stores |
| **New joiner** (primary for the pre-onboarding form) | At home, a week before day one, possibly on a relative's phone | A phone, no account, no password | Send their details and documents once and be done |

**Deliberately out of scope.** The employee does not open the Positions page and this
design does not give them one. They appear on it. That asymmetry is the one-way rule
(product-context §2), and §8 is the check against it.

**The three-persona check (CLAUDE.md §4).**

- **CXO** — gains faces on the chart and a mini profile; loses nothing; pays with a
  heavier page the first time it is opened (§5).
- **HR Manager** — gains the mini profile and stops hopping to Desk; loses nothing; gains
  one responsibility they did not have — deciding what a reader may see, which is why the
  settings card carries so much copy.
- **Employee** — gains a photo, six editable details and a password link; **pays** by
  appearing, with a face, to whoever the tenant has let onto Positions. At DTC that is HR
  Manager, which you confirmed. The privacy sentence beside the upload is how they find
  out before it happens, not after.

---

## 2 · Evidence — the real screens, at last

**Method.** Signed in through `/api/method/login` as `hr@ppj.dev.alvoraa.co` (HR Manager)
on `http://127.0.0.1:8010`, site `ppj.localhost`. Chrome channel, Playwright, 1440 × 900
and 390 × 844. **No data was changed.** All other facts come from read-only `bench console`
queries over standard input (never `docker cp` — CLAUDE.md gates it) and from the code.

Images, which hold tenant data and therefore never enter the repo:
`C:/Surbhi-Git/hrlocal-data/ux-review/2026-10-31/` — `positions-{desk,phone}.png`,
`my-profile-{desk,phone}.png`, `org-settings-{desk,phone}.png`, `home-{desk,phone}.png`,
`arjun-home-desk.png` (the password page).

### 2.1 What the browser showed that code could not

| # | Seen today | Why it matters |
|---|---|---|
| **E1** | **The Positions chart does not load on this bench.** The page, the title, the six filters and the find box all draw; the body says *"**The chart did not load.** Nothing has changed in your seats or your people. Check your connection, then try again. If it keeps happening, tell your administrator: code POS-LOAD."* with a **Try again** button | Two things. First: the chart, tray and seat dialog in this design are **unverified against a render** — treat every layout claim about them as read-from-code. Second, and better: this is **a good failure state**, and it is the model the mini profile's failure state copies (§6.3). The cause is the known local one (`Replacement Plan` not migrated), not a product bug |
| **E2** | **My profile shows an error and nothing else** for an HR user who has no Employee record: *"Something went wrong at the office. Tap Try again in a minute. If it keeps happening, tell HR."* `hr@ppj.dev.alvoraa.co` has no `Employee` row, so `birthdays_this_month` throws | A new state nobody had listed. My profile is about to become the employee's main screen; it cannot show a raw failure to an administrator who simply is not a member of staff. Designed as **S1-E** in §6.1 |
| **E3** | **The password page is Frappe's own.** `/update-password` renders Frappe's "Set Password" screen: Frappe's box logo, English only, a greyed **Confirm**, and **"Back to sign in"**, not "Back to the portal". The return to the portal after a *successful* change is ours (`auth.py`, confirmed in code) | The brief says "a link is the whole feature". The link is the whole *build*; it is not the whole *experience*. A frontline worker on a Hindi phone lands on an English Desk screen. ⚠ DECISION 6 |
| **E4** | Organisation Settings is exactly the ten-card pattern `01a` described, and **the red `Delete` beside every row is still there** (anti-pattern OS2, now seen in a browser rather than in code) | The new card must not add an eleventh instance of it. It does not — nothing on the new card deletes anything |
| **E5** | Nothing scrolled sideways at 390 px on any page I could reach. Slice 070's frame work is holding | Confirms the constraint "do not undo 070" is about controls, not the frame |

### 2.2 Measured facts (read-only queries, 31 Oct 2026)

Carried from `01a` and `07`, plus three new ones.

| Fact | Value |
|---|---|
| Active employees · with a photo | 403 · **0** |
| Seats · assignments · branches | 120 · 403 · 6 |
| Default view = two levels | 55 boxes, up to **165** faces on first paint |
| Table, unpaginated | 120 rows, up to **360** faces |
| Biggest seat | Sales Executive, Noida Sector 18 — **25 people** |
| `position_table` payload | 141,816 bytes raw / **10,717 gzipped**, 2 queries for 403 people |
| Employee Document Types | **18**, and I read all of them (table below) |
| Employee Document rows | 6,469 — 6,468 "Expired", **0 with a file** |
| **New:** `cell_number` on the six employees I sampled | **empty on all six** — so My profile's "Mobile number" field is empty for most people, and its empty state is the normal case, not the edge case |
| **New:** `Employee Document Type.category` | the doctype's own Select offers six options — Identity, Address, Education, Employment, Statutory, Verification — but PPJ's data **also holds "Company Issued"** on two rows. The field has values outside its own option list |
| **New:** who holds HR Manager on this copy | 5 user accounts, of which **3 are real people** — so "7 people can open Positions" in the prototype is a sample figure; the live count comes from the server |

**The 18 types, with their real categories and who collects them.** This is the list the
settings card has to render, and it is why that card carries the weight.

| Category | Types (collected by) |
|---|---|
| Identity | PAN card (Employee) · Aadhaar card (Employee) · Passport-size photographs (Employee) |
| Address | Address proof, current (Employee) |
| Education | Highest education certificate (Employee) |
| Employment | Previous employer relieving letter (Employee) · Last 3 months' salary slips (Employee) · Signed offer and appointment letter (HR) |
| Statutory | Bank account proof (Employee) · UAN / PF details (Employee) · ESI number (Employee) · Security agency licence (Store Admin) |
| Verification | Background verification report (HR) · Police verification certificate (Store Admin) · Police verification acknowledgement (Store Admin) · Reference check note (Manager) |
| Company Issued | Signed policy acknowledgement (HR) · Vault access authorisation (Manager) |

### 2.3 Keep — do not undo

- Slice 070's phone frame and 44 px zoom buttons.
- Three names then a count on a card (`POS_NAMES_SHOWN = 3`); the tray holds all 25.
- Two levels open by default.
- One renderer (`ocAvatar`, `ocRender`) for the Organisation chart and Positions.
- Slice 065's `.private` class, the session-only "hide before you share your screen" link,
  and slice 069's print suppression.
- The existing `my-docs-card` on Home. This slice does not touch it.

---

## 3 · Benchmark

**Nothing new was gathered today.** `01a` §5 stands in full and is not repeated: Frappe HR
already puts the photo on every node card (verified in this repo); Keka has an Employee
Profile Layout an admin configures; Zoho has a configurable view-only field set from the
chart **that its own users cannot predict**; Keka can download the chart as an image.

Two rows I would add from the brief's own research, because they shape screens here:

| Claim | Label | What it changes in this design |
|---|---|---|
| Frappe HR ships a **public, login-free Web Form** in this repo — `hrms/hr/web_form/job_application/`, `login_required: 0` | **read in this repo, 31 Oct 2026** (PM) | The pre-onboarding section of the settings card is drawn **both ways**, so you can see what our own list costs against the one that already exists (§6.5) |
| Zoho People's profile photo limit is 2 MB | read, 31 Oct 2026 | Our upload resizes on arrival rather than refusing a big file. A frontline worker should never see "your photo is too big" |

**What we deliberately do not copy** is unchanged: no face matching, no chart export as an
image, no unpredictable field picker, no hover preview, no grey silhouettes.

---

## 4 · Findings — what this design fixes, in order

IDs continue `01a`'s. Severity uses the P0–P4 ladder.

| ID | Finding | Impact | Kind | Size | Severity | Evidence |
|---|---|---|---|---|---|---|
| PF1 | 0 of 403 have a photo | High | New | — | P1 if nothing collects them | measured |
| PF2 | The Positions feed drops `image` although card, CSS and the Organisation endpoint all handle it | High | Fix | S | — | F2–F5 |
| PF3 | A field list on a page whose audience is a tenant tick; Frappe's levels lock **write**, not read | High | New | M | **P0** until the server deny list exists | `employee_field_rights.py` |
| PF4 | Documents on this page are identity, statutory and background scans for a wider audience | High | New | M | **P0** until the file is streamed by our own endpoint | §7, OPS-4 |
| PF6 | Up to 165 photos on first paint, 360 on the table, nothing resized anywhere in the repo | High | New | S–M | **P2** against 2.5 s / 3G | §5 |
| PF7 | `#emp-drawer` has no `role="dialog"`, no `aria-modal`, no Escape, no focus move | Medium | Fix | S | **P2** (WCAG 2.2 AA) | `drawers.html:111` |
| PF11 | The profile's fields must be their own call, not columns on `position_table` | Medium | New | S | P3 | §9 |
| PF12 | A failed photo falls back to initials silently | Low | New | S | P4 | §5 |
| **PF13** | **My profile shows a raw failure to a user with no Employee record** — seen today | Medium | Fix | S | **P2**, and it is about to become a landing screen | E2 |
| **PF14** | **The password page is Frappe's, in English, with "Back to sign in"** | Medium | Improve | S–M | P3, ⚠ DECISION 6 | E3 |
| **PF15** | **Initials in the chart avatar render at about 10 px** — below our own 12 px floor. The prototype raises them to 12 px inside the same 24 px circle, which fits | Low | Fix | S | P3 | measured in the prototype; the product's `.oc-who .av` is 24 px |
| **PF16** | **"Company Issued" is a category value outside the doctype's own Select options.** Any rule written as "only Company Issued types" is written against a value the doctype does not officially have | Medium | Fix | S | P3 — it is a data/metadata fault for the analyst, not a screen | `employee_document_type.json` vs PPJ data |
| **PF17** | **Mobile number is empty on every employee I sampled.** The My profile "details" card is mostly an empty form at switch-on | Medium | New | S | P3 | measured |
| **Keep** | The three-names rule, two levels, one renderer, 070's frame, 065's screen-share link, 069's print rule, the POS-LOAD failure wording | — | Keep | — | — | §2.3 |

---

## 5 · Faces — what I did so they are survivable

You were told the price and chose faces anyway. This is the part of the design that earns
that decision. **Nothing here removes faces.** Six measures, cheapest first, and the
reason each one exists.

### 5.1 The measures

| # | Measure | What it is | What it buys |
|---|---|---|---|
| 1 | **Only fetch what is on screen** | `loading="lazy"` plus `decoding="async"` on the photo | This is the big one and it changes the headline number. The chart opens two levels — 55 boxes, up to 165 faces — but at 1440 × 900 roughly **a dozen boxes** are actually on screen, so about **30 photos** are requested on first paint, not 403. The rest arrive as she scrolls. `[ASSUMPTION — the engineer should measure the real on-screen box count at the strategy gate]` |
| 2 | **Fixed width and height on every photo** | `width="24" height="24"` (or 40 — ⚠ DECISION 1) as attributes, not only CSS | Nothing reflows as photos land. A chart that jumps while it loads is worse than a chart with no faces |
| 3 | **The initials sit *under* the photo, not instead of it** | The avatar is one circle containing the two initials, with the photo layered on top at `opacity:0` until it loads | This single change gives us the **loading state**, the **failed state** and the **printed state** for nothing. There is never an empty circle, never a broken-image icon, never a grey silhouette, and never a gap |
| 4 | **A 48 px copy made once, when the photo is uploaded** | One hook, one Pillow call, at upload time. Not Frappe's `make_thumbnail`, which writes into `public/` (OPS-2) | ~2–3 KB per face instead of 40–200 KB. This is the one new mechanism and `no-over-engineering.md` §5's measured-exception rule is what allows it: 165 originals against a 2.5 s / 3G budget is two orders of magnitude out |
| 4b | **The stored photo itself stays, bounded** | The upload hook already converts to JPEG and caps the size (OPS-7, OPS-8). Spec it as **longest edge 512 px, quality 82** — about 30–60 KB | This is the picture the enlargement in §6.3.1 uses. **No second stored size is needed**, and nothing on the chart ever asks for it |
| 5 | **One request per person, not per box** | The same URL for a person drawn in three boxes (slice 072 copies) and in both the table and the chart | The browser dedupes it. 403 people is at most 403 photos however many boxes exist |
| 6 | **The wall chart loads every face first, and says so** | Before `window.print()`: *"Getting 55 photos ready…"*, then print. Ctrl+P keeps faces **off** | A lazy image prints as a blank circle (DevOps §5b). Because of measure 3, "faces off" is not a hole — it is the same chart with letters |

### 5.2 What the person sees while a photo is arriving

Exactly today's chart. **The circle is drawn at its final size with the person's initials
in it.** When the photo arrives it fades in over the initials in 150 ms. Nothing moves, no
spinner, no skeleton, no placeholder shape. Switch the prototype to *Faces on the chart →
Photos still arriving* to see it.

### 5.3 What happens when one fails

The photo simply never fades in. The initials stay. **No message, no icon, no retry.** A
failed face is not news to the person reading a chart, and a retry would cost another
request from the same eight slots. Prototype state: *One photo failed* (Ritika Malhotra).

### 5.4 What prints

| Path | Faces | Why |
|---|---|---|
| **Ctrl + P** | **Off** | One print rule beside slice 069's, `@media print { .av img { display:none } }`. The initials are already underneath |
| **Wall chart (slice 069)** | **A tick, off by default:** "Include photographs" | Recognising a manager may be the whole point of a chart on a staff-room wall. But a customer walks past that wall, so it is a deliberate tick each time, never remembered. ⚠ DECISION 2 |
| **A printed mini profile** | Nothing in the drawer prints, as 065 and 069 already do | — |

### 5.5 The one risk I cannot design away

**The ~8 concurrent request slots.** Measures 1 and 5 cut the count from ~403 to roughly
30 on first paint; measure 4 makes each one tiny. But they are still answered by Python,
because `/private/files/` is not named in nginx. If the engineer finds that 30 concurrent
30 ms requests still queue behind a payroll run, the next cheapest step is OPS-3
(X-Accel-Redirect), and **DevOps' own advice is not to touch nginx in this slice**. I am
recording this rather than hiding it: it is a `Risk`, owner `hrms-devops-engineer`, to be
re-measured at the strategy gate.

### 5.6 Faces in the table

In, as asked. A **24 px** circle before each name in "Who is in it", same avatar, same
lazy rule. A table cell is ordinary markup, so the name becomes a real link with no change
to any shared component. Only the rows on screen fetch a photo — about 15 of 120.

---

## 6 · Screen by screen, with the real words

English first. Hindi beneath, **machine drafts for a native reviewer** (standing open item),
and every new string goes through the existing `drT()` wrapper.

### 6.1 My profile — Employee, phone first

Four cards in the existing `#panel-my-profile`, in this order: **picture, details,
documents, password.** Picture first because it is the one-tap job and the thing the whole
slice depends on.

**S1 · Your picture, nobody has one yet (today's state)**

> **Your picture**
> **Add your picture**
> Colleagues who can already see you on the organisation chart will see it next to your
> name. Nothing else changes. Nobody uses it to check who you are or when you arrived.
> [ **Take a photo** ] [ Choose a file ]
> We make it smaller before we keep it, so it uses almost none of your data.

*Hindi:* **अपनी तस्वीर जोड़ें** · जो साथी आपको संगठन चार्ट में पहले से देख सकते हैं, उन्हें आपके नाम के साथ यह
दिखेगी। और कुछ नहीं बदलता। कोई इससे यह नहीं जाँचता कि आप कौन हैं या कब आए।

Two sentences do real work. *"can already see you"* says the audience does not widen.
*"Nobody uses it to check who you are or when you arrived"* is the refusal, said to the
person it protects, in their words — not buried in a policy.

**S1-A · After it is saved**

> *(the circle is now their picture)*
> **That is you. Colleagues who can see you on the organisation chart will see this picture.**
> [ Replace ] [ Remove ]

*Hindi:* **यह आप हैं। जो साथी आपको संगठन चार्ट में देख सकते हैं, उन्हें यही तस्वीर दिखेगी।**

**S1-B · While it is sending** — "Sending your picture… You can keep using the page." The
person is not blocked. If the call times out at 15 s, slice 070's honest wording applies:
*"We could not reach the office. Your picture may have gone through. Open this page again
in a minute and look before you send it a second time."*

**S1-C · Your details** — the six ticked fields, each a labelled input, 16 px text and
48 px high on a phone. Placeholder for an empty field is **"Not given yet"**, which is the
normal case at PPJ (PF17), not a fault.

> **Your details**
> Only you can change these. HR sees the change.
> Mobile number · *We use it only to reach you about work.*
> Personal email · *Used if you are ever locked out. Not shown to colleagues.*
> Current address · *Where you live now. Not shown to colleagues.*
> Emergency contact name · Relation · Emergency contact phone · *Used only if something happens to you at work.*
> [ **Save** ]

**S1-D · Nothing ticked** — the card stays, and says so rather than disappearing:
*"Your organisation has not chosen any detail for you to change here yet. To correct
something on your record, tell HR."*

**S1-E · No Employee record (new, from E2)** — replaces today's raw failure:

> **This account is not linked to an employee record**
> You are signed in as an administrator, not as a member of staff, so there is nothing
> here about you. If you should have an employee record, ask HR to link it to this account.

**S1-F · Your password**

> **Your password** · You last set it on 12 Oct 2026.
> [ **Change my password →** ]
> Opens the password page. When you have changed it you come straight back here.

That is the whole build. **But see E3 and ⚠ DECISION 6** — the page it opens is Frappe's,
in English, and its "cancel" says "Back to sign in".

**S1-G · Your documents** — the existing `my-docs-card`, unchanged, moved into this panel's
order. Hidden entirely when the plan is off. Nothing in this slice changes it.

### 6.2 Faces on the chart — HR Manager / CXO

No new component. `ocAvatar` gains the layered photo described in §5. Everything else on
the card is untouched: title, subtitle, three names, "+22 more in this seat", the whole card
still one `<button>`.

**The size is your choice.** The prototype draws both:

| Option | What it looks like | Cost |
|---|---|---|
| **24 px circle** (today's `.oc-who .av`) | Three names fit in a short card; the chart's shape is exactly as it is now | Nothing |
| **40 px photo** | Much easier to recognise across six stores | Every box grows by about 48 px, so fewer seats fit on a screen and the wall chart needs more sheets |

⚠ DECISION 1. My recommendation is **24 px**, because the chart's job is structure and the
mini profile is one click away with a big picture in its header. But "full photos on the
chart cards" may have meant the bigger one, so I drew it rather than assume.

### 6.3 The mini profile — one component, used everywhere

> **Changed in v2.** Surbhi, 31 Oct 2026: *"I would wish to show the same view here as it
> shows in Positions expanded view."*

**There is one mini profile, not two.** The same eleven details, the same sentence under
them, the same Documents section with the same "Hide before I share my screen" control, and
the same six states. It is built once and called from every place a name is clickable.
Neither caller holds a copy of the field list or the wording, so **the two cannot drift
apart** — which is the whole of her point, and it makes the build smaller, not larger.

Opened from four places:

| From | How |
|---|---|
| **The table** | Each name in "Who is in it" is a real link |
| **The seat tray** | Each name in the tray's people list is a real link. This is the only surface that can hold a 25-person seat, so it is the complete list |
| **The seat page** ("Change this seat") | The same drawer, opened the same way — §6.4 |
| **(not) a chart card** | Never. The card is a single `<button>`; a link inside it is invalid HTML and Chrome has already broken this page over exactly that. Clicking the card opens the tray |

**Not** from inside a chart card. The card is a single `<button>`; a link inside it is
invalid HTML, and the code already records Chrome breaking the card over exactly that.
Clicking the card opens the tray, which is one tap and holds everyone.

**The four conditions on `#emp-drawer`, carried from `01a` and binding:**

1. `role="dialog"`, `aria-modal="true"`, `aria-labelledby="ed-name"` — the payslip drawer
   beside it already has the first two.
2. **Escape closes it**, and focus moves to the drawer's name on open.
3. **Focus returns to the name that opened it** on close, and focus is trapped inside while
   it is open.
4. The close button is **44 × 44**. The drawer is already `max-width:100vw`, so it is full
   screen on a 360 px phone.

**S3 · The profile itself**

Header: the person's photo (or initials) at 40 px, their name, then job role · branch.
Body: a definition list of only the ticked fields, then documents.

> Job role · Department · Branch · Company · Reports to · Grade · Employment type ·
> In the company since · Shift · Work email · Work phone
>
> These are the details your organisation chose to show. Pay, bank details, identity
> numbers, date of birth and personal contact details are never shown here.

Two deliberate wordings. **"In the company since"**, not "Date of joining" — it is the fact
a reader wants and it does not read like a payroll field. **"Work phone"**, never the
personal mobile; where there is none, the value is **"Not recorded"**, never blank.

**S3 states**

| State | What it says |
|---|---|
| Loading | Three grey bars at the shape of the list, then *"Getting the details…"*. If 10 s pass: the failure below |
| Failed | *"**We could not reach the office.** Nothing has changed about this person. Check your connection and try again. If it keeps happening, tell your administrator: code POS-PROFILE."* [ Try again ] — the same shape as the POS-LOAD message seen today (E1) |
| Nothing ticked | *"Your organisation has not chosen any other detail to show here."* A System Manager, and only a System Manager, also sees a link to the setting |
| A field the reader may not see | The row is **absent**, not blank and not "hidden". A reader scoped out of a branch never learns there was a branch |
| The person has left | A warning line: *"**Kiran Sandhu left on 30 Sep 2026.** You are looking at how the seat was, not how it is."* |
| Documents off (plan off, or none ticked) | **No section at all.** Not an empty heading, not a greyed tab |

**S3-D · The documents section**, when types are ticked:

> **Documents**
> The 3 types your organisation chose to show here. Opening one is recorded.
> [ Hide before I share my screen ]
> Signed offer and appointment letter · *Verified* · View
> Signed policy acknowledgement · *Verified* · View
> Vault access authorisation · *Not given* · collected by HR

Rules: the existing My-profile row shape, reused exactly — type, status badge, **View**
link. **No inline preview, no thumbnail, no download-all, never printed.** Slice 065's
screen-share control covers this section too. A type with no file says who collects it,
which turns a dead row into an action for the reader.

And the one that is not a design rule but must be in the spec: **"View" must call our own
whitelisted endpoint, not a `/private/files/…` URL** (OPS-4, PF4). Otherwise the ticked
list is decoration and anyone who can read the Employee record can fetch every file on it.

#### 6.3.1 The enlarged picture — new in v4

> Surbhi, 31 Oct 2026: *"on hovering over the photo in the employee details page the photo
> should enlarge."*

**What it is for, honestly.** To **recognise somebody**. A 24 px circle on a chart, or the
40 px one in the drawer's header, is enough to tell two people apart in a list you already
know; it is not enough to match a face to someone you met once at a store two months ago.
That is the CXO job this whole slice exists for — *"is that the person I met at Karol
Bagh?"* So the reason is real, and it sets the size: big enough to recognise a face, which
is why 240 px rather than 96 px.

**The counterweight, said out loud.** An enlarged face of a colleague, on a page that
colleague cannot open, is the part of this slice that leans furthest toward *looking at a
person* rather than *reading a structure*. It is still ordinary — an internal directory
photo at a readable size — so I am not refusing it. Two guards keep it ordinary: there is
**no download, no "open in new tab" and no save action**, and it is covered by slice 065's
"hide before you share your screen" and slice 069's print suppression, like everything else
in the drawer.

**It is a button first, and hover is a shortcut on top.** That one decision answers touch
and the keyboard at the same time, instead of giving the phone a worse version:

| Input | Opens | Closes |
|---|---|---|
| **Mouse** | Pointer over the photo | Pointer leaves both the photo and the enlargement. A click **pins** it, and then it closes like the others below |
| **Touch** | A tap on the photo. The photo lives in the drawer's **fixed header**, not in the scrolling body, so a scroll can never trigger it | The Close button (44 px), a tap outside the card, or the system back gesture |
| **Keyboard** | Tab to the photo, then Enter or Space. Its name is *"Show a bigger picture of Kiran Sandhu"* | **Escape**, which closes the enlargement **and only the enlargement** — press it again to close the drawer. Focus returns to the photo |

**Where it appears, and how big.**

It is **an overlay inside the drawer**, not a third layer. The drawer may already be over
the chart; a lightbox on top of that would be three stacked things and would make Escape
ambiguous. Keeping it inside the drawer means Escape has one meaning at a time, and the
person never loses their place.

| Width | Picture | Note |
|---|---|---|
| Laptop, 480 px drawer | **240 px square**, with the name and job under it | Five times the header avatar. Enough to recognise a face |
| Phone, 390 px (drawer is full screen) | **min(62% of the frame, 320 px)** = about 240 px | Same as a laptop in practice |
| Phone at 200 % text, 195 px | about **120 px** | Small, and that is the honest limit of a 195 px screen. Still two and a half times the header avatar, and the name beneath it stays full size |

**Where the picture comes from, and what it costs.**

**No new stored size, and no extra bytes at rest.** §5 derives a 48 px copy for the chart;
the upload hook already keeps a bounded JPEG of the photo itself (§5, row 4b — longest edge
512 px, about 30–60 KB). The enlargement uses that. 512 px is ample for a 240 px square
even on a 2× screen.

**Fetched only on demand**, which keeps §5's request budget intact: the chart still asks
for nothing but 48 px copies, and the full picture is requested the moment somebody hovers,
taps or presses Enter — **one request, for one person, cached for the rest of the session**.
A reader who never enlarges anything downloads exactly what they download today.

**So it never looks empty while it arrives**, the 48 px copy is shown scaled up and blurred
straight away, and the real one fades in over it when it lands. That is the same structural
trick as §5 measure 3 — the smaller thing is already underneath — so it needs no spinner.

| State | What is shown | Drawn |
|---|---|---|
| Open, picture loaded | 240 px picture, name, job, Close | ✓ |
| Open, still arriving | The 48 px copy blurred at 240 px, plus *"Getting the full picture…"* | ✓ |
| The full picture failed | The blurred copy stays, with *"This is the small copy. The full picture did not load."* No retry — a retry is another request for something nobody is waiting on | ✓ |
| The person has no photo | **The photo is not a button at all.** Initials do not enlarge, and a control that does nothing is worse than no control | ✓ (switch *Photos on file* to *None*) |

**Not on My profile.** Your own picture is already 96 px there, on a page about you. Adding
it would be a control for a problem nobody has.

### 6.4 The seat page — "Change this seat" stops being a dialog

> **Changed in v2.** Surbhi, 31 Oct 2026: *"I like the idea making the Change this seat as
> a page."* In the live product it is a modal (`#pos-editor`, a `.gp-backdrop`). The v1
> prototype drew it as a page and she wants the page.

**It becomes a page**, reached from the Change button in the table, from "Change this seat"
in the seat tray, and by its own address so one person can send it to another. Back to
Positions is a labelled link at the top left, not a ✕.

The page has three parts, in this order:

1. **The seat** — title, branch, department, who it reports to, "3 of 3 filled".
2. **Who is in it** — every person, with their face, any leaving flag, and **Take out**.
3. **The seat itself** — the form that was in the dialog, unchanged.

**This removes the reason the details had to expand in place.** My v1 note said a drawer
over the dialog would be two layers, two focus traps and two closes on a phone. On a page
there is no dialog underneath, so that objection is gone — and the mini profile can be the
same drawer the rest of the product opens.

**⚠ DECISION 10 — the one thing left to choose. Both are in the prototype.**

| Option | What happens | Good at | Bad at |
|---|---|---|---|
| **The drawer** *(recommended)* | The name opens the same right-hand drawer as Positions | HR learns **one** behaviour for one job; the seat's own form stays where it is; a phone gets the full-screen view it already knows; one component, no second layout | You cannot see the drawer and the other people in the seat at the same time |
| **Open in place** | The row expands and the details appear inset under it | Comparing two people in the seat without closing anything | The eleven details plus the documents list are tall: in the prototype, opening the first of three people pushes the other two about 400 px down the page. It is also a second layout of the same component, which is the thing she just asked us to stop having |

**The content is identical either way. That part is settled** and is not a decision.

If the drawer is chosen, the four accessibility conditions in §6.3 apply unchanged, and
Escape closes the drawer and returns focus to the name. If "open in place" is chosen: the
name is a `<button aria-expanded>`, only one row opens at a time, Escape closes the open
row, and the inset block carries a left border so it plainly belongs to the row above it.

### 6.5 The Organisation Settings card

> **Changed in v3.** Surbhi, 31 Oct 2026: *"instead of in page collapsible panels, use a
> button to add/remove fields to open a dialog to see the selected fields and update. and
> show the selected fields in main page once the user says ok on the dialog box. same for
> the employe document type field"*

**One new card** on the existing page, after the ten already there, titled:

> **What people can see and change about each other**
> Only a System Manager can change these, and every change is recorded with who made it
> and when.

Inside it, four lists. Each one is now **an answer, not a drawer**:

- **The page shows what is chosen** — the real field names and the real document types, as
  the resting state. Not a count, not "and 8 more".
- **One button** — *Add or remove fields* / *Add or remove document types* — opens a dialog.
- **The dialog is where the choosing happens**: the whole list, grouped, with what is ticked.
- **OK closes the dialog and the page shows the new selection. Cancel changes nothing.**

**Why a dialog here when the seat page stopped being one (§6.4).** They are different jobs.
The seat page is somewhere you stay and do several things, so it earns an address. Choosing
from a list is short, self-contained and cancellable, and you come straight back to what you
were reading — which is exactly what a dialog is for. The two decisions do not conflict.

#### 6.5.1 Where the warnings go, and why

v2 put all the weight on the document list: a category chip per row, a red line on a ticked
sensitive type, a "What you are about to share" summary, and a Save button that named the
consequence. **That weight is what made the screen safe**, because you chose "HR ticks the
list, no restriction from us". None of it is lost. It splits by **moment**:

| Moment | Where it lives | What it is |
|---|---|---|
| **While you are choosing** | **In the dialog** | The standing "read this once" warning at the top · the real category as a chip on every row · who collects it and whether anybody has given one · a **red line the moment a sensitive type is ticked** · a running "What you are about to share" summary · an OK button that names the consequence: **"OK — 3 document types, seen by 7 people"** |
| **The standing consequence of what is already chosen** | **On the page** | The chosen types listed by name with their category · an amber sentence: *"**1 of these 3 is an identity, statutory, verification, employment or address document.** The **7 people** who can open the Positions page can open the file itself, for everyone in their own companies and branches."* |

**The move makes this better, not worse, and that is worth saying plainly.** In v2 a
collapsed panel said *"3 of 18 · 7 readers"* and nothing else — you had to open it to find
out what had been chosen or what it meant. In v3 the consequence of today's setting is on
the page, in words, without opening anything.

#### 6.5.2 Does OK save? Yes. There is no second Save

**Decided, not a ⚠ DECISION — but say so if you disagree.** The dialog's **OK saves**. The
page has no Save button, so **nothing is ever left unsaved**.

I considered the other way — OK stages, the page keeps one Save — and rejected it, because
it creates the very risk it is meant to avoid: two dialogs' worth of staged change sitting
on a page that a closed tab throws away. With OK-saves there is no unsaved state to lose.

Three things make that safe rather than hasty:

1. The consequence is **on the OK button**, not after it.
2. Each list is an independent setting. There is nothing to batch.
3. It is reversible in the same two clicks: press the button again and untick.

**Preview moves into the dialog**, where it belongs: it shows what a reader will see for
what is ticked *right now*, before OK. After OK the page says *"Saved. 3 document types are
now shown on the Positions page."* and the "Last changed by … Every change here is
recorded" line updates.

#### 6.5.3 The four lists on the page

| List | Resting state shows | Button |
|---|---|---|
| **What a reader sees about a person on the Positions page** | The 11 chosen details as chips, above a line naming the audience: *"These 11 details are visible to the **7 people** who can open the Positions page, for everyone in their own companies and branches. [See who]"* | Add or remove fields |
| **Which documents appear on a person's card** | Each chosen type on its own row, with its category and, where it applies, an "identity, statutory or background" mark, under the amber standing sentence | Add or remove document types |
| **What an employee may change about themselves** | The 6 chosen details as chips, plus *"A photo is always on. Every employee may add or replace their own picture, and they are told who sees it before they do."* | Add or remove fields |
| **What a new joiner is asked for** | Both ways still drawn (§6.5.5) | Add or remove fields / documents |

**The empty state matters here and is drawn.** With nothing ticked, the documents list says:

> No document types are shown on the Positions page. Nobody can open an employee's
> documents from there.

That is the safest setting and it should read as a statement of fact, not as a gap to fill.
There is no prompt, no "add your first", no empty-state picture.

#### 6.5.4 The dialog itself

- **Laptop:** a 620 px box, centred, scrolling body, footer pinned.
- **Phone:** a **full-screen sheet**. An 18-row list inside a floating 300 px box is a
  scroll inside a scroll. Measured at 390, 360 and 195 px.
- **Footer order.** Laptop: *Preview* on the left, then *Cancel*, then **OK**. Phone: the
  buttons stack full width, **OK first**, then *Preview*, then *Cancel* — the thumb reaches
  the bottom first, and the destructive-of-work button should not be what it lands on.
- **The document list is grouped by category** — Identity, Address, Education, Employment,
  Statutory, Verification, Company Issued — with the group name above each block. 18 flat
  rows is a wall; the grouping is also the warning, because it puts "Identity" above the
  PAN card rather than beside it.
- **Accessibility**, the same four conditions as the drawer: `role="dialog"`,
  `aria-modal="true"`, `aria-labelledby`, **Escape cancels**, focus moves to the dialog's
  heading on open and **returns to the button that opened it** on close, focus trapped
  while open, close control 44 × 44.

#### 6.5.5 The fourth list — pre-onboarding, still drawn both ways

Unchanged from v2 except that it now follows the same shape. Two buttons at the top of the
section, **Our own list** and **Frappe's Web Form**.

⚠ DECISION 5 is unchanged. The PM recommends the Web Form's own builder; so do I, for one
reason that is a design reason and not a cost one: **two pickers for one form will disagree,
and the person who finds out is the joiner, on a form that then asks for the wrong things.**

#### 6.5.6 Is the page safer than v2 was? Yes, and this is why

The coordinator asked me to check this rather than assume it. **The page is safer, on three
counts, and one caveat.**

1. **v2's consequence was one click away, and nobody clicks a panel they think they already
   understand.** A collapsed panel reading *"3 of 18 · 7 readers"* tells a System Manager
   nothing about *which* three. In v3 the three are named on the page, with their
   categories, every time anyone opens Organisation Settings.
2. **The sensitivity is now on the thing itself.** "Signed offer and appointment letter ·
   Employment · identity, statutory or background" is readable without opening anything. A
   wrong tick made six months ago is now visible to the next person who scrolls past, which
   is how a wrong tick actually gets found.
3. **The warning that matters while choosing is still in the dialog**, where the choosing
   happens, and the OK button still names the consequence. Nothing moved out of that moment.

**The caveat, drawn so you can judge it:** tags are compact when three types are chosen and
tall when twelve are. The prototype has a **12 documents chosen** state for exactly that.
At twelve the card is about two screens tall on a phone. I would not paginate it or
truncate it — a long list of exposed identity documents **should** look like a lot — but you
should see it before you agree.

#### 6.5.7 My one better idea — ⚠ DECISION 11, drawn beside yours

> *"If you have better idea I am open."* — Surbhi, 31 Oct 2026

**This is an extra option for you to compare, not a replacement.** The button-plus-dialog
pattern you asked for is built, works, and is what the rest of this design assumes.

Prototype state: **Remove on the tag (my proposal)**. It changes one thing about the
documents list only:

| Direction | Today (and in your pattern) | My proposal |
|---|---|---|
| **Adding** a document type — the risky direction, because it exposes something | Button → dialog → warning → tick → OK | **Unchanged.** Button reads *"+ Add document types"*, opens the same dialog with the same warning, showing the types not yet chosen |
| **Removing** one — the safe direction, because it exposes less | Button → dialog → find the row → untick → OK. **Four actions** | **One click on the row: "Stop showing this ✕"**, undoable for a few seconds |

**The reasoning, in one line: make the safe direction cheap and the risky direction
deliberate.** Realising *"we should not be showing Aadhaar here"* is the moment the product
should be fastest, and today it is the moment it is slowest. A removal can never expose
anything, so there is nothing to protect against beyond a slip, and an undo covers that.

**I recommend it**, but only mildly, and only for the documents list — the field lists are
not sensitive in the same way and do not need two mechanisms. If you would rather have one
pattern for all four lists, say so and I will drop it: **consistency across the card is a
good enough reason to refuse this**, and it is the one argument against it I find genuinely
strong.

### 6.6 The pre-onboarding form — the joiner, on a phone, with no account

Six screens, one column, 48 px controls, 16 px text, nothing wider than the screen.

**J1 · Welcome**

> **Welcome to PP Jewellers**
> Arjun Bhatia from HR sent you this link. Filling it in now saves you a morning of
> paperwork on your first day.
> **What we will ask for** — 7 details about you, 4 documents, and a photograph if you
> want one. About five minutes.
> **What happens to it** — Only PP Jewellers HR sees it. It becomes your staff record when
> you join. If you do not join, we delete everything you sent after 90 days. You can ask us
> to delete it sooner — the address is on this page.
> You do not need an account and you will not be asked for a password.
> [ **Start** ]
> This link is for you. Please do not pass it on.

*Hindi:* **पीपी ज्वैलर्स में आपका स्वागत है** · …

Three deliberate things. The notice is **before** the first question, not under a tick at
the end. **"You will not be asked for a password"** heads off the most common worry about
a link from an employer. The 90 days is a placeholder — ⚠ COMPLIANCE, counsel sets it
(brief ⚠ DECISION 13).

**J2 · Your details** — the ticked fields, one per row, with a hint where a joiner will
hesitate ("As it appears on your PAN card"). Footer: *"Your answers are kept on this phone
as you go, so you can stop and come back."*

**J3 · Your documents** — one block per type, each with **three** equal-width buttons:

> [ **Take a photo** ] [ Choose a file ] [ **I will bring it on my first day** ]
> A clear photograph of the document is fine. You do not need a scanner.

The third button is not a convenience. A joiner may not own the document yet, may be on
someone else's phone, or may not be able to scan anything. Without it, the form is a wall.

**J4 · Your photo** — optional, and said so:

> This is the picture colleagues will see next to your name on the organisation chart once
> you join. It is not used for anything else — nobody checks your face against it. You can
> skip it and add one later.
> [ Take a photo ] [ Choose a file ] [ Skip this ]

**J5 · Check and send** — a summary of everything, then:

> When you send this, PP Jewellers HR reads it and makes your staff record. You will not be
> able to change it here afterwards — ring HR if something is wrong.
> [ **Send** to PP Jewellers HR ]

**J6 · Sent**

> **Thank you. There is nothing else to do.**
> PP Jewellers HR has your details. You will hear from Arjun Bhatia before your first day.
> **Bring on your first day:** your bank account proof.
> If something above was wrong, ring HR on 0172 450 1180. This link will not open again.

**J-E1 · The link has run out**

> **This link has run out**
> Links last 7 days so your details cannot be opened by anybody else. Nothing you sent is lost.
> **What to do:** ring or message PP Jewellers HR on 0172 450 1180 and ask for a new link.
> They can send it to the same number.

**J-E2 · An upload failed**

> **That photo did not reach us.** It may be too big, or the signal dropped. Your other
> answers are safe on this phone — nothing is lost.
> Try again, or choose **I will bring it on my first day** and carry on.

A failure here never discards what was typed, and it always offers a way forward that is
not "try again".

---

## 7 · Every state, in one list

For the analyst, so none is missed. ✓ = drawn in the prototype.

| Area | State | Drawn |
|---|---|---|
| Chart | Nobody has a photo (today) | ✓ |
| Chart | Some have, some have not — circles the same size, nothing jumps | ✓ |
| Chart | Photos still arriving | ✓ |
| Chart | One photo failed | ✓ |
| Chart | Print / wall chart (faces off) | ✓ |
| Chart | 24 px circle vs 40 px photo | ✓ |
| Chart | A 25-person seat — three names, then "+22 more in this seat" | ✓ |
| Table | Faces and linked names | ✓ |
| Drawer | Normal, Loading, Failed, Nothing ticked, Documents off, Person has left | ✓ |
| Drawer | Picture enlarged; enlarged and still arriving; enlarged and the full picture failed | ✓ |
| Drawer | No photo — the picture is not a button | ✓ |
| Drawer | A field the reader may not see — the row is absent | described, §6.3 |
| Seat page | The page itself | ✓ |
| Seat page | Name opens the drawer (recommended) | ✓ |
| Seat page | Name opens in place, open and closed | ✓ |
| My profile | No photo / has a photo / sending / send failed | ✓ |
| My profile | Nothing ticked to edit | ✓ |
| My profile | No Employee record | ✓ |
| My profile | Save failed, "may have gone through" | ✓ |
| My profile | Documents card hidden when the plan is off | described |
| Settings | The page at rest, showing every chosen field and document type | ✓ |
| Settings | Each of the three pickers open, laptop and full-screen phone | ✓ |
| Settings | Nothing chosen — "No document types are shown on the Positions page" | ✓ |
| Settings | 12 document types chosen — the tall case | ✓ |
| Settings | "Remove on the tag", my proposal (⚠ DECISION 11) | ✓ |
| Settings | Saved, with the confirmation line | ✓ |
| Settings | Both pre-onboarding options | ✓ |
| Settings | Not a System Manager — the whole card is absent, not greyed | described, §8 |
| Joiner | Welcome, details, documents, photo, check, sent | ✓ |
| Joiner | Link expired, upload failed | ✓ |
| Joiner | Already submitted — "this link will not open again" | described, J6 |
| Everywhere | Hindi; Devanagari runs about 30 % longer | ✓ (switcher) |
| Everywhere | Dark theme | ✓ (switcher) |

---

## 8 · Privacy, permissions and the refusals

**Who sees what, per screen.**

| Screen | Who | The least they need? |
|---|---|---|
| My profile | The person themselves only | Yes. No other employee's data appears |
| Mini profile | Whoever has Frappe Read on `Alvoraa Position`, scoped to their companies and branches. **At DTC: HR Manager** | Only if the ticked list is short and the server refuses anything off it |
| The documents section | The same readers. **This is the widening** — today these files live on the Employee record in Desk | Your decision; the screen makes the consequence visible before the tick is saved |
| The settings card | **System Manager only.** The card is absent for everybody else, never greyed | Yes. It joins the `ACCESS_GRANTING` set in `settings.py`, which already writes a `Version` record on every change |
| The pre-onboarding form | A stranger holding a one-time link | The form must ask for the fewest fields that make a staff record, and nothing else |

**Four rules the server must enforce, not the browser.**

1. **A deny list no tick can override** — pay and CTC, bank, statutory identifiers, date of
   birth, personal contact, home address, emergency contact, marital status, blood group,
   anything health-related, the relieving date, and every field a payroll rule set names.
   The endpoint refuses an off-list field **even when posted directly**.
2. **The document file is streamed by our own endpoint**, which checks both that the reader
   may see this employee on this page and that the type is ticked. Never a
   `/private/files/…` URL. `Employee Document` is a child table; a rule written at the row
   never reaches the file (ALV-256, two days old).
3. **The profile is its own call**, one small read when a profile is opened. Ten fields for
   403 people on the table payload is 4,030 personal values in a browser that is showing ten.
4. **The photo is resized and converted on upload**, which strips metadata as a side effect.
   Frappe's EXIF strip only runs for JPEG, so a PNG or HEIC selfie keeps its GPS.

**⚠ COMPLIANCE, two, both carried from the brief and both still open.**

- One sentence in the privacy notice before the first photo is collected. Draft: *"The
  photo on your record is shown next to your name on the organisation and positions charts
  to colleagues who can see you."* Owner: Surbhi with `hrms-security-privacy-engineer`.
  Blocks switching the photo upload on at a tenant.
- The pre-onboarding form's lawful basis, consent wording and retention period for someone
  who never joins. Owner: counsel, via Surbhi. Blocks building the form at all.

**The refusals, written down so they cannot arrive later.** A photo collected anywhere in
this slice is never matched, compared, scored, or used to confirm who checked in. The field
app's check-in photos are never reused as profile photos. No emotion or facial analysis,
ever. No "download the chart as an image". No photo opt-out was designed — ⚠ DECISION 4
is where you overrule that.

**The one-way rule check.** Does any part of this improve a manager's convenience by
degrading an employee's experience? The honest answer is **the documents section does, a
little**: it makes an employee's scans reachable from a structure page by people who
previously had to open Desk. It is not a new permission, but it is a new door. You decided
it is in, and I have carried that. What I have refused to do is let the decision be made
silently: the settings card names the audience, the category and the count, and the
employee's own My profile card tells them who sees their picture. If you want one more
mitigation that costs almost nothing, it is ⚠ DECISION 3.

---

## 9 · Accessibility — WCAG 2.2 AA, measured

Measured in prototype **v4** with Playwright at **390 px, 360 px and 195 px** across all 7
screens and all 35 states — 735 renders. **0 faults at every width**, including the three
pickers as full-screen sheets and the enlarged picture.

v4 found one more fault at 195 px, and it is the same lesson as the last two: the enlarged
picture was sized in `vw`, which is the **browser**, not the phone frame, so at 200 % text it
was wider than the screen. Sized from the frame now.

| Check | Result |
|---|---|
| Overflow past the app or the drawer, at 390, 360 and 195 px | **None**, any screen, any state |
| Tap targets under 44 px on a phone | **None**, except the checkbox inputs themselves (20 px). The real target is the whole label row, which is 44 px — clicking anywhere on the row toggles it |
| Text under 12 px | **None.** This forced PF15: the chart avatar's initials render at about 10 px today; 12 px fits inside the same 24 px circle |
| Script errors | **None**, including the Hindi and dark sweeps |
| Focus visible | 3 px outline on every control, both themes |
| Colour never the only signal | Every chip carries a word; the sensitive-document warning is a sentence, not a red row |
| Dark theme | Every screen, from the design-system dark tokens |
| **200 % text** | **Tested in v2, and it found four faults, all now fixed.** See below |

**200 % text — what it is and what it found.** Our tokens are in `px`, so "200 % text" on
this product means 200 % page zoom, which leaves **195 CSS px** of room on a 390 px phone.
v2 has a fourth device button for it, so you can see it too. Four real faults, none of
which showed at 390 or 360:

1. **My profile's picture card ran off the screen** — a 96 px avatar beside a column with a
   fixed 190 px minimum. The column now shrinks and wraps.
2. **The settings sections' count line ("3 of 18 · 7 readers") ran off the card** — it
   refused to wrap. It now wraps onto its own line on a phone.
3. **Long document type names pushed their row wide** — "Police verification
   acknowledgement". They break now.
4. **The documents card's status badge sat on top of the type name** — a flex row that did
   not wrap. **My automated check missed this one; only looking at the render caught it**,
   because it is an overlap, not an overflow. New checklist item.

**v3 added the three pickers and they passed at all three widths first time**, because the
rules that fixed the four faults above are the same rules the dialog is built on. One new
fault did appear and it was in the review scaffolding, not the design: a `position:fixed`
sheet is fixed to the **browser**, not to the phone frame, so on a wide window it filled the
window and hid behind the review bar. Every fixed layer in the prototype is now pinned to
the frame. Checklist item.

**The four drawer conditions (PF7)** are specification items, not prototype items, and they
are repeated in §11 so the analyst cannot miss them.

**The four drawer conditions (PF7)** are specification items, not prototype items, and they
are repeated in §11 so the analyst cannot miss them.

---

## 10 · Checks before handoff

**Nielsen, where it bites.**

- *Visibility of system status* — the chart's loading state is the chart itself; the save
  states say what is happening and what may have gone through.
- *Match with the real world* — "In the company since", not "Date of joining". "Bring on
  your first day", not "pending documents".
- *User control* — Escape closes the drawer and the expanded row; the joiner can go back
  at every step; "I will bring it on my first day" is always a valid answer.
- *Error prevention* — the settings card's whole design. The consequence is on the button.
- *Recognition over recall* — Preview shows the result instead of describing it.
- *Help users recover* — every failure says what is safe, what to do, and gives a code.

**Persona walkthroughs, steps to the outcome.**

| Persona · task | Today | After |
|---|---|---|
| Employee: put my face on my record | **Impossible** without Desk | 3 taps: account menu → My profile → Take a photo |
| Employee: fix my phone number | Message HR, wait | 4 taps |
| HR: who is this person in this seat, and since when | Positions → read the name → open Desk → find the Employee → read | 2 clicks: name → drawer |
| HR: decide what a reader may see | **Does not exist** | Settings → one section → tick → Save, with the consequence on the button |
| Joiner: give HR my details before day one | HR types them from paper | One link, five minutes, on their own phone |

**The frontline bar — can it be done in two minutes on a phone?** My profile: yes, measured
at 390 and 360 px, 48 px controls, 16 px fields, one primary action per card. The
pre-onboarding form: yes for the details; the documents step depends on signal, which is
why every upload has a third way out.

**Red-team.**

| What if | Answer |
|---|---|
| The person is brand new | My profile opens on the picture card with one primary button |
| An expert in a hurry | Nothing added to their path; the drawer opens on a click and closes on Escape |
| No data at all | The chart is today's chart; the details card says "Not given yet"; the documents section is absent, not empty |
| 100× the data | The chart's request count is governed by what is on screen, not by headcount. The mini profile is one call. ⚠ the 8 slots remain a Risk (§5.5) |
| The network drops mid-action | The photo upload says "may have gone through"; the joiner's answers stay on the phone; no failure discards typing |
| Not allowed to see something | The row is absent, not blank and not "hidden". The settings card is absent for a non-System-Manager |
| An AI feature | **There is none, and §8 refuses the obvious one** |
| They cannot recover | Every failure carries a code (POS-LOAD, POS-PROFILE) and a human route (ring HR on a real number) |

**Plain-language test.** Every sentence above is short, concrete and says who does what.
The two I would test with a real reader are the document-types warning and the joiner's
"What happens to it".

---

## 11 · What the business analyst must turn into acceptance criteria

1. A chart with no photos looks **exactly** as it does today — no placeholder shape, no
   message, no prompt.
2. A photo that fails to load falls back to initials **silently**; no broken-image icon,
   no retry request.
3. The default two-level view **fetches no photo that is off screen**. Assert the request
   count against the number of boxes in the viewport, not the number in the tree.
4. Nothing reflows when a photo arrives: the circle's rendered box is identical before and
   after.
5. `position_table` runs **the same number of queries for 20 seats as for 400**, with the
   photo included.
6. The mini profile is **its own call**, and the table payload carries no personal field
   beyond what it carries today.
7. The profile endpoint **refuses a field outside the allow-list even when posted directly**.
8. A document file is served **only** by our own endpoint, which checks the reader's access
   to that employee on this page **and** that the type is ticked. A direct
   `/private/files/…` request for a non-ticked type must be refused — and that test must be
   written against the **parent** Employee permission, because a child-table rule never
   reaches the file.
9. The drawer: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, Escape closes,
   focus moves in on open and **returns to the name that opened it** on close, close button
   44 × 44.
10. **"Change this seat" is a page, not a modal**, with its own address and a labelled
    "← Positions" link. The old `#pos-editor` backdrop is retired, not left beside it.
11. **The mini profile is one component with one caller interface.** A test must assert
    that the field list, the sentence under it and the documents section are **identical**
    in the Positions drawer and on the seat page — ideally by asserting there is only one
    place in the code that builds them. Two copies is a test failure, not a style note.
12. **The settings page shows the chosen fields and document types themselves**, not a count,
    and the picker dialog has `role="dialog"`, `aria-modal`, `aria-labelledby`, Escape to
    cancel, focus in on open and **back to the button that opened it** on close.
13. **OK saves.** After OK there is no unsaved state anywhere on the page, and the `Version`
    record is written at that moment. **Cancel writes nothing** — test it by cancelling a
    dialog in which every box was changed.
14. **The enlarged picture is fetched only when it is opened**, never with the drawer and
    never with the chart. Assert the chart and the table request nothing but 48 px copies.
15. **The photo is a `<button>` with a spoken name**, reachable by Tab, opened by Enter or
    Space, closed by Escape with focus returning to it — and it is **not a button when the
    person has no photo**.
16. **Escape closes the enlargement only.** A second Escape closes the drawer.
17. Nothing private prints: faces off on Ctrl+P, documents never, and 069's existing
    suppression still passes.
18. The settings card is **absent** for anyone who is not a System Manager, and every save
    writes a `Version` record naming the key, the old value and the new one.
19. An uploaded photo is **stored resized and converted**, and a PNG or HEIC upload carries
    no metadata afterwards. Guard: p95 stored size ≤ 50 KB, no stored original above 200 KB.
20. My profile with no linked Employee record shows S1-E, **not** a server failure.
21. A save that times out shows the "may have gone through" wording and does **not** clear
    what was typed. Test it with a call that succeeds on the server and loses its reply.
22. Every new string goes through `drT()` and has a Hindi entry.
23. **Parity with the prototype** (Surbhi, 21 Oct 2026): the spec carries a parity table,
    row per screen, and any difference from `prototype-v4.html` needs her yes first.

---

## 12 · The prototype

**v2:** `C:/Surbhi-Git/hrlocal-data/prototypes/078-positions-faces/prototype-v2.html`
**v1 is kept beside it** so the change can be seen rather than described.

Outside the repo, because it holds real PP Jewellers names and seats. One self-contained
HTML file, built on the design-system tokens, light and dark.

**I do not have an artifact tool in this run, so I could not publish it. The session that
ran me must publish it and give Surbhi the link.**

Controls along the top: **Screen** (7) · **Device** (1440 / 390 / 360 / **390 at 200 %
text**) · **Theme** · **Words** (English / हिंदी) · **Photos on file** (none — today / some
/ all) · **State** (per screen, 30 in all).

**What changed in v2, and where to look**

| # | Change | Where |
|---|---|---|
| 1 | **"Change this seat" is a page**, with a "← Positions" link, the seat, the people and the seat form | Screen 5, state *The page* |
| 2 | **The person's view there is the Positions mini profile** — same eleven details, same sentence, same Documents section | Screen 5, states *Open as a drawer* and *Open in place*; compare with screen 4, state *Mini profile* |
| 3 | **A fourth device: 390 px at 200 % text.** It found four faults, all fixed | Device bar |

**What changed in v3**

| # | Change | Where |
|---|---|---|
| 1 | **No more collapsible panels.** The page shows the chosen fields and document types as tags and rows; one button opens a dialog | Screen 6, state *The page* |
| 2 | **Three pickers**, full-screen sheets on a phone, grouped by category for the 18 document types | Screen 6, the three *Choosing:* states |
| 3 | **OK saves. There is no page Save** | Screen 6, state *Saved* |
| 4 | **The empty case and the tall case**, both drawn | States *No documents chosen* and *12 documents chosen* |
| 5 | **My one alternative, labelled as a proposal** (⚠ DECISION 11) | State *Remove on the tag (my proposal)* |

**What changed in v4**

| # | Change | Where |
|---|---|---|
| 1 | **The picture enlarges** on hover, tap or Enter — 240 px, inside the drawer, with the name under it | Screen 4, state *Photo enlarged*. Set *Photos on file* to *Some* or *All* first |
| 2 | **Its two unhappy states**: still arriving, and the full picture failed | States *Photo enlarged — still loading* and *— did not load* |
| 3 | **No photo means no button.** Switch *Photos on file* to *None* and the avatar is not a control | Screen 4 |

Everything else is unchanged.

**"Photos on file" is the control I would start from.** It is the three-slide answer to
"what does this look like on day one": *None* is today's chart, *Some* is a month in,
*All* is the end state.

**A "photo" in the prototype is a tinted disc marked "Sample photo", not a face.** Nobody at
PP Jewellers has a photograph, so drawing invented faces would be inventing data. Every
name, seat, branch and document type in it is real.

---

## 13 · Usability test plan — for the High-impact items

Two tests, five people each, 20 minutes.

**Test A — My profile, with frontline staff.** Five DTC or PPJ store employees on their own
phones, in Hindi if they prefer.

| Task | Success | What would change the design |
|---|---|---|
| Put a photo of yourself on your record | Done in under 2 minutes, unaided | If anyone hesitates at the privacy sentence, the sentence is wrong, not them |
| Change your mobile number | Done, and they can say who will see it | If they look for a "submit to HR" step, the no-approval decision needs revisiting |
| Change your password | Reaches the password page and gets back | If anyone stops at Frappe's screen or taps "Back to sign in", ⚠ DECISION 6 becomes a P2 |

**Test B — the settings card, with HR.** Five HR managers, laptop, no training.

| Task | Success | What would change the design |
|---|---|---|
| Decide which documents appear on the Positions page | They can say, unprompted, **who** will be able to open the ones they ticked | If they cannot name the audience, the count line has failed and needs to be bigger or repeated at Save |
| Before saving, say what a reader will see | They use **Preview**, not guesswork | If nobody presses Preview, move it next to the tick list, not next to Save |

**I have no user research behind any of this.** The claim that an owner recognises faces
faster than names across six stores is my judgement. The cheapest check is ten faces in
front of one owner for five minutes.

---

## 14 · ⚠ DECISIONS — yours, with my recommendation

| # | Decision | Context and conflict | Options | My recommendation | Owner | Risk if it waits |
|---|---|---|---|---|---|---|
| **1** | **How big is a face on a chart card?** | You asked for "full photos on the chart cards". The card today draws a 24 px circle | (a) 24 px circle, chart shape unchanged · (b) 40 px photo, every box ~48 px taller, fewer seats per screen, more wall-chart sheets | **(a) 24 px**, with the big picture in the mini profile one click away. Both are in the prototype | Surbhi | Blocks the CSS and the wall-chart paper sizes |
| **2** | **Faces on the printed wall chart?** | Recognising a manager may be the whole point; a customer walks past that wall | (a) never · (b) a tick, off by default, not remembered · (c) always | **(b)**. Ctrl+P stays off either way | Surbhi | Blocks the print rule and slice 069's dialog |
| **3** | **One extra mitigation on documents, or none?** | You decided all 18 types are offered and HR judges. The only thing missing is the employee's own view of it | (a) nothing more · (b) **one line on the employee's My profile documents card: "HR has chosen 3 of these to show on the organisation chart. [Which ones]"** — about an hour of work | **(b)**. It costs almost nothing and it is the difference between a policy and a secret. It does not narrow your decision in any way | Surbhi, with `hrms-security-privacy-engineer` | Nothing blocks; it gets harder to add later |
| **4** | **May an employee hide their own photo?** | Slice 076 set the precedent for birthdays. The brief recommends no opt-out; so do I | (a) no opt-out · (b) one checkbox in My profile | **(a) no opt-out**, because a patchy chart helps nobody. But the precedent exists and the DPO view may differ, so it is your call, not mine | Surbhi, with security | Blocks the privacy notice wording |
| **5** | **Pre-onboarding: our list on the settings card, or Frappe's Web Form builder?** | You asked for the settings card. Frappe's Web Form already is a configured public field list | Both drawn in the prototype, section 4 | **Frappe's builder**, and the card states the facts and links to it. Two pickers for one form will disagree, and the joiner is who finds out | Surbhi | Blocks the settings card's fourth section and the 079 scope |
| **6** | **The password page** | The link works and returns to the portal. But it is Frappe's screen, English only, with "Back to sign in" | (a) ship the link as the brief says · (b) link it **and** add the one line of copy "You will come back here afterwards" · (c) restyle the page, which is a slice of its own | **(b) now, (c) never in this slice.** Seen today, E3 | Surbhi | P3; it ships either way |
| **7** | **The "7 people can open the Positions page" figure** | It must come from the server, counting real enabled users with Read on `Alvoraa Position`. On this copy that is 5 accounts of which 3 are real people | — | Make the server count enabled users, and say "7 people" only when it means people | `hrms-business-analyst` | Blocks the settings card's copy |
| **8** | ⚠ **COMPLIANCE — the privacy-notice sentence**, before the first photo | Carried from the brief, still open | — | One sentence, as drafted in §8 | Surbhi with security | **Blocks switching the photo upload on at a tenant** |
| **9** | ⚠ **COMPLIANCE — the joiner's retention period** | Counsel's number, not ours. The form says 90 days as a placeholder | — | Do not build the form until counsel gives a number | Counsel via Surbhi | **Blocks the pre-onboarding form entirely** |
| **11** | **Documents: one click to stop showing a type, or the dialog both ways?** (new in v3, my proposal) | You invited a better idea. Adding a document type exposes something; removing one never does. Today both cost the same four actions | (a) **the dialog both ways**, one pattern across all four lists · (b) **"Stop showing this ✕" on the row**, with undo; adding still goes through the dialog and its warning | **(b), mildly.** Make the safe direction cheap and the risky one deliberate. But **consistency across the card is a good enough reason to refuse it**, and that is the strongest argument against | Surbhi | Nothing blocks; (a) is already built |
| **10** | **On the seat page, does a name open the drawer or open under the row?** (new in v2, **still open**) | You asked for the page and for the same view as Positions. Both are done. This is the only thing left, and the **content is identical either way** | (a) **the drawer**, same as Positions · (b) open in place, inset under the row | **(a) the drawer.** One behaviour for one job, the seat's form stays put, and it is one component rather than one component with two layouts. **(b)** wins only at comparing two people without closing anything — and it pushes the next person about 400 px down | Surbhi | Blocks the seat page's build; everything else about it is settled |

---

## 15 · Where I disagree, and what I could not check

**Two disagreements, both small, both already written as decisions rather than quietly built
differently.**

1. **One slice, four outcomes, and the order inside it still matters.** You chose one slice
   and I have designed one slice. But **My profile has to be built and switched on first
   within it**, because until photographs exist, every face in this design is an initial.
   If the build runs out of time, the thing to cut is the chart faces, not the photo upload.
2. **The pre-onboarding list on the settings card** (⚠ DECISION 5). I agree with the PM.
   I have drawn your version anyway so you can see both.

**Honest gaps.**

- **The chart, the seat tray and the "Change this seat" dialog were never rendered.** The
  local bench cannot load `position_table` (E1). Every layout claim about those three is
  read from `portal.js` and `panels.css`. **Somebody should open Positions on dev before
  this is built**, which is now a one-line job because the login works.
- ~~**200 % text was not tested.**~~ **Done in v2** — a fourth device, 630 renders, four
  faults found and fixed (§9). One of them, the overlapping status badge, my automated
  check missed entirely; only looking at the render caught it.
- **Hindi is a machine draft** throughout, as it has been since slice 008.
- **The ~30-faces-on-first-paint figure is an assumption** with a measured basis (55 boxes
  at two levels, a 1440 × 900 viewport). The engineer should measure the real count.
- **No competitor org-chart screenshot was viewed.** `01a` §5's labels stand.
- **Nothing here has been tested with a real user.**
- **No data was changed on the bench.** Reads and screenshots only.

---

## 16 · Subtract pass — what I deleted before handing this over

Read back once asking only *what can I remove and still meet the requirement?*

**Removed:**

- **A separate "photo" settings row.** The photo is always on; it is not a ticked field. One
  less control, one less state.
- **A photo moderation queue, a "photo received" notification, and a profile-completeness
  nudge on Home.** None asked for. HR can already clear a photo in Desk.
- **A second avatar component and a second drawer.** `ocAvatar` and `.emp-drawer` are
  reused exactly as they are.
- **Four separate settings cards.** Collapsed into one card with four sections, which is why
  the Organisation Settings page gains one card rather than four.
- **A per-row confirm dialog on a sensitive document tick.** It was my first idea and it is a
  nag. Replaced by the category chip, the red line, the summary and the consequence on the
  Save button — which say more and interrupt less.
- **A "hidden fields" explanation in the mini profile.** A row a reader may not see is now
  simply absent; a label saying something is hidden tells them it exists.
- **An audit log screen for profile opens.** The drawer says "Opening one is recorded";
  reading that log is Desk's job, not a new page.
- **A progress tracker, a login and a chase reminder for the joiner.** One form, once.
- **A fourth "photos" state in the prototype** (half-loaded per person). Two states —
  arriving and failed — cover everything the design has to answer.

**Removed in v2, and this is the largest subtraction in the whole design:**

- **The second version of the mini profile.** v1 had a five-field inline view on the seat
  dialog and an eleven-field view in the drawer. Surbhi asked for one view; that turns two
  things into one — one field list, one set of words, one documents section, one set of
  states, one place to change it. **It is less to build, not more**, and it removes a whole
  class of future bug: the two drifting apart.
- **The modal wrapper around "Change this seat."** The page replaces it; the backdrop,
  its focus trap and its ✕ all go.
- **The reason for "expand in place."** v1 expanded the row only because a drawer over a
  dialog would have stacked two focus traps. On a page that reason is gone, so "expand in
  place" survives only as an option you may prefer (⚠ DECISION 10), not as a workaround.
- **One fixed minimum width, one `white-space:nowrap` and two non-wrapping rows**, all
  found by the 200 % test. Each was a small rule doing more harm than good.

**Removed in v3:**

- **Four collapsible panels and the open/closed state each one carried.** A panel is a
  control that hides the answer; the page now simply holds the answer.
- **The page-level Save button**, and with it every unsaved state on the screen. OK saves.
- **The counts as the page's content** ("11 of 11", "3 of 18"). A count is what you write
  when you have decided not to show the thing itself.
- **"Preview what a reader sees" as a page button.** It moved into the dialog, where it can
  show what is ticked *now*, before OK — which is the only moment it is useful.
- **My own first instinct, "let HR tick whole categories instead of 18 types."** Rejected
  before it was drawn: it is a narrowing of your decision that nobody asked for.

**Removed in v4 — all of it from the enlarged picture, which arrived wanting more than it needed:**

- **A second stored image size.** Not needed: the upload hook already keeps a bounded JPEG,
  and 512 px covers a 240 px square on a 2× screen. Nothing new at rest.
- **A lightbox over everything.** The enlargement lives inside the drawer, so there is never
  a third stacked layer and Escape keeps one meaning.
- **A spinner.** The 48 px copy blurred at full size is the loading state, for free.
- **A retry on the failed picture**, a zoom-and-pan control, a download, an "open in new tab",
  a next/previous between people in the seat, and the same enlargement on My profile. None
  was asked for; each would be a control for a problem nobody has.

**Kept, with the measured reason:** the **48 px copy made once at upload** (§5 measure 4).
165 full-size originals against a 2.5 s / 3G budget is two orders of magnitude out, which is
exactly the kind of number `no-over-engineering.md` §5 asks for before an extra is allowed.

---

## 17 · v5, 31 Oct 2026 — "must fill in", one list ticked twice, and a document that never walls anybody

**What this supersedes.** §6.5.3's list of four (there are now five), §6.5.5 (the two ways of
choosing the joiner's fields — settled), and §6.6's fixed six screens. §6.5.1, §6.5.2,
§6.5.4 and §6.5.6 stand: the button → dialog → tags pattern you approved is what all of this
is built inside, and nothing here replaces it. §5, §6.1–§6.4 and §8–§10 are untouched.

**The headline.** HR can now mark a detail or a document **must fill in**. It is a second
tick inside the picker you already approved, and it only exists on a row that is already
ticked, so an impossible setting cannot be made and nothing is greyed out. **The part worth
your time is not the tick. It is the two places a required thing can trap somebody** — an
employee who cannot save their own record (§17.5, ⚠ DECISION 14, the one I want you to look
at first) and a joiner standing on a factory floor whose PAN card is at home (§17.6, now
settled as a requirement).

### 17.1 Three corrections arrived while I was drawing. All three made it smaller

| What I started with | What you decided | Effect on the design |
|---|---|---|
| Three pickers get a required tick, including one for the joiner's fields | There was no joiner field picker — the seven were a closed constant | No control built for a list that did not exist |
| The joiner form asks **the My Profile list**, so a tick could put PAN on a public page | **One candidate list, ticked twice** — once for My profile, once for the joiner form. The joiner's **ships empty** | The accident I was designing against **cannot happen**. Two selections, two warnings, no "careful, this also goes public" |
| Design for a long, possibly statutory joiner form | **No official number is ever typed on the public form.** A photograph of the card is enough | The sensitive screen, the extra confirm and the heavy pagination scheme all deleted |

**Three-persona check.** **Employee:** meets a required field on My profile — §17.5.
**HR Manager:** can insist, and can see at a glance what is compulsory and what is public.
**CXO:** nothing changes.

### 17.2 The control: a second tick that only exists on a ticked row

**Rung 3 — a second state on a control that is already there.** No new component.

```
[✓] Full name                                      ← the tick you already approved
      asked on a public page, before they work here  ← who sees it: a fact, not a control
      [✓] Must fill in                               ← appears only once the row is ticked
```

- **A detail cannot be compulsory unless it is asked for**, so the required tick is not
  rendered until the row is ticked. The impossible combination cannot be made, and nothing
  is greyed out — a greyed control is on our anti-pattern list three times.
- Unticking a row takes its "must fill in" with it, and the dialog says so in one line.
- **Measured 44 px on a phone** (390, 360 and 195 px wide), `aria-label="Must fill in — Full
  name"` so a screen-reader user never hears "Must fill in" six times with nothing attached.

**Rejected:** *two always-visible columns with "required" auto-ticking "shown"* — one tap
cheaper, but it doubles the furniture on 18 document rows and on the Positions picker, where
required has no meaning at all. *A three-way segmented control* — a new component for a
two-state problem. *Tapping the tag on the main screen* — the main screen is the answer, not
the editor, and that distinction is the whole point of the pattern you approved.

### 17.3 Where a required tick bites — said on the screen, list by list

| List | Feeds | What "must fill in" does there |
|---|---|---|
| **What an employee may change** | My profile (signed in) | ⚠ DECISION 14 — §17.5 |
| **What a new joiner is asked for** | The public form, `/pre-onboarding` | Stops the form being sent with it blank. Named in the refusal; link keeps working |
| **Document types** | A person's Positions card **and** the joiner's uploads | **The joiner form only, and it never stops them sending** — §17.6. On Positions the file is only displayed, so there is nobody to require anything of |
| **Positions fields** | The Positions card | **Nothing.** No tick exists, and the dialog says why |

The fourth row matters: *"Nothing here can be made compulsory. This page only shows what is
already on the record, so there is nobody to ask."* Hide what a person cannot use, and say
why once.

### 17.4 The settings card: five lists, and the public one looks public

**One candidate list of details, ticked twice**, is why the card now has five sections rather
than four. It costs one more card and buys the thing that was most likely to go wrong: an HR
person helping employees fix their own details **cannot** put a field on a public page as a
side effect, because that is a different tick, in a different dialog, with a different
warning.

**Tags, grouped by name rather than marked by symbol.** The chips stay; they gain headings:

> **MUST FILL IN (3)** `Full name` `Mobile number` `Emergency contact phone`
> **THEY CAN LEAVE THESE BLANK (4)** `Personal email` `Current address` `Emergency contact name` `Relation`
> **HR KEEPS THESE — SHOWN TO THE EMPLOYEE, NOT EDITABLE (2)** `Bank account number` `IFSC code`

Words, not colour and not an asterisk; the count is in the heading, so no extra sentence is
needed; and it reads the same at three chosen and at twelve. On the document list, which is
rows rather than chips, required is a **`Must answer` chip in the row** — the row already
carries chips, so nothing new is introduced. Two shapes, because the two lists already had
two shapes.

**The public list says so, in red, above its tags:**

> **This list is public.** Whatever you tick is asked of anybody holding the link, including
> somebody it was forwarded to. Ask only what you need before their first day.
> [ See what a joiner is asked ]

and, immediately under it, the sentence that closes the statutory question for good:

> **Official numbers are not on this list at all.** PAN, Aadhaar, provident fund and bank
> details can never be typed into the public form. Where you need one, ask for a
> **photograph of the card** in the documents list below — the number is never read as data.

**The empty state is the shipped state, and it reads as a fact, not a gap.** The joiner list
starts empty:

> Nothing is asked. A joiner who opens the link is asked for documents and a photograph only.
> That is the starting setting, and it is the safe one.

No "add your first", no empty-state picture, no nudge. It is a prototype state of its own
("The joiner list on day one — nothing ticked") so you can see the day-one screen.

**One small thing to settle.** You asked that the joiner's **name ship ticked as required**,
and you have since asked that the list **ship empty**. I have taken the empty list as the
newer answer, and reconciled the two like this: *the saved list is empty; the picker opens
with Full name pre-ticked and marked must-fill-in*, so an HR person who opens it and presses
OK gets a safe, sensible minimum, and nothing is public until somebody acts. One line to
change if you meant the other thing.

**I removed a per-row confirm in v3 as a nag; I briefly added one back when the lists were
merged, and this decision deleted it again.** With two separate ticks and no statutory field
on the public form, the standing red block is proportionate and a confirm would be a nag.
Said out loud so the reversal is visible rather than quiet.

### 17.5 My Profile's refusal — the judgement you asked for

**My recommendation: do not block the save. Save what is valid and keep asking.** Both are
built so you can click one against the other (`1 · My profile`, the two "Something needed"
states). ⚠ **DECISION 14** — and this is the one place where a setting can lock an employee
out of their own record.

The case, from the real record: Nandini has no mobile number, no address and no emergency
phone on file. HR marks all three must-fill-in. She comes to the page to **change her mobile
number** — exactly what the page is for.

**(A) Block the save — what you chose.** Drawn as well as it can be drawn: the server's own
words, everything she typed kept, each missing one named and tappable, the Save button never
greyed (so pressing it moves focus to the error rather than doing nothing), each field marked
`Needed`, each refused field with a red 2 px edge **and** a sentence, and a closing line
naming who can take a field off the list.

> **We could not save your details.** PP Jewellers needs these 3 before anything on this page
> can be saved: · **Mobile number** · **Current address** · **Emergency contact phone**
> Everything you typed is still here, and nothing has been saved yet. Fill these in and press
> Save again.
> *If you cannot give one of these, ring HR on 0172 450 1180 and ask them to take it off the list.*

**What it costs, plainly.** An employee who cannot supply a required field — no permanent
address, nobody to name in an emergency — **can never change anything on this page again**.
Their only way out is a phone call to HR. That is the call this product exists to remove, and
it is a one-way-rule problem: HR's completeness is bought with the employee's ability to
correct their own record. **P2, and it is a trap rather than an obstacle however well the
screen is written.**

**(B) Save what is valid, keep asking — my proposal.** The save goes through. A standing
amber block at the top names what is still needed, every time she opens the page, and each
field keeps its `Needed` mark until it is filled.

> **Saved.** Your new mobile number is on your record.
> **PP Jewellers still needs 3 things from you:** Mobile number, Current address and Emergency
> contact phone. They are marked **Needed** below. You can change anything else on this page in
> the meantime — this will keep asking until they are filled in.

**What (B) costs you:** completeness on My profile is chased, not guaranteed, and HR needs a
list of who is still missing what — which is a report over the same ticked fields, not a new
screen. **What it buys:** nobody is locked out of their own record, and the support call does
not happen.

**Blocking still holds where it belongs — the joiner form** — because a joiner is sending
something once, as a stranger, before anything exists, while an employee is maintaining a
record they live in. Same word, two situations, and only one of them can take a hostage. I
would not call (B) weaker enforcement; it is enforcement that cannot trap anybody.

**If you keep (A):** one narrowing removes the worst case for little work — let HR record
that a particular person genuinely cannot supply a field, and treat it as satisfied for them.
That is a conversation with the analyst, not a screen, and I would still rather you took (B).

### 17.6 The joiner's refusal, and the document they have not got

**Two things are requirements now, not good manners, and the design is built on both:** the
refusal is the **server's own words** (the browser decides nothing, so the two can never
disagree), and **a refused send never burns the link**.

**The centre of the flow: a compulsory document must be *answered*, never *had*.** Every
compulsory type has **two answers, both one tap, and both send the form**: a photograph now,
or *"I will bring it on my first day"*. So:

- The documents screen says it before anything goes wrong: *"If you have not got one with
  you, say so and carry on — **you can still send this form today**."*
- Choosing the promise shows what it did: a green `You are bringing it on your first day`
  chip, *"Told PP Jewellers HR. It is on the list on your last screen… You can still send a
  photograph later on this same link, until 7 November."*, and **the promise button
  disappears**, because it is the answer already given.
- What "compulsory" still buys HR: **it cannot be ignored.** Tap neither and the send is
  refused and names it — and **the refusal offers the promise in place**, so the way out is
  inside the message.
- The "Sent" screen repeats it: *"Bring on your first day: your PAN card. You told us you
  would bring it, and HR has that on their list."*

**Why the rule splits between answers and documents:** a compulsory *answer* is in the
person's head, so asking is fair. A compulsory *document* is a piece of paper somewhere else
— a wall there punishes people who fully intend to comply, and it falls hardest on exactly
the joiner this product is for. HR gets the paper a day later either way, and gets the rest
of the form today instead of nothing.

**The refusal itself.** On a form of six screens or more, "something is missing" is a maze,
so every missing item is a **tap, not a hunt** — each line goes to the screen holding that
answer, with the field marked and focused.

> **We could not send your form. 3 answers are still needed.**
> · **Full name** — *on About you*
> · **Emergency contact phone** — *on In an emergency*
> · **PAN card** — *send a photograph, or say you will bring it on your first day*
> **Nothing has been sent, and your link still works.** Tap any of them to go straight to it.
> Everything else you typed is safe on this phone.
> [ I will bring the PAN card on my first day ]

The refusal is the backstop, not the mechanism: required details carry a `Needed` chip on
their own screen, and each group screen opens with *"Anything marked **Needed** has to be
filled in before you can send the form. You can leave the rest blank."* **Next is never
blocked mid-form** — a joiner may legitimately come back for an answer later, and blocking
each step turns a six-screen form into six walls.

### 17.7 A form for a list nobody has written yet

HR decides the list, so the screens cannot be drawn in advance. **The rule, and it is the
whole rule:**

> **One screen per group, in the order the details sit on the record. A group of more than 8
> questions splits into pages of 8.**

At PP Jewellers' ticks that is *About you · Where you live · In an emergency · Your documents
· A photograph of you · Check and send* — six steps for seven questions. The prototype also
draws the heavy case (the state "Many fields — how the form paces them"), where one group has
split and says so rather than renaming itself.

**The old "1 · 2 · 3 · 4" step line is replaced by a step list.** That line was drawn for
four fixed steps; at eight it wraps onto three rows on a 360 px phone. A list of named steps
costs one line each, says how much is left — the question a joiner on a slow phone actually
has — and does not break as the list grows. "Check and send" is grouped the same way.

**This got smaller on 31 Oct, and the design says so rather than keeping the scaffolding
quietly.** With no official numbers typed and an empty starting list, the realistic case is a
handful of ordinary questions. I kept the rule because the list is still HR's — not because
I expect twenty. **I did not build grouping configuration, a progress bar, or a save-and-
resume scheme.**

**⚠ DECISION 15, worth seeing now rather than after the build.** If HR ever does tick twenty,
the honest answer is not more screens — it is letting a joiner **send what they have and come
back on the same link**. Not built, not drawn beyond the note; say the word and it is a small
change (the submission stays editable until the link expires) rather than a redesign.

### 17.8 Accessibility, privacy and the states drawn

- **Measured, not eyeballed** (Chrome, 31 Oct 2026; every new state at 1440, 390, 360 and
  195 px, light and dark): **nothing wider than the app, no sideways scroll, no text under
  12 px, no button or link under 44 px.** The required sub-row label measures exactly 44 px
  on a phone.
- Every refusal is `role="alert"`; every confirmation is `role="status"`; a missing required
  field carries `aria-required`, and when refused `aria-invalid`, a red 2 px edge **and** a
  sentence — colour is never the only signal.
- Escape closes a picker and changes nothing; OK saves, so there is never an unsaved state to
  lose (§6.5.2 unchanged).
- **Privacy.** Required raises collection, so it is named where it is set. The joiner list
  carries a standing "this list is public" block; the document dialog says a compulsory type
  is asked of every joiner. The card keeps its System Manager-only, versioned,
  refusal-logged behaviour (078-SEC-5) — **the required tick adds no new permission
  surface**. HR-only fields are excluded from the public list entirely, and in My profile
  they are **shown as text, not as a box** that would be refused.
- **New states drawn:** the required tick on a ticked row · three grouped tag lists · the
  joiner list on day one, empty · My profile blocked · My profile saved and still asking ·
  a joiner group screen · the documents screen · the promised document · the refused send
  with tappable items · the step list at a heavy configuration.

### 17.9 What the business analyst must turn into acceptance criteria (added to §11)

1. A detail or document type **cannot be marked required unless it is ticked**; unticking
   clears required. The UI makes the invalid state unreachable; the server refuses it anyway.
2. **The joiner's field selection and My profile's field selection are two settings over one
   candidate list.** Changing one must not change the other. Negative criterion.
3. **The joiner's selection ships empty.** A tenant that has never configured it asks for
   documents and a photograph only.
4. **No field marked HR-only, and no official-number field (PAN, Aadhaar, UAN, bank), is ever
   offered on the joiner picker or accepted by the joiner form.** Negative criterion, and the
   server enforces it whatever is stored.
5. Required on a **detail** blocks the joiner's send and is named in the refusal. Required on
   a **document** must be **answered** — a file **or** an explicit "bringing it on my first
   day" — and **may never block the send on the absence of a file**.
6. A refused send **does not consume the link** (AC-110b holds) and returns the **server's**
   list of missing items; the client renders only what it was given.
7. A refused My profile save keeps every typed value and names every missing field — **or, if
   DECISION 14 goes to (B), the save succeeds and the page keeps asking.** Mutually
   exclusive; the analyst must write one, not both.
8. The joiner form renders **one screen per field group, splitting a group over 8 fields**,
   and the step list is generated, not hard-coded.
9. HR sees, per submission, which answer was given for each compulsory document, and the
   promised ones appear on a day-one list.

### 17.10 Subtract pass — what I deleted on this pass

- **A joiner field picker of its own invention**, then **a merged single list**, then **a
  per-tick public confirm** — all three were real work that three decisions removed. Deleted
  rather than kept "in case".
- **The "our own list vs Frappe's Web Form" toggle and its two prototype states.** The field
  source is settled; only the build mechanism (DECISION 5) is open, and that is one sentence.
- **The sensitive-field screen on the joiner form**, with its own explanation of why a PAN is
  asked for — no statutory field can be typed there any more.
- **The "HR-only fields went public" state.** Decided; the alternative is not drawn.
- **The hard version of the compulsory document** (no promise, come back with the card). You
  settled it the other way, so only one behaviour is drawn.
- **A "required" badge on every chip.** Two group headings instead, which carry the count.
- **A progress bar**, and **blocking Next at the end of each group**.
- **A per-document choice of hard or soft.** One product rule, decided once.
- **Four primary buttons on the documents screen.** "Take a photo" is first but no longer
  purple; only **Next** is primary, so the screen has one main action.
- **The repeated "I will bring it" button after the promise is given.** No button where no
  action would work.

**Nothing was kept on a "we will need it later" argument.** The only thing I kept against my
own subtract instinct is the group-splitting rule, and the reason is named in §17.7: the list
belongs to HR, not to us.

### 17.11 Prototype v5

`C:/Surbhi-Git/hrlocal-data/prototypes/078-positions-faces/prototype-v5.html` — built from
v4, **with v4's hover-to-enlarge code kept exactly as it is**. Every v4 screen and state still
works (all 60 screen/state/device combinations render clean). v1–v4 are kept beside it. Not
published by me — the session that ran me publishes it.

**Four things to look at, in this order:**

1. `1 · My profile` → **Something needed — block the save** against **— save what is valid**.
   This is ⚠ DECISION 14 and the only place a setting can lock an employee out.
2. `7 · The joiner's form` → **A document you have not got**, then **Send refused**. The
   factory-floor case, and the two requirements that must never break.
3. `6 · Organisation settings` → **The page** — five lists, the red public block, the grouped
   tags — then **Choosing: what a joiner is asked**.
4. `6` → **The joiner list on day one — nothing ticked**. What every tenant gets before HR
   touches anything.

**One prototype, not two.** The extra scope shrank rather than grew, and the settings screen
and the joiner form are the same decision seen from two ends: what HR ticks *is* what a
stranger is asked. Splitting them would hide the connection the screen exists to show.

### 17.12 Open items

| Item | Owner | Blocks |
|---|---|---|
| ⚠ **DECISION 14** — block the save on My profile, or save what is valid and keep asking. **Look at this first** | Surbhi | The My profile acceptance criteria; they are mutually exclusive |
| ⚠ **DECISION 15** — may a joiner send part of a long form and come back on the same link? | Surbhi | Nothing today; it gets harder once the form is built |
| **The joiner picker's starting tick** — list ships empty, picker opens with Full name pre-ticked and required (§17.4). One line either way | Surbhi | The default fixture |
| ⚠ **COMPLIANCE** — the security engineer is writing the replacement for the privacy cap that the earlier wider list removed. Even with no statutory field typed, **a public page collecting name, address and emergency contact is a DPDP question before it is a design one** | `hrms-security-privacy-engineer`, then Surbhi | Switching the joiner form on at a tenant |
| The candidate field list in the prototype is **mine, not measured** — 16 rows chosen to show the shapes that matter (ordinary, HR-only, official number). The real list is whatever the Employee doctype and field rights allow. `[ASSUMPTION]` | Analyst, with the engineer | The real counts on the card |
| Nothing in v5 was seen on the local site — the joiner form does not exist yet. The measurements are of the prototype in Chrome | — | Nothing; the flows are new |
| Hindi: the new strings are **not** translated. The existing machine drafts cover v4's wording only | Surbhi, or a native reviewer | Showing Hindi for this part |
