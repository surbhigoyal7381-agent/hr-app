---
slice: 081-bill-and-evidence-attachments
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-11-03
status: waiting for Surbhi's approval of the strategy
inputs: [01-product-brief.md, 01a-ux-opportunities.md, 01b-ux-design.md, prototype-v1.html, 01c-security-privacy-requirements.md, 02-functional-spec.md, 07-devops-inputs.md]
---

# Slice 081 — Impact analysis and proposed strategy

**No code has been written. This document stops at a gate.**

Everything below was read in the installed source today, 3 November 2026, in the worktree
`.claude/worktrees/078-positions-faces` and inside the running container `hrlocal-bench`
(image `dev-3830ed3`, **Frappe v16.33.1**, Pillow 12.3.0). Labels: **Confirmed** (file and
line read) · **Measured** (I ran it) · `[ASSUMPTION]` · **Could not check**.

---

## 0 · Read this first — the one thing that changes the slice

### 0.1 ⚠ A portal expense claim waits for its approver as a **Draft**, not as a Submitted document

**This is the biggest finding in this analysis, and it makes two decisions in the spec wrong
as written.**

**Confirmed, three facts, read today:**

| Fact | Where |
|---|---|
| `apply_expense_claim` ends with `doc.insert(ignore_permissions=True)` — **it never submits**. A portal claim is created at `docstatus = 0` | `hr_api.py:2446` |
| The approver's queue looks for `docstatus: 0, approval_status: "Draft"` | `inbox_api.py:576-577` |
| **`decide_expense` calls `doc.submit()` — for Approve *and* for Decline** | `hr_api.py:2522-2523` |

So "a claim already submitted and waiting for an approver" **does not exist** on the portal
path. Every portal claim at DTC that is waiting for a decision right now is a **Draft with no
file**. Three consequences:

1. **Brief §3.1 / D1 and AC-13b protect the wrong set.** They exempt claims "already
   submitted", which on this code means claims *already decided*. The claims actually in
   flight are drafts, and a `before_submit` gate catches every one of them on the day 081
   ships.
2. **Declining becomes impossible.** A decline is a submit. With a bare "must have a file"
   gate, an approver cannot even decline a claim that has no bill. The claim is stuck for
   ever, and the employee's row says "Waiting" for ever. Nobody specified this.
3. **The refusal lands on the wrong person.** The submit is the approver's action, so the
   Desk sentence *"The draft is still saved. Only Submit is blocked."* is read by a line
   manager who cannot fix it — they do not have the employee's bill.

**My recommended answer, and it is one line of condition, not a new mechanism:**

> The gate fires only when the claim is being **approved** — `doc.approval_status ==
> "Approved"`. A decline needs no evidence; money only moves on an approval.

That keeps the rule where 081-SEC-3 wants it (on the document, at submit, so Desk, REST and
data import all obey it), it keeps a decline working, and it needs no date constant in the
code. What it does **not** do is exempt the drafts already waiting: on release day those still
cannot be approved until somebody attaches a file, and the only person who can is HR, in Desk,
by the §3.1a self-declaration route.

**So Surbhi has a decision — OQ-6 below.** Either:
- **(a)** accept that, and run DevOps' read command 1 first to learn how many open drafts DTC
  has, so we know whether that is five claims or five hundred; or
- **(b)** add a cutoff as well — the gate skips a claim whose `creation` is before the release
  date, stored as a site-config value set once at release. That is one extra condition and one
  extra setting, and it means no in-flight claim is ever stranded.

**My recommendation is (a) plus the count first.** A date cutoff is a permanent extra branch
in a permanent rule, and if the number is small the operational answer is cheaper than the
code. If the count comes back large, (b) is the right call.

### 0.2 §0.5 of the spec — the medical-bill exposure

I have read §0.5 and the handoff note. **I found no cheap, honest, permission-layer control
that the security engineer missed**, and I did not invent one. The only thing that closes it
is the `permission_query_conditions` / `has_permission` pair, which is out of scope by
Surbhi's decision. I confirmed today that **no such pair exists on `Expense Claim`** in either
app (`alvoraa_portal/hooks.py:448-472` lists six doctypes; `Expense Claim` is not among them),
and that staff logins are `System User` (**Measured**: 407 of 408 users on `ppj.localhost`),
so they hold the `Desk User` role and Frappe's wide `File` list condition applies to them.
**R-2 in the spec is real, and I verified the mechanism rather than taking it on trust.**

The exposure stands exactly as §0.5 writes it. **OQ-3 is still Surbhi's, and I agree with the
analyst that it should be settled before the build starts.**

---

## 1 · The six things already paid for — each confirmed or corrected

| # | The claim | Verdict |
|---|---|---|
| **1** | The `File` row must carry `attached_to_doctype` and `attached_to_name`, or the file falls back to `owner == user` | **Confirmed, exactly** |
| **2** | The 1 MB / 3 MB caps live in our code, never in System Settings `max_file_size` | **Confirmed — and one part of the reasoning is now *less* scary than OPS-22 says. See 1.2** |
| **3** | The mandatory rule fires at submit, not save | **Confirmed as a mechanism — but see §0.1: *who* submits is not who the spec assumes** |
| **4** | `.mpf-dv` is 1250, `.hm-ov` is 1300, and 1400 is clear | **Confirmed. 1400 is free. But the z-index is the *smallest* part of this fix — see 1.4** |
| **5** | Two re-encodes, 1600 px / q82, ladder 82→72→62 then 1280→1024 | **Confirmed as implementable by reuse, with two build rules the spec does not state** |
| **6** | Two `[UNVERIFIED]` items are mine | **Answered. One of them is a "no" — see §2** |

### 1.1 The parent fields — confirmed

