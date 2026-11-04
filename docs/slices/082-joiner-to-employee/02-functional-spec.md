---
slice: 082-joiner-to-employee
artifact: 02-functional-spec
author: hrms-business-analyst
date: 2026-11-04
status: draft
inputs:
  - docs/slices/082-joiner-to-employee/01-product-brief.md  (read, origin/dev)
  - 01c-security-privacy-requirements.md  (NOT PRESENT when this was written — see §0)
  - 07-devops-inputs.md §3  (NOT PRESENT — see §0)
  - 01b-ux-design.md + prototype  (does not exist — see §0 and §13)
read_in_source:
  - alvoraa_portal/.../doctype/alvoraa_joiner_submission/alvoraa_joiner_submission.py + .json
  - alvoraa_portal/alvoraa_portal/public/js/alvoraa_joiner_submission.js
  - alvoraa_portal/alvoraa_portal/joiner_housekeeping.py
  - alvoraa_portal/alvoraa_portal/joiner_public.py
  - alvoraa_portal/alvoraa_portal/employee_field_rights.py
  - alvoraa_portal/alvoraa_portal/employee_documents_read.py
  - hrms/hrms/hr/doctype/employee_onboarding/employee_onboarding.py
  - hrms/hrms/alvoraa_employee_documents/employee_documents.py + setup.py + doctype/employee_document/employee_document.json
  - hrms/hrms/hooks.py
  - erpnext/setup/doctype/employee/employee.json + employee.py  (read inside hrlocal-bench)
---

# 082 · Functional spec — one button turns a joiner's submission into their personnel record

Surbhi approved building this on 4 Nov 2026: *"we need to build this without it the new joiner
form is of no use."* **Stakeholder statement**, recorded in the task.

---

## 0 · Two missing inputs, and three things in the brief that are wrong

**Missing inputs. I wrote the spec anyway; here is exactly what I could not read.**

| Input | State | What I did |
|---|---|---|
| `01c-security-privacy-requirements.md` | **Not on `origin/dev` at 2026-11-04**, and not in any worktree I can see | I use the three requirement ids the brief proposes — **082-SEC-1, 082-SEC-2, 082-SEC-3** — exactly as the brief words them (`01` §8), and carry them through to ACs. **I have not read a line of `01c`.** If the security engineer numbers them differently, or adds `082-PRIV-n`, §15 must be re-checked before build. Those three are the only security requirements this spec depends on |
| `07-devops-inputs.md` §3 `OPS` items | **Not written** | The brief recommends recording DevOps §1 as nil. §11 sets the numbers from `nfr-budget.md`. **There is no `OPS-n` row in the traceability table because none exists to trace.** If DevOps writes any, §15 needs a row each |
| `01b-ux-design.md` and a clickable prototype | **Do not exist.** The brief asks Surbhi to skip the UX scan (its OQ-4) | §13 says plainly what that costs: three pieces of wording are **open**, and prototype parity cannot be checked because there is no prototype |

**Three corrections to the brief. The first changes the shape of the slice.**

**1. The link step the brief calls "the step that exists today" does not exist today.**
`Alvoraa Joiner Submission.employee` is `"read_only": 1` in the DocType JSON, and **no code
anywhere sets it** (I grepped the whole repo: the only writers are tests). So HR cannot pick an
Employee on that form in Desk at all. **Confirmed fact.** Consequences:

- The status **"Made an employee" is unreachable through the product today.** So the brief's §0
  headline — "hiring a joiner destroys the documents, usually within 24 hours" — is **not what
  happens today**. What actually happens is the **30-day document clock**
  (`_delete_the_documents_sooner`, default `alvoraa_joiner_document_days` = 30) deletes the
  uploaded files, and the 90-day backstop erases the row. **The loss is real. The 24 hours is
  not.** The slice is still worth building; the burning-platform sentence should not be repeated
  to a customer.
- **The linking must be built in this slice.** It is not free, and it is where the ordering that
  closes ALV-306 lives (§6, US-3).

**2. "0 of 7 fields retyped" is true of the joiner's fields and misleading about the form.**
`Employee` has these mandatory fields: `first_name`, `company`, `status`, `gender`,
`date_of_birth`, `date_of_joining` (all `reqd: 1`, read in `employee.json` in the bench today —
**Confirmed fact**, which closes the brief's Risk 1 and its `[ASSUMPTION]`: `date_of_joining`
**is** mandatory, so the back-dating protection holds by itself). The prefill supplies
`first_name` and the six details. **HR still types `company`, `gender`, `date_of_birth` and
`date_of_joining`** — four fields, none of which the joiner was ever asked for. The
under-two-minutes target in `01` §12 stands; "no retyping" does not.

**3. `first_name`, `gender`, `date_of_birth` and `date_of_joining` are at field permission
level 2** (`employee_field_rights.py`, `LEVEL_2`), writable by **HR User, HR Manager, System
Manager** only. So a role with `create` on `Employee` but no level-2 write **cannot save the
prefilled form at all** — `first_name` is mandatory and locked to it. That is a good outcome, and
§8 states it rather than letting an engineer discover it.

---

## 1 · Cross-module reach

| App | Touched how |
|---|---|
| **`alvoraa_portal`** | The whole change: one prefill endpoint, one link-and-move endpoint, two buttons and two lines of copy on the existing Desk form `Alvoraa Joiner Submission` |
| **`hrms`** | **Read only.** The move writes rows in the `Employee Document` child table (an `hrms` custom field on `Employee`) through the parent's normal save, so `validate_documents` does the status work. No `hrms` file changes |
| **`erpnext`** | **Untouched.** `Employee` is read for its field names and written only by HR pressing Save on a form |
| **`frappe`** | `File` rows are re-pointed from the submission to the Employee. `Version` behaviour unchanged |
| **`alvoraa_goals`, `alvox_compensation`** | Not touched |

