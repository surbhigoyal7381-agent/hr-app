---
slice: 088-register-notice-and-forms
artifact: 02-functional-spec
author: hrms-business-analyst
date: 2026-11-21
risk tier: 1 (pay gate, personal data, a photo kept for years, retention)
status: draft for Surbhi. Recommendations are proposals. Nothing here is a legal ruling; I am not a lawyer.
inputs: 01-product-brief (with gate), 01a, 01b (with design gate D-1..D-4, parity P-6..P-8), prototype-v1.html, 01c (SEC-1..11, PRIV-1..6, C1..C3, R1..R8), 07 §1-§3 (OPS) and Surbhi's decisions at its end, 087's 02-functional-spec ("Confirm redesigned") and 01b v5
---

# 088 · The monthly change notice: functional spec

## 0 · Read this first

**Bad news first.**

1. **088 stands on 087 code that does not exist yet.** The 087 branch (`slice/087-attendance-follows-punches`, HEAD `70633e2a`, read this session) still holds the older ALV-419 rule: `refuse_unconfirmed` blocks approval until the employee confirms (`punch_fix.py:653`). The "Confirm redesigned" rules (approval never waits, slip blocked, register signature) are in 087's **spec only** (`02-functional-spec.md:813-826`, 15 lines). A search for `record_register_signature` in the 087 tree at `70633e2a` finds **nothing**. So the seam below is a **contract I define here, not code I read**. Marked [UNVERIFIED] where it matters. Build order is 087, then 088 (OPS-27).
2. **The brief and 01b say "if the tenant's 087 gate is on". No such switch exists.** I searched 087's spec: the only switch there is `alvoraa_hold_odd_punch_days` (AC-48), and 087 dropped a per-company switch (spec line 719). The slip block is always on. I **drop the "gate on" condition** (decision D-5).
3. **The notice prints HR's name. 087 decision 7 says the employee sees "HR" with no name** (087 `01b-ux-design.md:143, 159, 339`; "counsel was still to confirm"). The approved 088 prototype prints "Anil Sample, HR". This reverses an earlier decision for the employee. **Needs Surbhi's explicit yes** (OQ-1). I build the approved prototype unless she says no.
4. **Release is blocked on counsel (C1 thumb print, C3 one photo per page) and on Hindi review (D-1).** Not the build. Hindi is not built (Surbhi, 21 Nov): the paper is English only.
5. **No test for any of this exists yet.** Every AC below is a claim to be tested. The traceability table says "AC-n (test to be written)", never "test exists".

**Counts:** 10 stories (31 points), 63 acceptance criteria, 8 decisions I made (D-5 to D-12), 5 open questions for Surbhi.

## 1 · Cross-module reach

| Area | Touched? | How |
|---|---|---|
| `alvoraa_portal` | **Yes, all of it** | one new module `register_notice.py`, one new DocType and two child tables, one custom field, a card on the HR Attendance page, a small line on the employee month view |
| `hrms` | Read only | `alvoraa_hr_core/access.py` (`permitted_employee_filters`, `employee_in_scope`, `refuse`), read this session in this worktree |
| `erpnext` / `frappe` | Read only | Attendance Request, File (`content_hash`), `rate_limit`. No core change |
| `alvoraa_goals`, `alvox_compensation` | No | |
| 087 (not on dev) | **Depends** | the seam (§8.5); 088 branches from 087's final SHA, rebased, never merged |
| HRMS domains | Attendance (the changes), payroll (the slip block reads what 088 records) | leaves, appraisals, goals, compensation, org structure, learning: not touched |

**Personas:** HR Manager and HR User in scope (print, record); **Employee with no app** (holds the paper; no screen); Employee with the app (one list); line manager and CXO: **nothing** (permission matrix §6 states the negatives).

## 2 · The ask, questioned

- **Symptom or cause?** The brief ties the need to counsel's condition 3 ("staff who don't use the app get a monthly register notice") and to a real harm: a floor worker finds out her day was changed only when pay is short. That is the cause, not a symptom. **Confirmed fact (stakeholder statement):** the driver is counsel's reply of 21 Nov, relayed, unsigned.
- **What decision does it drive?** HR decides whether a slip can be submitted. The notice **acts**: signing unblocks the slip through 087's gate. It is not a display.
- **Automating chaos?** The paper process exists already in the customer's shop. We make one page per person instead of a shared register.

## 3 · Gap analysis (what exists, what does not)

Looked in: `alvoraa_portal/alvoraa_portal/` (worktree 088, dev `bad23ce0` base) and 087's `punch_fix.py` at `70633e2a`; the 01a/01b scans found no print format or register output in `alvoraa_portal`. **Not checked by me:** `hrms/` print formats (01b also did not search).

| Requirement | Today | Verdict | Cost |
|---|---|---|---|
| One A4 notice per person, filtered, logged | No print format or register output (01a). A Frappe print format is per document, cannot filter by month and filer, and cannot log "who opened it" before content leaves (SEC-2) | **Build new** (one portal module, browser print, no PDF engine) | M |
| The list of people with changes | 087 draws "Before payroll" on the HR page; its code is not yet built | **Extend** the same HR Attendance page: one card | S |
| Print log + signed-page photos + coverage list | `Alvoraa Photo Access Log` is a log of *views*, HR Manager can read and export it (`alvoraa_photo_access_log.json` permissions). `Alvoraa Notice Acknowledgement` is the app privacy notice. Attendance Request is readable by the employee and the manager (01c §0.1) | **Build new**: one DocType `Alvoraa Register Notice` + 2 child tables. One sentence: no existing record is HR-in-scope-only, one-per-print and able to hold many changes and many photos | M |
| Record "signed" on each covered change | 087's confirm fields (`alvoraa_confirmed_by/on`) mean "the employee pressed Confirm in the app" (`punch_fix.py:62-69`) | **Configure** one new custom field on Attendance Request, `alvoraa_signed_notice` (Link). Why not reuse `confirmed_on`: the employee's own screen must say "You signed for it on the register", a different sentence | S |
| Photo upload checks | `employee_photo.py`: 512 px edge (`STORED_EDGE`), wrong for a page (01c §0.3, 07 §2). `expense_evidence.py`: 1,600 px, 1 MB, 12 MB raw, JPEG/PNG, `EDGE = 1600` (lines 105-131) | **Extend**: call 081's decoder and caps; do not copy them | S |
| Open a photo by permission, logged | `expense_evidence.open_evidence` streams after the parent's read check and logs a view (`expense_evidence.py:625-700`) | **Extend**: same pattern, one function, no screen | S |
| Row filter on the log | `permission_query_conditions` in `hooks.py:604-614` has no entry for `Alvoraa Photo Access Log` | **Extend**: add one entry (SEC-10) | S |
| Scope by company and branch | `permitted_employee_filters`, `employee_in_scope` (`hrms/alvoraa_hr_core/access.py`, defs at lines 238-345 area) | **Reuse as is** | none |
| Rate limits | `field_app_limits.py` wraps Frappe `rate_limit`; `expense_evidence._limited` | **Reuse** | none |
| Tenant "gate on/off" for the pay line | **None exists** (087 spec) | **Drop** (D-5) | none |
| Hindi lines on the paper | Machine draft only | **Drop for now** (Surbhi, 21 Nov, decision 3). No setting, no flag | none |
| `retain_until` date (OPS-18) | n/a | **Drop**: 01c PRIV-4 says store employee and month so a later purge can compute the date; Surbhi's decision 5: nothing is deleted until counsel answers, so a date nobody chose is a guess | none |
| PDF engine, daily job, payslip lines, store-manager printing, reminders, CXO tiles, a photo viewer screen, statutory forms | not asked / 088b | **Drop** | none |

## 4 · Process flow