`frappe/core/doctype/file/file.py:989-1026`. In order: Administrator → not private and reading
→ `owner == user` → a DocShare row → **and only then** `attached_to_doctype and
attached_to_name` → the parent's `has_permission("read")`. With no parent the function falls
through to `return False` at line 1026.

So an unparented private bill is readable by **its uploader and nobody else** — not the
approver, not HR, not the Desk sidebar, and not any sweep that walks the claim. **OPS-17 is a
P1 for exactly the reason it says.** AC-16 must read the row back from `tabFile`; I will write
it that way.

### 1.2 The caps — confirmed, and OPS-22 is narrower than it looks

**Confirmed:** `File.check_max_file_size()` reads `get_max_file_size()` = System Settings
`max_file_size` (MB) → `conf` → **25 MB** (`frappe/core/api/file.py:81-91`,
`file.py:871-883`). It runs inside `File.before_insert` → `save_file`, so it happens **before
any app hook**. A site-wide 1 would refuse the 3 MB PDF and break employee documents (which
chose 5 MB). **OPS-6 and 081-SEC-5 clause 2 are right, and `max_file_size` must not be
touched.**

**Measured today:** on both local sites `max_file_size` is **0** → 25 MB applies. Site config
holds no value either. `strip_exif_metadata_from_uploaded_images` is **1**, which strips JPEG
EXIF and (confirmed at `file.py:813-819`) does nothing for a PNG — so 081-SEC-4 clause 5 earns
its place.

**Where I make OPS-22 cheaper.** OPS-22 says a stack already set to 1 or 5 "refuses every
upload at DTC on day one, whatever our endpoint does". **That is only true if we upload through
Frappe's own `/api/method/upload_file`.** If the upload is our own endpoint taking a base64
string — the `employee_photo` shape — then the raw 4 MB photo never becomes a `File` at all:
we decode it in memory, re-encode it, and create the `File` with the **final** bytes. The
ceiling then only ever sees ≤ 1 MB or ≤ 3 MB.

So my strategy uses **our own base64 endpoint, not `upload_file`**, and that choice alone:

- turns OPS-22 from a release blocker into "confirm it is not 1 or 2, because of the 3 MB PDF";
- lets us read the magic bytes **before** anything is written to disk;
- lets us choose the stored file name **before** `save_file` runs, which is the only point at
  which that is possible (see §2);
- skips Frappe's `ALLOWED_MIMETYPES` filename check for non-desk users (`handler.py:195-198`),
  which guesses from the device's name and is weaker than our magic-byte test anyway.

It costs one thing, said plainly: base64 adds about a third to the request body. A 900 KB
device-shrunk picture posts as about 1.2 MB. nginx allows 50 MB on both server blocks
(OPS-5, unchanged), so this is free in practice.

### 1.3 Submit, not save — confirmed as a mechanism

**Confirmed:** `Expense Claim` has `is_submittable: 1`; the attachment sidebar is hidden while
`frm.doc.__islocal` (`attachments.js:47-48`); `allow_attachments` appears **nowhere** in
`doctype.json` (grep count 0). A `before_submit` doc_event on `Expense Claim` already exists
(`hooks.py:435-437` → `refuse_own_submit`), so the hook point is proven in this codebase.

**Confirmed permissions** (read `expense_claim.json`): the **Employee** role holds create,
read, write, share, print, email, report and **no submit, no cancel, no delete**. The spec's
state table is right.

**But read §0.1.** The mechanism is correct; the assumption about who meets it is not.

### 1.4 The viewer — 1400 is clear, and the z-index is the cheap third of this job

**Confirmed:** `.mpf-dv` z-index **1250** (`panels.css:3064`), `.hm-ov` **1300**
(`panels.css:712`), `.gp-backdrop` **1200** (`panels.css:1489`). Between 1301 and 1999 **nothing
is used.** Above it sit `.mob-acct-menu` at 2000 and the two toast layers at 3000 — and a toast
*should* stay above the viewer, so **1400 is the right number and it is free.**

No stacking-context trap: `mpfShowDoc` appends the box to `document.body`
(`portal.js:11202`), not inside the sheet, so the number actually takes effect. The
`panels.css:1254` warning about descendants does not bite here.

**The part the design under-prices.** Three separate behaviours in `portal.js` are gated on
`#emp-drawer.open`, which is the Positions drawer and is **not** the approver's sheet:

| Line | What it does | What happens over the approver's sheet today |
|---|---|---|
| `portal.js:11406-11413` | the Escape order: viewer → enlargement → drawer | **Does not run.** The sheet's own handler at `portal.js:6492` catches Escape, calls `e.stopPropagation()` and **closes the sheet**, losing the reader's place — the exact bug the drawer handler exists to prevent |
| `portal.js:11425-11438` | the Tab focus trap | **Does not run.** Tab walks out of the viewer into the sheet behind it |
| `portal.js:11229-11234` (`mpfCloseDoc`) | focus returns to the button that opened it | **Does not run.** Focus is lost, so **AC-42 fails** |

So AQ3's *"generalise `mpfShowDoc` to (blob, name, who revokes it)"* is three gates and one
edit to the sheet's own Escape handler, not one argument. The sheet's handler is in a hot
function and must be changed to defer to `MPF_DOC` first. **I will do that; I am recording it
because it is more work than the design says, not less.** `.mpf-dv` is already listed in
`scripts/check_portal_trays.js:99`, so the geometry check travels with it for free.

### 1.5 The two re-encodes — confirmed, plus two build rules the spec does not state

`employee_photo._reencode(blob, edge, quality)` is already parameterised on edge and quality
(`employee_photo.py:141-158`): `Image.open` → `convert("RGB")` → `thumbnail((edge, edge),
LANCZOS)` → `save(JPEG, quality, optimize=True)`, with no `exif=` and no `icc_profile=`. The
ladder is a loop over that call. `_decode`'s check order — string length, then strict base64,
then magic bytes — is exactly what 081-SEC-5 clause 1 asks for, and adding `%PDF-` to `MAGIC`
is one tuple entry.

