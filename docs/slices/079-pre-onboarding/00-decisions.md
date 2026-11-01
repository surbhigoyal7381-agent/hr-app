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
