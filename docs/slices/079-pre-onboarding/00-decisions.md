---
slice: 079-pre-onboarding
artifact: 00-decisions
date: 2026-11-01
status: Surbhi's decisions, settled. Everything below is a given, not a question.
tickets: ALV-270 (the slice), ALV-215 (counsel, answered), ALV-268, ALV-277
---

# 079 · Pre-onboarding — the decisions everything else is built on

Slice 078 shipped the photographs, the mini profile and My Profile. The
pre-onboarding form shipped **switched off**, and this slice is the half that
was deferred on 31 October so 078 could go out.

Nobody on this slice re-opens a decision below. If one looks wrong, say so and
stop — do not design around it.

## 1 · How a new joiner gets in — **a login, no employee record**

Counsel's written advice (31 Oct) is that **a restricted login is much safer
than an expiring link**, because it identifies the person rather than trusting
whoever holds a URL.

Surbhi's decision, 1 Nov: **a restricted website login that can open one page
and nothing else. No `Employee` record is created.**

This is deliberately the third option, not the obvious one. A real `Employee`
record for somebody who has not started work would:

- count as a **billable seat**;
- appear in **headcount and the org chart** before the person exists;
- and, with a joining date in the past, make Frappe mark them **Absent for every
  day since** — a trap this project has already paid for once, and one that
  deleting the rows does not undo.

A login costs none of that and still satisfies counsel. **The bearer link is
replaced, not kept alongside.**

## 2 · HR marks fields required — **and we impose nothing of our own**

HR ticks which fields are required, on the same organisation settings screen
that chooses which fields appear. It applies to **the joiner form and My
Profile**. **Document types can be marked required too.**

Surbhi's standing rule holds: HR ticks the list, we add no mandatory-field list
of our own.

## 3 · My Profile refuses nothing — **save what is valid, keep asking**

If HR marks a field required and an employee's record lacks it, the employee's
save **still goes through**. The missing fields are marked `Needed` on every
visit.

The reason, which is the whole point: blocking would mean somebody with no
permanent address could never change anything on that page again — not even
their own phone number — and their only way out is a call to HR. A rule that
locks a person out of correcting their own record is worse than an incomplete
record.

**The joiner form still refuses an incomplete send.** Sending once as a
stranger and maintaining a record you live in are different situations.

## 4 · A joiner may come back — **until they press Send**

What they typed is kept. They can close the page and return to finish. The
access stays valid until they send or it expires. Cheap now, expensive to
retrofit.

## 4a · Send ends the form, not the sign-in — **and the refusal says which**

Two answers from Surbhi, 1 Nov, both reversing or settling an earlier reading.

**Send ends the form only.** The joiner stays signed in afterwards. This
reverses §4's "the account dies at Send", and the reason is the case the
designer named: somebody who finds their PAN card the next evening should not
have to ring HR. What they already sent is sent; they can still add a document
or correct something until the access expires.

So **the access ends on its own expiry date, or when HR ends it** — not on
Send. If the person is hired, the pre-onboarding account must be **closed, not
promoted**: their real staff login is a separate thing, and promoting this one
would lock the new employee out of their own record.

**The sign-in page may say "your access has ended" rather than "wrong
password".** Design decision D4, and the right call: a joiner typing the
*correct* password a day late, told they got it wrong, tries again, gets locked
out, and we lose them.

The trade, stated once so nobody rediscovers it as a finding: this tells
somebody holding the credential that an account existed and has ended. That is
a small disclosure about a person HR already chose to contact, by a credential
HR handed over by hand. It is worth it. The refusal still names no person, no
employer detail and no reason beyond the state.

## 5 · The joiner's field list — **its own tick, shipping empty**

One candidate list of fields, ticked twice: once for My Profile, once for the
joiner form. The joiner's tick **ships empty**, so nothing is asked of anybody
until a tenant deliberately ticks it.

