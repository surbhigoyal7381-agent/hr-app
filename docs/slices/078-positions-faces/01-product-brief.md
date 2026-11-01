---
slice: 078-positions-faces
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-10-31
status: draft, revision 2 — for Surbhi's gate (build, change or drop)
inputs: [01a-ux-opportunities.md, 07-devops-inputs.md §1, product-context.md, no-over-engineering.md, security-compliance-baseline.md, handoff-contract.md, hrms/alvoraa_org_structure/{register,api,settings,plans}.py, hrms/hr/web_form/job_application/, hrms/hr/doctype/employee_onboarding/, alvoraa_portal/{auth.py, employee_field_rights.py, portal.js, home.html}, PPJ local copy figures as measured by UX and DevOps on 31 Oct 2026, Surbhi's answers of 31 Oct 2026]
---

# 078 · Faces and a mini profile — product brief

> **Revision 2, same day.** Three things arrived after the first draft was written: two
> answers from Surbhi (no DTC photos, "but they will upload it"; **Positions is readable
> by HR Manager at DTC**, not System Manager only) and **new scope — a public
> pre-onboarding link for new joiners**. §11 is the new section and it changes my answer
> on how many slices this is. Nothing in the first draft turned out to be wrong; the
> DTC answers made two open questions go away.

## The answer first

**This is three slices plus a separate one, and the one you asked for second has to ship
first.**

Nobody has a photo. **0 of 403 employees** at PPJ have an image on their record
(measured 31 Oct 2026, both input documents agree), and **you have confirmed none at DTC
either — "No but they will upload it"**. So "photos on the Positions hierarchy" ships a
page that looks exactly as it does today. Your My Profile decision is what fixes that:
**employees supply their own photo, so that is the slice that makes every other part of
this idea visible.** It goes first.

My recommended order, each half a complete outcome on its own:

| # | Slice | One outcome | Who notices on day one |
|---|---|---|---|
| **078A** | **My profile is mine** — photo upload, the fields HR lets me edit, a link to change my password | An employee corrects their own record and puts their face on it, on a phone, without emailing HR | **Every employee.** And faces appear on the **Organisation** chart the same day, for free — no chart code at all |
| **078B** | **Who is in this seat** — the mini profile from the table, the seat tray and the "Change this seat" dialog, plus the one Org Settings card that chooses what it shows | HR or an owner answers "who is this, what do they do, since when" without opening Desk | HR Manager, CXO |
| **078C** | **The documents on that profile** — HR-only, behind a server endpoint that actually enforces the ticked types | HR reads an employee's document from the chart instead of from Desk | HR Manager only |
| **079** | **The pre-onboarding link** — a new joiner fills in their own details and uploads their own documents before they have an account | A new joiner arrives already on the system, with a photo | HR Manager, and the joiner |

**The new scope belongs in its own slice, and the reason it was meant to be joined to
this one does not survive inspection.** The pre-onboarding form was to share the
Organisation Settings screen. But **Frappe's Web Form already is that screen** — it owns
its own field list, its own public route and its own login-required switch, and it
already ships a working public example in this repo (`job_application`,
`login_required: 0`, **confirmed 31 Oct 2026**). Putting a third list on our settings
card would build a second field picker for a form that comes with one. Strip that away
and 079 shares nothing with 078 except the word "fields". Everything else about it is
different: a person who is not yet an employee, no account to check, a link that can be
forwarded, and **an upload endpoint reachable from the open internet** — the first one in
this product. Full reasoning and the price in **§11**.

**Second piece of bad news: faces on the chart cards is the one expensive thing here,
and it is expensive for a reason no thumbnail fixes.** The chart arrives in one payload
of 120 seats and 403 people. Faces on the cards means **about 400 image downloads, each
answered by a Python worker, through the 8 request slots the whole site has**. Small
images do not reduce the count. One HR user opening the chart could stall the site for
everybody, including a driver trying to punch in. Priced options are in ⚠ DECISION 2 —
you asked for this by name and I am not dropping it quietly, but I am recommending
against it for now and saying what would change my mind.

---

## 1 · Job to be done

**078A, in an employee's words** *(constructed from the request, not a quoted customer —
see "Evidence required"):*
> "My phone number on the record is my old one and there is no picture of me. I do not
> want to ask HR to fix it, and I do not have a laptop."

**078B, in yours (16 Oct 2026, carried from slice 072):**
> "I am looking at a chart I did not draw. I want to know who that is and what they do
> without opening three screens."

**Personas.** 078A is **Employee** (and the frontline worker above all — phone-only,
Hindi-first). 078B is **HR Manager** and **CXO**. 078C is **HR Manager** alone.

**What changes for the other two.**
- 078A for HR: fewer "please change my number" messages, and 403 photographs HR did not
  have to collect. Risk: an unsuitable photo arrives (§9).
- 078A for the CXO: the Organisation chart starts showing real faces, free.
- 078B for the employee: **their details become visible to whoever the tenant has given
  Read on `Alvoraa Position`.** **At DTC that is HR Manager (confirmed by you, 31 Oct
  2026)** — wider than the demo copy, which is System Manager alone, but narrower than
  the worst case of "every line manager". That matters twice: the audience for the mini
  profile at our live tenant is HR, and the HR-only document gate in 078C therefore lines
  up with the page's own permission instead of fighting it. The employee still does not
  get to see this page themselves, and that asymmetry is what product-context §2 tells us
  to look at hardest.
- 079 for the joiner: they are not an employee yet and have no account, so **every
  protection in this product that depends on a login does not apply to them.** §11.

## 2 · Current pain

**A story, not a statistic — I have no measured baseline and will not invent one.**

