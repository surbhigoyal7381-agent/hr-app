# 081 · Security and privacy requirements — a bill on a claim, evidence on a day-fix

**Security & privacy engineer · 3 November 2026 · for the business analyst, before the spec**

Inputs read in full: `01-product-brief.md`, `01a-ux-opportunities.md` (scanned),
`01b-ux-design.md`, `07-devops-inputs.md`, the prototype's state list.
**Every product decision in the brief and the design is settled. Nothing below reopens one.**
Where I disagree with a *claim about a protection*, I say so and change the claim, not the
decision.

**Labels used throughout:** **Verified in code** (file and line read) · **Verified by running
it** (I executed it and read the output) · **Inference** · `[ASSUMPTION]` · **Unknown — I
could not check that** · **Worry** (in its own list, §13) · **Obligation** (source + date
checked).

---

## 0 · The answer first — three sentences, then the one that matters

1. **The retention question (D6) is answered and needs no new counsel letter.** A bill is a
   third category counsel has not yet been asked about, and it does not need to be: it is a
   **statutory accounting voucher**, and the law sets the floor — **eight financial years**
   (Companies Act 2013 s.128(5)), with GST's 72-month clock and an appeal/investigation
   extension inside it. A regularization file is not a financial record and takes counsel's
   performance-records clock: **employment + a strict 6-month buffer, then permanent
   erasure.** Two clocks, which is exactly the shape counsel gave us on 31 October. §4 and
   §8.
2. **The reads are logged**, reusing `Alvoraa Photo Access Log` — but the reuse is **not
   free**: the table has no field that can name a claim, and its `document_type` is a Link to
   `Employee Document Type`. Two field additions, no new DocType. §8, 081-PRIV-3.
3. **The day-fix notice is a transparency control and is specified as one.** It appears in no
   protection column anywhere in this document.

### 0.1 · And the one that matters — **the routing control does not work yet**

**P1, and it is the load-bearing control of the whole slice.**

The brief's §3.3 and §9 rest on one sentence: *"changing who the claim is addressed to changes
who can see it — including its attachment."* **That sentence is not true of the code as it
stands today.** The claim's `expense_approver` decides **our portal queue**, and nothing else.

*Verified in code:*

- `Expense Claim` has **no `permission_query_conditions` and no `has_permission` hook** in
  either app — `hrms/hrms/hooks.py:155-185` and
  `alvoraa_portal/alvoraa_portal/hooks.py:448-473`. The only row-level controls on it are
  Frappe User Permissions and DocShare.
- Every staff login carries **one Employee User Permission on its own record, with
  `apply_to_all_doctypes = 1`** — `own_record_permission.py:83-99` (the ALV-249 fix).
- `Employee` is a **nested set** keyed on `reports_to` — `is_tree: 1`,
  `nsm_parent_field: reports_to` (read from the installed ERPNext source, **verified by
  running it**).
- Frappe **extends an own-record permission to every descendant** of a nested-set doctype
  unless `hide_descendants` is ticked —
  `frappe/core/doctype/user_permission/user_permission.py:136-137`, and
  `frappe/permissions.py:396-398`. `own_record_permission.py` writes the row **without**
  `hide_descendants`, and its own docstring records that as the deliberate choice of
  31 October 2026 (D-2).
- `Expense Claim.employee` is a plain Link with no `ignore_user_permissions`
  (`expense_claim.json`), so that extended permission reaches the claim.