**HR-only fields are excluded** from the joiner form. The reason is not
squeamishness: the permission-level intersection that stops self-service
bypassing field rights **does not exist on a path opened without a login** — so
asking a stranger for a field the employee themselves may not fill defeats a
control rather than widening a list. (Re-read this one against decision 1: the
joiner now HAS a login. The security engineer must say whether that changes the
answer. Until they do, HR-only stays excluded.)

## 6 · No typed statutory field — **a photograph of the card instead**

Nothing will read a PAN or Aadhaar number as data, so no such field is offered.
The need is met by the document upload, which HR can mark required. The deny
rule refuses statutory identity number fields in the setter and again in the
reader.

## 6a · Aadhaar — accepted, and we build the masking ourselves

Surbhi's decision, 1 Nov, taken against the security engineer's recommendation
and with the cost named: **we accept an Aadhaar image and black out the first 8
digits ourselves.** The alternatives — refusing Aadhaar, or asking the joiner to
mask it themselves — were put to her and declined.

This is the only option that actually satisfies counsel's ruling 5, and it is
the most work by a distance.

**The one rule that makes it safe, and it is not negotiable: mask or refuse.**

- The masking runs **before anything is stored**. The original never reaches
  disk, not even briefly, and not in a temporary file that a failure leaves
  behind.
- If the process cannot find and cover the digits **with confidence**, the
  upload is **refused** in plain words, asking for a different document. It is
  never stored unmasked "so HR can sort it out".
- The failure that matters is not a refused upload. It is **storing an
  unmasked Aadhaar while believing it was masked.** Every design choice breaks
  towards refusing.
- A refusal must not burn the joiner's access, and must leave them a route:
  another document type, or "I will bring it on my first day".

Alternative IDs (PAN, passport, driving licence, voter ID) are still offered
and are still the easier path for everybody. Counsel's ruling that Aadhaar is
**voluntary with alternatives accepted** holds regardless.

## 6b · Four more, settled 1 November after the spec

**The Aadhaar masker is HELD, not cancelled.** US-11 and US-12 — 13 of the
slice's 83 points, and its largest single piece of work — wait for counsel's
two written answers: may an employer ask for an Aadhaar card at all before
employment, and does the card's QR code carry the full number anyway. Nothing
else waits on them, because the Aadhaar document type is only a tick. If the
answer is no, we will not have built the biggest thing in the slice for
nothing. **Build the other 23 stories now.**

**Sign-in by mobile number is ON.** The joiner's username is the mobile the
employer already reached them on. This needs Frappe's tenant-wide
`allow_login_using_mobile_number`, so **every employee at that tenant can then
also sign in with their mobile number** — a change made for the joiners' sake
that reaches everybody. Surbhi chose it with that named. The login id itself
stays opaque and non-routable (079-SEC-1); the number lives on
`User.mobile_no` and Frappe resolves it.

**My Profile offers the six fields the code allows, not the sixteen the
prototype drew.** The drawing was wrong, not the code: the extra ten include
**bank account and IFSC**, and offering those would give an employee
self-service write on their own bank details, which is how payroll fraud
happens. Correct the prototype, not the allow-list. Widen later case by case if
HR asks, each considered on its own.

**The two-column My Profile ships in this slice**, even though it changes a
page already live in production. It is Surbhi's own fix to a real fault — a
1280 px box for a ten-digit phone number — and shipping it here means one
change and one test pass rather than two.

## 6c · Three more, settled 2 November

**The Aadhaar masker is dropped. Guidance replaces it.** Surbhi, 2 Nov: *"as per
the counsel we can show some guidance on the form about the correct way of
sharing masked Adhaar card."* So the form tells the joiner how to mask the card
themselves before uploading, and US-11 and US-12 are not built at all.

**This reverses her own decision of 1 November**, recorded in §6a, which
declined exactly this option — "asking the joiner to mask it themselves" was
put to her and declined, and the masker was chosen *against* the security
engineer's recommendation with the cost named. One day later the cost is no
longer worth paying. That is a legitimate change of mind and it saves the
slice's largest piece of work, 13 of 83 points. It is written down so nobody
re-reads §6a as current.

