# ALV-266 · Security re-check (changes since 06-security only)

Checked 1 Nov 2026 by `hrms-security-privacy-engineer`. Branch
`slice/alv-266-employee-write-fields` at `c60503da`. I did not write or specify this
slice, so there is no self-review conflict. I did write `06-security.md`, which this
re-check follows up.

How I tested: container `hrlocal-266`, site **fresh266**. The container's code matched
the branch exactly (compared file by file, line endings aside). I started a plain
gunicorn server (not the dev server) and made real HTTP calls, so every request went
through the ALV-249 request guard and the first-use password lock. I used four
throw-away logins: a manager (Employee + Employee Self Service), that manager's report
(same roles), an unrelated colleague (same roles) and an HR User. The report's record
held made-up passport, health, family, blood group, bank and PAN values, so a leak would
show by its marker. Afterwards I deleted every record, log row, share, version, ToDo and
login I made, and stopped the server. No source file was changed.

---

## Bad news first

**1. P0 - STOP THE LINE (not caused by this slice). The change history on the Desk form
shows a manager the report's bank account, PAN, passport and health details.**
*Verified by running it.* HR changed the report's passport and health details, and
Administrator changed the bank account and PAN. Then the manager called
`frappe.desk.form.load.getdoc` (what the Desk form calls when it opens) and
`frappe.desk.form.load.get_docinfo` on the report's record. The form itself hid every
level-1 and level-3 field, as it should. But `docinfo.versions` carried the last 10
change records with **old and new values** of every changed field: the bank account
number, the PAN, both passport numbers and both health texts. The report sees the same
on their own record.

- Cause: `frappe/desk/form/load.py:241-250`. `get_versions` reads `Version` with
  `frappe.get_all` and returns the raw `data`, with no field-level check. Employee has
  change tracking on. Reading `Version` directly is refused (403), so only this path
  leaks.
- Who: anyone who can open the Employee record - a manager for every report in their
  tree (ALV-249), the person for their own record, and HR User for level-1 fields that
  D2 keeps for HR Manager only.
- *Inference:* production has the same Frappe code and the same setting, so this is
  most likely live today for every DTC manager whose report had a bank, PAN, salary or
  passport change in their last 10 edits. **I could not check production.** It needs a
  read-only count of `tabVersion` rows for Employee that contain level-1 or level-3
  field names.
