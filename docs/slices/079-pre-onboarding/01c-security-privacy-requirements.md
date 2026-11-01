---
slice: 079-pre-onboarding
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-11-01
status: draft for the business analyst. Recommendations only — Surbhi decides. I approve nothing.
supersedes: docs/slices/078-positions-faces/01c-security-privacy-requirements.md §§5-7 and its 31 Oct 2026 addendum (A1-A12), for the pre-onboarding half only
inputs:
  - 079/00-decisions.md (Surbhi, 1 Nov 2026 — givens, not questions)
  - 078/01c-security-privacy-requirements.md and its 31 Oct addendum (mine)
  - 078/06-security-review.md (mine)
  - counsel's nine rulings of 31 Oct 2026, as listed in 00-decisions.md §7 — I have NOT read the written advice
  - code read in this worktree on 1 Nov 2026, file:line cited throughout. I ran nothing.
  - .claude/context/security-compliance-baseline.md (verified 24 Aug 2026 — 69 days old, inside the 90-day window; it goes stale on 22 Nov 2026)
---

# 079 · Security and privacy requirements — the restricted login

## 0 · For Surbhi, first: is this safer than the link?

**Yes, in the place that mattered, and it moves the risk somewhere new.**

The link design's worst property was that **we could not tell the right holder from the
wrong one**. A forwarded WhatsApp message was a valid credential, and a misuse left no
trace we could read. The login fixes exactly that: every opening of the form is an
identified account with a timestamp, it can be switched off in one click, and the
clear-text key problem disappears because there is no key.

**What it moves, and what you are buying instead:**

| | The link | The restricted login |
|---|---|---|
| Who can open it | whoever holds the URL | whoever holds **two** strings, in an account we can disable |
| Can we see misuse | **No.** Right and wrong holder look identical | **Mostly yes** — each sign-in is an attributable event *(Inference — see §16)* |
| Worst case if the credential leaks | one joiner's form | the same one joiner's form — **provided §7's one-page gate is built** |
| New risk the link did not have | — | **an account inside our site.** Typed addresses, a password-reset path, a session that outlives the form, and an account nobody removes |
| New personal data | none | **a `User` row** with the joiner's name, which erasure must now also delete |

### 0.1 · The load-bearing control of this slice

**There is one.** The product's own routing sends a login with **no Employee record** to the
staff portal: `auth.home_page_for` falls through to `_portal_home_for` → `/hrms-employee`
(`alvoraa_portal/alvoraa_portal/auth.py:47-52, 441-451`), and
`www/hrms_employee.py:get_context:9-11` refuses **only Guest**. So a joiner account, as the
code stands today, types `/` and lands in the employee portal shell. *Verified in code,
1 Nov 2026, and confirmed independently by the coordinator.*

**079-SEC-3, the one-page gate, is what makes the login decision safe.** It is not one item
in a list of seven. Without it the login design is **wider** than the link design, not
narrower — a bearer link at least reached only one page. Read §7's 079-SEC-3 before any
other requirement in this document, and if one thing in this slice is reviewed properly, it
should be that gate and its fail-closed clause.

### 0.2 · The most important defect, and it is not an incident

The submission doctype has `track_changes: 1` (`alvoraa_joiner_submission.json:233`,
confirmed by the coordinator) and `erase()` saves the row with no `ignore_version`
(`alvoraa_joiner_submission.py:138-141`). So every value the joiner typed is almost
certainly still in `tabVersion` **after** we have told them it was erased. If that is true,
both retention clocks are decorative.

**Nothing is exposed today.** The form ships off at every tenant, no joiner has ever
submitted anything, and so there are no rows and no residue. **This is a build defect to
close before switch-on, not an incident, and nobody needs to be told anything.** It is the
first thing I would check, and one query settles it — **079-PRIV-2**, question **M1**.

### 0.3 · Aadhaar: Surbhi has decided, against my recommendation

**Her decision, 1 Nov 2026 (`00-decisions.md` §6a): we accept an Aadhaar image and black
out the first 8 digits ourselves.** She was shown the alternatives and the failure mode and
chose this. **It is settled and this document implements it.** My objection is preserved in
079-PRIV-4, not deleted, because somebody will read this in a year.

Her rule — **mask or refuse** — is written in as a hard requirement, and it carries three
consequences the build has to accept, all of them in 079-PRIV-4:

1. **The masking is synchronous and inline.** No queue, no background job, no retry — all
   three would mean storing the original first, which the rule forbids.
2. **There is no going back.** Because we never keep the original, a masking rule later
   found wrong **cannot be re-run**. The only remedies are purge and re-ask — 079-PRIV-6.
3. **One thing I have to raise before anybody builds this, and it is new:** masking the
   printed digits may not be enough, because an Aadhaar card also carries a **QR code**, and
   I do not know whether the version on a given card holds the full number. If it does,
   digit-masking alone leaves the identifier machine-readable on the stored image. See
   **M5** in §13 — it does not re-open her decision, it says the job is bigger than the
   digits.

---

## 1 · What happens to 078's requirements

Read this table instead of re-reading 078. Nothing below re-opens a decision in
`00-decisions.md`.

### 1.1 Dead — delete them, do not carry them forward

| ID | Why it is dead |
|---|---|
| **078-SEC-9** · the token: hash-only, fragment, single use, retired state | **There is no token.** The whole requirement, and the recorded deviation that Frappe's `Web Form Request.key` is stored in clear, go with it |
| **078-SEC-13** · one answer for unknown / used / expired | Dead *as written* — there is no string for a stranger to probe. A narrower successor survives in altered form (§1.3) |
| **078-SEC-19** · confirm who can read `Web Form Request.key` before a statutory document type may be ticked | **Ceases to exist, and good.** It was dangerous debt: a control that depended on a clear-text credential sitting in a framework table nobody could purge. **Nothing replaces it.** When the `Web Form Request` row stops being created, R14 of the 078 addendum is closed outright rather than accepted |
| **078-SEC-14** · "no User is created by any path in this slice" | **Reversed by decision 1.** A User *is* created. The checklist answer changes and §7's 079-SEC-1 is what makes it safe |
| **078-SEC-15** · the public page hardening, *as a guest-page requirement* | The page is no longer public. The hardening itself survives in altered form (§1.3) |
| **A12 / A13 abuse cases** (the forwarded link; anyone who can read `Web Form Request`) | Both were about a bearer credential. **Gone.** §5 replaces them with the account's own abuse cases |
| **R9, R13, R14** (078 addendum §A9) | R9 and R13 were "a bearer link is unbounded and undetectable"; R14 was the clear-text key. All three retire. §15 names what replaces them |
| **Option 2's OTP, and its named trigger** | An OTP existed to bind a link to a person. The login does that by design. **Do not build an SMS channel for this.** |

### 1.2 Survive unchanged — re-verify at review, do not re-specify

`078-SEC-11` (upload: closed type list, magic bytes, ceilings, re-encode, PDF
attachment-only, never attached to `Employee`) · `078-SEC-12` **and its extension** (a
submission never becomes an `Employee`; no code copies a submission value onto one) ·
`078-SEC-17` (one candidate list, two separate ticks, both ends intersect) ·
`078-SEC-18` ("required" never widens what may be written or asked) · `078-PRIV-10`
(the page asks only what the tick names; the tick ships empty; HR-only excluded) ·
`078-PRIV-11` (the public deny rule, statutory identity number fields included) ·
`078-PRIV-12` (a required **document** is never a wall; "I'll bring it on day one") ·
`078-PRIV-13` (labels, hints, Hindi for every field **and** document type) ·
`078-PRIV-14` (one constant drives the warning, the erasure, the list view and the export) ·
`078-PRIV-7` (the form ships **off** at every tenant).

### 1.3 Survive in altered form

| Was | Becomes |
|---|---|
| **078-SEC-10** · rate limits keyed on the token (`_limited(JOINER_KEY, "web_form_request_key")`, `joiner_public.py:166, 268, 352`) | Keyed on the **signed-in user**. `field_app_limits._limited(..., "user")` already supports it (`joiner_invite.py:139` uses it). **079-SEC-4** |
| **078-SEC-13** · one answer to probing | Becomes: **one answer to a joiner whose work is finished** — sent, cancelled, expired, hired or turned down all give the same dead-page answer, and a live session gets it too. No stranger to protect; the point now is that a kept credential learns nothing. **079-SEC-5** |
| **078-SEC-15** · guest-page hardening | The page keeps `no-store`, `noindex`, `no-referrer` and inline-only assets — it still carries personal data and must not be cached or indexed — and **adds** a sign-in requirement. Guest gets the login page, not the form. **079-SEC-3** |
| **078-PRIV-6** · one retention clock, a setting, legal hold, real deletion | **Two clocks** (counsel 3 and 4), and erasure that now also reaches the `User` row and the `Version` rows. **079-PRIV-1**, **079-PRIV-2** |
| **078-PRIV-8** · our notice, before the first question, with the tenant's numbers and contact | Shape kept; the **words become the employer's** (counsel 6). **079-PRIV-3** |
| **078-SEC-16** · no new `ignore_permissions` | Stronger: the count in `joiner_public.py` must **go down**, because four of its five bypasses exist only because the caller was Guest. **079-SEC-7** |

---

## 2 · Threat model, four lines

**Who would want this, and what is the cheapest way to get it?** Still not an outsider.
In order of likelihood: **the joiner themselves**, poking at the one address they have been
given, because they are the only person in the system with a credential and no stake in our
rules; **somebody the joiner shares the credential with** (a relative filling the form for a
frontline worker — this will happen, and it is not malicious); **a rejected candidate
holding a credential nobody revoked**; and **a curious HR colleague** who can read every
submission in Desk today. The cheapest route for all four is a normal screen.

**Blast radius of one mistake.** One joiner's record and one joiner's identity documents —
**unless 079-SEC-3 is missing or fails open**, in which case the radius becomes *whatever
the employee portal answers to a login with no Employee record*, which is a question nobody
has asked. No path here crosses a tenant: the account is a site-local `User`. **So: one
person normally, one tenant's portal surface if the gate is wrong, never cross-tenant.**

**What this makes possible that was impossible before.** (a) **An account inside the site
for somebody who is not an employee** — new in this product's history. (b) A `User` row
holding a non-employee's name, which is new personal data in a new table. (c) A session
that can outlive the purpose it was created for. (d) A credential we may have to deliver by
email, which the link design also had. (e) **New since Surbhi's §6a decision: our code now
reads an identity document and alters it** — a native image parser on attacker-chosen input
(079-SEC-8), and the only thing in this slice whose worst case is the site rather than one
person. **No new outbound flow, no automation of a decision about a person, and no model
path** — 078-PRIV-3's refusal still holds, and the masker draws no inference about anybody:
it finds digits and covers them.