**What it does NOT do, stated plainly because §6a's rule was "mask or
refuse".** Guidance is an instruction, not a control. A joiner who ignores it
uploads an unmasked Aadhaar and we store it — the precise failure §6a said
every design choice must break away from. Guidance plus the alternative IDs is
the mitigation; there is no refusal behind it.

**So one question goes to counsel, and it is new:** does guidance on the form
satisfy ruling 5, which says the first 8 digits are *masked on the uploaded
image*? Our reading is that an instruction is weaker than a control, and we
would rather be told so now than after a card lands. Added to the 1 Nov letter.
**ALV-215 still gates switch-on.**

**Export logging is deferred, not solved.** Surbhi, 2 Nov: *"ok we can pick it
up later."* The consequence, once: **counsel's ruling 9 is not met.** `log_level`
is unset, Frappe defaults to ERROR outside a dev server, and all 16
`logger("alvoraa")` calls — the export line included — are discarded. Until it
is set, **nobody may tell a customer or a security questionnaire that exports
are logged**, because they are not.

**Hindi: the privacy notice needs no translation from us, and this was the
cheap discovery.** Surbhi asked for Hindi "for the privacy notice for now". The
notice is **already the employer's own typed text** — `alvoraa_joiner_notice_text`,
a per-tenant default, and `joiner_public.py:266-274` **refuses to render the
screen without it**. So a tenant may type it in Hindi today, with no build at
all. That is counsel's ruling 6 working as intended: the notice belongs to the
employer, so the language does too. What is owed is a test that Devanagari
survives save and render, and telling HR they may.

The rest of the journey — about **151 strings**, 41 server-side and 110 on the
page — is already wrapped for translation, with **nothing hardcoded**. The
plumbing exists; only a reviewed `hi.csv` is missing. That stays ALV-267.

## 6d · Aadhaar, settled 2 November — and it goes against counsel

Three answers from Surbhi, given as answers to the three questions drafted for counsel.
**They replace §6a and §6c's Aadhaar paragraphs. Those are no longer current.**

**1. Aadhaar is MANDATORY.** Her words: *"Aadhaar is mandatory."* Said twice, the second
time after being shown that **counsel's ruling 5 says the opposite** — voluntary, with
alternative IDs accepted. Her decision, recorded as hers.

**This needs no code.** The product already lets HR tick any document type as required
(§2). So "mandatory" is a **tenant configuration choice**, taken by the employer as Data
Fiduciary, and we supply the switch. **Nothing hard-codes Aadhaar as required for every
customer, and nothing should** — that would make the choice ours rather than theirs, and
would impose it on tenants who have taken no such decision.

**Counsel's ruling 5 stays in §7 exactly as written.** It is not deleted, softened or
re-worded. If this is ever questioned, the record must show that the ruling was on the
table and a decision was taken against it, not that nobody noticed.

**A basis that may make it lawful, which we cannot assess.** EPF enrolment requires
Aadhaar seeding for a UAN, so an employer can have a genuine statutory reason to insist.
If that is the basis, counsel can confirm it in a line. Question 1 of the 1 Nov letter
now asks exactly this.

**2. The uploaded card is the MASKED Aadhaar.** Her answer to "does the QR carry the full
number" was *"masked"* — read as: the joiner uploads **UIDAI's own masked Aadhaar**, the
download where the first eight digits are already hidden.

**This is the best answer of the three and it is better than what §6a chose.** The
masking is done by UIDAI, not by us and not by the joiner with a pen; there is no
judgement call and nothing for us to get wrong; and the digits are masked **on the
uploaded image**, which is the wording of ruling 5.