**The scenario, written the way a finding has to be written:** *Ramesh's line manager Sunil,
holding only `Employee` + `Employee Self Service` and his own Employee User Permission, with
Ramesh's `reports_to` pointing at him — calls `GET /api/resource/Expense Claim?filters=
[["employee","=","HR-EMP-RAMESH"]]` or `frappe.desk.reportview.get` with the same filter, for
a claim of the "Medical reimbursement" type that HR routed to a different approver role. He
gets the claim. He then reads the bill, because `File.has_permission` falls through to
`ref_doc.has_permission("read")` on the parent claim — `frappe/core/doctype/file/file.py:
1009-1024`, and the private-file route calls exactly that
(`file/utils.py:450-465` → `file.py:896`). The portal queue correctly shows him nothing. The
API, the report view, the CSV export and the link search all show him the claim.*

**So routing is a routing control, and the brief's §9 asked for it to be verified as an access
control. It cannot be, until something is built.** That something is small and is named in
081-SEC-1: **a `permission_query_conditions` + `has_permission` pair on `Expense Claim`,
limited to claim types that carry an approver role.** Rung 4 on the ladder, roughly one module
of the size of `grooming.py`'s two gates, because rungs 0-3 are all unavailable: there is no
setting, a Custom Field cannot filter a query, and the only configuration answer —
`hide_descendants` on every staff row — would reverse a decision Surbhi took on 31 October and
break every manager surface in the product.

**One piece of good news, and it corrects a note in this codebase before it misleads the next
person.** `employee_documents_read.py`'s docstring says Frappe's private-file gate "fires no
`has_permission` hook". That is true **of its own case** — the parent there is `Employee`,
which has no hook, and the product's rule lived on a child table where a hook cannot work.
It is **not** true in general, and must not be carried into this slice:
`ref_doc.has_permission("read")` → `Document.has_permission` (`frappe/model/document.py:402-414`)
→ `frappe.permissions.has_permission` → `has_controller_permissions` at
`frappe/permissions.py:239`, which is where the hook is read (`:483-499`). **Verified in code.**
**A `has_permission` hook on `Expense Claim` therefore does guard the bill on the raw
`/private/files/...` route too.** That is what makes 081-SEC-1 worth building rather than
decorative.

**If 081-SEC-1 is not built, the approver-role half of this slice must not ship.** The brief
already offers that split (§8, §16), and the attachments stand alone. Shipping the routing
without the permission pair would put a false protection in front of a medical receipt, which
is worse than today — today nobody expects routing to protect anything.

---

## 1 · Threat model, four lines

**Who wants this data, and what is the cheapest way to get it?** A colleague's line manager,
who already has a valid session and a legitimate reason to look at *attendance*, and for whom
the cheapest route is `/api/resource/Expense Claim` with a filter — not a screen. Second: HR
on Desk, who is entitled, in bulk, with export. Third: anyone who ends up holding an approver
role at a multi-company tenant. An outsider is nowhere in the top three.

**Blast radius of one mistake.** One employee per claim; **one manager's whole reporting line**
through the tree permission; **one company's staff** if the role is not company-scoped. Not
cross-tenant — nothing in this slice crosses a site boundary. The honest top of the scale here
is *one manager's team's medical and identity documents*, which is high enough.

**What does this make possible that was impossible before?** New **collection**, at volume and
of attacker-chosen bytes: every expense claim will now carry an employee-supplied file, and
some of those files will contain health data, bank details and identity numbers nobody asked
for. New **visibility**: a reviewing screen that shows another person's document. New
**outbound flow**: none — no model, no third party, no email of a file.

**How would we find out?** For a read: from the access log (081-PRIV-3), which is the only
mechanism in the product that can answer *"who opened my bill"*. For a listing: **we would
not** — Frappe keeps no record of list reads, and that is already written down in
`data-doors.md`. So prevention has to carry this, and 081-SEC-1 is that prevention.

---

## 2 · Data inventory

| Object | Sensitivity class | Purpose | Retention | Who may see it |
|---|---|---|---|---|
| **The bill** (image or PDF on an `Expense Claim`) | **High, and unbounded in content** — the field is free-form, so it inherits the worst thing an employee photographs: health, bank, an identity number. Classify at the ceiling, not the average | Justify a payment; satisfy the employer's statutory voucher duty | **Statutory**: the end of the 8th financial year after the one the claim belongs to, then permanent erasure. Legal hold wins. §4, 081-PRIV-1 | The claimant; the routed approver (role-holder, in the claim's company, Active); HR and finance in their own companies |
| **The day-fix file** (image or PDF on an `Attendance Request`) | **High** — the natural evidence for a missed punch is a doctor's note | Settle one day's attendance | **Employment + a strict 6-month buffer, then permanent erasure** (counsel, 18 Sep 2026). Never "for ever" | The person; **their own line manager, by design**; HR in their own companies |
| **File metadata** (stored name, size, type, uploader, time, parent id) | Medium. A device-supplied name can disclose on its own — `apollo-hospital-receipt.pdf` | Show the file back; audit | With its parent | See 081-PRIV-2: Frappe's own `File` list condition is wider than the parent's read, so this row is more visible than the bytes |
| **The access-log row** (who opened which file, which day) | Medium — it is a record about a reader, and it is the employee's evidence | Answer *"who looked at mine"*; the brief's ≥70% measure | Follow the parent's clock; it holds no file, no url, no content | System Manager, HR Manager (the doctype's existing rows); and the subject, about their own, through a product surface |
| **The approver role named on an `Expense Claim Type` per company** | Low in itself, **access-granting in effect** | Routing | Life of the configuration | HR/System Manager. A change to it changes who reads medical receipts — treat it as a configuration change worth a `Version` row |

**Nothing here is new personal data about a person we did not already hold.** What is new is
**volume**, **free-form content** and **a new reader**. All three are compliance events (the
brief's §10 says so, correctly).

---

## 3 · Access intent — including who must NOT see what

The analyst builds the permission matrix from this table. "Door" is the Frappe mechanism that
enforces it, not our screen.

| Actor | Expense claim + its bill | Day-fix request + its file | Door |
|---|---|---|---|
| **The claimant / requester** | read own, replace own until decided | same | own-record Employee User Permission (`own_record_permission.py`) |
| **Line manager, claim type with NO role** | read, decide | read, decide | `expense_approver` + Frappe HR's DocShare; plus the tree permission |
| **Line manager, claim type WITH a role they do not hold** | **MUST NOT see the claim or the bill, on any door** | n/a | **081-SEC-1 — does not exist yet.** Today the tree permission lets them through |
| **Role-holder, right company, Active employee** | read, decide, until someone acts | n/a | 081-SEC-1 + 081-SEC-2 |
| **Role-holder, WRONG company** | **MUST NOT see it** | n/a | 081-SEC-2, in the query. Frappe roles are not company-aware |
| **Role-holder whose employee is not Active, or whose login is disabled** | **MUST NOT see it, and must not be a route** | n/a | 081-SEC-2 (lesson 3: ERPNext does not disable a leaver's login by itself on every path) |
| **HR User / HR Manager** | read, correct, export, in their own companies and branches | same | existing role rows + Company/Branch User Permissions + `branch_scope.py`'s `alvoraa_branch` on both doctypes (**verified in code**, `branch_scope.py:22-36`) |
| **Finance** | read the claim they pay | **no** | existing role rows |
| **CXO / System Manager** | **summaries only** — the brief's §9 says "No". Today a System Manager's Home row opens the oldest individual claim (`portal.js:6538`, `:6625`, the design's AQ2). See §11 | no | decision needed, §11 |
| **A colleague who is not in the reporting line** | **nothing** | **nothing** | own-record User Permission |
| **Guest** | nothing. No public page, no token, no bearer link in this slice | nothing | no new route |

---

## 4 · Obligations engaged — and D6 answered

### 4.1 The statutory floor for expense evidence — established, cited, dated

This is the lookup the task asked for. **Checked 3 November 2026.**

| Source | What it requires | Verification level |
|---|---|---|
| **Companies Act 2013, s.128(5)** | A company shall keep its **books of account together with the vouchers relevant to any entry** for **not less than eight financial years** immediately preceding the current financial year (the whole period of existence, if shorter). A proviso lets the Central Government direct a longer period where an investigation is ordered under Chapter XIV | **Obligation.** Read two bare-act reproductions (ca2013.com; the Income Tax Department's s.128 page returned 403 to me) plus four secondary sources in agreement. **I did not read the Gazette text.** The "eight financial years" period is beyond doubt; the explicit word "vouchers" I have from reproductions and commentary, not from the Gazette |
| **CGST Act 2017, s.36** | Retain accounts and records until **72 months from the due date of furnishing the annual return** for that year; and where a person is party to an appeal, revision, proceeding or investigation, **one year after its final disposal, or the 72 months, whichever is later** | **Obligation.** Same verification level: statutory text via reproduction, proviso confirmed by two independent reproductions |
| **Income-tax Act 1961 s.44AA / Rule 6F(5)** | Books and documents kept **six years from the end of the relevant assessment year** | **Obligation**, narrower application (specified professions). Inside the 8-year floor, so it does not move it |
| **DPDP Act 2023, s.8(7)** | The Data Fiduciary must erase when the purpose is no longer served or consent is withdrawn — **unless retention is necessary for compliance with any law** | **Obligation.** Verified via commentary, not the Gazette. One further point I am **not** certain of and have marked: commentary says s.8 commences in a later phase (reported as 13 May 2027). `[ASSUMPTION]` — do not rely on the date; the retention rule we build does not depend on it |

**The floor, in one line:** **a bill must be kept until the end of the 8th financial year
after the financial year the claim belongs to, and longer while an appeal, GST proceeding or
company-law investigation touching it is live.** That last clause is our **legal hold**, and
it is the same mechanism the retention engine already needs.

**Does this conflict with anything counsel told us? No — and the reason matters.**

- **18 September 2026** ruled on **GPS and performance records**. A bill is neither.
- **31 October 2026** ruled on **identity-document images**, and gave us the two-clock shape
  precisely because an image carries more risk than a record.
- **A bill is a third category: it *is* the financial record.** The short image clock cannot
  apply, because deleting the bill destroys the evidence for the payment — the opposite of
  what the 31 October ruling was protecting. The long clock is not ours to shorten: it is the
  employer's statutory duty, and DPDP s.8(7) carves exactly this out of the erasure duty.
- **Counsel's prohibition on indefinite soft deletion is respected.** Eight financial years is
  a definite end, computed from a date on the claim, and the file is then **permanently
  erased**. Nothing we build may offer "keep for ever" — 081-PRIV-1 makes that a test.

**One place where a counsel ruling genuinely does not transfer, and I am recording it rather
than asking again.** 31 October: *mask sensitive IDs by default; restrict unmasked exports to
super-admins.* **We cannot mask the inside of a photograph.** A hotel invoice may carry a
passport number and a medical bill a patient ID, and there is no masking step for free-form
evidence — our re-encode resizes and strips metadata, it does not read the image. So for this
slice the equivalent of masking is **minimising the readers** (081-SEC-1/2) and **logging the
reads** (081-PRIV-3). **Nothing in the spec, the UI or any questionnaire answer may say or
imply that a bill is masked, redacted or protected.** That is 081-PRIV-5.

### 4.2 The other obligations this slice touches

| Obligation | Last verified | What it requires here |
|---|---|---|
| **DPDP Act 2023 + DPDP Rules 2025** — purpose limitation, minimisation, erasure, Fiduciary/Processor split | baseline §2, **24 Aug 2026** (71 days — inside the 90-day window, not re-verified today) | The employer is the Data Fiduciary and Alvora the Processor (counsel, 31 Oct). **Every retention number in this slice is a tenant setting with our cautious default**, never a hard-coded Alvora decision |
| **CERT-In directions (6-hour reporting, 180-day log residency)** | baseline §3, **24 Aug 2026** | No new obligation. This slice adds no new log pipeline, and must not: the access log is an existing DocType |
| **Counsel, 18 Sep 2026** — performance records: employment + strict 6-month buffer, then automatic permanent erasure; **no indefinite soft deletion**; access + grievance for automated decisions | relayed by Surbhi | The day-fix file's clock. No automated decision is made here, so the access/grievance limb is not engaged by this slice |
| **Counsel, 1 Nov 2026 (ALV-249)** — passport and health data are **not for managers** | relayed by Surbhi | This is the obligation 081-SEC-1 discharges. Routing without it does not discharge it |

**New-Frappe-app checklist:** **not applicable.** This slice installs no app, creates no role
by itself (the approver role is one an organisation already holds or creates in Desk), adds no
public page, no guest access and no self sign-up. Written down because the step is never
skipped.

---

## 5 · Abuse cases

| # | Actor and state | Path | What they get today | Must get |
|---|---|---|---|---|
| **A1** | **The curious line manager.** Valid session, `Employee` + `Employee Self Service`, one direct report | `/api/resource/Expense Claim` filtered on the report's employee; then the bill's `file_url` | **The routed medical claim and its bill** (§0.1) | Nothing, on every door |
| **A2** | **The over-scoped role-holder.** Holds the approver role; their own employee is in Company B | the role-scoped queue, and `reportview.get` | not built yet — must never be built without the company clause | Nothing outside their company |
| **A3** | **The departed approver.** Employee `status != Active`, login left enabled by hand | the same | `expense_approver_for` already refuses to *route* to them (`hr_api.py:2451-2466`, **verified in code**). A role-scoped queue is new code and would not inherit that | Nothing, and the role must not resolve to them |
| **A4** | **The curious colleague, no reporting line** | `/api/resource/File?filters=[["attached_to_doctype","=","Expense Claim"]]&fields=["file_name","file_url","attached_to_name"]` | **The stored name and url of every bill in the tenant.** Not the bytes — those still ask the parent. **Verified by running it**: for a login holding only `Employee`/`Desk User`, Frappe's own File condition is `is_private = 0 OR (attached_to_doctype IS NULL AND owner = me) OR attached_to_doctype IN (<every doctype I can read at all>)`, and `Expense Claim` and `Attendance Request` are both in that list (`frappe/core/doctype/file/file.py:1029-1043`) | A neutral stored name, so the index is worthless — 081-PRIV-2 |
| **A5** | **The uploader as attacker.** Any staff login; `upload_file` with `is_private=1` is reachable by all of them (DevOps OPS-12) | post an HTML file named `.jpg`; post a 200 MB body; post 500 files | Must be refused on magic bytes, refused on length **before** decode, and rate-limited | 081-SEC-4, 081-SEC-5 |
| **A6** | **The sharer.** A manager who can read a claim and holds `share` on it — `Employee` role has `share: 1` on `Expense Claim` (**verified in code**, `expense_claim.json` permissions) | share the claim with a third party; sharing a parent opens its attachments | Must be denied for a routed claim | 081-SEC-1, which covers `share` as a ptype |
| **A7** | **HR in bulk.** Entitled, but at scale | Desk report view, export | Metadata export is their job. A route that produces **copies of files** in bulk does not exist and must not be built here; if one ever is, counsel's 31 Oct "log every export" applies | 081-PRIV-3 |

---

## 6 · SEC requirements

### 081-SEC-1 · Routing becomes an access control, or the routing does not ship

**What must be true.** For an `Expense Claim` whose claim type names an approver role for the
claim's company, **read, report, print, email, export and share are denied to everyone except**:
the claimant; a holder of that role whose own Active Employee is in the claim's company; and
HR/finance roles within their existing company and branch scope. The denial lives in a
**`permission_query_conditions` + `has_permission` pair on `Expense Claim`**, registered in
`alvoraa_portal/hooks.py` beside the six pairs already there. The query half filters lists,
counts, reports and exports; the `has_permission` half guards one record at its own URL, and —
because the parent's `has_permission` hook **is** consulted by the private-file route (§0.1) —
guards the bill as well.

**Why both halves, and why not something cheaper.** The query condition alone leaves the
record readable at its own URL and leaves the file downloadable. The hook alone leaves the
list, the report and the CSV export open. The two together are the pattern this codebase
already uses for `Employee Performance Feedback` (ALV-117) and `Replacement Plan` (slice 065) —
same shape, same file, no new mechanism. **Rejected cheaper rungs:** no setting exists;
a Custom Field cannot filter a query; `hide_descendants` on every staff User Permission would
reverse Surbhi's 31 October decision that a manager sees their reports, and would change every
manager surface in the product, not just this one.

**Scope discipline.** The pair must be **inert for a claim type with no approver role** — a
fuel claim keeps today's behaviour exactly, so an untouched tenant sees no change. That is
also what keeps the hook cheap to reason about.

**How it will be tested.** As a **plain staff login and as a line manager with a direct
report, through the API, on a freshly created site** — each test failing without the hook:

1. `GET /api/resource/Expense Claim` (list), and with a filter naming the report's employee
2. `GET /api/resource/Expense Claim/<name>` (one record at its own URL)
3. `frappe.desk.reportview.get`, `get_list`, `get_count`, including the `reference_doctype`
   variant
4. `frappe.client.get`, `get_list`, `get_value` on `Expense Claim`
5. Report view **and CSV export**
6. Link search — `search_link`, `search_widget`, `validate_link_and_fetch`
7. `frappe.share.add` on the claim → refused
8. `GET /private/files/<the bill>` directly, with the url obtained as the uploader → refused
   for the excluded manager
9. The portal queue — `inbox_api._part_expense_approvals` — returns it to the role-holder and
   not to the manager
10. **`Expense Claim Detail` asked on its own** must not become the side door.
    `frappe.has_permission` on a child table answers **False for everybody** (ALV-256), so the
    guard is on the parent and the test asserts the child row is unreachable without it.
    `inbox_api.py:589-595` reads the lines with `frappe.get_all`, which checks no permissions —
    that is safe only because the parent list was already filtered, and the test must pin that
    ordering.

**What must exist for this to be observable** (lesson 1 — a rule can pass its tests and never
fire): the fixture needs **two companies**, **a claim type with a role named for company A and
nothing for company B**, **a role-holder in each company**, **a manager with a direct report**,
and **a filed claim of the routed type**. Without the routed type configured, every one of
these tests passes vacuously. The test must assert the fixture's shape first.

### 081-SEC-2 · The role resolves in the query: company, Active, and never a list of ids

**What must be true.** Wherever the role is resolved — the queue, the count, the permission
pair — the scope is composed **as filters in the query**, following
`inbox_api._with_hr_lwp` / `hr_lwp_filters` (`inbox_api.py:436-476`), never as a materialised
list of employee or claim ids. Three clauses, all three mandatory:

1. the caller holds the role named on that claim type **for that claim's company**;
2. the caller's **own Employee record is Active and in that company** — Frappe roles are not
   company-aware, so the company test is ours to make, and ERPNext does not reliably disable a
   leaver's login on every path (lesson 3);
3. a claim type whose named role **has no qualifying holder in that company refuses at
   filing**, reusing the sentence that already exists — *"Your expense claim could not be
   filed because nobody is set to approve it. Ask HR to set your approver."*
   (`hr_api.py:2408-2411`, **verified in code**). Never a claim in a queue nobody reads: an
   unreachable claim is a bill retained with no purpose.

**How it will be tested.** A role-holder in company B gets **zero rows and zero count** for a
company-A claim, through doors 1-6 of 081-SEC-1's list. A role-holder whose Employee is
`status = "Left"`, and one whose login is disabled, both get zero and are not counted as
holders. Filing against a type whose role has no qualifying holder throws the existing
message. **And one grep, written into the review** (lesson 2): every reader that touches
`Expense Claim` is listed and checked against this scope — `inbox_api._part_expense_approvals`,
`hr_api.decide_expense`, `home_people.py:52`, and any new role queue. One scoped reader with
three unscoped siblings is the failure slice 030 paid for.

### 081-SEC-3 · The mandatory rule lives on the document, at submit, and the server owns every refusal

**What must be true.** The "a claim must carry a file" rule is enforced in a **submit-time
check on `Expense Claim` itself**, so Desk, the REST API, a data import and any future caller
obey it. The portal **also** refuses at filing so the person hears it when they can act. The
message reaching `ec-error` is the server's own sentence — never a Python argument error,
never "check your connection". A draft stays saveable (the brief's §3, settled).

Security-relevant, and the only reason this is a SEC item at all: `apply_expense_claim` inserts
with `doc.insert(ignore_permissions=True)` (`hr_api.py:2446`, **verified in code**). A rule
written only inside that function is a rule inside a bypass. On the document it is not.

**How it will be tested.** Post a claim with no file to `apply_expense_claim` → the server's
sentence, asserted as a string. Build and submit an `Expense Claim` with no attachment through
`frappe.get_doc(...).submit()` and through `/api/resource/Expense Claim` → refused. Save a
draft with no attachment → **accepted**. Submit with an attachment → accepted. The test presses
the real path and asserts the payload and the refusal, not the drawing (the 28 Oct 2026
standing lesson).

### 081-SEC-4 · What we accept is decided by magic bytes, and what we store is named and typed by us

**What must be true**, reusing `employee_photo.py`'s ordered checks (`employee_photo.py:1-120`,
**verified in code**) and adding PDF:

1. **Three families only, by magic bytes** — JPEG (`FF D8 FF`), PNG (`89 PNG…`), PDF (`%PDF-`).
   Not the extension, not the browser's content type. A zip or an HTML file renamed `.jpg` is
   refused.
2. **We choose the stored file name and its extension** — generated, from the claim and a
   hash, never the device's name (this is also 081-PRIV-2's requirement, for a different
   reason).
3. **The served content type is derived from our stored name, never from anything the uploader
   supplied.** Frappe's `as_raw` sets the content type from the file name, so an accepted file
   named `x.html` would be served as HTML **from our own origin** — stored cross-site
   scripting. Magic bytes plus our own naming closes it; both clauses are needed, and a test
   must prove the pair.
4. **HEIC is refused in words, not converted.** Pillow 12.3.0 in the running image has no HEIC
   reader and `pillow_heif` is absent (DevOps OPS-11, measured). **This is my answer to the
   design's EC4 option (b): no.** Accepting HEIC unchanged means storing an
   original-resolution photograph with its GPS coordinates in it, in a format we cannot strip —
   that is new unstripped personal data to make a convenience work, and the client re-encode
   (option (a), drawn) already yields a JPEG whatever arrived. The server's refusal is the
   backstop and must read as the design's state 7.
5. **The image re-encode is the strip.** One Pillow call resizes and drops metadata; Frappe's
   own `strip_exif_metadata_from_uploaded_images` runs for `image/jpeg` only, so a PNG would
   otherwise keep its GPS (`file.py:813-819`).
6. **PDF is accepted and is the one type we cannot strip. Say that, and strip nothing you
   cannot.** No PDF parsing on the server — no page count, no text extraction, no sanitiser.
   A parser is attacker-chosen input in a library, and the design's "PDF · 2 pages" tile can be
   drawn without the server opening the file.

**How it will be tested.** A table test: a real phone JPEG (the one committed fixture,
OPS-10); a PNG with GPS EXIF, asserted stripped after re-encode; a `%PDF-` file, accepted and
byte-identical; an HTML file named `bill.jpg`, refused; a zip named `bill.pdf`, refused; a HEIC,
refused with the exact sentence; a stored file asserted to carry **our** name and extension;
and the response's content type asserted to come from our name.

### 081-SEC-5 · Size before decode, one file, a per-user limit, and the upload is bound to the caller

**What must be true.**

1. **Length checked on the encoded string before anything is decoded** — the first check in
   `employee_photo._decode` and the reason it exists: otherwise a 200 MB payload is expanded in
   a worker's memory before we refuse it. The stored caps are the settled numbers: **1 MB image
   after re-encode, 3 MB PDF.**
2. **The caps are enforced in our code, after the re-encode — not as System Settings
   `max_file_size`** (DevOps OPS-6). A site-wide 1 MB would refuse the raw 4 MB photo before we
   ever compress it and break every other attachment. Slice 078's outstanding
   "apply the per-file ceiling" item must not be closed at 1 MB.
3. **One file per document.** Not a policy, a check: a second upload replaces the first, and
   the server refuses to attach a second `File` to the same claim.
4. **A per-user rate limit on the new path**, reusing `field_app_limits._limited` with
   `SELF_KEY` exactly as `open_employee_document` does (`employee_documents_read.py`, 60/hour).
   DevOps OPS-12: `upload_file` with `is_private=1` is reachable by every logged-in staff
   member, and mandatory attachments multiply legitimate traffic, which is what makes abuse
   hard to spot. A full disk is the failure that took production down for nine days on
   10 September.
5. **The two-call shape (the design's §12.1) takes no identifier it does not check.** The
   endpoint that binds a file to a claim must resolve the claim from the caller's own employee
   record and refuse any claim that is not theirs and not in Draft; and the file must be
   **relinked, not duplicated**. Frappe's `find_file_by_url` returns the file if **any** row
   with that url is readable (`file/utils.py:450-465`, **verified in code**), so a second
   `File` row for the same bytes means the gate is satisfied by the weakest row. One row, moved.
6. **An orphan — a file uploaded for a claim that was never filed — is deleted by the
   housekeeping pass**, and starts the shorter of the two clocks, not the statutory one
   (081-PRIV-1 clause 5).

**How it will be tested.** A 200 MB string refused without a decode (asserted by patching the
decoder and proving it was never called); a 4 MB real photo accepted and stored under 1 MB; a
4 MB PDF refused with the 3 MB sentence; the 61st upload in an hour refused; posting another
employee's claim name to the bind endpoint refused and logged; two uploads to one claim leaving
exactly one `File` row; an orphan deleted by the job.

### 081-SEC-6 · One guarded endpoint streams the bytes, and nothing is called "protected"

**What must be true.** Reviewers and HR open a file through **one** whitelisted endpoint that
checks permission on the **parent document** and then streams the bytes, following
`employee_documents_read.open_employee_document` — the browser is never handed a
`/private/files/...` address, on any of the design's four callers. **No "open all", no
thumbnails in any list, no preloading** (DevOps OPS-7: the endpoint reads a whole file into one
of eight request slots). The viewer gets a blob and revokes it.

**And the honest half, stated once and never contradicted.** The guarded endpoint is **defence
in depth plus the access log**, not a boundary: a reader who already holds the url can fetch it
on Frappe's own route, where the decision is Administrator → not private → `owner == user` →
a DocShare row → **the parent's read permission**. With 081-SEC-1 built, that last step is our
hook and the answer is the same as the endpoint's. **Without 081-SEC-1 it is not.** No product
copy, spec sentence, release note or questionnaire answer may say a bill is "protected",
"secure" or "hidden" — the same rule `test_employee_documents_078` already enforces for
documents, with the same three words.

**How it will be tested.** Extend the existing word assertion to this slice's copy and spec
(the three words, about bills and day-fix files). Assert no response from any of the four
callers contains the string `/private/files/`. Assert a direct fetch of the url by an excluded
manager is refused once 081-SEC-1 exists — **this is the demonstration that proves 081-SEC-1,
and the review should not accept the slice without it.**

### 081-SEC-7 · No new `ignore_permissions`, and the new files start at zero

**What must be true.** `hr_api.py` stays at **67**; `attendance_correction.py` stays at **0**;
every new module this slice adds gets its **own entry at 0** in
`test_portal_security_010.TestSec16IgnorePermissionsCeiling.CEILINGS` (counts **verified in
code**, `test_portal_security_010.py:731-900`). 079-SEC-7 asked these numbers to go **down**;
this slice's expectation is **none added**, and a new file with no ceiling entry is the hole
slice 064 found, so the entry is part of the requirement.

If a bypass turns out to be unavoidable, the spec says which call, on which doctype, after
which check, and why no ORM path works — argued in the ceiling comment as every other entry is.
**Candidate I expect to be argued:** the access-log insert, exactly as
`employee_documents_read.py` carries **one** for the same reason (nobody holds `create` on that
doctype). One is acceptable; it is the same row, for the same purpose. Nothing else is.

**How it will be tested.** The existing gate, plus the new entries. It already counts in parsed
code rather than prose, so a comment cannot fail it.

---

## 7 · The transparency control, specified as one — not a protection

### 081-SEC-8 · The day-fix notice is present and **positioned before the file picker**

**What must be true.** The notice — *"Your manager reads this request, and will see any file
you attach. Attaching one is your choice — HR can fix the day without it."* — renders in the
day-fix form, **above the two file buttons, inside the same block**, as plain hint text, in
English and Hindi.

**What must never be true.** It must not appear in any protection column, verification table,
questionnaire answer or release note as a control over the manager. **Nothing restricts the
manager on a day-fix request, by design** (the brief's §3.4, settled). The only thing being
verified is that the person is told the truth before they choose.

**How it will be tested.** A **positional** assertion in the DOM test: the notice node's index
precedes the file input's index inside the same container, and the notice's text is
non-empty in both languages. Presence alone is not the criterion.

**The one thing that must not drift.** The notice is only honest while the attachment is
optional. **If a later slice makes it mandatory, the routing question returns** — the brief
says so, and this requirement is where it has to be re-read.

---

## 8 · PRIV requirements

### 081-PRIV-1 · Two clocks, two floors, legal hold, and never "for ever" — D6 answered

| | **The bill** (on an Expense Claim) | **The day-fix file** (on an Attendance Request) |
|---|---|---|
| Ruling applied | **Statutory voucher** — Companies Act s.128(5), §4.1. Counsel's image clock cannot apply: deleting it destroys the evidence for the payment | **Counsel, 18 Sep 2026** — performance records: duration of employment, then a **strict 6-month buffer**, then automatic permanent erasure |
| Clock starts | the **end of the financial year the claim belongs to** (from `posting_date`, never `modified` — ticking legal hold off and on restarts a `modified` clock, the lesson already written into `alvoraa_joiner_submission.py:50-58`) | the employee's **relieving date** |
| Deletes | the `File` row **and its bytes**; the claim and its ledger entries stay | the `File` row and its bytes; the request stays |
| Shipped default | **8 financial years**, as a tenant setting. We are the Processor; the employer owns the number and may only set it **longer** | **6 months after relieving**, as a tenant setting |
| Legal hold | **Wins, always.** An appeal, a GST proceeding or a company-law investigation extends it — s.36's proviso and s.128(5)'s | Wins — a live grievance about that day |
| Erasure request | **Refused for the bill, with the reason named**: DPDP s.8(7)'s carve-out for retention required by law. The refusal must say *which* law, because "we cannot delete that" with no reason is the answer that generates a complaint | Honoured once the buffer has run; before that, the purpose is live |
| "For ever" | **Never available.** No blank, no zero, no "indefinite" — a value outside the allowed range is refused, as `settings.py:381-383` already does for the joiner clocks | Same |

**Five more clauses, each of which is a real case somebody will hit:**

1. **A cancelled claim keeps its bill to the statutory clock.** A cancelled voucher is still a
   voucher, and a claim cancelled after a dispute is exactly the record that defends the
   decision. Do not delete on cancel.
2. **A leaver's claims keep their bills to the statutory clock.** The file follows the claim,
   not the person — already true of `expense_approver`. The **day-fix** files are what the
   leaver clock empties.
3. **Each pass logs its own count.** Two clocks, two counts. "Did the files actually go" must
   have an answer per pass, or the clock is a claim (079-PRIV-1's lesson, which earned itself).
4. **HR is told before a deletion**, through the `Notification Log` the existing housekeeping
   job already uses, naming the claim reference and **never the person**.
5. **The orphan clock is short and separate.** A file uploaded for a claim that was never filed
   has no purpose at all: delete it within **7 days**, by the same daily job, and do not let it
   inherit the statutory clock. This is the cost the design's two-call shape named in §12.1,
   and this is the answer to it.

**How it will be tested.** Age a claim's financial year past the 8th year end and assert the
`File` is gone and the claim is not; assert the same claim under legal hold survives; assert a
cancelled claim's bill survives to the clock; age a leaver past 6 months and assert the day-fix
file is gone; assert an orphan goes at 7 days; assert neither setting accepts 0, blank, or a
value below the shipped default; assert each pass logs its own count; assert an erasure request
against a bill inside the statutory window is refused **with the statute named in the message**.

### 081-PRIV-2 · The stored name is ours, because the `File` row is more visible than the bytes

**The exposure, verified by running it.** For a login holding `Employee` (plus `All`,
`Desk User`, `Guest`), Frappe's own `File` list condition is
`is_private = 0 OR (attached_to_doctype IS NULL AND owner = me) OR attached_to_doctype IN
(<every doctype the user can read at all>)` — and that list contains **`Expense Claim`** and
**`Attendance Request`**. I called
`frappe.core.doctype.file.file.get_permission_query_conditions(user)` for such a login on the
local dev bench and read the output. So **any staff login can list the stored name, the size
and the `file_url` of every bill and every day-fix file in the tenant**, through
`/api/resource/File` or `reportview.get`. The **bytes** are still gated by the parent
(`file.py:1009-1024`), so this is a metadata leak, not a content leak — but mandatory bills
turn it from a curiosity into a complete index.

**What must be true.** The stored file name is **generated by the server** — claim or request
reference plus a short hash plus our extension — and the device's name is never stored. The
design already draws this (`bill-03-nov.jpg`, §7.1 state 5), so this requirement agrees with
the design and makes it load-bearing. With a neutral name the index is worth nothing:
`apollo-hospital-receipt.pdf` never reaches `tabFile`.

**What is deliberately NOT built, and why.** A `permission_query_conditions` hook on `File`
would narrow the list properly — hooks combine with `and`
(`frappe/model/db_query.py:1159-1182`, **verified in code**), so it is technically cheap — but
expressing "a parent I may actually read" in SQL for every doctype is not cheap, and getting it
wrong hides HR's own attachments on Desk. **Generated names remove the harm for a tenth of the
risk.** The remaining metadata exposure is named in §12 as residual risk for Surbhi, with the
hook priced, not built.

**Two more clauses, same requirement:** **no file name, `file_url`, byte or document content
in any log, error message, notification or background-job message.** The existing pattern is
right and must be copied: `employee_documents_read.py` logs *"employee document: <row> on
<employee> opened by <user>"* — a reference and an actor, never a value. **Personal data in a
log is a Blocker in the review, never a Major.** And **no model, no prompt, no third party**
touches these files; this slice introduces no such path and must not.

**How it will be tested.** Upload a file called `apollo-hospital-receipt-aadhaar-1234.pdf` and
assert, by query, that no row in `tabFile` contains any of those words. Assert the `file_url`
and the original name appear in no `Error Log`, no `Notification Log`, no `frappe.logger`
output and no response body except the one the uploader gets back. Run the existing
PII-in-logs scanner over the new code paths.

### 081-PRIV-3 · The reads are logged, and the employee can ask who looked

**What must be true.** **One row per viewer per file per day**, on
`Alvoraa Photo Access Log` — the table that already answers *"who looked at my face"* and
*"who looked at my Aadhaar"*. Three narrowing rules, copied from the two siblings that exist:
only when there is something to look at; **never a person looking at their own**; one row per
viewer per file per day, not one per refresh. The row holds **no file, no url, no content** —
a reference and an actor, as the doctype's own description promises.

**The reuse is not free, and the spec must say so.** *Verified in code* —
`alvoraa_photo_access_log.json` has fields `checkin`, `employee`, `employee_name`,
`document_type` (a **Link to `Employee Document Type`**), `source` (a Select with exactly
`Check-in photo` and `Employee document`), `viewed_by`, `viewed_at`, `viewed_on_date`. **There
is no field that can name a claim or a request**, and `document_type` must not be abused to
hold `"Expense Claim"` — that would be a broken link. So:

- **two new `source` options** — `Expense bill` and `Day-fix evidence`;
- **one new `reference_name` Data field**, read-only, indexed, holding the parent document's
  id and nothing else.

That is **one DocType change, no new DocType, no new log pipeline** — the doctype's own
description already anticipated it ("a `WHERE` clause, not a redesign"). Without the reference
field the log can only say "somebody looked at something of Ramesh's today", and the brief's
own ≥70% measure cannot be computed.

**The subject's own answer.** The employee must be able to ask *"who opened my bill"* and get
one, through a product surface — the same reasoning as
`employee_documents_read.what_is_shown_about_me`, which exists because the person whose
documents they are cannot open the page that shows them. Scope it to **their own** files and
show the reader and the day. Nothing about any other person.

**Exports.** Counsel, 31 October: **log every export.** This slice builds **no** bulk file
export, and must not. Desk's report export produces metadata, which the existing
`Access Log` and `Permission Log` already record. **If a "download all bills" route is ever
proposed, it is a new slice with its own 01c**, and the log row is a precondition, not a
follow-up.

**How it will be tested.** One open → one row, with the right `source` and `reference_name`;
a second open the same day → still one row; the next day → two; the owner opening their own →
no row; a failure to write the row never stops the reviewer doing their job (the
`try/except` + `frappe.log_error` pattern, with the error message asserted to carry no file
name); the subject's endpoint returns their own rows and refuses any argument naming somebody
else. **Observability:** the log can only show the control working once a routed claim type and
a filed claim exist — the fixture assertion from 081-SEC-1 covers it.

### 081-PRIV-4 · Minimisation — what this slice must NOT grow

The opposite failure, checked deliberately: an unneeded cache, copy, export or route is a
security finding in its own right. **None of the following may appear in the build**, and the
review checks for each:

- **no second copy of the bytes** — no thumbnail, no derived preview, no cache, no object
  store, no CDN (DevOps OPS-2);
- **no OCR, no amount extraction, no text layer, no PDF parsing** — the person knows the
  amount, and a parser is attacker-chosen input in a library;
- **no new export, report or public route**, and no new whitelisted method beyond the minimum:
  upload-and-bind, stream-one-file, and whatever the role queue needs. Every new
  `@frappe.whitelist()` is listed in the spec and in `docs/security/whitelisted-endpoint-review.md`;
- **no copy leaves the server** — no email of a file, no attachment on a notification, no
  webhook;
- **nothing new on `Expense Claim Detail`.** The child table is where the ALV-256 trap lives;
  this slice adds no field and no rule there.

**How it will be tested.** A count of new whitelisted endpoints, asserted against the spec's
list; a grep for a second `File` insert per upload; and the review reads the diff asking only
"what did this grow that nobody asked for".

### 081-PRIV-5 · Nothing claims a bill is masked, protected or safe

**What must be true.** Counsel's masking rule (31 Oct) **does not transfer to free-form
evidence** — we cannot mask the inside of a photograph (§4.1). So no spec sentence, UI string,
release note, HR documentation page or questionnaire answer may say or imply that a bill or a
day-fix file is masked, redacted, protected, secure or hidden. What we may say is exactly what
is true: **who can open it, that every opening is recorded, and how long it is kept.**

**How it will be tested.** The three-word assertion of 081-SEC-6, extended to the words
"masked" and "redacted", run over this slice's copy, spec and release note.

---

## 9 · What must exist before any of this is observable

Lesson 1, applied. "Zero findings" means nothing if the data cannot show the control working.

| Control | Cannot be observed until |
|---|---|
| 081-SEC-1, 081-SEC-2 | a claim type carries an approver role **for one company and not another**; a role-holder exists in each; a manager has a direct report; a claim of that type is filed |
| 081-PRIV-1 | a claim exists whose financial year has passed the 8th year end (fixture dates, not real data); an employee with a relieving date over 6 months old |
| 081-PRIV-3 | a reviewer who is **not** the subject opens a file |
| 081-SEC-8 | the day-fix form renders with the notice and a file input in one container |
| The whole slice, on the real tenant | **a read-only count on DTC before and after release**: how many claim types carry a role, how many role-holders per company, how many staff logins hold `Expense Approver`, how many Employee User Permissions are broad vs narrow. **Counts only. No writes, and nothing run against production by me.** |

---

## 10 · Verification doors — the table the test engineer builds from

Every row as **a plain staff login**, **a line manager with a direct report**, and **an HR
User**, through the API, on a **freshly created site** (a copied site hides failures —
ALV-249 broke two tests that passed on the copy).

| # | Door | Expense Claim | File | Attendance Request |
|---|---|---|---|---|
| 1 | `/api/resource/<dt>` list / get | ✔ | ✔ | ✔ |
| 2 | `reportview.get` / `get_list` / `get_count` | ✔ | ✔ | ✔ |
| 3 | `frappe.client.*` (get, get_list, get_value, attach_file) | ✔ | ✔ | ✔ |
| 4 | link search (`search_link`, `validate_link_and_fetch`) | ✔ | — | ✔ |
| 5 | report view + **CSV export** | ✔ | ✔ | ✔ |
| 6 | **share** / assign / comment | ✔ | ✔ | ✔ |
| 7 | `/private/files/<url>` direct | — | ✔ | — |
| 8 | the child table on its own (`Expense Claim Detail`) | ✔ | — | — |
| 9 | the portal's own endpoints | ✔ | ✔ | ✔ |

---

## 11 · The design's open decisions that were handed to me

**AQ2 — a System Manager's Home row opens an individual claim.** The brief's §9 gives the CXO
*"No. Summaries only."*; `portal.js:6538` and `:6625` open the oldest individual claim for a
System Manager. **My recommendation is option (a): the row leads to a count and a screen, never
to one person's claim.** It is pre-existing behaviour, it is not what the brief authorised, and
the attachment is what makes it matter — a CXO who lands in a claim's sheet now lands on a
button that opens a medical receipt. **P2**, owner `hrms-fullstack-engineer`, Surbhi's call
whether it rides in this slice. **Fail-closed default meanwhile:** if it is not fixed, the
"View bill" button must not render for a caller who reached the claim through that row — and
that is a worse, screen-level control, which is the argument for fixing the row.

**EC4(b) — accept HEIC unchanged.** **No.** Answered in 081-SEC-4 clause 4.

---

## 12 · Residual risk — named, owned, dated

| # | Risk | Label | Owner | Date |
|---|---|---|---|---|
| **R1** | **No off-server copy of any backup.** `BACKUP_BUCKET` is unset and every `bench backup` deletes the set older than 23 hours (DevOps OPS-1, Fact). From the day a bill is mandatory, DTC's **statutory tax and audit evidence for every claim ever filed** exists on one server disk, and the 8-financial-year duty in §4.1 is a duty we cannot currently honour through a disk loss, a bad restore or a wrong `rm`. **ALV-299.** Not mine to fix, and **this slice depends on it**: the retention floor and the backup gap are the same obligation seen from two ends | **Dangerous debt — escalate now.** Not a quiet table row | **Surbhi, with `hrms-devops-engineer`** | 3 Nov 2026 |
| **R2** | Any staff login can **list** the stored name, size and url of every bill and day-fix file (081-PRIV-2, verified by running it). Generated names remove the harm; the listing itself remains. A `File` query-condition hook would close it and is priced, not built | **Intentional trade-off**, proportionate | Surbhi to accept, or commission the hook | 3 Nov 2026 |
| **R3** | **PDF is the one accepted type we cannot strip**, and it is rendered in an iframe in our own origin (ALV-287's deliberate choice). Magic bytes and our own naming and content type close type confusion; PDF-internal metadata and any embedded script stay | **Acceptable simplification** — refusing PDF would wall out the office filer with an emailed invoice | Surbhi, carried from ALV-287 | 3 Nov 2026 |
| **R4** | A day-fix doctor's note **reaches the line manager by design**. The control is a notice, not a restriction (081-SEC-8). Counsel's 1 Nov advice that health data is not for managers is discharged on expense claims and **deliberately not** on day-fix requests, because there the employee keeps the choice | **Intentional trade-off**, Surbhi's decision D9 of 3 Nov 2026 | Surbhi | 3 Nov 2026 |
| **R5** | The mandatory rule **raises volume and therefore raises the chance that identity and medical documents arrive at all**. Retention and the access log bound it; nothing prevents it | **Intentional trade-off** — it is the slice | Surbhi | 3 Nov 2026 |
| **R6** | DTC's live User Permission shape is **Inference**, not verified by me — I did not and will not probe production. If any staff login lacks the broad own-record row, the §0.1 door is wider than one reporting line | **Temporary debt.** Removed by the read-only count in §9, before release | `hrms-devops-engineer` | 3 Nov 2026 |

---

## 13 · Worries — concerns I cannot yet write as a finding

Kept separate on purpose. None of these is a finding, because I cannot name the actor, state,
path and data for it.

1. **Two role-holders deciding one claim.** The design drew the dead end (AP6) and explicitly
   did not design the mechanism. A race that records two approvers, or an approval written
   against a stale read, is a governance problem before it is a security one. The BA and the
   engineer own it; if the answer involves `for_update`, slice 021's REPEATABLE READ lesson
   applies.
2. **An approver role is a `Role`, and roles are granted from Desk by anyone with System
   Manager.** Naming a role on a claim type becomes an access-granting act. A `Version` row on
   the claim type would make it reviewable, as `settings.py` does for the other
   access-granting keys. I have not made it a requirement because the claim type already
   tracks changes by default and I have not verified that — worth one check at review.
3. **`frappe.get_all` on `Expense Claim Detail`** (`inbox_api.py:589`) checks no permissions. It
   is safe because the parent list was filtered first. A future reader that calls it with its
   own filters would not be, and no test currently pins the ordering. 081-SEC-1's test 10 adds
   one.
4. **The design's two-call shape starts a retention clock earlier.** 081-PRIV-1 clause 5
   answers the orphan; what I cannot yet say is whether a *filed* claim's file ever sits
   unbound long enough to matter.

---

## 14 · Open questions, sorted

### Must know — these block the spec

**Q1 · Does the permission pair (081-SEC-1) ride in this slice, or does the approver-role half
move to its own slice?**
*My reading:* counsel's 1 November advice is only discharged with the pair, and the brief's own
§9 asks for routing to be verified as an access control. *What is ambiguous:* the brief and the
design both treat routing as already protective, because the field-level reasoning
(`expense_approver` + DocShare) looked sufficient; the tree permission was not in anyone's
view. *Why it changes the control:* without the pair, the manager still reads the medical
receipt through the API, and the slice would ship a protection that does not exist. *The one
question:* **do we build the `Expense Claim` permission pair in 081, or ship the attachments
alone and take the routing as its own slice?** — which is a split the brief already offers
(§8, §16). *Fail-closed default I will apply meanwhile:* **the routing must not ship without
the pair.** Owner: **Surbhi**, informed by `hrms-fullstack-engineer`'s impact analysis.

**Q2 · Who owns the 8-financial-year number — us or the tenant?**
*My reading:* the employer is the Data Fiduciary and the duty is theirs, so it is a **tenant
setting with our default**, and the setting may only be lengthened, never shortened below the
statutory floor. *What is ambiguous:* nothing in law; only whether we expose a setting at all
in this slice or hard-code the default. *Why it changes the control:* a hard-coded number makes
Alvora the decision-maker on someone else's statutory duty. *The one question:* **setting with
a default, or default only for now?** *Fail-closed default:* the setting, refusing any value
below the floor and refusing blank. Owner: **`hrms-business-analyst`**, with Surbhi.
**This is not a question for counsel. Counsel has ruled twice and §4 applies those rulings.**

### Should know

- **Q3 · AQ2** — does the System Manager Home row fix ride here? §11. Owner: Surbhi.
- **Q4** — does `Expense Claim Type` already track changes, so that naming a role leaves a
  `Version` row? Worry 2. Owner: `hrms-fullstack-engineer`, one check.

### Nice to know

- **Q5** — DTC's October claim volume, for sizing the retention job. DevOps' §9 command list
  already has it.

---

## 15 · What I could not verify, and the access I would need

1. **The live DTC permission shape.** I did not probe production and will not. I need a
   read-only count, run by DevOps: broad vs narrow Employee User Permissions per login; holders
   of `Expense Approver`; claim types per company. §9.
2. **The Gazette text of Companies Act s.128(5) and CGST s.36.** I read bare-act reproductions
   and agreeing commentary, not the official Gazette. The eight-financial-year period and the
   72-month period are not in doubt; the exact word "vouchers" in s.128(5) rests on
   reproductions. If a customer questionnaire is ever going to quote the statute, somebody
   should read the Gazette once and record the date.
3. **Whether DPDP s.8(7) is yet in force.** Commentary says a later commencement phase. Marked
   `[ASSUMPTION]`; nothing in §8 depends on it, because the statutory retention floor binds
   regardless.
4. **The end-to-end iPhone upload.** Nobody here has tested it (DevOps OPS-11). My 081-SEC-4
   clause 4 assumes the browser canvas converts HEIC; if it does not, the refusal fires and an
   iPhone filer cannot file. That is a product risk the design already owns (EC4), and my
   requirement is unchanged either way.
5. **Any of 081-SEC-1's door tests, run for real.** I read the code and the installed Frappe
   source, and I ran `get_permission_query_conditions` for a synthetic plain-staff login on the
   local dev bench. I did **not** build the two-company fixture and execute the ten doors —
   that is the test engineer's work, and the review should insist on the demonstration before
   accepting 081-SEC-1 as met.
6. **I am the author of these requirements.** At the review I will be marking my own
   specification as met or not met. For 081-SEC-1 in particular — the one requirement that
   changes the architecture — **ask for a second pair of eyes**, from
   `hrms-technofunctional-reviewer`, on whether the permission pair is the right mechanism. The
   builder must not approve its own requirements.

---

## 16 · Subtract pass — what I removed

Read once more asking only *what can I delete and still meet the requirement?*

**Removed:**

- **A `File` `permission_query_conditions` hook.** Written as a requirement, then cut. It is
  technically cheap and behaviourally expensive — expressing "a parent I may actually read" in
  SQL risks hiding HR's own attachments on Desk, which is a control people route around.
  Generated file names (081-PRIV-2) remove the harm for a tenth of the risk. The hook is priced
  in §12 R2 as Surbhi's to commission, not built.
- **A separate SEC requirement for share and export.** Folded into 081-SEC-1 as ptypes, because
  they are the same read through another door and want the same mechanism, not a second one.
- **A separate SEC requirement for the leaver and for the cross-company role-holder.** Both are
  "who the role resolves to", so both are clauses of 081-SEC-2. Two requirements became one.
- **A separate PRIV requirement for cancellation and for leavers.** Folded into 081-PRIV-1 —
  they *are* the retention answer, and stating them twice would have buried it.
- **A PDF sanitiser, and a server-side page count.** Both would add attacker-chosen input to a
  library. The design's "PDF · 2 pages" tile does not need the server to open the file, and
  081-SEC-4 clause 6 now forbids it.
- **A new "evidence access" log doctype.** Two fields on the table that exists.
- **A new CI gate.** None. The four existing gates — the permission suite, the isolation suite,
  the `ignore_permissions` ceiling, the PII-in-logs scanner — already carry every assertion
  above. Adding a fifth would have been the easy way to look thorough.
- **A DPIA for this slice.** The processing is employee expense evidence held by the employer
  for a statutory purpose, with a named reader set and a statutory clock. It does not meet the
  threshold on its own, and 078/079 already cover employee documents. One less document that
  nobody would read.
- **A question to counsel.** There was a draft one about the voucher period. It is a statutory
  lookup, not a point of law, and §4.1 does it. Surbhi is right: *"we already have an answer
  for this why send it again."*

**What is left:** eight SEC items and five PRIV items, of which **one** (081-SEC-1) is new
architecture and the rest are the existing patterns in this codebase pointed at two new files.

---

## 17 · For the business analyst — the trace you must close

Every item below needs at least one acceptance criterion, and the ones in bold need a test that
**fails without the fix**.

| Requirement | One line |
|---|---|
| **081-SEC-1** | The permission pair on `Expense Claim`; ten doors; two companies; fresh site |
| **081-SEC-2** | Role scope in the query: company, Active, no holder → refuse at filing |
| **081-SEC-3** | Mandatory rule on the document at submit; the server's own sentence |
| **081-SEC-4** | Magic bytes; our name; our content type; HEIC refused; images stripped; PDF not parsed |
| **081-SEC-5** | Length before decode; one file; rate limit; the bind endpoint takes no unchecked id; one `File` row |
| **081-SEC-6** | One guarded stream; no `/private/files/` in any response; nothing called protected |
| **081-SEC-7** | `hr_api.py` ≤ 67; `attendance_correction.py` 0; new files at 0 with their own entry |
| 081-SEC-8 | The notice is present **and positioned before the file picker** — a transparency control |
| **081-PRIV-1** | Two clocks, 8 financial years / employment + 6 months, legal hold, orphans at 7 days, never "for ever", counts per pass |
| **081-PRIV-2** | Generated stored names; nothing personal in any log, message or notification |
| 081-PRIV-3 | One row per viewer per file per day; two new `source` options and a `reference_name`; the subject's own answer |
| 081-PRIV-4 | No second copy, no OCR, no new export, no new route beyond the minimum |
| 081-PRIV-5 | No copy anywhere says masked, redacted, protected, secure or hidden |

---

**Governance note.** The only requirement here that is new architecture is 081-SEC-1, and it
exists because the protection the brief and the design both relied on is not in the code yet. I
have not reopened a product decision to say so — the routing decision stands, and 081-SEC-1 is
what makes it true.
