---
slice: 078-positions-faces
artifact: 01a-ux-opportunities.md
author: hrms-ux-designer (opportunities scan)
date: 2026-10-31
status: evidence for the PM's brief. I recommend; Surbhi decides. No prototype at this stage.
inputs: [ux-learnings.md, product-context.md §2 §5 §6, nfr-budget.md §1 §2 §5 §7, no-over-engineering.md, docs/product/design-benchmark/2026-10-24-ux-priorities.md, docs/slices/064-organogram-improvements/, 065 (05-implementation-notes), 069, 070 (01a/01b), 071, 072, portal.js, register.py, api.py, settings.py, plans.py, employee_field_rights.py, employee_documents.py, panels.css, PPJ local copy (read-only queries, 31 Oct 2026)]
---

# 078 · Faces and a mini profile on Positions — UX opportunities

**The headline, first, because it changes the whole slice.**

**Nobody at the only tenant we have has a photo.** On the PPJ local copy, **0 of 403
active employees** have an `image` on their Employee record (measured 31 Oct 2026). The
chart's card already draws a real photo when one exists. So if we build exactly what was
asked, the hierarchy and the table will look **identical** the day it ships, at every
tenant, until somebody collects 403 photographs. The photo-collection question is not a
detail of this slice — it is the slice.

Second headline: **most of this is already there.** The card that draws the hierarchy
already renders `<img class="av">` when the person has an image (`ocAvatar`,
`portal.js:276`), the CSS is already a 24 px circle with `object-fit:cover`, and the
Organisation page's own endpoint already sends `image`. Only the Positions page's own
feed drops it. The mini profile has an existing drawer to live in. The setup screen has
an existing settings page to live on.

Third headline, and the one I would push back on: **the documents half of this slice
should not ship.** Fifteen of PPJ's eighteen Employee Document Types are identity,
statutory, financial or background-check documents — PAN card, Aadhaar card, bank account
proof, police verification, background verification report, last three months' salary
slips. A structure page is the wrong place for any of them. My reasoning and the smallest
safe version are in §7.

---

## 1 · Frame

**Who, when, where.** An owner or HR person, on a laptop, looking at a 120-seat chart
they did not draw, trying to recognise the person in a seat and answer one question about
them without leaving the page. At DTC the same page is held by the owners through a role
of their own, so "who sees this" is a tenant setting, not a fixed audience.

**Personas in scope:** CXO / founder (primary), HR Manager (primary, and the only one who
configures it), line manager (only where the tenant has opened the page to them).

**Deliberately out of scope:** the employee and the frontline worker **do not open this
page** — they get the Organisation page, bounded by `alvoraa_org_reach_up/down`. They are
in this slice only as the people whose faces and details appear on it. That asymmetry is
the one-way rule (product-context §2) and §6 below takes it seriously.

---

## 2 · Current state — read from code and the real data, not from a browser

**I could not take screenshots.** The local bench is up (`hrlocal-bench`,
`ppj.localhost`), and I ran read-only queries through standard input. I do not have a
demo login password, and looking for one was refused by the sandbox. Every layout number
below is measured from the CSS and the JavaScript, not from a render. **Before the design
step, somebody with a login should capture Positions at 1440 × 900 and 390 × 844** and
put the images in `C:/Surbhi-Git/hrlocal-data/ux-review/<date>/`. This is the fourth slice
in a row to carry that gap (slices 013, 059, 070), and it is listed again in §11.

### 2.1 Measured facts from the PPJ copy, 31 Oct 2026

| What | Number | Why it matters here |
|---|---|---|
| Active employees | 403 | |
| **Active employees with a photo** | **0** | F1. The feature ships invisible |
| Seats | 120, across 6 branches | |
| Seat assignments | 403 | |
| Seats by depth from the root | 1 · 15 · 39 · 40 · 25 | Default view opens two levels = **55 boxes** |
| Faces on first paint of the default view | **up to 165** (55 boxes × 3 names shown) | `POS_NAMES_SHOWN = 3` |
| Faces if somebody expands everything | up to 360 | |
| Rows in the table, unpaginated | 120 (`limit_page_length=0`) | Faces there would be **up to 360 images in one go** |
| Biggest seat | Sales Executive, Noida Sector 18 — **25 people** | The "+22 more here" case |
| Employee Document Types | 18 | §7 |
| Employee Document rows | 6,469 — of which **6,468 are "Expired"** and **0 have a file attached** | A document list is empty-with-red-badges today |

### 2.2 What the code already does (Fact, read 31 Oct 2026)

