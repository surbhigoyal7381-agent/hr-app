---
slice: 078-positions-faces
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-10-31
status: draft for the business analyst. Recommendations only — Surbhi decides.
inputs:
  - 01-product-brief.md (revision 2)
  - 01b-ux-design.md (prototype v4)
  - 01a-ux-opportunities.md
  - 07-devops-inputs.md §1
  - .claude/context/security-compliance-baseline.md (verified 24 Aug 2026 — 68 days old, not stale)
  - .claude/context/legal-retention-rules-2026-09.md (counsel, 18 Sep 2026)
  - code read in this worktree on 31 Oct 2026, cited file:line throughout
decisions_carried:
  - One slice, all four parts (Surbhi, 31 Oct 2026)
  - All 18 document types offered in the settings screen; HR's judgement which appear
  - Faces on the chart cards
  - Positions readable by HR Manager at DTC
  - The seat page is a page; names open the drawer
  - Pre-onboarding built now; retention period is a setting; counsel's number arrives later
  - One-click tag removal refused; all four lists use the same dialog
---

# 078 · Security and privacy requirements

## 0 · The answer first

**Three things to read before anything else. The first one changes what the slice can
honestly claim.**

**(1) The photo is not shown on two surfaces. It is already wired into ten.** The
brief and the design both say faces appear on the Positions page and — "as a free
consequence" — on the employee-facing Organisation page. That is not what the code says.
`Employee.image` is already selected and already returned by, at least:

| Surface | Where | Audience, as the code stands |
|---|---|---|
| Staff directory | `alvoraa_portal/alvoraa_portal/staff_api.py:87` | **Every employee, across their whole company** (`DIRECTORY_SCOPE_FOR_EMPLOYEES = "own_company"`, `staff_api.py:127`), behind the tenant feature switch |
| Organisation chart | `hrms/hrms/alvoraa_org_structure/api.py:177`, `:550` | Within reach — **and reach is unlimited for anyone with a direct report**, because `alvoraa_org_managers_see_all` defaults to `1` (`settings.py:58`, applied at `api.py:838`) |
| Portal frame "me" | `frame_api.py:44`, `hr_api.py:1943` | Self |
| Home | `home_api.py:119` | Self |
| Team list | `team_api.py:48` | A manager's team |
| Time screens | `time_api.py:77` | Scope of that screen |
| Goals | `goals_api.py:248`, `:1045` | Scope of that screen |
| HR people list | `hr_api.py:539` | HR scope |
| **Birthday and anniversary emails** | `hrms/hrms/controllers/employee_reminders.py:180` → `templates/emails/birthday_reminder.html:7` | The photo's **URL is placed in an email body** sent to colleagues, when the HR Setting is on |

*Verified in code, 31 Oct 2026.* The exposure is not created by this slice's code. **It is
created by the upload.** The day an employee presses "Take a photo", their face appears on
every one of those surfaces at once, with no further change by anybody.

That makes the privacy sentence the design drafted — *"shown next to your name on the
organisation and positions charts to colleagues who can see you"* — **factually
incomplete**, and a notice that understates the audience is worse than no notice, because
the employee relies on it. **PRIV-1** fixes the wording. Nothing else needs to change,
and no code needs to be removed: this is a sentence, not a feature.

**(2) The ticked-document-types list cannot be a confidentiality boundary, so the slice
must stop needing it to be one.** DevOps measured why (`07` §1, point 3): `Employee
Document` is a child table, its attachment belongs to the parent **Employee**, and
Frappe's private-file gate falls back to the parent's read permission
(`frappe/core/doctype/file/file.py` ~1009–1025). Tick three types and any reader who can
read that Employee can still fetch all eighteen by URL.

The usual answer — "write a streaming endpoint" — does not close the URL. **The answer
that does close it is to change who sees the section, not what the section lists.** At
DTC the Positions readers are HR Manager, and HR Manager already holds plain read on
Employee and can already open every one of those files from Desk today. So, for that
audience, the documents section adds **no new access** — it adds a faster door. The risk
appears the moment a tenant grants Positions read to a wider role. **SEC-3** therefore
gates the documents section on an HR role set, independently of who the tenant let onto
the page. Then every reader who can see the section could already fetch every file
anyway, and the child-table trap stops being fatal.

**SEC-4** keeps the ticked-type check as well, as defence in depth — and requires that
nothing in the product's wording claims it is a boundary.

**(3) Nothing about documents can be observed on the demo tenant, so "0 findings" from a
test run there means nothing.** Measured by UX and DevOps and re-confirmed: **6,469
`Employee Document` rows exist on `ppj.localhost` and 0 of them have a file attached**;
**0 of 403 employees have a photo**. This is lesson 1 from slice 028 exactly. §9 lists the
fixture that must exist before any of these controls is observable.

---

## 1 · Threat model, four lines

**Who would want this, and what is the cheapest way to get it?** Not an outsider. A
curious colleague who opens the staff directory and now sees 400 faces; an HR Manager at
DTC — a real group, not one administrator — who can reach an identity document from a
structure page in two clicks instead of four; a departing employee with a valid session
and three weeks' notice; and, newly, **anybody on the internet who is forwarded a
pre-onboarding link.** The cheapest route for every one of them is a normal, permitted
screen, not an exploit.

**Blast radius of one mistake.** One wrong tick on the settings card = every reader of
the Positions page sees one field or one document class for **everybody in their own
companies and branches**. One wrong field on the allow-list = the same, for ~400 people.
One leaked or guessed pre-onboarding token = **one joiner's** identity documents. No part
of this slice crosses a tenant boundary: every surface here is inside one site, and the
pre-onboarding page reads branding from site config only (the pattern `www/enrol.py` uses).
So: **company-wide, not tenant-wide** — serious, not top of the scale.

**What this makes possible that was impossible before.** (a) New *collection*: the
product gains its first employee-supplied photograph, and its first data from a person who
is not yet an employee. (b) New *visibility*: identity and statutory documents become
reachable from a structure page, and faces become real on ten existing surfaces at once.
(c) New *inbound flow*: a write-and-upload path open to a caller with no login. (d) New
*outbound flow*: a photo URL in a birthday email. **No new automation of a decision, and
no AI path** — and SEC/PRIV requirements keep it that way.

**How would we find out?** Honestly: for a wrong tick, today we would not — which is why
PRIV-5 records document opens and why the standing warning on the settings page carries
more weight than before (the one-click removal was refused, so the warning is now the only
thing that gets a stale tick noticed). For a mis-set field list, the test in SEC-1 is the
detection, because the list is a closed server constant and anything outside it fails CI,
not production. For pre-onboarding abuse, the rate limiter already writes a refusal line
(`field_app_limits.py`); for the rest, the answer today is "a customer would tell us", and
that is a residual risk named in §12.

---

## 2 · Data inventory

Sensitivity classes used here: **Ordinary** (work facts, routinely visible inside a
company) · **Personal** (about the person, not about the job) · **Sensitive** (identity,
statutory, financial, health, or a biometric-adjacent image) · **Restricted** (would be a
notifiable incident on its own).