**How would we find out?** Better than before, and that is the design's real prize: a
sign-in is an attributable event with a time and an address, so "the same account opened
this form from two places" is answerable in a way "somebody forwarded a link" never was.
*(Inference — I have not read Frappe's login-logging code; §16. 079-SEC-1's test pins it, so
if the trail does not exist the build goes red rather than the claim going quiet.)* What we
still would not find out: that HR read a submission (§12), and that a credential was
shared with the joiner's own consent.

---

## 3 · Data inventory — the delta only

078's inventory stands for the photograph, the Positions fields and the documents. What
changes:

| Data | Class | Purpose | Retention | Who may see it |
|---|---|---|---|---|
| **The joiner's `User` row** — login id, first name (their name), roles, enabled flag | **Personal.** New table, new copy | The only way to open one page | **Deleted with the submission** (079-PRIV-2). Never outlives it | System Manager. Nobody else needs a joiner in a user list |
| **The first credential** | **Restricted** (it opens a Restricted payload) | One person, one form | Never stored in clear; dies with the account | HR sees it once, at issue. Nobody after that |
| **The session** | Personal (it is a credential) | Keep the form open while they fill it | Killed at every terminal state, not left to expire | — |
| The submission row and its uploads | unchanged from 078 | unchanged | **Two clocks now** — §8 | HR roles, scoped; **not** the joiner after sending |
| **`tabVersion` rows for the submission** | **Personal, and currently invisible** | None. A side effect of `track_changes: 1` | **Must be deleted by erasure** (079-PRIV-2) | Unknown — I could not check who may read `Version` (§16) |
| **A masked Aadhaar image** | **Restricted.** Masking the first 8 digits does not declassify it: the last four digits, the name, the address, the photograph and the QR survive by design | HR's verification before day one | **The document clock, 30 days** — and now for two reasons (079-PRIV-1, §9.1) | HR roles, scoped. **There is no unmasked copy at any permission level** |
| **The unmasked Aadhaar image, in a worker's memory** | **Restricted**, and the most sensitive thing this product has ever held | To be masked, and nothing else | **Milliseconds. It never reaches disk, a temporary file, a log or an error row** (079-PRIV-4 clause 1) | Nobody. Not HR, not us |
| **The masker and engine versions on a stored file** | Ordinary | To answer "which rule masked this" when the rule turns out to be wrong | With the file | HR Manager, System Manager |
| The **employer's notice text** | Ordinary, but **legally load-bearing** | Counsel 6 | Kept with the tenant's settings | Everyone; it is the notice |

**The point of this table in one line:** the login did not reduce what we hold. It added
two rows — a `User` and a session — and reminded us of a third we were already keeping by
accident.

---

## 4 · Access intent, including who must NOT see what

The analyst builds the permission matrix from this. The "must NOT" column is where the
tests are.

| Actor | Must see | **Must NOT see or reach** |
|---|---|---|
| **A joiner account**, before sending | `/joiner` and the three endpoints that serve it, for **its own** submission only; `/logout`; the assets that page needs | **Everything else in the product.** `/hrms-employee`, `/goals-portal`, `/vendor-portal`, `/driver-portal`, `/checkin`, `/alvoraa-admin`, `/app`, `/api/method/<anything else>`, and `"/"` carrying any `cmd`. Also: any other submission, any employee, any count, any list, any report, any file not their own |
| **A joiner account**, after sending, cancelling, expiring, being hired or being turned down | The dead-page answer, once, if they still have a session | **The form, their own answers, and the fact that anything changed.** No "you were turned down" disclosure through a different answer |
| **HR Manager / HR User** | Submissions and their files, in their own scope; the logged export | **An unmasked bulk export** (counsel 9 — 079-SEC-6). HR User keeps read only |
| **System Manager** | Everything, including the bytes-included export, **logged every time** | — |
| **An ordinary employee, a manager, Guest** | Nothing at all. `/joiner` as Guest gives the sign-in page | Any submission, any joiner account, any credential |
| **The hired person's own staff login, on day one** | Their employee portal | **The joiner role.** The joiner account is never promoted into the staff login (079-SEC-5) |

**The asymmetry to state out loud:** the joiner can see what they typed only until they
press Send. After that the only route to their own data is to ask the employer, who has
`export_submission` and `purge_submission`. Counsel designed it that way (no self-service
portal needed, ruling 8) — but the notice must say so plainly, because a person with a
login reasonably expects to be able to sign back in and look (079-PRIV-3).

---

## 5 · Abuse cases

Each one as *this actor, in this state, calling this path, sees this data.*

| # | Actor and state | Path | What they get **without** the requirement | Stopped by |
|---|---|---|---|---|
| **J1** | **A joiner**, signed in, curious | types `/` or `/hrms-employee` | The employee portal shell. `home_page_for` sends any login with no Employee row to `_portal_home_for` (`auth.py:47-52`), `hrms_employee.py:9-11` refuses only Guest, and `hr_api.get_portal_context:311-350` answers a logged-in non-employee with `type: "employee"`, `employee: None`. **What the rest of the portal's endpoints answer to that session, nobody has audited** | **079-SEC-3** — a fail-closed allow-list, one mechanism, not an audit of every endpoint |
| **J2** | **A joiner**, signed in | `POST /` with `cmd=<any method>` | The same reach by the door a path check cannot see. This product has already paid for that lesson once: a website page's `frappe.call` posts to `/` with `cmd` (`auth.py:252-262`, and the 29 Oct incident recorded there) | **079-SEC-3** must check `form_dict.cmd`, and **only on `"/"`** — honouring `cmd` on any other path hands over the key, as `auth.py:316-324` already explains |
| **J3** | **A joiner**, signed in | `/api/method/frappe.client.get_list` on `Alvoraa Joiner Submission`, `Employee`, `User` | Nothing, if the role carries no read anywhere. **A role that appears in any doctype's permission JSON is created by Frappe with desk access on** — `announcements.py:565-578` names exactly that trap | **079-SEC-1** — one role, `desk_access = 0`, **zero permission rows anywhere**; the row is reached by server code, not by the joiner's own permissions |
| **J4** | **Two joiners**, if HR issues one password to a batch | the sign-in page | Joiner A signs in as joiner B and reads B's prefilled name and whatever B typed. This is **ALV-242 again** — the fault that exists today because HR hands one password to a whole batch (`auth.py:164-176`) | **079-SEC-2** — one random credential per account, generated by the server, never chosen or reused by HR |
| **J5** | **A rejected candidate**, three weeks later, credential still in their messages | the sign-in page | A live session into our site, and the form again | **079-SEC-5** — terminal state disables the account, strips its role, clears its sessions; the page refuses on status as well |
| **J6** | **Anyone with the joiner's login id** | `/api/method/frappe.core.doctype.user.user.reset_password` (Frappe's own, guest-allowed) | A password-reset mail to the joiner's mailbox, i.e. a route back in that nobody designed, plus — on stock Frappe — a different answer for a known and an unknown address | **079-SEC-1** — the login id is **not a routable address**, so there is no mailbox to mail and no real email to enumerate. *(Frappe's exact behaviour here is Unknown — §16.)* |
| **J7** | **A relative**, filling the form for a frontline joiner with their blessing | the form | Everything. **Nothing prevents this and nothing should**: it is the same person's data, given by their chosen hand | Not a finding. Named so nobody builds an identity check for it, and so the notice does not claim we know who typed |
| **J8** | **An HR Manager** | Desk list view → Export, or Report Builder | Every joiner's name, mobile, personal email, home address and emergency contact as a spreadsheet, **unlogged**. Verified: the doctype grants `export: 1, report: 1` to HR Manager | **079-SEC-6** — counsel's ruling 9 makes this mandatory, not optional |
| **J9** | **The hired person**, day one, if HR reuses the joiner account as their staff login | the portal | Nothing — worse, **they are locked out**, because 079-SEC-3's gate would still see the joiner role | **079-SEC-5** — the account is never promoted. A deliberate failure mode worth a test |
| **J10** | **Anybody reading the database after an erasure** — a support engineer, a backup, a Desk timeline | `tabVersion` | The mobile number, personal email, home address and emergency contact we told the person we had deleted. `track_changes: 1` + `erase()` saving without `ignore_version` | **079-PRIV-2** |

---

## 6 · Re-answering the HR-only question — **still excluded, for a different reason**

Surbhi flagged this in `00-decisions.md` §5 and asked me not to inherit my own instinct. So
I worked it again from the code.

**My 31 October sentence is now wrong as written.** I wrote: *"there is no permission level
on a page opened without a login."* The joiner has a login, so `has_permlevel_access_to`
would return an answer. **That reason is dead and should not be quoted again.**

**Three reasons replace it, and the first is stronger than the one it replaces.**

1. **The joiner holds no write right on `Employee` at any level, so no permission
   mechanism can ever license them to supply an HR-only value.** 078-SEC-7's control is
   `candidate constant ∩ has_permlevel_access_to(write)` (`people_fields.py:17-24`,
   `my_profile.py:123-131`). Run that intersection for a joiner account and it returns the
   **empty set** — they have no write on `Employee` at level 0 either. So the intersection
   cannot admit an HR-only field; it can only refuse everything. Admitting one would mean
   writing a **hard-coded exception for the least-trusted principal in the system**. That
   is not widening a list, it is a bypass — the same conclusion as before, now on ground
   that does not move when the login arrives.
2. **The submission doctype launders permission levels, and this is the part the login
   makes worse, not better.** The joiner never writes `Employee`; they write
   `Alvoraa Joiner Submission`, whose columns are plain fields with **no permlevel at all**
   (read in the doctype JSON on 1 Nov 2026: no field carries a `permlevel`). So a field
   locked at level 1 on `Employee` arrives at level 0 on the submission, and nothing in the
   framework notices the demotion. Now that the joiner is an identified account rather than
   an anonymous one, a value in that column reads as *attributable* — which makes the
   temptation to copy it onto the Employee record **higher**, not lower. 078-SEC-12's
   extension (no code ever copies a submission value onto an `Employee`) is therefore more
   important after this change, not less.
3. **Provenance, unchanged.** "HR-only" means *HR's record of the person, not the person's
   own claim*. A login proves which account typed it. It does not make the claim checked.
   A value typed by the subject landing in a column HR is relied upon to have verified
   destroys the difference between *claimed* and *checked*, and that difference is what
   defends HR in a grievance a year later.

