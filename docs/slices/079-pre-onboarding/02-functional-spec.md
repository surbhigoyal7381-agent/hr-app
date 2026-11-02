---
slice: 079-pre-onboarding
artifact: 02-functional-spec
author: hrms-business-analyst
date: 2026-11-01
status: draft for Surbhi's ready check. Recommendations only — every ⚠ DECISION is hers. I approve nothing.
user_stories_total: 25 (US-1 to US-25)
acceptance_criteria_total: 118 criteria, ids AC-1 to AC-118, no gaps and no suffixes
inputs:
  - 079/00-decisions.md (Surbhi, 1 Nov 2026 — givens)
  - 079/01b-ux-design.md (prototype v8 per its front matter; v7 is the newest file on disk — see §0.3)
  - 079/01c-security-privacy-requirements.md (8 SEC, 6 PRIV, plus 078's surviving items)
  - 078/02-functional-spec.md (format, and §17's parity table, mirrored here as §16)
  - 078/07-devops-inputs.md §3 (OPS-24 to OPS-46 — there is no 079 DevOps artifact, see §0.3)
  - .claude/context/{no-over-engineering,data-doors,change-process,frappe-conventions,nfr-budget,security-compliance-baseline,compliance-feature-map,definition-of-ready-done,handoff-contract}.md
  - code read in this worktree on 1 Nov 2026, cited file:line throughout. I ran nothing.
decisions_carried:
  - "1 · A restricted website login that opens one page. No Employee record"
  - "2 · HR marks fields and document types required. We impose nothing of our own"
  - "3 · My Profile never refuses a save. The joiner form still refuses an incomplete send"
  - "4 · A joiner may come back until they press Send"
  - "4a · Send ends the form, not the sign-in. The sign-in page may say 'your access has ended'"
  - "5 · One candidate list, two ticks. The joiner's tick ships empty. HR-only fields excluded"
  - "6 · No typed statutory field. 6a · Aadhaar accepted, masked by us, mask or refuse"
  - "7 · Counsel's nine rulings, all binding. Two clocks, not one"
---

# 079 · Pre-onboarding — a joiner with a sign-in, not a link — functional spec

## 0 · The answer first

**The biggest thing in this slice is one `before_request` hook, and it is the only reason
the login is safer than the link it replaces.** Today a signed-in account with **no
`Employee` record** is sent to the staff portal: `auth.home_page_for` falls through to
`_portal_home_for` → `/hrms-employee` (`alvoraa_portal/auth.py:44-49, 410-422`), and
`www/hrms_employee.py:get_context:9-11` refuses **only `Guest`** (**confirmed fact**, read
1 Nov 2026). A joiner account is exactly that user. Without the gate in **US-5**, this
slice is **wider** than the bearer link it replaces, because a link at least reached one
page. Everything else here is ordinary work; that one hook is **P1**.

**Three more things will decide whether this ships honestly.**

| | What it is | Where |
|---|---|---|
| **Two clocks** | A non-joiner's **record** lives 180–365 days; their **identity document** 30–60 days. One setting cannot say both. Counsel's rulings 3 and 4 | US-16, AC-84 to AC-92 |
| **Mask or refuse** | The Aadhaar masking runs before anything is stored, the original never reaches disk, and an unsure result **refuses**. The dangerous failure is not a refusal — it is storing an unmasked card while believing it was masked | US-11, US-12, AC-49 to AC-71 |
| **The version-history leak** | The submission doctype carries `track_changes: 1` (`alvoraa_joiner_submission.json`, confirmed), and `erase()` saves without `ignore_version` (`alvoraa_joiner_submission.py:138-141`). So values we told somebody we had erased are almost certainly still in `tabVersion`. **If that is true, both clocks are decorative** | US-17, AC-93 to AC-99 |

**Nothing is exposed today.** The form ships off at every tenant
(`settings.py:176`, `alvoraa_joiner_form_on = 0`), no joiner has ever submitted anything,
so there are no rows and no residue. These are build defects to close before switch-on,
not incidents.

### 0.1 · What is on which rung of the ladder

| Rung | What sits here |
|---|---|
| **1 · already there** | Frappe's `User`, `Website User`, its login page, lockout and session; `Notification Log`; `Version`; `File`; the existing limiter, settings setter, erase job, invite/export/purge buttons |
| **2 · configuration** | Six new settings keys, one new role, two doctype permission rows removed |
| **3 · customisation** | The one-page gate — a copy of `auth.lock_until_password_chosen`'s shape (`auth.py:296-376`), **failing closed instead of open** |
| **4 · new code** | Rewriting the three joiner endpoints to trust the session; the second retention pass; the Aadhaar masker **and one new native dependency** |
| **5 · a new DocType** | **None. Nothing in this slice needs one.** |
| **6 · a new app** | None |

The masker is the only rung-4-plus item, and it is there because Surbhi chose the only
option that satisfies counsel's ruling 5. **Everything else reuses something that exists.**

### 0.2 · ⚠ Three things that need Surbhi before an engineer starts

| # | What | Why it cannot wait |
|---|---|---|
| **⚠ S1** | **The two-column My Profile changes a page that has already shipped** (078). `01b` §10a says so plainly and says the call is hers | The design draws it; the parity rule says build the drawing. But it is a change to live code from a different slice. **My recommendation: ship it here** — it is two CSS rules and a DOM reorder, the fault it fixes (a 1280 px box for a ten-digit mobile number, measured) is live today, and holding it means two releases of the same page |
| **⚠ S2** | **Does the masker get built at all before counsel answers?** 078 ⚠ COMPLIANCE 4 asks whether an employer may ask for an Aadhaar card **before employment**, and `01c` M5 asks whether the card's **QR code** carries the full number | A "no" to the first makes the slice's largest piece of work worthless. A "yes" to the second means digit-masking alone is cosmetic and the masker needs a second native library. **My recommendation: build US-1 to US-10 and US-13 to US-25 now; hold US-11 and US-12 until both answers are in.** The Aadhaar document type is a tick, so the rest of the slice ships without it |
| **⚠ S3** | **May the sign-in name be the joiner's mobile number?** The design wants it (it is the only identifier a frontline joiner reliably has); `01c` 079-SEC-1 clause 4 wants an **opaque, non-routable** login id | They can both be had — see §2, conflict C4 — but it needs **`System Settings.allow_login_using_mobile_number = 1`, which changes sign-in for every employee at that tenant.** That is a tenant-wide side effect and it is hers to accept. **My recommendation: accept it, with AC-9's duplicate guard** |

### 0.3 · Two inputs I did not have, said plainly

- **There is no `079/01-product-brief.md` and no `079/07-devops-inputs.md`.** This slice is
  the deferred half of 078, so I used 078's brief and its 38 OPS rows, and carried the
  pre-onboarding ones (OPS-24 to OPS-30, OPS-33, OPS-39, OPS-40, OPS-44, OPS-45) into §10.
  **The masker has no DevOps input at all** — a new native dependency, its pin, its memory
  and its timeout are unmeasured and unowned. OPS-M1 in §10 names that gap.
- **`prototype-v8.html` does not exist.** `01b`'s front matter names
  `C:/Surbhi-Git/hrlocal-data/prototypes/078-positions-faces/prototype-v8.html`; the newest
  file in that folder is **`prototype-v7.html`** (11:14, 1 Nov 2026). Every parity claim in
  §16 is read from **v7**, whose screen and state lists I read in full. `01b` §10a and §15
  describe v8's one change — the password card moving into the right column — and I have
  specified that from the words. **[ASSUMPTION]** that v8 is otherwise v7. **Somebody should
  put v8 where the design says it is**, because the parity rule makes the prototype the
  contract and a missing contract cannot be checked.

---

## 1 · Cross-module reach — named before anything is specified

| App or module | What this slice does to it |
|---|---|
| **`alvoraa_portal`** | Almost all of it: `auth.py` (the gate, the landing branch), `joiner_public.py` (rewritten onto the session), `joiner_invite.py` (the account, the credential, the export log), `joiner_housekeeping.py` (the second clock), `www/joiner.py` → `www/joining.py`, `my_profile.py` (the `Needed` marks), `people_settings.py` + `portal.js` (the two new pickers, the two-column layout), the submission doctype (two fields, two permission rows), a new masker module |
| **`hrms`** | `alvoraa_org_structure/settings.py` (six keys, their ranges, their labels) and `people_fields.py` (the joiner tick's allow-list). No HR doctype is touched |
| **`erpnext`** | **Read only, and not even that on the joiner's path.** No `Employee` is created, read or written by anything a joiner can reach (078-SEC-12, carried) |
| **`frappe`** | A `User` row, a `Role`, a session, `Notification Log`, `Version`, `File`, `System Settings.allow_login_using_mobile_number`. No framework file is edited |
| **`alvoraa_goals`, `alvox_compensation`** | Nothing. Named so the next reader does not have to check |
| **HRMS domains** | **Org structure** (the settings card) and **employee records** (My Profile). **Attendance, leaves, payroll, appraisals, goals and learning are untouched** — and that is load-bearing: no `Employee` row means no `Attendance`, which is why decision 1 exists (the back-dated-joining-date trap, already paid for at DTC) |

**Personas.** **Employee** — My Profile only (`Needed` marks, two columns). **HR Manager /
HR User** — invite, read, export, purge; and HR Manager **loses** two doctype rights.
**System Manager** — the settings, and the only unmasked export. **CXO** — nothing on
screen; one sentence on HR's screen answers them: a joiner is not a seat, not headcount,
not on the chart. **New joiner (frontline, phone)** — a new persona with a login and no
employee record, which this product has never had before.

---

## 2 · Where the design and the security requirements disagree — and how I resolved it

`01b` and `01c` were written days apart by different agents. **Six real disagreements.**
I resolved five and send one to Surbhi.

| # | The design says | The security requirements say | Resolution, and why |
|---|---|---|---|
| **C1** | **Send ends the form, not the sign-in.** §5.4, §9 and ⚠ D5 were written the other way, and `01b` built "Send ends it" as decision 4 | **079-SEC-5 row 1: "They press Send → dies immediately"**, and M3's fail-closed default is "the account dies at Send" | **Decision 4a wins — it is dated after both, and it is a given.** Send ends the **form**; the sign-in lives until its expiry date or until HR ends it. 079-SEC-5 keeps its other four endings unchanged. **M3 is closed by 4a, not by me.** US-13, AC-72 to AC-77 |
| **C2** | **The draft moves to the server** — "saved with PP Jewellers", so "nothing was lost" is true across devices and nothing is left on a borrowed phone (§5.2, §14 criterion 6) | **079-PRIV-5: "The draft stays on the device. Do not move the draft to the server"** — a server draft is a half-filled personal record both clocks must learn about | **The design wins, and the cost security named is already paid.** Three reasons. (a) The prototype is the contract and Surbhi approved it. (b) **The row already exists from the moment HR invites** — `invite_joiner` inserts it with the joiner's name (`joiner_invite.py:152-158`), and documents already upload immediately, so the clocks must already cover an unsent row. Adding the typed answers to a row that exists is not a new object. (c) Signing out of a borrowed phone leaving nothing behind is itself a privacy gain, and `localStorage` cannot give it. **What I keep from 079-PRIV-5:** the clocks must cover an unsent row (they do — the 90-day backstop runs from `creation`), and document bytes still never reach `localStorage`. US-7, AC-30 to AC-34 |
| **C3** | **HR-only fields excluded** (⚠ D7), because the field-rights intersection is about what the *employee* may fill | **Excluded**, and §6 rewrites the reason: a joiner holds **no write right on `Employee` at any level**, so no permission mechanism could ever license them to supply one | **Same answer, and I use `01c`'s reason, as it asks.** The old sentence ("there is no permission level on a path opened without a login") is now false and must not be quoted again. Written into AC-105 and into §7's negative cases |
| **C4** | The sign-in name is **the mobile number or email HR already reached them on** (§3 line 3, ⚠ D2) | **079-SEC-1 clause 4: an opaque, non-routable login id**, so Frappe's guest-allowed `reset_password` has no mailbox and no future staff login can collide | **Both, by separating what is typed from what is stored.** `User.name`/`email` is an opaque non-routable address (`joiner-<hash>@joiner.invalid`); `User.mobile_no` holds the number the joiner types; Frappe resolves the typed number through **`allow_login_using_mobile_number`**. So there is no mailbox to mail, no collision with a real email, and the joiner types the thing they are holding. **Cost: that setting is site-wide — ⚠ S3 is Surbhi's.** US-1, US-3, AC-5 to AC-9 |
| **C5** | The masked copy is **shown back to the joiner**, small, in place, on the documents block — "a black bar they can see is a fact" (§5.5) | Nothing about showing it back; 079-SEC-3 allows the joiner no file access, and a private `File` on a row they hold no read on cannot be served to them | **Shown back, from the upload's own reply, and not stored twice.** The upload endpoint already holds the masked bytes in memory, so it returns them as a `data:` URL and the page draws it. **On a later visit the picture is not re-drawn** — the block says "Aadhaar card · kept, numbers covered" in words. A fourth endpoint streaming a private file to a joiner session is the alternative, and it is a new file door for one reassurance. **⚠ Parity difference P5** — small, and hers to overturn |
| **C6** | `01b` ⚠ D1: **no forced password change**, risk accepted and stated | 079-SEC-2: the joiner is **not asked to choose a password** at all, and `lock_until_password_chosen` must not engage | **Agreement, not a conflict** — recorded because the two documents reach it by different routes. AC-10 asserts the second half: the forced-change lock keys on `frappe.db.exists("Employee", {"user_id": user})` (`auth.py:345-347`), so it already excludes a joiner — and a later "fix" to that line would strand one on `/update-password` |

**One more, not a disagreement but worth naming:** `01c` §10 assertion 1 wants the joiner's
candidate list to **be** `MY_PROFILE_WRITE_FIELDS` "by identity", while the submission
doctype's `JOINER_FIELDS` carries a seventh name, `full_name`, which is not on My Profile at
all. Resolution in AC-104: **the tick covers the six; `full_name` is not a ticked field** —
it is HR's own entry at invite, pre-filled, correctable by the joiner, and never required by
a tick. That keeps the identity assertion true for the tick and leaves today's behaviour
alone. **[ASSUMPTION]**, flagged as OQ-3.

---

## 3 · Gap analysis — configure, extend, build new, drop

What Frappe, ERPNext, Frappe HR and our own code already do, read in this worktree today.

| Requirement | What exists today | Verdict | Cost |
|---|---|---|---|
| A login that is not an employee | Frappe's **`Website User`** — refused at `/app` by construction; `usage.py:104-106` counts only enabled **System** Users as seats | **Configure** | S |
| A role that reads nothing | `announcements.make_role` (`announcements.py:565-578`) already makes one with `desk_access = 0`, **and warns** that Frappe creates a role *with* desk access the first time it meets it in a doctype's permission rows | **Configure** (one role, zero permission rows) | S |
| A server-generated one-off credential | `Alvoraa App Invite` (`alvoraa_app_invite.py:1-26`) already does this shape; `frappe.generate_hash` | **Extend** | S |
| Expiry of the credential | `alvoraa_joiner_link_days` (7, `settings.py:150`) and the daily `expire_the_dead_links` (`joiner_housekeeping.py:181-209`) | **Configure** — reuse both | S |
| Lockout after wrong passwords | Frappe `System Settings.allow_consecutive_login_attempts` / `allow_login_after_fail`. **Values unread — ⚠ D4b** | **Configure** | S |
| Login by mobile number | `System Settings.allow_login_using_mobile_number` **[UNVERIFIED — engineer to confirm the field name and that it matches `User.mobile_no`]** | **Configure**, with a side effect — ⚠ S3 | S |
| **One page and nothing else** | **Nothing.** `Role.home_page` decides a landing, not a boundary. The nearest shape is `auth.lock_until_password_chosen` (`auth.py:296-376`): a path allow-list, a `cmd` allow-list honoured **only on `"/"`**, cheap checks first, the database last | **Extend** — copy that shape, **fail closed** | **M** |
| The landing | `home_page_for` is already the one rule three doors share (`auth.py:14-54`) | **Extend** — one branch | S |
| A joiner's endpoints without a token | `joiner_public.py`'s three endpoints, whose own docstring says *"there is no submission argument anywhere in this module"* (`:103-108`) | **Extend** — swap the token for `frappe.session.user`, keep that property literally true | **M** |
| Rate limits per joiner | `field_app_limits._limited(..., "user")` — already used at `joiner_invite.py:139` | **Configure** — re-key | S |
| HR invites, cancels, exports, purges | All four built (`joiner_invite.py`), Desk buttons built (`alvoraa_joiner_submission.js`) | **Extend** — the reply changes, the export logs, `purge_submission` gains its first test | S |
| HR cannot invite before the employer's values are set | `require_form_on()` exists; the page refuses to render with no contact (`joiner_public.py:180-199`). **But `alvoraa_hr_contact_phone` / `_email` are in no `DEFAULTS`, no `LABELS` and no setter — only tests write them** (confirmed: they appear nowhere else in the code) | **Configure** + **Extend** — add both to the settings screen, and make the invite refuse | S |
| The employer's own notice words | 078-PRIV-8's shape is built and proved: notice before the first question, the tenant's numbers, its own contact | **Configure** — one text key, shipped empty, and the page refuses without it | S |
| Required field marks | **Nothing.** `JOINER_FIELDS` is a closed tuple and 078's AC-110c says *"no field name appears in any required list in our code"* | **Build new** (small): two tick keys read by two screens | **M** |
| Required document types | `ticked_types()` reads one list; nothing marks one required | **Build new** (small): one tick key | S |
| My Profile never refusing a save | **Already true.** `save_my_profile` refuses only an off-list field name (`my_profile.py:123-131`) and has no required concept | **Already there** — the work is the marks, not the rule | S |
| Two columns on My Profile | `.pf-card` exists (`panels.css:1045`); the design's two rules are `grid` + `auto-fit` + `minmax`, no media query | **Configure** (CSS) + a DOM reorder | S |
| The second retention clock | One pass per rule in `joiner_housekeeping.py`; `erase()` deletes files **and** fields together | **Build new** (small): one key, one pass that deletes **only** `File` rows | **M** |
| Erasure reaching `tabVersion` and the `User` row | `erase()` reaches fields and files only | **Extend** | **M** |
| Aadhaar masking | **Nothing anywhere masks an image.** Pillow is already a dependency (`employee_photo._reencode:141-158`); OCR is not | **Build new** — rung 4, **plus a new system package** | **L** |
| An affected-record query for a wrong masking rule | Nothing | **Build new** (tiny): one function, one field | S |
| Export logging | `export_submission` already logs one line (`joiner_invite.py:268-272`) | **Extend** — add the masked/unmasked flag; **remove** HR Manager's `export` and `report` rows | S |
| Hindi for the new strings | `drT()` everywhere; **Hindi absent** for the joiner page (ALV-267) | **Extend** | **M** |
| **Drop · an unmasked bytes-included export** | 079-SEC-6 clause 3 offers it, System Manager only, and says *"build it only if HR genuinely needs to hand a candidate their own documents back"* | **Drop.** Counsel's ruling 8 is met without it: HR sends the files from the row, which is a read, not an export. **A permission surface for a case nobody has reported.** AC-83 asserts it does not exist | — |
| **Drop · a record that HR read a submission** | 079-SEC-6 §12 explicitly does not require it; `Alvoraa Photo Access Log` could carry it | **Drop**, stays named debt (R-6). No ruling asks for it, and the document clock is 30 days | — |
| **Drop · an SMS or email channel for the credential** | Email is the only channel the product has | **Drop** — M2's answer: HR hands it over by whatever means they already use, and the endpoint returns it once. **No mail path is built** | — |
| **Drop · a consent tick on the notice** | — | **Drop** (`01b` §5.4). We are the Processor; a tick implies a choice the joiner does not have | — |

---

## 4 · Process flow — the real sequence, unhappy paths included

### 4.1 HR invites somebody

1. HR opens **Alvoraa Joiner Submission → new**, types the person's name and their mobile
   number or email, and saves.
2. HR presses **Make the sign-in**.
   - *Switched off at this tenant* → refused, naming the setting (built: `require_form_on`).
   - *The employer's three values are not set* (record clock, document clock, HR contact) →
     refused, **listing which of the three is missing**, with a link to the settings screen.
   - *That number or email already belongs to any `User`* → refused, asking for the other
     one. **This is the ALV-242 lesson: one credential per person, never a batch.**
3. The server makes a `Website User` with one role, no permission rows, an opaque login id
   and a random credential; links it to the row; returns **the six-line message once**.
4. HR copies the message and sends it, or prints the slip. **The password is never shown
   again and is stored nowhere readable.**

### 4.2 The joiner gets in

5. They open `/joining`. **No session** → our own sign-in page in its joiner state.
6. They type the number and the password.
   - *Wrong password* → "That did not work", with the tries left counted out loud. It never
     says which of the two was wrong.
   - *Too many tries* → "Locked for 30 minutes", naming the time, no action button.
   - *The access has ended* (sent, cancelled, expired, hired, turned down) → **"This sign-in
     has finished its job"** — never "Invalid credentials". Decision 4a allows this.
   - *They cannot sign in at all* → an in-page block that ends at the employer's own phone
     number. **Not `Forgot password?`, which mails a link to a mailbox that does not exist,
     and not `mailto:`.**
7. Signed in, they land on `/joining` — **and nothing else answers them.** Any other address
   or API call gets the one refusal screen, or a `PermissionError` for an `/api/` call.

### 4.3 They fill it in

8. The notice first: the employer's own words, both retention numbers, the employer's
   contact, and three sentences we write (this login opens one page; what you send is sent;
   afterwards, ask the employer). **The page refuses to render if the employer's words are
   not set.**
9. One screen per group of questions, 8 to a page. Anything HR marked required carries a
   `Needed` chip.
10. Documents: one block per ticked type. A required type has **two** answers, both of which
    send the form — a photograph now, or **"I will bring it on my first day"**.
11. **Aadhaar** (if the tenant ticked it): the alternatives first, then the promise that we
    cover the first 8 digits before keeping it.
    - *Masked* → the covered copy is shown back once, and only the covered copy is stored.
    - *Not sure* → **refused. Nothing is stored, the session is untouched**, and three ways
      on: another photograph, another document type, or bring it on day one.
12. They can stop. Everything typed is on the employer's record; they sign in again — on any
    phone — and land on the step they left, with the counts ("4 of 7 answers, 2 of 4
    documents").

### 4.4 Send, and after

13. **Send.** Refused if anything marked required is empty or unanswered, listing each
    missing item as a tap. **A refusal costs them nothing** — nothing is sent, nothing is
    burned, they stay signed in.
14. Accepted → the Sent screen. The typed answers become read-only to them.
15. **The sign-in still works** (decision 4a). Until the expiry date, or until HR ends it,
    they can come back and add a document they promised. They cannot change what they sent.
16. HR reads the row, makes the `Employee` **by hand** and sets the joining date themselves
    — never from the form (the absence-backfill trap). Linking the Employee moves the status
    to *Made an employee* (built: `_follow_the_employee`).
17. **On that day the joiner account is closed, not promoted.** Their staff login is a
    separate account on their real address. Promoting the joiner account would leave the new
    employee locked out by the very gate in US-5.
18. The clocks run daily: the **documents** go at the document clock, the **record** at the
    record clock, legal hold wins over both — except HR's Purge, which is the person's own
    request.

---

## 5 · Data model — every field, and why an existing one cannot carry it

**No new DocType.** One new role, two new fields, six new settings keys.

### 5.1 `Alvoraa Joiner Submission` — two new fields

| Fieldname | Label | Type | Mandatory | Default | Why an existing field cannot carry it |
|---|---|---|---|---|---|
| `user` | Sign-in | `Link` → `User`, read-only, **unique** | no | — | **This is the whole of 079-SEC-4.** The endpoints resolve the row from `frappe.session.user`, so the mapping has to live on the row and never be passed in. `invited_by` is HR; `personal_email` is the joiner's own mailbox and must never be a credential |
| `masked_with` | Masked by | `Small Text`, read-only | no | — | 079-PRIV-6 clause 1. Holds the masker version and engine version used on this row's images, appended once per distinct version. It is what makes the affected-record query possible when a masking rule is later found wrong — and the original is gone, so there is no re-run |

**`web_form_request` is dropped**, with the `Web Form` anchor record and
`joiner_invite._web_form()`. There is no token, so 078-SEC-19 and its recorded deviation
(Frappe storing `Web Form Request.key` in clear) **cease to exist** rather than being
accepted again. This is the slice's largest subtraction.

**`track_changes` stays `1`** — but both personal-data saves pass `ignore_version`, and
erasure sweeps `tabVersion`. See US-19. *(Turning tracking off instead loses HR's own edit
history on the row, which §14 promises. Keeping the flag and opting two saves out is the
smaller change.)*

**No field is added for the draft.** A draft is the row with `status = "Invited"` and
`submitted_at` empty. The counts on the "coming back" screen are computed, not stored.

### 5.2 The joiner's fields are the employee's six, under the submission's own column names

**Confirmed fact:** the candidate list is `people_fields.MY_PROFILE_WRITE_FIELDS` (six
names, `people_fields.py:65-72`) and the submission's columns are named differently. The
map is fixed, in code, and tested:

| `Employee` field (the tick's name) | Submission column | On the joiner form |
|---|---|---|
| `cell_number` | `mobile` | yes, if ticked |
| `personal_email` | `personal_email` | yes, if ticked |
| `current_address` | `current_address` | yes, if ticked |
| `person_to_be_contacted` | `emergency_contact_name` | yes, if ticked |
| `relation` | `emergency_relation` | yes, if ticked |
| `emergency_phone_number` | `emergency_phone` | yes, if ticked |
| — | `full_name` | **always**, pre-filled from HR's entry, never required by a tick (AC-104) |

### 5.3 Six new settings keys, in `hrms/alvoraa_org_structure/settings.py`

| Key | Ships as | Range or rule | In `ACCESS_GRANTING`? | Rule id |
|---|---|---|---|---|
| `alvoraa_joiner_fields` | **empty** | names from `MY_PROFILE_WRITE_FIELDS` only, refused at the setter and intersected again at the reader | **yes** | 079-SEC-1 |
| `alvoraa_joiner_required_fields` | **empty** | a subset of `alvoraa_joiner_fields`, intersected at both ends | **yes** | 079-SEC-1 |
| `alvoraa_my_profile_required_fields` | **empty** | a subset of `alvoraa_my_profile_fields` | **yes** | 079-SEC-1 |
| `alvoraa_joiner_required_documents` | **empty** | a subset of the ticked `Employee Document Type` list | **yes** | 079-SEC-1 |
| `alvoraa_joiner_document_days` | **30** | **30–60** (counsel 4). No blank, no 0, no "for ever" | **yes** | 079-PRIV-1 |
| `alvoraa_joiner_notice_text` | **empty** | free text, the employer's own words. **The page refuses to render without it** | **yes** | 079-PRIV-3 |

And two keys that **exist in code but have no settings screen** — confirmed, they are
written only by tests: `alvoraa_hr_contact_phone`, `alvoraa_hr_contact_email`. Both join
`DEFAULTS` and `LABELS` so HR can actually set them. **Not** `ACCESS_GRANTING`: a phone
number is HR's own detail, not a decision about who sees whom.

**Why four tick keys and not one.** The prototype draws a separate "Must fill in" tick
inside each picker (`tickRow(..., req, ...)`, v7), and the two surfaces mean different
things: on the joiner form required **blocks the send**; on My Profile it only **asks
again**. One shared key would make a field required on a screen HR never meant.

### 5.4 One new role

**`Alvoraa Joiner`** — `desk_access = 0`, **and it appears in no doctype's permission rows
anywhere in either app.** `announcements.py:565-578` carries the warning this obeys: Frappe
creates a role *with* desk access the first time it meets it in a permission JSON. The
joiner's own row is reached by server code bound to their session, never by their own
permissions.

### 5.5 Two permission rows removed

`Alvoraa Joiner Submission` grants, today (confirmed in the JSON): System Manager
`read/write/create/delete/report/export`; **HR Manager `read/write/create/report/export`**;
HR User `read/report`. After this slice: **HR Manager loses `report` and `export`; HR User
loses `report`.** Counsel's ruling 9, and 078 finding F3 converted from "accept in writing"
to a requirement.

---

## 6 · States and transitions

### 6.1 The submission — one row, five states, and what Send no longer does

| State | Who can move it | Next | What becomes read-only | Notified |
|---|---|---|---|---|
| **Invited** | the joiner (Send), HR (Cancel), the daily job (Expire), HR (link an Employee) | Submitted · Cancelled · Expired · Made an employee | nothing | — |
| **Submitted** | HR (Cancel), HR (link an Employee) | Cancelled · Made an employee | **the typed answers, to the joiner.** Documents stay open to them until their access ends | HR, by the row in their list |
| **Made an employee** | — **terminal** | — | everything | the daily job erases the whole row on its next run (built) |
| **Cancelled** | — **terminal** | — | everything | `closed_on` stamped |
| **Expired** | — **terminal** | — | everything | `closed_on` stamped |

`_refuse_a_revival` already makes every move out of a terminal state impossible
(`alvoraa_joiner_submission.py:60-70`). **Nothing reverses.**

### 6.2 The account — five endings, one answer

| The day | The account |
|---|---|
| They press **Send** | **unchanged. This is decision 4a.** The form closes; the sign-in does not |
| The **expiry date** passes | ends — the daily job disables it at the same moment it marks the row Expired |
| HR **cancels** | ends |
| They are **hired** | ends. **Closed, never promoted** |
| They are **turned down** (HR cancels with that reason) | ends at that moment, not at the next job run |

"Ends" means four things in one transaction: `enabled = 0`, the role removed, **every
session cleared explicitly**, and the credential invalidated. Sessions are cleared by hand
because whether Frappe kills a live session when `enabled` goes to 0 is **Unknown**
(`01c` §16). `System Settings.session_expiry` is **not** touched — it is site-wide and would
change every member of staff's day.

**One answer out, for all five.** A session that somehow survives reaches the same dead-page
wording `_gone()` already carries (`joiner_public.py:112-118`) — byte for byte, whichever
ending it was. A different answer for "turned down" would tell a candidate the outcome
through a web page instead of from their employer.

### 6.3 The screens, and where each is drawn

| Screen / state | Where | Prototype (v7) |
|---|---|---|
| The six-line message, two shapes | HR's reply to **Make the sign-in**, Desk | `0 · Getting in` → *What HR sends* ×2 |
| HR's "she can now sign in" block | Desk `msgprint` | `0` → *HR's side — what HR sees once* |
| HR's "you cannot invite anybody yet" | Desk refusal | `0` → *HR's side — not ready to invite anybody* |
| Sign-in, joiner state + four failures | `www/alvoraa-login`, `?for=joining` | `0` → *Sign in* ×6 |
| Welcome, notice, questions, documents, photo, check, sent, refusals | `www/joining.html` | `7 · The joiner's form`, 17 states |
| Aadhaar, three states | inside the documents block | `7` → *Aadhaar* ×4 |
| "This sign-in only opens your joining form" | the gate's redirect target | `8 · What this sign-in opens` ×3 |
| My Profile, two columns, `Needed` chips | `#panel-my-profile` | `1 · My profile`, 6 states |
| The two new pickers | the Organisation Settings card | `6 · Organisation settings` |

---

## 7 · Permission and visibility matrix

### 7.1 Role × object × operation, and **which Frappe door enforces it**

`data-doors.md`: a rule that lives only in our portal code is not a rule.

| Object | Alvoraa Joiner | Employee | HR User | HR Manager | System Manager | The door that enforces it |
|---|---|---|---|---|---|---|
| `Alvoraa Joiner Submission` — **their own row** | **no permission at all**; reached only by server code bound to their session | — | r | r w c | r w c d | **doctype permission rows** (the role appears in none) + the gate |
| `Alvoraa Joiner Submission` — report / export | — | — | **none** (loses `report`) | **none** (loses `report`, `export`) | r + export | **doctype permission rows** — a row, not a rule in code |
| `File` on the submission | **none.** The masked copy comes back in the upload's own reply, never fetched | — | r | r | r | Frappe's private-file gate, which falls back to the parent's read permission |
| `Employee` | **none at any level** | own record, the six ticked fields, through `my_profile` | existing scope | existing scope | all | `employee_field_rights` permlevels + `own_record_permission` + our endpoint |
| `User` | **own row only**, by Frappe's own rule | — | — | — | all | Frappe's `User` permissions |
| The six new settings keys | — | — | **no** | **no** | **yes, only** | `_set_access_setting` — refuses and logs anybody else |
| `alvoraa_hr_contact_*` | — | — | yes | yes | yes | `set_cover_setting` (`frappe.only_for`) |
| `/joining` and its three endpoints | **yes, their own row only** | **no** | no | no | no | the gate + resolution from `frappe.session.user` |
| Every other page, `/app`, `/api/method/*`, `"/"` with a `cmd` | **refused** | as today | as today | as today | as today | **the gate, failing closed** + `Website User` + a role with no rows |

### 7.2 The negative cases — who must **not** see what

| # | Who | Must not | Proved by |
|---|---|---|---|
| N1 | A joiner | **Any other submission, any employee, any count, any list, any report, any file that is not their own** | AC-20 to AC-27; the role holds read on nothing, so there is nothing to scope |
| N2 | A joiner | `/hrms-employee`, `/goals-portal`, `/vendor-portal`, `/driver-portal`, `/checkin`, `/alvoraa-admin`, `/app`, `/api/resource/*`, `frappe.client.*`, `reportview.get`, link search, share/assign/comment | AC-20 to AC-26 — a table test, one row per door |
| N3 | A joiner | **`"/"` carrying any `cmd` that is not one of theirs.** This product has paid for this twice (`auth.py:208-220, 236-262`) | AC-24 |
| N4 | A joiner whose access has ended | **The form, their own answers, and the fact that anything changed.** No "you were turned down" through a different page | AC-76, AC-77 |
| N5 | A stranger holding a phone number | **Whether that number belongs to a joiner here.** The sign-in never says which of the two was wrong | AC-13 |
| N6 | HR Manager, HR User | **A spreadsheet of every joiner's name, mobile, personal email, home address and emergency contact.** Verified: the doctype grants them `report`/`export` today | AC-80, AC-81 |
| N7 | HR, and us | **An unmasked Aadhaar.** It never reaches disk, a temporary file, a log or an error row. There is no unmasked copy at any permission level | AC-55 to AC-60 |
| N8 | Anybody reading the database after an erasure — a support engineer, a backup, a Desk timeline | **The mobile number, personal email, home address or emergency contact we said we had deleted** | AC-93 to AC-99 |
| N9 | The hired person's own staff login | **The joiner role.** Carrying it would lock them out of their own record through the gate | AC-78, AC-79 |
| N10 | An employee on My Profile | **Any field not on the six**, and any field on somebody else's record. A required mark must not widen what may be written | AC-100, AC-105 |
| N11 | Guest | Everything. `/joining` as Guest gives the sign-in page, not the form | AC-28 |

### 7.3 The visibility delta, stated plainly

**Nobody gains sight of anybody else.** Four things change and three of them narrow:

1. **A joiner can see their own answers** — new, and it is their own data.
2. **HR Manager and HR User lose** the Desk report view and the export on the doctype.
3. **The public surface goes from one page and three guest endpoints to zero of each.**
4. **New: one `User` row per invited joiner**, holding their name and their number, visible
   to System Manager in a user list. Erasure must now delete it (AC-97).

---

## 8 · The epic and its user stories

### 8.1 The epic

> **As a new joiner at a small Indian employer, I want to give my details and my documents
> on my own phone before my first day, through a sign-in that opens one page and nothing
> else — so that my first day is about the job, and so that nothing I hand over goes
> anywhere I was not told about.**

And its other half: **as the employer, I want to ask only what I have chosen to ask, mark
what I must have, see what came back, hand it back or delete it on request, and have both
of counsel's clocks run by themselves.**

### 8.2 Stories

Every story is checked against INVEST. **One story is an 8** — US-12 — and §8.3 says why it
is not split.

#### Getting a joiner in

- **US-1** · *As an **HR Manager**, I want to make one sign-in for one person I have invited
  and get the message to send them, so that they can fill the form in and nobody else can.*
  **5** · AC-1 to AC-10 · 079-SEC-1, 079-SEC-2
- **US-2** · *As an **HR Manager**, I must not be able to invite anybody before my own
  organisation has set how long it keeps things and who a joiner can ring, so that nobody is
  ever asked for their details under a notice we invented.* **2** · AC-11, AC-12 · 079-PRIV-3
- **US-3** · *As a **new joiner holding a text message**, I want the sign-in page to speak to
  somebody who has never been here, so that I get through on the first try.* **3** · AC-13
  to AC-17 · `01b` §4
- **US-4** · *(must not)* *As a **stranger who has got hold of somebody's phone number**, I
  must not be able to learn from the sign-in page that the number belongs to a joiner at
  this employer.* **2** · AC-18, AC-19 · 079-SEC-1 clause 4

#### The one page — the load-bearing control

- **US-5** · *As a **new joiner**, I want my sign-in to open my joining form, so that I am
  not dropped into an employee portal I have no business in.* **5** · AC-20 to AC-24 ·
  **079-SEC-3. P1.**
- **US-6** · *(must not)* *As a **new joiner, or anybody holding their credential**, I must
  not be able to reach any other page, any API method, or `"/"` with a `cmd` — and the gate
  must refuse when it breaks.* **3** · AC-25 to AC-29 · **079-SEC-3's fail-closed clause**

#### Filling it in

- **US-7** · *As a **new joiner on a borrowed phone**, I want to stop and come back — on any
  phone — and be told what was kept, so that I do not have to start again.* **5** · AC-30 to
  AC-36 · decision 4, `01b` §5.2, §5.3
- **US-8** · *As a **new joiner**, I want to be told plainly what I must fill in before I can
  send, so that a refusal is never a surprise.* **3** · AC-37 to AC-41 · decision 2, 078-SEC-18
- **US-9** · *As a **new joiner who has not got the document with me**, I want "I will bring
  it on my first day" to be a real answer, so that a required document is never a wall.*
  **2** · AC-42 to AC-44 · 078-PRIV-12
- **US-10** · *As a **new joiner**, I want to send a photograph of a document from my camera,
  so that I do not need a scanner.* **3** · AC-45 to AC-48 · 079-SEC-4, 078-SEC-11

#### Aadhaar — gated on ⚠ S2

- **US-11** · *As a **new joiner who only has an Aadhaar card**, I want the first 8 digits
  covered before anything is kept, and I want to see the covered copy, so that I can check
  the promise myself.* **5** · AC-49 to AC-54 · 079-PRIV-4, counsel 5
- **US-12** · *(must not)* *As a **new joiner**, my unmasked Aadhaar must never be stored, and
  an unsure result must refuse without costing me my access.* **8** · AC-55 to AC-71 ·
  079-PRIV-4, 079-SEC-8, 079-PRIV-6

#### Sending, and ending

- **US-13** · *As a **new joiner who finds my PAN card the next evening**, I want my sign-in
  to still work after I have sent the form, so that I do not have to ring HR.* **3** · AC-72
  to AC-77 · **decision 4a**
- **US-14** · *As the **employer**, I want a joiner's sign-in to end every way it can end, and
  never to become their staff login, so that nobody keeps a way in that nobody meant.* **3** ·
  AC-78, AC-79 · 079-SEC-5

#### HR's side, and the clocks

- **US-15** · *As a **System Manager**, I want every export of a joiner's data logged and
  masked by default, and I do not want HR able to take a spreadsheet of everybody.* **3** ·
  AC-80 to AC-83 · 079-SEC-6, counsel 9
- **US-16** · *As the **employer**, I want a non-joiner's identity documents deleted much
  sooner than their record, because counsel set two different periods.* **5** · AC-84 to
  AC-92 · 079-PRIV-1, counsel 3 and 4
- **US-17** · *(must not)* *As a **person who never joined**, nothing of mine may survive an
  erasure — not in the row, not in a file, not in version history, and not as a user
  account.* **5** · AC-93 to AC-99 · 079-PRIV-2
- **US-22** · *As an **HR Manager**, I want to see what came back, hand a person everything we
  hold, and delete it when they ask.* **2** · AC-114, AC-115 · counsel 8
- **US-25** · *As an **HR Manager**, I want the one number that would tell me a credential was
  shared.* **1** · AC-118 · OPS-28

#### My Profile, and the settings

- **US-18** · *As an **employee**, I want to save my own record even when something HR wants
  is still missing, and be reminded what is missing, so that I am never locked out of
  correcting my own phone number.* **3** · AC-100 to AC-103 · decision 3
- **US-19** · *As a **System Manager**, I want to choose what a joiner is asked and what is
  compulsory, on the screen I already use, so that nothing is asked that I did not choose.*
  **3** · AC-104 to AC-107 · decision 2, decision 5, 078-SEC-17
- **US-20** · *As an **employee on a laptop**, I want My Profile not to stretch a ten-digit
  box across the screen, and I want the cards to drop into one column when I zoom in.* **2** ·
  AC-108 to AC-110 · `01b` §10a · **⚠ S1: this changes 078's shipped page**
- **US-21** · *As a **new joiner**, I want to be told in my employer's own words why they want
  this and how long they keep it, before the first question.* **3** · AC-111 to AC-113 ·
  079-PRIV-3, counsel 6

#### Proving it

- **US-23** · *As a **frontline joiner who reads Hindi**, I want every word on the sign-in and
  the form in Hindi, because a person who cannot read the door never reaches the form.* **3** ·
  AC-116 · 078-PRIV-13, ALV-267
- **US-24** · *As the **test engineer**, I want a dev tenant and a fixture set that make these
  controls observable, because the form ships off and an empty run proves nothing.* **3** ·
  AC-117 · `01c` §11

### 8.3 INVEST notes, and the one 8

- **US-12 is an 8 and is deliberately not split.** "Mask or refuse" is one rule with one
  answer; splitting it into "mask" and "refuse" would let a build land the half that stores
  things. The ladder's honest reading is that it is the most expensive thing in the slice.
- **US-5 and US-6 are split on purpose** — the gate and the proof that it is closed. The gate
  can be built and reviewed before the door table exists; the door table is what stops it
  being quietly reversed later.
- **US-10 is mostly already built** (`upload_invite_file`); its 3 points are the session
  re-key and the limiter.
- **US-18's rule is already true in code.** Its points are the marks and the amber block.
- Nothing here depends on US-11/US-12 landing, which is what makes ⚠ S2 payable.

### 8.4 YouTrack-ready table — **do not create these issues; that is Surbhi's call**

| Summary | Persona | Points | ACs | Requirements |
|---|---|---|---|---|
| 079 US-1 · One sign-in per invited joiner, the message shown once | HR Manager | 5 | AC-1–AC-10 | 079-SEC-1, 079-SEC-2 |
| 079 US-2 · No invite until the employer's three values are set | HR Manager | 2 | AC-11, AC-12 | 079-PRIV-3 |
| 079 US-3 · The sign-in page in its joiner state, and its four failures | New joiner | 3 | AC-13–AC-17 | `01b` §4, D4 |
| 079 US-4 · (must not) The sign-in reveals nothing about a number | Stranger | 2 | AC-18, AC-19 | 079-SEC-1 |
| 079 US-5 · **P1** One page and nothing else — the fail-closed gate | New joiner | 5 | AC-20–AC-24 | 079-SEC-3 |
| 079 US-6 · (must not) Every other door refused, Guest gets the sign-in | New joiner | 3 | AC-25–AC-29 | 079-SEC-3 |
| 079 US-7 · Stop and come back, on any phone | New joiner | 5 | AC-30–AC-36 | decision 4 |
| 079 US-8 · Required means required on the joiner form | New joiner | 3 | AC-37–AC-41 | decision 2, 078-SEC-18 |
| 079 US-9 · A required document is answered, never had | New joiner | 2 | AC-42–AC-44 | 078-PRIV-12 |
| 079 US-10 · Documents upload against the session | New joiner | 3 | AC-45–AC-48 | 079-SEC-4, 078-SEC-11 |
| 079 US-11 · Aadhaar: the covered copy is what is kept (**gated ⚠ S2**) | New joiner | 5 | AC-49–AC-54 | 079-PRIV-4 |
| 079 US-12 · (must not) No unmasked Aadhaar, ever (**gated ⚠ S2**) | New joiner | 8 | AC-55–AC-71 | 079-PRIV-4, 079-SEC-8, 079-PRIV-6 |
| 079 US-13 · Send ends the form, not the sign-in | New joiner | 3 | AC-72–AC-77 | decision 4a |
| 079 US-14 · The account's five endings; never promoted | HR Manager | 3 | AC-78, AC-79 | 079-SEC-5 |
| 079 US-15 · Exports masked and logged; HR Manager loses bulk export | System Manager | 3 | AC-80–AC-83 | 079-SEC-6 |
| 079 US-16 · Two retention clocks | Employer | 5 | AC-84–AC-92 | 079-PRIV-1 |
| 079 US-17 · (must not) Erased means erased, including `tabVersion` | Non-joiner | 5 | AC-93–AC-99 | 079-PRIV-2 |
| 079 US-18 · My Profile marks what is Needed and still saves | Employee | 3 | AC-100–AC-103 | decision 3 |
| 079 US-19 · HR chooses what a joiner is asked and what is required | System Manager | 3 | AC-104–AC-107 | decision 2, 078-SEC-17 |
| 079 US-20 · My Profile in two columns (**⚠ S1 — changes 078's page**) | Employee | 2 | AC-108–AC-110 | `01b` §10a |
| 079 US-21 · The employer's own notice, shipped empty | New joiner | 3 | AC-111–AC-113 | 079-PRIV-3 |
| 079 US-22 · HR sees what came back, exports and purges | HR Manager | 2 | AC-114, AC-115 | counsel 8 |
| 079 US-23 · Hindi at parity for every new string | New joiner | 3 | AC-116 | 078-PRIV-13 |
| 079 US-24 · The fixture set that makes the controls observable | Test engineer | 3 | AC-117 | `01c` §11 |
| 079 US-25 · The one invariant HR glances at | HR Manager | 1 | AC-118 | OPS-28 |

**Total 83 points.** US-11 and US-12 are 13 of them, and both are gated on ⚠ S2.

---

## 9 · Acceptance criteria

Given / When / Then. Every one has an observable oracle — a field value, a document state, a
database row, an HTTP status, a log line, or a string on a screen the prototype draws.

### US-1 · One sign-in per invited joiner

| ID | Given | When | Then |
|---|---|---|---|
| **AC-1** | The form on, the employer's three values set, a row with a name and a number | HR presses **Make the sign-in** | A `User` is created with **`user_type = "Website User"`**, `enabled = 1`, **exactly one role** (`Alvoraa Joiner`), `send_welcome_email = 0`, and no other role. The submission's `user` field holds it. `status` stays `Invited`, `expires_on` is creation + `alvoraa_joiner_link_days` and is **not** changed again |
| **AC-2** | The new role | A test reads it | `desk_access = 0`, and a **static test asserts the role name `Alvoraa Joiner` appears in no doctype's permission rows in `alvoraa_portal`, `hrms` or `alvoraa_goals`** — the `announcements.py:565-578` trap, where Frappe creates a role *with* desk access the first time it meets it in a permission JSON |
| **AC-3** | A joiner account exists | The seat count is read | **`usage.py`'s enabled-System-User count has not moved.** A joiner is not a billable seat, is not in headcount, is not on the organisation chart, and has **no `Employee` row and no `Attendance` row** |
| **AC-4** | Two invites | Both are made | **Two different credentials**, each from `frappe.generate_hash` or `secrets` on the server. **HR never types one, never chooses one, and no two accounts share one** — this is ALV-242, which is live in this product today |
| **AC-5** | The call that makes the sign-in | It returns | The reply carries the **username and the password exactly once**, plus the six-line message of `01b` §3 ready to copy. A second call to read it back **does not exist**. The credential is in **no** log line, **no** `Version` row and **no** field on either row — a test greps the row's `as_dict()` and the `alvoraa` logger output |
| **AC-6** | The created `User` | A test reads `name` and `email` | Both are an **opaque non-routable address** (`joiner-<hash>@joiner.invalid`), matching a pattern, and **equal to nothing HR typed**. `mobile_no` holds the number HR typed. **No personal email, no photograph and no address is on the `User`** — the joiner's own email stays a field on the submission, where erasure reaches it |
| **AC-7** | `System Settings` | The feature is used | **`allow_login_using_mobile_number` is on**, and the release note says plainly that this also lets every employee sign in with their mobile number. **[UNVERIFIED — engineer to confirm the field name]** |
| **AC-8** | A joiner signs in | A test reads the login history | **A log row attributable to that account exists**, with a time. If Frappe writes none, **this criterion fails and §14's detection claim is struck from this spec** rather than left as a hope |
| **AC-9** | A row whose number or email already belongs to **any** `User` — a staff login or another joiner | HR presses **Make the sign-in** | **Refused**, in plain words, asking for the other identifier. Two joiners can never share a credential or resolve to the same account (J4) |
| **AC-10** | A joiner account | It signs in | **`lock_until_password_chosen` does not engage** and the joiner is never sent to `/update-password`. A test asserts it, because that function keys on `frappe.db.exists("Employee", {"user_id": user})` (`auth.py:345-347`) and a later change to that line would strand a joiner on a page they cannot use |

### US-2 · No invite until the employer's own values are set

| ID | Given | When | Then |
|---|---|---|---|
| **AC-11** | A fresh site: `alvoraa_joiner_document_days` unset, `alvoraa_joiner_notice_text` empty, no HR contact | HR presses **Make the sign-in** | **Refused**, listing **which** of the three is missing in the shape `01b` §6.3 draws, with a link to the settings screen. **No `User` is created and no credential is generated.** A joiner-facing "we do not know how long they keep this" screen **does not exist** — the block lands on the person who can fix it |
| **AC-12** | All three set | The same press | It succeeds. A test sets them one at a time and asserts the refusal names exactly the ones still missing |

### US-3 · The sign-in page, in its joiner state

| ID | Given | When | Then |
|---|---|---|---|
| **AC-13** | The joiner state, a wrong password | Sign in is pressed | **"That did not work"** with the code `JOIN-BADPASS`, the tries remaining counted out loud, and a prompt to press **Show the password**. **It never says which of the two was wrong** — a test asserts the same wording for a wrong password on a real account and for a username that does not exist |
| **AC-14** | `/alvoraa-login?for=joining` | It renders | No marketing panel; the heading **"Fill in your details before your first day"**; the username field labelled **"The phone number or email HR sent the message to"** with no placeholder; field text **16 px** (below that iOS zooms and pushes the button off screen); a **full-width 44 px "Show the password"** button under the field; the button **"Sign in and open my form"**; **"I cannot sign in"** instead of `Forgot password?` and `mailto:`; and the grey footer **"<Employer> asked for these details. Alvora only runs the software they use."** With no `for=joining` hint the ordinary page renders and **the same credentials still work** |
| **AC-15** | Too many wrong tries | The lock bites | **"Locked for 30 minutes"** (`JOIN-LOCKED`), naming the clock time, saying **"Nothing you have already filled in is lost"**, and offering no button that would not work. The number of tries and the lock length are **read from `System Settings`, not guessed**, and the countdown wording matches them (⚠ D4b) |
| **AC-16** | **"I cannot sign in"** is pressed | The block opens | It names the two things the message carries, says it may be a text, a WhatsApp message or a slip of paper, and **ends at the employer's own phone number from settings** — never ours, never a `mailto:` |
| **AC-17** | An account whose access has ended — sent, cancelled, expired, hired or turned down — and the **correct** password | Sign in is pressed | **"This sign-in has finished its job"** (`JOIN-ENDED`), the same wording for all five, naming no person, no reason and no employer detail beyond the state. **It must never read "Invalid credentials."** Decision 4a allows this disclosure and the trade is recorded there |

### US-4 · (must not) The sign-in tells a stranger nothing

| ID | Given | When | Then |
|---|---|---|---|
| **AC-18** | Frappe's own guest-allowed `/api/method/frappe.core.doctype.user.user.reset_password` | It is called with a joiner's number, then with a number nobody holds | **Neither produces an email**, because the account's address is non-routable; and **the two answers do not differ** in a way that says whether the number exists. **[UNVERIFIED — Frappe's exact behaviour here is Unknown; `01c` §16. The test pins it either way]** |
| **AC-19** | A random number and a random password | Twenty attempts | Refused, rate-limited by Frappe's own lockout, and **no response reveals an employer's name beyond the branding already on every login page** |

### US-5 · One page and nothing else — **P1**

| ID | Given | When | Then |
|---|---|---|---|
| **AC-20** | A signed-in joiner session | They ask for `/` | They land on **`/joining`**. `home_page_for` answers `/joining` for a joiner account **before** it reaches `_portal_home_for` (`auth.py:44-49`) — one branch in the one function three doors share |
| **AC-21** | The same session | They ask for `/hrms-employee`, `/goals-portal`, `/vendor-portal`, `/driver-portal`, `/checkin`, `/alvoraa-admin`, `/app` | **Each is refused with a 302 to `/joining`** and the screen `01b` §6.1 draws: *"This sign-in only opens your joining form"*, one button that works, code `JOIN-ONEPAGE`. **No page name, no menu, no count** is in the refusal |
| **AC-22** | The same session | They call `/api/method/frappe.client.get_list`, `frappe.client.get`, `frappe.client.set_value`, `/api/resource/Employee`, `frappe.desk.reportview.get`, `frappe.desk.search.search_link`, and `alvoraa_portal.hr_api.get_portal_context` | **Every one is a `PermissionError`, not a redirect** — an XHR cannot follow one usefully (`auth.py:370-375`'s reasoning). The refusal names nothing |
| **AC-23** | The same session | They call the **three joining endpoints** | All three succeed, for **their own row only** |
| **AC-24** | The same session | They **POST to `"/"` with `cmd=frappe.client.get_list`** | **Refused.** The gate reads `frappe.local.form_dict["cmd"]` and only on `"/"` — honouring a `cmd` on any other path hands over the key, as `auth.py:316-324` already explains. **This product has paid for the missing-`cmd` half twice; a test that asks only with a path proves nothing** |

### US-6 · (must not) The gate fails closed, and Guest gets the sign-in

| ID | Given | When | Then |
|---|---|---|---|
| **AC-25** | The gate | **An exception is forced inside it** | **The joiner is refused.** This is the inverse of `test_it_fails_open` and **must not be copied from it**: `lock_until_password_chosen` fails open because locking 441 staff out at shift change is worse than the hole; here a false denial costs **one** person a phone call and a false allow puts an unidentified account inside the portal |
| **AC-26** | A joiner session and `/files/`, `/private/files/` | Either is requested | **Refused.** `/files/` is deliberately **not** on the allow-list, unlike `_FIRST_USE_MAY_REACH` (`auth.py:218`). The masked copy is returned in the upload's own reply, so no file door needs to open |
| **AC-27** | A joiner session | `/logout`, `/login`, `/alvoraa-login`, `/assets/`, `/favicon.ico`, `/api/method/login`, `/api/method/logout` are requested | **Allowed.** Leaving `/api/method/login` out makes the login reply carry "Logged In" and a 403 in one body — the fault `auth.py:231-239` records, found only by a real HTTP request |
| **AC-28** | **Guest** | `/joining` is opened | **The sign-in page**, not the form, the way `hrms_employee.py:9-11` already redirects. The page keeps `Cache-Control: no-store`, `X-Robots-Tag: noindex, nofollow` (header **and** meta), `Referrer-Policy: no-referrer` and **inline-only assets** — and **those headers are no longer set inside a silent `except Exception: pass`** (`www/joiner.py:48-53`, finding F5 of the 078 review) |
| **AC-29** | Every joining endpoint | A registry test runs | **No `allow_guest` endpoint remains in any joiner module** — the enumeration test that pinned three now pins **zero**, and the new-Frappe-app checklist rows read: public pages 0, guest endpoints 0, self sign-up none, new roles 1 |

### US-7 · Stop and come back

| ID | Given | When | Then |
|---|---|---|---|
| **AC-30** | A joiner part-way through | They close the browser and sign in again, **on a different phone** | They land on **the step they left**, with the strip `01b` §5.3 draws: *"You are back, and nothing was lost"*, **"4 of 7 answers done and 2 of 4 documents sent"** — real counts, computed from the row — and the finish-by date. The step list carries a word per row (`Done`, `2 of 4 sent`, `you are here`). **There is no separate "welcome back" page** |
| **AC-31** | The draft | A test reads the database | The typed answers are **on the submission row**, in the columns of §5.2's map, with `status` still `Invited` and `submitted_at` empty. **No new doctype and no new field holds a draft** |
| **AC-32** | A borrowed phone | The joiner presses **Sign out** | The session ends and **nothing about them is left in the browser** — no `localStorage`, no `sessionStorage`, no form values. The button is named, 44 px, and says what it does to the draft |
| **AC-33** | Any upload | A test reads `localStorage` | **No document bytes are ever put there** — `joiner_public.py:38-45` already forbids it; the rule survives the rewrite (OPS-29) |
| **AC-34** | A draft that nobody ever sends | The daily job runs | **Both clocks already cover it**: the documents go at the document clock and the whole row at the 90-day backstop, both measured from `creation` (`joiner_housekeeping._erase_the_untouched`). A test ages an unsent row and asserts it |
| **AC-35** | A part-filled draft, and a limit | The joiner saves it repeatedly | The save is rate-limited **per user** (`_limited(JOINER_KEY, "user")`), the same windows the token version used, asserted by the `__alvoraa_limit__` table test |
| **AC-36** | The questions | More than 8 are ticked in one group | **One screen per group, in record order, and a group over 8 splits into pages of 8** (078 §17.7, unchanged) |

### US-8 · Required means required — on the joiner form

| ID | Given | When | Then |
|---|---|---|---|
| **AC-37** | HR has ticked three fields and marked two of them required | The joiner opens the form | Each required field carries the **amber `Needed` chip** and `aria-required="true"`. The screen says once: *"Anything marked **Needed** has to be filled in before you can send the form. You can leave the rest blank."* **The same word, `Needed`, is used on My Profile — never "mandatory" on one and "required" on the other** |
| **AC-38** | A required field left empty | **Send** is pressed | **Refused.** The refusal **lists each missing item as a tap, not a name**, and each item's own way out travels inside the message (078 §17.6). `status` stays `Invited`, `submitted_at` stays empty, every input still holds what was typed, and **the session is untouched** |
| **AC-39** | The same refusal | A test reads the rule | **The only required list is the one HR ticked.** A test asserts **no field name appears in any required list in our code**, and that a submission with every ticked-required field filled and nothing else is **accepted** (decision 2: we impose nothing of our own) |
| **AC-40** | `alvoraa_joiner_required_fields` naming a field that is **not** in `alvoraa_joiner_fields` | The joiner opens the form | That name is **ignored** — required is intersected with asked at the reader as well as the setter. A required mark **never widens what may be asked or written** (078-SEC-18) |
| **AC-41** | Nothing ticked required | **Send** with one field filled in | **Accepted** — 078's AC-110c rule survives: at least one ticked field with a value, or one document |

### US-9 · A required document is answered, never had

| ID | Given | When | Then |
|---|---|---|---|
| **AC-42** | A document type HR marked required | The block renders | **Three equal-width buttons ≥ 44 px: [Take a photo] [Choose a file] [I will bring it on my first day]**, and the line *"A clear photograph of the document is fine. You do not need a scanner."* **The third button is a valid answer to every required document** — a joiner may not own it yet, may be on somebody else's phone, or may not be able to scan anything |
| **AC-43** | **"I will bring it on my first day"** | It is tapped | The promise is recorded in `bring_on_day_one`, **intersected with the types the organisation actually asked for** (built), the button disappears, **Send is now allowed**, and the Sent screen repeats the promise |
| **AC-44** | A required document with neither answer | **Send** | Refused, as AC-38, with that document listed as a tap |

### US-10 · Documents upload against the session

| ID | Given | When | Then |
|---|---|---|---|
| **AC-45** | A joiner session | An upload is posted **with another submission's name in any argument** | It reaches **their own row or nothing** — never the other row. A **static test asserts no function in the joining module takes a submission, row or name argument**, keeping `joiner_public.py:103-108`'s own promise literally true after the rewrite |
| **AC-46** | An upload | It is posted | The order of checks is unchanged (`joiner_public.py:352-452`): session, then ticked type, then count and running total, then **string length before any decode**, then strict base64, then **magic bytes**, then re-encode. JPEG, PNG, PDF and nothing else; an `.exe` renamed `.pdf` is refused; 5 MB per file, 6 files and 20 MB per joiner |
| **AC-47** | An image carrying GPS EXIF | It is stored | **Re-encoded**, so the stored copy carries no metadata. A PDF is **not** re-encoded and gets the narrower treatment: private, served only through our own endpoint with `Content-Disposition: attachment`, never inline. **We do not scan for malware and no product copy or questionnaire answer may say we do** |
| **AC-48** | An upload that fails | The joiner is watching | **J-E2's wording**: what did not reach us, that nothing else is lost, and a way forward that is not "try again" — another type, or the promise. **A failure never discards what was typed and never ends the session** |

### US-11 · Aadhaar — the covered copy is what is kept *(gated on ⚠ S2)*

| ID | Given | When | Then |
|---|---|---|---|
| **AC-49** | The Aadhaar type ticked | The block renders | **The alternatives come first**: *"You do not have to send this one. A PAN card, passport, driving licence or voter card will do instead, and they are simpler."* Then the promise, then the honest limit: *"We cover the numbers. We are not promising the picture is safe to pass around — it is still a photograph of your card."* **No "securely masked", no "verified", no accuracy figure anywhere** |
| **AC-50** | An upload in progress | The masking runs | A `role="status"` line: *"Covering the first 8 digits… This takes a few seconds. Please stay on this page — nothing is kept until it is done."* **Never a bare spinner** |
| **AC-51** | A synthetic card whose number is found with confidence | It is uploaded | **Exactly one `File` row exists**, holding the **masked** JPEG: the rectangles are **burned into the pixels**, not an overlay or an annotation; no EXIF, no ICC profile, no thumbnail; and the row's `masked_with` carries **the masker version and the engine version, from constants** |
| **AC-52** | The same success | The joiner looks | The covered copy is **shown back once, small, in place, never auto-enlarged**, labelled *"This is what <Employer> has. The photograph you took was not kept."* It comes from the upload's own reply as a `data:` URL — **no second stored copy and no file-serving door** (⚠ parity P5). The card block keeps a **light face in both themes**, because a black bar on a dark surface disappears (`01b` §10) |
| **AC-53** | A **PDF**, an **animated PNG** or a multi-frame image, for this type | It is uploaded | **Refused.** A mask drawn on a PDF is removable and we cannot re-encode one (`joiner_public.py:344-350`); frame two of an animation can carry the unmasked card |
| **AC-54** | Any Aadhaar-ish type | A static test reads the code | **One masker, one public entry point**, and **no other write path stores a document of an Aadhaar-ish type without going through it** — a name-pattern test. And the honest limit is written down: **HR attaching an Aadhaar card to an `Employee` in Desk bypasses this entirely**, so the only true sentence is *"we mask Aadhaar images collected through the pre-onboarding form"*. Nothing wider may be said to a customer |

### US-12 · (must not) No unmasked Aadhaar, ever *(gated on ⚠ S2)*

| ID | Given | When | Then |
|---|---|---|---|
| **AC-55** | Any upload of this type | It is processed | **One `File` insert, with the masked bytes, and no other write of any kind** — no `save_file` of the original, no `NamedTemporaryFile`, no cache entry, no second `File` row, no `localStorage`. A test counts writes |
| **AC-56** | The decoded bytes | Before any code that can raise | **The raw string and the decoded bytes are dropped from `frappe.local.form_dict`.** This is a real hole, not a precaution: Frappe's error snapshot masks form keys containing `key`, `token`, `secret`, `password`, `passwd` or `pwd`, and **`data` is none of those** — so an exception in the masker would write the whole unmasked Aadhaar, base64, into an `Error Log` row |
| **AC-57** | **A forced exception inside the masker** | It raises | **No `Error Log`, no `Version` row and no log line contains any 64-character run of the payload**, and the joiner gets a refusal. Every failure path logs **a code, never the payload** |
| **AC-58** | A masking step that needs a file path | The engine insists | The file goes to a **RAM-backed path** (`/dev/shm`), is unlinked in a `finally`, and that becomes **a recorded deviation with DevOps confirming the container provides it**. *"A temporary file a crash could leave behind"* is exactly what decision 6a forbids |
| **AC-59** | Two 12-digit candidates, or none, or a failed check digit, or a token below the confidence threshold | Any of them | **Refused.** Two candidates means we do not know which to cover. The check digit is implemented as **one named, replaceable function** (M6: widely documented as Verhoeff, **not primary-sourced**) |
| **AC-60** | A masked image, **before storing** | It is read back | **The masked image is read again and must yield no 12-digit candidate and no 8-digit run of the covered prefix.** If anything is still readable → **refused.** This is the clause that makes the control self-checking instead of trusting the masker, and it is why this requirement could be written at all |
| **AC-61** | The rectangles | A test checks them | Inside the image, non-degenerate, and their union covers the bounding boxes of the first 8 digits **plus a margin**. A zero-area or out-of-bounds box → refused |
| **AC-62** | Any exception anywhere in the finding, covering or read-back | It happens | **A refusal.** No `except: pass`, no "store it and warn", no default-allow branch. **The whole step is one function with one answer: masked bytes, or a refusal** |
| **AC-63** | A refusal | The joiner reads it | **`JOIN-MASKFAIL`**, in `01b` §5.5's words: we have not kept that photo; nothing from it was saved; **you are still signed in**; it is nearly always the light or the angle; and **three ways on** — another photograph, another document type, or bring it on day one. It must not say *"try again with a better photo"* and stop, and **must not explain the refusal in a way that teaches somebody how to get an unmasked one through** |
| **AC-64** | A refusal | A test checks the state | **Zero `File` rows**, the account still enabled, the session still live, the submission still sendable, and **no attempt consumed** |
| **AC-65** | The outcome table | A test runs over the fixture corpus | **Two columns only: *stored and read back clean*, or *refused with nothing stored*. The table has no third column.** The day somebody adds "stored, flagged for HR", this test fails. **A measured refusal rate over the fixtures is recorded; no accuracy figure is ever claimed** |
| **AC-66** | Hostile inputs — a truncated JPEG, a PNG with a bogus chunk length, a declared-huge decompression bomb, an animated PNG, a 0-byte file, valid base64 of random bytes | Each is posted | **Each is refused, nothing is stored, no unhandled exception, no worker restart** |
| **AC-67** | A 5 MB PNG that decodes to gigabytes | It is posted | **Refused by a pixel-count ceiling that bites before any pixel work** — `Image.MAX_IMAGE_PIXELS` set explicitly and `im.size` checked first. *The existing photo path has the same gap; fixing it in the shared helper fixes both* |
| **AC-68** | The OCR call | It is made | It is handed **the normalised JPEG our own Pillow produced**, never the request's bytes — so the attacker controls pixels, not file structure. **A static test, because only a reader can see an ordering.** It runs under **a hard timeout and a memory bound**, and either being hit is a refusal (proved with a stub that sleeps). **No network, no shell string** — an argument list, never a joiner-supplied filename |
| **AC-69** | The engine | A release is built | **The binary and its language data are pinned in the image**, and the pin is a DevOps item: a native parser that upgrades silently is a parser nobody reviewed |
| **AC-70** | Rows masked by a version later found wrong | The affected-record query runs | It returns **exactly** the rows holding an Aadhaar-ish document masked by that version and not yet erased, at this tenant — **and bumping the masker constant makes previously stored files findable with no code change.** *A remedy that starts with somebody composing SQL in an incident is not a remedy* |
| **AC-71** | That remedy | It is run | In order: the type stops being offered (one untick, no release); the affected `File` rows are deleted with `delete_permanently=True`; **the row survives, minus the file, and is marked as needing the document again**; one `Notification Log` carries **a count and a reason and no person**. **Because the original was never kept, re-running the masking is impossible — the only remedies are purge and re-ask, and that is the direct cost of decision 6a** |

### US-13 · Send ends the form, not the sign-in

| ID | Given | When | Then |
|---|---|---|---|
| **AC-72** | Everything required answered | **Send** | `status` becomes `Submitted`, `submitted_at` is set, the Sent screen renders with who they will hear from, anything promised for day one, and **a real telephone number from the tenant's settings**. **The typed answers become read-only to the joiner** |
| **AC-73** | The same moment | A test checks the account | **The account is still enabled, still holds its role, and the session still works.** **This is decision 4a and it reverses `01c` 079-SEC-5's first row and M3's default** — both of which say the account dies at Send |
| **AC-74** | A submitted row, inside the access period | The joiner signs in again | They reach **the Sent screen with the document blocks still open**, and may upload a document they promised. The promise text updates. **They cannot change a typed answer, and a second Send is refused** |
| **AC-75** | The Sent screen | It renders | It says the sign-in works until the date, and **does not say "this will not open again"** — that sentence belonged to the link and is now false |
| **AC-76** | The access period has passed, or HR has ended it | The joiner opens the page with a live session | **The dead-page wording, byte for byte the same for all five endings** (`_gone()`'s shape). **Nothing they typed is shown back**, and nothing says which ending it was |
| **AC-77** | A **turned-down** candidate three weeks later | They sign in | **The same answer as every other ending.** A different answer would tell somebody the outcome of their application through a web page instead of from their employer |

### US-14 · Five endings, and never promoted

| ID | Given | When | Then |
|---|---|---|---|
| **AC-78** | Each of the five endings — expiry, cancel, hired, turned down, and HR ending it by hand | Each happens | In **one transaction**: `enabled = 0`, the role removed, **every session cleared explicitly**, and the credential invalidated. **A request on a session captured before the change is refused.** `System Settings.session_expiry` is not touched. The hired case ends at the moment HR links the `Employee`; the turned-down case at the moment HR records it, **not at the next job run** |
| **AC-79** | The person is hired | Their staff login is created | **It is a new account on their real address.** The joiner account is **closed, never promoted**, and **the staff login carries no joiner role** — otherwise US-5's gate would lock the new employee out of their own record. A test asserts both halves (J9) |

### US-15 · Exports are masked and logged

| ID | Given | When | Then |
|---|---|---|---|
| **AC-80** | The doctype JSON | A test reads the permission rows | **No `export` and no `report` for HR Manager or HR User.** A permission-row assertion, so an upgrade or a merge that re-widens it goes red |
| **AC-81** | An **HR Manager** | They use Frappe's own report-view export, or Report Builder, on the doctype | **Refused.** Verified today: the doctype grants them `report: 1, export: 1`, which is every joiner's name, mobile, personal email, home address and emergency contact as a spreadsheet, **unlogged** (J8, 078 F3) |
| **AC-82** | HR's purpose-built **Export everything held** | It is used | It lists files **by name and date, without their bytes** — the mandated default, not a choice — and writes **exactly one log line** carrying the row, the actor, the time and **whether it was masked**, and **never a field value or a file**. A table test over **every** export endpoint asserts one line per call, so a fourth export cannot be added without one |
| **AC-83** | The code | A test looks for a bytes-included export | **There is none, at any permission level.** Dropped (§3): HR sends the files from the row, which is a read. And **for Aadhaar it is satisfied by construction** — no unmasked copy exists to export |

### US-16 · Two clocks

| ID | Given | When | Then |
|---|---|---|---|
| **AC-84** | A closed row **31 days** old with a file attached, `alvoraa_joiner_document_days = 30` | The daily job runs | **Its `File` rows are gone, bytes included (`delete_permanently=True`), and its typed fields are not.** The row survives minus its attachments |
| **AC-85** | The same row at **181 days**, `alvoraa_joiner_not_hired_days = 180` | The job runs | **The typed fields are gone too**, by the existing `erase()` path |
| **AC-86** | Both passes | They run | **Each measures from `closed_on`, never from `modified`** — the reason is already learned and written down (`alvoraa_joiner_submission.py:50-58`): ticking legal hold and unticking it restarts a `modified` clock |
| **AC-87** | A row nobody ever actioned, still `Invited` or `Submitted`, 31 days old | The job runs | **Its documents go at the document clock, measured from `creation`, whatever the row's state.** Otherwise an ignored submission keeps an identity document for the 90-day backstop, against counsel's 30–60 |
| **AC-88** | A row with **legal hold** | Both passes run | **Untouched, however old** — for both clocks. HR's **Purge** is the single exception, because there the erasure is the obligation (`erase:108-115`) |
| **AC-89** | Each pass | It finishes | **Each logs its own count.** Without a separate count for the document pass, *"did the documents actually go"* has no answer |
| **AC-90** | The setter | Somebody saves `alvoraa_joiner_document_days` | **Refused** for a blank, a 0, a non-number, or anything outside **30–60** — beside the existing range check (`settings.py:381-383`). **No value of either setting means "for ever"**, and there is no such value to save |
| **AC-91** | A document deletion | It happens | **HR is told through the `Notification Log` the job already uses, naming the reference and never the person.** *(Deliberate narrowing: HR is told **at** the deletion, not before it — see OQ-6. A pre-warning needs a second setting and a second stamp field, and HR already has legal hold and a visible row.)* |
| **AC-92** | Both numbers | A joiner reads the notice | **Both appear, separately, as the tenant's configured values** — never a literal. *"<Employer> keeps your details for 180 days and then deletes them. A photograph of an identity card is deleted sooner — after 30 days."* One sentence covering both would be wrong about one of them |

### US-17 · (must not) Erased means erased

| ID | Given | When | Then |
|---|---|---|---|
| **AC-93** | **Every** candidate field filled, a file attached, the form submitted, **and HR then edits the row once** | `erase()` runs | By query: **no field value in the row, no `File` row, no `Version` row holding any of those values, no `User` row for that account, no `Deleted Document` holding the name, and no `Email Queue` entry.** Generated from the candidate constant, so a new field cannot escape it. **Without the HR edit the `Version` assertion is vacuous** |
| **AC-94** | `track_changes: 1` on the doctype (confirmed) | A test counts | `select count(*) from tabVersion where ref_doctype = 'Alvoraa Joiner Submission'` after a submit, an HR edit and an erase returns **no row holding a joiner's value**. **This is the one query that settles M1, and until it is run both clocks are a claim** |
| **AC-95** | The two saves that carry personal data — `submit_invite` and `erase()` | They run | **Both pass `ignore_version`**, so no history row is written in the first place; and the erase **sweeps any rows already written**. An audit trail of *who issued and closed an invite* does not need the person's phone number in it |
| **AC-96** | HR's own edits to the row | They happen | **They still write history.** `track_changes` is not turned off: §14's promise to reconstruct who did what a year later depends on it |
| **AC-97** | The joiner's `User` row | Erasure runs | **Deleted with `delete_permanently=True`**, so Frappe's `Deleted Document` keeps no JSON copy of their name. If a linked row makes the delete impossible, the fallback is explicit — **strip the name, strip the roles, disable, and record that the row could not go. Never leave a named user row behind silently** |
| **AC-98** | The retention warning | It is sent | It is a **`Notification Log`** naming the reference, **never an email naming the person** (already right, `joiner_housekeeping.py:136-141`). **An email is a copy we cannot erase** |
| **AC-99** | `purge_submission` | A test calls it | **It works, and it is tested for the first time** — it is counsel's ruling 8 in code, it ignores legal hold on purpose, and it was untested at 078 (D5, R-8) |

### US-18 · My Profile marks what is Needed and still saves

| ID | Given | When | Then |
|---|---|---|---|
| **AC-100** | HR has marked two of the six required, and the employee's record is missing one of them | The employee changes **their phone number** and saves | **The save goes through.** The missing field is **not** a reason to refuse. A test asserts the response is a success and the changed field is written. *Blocking would mean somebody with no permanent address could never change anything on that page again, and their only way out is a call to HR* |
| **AC-101** | The same page | It is opened | The missing ones carry the **amber `Needed` chip** and a **standing amber block names them on every visit**, with one positive sentence: *"This is your own record, so you can change anything here and save as you go. We will keep asking for these until they are filled in."* **Neither screen compares itself to the other** |
| **AC-102** | The same page | A test looks for the old state | **The "blocked save" state does not exist** — deleted from the prototype, not parked beside it (`01b` §8) |
| **AC-103** | HR | They want to chase completeness | **A report over the same ticked fields**, not a new screen. *(Named here because the design names the need; it is one Report Builder view over `Employee`, rung 2.)* |

### US-19 · HR chooses what a joiner is asked, and what is required

| ID | Given | When | Then |
|---|---|---|---|
| **AC-104** | The joiner picker | It opens | Its candidate list **is `MY_PROFILE_WRITE_FIELDS`** — the same six, by identity, so a third list cannot appear and drift. **`full_name` is not a ticked field**: it is HR's own entry at invite, pre-filled on the form, correctable by the joiner, and never marked required by a tick. **[ASSUMPTION — OQ-3]** |
| **AC-105** | The same picker | A test checks what it refuses | **HR-only fields are excluded, and the reason recorded in the code is `01c` §6's: a joiner holds no write right on `Employee` at any level, so the intersection `candidate ∩ has_permlevel_access_to(write)` returns the empty set for them, and admitting one would be a hard-coded exception for the least-trusted principal in the system.** The old sentence — *"there is no permission level on a path opened without a login"* — **is false now and must not appear anywhere.** Plus: the submission's columns carry **no `permlevel` at all** (read in the JSON, 1 Nov), so a field locked at level 1 on `Employee` would arrive at level 0 here — which is why **078-SEC-12's extension matters more after this change: no code ever copies a submission value onto an `Employee`** |
| **AC-106** | Every deny name — including made-up statutory **field** names `aadhaar_no`, `pan_card_number`, `uan`, so the assertion is never vacuous on a site without the India pack — and a field a **payroll rule set** points at | Each is written straight into the setting | **Refused at the setter, and absent from the page endpoint, storing nothing.** The reader intersects again, which is the only half that survives a future UI. **Document *types* are no longer on the deny list** — decision 6a allows the Aadhaar type, and US-11/US-12 guard it instead. The asymmetry is deliberate: a statutory **number as a column** stays refused; a statutory **card as a masked image** is allowed |
| **AC-107** | A fresh site | The joiner picker is read | **`alvoraa_joiner_fields` is empty and the form asks nothing.** The settings card renders the day-one state, and the picker's footer counts (`"OK — ask a joiner for nothing"`). Every candidate field and **every offered document type** has a label, a hint and a Hindi entry — a test fails the day one is added without them |

### US-20 · My Profile in two columns — **⚠ S1, this changes 078's shipped page**

| ID | Given | When | Then |
|---|---|---|---|
| **AC-108** | A **1400 px** window | My Profile renders | **Two columns**: *Your details* on the left; *Your documents* and *Your password* **stacked in the right cell**, sharing its width and left edge, each keeping its own border. Heading order **details → documents → password**. **No card stretches to match its neighbour** (`align-items: start`), and the widest input is **≤ 430 px, not 1280** |
| **AC-109** | **200% zoom**, a 390 px phone, or a split screen | Any of them | **One column, in source order** — from `grid-template-columns: repeat(auto-fit, minmax(min(26em, 100%), 1fr))` and **no media query and no breakpoint**. `min(26em, 100%)` is load-bearing: a bare `minmax(26em, 1fr)` overflowed a 195 px app box, measured. **No `order:` override** — a CSS order that disagrees with the DOM is an accessibility fault waiting to happen |
| **AC-110** | One tile only (nothing to edit, or no documents) | It renders | **It does not sprawl**: the 36em cap on the tile holds it to 468 px inside a 988 px grid, measured. Both near-empty cases render as bounded cards anchored at the top, **and nothing is rebalanced** — no `grid-auto-flow: dense`, no equal-height trick, no card moved. And every full-width card above and below shares the grid's own width |

### US-21 · The employer's own notice

| ID | Given | When | Then |
|---|---|---|---|
| **AC-111** | `alvoraa_joiner_notice_text` **empty** | The page is opened, and the switch is tried | **The page refuses to render and the form cannot be switched on** — exactly as it already refuses with no HR contact (`joiner_public.py:180-199`). **No text, no form.** That makes the notice a precondition without inventing a new precondition mechanism |
| **AC-112** | It is set | The page renders | The employer's own words appear, **before the first input in the DOM** (asserted with `compareDocumentPosition`, as the existing browser test does), with **both configured retention numbers and no literal**, and the employer's own contact. The generated half stays ours and stays honest: the itemised list of what is asked and why, rendered from the actual ticked lists |
| **AC-113** | The same notice | A test reads it | It contains **three sentences we write, and all three precede the first input**: that the sign-in opens **this one page and nothing else**; that **what they send is sent**; and that **afterwards the way to see or delete their data is to ask the employer** (counsel 8). It also says **Aadhaar is voluntary, which other IDs are accepted, and that we black out the first 8 digits before storing it** — and **nothing more than US-11/US-12 deliver.** *A person given a login reasonably expects to sign back in and look; if we do not say otherwise we have misled them.* And the grey line: **the periods and the number above come from the employer's own settings** |

### US-22 · HR sees it, hands it back, deletes it

| ID | Given | When | Then |
|---|---|---|---|
| **AC-114** | A submitted row | HR opens it in Desk | They see the typed answers, the promised documents and the files — **in Desk, with no new screen.** The three buttons stay where they are (`alvoraa_joiner_submission.js`), renamed only where the words changed. **Nothing creates an `Employee`**, and no joining date comes from the form or from the row's own dates |
| **AC-115** | A person asks for their data back, or asks for it to be deleted | HR presses **Export everything held** or **Purge on their request** | Both work, both are logged, the purge **ignores legal hold on purpose** and deletes files bytes included, and the row records `erased_on` and `erased_why`. A comment on the form says so afterwards (built) |

### US-23 · Hindi at parity

| ID | Given | When | Then |
|---|---|---|---|
| **AC-116** | Every new user-facing string — the sign-in state and its four failures (~24), the joiner's new wording (~30), every refusal, every field label and hint, **every offered document type**, and the Aadhaar block | A test reads the translation files | **A Hindi entry exists for each, and every string goes through `drT()`.** **Hindi parity cannot be proved in this environment** (`01c` §16, `01b` §16) — so the test asserts the entries exist, and a Hindi reader must look before switch-on. **A person who cannot read the sign-in page never reaches the form** (ALV-267) |

### US-24 · The fixtures that make this observable

| ID | Given | When | Then |
|---|---|---|---|
| **AC-117** | A dev tenant | The suite runs | It runs against **the form on**, the joiner tick carrying **three** fields with **one marked required**, **one non-statutory document type ticked and marked required**, **one live joiner account**, and **invented data only**. Plus: a row with **every** field filled **and a file attached**, aged twice; **an HR edit between submit and erase**; the hostile-image table generated in code; and a **synthetic Aadhaar generator** in code — drawn card, plausible font, made-up numbers that satisfy the check digit, with skewed, dim, two-number, no-number and QR-like variants. **No real person's Aadhaar may ever be a fixture, on any site, at any time: a real one found in the fixtures or in a test site's files is a P0, not a tidy-up.** **If a run reports "0 findings" without the form switched on, it has proved nothing** |

### US-25 · The one number HR glances at

| ID | Given | When | Then |
|---|---|---|---|
| **AC-118** | A week of use | HR opens the count | `joiner_counts` shows links issued, submissions and the invariant **submissions ≤ links issued** (built). **No new tool.** With the login it gains a second reading: a sign-in is attributable, so *"the same account opened this from two places"* is answerable in a way a forwarded link never was |

---

## 10 · Non-functional requirements, made specific to this slice

From `nfr-budget.md` and 078's `07` §3. **There is no 079 DevOps artifact** (§0.3), so the
masker's numbers are shapes with nobody's measurement behind them yet.

| # | Requirement | Number, and where it comes from |
|---|---|---|
| **NFR-1** | Expected volume | **Tens of rows per tenant per year**, not thousands. One `User` per invited joiner, deleted with the row. No list view needs paging beyond Desk's default |
| **NFR-2** | The joiner's screens | **≤ 2.5 s p95 on a 3G profile, skeleton within 300 ms** (`nfr-budget` §2, phone-first employee-facing). Inline assets only, so no second round trip (OPS-44) |
| **NFR-3** | The one-page gate's cost on every request | **One cheap path check, then one `cmd` check on `"/"` only, then `frappe.get_roles()` (cached), and the database last** — the ordering `lock_until_password_chosen` already uses. **It must add no database read for a member of staff.** A test measures the query count on an ordinary portal request before and after |
| **NFR-4** | Uploads | 5 MB per file, **6 files and 20 MB per joiner** (built). Site-wide `max_file_size = 5` (OPS-24, side effect: every upload on the site) |
| **NFR-5** | **The masking's cost, and the one place this slice could blow a budget** | An OCR pass **plus two re-encodes, inline in a web worker**, on a phone photograph. The photo path already spends ~0.25 s of CPU inside a request. **This is unmeasured.** It is inline and cannot be queued — a queue means storing the original, which decision 6a forbids. **The engineer measures it on a real card photograph before this ships, and if it exceeds the request budget the answer is a lower pixel ceiling, not a background job** |
| **NFR-6** | The masker's timeout, memory bound, pixel ceiling and confidence threshold | **All four are shapes with no measured value.** Whoever measures them sets them; **no number in `01c` 079-PRIV-4 or 079-SEC-8 is a measurement** |
| **NFR-7** | Background work | **One scheduled job, the existing daily one**, which gains one pass. Nothing else goes on a queue. Nothing new is added to any other queue |
| **NFR-8** | Rate limits | Keyed on the **user**, same windows as the token version, through the existing `field_app_limits` (OPS-26). **No new limiter, no CAPTCHA, no new dependency** |
| **NFR-9** | nginx | **No change, and no new page on the compressed-HTML list** (OPS-27). `location /api/` already limits every `/api/method/...` at 120 r/m per address |
| **NFR-10** | Guest upload switch | **`allow_guests_to_upload_files` stays off and the allow-list stays empty** — asserted, not procedurally managed (OPS-40). After this slice there are **zero** guest endpoints to need it |
| **NFR-11** | Disk | The per-joiner caps, the 5 MB file cap, the 30-day document clock and the **hourly** disk alarm already in `scripts/check_workers.sh` (fail below 20 GB, warn below 40 GB). **Nothing new is built for disk** (OPS-30) |
| **NFR-12** | Retention | **Documents 30 days, record 180 days, backstop 90 days, warning 75 days**, all settings, all owned by the tenant (ruling 1) |
| **NFR-13** | Personal and sensitive data | The typed answers are **personal**; an identity document image is **restricted**, and **a masked Aadhaar stays restricted** — the last four digits, the name, the address, the photograph and the QR all survive the masking by design. Private storage, attachment-only serving, no inline render |
| **NFR-14** | Browser tests | Every new DOM test joins `run_dom_tests.js`'s `RUN` list and raises `EXPECTED_BROWSER_TESTS` in the same commit (OPS-45) |
| **OPS-M1** | **The gap I am naming rather than filling** | **The masker's native dependency has no DevOps owner**: which engine, pinned at which version, in which image layer, how much memory a worker may give it, and what a cold start costs. **This belongs in a `07-devops-inputs.md` for 079 before US-11 and US-12 are built** |

---

## 11 · Edge cases and boundaries

The ones that actually bite, not every case imaginable.

| # | Case | What must happen |
|---|---|---|
| E1 | **The joiner shares the credential with a relative** who fills the form for them | **Nothing prevents it and nothing should** — it is the same person's data given by their chosen hand. No identity check is built, and the notice must not claim we know who typed (J7) |
| E2 | **Two joiners, one number** — a shared family phone | AC-9 refuses the second invite on that number and asks for the other identifier. Without it this is ALV-242 again |
| E3 | **A joiner who already works there** (a re-hire, or a contractor becoming staff) | Their real login exists. The invite's duplicate guard (AC-9) refuses the number; HR uses the email, or skips pre-onboarding — **the joiner account is never the staff account** (AC-79) |
| E4 | **The person starts earlier than planned**, before they finish the form | HR hires them; the account ends (AC-78); whatever was sent stays on the row until the clocks take it. The missing answers are chased on My Profile, with `Needed` marks |
| E5 | **The joiner never comes back** | The link expires, the row goes `Expired`, `closed_on` is stamped, the documents go at 30 days and the row at 180 |
| E6 | **Nobody at the employer ever actions it** | The 90-day backstop takes the row and **the document clock takes the files at 30 days first** (AC-87) |
| E7 | **A document uploaded into the wrong box** — an Aadhaar card sent as a PAN card | **The masking follows the declared type, so this skips it.** `01b` J8 and `01c` M5's sibling. **Flagged, not solved: OQ-5.** Detecting a 12-digit Aadhaar on *every* upload is the alternative and it is a much bigger masker |
| E8 | **The joiner's phone loses signal mid-upload** | The typed answers are already on the server (US-7), so nothing is lost; the upload refusal offers the promise as a way out (AC-48) |
| E9 | **Two uploads at once**, or the same document twice | The count and byte ceilings are checked per call; a second file of the same type is a second `File` row, which is HR's to sort out. **No locking is added** — 6 files is the ceiling |
| E10 | **HR cancels while the joiner is typing** | Their next call gets the dead-page answer; their session is already cleared (AC-78). **They lose what was not yet saved, and nothing says why** |
| E11 | **The clock settings are changed mid-life** | Both passes read the setting live; the clocks measure from `closed_on`/`creation`, never from `modified`, so changing a setting does not restart anything (AC-86) |
| E12 | **A legal hold is ticked and unticked** | Nothing restarts. The reason this matters is already in the code's own comment |
| E13 | **The tenant unticks the Aadhaar type after images are stored** | Nothing new arrives; the stored masked copies stay until their clock. That untick is also step 1 of the remedy (AC-71) |
| E14 | **Multi-company / multi-branch** | A joiner belongs to no company and no branch — there is **nothing to scope**, and that is the point. HR's existing company scope decides who sees the row |
| E15 | **A time zone or DST boundary** | Both clocks are whole days from a stored datetime through `add_to_date`, as today. **No new time handling** |
| E16 | **Daylight-saving and the expiry date** | The sign-in page prints a weekday and a date, never "7 days" (`01b` §3 line 6) |
| E17 | **A cancelled or amended document** | There is no submit/cancel workflow on this doctype. Every move out of a terminal state is already impossible |
| E18 | **Bulk import of submissions** | Not offered, and HR Manager loses `report`/`export`; `import` was never granted. **Data Import on this doctype is a System Manager act** |
| E19 | **The masker is unavailable** — the engine missing from the image | **Every Aadhaar upload refuses**, with AC-63's wording, and a log line names the code. **It never falls back to storing the image** |
| E20 | **The employee on My Profile has no `Employee` record** | Already handled: `{"no_employee": True}` rather than a 500 (`my_profile.py:63-72`) |
| E21 | **A tenant with nothing ticked** | The joiner picker's day-one state; the form asks nothing; HR can still invite but there is nothing to fill in. **Worth a sentence on HR's screen** — it is the shipped default |
| E22 | **An employee with no manager, or a circular reporting line** | Not reachable from this slice. Named so nobody looks for it |

---

## 12 · Data migration and backfill

**Almost nothing, and that is because the feature has never been on.**

| What | Action | Rollback |
|---|---|---|
| Existing submissions | **There are none at any tenant** — the form ships off and no joiner has ever submitted anything. So there is **no backfill, no residue and nothing to clean** | — |
| `web_form_request` and its `Web Form` anchor | The field is dropped; **if any `Web Form Request` row exists on a dev site, delete it in the same patch** — it is a clear-text key with nothing left to open | Recreate nothing. The anchor record is not needed again |
| `Alvoraa Joiner Submission` permission rows | A patch removes HR Manager's `report`/`export` and HR User's `report`. **`Custom DocPerm` is the real table** on a site that has ever touched permissions — the 27 Oct lesson | Re-add the rows. **Do not**: counsel's ruling 9 |
| The six new settings keys | Written by the `DEFAULTS` dictionary on migrate. **The four tick keys and the notice text ship empty; the document clock ships at 30** | Unset them; the form refuses to switch on, which is the shipped state anyway |
| `alvoraa_hr_contact_phone` / `_email` | **Added to the settings screen for the first time.** Any value a test left behind stays; nothing is migrated | — |
| The `Alvoraa Joiner` role | Created on migrate, with no permission rows | Delete it; no row points at it except a joiner's `User` |
| `System Settings.allow_login_using_mobile_number` | **A deliberate, recorded tenant change, not a patch** (⚠ S3) | Turn it off; joiners then cannot sign in |
| The masker's engine | **An image change, pinned, and a DevOps item** (OPS-M1) | A rollback of the image refuses every Aadhaar upload (E19) |
| `Version` rows already written on a dev site | The erase sweep covers them; nothing needs a migration on a live site, because there are no rows | — |

---

## 13 · Notifications and messages — the exact words

Taken from `01b`, which is where the designer wrote them. **Every string is translatable and
has a Hindi entry (AC-116).** Sample names are the prototype's invented ones.

| # | Trigger | To whom | The words | What it must never carry |
|---|---|---|---|---|
| M1 | HR makes the sign-in | HR, once, on screen | The six lines of `01b` §3: the employer's name, what it is and how long it takes, the address, the sign-in name, the password, a weekday finish date, **"Keep this message — you need it if you stop and come back"**, and a named person with a phone number | — |
| M2 | The same reply | HR, once | **"Priya Khanna can now sign in. You will not see this password again."** … **"She cannot see anything else. This sign-in opens her own form and nothing else at PP Jewellers. She is not an employee, not in your headcount, not on the organisation chart, and not a paid seat until she starts."** | — |
| M3 | HR tries to invite too early | HR | `01b` §6.3's three-line list, each marked **not set** or ✓, with **[Open these settings]** | — |
| M4 | Wrong password | The joiner | `JOIN-BADPASS`, AC-13 | **Which of the two was wrong** |
| M5 | Lockout | The joiner | `JOIN-LOCKED`, AC-15, naming the clock time | A button that would not work |
| M6 | Cannot sign in | The joiner | `JOIN-NOSIGNIN`, AC-16, ending at the employer's phone number | Our own contact details |
| M7 | Access ended | The joiner | `JOIN-ENDED`, AC-17 | **Which ending it was**, any person, any reason |
| M8 | Any other address | The joiner | `JOIN-ONEPAGE`: *"This sign-in only opens your joining form … Once you start work, the same sign-in opens your own staff pages."* | Any page name, menu or count |
| M9 | Masking in progress | The joiner | AC-50's `role="status"` line | — |
| M10 | Masking refused | The joiner | `JOIN-MASKFAIL`, AC-63 | Why it was refused in a way that teaches somebody how to get an unmasked one through |
| M11 | Masked and kept | The joiner | *"This is what PP Jewellers has. The photograph you took was not kept."* | — |
| M12 | Send refused | The joiner | Each missing item as a **tap**, with its own way out inside the message | A field name a joiner cannot act on |
| M13 | Sent | The joiner | Thank you; who they will hear from; **what they are bringing on day one**; a real phone number; and that the sign-in works until the date | **"This link will not open again"** — false under decision 4a |
| M14 | Signing out | The joiner | *"Everything you have filled in is saved with PP Jewellers. You will need the phone number and the password from Arjun Bhatia's message to come back."* | — |
| M15 | 75 days, nobody actioned it | **HR who issued it**, `Notification Log` | Built: *"A joiner's details will be deleted in {0} days"*, naming **the reference** | **The person's name, any field, any file** |
| M16 | The document clock deletes files | HR who issued it, `Notification Log` | *"The identity documents on invite {0} were deleted after {1} days. Ask again if you still need them."* | The person, the type, the file |
| M17 | A masking rule found wrong | HR, `Notification Log` | **A count and the reason** | Any person |
| M18 | My Profile, something missing | The employee, on screen | AC-101's amber block and `Needed` chips | A comparison with the joiner form |

**No email is sent to a joiner by any path in this slice.** An email is a copy we cannot
erase, and it would put a live credential in a mailbox. HR hands the message over by whatever
means they already use (M2 answered).

---

## 14 · Audit and traceability — what can be reconstructed a year later

| Question, a year later | What answers it |
|---|---|
| Who invited this person, and when? | The surviving shell of the row: `invited_by`, `creation`, `expires_on`, `status`, `closed_on` — **personal data stripped, the trail intact** (`erase()`'s own docstring) |
| Did they sign in, and when? | **Frappe's own login trail, per account.** This is the design's real prize over the link: a sign-in is attributable. **AC-8 pins it — if the trail does not exist, this row and §7.3's claim come out of the spec rather than the claim going quiet** |
| Who changed the row, and what to? | `Version` rows for **HR's** edits (AC-96). The joiner's own submit and the erase write none, on purpose (AC-95) |
| Who exported a person's data? | **One log line per export**, with the row, the actor, the time and whether it was masked (AC-82) |
| Who read a submission? | **Nothing records it.** Named debt, R-6, deliberately not required: no ruling asks for it and the document clock is 30 days. The cheapest close remains one `source` value on `Alvoraa Photo Access Log` |
| Who turned the form on, or changed a clock, or ticked a field? | **A `Version` row per change**, in the same transaction, naming the key, the old value and the new — and a refusal is logged for anybody who was not a System Manager (`_set_access_setting`) |
| Which masking rule made this stored image? | `masked_with` on the row, from constants (AC-51), and the affected-record query (AC-70) |
| Was the deletion actually done? | **A count per pass in the log** (AC-89), plus `erased_on` and `erased_why` on the shell |
| Was a credential shared? | **Still not answerable** when the holder shares it willingly (R-5). The invariant in AC-118 is what catches the rest |

---

## 15 · Localisation and accessibility

- **Every user-facing string goes through `drT()`**, and **every one has a Hindi entry**
  (AC-116). The door is ~24 strings with its failures and the joiner's new wording ~30 more.
  **Hindi parity cannot be proved in this environment** — a Hindi reader must look before
  switch-on. This is ALV-267 and it got heavier, because the notice is now itemised,
  employer-authored and carries two numbers.
- **Dates** are a weekday and a date, never "in 7 days". **Numbers** are plain days.
  No currency appears anywhere in this slice.
- **Phones first.** Field text **16 px** (below that iOS zooms on focus and pushes the button
  off screen), every target **≥ 44 px on a phone and ≥ 24 px on a mouse**, nothing under
  12 px, nothing wider than the app box at 390, 360 and **390 at 200% text**.
- **The frontline joiner has no laptop.** One screen per group, one question per row, a
  full-width reveal button, and a step list whose status is **a word, not a tint**.
- Every refusal is `role="alert"`, every confirmation and the masking wait `role="status"`.
  Colour is never the only signal; the reveal button has words on it; nothing depends on an
  icon; the error names the field.
- **The masked card block keeps a light face in both themes** — a black redaction bar on a
  dark surface vanishes, and that bar is the one thing the screen exists to show.
- The **`View` link in the documents row goes from 20 px to ≥ 24 px** on a mouse — a
  pre-existing WCAG 2.2 AA failure the design's measurement found.

---

## 16 · Prototype parity

**Surbhi's rule, 21 Oct 2026: build every feature in the approved prototype exactly as
drawn; any difference needs her yes first.** The design names
`prototype-v8.html`; **the newest file on disk is `prototype-v7.html`** (§0.3), so this
table is read from v7 — **9 screens, 66 states**, the five that 079 owns listed first.

| # | Screen | States (v7) | Built as drawn? | Difference, and whose decision |
|---|---|---|---|---|
| **0** | **Getting in** — the message ×2, HR's block, HR not-ready, sign-in ×6 | **10** | **Yes** | **P1 · the address.** The design prints `ppj.alvoraa.co/joining`; the built page is `/joiner`. **Recommendation: rename to `/joining`** — the feature is off everywhere, so the rename is free today and never again. The sign-in hint becomes `/alvoraa-login?for=joining`, and `/login` keeps working |
| **7** | **The joiner's form** — welcome, coming back, the notice, questions, documents, the day-one answer, Aadhaar ×4, a photograph, check, send refused, sent, pacing, ended, upload failed | **17** | **Yes, with two differences** | **P5 · the masked copy** is shown back **from the upload's own reply**, and on a **later visit** the block says *"kept, numbers covered"* in words rather than re-drawing the picture. The alternative is a fourth endpoint streaming a private file to a joiner session (§2 C5). **P6 · the Sent screen's words change under decision 4a** — it no longer says the access has ended, because it has not. The *"The access has ended"* state itself still exists and is still drawn |
| **8** | **What this sign-in opens** — another address, signing out, signed out | **3** | **Yes** | — |
| **1** | **My profile** — normal, something needed, nothing to edit, saving, save failed, no employee record | **6** | **Yes, and it changes a page that has shipped** | **P3 · `prototype-v8.html` is missing**, and v8 is precisely the state that moves *Your password* into the right column. Specified from `01b` §10a's words and its measurements. **P4 · ⚠ S1 — this lands on 078's live page, and `01b` §10a says the call is Surbhi's.** **P2 · the picker draws 16 candidate rows** — including date of birth, permanent address, bank account number and IFSC code. **The code's allow-list is six** (`MY_PROFILE_WRITE_FIELDS`), and the extra rows are either on `people_fields.NEVER` or are HR's own. **Recommendation: offer the six.** Widening the list would grant self-service write on a date of birth and a bank account, which 078-SEC-7 and the deny list exist to refuse |
| **6** | **Organisation settings** — the page, four pickers, day-one, no documents, 12 documents, remove-on-tag, saved | **10** | **Yes — the fourth picker is now built** | 078 ⚠ DECISION B made the joiner section **facts only**, because the Web Form owned the list. **Decision 5 reverses that**: the joiner's tick is ours, so the fourth picker is built, with its own **Must fill in** tick and the day-one empty state. **"Remove on the tag" stays unbuilt** — 078 decision 6 refused it |
| 2 | Faces on the chart | 5 | 078, untouched | — |
| 3 | Faces in the table | 1 | 078, untouched | — |
| 4 | Seat tray + mini profile | 10 | 078, untouched | — |
| 5 | The seat page | 4 | 078, untouched | **Listed, not fixed:** `01b` §10a measured a 1280 px field here too and **left it alone on purpose**. One page is enough to judge the two-column rule by |

**Everything else is built exactly as drawn.** Six differences, **P1 to P6**, and **four of
them need Surbhi: P1, P2, P4 and P5.** P3 is a missing file and P6 follows from a decision
she has already taken.

**One honest gap carried from `01b` §16:** nothing in this design has been seen on a running
site. The joiner sign-in does not exist, so every measurement is of the prototype in Chrome.

---

## 17 · Compliance-impact sub-analysis

Built on `01c`, not re-derived. **I am not a lawyer**, and counsel's written advice has not
been read by me or by the security engineer — both of us worked from `00-decisions.md` §7.

### 17.1 Data touched

| Field / object | Sensitivity | Purpose it was collected for | Lawful basis (as recorded) | New collection? |
|---|---|---|---|---|
| `full_name`, `mobile`, `personal_email`, `current_address`, `emergency_*` on the submission | **sensitive** (personal, about a non-employee) | Making a staff record before day one | The employer's own, as the Data Fiduciary (ruling 1). **Not recorded by us** | No — 078 |
| An uploaded identity document (PAN, passport, licence, voter ID) | **statutory-id** | HR's verification before day one | the employer's | No — 078 |
| **A masked Aadhaar image** | **statutory-id, and masking does not declassify it** — the last four digits, the name, the address, the photograph and the QR survive by design | HR's verification | the employer's, and **voluntary with alternatives accepted** (ruling 5) | **Yes, new in this slice.** Impossible to avoid without refusing the type, which Surbhi declined with the cost named (decision 6a) |
| **The unmasked Aadhaar, in a worker's memory** | **statutory-id** — the most sensitive thing this product has ever held | **To be masked, and nothing else** | the employer's | **Yes, and it is new that our code reads an identity number at all.** It exists for **milliseconds** and never reaches disk, a temporary file, a log or an error row |
| **The joiner's `User` row** — login id, their name, `mobile_no`, roles, enabled flag | **sensitive**; a new table and a new copy | The only way to open one page | the employer's | **Yes.** Minimised to a name and a number; no email, no photograph, no address. **Deleted with the submission** |
| **The first credential** | **restricted** | One person, one form | — | Yes. Never stored in clear, never logged, dies with the account |
| **The session** | restricted (it is a credential) | Keeping the form open | — | Yes. Killed at every ending, not left to expire |
| **`tabVersion` rows for the submission** | **sensitive, and currently invisible** | **None. A side effect of `track_changes: 1`** | none | **No — we have been keeping it by accident.** US-17 stops it |
| `masked_with` | internal | Answering "which rule masked this" when the rule turns out to be wrong | — | Yes. **Never digits, never a confidence value that encodes the number** |
| **The employer's notice text** | internal, but **legally load-bearing** | Ruling 6 | — | Yes, and it is the employer's own words |

**Data minimisation, stated:** the joiner's tick ships **empty**, HR-only fields are
excluded, statutory **numbers as fields** are refused in the setter and again in the reader,
and the `User` row holds the least that will let somebody sign in.

### 17.2 Obligations engaged

| Obligation | Source | What this slice must do | The feature that does it |
|---|---|---|---|
| Notice before collection, in the Fiduciary's own terms | DPDP s.5; counsel 6 | The employer's own words, before the first question, with both periods and their own contact; **no words, no form** | US-21 |
| Purpose limitation and minimisation | DPDP s.4, s.6(1) | Closed allow-lists at both ends; the tick ships empty | US-19, AC-106 |
| Storage limitation | DPDP s.8(7); counsel 3, 4 | **Two clocks**, no "for ever" value, real deletion | US-16 |
| Erasure on request | DPDP s.12; counsel 8 | HR's Purge, ignoring legal hold, bytes included — **and tested for the first time** | US-22, AC-99 |
| Access / "what do you hold about me" | DPDP s.11; counsel 8 | HR's Export, in one click, logged | US-22, AC-82 |
| Reasonable security safeguards | DPDP s.8(5) | The one-page gate, a role with no permissions, one credential per person, limits, type and byte ceilings, hostile-input handling | US-5, US-6, US-1, US-12 |
| Breach notification | DPDP s.8(6); CERT-In **6 hours from awareness** | **The employer decides; we tell them promptly with the numbers and the affected-record list.** The runbook has **never been drilled** (R-10) | AC-70, AC-71 |
| Aadhaar's own regime | **unknown to us** | Masked image only; voluntary; alternatives offered | **⚠ C2 below** |
| Processor duties | DPDP s.8(2); ruling 1 | Every period, every list and the notice are **the tenant's settings** | §5.3 |

**Checked `compliance-feature-map.md` first.** The retention job, the access-granting
`Version` rows, the refusal log and the export log already exist and are **not respecified**
here. The per-field sensitivity classification (map item A1) **stays deleted** — still the
right long-term mechanism, still rung 5 for a rung-2 job.

### 17.3 Visibility delta

**Nobody can see anything about anybody else that they could not see before.** The four
changes are in §7.3, and three of them narrow. The negative cases are §7.2's eleven rows,
each with a named criterion. **The one new object is a `User` row for a non-employee**, which
System Manager can see in a user list and which erasure must delete.

### 17.4 Decision automation

**No decision about a person is automated or materially influenced by this slice.** The
masker **finds digits and covers them**; it draws no inference about anybody, scores nobody
and ranks nobody. 078-PRIV-3's refusal stands: nothing collected here is matched, scored,
used to confirm who checked in, or sent to a model.

**The one place a machine's answer affects a person:** a refused upload. The accountable
human is **HR** — the joiner's route out is another document type or *"I will bring it on my
first day"*, and the refusal names the employer's own contact. **The joiner is told plainly
that nothing was kept and that they are still signed in.** They contest it by sending
something else or by ringing HR. **No AI feature of any kind is in this slice**, so §7's
guardrail list and the prohibitions do not engage — and the masker is a deterministic image
operation, not a model.

### 17.5 Retention and deletion

| What | How long | On whose instruction | Survives an erasure request? |
|---|---|---|---|
| An identity document, including a masked Aadhaar | **30 days** from closing, or from arrival if nobody actioned it | the employer's setting, within counsel's 30–60 | no |
| The typed answers | **180 days** from closing | the employer's setting, within counsel's 180–365 | no |
| Anything nobody actioned | **90 days** from arrival, documents sooner | the employer's setting | no |
| The `User` row, the session, the credential | with the submission; the account ends at the first of its five endings | — | no |
| `Version` rows holding the joiner's values | **none are written, and any that exist are swept** | — | no |
| **The shell: `status`, `invited_by`, the dates, `erased_on`, `erased_why`, the `Employee` link** | kept | — | **Yes, deliberately.** It is decision-bearing — it answers *"who invited somebody on 3 November"* — and it holds nothing about the person |
| A legal hold | wins over both clocks, **except** HR's Purge | the employer | — |

### 17.6 ⚠ Open compliance questions

**Flag, do not rule.** None of these is mine to settle.

| # | Question | Who must decide | What it blocks |
|---|---|---|---|
| **⚠ C1** | *"Does the 180–365 day range still apply when the row holds a statutory **document** for somebody who was never employed?"* (078 ⚠ COMPLIANCE 3) | Surbhi with counsel | **Switch-on at a tenant with real joiners.** Not the build. *Fail-closed meanwhile:* the document clock stays at **30**, its shortest value |
| **⚠ C2** | *"May an employer ask for an Aadhaar card at all before employment, and does Aadhaar's own statutory regime restrict who may handle the identity?"* (078 ⚠ COMPLIANCE 4, sharpened) | Surbhi with counsel | **⚠ S2 — the masker itself.** A "no" makes the slice's largest piece of work worthless, so **ask before building it** |
| **⚠ C3** | *"Our software reads the unmasked number in memory in order to black out the first eight digits, and never stores the original. Does any UIDAI regulation restrict that, and does doing it as the employer's Processor engage a duty on us?"* | Surbhi with counsel | Offering the Aadhaar type at a tenant with real joiners |
| **⚠ C4** | *"Does the 30–60 day window apply unchanged to a **masked** Aadhaar image?"* | Surbhi with counsel | Nothing in the build. *Fail-closed:* 30 days |
| **⚠ C5** | *"Is offering alternatives and saying so in the notice enough for 'voluntary', or must the joiner's choice be recorded?"* | Surbhi with counsel | Nothing. *Fail-closed:* the notice says it plainly in both languages and **we build no consent ledger** — guessing would be a compliance feature nobody asked for |
| **⚠ C6** | **Does the Aadhaar card's QR code carry the full number?** (`01c` M5) | **Anybody with a card and a QR scanner, in five minutes** | **⚠ S2.** If it does, digit-masking leaves the identifier machine-readable and the masker needs a 2D-barcode library as well. *Fail-closed: the Aadhaar type stays unticked until this is answered* |
| **⚠ C7** | **Does `tabVersion` hold the joiner's values after an erasure?** (`01c` M1) | **One query settles it** — the engineer, on a dev site | Nothing in the design. **But until it is run, counsel's rulings 3 and 4 are claims.** AC-94 is that query |

**ALV-215 still gates switch-on.** And the compliance baseline was verified 24 Aug 2026;
**it goes stale on 22 November 2026**, inside this slice's life — re-verify before anybody
answers a customer questionnaire from it.

---

## 18 · Traceability — every requirement lands somewhere

| Source | ID or line | Story | Criteria | Status |
|---|---|---|---|---|
| Decisions | 1 · a restricted login, no `Employee` record | US-1, US-5 | AC-1, AC-3, AC-20 | covered |
| Decisions | 2 · HR marks fields and documents required | US-8, US-9, US-19 | AC-37–AC-44, AC-104 | covered |
| Decisions | 3 · My Profile never refuses a save | US-18 | AC-100–AC-102 | covered |
| Decisions | 4 · they may come back | US-7 | AC-30–AC-32 | covered |
| Decisions | **4a · Send ends the form, not the sign-in** | US-13 | AC-72–AC-77 | covered — **and it overrides `01c` 079-SEC-5 row 1 and M3** |
| Decisions | 4a · the page may say "access has ended" | US-3 | AC-17 | covered |
| Decisions | 5 · one candidate list, two ticks, joiner's ships empty, HR-only excluded | US-19 | AC-104, AC-105, AC-107 | covered |
| Decisions | 6 · no typed statutory field | US-19 | AC-106 | covered |
| Decisions | 6a · Aadhaar, mask or refuse | US-11, US-12 | AC-49–AC-71 | covered, **gated ⚠ S2** |
| Decisions | 7 · counsel's nine rulings | — | §17.2 | covered, two still open (⚠ C1, ⚠ C2) |
| Decisions | §9 · R11, HR exports unmasked and unlogged | US-15 | AC-80–AC-82 | covered |
| Decisions | §9 · no record that HR read a submission | — | — | **dropped, named debt R-6** (§3) |
| Decisions | §9 · the joiner page is English only | US-23 | AC-116 | covered, unprovable here |
| Security | **079-SEC-1** the account's shape | US-1 | AC-1–AC-3, AC-6, AC-8 | covered |
| Security | 079-SEC-2 the credential | US-1 | AC-4, AC-5, AC-10 | covered |
| Security | **079-SEC-3 the one-page gate, fail closed** | US-5, US-6 | AC-20–AC-29 | covered |
| Security | 079-SEC-4 the endpoints trust the session | US-10 | AC-45, AC-29, AC-35 | covered |
| Security | 079-SEC-5 the endings, one answer | US-14, US-13 | AC-76–AC-79 | covered, **first row amended by decision 4a** |
| Security | 079-SEC-6 export | US-15 | AC-80–AC-83 | covered; **clause 3's unmasked export dropped** (§3) |
| Security | 079-SEC-7 the `ignore_permissions` count goes **down** | US-10 | AC-29 + §19 OQ-7 | **partly — the number is the engineer's to set in the same commit** |
| Security | 079-SEC-8 the masker's attack surface | US-12 | AC-66–AC-69 | covered, gated |
| Privacy | 079-PRIV-1 two clocks | US-16 | AC-84–AC-92 | covered |
| Privacy | 079-PRIV-2 erasure is complete | US-17 | AC-93–AC-99 | covered |
| Privacy | 079-PRIV-3 the employer's notice | US-21, US-2 | AC-11, AC-12, AC-111–AC-113 | covered |
| Privacy | 079-PRIV-4 mask or refuse | US-11, US-12 | AC-49–AC-65 | covered, gated |
| Privacy | 079-PRIV-5 nothing extra collected | US-1, US-7 | AC-3, AC-6, AC-31 | **covered except the draft — resolved against it, §2 C2** |
| Privacy | 079-PRIV-6 when the masking is found wrong | US-12 | AC-51, AC-70, AC-71 | covered, gated |
| Security (078, surviving) | 078-SEC-11 upload rules | US-10 | AC-46, AC-47 | re-verified |
| Security (078, surviving) | 078-SEC-12 and its extension | US-19, US-22 | AC-3, AC-105, AC-114 | re-verified |
| Security (078, surviving) | 078-SEC-17, 078-SEC-18 | US-19, US-8 | AC-104, AC-40 | re-verified |
| Privacy (078, surviving) | 078-PRIV-10, -11, -12, -13, -14, -7 | US-19, US-9, US-23, US-17 | AC-106, AC-107, AC-42, AC-116, AC-93 | re-verified |
| Prototype | `0 · Getting in`, 10 states | US-1, US-2, US-3 | AC-11–AC-17, AC-5 | covered · **P1** |
| Prototype | `7 · The joiner's form`, 17 states | US-7 to US-13 | AC-30–AC-77 | covered · **P5, P6** |
| Prototype | `8 · What this sign-in opens`, 3 states | US-5, US-7 | AC-21, AC-32 | covered |
| Prototype | `1 · My profile`, 6 states | US-18, US-20 | AC-100–AC-110 | covered · **P2, P3, P4** |
| Prototype | `6 · Organisation settings`, the joiner picker and the required tick | US-19 | AC-104–AC-107 | covered |
| Design | §14 criterion 1 (Website User, one role, no Employee) | US-1 | AC-1–AC-3 | covered |
| Design | §14 criterion 2 (the ten doors, as that login, on a fresh site) | US-6 | AC-21, AC-22, AC-24, AC-26 | covered |
| Design | §14 criteria 3, 4, 5 (reveals nothing, ended ≠ wrong, lockout) | US-3, US-4 | AC-13, AC-15, AC-17, AC-18 | covered |
| Design | §14 criteria 6, 7 (the draft survives; sign-out leaves nothing) | US-7 | AC-30–AC-33 | covered |
| Design | §14 criterion 8, 9 (no invite until set; two clocks printed) | US-2, US-16 | AC-11, AC-92 | covered |
| Design | §14 criterion 10 (mask or refuse) | US-11, US-12 | AC-49–AC-65 | covered |
| Design | §14 criterion 11 (Send ends the access) | US-13 | AC-72–AC-75 | **covered as its D5 alternative — decision 4a chose it** |
| Design | §14 criterion 12 (My Profile always saves) | US-18 | AC-100 | covered |
| Design | §14 criterion 14 (log every sign-in, HR read, export) | US-1, US-15 | AC-8, AC-82 | **two of three. The HR-read record is dropped** (R-6) |
| Design | J6 (drafts hold personal data before Send) | US-7 | AC-34 | covered |
| Design | J7 (two clocks are one setting) | US-16 | AC-84–AC-90 | covered |
| Design | J8 (an Aadhaar in the PAN box skips masking) | — | — | **gap — OQ-5, Surbhi's, via ⚠ D6** |
| DevOps | OPS-24, 26, 27, 29, 30, 33, 44, 45 | NFR-4, 8, 9, 11, 14 | §10 | carried |
| DevOps | **OPS-25, OPS-39, OPS-40** (the guest-upload switch, the token's name, the allow-list) | US-6 | AC-29, NFR-10 | **closed by there being no guest path and no token** |
| DevOps | **the masker's dependency, pin, memory and timeout** | — | — | **gap — OPS-M1, nobody owns it** |

**Three gaps, listed as gaps:** J8 (OQ-5), the masker's DevOps inputs (OPS-M1), and
079-SEC-7's number. **Two items deliberately not adopted** — the HR-read record and the
unmasked export — and both are recorded with the reason in §3, **as my recommendation, for
Surbhi to overturn**.

---

## 19 · Open questions

| # | Question | Owner | What it blocks | My recommended default |
|---|---|---|---|---|
| **OQ-1** | **⚠ S1** · Does the two-column My Profile ship in 079, changing 078's live page? | **Surbhi** | US-20 | **Ship it here.** Two CSS rules, a DOM reorder, and the fault is live today |
| **OQ-2** | **⚠ S3** · May `allow_login_using_mobile_number` go on, knowing it changes sign-in for every employee at that tenant? | **Surbhi** | US-1, US-3 | **Yes**, with AC-9's duplicate guard and the side effect in the release note |
| **OQ-3** | Is `full_name` outside the tick, always asked and never required? (§2's closing note) | **Surbhi** | AC-104's wording only | **Yes** — it is HR's own entry, and making it required would be a rule of ours |
| **OQ-4** | **⚠ S2** · Is the masker built before counsel answers ⚠ C2 and ⚠ C6? | **Surbhi, with counsel** | US-11, US-12 — **13 of the slice's 83 points** | **Ask counsel first.** Build the other 23 stories now; the Aadhaar type is a tick, so nothing waits on it |
| **OQ-5** | **`01b` ⚠ D6** · Does the masking follow the **declared** document type, or every image? An Aadhaar sent in the PAN box skips it today | **Security, then Surbhi** | whether J8 is a gap or a design | **Follow the declared type for now, and say so plainly** — "we mask Aadhaar images sent as Aadhaar". Detecting a 12-digit number on every upload is a much bigger masker and a much bigger refusal rate |
| **OQ-6** | Is HR warned **before** the document clock deletes, or **at** the deletion? (AC-91) | **Surbhi** | one notification's timing | **At the deletion.** A pre-warning needs a second setting and a second stamp field; HR already has legal hold and a visible row |
| **OQ-7** | **079-SEC-7** · what number does `joiner_public.py`'s `ignore_permissions` ceiling drop to? It is **5** today against a ceiling of 4, and four of the five existed only because the caller was Guest | **Engineer**, in the same commit | the CI ceiling | **Argue each one away rather than re-ceilinging.** A ceiling that moves sideways means the rewrite kept a Guest-shaped design behind a login |
| **OQ-8** | `01b` ⚠ D4b · the **lockout threshold and duration** in `System Settings` | **Engineer** | AC-15's countdown wording | **Read them, do not guess**, then write the number into the copy |
| **OQ-9** | Does Frappe write an attributable login row for a Website User, and does a live session die when `enabled` goes to 0? | **Engineer** | AC-8, AC-78 | **Assume neither.** Clear sessions explicitly, and let AC-8 fail loudly if the trail is absent |
| **OQ-10** | `01c` S2 · may HR re-issue a credential for a joiner who lost theirs, or only cancel and start again? | Surbhi | HR's screen | **Cancel and reissue**, which is what the code already does and leaves a cleaner trail |
| **OQ-11** | Where does `prototype-v8.html` live? | Whoever ran the designer | the parity check | Publish v8 beside v7. **A contract nobody can open cannot be checked** |

**Not asked, deliberately** (they would not change what gets built): whether the notice text
needs its own version history (the settings `Version` row is enough — `01c` S1), and whether
the joiner is told when the document clock deletes a file (HR only is the smaller surface —
`01c` S3).

---

## 20 · Assumptions

- **[ASSUMPTION]** `prototype-v8.html` is `prototype-v7.html` plus the password card moving
  into the right column. Everything in §16 is read from v7 (OQ-11).
- **[ASSUMPTION]** `full_name` stays outside the tick (OQ-3, AC-104).
- **[ASSUMPTION — UNVERIFIED]** `System Settings.allow_login_using_mobile_number` is the
  field's name and it resolves against `User.mobile_no`. Frappe's source is not in this
  worktree.
- **[ASSUMPTION — UNVERIFIED]** Frappe accepts `joiner-<hash>@joiner.invalid` as a `User`
  name and email. If its validation refuses a reserved TLD, use the site's own domain with
  no mailbox behind it. **The requirement is "not routable", not the exact string.**
- **[ASSUMPTION]** One joiner account maps to exactly one submission row, enforced by making
  `user` unique. Nothing in the design asks for two.
- **[ASSUMPTION]** The Aadhaar type is uploaded at most a handful of times per row, so one
  `masked_with` field holding the distinct versions used is enough for the affected-record
  query.
- **Hypothesis, not a fact:** `tabVersion` holds the joiner's values after an erasure today.
  `track_changes: 1` is confirmed and nothing opts out, but **nobody has run the query**
  (AC-94, ⚠ C7).

---

## 21 · Subtract pass — what I deleted before handing this over

Read back once, asking only *what can I delete and still meet the requirement?*

**Removed:**

- **An unmasked, bytes-included export** (079-SEC-6 clause 3). Nobody has reported the case
  it serves, and HR can send the files from the row.
- **A record that HR read a submission.** No ruling asks for it; `01c` §12 explicitly does
  not require it; the window it would cover is 30 days.
- **An email or SMS channel for the credential.** HR hands it over however they already do.
- **A joiner-facing "the employer has not set a retention period" screen.** Replaced by
  blocking HR's invite — the problem moves to the person who can fix it.
- **A fourth endpoint to serve the masked copy back.** The upload's own reply carries it.
- **A pre-warning for the document clock** (a second setting and a second stamp field) —
  demoted to OQ-6 with a recommendation.
- **A server-side "required fields" list of ours.** Decision 2 forbids it, and so does 078's
  AC-110c; the only required list is HR's.
- **A fifth CI gate** for the route allow-list. The door table rides in the slice's own test
  module; four gates that fail honestly beat five nobody reads.
- **A "welcome back" page, a navigation, a consent tick, an Aadhaar wizard, a fourth "use a
  different document" button, a forced password change, a "change my password" link, a
  manual HR review queue for refused uploads, a confidence score stored on the row, a second
  OCR engine, a queue or retry for the masking, and a thumbnail of the masked card** — all
  already deleted by `01b` §11 and `01c` §17, and **none of them crept back in here**.
- **A new DocType, a new page, a new workspace and a new scheduled job.** There is one
  scheduled job and it gains one pass.
- **A per-screen criterion for every prototype state.** 66 states; the criteria cover the
  **behaviour**, and §16 covers the drawing.
- **`web_form_request`, the `Web Form` anchor, `_web_form()`, `_drop_request`, the token's
  fragment handling and 078-SEC-19** — the single largest subtraction, and the login made it
  free. **Net public surface: one page and three guest endpoints become zero of each.**

**Kept against my own instinct, and said out loud:** 079-SEC-7's demand that the
`ignore_permissions` count **go down**. It is not strictly a requirement of anything a user
can see, and it is the only way to tell whether the rewrite actually used the session instead
of keeping a Guest-shaped design behind a login.

---

## 22 · Ready check — Definition of Ready

| Item | State |
|---|---|
| The brief is approved | **Partly.** 078's brief covers this half; **there is no 079 brief** (§0.3). The decisions file is dated, settled and signed, and I treated it as the brief |
| The design is approved, with a clickable prototype | **Yes for the design** (Surbhi, 1 Nov). **No for the prototype at the named path** — v8 is missing, v7 read instead (OQ-11) |
| `01c` security and privacy requirements exist | **Yes.** 8 SEC, 6 PRIV, plus 078's surviving items, all traced in §18 |
| `07` DevOps requirements exist | **No.** 078's OPS rows carried; **the masker has no DevOps input at all** (OPS-M1) |
| Stories are INVEST-sized and estimated | Yes. 25 stories, 83 points, one 8 with its reason (§8.3) |
| Every story has testable criteria with an observable oracle | Yes. 118 criteria, AC-1 to AC-118 |
| Permissions are specified per persona, with the Frappe door named | Yes, §7, and the eleven negative cases |
| Compliance impact is assessed | Yes, §17. **Seven open compliance questions, two of which gate the masker** |
| No open question blocks a start | **Three do: OQ-1, OQ-2 and OQ-4 (⚠ S1, ⚠ S3, ⚠ S2).** OQ-4 blocks only US-11 and US-12 |

**So: this slice is ready to build, except for the Aadhaar masker.**

**US-1 to US-10 and US-13 to US-25 are ready** once Surbhi answers OQ-1 and OQ-2, which are
one-line answers. **US-11 and US-12 are not ready**, and the reason is not our work — it is
that the two questions which decide whether the masker is legal and whether digit-masking is
even sufficient have not been put to counsel yet. **Building them first would be the most
expensive guess in this slice.**