| Data | Class | Purpose | Retention | Who may see it |
|---|---|---|---|---|
| `Employee.image` — the profile photograph | **Sensitive** (a face; biometric-adjacent, and the only thing in the product that identifies a person visually) | Recognise a colleague. **Nothing else, ever** (PRIV-3) | Employment + the existing Employee record's life. Replaced or removed by the employee at will (PRIV-2) | Ten surfaces, §0(1). Widest is the staff directory: **every employee in the company** |
| The 48 px derived copy | **Sensitive** (same face) | Draw the chart inside the page budget | Same as the photo; deleted with it | Same as the photo |
| The 11 Positions profile fields (job role, department, branch, company, reports to, grade, employment type, date of joining, default shift, work email, work phone) | **Ordinary** | Answer "who is this, what do they do, since when" | Not stored by this slice — read from Employee | Positions readers, scoped to their companies and branches |
| The 6 My Profile editable fields (mobile, personal email, current address, emergency contact name / relation / phone) | **Personal** (and the emergency contact is a *third party's* data) | Keep the employee's own record correct | Already on Employee | The employee themselves; HR within scope. **Not on the Positions profile** |
| `Employee Document.attachment` — up to 18 types, 15 of them identity / statutory / financial / background-check | **Sensitive**, and PAN, Aadhaar, bank proof and police verification are **Restricted** | HR verification of a staff record | Already on Employee; not changed by this slice | **HR roles only** (SEC-3), scoped |
| The document-open record (who looked at whose document, when) | **Personal** (about the reader) | Answer "who looked at my documents" in a grievance | Open question §11-S1; default is keep | HR Manager, System Manager |
| Pre-onboarding submission — the joiner's details | **Personal** | Make a staff record without HR retyping it from paper | **A setting**, default unset; placeholder 90 days; counsel's number pending (⚠ COMPLIANCE 2) | HR roles only; the joiner, via their token, until they submit |
| Pre-onboarding uploads — identity documents from a non-employee | **Restricted** | Same | Same setting | Same |
| The pre-onboarding token | **Restricted** (it is a bearer credential for a Restricted payload) | Open the form for one joiner | Hash only, retired on use/expiry; row deleted with the submission | Nobody. Only its SHA-256 hash is stored (SEC-9) |
| The four settings keys | **Ordinary**, but **access-granting** | Decide what readers see | `DefaultValue` + a `Version` row per change, kept | System Manager |

**Nothing in this slice is new personal data on an existing Employee field** except the
photograph. Everything else is either an existing field read on a new screen, or a new
record about a person who is not yet an employee.

---

## 3 · Access intent — including who must NOT see what

The analyst builds the permission matrix from this table. "Must not" rows are the ones
that need a test.

| Surface | Must see | **Must NOT see** |
|---|---|---|
| My Profile | The employee's own record: the 6 ticked fields, read and write; their own photo, upload / replace / remove; a link to `/update-password` | **Any other person's record, in any field.** An HR login with no Employee row must get the designed empty state (design S1-E), not a server failure and not somebody else's record |
| Positions mini profile | A Positions reader (`register.may_view()`), scoped by `permitted_companies` / `permitted_branches`: the ticked fields from the closed allow-list, for employees inside their scope | **Pay, CTC, bank, PAN, Aadhaar, ESI, PF, salary mode, date of birth, personal mobile, personal email, home address, emergency contact, marital status, blood group, relieving date, and every field a payroll rule set names** — whatever is ticked, whatever the reader's permlevel. **And anyone outside their company/branch scope**, including the fact that such a person exists |
| The documents section | **HR Manager, HR User, System Manager only**, and only within their own scope | **Every other Positions reader**, including a line-manager role a tenant may add to the page later. Also: nobody, in any role, through print or a screen-share capture (065 / 069 already cover it) |
| Organisation page / staff directory / team list | What they see today, plus whatever photos now exist | Nothing new is authorised here. **No new field joins any of these payloads in this slice** |
| Settings card (four lists) | **System Manager only** | **HR Manager** — including through Desk. The tick must not be editable anywhere an HR Manager can reach (SEC-5) |
| Pre-onboarding form | The holder of one live token, for one joiner: the form, and their own answers while they are filling it in | **Any other submission, any employee's data, any count, any tenant data beyond the public brand.** A stranger must not be able to learn whether a token, a person or an email address exists (SEC-13) |
| Pre-onboarding review | HR roles, scoped | The joiner, after submitting. Guest, always |

**The asymmetry, stated plainly.** The employee whose face and documents are on the
Positions page cannot open that page. That is deliberate (design §1) and it is the reason
PRIV-1 and PRIV-5 exist: if a person cannot see the surface, the notice and the access
record are the only ways they can know what happened.

---

## 4 · Obligations engaged

From `security-compliance-baseline.md`, **verified 24 Aug 2026** (68 days old — inside the
90-day window, so I am relying on it without re-verification; §13 says what I did not
re-check).

| Obligation | Source, and date checked | What it demands here |
|---|---|---|
| **Notice** — clear and itemised, in a language the workforce reads | DPDP Act 2023 s.5; Rules notified 14 Nov 2025, duties phased to ~May 2027. Baseline verified 24 Aug 2026 | PRIV-1 and PRIV-8. Hindi at parity, because the frontline worker is the primary user of both screens |
| **Lawful basis** | DPDP s.4 and the legitimate-uses schedule. **Not mine to decide** | Employment relationship for the photo and the profile; **almost certainly notice-and-consent for the pre-onboarding joiner**, because there is no employment relationship yet. ⚠ COMPLIANCE 1 and 2 |
| **Purpose limitation** | DPDP s.6(1) | PRIV-3. A photo collected to recognise a colleague is never matched, scored or used for attendance |
| **Data minimisation** | DPDP s.6(1) | SEC-1, SEC-7, PRIV-4, PRIV-9. Closed allow-lists, not free picks |
| **Erasure when the purpose ends** | DPDP s.8(7) | PRIV-6. A submission from someone who never joins has no purpose left |
| **Correction and erasure on request** | DPDP s.12 | PRIV-2. The employee removes their own photo |
| **Reasonable security safeguards** | DPDP s.8(5) | SEC-6, SEC-9 to SEC-15 |
| **Breach reporting, 6 hours** | CERT-In Directions 28 Apr 2022, s.70B(6) IT Act. Baseline verified 24 Aug 2026, with a ⚠ to re-confirm the current text | A public upload endpoint makes "unauthorised access" more plausible. The clock is unchanged; §12 records that we have never drilled it |
| **EU AI Act Article 5** — emotion inference at work, and untargeted facial scraping | In force 2 Feb 2025 (baseline) | PRIV-3, as a refusal written down now so it cannot arrive later |
| **Counsel's retention policy, 18 Sep 2026** | `legal-retention-rules-2026-09.md` | See the answer below — it does **not** cover the pre-onboarding case |

### Does counsel's existing policy already answer the pre-onboarding retention period?

**No. I checked, and it does not — but it rules two answers out, which narrows the
question usefully.**

`legal-retention-rules-2026-09.md` (18 Sep 2026) sets two periods: GPS trail 30 days with
a 12-month summary; **performance records for the duration of employment plus a strict
6-month buffer after exit, then automatic permanent erasure**. It adds one binding rule of
general shape: **"indefinite soft deletion is prohibited"** and *"any retention setting we
build must not offer 'keep for ever'."*

Applied here, that gives us three things without asking counsel again:

1. **"Keep it indefinitely" is already refused.** So the setting must not accept a
   never-delete value — which is the opposite of the check-in photo setting, where `0`
   deliberately means keep for ever (`field_app_photos.py:133-135`). **Do not copy that
   semantics here.**
2. **Both of counsel's periods are anchored to a relationship** — a delivery, an
   employment. A joiner who never arrives has no relationship to anchor to, so neither
   period transfers by analogy.
3. **It therefore does not imply 90 days, or any other number.** The prototype's 90 is our
   invention and must not be presented to a joiner as a decided period. ⚠ COMPLIANCE 2
   stands, and PRIV-7 is the guard that keeps the gap safe.

---

## 5 · Abuse cases

Each one is written as *this actor, in this state, calling this path, sees this data* —
the form a finding has to take at review.

| # | Actor and state | Path | What they get today, or would get without the requirement | Stopped by |
|---|---|---|---|---|
| A1 | **A curious colleague**, ordinary Employee, signed in | The staff directory, after photos exist | 400 colleagues' faces, company-wide. **Already authorised** (slice 045) — but authorised when the field was always empty | Nothing, and nothing should: the decision stands. PRIV-1 makes the employee aware before they upload |
| A2 | **A System Manager in a hurry**, ticking the settings dialog | `set_cover_setting`-shaped endpoint, or a direct POST to it | Ticks `bank_ac_no` or `date_of_birth` onto the Positions profile. **Permlevel will not save us: HR Manager holds read at level 1** (`employee_field_rights.py:52-55`, `apply()` grants it), and HR Manager is exactly the DTC audience | **SEC-1** — a closed server allow-list that an off-list field cannot pass, posted directly or not |
| A3 | **An HR Manager**, in Desk, not on the settings card | `/app/employee-document-type/Aadhaar card` → tick a `show_in_positions` Check | Widens what the whole tenant's Positions readers see, bypassing the System-Manager-only rule — because **`Employee Document Type` ships `write: 1` to HR Manager** (`employee_document_type.json` permissions, read 31 Oct 2026) | **SEC-5** — the tick does not live on that doctype |
| A4 | **A line manager**, if a tenant ever grants Positions read to a manager role | The mini profile → Documents → View | A colleague's Aadhaar and police verification, from a structure page. And then, by URL, **the other 15 types too**, because the child-table gate asks the parent | **SEC-3** — the section is gated on HR roles, not on page read |
| A5 | **Any Positions reader**, holding one `/private/files/...` URL | A direct GET | Every file on that Employee, ticked or not | **Not closable at the URL** (§0(2)). SEC-3 removes the audience for whom it matters; **SEC-4** records the honest limit and forbids wording that claims otherwise |
| A6 | **A departing employee**, 3 weeks' notice, valid session, status still Active | My Profile; the directory | Their own record and the directory — correct, they are still employed. **The real trap is a leaver whose login is not disabled**: ERPNext does not disable it | **SEC-8** — every new "who am I" lookup filters `status = "Active"`, as `_get_employee` already does (`hr_api.py:300-308`) |
| A7 | **A stranger forwarded the invite link** | The public page, then the guest POST | One joiner's form; and if the link is reusable, the chance to overwrite what the real joiner sent | **SEC-9** — single use, expiring, hash-only, token in the fragment |
| A8 | **A script**, hitting the public endpoint | The guest POST, in a loop | Storage flooding, 50 MB bodies (nginx limit, `max_file_size` unset), malware on disk, and an existence oracle on employee emails | **SEC-10**, **SEC-11**, **SEC-13** |
| A9 | **A stranger**, probing without a token | The public page with a guessed or empty token | Confirmation that a tenant exists (acceptable — the brand is already public) and, without SEC-13, whether a token or a person exists | **SEC-13** — one answer for unknown, expired and used |
| A10 | **Anyone**, after a joiner never arrives | Nothing — the data just sits | Identity scans of people who were never employed, kept for ever, in every `bench backup --with-files` | **PRIV-6**, **PRIV-7** |
| A11 | **A support engineer with a good reason**, on the bench | Reading the sites volume | Every photo and every scan. Unchanged by this slice; no break-glass control exists | Out of scope; named in §12 as standing residual risk |

---

## 6 · SEC requirements

Every one says how it will be tested. **The rule id written into the security log must be
the slice-qualified form `078-SEC-n`** — `SEC-17` and `SEC-18` are already in use in this
codebase for field rights and access-granting settings (`employee_field_rights.py`,
`alvoraa_org_structure/settings.py`), and one grep must not conflate them.

### SEC-1 · The Positions profile field set is a closed server allow-list

The 11 fields are a **module constant in server code**. The tick list chooses *from* it
and can only ever be a subset. An off-list field is refused by the setting endpoint when
it is saved **and** ignored by the profile endpoint when it is read, so a value written
into `DefaultValue` by any other route still produces nothing. Permlevel is checked as
well, but **it is not the control** — HR Manager, the DTC audience, holds read at level 1.

Never on the list, whatever is ticked: pay and CTC, `salary_mode`, bank fields, `pan_number`,
`esi_number`, `provident_fund_account`, `date_of_birth`, `cell_number`, `personal_email`,
home address, emergency contact, marital status, blood group, `relieving_date`, and every
field `rule_set_fields()` names (`employee_field_rights.py:125`).

*Test:* a unit test asserts the constant's exact contents; a second posts `bank_ac_no`,
`pan_number` and `date_of_birth` to the setting endpoint as System Manager and asserts each
is refused; a third writes one of them straight into `DefaultValue` with
`frappe.db.set_default` and asserts the profile endpoint's response contains no such key.
The third test is the one that matters — it is the only one that survives a future UI.

### SEC-2 · The profile endpoint is scoped, and a field the reader may not see is absent

The endpoint requires `register.may_view()` **and** `employee_in_scope(employee_id)`
(`hrms/hrms/alvoraa_hr_core/access.py:291-301`). Do not build a new scope helper, and do
not write `dict(permitted_employee_filters(user), name=chosen_id)` — `scripts/check_scope_traps.py`
already fails CI on that and explains why. A field the reader may not see is **absent from
the response**, not blank and not `"hidden"`; the design requires this and it also means a
reader never learns that a branch they cannot see exists.

*Test:* an HR user permitted to one branch calls the endpoint for an employee in another
branch and gets a refusal, not an empty profile; a caller with no companies gets a refusal
(fail closed); and the response for a scoped reader is asserted key-by-key against the
ticked list.

### SEC-3 · The documents section is gated on HR roles, not on who may open Positions

The section is returned only to **HR Manager, HR User or System Manager**, in addition to
the page's own permission and the scope check. Any other Positions reader gets **no
section at all** — not an empty heading, not a locked row (the design already specifies
the absent state). This is the control that makes the child-table trap survivable: every
reader who can see the section already holds plain read on Employee and could already
fetch every file from Desk, so the section adds a door, not a disclosure.

*Test:* a user holding read on `Alvoraa Position` and **not** an HR role calls the profile
endpoint and the response has no documents key at all; the same user calling the document
endpoint directly is refused and the refusal is logged with rule `078-SEC-3`.

### SEC-4 · The ticked-type check exists, and nothing claims it is a boundary

The file is served by our own whitelisted endpoint, which checks, in order: HR role (SEC-3),
`may_view()`, `employee_in_scope`, that the row's `parent` is that employee, and that the
row's `document_type` is in the ticked list. The browser is never handed a
`/private/files/...` URL for a document.

**And the honest half.** That check is defence in depth, not confidentiality: the URL route
stays open to the parent's read permission. Therefore **no product copy — settings card,
mini profile, or a customer answer — may say or imply that the un-ticked types are
protected.** The design's line *"The 3 types your organisation chose to show here"* is
fine; a line saying the others are hidden would not be.

One engineering job at the strategy gate, half a day: read `frappe/core/doctype/file/file.py`
and `frappe/permissions.py` **in the running image** and record, in the strategy note,
whether Frappe consults a `has_permission` hook on `File` on the `download_private_file`
path. If it does, add the hook and this becomes a real boundary. If it does not, the answer
is written down once and nobody re-litigates it. **I could not check this myself: Frappe's
source is not in this worktree** (only `hrms`, `alvoraa_portal` and `alvoraa_goals` are). I
am relying on DevOps' read of the running image (`07` §1 point 3, §3).

*Test:* a ticked type downloads; a non-ticked type through the endpoint is refused and
logged; and — the test that must be written against the **parent**, not the child row — a
direct `/private/files/` GET for a non-ticked file by an HR reader is executed and **its
actual result is recorded in the test as the documented behaviour**, so the next person
reads the truth instead of an assumption. ALV-256 was the same shape two days ago:
`frappe.has_permission` on a child table silently returned `False` for everyone and killed
an Inbox part. Here the same fact bites in the opposite direction.

### SEC-5 · The four lists are access-granting settings: System Manager only, with a record

All four lists are stored as `DefaultValue` keys and join the existing **`ACCESS_GRANTING`**
set (`alvoraa_org_structure/settings.py:89-94`), which already gives, in code that works
today: System Manager only, a refusal logged for anyone else including an HR Manager, a
`Version` row written in the same transaction with the key, old value and new value, and a
structured security log line (`settings.py:172-231`).

**The document-type tick must not be a Check on `Employee Document Type`.** That doctype
ships `write: 1` to HR Manager (read 31 Oct 2026), so the tick would be editable in Desk by
the very role the card excludes — and at DTC that role is the Positions audience. This
contradicts DevOps' OPS-5, and the reason is the permission row, not a preference.

Rung on the ladder: **2 · configuration**, reusing a mechanism that already exists. Rung 3
(a Check on the doctype) is rejected on the permission row above; rung 5 (a Settings
DocType) buys a permission surface, a migration and a list view and I cannot name one thing
it does that a `DefaultValue` key with a `Version` row does not.

*Test:* an HR Manager calling the setter is refused and the refusal line is asserted; a
System Manager's change writes exactly one `Version` row naming the key and both values;
**Cancel in the dialog writes nothing** (assert zero `Version` rows after cancelling a
dialog in which every box was changed); and an HR Manager ticking the equivalent field in
Desk is impossible because no such field exists — assert that `Employee Document Type` has
no `show_in_positions` field.

### SEC-6 · The photo upload: own record, size before decode, magic bytes, re-encoded

The upload endpoint writes only to the caller's **own** Active Employee record. It follows
the pattern already proven in `field_app_photos.py:84-114`, in this order:

1. Check the length of the **string** before decoding anything. A 200 MB payload must not
   be expanded in a worker's memory before we say we did not want it.
2. Check magic bytes — accept JPEG and PNG; refuse anything else, including a file merely
   named `.jpg`.
3. **Re-encode to JPEG, longest edge 512, quality ~82.** This is the resize and the
   metadata strip in one call, and it is the only reason a PNG or HEIC selfie does not keep
   its GPS: Frappe's EXIF strip runs for `image/jpeg` only (`07` §3, measured).
4. Store as a **private** `File`. Nothing in this slice becomes public — least of all a
   folder of 400 faces at guessable addresses.
5. Derive the 48 px copy in the same call. **Do not use Frappe's `make_thumbnail`**: it
   writes into `public/` (`07` §3).

A failed photo never takes the request down with it, and never leaves a half-written
record.

*Test:* post a PNG carrying GPS EXIF, then read the stored file's EXIF and assert it is
empty and the format is JPEG; post a 6 MB phone photo and assert the stored size is under
200 KB with p95 under 50 KB over a sample; post a ZIP renamed `.jpg` and assert refusal;
post with employee B's id as employee A and assert refusal; assert the stored `File` has
`is_private = 1`.

### SEC-7 · The My Profile write list is permlevel 0 only, and also a closed allow-list

The 6 fields are a module constant. The server intersects the tick with that constant
**and** with `has_permlevel_access_to(..., "write")`, so a level-1 or level-2 field cannot
be written even if someone adds it to the key. This answers brief Q5 and DevOps Q4: **no,
a permlevel-1 or -2 field may never be on the My Profile write list**, and the existing
code already refuses it — but the list must not be able to contain one in the first place,
because a setting that silently does nothing is how a tenant comes to believe a field is
editable. Blood group and marital status stay off the list (health and family data; no
screen needs them).

No new permission machinery. Permlevel 0 is already employee-writable and
`refuse_own_locked_change` (`employee_field_rights.py:140`) already refuses the rest on a
person's own record. Rung **1 · already there**, plus a thin panel.

*Test:* post `designation`, `ctc` and `bank_ac_no` through the My Profile save endpoint as
an ordinary employee and assert each is refused and the stored value is unchanged; assert
the constant's exact contents; assert a tick of an off-list field is refused at the setting
endpoint.

### SEC-8 · Every new "who am I" lookup filters on Active

ERPNext does not disable a leaver's login. Every new lookup in this slice — My Profile, the
photo upload, the document endpoint's self-check — resolves the Employee with
`status = "Active"`, as `_get_employee` already does (`hr_api.py:300-308`) and as
`field_app_access._viewer` does (`field_app_access.py:32`). A login with no Active Employee
gets the designed empty state, never somebody else's record and never a raw failure
(design S1-E; this was seen in a browser today, E2).

*Test:* set an employee to Left, keep the session, and assert My Profile returns the empty
state and the photo upload is refused; assert an HR login with no Employee row gets S1-E
and not a 500.

### SEC-9 · The pre-onboarding token

Follow `Alvoraa App Invite` (`alvoraa_portal/.../alvoraa_app_invite.py`) — it already does
all of this and its reasoning is written down:

- `secrets.token_urlsafe(32)` or longer. A shorter value was not made by us; a longer one
  is not a token.
- **Only the SHA-256 hash is stored.** HR sees the link once. On use, expiry or
  cancellation the hash is **retired into a second field**, so a dead token can still be
  told "already used" rather than "not recognised", while a leaked table never holds a live
  hash for a dead token.
- **Single use.** `Used`, `Cancelled`, `Ran out` are final states and cannot change again.
- **Expiry: 7 days**, as the design's J-E1 screen says. Stored on the row at creation and
  frozen thereafter.
- **The token travels in the URL fragment** (`#t=...`), exactly as `www/enrol.html` does,
  and the page POSTs it in a request body. A fragment never reaches the server, so the
  token is not in an access log, a `Referer` header, or a browser's synced history. **It
  must never appear in a query string.**
- The rate-limit key is the **hash**, never the token (`field_app_limits.py:43-48`:
  Frappe writes the limiter's key value into Redis in clear).
- Only server code writes these rows; nobody creates, edits or deletes one by hand.

*Test:* reuse a used token and assert the "already used" answer; call after expiry and
assert the expired answer; assert the row never contains the token in plain text (query the
table and assert no field equals the token); assert the limiter's Redis key does not contain
the token; grep the request log of a test call and assert the token is absent.

### SEC-10 · Rate limits on every public endpoint, using the limiter that exists

Use `field_app_limits._limited` / `_limited_by_address`. It hashes the argument, keys
Frappe's limiter on the hash, puts the wait in the refusal, and exposes
`__alvoraa_limit__` on the function **so a test can read every endpoint's limit off the
function itself**. A limit per token and a limit per caller address; a one-hour window, as
the rest of the product uses. No new limiter, no CAPTCHA, no new dependency.

*Test:* a table test that reads `__alvoraa_limit__` from every new guest endpoint and pins
what it is keyed on and how many — the same shape slice 013's US-25 test uses. Then one
functional test that exceeds a limit and asserts the refusal carries a retry time.

### SEC-11 · Pre-onboarding uploads

- A closed type allow-list: **JPEG, PNG, PDF.** Nothing else — the design's "a clear
  photograph of the document is fine" means these three are enough.
- **Magic bytes checked**, not the extension and not the browser's content type.
- A per-file size ceiling and a per-submission total ceiling, both server-side. nginx allows
  50 MB bodies and `max_file_size` is unset on the bench (`07` §5), so the ceiling must be
  ours.
- Images are **re-encoded** (SEC-6), which strips metadata — a photograph of a document
  taken at home carries GPS.
- **PDFs are not re-encoded, so they get the narrower treatment:** stored private, served
  only through our own endpoint with `Content-Disposition: attachment`, and **never rendered
  inline in a browser**. We do not scan for malware and we must not claim we do; attachment
  disposition plus a private file is the proportionate control at this size, and §12 names
  the residual risk.
- Files attach to the **new submission DocType, never to `Employee`**. A guest-writable
  Employee would let strangers create personnel records, consume the naming series, and —
  because a joining date can be back-dated — trip the absence-backfill trap, where Frappe
  marks the person Absent for every day since and deleting the rows does not help.

*Test:* post an `.exe` renamed `.pdf` and assert refusal; post a 40 MB file and assert
refusal before the body is stored; post an image with GPS EXIF and assert the stored copy
has none; assert every stored `File` has `is_private = 1` and `attached_to_doctype` is the
new DocType; assert the response headers on a PDF fetch include `attachment`.

### SEC-12 · A submission never becomes an Employee by itself

Creating the Employee is an HR action, in HR's own screen, by a signed-in HR user. **No
joining date comes from the form or from the submission's own dates** — HR sets it on the
Employee. The absence-backfill trap is the reason and it is already logged.

*Test:* submit a form and assert no `Employee` row was created and the naming series did
not move; assert the submission's fields are read-only to the joiner after submit.

### SEC-13 · One answer to probing — no existence oracle

The public endpoints give the **same** answer for an unknown token, a used token that was
retired long ago, and a cancelled one: the design's J-E1 screen. (A token that is genuinely
"already used" may say so, as `Alvoraa App Invite` does — that is a deliberate, narrower
disclosure to a person who already held a live token, not to a prober.) Nothing confirms
that an email address, a phone number, a person or an employee exists. The tenant's brand
and name may appear — they are already public on the login page.

*Test:* call with an empty, a malformed and a random token and assert byte-identical
responses; call with a cancelled token and assert it is not distinguishable from unknown;
assert no employee name, count or email appears in any guest response.

### SEC-14 · Guest reads nothing but its own submission, and cannot enumerate

The new DocType ships **no Guest permission row** and HR roles read-only / System Manager
full — the shape `Alvoraa App Invite` uses. There is **no Web Form onto `Employee`**, and
no `login_required: 0` Web Form over the new DocType either unless the engineer can show
the token check cannot be bypassed on that path; the default is our own guest-allowed POST
endpoints behind the token, because that is where the token check provably runs.

New-Frappe-app checklist rows, answered here because this slice opens a public surface:
**public pages** — one, the pre-onboarding page, modelled on `www/enrol.html`. **Guest
access** — the token-bound POST endpoints only. **Self sign-up** — none; no User is created
by any path in this slice. **New roles created** — none.

*Test:* as Guest, call `frappe.client.get_list` and `frappe.client.get` on the new DocType
and assert refusal; assert the doctype JSON has no Guest permission row; a registry test
asserts that the only new `allow_guest` endpoints are the named pre-onboarding ones (the
shape `test_endpoint_guards_045.py` already uses).

### SEC-15 · The public page is hardened the way `enrol.html` already is

`no_cache = 1`; `X-Robots-Tag: noindex, nofollow` as a **header and** a meta tag;
`Cache-Control: no-store`; `referrer: no-referrer`; **no script, style, font or image from
any other host** — everything inline; and the token removed from the address bar with
`history.replaceState` without being read. Copy `www/enrol.py:12-28` and
`www/enrol.html:1-20`; do not reinvent it.

*Test:* fetch the page as Guest and assert the three headers; a static check asserts the
page references no external host (the repo already has `scripts/check_*` text checks of
this kind — extend the nearest one rather than adding a new gate).

### SEC-16 · No new `ignore_permissions`, and no new CI gate

The only justified `ignore_permissions` in this slice are the `File` insert (the pattern
`field_app_photos.py:107` already uses) and the `Version` insert (which has no create
permission for anyone, as `settings.py:205` explains). Everything else goes through the
permission system. New files start at **zero** in the per-file ceiling that
`test_portal_security_010` already holds; `scripts/check_scope_traps.py` and
`scripts/check_api_paths.py --max 0` already run in CI (`.github/workflows/ci.yml:87, 276`)
and cover the two scope mistakes this slice could make. **I am proposing no new gate, no
new scanner and no new log pipeline** — nothing in this slice names an obligation that the
existing four cover worse than a new one would.

*Test:* the existing ceiling test fails if a new file adds one.

---

## 7 · PRIV requirements

### PRIV-1 · The notice before the first photo names every surface that will show it

The sentence beside the upload must be **true**, and the true audience is wider than the
design's draft. It must name the staff directory, because that is the widest surface and
the design's draft does not mention it. Suggested wording, for Surbhi and counsel to
settle (⚠ COMPLIANCE 1):

> **"Your picture will appear next to your name wherever colleagues already see your name
> — the staff directory, the organisation chart, your team's pages and, if your
> organisation sends them, birthday messages. It is only used so people recognise you."**
>
> Hindi at parity, through the existing `drT()`.

Reachable from the My Profile card before the camera opens, not after. No versioned notice
object and no consent ledger is being built — this is one sentence, and the lawful basis
for an employee's photo is the employment relationship, not consent (⚠ COMPLIANCE 1
confirms that).