**Conclusion: HR-only fields stay excluded, and `078-PRIV-10a` carries forward unchanged.**
Surbhi's instinct was right; the wording of the reason was not. **Rewrite the reason in the
spec as (1) above** — "a joiner holds no write right at any level" — because the old
sentence invites somebody to re-open this the moment they notice there is a session.

*Second pair of eyes asked for:* I wrote the requirement I am re-affirming. Reason (2) is
an argument, not a measurement, and the reviewer should test it by asking the engineer to
confirm no `permlevel` exists on the submission's fields.

---

## 7 · SEC requirements

Rule ids written into security logs use the slice-qualified form **`079-SEC-n`**.

### 079-SEC-1 · The joiner account's shape, and the doors it is not allowed to have

One account per invited joiner, created only by HR's existing `invite_joiner` path
(`joiner_invite.py:138-186`). Every clause below is a door we are deliberately not opening:

1. **`user_type = "Website User"`**, never `System User`. Two reasons, both checkable:
   Frappe sends a System User to the desk, and **`usage.py:104-106` counts enabled System
   Users as seats** — so a System User joiner is a billable seat, which decision 1 exists
   to avoid.
2. **Exactly one role**, created by us with **`desk_access = 0`**, following
   `announcements.make_role` (`announcements.py:565-578`) — *including its warning*: Frappe
   creates a role **with desk access** the first time it meets it in a doctype's permission
   rows, so **the joiner role must appear in no doctype's permissions at all**.
3. **No permission rows anywhere.** The role grants read on nothing. The joiner's own row
   is reached by server code bound to their session, not by their permissions. This is what
   makes J3 impossible rather than merely unlikely.
4. **The login id is not a routable address** — an opaque per-invite identifier, not the
   joiner's email. This closes three things at once: Frappe's guest-allowed
   `reset_password` has no mailbox to mail (J6); the login page stops being an oracle for
   whether a real person's email exists; and a future staff login on the person's real
   email cannot collide with a leftover joiner account (J9). The joiner's personal email
   stays a **field on the submission**, where erasure already reaches it.
5. **`send_welcome_email = 0`**, as `tenant_setup._make_user:34-37` already does. Frappe's
   welcome mail carries a password link, and it does not belong in a stranger's inbox by
   accident.
6. **No self sign-up.** Only `invite_joiner` creates one of these. `Website Settings.
   disable_signup` stays as it is, and we add nothing that creates a User from a public
   call.

*Test:* assert the created `User` has `user_type = "Website User"`, `enabled = 1`, exactly
one role, and that the role has `desk_access = 0`; a static test asserting the role name
appears in **no** doctype permission row in either app; assert the seat count does not move;
assert the login id matches the opaque pattern and equals nothing the joiner typed;
**assert a sign-in by the account leaves an attributable log row** — this is the test that
turns §2's "how would we find out" from an inference into a fact, and if it fails, the
detection claim comes out of this document.

### 079-SEC-2 · The first credential: one per person, from the server, shown once

- **Generated by the server**, per account, with `frappe.generate_hash` or `secrets` — the
  same shape as `Alvoraa App Invite`, whose reasoning is already written down
  (`alvoraa_app_invite.py:1-26`).
- **HR never types it, never chooses it, and never reuses one.** This is the whole of J4.
  The batch-password fault (ALV-242) is live in this product today, and a joiner population
  is exactly where it would be repeated.
- **Returned once**, by the call that makes the invite, exactly as `invite_joiner` already
  returns its link once and stores nothing readable back (`joiner_invite.py:176-186`).
- **Never stored in clear and never logged.** Frappe's password store is the only copy.
  `joiner_invite.py:181` already logs the row and the actor and never the secret — keep that
  line as it is.
- **It expires with the invite** (`alvoraa_joiner_link_days`, default 7, `settings.py:150`),
  and the daily job that already expires links disables the account at the same moment
  (`joiner_housekeeping.expire_the_dead_links:181-209`).
- **The joiner is not asked to choose a password.** Said deliberately: a password they
  choose is a lasting secret for an account we are about to delete, and it would drag in
  `lock_until_password_chosen`, which keys on `frappe.db.exists("Employee", {"user_id":
  user})` (`auth.py:345-347`) and therefore does not cover a joiner at all. One short-lived
  credential, no reset path, no second secret.

*Test:* two invites produce two different credentials; the credential appears in no log, no
`Version` row and no field on either row; after the link days have passed the account
cannot sign in; assert `lock_until_password_chosen` is **not** engaged for a joiner account,
so nobody later "fixes" a redirect that would strand them on `/update-password`.

### 079-SEC-3 · One page and nothing else — fail **closed**

**The single most important requirement in this slice.** A joiner session may reach only:
`/joiner`, the three endpoints that serve it, `/logout`, `/login`, `/alvoraa-login`,
`/assets/`, `/favicon.ico` — and, on `"/"` **only**, the `cmd` values those endpoints use.
Everything else is refused: a page request gets a redirect to `/joiner`, an `/api/` call
gets a `PermissionError`.

- **Mechanism: the shape that already exists.** `auth.lock_until_password_chosen`
  (`auth.py:296-360`) is this control, built and paid for: an allow-list of paths, a second
  allow-list of `cmd` values honoured only on `"/"`, and an order that keeps the cheap
  checks first and the database last. **Copy its shape; do not invent a second mechanism.**
  Rung on the ladder: **3 · customisation** of a pattern already in the file. Rung 1
  (framework only) is rejected because Frappe has no "this role may reach one page" switch —
  `Role.home_page` decides a landing, not a boundary. Rung 5 (a per-route permission
  DocType) buys a permission surface and a migration for a list of eight strings.
- **It fails CLOSED**, and this is the one place it differs from its ancestor.
  `lock_until_password_chosen` fails open on purpose, because locking 441 staff out at shift
  change is worse than the hole it closes (`auth.py:302-306, 350-359`). The joiner gate is
  the opposite trade: a false denial costs **one** person a support call; a false allow puts
  an unidentified account inside the portal. **If the gate raises, the joiner is refused.**
- **`home_page_for` must answer `/joiner` for a joiner account**, before it reaches
  `_portal_home_for` (`auth.py:47-52`). One branch, in the one function three doors already
  share — which is why that function exists (`auth.py:20-34`).
- **`/joiner` requires a session.** Guest gets the sign-in page, the way
  `hrms_employee.py:9-11` already redirects. The page keeps every 078-SEC-15 header —
  `no-store`, `noindex, nofollow`, `no-referrer`, inline-only assets — because it still
  carries personal data. **And those headers must stop being set inside a silent
  `except Exception: pass`** (`www/joiner.py:48-53`): that was finding F5 of the 078 review,
  and it is now on an authenticated page carrying one person's identity documents.

*Test:* a table test, one row per door, as a **joiner session**: `/`, `/hrms-employee`,
`/goals-portal`, `/vendor-portal`, `/driver-portal`, `/checkin`, `/alvoraa-admin`, `/app`,
`/api/method/frappe.client.get_list`, `/api/method/frappe.client.get`,
`/api/method/alvoraa_portal.hr_api.get_portal_context`, and **`POST /` with
`cmd=frappe.client.get_list`** — every one refused, and the refusal naming nothing. Then:
the three joiner endpoints succeed; a forced exception inside the gate **refuses** (the
fail-closed test, which is the inverse of `test_it_fails_open` and must not be copied from
it); and Guest on `/joiner` gets the sign-in page, not the form.

### 079-SEC-4 · The endpoints trust the session, and take no identifier

The three endpoints lose `web_form_request_key` and resolve the submission **from
`frappe.session.user`**. The property that made `joiner_public.py` safe must survive the
rewrite, and it is written in its own docstring: *"there is no submission argument anywhere
in this module — so there is nothing a caller can post that reaches a row other than their
own"* (`joiner_public.py:103-108`). **Keep that literally true.** One joiner account maps to
exactly one submission row; the mapping is stored on the row, never passed in.

- `allow_guest` comes **off** all three. After this slice pre-onboarding adds **zero** guest
  endpoints, which is a reduction in public surface — assert it, so the enumeration test
  that pinned three now pins zero.
- **The limits re-key onto the user**: `_limited(JOINER_KEY, "user")`, the form
  `joiner_invite.py:139` already uses. Same windows, same `__alvoraa_limit__` table test.
- The ordering inside `upload_invite_file` does not change: session, then ticked type, then
  count and running total, then string length **before** decode, then strict base64, then
  magic bytes, then re-encode (`joiner_public.py:352-452`). None of that was about the token.

*Test:* a joiner session calling any endpoint with another submission's name in **any**
argument gets its own row or a refusal, never the other row — plus a static test asserting
no function in the module takes a submission, row or name argument; the registry test
asserts **no** `allow_guest` endpoint in the joiner modules; the `__alvoraa_limit__` table
test asserts each endpoint is keyed on `user`.

### 079-SEC-5 · The account's end — five ways in, one answer out

The account must die at **every** terminal state, and "die" means all four of these in one
transaction: `enabled = 0`, the role removed, the session cleared, and the credential
invalidated.

| The day | What happens to the account |
|---|---|
| They press **Send** | dies immediately. Decision 4 says they may come back **until** they send — not after |
| HR **cancels** the invite | dies (`cancel_invite`, `joiner_invite.py:189-205`) |
| The link **expires** | dies (`expire_the_dead_links`, `joiner_housekeeping.py:181-209`) |
| They are **hired** | dies. **It is never promoted into the staff login** — J9. HR's own account script creates the employee's login, as it does today |
| They are **turned down** | dies, at the moment HR records it, not at the next job run |

- **Sessions must be cleared explicitly**, not left to expire. Do not change
  `System Settings.session_expiry`: it is site-wide and would alter every member of staff's
  day. *(Whether Frappe invalidates a live session the moment `enabled` goes to 0 is Unknown
  to me — §16 — which is exactly why the clearing is explicit rather than assumed.)*
- **One answer out.** A session that survives anyway reaches the dead-page wording
  `_gone()` already carries (`joiner_public.py:112-118`), and **the same wording for every
  terminal state** — sent, cancelled, expired, hired and turned down. A different answer for
  "turned down" would tell a candidate the outcome through a page instead of from the
  employer.
- The account row itself is **deleted with the submission** — 079-PRIV-2.

*Test:* for each of the five states, assert `enabled = 0`, no roles, no session, and that a
request on a session captured **before** the change is refused; assert the hired path leaves
the employee's new staff login without the joiner role; assert all five produce the same
page answer, byte for byte.

### 079-SEC-6 · Export: counsel's ruling 9, enforced by a permission row

