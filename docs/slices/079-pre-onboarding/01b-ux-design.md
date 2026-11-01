---
slice: 079-pre-onboarding
artifact: 01b-ux-design.md
author: hrms-ux-designer (design mode)
date: 2026-11-01
status: draft for Surbhi's design gate. Prototype v6 exists and must be reviewed alongside this document. NOT published by me.
inputs: [ux-learnings.md, 079/00-decisions.md, 078/01b-ux-design.md §6.5 §6.6 §17, prototype-v5.html,
  no-over-engineering.md, data-doors.md, nfr-budget.md §2 §5 §7, product-context.md §2 §6, CLAUDE.md §6,
  design_system.html, alvoraa-login.html, auth.py, joiner.py, joiner.html, joiner_public.py,
  joiner_housekeeping.py, commit 5aa654d2 (ALV-232)]
prototype: C:/Surbhi-Git/hrlocal-data/prototypes/078-positions-faces/prototype-v8.html  (v1–v7 kept beside it)
revision: v8, 1 Nov 2026 — two columns on My Profile, with Your password stacked under Your documents on the right (§10a). Nothing else in the design changed.
screens: C:/Surbhi-Git/hrlocal-data/ux-review/2026-11-01/
supersedes: 078/01b §6.6 and the parts of §17.6–§17.7 that describe a link. Everything else in 078 §17 stands.
---

# 079 · Pre-onboarding — the joiner arrives with a sign-in, not a link

## The answer first

**The biggest thing in this document is not a screen. It is one line of existing code.**
`auth.py::home_page_for()` sends a signed-in user who has **no Employee record** and no
system role to `/hrms-employee` — the staff portal. A joiner is, by decision 1, exactly
that user. **Without a new branch there, a joiner's sign-in opens the employee portal.**
That is **P1**, it is in §7, and it is the first thing for the engineer.

**What I designed.**

| Part | What it is |
|---|---|
| **The message HR sends** | Six lines, two shapes (a text message, a printed slip). It is the first screen, so it is designed like one |
| **The sign-in page** | A **joiner state on the page we already have** — not a second login page. New heading, two renamed fields, a full-width reveal, a help block that ends at a human, and four failure screens each with a code for HR |
| **Coming back** | The **same screen** they left, with a "nothing was lost" strip and a step list that now says what is done |
| **The account's edges** | No navigation at all. One refusal screen when they ask for anything else. A named Sign out |
| **What happens to what I send** | The employer's own retention periods and contact, two clocks, the Aadhaar promise and its honest limit |
| **Aadhaar** (added mid-task, 1 Nov) | Three states inside the document block that already existed: before you send it, we could not cover the numbers, kept with the numbers covered |

**What I removed** is in §11. **What I want you to decide** is in §12 — six items, and
**D1 (do we force a password change?)** and **D4 (can the sign-in page tell "ended" from
"wrong password"?)** are the two that change the build.

**Where I disagree with nothing.** Every decision in `00-decisions.md` is built as
written. One of them — decision 4, "until they press Send" — contradicts a sentence v5
shipped; I followed the decision and say so in §9.

---

## 1 · Frame

**Priya Khanna, who starts at PP Jewellers in nine days, standing somewhere with one bar
of signal, holding a text message, on a phone that is sometimes hers.** She is not an
employee, has no record with us, and has never heard of Alvora.

| Persona | In scope | What changes for them |
|---|---|---|
| **New joiner (frontline, phone)** | **Primary.** Every screen in §4–§6 | Everything. The link is gone; they now sign in |
| **HR Manager** | The message, the invite block, the precondition | They relay a username and a password instead of a link, see it once, and cannot invite anybody until two retention numbers and a contact are set |
| **Employee** | My Profile only | DECISION 14 is settled: the page never refuses a save (§8) |
| **CXO** | Nothing on screen | One sentence matters: a joiner is **not a seat, not headcount, not on the chart**. It is said on HR's screen, because HR is who gets asked |
| **Customer IT / security reviewer** | §7 | A login finally makes "who opened this, and when" answerable. The limit must live in Frappe's permission layer, not in our page |

Out of scope, deliberately: everything in 078 that the decision did not touch — faces, the
chart, the mini profile, the seat page, the pickers, the required tick, the tags.

---

## 2 · What the decision actually changed, line by line

| v5 (a bearer link) | v6 (a restricted sign-in) | Where |
|---|---|---|
| A one-time URL in the fragment, never sent to the server | A username and a password typed on the sign-in page | §4 |
| "You do not need an account and you will not be asked for a password" | **Deleted.** It is now false | §5.1 |
| "This link is for you. Please do not pass it on." | **Deleted.** The sign-in is the control, not a warning at the foot of a welcome screen | §5.1 |
| Typed answers kept in the browser (`localStorage`) | Saved **with the employer**, against the sign-in | §5.2 |
| "This link has run out" | "This sign-in has finished its job" — two ways it ends: they pressed Send, or the date passed | §5.4 |
| "A refused send does not burn the link" | Same rule, new words: "Nothing has been sent, and you are still signed in" | §9 |
| "You can still send a photograph on this same link until 7 November" (on Sent) | **Deleted** — decision 4 says the access ends at Send | §9, ⚠ D5 |
| The settings card called the form "a public web page at `/pre-onboarding`" | "a page their own sign-in opens"; address `/joining` | §8 |
| Nothing stopped HR inviting before retention and contact were set | HR cannot invite until they are | §6.3 |

---

## 3 · The hand-over: what HR sends

**The message is the first screen.** A joiner's whole experience of us begins as six lines
of text on a lock screen, so it is designed, not left to whoever writes the SMS template.