DTC's HR is one person who also does the accounts, and 442 employee records are
maintained from spreadsheets (memory, 25–26 Oct 2026). When a number changes, it changes
in a sheet or not at all. There is no screen in this product today where an employee can
put their own photograph on their own record: `Employee.image` is a Desk upload, and
frontline staff neither have nor should have Desk.

**Measured, 31 Oct 2026:** 0 of 403 PPJ employees have a photo; **0 at DTC too
(confirmed by you)**. 6,469 `Employee Document` rows exist, 6,468 marked Expired, **0
with a file attached**. The checklist exists and is empty.

**And for a new joiner today**, every one of those details and documents reaches the
system by HR typing them in from paper or a sheet. That is the pain 079 addresses, and
it is the same pain as 078A one step earlier in a person's life.

**Evidence required.** No customer request, demo note or support ticket for any part of
this is on record that I could find. The request originates with you. That does not make
it wrong — it makes the Kano class in §4 a **proxy**, and it is why 078A's success
measure in §7 is "do employees actually upload" rather than a satisfaction claim.

## 3 · Competitive analysis — whole products

The UX scan's table (`01a` §5) stands; I am not repeating it. These are the rows it did
not cover: the self-service and pricing lens.

| Capability | Frappe HR (standard) | Keka | Zoho People | Darwinbox | Us today |
|---|---|---|---|---|---|
| Photo on the org-chart node | **Yes** — `node_card.html` puts the employee photo on every node, avatar fallback (**read in this repo, 31 Oct 2026**) | Org Tree + directory; node photo **not confirmed** (help centre returns 403) | Chart reaches a view-only profile | Directory + chart, node card undocumented | **No** — our Positions feed drops the field the card already renders |
| Employee edits own profile from a phone | Yes, the ESS portal and app | Yes, with an approval workflow on sensitive fields `[recall — verify]` | Yes | Yes | **Only one tick** (birthday sharing, slice 076) |
| Employee uploads own photo | Yes | Yes `[recall — verify]` | Yes, max 2 MB (**read, 31 Oct 2026**) | Yes `[recall — verify]` | **No** |
| Admin chooses which profile fields others see | Partly (permissions) | Yes — **Employee Profile Layout** (read, 31 Oct 2026) | Yes, and **nobody could predict the result** (read: Zoho community thread, 31 Oct 2026) | Yes `[recall — verify]` | No |
| Change own password from the employee surface | Yes | Yes | Yes | Yes | **Already there and unlinked** — `/update-password` works and our wrapper lands the user back in the portal (`auth.py:100`). There is no link to it (**confirmed**: no "password" string in the portal frame) |
| Identity documents reachable from the org chart | No | Not documented | No | No | — |
| **New joiner enters their own details before day one** | **Partly** — a public `job_application` **Web Form** collects a candidate's details and resume with **no login** (`login_required: 0`, **read in this repo 31 Oct 2026**); `Employee Onboarding` then runs a task list and creates the Employee, but **does not collect the joiner's own data** | Pre-onboarding / candidate portal with document upload, in the onboarding module `[recall — verify]` | Yes, in onboarding `[recall — verify]` | Yes, "pre-boarding" `[recall — verify]` | **No** |

**Pricing lens.** Self-service profile editing and a photo sit in everybody's **entry
tier**. Nobody charges for it, because it is the floor. Employee Documents is already a
plan feature for us (`plan_employee_documents`), and 078C inherits that.

**What we will deliberately NOT do that they all do, and why it makes us better.**

1. **No photo-match or face-recognition attendance.** Keka and Deputy ship it. We refuse
   it architecturally (product-context §6.3, EU AI Act Article 5, in force since 2 Feb
   2025). A photo collected here must never reach an AI path, and nothing in these three
   slices creates one.
2. **No "download the chart as an image".** Keka does (read). A file with 55 faces in it
   leaves the product and nobody can take it back.
3. **No free pick over every employee field.** Zoho has it, and their own community
   thread shows an admin who set everything to View and still could not explain what
   their manager's card showed. **We offer a short curated list with a preview of what a
   reader will actually see.** That is the "we explain" position
   (`2026-10-24-ux-priorities.md` §3) applied to privacy, and it is the only thing in
   this whole idea a competitor is not already doing.
4. **No approval workflow on a self-service edit.** Keka routes some changes to HR. Our
   field rights already decide what an employee may touch (`employee_field_rights.py`);
   a workflow on top of a permission is two mechanisms for one rule.

## 3a · Three ways to solve it

| | What it is | Verdict |
|---|---|---|
| **Conventional** | A new "Employee Profile" settings DocType, a new My Profile page, a new mini-profile component, a thumbnail service, documents inline | Rejected. Rungs 5–6 of the ladder for a job that needs rungs 2–4. It is also four screens where two cards would do |
| **Better** *(recommended)* | Reuse what is already built: `ocAvatar` draws the face, `.emp-drawer` holds the profile, the My profile panel holds the upload, Global Defaults holds the lists, `/update-password` is the password screen, `uploadMyDocument`'s plumbing becomes the photo upload. New code is: one field on one query, one small profile endpoint, one resize-on-upload hook, two settings keys and one card | **This is what I am proposing** |
| **Reimagined** | Collect photos through WhatsApp, which is where DTC's owners already live | Interesting, refused: a new integration, a new processor, a new consent story, and it still has to land on the Employee record. Written down so it is not re-proposed as cheap |
| **Could we not build it at all?** | Honest answer for **078B's chart faces**: yes — a seat's name list already tells HR who is in it, and clicking the card already opens the tray. For **078A**: no. There is no configuration, default or sort order that lets a phone-only employee put a photo on their own record. For **078C**: yes — HR already has the Employee record in Desk, which is the same documents with a narrower audience |