**Measured:** Pillow **12.3.0**, `heif` feature **absent**, `pillow_heif` **missing** in the
running bench venv. OPS-11, 081-SEC-4 clause 4 and the design's EC4 all rest on a real
measurement. HEIC is refused in words; no `pillow_heif` goes in the diff.

**Two rules the spec leaves open and the build needs:**

1. **Every rung of the ladder re-encodes the ORIGINAL bytes**, never the previous rung's
   output. Five chained encodes would compound generation loss on exactly the artefact AC-7
   judges. One line of discipline, easy to get wrong.
2. **There is no number for the raw input we accept.** The spec gives the *stored* caps (1 MB,
   3 MB) and says "length before decode", but never says what length. `[ASSUMPTION]` I will
   use **12 MB raw for an image** (a 12 MP phone photo is 3–8 MB, so this takes the ordinary
   case and refuses the outlier) and **3 MB raw for a PDF** (a PDF is stored as it arrived, so
   its raw and stored limits are the same number). Both as module constants, checked against
   the base64 string's length first. **If Surbhi wants different numbers, say so now.**

I also looked at whether the server's re-encode could be **skipped** when the phone already
sent a JPEG inside the caps, to avoid the double pass. **I recommend against it**: 081-SEC-4
clause 5 makes the re-encode the strip, and a skip would make our metadata stripping depend on
a site setting we do not control. The double pass stays, and AC-7 / OPS-24 is how we find out
whether it costs legibility. **Measured by DevOps:** 46 ms for the normal device-shrunk path.

---

## 2 · The two `[UNVERIFIED]` items — answered

### 2.1 `doc_events["File"]["before_insert"]` as the rename point — **NO. It cannot work.**

**The spec's §5.7 hook point does not exist.** Traced and confirmed today:

1. `Document.insert` calls `run_method("before_insert")` at `document.py:480`, and that is the
   **earliest** hook on an insert — `run_before_save_methods()` (before_validate, validate,
   before_save) comes afterwards at line 486.
2. `Document.hook`'s `compose` runs **the controller's own method first**, then the app hooks
   (`document.py:1633-1649`: `add_to_return_value(self, fn(self, ...))` and only then the loop
   over `hooks`).
3. `File.before_insert` (`file.py:105-142`) calls **`self.save_file(content=...)`** inside
   itself. `save_file` guesses the content type from `file_name`, appends the content hash,
   and `save_file_on_filesystem` writes the bytes and sets
   `file_url = "/private/files/<file_name>"` (`file.py:786-865`).

So by the time an app `before_insert` hook runs, **the bytes are already on disk under the
device's name and `file_url` already points at them.** Renaming `file_name` in that hook would
leave the url and the on-disk path carrying `apollo-hospital-receipt.pdf` — the exact thing
081-PRIV-2 exists to prevent — and would silently break the file, because `file_url` would no
longer match `file_name`.

**And renaming afterwards is not safe either.** `save_file` **de-duplicates by content hash**
(`file.py:823-840`): if a byte-identical file already exists, the new row is given the
*existing* row's `file_url` and nothing new is written. Renaming that file on disk would break
the other row. So an `after_insert` rename is a real hazard, not a tidy alternative.

**What I will do instead, and what it costs:**

| Door | Stored name |
|---|---|
| **The portal upload** (our own endpoint) | **Ours.** We set `file_name` before the insert, which is the only moment it works |
| Desk sidebar, REST `upload_file`, data import | **The uploader's.** No hook can change it |

**So AC-16b as written cannot be met on all four doors.** I recommend it is **narrowed to the
portal path**, with the Desk/REST residual recorded beside R-7 (which already says a Desk
attachment is not re-encoded, not capped and — if a PNG — not stripped). The honest reasoning:
the employee-supplied bill, which is the one with a disclosing device name on it, always comes
through the portal; on Desk the uploader is HR, who chose the name themselves.

**The one alternative, priced and not recommended:** Frappe reads an app-level `write_file`
hook inside `save_file` (`file.py:851-855`). Overriding it would let us name every file in the
product — and would mean re-implementing `save_file_on_filesystem` for **every attachment in
every module**, for one slice's naming rule. That is the definition of a change whose blast
radius dwarfs its purpose. **Priced, not built.** Surbhi can commission it later if a Desk
file name ever matters.

### 2.2 `System Settings.max_file_size` on dev and production — **I did not look, and I may not.**

**Could not check.** Reading a dev or production site is a dev-stage action and needs Surbhi's
word (`CLAUDE.md` §1). DevOps' command 2 in `07` §6 is the read, and it is still unrun.

**But §1.2 above changes what rests on it.** With our own base64 endpoint, a value of 1 or 2
on a stack would refuse the **3 MB PDF** and nothing else; images would still work. So this is
a release check with a known, narrow consequence — not the day-one blocker OPS-22 describes.
**Still worth running before release.** My recommendation: ask for it once, with DTC's open
draft-claim count from §0.1, in the same read.

---

## 3 · Functional impact

### 3.1 Cross-module reach

| App | Touched | How |
|---|---|---|
| **`alvoraa_portal`** | **Yes — the whole slice** | One new module; edits to `hr_api.py`, `attendance_correction.py`, `inbox_api.py`, `portal.js`, `request-modals.html`, `panels.css`, `hooks.py`, the access-log DocType JSON, the ceiling test |
| **`hrms`** | **Configuration only** | Two `alvoraa_legal_hold` Custom Fields created in `after_migrate`, the `branch_scope.after_migrate` pattern (**Confirmed**, `branch_scope.py:39-60`, which already adds `alvoraa_branch` to both `Expense Claim` and `Attendance Request`). **No hrms Python file changes** |
| **`erpnext`** | **No** | |
| **`frappe`** | **No change, heavy reuse** | Standard `File` rows, `frappe.local.response` streaming, `rate_limit`. `max_file_size` is neither read nor written |
| **`alvoraa_goals`** | **No** | |
| **`alvox_compensation`** | **No** | Not installed |

