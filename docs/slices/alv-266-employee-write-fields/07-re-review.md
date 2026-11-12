# ALV-266 · Re-review (delta only)

Reviewed 1 Nov 2026. Branch `slice/alv-266-employee-write-fields`, 7 commits on
`1b02705f` (`00679387` .. `c60503da`). All by the same author. `origin/dev` has since
moved to `3eaa3b4d` (4 commits: 071 budget, 078 notes, 079 docs). None of them touches
`employee_field_rights.py`, `hooks.py` or `access.py`, so a rebase should be clean
(inferred from `git diff --name-only`; not rebased by me).

## Verdict: SHIP WITH FIXES

M1 is really fixed, and the new level 3 works as built. **But two side doors still show
a report's passport and health details to their manager**, so the notes' promise
"nobody else sees them" is not true yet. Neither door is new: before D6 a manager read
these fields outright. D6 makes things much better, not worse. So these are P2: fix
them, or Surbhi accepts them in writing, before the push.

What I ran myself, all on `hrlocal-266`, site `fresh266`:

- `test_employee_write_fields_alv266`: **22 tests, OK.**
- `test_employee_field_rights_alv215`: **20 tests, OK.**
- `test_my_photo_078`: **34 tests, OK.**
- Three scripts of checks as real logins, each **rolled back** (nothing kept). Results
  are quoted below.

Not run by me: the other modules in 05, the full suite, anything on DTC or aahr.

---

## Major

### MA1 · P2 · The form's change history shows the old and new passport and health values (proven)

**What happens.** When HR changes a passport, blood group or health detail, Frappe
writes a change record (a "Version"). The Employee form loads the last 10 of these for
anyone who can open the record. Frappe's `get_versions`
(`frappe/desk/form/load.py:241-250`) reads them with `frappe.get_all` and never checks
field levels.

**Scenario, run on `fresh266`, rolled back:** HR sets passport `VER-PASS-SECRET` and
blood group `AB-` on the report's record and on the staff member's own record. Then:

- `alv266.manager` opens the report (`getdoc`): the passport field is hidden, but the
  history holds `VER-PASS-SECRET`. **Leak: True.**
- `alv266.ess` opens their own record: same. **Leak: True.**
- Listing `Version` directly is refused for both. Only the form's history leaks.

**Why it matters.** D6 says only HR sees these. A manager sees the value every time HR
changes it, before and after. `getdoc` is open to any logged-in user through the API,
so the portal hiding Desk is not a defence.

**Not new, and wider than D6.** The same path shows level-1 bank and PAN changes to
anyone who can open the record. That has been true since ALV-215 (inferred: same code
path; I did not run it for bank fields).

**Smallest fix.** This needs a decision, not a quick patch. Turning off change tracking
on Employee would remove the audit trail, which is worse. Owner:
`hrms-security-privacy-engineer`. Options:
(a) Surbhi accepts it in writing for this push, with a ticket;
(b) a small override of the form load that drops locked fields from the history for
readers without that level.
I recommend (a) now and (b) as its own ticket, because it covers bank details too.

### MA2 · P2 · Travel Request copies the passport number where the manager can read it (proven)

**What happens.** Frappe HR's Travel Request has `passport_number` with
`fetch_from: employee.passport_number` (`hrms/hr/doctype/travel_request/travel_request.json:145`).
The server copies the value when the request is saved, without checking field levels.
The copy sits at level 0.

**Scenario, run on `fresh266`, rolled back:**

- Staff member saves their own Travel Request: it holds their passport number, and
  they read it back (`TR-PASS`). So the person still sees their own passport here.
- A Travel Request for the manager's report: the manager reads it with
  `frappe.client.get` **and** lists it with `get_list`: `REPORT-PASS` shown both times.

**Why it matters.** It is a copy outside level 3. The portal does not use Travel Request
(grep of `alvoraa_portal`: no hits), but Desk and the REST API reach it, and ESS has
read and create on it.

**Smallest fix.** One Property Setter on `Travel Request.passport_number`: either a
permission level that only HR reads, or clear `fetch_from`. First count Travel Requests
on DTC and aahr (read-only). If there are none, accepting it with a ticket is fine.
**Not checked:** row counts on any tenant.

---

## Minor

### m1 · P3 · HR changing their own passport gets the wrong words (proven)

HR Manager changing their own passport or blood group is refused, which is the ALV-215
rule working as the notes say. But the message reads "You cannot change your own job,
pay or bank details." A passport is none of those. Fix: say "these details" or "your
HR-held details". One string in `own_record_message()`.

### m2 · P3 · The M1 fix lets HR edit their own work history and documents rows (proven)

`refuse_own_locked_change` now skips every table (`employee_field_rights.py:205`). So HR
can add a row to their own `internal_work_history` (proven: saved OK) and, by the same
rule, their own `employee_documents` rows (inferred). Non-HR staff are still put back by
Frappe. This is **not a step back**: before ALV-266 both tables were level 0 and anyone
could edit their own. Label: **acceptable simplification**. Write it in 05, or narrow
the skip to `documents_summary` and rows that code changes, if Surbhi wants it tight.

### m3 · P3 · A tenant's own HR-like role gets no level 3 (inferred)