**Rung on the cost ladder, item by item** — rejections named:

| Item | Rung | Why not cheaper |
|---|---|---|
| Employee changes their own password | **1 · already there** | `/update-password` exists and works. The gap is a link. Nothing is being built |
| Employee edits level-0 fields on their own record | **1 · already there** (permissions) + **4** (a thin panel) | Frappe HR already gives write on own record at permlevel 0; `employee_field_rights.py` already refuses levels 1 and 2 on your own record. **No new permission machinery at all.** The gap is a screen |
| `image` on the Positions feed | **4 · new code**, three lines | The query already joins Employee (`register.py:303`). No cheaper rung exists; the field is simply not selected |
| The two field lists | **2 · configuration** — Global Defaults keys, rendered by the existing Org Settings page | Rung 5 (a DocType per chosen field) buys a permission surface, a migration and a list view and I cannot name one thing it does that a comma-separated setting does not |
| The document-type list | **3 · customisation** — a Check on `Employee Document Type`, which already carries `verifier_roles` and `applies_to_grades` | A second list in Global Defaults duplicates a place HR already configures that doctype |
| Photo resize + metadata strip on upload | **4 · new code**, one hook, one Pillow call | Frappe only auto-optimises above 200 KB and only in Desk, and its EXIF strip runs for JPEG only — **so a PNG or HEIC selfie keeps its GPS** (DevOps, measured). Converting to JPEG at a fixed size does the resize and the strip in one step |
| The mini profile | **4 · new code** — one whitelisted read, rendered in the existing drawer | No existing endpoint returns a chosen subset of fields; `01a` F9 confirms the drawer itself is free |

## 4 · Kano class and demand

All **proxy**, no survey. CS+/CS− are not available and I will not fabricate them.

| Feature | Class (proxy) | Why that class | Demand evidence |
|---|---|---|---|
| Employee uploads own photo, edits own contact details, changes own password | **Must-be** | Every competitor ships it in the entry tier; its absence is invisible in a demo and infuriating in use | Weak and honest: no ticket on record. The strongest evidence is 0 photos and 442 records maintained in a spreadsheet |
| Photo on the org-chart node | **Must-be** | **We are behind our own framework** — Frappe HR's hierarchy chart already does it (confirmed in repo) | A buyer comparing us with standard Frappe HR sees a chart with faces and ours without |
| Mini profile opened from the chart | **Performance** | Keka and Zoho both have a path from chart to profile; buyers compare how few clicks it takes | 072 and 064 were both driven by "I don't want three screens" (your words) |
| **The curated list with a preview of what a reader sees** | **Attractive** | Nobody documented doing it, and Zoho's own users cannot predict their version | Our whitespace: explainability |
| New joiner fills in their own details and documents before day one | **Performance** | Every mid-market competitor's onboarding module has it, and buyers compare onboarding on how little HR typing it needs. It would be **Must-be** with one piece of evidence we do not have: a lost deal or a complaint naming it | None on record. Our own build status calls Onboarding 🟡 partial (product-context §3), which is the honest demand signal |
| Identity documents on a structure page | **Reverse for the employee**, Performance for HR | A feature some people would actively not want is Reverse by definition. 15 of 18 types are identity, statutory, financial or background-check | Nobody asked for it except us |

**What would change these:** run the two-question Kano survey on the next three demos
for "employee updates their own profile from a phone" and "see a colleague's face on the
chart". Five answers would beat all of the above.

## 5 · Persona enhancements through the portal

The `01a` ideas, decided.

| Persona | Enhancement | Job it serves | In this slice? | Why |
|---|---|---|---|---|
| **Employee** | Photo upload in My profile, one tap, phone-first | Be recognised; be correct | **078A** | The whole idea depends on it |
| **Employee** | Edit the level-0 fields HR has ticked (mobile, personal email, current address, emergency contact name/relation/phone) | Stop asking HR to change a phone number | **078A** | Already permitted; only the screen is missing |
| **Employee** | Change my password from My profile | Not be locked out | **078A**, as a link | Already built. A link is the whole change |
| **Frontline employee** | The same three things, in Hindi, 44 px targets, one upload under a minute on a poor network | They have no laptop and no Desk | **078A** | Non-negotiable: the frontline wins employee-screen trade-offs |
| **Employee** | Faces on the **Organisation** page (same renderer, zero code) | "Who do I talk to in Finance?" | **078A, free** | ⚠ DECISION 4 — it is a consequence you should accept on purpose, not discover |
| **Employee** | Hide my own photo | Control | **No** | Not asked, and a patchy chart is worse for everyone. 076's birthday precedent exists — ⚠ DECISION 10 |
| **Line manager** | A readable cross-store chart with faces | Recognise people across six sites | **Only where the tenant opened Positions to them** | Nothing extra to build; the setup card must say in words who the audience is |
| **HR Manager** | One Org Settings card with both lists, plus a live preview and a count of who can open Positions | Tick a box and know what it did | **078B** | This is our Attractive feature. The count matters: the audience is a permission HR may not have set |
| **HR Manager** | Mini profile from the table, the seat tray and the "Change this seat" dialog | Stop hopping to Desk | **078B** | All three entry points, option A — no restructured chart card |
| **HR Manager** | Documents on the mini profile, HR-only, with the 065 hide-before-screen-share control | Read a document where the question is asked | **078C**, after security writes `01c` | Needs a server streaming endpoint before it is honest (§8). Your "include them, HR-only" is recorded; see ⚠ DECISION 3 |
| **New joiner** (not yet an employee, no account) | A link they open on their phone, fill in once, upload their documents and photo, and get a plain confirmation | Start the job without a morning of paperwork | **079** | Public and unauthenticated. It needs its own security requirements, not a paragraph in this brief |
| **HR Manager** | A third list on the settings card for the pre-onboarding fields | One place to configure | **No** | Frappe's Web Form already owns its own field list. A second picker for the same form is two mechanisms for one rule. §11 |
| **CXO** | Faces on the chart cards | Recognise a face across six stores | **⚠ DECISION 2** | Priced three ways; I recommend not yet |
| **CXO** | Faces on the printed wall chart | Staff recognise their managers | ⚠ DECISION 5 | A printed sheet of 55 faces hangs where customers walk past |

