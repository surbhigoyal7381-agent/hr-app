---
slice: 081-bill-and-evidence-attachments
artifact: 02-functional-spec
author: hrms-business-analyst
date: 2026-11-03
status: ready
inputs: [01-product-brief.md, 01a-ux-opportunities.md, 01b-ux-design.md, prototype-v1.html, 01c-security-privacy-requirements.md, 07-devops-inputs.md]
---

# Slice 081 — Functional spec: a bill on an expense claim, evidence on a day-fix

**Read §0 first. The slice got smaller today, and the reason matters more than the change.**

---

## 0 · Scope — what this slice is, and what left it

### 0.1 The decision, and who took it

**Surbhi's decision, 3 November 2026: ship the bills first. The approver role moves to its
own slice.** This spec covers the attachments only.

**Why, in one paragraph.** The brief's §3.3 promised that a sensitive claim type routes to
an approver role, so a line manager never opens a medical receipt. The security engineer
then read the code and found that **the promise does not hold today** (`01c` §0.1,
**Confirmed fact**): `Expense Claim` has **no `permission_query_conditions` and no
`has_permission` hook** in either app — verified in `hrms/hrms/hooks.py:155-185` and
`alvoraa_portal/alvoraa_portal/hooks.py:448-473`, where six other doctypes do have the pair
and this one does not. Every staff login carries a broad own-record Employee User
Permission, `Employee` is a nested set on `reports_to`, and Frappe extends an own-record
permission to every descendant. So a line manager who sees nothing in their portal queue
can still fetch a routed claim — and then its bill — through `/api/resource/Expense Claim`,
`frappe.desk.reportview.get`, the report view, a CSV export, link search or share.

**So routing without the permission pair would put a false protection in front of a medical
receipt.** That is worse than today, because today nobody believes routing protects
anything. The honest order is **bills first, routing as its own slice.**

### 0.2 In scope for 081

| In | Where it comes from |
|---|---|
| A file on the portal expense claim form — **mandatory**, refused by the server in plain words | Brief §3, design §7.1 |
| The mandatory rule enforced **on the document at submit**, so Desk, the REST API and data import obey it; a draft with no file stays saveable | Brief §3 (D4), 081-SEC-3 |
| A file on the portal day-fix (attendance regularization) form — **optional**, with the notice **before** the file picker | Brief §3.4 (D9), 081-SEC-8 |
| Compress on the phone, re-encode and cap on the server: long edge 1600 px, JPEG 82, quality ladder then width ladder; **1 MB stored for an image, 3 MB for a PDF** | Design §5, OPS-3, 081-SEC-5 |
| Magic-byte type check; **our** stored file name, extension and served content type; HEIC refused in words; images stripped; PDF accepted and never parsed | 081-SEC-4, 081-PRIV-2 |
| "Bill attached" / "No bill attached" in words on the approver's queue row; **View bill** in the sheet body; the viewer above the sheet | Design §7.7, findings AQ1/AQ5 |
| "Evidence attached · View" on HR's day-fix card | Design §7.8, HQ1 |
| The employee sees their own file on their own claim row and day-fix card | Design §7.5, §7.6, findings EL1/AR3 |
| One guarded endpoint streams the bytes; no `/private/files/…` URL ever reaches a browser; one file per tap; a per-user rate limit | 081-SEC-6, OPS-7, OPS-12 |
| One access-log row per viewer per file per day, on the existing table, plus the employee's own answer to "who opened mine" | 081-PRIV-3 |
| Retention: two clocks, legal hold, orphan sweep, counts per pass, never "for ever" | 081-PRIV-1, OPS-15, OPS-16 |
| Four `<label for>` attributes on the expense modal's existing inputs | Design EC8 |
| **All of 081-SEC-3 … 081-SEC-8 and 081-PRIV-1 … 081-PRIV-5** | `01c` §17 |

### 0.3 Out of scope for 081 — the approver role, entirely

**Nothing about the approver role is built here.** No approver-role field on
`Expense Claim Type`, no role resolution, no role-scoped queue, no company scoping of a
role, no `permission_query_conditions` / `has_permission` pair on `Expense Claim`, no
routing.

**Expense claims keep going to the employee's own approver, exactly as they do today** —
`hr_api.expense_approver_for()` reads `Employee.expense_approver`, falls back to the first
`Department Approver`, and refuses to file when there is nobody (**Confirmed fact**,
`hr_api.py:2451-2466`). That path is untouched by this slice.

**081-SEC-1 and 081-SEC-2 belong to the routing slice, ALV-301.** They are listed in the
traceability table as *moved — Surbhi's decision, 3 Nov 2026*, not as gaps.

### 0.4 Carried forward, drawn but not built

Two prototype states exist only because a role creates them. **They ship wherever the
routing slice ships, and they are not built in 081.**

| Prototype state | What it is | Why it is not 081 |
|---|---|---|
| `Approver · 7` — the "Already decided" dead end (design AP6) | *"Priya Nair approved this 4 minutes ago. There is nothing for you to do."* | Only a role puts two people in front of one claim. With a single named approver this state is unreachable |
| `My expense claims` — the status chip reading **"Waiting for approval"** with no name (design EL2) | A role has no name a driver would recognise | With a single named approver the row can keep naming the approver, as it does today |

**Consequence for the row today:** the employee's claim row keeps today's wording. **081
does not change the status chip.** The "Waiting for approval" wording is the routing
slice's to ship.

### 0.5 ⚠ The medical-bill exposure — named, accepted by Surbhi, **not fixed here**

**Bad news, stated plainly and not softened. The facts below are unchanged by her
decision: accepting a risk is not the same as the risk going away, and this section does
not blur the two.**

From the day this slice ships, **every expense claim must carry a file**. A medical
reimbursement claim therefore goes to the employee's **line manager**, as all claims do
today, and **that manager can open the bill** — both through the queue, which is the
intended path, and through the API doors listed in §0.1, which is not.

- **Counsel, 1 November 2026 (ALV-249, relayed by Surbhi): passport and health data are not
  for managers.** That advice is **not discharged by this slice.**
- **081 makes the exposure more likely, not less**, because the file is now compulsory:
  `01c` §12 R5 — *"the mandatory rule raises volume and therefore raises the chance that
  identity and medical documents arrive at all."*
- **The answer is the routing slice, ALV-301** — the approver role plus the
  `permission_query_conditions` / `has_permission` pair (081-SEC-1, 081-SEC-2). Nothing
  else closes it.
- **No substitute control is specified here.** I have not invented a warning, a tick, a
  claim-type block or a screen-level hide. A screen-level control would be the false
  protection §0.1 exists to avoid, and `data-doors.md` forbids it in so many words.
- **081-PRIV-5 applies with full force:** no spec sentence, UI string, release note or
  questionnaire answer may say or imply a bill is masked, protected, secure or hidden.

#### The decision, with its reason — Surbhi, 3 November 2026

**OQ-3 is closed. Slice 081 ships with mandatory bills**, accepting that a line manager can
open a medical receipt until the routing slice lands.

**What she was shown before deciding**, so a reader in six months can see this was
considered and not missed:

1. **Counsel's advice of 1 November 2026 (ALV-249): passport and health data are not for
   managers.**
2. That **081 makes the exposure more likely, not less**, because the bill is now
   compulsory on every claim.
3. That the **only** answer is the routing slice, and that **no substitute control** was
   being offered — a screen-level hide would be the false protection the split exists to
   avoid.

**Her decision, in her own words:**

> *"i dont see it as a big risk, as such expenses like medical bills are just the part of
> the CTC and are just a formality."*

**Her reasoning:** medical reimbursement at DTC is a **CTC component and a formality** — a
pay element claimed back on paperwork — rather than a sensitive health disclosure. On that
reading the manager is seeing a routine pay formality, not a medical record.

**What that decision does and does not change:**

| | |
|---|---|
| **Does** | 081 ships. The build is not held. The Ready check's OQ-3 box is closed |
| **Does not** | **Counsel's 1 November advice is accepted-but-not-discharged.** It is not withdrawn, not satisfied, and not reinterpreted by this decision |
| **Does not** | The exposure in the bullets above remains true, word for word. **Nothing here may be quoted as "the risk was found to be low"** — it was *accepted*, by a named person, on a stated business reading |
| **Does not** | Remove the answer. **The routing slice — ALV-301 — remains the only thing that closes it**, and `01c`'s fail-closed rule still stands: the routing must not ship without the permission pair |

**Risk R-1 therefore stays OPEN in §17**, marked accepted by Surbhi on 3 November 2026 with
her reason and pointing at **ALV-301**. A risk somebody has accepted is still a risk on the
register; it is just no longer waiting for a decision.

---

## 1 · Cross-module reach — named before anything is specified

| App | Touched? | How |
|---|---|---|
| **`alvoraa_portal`** | **Yes, the whole slice** | A new module for the upload / stream / log / housekeeping; changes to `hr_api.apply_expense_claim`, `attendance_correction.raise_correction`, `inbox_api._part_expense_approvals`, the day-fix queue, `portal.js`, `request-modals.html`, the portal CSS, `hooks.py`, `patches.txt` |
| **`hrms`** | **Yes, lightly** | Two Custom Fields (`alvoraa_legal_hold`) on `Expense Claim` and `Attendance Request`, created the way `branch_scope.after_migrate` already creates `alvoraa_branch` on both (**Confirmed fact**, `branch_scope.py:22-36`). One `before_submit` hook on `Expense Claim`. No change to any hrms Python file |
| **`erpnext`** | **No** | `Expense Claim` and `Attendance Request` live in `hrms`. No ERPNext file changes |
| **`frappe`** | **No change, heavy reuse** | Standard `File` rows, `upload_file`'s shape, `frappe.local.response` streaming. **`System Settings.max_file_size` is read by nobody in this slice and is not changed by it** (081-SEC-5 clause 2, OPS-6) |
| **`alvoraa_goals`** | **No** | Goals already carry an evidence attachment; explicitly out of scope (brief §8) |
| **`alvox_compensation`** | **No** | Not installed in the live path |

**HRMS domains involved:** **attendance** (regularization evidence) and **expense claims**
(the bill). **Payroll** is touched only indirectly — an expense claim books to the ledger
through `payable_account` and `cost_center`, which this slice does not change. **Leaves,
appraisals, goals, org structure and learning: not touched.**

**Personas specified throughout:** **Employee** (own record; the frontline driver wins every
trade-off), **Line manager / expense approver**, **HR Manager / HR User**, **CXO / System
Manager**, and **Finance**.

---

## 2 · Questioning the ask before specifying it

Three checks, as the method requires. All three pass, and one produces a cut.

| Check | Answer |
|---|---|
| **Is the stated problem the real one?** Yes. The brief does not say "claims are slow" and then guess at a cause. It says a bill cannot reach an approver at all, and the code agrees: `apply_expense_claim(expense_type, expense_date, amount, description)` takes no file, and `_part_expense_approvals` returns no file (**Confirmed fact**, read today). The cause and the symptom are the same thing |
| **What happens after?** Every new surface drives a decision. "Bill attached" on the queue row changes whether the approver taps Approve. "View full size" on the employee's own row is the only way a driver learns their own photo came out readable — which is the kill criterion's instrument (design EL1). **No screen in this slice merely displays** |
| **Is anything a habit rather than a requirement?** Yes, one. The design's AQ2 — a System Manager's Home row opening an individual claim — is **pre-existing behaviour nobody specified**, and the attachment is what makes it matter. I have **not** specified a fix. It is **OQ-2**, carried for Surbhi |

---

## 3 · Gap analysis — what the installed code already does

Every "today" cell was read in the source in this worktree on 3 November 2026.

| Requirement | Standard / installed behaviour today | Verdict | Cost |
|---|---|---|---|
| Attach a file to an expense claim in Desk | **Already works.** `allow_attachments` no longer exists as a DocType field; the sidebar shows on any saved document with `write` permission (**Confirmed fact**, brief §1.1) | **Already there** | — |
| Attach a file to an expense claim from the portal | **Nothing.** `request-modals.html` L65-99 has Type, Date, Amount, Purpose. `apply_expense_claim` takes four arguments, none a file | **Build new** (new code, no new DocType) | M |
| Attach a file to a day-fix from the portal | **Nothing.** `raise_correction(from_date, to_date, reason, explanation, half_day, half_day_date)` — **Confirmed fact**, `attendance_correction.py:979` | **Extend** (one argument, one bind step) | S |
| A `Attach` field on either doctype | Neither has one. In all of `hrms/hr/doctype` only Travel Request, Job Applicant, Employee Referral and Appraisal do | **Drop the idea.** A standard `File` row attached to the document is cheaper and gives Desk the sidebar for free | — |
| Refuse a claim with no file | Nothing refuses it | **Extend** — one `before_submit` hook beside the two already registered on `Expense Claim` | S |
| Shrink and strip an image | **`employee_photo._reencode`** — one Pillow call, `convert("RGB")` → `thumbnail` → `save(JPEG, quality, optimize=True)`, no `exif=`, no `icc_profile=` (**Confirmed fact**, read today) | **Reuse, parameterised** on edge and quality | S |
| Length-before-decode, magic bytes | **`employee_photo._decode`** — string length first, then strict base64, then `MAGIC = (JPEG, PNG)` + a RIFF/WEBP test | **Reuse, plus `%PDF-`** | S |
| Serve a private file without handing out its URL | **`employee_documents_read.open_employee_document`** — guard, then `get_content(encodings=[])` into `frappe.local.response` | **Reuse the shape** on a new parent | M |
| Record who looked | **`Alvoraa Photo Access Log`** exists, with a `source` Select whose own description says a third kind of looking is *"a WHERE clause, not a redesign"* | **Configure + extend:** two `source` options and one new `reference_name` field. **No new DocType** | S |
| Per-user rate limit | **`field_app_limits._limited(SELF_KEY, "user", limit=60)`** as used by `open_employee_document` | **Reuse** | S |
| A per-file ceiling | `System Settings.max_file_size` is **0** locally → Frappe's 25 MB default. **Must not be used**: site-wide, whole megabytes, and at 1 MB it would refuse the raw photo before we compress it and break employee documents (OPS-6, design §0.3) | **Drop** — the caps live in our own code | — |
| Legal hold on a record | **`alvoraa_legal_hold`** Custom Field pattern already exists on `Employee Checkin` (**Confirmed fact**, `field_checkin.py:1177`, read by `field_app_photos.py:156-157`) | **Configure** — the same Custom Field on two more doctypes | S |
| A retention job | **`field_app_photos.purge_old_checkin_photos`** and **`joiner_housekeeping.daily`** are the two patterns: cutoff, legal-hold filter, `delete_doc(..., delete_permanently=True)`, one count line | **Extend** — one new daily entry, three passes, no new queue (OPS-15) | M |
| A row-level gate on `Expense Claim` | **None exists.** No `permission_query_conditions`, no `has_permission` | **Moved to the routing slice** (Surbhi, 3 Nov 2026) | — |
| Multiple files, a gallery, OCR, a settings screen, a "claims missing a bill" report, a self-declaration doctype | None of it exists | **Drop** — on the brief's and the design's do-not-build lists | — |