Level 3 goes only to HR User, HR Manager and System Manager. A tenant role such as "HR
Executive" with Employee read keeps level 0 and 2 but loses passport and health after
the migrate, and any other role's level-3 row is deleted. That is the rule as built.
**Not checked:** which roles read Employee on DTC and aahr. Run a read-only list of
Employee `Custom DocPerm` rows on both before the migrate.

### m4 · P3 · A tenant that made one of these fields mandatory (not checked)

On `fresh266` none of the nine is mandatory, and the only `depends_on` link is between
two level-3 fields (`health_insurance_no` on `health_insurance_provider`). But if a
tenant set, for example, `blood_group` as mandatory in Customize Form, a staff member's
own save would fail with a "missing value" error on a field they cannot see (inferred
from Frappe's mandatory check). Check Property Setters `reqd` on these nine fields on
DTC and aahr.

### m5 · P3 · Test gaps (my manual checks cover them, the suite does not)

- HR User writing a level-3 field is not tested. I proved it: HR User has write at
  0, 2 and 3, saves passport and blood group on a report, and lists them.
- HR's export is called but its content is not checked. I proved it: the CSV holds
  passport and blood group.
- Removal of another role's level-3 row is not tested. I proved it: added a level-3 row
  for `Employee`, ran `apply()`, the row was gone.
- Raising a field from 2 to 3, and never lowering one at 1, are not tested. I proved
  both.

---

## Nits (P4)

- `people_fields.py` docstring says field levels leave read open. Level 3 now closes
  read. The allow-list is still the control, so nothing breaks.
- The rollback step in 05 does not mention putting back Export and Share on Employee
  Self Service. Reverting leaves the stricter state, so nothing is exposed.

---

## What I checked and found fine

| Question | Answer | Evidence |
|---|---|---|
| Is M1 really fixed? | **Yes** | Expired document + own mobile change: old check → refused, new check → saved. Rebuilt full name: old → refused, new → saved. So both tests can fail |
| Level-3 rows | HR User and HR Manager have read+write at 0 **and** 3 on `fresh266`. System Manager has no Employee rows at all there, so it gets none - correct, it follows level 0 | `Custom DocPerm` dump |
| `apply()` runs twice safely | Yes | Rows and Property Setters identical after two runs (72 → 72) |
| Never lowers | Yes | `blood_group` set to 1 stays 1; set to 2 goes back to 3 |
| HR saves a level-3 field | Yes, both roles | HR Manager in the test; HR User in my script |
| HR import and export | Included | HR User may write level 3, so the import check allows the column; export CSV holds the values |
| Can staff guess a value by filtering? | No | Filter on `passport_number` or `blood_group` as manager: "You do not have permission to access field" (list and report view) |
| Desk form for staff and managers | Fields hidden, no error | `getdoc` returns them as empty; other fields intact |
| Anything that crashes | Nothing found | Grep of `erpnext`, `hrms`, `india_compliance`, `alvoraa_portal`, `alvoraa_goals`: no code reads these fields for a non-HR user except the `/hrms` Profile (blood group now blank, as the notes say) and Travel Request (MA2). `my_profile.py`, Positions, directory, mini profile never use them |
| Print | Hidden | `printview.py:568` checks field levels |
| Export removed for staff | Yes | Tested; HR keeps it |
| ALV-215 own-record rule covers level 3 | Yes | HR's own passport change refused (wording: m1) |
| Rename | Only HR | Tested for own, a report, and a merge |
| Refusal log | Field names only | `changed_fieldnames` returns names; the security review owns the detail |

## Non-functional, before and after (this round)

| Dimension | Notes say | I found |
|---|---|---|
| Performance | neutral | Neutral. Two more permission rows per HR role |
| Security | improves | Improves. Two side doors left (MA1, MA2) |
| Reliability | M1 fixed | Fixed. One untested risk on tenants with mandatory fields (m4) |
| Data integrity | improves | Improves. HR can edit own history tables (m2), not a step back |
| Compliance / privacy | improves | Improves, but "nobody else sees them" is not yet true |
| Maintainability | neutral | Neutral. One more level to remember; the comments explain why level 3 |

## What to delete

Nothing. Level 3 is the smallest way to say "HR User yes, staff no" without giving HR
User the bank fields at level 1. The Export removal is one loop entry.

## What was done well

- **Level 3 instead of widening level 1.** It keeps bank details HR Manager only while
  letting HR User handle passports.
- **The M1 tests were written to fail on the old code**, and they do.
- **The notes list every screen that showed these fields**, with before and after.
  That made this review fast. It missed two (MA1, MA2), both outside the screen list.

## Confidence

- **Proven:** M1 fix, level-3 rows and saves, idempotence, never-lower, filter
  refusal, export, MA1 and MA2 leaks, the HR own-record refusal.
- **Inferred:** level-1 bank values leak through form history the same way (same code);
  the HR documents-row edit (same skip as work history).
- **Not checked:** DTC and aahr roles, mandatory settings and Travel Request counts;
  the form's look on a phone (hidden sections); the full suite.

## For Surbhi

1. **Decide MA1 and MA2:** fix, or accept in writing with a ticket. They are not caused
   by this slice, but they break its promise.
2. Fix the message wording (m1). Five minutes.
3. Before the migrate on DTC and aahr, run three read-only checks: Employee roles,
   mandatory settings on the nine fields, Travel Request count.