| ID | Fact | Where |
|---|---|---|
| F2 | The hierarchy card **already draws a real photo** when the person object carries `image`, and falls back to two initials. `.oc-who .av` is already `24 × 24`, round, `object-fit:cover` | `portal.js:276` `ocAvatar()`; `panels.css:2141` |
| F3 | The **Organisation** page already sends `image` for every occupant | `api.py:177` in `_people_in` |
| F4 | The **Positions** page does not. `register.position_table` builds its `people` list without `image`, and `posOne()` copies only name, weight, cover and note | `register.py:313`; `portal.js:806` |
| F5 | The assignment query already joins the Employee table through link fields (`employee.reports_to`, `employee.status`). Adding `employee.image as image` costs **no extra statement** | `register.py:303` |
| F6 | **The chart card is one `<button>`.** The code records what happened last time something clickable went inside it: *"a button nested in a button is invalid HTML, so Chrome closed the card early and every Change button floated below its own card"* | `portal.js:376` |
| F7 | Zoom is **0.4 to 2.0** in 0.1 steps, applied as CSS `zoom` on one wrapper | `POS_ZMIN/POS_ZMAX`, `portal.js:1597` |
| F8 | On a phone (≤ 640 px) the tree becomes a **vertical stack**, and the zoom buttons are 44 px. Slice 070's work | `panels.css:2252` |
| F9 | `.emp-drawer` already exists: 480 px, slides in from the right, `max-width:100vw` so it is **full screen on a 360 px phone**. Already reused by the payslip, the employee scorecard and goals | `panels.css:543` |
| F10 | `#emp-drawer` has **no `role="dialog"`, no `aria-modal`, no Escape, no focus move**. The payslip drawer beside it has the first two | `drawers.html:111` |
| F11 | Who may open Positions is **Frappe's Read on `Alvoraa Position`** — a tenant choice in Role Permissions Manager — and reading is scoped to the reader's companies and, if they are tied to a store, their branches | `register.py:70` `may_view()` |
| F12 | `employee_field_rights.py` locks **write** on 22 job fields (level 2) and 13 bank/statutory/salary fields (level 1), and deliberately leaves **read open to every role that reads Employee**. A field allow-list therefore **cannot** lean on Frappe's permission levels for read protection | `employee_field_rights.py:12` |
| F13 | `Employee Document` is a **child table on Employee**. The repo's own lesson of 30 Oct 2026: `has_permission` on a child table is always False — guard on the parent | `alvoraa_employee_documents/setup.py`; memory note |
| F14 | Document files are uploaded **private** (`is_private: 1`) and attached to Employee. The employee's own list already exists in My profile with a status badge and a "View" link | `portal.js:4744` `loadMyDocuments()` |
| F15 | Documents are a **plan feature**: `plan_employee_documents` | `subscription.py:200` |
| F16 | Org structure settings live in **Global Defaults**, with a `LABELS` table ready for a screen to render, and `get_cover_settings` / `set_cover_setting` already whitelisted. **No screen calls them today** | `settings.py` |
| F17 | **Org Settings** is an existing portal page with ten cards in a settled pattern: header, meta line, checkbox, hint | `org-settings.html` |
| F18 | Slice 065's privacy gate on this page: a `.private` / `data-private` class, a session-only "Hide replacement plans (before you share your screen)" link that is never remembered, and a print rule that strips every private element | `portal.js:2923`; `panels.css` print block |
| F19 | Slice 069's print rule already strips flags, tags and the notice-period column from any print of this page | `panels.css` `@media print` |
| F20 | There is **no image resizing anywhere in this repo** for employee photos, and no `loading="lazy"` on any portal image | grep, 31 Oct 2026 |

### 2.3 Keep — do not undo these

- The phone stack and 44 px zoom buttons from slice 070 (F8).
- The 3-names-then-a-count rule. One seat holds 25 people; the learnings already record
  that a cell joining 25 names with a line break wrecks the chart.
- Two levels open by default (Surbhi, 16 Oct 2026: "keep it collapsed. after two levels").
- One renderer for both charts (F2). The code says the Positions page had its own
  renderer for a few hours and "it read as a list".
- The 065 screen-share control and the 069 print suppression.

---

## 3 · The three things you asked me about

### 3.1 Initials as the fallback — keep them, and keep them as the only fallback

**Recommendation.** Yes, keep initials. Never a grey silhouette, never a camera icon,
never an empty circle.

Reasons, in order:

1. **It is today's chart.** With 0 photos on file, initials are what everyone sees now.
   Keeping them means the chart degrades to exactly what works today, person by person,
   rather than filling with 403 identical placeholder shapes.
2. **It is free weight.** Two letters are text; a silhouette is another request.
   `2026-10-24-ux-priorities.md` already rejects "stock photos and illustrations" for
   this tenant on exactly this ground.
3. **It is honest.** A placeholder face says "this person has no photo" in the least
   useful way possible. Initials say who the person is.

One change worth making with it: the initials circle and the photo must be **the same
size and the same shape**, so a row of three does not jump when one of them has a photo.
`ocAvatar` already does this (`<span class="av">` and `<img class="av">` share the class).
Fact, no work needed.

### 3.2 A 400-seat chart when most cards gain a real image

**The numbers (Fact, measured).** At PPJ's 120 seats the default view is 55 boxes and up
to **165** faces on first paint; fully expanded, up to **360**. Scale that to 400 seats
and the fully-expanded chart is up to **1,200** faces. The NFR budget is ≤ 1.5 s on
broadband and **≤ 2.5 s on a 3G phone profile, with a skeleton inside 300 ms**
(`nfr-budget.md` §2).