1. **HR Manager loses `export` and `report`** on `Alvoraa Joiner Submission`. Verified in
   the doctype JSON today: System Manager and HR Manager both hold `report: 1, export: 1`,
   and HR User holds `report: 1`. This is 078 finding F3, and ruling 9 converts it from
   "accept in writing" to a requirement. HR keeps the purpose-built button, which is already
   logged (`export_submission`, `joiner_invite.py:237-272`).
2. **Masked by default.** HR's export lists files **by name and date, without their bytes** —
   which `export_submission` already does, for the right reason, written in its own
   docstring. That becomes the mandated default rather than a choice.
3. **The unmasked export — bytes included — is System Manager only**, and is the only thing
   in this slice that reads "super-admin". It does not exist today. Build it only if HR
   genuinely needs to hand a candidate their own documents back, which is the one case
   ruling 8 names; otherwise HR sends the files from the row and that is logged by the read,
   not by an export.
4. **Every export writes a log line**, from the endpoint, with the row, the actor, the time
   and whether it was masked. Never a field value, never a file.

*Test:* assert the doctype JSON grants no `export` and no `report` to HR Manager or HR User
(a permission-row assertion, so an upgrade that re-widens it goes red); an HR Manager
calling Frappe's own report-view export for the doctype is refused; a table test over every
export endpoint asserts exactly one log line per call, so a fourth export cannot be added
without one; the masked export contains no file bytes.

### 079-SEC-7 · The `ignore_permissions` count goes **down**

`joiner_public.py` holds five bypasses against a ceiling of four — 078 finding F1, the
Blocker. **Four of the five exist only because the caller was Guest** and held no permission
on `File` or on the submission. With a session and a bound row, most should be argued away
rather than re-ceilinged.

The requirement is the direction, not a number: **the per-file ceiling in
`test_portal_security_010` for every joiner module must be lower after this slice than
before, and each remaining bypass must carry one sentence naming why the permission system
cannot do its job there.** A ceiling that merely moves sideways means the rewrite kept a
Guest-shaped design behind a login.

*Test:* the existing gate, with the ceilings lowered in the same commit. **No new CI gate.**

### 079-SEC-8 · The masking step is new attack surface, and it parses attacker-chosen images

This requirement exists because of Surbhi's Aadhaar decision. **Image parsing is where this
kind of feature gets exploited**: the input is a file chosen by the least-trusted principal
in the system, and the code that reads it is native C or C++.

**Threat model of the step itself, in four lines.**
*Who would want it:* somebody who wants code execution or a worker crash on a tenant's
server — the first genuinely technical attacker in this slice, where everyone else was a
curious colleague. *Cheapest route:* a malformed or enormous image through the one endpoint
that now hands bytes to two parsers instead of one. *Blast radius:* the web worker, and
therefore the site — **this is the only place in this slice whose worst case is worse than
one person's data.** *How we would find out:* a worker crash or a timeout in the logs, and
nothing else; there is no detection beyond that, which is why the controls are preventive.

**What the design must do:**

1. **Our own decoder first, the new one second.** Pillow is **already** a dependency
   (`employee_photo`), so decoding adds no new surface. **OCR is a new native dependency**
   and must only ever see the **normalised JPEG our own Pillow produced** — never the bytes
   the joiner sent. The attacker then controls pixels, not file structure. This is the
   single biggest reduction available and it is free: it is an ordering, not a component.
2. **Pixel-count ceiling, not only a byte ceiling.** The existing limit is on the file
   (`MAX_FILE_BYTES = 5 MB`, `joiner_public.py:78-81`). A 5 MB PNG can decode to gigabytes —
   a decompression bomb. Set `Image.MAX_IMAGE_PIXELS` explicitly and check `im.size`
   **before** any pixel work. *This gap applies to the existing photo path too; fixing it in
   the shared helper fixes both.*
3. **A hard timeout and a memory bound on the OCR call**, and a refusal when either is hit.
   An OCR pass that hangs holds a web worker; a handful of them is the site.
4. **No network, no shell string.** The engine reads a local model file. If it is invoked as
   a subprocess it is invoked with an argument list, never a shell string, and never with a
   joiner-supplied filename anywhere in it.
5. **Pin the versions.** The OCR binary and its language data are pinned in the image, and
   the pin is a DevOps item: a native parser that silently upgrades is a parser nobody
   reviewed. Record the versions with each stored file (079-PRIV-6).
6. **Rung on the ladder: 4 · new code, plus a new system package in the image.** Said out
   loud because it is the most expensive rung anything in this slice occupies, and it is
   there because Surbhi chose the only option that satisfies counsel's ruling 5. Rungs 1-3
   cannot do it: nothing in Frappe, ERPNext or our own code masks an image.

*Test:* a table of hostile inputs through the endpoint — a truncated JPEG, a PNG with a
bogus chunk length, a decompression bomb (small file, huge declared dimensions), an
animated PNG, a 0-byte file, a file that is valid base64 of random bytes — each asserted to
produce a **refusal** and no stored file, with no unhandled exception and no worker
restart; assert the pixel ceiling refuses before any decode of the pixels; assert the OCR
timeout produces a refusal rather than a hang (a stub that sleeps); assert the OCR call is
given a path or buffer our own re-encode produced, never the request's bytes — a static
test, because this is an ordering and only a reader can see it.

---

## 8 · PRIV requirements

### 079-PRIV-1 · Two clocks (counsel 3 and 4)

The build has one clock and cannot express both. This is the largest piece of work counsel's
answers create.

| Clock | Deletes | Counsel's range | Setting, shipped default |
|---|---|---|---|
| **The document clock** | **the `File` rows only** — bytes included. The row survives, minus its attachments | **30-60 days** | a new key, default at the cautious end: **30** |
| **The record clock** | the typed fields and the row's personal content, as `erase()` does today | **180-365 days** | `alvoraa_joiner_not_hired_days`, 180 (`settings.py:127`) |

- Both run from **`closed_on`**, never from `modified`, for the reason already learned and
  written down (`alvoraa_joiner_submission.py:50-58`): ticking legal hold and unticking it
  restarts a `modified` clock.
- **The backstop splits too.** `alvoraa_joiner_backstop_days` (90) catches a submission
  nobody actioned. Its **documents** must go at the document clock, whatever the row's
  state — otherwise an ignored submission keeps an identity document for 90 days against
  counsel's 30-60.
- **Legal hold wins for both**, with HR's Purge the single exception, exactly as today
  (`erase:108-115`).
- **No value of either setting means "for ever"**, and the setter keeps its range check
  (`settings.py:381-383`) — add the document clock's 30-60 range beside it.
- **Both are settings because the employer is the Data Fiduciary and we are the Processor**
  (ruling 1). Our defaults are the Processor's starting point, nothing more.
- HR is **warned before each deletion**, through the `Notification Log` the job already
  uses, naming the reference and never the person (`joiner_housekeeping.py:129-180`).

**Who enforces it:** the daily job. **Who owns the numbers:** the tenant. **Who must be able
to prove it ran:** us — and the document pass must log its **own** count, or "did the
documents actually go" has no answer.

*Test:* age one row to 31 days and assert **its files are gone and its fields are not**; age
another to 181 days and assert the fields are gone too; assert legal hold survives both;
assert an unactioned row loses its files at the document clock; assert neither setting
accepts 0, blank, or a value outside counsel's range; assert each pass logs its own count.

### 079-PRIV-2 · Erasure is complete, or it is theatre

**A Blocker-shaped requirement, covering something nobody has looked at.** When a row is
erased, nothing personal may survive anywhere:

1. **The typed fields** — `strip_personal_fields`, derived from the constant (078-PRIV-14).
   Built.
2. **The files, bytes included** — built, with `delete_permanently=True`
   (`alvoraa_joiner_submission.py:124-132`).
3. **The `Version` rows — new, and currently almost certainly broken.** The doctype carries
   `track_changes: 1` (`alvoraa_joiner_submission.json:233`); `submit_invite` saves the
   joiner's values (`joiner_public.py:330-334`) and `erase()` saves the cleared row
   (`:138-141`), neither passing `ignore_version`. *Verified in code: the flag is on and
   nothing opts out. Inference: Frappe therefore keeps the old values in `tabVersion`.*
   **Either delete those rows as part of erasure, or pass `ignore_version` on both saves.**
   My recommendation is the second **plus** a sweep for rows already written: an audit trail
   of *who issued and closed an invite* does not need the person's phone number in it.
4. **The joiner's `User` row**, with `delete_permanently=True` so Frappe's
   `Deleted Document` does not keep a JSON copy of their name. If a linked row makes the
   delete impossible, the fallback is explicit — strip the first name, strip the roles,
   disable, and **record that the row could not go**. Never leave a named user row behind
   silently.
5. **No `Email Queue` copy.** The warning is a `Notification Log` naming the reference, not
   an email naming the person — already right (`joiner_housekeeping.py:136-141`). Keep it
   that way: an email is a copy we cannot erase.

*Test:* fill **every** candidate field, attach a file, submit, let HR edit the row once, then
erase — and assert, by query: no field value in the row, no `File`, **no `Version` row
holding any of those values**, no `User` row for that account, no `Deleted Document` holding
the name, and no `Email Queue` entry. Generated from the candidate constant, so a new field
cannot escape it. **This test is the proof for counsel's rulings 3 and 4. Without it, both
clocks are claims.**

### 079-PRIV-3 · The notice is the employer's words (counsel 6)

078-PRIV-8's shape is built and proved: notice before the first question, the tenant's
configured numbers, the tenant's own contact, and it **refuses to render with no contact**
(`joiner_public.py:180-199, 216-241`). Three changes:

1. **The purpose text becomes a tenant setting**, shipped **empty**, holding the employer's
   own words: why they are asking, what they do with it, who to contact. It joins the
   access-granting keys so every change writes a `Version` row (`settings.py:187-215`).
2. **The page refuses to render without it**, exactly as it already refuses without a
   contact. That makes the notice a **precondition for switching the form on** without
   inventing a new precondition mechanism: no text, no form.
3. **The generated half stays ours and stays honest**: the itemised list of what is asked
   and why, rendered from the actual ticked lists (078-PRIV-13), the real numbers from
   **both** clocks, and three sentences the employer should not have to write — **that the
   login opens this one page and nothing else; that it stops working the moment they press
   Send; and that afterwards the way to see or delete their data is to ask the employer**
   (ruling 8). A person given a login expects to be able to sign back in and look. If we do
   not say otherwise, we have misled them.

Hindi at parity, every string through `drT()`.

*Test:* with the text unset, the page refuses and the switch cannot be turned on; with it
set, the notice carries the tenant's words, both configured numbers and no literal; assert
the three sentences about the login are present and precede the first input
(`compareDocumentPosition`, as the existing browser test does); assert a Hindi entry for
every string.

