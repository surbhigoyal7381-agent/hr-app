---
slice: 082-joiner-to-employee
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-11-04
status: draft for the business analyst. Recommendations only — Surbhi decides. I approve nothing.
narrows: 078-SEC-12 (and its 079 §1.2 carry-forward) — see §2
inputs:
  - 082/01-product-brief.md (hrms-product-manager, 4 Nov 2026)
  - 079/01c-security-privacy-requirements.md and 079/00-decisions.md (mine, and Surbhi's)
  - counsel's rulings of 31 Oct 2026 as listed in 079/00-decisions.md §7 — I have NOT read the written advice
  - code read in this worktree on 4 Nov 2026, file:line cited throughout. I ran nothing.
  - .claude/context/security-compliance-baseline.md (verified 24 Aug 2026 — 72 days old, inside the 90-day window; stale on 22 Nov 2026)
  - .claude/context/data-doors.md
---

# 082 · Security and privacy requirements — one button, and a document that moves

## 0 · The short version, for Surbhi

**The button is safe and small. The document move is the risky half, and it has one
problem nobody has written down yet.**

Three things, in order of how much they matter:

1. **The button is fine.** Narrowing 078-SEC-12 to "no code writes the joining date" is
   the right call, and it is *stronger* than the brief claims — `date_of_joining` is
   already locked at field level 2, so only HR User, HR Manager and System Manager can
   write it at all (`employee_field_rights.py:40-42`, **verified in code**). The brief's
   proposed test (no date in the payload) plus that lock is enough. I accept 082-SEC-1
   to 082-SEC-3 with two additions, below.

2. **Moving the file takes it off a clock that exists and puts it on a clock that does
   not exist.** I searched: there is **no retention or purge anywhere for
   `Employee Document` files**. `expire_documents` only changes a row's *status* when an
   expiry date passes; it deletes no bytes
   (`hrms/hrms/alvoraa_employee_documents/employee_documents.py:224-259`, **verified in
   code**). So "it moves onto the employer's own document retention" is not true today —
   it moves onto nothing. Your decision of 4 Nov is a sound *purpose* argument, and I
   think it is right. But as built it means an Aadhaar image is kept for ever unless
   somebody deletes it by hand. **That is the part I would put to counsel in writing.**

3. **The picture is less protected than the number.** `pan_number` and the statutory IDs
   sit at field level 1 — HR Manager only (`employee_field_rights.py:53-56`). The
   *photograph of the same card* lands in a child table that carries **no permission rows
   and no field levels at all** (`employee_document.json`: `istable: 1`, `permissions: []`,
   **verified in code**), and Frappe serves the private file on the parent Employee's own
   read permission with **no `has_permission` hook on that path** — traced in our own code
   comment at `alvoraa_portal/alvoraa_portal/employee_documents_read.py:25-38`. So whoever
   can read an Employee row can fetch that Employee's Aadhaar image by URL, and no rule we
   write in the portal changes it. OQ-2's count is therefore **must-know**, and I cannot
   do it — see §7.

Nothing here is a P0. Nothing is live. This is a requirements note, not a review.

---

## 1 · Threat model, four lines

**Who would want this, and what is the cheapest way to get it?** A curious colleague with
read on `Employee`, and the cheapest way is the one that always wins here: a normal screen,
or a `/private/files/...` URL seen once over a shoulder or in a forwarded email. Not an
outsider. The joiner themselves is **not** in this slice's threat model: the slice adds no
joiner-facing path at all.

**Blast radius of one mistake.** One person's identity documents landing on the wrong
person's personnel record, visible to everyone who may read that record. Not cross-tenant —
nothing here leaves the site. The brief's Risk 5 (HR links the wrong Employee) is the worst
case and it is a **real** leak, because today nothing moves and the mistake is recoverable.

**What this makes possible that was impossible before.** An **identity document on an
`Employee` record** — new in this product. 078-SEC-11 explicitly forbade attaching a joiner
upload to `Employee`, and that is the clause this slice reverses. No new collection, no new
outbound flow, no model path, no new public route, no new DocType, no new job.

**How would we find out?** Badly, and this is the gap. There is **no read log on a private
file fetched by URL**, and the `logger("alvoraa")` INFO lines that would record the move are
**discarded in production**: `log_level` is unset, so Frappe defaults to ERROR
(079/00-decisions.md §6c, recorded by Surbhi on 2 Nov). So the proof that a move happened
must be **queryable state**, not a log line — see 082-SEC-5.

---

## 2 · What happens to 078-SEC-12 — I agree with narrowing it, with one addition

078-SEC-12 says *no code path anywhere creates an `Employee` from a submission, and no code
copies a submission value onto one*. It is carried forward unchanged by 079 §1.2. The reason
behind it is a paid-for fault: a back-dated joining date makes Frappe mark the person Absent
for every day since, and deleting those rows does not help.

**The brief's three rules are enough for the joining date.** My judgement, asked for
plainly:

- The date is protected **twice**, not once. 082-SEC-1's payload test is the first lock. The
  second is already shipped and the brief does not know about it: `date_of_joining` is in
  `LEVEL_2` (`employee_field_rights.py:40-42`), so a write from any role outside
  HR User / HR Manager / System Manager is refused by Frappe itself. A prefill endpoint that
  returned a date would still not let a non-HR caller save one.
- `reqd: 1` on `Employee.date_of_joining` is **[ASSUMPTION — not verified by me]**. ERPNext
  is not checked out in this worktree and I ran nothing. The task says it was verified today;
  I am recording that as the caller's verification, not mine. The engineer confirms it before
  building, as the brief's Risk 1 already requires. **If it is not mandatory, stop** — the
  brief's kill criterion is right.

**The addition the brief is missing.** 078-SEC-12 has a second half — *no code copies a
submission value onto an `Employee`* — and this slice breaks that half too, not only the
"creates" half. Six typed fields and a set of files now cross over. So the narrowed rule
must say what **may not** cross, or the next person will add the next field. That is
082-SEC-4.

**One thing I will not let go quietly:** 078-SEC-11's clause "never attached to `Employee`"
is reversed by this slice. That reversal is the document move, and it is the whole of §4.
Write it down in the spec as a reversal, not as a new feature.

---

## 3 · Data inventory — the delta only

078's and 079's inventories stand. What changes:

| Data | Class | Purpose | Retention | Who may see it |
|---|---|---|---|---|
| The **prefill payload** (six mapped fields + full name), in flight | Personal | Save HR retyping seven fields | **Never stored by this slice.** It lives in one unsaved form in one browser | The HR login that asked for it, and nobody else |
| The **six fields once saved on `Employee`** | Personal | The personnel record | The employer's employee-record retention (outside this slice) | Whoever may read `Employee` today. **No change** — these fields exist on `Employee` already |
| The **moved `File`** (PAN, Aadhaar, any ticked type) | **Restricted** | HR's verification of who this person is | **None. There is no clock.** See §0.2 and 082-PRIV-2 | **Anyone with read on the parent `Employee`** — by Frappe's own file gate, not by our choice |
| The **`Employee Document` row** set to *Received*, with `received_on` and `received_by` | Personal (it names an HR user and a date) | Proof the document arrived, and when | With the Employee record | Anyone with read on the parent `Employee`; the Positions drawer shows it only for ticked types (`employee_documents_read.py:94-125`) |
| The **joiner's photograph**, if OQ-3 says it moves | Personal, and a face | The employee photo surface | 078's photo rules | 078's photo audience, with its access log |

**The line that matters:** this slice stores no new field and asks the joiner for nothing.
It **relocates** files. Every privacy question below is about the relocation.

---

## 4 · Access intent — including who must NOT see what

| Actor | Must be able to | **Must NOT** |
|---|---|---|
| **HR Manager** (write on the submission today) | Press the button, read the prefill, save the Employee, link it, and have the files move with it | Have the prefill hand them a joining date, or any date |
| **HR User** (read-only on submissions, per 079 §4) | Nothing new | Call the prefill endpoint, or trigger a move. Read-only means read-only |
| **A joiner account** | Nothing at all | Call the prefill endpoint; read, create or write any `Employee`; reach any moved file |
| **A plain staff login (Employee role only)** | Their own documents, through the surfaces that already exist | Another person's moved file, by URL or by endpoint |
| **A manager-ish role with read on `Employee`** | Whatever they can already do | **This is the open question, and the answer is not ours.** If the tenant has given them read on `Employee`, Frappe will serve them the moved Aadhaar image. See 082-PRIV-1 |
| **CXO** | Nothing new | Any individual document |

**The five `data-doors.md` questions, answered plainly:**

1. **Which door stops everyone else?** For the prefill: Frappe's `read` on
   `Alvoraa Joiner Submission` **and** `create` on `Employee`, checked server-side. For the
   moved file: the **parent `Employee`'s own read permission**, which is the tenant's
   configuration and nothing we write.
2. **Tested as a plain staff login through the API?** Must be — prefill endpoint and moved
   file, as four logins (joiner, plain staff, manager, HR User), through `/api/method` and
   through the raw `/private/files/...` URL.
3. **Fresh site and real tenant?** Fresh site for the tests. A **read-only count at DTC**
   before the move ships (082-PRIV-1).
4. **How many bypasses?** Target **zero new**. See 082-SEC-3.
5. **What could a manager change or share?** On `Employee`, whatever they can today — plus,
   newly, **share the moved file's URL**, which is question 1's answer again.

---

## 5 · Abuse cases

Each as *this actor, in this state, calling this path, sees this data.*

| # | Actor and state | Path | What they get without the requirement | Stopped by |
|---|---|---|---|---|
| **A1** | A **manager** with read on `Employee`, signed in | `GET /private/files/joiner-ALV-J-0007-Aadhaar.jpg` after seeing the URL once, **or** `/api/method/...get_employee_documents` if the tenant ticked that type | A colleague's Aadhaar card. Frappe's private-file gate ends at the parent Employee's read and **no `has_permission` hook fires** (`employee_documents_read.py:25-38`) | **082-PRIV-1** — the count decides whether the move ships. There is no code control available here, and I will not pretend there is |
| **A2** | **HR**, having linked the **wrong** Employee | Save on the submission | Person A's identity documents on person B's record, and the nightly job then erases the submission, so the mistake is no longer recoverable | **082-SEC-6** — the link step names the person it is about to merge into, and confirms |
| **A3** | A **joiner** account, signed in, curious | `/api/method/<the prefill endpoint>` | The six fields of **any** submission, if the endpoint takes an id and does not check rights | **082-SEC-2** |
| **A4** | A **plain staff login** | `/api/method/frappe.client.get_list` on `Employee Document` with `parenttype=Employee` | Every colleague's document status and **`attachment` URL**, from a child table with no permission rows. *This door exists today and is not created by this slice* — but this slice is what makes an Aadhaar image sit behind it | **082-PRIV-1**, and the door test. Name it even though it predates us |
| **A5** | **Anybody**, after a partly failed move | — | The submission's nightly erase deletes the files that did not move, because `delete_the_documents` matches on `attached_to_name` (`alvoraa_joiner_submission.py:198-220`). Two files on the Employee, one gone for ever | **082-SEC-5** — all or nothing, in the same transaction as the link |
| **A6** | **HR**, pressing the button and abandoning the form | — | Nothing. No Employee, no change to the submission, no file moved. Safe by design | Worth one test (brief Risk 4). Not a finding |

---

## 6 · Requirements

Rule ids written into security logs use the slice-qualified form **`082-SEC-n`** /
**`082-PRIV-n`**. The analyst traces every one to an acceptance criterion.

### 082-SEC-1 · No code writes the joining date, and no date reaches the prefill

Accepted as the brief wrote it, with the second lock named. **What must be true:** the
prefill payload contains **no `Date` or `Datetime` value of any kind** — not
`date_of_joining`, not `date_of_birth`, not a default, not a null placeholder. The only
writer of an `Employee` in this slice is HR pressing Save on a form they can see.

*How it is tested:* a unit test calls the prefill endpoint as HR and asserts, **against the
returned payload** (not the screen), that every key's value is checked against
`Employee`'s own meta and **no key whose fieldtype is `Date` or `Datetime` is present**.
Written from the meta, not from a hand-written list, so a field added later cannot escape
it. A second assertion: the payload's key set is exactly `COLUMN_FOR_TICK`'s keys plus
`first_name`, and nothing else.

### 082-SEC-2 · The prefill endpoint is HR-only, and it is the only new entry point

**What must be true:** one whitelisted read-only method. It takes the submission name, and
before it returns a single field it requires **`read` on that `Alvoraa Joiner Submission`
row** (through `frappe.has_permission` with the doc, so User Permissions apply) **and
`create` on `Employee`**. It writes nothing, inserts nothing and creates no `Employee`. It
is rate-limited on the **signed-in user**, reusing `field_app_limits._limited(..., "user")`
as 079-SEC-4 does. No second endpoint. No endpoint that saves.

*How it is tested:* door tests through `/api/method`, **not through the screen**, as five
principals — Guest, a joiner account, a plain staff login, a manager, HR User — each
refused; HR Manager allowed. Plus one test that an HR login scoped to company A is refused
a company B submission.

### 082-SEC-3 · No new `ignore_permissions`, and the ceilings prove it

**What must be true:** the move runs inside HR's own save, with HR's own rights. The
ceilings in `test_portal_security_010.TestSec16IgnorePermissionsCeiling` for
`alvoraa_joiner_submission.py` (**4**) and `joiner_housekeeping.py` (**6**) do not rise. A
new file starts at **0**.

**One thing to settle before the build, and I could not settle it:** whether re-pointing a
`File`'s `attached_to_doctype` / `attached_to_name` and inserting a child row on `Employee`
succeeds with HR Manager's own rights. Frappe checks permission on the *target* document
when `attached_to` changes, and HR Manager has write on `Employee`, so I **expect** yes —
but that is **Inference**, not verified: `frappe` is not checked out in this worktree and I
ran nothing. **Fail-closed default meanwhile:** build it with HR's own rights and let it
fail loudly. If it genuinely cannot be done without a bypass, that is **one** counted
bypass with a written reason and a raised ceiling — and it must be raised in the same commit
that adds it, never later.

*How it is tested:* the existing ceiling test, unchanged, plus one test that performs the
whole move **as an HR Manager session** (not as Administrator). A move that only works as
Administrator is not a move.

### 082-SEC-4 · The narrowed 078-SEC-12 names what may cross, and refuses the rest

**What must be true:** exactly one list in one place governs what crosses from a submission
onto an `Employee`, and it is the existing `COLUMN_FOR_TICK` (`alvoraa_joiner_submission.py:51`)
inverted, plus `full_name` → `first_name`. **Nothing at field level 1 or level 2 may be
written by any code in this slice** — no `pan_number`, no bank field, no `designation`, no
`grade`, no `company`, no `status`, no `user_id`, and no date.

This is the half of 078-SEC-12 the brief did not narrow, and it is the half that stops the
drift. The joiner's own typed claim must never land in a column HR is relied upon to have
verified — 079 §6 reason (1) and (3), which stand unchanged.

*How it is tested:* a test reads the prefill payload's keys, looks each one up in
`employee_field_rights.LEVEL_1` and `LEVEL_2`, and **fails if any key appears in either**.
Generated from those constants, so adding a field to them automatically tightens the test.

### 082-SEC-5 · The move and the link are one step, or neither happens

**What must be true, and this is ALV-306's fix by construction:**

1. The files move **in the same database transaction as the `employee` link being set**. If
   any part of the move raises, the save fails and the link is not written — so the status
   never becomes *Made an employee*, so `_erase_the_redundant_copies` never picks the row up.
   This matters because that pass runs **first** in `run_daily`, before the document clock
   (`joiner_housekeeping.py:68-80`, **verified in code**).
2. **All or nothing.** A partial move is the A5 scenario: `delete_the_documents` matches on
   `attached_to_name`, so anything left behind is deleted that night, bytes included
   (`alvoraa_joiner_submission.py:198-220`).
3. The proof that a move happened is **queryable state** — the `File` rows'
   `attached_to_doctype`/`attached_to_name`, and the `Employee Document` rows'
   `attachment`, `received_on`, `received_by` — **never a log line**. `logger("alvoraa")`
   INFO is discarded in production (079/00-decisions.md §6c).
4. `is_private` stays **1**. No moved file ever becomes public.
5. A file whose type has no checklist row **still moves**, as a plain attachment, and the
   confirmation line says so honestly ("3 documents, 1 not on the checklist"). Nothing is
   dropped silently. The checklist rows only exist at all when the
   `employee_documents` feature is on (`employee_documents.py:44-46`) and only for types
   that apply to the grade — and the prefill sets no grade, so **the no-row case is the
   likely one, not the edge case**.
6. A moved row is set to **Received**, never **Verified**. `check_can_verify` must never be
   reached by this slice's code.

*How it is tested:* (a) hire a joiner with three files, run `joiner_housekeeping.run_daily`,
assert the Employee still has all three and the submission has none; (b) force the child-row
write to raise and assert **no file moved and `employee` is still empty on the submission**;
(c) assert every moved `Employee Document` row's status is `Received` and
`verified_by` is empty; (d) assert every moved `File` still has `is_private = 1`.

### 082-SEC-6 · The link step names the person before it merges

**What must be true:** before the files move, HR is shown the `employee_name` of the
`Employee` they picked and confirms. A2 is the worst outcome in the slice and the confirm is
one line.

*How it is tested:* a test presses the real confirm path and asserts the payload carries the
employee it named (per the 28 Oct rule — test what it sends, not what it draws). Plus one
test that a refusal moves nothing.

---

### 082-PRIV-1 · The document move does not ship until somebody has counted who can read an `Employee`

**This is the load-bearing privacy requirement, and it is a gate, not code.**

**What must be true:** before the document half ships, a **read-only count** on the real
tenant answers two questions:

1. How many **enabled logins hold `read` on `Employee`** (by role, including
   `Employee Self Service` and anything manager-ish), and what each one's User Permissions
   narrow it to.
2. How many hold **`read` on `Alvoraa Position`**, which is what `register.may_view()` gates
   (`hrms/hrms/alvoraa_org_structure/register.py:68-72`), and whether
   `alvoraa_positions_document_types` is non-empty at that tenant — because the Positions
   drawer serves the `attachment` of every **ticked** type to everyone who passes
   `_guard` + scope (`employee_documents_read.py:94-125`).

**Why it changes the control, in one sentence:** if any non-HR role holds read on `Employee`,
then moving an Aadhaar image onto `Employee` shows it to that role, and **no rule we can
write stops it** — Frappe's private-file gate ends at the parent's read permission with no
`has_permission` hook on the path (`employee_documents_read.py:25-38`), and
`Employee Document` is a child table with no permission rows and no field levels at all
(`employee_document.json`). The number is HR-Manager-only at level 1; the picture of the same
card would not be.

**Fail-closed default until the count is in:** the **button ships, the document move does
not**. That is the brief's own split and I endorse it.

**I could not do this count.** It needs a read-only query on the DTC site, which is
production, and I do not probe production. The access I would need: a read-only
`bench --site` console on a restored backup, or someone else running the count and pasting
the output. See §7.

*How it is tested:* the count itself is evidence, dated and recorded in the slice folder, not
a test. The test that goes alongside it is the door test: as a plain staff login and as a
manager, fetch a moved file's `/private/files/...` URL directly and record **what actually
happens**. If it is served, that is a finding to put in front of Surbhi before the move
ships — not a test to soften.

### 082-PRIV-2 · The moved document needs a retention answer, and today there is not one

**The honest statement, first.** Surbhi's working decision of 4 Nov — the documents move,
because a hired joiner is a different purpose from a candidate — is **recorded as hers** and
I think the purpose reasoning is right. Her words: *"all the data including the documents are
transferred to employee's record. after that only this delete documents on new joiners form
make sense."*

**The DPDP reasoning, for and against, and I am not a lawyer.**

*For the move:* purpose limitation works on purposes, not on files. The candidate-screening
purpose ends when the person is hired; an **employment** purpose begins, and holding the
identity document HR verified is part of it. Counsel's ruling 4 is written about *"a
non-joiner's identity document"* — by its own words it does not reach a person who joined.
Ruling 1 makes the employer the Data Fiduciary, so the retention choice is theirs, and the
`Employee Document` checklist that already ships is the lawful home for it. Deleting the only
copy of a document HR verified also destroys the evidence that defends the verification in a
grievance — the priority order's auditability point.

*Against the move, and this is the part that needs an answer:* **it moves the file from a
clock that exists onto a clock that does not.** I searched the whole app: there is **no
retention, purge or deletion of `Employee Document` files anywhere**. `expire_documents`
changes a row's `status` to *Expired* when an expiry date passes and deletes nothing
(`employee_documents.py:224-259`). The only retention keys we ship are the joiner ones
(`hrms/hrms/alvoraa_org_structure/settings.py:127-210`). Counsel's own logic in ruling 4 —
*a photograph of an identity card goes much sooner than the record it came with* — applies
with the same force to an employee's card as to a candidate's. And counsel's 18 Sep policy
prohibits indefinite soft deletion; "kept for ever unless somebody deletes it by hand" is
worse than a soft delete, because nothing even flags it.

**What must be true:** the spec states, in one sentence that a customer could read, **how
long the employer keeps a moved identity document and what deletes it**. Three ways to be
true, cheapest first:

1. **Already there** — the employer's own employee-record retention covers it. *Rejected: it
   does not exist in the product.*
2. **Configuration / documentation** — the slice ships the move and says plainly, in the
   tenant's notice and in the questionnaire answers, that an employee document is kept for
   the employment and is deleted by HR by hand. Honest, cheap, and **not a control**.
3. **New code** — an employee-document clock. **Out of scope for this slice** and I am not
   asking for it here; it is a slice of its own.

**My recommendation:** ship the move with option 2, say it plainly, and put the clock on the
backlog as a named gap — **and get counsel's one line in writing before the move is switched
on at a tenant**, because this is the one point in the slice that turns on law. ALV-215
already gates switch-on of the joiner form; this belongs in the same letter.

*How it is tested:* a test asserts that a hired joiner's moved files **survive**
`run_daily` (the positive half of the decision), and the spec's retention sentence is an
acceptance criterion the reviewer checks against the shipped text. The absence of a clock is
recorded as residual risk in §8, with a name and a date. **Nobody may tell a customer that
employee documents are deleted on a schedule, because they are not.**

### 082-PRIV-3 · Aadhaar: what the missing masker means for the move

**Correcting the task's premise, because it changes the answer.** The task says ALV-270
*holds* the masker. It does not — **the masker was dropped**, twice-decided: 2 Nov, §6c and
§6d of `079/00-decisions.md`. Guidance replaces it: the joiner is told to download UIDAI's
own masked Aadhaar. 079's own words, Surbhi's decision recorded against my recommendation:
*"guidance is an instruction, not a lock... §6a's rule was 'mask or refuse'; there is now
neither."*

**So, plainly: unmasked Aadhaar images will exist on submissions.** Not "may" — a joiner who
photographs their plastic card produces one, and nothing refuses it. 079 also recorded that
an **older** card's QR can carry the full twelve digits even when the print is covered.

**What that means for this slice, in one line:** the move does not create this exposure, but
it **multiplies its lifetime and its audience** — from a 30-day clock and an HR-only
submission to no clock at all and whatever audience 082-PRIV-1's count finds. That is the
whole of why 082-PRIV-1 is a gate.

**What must be true:** nothing new in code. Three statements:

1. This slice adds **no masking and no inspection of the image**. It moves bytes it does not
   read. (Good: 079-SEC-8's attack surface is not re-opened — no parser runs on
   attacker-chosen pixels in this slice.)
2. No product copy, questionnaire answer or notice says a stored Aadhaar is masked. It may
   not be.
3. 082-PRIV-1's count and 082-PRIV-2's retention sentence are the mitigation. There is no
   other.

*How it is tested:* a grep-style assertion in the test suite that the words "masked",
"protected" and "secure" do not appear in this slice's strings about moved documents —
exactly the pattern `test_employee_documents_078` already uses for un-ticked types.

### 082-PRIV-4 · The joiner's photograph (OQ-3) — my answer is yes, under 078's rules

**What must be true if Surbhi says the photo moves:** it goes to the employee photo surface
built in 078, under **078's own rules and its access log**, not as a plain attachment and not
as an `Employee Document` row. It gets the same treatment a member of staff's face gets —
which `joiner_public.py:613-615` already does on the way in, re-encoding the joiner's photo
with the employee's own constants.

**If Surbhi says no:** the photo is deleted by the nightly job exactly as today, and that is
the status quo, not a regression. Either answer is safe. This is the one open question that
genuinely changes nothing about the rest of the slice.

*How it is tested:* if it moves, one test that the access log records a read of a moved
photo, reusing 078's existing log test.

---

## 7 · What must exist before any control is observable, and what I could not check

**The slice-028 lesson applies hard here.** Three of these controls read "pass" on an empty
site and prove nothing:

| Control | What must exist for it to be observable | Where it comes from |
|---|---|---|
| **082-SEC-5's move** | At least one `Employee Document Type` row, **and the `employee_documents` feature switched on**, **and** a type that applies to an employee with **no grade** — because the prefill sets no grade and `applicable_types(None, None)` returns only types with no grades and no designations (`employee_documents.py:22-41`) | `tests/fixtures_078.py` already builds types; the no-grade case must be added. **dev holds no `Employee Document` rows and no `Employee Document Type` rows at all** — `fixtures_078.py:4-5, 293-294` says so in its own words |
| **082-PRIV-1's door test** | A real moved file with a real `/private/files/...` URL, and sessions for four different logins | Fresh site, per `data-doors.md` |
| **082-SEC-1's payload test** | `Employee`'s meta, which needs `erpnext` installed | The bench, not this worktree |

**What I could not verify, and the access I would need:**

1. **`Employee.date_of_joining` is `reqd: 1`.** `erpnext` is not in this worktree. I need a
   bench, or the engineer's confirmation. *Recorded as the caller's verification of 4 Nov,
   not mine.*
2. **Who holds read on `Employee` and on `Alvoraa Position` at DTC** (082-PRIV-1). I need a
   read-only console on a restored backup, or the count run by someone with it. **I did not
   probe production and will not.**
3. **Whether HR Manager's own rights are enough to re-point a `File` and insert an
   `Employee Document` row** (082-SEC-3). `frappe` is not in this worktree. I need a bench.
4. **Frappe's exact private-file gate.** I am relying on our own traced comment at
   `employee_documents_read.py:25-38`, written by me on 1 Nov against the installed source.
   It is the best evidence I have in this worktree and it is second-hand today. **Re-trace it
   at review** — lesson 5: notes and docstrings have been wrong.
5. **I ran nothing.** No test, no bench command, no query.

---

## 8 · Residual risk

| # | Risk | Level | Who accepts it | Date |
|---|---|---|---|---|
| **R1** | **A moved identity document has no retention clock.** It is kept until somebody deletes it by hand. 082-PRIV-2 | **P1 — blocks the document half** until counsel answers in writing, or Surbhi accepts it knowingly | Surbhi, after counsel | open, 4 Nov 2026 |
| **R2** | **Anyone with read on `Employee` can fetch a moved file by URL.** No code control exists. 082-PRIV-1 | **P1 — blocks the document half** until the count is in | Surbhi, with the count | open, 4 Nov 2026 |
| **R3** | **Unmasked Aadhaar images exist on submissions** and will now be moved and kept longer. Inherited from 079 §6c/§6d, decided against my recommendation | P2 — carried forward, not new | Surbhi, 2 Nov 2026 | carried |
| **R4** | **`Employee Document` is readable through `frappe.client.get_list` by anyone with read on the parent.** Pre-existing (A4), but this slice is what puts an Aadhaar behind it | P2 — name it, own it, fix it in a slice of its own | unowned — needs a name | open, 4 Nov 2026 |
| **R5** | **No read log on a private file.** We would not learn that a colleague looked. Detection gap, not prevention | P3 | unowned | open, 4 Nov 2026 |
| **R6** | **The type is recovered from the file name** by substring match (`_sent_types`, `joiner_public.py:236-250`), and `document_type` is truncated to 40 characters on the way in (`:628`). Two types whose names contain one another, or a name over 40 characters, can attach a file to the **wrong** checklist row | P2 — an integrity fault, not a leak. One test with two overlapping type names answers it | hrms-fullstack-engineer | open, 4 Nov 2026 |

**Debt labels:** R1 and R2 are **dangerous debt — escalate now**, and they are escalated in
§9. R3 is an **intentional trade-off** already recorded. R4 and R6 are **temporary debt**;
what removes R4 is a scoped reader for `Employee Document`, and what removes R6 is a test and
a stricter match. R5 is an **acceptable simplification** for a tenant of this size.

---

## 9 · Questions, sorted

### Must know — these stop the document half

**Q1 · For counsel, in writing.** *Decision needed:* may an identity document uploaded
before joining be kept on the hired person's `Employee` record with **no retention period in
the product**, deleted only by HR by hand? *Context:* ruling 4 sets 30–60 days for a
non-joiner's document; it says nothing about a joiner's. *Conflict:* ruling 4's own logic —
an identity image goes much sooner than the record — versus the employment purpose, and
versus counsel's 18 Sep prohibition on indefinite retention. *Who is affected:* every hired
person at every tenant; at DTC, 597 staff over time. *Options:* (a) move, no clock, say so
plainly — my recommendation **for this slice**, with the clock as a named gap; (b) move, and
build an employee-document clock — a slice of its own; (c) do not move, and HR downloads by
hand before the nightly job. *Risk if it waits:* the button ships without the document half
and HR keeps losing documents — which is survivable. *Owner:* counsel, via Surbhi; add it to
the 1 Nov letter beside ALV-215. **Blocks: the document move.**

**Q2 · For Surbhi, with the count.** Does any role other than HR hold read on `Employee` —
and on `Alvoraa Position` — at DTC, and is `alvoraa_positions_document_types` empty there?
*Why it changes the control:* it decides whether moving an Aadhaar image is a filing action
or a disclosure to colleagues. *The one question:* run the count. *Fail-closed default
meanwhile:* **the document move does not ship.** **Blocks: the document move.**

### Should know

**Q3 · For Surbhi.** OQ-3, the photograph: does it move? Either answer is safe
(082-PRIV-4). *Default meanwhile:* it does not move, i.e. today's behaviour.

**Q4 · For the engineer.** Can the move be done with HR Manager's own rights, no bypass?
*Default meanwhile:* build it that way and let it fail loudly (082-SEC-3).

### Nice to know

**Q5.** Would DTC's HR rather retype than trust a prefill (the brief's OQ-5)? It changes the
Kano class, not a single control.