**Ladder rung: 4 — new code**, for one new module in `alvoraa_portal` plus edits to existing
functions. Rung 0 (*already there*) is true on Desk and false on the portal, which is where
staff are. Rung 1 (*configuration*) has nothing to set — the box is gone and `max_file_size`
is the wrong lever. Rung 2-3 (*customisation*) cannot put a file control on a hand-written
portal page; a Property Setter has nothing to set. **Rung 5 (new DocType) and rung 6 (new
app) are rejected and not needed:** the file is a standard Frappe `File` row and the access
log already exists. The only configuration-rung items are the two `alvoraa_legal_hold`
Custom Fields and the two new `source` options.

### 3.1 Two data models describing the same thing — the source of truth

| Thing | Source of truth | How the other stays in step |
|---|---|---|
| **The evidence file itself** | The **`File` row** attached to the parent document (`attached_to_doctype` + `attached_to_name`). There is no second record, no field on the claim, no child row | Nothing to keep in step. Every reader — our endpoint, the Desk sidebar, every retention pass — asks `File` by parent. This is why OPS-17 is a P1: an unparented file is invisible to all three |
| **Who opened a file** | **`Alvoraa Photo Access Log`**, one row per viewer per file per day | The two existing sources (`Check-in photo`, `Employee document`) are untouched; this slice adds two more `source` values and one `reference_name`. The job and the subject's own view filter on `source` — a WHERE clause, as the doctype intended |
| **The retention clock's anchor** | **The parent document**: `Expense Claim.posting_date` for a bill, `Employee.relieving_date` for a day-fix file. **Never `File.creation` and never `modified`** (OPS-16; the `modified` lesson is already written into `alvoraa_joiner_submission.py:50-58`) | An orphan has no parent and therefore no anchor, which is exactly why it gets its own short window |

---

## 4 · Process flow

### 4.1 The expense claim, happy path (employee, phone)

1. The driver pays ₹420 at the pump and opens **New Expense Claim** in the portal.
2. The **first** control in the modal is **"Photo of the bill · required"**, with two
   buttons and a standing grey line: *"No bill? Ask HR to file this claim with your signed
   statement of what you spent."*
3. He taps **Take a photo of the bill**; the back camera opens (`capture="environment"`).
4. **Decision point — can this browser decode the picture?**
   - No → *"This phone could not read that picture…"*; **nothing has been sent**; both
     buttons stay. (State 7b.)
   - Yes → the browser re-encodes it on a canvas at long edge 1600 px, JPEG 82, targeting
     ≤ 900 KB. Screen says *"Making the picture smaller…"*.
5. The shrunk picture is uploaded on its own call. Screen says *"Sending the picture…"*.
6. **Decision point — the server's checks, in order:** string length → base64 → magic bytes
   → re-encode (image) or pass through (PDF) → cap.
   - Refused → one sentence naming the real size and the real limit, or the real type.
   - Accepted → the picture is shown back with **"Bill attached · 380 KB · 1600 px ·
     bill-03-nov.jpg"** and **View full size** / **Replace**.
7. He types the type, the date, ₹420 and a purpose, and presses **Submit Claim**.
8. **Decision point — the server's mandatory check.** No file reference → the server's own
   sentence in `ec-error`. With one → the claim is created, the file is bound to it, the
   modal closes, a toast says **"Expense claim submitted."**, and the new row already reads
   **Bill attached · View full size**.

### 4.2 The unhappy paths, and what each does

| What goes wrong | What happens |
|---|---|
| Camera denied or cancelled | *"Nothing was chosen. If the camera will not open, use Choose a file."* Both buttons stay. **No definite error message**, because a denied camera returns no file and no error |
| Image still over 1 MB after the full ladder | *"This photo is still 3.4 MB after we shrank it. The limit is 1 MB — take it again with just the bill in the frame."* |
| PDF over 3 MB | *"This PDF is 7.2 MB and the limit is 3 MB. Send one page with the bill on it, or photograph the bill instead."* |
| Not a JPG / PNG / PDF, by magic bytes | *"We can take a JPG, a PNG or a PDF. Most phones can take a JPG — try again from the camera."* |
| A HEIC that reaches the server | The same sentence. **HEIC is refused, not converted** (081-SEC-4 clause 4) |
| The upload call itself fails | The chosen file is **still held in the page**. *"We could not send the picture. Nothing was lost."* + **Send the picture again** |
| Submit with no file | The **server** refuses: *"A claim needs a photo or a PDF of the bill. Please attach one and send it again."* |
| Offline at Submit | *"We could not reach the office. Nothing was sent."* / *"Your details **and your bill** are still here. When you have signal, tap Try again."* |
| No answer at Submit | *"No answer from the office. It may have gone through."* / *"Look in your list before you send it again."* — **Try again is removed.** There is no duplicate guard on `apply_expense_claim` |
| The claim is never sent | The uploaded file is an **orphan**, swept within 24 hours |
| HR submits a Desk claim with no attachment | Refused at submit: *"This claim cannot be submitted yet"* + the portal's own first sentence + the HR-only clause + *"The draft is still saved. Only Submit is blocked."* |
| HR **saves** a Desk draft with no attachment | **Accepted.** A draft is a working document |

### 4.3 The day-fix, employee

1. The employee taps an absent day; the form opens inside the day row.
2. Reason → *"Anything HR should know"*.
3. **"Add a photo or document if you have one"**, then **the notice**, then the two buttons.
   The notice is **above** the buttons, inside the same block, in plain grey:
   *"Your manager reads this request, and will see any file you attach. Attaching one is
   your choice — HR can fix the day without it."*
4. **Decision point — attach or not.** Both lead on. **Send works with nothing attached and
   says nothing about it.**
5. **Ask HR to fix this day** → the request is created and any file is bound to it.

### 4.4 The reviewer

1. Home → **Pending for you**. The queue row is one `<button>` and carries a third line in
   words: **Bill attached** or **No bill attached** (grey, not red — it is not an error).
2. Tap → the decision sheet: amount, type, date, the note, how long it has waited.
3. **View bill** sits in the **sheet body, above the decision buttons** — never between
   Approve and Decline, because the evidence is read before the act that cannot be undone.
4. Tap → *"Opening the bill…"* → the viewer opens **above** the sheet. Escape closes it and
   focus returns to **View bill**. The sheet is untouched.
5. **Decision point** — Approve or Decline-with-a-reason. Unchanged by this slice.
6. An older claim with no file: the sheet says plainly there is nothing to open.

HR's day-fix card carries **Evidence attached · View** and nothing else. The card is not a
single button, so **View** is a real button there.

---

## 5 · Data model

### 5.1 New DocTypes: none

**Confirmed fact:** the evidence is a standard Frappe `File` row. No new DocType, no new
child table, no new field on `Expense Claim` or `Attendance Request` to hold a file.

*Why can't an existing field carry this?* It already does: `File.attached_to_doctype` +
`File.attached_to_name`. An `Attach` field on the parent would duplicate the url in a second
place and would have to be kept in step with the `File` row; the standard attachment gives
the Desk sidebar for free (brief §1.3).

### 5.2 Changes to `Alvoraa Photo Access Log`

| Fieldname | Label | Fieldtype | Mandatory | Default | Options / notes | Why can't an existing field carry it? |
|---|---|---|---|---|---|---|
| `source` *(existing — options extended)* | What was opened | Select | no | `Check-in photo` | `Check-in photo`<br>`Employee document`<br>**`Expense bill`**<br>**`Day-fix evidence`** | The field exists and its own description anticipates this. Existing rows keep their value — every pre-078 row really was a check-in photo |
| `reference_name` **(new)** | Reference | Data | no | — | `read_only: 1`, `search_index: 1`. Holds the parent document's id (`EXP-CLM-2026-00123`) and nothing else | `document_type` is a **Link to `Employee Document Type`** (**Confirmed fact**, read the JSON) — putting `"Expense Claim"` in it is a broken link. `checkin` is a Link to `Employee Checkin`. **There is no field that can name a claim** |

**Not added, deliberately:** no `reference_doctype` field. The `source` value already says
which doctype it is — two values, two doctypes — and a second column nothing filters on is
the kind of field 081-PRIV-4 forbids.

### 5.3 Custom Fields — two, both the existing pattern

| DocType | Fieldname | Label | Fieldtype | Default | Notes |
|---|---|---|---|---|---|
| `Expense Claim` | `alvoraa_legal_hold` | Legal hold | Check | `0` | Created in `after_migrate` and on install, exactly as `branch_scope.after_migrate` creates `alvoraa_branch` on this doctype already. Read by the retention pass as a filter, never written by it |
| `Attendance Request` | `alvoraa_legal_hold` | Legal hold | Check | `0` | Same |

*Why can't an existing field carry this?* Nothing on either doctype means "do not delete
this". 081-PRIV-1 makes legal hold mandatory and says it always wins. The field name and
the read pattern are copied from `Employee Checkin.alvoraa_legal_hold` so one grep finds
every holder.

### 5.4 Settings — one key, and its shape is **OQ-1**

| Key | Label | Default | Range | Rule id |
|---|---|---|---|---|
| `alvoraa_expense_evidence_years` | How long a bill is kept | **8** financial years | **8-25**, refuses blank, 0 and anything below 8 | `081-PRIV-1` |
| `alvoraa_dayfix_evidence_months` | How long a day-fix file is kept after someone leaves | **6** months | **6-24**, refuses blank and 0 | `081-PRIV-1` |

Both follow `hrms/alvoraa_org_structure/settings.py`'s existing shape — `DEFAULTS`,
`ACCESS_GRANTING` where relevant, `RULE_FOR_KEY`, `LABELS`, and the `_DAYS`-style range
refusal at `settings.py:502-520` (**Confirmed fact**, read today).

**Whether these are settings at all is OQ-1, and it is not mine to close.** The ACs are
written so that the *behaviour* is testable either way (AC-59 … AC-66), with AC-65 — the
refusal of 0, blank and an out-of-range value — applying only if the setting ships.

### 5.5 New and changed endpoints — the complete list (081-PRIV-4)

| Endpoint | New / changed | What it does | Rate limit |
|---|---|---|---|
| `expense_evidence.upload_evidence(file, kind)` | **New** | Length → magic bytes → re-encode or pass → cap → store one **private, unparented** `File` owned by the caller, with **our** generated name. Returns `{file_url, bytes, label}` | `_limited(SELF_KEY, "user", limit=60)` |
| `expense_evidence.open_evidence(parent_doctype, parent_name)` | **New** | Parent permission check → stream the bytes → one log row. One file per call | `_limited(SELF_KEY, "user", limit=60)` |
| `expense_evidence.who_opened_mine()` | **New** | The caller's **own** files only: reader and day. Refuses any argument naming somebody else | — |
| `expense_evidence.counts()` | **New** | HR only. Two numbers (OPS-19): submitted claims with no file; orphans in the last 7 days. Reuses the `joiner_counts` shape from 078 | — |
| `hr_api.apply_evidence_claim` → `apply_expense_claim(expense_type, expense_date, amount, description=None, file_url=None)` | **Changed** | Refuses with no `file_url`; binds the file to the new claim | existing |
| `attendance_correction.raise_correction(..., file_url=None)` | **Changed** | Binds the file if one is given; says nothing if not | existing |

**Four new whitelisted endpoints, and no more.** Each goes into
`docs/security/whitelisted-endpoint-review.md`. AC-78 asserts the count.

### 5.6 The bind step — where the file gets its parent

**`attached_to_doctype` and `attached_to_name` are set by the same server call that creates
the parent document**, inside the same transaction, before the response is returned. The
`File` row is **moved, not copied**: one row, two fields written.

| Check, in order | Refusal |
|---|---|
| The `File` row exists and `is_private = 1` | Generic refusal, logged with the row id and no file name |
| `File.owner == frappe.session.user` | Same |
| `File.attached_to_name` is **empty** — a file already bound to something is never re-parented | Same |
| The parent is the document this call just created for this caller's own employee | Same |

**One `File` row per parent.** A second upload creates a new unparented row, the client
sends the newer url, and the older row is swept as an orphan. 081-SEC-5 clause 3 is met by
construction: the bind only ever happens once per parent, at creation. **A Desk attachment
is Frappe's own path** — see §5.7.

### 5.7 Desk attachments — what this slice does and does not do to them

**Stated plainly, because it is a real limit.**

| | Portal path | Desk sidebar / REST `upload_file` / data import |
|---|---|---|
| Magic-byte type check | **Ours** | Frappe's own |
| Re-encode, strip, 1 MB / 3 MB caps | **Ours** | **Not applied.** Frappe's `max_file_size` (25 MB locally) applies |
| Generated stored file name | **Ours** | **Ours** — through the `File` hook below |
| The mandatory rule at submit | **Yes** | **Yes** — it is on the document |