### 079-PRIV-4 · Aadhaar is accepted, and the rule is **mask or refuse** (counsel 5)

**Surbhi's decision, 1 Nov 2026, `00-decisions.md` §6a, taken against my recommendation
with the failure mode named. Settled. This requirement implements it.**

<details>
<summary>My objection, preserved — read this before changing anything here</summary>

I recommended **not accepting the image**, and offering PAN, passport, driving licence and
voter ID only. The reason was not squeamishness about work: it was that **the failure mode
of automatic masking is silently storing an unmasked identity document while telling the
person it was masked.** A refused upload is a nuisance; that is not.

The three options as put to her:

| Way to do it | What it really is | My verdict then |
|---|---|---|
| **Server-side OCR + auto-mask** | A new native dependency, finding 12 digits on a phone photograph of a laminated card, at an angle, in bad light | Rejected — the failure *is* the harm |
| **The joiner masks it themselves** | Honest, cheap and **unverifiable**. The control would read as enforced and be advisory | Rejected as a control |
| **Ask for UIDAI's own masked download** | The right artefact, but **we cannot tell a masked download from a photograph of the card** | Rejected on its own |
| **Do not offer the type** | Nothing to mask, nothing to claim, nothing to get wrong | **Recommended** |

**What changes my position from "do not build it" to "this is buildable, carefully".** Her
"mask or refuse" rule turns the failure mode inside out: the dangerous outcome
(stored-unmasked) is no longer the *default* of a failure, it is the *only* outcome the
design forbids. With clause 3 below — mask, then **read the image back** and refuse unless
the number has gone — the control is self-checking rather than trusting OCR. That is a real
answer to my objection, and it is why I can write a requirement rather than an escalation.

**What has not changed:** we will refuse some genuine Aadhaar photographs, and some users
will be annoyed. That is the trade she accepted, in writing, and the build must not quietly
soften it later to reduce support calls. **If a future change swaps a refusal for a
"store it and flag it for HR", that is a P0 at review, not a P2.**

</details>

**The rule, as five clauses. Clause 3 is the one that makes the rest believable.**

**1 · The original never reaches disk.**
- The image arrives base64 in the request body and lives only in the worker's memory, as
  today (`joiner_public.upload_invite_file:352-452`). **One `File` insert, with the masked
  bytes, and no other write of any kind** — no `save_file` of the original, no
  `NamedTemporaryFile`, no cache entry, no second `File` row, no `localStorage`
  (`joiner_public.py:38-45` already forbids the last one).
- **The raw string and the decoded bytes are dropped from `frappe.local.form_dict` as soon
  as they are decoded, and before any code that can raise.** This is a real hole, not a
  precaution: Frappe's error snapshot masks form keys containing `key`, `token`, `secret`,
  `password`, `passwd` or `pwd` — and `data` is **none of those**. So an exception anywhere
  in the masking step would write the **whole unmasked Aadhaar, base64, into an Error Log
  row**. The same mechanism was already load-bearing in the other direction for the token
  parameter (`joiner_invite.py` docstring, `joiner_public.py:21-27`).
- **Every failure path logs a code, never the payload**, and no `except` block passes the
  image, the filename or a traceback that could carry them.
- If the OCR library cannot be driven from memory and insists on a file path, the file goes
  to a **RAM-backed path** (`/dev/shm`), is unlinked in a `finally`, and that becomes a
  **recorded deviation with DevOps confirming the container provides it**. "A temporary file
  a crash could leave behind" is exactly what Surbhi's rule names.

**2 · Mask first, store second, and only ever the masked pixels.**
- **Pillow normalises before anything else.** Decode and re-encode to a plain JPEG at a
  bounded size *first* (the existing `employee_photo._reencode(blob, 1600, 82)`), **then**
  do the finding and the covering on that normalised image. The attacker then controls
  pixels, not file structure — see 079-SEC-8.
- The mask is **filled rectangles burned into the pixels**, then a final re-encode. Not an
  overlay, not an annotation, not a layer.
- **PDF is refused for this document type.** We cannot re-encode a PDF — the existing code
  says so and gives it the narrower attachment-only treatment (`joiner_public.py:344-350`) —
  and a mask drawn onto a PDF is removable. JPEG and PNG in, JPEG out.
- **Single frame only.** An animated PNG or a multi-frame image is refused: frame two can
  carry the unmasked card.
- Metadata and thumbnails go with the re-encode, as they already do, because the output is
  built from pixels with no `exif=` and no `icc_profile=` (`employee_photo._reencode:141-158`).

**3 · "With confidence" — what a test can actually assert.**

Said plainly first: **nobody can assert that this works on an arbitrary real-world
photograph, and no accuracy figure may be claimed.** What *can* be asserted is the decision
rule and the stored artefact. Four checks, all of them refusals when they fail:

| Check | Assertable as |
|---|---|
| **a · Exactly one candidate** | The normalised image yields **one** 12-digit candidate. Two candidates means we do not know which to cover → **refuse** |
| **b · The digits were read, not guessed** | Every token covering the first 8 digits is above a named per-token OCR confidence threshold, **and** the 12 digits satisfy Aadhaar's own check digit. *(The check-digit algorithm is widely described as Verhoeff — I am not stating that from memory as fact; see §16. If it holds, it converts "did OCR read this correctly" into a deterministic yes/no, which is the cheapest confidence signal available.)* Either fails → **refuse** |
| **c · The cover is real** | The rectangles are inside the image, non-degenerate, and their union covers the bounding boxes of the first 8 digit glyphs **plus a margin**. A zero-area or out-of-bounds box → **refuse** |
| **d · The read-back — the one that matters** | **After masking and before storing, read the masked image again and assert no 12-digit candidate and no 8-digit run of the covered prefix can be found.** If anything is still readable → **refuse**. This is the clause that makes the control self-checking instead of trusting the masker |
- **Any exception anywhere in a-d is a refusal.** No `except: pass`, no "store it and warn",
  no default-allow branch. The whole step is one function with one answer: *masked bytes, or
  a refusal.*
- **A measured refusal rate on a fixture corpus is reported, never a claimed accuracy.** The
  test engineer records "n of m synthetic cards were masked, k refused" so the number is
  known; it is a measurement of our fixtures, and it must not be quoted to a customer as an
  accuracy figure.

**4 · A refusal costs the joiner nothing.**
- The upload is refused **before any write**, so nothing is stored and nothing is burned. By
  construction today: `upload_invite_file` throws before the `File` insert, and the account
  dies only at Send (079-SEC-5).
- The wording follows `_bad_type`'s shape (`joiner_public.py:455-464`) — it always offers a
  way forward: **another document type, or "I will bring it on my first day"**. It must not
  say "try again with a better photo" and stop there, and it must **not** say why the image
  was refused in a way that teaches somebody how to get an unmasked one through.
- Hindi at parity. A frontline joiner reading a refusal in English only has been given a
  dead end.

**5 · What the product may and may not say.**
- The notice says, in both languages, **that Aadhaar is voluntary, which other IDs are
  accepted, and that we black out the first 8 digits before storing it.** That last sentence
  is now true, and PRIV-3 requires the notice to be true.
- **It must not claim more than clause 3 delivers.** No "securely masked", no "verified", no
  accuracy figure.
- **One masker, one entry point, and the honest limit.** The masking lives in one module
  with one public function, and **no other path may store a document of an Aadhaar-ish type
  without going through it** — enforced by the same name-pattern test. **But HR attaching an
  Aadhaar card to an `Employee` in Desk bypasses this entirely.** That is HR's own act under
  the employer's own duty, it is out of this slice, and it means **a questionnaire answer
  "we mask Aadhaar" would be false for the Desk path.** The honest answer is "we mask
  Aadhaar images collected through the pre-onboarding form". Say that, and nothing wider.
- **Alternative IDs stay offered** and stay the easier path — ruling 5's "voluntary, with
  alternatives accepted" holds whatever we build.
- **One pleasant consequence worth stating:** because the original never exists, there is no
  unmasked copy of an Aadhaar to export, at any permission level. Ruling 9's "unmasked
  exports to super-admins only" is satisfied for this document class **by construction**
  rather than by a permission row.

*Test:* for each fixture — a clean synthetic card, a skewed one, one with the number
printed twice, one with no number at all, one with two 12-digit sequences, an animated PNG,
a PDF, and an image whose check digit fails — assert the outcome is either *stored and
read-back clean* or *refused*, and **never** stored-with-a-number-readable; assert exactly
one `File` row exists after a success and **zero** after every refusal; assert the stored
file is JPEG with no EXIF; assert a refusal leaves the account live and the submission
sendable; assert the refusal wording offers the two routes out and has a Hindi entry; force
an exception inside the masker and assert **no Error Log, no Version row and no log line
contains any 64-character run of the payload**; and a static test that the masker has one
public entry point and that no other write path accepts an Aadhaar-ish type.

### 079-PRIV-5 · The login collects nothing extra, and nothing lands server-side early

- **No `Employee` record** (decision 1), and no joining date anywhere on the row —
  078-SEC-12, Met, carried forward. The absence-backfill trap and the billable seat are the
  reasons, both already logged.
- **The `User` row holds the minimum**: an opaque login id and the name HR typed. No mobile,
  no personal email, no photograph on the `User`.
- **The draft stays on the device.** Decision 4 ("they may come back") is already met by
  `localStorage`, and `joiner_public.py:38-45` already refuses to put document bytes there.
  **Do not move the draft to the server** now that there is a session to hang it on: a
  server-side draft is a half-filled personal record, written before anybody has acted on
  the notice, that both clocks would have to learn about.
- **078-PRIV-3's refusal stands**: nothing collected here is matched, scored, used to
  confirm who checked in, or sent to a model. The joiner's photograph is not check-in
  evidence, and a check-in photograph is never a joiner's.

*Test:* submitting creates no `Employee` and does not move the naming series (the existing
test); assert the `User` row carries no value the joiner typed; a static test asserting the
joiner modules write nothing to the server before the submit call, and that no joiner field
appears under any AI or model path.

### 079-PRIV-6 · When the masking is later found wrong — and it will be, at least once

**Start with the hard part: we cannot re-run the masking.** The original does not exist, by
design (079-PRIV-4 clause 1). So the familiar remedy — "fix the masker and reprocess" — is
not available here, and that is a deliberate consequence of Surbhi's rule, not an oversight.
**The only remedies are purge and re-ask, plus telling somebody.** Nobody should discover
that during an incident, so it is written here now.

