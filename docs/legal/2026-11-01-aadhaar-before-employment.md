# Two questions about the Aadhaar card, before we build the masking

## A short follow-up to your advice of 31 October 2026

| | |
|---|---|
| **For** | Alvoraa's external legal reviewer |
| **From** | Alvoraa's security and privacy engineer, for Surbhi (founder, interim compliance owner) |
| **Date** | 1 November 2026 |
| **Status** | **A request for two short answers. Not legal advice, and nothing here is settled.** |
| **What we need back** | A yes or no on each of the two questions in section 3, with a sentence of reasoning. |
| **Why now** | Your ruling 5 asks us to mask the first eight digits on the uploaded image. That is the largest single piece of engineering in the work we have in hand, and we have **held it** rather than build it. Both answers below change what we build, or whether we build it at all. |

---

## 1 · What we are building, in four lines

A person the employer has chosen to contact, but has **not yet employed**, signs in to one
page and fills in their own details before their first day. They may upload a photograph of
an identity card. Nobody types an Aadhaar number anywhere: there is no field for it, by
design. The only Aadhaar data we would ever hold is **a picture of the card**.

We are the Processor. The employer is the Fiduciary. Nothing is switched on at any customer
today, and no candidate has ever submitted anything, so we are still choosing the rule
rather than explaining a past choice.

## 2 · What we have done with your ruling 5

We accepted it in full and chose the hardest reading of it. Our rule is **mask or refuse**:

- the masking runs **before anything is written to disk** — the unmasked original never
  reaches storage, not even briefly, and not in a temporary file a crash could leave behind;
- if the software cannot find and cover the digits **with confidence**, the upload is
  **refused** in plain words and the person is asked for a different document. It is never
  stored unmasked "so HR can sort it out later";
- the failure we are designing against is not a refused upload. It is **storing an unmasked
  Aadhaar while believing it was masked.**

PAN, passport, driving licence and voter ID are all offered and are the easier path for
everybody. Your ruling that Aadhaar is voluntary with alternatives accepted holds whatever
the answers below are.

## 3 · The two questions

### Question 1 — may the employer ask for an Aadhaar card at all, before the person is employed?

Our reading is that it may be asked **voluntarily, with alternatives genuinely accepted**,
and that there is no lawful basis to require it from somebody who is not yet an employee —
the employment purpose has not begun. We have assumed that and built accordingly.

*What we need:* confirmation, or a correction. If the answer is that it may not be asked
before the employment relationship exists, we will **not offer the Aadhaar document type on
this page at all**, and the masking work disappears.

### Question 2 — does the card's QR code carry the full Aadhaar number?

This is the question that may change the shape of the control rather than its size. Modern
Aadhaar cards and e-Aadhaar PDFs carry a machine-readable code. **If that code contains the
full twelve digits, then blacking out the first eight printed digits leaves the whole number
legible to anyone with a phone, and the masking achieves very little.**

We have not verified this ourselves and will not guess at it, because the answer decides
between three quite different pieces of work:

| If the code carries | Then masking means |
|---|---|
| Nothing identifying | Cover the eight printed digits. What we planned. |
| The full number | Cover the printed digits **and destroy or cover the code** — a different and harder problem, and one that damages the document's own usefulness |
| We cannot tell reliably | **Refuse Aadhaar images entirely** and rely on the alternative IDs, which we already accept |

*What we need:* whether, in your view, masking the printed digits satisfies the obligation
when a machine-readable code may still carry the number — and if not, which of the three
rows above we should build to.

## 4 · One thing we are not asking you to decide

Whether to accept Aadhaar at all is the founder's commercial decision, and she has taken
it: we accept it, and we build the masking ourselves. We are asking only what the law
requires of that masking, and whether the question arises before employment at all.

## 5 · Still outstanding from 31 October

Your two written answers on retention are still awaited and still gate switching this on at
a customer with real candidates:

- does the **180–365 day** range for a non-joiner's record still apply when the row holds a
  statutory **document** for somebody never employed, and
- Aadhaar's own statutory regime, including whether any of it binds us as Processor.

An image of an identifier is still the identifier, which is why we have asked twice.
