# ALV-266 · Security and privacy review

Reviewed 31 Oct 2026 by `hrms-security-privacy-engineer`. Branch
`slice/alv-266-employee-write-fields` (commits fd64236e, cd225673 on top of `origin/dev`
9b99a421). I did not write or specify this slice, so there is no self-review conflict.

How I tested: I read the diff, `employee_field_rights.py`, `hooks.py` and the installed
Frappe 16.33.1 source. Then I attacked the rule over real HTTP on container
`hrlocal-266`, site `test266`. I used five throw-away logins: a manager with Employee Self
Service (ESS), that manager's report (ESS), a manager without ESS, an unrelated ESS
person, and an HR User. Every request went through the full request pipeline, including
the ALV-249 sign-in hook and the first-use password lock. Afterwards I deleted every
record, file, share, comment, log row and login I made, stopped the test server and
removed my scripts. Source code was not changed.

---

## Bad news first

1. **BLOCKER - the new hook writes the other person's existing data into the Error Log.**
   *Verified by running it.* A manager tried to change a report's mobile through bulk
   edit (`frappe.desk.doctype.bulk_update.bulk_update.submit_cancel_or_update_docs`).
   The hook refused, as it should. But Frappe's bulk action logs the failure as a
   "traceback with variables", and the hook's local variable `diff` holds the old and
   new value of every field the caller tried to change. The Error Log row contained
   `diff = {'changed': [('cell_number', '9111111111', '9777777777')], ...}` - the
   report's **real** phone number. The same happens for passport number, address,
   health details or any other field the caller names. The caller chooses which of the
   other person's values get written to the log. Only a System Manager can read the
   Error Log, so this is not stop-the-line, but it is personal data in a log, and this
   slice's code put it there.
   Fix (small): work out the changed field names in a separate small function that
   returns names only, so no value is ever held in the hook's own frame when it raises.
   Add a test that runs a refused bulk edit and asserts the Error Log row holds no
   field value.

2. **BLOCKER - a person can rename their own Employee ID.** *Verified by running it.*
   The report (ESS) called `frappe.model.rename_doc.update_document_title` with
   `name=HR-EMP-PROBE` on their own record. Frappe answered "Document renamed" and
   relinked everything that points at that ID. The hook allows it because it is their
   own record; ESS has write; Employee has `allow_rename` on. The rule says a person
   changes only their own personal details. The ID is not one of them. At DTC, 429
   logins hold ESS. A renamed ID breaks every outside sheet keyed by employee ID (DTC
   payroll runs from Excel workings) and rewrites many tables in one go.
   Before this slice, a manager could also rename a report's ID; that is now refused
   (verified). Renaming *into* another person's ID (merge) is refused too (verified).
   Fix (small): one `before_rename` check on Employee that refuses anyone outside
   HR User / HR Manager / System Manager. Add a test.

3. **MAJOR (P1) - a manager with ESS can show a report's whole record to anyone,
   including "everyone".** *Verified by running it.* ESS holds the **Share** right on
   Employee (`tabCustom DocPerm`, ESS, level 0, share=1), and the hook says yes to every
   check that is not "write". The manager shared the report's record with an unrelated
   colleague, and with "everyone". The unrelated colleague, and a login with no link to
   either person, then read the passport number, health details, phone and address, and
   the record showed up in their Employee list. This walks straight past the ALV-249 row
   scope. **Assigning** the record to someone does the same thing silently: Frappe
   shares it with the assignee ("Shared with the following Users with Read access").
   Any ESS person can also share their own record with everyone. This is not new in this
   slice, but the slice's rule says non-HR people change nothing about another person's
   record, and "who may see it" is part of that.
   Fix (configuration, cheapest): take the Share right off ESS on Employee (one line in
   `apply()`), or have the hook answer "share" the same way as "write". Either also stops
   assignment, because assigning needs Share. Add a test.

4. **MAJOR (P2) - refusals are not actually logged.** *Verified by running it, plus the
   installed Frappe source.* No ALV-266 line reached `security.log` (bench or site)
   after about 20 refusals. Frappe sets every `frappe.logger()` to ERROR unless the
   process runs as the dev server (`frappe/utils/logger.py:12` and `:80`;
   `DEV_SERVER` in `frappe/__init__.py:85`). `log_refusal` writes at WARNING, so it is
   thrown away. Nothing in our code or deploy files raises the level. *Inference:* the
   same is true on production, for SEC-17 and every other `refuse()` in the product. I
   could not check production. This is not new, but 05 lists "refusals logged without
   values" as a benefit, and today nobody would find out about a manager trying to
   change a report's record.

5. **MAJOR (P2) - anyone who can read a record can attach files to it.** *Verified by
   running it.* `frappe.client.attach_file` (without `docfield`) needs only read. Both
   managers (with and without ESS) attached a private file to their report's Employee
   record. It shows on the record's attachment list. The person and HR would see an
   attachment they did not add, and could mistake it for an HR document. With
   `docfield=image` the hook refuses and the file is rolled back (verified). The upload
   route (`/api/method/upload_file`) is refused for a manager (verified).
   This is standard Frappe behaviour, not new. Fix if wanted: a File `before_insert`
   check that an Employee attachment needs write on that Employee.