**No upstream source is edited. Nothing goes in `patches.txt`** — the DocType change travels
with the app and `bench migrate` applies it; the Custom Fields go in `after_migrate`. That
keeps us out of one hot file entirely.

### 3.2 Every caller of every function I will change — grepped today

| Function | Callers found | What I must not break |
|---|---|---|
| `hr_api.apply_expense_claim` | `portal.js:10062`; `hr_api.py` itself; **6 assertions in `test_expense_and_scoping.py`, 4 in `test_expense_birthdays_076.py`, 2 in `portal_phone_070_test.js`** | The new `file_url` argument is **keyword, defaulted to None**, so every existing caller still compiles — but those twelve tests will start failing once the endpoint refuses a claim with no file. **They are the pin tests for slice 076 and must be updated with a file, not loosened** |
| `attendance_correction.raise_correction` | `portal.js` (×2), **`next-time.js`** (the discarded-redesign preview page), `attendance_correction.py` (×5 internal), **20 assertions in `test_attendance_correction.py`, 8 in `portal_correction_test.js`, 1 in `test_leave_063_rules.py`** | Optional argument, so nothing breaks. **`next-time.js` gets no file control** — see the known limit below |
| `inbox_api._part_expense_approvals` | `inbox_api.py:1064`; 1 test | The `PARTS` contract check at `inbox_api.py:1073` — I add a field to a row, never a part |
| `hr_api.decide_expense` | `portal.js`, `hr_api.py` (×4), **6 + 4 assertions** | §0.1. A decline must keep working |
| `hr_api.expense_approver_for` | `hr_api.py` (×3), `patches/v1_0/expense_claim_approver_backfill.py` | **Untouched by this slice** |
| `mpfShowDoc` / `mpfOpenDoc` | `portal.js` (×3 / ×2), `portal_faces_078_test.js`, `test_employee_documents_078.py`, `employee_documents_read.py` docstring | The ALV-287 decisions: no sandbox on the PDF iframe, the footer line, the blob lifetime. **Four callers after this slice, so the signature change must not break the Positions one** |
| `submitExpenseClaim` | `request-modals.html`, `portal.js`, `portal_phone_070_test.js` (×2) | The three send-failure states (`portal.js:10033-10095`) and the **absence of a Try again on no-answer** — there is no duplicate guard, and adding one is not this slice |
| `hmPendRowHtml` / `hmExpenseSheet` | `portal.js` (×3 / ×2), `portal_expense_birthdays_076_test.js` | The row stays **one** `<button>` (AC-37) |
| `acReqCard` | `portal.js` (×3), `scripts/check_attendance_strip.js` | That script is a CI gate on this markup |
| `grooming.refuse_side_record` on `File.validate` | already registered at `hooks.py:429-431` | **Checked: it returns for any parent that is not a Grooming Mark or Review** (`grooming.py:620-624`), so it does not interfere |

### 3.3 Persona impact

| Persona | What changes | What it costs them |
|---|---|---|
| **Employee / frontline** | A camera button first in the claim form; the picture shown back with its size, which is the only way a driver learns his own bill is readable; his own bill one tap from his own row; an optional file on a day-fix with the notice **before** the picker | **A claim with no bill cannot be filed.** The standing "No bill? Ask HR…" line is the whole mitigation. Hindi is a machine draft on most of it |
| **Line manager / expense approver** | "Bill attached" / "No bill attached" in words on the queue row; **View bill** in the sheet body above the decision; the viewer above the sheet | **§0.1: on release day they may be unable to approve the drafts already in their queue.** And **§0.5: they can open a medical receipt** |
| **HR Manager / HR User** | The file in the Desk sidebar for free; "Evidence attached · View" on the day-fix card; two numbers on demand | Two duties that are documentation, not code, and fail silently if nobody tells them: the two-step expense-type setup, and the self-declaration route. **Plus, from §0.1, attaching statements to in-flight drafts on release day** |
| **CXO / System Manager** | **Nothing, by design** | **But the code does not agree.** `portal.js:6538` / `:6625` open the oldest individual claim for a System Manager, which from this slice carries a bill. **Pre-existing. OQ-2 is Surbhi's, and I am not fixing it unasked** |
| **Finance** | The bill of the claim they pay | — |

### 3.4 HRMS domain impact

**Expense claims** and **attendance** only. **Payroll** is untouched: the claim still books
through `payable_account` and `cost_center` from `_expense_claim_accounts`, which I do not
change. **Leaves, appraisals, goals, org structure, learning: not engaged.** Nothing in this
slice reads a leave balance, an attendance total or a holiday list.

One domain note worth stating: `branch_scope` already copies `alvoraa_branch` onto both
`Expense Claim` and `Attendance Request` at save (**Confirmed**), so location HR's Branch
permission already reaches both parents, and therefore reaches the bytes through the parent's
read. **081 adds no company or branch logic, because it adds no role.**

---