- Detection: none. Nothing logs who opened which form's history.
- This slice did not cause it and does not make it worse. But it means **D6 ("nobody
  but HR sees passport and health") and D2 ("only HR Manager sees bank and pay") are not
  true yet** on the Desk form.
- Smallest fix (customisation, rung 4): override `getdoc` and `get_docinfo` so each
  version row drops the values of fields the reader cannot read, keeping the field name
  and who changed it. Turning change tracking off is cheaper but destroys the audit
  trail for bank-account changes, which is exactly the trail a payroll-fraud case
  needs - I do not recommend it.

**2. MAJOR (P1, not caused by this slice) - a Travel Request copies the passport
number.** *Verified by running it.* The manager created a Travel Request with the
report as the employee. Frappe filled `passport_number` from the report's Employee
record on save (`fetch_from: employee.passport_number`, `travel_request.json:145`) and
returned it; it then showed in the manager's own Travel Request list. Employee Self
Service holds create on Travel Request. The link check the form uses
(`validate_link_and_fetch`) does respect the field level (it returned nothing); the
copy happens on the server at save. Fix (configuration): a Property Setter that clears
that `fetch_from`, or sets the Travel Request field to level 3 too. Existing Travel
Requests already hold copies.

**3. MAJOR (P1, not caused by this slice) - an Employee Promotion copies the salary
(CTC).** *Verified by running it.* With a promotion on the report's record, the manager,
the report and the HR User all read `current_ctc` and `revised_ctc` through
`/api/resource/Employee Promotion`. The unrelated colleague saw nothing. `current_ctc`
is `fetch_from: employee.ctc`, and Employee Promotion's fields are all level 0. CTC is a
level-1 field that only HR Manager may see (D2). Fix (configuration): put the two CTC
fields on Employee Promotion at level 1 with an HR Manager row, or accept it in writing.
I do not know whether DTC uses Employee Promotion.

**4. MAJOR (P2, not caused by this slice) - a save answers with every field.**
*Verified by running it.* When an HR User saves any Employee record through
`/api/resource` PUT, `frappe.client.set_value`, `frappe.client.save` or the Desk form's
save, the reply holds the bank account, PAN and other level-1 values that HR User may
not read. A member of staff saving their own mobile number gets back their own bank,
PAN, passport and health values. For staff that is their own data, so no one else's
privacy is broken, but the D6 wording "the person included" is not true. The v2 API
(`/api/v2/document` PATCH) did not leak. This is standard Frappe.

---

## Did the earlier fixes hold?

| 06 item | Now | How I proved it |
|---|---|---|
| B1 values in Error Log | **Fixed** | The manager ran a refused bulk edit on the report (phone, then passport). The Error Log row's variables hold the record ID and the value the **caller typed** (`data = {'cell_number': '9555555555'}`), and nothing stored on the report: no old phone, passport, bank or health marker. The test `test_alv266_a_refused_bulk_edit_logs_no_value_of_the_report` covers it. |
| B2 rename | **Fixed** | Report renaming own ID: 403 "Only HR can change an employee ID". Manager renaming the report: 403. Test `test_alv266_only_hr_renames_an_employee`. |
| Major: Share | **Fixed** | Share with one user, and with everyone: 403 for the manager (report's record) and the report (own record). Assigning the report's record to the unrelated colleague: 403 ("No permission to share"); the colleague still gets 403 reading it. Assigning to HR works but creates only a ToDo, no share, because HR already reads the record - harmless. |
| D6 Export off staff | **Done** | `export_query` and the Data Import template: 403 for manager and staff. |
| D6 level 3 | **Done, except the paths in Bad news 1-4** | Table below. |

### Level 3 (passport, dates, place, health, family, blood group, health insurance)

Manager on the report's record and on their own; staff on their own. "Hidden" means
the call worked and the values were not in the reply.

| Path | Result |
|---|---|
| `/api/resource/Employee/<id>`, `/api/v2/document/...` | Hidden |
| `frappe.client.get`, `get_value` (named fields and `*`), `get_list` (named fields and `*`), `/api/resource` list with fields | Hidden |
| `frappe.desk.reportview.get` with the fields, and with `max(passport_number)` | Hidden |
| Filter or sort on a level-3 field (`like 'PP...%'`), as a yes/no guessing trick | Refused 403 - cannot be used to guess values |
| List sidebar counts by blood group (`get_group_by_count`) | Refused 403 |
| Link search (`search_link`, `search_widget`, also with `searchfield=passport_number`) | Nothing found |
| Global search for the passport text | Nothing; the global search table holds no marker |
| `validate_link_and_fetch` asking for passport, health, bank | Returns only the ID |
| Print view (`/printview`, `get_html_and_style`) | Hidden (`printview.py:568` checks the level) |
| PDF download | Could not run: wkhtmltopdf is missing in the container (OSError). *Inference:* same renderer as print view, so hidden |
| Desk form (`getdoc`): the record | Hidden |
| Desk form (`getdoc`, `get_docinfo`): **change history** | **Leaks** - Bad news 1 |
| `Version` read directly | Refused 403 |
| Comments / communications timeline | Nothing |
| Employee list view settings | No level-3 column |
| Export, Data Import template | Refused 403 |
| Travel Request copy | **Leaks passport** - Bad news 2 |
| Save reply (own record) | **Shows own values** - Bad news 4 |
| Our own code (`alvoraa_portal`, `alvoraa_goals`, `alvoraa_hr_core`) | No reader of these fields (grep). `people_fields.py` keeps blood group and health off the Positions page |
| Email Queue, notifications | None sent; no Employee notification is set up on the site |

### Can a person raise their own rights now?

No. *Verified by running it.* The report, on their own record, sent passport, blood
group, `reports_to` (empty), `user_id` (the HR login) and `status = Left`. Each was put
back quietly; the database still held the old values. Their mobile number saved, as
intended. Level 3 gives staff nothing to write.

### ALV-249 after the rebase

Still holding. *Verified by running it.* Employee list: manager sees self and report;
report sees self; colleague sees self. Report to manager, report to colleague,
colleague to report, manager to colleague: all 403. Asking to skip permissions
(`ignore_user_permissions=1`, `ignore_permissions=1`, and the same through `/` with
`cmd`) changed nothing.

**The branch is 4 commits behind `origin/dev`** (`3eaa3b4d`: `portal.js`, tests for 071
and 078, docs). None touches this slice's files. It must be rebased before any push,
and the suites run again after.

## Minor

| # | Rating | Finding |
|---|---|---|
| m1 | Minor, P4 | A refused bulk edit logs the value the **caller** typed. That is their own input, not the other person's data. Acceptable. |
| m2 | Minor, P4 | The code note says System Manager reads level 3. On both test sites System Manager has no Employee permission rows at all, so a System Manager without an HR role reads no Employee. The code is right; the note is loose. |
| m3 | Minor, P3 | The D6 tests check `client.get` and `get_list` only. They would not catch Bad news 1 or 2. Add `getdoc` versions once Bad news 1 is fixed. |

Carried over from 06, not re-tested: refusals are not logged (ALV-272), readers can
attach files (ALV-273), and minors M1-M4.

## What I could not check

- **Production.** Whether the change-history leak has real rows there, and whether DTC
  uses Travel Request or Employee Promotion. Needs read-only database access to the
  production tenant.
- **PDF output** (wkhtmltopdf missing locally).
- **The Desk screen in a browser.** I made the same calls the form makes.

---

## Can ALV-266 be pushed to dev?

**Yes, after a rebase onto `origin/dev` and a fresh run of the suites.** Both blockers
and the Share finding are fixed and proven. Nothing in this slice causes or widens
Bad news 1-4; the slice closes several holes.

But **do not describe D6 or D2 as finished** - not to DTC, and not in a release note -
until Bad news 1 is fixed. That one is likely live on production now.

## What Surbhi must decide or accept

| # | Decision | My recommendation |
|---|---|---|
| A | Change history leaks bank, PAN, salary, passport and health to managers (Bad news 1) | Open a P0 ticket today. Fix by filtering version values in `getdoc`/`get_docinfo`. Ask for a read-only production count first, to know how many people saw what. If real rows exist, that is a question for counsel about notifying the people concerned |
| B | Travel Request passport copy (Bad news 2) | Clear the copy with one Property Setter; decide whether to blank existing copies |
| C | Employee Promotion salary copy (Bad news 3) | Put the two CTC fields at level 1, or accept in writing if DTC does not use promotions |
| D | Save replies show every field (Bad news 4) | Accept for a person's own record. For HR User, accept in writing or fix together with A |
| E | Push ALV-266 to dev | Yes, after rebase and suite run |

## Residual risk

| Risk | Kind | Owner | Accepted? |
|---|---|---|---|
| Change history shows locked values to anyone who reads the record | Dangerous debt - escalate now | Surbhi | Not accepted |
| Travel Request copies passport | Temporary debt (one Property Setter removes it) | Surbhi | Not accepted |
| Employee Promotion copies CTC | Temporary debt | Surbhi | Not accepted |
| Save reply shows the saver every field | Acceptable for own record; temporary debt for HR User | Surbhi | Not accepted |
| Refusals not logged (ALV-272), reader attachments (ALV-273) | Temporary debt, ticketed | Surbhi | Not accepted |

Nothing above has a name and a date yet.

**Subtract pass:** I dropped a full list of every call that returned 200 with nothing in
it (the level-3 table already says so), and a draft code sketch for the version filter
(the engineer's choice). Nothing else could go without losing a finding.