There is **no thumbnail anywhere in this repo** (F20), so whatever HR uploads is what the
browser downloads into a 24 px circle. A phone photo is commonly 1.5–3 MB. 165 × 2 MB is
about 330 MB for a chart that needs about 3 KB per face.

**What I would do, cheapest first:**

| # | Measure | Cost | Effect |
|---|---|---|---|
| 1 | `loading="lazy"` plus explicit `width="24" height="24"` and `decoding="async"` on the photo | one attribute each, no new code | Only the faces actually on screen are fetched, and nothing reflows as they arrive |
| 2 | **No faces in the table** (§4.2) | a decision, not code | Removes the 360-image page outright |
| 3 | A **48 px square copy made once, at the moment a photo is collected**, and that copy is what the chart asks for | real work, and the only item here I would call new code | Turns ~2 MB per face into ~3 KB. This is the measured exception `no-over-engineering.md` §5 allows: 165 × original misses the 2.5 s budget by two orders of magnitude |
| 4 | Faces **off in print** by default (⚠ DECISION 4) | one print rule, beside 069's | A wall chart does not carry 55 faces past a customer, and does not need 55 images at print resolution |

**What I would not do:** a cache, a background job, a sprite sheet, a CDN, or a
"photo service". The banned list in `no-over-engineering.md` §2 covers all of them and
none is needed once items 1–3 are in.

### 3.3 The 60 %-zoom click target — no, and here is what instead

**Recommendation: do not tie a click target to the zoom level.** Three reasons, and the
second one is a hard stop.

1. **At 60 % the name is already too small to be a target.** A 24 px avatar becomes
   14 px and 13 px name text becomes about 8 px. Our own floors are nothing under 12 px
   of text, 24 px targets on a mouse and 44 px on a phone (`nfr-budget.md` §7, learnings
   P4). So the very threshold proposed is **below every floor we have**. The rule would
   switch the feature on at the exact point it stops being usable.
2. **The hierarchy card is a single `<button>` (F6), and the code already paid for
   finding that out.** A link or a button inside it is invalid HTML and Chrome breaks the
   card. So "make the name clickable inside a chart card" is not a small change — it is a
   restructure of the one card both charts share.
3. **A target that appears and disappears teaches people the page is broken.** Our own
   principle is "hide what a person cannot use" and the anti-pattern list already carries
   "greyed-out tabs a person cannot open", seen three times. A name that is clickable at
   70 % and dead at 50 %, with nothing saying why, is the same fault with a worse tell.

**What I recommend instead — the same outcome, no zoom rule, no invalid markup:**

| Entry point you asked for | My recommendation | Cost |
|---|---|---|
| **The table** | Each name in "Who is in it" becomes a real link. A table cell is ordinary markup, so this is safe, and the row already gives it height | Smallest possible |
| **The "Change this seat" dialog** | Each name in the "WHO IS IN IT" list becomes a link, beside the existing "Take out" button | Smallest possible |
| **The hierarchy** | Clicking the card **already** opens the seat, and the seat tray already lists **every** occupant, not just three. Make the names there the link. One extra tap, no zoom rule, and it is the only surface that can hold the 25-person seat anyway | Smallest possible |

That gives two of your three entry points natively and the third in one more tap, at
every zoom level and on a phone.

**If you want it straight off a chart card anyway (option B), here is the honest price.**
Split the card: the title and subtitle stay a button, and each person's row becomes its
own button underneath it inside one bordered wrapper. It would look the same. It would
also: change the **Organisation** chart for every employee, change the **wall chart**
print (069) and the shared-seat copies (072), and add up to **165 extra tab stops** to
the default view for a keyboard user — a real accessibility cost, which the priority
ladder puts above convenience. Size M, and it touches three shipped slices. I recommend
option A. ⚠ DECISION 3.

### 3.4 Panel, drawer or modal — the existing drawer

**Recommendation: the existing right-hand drawer (`.emp-drawer`, F9).** Not a modal, not
a new page, not a hover card.

| Option | Verdict |
|---|---|
| **Drawer** (recommended) | Already built, already reused three times, already full-screen on a 360 px phone, and it keeps the chart visible behind it so the reader does not lose their place. Rung 1 of the ladder: already there |
| Modal | The seat tray is already a modal. A modal opened from a modal stacks focus traps and gives a phone two "close" buttons. Our own learnings flag exactly this ("two bottom bars, two buttons for one job") |
| Hover card | No hover on a phone, and it would put the whole feature out of reach of the frontline-first rule |
| New page | A new page needs a reason. Losing the chart is not one |

**Four things the drawer needs before it carries this:**

1. **Accessibility, P2.** `#emp-drawer` has no `role="dialog"`, no `aria-modal`, no
   Escape and no focus move (F10). The anti-pattern list already records this for the
   Positions modals (P7). Whatever drawer this slice opens must get those four.
2. **Phone.** It is already full width. It needs a 44 px close, and focus must return to
   the name that opened it.