## 4 · Non-functional verdict — seven dimensions

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **neutral, with one number to hold** | The upload is **46 ms** of CPU on the normal device-shrunk path (DevOps, Measured), 0.5–1.5 s on the raw fallback, inline, no job. The queue row's attachment flag is **one** extra `frappe.get_all("File", filters={"attached_to_name": ["in", names]})` for the whole page — the same shape as the existing single read of `Expense Claim Detail` at `inbox_api.py:590`, so 200 rows cost the same as 20. **Zero evidence calls on any list render.** One file per tap, ≤ 1 MB, is one of 8 request slots for a few hundred ms |
| **Security** | **improves on the new surfaces, unchanged on the old** | Magic bytes before anything is stored; our own name and therefore our own served content type (**Confirmed**: `save_file` sets `content_type` from `file_name`, `file.py:813`); length checked on the string before decode; one guarded stream and no `/private/files/` in any response; a per-user rate limit. **It does not improve the thing §0.5 names, and nothing in my code or copy will claim it does** |
| **Reliability** | **improves** | Every refusal is a sentence a person can act on. The chosen file survives Try again. The upload retries on its own. The access-log insert is wrapped so a failed log never stops a reviewer. The orphan sweep is bounded and safe to run twice. **One new failure mode, named: §0.1's stuck draft** |
| **Scalability** | **neutral** | 0.7–2.2 GB a year typical, 6.5 GB worst, against a 25 GB deploy gate. No new container, queue, bucket or CDN. One extra entry in a `daily` list that already holds eight |
| **Maintainability** | **neutral to improves** | One new module; the four reuse points are existing, documented patterns. **It does add three hot-file edits** (`portal.js`, `hr_api.py`, `hooks.py`) and one change to the sheet's Escape handler. Four `<label for>` attributes repay a small accessibility debt |
| **Data integrity** | **improves** | The `File` row is the single source of truth — no second field, no "has a file" check box, nothing to keep in step. The bind is one row, two fields, inside the call that created the parent. Both retention clocks are anchored to the **parent**, never to `File.creation` and never to `modified` |
| **Compliance / privacy** | **improves on retention and logging, unchanged on the exposure** | Two clocks with a floor, legal hold that always wins, real erasure with the bytes, a count per pass, an erasure refusal that names the statute, a log row per viewer per file per day, and generated stored names on the portal path. **Set against that: new personal data at volume, compulsory, free-form in content, with a reader who is not always the right one.** §0.5 |

**No new `ignore_permissions`.** `hr_api.py` stays at **67**, `attendance_correction.py` at
**0** (both **Confirmed** in `test_portal_security_010.py:736-764`), and the new module gets
its own entry. **One argued bypass**, and only one: the access-log insert, because the
`Alvoraa Photo Access Log` DocType grants read to System Manager and HR Manager and **create
to nobody** (**Confirmed**, read its JSON). That is the same single bypass
`employee_documents_read.py:258` already carries, for the same reason.

**Good news I can now state rather than assume:** the `File` insert and the bind **need no
bypass at all.** `file.json` grants the role **`All`** create, read, write and delete, and
`File.has_permission` returns True on `owner == user`. So the new module's ceiling is **1, not
2** — and `employee_photo._store`'s comment that "an employee holds no create permission on
File" is, as far as I can read it, **wrong**. I am not changing that file (it is not this
slice's), but it is worth a note for whoever next touches it.

---

## 5 · Parallel-work check

### 5.1 What came in while I read

`git fetch origin` brought **one** commit into this worktree's view:

- **`b7841327` — "ALV-286: a named way back to the tray, and the documents say they are
  coming"** (someone else's). It touches `panels.css` (+15), `portal.js` (+64/-3),
  `templates/includes/ess/parts/drawers.html` (+6) and adds
  `alvoraa_portal/tests/portal_faces_078_test.js` (+48).

**Three of those four files are files I will change.** The slice folder sits in the
`078-positions-faces` worktree, which is on `slice/078-positions-faces` at **`dcf74d58`** — one
commit behind `origin/dev`. **I have absorbed nothing quietly: that commit is named here, and
I will rebase onto it before the first line of code.**

ALV-286 is in the Positions **drawer** and the mini-profile back link; 081's `portal.js` work
is in the expense modal, the claim list, the day-fix card, the approver's queue and sheet, and
`mpfShowDoc`. **`mpfShowDoc` / `.mpf-dv` is the one place the two could meet**, because
ALV-286's "the documents say they are coming" is about the same drawer the viewer is used
from. I will read that diff line by line at rebase.

### 5.2 Other sessions' uncommitted work in the main checkout

`git status` in `C:/Surbhi-Git/hr-app` shows **40+ modified files that are not mine**,
including `hr_api.py`, `hooks.py`, `auth.py`, `attendance_correction.py`, `inbox_api.py`,
`patches.txt`, `public/css/ess/panels.css` and several payroll modules. **Every one of those
belongs to somebody else. I will not stage, revert, reformat or tidy any of them**, and I will
not edit in the main checkout at all.

### 5.3 Files I will change, and who else is in them

