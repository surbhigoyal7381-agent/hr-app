---
slice: 078-positions-faces
artifact: 06-security-review
author: hrms-security-privacy-engineer
date: 2026-10-31 (evening)
head_reviewed: c5494a29
inputs:
  - 01c-security-privacy-requirements.md §§1-7 (the requirements I am verifying)
  - 01c addendum of this evening (A1-A12) - OUT OF SCOPE, see §0
  - 04-test-report.md (test engineer, written on head d3696e82)
  - counsel's rulings of 29 Oct 2026 (in the code) and of 31 Oct 2026 (summarised to me, not read by me)
  - every file in the diff, read in this worktree on 31 Oct 2026
status: recommendation only. I do not approve the release. Surbhi decides.
---

# 078 · Security and privacy review

## 0 · Read this first

**Three scope facts, before any finding.**

1. **The addendum I wrote this evening is not a list of unmet requirements.**
   Surbhi deferred the whole required-fields and wider-joiner-list change to its own
   slice. So `078-SEC-17`, `078-SEC-18`, `078-SEC-19` and `078-PRIV-10` to `078-PRIV-14`
   are **not in scope for this release**. Nothing in them is built, and nothing in them
   should be. **`078-PRIV-9` is still the live control** - the joiner form asks the fixed
   seven fields, and I verified that in the code.
2. **The joiner form ships switched off.** Verified in code, not taken on trust.
3. **Tonight's push also carries slice 076 Part C** (expense approver, birthdays, home).
   That was reviewed in `docs/slices/076-home-notices/06-security-C.md`. I did not
   re-review it here.

**Governance note, as my own rules require.** I wrote the requirements I am marking. Two
of them are arguments rather than measurements and wanted a second pair of eyes:
`078-SEC-3`'s reasoning (now moot - it was declined) and `078-PRIV-7`'s
proof-of-deliberate-setting (now removed by decision). I say so at the top, not at the
bottom.

---

## 1 · The verdict, in one paragraph

**One thing fails tonight, and it is small: a new permission bypass went into
`joiner_public.py` with defect fix D-3, and the counter that exists to catch exactly that
was not updated - so `test_sec16_ignore_permissions_does_not_grow` fails on this head.
The gate is working; the fix is one number and one sentence of reasoning.** Everything
else I checked holds. The company boundary, which was the one real hole in the test
report, is a real control in real code and now has a real test. The 48 px face is private
- both copies come out of one `_store` with `is_private: 1`. No personal value reaches a
log line anywhere in the new code; I read every logging call. The joiner form is off by
default, and every guest endpoint gives a dead-link answer while it is off. **Counsel's
three new rulings are correctly deferred with the feature** - none of them has to be true
before this code ships with the form off, because with the form off no joiner data exists
to retain, export, or be told about. But two of them become true the moment a System
Manager ticks one box, and today **nothing in the code stops that tick** - the only thing
between it and a stranger's Aadhaar scan is an instruction, and an instruction is not a
control. I recommend one five-line guard before `main`, or a written, dated acceptance
instead. Tonight's residual risk is otherwise small, and almost all of it is risk the
product already carried this morning.

---

## 2 · Every requirement, by name

Marked against **head `c5494a29`**, by me, reading the code. Where the test engineer and I
differ, I say so. `Met` means I can name the file and the line.

### 2.1 Security

