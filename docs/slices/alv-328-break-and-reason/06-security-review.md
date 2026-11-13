# ALV-328 - Security review

Written 13 Nov 2026 by `hrms-security-privacy-engineer`. Reviewed: commit `ccca2b6c` on
branch `slice/alv-328-break-and-reason` (parent `c5d57333` = `origin/dev`), worktree
`.claude/worktrees/alv-328`. Requirements: `03-security-privacy.md` (SEC-1..11, PRIV-1..4,
its Re-check, and Surbhi's answers Q-1, Q-2, Q-E), `04-functional-spec.md` (Q-A..Q-D),
`05-impact-and-strategy.md` (D1 no, D2 no change, D3 get_list accepted).

**Same author warning (lesson 6).** The security role wrote `03`, including SEC-6 and SEC-7.
This review is that role checking its own requirements against someone else's code. A
second pair of eyes on SEC-6 and SEC-7 (the punch rule) is still asked of the reviewer.

## Verdict

**No blocker. 13 Met, 2 Partly, 0 Not met.** The two "Partly" items are missing tests, not
missing controls. One new Minor finding: an explicit document share still overrides the new
"punches are read-only" rule (Frappe's design). It needs one read-only count on DTC before
release.

## Tests run (on `test328`, a fresh site built from this worktree; files checked identical)

| Module | Result |
|---|---|
| `test_punch_rights_alv332` | 17 tests, OK (run alone). A first run deadlocked because another session ran the same module on the same site at the same time; not a code fault |
| `test_break_and_reason_alv328` | 2 + 16 tests, OK |
| `test_portal_security_010` (the `ignore_permissions` ceiling) | 45 + 5 tests, OK |

Nothing was called over HTTP. The tests use the Python functions that REST, Desk and
`frappe.client` call (`frappe.has_permission`, `frappe.get_list`, `frappe.client.*`). No
browser was run. DTC and dev were not touched.

## Requirement by requirement

| Req | Verdict | Mechanism (verified in code) | Proof |
|---|---|---|---|
| SEC-1 New values only through month() and person(), after their checks | **Met** | Diff adds 0 `@frappe.whitelist`. Break and reason are added after `_subject` in `attendance_correction.month()` (`:608`, `:816-819`) and after the `allowed` check in `attendance_analytics.person()` (`:646-657`). The website "/" cmd path reaches only whitelisted functions, so it meets the same checks | `test_alv328_a_colleague_is_refused_and_gets_nothing` (month and person raise PermissionError) |
| SEC-2 No new bypass | **Met** | Reason read in the existing Attendance `get_list` (`attendance_correction.py:492-499`). person()'s punches read with `frappe.get_list` (`attendance_analytics.py:646`). No new `ignore_permissions`, `get_all` or SQL on Attendance or Employee Checkin in app code. The one new `frappe.db.sql` (`field_app_access.py:270-272`) is the permission rule itself, parameterised | `test_portal_security_010` ceiling green, ceiling file untouched; `QueryCounts` (one Checkin read) |
| SEC-3 Break only from punches the caller may read | **Met** | Both screens build the break only from punches returned by `get_list`, which applies `checkin_query_conditions`. `breaks_by_day` returns nothing when no punch came back (`payroll_rules_apply.py:406-407`), so no "missing" state is made from an empty list. D3 confirmed: this is safe | `test_alv328_a_skip_level_manager_gets_no_break_by_default` (month and person), `..._with_the_switch_on_...` |
| SEC-4 Frappe doors closed to a colleague for the reason | **Met** | Own-record User Permission, unchanged | `test_alv328_frappe_doors_keep_a_colleague_out_of_the_reason`: `get_list` (what REST list and report view use), `client.get_value`, `client.get`, with a negative control that opens the list when the row is deleted. `frappe.desk.reportview.get` is not called directly [Inference: it goes through `get_list`] |
| SEC-5 Reason shown as text | **Partly** | `portal.js:6133` passes `rules_why` through `gpEsc` → `esc` (`:219`, escapes `& < > "`); the date sits in a double-quoted attribute and is escaped too | **No test.** AC-21 was not run; there was no browser pass (`06-implementation-notes.md`, "Known gaps") |
| SEC-6 One rule, list and record agree | **Met** | `_line_sql` (`field_app_access.py:209-224`) is the one SQL text used by `checkin_query_conditions` (`:227-242`) and `checkin_has_permission` (`:246-272`). Screens use `get_list` (D3) | `test_alv328_the_list_and_the_single_record_agree` (4 users, switch off and on, record by record) |
| SEC-7 Outside HR, read only | **Met** | `_READ_RIGHTS = ("read", "select")` (`:198`); self `:268` (read/select, or create of a new own punch); others `:269` (anything but read/select → False, `ptype` None → False). Frappe v16 calls the hook first and returns `{ptype: 0}` on False (`frappe/permissions.py:239-241`). Photo File write/delete also needs the punch's write, so it is closed too [Inference from Frappe's File rule] | `test_alv332_the_doors_rest_uses_refuse_a_change` (`client.set_value`, `client.delete` as self and as direct manager), `test_alv332_the_refusal_is_real` (negative control), `..._a_manager_cannot_file_a_punch_for_a_report` (D1). Skip-level manager with the switch on: only `has_permission("write")` is tested, not the four doors (P4 gap) |
| SEC-8 Leavers and inactive stay out | **Met** | `_viewer` needs an Active Employee (`:182-188`). `_line_sql` keeps `status = 'Active'` at every level, so a report under a Left manager is not reached | `test_alv328_on_the_whole_active_line_and_still_read_only` (report under a Left manager and an Inactive report excluded). "Top manager Left → empty list" is not tested (P4 gap); the code line is verified |
| SEC-9 Only a System Manager changes the setting | **Met** | `_refuse_whole_line_change` (`field_app_settings.py:234-249`) runs first in `validate_hr_settings` (`:260`), before the `F_ENABLED` early return (`:261`). Compares old and new with `cint`. No app code saves HR Settings with `ignore_validate` or sets this field with `db.set_single_value` (grep). Nobody holds `import` on HR Settings (`hr_settings.json`) | `test_alv328_hr_manager_is_refused_on_every_door` (Desk save, `client.save`, `client.set_value`), `..._may_still_save_other_settings`, `..._a_system_manager_may_flip_it_...`. REST PUT is the same `doc.save()` path [Inference]; the Data Import assertion was not written (P4) |
| SEC-10 The flip is in history | **Met** | HR Settings `track_changes` = 1 (read in the bench) | `test_alv328_a_system_manager_may_flip_it_and_it_is_recorded` (0 → 1 makes one Version row). Reverse flip and "refused leaves no Version" not tested (P4); a throw rolls back, so no row [Inference] |
| SEC-11 Photo log, and honest wording | **Partly** | Wording met: the field's description (`field_app_settings.py:598`) says a punch includes its photo and location, and does not claim every view is logged. `log_photo_view` unchanged. Surbhi accepted the gap (Q-E, 12 Nov 2026) | **No test.** AC-35 (Desk open leaves a log row with the switch on) and the "REST GET leaves no row" test were not written (`06-implementation-notes.md` row AC-35) |
| PRIV-1 No break on any group view | **Met** | `breaks_by_day` has two callers only, month() and person() (grep). Group tables in `portal.js` unchanged; the Break column is only on the one-person tables | `test_alv328_no_break_on_any_group_view` (summary mine/team direct/deep, organisation, `team_days`, `filter_options`; no `"break` in any response) |
| PRIV-2 Nothing new stored, cached or logged | **Met** | One Custom Field, on HR Settings (the switch), as changed by the spec. No field on Attendance or Checkin, no write, no cache key; switch read with `cache=False` | Diff review; `test_alv328_the_field_is_there_and_off_on_a_fresh_site` |
| PRIV-3 No break or reason in a log or error | **Met** | The diff's only new `throw` is the settings refusal, which names nobody. No new `log_error` or logger | Diff review |
| PRIV-4 Off by default, off when unreadable | **Met** | `whole_line_on` (`:201-206`) returns False on any error; read fresh each call | `test_alv328_an_unreadable_switch_counts_as_off`, `..._off_again_on_the_very_next_request`, `..._the_field_is_there_and_off_on_a_fresh_site` |

### The specific questions asked

- **person()'s `has_permission("Employee Checkin", "read")` guard opens nothing.** It runs with
  no document, so it only checks role rights. It decides whether to call `get_list` at all;
  when it does, `get_list` still applies role rights, User Permissions and
  `checkin_query_conditions`. A login with no punch read right gets the page without a break,
  which is the safe result. **Verified in code** (`attendance_analytics.py:646-651`).
- **`/api/resource/Attendance` and `alvoraa_rules_why` (permlevel 0).** Still limited by the
  own-record User Permission, as before. A skip-level manager can read the reason text,
  "Breaks: N minutes" included, through the API with the switch off. That is Q-B, accepted.
- **`/api/resource/Employee Checkin`.** List: `checkin_query_conditions`. One record, PUT,
  DELETE, POST: `checkin_has_permission`. Both verified above.
- **Machine account.** Create of a new punch still allowed (`:263`); nothing else, as before.

## Findings

### Minor - an explicit share overrides "punches are read-only" (P3)

**Scenario (Inference, read in Frappe v16.35 source, not run):** HR shares one punch with a
manager and ticks "Can write". The manager sends `PUT /api/resource/Employee Checkin/<name>`.
Our hook says no, so `get_doc_permissions` returns `{write: 0}`
(`frappe/permissions.py:239-241`), but `has_permission` then checks shares
(`:208-210`) and finds the write share. The edit goes through. The same holds for any share
row that already exists at a tenant.

**Why only Minor:** the Employee role has no `share` right on Employee Checkin
(`employee_checkin.json`), so only HR or a System Manager can create such a share. It is a
deliberate HR act. But it means "nobody outside HR edits a punch" is true only while no write
share exists.

**Do before release:** a read-only count on DTC: DocShare rows with
`share_doctype = 'Employee Checkin'`, split by `write = 1` and `everyone = 1`. If 0, nothing
more. If not 0, Surbhi decides. No code change asked for now.

### Minor - two promised tests are missing (P3)

- SEC-11: AC-35 and the "REST GET leaves no log row" test. *Temporary debt*: removed by adding
  the two tests.
- SEC-5: AC-21 has no test and the page was never opened in a browser. *Temporary debt*:
  removed by the browser pass the engineer already lists before the dev push.

### P4 - thinner tests than `03` asked for (note only)

SEC-7 doors for the skip-level manager; SEC-8 "top manager Left"; SEC-9 REST PUT and the
Data Import assertion; SEC-10 reverse flip and "refused leaves no Version row"; SEC-4
`reportview.get` called directly. Each mechanism is the same line already tested on another
path, so the risk is low. *Acceptable simplification*.

### Unneeded surface

None found. No new endpoint, route, export, cache or copy of personal data. One Custom Field,
which the spec asked for.

## Worries (not findings)

- **W6 · A person's own new punch.** Staff may still create their own punch through REST
  (Surbhi's rule). `time` is permlevel 1, so Frappe resets it on create, but `log_type`,
  `device_id` and the coordinates are level 0 and chosen by the caller. A punch posted with
  the phone app's device id would look like a phone punch on the Attendance page. Pre-existing,
  not widened here. To check: one REST POST as a plain staff login.
- **W7 · Shift Attendance report** (Frappe HR, Employee role) reads Employee Checkin with raw
  queries. Its rows are filtered by User Permissions on the Attendance links
  (`frappe/desk/query_report.py:45, 946`), and it shows shift times only, no punches, photos,
  break or reason. Not changed here; checked only that far.
- W1-W3 from `03` are unchanged by this slice.

## Real data shape - what must exist to see the controls work

- Break: a company with an enabled pay rule set with a break allowance, and days with more
  than two punches. Without those, "no break shown" is the normal result, not proof of a
  control.
- Reason: Attendance rows with `alvoraa_evaluated_on` set (`03` release count d). ALV-326 is
  not on production, so DTC holds none yet.
- Read-only rule: DTC count E (12 Nov 2026) showed 0 punches added for others by non-HR logins
  in 120 days, so D1 breaks nobody. Share rows: **unknown** (finding above).

## What I could not check

- Any door over HTTP, and the page in a browser.
- DTC: DocShare rows on Employee Checkin, and Custom DocPerm `share` on Employee Checkin for
  non-HR roles. Needs a read-only count by whoever may run one on the tenant.
- File download of a punch photo, traced line by line (marked Inference above).

## Residual risk

| # | Risk | Label | Owner | Accepted |
|---|---|---|---|---|
| R1 | HR exports reasons, break minutes included; a manager lists the tree's reasons through the API | Intentional trade-off | Surbhi | Yes, 12 Nov 2026 (Q-2, Q-B) |
| R2 | W1-W3 in `03` | Temporary debt, outside this slice | Surbhi, via a ticket | Not yet |
| R3 | With the switch on, photo and location reads outside Desk are not logged | Temporary debt | Surbhi | Yes, 12 Nov 2026 (Q-E) |
| R4 | Staff edit or delete their own punches | Closed by this slice (ALV-333), verified above | - | - |
| R5 | A write share on a punch still lets a non-HR user edit it | Temporary debt until the DTC count says 0 | Surbhi | Not yet |

## Subtract pass

Removed from this review: a recommendation to block shares in the hook (it cannot: Frappe
checks shares after the hook), a call for a new audit log on reads of the reason (no
obligation asks for it), and a re-check of the pay figures (that is the techno-functional
reviewer's).

## R5 follow-up, 13 Nov 2026 (DTC read-only count, step32)

- Punch shares at DTC: **0** in total, 0 with write, 0 shared with everyone, 0 write shares
  held by people outside HR. R5 does not block the release.
- **New fact:** at DTC the roles allowed to share a punch include "Employee Self Service" and
  "Payroll team", not only HR. A staff member could share their own punch. Frappe should
  refuse a share that grants write the sharer does not hold, and from this slice nobody
  outside HR holds write, so the colleague should still not be able to edit. **Not tested.**
  Add one test: an Employee Self Service login shares its own punch with write; the share is
  refused or grants no write.