```
PP Jewellers — before your first day

Please fill in a few details before you start. About 5 minutes on your phone.

Open:          ppj.alvoraa.co/joining
Sign in with:  98xxxx4417
Password:      tiger-lamp-74

Finish by Saturday 8 November.
Keep this message — you need it if you stop and come back.

Questions: Arjun Bhatia, 0172 450 1180
```

Six facts and nothing else. Each one earns its line:

1. **No brand headline, no sales paragraph.** Today's sign-in page shows "People. Process.
   *Progress.*" and a paragraph about OKRs — on phones too (064 §2.1). A person who does
   not work here is not buying anything.
2. **A short, typeable address.** It has to survive being read off paper or down a phone.
3. **The username is the thing they already carry** — the mobile number or email the
   employer already reached them on. Nothing new to remember, nothing synthetic to type.
   *(This needs a tenant-wide setting — ⚠ D2.)*
4. **A password of three words and two numbers**, not `Xk9#mQ2z`. It is typed once, on a
   cracked screen, sometimes dictated. A stronger string loses more real joiners than it
   protects, for an account that lives days and opens one form. ⚠ D3, security's call.
5. **"Keep this message."** The thing they will not remember on Thursday is *which number
   they signed in with*. The message is where that lives, so the message says so.
6. **A weekday and a date**, never "7 days". Nobody counts days from a message read on a bus.

### 3.1 Two shapes, one mechanism

**Shape A — a text or WhatsApp message.** The default; the employer already has a number.
**Shape B — a printed slip.** The same six facts on one sheet, for a joiner taken on at
the gate or with no phone of their own. **The only difference is the paper.**

That is the whole reason the password is words rather than a link: *a set-password link
cannot be printed, dictated, or read down a phone line.* One mechanism covers both routes,
so there is no second flow to design, test or explain.

### 3.2 What I chose against: the set-password link

The brief allowed "a password **or** a set-password link". I rejected the link, and the
reasoning is worth having in writing because it looks like the friendlier option:

| | Set-password link | Issued password **(chosen)** |
|---|---|---|
| First contact | **Better** — one tap, nothing typed | Two fields typed |
| Works from paper / dictation | **No** | Yes |
| Second visit | Needs a username they have never typed | The same two facts as visit 1 |
| Is it a bearer URL? | **Yes, for the first step** — the thing decision 1 removed | No |
| Extra screens | "Choose your password", "this link has been used" | None |
| HR knows the secret | No **(better)** | Yes, once |

The link wins one row and loses four. Its one real advantage — HR never seeing the secret
— is worth less here than it looks, because HR reads the whole submission anyway; the
exposure is a **detection** problem (every sign-in is logged against a named username,
which a link never was), not a prevention one.

---

## 4 · The sign-in page — the screen that decides whether she gets through

**It is the page we already have, in a joiner state.** Not a second login page: one page,
one set of fields, one error pattern, one place to fix a bug. The state is chosen by a
hint in the address HR sends (`/login?for=joining`); with no hint the ordinary page
appears and the same credentials still work, so nothing breaks if the hint is lost.

### 4.1 What changes in that state

| # | Today | In the joiner state | Why |
|---|---|---|---|
| 1 | "Welcome back · Sign in to your workspace" | **"Fill in your details before your first day"** · *"Arjun Bhatia from PP Jewellers sent you a message with two things in it. Type them here."* | A login page has two states; the first-time one has never existed (064 §2.1). This person has never been anywhere |
| 2 | Marketing panel, visible at every width | **Not drawn at all** | P2 in 064, fixed here for this state only |
| 3 | "Email / Username", placeholder `you@company.com` | **"The phone number or email HR sent the message to"**, no placeholder | Name the thing the person is holding, not the thing our database calls it |
| 4 | Field text 15.2 px | **16 px** | Under 16 px, iOS zooms on focus and pushes the button off screen |
| 5 | "Password" | **"Your password"** → *"Three words and two numbers, like `tiger-lamp-74`. Type it exactly as it is written, dashes and all."* | The hint is the format, because the format is unusual |
| 6 | ~28 px eye icon in the corner | **A full-width 44 px "Show the password" button** under the field | The mistype is the likeliest failure in the journey and the reveal is the smallest target on the page |
| 7 | "Sign In" | **"Sign in and open my form"** | Says what happens |
| 8 | "Forgot password?" → emails a link · "Need help?" → `mailto:` | **"I cannot sign in"** → an in-page block ending at the employer's own phone number | **Both of today's escape routes are dead ends for a person with no email address** |
| 9 | — | A grey footer: *"PP Jewellers asked for these details. Alvora only runs the software they use."* | Counsel's ruling 1 in plain words, at the moment the stranger is deciding whether to trust the page |

### 4.2 Every failure, with its words

Four screens. All four carry a **code for HR** — the pattern slices 013 and 064 settled,
because the code is the only thing a person who reads slowly can still show somebody.

**That did not work** (`JOIN-BADPASS`)
> **That did not work.** Check the password against Arjun Bhatia's message — a dash or a
> letter is easy to miss. Press **Show the password** to see what you have typed.
> **2 more tries** before this sign-in locks for 30 minutes.