| File | Hot? | Who else | Plan |
|---|---|---|---|
| `public/js/ess/portal.js` | **Yes, the hottest** | **ALV-286 (now on `origin/dev`)**; the board shows `070-readable-on-phone`, `064-old-chart`, `064-old-v2` all holding portal.js locally and **none pushed**; uncommitted changes in the main checkout | **Sequence.** Rebase on `origin/dev` first. My functions (`submitExpenseClaim`, `ecList`, `acForm`, `acReqCard`, `hmPendRowHtml`, `hmExpenseSheet`, `mpfShowDoc`, the Escape handlers) do not overlap 070's or 064's Positions-chart work. **If 070 or 064 land before me, I rebase again and re-read.** |
| `public/css/ess/panels.css` | **Yes** | ALV-286 (+15 lines); uncommitted in the main checkout; 064 holds the Positions block | **Split.** I touch one existing line (`.mpf-dv` z-index) and append one new block. I do not reformat anything |
| `hr_api.py` | **Yes** | `063-dtc-leave` holds `apply_leave` and others locally, unpushed; uncommitted in the main checkout | **Split by function.** I touch `apply_expense_claim` only. 063 is in the leave functions |
| `hooks.py` | **Yes** | uncommitted in the main checkout; several unpushed branches | **Split.** Three additions: one key in `doc_events["Expense Claim"]`, one `after_migrate` entry, one `daily` entry. I turn one `before_submit` string into a two-item list and change nothing else |
| `attendance_correction.py` | Yes | `045-redesign-wave4` claimed it long ago (stale); uncommitted in the main checkout | **Split.** `raise_correction` only |
| `inbox_api.py` | Yes | `063-dtc-leave`; ALV-269/275 (already on dev) | **Split.** `_part_expense_approvals` and the day-fix queue rows only |
| `templates/.../request-modals.html` | Medium | nobody on the board | mine |
| `.../doctype/alvoraa_photo_access_log/*.json` | Low | 078/079 (both already on dev) | mine. **Additive only:** two Select options, one new field |
| `tests/test_portal_security_010.py` (`CEILINGS`) | Medium | **ALV-291 adds one line here and is unpushed** | **Sequence or split.** One dict entry each, different keys — a trivial conflict if both land |
| `docs/security/whitelisted-endpoint-review.md` | Low | — | mine |
| **Not touched:** `patches.txt`, `own_record_permission.py`, `manager_scope.py`, any hrms Python file, `nginx.conf`, any workflow | | | |

### 5.4 The pin test for every existing feature I touch

| Feature I could break | The test that fails if I do |
|---|---|
| The three send-failure states and the missing Try again | `portal_phone_070_test.js` (existing) + one new assertion that the no-answer state still offers **no** re-send |
| The approver's queue row is one button | `portal_expense_birthdays_076_test.js` + AC-37 |
| `decide_expense` still declines | **New test, and it is the pin for §0.1** |
| ALV-287's viewer: no sandbox, the footer line, the blob revoke | `test_employee_documents_078.py` + `portal_faces_078_test.js` (both existing) |
| The Positions drawer's Escape / focus order (AC-60, AC-62) | existing, and it must still pass after `mpfShowDoc` is generalised |
| The day-fix card markup | `scripts/check_attendance_strip.js` (existing CI gate) |
| `hr_api.py` at 67 bypasses | `test_portal_security_010.TestSec16IgnorePermissionsCeiling` |

**Once the strategy is approved I add a row to `.claude/work-in-progress.md`** naming the
worktree, these files and the bench state, and I keep it current.

### 5.5 Bench and containers

Other sessions were stopping and starting containers today. `hrlocal-294`, `hrlocal-291`,
`hrlocal-297`, `hrlocal-067` and `hrlocal-bench` are all up. Everything I did today was
**read-only**: `cat`, `grep` and one read-only `mysql` SELECT against `ppj.localhost` to read
three System Settings values. **I changed no site setting, no container and no file in any
bench.** The board says the bench was freed at ~18:30 by ALV-294; I will claim my own
container for the test run and name it on the board.

### 5.6 A question only Surbhi can answer

**Is anybody outside this machine working in `hr_api.py`, `portal.js` or `inbox_api.py` right
now?** The board only sees this machine. `git log origin/dev --since="7 days ago"` shows those
three files moving several times a week.

---

## 6 · Proposed strategy

### 6.1 Rung on the cost ladder

**Rung 4 — new code**, for one new module plus edits to existing functions. **Two items sit at
rung 1 — configuration**: the two `alvoraa_legal_hold` Custom Fields, and the two new `source`
options on a DocType that already exists.

Every cheaper rung, and why it is not available:

| Rung | Why rejected |
|---|---|
| **0 · already there** | True on Desk — the sidebar works today on any saved claim. **False on the portal**, which is where 442 staff are, and false for every reviewing screen |
| **1 · configuration** | There is no box. `allow_attachments` does not exist in Frappe 16.33.1 (grep count **0** in `doctype.json`). `max_file_size` is the wrong lever and must not be used (§1.2). `max_attachments` on the parent looked promising for "one file per claim" — **it does not work for us**, because `validate_attachment_limit` only runs in `before_insert` while `attached_to_name` is set, and our bind happens *after* the insert (**Confirmed**, `file.py:396-422`). It would constrain Desk and not us |
| **2–3 · customisation** | A Custom Field, a Property Setter or a Client Script cannot put a file control on a hand-written portal page, and there is no DocType field to set |
| **5 · new DocType** | **Rejected and not needed.** The evidence is a standard `File` row with two fields set; the access log already exists and takes two Select options and one Data field |
| **6 · new app** | No |

### 6.2 What gets built, file by file

**One new module. Eleven files touched. No new DocType, no new app, no new job, no new
queue, no new dependency, no nginx change, no `patches.txt` entry.**