*Test:* a string test asserts the sentence is present on the My Profile panel, has a Hindi
entry, and is rendered **before** the upload control in the DOM. And a reviewer's check, not
an automated one: the surfaces named in the sentence must match the readers listed in §0(1).
If a future slice adds a surface, the sentence is wrong — that is a review item, recorded
here so the next reviewer knows to look.

### PRIV-2 · The employee can remove their own photo, and this is not the opt-out that was refused

An employee who may upload and replace a photo must also be able to **remove** it, falling
back to initials. This is DPDP s.12 correction and erasure over data the person supplied
themselves, and it costs nothing: it is the same write, cleared.

**It is a different thing from ⚠ DECISION 10.** That decision refused a *per-person
visibility toggle* — "show my photo on the chart but not in the directory". This is "I no
longer want you to hold my photograph", which is a right, not a preference. I recommend
building it; it also makes PRIV-1's sentence much easier to defend, because the notice can
end *"you can remove it at any time"*.

*Test:* an employee removes their photo; assert `Employee.image` is empty, the derived 48 px
copy and the stored `File` are both deleted, and every surface in §0(1) falls back to
initials with no broken image.

### PRIV-3 · Purpose limitation, written as a refusal

A photo collected anywhere in this slice is **never** matched, compared, scored, or used to
confirm who checked in. No emotion or facial analysis, ever. The field app's check-in photos
are **never** reused as a profile photo and a profile photo is never used as check-in
evidence — they were collected for different purposes and have different retention. No photo
or document from this slice reaches a model prompt. No "download the chart as an image".

*Test:* a static test asserting that `Employee.image`, the 48 px field and the submission's
upload fields appear in no module under an AI or model path, and that nothing reads
`alvoraa_checkin_photo` into `Employee.image` or the reverse. This is a text assertion, not
a gate — it rides in the slice's own test module.

### PRIV-4 · Minimisation on the Positions surfaces

The mini profile is **its own call**, made when a profile is opened. No personal field joins
the `position_table` payload beyond what it carries today: ten fields for 403 people is
4,030 personal values delivered to a browser showing ten. The 48 px copy is what the chart
and the table request; the full picture is fetched only when somebody actually enlarges it.

*Test:* assert the `position_table` response keys are unchanged except for the photo URL;
assert the chart and table request no full-size image; assert the query count is the same
for 20 seats as for 400 (the NFR gate, and it is also a privacy gate — a per-person read is
how a payload quietly grows).

### PRIV-5 · The document-open record: narrow, and it holds no document

"Opening one is recorded" (design S3-D). The record holds: **who looked** (user), **whose
document** (employee id and name), **which type** (the document type name), **when**
(datetime and date). It must **not** hold the file, the file URL, the document number, or
any field value from the document. The same three narrowing rules the existing photo access
log already applies (`field_app_access.py:160-172`): only when there is something to look
at; **never a person looking at their own**; and **one row per viewer per document per day**,
not one per refresh.

Mechanism, cheapest rung: **extend the existing `Alvoraa Photo Access Log`** with a
`document_type` field and a `source` field, and make `checkin` optional. One table, one
reader, one permission surface (it already reads to HR Manager and System Manager only), one
retention answer. A second DocType would buy a second of each and I cannot name what it does
that the extra column does not. The cost, said out loud: two kinds of looking share one
table, and if their retention ever differs the job has to filter — which is a `WHERE`
clause, not a redesign.

*Test:* open a document twice in a day and assert exactly one row; open your own and assert
none; assert the row contains no file URL and no document number; assert the row is
unreadable to an ordinary employee.

### PRIV-6 · Pre-onboarding retention is a setting, and the job reads it

The period is a **`DefaultValue` setting, not a constant in code**, read by a daily erase
job. The job:

- Deletes the **uploaded files and the submission row** for submissions older than the
  period that never became an Employee.
- **Respects legal hold.** A submission flagged for hold is skipped however old it is —
  deleting something somebody asked you to preserve is worse than keeping it too long
  (`field_app_photos.py:136-138` already states this rule and implements it).
- **Says what it did**: a count to the log, so "are these actually being deleted" has an
  answer that is not "look in the files folder and guess".
- **Has no "keep for ever" value.** Counsel's 18 Sep 2026 policy prohibits indefinite
  retention in so many words, and says any setting we build must not offer it. So, unlike
  the check-in photo setting where `0` means never delete, **an unset or `0` value here
  means the feature is off, not that nothing is deleted** (PRIV-7).
- Submissions that **did** become an Employee are out of its way: the personnel record is
  the retained thing and the submission row can be deleted once the Employee exists.

*Test:* set the period to 1 day, age two submissions, flag one for legal hold, run the job,
and assert the unflagged one's row and files are gone, the flagged one is untouched, and the
log line carries a count; assert the job returns without deleting anything when the setting
is unset.

### PRIV-7 · The form ships off, and switching it on requires a deliberately set period

This is the guard that makes "build now, number later" safe.

1. The pre-onboarding form is **off at every tenant on install**, and no token can be
   created while it is off.
2. Turning it on goes through the existing precondition mechanism —
   `ORG_SWITCH_NEEDS` / `_switch_missing` in `hr_api.py:3278-3306`, which already refuses a
   switch whose preconditions are unmet and names what is missing. The precondition here is
   the retention period.
3. **How a tenant proves the period was set rather than inherited.** The retention key joins
   the same **`ACCESS_GRANTING`-style write path** as the other settings in this slice, which
   writes a `Version` row on every real change (`settings.py:197-206`). So the switch's
   precondition is: *a `Version` row exists for the retention key, and the current value is a
   positive number.* That is attributable (the `Version` row names its owner), dated (its
   `creation`), and checkable in one query — and it is impossible to satisfy by leaving a
   default alone, because a default writes no `Version` row. **The shipped default is
   therefore unset, not 90.** The joiner's notice renders the configured number; it never
   renders a number we invented.