**HRMS domains:** org structure (a new `Employee` appears, as today), employee documents (rows
move to *Received*), pre-onboarding (status and retention). **Not** leaves, attendance, payroll,
appraisals or learning — but note the back-dating link: a wrong `date_of_joining` produces Absent
rows for every day since (DTC's logged fault), which is why no date is prefilled.

---

## 2 · Question the ask before specifying it

- **Symptom or cause?** The brief's stated problem — HR retypes seven fields and the uploaded
  documents are deleted — is a cause, not a symptom. The retyping is caused by there being no
  mapping; the deletion by a retention job with nowhere to move the files to. Both are in the code
  I read. **No re-direction needed.**
- **What happens after the screen?** Nothing here is a report or a dashboard. The two outputs are
  a form HR acts on immediately and a confirmation line. The system does **not** act on its own
  anywhere (§10).
- **Could the system act instead?** It could create the Employee automatically at hire. Surbhi
  refused that on 4 Nov: *"many joiners never turn up"*. **Stakeholder statement**, and the reason
  the transfer stays a deliberate act. Recorded here because it is the most likely thing a future
  engineer would try to "improve".

---

## 3 · Gap analysis — what already exists, verified in source

| Requirement | What the installed code does today | Verdict | Cost |
|---|---|---|---|
| Open a prefilled, **unsaved** Employee form from another record | `hrms` does exactly this: `employee_onboarding.make_employee` calls `get_mapped_doc(...)` and **returns the doc without inserting it** (`employee_onboarding.py:102-130`). **Confirmed — I read it.** But it is reachable only from an `Employee Onboarding` with a mandatory `job_applicant` Link and `docstatus == 1` (`validate_employee_creation` throws otherwise) | **Extend** — reuse the mechanism (a mapped, unsaved doc handed to the client), not the chain | S |
| The field map joiner → Employee | **Already exists**, in one place: `COLUMN_FOR_TICK` (`alvoraa_joiner_submission.py:51`), six pairs, named after `people_fields.MY_PROFILE_WRITE_FIELDS`. Inverting it is the whole map | **Already there** — invert it, never retype it | S |
| The joiner's name onto the Employee | Nothing. `full_name` is deliberately not in `COLUMN_FOR_TICK` | **Extend** — one line, `full_name` → `first_name`, whole, exactly as `make_employee` maps `employee_name` → `first_name` | S |
| A joining date that is never guessed | `Employee.date_of_joining` is `reqd: 1`, and `validate_date` enforces `date_of_birth < date_of_joining` (`employee.py:259`). **Confirmed in the bench today** | **Already there** — prefill no date and Frappe refuses the save | S |
| Link the Employee back on the submission | **Nothing. The field is read-only and nothing writes it** (§0.1) | **Build new** (code, rung 4): one whitelisted method. Justified in one sentence: no setting makes a read-only field editable-but-confirmed, and a plain editable field loses both the "name the person before you merge" guard (`01` Risk 5) and the one-transaction guarantee (FR-ORDER) | S |
| Move the uploaded files to the Employee | Nothing moves them. `delete_the_documents` deletes them, bytes included (`alvoraa_joiner_submission.py:198`) | **Build new** (same method, same transaction) | M |
| Tick the document checklist *Received* | **Already there.** `validate_documents` sets `status = "Received"` and stamps `received_on` / `received_by` the moment a row has an `attachment` and is `Pending` (`employee_documents.py:94-101`). *Verified* needs a verifier role and is never set by us | **Already there** — set `attachment` and let the parent's own validate do the rest | S |
| Work out which document type a file belongs to | **Already there.** `_sent_types` reads it from our own file name `joiner-<row>-<type>.<ext>` (`joiner_public.py:236`) | **Already there** — reuse the same matching | S |
| Status moves to *Made an employee* | **Already there.** `_follow_the_employee` does it in `validate` the moment `employee` is set | **Already there** | S |
| Close the joiner's sign-in on hire | **Already there.** `_close_the_sign_in` runs on `on_update` for any terminal status (079-SEC-5) | **Already there** | S |
| A preview of what will be copied | The unsaved Employee form **is** the preview | **Drop** | — |
| A "converted by / converted on" stamp | `tabVersion` and `status` already answer it | **Drop** | — |
| A setting for "move documents, yes/no" | — | **Drop.** One behaviour, decided once by OQ-1 | — |
| Bulk convert; per-place field choice (ALV-311); Aadhaar masking (ALV-270); the staff login | — | **Drop — out of scope**, by the task | — |

**Cost ladder: rung 4, new code.** Two endpoints and two buttons in files that already exist.
Rung 1 rejected: `Employee Onboarding` needs a `Job Applicant` and a submit. Rung 2 rejected: no
setting copies a row of one DocType onto a form of another, and none makes a read-only field
settable-with-confirmation. Rung 3 (a Client Script alone) rejected for one reason: the field map
lives in Python and a second copy in JavaScript is two lists that drift. **Rungs 5 and 6 are not
needed — no new DocType, no new field, no new app, no new setting, no new scheduled job, no new
storage.**

**Single source of truth where two models describe the same thing:**

| Thing | Source of truth | How the other stays in step |
|---|---|---|
| joiner column ↔ Employee column | `COLUMN_FOR_TICK` (`alvoraa_joiner_submission.py:51`) | the prefill endpoint **inverts it at runtime**. No second list anywhere, including the browser |
| which document type a file is | the stored file name `joiner-<row>-<type>.<ext>` | `_sent_types`' own matching is reused, not re-implemented |
| document row status | `Employee Document.status`, set by `validate_documents` on the parent's save | we set only `attachment`; never `status`, `received_on` or `received_by` ourselves |

---

## 4 · Process flow, in HR's words

**Sunny day**

1. HR opens the joiner's submission in Desk. Status is *Submitted*. They read what the person sent.
2. HR presses **"Make their employee record"**.
3. A new Employee form opens, already filled with the person's name and their six details.
   **Nothing has been saved.** A line next to the button already told them the joining date is not
   filled in.
4. HR types the joining date, the date of birth, gender and company, checks the rest, presses
   **Save**. Frappe creates the Employee under HR's own permission. *(Decision point: if HR leaves
   the joining date blank, Frappe refuses the save. That is the protection.)*
5. HR goes back to the submission and presses **"Link this employee and move the documents"**.
6. They are asked which Employee, and shown the name they are about to merge into. They confirm.
7. In one step: the Employee is linked, the uploaded files move onto the Employee record, the
   matching checklist rows read **Received**, the status becomes *Made an employee*, and the
   joiner's sign-in closes.
8. A green line says what moved, with real counts.

**Unhappy paths, all specified in §12**

- HR abandons the form at step 4 → nothing exists, the submission is untouched.
- HR presses the link button twice → the second press refuses and moves nothing.
- The joiner uploaded nothing → it links and says "no documents".
- A document type was deleted, or does not apply to this employee → the file still moves, as a
  plain attachment, and the message says so. Nothing is dropped silently.
- HR picks the wrong Employee → the confirmation names the person before anything is written.
- The move fails half way → nothing is written at all (one transaction).
- A joiner, a plain staff login or a line manager calls either endpoint → refused.

---

## 5 · Data model

**No new DocType. No new field. No new setting. No change to any DocType JSON.**

For each thing a new field might have carried, why no field is needed:

| Thing | Why no new field |
|---|---|
| "converted on / by" | `tabVersion` on the submission records the save; `status` and `closed_on` already exist |
| which Employee it became | `Alvoraa Joiner Submission.employee` already exists (read-only Link) |
| which files moved | the `File` rows' own `attached_to_doctype` / `attached_to_name` are the record |
| that a document was received | `Employee Document.status`, `received_on`, `received_by` already exist |

**Fields read by the prefill** (the inverse of `COLUMN_FOR_TICK`, plus the name):

| Employee fieldname | From submission | Employee fieldtype | permlevel | Notes |
|---|---|---|---|---|
| `first_name` | `full_name`, whole | Data, `reqd: 1` | **2** | Not split. Splitting a name in code is a guess |
| `cell_number` | `mobile` | Data | 0 | The field payslip and attendance messages use |
| `personal_email` | `personal_email` | Data | 0 | |
| `current_address` | `current_address` | Small Text | 0 | |
| `person_to_be_contacted` | `emergency_contact_name` | Data | 0 | |
| `relation` | `emergency_relation` | Data | 0 | |
| `emergency_phone_number` | `emergency_phone` | Data | 0 | |