**The generated name is made true on every door by one hook**, not by the portal:
`doc_events["File"]["before_insert"]` → a function that returns immediately unless
`attached_to_doctype` is `Expense Claim` or `Attendance Request`, and otherwise replaces
`file_name` with `{parent}-{short hash}{our extension}`. That is what makes 081-PRIV-2 a
rule rather than a portal habit (`data-doors.md`: *"a rule that lives only in our portal
code is not a rule"*).
`[UNVERIFIED — engineer to confirm]` that `before_insert` is the correct hook point for
`File` and that `file_url` follows the renamed `file_name`. If it is not, the engineer says
so at impact analysis rather than moving the rule into the portal.

**Named limit, accepted:** a bill attached in Desk is **not** re-encoded, **not** capped at
1 MB and — if it is a PNG — **not** stripped of EXIF, because Frappe's own
`strip_exif_metadata_from_uploaded_images` runs for `image/jpeg` only
(`file.py:813-819`, **Confirmed fact**). HR is the uploader, the volume is small, and
capping Desk would refuse a legitimate scanned self-declaration. **Risk**, carried into §13
as R-7.

---

## 6 · States and transitions

### 6.1 The documents' own states — unchanged by this slice

`Expense Claim` is submittable (**Confirmed fact**, `is_submittable: 1`). This slice adds
**no workflow, no new status value and no new state field**. It adds one gate on one
existing transition.

| State | Allowed roles | Next states | Read-only | Notified | Reversible |
|---|---|---|---|---|---|
| **Draft, no file** | Employee (portal: never saved as a draft — the modal sends or it does not); HR Manager, HR User, Expense Approver, System Manager in Desk | Draft with a file; deleted | nothing | nobody | yes |
| **Draft, no file → Submitted** | — | **Refused.** The new `before_submit` gate | — | nobody | n/a |
| **Draft, with a file → Submitted** | the holders of `submit` on `Expense Claim`: HR Manager, Expense Approver, System Manager (**Confirmed fact**, read `expense_claim.json` permissions — the **Employee** role holds `create`, `read`, `write`, `share`, `print`, `email` and **no `submit`**) | Approved / Rejected, then Paid / Cancelled | Frappe locks submitted fields | the approver, by Frappe HR's own share | by cancel + amend |
| **Submitted before 081 shipped, no file** | — | decides normally | — | — | **Never refused.** The rule fires at submit, and these are already past it |
| **Cancelled** | as today | Amended | — | — | **The bill is kept** to the statutory clock (081-PRIV-1 clause 1) |
| **Amended** (`amended_from` set) | as today | needs its **own** file before submit | — | — | see AC-13 |

`Attendance Request` keeps its own existing states — the portal's `alvoraa_review_status`
of `Waiting` / `Declined` / `Withdrawn` on top of docstatus, read through
`attendance_correction._state` (**Confirmed fact**). **This slice adds nothing to them.** An
attached file never changes a state and never blocks one.

### 6.2 The file's own lifecycle

| State | How it gets there | Who can read it | What ends it |
|---|---|---|---|
| **Unparented** (`attached_to_name` empty, private, owned by the uploader) | `upload_evidence` returned | the uploader only — Frappe's gate falls back to `owner == user` | bound to a parent, **or** swept within 24 hours |
| **Bound** | the parent's creation call | the parent's readers (§7) | the retention pass, at the parent's clock |
| **Erased** | the retention pass or a Desk delete | nobody | **terminal, and permanent.** `delete_permanently=True`, bytes included. **There is no soft-delete and no "deleted" flag anywhere** (counsel, 18 Sep 2026) |

**Terminal states: Erased** (both clocks, and the orphan sweep). **Nothing is reversible
once erased** — that is the requirement, not a side effect.

---

## 7 · Permission and visibility matrix

### 7.1 The doors, and who enforces them

| Door | What enforces it in this slice |
|---|---|
| The parent document's read permission | Frappe's own role permissions + the broad own-record Employee User Permission + Frappe HR's DocShare from `expense_approver` + `alvoraa_branch` User Permissions. **Unchanged by 081** |
| The bytes, through our endpoint | `open_evidence` checks `frappe.has_permission(parent_doctype, "read", parent_name)` **on the parent** — never on a child row, because `has_permission` on a child table answers False for everybody (ALV-256, **Confirmed fact**) |
| The bytes, through Frappe's own `/private/files/…` route | Frappe's gate: Administrator → not private → `owner == user` → DocShare → **the parent's read permission**. **Defence in depth plus the log, not a boundary** (081-SEC-6) |
| The `File` row's metadata | **Frappe's own File list condition, which is wider than the parent's read** — see §7.4 |

### 7.2 Role × DocType × action

| Role | Expense Claim | Attendance Request | File (evidence) | Alvoraa Photo Access Log |
|---|---|---|---|---|
| **Employee** (own record) | C R W S(hare) P E · **no submit, no cancel, no delete** | C R W D S P E X · no submit | create through `upload_evidence` only; read **own** through `open_evidence` | **no read.** Their own answer comes through `who_opened_mine()` |
| **Line manager** (via `reports_to` tree permission + DocShare as `expense_approver`) | R, and submit where they hold `Expense Approver` | R (their report's day) | read the file of a claim or request they can read | no |
| **Expense Approver** | C R W Submit Cancel Amend D S P E | — | as above | no |
| **HR User** | per `expense_claim.json`, within their companies and branches | C R W Submit Cancel Amend D S P E X | read within scope | no |
| **HR Manager** | full, within scope | full, within scope | read within scope | **read, report, export** (existing rows) |
| **Finance** (as configured by the tenant; no new role) | R the claim they pay | **no** | the bill of that claim | no |
| **System Manager / CXO** | existing powers | existing | existing | read, report, export |
| **Guest** | **nothing.** No public page, no token, no bearer link in this slice | nothing | nothing | nothing |

### 7.3 The negative cases — who must **not** see this

| Must not | Enforced by | Status in 081 |
|---|---|---|
| A colleague with no reporting line must not read another person's bill or day-fix file, on any door | the broad own-record Employee User Permission on `Employee`, which does not reach a non-descendant | **Met today.** AC-50 proves it per door |
| An employee must not read another person's file through `open_evidence` by passing a parent id | the parent permission check inside the endpoint | **Met.** AC-51 |
| An employee must not be handed a `/private/files/…` address, on any of the four callers | the endpoint streams bytes; the viewer gets a blob | **Met.** AC-52 |
| Nobody must be able to list another person's **file names** | **Not met, and not fixable cheaply** — see §7.4 | **Residual risk R-2**, reduced by generated names (AC-16) |
| An employee must not see who opened somebody else's file | `who_opened_mine()` is scoped to the caller's own and refuses an argument | **Met.** AC-37 |
| **A line manager must not read a routed medical bill** | the `permission_query_conditions` / `has_permission` pair | **NOT MET. Moved to the routing slice.** §0.5 |
| A role-holder in the wrong company must not read a claim | 081-SEC-2 | **Moved to the routing slice** — no role exists in 081, so there is nothing to scope |
| Nothing new may bypass permissions | the CI ceiling | **Met.** AC-61 |

### 7.4 The one visibility delta this slice creates, and it is metadata

**Confirmed fact, verified by the security engineer by running
`frappe.core.doctype.file.file.get_permission_query_conditions(user)` on the local bench:**
for a login holding only `Employee` / `Desk User`, Frappe's own `File` list condition is
`is_private = 0 OR (attached_to_doctype IS NULL AND owner = me) OR attached_to_doctype IN
(<every doctype I can read at all>)`, and both `Expense Claim` and `Attendance Request` are
in that list.

**So any staff login can list the stored name, the size and the `file_url` of every bill and
every day-fix file in the tenant.** The **bytes** still ask the parent, so this is a
metadata leak and not a content leak. Mandatory bills turn it from a curiosity into a
complete index.

**What 081 does about it:** generated stored names (AC-16, AC-17), so
`apollo-hospital-receipt.pdf` never reaches `tabFile` and the index is worth nothing.
**What 081 deliberately does not do:** a `permission_query_conditions` hook on `File`. It is
technically cheap and behaviourally expensive — expressing "a parent I may actually read" in
SQL for every doctype risks hiding HR's own attachments on Desk, which is a control people
route around. **Priced, not built** (081-PRIV-2, and R-2 in §13).

---

## 8 · Epic and user stories

**Epic:** *An employee can put a bill on an expense claim and evidence on a day-fix from
their phone, and the person who decides it can open the file without asking anybody.*

Personas are the ones in `product-context.md`: **frontline employee**, **employee**, **line
manager / expense approver**, **HR Manager / HR User**, **System Manager / CXO**.

### 8.1 The stories

| ID | Story | Persona | Pts | Prototype | Requirements | ACs |
|---|---|---|---|---|---|---|
| **US-1** | As a **frontline employee**, I want the bill control to be the first thing in the claim form, with a camera button and a plain line about having no bill, so that I can start with the thing in my hand and learn the HR route before I waste a trip | frontline employee | 3 | `ec · 1, 2` | design §7.1, EC7 | AC-1 … AC-4 |
| **US-2** | As a **frontline employee**, I want my photo made smaller on my own phone before anything is sent, so that an iPhone picture works and a 3G upload is seconds not minutes | frontline employee | 5 | `ec · 3, 7b` | design §5, EC4, OPS-25 | AC-5 … AC-7 |
| **US-3** | As a **frontline employee**, I want the picture shown back with its size before I send the claim, so that I can see for myself whether my own bill came out readable | frontline employee | 3 | `ec · 5, 5b` | design EL1, §5 | AC-8, AC-9 |
| **US-4** | As an **employee**, I want the server to shrink, cap and type-check what I send and to tell me the real size and the real limit when it refuses, so that I know what to do differently | employee | 5 | `ec · 6, 6b, 7` | 081-SEC-4, 081-SEC-5, OPS-3, OPS-6 | AC-10 … AC-12, AC-17 … AC-22 |
| **US-5** | As an **HR Manager**, I want a claim with no file refused **at submit on the document**, so that the rule holds in Desk, through the REST API and through a data import, while a half-finished draft stays saveable | HR Manager | 3 | `desk · refuse`, `ec · 9` | 081-SEC-3, brief D4 | AC-13 … AC-15, AC-23 |
| **US-6** | As an **employee**, I want the file linked to my claim the moment the claim is created, so that my approver can actually see it | employee | 3 | `ec · 13` | **OPS-17**, 081-SEC-5 cl. 5 | **AC-16**, AC-24, AC-25 |
| **US-7** | As a **frontline employee**, I want my chosen bill to survive Try again and the upload to be retryable on its own, so that a dropped signal does not cost me a second trip to the pump | frontline employee | 3 | `ec · 8, 11, 12` | design EC2, §7.3 | AC-26 … AC-28 |
| **US-8** | As an **employee**, I want to open my own bill from my own claim row, and to see an honest "No bill attached" on an older claim, so that an empty button never lies to me | employee | 2 | `eclist · mix` | design §7.5, EL1 | AC-29, AC-30 |
| **US-9** | As an **employee**, I want to attach a photo to a day-fix if I have one, and to be told plainly **before** I choose a file that my manager will see it, so that attaching is my informed choice | employee | 3 | `ar · 1 … 4` | **081-SEC-8**, brief D9 | **AC-31**, AC-32 … AC-34 |
| **US-10** | As an **employee**, I want to see the evidence on my own day-fix card | employee | 1 | `arcard · mix` | design AR3 | AC-35 |
| **US-11** | As a **line manager**, I want the queue row to tell me in words whether a bill is attached, so that I know before I open anything whether this claim is decidable | line manager | 2 | `ap · 1` | design §7.7, AQ5 | AC-36, AC-37 |
| **US-12** | As a **line manager**, I want **View bill** in the sheet body above the decision, and the bill to open **on top of** the sheet, so that I read the evidence before the act I cannot take back | line manager | 5 | `ap · 2, 3, 4, 5, 5b, 6` | design AQ1, AQ4, §7.9 | AC-38 … AC-43 |
| **US-13** | As an **HR User**, I want "Evidence attached · View" on a day-fix card and no thumbnails anywhere in the list, so that the busiest page in the product stays fast | HR User | 2 | `hr · mix, view` | HQ1, **OPS-7** | AC-44, AC-45 |
| **US-14** | As an **employee**, I **must not** be able to read a colleague's bill or day-fix file through any Frappe door, and no browser may ever receive a private-file address | employee *(must-not)* | 5 | — | 081-SEC-6, `data-doors.md` | AC-46 … AC-52 |
| **US-15** | As an **employee**, I want every opening of my file recorded, and I want to be able to ask who opened it | employee | 3 | — | **081-PRIV-3** | AC-53 … AC-58 |
| **US-16** | As an **HR Manager**, I want a bill kept for as long as the law requires and then **permanently erased**, with legal hold winning and nothing ever kept for ever | HR Manager | 5 | — | **081-PRIV-1**, OPS-16 | AC-59 … AC-66 |
| **US-17** | As an **HR Manager**, I want a day-fix file erased six months after the person leaves, and an abandoned upload gone within a day | HR Manager | 3 | — | 081-PRIV-1, **OPS-15** | AC-67 … AC-70 |
| **US-18** | As an **HR Manager**, I want two numbers I can read on demand — submitted claims with no file, and orphans in the last week — so that a rule that quietly stopped firing is visible | HR Manager | 2 | — | **OPS-19**, brief §12 | AC-71, AC-72 |
| **US-19** | As an **employee using a screen reader**, I want every input in the claim form to have a real label, so that the form is usable at all | employee | 1 | `ec · all` | design EC8, §8 | AC-73, AC-74 |
| **US-20** | As an **HR Manager**, I **must not** find a second copy of the bytes, an OCR step, a new export, a new public route or a new permission bypass anywhere in this slice | HR Manager *(must-not)* | 2 | — | **081-PRIV-4**, 081-SEC-7, 081-PRIV-5 | AC-75 … AC-79 |
| **US-21** | As a **frontline employee**, I want every refusal and every progress line in Hindi as well as English | frontline employee | 2 | all, `Language` switch | design §7, nfr §7 | AC-80, AC-81 |

**INVEST check.** Every story is independently demonstrable except US-6, which only makes
sense alongside US-4 (the upload) — it stays separate anyway because OPS-17 is a P1 with its
own failure mode and its own assertion. No story is an 8: US-16 was an 8 and was split into
US-16 (the bill clock, legal hold, erasure refusal) and US-17 (the leaver clock and the
orphan sweep), because they run on different anchors and will be tested with different
fixtures. US-10 and US-19 are 1-pointers and are kept rather than merged, because each has
its own observable oracle and merging them would hide one behind the other.

### 8.2 YouTrack-ready table

**Do not create these issues. That is Surbhi's call.** Project `ALV`, one Epic plus 21
Stories.

| Type | Summary | Description | Persona | Points | ACs | Requirements |
|---|---|---|---|---|---|---|
| Epic | 081 · A bill on an expense claim, evidence on a day-fix | §8 epic line. Attachments only; the approver role is a separate slice (Surbhi, 3 Nov 2026) | all | 60 | AC-1…AC-81 | brief, 01b, 01c, 07 |
| Story | 081 US-1 · The bill control, first in the claim form | US-1 as written | frontline employee | 3 | AC-1…AC-4 | design §7.1 |
| Story | 081 US-2 · Shrink the picture on the phone | US-2 | frontline employee | 5 | AC-5…AC-7 | EC4, OPS-25 |
| Story | 081 US-3 · Show the picture back with its size | US-3 | frontline employee | 3 | AC-8, AC-9 | EL1 |
| Story | 081 US-4 · Server-side shrink, cap and type check | US-4 | employee | 5 | AC-10…AC-12, AC-17…AC-22 | 081-SEC-4/5, OPS-3/6 |
| Story | 081 US-5 · A claim with no bill cannot be submitted | US-5 | HR Manager | 3 | AC-13…AC-15, AC-23 | 081-SEC-3 |
| Story | 081 US-6 · The file is linked to its claim on the way in | US-6 | employee | 3 | AC-16, AC-24, AC-25 | OPS-17 |
| Story | 081 US-7 · The bill survives Try again | US-7 | frontline employee | 3 | AC-26…AC-28 | EC2 |
| Story | 081 US-8 · My own bill on my own claim row | US-8 | employee | 2 | AC-29, AC-30 | EL1 |
| Story | 081 US-9 · Optional evidence on a day-fix, with the notice first | US-9 | employee | 3 | AC-31…AC-34 | 081-SEC-8 |
| Story | 081 US-10 · Evidence on my own day-fix card | US-10 | employee | 1 | AC-35 | AR3 |
| Story | 081 US-11 · "Bill attached" in words on the queue row | US-11 | line manager | 2 | AC-36, AC-37 | AQ5 |
| Story | 081 US-12 · View bill, above the sheet | US-12 | line manager | 5 | AC-38…AC-43 | AQ1, AQ4 |
| Story | 081 US-13 · Evidence on HR's day-fix card, no thumbnails | US-13 | HR User | 2 | AC-44, AC-45 | HQ1, OPS-7 |
| Story | 081 US-14 · Nobody reads a colleague's file, on any door | US-14 | employee (must-not) | 5 | AC-46…AC-52 | 081-SEC-6 |
| Story | 081 US-15 · Every opening recorded; the employee can ask | US-15 | employee | 3 | AC-53…AC-58 | 081-PRIV-3 |
| Story | 081 US-16 · The bill's statutory clock, legal hold, real erasure | US-16 | HR Manager | 5 | AC-59…AC-66 | 081-PRIV-1 |
| Story | 081 US-17 · The leaver clock and the orphan sweep | US-17 | HR Manager | 3 | AC-67…AC-70 | OPS-15 |
| Story | 081 US-18 · Two numbers HR can read on demand | US-18 | HR Manager | 2 | AC-71, AC-72 | OPS-19 |
| Story | 081 US-19 · Real labels on the claim form's inputs | US-19 | employee | 1 | AC-73, AC-74 | EC8 |
| Story | 081 US-20 · Nothing grew that nobody asked for | US-20 | HR Manager (must-not) | 2 | AC-75…AC-79 | 081-PRIV-4/5, 081-SEC-7 |
| Story | 081 US-21 · English and Hindi on every new string | US-21 | frontline employee | 2 | AC-80, AC-81 | nfr §7 |

**Total: 60 points.** For comparison, the routing slice (081-SEC-1 + 081-SEC-2 + the role
field + the role queue + AP6 + EL2) is a separate backlog item and is **not** sized here.

---

## 9 · Acceptance criteria

Every AC is Given / When / Then with an observable oracle. **"Works correctly" appears
nowhere.** The seven ACs that were paid for today are marked **★**.

### US-1 · The bill control

- **AC-1** Given the portal expense claim modal, When it opens, Then the file control is the
  **first** element inside the form — its DOM index precedes the Expense Type field's — and
  its label reads **"Photo of the bill · required"** as text, not an asterisk.
- **AC-2** Given the control, When it renders in any of its eight states, Then the line
  *"No bill? Ask HR to file this claim with your signed statement of what you spent."* is
  present and visible, as plain hint text, with no `href`, no `role="button"` and no
  `onclick`. *(Asserted on all eight states, not just the empty one.)*
- **AC-3** Given the control, Then there are exactly two visible buttons —
  **"Take a photo of the bill"** carrying `capture="environment"` and **"Choose a file"** —
  in front of one `<input type="file">` that is visually hidden, keyboard reachable and has
  an accessible name.
- **AC-4** Given the camera returns no file, When the input's change event fires with an
  empty list, Then the screen shows *"Nothing was chosen. If the camera will not open, use
  Choose a file."*, both buttons remain, and **no request is sent** (asserted on the network
  mock: zero calls).

### US-2 · Shrink on the phone

- **AC-5** Given a 4 MB camera JPEG, When it is chosen, Then the browser draws it to a
  canvas at long edge 1600 px and quality 82, the status line reads *"Making the picture
  smaller…"* with `role="status" aria-live="polite"`, and the bytes posted are **smaller
  than the bytes chosen** (asserted on the request body's length).
- **AC-6** Given a file the browser cannot decode, When it is chosen, Then the screen shows
  *"This phone could not read that picture. Use "Take a photo of the bill" instead — nothing
  has been sent."*, and **zero requests are sent**.
- **AC-7 ★** Given the one committed real phone photo (OPS-10), When it passes through the
  **device re-encode and then the server re-encode** — both passes, in that order — Then
  the printed amount is legible in the final stored artefact, judged by a human against five
  real DTC bills, and the result is recorded in `04-test-report.md` with the byte size of
  each pass. *(OPS-24. A single-pass test does not satisfy this AC.)*

### US-3 · Shown back

- **AC-8** Given an accepted image, Then the page shows the picture, the words **"Bill
  attached"**, and a line reading `{size} · {long edge} px · {our stored file name}` — e.g.
  `380 KB · 1600 px · EXP-CLM-2026-00123-a1b2c3.jpg` — plus **View full size** and
  **Replace**. There is **no Remove button** on the expense control.
- **AC-9** Given an accepted PDF, Then a tile is shown instead of a preview, with
  `{size} · {our stored file name}`, and the same two buttons. **No server-side page count
  is requested** (asserted: no endpoint returns a page count).

### US-4 · The server's shrink, cap and type check

- **AC-10** Given an image whose re-encode at 1600/q82 still exceeds 1 MB, When it is
  uploaded, Then the server retries at quality **72**, then **62**, then width **1280**, then
  **1024**, in that order, and only then refuses — asserted by counting the re-encode calls
  and their arguments.
- **AC-11** Given the ladder has run out, Then the response message is
  *"This photo is still {actual} after we shrank it. The limit is 1 MB — take it again with
  just the bill in the frame."*, with `{actual}` the real post-ladder size, and it reaches
  the screen's `role="alert"` region verbatim.
- **AC-12** Given a PDF over 3 MB, Then the message is *"This PDF is {actual} and the limit
  is 3 MB. Send one page with the bill on it, or photograph the bill instead."* — a
  **different sentence** from AC-11.
- **AC-17** Given a 200 MB base64 string, When it is posted, Then it is refused **before any
  decode** — asserted by patching the decoder and proving it was never called — and the
  response is the size refusal.
- **AC-18** Given an HTML file named `bill.jpg`, Then it is refused on magic bytes with
  *"We can take a JPG, a PNG or a PDF. Most phones can take a JPG — try again from the
  camera."* Same for a zip named `bill.pdf`.
- **AC-19** Given a HEIC file, Then it is **refused with that same sentence** and **not
  converted**. No `pillow_heif` import appears anywhere in the diff.
- **AC-20** Given a PNG carrying GPS EXIF, When it is accepted, Then the stored bytes
  contain no EXIF block (asserted by reading the stored file's metadata).
- **AC-21** Given a valid `%PDF-` file within the cap, Then the stored bytes are
  **byte-identical** to what was posted, and no PDF parser, page counter or text extractor
  is called.
- **AC-22 ★** Given a site where `System Settings.max_file_size` is **0**, 5 and 25 in three
  separate runs, When a 4 MB photo is uploaded, Then the outcome is identical in all three —
  the caps come from our own module constants. **And:** the diff contains no write to
  `max_file_size`, and `System Settings` is not in `patches.txt` or any fixture of this
  slice. *(081-SEC-5 clause 2, OPS-6.)*

### US-5 · Mandatory at submit

- **AC-13 ★** Given a draft `Expense Claim` with no attachment, When it is submitted through
  **`frappe.get_doc(...).submit()`**, through **`PUT /api/resource/Expense Claim/<name>`
  with `docstatus: 1`**, and through a **data import** that submits, Then each one raises and
  the message's first sentence is *"A claim needs a photo or a PDF of the bill."*
  *(Three doors, three assertions. A portal-only check does not satisfy this AC.)*
- **AC-14 ★** Given a draft `Expense Claim` with no attachment, When it is **saved**, Then
  the save succeeds and `docstatus` is 0. *(A validate-time rule would fail this AC.)*
- **AC-15** Given a Desk submit refusal, Then the dialog shows exactly three lines, in
  order: *"This claim cannot be submitted yet"*, *"A claim needs a photo or a PDF of the
  bill."*, *"Where there is no bill, attach the employee's signed statement of what was
  spent and why there is no bill."*, plus *"The draft is still saved. Only Submit is
  blocked."* The second line is **character-for-character** the first sentence of AC-23's
  portal message.
- **AC-23** Given `apply_expense_claim` is posted with no `file_url`, Then the response is
  the server's own sentence *"A claim needs a photo or a PDF of the bill. Please attach one
  and send it again."*, it reaches the `ec-error` element verbatim, and it is **never**
  "check your connection", "upload failed", or a Python `TypeError`. *(A test that only
  inspects the form does not satisfy this AC — press the real path.)*
- **AC-13b** Given a claim **already submitted** before this slice shipped with no
  attachment, When an approver decides it, Then nothing refuses and the decision succeeds.
  *(Brief §3.1, D1.)*

### US-6 · The link on the way in

- **AC-16 ★** Given an accepted upload and a claim filed in the same session, When the claim
  is created, Then **a query of `tabFile` for that row** returns
  `attached_to_doctype = "Expense Claim"` and `attached_to_name = <the new claim's name>`.
  **The assertion is on the stored row, read back from the database — not on the endpoint's
  response.** *(OPS-17. Without it the approver sees nothing and every retention pass
  silently skips the file.)*
- **AC-24** Given a `file_url` belonging to another user, or already bound to a parent, or
  not private, When it is passed to `apply_expense_claim`, Then the call is refused, the
  claim is **not** created, and one log line records the row id, the rule id and the caller
  — **and no file name and no url**.
- **AC-25** Given two uploads and one filed claim, Then `tabFile` holds exactly **one** row
  with that claim as its parent, and the other row has no parent. *(081-SEC-5 clause 3.)*

### US-7 · Surviving a retry

- **AC-26** Given a chosen and uploaded bill and an offline Submit, Then the message reads
  *"We could not reach the office. Nothing was sent."* / *"Your details **and your bill** are
  still here. When you have signal, tap Try again."*, **Try again** is present, and pressing
  it re-posts the claim with the **same** `file_url` and uploads nothing again.
- **AC-27** Given the upload call itself failed, Then the chosen file is still held in the
  page, the heading reads *"We could not send the picture. Nothing was lost."*, and a
  **Send the picture again** button re-posts the same file.
- **AC-28** Given Submit received no answer, Then the message reads *"No answer from the
  office. It may have gone through."* / *"Look in your list before you send it again."*, and
  **no Try again button exists** — only Close. *(Negative criterion: there is no duplicate
  guard on `apply_expense_claim`.)*

### US-8 · The employee's own row

- **AC-29** Given a claim with a bill, Then the employee's own row shows **"Bill attached"**
  and a **View full size** button that opens the same viewer the approver gets.
- **AC-30** Given a claim filed before this slice shipped, Then the row shows
  **"No bill attached"** as plain grey text with **no button**.

### US-9 · The day-fix

- **AC-31 ★** Given the day-fix form, When it renders, Then **inside the same container**,
  the notice node's index is **strictly less than** the file input's index, and the notice's
  text is non-empty in **both** English and Hindi. *(A presence-only assertion does not
  satisfy this AC — it is positional.)*
  **And the negative half:** the strings "notice", "warning", "protection" or any equivalent
  claim about this notice appear in **no** protection column, verification table, release
  note or questionnaire answer in this slice. **Nothing restricts the manager on a day-fix
  request, by design** (081-SEC-8).
- **AC-32** Given the notice, Then its text is exactly *"Your manager reads this request, and
  will see any file you attach. Attaching one is your choice — HR can fix the day without
  it."*, rendered as plain hint text — asserted to carry no warning/alert colour class and no
  callout container.
- **AC-33** Given the day-fix form with **no** file, When it is sent, Then the request is
  created, `docstatus` is 0, `alvoraa_review_status` is `Waiting`, and **no message about a
  file is shown**. *(Negative criterion: no "are you sure?" confirm exists.)*
- **AC-34** Given a file is attached and sent, Then a `tabFile` query returns
  `attached_to_doctype = "Attendance Request"` and `attached_to_name = <the new request>`.
- **AC-34b** Given a 360 px viewport at 200% text, When a file is attached, Then the action
  row is scrolled into view (asserted on the scroll call or the element's position). *(AR2.)*

### US-10 / US-11 / US-13 · The rows

- **AC-35** Given the employee's own day-fix card with evidence, Then one line reads
  **"Evidence attached"** with a **View** control; with no evidence, the card is unchanged
  from today.
- **AC-36** Given the approver's queue row, Then its third line reads **"Bill attached"** or
  **"No bill attached"** as **words** — the second in the grey class, not the error class —
  and the row's payload from `_part_expense_approvals` carries a boolean, never a url.
- **AC-37** Given the approver's queue row, Then the row element contains **exactly one**
  interactive node (itself). *(Negative criterion: a button inside a button is a WCAG 2.2 AA
  failure.)*
- **AC-44** Given HR's day-fix queue, Then a card with evidence shows **"Evidence attached ·
  View"** and nothing else, and View opens the same viewer.
- **AC-45** Given any list in this slice — the approver's queue, HR's queue, the employee's
  own lists — Then **no `<img>` whose source is an evidence file is rendered**, no evidence
  endpoint is called during the list's render, and the number of evidence calls on a page
  view is **0**. *(Negative criterion: no thumbnails, no preloading, no "open all" —
  OPS-7.)*

### US-12 · View bill

- **AC-38** Given the decision sheet, Then **View bill** is inside the sheet **body** and its
  DOM index is **less than** the decision footer's. *(Positional, not presence.)*
- **AC-39** Given View bill is tapped, Then the button shows *"Opening the bill…"* with
  `role="status"` while the fetch is in flight.
- **AC-40** Given the fetch failed, Then the sheet shows *"The bill did not open. Check your
  signal and tap View bill again."* and View bill is usable again.
- **AC-41** Given the viewer opens, Then its computed `z-index` is **greater than** the
  decision sheet's computed `z-index`. *(Asserted on the computed order, not on the
  element's existence. The prototype's `Approver · 5b` is what ships if this AC is not met —
  it is a bug drawn on purpose, not a screen to build.)*
- **AC-42** Given the viewer, Then it carries `role="dialog"`, `aria-modal="true"` and an
  `aria-label`; **Escape** closes it; focus moves into it on open and **returns to the View
  bill button** on close; the footer reads *"Shown here so you do not have to save a copy."*
- **AC-43** Given a claim with no file, Then the sheet says plainly there is nothing to open
  and **View bill does not render**.

### US-14 · The doors (must-not)

Every one of these runs **as a plain staff login, as a line manager with a direct report,
and as an HR User**, through the API, **on a freshly created site** — a copied site hides
failures (ALV-249).

- **AC-46** Given a colleague with no reporting line to the claimant, When they call
  `GET /api/resource/Expense Claim` (list and by name),
  `frappe.desk.reportview.get` / `get_list` / `get_count`,
  `frappe.client.get` / `get_list` / `get_value`, the report view **and its CSV export**,
  link search (`search_link`, `validate_link_and_fetch`), and `frappe.share.add`, Then every
  one returns **zero rows or a refusal** for that claim. Each test must **fail** if the
  own-record User Permission is removed.
- **AC-47** The same seven doors on `Attendance Request`.
- **AC-48** The same doors on `File`, for the **bytes**: a staff login calling
  `frappe.client.attach_file` or fetching `/private/files/<another person's bill>` is
  refused. *(The **metadata** listing is **not** asserted as blocked — see AC-49.)*
- **AC-49** Given a plain staff login, When they list `/api/resource/File` filtered on
  `attached_to_doctype = "Expense Claim"`, Then rows **are** returned — and **every returned
  `file_name` matches our generated pattern** and contains none of the words from the
  uploaded device name. *(This AC records the residual exposure R-2 honestly rather than
  asserting a protection that does not exist.)*
- **AC-50** Given `Expense Claim Detail` asked **on its own** via
  `/api/resource/Expense Claim Detail` and `frappe.client.get_list`, Then no row of another
  person's claim is returned. And the test pins the ordering inside
  `_part_expense_approvals`: the parent list is filtered **before** the
  `frappe.get_all("Expense Claim Detail", ...)` call at `inbox_api.py:589` — asserted by
  call order, because that `get_all` checks no permissions.
- **AC-51** Given `open_evidence` is called with another person's claim or request id, Then
  it is refused, the refusal names **no** employee and **no** file, and one log line records
  the rule id, the endpoint, the doctype and the parent id.
- **AC-52 ★-adjacent** Given any of the four callers — the employee's claim row, the
  employee's day-fix card, the approver's sheet, HR's card — Then **no response body
  contains the string `/private/files/`**, and the viewer is given a blob which is revoked
  on close.

### US-15 · The log

- **AC-53** Given an approver opens a bill, Then exactly one `Alvoraa Photo Access Log` row
  exists with `source = "Expense bill"`, `reference_name = <the claim>`,
  `employee = <the claimant>`, `viewed_by = <the approver>` and today's `viewed_on_date`.
- **AC-54** Given the same approver opens it again the same day, Then there is still exactly
  **one** row; the next day, **two**.
- **AC-55** Given the **claimant** opens their own bill, Then **no row is written**.
- **AC-56** Given HR opens a day-fix file, Then the row's `source` is
  **`"Day-fix evidence"`** and `reference_name` is the request's name.
- **AC-57** Given the log insert raises, Then the file is still streamed, and the logged
  error contains **no file name and no url**.
- **AC-58** Given an employee calls `who_opened_mine()`, Then they receive the reader and the
  day for **their own** files only; passing any argument naming another person is refused.

### US-16 · The bill's clock

- **AC-59** Given a claim whose `posting_date` falls in a financial year that ended more
  than 8 financial years ago, When the daily pass runs, Then the `File` row **and its
  bytes** are gone, the **claim and its ledger entries remain**, and the pass logs its own
  count.
- **AC-60** Given the same claim with `alvoraa_legal_hold = 1`, Then the file **survives**.
- **AC-61** Given a **cancelled** claim inside the window, Then the file **survives** to the
  statutory clock. *(081-PRIV-1 clause 1 — a cancelled voucher is still a voucher.)*
- **AC-62** Given a **leaver's** claim inside the window, Then the bill **survives**.
  *(Clause 2 — the file follows the claim, not the person.)*
- **AC-63** Given the clock is anchored, Then it is computed from **`posting_date`** and
  **never** from `File.creation` or `modified` — asserted by changing `modified` and
  observing no change in the due date. *(OPS-16.)*
- **AC-64** Given an erasure request against a bill inside the statutory window, Then it is
  **refused** and the refusal message **names the statute** — Companies Act 2013 s.128(5) —
  rather than saying only "we cannot delete that".
- **AC-65** Given the retention number, Then no value means "for ever": 0, blank and any
  value below 8 financial years are **refused**, the way `settings.py:502-520` already
  refuses the joiner clocks.
- **AC-66** Given a deletion is due, Then HR is told through `Notification Log` naming the
  **claim reference and never the person**. *(Clause 4.)*

### US-17 · The leaver clock and the orphans

- **AC-67** Given an employee whose `relieving_date` is more than 6 months past, Then their
  day-fix evidence files are gone, bytes included, the requests remain, and the pass logs
  **its own** count — separate from AC-59's. *(Clause 3: two clocks, two counts.)*
- **AC-68** Given a live grievance flagged by `alvoraa_legal_hold = 1`, Then the file
  survives.
- **AC-69** Given a private `File` row with **no `attached_to_name`**, created by the
  evidence upload path, older than **24 hours**, Then the daily pass deletes it, bytes
  included, bounded to a few hundred rows per run, with one count line. *(OPS-15.)*
- **AC-70** Given a file **younger than two hours**, or one that **has a parent**, Then the
  orphan pass does **not** touch it — asserted as a negative, with an attached file present
  in the fixture.
- **AC-70b** Given the daily pass runs twice in a day, Then the second run deletes nothing
  extra and raises nothing. *(It runs safely twice.)*

### US-18 · The two numbers

- **AC-71** Given an HR Manager calls `counts()`, Then they receive **submitted expense
  claims with no attached file** and **orphan uploads in the last 7 days**. On a healthy
  fixture the first number is **0**.
- **AC-72** Given a non-HR login calls `counts()`, Then it is refused. *(No dashboard, no
  alert, no new tool — OPS-19.)*

### US-19 · Labels

- **AC-73** Given the expense claim modal, Then Expense Type, Expense Date, Amount and
  Purpose each have a real `<label for>` and therefore an accessible name. *(EC8 — today
  every one of them is a `<div class="gp-label">` and has none.)*
- **AC-74** Given any control in the new file block, Then it has an accessible name, a
  minimum touch height of 44 px, and a visible `:focus-visible` ring.

### US-20 · Nothing grew (must-not)

- **AC-75 ★** Given the diff, Then **no new `ignore_permissions` exists**:
  `hr_api.py` stays at **67**, `attendance_correction.py` stays at **0**, and **every new
  module has its own entry at 0** in
  `test_portal_security_010.TestSec16IgnorePermissionsCeiling.CEILINGS`. **Exactly one
  exception is permitted and must be argued in the ceiling comment:** the access-log insert,
  as `employee_documents_read.py` already carries one for the same reason — nobody holds
  `create` on that doctype. *(A new file with no ceiling entry is the hole slice 064 found,
  so the entry is part of the AC.)*
- **AC-76** Given the diff, Then there is **no second copy of the bytes** — no thumbnail, no
  derived preview, no cache, no object store, no CDN — asserted by grepping for a second
  `File` insert per upload and for any new storage path.
- **AC-77** Given the diff, Then there is **no OCR, no amount extraction, no text layer and
  no PDF parsing**, and **nothing new on `Expense Claim Detail`**.
- **AC-78** Given the diff, Then **exactly four** new `@frappe.whitelist()` endpoints exist,
  they are the four in §5.5, each appears in
  `docs/security/whitelisted-endpoint-review.md`, and **no new public page, guest route or
  export** exists.
- **AC-79** Given this slice's copy, this spec and the release note, Then the words
  **"protected", "secure", "hidden", "masked"** and **"redacted"** appear nowhere about a
  bill or a day-fix file — the existing `test_employee_documents_078` word assertion,
  extended. *(081-PRIV-5.)*
- **AC-79b** Given every refusal and server-side failure on this path, Then one Error Log or
  one counted log line is written, with a separately countable reason — no file at submit ·
  over the cap · unreadable or HEIC · magic-byte mismatch · rate-limited — and **no file
  name** in any of them. *(OPS-18.)*
- **AC-79c** Given the 61st upload by one user in an hour, Then it is refused by
  `_limited(SELF_KEY, "user", limit=60)`, and the limit is readable off the function so a
  table test can pin it. *(OPS-12.)*

### US-21 · Language

- **AC-80** Given the Hindi locale, Then every string in design §7 that has a Hindi draft
  renders in Hindi, and every one without a draft falls back to English rather than showing
  a key or an empty string.
- **AC-81** Given the Hindi locale at 360 px, Then the two-button row **wraps** and nothing
  overflows the viewport. *(Devanagari runs ~30% longer.)*

---

## 10 · Edge cases and boundaries

Only cases that actually happen. Each one has an AC or an explicit "no behaviour needed".

| Case | Specified behaviour |
|---|---|
| **A claim already submitted with no bill** | Decides normally, for ever. The rule fires at submit and these are past it. AC-13b. *(Brief D1, Surbhi's recommendation accepted.)* |
| **A Desk draft that exists today with no file** | Stays saveable; cannot be submitted until a file is attached. AC-14, AC-13 |
| **An amended claim** (`amended_from` set) | Frappe copies the document, **not** the `File` rows. So an amendment needs its **own** attachment before submit, and the same refusal fires. **AC-13 covers it with an amended-claim fixture.** This is a real case: a cancelled-then-amended claim is exactly the disputed one |
| **A cancelled claim** | The bill is **kept** to the statutory clock. AC-61 |
| **A mixed Desk claim** — a medical line beside a fuel line | **Known limit, no code.** One claim, one approver, wherever it is addressed. The portal cannot produce one: `apply_expense_claim` builds a single `expenses` row (**Confirmed fact**) |
| **The employee has no bill at all** (an autorickshaw fare) | **No code.** The rule is "a file", not "a receipt": HR attaches the employee's signed self-declaration. The product sees a file. The standing line on the form is how the driver learns the route exists. AC-2, AC-15 |
| **An iPhone filer** | The canvas re-encode yields a JPEG. If the browser cannot decode, AC-6 fires before anything is sent. A HEIC that reaches the server is refused in words, AC-19. **One real iPhone upload is a release check, not a code change** (OPS-25) |
| **A re-hired employee** | Their old claims keep their own clocks, anchored to each claim's `posting_date`. Their day-fix clock restarts from the **new** relieving date, because the anchor is read at run time. No special case |
| **An employee with no manager** | `expense_approver_for` returns `None` and filing is already refused with *"nobody is set to approve it. Ask HR to set your approver."* (**Confirmed fact**). **Unchanged by this slice** |
| **A leaver whose login was left enabled** | `expense_approver_for` already refuses to route to a disabled login or a non-Active employee. Unchanged |
| **Two people deciding one claim at once** | **Cannot happen in 081** — one claim, one named approver. This is the routing slice's problem (`01c` Worry 1), and it is why AP6 travels with the role |
| **A claim whose expense type has no account for the company** | Already refused at filing with a message naming what HR must set (ALV-178, **Confirmed fact**). Unchanged. The release note carries the two-step setup |
| **Multi-company** | `alvoraa_branch` is copied onto both doctypes at save already, and company scoping on the claim is Frappe's existing User Permissions. **081 adds no company logic**, because it adds no role |
| **A bulk data import of claims** | Obeys the submit rule — AC-13's third door. An import that submits claims with no attachment fails row by row with the same sentence |
| **Back-dated claims** | A `posting_date` in a past financial year starts an **earlier** clock. AC-63's anchor handles it; no special case |
| **Time zones / DST** | The only date arithmetic is financial-year ends and a months-since-relieving comparison, both on dates, not timestamps. The orphan sweep uses a 24-hour window on `creation` and a 2-hour floor, both in server time. **No DST behaviour is specified because none is needed** |
| **Half-days, probation, negative balances, holiday lists, carry-forward** | **Not engaged.** Nothing in this slice reads a leave balance, an attendance total or a holiday list |
| **A file deleted in Desk while an approver is looking at it** | `open_evidence` returns the generic open failure and the sheet shows *"The bill did not open…"*. **No separate state** — the design cut one deliberately, and a deleted file is not a case this slice creates |
| **The scheduler is not ticking** | The retention and orphan passes do not run. This is a **known operational dependency**, checked after deploy (OPS, §2.3 check 7), not something the slice can fix |

---

## 11 · Non-functional requirements for this slice

Taken from `nfr-budget.md` and the `OPS` items, made specific.

| Dimension | Number for 081 | Source |
|---|---|---|
| Expected volume | **442 staff at DTC**; 150-450 claims a month `[ESTIMATE]`; **one** file per document | 07 §2.1 |
| Stored size per file | image **≤ 1 MB** (typically 250-600 KB `[ESTIMATE]`); PDF **≤ 3 MB** | brief D5, D5b |
| Storage growth | **0.7-2.2 GB/year typical, 6.5 GB worst**, against a deploy gate wanting 25 GB free. **Not material; the slice must not shrink for it** | OPS-2 |
| Server CPU per upload | **~46 ms** for a device-shrunk 1600 px JPEG; **0.5-1.5 s** for a raw 12 MP fallback. **Inline, no background job, no queue** | OPS-4, 07 §2.1 (Measured) |
| Request budget | the upload endpoint **p95 ≤ 500 ms** on the normal device-shrunk path; the claim form on a 3G phone **p95 ≤ 2.5 s**, skeleton in 300 ms | nfr §2 |
| Reviewer's queue page | **zero** evidence calls on render; **one file per tap**. One file occupies 1 of **8 request slots** (4 gunicorn workers × 2 threads) for a few hundred ms | OPS-7, OPS-26 |
| Query count | the queue row's attachment flag must be **one** extra query for the whole page, not one per row — the same shape as the existing single read of `Expense Claim Detail`. **The count must be the same for 20 rows as for 200** | nfr §2 |
| A scope inside a query | any filter stays **in the database** — no list of ids read into Python and shipped back as `IN (...)` | nfr §2 |
| Background work | **one new entry in the existing `daily` list.** No new job, queue, container, bucket or CDN | OPS-15, §2.3 |
| Rate limit | **60 uploads per user per hour**; **60 opens per user per hour** | OPS-12, 081-SEC-5 |
| Retention | bill: **8 financial years** from `posting_date`; day-fix file: **6 months** after relieving; orphan: **24 hours** | 081-PRIV-1, OPS-15 |
| Personal / sensitive data | **Yes — high, and unbounded in content.** A free-form evidence file inherits the worst thing an employee photographs. Private `File`, guarded stream, generated name, logged reads, two clocks | `01c` §2 |
| nginx | **untouched.** Both server blocks already allow 50 MB and `upload_file` is in no capped location | OPS-5, OPS-21 |
| `System Settings.max_file_size` | **not read, not written, not the enforcement point.** Confirmed as not 1 or 5 on dev and production at release | OPS-6, OPS-22 |
| CI | this slice's own image tests cost **seconds**. The Python job's `timeout-minutes` 90 → 120 is **its own change, with its own ticket, before this build** | OPS-23 |

### 11.1 Reconciling the one place two inputs disagree

**OPS-15 says delete orphans older than 24 hours. 081-PRIV-1 clause 5 says delete an orphan
within 7 days.** These are not in conflict once stated as an outer bound: **the rule is 24
hours**, which is inside 7 days. **Recorded here rather than chosen silently.** AC-69 asserts
24 hours; AC-71 reports orphans over a 7-day window, which is the measurement, not the rule.

---

## 12 · Data migration and backfill

| What | Answer |
|---|---|
| Existing expense claims | **Nothing.** No backfill, no default, no recompute. A claim filed before this ships shows an honest "No bill attached" (AC-30) and decides normally (AC-13b) |
| Existing attendance requests | **Nothing** |
| Existing `Alvoraa Photo Access Log` rows | **Nothing.** They keep their `source` value, which is correct — every pre-078 row really was a check-in photo. `reference_name` is empty on them, and both the subject's view and the job filter on `source` |
| New Custom Fields | Two `alvoraa_legal_hold` Check fields, created in `after_migrate` **and** on install (a site built with `bench install-app` never runs a migrate — the reason is already written into `attendance_correction.after_migrate`). **Additive, default 0**, so a rollback can leave them in place harmlessly |
| New `source` options + `reference_name` | A DocType change, shipped in the app, applied by `bench migrate`. Additive |
| New settings keys | Ship with defaults; **no row is written** until HR sets one. `settings.get()` returns the default when nobody has chosen (**Confirmed fact**) |
| Assets | **This is the step that makes the slice visible.** `portal.js` and the portal CSS change; the deploy's `refresh_bench_files.sh` copies the image's built assets onto the sites volume before the swap, and a later step asserts `/assets/alvoraa_portal/js/ess/portal.js` is served. Without it the volume keeps the old JavaScript and the form ships with no file control while the deploy reports success |
| **Rollback** | Redeploy the previous tag with migrations off. The two Custom Fields, the two `source` options and the `reference_name` field stay — all additive and harmless. **Files already uploaded stay where they are**, bound to their claims, readable in the Desk sidebar. The one thing lost on rollback is the portal's own stream endpoint, so the file is reachable only from Desk until the tag is restored. **No data is destroyed by a rollback** |

---

## 13 · Notifications and messages

**No new email is sent by this slice.** No file is ever attached to a notification, and no
copy of a file leaves the server (081-PRIV-4).

| Trigger | Channel | Recipient | Exact copy | Must never leak |
|---|---|---|---|---|
| Claim filed | the existing toast | the filer | **"Expense claim submitted."** | — |
| Claim filed | Frappe HR's existing share | the named approver | unchanged by this slice | — |
| Submit with no file (portal) | inline in `ec-error` | the filer | **"A claim needs a photo or a PDF of the bill. Please attach one and send it again."** · हिंदी: क्लेम के साथ बिल की फ़ोटो या PDF ज़रूरी है। कृपया एक लगाकर दोबारा भेजिए। | nothing to leak |
| Submit with no file (Desk) | `frappe.throw` dialog | whoever submitted | **"This claim cannot be submitted yet"** / "A claim needs a photo or a PDF of the bill." / "Where there is no bill, attach the employee's signed statement of what was spent and why there is no bill." / *"The draft is still saved. Only Submit is blocked."* | — |
| Image over the cap | inline, `role="alert"` | the filer | **"This photo is still {size} after we shrank it. The limit is 1 MB — take it again with just the bill in the frame."** | — |
| PDF over the cap | inline | the filer | **"This PDF is {size} and the limit is 3 MB. Send one page with the bill on it, or photograph the bill instead."** | — |
| Wrong type / HEIC | inline | the filer | **"We can take a JPG, a PNG or a PDF. Most phones can take a JPG — try again from the camera."** | — |
| The device could not decode | inline | the filer | **"This phone could not read that picture. Use "Take a photo of the bill" instead — nothing has been sent."** | — |
| Upload failed | inline | the filer | **"We could not send the picture. Nothing was lost."** / *"Your bill is still here. When you have signal, tap Send the picture again."* | — |
| Offline at submit | inline | the filer | **"We could not reach the office. Nothing was sent."** / *"Your details and your bill are still here. When you have signal, tap Try again."* | — |
| No answer at submit | inline | the filer | **"No answer from the office. It may have gone through."** / *"Look in your list before you send it again."* | — |
| The bill did not open | inline in the sheet | the reviewer | **"The bill did not open. Check your signal and tap View bill again."** | — |
| A deletion is due | `Notification Log` | HR | the **claim reference** and the count | **never the person's name**, never a file name, never a url (081-PRIV-1 cl. 4) |
| An erasure request against a bill in the window | the refusal message | the requester | names **Companies Act 2013 s.128(5)** as the reason | — |
| Any refusal on this path | one Error Log / counted log line | nobody — it is a record | the reason, the rule id, the parent id | **no file name, no url, no document content** (081-PRIV-2) |

**The day-fix notice is on the form, not a notification:** *"Your manager reads this request,
and will see any file you attach. Attaching one is your choice — HR can fix the day without
it."* It is a **transparency control**, never a protection (081-SEC-8).

---

## 14 · Localisation and accessibility

| Item | Requirement |
|---|---|
| Translatable strings | **Every** new user-facing string goes through `_()` on the server and the portal's `t()` on the client. Hindi drafts exist for the labels, hints, the two cap refusals, the type refusal, the no-file refusal and the day-fix notice (design §7) |
| **Still to translate** | the day-fix label, the five reviewer strings, "Opening the bill…" and its failure line, "Bill attached"/"No bill attached", "View full size", "Replace", "Remove", the viewer footer. **Hindi is a machine draft everywhere and needs a native reviewer before release** — a standing open item, not this slice's invention |
| Fallback | A string with no Hindi draft falls back to **English**, never to a key and never to empty. AC-80 |
| Numbers and sizes | File sizes shown in the user's locale format; the long edge in px. No currency or date format changes in this slice |
| **Frontline on a phone** | The primary user is a driver on a cheap Android on 3G. The camera button opens the **back** camera directly. **One** file. The picture is shrunk on the device, so the upload is a few hundred KB, not 4 MB. The whole form must reach a skeleton in 300 ms and be usable at p95 ≤ 2.5 s |
| Tap targets | **≥ 44 px** on every button, the modal close and the viewer close |
| Font size | **16 px** on everything a finger touches in the new block, so iOS does not zoom on focus. The portal's `--fs-base` of 13 px is existing debt and **not this slice's to change** |
| Nothing under 12 px | `--fs-sm` is the floor |
| Status in words | "Bill attached" / "No bill attached" are **words**; ✓ and ⚠ sit beside text, never instead of it; "No bill attached" is **grey, not red** |
| Live regions | every progress and result line is `role="status" aria-live="polite"`; every refusal that stops the person is `role="alert"` |
| Labels | AC-73 fixes the four existing unlabelled inputs; the hidden file input is labelled by its visible buttons |
| Keyboard | visible `:focus-visible` ring; the viewer traps focus, closes on **Escape**, and returns focus to the button that opened it |
| No nested interactive content | the approver's queue row stays **one** button. AC-37 |
| 200% text at 360 px | the day-fix action row is scrolled into view once a file is attached. AC-34b |
| **Not verified by anyone yet** | colour contrast ratios and all rendered geometry — the designer had no browser. **A human with a browser must check these before release** |

---

## 15 · Audit and traceability

What must be reconstructable a year later, during an audit.

| Question an auditor asks | Where the answer is |
|---|---|
| *What evidence justified this payment?* | The `File` row attached to the claim, in the Desk sidebar and through the portal. Kept **8 financial years** from the claim's financial year |
| *Who uploaded it, and when?* | `File.owner` and `File.creation` — standard Frappe |
| *Who opened it?* | `Alvoraa Photo Access Log`: `viewed_by`, `viewed_at`, `viewed_on_date`, `source`, `reference_name`. **One row per viewer per file per day** — not one per refresh, and never a row for the owner looking at their own |
| *Who decided the claim, and when?* | Existing `Expense Claim` fields and Frappe's own `Version` rows. Unchanged |
| *Was the mandatory rule actually in force?* | `counts()` returns **submitted claims with no attached file**, which must be 0 (OPS-19). A number, on demand, read from the data — not a claim in a document |
| *Did the deletions actually happen?* | Each retention pass logs **its own count**. Two clocks, two counts, plus the orphan count. *"Did the files go"* has an answer that is not "look in the folder and guess" |
| *Who changed the retention number?* | A `Version` row, through the existing `settings.py` access-granting path, with the rule id `081-PRIV-1` |
| *Who changed who can approve?* | **Out of scope in 081** — no approver-role field exists. In the routing slice, `Expense Claim Type` change tracking is `01c` Worry 2 and `OQ-4` there |
| *What did we refuse, and why?* | One Error Log / counted line per refusal reason, carrying the reason and the parent id and **no file name** (OPS-18) |

**What is deliberately not recorded:** no record of a **list** read, because Frappe keeps
none — `data-doors.md` says so, and 081 does not pretend otherwise. **So prevention has to
carry the list case, and in 081 prevention for a routed claim does not exist** (§0.5).

---

## 16 · Compliance-impact sub-analysis

**I am not a lawyer. Nothing below is a legal ruling.** It applies the rulings already
recorded and flags what only a human can decide. Built on `01c` §4; not re-derived.

### 16.1 Data touched

| Field / object | Sensitivity class | Purpose it was collected for | Lawful basis (as recorded) | New collection? |
|---|---|---|---|---|
| The bill (image or PDF on `Expense Claim`) | **sensitive, and unbounded in content** — classify at the ceiling, not the average | Justify a payment; the employer's statutory voucher duty | Legal obligation / employment contract, as recorded by the employer (the Data Fiduciary) | **Yes — and now compulsory.** The outcome is impossible without it: a claim without evidence is the thing the brief exists to fix, and the law requires the voucher |
| The day-fix file (`Attendance Request`) | **sensitive** — a doctor's note is the natural evidence for a missed punch | Settle one day's attendance | Employment contract; **the employee's own choice to attach** | **Yes, optional** |
| File metadata (stored name, size, type, uploader, time, parent) | internal — but a device name can disclose on its own (`apollo-hospital-receipt.pdf`) | Show the file back; audit | with its parent | **Yes** — and the stored name is **generated by us** precisely to remove that disclosure |
| Access-log row (reader, file reference, day) | internal — a record about a **reader** | Answer *"who opened mine"*; the brief's ≥70% measure | legitimate interest / the employee's own right of access | **Yes**, two new `source` values |
| `alvoraa_legal_hold` | internal | Stop a deletion somebody has asked us to preserve | legal obligation | Yes, a flag |

**Minimisation:** one file per document; no second copy; no thumbnail; no OCR; no text
layer; no page count; no bulk export; no new public route. The device name is discarded.

### 16.2 Obligations engaged

| Obligation | Source | What this slice must do | Feature that does it |
|---|---|---|---|
| Keep books with the **vouchers** for **not less than eight financial years** | Companies Act 2013 s.128(5) (read via bare-act reproductions, **not** the Gazette — `01c` §15) | Keep a bill to the end of the 8th financial year after the claim's; longer under legal hold | US-16, AC-59, AC-60, AC-63 |
| Retain records **72 months** from the annual return's due date, extended by an appeal or investigation | CGST Act 2017 s.36 | Inside the 8-year floor; the proviso is our legal hold | AC-60 |
| Erase when the purpose is served, **unless retention is required by law** | DPDP Act 2023 s.8(7) | Refuse an erasure request against a bill inside the window, **naming the law** | AC-64 |
| Performance-type records: employment + a **strict 6-month buffer**, then permanent erasure; **no indefinite soft deletion** | Counsel, 18 Sep 2026 | The day-fix clock; no "deleted" flag anywhere; no value means "for ever" | US-17, AC-65, AC-67 |
| **Passport and health data are not for managers** | Counsel, 1 Nov 2026 (ALV-249) | **NOT DISCHARGED BY THIS SLICE.** The risk is **accepted** by Surbhi on 3 Nov 2026 with her reason recorded — **accepted is not discharged**. §0.5 | the routing slice, **ALV-301** (081-SEC-1/2) |
| Mask sensitive IDs; restrict unmasked exports | Counsel, 31 Oct 2026 | **Does not transfer** — we cannot mask the inside of a photograph. The equivalent is minimising readers and logging reads, and **nothing may claim a bill is masked** | AC-79, US-15 |
| Log every export | Counsel, 31 Oct 2026 | **No bulk file export is built, and none may be.** Desk's metadata export is already covered by the existing `Access Log` / `Permission Log` | AC-78 |
| 180-day log residency, 6-hour reporting | CERT-In | **No new log pipeline.** The access log is an existing DocType | — |
| Processor / Fiduciary split | DPDP + counsel 31 Oct | Every retention number is the employer's to set, with our cautious default — never Alvora deciding somebody else's statutory duty | US-16, OQ-1 |

Checked against `compliance-feature-map.md`'s shape: the access log, the legal-hold flag and
the settings-with-a-floor pattern are all **already-specified features reused**, not
respecified.

### 16.3 Visibility delta

**Who can see something after this slice that they could not see before:**

1. **A line manager can open a document their report photographed.** That is the feature, and
   for a fuel bill it is right and necessary.
2. **A line manager can open a *medical* receipt their report was compelled to photograph.**
   That is §0.5 — a named exposure **accepted by Surbhi on 3 November 2026 with her reason
   recorded**, answered only by the routing slice (**ALV-301**). Accepted is not discharged.
3. **Any staff login can list the stored name, size and url of every evidence file in the
   tenant** — Frappe's own `File` condition, not something 081 creates, but 081 makes it a
   complete index. Reduced to worthlessness by generated names (AC-16, AC-17, AC-49).
   **Residual risk R-2.**

**The negative cases, explicitly:** a colleague with no reporting line sees **nothing**
(AC-46 … AC-48). A CXO gains **nothing** by design — but see **OQ-2**, because the code does
not currently agree. Finance sees the bill of the claim they pay and **no day-fix file**.
Guest sees nothing: no public page, no token, no bearer link. **An employee sees who opened
their own file and nothing about anybody else** (AC-58).

### 16.4 Decision automation

**No.** Nothing in this slice automates or materially influences a decision about a person.
A human approver decides the claim; a human HR user decides the day. The file is evidence
placed in front of a person, and **the system does not read it** — no OCR, no amount
extraction, no scoring, no flagging. There is **no AI feature in this slice**, so §7 of the
compliance method does not apply, and none of the prohibitions is engaged.

**And it must stay that way:** AC-77 is the negative criterion that proves it.

### 16.5 Retention and deletion

| Object | Kept | On whose instruction | What survives an erasure request |
|---|---|---|---|
| The bill | to the end of the **8th financial year** after the claim's financial year, from `posting_date` | the employer's, with our default of 8 and a floor of 8 | **The bill survives**, because it is decision-bearing and legally required. The refusal names the statute (AC-64) |
| The day-fix file | **6 months** after the person's relieving date | the employer's, with our default of 6 | Honoured once the buffer has run; before then the purpose is live |
| An orphan upload | **24 hours** | nobody — it has no purpose at all | nothing; it is deleted either way |
| The claim, the request, the ledger entries | untouched by every pass | — | they are the record |
| The access-log row | follows its parent's clock | — | it holds no file, no url and no content |
| **Legal hold** | **wins, always**, on every pass | HR | — |
| **"For ever"** | **never available.** 0, blank and out-of-range are refused | — | AC-65 |

### 16.6 ⚠ Open compliance questions

| Question | Who must decide | What it blocks |
|---|---|---|
| **A compulsory medical bill reaches the line manager, and counsel's 1 Nov advice is not discharged in 081.** Do we ship the attachments knowing that, with the routing slice to follow? | **Surbhi** | **CLOSED, 3 November 2026 — ship.** Her reason: medical reimbursement at DTC is *"part of the CTC and just a formality"*. **Counsel's advice remains accepted-but-not-discharged**; closure sits with **ALV-301**. Full record and what she was shown: §0.5 |
| Is the 8-financial-year number a **tenant setting with a floor** or a fixed default for now? | **Surbhi**, on my recommendation | AC-65 only. **OQ-1 — ANSWERED 3 Nov 2026: a fixed default, not a setting** |
| Should a System Manager's Home row open an **individual** claim at all, now that it carries a bill? The brief's §9 says "summaries only"; the code opens the oldest claim | **Surbhi**, informed by security's recommendation (a count and a screen, never a claim) | Nothing in 081. **OQ-2** |
| Nobody has read the **Gazette** text of Companies Act s.128(5) or CGST s.36 — only reproductions and commentary | Surbhi, if a customer questionnaire will ever quote the statute | nothing in this slice | 
| **No off-server copy of any backup exists** (`BACKUP_BUCKET` unset; each `bench backup` deletes the previous set). From the day a bill is mandatory, DTC's statutory tax evidence lives on one disk — and the 8-year duty cannot be honoured through a disk loss. **ALV-299** | **Surbhi, with DevOps** | **Release.** Not the build | 

**Flagged, not ruled on.** I am not a lawyer, and nothing above is legal advice.

---

## 17 · Risks

| # | Risk | Label | Owner |
|---|---|---|---|
| **R-1** | **A compulsory medical bill reaches the line manager, through the queue and through the API doors of §0.1. Counsel's 1 November advice is accepted-but-not-discharged.** §0.5 | **OPEN — risk accepted, not removed.** Accepted by **Surbhi on 3 November 2026**, on the grounds that medical reimbursement at DTC is *"part of the CTC and just a formality"*. **Its only answer is the routing slice, ALV-301.** Not to be recorded anywhere as "low risk" or "resolved" | **Surbhi** — accepted 3 Nov 2026. Closure sits with **ALV-301** |
| **R-2** | Any staff login can list every evidence file's stored name, size and url. Generated names remove the harm; the listing remains | **Intentional trade-off.** A `File` query-condition hook is priced, not built | Surbhi, to accept or commission |
| **R-3** | **PDF is the one accepted type we cannot strip**, and it renders in an iframe on our own origin | **Acceptable simplification**, carried from ALV-287. Refusing PDF would wall out the office filer | Surbhi |
| **R-4** | A day-fix doctor's note reaches the line manager **by design**. The control is a notice, not a restriction | **Intentional trade-off**, Surbhi's D9 of 3 Nov 2026 | Surbhi |
| **R-5** | Mandatory raises volume and therefore the chance that identity and medical documents arrive at all | **Intentional trade-off** — it is the slice | Surbhi |
| **R-6** | **No off-server copy of these files.** ALV-299 | **Dangerous debt — escalate.** This slice depends on it | Surbhi + DevOps |
| **R-7** | A bill attached **in Desk** is not re-encoded, not capped and — if a PNG — not stripped. §5.7 | **Named limit.** HR is the uploader, volume is small, and capping Desk would refuse a scanned self-declaration | Surbhi to accept |
| **R-8** | The HEIC answer rests on an **untested assumption** that the browser canvas converts it. Nobody here has run one real iPhone upload | **Unverified.** A release check (OPS-25), with AC-6 and AC-19 as the honest failure path | engineer, then release |
| **R-9** | A deploy that reports success while the sites volume keeps the old `portal.js`, so the form ships **with no file control** | **Covered** by `refresh_bench_files.sh` and the portal-asset assertion — **provided the release plan keeps them** | DevOps |

---

## 18 · Prototype parity

Prototype parity is a standing rule: **what the approved prototype shows gets built exactly
as drawn, and any difference needs Surbhi's explicit agreement.**

| Prototype screen · state | Must ship | In 081? |
|---|---|---|
| `ec · 1-8` | the file control first in the modal, with all eight of its own states | **Yes** |
| `ec · 9` | the server's refusal in `ec-error` | **Yes** |
| `ec · 10-13` | the three send states with "and your bill", and the toast | **Yes** |
| `eclist · mix` | "Bill attached · View full size" and the honest "No bill attached" | **Yes** |
| `eclist · mix` — the chip reading **"Waiting for approval"** with no name | | **No — routing slice** (§0.4). The row keeps today's wording |
| `ar · 1-4` | the label, the notice **above** the buttons, the two buttons, the shown-back file | **Yes** |
| `arcard · mix` | one evidence line inside the existing card | **Yes** |
| `ap · 1` | the third line in the queue row, in words | **Yes** |
| `ap · 2-4` | View bill in the body above the decision, its opening state, its failure | **Yes** |
| `ap · 5` | the viewer above the sheet | **Yes** |
| `ap · 5b` | **not a screen to build** — it is what ships if nobody moves the z-index | n/a |
| `ap · 6` | an older claim's sheet saying there is nothing to open | **Yes** |
| `ap · 7` | the role dead end | **No — routing slice** (§0.4) |
| `hr · mix, view` | "Evidence attached · View" on the card; the viewer; no thumbnails | **Yes** |
| `desk · refuse` | both sentences, and "the draft is still saved" | **Yes** |

**Two deliberate differences from the approved prototype, both caused by the role leaving
the slice:** `eclist`'s "Waiting for approval" chip (the row keeps today's wording) and
`ap · 7`, the "Already decided" state (not built).

**Both were agreed by Surbhi on 3 November 2026** ("1 2 and 3 all ok"), so the
prototype-parity rule is satisfied for this slice. They did not block the build and have it
yet.** They are being put to her separately. They do not block the build — nothing is built
differently either way, because what is at issue is two things *not* being built. **No other
difference is specified, and none may be introduced at build without her word.**

---

## 19 · Traceability

Every brief line, prototype screen, `SEC`, `PRIV` and `OPS` item lands in an AC — or is
marked with the user's decision.

| Source | ID or line | Story | Acceptance criteria | Status |
|---|---|---|---|---|
| Brief | §3 "mandatory on the expense claim" | US-5 | AC-13, AC-23 | covered |
| Brief | §3 "the rule fires at submit on the document" (D4) | US-5 | AC-13, AC-14 | covered |
| Brief | §3 "a draft with no file stays a legal draft" | US-5 | AC-14 | covered |
| Brief | §3.1 claims already submitted stay decidable (D1) | US-5 | AC-13b | covered |
| Brief | §3.1a "a file, not a receipt" — the standing HR line (D4b) | US-1 | AC-2, AC-15 | covered |
| Brief | §3.2 1 MB image / 3 MB PDF, compress first (D5, D5b) | US-4 | AC-10 … AC-12 | covered |
| Brief | §3.3 the approver role routes a sensitive type (D3, D3b) | — | — | **moved to the routing slice — Surbhi, 3 Nov 2026** |
| Brief | §3.4 the day-fix notice, before the file picker (D9) | US-9 | AC-31, AC-32 | covered |
| Brief | §3.4 "no routing on regularizations" | US-9 | AC-31 negative half | covered |
| Brief | §1.4 HR adds their own expense types (D8) | — | — | **already works. Release-note line only, no code** |
| Brief | §7 the WOW — "Bill attached — view" on the queue row | US-11, US-12 | AC-36, AC-38, AC-41 | covered |
| Brief | §8 "a view line on both queue rows" | US-11, US-13 | AC-36, AC-44 | covered |
| Brief | §8 "one access-log row per viewer per file per day" | US-15 | AC-53, AC-54 | covered |
| Brief | §12 ≥70% of approvers open the file before deciding | US-15 | AC-53 (the instrument) | covered |
| Brief | §12 "uploads refused for size ≈ 0" | US-18 | AC-71 | covered |
| Brief | §16 kill criterion — five real bills legible | US-2 | **AC-7** | covered |
| Prototype | `ec · 1-13` | US-1 … US-7 | AC-1 … AC-28 | covered |
| Prototype | `eclist · mix` | US-8 | AC-29, AC-30 | covered |
| Prototype | `eclist` "Waiting for approval" chip (EL2) | — | — | **moved to the routing slice** |
| Prototype | `ar · 1-4` | US-9 | AC-31 … AC-34b | covered |
| Prototype | `arcard · mix` | US-10 | AC-35 | covered |
| Prototype | `ap · 1-6` | US-11, US-12 | AC-36 … AC-43 | covered |
| Prototype | `ap · 7` the role dead end (AP6) | — | — | **moved to the routing slice** |
| Prototype | `hr · mix, view` | US-13 | AC-44, AC-45 | covered |
| Prototype | `desk · refuse` | US-5 | AC-15 | covered |
| Design | AQ1 the viewer renders behind the sheet | US-12 | **AC-41** | covered |
| Design | EC4 HEIC | US-2, US-4 | AC-5, AC-6, AC-19 | covered |
| Design | EC2 the file survives Try again | US-7 | AC-26, AC-27 | covered |
| Design | EC6 1600 px / q82 / the step-down order | US-4 | AC-10 | covered |
| Design | EC8 four unlabelled inputs | US-19 | AC-73 | covered |
| Design | EL1 the employee sees their own bill | US-8 | AC-29 | covered |
| Design | AQ3 one viewer, four callers | US-12 | AC-42, AC-52 | covered |
| Design | AQ4 "Opening the bill…", viewer before Approve | US-12 | AC-38, AC-39 | covered |
| Design | AQ5 no file on either queue payload | US-11, US-13 | AC-36, AC-44 | covered |
| Design | AR2 360 px at 200% text | US-9 | AC-34b | covered |
| Design | AR3 the employee's own day-fix card | US-10 | AC-35 | covered |
| Design | HQ1 no thumbnails in HR's list | US-13 | AC-45 | covered |
| Design | UP1 never Frappe's "File size exceeded…" sentence | US-4 | AC-11, AC-12 | covered |
| Design | §12.1 two calls, not one | US-6 | AC-16, AC-24, AC-25 | covered |
| Design | AQ2 System Manager's Home row | — | — | **OQ-2, Surbhi's call. Not adopted in 081** |
| Design | UP2 My Documents' raw href | — | — | **explicitly out of scope; AC-52 stops the new surfaces copying it** |
| **081-SEC-1** | the permission pair on `Expense Claim` | — | — | **moved to the routing slice — Surbhi, 3 Nov 2026** |
| **081-SEC-2** | role scope in the query | — | — | **moved to the routing slice — Surbhi, 3 Nov 2026** |
| **081-SEC-3** | mandatory on the document at submit; the server's own sentence | US-5 | AC-13, AC-14, AC-15, AC-23 | covered |
| **081-SEC-4** | magic bytes; our name; our content type; HEIC refused; stripped; PDF not parsed | US-4 | AC-17 … AC-21, **AC-16b** below | covered |
| **081-SEC-5** | length before decode; one file; rate limit; the bind takes no unchecked id; one `File` row | US-4, US-6 | AC-17, AC-22, AC-24, AC-25, AC-79c | covered |
| **081-SEC-6** | one guarded stream; no `/private/files/`; nothing called protected | US-14 | AC-48, AC-51, AC-52, AC-79 | covered |
| **081-SEC-7** | no new `ignore_permissions`; new files at 0 with their own entry | US-20 | **AC-75** | covered |
| **081-SEC-8** | the notice present **and positioned**; never a protection | US-9 | **AC-31** | covered |
| **081-PRIV-1** | two clocks; legal hold; orphans; never "for ever"; counts per pass | US-16, US-17 | AC-59 … AC-70b | covered |
| **081-PRIV-2** | generated stored names; nothing personal in any log | US-4, US-14 | AC-16b, AC-24, AC-49, AC-57, AC-79b | covered |
| **081-PRIV-3** | one row per viewer per file per day; two `source` options + `reference_name`; the subject's own answer | US-15 | AC-53 … AC-58 | covered |
| **081-PRIV-4** | no second copy, no OCR, no new export or route | US-20 | AC-76, AC-77, AC-78 | covered |
| **081-PRIV-5** | nothing says masked, protected or safe | US-20 | AC-79 | covered |
| OPS-1 / ALV-299 | off-server backup | — | — | **release decision, Surbhi + DevOps. Not an AC** |
| OPS-2 | do not shrink the slice for storage | — | §11 | recorded |
| OPS-3 | 1600 px / q82 / the width ladder | US-4 | AC-10 | covered |
| OPS-4 | compression inline, no job | US-4 | §11, AC-10 (no queue asserted in AC-76) | covered |
| OPS-5 / OPS-21 | nginx untouched | — | AC-78 (no new route) + §11 | covered as a "do not" |
| **OPS-6 / OPS-22** | the caps are ours; `max_file_size` is not the enforcement point and is not changed | US-4 | **AC-22** | covered |
| OPS-7 / OPS-26 | one file per tap, no thumbnails, no preloading | US-13 | AC-45 | covered |
| OPS-8 / OPS-23 | the CI timeout 90 → 120 | — | — | **its own change, its own ticket, before this build. Not an AC of 081** |
| OPS-9 | keep `refresh_bench_files.sh` and the portal-asset check | — | §12 | recorded in the release plan |
| OPS-10 | one real phone photo as a fixture | US-2 | AC-7 | covered |
| OPS-11 / OPS-25 | the iPhone path; no `pillow_heif`; refuse in words | US-2, US-4 | AC-6, AC-19 + a release check | covered |
| OPS-12 | per-user upload rate limit | US-20 | AC-79c | covered |
| OPS-13 | say what deletes these files | US-16, US-17 | AC-59 … AC-69 | covered |
| OPS-14 | watch the deploy's backup duration | — | — | **FYI, release-time observation. Not an AC** |
| **OPS-15** | the orphan sweep, inside a job that already runs | US-17 | **AC-69, AC-70** | covered |
| OPS-16 | say what each clock is anchored to | US-16 | AC-63 | covered |
| **OPS-17** | `attached_to_doctype` / `attached_to_name` asserted **on the stored row** | US-6 | **AC-16** | covered |
| OPS-18 | one countable log line per refusal reason, no file name | US-20 | AC-79b | covered |
| OPS-19 | two on-demand numbers, HR only | US-18 | AC-71, AC-72 | covered |
| OPS-20 | no browser beacon | — | AC-78 | covered as a "do not" |
| **OPS-24** | the legibility test on the **device-then-server** output | US-2 | **AC-7** | covered |

**One AC referenced above and stated here so it is not lost:**

- **AC-16b ★** Given any evidence file stored by any door — the portal upload, a Desk sidebar
  attachment, `upload_file` through the REST API, or a data import — Then its `file_name` in
  `tabFile` matches **our** generated pattern `{parent}-{hash}{our extension}`, the extension
  is derived from the **magic bytes we read** and not from what the uploader supplied, and the
  **response's content type** for that file is derived from our stored name. Upload a file
  called `apollo-hospital-receipt-aadhaar-1234.pdf` and assert, by query, that **no row in
  `tabFile` contains any of those words**. *(081-SEC-4 clauses 2 and 3, 081-PRIV-2. The
  pairing matters: magic bytes alone would still let `x.html` be served as HTML from our own
  origin.)*

**Gaps:** none. Every item is either covered by an AC or carries a recorded decision.

---

## 20 · Open questions

| # | Question | Owner | Decision it blocks | My recommendation |
|---|---|---|---|---|
| **OQ-1** | Is the **8-financial-year** retention a **tenant setting with a floor of 8**, or a fixed default for now? | **Surbhi**, with me | **AC-65 only.** The clock, the legal hold and the erasure refusal are specified either way | **A setting with our default of 8 and a floor of 8**, refusing blank, 0 and anything lower. The employer is the Data Fiduciary and the duty is theirs; a hard-coded number makes Alvora the decision-maker on somebody else's statutory obligation. The mechanism already exists (`settings.py`'s `_DAYS` range refusal), so the setting is cheaper than arguing about it later. **ANSWERED by Surbhi, 3 Nov 2026: a fixed default for now, not a setting.** The constants stay in the module and AC-65 is not applicable as shipped. Making it a setting later is one `DEFAULTS` entry and one range |
| **OQ-2** | Should a **System Manager's Home row open an individual expense claim at all**, now that it carries a bill? `portal.js:6538` / `:6625` open the oldest claim; the brief's §9 gives the CXO "summaries only" | **Surbhi**, informed by security's recommendation | Nothing in 081's build. It decides whether a one-line fix rides here | Security recommends the row leads to a count and a screen, never a claim. **It is pre-existing behaviour the attachment makes matter, not something 081 creates.** **Carried, not answered** |
| ~~**OQ-3**~~ | ~~Do we ship a compulsory bill knowing a medical receipt reaches the line manager?~~ | Surbhi | — | **CLOSED 3 November 2026 — ship.** *"i dont see it as a big risk, as such expenses like medical bills are just the part of the CTC and are just a formality."* The full record, including what she was shown before deciding, is **§0.5**. **Risk R-1 stays open and accepted; ALV-301 is still its only answer** |
| OQ-4 | Is **"manager"** or **"supervisor"** the word? `field-checkin.html` uses both | Surbhi, or the designer | Nothing. One string | **"manager"** everywhere, and fix the check-in string when something next touches it. Does not block |
| OQ-5 | The Hindi strings are **machine drafts** and need a native reviewer; several surfaces have no draft at all | Surbhi | Release, not build | Ship with English fallback (AC-80) and get the review before DTC sees it |

---

## 21 · Assumptions

- `[ASSUMPTION]` **The browser canvas converts HEIC.** Safari decodes HEIC, so a canvas
  re-encode should yield JPEG. **Nobody here has tested it end to end.** AC-6 is the designed
  failure path and OPS-25 is the release test. Carried from the design.
- `[ASSUMPTION]` **One file per form is enough.** A claim is one bill at DTC. Carried from
  the brief.
- `[ASSUMPTION]` **The ESS portal is the only phone surface that needs this** — the field app
  is check-in, codes, punches and notices only. Confirmed for `field_app_records.py`, assumed
  for the app as a whole.
- `[ASSUMPTION]` A real photographed bill lands at **250-600 KB** at 1600/q82. DevOps'
  measured 145 KB is on a low-detail synthetic source and is optimistic.
- `[ASSUMPTION]` `Expense Claim Type`'s existing change tracking is not needed in 081,
  because no approver-role field is added here.
- `[UNVERIFIED — engineer to confirm]` `doc_events["File"]["before_insert"]` is the right
  hook point for renaming a stored file, and `file_url` follows the renamed `file_name`
  (§5.7).
- `[UNVERIFIED — engineer to confirm]` `System Settings.max_file_size` on **dev and
  production**. Local reads 0 → Frappe's 25 MB default. **If a stack already has 1 or 5, raw
  photo uploads break before our code runs** — OPS-22, and it is the one item that turns a
  requirement into a blocker.

---

## 22 · Subtract pass — what I deleted

Read once more asking only *what can I remove and still meet the requirement?*

**Removed:**

- **The whole approver-role specification** — the field on `Expense Claim Type`, the role
  resolution, the company scoping, the role-scoped queue, the permission pair, the
  concurrency answer, and the two states that only a role creates. Surbhi's decision, and
  the spec is roughly a third shorter for it.
- **A `reference_doctype` field on the access log.** The two new `source` values already say
  which doctype it is. A second column nothing filters on is exactly what 081-PRIV-4 forbids.
- **A "file attached" Check field on `Expense Claim`.** It would be a second place holding
  what `tabFile` already knows, and it would need keeping in step. The queue reads a parent
  → boolean map in one query instead.
- **A separate "orphan" doctype or a flag to mark an upload as pending.** An unparented
  private `File` owned by the caller already *is* that state, and §6.2 says so.
- **A fourth retention pass for the access-log rows.** They follow their parent's clock; a
  pass of their own would be a job for rows holding no file and no content.
- **A "claims missing a bill" report.** `counts()` returns the one number that matters, on
  demand, HR-only. A report is a screen where a number will do.
- **An alert, an email or a dashboard tile on the orphan count.** OPS-20 declines the beacon
  and OPS-19 declines the dashboard; I did not re-add either.
- **A fifth CI gate.** The four that exist — the permission suite, the isolation suite, the
  `ignore_permissions` ceiling, the PII-in-logs scanner — already carry every assertion here.
- **Three "for completeness" ACs** on states nobody can trigger: a viewer state for a deleted
  file (the generic open failure covers it), a confirm dialog on sending a day-fix with no
  file (optional fields do not get nudges), and a "camera permission denied" error message
  (a denied camera returns no file and no error, so a definite message would be a guess).
- **A `permission_query_conditions` hook on `File`.** Priced by security, not built, and I
  did not quietly reinstate it. Generated names remove the harm for a tenth of the risk, and
  §7.4 records what remains.

**Kept deliberately, though each costs something:** the employee seeing their own bill (it is
the only way a driver learns their own photo is readable, and the kill criterion's cheapest
instrument); the standing "No bill?" line (one grey line against somebody losing their
money); AC-49, which asserts an exposure rather than a protection, because an honest AC is
worth more than a comfortable one; and the 8-year bill pass, which will find nothing for
years — but the erasure refusal in AC-64 depends on the clock existing, and "we will add it
later" is not a plan.

---

## 23 · Ready check — Definition of Ready

**The brief**

- [x] One named user, one complete outcome — a driver files a claim with its bill, and the
      approver decides it.
- [x] The job to be done is in the user's own words.
- [x] Competitive analysis present, every claim labelled, including what we will not copy.
- [x] Kano class stated — **Must-be, no longer a proxy** (DTC asked for it, Surbhi, 3 Nov).
- [x] Persona enhancements decided, each in / later / no with a reason.
- [x] The WOW moment is named and achievable — the queue row's "Bill attached".
- [x] Out of scope is written down, and **§0 widens it with Surbhi's decision of today**.
- [x] **Surbhi approved the brief today.**

**The design**

- [x] A clickable prototype exists — `prototype-v1.html`, **approved by Surbhi today**.
- [ ] **The user's feedback is logged in `ux-learnings.md`** — I cannot verify that the
      designer has written today's design-gate feedback there yet. **Owner: the UX designer.
      It does not block the first day of work.**
- [x] Every state designed: empty, loading, error, no-permission, first-time. 66 states
      rendered and structurally checked.
- [ ] **Rendered geometry, tap heights and colour contrast are unmeasured** — the designer
      had no browser. **Owner: a human with a browser, before release.** Does not block build.

**The requirements**

- [x] `01c` written, with numbered `SEC` and `PRIV` items.
- [x] `07` §1-2 written with numbered `OPS` items. *(§3 "Requirements" is titled §2 in the
      file; its content is the requirements stage and it is complete.)*
- [x] Gap analysis done against the source actually installed, verdict per requirement.
- [x] Epic and stories written — named personas, INVEST-checked, sized, linked to prototype
      screens, **including the two must-not stories** (US-14, US-20).
- [x] Every story has at least one Given/When/Then AC with an observable oracle.
- [x] **Traceability complete** — every brief line, prototype screen, `SEC`, `PRIV` and `OPS`
      item maps to an AC or carries a recorded decision. **No gaps.**
- [x] Permission matrix written, including the negative cases.
- [x] Edge cases listed — amendments, cancellations, back-dating, leavers, re-hires, imports,
      multi-company, no-manager, concurrency (and why it cannot arise in 081).
- [x] NFR numbers pulled from the budget and made specific.
- [x] Migration/backfill stated — **nothing migrates**, written down anyway, with the
      rollback.
- [x] Compliance-impact sub-analysis present, all six sections plus the AI check.
- [x] Every ⚠ COMPLIANCE question names a human and what it blocks.
- [x] Nothing requires a prohibited capability. **No AI in this slice**, and AC-77 proves it.
- [x] New-Frappe-app checklist: **not applicable** — no app installed, no role created, no
      public page, no guest access, no self sign-up. Written down because the step is never
      skipped.
- [x] **Open questions have owners and none blocks the first day of work.** **OQ-3 is
      closed** — Surbhi decided on 3 November 2026 to ship with mandatory bills, with her
      reason recorded in §0.5 and risk R-1 left open and accepted. **OQ-1** (retention as a
      setting with an 8-year floor) and **OQ-2** (the System Manager Home row) stay open,
      need her word **before release**, and block nothing in the build. OQ-4 and OQ-5 are
      one string and a translation review.

**Verdict: ready to build. No failing box is a gap in this spec.**

Four things are still unproven, and **every one of them is a human release check, owned by a
person, not a hole in the requirements:**

| Still to do | Owner | Blocks |
|---|---|---|
| The **five-real-bills legibility judgement** on the device-then-server output (AC-7) | a human eye, with a DTC supervisor's bills | **release** — it is the brief's kill criterion |
| **Rendered geometry and colour contrast** — tap heights, 360 px overflow, 200% text | somebody with a browser | release |
| **One real iPhone upload, end to end** (OPS-25) | release readiness | release |
| **Reading `System Settings.max_file_size` on dev and production** (OPS-22) | DevOps | release — a value of 1 or 5 breaks uploads at DTC whatever our code does |

Two further items are owned by other people and block neither build nor release: the UX
designer's `ux-learnings.md` entry for today's design gate, and **Surbhi's agreement to the
two prototype departures the split caused** (§18) — the missing "Already decided" state and
the claim row keeping today's wording. Under the prototype-parity rule those still need her
word; the coordinator is putting them to her.

---

## 24 · Handoff note

**To `hrms-fullstack-engineer`, at impact analysis.**

Three things to watch out for, in order of what will cost you most.

**One: the slice you are building is not the slice the brief describes.** Read §0 before
anything else. The approver role, the routing, and the `permission_query_conditions` /
`has_permission` pair are **all out** — Surbhi's decision today. Claims keep going to the
employee's own approver through the existing `expense_approver_for`. If you find yourself
reading `inbox_api._with_hr_lwp` for a role-scoped queue, you have drifted into the next
slice.

**Two: §0.5 is decided, and the decision is not a licence to tidy it away.** A compulsory
medical bill reaches the line manager, 081 does not fix it, and **Surbhi accepted that risk
on 3 November 2026** on the grounds that medical reimbursement at DTC is part of the CTC and
a formality. Three consequences for you:

- **Do not invent a substitute control.** A screen-level hide would be the false protection
  the split exists to avoid, and `data-doors.md` forbids it.
- **Do not soften the record.** Counsel's 1 November advice is **accepted, not discharged**.
  R-1 stays open on the register and **ALV-301** is still its only answer. Nothing in your
  impact analysis, the implementation notes or a release note may read as "the risk was
  found to be low".
- If your analysis finds a cheap, honest, **permission-layer** control I have missed, say so
  at the strategy gate rather than building it — it would change the slice's shape.

**Three: the two unverified things that could cost you a day each.**
`System Settings.max_file_size` on dev and production has never been read (OPS-22) — if it
is already 1 or 5, uploads break at DTC on day one whatever our endpoint does, and that is a
release blocker, not a code change. And `doc_events["File"]["before_insert"]` as the rename
point (§5.7) is `[UNVERIFIED]`; if it is the wrong hook, tell me rather than moving the rule
into the portal, because `data-doors.md` is what makes that rule worth having.

**Where I disagree with nothing above me**, with one exception worth naming: the design's
§12.1 chose two calls over the brief's one, and I have specified two. The brief's sentence
was reasoning about *when the rule fires*, not about HTTP shape, so this is not a
contradiction — but it creates the orphan, and the orphan is why OPS-15 is a P1 and AC-69
exists.

**To `hrms-test-automation-engineer`:** seven ACs were paid for with somebody's time today
and each has a way of passing vacuously. **AC-16** must read the row back from the database,
not the response. **AC-22** needs three runs at three `max_file_size` values. **AC-13** needs
three doors, including an amended claim. **AC-31** is positional, not presence. **AC-7** must
run both re-encode passes. **AC-75** needs the new modules' own ceiling entries. And every
door test in US-14 must be run on a **freshly created site** — a copied site hid two failures
during ALV-249.