| # | File | What |
|---|---|---|
| 1 | **NEW** `alvoraa_portal/alvoraa_portal/expense_evidence.py` | The whole server side: module constants (the two stored caps, the two raw ceilings, the ladder, `MAGIC` with `%PDF-`); `_decode` (length → base64 → magic bytes, the `employee_photo` order); the re-encode ladder, always from the original bytes; `upload_evidence`; `bind` (the four ordered checks of §5.6); `require_evidence_before_submit` (the gate, with §0.1's condition); `open_evidence` (the `open_employee_document` shape, parent permission, stream, log); `log_view`; `who_opened_mine`; `counts`; `daily` (three passes, three counts). **Its own ceiling entry: 1, argued — the access-log insert** |
| 2 | `hooks.py` | One key in `doc_events["Expense Claim"]` (`before_submit` becomes a two-item list); one `after_migrate` entry for the two Custom Fields; one `daily` entry. **Nothing added to `permission_query_conditions` or `has_permission`** |
| 3 | `hr_api.py` | `apply_expense_claim(..., file_url=None)`: refuse with the server's own sentence; bind after insert, in the same transaction. **Ceiling stays 67** |
| 4 | `attendance_correction.py` | `raise_correction(..., file_url=None)`: bind if given, say nothing if not. **Ceiling stays 0** |
| 5 | `inbox_api.py` | One extra `File` query per page in `_part_expense_approvals` → a boolean per row; the same for the day-fix queue rows. **Never a url in a payload** |
| 6 | `public/js/ess/portal.js` | The file-control block (one implementation, two forms, eight states); the canvas re-encode, reusing `field-checkin.html:718-724`'s technique for a chosen file; `submitExpenseClaim` keeps the file across Try again; the claim row and the day-fix card lines; the queue row's third line; **View bill** in the sheet body; `mpfShowDoc` generalised and the **three `#emp-drawer` gates** plus the sheet's Escape handler at `:6492` |
| 7 | `templates/includes/ess/parts/request-modals.html` | The file block **first** in the modal; four real `<label for>` attributes |
| 8 | `public/css/ess/panels.css` | `.mpf-dv` 1250 → **1400**; one new block for the file control |
| 9 | `.../doctype/alvoraa_photo_access_log/alvoraa_photo_access_log.json` | Two `source` options; one `reference_name` Data field, read-only, indexed. Additive; existing rows keep their value |
| 10 | `tests/test_portal_security_010.py` | One `CEILINGS` entry for the new module |
| 11 | `docs/security/whitelisted-endpoint-review.md` | The four new endpoints |

**Four new `@frappe.whitelist()` endpoints and no more**: `upload_evidence`, `open_evidence`,
`who_opened_mine`, `counts`.

**One build detail from the source that AC-79c does not cover:** `_limited` wraps Frappe's
`rate_limit` with `methods=["POST"]`, and `rate_limit` **skips any request whose method is not
in that list** (**Confirmed**, `rate_limiter.py:129-135`). So `open_evidence` must be declared
`@frappe.whitelist(methods=["POST"])` or its 60-opens-an-hour limit will never fire. I will
declare it POST-only and pin it in a test.

### 6.3 The order I would build it in — one thin vertical path first

1. **The gate and its condition** (§0.1), with the decline test, as the first commit. It is the
   decision that could change everything else.
2. **`upload_evidence` + the bind + AC-16 read back from `tabFile`.** Server only, proven by
   test.
3. **The claim form's file control end to end**, one role, one path: a driver files a claim with
   a photo and the `File` row has its parent.
4. **`open_evidence` + the viewer above the sheet + the three gates.** The approver can read it.
5. The queue rows, the employee's own rows, HR's card.
6. The day-fix side (one argument, one bind, the notice, the positional test).
7. The access log, `who_opened_mine`, `counts`.
8. Retention: three passes, three counts, legal hold.
9. Hindi, labels, 200% at 360 px.

### 6.4 Risks and trade-offs, in the order I would want them weighed

| # | Risk | Label | Owner |
|---|---|---|---|
| **E-1** | **§0.1 — every portal claim waiting for a decision is a Draft with no file.** Declines break, and in-flight claims may strand | **Must be decided before the build.** My answer: gate on `approval_status == "Approved"`, and read DTC's open-draft count first | **Surbhi · OQ-6** |
| **E-2** | **§2.1 — the generated stored name can only be ours on the portal path.** No File hook fires before the bytes are written, and a post-insert rename is unsafe because `save_file` de-duplicates by content hash | **Intentional trade-off.** Narrow AC-16b to the portal; record the Desk residual beside R-7. The `write_file` override is priced, not built | **Surbhi to accept · OQ-7** |
| **E-3** | **The viewer over the sheet is three gates and a hot-function edit**, not one z-index. Get the Escape order wrong and an approver loses their place in the sheet | **Named cost.** Pinned by a test that presses Escape with the viewer open over the sheet | engineer |
| **E-4** | **Twelve existing assertions in four test files will start failing** the moment the claim endpoint refuses a claim with no file | **Expected, and the right kind of failure.** They are updated to pass a file, never loosened | engineer |
| **E-5** | **R-2 confirmed by me, not just inherited:** staff logins are System Users, hold `Desk User`, and Frappe's `File` list condition therefore gives them the stored name, size and url of every bill in the tenant | **Intentional trade-off** — generated names reduce it to noise on the portal path, and E-2 limits that to the portal path | Surbhi |
| **E-6** | **The raw-input ceiling is a number nobody has set.** I propose 12 MB image / 3 MB PDF | `[ASSUMPTION]`, cheap to change | **Surbhi, one line · OQ-8** |
| **E-7** | **R-6 / ALV-299 — no off-server copy.** From the day a bill is mandatory, DTC's statutory tax evidence is on one disk | **Dangerous debt — escalate now.** This slice depends on it; it is not mine to fix | **Surbhi + DevOps** |
| **E-8** | **OPS-23 has not landed.** `ci.yml:336` is still `timeout-minutes: 90`, and DevOps measured a run at 85 min 49 s. CI will fail on a timeout during this build and look like a test failure | **Temporary debt**, removed by one line in its own change **before** this build | DevOps |
| **E-9** | **R-8 — nobody has run one real iPhone upload.** The HEIC answer rests on the browser canvas converting it | **Unverified.** AC-6 is the designed failure path; OPS-25 is the release test | engineer, then release |
| **E-10** | **The new retention pass deletes real data** (the 6-month day-fix clock). `grooming.erase_daily` ships **off** behind a site-config flag for exactly this reason | **Decision:** I propose the 8-year bill pass and the orphan sweep ship **on**, and the 6-month day-fix pass ships **off** until Surbhi switches it, following the grooming precedent | **Surbhi · OQ-9** |
| **E-11** | **`next-time.js` also calls `raise_correction`** (the discarded-redesign preview page). It gets no file control | **Acceptable simplification** — the attachment is optional there, so a day-fix raised from that page behaves exactly as today. Recorded so nobody calls it a bug | engineer |

### 6.5 Where I disagree with what is above me

Four places, all of them mechanism, none of them a product decision:

1. **§0.1** — the brief's D1 and the spec's AC-13b rest on a premise the code contradicts.
   **This is the one that needs Surbhi.**
2. **§2.1** — the spec's `before_insert` rename point does not exist, and AC-16b must narrow.
   I am telling the analyst rather than moving the rule into the portal, as the handoff asked.
3. **§1.2** — OPS-22 is real but narrower than "a day-one blocker", provided the upload is our
   own base64 endpoint rather than Frappe's `upload_file`. I recommend our own endpoint for
   four independent reasons, and this is one of them.
4. **§1.4** — AQ3 is priced as one argument and is really three gates plus one hot-function
   edit. More work than stated, and I am saying so before, not after.

I agree with everything else, including the analyst's two calls over the brief (two HTTP calls
rather than one, and the orphan sweep that follows from it) and the security engineer's refusal
of HEIC and of a `File` query-condition hook.