**Never in the payload:** any `Date` field (082-SEC-1), `company`, `gender`, `designation`,
`department`, `grade`, `holiday_list`, `user_id`, anything about bank, salary, CTC or a statutory
id (the joiner is never asked: 078-PRIV-9), and `status` (Frappe's own default `Active` applies).

**Rows written by the link-and-move step:**

| Record | Written | By whose rights |
|---|---|---|
| `Alvoraa Joiner Submission` | `employee`; `status` → *Made an employee* and `closed_on` follow from the existing controller | HR's own write on the submission |
| `File` (0–6 rows) | `attached_to_doctype` = `Employee`, `attached_to_name` = the Employee. **`is_private` unchanged (1); `file_url` and `file_name` unchanged** — so the stored URL still resolves and the file is not copied | HR's own rights |
| `Employee Document` (0–6 existing *Pending* rows) | `attachment` only. `status`, `received_on`, `received_by` are then set by `validate_documents` on the parent save | HR's own write on the parent `Employee` |
| `Employee.documents_summary` | recomputed by the same validate | same |

---

## 6 · States and transitions

`Alvoraa Joiner Submission.status` — existing field, existing rules, **no new state**.

| State | Who can move it | Next | Becomes read-only | Notified |
|---|---|---|---|---|
| Invited | HR Manager / System Manager | Submitted (joiner sends), Expired (job), Cancelled (HR) | — | — |
| **Submitted** | HR Manager / System Manager | **Made an employee (this slice)**, Expired, Cancelled | — | — |
| **Made an employee** | nobody — **terminal and irreversible** (`_refuse_a_revival`) | — | in practice the whole row: `status` and `employee` are read-only fields | the joiner's sign-in is closed (079-SEC-5). **No message to the joiner** |
| Expired / Cancelled | nobody — terminal | — | — | sign-in closed |

**Reversibility: none.** Confirmed in `_refuse_a_revival`. A wrong link cannot be undone in the
product — which is why the confirmation in US-3 names the person. **Risk**, stated plainly: after a
wrong link and that night's job, the submission's own copy is erased and only the Employee record
holds the data. That is the worst outcome in the slice (`01` Risk 5) and the confirmation is the
whole mitigation. I am not proposing an undo: an undo of a merge is a second feature with its own
failure modes.

**The ordering that closes ALV-306 — safe by construction, not by timing.** The documents must move
**in the same database transaction** as the status change, because `_erase_the_redundant_copies`
erases every row in *Made an employee* on the next nightly run.

- Requirement **FR-ORDER**: the link-and-move endpoint performs the file move, the checklist write
  and the submission save in **one transaction with no `frappe.db.commit()` inside it**. If any
  part throws, the whole step rolls back: no link, no status change, no moved file.
- This is why linking is not simply "make the field editable and let HR save it": a plain field
  save could succeed while a later move failed, and the night would then erase the originals.

---

## 7 · Epic and user stories

**Epic:** one button turns a joiner's own words and their uploaded documents into their personnel
record, without copying the joining date.

Personas from `product-context.md`: **HR Manager** (their companies), **Employee** (own record),
**CXO** (all companies), plus the **line manager** named in `01` §9.

| ID | Story | Points | INVEST note |
|---|---|---|---|
| **US-1** | As an **HR Manager**, I want a button on a submitted joiner's record that opens a new, unsaved Employee form already filled with their name and their six details, so that I do not retype what they already sent. | 3 | Independent of US-3. Testable on the payload |
| **US-2** | As an **HR Manager**, I want to be told, on the form, that the joining date is not filled in and why, so that I type the real first working day. | 1 | Copy plus the existing mandatory check |
| **US-3** | As an **HR Manager**, I want one action that links the Employee I just created **and** moves the uploaded documents onto their record in the same step, so that the documents cannot be deleted between the two. | 3 | Carries FR-ORDER. Could not be split without reopening ALV-306 |
| **US-4** | As an **HR Manager**, I want one line telling me exactly what moved, with real counts, so that I know whether anything still needs chasing. | 1 | Valuable on its own; it is the WOW |
| **US-5** | As an **employee, a line manager and a joiner, I must not** be able to call the prefill or the link action, or see either button, so that nobody but HR turns a candidate into an employee or reads their details. | 2 | 082-SEC-2. Negative story |
| **US-6** | As an **HR Manager, I must not** be able to have any date filled in for me from the joiner's record, so that nobody is marked Absent for every day since a date I did not choose. | 2 | 082-SEC-1. Negative story |
| **US-7** | As an **HR Manager**, I want the documents to survive that night's retention job once they are on the Employee, so that I am not asked for an Aadhaar photo twice. | 2 | The regression this slice exists to stop |
| **US-8** | *(BLOCKED — do not build)* As an **HR Manager**, I want the joiner's photograph to move to their employee photo in the same step. | — | Blocked by OQ-3. **Not sized, not in this slice** until Surbhi and the security engineer answer |

**Total in scope: 7 stories, 14 points.** Nothing is an 8.

### YouTrack-ready table — **do not create these issues; that is Surbhi's call**

| Summary | Description | Persona | Points | ACs | Requirements |
|---|---|---|---|---|---|
| 082 Prefill a new Employee from a joiner submission | Button on a *Submitted* submission opens an unsaved Employee form filled from the inverse of `COLUMN_FOR_TICK` plus `full_name` → `first_name`. Nothing saved by the button | HR Manager | 3 | AC-1…AC-5 | 082-SEC-1, 082-SEC-2 |
| 082 Say that the joining date is not filled in | One line of guidance next to the button; Frappe's own mandatory check refuses a save without a date | HR Manager | 1 | AC-6, AC-7 | 082-SEC-1 |
| 082 Link the employee and move the documents in one step | One whitelisted method: confirm the person, set `employee`, re-point the `File` rows, set `attachment` on the matching `Employee Document` rows, save the submission. One transaction | HR Manager | 3 | AC-8…AC-15 | FR-ORDER, ALV-306, 082-SEC-3 |
| 082 Say what moved, with real counts | Green dashboard line: the details and documents that actually moved, and that the sign-in is closed | HR Manager | 1 | AC-16, AC-17 | — |
| 082 Nobody but HR may prefill or link | Both endpoints refuse a joiner session, a plain staff login and a line manager, through `/api/method`; neither button is drawn | Employee / line manager / joiner | 2 | AC-18…AC-21 | 082-SEC-2 |
| 082 No date may ever be prefilled | A test on the payload fails if any `Date` field appears | HR Manager | 2 | AC-22, AC-23 | 082-SEC-1, 082-SEC-3 |
| 082 Moved documents survive the nightly job | Hire a joiner with a file, run the job: the Employee keeps the file, the submission keeps nothing | HR Manager | 2 | AC-24, AC-25 | ALV-306 |

---

## 8 · Permission and visibility matrix

**Start from the access intent in `01` §9.** `01c` is unread, so every row here is mine and must be
re-checked against `01c` when it lands.

### Doctype level — what the installed code actually grants (Confirmed fact, read today)

| Role | `Alvoraa Joiner Submission` | `Employee` | `Employee Document` (child) |
|---|---|---|---|
| System Manager | read, write, create, delete | read, write, create, delete | follows the parent |
| HR Manager | read, write, create | read, write, create, delete (+ the only role with level-1 write) | follows the parent |
| HR User | **read only** | read, write, create, delete (level-2 write) | follows the parent |
| Employee (every staff login) | **none** | **read 1 at level 0** — scoped by User Permission only | **follows the parent** |

**The one thing an engineer must not miss.** The `employee_documents` child field is a custom field
with **no permlevel**, i.e. level 0, and `has_permission` on a child table always returns False so
it cannot be guarded at the row (ALV-256, and our 30 Oct lesson). **Therefore anyone who can read
an `Employee` row can read that row's document rows and the attachment URL, and Frappe's
private-file gate falls back to the parent's read permission with no `has_permission` hook on that
path** (traced in `employee_documents_read.py`'s own docstring). There is **no
`permission_query_conditions` on `Employee`** in either app — I grepped. So the safety of the
document move rests **entirely** on how `Employee` reads are scoped by User Permission on the
tenant. That is OQ-2, and it blocks the document move, not the button.

### This slice's two actions

| Action | May do it | Frappe door that enforces it |
|---|---|---|
| See **"Make their employee record"** | HR Manager, System Manager (and HR User, who can prefill but not link) | the form itself (no read on the submission ⇒ no form), plus the JS checks `frappe.model.can_create("Employee")` |
| Call the **prefill** endpoint | a session with **read on this submission** *and* **create on `Employee`** — checked with `frappe.has_permission` before one field is returned (082-SEC-2) | role permission on both doctypes |
| **Save** the prefilled Employee | create on `Employee` **and** level-2 write (for the mandatory `first_name`) ⇒ HR User, HR Manager, System Manager | `create` + field permission level (`employee_field_rights.py`) |
| Call **link-and-move** | **write on this submission** *and* **write on the target `Employee`** — `frappe.has_permission` on both, no `ignore_permissions` on the Employee side (082-SEC-3) | role permission on both |

**Negative cases, stated explicitly.**

| Who | Must not | What they get |
|---|---|---|
| **The joiner's own sign-in** | read any Employee, call either endpoint, see anything but their own form | HTTP 403 `PermissionError`. They hold no role that reads `Employee` or `Alvoraa Joiner Submission` |
| **A plain staff login (Employee role)** | call either endpoint; read any submission | 403. Employee role has **no permission at all** on `Alvoraa Joiner Submission` |
| **A line manager** (Employee role + a wider User Permission on `Employee`) | call either endpoint; see a candidate's address, personal email, emergency contact or identity documents | 403 on both endpoints and no button. **But** see the child-table warning above: on the `Employee` record itself, whatever they can read today they will be able to read after the move. OQ-2 |
| **CXO** | see an individual submission | no permission on the submission doctype |
| **HR User** | link or move | 403 on link-and-move: write on the submission is HR Manager / System Manager only. **HR User may prefill, not commit.** That is the existing 078/079 split and it is the right one |
| **Anybody** | mark a document *Verified* | we never set `status`; `check_can_verify` guards verification by the document type's own verifier roles |

**Row-level scoping — an existing limitation, not new scope.** `Alvoraa Joiner Submission` has
**no `company` field**, so an HR Manager of one company in a multi-company tenant sees every
company's submissions. **Confirmed fact**, inherited from 078. This slice neither widens nor fixes
it. Logged as OQ-6, not for this slice.

---

## 9 · Acceptance criteria

Every AC has an observable oracle. "Works correctly" appears nowhere.

**US-1 — the prefill**

- **AC-1** *Given* a submission with status *Submitted* and `employee` empty, *when* an HR Manager
  opens it in Desk, *then* a button labelled **"Make their employee record"** is present.
- **AC-2** *Given* a submission whose `mobile` is `9811112222`, `personal_email`
  `rakesh@example.com`, `current_address` `12 Nehru Road, Pune`, `emergency_contact_name`
  `Sunita Kumar`, `emergency_relation` `Sister`, `emergency_phone` `9822223333` and `full_name`
  `Rakesh Kumar`, *when* the prefill endpoint is called, *then* it returns exactly
  `first_name = "Rakesh Kumar"`, `cell_number = "9811112222"`,
  `personal_email = "rakesh@example.com"`, `current_address = "12 Nehru Road, Pune"`,
  `person_to_be_contacted = "Sunita Kumar"`, `relation = "Sister"`,
  `emergency_phone_number = "9822223333"` — **character for character**.
- **AC-3** *Given* the prefill endpoint has been called, *when* the test counts `Employee` rows,
  *then* the count is unchanged and
  `frappe.db.exists("Employee", {"personal_email": "rakesh@example.com"})` is falsy. **The endpoint
  creates nothing.**
- **AC-4** *Given* a submission whose status is *Invited*, *Made an employee*, *Cancelled* or
  *Expired*, **or** whose `employee` is already set, **or** whose `erased_on` is set, *when* HR
  opens it, *then* the button is **absent**; and *when* the endpoint is called anyway, *then* it
  throws `ValidationError` with a message naming the state, and returns no field.
- **AC-5** *Given* the prefill endpoint is called, *when* the returned keys are compared with the
  seven in §5, *then* they are equal as sets — no eighth key, whatever is on the submission.

**US-2 — the joining date**

- **AC-6** *Given* a submission with status *Submitted*, *when* HR opens it, *then* the form shows
  the line **"It will not fill in the joining date. Type the real first working day — a date in the
  past marks them absent for every day since."** (exact copy; **wording open**, see §13).
- **AC-7** *Given* the prefilled Employee form with `date_of_joining` empty, *when* HR presses Save,
  *then* Frappe refuses with a mandatory-field error naming **Date of Joining** and no `Employee`
  row is created. *(Oracle: `frappe.exceptions.MandatoryError`.)*

**US-3 — link and move, one step**

- **AC-8** *Given* HR presses **"Link this employee and move the documents"** and picks Employee
  `HR-EMP-00123` whose `employee_name` is `Rakesh Kumar`, *then* before anything is written they
  are shown a confirmation naming **Rakesh Kumar** and `HR-EMP-00123`; and *when* they dismiss it,
  *then* the submission's `employee` is still empty and its `status` is still *Submitted*.
- **AC-9** *Given* a *Submitted* submission with three uploaded files
  (`joiner-<row>-Aadhaar.jpg`, `joiner-<row>-PAN.jpg`, `joiner-<row>-Bank Passbook.jpg`) and an
  Employee with *Pending* checklist rows for all three types, *when* HR confirms the link, *then*
  **all of the following hold**: the submission's `employee` is that Employee; its `status` is
  *Made an employee*; `closed_on` is set; **zero** `File` rows remain with
  `attached_to_doctype = "Alvoraa Joiner Submission"`; three `File` rows have
  `attached_to_doctype = "Employee"` and `attached_to_name` = that Employee, each with
  `is_private = 1` and an unchanged `file_url`; the three `Employee Document` rows have
  `status = "Received"`, a non-empty `attachment`, `received_on` = today and `received_by` = the HR
  user; and `Employee.documents_summary` contains `3 received`.
- **AC-10** *Given* the same setup but the checklist write is made to fail (the parent save
  throws), *when* the action runs, *then* **nothing** is written: the submission's `employee` is
  empty, `status` is *Submitted*, and all three `File` rows are still attached to the submission.
- **AC-11** *Given* a submission already linked to an Employee, *when* HR calls link-and-move again
  with the same or a different Employee, *then* it throws `ValidationError` saying the record is
  already linked and naming the linked Employee, and **no file moves and no row changes** —
  including on the Employee named in the second call.
- **AC-12** *Given* a *Submitted* submission with **no uploaded files**, *when* HR confirms the
  link, *then* `employee` is set, `status` is *Made an employee*, no `Employee Document` row
  changes, and the message says **"no documents"** rather than a count of zero dressed as a tick.
- **AC-13** *Given* a file named `joiner-<row>-Aadhaar.jpg` and **no** `Employee Document Type`
  called `Aadhaar` any more (deleted since the upload), *when* HR confirms, *then* the `File` row
  still moves to the Employee, no `Employee Document` row is created, and the message names it as
  **not on the checklist**. Nothing is dropped silently.
- **AC-14** *Given* a file whose type exists but whose `Employee Document Type` is restricted to a
  grade, and an Employee with no grade (so `applicable_types` produced no row for it — confirmed
  behaviour), *then* the same as AC-13: the file moves, nothing is ticked, the message says one is
  not on the checklist.
- **AC-15** *Given* any file moved by this action, *when* its `Employee Document` row is read,
  *then* `status` is `"Received"` — never `"Verified"` — and `verified_on` and `verified_by` are
  empty.

**US-4 — what moved**

- **AC-16** *Given* AC-9's setup, *when* the action finishes, *then* the form shows a green line
  containing the person's name, **"6 details"**, **"3 documents"** and the words **"sign-in is
  closed"**. The counts are computed from what moved, never a fixed string.
- **AC-17** *Given* AC-13's setup (one of three not on the checklist), *then* the line reads
  **"3 documents, 1 not on the checklist"**. It never claims a tick that does not exist.

**US-5 — who must not (082-SEC-2). Each of these is tested through `/api/method` as a real HTTP
request, not a unit call, on a freshly created site.**

- **AC-18** *Given* a joiner's own sign-in session, *when* it POSTs to the prefill endpoint with its
  own submission name, *then* HTTP 403 and the body carries no joiner field.
- **AC-19** *Given* a plain staff login (Employee role only), *when* it POSTs to the prefill
  endpoint and to link-and-move with a real submission name, *then* 403 both times, and the
  submission is unchanged afterwards.
- **AC-20** *Given* a line manager login (Employee role plus a User Permission covering their
  team), *when* it calls both endpoints, *then* 403 both times; and *when* it opens the submission
  by URL, *then* Frappe refuses the document itself.
- **AC-21** *Given* an **HR User** session (read-only on the submission), *when* it calls
  link-and-move, *then* 403 and the submission is unchanged. *(The prefill is allowed to them —
  §8.)*

**US-6 — no date, ever (082-SEC-1)**

- **AC-22** *Given* the prefill endpoint's returned payload, *when* every key is looked up in
  `Employee`'s meta, *then* **no key has fieldtype `Date` or `Datetime`**, and in particular
  `date_of_joining` and `date_of_birth` are absent. **This test must fail if anyone adds one.**
- **AC-23** *Given* the whole slice's diff, *when* the `ignore_permissions` count in
  `test_portal_security_010` is run, *then* it is **unchanged** from before the slice (082-SEC-3) —
  the move runs with HR's own rights.

**US-7 — the documents survive (ALV-306)**

- **AC-24** *Given* a submission linked by this action today with one moved file, *when*
  `joiner_housekeeping.daily()` runs, *then* the submission's seven joiner fields are empty,
  `erased_on` is set and it has **zero** `File` rows — **and** the Employee still has its `File`
  row and its *Received* checklist row with the attachment readable.
- **AC-25** *Given* a submission **not** linked, aged past `alvoraa_joiner_document_days`, *when*
  the job runs, *then* its files are deleted as today. **Unchanged behaviour** — this slice extends
  no retention clock.

**25 acceptance criteria.**

---

## 10 · Decision automation

**No decision about a person is automated or influenced by this slice.** Every write follows a
human pressing a button on a record they are looking at, and the one judgement in the area —
whether a document is genuine — stays with the verifier role (*Received*, never *Verified*). The
accountable human is the HR Manager who confirms. There is **no AI anywhere in this slice**, so
§14.7 is nil and none of the prohibitions is engaged.

---

## 11 · Non-functional requirements for this slice

From `nfr-budget.md`, made specific. **`07` §3 does not exist, so there is no `OPS-n` to carry.**

| Dimension | Number for this slice | Why it is safe |
|---|---|---|
| Record volume | a handful of submissions a week per tenant. **Not** a bulk path | no pagination, no job, no queue |
| Files per action | **at most 6** (`MAX_FILES_PER_JOINER = 6`), **at most 5 MB each and 20 MB in total** (`MAX_FILE_BYTES`, `MAX_BYTES_PER_JOINER`) — confirmed constants | worst case: 6 row updates and one parent save |
| Prefill endpoint, p95 | **≤ 500 ms** (the budget for a whitelisted call). One `get_doc` plus one meta read; **no file touched** | |
| Link-and-move, p95 | **≤ 500 ms**. Worst-case queries: 1 read of the submission, 1 of the Employee, 1 `get_all` on `File` (≤ 6 rows), 1 `get_all` on `Employee Document Type`, 1 parent save, 1 submission save | no N+1: the type list is read once for all files |
| Background work | **none.** No new scheduled job, no new queue. Explicitly rejected: a 6-row move does not need one | |
| Storage | **zero new bytes.** The files **move** (`attached_to_*` changes); nothing is copied | |
| Transaction | one. **No `frappe.db.commit()` inside the move** (FR-ORDER) | |
| Retention of the moved data | the employer's own employee-document retention. **This slice writes no number into code** | §14.5 |
| Personal / sensitive data | yes: mobile, personal email, home address, emergency contact, and **identity documents** — the sensitive end of what we hold. Protected by role permission on `Employee`, `is_private = 1` on every file, and User Permission scoping of `Employee` on the tenant | §8, OQ-2 |
| Mobile | **nothing.** Desk only; the HR Manager is on a laptop. The joiner's phone screens do not change at all | §13 |

---

## 12 · Edge cases and boundaries

Only cases that can actually happen here. What I deliberately did **not** cover is named at the
end, so the omission is visible.

| Case | Specified behaviour |
|---|---|
| **Prefill pressed twice** | Two unsaved forms open. Neither saves anything. If HR saves both, two Employees exist — **Frappe's normal duplicate problem, not ours** — and the link step then refuses the second (AC-11). No new guard: a guard would mean tracking an unsaved form |
| **Link pressed twice** | AC-11: refused, nothing moves |
| **Already linked by another session** between opening and confirming | the same refusal. The check is made inside the transaction, read from the database, not from the loaded form |
| **Two HR users confirm at the same moment** | one wins; the second reads `employee` already set inside its own transaction and refuses (AC-11). No lock needed: `employee` is written once and never cleared |
| **Document type deleted since upload** | AC-13 |
| **Type exists but does not apply to this employee** (no grade) | AC-14 |
| **Joiner uploaded nothing** | AC-12 |
| **The tenant has not bought `employee_documents`** | `fill_checklist` does nothing (`feature_enabled`), so there are no rows. The files still move as plain attachments and the message says none are on a checklist — the same path as AC-13 |
| **Back-dated joining date** | not prevented by us and **not prefilled**. HR types it, and the guidance line says what a past date does. `validate_date` also refuses a date before the date of birth |
| **Mid-period joiner, probation, leaver, half-days, carry-forward, holiday lists, time zones** | no behaviour here depends on a period or a calendar. Out of reach of this slice |
| **Re-hired employee** | HR links the submission to the **existing** Employee. It works: files move onto that record, and **a checklist row whose status is `Verified` is skipped** — the file still moves and is reported as not ticked, so an earlier verification is never overwritten |
| **A file whose name no longer matches our convention** (hand-uploaded in Desk) | it still moves; it ticks nothing; it is counted in "not on the checklist" |
| **Multi-company** | the submission carries no company, so HR picks the Employee and the Employee carries the company. No cross-company check is possible on the submission side — §8, OQ-6 |
| **An employee with no manager, or a circular reporting line** | not touched; the prefill sets no `reports_to` |
| **Erased submission** (`erased_on` set) | the button is hidden and the endpoint refuses (AC-4). Prefilling from an erased row would look like data loss rather than deletion |
| **Legal hold on** | unaffected. Hold stops erasure, not linking |
| **Bulk import, cancelled or amended documents** | not applicable: nothing submittable here, and bulk convert is out of scope |

**Deliberately not covered:** an undo of a wrong link (§6 — a second feature), a duplicate-Employee
check (Frappe's, not ours), and anything about the staff login (out of scope by the task).

---

## 13 · There is no prototype — and these words are therefore open

**Prototype parity is a standing rule here** (Surbhi, 21 Oct 2026: build every feature in the
approved prototype exactly as drawn). **This slice has no prototype and no `01b`.** The brief asks
Surbhi to skip the UX scan. So:

- **There is nothing to check parity against.** The parity table a spec normally carries is
  **empty, by cause**, and I say so rather than leaving a blank.
- **Three wording decisions are open.** I have written the brief's words into the ACs so the
  engineer has something exact to build, but **they are the product manager's draft, not an
  approved design**: the button label *"Make their employee record"*, the joining-date guidance in
  AC-6, and the confirmation line in AC-16/AC-17. **Owner: Surbhi** (one line each). They block
  nothing — a label change is a one-line edit.
- **One interaction is my own invention and needs her yes:** the second button *"Link this employee
  and move the documents"* with a confirmation naming the person. The brief assumed HR could
  already pick the Employee on the form; they cannot (§0.1). **Owner: Surbhi.** My recommendation:
  keep the button and the confirmation rather than making `employee` an ordinary editable field,
  because the confirmation is the only guard against `01` Risk 5 and a field save cannot carry
  FR-ORDER safely.

**Localisation and accessibility.** Every string goes through `__()` / `_()`. Dates render through
`frappe.datetime.str_to_user`, so the Indian format follows the site. Desk is the surface, so
screen-reader behaviour is Frappe's own. **No frontline or mobile user sees any of this** — the
joiner's phone screens do not change at all.

---

## 14 · Compliance-impact sub-analysis

**I am not a lawyer. Nothing below is a legal ruling.** Built on `01` §10 and the 29 Oct and 1 Nov
counsel notes as recorded. `01c` is unread.

### 1 · Data touched

| Field / object | Sensitivity | Purpose collected for | Lawful basis (as recorded) | New collection? |
|---|---|---|---|---|
| `mobile`, `personal_email`, `current_address` | internal / personal | reaching a new joiner; payslip and attendance messages | employment, as recorded in the employer's own joiner notice (078-PRIV-8) | **No** |
| `emergency_contact_name`, `emergency_relation`, `emergency_phone` | **sensitive** (a third party's number) | emergencies | same | **No** |
| `full_name` | internal | identity | same | **No** |
| Uploaded identity documents (`File`, ≤ 6) | **statutory-id / sensitive** | proving identity before joining | same | **No** |
| `Employee Document` rows | internal | the employer's own document checklist | employment | **No** |

**Nothing new is collected.** No field is added anywhere. Data minimisation: the payload is a
closed allow-list of seven keys (AC-5), with no date, bank, salary or statutory field in it.

### 2 · Obligations engaged

| Obligation | Source | What this slice must do | Feature that does it |
|---|---|---|---|
| Purpose limitation when data moves between purposes | DPDP 2023, via `security-compliance-baseline.md` | a candidate's document becomes an employee's document only on a human act, with the employer's own checklist as its home | US-3; **OQ-1 must be answered first** |
| No indefinite retention | counsel, 18 Sep 2026 (recorded) | the moved file falls under the employer's employee-document retention, not a new clock of ours | §14.5; **no number in code** |
| Accuracy | DPDP | the joiner's own words reach the record unchanged, character for character | AC-2 |
| Access control over sensitive documents | counsel, 1 Nov 2026: passport and health are not for managers | **unresolved on the Employee side** | **OQ-2 blocks the document move** |
| Access review before widening visibility | ALV-249 and `data-doors.md` | a read-only count on the real tenant **before** the move ships | OQ-2 |
| Already specified elsewhere — do not respecify | `compliance-feature-map.md`, 078/079 | the joiner notice, the two clocks, legal hold, export, purge, the `Version` sweep | shipped in 079 |

### 3 · Visibility delta — **the most important section of this spec**

**After this slice, an identity document the joiner sent moves from a record only HR Manager and
System Manager can read (`Alvoraa Joiner Submission`) onto a record the `Employee` role can read at
level 0.** Confirmed from the permission tables I read today.

- **What actually limits it:** `Employee` reads are scoped by **User Permission** on the tenant
  (DTC's pattern, 26 Oct). There is **no `permission_query_conditions` on `Employee`** in either
  app. So on a tenant where any login holds a wide User Permission on `Employee`, that login gains
  the ability to read these documents.
- **The child table cannot carry the guard** (ALV-256 / 30 Oct). The guard is the parent's read.
- **Negative cases that must stay true:** a plain staff login reads only their own Employee row; a
  line manager must not read a colleague's identity documents; a CXO reads summaries, not a
  person's documents; no outside party reads anything.
- **Therefore: the document move must not ship until OQ-2's read-only count on DTC is in.** The
  button half (US-1, US-2, US-4 in part, US-5, US-6) adds **no** visibility delta and can ship on
  its own.

### 4 · Decision automation

**None.** See §10. The system never decides who becomes an employee; HR presses Save. The employee
is told nothing new by this slice, and nothing to contest arises from it.

### 5 · Retention and deletion

| What | Kept how long | On whose instruction | Survives an erasure request? |
|---|---|---|---|
| The moved `File` rows on the Employee | the employer's own employee-document retention. **This slice writes no number** | the customer (Data Fiduciary) | treated as an employment record; counsel's 18 Sep periods apply, not the 30-day joiner clock |
| The submission's own copy | erased on the next nightly run after *Made an employee* — **unchanged, existing behaviour** | the customer's settings | no |
| `Employee Document.received_on` / `received_by` | with the Employee record | | **decision-bearing** — it records who accepted a document, and survives |
| `Version` on the submission | swept at erasure (079-PRIV-2) — unchanged | | no |

**What changes:** the file crosses from the 30-day joiner clock to the employer's own employee
retention. **That crossing is the compliance event in this slice**, and it is OQ-1.

### 6 · ⚠ Open compliance questions

| Question | Who must decide | What it blocks |
|---|---|---|
| **OQ-1** May an identity document move from the joiner record to the Employee record, leaving the 30-day joiner clock? | **Surbhi, after counsel** | US-3's document half and US-7. **Not** US-1, US-2, US-5, US-6 |
| **OQ-2** Which logins at DTC hold read on `Employee`, and how wide is each User Permission? (read-only count) | **Surbhi + the security engineer** | the same half as OQ-1 |
| **OQ-3** Does the joiner's photograph move too, under 078's photo access-log rules? | **Surbhi + the security engineer** | US-8 only, which is not in this slice |

### 7 · AI features

**None. No AI, no model, no inference, no suggestion.** None of the prohibited capabilities is
engaged: nothing here sets a rating, infers emotion or a face, monitors behaviour, or surveils an
individual.

---

## 15 · Traceability

| Source | ID or line | Story | Acceptance criteria | Status |
|---|---|---|---|---|
| Brief | §7.1 button on a *Submitted* submission, unsaved Employee form | US-1 | AC-1, AC-2, AC-3, AC-4, AC-5 | covered |
| Brief | §7.2 "no date of any kind in the prefill" | US-6 | AC-22 | covered |
| Brief | §7.3 the line about the joining date | US-2 | AC-6, AC-7 | covered |
| Brief | §7.4 the files move; matching rows *Received* | US-3 | AC-9, AC-13, AC-14, AC-15 | covered |
| Brief | §7.5 the green line with real counts | US-4 | AC-16, AC-17 | covered |
| Brief | §7.6 a test that fails if a date appears in the payload | US-6 | AC-22 | covered |
| Brief | §7.7 hire a joiner with a file, run the nightly job | US-7 | AC-24, AC-25 | covered |
| Brief | §3a "HR's own Save is the only writer" | US-1 | AC-3, AC-7 | covered |
| Brief | §3 "we will not mark a document Verified" | US-3 | AC-15 | covered |
| Brief | Risk 3 the checklist row may not exist | US-3 | AC-13, AC-14, AC-17 | covered |
| Brief | Risk 4 HR abandons the form | US-1 | AC-3 | covered |
| Brief | Risk 5 show the name before merging | US-3 | AC-8 | covered |
| Brief | Risk 1 `date_of_joining` mandatory | US-2 | AC-7 | **closed as a Confirmed fact** (§0.2) |
| Task | ALV-306 ordering, safe by construction | US-3, US-7 | AC-9, AC-10, AC-24 | covered (FR-ORDER) |
| Task | pressed twice / already linked / type deleted / nothing uploaded | US-3 | AC-11, AC-12, AC-13 | covered |
| Task | who may press it; a person without `create` on Employee | US-5 | AC-18, AC-19, AC-20, AC-21 | covered |
| Security | **082-SEC-1** no code writes `date_of_joining`; no joiner value reaches it | US-6 | AC-22 | covered — **from `01` §8; `01c` unread** |
| Security | **082-SEC-2** nothing a joiner reaches creates, reads or writes an Employee; the endpoint is HR-only | US-5 | AC-18, AC-19, AC-20, AC-21 | covered — **`01c` unread** |
| Security | **082-SEC-3** no `ignore_permissions` on the Employee side | US-6 | AC-23 | covered — **`01c` unread** |
| Security | **078-SEC-12** as written ("no code path creates an Employee from a submission") | — | — | **superseded by 082-SEC-1/2/3 on the brief's recommendation. Surbhi's decision needed — OQ-4.** It is not mine to retire |
| Privacy | 079-PRIV-2 the `Version` sweep and the two clocks | US-7 | AC-24 | unchanged behaviour, re-proved |
| Privacy | 078-PRIV-9 no bank, salary, CTC or statutory field | US-1 | AC-5 | covered |
| Privacy | 079-SEC-5 the sign-in closes on a terminal status | US-4 | AC-16 | unchanged behaviour, re-proved |
| Prototype | **none exists** | — | — | **gap, by cause.** §13 names the three open wordings |
| DevOps | **no `07` §3, so no `OPS-n`** | — | — | **gap, by cause.** §11 sets the numbers from `nfr-budget.md` instead |
| Out of scope | ALV-311, ALV-270, the staff login, bulk convert | — | — | **not adopted — the user's instruction, 4 Nov 2026** |
| Brief | OQ-3 the photograph | US-8 | — | **not built. Blocked on Surbhi + security** |

---

## 16 · Data migration / backfill

**Almost nothing, and this is the whole of it.**

- **No schema change, so no migration.** No new field, no new DocType, no new setting, no patch.
- **No existing row needs defaulting or recomputing.** No submission can be in *Made an employee*
  through the product today (§0.1), so there is no half-converted state to repair. **Needs
  validation:** a one-line read-only count at DTC before build, in case one was set by API.
- **What cannot be recovered, said plainly:** submissions whose files were already deleted by the
  30-day document clock are **gone, bytes included**. This slice cannot bring them back. HR must
  ask those people again.
- **Rollback:** remove the two buttons and the two endpoints. Any submission already linked keeps
  its link and its moved files, and the files stay on the Employee. **Nothing needs undoing** — a
  consequence of adding no field and no state.

---

## 17 · Notifications and messages

**No new notification, no email, no toast beyond the on-form lines.**

| Message | Trigger | Recipient | Exact copy | Must never leak |
|---|---|---|---|---|
| The joining-date guidance | opening a *Submitted* submission | HR only | AC-6's line (**wording open**) | nothing personal is in it |
| The confirmation before linking | pressing link-and-move | HR only | names the Employee id and the employee name (AC-8) | — |
| The green "what moved" line | a successful link | HR only | AC-16 / AC-17 (**wording open**) | **counts and the person's own name only — never a document type, never a file name, never a number off a document** |
| *(existing, unchanged)* "Identity documents on a joiner invite were deleted" | the 30-day clock | whoever invited them | as shipped | already names the reference, not the person |

**Nothing is sent to the joiner.** Their staff login arriving is that message, and it belongs to
079. **Nothing is sent to a manager.**

---

## 18 · Audit and traceability for an audit a year later

| Question | Answered by |
|---|---|
| Who turned this candidate into an employee, and when? | the submission's `tabVersion` row for the save that set `employee`, plus `closed_on`; and the `Employee`'s own `owner` and `creation` |
| Which Employee did it become? | `Alvoraa Joiner Submission.employee` — the shell survives erasure deliberately |
| Who accepted which document, and when? | `Employee Document.received_by` / `received_on` (**decision-bearing; survives an erasure request**) |
| Was it ever verified, and by whom? | `verified_by` / `verified_on` — never set by this slice |
| Did the files move or were they copied? | the `File` row's own `attached_to_doctype` / `attached_to_name`; there is only ever one row per file |

**No new audit field.** Adding one was rejected: `tabVersion` and the existing stamps answer every
question above.

---

## 19 · Open questions

| # | Question | Owner | Blocks | My recommendation |
|---|---|---|---|---|
| **OQ-1** | May the identity documents move to the Employee record? | **Surbhi, after counsel** | US-3's document half and US-7. **US-1, US-2, US-4, US-5, US-6 can be built today** | Yes, move them. A person who has joined is a different purpose from a candidate. I am not a lawyer |
| **OQ-2** | Which logins at DTC hold read on `Employee`, and how wide is each User Permission? | **Surbhi + security engineer** (read-only count) | the same half as OQ-1 | Assume a wide one exists until counted. Hold the document move; ship the button |
| **OQ-3** | Does the photograph move (US-8)? | Surbhi + security engineer | US-8 only — **not in this slice** | Later, under 078's photo rules, not bolted on here |
| **OQ-4** | Is **078-SEC-12** formally replaced by 082-SEC-1/2/3? | **Surbhi** | nothing on day one, but the security review will fail this slice against 078-SEC-12 as written if it is not recorded | Replace it. The old rule banned everything to protect one date; the new three protect the date by name |
| **OQ-5** | Is a second button plus a confirmation the right shape for linking, given that the field is read-only and nothing sets it today? | **Surbhi** | the shape of US-3, not whether it is built | Keep the button and the confirmation. A plain editable field cannot carry FR-ORDER safely |
| **OQ-6** | `Alvoraa Joiner Submission` has no company field, so an HR Manager sees every company's submissions in a multi-company tenant | Surbhi | **nothing in this slice** — existing 078 behaviour, not widened here | Log it as its own ticket |

**Nice to know, not asked:** whether DTC's HR would rather retype than trust a prefill (`01`
OQ-5). It would reclassify the Kano, not change a requirement here.

---

## 20 · Assumptions

- `[ASSUMPTION]` The three security ids I depend on are numbered **082-SEC-1, 082-SEC-2,
  082-SEC-3** as the brief words them. **`01c` was not written when this spec was.**
- `[ASSUMPTION]` The file-name convention `joiner-<row>-<type>.<ext>` is reliable enough to recover
  the document type. It is our own naming and `_sent_types` already depends on it. A file that does
  not match simply moves without a tick (AC-13), so the assumption fails safely.
- `[ASSUMPTION]` The joiner's full name may go whole into `first_name`, as `make_employee` does
  with `employee_name`. HR can split it on the form. **We do not split names in code.**
- `[ASSUMPTION]` Re-pointing a `File` row does not change `file_url`, so an already-issued URL still
  resolves and no byte is copied. **Needs validation** by the engineer in the bench: change
  `attached_to_name` on a private `File` and confirm the URL still serves and permission now
  follows the Employee.
- `[ASSUMPTION]` Both endpoints stay inside the 500 ms budget. Evidence that would confirm it: a
  timed call with six 5 MB files on the local bench. No file bytes are read, so the risk is low.
- `[ASSUMPTION]` DTC has no submission currently in *Made an employee*. **Needs validation** — a
  read-only count before build (§16).

---

## 21 · Subtract pass

Read once more asking only *what can I delete and still meet the requirement?* What I removed:

- **An "undo the link" action.** Terminal is terminal (`_refuse_a_revival`), and an undo of a merge
  is a second feature with its own failure modes. The confirmation naming the person is the
  mitigation.
- **A duplicate-Employee check** before the prefill. Frappe's own problem, not this slice's, and a
  check on an unsaved form is a guess.
- **A story for "the button is hidden in the wrong state".** It is AC-4 of US-1, not a story.
- **A story for the edge cases.** They are ACs on the stories they belong to; an edge case is not
  independently valuable.
- **An `082-OPS` numbering of my own** for the NFR table. Inventing ids DevOps has not written
  would create a second list that drifts; §11 states the numbers and names `nfr-budget.md`.
- **A "needs attention" indicator** on the submission list for unlinked submissions. Nobody asked,
  and the 75-day warning already exists.
- **The photograph.** Moved out of the slice into US-8 and left unsized, because OQ-3 is open and
  078's photo surface has its own access-log rules.
- **A field-level rule for identity documents on `Employee`** that I had begun drafting under §8.
  It is a real need, but it is **not this slice** — it is what OQ-2 may create, and specifying it
  here would be me deciding a question Surbhi owns.

---

## 22 · Ready check — Definition of Ready

**The slice is NOT fully ready. Three boxes fail, and two of them are inputs that do not exist.**

| Box | State |
|---|---|
| Brief: one persona, one outcome, JTBD, competitive analysis, Kano, WOW, out of scope, **user approved** | ✅ all present; Surbhi approved on 4 Nov |
| Design: a clickable prototype reviewed at the design check; `ux-learnings.md` updated; every state designed | ❌ **FAILS — no `01b` and no prototype.** By cause (the brief's OQ-4); §13 says what it costs. Surbhi is asked to confirm the skip |
| `01c` written, with numbered `SEC` and `PRIV` | ❌ **FAILS — not written.** The spec names the three ids it depends on and they are traceable, but nobody has threat-modelled this yet |
| `07` §1–3 with numbered `OPS` | ❌ **FAILS — not written.** §11 sets the numbers from the budget instead |
| Gap analysis against what Frappe HR **actually** ships, verified in source | ✅ §3, every row read in the installed code |
| Stories: named personas, INVEST, sized, "must not" stories | ✅ 7 stories, 14 points, two negative stories |
| Every story has a Given/When/Then AC with an observable oracle | ✅ 25 ACs |
| Traceability complete; anything not adopted shows the user's decision | ✅ §15, including the two gaps named by cause |
| Permission matrix with the negative cases | ✅ §8 — and it found the child-table exposure |
| Edge cases listed | ✅ §12 |
| NFR numbers pulled from the budget and made specific | ✅ §11 |
| Migration/backfill stated | ✅ §16 |
| Compliance sub-analysis present | ✅ §14 |
| Every ⚠ COMPLIANCE question names a human and what it blocks | ✅ §14.6 |
| Nothing requires a prohibited capability | ✅ no AI at all |
| Open questions have owners, **and none blocks the first day of work** | ⚠️ **partly.** OQ-1 and OQ-2 block the **document half** of US-3 and all of US-7. US-1, US-2, US-4, US-5 and US-6 — the button, the guidance, the counts, the refusals and the no-date test — are unblocked and are a sensible first day |

**Plainly: build the button half now if Surbhi wants to start. Do not build the document move until
OQ-1 (counsel) and OQ-2 (the DTC count) are answered** — that is the half that moves identity
documents onto a record a wider set of logins can read.

**The three closing questions**

- **The human test.** If I were DTC's HR doing this every week: yes, it helps. Two presses instead
  of reading one screen and typing into another, and I stop ringing people for an Aadhaar photo they
  already sent. It is not more screens for the same work — it is the same screen with less typing.
- **The AI test.** No AI anywhere, and none would help: a map and a mandatory field do this exactly,
  every time, for nothing.
- **The automation test.** We are automating a **good** process: a human reads, a human decides the
  date, a human confirms the person. The one thing the machine does is copy characters, which is
  the part a human does worst.
