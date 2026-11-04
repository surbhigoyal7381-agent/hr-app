# Slice 081 — A bill on an expense claim, evidence on a regularization

**UX design · `hrms-ux-designer` · 3 November 2026 · Status: for Surbhi's design gate**

**Prototype (mandatory, and the thing to review):**
`docs/slices/081-bill-and-evidence-attachments/prototype-v1.html` — open it in a browser.
It holds **no real tenant data**; every name, number and bill in it is invented and the
review bar says so, which is why it sits in the slice folder rather than outside the repo.

**Inputs read, in this order:** `01-product-brief.md` (every product decision in it is
settled — nothing here reopens one) · `01a-ux-opportunities.md` (my own scan, same day —
this document builds on it and does not restate it) · `07-devops-inputs.md` §1, all 14
OPS rows · `.claude/context/ux-learnings.md` · the design system
(`templates/includes/design_system.html`) · the portal source named throughout.

**A naming note, because it affects the next person.** I was asked for `02-design.md`.
`handoff-contract.md` reserves `02` for the business analyst's functional spec, and the
design artifact is `01b-ux-design.md`. I used the contract's name so the analyst's `02`
has somewhere to land. Say the word and I will rename it.

---

## 0 · Read this first — four things, three of them bad

**1. The bill will not render for the approver, and nothing will look broken.**
`.hm-ov` (the approver's decision sheet) is `z-index: 1300`. `.mpf-dv` (the ALV-287
document viewer the brief tells us to reuse) is `1250`. Both measured, in
`public/css/ess/panels.css` at L712 and L3064. Taken as it is, the approver taps
**View bill**, the viewer opens *behind* the sheet, and the screen does not change. No
error, because nothing failed. **The slice's whole point ships blank.**

**What has to move: the viewer, not the sheet.** Lowering the sheet is not available —
`1200` is already the employee's own modal `.gp-backdrop` — so the viewer goes above
everything at **1400**. The fix itself is the engineer's at impact analysis; the prototype
draws the flow as it must actually work, and has a state (`Approver · 5b`) showing exactly
what ships if nobody moves the number. **P1.**

**2. An iPhone bill is refused today, and "take it again" does not help.** Pillow in the
running image has no HEIC reader, `pillow_heif` is not installed, and
`employee_photo.py:22` refuses HEIC deliberately (measured today by DevOps, OPS-11, and by
me in the scan). On an **optional** field that is a shrug. On a **mandatory** one it is a
wall, because the phone will produce HEIC again next time.

**The answer is the one from my own scan, and it is drawn:** re-encode the picture in the
phone browser on a canvas before anything is sent — the way `www/field-checkin.html`
already does at L718–724. The browser's own decoder turns HEIC into JPEG for free. When
the browser cannot decode it either, the person hears so **in about a second, before a
single byte leaves the phone** (prototype `Expense claim · 7b`), not after a 4 MB upload.
The server keeps its refusal as the backstop (`7`). **P1.**

**3. The two caps cannot be Frappe's `max_file_size`, and this is not a detail.** That
setting is **whole megabytes and site-wide** (`frappe/core/api/file.py:85-90`). Set to 1,
it would refuse the agreed 3 MB PDF, refuse the raw 4 MB photo *before* we ever compress
it, and break every other attachment in the product including employee documents, which
chose 5 MB. **Both caps live in our own endpoint, after the re-encode.** DevOps says the
same thing from the run side (OPS-6), and slice 078's outstanding "apply the per-file
ceiling" item must not be closed the obvious way during this slice. **No settings screen —
Surbhi settled that. Two constants.**

**4. The good news.** Nothing here needs a new screen, a new DocType, a new component, a
new container, a job queue, object storage or an nginx change. The viewer exists. The
upload shape exists. The two-button file picker exists in `www/joining.html`. The canvas
re-encode exists in `field-checkin.html`. The three failure states on the claim modal
exist and are good. **This design is one file control on two forms, one agreed recipe, one
word on two rows, one button in one sheet, one generalised viewer and one z-index.**

---

## 1 · Frame

A **driver at DTC** is standing at a petrol pump in daylight, on a cheap Android phone on
3G, with ₹420 of his own money gone and one hand free. He needs the claim to leave his
phone with the bill on it, and he needs to know it went.

A **line manager** between two things needs to decide that claim in one tap without asking
anybody a question.

**Personas in scope:** frontline employee (primary — wins every trade-off, per
product-context §2) · employee · line manager / expense approver · HR manager (as the
regularization reviewer, and as the Desk filer of a claim with no receipt).

**What changes for the three CLAUDE.md personas**

| Persona | Gains | Pays |
|---|---|---|
| **Employee** | A camera button, a picture they can check before sending, their own bill one tap from their own claim row, and a claim decided days sooner | One new obstacle: a claim with no bill cannot be sent. The "No bill?" line (§7.1) is what stops that becoming a lost ₹120 |
| **HR Manager** | Evidence attached to the record, in the Desk sidebar for free; a day-fix decided from the card | Two documentation duties that are not code and fail silently if nobody tells HR: the two-step expense-type setup (brief §1.4) and the self-declaration route (§3.1a) |
| **CXO** | Nothing, by design | Nothing — **but see D-AQ2: the code does not currently agree.** A System Manager's Home row opens the *oldest individual claim*, which from this slice onwards carries a bill |

**The one-way rule holds.** Nothing here improves a reviewer's convenience by degrading an
employee's experience. The one place it was at risk — a manager opening a medical receipt
— is answered by routing (brief §3.3), not by asking the employee to be careful.

---

## 2 · Evidence — and what I could not do

**Bad news, stated plainly: there are no screenshots and I did not open a browser.**
The local containers are up but every HTTP probe from this session is refused, and there
is no Playwright or Puppeteer available here. So:

- **Every current-state fact is labelled `read in code`**, with a file and line. Nothing
  in this document rests on a layout I imagined.
- **The prototype was verified structurally, not visually.** I rendered **all 66
  screen × state × language combinations** through jsdom and asserted: nothing throws, no
  nested interactive content (a button inside a button), no control without an accessible
  name, no button without words, and the string `undefined` never reaches the screen.
  All 66 pass. **That is a structural check, not a look.** Geometry — overflow past 360 px,
  real tap-target heights, the 200% text case — is specified in §8 and written into the
  CSS, but **I have not measured it rendered.** Somebody with a browser should, and §11
  says so.