3. **Opened from inside the seat dialog**, it would be a third layer. Recommendation: in
   the dialog the person's row **expands in place** rather than opening a drawer over a
   modal. Same content, no stack. For design to settle in `01b`.
4. **Its own call.** The chosen fields must be fetched **when a profile is opened**, not
   added to the `position_table` payload. A table reply that carries ten personal fields
   for 403 people is a disclosure of 4,030 values to the browser even if the screen shows
   ten at a time. One small call per open is both cheaper and narrower.

---

## 4 · Ideas by persona

Every row says what it serves and what it costs. The PM chooses; I do not.

### 4.1 CXO / founder — the persona this slice is really for

| Idea | Job it serves | Evidence | Size |
|---|---|---|---|
| **Faces on the hierarchy**, initials where there is no photo | An owner with 403 staff across six stores knows the faces better than the names. A face is the fastest way to confirm "is that the person I met at Karol Bagh?" | F2–F5: three lines of code. Frappe HR's own chart already does it (F3 in §5) | **S** |
| **Name → mini profile** from the table and the seat tray | Answers "who is this, what do they do, where, since when" without opening Desk | F9: the drawer exists | S–M |
| Faces **on the wall chart** so staff recognise managers | A printed chart on a store wall is for the people who work there | 069 built the print path | S, but ⚠ DECISION 4 (a customer walks past that wall) |

**What it makes worse for them:** nothing, provided §3.2 items 1–3 are in. A slow chart
is worse than a chart with no faces.

### 4.2 HR Manager — the one who configures it, and the one who pays for it

| Idea | Job it serves | Evidence | Size |
|---|---|---|---|
| **Mini profile with the fields the tenant chose** | Stops the hop to Desk for "when did she join", "which shift", "who does she report to" | F9, F11 | M |
| **One setup card on the existing Org Settings page** (§6) | One place, one save, no new page | F16, F17 | S–M |
| **A preview in the setup card: "this is what a reader sees"** | The Zoho failure in §5 is a field picker whose result nobody can predict. HR should see the drawer as it will look, with a real person, before saving | §5 | S |
| **A way to collect 403 photos** that is not HR uploading them one at a time | Without it the feature never appears. ⚠ DECISION 1 | F1 | see §8 |

**What it makes worse for them:**

- **HR becomes the photo department.** 403 photographs, at a tenant where one person also
  does the accounts. §8 is about this.
- **A wrong tick is a disclosure.** The setup screen is the first screen in this product
  that lets HR choose, per tenant, which personal fields appear on a page the tenant may
  have opened to its managers. §6 is about this.
- One more card on an Org Settings page that already has ten.

### 4.3 Employee and frontline worker — what this does *to* them

**They do not open this page.** They get the Organisation page. So every line below is a
cost they carry for someone else's convenience, which is exactly what the one-way rule
(product-context §2) tells us to look at hardest.

| What changes for them | Good or bad | What I would do |
|---|---|---|
| Their face appears to everyone who can open Positions | Mostly fine — a face beside a name on an internal chart is ordinary, and colleagues already see the name. But it is new, and they were not asked | Say it in the privacy notice before the first photo is collected (§7, ⚠ COMPLIANCE) |
| They are asked to upload a photo | Fine, **if** they are asked through the surface they already use and in one tap. Not fine as an HR chase-list | §8 option C |
| **Their documents could appear** on a structure page | **Bad.** PAN, Aadhaar, bank proof, police verification. §7 | Leave documents out of this slice |
| Faces on the **Organisation** page too (same renderer, F2) | Good, and free. An employee looking up "who do I talk to in Finance" is helped most by a face | Ship it with the same change; say so out loud |
| A face on a **printed** chart on a shop wall | Depends entirely on who walks past the wall | ⚠ DECISION 4 |
| 3G cost of 165 images | Only matters if a frontline worker opens a chart — the Organisation page is bounded to about 5 boxes, so small | Items 1 and 3 of §3.2 cover it |

**The one thing I would refuse outright.** Nothing in this request asks for it, and I am
writing it down so it cannot arrive later: a photo on this page must never be matched,
compared, scored or used to confirm who checked in. That is facial analysis, and
`product-context.md` §6.3 and `nfr-budget.md` §6 make it architecturally refused.
`2026-10-24-ux-priorities.md` §3 already rejects the "face recognition kiosk" that Keka
and Deputy ship.

### 4.4 Line manager — only where the tenant has opened the page

Better: a face makes a cross-store chart readable. Worse: nothing new, **but** F11 means
the audience for the mini profile is whatever the tenant ticked, and
`alvoraa_org_managers_see_all` defaults to on. A tenant that gives managers Read on
`Alvoraa Position` gives every one of them the mini profile for everybody in their
companies. That is a setting, not a bug — but the setup card must say it in words (§6).

---

## 5 · Benchmark — faces and a quick profile on an org chart

Labels are strict: **read** means I read a page and dated it; `[recall — verify]` means
memory. **I viewed no competitor product screenshots of an org chart.** Keka's help
centre returned HTTP 403 to my fetcher, which the learnings already record.