---

## 10 · Governance note — I must not approve my own work

I wrote 078-SEC-11 and 078-SEC-12, and 079's whole requirement set. **This document narrows
two of my own rules**, and §2's judgement that the narrowing is safe is therefore mine about
mine. **Ask the techno-functional reviewer to take a second look at §2 specifically** — in
particular at whether "no date in the payload" plus the level-2 lock really is equivalent to
the old blanket ban. I believe it is. I should not be the only one who says so.

I also recorded a **correction to the task I was given** (the masker is dropped, not held,
082-PRIV-3) and an **addition the brief did not ask for** (082-SEC-4). Both are stated
openly rather than folded in.

---

## 11 · Subtract pass — what I removed

I wrote a longer version first. Removed:

- **A new `Alvoraa Document Move Log` DocType**, to record every moved file. Deleted: the
  `File` row's own `attached_to_name` and the `Employee Document` row's `received_on` /
  `received_by` already answer "what moved, when, by whom", and `Version` answers who linked
  the Employee. A new DocType would have been a permission surface and a migration for a
  question already answered. This is why 082-SEC-5 clause 3 says *queryable state*.
- **A new `has_permission` hook on `Employee`** to guard moved files. Deleted: it would not
  fire. The private-file path never reads the hook (`employee_documents_read.py:25-38`), so
  it would be a control that reads as safe and is not — the exact failure this role exists to
  prevent.
- **A sensitivity-class field on `Employee Document Type`**, to drive masking and export
  automatically. Deleted as out of scope: the right shape, the wrong slice. It belongs with
  the employee-document clock, if that ever gets built.
- **A "confirm you have read counsel's answer" checkbox before the move.** A control nobody
  can operate. Q1 and 082-PRIV-1 are the gate; a tick box is theatre.
- **An export-logging requirement.** Already owed by 079 and deferred by Surbhi on 2 Nov. Not
  this slice's to re-open, and padding this list would bury R1 and R2.
- **Four more abuse cases** about the joiner account reaching `Employee`. 079-SEC-1 and
  079-SEC-3 already cover them; A3 is the only one this slice creates.

Count: **six SEC/PRIV requirements plus two gates**, down from eleven. The two that matter
are 082-PRIV-1 and 082-PRIV-2.
