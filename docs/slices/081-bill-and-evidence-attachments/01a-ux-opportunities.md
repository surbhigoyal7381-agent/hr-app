# Slice 081 — UX opportunities scan

**Author:** `hrms-ux-designer` · **Date:** 3 November 2026 · **Mode:** opportunities scan
**Status:** for the product brief and the design gate. **No prototype in this mode** — the
clickable prototype comes at the design step (`01b`), as principle P6 requires.

**Read first:** `01-product-brief.md` in this folder. Every product decision in it is
settled and **nothing here reopens one.** Where I disagree with the brief it is about
*mechanism and wording*, and it is marked **⚠ DECISION** with a named owner.

**Bad news first, three things.**

1. **The reviewer's bill will not render.** The ALV-287 document viewer the brief tells us
   to reuse sits at `z-index: 1250`. The approver's decision sheet, where the decision
   actually happens, sits at **1300**. Reused as it stands, the bill opens *behind* the
   sheet and the approver sees nothing. **Measured in the stylesheet, not guessed**
   (`panels.css:712` and `:3064`). One number fixes it; unnamed, it is found in test.
2. **An iPhone bill is refused today.** Our one server-side image path refuses HEIC on
   purpose, because Pillow in this image cannot read it (measured, `employee_photo.py:22`).
   On a *mandatory* field that is not an inconvenience, it is a wall — the exact failure
   §3.2 of the brief set out to avoid.
3. **The 1 MB cap cannot be set the way the brief's release list says.** Frappe's
   `max_file_size` is **whole megabytes and site-wide** (`frappe/core/api/file.py:85-90`,
   read in the running container). Set to 1, it refuses the agreed 3 MB PDF and shows a
   framework sentence — *"File size exceeded the maximum allowed size of 1.0 MB"*
   (`file.py:885`). The two caps have to be ours.

**Evidence honesty.** I could not reach a local site from this session: the containers are
up (`hrlocal-078`, `hrlocal-297` and others) but every HTTP probe to `127.0.0.1:8078`,
`:8297` and `:8010` returned no connection — almost certainly this session's sandbox, not
the bench. **So every finding below is labelled `read in code`, not `seen on screen`, and
there are no screenshots.** Nothing in this scan rests on a layout I only imagined; the
three numbers that matter (z-index, `max_file_size`, HEIC) come from source I read.

---

## 1 · Frame

A **driver at DTC**, at a petrol pump, in daylight, on a cheap Android phone on 3G, has
just paid ₹420 of his own money. He has thirty seconds and one hand free. He needs the
claim to leave his phone with the bill attached, and he needs to know it went.

And a **line manager**, between two things, needs to decide that claim in one tap without
asking anyone a question.

**Personas in scope:** frontline employee (primary), employee, line manager / expense
approver, HR manager (as the regularization reviewer and as the Desk filer of a claim
with no receipt).
**Deliberately out:** CXO — the brief gives them nothing here. See **AQ2**: the product
does not currently agree with that.

---

## 2 · Current state — read in code

All line numbers are in this worktree (`.claude/worktrees/078-positions-faces`).

### 2.1 The expense claim, employee side