| Product | What they do | Label |
|---|---|---|
| **Frappe HR (standard)** | Its own Employee Hierarchy chart **already puts the employee photo on every node card**, with an avatar frame as the fallback, plus name, designation, a count of people beneath, and an edit button into the Employee record | **Read in this repo, 31 Oct 2026**: `hrms/public/js/templates/node_card.html` and `hierarchy_chart_desktop.js`. Confirmed by the ERPNext manual page for the organisational chart (read 31 Oct 2026) |
| **Keka** | Org Tree plus Employee Directory; the tree filters to whole company / me and my team / by department, and downloads as PDF, image or CSV. Directory rows show role, department and contact, and "Open Profile" opens the person. **Profile cards are configurable by an admin** at Org → Employees → Settings → **Employee Profile Layout** | **Read, 31 Oct 2026**, from the help-centre search summary for *Using the employee directory and organization tree*. The page itself returned 403. Whether the **tree** nodes carry photos: **not confirmed** |
| **Zoho People** | A community thread titled *"View Only Fields on Employee Profile via Organization Chart"* exists, so there **is** a configurable set of view-only fields reachable from the chart. The post reports that with every field set to View, the poster's **own** profile showed everything and their **manager's** showed only a few, telephone missing, and nobody answered why. Profile photo max 2 MB | **Read, 31 Oct 2026** (help.zoho.com community thread). The failure is the useful part — see "what not to copy" |
| **Darwinbox** | App listing: *"Find colleagues in the directory, view the org chart, and reach out to team members instantly."* No description of the node card | **Read, 31 Oct 2026**, App Store India listing, app version dated 13 Oct 2026 |
| **HiBob** | Marketing and review material describes customisable org charts, and their developer docs treat the profile photo as its own employee field with an "upload employee avatar" action | `[recall — verify]` for the chart card itself. The avatar upload action is **read, 31 Oct 2026** (integration docs listing) |
| **greytHR** | Nothing found on org-chart faces | no evidence either way |

**So: faces on an org chart are parity, not an advantage — and we are behind our own
framework.** The thing none of them was documented as doing is the thing this slice could
actually own: **the tenant decides which fields a reader sees, and HR can see exactly
what that reader will see before saving.** That is the same "we explain" position
`2026-10-24-ux-priorities.md` §3 identifies as our real advantage.

### What not to copy, and why

| Do not | Seen at | Why not |
|---|---|---|
| A field-visibility model nobody can predict | Zoho (read, thread above) | The admin set every field to View and still could not explain what their manager's card showed. Our setup card must **preview the result** |
| A hover preview on the node | common in chart tools `[recall — verify]` | No hover on a phone, and slice 070 made this page work on a phone |
| A grid or wall of faces | our own Employee Home, anti-pattern H2 | A 40-row people grid was already a finding against us |
| Photo-match or face-recognition attendance | Keka, Deputy (per `2026-10-24-ux-priorities.md` §3) | Refused: product-context §6.3, nfr §6 |
| Grey silhouette placeholders | generic | Slower and less useful than initials (§3.1) |
| Downloading the chart as an image with faces on it | Keka (read) | A file of 55 faces leaves the product. If export is ever wanted, it needs its own privacy answer |

---

## 6 · The setup screen — where it should live, and the part that worries me

### 6.1 The ladder

| Rung | Option | Verdict |
|---|---|---|
| 1 · already there | Nothing today chooses which Employee fields a page shows | Rejected: it does not exist |
| 2 · **configuration** | **Two Global Defaults keys, written through the pattern `settings.py` already uses, rendered as one new card on the existing Org Settings page** | **Recommended** |
| 3 · customisation | A Custom Field check box "Show on the Positions page" on `Employee Document Type` | A reasonable alternative for the documents half only — it puts the choice where the type already is. But it splits one screen into two, against the request. Noted, not recommended |
| 4 · new code | A whitelisted getter and setter for the two keys | Needed, and small. `set_cover_setting` is the shape to copy |
| 5 · new DocType | A "Positions Profile Field" record per chosen field | **Rejected.** It buys a permission surface, a migration and a list view, and I cannot name one thing it does that a comma-separated setting does not |
| 6 · new app / new page | — | Rejected |

**So: one new card on Org Settings, two settings keys, one getter, one setter.** The card
follows the ten cards already there — header, meta line, controls, hint (F17).

### 6.2 The part I would not build as asked

**A free pick over the Employee doctype is not safe here.** Employee has roughly two
hundred fields, including `bank_ac_no`, `pan_number`, `ctc`, `date_of_birth`,
`cell_number`, `marital_status`, `blood_group`, `personal_email` and the emergency
contact. And **read on those is deliberately open** to every role that reads Employee
(F12) — `employee_field_rights.py` locked **write**, on purpose, so that no screen would
lose a field. So Frappe's permission levels will not stop a bad tick.

**Recommendation, two parts:**

1. **A curated candidate list**, not the whole doctype. Ten or so fields that describe a
   person's place in the organisation and nothing else: job role, department, branch,
   company, reports to, grade, employment type, date of joining, default shift, work
   email, work phone. Each with a one-line plain-English label, like `settings.LABELS`
   already does.