**1 · Every stored masked image must be attributable to the rule that made it.** On the row
or on a small sidecar field, recorded at store time: the **masker version** (a constant
bumped on any change to the finding, covering or read-back rule), the **OCR engine and
model version**, and the **outcome** (`masked`). **Never the digits, never the boxes'
contents, never a confidence value that encodes the number.**

**2 · The affected-record query exists from day one.** One query, in code, that answers:
*which rows hold a document of an Aadhaar-ish type, masked by masker version X, not yet
erased, at this tenant?* Written and tested now, while nobody needs it. **A remedy that
starts with somebody composing SQL in an incident is not a remedy** — this is the
affected-record query the breach workbench exists to provide, and it is the cheapest part
of incident readiness in the whole slice.

**3 · The remedy, in order.**
1. **Stop the bleeding:** the Aadhaar type stops being offered — one untick, no release
   (078-PRIV-11's mechanism) — so nothing new arrives while the masker is wrong.
2. **Purge:** delete the affected `File` rows, bytes included, through the existing
   `erase`-shaped path with `delete_permanently=True`. The submission row survives, minus
   the file, and is marked as needing the document again.
3. **Re-ask**, through the ordinary route, with a new invite if the person is still live.
4. **Tell:** HR is told, with a **count and the reason**, through the `Notification Log` the
   retention job already uses — naming references, never people.

**4 · Who decides whether it is notifiable, and the clock.** **Not us.** The employer is the
Data Fiduciary (ruling 1); we are the Processor. Our duty is to tell them **promptly and
with the numbers**, and to hand over the affected-record list. Their duty is the DPDP breach
notification and, if it engages, **CERT-In's 6 hours from awareness** (baseline, verified
24 Aug 2026). **Our own awareness starts the clock for our telling them, not for our
deciding anything.** The runbook for this has **never been drilled** — R-10 — and this is
the first feature in the product whose remedy needs it.

**5 · What would *not* be a finding.** A refused upload, however many. A masker that finds
nothing on a bad photograph. A tenant choosing to stop offering Aadhaar. None of those loses
anybody's data; they cost support calls, which is the trade Surbhi accepted.

*Test:* assert every stored masked file carries a masker version and an engine version, and
that the versions come from constants rather than being typed per call; assert the
affected-record query returns exactly the rows seeded with a given masker version and
nothing else, including across two tenants' worth of fixture rows if the test site has them;
run the purge path and assert the file and its bytes are gone, the row survives, the row is
marked as needing the document, and one notification was written naming a count and no
person; assert bumping the masker version constant makes previously stored files findable by
the query **with no code change** — that is the property the remedy depends on.

---

## 9 · Counsel's nine rulings → what must be true, and who enforces it

I have **not** read the written advice; I am working from `00-decisions.md` §7. Labelled as
such, and **I am not a lawyer.**

| # | Ruling | What must be true | Requirement | Who enforces it |
|---|---|---|---|---|
| 1 | Employer is Data Fiduciary, we are Processor | Every period, every field list and the notice text are **the tenant's settings**, shipped at a cautious default or empty. No number is hard-coded | 079-PRIV-1, 079-PRIV-3, 078-PRIV-10 | the settings layer (`ACCESS_GRANTING`), with a `Version` row per change |
| 2 | A restricted login beats an expiring link | The login exists **and the restriction is real** — one page, fail closed | **079-SEC-1, 079-SEC-3** | `before_request`, the role, the account shape |
| 3 | Non-joiner's **record**: 180-365 days | The record clock, from `closed_on`, no "for ever", legal hold respected | 079-PRIV-1 | the daily job; the setter's range check |
| 4 | Non-joiner's **identity document**: 30-60 days | **A second clock** that deletes only the files, including for unactioned rows | **079-PRIV-1** | the daily job, a separate pass with its own count |
| 5 | Aadhaar voluntary, alternatives accepted, first 8 digits masked on the image | **We accept it and mask it ourselves** (Surbhi, 1 Nov). Mask or refuse; the original never reaches disk; the masked image is read back before storing; alternatives stay offered | **079-PRIV-4**, **079-SEC-8**, **079-PRIV-6** | the masker's own read-back check — not a permission, not a setting, and not an instruction |
| 6 | The notice is the employer's — purpose, periods, their HR contact | A tenant-authored notice text, shipped empty, and the page refuses to render without it | **079-PRIV-3** | the page; the switch precondition |
| 7 | An expiring link is acceptable; a one-time code is much more secure | Met by the login: a per-account server-generated credential, short-lived, no reset path, no second secret | 079-SEC-2 | `invite_joiner`; the daily expiry job |
| 8 | No public self-service portal; HR must be able to **export or purge** on request | Both exist (`export_submission`, `purge_submission`) — and **`purge_submission` is untested today** (078 D5). The notice must tell the joiner this is the route | 079-SEC-6, 079-PRIV-3 | HR's two buttons, both logged |
| 9 | Unmasked exports to super-admins only; sensitive IDs masked by default; **every export logged** | HR Manager loses `export`/`report`; bytes-included export is System Manager only; a log line per export, asserted by a table test | **079-SEC-6** | the doctype permission rows — a row, not a rule in code |

**The two heaviest, said plainly:** ruling 4 needs new code (a second clock), and **ruling 5
is now the largest single piece of work in the slice** — a native dependency, an image
pipeline, a self-check and a remedy path, because Surbhi chose the only option that actually
satisfies it.

### 9.1 · Do counsel's two outstanding written answers matter more now? **Yes, decisively.**

**I am not a lawyer.** Both questions were already open (078 ⚠ COMPLIANCE 3 and 4). Before
today they blocked *a tenant ticking a statutory document type*. **Now they block the
feature's purpose**, because we are deliberately building a thing whose job is to hold an
identity document for a person who may never be employed — and **an image of an identifier
is still the identifier, masked or not: the last four digits, the name, the address, the
photograph and the QR code all survive the masking by design.**

Three things changed, and each sharpens a question counsel has **not** been asked:

1. **We now touch the unmasked identifier ourselves.** Briefly, in memory, by design. That
   is a new fact. **Question for counsel:** *"Our customer, the employer, collects an
   Aadhaar card image. Our software reads the unmasked number in memory in order to black
   out the first eight digits, and never stores the original. Does the Aadhaar Act or any
   UIDAI regulation restrict who may handle an Aadhaar identity in that way, and does doing
   it as the employer's Processor engage any duty on us?"* **Blocks:** offering the Aadhaar
   type at a tenant with real joiners. **Not the build.**
2. **Does masking change the retention period?** Counsel's 30-60 days was for "a non-joiner's
   identity document". **Question:** *"Does the 30-60 day window apply unchanged to a
   **masked** Aadhaar image, or does masking shorten or lengthen it?"* **Fail-closed
   default:** the document clock stays at **30**, its shortest value, and that is a second
   reason for the default beyond the one in 079-PRIV-1.
3. **Is "voluntary" satisfied by the shape of the form?** We offer several types and the
   notice says Aadhaar is optional; **we record no choice**. **Question:** *"Is offering
   alternatives and saying so in the notice enough for 'voluntary', or must the joiner's
   choice be recorded?"* **Fail-closed default:** the notice says it plainly in both
   languages, and we do **not** build a consent ledger for it — if counsel wants a recorded
   choice, that is a small addition, and guessing it now would be building a compliance
   feature nobody asked for.

**And the one that is now urgent rather than pending:** 078 ⚠ COMPLIANCE 4 asked whether the
employer may ask for an Aadhaar card at all before employment. **That answer now gates a
feature we are spending the slice's biggest budget on.** If it comes back "no", the masker
is wasted work. **That is worth asking before the build starts, not after** — it is one
sentence to counsel, and it is the cheapest risk reduction available in this slice.

---

## 10 · The CI assertions — rewritten for the login and the masker

**No new CI gate, no new scanner, no new log pipeline.** The four gates that exist
(`check_scope_traps.py`, `check_api_paths.py --max 0`, the `ignore_permissions` ceiling in
`test_portal_security_010`, the demo-password check) already cover the mistakes this change
can make. These ten assertions ride in the slice's own test modules, and **every one pins a
shape rather than a number** — the property the seven link-era assertions had.

| # | Assertion | Why it is the gate |
|---|---|---|
| 1 | **The joiner candidate list *is* `MY_PROFILE_WRITE_FIELDS`**, by identity, and HR-only names are refused at the setter and ignored by the reader | Stops a third list appearing; a third list is how two lists drift apart. Carries 078 assertions 1 and the PRIV-10a half |
| 2 | **Every deny name is refused at the setter**, one table row per name, **and** each one written straight into the setting is absent from the page endpoint and stores nothing. Includes made-up statutory **field** names (`aadhaar_no`, `pan_card_number`, `uan`) so the assertion is never vacuous on a site without the India pack. **Document *types* are no longer on the deny list** — Surbhi's §6a decision allows the Aadhaar type, and assertions 9 and 10 are what guard it instead | **The one that matters.** The only half that survives a future UI. Carries 078 assertions 2 and 3. Note the deliberate asymmetry: a statutory **number as a column** stays refused; a statutory **card as a masked image** is allowed |
| 3 | **A rule set pointed at an ordinary field makes that field refused, with no code change** | Proves the live `rule_set_fields()` read rather than the static tuple |
| 4 | **Every candidate field and every offered document type has a label, a hint and a Hindi entry** | Fails the day one is added; otherwise a public page says "pan_number", and a required document nobody can read |
| 5 | **The account's shape:** Website User, one role, `desk_access = 0`, the role in no doctype's permission rows, an opaque login id, and a sign-in that leaves an attributable log row | Pins 079-SEC-1. Shapes, not counts — it does not care how many joiners exist |
| 6 | **A joiner session is refused at every door but one** — a table of paths plus `POST /` with a `cmd` — **and the gate refuses when it raises** | Pins 079-SEC-3, including the fail-closed property, which is the clause a future "make the test pass" change would quietly reverse |
| 7 | **Every terminal state ends the account**, and a session captured before the change is refused; the hired person's staff login carries no joiner role | Pins 079-SEC-5. Five rows, one assertion each |
| 8 | **Erasure leaves nothing**, generated from the candidate constant: no field, no file, no `Version` row, no `User` row, no `Deleted Document`, no `Email Queue` — and each clock deletes only what it owns | Pins 079-PRIV-1 and 079-PRIV-2, which together are the whole of counsel's rulings 3 and 4. Erasure cannot fall behind the list, and the export tick cannot outlive it |
| 9 | **Mask or refuse, as a two-column outcome table over a fixture set**: every fixture ends either *stored and read back clean* or *refused with nothing stored* — **and the table has no third column.** Plus: exactly one `File` after a success, **zero** after every refusal; a forced exception inside the masker leaves no payload in any log, `Version` row or error row | Pins 079-PRIV-4. **It pins the shape in the strongest available sense: the absence of a third outcome.** The day somebody adds "stored, flagged for HR", this test is what fails |
| 10 | **The masker is hostile-input safe and ordered correctly**: the hostile-image table refuses with no unhandled exception; the pixel ceiling bites before the pixels are read; the OCR call is handed **our own re-encoded image**, never the request's bytes; every stored masked file carries a masker and engine version; and the affected-record query finds exactly those rows | Pins 079-SEC-8 and 079-PRIV-6. The ordering clause is a static assertion because only a reader can see an ordering — and the version clause is what makes the remedy possible at all |

