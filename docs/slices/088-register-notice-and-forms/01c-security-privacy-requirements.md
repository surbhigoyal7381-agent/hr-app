---
slice: 088-register-notice-and-forms
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-11-21
status: draft for the business analyst. Recommendations only. Surbhi decides; I approve nothing.
risk tier: 1 (pay gate, a photo of a signature or thumb print kept for years, retention)
inputs:
  - 01-product-brief.md, with the brief gate (Surbhi, 21 Nov 2026)
  - 01b-ux-design.md, with the design gate D-1 to D-4 (Surbhi, 21 Nov 2026)
  - prototype-v1.html (read as text, not opened in a browser)
  - 07-devops-inputs.md §1
  - memory counsel-087-hr-punches-nov21 (counsel, 21 Nov 2026, relayed by Surbhi, unsigned)
  - 087 01c, and the 087 spec section "Confirm redesigned" (02-functional-spec.md:813-826)
---

# 088 · Security and privacy requirements: the monthly change notice

## 0 · The short version

**Bad news first.**

1. **If the signed-page photo is attached to the Attendance Request, the employee and their line manager can open it.** Frappe's private-file gate falls back to the read right on the record the file is attached to (`frappe/core/doctype/file/file.py:1009-1024`, installed Frappe 16.33.1). The Employee role reads its own Attendance Request (stock `attendance_request.json`), and a manager reads their reports' requests through a User Permission (`manager_scope.py:52-56`). So "only HR can open the photo", which the dialog says, would be false. SEC-8 puts the photo on a record only HR in scope can read.
2. **The design logs printing at the Print button, but the notice content reaches the screen earlier, at the preview.** A screenshot or Ctrl+P of the preview would leave no log. SEC-2 logs at the moment the server releases the content, and refuses the content if the log row cannot be written.
3. **The photo checks the brief names would make the evidence unreadable.** `employee_photo.py` stores every image at 512 px on the long edge (`STORED_EDGE = 512`, line 84). A signed A4 page needs about 1,600 px (`expense_evidence.py:126-131`, slice 081). SEC-6 reuses 081's checks instead. This differs from brief §8 and DevOps OPS-4, which name `employee_photo.py`.
4. **The access log 088 would write into is not scoped by company.** `Alvoraa Photo Access Log` has no row filter in `hooks.py` `permission_query_conditions` (read this session), and HR Manager holds read, report and export on it (its DocType json). An HR Manager limited to company A can probably list company B's rows: employee names and who looked at their photos. **Inference from code, not run.** It exists today; 088 adds to it. SEC-10.
5. **The thumb-print question is open, and an older law may answer it before DPDP does.** The DPDP Act has no special category for biometric data, but the IT Act's SPDI Rules 2011 list "biometric information" as sensitive and stay in force until section 43A is omitted on 13 May 2027 (secondary source, read 21 Nov 2026; §8). ⚠ COMPLIANCE C1.

**Counts: 11 SEC, 6 PRIV, 3 ⚠ COMPLIANCE questions.**

## 1 · What I read, and on which checkout