---

## Did the rule hold? Write paths tried on another person's record

Manager **with** ESS on their report, and manager **without** ESS on theirs. "Refused"
means nothing changed (checked by re-reading the record as HR after each call).

| Path | With ESS | Without ESS |
|---|---|---|
| `/api/resource/Employee/<id>` PUT (mobile; reports_to) | Refused, new message | Refused, new message |
| `/api/v2/document/Employee/<id>` PATCH | Refused (403) | Refused (403) |
| `frappe.client.set_value` (single field; JSON of `status=Left`) | Refused | Refused |
| `frappe.client.save` | Refused | Refused |
| `frappe.desk.form.save.savedocs` (the Desk form's Save) | Refused | Refused |
| `frappe.client.bulk_update`, Desk bulk edit | Refused, but see Blocker 1 | Refused, but see Blocker 1 |
| `frappe.client.set_multiple` | Does not exist in v16 | - |
| Delete (`/api/resource` DELETE, `frappe.client.delete`) | Refused (no delete right) | Refused |
| Rename ID / change title | Refused | Refused |
| Create a new Employee (`insert`, POST) | Refused (no create right) | Refused |
| Child rows alone: Employee Education, Internal Work History (`frappe.client.insert`); child via `/api/resource` | Refused | Refused |
| `erpnext...employee.create_user` (gives the record a login) | Refused - this was open to a manager before | Refused |
| `deactivate_sales_person` | Refused | Refused |
| Tags (`add_tag`) | Refused | Refused |
| `frappe.model.workflow.apply_workflow` | Refused (no workflow on Employee) | Refused |
| `attach_file` with `docfield=image` | Refused, file rolled back | - |
| `upload_file` (plain, and as the photo) | Refused | Refused |
| `attach_file` without a field | **Allowed** (finding 5) | **Allowed** |
| Share with read (one user, everyone) / assign | **Allowed** (finding 3) | Refused (no share right) |
| Share with write | Refused | Refused |
| Comment (`add_comment`) | Allowed (minor, below) | Allowed |
| Like (`toggle_like`) | Allowed (minor, below) | Allowed |
| Data Import | Not run: ESS has no import right (read from `tabCustom DocPerm`) | Same |
| Record outside their tree, or HR's own record | Refused, same message | - |

## Own-record privilege escalation (ESS staff, and an ESS manager)

| Attempt on own record | Result |
|---|---|
| Set `reports_to` to someone else (make yourself report elsewhere / widen a tree) | Put back quietly, unchanged |
| Set own `user_id` to another person's login | Put back, unchanged |
| Set own `status` to Left, or move `company` | Put back, unchanged |
| `department`, `designation`, `employee_number`, `company_email`, `create_user_permission` | Put back, unchanged |
| Add a row to own Internal Work History (form, or child insert) | Put back, unchanged |
| `attach_file` with `docfield=user_id` | `user_id` put back; the file stays on own record (harmless) |
| Change own mobile, passport, education | Saved - as intended |
| Rename own ID | **Renamed** (Blocker 2) |
| Merge own record into HR's | Refused |

A manager cannot change a report's `reports_to` to widen their own tree: refused on
every path above.

## Other checks

- **The refusal message** carries no personal data: "Only HR can change another
  person's employee record. Ask HR to make this change." *Verified by running it.*
- **The log line** (when it is written) holds the login, the Employee ID and the rule,
  never a value. *Verified in code* (`hrms/alvoraa_hr_core/access.py:28-48`). But see
  finding 4: it is not written at all today.
- **Quiet put-back cannot be used to probe.** It only happens on the caller's own
  record, which they can read anyway. On anyone else's record the hook refuses before
  any put-back. Out-of-scope IDs answer 403 and missing IDs 404, which a plain read
  already shows; the hook adds nothing.
- **Hook order.** Frappe runs the hook before role rights and User Permissions
  (`frappe/permissions.py:239`). So it is checked first on every path that asks for
  write with a document. *Verified in code.*
- **`is_own_record`** reads `user_id` from the database, not from the incoming
  document, so a forged `user_id` in the request cannot make someone else's record
  "own". *Verified in code* (`access.py:56-61`).
- **First-use password lock and ALV-249.** A login that has not chosen a password is
  stopped at every `/api/` call before the hook runs (seen when I first signed in).
  ALV-249's sign-in rows were created normally and did not change the result.
- **Photo upload.** Own photo upload works. A manager cannot set a report's photo
  (refused, file rolled back).
- **Whitelisted code that writes Employee directly.** Grep of `alvoraa_portal`,
  `alvoraa_goals`, `hrms` and `erpnext` for `db.set_value("Employee"`, `db_set`,
  `db_update` on Employee: `home_people.py:148` writes the caller's own record only;
  `attach_my_document` (`hr_api.py:3947`) uses the caller's own active Employee;
  `backfill_checklists` needs HR Manager; Position Assignment delegation writes
  approvers but needs Write on Alvoraa Position, which only HR Manager and System
  Manager hold on `test266`. I found no path that lets a non-HR user write another
  person's Employee fields.

## Minor findings

| # | Rating | Finding |
|---|---|---|
| M1 | Minor, P3 | A manager can add a **comment** or a **like** to a report's record (needs only read). Standard Frappe. The comment is visible to the person and HR. *Verified by running it.* |
| M2 | Minor, P3 | `is_own_record` does not check `status = "Active"` (lesson 3). A leaver whose login is still enabled can still edit their own personal details. Own record only. *Verified in code.* |
| M3 | Minor, P3 | `MANAGER_EDITABLE` is not limited to managers. If a field is ever added, anyone who can reach someone else's record (including through a share) may change it, and may then share it with write. Harmless while the list is empty. *Verified in code* (`employee_field_rights.py:283-286`). |
| M4 | Minor, P4 | The Positions page still sets `may_edit_employee` from "may this login write Employee at all" (`register.py:464`), so an ESS user who can open Positions sees "Set manager", and the form then opens read-only. Cosmetic. |

## Personal data that stays readable (for Surbhi to decide; not caused by this slice)

*Verified by running it.* Through the ALV-249 tree, a manager (with or without ESS)
reads a report's **passport number, health details, family background, blood group,
date of birth and current address**. With ESS they can also **export** these to CSV
(ESS has the Export right on Employee): the export returned the report's passport and
health details. Bank, PAN, salary and other level-1 fields are hidden (verified). Health
details and passport are not needed to manage someone day to day. Removing them from
managers would be a field-level change (a read level for those fields), not a new
feature.

## Worries (not proven as findings)

- `attach_my_document` accepts any `file_url`. I did not check whether a person could
  point their own checklist row at another person's private file URL and so make HR
  open it as "their" document. Needs one test.
- Frappe's "traceback with variables" may capture other hooks' locals the same way as
  Blocker 1. I only checked this hook.

## What I could not check

- **Production's log level and share settings.** Needs read-only access to the
  production bench (log files and `tabCustom DocPerm` for Employee). Findings 3 and 4
  are inferences for production.
- **The Desk screen by hand.** I used the same calls the Desk form makes, not a browser.
- **Data Import by a non-HR user** - not possible today (no import right), so not run.
- The full `alvoraa_portal` and `alvoraa_goals` suites (05 says they were not run).

## Process note

There is no `01c-security-privacy-requirements.md` for this slice, so there were no
SEC/PRIV items to mark met or not met. I tested against Surbhi's rule as written in 04.

---

## What Surbhi must decide or accept

| # | Decision | My recommendation |
|---|---|---|
| D1 | Fix Blocker 1 (values in Error Log) before this goes to dev | Yes. Small change plus one test |
| D2 | Fix Blocker 2 (own ID rename) in this slice | Yes. One `before_rename` check plus one test |
| D3 | Take the Share right off ESS on Employee (stops share-to-everyone and assign-shares) | Yes, in this slice: it is one line of configuration, and it is the same promise |
| D4 | Refusal logging is silent everywhere (finding 4) | Separate ticket now; raise the `security` logger to INFO/WARNING at start-up. Until then, accept in writing that refusals leave no trace |
| D5 | Attachments by readers (finding 5) | Separate ticket, or accept in writing |
| D6 | Should managers keep reading reports' passport and health details, and exporting them? | Hide passport and health details from non-HR (same field-level mechanism), and drop Export from ESS on Employee. Needs your yes |
| D7 | Minor items M1-M4 | Accept as known; M2 and M3 tracked |

## Residual risk

| Risk | Kind | Owner | Accepted? |
|---|---|---|---|
| Values of another person's record in the Error Log via bulk edit | Dangerous debt - fix before dev | Engineer | Not accepted |
| Own Employee ID rename | Dangerous debt - fix before dev | Engineer | Not accepted |
| Share / assign widens who reads a record | Dangerous debt - escalate now | Surbhi | Not accepted |
| Refusals not logged anywhere | Temporary debt (removed by raising the log level) | Surbhi | Not accepted |
| Readers can attach files | Temporary debt | Surbhi | Not accepted |
| Managers read passport / health details | Intentional trade-off only if Surbhi says so | Surbhi | Not decided |
| Comments, likes, leaver self-edit, `MANAGER_EDITABLE` scope | Acceptable simplification | Surbhi | Not decided |

Nothing above has been accepted by anyone yet. Each needs a name and a date.

**Subtract pass:** I removed a draft section re-listing every SELF_EDITABLE field (04
already has it) and a proposed new test file layout (the engineer's choice). Nothing
else could go without losing a finding.