## 6 · The WOW

**078A, and it is the one I would spend the design effort on.**

The employee opens My profile on their phone. Where the circle with their initials is,
there is a camera button. They tap it, take a selfie, and the circle becomes their face
with a line under it:

> **"That's you. Colleagues who can see you on the organisation chart will see this
> picture."**
> *Hindi: "यह आप हैं। जो साथी आपको संगठन चार्ट में देख सकते हैं, उन्हें यही तस्वीर दिखेगी।"*
> *(Hindi copy is a draft for `01b` to settle; it goes through the existing `drT()`.)*

Then they tap **Organisation** and their own face is on the chart. **No chart code was
written to make that happen** — the card already draws a photo and the Organisation
endpoint already sends one. That is the moment, it is inside 078A, and it needs no
second phase.

**078B's smaller wow**, for HR: the setup card's **"Preview what a reader sees"** button
opens the real drawer with a real colleague in it, before anything is saved. The copy
above the preview reads: *"Right now, 7 people can open the Positions page."*

## 7 · Thin slice, success measures, and what is out

### 078A — My profile is mine

**In:** photo upload (camera or file) in the existing My profile panel · the ticked
level-0 fields, editable in place · a link to `/update-password` · resize-and-convert on
upload · the Organisation chart showing whatever photos now exist · the privacy sentence
beside the upload.

**Out:** the Positions page, the mini profile, the settings card for the Positions list,
documents, chart-card faces, thumbnails, any opt-out, any approval workflow, any photo
moderation screen.

| Measure | Baseline | Target | Instrumented by |
|---|---|---|---|
| Active employees with a photo | **0 of 403** (PPJ, 31 Oct 2026) | ≥ 60% within 30 days of switch-on | Weekly count of non-empty `Employee.image` |
| Employees who corrected a detail themselves | baseline unknown — measure first | ≥ 50 self-edits in the first 30 days at DTC | Count of `Version` rows on Employee whose owner is the employee |
| Employees who set their own password instead of asking HR | baseline unknown — measure first | up at 30 days | Count of Users with `last_password_reset_date` set (the field already exists, `auth.py:96`) |
| **Guard: stored photo size** | n/a | p95 ≤ 50 KB, and no stored original above 200 KB | One query over `File` for the Employee image folder |

### 078B — Who is in this seat

**In:** `employee.image` added to the existing Positions query · the mini profile in the
existing drawer, opened from a name in the table, in the seat tray and in the "Change
this seat" dialog (expanded in place there, not a drawer over a modal) · one Org
Settings card with the two lists and a preview · the drawer's missing accessibility
(`role="dialog"`, `aria-modal`, Escape, focus return).

**Out:** faces on the chart cards (⚠ DECISION 2) · faces in the table (up to 360 images
on one unpaginated page, answering none of the three questions the table exists for) ·
any zoom rule · documents · a clickable name inside a chart card (it is a single
`<button>`; a nested button already broke this page once).

| Measure | Baseline | Target | Instrumented by |
|---|---|---|---|
| Mini profiles opened per HR/CXO user per week | baseline unknown — measure first | ≥ 5 in week one, still ≥ 3 in week four | Count the whitelisted profile call, no personal data in the log |
| Fields a reader can see that the tenant did not tick | n/a | **zero**, including when posted directly to the endpoint | A test, not a dashboard |
| `position_table` query count | 2 queries for 403 people (measured) | unchanged at 400 seats | Assertion in the test suite |

### 078C — Documents (recommend: after `01c`)

Scope, measures and the narrowing I recommend are in ⚠ DECISION 3 and §8. Nothing is
specified here until security has written `01c`, because the enforcement point does not
exist yet.

**Why this is three complete slices and not one slice with two phases.** 078A gives an
employee a finished outcome and a visible result the same day, with no dependency on
078B. 078B gives HR a finished outcome whether or not any photo exists — the mini profile
is useful with initials. 078C gives HR a finished outcome on its own. 079 gives a joiner
a finished outcome whether or not any of the other three exist. None of them is half of
another, and none needs a phase 2 to be right.

**Out of scope for all of 078:** the pre-onboarding link, in every form. It is slice 079.

## 8 · Regulatory read

1. **Which regime.** India's **DPDP Act 2023** (DPDP Rules notified 14 Nov 2025, phased
   to roughly May 2027). A facial image is personal data; the 15 identity and statutory
   document types in 078C are the most sensitive data in this product. No AI regime is
   engaged, and nothing here may create a path to one.
   **079 adds a second regime question:** personal data collected from someone who is
   **not yet an employee**, over a public channel. There is no employment relationship to
   rely on, so the lawful basis is almost certainly **notice and consent**, and the data
   needs a **stated retention period and a deletion job** for joiners who never arrive.
   CERT-In's logging duties also become more real once an endpoint is open to the
   internet.
2. **Whose obligation.** Our **customer's** — the employer is the Data Fiduciary for its
   employees. What we are building helps them discharge it: a short curated field list, a
   server deny list no tick can override, and a plain sentence next to the upload. That
   is the version that wins a security review. *I am not a lawyer.*