4. The refusal says which thing is missing, in the plain shape `_switch_missing` already
   uses: *"Set how long a joiner's details are kept before you turn this on."*

**And plainly: between build and counsel's answer, no real person's documents may be
collected through this form.** The switch stays off at DTC and at every tenant with real
joiners. Local and demo tenants may turn it on with made-up data to prove the controls. If
this form is switched on at a real tenant before ⚠ COMPLIANCE 2 is answered, that is a
**P1 finding at review**, not a P2.

*Test:* with the key unset, assert the switch refuses and names the retention period; set
the key through a route that writes no `Version` row (`frappe.db.set_default` directly) and
assert the switch **still** refuses; set it through the proper endpoint and assert the switch
is allowed; with the feature off, assert token creation and every guest endpoint refuse.

### PRIV-8 · The joiner's notice is before the first question, and it is honest

The design's J1 screen is right in shape and must stay that shape: the notice is **before
the first question**, not under a tick at the end. It must render the **configured**
retention period, name who sees the data (the tenant's HR, nobody else), say that no account
or password is involved, and give a **real route to ask for earlier deletion** — a telephone
number or email from the tenant's own settings, not the prototype's "the address is on this
page". Hindi at parity. Every string through `drT()`.

If the lawful basis is consent (⚠ COMPLIANCE 2), an affirmative act is needed — pressing
**Send** after reading the notice is the candidate, and counsel should confirm that is
enough rather than a separate tick. I am not a lawyer.

*Test:* assert the notice renders the setting's value and not a literal 90; assert it appears
before the first input in the DOM; assert the contact details come from the tenant settings
and the screen refuses to render with a blank contact; assert a Hindi entry exists for every
string.

### PRIV-9 · The public form asks for the fewest fields that make a staff record

The joiner's field list is a **closed server allow-list** on the same principle as SEC-1,
and the SEC-1 deny list applies to it too: no bank account, no salary, no CTC, no statutory
identifier as a *typed field*. Where an identity number is genuinely needed it arrives as
one of the ticked document types, where it is at least a file under HR's existing
verification flow rather than a searchable column on a guest-writable table.

*Test:* assert the constant's contents; post an off-list field name and assert it is not
stored; assert the stored row has no column holding a bank or salary value.

---

## 8 · ⚠ COMPLIANCE — two questions for counsel

Both are stated so a lawyer can answer in one line. **I am not a lawyer**, and neither is
any agent here. Note the 25 Oct 2026 memory that counsel is "OK with our approaches"
**orally, with no retention number and nothing in writing** — which is exactly the gap below.

**⚠ COMPLIANCE 1 — the notice before an employee's first photograph.**
*Question:* "Is the employment relationship the lawful basis for collecting and showing an
employee's photograph to colleagues across the company, or is consent required — and is this
sentence a sufficient notice? *[PRIV-1's wording]*"
*Owner:* Surbhi, with counsel.
*Blocks:* switching the photo upload on at a tenant. **Not** the build.
*Fail-closed default meanwhile:* we show PRIV-1's wording, we build PRIV-2's removal so the
employee has a working route out, and we do not switch the upload on at a real tenant
without an answer.

**⚠ COMPLIANCE 2 — the retention period for a pre-onboarding submission from a person who
never joins.**
*Question:* "A person we invited to a job sends us their name, contact details and scans of
their PAN card, Aadhaar, bank proof and police verification before they have any
relationship with the employer. They never join. How many days may the employer keep that,
and does the answer change if the employer is still considering them?"
*Owner:* counsel, via Surbhi. **Still open.**
*Blocks:* switching the form on at a tenant with real joiners — **no longer the build**
(Surbhi, 31 Oct 2026).
*Why the existing policy does not answer it:* §4 above. It rules out "for ever" and gives no
transferable number.
*Fail-closed default meanwhile:* PRIV-7. The feature ships off; it cannot be turned on until
somebody deliberately sets a period; the shipped default is unset, not 90.

**One question I am not escalating as a third compliance item, because the answer does not
change what we build:** how long the document-open record is kept. Counsel's 18 Sep policy
does not cover access logs. The fail-closed default is **keep it** — the record exists to
defend an employee in a grievance, and deleting it early destroys the only evidence that
anybody looked. It appears in §11 as a should-know and in §12 as a named residual risk,
because the existing photo access log has no retention either.

---

## 9 · What must exist before any of this is observable

Lesson 1, slice 028: a rule can pass every unit test and never fire on real data. Here it
would be worse than that, because the numbers are already known.

| Control | What the demo tenant shows today | What must exist for the control to be observable |
|---|---|---|
| Anything about documents (SEC-3, SEC-4, PRIV-5) | **6,469 `Employee Document` rows, 0 with a file attached** (measured). Every document test would pass against nothing | At least **four** rows with real files: one of a ticked type and one of a non-ticked type, on an employee **inside** the reader's scope; and the same pair on an employee **outside** it. Made as test fixtures, never with a real person's scan |
| Anything about photos (SEC-6, PRIV-1, PRIV-2, PRIV-4) | **0 of 403 employees have a photo**; the whole site has 2 `File` rows | At least one employee with a photo, one with none (so the initials fallback is exercised), and one with a **PNG carrying GPS EXIF**, which is the only way SEC-6's strip is proved |
| The scope checks (SEC-2) | 412 `User Permission` rows on Employee exist; branch rows are narrow at DTC by design | A test user who is HR Manager with a **Branch** User Permission, and one with **none** — the two cases behave differently and only the second is the common demo shape |
| The Positions page itself | **The chart does not load on `ppj.localhost`** — `Replacement Plan` is not migrated (`07` §5, design E1) | Whoever builds this will lose an hour to it. The permission tests do not need the chart to render, but any browser check does |
| Pre-onboarding (SEC-9 to SEC-15, PRIV-6 to PRIV-9) | Nothing exists | A tenant with the feature **on** and invented joiner data. **Never a real joiner's documents** until ⚠ COMPLIANCE 2 is answered |

**If a test run reports "0 findings" without these fixtures, it has proved nothing.** That
sentence belongs in the test engineer's own notes.

---

## 10 · The scoped-reader sweep

Lesson 2, slice 030: scoping helpers get bypassed by readers that build their own queries.
I swept for the siblings of every reader this slice touches.

**`Employee.image` readers — ten, listed in §0(1).** Each has its own scope, and I did
**not** re-verify each one's scope in this pass; that would be its own slice. What I did
verify: every one of them already selects `image`, so **this slice adds no reader and
widens no scope**. The exposure is the upload. One scope I did read, because it is the
widest: `staff_api.DIRECTORY_SCOPE_FOR_EMPLOYEES = "own_company"` (`staff_api.py:127`) —
every employee, their whole company, behind the tenant feature switch. The second widest is
the Organisation chart's reach, which is **unlimited for anyone with a direct report** by
default (`settings.py:58`, `api.py:838`).

**`Employee Document` readers — three, and all are self-scoped or HR-scoped:**
`hr_api.get_my_documents` (own record only, via the Active-filtered `_get_employee`),
`employee_documents.py:151/187/231/246` (HR compliance and expiry work, behind `_require_hr`
at the endpoint). **No unscoped sibling found.** The new document endpoint will be the
fourth, and SEC-3 and SEC-4 are its scope.

**The two scope traps `scripts/check_scope_traps.py` guards** — laying a caller-supplied id
over `permitted_employee_filters()` — are the mistake the profile endpoint is most likely to
make. The gate already runs in CI. Use `employee_in_scope` instead, as SEC-2 says.

**One existing N+1 that is also a privacy shape, not only a performance one:**
`api.py:177` reads the photo with one `frappe.db.get_value` per person per node per
expansion, and `_card` (`api.py:550`) does one read per person. A per-person read is how a
payload quietly grows to carry fields nobody authorised. Batch it (OPS-6), and PRIV-4's
query-count assertion is the thing that keeps it batched.

---

## 11 · Open questions

**Must know — these change a requirement or the verdict.**

| # | Question | My reading | Fail-closed default meanwhile | Owner |
|---|---|---|---|---|
| M1 | **May an employee remove their own photo?** | Yes, and it is a right rather than a preference — different from the per-person visibility toggle ⚠ DECISION 10 refused. It costs one cleared field | **Build the removal** (PRIV-2). A notice that cannot be acted on is not a notice | Surbhi |
| M2 | **Does the documents section go to HR roles only, independently of who may open Positions?** | Yes. It is the only control that makes the child-table trap survivable, and at DTC it changes nothing because the audience is already HR Manager | **HR roles only** (SEC-3). If a tenant later wants a manager role to see documents, that is a new decision with a new review | Surbhi |
| M3 | **Is `Employee Document Type`'s HR-Manager write acceptable, or does the tick move off that doctype?** | It moves. HR Manager can write that doctype today, and HR Manager is the DTC Positions audience, so a Check there is a bypass of the System-Manager-only rule | **A `DefaultValue` key in the access-granting set** (SEC-5). This contradicts OPS-5 and the reason is a permission row, not taste | Surbhi, with DevOps |

**Should know.**

| # | Question | Default meanwhile |
|---|---|---|
| S1 | How long is the document-open record kept? Counsel's 18 Sep policy does not cover access logs, and the existing photo access log has no retention at all | **Keep it.** Deleting it destroys the only evidence of snooping |
| S2 | Is the birthday / anniversary reminder on at any tenant? It puts a `/private/files/` photo URL in an email body to colleagues (`employee_reminders.py:180`, `birthday_reminder.html:7`). **I could not check: that is production** | PRIV-1's wording names birthday messages, so the notice is true either way |
| S3 | Is `BACKUP_BUCKET` set? It decides whether every photo and every scan also leaves the server on every deploy (`07` §4; DevOps could not check a repository secret) | Nothing in the build changes. It changes whether the privacy notice is complete |
| S4 | Who sends the pre-onboarding invite, and over what — email, or WhatsApp? | Email: it is the only channel this product has. A copyable link covers the rest |

**Nice to know.** The design says `Employee Document Type.category` holds values outside its
own option list. I read the doctype JSON: the Select offers **seven** options and "Company
Issued" is one of them, so PPJ's data is inside the list after all. A small correction, no
consequence.

---

## 12 · Residual risk

Named, owned, dated. An accepted risk with a name and a date is governance; an unnamed one
is an accident waiting for an owner.

| # | Risk | Severity if it happens | Owner | Accepted on | Label |
|---|---|---|---|---|---|
| R1 | **A private file URL fetched directly still asks only the parent Employee's read permission.** SEC-3 removes the audience for whom that matters; it does not close the route | P1 if a tenant ever widens Positions read without revisiting SEC-3 | Surbhi | 31 Oct 2026, if she accepts SEC-3 | **Intentional trade-off** — the alternative is changing the `Employee Document` data model, which is not this slice |
| R2 | **Faces appear on ten surfaces, including a company-wide directory, the moment the first photo is uploaded.** The widest audience was authorised in slice 045 when the field was always empty | P2 — authorised, but nobody has looked at it since the data became real | Surbhi | 31 Oct 2026 | **Acceptable simplification**, on the condition that PRIV-1's wording names those surfaces |
| R3 | **No malware scanning on an upload from an unauthenticated caller.** Type allow-list, magic bytes, size ceiling, private storage and attachment-only serving are the controls; no scanner | P2 | Surbhi | 31 Oct 2026 | **Intentional trade-off.** Removed by an anti-virus step if a customer ever requires one; do not claim scanning in a questionnaire |
| R4 | **The retention period for a pre-onboarding submission is unknown.** Built, switched off, guarded by PRIV-7 | **P1 if the form is ever switched on at a real tenant before counsel answers** | Surbhi, with counsel | open | **Dangerous debt — escalate now.** It is not sitting quietly in this table: ⚠ COMPLIANCE 2, and PRIV-7 is the only thing standing between the gap and a pile of strangers' Aadhaar scans |
| R5 | **The breach runbook has never been drilled**, and this slice adds the first inbound public write path. CERT-In's clock is **6 hours from awareness** | P1 on the day it matters | Surbhi | standing | **Temporary debt.** Removed by one drill. A runbook that has never been exercised is a document, not a capability |
| R6 | **No break-glass control over the sites volume.** Anybody with bench access reads every photo and every scan | P2 | Surbhi | standing, unchanged by this slice | **Intentional trade-off** at this size |
| R7 | **A wrong tick on the settings card is found only by somebody reading the page.** One-click removal was refused (31 Oct 2026), so the standing amber warning is now the sole detection | P2 | Surbhi | 31 Oct 2026 | **Intentional trade-off.** The warning must therefore name the count, the categories and the audience, on the page, every time — not only inside the dialog |
| R8 | **The document-open record has no retention**, like the photo access log beside it | P3 | Surbhi | 31 Oct 2026 | **Temporary debt**, removed by S1's answer |

---

## 13 · Subtract pass — what I removed

Read back once, asking only what can be deleted and still meet the requirement.

**Removed:**

- **A new CI gate.** My first draft proposed a scanner for photo URLs in email templates and
  a page-weight gate. Deleted: `check_scope_traps.py`, `check_api_paths.py`, the
  `ignore_permissions` ceiling in `test_portal_security_010` and the demo-password check
  already cover the mistakes this slice can make, and a fifth gate nobody reads is worse than
  four that fail honestly.
- **A versioned privacy-notice object, a per-employee record of which notice version they
  saw, and a consent ledger.** Deleted. The baseline lists them as DPDP capabilities and they
  will be a slice of their own one day. For this slice the lawful basis for an employee photo
  is the employment relationship, and one accurate sentence meets the notice duty. Building a
  notice-versioning engine here would be rung 5 for a rung-4 job.
- **A new DocType for the document-open record.** Deleted — PRIV-5 extends the existing
  `Alvoraa Photo Access Log` with two columns.
- **A new DocType for the retention setting.** Deleted — a `DefaultValue` key and the
  existing switch-precondition mechanism.
- **A separate EXIF-stripping step and an image library choice.** Deleted — the re-encode in
  SEC-6 does the resize and the strip in one call, which is also DevOps' OPS-7 and OPS-8 in
  one.
- **A bespoke rate limiter, a CAPTCHA, and an IP allow-list for the public form.** Deleted —
  `field_app_limits` already exists, already hashes its key, and already exposes its limits
  to a test.
- **A purpose-tag table and a field-sensitivity DocType.** Deleted for this slice. The two
  closed allow-lists (SEC-1, SEC-7) do the same job here in two constants, and a
  classification mechanism with two users is a mechanism nobody maintains. I will say plainly
  that the moment a third list appears, the constants should become one table — but that is a
  statement about a future requirement, and there is no future requirement, there is this one.
- **A fifth SEC requirement for the enlarged photograph.** Deleted. It fetches the same
  bounded JPEG the drawer already has, to the same reader, with no download, no new-tab and no
  save action — SEC-6 and PRIV-4 already cover everything it does.
- **Two abuse cases** about tenant isolation. Deleted: every surface here is inside one site,
  and the public page reads branding from site config only. Padding the list with a
  cross-tenant case would have buried the two that matter (A2 and A4).
- **An "AI path" static gate.** Reduced to a test assertion inside the slice's own module
  (PRIV-3). A gate implies a pipeline; this is three greps in a test.

**Not removed, and why:** SEC-13 (the existence oracle) looks like padding beside SEC-9, and
it is not. A token system with perfect token handling and a chatty error message still tells
a prober which of a tenant's people are being hired, and that is a different disclosure with a
different fix.

---

## 14 · What I could not verify, and the access I would need

Said plainly, because each of these is a finding in its own right.

1. **Frappe's private-file permission path.** I did not read
   `frappe/core/doctype/file/file.py` or `frappe/permissions.py` myself — **Frappe's source
   is not in this worktree**; only `hrms`, `alvoraa_portal` and `alvoraa_goals` are. Every
   claim about the parent-permission fallback rests on DevOps' read of the running image
   (`07` §1 point 3 and §3), which cites exact line ranges. *Access I would need:* a read
   inside `hrlocal-bench`. **SEC-4 makes that read an explicit half-day job at the strategy
   gate**, because lesson 5 applies: a wrong explanation sends the next person to the wrong
   file.
2. **DTC's actual permission rows.** `Alvoraa Position` read at DTC is HR Manager per
   Surbhi's answer of 31 Oct 2026; the `Custom DocPerm` rows are on production and I did not
   and will not look. Once any custom row exists, Frappe ignores the shipped rows entirely
   (`frappe/permissions.py:528-529`, per DevOps). So SEC-3 deliberately does not depend on
   that answer.
3. **Whether the birthday reminder is on anywhere.** Production. S2.
4. **`BACKUP_BUCKET`.** A repository secret. S3.
5. **I ran nothing.** No bench command, no browser, no container. Everything above is
   *verified in code* at the cited file and line in this worktree on 31 Oct 2026, or
   explicitly attributed to DevOps' or UX's measurement, or labelled `[ASSUMPTION]`.
6. **The 90-day placeholder** in the prototype's joiner notice is ours, not counsel's, and
   PRIV-7 exists so it never reaches a real joiner.

**One governance note, as the rules require.** I wrote these requirements; I must not be the
only person who verifies them at `06`. The pieces where a second pair of eyes matters most are
**SEC-3's reasoning** (that the HR-role gate makes the child-table trap survivable) and
**PRIV-7's proof-of-deliberate-setting** (that a missing `Version` row really is impossible
to fake through the normal UI). Both are arguments, not measurements, and I made them.

---

# Addendum · 31 October 2026 (evening) · The joiner form asks the whole My Profile list

**Author:** `hrms-security-privacy-engineer`. **Status:** advice and requirements, with her
answers of the same evening folded in. Recommendations only — **Surbhi decides.**
**Written in two passes on one day. Both are kept, in order, because the second pass
narrowed the first and the reasoning for each is worth reading once.**

**Trigger, morning:** Surbhi's decision of 31 Oct 2026, in two parts. (1) HR may mark fields
and document types **required**, on My Profile and on the joiner form — with UX now. (2) The
joiner form asks **the whole My Profile field list**, not the fixed seven. She was shown the
consequence — as first taken, the list could include a statutory field such as PAN or
Aadhaar, asked on a page opened by somebody who is not yet an employee, replacing 078-PRIV-9
— and she chose it. **Nothing below re-opens that.** She then asked how to do it wisely.

**Trigger, evening:** she answered the three must-know questions this advice raised, and
**all three went the cautious way** — its own tick, HR-only fields excluded, and **no typed
statutory field at all** because a photograph of the card is enough. A0 records them as
settled decisions; A0.1 records the much smaller risk they bought.

## A0 · Settled — Surbhi's three answers, 31 October 2026 (evening)

**All three went the cautious way. They are decisions, not options, and the rest of this
addendum follows them.**

| # | Question | **Her answer** | What it settles |
|---|---|---|---|
| **M5** | Does the joiner form share the My Profile tick, or get its own? | **Its own tick.** One candidate list, ticked twice — once for My Profile, once for the joiner form. `alvoraa_joiner_fields`, shipping empty | 078-SEC-17 as recommended. ⚠ closed |
| **M4** | May the public form ask for an **HR-only** field? | **No. Excluded.** | **078-PRIV-10a is the rule. PRIV-10b is deleted** and survives only as a one-line record of what was considered and rejected. ⚠ DECISION 078-G closed |
| **M7** | Will anything ever read a statutory number **as data**? | **No — a photograph of the card is enough.** So **no typed statutory field is offered on the joiner form at all**; the need is met by the document upload that is already built and tested, which HR can now mark required | 078-PRIV-11's deny rule now **also covers statutory identity number fields**. ⚠ COMPLIANCE 4 narrows to documents. M6 falls away |

**The sentence that should stop this being reopened in six months, written plainly:**
an HR-only field on the public joiner form was the **one move in this change that defeats a
control rather than widening a list** — 078-SEC-7's `constant ∩ permlevel-0 write`
intersection, the thing that keeps a self-service screen from becoming a way round field
rights (`people_fields.py:17-24`, US-6, ALV-215), **does not exist on a guest path at all.**
There is no permission level on a page opened without a login. That is why HR-only fields are
excluded, and it is not a matter of taste.

### What I advised this afternoon, and what superseded it

Kept with its reasoning intact, because a superseded recommendation that quietly disappears
is how the same ground gets argued twice.

> **What I advised:** ship it as asked, but ship the cautious ticks as the default — the
> ordinary things on the public link, **and PAN as well, because it is the market pattern and
> there is a real payroll reason for it** — leaving Aadhaar and anything to do with money
> unticked, with the joiner list as its own tick, everything reversible by a tick rather than
> a release.

**Superseded by her M7 answer.** Two of the three parts survive and are now requirements: the
separate tick, and the cautious default. The part about **PAN as a typed field does not.**
Nothing will read the number as data, so a column buys nothing and costs a searchable,
reportable, exportable field on a table a stranger can write to. **The market point still
stands — it is why the *document* covers this need, not why a column should exist.**

## A0.1 · The residual risk now — and her three answers bought the difference

**A stolen link now carries contact details, an emergency contact, and whatever cards the
joiner chose to upload.** No statutory number as a field, no HR-only field, and **nothing at
all until a tenant ticks it** — the joiner list ships empty and the whole form ships off.
That is close to where the form stood this morning under 078-PRIV-9, reached by a route that
leaves HR in charge of the list instead of us. The uploaded card is the real remaining
payload, and it is covered by controls that are already built and tested: private storage,
magic-byte checks, re-encoding that strips metadata, attachment-only serving, size and count
ceilings, and an erase job with legal hold. **The three cautious answers are what bought
that**, which is the argument for leaving the defaults where they are.

<details>
<summary>What the risk would have been without those three answers — kept for the record</summary>

A joiner's invite link is a **bearer link** — whoever holds it, inside its window, can open
that one joiner's form. Until today it was worth seven ordinary contact details; under the
decision as first taken it would have been worth **whatever HR had ticked, including a
statutory identifier**, and a stolen link also leaks the joiner's name because the form
pre-fills it. The expiry (HR's setting, 7 days by default), the single use, the by-hand HR
invite and the whole form shipping **off** bound how long the window is open and how many
links exist — **they do not bound what is behind the link**, and only the field list does
that. So the risk would have been this: for as long as one live link existed, a forwarded,
shoulder-read or screenshotted link would hand over the ticked list in full, and if that list
named Aadhaar or PAN, that is an identity-theft payload rather than a contact card.

</details>

## A0.2 · The four approaches, weighed by name — and which one she chose

**Chosen: option 1, with option 3's refusal, and the number asked for as a document rather
than a field.** The table below is kept as the reasoning, with her decision marked on it.

| # | Approach | What it buys | What it costs | Verdict |
|---|---|---|---|---|
| **1** | **Two stages.** Public link asks harmless things only; anything statutory is asked after hire, signed in, inside the portal | The public surface stays roughly where it is today. Every existing control — login, permission level, field rights, the audit trail — applies to the statutory half. Smallest change | HR chases documents in a second pass. And it is **slightly behind market practice**: Indian HR tools do collect PAN at pre-boarding (A0.3), and PAN specifically has a payroll reason — without it the first salary is taxed at a penal flat rate rather than the person's slab | **CHOSEN (31 Oct 2026), and as a rule rather than a default** — no typed statutory field is offered at all. The second-pass cost is smaller than I assumed, because the **card can still be collected on the public form as a document**, and HR can mark it required |
| **2** | **Bind the link to the person.** An OTP to the mobile HR holds, once, before the form opens | A forwarded or shoulder-read link stops being enough on its own. It is the only option here that answers a **stolen** link rather than shrinking the prize | A new SMS dependency, a cost per invite, a dead end for anybody whose number HR typed wrong, and one more hurdle for a frontline joiner on a weak signal. We have no SMS channel today — email is the only channel this product has | **Not now.** The 7-day single-use expiry is proportionate while the list is ordinary. **Revisit the day Aadhaar is ticked** — then the prize justifies the friction. Recorded as the named trigger, not as a no |
| **3** | **Guard rails on what HR can tick** | Stops money, bank and health data reaching a public page whatever anybody ticks, for ever, in about thirty lines | Almost nothing — the mechanism exists (`people_fields.NEVER` + `is_denied()`) | **CHOSEN, as a refusal**, and **now wider than I proposed: statutory identity number fields are in the deny rule too**, on her M7 answer. See the next paragraph |
| **4** | **Build it as asked, nothing extra** | Exactly what she decided, in the fewest lines. HR has complete freedom | One paragraph, no hedging, below | **Not chosen.** And after M7 it is **no longer one tick away** — see A0.4. A0.5 is kept as the record of what it would have meant |

**Why a refusal in option 3 is not us inventing a rule.** The joiner list is now the My
Profile list, and **the My Profile list already excludes money, bank, health, date of birth
and marital status** — that was Surbhi's own earlier decision, and it is in the code
(`people_fields.py:62-74` and the `NEVER` tuple at `:84-112`). So the refusal pins what is
**already true today**; it invents nothing. What it adds is that the public page keeps that
boundary **even if the My Profile list is widened later for employees**. **Updated 31 Oct
2026 (evening): statutory identity number fields are now in the refusal too**, on Surbhi's
M7 answer — nothing will read such a number as data, so there is no reason for one to be a
column on a guest-writable table. That is her decision being implemented, not me overruling
it; the earlier draft left statutory out precisely because it was hers to decide.
A click-through warning was considered and rejected: a dialog
that a System Manager dismisses on the way to doing what they intended is worth nothing. The
**standing amber line** the document-types card already uses is worth something, because it
is on the page every time somebody looks (`people_settings.py:82-90`).

**Have I missed an option? One, and it is worth naming — and it is the one she chose: ask
for the number as a document, not as a field.** The product already collects identity papers as files under HR's existing
verification flow. A photograph of a PAN card is the same disclosure as a typed PAN number,
but it is **not a searchable, reportable, exportable column** on a table a stranger can
write to, and it is already covered by the upload controls that were built and tested. If
HR's real need is "I want the PAN before day one", the file already meets it. The typed field
only adds value if something later reads the number as data. **If nobody will, do not add the
column.**

**That is what she answered, and it is the simplest answer that beats all four.** HR's
purpose is *"don't make me retype this from paper on day one"*. Options 1 + 3 + "as a
document" cover it completely, so option 4 buys nothing we need. **The typed statutory
column is therefore not built, and the deny rule refuses it** (078-PRIV-11).

## A0.3 · What comparable products do

**Searched today, 31 Oct 2026. Label: mostly vendor marketing and practitioner blogs, not
a standard.** I found no authoritative best-practice standard, and I am reporting the
pattern rather than endorsing it.

- The conventional Indian pattern is **the opposite of my instinct**: PAN, Aadhaar and bank
  details are collected through a pre-boarding portal **after the offer is accepted and
  3-5 days before joining**, not after day one. So **asking before day one is in line with
  the market**, and "nothing statutory before day one" would have put us behind it.
  **Read correctly after her M7 answer:** the market point is about *timing*, not about
  *shape*. We still collect it before day one — **as a photograph of the card, which the
  product already handles**. Nothing in these sources says the number must be a typed,
  searchable column, and we have no use for it as one.
- **PAN has a concrete payroll reason.** One source states that without PAN before the first
  salary, tax is deducted at a flat penal rate rather than the person's slab. That is a
  business reason to allow PAN early, and it is why I recommend allowing it rather than
  deferring it. **I have not verified the tax rule against a primary source** — it is not
  mine to state — but it does not need to be verified to justify leaving the choice to HR.
- **Where those products differ from us is identity binding, not field lists.** Several
  vendors describe Aadhaar **OTP / eKYC** verification during pre-boarding — i.e. they do
  option 2 as a matter of course once Aadhaar is involved. That is the strongest support for
  the trigger I recommend: ordinary fields on an expiring link, and an OTP the day Aadhaar
  is ticked.
- Several sources also stress **explicit consent before any identity verification**. That
  matches 078-PRIV-13 below and ⚠ COMPLIANCE 4.

Sources: [SalaryBox — onboarding process in India](https://salarybox.in/employee-onboarding-process-in-india-2026-complete-checklist-compliance-documents-best-practices/) ·
[Keka — new hire preboarding checklist](https://www.keka.com/new-hire-preboarding-checklist) ·
[Wisemonk — onboarding checklist, hiring in India](https://www.wisemonk.io/blogs/employee-onboarding-checklist-2024-hire-in-india) ·
[Ascent HR — UAN/Aadhaar in onboarding](https://ascent-hr.com/resources/in-the-press/ensuring-compliance-in-employee-onboarding-through-uan-aadhaar-integration/) ·
[Meon — Aadhaar-based onboarding API](https://meon.co.in/aadhaar-based-employee-onboarding-api)

## A0.4 · What changing our mind later costs

**This was the argument that settled the choice, and her M7 answer changes one row of it.
Said plainly rather than left to be discovered:** widening to the ordinary fields later is
still one tick, because the field list is a `DefaultValue` key in the existing
access-granting set. **Adding a typed statutory field later is no longer a tick — it is a
code change**, because the deny rule now refuses those names. That is the intended effect of
her decision, and it is a feature: the expensive direction is the dangerous one.

| Move | Cost |
|---|---|
| The shipped empty tick → more **ordinary** fields | **One tick. No code.** A `Version` row records who did it and when |
| → a typed **statutory** field (option 4) | **A code change, a review and a release** — the deny rule refuses the name, in the setter and again in the reader. Deliberate, after her M7 answer |
| Untick, after a scare | One untick. No code. **But anything already collected has already been collected** — that is the asymmetry, and it is why the default matters more than the ceiling |
| Add option 2's OTP later | A real piece of work: a new SMS channel the product does not have, a cost per invite, and two new screens. Days, not hours |
| Add the refusal list later instead of now | Thirty lines, but it has to be retro-fitted into a running form, and a tenant may already have ticked something it bars |

**So: cheap to loosen, cheap to tighten, expensive to retrofit identity binding, and
impossible to un-collect.** Ship the cautious ticks and the refusal list now; leave the
OTP as a named trigger.

## A0.5 · Option 4, **not chosen** — what it would have meant, no hedging

*Kept as the record of what was weighed, and of why the deny rule is worth its thirty lines.
This describes a path the 31 Oct decisions close.*

We would be accepting that **any live invite link is, in effect, a bearer credential for one
named person's full identity record**: whoever holds it within its window can read the
joiner's name and submit, or read back nothing but learn the name, and if HR has ticked
Aadhaar and PAN then a single forwarded WhatsApp message, a screenshot in a photo roll, or a
glance over a shoulder in a queue is enough to put a real person's statutory identifiers in
somebody else's hands — with no login to revoke, no second factor, no record that it
happened, and no way for us to tell the wrong holder from the right one. We would also be
accepting that those identifiers become ordinary columns on a doctype that HR Manager can
**export to a spreadsheet** from Desk, that we hold them for a period counsel has not been
asked about in this form, and that the first time anyone finds out something went wrong will
be when a joiner tells their employer. The guards that remain are real but all upstream of
the payload — HR creates each link by hand, the name is pre-filled, the link expires on HR's
setting, it is single use, and the whole form is off until a tenant switches it on — and
none of them makes the contents smaller. That is a defensible position for a Processor whose
Controller has instructed it; it is not a position I would choose for a default.

## A1 · 078-PRIV-9 is superseded, not deleted

**PRIV-9 as written** (§7 above): the joiner's field list is a closed server allow-list of
seven, with no statutory identifier as a typed field. `JOINER_FIELDS` is that list
(`alvoraa_joiner_submission.py:32-41`), and
`test_the_allow_list_has_no_bank_salary_or_statutory_field` asserts both the names and
`len(...) == 7`. The test report marks it **Met**, twice over — in Python and in the browser
payload (`04` §5.3, §7.2).

**What PRIV-9 actually bought.** Not confidentiality — the page was already token-gated. It
bought a **cap on the blast radius of a tick**: no HR choice, no settings mistake and no
future UI could make the public page ask for more than seven ordinary fields. The worst case
was known in advance.

**It is superseded because the decision removes the cap by design.** HR now chooses. What
replaces the cap is **(a) a narrower source list, (b) a separate deliberate tick, (c) a deny
rule no tick can cross, and (d) a visible standing warning** — 078-SEC-17, 078-PRIV-10,
078-PRIV-11 and 078-PRIV-14 below. PRIV-9 stays in §7 exactly as written, so the history
reads honestly: it was met, and then it was traded away for a feature, deliberately, on a
dated decision.

## A2 · The replacement control — the mechanism, in one paragraph

**One candidate list. Two separate ticks. One deny rule. One standing warning.** The
candidate list stays `people_fields.MY_PROFILE_WRITE_FIELDS` — one source of truth, extended
by the required-fields work, never copied. The **joiner tick** is its own key,
`alvoraa_joiner_fields`, in the existing `ACCESS_GRANTING` set
(`alvoraa_org_structure/settings.py:89-94`, `:172-231`): System Manager only, refusal
logged, one `Version` row per real change, **ships empty**. The **deny rule** is a narrow
tuple plus a function beside `NEVER` in `people_fields.py`, applied in the setter **and
again in the public reader** — the second application is the only half that survives a
future UI. The **standing warning** copies the document-types shape (AC-84,
`people_settings.py:82-90`): on the card, always, no dialog to open. **The deny rule now
covers statutory identity number fields as well** (her M7 answer, 31 Oct 2026 evening).

**Rung on the ladder: 2 · configuration.** One new settings key reusing a mechanism that
works today, one tuple, one function. Rung 3 (a per-field Check on a doctype) is rejected for
the reason 078-SEC-5 already gives — HR Manager can write those doctypes in Desk. Rung 5
(a per-field sensitivity classification, which is compliance-map A1 and the right long-term
shape) is rejected as rung 5 for a rung-2 job with one user — and after M7 it has nothing
left to classify here, because the only field class that needed a judgement call is now
simply refused.

**Why separate ticks matter more than they look.** With one shared tick, the day HR adds a
field to My Profile so employees can correct it, that field appears on a **public** page.
Two ticks make public collection its own deliberate act. That is DPDP s.6(1) minimisation
expressed as a mechanism rather than as a reminder.

## A3 · The HR-only question — **settled: excluded** (Surbhi, 31 Oct 2026)

**Decided. HR-only fields do not appear on the public joiner form.** ⚠ DECISION 078-G is
closed. **078-PRIV-10a is the rule; PRIV-10b is deleted.** My reasoning carried the decision
and is kept below, because the first reason is the one that should stop this being reopened:
**there is no permission level on a page opened without a login, so 078-SEC-7's
`constant ∩ permlevel-0 write` intersection — the control that keeps a self-service screen
from becoming a way round field rights (ALV-215) — does not exist on a guest path at all.**
Putting an HR-only field there defeats a control rather than widening a list.

1. **A field the employee themselves may not fill is strictly worse asked of a stranger.**
   "HR-only" means *this is HR's record of the person, not the person's own claim*. The
   joiner form has no login, no permission level and no identity proof. 078-SEC-7's permlevel
   intersection — the thing that stops a self-service screen becoming a way round field
   rights (`people_fields.py:17-24`, US-6, ALV-215) — **does not exist on a guest path.**
   This is the one move in the change that defeats a control rather than widening a list.
2. **Provenance.** An HR-only field is usually something HR verified. A value typed by
   whoever held the link, landing in the same column, destroys the difference between
   *claimed* and *checked* — and that difference is what defends HR a year later.
3. **It is not needed for the purpose.** The purpose is "HR does not retype a joiner's
   details from paper". HR-only fields are not the joiner's details.

**The rule, as decided:**

- **078-PRIV-10a — the rule.** The joiner candidate list is `MY_PROFILE_WRITE_FIELDS`
  **minus every field marked HR-only**. An HR-only name is **refused** at the setter and
  **ignored** by the public reader, so a name forced into `DefaultValue` by any other route
  produces nothing.
- **078-PRIV-10b — deleted, recorded only.** It would have allowed an HR-only field in its
  own joiner column, with the amber line naming it and HR's review screen labelling the value
  *"typed by the joiner, not checked"*. **Considered and rejected on 31 Oct 2026.** Written
  down so nobody rebuilds it believing it was never thought about.

## A4 · DPDP consequences, concretely

**I am not a lawyer.** Counsel's answers to date have been **oral, relayed by Surbhi** — the
25 Oct "OK with our approaches", and the 29 Oct 2026 closure of ⚠ COMPLIANCE 2 with a
**180-365 day range** for a not-hired submission (`03` §8). Nothing is in writing.
**ALV-215 still gates switch-on.** What follows says where this change creates a question
the oral answers did not cover.

**1 · Notice and purpose limitation on a public form.** 078-PRIV-8 is built and proved: the
notice precedes the first input in the DOM, carries the configured numbers and a real
employer contact (`04` §5.3). It survives this change **in shape and fails it in content**,
because it describes "your details" while the page now asks for whatever is ticked. Purpose
limitation (DPDP s.6(1)) is a per-item duty: a joiner told *"so we can make your staff
record"* has not been told why a photograph of their PAN card is wanted. **078-PRIV-13**
makes the notice render from the actual ticked lists — **fields and document types** — in
plain words, with a reason per sensitive item.

**2 · What a joiner who never gets hired has a right to.** Unchanged in kind, heavier in
substance. They may know what is held, have it corrected, and have it erased when the purpose
ends (DPDP s.8(7), s.12). The product already answers all three — the not-hired erase keyed
on `closed_on`, HR's **Purge** button which ignores legal hold because there erasure is the
obligation, and the employer contact in the footer (`03` §8). **What changes:** the erase must
cover **every** new column, which is why **078-PRIV-14** derives `strip_personal_fields` and
the erase job from the one constant instead of a hand-kept list. A forgotten column is a
retained personal detail, and a forgotten `File` is a retained Aadhaar card.

**3 · Does it change the retention answer?** **The number, no. The question, yes — and her
M7 answer narrows it to documents without removing it.** Counsel's 180-365 range was given on
29 Oct for *a joiner's details* as the form then stood — seven contact fields. Counsel was not
asked about **photographs of identity documents held for up to 365 days about a person who was
never employed**. I am not qualified to say whether the same range applies; I can say the
question changed after the answer was given. **⚠ COMPLIANCE 3.** Fail-closed meanwhile: **do
not tick a statutory document type at any tenant with real joiners** until there is a written
answer.

**4 · Does asking for a statutory document before employment change our processor framing?**
**In framing, no. In obligations, yes, in two specific ways.** The customer is the Controller
and decides what to ask; we supply the tool and the settings (`03` §8.1). That is the same
whether the ask is a mobile number or a photograph of a PAN card. But: **(a)** our shipped
default is the Processor's operating choice until a Controller changes it, so the joiner tick
must ship **empty** (078-PRIV-10). **(b)** Aadhaar is not an ordinary document. There is a
separate statutory regime about who may collect an Aadhaar identity and how it may be stored
and displayed, and **that regime does not stop applying because the number arrives as an
image rather than as text.** **I will not state it from memory, and I have not verified it
against a primary source.** **⚠ COMPLIANCE 4.**

### ⚠ COMPLIANCE 3 — the retention period, re-asked **about documents**

**Still needed after the 31 Oct decisions.** The typed column is gone; the **uploaded card
raises the same retention question**, and counsel's answer of 29 October was given about
seven contact fields.

*Question, in one line:* "Your 180-365 day range of 29 October was given for a joiner's name,
contact details and emergency contact. Does the same range apply when the submission also
holds **photographs of identity documents** — a PAN card, an Aadhaar card — for a person who
was never employed, and if not, what is the shorter period?"
*Owner:* counsel, via Surbhi. *Blocks:* ticking a statutory **document type** for the joiner
form at a tenant with real joiners. **Not the build.**
*Fail-closed default meanwhile:* the joiner tick and the document-type list ship empty; no
statutory document type is ticked at a real tenant; the configured not-hired period and the
backstop both already run, and both already take the files with them (078-PRIV-14).

### ⚠ COMPLIANCE 4 — Aadhaar specifically, and in writing this time

**Narrowed by her M7 answer, not closed by it.** The question is no longer about a typed
field; it is about the **card**.

*Question:* "May our customer, as the employer, ask a prospective employee to upload a
**photograph of their Aadhaar card** before they are employed, and store it in our system;
are there conditions on storage, masking or display; and does any of it bind us as the
Processor? The same question for a **PAN card**, which we believe is ordinary."
*Owner:* counsel, via Surbhi. *Blocks:* offering an Aadhaar document type on the joiner form
at a tenant with real joiners.
*Why it is still live:* 078-PRIV-9 made it moot by collecting nothing statutory at all. The
new form collects the card. **An image of an identifier is still the identifier.**
*Fail-closed default meanwhile:* **no Aadhaar document type is ticked for the joiner form**
until there is a written answer; a PAN card type may be offered, unticked. If Surbhi wants
Aadhaar offered first, that is hers to record, and it is a **P1 at review**.

## A5 · Threat model deltas — what a stolen link is now worth

The page is unchanged in shape. Every guard re-verified in code today:

| Guard | Verified in code, 31 Oct 2026 |
|---|---|
| The link exists only because HR made the row by hand, typing the name | `joiner_invite.py:142-164` |
| The joiner's name is **pre-filled** from that row | `joiner_public.py:188`; `joiner.html:267-268, 305` |
| Expiry, HR's setting, 7 days by default | `joiner_invite.py:155-156, 170` |
| 32 bytes from `secrets.token_urlsafe`, minted by Frappe, single use, the key's row destroyed on submit | `joiner_invite.py:166-175`; `04` §7.1 SEC-9 |
| Token in the fragment, POSTed in the body, out of the address bar | proved in a browser, `04` §5.3 |
| The whole form ships **off** behind a setting | `04` §7.2 PRIV-7 |

**So the delta is not access. It is prize** — and **her three answers of 31 Oct shrink three
of the four movements back down.** Both columns are kept, because the "would have been"
column is what the deny rule is paying for.

| # | Before today | Without her answers | **As decided, 31 Oct evening** |
|---|---|---|---|
| D1 | A stolen link yielded a name plus six ordinary contact fields | **The ticked list in full**, including a statutory identifier. The expiry bounds the window, not the contents | **Contact details, an emergency contact, and whatever cards the joiner uploaded.** No statutory column, no HR-only field, and nothing at all until a tenant ticks something |
| D2 | A stolen link was mostly a **nuisance** | An **identity-theft target**, worth seeking rather than stumbling on | **Still worth something** — an uploaded Aadhaar or PAN card is the identifier, just as an image. The incentive is lower than a typed, exportable column but it is not zero |
| D3 | `Web Form Request.key` stored **in clear** in Frappe's own row — the recorded SEC-9 deviation (`04` §7.1) — unlocked six contact fields | It unlocks the ticked list | **Unchanged and still open: whoever can read that table can open any live form**, and a live form now accepts document uploads. I could not check which roles may read it — Frappe's source is not in this worktree. **078-SEC-19** |
| D4 | Integrity was not interesting | A **false** statutory number typed against a real named person, burning the single-use link | **Mostly gone, not entirely.** There is no number column to falsify, but somebody in the window can still upload **somebody else's card** against a real joiner's row and burn the link. HR verifies the document anyway, which is what that flow is for |

**Two abuse cases to add to §5:**

| # | Actor and state | Path | What they get | Stopped by |
|---|---|---|---|---|
| A12 | **Whoever holds a forwarded, shoulder-read or screenshotted link**, inside its window | The public page | The pre-filled name, the ticked contact fields, and the chance to upload **somebody else's card** against a real person's row and burn the link | Nothing prevents it — it is a bearer link. Bounded by expiry and single use; **shrunk materially by PRIV-10 and PRIV-11 as decided** — there is no statutory column and no HR-only field to take; **SEC-12 extended** keeps the claim off the Employee record; HR verifies the document. **Option 2's OTP is the only control that answers the stolen link itself; the named trigger for building it is the day a statutory document type is ticked** |
| A13 | **Anyone who can read `Web Form Request`** on the site | Desk, or a report | Every **live** key, so every open form | **078-SEC-19** — confirm the readership before any statutory **document type** may be ticked |

**Two facts this analysis rests on.** (1) **There is no `Employee` record at invite time** —
the submission stands alone and HR creates the Employee by hand
(`joiner_invite.py:158-164`; SEC-12, Met). **My analysis does depend on that.** Hanging the
link off a real Employee row would put an unhired person into headcount, the chart and a
billable seat, and a back-dated joining date would make Frappe mark them Absent for every day
since — a logged DTC fault, not a theory. If that changes, these requirements must be
re-read. (2) **The pre-filled name means a stolen link leaks the name even if nothing is
submitted.** Small, and it belongs in the model rather than being found later.

**How would we find out?** For D1 and D2, honestly: we would not. A bearer link used by the
wrong person looks exactly like the right person using it. The limiter writes a refusal line
on volume (`field_app_limits.py`), and that is all. Named as residual risk R13; the
prevention that exists is a narrow list, a short window and a single use.

## A6 · New requirements

### 078-SEC-17 · One candidate list, two separate ticks, two intersections

The joiner's field list is a **separate access-granting setting**, `alvoraa_joiner_fields`,
chosen from the **same** candidate constant as My Profile
(`people_fields.MY_PROFILE_WRITE_FIELDS`). **No third list exists anywhere** — not in
`joiner_public.py`, not on the doctype, not in the page. `JOINER_FIELDS` as a constant of its
own is deleted and replaced by a read of the tick.

- The key joins `ACCESS_GRANTING` (`settings.py:89-94`): System Manager only; anybody else
  refused and logged with rule `078-SEC-5`; one `Version` row per real change.
- The setter refuses an off-candidate name. **The public reader intersects again** through
  `people_fields.allowed()`, so a name written straight into `DefaultValue` by any other
  route produces nothing on the page and stores nothing.

*Test:* assert the joiner candidate list **is** `MY_PROFILE_WRITE_FIELDS` (the same object,
not a copy); an HR Manager calling the setter is refused and the refusal line asserted; a
System Manager's change writes exactly one `Version` row; `frappe.db.set_default` writes
`ctc` into the key directly, then `open_invite` returns a field list **without** it and
`submit_invite` stores nothing for it. **That last test is the one that matters** — it is the
only half that survives a future UI.

### 078-SEC-18 · "Required" never widens what may be written or asked

Marking a field or document type **required** changes only whether a form may be sent without
it. It must not add anything to either allow-list, must not raise a permission level, and must
not make an HR-only or permlevel-1 field employee-writable: SEC-7's
`constant ∩ permlevel-0 write` intersection stands untouched (`people_fields.py:17-24`,
US-6). A required mark on a field that is **not** ticked is ignored, never a reason to show
it.

*Test:* write `ctc` into the required key directly; assert it appears on neither form and is
written nowhere. Mark an HR-only field required; assert an ordinary employee still cannot
write it through the My Profile save endpoint and the stored value is unchanged.

### 078-SEC-19 · Confirm who can read `Web Form Request.key` before any statutory **document type** may be ticked

Frappe stores the invite key **in clear** on its own `Web Form Request` row — the recorded
SEC-9 deviation. Whoever can read that row can open any live joiner form. **I could not check
which roles may read it: Frappe's source is not in this worktree** (only `hrms`,
`alvoraa_portal` and `alvoraa_goals` are). *Access I would need:* a read of
`frappe/website/doctype/web_form_request/web_form_request.json` inside `hrlocal-bench`.

One job, under an hour, at the strategy gate: read that JSON in the running image and record
the answer in the strategy note. **If any role below System Manager can read it, no statutory
**document type** may be ticked for the joiner form until that is closed** — by a permission
row, or by not offering the type. (Re-expressed after the 31 Oct decisions: there is no typed
statutory field left to gate, and the uploaded card is what a live key now reaches.)

*Test:* assert the permission rows of `Web Form Request` are what the strategy note recorded,
so the day an upgrade widens them the build goes red rather than the exposure going quiet.

### 078-SEC-12, extended · No code ever copies a submission onto an Employee

SEC-12 is Met and stands: a submission never becomes an Employee by itself, and no joining
date comes from the form. **This change makes an addition necessary**, because a longer field
list makes a "create the employee from this" button genuinely tempting — and that button
would copy an unverified, possibly attacker-typed statutory identifier onto the personnel
record.

**No code path writes a submission's field value onto an `Employee` record.** HR reads the row
and types, or does not. A copy feature, if ever wanted, is a new slice with its own review.

*Test:* a static test over the joiner modules asserting no assignment from a submission field
to an `Employee` field, and no `Employee` insert or `db_set` anywhere in them; plus the
existing `test_submitting_creates_no_employee_and_does_not_move_the_series`.

### 078-PRIV-10 · Supersedes 078-PRIV-9 · The page asks only what the joiner tick names, and it ships empty

The public page asks **exactly** the fields named by `alvoraa_joiner_fields`, in candidate-list
order, and nothing else. **The key ships empty at every tenant.** A tenant that switches the
form on and ticks nothing gets a form that asks for documents only — not one that quietly asks
for everything. We do not choose what a Controller collects (`03` §8.1).

**078-PRIV-10a — the rule (decided 31 Oct 2026):** the joiner candidate list excludes every
field marked **HR-only**; an HR-only name is refused at the setter and ignored by the reader.
**078-PRIV-10b is deleted** — recorded in A3 as considered and rejected, nothing to build.

*Test:* with the key empty, `open_invite` returns an empty `fields` list and J2 renders no
inputs; tick three and assert the endpoint, the rendered DOM and the submitted payload carry
exactly those three, in candidate order; post a fourth field name through the guest endpoint
and assert its **value** reaches no column (the shape `test_only_the_closed_allow_list_is_stored`
already uses). For 10a: assert an HR-only name is refused at the setter and absent from
`open_invite` even when forced into `DefaultValue`.

### 078-PRIV-11 · The public deny rule — what no tick may ever reach a public page

A narrow, named tuple beside `NEVER` in `people_fields.py`, with its own function. `NEVER`
itself cannot be reused as-is: it already contains `current_address`, `personal_email`,
`cell_number` and the three emergency fields, which are joiner fields today
(`people_fields.py:103-107`).

**Never on a public page, whatever is ticked and whatever the required mark says:** every pay
field (`ctc`, `salary_mode`, `salary_currency`, `payroll_cost_center`,
`employee_advance_account`); every bank field (`bank_name`, `bank_ac_no`, `iban`, `ifsc_code`,
`micr_code`); every health field (`health_details`, `health_insurance_no`,
`health_insurance_provider`, `blood_group`); `date_of_birth`; `marital_status`; **every
statutory identity number field — `pan_number`, `esi_number`, `provident_fund_account`, any
Aadhaar or UAN field, and anything of that kind, by name and by a `aadhaar` / `aadhar` /
`uid` / `pan` name match** (added 31 Oct 2026 on Surbhi's M7 answer); and **every field a
payroll rule set names**, read live through `rule_set_fields()`
(`employee_field_rights.py:125`) — a tenant that points a pay rule at a field has told us that
field decides money.

**This invents nothing.** Every name above is already excluded from the My Profile candidate
list today (`people_fields.py:62-74`, `NEVER` at `:84-112`). The tuple pins that boundary so
the **public** page keeps it even if the My Profile list is widened later for employees.

**Why statutory identity is now in the tuple, when the first draft left it out.** The first
draft left it out because it was Surbhi's to decide and she had decided to allow it. **On
31 Oct she answered M7: nothing will read such a number as data, so the need is met by the
document upload.** A column that nothing reads buys nothing and costs a searchable,
reportable, exportable field on a table a stranger can write to. The refusal is her decision
being implemented. **Collecting the card is still allowed** and is the intended route — it is
a `File` under HR's existing verification flow, with the controls that are already built and
tested, and HR can mark it required (078-PRIV-12).

**A name match, not only a list, and the reason.** `pan_number` and the other India fields
are **custom fields created by `hrms/regional/india/setup.py`** and exist only on an
India-regional tenant (`people_fields.py:77-82`). A pure name list is therefore both
incomplete — a tenant's own custom `aadhaar_no` would not be on it — and untestable without
the regional pack. The pattern match covers both.

Applied in the setter **and again** in the public reader.

*Test:* a table test posting **every** name in the tuple to the joiner tick, asserting each is
refused; then each written straight into `DefaultValue` and asserted absent from `open_invite`
and unstored by `submit_invite`; a test that a **made-up** statutory name — `aadhaar_no`,
`pan_card_number`, `uan` — is refused by the pattern **on a site without the India pack**, so
the assertion is never vacuous (A8); and one test that points a rule set at an ordinary field
and asserts that field becomes refused **with no code change**.

### 078-PRIV-12 · "Required" means required before day one, not required to send the form

**This requirement carries more weight after the 31 Oct decisions**, because the document is
now the **only** route by which a statutory identity reaches us — so the pressure to make a
required document a hard wall goes up.

A required **document type** must not be the only way the form can be sent. The right answer is
already drawn and built: *"I will bring it on my first day"* (`submit_invite`'s `bringing`,
J3/J6). A joiner who cannot photograph their PAN card on a phone in a queue must still be able
to send their details, with the document deferred, named back to them on J6 and recorded on the
row.

AC-110c stands: one field with a value, or one document. A required mark adds a **prompt and a
prominent reminder**, not a wall. Required **fields** may block sending, because typing is
free; required **documents** may not, because uploading is not.

*Test:* mark two document types required; assert the form can still be sent with both deferred,
and that J6 and the stored `bring_on_day_one` name both; assert a required field left blank
does block sending and the refusal names the field; assert a refused send **does not burn the
key** and the link still opens (AC-110a, AC-110b).

### 078-PRIV-13 · The notice itemises the real list, in plain words, in both languages

PRIV-8 keeps its shape — notice before the first question, configured numbers, a real employer
contact, refuse to render with no contact (built and proved, `04` §5.3). Three additions the
wider list makes necessary:

1. **The notice itemises what is asked and why**, generated from the ticked lists — **fields
   and document types** — so it cannot drift from the form. Where a statutory **document
   type** is ticked, its own line says why the card is wanted and what happens to it.
2. **Every candidate field and every offered document type has a plain-English label, a hint
   and a Hindi entry.** Today `joiner.html:304` falls back to `LABELS[f] || [f, ""]`, so an
   unlabelled item renders its **raw name** — a public page asking a frontline joiner for
   "pan_number", with no hint and no Hindi. **This matters more after the 31 Oct decisions,
   not less:** the statutory ask is now a *document type*, so the label and the Hindi must
   cover document types too, and a required document with no label is a required thing nobody
   can read. `Employee Document Type` carries a `description`, which is the natural place for
   the plain words — but a blank description must then fail the test, not fall back to a
   fieldname.
3. **The form says what it is not:** no account, no password, and the answers and uploads are
   a claim that HR checks — the plain-language half of D4.

*Test:* a static test over the candidate constant **and over every document type a tenant may
offer**, asserting each has a label, a hint and a Hindi entry, which fails the day one is
added without them; a DOM test asserting the notice lists exactly the ticked fields and
document types and precedes the first input (`compareDocumentPosition`, as the browser test
already does); assert the J2 and J3 screens never render a raw fieldname or a raw type name;
assert the notice renders no literal number.

### 078-PRIV-14 · One constant drives the warning, the erasure, the list view and the export

The amber line on the settings card, the erase job, HR's Purge, the list view and Desk's export
must all be **derived from the ticked list**, never from a hand-kept copy. A forgotten column is
a retained statutory identifier.

- **The standing warning** copies the document-types shape (AC-84, `people_settings.py:82-90`):
  on the card, always, no dialog — *how many fields the joiner form asks for, which of them are
  statutory, and the real roles that can read a submission* (System Manager, HR Manager, HR
  User — read from the doctype, not hard-coded).
- **Erasure:** `strip_personal_fields` and `erase()` iterate the **candidate constant**, not a
  literal list, so every column a tenant can tick is cleared by both the not-hired job and Purge
  (`alvoraa_joiner_submission.py:79-90`).
- **No statutory column in `search_fields`, and none `in_list_view`.** The submission list must
  never show an identifier, and nobody should be able to search people by one. The doctype has no
  `search_fields` today — keep it that way.
- **Export:** HR Manager holds `export: 1` and `report: 1` on the submission (doctype JSON, read
  today), so a widened list makes a Desk export of joiners a spreadsheet of statutory numbers.
  We are **not** building masking here (compliance map C1, not built). The requirement is
  narrower and achievable: the warning names it, and R11 records it as accepted.

*Test:* for every name in the candidate constant, assert `strip_personal_fields` clears it —
generated from the constant, so a field cannot be added without erasure; age a submission with
every field filled, run the job, assert **no** field value survives in the row or in any attached
`File`; assert `legal_hold` still wins for the job and still does not for Purge; assert the
doctype has no `search_fields` and no statutory `in_list_view`; assert the card's amber line names
the count, the statutory names and the roles read from the doctype.

## A7 · The CI gate that replaces the seven-field test

`test_the_allow_list_has_no_bank_salary_or_statutory_field` — and its
`assertEqual(len(JOINER_FIELDS), 7)` — is deleted with the constant, and the browser test's
*"exactly the seven"* assertion goes with it. **What replaces them is seven assertions in the
slice's own test modules. No new CI gate, no new scanner, no new log pipeline** — the four gates
that exist (`check_scope_traps.py`, `check_api_paths.py --max 0`, the `ignore_permissions`
ceiling in `test_portal_security_010`, the demo-password check) already cover the mistakes this
change can make, and a fifth gate nobody reads is worse than four that fail honestly.

| # | Assertion | Why it is the gate |
|---|---|---|
| 1 | The joiner candidate list **is** `MY_PROFILE_WRITE_FIELDS`, by identity | Stops a third list appearing; a third list is how two lists drift apart |
| 2 | Every name in the PRIV-11 deny tuple is refused at the setter — a table test, one row per name | The test output reads as the deny list, so a reviewer can see what is barred |
| 3 | **Each deny name written straight into `DefaultValue`** is absent from `open_invite`'s `fields` and stores nothing through `submit_invite` — **and that now includes statutory names: `pan_number`, plus made-up ones like `aadhaar_no`, `pan_card_number` and `uan`, which must be refused by the pattern on a site with no India regional pack** | **The one that matters.** The only half that survives a future UI — and the statutory half is written against made-up names on purpose, so it is never vacuous (A8) |
| 4 | A rule set pointed at an ordinary field makes that field refused, with no code change | Proves the live `rule_set_fields()` read, not the static tuple |
| 5 | Every candidate field **and every document type a tenant may offer** has a label, a hint and a Hindi entry | Fails the day one is added; otherwise a public page says "pan_number", and a required document nobody can read |
| 6 | For every candidate field, `strip_personal_fields` clears it; and a fully-filled aged row leaves no value after the job | Erasure cannot fall behind the list |
| 7 | The joiner tick **ships empty**, and no statutory document type is ticked by default | The Processor's default is what operates until a Controller changes it |

**Said honestly:** the old test pinned a number. None of these pins a number, because the number
is now HR's. They pin the **shape** — one source, two ticks, a deny rule applied twice, labels,
erasure, and an empty default.

## A8 · What must exist before any of this is observable

Lesson 1, slice 028. Three traps, and the third is the nasty one.

| Control | What a test run shows today | What must exist |
|---|---|---|
| PRIV-10, PRIV-11, PRIV-13 | The joiner tick **ships empty**, so every test passes against a form that asks nothing | A dev tenant with the form **on**, the tick carrying **three** fields, **one statutory document type ticked**, and **invented joiner data only** — a made-up card image, never a real person's |
| PRIV-14's erasure | Only the fields a fixture happens to fill are proved erased | A fixture that fills **every** candidate field **and attaches one file** before ageing the row |
| PRIV-11's statutory refusal | **`pan_number` and the other India fields are custom fields created by `hrms/regional/india/setup.py`** — they exist only on an India-regional tenant (`people_fields.py:77-82` says so). On a site without that pack, a tick naming them does nothing and an assertion about them proves nothing | **Settled by PRIV-11's design, not by a fixture:** the refusal is asserted against **made-up names** (`aadhaar_no`, `pan_card_number`, `uan`) which the pattern must refuse on any site. A test that relies on `pan_number` existing must say so in its own docstring |

**If a test run reports "0 findings" without the first row, it has proved nothing.**

## A9 · Residual risk added by this change

| # | Risk | Severity if it happens | Owner | Accepted on | Label |
|---|---|---|---|---|---|
| R9 | **A bearer link carries the ticked contact fields, the pre-filled name, and any card the joiner uploaded.** Bounded by HR's 7-day expiry, single use, HR-created rows and the form shipping off; **not bounded in contents** — but the contents are now much smaller: no statutory column, no HR-only field | P2 for one joiner, P1 if a statutory **document type** is ticked. No cross-tenant reach | Surbhi | 31 Oct 2026, **reduced the same evening by her three answers** | **Intentional trade-off**, much smaller than the morning's version. **Named trigger:** the day a statutory document type is ticked, build option 2's OTP binding |
| R10 | **No written answer on Aadhaar, and none on retention for identity *documents* from a non-employee.** Both answers to date are oral and relayed | **P1 if a statutory document type is ticked at a real tenant before the written answers** | Surbhi, with counsel | open | **Dangerous debt — escalate now.** ⚠ COMPLIANCE 3 and 4, both re-worded to be about documents. ALV-215 still gates switch-on |
| R11 | **HR Manager can export the submission list from Desk** (`export: 1`, `report: 1` on the doctype) and read the attached files. **Downgraded by the 31 Oct decisions:** the export carries contact details and an emergency contact, **not statutory numbers**, because there are no such columns. The **files** still have to be opened one at a time | P3, down from P2 | Surbhi | 31 Oct 2026 | **Acceptable simplification.** C1 masking would close the rest one day. **Do not claim masking in a questionnaire** |
| R12 | **Nothing records that HR read a submission.** PRIV-5 records document opens; a number typed into a column has no open record | P3 | Surbhi | 31 Oct 2026 | **Temporary debt.** One `source` value on the existing access log closes it; not worth it while the row is erased inside the configured period |
| R13 | **A misused bearer link is undetectable.** The right and the wrong holder look identical to us; only volume shows, in the limiter's refusal line | P2 | Surbhi | 31 Oct 2026 | **Intentional trade-off** at this size. Named because "a customer would tell us" is the detection, which makes detection the gap |
| R14 | **`Web Form Request.key` is stored in clear** and I could not check who may read it | P1 if a role below System Manager can read it **and** a statutory document type is ticked | Surbhi | open until SEC-19 is answered | **Temporary debt.** Removed by one read of one JSON in the running image |

R1 to R8 above stand unchanged. **R4 is superseded in part:** counsel closed ⚠ COMPLIANCE 2 on
29 Oct with a 180-365 range, orally; R10 is its narrower successor for the statutory case.

## A10 · Open questions

**Must know — all four are now answered. Kept with the answers on them, because the reasoning
is what stops them being re-asked.**

| # | Question | **Answer, 31 Oct 2026** | Where it lands |
|---|---|---|---|
| M4 | **May the public joiner form ask for an HR-only field?** (⚠ DECISION 078-G) | **No — excluded.** There is no permission level on a guest page, so SEC-7's intersection does not exist there; this was the one move that defeated a control rather than widening a list | **PRIV-10a is the rule. PRIV-10b deleted.** ⚠ closed |
| M5 | **Does "the whole My Profile field list" mean the candidate list, or whatever HR ticked for employees?** | **Its own tick.** One candidate list, ticked twice. My assumption was right | **SEC-17 as written.** `alvoraa_joiner_fields`, shipping empty. ⚠ closed |
| M6 | **Is Aadhaar offered before counsel answers in writing?** | **Falls away as a field question** — there is no statutory field. It survives as a **document** question | ⚠ COMPLIANCE 4, re-worded: no Aadhaar **document type** ticked until the written answer |
| M7 | **Will anything ever read a statutory number as data?** | **No — a photograph of the card is enough.** So no typed statutory field is offered at all, and the need is met by the document upload that is already built and tested, which HR can mark required | **PRIV-11 now refuses statutory identity number fields.** My own PAN recommendation is superseded; the reasoning is kept in A0 |

**Still open, and not mine to close:** ⚠ COMPLIANCE 3 and ⚠ COMPLIANCE 4 — both now about
**documents** rather than fields, both needing a **written** answer, both blocking the ticking
of a statutory document type at a tenant with real joiners rather than blocking the build. And
**078-SEC-19**, which is a read of one JSON in the running image.

**Should know.** **S5:** should a required **field** block sending while a required **document**
does not, as PRIV-12 assumes? My reading is yes — typing is free, uploading in a queue is not.
**S6:** does HR want a fresh invite after a submitted row, so a disputed answer is not the only
record? Today HR can issue another invite as a new row; nothing to change unless she wants them
linked.

## A11 · Subtract pass — what I removed from this addendum

Read back once, asking only what can be deleted and still meet the requirement.

**Removed:**

- **A new per-field sensitivity classification** (compliance-map A1). The right long-term
  mechanism, and rung 5 with one user. Deleted; the deny tuple and the two ticks do this
  change's job in about thirty lines.
- **A click-through warning dialog** when ticking a statutory document type. Deleted — it trains people
  to click through. The standing amber line that already exists is strictly better and cheaper.
- **An OTP on the link** as a requirement. Deleted to a **named trigger** (R9): build it the day
  a statutory **document type** is ticked. Requiring it now would add an SMS channel we do not
  have, for a payload that is a contact card.
- **078-PRIV-10b**, the HR-only variant. Deleted on her 31 Oct answer, and kept as one line in
  A3 so it is not rebuilt by somebody who assumes it was never considered.
- **A typed statutory field, and everything that would have had to guard it** — a reason-per-field
  notice line for it, the masking argument, and the "PAN is conventional" recommendation.
  Deleted on her M7 answer. **This is the largest subtraction in the slice**, and she made it,
  not me: the need is met by a file the product already handles.
- **A new access record for reading a submission.** Deleted to R12 as named debt.
- **Masking of statutory answers in Desk**, and a reveal-with-reason path. Deleted — compliance
  map C1, a slice of its own. R11 records the gap instead of half-building it.
- **A fifth CI gate** for public-page field lists. Deleted; A7's seven assertions ride in the
  slice's own modules.
- **A requirement that the joiner's answers be stored in one JSON blob** rather than a column per
  field. Attractive — unsearchable, unexportable — but it breaks HR's review screen, Desk's form
  and the field-by-field erasure for a benefit PRIV-14's three narrower clauses already deliver.
- **Two more abuse cases**, about tenant isolation and about the limiter. Deleted: nothing here
  crosses a tenant, and padding would bury A12 and A13, which are the two that matter.
- **A requirement forbidding a statutory field on my own authority.** Deleted in the morning
  pass, because it would have re-litigated her decision. **It is in the document now, as
  PRIV-11's statutory clause, because she decided it in the evening.** Noted rather than
  tidied away: the difference between a control I impose and a control she chooses is the
  whole of why the morning draft left it out.

## A12 · Governance note, and what I could not verify

**I wrote 078-PRIV-9 and I am now writing what replaces it.** Under the rule that the builder
must not approve its own requirements, the two arguments that most need a second reader are
**A2's claim that two separate ticks are materially safer than one**, and **A3's claim that an
HR-only field on a guest path defeats SEC-7 rather than merely widening it.** Both are arguments,
not measurements, and I made them.

**I could not verify:** which roles may read `Web Form Request.key` (Frappe's source is not in
this worktree — 078-SEC-19 makes it a named job); the Aadhaar statutory regime, which applies to
the **card** as much as to the number (not mine, and I will not state it from memory —
⚠ COMPLIANCE 4); the TDS-without-PAN rule cited in A0.3 (a practitioner blog, not a primary
source — **now moot for the build**, since no PAN column is created, and it **must not be quoted
to a customer**); and whether counsel's 180-365 range was given with identity documents in
contemplation (relayed orally, so only Surbhi can say — ⚠ COMPLIANCE 3).

**One thing that was open this afternoon and is now closed:** what **HR-only** means for this
form. It does not matter to the public page any more, because HR-only fields are excluded from
it outright (M4). Whatever the UX designer settles for My Profile, the joiner form is unaffected
— which is a smaller surface for the required-fields work to land on, and a deliberate
consequence of her answer.

**I ran nothing.** Every code claim is *verified in code* at the cited file and line in this
worktree on 31 October 2026, or attributed, or marked.