- **088 worktree**, branch `slice/088-register-notice-and-forms`, HEAD `87a8e614`, based on dev `bad23ce0`. `origin/dev` is `b3844e58`, 2 commits ahead (ALV-422 joiner sign-out; nothing about attendance). **This worktree has no 087 code**: `punch_fix.py` is not here. 088 must be built on top of 087.
- **087 worktree**, branch `slice/087-attendance-follows-punches`, HEAD `70633e2a`, 42 commits ahead of `origin/dev`, not pushed. Read `punch_fix.py:55-80` (the Confirm fields) and `:316-343` (`_own_the_confirm_fields`: the server puts the Confirm fields back on every edit and clears a Confirm when the content changes). **No "signed on the register" field exists in 087's code** (grep for `register` in `punch_fix.py`: nothing). 088 adds it.
- **Read in 088 code:** `hrms/alvoraa_hr_core/access.py:238-345` (`permitted_companies`, `permitted_branches`, `permitted_employee_filters`, `employee_in_scope`); `field_app_access.py:248-275` (`checkin_query_conditions`, ALV-412) and `:475-530` (`log_photo_view`); `employee_photo.py` (header, `_decode`, `_reencode`, `_store`); `expense_evidence.py:1-160, 625-700` (081's decoder, caps and `open_evidence`); `employee_documents_read.py:1-60, 210-265`; `manager_scope.py:40-56`; `hooks.py:560-580, 620-631` and `permission_query_conditions`; the `Alvoraa Photo Access Log` and `Alvoraa Notice Acknowledgement` DocType json.
- **Read in installed Frappe** (container `alv394-bench`, Frappe `988e54f`, v16.33.1), read only: `file.py` `has_permission` (989-1026), `is_downloadable` (896); `file/utils.py` `find_file_by_url` (452-465); `utils/response.py` `download_private_file` (294-306); `permissions.py` `has_permission` (81-245) and `has_controller_permissions` (483); `model/document.py` `has_permission` (402-414); `auth.py` `validate_csrf_token` (81-97); `access_log.py` `make_access_log` (49-77); `hooks.py` `default_log_clearing_doctypes` (522-538).
- **Not run:** no test, no site query, no production access. Every permission statement is about stock role rows in code. A tenant's Custom DocPerm can differ.

## 2 · Threat model, four questions

1. **Who wants it, and what is the cheapest way?** An HR person who wants a change they filed to count without the worker's real agreement: they sign the box themselves, or a second HR person records a page nobody signed. Next, a curious colleague or supervisor who wants another worker's notice (the reasons can be personal) or the signature photo. Then an HR person in another store who opens notices outside their branch.
2. **Blast radius.** One forged record is one person's pay for one month. One scope mistake in the list or the photo reader is every notice in a company. Each tenant is its own site, so nothing here is cross-tenant. Cross-company and cross-branch exposure is real on a multi-company site (SEC-1).
3. **What becomes possible that was not.** A photo of a person's signature or thumb print, kept for years. A printed sheet of personal data leaving the system. A paper route that confirms a pay change and unblocks a salary slip.
4. **How would we find out?** For an app user: the app says "You signed for it on the register", and they can press "Not right" at any time (087). For a worker with no app: only in a grievance, by looking at the photo. **That gap is residual risk R1.** The durable trail is the records themselves (SEC-2, SEC-5), not `security.log`, which rotates.

## 3 · Data inventory: what 088 adds

A1 (field sensitivity classes) is not built, so these classes are written here and enforced by nothing automatic.

| Item | Class | Purpose | Retention | Who may see it |
|---|---|---|---|---|
| The notice content: the person's own changes, filer name and role, the filer's reason, valid hours | sensitive (decides pay; free text can hold health or family reasons) | tell the worker what others changed | not stored again. It is read from the existing requests at print time. No PDF, no file, no copy (PRIV-1) | the employee; HR in scope |
| The print record: employee, month, the reference printed on the page, the exact list of changes on it, printed by, printed at | internal (ids, a time) | evidence the change was shown on the monthly register (counsel's condition for manager additions); what a signature covers (SEC-3) | as the attendance records it covers. ⚠ C2 | HR in scope |
| Photo of each signed page | **sensitive, treated as biometric-class until counsel answers** (a thumb print or signature, plus the page's content) | proof of the worker's confirmation | ⚠ C2. Nothing deletes it in 088 | **HR in scope only** (SEC-8) |
| Recorded by, recorded at, outcome (signed or disputed), dispute reason | internal; the dispute reason is sensitive free text | the 087 pay gate; audit | as above | HR in scope; the employee sees the state and date |
| Who opened a photo | internal | "who looked at my signature" | as the photo | HR in scope (SEC-10) |

## 4 · Access intent, including who must NOT

| Actor | May | Must NOT |
|---|---|---|
| HR User / HR Manager, in scope (companies, then branches) | see the list, print notices, record a signature or a dispute, open a photo through the product | act outside their companies or branches; record for a page that holds a change they filed; record their own notice; get a `/private/files` address; export photos |
| HR with no company and no branch permission | nothing | anything (`permitted_companies` returns `[]`) |
| System Manager | as HR, every company (`permitted_employee_filters` returns everyone) | record a page holding a change they filed, or their own |
| Employee (Active) with the app | see their own changed days, who filed them, the state, and press Confirm or Not right (087) | see or download any photo, including their own; see anyone else's notice |
| Employee with no app | hold their own paper | n/a |
| Line manager, a supervisor, a Biometric Sync account, any login with only a print right | nothing new | see the list, a notice, or a photo |
| A leaver | nothing in the app (`_me` filters `status = "Active"`). HR may still print their last month | n/a |

## 5 · Abuse cases

| # | Actor and act | Closed by |
|---|---|---|
| A1 | **Forged signature.** HR person A files a change, signs the box, and asks B to record it | SEC-4 refuses A as recorder. B recording a page nobody signed is collusion: not preventable by structure. Residual R1 |
| A2 | **HR records for its own filing,** on the portal, the Desk or REST | SEC-4 on every door; SEC-5 makes the fields server-owned |
| A3 | **HR in another company or branch** lists, prints, records or opens a photo for someone outside their scope | SEC-1, SEC-8 |
| A4 | **Wrong person's photo.** HR photographs Ravi's signed page and records it for Joginder | The page shows the name and a reference; the dialog shows both next to the preview (SEC-7). No server check is possible without reading the image. Residual R2 |
| A5 | **Reused photo.** HR uploads last month's photo, or one page photo for two people | SEC-7 refuses a photo whose bytes match any stored register photo. A new shot of an old page is not caught; the month and reference on the page are the defence. Residual R3 |
| A6 | **Stale paper.** A change is edited or withdrawn after printing, then the old page is recorded | SEC-3 |
| A7 | **Print without a trace.** HR opens the preview and screenshots it | SEC-2 |
| A8 | **Photo by URL.** The employee, a manager or a colleague with the URL fetches `/private/files/...` | SEC-8 |
| A9 | **Script in a reason.** A manager writes `<img src=x onerror=...>` as the reason; it runs in HR's session at preview | SEC-9 |
| A10 | **Forged link.** A page on another site makes HR's browser post "record signature" | SEC-11 |
| A11 | **The paper is read on the floor** by a colleague | One person per page, footer "Keep it private", HR hands it over (PRIV-2). Residual R5 |

## 6 · Requirements

"Fails first" means: break the control, watch that exact test fail, then put it back (verify rule 5).

### SEC-1 · One scope rule, the ALV-412 one, on every 088 reader and writer

Every 088 call (the list, the notice content, record signature, record dispute, open photo) and every row filter and `has_permission` hook on a record 088 adds uses `permitted_employee_filters` or `employee_in_scope` (`access.py:297-345`). That is the rule `checkin_query_conditions` uses since ALV-412 (`field_app_access.py:248-275`): HR roles only, its companies, narrowed to its branches where it has any, an employee with no branch outside a branch HR's scope, and nothing at all for HR with neither.
- Do **not** copy `_scoped_by_employee_company` (`field_app_access.py`): it checks company only, never branch.
- Do **not** write `dict(permitted_employee_filters(), name=X)`: the `name` key replaces the refusal (warning in `employee_in_scope`'s docstring).
- Lesson 2: the BA lists every reader 088 adds, and the engineer greps for any that builds its own query.

**Test:** with the people in §9: company-A HR refused on a company-B employee at each call; branch-1 HR refused on a branch-2 employee and on a no-branch employee; no-company HR gets an empty list and is refused by name; a manager, a plain employee and a Biometric Sync login are refused at each call; System Manager succeeds. Fails first: replace the helper with a company-only check, and watch the branch test go green when it should not.

### SEC-2 · The notice content leaves the server only through one logged call

- The list payload carries no reason and no change detail. Only name, number, branch, a count and the state.
- The content (changes, filer, reason) is returned only by one `POST` call, which first writes the print record (§3): who, when, which employee, which month, which change ids, the reference. **If the write fails, the content is refused** (Surbhi's rule for joiner exports, 19 Nov 2026: "refuse the export").
- The log is written when the content is released, i.e. at **preview**, not at the Print button. The row may still say "Print opened". This changes when the design logs, not what HR sees; the BA should confirm with the designer.
- At most 100 people per call, refused on the server (design gate assumption, 21 Nov).
- The durable record is a database row. Not `frappe.logger("alvoraa")`, not `security.log`, not Frappe's `Access Log`, which is written later by a 15-minute job (`deferred_insert`, Frappe `hooks.py:232`).

**Test:** press Preview in a browser test and assert one print row per person with the change ids (memory: test what it sends); force the insert to fail and assert no content is returned; ask for 101 people and assert a refusal; the list response holds no `explanation` or reason key. Fails first: move the insert after the return.

### SEC-3 · A signature covers exactly what was printed, read from the server

- "Record signature" names a print record, never a list of change ids from the browser. It covers the changes on that record only. Later changes stay open (design N4).
- A covered change that was withdrawn, replaced, or edited in its confirmed content since the print (087's `CONFIRMED_CONTENT` test, `punch_fix.py:342`) is **not** confirmed, and the dialog says which.
- No print record, no recording.

**Test:** print, file a new change, record: the new change stays unconfirmed. Print, edit a covered change's time, record: that change stays unconfirmed. Post a forged id list: ignored or refused.

### SEC-4 · Nobody records a confirmation they have an interest in

Checked on the server, at recording, for both outcomes (signed and disputed). The recorder must:
- hold HR User, HR Manager or System Manager, and pass SEC-1 for the employee;
- **not be the filer of any change on the page** (087 rule, kept by the design gate). The test reads the request `owner`, from the database;
- **not be the employee**, by `user_id` whatever the Employee status, the way `refuse_own_decision` does (`access.py:109`). So an HR person cannot record their own notice, even after leaving.

A dispute (D-2) follows the same rule. The filer would otherwise write the worker's objection in their own words.

**Test:** filer refused, at the endpoint and on the Desk and REST doors (SEC-5); own notice refused, including with the Employee set to Left; a second HR person in scope succeeds and is named as recorder.

### SEC-5 · The confirmation fields are written by the record call only

The new fields (signed on the register by, at, the print record link, the outcome) follow `_own_the_confirm_fields` (`punch_fix.py:316-343`): set only under a process flag that a client cannot send, and put back to the stored value on every other insert or save, from the Desk, REST or a data import. `read_only` alone does not stop an API write. The salary-slip gate reads these fields.
- Once recorded, HR cannot remove or replace a signature. The worker's "Not right" (087) is the way to undo it. A System Manager change in the Desk stays possible and is recorded in Version.

**Test:** REST `PUT` of the "signed" fields as HR: stored value unchanged, slip still blocked; Desk save as System Manager with the field changed: unchanged. Fails first: remove the put-back.

### SEC-6 · The photo upload reuses slice 081's checks, not the profile photo's

Reuse `expense_evidence.py`'s decoder and caps for a page: length checked before decode; magic bytes JPEG or PNG only; re-encode through Pillow, which strips EXIF and GPS; long edge 1,600 px; stored size at most 1 MB (`expense_evidence.py:105-131`, Surbhi 3 Nov 2026 for bills). **PDF refused** (photo only). HEIC refused. The stored file name is generated and names no person (081-PRIV-2: any staff login can list File names). `POST` only, rate-limited like `open_evidence`. One photo per printed page, required for "signed"; none required for a dispute, so an objection is never harder to record than a signature.

**Test:** a zip renamed `.jpg` refused; a PDF refused; a 13 MB image refused before decode; a PNG with GPS stored with no EXIF; the stored file is at most 1 MB and 1,600 px; the file name holds no employee name; three pages need three photos.

### SEC-7 · A reused photo is refused, and the dialog makes the wrong person visible

- Refuse a page photo whose stored `content_hash` (Frappe `file.py:62, 822`) equals any other register photo, for any person or month, or another page of the same record. **Honest scope:** this stops the same file being used twice. It does not catch a new photo of an old page.
- Every printed page carries the month and a reference. The dialog shows the person's name and that reference next to the photo preview: "Check the page shows {name} and {ref}". The design already shows the preview (01b §4.4).

**Test:** record a photo, then the same file for another person: refused; same file for page 2 of the same record: refused.

### SEC-8 · Only HR in scope can open the photo, by structure

- **The photo's File is attached to a record whose read right is HR-in-scope only**: no Employee role row, not on a manager User Permission list, with a row filter and a `has_permission` hook built from SEC-1's helpers. The private-file route then refuses everyone else, because it asks the parent's read right (`file.py:1009-1024`), which runs the parent's `has_permission` hook (`permissions.py:239`, `has_controller_permissions`).
- **Not Attendance Request** (the employee and the manager read it, §0 point 1), and not Employee (the employee reads their own record).
- **Smallest shape, for the engineer to confirm:** one record per print, the print record in §3. It is the print log (SEC-2), the coverage list (SEC-3) and the photo's parent, in one. Cheaper rungs rejected: Attendance Request (above; and one photo covers many requests); `Alvoraa Notice Acknowledgement` (another purpose, the app privacy notice, and scoped by company only); `Alvoraa Photo Access Log` (a log of views, readable and exportable by HR Manager).
- The browser never gets a `/private/files` address. A photo opens through a `POST` endpoint that checks SEC-1, streams the bytes and writes one view row, as `expense_evidence.open_evidence` does (`expense_evidence.py:625-700`). The design draws no viewer yet; this rule applies when one is built.
- **No export:** no role holds export on the record, no "download all", no photo in any report, email, notification, Inbox row or API list payload.

**Test:** as the employee, and as the line manager, `GET /private/files/<the photo>`: 403. As company-B HR: 403. As in-scope HR through the endpoint: the bytes, and one view row. Report Builder export on the record as HR Manager: refused. Fails first: attach the photo to the Attendance Request, and watch the employee fetch succeed.

### SEC-9 · Free text is shown as text, never as markup

The filer's reason, names and the dispute reason are escaped in the list, the preview, the paper and the dialog.

**Test:** a reason of `<img src=x onerror=window.__x=1>` prints as those characters and sets nothing, in a browser test of the preview.

### SEC-10 · The photo access log is scoped too

088 writes view rows into `Alvoraa Photo Access Log` (new `source` options, for example "Register signature photo"). Add a row filter by SEC-1's rule. Today it has none (§0 point 4). If Surbhi prefers, this goes into its own ticket, but then the residual risk R6 is named and dated.

**Test:** company-A HR Manager lists the log: no company-B rows. Fails first: remove the filter.

### SEC-11 · Calls that change or release data are POST-only, with the CSRF token

Every new 088 endpoint is `@frappe.whitelist(methods=["POST"])` (the ALV-411 pattern). The page that calls them renders a CSRF token. Frappe skips the token check when the session holds none (`auth.py:87`), which is the ALV-343 trap.

**Test:** a GET to each endpoint changes nothing; a POST without the token from a session that holds one is refused.

### PRIV-1 · Collect nothing new about the person except the photo

- No PDF, no server copy of the notice, no cache of its content.
- The kept-on-retry photo (01b states) stays in page memory only: never `localStorage`, `IndexedDB` or a service-worker cache. HR phones are shared.
- Logs, errors and refusal sentences carry ids only: never a reason, a name or a file name.

**Test:** after a failed and a retried record, browser storage holds no image; force an error and grep the Error Log for the reason text: no hits.

### PRIV-2 · What goes on paper (reasons in full, as Surbhi decided)

- One person per page, only their own changes made by someone else (HR-filed, set-asides and, by D-4, manager additions), only valid hours, the filer's name and role, and **the filer's reason in full** (D-3, Surbhi, 21 Nov 2026).
- **Never on paper:** HR's review note (`alvoraa_review_note`), any other person's data, any leave or absence reason, pay amounts, punch photos, GPS, the repeat scans the system did not count.
- 087's send bar gets the hint that the reason is printed on the employee's notice (D-3). That is the only warning the filer gets, so it must be on every door where a filer types a reason for someone else.
- Footer: "This page is only about you. Keep it private."

**Test:** a notice for a person with an HR note, a leave day and a colleague's change on the same day: none of the three appears.

### PRIV-3 · The photo is handled as the most sensitive thing this slice holds

Until counsel answers C1: SEC-8 (HR in scope only, every opening recorded), SEC-6 (no metadata, capped), never exported, never in a log, notification, email, report or model prompt, never shown to a line manager.

**Test:** covered by SEC-6, SEC-8, SEC-10.

### PRIV-4 · Retention: nothing deletes, and nothing is deletable by HR

- 088 adds no deletion path, and the erase job stays off.
- HR cannot delete a print record or a photo. Frappe's own rule lets a draft's attachment be deleted (`file.py` `validate_protected_file`), so the record must refuse it itself.
- The print record stores the employee and the month, so a future purge can work out its date without reading the photo.
- Backups copy every file (`bench backup --with-files`). Any future deletion must say what happens to backups.

**Test:** HR delete of the record and of its File: refused, from the Desk and REST.

### PRIV-5 · The employee app shows the same facts as the paper, about them only

- Own days only, through the Active-only `_me` lookup. The same facts as the notice, including the filer's reason: the app must never show less than the paper (the design's one-way rule).
- The states in 087 v5's words ("You signed for it on the register").
- Never the photo, its address or its file name, in any payload.

**Test:** the employee's API response has the reason and the state, and no key holding `photo`, `file` or `url`; a colleague asking for another person's list is refused.

### PRIV-6 · The print record is evidence, so it lives as long as what it proves

Counsel's rule for a manager's addition is that it is shown "on the monthly register or payslip" (counsel, 21 Nov 2026, relayed). The print record is the proof it was shown. So it is kept with the attendance records, not cleared like a log. Nothing in Frappe clears it by default (`Access Log` is not in `default_log_clearing_doctypes`, and this record is ours).

**Test:** none needed beyond PRIV-4; the BA records it as a rule.

## 7 · The audit trail

From the database alone, for any confirmed change, a person can answer: which page it was on and when it was printed and by whom (print record); who recorded the signature or the dispute, when, and with what photo (SEC-5 fields, SEC-8); who opened the photo since (SEC-10). The question "did the worker really sign" is answered only by the photo (R1).

## 8 · Obligations engaged

| Obligation | Source and date checked | What it asks of 088 |
|---|---|---|
| DPDP Act 2023 and Rules 2025: security safeguards, accuracy, notice | baseline §2, verified 24 Aug 2026, **stale from 22 Nov 2026** | SEC-1, SEC-8, PRIV-3. The employer is the Data Fiduciary, Alvora the processor (counsel, 31 Oct 2026, relayed) |
| IT Act s.43A and SPDI Rules 2011: "biometric information" is sensitive (Rule 3); s.43A omitted from 13 May 2027 by DPDP s.44(2) | [Taxmann](https://www.taxmann.com/post/blog/spdi-rules-vs-dpdp-act), secondary source, read 21 Nov 2026. **I did not read the Rule 2(1)(b) definition or the gazette** | ⚠ C1 |
| Wage and attendance records retention | counsel, 21 Nov 2026, relayed: "attendance and wage records at least 5 years from the last entry (6 to 8 for tax/PF audits)" | ⚠ C2 |
| Grace go-live condition 3 | counsel, 21 Nov 2026, relayed: "staff who don't use the app get a monthly register notice" | the whole slice |

**⚠ COMPLIANCE C1 (owner: Surbhi to send, counsel answers). Is the photo biometric data?** "We keep a phone photo of a printed page that carries the worker's handwritten signature or ink thumb impression, to prove they confirmed attendance changes. Is that 'biometric information' under the SPDI Rules 2011 while they remain in force, and does it need anything under DPDP beyond ordinary personal data? If it is sensitive, does the employer need the worker's written consent (Rule 5), and who may open it?" **Blocks:** release to a customer, not the build. **Until answered:** PRIV-3.

**⚠ COMPLIANCE C2 (owner: Surbhi, counsel). How long are the signed-page photo and the print record kept, from when, and who deletes them?** Is the signed notice an "attendance record" under the 5-year rule? Counsel's 18 Sep 2026 position on not keeping personal data for ever is the other pull (memory `legal-retention-rules-2026-09`). **Blocks:** the purge design and the retention sentence in any customer answer. Not the build: nothing deletes in 088.

**⚠ COMPLIANCE C3 (owner: Surbhi, counsel; brief Q3). Is one photo per signed page, one person per page, enough evidence?** And is a dispute that HR records from the worker's words (D-2) enough, with no signature of the worker on it? **Blocks:** release for Grace. The design assumes yes.

## 9 · What must exist before each control can be seen working

Without these, "0 findings" means nothing (lesson 1). On the test site, with 087's code underneath:
- in one month, for one person: an HR-filed change, a manager set-aside, a manager addition, and one change filed after the print; a second person with six changes (two pages);
- two HR logins in one company (one is the filer); HR in a second company; a branch HR with an employee in another branch and one with no branch; a no-company HR; a System Manager; an HR person who is also an employee with their own notice, then set to Left;
- a line manager and a plain employee; a Biometric Sync account;
- a company with 087's slip gate on, and one with it off.

## 10 · What I could not check

- Whether the `has_permission` hook on the photo's parent runs on the private-file route in practice. **Verified in code** (the call chain above), **not run**. SEC-8's direct-URL test settles it.
- Whether `Alvoraa Photo Access Log` really lists other companies' rows (SEC-10). I would need a site with two companies and an HR Manager limited to one.
- Tenant Custom DocPerm on Attendance Request and on the log. I would need read-only site access.
- What a real signed-page photo weighs after 081's re-encode (OPS-8). The engineer times one.
- The SPDI Rules' own text, and the gazette for the 13 May 2027 date.

## 11 · Residual risk (proposed. Owner: Surbhi. Nothing is accepted until she says so)

| # | Risk | Label |
|---|---|---|
| R1 | Collusion or forgery: two HR people record a page the worker never signed. A worker with no app cannot see it; only a grievance and the photo find it | intentional trade-off, **needs her name and date** |
| R2 | Wrong person's page recorded. Only HR's eye on the name and reference stands in the way | acceptable simplification |
| R3 | A fresh photo of an old page passes SEC-7 | acceptable simplification; the month is on the page |
| R4 | Frappe lets a File's owner read it always (`file.py:998`). The recording HR keeps that right even after losing the HR role. They never get the URL (SEC-8) | acceptable simplification |
| R5 | Once printed, the paper is out of our control | intentional trade-off, accepted with D-3 on 21 Nov 2026 |
| R6 | The photo access log stays unscoped if SEC-10 is split off | **dangerous debt if untracked: ticket it now** |
| R7 | Photos kept with no deletion until C2 is answered; every backup copies them | temporary debt; removed by the purge slice after C2 |
| R8 | The baseline's DPDP section goes stale on 22 Nov 2026 | temporary debt; I re-verify before the 06 review |

## 12 · Questions

**Must know:** C1 and C3 block release, not the build (§8).

**Should know**
- **Q1 (Surbhi).** A wrong photo was recorded (wrong person). HR cannot delete it (PRIV-4). My default: a System Manager fixes it in the Desk, and Version records it. Is that enough?
- **Q2 (Surbhi).** Should the employee app also say who recorded their signature? It would let a worker spot a signature they never gave (R1). It changes 087 v5's approved words, so it needs her yes. Default: keep the approved words.
- **Q3 (BA).** A dispute recorded from paper files 087's replacement request. Who is its filer? If HR, 087's rule would make it need the worker's Confirm again. The BA should settle this before writing the criteria.

## 13 · Found on the way (not 088's to fix)

- `employee_documents_read.py` (docstring, lines 26-37) says no `has_permission` hook fires on the private-file route. In installed Frappe 16.33.1 the parent's read check reaches `has_controller_permissions` (`permissions.py:239`). The docstring may be wrong (lesson 5). Its claim is about the `Employee` parent, so check it there with a test before anyone relies on either version.

## 14 · Subtract pass

I removed these:
- a requirement for a second HR person to *print* (only recording needs one);
- a server-side check of the photo's content (OCR or name matching): a parser of attacker-chosen input, and over-building (081-PRIV-4 made the same call);
- a "who looked at my signature" screen for the employee (081 has `who_opened_mine`; nobody asked here);
- a QR code on the page; a per-day signature box (the design gate chose one per page);
- a DPIA. The processing (attendance correction) exists; the new item is one photo class, covered by C1. If counsel says it is biometric, a DPIA becomes the next step.

I added no new gate, no new log pipeline and no new tool. SEC-10 fixes an existing table rather than adding one.

**Governance note.** I will also write `06-security-review.md` for this slice, which means verifying requirements I wrote. The technofunctional reviewer should check SEC-4 and SEC-8 independently.