3. **What becomes newly possible.** (a) An employee's face is shown to colleagues — a new
   use of their image. (b) Personal fields become visible on a page whose audience is a
   tenant permission tick, not a fixed role. (c) 078C would make identity documents
   reachable from a structure page. Each is a compliance event and security turns it into
   `SEC`/`PRIV` requirements next.
4. **The honest downside.** 078A and 078B I would defend on a front page without
   hesitation. **078C as asked — all 18 types, including Aadhaar, PAN, bank proof and
   police verification, on the org chart — I would not.** It is defensible narrowed to
   Company Issued types, HR-only, behind a server endpoint. That is what I recommend.

⚠ **COMPLIANCE, 079:** the consent wording on the public form, the retention period for a
submission from someone who never joins (⚠ DECISION 13), and whether a public endpoint
accepting identity documents changes our breach-notification posture. Owner: **Surbhi,
with `hrms-security-privacy-engineer`, and a question for counsel.** Blocks: building 079
at all. *I am not a lawyer and neither is any agent here.*

⚠ **COMPLIANCE, one sentence in the privacy notice before the first photo is collected.**
Owner: **Surbhi, with `hrms-security-privacy-engineer`.** Draft: *"The photo on your
record is shown next to your name on the organisation and positions charts to colleagues
who can see you."* Blocks: switching 078A on at a tenant.

**Refusals, written down so they cannot arrive later.** A photo collected here is never
matched, compared, scored or used to confirm who checked in. The field app's check-in
photos are never reused as profile photos — they were collected as attendance evidence
and the retention rules differ. No emotion or facial analysis, ever.

## 9 · Risks, red-teamed