2. **A deny list the server enforces and no setting can override**: pay and CTC, bank,
   statutory identifiers, date of birth, personal contact details, home address,
   emergency contact, marital status, blood group, anything health-related, the relieving
   date (slice 065 already treats that as private news — see the open item from slice
   059), and every field named by a payroll rule set (`rule_set_fields()` already
   computes that list).

A refusal in the server, not only a short list in the browser: the endpoint must refuse a
field outside the allow-list even if somebody posts it directly.

### 6.3 The words the card needs

Draft copy, for `01b` to finish. English first; Hindi needed for parity
(`product-context` §5) and new strings go through the existing `drT()` wrapper.

> **What a reader sees about a person on the Positions page**
> Tick the details that appear when somebody opens a person's card from the
> organisation chart or the positions list. Everyone who can open the Positions page
> sees these, for the people in their own companies and branches. Pay, bank details,
> identity numbers, date of birth and personal contact details can never be shown here.
>
> **Right now, 7 people can open the Positions page.** [See who]
>
> [ Preview what a reader sees ]

The count and the "see who" link matter: HR is ticking a box whose audience is a
permission they may not have set themselves (F11). Without the count, the card asks HR to
guess.

---

## 7 · Documents — my recommendation is to leave them out, and why

### 7.1 The evidence

**The eighteen Employee Document Types at PPJ** (Fact, read 31 Oct 2026):

| Category | Types |
|---|---|
| Identity | PAN card · Aadhaar card · Passport-size photographs |
| Statutory | Bank account proof · UAN / PF details · ESI number · Security agency licence |
| Verification | Background verification report · Police verification certificate · Police verification acknowledgement · Reference check note |
| Employment | Previous employer relieving letter · Last 3 months' salary slips · Signed offer and appointment letter |
| Address | Address proof (current) |
| Education | Highest education certificate |
| Company Issued | Signed policy acknowledgement · Vault access authorisation |

**Fifteen of the eighteen are identity, statutory, financial or background-check
documents.** The only one with any business on a structure page is "Passport-size
photographs" — and that is the photo feature in §3, not a document list.

**And the list would be empty.** 6,468 of 6,469 rows are "Expired" and **not one has a
file attached**. So the first thing this feature would show, at the only tenant we have,
is a column of red "Expired" badges with nothing behind them.

### 7.2 Why it is a bigger step than it looks

- It is **not a new disclosure path only** — it is a new *audience*. Today the documents
  are reachable by HR, on the Employee record, in Desk. Positions can be opened to the
  owners or to managers by a tick (F11).
- The files are private, attached to Employee (F14). Frappe lets a user read a private
  file when they can read the attached document, so the gate is Employee read, not
  something this slice controls.
- `Employee Document` is a child table, and the repo learned on 30 Oct 2026 that
  `has_permission` on a child table is always False (F13). Any guard written carelessly
  here fails open.
- It is a plan feature (F15), so the screen needs a "not switched on for this
  organisation" state — the pattern slice 009 already settled.

### 7.3 ⚠ COMPLIANCE — and the smallest safe version if you still want it