1. HR opens the **Change notices** card on the HR Attendance page, picks a month (default: this month).
2. The server lists people (in HR's scope) with at least one open qualifying change (§5.1). **Decision point:** none for this month, then "No changed days in {month}".
3. HR presses **Print notice** (one) or ticks several and presses **Print selected** (up to 100). The server writes one `Alvoraa Register Notice` per person, **then** returns the content. **Unhappy path:** the write fails, then no content, "Could not open the notices. Nothing was printed."
4. The preview shows one A4 page per person (5 changes per page, more pages as needed). HR presses **Print**. The browser's own print window opens.
5. The worker reads (HR may read it aloud), tells HR if it is wrong, signs or presses a thumb.
6. **Decision point:** a) it is right: HR presses **Signed on the register**, adds one photo per page, **Record signature**. b) The worker says it is not right: HR presses **Says it is not right**, writes what the worker said, **Record that it is not right**.
7. a) Each covered change that is still unchanged since the print is marked signed; the slip block (087) lifts for it. b) Nothing is marked; the changes stay open; the row shows the worker's objection.
8. **Unhappy paths:** a change is filed or edited after the print (stays open, row warns); HR is the filer of a covered change (cannot record, another HR person does); a blurry, reused or wrong-size photo is refused; the network drops while recording (photo kept in page memory, "Not saved yet. Try again").

## 5 · Business rules (the numbers and the words)

### 5.1 Which changes are on a notice

A change is on the notice for employee E, month M if **all** hold (`[UNVERIFIED: field names from 087 punch_fix.py at 70633e2a; the engineer re-reads them on 087's final SHA]`):

| Test | Field / source |
|---|---|
| It is a punch fix | `punch_fix.is_punch_fix(doc)` (`punch_fix.py:114`) |
| It is Approved | `docstatus = 1` and status Approved. `alvoraa_fix_after` (the day after the fix, which gives "now counts X h Y m") is written only at approval (`punch_fix.py:806`) |
| It was filed by someone else | `owner` is not E's `user_id` and not `Administrator` (087's break-glass account is not "a person filing for somebody", AC-104) |
| It falls in M | `from_date` in M (a punch fix is one day) |
| It is **open** | not confirmed in the app (`alvoraa_confirmed_on` empty) **and** `alvoraa_signed_notice` empty |

Declined, cancelled and Waiting changes are not on the notice (D-6: "now counts" is only true after approval). HR-filed, manager-added and manager set-asides are all on it (design gate D-4). A person is on the list if they have at least one such change. A person with every change confirmed or signed shows **done**, with no tick box.

### 5.2 The sheet (English only)