It does not say *which* of the two was wrong — that would tell a stranger whether a given
phone number belongs to a joiner at PP Jewellers. It **counts down out loud**, because
hitting a silent lock is the single most likely way we lose a real joiner. *(The number of
tries and the lock length are Frappe's `System Settings`; ⚠ D4b — confirm, do not guess.)*

**I cannot sign in** (`JOIN-NOSIGNIN`)
> **Arjun Bhatia's message has both things you need**
> · the phone number or email it was sent to
> · a password of three words and two numbers
> It may be a text message, a WhatsApp message, or a slip of paper.
> **Still stuck?** Ring Arjun Bhatia at PP Jewellers on **0172 450 1180** and ask for a new
> message. He can send it to the same number, and the new password replaces the old one.

**Locked for 30 minutes** (`JOIN-LOCKED`)
> **Locked for 30 minutes.** The password was wrong too many times, so this sign-in is
> closed until about **11:40 am**. That is there to protect your details.
> **Nothing you have already filled in is lost.** It is saved with PP Jewellers.
> **What to do:** wait until 11:40 am and try again, or ring Arjun Bhatia on 0172 450 1180
> and ask for a new password.

The only button names the time rather than pretending it will work now — *no action button
where no action would work*.

**The access has ended** (`JOIN-ENDED`)
> **This sign-in has finished its job.** Either you have already sent your form, or PP
> Jewellers has closed it. **Nothing is wrong, and nothing you sent is lost — HR has it.**
> If you still need to send something, ring Arjun Bhatia at PP Jewellers on 0172 450 1180.

**This screen must never read "Invalid credentials."** A joiner typing a password that was
correct yesterday and being told it is wrong will try again, lock themselves out, and ring
to say the system is broken. Whether the page *can* tell the two apart is ⚠ **D4** — an
engineering and security question, not a wording one. I have drawn the screen we need
either way.

---

## 5 · The joiner's own screens

### 5.1 Welcome — four sentences changed, two of them deleted

Four headed blocks, in this order: **What we will ask for · You can stop and come back ·
This sign-in opens this one page · What happens to what you send.** Then **Start**, then a
secondary **"What happens to what I send, in full"**.

- *"Arjun Bhatia sent you this link"* → *"asked you for a few details"*. There is no link.
- **"You do not need an account and you will not be asked for a password" is deleted.** It
  was the most reassuring sentence on v5's welcome screen and it is now false. **Nothing
  replaces it** — they have already typed a password to get here, so the worry it answered
  has either been met or has already failed.
- **"This link is for you. Please do not pass it on." is deleted.** A link could be
  forwarded. Telling somebody not to share their own password, at the bottom of a welcome
  screen, is a warning in the wrong place at the wrong moment.
- *"Kept on this phone … the same link until 7 November"* → *"saved with PP Jewellers …
  sign in again before Saturday 8 November"*.

### 5.2 Where the draft lives — a real change, named

**v5 kept typed answers in the browser.** That was right when there was no sign-in: a
joiner may be on somebody else's phone, and an uploaded image blows the `localStorage`
quota anyway (documents already upload to the server immediately — `upload_invite_file`).

**With a sign-in, the draft moves to the employer's record.** Three things follow, and they
are the reason, not a side effect:

1. **"Nothing was lost" becomes true across devices.** They can finish on a different phone.
2. **Signing out leaves nothing behind on a borrowed handset.** With a browser draft,
   "nothing was lost" and "nothing is left behind" could not both be true.
3. **It deletes a state** — the quota failure that fails silently.

**What it costs, said plainly:** a part-filled row of somebody's personal details now sits
with the employer *before* they press Send, which starts the retention clock earlier.
Housekeeping must cover drafts, not only submissions (⚠ COMPLIANCE, §7).

### 5.3 Coming back — the same screen, not a new one

They land on **the step they left**, with two answers to "what was kept?":

> **You are back, and nothing was lost.** Everything you filled in on **2 November** is
> still here: **4 of 7 answers** done and **2 of 4 documents** sent.
> You have until **Saturday 8 November** to finish.

and the step list, which now carries a word per row — `Done`, `2 of 4 sent`, `you are
here`. One word in a component that already existed.

**Why not a "welcome back" page.** It would be a screen whose only job is one strip of
text — plus its own empty, loading and error states, and one more tap before the first
question. And re-reading the introduction hides the thing they actually want to know.
**The counts matter more than the reassurance: "nothing was lost" is a claim, "4 of 7" is
a fact.**

### 5.4 What happens to what I send

Reachable from the Welcome screen and from the footer of every step. Seven short blocks:
who reads it · if you join · if you do not join · you do not have to send an Aadhaar card ·
if you want it back or deleted · who we are · and a grey line saying **the periods and the
number above come from PP Jewellers' own settings**.

> **If you do not join.** PP Jewellers keeps your details for **180 days** and then deletes
> them. A photograph of an identity card is deleted sooner — after **45 days**.

**Two clocks, said separately**, because counsel's rulings 3 and 4 set different periods
and one sentence covering both would be wrong about one of them. The build has a single
setting today; that gap is named in §7.

**No tick, no consent box, no "I agree".** Nothing here asks permission: we are the
processor, the employer is the fiduciary, and the joiner is *told*, before the first
question and again from every step. A tick would be decoration that implies a choice they
do not have.

### 5.5 Aadhaar — we cover the digits, or we keep nothing *(added 1 Nov)*

Three states **inside the document block that already existed**. No wizard, no new screen,
no fourth button: it is one document type among several and most joiners will send a PAN
card.

**Before they send it**
> **You do not have to send this one.** A PAN card, passport, driving licence or voter card
> will do instead, and they are simpler.
>
> **If you do send it, we cover the first 8 digits on the picture before we keep it.** Only
> the covered copy is kept; the photograph you take is not. You will see the covered copy
> here afterwards.
>
> We cover the numbers. We are not promising the picture is safe to pass around — it is
> still a photograph of your card.

The alternatives come **first**, because they are the easier path. The last line is the one
I care about: anything warmer is a claim we cannot keep.

**Covering the numbers** — a `role="status"` line in the block: *"Covering the first 8
digits… This takes a few seconds. Please stay on this page — nothing is kept until it is
done."*

**We could not cover the numbers** (`JOIN-MASKFAIL`)
> **We have not kept that photo.** We could not be sure we had covered the first 8 digits,
> so we did not keep the picture at all. **Nothing from it was saved, and you are still
> signed in.**
> That is nearly always the light or the angle — not anything you did.
>
> **Three ways on, and PP Jewellers is happy with any of them:** take another photo with
> the card flat and the whole card in the frame; send a **PAN card, passport, driving
> licence or voter card** instead — their boxes are on this same page; or say you will
> bring it on your first day.

It blames the light, not the person. It says what was *not* saved. **It says they are still
signed in — the hard requirement.** The alternatives are words, not a fourth button,
because their own boxes are already on this screen. "Take another photo" is **not** the
primary button: `Next` is still the screen's one main action, as it has been since v5.

**Kept, with the numbers covered** — the masked copy shown back, small, in place, never
auto-enlarged, labelled *"This is what PP Jewellers has. The photograph you took was not
kept."*

**Showing it back is right, and here is the argument.** "We covered it" is a claim; a black
bar they can see is a fact, and the joiner is the only person who can check it. The cost is
that we re-draw an identity document on a screen that may be borrowed — answered by size,
placement and the fact that nothing enlarges on its own.

---

## 6 · What the sign-in opens, and what it does not

### 6.1 To the joiner

**There is no navigation.** Not a sidebar with one entry, not a bottom bar with one tab. A
navigation is a way of getting somewhere else and there is nowhere else. The only furniture
is the strip at the top of the form: **who they are signed in as**, and **Sign out**.

**If they type another address** — `/hrms-employee`, `/app`, anything:

> **This sign-in only opens your joining form**
> You are signed in as a new joiner at PP Jewellers, so there is nothing else here for you
> yet. Once you start work, the same sign-in opens your own staff pages.
> [ **Back to my form** ] · Code for HR: `JOIN-ONEPAGE`

One button, and it works. No hint of what is behind the refusal — no menu, no page names,
no counts. *"Not yet"* is the honest word: they are about to work here, so "you are not
allowed" would be true, unkind, and wrong in a week.

**Sign out** is named, 44 px, and says what it does to the draft: *"Everything you have
filled in is saved with PP Jewellers. You will need the phone number and the password from
Arjun Bhatia's message to come back."* A joiner is the most likely person in the whole
product to be on somebody else's phone.

### 6.2 To us, and to the customer's IT reviewer — **read `data-doors.md` with this**

A screen is not the control. What has to be true underneath:

| Door | What must hold |
|---|---|
| **User type** | A **Website User**, not a System User. Frappe refuses a Website User at `/app` by construction — the cheapest door available, and it is a property of the account, not of our page |
| **Roles** | One role that reads nothing. Never `Employee Self Service` |
| **Landing** | `home_page_for()` must return the joining page **before** its `_portal_home_for()` fall-through. **Today it does not — see §7, P1** |
| **The form's own calls** | Authorise on `frappe.session.user` owning the submission, not on a token. The `web_form_request_key` machinery goes |
| **Every other door** | The ten in `data-doors.md`, tested as this login on a fresh site: `/api/resource/Employee`, `reportview.get`, `frappe.client.*`, link search, report view and export, share/assign/comment, `hrms`/`erpnext` whitelisted methods, child tables, write rights, bulk paths |
| **Detection** | Every sign-in, every HR read of a submission, every export. Counsel's ruling 9. **Two of the three are open defects carried in from 078** |

**I have verified none of this on a site.** It is read from code and must be proved by the
security engineer and the test engineer.

### 6.3 HR's side

**After "Invite":** one block where the "copy this link" block used to be — the exact
message, a **Copy the message** button, a **Send it as a text message** button, and:

> **Priya Khanna can now sign in.** Send her these lines. **You will not see this password
> again.** … If she loses it there is nothing to look up — send a new invite and the old one
> stops working.
> **She cannot see anything else.** This sign-in opens her own form and nothing else at PP
> Jewellers. She is not an employee, not in your headcount, not on the organisation chart,
> and not a paid seat until she starts.

That last sentence is the CXO's answer, put where HR is, because HR is who gets asked.

**Before the tenant has set its own numbers, there is no invite button at all:**

> **You cannot invite anybody yet.** A joiner has to be told three things before they hand
> over anything, and they come from your settings, not from us:
> · how long you keep the details of somebody who does not join — **not set**
> · how long you keep a photograph of an identity card — **not set**
> · a phone number or email a joiner can reach you on — **0172 450 1180 ✓**
> [ **Open these settings** ]

**This deletes a joiner-facing screen.** The alternative was a notice reading "PP Jewellers
has not told us how long they keep this" — frightening, unanswerable by the joiner, and
shown to the only person who cannot fix it. Blocking the invite moves the problem to the
person who can.

---

## 7 · Findings — what the engineer and security must act on

| ID | Finding | Severity | Evidence |
|---|---|---|---|
| **J1** | **A joiner's sign-in lands on the employee portal.** `home_page_for()` → no `Employee` row, no desk role → `_portal_home_for()` → `/hrms-employee` | **P1** | `auth.py:38-49` (read 1 Nov) |
| **J2** | The portal's forced password change (ALV-232) **excludes users with no Employee record by design**, so a joiner is never caught by it. If you want a forced change (⚠ D1) it is new code, not reuse | P3 | `auth.py:40-42`, commit `5aa654d2` |
| **J3** | **"Access ended" may be indistinguishable from "wrong password"** at the sign-in page. If so, the worst state in the journey ships | **P1 if it is true** | ⚠ D4 |
| **J4** | The **lockout threshold and duration are unknown to me.** A silent lock after a mistyped dashed password is the likeliest real-world loss | P2 | Frappe `System Settings`; not read |
| **J5** | Signing in **by mobile number** needs a tenant-wide setting that changes it for every employee, and two users sharing a number is undefined | P2 | ⚠ D2 |
| **J6** | **Drafts now hold personal data before Send.** `joiner_housekeeping` must purge drafts, and the clock starts at the draft | **P2, COMPLIANCE** | §5.2; `joiner_housekeeping.py` |
| **J7** | **Two retention clocks are still one setting.** `alvoraa_joiner_not_hired_days` / `backstop_days` exist; there is no separate document clock, and §5.4's screen cannot be honest without it | **P1 for switch-on**, not for build | `joiner_housekeeping.py:11-13`; counsel rulings 3 and 4 |
| **J8** | **The Aadhaar rule follows the declared document type.** An Aadhaar photograph uploaded into the *PAN card* box skips masking entirely — which makes it a label, not a control | **P2, security decision** | §5.5 |
| **J9** | Nobody has measured **how often the masking will be unsure** on a phone photo in shop lighting. If it is often, the refusal screen is the journey, not an edge case | P2 | Unmeasured |
| **J10** | **English only** (ALV-267). The door is ~24 strings with every failure; the joiner's own new wording is ~30 more. **A person who cannot read the sign-in page never reaches the form** | **P2** | §10 |
| **J11** | Carried from 078 and **not fixed here**: HR can export submissions unmasked with nothing logged (R11); no record that HR read a submission | **P2** | `00-decisions.md` §9 |
| **Keep** | The required tick, the grouped tags, the two-answer compulsory document, the tappable refusal, the step list, the group-splitting rule, the day-one empty state | — | 078 §17, unchanged |

---

## 8 · My Profile — DECISION 14, settled, and made to feel deliberate

Decision 3 settles it: **My Profile never refuses a save.** The "block the save" state is
**deleted from the prototype**, not parked beside it. What remains: the save goes through,
a standing amber block names what is still needed on every visit, each field keeps its
`Needed` chip.

**The joiner form still refuses an incomplete send.** The same person meets both inside a
week, so the difference has to read as a rule. Two things make it one:

1. **The same word everywhere.** `Needed`, the same amber chip, on both screens. Never
   "mandatory" on one and "required" on the other.
2. **One sentence of reason on each screen, stated positively.**
   - My Profile: *"This is your own record, so you can change anything here and save as you
     go. We will keep asking for these until they are filled in."*
   - The joiner form: *"Anything marked **Needed** has to be filled in before you can send
     the form. You can leave the rest blank."*

**Send once, against keep up to date.**

**What I deliberately did not do: compare the two screens on either screen.** "Unlike the
joining form, this page…" asks most readers to remember a form they filled in weeks ago, or
never saw at all. **Each screen states its own rule in the same vocabulary — that is what
makes it deliberate, not a cross-reference.**

**What it costs HR:** completeness on My Profile is chased, not guaranteed, so HR needs a
list of who is still missing what. That is a report over the same ticked fields, not a new
screen.

---

## 9 · What of v5 still stands — explicitly

**Unchanged, not re-opened, not re-drawn:**

- **The required tick** — a second tick that only exists on a ticked row (078 §17.2).
- **The grouped tag headings** — `MUST FILL IN (3)` etc. (078 §17.4).
- **A compulsory document must be *answered*, never *had*** — a photograph **or** "I will
  bring it on my first day", both one tap, both send the form; the promise button
  disappears once given; the Sent screen repeats the promise (078 §17.6).
- **The refusal lists each missing item as a tap, not a name**, with the item's own way out
  travelling inside the message (078 §17.6).
- **The step list and the one-screen-per-group rule**, splitting over 8 (078 §17.7).
- **The settings card**: button → dialog → tags, OK saves, the empty day-one state, the
  five lists, the "official numbers are not on this list" block (078 §6.5, §17.4).
- **The server's words win.** The browser decides nothing about what is missing.

**Changed only in wording, because the link is gone:** the welcome screen (§5.1), the
refusal's closing line, the upload-failure line, the settings card's description of the
form, and the picker dialog's warning.

**One behaviour deleted, and it is worth your eye.** v5's Sent screen said *"this same link
takes a photograph of it until 7 November."* Decision 4 says the access lasts **until they
press Send**, so it is gone and the screen says so. **Cost:** a joiner who finds their PAN
card the next evening has to ring HR. **If you would rather keep it**, the rule becomes
"Send ends the form but not the sign-in, until the end date" — one sentence and one state.
⚠ **D5**.

---

## 10 · Accessibility, privacy, performance

**Measured, not eyeballed** (Chrome, 1 Nov 2026; every screen × every state × 1400 desk,
390, 360 and 390-at-200% text): **no console errors; nothing on the new screens wider than
the app; no target under 44 px on a phone or 24 px on a mouse; no text under 12 px.** The
only real defect the measurement found was pre-existing and is fixed: the `View` link in
the documents row was a **20 px** target on a mouse, under WCAG 2.2 AA's 24 px.
**One dark-theme fault found by looking, not measuring:** the masked copy's black
redaction bar sat on a dark surface and vanished. The card block now keeps a light face in
both themes, because it stands in for a **photograph**, not a UI surface — otherwise the
one thing the screen exists to show is invisible to half the users.

*(Remaining reported items are known false positives — fixed-position scrims and drawer
internals measured against the app box, a 20 px checkbox inside a 44 px label, and the
Positions table's deliberate sideways scroll.)*

- Every refusal is `role="alert"`; every confirmation `role="status"`; the masking wait is
  `role="status"`.
- Colour is never the only signal: every chip and every refusal carries words, and the
  step list's status is a word, not a tint.
- The reveal button has words on it; the error names the field; nothing depends on an icon.
- **Privacy:** the only personal data on any joiner screen is **their own**. The refusal at
  §6.1 names nothing about the employer. The masked copy is the only image we re-draw, and
  it is the covered one.
- **Performance (nfr-budget §2):** these screens are a phone-first employee-facing surface
  — **≤ 2.5 s p95 on a 3G profile, skeleton within 300 ms.** Two places need design, not a
  number: the **masking wait** (acknowledge immediately, say it is a few seconds, never a
  bare spinner) and the **upload** (keep the typed answers, offer the promise as a way out,
  never discard).

---

## 10a · The measure, and two columns — v7 and v8, 1 Nov 2026

> *"isn't it too wide in desktop, can we put two tiles side by side. Your details and Your
> documents. in case someone zooms the screen the tile should drop the next row."*
> — Surbhi, 1 Nov 2026

**She is right, and the screen she is looking at is My Profile — not the joiner's form.**
Measured on v6 at a 1400 px window: the mobile-number box on My Profile was **1280 px wide**
for a ten-digit answer. **The joiner's form has been capped at 420 px since v5, so it never
had the fault at all.** I am saying that plainly rather than quietly fixing the screen I was
pointed at, because it changes where the change lands.

**Where the fault actually is** (measured, every screen and state, 1400 px window):

| Screen | Widest field or button in v6 | What I did |
|---|---|---|
| **1 · My profile** — "Your details", "Your documents" | **1280 px** | **Two tiles side by side.** The change she asked for |
| **0 · Getting in** (sign-in, the message, HR's block) | 1280 px | **Capped** — these are mine, new in this slice |
| **8 · What this sign-in opens** | 1280 px | **Capped** — mine |
| **5 · The seat page** | **1280 px** | **Left alone, and listed.** Another shipped 078 page nobody has asked about; one page is enough to judge the rule by |
| **7 · The joiner's form** | 382 px | Nothing. Already right |
| 2, 3, 4, 6 | n/a — charts, tables, and a 620 px dialog | Nothing |

**⚠ This lands on 078's page.** My Profile has already shipped. I have drawn the change
because it is unmistakably the screen and the change she means, but **whether it ships in
078 or waits is her call, not mine.**

### v8 — the right column holds two cards

> *"and the same for this section move it to the right side"* — Surbhi, of **Your password**

**Your details** on the left; **Your documents** and **Your password** stacked on the right.
It is the **same grid**, not a second mechanism: the right cell holds a two-card flex stack,
so the grid still decides how many columns there are and the stack only decides what is in
one of them. The two cards share the column's width and left edge (both 468 px at the same
x, measured) and each keeps its own border, so it never reads as one card with two headings.

**The reflow order is deliberate: details → documents → password.** When the three collapse
into one column, the order is source order, and I agree with the coordinator's reasoning and
would add one more: **documents can carry work** — *"2 are needed before your first pay
run"* — while a password set three weeks ago cannot. So the phone order is also the order
of urgency, not just of frequency. Password last.

**The columns are unequal, and it looks intentional rather than unfinished.** I looked
rather than assumed. Three things make it read as deliberate: both columns start on the same
line; `align-items: start` means **nothing stretches**; and each card is a bounded object
with its own border and fill, so the space under the shorter column reads as **page**, not as
a card that failed to fill. The failure mode would be a card stretched to match its
neighbour's height, and that cannot happen here.

**Both near-empty cases are drawn, because this is where a two-column page usually goes
wrong — and I did not quietly rebalance them.**

| Case | Left | Right | My reading |
|---|---|---|---|
| **A short right column** (new prototype state): one document, password set last week | 1,079 px | **282 px** | Fine. A long form beside two small, complete cards. Nothing looks broken; there is simply less to say on the right |
| **Nothing to edit** (the inverse): the tenant has ticked no editable field | **113 px** | 599 px | The odder of the two, and still legible as two bounded cards anchored at the top. It is also a rare tenant configuration |

**I have deliberately not moved a card back to even them up.** The balance changes with
every person's record — how many documents they have given, whether they have a photo — so
a layout tuned to one person's balance is wrong for the next. **If you would rather the
password card went back under the two columns**, that is one line, and I would rather you
decided it looking at both states above than have me pick for you.

### The two rules, and why both are in `em`

```css
.col    { max-width: 40em; margin: 0 auto }
.two-up { display: grid; gap: 18px; align-items: start; max-width: 76em; margin: 0 auto;
          grid-template-columns: repeat(auto-fit, minmax(min(26em, 100%), 1fr)) }
.two-up > *   { max-width: 36em; width: 100% }
.stack        { display: flex; flex-direction: column; gap: 18px }   /* v8 */
.stack > .pf-card { margin-bottom: 0 }                               /* v8 */
```

**There is no media query and no breakpoint.** `auto-fit` + `minmax` *is* the breakpoint:
the grid takes as many columns as fit at 26em each, so it falls to one column for a narrow
window, a zoomed-in page and a split screen from **one rule**. The wrap is a consequence of
the content's smallest comfortable width, not a number picked off a laptop.

**`em`, not `px`, and here is the honest version of why.** An em describes the reading; a px
describes the hardware. Under ordinary browser zoom the two behave the same, because zoom
scales px and em together. The em earns its place for the *other* case — a reader whose own
default text is larger — and it keeps the rule stated in terms of the text it protects.
**I will not overclaim it:** our type tokens are hard px (`--fs-base: 13px`), so today the em
resolves to a fixed 13 px and the text-size case does not yet reach it. It will, the day the
tokens become relative — already a live open item (`--fs-xs` is 11 px against our own 12 px
floor). **The rule is correct now and becomes more correct then.**

**A lone tile does not sprawl.** `auto-fit` collapses an empty track, so one tile would
otherwise stretch across the whole row — the thing she said must not happen. The **36em cap
on the tile itself** is what prevents it. Proved, not assumed: removing one tile at 1400 px
leaves the survivor at **468 px inside a 988 px grid**.

### What I measured

Re-measured for v8, with the password card in the right column:

| Case | Columns | Left column | Right column | Stacked cards | Widest input |
|---|---|---|---|---|---|
| **1400 px desktop** | **2** | 468 × 1079 | 468 × 599 | 468 and 468, same left edge | **430 px** (was 1280) |
| **1024 px laptop** | **2** | 462 × 1079 | 462 × 599 | 462 and 462 | 424 px |
| **200% zoom on a 1400 px window** — a 700 px CSS viewport, which is exactly what the page sees | **1** | 468 | 468 | 468 and 468 | 430 px |
| **390 px phone** | **1** | 360 | 360 | 360 and 360 | 322 px |
| **1400, short right column** | **2** | 468 × 1079 | 468 × **282** | 136 and 129 | 430 px |
| **1400, short left (nothing to edit)** | **2** | 468 × **113** | 468 × 599 | 299 and 283 | — |
| **One column only, 1400 px** | — | **468 px, not stretched** | — | — | — |

In every case the heading order is **Your details → Your documents → Your password**, both
columns share a top edge, and no card stretches to match its neighbour.

Plus the full suite again — every screen × every state × 1400 / 390 / 360 / 390-at-200%:
**no console errors, no new overflow, no target under 44 px on a phone or 24 px on a mouse,
no text under 12 px.** The 44 px targets, the `Needed` marks and the phone's step-at-a-time
structure are untouched.

**Three faults these two passes found in my own first attempts, and they were caught by
three different methods — which is the point:**

1. **`minmax(26em, 1fr)` overflowed the 195 px case.** A bare minimum track cannot shrink
   below itself, so the grid was 338 px wide inside a 195 px app and pushed the page
   sideways. **`minmax(min(26em, 100%), 1fr)`** fixes it. **Measuring caught this; looking at
   1400 px never would have.**
2. **The full-width cards above and below stopped lining up with the tiles** — the photo card
   began 166 px to their left. Everything on the page now shares the grid's own width.
   **Looking caught this; measuring never would have.**
3. **v8: "1 of 11 given.This card…"** — a missing space after a full stop, only in the new
   short-documents case. **Reading the rendered words caught this; neither measuring nor
   glancing at the layout would have.**

---

## 11 · Subtract pass — what I deleted before handing this over

- **The set-password link**, and with it a "choose your password" screen and a "this link
  has already been used" state (§3.2).
- **A forced password change** on first sign-in, and its screen. Argued in ⚠ D1; not drawn.
- **A "Change my password" link on the joiner's form.** For an account that lives days and
  holds only what the joiner typed, it costs a control and a Frappe page that is English
  and asks for an email. Named as an accepted risk in ⚠ D1 instead.
- **A "welcome back" page** (§5.3).
- **A joiner-facing "the employer has not set a retention period" screen** — replaced by
  blocking HR's invite (§6.3).
- **Any navigation**: no one-item sidebar, no one-item bottom bar (§6.1).
- **A consent tick on the notice.** We are the processor; a tick implies a choice.
- **An Aadhaar wizard, and a fourth "use a different document" button** — the other
  documents' boxes are already on the same screen (§5.5).
- **The "block the save" state on My Profile**, deleted rather than kept for comparison (§8).
- **"You will not be asked for a password" and "do not pass this on"** on the welcome
  screen, with nothing put in their place (§5.1).
- **The browser draft**, and its silent quota-failure state (§5.2).
- **v7:** a media query and a hand-picked breakpoint for the two tiles — `auto-fit` +
  `minmax` already is one. A fix to the seat page nobody asked for. A `justify-items: center`
  on the grid, which would have centred a lone tile and broken the left edge it shares with
  the heading and the cards above it.
- **v8:** a second layout mechanism for the right column — the existing grid cell plus a
  flex stack does it. A third grid column. Any rebalancing of the unequal columns: no
  `grid-auto-flow: dense`, no moving a card back, no equal-height trick. And an explicit
  order override (`order:`) for the reflow — source order is already the order I want, and
  a CSS order that disagrees with the DOM is an accessibility fault waiting to happen.

Nothing was kept on a "we will need it later" argument. **One thing I kept against my own
instinct:** the printed-slip shape, because it is what makes the words-password choice
coherent and it costs one prototype state.

---

## 12 · ⚠ DECISIONS — yours, with my recommendation

| # | Decision | My recommendation | Owner | Blocks |
|---|---|---|---|---|
| **D1** | **Must a joiner change the HR-issued password on first sign-in?** | **No.** The account lives days, opens one page, and shows nothing about anybody else; counsel's point — attribution to a named person — is met by issuing and logging it, not by rotating it. Forcing it is new code (J2) and one more wall at the moment the joiner is least committed. **Risk accepted and stated: whoever read the message can sign in once before she does.** | `hrms-security-privacy-engineer`, then Surbhi | The first-contact flow |
| **D2** | **May the username be a mobile number?** It needs a tenant-wide setting that changes sign-in for every employee, and two people sharing a number is undefined | Yes — it is the only identifier a frontline joiner reliably has. Name the side effect in the release note | `hrms-fullstack-engineer` + security | The message, the field label |
| **D3** | **A word-style password** (`tiger-lamp-74`) rather than a random string | Keep it, with a short life and a lockout. It is typed once from a text message on a cracked screen | Security | The invite |
| **D4** | **Can the sign-in page tell "this access has ended" from "wrong password"** without telling a stranger that a number belongs to a joiner here? | It must. Otherwise the correct password is called wrong and we lose the person. If it cannot, say so and I will redesign around it | Engineer + security | **P1 if the answer is no** |
| **D4b** | The **lockout threshold and duration** | Read them, then set the countdown wording to match | Engineer | §4.2 |
| **D5** | **Does Send end the sign-in, or only the form?** v5 let a joiner send a promised document later on the same link | I have built decision 4 as written (Send ends it). If you want the later photograph, say so — one sentence, one state | Surbhi | The Sent screen |
| **D6** | **Does the Aadhaar rule follow the declared type, or every image?** An Aadhaar sent in the PAN box skips masking today | Detect the number on **any** upload, or stop calling it a control. Not mine to decide | Security, then Surbhi | Whether J8 is a gap or a design |
| **D7** | **HR-only fields on the joiner form.** Decision 5 excluded them because there was no login. **There is one now** | Keep them excluded. The reason survives: the field-rights intersection is about what the *employee* may fill, and a joiner is not the employee yet | Security (the decision file asks them explicitly) | The picker's candidate list |

---

## 13 · Usability test plan — for the High-impact item

**One test, on the door, because it is the only screen where failure is silent.** Five
people who have never used Alvora: two frontline (limited English, cheap Android), one
office joiner, one person who reads slowly, one on a borrowed phone.

| Task | Success | What would change the design |
|---|---|---|
| You got this text message. Fill in your details | Signs in and reaches the first question **unaided, in under 2 minutes** | 2+ of 5 fail → the password format or the field labels change |
| (Password pre-mistyped) Something is wrong — fix it | Finds **Show the password** and corrects it | Nobody uses the reveal → it is in the wrong place |
| You filled some in yesterday. Carry on | Knows **what was kept** without asking | Cannot say what was kept → the strip or the step words are wrong |
| You have no Aadhaar card with you | Reaches "I will bring it" or another document **without stopping** | Anyone stalls → the refusal's three ways out are not readable |
| What happens to this if you do not join? | Can say "they delete it", roughly when, and who to ring | Cannot → the notice is in the wrong place |

---

## 14 · What the business analyst must turn into acceptance criteria

1. A joiner account is a **Website User** with one role that reads nothing, and **no
   `Employee` record is created**. Negative criteria: not in headcount, not on the
   organisation chart, no `Attendance` row, not counted as a paid seat.
2. **A signed-in joiner asking for any address other than the joining page gets the
   refusal screen** — never the employee portal, never Frappe's desk, never a raw 403.
   Tested through the ten doors in `data-doors.md`, as that login, on a fresh site.
3. **A refused sign-in never reveals** whether the username exists.
4. **"The access has ended" is a distinct outcome from "wrong password"** at the page (D4).
5. **A lockout screen exists**, names the time, and the error before it counts down.
6. **A draft survives sign-out, a closed browser and a different device**, until Send or
   the end date. Negative criterion: it is **not** read from the browser.
7. **Signing out leaves nothing about the joiner in the browser.**
8. **HR cannot invite** until both retention periods and an HR contact are set. The joiner
   screens read those three values and never a value of ours.
9. **The two retention clocks are two settings**, and the joiner screen prints both.
10. **Aadhaar: mask or refuse.** Masking runs **before** anything is stored; an uncertain
    result stores **nothing**; a refusal **never ends the session** and never consumes an
    attempt; the kept copy is the masked one and is shown back to the joiner.
11. **Send ends the access** (unless D5 reverses it). After Send, the sign-in returns the
    "finished its job" screen, not "invalid credentials".
12. **My Profile's save always succeeds** for otherwise-valid input, and missing required
    fields are marked `Needed` on every visit. This is 078 §17.9 criterion 7, resolved
    to (B).
13. **Everything in 078 §17.9 criteria 1–6, 8 and 9 stands**, with "the link keeps working"
    re-worded to "the session and the draft survive".
14. **Logged:** every joiner sign-in, every HR read of a submission, every export (ruling 9).

---

## 15 · The prototype

`C:/Surbhi-Git/hrlocal-data/prototypes/078-positions-faces/prototype-v7.html` — built from
v7 and v6. **Every earlier screen and state still works**; v1–v7 are kept
beside it. **Not published by me — the session that ran me publishes it.**

**Five things to look at, in this order:**

1. `0 · Getting in` → **Sign in — first time**, then **that did not work**, **locked for 30
   minutes**, **I cannot sign in**. This is the screen the slice turns on.
2. `0` → **What HR sends — a text message**, then **HR's side — what HR sees once**.
3. `7 · The joiner's form` → **Coming back — a second visit**, then **What happens to what
   I send**.
4. `7` → **Aadhaar — before you send it**, then **we could not cover the numbers**, then
   **kept, with the numbers covered**.
5. `8 · What this sign-in opens` → **They typed another address**.

**For v8, also:** `1 · My profile → Normal` on a wide window — two columns, with the
password card under the documents card on the right. Narrow the window or press Ctrl+ twice
and watch all three drop to one column in the order details → documents → password. Then
the two near-empty cases, which are the ones worth your eye: **A short right column** and
**Nothing to edit**.

Also fixed in v6, unasked: the review bar's Device / Theme / Words buttons never showed
which one you had picked.

---

## 16 · Where I could not check

- **Nothing was seen on a running site.** The joiner sign-in does not exist; every
  measurement is of the prototype in Chrome. Three findings (J1, J2, and the `auth.py`
  landing rule in §6.2) are read from code, not observed.
- **The lockout numbers, the Website User's exact behaviour at `/app`, and whether Frappe
  can distinguish a disabled account at the login page** are all unread.
- **Hindi is absent**, not machine-drafted (J10).
- **The masking's accuracy is unmeasured** (J9). If it refuses often, §5.5's refusal is not
  an edge case.
- The PP Jewellers names are real local-copy data; **Priya Khanna, her number, the password
  and the dates are invented and tagged `Sample`.**