**Owner: `hrms-security-privacy-engineer`, before any spec.** This is a DPDP question
about purpose limitation and minimum necessary (`nfr-budget.md` §5: sensitive identifiers
are "read only on a need-to-know path; **never** in list views, default exports or
notifications"). I am not a lawyer and neither is any agent here.

**My recommendation: documents are not in this slice.** HR, the only legitimate reader,
already has the Employee record and already has the compliance card on Org Settings
(`hr_document_compliance`). Nothing is gained by a second door with a wider audience.

**If you want them anyway, the smallest safe version is:**

- Only types whose category is **Company Issued** (offer letter, policy
  acknowledgement, vault authorisation) — never Identity, Statutory, Verification,
  Employment or Address.
- Shown only to a reader who could already read that employee's documents, checked on
  **Employee**, never on the child table.
- The existing My-profile row shape reused exactly: type, status badge, a "View" link to
  the private file. **No inline preview, no thumbnail, no download-all.**
- Nothing printed, under the same rule as 069 and 065.

---

## 8 · The question that decides whether any of this is visible — 403 photos

⚠ **DECISION 1.** With 0 photos on file, nothing in §3 shows up until photos exist. Four
routes, cheapest first:

| # | Route | Cost | Honest view |
|---|---|---|---|
| A | **HR uploads them on Desk, one at a time** | Zero build | 403 uploads by the person who also does the accounts. It will not happen. This is the default if nobody decides |
| B | **A bulk import** from a folder of photos named by attendance device id or employee id | Small script | The DTC matching rule in memory applies: device id first, never the sheet's own employee id. Needs a source folder that may not exist |
| C | **The employee adds their own, from My profile, in one tap** | Small — the upload plumbing already exists in `uploadMyDocument`, and "Passport-size photographs" is already a type collected **from the employee** | **My recommendation.** It is one tap for the person, it needs no HR time, the consent conversation happens with the right person, and it is the only route that stays current as people join. A frontline worker on a phone can do it in under a minute |
| D | Reuse the field app's check-in photos as profile photos | — | **No.** They were collected for attendance evidence. Reusing them as a directory photo is purpose creep, and the retention rules differ. Flagging it so nobody proposes it later |

**With route C, the slice has a real first-run story:** faces appear gradually, initials
hold the line, and the chart never looks broken. Without a decision here, ship-and-see
means ship-and-nothing-changes.

---

## 9 · States this will need, and the ones that are easy to forget

For `01b` to draw. Listing them now because the learnings record that a state nobody drew
is where the untrue sentence lives.

| State | What it is |
|---|---|
| Nobody in the seat has a photo | Today's chart. Initials. No message, no prompt |
| Some have, some have not | Mixed row, same size circles, no jump |
| A photo that fails to load | Fall back to initials, silently. Never a broken-image icon |
| The tenant has ticked **no** fields | The mini profile still opens, showing name and job role, and says in plain words that the organisation has not chosen anything else to show. HR, and only HR, sees a link to the setting |
| The reader may see the name but not the person's branch | Scoped out by F11's company/branch rule. Say "not shown to you", not a blank |
| The person has left | A mini profile opened from a historical view. Say so |
| The call for the profile fails | Plain words plus **Try again** inside the drawer, within 10 s, per slice 070's rule |
| A 25-person seat | The tray, not the card. The card keeps three names and a count |
| Documents off (plan, or not ticked) | No section at all. Not an empty heading, not a greyed tab |
| Print | Faces off by default (⚠ DECISION 4); documents never |
| Phone, 360 px | Drawer full screen, 44 px close, focus returns to the name |
| Hindi | Every new string through `drT()`; Devanagari runs about 30 % longer, so the card's labels need the long case drawn |

---

## 10 · Findings and ideas, ranked

Impact · Kind (Fix / Improve / New / Keep) · Size · Severity where it could block a
release.

| ID | Finding or idea | Impact | Kind | Size | Severity | Evidence |
|---|---|---|---|---|---|---|
| PF1 | **0 of 403 employees have a photo.** The feature is invisible on delivery unless photo collection is decided | High | New | — | **P1** if the slice ships without a decision — it would be a release with no visible change | measured, §2.1 |
| PF2 | The Positions feed drops `image` although the card, the CSS and the Organisation endpoint all already handle it | High | Fix | **S** | — | F2–F5 |
| PF3 | A free pick over Employee fields would let HR tick bank, PAN, CTC or date of birth onto a page a tenant may have opened to managers; Frappe's levels do not block **read** | High | New | M | **P0** as asked. Needs the curated list and the server deny list of §6.2 | F11, F12 |
| PF4 | Documents on this page means PAN, Aadhaar, bank proof and police verification on a structure page, to a wider audience | High | New | M | **P0** as asked. ⚠ COMPLIANCE, security owns it | §7 |
| PF5 | The 60 % zoom threshold puts the target below every size floor we have, and the chart card cannot hold a nested button | High | Fix | S | **P2** if built as described | F6, F7, §3.3 |
| PF6 | Up to 165 full-size photos on first paint, 360 on the table, with no resizing anywhere in the repo | High | New | S–M | **P2** against the 2.5 s / 3G budget | §2.1, F20, nfr §2 |
| PF7 | `#emp-drawer` has no `role="dialog"`, no `aria-modal`, no Escape, no focus move | Medium | Fix | S | **P2** (WCAG 2.2 AA, and anti-pattern P7 seen again) | F10 |
| PF8 | Faces would print onto the wall chart, which hangs where customers walk | Medium | New | S | P3 once decided | F19, ⚠ DECISION 4 |
| PF9 | The setup card asks HR to tick a box whose audience is a permission they may not control; it needs the reader count and a preview | Medium | New | S | P3 | F11, §5 Zoho |
| PF10 | Faces also appear on the **Organisation** page for every employee, free, from the same change. Say it out loud rather than letting it arrive as a surprise | Medium | Improve | — | — | F2 |
| PF11 | The mini profile's fields must be their own call, not extra columns on `position_table` | Medium | New | S | P3 | §3.4 item 4 |
| PF12 | No photo on a card must fall back to initials silently; no silhouette, no broken-image icon | Low | New | S | P4 | §3.1 |
| **Keep** | The 3-names-then-a-count rule; two levels open; one shared renderer; 070's phone stack; 065's screen-share link; 069's print suppression | — | **Keep** | — | — | §2.3 |

---

## 11 · Decisions only you can make

| # | Decision | Why it matters | Blocks | My recommendation | Owner |
|---|---|---|---|---|---|
| ⚠ 1 | **How do 403 photos get onto the records?** | Without an answer the slice ships and nothing looks different | Whether the slice is worth building at all | **Route C** — the employee adds their own from My profile in one tap. Plumbing exists; "Passport-size photographs" is already collected from the employee | Surbhi |
| ⚠ 2 | **Documents: in or out?** | 15 of 18 types are identity, statutory, financial or background-check, and the audience is a tenant tick | The spec, and a DPIA question | **Out of this slice.** If in, only Company Issued types, HR-only, guarded on Employee, no preview | Surbhi, with `hrms-security-privacy-engineer` ⚠ COMPLIANCE |
| ⚠ 3 | **Clickable name: option A (table + seat tray) or option B (restructure the shared card)?** | B changes the Organisation chart, the wall chart and 072's copies, and adds ~165 tab stops | The design, and three shipped slices | **Option A.** Same outcome, one extra tap on the chart, no zoom rule, no invalid markup | Surbhi |
| ⚠ 4 | **Faces in print — on the wall chart, and on Ctrl+P?** | A printed chart of 55 faces hangs where customers walk past | The print rule | Off by default for Ctrl+P; **ask you** about the wall chart, where recognising a manager may be the whole point | Surbhi |
| ⚠ 5 | **Which fields are on the candidate list?** | It is the whole privacy surface of the mini profile | The setup card and the server allow-list | The eleven in §6.2 part 1, and the deny list enforced on the server | Surbhi, with `hrms-business-analyst` |
| ⚠ 6 | **Does an employee get to hide their own photo?** | Slice 076 already set the pattern ("each person can hide themselves in My profile") for birthdays, so it is one checkbox, not a new idea | The privacy notice and the employee's own screen | **No opt-out for the photo** — a face beside a name on an internal chart is ordinary, and a patchy chart is worse for everyone. But the precedent exists and the DPO view may differ, so it is your call, not mine | Surbhi, with security |
| ⚠ 7 | **Does the privacy notice need updating before the first photo is collected?** | A new use of a person's image | Photo collection | Yes, one sentence: the photo on your record is shown on the organisation and positions charts to colleagues who can see you | Surbhi, with security ⚠ COMPLIANCE |

---

## 12 · What I removed on the subtract pass

Per `no-over-engineering.md` §4, read back once asking only what can be deleted:

- **Faces in the table.** Removed. Up to 360 images on one unpaginated page, answering
  none of the three questions the table exists for (where are we short, who is leaving,
  who could cover — your own words, 15 Oct 2026). The names there become links instead,
  which is the part you actually asked for.
- **The zoom threshold.** Removed entirely rather than re-tuned.
- **A new settings page and a new DocType** for the field choices. Replaced with one card
  on Org Settings and two Global Defaults keys.
- **A free field picker over the Employee doctype.** Replaced with a curated list plus a
  server deny list.
- **The documents section.** Recommended out, with the smallest safe version written down
  in case you want it.
- **A per-person photo opt-out, a thumbnail cache, a background job, a photo service, a
  hover preview, an audit log of profile opens, and an "export the chart with faces"
  action.** None was asked for and none is needed.
- **A second renderer or a second avatar component.** `ocAvatar` and `.emp-drawer` are
  reused as they are.

What I did **not** remove, and the measured reason: the **48 px copy made once when a
photo is collected** (§3.2 item 3). 165 originals against a 2.5 s / 3G budget is the kind
of number `no-over-engineering.md` §5 asks for before an extra is allowed.

---

## 13 · What the PM and the analyst need from this

1. **Answer ⚠ 1 and ⚠ 2 before the brief is written.** They decide whether the slice is
   one small change or two risky ones.
2. **The brief should name three outcomes, not five:** faces on the hierarchy (and, for
   free, on the Organisation page); a name that opens a cut-down profile from the table
   and the seat tray; one Org Settings card that chooses what that profile shows.
3. **For the design step** (`01b`, with a prototype as P6 requires): someone with a login
   must capture Positions at 1440 × 900 and 390 × 844 first. This is the fourth
   consecutive slice on this page where no screen was seen in a browser.
4. **For security** (`01c`): the field allow-list and server deny list (§6.2), the
   audience count on the setup card (§6.3), the print rule (⚠ 4), the privacy-notice
   sentence (⚠ 7), and — if documents survive — all of §7.
5. **Acceptance criteria this scan already points at:** a chart with no photos looks
   exactly as it does today; a photo that fails to load falls back to initials; the
   profile endpoint refuses a field outside the allow-list even when posted directly;
   the default two-level view fetches no photo that is off screen; the drawer closes on
   Escape and returns focus; nothing private prints; and the query count for
   `position_table` is the same for 20 seats as for 400.

---

## 14 · Honest gaps in this scan

- **No browser capture.** Every layout number is read from CSS and JavaScript (§2).
- **No competitor org-chart screenshot was viewed.** Keka's help centre returns 403 to a
  fetcher; the rest of the benchmark is read-with-dates or marked `[recall — verify]`.
  Frappe HR's photo node is the one claim I verified in code.
- **The 0-photo figure is the PPJ demo copy only.** DTC and the other tenants were not
  queried. It would be worth one read-only check on dev before the brief.
- **Nothing here has been tested with a real user.** The CXO claim — that a face is how
  an owner recognises someone across six stores — is my judgement, not research. It is
  cheap to check: show one owner the chart with ten faces on it.
- **No data was changed on the bench.** Reads only, through standard input.