- One person per page. Pages hold up to **5 changes**, in date order; the **server** decides which change is on which page and stores it (`page_no`). Every page stands alone: company name, reference, title, name, employee number and branch, intro, the changes, the rule box, the read line, the sign box (26 mm), the date box, the footer ("Printed by {user} on {date}. Page {n} of {m}." and "This page is only about you. Keep it private.").
- Per change: day ("Fri 13 Nov", real weekday), what changed (four templated sentences: "Out time {t} added", "In time {t} added", "Back after break at {t} added", "Scan at {t} not counted"), "This day now counts {h} h {m} m." (valid hours only), who filed it (name and role, "HR" or "Manager"), the filer's reason as written, in full.
- **Reference:** `{employee}/{YYYY-MM}/{page}-{pages}` as drawn, **plus the print number** (the notice record's name, e.g. "No. RN-00012") so a reprint can be told from the page before it (parity P-9, needs Surbhi's yes).
- **Pay line** ("Your salary slip for this month waits until each change is confirmed."): printed on a sheet **only if that sheet holds at least one change with `alvoraa_needs_confirm = 1`** at print time (D-5, D-7). **A sheet holding only manager additions does not print it** (the designer's open point, decided): a manager addition does not block the slip (087), so the sentence would be false. The read line and sign box still print.
- **Never on the sheet:** another person's data, HR's review note (`alvoraa_review_note`), a leave or absence reason, pay amounts, punch photos, GPS, scans the system did not count.
- The paper is generated in **English whatever the user's screen language**. The screen strings are translatable (`_()`).

### 5.3 The states of a row

| State | Computed from | Words (01b §3) | Buttons |
|---|---|---|---|
| Not printed | no notice for this person and month covers an open change | "Not printed yet" | Print notice |
| Printed | latest notice has outcome Printed and covers every open change | "Print opened on {d} by {name}. Waiting for the signature." | Signed on the register, Says it is not right, Print again |
| Changed after printing | an open change is not in the latest notice, or its content differs from the stored hash | amber triangle + "{n} change added after the page was printed. It is not on that page. Print again." | Print again |
| Not right | latest notice outcome "Not right" and a covered change is still open and unchanged | "{name} says it is not right (told HR on {d}, recorded by {name}). The changes stay open: ..." | Print again |
| Signed / confirmed | every change confirmed in the app or `alvoraa_signed_notice` set | "Signed on the register on {d}. Recorded by {name}." or "Confirmed in the app." | none |
| Filer | recorder would be the filer of a covered change | "You filed a change on this page, so another HR person records the signature." | Print again only |

"Print opened" means the server released the content (SEC-2), not that paper came out.

## 6 · Permission and visibility matrix

**Record type:** `Alvoraa Register Notice` (new) with child tables `Alvoraa Register Notice Change` and `Alvoraa Register Notice Page`.

| Role | DocType rows | Create | Read | Write | Delete | Export / report | Row rule |
|---|---|---|---|---|---|---|---|
| HR Manager | notice | **No** (only through the 088 calls) | Yes | No | **No** | **No** | `permitted_employee_filters` (company, then branch) via `permission_query_conditions` and `has_permission` hook |
| HR User | notice | No | Yes | No | No | No | same |
| System Manager | notice | No | Yes | Yes (to correct a wrong photo; Version records it, Q1 default) | **No** (delete refused in code) | No | every company |
| Employee, line manager, CXO, Biometric Sync, any other role | notice | No | **No** | No | No | No | no role row at all |

**Roles on the calls:** list, open notices, record signature, record "not right", open photo: HR User, HR Manager, System Manager, in scope (SEC-1). Employee's own list: any Active employee, own record only (`_me`, Active only).

**Negative cases, stated:**
- An employee and a line manager cannot list, preview, record or open a photo, and cannot fetch `/private/files/...` for it (the photo's parent refuses them; SEC-8).
- HR in company B, or in branch 2 when scoped to branch 1, or with no company permission: refused on every call.
- The filer of a covered change cannot record the signature or the objection; nobody records their own notice (even after leaving).
- **No one** can export the photo or the record: not a report, a list view, an email, a notification, the Inbox or an API list.
- HR Manager of company A cannot list company B's rows in `Alvoraa Photo Access Log` after SEC-10.
- Count of roles: **3** can read the notice (HR User, HR Manager, System Manager). All others: 0.

## 7 · Data model

All verified against source unless marked. The custom-field mechanism follows `punch_fix.FIELDS` and `after_migrate` (`punch_fix.py:41-95`).

### 7.1 New DocType `Alvoraa Register Notice` (one record per person per print)

| Fieldname | Type | Req | Notes / why no existing field |
|---|---|---|---|
| `employee` | Link Employee | yes | |
| `employee_name` | Data, fetch | | for lists |
| `month` | Date (1st of month) | yes | |
| `printed_by` | Link User | yes | who released the content |
| `printed_at` | Datetime | yes | |
| `page_count` | Int | yes | pages in this print |
| `outcome` | Select: Printed / Signed / Not right | yes, default Printed | read by the row state and the audit |
| `recorded_by` | Link User | | set once |
| `recorded_on` | Datetime | | set once |
| `dispute_reason` | Small Text | | `depends_on: outcome == "Not right"`; required there |
| `changes` | Table → `Alvoraa Register Notice Change` | yes | `request` (Link Attendance Request), `page_no` (Int), `content_hash` (Data: SHA-256 of the values of `punch_fix.CONFIRMED_CONTENT`, `punch_fix.py:41`) |
| `pages` | Table → `Alvoraa Register Notice Page` | | `page_no` (Int), `photo` (Attach, private), set when signed |

- Naming: series `RN-.#####`. `track_changes = 1`. Never contains the reason text, the hours or any change content (OPS-20).
- Controller refuses insert unless a process flag set by the 088 call is present (a client cannot send it), refuses delete for every role, refuses edits to `printed_by/at`, `changes` and, once `outcome` is Signed or Not right, to `outcome`, `recorded_by/on`, `dispute_reason` and `pages` (SEC-5).
- Index on (`employee`, `month`) (OPS-21).
- Photo files: private File attached to this record, **generated** file name that names no person (081-PRIV-2).

### 7.2 One custom field on Attendance Request

`alvoraa_signed_notice` · Link `Alvoraa Register Notice` · read_only · `insert_after: alvoraa_replaces`. Created by 088's own `after_migrate` hook entry with the `columns_ready()` pattern (`punch_fix.py:89`). **Why not an existing field:** `alvoraa_confirmed_*` mean the employee pressed Confirm (§3). Signer and date are read from the linked notice (`recorded_by/on`), not copied. Written only under the process flag and put back on every other save (§8.5, AC-30).

### 7.3 Existing DocType edited

`Alvoraa Photo Access Log.source` gets the option "Register signature photo" (current options read from the json: Check-in photo, Employee document, Expense bill, Day-fix evidence, Joiner export (masked), Joiner export (not masked), Joiner purge). Row filter added in `hooks.py` `permission_query_conditions` (SEC-10).

## 8 · Calls (all `@frappe.whitelist(methods=["POST"])`, CSRF token rendered on the page; SEC-11)

Names are proposals.

| # | Call | Does | Limit (OPS-22, `[ESTIMATE]`) |
|---|---|---|---|
| 8.1 | `register_notice.list_people(month, start)` | name, number, branch, count of changes, state. No reason, no change detail (SEC-2). 25 per page, "Show more" | 60 / min / user |
| 8.2 | `register_notice.open_notices(employees, month)` | ≤100 people. For each: writes the notice record, then returns the content. Insert fails, content refused | 10 / min / user |
| 8.3 | `register_notice.record(notice, outcome, photos=None, reason=None)` | SEC-3, 4, 5, 6, 7; all or nothing | 20 / min / user |
| 8.4 | `register_notice.open_photo(notice, page)` | streams one photo after the notice's read check, writes one view row; **no screen calls it in 088** | 60 / min / user |
| 8.5 | the 087 seam | below | n/a |
| 8.6 | `register_notice.my_changes(month)` | the employee's own days, Active only | 60 / min / user |

Rate-limit keys: the user, never the IP (a store shares one address). Refusal text holds no personal data.

### 8.5 The seam with 087 `[UNVERIFIED: 087's final code unseen; engineer and 087's owner agree these names]`

- `record_register_signature(requests: list[str], notice: str) -> None`: **087 declares it; 088 implements it.** It sets `alvoraa_signed_notice = notice` on each request under a process flag, with no commit. Called only by `register_notice.record`, inside its transaction.
- 087's `_own_the_confirm_fields` (`punch_fix.py:314-343`) must put `alvoraa_signed_notice` back on every other save, as it does for `alvoraa_confirmed_*`.
- 087's slip gate must treat a request as confirmed when `alvoraa_confirmed_on` **or** `alvoraa_signed_notice` is set.
- 087's employee day sheet reads "You signed for it on the register" when `alvoraa_signed_notice` is set.

## 9 · User stories

INVEST checked. Points use the backlog scale (1, 2, 3, 5, 8). Total 31.

| ID | Story | Pts | Prototype | Carries |
|---|---|---|---|---|
| **US-1** | *As an* **HR Manager** *I want* a list of people whose attendance someone else changed in a month *so that* I know who needs a notice and who is done | 5 | list, states | SEC-1, SEC-2 (no reason in payload), OPS-11 |
| **US-2** | *As an* **HR Manager** *I want* to print a notice for one or many people *so that* every release of the content is logged | 3 | preview | SEC-2, SEC-9, SEC-11, PRIV-1, OPS-20, OPS-22 |
| **US-3** | *As an* **Employee with no app** *I want* a one-page paper in large print listing only my own changed days, who filed each and why *so that* I know what I am paid for before I sign | 5 | A4 sheet | PRIV-2, SEC-9, D-1, D-3, D-4 |
| **US-4** | *As an* **HR Manager** *I want* to record "Signed on the register" with one photo per page *so that* the slip block lifts for exactly what the page covered | 5 | dialog | SEC-3, 4, 5, 6, 7, 11, PRIV-1, OPS-9, OPS-15, OPS-22 |
| **US-5** | *As an* **HR Manager** *I want* to record that the worker says it is not right *so that* the objection is on record and the changes stay open | 2 | dialog, second action | D-2, SEC-4, PRIV-2, P-7, P-8 |
| **US-6** | *As an* **HR Manager** *I want* the signed-page photo kept where only HR in scope can open it, every opening logged *so that* a worker's signature is never readable by colleagues | 3 | none (no screen) | SEC-8, SEC-10, PRIV-3, PRIV-4, OPS-10, R4 |
| **US-7** | *As an* **Employee with the app** *I want* one list of this month's days changed by someone else *so that* I can open the existing Confirm / Not right sheet | 2 | month card | PRIV-5, **cut candidate (OQ-3)** |
| **US-8** (must-not) | *As an* **Employee** *I must not* see a colleague's notice or any photo, *and* a **line manager** *must not* see any notice, list or photo *so that* personal data stays with the person and HR | 2 | none | SEC-1, SEC-8, PRIV-3, PRIV-5 |
| **US-9** (must-not) | *As an* **HR Manager** *I must not* be able to record a signature for a change I filed, for my own notice, or outside my company or branch *so that* nobody confirms a change they have an interest in | 2 | filer sentence | SEC-1, SEC-4, OPS-23 |
| **US-10** | *As the* **business** *I want* the record, the field, the row filter and the release to land safely on a live tenant *so that* the 087 gate and Grace are not disturbed | 2 | none | OPS-25, OPS-26, OPS-27, OPS-28, SEC-10 |

Not carried: a viewer for the photo, per-day sign boxes, chasing, store printing (see Subtract).

### YouTrack-ready table (do not create issues; Surbhi decides)

| Summary | Description | Persona | Pts | ACs | Requirements |
|---|---|---|---|---|---|
| 088 Change notices: HR list | Month list of people with open changes by someone else; states; paging; empty and error | HR Manager | 5 | AC-1 to AC-10 | brief §7, SEC-1, SEC-2 |
| 088 Change notices: print | Open notices through one logged call; preview; cap 100 | HR Manager | 3 | AC-11 to AC-17 | SEC-2, SEC-9, SEC-11, OPS-20, OPS-22 |
| 088 Change notices: the A4 sheet | English notice, 5 changes a page, no extra data | Employee, no app | 5 | AC-18 to AC-26 | PRIV-2, D-1, D-3, D-4 |
| 088 Change notices: record signature | One photo per page, all-or-nothing, seam to 087 | HR Manager | 5 | AC-27 to AC-39 | SEC-3..7 |
| 088 Change notices: says it is not right | Second action with required reason | HR Manager | 2 | AC-40 to AC-43 | D-2 |
| 088 Change notices: photo kept private | HR in scope only, opening logged, nothing deletable | HR Manager | 3 | AC-44 to AC-50 | SEC-8, SEC-10, PRIV-3, PRIV-4 |
| 088 Change notices: app month list | Employee's own list | Employee | 2 | AC-51 to AC-53 | PRIV-5 |
| 088 Change notices: must-not (employee, manager) | Refusals | Employee, line manager | 2 | AC-54 to AC-56 | SEC-1, SEC-8 |
| 088 Change notices: must-not (HR as filer) | Filer, self, scope | HR Manager | 2 | AC-57 to AC-59 | SEC-4 |
| 088 Change notices: migrate and release | Fields, rate limits, logs, rollback | Business | 2 | AC-60 to AC-63 | OPS-22..28 |

## 10 · Acceptance criteria

Each has an observable oracle. "Fails first" ones are named for the test engineer (break the control, watch the test fail, restore; the rule in CLAUDE.md §0.5). People used: the §13 fixture set.

### US-1 · The HR list

- **AC-1** Given employee E has an Approved punch fix filed by an HR user, in November 2026, still open, when HR in scope opens the card on November, then E is in the list with "1 changed day" and state "Not printed yet". *Oracle: `list_people` response row.*
- **AC-2** Given E's only change was filed by E, or is Declined, Waiting or cancelled, or was filed by `Administrator`, then E is not in the list. *Oracle: absent row, one case each.*
- **AC-3** Given a manager-added change only, then E is in the list (design gate D-4, P-6).
- **AC-4** Given every change of E is confirmed in the app or has `alvoraa_signed_notice`, then E shows done with no tick box and is not counted in "still need".
- **AC-5** Given 7 people, 2 done and 5 open, then the summary reads "7 people have changed days in November 2026. 2 are done. 5 still need a signature or a confirmation." Select all counts 5.
- **AC-6** Given a month with none, then "No changed days in October 2026" and no button. Given the server errors, then "Could not load the list. Nothing was changed." and **Try again**, with no server text.
- **AC-7** Given 60 people, then the first response holds 25 rows and "Showing 25 of 60"; Show more loads the next 25. Select all means "all that are loaded".
- **AC-8** The `list_people` response has no key named `explanation`, `reason`, or any change detail; only name, number, branch, count, state. *Fails first: add `explanation` to the query and watch it fail.* (SEC-2)
- **AC-9** The card is **not rendered** for a user without HR User, HR Manager or System Manager; the call is refused for them.
- **AC-10** The month arrow forward is off at the current month; the default month is the current month. Skeleton shows within 300 ms (nfr-budget §2).

### US-2 · Print

- **AC-11** When HR presses Print notice for E, then exactly one `Alvoraa Register Notice` exists for (E, month) with `printed_by` = HR, `printed_at` set, `page_count`, and one `changes` row per change with `request`, `page_no`, `content_hash`; and **then** the content is returned. *Oracle: row count and fields, in a browser test that presses the button (feedback-test-what-it-sends).*
- **AC-12** Given the notice insert fails (forced), then the response holds no change content and the screen says "Could not open the notices. Nothing was printed." *Fails first: move the insert after the return.*
- **AC-13** Given 101 people, then the server refuses the whole call with "Print up to 100 at a time, then the rest." and writes no notice rows.
- **AC-14** Given 5 people ticked, then 5 notice rows are written, one each, and the preview has 5 sheets at least.
- **AC-15** The notice row holds no reason, no hours and no change text anywhere in its fields (field list check), and the Error Log holds no reason text after a forced error. (OPS-20, PRIV-1)
- **AC-16** A filer reason of `<img src=x onerror=window.__x=1>` appears in the list, preview, sheet and dialog as those literal characters and `window.__x` stays undefined. (SEC-9)
- **AC-17** A GET to each 088 call changes nothing and is refused; a POST without the CSRF token from a session that holds one is refused. After the 11th `open_notices` call in a minute by one user, the call is refused with a message holding no name, no id, no reason. (SEC-11, OPS-22)

### US-3 · The sheet

- **AC-18** Given E has 3 open changes, then one A4 sheet, "Page 1 of 1", with all 3, in date order, each with the real weekday (13 Nov 2026 reads "Fri"). Footer text as §5.2.
- **AC-19** Given E has 6 changes, then 2 sheets (5, then 1), "Page 1 of 2", "Page 2 of 2", each with name, boxes, footer; `page_count = 2` and `changes.page_no` 1×5, 2×1.
- **AC-20** Each change shows: day, the templated sentence (all four kinds covered by four tests), "This day now counts {h} h {m} m.", filer name and "HR" or "Manager", the reason in full as written (reason text only, without 087's "Raised by" stamp, `_reason_of`).
- **AC-21** Given E has an HR note, a leave day, and a colleague's change on the same day, then none of the three appears on the sheet. (PRIV-2)
- **AC-22** Given a scan the system did not count (a repeat scan) on a changed day, then it is not on the sheet.
- **AC-23** Given a sheet holding one HR-filed change with `alvoraa_needs_confirm = 1`, then the pay line prints. Given a sheet holding only manager additions, then the pay line does **not** print (D-7). Given 6 changes where only the 6th (page 2) is HR-filed, then the pay line is on page 2 only.
- **AC-24** The sheet prints in English when the user's language is Hindi. No Devanagari text is on it.
- **AC-25** The sheet has the boxed rule "If something here is not right, tell HR before you sign.", the read line "I have read the changes on this page.", a signature box 26 mm tall and a date box. *Checked by a screenshot of the print layout, not by a printer (OPS-13 is a manual release check).*
- **AC-26** The reference reads `{employee}/{YYYY-MM}/{page}-{pages}` with the print number, and differs on a reprint.

### US-4 · Record signature

- **AC-27** Given a printed notice with 1 page, when a second HR user in scope records "Signed" with one valid photo, then `outcome = Signed`, `recorded_by`, `recorded_on` set, the photo is one private File attached to the notice, and every covered change has `alvoraa_signed_notice` = the notice. *Oracle: stored values.*
- **AC-28** Given 3 pages, recording with 1 photo is refused ("Add 3 photos, one for each page. You added 1."); with 3 it succeeds. A dispute (US-5) needs no photo.
- **AC-29** Given a covered change was edited in its confirmed content (day, time, set-aside list, words) after the print, then that change stays open and the dialog names it; the others are marked. Given a new change was filed after the print, then it stays open and the row shows the amber line. *Fails first: skip the hash check.* (SEC-3)
- **AC-30** Given a REST PUT or Desk save sets `alvoraa_signed_notice` or the notice's `outcome` by hand, then the stored value is unchanged and the slip block stays. A System Manager Desk edit of a signed notice's recorded fields is also refused except for the photo correction path (Q1). *Fails first: remove the put-back.* (SEC-5)
- **AC-31** Given the call names a change id list in the request body, then the list is ignored or refused; only the notice's own `changes` are covered. (SEC-3)
- **AC-32** Given no print record exists for the notice name, then recording is refused.
- **AC-33** Given a notice that is not the latest for (E, month), then recording is refused: "A newer notice was printed. Use the newer one."
- **AC-34** Photo checks: a zip renamed `.jpg` refused; a PDF refused; HEIC refused; a 13 MB image refused before decode; a PNG with GPS EXIF stored with no EXIF; stored file at most 1 MB and 1,600 px on the long edge. (SEC-6, `expense_evidence.py:105-131`)
- **AC-35** The stored file name is generated and contains neither the employee's name nor id.
- **AC-36** Given a photo whose `content_hash` equals any other register photo (any person, month, or another page of the same notice), then it is refused ("That photo was already used."). Given the same file for a different person, refused. (SEC-7)
- **AC-37** The dialog shows the photo preview and "Check the page shows {name} and {ref}". Empty photo: "Add the photo of the signed notice first."
- **AC-38** Given a failed record call (forced network or server error), then no photo File exists, no change is marked and the notice stays `Printed`: all or nothing. The chosen photo stays in page memory with "Not saved yet. Try again", and `localStorage`, `IndexedDB` and the service-worker cache hold no image. (PRIV-1)
- **AC-39** Given the stored size of each photo, then a log line is written with the size and no names (OPS-15).

### US-5 · Says it is not right

- **AC-40** Given the second action with an empty reason, then refused: "Write what {name} said is not right." Nothing stored.
- **AC-41** Given a reason, then `outcome = Not right`, `dispute_reason`, `recorded_by`, `recorded_on` set; **every covered change keeps `alvoraa_signed_notice` empty**, so the slip stays blocked (087 gate). No photo is needed.
- **AC-42** The row then reads "{name} says it is not right (told HR on {d}, recorded by {name}). The changes stay open: ..." and clears (reads the next state) once the covered changes are no longer open or a newer notice was printed.
- **AC-43** The filer of a covered change is refused here too (US-9). The reason is shown as text, never markup.

### US-6 · The photo stays private

- **AC-44** The photo File has `is_private = 1` and its parent is the notice. As the employee, as the line manager, as company-B HR and with no login, `GET /private/files/<photo>` returns 403. *Fails first: attach the photo to the Attendance Request and watch the employee fetch succeed.* (SEC-8)
- **AC-45** As in-scope HR, `open_photo` returns the bytes and writes one `Alvoraa Photo Access Log` row with source "Register signature photo", viewer and time; a refused call writes none.
- **AC-46** Report Builder export on the notice as HR Manager is refused; no role holds export on it; the photo appears in no list payload, email, notification or Inbox row.
- **AC-47** Given company-A HR Manager lists `Alvoraa Photo Access Log`, then no company-B rows show. *Fails first: remove the row filter.* (SEC-10)
- **AC-48** HR delete of the notice and of its File is refused from the Desk and REST. System Manager delete is refused too. (PRIV-4)
- **AC-49** No code in 088 deletes a photo or a notice, and no scheduler entry is added (OPS-19, OPS-25).
- **AC-50** The notice stores `employee` and `month`, so a later purge can compute its date without reading the photo. No `retain_until` field exists.

### US-7 · App month list (cut candidate)

- **AC-51** Given an Active employee with 3 changed days filed by someone else, then the month view shows "3 days this month were changed by someone else." and **See them**; the list shows day, what, who filed it, the date and one of: "Not confirmed by you yet." / "You confirmed it." / "You signed for it on the register." Tapping a row opens 087's day sheet.
- **AC-52** The response has the reason and the state and no key holding `photo`, `file` or `url`. A colleague's id returns a refusal. A Left employee gets nothing (`_me` is Active only). (PRIV-5)
- **AC-53** A manager-added change with no signature reads "Shown to you. Say if it is not right." `[ASSUMPTION: new words, the designer confirms]`.

### US-8 · Must-not (employee, manager, others)

- **AC-54** As an Employee, a line manager and a Biometric Sync login, each of `list_people`, `open_notices`, `record`, `open_photo` is refused, and a refusal is logged with the rule id and ids only, never a name or reason. (SEC-1)
- **AC-55** As a plain employee, REST GET on `Alvoraa Register Notice` returns a permission error and the list is empty.
- **AC-56** A line manager who holds a User Permission on a report's Employee cannot read their notice (no role row, no User Permission path; `manager_scope.py:52-56` read).

### US-9 · Must-not (HR)

- **AC-57** HR in company B, HR scoped to branch 1 on a branch-2 employee, and HR scoped to a branch on an employee with no branch, are each refused on all four HR calls; HR with no company or branch permission gets an empty list and is refused by name; System Manager succeeds. *Fails first: replace the helper with a company-only check and watch the branch test pass wrongly.* (SEC-1)
- **AC-58** Given HR user A filed a covered change, then A is refused on `record` for both outcomes, on the screen (the sentence "You filed a change on this page, so another HR person records the signature.") and on the endpoint, read from the database `owner`. A second HR user in scope succeeds and is named as recorder.
- **AC-59** Given an HR user who is also employee E, then they are refused recording E's notice, including when E's status is set to Left (by `user_id`, as `refuse_own_decision`, `access.py:109`).

### US-10 · Migrate and release

- **AC-60** After migrate on a copy of a real tenant: the DocType and the custom field exist, `columns_ready()` is true, no existing row changed; before migrate, the readers behave as before (no unknown-column error). *(OPS-26)*
- **AC-61** `scripts/check_app_integrity.py` passes; the image diff shows no new package; no scheduler entry, queue, worker or volume is added. (OPS-25)
- **AC-62** Each print, photo upload, refusal and stored size writes one log line with counts and ids only (no names, no reasons); per-tenant daily counts come from counting lines. No daily job. (OPS-24; the alert thresholds go in the release plan.)
- **AC-63** Rollback: redeploying the previous tag with migrations off leaves the DocType and field in the database, unused and empty. The tag exists in `alvoraa-app` before release. (OPS-28)

## 11 · Edge cases that can happen here

| Case | What happens |
|---|---|
| A change is filed after printing | Stays open and off the paper; row shows the amber line; HR prints again (AC-29) |
| A change is edited after printing | Its `content_hash` no longer matches: not marked at recording; dialog names it (AC-29). A withdrawn or declined one is also not marked |
| Multi-page notice | One record, N pages, N photos (one per page). Each page is signed separately. A page photo missing refuses the whole record (AC-28) |
| Reprint after a late change | A new notice record with a new print number; recording on an older one is refused (AC-33). The earlier paper is dead |
| A reused photo | Refused by hash (AC-36). A new shot of an old page passes; the month and print number on the page are the HR eye check (R3, accepted) |
| The wrong person's page recorded | The dialog shows name and reference next to the preview (AC-37). No server check is possible (R2, accepted). A System Manager corrects it (Q1) |
| The filer records | Refused (AC-58). With only one HR person in a branch, another HR person in scope, or a System Manager, records. If there is none, the slip stays blocked; the app Confirm or Withdraw still work |
| Manager-only sheet | No pay line (AC-23). Signing marks the changes seen; it changes no pay. The person stays "open" in the list until signed (§5.1), because the list is about whether the notice was shown and signed |
| Worker disputes | Stored on the notice (AC-41). Changes stay open. Q3 of 01c is settled: no request is created, so there is no filer (see D-2 note) |
| Worker cannot read | Sheet in large print; HR reads aloud; "tell HR before you sign" boxed. No timer, no warning colour |
| Leaver, mid-month | Still listed; last month still prints. The leaver sees nothing in the app (AC-52) |
| Rehired, duplicate employee | The notice follows the Employee id; nothing merges them |
| Employee with no manager | No effect. The filer is whoever filed |
| Month with 0 changes | Empty state (AC-6) |
| 100 people printed | Cap and the time test on a real laptop and phone (OPS-12; an unproven number, [ASSUMPTION]) |
| Two HR users record the same notice at once | The first sets the outcome; the second is refused because the outcome is no longer Printed (AC-30) |
| Concurrent print by two HR users | Two notice records; only the latest can be recorded (AC-33) |
| A change approved after printing (it was Waiting) | Not on that paper; it appears as "added after printing" once approved |
| A holiday, half-day, DST, regional holiday list | Not affected: the notice lists a day and the 087 snapshot's hours, and does not recompute attendance |
| Bulk import, amended documents | An amended (cancelled) change drops off at the next print; an import cannot set `alvoraa_signed_notice` (AC-30) |
| Devanagari / fonts | Not applicable: English only. Hindi font checks (OPS-13) are for the later Hindi release |

## 12 · Non-functional requirements for this slice

| Item | Number | Source |
|---|---|---|
| Volume | up to 600 people per tenant per month; notices only for people with changes (a few a month per tenant is the brief's guess, [ASSUMPTION], no data) | brief §7 |
| List | 25 per page; skeleton in 300 ms; list API under 1.5 s for 600 (nfr-budget §2 core HR view) | 01b §3; nfr-budget |
| Print call | ≤100 people; browser layout time of 100 notices **unmeasured**, to time on a mid-range Windows laptop and a phone (OPS-12). If slow, lower the cap, do not add a PDF engine | 07 §2 |
| Photo | stored ≤1 MB and ≤1,600 px; phone shrinks to about 1,600 px, JPEG about 75 before upload; a 3G upload of about 350 KB takes 3-5 s ([ESTIMATE]); 5 MB is not the cap here, 12 MB raw / 1 MB stored is | 07 OPS-9; `expense_evidence.py:105-131` |
| Storage | target under 1 GB per tenant per year (brief §9) | OPS-15 |
| Queues | none. No background job, no new queue | OPS-25 |
| Cache | the list and the preview are never cached; no `Cache-Control: public` | OPS-11 |
| Sensitive data | the photo (biometric-class until C1), the filer's reason on paper, the dispute reason; all HR-in-scope only | 01c §3 |
| Retention | nothing deletes; erase job stays off | PRIV-4, decision 5 |

## 13 · Test fixture the engineer must build (without it "0 findings" means nothing)

From 01c §9: in one month, for one person an HR-filed change, a manager set-aside, a manager addition and one filed after the print; a second person with six changes (two pages); two HR logins in one company (one the filer); HR in a second company; a branch-1 HR with employees in branch 2 and with no branch; a no-company HR; a System Manager; an HR user who is also an employee, then set to Left; a line manager and a plain employee; a Biometric Sync account. (No "gate on/off" company: D-5.)

## 14 · Data migration and backfill

- **Create:** DocType and two child tables; one custom field; the new `source` option; the `permission_query_conditions` entry. All by migrate (`after_migrate` and `after_install`, as `punch_fix.after_migrate`).
- **Default / recompute:** nothing. No existing row is touched. No backfill: past months have no notices and none is needed.
- **Rollback:** redeploy the previous tag with migrations off (AC-63). The DocType and field stay empty. About 7 minutes measured because of the `bench version` wait (07 OPS-28).
- **Before migrating:** check the job queue is empty (migrate-queue trap); run the dry run per `REHEARSAL.md`.

## 15 · Notifications and messages

**No email, push or Inbox item is sent.** Nothing is sent to anyone when a notice is printed or recorded (subtract). Screen messages, from 01b §3-§4 (all `_()` translatable on screen; the paper is English):

| Where | Copy | Never contains |
|---|---|---|
| List error | "Could not load the list. Nothing was changed." | server text |
| Empty | "No changed days in {month}" | |
| Print fail | "Could not open the notices. Nothing was printed." | ids, reasons |
| Over cap | "Print up to 100 at a time, then the rest." | |
| Empty photo | "Add the photo of the signed notice first." | |
| Photos short | "Add {n} photos, one for each page. You added {k}." | |
| Newer notice | "A newer notice was printed. Use the newer one." | |
| Reused photo | "That photo was already used." | the other person |
| Empty objection | "Write what {name} said is not right." | |
| Network fail | "Not saved yet. Try again." | |
| Filer | "You filed a change on this page, so another HR person records the signature." | |
| Refusals | one generic sentence | a name, a reason, a file name |

## 16 · Localisation and accessibility

- Screen strings translatable. Date "Fri 13 Nov 2026"; times 24 h; hours "8 h 20 m". Paper: **English only, whatever the screen language** (decision 3). Hindi lines are a later change after a Hindi reader checks them (D-1); no setting is added.
- WCAG 2.2 AA (nfr-budget §7): tick boxes named ("Select Ravi Sample"), targets ≥44 px, status = word + icon (never colour alone), dialog traps focus and Escape closes, paper black on white at 11 pt or more, works on a black-and-white printer.
- Phone: HR can do all of it at 390 px (rows stack). The worker uses no screen.

## 17 · Audit and traceability of the data

From the database alone, a year later: which changes were on a page, who released the content and when (notice, `printed_by/at`, `changes`); who recorded signed or not right, when, with which photo (`recorded_by/on`, `pages`); who opened a photo (`Alvoraa Photo Access Log`); every edit by a System Manager (Version, `track_changes = 1`). Whether the worker really signed is answered **only by the photo** (R1, accepted by Surbhi, 21 Nov 2026). `security.log` is not the durable trail (it rotates).

## 18 · Parity table: approved prototype-v1 against this spec

| # | Prototype (v1, with the gate) | Spec | Verdict |
|---|---|---|---|
| P-1 | One signature records many changes | as drawn (AC-27) | same |
| P-2 | Dialog wording 4.4 | as drawn | same |
| P-3 | One person per page | as drawn | same |
| P-4 | One sign box per page | as drawn (Surbhi's recommendation taken) | same |
| P-5 | Real weekday | as drawn (AC-18) | same |
| P-6 | Manager additions on the notice, name + "Manager" | as drawn (AC-3, AC-20) | same |
| P-7 | Second action "Says it is not right", required reason | as drawn (AC-40..43). Stored on the notice; 087 side: see OQ-2 | same, one dependency |
| P-8 | Row line "says it is not right" | as drawn (AC-42) | same |
| **P-9** | Reference "EMP-0207/2026-11/1-3" | adds the print number, so a reprint's paper differs | **different, needs Surbhi's yes** |
| **P-10** | Hindi line under every English line | English only until a Hindi reader checks (Surbhi's decision 3, 21 Nov) | **different, decided** |
| **P-11** | Pay line follows "the tenant's 087 setting" | follows the sheet's content (D-5, D-7); no setting exists | **different, needs Surbhi's yes** |
| **P-12** | The preview toggle "Salary-slip line on the sheet" | prototype control only, not built (01b says so) | same |
| **P-13** | Row "Print opened" after the Print button | the log is written at preview (SEC-2); wording unchanged | different in timing, not on screen |
| **P-14** | Photo opening: "no viewer" | an endpoint `open_photo` exists with no screen, so every opening is logged | needs her yes (OQ-4) |
| **P-15** | Employee list line "Not confirmed by you yet" for every row | manager additions get "Shown to you. Say if it is not right." | **different, needs the designer and her yes** |
| P-16 | Prints HR filer's name | built as drawn; reverses 087 decision 7 | needs her yes (OQ-1) |

Every other element of the prototype (card, month arrows, summary line, Select all, Print selected, rows, foot line, preview bar, states) is built as drawn.

## 19 · Compliance-impact sub-analysis (not a lawyer; nothing here is a legal ruling)

### 19.1 Data touched

| Field / object | Class | Purpose | Lawful basis (as recorded) | New? |
|---|---|---|---|---|
| Notice content (own changes, filer, reason, hours) | sensitive | tell the worker what others changed | employment contract / legitimate use, per counsel's condition 3 (relayed, unsigned) `[ASSUMPTION]` | No: read from existing requests, never copied |
| Print record (employee, month, printed by/at, change ids, hashes) | internal | evidence it was shown; coverage of a signature | as the attendance record | **Yes**, needed for SEC-2/3 |
| Photo of each signed page | sensitive, **treated as biometric-class until counsel answers C1** | proof of the worker's confirmation | not recorded: C1 | **Yes**. Outcome impossible without it: counsel requires a signed paper (condition 3, relayed) |
| `recorded_by/on`, outcome, dispute reason | internal; reason is sensitive free text | the 087 pay gate; audit | as above | **Yes** |
| Photo access log row | internal | who looked at a signature | security | extends an existing table |

### 19.2 Obligations engaged

| Obligation | Source | What 088 does | Feature |
|---|---|---|---|
| DPDP security safeguards; fiduciary = employer, Alvora = processor | `security-compliance-baseline.md`, 01c §8 (stale from 22 Nov) | HR-in-scope only; logged | SEC-1, SEC-8, PRIV-3 |
| IT Act s.43A / SPDI Rules "biometric information" | 01c §8, secondary source | treat photo as sensitive until C1 | PRIV-3 |
| Wage and attendance records, 5 years (relayed) | 01c §8 | nothing deletes | PRIV-4 |
| Grace go-live condition 3 | counsel, relayed | the whole slice (Grace still waits for 088b) | |
| Export of personal data is logged | baseline | no export at all | AC-46 |

### 19.3 Visibility delta

New: HR in scope sees a list of employees with attendance changes and the filer's reason on paper; HR in scope can open signed-page photos. The employee with the app sees the same facts as the paper. **Negative cases:** employee, line manager, CXO (as a role without HR), Biometric Sync, any other role: nothing. HR out of scope: nothing. Nobody sees a photo through a URL. **The filer's reason is now printed in full on a shop-floor paper** (Surbhi's D-3, R5 accepted).

### 19.4 Decision automation

No. Nothing decides about a person. A human (HR) records each signature or objection; a different HR person from the filer; the worker is told in writing and can say it is not right before signing. How they contest: tell HR before signing (printed), or Not right in the app (087).

### 19.5 Retention and deletion

Nothing is kept for a stated period and nothing deletes in 088; the erase job stays off. HR cannot delete a notice or photo. Retention (5 years, 6 to 8, or other) is **asked of counsel** (C2). Backups copy every file.

### 19.6 ⚠ Open compliance questions

| Question | Who decides | Blocks |
|---|---|---|
| C1: is the photo "biometric information"; consent; who may open | Surbhi sends, counsel answers | release to a customer |
| C2: retention period, start, who deletes | Surbhi, counsel | the purge slice, the retention sentence |
| C3: one photo per page and one person per page enough; dispute from HR's record of the worker's words enough | Surbhi, counsel | release for Grace |
| New: may the filer's name be printed when 087 hid HR's name from the employee (OQ-1) | Surbhi (counsel if she wants) | the exact words on the paper |

### 19.7 AI features

None. 088 uses no AI.

### The prohibitions

Nothing in 088 needs AI to set a rating, emotion or inference, passive monitoring or surveillance. No refusal needed.

## 20 · Decisions I made, and open questions

### Decisions made in this spec (proposals; each can be reversed)

| ID | Decision | Why |
|---|---|---|
| D-5 | The pay line follows the sheet's content, no tenant switch | none exists in 087 (searched) |
| D-6 | Notices carry **Approved** changes only | "now counts" is only true after approval; the snapshot is written at approval |
| D-7 | **A sheet holding only manager additions does not print the pay line** | a manager addition does not block a slip (087) |
| D-8 | One DocType per print, with two child tables | no existing record is HR-only, one-per-print and many-to-many |
| D-9 | `retain_until` dropped | no decided period; PRIV-4 stores employee and month instead |
| D-10 | Recording is allowed only on the latest notice for the person and month | stops an old paper being recorded |
| D-11 | The objection (D-2) is stored on the notice, and creates no request | it avoids the "who is the filer" problem (01c Q3) |
| D-12 | No daily log job: each call logs its own line | OPS-24 and OPS-25 conflict; this satisfies both |

### Open questions

| # | Question | Owner | Blocks | My default |
|---|---|---|---|---|
| OQ-1 | The paper prints the HR filer's name; 087 decision 7 hid it from the employee. Confirm the paper and the app list print it | Surbhi (counsel optional) | the words on the sheet and AC-20 | Print it, as the approved prototype shows |
| OQ-2 | 087's "dispute" has no code yet. 088 stores the objection on its own notice. Is that enough, or must 087's own dispute record also be written? | Surbhi, 087 owner | AC-41 wiring | Notice only |
| OQ-3 | Cut US-7 (the app month list)? Counsel's condition is about non-app staff; 087's day sheet already carries Confirm. 2 points saved | Surbhi | scope | Keep (approved in the prototype); cut only with her yes |
| OQ-4 | Build `open_photo` with no screen so every opening is logged (decision 4), or build nothing and leave an HR person with a URL unlogged? | Surbhi | US-6 | Build the endpoint |
| OQ-5 | Seam names with 087 (§8.5) | 087 engineer | build start | as written |

(01c Q1 and Q2: Q1, default kept: a System Manager fixes a wrong photo in the Desk. Q2, default kept: the app does not say who recorded.)

## 21 · Assumptions

- `[ASSUMPTION]` 087 ships first and its final code carries the fields and the slip gate as its spec says (OPS-27).
- `[ASSUMPTION]` 5 changes per page and 100 per batch are right; both are checked on a real printer (Surbhi accepted).
- `[ASSUMPTION]` Counsel accepts one photo per printed page (C3, open).
- `[ASSUMPTION]` Browser print counts as "printed".
- `[ASSUMPTION]` The rate-limit numbers (60, 10, 20, 60 per minute) are right; confirm on the build bench.
- `[ASSUMPTION]` Words for a manager addition in the app list (AC-53).
- `[ASSUMPTION]` Counsel's replies are accurate as relayed; unsigned.

## 22 · Traceability

"AC-n" means the criterion exists; **no test exists yet**. The test engineer writes them (04).

### Brief (`01-product-brief.md`, including the gate)

| Source | Line | Story | AC | Status |
|---|---|---|---|---|
| Brief §1 | Employee reads and signs a changed day on paper | US-3, US-4 | AC-18..28 | covered |
| Brief §1 | HR gets one list and one place to record | US-1, US-4 | AC-1..10, AC-27 | covered |
| Brief §1 | CXO and line manager: nothing | US-8 | AC-54, AC-56 | covered |
| Brief §5 | App employee: same list under month view | US-7 | AC-51..53 | covered (cut candidate OQ-3) |
| Brief §5 | Line manager printing: later | none | none | **deliberately not built** (brief) |
| Brief §5 | CXO share, payslip lines | none | none | not built (brief) |
| Brief §7 | one notice per person per month, own days only | US-3 | AC-18, AC-21 | covered |
| Brief §7 | only valid hours | US-3 | AC-20, AC-22 | covered |
| Brief §7 | filer and mandatory reason | US-3 | AC-20 | covered |
| Brief §7 | opened from portal, browser print, no PDF engine, no job | US-2, US-10 | AC-11, AC-61 | covered |
| Brief §7 | HR records signature, one photo of the page | US-4 | AC-27, AC-28 | covered |
| Brief §7 | printed only for people with changes | US-1 | AC-1..3 | covered |
| Brief §7 | export is logged | US-2 | AC-11 | covered |
| Brief §10 | "if it is not right, tell HR before you sign" | US-3 | AC-25 | covered |
| Brief §10 | leaver mid-month still prints | US-1 | AC-52 and §11 | covered |
| Brief §10 | photo blurry: slip stays blocked | US-4 | AC-37, AC-34 | covered |
| Brief §10 | wrong tenant config / 087 gate off: notice is information | US-3 | none | **dropped: no such switch exists (D-5); Surbhi's yes needed (P-11)** |
| Brief §10 | cheapest check: print a dummy for 3 Grace staff | none | none | **gap: a manual release step (OPS-13), not an AC** |
| Brief §9 | success measures 1 to 4 | none | none | **gap: measures, not behaviour. Measure 4 (photo storage) via AC-39 only** |
| Brief gate | 088 ships alone, Grace waits for 088b | all | all | covered; 088b out of scope |
| Brief Q1..Q6 | counsel questions | n/a | n/a | carried as C1..C3 (Surbhi to send) |
| Surbhi's decision 1 | signature and photo moved from 087 | US-4 | AC-27..39 | covered |
| Decision 2 | until 088, HR-filed change only confirmed in app or withdrawn | n/a | n/a | accepted consequence; no AC |
| Decision 3 | English only until Hindi checked | US-3 | AC-24 | covered |
| Decision 4 | HR of the company only opens photo, logged, never exported | US-6 | AC-44..46 | covered |
| Decision 5 | nothing deleted, erase job off | US-6 | AC-48, AC-49 | covered |
| Decision 6 | R1..R8 accepted | n/a | n/a | recorded, no AC |

### Prototype-v1 and the design gate

| Source | Screen / line | Story | AC | Status |
|---|---|---|---|---|
| 01b §4.1 | Card, month arrows, summary, Select all, Print selected, row, foot line | US-1, US-2 | AC-1..10 | covered |
| 01b §3 | loading, empty, error | US-1 | AC-6, AC-10 | covered |
| 01b §3 | no permission: card not shown | US-1 | AC-9 | covered |
| 01b §3 | 400 people paging | US-1 | AC-7 | covered |
| 01b §3 | row states (not printed, printed, changed after, signed, app, filer) | US-1, US-9 | AC-29, AC-42, AC-58, §5.3 | covered |
| 01b §3 | network drops | US-4 | AC-38 | covered |
| 01b §4.2 | A4 sheet parts | US-3 | AC-18..26 | covered |
| 01b §4.2 | several pages | US-3, US-4 | AC-19, AC-28 | covered |
| 01b §4.3 | preview and Print | US-2 | AC-11, AC-14 | covered |
| 01b §4.4 | dialog and photo preview | US-4 | AC-27..37 | covered |
| 01b §5 | Employee month card | US-7 | AC-51..53 | covered (OQ-3) |
| 01b §8 | accessibility | all | §16, no single AC | **gap: no AC. A screen-reader and 200% zoom check is a release step** |
| Gate D-1 | Hindi read before print | US-3 | AC-24 | covered (Hindi not built) |
| Gate D-2 | Says it is not right | US-5 | AC-40..43 | covered |
| Gate D-3 | reason prints in full; 087 send bar hint | US-3 | AC-20 | **partly: the hint is a 087 screen, not 088's. Gap, to be added in 087 (Surbhi said yes)** |
| Gate D-4 | manager additions on notice | US-3 | AC-3, AC-20, AC-23 | covered |
| Gate assumptions | 5 per page, 100 per batch | US-2, US-3 | AC-13, AC-19 | covered; real-printer check is a manual step |
| P-6, P-7, P-8 | parity rows | US-3, US-5 | AC-3, AC-40..42 | covered |

### Security and privacy (`01c`)

| Source | Item | Story | AC | Status |
|---|---|---|---|---|
| SEC-1 | one scope rule | US-8, US-9 | AC-54, AC-57 | covered |
| SEC-2 | content leaves through one logged call | US-1, US-2 | AC-8, AC-11, AC-12, AC-13 | covered |
| SEC-3 | signature covers what was printed | US-4 | AC-29, AC-31, AC-32 | covered |
| SEC-4 | no interest recording | US-9 | AC-58, AC-59 | covered |
| SEC-5 | fields written by the call only | US-4 | AC-30 | covered |
| SEC-6 | photo checks | US-4 | AC-34, AC-35 | covered |
| SEC-7 | reused photo | US-4 | AC-36, AC-37 | covered |
| SEC-8 | photo private by structure | US-6 | AC-44..46 | covered |
| SEC-9 | free text as text | US-2 | AC-16, AC-43 | covered |
| SEC-10 | access log scoped | US-6 | AC-47 | covered |
| SEC-11 | POST only, CSRF | US-2 | AC-17 | covered |
| PRIV-1 | nothing new but the photo, no copy, no cache | US-2, US-4 | AC-15, AC-38 | covered |
| PRIV-2 | what is on paper | US-3 | AC-20..22 | covered |
| PRIV-3 | photo most sensitive | US-6 | AC-44..47 | covered |
| PRIV-4 | nothing deletes | US-6 | AC-48..50 | covered |
| PRIV-5 | app shows same facts | US-7 | AC-52 | covered |
| PRIV-6 | print record kept with the records | US-6 | AC-48 | covered (a rule; no extra test beyond delete refused) |
| C1, C2, C3 | counsel questions | n/a | n/a | open; block release, not build |
| R1..R8 | residual risks | n/a | n/a | accepted by Surbhi, 21 Nov |

### DevOps (`07`)

| Source | Item | Story | AC | Status |
|---|---|---|---|---|
| OPS-1 | one photo per page | US-4 | AC-28 | covered (C3 open) |
| OPS-2 | no per-person PDF | US-10 | AC-61 | covered |
| OPS-3 | register in a background job | n/a | n/a | **088b; not in this slice** |
| OPS-4 | reuse photo checks | US-4 | AC-34 | covered (081's checks, not the 512 px profile ones; differs from OPS-4's wording) |
| OPS-5 | retention needs a named owner and a deleter | US-6 | AC-49 | **not built; Surbhi's decision 5 (asked of counsel)** |
| OPS-6 | ask counsel about biometric | n/a | n/a | C1 |
| OPS-7 | statutory forms layouts | n/a | n/a | 088b |
| OPS-8 | time one PDF and one photo | US-4 | AC-39 | **partly: a manual release step for the photo timing; the PDF timing is 088b** |
| OPS-9 | phone-side shrink, 1,600 px | US-4 | AC-34 | covered (server cap) ; the phone-side step is in the build, **no AC can prove the phone side. Gap** |
| OPS-10 | private serving, URL test | US-6 | AC-44 | covered |
| OPS-11 | no caching | US-1, US-2 | AC-8 | **gap: no AC proves "no cache". Add: response has `Cache-Control: no-store`** |
| OPS-12 | 100-person time | US-2 | AC-13 | cap covered; **the timing is a manual release step** |
| OPS-13 | print on a real printer | n/a | n/a | **manual release step, not an AC** |
| OPS-14 | no web font, CDN | n/a | n/a | **not tested; AC-61 covers packages only** |
| OPS-15 | storage and size log | US-4 | AC-39 | covered |
| OPS-16 | disk free, backups | US-10 | n/a | **release-plan step (DevOps), not an AC** |
| OPS-17 | restore proof | US-10 | n/a | **release-plan step, not an AC** |
| OPS-18 | `retain_until` | n/a | AC-50 | **not adopted; my decision D-9; needs Surbhi's agreement** |
| OPS-19 | erase job off | US-6 | AC-49 | covered |
| OPS-20 | insert-only print log | US-2 | AC-11, AC-15, AC-30 | covered |
| OPS-21 | retention of the log; index | US-10 | §7.1 | **gap: no AC for the index; a code review check** |
| OPS-22 | rate limits | US-2 | AC-17 | covered for print; **the other three limits: no AC. Gap** |
| OPS-23 | HR-roles only | US-8, US-9 | AC-54, AC-58 | covered |
| OPS-24 | monitoring | US-10 | AC-62 | covered by log lines; thresholds are a release-plan item |
| OPS-25 | no new container, queue, job | US-10 | AC-61 | covered |
| OPS-26 | migrate dry run | US-10 | AC-60 | covered |
| OPS-27 | release order 087, 088, 086 | US-10 | n/a | **release plan; no AC** |
| OPS-28 | rollback | US-10 | AC-63 | covered |
| OPS-R-1..R-4 | Surbhi's decisions | n/a | n/a | answered: decision 3 (R-3), 4 (R-4), 5 (R-1, R-2) |

## 23 · Subtract pass

**Removed from this spec, and why:**
- the tenant "slip gate" condition on the pay line (no such setting);
- `retain_until` (OPS-18): no period is decided;
- a daily monitoring job (OPS-24 versus OPS-25);
- an email or notification on print or record;
- a per-person "history of notices" screen;
- a photo viewer screen; the endpoint stays only so that every opening can be logged (OQ-4);
- Waiting changes on the paper (D-6);
- a second child table for photos on the Attendance Request, a "disputed" field on the request, and a request created for the objection;
- any Hindi switch or flag.

**Kept though I looked hard at it:** the new DocType (nothing existing is HR-only and many-to-many), the custom field (the employee's screen needs its own sentence), the `content_hash` per change (SEC-3 cannot be met without it), and US-7 (Surbhi approved it in the prototype; marked a cut candidate).

## 24 · Ready check (`definition-of-ready-done.md`)

- [x] Brief, design, security and DevOps requirements read; the design is approved at its gate; 01c and 07 §3 present.
- [x] Gap analysis done, with the places looked.
- [x] Every story has persona, points and ACs; AC oracles are observable.
- [x] Permission matrix and negative cases stated.
- [x] Compliance sub-analysis present.
- [x] Traceability complete; gaps listed, not hidden.
- [ ] **No open question that blocks the build:** OQ-1 and OQ-5 change the words and the seam. **Not ready to build until Surbhi answers OQ-1 and the 087 engineer confirms OQ-5.**
- [ ] **087's code with the seam does not exist.** Build cannot start on 088 until 087's branch carries it (OPS-27).
- [ ] Release (not build) is blocked on C1, C2, C3 and the Hindi review.

**Verdict: the spec is complete; the slice is NOT ready to build until OQ-1 and OQ-5 are closed and 087 has landed its side of the seam.**