**3. Guidance is enough.** Her words: *"yes enought."* So the form tells the joiner to
download their masked Aadhaar from UIDAI and upload that. **We build no masker.** US-11
and US-12 are **dropped**, not held — 13 of the slice's 83 points.

**The weakness, stated once so it is not rediscovered as a finding:** guidance is an
instruction, not a lock. A joiner who ignores it, or who photographs the plastic card,
uploads an unmasked number and we store it. Nothing refuses such a file. §6a's rule was
"mask or refuse"; there is now neither.

**4. The QR question is answered, and it holds — with one trap.** Surbhi, 2 Nov: the
masked card's QR carries *"just last 4 digits"*. Checked against UIDAI's own
**Aadhaar (Authentication and Offline Verification) Regulations 2021**, which define the
Aadhaar Secure QR Code as digitally signed data holding the **last four digits**, plus
demographics and photograph. So the masked download really is masked, QR included, and
answer 2 stands.

**The trap: OLDER Aadhaar prints used QR formats that could hold the full number in
plain text.** So a joiner who photographs an old physical card can hand us the twelve
digits through the QR even though the printed digits are covered. Masking the print is
not the whole of masking on an old card.

**What that means for the guidance, and it is the difference between working and not:**
the words must say **download the masked Aadhaar from UIDAI**, not "cover the digits on
your card". A photograph of a covered old card can still carry the number. The guidance
has one job and this is it.

Sources: UIDAI's regulations (the definition of Aadhaar Secure QR Code) and secondary
guides on the current format. No direct UIDAI page stating the current QR contents was
found; the regulation definition is the strongest evidence. Counsel's Question 2 is
answered for our purposes but is worth their confirmation.

## 7 · Counsel's rulings, 31 October — all binding

| # | Ruling |
|---|---|
| 1 | The employer is the **Data Fiduciary**; we are the **Data Processor** |
| 2 | A **restricted login** is much safer than an expiring link — see decision 1 |
| 3 | A non-joiner's **record**: keep **180–365 days** |
| 4 | A non-joiner's **identity document**: delete **much sooner, 30–60 days** |
| 5 | **Aadhaar** must be voluntary, alternative IDs accepted, and the **first 8 digits masked on the uploaded image** |
| 6 | The **privacy notice belongs to the employer** — exact purpose, retention periods, their own HR contact |
| 7 | An expiring link is legally acceptable; a one-time code makes it much more secure |
| 8 | No public self-service portal needed, but HR must be able to **export or purge** a candidate's data on request |
| 9 | **Unmasked exports to super-admins only**, sensitive IDs masked by default, **every export logged** |

**Two retention clocks, not one.** The build has a single setting and cannot
express both. This is the largest piece of work counsel's answers create.

**Aadhaar masking is image work**, not a configuration flag.

**Two written answers still to come**, and they gate switching the form on at a
tenant with real joiners, not the build: whether the 180–365 range still applies
when the row holds a statutory **document** for somebody never employed, and
Aadhaar's own statutory regime. An image of an identifier is still the
identifier.

## 8 · What already exists and is not to be rebuilt

- `prototype-v5.html` and `01b-ux-design.md` §17 — the required tick, the tags,
  both refusal screens, the "I'll bring it on day one" answer for a required
  document. **Surbhi has not yet reviewed v5.**
- `01c-security-privacy-requirements.md` and its 31 Oct addendum — SEC-17, 18,
  19 and PRIV-10 to 14, written for the link design. **Decision 1 changes their
  premise.**
- The joiner form itself, shipped off: three guest endpoints, the submission
  doctype, the housekeeping job, HR's invite and export and purge.

## 9 · Known defects carried in from 078

- **R11** — HR Manager can export joiner submissions **unmasked** and nothing is
  logged. Counsel's ruling 9 now makes this a requirement, not a nicety.
- **No record that HR read a submission**, and **a misused link is
  undetectable**. Detection is the gap, not prevention.
- The joiner page is **English only** (ALV-267), against the product's
  English–Hindi parity rule for the frontline journey.