Plus two that are already gates and must simply not be weakened: the `ignore_permissions`
ceilings (**lower**, per 079-SEC-7) and the export permission rows (079-SEC-6), both of
which fail red when an upgrade or a merge re-widens them.

**What I removed from this list, and why:** the "joiner tick ships empty" assertion (078
assertion 7) collapses into assertion 1's reader half — a tick that ships empty is proved by
asserting the page renders no inputs with the key unset, which assertion 1 already does; and
a separate "no statutory type ticked by default" assertion collapses into assertion 2, whose
deny rule now makes it impossible rather than merely untrue. Two assertions fewer, nothing
unproved.

---

## 11 · What must exist before any of this is observable

Lesson 1 of slice 028: a rule can pass every unit test and never fire on real data. Here it
is worse, because the feature ships **off** — so an empty test run is the default outcome.

| Control | What a run shows today | What must exist |
|---|---|---|
| Everything about the form (079-SEC-3 to 6, PRIV-1 to 5) | The joiner tick ships empty and the form ships off, so every test passes against a form that asks nothing and an account that is never made | A dev tenant with the form **on**, the tick carrying **three** fields, **one non-statutory document type ticked**, one live joiner account, and **invented data only** — a made-up card image, never a real person's |
| 079-SEC-3, the one-page gate | A test that asks with a path and never with a `cmd` passes while the real door stands open. **This has happened in this codebase twice** (`auth.py:208-220, 236-262`) | A test that posts to `"/"` with a `cmd`, and a real HTTP request, not only a unit call |
| 079-PRIV-1's two clocks | A fixture that fills a few fields proves a few fields erased | A row with **every** candidate field filled **and a file attached**, aged twice — once past the document clock, once past the record clock |
| 079-PRIV-2's `Version` sweep | Nothing, unless the fixture makes HR **edit** the row after submit | An HR edit between submit and erase. Without it the `Version` assertion is vacuous |
| 079-SEC-6's export | Nothing — with the form off there are no rows to export | One submission, one HR Manager login, one attempt at Frappe's own export |
| **079-PRIV-4's masking** | **Nothing at all, and this is the nastiest fixture problem in the slice.** No card images exist, and **no real person's Aadhaar may ever be used as a fixture, on any site, at any time** | A **synthetic card generator** in the test fixtures: a drawn rectangle, the card's layout, a plausible font, and **made-up 12-digit numbers that satisfy the check digit** — plus variants (skewed, dim, number printed twice, two numbers, no number, a QR-like block). It must be generated in code, not committed as images, so nobody is ever tempted to commit a real one. **If a review finds a real Aadhaar in the fixtures or in a test site's files, that is a P0, not a tidy-up** |
| **079-SEC-8's hostile inputs** | Nothing | The hostile-image table, generated in code: truncated JPEG, bad PNG chunk, declared-huge bomb, animated PNG, 0 bytes, random base64 |

**If a test run reports "0 findings" without the first row, it has proved nothing.** That
sentence belongs in the test engineer's notes, not only here.

---

## 12 · The carried-forward defects (00-decisions §9)

| Defect | Status now | Which ruling makes it mandatory |
|---|---|---|
| **R11 — HR Manager can export submissions unmasked, and nothing is logged** | **Mandatory.** Was "accept in writing" at 078 (F3, P2) | **Ruling 9**, in terms. Becomes **079-SEC-6**: a permission row, a masked default, and a log line per export |
| **No record that HR read a submission** | **Not mandated by any ruling.** Ruling 9 is about exports, not reads | Stays **P3 debt**, honestly labelled. The cheapest close remains one `source` value on the existing `Alvoraa Photo Access Log`, which already holds "who looked at whose document, when" (078-PRIV-5, built). **I am not requiring it**, because a control nobody asked for buries the two that matter — and because inside a 30-day document clock the window it would cover is short |
| **A misused link is undetectable** | **Changes character rather than closing.** A misused *account* leaves a sign-in trail; a *shared* credential still does not, because the holder is the account | Not mandated. **079-SEC-1's log-row test** is what makes the improvement real instead of assumed. Residual risk R-5 in §15 |
| **The joiner page is English only (ALV-267)** | **Still open, and it got heavier**, because the notice is now itemised, employer-authored and carries two retention numbers — more words, on the page read by the people least likely to read English | Not a counsel ruling; it is the product's own English-Hindi parity rule for the frontline journey. 078-PRIV-13 and 079-PRIV-3 both require Hindi at parity. **Hindi parity cannot be proved in this environment** (§16) |

---

## 13 · Open questions

**Must know — these block the spec or the verdict.**

| # | Question | My reading | Why it changes a control | **Fail-closed default meanwhile** |
|---|---|---|---|---|
| **M1** | **Does `tabVersion` keep the joiner's values after erasure?** | It does: `track_changes: 1`, no `ignore_version` on either save. Inference, not run | If yes, **both retention clocks are decorative** and counsel's rulings 3 and 4 are unmet on a site that thinks they are met | Treat it as true. Build 079-PRIV-2 clause 3 and let the test prove it either way. One query settles it: `select count(*) from tabVersion where ref_doctype = 'Alvoraa Joiner Submission'` on a site where one submission has been erased |
| **M2** | **How does the first credential reach the person?** Email, or read out by HR? | Email is the only channel this product has. Emailing it puts a working credential in a mailbox — the same exposure the link had, but revocable and attributable | It decides whether 079-SEC-2 needs an email template and a mail log, or nothing at all | **HR hands it over by whatever means they already use**, and the endpoint returns it once. We build no mail path for it. If email is wanted, it is a named addition with its own review |
| **M3** | **Is the joiner expected to sign back in after sending?** | No — decision 4 says the access stays valid *until* they send | If yes, the account must survive after submit and the whole of 079-SEC-5's first row changes, as does the notice | **The account dies at Send.** The notice says so before the first question |
| **M4** | ~~Do we accept an Aadhaar image at all?~~ | **Answered by Surbhi, 1 Nov 2026: yes, and we mask it ourselves** (`00-decisions.md` §6a). **Closed. Not to be re-asked** | — | — |
| **M5** | **Does the QR code on an Aadhaar card carry the full number?** **New, and it is mine to raise rather than hers to have anticipated.** | I do not know. The newer "secure QR" is described as carrying only the last four digits; older printed QR codes are described as carrying the full number. **I will not state either from memory** | **If any version carries the full number, masking the printed digits leaves the identifier machine-readable on the stored image, and ruling 5 is not met.** It changes the masker's job from "cover 8 digits" to "cover 8 digits **and** every 2D barcode", which needs another library and more of 079-SEC-8's surface | **Cover every detected 2D barcode region as well as the digits**, and if no detection library is available, **refuse any Aadhaar image in which a QR-shaped block is found.** Fail closed, and tell Surbhi the job is bigger than the digits. *Who can settle it:* anybody with a card and a QR scanner, in five minutes — or UIDAI's own documentation |
| **M6** | **Is the 12th digit a Verhoeff check digit?** | Widely documented as such, which is why clause 3(b) leans on it. **Not verified against a primary source, and not mine to state as fact** | If it is not, clause 3(b) loses its deterministic half and "with confidence" rests on OCR confidence scores alone — weaker, and I would want the read-back threshold raised in compensation | **Implement it as one named, replaceable check**, and have the test prove it with made-up numbers. If it turns out not to hold, one function changes, not the design |

**Should know.** **S1:** does the employer's notice text need a version history, or is the
`Version` row on the settings key enough? My reading: enough — a `Version` row names who
changed it and when, which is what a grievance needs. **S2:** should HR be able to re-issue a
credential for a joiner who lost theirs, or only cancel and start again? Today the shape is
cancel-and-reissue (`cancel_invite` is terminal), which is simpler and leaves a cleaner
trail; I would keep it. **S3:** who is told when the document clock deletes a file — the
tenant's HR only, or the joiner too? Counsel did not say; HR only is the smaller surface.

**Still open and not mine to close:** 078's ⚠ COMPLIANCE 3 (does the 180-365 range apply
when the row holds a statutory *document*) and ⚠ COMPLIANCE 4 (Aadhaar's own statutory
regime) — `00-decisions.md` §7 records both as **written answers still to come** — plus the
**three new questions in §9.1** that the Aadhaar decision creates. All of them gate
switching the form on at a tenant with real joiners rather than the build, **except
COMPLIANCE 4, which I would now ask before the masker is built**, because a "no" makes the
slice's largest piece of work worthless. **ALV-215 still gates switch-on.**

---

## 14 · The new-Frappe-app checklist rows, re-answered

No app is installed by this slice, but three of its security rows changed and the honest
answers are:

- **Public pages:** was one (`/joiner`, guest). **Now zero** — the page requires a session.
- **Guest access:** was three guest POST endpoints. **Now zero.**
- **Self sign-up:** none, before and after. A User is created, but only by HR's invite
  endpoint, never by a public call.
- **New roles created:** was none. **Now one**, `desk_access = 0`, with no permission rows —
  079-SEC-1.

**Net public surface goes down.** That is worth saying to a customer, and it is the clearest
single argument for decision 1.

---

## 15 · Residual risk