| Risk | What breaks | Cheapest way to find out first |
|---|---|---|
| **Nobody uploads a photo** | 078B's whole benefit is zero and 078A looks like a wasted release | Ship 078A to one DTC branch and count photos after seven days. This is the kill criterion |
| **10× the data** | 400 faces on the chart is ~400 Python-served requests through 8 slots. At 1,000 employees it is 1,000. The site stalls for everybody, including check-ins | Already measured by DevOps. It is the reason for ⚠ DECISION 2 |
| **A phone photo is 3–8 MB** | Multi-megabyte originals in the sites volume, in every deploy backup, for ever. `max_file_size` is unset on the bench | Resize and convert on upload — one hook, in 078A, not optional |
| **A PNG or HEIC selfie keeps its GPS** | A staff photo carrying the location of someone's home | Converting to JPEG at a fixed size strips it as a side effect. No second mechanism |
| **An unsuitable photo is uploaded** | A support ticket and an embarrassment | **No build.** HR can already replace or clear `Employee.image` in Desk, and the chart says whose it is. Named so nobody builds a moderation queue |
| **A wrong tick is a disclosure** | HR ticks bank account or date of birth onto a page the tenant opened to managers. Frappe's levels lock **write**, not read (`employee_field_rights.py` — deliberate) | The curated list **and** a server deny list that refuses an off-list field even when posted directly. Security owns the list in `01c` |
| **The child-table trap, again** | 078C's ticked-types rule is decoration: `Employee Document`'s attachment belongs to the **Employee**, so Frappe asks the parent's read permission. This is ALV-256, two days old | Do not ship 078C without a server endpoint that streams the file and checks the type |
| **The employee leaves mid-flow** | A mini profile opened from a historical view shows a former employee as current | `01a` §9 already lists the state; the spec must carry it |
| ~~Who can open Positions is unverified at DTC~~ | **Answered 31 Oct 2026: HR Manager at DTC.** Wider than the demo copy, narrower than "every manager". Security should still see the role list in `01c` | Done |
| **079: a public form is abused** | Spam submissions, 50 MB uploads (nginx's body limit, and `max_file_size` is unset), malware in a file, or a forwarded link used by a stranger | The tokenised invite (⚠ DECISION 11) removes most of it before any rate limit is written |
| **079: a submission becomes an Employee with a back-dated joining date** | **Frappe marks the person Absent for every day since, and deleting the rows does not fix it** (logged, DTC) | HR reviews and sets the joining date on the Employee — never the joiner, never the form |
| **079: data about people who never join piles up for ever** | A DPDP problem and a growing pile of identity scans nobody owns | ⚠ DECISION 13: a stated period and a deletion job, with counsel's number |
| **The release serves the old file** | `portal.js` and `panels.css` change, and the sites volume shadows them | Known: asset refresh plus an `assets.json` bump (OPS-9) |

## 10 · Thriving-workplace check

- **Engagement** — 078A gives an employee agency over their own record for the first
  time: their face, their number, their password, without asking permission.
- **Collaboration** — a face next to a name on the Organisation chart makes "who do I
  talk to in Finance" answerable by the person who needs the answer.
- **Inclusiveness** — the risk sits here. A frontline worker on a cheap Android with a
  poor network must be able to upload a photo in under a minute, in Hindi, with 44 px
  targets. Anyone with no camera, or who does not want to be photographed, keeps their
  initials and loses nothing — that is why initials stay the only fallback. **079 is the
  harder case:** a joiner filling a form on someone else's phone, in Hindi, who may not
  be able to scan a document — so the form must accept a photograph of a document, and
  "I will bring it on day one" must be a valid answer to every upload.
- **Transparency** — it makes visible who sits in which seat, and (078B) a short list of
  work facts the tenant chose. It must **not** make visible pay, bank details, identity
  numbers, date of birth, home address or personal contact details. The deny list is a
  server rule, not a short list in the browser.

## 11 · The pre-onboarding link — new scope, and why it is its own slice

**Arrived after the first draft of this brief.** Your words: *"we need to prepare some
public link for the new joiners to enter their details on their own, till the time they
have their own user-id and login… the same page of organisational settings can be reused
to choose which fields to be enabled for them. Also including the documents to be
uploaded."*

**My recommendation: build it, as slice 079, after 078A — and do not share the settings
screen.**

### 11.1 Why not one slice with 078

| What they share | Does it hold up? |
|---|---|
| "The same settings page, a third list" | **No.** A Frappe **Web Form** is itself a configured field list with a public route and a login switch. This repo already ships a working public one (`job_application`, `login_required: 0`, confirmed). Building our own third picker for it means maintaining two field pickers for one form |
| "It is also about which fields and which documents" | Only in words. 078's lists answer *what may a signed-in reader see* and *what may an employee change about themselves*. 079's list answers *what must a stranger send us*. Different question, different audience, different enforcement |
| The audience | 078 is signed-in people inside one tenant. **079 is the open internet.** No login to check, a link that can be forwarded to anyone, and a file upload endpoint a stranger can reach |
| The record | 078 reads and writes an existing `Employee`. **079 has no Employee yet** — a joiner is not an employee until HR says so |

A slice that fully works for the joiner is worth more than one that half-works for three
audiences. Separate.

### 11.2 The ladder, and the one rung I am recommending we climb to

| Rung | Option | Verdict |
|---|---|---|
| 1 · already there | `Employee Onboarding` + `Employee Onboarding Template` (Frappe HR) | **Rejected, and this is worth knowing: it is a task checklist, not a form.** It tracks what HR must do and creates the Employee from a `Job Applicant`. It never asks the joiner for anything |
| 1 · already there | The shipped `job_application` Web Form | Rejected: it is recruitment, it writes `Job Applicant`, and its fields are a job application |
| 2 · **configuration** | **A Web Form with `login_required: 0`, over a doctype, with the document types as attach fields** | **Recommended for the form itself.** It brings the public route, the field builder, the file upload, the success message and the mandatory-field handling with it. We write none of that |
| 3 · customisation | A Web Form straight onto **`Employee`** | **Rejected, firmly.** A guest-writable Employee means strangers creating records in the HR master, consuming the naming series, and — because a joining date can be back-dated — **tripping the absence-backfill trap: Frappe marks the person Absent for every day since, and deleting the rows does not help** (memory, logged). Never |
| 4 · new code | A guest-allowed page that checks a one-time token before showing the form | **Recommended as the door**, see 11.3 |
| **5 · new DocType** | **One doctype to hold a joiner's submission until HR turns it into an Employee** | **Recommended, and it is an exception I have to justify.** A Web Form needs a doctype, `Employee` is refused above, and no shipped doctype means "a person who has told us about themselves but is not yet an employee". It also gives the submission somewhere to be reviewed, and somewhere to be **deleted** when the joiner never turns up |
| 6 · new app | — | Rejected |

So 079 is: **one small DocType, one Web Form, one tokenised link, and one HR screen that
turns a submission into an Employee.** That last step must stay a human action — HR
reads what a stranger sent before it becomes a personnel record.

### 11.3 The decision I would not leave to the build

**An open public form that accepts Aadhaar and PAN scans from anyone on the internet is
not something I would defend on a front page.** The alternative is barely more work: HR
clicks "invite" on the joiner, the system emails or WhatsApps a **link with a one-time
token** that expires, and the form only opens for that token. One field on the doctype
and one check in the page. It also ties each submission to a joiner HR actually expects,
which removes the review queue's worst problem — telling a real joiner from spam.

⚠ **DECISION 11** below. My recommendation is the tokenised invite.

### 11.4 What this adds that nothing else in 078 does

- **A new joiner arrives with a photo already on file.** 079 is the long-term answer to
  the 0-of-403 problem; 078A is the answer for the 403 who are already here.
- Risks that are new to this product, each needing `01c` and a DevOps section of its own:
  a public endpoint that writes to the database; file uploads from unauthenticated
  callers (nginx allows 50 MB bodies, and `max_file_size` is unset on the bench); spam
  and storage flooding; malware in an uploaded file; a forwarded link; and **personal
  data held about a person who may never join**, which needs a stated retention period
  and a deletion job. ⚠ COMPLIANCE, below.
- It is the only part of this whole idea where **consent is plainly the lawful basis** —
  there is no employment relationship yet. That is a question for counsel, not for me.

## 12 · ⚠ DECISIONS — yours, with my recommendation beside each

| # | Decision | My recommendation |
|---|---|---|
| **1** | **One slice, or several?** | **Three here plus one elsewhere: 078A, then 078B, then 078C, with the pre-onboarding link as its own slice 079 after 078A.** 078A first, because it is the only one that makes anything visible and the only one that serves the employee |
| **2** | **Faces on the chart cards.** Three priced options: **(a)** no faces on cards, initials as today — faces in the mini profile, the seat tray list, the "Change this seat" dialog and the Organisation page. Cost: nothing. **(b)** faces on cards from a stored 48 px thumbnail: ~1.3 MB and **~400 Python-served requests** per page open, ~27 s on slow 3G against a 2.5 s budget; cost ~30 lines in an upload hook plus a one-off pass over existing photos; the request count is the real risk, not the bytes. **(c)** 48 px thumbnails sent **inside the one payload the chart already fetches** — zero extra requests, payload grows from 11 KB to roughly 1.4 MB. `Needs validation`: neither input document costed this; the engineer would price it at the strategy gate | **(a) for now.** Then look at the photo count after 30 days of 078A: if most people have a photo and you still want faces on cards, ask the engineer to price (c) against (b). Option (b) trades a slow page for a site-wide capacity risk, which is the worse of the two |
| **3** | **Documents.** You chose "include them, HR-only", knowing 15 of 18 types are identity, statutory, financial or background-check | **Keep them, but as 078C, narrowed and after `01c`:** Company Issued types only, HR Manager by role (the 065 gate), the 065 hide-before-screen-share link, never printed, no inline preview, and a server endpoint that streams the file and checks the type. If you want all 18 types, say so and security will write the requirements for all 18 — but it cannot ship alongside 078B, because the enforcement point does not exist yet |
| **4** | **The Organisation page will show faces to every employee**, from the same photos, with no extra code | **Accept it on purpose**, and say it in the privacy sentence. It is 078A's visible payoff |
| **5** | **Faces in print** — Ctrl+P and the wall chart | **Off for Ctrl+P.** The wall chart is your call: recognising a manager may be the whole point, and a customer walks past that wall |
| **6** | **The Positions candidate list.** My proposal: job role, department, branch, company, reports to, grade, employment type, date of joining, default shift, work email, work phone — eleven, read-only | Approve the eleven, and let security add the server deny list (pay, bank, statutory IDs, date of birth, personal contact, home address, emergency contact, marital status, blood group, relieving date, and every field a payroll rule set names) |
| **7** | **The My Profile list.** My proposal: mobile number, personal email, current address, emergency contact name, relation and phone — six, read **and write**. Plus the photo, which is always on and not a ticked field | Approve the six. **Leave blood group and marital status out** — health and family data, and no screen needs them. Note the permissions are already right: these are permlevel 0, and `employee_field_rights.py` already refuses levels 1 and 2 on a person's own record, so **no new permission code is needed** |
| **8** | **Why two lists and not one.** They answer different questions — "what others see about you" (read-only, includes job fields) and "what you may change about yourself" (level-0 only) | **Two lists, one card**, as you asked. One list cannot serve both without letting a tick on a job field become an employee edit |
| **9** | **Who may change the lists** | **System Manager only, with a `Version` record of every change** — join the existing `ACCESS_GRANTING` set in `settings.py`, which already does exactly this for the reach settings. These keys decide who sees whom |
| **10** | **May an employee hide their own photo?** 076 set the precedent for birthdays | **No opt-out.** A face beside a name on an internal chart is ordinary and a patchy chart helps nobody. The precedent exists, so it is your call with security, not mine |
| **11** | **Pre-onboarding: an open public link, or a tokenised invite that expires?** | **Tokenised invite.** Roughly one extra field and one extra check, and it keeps identity documents from being uploadable by anyone who finds or is forwarded the link |
| **12** | **Does the pre-onboarding field list live on the Organisation Settings card, as you asked, or in the Web Form's own field builder?** | **The Web Form's own builder.** It is the cheaper rung and it already exists. If you want it on the settings card anyway, say so — it is roughly a week of work that buys a second way to do one thing |
| **13** | **How long do we keep a submission from someone who never joins, and who deletes it?** | My recommendation is a stated short period — **90 days, then deleted automatically** — but this is a legal question about data from a non-employee and **counsel must set the number.** It is a question, not a recommendation I can stand behind |

## 13 · Subtract pass — what I removed

Read back once, asking only what can be deleted:

- **A password form in My profile.** Removed. `/update-password` already exists, already
  checks the old password and strength, and our wrapper already lands the user back in
  the portal. **A link is the whole feature.**
- **A separate EXIF-stripping step.** Removed by merging: converting the upload to JPEG at
  a fixed size does the resize and the metadata strip in one call.
- **Any new permission mechanism for My Profile edits.** Removed. Permlevel 0 is already
  employee-writable, and locked fields are already refused on your own record.
- **A thumbnail, in 078A.** Removed. The Organisation page shows about five boxes, so a
  single resized photo is enough. The thumbnail only earns its place if you choose
  chart faces (⚠ DECISION 2), and then it belongs to that decision.
- **Faces in the Positions table, the zoom rule, a new settings page, a new DocType per
  chosen field, a photo moderation queue, a photo opt-out, an audit log of profile
  opens, an "export the chart with faces" action, an approval workflow on self-service
  edits, and a WhatsApp photo-collection path.** All removed, none asked for.
- **A fourth slice for the drawer's accessibility.** Removed — it rides inside 078B,
  because the drawer is the thing 078B opens.
- **My own first instinct: a "profile completeness" nudge on Home.** Removed. There is no
  evidence it works and it is a second surface for a one-tap job.

**Removed on revision 2, after the pre-onboarding scope arrived:**

- **The third list on the Organisation Settings card.** Removed. Frappe's Web Form owns
  its own field list; a second picker is two mechanisms for one rule. This is the single
  largest saving in the brief — roughly a week of work that buys nothing.
- **A pre-onboarding "portal" for joiners** — a login, a progress tracker, a task list, a
  chase reminder. Removed. One form, once, then HR reviews it. `Employee Onboarding`
  already holds HR's own checklist if they want one.
- **Any automatic creation of an Employee from a submission.** Removed deliberately: HR
  reads what a stranger sent before it becomes a personnel record, and the
  absence-backfill trap makes an automatic joining date actively dangerous.
- **A spam/CAPTCHA/rate-limit design of my own.** Removed: the tokenised invite makes
  most of it unnecessary, and the rest is DevOps' and security's to specify, not mine.

What I did **not** remove: the preview button on the setup card. It is the one thing a
competitor is not doing, and Zoho's own users prove what happens without it.

---

## Open questions

**Must know — these block starting.**

| # | Question | Owner | Blocks |
|---|---|---|---|
| ~~Q1~~ | ~~Do any employee photos exist at DTC?~~ **Answered: none, "but they will upload it."** Self-service collection is confirmed, and 078A is confirmed as the first slice | — | closed |
| ~~Q2~~ | ~~Who can open Positions at DTC?~~ **Answered: HR Manager** | — | closed |
| Q3 | ⚠ DECISIONS 1, 2, 3, 11 and 12 above | Surbhi | The whole shape of the work |
| Q7 | **079: who sends the invite, and over what?** Email, or WhatsApp (where DTC's owners actually live)? My reading is email, because that is the only channel this product has | Surbhi | 079's design, and whether it needs anything beyond a copyable link |
| Q8 | **079: what is the retention period for a submission from someone who never joins?** ⚠ DECISION 13 | Counsel, via Surbhi | Building 079 at all |

**Should know.**

| # | Question | Owner | Blocks |
|---|---|---|---|
| Q4 | **Somebody with a login must capture Positions and My profile at 1440 × 900 and 390 × 844** into `C:/Surbhi-Git/hrlocal-data/ux-review/<date>/`. This is the **fourth consecutive slice** on this page with no screen seen in a browser | Surbhi | `01b`'s design quality |
| Q5 | May the My Profile write list ever include a permlevel-1 or 2 field? My reading is no, and the server already refuses it | `hrms-security-privacy-engineer` | `01c` |
| Q6 | Is `BACKUP_BUCKET` set? It decides whether every photo also leaves the server on every deploy | Surbhi | Nothing in the build; the privacy notice's accuracy |

**Nice to know.** Whether the ~16 MB of photos per tenant changes the deploy disk gate
(DevOps says no: +10% on a 169 MB volume).

## Assumptions

- `[ASSUMPTION]` DTC is roughly PPJ's shape — about 400 seated people. DTC's own seat
  count was not read.
- `[ASSUMPTION]` ~40 KB per stored photo after resize; the true spread is 20–200 KB
  (DevOps' basis: Frappe resizes only above 200 KB).
- `[ASSUMPTION]` Most DTC staff have a phone with a working camera. If a large share do
  not, 078A's 60% target is wrong and initials carry more of the chart than planned.
- `[ASSUMPTION]` Employees will accept their face on an internal chart without an
  opt-out. ⚠ DECISION 10 is where you overrule me.
- `[ASSUMPTION]` No customer has asked for any of this in writing. If a demo note or
  ticket exists, it would change the Kano classes in §4 from proxy to evidenced.
- `[ASSUMPTION]` Positions is a laptop page for HR and owners, so the 3G budget binds
  078A and the Organisation page, not 078B.
- `[ASSUMPTION]` 079's volume is small — a handful of joiners a month per tenant, not
  hundreds. If a tenant onboards 50 people in a week the review step needs rethinking.
- `[ASSUMPTION]` A Web Form with `login_required: 0` is acceptable to our security
  reviewers at all. Confirmed only that Frappe ships one; **not** confirmed that we are
  willing to expose one. If the answer is no, 079 stops at the gate, not at the build.

## Kill criteria

- **Kill 078B's chart faces** if fewer than 20% of active employees have uploaded a
  photo 30 days after 078A is switched on at one tenant.
- **Kill 079** if counsel will not set a retention period, or if security concludes a
  public unauthenticated upload endpoint is not acceptable on this stack. Both are
  answerable before a line is written, and both are cheaper to find out now.
- **Kill 078C** if the server streaming endpoint with the type check cannot be built and
  tested in about a day. HR already has the documents in Desk; a second door is not worth
  a week.
- **Stop the whole idea** if security concludes in `01c` that the mini profile cannot be
  scoped to a safe field set on a page whose audience is a tenant tick.

## Handoff note

To **`hrms-ux-designer`** (`01b`): design **078A first** — the photo upload and the six
editable fields in the existing My profile panel, phone-first, Hindi at parity, with the
one-sentence privacy line and the link to `/update-password`. The prototype is mandatory,
and Q4's screenshots should come before it. Do not design the Positions mini profile until
⚠ DECISIONS 1–3 are answered, and do not design chart-card faces unless ⚠ DECISION 2 says
(b) or (c).

To **`hrms-security-privacy-engineer`** (`01c`): three things are yours and one of them is
the reason 078C is a separate slice. The field deny list for the Positions profile (read is
open on Employee; Frappe's levels will not save us). The privacy sentence and when consent
is or is not the right basis. And the `Employee Document` child-table trap — the ticked-types
rule is cosmetic until a server endpoint streams the file, and that is ALV-256 restated.

To **`hrms-devops-engineer`** (§3): the resize-and-convert-on-upload hook in 078A is the
one new mechanism I am proposing, and it exists to satisfy OPS-7 and OPS-8 in one call. If
⚠ DECISION 2 goes to option (c), please cost thumbnails carried inside the existing payload
against OPS-2 — I have marked it `Needs validation` because neither of us has measured it.

**On 079, to everyone:** nothing in it should be designed, specified or built inside this
slice folder. It needs its own `01a`, its own `01c` and its own DevOps section, because it
is the first public unauthenticated write endpoint in this product. If Surbhi says build
it, open `docs/slices/079-pre-onboarding-link/` and start at step 1.

**Where I disagree with my inputs:** nowhere on the facts. Two differences of emphasis.
On the settings screen, Surbhi asked for the pre-onboarding list on the Organisation
Settings card and I am recommending the Web Form's own builder instead — ⚠ DECISION 12,
hers to overrule. One difference of emphasis —
UX recommends documents are out, you have decided they are in. I have carried your
decision and recommended the narrowing and the sequencing rather than re-arguing the
refusal, because HR-only behind a real server gate is a defensible version of what you
asked for.