### 6.6 Subtract pass — what I removed from my own plan

Read once more asking only *what can I delete and still meet the requirement?*

**Removed:**

- **A second module for the retention passes.** One module, one subject. The three passes are
  ~60 lines inside `expense_evidence.py`.
- **A `has_evidence` helper called from two places.** It is one `frappe.get_all` with an `in`
  filter; a helper with two callers that each want a different shape is not a helper.
- **A shared base for the two forms' file control.** One JavaScript function with a container
  argument, not a class with two subclasses.
- **A `write_file` hook override** to make the generated name true on every door. Priced in
  §2.1 and rejected: a product-wide re-implementation of Frappe's filesystem write for one
  slice's naming rule.
- **`max_attachments = 1` as a Property Setter.** Investigated, and it does not work for our
  bind (§6.1). It would only constrain Desk, which nobody asked for.
- **Skipping the server re-encode when the phone already sent a small JPEG.** Faster and
  wrong: the re-encode *is* the metadata strip.
- **A client-side quality ladder.** One canvas pass at 1600/q82; the server's ladder is the
  control and already exists.
- **A `reference_doctype` field on the access log.** Two `source` values already say which
  doctype it is.
- **Any fix to `portal.js:6538` / `:6625`** (the System Manager's Home row, OQ-2) and any
  change to `employee_photo._store`'s wrong comment. Both are tempting, neither is this slice,
  and both are written down here instead.
- **A new CI gate.** The four that exist carry every assertion in this slice.

**Nothing was added that the spec did not ask for**, except the two numbers in §1.5 that the
spec left blank and the code cannot run without.

---

## 7 · Open questions for Surbhi — before I write a line

| # | Question | Blocks | My recommendation |
|---|---|---|---|
| **OQ-3** *(carried)* | **Do we ship a compulsory bill knowing a medical receipt reaches the line manager, with the routing slice to follow?** | **The build starting.** I agree with the analyst | **No recommendation offered.** I looked for an honest permission-layer control and found none |
| **OQ-6** *(new, mine)* | **§0.1.** The gate fires on the approver's submit, which is also how a decline is recorded. Gate on `approval_status == "Approved"` only — and do we also exempt claims created before release? | **The first commit** | Gate on **Approved** only, and **run DevOps' command 1 first** to learn DTC's open-draft count. Add a creation cutoff only if that number is large |
| **OQ-7** *(new, mine)* | **§2.1.** The generated stored name can only be ours on the portal path. Accept that and narrow AC-16b, or commission the `write_file` override? | AC-16b's wording | **Accept and narrow.** The disclosing device name only ever arrives through the portal |
| **OQ-8** *(new, mine)* | **The raw-input ceiling.** I propose 12 MB for an image, 3 MB for a PDF | One constant each | As proposed |
| **OQ-9** *(new, mine)* | **Does the 6-month day-fix retention pass ship on or off?** It deletes real data; `grooming.erase_daily` ships off behind a flag | The retention commit | **Bill pass and orphan sweep on; day-fix pass off** until she switches it |
| **OQ-1** *(carried)* | 8 financial years: a tenant setting with a floor of 8, or a fixed default? | AC-65 only | **A setting with a floor**, as the analyst recommends. The mechanism already exists in `settings.py` |
| **OQ-2** *(carried)* | Should a System Manager's Home row open an individual claim at all? | Nothing in 081 | **Not in this slice.** Pre-existing; I will not touch it unasked |
| **OQ-5** *(carried)* | Hindi is a machine draft and several strings have none | Release, not build | Ship with the English fallback (AC-80), get the review before DTC sees it |

**Two reads I need Surbhi's word for, and they are reads, not changes:**

1. **DTC's open draft expense claims** — the number OQ-6 turns on.
2. **`System Settings.max_file_size` on dev and on production** — OPS-22, now a narrow check
   (§2.2) rather than a blocker.

Both are DevOps' commands 1 and 2 in `07` §6, quoted and unrun.

---

## 8 · What I could not check

1. **Anything on dev or production.** DTC's claim count, its open drafts, `max_file_size` on
   either stack, free disk. All need her word.
2. **One real iPhone upload end to end.** Nobody here has run one (R-8, OPS-25).
3. **A real photographed bill through both re-encode passes.** AC-7 / OPS-24 needs the five
   real DTC bills; the pipeline is ready for them, the bills are not here.
4. **Rendered geometry and colour contrast.** The designer had no browser and neither have I.
   A human with one must check before release.
5. **The ten door tests of US-14, run for real.** That is the test engineer's, on a freshly
   created site — a copied site hid two failures during ALV-249.

---

**Nothing is built. I stop here for the strategy gate.**