| # | Risk | Severity if it happens | Owner | Accepted | Label |
|---|---|---|---|---|---|
| **R-1** | **An account exists inside the site for a non-employee.** The whole boundary is one `before_request` gate plus a role with no permissions | **P1** if the gate is wrong or fails open; one joiner otherwise. Never cross-tenant | Surbhi | 1 Nov 2026 | **Intentional trade-off.** The gate is 079-SEC-3 and its fail-closed clause is the part that must not be traded for a passing test |
| **R-2** | **`tabVersion` may hold erased values.** Inference, not measured | **P1 if true** — counsel's rulings 3 and 4 unmet while believed met | Surbhi | open until M1 is answered | **Dangerous debt — escalate now.** One query removes the doubt |
| **R-3** | **No written answer yet on Aadhaar, nor on retention for identity *documents* from a non-employee** — and we are now **building a feature whose purpose is to hold one** | **P1** if the Aadhaar type is offered at a real tenant before the written answers. **And a wasted slice** if the answer is "the employer may not ask" | Surbhi, with counsel | open | **Dangerous debt — escalate now.** 078 ⚠ COMPLIANCE 3 and 4, plus §9.1's three new questions. ALV-215 gates switch-on |
| **R-11** | **A masking rule later found wrong cannot be re-run**, because the original is gone by design. The remedy is purge and re-ask | P2 per affected person, **P1 if the wrong rule ran for weeks** | Surbhi | 1 Nov 2026, with her §6a decision | **Intentional trade-off**, and the direct cost of "the original never reaches disk". 079-PRIV-6 is what makes it survivable; the affected-record query is the part that must exist **before** it is needed |
| **R-12** | **A native image parser now processes attacker-chosen pictures on the server.** The only risk in this slice whose worst case is bigger than one person's data | **P1** if it is exploitable | Surbhi | 1 Nov 2026 | **Intentional trade-off.** Reduced, not removed, by 079-SEC-8: our own decoder first, a pixel ceiling, a timeout, pinned versions, no shell |
| **R-13** | **We will refuse some genuine Aadhaar photographs, and we cannot say how many.** No accuracy figure may be claimed to anybody | P3 — support calls | Surbhi | 1 Nov 2026 | **Acceptable simplification**, and the right side of her rule. **Watch for the softening:** the pressure to "store it and let HR sort it out" will arrive with the first complaint, and that change is a P0 |
| **R-14** | **The QR code may carry the full number, and I do not know** (M5) | **P1 if true and unhandled** — digit-masking would then be cosmetic | Surbhi | open until M5 is answered | **Dangerous debt — escalate now.** Five minutes with a card and a scanner closes it |
| **R-4** | **The credential is delivered by whatever channel HR uses** — a message, read out, or email. We do not control it | P2 for one joiner | Surbhi | 1 Nov 2026 | **Intentional trade-off.** Revocable and attributable, unlike the link. M2 is the decision |
| **R-5** | **A credential shared with the joiner's consent is indistinguishable from the joiner** | P3 | Surbhi | 1 Nov 2026 | **Acceptable simplification.** J7 — and nothing should prevent it |
| **R-6** | **Nothing records that HR read a submission** | P3 | Surbhi | 1 Nov 2026 | **Temporary debt.** §12 says what closes it and why I am not requiring it |
| **R-7** | **No malware scanning on an upload.** Type allow-list, magic bytes, ceilings, private storage, attachment-only serving — and no scanner | P2 | Surbhi | standing | **Intentional trade-off.** **Never claim scanning in a questionnaire** |
| **R-8** | **`purge_submission` is untested**, and it is the path that erases on a person's own request, ignoring legal hold | P2 — it is counsel's ruling 8 in code | Surbhi | 078, still open | **Temporary debt.** One test removes it, and ruling 8 makes it worth writing now |
| **R-9** | **The joiner page is English only** (ALV-267), against the product's parity rule, and the notice just got longer | P2 for the frontline journey | Surbhi | 1 Nov 2026 | **Temporary debt.** Hindi parity is also unprovable in this environment (§16) |
| **R-10** | **The breach runbook has still never been drilled.** CERT-In's clock is 6 hours from awareness, and this slice holds non-employees' identity documents | **P1 on the day it matters** | Surbhi | standing | **Temporary debt.** One drill removes it, and it should happen before the form is switched on anywhere real |

**Retired from 078 by this change:** R9 (a bearer link's contents are unbounded), R13 (a
misused link is undetectable — partly, see R-5), R14 (`Web Form Request.key` in clear —
**closed outright**).

---

## 16 · What I could not verify, and the access I would need

Each of these is a finding in its own right.

1. **I ran nothing.** Every code claim above is *verified in code* at a cited line in this
   worktree on 1 November 2026, or labelled Inference, Assumption or Unknown.
2. **Frappe's source is not in this worktree** (only `hrms`, `alvoraa_portal` and
   `alvoraa_goals`). So these are **Unknown**: whether Frappe writes an attributable log row
   for a Website User's login; whether a live session dies when `enabled` goes to 0; whether
   `reset_password` refuses a disabled user and whether it answers differently for an
   unknown address; who may read a `Version` row; and whether a Desk list export writes an
   Access Log row. *Access I would need:* a read of `frappe/auth.py`,
   `frappe/sessions.py`, `frappe/core/doctype/user/user.py`,
   `frappe/core/doctype/version/version.json` and `frappe/desk/reportview.py` **inside the
   bench image**. Each requirement above is written so the build goes red rather than the
   claim going quiet.
3. **I did not query any site.** A full test run was in flight in `hrlocal-078`, and another
   session's bench is not mine to touch. **I also cannot read DTC's real roles: DTC is
   production.** *What I need, and who can run it:* on a dev site —
   `select name, desk_access from tabRole`, and the `User Permission` rows for one staff
   login — to confirm no existing role would accidentally match a joiner gate. The DTC
   pattern recorded on 26 Oct (narrow per-doctype rows, an Employee permission that
   restricts) says nothing here would widen, but I have not seen it.
4. **I have not read counsel's written rulings.** I worked from `00-decisions.md` §7 and have
   said so at every use. **I am not a lawyer**, and ruling 5 in particular turns on a
   statutory regime I will not state from memory.
4a. **Two facts the masker's design leans on, and neither is verified.** **(i)** What an
   Aadhaar card's **QR code** contains, by card version — M5, R-14. **(ii)** That the 12th
   digit is a **Verhoeff check digit** — M6, widely documented and not primary-sourced by
   me. *Access I would need:* UIDAI's own published documentation, and one physical card
   with a QR scanner. **Both are five-minute checks for somebody who is not me**, and the
   requirements are written so that a wrong answer changes one function rather than the
   design.
4b. **I have measured nothing about OCR.** Not its accuracy, not its speed, not its memory.
   **No number in 079-PRIV-4 or 079-SEC-8 is a measurement** — the confidence threshold, the
   timeout and the pixel ceiling are all *shapes with a value to be set by whoever measures
   them*, and the DevOps engineer should set them from a real run rather than inheriting my
   placeholders. The **NFR cost is also unmeasured**: an OCR pass plus two re-encodes, inline
   in a web worker, on a frontline phone's upload. That belongs in the DevOps requirements,
   and it is the one place this slice could blow a response-time budget.
5. **Hindi parity cannot be proved in this environment**, as in 078.
6. **The compliance baseline is 69 days old** (verified 24 Aug 2026). Inside the window, so
   I relied on it — DPDP s.4, s.5, s.6(1), s.8(5), s.8(7), s.12 and the CERT-In 6-hour clock
   are quoted from it, not re-verified today. **It goes stale on 22 November 2026**, which is
   inside this slice's likely life: re-verify before anyone answers a questionnaire from it.

---

## 17 · Subtract pass — what I removed

Read back once, asking only what can be deleted and still meet the requirement.

**Removed:**

- **Seven of 078's requirements, outright** (§1.1), including **078-SEC-19**, which was
  dangerous debt. That is the largest subtraction here and the login made it free.
- **A numbered requirement per surviving 078 item.** §1.2 lists them in one paragraph instead.
  Re-stating a met requirement to look thorough is how the two that matter get skimmed.
- **An HR-read access record** as a requirement. Demoted to named debt (§12, R-6): no ruling
  asks for it, and the window it would cover is 30 days.
- **A session-expiry change** for the site. Deleted: it is site-wide and would change every
  member of staff's day to control one account. 079-SEC-5 ends the account instead.
- **An OTP, an SMS channel, and a CAPTCHA.** The login is the identity binding the OTP
  existed to add.
- **~~Server-side OCR masking of Aadhaar~~ — restored by Surbhi's decision of 1 Nov**, and it
  is now the largest requirement in the document. My objection is kept inside 079-PRIV-4
  rather than deleted. **The client-side black-box variant stays deleted**: unverifiable.
- **From the masking requirement itself, subtracted:** a **confidence score stored on the
  row** (it is a number about a person's document that nothing would read — the outcome
  `masked` plus the masker version is enough); a **second opinion from a second OCR engine**
  (double the native surface to improve a figure we are not allowed to claim; the read-back
  check already answers "did it work"); a **queue or retry for the masking** (impossible —
  it would mean storing the original); a **manual HR review queue for refused uploads**
  (that is the "store it unmasked and sort it out later" door Surbhi's rule closes, wearing
  a nicer name); and **keeping a thumbnail of the masked card** for a list view, which would
  be a second copy of an identity document to erase.
- **A per-field sensitivity classification** (compliance-map A1). Still the right long-term
  mechanism, still rung 5 for a rung-2 job, still deleted.
- **A new CI gate** for route allow-lists. Deleted: assertion 6 rides in the slice's own
  module, and a fifth gate nobody reads is worse than four that fail honestly.
- **Two of the eight CI assertions** (§10's closing paragraph), folded into others with
  nothing left unproved.
- **A server-side draft** for "they may come back". The device already does it; a server
  draft would be a half-filled personal record both clocks would have to learn about.
- **A per-finding "which test proves it" table.** Each requirement carries its own test.

**Kept deliberately, though it is not strictly required:** 079-SEC-7, the demand that the
`ignore_permissions` count go **down**. It proves the rewrite actually used the session
instead of keeping a Guest-shaped design behind a login, and that is not visible any other
way.

---

## 18 · Governance note

**I wrote 078's requirements, its addendum and its security review, and I am now writing
what replaces them.** Under the rule that the builder must not approve its own requirements,
three things here want a second reader:

1. **§6 reason (2)** — that the submission doctype launders permission levels. It is an
   argument, and the check is one read of the doctype's field list.
2. **§7 079-SEC-3's fail-closed choice.** I am reversing, for one role, the fail-open
   decision made deliberately for the first-use lock. The reasoning is in the text; the
   trade is a judgement.
3. **§8 079-PRIV-4, the masking.** My recommendation was to refuse Aadhaar images; **Surbhi
   decided otherwise on 1 Nov 2026 and the decision is hers to make.** I have written the
   requirement to her rule and kept my objection inside it. The clause that most needs a
   second reader is **3(d), the read-back check**, because the whole of my willingness to
   call this buildable rests on it: if the read-back is ever weakened, softened, or made
   advisory, the design is back to trusting OCR and my original objection applies again in
   full. **Reviewers: check 3(d) first, and check that the outcome table in assertion 9 still
   has only two columns.**

**A Blocker from me blocks a slice at review. Nothing in this document is approval of
anything.**
