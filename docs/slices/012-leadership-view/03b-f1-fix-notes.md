# Slice 012 · F1 fix notes — org chart access settings

Finding F1 (Major) in `06-security-review.md`. Requirement SEC-18 in `01c`. The user said
"fix first" on 2026-09-17. The approach is the reviewer's recommendation, which the user
accepted. Branch `slice/012-f1-org-access`, from local `dev` at `24eb10a`.

## What was wrong

`set_cover_setting` let an HR Manager write any of its keys. Two of them decide who sees
the whole org chart. One call could add "Employee" to the full-reach roles and show every
employee the whole company. Nothing recorded who did it.

## What changed

| File | Change | Mechanism |
|---|---|---|
| `hrms/hrms/alvoraa_org_structure/settings.py` | New `ACCESS_GRANTING` set. `set_cover_setting` sends those keys to a new `_set_access_setting`: System Manager only; anyone else gets a plain message, a `PermissionError` and a `SEC-18` refusal line through `access.refuse`. A real change writes a `Version` record, then the default, then one commit. A security log line `"event": "changed"` names the key (no values). Other keys: unchanged. | Extend (our own module) |
| `alvoraa_portal/alvoraa_portal/tests/test_org_access_settings_012f1.py` | New pin tests (6). | Test |
| `alvoraa_portal/alvoraa_portal/tests/test_portal_security_010.py` | One row at the end of `CEILINGS`: `settings.py` at 1 `ignore_permissions`. | Test |

### Which keys grant access, and why

| Key | Access-granting? | Reason |
|---|---|---|
| `alvoraa_org_full_reach_roles` | Yes | Named in SEC-18. Any role listed roams the whole chart. |
| `alvoraa_org_managers_see_all` | Yes | Named in SEC-18. Turns on whole-chart reach for every manager. |
| `alvoraa_org_reach_up`, `alvoraa_org_reach_down` | Yes | `api.reach()` uses them as the window for everyone else. Setting 99 gives every employee close to the whole chart, which is the same harm. |
| `alvoraa_cover_*` (8 keys) | No | Cover alerts, load cap and allowance rules. They change nobody's view of anybody. |
| `alvoraa_org_span_wide`, `alvoraa_org_span_narrow` | No | Only decide which managers get flagged in org health, which HR already sees. |

### The change record: a `Version` row, not only a log line

- **What it holds:** `owner` (who), `creation` (when), `docname` = the key,
  `data` = `{"changed": [[key, old, new]]}`, `ref_doctype` = `DefaultValue`.
- **Why `Version`:** it is written in the same database transaction as the change, so a
  change can never exist without its record. It lives in the database, so a redeploy or log
  rotation cannot lose it. Frappe's Log Settings do not clear it (checked
  `clear_old_logs` in v16.33.1: `Version` is not in the list). Only System Manager can read
  it. This fits the "settings history for the life of the tenant" answer in `01c` Q10.
- **The log file line** (`frappe.logger("security")`) is kept for both refusals and changes,
  so one grep finds both. It carries the key only, never a value, as `access.py` does.
- **Find every change:** `frappe.get_all("Version", filters={"ref_doctype": "DefaultValue"}, fields=["owner","creation","docname","data"])`.
- `ignore_permissions` on the `Version` insert is deliberate: nobody has create on
  `Version`, and Frappe writes its own versions the same way. The caller has already been
  checked as System Manager.

## Callers checked

| Caller | Result |
|---|---|
| `alvoraa_portal/www/hrms-employee.html` | Does not call `set_cover_setting` or `get_cover_settings` (grep). **No page change needed**, and no HR Manager is shown a control that is now refused. |
| `hr_api.set_org_setting` / `get_org_setting` | Separate allowlist (G2 fix), `kra_link_mandatory` only. Unchanged. |
| `hrms/alvoraa_org_structure/api.py` `reach()` | Reads the keys with `settings.get`. Reading is unchanged. |
| `test_cover_policy.py` (unknown key refused), `test_reach.py`, `test_metrics.py`, `test_portal_security_010.py` `_OrgBase` | Write defaults with `frappe.db.set_default` directly, not through the endpoint. Unaffected, and all pass. |
| Desk / REST | The only write path for these keys is this whitelisted function. `DefaultValue` is a child table with no permission rows (checked in v16.33.1), so desk and `/api/resource` cannot write it directly. |