| Fact | Where | Label |
|---|---|---|
| The modal has Expense Type, Expense Date, Amount, Purpose. **No file control.** | `templates/includes/ess/parts/request-modals.html:65-99` | Confirmed |
| Required fields are marked with an **asterisk only** (`Expense Type *`) | same | Confirmed |
| The send has **three designed failure states** — refused (inline, server's own words), offline (*"We could not reach the office. Nothing was sent."* + **Try again**), and no-answer (*"It may have gone through. Look in your list"*, Try again removed) | `portal.js:10033-10095` | Confirmed |
| **There is no duplicate guard on the server** for an expense claim — slice 070's own note, in the code | `portal.js:10047-10050` | Confirmed |
| The employee's own list shows remark, date, status, amount, and a decline reason. **No file.** | `portal.js:9946-9960` | Confirmed |

### 2.2 The regularization, employee side

| Fact | Where | Label |
|---|---|---|
| `acForm()` is a reason `<select>`, a help line that changes with the reason, a free-text box, and two buttons. **No file control.** | `portal.js:6141-6158` | Confirmed |
| It renders **inside a table cell in the day row** (`</div></td></tr>`), opened by `acToggle(date)` — a narrow, vertically cramped space on a phone | `portal.js:6100-6112`, `6141` | Confirmed |
| The person's own request card shows reason, dates, state, HR's note, their explanation. **No file.** | `acReqCard`, `portal.js:6233` | Confirmed |
| A regularization is reviewed by the employee's **own manager** and by HR. No routing by reason — a fixed reason list plus free text | `attendance_correction.py` `_reports_to` | Confirmed (brief §3.4) |

### 2.3 The reviewer's side — and the brief's "queue row" is not a row

This is the half most likely to be built wrong, so it is worth being exact.

| Fact | Where | Label |
|---|---|---|
| The expense approver decides in a **bottom sheet** reached from the Home "Pending for you" card — not on a list page. The sheet shows amount, type, date, the note, how long it has waited, then Approve / Decline-with-a-reason | `hmExpenseSheet`, `portal.js:6657-6680` | Confirmed |
| The sheet already says the act is final: *"Approving passes it to accounts for payment. You cannot take it back here."* | `portal.js:6667` | Confirmed |
| **The queue row is a `<button>`** (`hm-row`, one element, three spans) | `hmPendRowHtml`, `portal.js:6585-6591` | Confirmed |
| The sheet overlay `.hm-ov` is **z-index 1300**. The ALV-287 viewer `.mpf-dv` is **1250**. The employee's modal `.gp-backdrop` is 1200 | `panels.css:712`, `:3064`, `:1489` | **Confirmed — measured** |
| A **system manager (CXO)** gets one row per kind, and for expense claims that row *"opens the oldest"* — i.e. an individual claim's sheet | `portal.js:6538`, `6625` | Confirmed |
| HR's regularization queue is a list of up to 100 plain cards with Approve / Decline, built in `acReviewQueue`. No file, and no per-row action beyond the decision | `portal.js:~6280-6300` | Confirmed |
| The approver's server-side queue returns name, employee_name, expense_type, expense_date, amount, note, waiting_since. **No file** | `inbox_api._part_expense_approvals:565-609` | Confirmed |

### 2.4 The upload machinery we are told to reuse

| Fact | Where | Label |
|---|---|---|
| `uploadMyDocument` posts to Frappe's generic `/api/method/upload_file`, then records the url. **It reports failure with `alert()` and the literal words "Upload failed"** — the exact wording the brief bans | `portal.js:5122-5146` | **Confirmed** |
| The same card's **View is a raw `<a href="<file_url>" target="_blank">`** — a private-file address handed straight to the browser, which is what ALV-287 removed elsewhere | `portal.js:5083` | Confirmed |
| The ALV-287 viewer is **welded to the Positions mini profile**: its endpoint is `employee_documents_read.open_employee_document` keyed by a *document row*, its blob url is revoked when the profile closes, and its state is the single global `MPF_DOC` | `portal.js:11060-11200` | Confirmed |
| Client-side resize **already exists in this product**: the field check-in page draws the frame to a canvas at **width 480** and re-encodes **JPEG quality 0.6** | `www/field-checkin.html:718-724` | Confirmed |
| The closest two-button file pattern also exists: the joiner form offers **"Take a photo"** (`capture="environment"`) beside **"Choose a file"**, uploads **one file at a time, separately from the form submit**, with a per-item status line | `www/joining.html:503-546` | Confirmed |
| Server-side image handling refuses **HEIC rather than converting it** — Pillow 12.3.0 here has no HEIC reader (measured, 078). Accepted: JPEG, PNG, WEBP, checked by **magic bytes**, not extension | `employee_photo.py:22-26, 98-137` | Confirmed |
| Re-encoding a 10.5 MB source costs **~240 ms of CPU inside the request**, in one of 8 gunicorn slots (measured, OPS-42) | `employee_photo.py:370` | Confirmed |
| Frappe's `max_file_size`: System Settings value **× 1024 × 1024**, else `site_config`, else **25 MB**. Whole MB, site-wide | `frappe/core/api/file.py:85-90` (read in `hrlocal-078`) | **Confirmed** |

---

## 3 · Benchmark — labelled

Whole-product read, not one screen. **No trial accounts**, so these are what each company
publishes.

| Product | What it does with a receipt | Label |
|---|---|---|
| **Zoho Expense** | Up to **5 receipts per expense, 10 MB each**. Also has a *"receipt required limit"* — a receipt becomes mandatory only **above an amount threshold**. AutoScan reads the receipt and pre-fills the expense | **read**, zoho.com help centre, 3 Nov 2026 |
| **Keka** | PDF, JPG, PNG, JPEG. *"Typically up to 5 MB per file"*, and the limit *"may vary by organisation policy"*. Warns against password-protected PDFs | **read**, help.keka.com, 3 Nov 2026 |
| **SAP Concur** | 5 MB per receipt image; mobile capture is the headline flow | **read**, university help pages, 3 Nov 2026 |
| **ApprovalMax** | 10 MB per file | **read**, 3 Nov 2026 |
| **Frappe HR (our own stack)** | Standard Desk attachment sidebar on any saved document. Nothing receipt-specific | Confirmed (brief §1.1) |
| **Darwinbox, HiBob** | Attach receipts to a claim | `[recall — verify]` |

**The number that matters: our 1 MB stored cap is the tightest in this market by 5–10×.**
That is not an argument against it — it is a measured statement that **the whole burden
falls on the compress-first step**, and that a design which sends the camera's raw file to
the server and hopes will fail. It also makes the brief's kill criterion (§16) the right
first test.

**Legibility, since the brief leaves the number to be set.** Document-imaging guidance
converges on **200 dpi as a floor and 300 dpi as the comfortable figure for printed
receipts and invoices**, with small print needing more (**read**, several university
finance and scanning-vendor guides, 3 Nov 2026; I found no binding standard). My
recommendation is in **EC6**.

**What we will deliberately not copy, and why it is better for a DTC driver:**

- **No receipt gallery and no multiple files.** One bill, one tap. A gallery is bytes and
  taps a 2 GB phone on 3G pays for and nobody at DTC asked for.
- **No OCR / AutoScan.** The person is standing at the pump and knows the amount. An AI
  guess at a number that moves money has to be checked anyway, so it buys nothing and
  costs trust.
- **No amount threshold for "receipt required"** (Zoho's model). Settled: mandatory
  always. Recorded here only so nobody proposes it as a kindness later.
- **No 5–10 MB cap.** We compress instead. Their cap is generous because they do nothing
  to the file; ours is tight because we do.

---

## 4 · Findings

`P0`–`P4` is the release-blocking ladder. Every item is `read in code`.

| ID | Finding | Impact | Kind | Size | Severity |
|---|---|---|---|---|---|
| **AQ1** | **The viewer renders behind the decision sheet.** `.hm-ov` 1300 > `.mpf-dv` 1250. The approver taps "View bill" and sees nothing | High | Fix | S | **P1** |
| **EC4** | **HEIC is refused by our only image path** (measured, no Pillow reader). On a mandatory field that is a wall for every iPhone filer, and "take it again" does not help — the phone will produce HEIC again | High | New | M | **P1** |
| **EC1** | No file control on the expense modal; `apply_expense_claim` takes no file | High | New | M | **P1** |
| **AR1** | No file control on the regularization form, and no notice | High | New | M | **P1** |
| **AQ5** | No file on the approver's queue payload; HR's regularization queue the same. **An attachment nobody reviewing can open is not a feature** | High | New | M | **P1** |
| **EC2** | **The chosen file must survive "Try again".** The modal's offline state promises *"Your details are still here"*. A file that silently drops breaks that promise and makes a 3G blip cost a second trip to the pump | High | New | S | **P1** |
| **UP1** | The upload path we are told to reuse fails with `alert("Upload failed")`, and its underlying endpoint answers with Frappe's *"File size exceeded the maximum allowed size of 1.0 MB"*. **Reusing it as-is ships the banned wording** | High | Fix | S | **P1** |
| **EC3** | **One call or two.** With no duplicate guard, the "no answer — it may have gone through" state re-sends the whole photo. Upload the file first, post the claim with its url: the retry then costs ~1 KB | High | Improve | M | **P2** ⚠ |
| **EC5** | The 1 MB cap cannot be expressed in `max_file_size` (whole MB, site-wide) without refusing the agreed 3 MB PDF. Caps belong in our endpoint; `max_file_size` stays a generous backstop | High | Fix | S | **P2** |
| **AQ2** | **A system manager's Home row "opens the oldest" expense claim** — so a CXO lands in a single claim's sheet and would open its bill. Brief §9 says CXO: *"No. Summaries only."* The product already disagrees; the attachment turns that into a privacy question | High | Fix | S | **P2** ⚠ |
| **EC6** | The resize width is unset, and it is the number the kill criterion tests. **Recommendation: long edge 1600 px, JPEG quality 80, and step the *quality* down before the *width*** | High | New | S | **P2** |
| **EL1** | The employee cannot see the file on their own claim. **After compression they are the only person who can tell whether their own bill is readable** — and that is also the cheapest instrument for the kill criterion | Medium | New | S | **P2** |
| **AQ3** | Reuse the ALV-287 viewer — but it is welded to the mini profile (its own endpoint, its own revoke owner, one global). Generalise to *(blob, name, who revokes it)*. **One viewer, three callers, no new component** | Medium | Improve | M | **P2** |
| **AQ4** | Opening a 1 MB bill on 3G is seconds. `mpfOpenDoc` disables the button and says nothing on screen until it fails. Needs a visible "Opening the bill…" state — and the viewer must come **before** the irreversible Approve | Medium | Improve | S | **P2** |
| **HQ1** | HR's regularization cards need "Evidence attached · View" and nothing else. **No thumbnails in the list** — 078's deliberate rule, and a 100-row queue of images is a phone killer | Medium | New | S | **P2** |
| **AR2** | The regularization form lives in a table cell in a day row. The notice plus two buttons need the vertical space designed at 360 px and at 200% text, or the Send button leaves the screen | Medium | Improve | S | **P3** |
| **EC7** | Required is marked with an asterisk today. The new control says it **in words** — "Photo of the bill · required" — not with a symbol | Low | Improve | S | **P3** |
| **AR3** | The employee's own request card shows no file either. Same one-line fix as EL1 | Low | New | S | **P3** |
| **UP2** | My Documents' View is still a raw private-file `href`. **Not this slice's job** — but the two new surfaces must not copy that line | Low | Keep out | — | **P3** |
| **KEEP** | `submitExpenseClaim`'s three failure states, the server's own words reaching `ec-error`, Decline-with-a-reason reaching the employee's list, the reason-help line on the regularization form, "no thumbnail in a list", and ALV-287's "shown so you do not have to save a copy". **All good, all reused, none re-litigated** | — | Keep | — | — |

---

## 5 · The opportunities, persona by persona

The PM decides which of these the slice takes. Each one is small and each one is in
service of a job already in the brief.

| # | Persona | The opportunity | The job it serves | Evidence | Size |
|---|---|---|---|---|---|
| **O1** | **Frontline employee** | **Shrink the picture on the phone, before it is sent.** A canvas re-encode (the field check-in page already does one) turns a 4 MB camera file into ~400 KB, and the browser's own decoder turns an iPhone HEIC into a JPEG on the way | Claim at the pump in 30 seconds on 3G | `field-checkin.html:718`; HEIC refused server-side (`employee_photo.py:22`); 240 ms server CPU per raw photo (OPS-42) | M |
| **O2** | Frontline employee | **Two buttons, not one input: "Take a photo of the bill" and "Choose a file".** The camera one carries `capture="environment"` — the back camera, which is the one pointing at the bill | One tap to the right camera | `joining.html:504-519` | S |
| **O3** | Frontline employee | **Show the shrunk picture back, with its size, before Send.** "Bill attached · 380 KB · Replace". A person who can see it is blurred retakes it for free; nobody downstream can | The approver gets a readable bill first time | Learnings: "keep the captured photo across a retry" (008) | S |
| **O4** | Employee | **Carry the file through the retry states.** Offline → Try again keeps the picture. No-answer → "Look in your list" is unchanged | A 3G blip never costs a second trip | `portal.js:10080-10095` | S |
| **O5** | Employee | **"No bill? Ask HR to file this claim with your signed statement of what you spent."** One grey line under the control, **always shown** — not a message you only meet once you are stuck | The autorickshaw fare does not cost the driver his money | Brief §3.1a; learnings: "ask what happens to the person who cannot comply" | S |
| **O6** | Employee | **Open your own bill from your own claim row** — the same viewer, the same words | "Did my photo come out readable?" | EL1, AR3 | S |
| **O7** | **Line manager / approver** | **"Bill attached" as words in the row; "View bill" as a button in the sheet, above Approve.** Never a link inside the row — the row is a `<button>`, so that would be a button inside a button and unreachable by keyboard | Decide in one tap without asking | `hmPendRowHtml:6585`; WCAG 2.2 AA | S |
| **O8** | Line manager | **"Opening the bill…" on the button, and a failure that says what to do** — not a silent wait on 3G | Trust that the tap worked | `mpfOpenDoc:11060` | S |
| **O9** | Line manager | **No bill? Say so in the row, in words:** "No bill attached" on a claim filed before this ships. An empty "View" is worse than an honest absence | Old claims stay decidable (brief §3.1) | Brief §3.1 | S |
| **O10** | **HR manager** | **"Evidence attached · View" on the regularization card, and nothing else.** No thumbnails, no gallery, no bulk open | Decide 100 requests without a 100-image page | HQ1; 078's rule | S |
| **O11** | HR manager | **Desk's refusal names the escape:** "Where there is no bill, attach the employee's signed statement of what was spent and why there is no bill." HR is the only person who can use §3.1a, so HR is the only person who should read that sentence | The rule stays absolute and nobody is trapped | Brief §3.1a | S |
| **O12** | **Employee, regularization** | **The notice, in plain grey text directly above the two buttons** — a fact, not a warning badge. §6 below | "Optional" becomes an informed choice | Brief §3.4 | S |
| **O13** | Everyone | **One document viewer, three callers.** Generalise ALV-287's `mpfShowDoc` instead of writing a second popup — and fix its z-index so it is above the sheet | A bill looks like a document, everywhere | AQ1, AQ3 | M |
| **CXO** | — | **Nothing.** But see **AQ2**: today the product hands them an individual claim | — | `portal.js:6538` | — |

**What changes for the three CLAUDE.md personas**

- **Employee:** gains a camera button, a picture they can check, and a claim that is
  decided days sooner. Pays one new obstacle — a claim without a bill cannot be sent — and
  O5 is the sentence that keeps that from becoming a loss.
- **HR Manager:** gains evidence attached to the record for audit, in the Desk sidebar for
  free. Pays two documentation duties: the two-step expense-type setup (brief §1.4) and the
  self-declaration route (§3.1a). **Neither is code, and both fail silently if nobody tells
  HR.**
- **CXO:** nothing by design. **⚠ AQ2 says the code does not agree.**

---

## 6 · The three pieces of copy

Substance is settled; these are my words. Hindi drafts are **machine drafts and need a
native reviewer** before they ship (standing open item in `ux-learnings.md`). EN/HI parity
on employee-facing surfaces is an NFR, not a nicety (`nfr-budget.md` §7).

### 6.1 The regularization notice — before the person chooses a file

> **Your manager reads this request, and will see any file you attach. Attaching one is
> your choice — HR can fix the day without it.**

**हिंदी [machine draft — needs native review]:** आपका यह अनुरोध आपका मैनेजर पढ़ता है, और
आप जो फ़ाइल लगाएँगे वह उन्हें भी दिखेगी। फ़ाइल लगाना आपकी मर्ज़ी है — इसके बिना भी HR आपका
दिन ठीक कर सकता है।

Why these words:

- **Two facts, no advice.** Who reads it, and that it is optional. Nothing tells the person
  what to decide — the brief's principle is that we respect their judgement rather than
  overriding it.
- **The second sentence is what makes the first fair.** A notice that says only "your
  manager will see this" reads as a warning against attaching anything, and HR loses
  evidence it needs. Saying the request works either way is the escape, in the same breath
  as the limit (learnings: *"say the limit of a promise in the same breath as the
  promise"*).
- **"reads this request"**, not "can see" — it is not a possibility, it is what happens.
- **Placement and weight:** plain grey hint text (`gp-hint`), directly above the two
  buttons, inside the same block. **Not a coloured callout.** A warning-coloured box on an
  optional field is a nudge away from giving HR the punch slip, and the brief is explicit
  that this is transparency, not protection.
- **Not in a help panel, not after the picker, not on hover.** The obligation is "before
  they choose".
- `[ASSUMPTION]` the word **manager** is the right one. The field check-in page already
  mixes "manager" and "supervisor" (anti-pattern MA2/FC-2) — **one word for one thing:**
  whichever is chosen must be the word on both screens.

### 6.2 The server's refusal when the file is too large

**Two sentences, not one, because the advice differs and you cannot stand closer to a PDF.**

Image, after compression:

> **This photo is still 3.4 MB after we shrank it. The limit is 1 MB — take it again with
> just the bill in the frame.**

PDF:

> **This PDF is 7.2 MB and the limit is 3 MB. Send one page with the bill on it, or
> photograph the bill instead.**

And a third the brief does not cover but the magic-byte check will produce — **a file we
cannot read at all** (HEIC the browser did not convert, a `.zip` renamed `.jpg`, a
password-protected PDF):

> **We can take a JPG, a PNG or a PDF. Most phones can take a JPG — try again from the
> camera.**

**हिंदी [machine drafts — need native review]:**
यह फ़ोटो छोटा करने के बाद भी 3.4 MB है। सीमा 1 MB है — फ़्रेम में सिर्फ़ बिल रखकर दोबारा
खींचिए। · यह PDF 7.2 MB है और सीमा 3 MB है। बिल वाला एक पेज भेजिए, या बिल की फ़ोटो खींचिए। ·
हम JPG, PNG या PDF ले सकते हैं। ज़्यादातर फ़ोन JPG खींच सकते हैं — कैमरे से दोबारा कोशिश
कीजिए।

Why: the real size, the real limit, one thing to do, no "upload failed", no "check your
connection", no megabyte arithmetic the person has to do. The number is substituted by the
server, which already owns the figure (pattern: *the server's own sentence wins when it
names a real number*).

### 6.3 The refusal when a claim has no bill

**One rule, one sentence — plus one clause only HR can act on.**

Portal (ESS), shown inline in `ec-error` where the Send was pressed:

> **A claim needs a photo or a PDF of the bill. Please attach one and send it again.**

Desk, at submit:

> **A claim needs a photo or a PDF of the bill. Where there is no bill, attach the
> employee's signed statement of what was spent and why there is no bill.**

And, standing under the file control in the portal — **always visible, not a punishment
after the fact**:

> **No bill? Ask HR to file this claim with your signed statement of what you spent.**

**हिंदी [machine drafts — need native review]:** क्लेम के साथ बिल की फ़ोटो या PDF ज़रूरी है।
कृपया एक लगाकर दोबारा भेजिए। · बिल नहीं है? HR से कहिए कि आपके हस्ताक्षर किए हुए ब्यौरे के
साथ यह क्लेम दर्ज कर दें।

Why: the first sentence is identical on both surfaces, so the rule has one voice. The
second clause differs because the two readers are different people with different powers —
only HR can attach a declaration. **The third line is the one I would fight for**: without
it, §3.1a exists in a release note and nowhere a driver will ever read it, and the honest
outcome is that he loses ₹120. See **Q2**.

---

## 7 · What the picture needs to stay readable — EC6, my recommendation

The brief leaves this number to be set and says it is partly a design judgement. Mine:

| | Recommendation | Basis |
|---|---|---|
| **Long edge** | **1600 px** | At 200 dpi — the floor in document-imaging guidance (**read**, 3 Nov 2026) — a 210 mm A4 invoice needs ~1650 px *across the page*. 1600 px on the long edge puts an A4 that fills the frame at roughly 190 dpi, and a 58–80 mm thermal receipt that fills the frame far above 300 dpi. A bill is the easy case; the A4 hotel invoice is the hard one, and it is the one to size for |
| **Quality** | **JPEG 80** | 082's measured floor before artefacts (`employee_photo.py:72`). At 1600 px / q80 an ordinary bill lands ~250–600 KB, under the cap with room |
| **When it is still too big** | **Step the quality down (80 → 70 → 60) before touching the width** | Width loses *characters*; quality loses *smoothness*. A printed amount survives a soft JPEG and does not survive being 600 px wide |
| **Where** | **On the phone, in the browser** | Removes 3–4 MB from a 3G upload, removes 240 ms of server CPU per claim, and converts HEIC for free. The server still re-encodes and caps — the client step is an optimisation, never the control |
| **Greyscale?** | **No** | A faint thermal receipt needs contrast, and colour is also how an approver tells a fuel bill from a food bill. Not worth the bytes saved |

**This is an `Experiment`, not a fact.** The brief's kill criterion is the test: five real
DTC bills, photographed as a driver would, run through 1600/q80. Look at the amount. If it
is unreadable, the fix is a bigger long edge, not a bigger cap.

---

## 8 · Decisions and questions

### ⚠ DECISION — AQ1 · the viewer is below the sheet

**Decision needed:** raise `.mpf-dv` above `.hm-ov`, or give the sheet a lower layer?
**Context:** measured, `panels.css:712` vs `:3064`. **Conflict:** none — it is a bug the
reuse plan walks into. **Affected:** every approver. **Recommendation:** raise the viewer,
and add it to `scripts/check_portal_trays.js`'s geometry checks (it is already listed
there for the profile case). **Risk if it waits:** the slice's WOW moment ships blank.
**Owner:** `hrms-fullstack-engineer`, at impact analysis.

### ⚠ DECISION — EC4 · what happens to a HEIC bill

**Decision needed:** does a client-side re-encode satisfy the mandatory rule for iPhone
filers, and what does the server do with a HEIC that reaches it anyway?
**Context:** our only image path refuses HEIC, measured. **Conflict:** "mandatory
everywhere" vs "nobody honest is refused" (brief §3.2). **Affected:** every iPhone filer —
likely supervisors and office staff, not drivers. **Options:** (a) compress on the client,
which yields JPEG whatever arrived, and keep the server's refusal as a backstop
— **recommended**; (b) accept HEIC unchanged, which means storing an unstrippable file
(and the brief already names PDF as the only such type); (c) refuse it with the 6.2 third
sentence and accept that some people cannot file. **Risk if it waits:** found at UAT by the
one persona most likely to be in the room. **Owner:** `hrms-fullstack-engineer` for
feasibility, `hrms-security-privacy-engineer` for (b).

### ⚠ DECISION — EC3 · one call or two

**Decision needed:** does the portal send file-and-claim in one call (brief §3), or upload
the file first and post the claim with its url?
**Context:** there is no duplicate guard on `apply_expense_claim` (slice 070 D2, in the
code), so the no-answer state asks the person to retry a request that may have landed. With
the photo in the body, that is 1 MB re-sent on 3G. **The reuse path the brief itself points
at is already two calls** (`uploadMyDocument`; `joining.html` uploads each file on its own).
**Conflict:** brief §3's *"one call, so there is nothing to split"* against the retry
experience and the 078 precedent. **Recommendation:** two calls — upload, then file the
claim with the url. A retry then re-sends ~1 KB, the picture can be shown back before Send
(O3), and the size refusal arrives *before* the person has filled in the amount.
**The cost, said out loud:** an uploaded file whose claim is never sent is an orphan, so
something has to tidy those up — which is a retention question for D6 anyway. **Owner:**
`hrms-business-analyst` to specify, `hrms-fullstack-engineer` to confirm. Not a product
decision; it does not change what the brief promises.

### ⚠ DECISION — AQ2 · the CXO and the single claim

**Decision needed:** should a system manager's Home row open an individual expense claim at
all, now that it will carry a bill?
**Context:** `portal.js:6538` and `:6625` — for a system manager the expense row opens the
oldest claim's sheet. Brief §9 gives the CXO *"No. Summaries only"* on the bill.
**Conflict:** the product's current behaviour against the brief's own access table.
**Affected:** founders and anyone with System Manager. **Options:** (a) the CXO row leads to
a count and a screen, never a claim — consistent with §9; (b) accept it and record it in the
access table as a deliberate System Manager power. **Recommendation:** (a), and note that
either way this is a pre-existing behaviour the attachment makes visible, not something this
slice creates. **Owner:** `hrms-security-privacy-engineer`, then Surbhi.

### Q1 — the word for the person who reviews a regularization

The notice says **manager**. `attendance_correction.py` routes by `_reports_to`, and the
field check-in page already says "supervisor" in one place and "manager" in another
(anti-pattern MA2/FC-2). **One word for one thing.** My recommendation: **manager**
everywhere, and fix the check-in string when something next touches it. Does not block.

### Q2 — may the employee's refusal name the HR route? (one line, for Surbhi)

The brief's fifth subtract pass deleted an "ask HR to file this claim for you" sentence as
untrue — but **§3.1a makes it true again**: HR files the claim with a signed declaration.
**Without that line, a driver who paid cash with no receipt meets a wall and never learns
there is a door.** I recommend the single line in §6.3. If the answer is no, say so and I
will design the wall honestly instead.

### Still open from the brief, not mine

**D6** — retention clock and logging for evidence files (security/privacy, with counsel).
It now also has to cover **orphan uploads** if EC3 goes to two calls, and a draft that
reaches the server **starts the clock earlier** (standing checklist item).

---

## 9 · For the design step (`01b`), and what the BA will need

States to draw, none of them optional: nothing attached · camera denied · a file chosen and
being shrunk · shrunk and shown back with its size · uploading on 3G · refused for size ·
refused for type · offline with the file still held · no answer · sent · the approver's
"Bill attached" row · the sheet before and during "Opening the bill…" · the viewer on a
phone at 360 px and at 200% text · an old claim with no bill · HR's 100-row queue.
Plus the frontline bar: **the whole claim in two minutes on a phone, skeleton in 300 ms,
p95 ≤ 2.5 s on 3G** (`nfr-budget.md` §2, §7).

Acceptance criteria the BA will want from this scan: the exact words in §6 on the exact
surfaces; "before the file picker" as a positional assertion, not a presence assertion; the
row carries words and the sheet carries the button; no private-file URL reaches the browser;
the viewer is above the sheet; the file survives a retry; and **a test that posts a claim
with no file and asserts the server's own sentence reaches `ec-error`** (brief §3 — test
what it sends, not what it draws).

---

## 10 · Subtract pass — what I removed

Read once more asking only what could go.

**Removed:** a thumbnail on the employee's claim list (the viewer is one tap away and 078
already decided no thumbnails in lists); a separate "evidence" section on the regularization
card (one line inside the existing card does it); a progress bar for the upload (a button
that says "Sending…" is the pattern this product already uses, and a real percentage on a
3G POST is not reliably available); an "are you sure you want to send without a file?"
confirm on the regularization — it is optional, and a confirm on an optional field is a
nudge; a second set of words for the Desk refusal's first sentence (one rule, one voice);
and my first draft's three-sentence version of the notice, which had a sentence of advice in
it.

**Kept deliberately, though each costs something:** the shown-back picture (O3) — it is the
only way the person can tell their own bill is readable, and it is the kill criterion's
instrument; and the "No bill?" line (O5) — it is one grey line against somebody losing
their money.

**What is left:** one file control on two forms, two buttons on it, one shown-back picture,
one notice, three refusals, one word on two queue rows, one button in one sheet, one
generalised viewer, one z-index.
