---
slice: 083-joiner-form-fields
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-11-16
status: draft
inputs: [Surbhi's request 14 Nov 2026, docs/slices/079-pre-onboarding/00-decisions.md, docs/slices/078-positions-faces/01-product-brief.md §11, source read of joiner_public.py / people_settings.py / people_fields.py / alvoraa_joiner_submission / joining.html / employee_field_rights.py / event_form.py]
supersedes: the 16 Nov 2026 draft written against a stale checkout
---

# 083 · More fields for the joiner, and documents that actually get asked for

## The headline: almost all of this is already built, and the real fault is one shared tick

**Your three asks are not three gaps. They are one configuration step, one coupling fault,
and one closed list you may want to open a little.**

I have now read the real code. The joiner form is a complete, careful, shipped feature that
has never been switched on. Of the three things you asked for:

| Your ask | What I found | What is actually missing |
|---|---|---|
| "allow System Admin to allow as many fields as they want" | **The picker is built.** A System Manager ticks which details the joiner is asked for, and a second tick inside it marks each one "must fill in" (079 decision 5) | The **candidate list is six fields** — and those six are shared, by identity, with My Profile. Widening it is a real decision, not a setting |
| "with some warnings on a few sensitive fields" | **The warning is built, for documents.** Ticking an Identity, Statutory, Verification, Employment or Address document type shows a standing amber line on the card (AC-84) | Nothing for *fields* — because today no sensitive field can be ticked at all. The warning becomes necessary only if you widen the list |
| "allow to upload document which is not happening at present" | **The upload is built, and it is thorough.** `upload_invite_file`: session first, magic bytes not file extension, re-encode to strip the photo's location data, per-joiner file and byte caps, private files, our own serving endpoint | **The joiner is offered a document only if a System Manager ticked that type on the Positions card** — a setting whose other job is publishing staff documents on the profile page. Nobody has ticked any, so the joiner's document screen is empty. **That is why it "is not happening".** |

**The one thing I would fix even if you dropped the rest of this brief.** The joiner's
document list and the staff profile's document list are **the same tick**
(`alvoraa_positions_document_types`). So to let a joiner send you an Aadhaar card, a System
Manager must tick "Aadhaar card" — and that same tick puts your existing staff's Aadhaar
cards one click from a structure page. **Confirmed:** `joiner_public.py:191 _document_types`
and `employee_documents_read.py:60 ticked_types` read the same key. You cannot ask a joiner
for a sensitive paper today without also publishing your employees' copies of it.

Your own team already wrote down this exact lesson: *"When one setting feeds two surfaces and
one of them is public, split the tick before you improve the warning"* —
`.claude/context/ux-learnings.md`, from slice 078 v5. It was applied to a different pair of
surfaces. Here is the same shape again.

### What I could not check

- **ALV-343 (the CSRF fault).** I searched the whole tree: **no trace of ALV-343 anywhere**,
  and no sign of the fault in the code. `joining.html:318` has a `csrf()` function that reads
  `window.frappe.csrf_token` and falls back to the `csrf_token` cookie, and the page now
  requires a session, so a signed-in joiner should have that cookie. I cannot say the defect
  is not real — only that I could not find it or its fix in this tree. **Someone must prove
  the form works end to end on a real phone before any of this is worth building.** That is
  a gate, not scope.
- **Whether the form is switched on at any tenant.** `alvoraa_joiner_form_on` ships off and
  `joining.py` says so. I cannot read tenant data.
- **Demand.** Nobody has asked us for more joiner fields except you. No customer evidence
  exists, because the feature has never been on.

---

## 1 · The job to be done

> "I have hired someone. I want their details and their papers before they walk in, and I
> do not want to type it all myself." — the **HR Manager**.

The three asks are all made by the **System Manager** (who ticks) on behalf of the **HR
Manager** (who lives with it), and are paid for by the **joiner** — a person with no
employment relationship, no reason to trust us, and, now, a login that opens one page and
nothing else.

For the **CXO** and for existing **employees**, nothing changes — *unless* we leave the
shared document tick as it is, in which case employees lose privacy to serve joiners. That
is the "quietly harms another persona" test, and today's build fails it.

## 2 · The pain, as a story

A System Manager at DTC ticks the fields, types the notice, sets the two retention numbers
and the HR phone number, switches the form on, and sends the first joiner their sign-in. The
joiner signs in, reads the notice, answers up to six questions, reaches **"Your documents"**
— and the screen is empty, because no document type is ticked. They reach **"Your photo"**,
send one, press **Check and send**, and HR receives a name, a mobile number, an address and
an emergency contact. HR then types the date of birth, the gender, the surname and the
permanent address off a WhatsApp photo, exactly as before.

**No numbers. The feature has never been on at any tenant.** Every baseline below is
"measure the first twenty".

## 3 · What the whole products do

All **read, 16 Nov 2026**, from each vendor's own help centre. Update dates vary from 2024 to
mid-2026 and behaviour varies by plan, so treat the detail as directional.

| Capability | Keka | greytHR | Zoho People | Darwinbox | Frappe HR | Us, today |
|---|---|---|---|---|---|---|
| A portal for someone who is not an employee yet | Candidate Portal | Self-onboarding | Separate portal, no People access, link up to 120 days | Pre-joining phase | `job_application` Web Form only | **A restricted login that opens one page** |
| Admin picks which details the joiner fills | Yes — "Profile Field Task" templates over profile fields | Partly — mandatory ticks, and a short named list of custom fields (a June 2025 release added exactly two: Hobby, Caste) | Yes — a Candidate form plus per-field permissions plus a mapping step | Yes — "customize data fields by country" | No | **Yes, over six fields** |
| Admin picks which documents are required | Yes, per candidate | Yes — document types with a Mandatory tick | Yes | Yes, per country and role | No | **Yes — but the tick is shared with the staff profile** |
| Joiner uploads a file | Yes | Yes | Yes (a known third-party-cookie fault) | Yes | Web Form attachments | **Yes, and more carefully than any of them** |
| Strips the photo's location data on upload | Not stated | Not stated | Not stated | Not stated | No | **Yes** |
| Deletes a non-joiner's papers sooner than their record | Not stated anywhere | Not stated | Not stated | Not stated | No | **Yes — two clocks** |
| Warns the admin that a field or document is sensitive | **None of the four, as far as I can find** | — | — | — | — | **Yes, for documents** |

**Where we already win, and it is not the field count.** Two clocks, EXIF stripped, a login
instead of a forwarded link, an export that is masked with no unmasked version at any
permission level, and a real erase that also sweeps `tabVersion` so the audit history does
not keep the data we said we deleted. None of the four vendors documents any of that.

**What we will deliberately NOT do, and why it makes us better.**

1. **"As many fields as they want."** We will not offer an open field list. Every field on the
   joiner's picker is a column a not-yet-employee can write. A long list is a long row of
   stranger-supplied personal data attached to a person who may never join. Keka and Zoho let
   an admin invent fields; their own help centres have pages about fields going missing
   between the candidate form and the employee record. We offer a short, closed list where
   every answer has somewhere real to land.
2. **No typed statutory or bank field, ever.** Already settled (079 §6, and the `NEVER` deny
   list in `people_fields.py`). An identity number arrives as a *document* under HR's
   verification flow, never as a searchable column. Slice 082 holds the same line on its
   public form: a regex refuses any field named for aadhaar, pan, passport, voter, bank,
   ifsc, health, religion or caste, in English and Devanagari. **Confirmed:**
   `event_form.py:94`.
3. **No masker, and no promise of one.** Settled 2 Nov (079 §6c, §6d): the joiner is told to
   download **UIDAI's own masked Aadhaar** and upload that. The weakness is written down
   already — guidance is an instruction, not a lock.

## 3a · Three ways to do it

| | What it is | Rung | Verdict |
|---|---|---|---|
| **Conventional** | A new per-field builder over all of `Employee`, a joiner document picker, field-level warning dialogs | 4–5 | Rebuilds a picker that exists and re-opens decisions 079 settled. No |
| **Better** | **Give the joiner's documents their own tick, and add five fields to the candidate list.** Reuse the picker, reuse the amber line, reuse both clocks | 2–3 | **My recommendation** |
| **Reimagined** | Drop the field list entirely: HR types a draft from the offer letter, the joiner corrects it (`joiner_to_employee.py` already prefills HR-side) | 4 | Honest, but it does not answer the ask and it adds an HR step |

**Could we not build this at all?** For ask 3, **very nearly yes.** Tick some document types,
set the four values, switch the form on, and the upload works today — that is a screenshot,
not a slice. The only reason it is not purely configuration is the shared tick, which turns a
configuration choice into a privacy decision about your existing staff. That coupling is the
build.

## 4 · Kano class

**Proxy, not survey.** No survey data exists and I will not invent any.

| # | The ask | Class | Why | What would change it |
|---|---|---|---|---|
| 1 | The joiner's documents get **their own tick** | **Must-be** | Every competitor separates "what we ask a candidate for" from "what we show about staff". Ours does not, and the consequence is a privacy coupling, not a missing feature | Nothing |
| 2 | **Five more fields** on the candidate list | **Performance** | Buyers compare on how complete the joining record is. But six fields already covers contact and next of kin; the next five save HR typing, they do not win a deal | A lost deal naming the field list. Then it is Must-be |
| 3 | A **warning on a sensitive field** | **Attractive** | I can find no competitor that warns the admin at tick time. It helps the *employer* discharge their own duty, which is what wins a security review. And we already have the pattern | Tenants reading it as noise. Then it is Indifferent and we delete it |
| 4 | "**As many fields as they want**" | **Reverse** | A free field list on a stranger-writable record trades the joiner's privacy for the admin's convenience. `product-context.md` §6 already refuses that shape of trade | Nothing. I will not recommend it |
| 5 | An **Aadhaar masker** | **Already decided: not built** | 079 §6c and §6d. Guidance plus UIDAI's masked download | Counsel saying guidance does not satisfy ruling 5. ALV-215 |

## 5 · Persona enhancements

There is no `01a` for this slice, so these are my ideas, not the designer's.

| Persona | The idea | The job it serves | In this slice? | Why |
|---|---|---|---|---|
| **System Manager** | A separate "documents to ask a joiner for" tick, with its own amber line | "Ask for the Aadhaar card without publishing my staff's" | **Yes — this is the slice** | It is the fault |
| **System Manager** | A live line as ticks change: how many questions and how long on a phone | "What am I asking of this person?" | **Yes** | One line of copy and arithmetic. §6 |
| **The joiner** | Five more questions, each one a thing only they know | Fewer WhatsApp exchanges with HR later | **Yes, if you accept §8** | Five, not nineteen |
| **The joiner** | A grey line per sensitive group: who reads it, how long it is kept, that it may be left blank | "Why does a stranger want this?" | **Partly — already built for documents** | The notice screen already carries "What we will ask for" and "What happens to what you send" |
| **HR Manager** | The five new answers copy onto `Employee` at accept | Stop retyping | **No — and say why** | `joiner_to_employee.py` copies six columns under 082-SEC-4. Widening the copy is a *second* decision with its own security review. The five fields reach HR as answers she can read and type once |
| **HR Manager** | "Who has not finished their form" | Chase three, not thirty | **No** | Desk lists the submissions by status today |
| **Line manager** | "Your new person has finished" | Day-one readiness | **No** | Hands a manager a joiner's record. Least privilege says no |
| **Frontline joiner** (Hindi-first, cheap phone) | Hindi | "I cannot read this" | **No — and it is the biggest gap in the whole feature** | ALV-267. 151 strings are already wrapped; only a reviewed `hi.csv` is missing. It is not this slice, and it matters more than five fields |
| **CXO** | Nothing | — | **No** | — |

## 6 · The WOW

**Where:** the people-settings card, the moment a System Manager ticks a document type in the
new joiner-only picker.

> **Joiners will be asked for this.** Your own staff's Aadhaar cards stay off the profile
> page.
>
> *(and under the field ticks, live)*
> A joiner will answer 9 questions and send 2 papers. About 5 minutes on a phone.

Why it is the WOW: the first line is the fix made visible. Today the honest version of that
sentence would be *"and your staff's Aadhaar cards will appear on the profile page"* — which
is precisely why nobody has ticked anything. The second line tells an admin what their
configuration costs the other person, in that person's time, before they save. Both are copy
and arithmetic over data the card already holds. No new screen, no new component.

## 7 · How many slices, and which first

**Two small slices, after one configuration step that needs no build.**

| Order | What | Why here |
|---|---|---|
| **Step 0 — no build** | Prove the form works end to end on a real phone (the ALV-343 question). Then at one tenant: (`log_level` cannot be set and is not needed: exports and purges are rows in `Alvoraa Photo Access Log` since ALV-353) type the notice, set the two clocks and the HR contact, tick the document types, switch the form on. **Take screenshots** | Most of ask 3 is answered here. The honest claim now is "each export THROUGH THE PRODUCT writes a row naming the user, time, record and whether it was masked" (ALV-353, `Alvoraa Photo Access Log`; a System Manager can still export from Desk, ticketed), not "every export is logged" (setting `log_level` was never a real fix) |
| **083 — split the tick** | One new setting for the joiner's own document types, defaulting to empty; the Positions tick keeps its own meaning; the amber line on the new picker; the WOW lines | **Must-be, and a privacy fix.** Smallest useful thing. Stands alone: the outcome is "HR can ask a joiner for a paper without exposing colleagues' copies" |
| **084 — five more fields** | Break the joiner list's identity with My Profile, add five fields, extend the amber line to sensitive field categories | Performance, not Must-be. It re-opens a deliberate 079 design choice, so it deserves its own security review rather than riding along |

**Do not do them as one slice.** They look adjacent and they are not: 083 changes who can see
an existing employee's papers; 084 changes what a stranger may write. Different audience,
different enforcement, different review.

**The piles.**

- **Needed to validate now:** the joiner's own document tick; its amber line; the two WOW
  lines.
- **Needed before it can ship:** proof the form works on a phone. Exports logged as `Alvoraa Photo Access Log` rows (ALV-353; `log_level` is not a real setting). A test that
  a type ticked for joiners does **not** appear on the staff profile surface, and vice versa.
- **Worth doing later:** the five fields (084). Hindi (ALV-267 — worth more than 084).
  Widening the accept-time copy to `Employee`.
- **Not doing:** an open field list. Any typed statutory, bank, pay or health field. A
  masker. A new settings page. A new DocType. A manager notification. A "who has not
  finished" screen.

**Out of scope, plainly:** the login, the invite, the clocks, the erase job, the export, the
notice text, `joiner_to_employee.py`. All built; all working; leave them alone.

## 8 · The field list — five, not nineteen

**The constraint, confirmed in source.** `people_fields.py` holds one candidate list used by
three ticks **by identity, deliberately** — My Profile, the joiner's asked list, the joiner's
required list — *"so a third candidate list cannot appear and drift away from the one the code
actually allows"*. It is six fields: `cell_number`, `personal_email`, `current_address`,
`person_to_be_contacted`, `relation`, `emergency_phone_number`. Beside it sits a named deny
list, `NEVER`, covering pay, bank, `pan_number`, `esi_number`, `provident_fund_account`,
`date_of_birth`, `marital_status`, `blood_group` and health.

So **"as many fields as they want" cannot be granted without breaking that design**, and I am
not recommending it. What I recommend instead, for slice 084:

| Field on `Employee` | Why it earns a place | Level today | Risk |
|---|---|---|---|
| `middle_name` | HR has one `full_name` typed by HR, and the joiner can correct it. The name on the payroll should be the name the person gives | 2 | None |
| `last_name` | same | 2 | None |
| `permanent_address` | Only the person knows it. Needed for statutory filings and for post | — | Low |
| `gender` | **`Employee` cannot be created without it.** Today HR guesses or asks on WhatsApp | 2 | A protected attribute. Asked by every competitor. Must be optional and must carry the grey line |
| `date_of_birth` | Needed for the record, for EPF/ESI eligibility, and for the birthday feature | 2 | **The judgement call.** It is on the `NEVER` list. It is also the single field HR most often retypes |

**Five. That is the whole widening I will recommend.** Note that `gender` and `date_of_birth`
are **permission level 2** — HR writes them, an employee cannot. That is exactly right for a
joiner: they *tell* HR, and HR writes. The route preserves the control instead of bypassing
it, because the joiner writes `Alvoraa Joiner Submission`, never `Employee`.

**Refused, and the reason is already written down:** `pan_number`, `esi_number`,
`provident_fund_account`, every bank field, `ctc` and every salary field, `blood_group`,
`marital_status`, `health_details`, `passport_number`, `permanent_accommodation_type`,
education and previous employment. Where an identity number is genuinely needed it arrives as
a ticked document type — which is already how you decided Aadhaar would work (079 §6d).

**The honest cost of 084.** Breaking the three-way identity means `LIST_KEYS` needs a
separate joiner tuple, and the comment that warns against exactly that needs rewriting rather
than deleting. A test must assert the joiner list is a **superset of** My Profile's and a
**subset of** "fields a joiner may be asked", and that `NEVER` still refuses everything it
refuses today. That is the whole of 084's engineering, and it is why it is its own slice.

## 9 · Groups or per-field? Settled — per field, and it is already built

I was going to argue for five named groups instead of a per-field tick list. **I withdraw
it.** 079 decision 5 chose the per-field picker, built it with its own "must fill in" tick
inside each row, and `ux-learnings.md` records the design: *"a dependent setting is a second
tick that only EXISTS once the first is ticked"*, and *"MUST FILL IN (3)"* as a group heading
over the chips. It ships. At six candidates — nine if you take §8 — a group layer would add a
concept and remove nothing. Groups were the right answer to a forty-field list, and there is
no forty-field list.

## 10 · What a warning is, in practice

The pattern exists; extend it, do not invent one.

1. **To the admin, standing, amber, no dialog** — on the joiner's new document picker:
   *"Joiners will be asked for this. Your own staff's Aadhaar cards stay off the profile
   page."* Today's equivalent line names the actual roles that can read the file; the new one
   names the audience that changes.
2. **To the admin, once, as a confirm** — only when they mark a sensitive item **compulsory**,
   because that is the one action that takes the joiner's choice away: *"A joiner who cannot
   send this will not be able to finish the form. Make it compulsory?"*
3. **To the joiner** — nothing new. The notice screen already carries "What we will ask for"
   and "What happens to what you send", in the employer's own words, and the form refuses to
   render without them.

**Who sees what: admin gets 1 and 2; the joiner's version is the employer's own notice.** One
set of facts behind all three, so changing a retention number changes every line.

## 11 · Documents — what counsel's rulings actually force now

All nine rulings are recorded in `079/00-decisions.md` §7 and all are **already met in code**,
with two exceptions I must name:

| Ruling | State |
|---|---|
| 3 · record kept 180–365 days | **Built.** `alvoraa_joiner_not_hired_days`, clocked from `closed_on` not `modified`, with a backstop and a warning day |
| 4 · papers deleted much sooner, 30–60 days | **Built.** `alvoraa_joiner_document_days`, sharing one `delete_the_documents` with the erase job so the two cannot drift |
| 5 · Aadhaar masked on the image | **Decided, not built.** Guidance pointing at UIDAI's masked download (079 §6d). **The weakness is on the record: a joiner who photographs the plastic card hands us the full number and nothing refuses it.** ⚠ Still gated by ALV-215 |
| 6 · the notice is the employer's | **Built**, per tenant, and the form refuses to render without it. Hindi needs no build — a tenant can type it in Hindi today |
| 8 · HR can export or purge on request | **Built.** `export_submission`, `purge_submission` |
| 9 · masked by default, unmasked to super-admins only, every export logged | **Built — masked with no unmasked version at any permission level, and one log line per export, table-tested.** The log line is discarded (`log_level` is read from no config, so it cannot be set), **but ALV-353 now also writes a durable `Alvoraa Photo Access Log` row per export and purge, and that row is the control** |

So the smallest honest version of ask 3 is: **tick the document types** — on a tick that is
the joiner's own, which is slice 083.

## 12 · Access expectations

| Data | Persona | May see | May change | May share | Purpose | Must NOT have | M? |
|---|---|---|---|---|---|---|---|
| A joiner's own answers and files | **The joiner** | Own only | Own, and documents stay open after Send | No | It is their record | Any other row, any other page. **Their role is in no permission row at all; the row is resolved from the session** | **M** |
| | **HR Manager** | Yes (read/write/create on the doctype) | Correct, with history | Export **masked**; purge | Make the Employee record; answer "what do you hold about me" | An unmasked export — there is none at any level | **M** |
| | **HR User** | **Read, all rows** `[Confirmed — the doctype's own permission rows]` | No | No export flag | HR ops support | Write, export | expectation — **see Q2** |
| | **System Manager** | Full | Full | Export masked | Configuration and support | — | expectation |
| | **Line manager, employees, CXO** | **Nothing** | No | No | No purpose exists | Everything | **M** |
| **An employee's own documents** (the coupling) | **Whoever reads the Positions/profile surface** | Today: any type ticked for joiners becomes visible here too | — | — | — | **This is the fault 083 fixes** | **M** |
| **The settings** (which fields, which documents, the clocks, the notice) | **System Manager only** | Yes | Yes, through the access-granting path with a `Version` row | No | Ownership of the decision | — | expectation — **see Q3** |
| **The five new fields** (084) | **The joiner** | Own | Own, until Send | No | Facts only they know | — | **M** |
| | **HR Manager** | Yes | Yes | Masked export | Create the record | — | **M** |

**Where expectation fights least privilege — your calls:**

- **HR User reads every joiner submission.** Defensible for HR ops. Worth a conscious yes.
- **System Manager owns the ticks, HR Manager lives with them.** If the System Manager is us,
  we are choosing what a customer's joiners are asked. I do not want that.

**The five `data-doors.md` questions, answered at product level.**

1. **Who can read this, and which door stops everyone else?** The joiner reads one row,
   resolved **from the session** through the `user` link — "there is nothing a caller can post
   that reaches another person's row" (079-SEC-4). Everyone else is stopped by the doctype's
   own permission rows: System Manager, HR Manager, HR User, and nobody else. The joiner's
   role appears in no row at all, deliberately.
2. **Tested as a plain staff login through the API?** It must be re-run for the new setting
   key and, in 084, for the new fields — all ten doors, on a fresh site. A test that passes
   before the fix proves nothing.
3. **Fresh site, and the real tenant?** Fresh site for the tests. At the first tenant, a
   read-only count: how many logins can list `Alvoraa Joiner Submission`, and how many rows
   exist. Counts only.
4. **How many bypasses?** Three exist in this area today and each is named in the source:
   `File.insert`, `delete_doc` on files and users, and the erase `save` — all on the
   retention and upload path, none reachable to widen a read. **083 should add zero.** If the
   engineer needs one, the shape is wrong.
5. **What could a manager with a self-service role change or share?** Nothing here — provided
   the new joiner document tick never feeds the profile surface, which is the whole point of
   the slice, and provided nobody adds a Share row.

## 13 · Regulatory read

1. **Which regime?** India's **DPDP Act 2023**. Counsel's nine rulings of 31 Oct bind. No AI.
   No new EU exposure. I am not a lawyer.
2. **Whose duty?** The **employer's** — they are the Data Fiduciary, we are the Processor
   (ruling 1). 083 makes their duty easier to discharge: it stops a joiner-facing choice from
   silently widening who sees their existing staff's papers.
3. **What becomes possible that was not?** 083: nothing new is collected; one existing
   exposure is **closed**. 084: five more fields about a not-yet-employee, two of them
   (`gender`, `date_of_birth`) attributes a person could be sorted on. Each needs a `PRIV-n`.
4. **Front page test.** 083 passes easily — it is a privacy fix. 084 passes if `gender` and
   `date_of_birth` are optional, carry the grey line, and never become compulsory by default.

⚠ **COMPLIANCE, unchanged and still open: ALV-215.** Whether guidance pointing at UIDAI's
masked download satisfies ruling 5, and whether an employer may require an Aadhaar card
before employment. **Owner: Surbhi, with counsel.** It gates switching the form on at a
tenant with real joiners. It does not gate this build.

## 14 · Run-side reality

**No `07-devops-inputs.md` §1 exists for this slice, so this is my guess.** 083: one more
`DefaultValue` row, no new app, worker, page, job or storage. Nothing measurable. 084: five
more columns on one doctype. The real run cost in this whole area is file storage, and it
already exists with per-joiner caps. **DevOps must confirm before the design check.**

## 15 · Success criteria

| Measure | Baseline | Target | Instrument |
|---|---|---|---|
| Document types ticked for joiners at the first tenant | **0 today — and that is the bug** | At least 3, within a week of 083 | Read the new setting |
| Joiners who send at least one paper before day one | **0 — impossible today** | 70% of invited | Count `File` rows per submission |
| `Employee Document Type`s exposed on the staff profile surface *because of a joiner decision* | **Unknown; currently any tick does both** | **0, proved by a test** | The new test |
| Fields HR retypes after accepting (084 only) | 4 of 9 `[ASSUMPTION]` | ≤ 1 | Count the accept mapping; ask the HR person at week 2 |
| Minutes a joiner spends on the form | Unknown | under 6, median, on a phone | First to last save on the submission |
| Export log lines per export | **0 in fact before ALV-353; now 1 row per export** | 1 per export, always | Count lines against calls |

**Not measures:** logins, page views, forms created.

## 16 · Thriving-workplace check

| Lens | One line |
|---|---|
| **Engagement** | Small and real: the joiner can finally hand over their papers from a phone instead of carrying them in |
| **Collaboration** | The admin's tick becomes the joiner's screen, and the papers reach HR's existing verification flow instead of a WhatsApp thread |
| **Inclusiveness** | **The honest answer is that this feature excludes Hindi-first frontline joiners today** (ALV-267). Five more English fields makes that worse, not better. If you want one thing for inclusiveness, pick the `hi.csv`, not slice 084 |
| **Transparency** | 083 *removes* an unintended disclosure about existing staff. That is the best kind of transparency work: it makes the admin's choice honest before they make it |

## 17 · Risks, red-teamed

| Risk | What happens | Cheapest way to find out first |
|---|---|---|
| **The form does not actually work** (the ALV-343 question) | Everything here is zero | One real invite, one real phone, mobile data, before the design check |
| **Someone ticks a type on the old key to help joiners, after 083 ships** | The coupling bites anyway | The old picker's amber line must say what it does **not** do |
| **084 widens `gender` and `date_of_birth`, a tenant marks them compulsory** | A joiner who will not state a gender cannot finish the form | Confirm in §10 item 2, and the "bring it on day one" escape does not apply to a typed field — so these two must never be markable compulsory. **Worth a hard rule** |
| **A joiner photographs the plastic Aadhaar card** | We store an unmasked number. Already on the record (079 §6d) | Nothing new. ALV-215 |
| **`log_level` cannot be set** | The retention log lines are still discarded; the export and purge are now rows (ALV-353) | Retention counts still need their own answer |
| **10x: a 50-person seasonal intake** | 50 logins made by hand, 50 accepts. No bulk path exists | Ask DTC whether they ever hire 50 at once |
| **Support tickets this creates** | "Why is the document screen empty?" (nothing ticked), "why did my staff's Aadhaar appear on the profile page?" (today's coupling), "why can't HR User export?" | One release-note line each, written before release |

## Subtract pass — what I deleted from my own draft

- **My entire nineteen-field list.** Nineteen became five once I read `people_fields.py`.
- **My five field groups**, and the whole groups-versus-chips argument. The per-field picker
  is built and is right at this size. §9.
- **"Masking is real engineering, so this is not a small slice."** Wrong: the masker was
  dropped on 2 November and replaced with guidance.
- **"The build has one clock and cannot express both."** Wrong: both clocks are built.
- **"HR Manager can export unmasked and nothing is logged."** Wrong in code — masked, no
  unmasked path at any level, one log line per export, table-tested. The line is discarded and
  `log_level` cannot fix that; ALV-353 adds a durable row per export instead.
- **A recommendation that we never collect ID-card images.** 078 §11.3, 079 §6 and §6d
  considered this and chose the opposite with reasons: a *file* under HR verification is safer
  than a searchable column a stranger can write. I accept that and have withdrawn mine.
- **The "two retention clocks" and "per-tenant notice" work** from the slice — built.
- **A preview button, education and work-history rows, a "who has not finished" screen,
  `micr_code`, a manager notification** — all gone as before.

## Open questions — your decisions

| # | Decision | Why it matters | My recommendation | Blocks |
|---|---|---|---|---|
| **Q1** | **Do the joiner's documents get their own tick?** | Today you cannot ask a joiner for a paper without exposing your staff's copies of it | **Yes. This is slice 083 and I would ship nothing else first** | The slice |
| **Q2** | **Slice 084 at all — five more fields?** | It re-opens a deliberate 079 design choice for a Performance-class gain | **Yes, but after 083 and after the Hindi file.** Five fields, the five in §8, nothing else | 084's existence |
| **Q3** | **`gender` and `date_of_birth`: may a tenant ever mark them compulsory?** | A person who will not state a gender must still be able to join | **No — askable, never compulsory. A hard rule in code, not a guideline** | 084's spec |
| **Q4** | **HR User keeps read on every joiner submission?** | They see name, mobile, home address, next of kin for everyone invited | **Keep it.** HR ops needs it, and they hold no write and no export | `01c` |
| **Q5** | **Who owns the ticks — System Manager only, or HR Manager too?** | If System Manager is us, we are choosing what a customer's joiners are asked | **Add HR Manager, scoped to their company.** The customer should own this | The permission matrix |
| **Q6** | **Is `log_level` set at any tenant?** | (It cannot be set; see ALV-353.) Before ALV-353, "every export is logged" was false in fact | **Corrected: it cannot be set. The export row now exists (ALV-353)** | Any claim about logging, and ruling 9 |
| **Q7** | **Hindi (ALV-267) before slice 084?** | 151 strings are already wrapped; only a reviewed `hi.csv` is missing. The feature is English-only on a journey our own rules say must be at parity | **Yes. It is worth more to a DTC joiner than five fields** | Nothing — but it changes what you build next |

## Assumptions

- `[ASSUMPTION]` Nobody has ticked any document type at the tenant you tried, which is why
  upload looked broken. I cannot read tenant data. **The cheapest test in this brief: look at
  `alvoraa_positions_document_types` on that site.** If it is non-empty, I am wrong and there
  is a real defect to find.
- `[ASSUMPTION]` `permanent_address` exists on `Employee` with that name. `Employee` lives in
  `erpnext`, which is not in this repo. The other four are confirmed in
  `employee_field_rights.py`.
- `[ASSUMPTION]` The form has never been switched on, so there is no migration and no data to
  convert. If a tenant has live submissions, 083 needs a default for the new key that
  preserves today's behaviour, and I would want to know before the design.
- `[ASSUMPTION]` Web-only. No change to the phone app, so the mobile engineer does not run.

## Kill criteria

1. **The form does not work on a real phone.** Stop; fix that first.
2. **`alvoraa_positions_document_types` is already non-empty** at the tenant where upload
   failed. Then my diagnosis is wrong and this brief needs redoing against the real defect.
3. **Counsel says guidance does not satisfy ruling 5** (ALV-215). Then the document path
   narrows to non-identity papers and 083's value shrinks — still worth doing, but say so.
4. **Any part needs a permission bypass to work.** The shape is wrong; ALV-249 is why we stop
   rather than negotiate.
5. **Nobody switches the form on within 30 days of 083.** Then the whole area is Indifferent
   and 084 should not be built.

## Handoff note

**Read 079's `00-decisions.md` before you read anything else.** Every decision in it is
settled and I have not re-opened one. Two things in this brief do touch it, and both are
flagged: slice 084 breaks the deliberate three-way identity of the candidate field list
(§8), and 083 splits a tick that 078 chose to share (§7).

To the **UX designer**: the picker, the amber line and the chips exist and you designed them.
I need two things — the wording of the new amber line so it names what *changes* rather than
what is sensitive, and whether the joiner's document picker belongs in the same card or
beside it. Please also tell me plainly whether Hindi (ALV-267) should jump ahead of 084; I
think it should.

To the **security engineer**: §12 is product intent. The question I most want your answer to
is whether a document type ticked for joiners can be proved *not* to reach
`employee_documents_read.get_employee_documents`, by a test that fails without the fix. And
please confirm the bypass count stays at three.

To the **BA**: verify `permanent_address` on `Employee`'s meta before writing a story about
it, and hold two lines — the joiner never writes `Employee`, and `gender` and
`date_of_birth` can never be marked compulsory.

To **DevOps**: §14 is a guess. Correct it, and `log_level` is not a real setting (ALV-353), so there is
no log-volume cost to estimate for it.

**Where I disagree with the request:** "as many fields as they want" I am refusing, and §8
explains why in terms of the design that is already shipped. If you want an open field list,
say so and I will write the brief — but it reverses 079 decisions 5 and 6 and the `NEVER`
deny list, and that is a security review, not a picker.