- No screenshot folder was created, because there are no screenshots. Where earlier
  reviews stored them: `C:/Surbhi-Git/hrlocal-data/ux-review/<date>/`.

Current state is in `01a` §2 and is not repeated. The four facts that drive this design:

| Fact | Where | Label |
|---|---|---|
| The expense modal has Type, Date, Amount, Purpose and **no file control**; required is marked with an asterisk only | `request-modals.html:65-99` | read in code |
| Its three send-failure states are good and are reused: refused inline in `ec-error`, offline *"We could not reach the office. Nothing was sent."*, and no-answer with Try again removed | `portal.js:10033-10095` | read in code |
| **There is no duplicate guard** on `apply_expense_claim` | `portal.js:10047-10050` (slice 070's own note) | read in code |
| The approver decides in a **bottom sheet**, and the queue row is a single `<button>` with three spans | `hmExpenseSheet:6657`, `hmPendRowHtml:6585` | read in code |

---

## 3 · Benchmark

In `01a` §3 and not repeated. The one number that drives this design: **our 1 MB stored
cap is the tightest in this market by 5 to 10×** (Zoho Expense 10 MB × 5 receipts; Keka
~5 MB; Concur 5 MB; ApprovalMax 10 MB — all **read**, 3 Nov 2026). Their caps are generous
because they do nothing to the file. Ours is tight because we re-encode. **The whole burden
therefore falls on the compress-first step in §5**, and a design that sends the camera's
raw file and hopes will fail.

Deliberately not copied, and why it is better for a DTC driver: no receipt gallery, no
multiple files, no OCR/AutoScan, no "receipt required above an amount" threshold.

---

## 4 · Findings

IDs carry forward from `01a` so nothing is renumbered. New in this run: **EC8, EL2, AP6.**
`P0`–`P4` is the release-blocking ladder.

| ID | Finding | Impact | Kind | Size | Severity |
|---|---|---|---|---|---|
| **AQ1** | The viewer renders **behind** the decision sheet (1250 vs 1300). The approver sees nothing and nothing looks broken | High | Fix | S | **P1** |
| **EC4** | HEIC is refused by our only image path. On a mandatory field that is a wall for every iPhone filer | High | New | M | **P1** |
| **EC1** | No file control on the expense modal; the endpoint takes no file | High | New | M | **P1** |
| **AR1** | No file control on the regularization form, and no notice | High | New | M | **P1** |
| **AQ5** | No file on the approver's queue payload, nor on HR's. **An attachment nobody reviewing can open is not a feature** | High | New | M | **P1** |
| **EC2** | The chosen file must survive **Try again**. The offline state promises *"your details are still here"*; a file that silently drops breaks that promise and costs a second trip to the pump | High | New | S | **P1** |
| **UP1** | The upload path we are told to reuse fails with `alert("Upload failed")`, and its endpoint answers with Frappe's *"File size exceeded the maximum allowed size of 1.0 MB"*. **Both are on our banned list — reuse the shape, never the sentences** | High | Fix | S | **P1** |
| **EC3** | **Two calls, not one** — upload the file, then file the claim with its reference. See §12.1 | High | Improve | M | **P2** ⚠ |
| **EC5** | The caps cannot be `max_file_size`; they belong in our endpoint after the re-encode | High | Fix | S | **P2** |
| **AQ2** | A System Manager's Home row **"opens the oldest" individual claim**, so a CXO lands in a claim's sheet and would open its bill. Brief §9 says *"No. Summaries only."* Pre-existing; the attachment makes it a privacy question | High | Fix | S | **P2** ⚠ |
| **EC6** | The resize recipe was unset. **Agreed in §5: long edge 1600 px, JPEG 82, quality steps down before width** | High | New | S | **P2** |
| **EL1** | The employee cannot see the file on their own claim. **After compression they are the only person who can tell whether their own bill is readable** — and that is the kill criterion's cheapest instrument | Medium | New | S | **P2** |
| **AQ3** | The ALV-287 viewer is welded to the Positions mini profile (own endpoint, own revoke owner, one global `MPF_DOC`). Generalise to *(blob, name, who revokes it)*. **One viewer, four callers, no new component** | Medium | Improve | M | **P2** |
| **AQ4** | `mpfOpenDoc` disables the button and says nothing until it fails. A 1 MB bill on 3G is seconds. Needs an **"Opening the bill…"** state, and the viewer must come **before** the irreversible Approve | Medium | Improve | S | **P2** |
| **EC8** | **New today.** Every label in the expense modal is a `<div class="gp-label">`, not a `<label for>`, so **no input in it has an accessible name** — including the new control's neighbours. Found by rendering all 66 states. One attribute each; the prototype draws it fixed | Medium | Fix | S | **P2** |
| **HQ1** | HR's day-fix cards need *"Evidence attached · View"* and nothing else. **No thumbnails in the list** — 078's rule, and OPS-7 prices it: a preloading queue is 20 MB through 8 request slots on one page view | Medium | New | S | **P2** |
| **AP6** | **New today.** The approver **role** lets several people open one claim. Whoever acts first is recorded as the approver, so everyone else needs an honest dead end: who acted, when, nothing left to do. **The mechanism is not designed here** (brief §3.3); only the state is | Medium | New | S | **P2** |
| **AR2** | The regularization form renders inside a table cell in the day row. At 360 px and 200% text the action buttons leave the screen; the action row must be scrolled into view once a file is attached | Medium | Improve | S | **P3** |
| **EC7** | Required is an asterisk today. The new control says it **in words**: "Photo of the bill · required" | Low | Improve | S | **P3** |
| **EL2** | **New today.** A role-routed claim has no approver to name, so the employee's own row cannot say *"Waiting for Sunil Mehra"*. **Recommendation: "Waiting for approval", with no name** — a Frappe role name means nothing to a driver | Low | New | S | **P3** |
| **AR3** | The employee's own day-fix card shows no file either. Same one-line fix as EL1 | Low | New | S | **P3** |
| **UP2** | My Documents' View is still a raw private-file `href`. **Not this slice's job** — but the two new surfaces must not copy that line | Low | Keep out | — | **P3** |
| **KEEP** | `submitExpenseClaim`'s three failure states · the server's own words reaching `ec-error` · Decline-with-a-reason reaching the employee's list · *"Approving passes it to accounts… you cannot take it back here"* · the reason-help line on the day-fix form · "no thumbnails in a list" · ALV-287's *"shown so you do not have to save a copy"*. **All good, all reused, none re-litigated** | — | Keep | — | — |

**Release view.** Seven P1s, all of them in scope and all of them answered by this design.
**AQ1 and EC4 are the two that would otherwise be found in test or at UAT**, and both are
drawn. Nothing here is a reason to hold the slice.

---

## 5 · The compression recipe — DevOps and I, reconciled

We measured independently and landed on the same width. Here is the single agreed recipe,
with the one place we differed and how it resolves.

| | Agreed |
|---|---|
| **Long edge** | **1600 px.** Both of us. At 200 dpi — the floor in document-imaging guidance (**read**, 3 Nov 2026) — a 210 mm A4 invoice needs about 1650 px across the page. 1600 px puts a frame-filling A4 at roughly 190 dpi and a 58–80 mm thermal receipt far above 300 dpi. **The A4 hotel invoice is the hard case and the one to size for**; a till receipt is easy |
| **Quality** | **JPEG 82.** DevOps measured 82 on this exact pipeline; I had recommended 80 from `employee_photo.py:72`. **Take 82** — it is the measured number on the real path and the difference from 80 is invisible. My 80 is withdrawn |
| **When the result is still over 1 MB** | **Step the quality down first — 82 → 72 → 62 — and only then the width — 1280, then 1024.** Refuse after that, with the §7.2 sentence |
| **Why that order (mine, and the one thing I argued for)** | **Width loses characters; quality loses smoothness.** A printed amount survives a soft JPEG and does not survive being 600 px wide. DevOps' OPS-3 already allowed a width ladder (1280 then 1024); this puts three quality steps in front of it, so the width is the last thing touched instead of the first |
| **Where it runs** | **On the phone, in the browser, on a canvas**, targeting ≤ 900 KB. It removes 3–4 MB from a 3G upload, removes ~1.4 s of server CPU per claim (DevOps measured, OPS-4), and converts HEIC for free. **The server then re-encodes and caps — the device step is an optimisation and never the control** |
| **Greyscale?** | **No.** A faint thermal receipt needs contrast, and colour is also how an approver tells a fuel bill from a food bill. Not worth the bytes |

**This is an `Experiment`, not a fact, and the brief already names the test that settles
it:** five real bills from a DTC supervisor, photographed as a driver would, run through
1600 / q82. Look at the amount. **If it is unreadable the fix is a bigger long edge, not a
bigger cap** (kill criterion, brief §16). The prototype's "380 KB · 1600 px" line is how
that test gets measured in the field, by the only person who can judge it.

Measured sizes, for the record: DevOps' synthetic 4.28 MB 12 MP source lands at **145 KB**
at 1600 px, which is optimistic because the source is low-detail; a real photographed bill
is **250–600 KB** `[ESTIMATE]`. Either way, comfortably inside 1 MB with room.

---

## 6 · Flows, with every state

### 6.1 The expense claim — employee, phone

```
Open "New Expense Claim"
  │
  ├─ 1 nothing attached ─ "Photo of the bill · required"
  │      two buttons: Take a photo of the bill | Choose a file
  │      standing line: "No bill? Ask HR to file this claim with your signed statement…"
  │
  ├─ camera returns nothing (denied, or cancelled)  → 2 hint, both buttons still there
  ├─ file chosen
  │      ├─ the browser cannot decode it           → 7b device refusal, nothing sent
  │      └─ 3 making the picture smaller (canvas)  → 4 sending the picture (upload)
  │             ├─ over the cap after the ladder   → 6 / 6b, per type
  │             ├─ not a JPG / PNG / PDF           → 7 (magic bytes, server)
  │             ├─ the upload itself failed        → 8 file still held, "Send the picture again"
  │             └─ stored                          → 5 shown back with its size
  │
  ├─ Submit with nothing attached → 9 the SERVER's refusal, in ec-error
  └─ Submit with a bill → 10 Sending…
         ├─ refused            → the server's own sentence in ec-error
         ├─ offline            → 11 "your details AND YOUR BILL are still here" · Try again
         ├─ no answer          → 12 "look in your list" · Close only, no re-send
         └─ accepted           → 13 modal closes · toast · the new row says "Bill attached · View"
```

**Every one of those states is in the prototype and selectable.** None was left out for
being awkward — a state missing from the prototype becomes an argument during the build.

### 6.2 The day-fix (regularization) — employee, phone

```
Tap an absent day → the form opens inside the day row
  reason → what HR should know
  → "Add a photo or document if you have one"
  → THE NOTICE, in plain grey, directly above the two buttons
  → Take a photo | Choose a file          (optional; Send works with nothing attached)
      → making the picture smaller → attached, shown back, Remove
  → "Ask HR to fix this day"
```

### 6.3 The reviewer

```
Home · "Pending for you"
  row (one <button>): name · claim · amount · date · waiting
                      + a third line in WORDS: "Bill attached" / "No bill attached"
  tap → the sheet
        amount, type, date, the note, how long it has waited
        → [ View bill ]        ← in the BODY, above the decision, never between the buttons
              → "Opening the bill…"  → the viewer, ABOVE the sheet (z 1400)
                                      → Close returns focus to View bill; the sheet is untouched
              → failed → "The bill did not open. Check your signal and tap View bill again."
        → Approve | Decline-with-a-reason        (unchanged)
  an older claim → the sheet says plainly there is nothing to open
  a role-routed claim somebody else already decided → the dead end (AP6)
```

### 6.4 Desk — HR

Save the draft → attach → **Submit**. The rule fires at submit, never at save, because
Frappe only draws the attachment area on a document that already exists. A half-finished
draft stays a legal draft.

---

## 7 · Screen-by-screen, with the exact words

Hindi is a **machine draft and needs a native reviewer** before it ships — a standing open
item. EN/HI parity on employee-facing surfaces is an NFR (`nfr-budget.md` §7), not a
nicety. Strings with no Hindi draft below are chrome reused from the existing screens and
are listed in §14 as still to translate.

### 7.1 The file control on the expense claim

**Position: FIRST in the modal, above Expense Type.** A departure from the current field
order, and deliberate for three reasons: it is the only step that can fail; it is the only
step that needs the bill physically in the person's hand; and because the file uploads on
its own (§12.1), **a size refusal arrives before anything has been typed.**

| Element | English | हिंदी [machine draft] |
|---|---|---|
| Label | **Photo of the bill · required** | बिल की फ़ोटो · ज़रूरी |
| Hint | A photo or a PDF. We make the picture smaller on your phone before it is sent. | फ़ोटो या PDF। भेजने से पहले हम तस्वीर आपके फ़ोन पर ही छोटी कर देते हैं। |
| Primary button | 📷 **Take a photo of the bill** | बिल की फ़ोटो खींचिए |
| Second button | **Choose a file** | फ़ाइल छाँटिए |
| Standing line, always visible | **No bill? Ask HR to file this claim with your signed statement of what you spent.** | बिल नहीं है? HR से कहिए कि आपके हस्ताक्षर किए हुए ब्यौरे के साथ यह क्लेम दर्ज कर दें। |

**The standing line is settled copy — Surbhi confirmed it on 3 November ("yes").** Three
things about it that the build must not drift on:

1. **It is standing text under the control, always visible — not only part of the
   refusal.** A person who already knows they have no receipt should meet the route
   *before* they waste a trip trying to photograph something, not after being refused. It
   also appears in the Desk refusal (§7.4), where it reads naturally; the always-visible
   line is the one that earns its place.
2. **It is not an exemption, and must never read like one.** The claim still needs a
   file. **The signed statement *is* the file**, and **HR attaches it** — which is why the
   line says "ask HR", not "you can file without a bill". If the wording ever drifts
   toward the second thing, it quietly undoes the mandatory decision.
3. It is plain grey hint text. Not a button, not a link, not a callout — there is no
   screen for it to lead to. Its job is to tell a driver a door exists.

**Two buttons, not one input,** copying `www/joining.html:503-546`. The camera button
carries `capture="environment"` — the back camera, the one pointing at the bill. Both are
styled buttons in front of a visually hidden `<input type="file">` that stays keyboard
reachable and labelled.

**The states, word for word**

| # | State | What the person sees |
|---|---|---|
| 1 | nothing attached | label, hint, two buttons, the standing line |
| 2 | camera gave nothing back | ℹ **Nothing was chosen. If the camera will not open, use Choose a file.** Both buttons stay. *A denied camera returns no file and no error, so this names the other button rather than guessing at the cause.* |
| 3 | shrinking | spinner · **Making the picture smaller…** · में तस्वीर छोटी की जा रही है |
| 4 | uploading | spinner · **Sending the picture…** · the shrunk picture already shown beside it. **No percentage bar** — a real one is not reliably available on a 3G POST |
| 5 | shown back | the picture, **Bill attached**, **380 KB · 1600 px · bill-03-nov.jpg**, and **View full size** / **Replace** |
| 5b | PDF shown back | a "PDF · 2 pages" tile instead of a preview, **1.8 MB · hotel-invoice.pdf**, same two buttons |
| 6 | image over the cap | ⚠ **This photo is still 3.4 MB after we shrank it. The limit is 1 MB — take it again with just the bill in the frame.** |
| 6b | PDF over the cap | ⚠ **This PDF is 7.2 MB and the limit is 3 MB. Send one page with the bill on it, or photograph the bill instead.** |
| 7 | a file we cannot read (server, magic bytes) | ⚠ **We can take a JPG, a PNG or a PDF. Most phones can take a JPG — try again from the camera.** |
| 7b | the device could not read it | ⚠ **This phone could not read that picture. Use "Take a photo of the bill" instead — nothing has been sent.** |
| 8 | the upload failed | the file still held, **Send the picture again** / **Replace**, and above it: **We could not send the picture. Nothing was lost.** / *Your bill is still here. When you have signal, tap Send the picture again.* |

हिंदी drafts for 6, 6b and 7: यह फ़ोटो छोटा करने के बाद भी 3.4 MB है। सीमा 1 MB है — फ़्रेम
में सिर्फ़ बिल रखकर दोबारा खींचिए। · यह PDF 7.2 MB है और सीमा 3 MB है। बिल वाला एक पेज
भेजिए, या बिल की फ़ोटो खींचिए। · हम JPG, PNG या PDF ले सकते हैं। ज़्यादातर फ़ोन JPG खींच
सकते हैं — कैमरे से दोबारा कोशिश कीजिए।

**Why one sentence per type.** The advice differs, and **you cannot stand closer to a
PDF.** A single "that file is too large" has to be vague about the fix, which is what makes
it useless. Every sentence names the real size and the real limit, substituted by the
server, which already owns the figure.

### 7.2 The refusal when a claim has no bill — the server's own words

Shown inline in **`ec-error`**, where the Send was pressed:

> **A claim needs a photo or a PDF of the bill. Please attach one and send it again.**

**हिंदी [draft]:** क्लेम के साथ बिल की फ़ोटो या PDF ज़रूरी है। कृपया एक लगाकर दोबारा भेजिए।

**This must come from the server, not from the form.** The form also guards first, so in
practice a person rarely sees it — but the standing lesson in this product is *test what it
sends, not just what it draws*, so the acceptance criteria need a test that **posts a claim
with no file and asserts the server's own sentence reaches `ec-error`**. Never "upload
failed". Never "check your connection". Never a Python argument error.

### 7.3 The three send states, with one word changed

Reused exactly from `portal.js:10080-10095`, except the offline line, which has to cover
the new thing:

| State | Words |
|---|---|
| offline | **We could not reach the office. Nothing was sent.** / *Your details **and your bill** are still here. When you have signal, tap Try again.* |
| no answer | **No answer from the office. It may have gone through.** / *Look in your list before you send it again.* — Try again is removed, only Close, because **there is no duplicate guard on the server** |
| sent | toast: **Expense claim submitted.** and the new row already says *Bill attached · View full size* |

### 7.4 Desk, at submit

> **This claim cannot be submitted yet**
> A claim needs a photo or a PDF of the bill.
> Where there is no bill, attach the employee's signed statement of what was spent and why there is no bill.

Plus, below it: *The draft is still saved. Only Submit is blocked.*

**One rule, one first sentence.** The first sentence is word-for-word the one the driver
sees, so the rule has a single voice on every surface. The second sentence exists **only
here**, because HR is the only person who can attach a statement on somebody else's behalf
— and a sentence only one reader can act on belongs at the end of the message, not at the
start.

### 7.5 The employee's own claim row

| Case | Words |
|---|---|
| has a file | ✓ **Bill attached** · **View full size** → the same viewer the approver gets |
| filed before this ships | **No bill attached** — plain grey, no button. *An empty View is worse than an honest absence.* |
| routed to a role | the status chip says **Waiting for approval**, with no name (**EL2**) |

**Why the employee sees their own bill at all (EL1).** After compression **they are the
only person who can tell whether their own bill came out readable.** Nobody downstream can
hand that judgement back to them, and it is the cheapest instrument the kill criterion has.

### 7.6 The day-fix form — the notice

| Element | English | हिंदी [machine draft] |
|---|---|---|
| Label | **Add a photo or document if you have one** | *draft needed* |
| **The notice** | **Your manager reads this request, and will see any file you attach. Attaching one is your choice — HR can fix the day without it.** | आपका यह अनुरोध आपका मैनेजर पढ़ता है, और आप जो फ़ाइल लगाएँगे वह उन्हें भी दिखेगी। फ़ाइल लगाना आपकी मर्ज़ी है — इसके बिना भी HR आपका दिन ठीक कर सकता है। |
| Buttons | **Take a photo** · **Choose a file** | बिल की फ़ोटो खींचिए · फ़ाइल छाँटिए |

**Everything about this notice is deliberate:**

- **Two facts, no advice.** Who reads it, and that it is the person's choice. Nothing tells
  them what to decide. The brief's principle is that we respect their judgement rather than
  overriding it.
- **The second sentence is what makes the first fair.** A notice that says only "your
  manager will see this" reads as a warning against attaching anything, and HR loses the
  punch slip it needs to settle the day. Saying the request works either way is the escape,
  in the same breath as the limit.
- **"reads this request"**, not "can see" — it is not a possibility, it is what happens.
- **Plain grey hint text, directly above the two buttons, inside the same block. Never a
  coloured callout.** A warning-coloured box on an optional field is a nudge away from the
  evidence the reviewer needs.
- **Position is the requirement, not presence.** It must come **before** the file picker —
  not after, not on hover, not in a help panel. The acceptance criterion is positional.
- **It is a transparency control, not an access control.** Nothing restricts the manager
  here, by design, and it must never be recorded as a protection.
- `[ASSUMPTION]` the word **manager** is right. `field-checkin.html` already says
  "supervisor" in one place and "manager" in another (anti-pattern MA2/FC-2). **One word
  for one thing:** whichever is chosen must be the word on both screens. My recommendation
  is **manager** everywhere, and fix the check-in string when something next touches it.
  Does not block. (Q1.)

### 7.7 The reviewer's row and sheet

**The row carries words. The sheet carries the button.** The row is a single `<button>`
(`hmPendRowHtml:6585`), so a "View" link inside it would be a button inside a button —
unreachable by keyboard and a WCAG 2.2 AA failure. So:

| Surface | Words |
|---|---|
| queue row, third line | **Bill attached** / **No bill attached** (the second in plain grey, not red — it is not an error) |
| day-fix row | **Evidence attached** |
| sheet, in the body above the decision | 🗎 **View bill** |
| while opening | spinner · **Opening the bill…** |
| if it fails | **The bill did not open. Check your signal and tap View bill again.** |
| the sheet's existing final-act line | *Approving passes it to accounts for payment. You cannot take it back here.* — **unchanged** |

**View bill never sits between Approve and Decline.** The footer stays the decision, and
the evidence is read before the act that cannot be taken back.

**The role dead end (AP6):**

> **Already decided**
> Priya Nair approved this 4 minutes ago. There is nothing for you to do.
> *[ Back to what is waiting ]*

With a role, several people can open one claim; whoever acts first is recorded as the
approver. **I am not designing the mechanism** — brief §3.3 reserves that for the analyst
and the engineer, and §12.3 says what I did and did not draw.

### 7.8 HR's day-fix queue

**Evidence attached · View**, and nothing else. These cards already carry Fix and Decline,
so they are not single buttons and **View can be a real button here** — same words, same
viewer. **No thumbnails, no preloading, no "open all"** (HQ1, OPS-7): the endpoint reads a
whole file into one of eight request slots, so a 47-row queue that preloaded pictures would
be the slowest page in the product, on the surface that matters most.

### 7.9 The viewer

One viewer, four callers: the Positions mini profile (today), the employee's own claim and
day-fix rows, the approver's sheet, and HR's card. Generalise `mpfShowDoc` to
*(blob, name, who revokes it)* rather than writing a second popup (AQ3).

- Title names what it is: **Bill · Ramesh Kumar · 3 Nov 2026**
- Footer keeps ALV-287's line: *Shown here so you do not have to save a copy.*
- `role="dialog"`, `aria-modal="true"`, an `aria-label`, **Escape closes it**, focus moves
  in on open and **returns to the button that opened it** on close. (Slice 059 anti-pattern
  P7 was modals with no role, no Escape and no focus move — do not repeat it.)
- **z-index 1400**, above the sheet's 1300 (AQ1).
- The blob URL is revoked by whoever opened it, and **no `/private/files/...` address ever
  reaches the browser.**

---

## 8 · Accessibility — WCAG 2.2 AA (`nfr-budget.md` §7)

| Item | What this design does |
|---|---|
| **Every input labelled** | **EC8 is fixed in the prototype**: real `<label for>` on Type, Date, Amount and Purpose, which have no accessible name today. The hidden file inputs are labelled by their visible buttons |
| **Tap targets** | **≥ 44 px on the phone** (our rule; WCAG 2.2 AA's own floor is 24 px on a mouse). Every `.btn`, the modal close and the viewer close are min-height 44 px in the prototype's CSS. **Not measured rendered — §2** |
| **Field and button text** | **16 px** on everything a finger touches, so iOS does not zoom the page on focus. **Note the existing debt:** the portal's `--fs-base` is 13 px and the modal's inputs inherit it. The new control sets 16 px for itself; raising it product-wide is not this slice's call |
| **Nothing under 12 px** | `--fs-sm` (12 px) is the floor used. `--fs-xs` (11 px) is used only in the prototype's own review bar, never in a drawn screen |
| **Status in words, not only colour** | "Bill attached" and "No bill attached" are words. The ✓ and ⚠ marks sit **beside** text, never instead of it. "No bill attached" is grey, not red — it is not an error |
| **Live regions** | Every progress and result line is `role="status" aria-live="polite"`: shrinking, uploading, attached, and each refusal. A refusal that stops the person is `role="alert"` |
| **No nested interactive content** | Asserted across all 66 states. The queue row stays one button |
| **Keyboard** | Visible focus ring (`:focus-visible`, 3 px, offset 2). The viewer traps and returns focus. Escape closes the viewer and the modal |
| **200% text** | Switchable in the prototype. **AR2 is the known failure:** at 360 px and 200% the day-fix form's buttons leave the screen, so the action row must be scrolled into view after a file is attached |
| **Hindi runs ~30% longer** | The language switch proves the layout at Devanagari length. The two-button row wraps (`flex: 1 1 9.5em`) rather than overflowing |

**Not verified:** colour contrast ratios, and all rendered geometry. Both need a browser
(§2, §11).

---

## 9 · Privacy — what each screen shows, and to whom

| Screen | Whose data | Least needed? |
|---|---|---|
| The file control | the person's own | Yes — their own file, their own claim |
| The employee's claim and day-fix rows | their own | Yes |
| The approver's row | one name, one amount, one date, and **the word** "Bill attached" | Yes. **The row never shows the file**, only that one exists. One tap, one file, one person's claim |
| The approver's sheet and the viewer | one claim at a time | Yes. **No bulk open, no gallery, no thumbnails in any list** |
| HR's day-fix queue | the requests in their own companies | Yes — one line per card, the file only on a tap |
| Desk | HR's existing powers | Unchanged |

**Four things the build must not quietly drop:**

1. **No private-file URL reaches the browser, on any of the four callers.** A guarded
   endpoint streams the bytes; the viewer gets a blob. The honest half, already documented
   in this product and not claimed away here: a reader who somehow holds a private-file URL
   can still fetch it, because Frappe's private-file gate falls back to the parent's read
   permission and fires no hook.
2. **One access-log row per viewer per file per day**, reusing `Alvoraa Photo Access Log`
   and its existing `source` Select. The brief's own measure — *≥70% of approvers open the
   file before deciding* — is instrumented by that row and nothing else.
3. **The day-fix notice is a transparency control, never a protection.** Verify that it is
   present *and positioned before the file picker*. Nothing restricts the manager there.
4. **The routing on expense claims is the access control** (brief §3.3). It must live in
   the permission layer and the query, tested as a plain staff login through the API on a
   fresh site — `/api/resource/Expense Claim`, `/api/resource/File`,
   `frappe.client.get_list` on File, `frappe.client.attach_file`,
   `frappe.desk.reportview.get`, report view and export, link search, and **share**.
   Sharing a claim opens its attachments to whoever it was shared with, and `share` is the
   dangerous verb. Flagged here because I am designing screens that show another person's
   data; the requirements are the security engineer's (`01c`).

**⚠ COMPLIANCE — the screen I am flagging.** Three of the surfaces in this design show
another person's file: the approver's sheet, HR's day-fix card, and Desk. Per the
`data-doors.md` rule, **the portal is not the security** — none of the three may rely on
our own screen code to decide who sees what.

---

## 10 · The prototype

**`docs/slices/081-bill-and-evidence-attachments/prototype-v1.html`** — one file, no
network, opens straight from disk. If this session has no Artifact tool, the session that
ran me should publish it and give Surbhi the link.

**How to drive it.** The review bar has six controls: **Screen** (7), **State** (up to 16
per screen), **Device** (Phone 390 / Phone 360 / Desktop 960), **Theme** (light / dark),
**Language** (English / हिंदी draft) and **Text size** (100% / 200%).

Language and theme sit on the review bar here because neither exists as an in-product
control on these screens; they are scaffolding, and they are labelled as such.

**The parity table the analyst will need.** Prototype parity is a standing rule in this
project — *what the approved prototype shows gets built exactly as drawn, and any later
difference needs Surbhi's explicit agreement.*

| Prototype screen · state | What must ship |
|---|---|
| Expense claim · 1–8 | the file control, first in the modal, with all eight of its own states |
| Expense claim · 9 | the server's refusal, in `ec-error` |
| Expense claim · 10–13 | the three existing send states with "and your bill", and the toast |
| My expense claims | "Bill attached · View full size", the honest "No bill attached", "Waiting for approval" with no name |
| Fix a day · 1–4 | the label, the notice above the buttons, the two buttons, the shown-back file |
| My day-fix request | one evidence line inside the existing card |
| Approver · 1 | the third line in the queue row, in words |
| Approver · 2–4 | View bill in the body above the decision, its opening state, its failure |
| Approver · 5 | the viewer above the sheet |
| Approver · 5b | **not a screen to build — it is what ships if nobody moves the z-index** |
| Approver · 6 | an older claim's sheet, saying there is nothing to open |
| Approver · 7 | the role dead end — **ships wherever the role flow ships** |
| HR · both | "Evidence attached · View" on the card; the viewer; no thumbnails |
| Desk | the submit refusal, both sentences, and "the draft is still saved" |

**What the prototype is not.** It is not a spec and not production code. It is a single
page of invented data built on the design-system tokens, and it lives in the slice folder
only because it contains nothing real.

---

## 11 · Usability test plan — for the High-impact items

**Five people, on their own phones, one task each.** The whole point is the frontline bar:
**the claim leaves the phone in two minutes.**

| | |
|---|---|
| **Who** | Three DTC drivers or frontline staff on their own Android phones, one supervisor on an iPhone (**the iPhone is not optional — EC4 is the whole reason**), one HR person on a laptop |
| **Task 1** (driver) | "You have just paid ₹420 for diesel. Claim it back." Success: filed with a readable bill, unaided, in **under two minutes** |
| **Task 2** (iPhone supervisor) | The same, from the camera. Success: it files. **Failure mode to watch for: a HEIC the browser did not convert** |
| **Task 3** (supervisor) | "Decide Ramesh's claim." Success: the bill is opened **before** Approve is pressed |
| **Task 4** (HR) | "Fix Pooja's day." Success: the evidence is opened from the card |
| **Task 5** (driver, no receipt) | "You paid ₹120 cash for an autorickshaw and have no bill." Success: **they find the HR route from the standing line and do not simply give up.** This is the test of §7.1 |
| **What would change the design** | Anyone refused twice in a row → the compression is set too conservatively (brief §12 puts the bar at ≤2%) · anyone photographing something misleading to get past the rule → the standing line is not being read · an approver pressing Approve without opening the bill → View bill is in the wrong place · an unreadable amount at 1600/q82 → **a bigger long edge, not a bigger cap** |

**Before any of that, and cheaper: the five real bills.** One DTC supervisor sends five
bills photographed as a driver would. Run them through 1600 / q82 and look at the amount.
One afternoon, and it is the brief's own kill criterion.

**And one thing a browser must do that this session could not:** render the prototype at
390 px, 360 px and 360 px at 200% text, and measure overflow, tap heights and contrast
(§2, §8).

---

## 12 · Where I depart from the brief, or from my own scan

Three departures. None changes what the brief promises anybody; all three are mechanism.

### 12.1 Two calls, not one — the brief's §3 says one

The brief says *"the form sends the file and the claim in one call… one call, so there is
nothing to split."* **I am drawing two: upload the file, then file the claim with its
reference.**

- **Why.** There is **no duplicate guard** on `apply_expense_claim`, so the no-answer state
  asks the person to retry a request that may already have landed. With the photo in the
  body that is 1 MB re-sent over 3G from a petrol pump. Two calls make the retry ~1 KB, let
  the picture be shown back before Send (which is the kill criterion's instrument), and put
  the size refusal **before** the amount is typed.
- **The reuse path the brief itself points at is already two calls** — `uploadMyDocument`,
  and `joining.html` uploads each file on its own.
- **The product promise is unchanged.** The refusal still comes from the server, at filing,
  in plain words. The brief's §3 sentence was reasoning about *when the rule fires*, not a
  decision about HTTP shape.
- **The cost, said out loud:** a file uploaded for a claim that is never sent is an orphan,
  so something has to tidy those up — and a draft that reaches the server **starts a
  retention clock earlier**. Both belong in D6.
- **Owner:** `hrms-business-analyst` to specify, `hrms-fullstack-engineer` to confirm.

### 12.2 Quality 82, not my 80

My scan recommended JPEG 80; DevOps measured 82 on this exact pipeline. **82 wins and 80 is
withdrawn.** What I kept is the **step-down order** — quality before width (§5).

### 12.3 What I deliberately did *not* design: the approver role

Brief §3.3 says the role is the one part of this slice with real design risk and must not
be waved through. I have **not** designed it. What I drew is only what the attachment work
forces into existence:

- **AP6**, the honest dead end when another role-holder has already acted. Without it, a
  second approver taps Approve on a decided claim and meets a server error.
- **EL2**, the employee's own row, which cannot name an approver that is a role.

**Everything else about the role is out of this design**: no role-queue screen, no "claims
for my role" list, no role picker, no settings screen (there is none, settled). If the
analyst's spec or the engineer's impact analysis shows the role flow is bigger than the
attachments, **the attachments stand alone as a complete outcome** — claims go to the
manager, exactly as today — and those two states travel with the role flow to wherever it
lands.

---

## 13 · Open decisions

### ⚠ DECISION — AQ1 · which element moves

**The question:** raise `.mpf-dv` above `.hm-ov`, or lower the sheet?
**Context:** measured, `panels.css:712` vs `:3064`. **Conflict:** none — it is a bug the
reuse plan walks into. **Affected:** every approver. **Recommendation:** **raise the
viewer to 1400.** Lowering the sheet is not available, because 1200 is already the
employee's own modal. Add it to `scripts/check_portal_trays.js`'s geometry checks, where
the profile case is already listed. **Risk if it waits:** the slice's WOW moment ships
blank and nothing looks broken. **Owner:** `hrms-fullstack-engineer`, at impact analysis.

### ⚠ DECISION — EC4 · what happens to an iPhone photo

**The question:** does the client re-encode satisfy the mandatory rule for iPhone filers,
and what does the server do with a HEIC that reaches it anyway?
**Conflict:** "mandatory everywhere" against "nobody honest is refused" (brief §3.2).
**Affected:** every iPhone filer — likely supervisors and office staff, not drivers.
**Options:** **(a) re-encode on the client, which yields a JPEG whatever arrived, and keep
the server's refusal as a backstop — recommended, and drawn**; (b) accept HEIC unchanged,
which means storing a second file type we cannot strip; (c) refuse it and accept that some
people cannot file. **Risk if it waits:** found at UAT by the persona most likely to be in
the room. **Owner:** `hrms-fullstack-engineer` for feasibility, with
`hrms-security-privacy-engineer` on (b). DevOps recommends the same thing (OPS-11) and adds
that the end-to-end iPhone upload has never been tested by anybody here.

### ⚠ DECISION — AQ2 · the CXO and the single claim

**The question:** should a System Manager's Home row open an **individual** expense claim at
all, now that it will carry a bill?
**Context:** `portal.js:6538` and `:6625` — for a System Manager that row "opens the
oldest". Brief §9 gives the CXO *"No. Summaries only."*
**Conflict:** the product's current behaviour against the brief's own access table.
**Options:** (a) the CXO row leads to a count and a screen, never a claim — consistent with
§9; (b) accept it and record it in the access table as a deliberate System Manager power.
**Recommendation:** (a). Either way, **this is pre-existing behaviour the attachment makes
visible, not something this slice creates.** **Owner:**
`hrms-security-privacy-engineer`, then Surbhi.

### ⚠ DECISION — OPS-1 · where a copy of these files lives

Not mine, and not strictly a design question, but it is the only item in DevOps §1 that
could change what we ship. **`BACKUP_BUCKET` is not set**, and every `bench backup` deletes
backup sets older than 23 hours. From the day a bill is mandatory, DTC's expense evidence —
a tax and audit record — exists on one server disk. **I am naming it here because my
design is what makes those files mandatory.** **Owner:** Surbhi, with
`hrms-devops-engineer`. **P1.**

### Q1 — manager or supervisor?

One word for one thing. **Recommendation: manager everywhere**, and fix
`field-checkin.html`'s stray "supervisor" when something next touches it. Does not block.

### Still open from the brief, not mine

**D1** — expense claims already submitted with no bill: the brief's §3.1 recommendation
(leave them decidable) is what the prototype draws, in `Approver · 6`.
**D6** — the retention clock and logging for evidence files. It now also has to cover
**orphan uploads** (§12.1) and the earlier clock a server-side draft starts. Owner:
`hrms-security-privacy-engineer`, with counsel.

**Nothing in this design is waiting on Surbhi's word except the four decisions above, and
three of those have a named recommendation she can simply approve.** The copy question that
was open this morning — the "No bill?" line — **is settled: she said yes.**

---

## 14 · What the business analyst must turn into acceptance criteria

**Behaviour**

1. The server refuses an expense claim with no file, and **the server's own sentence
   reaches `ec-error`** — tested by posting a claim with no file, not by looking at the
   form. Never a Python argument error, never "check your connection".
2. The same rule fires **at submit on `Expense Claim` itself**, so Desk, the REST API and
   data import obey it. **A draft with no file stays saveable.**
3. A regularization saves with **no** file and says nothing about it.
4. The caps are **ours**, after the re-encode: **1 MB image, 3 MB PDF**. Negative
   criterion: **`System Settings.max_file_size` is not the enforcement point** and is not
   changed by this slice.
5. The recipe: **long edge 1600 px, JPEG 82, quality 82 → 72 → 62, then width 1280 → 1024,
   then refuse.** Tested with a **real phone photo** (one committed fixture, per OPS-10),
   not a 200 KB synthetic one.
6. Accepted types are checked by **magic bytes, not extension**: JPEG, PNG, PDF.
7. **The chosen file survives Try again**, and the offline message says so.
8. The no-answer state **offers no re-send** — there is no duplicate guard.
9. One access-log row **per viewer per file per day**.
10. A per-user upload rate limit on the new path, reusing `field_app_limits._limited`
    (OPS-12).

**Words and position**

11. Every string in §7, verbatim, on the surface named, in English and Hindi.
12. **The day-fix notice is positioned before the file picker** — a *positional* assertion
    in the DOM, not a presence assertion.
13. **The "No bill?" line is standing text under the control and always visible**, on every
    state of the control — not only inside a refusal.
14. The size refusal has **one sentence per type**, each naming the real size and the real
    limit.
15. The Desk refusal's **first sentence is identical** to the portal's; the HR clause is
    additional and appears only on Desk.
16. The queue row says **"Bill attached" / "No bill attached" in words**; the row contains
    **no second interactive element** (negative criterion).

**Reviewer surfaces**

17. **The viewer renders above the decision sheet.** Assert the computed z-order, not that
    the element exists.
18. "View bill" is in the sheet **body, above the decision buttons**, never in the footer.
19. The viewer has `role="dialog"`, closes on Escape, and **returns focus to the button
    that opened it**.
20. **No `/private/files/...` URL reaches the browser**, on any of the four callers.
21. **No thumbnails, no preloading and no bulk open** in any list (negative criterion).

**Permissions — the door tests, as a plain staff login through the API on a fresh site**

22. A staff login cannot list another person's files: `/api/resource/File`,
    `frappe.client.get_list` on File, `frappe.client.attach_file`,
    `frappe.desk.reportview.get`, report view and export, link search, **and share**.
23. A role-routed claim **cannot be returned by the line manager's queue** through any of
    those doors. The company scoping lives **in the query**, because Frappe roles are not
    company-aware.
24. **Zero new `ignore_permissions` bypasses.** The existing one in `apply_expense_claim`
    is counted; this slice adds none.

**Still to translate.** The Hindi drafts in §7 are machine drafts and need a native
reviewer. Strings with no draft at all: the day-fix label, the five reviewer strings, the
"Opening the bill…" and failure lines, "Bill attached"/"No bill attached", "View full
size", "Replace", "Remove", and the viewer's footer.

---

## 15 · Not in this slice — put here so nobody builds it by reflex

More than one file · a gallery · thumbnails in any list · OCR or amount extraction ·
cropping · a settings screen of any kind · per-claim-type file rules · a "claims missing a
bill" report · a retention job of its own · a self-declaration type, template, flag or
form · routing on regularizations (no approver field, no role, no reason-level
configuration) · designing for a mixed Desk claim · evidence on leave applications · a
role-queue screen or a role picker (§12.3) · a progress percentage on the upload · an "are
you sure you want to send without a file?" confirm on the regularization — it is optional,
and a confirm on an optional field is a nudge.

---

## 16 · Assumptions

- `[ASSUMPTION]` **The browser canvas converts HEIC.** Safari decodes HEIC, so a canvas
  re-encode yields JPEG. Nobody here has tested it end to end. §11 Task 2 is that test, and
  state 7b is the design for when it fails.
- `[ASSUMPTION]` "manager" is the right word on the day-fix notice (Q1).
- `[ASSUMPTION]` The ESS portal is the only phone surface that needs this — the field app
  is check-in only. Carried from the brief §15.
- `[ASSUMPTION]` One file per form is enough. A claim is one bill at DTC.
- `[ESTIMATE]` A real photographed bill lands at 250–600 KB at 1600/q82. DevOps' measured
  145 KB is on a low-detail synthetic source and is optimistic.

---

## 17 · Subtract pass — what I deleted

Read once more asking only *what can I remove and still meet the requirement?*

**Removed from my own scan's output:** the "+30% longer words" review switch (the Hindi
switch already proves Devanagari length — one control instead of two); a separate note
block on every single prototype state (they now appear only where the state teaches
something that is not obvious); a second viewer state for "the file was deleted" (the
generic open-failure sentence covers it, and a deleted file is not a case this slice
creates); a "Remove" button on the expense control (the file is mandatory, so Replace is
the only sensible verb — Remove survives only on the optional day-fix form); and an
explicit "camera denied" error state, which I replaced with the honest hint in state 2
because **a denied camera returns no file and no error, so a definite error message would
be a guess.**

**Removed from the brief's shape, in §12.3:** every role screen except the two states the
attachments actually force.

**Kept deliberately, though each costs something:** the shown-back picture with its size —
it is the only way a person can tell their own bill is readable, and it is the kill
criterion's instrument; the standing "No bill?" line — one grey line against somebody
losing their money, now settled copy; and the `Approver · 5b` state, which draws a bug
rather than a screen, because the whole slice ships blank without it.

**What is left:** one file control on two forms, two buttons on it, one shown-back file,
one notice, four refusals, one agreed recipe, one word on two queue rows, one button in one
sheet, one generalised viewer, one z-index, and four `<label for>` attributes.