| ID | State | Evidence I checked myself |
|---|---|---|
| SEC-1 | **Met** | `hrms/alvoraa_org_structure/people_fields.py:40-59` is the closed list (ten, not eleven - "work phone" does not exist on Employee). The setter refuses an off-list name in `settings.py:_set_access_setting`; the reader intersects **again** in `positions_profile.ticked_fields()` → `people_fields.allowed()`. The deny list and `is_denied()` read live payroll rule-set fields. Both ends intersect, which is the half that survives a future UI |
| SEC-2 | **Met** | `positions_profile._guard` (`:79-91`) = `register.may_view()` **and** `access.employee_in_scope`. `employee_in_scope` (`hrms/alvoraa_hr_core/access.py:291-301`) joins its conditions as a **list**, so the caller's `name` cannot replace the refusal. `permitted_employee_filters` returns `NO_EMPLOYEES` for a caller with no companies - fails closed. Denied link fields are **absent**, not blank (`positions_profile.py:118-121`). **The company half now has a test** (`test_company_scope_078.py`, 9 tests, `c5494a29`) - §4.1 says what that proves tonight and what it does not |
| SEC-3 | **Not adopted, by decision** (Surbhi, Decision 4, 31 Oct) | Not a test gap. **And a mitigation nobody had written down:** `access.permitted_companies` returns `[]` for any role that is not HR Manager, HR User, System Manager or Administrator (`access.py:206-207`), so `employee_in_scope` refuses them - so **the documents section is HR-only in practice today even without SEC-3**. A tenant granting Positions read to an owners' role gets the page and the seat table, and a refusal on every mini profile and every document. That shrinks R1 materially. It is a consequence of a shared helper, not a decision anybody made, so it can change under us - F7 |
| SEC-4 | **Met** | `employee_documents_read.open_employee_document:150-180` runs the five checks in the required order - row shape, then `_guard` (page + scope), then parent, then ticked type, then plan. The browser is handed a **row id, never a file url** (`:126`). The honest half is in the module docstring (`:26-41`) with the full trace. The "hidden / protected / secure" wording assertion exists |
| SEC-5 | **Met, one clause short** | All nine keys are in `settings.ACCESS_GRANTING` (`:187-215`); `_set_access_setting` is System Manager only, logs the refusal under the slice-qualified rule id, writes one `Version` row naming key, old and new, and a structured security line. `people_settings.set_people_setting` is thin and hands over - nothing decides this twice. **Short clause:** nothing counts `Version` rows after a Cancel in the dialog. P3 |
| SEC-6 | **Met, with one widening** | `employee_photo._decode:122-138` is length-of-string → strict base64 → magic bytes, in that order. `_reencode:141-158` builds a new image from pixels only - no `exif=`, no `icc_profile=` - which is the strip. `_store:231-245` sets `is_private: 1`. The 48 px copy comes out of the **same** `_store` (`:290`). **Widening:** WEBP is accepted (`:99-119`) and SEC-6 named only JPEG and PNG. It is re-encoded like the others, so the stored artefact is identical; no test uploads one. P3 |
| SEC-7 | **Met** | Six-field constant (`people_fields.py:66-73`), all permlevel 0. `my_profile.save_my_profile:123-131` **refuses** an off-list key and logs it under `078-SEC-7` rather than dropping it quietly. Neither write endpoint takes an employee argument, so there is nothing a browser can post that reaches another person's record |
| SEC-8 | **Met** | `employee_photo._my_employee:341-343` filters `status = "Active"`. So does the self-check in `log_document_view` (`employee_documents_read.py:228`). `my_profile` uses the same helper. ERPNext does not disable a leaver's login; this filter is the whole control |
| SEC-9 | **Partly met - a recorded, decided deviation** | Verified: the token is Frappe's `Web Form Request` key, so **it is stored in clear** and SEC-9's "hash only" is not what was built. The narrowing is real: `_drop_request` (`joiner_invite.py:214-232`) deletes the row on submit, on cancel and in the daily job, so a clear key exists only while the link works. The fragment half is kept in full, and the parameter name `web_form_request_key` is load-bearing for Frappe's own log redaction. `purge_submission` remains untested |
| SEC-10 | **Met in code; one test missing** | **I disagree with the test report on one point.** It says `retry_after` appears nowhere. The retry time is not in `joiner_public.py` - it is in the shared limiter the endpoints are decorated with: `field_app_limits.py:79-81` refuses with `retry_after_s=_seconds_left(...)`. So the clause is met; what is missing is the functional test that exceeds a limit. The table test exists and reads `__alvoraa_limit__` off each function. P2 on the test, not on the control |
| SEC-11 | **Met in code; two tests missing** | `joiner_public.upload_invite_file:355-452`: token first (nothing stored before it), ticked type, file count `MAX_FILES_PER_TOKEN = 6`, running total `MAX_BYTES_PER_TOKEN = 20 MB`, string length before decode, strict base64, magic bytes, images re-encoded, PDF not re-encoded and served attachment-only, `is_private: 1`, attached to the **joiner doctype and never to Employee**. **Missing tests:** nothing asserts `is_private` or the attachment target, and neither ceiling is exercised. P2 |
| SEC-12 | **Met** | No code path creates an `Employee`. `_follow_the_employee` is declarative - HR links the record and that moves the status on. No joining date anywhere on the row (verified in the doctype's field list) |
| SEC-13 | **Met** | `_gone()` is one answer for missing, unknown, expired, cancelled **and for the feature being off** (`joiner_public.py:120-123`). The narrower "already used" goes only to somebody who held a live token. The test engineer verified it byte for byte |
| SEC-14 | **Met** | I read the doctype JSON: permissions are System Manager, HR Manager, HR User. **No Guest row.** The Web Form anchor is `published = 0` and `accept()` is never called, so Frappe serves no form of its own. Exactly three guest endpoints, all POST, and the enumeration test now reads Frappe's own `guest_methods` registry instead of a non-existent attribute |
| SEC-15 | **Partly met** | Verified: `<meta name="robots">` and `<meta name="referrer">` are in `www/joiner.html:6-7`; the page reads nothing about any invite; assets are inline. **The three HTTP headers are set inside a silent `except Exception: pass`** (`www/joiner.py:48-53`) and no Python test fetches the page. The test engineer proved the meta tags and the zero external assets in a browser. The headers remain unobserved. P2 |
| SEC-16 | **NOT MET** | **`joiner_public.py` holds five `ignore_permissions` in code; its ceiling is four.** §3.1. This is the gate doing its job |

### 2.2 Privacy

| ID | State | Evidence I checked myself |
|---|---|---|
| PRIV-1 | **Met in substance; Hindi unproved** | The notice is served with the panel (`my_profile.get_my_profile:93-98`) and - the part that makes it honest - it carries `photo_in_emails()`, so the sentence can stop claiming an email audience that does not exist. `people_settings.photo_in_emails` fails **closed** (`:268-274`), the setting ships **off** (`settings.py:176`), and our copies of the two reminder templates gate the photograph on it. So the widest new outbound surface is shut by default. Hindi parity is untestable in this environment |
| PRIV-2 | **Met** | `remove_my_photo:406-428` deletes both files with `delete_permanently`, clears the field, and clears the login's copy. Ten replace cycles leave two files, not twenty-one |
| PRIV-3 | **Met** | Static assertions over the real source tree, including that the two photo stores are never joined. The refusal is written down where a future slice will trip over it |
| PRIV-4 | **Met** | The mini profile is its own call. `thumbnails_for` is **one** statement for any headcount (`people_fields.py:181-196`), and `_cards_for` is one more. The chart draws the 48 px copy; only the drawer's enlargement reads the 512 px file |
| PRIV-5 | **Met** | `log_document_view:202-253` holds who, whose, which type, when - and nothing from the document. Three narrowings: only when there is something to look at, never your own, one row per viewer per type per day. The access log's permission rows are unchanged; only two `read_only` field properties were added |
| PRIV-6 | **Met as specified in `01c`; now short of counsel's 31 Oct ruling** | Real deletion, files included, bytes included (`alvoraa_joiner_submission.erase:92-144`). Legal hold wins, except HR purging on the person's own request. A count to the log. No value means "keep for ever". **But there is ONE clock, and counsel's ruling of today needs two** - §4.2(a) |
| PRIV-7 | **Partly met - the precondition was removed by decision** | The half that matters tonight **is met and I verified it**: `DEFAULTS["alvoraa_joiner_form_on"] = 0` (`settings.py:176`), `form_is_on()` fails closed on any error (`joiner_invite.py:68-81`), `require_form_on()` blocks invites, and `_open()` gives a dead-link answer to every guest call while it is off. The `Version`-row precondition is gone, because counsel answered on 29 Oct the question it existed for. That is a decision, not an oversight - and §4.2 says why what replaced it is now thinner than the risk |
| PRIV-8 | **Met except Hindi** | `open_invite` renders the **configured** periods, never a literal 90 (`joiner_public.py:197-199`), and **refuses to render with no HR contact** (`:180-186`). `_hr_contact` reads the tenant's own settings, then the tenant's Company email - never ours |
| PRIV-9 | **Met, and still the live control** | `JOINER_FIELDS` is exactly the seven: full name, mobile, personal email, current address, emergency contact name, relation, phone (`alvoraa_joiner_submission.py:32-40`). The page renders the server's list (`joiner.html:304`), and `submit_invite` writes only those seven, 500 characters each, dropping anything else silently so an error cannot confirm a guessed field name |

### 2.3 The addendum

| IDs | State |
|---|---|
| SEC-17, SEC-18, SEC-19, PRIV-10, PRIV-11, PRIV-12, PRIV-13, PRIV-14 | **Not applicable this release.** Deferred with the feature (Surbhi, 31 Oct 2026 evening). Nothing is built and nothing should be. They are not findings and they do not block tonight |

---

## 3 · What must be fixed before `dev`

### 3.1 P1 · A new permission bypass, and the counter that should have caught it

**Verified by running the gate's own logic locally** - pure Python over the files, no
bench, no container, no site.

`alvoraa_portal/alvoraa_portal/joiner_public.py` contains **five** `ignore_permissions` in
code; `test_portal_security_010.py:899` sets its ceiling at **four**. The assertion is
`assertLessEqual(count, ceiling)`, so this head fails
`test_sec16_ignore_permissions_does_not_grow`.

The fifth one arrived in `5ab76ebd` (defect fix D-3), in `_has_a_document`
(`joiner_public.py:205-213`) - the read that decides whether a joiner has already sent a
file, so an empty form can be refused without burning their link.

**Scenario:** nobody's data is exposed. The bypass itself is sound - a guest holds no
permission on `File`, and the read is bound to the token's own submission, with no
caller-supplied id anywhere in that module. **The failure is that an unargued bypass went
in unnoticed, which is exactly what SEC-16 exists to prevent, and it will make CI red.**

**Fix:** raise the ceiling to 5 and add the one sentence that names the fifth, the way the
other four are named. Do not delete the entry, and do not round the ceiling up for
headroom.

I re-checked **every** other 078 ceiling the same way. All nine match exactly:
`employee_photo` 3, `my_profile` 1, `positions_profile` 0, `employee_documents_read` 1,
`people_settings` 0, `joiner_invite` 4, `joiner_housekeeping` 6,
`alvoraa_joiner_submission` 4, `home_people` 0.

---

## 4 · The judgements asked of me

### 4.1 Is the company boundary genuinely proved?

**The control is real. The test is the right shape. I have not seen it pass.**

- **The control.** `employee_in_scope` → `permitted_employee_filters` → `permitted_companies`.
  A reader's companies come from User Permissions, else their own Active Employee's
  company, else nothing. Nothing means `NO_EMPLOYEES`, which matches no row - and it is
  never `{}`, for the reason written at `access.py:238-243`. Both new endpoints go through
  `_guard`, so both get the same answer. **A plain employee or plain manager gets nothing
  at all**, because `permitted_companies` returns `[]` for any non-HR role.
- **The test.** `test_company_scope_078.py` puts the out-of-company person in the **same
  branch** as everybody in scope, so company is the only difference. It asserts a
  **refusal**, not an empty answer, on the profile, the documents list and the document
  stream; that the refusal names no company, person, branch or type; that a refused read
  writes **no** access-log row; that a CXO reads both companies - which is what stops the
  four refusals passing merely because the data is unreachable; and that a reader with no
  company fails closed. It restores `frappe.local.response` after each stream. That is a
  well-built test.
- **What I cannot say.** The test engineer's run is in flight on `test078f` and I was
  instructed to run nothing. These nine tests landed at 20:47 today, and **no completed
  run has included them**. So: control verified in code, proof pending that run. If the
  run is red on this file, the slice is not ready.

### 4.2 Counsel's three rulings - must any be true before this code ships with the form off?

**I am not a lawyer, and I have not read counsel's written rulings - I am working from the
summary given to me. Labelled as such.**

**My answer: no. None of the three must be true tonight. All three must be true before any
tenant switches the form on, and two of them are one tick away from being needed.**

**(a) The document clock - 30-60 days for a non-joiner's identity documents, 180-365 for
the record.** We have **one** clock, and it deletes the fields and the files together
(`erase:119-138`). The shipped numbers are `not_hired_days` 180 (range 180-365) and a
`backstop_days` 90 for a submission nobody actioned. So as built, a non-joiner's identity
documents would be kept **90 to 180 days** - outside counsel's 30-60 day window for
documents. **Correctly deferred tonight,** because with the form off no document exists.
**Not deferrable past switch-on.** The two-clock change is small - a second cutoff in
`joiner_housekeeping` that deletes only the `File` rows, plus one setting - but it is new
code and it belongs in the deferred slice, not in a Friday night release.

**One correction to the brief I was given:** the retention period is **not** unset.
Counsel answered on 29 Oct and the code carries dated, counsel-backed defaults
(`settings.py:109-136`). That is better than unset for the record, and it is the reason
the *document* gap is now the live one.

**(b) Every export logged; unmasked exports restricted.** Half built, half open.

- Our own purpose-built export **is** logged: `export_submission` writes an `alvoraa` log
  line with the row, the actor and the time, and it deliberately lists files by name and
  date **without their bytes** (`joiner_invite.py:237-272`). Good.
- **But the doctype grants `export: 1` and `report: 1` to HR Manager** (verified in the
  doctype JSON). So an HR Manager can also pull every joiner row - name, mobile, personal
  email, home address, emergency contact - out of a Desk list view or Report Builder,
  unmasked. **Whether Frappe writes its own Access Log row for that, I could not check:
  Frappe's source is not in this worktree and I was told to run nothing.** That is the
  access I would need - one read of `frappe/desk/reportview.py` and
  `frappe/core/doctype/access_log/` in the image.
- **Tonight this cannot happen, because with the form off there are no rows to export.**
  Before switch-on, the cheapest fix is to drop `export` from the HR Manager row - they
  already have the purpose-built, logged button - which is one line of JSON and one test.
  I recommend that over researching Frappe's logging.

**(c) The notice belongs to the employer, naming their purpose, periods and HR contact.**
Mostly already true, which surprised me until I read it: the joiner notice renders the
**tenant's** configured periods and the **tenant's own** phone or email, and **refuses to
render at all** with no contact (`joiner_public.py:180-186`, `_hr_contact:216-241`). What
is still ours rather than the employer's is the **wording**, purpose included. That is a
real gap against counsel, and it is correctly deferred with the feature. The **employee
photo** notice does ship tonight and is also our wording; it states a purpose and an
audience and asserts no retention period, so it is not a misstatement. A notice the
employer authors is a slice of its own. P3.

**What I would do about (a) and (b) before `main`.** The feature ships off, but
`alvoraa_joiner_form_on` is a tick in a dialog a System Manager can make without us, and
after that tick both gaps are live within a working day. My own rule says a prohibition
enforced by instruction is not a control. **The proportionate answer is about five lines:
refuse `alvoraa_joiner_form_on = 1` in `_set_access_setting`, with the plain message
"Asking joiners for documents is not ready to switch on yet", plus one test.** It is the
same shape as the precondition PRIV-7 used to have, the deferred slice removes it in one
line, and it costs nobody anything - nobody is enabling this feature this week.
**If Surbhi would rather not add code tonight, the alternative is an acceptance in
writing, with her name and today's date, that the switch stays off at every tenant until
the document clock and the export restriction exist.** Either is governance. Neither being
present is not.

### 4.3 The private-file download path, and the tripwire

**It still reads the way it did.** `employee_documents_read`'s docstring (`:26-41`) carries
the full trace - `app.py` → `utils/response.py` → `file/utils.py` → `file.py:896` →
`file.py:989`, where the decision is Administrator, not private, owner, DocShare, then the
**parent's** read - and `frappe/permissions.py:483` as the only place the `has_permission`
hook is read, which that path never enters. The diff adds **no** `has_permission` hook and
**no** `permission_query_conditions`, which is correct: a hook on a child table is always
False (ALV-256).

**Label: Inference, not verified by me.** Frappe's source is not in this worktree and I ran
nothing. I am relying on DevOps' read of the running image and the engineer's trace.

**The tripwire is NOT written down where a future reviewer would find it.** I checked:
`docs/security/` holds only `whitelisted-endpoint-review.md`, and neither
`.claude/context/compliance-feature-map.md` nor `security-compliance-baseline.md` mentions
078 at all. So the accepted risk and its tripwire live in a module docstring and in this
slice folder - findable by us, invisible to somebody answering a customer questionnaire in
six months. **That is my own file and my own gap.** One row in the feature map fixes it.
F6, P3, mine.

### 4.4 `thumbnails_for`'s `ignore_permissions=True` - my own conclusion

**Sound, and I would not change it.** Three reasons, in order:

1. **The bypass lifts a `File` permission only.** No employee holds read on `File`, and
   `Employee.image` and its 48 px copy are `File` rows. Without the bypass the chart would
   draw initials for everybody - the control would be removed by its own side effect.
2. **The key is not caller-supplied.** `thumbnails_for(employees)` is handed the list the
   caller has **already** been authorised to see - the reach-scoped tree walk, or one
   employee `_guard` has just approved. There is no filter a browser can post into it, and
   it returns **only** `{employee: url}`. It cannot be used to enumerate, because you must
   already know the names.
3. **What it returns is a private url.** Verified in code: both copies are written by one
   `_store` with `is_private: 1` (`employee_photo.py:231-245`).

**The one honest caveat.** A private url is still served by the parent-permission path in
§4.3, and most employees hold read on `Employee`. So an employee handed a 48 px url by
some other means could fetch it. The person it would show is somebody the company-wide
staff directory already shows them (slice 045). Same unfixable path, materially smaller
prize. F10, P4 - noted, not worth code.

### 4.5 The 48 px thumbnail is pinned private - claim verified

`3eda205a`'s claim is **true of the code**: there is one `_store`, it sets `is_private: 1`,
and `derive_thumbnail:290` goes through it.

**And the test as committed in `3eda205a` was wrong** - it read `THUMB_FIELD` as a column
on `Employee`, which it is not (it is the `File` row's `attached_to_field`). That would
have errored rather than asserted. **It was fixed in `623d0347`**, and the version in the
tree now reads the `File` rows exactly the way `thumbnails_for` does, asserting
`is_private = 1` on each. Good catch by the test engineer, and worth saying out loud: a
test that errors is not a pin.

### 4.6 Personal data in logs, on the new code

**Clean. Verified by reading every call.** I read all sixteen `logger` / `log_error` calls
in the new modules, the ones the defect fixes added included. They carry row ids,
`frappe.session.user`, byte counts, document **type** names, counts and timestamps.

- `joiner_public:341` - the submission id and the time. No field, no name, no key.
- `joiner_public:455` - the row, the **type name**, the byte count. Not the bytes, not the url.
- `joiner_invite:181` - the submission id, the actor, the link length in days. **Never the key.**
- `my_profile:160` - the record and a **count** of changed fields. Never a value, which
  matters: those values are a mobile number and a home address.
- `employee_documents_read:196` - the row, the employee, the actor. No document number.
- `joiner_housekeeping:73,210` - counts only.
- Every `log_error` names a row id and what failed.

One nuance to state rather than hide: `frappe.session.user` is an email address. That is
the **actor** identifier, it is what PRIV-5 requires, and it is this product's established
pattern. Not a finding.

**One worry, in §6 rather than here:** `my_profile` writes a `Version` row whose `data`
holds the **old and new values** of the changed fields - a mobile number, a home address,
an emergency contact. That is deliberate and needed ("who changed my emergency contact"),
and it follows `settings.py`'s pattern. **I could not check who may read `Version`.**

### 4.7 `daca7224` - the gate was strengthened, not weakened

**It still checks what it claims, and it checks more than before.**

- `MIN_CALL_SITES` went **200 → 201**. Up, not down. The docstring's real count went
  220 → 226, so the headroom between reality and the floor **shrank** from 20 to 5. A
  tighter floor, not a looser one.
- The change **adds** a shape - a raw `fetch` to a literal `/api/method/...` path, reading
  the argument names out of the `JSON.stringify` in its body. The one new site found,
  `open_employee_document({ row })`, is now argument-checked against
  `open_employee_document(row=None)`.
- It did **not** take the cheap route. The test report had suggested listing the endpoint in
  `NO_ARG_CALL`, which would have made CI green and left a new endpoint on the **documents**
  path permanently unchecked. That would have been the downgrade. It was refused, and the
  docstring now says plainly what the reader still cannot read.
- One honest limit, pre-existing: a site whose arguments cannot be read is recorded with
  `keys = None`, skipped by the argument assertion, and still counted toward the floor. So
  a dynamically built body inflates the count without being checked. The docstring says so.
  F11, P4.

---

## 5 · Findings, ranked

| # | Level | Urgency | Finding | Where |
|---|---|---|---|---|
| F1 | **Blocker** | **P1 - blocks `dev`** | A fifth `ignore_permissions` in `joiner_public.py` against a ceiling of four. SEC-16 not met and CI red. The bypass is sound; the accounting is not | `joiner_public.py:213`, `test_portal_security_010.py:899` · §3.1 |
| F2 | Major | **P2 - before `main`, or accept in writing** | Nothing in the code stops a System Manager switching the joiner form on, and after that tick counsel's document clock (30-60 days) and the export restriction are both breached within a day. The only control today is an instruction | `settings.py:176` + `_set_access_setting` · §4.2 |
| F3 | Major | **P2 - before switch-on** | `Alvoraa Joiner Submission` grants `export: 1` and `report: 1` to HR Manager, so an unmasked Desk export of joiner data exists beside the logged one. No rows exist tonight | doctype JSON permissions · §4.2(b) |
| F4 | Minor | P2 | SEC-11's ceilings (`6` files, `20 MB`) and the `is_private` / attachment target of a joiner file are asserted by no test. All are correct in code | `joiner_public.py:78-81, 443-452` |
| F5 | Minor | P2 | SEC-15's three HTTP headers are set in a silent `except Exception: pass` and no test observes them | `www/joiner.py:48-53` |
| F6 | Minor | P3 | The R1 tripwire and the private-file limit are recorded only in a docstring and this slice folder - not in `docs/security/`, and `compliance-feature-map.md` has no 078 row at all. **My file, my gap** | §4.3 |
| F7 | Minor | P3 | The documents section is HR-only today only because `permitted_companies` returns `[]` to non-HR roles. That is a consequence of a shared helper, not a decision. If the helper ever softens, SEC-3's declined risk becomes live with no warning | `access.py:206-207` |
| F8 | Minor | P3 | WEBP is accepted by the photo upload beyond what SEC-6 named, and no test uploads one | `employee_photo.py:99-119` |
| F9 | Minor | P3 | No test counts `Version` rows after a Cancel in the settings dialog (SEC-5's last clause) | - |
| F10 | Note | P4 | A 48 px url, once held, is still served by the parent-permission path. Same person the staff directory already shows | §4.4 |
| F11 | Note | P4 | The arguments gate counts a call site it cannot read toward its own floor | §4.7 |

**Nothing I found is a P0.** No cross-tenant leak, no permission bypass, no secret or
statutory id in a log, no personal data reaching a model.

**Can follow the release:** F6 to F11.

### The opposite failure - did the slice build surface it did not need?

I checked for this deliberately, because unneeded surface is a security finding.

- **One new public route** (`/joiner`), and it renders even when the feature is off. It
  discloses the tenant's name and colour, both already public on its login page. Accepted.
- **Three guest endpoints, and exactly three** - now asserted against Frappe's own
  registry. J4's photograph reuses `upload_invite_file` under a reserved type name rather
  than adding a fourth.
- **One scheduled job.** No queue, no worker, and no cache across requests - the card cache
  is per request, deliberately, so the chart cannot keep drawing a face somebody removed.
- **No new copy of personal data.** The 48 px file is a derived copy, deleted with its
  original; `erase` takes the files with the fields.
- **Surface removed, not added:** `www/joiner.py` dropped a settings read no template used,
  on the most attacked page in the product.

That is a lean slice. I have nothing to subtract from it.

---

## 6 · Worries - not findings

Each of these I cannot yet write as *this actor, in this state, calling this path, sees
this data*.

1. **Who may read a `Version` row.** `my_profile` puts a mobile number and a home address
   into `Version.data`. I could not check Frappe's `Version` permission rows, nor how the
   Desk timeline fetches them. *Access I would need:* a read of
   `frappe/core/doctype/version/version.json` and `frappe/desk/form/load.py` in the image.
   A pre-existing pattern, not introduced by this slice's shape.
2. **Whether a Desk list export is logged by Frappe itself** (§4.2(b)). Same access.
3. **A private file url in an email body.** If a tenant ticks `alvoraa_photo_in_emails` on,
   the reminder template puts a private url into the mail. Most recipients will see a broken
   image, and the url travels the mail path. Upstream behaviour, off by default, not changed
   by us - but somebody will report it as a bug one day.

---

## 7 · What must exist for these controls to be observable

Lesson 1 of slice 028. The test engineer's `fixtures_078.py` builds what §9 of `01c` asked
for - a GPS-carrying PNG, employees with and without a photograph, documents of a ticked
and an un-ticked type on employees inside and outside scope - and `c5494a29` adds a second
**company** and a CXO login. §11 of the test report walks which result was produced with
which fixture present.

**So "0 findings" from this suite is not empty tonight.** One caveat stands: none of this
slice's controls can be observed on the demo tenant, where 6,469 `Employee Document` rows
have 0 attachments and 0 of 403 employees have a photograph. A browser check there proves
nothing about any of this.

---

## 8 · Residual risk - tonight, as distinct from the deferred feature

### 8.1 What Surbhi carries tonight, with the form off

| # | Risk tonight | If it happens | Owner | Accepted | Label |
|---|---|---|---|---|---|
| T1 | **The first photograph makes a face real on ten existing surfaces at once**, the widest being the company-wide staff directory. Authorised in slice 045 when the field was always empty | P2 - authorised, but nobody had looked since the data became real | Surbhi | 31 Oct 2026 | **Acceptable simplification.** PRIV-1's sentence is the condition, it is in the build, and the email surface is **off** by default |
| T2 | **A private file url, once held, is still served against the parent's read permission.** Smaller than `01c` feared: the two new readers refuse every non-HR role today | P2; P1 only if a tenant widens Positions read **and** `permitted_companies` ever softens | Surbhi | 31 Oct 2026 | **Intentional trade-off.** Tripwire in code, not yet in `docs/security` (F6) |
| T3 | **A wrong tick on the settings card is found only by somebody reading the page.** One-click removal was refused | P2 | Surbhi | 31 Oct 2026 | **Intentional trade-off.** The amber line naming the actual roles is the only detection, and it is built and tested |
| T4 | **The document-open record has no retention**, like the photo access log beside it | P3 | Surbhi | 31 Oct 2026 | **Temporary debt** |
| T5 | **No break-glass control over the sites volume.** Bench access reads every photograph | P2 | Surbhi | standing, unchanged | **Intentional trade-off** at this size |
| T6 | **A new public route exists at every tenant**, serving a page whose feature is off | P3 | Surbhi | 31 Oct 2026 | **Acceptable simplification** - brand only, and the endpoints answer a dead link |
| T7 | **The breach runbook has still never been drilled**, and this slice is the first inbound public write path - even switched off, the route exists. CERT-In's clock is 6 hours from awareness | P1 on the day it matters | Surbhi | standing | **Temporary debt.** One drill removes it |

### 8.2 What belongs to the deferred feature, not to tonight

| # | Risk | Becomes live when | Label |
|---|---|---|---|
| D1 | **One retention clock where counsel's ruling needs two.** A non-joiner's identity documents would sit 90-180 days against counsel's 30-60 | the form is switched on at any tenant | **Dangerous debt - escalate now.** It does not sit quietly: it is F2, and the five-line switch guard or a written acceptance is the ask |
| D2 | **An unmasked, possibly unlogged Desk export of joiner data** | the form is switched on and rows exist | F3 |
| D3 | **The joiner notice is our wording, not the employer's** | the form is switched on | **Temporary debt**, removed by the deferred slice |
| D4 | **No malware scanning on an upload from an unauthenticated caller.** Type allow-list, magic bytes, size ceilings, private storage, attachment-only serving - and no scanner. Do not claim scanning in any questionnaire | the form is switched on | **Intentional trade-off** |
| D5 | **`purge_submission` is untested**, and it is the path that erases on a person's own request with `force=True` | the form is switched on | **Temporary debt** |

**Nothing in the addendum is residual risk.** It is unbuilt work on a deferred slice.

---

## 9 · Subtract pass

Read back once, asking only what I could delete.

**Removed:** a proposed new CI gate for "an access-granting key changed without a `Version`
row" - `ACCESS_GRANTING` already does that, and a fifth gate nobody reads is worse than
four that fail honestly. Two further worries about the joiner page's caching and gzip -
DevOps measured both and neither changes a control. A recommendation to re-verify the
compliance baseline tonight - it is 68 days old, inside the 90-day window, and re-verifying
DPDP on a Friday evening would delay the release without changing one finding. A
per-finding "which test proves it" table duplicating the test report - I cite it instead.

**Kept, deliberately:** §4.7 on the arguments gate, even though the answer is "it is fine".
A gate that was touched and not checked is how a control decays quietly, and "I looked, and
it is stronger" is worth writing down once.

---

## 10 · What I could not verify tonight

Said plainly, because each is a finding of its own.

1. **I ran no test.** The test engineer's full suite is in flight against `test078f` in
   `hrlocal-078`, and a second run would destroy a pass nobody has completed. So every
   "Met" above is *verified in code* at a cited line, except §3.1 and the ceiling sweep,
   which I verified by running the gate's own logic as plain Python over the files.
2. **The nine company-scope tests have never been part of a completed run** (§4.1).
3. **Frappe's source is not in this worktree.** So the private-file path (§4.3), the
   `Version` permission (§6.1) and whether a Desk export is logged (§6.2) are Inference or
   Unknown, not verified. *Access I would need:* a read inside the bench image.
4. **I have not read counsel's written rulings of 31 Oct 2026.** I worked from the summary
   given to me, and I have labelled it.
5. **DTC's actual `Custom DocPerm` rows for `Alvoraa Position`** are on production. I did
   not and will not look.
6. **Hindi parity** for PRIV-1 and PRIV-8 cannot be proved in this environment.

---

## 11 · Recommendation

- **Before `dev`:** fix F1. One number and one sentence.
- **Before `main`:** decide F2 - the five-line switch guard, or an acceptance in writing
  with a name and today's date. Optionally take F3 at the same time; it is one line of JSON
  and a test.
- **After:** F4 to F11, each with an owner and a date.
- **Not tonight, and say so to anybody who asks:** the pre-onboarding feature is built and
  switched off. It is **not ready to be switched on at a tenant with real joiners**, and
  the reason is counsel's document clock, not the quality of the code.

**A Blocker from me blocks the slice. F1 is a Blocker. What happens next is Surbhi's call,
not mine.**