## Tests and real results (test_site, 2026-09-17)

| Run | Result |
|---|---|
| `alvoraa_portal.tests.test_org_access_settings_012f1` | Ran 6, OK |
| `hrms.alvoraa_org_structure.tests.test_cover_policy` | Ran 23, OK |
| `hrms.alvoraa_org_structure.tests.test_reach` | Ran 13, OK |
| `hrms.alvoraa_org_structure.tests.test_metrics` | Ran 24, OK |
| `hrms.alvoraa_org_structure.tests.test_org_structure` | Ran 33, OK |
| `alvoraa_portal.tests.test_portal_security_010` | Ran 45, OK |
| Full `alvoraa_portal` | Ran 1,079 (540 + 539). Only the known 14: `test_leave_year` 3 errors, `test_invoicing` 1 failure + 10 errors. Nothing else failed. |
| Full `alvoraa_goals` | Ran 18, OK (2 skipped) |

`python scripts/check_app_integrity.py`: "OK - all consistent" (559 checks) before each commit.

Pin tests, one per rule:
- HR Manager refused on both named keys; value unchanged; no `Version` row; refusal logged as SEC-18.
- Plain employee refused on an access key; refusal logged.
- System Manager allowed; one `Version` row with the System Manager as owner and the exact old and new values.
- Saving the same value again writes no record.
- HR Manager still changes an ordinary cover key.
- The two named keys stay in `ACCESS_GRANTING`.

## Non-functional check (against the code written)

| Dimension | Verdict | One line |
|---|---|---|
| Performance | Neutral | One extra read and one insert, only when a System Manager changes one of four keys. |
| Security | Improves | HR Manager can no longer widen the org chart; every refusal is logged. |
| Reliability | Neutral | Change and record commit together; a failed record insert stops the change. |
| Scalability | Neutral | Rare admin action; nothing grows with headcount. |
| Maintainability | Neutral | One small set and one function in the module that owns the keys; pinned by tests. |
| Data integrity | Improves | A before-and-after record exists for every change of who sees whom. |
| Compliance / privacy | Improves | SEC-18 met for these keys: System Manager only, change record kept. No personal data in logs. |

## Personas

- **CXO / System Manager:** can still change all settings; changes to the four access keys now leave a record.
- **HR Manager:** still changes cover and span settings. Refused on the four access keys with "Only a System Manager can change who may see the org chart. Ask your System Manager to make this change."
- **Employee:** no change to what they see. Refused as before, and now logged if they try an access key.

## Known gaps

- There is no screen for these settings today, so a System Manager changes them through the
  API or console. That was already true.
- A Frappe personal-data deletion request for a System Manager's user (`user_data_fields`
  lists `Version` as strict) would delete the `Version` rows they own. That only happens on
  an explicit erasure request. Worth knowing for the retention decision; not changed here.
- The reach levels were added to the access-granting set by my reading of "keys that widen
  who sees whom". If the user wants HR Managers to keep editing the reach levels, it is a
  one-line change to `ACCESS_GRANTING`.

## What else moved while I worked

- `24eb10a` (012 documents, committed by the 010 session) arrived on local `dev` before I
  branched. Documents only; my branch starts on top of it.
- Main checkout had another session's uncommitted edits (`alvoraa_position.py`,
  `ux-learnings.md`, `KPI_AUTOMATION_BACKLOG.md`, a deleted `OBJECTIVES_KPI_REQUIREMENTS.md`).
  None are in files I changed; untouched.
- No conflicts. `merge --ff-only` succeeded.
